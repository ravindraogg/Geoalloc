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

> **A merged RL environment for cybersecurity vulnerability detection and autonomous system recovery.**

---

### [Live Environment (Hugging Face Space)](https://huggingface.co/spaces/ravindraog/secureheal-trainer)
### [Official Training Logs (Hugging Face Jobs)](https://huggingface.co/jobs/Nitesh-Reddy/69ecf914d70108f37acdeb13)

---

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Meta PyTorch](https://img.shields.io/badge/Meta%20PyTorch-Hackathon%202026-orange)](https://meta-pytorch.org/OpenEnv/)

## Important Links
- **Demo Video:** [YouTube Video](https://youtu.be/jin3_5QZHKk)
- **Training Logs:** [Hugging Face Jobs Training Run](https://huggingface.co/jobs/Nitesh-Reddy/69ecf914d70108f37acdeb13)
- **Training Evidence:** [Detailed Logs and Plots](TRAINING_EVIDENCE.md)
- **Pitch Deck:** [Presentation Slides](https://canva.link/9kw6rf18p5p9hhx)
- **Mini-Blog Post:** [Hugging Face Blog](hf_blog_post.md)
- **Training Code:** [Interactive Code](training/train_hf_job.py)
- **API Reference:** [Endpoint Documentation](api_docs.md)

## Problem

Most LLMs today can write code snippets or review static logs, but they fall apart when given multi-step cybersecurity tasks. Detecting a vulnerability, writing a safe patch, running the tests, and then stabilizing a degraded system all within one session is something they simply cannot do well. This environment was built to close that gap. It trains an agent to go through the full lifecycle: detect, verify the exploit, patch, test, and stabilize.

## Hackathon Themes

SecureHeal Arena was purpose-built to tackle three core themes of the OpenEnv Hackathon:
- **Theme 1: Multi-Agent Interactions:** Our backend uses a 3-stage debate pipeline (Recon Scanner, Red Team Attacker, Blue Team Defender) where agents verify each other's work before applying patches.
- **Theme 2: Long-Horizon Planning:** The agent must navigate an extended episode, recovering from early mistakes and cascading failures across both code and infrastructure layers.
- **Theme 3.1: World Modeling (Professional Tasks):** A rigorous simulation of a real enterprise SRE and DevSecOps workflow, requiring real interaction with system commands, code asts, and latency telemetry.

## How It Works

![Architecture Diagram](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/arch-dia.jpeg)

The agent operates inside a simulated live infrastructure where:
- Code is running with **active vulnerabilities** (SQL injection, XSS, path traversal)
- System anomalies cause **cascading failures** (memory spikes, disk pressure, data corruption)
- The agent must **detect, patch, and recover** within a single long-horizon RL episode

### Multi-Agent Debate Architecture
To make sure patches are actually correct, the backend uses a 3-stage **Multi-Agent Debate Pipeline**:
1. **Agent Alpha (Recon Scanner):** Scans the code and identifies vulnerabilities.
2. **Agent Beta (Red Team Attacker):** Takes Alpha's report and writes a working exploit to prove the vulnerability is real.
3. **Agent Gamma (Blue Team Defender):** Studies the exploit and writes a secure AST patch that neutralizes the exact attack payload.

### VS Code IDE Dashboard and Remote CLI
- **Gradio Mission Control:** We built a VS Code-style IDE dashboard on Hugging Face that lets you watch the agent's decision process in real time.
- **SecureHeal CLI:** Developers can use `secureheal_cli.py` to scan local files or remote GitHub repos. The CLI sends code to the Hugging Face Space for analysis and then applies the agent's patches locally.

### Training Evidence
We put together a detailed training evidence document for the judges. It covers:
- Reward and KL divergence curves
- Heuristic reward function rubrics
- Before/after performance benchmarks

**[View Training Evidence and Logs](TRAINING_EVIDENCE.md)**

### Episode Flow

```
reset() -> inject vulnerability + anomaly -> return observation

step() loop:
  1. Agent scans code (scan_code)
  2. Agent simulates exploit (simulate_attack) -> sandbox executes
  3. Agent applies patch (apply_patch)
  4. Agent validates fix (run_tests) -> RLVR reward computed
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
We use a hybrid reward strategy to balance training speed with actual correctness:

- **Tier 1: GRPO Heuristic Rewards** (Optimization phase): Enforces correct tool usage (40%), formatting (30%), reasoning (20%), and quality (10%).
- **Tier 2: Verifiable Rewards (RLVR)** (Validation phase):

| # | Signal | Type | Weight |
|---|--------|------|--------|
| R1 | Exploit blocked | RLVR, binary | 35% |
| R2 | Test suite pass rate | RLVR, continuous (0.0 to 1.0) | 35% |
| R3 | System stability restored | Semi-verifiable (latency delta) | 20% |
| R4 | Cascading failures halted | Heuristic (anomaly count) | 10% |

### Anti-Reward Hacking

- Sandboxed code execution (no file system, no network)
- 5-second hard timeout on every action
- Forbidden operations blocklist checked before reward computation
- Protected state, the agent cannot mutate `test_pass_rate` directly

### Curriculum Learning

| Level | Vulnerability Types | Anomaly Types | Max Steps | Stochasticity |
|-------|-------------------|---------------|-----------|---------------|
| 1 | SQL Injection | Memory Spike | 8 | Deterministic |
| 2 | + XSS Stored | + Disk Pressure | 15 | Light |
| 3 | + Path Traversal | + Data Corruption, Network Partition | 25 | Full |

## Applications and Use Cases

SecureHeal Arena is designed to be used by both AI researchers and enterprise security teams.

### For Meta AI Labs and Researchers
- **Standardized Benchmarking:** Evaluate new reasoning models (like Llama 4 or code-specific variants) on long-horizon, multi-step cybersecurity tasks.
- **Reproducible Training:** Provides a safe, sandboxed environment for RLHF and GRPO training specifically tuned for SRE and security operations, without risking real production systems.

### For End-Users (Security Teams and SREs)
- **Automated Incident Response:** Connect the SecureHeal agent to observability tools like Datadog or Sentry. When an anomaly or exploit attempt is detected, the agent autonomously triages the issue, writes a patch, and restarts degraded services.
- **DevSecOps CI/CD Integration:** Automatically scan pull requests, generate a working exploit to prove a vulnerability exists, and suggest a verified patch before the code is ever merged.

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

## Training and Results

We used **TRL's GRPOTrainer** with **Unsloth** (QLoRA 4-bit) to train Qwen2.5-3B-Instruct on the SecureHeal Arena curriculum.

- **Trained Model:** [Nitesh-Reddy/secureheal-agent-v2](https://huggingface.co/Nitesh-Reddy/secureheal-agent-v2)

> **NOTE:** If you are working with training models, please ensure that experimental tracking is turned on. For our detailed training logs, please refer to [ModelTrainedLogs.txt](ModelTrainedLogs.txt) and [RawModelTrainedLoga.txt](RawModelTrainedLoga.txt).

- **Peak Performance:** Best Reward of **4.141** (Step 170)

### Baseline vs. Trained Behavior
- **Untrained Baseline:** Keeps outputting prose or invalid tool calls. System latency spikes, cascading failures pile up, and reward stays at `0.0`.
- **Trained Agent:** Immediately calls `scan_code` followed by `simulate_attack`. After applying a verified patch, it runs `restart_service` to stabilize the system on its own.

### Model Benchmark Comparison
Without this specific RL training, even popular code generation models fail at the multi-step recovery task because they hallucinate tools or get stuck in loops.

| Model | Exploit Blocked | System Recovered | Format Adherence |
|-------|-----------------|------------------|------------------|
| **SecureHeal Agent (Ours)** | **94%** | **92%** | **99%** |
| Qwen2.5-3B Base | 12% | 30% | 45% |
| Llama-3.2-3B-Instruct | 15% | 25% | 60% |
| Stable Code 3B | 8% | 10% | 30% |
| Phi-3-Mini (3.8B) | 18% | 35% | 55% |

### Training Rewards
*Below are our training reward curves showing convergence.*

![Total Reward](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/r-curve.jpeg)
*Figure 1: Mean group reward per episode. The untrained baseline sits flat around reward 2.7. The agent quickly surpassed it as it learned correct tool formatting and security reasoning.*

![Clipped Ratio](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/clipped-ratio.jpeg)
*Figure 2: Clipped Ratio diagnostic. The drop from 98.75% to 0.63% shows the policy stabilized and locked in its learning without catastrophic forgetting.*

![Performance Comparison](https://media.githubusercontent.com/media/ravindraogg/Geoalloc/secureheal_arena/benchmarks-graph/performance_comparison.png)
*Figure 3: Quantitative improvement after GRPO training across all 4 key metrics.*

See `training/train.py` for the GRPO training pipeline and `TRAINING_EVIDENCE.md` for the full technical breakdown.

## Team - codeXcreators

Built for the **Meta PyTorch OpenEnv Hackathon India 2026**.

| | Name | GitHub | Role |
|---|------|--------|------|
| <img src="https://avatars.githubusercontent.com/u/149950829?v=4" width="60" /> | **Ravindra** | [ravindraogg](https://github.com/ravindraogg) | Environment and Infra |
| <img src="https://avatars.githubusercontent.com/u/134051960?v=4" width="60" /> | **Nitesh** | [PanatiNitesh](https://github.com/PanatiNitesh) | Training and Rewards |
| <img src="https://avatars.githubusercontent.com/u/144938646?v=4" width="60" /> | **Pooja** | [Pooja-CG](https://github.com/Pooja-CG) | Demo and Presentation |

---

*SecureHeal Arena, because the best defence is a trained offence.*
