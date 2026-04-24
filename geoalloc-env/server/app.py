"""
FastAPI application for the GeoAlloc Environment.
"""
try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required. Run: uv sync") from e

import sys
import os
import json
# Ensure root is in PATH for Docker and local execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.models import Action, Observation
from server.geoalloc_environment import GeoAllocEnvironment
from fastapi.middleware.cors import CORSMiddleware

app = create_app(
    GeoAllocEnvironment,
    Action,
    Observation,
    env_name="geoalloc",
    max_concurrent_envs=1,
)

@app.get("/countries")
async def get_countries():
    file_path = os.path.join(os.path.dirname(__file__), "countries.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

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
