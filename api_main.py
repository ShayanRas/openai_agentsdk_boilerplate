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
from database import db_manager, ensure_db_initialized
from openai_tools import get_all_tools, get_tools_by_type, get_safe_tools

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables.")

# --- Pydantic Models for API --- 
class InvokeRequest(BaseModel):
    user_input: str
    user_id: Optional[str] = None 
    thread_id: Optional[str] = None
    history_mode: str # Expected values: "api", "local_text", "none"
    enable_tools: bool = True  # Enable OpenAI tools
    tool_types: Optional[List[str]] = None  # Optional specific tools

class InvokeResponse(BaseModel):
    assistant_output: str
    thread_id: str
    new_thread_created: bool

# --- Custom Agent Context Definition (Copied from main.py) ---
class AgentCustomContext(BaseModel):
    user_id: Optional[str] = None
    current_thread_id: Optional[str] = None
    session_start_time: Optional[str] = None

# --- History Management Constants ---
EXPIRY_DAYS = 30

# Database-backed history management functions
async def add_response_to_api_thread_history(thread_id: str, response_id: Optional[str]) -> None:
    if not response_id:
        return
    await ensure_db_initialized()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=EXPIRY_DAYS)
    await db_manager.add_api_history_entry(thread_id, response_id, now, expires_at)

async def get_latest_valid_response_id_from_api_thread(thread_id: str) -> Optional[str]:
    await ensure_db_initialized()
    return await db_manager.get_latest_valid_api_response(thread_id)

async def load_local_text_thread_history(thread_id: str) -> str:
    await ensure_db_initialized()
    return await db_manager.get_text_history(thread_id)

async def append_to_local_text_thread_history(thread_id: str, user_input: str, assistant_response: str) -> None:
    await ensure_db_initialized()
    await db_manager.add_text_history_entry(thread_id, user_input, assistant_response)

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

    await ensure_db_initialized()
    
    agent_hooks = CustomAgentHooks(display_name="FastAPI_Agent_NonStream")
    mcp_params = MCPServerStreamableHttpParams(url=MCP_SERVER_URL)
    
    current_thread_id = request.thread_id
    new_thread_created = False
    
    # Determine thread type from existing thread or create new one
    thread_type = None
    if current_thread_id:
        thread_info = await db_manager.get_thread(current_thread_id)
        if thread_info:
            thread_type = thread_info['thread_type']
    
    if not current_thread_id or not thread_info:
        if request.history_mode == "api":
            current_thread_id = f"api_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            thread_type = "api"
        elif request.history_mode == "local_text":
            current_thread_id = f"text_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            thread_type = "text"
        else: # none or other
            current_thread_id = f"temp_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            thread_type = "temp"
        new_thread_created = True
        await db_manager.create_thread(current_thread_id, thread_type, request.user_id)
        print(f"New thread ID created for API request: {current_thread_id}")

    async with MCPServerStreamableHttp(
        params=mcp_params,
        name=f"MCPServerClient_NonStream_{current_thread_id}",
        cache_tools_list=True
    ) as mcp_http_server:

        # Determine which tools to include
        openai_tools = []
        if request.enable_tools:
            if request.tool_types:
                openai_tools = get_tools_by_type(request.tool_types)
            else:
                openai_tools = get_all_tools()  # Use all tools by default

        agent = Agent[AgentCustomContext](
            name="FastAPIAgent",
            model="gpt-4.1", # TODO: Make model configurable
            instructions=main_system_prompt,
            hooks=agent_hooks,
            tools=openai_tools,  # Add OpenAI tools
            mcp_servers=[mcp_http_server]  # Keep existing MCP integration
        )

        custom_context = AgentCustomContext(
            user_id=request.user_id,
            current_thread_id=current_thread_id,
            session_start_time=datetime.now(timezone.utc).isoformat()
        )

        prompt = request.user_input
        kwargs_for_run = {}

        if request.history_mode == "local_text" and current_thread_id:
            local_history_content = await load_local_text_thread_history(current_thread_id)
            if local_history_content:
                prompt = f"{local_history_content.strip()}\n\nUser: {request.user_input}\nAssistant:"
            else:
                prompt = f"User: {request.user_input}\nAssistant:"
            print(f"(API using local text history from thread '{current_thread_id}')")
        elif request.history_mode == "api" and current_thread_id:
            latest_response_id = await get_latest_valid_response_id_from_api_thread(current_thread_id)
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
            await append_to_local_text_thread_history(current_thread_id, request.user_input, assistant_output)
        elif request.history_mode == "api" and current_thread_id and result and result.last_response_id:
            await add_response_to_api_thread_history(current_thread_id, result.last_response_id)
        
        return InvokeResponse(
            assistant_output=assistant_output,
            thread_id=current_thread_id,
            new_thread_created=new_thread_created
        )

