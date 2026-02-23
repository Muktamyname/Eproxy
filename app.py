import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import urllib.parse
from io import BytesIO

st.set_page_config(page_title="J J International Proxy Pro", layout="wide")
st.title("⚖️ J J International: Autonomous Proxy Manager")

# 1. Sidebar Setup
st.sidebar.header("1. Upload Center")
uploaded_files = st.sidebar.file_uploader("Upload Teacher Timetables (PDF)", accept_multiple_files=True, type=['pdf'])
contact_file = st.sidebar.file_uploader("Upload Teacher Contact List (Excel/CSV)", type=['xlsx', 'csv'])

st.sidebar.header("2. Attendance Management")
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
            st.error("Contact file format error.")

    # PASS 1: Build Schedule Database
    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            
            # Smart Name Search: Finds the teacher name in the header
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
                    all_slots.append({'teacher': t_name, 'period': row[0], 'time': row[1], 'subject_info': sub_val})
                teacher_workload[t_name] = daily_count

    with st.expander("🔍 View All Detected Teachers"):
        st.write(", ".join(teacher_workload.keys()))

    # PASS 2: Allocation & Output
    if btn_generate and absent_input:
        absent_list = [name.strip().lower() for name in absent_input.split('\n') if name.strip()]
        needed_proxies = [s for s in all_slots if any(a in s['teacher'].lower() for a in absent_list) and s['subject_info'] != "FREE"]
        
        if needed_proxies:
            st.subheader(f"📋 Final Proxy Plan for {today}")
            report_data = []
            
            for slot in needed_proxies:
                candidates = [s for s in all_slots if not any(a in s['teacher'].lower() for a in absent_list) 
                              and s['period'] == slot['period'] 
                              and (s['subject_info'] == "FREE" or "Library" in str(s['subject_info']))]
                
                if candidates:
                    candidates.sort(key=lambda x: teacher_workload.get(x['teacher'], 99))
                    chosen = candidates[0]
                    teacher_workload[chosen['teacher']] += 1
                    
                    # Store data for Download Sheet
                    report_data.append({
                        "Period": slot['period'], "Time": slot['time'],
                        "Absent Teacher": slot['teacher'], "Class": slot['subject_info'],
                        "Assigned Proxy": chosen['teacher']
                    })
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**P{slot['period']}**: {slot['teacher']} ({slot['subject_info']})")
                    c2.write(f"👉 **Proxy**: {chosen['teacher']}")
                    
                    # WhatsApp Logic
                    phone = contacts.get(chosen['teacher'].lower().strip())
                    if phone:
                        msg = f"Hello {chosen['teacher']}, you have a Proxy in P{slot['period']} for {slot['teacher']} ({slot['subject_info']}). - J J International"
                        url = f"https://wa.me/{str(phone).strip()}?text={urllib.parse.quote(msg)}"
                        c3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({url})")
                    else:
                        c3.info("No Contact Found")

            # 3. THE DOWNLOAD BUTTON (Excel Export)
            if report_data:
                df_report = pd.DataFrame(report_data)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_report.to_excel(writer, index=False, sheet_name='ProxyAssignments')
                st.download_button(
                    label="📥 Download Proxy Sheet (Excel)",
                    data=output.getvalue(),
                    file_name=f"J_J_International_Proxies_{today}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No teaching periods found. Please ensure the names typed match the 'Detected Teachers' list exactly.")
