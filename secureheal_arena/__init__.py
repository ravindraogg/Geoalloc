"""
SecureHeal Arena — A merged RL environment for cybersecurity + system recovery.

Combines vulnerability detection/patching (SecureCode Arena X) with autonomous
system recovery (DataHeal Arena) in a single long-horizon RL episode.

Example:
    >>> from secureheal_arena import SecureHealEnv
    >>>
    >>> with SecureHealEnv(base_url="http://localhost:8000") as env:
    ...     env.reset(seed=42)
    ...     tools = env.list_tools()
    ...     result = env.call_tool("scan_code")
    ...     print(result)
"""

# Re-export MCP types for convenience
from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction

from .client import SecureHealEnv

__all__ = ["SecureHealEnv", "CallToolAction", "ListToolsAction"]
