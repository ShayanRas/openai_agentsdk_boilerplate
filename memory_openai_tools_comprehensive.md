# OpenAI Agents Tools - Comprehensive Implementation Guide

## Tool Categories Overview

### 1. Hosted Tools (OpenAI-Provided)
Directly managed by OpenAI with built-in capabilities:
- WebSearchTool
- FileSearchTool  
- ComputerTool
- CodeInterpreterTool
- HostedMCPTool
- ImageGenerationTool
- LocalShellTool

### 2. Function Tools (Custom Python Functions)
User-defined tools created from Python functions:
- Automatic schema generation
- Docstring-based descriptions
- Support for complex type annotations
- Sync and async function support

### 3. Agent-as-Tool
Agents that can be called as tools without full handoffs:
- Custom output extraction
- Tool name/description override
- Complex agent orchestration

## Hosted Tools Deep Dive

### WebSearchTool
**Purpose**: Enable LLMs to search the web for current information

**Configuration**:
```python
from agents import Agent, WebSearchTool

# Basic configuration
web_search = WebSearchTool()

# Advanced configuration
web_search_advanced = WebSearchTool(
    user_location={"type": "approximate", "city": "New York"},
    search_context_size="high"  # Options: "low", "medium", "high"
)

# Agent integration
agent = Agent(
    name="Web Researcher",
    instructions="Search the web for current information and provide summaries",
    tools=[web_search_advanced]
)
```

**Use Cases**:
- Current events research
- Real-time data retrieval
- Market information gathering
- News summarization
- Location-specific searches

**Example Implementation**:
```python
async def web_research_workflow():
    agent = Agent(
        name="Web searcher",
        instructions="You are a helpful research agent.",
        tools=[WebSearchTool(
            user_location={"type": "approximate", "city": "San Francisco"}
        )]
    )
    
    result = await Runner.run(
        agent,
        "Search for latest AI developments and summarize the top 3 trends"
    )
    return result.final_output
```

### FileSearchTool  
**Purpose**: Search through vector stores for document-based information

**Configuration**:
```python
from agents import Agent, FileSearchTool

# Advanced file search configuration
file_search = FileSearchTool(
    vector_store_ids=["vs_67bf88953f748191be42b462090e53e7"],
    max_num_results=5,
    include_search_results=True,
    ranking_options={
        "score_threshold": 0.8,
        "ranker": "cohere_rerank"
    },
    filters={
        "file_type": "pdf",
        "created_after": "2024-01-01"
    }
)

agent = Agent(
    name="Document Searcher",
    instructions="Search through documents to find relevant information",
    tools=[file_search]
)
```

**Use Cases**:
- Document retrieval from knowledge bases
- Research paper searches
- Internal documentation queries
- Compliance document searches
- Technical specification lookups

**Example Implementation**:
```python
async def document_research_workflow(query):
    agent = Agent(
        name="File searcher",
        instructions="Search documents for specific information",
        tools=[FileSearchTool(
            max_num_results=3,
            vector_store_ids=["your_vector_store_id"],
            include_search_results=True
        )]
    )
    
    result = await Runner.run(agent, query)
    return {
        "answer": result.final_output,
        "sources": [str(item) for item in result.new_items]
    }
```

### CodeInterpreterTool
**Purpose**: Execute code in a sandboxed environment

**Configuration**:
```python
from agents import Agent, CodeInterpreterTool

# Basic code interpreter
code_tool = CodeInterpreterTool(
    tool_config={
        "type": "code_interpreter",
        "container": {"type": "auto"}
    }
)

agent = Agent(
    name="Code Analyst",
    instructions="You excel at mathematical calculations and data analysis",
    tools=[code_tool]
)
```

**Streaming Implementation**:
```python
async def code_execution_with_streaming():
    agent = Agent(
        name="Math Solver",
        instructions="Solve complex mathematical problems using code",
        tools=[CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
        )]
    )
    
    result = Runner.run_streamed(
        agent,
        "Calculate the fibonacci sequence up to 1000 and plot the results"
    )
    
    async for event in result.stream_events():
        if (event.type == "run_item_stream_event" and 
            event.item.type == "tool_call_item" and
            event.item.raw_item.type == "code_interpreter_call"):
            print(f"Executing code:\n```python\n{event.item.raw_item.code}\n```")
```

