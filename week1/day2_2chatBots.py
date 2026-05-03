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

groq_model="llama-3.1-8b-instant"
groq_polite_model="llama-3.1-8b-instant"  # Using same model with different prompt

groq_argumentative_prompt="You are an assistant who is very argumentative; you disagree with everything and provide counter arguments."

groq_polite_prompt="You are an assistant who is very polite, courteous and respectful; you agree with everything and provide supportive arguments or find common ground and try to calm them down and keep chatting."

gpt_messages = ["Hi there"]
claude_messages = ["Hi"]

def call_gpt():
    messages = [{"role": "system", "content": groq_argumentative_prompt}]
    for gpt, claude in zip(gpt_messages, claude_messages):
        messages.append({"role": "user", "content": gpt})
        messages.append({"role": "assistant", "content": claude})
    response = client.chat.completions.create(
        model=groq_model,
        messages=messages
    )
    return response.choices[0].message.content

def call_claude():
    messages = [{"role": "system", "content": groq_polite_prompt}]
    for gpt, claude in zip(gpt_messages, claude_messages):
        messages.append({"role": "user", "content": gpt})
        messages.append({"role": "assistant", "content": claude})
    response = client.chat.completions.create(
        model=groq_polite_model,
        messages=messages
    )
    return response.choices[0].message.content

try:
    for i in range(1):
        print(f"\n--- Round {i+1} ---")
        
        gpt_next = call_gpt()
        print(f"### Argumentative Gemini:\n{gpt_next}\n")
        gpt_messages.append(gpt_next)
        
        time.sleep(15)  # Wait to avoid rate limits
        claude_next = call_claude()
        print(f"### Polite Gemini:\n{claude_next}\n")
        claude_messages.append(claude_next)

except Exception as e:
    print(f"Error: {e}")
    print("This approach often fails due to model name incompatibility")
