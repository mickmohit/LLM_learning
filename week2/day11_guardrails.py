import os
import asyncio
import sys
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

# WINDOWS ASYNC LOOP PATCH
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_tracing_disabled,
    GuardrailFunctionOutput,
    input_guardrail
)

load_dotenv(override=True)
set_tracing_disabled(True)

groq_api_key = os.getenv("GROQ_API_KEY")
groq_async_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
set_default_openai_client(groq_async_client)

# Email sending logic from day10_handoffs.py
import mailtrap as mt

def execute_send_email_logic(body: str):
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
        text=body,
        category="AI Agent Test"
    )
    
    response = client.send(mail)
    return {"status": "success", "response": str(response)}

# Sales agents from day10_handoffs.py
instructions1 = "You are a professional sales agent for ComplAI, a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. You write professional, serious cold emails. Use the actual recipient information from the input - do NOT use placeholders like [CEO's Name] or [Company Name]."

instructions2 = "You are a humorous, engaging sales agent for ComplAI, a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. You write witty, engaging cold emails that are likely to get a response. Use the actual recipient information from the input - do NOT use placeholders like [CEO's Name] or [Company Name]."

instructions3 = "You are a busy sales agent for ComplAI, a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. You write concise, to the point cold emails. Use the actual recipient information from the input - do NOT use placeholders like [CEO's Name] or [Company Name]."

# FIX 1: Removed spaces from sub-agent names to align with Groq's functional specifications
sales_agent1 = Agent(name="Professional_Sales_Agent", instructions=instructions1, model="llama-3.1-8b-instant")
sales_agent2 = Agent(name="Engaging_Sales_Agent", instructions=instructions2, model="llama-3.1-8b-instant")
sales_agent3 = Agent(name="Busy_Sales_Agent", instructions=instructions3, model="llama-3.1-8b-instant")

# Tools from day10_handoffs.py - using agents-as-tools for proper handoff support
@function_tool
def send_email(body: str) -> str:
    """Sends the single best cold sales email draft to the user dashboard inbox."""
    cleaned_body = body.replace("\\'", "'").replace('\\"', '"')
    res = execute_send_email_logic(cleaned_body)
    return str(res)

description = "Write a cold sales email"

tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

tools = [tool1, tool2, tool3, send_email]


# Handoff agents from day10_handoffs.py
subject_instructions = "You can write a subject for a cold sales email. You are given a message and you need to write a subject."
html_instructions = """
You convert a plain text email body into a beautifully structured HTML email body.
CRITICAL JSON SAFETY RULE: Use single quotes (') for all internal HTML attributes. Never output raw double quotes (").
"""

subject_writer = Agent(name="Email_Subject_Writer", instructions=subject_instructions, model="llama-3.1-8b-instant")
subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for a cold sales email")

html_converter = Agent(name="HTML_Email_Converter", instructions=html_instructions, model="llama-3.1-8b-instant")
html_tool = html_converter.as_tool(tool_name="html_converter", tool_description="Convert text body to HTML")

@function_tool
def send_html_email(input: str) -> str:
    """Sends the fully formatted HTML email body content using Mailtrap."""
    res = execute_send_email_logic(input)
    return str(res)

tools_handoffs = [subject_tool, html_tool, send_html_email]

sales_manager_instructions = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
 
Follow these steps carefully:
1. Generate Drafts: Use all three sales_agent tools (sales_agent1, sales_agent2, sales_agent3) to generate three unique email drafts. Pass the prompt text exactly as the 'message' argument.
2. Evaluate and Select: Review the drafts and choose the single best email.
3. Handoff for Sending: Pass ONLY the winning email draft text to the 'Email_Manager' agent.
"""

emailer_agent = Agent(
    name="Email_Manager",
    instructions=sales_manager_instructions,
    tools=tools_handoffs,
    model="llama-3.1-8b-instant",
    handoff_description="Convert an email to HTML and send it"
)

class NameCheckOutput(BaseModel):
    is_name_in_message: bool
    name: str

guardrail_agent = Agent(
    name="Name_Check",
    instructions=(
        "You are a strict safety validator. Your ONLY job is to check if a real, individual "
        "person's name (like Alice, Bob, Mohit, John) is present in the message.\n\n"
        "CRITICAL RULES:\n"
        "- Generic business titles like 'CEO', 'Manager', 'CFO', 'VP', 'Director' are NOT names.\n"
        "- Your response MUST be exactly a raw JSON string like this:\n"
        "{\"is_name_in_message\": false, \"name\": \"\"}"
    ),
    model="llama-3.1-8b-instant"
)

@input_guardrail
async def guardrail_against_name(ctx, agent, message):
    input_text = getattr(message, "content", str(message))
    result = await Runner.run(guardrail_agent, input_text, context=ctx.context)
    raw_text = result.final_output
    
    is_name_in_message = False
    try:
        parsed_data = json.loads(raw_text)
        is_name_in_message = parsed_data.get("is_name_in_message", False)
    except Exception:
        cleaned_text = raw_text.upper()
        if '"IS_NAME_IN_MESSAGE": TRUE' in cleaned_text or "REJECT" in cleaned_text:
            is_name_in_message = True

    return GuardrailFunctionOutput(
        output_info={"found_name": raw_text}, 
        tripwire_triggered=is_name_in_message
    )

# FIX 3: Renamed parameter key from 'guardrails' to 'input_guardrails'
careful_sales_manager = Agent(
    name="Careful_Sales_Manager",
    instructions="""
    You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
    
    Follow these steps carefully:
    1. Generate Drafts: Use all three sales_agent tools (sales_agent1, sales_agent2, sales_agent3) to generate three different email drafts. Do not proceed until all three drafts are ready.
    
    2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
    
    3. Handoff for Sending: Pass ONLY the winning email draft to the 'Email_Manager' agent. The Email Manager will take care of formatting and sending.
    
    Crucial Rules:
    - You must use the sales agent tools to generate the drafts — do not write them yourself.
    - You must hand off exactly ONE email to the Email Manager — never more than one.
    """,
    model="llama-3.1-8b-instant",
    input_guardrails=[guardrail_against_name],
    tools=tools,
    handoffs=[emailer_agent]
)

# -------------------------------------------------------------
# RUNNER LOOP CONTROL WITH EXCEPTION HANDLING
# -------------------------------------------------------------
from agents.exceptions import InputGuardrailTripwireTriggered

async def call_agent():
    messgae = "Send cold sales email addressed to Dear CEO"
    
    try:
        print("🚀 Executing agent runner...")
        result = await Runner.run(careful_sales_manager, messgae)
        print("\n✅ Success! Final Response Summary:")
        print(result.final_output)
    except InputGuardrailTripwireTriggered as e:
        print(f"\n🛡️ [GUARDRAIL BLOCK] Detected forbidden context entity footprint.")
    except Exception as general_error:
        print(f"\n❌ Unexpected System Error: {general_error}")

if __name__ == "__main__":
    asyncio.run(call_agent())
