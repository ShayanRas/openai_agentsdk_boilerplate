import os
import json
import httpx
import chainlit as cl
from chainlit.input_widget import Select, Switch
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://agent_app:8001")
DEFAULT_HISTORY_MODE = os.getenv("DEFAULT_HISTORY_MODE", "api")

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session with thread management"""
    # For simplicity, use a demo user ID - in production, get from authentication
    user_id = "demo_user"
    
    # Initialize session variables
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("thread_id", None)
    cl.user_session.set("history_mode", DEFAULT_HISTORY_MODE)
    cl.user_session.set("enable_tools", True)
    cl.user_session.set("streaming", True)
    
    # Send welcome message with thread management options
    welcome_actions = [
        cl.Action(name="load_threads", value="load", description="📋 View My Conversations"),
        cl.Action(name="new_thread", value="new", description="🆕 Start New Conversation"),
    ]
    
    await cl.Message(
        content=f"👋 Welcome to MarketGuru 2.0!\n\nI'm your AI assistant with access to various tools:\n- 🔍 Web searches\n- 💻 Code interpretation\n- 🧮 Mathematical calculations\n- 💬 General conversations\n\nChoose an option below or start chatting:",
        actions=welcome_actions
    ).send()
    
    # Load and display user's recent threads
    await load_user_threads()
    
    # Show settings
    settings = await cl.ChatSettings(
        [
            Select(
                id="history_mode",
                label="History Mode",
                values=["api", "local_text", "none"],
                initial_index=0,
                description="How to handle conversation history"
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
        ]
    ).send()

async def load_user_threads():
    """Load and display user's conversation threads"""
    user_id = cl.user_session.get("user_id")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/users/{user_id}/threads")
            response.raise_for_status()
            
            data = response.json()
            threads = data.get("threads", [])
            
            if threads:
                thread_list = "📋 **Your Recent Conversations:**\n\n"
                for i, thread in enumerate(threads[:5]):  # Show last 5 threads
                    thread_type = thread["thread_type"].upper()
                    created_at = thread["created_at"][:10]  # Just the date
                    thread_list += f"**{i+1}.** `{thread['id']}` ({thread_type}) - {created_at}\n"
                
                thread_actions = [
                    cl.Action(name="select_thread", value=thread["id"], description=f"💬 Resume: {thread['id'][:20]}...")
                    for thread in threads[:3]  # Buttons for first 3 threads
                ]
                
                await cl.Message(
                    content=thread_list,
                    actions=thread_actions
                ).send()
            else:
                await cl.Message(
                    content="📝 No previous conversations found. Start chatting to create your first thread!"
                ).send()
                
    except Exception as e:
        print(f"Error loading threads: {e}")
        await cl.Message(
            content="⚠️ Could not load previous conversations. Starting fresh conversation."
        ).send()

@cl.action_callback("load_threads")
async def on_load_threads(action):
    """Handle load threads action"""
    await load_user_threads()
    await action.remove()

@cl.action_callback("new_thread")
async def on_new_thread(action):
    """Handle new thread action"""
    cl.user_session.set("thread_id", None)
    await cl.Message(
        content="🆕 Starting a new conversation thread. Your next message will create a new thread."
    ).send()
    await action.remove()

@cl.action_callback("select_thread")
async def on_select_thread(action):
    """Handle thread selection"""
    thread_id = action.value
    cl.user_session.set("thread_id", thread_id)
    
    # Load thread history if it's a text thread
    await load_thread_history(thread_id)
    
    await cl.Message(
        content=f"📂 Switched to conversation: `{thread_id}`\n\nYou can now continue this conversation."
    ).send()
    await action.remove()