**Use Cases**:
- Mathematical calculations
- Data analysis and visualization
- Statistical computations
- Algorithm implementation
- Scientific computing

### ComputerTool
**Purpose**: Control computer interfaces and browser automation

**Configuration**:
```python
from agents import Agent, ComputerTool
from agents.computer import LocalPlaywrightComputer

async def computer_automation_workflow():
    async with LocalPlaywrightComputer() as computer:
        agent = Agent(
            name="Browser Automator",
            instructions="You can interact with websites and applications",
            tools=[ComputerTool(computer)],
            model="computer-use-preview"  # Specialized model for computer use
        )
        
        result = await Runner.run(
            agent,
            "Navigate to GitHub and search for OpenAI repositories"
        )
        return result.final_output
```

**Capabilities**:
- Screenshot capture
- Mouse interactions (click, double-click, drag)
- Keyboard input and shortcuts
- Scrolling and navigation
- Form filling and submission
- Browser automation

**Advanced Computer Interactions**:
```python
class CustomComputerInteraction:
    def __init__(self, computer):
        self.computer = computer
    
    async def automated_research_task(self, search_query):
        # Take screenshot for context
        screenshot = await self.computer.screenshot()
        
        # Navigate and search
        await self.computer.click({"x": 500, "y": 300})  # Search box
        await self.computer.type(search_query)
        await self.computer.key("Return")
        
        # Capture results
        await asyncio.sleep(2)  # Wait for results
        results_screenshot = await self.computer.screenshot()
        
        return {
            "initial_state": screenshot,
            "results_state": results_screenshot
        }
```

### ImageGenerationTool
**Purpose**: Generate images from text prompts

**Configuration**:
```python
from agents import Agent, ImageGenerationTool

# Image generation with quality settings
image_tool = ImageGenerationTool(
    tool_config={
        "type": "image_generation",
        "quality": "high",  # Options: "low", "standard", "high"
        "size": "1024x1024",
        "style": "vivid"  # Options: "vivid", "natural"
    }
)

agent = Agent(
    name="Creative Assistant",
    instructions="Create images based on detailed descriptions",
    tools=[image_tool]
)
```

**Implementation with File Handling**:
```python
import base64
import tempfile
import subprocess
import platform

async def image_generation_workflow(prompt):
    agent = Agent(
        name="Image generator",
        instructions="Create high-quality images from descriptions",
        tools=[ImageGenerationTool(
            tool_config={"type": "image_generation", "quality": "high"}
        )]
    )
    
    result = await Runner.run(agent, f"Create an image: {prompt}")
    
    # Extract and save image (if needed)
    if hasattr(result, 'image_data'):
        image_data = base64.b64decode(result.image_data)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(image_data)
            image_path = tmp_file.name
        
        # Auto-open image based on platform
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", image_path])
        elif platform.system() == "Windows":
            subprocess.run(["start", image_path], shell=True)
        else:  # Linux
            subprocess.run(["xdg-open", image_path])
        
        return {"result": result.final_output, "image_path": image_path}
    
    return {"result": result.final_output}
```

### LocalShellTool
**Purpose**: Execute shell commands on the local system

**Configuration**:
```python
from agents import Agent, LocalShellTool
from agents.tool import LocalShellExecutor

# Custom shell executor
async def secure_shell_executor(command_request):
    """Secure shell command execution with validation"""
    command = command_request.command
    
    # Security validation
    dangerous_commands = ['rm', 'del', 'format', 'sudo', 'su']
    if any(cmd in command.lower() for cmd in dangerous_commands):
        return "Error: Command not allowed for security reasons"
    
    # Execute safe commands
    try:
        import subprocess
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        return f"Exit code: {result.returncode}\nOutput: {result.stdout}\nError: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {str(e)}"

# Agent with secure shell tool
shell_agent = Agent(
    name="System Administrator",
    instructions="Execute system commands safely and provide clear output",
    tools=[LocalShellTool(executor=secure_shell_executor)]
)
```

