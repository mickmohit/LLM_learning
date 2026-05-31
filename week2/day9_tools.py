import os
import sendgrid
from dotenv import load_dotenv
from sendgrid.helpers.mail import Mail, Email, To, Content

from agents import (
    Agent, 
    Runner, 
    function_tool,
    set_default_openai_api, 
    set_default_openai_client, 
    set_tracing_disabled
)

load_dotenv(override=True)

# =====================================================================
# 1. THE PLAIN PYTHON LOGIC FUNCTION (Perfect for Direct Testing!)
# =====================================================================
def execute_send_email_logic(body: str):
    # Fetch the key from environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    
    # DIAGNOSTIC CHECK: Print key status to the console
    if not api_key:
        print("❌ CRITICAL: SENDGRID_API_KEY is completely empty! Check your .env file.")
    else:
        print(f"Checking API Key extraction: {api_key[:10]}...") # Prints the prefix to check loading

    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    from_email = Email("mickmohit4@gmail.com")
    to_email = To("mickmohit4@gmail.com")
    
    subject = "Sales Agent Email Update"  
    content = Content("text/plain", body)
    
    mail = Mail(from_email=from_email, to_emails=to_email, subject=subject, plain_text_content=content).get()
    response = sg.client.mail.send.post(request_body=mail)
    return {"status": "success", "status_code": response.status_code}


# =====================================================================
# 2. THE AGENT DECORATOR (Exclusively for the AI Runner Engine)
# =====================================================================
@function_tool
def send_email(body: str):
    """
    Sends an automated email update to the team.

    Args:
        body: The text content string to place in the email body.
    """
    # Simply forward the argument context to our untampered backend logic
    return execute_send_email_logic(body)


# =====================================================================
# TESTING AND EXECUTION SETUP
# =====================================================================
if __name__ == "__main__":
    print("Executing local function validation check directly...")
    
    # SUCCESS: Test the raw connection using the plain function name!
    # This completely avoids the locked 'FunctionTool' wrapper constraints.
    # Option 1: Use plain function for direct testing
    test_result = execute_send_email_logic("Test Email from direct code execution")
    
    # Option 2: Access underlying function from tool (if needed)
    #test_result = send_email.fn("Test Email from direct code execution")
    print(test_result)
