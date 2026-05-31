import os
import mailtrap as mt
from dotenv import load_dotenv
import asyncio
from openai import AsyncOpenAI
import sys
# WINDOWS ASYNC LOOP PATCH:
    # Forces Python on Windows to use the Selector loop policy,
    # preventing the premature connection tear-down and closed event loop crash.
if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
from agents import (
    Agent, 
    Runner, 
    function_tool,
    set_default_openai_client, 
    set_tracing_disabled
)

load_dotenv(override=True)

# Silence tracking to avoid 401 collisions
set_tracing_disabled(True)



def execute_send_email_logic(body: str):
    token = os.environ.get('MAILTRAP_TOKEN')
    
    if not token:
        print("❌ CRITICAL: MAILTRAP_TOKEN is completely empty!")
        return {"status": "error", "message": "Missing token"}
    else:
        print(f"Checking Token extraction: {token[:10]}...") 

    MY_SANDBOX_INBOX_ID = os.environ.get('SANDBOX_ID')
    
    client = mt.MailtrapClient(
        token=token,
        sandbox=True,               
        inbox_id=MY_SANDBOX_INBOX_ID 
    )
    
    mail = mt.Mail(
        sender=mt.Address(email="sales-agent@yourproject.com", name="Sales Agent"),
        to=[mt.Address(email="mickmohit4@gmail.com")],
        subject="Sales Agent Email Update",
        text=body,
        category="AI Agent Test"
    )
    
    response = client.send(mail)
    return {"status": "success", "response": str(response)}


# Step 1: Agent workflows
instructions1 = "You are a sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write professional, serious cold emails."

instructions2 = "You are a humorous, engaging sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write witty, engaging cold emails that are likely to get a response."

instructions3 = "You are a busy sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write concise, to the point cold emails."

groq_api_key = os.getenv("GROQ_API_KEY")

groq_async_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
set_default_openai_client(groq_async_client)


sales_agent1 = Agent(
    name="Professional Sales Agent",
    instructions=instructions1,
    model="llama-3.1-8b-instant"
)

sales_agent2 = Agent(
    name="Engaging Sales Agent",
    instructions=instructions2,
    model="llama-3.1-8b-instant"
)

sales_agent3 = Agent(
    name="Busy Sales Agent",
    instructions=instructions3,
    model="llama-3.1-8b-instant"
)


# Steps 2 and 3: Tools and Agent interactions
@function_tool
def send_email(body: str) -> str:
    """
    Sends the single best cold sales email draft to the user dashboard inbox.
    
    Args:
        body (str): The final selected text content of the email.
    """
    res = execute_send_email_logic(body)
    return str(res)


description = "Write a cold sales email"

#Agents-as-tools 
tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

tools = [tool1, tool2, tool3, send_email]


async def run_sales_parallel_agents_astools(message: str = "Send a cold sales email addressed to 'Dear CEO'"):

    # FIX: Rewrote prompt to be explicit and removed text that tricks Llama into hallucinating tools
    instructions = """
    You are a Sales Manager at ComplAI. Your task is to use the provided tools to send a cold sales email.
    
    You must execute these exact steps in order:
    1. Call 'sales_agent1' to get a professional draft.
    2. Call 'sales_agent2' to get an engaging draft.
    3. Call 'sales_agent3' to get a concise draft.
    4. Internally compare the text of the three drafts you received. 
    5. Choose the single most effective draft from your internal comparison.
    6. Call the 'send_email' tool EXACTLY ONCE, passing the text of the chosen best draft as the 'body' argument.
    
    CRITICAL: Never invent, make up, or hallucinate tool names. You only have access to: sales_agent1, sales_agent2, sales_agent3, and send_email.
    """

    sales_manager = Agent(
        name="Sales Manager", 
        instructions=instructions, 
        tools=tools, 
        model="llama-3.1-8b-instant"
    )

    result = await Runner.run(sales_manager, message)
    return result.final_output


@function_tool
def send_html_email(input: str) -> str:
    """
    Sends the fully formatted HTML email body content using Mailtrap.
    
    Args:
        input (str): The complete HTML formatted string of the email body.
    """
    res = execute_send_email_logic(input)
    return str(res)

