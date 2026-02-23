import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import urllib.parse

st.set_page_config(page_title="J J International Proxy Pro", layout="wide")
st.title("🏫 J J International: WhatsApp Proxy Manager")

# 1. SIDEBAR: Setup for Timetables and Contacts
st.sidebar.header("1. Upload Center")
uploaded_files = st.sidebar.file_uploader("Upload Teacher Timetables (PDF)", accept_multiple_files=True, type=['pdf'])
contact_file = st.sidebar.file_uploader("Upload Teacher Contact List (Excel/CSV)", type=['xlsx', 'csv'])

# 2. Daily Attendance Setup
st.sidebar.header("2. Daily Attendance")
today = datetime.datetime.now().strftime("%A")
if today == "Sunday": today = "Monday" 

absent_input = st.sidebar.text_area("Absent Teacher Names (One per line):").lower().split('\n')
absent_list = [name.strip() for name in absent_input if name.strip()]

if uploaded_files:
    all_slots = []
    teacher_stats = {} 
    contacts = {}

    # Load Contacts from Excel/CSV
    if contact_file:
        df_contacts = pd.read_excel(contact_file) if contact_file.name.endswith('xlsx') else pd.read_csv(contact_file)
        # Assuming Name is 1st column and Phone is 2nd column
        contacts = dict(zip(df_contacts.iloc[:,0].str.lower(), df_contacts.iloc[:,1]))

    # Pass 1: Build Master Schedule from PDFs
    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            t_name = table[0][2] if table[0][2] else file.name.replace(".pdf", "")
            headers = table[1]
            day_idx = next((i for i, d in enumerate(headers) if d and today in d), -1)
            
            if day_idx != -1:
                daily_count = 0
                for row in table[2:]:
                    if not row or "Break" in str(row): continue
                    sub = row[day_idx] if row[day_idx] else "FREE"
                    if sub != "FREE": daily_count += 1
                    all_slots.append({'teacher': t_name, 'period': row[0], 'time': row[1], 'subject': sub, 'is_absent': any(a in t_name.lower() for a in absent_list)})
                teacher_stats[t_name] = {'daily_load': daily_count}

    # Pass 2: Fair Allocation Logic
    needed_proxies = [s for s in all_slots if s['is_absent'] and s['subject'] != "FREE"]
    
    if needed_proxies:
        st.subheader(f"📋 WhatsApp Proxy Assignments for {today}")
        
        for slot in needed_proxies:
            candidates = [s for s in all_slots if not s['is_absent'] and s['period'] == slot['period'] and (s['subject'] == "FREE" or "P.E" in str(s['subject']) or "Libray" in str(s['subject']))]
            
            if candidates:
                candidates.sort(key=lambda x: teacher_stats[x['teacher']]['daily_load'])
                chosen = candidates[0]
                teacher_stats[chosen['teacher']]['daily_load'] += 1
                
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"**Period {slot['period']}**: {slot['teacher']} (Absent)")
                col2.write(f"👉 **Assigned to**: {chosen['teacher']}")
                
                # WhatsApp Button Logic
                phone = contacts.get(chosen['teacher'].lower())
                if phone:
                    msg = f"Hello {chosen['teacher']}, you have a Proxy in Period {slot['period']} ({slot['time']}) for {slot['teacher']}. Regards, J J International School."
                    encoded_msg = urllib.parse.quote(msg)
                    whatsapp_url = f"https://wa.me/{phone}?text={encoded_msg}"
                    col3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({whatsapp_url})")
                else:
                    col3.warning("No Phone #")
