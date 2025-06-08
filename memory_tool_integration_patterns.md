# Tool Integration Patterns - Advanced Implementation Guide

## Multi-Tool Agent Architectures

### 1. Layered Tool Architecture
**Pattern**: Organize tools by capability layers for systematic access

```python
from agents import Agent, WebSearchTool, CodeInterpreterTool, FileSearchTool

class LayeredToolAgent:
    def __init__(self):
        # Layer 1: Information Gathering
        self.research_tools = [
            WebSearchTool(search_context_size="high"),
            FileSearchTool(
                vector_store_ids=["knowledge_base_id"],
                max_num_results=10
            )
        ]
        
        # Layer 2: Analysis and Processing
        self.analysis_tools = [
            CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
            )
        ]
        
        # Layer 3: Output Generation
        self.generation_tools = [
            ImageGenerationTool(
                tool_config={"type": "image_generation", "quality": "high"}
            )
        ]
    
    def create_research_agent(self):
        """Agent focused on information gathering"""
        return Agent(
            name="Research Specialist",
            instructions="""
            You are a research specialist. Use web search and file search to gather comprehensive information.
            Always cross-reference multiple sources and provide source citations.
            """,
            tools=self.research_tools
        )
    
    def create_analysis_agent(self):
        """Agent focused on data analysis"""
        return Agent(
            name="Data Analyst",
            instructions="""
            You are a data analyst. Use code interpreter to perform calculations, statistical analysis,
            and data visualization. Always explain your methodology.
            """,
            tools=self.analysis_tools
        )
    
    def create_full_capability_agent(self):
        """Agent with access to all tool layers"""
        all_tools = self.research_tools + self.analysis_tools + self.generation_tools
        
        return Agent(
            name="Full Capability Agent",
            instructions="""
            You have access to comprehensive toolset:
            - Use research tools for information gathering
            - Use analysis tools for data processing and calculations
            - Use generation tools for visual content creation
            
            Always choose the most appropriate tool for each task.
            """,
            tools=all_tools
        )
```

### 2. Adaptive Tool Selection
**Pattern**: Dynamic tool selection based on query analysis

```python
import re
from typing import List, Dict, Any

class AdaptiveToolSelector:
    def __init__(self):
        self.tool_patterns = {
            "web_search": [
                r"current|latest|news|recent|today|yesterday",
                r"search|find|look up|research",
                r"what.*happening|what.*new"
            ],
            "code_interpreter": [
                r"calculate|compute|math|statistics",
                r"analyze.*data|data.*analysis",
                r"plot|graph|chart|visualize"
            ],
            "file_search": [
                r"document|file|pdf|knowledge base",
                r"find.*in.*documents|search.*files"
            ],
            "image_generation": [
                r"create.*image|generate.*picture|draw|design",
                r"visual|illustration|artwork"
            ]
        }
        
        self.available_tools = {
            "web_search": WebSearchTool(),
            "code_interpreter": CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
            ),
            "file_search": FileSearchTool(
                vector_store_ids=["default_store"],
                max_num_results=5
            ),
            "image_generation": ImageGenerationTool(
                tool_config={"type": "image_generation", "quality": "standard"}
            )
        }
    
    def analyze_query(self, query: str) -> List[str]:
        """Analyze query to determine needed tools"""
        query_lower = query.lower()
        needed_tools = []
        
        for tool_type, patterns in self.tool_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    needed_tools.append(tool_type)
                    break
        
        # Default to web search if no specific tools identified
        if not needed_tools:
            needed_tools.append("web_search")
        
        return list(set(needed_tools))  # Remove duplicates
    
    def create_adaptive_agent(self, query: str) -> Agent:
        """Create agent with tools adapted to the query"""
        needed_tool_types = self.analyze_query(query)
        selected_tools = [self.available_tools[tool_type] for tool_type in needed_tool_types]
        
        tool_descriptions = {
            "web_search": "web search for current information",
            "code_interpreter": "code execution for calculations and analysis", 
            "file_search": "document search in knowledge base",
            "image_generation": "image creation and visual content"
        }
        
        available_capabilities = [tool_descriptions[tool_type] for tool_type in needed_tool_types]
        
        return Agent(
            name="Adaptive Agent",
            instructions=f"""
            You have been equipped with the following capabilities based on the user's query:
            {', '.join(available_capabilities)}
            
            Use these tools appropriately to provide the best response to the user's request.
            """,
            tools=selected_tools
        )

# Usage example
async def adaptive_workflow(user_query: str):
    selector = AdaptiveToolSelector()
    agent = selector.create_adaptive_agent(user_query)
    
    result = await Runner.run(agent, user_query)
    return {
        "response": result.final_output,
        "tools_used": selector.analyze_query(user_query)
    }
```

