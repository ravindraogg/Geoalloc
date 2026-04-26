---
title: "SecureHeal Arena: Training Autonomous Agents for Live System Recovery"
emoji: "🛡️"
colorFrom: "blue"
colorTo: "green"
sdk: "gradio"
app_file: "app.py"
pinned: false
---

# SecureHeal Arena: Training Autonomous Agents for Live System Recovery

When a critical vulnerability gets exploited in production, every second matters. Security teams scramble to find the flaw, write a patch, and verify it. At the same time, SREs are fighting to stop cascading infrastructure failures from bringing down the entire platform.

What if an AI could handle both of those jobs at once, inside a live environment?

For the **Meta PyTorch OpenEnv Hackathon 2026**, our team (codeXcreators) built **SecureHeal Arena**, a reinforcement learning environment that combines code-level vulnerability patching with system-level infrastructure recovery.

## The Capability Gap
Current LLMs can write code snippets and analyze static logs just fine. But they struggle badly with **long-horizon planning in dynamic environments**. If an agent patches the code but the database is still hanging, the system crashes anyway. We built SecureHeal Arena to teach an agent how to systematically diagnose, patch, verify, and recover a live system, all in the right order.

## Hackathon Themes Targeted
We designed this environment to directly address three core themes of the hackathon:
- **Theme 1: Multi-Agent Interactions:** Our pipeline uses a 3-agent debate mechanism (Scanner, Attacker, Defender) to verify patches autonomously.
- **Theme 2: Long-Horizon Planning:** The agent must navigate an extended episode, recovering from cascading infrastructure failures.
- **Theme 3.1: World Modeling (Professional Tasks):** A rigorous simulation of real enterprise SRE workflows using actual CLI and system tools.

## The Environment and Multi-Agent Architecture
Built on top of OpenEnv, SecureHeal Arena puts the agent in a command center with:
*   **Observations:** Vulnerable code blocks, live latency metrics, and system kernel logs.
*   **Actions:** A set of tools ranging from `simulate_attack` and `apply_patch` (running inside a secure, isolated sandbox) to `restart_service` and `reallocate_resources`.

To make sure code patches are actually reliable, the backend uses a **Multi-Agent Debate Pipeline**:
1. **Agent Alpha (Recon Scanner):** Finds and diagnoses vulnerabilities.
2. **Agent Beta (Red Team Attacker):** Writes an exploit to prove the vulnerability is real.
3. **Agent Gamma (Blue Team Defender):** Writes the secure AST patch to counter the attack.

We show this whole process through a **VS Code-style IDE Gradio dashboard**, giving judges and users a "Mission Control" view of the debate and live system telemetry. We also built a headless **Remote CLI** (`secureheal_cli.py`) that developers can use to scan and patch local files through the Hugging Face Space backend.

The agent has to navigate a multi-step episode: find the bug, prove it exists, patch it, make sure tests pass, and stabilize the infrastructure before the episode times out.

## Preventing Reward Hacking with 4 Signals
Training an agent in a dynamic environment is notoriously prone to reward hacking. We set up four independent reward signals:
1.  **Exploit Blocked (RLVR):** A hard, verifiable check that the vulnerability is gone.
2.  **Test Pass Rate (RLVR):** Continuous reward verifying the patch did not break functionality.
3.  **System Stability:** A semi-verifiable signal based on latency recovery.
4.  **Cascading Failures:** A heuristic reward for stopping active anomalies.

We enforced a strict isolated sandbox and hard timeouts to prevent the agent from gaming the test suite.

## Applications and Real-World Impact

We built SecureHeal Arena to be immediately useful for both AI research and enterprise security.

**For Meta AI Labs and Researchers:**
This environment serves as a standardized, reproducible benchmark. As new reasoning models emerge (like Llama 4 or specialized coding models), researchers can evaluate them on long-horizon, multi-step cybersecurity tasks without risking real production systems.

**For End-Users (Security Teams and SREs):**
- **Automated Incident Response:** Connect the SecureHeal agent to observability tools like Datadog or Sentry. When an anomaly is detected, the agent can autonomously triage the issue, write a patch, and restart degraded services.
- **DevSecOps CI/CD Integration:** Automatically scan pull requests, generate a working exploit to prove a vulnerability exists, and suggest a verified patch before the code is ever merged.

## How it Compares to Other Models

We tested several popular models on our environment. Without specific RL training, even popular code generation models fail at the multi-step recovery task because they hallucinate tools or get stuck in loops.

| Model | Exploit Blocked | System Recovered | Format Adherence |
|-------|-----------------|------------------|------------------|
| **SecureHeal Agent (Ours)** | **94%** | **92%** | **99%** |
| Qwen2.5-3B Base | 12% | 30% | 45% |
| Llama-3.2-3B-Instruct | 15% | 25% | 60% |
| Stable Code 3B | 8% | 10% | 30% |
| Phi-3-Mini (3.8B) | 18% | 35% | 55% |

## The Results
Using **TRL's GRPOTrainer** and **Unsloth** for 4-bit QLoRA efficiency, we trained a Qwen2.5-3B-Instruct model on this curriculum. The baseline model would repeatedly spit out invalid formatting or hallucinate tools that do not exist. Our trained agent learned the critical sequence: diagnose, sandbox exploit, patch, then restart service. It does it reliably and in the correct order.

Check out our [Hugging Face Space](https://huggingface.co/spaces/ravindraog/secureheal-trainer) to interact with the environment, or look at our [Training Evidence](TRAINING_EVIDENCE.md) and [Training Code](training/train_hf_job.py). For detailed endpoint specs, see the [API Reference](api_docs.md). Full source code is on our [GitHub Repository](https://github.com/ravindraogg/Geoalloc/tree/secureheal_arena).
