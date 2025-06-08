from agents import (
    WebSearchTool, CodeInterpreterTool,
    #FileSearchTool, 
    # ImageGenerationTool,
    #LocalShellTool
)
import os

def get_all_tools():
    """Get all available OpenAI tools"""
    return [
        WebSearchTool(),
        # FileSearchTool(
        #     vector_store_ids=[os.getenv("VECTOR_STORE_ID", "default")],
        #     max_num_results=5
        # ),
        CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
        ),
        #LocalShellTool(executor="docker")
        # ImageGenerationTool(
        #     tool_config={"type": "image_generation", "quality": "high"}
        # )
    ]

def get_tools_by_type(tool_types: list):
    """Get specific tools by type"""
    all_tools = {
        "web_search": WebSearchTool(),
        # "file_search": FileSearchTool(
        #     vector_store_ids=[os.getenv("VECTOR_STORE_ID", "default")],
        #     max_num_results=5
        # ),
        "code_interpreter": CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
        ),
        # "image_generation": ImageGenerationTool(
        #     tool_config={"type": "image_generation", "quality": "standard"}
        # ),
        # "local_shell": LocalShellTool(executor="docker")
    }
    
    return [all_tools[tool_type] for tool_type in tool_types if tool_type in all_tools]

def get_safe_tools():
    """Get production-safe tools (excludes local_shell)"""
    return [
        WebSearchTool(),
        CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
        ),
        # ImageGenerationTool(
        #     tool_config={"type": "image_generation", "quality": "high"}
        # )
    ]