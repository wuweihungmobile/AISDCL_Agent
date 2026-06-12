"""tools/hooks/loc_budget_check.py 單元測試。

策略：
  - CLI 黑盒測試覆蓋「真實 repo CLAUDE.md ≤ 400」「外部檔 fail-open」「缺 payload fail-open」
  - 直接 import hook 模組函式測 oversized 阻斷邏輯（透過 monkeypatch SPECIAL_FILES + PROJECT_ROOT）
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "loc_budget_check.py"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def _load_hook_module():
    """以 importlib 方式載入 hook 模組（避免 sys.modules 污染）。"""
    spec = importlib.util.spec_from_file_location("_hook_loc_budget_check", HOOK_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_claude_md_under_limit():
    """目前 repo 內的 CLAUDE.md（≤ 400 行）→ exit 0 或 1（≥ 380 預警）。

    SD_09 R18 後續新增 380 預警閾值（max_lines - 20），預警 rc=1 不阻斷。
    """
    assert CLAUDE_MD.exists()
    result = _run({"tool_input": {"file_path": str(CLAUDE_MD)}})
    assert result.returncode in (0, 1), f"stderr={result.stderr}"
    # 確保非阻斷（rc != 2）
    assert result.returncode != 2, f"unexpected BLOCK: stderr={result.stderr}"


def test_oversized_claude_md_blocks(tmp_path, monkeypatch):
    """偽造 401 行的 CLAUDE.md → check_special_file 應回 2。"""
    mod = _load_hook_module()
    # 製造 401 行檔案
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("\n".join(f"line {i}" for i in range(401)), encoding="utf-8")
    # monkeypatch hook 模組的 PROJECT_ROOT 與 SPECIAL_FILES
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(mod, "SPECIAL_FILES", {"CLAUDE.md": 400}, raising=True)
    rc = mod.check_special_file(Path("CLAUDE.md"))
    assert rc == 2


def test_special_file_within_limit_passes(tmp_path, monkeypatch):
    """379 行的 CLAUDE.md（≤ 380 預警閾值）→ check_special_file 應回 0。

    SD_09 R18 後續：預警閾值 = max_lines - 20 = 380；< 380 才完全綠。
    """
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("\n".join(f"line {i}" for i in range(379)), encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(mod, "SPECIAL_FILES", {"CLAUDE.md": 400}, raising=True)
    rc = mod.check_special_file(Path("CLAUDE.md"))
    assert rc == 0


def test_special_file_at_warn_threshold_warns(tmp_path, monkeypatch):
    """390 行的 CLAUDE.md（≥ 380 預警閾值，< 400 紅線）→ rc=1（WARN 不阻斷）。

    SD_09 R18 新增抗膨脹保險 #3：預警讓 user 在撞紅線前看到剩餘 buffer。
    """
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("\n".join(f"line {i}" for i in range(390)), encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(mod, "SPECIAL_FILES", {"CLAUDE.md": 400}, raising=True)
    rc = mod.check_special_file(Path("CLAUDE.md"))
    assert rc == 1


def test_unrelated_file_outside_project_fail_open(tmp_path):
    """tmp_path 外部檔案 → normalize 失敗 → fail-open exit 0。"""
    target = tmp_path / "stray.py"
    target.write_text("y = 2\n", encoding="utf-8")
    result = _run({"tool_input": {"file_path": str(target)}})
    assert result.returncode == 0


def test_missing_file_path_fail_open():
    """payload 缺 tool_input → fail-open exit 0。"""
    result = _run({})
    assert result.returncode == 0
