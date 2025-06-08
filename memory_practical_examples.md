# OpenAI Agents - Practical Examples and Implementation Guide

## Complete Example Implementations

### 1. Message Filter with Streaming Handoffs

**Core Pattern**: Dynamic handoff with message filtering and streaming
```python
from agents import Agent, Runner, handoff
from agents.handoff_filters import HandoffInputData, handoff_filters

# Define message filter function
def spanish_handoff_message_filter(handoff_message_data: HandoffInputData) -> HandoffInputData:
    # Remove tool-related messages from history
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)
    
    # Remove first two items from conversation history
    history = tuple(handoff_message_data.input_history[2:])
    
    return HandoffInputData(
        input_history=history,
        pre_handoff_items=tuple(handoff_message_data.pre_handoff_items),
        new_items=tuple(handoff_message_data.new_items)
    )

# Agent configuration with filtered handoffs
spanish_agent = Agent(
    name="Spanish Assistant", 
    instructions="You only speak Spanish and are extremely concise.",
    handoff_description="A Spanish-speaking assistant for Spanish queries."
)

second_agent = Agent(
    name="Assistant",
    instructions="Be helpful. If user speaks Spanish, handoff to Spanish assistant.",
    handoffs=[handoff(spanish_agent, input_filter=spanish_handoff_message_filter)]
)

# Streaming handoff execution
async def streaming_handoff_workflow():
    # Build conversation history
    result = await Runner.run(first_agent, "Hi, my name is Sora.")
    result = await Runner.run(
        first_agent, 
        input=result.to_input_list() + [
            {"content": "Generate a random number", "role": "user"}
        ]
    )
    
    # Stream with handoff potential
    stream_result = Runner.run_streamed(
        second_agent,
        input=result.to_input_list() + [
            {"content": "Hola, ¿cómo estás?", "role": "user"}
        ]
    )
    
    # Process streaming events
    async for event in stream_result.stream_events():
        if event.type == "raw_response_event":
            if hasattr(event.data, 'delta') and event.data.delta:
                print(event.data.delta, end="")
```

**Key Features**:
- Message filtering to clean handoff context
- Streaming with handoff detection
- Conditional handoff based on language detection
- History management across agent transitions

### 2. Financial Research Agent - Multi-Agent Research System

**Architecture**: 5-stage research workflow with specialized agents
```python
# Stage 1: Planning Agent
planner_agent = Agent(
    name="ResearchPlanner",
    instructions="""
    Generate comprehensive search terms for financial research.
    Break down company analysis into key research areas:
    - Financial performance
    - Market position  
    - Risk factors
    - Growth prospects
    """,
    tools=[web_search_tool]
)

# Stage 2: Search Coordinator
search_agent = Agent(
    name="SearchCoordinator", 
    instructions="Execute searches and organize information by topic",
    tools=[web_search_tool, document_retrieval_tool]
)

# Stage 3: Specialist Sub-Analysts (as tools)
def create_analyst_tool(specialist_agent, tool_name, description):
    async def analyst_tool(data: str) -> str:
        """Execute specialized analysis"""
        result = await Runner.run(specialist_agent, data)
        return result.final_output
    
    analyst_tool.__name__ = tool_name
    analyst_tool.__doc__ = description
    return analyst_tool

# Fundamentals analyst
fundamentals_analyst = Agent(
    name="FundamentalsAnalyst",
    instructions="Analyze financial fundamentals, ratios, and performance metrics"
)

# Risk analyst  
risk_analyst = Agent(
    name="RiskAnalyst",
    instructions="Assess risk factors, market risks, and regulatory concerns"
)

# Create analyst tools
fundamentals_tool = create_analyst_tool(
    fundamentals_analyst,
    "fundamentals_analysis",
    "Perform fundamental financial analysis"
)

risk_tool = create_analyst_tool(
    risk_analyst, 
    "risk_analysis",
    "Assess investment risks and concerns"
)

# Stage 4: Writer Agent (synthesis)
writer_agent = Agent(
    name="FinancialWriter",
    instructions="""
    Act as senior financial analyst. Synthesize research into comprehensive report.
    Include:
    - Executive summary
    - Key findings
    - Specialist analysis integration
    - Follow-up research questions
    
    Use markdown formatting for professional presentation.
    """,
    tools=[fundamentals_tool, risk_tool]
)

# Stage 5: Verification Agent
verifier_agent = Agent(
    name="ReportVerifier",
    instructions="Audit report for consistency, accuracy, and completeness"
)

# Complete research workflow
async def financial_research_workflow(company_query):
    # Stage 1: Planning
    plan_result = await Runner.run(planner_agent, company_query)
    search_terms = plan_result.final_output
    
    # Stage 2: Search execution
    search_result = await Runner.run(
        search_agent, 
        f"Execute searches for: {search_terms}"
    )
    
    # Stage 3: Writer synthesis (calls specialist tools)
    report_result = await Runner.run(
        writer_agent,
        f"Research data: {search_result.final_output}\nCompany: {company_query}"
    )
    
    # Stage 4: Verification
    verified_result = await Runner.run(
        verifier_agent,
        f"Verify this report: {report_result.final_output}"
    )
    
    return {
        "plan": plan_result.final_output,
        "research_data": search_result.final_output, 
        "report": report_result.final_output,
        "verification": verified_result.final_output
    }
```

