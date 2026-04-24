from env.models import CountryState, EnvState
from env.env import GeoAllocEnv


def make_easy_env() -> GeoAllocEnv:
    """
    Easy task:
    - 2 countries
    - No enemy relations
    - Sufficient oil (total demand = 100, available = 120)
    - Low initial tension
    - High refinery capacity → almost all oil refined efficiently
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
                refinery_capacity=0.8,
                refined_buffer=0.0,
            ),
            CountryState(
                id="beta",
                demand=50,
                received=0,
                stability=0.6,
                allies=["alpha"],
                enemies=[],
                refinery_capacity=0.7,
                refined_buffer=0.0,
            ),
        ],
    )
    return GeoAllocEnv(initial_state=state)
