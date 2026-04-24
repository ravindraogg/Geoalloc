# GeoAlloc Project Context: Architectural Review

## 1. CURRENT PROJECT OVERVIEW

*   **Objective**: GeoAlloc is a strategic resource allocation simulation designed to train and evaluate AI agents on complex geopolitical decision-making. 
*   **Problem Solved**: The system models the tension between satisfying energy demands and maintaining global stability. It forces agents to learn "Strategic Delay"—the ability to withhold resources to allow geopolitical tension to decay or to utilize refining buffers for higher efficiency.
*   **System Type**: A hybrid of an **RL Simulation Environment** (OpenEnv compliant), a **Training Pipeline** (GRPO + Unsloth), and a **Strategic Monitoring Dashboard** (Next.js/Three.js).

## 2. IMPLEMENTED FEATURES (WHAT EXISTS TODAY)

*   **GeoAllocEnv (Core)**: A deterministic simulation engine implementing the OpenEnv specification (`step`, `reset`, `state`). 
    *   *Real Behavior*: Handles allocation, stability gain, tension increases based on enemy networks, and a unique "Refinery Buffer" mechanic for delayed stability gains.
*   **OpenEnv Server**: A FastAPI wrapper that exposes the environment as a web service.
*   **GRPO Training Pipeline**: Implementation of Group Relative Policy Optimization (GRPO) using Unsloth for Llama-3 fine-tuning. 
    *   *Real Behavior*: Optimized for Kaggle T4 GPUs; learns reasoning tags (`<thought>`) to justify actions.
*   **Neural Link Dashboard**: A premium Next.js frontend with a 3D Globe visualization.
    *   *Real Behavior*: Allows manual "Decision Mode" play, displays real-time intelligence feeds, and provides "Strategic Foresight" (outcome projections).

## 3. SYSTEM ARCHITECTURE

*   **Environment**: Python-based logic using Pydantic v2 for strict state validation. 
*   **Agent Logic**: Llama-3 8B (4-bit quantized) acting as the controller, trained to output JSON actions after chain-of-thought reasoning.
*   **Frontend-Backend Sync**: The Next.js dashboard polls the FastAPI server. Communication is primarily JSON-based observation objects.
*   **Data Flow**: `EnvState` -> `Observation` -> `Agent/Dashboard` -> `Action` -> `EnvStep`.

## 4. CURRENT CAPABILITIES

*   **End-to-End Simulation**: The system can fully simulate a 30-step resource crisis.
*   **Strategic Foresight**: The environment can "predict" the delta in stability and tension for a given action without mutating state, enabling the dashboard's decision-support UI.
*   **Automated Training**: Can run on Kaggle/local GPU to generate "Strategic Delay" behavior evidence.

## 5. GAPS & MISSING PIECES

*   **Data Integration**: Geopolitical coordinates and country data are largely hardcoded or randomized. There is no real-world live data feed.
*   **Multi-Agent Support**: Currently a single agent vs. environment. Lacks adversarial or cooperative multi-agent scenarios.
*   **Robustness**: The Kaggle training script is heavily dependent on specific path structures (`/kaggle/input/...`) which makes it non-portable.
*   **Logic Issue**: "Tension Decay" is a flat constant; it doesn't scale with global stability or regional peace treaties.

## 6. TECHNICAL DEBT & RISKS

*   **Redundancy**: Multiple `models.py` and `env/models.py` files across the repo create a maintenance nightmare and potential import circularities.
*   **Coupling**: The frontend expects a specific `projection` object that is calculated on the fly in `geoalloc_environment.py`, adding latency to the observation loop.
*   **Performance**: The `predict_outcome` method uses `copy.deepcopy(self)`, which will become a bottleneck as state complexity grows.

## 7. ALIGNMENT WITH ORIGINAL GOAL

*   **Alignment**: High. The project successfully implements the "OpenEnv" spec and demonstrates the "Strategic Delay" concept.
*   **Deviation**: The "Refinery" mechanic was added later and isn't fully integrated into the baseline "Easy" tasks, creating a feature gap between difficulty levels.

## 8. NEXT BUILD PRIORITIES

### Immediate (Must Build Now)
*   **Model Consolidation**: Move all Pydantic models to a single shared package to prevent "Type Mismatch" errors between training and server code.
*   **State Persistence**: Implement a way to save/load simulation snapshots for auditability.

### Short-term
*   **Refinery Optimization**: Tune the `REFINERY_BETA` constant; currently, the "Strategic Delay" bonus is too low to consistently incentivize waiting over immediate allocation.
*   **Dynamic Task Generator**: Replace static Easy/Medium/Hard factories with a generator that creates random geopolitical clusters based on a seed.

### Advanced Improvements
*   **Scenario Branching**: Allow the agent to explore multiple "What-if" branches in parallel during a single session.
*   **LLM-as-Grader**: Replace the mathematical reward function with an LLM that evaluates the "Diplomatic Quality" of the reasoning.

## 9. REWRITE OR REFACTOR SUGGESTIONS

*   **Redesign `predict_outcome`**: Instead of deep-copying the environment, implement a "delta-only" math model for projections.
*   **Frontend Logic**: Move the "Top Unstable" sorting and filtering logic to the backend to reduce client-side compute and ensure consistency.
