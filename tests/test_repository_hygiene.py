import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_env_files_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = result.stdout.splitlines()
    exposed = [
        path
        for path in tracked
        if path.endswith(".env.production") or ".env.production." in path
    ]
    assert exposed == []


def test_gitignore_blocks_env_variants_but_keeps_examples():
    patterns = [
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    ]
    assert ".env.*" in patterns
    assert "!.env.example" in patterns
    assert "!backend/.env.example" in patterns
