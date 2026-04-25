"""
secureheal_arena/models.py
──────────────────────────
Action, Observation, and State types for the SecureHeal Arena environment.

The agent operates inside a simulated live infrastructure where code is being
actively attacked.  It must detect vulnerabilities, simulate exploits,
apply patches, and stabilise the system — all within a single long-horizon
RL episode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openenv.core.env_server.interfaces import Action, Observation, State


# ─────────────────────────── Actions ───────────────────────────

VALID_ACTIONS = [
    "scan_code",            # scan for vulnerabilities
    "simulate_attack",      # test if exploit succeeds
    "apply_patch",          # apply a code fix
    "run_tests",            # execute test suite
    "restart_service",      # restart a failing service
    "clean_data",           # clear corrupted data
    "reallocate_resources", # shift compute resources
    "classify_issue",       # tag anomaly type
]


class SecureHealAction(Action):
    """A single action the agent can take inside the arena.

    Attributes:
        action_type: One of the eight valid action strings.
        parameters:  Optional key-value payload for the action (e.g. patch
                     code, service name, classification label).
    """
    action_type: str
    parameters: Dict[str, Any] = {}


# ─────────────────────────── Observations ──────────────────────

class SecureHealObservation(Observation):
    """What the agent sees after each step.

    Attributes:
        code_snippet:       The vulnerable (or patched) code block.
        system_logs:        Recent sensor / log lines.
        latency_metrics:    Current latency readings (service -> ms).
        error_states:       Active error labels.
        anomaly_flags:      Detected anomaly types.
        episode_step:       Current step number.
        available_actions:  Actions available at this point.
        action_result:      Human-readable description of what happened.
        reward:             Step reward (also returned via StepResult).
        done:               Whether the episode has ended.
    """
    code_snippet: str = ""
    system_logs: List[str] = []
    latency_metrics: Dict[str, float] = {}
    error_states: List[str] = []
    anomaly_flags: List[str] = []
    episode_step: int = 0
    available_actions: List[str] = []
    action_result: str = ""
    reward: float = 0.0
    done: bool = False


# ─────────────────────────── State ─────────────────────────────

class SecureHealState(State):
    """Internal episode state — not visible to the agent.

    Tracks security posture, system health, and curriculum level.
    """
    # --- Security layer (from SecureCode Arena X) ---
    vulnerability_type: str = ""
    vulnerability_present: bool = False
    exploit_possible: bool = False
    patch_applied: bool = False
    patch_code: str = ""
    test_pass_rate: float = 0.0       # 0.0 – 1.0, RLVR signal

    # --- Stability layer (from DataHeal Arena) ---
    anomaly_type: str = ""
    system_stability: float = 1.0     # 0.0 – 1.0
    cascading_failures: List[str] = []
    latency_baseline: float = 50.0    # ms
    latency_current: float = 50.0     # ms
    services_status: Dict[str, str] = {}   # service_name -> "up" | "down"
    data_corrupted: bool = False

    # --- Episode tracking ---
    max_steps: int = 8
    curriculum_level: int = 1
    seed: int = 0

    # --- Reward components (for logging) ---
    r1_exploit_blocked: float = 0.0
    r2_test_pass_rate: float = 0.0
    r3_stability_delta: float = 0.0
    r4_cascading_cleared: float = 0.0
    total_reward: float = 0.0

    # --- Sandbox flags ---
    timeout_occurred: bool = False
    forbidden_op_detected: bool = False
    format_error: bool = False