### 3. Tool Chain Orchestration
**Pattern**: Sequential tool usage with result passing

```python
class ToolChainOrchestrator:
    def __init__(self):
        self.research_agent = Agent(
            name="Researcher",
            instructions="Research the topic thoroughly using web search",
            tools=[WebSearchTool(search_context_size="high")]
        )
        
        self.analyst_agent = Agent(
            name="Analyst",
            instructions="Analyze the provided research data using code interpreter",
            tools=[CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
            )]
        )
        
        self.visualizer_agent = Agent(
            name="Visualizer",
            instructions="Create visual representations of the analysis",
            tools=[ImageGenerationTool(
                tool_config={"type": "image_generation", "quality": "high"}
            )]
        )
    
    async def execute_research_chain(self, research_topic: str):
        """Execute a complete research -> analysis -> visualization chain"""
        
        # Step 1: Research
        print("🔍 Researching topic...")
        research_result = await Runner.run(
            self.research_agent,
            f"Research comprehensive information about: {research_topic}"
        )
        
        # Step 2: Analysis
        print("📊 Analyzing research data...")
        analysis_result = await Runner.run(
            self.analyst_agent,
            f"""
            Analyze this research data and identify key trends, patterns, and insights:
            
            Research Data:
            {research_result.final_output}
            
            Provide quantitative analysis where possible.
            """
        )
        
        # Step 3: Visualization
        print("🎨 Creating visualizations...")
        visualization_result = await Runner.run(
            self.visualizer_agent,
            f"""
            Create a visual representation based on this analysis:
            
            Analysis Results:
            {analysis_result.final_output}
            
            Create an informative chart or infographic.
            """
        )
        
        return {
            "research": research_result.final_output,
            "analysis": analysis_result.final_output,
            "visualization": visualization_result.final_output,
            "complete_chain": True
        }

# Enhanced version with error handling and fallbacks
class RobustToolChain(ToolChainOrchestrator):
    async def execute_research_chain_robust(self, research_topic: str, max_retries: int = 2):
        """Execute tool chain with error handling and fallbacks"""
        results = {"research": None, "analysis": None, "visualization": None}
        
        # Step 1: Research with fallback
        for attempt in range(max_retries + 1):
            try:
                research_result = await Runner.run(
                    self.research_agent,
                    f"Research: {research_topic}"
                )
                results["research"] = research_result.final_output
                break
            except Exception as e:
                if attempt == max_retries:
                    results["research"] = f"Research failed: {str(e)}"
                    return results
        
        # Step 2: Analysis with conditional execution
        if results["research"] and "failed" not in results["research"]:
            try:
                analysis_result = await Runner.run(
                    self.analyst_agent,
                    f"Analyze: {results['research']}"
                )
                results["analysis"] = analysis_result.final_output
            except Exception as e:
                results["analysis"] = f"Analysis failed: {str(e)}"
        
        # Step 3: Visualization with conditional execution
        if results["analysis"] and "failed" not in results["analysis"]:
            try:
                viz_result = await Runner.run(
                    self.visualizer_agent,
                    f"Visualize: {results['analysis']}"
                )
                results["visualization"] = viz_result.final_output
            except Exception as e:
                results["visualization"] = f"Visualization failed: {str(e)}"
        
        return results
```

### 4. Parallel Tool Execution
**Pattern**: Concurrent tool usage for efficiency

