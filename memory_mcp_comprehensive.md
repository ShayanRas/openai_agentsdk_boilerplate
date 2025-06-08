# Model Context Protocol (MCP) - Comprehensive Implementation Guide

## MCP Core Architecture

### Protocol Overview
MCP is a standardized protocol enabling seamless communication between AI applications, servers, and LLMs through unified interfaces for resources, tools, prompts, and sampling.

### Key Design Principles
1. **Flexibility**: Support diverse AI application architectures
2. **Interoperability**: Cross-platform and cross-language compatibility
3. **Security**: Built-in access controls and validation
4. **User Control**: Human oversight in AI interactions
5. **Dynamic Discovery**: Runtime capability discovery

## MCP Components Deep Dive

### 1. Resources
**Purpose**: Expose data and content from servers to clients

**Architecture**:
- Identified by unique URIs (e.g., `file://documents/report.pdf`)
- Support text and binary content types
- Discoverable through standardized endpoints
- Can be static or dynamically generated

**Implementation Pattern**:
```python
# Resource discovery
resources = await client.list_resources()

# Resource access
resource_content = await client.read_resource("file://config/settings.json")
```

**Use Cases**:
- File system access
- Database content
- API data
- Configuration files
- Documentation
- Real-time data feeds

### 2. Tools
**Purpose**: Enable servers to expose executable functions to clients

**Capabilities**:
- API calls
- System operations
- Data processing
- External service integration
- File manipulation
- Database operations

**Discovery Pattern**:
```python
# Tool discovery
available_tools = await client.list_tools()

# Tool execution
result = await client.call_tool("calculator", {"operation": "add", "a": 5, "b": 3})
```

**Advanced Tool Patterns**:
- **Chained Tools**: Tools that call other tools
- **Stateful Tools**: Tools that maintain state across calls
- **Streaming Tools**: Tools that return streaming responses
- **Authenticated Tools**: Tools requiring authorization

### 3. Prompts
**Purpose**: Define reusable prompt templates with dynamic arguments

**Features**:
- Template-based prompts
- Dynamic argument injection
- Multi-step workflow support
- Context-aware prompts

**Implementation**:
```python
# Prompt discovery
prompts = await client.list_prompts()

# Prompt usage with arguments
prompt_result = await client.get_prompt(
    "code_review", 
    arguments={"language": "python", "file_path": "main.py"}
)
```

**Prompt Patterns**:
- **Conditional Prompts**: Different prompts based on context
- **Hierarchical Prompts**: Nested prompt structures
- **Workflow Prompts**: Multi-step prompt sequences

### 4. Sampling
**Purpose**: Enable servers to request LLM completions through clients

**Control Features**:
- Model selection
- Generation parameters (temperature, max_tokens, etc.)
- Human oversight integration
- Fine-grained completion control

**Usage Pattern**:
```python
# Server requests LLM completion
completion = await client.sample({
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Analyze this data"}],
    "temperature": 0.7,
    "max_tokens": 1000
})
```

## MCP Server Implementation

### Basic Server Structure
```python
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http import EventStore

class MCPServer:
    def __init__(self):
        self.server = Server("my-mcp-server")
        self.setup_handlers()
    
    def setup_handlers(self):
        # Resource handlers
        @self.server.list_resources()
        async def list_resources() -> list[types.Resource]:
            return [
                types.Resource(
                    uri="file://config.json",
                    name="Configuration",
                    description="Application configuration"
                )
            ]
        
        # Tool handlers
        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="calculator",
                    description="Perform mathematical calculations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {"type": "string"},
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        }
                    }
                )
            ]
```

### Advanced Server Patterns

#### 1. Stateful MCP Server
```python
class StatefulMCPServer:
    def __init__(self):
        self.state = {}
        self.session_data = {}
    
    async def handle_tool_call(self, name: str, arguments: dict):
        session_id = arguments.get("session_id")
        
        if name == "set_context":
            self.session_data[session_id] = arguments["context"]
        elif name == "get_context":
            return self.session_data.get(session_id, {})
```

#### 2. Dynamic Resource Server
```python
class DynamicResourceServer:
    async def list_resources(self) -> list[types.Resource]:
        # Dynamically discover available resources
        resources = []
        
        # File system resources
        for file_path in self.scan_files():
            resources.append(types.Resource(
                uri=f"file://{file_path}",
                name=file_path.name,
                description=f"File: {file_path}"
            ))
        
        # Database resources  
        for table in self.database_tables():
            resources.append(types.Resource(
                uri=f"db://{table}",
                name=table,
                description=f"Database table: {table}"
            ))
        
        return resources
```