**Use Cases**:
- File system operations
- System monitoring
- Development workflow automation
- Build and deployment scripts
- Environment setup

### HostedMCPTool
**Purpose**: Connect to remote MCP servers for external tool access

**Configuration**:
```python
from agents import Agent, HostedMCPTool

# Hosted MCP tool configuration
def approval_handler(request):
    """Handle tool approval requests"""
    print(f"Tool approval requested: {request.tool_name}")
    print(f"Arguments: {request.arguments}")
    return True  # Auto-approve for demo

hosted_mcp = HostedMCPTool(
    tool_config={
        "url": "https://api.example.com/mcp",
        "authentication": {
            "type": "bearer",
            "token": "your_api_token"
        }
    },
    on_approval_request=approval_handler
)

agent = Agent(
    name="External Tool User",
    instructions="Use external MCP tools for specialized tasks",
    tools=[hosted_mcp]
)
```

## Function Tools (Custom Python Tools)

### Basic Function Tool Creation
```python
from agents import function_tool
from typing import Dict, List
from pydantic import BaseModel

# Simple function tool
@function_tool
def calculate_compound_interest(
    principal: float,
    rate: float,
    time: float,
    compounds_per_year: int = 12
) -> float:
    """Calculate compound interest.
    
    Args:
        principal: Initial investment amount
        rate: Annual interest rate (as decimal)
        time: Investment time in years
        compounds_per_year: Compounding frequency per year
    
    Returns:
        Final amount after compound interest
    """
    amount = principal * (1 + rate/compounds_per_year) ** (compounds_per_year * time)
    return round(amount, 2)

# Complex function tool with structured output
class WeatherData(BaseModel):
    city: str
    temperature: float
    conditions: str
    humidity: int
    wind_speed: float

@function_tool
async def get_detailed_weather(city: str, units: str = "metric") -> WeatherData:
    """Get detailed weather information for a city.
    
    Args:
        city: City name to get weather for
        units: Units for temperature (metric/imperial)
    
    Returns:
        Detailed weather data including temperature, conditions, etc.
    """
    # Simulate API call
    await asyncio.sleep(0.1)
    
    return WeatherData(
        city=city,
        temperature=22.5 if units == "metric" else 72.5,
        conditions="Partly cloudy",
        humidity=65,
        wind_speed=12.0
    )
```

### Advanced Function Tool Patterns
```python
from agents import RunContextWrapper

@function_tool
def context_aware_tool(
    ctx: RunContextWrapper[Any],
    query: str,
    use_history: bool = True
) -> str:
    """Tool that can access conversation context.
    
    Args:
        ctx: Runtime context wrapper
        query: User query to process
        use_history: Whether to consider conversation history
    
    Returns:
        Context-aware response
    """
    if use_history and hasattr(ctx, 'conversation_history'):
        history_context = "Previous conversation considered."
    else:
        history_context = "No history context used."
    
    return f"Processing: {query}. {history_context}"

# Tool with custom behavior
async def custom_tool_behavior(
    context: RunContextWrapper[Any],
    results: List[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    """Custom tool result processing"""
    processed_results = []
    
    for result in results:
        if isinstance(result.output, WeatherData):
            weather_summary = f"{result.output.city}: {result.output.temperature}°C, {result.output.conditions}"
            processed_results.append(weather_summary)
        else:
            processed_results.append(str(result.output))
    
    final_output = "\n".join(processed_results)
    
    return ToolsToFinalOutputResult(
        is_final_output=True,
        final_output=final_output
    )
```

## Agent-as-Tool Pattern

