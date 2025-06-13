# Render Deployment Guide - CastForge Agent

## Summary
This guide provides complete instructions for deploying the CastForge Agent multi-service application to Render. This memory addresses all known issues and provides preemptive solutions to common deployment problems.

## Architecture Overview
The CastForge Agent consists of 4 services:
1. **postgres** - Managed PostgreSQL database
2. **mcp-server** - MCP (Model Context Protocol) tool server
3. **agent-api** - FastAPI backend with OpenAI Agents SDK
4. **web** - Chainlit frontend interface

## Critical Issues & Solutions

### 1. Environment Variable Hardcoding Issue ⚠️
**Problem**: Hardcoded URLs in render.yaml override manually set environment variables
**Impact**: Services can't communicate via public URLs, causing "Name or service not known" errors

**Solution**: Use `sync: false` for all cross-service URLs in render.yaml:

```yaml
# In render.yaml - agent-api service
envVars:
- key: MCP_SERVER_URL
  sync: false # This will be set manually in Render dashboard

# In render.yaml - web service  
envVars:
- key: API_BASE_URL
  sync: false # This will be set manually in Render dashboard
```

**Code Fix**: Ensure environment variable fallbacks in code:
```python
# In api_main.py
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp_server:8000/mcp")
```

### 2. Prisma Memory Issues 🧠
**Problem**: Chainlit service runs out of memory during Prisma installation (512MB limit)
**Impact**: "Out of memory" errors during container startup

**Solution**: Build-time Prisma generation + memory optimization

**Dockerfile.chainlit changes**:
```dockerfile
# Add before CMD
COPY schema.prisma .
COPY init_db.py .

# Generate Prisma client during build (unlimited memory)
RUN python -m prisma generate

# Runtime uses pre-generated client
CMD python init_db.py && chainlit run chainlit_app.py -h --host 0.0.0.0 --port 8002
```

**init_db.py modification**:
```python
def run_prisma_migrate():
    print("✓ Prisma client already generated during build")
    
    # Only run schema push (lightweight operation)
    result = subprocess.run(["python", "-m", "prisma", "db", "push"])
    # Remove any prisma generate calls
```

### 3. Database Connection Pool Exhaustion 💾
**Problem**: Multiple services exhaust PostgreSQL connection limits
**Impact**: "TooManyConnectionsError: remaining connection slots are reserved for roles with the SUPERUSER attribute"

**Solution**: Reduce pool sizes and upgrade database plan

**database.py fix**:
```python
self.pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=1,
    max_size=3,  # Reduced from 10 to 3 for basic plan
    command_timeout=60,
    statement_cache_size=0
)
```

**render.yaml database upgrade**:
```yaml
databases:
- name: postgres
  plan: basic-1gb  # Upgraded from basic-256mb
  diskSizeGB: 10   # Increased storage
```

### 4. CORS Issues for MCP Server 🌐
**Problem**: Cross-origin requests between services fail
**Impact**: MCP tools not accessible from agent-api

**Solution**: Add CORS middleware to MCP server

**test_mcp_server.py addition**:
```python
from starlette.middleware.cors import CORSMiddleware

# Add after Starlette app creation
starlette_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Streaming Response Completion 🌊
**Problem**: ASGI responses don't complete properly
**Impact**: "ASGI callable returned without completing response" errors

**Solution**: Add finally block to streaming functions

**api_main.py fix**:
```python
except Exception as e:
    print(f"Error during streaming: {e}")
    yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
finally:
    # Ensure the stream always ends properly
    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
```

## Complete render.yaml Configuration

```yaml
databases:
- name: postgres
  databaseName: castforge_db
  user: castforge_user
  ipAllowList: []
  plan: basic-1gb
  diskSizeGB: 10

services:
# MCP Server - Internal service for tools
- type: web
  name: mcp-server
  runtime: docker
  dockerfilePath: ./Dockerfile.mcp
  plan: starter
  healthCheckPath: /health
  envVars:
  - key: PORT
    value: 8000
  - key: HOST
    value: 0.0.0.0
  - key: LOG_LEVEL
    value: INFO

