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
      `test_real_repo_bands_match_production_output`（M5 記帳分離後之名；R60 原名
      `test_real_repo_band_is_exercised_on_real_data`）。
  (2) `TIER_WARN_MARGIN` 注入為 0（runtime patch，不落地改檔）⇒ **2 failed / 7 passed**：
      `test_margin_constant_is_positive_and_documented` ＋
      `test_boundary_at_margin_and_one_beyond[1-True]`。
      🔴 **真 repo 一致性測試在此注入下不紅**——band 縮成「餘裕恰為 0」後仍非空
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

def _real_layers() -> dict[str, tuple[list[clb.FileReport], int]]:
    """三層預警帶的 `(真 repo 報表, 該層 margin)`——取數面唯一的家。"""
    return {
        "tier_warn_band": (clb.build_reports(clb.load_overrides()), clb.TIER_WARN_MARGIN),
        "special_warn_band": (clb.special_file_reports(), clb.SPECIAL_WARN_MARGIN),
        "root_tools_warn_band": (clb.root_tools_reports(), clb.TIER_WARN_MARGIN),
    }


def _expected_bands() -> dict[str, dict[str, int]]:
    """測試側**獨立推導**的逐層期望成員（刻意不重用 production 的 band 物件——重用即恆真）。"""
    return {
        field: {r.rel_path: r.budget - r.loc for r in reports
                if r.over_by == 0 and r.budget - r.loc <= margin}
        for field, (reports, margin) in _real_layers().items()
    }


def test_real_repo_bands_match_production_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """真 repo 資料上，production 逐層吐出的預警帶 == 測試側獨立推導的期望成員。

    🔴 **本鎖只驗「一致」，不驗「篩選語意」**（ADR-XPLAT-013 否決權複審 M5 的記帳分離）。
    沿革與這一刀為什麼要切：
      DEF-101-526 的當事檔 `pg_state_repository.py` 原為 400/400，本鎖曾以
      `assert target in band` 寫死該檔名；該檔合法瘦身後鎖轉紅 ⇒ 一次改形改成
      「band 必須在真 repo 上真的命中東西」。二次改形訂正了一條**恆真**斷言
      （`all(0 <= h <= MARGIN ...)` 被自己的篩選條件蘊涵）。三次改形（ADR-XPLAT-013）
      把「非空」的分母由單層上移到三層聯集。
      🔴 四次改形（本次）＝**記帳分離**：三次改形之後，「非空」這個前提從此**永遠**由
      `special_warn_band` 滿足（它走 raw-line 軸，結構上不受計價改動影響，實測仍有 6 支），
      而 `tier_warn_band` 與 `root_tools_warn_band` 皆已空 ⇒ 那兩層的「成員比對」退化成
      **空集合互比**。一支拿空集合互比、卻掛在「真實資料驗收」名下的測試，會讓人誤以為
      篩選語意在真資料上被驗過。分離後的權責：
        · **篩選語意**（`<=` vs `<`、破線檔要排除、`headroom` 算式、排序去重）一律由本檔的
          **合成資料**鎖負責，見 `_SEMANTIC_OWNERS`——那些鎖對空層照樣有牙。
        · **本鎖**只回答一個問題：production 與獨立推導在**當下的真實資料**上是否一致。
          因此它**刻意允許任一層為空**（空集合相等是合法通過），不再兼職「母體非空」。
        · 「整套機制是不是已經沒有任何母體」由 `test_the_warn_band_machinery_has_a_live_population`
          單獨記帳。
    """
    expected = _expected_bands()
    clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)
    census = {k: len(v) for k, v in expected.items()}
    for field, want in expected.items():
        emitted = {e["rel_path"]: e["headroom"] for e in payload[field]}
        assert emitted == want, (
            f"production 在**真 repo 資料**上吐出的 `{field}` 與獨立推導的期望成員不符。\n"
            f"  production 吐出：{emitted}\n"
            f"  期望（over_by == 0 且餘裕 ≤ 該層 margin）：{want}\n"
            f"  逐層母體筆數：{census}\n"
            "  只出現在 production 側 ⇒ 篩選條件放太寬（如漏排除已破線檔）；\n"
            "  只出現在期望側 ⇒ 篩選條件太緊（如 `<=` 誤寫成 `<`）；\n"
            "  成員相同但值不同 ⇒ `headroom` 欄位的算式漂移。"
        )