#### 3. Authenticated MCP Server
```python
class AuthenticatedMCPServer:
    def __init__(self):
        self.auth_tokens = {}
    
    async def authenticate(self, token: str) -> bool:
        return token in self.auth_tokens
    
    async def handle_authenticated_tool(self, name: str, arguments: dict, auth_token: str):
        if not await self.authenticate(auth_token):
            raise PermissionError("Invalid authentication token")
        
        # Proceed with tool execution
        return await self.execute_tool(name, arguments)
```

## MCP Client Integration

### Client Connection Patterns
```python
# HTTP/SSE Transport
client = MCPClient(transport="http", url="http://localhost:8000/mcp")

# Stdio Transport  
client = MCPClient(transport="stdio", command=["python", "server.py"])

# WebSocket Transport
client = MCPClient(transport="websocket", url="ws://localhost:8000/mcp")
```

### Client Usage Patterns

#### 1. Resource Management Client
```python
class ResourceManager:
    def __init__(self, mcp_client):
        self.client = mcp_client
        self.resource_cache = {}
    
    async def get_resource(self, uri: str, use_cache: bool = True):
        if use_cache and uri in self.resource_cache:
            return self.resource_cache[uri]
        
        resource = await self.client.read_resource(uri)
        
        if use_cache:
            self.resource_cache[uri] = resource
        
        return resource
```

#### 2. Tool Orchestration Client
```python
class ToolOrchestrator:
    def __init__(self, mcp_client):
        self.client = mcp_client
        self.tool_registry = {}
    
    async def discover_tools(self):
        tools = await self.client.list_tools()
        for tool in tools:
            self.tool_registry[tool.name] = tool
    
    async def execute_workflow(self, workflow_steps):
        results = []
        for step in workflow_steps:
            tool_name = step["tool"]
            arguments = step["arguments"]
            
            result = await self.client.call_tool(tool_name, arguments)
            results.append(result)
            
            # Pass result to next step if needed
            if "pass_result" in step:
                next_step = workflow_steps[step["pass_result"]]
                next_step["arguments"].update({"previous_result": result})
        
        return results
```

## Integration with OpenAI Agents

### MCP Server as Agent Tool Provider
```python
from agents import Agent
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

# MCP integration with agent
mcp_params = MCPServerStreamableHttpParams(url="http://localhost:8000/mcp")

async with MCPServerStreamableHttp(
    params=mcp_params,
    name="AgentMCPClient",
    cache_tools_list=True
) as mcp_server:
    
    agent = Agent(
        name="MCPAgent",
        instructions="You have access to MCP tools for various operations",
        tools=[],  # Direct tools
        mcp_servers=[mcp_server]  # MCP-provided tools
    )
    
    result = await Runner.run(agent, user_input)
```

### Multi-Agent MCP Coordination
```python
# Different agents with different MCP capabilities
research_mcp = MCPServerStreamableHttp(
    params=MCPServerStreamableHttpParams(url="http://research-server:8000/mcp")
)

analysis_mcp = MCPServerStreamableHttp(
    params=MCPServerStreamableHttpParams(url="http://analysis-server:8000/mcp")
)

# Specialized agents with specific MCP tools
research_agent = Agent(
    name="Researcher",
    instructions="Research topics using available research tools",
    mcp_servers=[research_mcp]
)

analysis_agent = Agent(
    name="Analyst", 
    instructions="Analyze data using statistical tools",
    mcp_servers=[analysis_mcp]
)

# Orchestrator can hand off to specialized agents
orchestrator = Agent(
    name="Orchestrator",
    instructions="Route tasks to appropriate specialists",
    handoffs=[research_agent, analysis_agent]
)
```

## Security and Best Practices

### 1. Input Validation
- Validate all tool inputs against schemas
- Sanitize resource URIs
- Implement rate limiting
- Use authentication tokens

### 2. Resource Access Control
- Implement permission systems
- Audit resource access
- Use principle of least privilege
- Monitor resource usage

### 3. Error Handling
- Graceful degradation when MCP servers unavailable
- Retry mechanisms for transient failures
- Fallback tools when MCP tools fail
- Comprehensive error logging

### 4. Performance Optimization
- Cache frequently accessed resources
- Implement connection pooling
- Use streaming for large responses
- Monitor tool execution times

This comprehensive MCP implementation enables powerful tool integration and resource management for sophisticated AI agent systems.