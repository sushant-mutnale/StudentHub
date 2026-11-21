"""Regression coverage for the CI pytest console-script invocation."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _pytest_console_script():
    candidate = Path(sys.executable).with_name(
        "pytest.exe" if os.name == "nt" else "pytest"
    )
    if candidate.exists():
        return str(candidate)
    return shutil.which("pytest")


@pytest.mark.parametrize("target", ["tests/", "backend/tests/"])
def test_pytest_console_script_can_collect_ci_suites(target):
    """CI invokes pytest directly; both suites must collect from the root."""
    executable = _pytest_console_script()
    assert executable, "pytest console script not found"

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [executable, target, "--collect-only", "-q"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "No module named 'backend'" not in result.stderr


def _ci_redis_port():
    ci_path = PROJECT_ROOT / ".github/workflows/ci.yml"
    ci_config = ci_path.read_text(encoding="utf-8")
    ports = set(re.findall(r'REDIS_PORT:\s*"(\d+)"', ci_config))
    assert len(ports) == 1, f"expected one CI Redis port, found {ports}"
    return ports.pop()


@pytest.mark.parametrize(
    "conftest",
    ["tests/conftest.py", "backend/tests/conftest.py"],
)
def test_conftest_uses_ci_redis_port(conftest):
    """Both test suites must use the Redis port exposed by the CI service."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("REDIS_PORT", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy; "
                f"runpy.run_path({conftest!r}); "
                "from backend.config import settings; "
                "print(settings.redis_port)"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == _ci_redis_port()


@pytest.mark.parametrize(
    "conftest",
    ["tests/conftest.py", "backend/tests/conftest.py"],
)
def test_conftest_forces_local_mongo(conftest):
    """Tests must never inherit the cloud MongoDB URI from backend/.env."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("MONGODB_URI", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy; "
                f"runpy.run_path({conftest!r}); "
                "from backend.config import settings; "
                "print(settings.mongodb_uri == 'mongodb://localhost:27017')"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "True"
