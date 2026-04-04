"""GeoAlloc Environment Client."""
from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import GeoAllocAction, GeoAllocObservation


class GeoAllocEnv(
    EnvClient[GeoAllocAction, GeoAllocObservation, State]
):
    """
    Client for the GeoAlloc Environment.

    Enables persistent WebSocket connections and Docker-based initialization.
    """

    def _step_payload(self, action: GeoAllocAction) -> Dict:
        """Convert action to JSON payload."""
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict) -> StepResult[GeoAllocObservation]:
        """Parse server response into StepResult."""
        obs_data = payload.get("observation", {})
        observation = GeoAllocObservation(**obs_data)
        
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """Parse server response into State."""
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
