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


def test_claude_md_long_line_blocks(tmp_path, monkeypatch):
    """CLAUDE.md 含 801 codepoint 單行 → check_claude_md_line_length 回 2（流程改善 #10a）。

    對齊 contract test_claude_md_no_long_lines：edit 當下即攔「累積敘事繞過 ≤400 行紅線」反模式。
    """
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("short\n" + "a" * 801 + "\nok\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    rc = mod.check_claude_md_line_length(Path("CLAUDE.md"))
    assert rc == 2


def test_claude_md_line_at_800_passes(tmp_path, monkeypatch):
    """CLAUDE.md 邊界 800 codepoint 單行 → 回 0（與 contract test 800 邊界一致）。"""
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("a" * 800 + "\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    assert mod.check_claude_md_line_length(Path("CLAUDE.md")) == 0


def test_claude_md_cjk_800_codepoint_passes(tmp_path, monkeypatch):
    """800 個 CJK 字（2400 bytes / 800 codepoint）→ 回 0（codepoint 計非 byte）。"""
    mod = _load_hook_module()
    fake_claude = tmp_path / "CLAUDE.md"
    fake_claude.write_text("中" * 800 + "\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    assert mod.check_claude_md_line_length(Path("CLAUDE.md")) == 0


def test_non_claude_md_skips_line_length_check(tmp_path, monkeypatch):
    """非 root CLAUDE.md（如 sprint_history.md）不受單行限制 → 回 0。"""
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    assert mod.check_claude_md_line_length(Path("docs/05_development/sprint_history.md")) == 0


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


# ── ADR-XPLAT-013 M4：`UnparseableSourceError` 的 hook 端翻譯路徑 ──────────────


def _import_check_loc_budget():
    """與 hook 同一條解析路徑載入 `check_loc_budget`（供符號同一性比對）。"""
    for extra in (PROJECT_ROOT / "tools", PROJECT_ROOT.parent / "tools" / "lib"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    import check_loc_budget  # type: ignore[import-not-found]

    return check_loc_budget


def test_unparseable_python_file_warns_and_does_not_block(tmp_path, monkeypatch, capsys):
    """🔴 語法壞掉的 `.py` → rc=1 ＋ stderr 說話，**不是** rc=0 靜默放行。

    意圖（Rule 9）：ADR-XPLAT-013 條文二把「計價不出來」由靜默回 0 改成拋
    `UnparseableSourceError`，理由是回 0 會讓「把檔弄壞」變成零預算成本。這條主張在
    **hook 側**原本是無保護的散文——`check_python_file()` 的 `except` 分支零覆蓋，
    而本 hook 掛在 PostToolUse、每次寫入都會跑：它若靜默 `return 0`，剛被寫壞的檔就
    完全沒有訊號，正是該 ADR 要關掉的失效方向。

    本鎖同時釘住「不阻斷」那一半：rc 必須是 1（WARN）而不是 2（BLOCK）——寫壞檔的
    下一個動作通常就是把它修好，把 PostToolUse 升成阻斷只會讓人關掉 hook。
    判準會在下列任一情形轉紅：`except` 分支被拿掉（例外直接炸出 traceback）、
    改回 `return 0`（rc 不再是 1）、或訊息被靜音（stderr 空）。
    """
    mod = _load_hook_module()
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)

    rc = mod.check_python_file(Path("broken.py"))

    assert rc == 1, f"解析不出來的 .py 應回 1（WARN、不阻斷），實得 {rc}"
    err = capsys.readouterr().err
    assert "broken.py" in err and "WARN" in err, (
        f"WARN 路徑沒有留下可讀的訊號（stderr={err!r}）——rc=1 但不說話等於靜默放行"
    )


def test_the_unparseable_symbol_is_the_same_object_the_pricer_raises(tmp_path, monkeypatch):
    """🔴 fail-open 缺口的鎖：hook 抓的必須**就是**計價器拋的那一個類別。

    意圖：`UnparseableSourceError` 被塞進 `loc_budget_check.py` 那個「ImportError ⇒
    `sys.exit(0)`」的 import tuple 裡。該符號一旦被改名／搬家，整支 hook 會**靜默放行**
    （CLAUDE.md 400 行紅線與單行 codepoint 紅線這兩道阻斷級檢查一起消失），而表徵與
    「一切正常」完全相同。本鎖把那個靜默事件變成會轉紅的事件：
      · 符號被改名 ⇒ `_load_hook_module()` 在 `sys.exit(0)` 上拋 SystemExit ⇒ 本測試 error；
      · 符號還在但 hook 抓成別的類別（例如自己再定義一份）⇒ 身分比對紅。
    順帶釘住「真的會被抓到」：同一個壞檔走一次 `check_python_file()` 必須是 rc=1，
    不是 traceback 冒出來。
    """
    mod = _load_hook_module()
    clb = _import_check_loc_budget()

    assert mod.UnparseableSourceError is clb.UnparseableSourceError, (
        "hook 端的 UnparseableSourceError 與 check_loc_budget 的不是同一個類別 ⇒ "
        "計價器拋的例外不會被 hook 的 except 攔到"
    )
    assert issubclass(clb.UnparseableSourceError, ValueError), (
        "ADR-XPLAT-013 條文二把它定為 ValueError 子類（既有 ValueError 消費端得以承接）"
    )

    broken = tmp_path / "still_broken.py"
    broken.write_text("class C(\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    assert mod.check_python_file(Path("still_broken.py")) == 1
