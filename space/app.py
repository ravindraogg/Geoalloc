"""
SecureHeal Agent — HuggingFace Space FastAPI Server
────────────────────────────────────────────────────
Loads the trained model at startup, caches it, and exposes a FastAPI
endpoint that takes application code (text or file upload) → runs the
SecureHeal agent → finds vulnerabilities → suggests fixes.

Deploy to HF Spaces with GPU (T4).
"""

import os
import json
import re
import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from transformers import pipeline as hf_pipeline

# ────────────────────── Model Cache ──────────────────────────

MODEL_ID = os.environ.get("MODEL_ID", "Nitesh-Reddy/secureheal-agent-v2")
PIPE = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global PIPE
    print(f"🔄 Loading model: {MODEL_ID}")
    PIPE = hf_pipeline(
        "text-generation",
        model=MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    print(f"✅ Model loaded and cached!")
    yield


# ────────────────────── FastAPI App ──────────────────────────

app = FastAPI(
    title="SecureHeal Agent API",
    description="Autonomous SRE & Security agent — scans code, finds vulnerabilities, suggests fixes",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────── Models ───────────────────────────────

class ScanRequest(BaseModel):
    code: str
    context: Optional[str] = "web application"
    max_tokens: Optional[int] = 512

class ToolCall(BaseModel):
    tool: str
    args: dict

class VulnerabilityReport(BaseModel):
    vulnerabilities_found: bool
    tool_calls: List[ToolCall]
    analysis: str
    filename: Optional[str] = None

class AgentRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 512

class AgentResponse(BaseModel):
    response: str
    tool_calls: List[ToolCall]


# ────────────────────── Helper ───────────────────────────────

def parse_tool_calls(text: str) -> List[ToolCall]:
    calls = []
    pattern = r'<tool_call>\s*(\w+)\((\{.*?\})\)\s*</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)
    for tool_name, args_str in matches:
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {"raw": args_str}
        calls.append(ToolCall(tool=tool_name, args=args))
    if not calls:
        valid_tools = [
            "scan_code", "simulate_attack", "apply_patch", "run_tests",
            "restart_service", "clean_data", "reallocate_resources", "classify_issue",
        ]
        for tool in valid_tools:
            if tool in text.lower():
                calls.append(ToolCall(tool=tool, args={}))
    return calls


def run_agent(code: str, context: str = "web application", max_tokens: int = 512) -> str:
    """Run the SecureHeal agent on the given code."""
    prompt = (
        f"You are an autonomous SRE and Security agent. "
        f"Analyze the following {context} code for vulnerabilities. "
        f"Use scan_code, simulate_attack, apply_patch, run_tests to analyze and fix. "
        f'Output each action as <tool_call>tool_name({{"param": "value"}})</tool_call>. '
        f"End with DONE when finished.\n\n"
        f"Code to analyze:\n```\n{code}\n```"
    )
    messages = [{"role": "user", "content": prompt}]
    output = PIPE(messages, max_new_tokens=max_tokens, do_sample=True, temperature=0.7)
    return output[0]["generated_text"][-1]["content"]


# ────────────────────── Endpoints ────────────────────────────

import sys
import gradio as gr

# Add parent directory to path to import app and secureheal_arena
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from app import create_demo
    demo = create_demo()
    app = gr.mount_gradio_app(app, demo, path="/")
except Exception as e:
    print(f"Error mounting Gradio app: {e}")


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": PIPE is not None, "model": MODEL_ID}


@app.post("/scan", response_model=VulnerabilityReport)
async def scan_code_json(request: ScanRequest):
    """Scan code for vulnerabilities (JSON body with code string)."""
    if not PIPE:
        raise HTTPException(503, "Model still loading")

    response_text = run_agent(request.code, request.context, request.max_tokens)
    tool_calls = parse_tool_calls(response_text)

    return VulnerabilityReport(
        vulnerabilities_found=len(tool_calls) > 0,
        tool_calls=tool_calls,
        analysis=response_text,
    )


@app.post("/scan/file", response_model=VulnerabilityReport)
async def scan_code_file(
    file: UploadFile = File(..., description="Source code file to scan"),
    context: str = Form("web application", description="What kind of app (e.g. flask, django, express)"),
    max_tokens: int = Form(512, description="Max response tokens"),
):
    """
    Upload a source code file for vulnerability scanning.
    Supports .py, .js, .ts, .java, .go, .rb, .php, etc.
    """
    if not PIPE:
        raise HTTPException(503, "Model still loading")

    # Read file content
    content = await file.read()
    try:
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be a text/source code file")

    # Truncate very long files to fit model context
    if len(code) > 8000:
        code = code[:8000] + "\n\n# ... (truncated, file too large)"

    response_text = run_agent(code, context, max_tokens)
    tool_calls = parse_tool_calls(response_text)

    return VulnerabilityReport(
        vulnerabilities_found=len(tool_calls) > 0,
        tool_calls=tool_calls,
        analysis=response_text,
        filename=file.filename,
    )


@app.post("/agent", response_model=AgentResponse)
async def agent_prompt(request: AgentRequest):
    """Send a free-form prompt to the SecureHeal agent."""
    if not PIPE:
        raise HTTPException(503, "Model still loading")

    messages = [{"role": "user", "content": request.prompt}]
    output = PIPE(messages, max_new_tokens=request.max_tokens, do_sample=True, temperature=0.7)
    response_text = output[0]["generated_text"][-1]["content"]
    tool_calls = parse_tool_calls(response_text)

    return AgentResponse(response=response_text, tool_calls=tool_calls)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
