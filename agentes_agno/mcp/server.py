import os
import sys
from mcp.server.fastmcp import FastMCP
from agentes_agno import gerar_backend

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default

transport = os.getenv("MCP_TRANSPORT", "stdio")
host = os.getenv("FASTMCP_HOST", "127.0.0.1")
port = _env_int("FASTMCP_PORT", 8001)

mcp = FastMCP("agno", host=host, port=port)

@mcp.tool()
def gerar_backend_tool(tarefa: str):
    return gerar_backend(tarefa)

if __name__ == "__main__":
    if transport == "stdio":
        print("MCP (stdio) iniciado e aguardando um cliente MCP...", file=sys.stderr, flush=True)
    elif transport == "sse":
        print(f"MCP (sse) em http://{host}:{port}/sse", file=sys.stderr, flush=True)
    elif transport == "streamable-http":
        print(f"MCP (streamable-http) em http://{host}:{port}/mcp", file=sys.stderr, flush=True)
    mcp.run(
        transport=transport,
        mount_path=os.getenv("MCP_MOUNT_PATH"),
    )