### Basic Agent-as-Tool
```python
# Specialist agents
spanish_translator = Agent(
    name="Spanish Translator",
    instructions="Translate text to Spanish with cultural context"
)

technical_writer = Agent(
    name="Technical Writer", 
    instructions="Write clear technical documentation"
)

# Manager agent using specialists as tools
manager_agent = Agent(
    name="Content Manager",
    instructions="Coordinate content creation using specialist agents",
    tools=[
        spanish_translator.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate content to Spanish"
        ),
        technical_writer.as_tool(
            tool_name="write_technical_docs",
            tool_description="Create technical documentation"
        )
    ]
)
```

### Advanced Agent-as-Tool with Custom Extractors
```python
# Custom output extractor
async def summary_extractor(run_result: RunResult) -> str:
    """Extract summary from agent result"""
    if hasattr(run_result, 'structured_output'):
        return run_result.structured_output.get('summary', run_result.final_output)
    return run_result.final_output[:200] + "..." if len(run_result.final_output) > 200 else run_result.final_output

# Financial analyst agents with extractors
fundamentals_agent = Agent(
    name="Fundamentals Analyst",
    instructions="Analyze company fundamentals and provide structured output"
)

risk_agent = Agent(
    name="Risk Analyst", 
    instructions="Assess investment risks and provide risk summary"
)

# Portfolio manager using agent tools with custom extractors
portfolio_manager = Agent(
    name="Portfolio Manager",
    instructions="Make investment decisions using specialist analysis",
    tools=[
        fundamentals_agent.as_tool(
            tool_name="fundamentals_analysis",
            tool_description="Get fundamental analysis summary",
            custom_output_extractor=summary_extractor
        ),
        risk_agent.as_tool(
            tool_name="risk_analysis",
            tool_description="Get risk assessment summary",
            custom_output_extractor=summary_extractor
        )
    ]
)
```

## Tool Integration Best Practices

### 1. Tool Selection Strategy
```python
class ToolSelector:
    def __init__(self):
        self.available_tools = {
            "research": [WebSearchTool(), FileSearchTool()],
            "analysis": [CodeInterpreterTool()],
            "creative": [ImageGenerationTool()],
            "automation": [ComputerTool(), LocalShellTool()],
            "external": [HostedMCPTool()]
        }
    
    def get_tools_for_task(self, task_type: str) -> List:
        """Select appropriate tools based on task type"""
        return self.available_tools.get(task_type, [])
    
    def create_specialized_agent(self, task_type: str, instructions: str):
        """Create agent with task-appropriate tools"""
        tools = self.get_tools_for_task(task_type)
        return Agent(
            name=f"{task_type.title()}Agent",
            instructions=instructions,
            tools=tools
        )
```

### 2. Tool Error Handling
```python
async def robust_tool_execution(agent, user_input, max_retries=3):
    """Execute agent with tool error handling"""
    for attempt in range(max_retries):
        try:
            result = await Runner.run(agent, user_input)
            return result
        except ToolExecutionError as e:
            if attempt == max_retries - 1:
                # Fallback to basic agent without tools
                fallback_agent = Agent(
                    name="Fallback Agent",
                    instructions="Provide helpful responses without external tools"
                )
                return await Runner.run(fallback_agent, user_input)
            else:
                # Retry with modified input
                user_input += f"\n\nNote: Previous tool execution failed: {str(e)}"
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
```

### 3. Tool Performance Monitoring
```python
import time
from typing import Dict, List

class ToolPerformanceMonitor:
    def __init__(self):
        self.tool_metrics: Dict[str, List[float]] = {}
    
    async def monitored_tool_execution(self, tool_name: str, tool_func, *args, **kwargs):
        """Monitor tool execution performance"""
        start_time = time.time()
        
        try:
            result = await tool_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if tool_name not in self.tool_metrics:
                self.tool_metrics[tool_name] = []
            
            self.tool_metrics[tool_name].append(execution_time)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"Tool {tool_name} failed after {execution_time:.2f}s: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for all tools"""
        stats = {}
        for tool_name, times in self.tool_metrics.items():
            if times:
                stats[tool_name] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_calls": len(times)
                }
        return stats
```

This comprehensive tool system enables building sophisticated AI agents with powerful capabilities for research, analysis, automation, and creative tasks.