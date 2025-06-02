import asyncio
import os
import dotenv
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List, Dict

from agents import Agent, Runner, AgentHooks, Tool
from instructions import main_system_prompt

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HISTORY_FILE_NAME = "conversation_history.json"
EXPIRY_DAYS = 30

# --- Conversation History Management --- 
def _get_history_file_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), HISTORY_FILE_NAME)

def load_response_history() -> List[Dict[str, str]]:
    file_path = _get_history_file_path()
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        print(f"Warning: Could not load or parse history file at {file_path}")
        return []

def save_response_history(history: List[Dict[str, str]]) -> None:
    file_path = _get_history_file_path()
    try:
        with open(file_path, "w") as f:
            json.dump(history, f, indent=4)
    except IOError:
        print(f"Error: Could not write to history file: {file_path}")

def add_response_to_history(response_id: Optional[str]) -> None:
    if not response_id:
        return
    history = load_response_history()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=EXPIRY_DAYS)
    new_entry = {
        "id": response_id,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    history.append(new_entry)
    save_response_history(history)

def get_latest_valid_response_id() -> Optional[str]:
    history = load_response_history()
    valid_entries = []
    now = datetime.now(timezone.utc)
    for entry in history:
        try:
            expires_at_dt = datetime.fromisoformat(entry["expires_at"])
            # Ensure datetime is timezone-aware for comparison
            if expires_at_dt.tzinfo is None:
                expires_at_dt = expires_at_dt.replace(tzinfo=timezone.utc)
            
            if expires_at_dt > now:
                created_at_dt = datetime.fromisoformat(entry["created_at"])
                if created_at_dt.tzinfo is None:
                    created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
                valid_entries.append({"id": entry["id"], "created_at_dt": created_at_dt})
        except (KeyError, ValueError):
            print(f"Warning: Skipping malformed history entry: {entry}")
            continue
            
    if not valid_entries:
        return None
    
    valid_entries.sort(key=lambda x: x["created_at_dt"], reverse=True)
    return valid_entries[0]["id"]

# --- Agent Hooks and Main Logic --- 
class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self, context: Any, agent: Agent) -> None:
        self.event_counter += 1
        print(f"\r\n### ({self.display_name}) {self.event_counter}: Agent {agent.name} starting run...")

    async def on_end(self, context: Any, agent: Agent, output: Any) -> None:
        self.event_counter += 1
        print(f"\r\n### ({self.display_name}) {self.event_counter}: Agent {agent.name} finished run.")

    async def on_tool_start(self, context: Any, agent: Agent, tool: Tool, tool_input: Any) -> None:
        self.event_counter += 1
        tool_name = getattr(tool, 'name', 'Unknown Tool')
        print(f"\r\n### ({self.display_name}) {self.event_counter}: Agent {agent.name} starting tool: {tool_name} with input: {tool_input}")

    async def on_tool_end(self, context: Any, agent: Agent, tool: Tool, result: str) -> None:
        self.event_counter += 1
        tool_name = getattr(tool, 'name', 'Unknown Tool')
        print(f"\r\n### ({self.display_name}) {self.event_counter}: Agent {agent.name} finished tool: {tool_name} with result: {result}")

async def main(use_history: bool):
    agent_hooks = CustomAgentHooks(display_name="Boiletplate_Agent_NonStream")
    agent = Agent(
        name="Boiletplate_Agent", model="gpt-4.1",
        instructions=main_system_prompt, hooks=agent_hooks, tools=[]
    )

    print("--- Running Non-Streaming Agent (Call 1) ---")
    result1 = await Runner.run(agent, "my name is Shayan. ok?")
    print("Final Output (Call 1):", result1.final_output)
    add_response_to_history(result1.last_response_id)

    print("\n--- Running Non-Streaming Agent (Call 2) ---")
    kwargs_for_run2 = {}
    if use_history:
        previous_id = get_latest_valid_response_id()
        if previous_id:
            kwargs_for_run2["previous_response_id"] = previous_id
            print(f"(Using conversation history ID: {previous_id} for next call)")
        else:
            print("(No valid conversation history ID found. Starting fresh.)")
    else:
        print("(Not using conversation history for next call)")

    result2 = await Runner.run(agent, "What is my name?", **kwargs_for_run2)
    print("Final Output (Call 2):", result2.final_output)
    add_response_to_history(result2.last_response_id)
    print("--- Non-Streaming Agent Complete ---")

async def main_stream(use_history: bool):
    agent_hooks_stream = CustomAgentHooks(display_name="Boiletplate_Agent_Streamed")
    agent = Agent(
        name="Boiletplate_Agent_Streamed", model="gpt-4.1",
        instructions=main_system_prompt, hooks=agent_hooks_stream, tools=[]
    )

    print("\r\n--- Running First Streamed Agent Call ---")
    result1_stream = Runner.run_streamed(agent, "my name is Shayan, ok?")
    async for event in result1_stream.stream_events():
        if event.type == "raw_response_event" and hasattr(event, 'data') and event.data.type == "response.output_text.delta":
            if hasattr(event.data, 'delta') and event.data.delta:
                print(event.data.delta, end="", flush=True)
        elif event.type == "run_item_stream_event" and hasattr(event, 'item') and event.item.type == "message_output_item":
            print(f"\r\n[Stream Info: Message unit complete]", flush=True)
    add_response_to_history(getattr(result1_stream, 'last_response_id', None))
    print("\r\n--- First Streamed Agent Call Complete ---\r\n")

    print("--- Running Second Streamed Agent Call ---")
    kwargs_for_stream2 = {}
    if use_history:
        previous_id = get_latest_valid_response_id()
        if previous_id:
            kwargs_for_stream2["previous_response_id"] = previous_id
            print(f"(Using conversation history ID: {previous_id} for next streamed call)")
        else:
            print("(No valid conversation history ID found. Starting fresh.)")
    else:
        print("(Not using conversation history for next streamed call)")

    result2_stream = Runner.run_streamed(agent, "what is my name?", **kwargs_for_stream2)
    async for event in result2_stream.stream_events():
        if event.type == "raw_response_event" and hasattr(event, 'data') and event.data.type == "response.output_text.delta":
            if hasattr(event.data, 'delta') and event.data.delta:
                print(event.data.delta, end="", flush=True)
        elif event.type == "run_item_stream_event" and hasattr(event, 'item') and event.item.type == "message_output_item":
            print(f"\r\n[Stream Info: Message unit complete]", flush=True)
    add_response_to_history(getattr(result2_stream, 'last_response_id', None))
    print("\r\n--- Second Streamed Agent Call Complete ---")

if __name__ == "__main__":
    is_stream_input = input("Run in stream mode? (y/n): ").lower()
    use_stream = is_stream_input == 'y'

    use_history_input = input("Use conversation history (previous_response_id)? (y/n): ").lower()
    use_history_flag = use_history_input == 'y'

    if use_stream:
        asyncio.run(main_stream(use_history_flag))
    else:
        asyncio.run(main(use_history_flag))
