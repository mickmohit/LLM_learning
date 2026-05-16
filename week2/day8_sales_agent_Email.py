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
    else:
        # Fallback if tracer fails to boot
        result = Runner.run_streamed(sales_agent_1, input=input_text)
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(sales_main())
    
    # Force the local exporter engine to dispatch data before the script exits
    if tracer_provider:
        tracer_provider.force_flush()
        print("\n\nSpans successfully transmitted to http://localhost:6006.")
