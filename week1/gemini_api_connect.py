import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)
api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    print("No API Key")
else:
    print("API Key found")

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello Gemini, This is my first message"
)
print(response.text)
