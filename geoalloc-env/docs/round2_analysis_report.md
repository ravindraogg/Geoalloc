# GeoAllocEnv: Round 2 Upgrade & Strategic Analysis Report

This report evaluates the current state of **GeoAllocEnv** and provides a roadmap for Round 2 of the OpenEnv Hackathon.

---

## 1. THEME ALIGNMENT ANALYSIS

### Primary Theme: Theme #2 — (Super) Long-Horizon Planning & Instruction Following
GeoAllocEnv aligns most strongly with **Theme #2**. The core challenge is distributing limited resources across multiple steps while managing a "global tension" budget. 

*   **Mapping:** The docs explicitly list "strategic resource management worlds" as a key example for this theme.
*   **Current Alignment:**
    *   **Satisfies:** Multi-step decision making (1.0 budget management) and resource scarcity.
    *   **Weak/Shallow:** Rewards are too dense (immediate feedback), and trajectories lack "recoverable mistakes" logic. Tension only increases, meaning there is no way to "wait out" a bad state.

---

## 2. ROUND 2 GAP ANALYSIS (CRITICAL)

The current implementation is a solid "proof-of-concept" but lacks the research-grade depth required for Round 2 success.

| Area | Current State | Gap / Weakness |
| :--- | :--- | :--- |
| **Evidence of Learning** | Zero | No training curves or before/after comparisons exist. |
| **Training Pipeline** | None | Project relies on zero-shot inference; no Unsloth/TRL loop. |
| **Tension Mechanics** | Monotonic | Tension only goes up. This reduces "long-horizon" reasoning to a simple knapsack-style problem. |
| **Observability** | Full | The agent sees the entire enemy network. This eliminates the need for "world modeling" or belief tracking. |
| **Reward Richness** | Dense / Additive | High reward density makes it "easy" for SFT models but doesn't challenge the RL trainer to find deep strategies. |
| **Reasoning Difficulty** | Low | Hard tasks are just "more of the same" (more countries) rather than logically deeper. |

---

## 3. TRAINING REQUIREMENTS PLAN

To satisfy the "agent learns over time" requirement, we will implement a **GRPO (Group Relative Policy Optimization)** loop.

### Proposed Setup
*   **Baseline:** `gpt-4o-mini` zero-shot (current performance).
*   **Target Model:** `llama-3-8b` or `phi-3-mini` (quantized via Unsloth).
*   **Training Loop:**
    1.  Sample 8–16 trajectories per prompt.
    2.  Group trajectories by task (Easy/Medium/Hard).
    3.  Compute relative rewards (how much better a trajectory was compared to its siblings).
    4.  Update policy via TRL/Unsloth.

### Metrics to Track
1.  **Mean Reward Curve:** Overall performance improvement.
2.  **Tension Survival Rate:** Percentage of episodes not terminating via 1.0 tension.
3.  **Oil Efficiency:** Ratio of demand met vs. total available resources.
4.  **Stability-to-Tension Ratio:** The "Golden Metric" for this environment—how much stability was gained per unit of tension produced.

---

## 4. ENVIRONMENT IMPROVEMENTS (HIGH IMPACT)

### Long-Horizon Reasoning: Tension Decay & Cool-downs
*   **Change:** Implement a `0.02` tension decay per `no_op` step.
*   **Impact:** Forces the agent to decide: *"Should I allocate now and risk 1.0 tension, or wait 3 turns to cool the world down?"* This creates a true long-horizon dependency and "compound consequences."

### Complexity Scaling: Dynamic Volatility
*   **Change:** Introduce "Events" (e.g., "Conflict escalates between Zeus and Hera") that double the tension sensitivity for specific pairs for 3 turns.
*   **Impact:** Prevents static, hard-coded strategies. The agent must adapt to shifting "world states."

### Partial Observability: "Intelligence Fog"
*   **Change:** Hide the `enemies` list for non-neighboring countries or make it visible only through a `probe` action (costs 1 oil).
*   **Impact:** Forces the model to build an internal "belief map" of the world.

---

## 5. REWARD SYSTEM REVIEW

### Current Status: **Dense & Hackable**
The current reward `(0.5 * stability) - (0.2 * tension)` is easily gamed by models that meet demand for 1 "safe" country and then spam `no_op`.

### Proposed Improvements
To minimize reward hacking, we will use **four independent reward signals**:
1.  **Demand Satisfaction (Outcome):** Percentage of total demand met.
2.  **Stability Growth (Outcome):** Average stability of all countries.
3.  **Tension Penalty (Constraint):** Negative reward proportional to `global_tension^2` (punishes escalation exponentially).
4.  **Operational Efficiency (Process):** Bonus for minimizing `waste` (over-allocation).

**Anti-Hacking Mechanisms:**
*   **Survival Bonus:** Grant `+0.3` only at the end if `global_tension < 1.0`.
*   **Early Termination:** If the model sends an invalid JSON action twice, the episode is zeroed.
*   **No-Op Spam Penalty:** Small penalty if `no_op` is used more than 5 times consecutively when oil is available.

---

## 6. DEMO & STORYTELLING PLAN

The final submission must tell a story of **Strategic Restraint**.

1.  **The Tragedy (Before):** Show a baseline model allocating aggressively, hitting 1.0 tension by step 4, and failing the task.
2.  **The Strategy (After):** Show the trained agent using `no_op` steps strategically to lower tension, then satisfying all demands by step 14.
3.  **Visualization:**
    *   **Dual-Graph:** Oil Levels vs. Tension Over Time.
    *   **Reward Heatmap:** Showing how the agent avoids "Hot Zones" (high enemy countries) until it has a tension buffer.

---

## 7. PRIORITIZED ACTION PLAN

### Phase 1: Survival (Must-do for Round 2)
*   Integrate **Unsloth + TRL (GRPO)** training script.
*   Log training metrics to HuggingFace / Weights & Biases.
*   Modify `geoalloc_environment.py` to include **Tension Decay**.

### Phase 2: Depth (High Impact)
*   Implement **Events System** for dynamic difficulty.
*   Refine Reward model with **Sparse Survival Bonuses**.
*   Add **Reasoning Traces** to the agent's observation/action loop.

### Phase 3: Polish (Optional)
*   Add `probe` actions for Partial Observability.
*   Create a Gradio/Streamlit UI for the final "Live Demo" on Spaces.
*   Record a <2min video explaining the "Equilibrium Challenge."

---
**Goal:** Shift from a sequence-prediction task to a true **Strategic Equilibrium Simulation**.
