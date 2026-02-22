import streamlit as st
import pdfplumber
import datetime

st.set_page_config(page_title="J J International Proxy", layout="centered")
st.title("📲 School Proxy Generator")

# Mobile File Uploader
uploaded_files = st.file_uploader("Upload all Teacher PDFs", accept_multiple_files=True, type=['pdf'])

if uploaded_files:
    # Sunday Fix: Default to Monday for testing
    today = datetime.datetime.now().strftime("%A")
    if today == "Sunday": today = "Monday" 
    
    st.write(f"Showing Proxy for: **{today}**")
    absent_sub = st.text_input("Enter Absent Subject (e.g., Account):")

    if st.button("Generate Proxy Now"):
        for file in uploaded_files:
            with pdfplumber.open(file) as pdf:
                table = pdf.pages[0].extract_table()
                if not table: continue
                
                # Logic to find the day column
                headers = table[1]
                day_idx = next((i for i, d in enumerate(headers) if d and today in d), -1)
                
                if day_idx != -1:
                    for row in table[2:]:
                        if "Break" in str(row): continue
                        if len(row) > day_idx and row[day_idx] and absent_sub.lower() in row[day_idx].lower():
                            st.error(f"⚠️ {file.name}: Period {row[0]} needs Proxy.")
