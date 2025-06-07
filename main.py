import asyncio
import os
import dotenv
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List, Dict

from agents import Agent, Runner, AgentHooks, Tool, RunContextWrapper # Added RunContextWrapper for potential future use in tools
from pydantic import BaseModel
from instructions import main_system_prompt

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Custom Agent Context Definition ---
class AgentCustomContext(BaseModel):
    user_name: Optional[str] = None
    current_thread_id: Optional[str] = None
    session_start_time: Optional[str] = None
    # Add other relevant fields that need to be shared across turns or agents


API_HISTORY_DIR = "api_history_threads"
TEXT_HISTORY_DIR = "text_history_threads"
EXPIRY_DAYS = 30 # Retained for API history threads

# --- API-based Threaded Conversation History Management --- 
def _get_api_thread_file_path(thread_id: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    thread_dir = os.path.join(base_dir, API_HISTORY_DIR)
    if not os.path.exists(thread_dir):
        os.makedirs(thread_dir)
    return os.path.join(thread_dir, f"{thread_id}.json")

def load_api_thread_history(thread_id: str) -> List[Dict[str, str]]:
    file_path = _get_api_thread_file_path(thread_id)
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        print(f"Warning: Could not load or parse API history file for thread {thread_id} at {file_path}")
        return []

def save_api_thread_history(thread_id: str, history: List[Dict[str, str]]) -> None:
    file_path = _get_api_thread_file_path(thread_id)
    try:
        with open(file_path, "w") as f:
            json.dump(history, f, indent=4)
    except IOError:
        print(f"Error: Could not write to API history file for thread {thread_id}: {file_path}")

def add_response_to_api_thread_history(thread_id: str, response_id: Optional[str]) -> None:
    if not response_id:
        return
    history = load_api_thread_history(thread_id)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=EXPIRY_DAYS)
    new_entry = {
        "id": response_id,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    history.append(new_entry)
    save_api_thread_history(thread_id, history)

def get_latest_valid_response_id_from_api_thread(thread_id: str) -> Optional[str]:
    history = load_api_thread_history(thread_id)
    valid_entries = []
    now = datetime.now(timezone.utc)
    for entry in history:
        try:
            expires_at_dt = datetime.fromisoformat(entry["expires_at"])
            if expires_at_dt.tzinfo is None: expires_at_dt = expires_at_dt.replace(tzinfo=timezone.utc)
            if expires_at_dt > now:
                created_at_dt = datetime.fromisoformat(entry["created_at"])
                if created_at_dt.tzinfo is None: created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
                valid_entries.append({"id": entry["id"], "created_at_dt": created_at_dt})
        except (KeyError, ValueError):
            print(f"Warning: Skipping malformed API history entry in thread {thread_id}: {entry}")
            continue
    if not valid_entries:
        return None
    valid_entries.sort(key=lambda x: x["created_at_dt"], reverse=True)
    return valid_entries[0]["id"]

# --- Local Text-based Threaded Conversation History Management --- 
def _get_local_text_thread_file_path(thread_id: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    thread_dir = os.path.join(base_dir, TEXT_HISTORY_DIR)
    if not os.path.exists(thread_dir):
        os.makedirs(thread_dir)
    return os.path.join(thread_dir, f"{thread_id}.txt")

def load_local_text_thread_history(thread_id: str) -> str:
    file_path = _get_local_text_thread_file_path(thread_id)
    if not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            return f.read()
    except IOError:
        print(f"Warning: Could not load local text history file for thread {thread_id} at {file_path}")
        return ""

def append_to_local_text_thread_history(thread_id: str, user_input: str, assistant_response: str) -> None:
    file_path = _get_local_text_thread_file_path(thread_id)
    try:
        with open(file_path, "a", encoding='utf-8') as f:
            f.write(f"User: {user_input}\nAssistant: {assistant_response}\n\n")
    except IOError:
        print(f"Error: Could not write to local text history file for thread {thread_id}: {file_path}")

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

async def main(history_mode: str, thread_id: Optional[str] = None):
    agent_hooks = CustomAgentHooks(display_name="Boiletplate_Agent_NonStream")
    # Specify the custom context type for the Agent
    agent = Agent[AgentCustomContext](name="Boiletplate_Agent", model="gpt-4.1", instructions=main_system_prompt, hooks=agent_hooks, tools=[])

    # Initialize custom context
    custom_context = AgentCustomContext(
        session_start_time=datetime.now(timezone.utc).isoformat()
    )
    if thread_id:
        custom_context.current_thread_id = thread_id

    # --- Call 1 (Non-Streamed) ---
    print("--- Running Non-Streaming Agent (Call 1) ---")
    user_input_1 = "my name is Shayan. ok?"
    prompt_1 = user_input_1

    if history_mode == "local_text" and thread_id:
        local_history_content = load_local_text_thread_history(thread_id)
        prompt_1 = f"{local_history_content}User: {user_input_1}\nAssistant:"
        print(f"(Using local text history from thread '{thread_id}' for call 1)")
    elif history_mode == "api" and thread_id:
         print(f"(API history mode active for thread '{thread_id}', will apply to next call if applicable)")

    result1 = await Runner.run(agent, prompt_1, context=custom_context) # Pass custom_context
    print("Final Output (Call 1):", result1.final_output)

    if history_mode == "api" and thread_id and result1.last_response_id:
        add_response_to_api_thread_history(thread_id, result1.last_response_id)
    elif history_mode == "local_text" and thread_id and result1.final_output is not None:
        append_to_local_text_thread_history(thread_id, user_input_1, result1.final_output)

    # --- Call 2 (Non-Streamed) ---
    print("\n--- Running Non-Streaming Agent (Call 2) ---")
    user_input_2 = "What is my name?"
    prompt_2 = user_input_2
    kwargs_for_run2 = {}

    if history_mode == "api" and thread_id:
        previous_api_id = get_latest_valid_response_id_from_api_thread(thread_id)
        if previous_api_id:
            kwargs_for_run2["previous_response_id"] = previous_api_id
            print(f"(Using API history ID: {previous_api_id} from thread '{thread_id}' for next call)")
        else:
            print(f"(No valid API history ID found in thread '{thread_id}'. Starting fresh.)")
    elif history_mode == "local_text" and thread_id:
        local_history_content = load_local_text_thread_history(thread_id)
        prompt_2 = f"{local_history_content}User: {user_input_2}\nAssistant:"
        print(f"(Using local text history from thread '{thread_id}' for next call)")
    elif history_mode == "none":
        print("(Not using any conversation history for next call)")

    result2 = await Runner.run(agent, prompt_2, context=custom_context, **kwargs_for_run2) # Pass custom_context
    print("Final Output (Call 2):", result2.final_output)

    if history_mode == "api" and thread_id and result2.last_response_id:
        add_response_to_api_thread_history(thread_id, result2.last_response_id)
    elif history_mode == "local_text" and thread_id and result2.final_output is not None:
        append_to_local_text_thread_history(thread_id, user_input_2, result2.final_output)
    
    print("--- Non-Streaming Agent Complete ---")

async def main_stream(history_mode: str, thread_id: Optional[str] = None):
    agent_hooks_stream = CustomAgentHooks(display_name="Boiletplate_Agent_Streamed")
    # Specify the custom context type for the Agent
    agent = Agent[AgentCustomContext](name="Boiletplate_Agent_Streamed", model="gpt-4.1", instructions=main_system_prompt, hooks=agent_hooks_stream, tools=[])

    # Initialize custom context for streaming
    custom_context_stream = AgentCustomContext(
        session_start_time=datetime.now(timezone.utc).isoformat()
    )
    if thread_id:
        custom_context_stream.current_thread_id = thread_id

    # --- Call 1 (Streamed) ---
    print("\r\n--- Running First Streamed Agent Call ---")
    user_input_stream_1 = "my name is Shayan, ok?"
    prompt_stream_1 = user_input_stream_1
    
    if history_mode == "local_text" and thread_id:
        local_history_content_stream_1 = load_local_text_thread_history(thread_id)
        prompt_stream_1 = f"{local_history_content_stream_1}User: {user_input_stream_1}\nAssistant:"
        print(f"(Using local text history from thread '{thread_id}' for streamed call 1)")
    elif history_mode == "api" and thread_id:
         print(f"(API history mode active for thread '{thread_id}', will apply to next call if applicable)")

    result1_stream = Runner.run_streamed(agent, prompt_stream_1, context=custom_context_stream) # Pass custom_context # previous_response_id not applicable for first call
    assistant_response_stream_1 = ""
    async for event in result1_stream.stream_events():
        if event.type == "raw_response_event" and hasattr(event, 'data') and event.data.type == "response.output_text.delta":
            if hasattr(event.data, 'delta') and event.data.delta: 
                print(event.data.delta, end="", flush=True)
                assistant_response_stream_1 += event.data.delta
        elif event.type == "run_item_stream_event" and hasattr(event, 'item') and event.item.type == "message_output_item":
            print(f"\r\n[Stream Info: Message unit complete]", flush=True)
    
    response1_id = getattr(result1_stream, 'last_response_id', None)
    if history_mode == "api" and thread_id and response1_id:
        add_response_to_api_thread_history(thread_id, response1_id)
    elif history_mode == "local_text" and thread_id:
        append_to_local_text_thread_history(thread_id, user_input_stream_1, assistant_response_stream_1)
    print("\r\n--- First Streamed Agent Call Complete ---\r\n")

    # --- Call 2 (Streamed) ---
    print("--- Running Second Streamed Agent Call ---")
    user_input_stream_2 = "what is my name?"
    prompt_stream_2 = user_input_stream_2
    kwargs_for_stream2 = {}

    if history_mode == "api" and thread_id:
        previous_api_id = get_latest_valid_response_id_from_api_thread(thread_id)
        if previous_api_id:
            kwargs_for_stream2["previous_response_id"] = previous_api_id
            print(f"(Using API history ID: {previous_api_id} from thread '{thread_id}' for next streamed call)")
        else:
            print(f"(No valid API history ID found in thread '{thread_id}'. Starting fresh.)")
    elif history_mode == "local_text" and thread_id:
        local_history_content_stream_2 = load_local_text_thread_history(thread_id)
        prompt_stream_2 = f"{local_history_content_stream_2}User: {user_input_stream_2}\nAssistant:"
        print(f"(Using local text history from thread '{thread_id}' for next streamed call)")
    elif history_mode == "none":
        print("(Not using any conversation history for next streamed call)")

    result2_stream = Runner.run_streamed(agent, prompt_stream_2, context=custom_context_stream, **kwargs_for_stream2) # Pass custom_context
    assistant_response_stream_2 = ""
    async for event in result2_stream.stream_events():
        if event.type == "raw_response_event" and hasattr(event, 'data') and event.data.type == "response.output_text.delta":
            if hasattr(event.data, 'delta') and event.data.delta: 
                print(event.data.delta, end="", flush=True)
                assistant_response_stream_2 += event.data.delta
        elif event.type == "run_item_stream_event" and hasattr(event, 'item') and event.item.type == "message_output_item":
            print(f"\r\n[Stream Info: Message unit complete]", flush=True)

    response2_id = getattr(result2_stream, 'last_response_id', None)
    if history_mode == "api" and thread_id and response2_id:
        add_response_to_api_thread_history(thread_id, response2_id)
    elif history_mode == "local_text" and thread_id:
        append_to_local_text_thread_history(thread_id, user_input_stream_2, assistant_response_stream_2)
    print("\r\n--- Second Streamed Agent Call Complete ---")

if __name__ == "__main__":
    is_stream_input = input("Run in stream mode? (y/n): ").lower()
    use_stream = is_stream_input == 'y'

    print("\nChoose conversation history mode:")
    print("  1: API-based (previous_response_id, threaded, expires in 30 days)")
    print("  2: Local Text (prepended to input, threaded, no expiry)")
    print("  3: None")
    history_mode_choice = input("Enter choice (1, 2, or 3): ").strip()

    chosen_history_mode = "none"
    current_thread_id = None

    if history_mode_choice == '1':
        chosen_history_mode = "api"
        current_thread_id = input(f"Enter API history thread ID (leave blank for new, stored in '{API_HISTORY_DIR}/'): ").strip()
        if not current_thread_id:
            current_thread_id = f"api_thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"New API history thread ID created: {current_thread_id}")
    elif history_mode_choice == '2':
        chosen_history_mode = "local_text"
        current_thread_id = input(f"Enter Local Text history thread ID (leave blank for new, stored in '{TEXT_HISTORY_DIR}/'): ").strip()
        if not current_thread_id: 
            current_thread_id = f"text_thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"New Local Text history thread ID created: {current_thread_id}")
    elif history_mode_choice == '3':
        chosen_history_mode = "none"
    else:
        print("Invalid choice. Defaulting to 'none' history mode.")
        chosen_history_mode = "none"

    print(f"\nRunning with history mode: '{chosen_history_mode}'" + (f" and thread ID: '{current_thread_id}'" if current_thread_id else ""))

    if use_stream:
        asyncio.run(main_stream(history_mode=chosen_history_mode, thread_id=current_thread_id))
    else:
        asyncio.run(main(history_mode=chosen_history_mode, thread_id=current_thread_id))
