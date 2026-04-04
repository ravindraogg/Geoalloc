from env.models import CountryState, EnvState
from env.env import GeoAllocEnv


def make_medium_env() -> GeoAllocEnv:
    """
    Medium task:
    - 3 countries
    - 1 enemy relation (gamma ↔ delta)
    - Limited oil (total demand = 150, available = 130)
    - Moderate initial tension
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
            ),
            CountryState(
                id="delta",
                demand=50,
                received=0,
                stability=0.5,
                allies=[],
                enemies=["gamma"],
            ),
            CountryState(
                id="epsilon",
                demand=40,
                received=0,
                stability=0.7,
                allies=["gamma"],
                enemies=[],
            ),
        ],
    )
    return GeoAllocEnv(initial_state=state)