```python
import asyncio
from typing import Dict, List, Tuple

class ParallelToolExecutor:
    def __init__(self):
        self.web_agent = Agent(
            name="Web Researcher",
            instructions="Search the web for current information",
            tools=[WebSearchTool()]
        )
        
        self.doc_agent = Agent(
            name="Document Searcher", 
            instructions="Search internal documents and knowledge base",
            tools=[FileSearchTool(
                vector_store_ids=["knowledge_base"],
                max_num_results=5
            )]
        )
        
        self.calc_agent = Agent(
            name="Calculator",
            instructions="Perform calculations and analysis",
            tools=[CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
            )]
        )
    
    async def parallel_research(self, query: str) -> Dict[str, str]:
        """Execute multiple research approaches in parallel"""
        
        # Define parallel tasks
        tasks = [
            ("web_search", self.web_agent, f"Search web for: {query}"),
            ("document_search", self.doc_agent, f"Search documents for: {query}"),
            ("calculation", self.calc_agent, f"Perform any relevant calculations for: {query}")
        ]
        
        # Execute all tasks concurrently
        async def execute_task(task_name: str, agent: Agent, task_query: str) -> Tuple[str, str]:
            try:
                result = await Runner.run(agent, task_query)
                return task_name, result.final_output
            except Exception as e:
                return task_name, f"Error: {str(e)}"
        
        # Run all tasks in parallel
        results = await asyncio.gather(*[
            execute_task(name, agent, query) 
            for name, agent, query in tasks
        ])
        
        return dict(results)
    
    async def parallel_analysis_synthesis(self, research_query: str) -> str:
        """Parallel research followed by synthesis"""
        
        # Step 1: Parallel research
        parallel_results = await self.parallel_research(research_query)
        
        # Step 2: Synthesize results
        synthesizer = Agent(
            name="Synthesizer",
            instructions="""
            Synthesize information from multiple sources into a comprehensive response.
            Identify key themes, resolve conflicts, and provide a unified analysis.
            """,
            tools=[]  # No additional tools needed for synthesis
        )
        
        synthesis_input = f"""
        Synthesize the following research results for query: {research_query}
        
        Web Search Results:
        {parallel_results.get('web_search', 'No web results')}
        
        Document Search Results:
        {parallel_results.get('document_search', 'No document results')}
        
        Calculation Results:
        {parallel_results.get('calculation', 'No calculation results')}
        """
        
        synthesis_result = await Runner.run(synthesizer, synthesis_input)
        
        return synthesis_result.final_output
```

### 5. Tool Result Caching and Optimization

```python
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class ToolResultCache:
    def __init__(self, cache_duration_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = timedelta(hours=cache_duration_hours)
    
    def _generate_cache_key(self, tool_name: str, inputs: Dict[str, Any]) -> str:
        """Generate cache key from tool name and inputs"""
        cache_input = f"{tool_name}:{json.dumps(inputs, sort_keys=True)}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get_cached_result(self, tool_name: str, inputs: Dict[str, Any]) -> Optional[str]:
        """Retrieve cached result if available and not expired"""
        cache_key = self._generate_cache_key(tool_name, inputs)
        
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if datetime.now() - cached_entry["timestamp"] < self.cache_duration:
                return cached_entry["result"]
            else:
                # Remove expired entry
                del self.cache[cache_key]
        
        return None
    
    def cache_result(self, tool_name: str, inputs: Dict[str, Any], result: str):
        """Cache tool result"""
        cache_key = self._generate_cache_key(tool_name, inputs)
        self.cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }

class OptimizedToolAgent:
    def __init__(self):
        self.cache = ToolResultCache(cache_duration_hours=6)
        
        self.web_search_tool = WebSearchTool()
        self.code_tool = CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
        )
        
        self.agent = Agent(
            name="Optimized Agent",
            instructions="Use tools efficiently with caching when appropriate",
            tools=[self.web_search_tool, self.code_tool]
        )
    
    async def cached_web_search(self, query: str, location: Optional[str] = None) -> str:
        """Web search with caching"""
        cache_inputs = {"query": query, "location": location}
        
        # Check cache first
        cached_result = self.cache.get_cached_result("web_search", cache_inputs)
        if cached_result:
            print(f"📋 Using cached web search result for: {query}")
            return cached_result
        
        # Execute search
        print(f"🔍 Executing new web search for: {query}")
        search_agent = Agent(
            name="Web Searcher",
            instructions="Search the web for information",
            tools=[WebSearchTool(
                user_location={"type": "approximate", "city": location} if location else None
            )]
        )
        
        result = await Runner.run(search_agent, query)
        
        # Cache result
        self.cache.cache_result("web_search", cache_inputs, result.final_output)
        
        return result.final_output
    
    async def optimized_workflow(self, user_query: str) -> str:
        """Execute workflow with caching optimization"""
        
        # Extract potential search terms for caching
        if "latest" in user_query.lower() or "current" in user_query.lower():
            # Don't cache time-sensitive queries
            result = await Runner.run(self.agent, user_query)
            return result.final_output
        else:
            # Use caching for stable queries
            return await self.cached_web_search(user_query)
```

