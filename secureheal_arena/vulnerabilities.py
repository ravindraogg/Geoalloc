"""
secureheal_arena/vulnerabilities.py
────────────────────────────────────
Vulnerability catalogue for the SecureHeal Arena.

Each entry defines:
  • vulnerable_code   – the code snippet with the flaw
  • patched_code      – the correct fix
  • test_code         – a test suite that validates the fix
  • vulnerability_type – classification label
  • exploit_code      – code that exploits the vulnerability

This catalogue is used by the environment to inject scenarios at ``reset()``
and to verify patches via the sandbox at ``step("run_tests")``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class VulnerabilityScenario:
    """A single vulnerability scenario injected into an episode."""
    vulnerability_type: str
    vulnerable_code: str
    patched_code: str
    test_code: str
    exploit_code: str
    description: str


# ──────────────────── Level 1 Scenarios ────────────────────────

SQL_INJECTION = VulnerabilityScenario(
    vulnerability_type="sql_injection",
    description="Classic SQL injection via string concatenation in a login query.",
    vulnerable_code='''\
def get_user(username, password, db_execute):
    """Fetch user from database by credentials."""
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    return db_execute(query)
''',
    patched_code='''\
def get_user(username, password, db_execute):
    """Fetch user from database by credentials — parameterised."""
    query = "SELECT * FROM users WHERE username=? AND password=?"
    return db_execute(query, (username, password))
''',
    test_code='''\
# ---- test suite for SQL injection fix ----
_passed = 0
_total = 3

# mock db_execute that records the query
_last_query = None
_last_params = None

def mock_db(query, params=None):
    global _last_query, _last_params
    _last_query = query
    _last_params = params
    return [{"id": 1, "username": "alice"}]

# Test 1: normal lookup works
get_user("alice", "password123", mock_db)
if _last_query and "?" in _last_query:
    _passed += 1

# Test 2: injection payload is escaped
get_user("' OR 1=1 --", "x", mock_db)
if _last_params and "' OR 1=1 --" in _last_params:
    _passed += 1

# Test 3: query uses parameterised markers
get_user("bob", "secret", mock_db)
if _last_query == "SELECT * FROM users WHERE username=? AND password=?":
    _passed += 1

__pass_rate__ = _passed / _total
''',
    exploit_code='''\
# Exploit: bypass authentication via SQL injection
result = get_user("' OR 1=1 --", "anything", mock_db)
# If the query is injectable the mock will receive a tautology query
exploit_success = "' OR 1=1 --" in _last_query if _last_query else False
''',
)


XSS_STORED = VulnerabilityScenario(
    vulnerability_type="xss_stored",
    description="Stored XSS via unsanitised user input rendered in HTML.",
    vulnerable_code='''\
def render_comment(comment_text):
    """Render a user comment as HTML."""
    return f"<div class='comment'>{comment_text}</div>"
''',
    patched_code='''\
def render_comment(comment_text):
    """Render a user comment as HTML — escaped."""
    import html
    safe = html.escape(comment_text)
    return f"<div class='comment'>{safe}</div>"
''',
    test_code='''\
_passed = 0
_total = 3

# Test 1: normal text passes through
result = render_comment("Hello world")
if "Hello world" in result:
    _passed += 1

# Test 2: script tags are escaped
result = render_comment("<script>alert('xss')</script>")
if "<script>" not in result and "&lt;script&gt;" in result:
    _passed += 1

# Test 3: quotes are escaped
result = render_comment('"><img src=x onerror=alert(1)>')
if 'onerror' not in result or '&lt;' in result:
    _passed += 1

__pass_rate__ = _passed / _total
''',
    exploit_code='''\
result = render_comment("<script>alert('xss')</script>")
exploit_success = "<script>" in result
''',
)


PATH_TRAVERSAL = VulnerabilityScenario(
    vulnerability_type="path_traversal",
    description="Path traversal via unsanitised filename in file reader.",
    vulnerable_code='''\
def read_user_file(filename, base_dir="/uploads"):
    """Read a file from the uploads directory."""
    filepath = base_dir + "/" + filename
    # Simulated file read — returns the path that would be accessed
    return filepath
''',
    patched_code='''\
def read_user_file(filename, base_dir="/uploads"):
    """Read a file from the uploads directory — path-safe."""
    import posixpath
    # Strip traversal components
    safe_name = posixpath.basename(filename)
    filepath = base_dir + "/" + safe_name
    return filepath
''',
    test_code='''\
_passed = 0
_total = 3

# Test 1: normal filename works
r = read_user_file("photo.jpg")
if r == "/uploads/photo.jpg":
    _passed += 1

# Test 2: directory traversal is blocked
r = read_user_file("../../etc/passwd")
if "/etc/passwd" not in r and "passwd" in r:
    _passed += 1

# Test 3: another traversal attempt
r = read_user_file("../config/secrets.yaml")
if "../" not in r:
    _passed += 1

__pass_rate__ = _passed / _total
''',
    exploit_code='''\
result = read_user_file("../../etc/passwd")
exploit_success = "/etc/passwd" in result
''',
)


# ──────────────────── Catalogue Registry ───────────────────────

VULNERABILITY_CATALOGUE: List[VulnerabilityScenario] = [
    SQL_INJECTION,
    XSS_STORED,
    PATH_TRAVERSAL,
]

LEVEL_1_SCENARIOS = [SQL_INJECTION]
LEVEL_2_SCENARIOS = [SQL_INJECTION, XSS_STORED]
LEVEL_3_SCENARIOS = [SQL_INJECTION, XSS_STORED, PATH_TRAVERSAL]


def get_scenarios_for_level(level: int) -> List[VulnerabilityScenario]:
    """Return the vulnerability scenarios available at a given curriculum level."""
    if level <= 1:
        return LEVEL_1_SCENARIOS
    elif level == 2:
        return LEVEL_2_SCENARIOS
    else:
        return LEVEL_3_SCENARIOS
