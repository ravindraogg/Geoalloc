"""
secureheal_arena/client.py
───────────────────────────
Client for connecting to a running SecureHeal Arena server.

Extends MCPToolClient to provide tool-calling style interactions for
all eight SecureHeal actions.

Example:
    >>> from secureheal_arena import SecureHealEnv
    >>>
    >>> with SecureHealEnv(base_url="http://localhost:8000") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     print([t.name for t in tools])
    ...     result = env.call_tool("scan_code")
    ...     print(result)
"""

from openenv.core.mcp_client import MCPToolClient


class SecureHealEnv(MCPToolClient):
    """Client for the SecureHeal Arena environment.

    Inherits all functionality from MCPToolClient:
      - list_tools()              — discover available tools
      - call_tool(name, **kwargs) — call a tool by name
      - reset(**kwargs)           — reset the environment
      - step(action)              — execute an action (advanced use)

    Available tools:
      - scan_code             — scan for vulnerabilities
      - simulate_attack       — simulate an exploit
      - apply_patch           — apply a code fix
      - run_tests             — execute test suite
      - restart_service       — restart a failing service
      - clean_data            — clear corrupted data
      - reallocate_resources  — shift compute resources
      - classify_issue        — classify anomaly type

    Example with Docker:
        >>> env = SecureHealEnv.from_docker_image("secureheal-arena:latest")
        >>> try:
        ...     env.reset()
        ...     result = env.call_tool("scan_code")
        ... finally:
        ...     env.close()

    Example with HuggingFace Space:
        >>> env = SecureHealEnv.from_env("your-username/secureheal-arena")
        >>> try:
        ...     env.reset(seed=42)
        ...     tools = env.list_tools()
        ...     result = env.call_tool("scan_code")
        ... finally:
        ...     env.close()
    """

    pass  # MCPToolClient provides all needed functionality
