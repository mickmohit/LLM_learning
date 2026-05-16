from dotenv import load_dotenv
import asyncio
import os
from agents import Agent, Runner, trace
from openai import OpenAI
from phoenix.otel import register
from opentelemetry import trace as otel_trace

load_dotenv(override=True)

# Configure Phoenix tracing - disabled for Groq compatibility
# Phoenix tracing with Groq requires custom instrumentation
tracer = None

# Configure OpenAI client to use Groq
groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    # Set environment variables for OpenAI client
    os.environ["OPENAI_API_KEY"] = groq_api_key
    os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
    
    # Suppress all warnings and verbose logging
    import warnings
    import logging
    warnings.filterwarnings("ignore")
    logging.getLogger("openai").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("phoenix").setLevel(logging.CRITICAL)
    logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)
    
    print(f"Groq API key found: {groq_api_key[:10]}...")
else:
    print("Warning: GROQ_API_KEY not found")

agent = Agent(name="My Agent", 
        instructions="You are a helpful assistant",
        model="llama-3.3-70b-versatile")

#print(agent)

@tracer.chain if tracer else (lambda f: f)
async def run_agent(input_text: str) -> str:
    """Run the agent with Phoenix tracing"""
    result = await Runner.run(agent, input_text)
    return str(result)

async def main():
    try:
        result = await run_agent("What is capital of France?")
        # Extract just the final output text
        if hasattr(result, 'final_output'):
            print(result.final_output)
        else:
            print(str(result))
    except Exception as e:
        print(f"Error running agent: {e}")

if __name__ == "__main__":
    asyncio.run(main())