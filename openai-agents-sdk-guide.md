# OpenAI Agents SDK: Building Multi-Agent MCP-Enabled Applications

## Table of Contents

1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Getting Started](#getting-started)
4. [Multi-Agent Patterns](#multi-agent-patterns)
5. [MCP Integration](#mcp-integration)
6. [Deployment Strategies](#deployment-strategies)
   - [Kubernetes Deployment](#kubernetes-deployment)
   - [Serverless Deployment](#serverless-deployment)
7. [Best Practices](#best-practices)
8. [Advanced Topics](#advanced-topics)
9. [Conclusion](#conclusion)

## Introduction

The OpenAI Agents SDK is a lightweight yet powerful framework for building multi-agent workflows. It is provider-agnostic, supporting the OpenAI Responses and Chat Completions APIs, as well as 100+ other LLMs. This guide will help you understand how to use the SDK to develop multi-agent MCP-enabled applications that can be deployed on Kubernetes or as serverless functions.

## Core Concepts

The OpenAI Agents SDK is built around four key concepts:

1. **Agents**: LLMs configured with instructions, tools, guardrails, and handoffs
2. **Handoffs**: A specialized tool call used by the Agents SDK for transferring control between agents
3. **Guardrails**: Configurable safety checks for input and output validation
4. **Tracing**: Built-in tracking of agent runs, allowing you to view, debug and optimize your workflows

## Getting Started

### Installation

```bash
pip install openai-agents
```

For voice support:

```bash
pip install 'openai-agents[voice]'
```

### Basic Example

Here's a simple "Hello World" example to get started:

```python
import asyncio

from agents import Agent, Runner

async def main():
    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
    )

    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)
    # Function calls itself,
    # Looping in smaller pieces,
    # Endless by design.

if __name__ == "__main__":
    asyncio.run(main())
```

## Multi-Agent Patterns

The OpenAI Agents SDK supports several patterns for building multi-agent systems:

### 1. Routing/Handoffs Pattern

This pattern allows an agent to delegate tasks to other agents based on specific criteria:

```python
import asyncio
import uuid

from openai.types.responses import ResponseContentPartDoneEvent, ResponseTextDeltaEvent

from agents import Agent, RawResponsesStreamEvent, Runner, TResponseInputItem, trace

french_agent = Agent(
    name="french_agent",
    instructions="You only speak French",
)

spanish_agent = Agent(
    name="spanish_agent",
    instructions="You only speak Spanish",
)

english_agent = Agent(
    name="english_agent",
    instructions="You only speak English",
)

triage_agent = Agent(
    name="triage_agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[french_agent, spanish_agent, english_agent],
)

async def main():
    # Create an ID for this conversation to link each trace
    conversation_id = str(uuid.uuid4().hex[:16])

    msg = input("Hi! We speak French, Spanish and English. How can I help? ")
    agent = triage_agent
    inputs: list[TResponseInputItem] = [{"content": msg, "role": "user"}]

    while True:
        # Each conversation turn is a single trace
        with trace("Routing example", group_id=conversation_id):
            result = Runner.run_streamed(
                agent,
                input=inputs,
            )
            async for event in result.stream_events():
                if not isinstance(event, RawResponsesStreamEvent):
                    continue
                data = event.data
                if isinstance(data, ResponseTextDeltaEvent):
                    print(data.delta, end="", flush=True)
                elif isinstance(data, ResponseContentPartDoneEvent):
                    print("\n")

        inputs = result.to_input_list()
        print("\n")

        user_msg = input("Enter a message: ")
        inputs.append({"content": user_msg, "role": "user"})
        agent = result.current_agent

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Agents as Tools Pattern

This pattern allows agents to use other agents as tools:

```python
import asyncio

from agents import Agent, ItemHelpers, MessageOutputItem, Runner, trace

spanish_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
    handoff_description="An english to spanish translator",
)

french_agent = Agent(
    name="french_agent",
    instructions="You translate the user's message to French",
    handoff_description="An english to french translator",
)

italian_agent = Agent(
    name="italian_agent",
    instructions="You translate the user's message to Italian",
    handoff_description="An english to italian translator",
)

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=(
        "You are a translation agent. You use the tools given to you to translate."
        "If asked for multiple translations, you call the relevant tools in order."
        "You never translate on your own, you always use the provided tools."
    ),
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate the user's message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate the user's message to French",
        ),
        italian_agent.as_tool(
            tool_name="translate_to_italian",
            tool_description="Translate the user's message to Italian",
        ),
    ],
)

synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions="You inspect translations, correct them if needed, and produce a final concatenated response.",
)

async def main():
    msg = input("Hi! What would you like translated, and to which languages? ")

    # Run the entire orchestration in a single trace
    with trace("Orchestrator evaluator"):
        orchestrator_result = await Runner.run(orchestrator_agent, msg)

        for item in orchestrator_result.new_items:
            if isinstance(item, MessageOutputItem):
                text = ItemHelpers.text_message_output(item)
                if text:
                    print(f"  - Translation step: {text}")

        synthesizer_result = await Runner.run(
            synthesizer_agent, orchestrator_result.to_input_list()
        )

    print(f"\n\nFinal response:\n{synthesizer_result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Parallelization Pattern

This pattern allows running multiple agents in parallel and then selecting the best result:

```python
import asyncio

from agents import Agent, ItemHelpers, Runner, trace

spanish_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
)

translation_picker = Agent(
    name="translation_picker",
    instructions="You pick the best Spanish translation from the given options.",
)

async def main():
    msg = input("Hi! Enter a message, and we'll translate it to Spanish.\n\n")

    # Ensure the entire workflow is a single trace
    with trace("Parallel translation"):
        res_1, res_2, res_3 = await asyncio.gather(
            Runner.run(
                spanish_agent,
                msg,
            ),
            Runner.run(
                spanish_agent,
                msg,
            ),
            Runner.run(
                spanish_agent,
                msg,
            ),
        )

        outputs = [
            ItemHelpers.text_message_outputs(res_1.new_items),
            ItemHelpers.text_message_outputs(res_2.new_items),
            ItemHelpers.text_message_outputs(res_3.new_items),
        ]

        translations = "\n\n".join(outputs)
        print(f"\n\nTranslations:\n\n{translations}")

        best_translation = await Runner.run(
            translation_picker,
            f"Input: {msg}\n\nTranslations:\n{translations}",
        )

    print("\n\n-----")
    print(f"Best translation: {best_translation.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
```

## MCP Integration

The Model Context Protocol (MCP) allows agents to interact with external tools and services. The OpenAI Agents SDK provides built-in support for MCP through the `HostedMCPTool` and various MCP server implementations.

### Setting Up an MCP Server

The SDK supports different types of MCP servers:

1. **MCPServerStdio**: Communicates with an MCP server via stdin/stdout
2. **MCPServerSSE**: Communicates with an MCP server via Server-Sent Events (SSE)
3. **MCPServerStreamableHTTP**: Communicates with an MCP server via HTTP

Here's an example of using an MCP server with the filesystem MCP server:

```python
import asyncio
import os
import shutil

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio

async def run(mcp_server: MCPServer):
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to read the filesystem and answer questions based on those files.",
        mcp_servers=[mcp_server],
    )

    # List the files it can read
    message = "Read the files and list them."
    print(f"Running: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "sample_files")

    async with MCPServerStdio(
        name="Filesystem Server, via npx",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
        },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="MCP Filesystem Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            await run(server)

if __name__ == "__main__":
    # Let's make sure the user has npx installed
    if not shutil.which("npx"):
        raise RuntimeError("npx is not installed. Please install it with `npm install -g npx`.")

    asyncio.run(main())
```

### Creating Custom MCP Servers

You can create custom MCP servers by implementing the `MCPServer` abstract class:

```python
from agents.mcp import MCPServer

class CustomMCPServer(MCPServer):
    def __init__(self, name: str):
        super().__init__(cache_tools_list=True)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def connect(self):
        # Implementation for connecting to your server
        pass

    async def cleanup(self):
        # Implementation for cleaning up resources
        pass

    # Implement other required methods
```

## Deployment Strategies

### Kubernetes Deployment

To deploy multi-agent MCP-enabled applications on Kubernetes, you'll need to:

1. **Containerize your application**: Create a Docker image that includes your application code and dependencies.

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

2. **Create a Kubernetes deployment**: Define a Kubernetes deployment manifest for your application.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-app
  template:
    metadata:
      labels:
        app: agent-app
    spec:
      containers:
      - name: agent-app
        image: your-registry/agent-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-credentials
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

3. **Create a Kubernetes service**: Expose your application with a Kubernetes service.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: agent-app
spec:
  selector:
    app: agent-app
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

4. **Configure horizontal pod autoscaling**: Set up autoscaling based on CPU or memory usage.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

### Serverless Deployment

For serverless deployment, you can use services like AWS Lambda, Google Cloud Functions, or Azure Functions:

#### AWS Lambda Example

1. **Create a Lambda function handler**:

```python
import asyncio
import json
from agents import Agent, Runner

async def run_agent(event, context):
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )
    
    user_input = event.get('body', {}).get('message', '')
    
    result = await Runner.run(agent, user_input)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'response': result.final_output
        })
    }

def lambda_handler(event, context):
    return asyncio.run(run_agent(event, context))
```

2. **Deploy using AWS SAM**:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Resources:
  AgentFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: app.lambda_handler
      Runtime: python3.10
      Timeout: 30
      MemorySize: 1024
      Environment:
        Variables:
          OPENAI_API_KEY: !Ref OpenAIApiKey
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /agent
            Method: post

Parameters:
  OpenAIApiKey:
    Type: String
    NoEcho: true
```

## Best Practices

### 1. Agent Design

- **Single Responsibility**: Each agent should have a clear, focused responsibility
- **Clear Instructions**: Provide detailed instructions to guide agent behavior
- **Appropriate Tools**: Equip agents with the tools they need for their specific tasks
- **Effective Handoffs**: Design handoff patterns that make sense for your workflow

### 2. MCP Integration

- **Tool Caching**: Use `cache_tools_list=True` when appropriate to improve performance
- **Error Handling**: Implement proper error handling for MCP tool calls
- **Security**: Ensure MCP servers have appropriate access controls

### 3. Deployment

- **Resource Allocation**: Allocate appropriate CPU and memory resources
- **Scaling**: Implement autoscaling based on workload
- **Monitoring**: Set up monitoring and alerting for your deployed agents
- **Security**: Secure API keys and sensitive information using secrets management

### 4. Performance Optimization

- **Parallel Execution**: Use parallelization when appropriate
- **Caching**: Implement caching for expensive operations
- **Efficient Handoffs**: Minimize unnecessary handoffs between agents

## Advanced Topics

### Custom Model Providers

The OpenAI Agents SDK supports custom model providers, allowing you to use different LLMs:

```python
from agents import Agent, Model, ModelProvider, OpenAIChatCompletionsModel, RunConfig, Runner

class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        return OpenAIChatCompletionsModel(
            model=model_name or "your-model-name",
            openai_client=your_custom_client
        )

CUSTOM_MODEL_PROVIDER = CustomModelProvider()

agent = Agent(name="Assistant", instructions="You are a helpful assistant.")

result = await Runner.run(
    agent,
    "What's the weather in Tokyo?",
    run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
)
```

### Streaming Responses

For real-time interactions, you can stream responses from agents:

```python
result = Runner.run_streamed(
    agent,
    input=inputs,
)
async for event in result.stream_events():
    if not isinstance(event, RawResponsesStreamEvent):
        continue
    data = event.data
    if isinstance(data, ResponseTextDeltaEvent):
        print(data.delta, end="", flush=True)
    elif isinstance(data, ResponseContentPartDoneEvent):
        print("\n")
```

### Tracing and Debugging

The SDK provides built-in tracing capabilities:

```python
with trace("My workflow", group_id=conversation_id):
    result = await Runner.run(agent, input)
```

You can view traces in the OpenAI platform or use external tracing processors.

## Conclusion

The OpenAI Agents SDK provides a powerful framework for building multi-agent MCP-enabled applications. By following the patterns and best practices outlined in this guide, you can develop sophisticated agent systems that can be deployed on Kubernetes or as serverless functions.

The key advantages of the SDK include:

1. **Provider-agnostic**: Works with OpenAI and 100+ other LLMs
2. **Flexible architecture**: Supports various multi-agent patterns
3. **MCP integration**: Connects with external tools and services
4. **Built-in tracing**: Helps with debugging and optimization

By leveraging these capabilities, you can build complex, scalable agent systems that solve real-world problems.
