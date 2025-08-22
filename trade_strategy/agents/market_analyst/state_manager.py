import datetime
import logging

from google.adk.agents.callback_context import CallbackContext
from google.genai import types


OUTPUT_KEY = "market_analysis_output"

logger = logging.getLogger(__name__)

class StateManagerMemory:
    def __init__(self):
        self.state = {}

    def save_state(self, key, content):
        self.state[key] = {
            "content": content,
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc)
        }

    def get_state(self, key):
        return self.state.get(key, None)
    
    def get_state_by(self, key, hours_before=1):
        item = self.state.get(key, None)
        if item and item["timestamp"] >= datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=hours_before):
            return item["content"]
        return None
    
    def before_callback(self, callback_context: CallbackContext):
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        logger.debug(f"\n[Callback] Exiting agent: {agent_name} (Inv: {invocation_id})")
        id = callback_context._invocation_context.session.id
        report = self.get_state_by(id)
        if report:
            logger.debug(f"[Callback] Found report in memory for {id} of {agent_name}")
            # Return Content to skip the agent's run
            return types.Content(
                parts=[types.Part(text=report)],
                role="model" # Assign model role to the overriding response
            )
        else:
            return None
        
    def after_callback(self, callback_context: CallbackContext):
        agent_name = callback_context.agent_name
        current_state = callback_context.state.to_dict()
        if current_state.get(OUTPUT_KEY, False):
            key = callback_context._invocation_context.session.id
            self.save_state(key, current_state[OUTPUT_KEY])
            logger.debug(f"[Callback] Report saved: {agent_name} for {key}")
            return None
        else:
            logger.debug(f"[Callback] State condition not met: End agent without saving the response")
            # Return None - the agent's output produced just before this callback will be used.
            return None