### 6. Tool Performance Monitoring and Metrics

```python
import time
from dataclasses import dataclass
from typing import List, Dict
from statistics import mean, median

@dataclass
class ToolMetric:
    tool_name: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ToolPerformanceMonitor:
    def __init__(self):
        self.metrics: List[ToolMetric] = []
        self.performance_thresholds = {
            "WebSearchTool": 10.0,  # seconds
            "CodeInterpreterTool": 30.0,
            "FileSearchTool": 5.0,
            "ImageGenerationTool": 60.0
        }
    
    async def monitored_execution(self, agent: Agent, query: str) -> Dict[str, Any]:
        """Execute agent with comprehensive performance monitoring"""
        start_time = time.time()
        
        try:
            result = await Runner.run(agent, query)
            execution_time = time.time() - start_time
            
            # Record success metric
            self.metrics.append(ToolMetric(
                tool_name=agent.name,
                execution_time=execution_time,
                success=True
            ))
            
            # Check performance thresholds
            threshold = self.performance_thresholds.get(agent.name, 30.0)
            if execution_time > threshold:
                print(f"⚠️ Performance warning: {agent.name} took {execution_time:.2f}s (threshold: {threshold}s)")
            
            return {
                "result": result.final_output,
                "execution_time": execution_time,
                "success": True
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record failure metric
            self.metrics.append(ToolMetric(
                tool_name=agent.name,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            ))
            
            return {
                "result": f"Tool execution failed: {str(e)}",
                "execution_time": execution_time,
                "success": False
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.metrics:
            return {"message": "No metrics recorded"}
        
        # Overall statistics
        total_executions = len(self.metrics)
        successful_executions = sum(1 for m in self.metrics if m.success)
        success_rate = successful_executions / total_executions * 100
        
        # Execution time statistics
        execution_times = [m.execution_time for m in self.metrics if m.success]
        if execution_times:
            avg_time = mean(execution_times)
            median_time = median(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
        else:
            avg_time = median_time = max_time = min_time = 0
        
        # Tool-specific statistics
        tool_stats = {}
        for tool_name in set(m.tool_name for m in self.metrics):
            tool_metrics = [m for m in self.metrics if m.tool_name == tool_name]
            tool_successes = [m for m in tool_metrics if m.success]
            
            tool_stats[tool_name] = {
                "total_calls": len(tool_metrics),
                "successful_calls": len(tool_successes),
                "success_rate": len(tool_successes) / len(tool_metrics) * 100,
                "avg_execution_time": mean([m.execution_time for m in tool_successes]) if tool_successes else 0
            }
        
        return {
            "overview": {
                "total_executions": total_executions,
                "success_rate": f"{success_rate:.1f}%",
                "avg_execution_time": f"{avg_time:.2f}s",
                "median_execution_time": f"{median_time:.2f}s",
                "max_execution_time": f"{max_time:.2f}s",
                "min_execution_time": f"{min_time:.2f}s"
            },
            "tool_breakdown": tool_stats,
            "recent_failures": [
                {
                    "tool": m.tool_name,
                    "error": m.error_message,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in self.metrics[-10:] if not m.success
            ]
        }

# Usage example
async def monitored_workflow():
    monitor = ToolPerformanceMonitor()
    
    # Create various agents
    agents = [
        Agent(name="WebSearchTool", instructions="Search web", tools=[WebSearchTool()]),
        Agent(name="CodeInterpreterTool", instructions="Execute code", tools=[CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
        )])
    ]
    
    # Execute monitored workflows
    for agent in agents:
        result = await monitor.monitored_execution(
            agent, 
            "Perform your specialized task"
        )
        print(f"Agent {agent.name}: {result['success']} in {result['execution_time']:.2f}s")
    
    # Generate performance report
    report = monitor.get_performance_report()
    print("\n📊 Performance Report:")
    print(json.dumps(report, indent=2))
```

These advanced tool integration patterns enable building sophisticated, efficient, and robust AI agent systems with comprehensive monitoring, optimization, and error handling capabilities.