import asyncio
import os
import sys
import unittest

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
import dotenv
BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
dotenv.load_dotenv(f"{BASE_PATH}/tests/.env")

# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
# for trade_strategy
module_path = os.path.abspath(BASE_PATH)
sys.path.append(module_path)
from finance_client import CSVClient, AgentTool
from trade_strategy.agents import agent, utils

data_folder = os.environ["ts_data_folder"]
file_path = os.path.join(data_folder, "yfinance_1333.T_D1.csv")

client = CSVClient(files=file_path, auto_step_index=True, start_index=300)
client_tool = AgentTool(client)

async def _call_agent_async(query, runner, user_id, session_id):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    final_response = None
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content,
    ):
        if event.is_final_response():
            if (
                event.content
                and event.content.parts
                and event.content.parts[0].text
            ):
                # print("DEBUG: Final response received")
                # for part in event.content.parts:
                #     if part.text and not part.text.isspace():
                #         print(f"  Text: '{part.text.strip()}'")
                final_response = [{"author": event.author, "text": part.text.strip()} for part in event.content.parts if part.text and not part.text.isspace()]
        elif event.content and event.content.parts:
            # debug
            for part in event.content.parts:  # Iterate through all parts
                if part.executable_code:
                    # Access the actual code string via .code
                    print(
                        f"  Debug: Agent generated code:\n```python\n{part.executable_code.code}\n```"
                    )
                    has_specific_part = True
                elif part.code_execution_result:
                    # Access outcome and output correctly
                    print(
                        f"  Debug: Code Execution Result: {part.code_execution_result.outcome} - Output:\n{part.code_execution_result.output}"
                    )
                    has_specific_part = True
                # Also print any text parts found in any event for debugging
                elif part.text and not part.text.isspace():
                    print(f"  Text: '{part.text.strip()}'")
    return final_response

class AgentTest(unittest.TestCase):
    SYMBOL = "1333.T"

    def test_trend_analyst(self):
        session_service = InMemorySessionService()
        asyncio.run(session_service.create_session(app_name="Trend", user_id="system", session_id="test_session"))
        root_agent = agent.trend_analyst_generator(client_tool.get_ohlc_with_indicators)
        trend_runner = Runner(app_name="Trend", agent=root_agent, session_service=session_service)
        responses = asyncio.run(_call_agent_async(query=f"Analyze the trend of {self.SYMBOL} for daily trade based on market analysis", runner=trend_runner, user_id="system", session_id="test_session"))
        self.assertIsNotNone(responses)
        self.assertGreater(len(responses), 0)
        for response in responses:
            self.assertIn("author", response)
            self.assertIn("text", response)
            # print(f"Trend analysis response: {response}")
        trend_response = responses[-1]["text"]
        trend_json = utils.parse_json_string(trend_response)
        self.assertIsNotNone(trend_json)
        self.assertIn("trend", trend_json)
        self.assertIn("strength", trend_json)

    def test_signal_refiner(self):
        session_service = InMemorySessionService()
        asyncio.run(session_service.create_session(app_name="Signal", user_id="system", session_id="test_session"))
        root_agent = agent.signal_refiner_generator(client_tool.get_ohlc_with_indicators)
        signal_runner = Runner(app_name="Signal", agent=root_agent, session_service=session_service)
        responses = asyncio.run(_call_agent_async(query=f"Refine the trading signal for daily trading for {self.SYMBOL} based on market analysis.\n Signal: Buy", runner=signal_runner, user_id="system", session_id="test_session"))
        self.assertIsNotNone(responses)
        self.assertGreater(len(responses), 0)
        for response in responses:
            self.assertIn("author", response)
            self.assertIn("text", response)
            print(f"Signal refinement response: {response}")
        signal_response = responses[-1]["text"]
        signal_json = utils.parse_json_string(signal_response)
        self.assertIsNotNone(signal_json)
        self.assertIn("signal", signal_json)
        self.assertGreater(len(signal_json["signal"]), 0)

if __name__ == "__main__":
    unittest.main()