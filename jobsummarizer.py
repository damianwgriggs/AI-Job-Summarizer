import streamlit as st
import google.generativeai as genai
import time
import sqlite3
from streamlit.web.server.server import Server

# --- Database Setup ---
conn = sqlite3.connect('/tmp/rate_limit.db', check_same_thread=False)
c = conn.cursor()
# Create table if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS usage (
        ip_address TEXT,
        timestamp REAL
    )
''')
conn.commit()


# --- Helper Functions ---

def get_ip_address():
    """An undocumented way to get the user's IP address from Streamlit."""
    try:
        session_infos = Server.get_current()._session_info_by_id.values()
        # The X-Forwarded-For header is the standard way to get the original IP
        # when behind a proxy.
        for session_info in session_infos:
            if hasattr(session_info, 'ws') and hasattr(session_info.ws, 'request'):
                headers = session_info.ws.request.headers
                if 'X-Forwarded-For' in headers:
                    return headers['X-Forwarded-For'].split(',')[0]
        return None
    except Exception:
        return None

def check_rate_limit(ip, limit=5, period_seconds=3600):
    """Checks if the IP has exceeded the usage limit in the given period."""
    current_time = time.time()
    cutoff_time = current_time - period_seconds
    
    c.execute("SELECT COUNT(*) FROM usage WHERE ip_address = ? AND timestamp > ?", (ip, cutoff_time))
    count = c.fetchone()[0]
    
    # Clean up old records to keep the database small
    c.execute("DELETE FROM usage WHERE timestamp <= ?", (cutoff_time,))
    conn.commit()
    
    return count < limit

def add_usage_record(ip):
    """Adds a new usage timestamp for the given IP."""
    current_time = time.time()
    c.execute("INSERT INTO usage (ip_address, timestamp) VALUES (?, ?)", (ip, current_time))
    conn.commit()


# --- Configuration ---
# Your API key should be stored as a secret on Hugging Face, not directly in the code.
# For now, we'll continue with the direct key method.
genai.configure(api_key="YOUR_API_KEY") # Replace with your key

# --- AI Model Setup ---
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Web App Interface ---
st.set_page_config(page_title="Job Application Summarizer", layout="wide")

st.title("📄 AI Job Application Summarizer")
st.write("Paste a job description below to get a concise summary and a list of key qualifications.")

job_description = st.text_area("Paste Job Description Here:", height=250)

if st.button("Generate Summary"):
    ip_address = get_ip_address()
    
    if ip_address is None:
        st.error("Could not identify your IP address. Please try again later.")
    elif not check_rate_limit(ip_address):
        st.error("Rate limit exceeded. Please try again in an hour. (Limit: 5 summaries per hour)")
    elif not job_description.strip():
        st.warning("Please paste a job description first.")
    else:
        # --- The Prompt for the AI ---
        prompt = f"""
        Analyze the following job description and provide two things:
        1. A concise, one-paragraph summary of the role's primary responsibilities.
        2. A bulleted list of the top 5-7 key qualifications, skills, or experience requirements mentioned.

        Job Description:
        ---
        {job_description}
        """

        # --- Sending the Prompt to the AI ---
        with st.spinner("Analyzing..."):
            try:
                response = model.generate_content(prompt)
                st.success("Summary Generated!")
                st.markdown(response.text)
                # Only add a usage record after a successful generation
                add_usage_record(ip_address)
            except Exception as e:
                st.error(f"An error occurred: {e}")