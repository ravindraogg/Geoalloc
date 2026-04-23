"""
Data models for the GeoAlloc Environment.

Extends OpenEnv base types (Action, Observation) while keeping
all existing Pydantic models for internal state management.
"""
from __future__ import annotations
from typing import List, Optional, Literal

from openenv.core.env_server.types import Action as BaseAction, Observation as BaseObservation
from pydantic import BaseModel, Field, model_validator


# ── Internal state models (not exposed via OpenEnv API) ────────────────────────

class CountryState(BaseModel):
    id: str
    demand: int
    received: int = 0
    stability: float = Field(ge=0.0, le=1.0)
    allies: List[str] = Field(default_factory=list)
    enemies: List[str] = Field(default_factory=list)


class EnvState(BaseModel):
    available_oil: int
    countries: List[CountryState]
    global_tension: float = Field(ge=0.0, le=1.0)
    time_step: int = 0
    max_steps: int = 10


# ── OpenEnv-compatible Action ──────────────────────────────────────────────────

class GeoAllocAction(BaseAction):
    """Action for the GeoAlloc environment."""
    type: Literal["allocate", "no_op"]
    country_id: Optional[str] = None
    amount: Optional[int] = None

    @model_validator(mode="after")
    def validate_action(self) -> "GeoAllocAction":
        if self.type == "allocate":
            if self.country_id is None:
                raise ValueError("allocate requires country_id")
            if self.amount is None or self.amount < 0:
                raise ValueError("allocate requires non-negative amount")
        return self


# ── OpenEnv-compatible Observation ─────────────────────────────────────────────

class CountryObservation(BaseModel):
    id: str
    demand: int
    received: int
    stability: float
    allies: List[str]
    enemies: List[str]
    unmet_demand: int


class GeoAllocObservation(BaseObservation):
    """Observation from the GeoAlloc environment."""
    available_oil: int = Field(default=0, description="Oil remaining to allocate")
    countries: List[CountryObservation] = Field(default_factory=list, description="Per-country state")
    global_tension: float = Field(default=0.0, description="Cumulative geopolitical tension")
    time_step: int = Field(default=0, description="Current step index")
    max_steps: int = Field(default=10, description="Episode length cap")


# ── Legacy aliases (for inference.py compatibility) ────────────────────────────

Action = GeoAllocAction
Observation = GeoAllocObservation


class StepInfo(BaseModel):
    waste: float
    unmet_demand_ratio: float
    avg_stability: float
    action_valid: bool
    error: Optional[str] = None


class StepResult(BaseModel):
    observation: GeoAllocObservation
    reward: float
    done: bool
    info: StepInfo
