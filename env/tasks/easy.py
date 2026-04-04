from env.models import CountryState, EnvState
from env.env import GeoAllocEnv


def make_easy_env() -> GeoAllocEnv:
    """
    Easy task:
    - 2 countries
    - No enemy relations
    - Sufficient oil (total demand = 100, available = 120)
    - Low initial tension
    """
    state = EnvState(
        available_oil=120,
        global_tension=0.0,
        time_step=0,
        max_steps=10,
        countries=[
            CountryState(
                id="alpha",
                demand=50,
                received=0,
                stability=0.6,
                allies=["beta"],
                enemies=[],
            ),
            CountryState(
                id="beta",
                demand=50,
                received=0,
                stability=0.6,
                allies=["alpha"],
                enemies=[],
            ),
        ],
    )
    return GeoAllocEnv(initial_state=state)
