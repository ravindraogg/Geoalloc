# SecureHeal Arena - Pitch Deck Outline

## Slide 1: Title Slide
*   **Title:** SecureHeal Arena
*   **Subtitle:** Autonomous System Recovery & Vulnerability Patching Command Center
*   **Logos:** Meta, PyTorch, Hugging Face (OpenEnv Hackathon 2026)
*   **Visual:** The clean, pastel UI from our Gradio app.

## Slide 2: The Problem (Capability Gap)
*   **Headline:** AI can write code, but can it save a dying system?
*   **Points:**
    *   **Siloed capabilities:** Current LLMs handle code OR infrastructure logs, rarely both.
    *   **Static vs. Dynamic:** Finding a bug in a text file is easy; applying a patch while latency spikes and cascading failures trigger is hard.
    *   **Long-Horizon Planning:** Agents lack the ability to chain *Diagnosis -> Exploit -> Patch -> Verification -> System Recovery*.
*   **Visual:** A flowchart showing the chaotic reality of a live production incident.

## Slide 3: The Environment (SecureHeal Arena)
*   **Headline:** A Dual-Layer OpenEnv Simulation
*   **Points:**
    *   **Layer 1: Code Vulnerability:** Agent must use `scan_code` and `simulate_attack` inside a strict execution sandbox.
    *   **Layer 2: System Stability:** Agent monitors latency and logs, using `restart_service` and `reallocate_resources`.
    *   **Curriculum Learning:** Progresses from simple SQLi to complex, stochastic cascading anomalies.
*   **Visual:** Screenshot of the Agent Action Deck and System Telemetry dashboard.

## Slide 4: Reward Engineering & Pipeline
*   **Headline:** Preventing Hacks with Verifiable Rewards
*   **Points:**
    *   **R1 & R2 (RLVR):** Hard execution checks—did the exploit fail? Did the test suite pass?
    *   **R3 & R4 (Heuristics):** Latency delta and cascading failure mitigation.
    *   **Anti-Cheat Sandbox:** Hard 5-second timeouts, protected state locks, and forbidden operation penalties.
*   **Visual:** Architecture diagram: `Agent -> Sandbox Execution -> 4-Part Reward Rubric -> TRL/Unsloth`

## Slide 5: Results & Impact
*   **Headline:** From Hallucinations to Hero
*   **Points:**
    *   **Baseline Model:** Hallucinates actions, system crashes, 0% reward.
    *   **Trained Model:** Follows multi-step recovery policy, achieves high stability.
    *   **Impact:** Proves we can train LLMs for complex, multi-domain SRE and security tasks using GRPO.
*   **Visual:** Reward curve plots from WandB (Training Step vs. Reward) showing clear upward trajectory.

## Slide 6: Demo & Links
*   **Headline:** Try It Live
*   **Points:**
    *   QR Code to Hugging Face Space Demo
    *   Link to GitHub Repo and YouTube Demo Video
    *   "Thank You!"
