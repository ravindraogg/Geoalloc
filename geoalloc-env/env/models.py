"""
env/models.py — Re-export proxy.
All canonical definitions live in shared/models.py.
This file exists solely to keep `from env.models import X` working.
"""
from shared.models import (  # noqa: F401
    CountryState,
    EnvState,
    Action,
    CountryObservation,
    Observation,
    StepInfo,
    StepResult,
    EvalMetrics,
    GeoAllocAction,
    GeoAllocObservation,
)

# Legacy aliases
AllocateAction = Action
NoOpAction = Action