@app.post("/invoke_stream")
async def invoke_agent_stream(request: InvokeRequest):
    """
    Streaming endpoint that returns Server-Sent Events (SSE) for real-time agent responses.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured on server.")
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        await ensure_db_initialized()
        
        agent_hooks = CustomAgentHooks(display_name="FastAPI_Agent_Stream")
        mcp_params = MCPServerStreamableHttpParams(url=MCP_SERVER_URL)
        
        current_thread_id = request.thread_id
        new_thread_created = False
        
        # Determine thread type from existing thread or create new one
        thread_type = None
        if current_thread_id:
            thread_info = await db_manager.get_thread(current_thread_id)
            if thread_info:
                thread_type = thread_info['thread_type']
        
        if not current_thread_id or not thread_info:
            if request.history_mode == "api":
                current_thread_id = f"api_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                thread_type = "api"
            elif request.history_mode == "local_text":
                current_thread_id = f"text_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                thread_type = "text"
            else:  # none or other
                current_thread_id = f"temp_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                thread_type = "temp"
            new_thread_created = True
            await db_manager.create_thread(current_thread_id, thread_type, request.user_id)
            print(f"New thread ID created for streaming API request: {current_thread_id}")
        
        # Send initial metadata
        yield f"data: {json.dumps({'type': 'metadata', 'thread_id': current_thread_id, 'new_thread_created': new_thread_created})}\n\n"
        
        try:
            async with MCPServerStreamableHttp(
                params=mcp_params,
                name=f"MCPServerClient_Stream_{current_thread_id}",
                cache_tools_list=True
            ) as mcp_http_server:
                
                # Determine which tools to include for streaming
                openai_tools = []
                if request.enable_tools:
                    if request.tool_types:
                        openai_tools = get_tools_by_type(request.tool_types)
                    else:
                        openai_tools = get_all_tools()  # Use all tools by default

                agent = Agent[AgentCustomContext](
                    name="FastAPIAgent_Stream",
                    model="gpt-4.1",
                    instructions=main_system_prompt,
                    hooks=agent_hooks,
                    tools=openai_tools,  # Add OpenAI tools
                    mcp_servers=[mcp_http_server]  # Keep existing MCP integration
                )
                
                custom_context = AgentCustomContext(
                    user_id=request.user_id,
                    current_thread_id=current_thread_id,
                    session_start_time=datetime.now(timezone.utc).isoformat()
                )
                
                # Prepare prompt and kwargs
                prompt = request.user_input
                kwargs_for_run = {}
                
                if request.history_mode == "local_text" and current_thread_id:
                    local_history_content = await load_local_text_thread_history(current_thread_id)
                    prompt = f"{local_history_content}User: {request.user_input}\nAssistant:"
                    print(f"(Using local text history from thread '{current_thread_id}' for streaming)")
                elif request.history_mode == "api" and current_thread_id:
                    previous_api_id = await get_latest_valid_response_id_from_api_thread(current_thread_id)
                    if previous_api_id:
                        kwargs_for_run["previous_response_id"] = previous_api_id
                        print(f"(Using API history ID: {previous_api_id} from thread '{current_thread_id}' for streaming)")
                    else:
                        print(f"(API history mode for thread '{current_thread_id}', but no valid previous response ID found)")
                
                # Run the agent in streaming mode
                result_stream = Runner.run_streamed(agent, prompt, context=custom_context, **kwargs_for_run)
                
                # Process stream events
                final_output = ""
                last_message_id = None
                
                async for event in result_stream.stream_events():
                    if event.type == "raw_response_event" and hasattr(event, 'data'):
                        if hasattr(event.data, 'type') and event.data.type == "response.output_text.delta":
                            if hasattr(event.data, 'delta') and event.data.delta is not None:
                                final_output += event.data.delta
                                # Send text delta
                                yield f"data: {json.dumps({'type': 'delta', 'content': event.data.delta})}\n\n"
                    
                    elif event.type == "run_item_stream_event" and hasattr(event, 'item'):
                        if hasattr(event.item, 'type') and event.item.type == "message_output_item":
                            current_message_id = getattr(event.item, 'id', getattr(event.item, 'message_id', None))
                            if current_message_id:
                                last_message_id = current_message_id
                                # Send message ID update
                                yield f"data: {json.dumps({'type': 'message_id', 'message_id': current_message_id})}\n\n"
                                print(f"(Stream: Message unit processed, ID: {current_message_id})")
                
                # Handle history updates after stream completion
                if request.history_mode == "local_text" and current_thread_id and final_output:
                    await append_to_local_text_thread_history(current_thread_id, request.user_input, final_output)
                    print(f"(Local text history updated for thread '{current_thread_id}')")
                elif request.history_mode == "api" and current_thread_id:
                    if last_message_id:
                        await add_response_to_api_thread_history(current_thread_id, last_message_id)
                        print(f"(API history updated for thread '{current_thread_id}' with response ID: {last_message_id})")
                    else:
                        # Fallback: try to get response ID from result object
                        fallback_id = getattr(result_stream, 'last_response_id', None)
                        if fallback_id:
                            await add_response_to_api_thread_history(current_thread_id, fallback_id)
                            print(f"(API history updated with fallback response ID: {fallback_id})")
                
                # Send completion event
                yield f"data: {json.dumps({'type': 'done', 'thread_id': current_thread_id, 'final_output': final_output})}\n\n"
                
        except Exception as e:
            print(f"Error during streaming: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Access-Control-Allow-Origin": "*"  # CORS support (adjust as needed)
        }
    )

# Thread management endpoints
@app.get("/users/{user_id}/threads")
async def list_user_threads(user_id: str):
    """Get all threads for a user"""
    await ensure_db_initialized()
    threads = await db_manager.get_user_threads(user_id)
    return {"threads": threads}

@app.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, user_id: str):
    """Get conversation history for a thread"""
    await ensure_db_initialized()
    
    thread = await db_manager.get_thread(thread_id)
    if not thread or thread.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if thread['thread_type'] == 'text':
        history = await db_manager.get_text_history(thread_id)
        return {"thread_id": thread_id, "history_type": "text", "history": history}
    else:
        history = await db_manager.get_api_history(thread_id)
        return {"thread_id": thread_id, "history_type": "api", "history": history}

# Tool management endpoints
@app.get("/tools/available")
async def list_available_tools():
    """List all available OpenAI tools"""
    return {
        "tools": [
            {"name": "web_search", "description": "Search the web for current information"},
            {"name": "file_search", "description": "Search through uploaded documents"},
            {"name": "code_interpreter", "description": "Execute Python code and analysis"},
            {"name": "image_generation", "description": "Generate images from text prompts"},
            {"name": "local_shell", "description": "Execute local shell commands"}
        ],
        "mcp_tools": [
            {"name": "echo", "description": "Echo back messages"},
            {"name": "add", "description": "Add two numbers"},
            {"name": "get_server_time", "description": "Get current server time"}
        ]
    }

@app.post("/invoke_with_tools")
async def invoke_with_specific_tools(request: InvokeRequest):
    """Invoke agent with specific tools enabled - same as /invoke but more explicit"""
    # This endpoint does the same as /invoke but makes tool selection more explicit
    return await invoke_agent(request)

# Lifecycle management for database connections
@app.on_event("startup")
async def startup_event():
    await db_manager.initialize()
    print("Database connection pool initialized")

@app.on_event("shutdown")
async def shutdown_event():
    await db_manager.close()
    print("Database connection pool closed")

# Health check endpoint for Docker
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MarketGuru Agent API"}

if __name__ == "__main__":
    # This part is for direct execution testing, not for uvicorn deployment
    # For uvicorn, run: uvicorn api_main:app --reload
    print("To run this FastAPI application, use: uvicorn api_main:app --reload")
    print("Ensure OPENAI_API_KEY is set in your .env file or environment.")
    print("Ensure DB_URL is set in your .env file or environment.")
    print(f"MCP Server URL is configured as: {MCP_SERVER_URL}")
