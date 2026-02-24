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
contact_file = st.sidebar.file_uploader("Upload Teacher Contacts (CSV/Excel)", type=['xlsx', 'csv', 'xls'])

st.sidebar.header("2. Attendance Management")
today = datetime.datetime.now().strftime("%A")
if today == "Sunday": today = "Monday" 

absent_input = st.sidebar.text_area("Absent Teacher Names (one per line):")
btn_generate = st.sidebar.button("🚀 Run Auto-Allocation")

# Normalizes text to ensure a 100% match
def normalize(txt):
    return "".join(filter(str.isalnum, str(txt))).lower()

if uploaded_files:
    all_slots = []
    teacher_workload = {} 
    contacts = {}

    if contact_file:
        try:
            df_c = pd.read_csv(contact_file) if contact_file.name.endswith('.csv') else pd.read_excel(contact_file)
            for _, row in df_c.iterrows():
                # Store using normalized names from your Excel
                contacts[normalize(row[0])] = str(row[1]).strip()
        except Exception as e:
            st.sidebar.error(f"Contact File Error: {e}")

    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            
            # DEEP STUDY FIX: Use ONLY the filename you created (e.g., A, B, C)
            # This ignores the "Std. - 12 Com" text inside the PDF entirely
            t_name = file.name.replace(".pdf", "").strip()
            
            # Find the Day Column automatically
            headers = []
            header_row_idx = -1
            for i, row in enumerate(table):
                if any(day in str(row).lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]):
                    headers = row
                    header_row_idx = i
                    break
            
            day_idx = next((i for i, d in enumerate(headers) if d and today.lower() in str(d).lower()), -1)
            
            if day_idx != -1:
                daily_count = 0
                for row in table[header_row_idx+1:]:
                    if not row or not row[0]: continue
                    if any(x in str(row).lower() for x in ["break", "lunch", "short"]): continue
                    
                    raw_val = row[day_idx]
                    # If blank, it's a free period
                    if raw_val is None or str(raw_val).strip() == "":
                        is_free = True
                        sub_val = "FREE"
                    else:
                        is_free = False
                        sub_val = str(raw_val).strip()
                        daily_count += 1
                    
                    all_slots.append({'teacher': t_name, 'period': row[0], 'time': row[1] if len(row) > 1 else "", 'subject_info': sub_val, 'is_free': is_free})
                teacher_workload[t_name] = daily_count

    with st.expander("🔍 View All Detected Teachers"):
        st.write(list(teacher_workload.keys()))

    if btn_generate and absent_input:
        absent_list = [normalize(n) for n in absent_input.split('\n') if n.strip()]
        needed_proxies = [s for s in all_slots if normalize(s['teacher']) in absent_list and not s['is_free']]
        
        if needed_proxies:
            st.subheader(f"✅ Final Proxy Plan for {today}")
            report_data = []
            for slot in needed_proxies:
                candidates = [s for s in all_slots if normalize(s['teacher']) not in absent_list 
                              and str(s['period']) == str(slot['period']) and s['is_free']]
                
                if candidates:
                    candidates.sort(key=lambda x: teacher_workload.get(x['teacher'], 99))
                    chosen = candidates[0]
                    teacher_workload[chosen['teacher']] += 1
                    
                    report_data.append({"Period": slot['period'], "Time": slot['time'], "Absent": slot['teacher'], "Class": slot['subject_info'], "Proxy": chosen['teacher']})
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**P{slot['period']}**: {slot['teacher']} ({slot['subject_info']})")
                    c2.write(f"👉 **Proxy**: {chosen['teacher']}")
                    
                    phone = contacts.get(normalize(chosen['teacher']))
                    if phone:
                        msg = f"Hello {chosen['teacher']}, Proxy in P{slot['period']} for {slot['teacher']} ({slot['subject_info']})."
                        url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
                        c3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({url})")
                    else:
                        c3.info("No Number")

            if report_data:
                df_report = pd.DataFrame(report_data)
                output = BytesIO()
                df_report.to_excel(output, index=False)
                st.download_button(label="📥 Download & Print Proxy Sheet", data=output.getvalue(), file_name=f"Proxies_{today}.xlsx")
        else:
            st.error("No matches found. Please copy the name from 'Detected Teachers' above.")
