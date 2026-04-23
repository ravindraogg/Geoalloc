"""
FastAPI application for the GeoAlloc Environment.
"""
try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required. Run: uv sync") from e

import sys
import os
# Ensure root is in PATH for Docker and local execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models import Action, Observation
    from server.geoalloc_environment import GeoAllocEnvironment
except (ImportError, ModuleNotFoundError):
    from ..models import Action, Observation
    from .geoalloc_environment import GeoAllocEnvironment

from fastapi.middleware.cors import CORSMiddleware

app = create_app(
    GeoAllocEnvironment,
    Action,
    Observation,
    env_name="geoalloc",
    max_concurrent_envs=1,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    import uvicorn
    # Use the string import path to ensure uvicorn can find the app in mono-mode
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