**Key Patterns**:
- Agents as callable tools for inline analysis
- Multi-stage workflow with clear separation of concerns
- Specialist agents for domain expertise
- Verification stage for quality assurance
- Markdown report generation

### 3. Portfolio Manager - Hub-and-Spoke Architecture

**Pattern**: Central coordinator with specialist agents
```python
# Specialist agents for different analysis types
macro_agent = Agent(
    name="MacroAnalyst",
    instructions="Analyze macroeconomic factors affecting investments",
    tools=[web_search_tool, economic_data_tool]
)

fundamental_agent = Agent(
    name="FundamentalAnalyst", 
    instructions="Perform fundamental company analysis",
    tools=[financial_data_tool, earnings_tool]
)

quant_agent = Agent(
    name="QuantAnalyst",
    instructions="Perform quantitative analysis and modeling",
    tools=[code_interpreter, data_analysis_tool]
)

# Create agent tools for portfolio manager
def create_specialist_tool(agent, name, description):
    async def specialist_analysis(query: str) -> str:
        result = await Runner.run(agent, query)
        return f"{name} Analysis:\n{result.final_output}"
    
    specialist_analysis.__name__ = name
    specialist_analysis.__doc__ = description
    return specialist_analysis

# Portfolio manager with all specialist tools
portfolio_manager = Agent(
    name="PortfolioManager",
    instructions="""
    Coordinate comprehensive investment analysis using specialist tools:
    
    1. Use macro_analysis for economic context
    2. Use fundamental_analysis for company specifics  
    3. Use quant_analysis for quantitative insights
    4. Synthesize all analyses into investment recommendation
    
    Always use multiple specialists for complete analysis.
    """,
    tools=[
        create_specialist_tool(macro_agent, "macro_analysis", "Macroeconomic analysis"),
        create_specialist_tool(fundamental_agent, "fundamental_analysis", "Fundamental analysis"),
        create_specialist_tool(quant_agent, "quant_analysis", "Quantitative analysis"),
        web_search_tool,
        code_interpreter
    ]
)

# Execution
async def portfolio_analysis(investment_query):
    result = await Runner.run(portfolio_manager, investment_query)
    return result.final_output
```

### 4. Advanced Handoff Patterns

