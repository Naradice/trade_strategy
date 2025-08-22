import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm

from . import prompt
from .market_analyst import market_analyst, persist_market_analyst

if "LLM_MODEL" in os.environ:
    model_name = os.environ["LLM_MODEL"]
else:
    model_name = "gemini-2.0-flash"


def signal_refiner_generator(client_tool=None):
    tools = [AgentTool(agent=persist_market_analyst)]
    if client_tool:
        tools.append(client_tool)
    signal_analyst_agent = LlmAgent(
        model=model_name,
        name="signal_analyst_agent",
        instruction=prompt.SIGNAL_ANALYST_PROMPT,
        output_key="signal_analysis_output",
        tools=tools,
    )

    price_refiner_agent = LlmAgent(
        model=model_name,
        name="price_refiner_agent",
        instruction=prompt.ORDER_PRICE_ANALYST,
        output_key="order_price_analysis_output",
        tools=tools,
    )

    root_agent = SequentialAgent(
        name="signal_refiner_agent",
        description="Agent to refine trading signals and order prices",
        sub_agents=[
            signal_analyst_agent,
            price_refiner_agent
        ]
    )
    return root_agent

def trend_analyst_generator(client_tool=None):
    tools = [AgentTool(agent=persist_market_analyst)]
    if client_tool:
        tools.append(client_tool)
    agent = LlmAgent(
        model=model_name,
        name="trend_analyst_agent",
        instruction=prompt.TREND_ANALYST_PROMPT,
        output_key="trend_analysis_output",
        tools=tools,
    )
    return agent