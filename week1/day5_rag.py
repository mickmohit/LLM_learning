import os
import glob
from dotenv import load_dotenv
from pathlib import Path
import gradio as gr
from openai import OpenAI


load_dotenv(override=True)
api_key = os.getenv('GROQ_API_KEY')

if not api_key:
    print("No API Key")
else:
    print("API Key found")


knowledge = {}

filenames = glob.glob("week1/data/*")

for filename in filenames:
    # Extract name without extension
    name = Path(filename).stem
    with open(filename, 'r', encoding='utf-8') as file:
        knowledge[name.lower()] = file.read()

# print(knowledge)
print(knowledge.keys())

system_prefix = """
You represent Insurellm, Insurance Tech Company.
You are expert on answering insurellm question and its employee and its products.
Give brief answers.

Relevant Context:
"""

# def get_relevant_context(query):
#     text = ''.join(ch for ch in query if ch.isalpha() or ch.isspace())
#     words = text.lower().split()
#     relevant_context = []
#     for word in words:
#         if word in knowledge:
#             relevant_context.append(knowledge[word])
#     return '\n'.join(relevant_context)

def get_relevant_context(query):
    text = ''.join(ch for ch in query if ch.isalpha() or ch.isspace())
    words = text.lower().split()
    relevant_context = []
    
    # Search within each knowledge file content
    for key, content in knowledge.items():
        content_lower = content.lower()
        for word in words:
            if word in content_lower:
                # Extract relevant section around the match
                lines = content.split('\n')
                for line in lines:
                    # Only add line if it contains the exact word as a standalone word
                    line_words = line.lower().split()
                    if word in line_words:
                        relevant_context.append(line.strip())
                        break  # Only add first matching line per file
    
    return '\n'.join(relevant_context) if relevant_context else "No relevant information found."

get_relevant_context("who is smith")

print(get_relevant_context("who is smith"))
