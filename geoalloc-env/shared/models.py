"""
shared/models.py — Single Source of Truth for GeoAlloc Data Models.

All Pydantic v2 models live here. Every other module imports from this file.
No duplicates. No drift. No ambiguity.
"""
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


# ── Internal State Models ──────────────────────────────────────────────────────

class CountryState(BaseModel):
    """Mutable internal state for a single country."""
    id: str
    demand: int
    received: int = 0
    stability: float = Field(ge=0.0, le=1.0)
    allies: List[str] = Field(default_factory=list)
    enemies: List[str] = Field(default_factory=list)
    refinery_capacity: float = 0.5   # 0.0–1.0
    refined_buffer: float = 0.0      # Oil queued for next-step refining


class EnvState(BaseModel):
    """Full mutable environment state."""
    available_oil: int
    countries: List[CountryState]
    global_tension: float = Field(ge=0.0, le=1.0)
    time_step: int = 0
    max_steps: int = 10


# ── Action ─────────────────────────────────────────────────────────────────────

class Action(BaseModel):
    """Agent action: allocate oil to a country or do nothing."""
    type: Literal["allocate", "no_op"]
    country_id: Optional[str] = None
    amount: Optional[int] = None

    @model_validator(mode="after")
    def validate_action(self) -> "Action":
        if self.type == "allocate":
            if self.country_id is None:
                raise ValueError("allocate requires country_id")
            if self.amount is None or self.amount < 0:
                raise ValueError("allocate requires non-negative amount")
        return self


# ── Observation ────────────────────────────────────────────────────────────────

class CountryObservation(BaseModel):
    """Read-only snapshot of a country visible to the agent."""
    id: str
    demand: int
    received: int
    stability: float
    allies: List[str]
    enemies: List[str]
    unmet_demand: int
    refinery_capacity: float
    refined_buffer: float


class Observation(BaseModel):
    """Full observation returned by env.step() and env.reset()."""
    available_oil: int
    countries: List[CountryObservation]
    global_tension: float
    time_step: int
    max_steps: int
    done: bool = False
    reward: float = 0.0
    reasoning: Optional[str] = None
    projection: Optional[dict] = None   # Strategic Foresight projections


# ── Evaluation Metrics (Phase 2 addition) ──────────────────────────────────────

class EvalMetrics(BaseModel):
    """Detailed per-step evaluation metrics for training analysis."""
    stability_delta: float = 0.0
    tension_delta: float = 0.0
    strategic_delay_used: bool = False
    resource_efficiency: float = 0.0    # received / total_demand
    refinery_utilization: float = 0.0   # active buffers / total countries


# ── Step Info & Result ─────────────────────────────────────────────────────────

class StepInfo(BaseModel):
    """Metadata returned alongside each step."""
    waste: float
    unmet_demand_ratio: float
    avg_stability: float
    action_valid: bool
    error: Optional[str] = None
    eval_metrics: Optional[EvalMetrics] = None


class StepResult(BaseModel):
    """Complete result of a single environment step."""
    observation: Observation
    reward: float
    done: bool
    info: StepInfo


# ── Compatibility Aliases ──────────────────────────────────────────────────────
GeoAllocAction = Action
GeoAllocObservation = Observation
