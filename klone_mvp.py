import os
import json
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from datetime import datetime

# This loads our secret API key from the .env file
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_openai import ChatOpenAI

# ==========================================
# 1. CONNECT TO QWEN AI BRAIN
# ==========================================
qwen_llm = ChatOpenAI(
    model="qwen-plus", 
    api_key="sk-ws-H.DHYIRIL.ODuf.MEUCIQCZKoMwiP2h7w6s9RQm6NHkxtW_EQfPdhKxc0jB6Jkq7QIgQrHQycEKa4bFepFAhKbeZ4tWHhnAuzkkzlGTZdOGgHk",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.3 
)

# ==========================================
# 2. DEFINE THE AGENT TOOLS
# ==========================================
@tool("Website Scraper")
def scrape_website(url: str) -> str:
    """Scrapes the text content of a given website URL and returns clean text."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KloneBot/1.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.extract()
            
        text = md(str(soup))
        return text[:4000] # Keep it short so the AI doesn't get overwhelmed
    except Exception as e:
        return f"Error scraping website: {str(e)}"

@tool("Mock CRM Logger")
def log_to_crm(company_name: str, prospect_email: str, email_draft: str, research_summary: str) -> str:
    """Logs a new lead, the research summary, and the drafted email to the mock CRM JSON file."""
    crm_file = "klone_mock_crm.json"
    
    try:
        with open(crm_file, 'r') as f:
            crm_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        crm_data = []

    new_lead = {
        "id": len(crm_data) + 1,
        "company": company_name,
        "prospect_email": prospect_email,
        "research_summary": research_summary,
        "email_draft": email_draft,
        "status": "Drafted - Pending Human Review",
        "created_at": datetime.now().isoformat()
    }
    crm_data.append(new_lead)

    with open(crm_file, 'w') as f:
        json.dump(crm_data, f, indent=2)

    return f"Success: Logged {company_name} to Klone CRM with Lead ID {new_lead['id']}."

# ==========================================
# 3. DEFINE THE KLONE AGENTS
# ==========================================
researcher = Agent(
    role='Elite Market Researcher',
    goal='Deeply understand the prospect company by analyzing their website to find their core product, target audience, and potential pain points.',
    backstory='You are a veteran B2B researcher. You extract strategic business intelligence that sales teams can use to win deals.',
    llm=qwen_llm,
    tools=[scrape_website],
    verbose=True,
    allow_delegation=False
)

sdr = Agent(
    role='Klone SDR (Sales Development Rep)',
    goal='Craft a hyper-personalized, high-converting cold email based on the research provided.',
    backstory='You are a top 1% SDR. You hate generic spam. You write concise, punchy, and highly relevant emails. You pitch Klone as the solution to their sales pain points.',
    llm=qwen_llm,
    verbose=True,
    allow_delegation=False
)

sales_ops = Agent(
    role='Sales Operations Manager',
    goal='Ensure all lead data, research, and email drafts are accurately logged into the CRM.',
    backstory='You are a meticulous Sales Ops professional. You ensure CRM hygiene is perfect.',
    llm=qwen_llm,
    tools=[log_to_crm],
    verbose=True,
    allow_delegation=False
)

# ==========================================
# 4. RUN THE PIPELINE
# ==========================================
if __name__ == "__main__":
    # We are targeting Gong.io for our first test
    target_url = "https://www.gong.io"
    prospect_name = "Amit"
    prospect_email = "amit@gong.io"
    
    print(f"\n🚀 Klone MVP: Initiating outbound sequence for {target_url}...\n")

    # Task 1: Research
    research_task = Task(
        description=f"Scrape and analyze the website at {target_url}. Provide a concise summary of what the company does, who they sell to, and 2-3 potential pain points they might have regarding sales efficiency.",
        expected_output="A structured summary containing: 1. Core Product/Service. 2. Target Audience. 3. Identified Sales Pain Points.",
        agent=researcher
    )

    # Task 2: Draft Email
    email_task = Task(
        description=f"Using the research summary, write a cold email to {prospect_name} at {prospect_email}. Keep it under 120 words. Use a strong, personalized hook. Pitch Klone. End with a soft call to action.",
        expected_output="The final draft of the cold email body. Do not include subject lines.",
        agent=sdr,
        context=[research_task] 
    )

    # Task 3: Log to CRM
    crm_task = Task(
        description=f"Log the following into the CRM: Company Name: Gong, Prospect Email: {prospect_email}. Include the research summary and the final email draft.",
        expected_output="A confirmation message that the lead was successfully logged into the CRM.",
        agent=sales_ops,
        context=[research_task, email_task]
    )

    # Assemble the Crew and kick it off
    klone_crew = Crew(
        agents=[researcher, sdr, sales_ops],
        tasks=[research_task, email_task, crm_task],
        process=Process.sequential,
        verbose=True
    )

    result = klone_crew.kickoff()
    
    print("\n" + "="*50)
    print("✅ KLONE MVP EXECUTION COMPLETE")
    print("="*50)
    print(result)