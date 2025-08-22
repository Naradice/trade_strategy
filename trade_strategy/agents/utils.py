
import json
import re
import logging

from google.genai import types

logger = logging.getLogger(__name__)

def parse_json_string(json_str):
    match = re.search(r'({.*})', json_str, re.DOTALL)
    if match:
        json_body = match.group(1)
    else:
        json_body = json_str
    try:
        obj = json.loads(json_body)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON string: {e}")
        logger.debug(f"Original string: {json_str}")
        obj = {}
    return obj

async def call_agent_async(query, runner, user_id, session_id):
        content = types.Content(role="user", parts=[types.Part(text=query)])
        responses = None
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
                    responses = [{"author": event.author, "text": part.text.strip()} for part in event.content.parts if part.text and not part.text.isspace()]
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
        return responses