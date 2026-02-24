import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import urllib.parse
from io import BytesIO

st.set_page_config(page_title="J J International AI Proxy", layout="wide")
st.title("⚖️ J J International: Autonomous Proxy Agent")

# 1. Upload Center
st.sidebar.header("1. Data Center")
uploaded_files = st.sidebar.file_uploader("Upload Timetables (PDF)", accept_multiple_files=True, type=['pdf'])
contact_file = st.sidebar.file_uploader("Upload Contacts (CSV/Excel)", type=['xlsx', 'csv', 'xls'])

st.sidebar.header("2. Attendance")
today = datetime.datetime.now().strftime("%A")
if today == "Sunday": today = "Monday" 

absent_input = st.sidebar.text_area("Absent Teacher Names (Comp, Chem, English, etc.):")
btn_generate = st.sidebar.button("🚀 Run Auto-Allocation")

# AI Normalization: Removes quotes, dots, and spaces
def ai_clean(txt):
    return "".join(filter(str.isalnum, str(txt))).lower().strip()

if uploaded_files:
    all_teacher_data = []
    teacher_stats = {} 
    contacts = {}

    # Load Contacts
    if contact_file:
        try:
            df_c = pd.read_csv(contact_file) if contact_file.name.endswith('.csv') else pd.read_excel(contact_file)
            for _, row in df_c.iterrows():
                contacts[ai_clean(row[0])] = str(row[1]).strip()
        except Exception:
            st.sidebar.error("Check Contact File Format")

    # Step 1: Deep Scan PDFs for Load and Lectures
    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            table = pdf.pages[0].extract_table()
            if not table: continue
            
            t_name = file.name.replace(".pdf", "").strip()
            
            # Find Day Headers (TUE vs Tuesday)
            h_row = -1
            headers = []
            for i, row in enumerate(table):
                if any(day in str(row).lower() for day in ["mon", "tue", "wed", "thu", "fri", "sat"]):
                    headers = row
                    h_row = i
                    break
            
            day_idx = next((i for i, d in enumerate(headers) if d and today[:3].lower() in str(d).lower()), -1)
            
            if day_idx != -1:
                daily_load = 0
                weekly_load = 0
                for row in table[h_row+1:]:
                    if not row or len(row) < 2: continue
                    if any(x in str(row).lower() for x in ["break", "lunch", "short"]): continue
                    
                    # Calculate Weekly Load (any non-empty cell in day columns)
                    for cell in row[2:]: # Assuming periods are cols 2+
                        if cell and str(cell).strip(): weekly_load += 1
                    
                    raw_val = row[day_idx]
                    is_free = (raw_val is None or str(raw_val).strip() == "")
                    
                    if not is_free: daily_load += 1
                    
                    all_teacher_data.append({
                        'teacher': t_name, 
                        'period': row[0], 
                        'time': row[1] if len(row) > 1 else "", 
                        'subject': str(raw_val).strip() if not is_free else "FREE",
                        'is_free': is_free
                    })
                teacher_stats[t_name] = {'daily': daily_load, 'weekly': weekly_load}

    # Step 2: Allocation Logic
    if btn_generate and absent_input:
        absent_list = [ai_clean(n) for n in absent_input.split('\n') if n.strip()]
        needed_proxies = [s for s in all_teacher_data if ai_clean(s['teacher']) in absent_list and not s['is_free']]
        
        if needed_proxies:
            st.subheader(f"✅ Final Proxy Plan for {today}")
            report_data = []
            
            for slot in needed_proxies:
                # Find all teachers who are FREE in this specific period
                candidates = [s for s in all_teacher_data if ai_clean(s['teacher']) not in absent_list 
                              and str(s['period']) == str(slot['period']) and s['is_free']]
                
                if candidates:
                    # Sort by least daily workload, then least weekly workload
                    candidates.sort(key=lambda x: (teacher_stats[x['teacher']]['daily'], teacher_stats[x['teacher']]['weekly']))
                    chosen = candidates[0]
                    
                    # Update their load so they aren't overworked in the next loop
                    teacher_stats[chosen['teacher']]['daily'] += 1
                    
                    report_data.append({
                        "Period": slot['period'], "Time": slot['time'], 
                        "Absent Teacher": slot['teacher'], "Class": slot['subject'], 
                        "Assigned Proxy": chosen['teacher']
                    })
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**P{slot['period']}**: {slot['teacher']} ({slot['subject']})")
                    c2.write(f"👉 **Proxy**: {chosen['teacher']}")
                    
                    phone = contacts.get(ai_clean(chosen['teacher']))
                    if phone:
                        msg = f"Hello {chosen['teacher']}, Proxy in P{slot['period']} for {slot['teacher']} ({slot['subject']})."
                        url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
                        c3.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-Send-25D366?style=for-the-badge&logo=whatsapp)]({url})")
                    else:
                        c3.info("No Number")

            if report_data:
                df_r = pd.DataFrame(report_data)
                out = BytesIO()
                df_r.to_excel(out, index=False)
                st.download_button(label="📥 Download Proxy Sheet", data=out.getvalue(), file_name=f"Proxies_{today}.xlsx")
        else:
            st.error("AI Error: No classes detected for these names. Check your PDF content!")