# Agent API - Internal FastAPI backend
- type: web
  name: agent-api
  runtime: docker
  dockerfilePath: ./Dockerfile.agent
  plan: starter
  healthCheckPath: /health
  envVars:
  - key: PORT
    value: 8001
  - key: OPENAI_API_KEY
    sync: false # Set manually in dashboard
  - key: MCP_SERVER_URL
    sync: false # Set manually in dashboard
  - key: DATABASE_URL
    fromDatabase:
      name: postgres
      property: connectionString

# Chainlit Web UI - Public web service
- type: web
  name: web
  runtime: docker
  dockerfilePath: ./Dockerfile.chainlit
  plan: standard  # Upgraded for Prisma memory requirements
  domains:
  - demo.castforge.ca
  envVars:
  - key: PORT
    value: 8002
  - key: API_BASE_URL
    sync: false # Set manually in dashboard
  - key: DEFAULT_HISTORY_MODE
    value: local_text
  - key: CHAINLIT_AUTH_SECRET
    generateValue: true
  - key: DATABASE_URL
    fromDatabase:
      name: postgres
      property: connectionString
```

## Manual Environment Variable Setup

After deployment, set these in Render Dashboard:

### agent-api service:
- `OPENAI_API_KEY` = your_openai_api_key
- `MCP_SERVER_URL` = `https://mcp-server-XXXX.onrender.com/mcp`

### web service:
- `API_BASE_URL` = `https://agent-api-XXXX.onrender.com`

*Replace XXXX with your actual Render service identifiers*

## Comprehensive Startup Logging

Add detailed logging to all services for debugging:

### api_main.py startup event:
```python
@app.on_event("startup")
async def startup_event():
    print("🚀 [AGENT-API] Starting up...")
    print(f"🔧 [AGENT-API] OpenAI API Key configured: {'✅ Yes' if OPENAI_API_KEY else '❌ No'}")
    print(f"🔧 [AGENT-API] MCP Server URL: {MCP_SERVER_URL}")
    
    # Test database connection
    try:
        await db_manager.initialize()
        print("✅ [AGENT-API] Database connection pool initialized successfully")
    except Exception as e:
        print(f"❌ [AGENT-API] Database connection failed: {e}")
        raise
    
    # Test MCP server connection
    try:
        import httpx
        if MCP_SERVER_URL.endswith('/mcp'):
            health_url = MCP_SERVER_URL[:-4] + '/health'
        else:
            health_url = MCP_SERVER_URL.rstrip('/') + '/health'
        
        print(f"🔧 [AGENT-API] Testing MCP server health at: {health_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(health_url)
            if response.status_code == 200:
                print("✅ [AGENT-API] MCP Server connection successful")
            else:
                print(f"⚠️ [AGENT-API] MCP Server health check responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ [AGENT-API] MCP Server connection failed: {e}")
        print("⚠️ [AGENT-API] Will continue without MCP tools")
    
    print("🎉 [AGENT-API] Startup complete!")
```

### database.py logging:
```python
async def initialize(self):
    if not self.pool:
        print(f"🔧 [DATABASE] Connecting to: {DATABASE_URL[:50]}..." if DATABASE_URL else "❌ [DATABASE] No DATABASE_URL provided")
        try:
            self.pool = await asyncpg.create_pool(...)
            print("✅ [DATABASE] Connection pool created successfully")
            await self.ensure_schema()
            print("✅ [DATABASE] Schema initialization complete")
        except Exception as e:
            print(f"❌ [DATABASE] Initialization failed: {e}")
            raise
```

### test_mcp_server.py lifespan:
```python
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
```

