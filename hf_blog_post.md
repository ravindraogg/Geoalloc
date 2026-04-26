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

When a critical vulnerability is exploited in production, every second counts. Security teams scramble to find the flaw, write a patch, and verify it, while SREs fight to keep cascading infrastructure failures from taking down the entire platform. 

What if an AI could do both, simultaneously, inside a live environment?

For the **Meta PyTorch OpenEnv Hackathon 2026**, our team built **SecureHeal Arena**—a novel reinforcement learning environment that merges code-level vulnerability patching with system-level infrastructure recovery.

## The Capability Gap
Current LLMs are great at writing code snippets or analyzing static logs. However, they struggle with **long-horizon planning in dynamic environments**. If an agent applies a patch but the database is still hanging, the system will still crash. We built SecureHeal Arena to teach an agent how to systematically diagnose, patch, verify, and recover a live system.

## The Environment & Multi-Agent Architecture
Built on top of OpenEnv, SecureHeal Arena places the agent in a command center with:
*   **Observations:** Vulnerable code blocks, live latency metrics, and system kernel logs.
*   **Actions:** A suite of tools ranging from `simulate_attack` and `apply_patch` (running inside a secure, isolated sandbox) to `restart_service` and `reallocate_resources`.

To ensure highly reliable code patches, our backend employs a **Multi-Agent Debate Pipeline**:
1. 🕵️ **Agent Alpha (Recon Scanner):** Diagnoses vulnerabilities.
2. 🥷 **Agent Beta (Red Team Attacker):** Writes an exploit proving the vulnerability exists.
3. 🛡️ **Agent Gamma (Blue Team Defender):** Writes the secure AST patch to counter the attack.

We visualize this entire process using a **VS Code-style IDE Gradio dashboard**, giving judges and users a "Mission Control" view of the debate and live system telemetry. We also built a headless **Remote CLI** (`secureheal_cli.py`) that developers can use to scan and patch local files securely via the Hugging Face Space backend.

The agent must navigate a multi-step episode: detect the bug, prove it exists, patch it, ensure tests pass, and stabilize the infrastructure before the episode times out.

## Preventing Reward Hacking with 4 Signals
Training an agent in a dynamic environment is notoriously prone to reward hacking. We implemented four independent reward signals:
1.  **Exploit Blocked (RLVR):** A hard, verifiable check that the vulnerability is gone.
2.  **Test Pass Rate (RLVR):** Continuous reward verifying the patch didn't break functionality.
3.  **System Stability:** A semi-verifiable signal based on latency recovery.
4.  **Cascading Failures:** A heuristic reward for halting active anomalies.

We enforced a strict isolated sandbox and hard timeouts to prevent the agent from short-circuiting the test suite.

## The Results
Using **TRL's GRPOTrainer** and **Unsloth** for 4-bit QLoRA efficiency, we trained a Qwen2.5-3B-Instruct model on this curriculum. While the baseline model would repeatedly output invalid formatting or hallucinate non-existent tools, our trained agent successfully learned the critical sequence: *diagnose → sandbox exploit → patch → restart service*. 

Check out our [Hugging Face Space](https://huggingface.co/spaces/ravindraog/secureheal-trainer) to interact with the environment via our custom Gradio dashboard, or read the full details in our [GitHub Repository](https://github.com/ravindraogg/Geoalloc/tree/secureheal_arena).
