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

app = create_app(
    GeoAllocEnvironment,
    Action,
    Observation,
    env_name="geoalloc",
    max_concurrent_envs=1,
)

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)
