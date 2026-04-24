"""
visualize_results.py — Generate training curve and rollout log artifacts.
Produces:
  1. training_curve.png — Reward vs Episode with improvement trend
  2. rollout_log.txt    — Annotated step log showing Strategic Delay
"""
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "geoalloc_agent_grpo")


def plot_training_curve():
    """Generate reward vs episode graph from trainer_state.json or training_log.json."""
    # Try trainer_state.json first (GPU GRPO output), then training_log.json (CPU output)
    trainer_state = os.path.join(OUTPUT_DIR, "trainer_state.json")
    training_log = os.path.join(OUTPUT_DIR, "training_log.json")

    steps, rewards = [], []

    if os.path.exists(trainer_state):
        with open(trainer_state) as f:
            data = json.load(f)
        for entry in data.get("log_history", []):
            if "reward" in entry:
                steps.append(entry.get("step", len(steps)))
                rewards.append(entry["reward"])
    elif os.path.exists(training_log):
        with open(training_log) as f:
            data = json.load(f)
        for entry in data:
            steps.append(entry["episode"])
            rewards.append(entry["reward"])
    else:
        print("No training data found. Run train.py first.")
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available. Install with: pip install matplotlib")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    # Raw rewards
    ax.plot(steps, rewards, alpha=0.3, color="#4ECDC4", linewidth=0.8, label="Raw Reward")

    # Smoothed trend (moving average)
    window = min(20, len(rewards) // 4) if len(rewards) > 8 else 1
    if window > 1:
        smoothed = np.convolve(rewards, np.ones(window) / window, mode="valid")
        smooth_steps = steps[window - 1:]
        ax.plot(smooth_steps, smoothed, color="#FF6B6B", linewidth=2.5, label=f"Trend (MA-{window})")

    # Annotations
    if len(rewards) > 20:
        early_avg = sum(rewards[:20]) / 20
        late_avg = sum(rewards[-20:]) / 20
        ax.axhline(y=early_avg, color="#888", linestyle="--", alpha=0.5, label=f"Early Avg: {early_avg:.3f}")
        ax.axhline(y=late_avg, color="#2ECC71", linestyle="--", alpha=0.7, label=f"Final Avg: {late_avg:.3f}")

    ax.set_xlabel("Episode / Step", fontsize=12)
    ax.set_ylabel("Reward", fontsize=12)
    ax.set_title("GeoAlloc GRPO Training — Reward Improvement", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.2)

    output_path = os.path.join(OUTPUT_DIR, "training_curve.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[SAVED] Training curve -> {output_path}")


def generate_rollout_log():
    """Generate a formatted rollout log showing Strategic Delay behavior."""
    from shared.models import Action
    from env.env import GeoAllocEnv
    from env.tasks.hard import make_hard_env

    env = make_hard_env()
    obs = env.reset()
    lines = []
    lines.append("=" * 70)
    lines.append("GeoAlloc Round 2 -- Strategic Rollout Log (Hard Scenario)")
    lines.append("=" * 70)
    lines.append(f"Countries: {[c.id for c in obs.countries]}")
    lines.append(f"Oil: {obs.available_oil} | Tension: {obs.global_tension:.2f}")
    lines.append("")

    step = 0
    while True:
        # Strategic policy: delay when tension is high
        if obs.global_tension > 0.5:
            action = Action(type="no_op")
            reason = "STRATEGIC DELAY -- tension too high, waiting for decay"
        elif obs.available_oil > 0:
            candidates = [c for c in obs.countries if c.unmet_demand > 0]
            if candidates:
                candidates.sort(key=lambda c: (-c.refinery_capacity, c.stability))
                target = candidates[0]
                amount = min(int(target.unmet_demand * 0.5), obs.available_oil)
                if amount >= 1:
                    action = Action(type="allocate", country_id=target.id, amount=amount)
                    reason = f"ALLOCATE {amount}u -> {target.id} (refinery={target.refinery_capacity:.1f})"
                else:
                    action = Action(type="no_op")
                    reason = "NO-OP -- insufficient allocation possible"
            else:
                action = Action(type="no_op")
                reason = "NO-OP -- all demand met"
        else:
            action = Action(type="no_op")
            reason = "NO-OP -- oil depleted"

        result = env.step(action)
        step += 1
        obs = result.observation
        em = result.info.eval_metrics

        marker = " [*]" if em and em.strategic_delay_used else ""
        lines.append(f"[STEP {step:>2}] {reason}{marker}")
        lines.append(f"         reward={result.reward:+.3f}  tension={obs.global_tension:.3f}  "
                     f"stability={result.info.avg_stability:.3f}  oil={obs.available_oil}")
        if em:
            lines.append(f"         d_stab={em.stability_delta:+.4f}  d_tens={em.tension_delta:+.4f}  "
                         f"efficiency={em.resource_efficiency:.2f}")
        lines.append("")

        if result.done:
            lines.append("[RESULT] Episode Complete")
            lines.append(f"  Final Tension:   {obs.global_tension:.3f}")
            lines.append(f"  Final Stability: {result.info.avg_stability:.3f}")
            lines.append(f"  Total Reward:    {sum(1 for _ in [])}")  # placeholder
            lines.append(f"  Total Steps:     {step}")
            break

    output_path = os.path.join(OUTPUT_DIR, "rollout_log.txt")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[SAVED] Rollout log -> {output_path}")

    # Print to console too
    for line in lines:
        print(line)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    plot_training_curve()
    generate_rollout_log()
