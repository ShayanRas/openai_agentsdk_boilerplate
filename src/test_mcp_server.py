import os
import logging
import contextlib
from collections.abc import AsyncIterator
import datetime

import mcp.types as types
from mcp.server.lowlevel import Server as LowLevelMCPAPIServer # Renamed to avoid conflict
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.streamable_http import EventStore, EventCallback, EventId, EventMessage, StreamId # For InMemoryEventStore base types
from mcp.types import JSONRPCMessage # For InMemoryEventStore

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import uvicorn

# --- Environment Variables ---
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Logging Configuration ---
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Simple In-Memory Event Store (from example, for resumability if needed) ---
from collections import deque
from dataclasses import dataclass
from uuid import uuid4

@dataclass
class EventEntry:
    event_id: EventId
    stream_id: StreamId
    message: JSONRPCMessage

class InMemoryEventStore(EventStore):
    def __init__(self, max_events_per_stream: int = 100):
        self.max_events_per_stream = max_events_per_stream
        self.streams: dict[StreamId, deque[EventEntry]] = {}
        self.event_index: dict[EventId, EventEntry] = {}

    async def store_event(
        self, stream_id: StreamId, message: JSONRPCMessage
    ) -> EventId:
        event_id = str(uuid4())
        event_entry = EventEntry(
            event_id=event_id, stream_id=stream_id, message=message
        )
        if stream_id not in self.streams:
            self.streams[stream_id] = deque(maxlen=self.max_events_per_stream)
        if len(self.streams[stream_id]) == self.max_events_per_stream:
            oldest_event = self.streams[stream_id][0]
            self.event_index.pop(oldest_event.event_id, None)
        self.streams[stream_id].append(event_entry)
        self.event_index[event_id] = event_entry
        return event_id

    async def replay_events_after(
        self,
        last_event_id: EventId,
        send_callback: EventCallback,
    ) -> StreamId | None:
        if last_event_id not in self.event_index:
            logger.warning(f"Event ID {last_event_id} not found in store")
            return None
        last_event = self.event_index[last_event_id]
        stream_id = last_event.stream_id
        stream_events = self.streams.get(last_event.stream_id, deque())
        found_last = False
        for event in stream_events:
            if found_last:
                await send_callback(EventMessage(event.message, event.event_id))
            elif event.event_id == last_event_id:
                found_last = True
        return stream_id

# --- MCP Application Setup ---
mcp_app = LowLevelMCPAPIServer("MyLowLevelTestServer")

@mcp_app.list_tools()
async def list_tools() -> list[types.Tool]:
    logger.info("list_tools called")
    return [
        types.Tool(
            name="echo",
            description="Echoes the input message back to the caller.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to echo."}
                },
                "required": ["message"],
            },
        ),
        types.Tool(
            name="add",
            description="Adds two integers and returns the result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "The first number."},
                    "b": {"type": "integer", "description": "The second number."},
                },
                "required": ["a", "b"],
            },
        ),
        types.Tool(
            name="get_server_time",
            description="Returns the current server time as an ISO 8601 string.",
            inputSchema={"type": "object", "properties": {}}, # No input properties
        ),
    ]

@mcp_app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[
    types.TextContent
    | types.ImageContent
    # | types.AudioContent # Temporarily removed due to AttributeError
    | types.EmbeddedResource
]:
    ctx = mcp_app.request_context # Get context for sending logs, etc.
    logger.info(f"call_tool called for tool: '{name}' with arguments: {arguments}")
    
    # Send a log message associated with this request
    await ctx.session.send_log_message(
        level="info",
        data=f"Executing tool '{name}'",
        logger="tool_executor",
        related_request_id=ctx.request_id,
    )

    if name == "echo":
        message = arguments.get("message", "No message provided")
        logger.info(f"Tool 'echo' implementation: echoing '{message}'")
        return [types.TextContent(type="text", text=f"Echo: {message}")]
    elif name == "add":
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        result = a + b
        logger.info(f"Tool 'add' implementation: {a} + {b} = {result}")
        return [types.TextContent(type="text", text=str(result))]
    elif name == "get_server_time":
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        logger.info(f"Tool 'get_server_time' implementation: returning {now}")
        return [types.TextContent(type="text", text=now)]
    else:
        logger.error(f"Unknown tool called: {name}")
        # It's good practice to return an error structure if the MCP spec defines one
        # For now, returning an empty list or a text error
        return [types.TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

# --- ASGI Application Setup ---
event_store = InMemoryEventStore()
session_manager = StreamableHTTPSessionManager(
    app=mcp_app,
    event_store=event_store, # Enable resumability
    json_response=False, # Use SSE by default
)

async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    await session_manager.handle_request(scope, receive, send)

async def health_check(request):
    """Health check endpoint for Render"""
    return JSONResponse({"status": "healthy", "service": "MCP Server"})

@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    print("🚀 [MCP-SERVER] Starting up...")
    print(f"🔧 [MCP-SERVER] Server Host: {SERVER_HOST}")
    print(f"🔧 [MCP-SERVER] Server Port: {SERVER_PORT}")
    print(f"🔧 [MCP-SERVER] Log Level: {LOG_LEVEL}")
    
    try:
        async with session_manager.run():
            print("✅ [MCP-SERVER] StreamableHTTPSessionManager initialized successfully")
            print(f"✅ [MCP-SERVER] Available tools: echo, add, get_server_time")
            print(f"🌐 [MCP-SERVER] Health check available at: http://{SERVER_HOST}:{SERVER_PORT}/health")
            print(f"🌐 [MCP-SERVER] MCP endpoint available at: http://{SERVER_HOST}:{SERVER_PORT}/mcp")
            print(f"🎉 [MCP-SERVER] Startup complete! Ready to handle MCP requests")
            try:
                yield
            finally:
                print("🛑 [MCP-SERVER] Shutting down...")
                print("👋 [MCP-SERVER] Shutdown complete!")
    except Exception as e:
        print(f"❌ [MCP-SERVER] Startup failed: {e}")
        raise

starlette_app = Starlette(
    debug=LOG_LEVEL == "DEBUG", # Set Starlette debug mode based on log level
    routes=[
        Route("/health", health_check),
        Mount("/mcp", app=handle_streamable_http),
    ],
    lifespan=lifespan,
)

# Add CORS middleware
starlette_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    logger.info(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(
        starlette_app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level=LOG_LEVEL.lower() # Uvicorn uses lowercase log levels
    )