import asyncio
import os
import json
import warnings
from dotenv import load_dotenv
from groq import AsyncGroq
from tavily import TavilyClient
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal
import mailtrap as mt

warnings.filterwarnings("ignore", category=RuntimeWarning)
load_dotenv(override=True)

# 1. Initialize Clients
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# 2. Define the Rigid Pydantic Structure
class AgentStateResponse(BaseModel):
    status: Literal["searching", "complete"] = Field(
        description="Current workflow phase. Set to 'searching' if more web data is required, or 'complete' if ready to output final findings."
    )
    query: Optional[str] = Field(
        default=None, 
        description="The optimized web search keywords string. Required if status is 'searching'."
    )
    final_answer: Optional[str] = Field(
        default=None, 
        description="The detailed synthesized summary citing facts and URLs. Required if status is 'complete'."
    )

# 3. Custom Local Web Search Tool (Tavily)
def local_web_search(query: str) -> str:
    try:
        response = tavily.search(query=str(query), max_results=3)
        results = response.get('results', [])
        if not results:
            return "No search results found."
        
        formatted = []
        for r in results:
            formatted.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content']}\n---")
        return "\n".join(formatted)
    except Exception as e:
        return f"Search execution failed: {str(e)}"

# 4. Native EmailTrap Dispatcher Tool
def send_research_email(subject_topic: str, report_body: str):
    token = os.environ.get('MAILTRAP_TOKEN')
    if not token:
        print("❌ CRITICAL: MAILTRAP_TOKEN is completely empty!")
        return {"status": "error", "message": "Missing token"}

    MY_SANDBOX_INBOX_ID = os.environ.get('SANDBOX_ID')
    client = mt.MailtrapClient(token=token, sandbox=True, inbox_id=MY_SANDBOX_INBOX_ID)
    
    mail = mt.Mail(
        sender=mt.Address(email="sales-agent@yourproject.com", name="Sales Agent"),
        to=[mt.Address(email="mickmohit4@gmail.com")],
        subject="Sales Agent Email Update",
        text=report_body,
        category="AI Agent Test"
    )
    
    response = client.send(mail)
    return {"status": "success", "response": str(response)}



# 5. Inject Pydantic Schema directly into the System Instructions
SYSTEM_INSTRUCTIONS = f"""
You are a factual research assistant. You MUST think and communicate EXCLUSIVELY by matching the following JSON structural schema model:

{json.dumps(AgentStateResponse.model_json_schema(), indent=2)}

Rules:
- If you lack current accurate information, you must set "status" to "searching" and fill out the "query" field.
- If you have search data context provided to you, analyze it and write a comprehensive analysis inside the "final_answer" field, setting "status" to "complete".
- Do not include conversational text, markdown strings, or backticks (` ```json `). Output ONLY the raw JSON block.
"""

async def run_search_agent(user_prompt: str):
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": user_prompt}
    ]
    
    for turn in range(3):
        # Request Native JSON block from Groq
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"} 
        )
        
        raw_json_string = response.choices[0].message.content.strip()
        
        try:
            # Force structural verification
            validated_state = AgentStateResponse.model_validate_json(raw_json_string)
            
            if validated_state.status == "searching":
                search_query = validated_state.query
                if not search_query:
                    print("[!] Model requested search but provided an empty query field.")
                    break
                    
                print(f"[*] Executing Pydantic-Validated Search Step for: '{search_query}'...")
                search_data = local_web_search(query=search_query)
                
                messages.append({"role": "assistant", "content": raw_json_string})
                messages.append({
                    "role": "user", 
                    "content": f"Live Tavily web engine findings for execution context:\n\n{search_data}"
                })
                
            elif validated_state.status == "complete":
                print("\n--- AGENT PYDANTIC-VALIDATED SUMMARY ---")
                print(validated_state.final_answer)
                
                # INTEGRATION POINT: Automatically trigger your email function using validated strings
                print("\n[*] Dispatching report data to SendGrid Pipeline...")
                send_research_email(subject_topic=user_prompt, report_body=validated_state.final_answer)
                return
                
        except ValidationError as val_err:
            print(f"[!] Structured validation failed! Schema broke constraint rules: {val_err}")
            return
        except Exception as err:
            print(f"[!] System processing error: {err}")
            return

if __name__ == "__main__":
    message = "Latest AI Agent frameworks in 2026"
    asyncio.run(run_search_agent(message))
