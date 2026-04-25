"""
tests/test_environment_local.py
────────────────────────────────
Local integration test for the SecureHeal Arena environment.

Validates the complete episode loop WITHOUT needing OpenEnv server
infrastructure.  Tests the environment engine directly.

Run: python -m pytest tests/test_environment_local.py -v
  or: python tests/test_environment_local.py
"""

from __future__ import annotations

import sys
import os

# Add project root to path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secureheal_arena.sandbox import SandboxEngine
from secureheal_arena.vulnerabilities import (
    SQL_INJECTION,
    XSS_STORED,
    PATH_TRAVERSAL,
    get_scenarios_for_level,
)
from secureheal_arena.anomalies import (
    MEMORY_SPIKE,
    select_anomaly,
)
from secureheal_arena.rewards import compute_reward
from secureheal_arena.models import SecureHealState


def test_sandbox_basic():
    """Test sandbox can execute simple code."""
    engine = SandboxEngine()
    result = engine.execute("x = 1 + 1\nprint(x)")
    assert result.success, f"Sandbox failed: {result.error_message}"
    assert "2" in result.stdout
    print("[PASS] Sandbox basic execution works")


def test_sandbox_timeout():
    """Test sandbox enforces timeout."""
    engine = SandboxEngine(timeout=1)
    result = engine.execute("while True: pass")
    assert result.timeout, "Timeout should have been triggered"
    print("[PASS] Sandbox timeout enforcement works")


def test_sandbox_forbidden_ops():
    """Test sandbox blocks forbidden operations."""
    engine = SandboxEngine()

    forbidden_codes = [
        "import os",
        "import subprocess",
        "from os import path",
        "open('file.txt')",
        "eval('1+1')",
        "__import__('os')",
    ]

    for code in forbidden_codes:
        result = engine.execute(code)
        assert result.forbidden_op, f"Should have blocked: {code}"

    print("[PASS] Sandbox forbidden operations detection works")


def test_vulnerability_test_suite():
    """Test that vulnerability test suites work in sandbox."""
    engine = SandboxEngine()

    # Test SQL injection — vulnerable code should fail tests
    result = engine.execute_tests(
        SQL_INJECTION.vulnerable_code,
        SQL_INJECTION.test_code,
    )
    pass_rate = float(result.return_value) if result.return_value is not None else 0.0
    print(f"  SQL injection (vulnerable): pass_rate = {pass_rate:.1%}")
    assert pass_rate < 1.0, "Vulnerable code should not pass all tests"

    # Test SQL injection — patched code should pass tests
    result = engine.execute_tests(
        SQL_INJECTION.patched_code,
        SQL_INJECTION.test_code,
    )
    pass_rate = float(result.return_value) if result.return_value is not None else 0.0
    print(f"  SQL injection (patched):    pass_rate = {pass_rate:.1%}")
    assert pass_rate >= 0.9, f"Patched code should pass tests, got {pass_rate}"

    print("[PASS] Vulnerability test suites work correctly")


def test_xss_test_suite():
    """Test XSS vulnerability test suite."""
    engine = SandboxEngine()

    # Vulnerable
    result = engine.execute_tests(
        XSS_STORED.vulnerable_code,
        XSS_STORED.test_code,
    )
    pass_rate = float(result.return_value) if result.return_value is not None else 0.0
    print(f"  XSS stored (vulnerable): pass_rate = {pass_rate:.1%}")

    # Patched
    result = engine.execute_tests(
        XSS_STORED.patched_code,
        XSS_STORED.test_code,
    )
    pass_rate = float(result.return_value) if result.return_value is not None else 0.0
    print(f"  XSS stored (patched):    pass_rate = {pass_rate:.1%}")
    assert pass_rate >= 0.9, f"Patched code should pass tests, got {pass_rate}"

    print("[PASS] XSS test suite works correctly")


def test_path_traversal_test_suite():
    """Test path traversal vulnerability test suite."""
    engine = SandboxEngine()

    # Vulnerable
    result = engine.execute_tests(
        PATH_TRAVERSAL.vulnerable_code,
        PATH_TRAVERSAL.test_code,
    )
    pass_rate = float(result.return_value) if result.return_value is not None else 0.0
    print(f"  Path traversal (vulnerable): pass_rate = {pass_rate:.1%}")

    # Patched
    result = engine.execute_tests(
        PATH_TRAVERSAL.patched_code,
        PATH_TRAVERSAL.test_code,
    )
    pass_rate = float(result.return_value) if result.return_value is not None else 0.0
    print(f"  Path traversal (patched):    pass_rate = {pass_rate:.1%}")
    assert pass_rate >= 0.9, f"Patched code should pass tests, got {pass_rate}"

    print("[PASS] Path traversal test suite works correctly")


def test_curriculum_levels():
    """Test that curriculum levels return appropriate scenarios."""
    l1 = get_scenarios_for_level(1)
    l2 = get_scenarios_for_level(2)
    l3 = get_scenarios_for_level(3)

    assert len(l1) == 1, f"Level 1 should have 1 scenario, got {len(l1)}"
    assert len(l2) == 2, f"Level 2 should have 2 scenarios, got {len(l2)}"
    assert len(l3) == 3, f"Level 3 should have 3 scenarios, got {len(l3)}"

    print("[PASS] Curriculum levels are correctly configured")


