"""tests/tools/test_check_loc_budget_tier_headroom_warn.py — 單檔 tier 餘裕預警帶
（[TIER-WARN]）回歸鎖（R60，承接 DEF-101-526 明文交棒的 R60 候選）。

DEF-101-526 記載的治理衝突：在 LOC tier **滿載檔**上「修 lint」與「守 LOC 預算」
互斥，而兩者都是硬閘——該輪在 `pg_state_repository.py`（400/400）修 4 處 E501，
斷行後實測 `[TIER] adapter<=400 … 406 > 400 (+6)`，LOC 閘門當場紅（+5 來自 4 處斷行、
+1 來自 ruff I001 自動修復）。當時的處置是行內 noqa 緩解，並把「衝突本身」交棒：
「把『LOC tier 滿載檔 × lint 斷行』列為固定掃描檢查點（如 `check_loc_budget` 對餘裕
≤ 3 行的檔印 warning），讓下一個踩到的人事先知道」。本檔即該檢查點的回歸鎖。

鎖的不變量：
  1. 門檻常數存在，且**刻意不是 fail**：只有在 band 內的檔不得讓 rc 變 1
     （現況 3 支合法滿載檔，改成 fail 會當場擋住 repo）。
  2. 邊界精確：餘裕 == TIER_WARN_MARGIN 進 band；== +1 不進；已破預算的檔不進
     band（由既有 [TIER] 阻塞段接手，避免同一件事印兩段）。
  3. 標籤隔離：tier band 用 `[TIER-WARN]`，**不得**吐出 `[WARN]` ——後者被
     tests/contract/test_loc_budget_tiered.py::test_warn_band_boundary_and_rc_invariant
     以 `("[WARN]" in out) is expect_warn` 釘為總量預警帶專屬訊號，共用標籤會讓那道鎖
     在 repo 現況下恆真而失效。
  4. JSON ↔ 文字一致（同 total band 先例：以 --json 取證的自動化才看得到本訊號）。
  5. 真 repo 錨點：DEF-101-526 的當事檔 `pg_state_repository.py` 必須真的被命中
     ——這是交棒條目的驗收條件本身，不能只用合成資料證明。

鑑別力（R60 實測）：把 `TIER_WARN_MARGIN` 改成 0 → 邊界與真 repo 錨點測試轉紅；
把 tier band 的標籤改回 `[WARN]` → 標籤隔離測試轉紅。兩次還原後全綠。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import check_loc_budget as clb  # noqa: E402


def _report(rel: str, loc: int, budget: int, tier: str = "adapter") -> clb.FileReport:
    return clb.FileReport(
        rel_path=rel, loc=loc, tier=tier, budget=budget,
        over_by=max(0, loc - budget), override_reason=None,
    )


@pytest.fixture
def isolated(monkeypatch: pytest.MonkeyPatch):
    """把 check() 的外部依賴全部隔離：不讀真檔、不寫 .loc_baseline、不觸發總量帶。"""
    monkeypatch.setattr(clb, "load_overrides", lambda: {})
    monkeypatch.setattr(clb, "check_special_files", lambda: [])
    # baseline 給極大值 → cap 遠高於 total → total_violation / total_warn_band 皆 False，
    # 使本檔的斷言只反映 tier band 一件事。
    monkeypatch.setattr(clb, "read_baseline", lambda: 10_000_000)
    monkeypatch.setattr(
        clb, "write_baseline",
        lambda _v: pytest.fail("check() 不應在 baseline 已存在時寫檔"),
    )

    def _use(reports: list[clb.FileReport]) -> None:
        monkeypatch.setattr(clb, "build_reports", lambda _ov: reports)

    return _use


# --- 不變量 1：非阻塞 ---

def test_margin_constant_is_positive_and_documented() -> None:
    assert isinstance(clb.TIER_WARN_MARGIN, int)
    assert clb.TIER_WARN_MARGIN > 0, (
        "TIER_WARN_MARGIN ≤ 0 等於關掉 DEF-101-526 交棒的檢查點"
    )


def test_full_tier_file_warns_but_does_not_fail(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """餘裕 0（滿載）→ 印 [TIER-WARN] 但 rc 必須為 0。

    刻意不改成 fail：repo 現況有 3 支合法滿載檔（pg_state_repository.py 400/400、
    models/escalation.py 150/150、steps_orchestrator/_impl.py 500/500），改 fail
    會當場把它們變成閘門紅。
    """
    isolated([_report("autoclaude/infra/repositories/x.py", 400, 400)])
    rc = clb.check()
    out = capsys.readouterr().out
    assert rc == 0, f"tier 預警帶必須非阻塞，實得 rc={rc}\n{out}"
    assert "[TIER-WARN]" in out
    assert "violations=0" in out, "預警帶不得被算進 violations 計數"
    assert "[TIER]" not in out.replace("[TIER-WARN]", ""), (
        "未破預算的檔不得出現在 [TIER] 阻塞段"
    )


# --- 不變量 2：邊界精確 ---

@pytest.mark.parametrize("headroom,expect_warn", [(0, True), (1, True), (None, None)])
def test_boundary_at_margin_and_one_beyond(
    headroom, expect_warn, isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """餘裕 == margin 進 band、== margin+1 不進（None 代表用 margin/margin+1 兩點）。"""
    budget = 400
    if headroom is None:
        cases = [(clb.TIER_WARN_MARGIN, True), (clb.TIER_WARN_MARGIN + 1, False)]
    else:
        cases = [(headroom, expect_warn)]
    for hr, expect in cases:
        isolated([_report("autoclaude/infra/repositories/x.py", budget - hr, budget)])
        clb.check()
        out = capsys.readouterr().out
        assert ("[TIER-WARN]" in out) is expect, (
            f"餘裕 {hr} 行（margin={clb.TIER_WARN_MARGIN}）時 [TIER-WARN] 應"
            f"{'出現' if expect else '不出現'}；實際輸出：\n{out}"
        )


def test_over_budget_file_goes_to_blocking_tier_not_warn_band(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """已破預算的檔只能進 [TIER] 阻塞段，不得同時進預警帶（同一件事不印兩段）。"""
    isolated([_report("autoclaude/infra/repositories/x.py", 406, 400)])
    rc = clb.check()
    out = capsys.readouterr().out
    assert rc == 1
    assert "[TIER]" in out
    assert "[TIER-WARN]" not in out, (
        "破線檔同時出現在預警帶——同一件事印兩段，且會讓「預警」語意變成「已失敗」"
    )


# --- 不變量 3：標籤隔離（保護既有總量帶那道鎖）---

def test_tier_band_does_not_emit_the_total_band_tag(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    isolated([_report("autoclaude/infra/repositories/x.py", 400, 400)])
    clb.check()
    out = capsys.readouterr().out
    assert "[TIER-WARN]" in out
    assert "[WARN]" not in out, (
        "tier 預警帶吐出了 [WARN] —— 會讓 tests/contract/test_loc_budget_tiered.py::"
        "test_warn_band_boundary_and_rc_invariant 的 `(\"[WARN]\" in out) is "
        "expect_warn` 在 repo 現況（有滿載檔）下恆真，那道鎖等於被關掉"
    )


# --- 不變量 4：JSON ↔ 文字一致 ---

def test_json_payload_matches_text_mode(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    reports = [
        _report("autoclaude/infra/repositories/full.py", 400, 400),
        _report("autoclaude/models/roomy.py", 10, 150, tier="data"),
    ]
    isolated(reports)
    clb.check()
    text_out = capsys.readouterr().out
    clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["tier_warn_margin"] == clb.TIER_WARN_MARGIN
    assert bool(payload["tier_warn_band"]) is ("[TIER-WARN]" in text_out), (
        f"--json 的 tier_warn_band 與文字模式不一致；文字輸出：\n{text_out}"
    )
    entries = payload["tier_warn_band"]
    assert [e["rel_path"] for e in entries] == [
        "autoclaude/infra/repositories/full.py"
    ], f"餘裕充足的檔不該進 band：{entries}"
    assert entries[0]["headroom"] == 0, "JSON 必須帶 headroom（餘裕）供機讀判讀"


# --- 不變量 5：真 repo 錨點（DEF-101-526 的當事檔）---

def test_real_repo_full_tier_file_is_actually_caught() -> None:
    """DEF-101-526 的當事檔（滿載 400/400）必須真的被命中——合成資料不算驗收。"""
    reports = clb.build_reports(clb.load_overrides())
    band = {
        r.rel_path: r.budget - r.loc
        for r in reports
        if r.over_by == 0 and r.budget - r.loc <= clb.TIER_WARN_MARGIN
    }
    target = "autoclaude/infra/repositories/pg_state_repository.py"
    assert target in band, (
        f"DEF-101-526 的當事檔未被預警帶命中（band={band}）——交棒條目的驗收條件未達成"
    )
    assert band[target] == 0, (
        f"該檔應為滿載（餘裕 0），實測餘裕 {band[target]}；若 tier 或行數已變動，"
        f"請重新核對本鎖的錨點"
    )
