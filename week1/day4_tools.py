import os
import time
import json
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

groq_model="llama-3.1-8b-instant"  # Current supported Groq model

system_prompt = """
You are helpful assistant for an airline called FlightAI.
Give us short, courteous answers, no more than 1 sentence.

IMPORTANT: You only have access to ONE tool: get_ticket_price. Use this tool ONLY when asked about ticket prices for cities like London, Paris, or Berlin. Do NOT attempt to use any other tools or functions.

When asked about ticket prices, call the get_ticket_price function with the city name as the parameter.
""" 

ticket_prices = {"london": 200, "paris": 150, "berlin": 100}

def get_ticket_price(city):
    city_lower = city.lower()
    price = ticket_prices.get(city_lower, "City not found")
    return f"The ticket price for {city.title()} is {price}"

#Tool to get ticket price
#dictionary structure to describe function
price_function = {
    "name": "get_ticket_price",
    "description": "Get the ticket price for a given city",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The city to get the ticket price for"
            }
        },
        "required": ["city"],
        "additionalProperties": False
    }
}

# and include above function defination in list of tools
tools = [{"type": "function", "function": price_function}]

def chat(message, history):
    
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(
        model=groq_model,
        messages=messages,
        tools=tools
    )
    
    if response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        tool_responses = handle_tool_calls(message)
        messages.append(message)
        
        # Handle multiple tool responses
        if tool_responses:
            if isinstance(tool_responses, list):
                messages.extend(tool_responses)
            else:
                messages.append(tool_responses)
        
        response = client.chat.completions.create(
            model=groq_model,
            messages=messages,
            tools=tools
        )
        return response.choices[0].message.content

    return response.choices[0].message.content

def handle_tool_calls(message):
    responses = []
    print(f"Processing {len(message.tool_calls)} tool calls")
    
    for tool_call in message.tool_calls:
        print(f"Tool call: {tool_call.function.name}")
        if tool_call.function.name == "get_ticket_price":
            arguments = json.loads(tool_call.function.arguments)
            city = arguments["city"]
            print(f"Getting price for: {city}")
            price_details = get_ticket_price(city)
            response = {"role": "tool", "content": price_details, "tool_call_id": tool_call.id}
            responses.append(response)
    
    print(f"Returning {len(responses)} responses")
    # Return all responses (or None if no tool calls matched)
    return responses if responses else None

try:
   
   gr.ChatInterface(fn=chat).launch()

except Exception as e:
    print(f"Error: {e}")
    print("This approach often fails due to model name incompatibility")
