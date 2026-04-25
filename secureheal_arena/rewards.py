"""
secureheal_arena/rewards.py
────────────────────────────
Reward functions for the SecureHeal Arena.

Implements four independent reward signals:
  R1 — Exploit blocked (RLVR, binary)
  R2 — Test suite pass rate (RLVR, continuous 0.0–1.0)
  R3 — System stability restored (semi-verifiable, latency delta)
  R4 — Cascading failures halted (heuristic, anomaly count)

Plus anti-cheat penalties for timeout, forbidden ops, and format errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SecureHealState
    from .sandbox import SandboxResult


@dataclass
class RewardBreakdown:
    """Structured breakdown of the four reward signals + penalties."""
    r1_exploit_blocked: float = 0.0
    r2_test_pass_rate: float = 0.0
    r3_stability_delta: float = 0.0
    r4_cascading_cleared: float = 0.0
    penalty: float = 0.0
    total: float = 0.0


# ────────────────── Weights ────────────────────────────────────

R1_WEIGHT = 0.35
R2_WEIGHT = 0.35
R3_WEIGHT = 0.20
R4_WEIGHT = 0.10

# ────────────────── Penalties ──────────────────────────────────

PENALTY_TIMEOUT = -1.0
PENALTY_FORBIDDEN_OP = -2.0
PENALTY_FORMAT_ERROR = -0.2


def compute_reward(
    state: "SecureHealState",
    sandbox_result: "SandboxResult | None" = None,
) -> RewardBreakdown:
    """Compute the composite reward for the current step.

    Args:
        state:          Current environment state.
        sandbox_result: Result from sandbox (if an action triggered execution).

    Returns:
        RewardBreakdown with individual signals and total.
    """
    # R1 — Exploit blocked
    if state.patch_applied and not state.exploit_possible:
        r1 = 1.0
    elif state.vulnerability_present:
        r1 = -0.5
    else:
        r1 = 0.0

    # R2 — Test pass rate (continuous RLVR)
    r2 = state.test_pass_rate  # 0.0 – 1.0

    # R3 — System stability delta (semi-verifiable)
    stability_delta = state.system_stability - 0.5  # delta from "degraded baseline"
    r3 = max(0.0, stability_delta)

    # R4 — Cascading failures cleared
    r4 = 1.0 if len(state.cascading_failures) == 0 else 0.0

    # Anti-cheat penalties
    penalty = 0.0
    if sandbox_result:
        if sandbox_result.timeout:
            penalty += PENALTY_TIMEOUT
        if sandbox_result.forbidden_op:
            penalty += PENALTY_FORBIDDEN_OP
        if sandbox_result.format_error:
            penalty += PENALTY_FORMAT_ERROR

    # Also check state-level flags (accumulated over episode)
    if state.timeout_occurred:
        penalty += PENALTY_TIMEOUT * 0.5  # half weight for state-level
    if state.forbidden_op_detected:
        penalty += PENALTY_FORBIDDEN_OP * 0.5

    total = (
        R1_WEIGHT * r1
        + R2_WEIGHT * r2
        + R3_WEIGHT * r3
        + R4_WEIGHT * r4
        + penalty
    )

    return RewardBreakdown(
        r1_exploit_blocked=r1,
        r2_test_pass_rate=r2,
        r3_stability_delta=r3,
        r4_cascading_cleared=r4,
        penalty=penalty,
        total=total,
    )
