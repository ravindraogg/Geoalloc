"""
secureheal_arena/sandbox.py
────────────────────────────
Isolated code execution engine for the SecureHeal Arena.

Provides a constrained sandbox that:
  • Executes code in a restricted namespace (no builtins abuse)
  • Enforces a 5-second hard timeout per execution
  • Blocks forbidden operations (file I/O, network, os, subprocess, etc.)
  • Returns structured results including stdout, stderr, success flag
"""

from __future__ import annotations

import io
import re
import sys
import signal
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# ────────────────────── Constants ──────────────────────────────

TIMEOUT_SECONDS = 5

# Patterns that must NEVER appear in agent-submitted code
FORBIDDEN_PATTERNS = [
    r"\bimport\s+os\b",
    r"\bfrom\s+os\b",
    r"\bimport\s+sys\b",
    r"\bfrom\s+sys\b",
    r"\bimport\s+subprocess\b",
    r"\bfrom\s+subprocess\b",
    r"\bimport\s+socket\b",
    r"\bfrom\s+socket\b",
    r"\bimport\s+shutil\b",
    r"\bfrom\s+shutil\b",
    r"\bopen\s*\(",
    r"\bexec\s*\(",
    r"\beval\s*\(",
    r"\b__import__\s*\(",
    r"\bglobals\s*\(",
    r"\blocals\s*\(",
    r"\bcompile\s*\(",
    r"\bgetattr\s*\(",
    r"\bsetattr\s*\(",
    r"\bdelattr\s*\(",
]


# ────────────────────── Result Dataclass ───────────────────────

@dataclass
class SandboxResult:
    """Structured result from sandbox execution."""
    stdout: str = ""
    stderr: str = ""
    success: bool = False
    timeout: bool = False
    forbidden_op: bool = False
    format_error: bool = False
    error_message: str = ""
    return_value: Any = None


# ────────────────────── Safe Import ────────────────────────────

# Modules that are safe for test/patch code to import
ALLOWED_MODULES = frozenset({
    "html", "posixpath", "re", "math", "json",
    "collections", "string", "functools", "itertools",
    "hashlib", "hmac", "base64", "binascii",
    "copy", "dataclasses", "typing",
})


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Restricted __import__ that only allows whitelisted modules."""
    if name not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")
    return __builtins__["__import__"](name, globals, locals, fromlist, level) if isinstance(__builtins__, dict) else __import__(name, globals, locals, fromlist, level)


# ────────────────────── Safe Builtins ──────────────────────────

SAFE_BUILTINS = {
    "__import__": _safe_import,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "id": id,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


# ────────────────────── Sandbox Engine ─────────────────────────

class SandboxEngine:
    """Executes code snippets in a restricted, time-boxed namespace.

    Usage::

        engine = SandboxEngine()
        result = engine.execute("print(1 + 1)")
        assert result.success
        assert result.stdout.strip() == "2"
    """

    def __init__(self, timeout: int = TIMEOUT_SECONDS):
        self.timeout = timeout

    # ── public API ──

    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> SandboxResult:
        """Execute *code* inside a safe sandbox.

        Args:
            code:    Python source to run.
            context: Extra variables injected into the namespace.

        Returns:
            SandboxResult with stdout/stderr/flags.
        """
        result = SandboxResult()

        # 1. Static analysis — check for forbidden patterns
        if self._has_forbidden_ops(code):
            result.forbidden_op = True
            result.error_message = "Forbidden operation detected in code."
            return result

        # 2. Build restricted namespace
        namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
        if context:
            namespace.update(context)

        # 3. Execute with timeout
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        try:
            # On Windows, signal.SIGALRM is not available.
            # Use a threading-based timeout fallback.
            if sys.platform == "win32":
                result = self._execute_with_thread_timeout(code, namespace, stdout_buf, stderr_buf, result)
            else:
                result = self._execute_with_signal_timeout(code, namespace, stdout_buf, stderr_buf, result)
        except Exception as exc:  # noqa: BLE001
            result.stderr = traceback.format_exc()
            result.error_message = str(exc)

        return result

    def execute_tests(self, code: str, test_code: str) -> SandboxResult:
        """Run *test_code* against *code* and return pass-rate in return_value.

        The test code should set a variable ``__pass_rate__`` (float 0-1) in
        its namespace.  If it doesn't, the engine infers pass/fail from the
        absence of exceptions.
        """
        combined = f"{code}\n\n{test_code}"
        result = self.execute(combined)
        if result.success and result.return_value is None:
            # If the test code didn't crash, count that as 100% pass
            result.return_value = 1.0
        elif not result.success:
            result.return_value = 0.0
        return result

    # ── internals ──

    @staticmethod
    def _has_forbidden_ops(code: str) -> bool:
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                return True
        return False

    def _execute_with_signal_timeout(
        self, code, namespace, stdout_buf, stderr_buf, result
    ) -> SandboxResult:
        """POSIX implementation using SIGALRM."""

        def _timeout_handler(signum, frame):
            raise TimeoutError("Sandbox execution timed out")

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(self.timeout)
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compile(code, "<sandbox>", "exec"), namespace)  # noqa: S102
            result.success = True
            result.stdout = stdout_buf.getvalue()
            result.stderr = stderr_buf.getvalue()
            # Grab __pass_rate__ if tests set it
            if "__pass_rate__" in namespace:
                result.return_value = float(namespace["__pass_rate__"])
        except TimeoutError:
            result.timeout = True
            result.error_message = f"Execution timed out after {self.timeout}s"
        except Exception as exc:  # noqa: BLE001
            result.stderr = stderr_buf.getvalue() + "\n" + traceback.format_exc()
            result.error_message = str(exc)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        return result

    def _execute_with_thread_timeout(
        self, code, namespace, stdout_buf, stderr_buf, result
    ) -> SandboxResult:
        """Windows-compatible implementation using threading.

        Note: On Windows, tight GIL-holding loops (``while True: pass``)
        cannot be interrupted.  The production deployment target is Linux
        (HF Spaces) where SIGALRM handles this correctly.  On Windows
        the daemon thread is simply abandoned on timeout.
        """
        import threading

        exec_error: Optional[Exception] = None
        exec_success = False

        def _run():
            nonlocal exec_error, exec_success
            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(compile(code, "<sandbox>", "exec"), namespace)  # noqa: S102
                exec_success = True
            except Exception as exc:  # noqa: BLE001
                exec_error = exc

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            result.timeout = True
            result.error_message = f"Execution timed out after {self.timeout}s"
            return result

        if exec_success:
            result.success = True
            result.stdout = stdout_buf.getvalue()
            result.stderr = stderr_buf.getvalue()
            if "__pass_rate__" in namespace:
                result.return_value = float(namespace["__pass_rate__"])
        else:
            result.stderr = stderr_buf.getvalue()
            if exec_error:
                result.stderr += "\n" + "".join(
                    traceback.format_exception(type(exec_error), exec_error, exec_error.__traceback__)
                )
                result.error_message = str(exec_error)

        return result
