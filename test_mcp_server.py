import datetime
import logging

# Attempt to import FastMCP. Users might need to install mcp-server-framework
# pip install mcp-server-framework
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: FastMCP not found. Please install mcp-server-framework: pip install mcp-server-framework")
    exit(1)

# Configure basic logging for the server
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Create FastMCP server instance ---
mcp_server = FastMCP(
    name="MyLocalTestServer",
    version="0.1.0",
    description="A local test MCP server for agent integration."
)

# --- Define Tools ---
@mcp_server.tool()
def echo(message: str) -> str:
    """Echoes the input message back to the caller."""
    logger.info(f"Tool 'echo' called with message: '{message}'")
    return message

@mcp_server.tool()
def add(a: int, b: int) -> int:
    """Adds two integers and returns the sum."""
    logger.info(f"Tool 'add' called with a={a}, b={b}")
    return a + b

@mcp_server.tool()
def get_server_time() -> str:
    """Returns the current UTC date and time of the server."""
    logger.info(f"Tool 'get_server_time' called")
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return now_utc

# --- Main execution block to run the server ---
if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8000  # Default port for FastMCP's streamable-http often is 8000
    path = "/mcp"   # Default path for FastMCP's streamable-http

    logger.info(f"Starting MyLocalTestServer (Streamable HTTP)...")
    logger.info(f"MCP Endpoint will be available at: http://{host}:{port}{path}")
    logger.info("Available tools: echo, add, get_server_time")
    logger.info("Press Ctrl+C to stop the server.")

    try:
        # FastMCP's run method with streamable-http transport typically uses uvicorn.
        # It should handle host, port, and path internally based on its defaults
        # or allow overriding them. The example client connected to http://localhost:8000/mcp.
        mcp_server.run(
            transport="streamable-http",
            # host=host, # FastMCP might take these from uvicorn args or have its own way
            # port=port,
            # path=path # FastMCP usually sets a default path like /mcp or /
        )
    except Exception as e:
        logger.error(f"Failed to start the server: {e}", exc_info=True)