#Handoffs represent a way an agent can delegate to an agent, passing control to it
#Handoffs and Agents-as-tools are similar:
#In both cases, an Agent can collaborate with another Agent
#With tools, control passes back
#With handoffs, control passes across


subject_instructions = "You can write a subject for a cold sales email. \
You are given a message and you need to write a subject for an email that is likely to get a response."

html_instructions = """
You convert a plain text email body into a beautifully structured HTML email body.

CRITICAL JSON SAFETY RULE:
- You MUST use single quotes (') for all internal HTML attributes, inline styles, classes, or IDs.
- EXAMPLE: Use <div style='font-family: Arial; color: #333;'> instead of <div style="font-family: Arial; color: #333;">.
- NEVER output raw double quotes (") inside your HTML string, or you will break the system's JSON function calling payload parser.
"""


subject_writer = Agent(name="Email subject writer", instructions=subject_instructions, model="llama-3.1-8b-instant")
subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for a cold sales email")

html_converter = Agent(name="HTML email body converter", instructions=html_instructions, model="llama-3.1-8b-instant")
html_tool = html_converter.as_tool(tool_name="html_converter",tool_description="Convert a text email body to an HTML email body")

tools_handoffs = [subject_tool, html_tool, send_html_email]


sales_manager_instructions = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
 
Follow these steps carefully:
1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do not proceed until all three drafts are ready.
 
2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
 
3. Handoff for Sending: Pass ONLY the winning email draft to the 'Email Manager' agent. The Email Manager will take care of formatting and sending.
 
CRITICAL HTML QUOTE CONSTRAINTS FOR THE EMAIL MANAGER:
- When you use tools to generate HTML styles or parameters, you MUST use single quotes (') for attributes.
- Example: Generate <div style='font-family: Arial;'> instead of <div style="font-family: Arial;">.
- NEVER generate unescaped double quotes inside the parameter payload arguments, as this completely breaks JSON string serialization syntax.

Crucial Rules:
- You must use the sales agent tools to generate the drafts — do not write them yourself.
- You must hand off exactly ONE email to the Email Manager — never more than one.
"""

emailer_agent = Agent(
    name="Email Manager",
    instructions=sales_manager_instructions,
    tools=tools_handoffs,
    model="llama-3.1-8b-instant",
    handoff_description="Convert an email to HTML and send it")

#Now we have 3 tools and 1 handoff
tools_method = [tool1, tool2, tool3]
handoffs = [emailer_agent]
print(tools)
print(handoffs)

async def run_sales_agent_with_handoff(message: str = "Send a cold sales email addressed to 'Dear CEO'"):

    sales_manager_instructions = """
    You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
    
    Follow these steps carefully:
    1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do not proceed until all three drafts are ready.
    
    2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
    You can use the tools multiple times if you're not satisfied with the results from the first try.
    
    3. Handoff for Sending: Pass ONLY the winning email draft to the 'Email Manager' agent. The Email Manager will take care of formatting and sending.
    
    Crucial Rules:
    - You must use the sales agent tools to generate the drafts — do not write them yourself.
    - You must hand off exactly ONE email to the Email Manager — never more than one.
    """


    sales_manager = Agent(
        name="Sales Manager",
        instructions=sales_manager_instructions,
        tools=tools_method,
        handoffs=handoffs,
        model="llama-3.1-8b-instant")

    message = "Send out a cold sales email addressed to Dear CEO from Alice"

    result = await Runner.run(sales_manager, message)
    return result.final_output


if __name__ == "__main__":
    print("Executing local function validation check directly...")

    #Dont run below 2 methods together, it is causing event loop for agents.

    # test_result = asyncio.run(run_sales_parallel_agents_astools())
    # print("\nFinal Returned Result Object(with agent as tools):", test_result)
  
    # Run the handoff version
    test_result_handoff = asyncio.run(run_sales_agent_with_handoff())
    print("\nFinal Returned Result Object (with handoff):", test_result_handoff)

    print("send_email = ", send_email)
