import asyncio
import os
from openai import OpenAI
from agents import Agent, Runner, function_tool, WebSearchTool
from dotenv import load_dotenv
import requests
    
load_dotenv()

# Load environment variables
load_dotenv()
access_token = os.getenv("ACCESS_TOKEN")
api_domain = os.getenv("API_DOMAIN") or "https://www.zohoapis.com"

headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Content-Type": "application/json"
}

# Step 1: Get Account ID for the given account name
def get_account_id(account_name):
    search_url = f"{api_domain}/crm/v2/Accounts/search"
    params = {
        "criteria": f"(Account_Name:equals:{account_name})"
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        accounts = response.json().get("data", [])
        if accounts:
            return accounts[0]["id"]
    print("❌ Account not found:", response.text)
    return None

# Step 2: Find the Deal by Name and Account ID
def find_deal_by_name_and_account(deal_name, account_id):
    search_url = f"{api_domain}/crm/v2/Deals/search"
    params = {
        "criteria": f"(Deal_Name:equals:{deal_name})"
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        deals = response.json().get("data", [])
        for deal in deals:
            related_account_id = deal.get("Account_Name", {}).get("id")
            if related_account_id == account_id:
                return deal
    print("❌ Deal not found:", response.text)
    return None

# Step 3: Update the Deal Stage
def update_deal_stage(deal_id, new_stage="Closed (Won)"):
    update_url = f"{api_domain}/crm/v2/Deals"
    payload = {
        "data": [
            {
                "id": deal_id,
                "Stage": new_stage
            }
        ]
    }
    response = requests.put(update_url, headers=headers, json=payload)
    if response.status_code == 200:
        print("✅ Deal stage updated to:", new_stage)
    else:
        print("❌ Failed to update deal:", response.status_code, response.text)

# Function to process the deal stage
@function_tool
def process_deal_stage(account_name: str, deal_name: str, deal_stage: str):
    print(f"Processing deal stage update for '{deal_name}' under account '{account_name}' to '{deal_stage}'")
    account_id = get_account_id(account_name)
    if account_id:
        deal = find_deal_by_name_and_account(deal_name, account_id)
        if deal:
            update_deal_stage(deal["id"], deal_stage)
        else:
            print(f"❌ Deal '{deal_name}' not found under '{account_name}'")
    else:
        print(f"❌ Account '{account_name}' not found")

    
client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
)


crm_agent = Agent(
    name="Communicates with CRM",
    handoff_description="Specialist agent for creating, reading, updating and deleting accounts and deals in Zoho CRM",
    instructions="You are integrated with a CRM system. Retrieve the account name, deal name and deal stage from the conversation and pass it to the tool.",
    tools=[process_deal_stage],
)

sales_coach_agent = Agent(
    name="Provides Sales Coaching",
    handoff_description="Specialist agent for sales coaching",
    instructions="You are a Specialist AI agent for sales coaching. Focus on refining messaging, objection handling, \
    and closing techniques. Deliver concise, actionable, and context-aware coaching to help reps consistently improve performance.",
    tools=[WebSearchTool(client, "https://www.salescoach.com")],
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's question, if the question is about updating \
    a deal use the CRM agent, if the question is about sales coaching use the Sales Coach agent",
    handoffs=[crm_agent, sales_coach_agent]
)

async def main():
    result = await Runner.run(triage_agent, "Hi, can you update the deal stage for the deal name 'C# Developer' under the account name 'Ford' to 'Closed (Won)'?")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())