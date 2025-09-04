import streamlit as st
import google.generativeai as genai
import os
import time
import json
from streamlit_cookies_manager import CookieManager

# --- Cookie Manager Setup ---
cookies = CookieManager()

# --- Helper Functions for Cookie-based Rate Limiting ---
def check_rate_limit(limit=5, period_seconds=3600):
    """Checks if the user has exceeded the usage limit based on browser cookies."""
    usage_log_str = cookies.get('usage_log', '[]') # Get cookie, default to empty list string
    usage_log = json.loads(usage_log_str)
    
    current_time = time.time()
    cutoff_time = current_time - period_seconds

    # Filter out timestamps that are older than the period
    recent_timestamps = [ts for ts in usage_log if ts > cutoff_time]
    
    # CORRECT SYNTAX: Use dictionary-style assignment to set the cookie
    cookies['usage_log'] = json.dumps(recent_timestamps)
    
    return len(recent_timestamps) < limit

def add_usage_record():
    """Adds a new usage timestamp to the browser cookie."""
    usage_log_str = cookies.get('usage_log', '[]') # Get cookie, default to empty list string
    usage_log = json.loads(usage_log_str)
        
    usage_log.append(time.time())
    
    # CORRECT SYNTAX: Use dictionary-style assignment to set the cookie
    cookies['usage_log'] = json.dumps(usage_log)

# --- Configuration ---
# Securely loads your API key from Hugging Face's secrets manager
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# --- AI Model Setup ---
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Web App Interface ---
st.set_page_config(page_title="Job Application Summarizer", layout="wide")
st.title("📄 AI Job Application Summarizer")
st.write("Paste a job description below to get a concise summary and a list of key qualifications.")

job_description = st.text_area("Paste Job Description Here:", height=250)

if st.button("Generate Summary"):
    if not cookies.ready():
        st.warning("Cookies are not available. Please enable them in your browser.")
        st.stop()

    if not check_rate_limit():
        st.error("Rate limit exceeded. Please try again in an hour. (Limit: 5 summaries per hour)")
    elif not job_description.strip():
        st.warning("Please paste a job description first.")
    else:
        with st.spinner("Analyzing..."):
            try:
                # --- The Prompt for the AI ---
                prompt = f"""
                Analyze the following job description and provide two things:
                1. A concise, one-paragraph summary of the role's primary responsibilities.
                2. A bulleted list of the top 5-7 key qualifications, skills, or experience requirements mentioned.
                Job Description:
                ---
                {job_description}
                """
                response = model.generate_content(prompt)
                st.success("Summary Generated!")
                st.markdown(response.text)
                add_usage_record() # Log successful use in the cookie
            except Exception as e:
                st.error(f"An error occurred: {e}")
