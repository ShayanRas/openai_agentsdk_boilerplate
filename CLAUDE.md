# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a multi-modal agentic boilerplate that provides both FastAPI HTTP endpoints and standalone CLI interfaces for OpenAI agent interactions. The system supports multiple conversation history modes and multi-user thread management.

### Core Components

**api_main.py** - FastAPI application providing HTTP endpoints (`/invoke`, `/invoke_stream`) for agent interactions. Supports both synchronous and streaming responses with PostgreSQL-backed conversation history.

**main.py** - Standalone CLI interface for testing agent functionality locally. Provides interactive mode selection for history management and streaming options.

**database.py** - PostgreSQL connection manager with async connection pooling. Handles schema initialization and provides thread/history management methods.

**test_mcp_server.py** - MCP (Model Context Protocol) server providing external tools (echo, add, get_server_time) that agents can invoke.

**instructions.py** - System prompt definitions that inform agents about available MCP tools.

### Conversation History Architecture

The system implements a dual-mode conversation history system:

**API Mode**: Stores OpenAI response IDs with expiry timestamps. Uses OpenAI's `previous_response_id` for efficient conversation chaining without token overhead. Response IDs expire after 30 days.

**Text Mode**: Stores full conversation text and replays as prompt context. More token-intensive but provides complete conversation control.

**Database Schema**:
- `threads` table: User-scoped conversation threads with type classification
- `api_history` table: OpenAI response ID storage with expiry management  
- `text_history` table: Full conversation text with sequence ordering

### Multi-User Thread Management

Threads are associated with optional `user_id` for multi-tenant support. Users can only access their own threads. Thread IDs follow format: `{type}_thread_{timestamp}_{microseconds}`.

API endpoints for thread management:
- `GET /users/{user_id}/threads` - List user's threads
- `GET /threads/{thread_id}/history?user_id={user_id}` - Get thread conversation history

## Development Commands

### Local Development
```bash
# Run CLI interface (interactive mode selection)
python main.py

# Start MCP server (required for agent tools)
python test_mcp_server.py

# Start FastAPI application  
uvicorn api_main:app --reload --port 8001
```

### Docker Development
```bash
# Build and start all services
docker-compose up --build

# Start with orphan cleanup
docker-compose up --build --remove-orphans

# Stop services
docker-compose down
```

The Docker setup runs:
- Agent app on port 8001 (FastAPI)
- MCP server on port 8000 (tool provider)

### Database Operations

The database schema auto-initializes on startup by dropping and recreating tables. This ensures clean schema for fresh deployments.

To migrate existing file-based history:
```bash
python migrate_history_to_db.py
```

## Environment Configuration

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API access
- `DB_URL` - PostgreSQL connection string (defaults to provided Supabase URL)

Optional:
- `HOST`, `PORT` - MCP server configuration
- `LOG_LEVEL` - Logging verbosity

## Request/Response Patterns

### FastAPI Invocation
```json
{
    "user_input": "Your message here",
    "user_id": "optional_user_identifier", 
    "thread_id": "optional_existing_thread",
    "history_mode": "api|local_text|none"
}
```

The system automatically creates new threads when `thread_id` is omitted or invalid. Thread creation is user-scoped when `user_id` is provided.

### MCP Tool Integration

Agents have access to external tools via the MCP server:
- `echo(message: str)` - Message echoing
- `add(a: int, b: int)` - Integer arithmetic  
- `get_server_time()` - Server timestamp

Tools are automatically discovered and available to agents when the MCP server is running.

## Important Implementation Notes

- Database connection pooling is managed automatically with startup/shutdown lifecycle hooks
- Schema initialization drops existing tables for clean deployments (appropriate for boilerplate usage)
- Both streaming and non-streaming agent execution modes are supported
- Thread access control prevents cross-user data access when user_id is specified
- Response ID expiry handling prevents using stale OpenAI conversation references