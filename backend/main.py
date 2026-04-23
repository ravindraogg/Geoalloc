from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import json

app = FastAPI(title="GeoAlloc Backend Bridge")

# Enable CORS for Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration: Point this to your Hugging Face Space URL
# Example: https://huggingface.co/spaces/your-username/geoalloc-env
HF_SPACE_URL = os.getenv("HF_SPACE_URL", "http://localhost:7860")

@app.get("/")
async def root():
    print(f"[Bridge] Status check. Targeting environment at: {HF_SPACE_URL}")
    return {"status": "operational", "bridge_to": HF_SPACE_URL}

@app.post("/reset")
async def reset_env(request: Request):
    print("[Bridge] Received /reset request")
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{HF_SPACE_URL}/reset", json=body, timeout=60.0)
            print(f"[Bridge] Reset successful: {response.status_code}")
            return response.json()
    except Exception as e:
        print(f"[Bridge] Reset ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
async def step_env(request: Request):
    print("[Bridge] Received /step request")
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{HF_SPACE_URL}/step", json=body, timeout=60.0)
            print(f"[Bridge] Step successful: {response.status_code}")
            return response.json()
    except Exception as e:
        print(f"[Bridge] Step ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
