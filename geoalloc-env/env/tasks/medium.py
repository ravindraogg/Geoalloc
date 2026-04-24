from env.models import CountryState, EnvState
from env.env import GeoAllocEnv


def make_medium_env() -> GeoAllocEnv:
    """
    Medium task:
    - 3 countries
    - 1 enemy relation (gamma ↔ delta)
    - Limited oil (total demand = 150, available = 130)
    - Moderate initial tension
    - Mixed refinery capacity → must decide who benefits from refining
    """
    state = EnvState(
        available_oil=130,
        global_tension=0.1,
        time_step=0,
        max_steps=12,
        countries=[
            CountryState(
                id="gamma",
                demand=60,
                received=0,
                stability=0.5,
                allies=[],
                enemies=["delta"],
                refinery_capacity=0.5,
                refined_buffer=0.0,
            ),
            CountryState(
                id="delta",
                demand=50,
                received=0,
                stability=0.5,
                allies=[],
                enemies=["gamma"],
                refinery_capacity=0.3,
                refined_buffer=0.0,
            ),
            CountryState(
                id="epsilon",
                demand=40,
                received=0,
                stability=0.7,
                allies=["gamma"],
                enemies=[],
                refinery_capacity=0.6,
                refined_buffer=0.0,
            ),
        ],
    )
    return GeoAllocEnv(initial_state=state)
