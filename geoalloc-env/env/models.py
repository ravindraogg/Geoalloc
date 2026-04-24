from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


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


class AllocateAction(BaseModel):
    type: Literal["allocate"] = "allocate"
    country_id: str
    amount: int = Field(ge=0)


class NoOpAction(BaseModel):
    type: Literal["no_op"] = "no_op"


class Action(BaseModel):
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


class CountryObservation(BaseModel):
    id: str
    demand: int
    received: int
    stability: float
    allies: List[str]
    enemies: List[str]
    unmet_demand: int


class Observation(BaseModel):
    available_oil: int
    countries: List[CountryObservation]
    global_tension: float
    time_step: int
    max_steps: int


class StepInfo(BaseModel):
    waste: float
    unmet_demand_ratio: float
    avg_stability: float
    action_valid: bool
    error: Optional[str] = None


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: StepInfo


# Compatibility Aliases
GeoAllocAction = Action
GeoAllocObservation = Observation
