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
     （repo 現況存在合法滿載檔，改成 fail 會當場擋住 repo；**現值刻意不寫死在此**，
     現查＝`python tools/check_loc_budget.py --json` 的 `tier_warn_band`）。
  2. 邊界精確：餘裕 == TIER_WARN_MARGIN 進 band；== +1 不進；已破預算的檔不進
     band（由既有 [TIER] 阻塞段接手，避免同一件事印兩段）。
  3. 標籤隔離：tier band 用 `[TIER-WARN]`，**不得**吐出 `[WARN]` ——後者被
     tests/contract/test_loc_budget_tiered.py::test_warn_band_boundary_and_rc_invariant
     以 `("[WARN]" in out) is expect_warn` 釘為總量預警帶專屬訊號，共用標籤會讓那道鎖
     在 repo 現況下恆真而失效。
  4. JSON ↔ 文字一致（同 total band 先例：以 --json 取證的自動化才看得到本訊號）。
  5. 真 repo 錨點：band 必須在真 repo 資料上真的命中、且命中的餘裕落在
     [0, TIER_WARN_MARGIN] ——這是交棒條目的驗收條件本身，不能只用合成資料證明。
     （原文寫死 DEF-101-526 當事檔 `pg_state_repository.py` 為 400/400 滿載錨點；
     該檔於「刪死碼／收斂重複」輪降至 393/400 後合法離帶，錨點已改形，見該支測試）

鑑別力（**本輪逐項重量**，取代 R60 原註記——原註記宣稱「把 `TIER_WARN_MARGIN` 改成 0
→ 邊界**與真 repo 錨點**測試轉紅」，實測**真 repo 錨點測試不紅**，見下表第 2 列；
該句在錨點測試改形後即已失真，屬本檔自己犯下的「寫死宣稱不隨改形同步」）：

  (1) production band 篩選 `<=` 誤寫成 `<` ⇒ **2 failed / 7 passed**：
      `test_boundary_at_margin_and_one_beyond[None-None]` ＋
      `test_real_repo_band_is_exercised_on_real_data`。
  (2) `TIER_WARN_MARGIN` 注入為 0（runtime patch，不落地改檔）⇒ **2 failed / 7 passed**：
      `test_margin_constant_is_positive_and_documented` ＋
      `test_boundary_at_margin_and_one_beyond[1-True]`。
      🔴 **真 repo 錨點測試在此注入下不紅**——band 縮成「餘裕恰為 0」後仍非空
      （現況有滿載檔），且測試側期望值與 production 同步縮小，故此注入抓不到它。
      這正是 R60 原註記失真之處，記於此以免下一輪又照抄。
  (3) tier band 標籤改回 `[WARN]` ⇒ **6 failed / 3 passed**，含
      `test_tier_band_does_not_emit_the_total_band_tag`。

  三次注入還原後皆為 `9 passed`；`tools/check_loc_budget.py` 以 `git diff --exit-code`
  確認與 HEAD 逐位元組相同（注入僅為驗紅，未留在樹上）。
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

    刻意不改成 fail：repo 現況存在**合法**滿載／近滿載檔，改 fail 會當場把它們變成
    閘門紅。**具體是哪幾支、各自餘裕多少刻意不寫死在此**——那是會隨每次瘦身漂移的
    量測值（本檔原文寫死的三支已於「刪死碼／收斂重複」輪全數失真：
    `pg_state_repository.py` 已降至 393/400、`steps_orchestrator/_impl.py` 已降至
    494/500）。現查＝`python tools/check_loc_budget.py --json` 的 `tier_warn_band`。
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

def test_real_repo_band_is_exercised_on_real_data(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """預警帶必須在**真 repo 資料**上真的跑起來，且 production 吐出的成員逐筆正確。

    錨點沿革（本鎖原名 `test_real_repo_full_tier_file_is_actually_caught`）：
      DEF-101-526 的當事檔 `pg_state_repository.py` 原為 400/400，本鎖曾以
      `assert target in band and band[target] == 0` 寫死該檔名。ADR-SD07-001 §6.3
      順位一（刪死碼／收斂重複）把四個 state repository 逐字重複的 deprecation
      shim 收斂成共用函式之後，該檔降為 393/400（餘裕 7 > TIER_WARN_MARGIN），
      **合法**離開預警帶，本鎖因此轉紅。

      🔴 改形理由（而非只換一個檔名）：把「某支檔必須是滿載的」寫進斷言，等於讓
      每一次成功瘦身都把這道鎖打紅，把「減行成功」誤報成「鎖壞了」——那是會養成
      忽略紅燈習慣的反向誘因。真正該守的不變量是原註記那句「不能只用合成資料證明」：
      band 的計算必須跑在真 repo 上、真的命中東西、且命中的成員與 production 一致。
      滿載檔的**存在**不是本鎖的目的，是本 repo 當下的狀態。

      🔴 二次改形（本輪；前一版第二條斷言是**恆真的**）：改形後的第二條斷言寫成
      `all(0 <= h <= TIER_WARN_MARGIN for h in band.values())`，而 `band` 正是**本函式
      自己**用 `over_by == 0 and budget - loc <= TIER_WARN_MARGIN` 篩出來的——篩選條件
      直接蘊涵被斷言的區間（`over_by == 0` ⟺ `loc <= budget` ⟺ `h >= 0`，見
      `check_loc_budget.py:327` 的 `over_by=max(0, loc - budget)`），故它對**任何** repo
      狀態、**任何** TIER_WARN_MARGIN 值都不可能紅。等於「兩條真斷言」被換成「一條真
      ＋一條永遠通過」，而註記還宣稱它有鑑別力——比沒有鎖更糟。
      本版把比對對象換成 **production 實際吐出的 `--json` band**：測試側自 raw reports
      獨立算出期望成員，再與 production 的輸出做集合相等比對。production 的篩選語意
      一漂移（`<=` 誤寫成 `<`、漏排除破線檔、`headroom` 欄位算錯、排序去重寫壞）即紅。
    """
    reports = clb.build_reports(clb.load_overrides())
    # 測試側獨立推導期望成員（刻意不重用 production 的 band 物件——重用即恆真）。
    expected = {
        r.rel_path: r.budget - r.loc
        for r in reports
        if r.over_by == 0 and r.budget - r.loc <= clb.TIER_WARN_MARGIN
    }
    assert expected, (
        "真 repo 的 tier 預警帶為空 —— 本鎖退化為恆真（DEF-101-526 交棒條目要求以"
        "真實資料驗收）。若 repo 真的已無任何接近 tier 上限的檔，請連同 "
        "TIER_WARN_MARGIN 的存在意義一起重新評估，不要直接刪本鎖。"
    )
    clb.check(as_json=True)
    emitted = {
        e["rel_path"]: e["headroom"]
        for e in json.loads(capsys.readouterr().out)["tier_warn_band"]
    }
    assert emitted == expected, (
        "production 在**真 repo 資料**上吐出的 tier 預警帶與獨立推導的期望成員不符。\n"
        f"  production 吐出：{emitted}\n"
        f"  期望（over_by == 0 且餘裕 ≤ {clb.TIER_WARN_MARGIN}）：{expected}\n"
        "  只出現在 production 側 ⇒ 篩選條件放太寬（如漏排除已破線檔）；\n"
        "  只出現在期望側 ⇒ 篩選條件太緊（如 `<=` 誤寫成 `<`）；\n"
        "  成員相同但值不同 ⇒ `headroom` 欄位的算式漂移。"
    )
