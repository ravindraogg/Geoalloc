# SecureHeal Arena - API Reference

Complete reference for every endpoint exposed by the SecureHeal Agent backend on Hugging Face Spaces.

**Base URL:** `https://ravindraog-secureheal-trainer.hf.space`

---

## GET /health

Returns the current health status of the Space and whether the model is loaded.

**Request:**
```
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model": "Nitesh-Reddy/secureheal-agent-v2"
}
```

**When to use:** Call this before any scan request to confirm the Space is awake and the model is ready. If `model_loaded` is `false`, wait 1-2 minutes and retry.

---

## POST /scan

Scans a code snippet provided as a JSON body. Runs the full 3-agent debate pipeline (Alpha scanner, Beta attacker, Gamma defender) and returns the combined analysis along with any tool calls the agents produced.

**Request:**
```
POST /scan
Content-Type: application/json
```

**Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `code` | string | Yes | - | The source code to analyze |
| `context` | string | No | `"web application"` | Describes the application type (e.g. "flask api", "express server") |
| `max_tokens` | integer | No | `512` | Maximum tokens for the model response |

**Example:**
```json
{
  "code": "cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")",
  "context": "flask api",
  "max_tokens": 512
}
```

**Response (200):**
```json
{
  "vulnerabilities_found": true,
  "tool_calls": [
    { "tool": "scan_code", "args": {} },
    { "tool": "simulate_attack", "args": { "payload": "1 OR 1=1" } },
    { "tool": "apply_patch", "args": { "patch_code": "cursor.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))" } }
  ],
  "analysis": "[AGENT ALPHA - RECON SCANNER]\n..."
}
```

**Error Codes:**
- `503` - Model is still loading. Retry after a short wait.

---

## POST /scan/file

Uploads a source code file for vulnerability scanning. This is what the SecureHeal CLI (`secureheal_cli.py`) calls under the hood. Supports `.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.php`, and more.

**Request:**
```
POST /scan/file
Content-Type: multipart/form-data
```

**Fields:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | file (binary) | Yes | - | The source code file to scan |
| `context` | string (form) | No | `"web application"` | Application type hint |
| `max_tokens` | integer (form) | No | `512` | Maximum tokens for the model response |

**Example (curl):**
```bash
curl -X POST https://ravindraog-secureheal-trainer.hf.space/scan/file \
  -F "file=@vulnerable_app.py" \
  -F "context=flask api" \
  -F "max_tokens=512"
```

**Response (200):**
```json
{
  "vulnerabilities_found": true,
  "tool_calls": [ ... ],
  "analysis": "...",
  "filename": "vulnerable_app.py"
}
```

**Notes:**
- Files larger than 8000 characters are automatically truncated to fit the model context window.
- The `filename` field in the response echoes back the uploaded file name.

**Error Codes:**
- `400` - File is not a valid text/source code file.
- `503` - Model is still loading.

---

## POST /agent

A free-form prompt endpoint. Send any text prompt to the SecureHeal agent and get back a raw response along with any parsed tool calls. This is useful for custom queries outside the standard scan workflow.

**Request:**
```
POST /agent
Content-Type: application/json
```

**Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Free-form text prompt for the agent |
| `max_tokens` | integer | No | `512` | Maximum tokens for the response |

**Example:**
```json
{
  "prompt": "Explain the OWASP Top 10 vulnerability categories and which ones apply to Python Flask apps.",
  "max_tokens": 256
}
```

**Response (200):**
```json
{
  "response": "The OWASP Top 10 covers...",
  "tool_calls": []
}
```

**Error Codes:**
- `503` - Model is still loading.

---

## GET / (Gradio Dashboard)

The root path serves the **VS Code-style Gradio IDE Dashboard**. This is the visual interface that judges and users see when they visit the Hugging Face Space directly. It is mounted as a Gradio app on top of the FastAPI backend.

**URL:** `https://ravindraog-secureheal-trainer.hf.space/`

This is not an API endpoint in the traditional sense. It renders the interactive web UI.

---

## Data Models

### VulnerabilityReport

Returned by `/scan` and `/scan/file`.

| Field | Type | Description |
|-------|------|-------------|
| `vulnerabilities_found` | boolean | Whether the agent detected any issues |
| `tool_calls` | array of ToolCall | Parsed tool calls from the agent output |
| `analysis` | string | Full text of the multi-agent debate log |
| `filename` | string or null | Original filename (only for `/scan/file`) |

### ToolCall

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Name of the tool called (e.g. `scan_code`, `apply_patch`) |
| `args` | object | Arguments passed to the tool |

### AgentResponse

Returned by `/agent`.

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | The agent's text response |
| `tool_calls` | array of ToolCall | Any tool calls parsed from the response |

---

## Rate Limits and Constraints

- The Hugging Face Space runs on a **T4 GPU** with limited concurrency.
- Each scan triggers three sequential model inferences (Alpha, Beta, Gamma), so expect response times of 30 to 90 seconds depending on code length.
- Files over 8000 characters are truncated.
- If the Space has been idle for a while, the first request will take longer because the model needs to load into GPU memory.

---

## Related Documentation

For a complete overview of the SecureHeal Arena project, please refer to:

- [README.md](README.md) - Project overview, architecture, and quick start guide.
- [TRAINING_EVIDENCE.md](TRAINING_EVIDENCE.md) - Training curves, reward architecture, and performance benchmarks.
- [project_context.md](project_context.md) - Detailed hackathon strategy and execution plan.
- [hf_blog_post.md](hf_blog_post.md) - Short blog post explaining the project.
- [secureheal_cli.py](secureheal_cli.py) - CLI source code that calls these endpoints.
- [training/train_hf_job.py](training/train_hf_job.py) - GRPO training script.

---
*Prepared for the Meta PyTorch OpenEnv Hackathon India 2026 by team codeXcreators.*
