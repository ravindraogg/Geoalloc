from env.models import CountryState, EnvState
from env.env import GeoAllocEnv


def make_hard_env() -> GeoAllocEnv:
    """
    Hard task:
    - 5 countries
    - Dense enemy network (multiple bilateral tensions)
    - Severe oil scarcity (total demand = 300, available = 160)
    - High initial tension (0.3)
    - Varied refinery capacity → forces strategic allocation decisions
      ares:     0.3 (low  — needs immediate aid, refining is slow)
      zeus:     0.7 (high — benefits massively from delayed refining)
      hera:     0.2 (very low — almost no refinery, direct-only)
      poseidon: 0.6 (good — moderate delayed benefit)
      athena:   0.4 (low-mid — slight refinery advantage)
    """
    state = EnvState(
        available_oil=160,
        global_tension=0.3,
        time_step=0,
        max_steps=15,
        countries=[
            CountryState(
                id="ares",
                demand=70,
                received=0,
                stability=0.4,
                allies=["zeus"],
                enemies=["hera", "poseidon"],
                refinery_capacity=0.3,
                refined_buffer=0.0,
            ),
            CountryState(
                id="zeus",
                demand=60,
                received=0,
                stability=0.3,
                allies=["ares"],
                enemies=["hera", "athena"],
                refinery_capacity=0.7,
                refined_buffer=0.0,
            ),
            CountryState(
                id="hera",
                demand=65,
                received=0,
                stability=0.35,
                allies=["poseidon"],
                enemies=["ares", "zeus"],
                refinery_capacity=0.2,
                refined_buffer=0.0,
            ),
            CountryState(
                id="poseidon",
                demand=55,
                received=0,
                stability=0.3,
                allies=["hera"],
                enemies=["ares", "athena"],
                refinery_capacity=0.6,
                refined_buffer=0.0,
            ),
            CountryState(
                id="athena",
                demand=50,
                received=0,
                stability=0.25,
                allies=[],
                enemies=["zeus", "poseidon"],
                refinery_capacity=0.4,
                refined_buffer=0.0,
            ),
        ],
    )
    return GeoAllocEnv(initial_state=state)