### chainlit_app.py startup:
```python
# At module level
print("🚀 [CHAINLIT-WEB] Chainlit application starting...")
print(f"🔧 [CHAINLIT-WEB] OpenAI API Key configured: {'✅ Yes' if os.getenv('OPENAI_API_KEY') else '❌ No'}")
print(f"🔧 [CHAINLIT-WEB] API Base URL: {os.getenv('API_BASE_URL', 'http://agent_app:8001')}")
print(f"🔧 [CHAINLIT-WEB] Default History Mode: {os.getenv('DEFAULT_HISTORY_MODE', 'local_text')}")
print(f"🔧 [CHAINLIT-WEB] DATABASE_URL configured: {'✅ Yes' if os.getenv('DATABASE_URL') else '❌ No'}")
print("✅ [CHAINLIT-WEB] Chainlit application configuration complete")

# In @cl.on_chat_start
@cl.on_chat_start
async def on_chat_start():
    print("🔧 [CHAINLIT-WEB] New chat session starting...")
    
    # Test backend connection
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print("✅ [CHAINLIT-WEB] Agent API connection successful")
            else:
                print(f"⚠️ [CHAINLIT-WEB] Agent API responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ [CHAINLIT-WEB] Agent API connection failed: {e}")
```

### init_db.py logging:
```python
async def main():
    print("🚀 [CHAINLIT-DB] Database initialization starting...")
    print(f"🔧 [CHAINLIT-DB] DATABASE_URL configured: {'✅ Yes' if os.getenv('DATABASE_URL') else '❌ No'}")
    
    try:
        print("🔧 [CHAINLIT-DB] Testing PostgreSQL connection...")
        await wait_for_postgres()
        print("✅ [CHAINLIT-DB] PostgreSQL connection successful")
        
        print("🔧 [CHAINLIT-DB] Setting up Chainlit database schema...")
        if run_prisma_migrate():
            print("✅ [CHAINLIT-DB] Chainlit schema created successfully")
            print("🎉 [CHAINLIT-DB] Database initialization complete!")
        else:
            print("❌ [CHAINLIT-DB] Database initialization failed!")
            exit(1)
    except Exception as e:
        print(f"❌ [CHAINLIT-DB] Error initializing database: {e}")
        exit(1)
```

## Deployment Process

1. **Create render.yaml** with the configuration above
2. **Connect GitHub repository** to Render
3. **Render auto-detects blueprint** and creates all services
4. **Manually set environment variables** in Render dashboard:
   - agent-api: `OPENAI_API_KEY`, `MCP_SERVER_URL`
   - web: `API_BASE_URL`
5. **Deploy all services**
6. **Monitor startup logs** for successful connections

## Expected Success Logs

When everything works correctly, you'll see:

```
🚀 [MCP-SERVER] Starting up...
✅ [MCP-SERVER] Available tools: echo, add, get_server_time
🎉 [MCP-SERVER] Startup complete! Ready to handle MCP requests

🚀 [AGENT-API] Starting up...
🔧 [AGENT-API] OpenAI API Key configured: ✅ Yes
🔧 [AGENT-API] MCP Server URL: https://mcp-server-XXXX.onrender.com/mcp
✅ [AGENT-API] Database connection pool initialized successfully
✅ [AGENT-API] MCP Server connection successful
🎉 [AGENT-API] Startup complete!

🚀 [CHAINLIT-WEB] Chainlit application starting...
✅ [CHAINLIT-WEB] Agent API connection successful
```

## Cost Estimation

- **mcp-server**: ~$7/month (starter plan)
- **agent-api**: ~$7/month (starter plan)
- **web**: ~$14/month (standard plan)
- **postgres**: ~$7-15/month (basic-1gb plan)
- **Total**: ~$35-43/month

## Common Troubleshooting

### "Name or service not known" errors
- Check environment variables are set manually in dashboard
- Verify render.yaml uses `sync: false` for cross-service URLs
- Ensure public Render URLs are used, not internal service names

### Memory issues during build
- Verify Prisma generation happens at build-time in Dockerfile
- Check init_db.py doesn't run `prisma generate` at runtime
- Consider upgrading service plan if needed

### Database connection errors
- Reduce connection pool max_size to 3 or lower
- Upgrade database plan to basic-1gb or higher
- Check DATABASE_URL is properly configured

### MCP tools not working
- Verify CORS middleware is added to MCP server
- Check MCP_SERVER_URL points to correct public endpoint
- Test MCP server health endpoint manually

This comprehensive guide should enable successful Render deployment while avoiding all known pitfalls!