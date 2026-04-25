"""
secureheal_arena/anomalies.py
──────────────────────────────
Anomaly injection catalogue for the DataHeal side of SecureHeal Arena.

Each anomaly specifies:
  • anomaly_type   – classification label the agent must guess
  • services       – affected services and their initial states
  • latency_spike  – how much latency degrades (ms)
  • cascading      – secondary anomalies that can fire after a patch
  • recovery_steps – correct sequence of recovery actions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


@dataclass
class AnomalyScenario:
    """A stochastic system anomaly injected alongside a code vulnerability."""
    anomaly_type: str
    description: str
    affected_services: Dict[str, str]       # service_name -> "up" | "down" | "degraded"
    latency_spike_ms: float                 # added on top of baseline
    cascading_probability: float            # chance of secondary anomaly on patch
    cascading_anomaly: Optional[str]        # type of secondary anomaly
    data_corruption: bool                   # whether data needs cleaning
    recovery_actions: List[str]             # correct actions to resolve


# ──────────────────── Anomaly Registry ─────────────────────────

MEMORY_SPIKE = AnomalyScenario(
    anomaly_type="memory_spike",
    description="Memory consumption on the auth-service exceeds threshold, causing latency degradation.",
    affected_services={"auth-service": "degraded", "api-gateway": "up", "db-primary": "up"},
    latency_spike_ms=120.0,
    cascading_probability=0.3,
    cascading_anomaly="disk_pressure",
    data_corruption=False,
    recovery_actions=["classify_issue", "restart_service", "reallocate_resources"],
)

DISK_PRESSURE = AnomalyScenario(
    anomaly_type="disk_pressure",
    description="Disk space on db-primary is critically low, logs are failing to write.",
    affected_services={"db-primary": "degraded", "auth-service": "up", "api-gateway": "up"},
    latency_spike_ms=80.0,
    cascading_probability=0.2,
    cascading_anomaly="data_corruption",
    data_corruption=False,
    recovery_actions=["classify_issue", "clean_data", "restart_service"],
)

DATA_CORRUPTION = AnomalyScenario(
    anomaly_type="data_corruption",
    description="Cache poisoning detected — stale data served to downstream consumers.",
    affected_services={"cache-layer": "down", "api-gateway": "degraded", "db-primary": "up"},
    latency_spike_ms=200.0,
    cascading_probability=0.0,
    cascading_anomaly=None,
    data_corruption=True,
    recovery_actions=["classify_issue", "clean_data", "restart_service", "reallocate_resources"],
)

NETWORK_PARTITION = AnomalyScenario(
    anomaly_type="network_partition",
    description="Intermittent network partition between api-gateway and db-primary.",
    affected_services={"api-gateway": "degraded", "db-primary": "degraded", "auth-service": "up"},
    latency_spike_ms=300.0,
    cascading_probability=0.4,
    cascading_anomaly="memory_spike",
    data_corruption=False,
    recovery_actions=["classify_issue", "restart_service", "reallocate_resources"],
)


ANOMALY_CATALOGUE = [
    MEMORY_SPIKE,
    DISK_PRESSURE,
    DATA_CORRUPTION,
    NETWORK_PARTITION,
]

LEVEL_1_ANOMALIES = [MEMORY_SPIKE]
LEVEL_2_ANOMALIES = [MEMORY_SPIKE, DISK_PRESSURE]
LEVEL_3_ANOMALIES = ANOMALY_CATALOGUE  # all


def get_anomalies_for_level(level: int) -> List[AnomalyScenario]:
    """Return available anomaly scenarios for a given curriculum level."""
    if level <= 1:
        return LEVEL_1_ANOMALIES
    elif level == 2:
        return LEVEL_2_ANOMALIES
    else:
        return LEVEL_3_ANOMALIES


def select_anomaly(level: int, rng: random.Random) -> AnomalyScenario:
    """Randomly select an anomaly scenario appropriate for the curriculum level."""
    candidates = get_anomalies_for_level(level)
    return rng.choice(candidates)
