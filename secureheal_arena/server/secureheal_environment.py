"""
secureheal_arena/server/secureheal_environment.py
──────────────────────────────────────────────────
Core environment implementing reset(), step(), and state() for
the SecureHeal Arena OpenEnv environment.

Episode flow:
  reset() → inject vulnerability + anomaly → return observation
  step(action) → route action → update state → compute reward → return observation
  state()  → return internal state (for logging / debugging)
"""

from __future__ import annotations

import copy
import random
import uuid
from typing import Any, Dict, List, Optional

from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.types import Action, Observation, State

from fastmcp import FastMCP

from ..models import (
    VALID_ACTIONS,
    SecureHealAction,
    SecureHealObservation,
    SecureHealState,
)
from ..sandbox import SandboxEngine, SandboxResult
from ..vulnerabilities import (
    VulnerabilityScenario,
    get_scenarios_for_level,
)
from ..anomalies import (
    AnomalyScenario,
    select_anomaly,
)
from ..rewards import compute_reward, RewardBreakdown


class SecureHealEnvironment(MCPEnvironment):
    """SecureHeal Arena — a merged RL environment combining cybersecurity
    vulnerability detection/patching (SecureCode Arena X) with autonomous
    system recovery (DataHeal Arena).

    The agent operates in a simulated live infrastructure where:
      • Code is running and being actively attacked
      • The agent must detect vulnerabilities, simulate exploits,
        apply patches, and monitor system stability
      • All within a single long-horizon RL episode
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self, curriculum_level: int = 1):
        """Initialise the environment with MCP tools.

        Args:
            curriculum_level: 1 (easy), 2 (medium), or 3 (hard).
        """
        # Create MCP server with tools for agent interaction
        mcp = FastMCP("secureheal_arena")

        @mcp.tool
        def scan_code() -> dict:
            """Scan the current code snippet for vulnerabilities.

            Returns a report indicating vulnerability type and location.
            """
            return self._handle_scan_code()

        @mcp.tool
        def simulate_attack() -> dict:
            """Simulate an exploit against the current code.

            Runs the exploit in a sandboxed environment and reports
            whether the attack succeeded.
            """
            return self._handle_simulate_attack()

        @mcp.tool
        def apply_patch(patch_code: str) -> dict:
            """Apply a code patch to fix the vulnerability.

            Args:
                patch_code: The corrected code to replace the vulnerable snippet.

            Returns result of applying the patch.
            """
            return self._handle_apply_patch(patch_code)

        @mcp.tool
        def run_tests() -> dict:
            """Execute the test suite against the current code.

            Returns the test pass rate (0.0 to 1.0).
            """
            return self._handle_run_tests()

        @mcp.tool
        def restart_service(service_name: str) -> dict:
            """Restart a failing or degraded service.

            Args:
                service_name: Name of the service to restart (e.g. 'auth-service').
            """
            return self._handle_restart_service(service_name)

        @mcp.tool
        def clean_data() -> dict:
            """Clear corrupted data from the system cache/storage."""
            return self._handle_clean_data()

        @mcp.tool
        def reallocate_resources() -> dict:
            """Shift compute resources to stabilise overloaded services."""
            return self._handle_reallocate_resources()

        @mcp.tool
        def classify_issue(classification: str) -> dict:
            """Classify the detected anomaly type.

            Args:
                classification: The anomaly label (e.g. 'memory_spike', 'disk_pressure').
            """
            return self._handle_classify_issue(classification)

        super().__init__(mcp)

        self._curriculum_level = curriculum_level
        self._sandbox = SandboxEngine()
        self._state = SecureHealState(episode_id=str(uuid.uuid4()), step_count=0)
        self._scenario: Optional[VulnerabilityScenario] = None
        self._anomaly: Optional[AnomalyScenario] = None
        self._current_code: str = ""
        self._rng = random.Random()
        self._last_reward_breakdown: Optional[RewardBreakdown] = None

    # ━━━━━━━━━━━━━━━━━━━━━━ RESET ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """Reset the environment — inject a fresh vulnerability + anomaly.

        Args:
            seed:       Random seed for reproducibility.
            episode_id: Optional episode ID override.

        Returns:
            Initial observation for the agent.
        """
        # Seed RNG
        effective_seed = seed if seed is not None else random.randint(0, 999_999)
        self._rng = random.Random(effective_seed)

        # Select curriculum parameters
        level = kwargs.get("curriculum_level", self._curriculum_level)
        if level == 1:
            max_steps = 8
        elif level == 2:
            max_steps = 15
        else:
            max_steps = 25

        # Pick vulnerability scenario
        scenarios = get_scenarios_for_level(level)
        self._scenario = self._rng.choice(scenarios)

        # Pick anomaly
        self._anomaly = select_anomaly(level, self._rng)

        # Set current code to the vulnerable version
        self._current_code = self._scenario.vulnerable_code

        # Build initial state
        self._state = SecureHealState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            # Security layer
            vulnerability_type=self._scenario.vulnerability_type,
            vulnerability_present=True,
            exploit_possible=True,
            patch_applied=False,
            patch_code="",
            test_pass_rate=0.0,
            # Stability layer
            anomaly_type=self._anomaly.anomaly_type,
            system_stability=0.5,  # starts degraded
            cascading_failures=[],
            latency_baseline=50.0,
            latency_current=50.0 + self._anomaly.latency_spike_ms,
            services_status=dict(self._anomaly.affected_services),
            data_corrupted=self._anomaly.data_corruption,
            # Episode
            max_steps=max_steps,
            curriculum_level=level,
            seed=effective_seed,
            # Reward tracking
            r1_exploit_blocked=0.0,
            r2_test_pass_rate=0.0,
            r3_stability_delta=0.0,
            r4_cascading_cleared=0.0,
            total_reward=0.0,
            # Sandbox
            timeout_occurred=False,
            forbidden_op_detected=False,
            format_error=False,
        )

        self._last_reward_breakdown = None

        return Observation(
            done=False,
            reward=0.0,
            metadata=self._build_observation_metadata(
                action_result="Environment reset. A vulnerable system awaits your attention."
            ),
        )

    # ━━━━━━━━━━━━━━━━━━━━━━ STEP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Handle non-MCP actions (SecureHealAction direct calls)."""
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "error": f"Unknown action type: {type(action).__name__}. "
                "Use MCP tools (scan_code, simulate_attack, apply_patch, etc.) "
                "or ListToolsAction/CallToolAction."
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Execute a step — delegates to MCP tool handlers.

        Increments step count, checks episode termination, and returns
        observation with reward.
        """
        self._state.step_count += 1
        result = super().step(action, timeout_s=timeout_s, **kwargs)

        # Check termination
        if self._check_done():
            # Rebuild observation with done=True
            result = Observation(
                done=True,
                reward=result.reward if hasattr(result, 'reward') else 0.0,
                metadata=result.metadata if hasattr(result, 'metadata') else {},
            )

        return result

    async def step_async(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Async step for WebSocket handler."""
        self._state.step_count += 1
        result = await super().step_async(action, timeout_s=timeout_s, **kwargs)

        if self._check_done():
            result = Observation(
                done=True,
                reward=result.reward if hasattr(result, 'reward') else 0.0,
                metadata=result.metadata if hasattr(result, 'metadata') else {},
            )

        return result

    @property
    def state(self) -> State:
        """Return current internal state."""
        return self._state

    # ━━━━━━━━━━━━━━━━━━━━━ ACTION HANDLERS ━━━━━━━━━━━━━━━━━━━

    def _handle_scan_code(self) -> dict:
        """Scan for vulnerabilities in the current code."""
        if self._state.vulnerability_present:
            result_msg = (
                f"VULNERABILITY DETECTED: {self._scenario.vulnerability_type}\n"
                f"Description: {self._scenario.description}\n"
                f"Affected code:\n{self._current_code}"
            )
        elif self._state.patch_applied:
            result_msg = "No vulnerabilities detected. Code has been patched."
        else:
            result_msg = "No vulnerabilities detected in current scan."

        # Compute reward
        breakdown = compute_reward(self._state)
        self._update_reward_state(breakdown)

        return {
            "action": "scan_code",
            "result": result_msg,
            "vulnerability_found": self._state.vulnerability_present,
            "vulnerability_type": self._state.vulnerability_type if self._state.vulnerability_present else None,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_simulate_attack(self) -> dict:
        """Simulate an exploit against the current code."""
        if not self._scenario:
            return {"action": "simulate_attack", "result": "No scenario loaded.", "reward": 0.0}

        # Run exploit in sandbox
        context = {}
        # First execute the current code to define functions
        setup_result = self._sandbox.execute(self._current_code, context)
        if not setup_result.success:
            return {
                "action": "simulate_attack",
                "result": f"Code setup failed: {setup_result.error_message}",
                "exploit_succeeded": False,
                "reward": 0.0,
            }

        # Build mock environment for exploit
        mock_code = self._build_exploit_mock()
        combined = f"{self._current_code}\n\n{mock_code}\n\n{self._scenario.exploit_code}"
        exploit_result = self._sandbox.execute(combined)

        # Update sandbox flags
        if exploit_result.timeout:
            self._state.timeout_occurred = True
        if exploit_result.forbidden_op:
            self._state.forbidden_op_detected = True

        # Check if exploit succeeded
        exploit_succeeded = self._state.exploit_possible and not self._state.patch_applied

        if self._state.patch_applied:
            self._state.exploit_possible = False
            result_msg = "Exploit BLOCKED — the patch prevents the attack."
        elif exploit_succeeded:
            result_msg = "Exploit SUCCEEDED — the system is vulnerable!"
        else:
            result_msg = "Exploit attempt completed. No clear vulnerability path."

        breakdown = compute_reward(self._state, exploit_result)
        self._update_reward_state(breakdown)

        return {
            "action": "simulate_attack",
            "result": result_msg,
            "exploit_succeeded": exploit_succeeded,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_apply_patch(self, patch_code: str) -> dict:
        """Apply a code patch."""
        if not patch_code or not patch_code.strip():
            self._state.format_error = True
            return {
                "action": "apply_patch",
                "result": "Empty patch rejected. Provide valid code.",
                "patch_applied": False,
                "reward": -0.2,
            }

        # Validate patch in sandbox
        patch_result = self._sandbox.execute(patch_code)
        if patch_result.forbidden_op:
            self._state.forbidden_op_detected = True
            return {
                "action": "apply_patch",
                "result": "Patch contains forbidden operations and was rejected.",
                "patch_applied": False,
                "reward": -2.0,
            }

        if patch_result.timeout:
            self._state.timeout_occurred = True
            return {
                "action": "apply_patch",
                "result": "Patch execution timed out.",
                "patch_applied": False,
                "reward": -1.0,
            }

        # Accept the patch
        self._current_code = patch_code
        self._state.patch_applied = True
        self._state.patch_code = patch_code
        self._state.exploit_possible = False  # Optimistic — run_tests will verify

        # Stochastic cascading failure on patch (DataHeal contribution)
        if (
            self._anomaly
            and self._anomaly.cascading_probability > 0
            and self._rng.random() < self._anomaly.cascading_probability
            and self._state.curriculum_level >= 2
        ):
            cascade_type = self._anomaly.cascading_anomaly or "unknown_cascade"
            self._state.cascading_failures.append(cascade_type)
            self._state.system_stability = max(0.1, self._state.system_stability - 0.2)
            self._state.latency_current += 50.0
            result_msg = (
                f"Patch applied, but a cascading failure triggered: {cascade_type}. "
                "System stability decreased."
            )
        else:
            result_msg = "Patch applied successfully. Run tests to verify the fix."

        breakdown = compute_reward(self._state, patch_result)
        self._update_reward_state(breakdown)

        return {
            "action": "apply_patch",
            "result": result_msg,
            "patch_applied": True,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_run_tests(self) -> dict:
        """Run the test suite against the current code."""
        if not self._scenario:
            return {"action": "run_tests", "result": "No scenario loaded.", "reward": 0.0}

        test_result = self._sandbox.execute_tests(
            self._current_code, self._scenario.test_code
        )

        if test_result.timeout:
            self._state.timeout_occurred = True
        if test_result.forbidden_op:
            self._state.forbidden_op_detected = True

        pass_rate = float(test_result.return_value) if test_result.return_value is not None else 0.0
        self._state.test_pass_rate = pass_rate

        # If tests pass fully and patch was applied, exploit is definitely blocked
        if pass_rate >= 0.9 and self._state.patch_applied:
            self._state.exploit_possible = False

        result_msg = f"Test suite completed. Pass rate: {pass_rate:.1%}"
        if pass_rate >= 0.9:
            result_msg += " — All tests passing!"
        elif pass_rate > 0:
            result_msg += " — Some tests failing."
        else:
            result_msg += " — Tests failed."

        breakdown = compute_reward(self._state, test_result)
        self._update_reward_state(breakdown)

        return {
            "action": "run_tests",
            "result": result_msg,
            "pass_rate": pass_rate,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_restart_service(self, service_name: str) -> dict:
        """Restart a service."""
        if service_name not in self._state.services_status:
            available = list(self._state.services_status.keys())
            return {
                "action": "restart_service",
                "result": f"Unknown service '{service_name}'. Available: {available}",
                "reward": -0.1,
            }

        old_status = self._state.services_status[service_name]
        self._state.services_status[service_name] = "up"

        # Improve stability
        if old_status in ("down", "degraded"):
            self._state.system_stability = min(1.0, self._state.system_stability + 0.15)
            self._state.latency_current = max(
                self._state.latency_baseline,
                self._state.latency_current - 40.0,
            )

        result_msg = f"Service '{service_name}' restarted ({old_status} → up)."

        breakdown = compute_reward(self._state)
        self._update_reward_state(breakdown)

        return {
            "action": "restart_service",
            "result": result_msg,
            "service": service_name,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_clean_data(self) -> dict:
        """Clear corrupted data."""
        if self._state.data_corrupted:
            self._state.data_corrupted = False
            self._state.system_stability = min(1.0, self._state.system_stability + 0.1)
            result_msg = "Corrupted data cleared. System stability improved."
        else:
            result_msg = "No data corruption detected. Action had no effect."

        breakdown = compute_reward(self._state)
        self._update_reward_state(breakdown)

        return {
            "action": "clean_data",
            "result": result_msg,
            "data_corrupted": self._state.data_corrupted,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_reallocate_resources(self) -> dict:
        """Shift compute resources to stabilise services."""
        improvement = 0.1 + self._rng.uniform(0, 0.1)
        self._state.system_stability = min(1.0, self._state.system_stability + improvement)
        self._state.latency_current = max(
            self._state.latency_baseline,
            self._state.latency_current - 30.0,
        )

        # Can resolve cascading failures
        if self._state.cascading_failures:
            resolved = self._state.cascading_failures.pop(0)
            result_msg = f"Resources reallocated. Resolved cascading failure: {resolved}."
        else:
            result_msg = f"Resources reallocated. Stability improved by {improvement:.0%}."

        breakdown = compute_reward(self._state)
        self._update_reward_state(breakdown)

        return {
            "action": "reallocate_resources",
            "result": result_msg,
            "stability": self._state.system_stability,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    def _handle_classify_issue(self, classification: str) -> dict:
        """Classify the anomaly type."""
        correct = classification.lower().strip() == self._state.anomaly_type.lower().strip()

        if correct:
            self._state.system_stability = min(1.0, self._state.system_stability + 0.05)
            result_msg = f"Correct classification: {classification}. Stability bonus applied."
        else:
            result_msg = (
                f"Incorrect classification: '{classification}'. "
                f"The actual anomaly is different."
            )

        breakdown = compute_reward(self._state)
        self._update_reward_state(breakdown)

        return {
            "action": "classify_issue",
            "result": result_msg,
            "correct": correct,
            "reward": breakdown.total,
            "done": self._check_done(),
            **self._build_observation_metadata(action_result=result_msg),
        }

    # ━━━━━━━━━━━━━━━━━━━━━ HELPERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_observation_metadata(self, action_result: str = "") -> dict:
        """Build the metadata dict that mirrors SecureHealObservation fields."""
        return {
            "code_snippet": self._current_code,
            "system_logs": self._build_system_logs(),
            "latency_metrics": {
                "baseline_ms": self._state.latency_baseline,
                "current_ms": self._state.latency_current,
                "delta_ms": self._state.latency_current - self._state.latency_baseline,
            },
            "error_states": [
                s for s, status in self._state.services_status.items()
                if status != "up"
            ],
            "anomaly_flags": (
                [self._state.anomaly_type] + list(self._state.cascading_failures)
            ),
            "episode_step": self._state.step_count,
            "max_steps": self._state.max_steps,
            "available_actions": VALID_ACTIONS,
            "action_result": action_result,
            "vulnerability_present": self._state.vulnerability_present,
            "patch_applied": self._state.patch_applied,
            "test_pass_rate": self._state.test_pass_rate,
            "system_stability": self._state.system_stability,
            "services_status": dict(self._state.services_status),
        }

    def _build_system_logs(self) -> list:
        """Generate realistic-looking system log lines."""
        logs = []
        for svc, status in self._state.services_status.items():
            if status == "down":
                logs.append(f"[ERROR] {svc}: service unreachable — connection refused")
            elif status == "degraded":
                logs.append(f"[WARN]  {svc}: response time elevated ({self._state.latency_current:.0f}ms)")
            else:
                logs.append(f"[INFO]  {svc}: healthy")

        if self._state.data_corrupted:
            logs.append("[ERROR] cache-layer: data integrity check FAILED")

        for cf in self._state.cascading_failures:
            logs.append(f"[CRIT]  cascading failure active: {cf}")

        if self._state.vulnerability_present and not self._state.patch_applied:
            logs.append(f"[SEC]   vulnerability detected: {self._state.vulnerability_type}")

        return logs

    def _build_exploit_mock(self) -> str:
        """Build mock infrastructure code for exploit simulation."""
        return """\
# Mock DB execute for exploit simulation
_last_query = None
_last_params = None

def mock_db(query, params=None):
    global _last_query, _last_params
    _last_query = query
    _last_params = params
    return [{"id": 1, "username": "test"}]
"""

    def _check_done(self) -> bool:
        """Check if the episode should terminate."""
        # Max steps reached
        if self._state.step_count >= self._state.max_steps:
            return True

        # Win condition: vulnerability patched + tests passing + system stable
        if (
            self._state.patch_applied
            and self._state.test_pass_rate >= 0.9
            and self._state.system_stability >= 0.8
            and not self._state.cascading_failures
        ):
            return True

        return False

    def _update_reward_state(self, breakdown: RewardBreakdown) -> None:
        """Persist reward breakdown to state for logging."""
        self._state.r1_exploit_blocked = breakdown.r1_exploit_blocked
        self._state.r2_test_pass_rate = breakdown.r2_test_pass_rate
        self._state.r3_stability_delta = breakdown.r3_stability_delta
        self._state.r4_cascading_cleared = breakdown.r4_cascading_cleared
        self._state.total_reward += breakdown.total
        self._last_reward_breakdown = breakdown

    # ━━━━━━━━━━━━━━━ LATENCY DEGRADATION ━━━━━━━━━━━━━━━━━━━━━

    def _degrade_latency(self) -> None:
        """Called each step — latency worsens if the agent delays."""
        if self._state.step_count > 3 and self._state.vulnerability_present:
            self._state.latency_current += 10.0 * self._rng.uniform(0.5, 1.5)
            self._state.system_stability = max(
                0.0, self._state.system_stability - 0.02
            )
