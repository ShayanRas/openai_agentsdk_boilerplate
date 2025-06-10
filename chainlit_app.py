import os
import json
import httpx
import chainlit as cl
from chainlit.input_widget import Select, Switch
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import asyncio
from mcp import ClientSession
import openai

load_dotenv()

# Initialize OpenAI client for direct mode
openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://agent_app:8001")
DEFAULT_HISTORY_MODE = os.getenv("DEFAULT_HISTORY_MODE", "local_text")

# OpenAI Agent tools for direct mode (same as in openai_tools.py)
OPENAI_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information and news",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "code_interpreter",
            "description": "Execute Python code for calculations, data analysis, and problem solving",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        }
    }
]

# System prompt for direct mode (from instructions.py)
AGENT_INSTRUCTIONS = """
You are an advanced AI assistant powered by OpenAI Agents SDK with access to multiple tools and capabilities.

Core Capabilities:
- Web search for current information and market data
- Code interpretation for calculations and analysis  
- MCP server tools for specialized functions
- Mathematical calculations and data processing

Guidelines:
- Always use tools when they can provide better, more current, or more accurate information
- For market data, news, or current events, use web search
- For calculations, data analysis, or code execution, use code interpreter
- For specialized functions, use available MCP tools
- Be thorough and analytical in your responses
- Provide sources when using web search results
"""

# Authentication callback for thread persistence
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Authentication - accept any username/password for demo purposes"""
    if username and password:
        return cl.User(
            identifier=username,
            metadata={"username": username, "role": "user"}
        )
    return None

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session"""
    # Get authenticated user
    user = cl.user_session.get("user")
    user_id = user.identifier if user else "demo_user"
    
    # Initialize session variables
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("backend_thread_id", None)
    cl.user_session.set("history_mode", DEFAULT_HISTORY_MODE)
    cl.user_session.set("enable_tools", True)
    cl.user_session.set("streaming", True)
    cl.user_session.set("agent_mode", "backend")  # New: backend vs direct
    cl.user_session.set("mcp_tools", {})  # Store MCP tools from connections
    cl.user_session.set("chat_messages", [])
    
    # Send welcome message
    await cl.Message(
        content="👋 Welcome to OpenAI Agents SDK Boilerplate! I'm your AI assistant with access to various tools:\n\n- 🔍 Web searches\n- 💻 Code interpretation and analysis\n- 🧮 Mathematical calculations\n- 💬 General conversations\n\n**💾 Full Conversation Memory Enabled** - I'll remember our entire conversation history!\n\nStart chatting! Your conversations will appear in the sidebar."
    ).send()
    
    # Show settings
    settings = await cl.ChatSettings([
        Select(
            id="agent_mode",
            label="Agent Mode",
            values=["backend", "direct"],
            initial_index=0,
            description="backend: FastAPI + Agents SDK (full features) | direct: Chainlit native + MCP integration"
        ),
        Select(
            id="history_mode",
            label="History Mode",
            values=["local_text", "api", "none"],
            initial_index=0,
            description="local_text: Full conversation memory (default) | api: OpenAI threading | none: No memory"
        ),
        Switch(
            id="enable_tools",
            label="Enable Tools",
            initial=True,
            description="Enable AI tools (web search, code interpreter, etc.)"
        ),
        Switch(
            id="streaming",
            label="Streaming Responses",
            initial=True,
            description="Stream responses in real-time"
        )
    ]).send()

@cl.on_settings_update
async def setup_agent(settings):
    """Update settings when changed"""
    cl.user_session.set("agent_mode", settings["agent_mode"])
    cl.user_session.set("history_mode", settings["history_mode"])
    cl.user_session.set("enable_tools", settings["enable_tools"])
    cl.user_session.set("streaming", settings["streaming"])
    
    mode_desc = {
        "backend": "FastAPI + OpenAI Agents SDK (full backend features)",
        "direct": "Chainlit native with MCP integration"
    }
    
    memory_desc = {
        "local_text": "Full conversation memory (saves everything to database)",
        "api": "OpenAI threading (token-efficient)",
        "none": "No memory (fresh conversation each time)"
    }
    
    await cl.Message(
        content=f"✅ Settings updated:\n- Agent Mode: **{settings['agent_mode']}** - {mode_desc.get(settings['agent_mode'], settings['agent_mode'])}\n- History Mode: **{settings['history_mode']}** - {memory_desc.get(settings['history_mode'], settings['history_mode'])}\n- Tools: {'Enabled' if settings['enable_tools'] else 'Disabled'}\n- Streaming: {'Enabled' if settings['streaming'] else 'Disabled'}"
    ).send()

