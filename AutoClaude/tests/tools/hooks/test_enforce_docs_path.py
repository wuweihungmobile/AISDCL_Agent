"""tools/hooks/enforce_docs_path.py 單元測試。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "enforce_docs_path.py"


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_docs_subdir_md_allowed():
    """Write 到 docs/05_development/foo.md → exit 0。"""
    payload = {"tool_input": {"file_path": str(PROJECT_ROOT / "docs" / "05_development" / "foo.md")}}
    result = _run(payload)
    assert result.returncode == 0, f"stderr={result.stderr}"


def test_random_md_blocked():
    """Write 到 random/foo.md → exit 2 阻斷。"""
    payload = {"tool_input": {"file_path": str(PROJECT_ROOT / "random" / "foo.md")}}
    result = _run(payload)
    assert result.returncode == 2
    assert "違反" in result.stderr or "BLOCK" in result.stderr or "阻斷" in result.stderr


def test_python_file_passthrough():
    """非 .md（tests/x.py）→ exit 0 略過。"""
    payload = {"tool_input": {"file_path": str(PROJECT_ROOT / "tests" / "x.py")}}
    result = _run(payload)
    assert result.returncode == 0


def test_root_claude_md_whitelisted():
    """根層 CLAUDE.md → exit 0（白名單）。"""
    payload = {"tool_input": {"file_path": str(PROJECT_ROOT / "CLAUDE.md")}}
    result = _run(payload)
    assert result.returncode == 0


def test_adr_subdir_md_allowed():
    """Write 到 docs/04_planning/ADR/ADR-XXX.md → exit 0。"""
    payload = {
        "tool_input": {
            "file_path": str(PROJECT_ROOT / "docs" / "04_planning" / "ADR" / "ADR-test.md")
        }
    }
    result = _run(payload)
    assert result.returncode == 0
