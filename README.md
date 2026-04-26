---
title: SecureHeal Agent
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
license: mit
---

# SecureHeal Arena

> **A merged RL environment for cybersecurity vulnerability detection + autonomous system recovery.**

---

### [Live Environment (Hugging Face Space)](https://huggingface.co/spaces/ravindraog/secureheal-trainer)
### [Official Training Logs (Hugging Face Jobs)](https://huggingface.co/jobs/Nitesh-Reddy/69ecf914d70108f37acdeb13)

---

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Meta PyTorch](https://img.shields.io/badge/Meta%20PyTorch-Hackathon%202026-orange)](https://meta-pytorch.org/OpenEnv/)

## Important Links
- **Demo Video:** [YouTube Video]()
- **Training Logs:** [Hugging Face Jobs Training Run](https://huggingface.co/jobs/Nitesh-Reddy/69ecf914d70108f37acdeb13)
- **Training Evidence:** [Detailed Logs & Plots](TRAINING_EVIDENCE.md)
- **Pitch Deck:** [Presentation Slides](https://canva.link/9kw6rf18p5p9hhx)
- **Mini-Blog Post:** [Hugging Face Blog](hf_blog_post.md)
- **Training Code:** [Interactive Code](training/train_hf_job.py) 

## Problem

LLMs currently struggle with **multi-step cybersecurity tasks** — detecting vulnerabilities in running code, applying safe patches, and simultaneously stabilising degraded infrastructure. This environment trains an agent to handle the full lifecycle: **detect → exploit-verify → patch → test → stabilise**.

## How It Works

The agent operates inside a simulated live infrastructure where:
- Code is running with **active vulnerabilities** (SQL injection, XSS, path traversal)
- System anomalies cause **cascading failures** (memory spikes, disk pressure, data corruption)
- The agent must **detect, patch, and recover** within a single long-horizon RL episode

### Multi-Agent Debate Architecture
To ensure the highest accuracy of patches, our backend employs a 3-stage **Multi-Agent Debate Pipeline**:
1. **Agent Alpha (Recon Scanner):** Analyzes code to detect vulnerabilities.
2. **Agent Beta (Red Team Attacker):** Takes Alpha's report and writes an exploit to prove the vulnerability is real.
3. **Agent Alpha (Blue Team Defender):** Analyzes the exploit and writes a secure AST patch to neutralize the exact attack payload.

### VS Code IDE Dashboard & Remote CLI
- **Gradio Mission Control:** We built a high-fidelity VS Code-style IDE dashboard on Hugging Face to visualize the agent's multi-step decision process.
- **SecureHeal CLI:** Developers can use `secureheal_cli.py` to scan local files or remote GitHub repos. The CLI routes code to the Hugging Face Space for analysis and automatically applies the agent's secure patches locally.

### Training Evidence
For the hackathon judges, we have compiled a detailed **Training Evidence** document containing:
- **WandB Rewards & KL Curves**
- **Heuristic Reward Function Rubrics**
- **Before/After Performance Benchmarks**

**[View Training Evidence & Logs](TRAINING_EVIDENCE.md)**

### Episode Flow

```
reset() → inject vulnerability + anomaly → return observation

step() loop:
  1. Agent scans code (scan_code)
  2. Agent simulates exploit (simulate_attack) → sandbox executes
  3. Agent applies patch (apply_patch)
  4. Agent validates fix (run_tests) → RLVR reward computed
  5. Agent classifies anomaly (classify_issue)
  6. Agent stabilises services (restart_service / reallocate_resources)

Episode ends when: system stable + tests passing OR max_steps reached
```

### Available Tools (MCP)

| Tool | Source | Description |
|------|--------|-------------|
| `scan_code` | SecureCode | Scan for vulnerabilities |
| `simulate_attack` | SecureCode | Test if exploit succeeds |
| `apply_patch` | SecureCode | Apply a code fix |
| `run_tests` | SecureCode | Execute test suite |
| `restart_service` | DataHeal | Restart a failing service |
| `clean_data` | DataHeal | Clear corrupted data |
| `reallocate_resources` | DataHeal | Shift compute resources |
| `classify_issue` | DataHeal | Tag anomaly type |

### Multi-Tier Reward Architecture
To ensure the highest accuracy of patches, we use a hybrid reward strategy:

- **Tier 1: GRPO Heuristic Rewards** (Optimization phase): Enforces correct tool usage (40%), formatting (30%), reasoning (20%), and quality (10%).
- **Tier 2: Verifiable Rewards (RLVR)** (Validation phase):

| # | Signal | Type | Weight |
|---|--------|------|--------|
| R1 | Exploit blocked | RLVR — binary | 35% |
| R2 | Test suite pass rate | RLVR — continuous (0.0–1.0) | 35% |
| R3 | System stability restored | Semi-verifiable (latency delta) | 20% |
| R4 | Cascading failures halted | Heuristic (anomaly count) | 10% |

### Anti-Reward Hacking

- Sandboxed code execution (no file system, no network)
- 5-second hard timeout on every action
- Forbidden operations blocklist checked before reward computation
- Protected state — agent cannot mutate `test_pass_rate` directly

### Curriculum Learning

| Level | Vulnerability Types | Anomaly Types | Max Steps | Stochasticity |
|-------|-------------------|---------------|-----------|---------------|
| 1 | SQL Injection | Memory Spike | 8 | Deterministic |
| 2 | + XSS Stored | + Disk Pressure | 15 | Light |
| 3 | + Path Traversal | + Data Corruption, Network Partition | 25 | Full |

## Quick Start

### Install
```bash
pip install openenv-core
pip install -e .
```

### Run Tests Locally
```bash
python tests/test_environment_local.py
```

### Start Server
```bash
uvicorn secureheal_arena.server.app:app --host 0.0.0.0 --port 8000
```

### Use Client
```python
from secureheal_arena import SecureHealEnv

with SecureHealEnv(base_url="http://localhost:8000").sync() as env:
    env.reset(seed=42)
    
    # Discover tools
    tools = env.list_tools()
    print([t.name for t in tools])
    
    # Scan for vulnerabilities
    result = env.call_tool("scan_code")
    print(result)
    
    # Apply a patch
    result = env.call_tool("apply_patch", patch_code="...")
    print(result)
    
    # Run tests
    result = env.call_tool("run_tests")
    print(result)
```

## Project Structure

```
secureheal_arena/
├── __init__.py              # Package exports
├── models.py                # Action, Observation, State dataclasses
├── sandbox.py               # Isolated code execution engine
├── vulnerabilities.py       # Vulnerability catalogue (3 types)
├── anomalies.py             # Anomaly injection catalogue (4 types)
├── rewards.py               # 4 independent reward functions
├── client.py                # SecureHealEnv client
├── openenv.yaml             # OpenEnv manifest
└── server/
    ├── __init__.py
    ├── secureheal_environment.py  # Core reset/step/state logic
    ├── app.py                     # FastAPI application
    ├── requirements.txt           # Docker dependencies
    └── Dockerfile                 # Container image

tests/
└── test_environment_local.py  # Local integration tests

pyproject.toml               # Package configuration
```

## Training & Results

We used **TRL's GRPOTrainer** alongside **Unsloth** (QLoRA 4-bit) to train Qwen2.5-3B-Instruct on the SecureHeal Arena curriculum.

- **Trained Model:** [Nitesh-Reddy/secureheal-agent-v2](https://huggingface.co/Nitesh-Reddy/secureheal-agent-v2)
- **Peak Performance:** Best Reward of **4.141** (Step 170)

### Baseline vs. Trained Behavior
*   **Untrained Baseline:** Repeatedly outputs prose or invalid tool calls, causing system latency to skyrocket and cascading failures to overwhelm the service. Reward stays at `0.0`.
*   **Trained Agent:** Immediately uses `scan_code` followed by `simulate_attack`. After applying a verified patch, it proactively uses `restart_service` to stabilize the degraded system.

### Training Rewards
*As required by the hackathon, here are our training reward curves showing convergence.*

![Total Reward](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/r-curve.jpeg)
*Figure 1: Mean group reward per episode. The **untrained baseline (flat line at reward=2.7)** was quickly surpassed as the agent mastered tool XML formatting and security reasoning.*

![Clipped Ratio](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/clipped-ratio.jpeg)
*Figure 2: The Clipped Ratio diagnostic. The drop from 98.75% to 0.63% proves the policy stabilized and "locked in" its learning without catastrophic forgetting.*

![Performance Comparison](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/performance_comparison.png)
*Figure 3: Quantitative improvement after GRPO training across all 4 key metrics.*

See `training/train.py` for the GRPO training pipeline and `TRAINING_EVIDENCE.md` for the full technical breakdown.

## Team

Built for the **Meta PyTorch OpenEnv Hackathon India 2026**.

---

*SecureHeal Arena — because the best defence is a trained offence.*
