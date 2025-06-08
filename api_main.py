import asyncio
import os
import dotenv
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List, Dict, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import Agent, Runner, AgentHooks, Tool # RunContextWrapper removed as it wasn't used
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from instructions import main_system_prompt

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables.")

# --- Pydantic Models for API --- 
class InvokeRequest(BaseModel):
    user_input: str
    thread_id: Optional[str] = None
    history_mode: str # Expected values: "api", "local_text", "none"
    user_name: Optional[str] = None # Optional user name for context

class InvokeResponse(BaseModel):
    assistant_output: str
    thread_id: str
    new_thread_created: bool

# --- Custom Agent Context Definition (Copied from main.py) ---
class AgentCustomContext(BaseModel):
    user_name: Optional[str] = None
    current_thread_id: Optional[str] = None
    session_start_time: Optional[str] = None

# --- History Management Constants and Functions (Copied from main.py) ---
API_HISTORY_DIR = "api_history_threads"
TEXT_HISTORY_DIR = "text_history_threads"
EXPIRY_DAYS = 30

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

# --- Agent Hooks (Copied from main.py) ---
class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self, context: Any, agent: Agent) -> None:
        self.event_counter += 1
        print(f"### (API-{self.display_name}) {self.event_counter}: Agent {agent.name} starting run...")

    async def on_end(self, context: Any, agent: Agent, output: Any) -> None:
        self.event_counter += 1
        print(f"### (API-{self.display_name}) {self.event_counter}: Agent {agent.name} finished run.")

    async def on_tool_start(self, context: Any, agent: Agent, tool: Tool) -> None:
        self.event_counter += 1
        tool_name = getattr(tool, 'name', 'Unknown Tool')
        print(f"### (API-{self.display_name}) {self.event_counter}: Agent {agent.name} starting tool: {tool_name}")

    async def on_tool_end(self, context: Any, agent: Agent, tool: Tool, result: str) -> None:
        self.event_counter += 1
        tool_name = getattr(tool, 'name', 'Unknown Tool')
        print(f"### (API-{self.display_name}) {self.event_counter}: Agent {agent.name} finished tool: {tool_name} with result: {result}")

# --- FastAPI App Setup ---
app = FastAPI()

# TODO: Make MCP server URL configurable
MCP_SERVER_URL = "http://mcp_server:8000/mcp"  # Updated for Docker Compose service name

@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured on server.")

    agent_hooks = CustomAgentHooks(display_name="FastAPI_Agent_NonStream")
    mcp_params = MCPServerStreamableHttpParams(url=MCP_SERVER_URL)
    
    current_thread_id = request.thread_id
    new_thread_created = False
    if not current_thread_id:
        if request.history_mode == "api":
            current_thread_id = f"api_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        elif request.history_mode == "local_text":
            current_thread_id = f"text_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        else: # none or other
            current_thread_id = f"temp_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}" # Still need an ID for context
        new_thread_created = True
        print(f"New thread ID created for API request: {current_thread_id}")

    async with MCPServerStreamableHttp(
        params=mcp_params,
        name=f"MCPServerClient_NonStream_{current_thread_id}",
        cache_tools_list=True
    ) as mcp_http_server:

        agent = Agent[AgentCustomContext](
            name="FastAPIAgent",
            model="gpt-4.1", # TODO: Make model configurable
            instructions=main_system_prompt,
            hooks=agent_hooks,
            tools=[],
            mcp_servers=[mcp_http_server]
        )

        custom_context = AgentCustomContext(
            user_name=request.user_name,
            current_thread_id=current_thread_id,
            session_start_time=datetime.now(timezone.utc).isoformat()
        )

        prompt = request.user_input
        kwargs_for_run = {}

        if request.history_mode == "local_text" and current_thread_id:
            local_history_content = load_local_text_thread_history(current_thread_id)
            if local_history_content:
                prompt = f"{local_history_content.strip()}\n\nUser: {request.user_input}\nAssistant:"
            else:
                prompt = f"User: {request.user_input}\nAssistant:"
            print(f"(API using local text history from thread '{current_thread_id}')")
        elif request.history_mode == "api" and current_thread_id:
            latest_response_id = get_latest_valid_response_id_from_api_thread(current_thread_id)
            if latest_response_id:
                kwargs_for_run['previous_response_id'] = latest_response_id
                print(f"(API using API history from thread '{current_thread_id}', prev_resp_id: {latest_response_id})")
            else:
                print(f"(API history mode for thread '{current_thread_id}', but no valid previous response ID found)")
        
        try:
            result = await Runner.run(agent, prompt, context=custom_context, **kwargs_for_run)
        except Exception as e:
            print(f"Error during Runner.run: {e}")
            raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}")

        assistant_output = result.final_output if result else "Error: No output from agent."

        if request.history_mode == "local_text" and current_thread_id:
            append_to_local_text_thread_history(current_thread_id, request.user_input, assistant_output)
        elif request.history_mode == "api" and current_thread_id and result and result.last_response_id:
            add_response_to_api_thread_history(current_thread_id, result.last_response_id)
        
        return InvokeResponse(
            assistant_output=assistant_output,
            thread_id=current_thread_id,
            new_thread_created=new_thread_created
        )

# Placeholder for streaming endpoint - to be implemented next
# @app.post("/invoke_stream")
# async def invoke_agent_stream(request: InvokeRequest):
#     # ... implementation for streaming ...
#     pass

if __name__ == "__main__":
    # This part is for direct execution testing, not for uvicorn deployment
    # For uvicorn, run: uvicorn api_main:app --reload
    print("To run this FastAPI application, use: uvicorn api_main:app --reload")
    print("Ensure OPENAI_API_KEY is set in your .env file or environment.")
    print(f"MCP Server URL is configured as: {MCP_SERVER_URL}")
