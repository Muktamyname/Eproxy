import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import urllib.parse

st.set_page_config(page_title="J J International Proxy Pro", layout="wide")
st.title("⚖️ J J International: Autonomous Proxy Manager")

# 1. Sidebar Setup
st.sidebar.header("1. Upload Center")
uploaded_files = st.sidebar.file_uploader("Upload All Teacher Timetables (PDF)", accept_multiple_files=True, type=['pdf'])
contact_file = st.sidebar.file_uploader("Upload Teacher Contact List (Excel/CSV)", type=['xlsx', 'csv'])

st.sidebar.header("2. Attendance Management")
# Logic to handle the day for testing/live school days
today = datetime.datetime.now().strftime("%A")
if today == "Sunday": today = "Monday" 

absent_input = st.sidebar.text_area("Type Absent Teacher Names (one per line):")
btn_generate = st.sidebar.button("🚀 Run Auto-Allocation")

if uploaded_files:
    all_slots = []
    teacher_workload = {} 
    contacts = {}

    # Load Contacts for WhatsApp
    if contact_file:
        try:
            df_contacts = pd.read_excel(contact_file) if contact_file.name.endswith('xlsx') else pd.read_csv(contact_file)
            contacts = {str(row[0]).lower().strip(): str(row[1]).strip() for _, row in df_contacts.iterrows()}
        except Exception:
            st.error("Contact file format error. Please use: Name, Phone Number.")

    # PASS 1: Read all PDFs and identify every teacher's load
    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            
            # Find Teacher Name in the PDF header/file
            t_name = ""
            for row in table[:2]:
                for cell in row:
                    if cell and len(str(cell)) > 3 and "period" not in str(cell).lower():
                        t_name = str(cell).strip()
                        break
                if t_name: break
            if not t_name: t_name = file.name.replace(".pdf", "")
            
            headers = table[1]
            day_idx = next((i for i, d in enumerate(headers) if d and today.lower() in str(d).lower()), -1)
            
            if day_idx != -1:
                daily_count = 0
                for row in table[2:]:
                    if not row or any(x in str(row) for x in ["Break", "Lunch", "Short"]): continue
                    
                    sub_val = row[day_idx] if row[day_idx] else "FREE"
                    if sub_val != "FREE": daily_count += 1
                    
                    all_slots.append({
                        'teacher': t_name,
                        'period': row[0],
                        'time': row[1],
                        'subject_info': sub_val # This contains the Standard/Subject
                    })
                teacher_workload[t_name] = daily_count

    # View available teachers for troubleshooting
    with st.expander("🔍 View All Detected Teachers"):
        st.write(", ".join(teacher_workload.keys()))

    # PASS 2: Find Absent Teacher Classes and Allocate
    if btn_generate and absent_input:
        absent_list = [name.strip().lower() for name in absent_input.split('\n') if name.strip()]
        
        # 1. Identify classes that need a proxy
        needed_proxies = [s for s in all_slots if any(a in s['teacher'].lower() for a in absent_list) and s['subject_info'] != "FREE"]
        
        if needed_proxies:
            st.subheader(f"📋 Final Proxy Plan for {today}")
            
            for slot in needed_proxies:
                # 2. Find present teachers free during this specific period
                candidates = [s for s in all_slots if not any(a in s['teacher'].lower() for a in absent_list) 
                              and s['period'] == slot['period'] 
                              and (s['subject_info'] == "FREE" or "Library" in str(s['subject_info']))]
                
                if candidates:
                    # 3. Workload Balancer: Sort candidates by least daily periods
                    candidates.sort(key=lambda x: teacher_workload.get(x['teacher'], 99))
                    chosen = candidates[0]
                    
                    # Update workload so the next proxy goes to someone else
                    teacher_workload[chosen['teacher']] += 1
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**Period {slot['period']}**: {slot['teacher']} ({slot['subject_info']})")
                    c2.write(f"👉 **Proxy**: {chosen['teacher']} (Load: {teacher_workload[chosen['teacher']]})")
                    
                    # 4. WhatsApp with Standard details
                    phone = contacts.get(chosen['teacher'].lower().strip())
                    if phone:
                        msg = (f"Hello {chosen['teacher']}, Proxy assigned! "
                               f"Period: {slot['period']} ({slot['time']}), "
                               f"Class: {slot['subject_info']}. "
                               f"Regards, J J International.")
                        url = f"https://wa.me/{str(phone).strip()}?text={urllib.parse.quote(msg)}"
                        c3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({url})")
                    else:
                        c3.info("No Contact")
        else:
            st.warning("No teaching periods found for these names. Check spelling in the 'Detected Teachers' list above.")