**Pattern**: Conditional routing with context preservation
```python
# Context-aware routing
class SmartRoutingSystem:
    def __init__(self):
        self.specialists = {
            "technical": technical_analyst,
            "fundamental": fundamental_analyst,
            "sentiment": sentiment_analyst,
            "risk": risk_analyst
        }
    
    async def smart_route(self, query, user_context=None):
        # Routing agent with context awareness
        router = Agent(
            name="SmartRouter",
            instructions=f"""
            Route this query to the most appropriate specialist:
            
            Query: {query}
            User Context: {user_context or "No context"}
            
            Available specialists:
            - technical: Technical analysis and chart patterns
            - fundamental: Company fundamentals and financials
            - sentiment: Market sentiment and news analysis  
            - risk: Risk assessment and management
            
            Return only the specialist name.
            """
        )
        
        routing_result = await Runner.run(router, query)
        specialist_name = routing_result.final_output.strip().lower()
        
        if specialist_name in self.specialists:
            specialist = self.specialists[specialist_name]
            result = await Runner.run(specialist, query)
            return {
                "routed_to": specialist_name,
                "analysis": result.final_output
            }
        else:
            # Fallback to general analysis
            fallback = Agent(
                name="GeneralAnalyst",
                instructions="Provide general financial analysis"
            )
            result = await Runner.run(fallback, query)
            return {
                "routed_to": "general_fallback", 
                "analysis": result.final_output
            }

# Usage
routing_system = SmartRoutingSystem()
result = await routing_system.smart_route(
    "What's the RSI for AAPL?",
    user_context="Day trader focused on technical indicators"
)
```

### 5. Parallel Processing with Synthesis

**Pattern**: Parallel execution with result aggregation
```python
async def parallel_research_workflow(company_symbol):
    # Define parallel research tasks
    research_tasks = [
        ("earnings_analysis", f"Analyze recent earnings for {company_symbol}"),
        ("competitor_analysis", f"Compare {company_symbol} with competitors"),
        ("news_sentiment", f"Analyze recent news sentiment for {company_symbol}"),
        ("technical_analysis", f"Technical chart analysis for {company_symbol}")
    ]
    
    # Execute all tasks in parallel
    async def execute_task(task_name, task_query):
        agent = Agent(
            name=f"{task_name.title()}Agent",
            instructions=f"Perform {task_name.replace('_', ' ')} analysis",
            tools=[web_search_tool, financial_data_tool]
        )
        result = await Runner.run(agent, task_query)
        return task_name, result.final_output
    
    # Run all tasks concurrently
    parallel_results = await asyncio.gather(*[
        execute_task(name, query) for name, query in research_tasks
    ])
    
    # Synthesize results
    synthesis_input = "\\n\\n".join([
        f"{name.replace('_', ' ').title()}:\\n{result}"
        for name, result in parallel_results
    ])
    
    synthesizer = Agent(
        name="ResearchSynthesizer",
        instructions="""
        Synthesize multiple research analyses into unified investment thesis.
        Identify:
        - Key themes across analyses
        - Conflicting signals
        - Overall investment recommendation
        - Risk factors
        """
    )
    
    synthesis_result = await Runner.run(synthesizer, synthesis_input)
    
    return {
        "individual_analyses": dict(parallel_results),
        "synthesis": synthesis_result.final_output
    }
```

## Best Practices from Examples

### 1. Agent Specialization
- Create focused agents with specific expertise
- Use clear, domain-specific instructions
- Provide relevant tools for each agent's domain

### 2. Workflow Orchestration
- Break complex tasks into discrete stages
- Use handoffs for sequential processing
- Use agents-as-tools for parallel coordination
- Implement verification stages for quality

### 3. Context Management
- Use message filters to clean handoff context
- Preserve relevant conversation history
- Pass structured context between agents
- Implement state management for complex workflows

### 4. Error Handling and Fallbacks
- Implement fallback agents for error scenarios
- Use retry mechanisms with context updates
- Provide graceful degradation options
- Monitor and log agent interactions

### 5. Performance Optimization
- Cache agent results when appropriate
- Use parallel execution for independent tasks
- Implement connection pooling for external tools
- Monitor execution times and optimize bottlenecks

These patterns provide comprehensive coverage for implementing sophisticated multi-agent systems with the OpenAI Agents SDK.