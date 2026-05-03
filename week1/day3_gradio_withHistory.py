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

# Use Groq API with OpenAI library
client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1/"
)

#gemini_model="gemini-2.5-flash"
groq_model="llama-3.1-8b-instant" 

system_prompt = """
You are helpful assistant for an airline called FlightAI.
Give us short, courteous answers, no more than 1 sentence.
""" 

def chat(message, history):
    
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(
        model=groq_model,
        messages=messages
    )
    return response.choices[0].message.content

try:
   
   gr.ChatInterface(fn=chat).launch()

except Exception as e:
    print(f"Error: {e}")
    print("This approach often fails due to model name incompatibility")
