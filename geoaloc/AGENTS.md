# GeoAlloc Strategic Agents

## Round 1: Foundation (Manual & Mock)
- Integrated 250+ real-world countries.
- High-fidelity Globe visualization.
- Manual Neural Override system for emergency intervention.

## Round 2: Strategic Autonomy (RL Pipeline)
- **Framework:** TRL (Proximal Policy Optimization) + Unsloth (4-bit LoRA).
- **Behavioral Objective:** Learn "Strategic Delay".
- **Mechanism:** Introduced `COOLING_RATE` (0.05) to allow global tension to decay over time.
- **Reward Shaping:** The agent is penalized for high tension and rewarded for long-term stability maintenance.

### Training Specs
- **Model:** Llama-3-8B-bnb-4bit
- **Loop:** `train.py` implements a PPO loop over the `GeoAllocEnv`.
- **Target:** Trigger `no_op` actions during high-tension windows to facilitate geopolitical cooling.

### How to Run Training
```bash
cd geoalloc-env
pip install -r requirements.txt
python train.py
```

### Observation Interface
The agent monitors:
- `global_tension`: The primary variable for "Strategic Delay".
- `unmet_demand`: The pressure to allocate resources.
- `stability`: The local state of each node.
