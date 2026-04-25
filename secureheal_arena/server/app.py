"""
secureheal_arena/server/app.py
───────────────────────────────
FastAPI application for the SecureHeal Arena environment.

Exposes the environment over HTTP and WebSocket endpoints,
compatible with OpenEnv clients and MCPToolClient.

Usage:
    # Development (with auto-reload):
    uvicorn secureheal_arena.server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn secureheal_arena.server.app:app --host 0.0.0.0 --port 8000 --workers 4
"""

import os

# Support both in-repo and standalone imports
try:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from .secureheal_environment import SecureHealEnvironment
except ImportError:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from server.secureheal_environment import SecureHealEnvironment

# Create the app
max_concurrent = int(os.getenv("MAX_CONCURRENT_ENVS", "8"))

app = create_app(
    SecureHealEnvironment,
    CallToolAction,
    CallToolObservation,
    env_name="secureheal_arena",
    max_concurrent_envs=max_concurrent,
)


def main():
    """Entry point for direct execution.

    Run with:
        python -m secureheal_arena.server.app
        uv run --project . server
        openenv serve secureheal_arena
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