#: M5 記帳分離的另一半：篩選語意的**合成資料**擁有者。真資料鎖把語意委派給它們，
#: 而「委派對象還在不在」必須是機械可查的——否則那句委派就是散文，合成鎖被順手刪掉
#: 之後，真資料鎖仍會綠著並繼續自稱「已驗收」。
_SEMANTIC_OWNERS: tuple[str, ...] = (
    "test_boundary_at_margin_and_one_beyond",              # tier 層邊界（margin / margin+1）
    "test_over_budget_file_goes_to_blocking_tier_not_warn_band",  # 破線檔要排除
    "test_new_warn_bands_are_non_blocking_and_boundary_exact",    # special／root_tools 兩層邊界
    "test_new_bands_are_machine_readable_and_match_text_mode",    # headroom 欄位算式
    "test_all_three_bands_share_one_selection_implementation",    # 三層共用同一份篩選
)


def test_the_warn_band_machinery_has_a_live_population() -> None:
    """三層預警帶在真 repo 上**同時**為空 ⇒ 這套機制已經沒有任何母體，該紅。

    意圖（Rule 9）：單一層空掉是合法的——一次成功的瘦身或一次計價規則變更就會發生
    （ADR-XPLAT-013 當輪 `tier_warn_band` 與 `root_tools_warn_band` 同時合法地空了）。
    三層全空是另一件事：那代表三個 `*_WARN_MARGIN` 常數已經沒有任何檔會落進來，
    「第一個訊號就是紅」這個設計目標從此不可能達成，而它會靜靜地不出現。

    本鎖同時把「逐層母體」印進失敗訊息——記帳分離之後，哪一層在承重必須是**看得見**的，
    不能再被聯集蓋掉（那正是四次改形要修的東西）。
    """
    census = {k: len(v) for k, v in _expected_bands().items()}
    assert any(census.values()), (
        "三層預警帶在真 repo 上同時為空 —— 這套機制已無母體（DEF-101-526 交棒條目要求以"
        "真實資料驗收）。請連同三個 margin 常數的存在意義一起重新評估，不要直接刪本鎖。"
        f"\n  逐層母體筆數：{census}"
    )


def test_the_semantic_owners_delegated_to_by_the_real_data_lock_still_exist() -> None:
    """🔴 記帳分離的封閉性：真資料鎖委派出去的合成鎖，必須真的還在本模組裡。

    意圖（Rule 9）：`test_real_repo_bands_match_production_output` 的 docstring 明文把
    「篩選語意」委派給合成資料鎖，並據此**放棄**了「母體非空」這個要求。那句委派若只是
    散文，合成鎖被順手刪掉（或改名）之後，真資料鎖會繼續綠著、繼續自稱已驗收，而
    `<=` 誤寫成 `<`、破線檔沒排除這類漂移將**完全無人守**——退化方向與二次改形治的
    「恆真斷言」同型。本鎖讓那個刪除變成會轉紅的事件。
    """
    module = sys.modules[__name__]
    missing = [name for name in _SEMANTIC_OWNERS if not callable(getattr(module, name, None))]
    assert not missing, (
        f"真資料鎖委派的合成語意鎖已消失：{missing}。"
        "要嘛把它們找回來／改名同步進 `_SEMANTIC_OWNERS`，"
        "要嘛把 `test_real_repo_bands_match_production_output` 的委派說明一起改掉"
        "——不能只刪鎖不改那句話。"
    )


# --- R76（R76-16）：另外兩層預警帶（SPECIAL_FILES raw-line 棘輪／根層 tools tier）---
#
# 🔴 為何非補不可：這兩層是 R76 新增的，而它們的鎖檔（本檔）當時不在該包的授權面 ⇒
# 落地當下「整段 [SPECIAL-WARN]／[ROOT-TOOLS-WARN] 與兩個 JSON 欄位刪掉不會有任何東西
# 轉紅」（該包自陳缺口 DEF-101-856①）。沒有回歸鎖的預警帶，會在下一次有人「順手清理
# 輸出」時無聲消失，而它防的正是「第一個訊號就是紅」——消失了也沒人會發現。


