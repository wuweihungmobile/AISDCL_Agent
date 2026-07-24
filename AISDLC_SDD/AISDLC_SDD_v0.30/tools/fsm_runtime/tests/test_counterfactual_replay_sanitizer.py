"""counterfactual_replay.write_report() 檔名淨化回歸測試（R39 掃描 P2 缺陷修復）.

缺陷：write_report() 組 `REPLAY-{patch.ac_id or 'unknown'}-{date}.md` 時完全未淨化
patch.ac_id（同一 ac_id 在姊妹檔 spec_patch_proposer.py:105 已正確呼叫
state_loader._sanitize_component()），導致帶 Windows 禁用字元（如 DEF-101-324
backlog 中真實存在的 `AC:042` 這種帶冒號格式）的 ac_id 在 Windows 上落盤失敗。

比照同目錄 test_state_component_sanitizer_parity.py 的攻擊向量手法，鎖定：
  - 禁用字元（`:`、`<`、`>` 等）被擋下，檔案仍可成功落盤
  - 正常合法 ac_id 不受影響（原樣通過）
  - ac_id=None / "" 時 fallback 為 'unknown' 的既有行為不變
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import counterfactual_replay as CR

_WIN_FORBIDDEN_CHARS = '<>:"|?*\\'


def _make_report() -> CR.ReplayReport:
    return CR.replay(
        CR.PatchProposal(ac_id="AC-014", guard_text="discount stacking forbidden coupon"),
        [CR.HistoricalCase(case_id="FPL-010", ac_id="AC-014",
                            failure_text="discount stacking coupon double")],
    )


def test_forbidden_chars_in_ac_id_are_sanitized(tmp_path):
    """帶 Windows 禁用字元的 ac_id（如 DEF-101-324 backlog 的 'AC:042'）不得原樣入檔名。"""
    rep = _make_report()
    for ch in _WIN_FORBIDDEN_CHARS:
        patch = CR.PatchProposal(ac_id=f"AC{ch}042", guard_text="x")
        path = CR.write_report(patch, rep, out_dir=tmp_path, today="2026-07-24")
        assert path.exists(), f"帶禁用字元 {ch!r} 的 ac_id 落盤失敗"
        assert ch not in path.name, f"檔名淨化未擋下 {ch!r}：{path.name!r}"


def test_path_traversal_ac_id_does_not_escape_target_dir(tmp_path):
    """路徑穿越輸入不得使 write_report 寫到 target_dir 之外。"""
    rep = _make_report()
    patch = CR.PatchProposal(ac_id="../../etc/passwd", guard_text="x")
    path = CR.write_report(patch, rep, out_dir=tmp_path, today="2026-07-24")
    assert path.exists()
    assert path.parent == tmp_path
    assert "/" not in path.name and "\\" not in path.name


def test_normal_ac_id_unaffected(tmp_path):
    """正常合法 ac_id（英數字、連字號）不受淨化影響，行為與修復前一致。"""
    rep = _make_report()
    patch = CR.PatchProposal(ac_id="AC-014", guard_text="x")
    path = CR.write_report(patch, rep, out_dir=tmp_path, today="2026-07-24")
    assert path.name == "REPLAY-AC-014-2026-07-24.md"


def test_none_ac_id_falls_back_to_unknown(tmp_path):
    """ac_id=None 時既有 'unknown' fallback 行為不受淨化引入影響。"""
    rep = _make_report()
    patch = CR.PatchProposal(ac_id=None, guard_text="x")
    path = CR.write_report(patch, rep, out_dir=tmp_path, today="2026-07-24")
    assert path.name == "REPLAY-unknown-2026-07-24.md"


def test_empty_string_ac_id_falls_back_to_unknown(tmp_path):
    """ac_id="" 時既有 'unknown' fallback 行為不受淨化引入影響。"""
    rep = _make_report()
    patch = CR.PatchProposal(ac_id="", guard_text="x")
    path = CR.write_report(patch, rep, out_dir=tmp_path, today="2026-07-24")
    assert path.name == "REPLAY-unknown-2026-07-24.md"
