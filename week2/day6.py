from dotenv import load_dotenv
import os
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv(override=True)

app = FastAPI()

# Initialize OpenAI client
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    print("API key loaded successfully")
    openai_client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1/")
else:
    print("API key not found")
    openai_client = None

class Message(BaseModel):
    content: str

@app.get("/")
async def root():
    return {"message": "FastAPI app is running with Groq API"}

@app.post("/chat")
async def chat(message: Message):
    if not openai_client:
        return {"error": "API key not configured"}
    
    messages = [{"role": "user", "content": message.content}]
    
    response = openai_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )
    
    return {"response": response.choices[0].message.content}

# Keep the original functionality for direct execution
if __name__ == "__main__":
    if openai_client:
        messages = [{"role": "user", "content": "What is 5*0"}]
        
        response = openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        
        print(response.choices[0].message.content)
    else:
        print("Cannot run - API key not found")
