"""tools/hooks/claude_md_freshness.py 單元測試。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "claude_md_freshness.py"


def _run() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps({}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("_hook_freshness", HOOK_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_repo_freshness_ok():
    """目前 repo 狀態：CLAUDE.md ≤ 400 + snapshot 同步 → exit 0。

    Note: 若 Architecture Snapshot 偶有漂移，會回 1（warn）；本測試容許 0 或 1，
    但禁止 2（阻斷），因為阻斷代表 CLAUDE.md > 400 — 這違反 ADR-SD08-001。
    """
    result = _run()
    assert result.returncode in (0, 1), f"rc={result.returncode}, stderr={result.stderr}"


def test_oversized_claude_md_blocks(tmp_path, monkeypatch):
    """偽造 401 行的 CLAUDE.md → check_line_count 應回 2。"""
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("\n".join(f"line {i}" for i in range(401)), encoding="utf-8")
    monkeypatch.setattr(mod, "CLAUDE_MD", fake_claude, raising=True)
    monkeypatch.setattr(mod, "MAX_LINES", 400, raising=True)
    rc = mod.check_line_count()
    assert rc == 2


def test_normal_claude_md_passes(tmp_path, monkeypatch):
    """399 行 → check_line_count 應回 0。"""
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("\n".join(f"line {i}" for i in range(399)), encoding="utf-8")
    monkeypatch.setattr(mod, "CLAUDE_MD", fake_claude, raising=True)
    monkeypatch.setattr(mod, "MAX_LINES", 400, raising=True)
    rc = mod.check_line_count()
    assert rc == 0


def test_missing_snapshot_tool_fail_open(tmp_path, monkeypatch):
    """SNAPSHOT_TOOL 不存在 → check_snapshot_drift 應回 0（fail-open）。"""
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "SNAPSHOT_TOOL", tmp_path / "nonexistent.py", raising=True)
    rc = mod.check_snapshot_drift()
    assert rc == 0


def test_snapshot_drift_returns_warn(tmp_path, monkeypatch):
    """模擬 snapshot drift（exit 1）→ check_snapshot_drift 應回 1（warn）。"""
    mod = _load_hook_module()
    # 製造一個假的 snapshot tool 永遠 exit 1
    fake_tool = tmp_path / "fake_snapshot.py"
    fake_tool.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    monkeypatch.setattr(mod, "SNAPSHOT_TOOL", fake_tool, raising=True)
    rc = mod.check_snapshot_drift()
    assert rc == 1
