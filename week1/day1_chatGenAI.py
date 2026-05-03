import os
import time
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr

load_dotenv(override=True)
api_key = os.getenv('GROQ_API_KEY')

if not api_key:
    print("No API Key")
else:
    print("API Key found")

groq_model="llama-3.1-8b-instant"

# Use Groq API with OpenAI library
client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1/"
)

try:
    response = client.chat.completions.create(
        model=groq_model,  # Groq model
        messages=[
            {"role": "user", "content": "Hello Groq, This is my first message"}
        ]
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
    print("This approach often fails due to model name incompatibility")


system_prompt="""
You are an assitant that analyse content of website
"""

user_promt_prefix="""
What is 2+2?
Please provide the summary
"""


messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_promt_prefix}
]



response = client.chat.completions.create(
    model=groq_model,
    messages=messages
)
print(response.choices[0].message.content)
