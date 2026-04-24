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
import subprocess
from fastapi import BackgroundTasks
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

@app.post("/train")
async def trigger_training(background_tasks: BackgroundTasks):
    """
    Triggers the GRPO training loop as a background process on the HF GPU.
    """
    def run_training():
        env_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        train_script = os.path.join(env_dir, "train.py")
        print(f"[Cloud-Train] Starting background training: {train_script}")
        # Run using the same python interpreter (which has GPU access in the Space)
        subprocess.run([sys.executable, train_script], cwd=env_dir)

    background_tasks.add_task(run_training)
    return {"status": "Training initiated on Hugging Face Cloud", "method": "GRPO", "device": "GPU-Remote"}

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
