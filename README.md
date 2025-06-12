# OpenAI Agents SDK Boilerplate

> **A production-ready, multi-modal agentic AI boilerplate with OpenAI Agents SDK, Chainlit UI, and Model Context Protocol (MCP) integration.**

Created by **Shayan Rastgou**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-Agents%20SDK-green.svg)](https://github.com/openai/agents-sdk)
[![Chainlit](https://img.shields.io/badge/Chainlit-UI-orange.svg)](https://chainlit.io)
[![MCP](https://img.shields.io/badge/MCP-Integrated-purple.svg)](https://modelcontextprotocol.io)

## 🚀 Quick Start

**Get up and running in 3 minutes:**

```bash
# 1. Clone and setup
git clone https://github.com/your-username/openai-agentsdk-boilerplate.git
cd openai-agentsdk-boilerplate

# 2. Configure environment
cp .env.example .env
# Edit .env with your OpenAI API key

# 3. Launch with Docker
docker-compose up --build
```

**Access your AI assistant:**
- 🌐 **Chainlit UI**: http://localhost:8002 *(Recommended)*
- 🔧 **API Endpoints**: http://localhost:8001
- 🛠️ **MCP Tools**: http://localhost:8000

## Features Overview

### Core Capabilities
- **OpenAI Agents SDK** - Production-grade agent execution
- **Chainlit Web UI** - Beautiful, interactive chat interface
- **Web Search** - Real-time information retrieval
- **Code Interpreter** - Python execution and analysis
- **MCP Tools** - Extensible external tool integration
- **Multi-modal Support** - Text, images, and file uploads
- **Persistent Memory** - Three conversation history modes
- **Streaming Responses** - Real-time token-by-token output
- **Multi-user Support** - User-scoped conversations
- **Docker Ready** - One-command deployment

### Advanced Features
- **Dual Agent Modes**: Backend (full SDK) vs Direct (Chainlit native)
- **Flexible History**: API mode, local text, or stateless
- **MCP Protocol**: Both SSE and stdio transport support
- **Tool Management**: Selective tool enabling and filtering
- **Database Persistence**: PostgreSQL with async connection pooling
- **Authentication**: User session management
- **Health Monitoring**: Built-in health checks and logging

---

## 🏗️ Architecture

### Service Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chainlit UI   │    │  FastAPI Agent  │    │   MCP Server    │
│   (Port 8002)   │◄──►│   (Port 8001)   │◄──►│   (Port 8000)   │
│                 │    │                 │    │                 │
│ • Web Interface │    │ • Agent Engine  │    │ • Custom Tools  │
│ • User Auth     │    │ • OpenAI SDK    │    │ • Tool Provider │
│ • Thread Mgmt   │    │ • Conversation  │    │ • MCP Protocol  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (Port 5432)   │
                    │                 │
                    │ • Conversations │
                    │ • User Data     │
                    │ • Thread Mgmt   │
                    └─────────────────┘
```

### Core Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Chainlit UI** | Interactive web interface with chat, settings, and thread management | Python + Chainlit + React |
| **FastAPI Agent** | Core agent execution engine with OpenAI Agents SDK | FastAPI + OpenAI SDK + Async |
| **MCP Server** | External tool provider using Model Context Protocol | FastMCP + Custom Tools |
| **PostgreSQL** | Persistent storage for conversations and user data | PostgreSQL 15 + AsyncPG |

---

## 🚀 Getting Started

### Prerequisites
- **Docker & Docker Compose** (Recommended)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **Git** for cloning the repository

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/openai-agentsdk-boilerplate.git
   cd openai-agentsdk-boilerplate
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your settings:
   ```bash
   # Required: Add your OpenAI API key
   OPENAI_API_KEY=sk-your-key-here
   
   # Database (use defaults or customize)
   POSTGRES_DB=chainlit_db
   POSTGRES_USER=chainlit_user
   POSTGRES_PASSWORD=your_secure_password_here
   
   # Optional: Customize other settings
   DEFAULT_HISTORY_MODE=local_text
   CHAINLIT_AUTH_SECRET=your_super_secret_jwt_key
   ```

3. **Launch the application:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - **Chainlit UI**: http://localhost:8002
   - **FastAPI Docs**: http://localhost:8001/docs
   - **MCP Server**: http://localhost:8000

### Option 2: Local Development

<details>
<summary>Click to expand local development setup</summary>

1. **Prerequisites:**
   ```bash
   # Python 3.11+
   python --version
   
   # Node.js 18+ (for MCP Everything server)
   node --version
   
   # PostgreSQL (local installation)
   psql --version
   ```

2. **Install dependencies:**
   ```bash
   # Core dependencies
   pip install -r requirements.txt
   
   # Chainlit dependencies
   pip install -r requirements.chainlit.txt
   
   # MCP dependencies
   pip install -r requirements.mcp.txt
   
   # Install MCP Everything server
   npm install -g @modelcontextprotocol/server-everything
   ```

3. **Setup database:**
   ```bash
   # Create database
   createdb chainlit_db
   
   # Run initialization
   python init_db.py
   ```

4. **Run services:**
   ```bash
   # Terminal 1: MCP Server
   python test_mcp_server.py
   
   # Terminal 2: FastAPI Agent
   uvicorn api_main:app --reload --port 8001
   
   # Terminal 3: Chainlit UI
   chainlit run chainlit_app.py --port 8002
   ```

</details>

---

## 📖 Usage Guide

### Authentication & Setup

1. **First Access:**
   - Navigate to http://localhost:8002
   - Enter any username/password (demo mode)
   - Your conversations will be saved under your username

2. **Agent Mode Selection:**
   - **Backend Mode** *(Default)*: Full OpenAI Agents SDK with all features
   - **Direct Mode**: Chainlit native with MCP integration

3. **History Mode:**
   - **local_text** *(Recommended)*: Full conversation memory
   - **api**: OpenAI's native threading (30-day expiry)
   - **none**: Stateless conversations

### File Upload & Analysis

1. **Upload files** using the attachment button
2. **Ask questions** about the content
3. **Get AI analysis** with code execution if needed

---

## 🎨 Chainlit UI vs API Endpoints

### Chainlit UI (Port 8002) - **Recommended for Users**

#### **Advantages:**
- ✅ **Beautiful Interface** - Professional chat UI with thread management
- ✅ **Real-time Streaming** - Token-by-token response rendering
- ✅ **File Uploads** - Drag & drop support for documents and images
- ✅ **Thread Persistence** - Conversation history in sidebar
- ✅ **Settings Panel** - Dynamic configuration without restarts
- ✅ **Authentication** - User session management
- ✅ **Tool Visualization** - Step-by-step tool execution display
- ✅ **MCP Integration** - Direct connection to MCP servers

#### **Features:**
```typescript
• Dual Agent Modes (Backend/Direct)
• Three History Modes (local_text/api/none)
• Tool Selection (web_search, code_interpreter, MCP)
• Streaming Controls (enable/disable)
• User Authentication
• Thread Management
• File Upload Support
• Settings Persistence
```

#### **Best For:**
- End users and demos
- Interactive conversations
- File analysis workflows
- Development and testing
- Production user interfaces

### API Endpoints (Port 8001) - **For Developers**

#### **Advantages:**
- ✅ **Programmatic Access** - REST API for integrations
- ✅ **Flexible Integration** - Embed in any application
- ✅ **Batch Processing** - Multiple requests programmatically
- ✅ **Custom UI** - Build your own interface
- ✅ **Webhook Support** - Server-to-server communication
- ✅ **Performance** - Lower overhead for automation

#### **Available Endpoints:**

##### **Core Agent Endpoints:**
```http
POST /invoke
Content-Type: application/json

{
  "user_input": "What's the weather like?",
  "user_id": "user_123",
  "thread_id": "local_text_thread_20241209_123456",
  "history_mode": "local_text",
  "enable_tools": true,
  "tool_types": ["web_search"]
}
```

##### **Streaming Endpoint:**
```http
POST /invoke_stream
Accept: text/event-stream

# Returns Server-Sent Events stream
data: {"type": "token", "content": "The"}
data: {"type": "token", "content": " weather"}
data: {"type": "tool_start", "tool": "web_search"}
data: {"type": "tool_result", "result": "..."}
data: {"type": "done", "thread_id": "..."}
```

##### **Thread Management:**
```http
GET /users/{user_id}/threads
GET /threads/{thread_id}/history?user_id={user_id}
```

##### **Tool Information:**
```http
GET /tools/available
GET /health
```

#### **Best For:**
- Custom integrations
- Mobile app backends
- Automated workflows
- Third-party applications
- Microservice architectures

---

## 💾 History Management

### Three History Modes

#### 1. **local_text** *(Recommended)*
```yaml
Storage: PostgreSQL database
Memory: Complete conversation history
Tokens: Higher usage (full context replay)
Persistence: Permanent until manually deleted
Best For: Production, important conversations
```

**How it works:**
- Stores every message in `agent.text_history` table
- Replays entire conversation as prompt context
- Maintains perfect conversation continuity
- Survives server restarts and deployments

#### 2. **api** *(Token Efficient)*
```yaml
Storage: OpenAI's servers + response ID tracking
Memory: OpenAI's native conversation threading
Tokens: Lower usage (OpenAI manages context)
Persistence: 30 days (OpenAI's limitation)
Best For: Cost optimization, temporary conversations
```

**How it works:**
- Uses OpenAI's `previous_response_id` for threading
- Stores only response IDs in `agent.api_history` table
- Automatic cleanup of expired response IDs
- Relies on OpenAI's conversation memory

#### 3. **none** *(Stateless)*
```yaml
Storage: No persistence
Memory: Single conversation only
Tokens: Lowest usage (no context)
Persistence: Lost after each message
Reliability: N/A - no memory
Best For: One-off questions, testing
```

**How it works:**
- Each message is independent
- No conversation history maintained
- Fresh context for every interaction
- Minimal resource usage

### Database Schema

```sql
-- Thread management (all modes)
CREATE TABLE agent.threads (
    id VARCHAR PRIMARY KEY,
    thread_type VARCHAR NOT NULL,
    user_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API mode: Response ID tracking
CREATE TABLE agent.api_history (
    thread_id VARCHAR REFERENCES agent.threads(id),
    response_id VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- local_text mode: Full conversation storage
CREATE TABLE agent.text_history (
    thread_id VARCHAR REFERENCES agent.threads(id),
    user_input TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```


## 🔗 MCP Integration

### What is MCP?

The **Model Context Protocol (MCP)** is an open standard that enables AI assistants to securely connect to external data sources and tools. Think of it as a universal plugin system for AI agents.

### MCP in This Boilerplate

#### **Built-in MCP Server** (Port 8000)
```python
# Available tools:
echo(message: str)           # Message echoing for testing
add(a: int, b: int)          # Integer arithmetic
get_server_time()           # Server timestamp
```

#### **MCP Everything Server** (Built into Chainlit)
```bash
# Provides 15+ tools including:
• File system operations (read, write, list)
• Git operations (status, diff, log)
• Database queries (SQLite)
• Text processing
• And more...
```

### Using MCP Tools

#### **In Backend Mode:**
MCP tools are automatically available alongside OpenAI tools:

```python
# Your agent has access to:
• web_search()         # OpenAI tool
• code_interpreter()   # OpenAI tool  
• echo()              # MCP tool
• add()               # MCP tool
• get_server_time()   # MCP tool
```

#### **In Direct Mode:**
Connect to MCP servers via the UI:

1. **Open Chainlit UI** settings panel
2. **Add MCP Server**:
   - URL: `http://mcp_server:8000/mcp/`
   - Transport: SSE
3. **Tools are automatically discovered** and available

#### **Adding Custom MCP Servers:**

##### **SSE Transport (HTTP):**
```toml
# .chainlit/config.toml
[[features.mcp.servers]]
name = "my_server"
transport = "sse"
url = "https://my-mcp-server.com/mcp"
```

##### **Stdio Transport (Local Command):**
```toml
[[features.mcp.servers]]
name = "custom_tool"
command = "python"
args = ["my_mcp_server.py"]
```

### MCP Server Development

Create your own MCP server:

```python
# my_mcp_server.py
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Custom Server")

@mcp.tool()
def my_custom_tool(input_text: str) -> str:
    """A custom tool that processes text."""
    return f"Processed: {input_text.upper()}"

if __name__ == "__main__":
    mcp.run()
```


### Project Structure

```
openai-agentsdk-boilerplate/
├── 🐳 Docker Configuration
│   ├── docker-compose.yml          # Multi-service orchestration
│   ├── Dockerfile.agent            # FastAPI agent container
│   ├── Dockerfile.chainlit         # Chainlit UI container
│   └── Dockerfile.mcp              # MCP server container
│
├── 🤖 Core Application
│   ├── api_main.py                 # FastAPI endpoints
│   ├── chainlit_app.py             # Chainlit UI application
│   ├── database.py                 # PostgreSQL connection manager
│   ├── instructions.py             # System prompts
│   └── openai_tools.py             # Tool definitions
│
├── 🔧 MCP Integration
│   ├── test_mcp_server.py          # Custom MCP server
│   └── requirements.mcp.txt        # MCP dependencies
│
├── 🗄️ Database
│   ├── schema.prisma               # Chainlit database schema
│   └── init_db.py                  # Database initialization
│
├── ⚙️ Configuration
│   ├── .env.example                # Environment template
│   ├── .chainlit/config.toml       # Chainlit configuration
│   ├── requirements.txt            # Core dependencies
│   ├── requirements.chainlit.txt   # UI dependencies
│   └── CLAUDE.md                   # Development notes
│
└── 📚 Documentation
    └── README.md                   # This file
```

### Adding New Tools

#### **1. OpenAI Agent Tools:**

```python
# openai_tools.py
from openai import AsyncOpenAI

def get_my_custom_tool():
    return {
        "type": "function",
        "function": {
            "name": "my_tool",
            "description": "My custom tool description",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Input parameter"}
                },
                "required": ["input"]
            }
        }
    }

# Add to get_all_tools() function
```

#### **2. MCP Tools:**

```python
# test_mcp_server.py or new file
@mcp.tool()
def my_mcp_tool(param: str) -> str:
    """My custom MCP tool."""
    # Implementation here
    return result
```

### Environment Configuration

```bash
# .env file - Complete configuration

# === REQUIRED ===
OPENAI_API_KEY=sk-your-openai-api-key-here

# === DATABASE ===
POSTGRES_DB=chainlit_db
POSTGRES_USER=chainlit_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# === CONSTRUCTED URLs (don't modify) ===
DB_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# === CHAINLIT ===
DEFAULT_HISTORY_MODE=local_text              # local_text|api|none
CHAINLIT_AUTH_SECRET=your_jwt_secret_here     # Change in production
API_BASE_URL=http://agent_app:8001            # Internal service URL

# === OPTIONAL ===
VECTOR_STORE_ID=default_store                 # For file search (if enabled)
HOST=0.0.0.0                                  # MCP server host
PORT=8000                                     # MCP server port
LOG_LEVEL=INFO                                # DEBUG|INFO|WARNING|ERROR
```

### Development Workflow

1. **Make code changes** in your editor
2. **Services auto-reload** (via volume mounts)
3. **Test in browser** at http://localhost:8002
4. **Check logs** with `docker-compose logs -f service_name`
5. **Debug API** at http://localhost:8001/docs

### Debugging

#### **View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f chainlit_ui
docker-compose logs -f agent_app
docker-compose logs -f mcp_server
docker-compose logs -f postgres
```

#### **Enter containers:**
```bash
# Chainlit UI container
docker-compose exec chainlit_ui bash

# Agent app container
docker-compose exec agent_app bash

# Database
docker-compose exec postgres psql -U chainlit_user -d chainlit_db
```

#### **Reset database:**
```bash
docker-compose down -v  # Removes volumes
docker-compose up --build
```

---

## 🚀 Deployment

### Production Deployment

#### **Option 1: Docker Compose (Simple)**

1. **Prepare production environment:**
   ```bash
   # Clone on production server
   git clone https://github.com/your-username/openai-agentsdk-boilerplate.git
   cd openai-agentsdk-boilerplate
   
   # Create production .env
   cp .env.example .env
   # Edit with production values
   ```

2. **Production environment variables:**
   ```bash
   # .env - Production settings
   OPENAI_API_KEY=sk-prod-key-here
   
   # Use strong passwords
   POSTGRES_PASSWORD=very_secure_production_password
   CHAINLIT_AUTH_SECRET=cryptographically_secure_jwt_secret
   
   # Production database (optional: use managed PostgreSQL)
   DB_URL=postgresql://user:pass@your-prod-db:5432/db
   
   # Security
   LOG_LEVEL=WARNING
   ```

3. **Deploy:**
   ```bash
   docker-compose -f docker-compose.yml up -d --build
   ```

#### **Option 2: Kubernetes (Scalable)**

<details>
<summary>Click to expand Kubernetes deployment guide</summary>

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openai-agentsdk-boilerplate
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openai-agentsdk-boilerplate
  template:
    metadata:
      labels:
        app: openai-agentsdk-boilerplate
    spec:
      containers:
      - name: chainlit-ui
        image: your-registry/openai-agentsdk-chainlit:latest
        ports:
        - containerPort: 8002
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
      # Add other containers...
```

Deploy:
```bash
kubectl apply -f k8s-deployment.yaml
```

</details>

### Environment-Specific Configurations

#### **Development:**
```yaml
# docker-compose.override.yml
services:
  chainlit_ui:
    environment:
      - LOG_LEVEL=DEBUG
    volumes:
      - ./chainlit_app.py:/app/chainlit_app.py  # Live reload
```

#### **Staging:**
```yaml
services:
  chainlit_ui:
    environment:
      - LOG_LEVEL=INFO
      - CHAINLIT_AUTH_SECRET=${STAGING_JWT_SECRET}
```

#### **Production:**
```yaml
services:
  chainlit_ui:
    environment:
      - LOG_LEVEL=WARNING
    restart: unless-stopped
    # Remove volume mounts for security
```

### SSL/HTTPS Setup

#### **With Reverse Proxy (Recommended):**

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api/ {
        proxy_pass http://localhost:8001/;
    }
}
```

### Monitoring & Health Checks

#### **Health Check Endpoints:**
```bash
# Agent API health
curl http://localhost:8001/health

# Response:
{"status": "healthy", "service": "OpenAI Agents SDK Boilerplate API"}
```

#### **Database Health:**
```bash
# Check database connection
docker-compose exec postgres pg_isready -U chainlit_user
```

#### **Docker Health Checks:**
```yaml
# Add to docker-compose.yml
services:
  agent_app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## ⚙️ Configuration

### Complete Configuration Reference

#### **.env Variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | - | OpenAI API key |
| `POSTGRES_DB` | ✅ Yes | `chainlit_db` | Database name |
| `POSTGRES_USER` | ✅ Yes | `chainlit_user` | Database user |
| `POSTGRES_PASSWORD` | ✅ Yes | - | Database password |
| `POSTGRES_HOST` | No | `postgres` | Database host |
| `POSTGRES_PORT` | No | `5432` | Database port |
| `DEFAULT_HISTORY_MODE` | No | `local_text` | Default conversation mode |
| `CHAINLIT_AUTH_SECRET` | ✅ Production | - | JWT secret for auth |
| `API_BASE_URL` | No | `http://agent_app:8001` | Internal API URL |
| `VECTOR_STORE_ID` | No | `default_store` | File search store ID |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

#### **Chainlit Configuration (.chainlit/config.toml):**

```toml
[project]
enable_telemetry = false                    # Disable analytics
session_timeout = 3600                      # 1 hour session timeout
data_persistence = true                     # Enable database storage

[features]
multi_modal = true                          # Enable file uploads
unsafe_allow_html = false                   # Security: disable HTML

[features.mcp]
enabled = true                              # Enable MCP integration

[features.mcp.sse]
enabled = true                              # Enable SSE transport

[features.mcp.stdio]
enabled = true                              # Enable stdio transport
allowed_executables = ["npx", "uvx", "python"]  # Security whitelist

# MCP Server configurations
[[features.mcp.servers]]
name = "everything"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-everything"]

[UI]
name = "OpenAI Agents SDK Boilerplate"
description = "Multi-modal agentic AI boilerplate"
default_collapse_content = true
hide_cot = false                            # Show chain of thought

# Theme customization
[UI.theme.light]
background = "#FAFAFA"
paper = "#FFFFFF"

[UI.theme.light.primary]
main = "#4A90E2"
dark = "#357ABD"
light = "#6BA3E5"
```

### Customization Options

#### **System Prompts:**
```python
# instructions.py
AGENT_INSTRUCTIONS = """
You are an advanced AI assistant powered by OpenAI Agents SDK.

Core Capabilities:
- Web search for current information
- Code interpretation for calculations  
- MCP server tools for specialized functions

Guidelines:
- Always use tools when they provide better information
- Be thorough and analytical in responses
- Provide sources for web search results
"""
```

#### **Tool Selection:**
```python
# openai_tools.py
def get_production_tools():
    """Safe tools for production use."""
    return [
        WebSearchTool(),
        CodeInterpreterTool(),
        # FileSearchTool(),        # Enable if needed
        # ImageGenerationTool(),   # Enable if needed
    ]
```

#### **UI Customization:**
```toml
# Custom CSS
[UI]
custom_css = "/public/custom.css"

# GitHub link
github = "https://github.com/your-username/your-repo"
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### **🔴 "OpenAI API Key not found"**
```bash
# Check environment variable
docker-compose exec agent_app env | grep OPENAI

# Solution: Add to .env file
OPENAI_API_KEY=sk-your-key-here
```

#### **🔴 "Database connection failed"**
```bash
# Check database status
docker-compose ps postgres

# Check connection
docker-compose exec postgres pg_isready -U chainlit_user

# Solution: Ensure database is running
docker-compose up postgres -d
```

#### **🔴 "MCP server connection failed"**
```bash
# Check MCP server logs
docker-compose logs mcp_server

# Test MCP endpoint
curl http://localhost:8000/mcp/

# Solution: Restart MCP service
docker-compose restart mcp_server
```

#### **🔴 "Chainlit UI not loading"**
```bash
# Check Chainlit logs
docker-compose logs chainlit_ui

# Common issues:
# 1. Port conflict - change port in docker-compose.yml
# 2. Build failed - run docker-compose build chainlit_ui
# 3. Environment missing - check .env file
```

#### **🔴 "Streaming not working"**
```bash
# Check browser network tab for SSE connection
# Look for /stream endpoint calls

# Solutions:
# 1. Enable streaming in UI settings
# 2. Check proxy configuration (if behind reverse proxy)
# 3. Verify CORS settings in FastAPI
```

#### **🔴 "Tools not available"**
```bash
# Check tool loading
curl http://localhost:8001/tools/available

# Solutions:
# 1. Enable tools in UI settings
# 2. Check OpenAI API key permissions
# 3. Verify tool imports in openai_tools.py
```

**Built with ❤️ by [Shayan Rastgou](https://github.com/ShayanRas)**