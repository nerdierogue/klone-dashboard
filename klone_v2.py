import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
# PASTE YOUR OPENROUTER API KEY BELOW
API_KEY = "PASTE_YOUR_KEY_HERE"  # Example: "sk-or-v1-abc123..."
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ==========================================
# 2. THE TARGET LIST (Our "Mini-Excel Sheet")
# ==========================================
# Each target is a dictionary with the info we need.
# To add more companies, just copy/paste a new block!
TARGET_LIST = [
    {
        "company": "Gong",
        "url": "https://www.gong.io",
        "prospect_name": "Amit",
        "prospect_email": "amit@gong.io"
    },
    {
        "company": "Outreach",
        "url": "https://www.outreach.io",
        "prospect_name": "Nate",
        "prospect_email": "nate@outreach.io"
    },
    {
        "company": "Salesloft",
        "url": "https://www.salesloft.com",
        "prospect_name": "Kyle",
        "prospect_email": "kyle@salesloft.com"
    }
]

# ==========================================
# 3. THE KLONE TOOLS
# ==========================================
def scrape_website(url):
    print(f"🔍 [Researcher] Scraping {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (KloneBot)'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.extract()
            
        text = soup.get_text(separator='\n', strip=True)
        print("✅ [Researcher] Website scraped successfully.")
        return text[:4000]
    except Exception as e:
        print(f"❌ Error scraping: {e}")
        return ""

def ask_qwen(system_prompt, user_prompt):
    print("🧠 [AI Brain] Thinking...")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
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
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"❌ Error calling AI: {e}")
        raw_text = response.text if 'response' in locals() else "No response object"
        print(f"🔍 RAW API RESPONSE: {raw_text}")
        return "Error generating response."

def log_to_crm(company, email, research, draft):
    print("📂 [Sales Ops] Logging to CRM...")
    crm_file = "klone_mock_crm.json"
    try:
        with open(crm_file, 'r') as f:
            crm_data = json.load(f)
    except:
        crm_data = []
        
    crm_data.append({
        "id": len(crm_data) + 1,
        "company": company,
        "email": email,
        "research_summary": research,
        "email_draft": draft,
        "status": "Drafted",
        "created_at": datetime.now().isoformat()
    })
    
    with open(crm_file, 'w') as f:
        json.dump(crm_data, f, indent=2)
    print("✅ [Sales Ops] Logged successfully!")

# ==========================================
# 4. RUN THE BATCH PIPELINE
# ==========================================
if __name__ == "__main__":
    print("🚀 Klone V3 BATCH MVP: Starting Pipeline...\n")
    print(f"📋 Total targets in queue: {len(TARGET_LIST)}\n")
    
    total_processed = 0
    
    # THE LOOP: Process every target in the list
    for i, target in enumerate(TARGET_LIST, start=1):
        print(f"\n{'='*60}")
        print(f"🎯 TARGET {i} of {len(TARGET_LIST)}: {target['company']}")
        print(f"{'='*60}")
        
        # 1. RESEARCH PHASE
        raw_text = scrape_website(target['url'])
        
        researcher_prompt = f"You are an elite B2B market researcher. Summarize this website text for {target['company']}. Identify their core product, target audience, and 2 specific sales pain points they might have."
        research_summary = ask_qwen(researcher_prompt, raw_text)
        
        # 2. SDR DRAFTING PHASE (with spacing fix)
        sdr_prompt = f"You are a top 1% B2B SDR. Write a hyper-personalized cold email to '{target['prospect_name']}' at {target['company']}. Pitch 'Klone' (an autonomous AI sales team). RULES: 1. Start with 'Hi {target['prospect_name']},'. 2. Reference a specific detail from the research. 3. NO cliché buzzwords like 'supercharge', 'unlock', or 'game-changer'. 4. Keep it under 100 words. 5. End with a low-friction CTA like 'Open to a 5-min chat next Tuesday?'. 6. Sign off as 'Josh, Founder at Klone'. 7. Ensure perfect spacing between words - no merged words."
        email_draft = ask_qwen(sdr_prompt, research_summary)
        
        # 3. SALES OPS PHASE
        log_to_crm(target['company'], target['prospect_email'], research_summary, email_draft)
        
        total_processed += 1
        print(f"✅ Completed {target['company']} ({total_processed}/{len(TARGET_LIST)})")
    
    print(f"\n{'='*60}")
    print(f"🎉 BATCH COMPLETE: Successfully processed {total_processed} targets!")
    print(f"📂 Check 'klone_mock_crm.json' to see all {total_processed} leads.")
    print(f"{'='*60}")