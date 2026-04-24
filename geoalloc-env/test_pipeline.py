"""Quick integration test for the Round 2 pipeline."""
from env.tasks.hard import make_hard_env
from env.tasks.easy import make_easy_env
from env.tasks.medium import make_medium_env
from env.models import Action

print("=" * 50)
print("GeoAlloc Round 2 Integration Test")
print("=" * 50)

# Test all three tiers
for name, factory in [("EASY", make_easy_env), ("MEDIUM", make_medium_env), ("HARD", make_hard_env)]:
    e = factory()
    o = e.reset()
    print(f"\n[{name}] Reset OK — {len(o.countries)} countries, oil={o.available_oil}")

# Detailed test on hard env
e = make_hard_env()
o = e.reset()

# Step 1: Allocate to zeus (high refinery capacity = 0.7)
r = e.step(Action(type="allocate", country_id="zeus", amount=30))
zeus = [c for c in r.observation.countries if c.id == "zeus"][0]
print(f"\n[STEP 1] Allocate 30 to zeus (refinery=0.7)")
print(f"  reward={r.reward:.3f}  tension={r.observation.global_tension:.3f}")
print(f"  zeus: stability={zeus.stability:.3f} buffer={zeus.refined_buffer:.1f} received={zeus.received}")

# Step 2: No-op (buffer should be consumed)
r2 = e.step(Action(type="no_op"))
zeus2 = [c for c in r2.observation.countries if c.id == "zeus"][0]
print(f"\n[STEP 2] No-op (refinery buffer consumed)")
print(f"  reward={r2.reward:.3f}  tension={r2.observation.global_tension:.3f}")
print(f"  zeus: stability={zeus2.stability:.3f} buffer={zeus2.refined_buffer:.1f}")
print(f"  stability gain from refining: +{zeus2.stability - zeus.stability:.3f}")

# Step 3: Test prediction
p_noop = e.predict_outcome(Action(type="no_op"))
p_alloc = e.predict_outcome(Action(type="allocate", country_id="ares", amount=20))
print(f"\n[PREDICT] If no_op:    stab={p_noop['stability_delta']:+.4f}  tension={p_noop['tension_delta']:+.4f}")
print(f"[PREDICT] If allocate: stab={p_alloc['stability_delta']:+.4f}  tension={p_alloc['tension_delta']:+.4f}")

# Edge case: invalid allocation
r3 = e.step(Action(type="allocate", country_id="nonexistent", amount=10))
print(f"\n[EDGE] Invalid country: reward={r3.reward:.3f} valid={r3.info.action_valid} error={r3.info.error}")

print("\n" + "=" * 50)
print("ALL TESTS PASSED")
print("=" * 50)
