import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PREFIXES = ("Success:", "Found ")


def _normalize(line):
    return line.strip().replace("\\", "/")


def new_findings(current, baseline):
    current_lines = [
        _normalize(line)
        for line in current
        if line.strip() and not line.strip().startswith(IGNORED_PREFIXES)
    ]
    baseline_lines = {_normalize(line) for line in baseline if line.strip()}
    return [line for line in current_lines if line not in baseline_lines]


def run_tool(command):
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.splitlines() + result.stderr.splitlines()
    return new_findings(lines, []), result.returncode


def compare_to_baseline(command, baseline_path):
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    current = result.stdout.splitlines() + result.stderr.splitlines()
    baseline_file = ROOT / baseline_path
    baseline = (
        baseline_file.read_text(encoding="utf-8").splitlines()
        if baseline_file.exists()
        else []
    )
    return new_findings(current, baseline)


def main():
    failures = []

    flake8_findings = compare_to_baseline(
        [sys.executable, "-m", "flake8", "backend", "tests"],
        "tools/flake8-baseline.txt",
    )
    if flake8_findings:
        failures.append("New flake8 findings:")
        failures.extend(flake8_findings)

    mypy_findings = compare_to_baseline(
        [sys.executable, "-m", "mypy", "backend"],
        "tools/mypy-baseline.txt",
    )
    if mypy_findings:
        failures.append("New mypy findings:")
        failures.extend(mypy_findings)

    if failures:
        print("\n".join(failures))
        return 1

    print("Quality gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
