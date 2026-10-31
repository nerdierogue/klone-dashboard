import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Klone AI Sales Team", page_icon="🚀", layout="wide")

st.title("🚀 Klone: Autonomous AI Sales Team")
st.markdown("Generate hyper-personalized, research-backed cold emails at scale.")

# ==========================================
# 2. SIDEBAR: CONFIGURATION
# ==========================================
st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input("OpenRouter API Key", type="password", help="Starts with sk-or-v1-...")
hubspot_key = st.sidebar.text_input("HubSpot API Key (Optional)", type="password", help="Starts with pat-eu1-...")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Target List")
st.sidebar.markdown("Paste your targets below (Company | URL | Name | Email)")
default_targets = """Gong | https://www.gong.io | Amit | amit@gong.io
Outreach | https://www.outreach.io | Nate | nate@outreach.io
Salesloft | https://www.salesloft.com | Kyle | kyle@salesloft.com"""

target_input = st.sidebar.text_area("Targets", value=default_targets, height=200)

# ==========================================
# 3. THE KLONE ENGINE (Backend Functions)
# ==========================================
def scrape_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (KloneBot)'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.extract()
        return soup.get_text(separator='\n', strip=True)[:4000]
    except Exception as e:
        return f"Error scraping: {e}"

def ask_qwen(system_prompt, user_prompt, key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {e}"

def push_to_hubspot(lead_data, hubspot_key):
    """Push a lead to HubSpot as a new contact."""
    url = "https://api.hubapi.com/contacts/v1/contact"
    headers = {
        "Authorization": f"Bearer {hubspot_key}",
        "Content-Type": "application/json"
    }
    
    # Map our lead data to HubSpot's guaranteed standard contact fields
    payload = {
        "properties": [
            {"property": "email", "value": lead_data['email']},
            {"property": "firstname", "value": lead_data['name'].split()[0]},
            {"property": "lastname", "value": " ".join(lead_data['name'].split()[1:]) if len(lead_data['name'].split()) > 1 else ""}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return True, data.get('vid', 'Unknown')
    except requests.exceptions.HTTPError as e:
        # Print the exact reason HubSpot rejected it
        print(f"❌ HubSpot Error Details: {response.text}")
        if response.status_code == 409:
            return False, "Contact already exists"
        return False, f"HTTP Error: {response.status_code}"
    except Exception as e:
        return False, f"Error: {e}"

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
if st.button("🚀 Run Klone Agents", type="primary"):
    if not api_key.startswith("sk-or-"):
        st.error("⚠️ Please enter a valid OpenRouter API Key in the sidebar.")
        st.stop()

    # Parse targets
    lines = target_input.strip().split('\n')
    targets = []
    for line in lines:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) == 4:
            targets.append({"company": parts[0], "url": parts[1], "name": parts[2], "email": parts[3]})

    if not targets:
        st.error("⚠️ Please format targets as: Company | URL | Name | Email")
        st.stop()

    st.success(f"✅ Queueing {len(targets)} targets. Starting AI agents...")
    
    # Create a container for live updates
    results_container = st.container()
    
    generated_leads = []

    for i, target in enumerate(targets):
        with results_container:
            st.markdown(f"### 🎯 Processing {i+1}/{len(targets)}: **{target['company']}**")
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Step 1: Scrape
            status_text.text("🔍 Researcher is scraping the website...")
            progress_bar.progress(20)
            raw_text = scrape_website(target['url'])
            time.sleep(0.5) # Visual pause for UX

            # Step 2: Research Summary
            status_text.text("🧠 AI Brain is analyzing pain points...")
            progress_bar.progress(50)
            researcher_prompt = f"Summarize this website text for {target['company']}. Identify core product, target audience, and 2 specific sales pain points."
            research_summary = ask_qwen(researcher_prompt, raw_text, api_key)
            time.sleep(0.5)

            # Step 3: Draft Email
            status_text.text("✍️ SDR is drafting the personalized email...")
            progress_bar.progress(80)
            sdr_prompt = f"You are a top 1% B2B SDR. Write a hyper-personalized cold email to '{target['name']}' at {target['company']}. Pitch 'Klone' (an autonomous AI sales team). RULES: 1. Start with 'Hi {target['name']},'. 2. Reference a specific detail from the research. 3. NO cliché buzzwords. 4. Keep it under 100 words. 5. End with 'Open to a 5-min chat next Tuesday?'. 6. Sign off as 'Josh, Founder at Klone'. 7. Ensure perfect spacing."
            email_draft = ask_qwen(sdr_prompt, research_summary, api_key)
            progress_bar.progress(100)
            status_text.text("✅ Complete!")
            st.divider()

            # Save to our local list
            generated_leads.append({
                "company": target['company'],
                "name": target['name'],
                "email": target['email'],
                "research": research_summary,
                "draft": email_draft
            })

            # Push to HubSpot if key is provided
            if hubspot_key and (hubspot_key.startswith("pat-") or hubspot_key.startswith("eu1-") or hubspot_key.startswith("pat-eu1-")):
                with results_container:
                    status_text.text("📤 Pushing to HubSpot CRM...")
                    success, contact_id = push_to_hubspot({
                        "company": target['company'],
                        "name": target['name'],
                        "email": target['email'],
                        "draft": email_draft
                    }, hubspot_key)
                    
                    if success:
                        st.success(f"✅ Created HubSpot Contact ID: {contact_id}")
                    else:
                        st.warning(f"⚠️ HubSpot: {contact_id}")



    # ==========================================
    # 5. DISPLAY RESULTS
    # ==========================================
    st.success(f"🎉 Successfully processed {len(generated_leads)} targets!")
    
    st.markdown("### 📬 Generated Emails")
    for lead in generated_leads:
        with st.expander(f"📧 {lead['company']} - {lead['name']} ({lead['email']})"):
            st.markdown("**🔍 Research Summary:**")
            st.info(lead['research'])
            st.markdown("**✉️ Email Draft:**")
            st.success(lead['draft'])
            
    # Optional: Save to JSON behind the scenes
    with open("klone_mock_crm.json", "w") as f:
        json.dump(generated_leads, f, indent=2)