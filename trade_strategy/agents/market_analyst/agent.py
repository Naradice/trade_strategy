import os

from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.models.lite_llm import LiteLlm

from . import prompt, state_manager

if "LLM_MODEL" in os.environ:
    model_name = os.environ["LLM_MODEL"]
else:
    model_name = "gemini-2.0-flash"


report_manager = state_manager.StateManagerMemory()
persist_market_analyst = Agent(
    model=model_name,
    name="market_analyst_agent",
    instruction=prompt.MARKET_ANALYST_PROMPT,
    output_key=state_manager.OUTPUT_KEY,
    tools=[google_search],
    before_agent_callback=report_manager.before_callback,
    after_agent_callback=report_manager.after_callback
)

market_analyst = Agent(
    model=model_name,
    name="market_analyst_agent",
    instruction=prompt.MARKET_ANALYST_PROMPT,
    output_key=state_manager.OUTPUT_KEY,
    tools=[google_search]
)