# MCP Integration for Direct Mode
@cl.on_mcp_connect
async def on_mcp_connect(connection, session: ClientSession):
    """Called when an MCP connection is established"""
    result = await session.list_tools()
    tools = [{
        "name": t.name,
        "description": t.description,
        "input_schema": t.inputSchema,
    } for t in result.tools]
    
    # Store tools in session
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = tools
    cl.user_session.set("mcp_tools", mcp_tools)
    
    await cl.Message(
        content=f"🔌 **MCP Connected**: {connection.name}\n📋 **Available Tools**: {', '.join([t['name'] for t in tools])}"
    ).send()

@cl.on_mcp_disconnect  
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Called when an MCP connection is terminated"""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    if name in mcp_tools:
        del mcp_tools[name]
        cl.user_session.set("mcp_tools", mcp_tools)
    
    await cl.Message(
        content=f"🔌 **MCP Disconnected**: {name}"
    ).send()

@cl.step(type="tool")
async def call_mcp_tool(tool_use):
    """Execute MCP tools in direct mode"""
    tool_name = tool_use.name
    tool_input = tool_use.input
    
    current_step = cl.context.current_step
    current_step.name = tool_name
    
    # Find which MCP connection has this tool
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_name = None
    
    for connection_name, tools in mcp_tools.items():
        if any(tool.get("name") == tool_name for tool in tools):
            mcp_name = connection_name
            break
    
    if not mcp_name:
        current_step.output = json.dumps({"error": f"Tool {tool_name} not found in any MCP connection"})
        return current_step.output
    
    mcp_session, _ = cl.context.session.mcp_sessions.get(mcp_name)
    
    if not mcp_session:
        current_step.output = json.dumps({"error": f"MCP {mcp_name} session not found"})
        return current_step.output
    
    try:
        current_step.output = await mcp_session.call_tool(tool_name, tool_input)
    except Exception as e:
        current_step.output = json.dumps({"error": str(e)})
    
    return current_step.output

@cl.on_message
async def on_message(message: cl.Message):
    """Handle user messages - route between backend and direct modes"""
    agent_mode = cl.user_session.get("agent_mode", "backend")
    
    if agent_mode == "backend":
        await handle_backend_mode(message)
    else:  # direct mode
        await handle_direct_mode(message)

async def handle_backend_mode(message: cl.Message):
    """Handle messages using the existing FastAPI backend"""
    # Get current settings and user info
    user_id = cl.user_session.get("user_id")
    backend_thread_id = cl.user_session.get("backend_thread_id")
    history_mode = cl.user_session.get("history_mode", DEFAULT_HISTORY_MODE)
    enable_tools = cl.user_session.get("enable_tools", True)
    streaming = cl.user_session.get("streaming", True)
    
    # Create request payload with user context
    request_data = {
        "user_input": message.content,
        "user_id": user_id,
        "history_mode": history_mode,
        "enable_tools": enable_tools
    }
    
    # Use existing backend thread if available
    if backend_thread_id:
        request_data["thread_id"] = backend_thread_id
    
    # Use streaming or non-streaming endpoint
    endpoint = "/invoke_stream" if streaming else "/invoke"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if streaming:
                await handle_streaming_response(client, endpoint, request_data, message)
            else:
                await handle_non_streaming_response(client, endpoint, request_data)
                
    except httpx.ReadTimeout:
        await cl.Message(
            content="⏱️ Request timed out. Please try again with a simpler query."
        ).send()
    except Exception as e:
        await cl.Message(
            content=f"❌ An error occurred: {str(e)}"
        ).send()

async def handle_direct_mode(message: cl.Message):
    """Handle messages using direct OpenAI API + Chainlit MCP"""
    chat_messages = cl.user_session.get("chat_messages", [])
    enable_tools = cl.user_session.get("enable_tools", True)
    
    # Add user message to history
    chat_messages.append({"role": "user", "content": message.content})
    
    # Combine OpenAI Agent tools with MCP tools
    all_tools = []
    if enable_tools:
        # Add OpenAI Agent tools (web search, code interpreter, etc.)
        all_tools.extend(OPENAI_AGENT_TOOLS)
        
        # Add MCP tools
        mcp_tools = cl.user_session.get("mcp_tools", {})
        for connection_tools in mcp_tools.values():
            for tool in connection_tools:
                # Convert MCP tool format to OpenAI format
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }
                }
                all_tools.append(openai_tool)
    
    # Call OpenAI with combined tools
    msg = cl.Message(content="")
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "system", "content": AGENT_INSTRUCTIONS}] + chat_messages,
            tools=all_tools if all_tools else None,
            stream=True
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                await msg.stream_token(chunk.choices[0].delta.content)
        
        await msg.send()
        
        # Add assistant response to history
        chat_messages.append({"role": "assistant", "content": msg.content})
        cl.user_session.set("chat_messages", chat_messages)
        
    except Exception as e:
        await cl.Message(
            content=f"❌ Direct mode error: {str(e)}"
        ).send()

async def handle_streaming_response(client: httpx.AsyncClient, endpoint: str, request_data: Dict[str, Any], user_message: cl.Message):
    """Handle streaming responses from the API"""
    msg = cl.Message(content="")
    await msg.send()
    
    full_response = ""
    backend_thread_id = None
    
    try:
        async with client.stream(
            "POST",
            f"{API_BASE_URL}{endpoint}",
            json=request_data,
            headers={"Accept": "text/event-stream"}
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data["type"] == "metadata":
                            # Store backend thread ID for future requests
                            backend_thread_id = data["thread_id"]
                            cl.user_session.set("backend_thread_id", backend_thread_id)
                            
                            if data.get("new_thread_created"):
                                # This message will be associated with the new Chainlit thread
                                # The thread will automatically appear in the sidebar
                                pass
                        
                        elif data["type"] == "delta":
                            content = data.get("content", "")
                            full_response += content
                            await msg.stream_token(content)
                        
                        elif data["type"] == "message_id":
                            print(f"Message ID: {data['message_id']}")
                        
                        elif data["type"] == "done":
                            await msg.update()
                        
                        elif data["type"] == "error":
                            await cl.Message(
                                content=f"❌ Error: {data['content']}"
                            ).send()
                            
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        await cl.Message(
            content=f"❌ Streaming error: {str(e)}"
        ).send()

async def handle_non_streaming_response(client: httpx.AsyncClient, endpoint: str, request_data: Dict[str, Any]):
    """Handle non-streaming responses from the API"""
    thinking_msg = cl.Message(content="🤔 Thinking...")
    await thinking_msg.send()
    
    try:
        response = await client.post(
            f"{API_BASE_URL}{endpoint}",
            json=request_data
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Store backend thread ID
        backend_thread_id = result["thread_id"]
        cl.user_session.set("backend_thread_id", backend_thread_id)
        
        await thinking_msg.remove()
        
        # Send the response
        await cl.Message(
            content=result["assistant_output"]
        ).send()
            
    except Exception as e:
        await thinking_msg.remove()
        await cl.Message(
            content=f"❌ Request error: {str(e)}"
        ).send()

@cl.on_stop
async def on_stop():
    """Handle when user stops generation"""
    await cl.Message(
        content="⏹️ Generation stopped by user."
    ).send()

@cl.on_chat_end
async def on_chat_end():
    """Clean up when chat ends"""
    backend_thread_id = cl.user_session.get("backend_thread_id")
    user_id = cl.user_session.get("user_id")
    if backend_thread_id:
        print(f"Chat ended. User: {user_id}, Backend Thread: {backend_thread_id}")

@cl.on_chat_resume
async def on_chat_resume(thread: Dict):
    """Resume a previous conversation thread"""
    user_id = cl.user_session.get("user_id", "demo_user")
    cl.user_session.set("user_id", user_id)
    
    # Clear backend thread ID so it starts fresh or gets linked
    cl.user_session.set("backend_thread_id", None)
    
    # Get thread metadata
    thread_id = thread.get("id")
    thread_name = thread.get("name", "Conversation")
    
    # Welcome back message
    await cl.Message(
        content=f"📂 Resumed conversation: **{thread_name}**\n\nAll your previous messages are shown above. Continue the conversation!"
    ).send()

if __name__ == "__main__":
    pass