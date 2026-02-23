import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import urllib.parse

st.set_page_config(page_title="J J International Proxy Pro", layout="wide")
st.title("🏫 J J International: WhatsApp Proxy Manager")

# 1. SIDEBAR: Upload Center
st.sidebar.header("1. Upload Center")
uploaded_files = st.sidebar.file_uploader("Upload Teacher Timetables (PDF)", accept_multiple_files=True, type=['pdf'])
contact_file = st.sidebar.file_uploader("Upload Teacher Contact List (Excel/CSV)", type=['xlsx', 'csv'])

# 2. Daily Attendance
st.sidebar.header("2. Daily Attendance")
today = datetime.datetime.now().strftime("%A")
if today == "Sunday": today = "Monday" 

absent_input = st.sidebar.text_area("Type Absent Teacher Names (one per line):")
# Add a clear button to trigger the search
btn_generate = st.sidebar.button("🔍 Generate Proxy Plan")

if uploaded_files:
    all_slots = []
    teacher_stats = {} 
    contacts = {}

    # Load Contacts safely
    if contact_file:
        try:
            df_contacts = pd.read_excel(contact_file) if contact_file.name.endswith('xlsx') else pd.read_csv(contact_file)
            contacts = dict(zip(df_contacts.iloc[:,0].astype(str).str.lower().str.strip(), df_contacts.iloc[:,1]))
        except Exception as e:
            st.error(f"Error reading Contact file: {e}")

    # Pass 1: Extract Data
    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            # Name is usually in the first row
            t_name = table[0][2].strip() if table[0][2] else file.name.replace(".pdf", "")
            headers = table[1]
            day_idx = next((i for i, d in enumerate(headers) if d and today in d), -1)
            
            if day_idx != -1:
                daily_count = 0
                for row in table[2:]:
                    if not row or any(x in str(row) for x in ["Break", "Lunch", "Short"]): continue
                    sub = row[day_idx] if row[day_idx] else "FREE"
                    if sub != "FREE": daily_count += 1
                    all_slots.append({'teacher': t_name, 'period': row[0], 'time': row[1], 'subject': sub})
                teacher_stats[t_name] = {'daily_load': daily_count}

    # Debug: Show found teachers so you know what to type
    with st.expander("👀 See all loaded teachers"):
        st.write(", ".join(teacher_stats.keys()))

    # Pass 2: Allocate when button is clicked
    if btn_generate and absent_input:
        absent_list = [name.strip().lower() for name in absent_input.split('\n') if name.strip()]
        
        # Identify who is absent
        for slot in all_slots:
            slot['is_absent'] = any(a in slot['teacher'].lower() for a in absent_list)

        needed_proxies = [s for s in all_slots if s['is_absent'] and s['subject'] != "FREE"]
        
        if needed_proxies:
            st.subheader(f"📋 Proxy Assignments for {today}")
            for slot in needed_proxies:
                # Find candidates
                candidates = [s for s in all_slots if not s['is_absent'] 
                              and s['period'] == slot['period'] 
                              and (s['subject'] == "FREE" or "P.E" in str(s['subject']) or "Libray" in str(s['subject']))]
                
                if candidates:
                    candidates.sort(key=lambda x: teacher_stats[x['teacher']]['daily_load'])
                    chosen = candidates[0]
                    teacher_stats[chosen['teacher']]['daily_load'] += 1
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**P{slot['period']}**: {slot['teacher']}")
                    c2.write(f"👉 **Proxy**: {chosen['teacher']}")
                    
                    # WhatsApp
                    phone = contacts.get(chosen['teacher'].lower().strip())
                    if phone:
                        msg = f"Hello {chosen['teacher']}, you have a Proxy in Period {slot['period']} for {slot['teacher']}. - J J International"
                        url = f"https://wa.me/{str(phone).strip()}?text={urllib.parse.quote(msg)}"
                        c3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({url})")
                    else:
                        c3.info("No Number")
        else:
            st.warning("No teaching periods found for the names entered. Check the spelling!")