@pytest.fixture
def isolated_layers(monkeypatch: pytest.MonkeyPatch):
    """把 SPECIAL_FILES 與根層 tools 兩層的**資料來源**換成合成報表。

    與 `isolated` 互補：那個 fixture 只隔離 tier 層（`build_reports`）與
    `check_special_files`（違規側），本 fixture 隔離的是 R76 新增的預警帶取數面
    （`special_file_reports` / `root_tools_reports`）——兩者是不同函式，漏了任一個，
    測試就會混進真 repo 現況而不再是確定性判準。
    """
    def _use(
        special: list[clb.FileReport] | None = None,
        root_tools: list[clb.FileReport] | None = None,
    ) -> None:
        monkeypatch.setattr(clb, "special_file_reports", lambda: list(special or []))
        monkeypatch.setattr(clb, "root_tools_reports", lambda: list(root_tools or []))

    return _use


@pytest.mark.parametrize(
    "tag,margin_name,tier,budget",
    [
        ("[SPECIAL-WARN]", "SPECIAL_WARN_MARGIN", "special", 1618),
        ("[ROOT-TOOLS-WARN]", "TIER_WARN_MARGIN", "guardrail_cli", 750),
    ],
)
def test_new_warn_bands_are_non_blocking_and_boundary_exact(
    tag, margin_name, tier, budget, isolated, isolated_layers,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """兩層各自：餘裕 == margin 進帶、== margin+1 不進、已破線不進帶，且 rc 恆 0。

    意圖（Rule 9）：預警帶一旦變成阻塞，repo 當場被自己的合法現況擋死（這批棘輪
    依 R69 P3 慣例＝納管當下實際行數，零餘裕本來就是合法狀態）；而邊界若寫成 `<`，
    「剛好卡在門檻上」的檔——也就是最需要被警告的那一支——會靜靜地不出現。
    """
    margin = getattr(clb, margin_name)
    is_special = tag == "[SPECIAL-WARN]"
    for headroom, expect in ((margin, True), (margin + 1, False), (-3, False)):
        rep = _report("x/y.py", budget - headroom, budget, tier=tier)
        isolated([])
        isolated_layers(
            special=[rep] if is_special else [],
            root_tools=[] if is_special else [rep],
        )
        rc = clb.check()
        out = capsys.readouterr().out
        if headroom >= 0:
            # 只有「尚未破線」這一側該保證 rc 不變 —— 破線側本來就該由各自的阻塞段
            # 接手（根層 tools 破線＝rc 1）。把 rc==0 一律要求下去，等於順手把阻塞段
            # 也一起斷言掉，那是另一件事，而且方向是把閘門變鬆。
            assert rc == 0, f"{tag} 必須非阻塞（餘裕 {headroom}），實得 rc={rc}\n{out}"
        assert (tag in out) is expect, (
            f"餘裕 {headroom} 行（margin={margin}）時 {tag} 應"
            f"{'出現' if expect else '不出現'}；實際輸出：\n{out}"
        )


def test_special_warn_margin_is_positive_and_separate_from_tier_margin() -> None:
    """`SPECIAL_WARN_MARGIN` 必須存在且為正；≤0 等於把整個預警帶關掉。

    刻意也不斷言它「等於」或「不等於」`TIER_WARN_MARGIN`：兩者度量面不同
    （raw line vs `count_loc`），未來調成同值不是缺陷；要守的是**它是一個獨立的、
    可被單獨調整的門檻**，而不是被誤讀成 tier 那個數字的別名。
    """
    assert isinstance(clb.SPECIAL_WARN_MARGIN, int)
    assert clb.SPECIAL_WARN_MARGIN > 0, "SPECIAL_WARN_MARGIN ≤ 0 等於關掉 R76-16 的預警帶"


def test_new_bands_are_machine_readable_and_match_text_mode(
    isolated, isolated_layers, capsys: pytest.CaptureFixture[str],
) -> None:
    """JSON ↔ 文字一致：只印文字的話，以 `--json` 取證的自動化看不到這兩層訊號。

    同時釘住 `headroom` 欄位——沒有它，機讀端只知道「有東西快滿了」卻不知道「剩幾行」，
    而「剩幾行」正是這個訊號唯一可行動的部分。
    """
    special = [_report("../tools/a.py", 1616, 1618, tier="special")]
    root_tools = [_report("tools/b.py", 748, 750, tier="guardrail_cli")]
    isolated([])
    isolated_layers(special=special, root_tools=root_tools)
    clb.check()
    text_out = capsys.readouterr().out

    isolated([])
    isolated_layers(special=special, root_tools=root_tools)
    clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["special_warn_margin"] == clb.SPECIAL_WARN_MARGIN
    assert bool(payload["special_warn_band"]) is ("[SPECIAL-WARN]" in text_out)
    assert bool(payload["root_tools_warn_band"]) is ("[ROOT-TOOLS-WARN]" in text_out)
    assert [(e["rel_path"], e["headroom"]) for e in payload["special_warn_band"]] == [
        ("../tools/a.py", 2)
    ], "special 預警帶成員／餘裕不符"
    assert [(e["rel_path"], e["headroom"]) for e in payload["root_tools_warn_band"]] == [
        ("tools/b.py", 2)
    ], "根層 tools 預警帶成員／餘裕不符"


def test_special_warn_text_tells_people_not_to_raise_the_ratchet(
    isolated, isolated_layers, capsys: pytest.CaptureFixture[str],
) -> None:
    """訊息必須明說「不得調高棘輪」並給出正解順序。

    意圖（Rule 9）：這批門檻是 shrink-only 棘輪，而看到紅字最省事的做法就是把數字改大
    ——本 repo 已明文禁止（砸溫度計）。預警帶若只說「快滿了」而不說「不准調高、該怎麼做」，
    它把人推向的正是那個錯誤出口。
    """
    isolated([])
    isolated_layers(special=[_report("../tools/a.py", 1618, 1618, tier="special")])
    clb.check()
    out = capsys.readouterr().out
    assert "[SPECIAL-WARN]" in out
    assert "不得為了讓修改通過而調高" in out, "預警訊息沒有擋住「調高棘輪」這個錯誤出口"
    assert "抽共用模組" in out, "預警訊息沒有給出正解順序（先刪死碼／抽共用模組）"


def test_all_three_bands_share_one_selection_implementation(
    isolated, isolated_layers, capsys: pytest.CaptureFixture[str],
) -> None:
    """三層預警帶必須走同一個 `warn_band()`：把它換掉，三層應**同時**失聲。

    這是「同一份知識只有一個家」的行為版斷言（不是讀原始碼比對字面）：若哪一層自己
    另抄一份篩選條件，它就不會跟著這個 monkeypatch 一起消失 ⇒ 本鎖轉紅。
    """
    tier_rep = _report("autoclaude/infra/repositories/x.py", 400, 400)
    special_rep = _report("../tools/a.py", 1618, 1618, tier="special")
    root_rep = _report("tools/b.py", 750, 750, tier="guardrail_cli")

    isolated([tier_rep])
    isolated_layers(special=[special_rep], root_tools=[root_rep])
    clb.check()
    before = capsys.readouterr().out
    for tag in ("[TIER-WARN]", "[SPECIAL-WARN]", "[ROOT-TOOLS-WARN]"):
        assert tag in before, f"控制組未命中 {tag} —— 本鎖的注入基底已失效\n{before}"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(clb, "warn_band", lambda _reports, _margin: [])
        isolated([tier_rep])
        isolated_layers(special=[special_rep], root_tools=[root_rep])
        clb.check()
        after = capsys.readouterr().out
    for tag in ("[TIER-WARN]", "[SPECIAL-WARN]", "[ROOT-TOOLS-WARN]"):
        assert tag not in after, (
            f"{tag} 沒有走共用的 warn_band() —— 那一層自己抄了第二份篩選條件，"
            f"判準從此有兩個家（改一邊不會改到另一邊）\n{after}"
        )
