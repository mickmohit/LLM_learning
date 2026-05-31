import os
from dotenv import load_dotenv

# =====================================================================
# STEP 1 & 2: CONFIGURE ENVIRONMENT VARIABLES
# =====================================================================
load_dotenv(override=True)

# Purge cloud parameters to ensure local-only processing
if "PHOENIX_API_KEY" in os.environ:
    del os.environ["PHOENIX_API_KEY"]
if "PHOENIX_CLIENT_HEADERS" in os.environ:
    del os.environ["PHOENIX_CLIENT_HEADERS"]

groq_api_key = os.getenv("GROQ_API_KEY")

# =====================================================================
# STEP 3: EXECUTE DEPENDENCY IMPORTS
# =====================================================================
import asyncio
from openai.types.responses import ResponseTextDeltaEvent
from openai import AsyncOpenAI

# OpenTelemetry core libraries
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# CRITICAL FOR PHOENIX: Resource library to map project names
from opentelemetry.sdk.resources import Resource

# Framework packages
from agents import Agent, Runner, set_default_openai_api, set_default_openai_client, set_tracing_disabled

# Completely deactivate the default OpenAI tracking system
set_tracing_disabled(True)

# =====================================================================
# STEP 4: INITIALIZE MANUAL OPENTELEMETRY WITH PROJECT RESOURCE
# =====================================================================
try:
    # FIX: Explicitly bind the project name resource so Phoenix registers it
    resource = Resource.create(attributes={
        "project_name": "sales_agent",       # Tells Phoenix where to route the trace rows
        "service.name": "sales_agent_service"
    })
    
    # Instantiate the provider with our explicit resource block
    tracer_provider = TracerProvider(resource=resource)
    
    # Directly point to the HTTP trace ingestion endpoint
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:6006/v1/traces"
    )
    
    span_processor = SimpleSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    otel_trace.set_tracer_provider(tracer_provider)
    
    # Create the named tracer instance
    tracer = otel_trace.get_tracer("sales_agent_tracer")
    print("Manual OpenTelemetry tracking successfully mapped to local Phoenix database.")
except Exception as e:
    print(f"Failed to initialize manual tracing layout: {e}")
    tracer = None
    tracer_provider = None

# =====================================================================
# STEP 5: RUNNER OVERRIDES FOR GROQ
# =====================================================================
set_default_openai_api("chat_completions")
groq_async_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
set_default_openai_client(groq_async_client)

# =====================================================================
# STEP 6: AGENT DEFINITIONS AND PROMPTS
# =====================================================================
instructions1 = (
    "You are a sales agent working for ComplAI, a company that provides a "
    "SaaS tool for ensuring SOC2 compliance and preparing for audits, "
    "powered by AI. You write professional, serious cold emails."
)

sales_agent_1 = Agent(
    name="Professional Sales Agent", 
    instructions=instructions1,
    model="llama-3.1-8b-instant"
)

instructions2 = (
    "You are a sales agent working for ComplAI, a company that provides a "
    "SaaS tool for ensuring SOC2 compliance and preparing for audits, "
    "powered by AI. You write friendly, conversational cold emails."
)

sales_agent_2 = Agent(
    name="Friendly Sales Agent", 
    instructions=instructions2,
    model="llama-3.1-8b-instant"
)

instructions3 = (
    "You are a sales agent working for ComplAI, a company that provides a "
    "SaaS tool for ensuring SOC2 compliance and preparing for audits, "
    "powered by AI. You write concise, direct cold emails."
)

sales_agent_3 = Agent(
    name="Concise Sales Agent", 
    instructions=instructions3,
    model="llama-3.1-8b-instant"
)

async def sales_main(input_text: str = "Write a cold email to a potential client"):
    if tracer:
        with tracer.start_as_current_span("sales_agent_run") as span:
            # Mandated Semantic attributes required to populate UI columns
            span.set_attribute("openinference.span.kind", "CHAIN")
            span.set_attribute("input.value", input_text)
            span.set_attribute("llm.model_name", sales_agent_1.model)
            span.set_attribute("agent.name", sales_agent_1.name)
            
            # String buffer to capture the streamed output chunks
            full_output_response = ""
            
            result = Runner.run_streamed(sales_agent_1, input=input_text)
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    chunk_text = event.data.delta
                    print(chunk_text, end="", flush=True)
                    if chunk_text:
                        full_output_response += chunk_text
            
            # Flush the completed buffer string to output.value column fields
            span.set_attribute("output.value", full_output_response)
    

async def run_parallel_agents(message: str = "Write a cold sales email to a potential client"):
    if tracer:
        with tracer.start_as_current_span("Parallel Sales Agent") as span:
            span.set_attribute("openinference.span.kind", "CHAIN")
            span.set_attribute("input.value", message)
            
            results = await asyncio.gather(
                Runner.run(sales_agent_1, input=message),
                Runner.run(sales_agent_2, input=message),
                Runner.run(sales_agent_3, input=message)
            )
            
            outputs = [result.final_output for result in results]
            span.set_attribute("output.value", str(outputs))
  
    for output in outputs:
        print(output)
    
    return outputs

instructions4 = "You pick the best cold email from given options. \
    Imagine you are customer and pick the one you most likely to respond to. \
    Reply with the selected email only. Do not give an explanation."

sales_picker = Agent(
     name="sales_picker", 
    instructions=instructions4,
    model="llama-3.1-8b-instant"
)

async def run_parallel_agents_with_picker(message: str = "Write a cold sales email to a potential client"):
    if tracer:
        with tracer.start_as_current_span("Parallel Sales Agent With Sales Picker") as span:
            span.set_attribute("openinference.span.kind", "CHAIN")
            span.set_attribute("input.value", message)
            
            results = await asyncio.gather(
                Runner.run(sales_agent_1, input=message),
                Runner.run(sales_agent_2, input=message),
                Runner.run(sales_agent_3, input=message)
            )
            
            # Track outputs with their agent names
            agents = [sales_agent_1, sales_agent_2, sales_agent_3]
            outputs = [result.final_output for result in results]
            agent_outputs = list(zip(agents, outputs))
            
            emails = "Cold Sales Emails: \n\n".join(outputs)
            best = await Runner.run(sales_picker, input=emails)
            span.set_attribute("output.value", str(outputs))
  
            # Find which agent produced the best email by matching content
            best_output = best.final_output
            best_agent = "Unknown"
            
            for agent, output in agent_outputs:
                if output.strip() == best_output.strip() or best_output.strip() in output.strip():
                    best_agent = agent.name
                    break
            
            print(f"Best Agent: {best_agent}")
            print(f"Best Sales email: \n{best_output}")
    
    return best.final_output


if __name__ == "__main__":
    asyncio.run(run_parallel_agents_with_picker())
    
    # Force the local exporter engine to dispatch data before the script exits
    if tracer_provider:
        tracer_provider.force_flush()
        print("\n\nSpans successfully transmitted to http://localhost:6006.")