async def load_thread_history(thread_id: str):
    """Load and display thread history"""
    user_id = cl.user_session.get("user_id")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/threads/{thread_id}/history",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            
            data = response.json()
            history_type = data.get("history_type")
            
            if history_type == "text" and data.get("history"):
                # Parse and display text history
                history = data["history"]
                lines = history.strip().split('\n')
                
                current_messages = []
                for line in lines:
                    if line.startswith("User: "):
                        current_messages.append(("user", line[6:]))
                    elif line.startswith("Assistant: "):
                        current_messages.append(("assistant", line[11:]))
                
                # Display last few messages as context
                if current_messages:
                    context = "📚 **Previous conversation context:**\n\n"
                    for role, content in current_messages[-4:]:  # Show last 4 messages
                        if role == "user":
                            context += f"**You:** {content}\n\n"
                        else:
                            context += f"**Assistant:** {content}\n\n"
                    
                    await cl.Message(content=context).send()
            
            elif history_type == "api":
                await cl.Message(
                    content="📚 **API History Mode:** Conversation context will be automatically maintained by OpenAI."
                ).send()
                
    except Exception as e:
        print(f"Error loading thread history: {e}")

@cl.on_settings_update
async def setup_agent(settings):
    """Update settings when changed"""
    cl.user_session.set("history_mode", settings["history_mode"])
    cl.user_session.set("enable_tools", settings["enable_tools"])
    cl.user_session.set("streaming", settings["streaming"])
    
    await cl.Message(
        content=f"✅ Settings updated:\n- History Mode: {settings['history_mode']}\n- Tools: {'Enabled' if settings['enable_tools'] else 'Disabled'}\n- Streaming: {'Enabled' if settings['streaming'] else 'Disabled'}"
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle user messages with thread management"""
    # Get current settings and user info
    user_id = cl.user_session.get("user_id")
    thread_id = cl.user_session.get("thread_id")
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
    
    if thread_id:
        request_data["thread_id"] = thread_id
    
    # Use streaming or non-streaming endpoint
    endpoint = "/invoke_stream" if streaming else "/invoke"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if streaming:
                await handle_streaming_response(client, endpoint, request_data)
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

async def handle_streaming_response(client: httpx.AsyncClient, endpoint: str, request_data: Dict[str, Any]):
    """Handle streaming responses from the API"""
    msg = cl.Message(content="")
    await msg.send()
    
    full_response = ""
    
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
                            # Update thread ID if new thread created
                            thread_id = data["thread_id"]
                            cl.user_session.set("thread_id", thread_id)
                            
                            if data.get("new_thread_created"):
                                thread_actions = [
                                    cl.Action(name="load_threads", value="load", description="📋 View All Threads"),
                                    cl.Action(name="new_thread", value="new", description="🆕 Start Another Thread"),
                                ]
                                
                                await cl.Message(
                                    content=f"🆕 **New conversation started:** `{thread_id}`\n\nThis conversation will be saved and you can return to it later.",
                                    actions=thread_actions
                                ).send()
                        
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
        
        # Update thread ID
        thread_id = result["thread_id"]
        cl.user_session.set("thread_id", thread_id)
        
        await thinking_msg.remove()
        
        # Send the response
        await cl.Message(
            content=result["assistant_output"]
        ).send()
        
        if result.get("new_thread_created"):
            thread_actions = [
                cl.Action(name="load_threads", value="load", description="📋 View All Threads"),
                cl.Action(name="new_thread", value="new", description="🆕 Start Another Thread"),
            ]
            
            await cl.Message(
                content=f"🆕 **New conversation started:** `{thread_id}`",
                actions=thread_actions
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
    thread_id = cl.user_session.get("thread_id")
    user_id = cl.user_session.get("user_id")
    if thread_id:
        print(f"Chat ended. User: {user_id}, Thread: {thread_id}")

@cl.on_chat_resume
async def on_chat_resume(thread: cl.ThreadDict):
    """Resume a previous conversation thread"""
    user_id = cl.user_session.get("user_id") 
    
    # Extract thread_id from Chainlit's thread metadata
    thread_id = thread.get("metadata", {}).get("thread_id")
    
    if thread_id:
        cl.user_session.set("thread_id", thread_id)
        await load_thread_history(thread_id)
        
        await cl.Message(
            content=f"📂 **Resumed conversation:** `{thread_id}`\n\nYou can continue where you left off."
        ).send()
    else:
        await cl.Message(
            content="📂 Welcome back! Starting a fresh conversation."
        ).send()