def test_reward_computation():
    """Test reward function with different state configurations."""
    # State where nothing is fixed
    state = SecureHealState(
        episode_id="test",
        step_count=1,
        vulnerability_present=True,
        exploit_possible=True,
        patch_applied=False,
        test_pass_rate=0.0,
        system_stability=0.3,
        cascading_failures=["disk_pressure"],
    )

    breakdown = compute_reward(state)
    print(f"  Unfixed state: total={breakdown.total:.3f} (r1={breakdown.r1_exploit_blocked}, r2={breakdown.r2_test_pass_rate}, r3={breakdown.r3_stability_delta}, r4={breakdown.r4_cascading_cleared})")
    assert breakdown.total < 0, "Unfixed state should have negative reward"

    # State where everything is fixed
    state.patch_applied = True
    state.exploit_possible = False
    state.vulnerability_present = False
    state.test_pass_rate = 1.0
    state.system_stability = 1.0
    state.cascading_failures = []

    breakdown = compute_reward(state)
    print(f"  Fixed state:   total={breakdown.total:.3f} (r1={breakdown.r1_exploit_blocked}, r2={breakdown.r2_test_pass_rate}, r3={breakdown.r3_stability_delta}, r4={breakdown.r4_cascading_cleared})")
    assert breakdown.total > 0.5, f"Fixed state should have high reward, got {breakdown.total}"

    print("[PASS] Reward computation works correctly")


def test_anomaly_selection():
    """Test anomaly selection for different levels."""
    import random
    rng = random.Random(42)

    a1 = select_anomaly(1, rng)
    assert a1.anomaly_type == "memory_spike", f"Level 1 should give memory_spike, got {a1.anomaly_type}"

    # Level 3 should draw from full catalogue
    types = set()
    for _ in range(50):
        a = select_anomaly(3, rng)
        types.add(a.anomaly_type)
    assert len(types) > 1, "Level 3 should have multiple anomaly types"

    print("[PASS] Anomaly selection works correctly")


def test_full_episode_loop():
    """Simulate a complete episode loop — the critical integration test.

    This tests the environment logic without needing the FastAPI server.
    It directly calls the action handlers.
    """
    print("\n--- Full Episode Simulation ---")

    # We'll test the environment logic by importing and constructing it
    # This requires openenv to be installed. If not available, skip.
    try:
        from secureheal_arena.server.secureheal_environment import SecureHealEnvironment
    except ImportError as e:
        print(f"  [SKIP] Skipping full episode test (openenv not installed): {e}")
        return

    env = SecureHealEnvironment(curriculum_level=1)

    # Reset
    obs = env.reset(seed=42)
    print(f"  Step 0 (reset): done={obs.done}")
    assert not obs.done

    # Step 1: Scan code
    result = env._handle_scan_code()
    print(f"  Step 1 (scan_code): vulnerability_found={result.get('vulnerability_found')}")
    assert result["vulnerability_found"] is True

    # Step 2: Simulate attack
    result = env._handle_simulate_attack()
    print(f"  Step 2 (simulate_attack): exploit_succeeded={result.get('exploit_succeeded')}")

    # Step 3: Apply patch (use the known good patch)
    from secureheal_arena.vulnerabilities import SQL_INJECTION
    result = env._handle_apply_patch(SQL_INJECTION.patched_code)
    print(f"  Step 3 (apply_patch): patch_applied={result.get('patch_applied')}")
    assert result["patch_applied"] is True

    # Step 4: Run tests
    result = env._handle_run_tests()
    print(f"  Step 4 (run_tests): pass_rate={result.get('pass_rate')}")
    assert result["pass_rate"] >= 0.9

    # Step 5: Classify issue
    result = env._handle_classify_issue("memory_spike")
    print(f"  Step 5 (classify_issue): correct={result.get('correct')}")
    assert result["correct"] is True

    # Step 6: Restart service
    result = env._handle_restart_service("auth-service")
    print(f"  Step 6 (restart_service): result={result.get('result')}")

    # Step 7: Reallocate resources
    result = env._handle_reallocate_resources()
    print(f"  Step 7 (reallocate_resources): stability={result.get('stability')}")

    # Check final state
    final_state = env.state
    print(f"\n  Final state:")
    print(f"    patch_applied:     {final_state.patch_applied}")
    print(f"    test_pass_rate:    {final_state.test_pass_rate}")
    print(f"    system_stability:  {final_state.system_stability}")
    print(f"    total_reward:      {final_state.total_reward:.3f}")
    print(f"    cascading_failures: {final_state.cascading_failures}")

    print("[PASS] Full episode simulation completed successfully")


# ────────────────────── Run All Tests ──────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  SecureHeal Arena — Local Environment Tests")
    print("=" * 60)
    print()

    tests = [
        test_sandbox_basic,
        test_sandbox_timeout,
        test_sandbox_forbidden_ops,
        test_vulnerability_test_suite,
        test_xss_test_suite,
        test_path_traversal_test_suite,
        test_curriculum_levels,
        test_reward_computation,
        test_anomaly_selection,
        test_full_episode_loop,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            print(f"\n> {test_fn.__name__}")
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL]: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
