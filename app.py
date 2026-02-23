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
uploaded_files = st.sidebar.file_uploader("Upload Timetables (PDF)", accept_multiple_files=True, type=['pdf'])
contact_file = st.sidebar.file_uploader("Upload Contacts (CSV/Excel)", type=['xlsx', 'csv', 'xls'])

st.sidebar.header("2. Attendance Management")
today = datetime.datetime.now().strftime("%A")
if today == "Sunday": today = "Monday" 

absent_input = st.sidebar.text_area("Absent Teacher Names (one per line):")
btn_generate = st.sidebar.button("🚀 Run Auto-Allocation")

# FORCE MATCH: This function removes dots, dashes, and spaces
def force_clean(txt):
    return "".join(filter(str.isalnum, str(txt))).lower()

if uploaded_files:
    all_slots = []
    teacher_workload = {} 
    contacts = {}

    if contact_file:
        try:
            # Reads your specific contact.csv
            df_c = pd.read_csv(contact_file) if contact_file.name.endswith('.csv') else pd.read_excel(contact_file)
            for _, row in df_c.iterrows():
                # Matches Column A names to Column B numbers
                contacts[force_clean(row[0])] = str(row[1]).strip()
        except Exception as e:
            st.sidebar.error(f"Contact File Error: {e}")

    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            
            # Smart Name Search for J J International PDFs
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
        # Shows you exactly what names were found
        st.write(list(teacher_workload.keys()))

    if btn_generate and absent_input:
        absent_list = [force_clean(n) for n in absent_input.split('\n') if n.strip()]
        # Finds matches even if user types with different spacing
        needed_proxies = [s for s in all_slots if force_clean(s['teacher']) in absent_list and s['subject_info'] != "FREE"]
        
        if needed_proxies:
            st.subheader(f"✅ Final Proxy Plan for {today}")
            report_data = []
            
            for slot in needed_proxies:
                # Workload balancing logic
                candidates = [s for s in all_slots if force_clean(s['teacher']) not in absent_list 
                              and str(s['period']) == str(slot['period']) 
                              and (s['subject_info'] == "FREE" or "Library" in str(s['subject_info']))]
                
                if candidates:
                    candidates.sort(key=lambda x: teacher_workload.get(x['teacher'], 99))
                    chosen = candidates[0]
                    teacher_workload[chosen['teacher']] += 1
                    
                    report_data.append({"Period": slot['period'], "Time": slot['time'], "Absent": slot['teacher'], "Class": slot['subject_info'], "Proxy": chosen['teacher']})
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**P{slot['period']}**: {slot['teacher']} ({slot['subject_info']})")
                    c2.write(f"👉 **Proxy**: {chosen['teacher']}")
                    
                    # Sends pre-filled WhatsApp message
                    phone = contacts.get(force_clean(chosen['teacher']))
                    if phone:
                        msg = f"Hello {chosen['teacher']}, Proxy assigned in P{slot['period']} for {slot['teacher']} ({slot['subject_info']})."
                        url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
                        c3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({url})")
                    else:
                        c3.info("No Number Found")

            if report_data:
                df_report = pd.DataFrame(report_data)
                output = BytesIO()
                # Requires openpyxl which is in your requirements.txt
                df_report.to_excel(output, index=False)
                st.download_button(label="📥 Download & Print Proxy Sheet", data=output.getvalue(), file_name=f"Proxies_{today}.xlsx")
        else:
            st.error("Match Failed. Copy the name exactly from the 'View All Detected Teachers' list above.")
