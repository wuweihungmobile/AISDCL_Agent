"""tests/tools/test_check_loc_budget_hub_tier_and_special_stale.py — R84（W0）

兩個判準的回歸鎖，各自對應 R84 Phase 1 的一筆 finding：

A. **`guardrail_hub` tier（ARCH-04）** — `guardrail_lib=400` 把 `tools/lib/` 整層當成同一種
   東西，而 `quota_gate.py` 是把 5 支同層 lib 組起來的**合成面**（fan-out 5、對外 production
   消費者 1），實測 400/400 餘裕 0，於是「在它上面加任何一行」都被擋住。本鎖守的不是那
   +100 行，而是**它不能變成後門**：成員清單只准縮不准長、每一支成員必須被 AST 現查證明
   真的是 hub、預算不得發明新數字、pattern 不得用寬 glob。

   🔴 為什麼「成員數只准縮」是本鎖的核心：放寬單檔上限本身是可辯護的（分類錯誤），
   但「誰能進這個 tier」若沒有代價，下一個貼牆的檔就會把自己加進來 —— 那時放寬的
   不是一支檔而是整層。要加第二支，必須先改 `ROOT_TOOLS_HUB_MEMBER_CAP`，
   那一行 diff 就是可見痕跡。

B. **`SPECIAL_FILES` 棘輪的門檻過期側（ARCH-05）** — 那批門檻自陳「＝納管當下實際行數，
   只准往下改」，買到的是「再往裡塞就會紅」；R84 實測 `context_budget_guard.py`
   cap 1451 / raw 1089 ⇒ **362 行**可以無聲長回去，而該保證因此三輪不成立。
   既有的 `SPECIAL_WARN_MARGIN` 只量「快滿了」這一側，對「門檻自己過期」結構上失明。

   🔴 意圖（Rule 9）：本鎖要守的**不是**「今天那幾支各是多少行」（那是每輪都會漂移的
   量測值，寫進斷言等於每次合法瘦身都把鎖打紅），而是三件會讓判準靜默失效的事：
   ① 邊界寫成 `>=`／`>` 反了（剛好卡在門檻上的那一列會靜靜地不出現）；
   ② 判準被改成非阻塞（這一族**已經有**一個非阻塞訊號，而它多輪未被行動 —— 再加一個
      不會紅的訊號等於什麼都沒做）；
   ③ 射程被悄悄縮小（把某一列從 `_SPECIAL_REASONS` 拿掉即可逃出射程，而那個動作在
      任何其他鎖下都是綠的）。
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import check_loc_budget as clb  # noqa: E402


def _report(rel: str, loc: int, budget: int, tier: str = "special") -> clb.FileReport:
    return clb.FileReport(
        rel_path=rel, loc=loc, tier=tier, budget=budget,
        over_by=max(0, loc - budget), override_reason=None,
    )


# ════════════════════════════════════════════════════════════════════════════
# A. guardrail_hub tier（ARCH-04）
# ════════════════════════════════════════════════════════════════════════════

def _hub_spec() -> dict:
    spec = clb.ROOT_TOOLS_TIERS.get(clb.ROOT_TOOLS_HUB_TIER)
    assert spec is not None, (
        f"`ROOT_TOOLS_TIERS` 裡找不到 {clb.ROOT_TOOLS_HUB_TIER} —— 本鎖失去比較對象"
    )
    return spec


def _lib_dir() -> Path:
    return clb.ROOT_TOOLS_ROOT / "lib"


def _fanout(member_rel: str) -> tuple[int, list[str]]:
    """該成員 import 了幾支**同層** `tools/lib/*.py`（AST，不執行那支檔）。

    刻意用 AST 而不是字串搜尋：`tools/lib/` 的檔頭註解大量提到別支同層模組的名字，
    grep 版會把「註解裡講到」算成「真的相依」，那樣的 fan-out 數字沒有鑑別力。
    """
    lib = _lib_dir()
    siblings = {p.stem for p in lib.glob("*.py")}
    path = clb.ROOT_TOOLS_ROOT.parent / member_rel
    tree = ast.parse(path.read_text(encoding="utf-8"))
    deps: set[str] = set()
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module.split(".")[0]]
        deps.update(m for m in mods if m in siblings and m != path.stem)
    return len(deps), sorted(deps)


def test_hub_budget_reuses_an_existing_policy_number_and_is_not_the_red_line() -> None:
    """預算不得是發明出來的數字，也不得等於絕對紅線。

    WHY：發明一個新數字＝變相放寬（沒有人能說出它為什麼是那個值）；而等於
    `ABSOLUTE_LIMIT` 則讓本 tier 與 `guardrail_cli` 逐字同值 —— **一個等於絕對紅線的
    tier 不是 tier**，等於只剩絕對紅線在守，而那正是本 tier 想避免的形態。
    """
    budget = _hub_spec()["budget"]
    known = {spec["budget"] for spec in clb.LOC_TIERS.values()} | {clb.ABSOLUTE_LIMIT}
    assert budget in known, (
        f"guardrail_hub 的預算 {budget} 不在既有政策數字 {sorted(known)} 之內 ⇒ "
        "發明新數字＝變相放寬（ADR-SD07-001 的分級表才是那些數字的家）"
    )
    assert budget < clb.ABSOLUTE_LIMIT, (
        f"guardrail_hub 預算 {budget} == 絕對紅線 {clb.ABSOLUTE_LIMIT} ⇒ 本 tier 退化為"
        "「無上限」，與 guardrail_cli 無從區分"
    )
    assert budget > clb.ROOT_TOOLS_TIERS["guardrail_lib"]["budget"], (
        "guardrail_hub 不比 guardrail_lib 寬 ⇒ 這個 tier 不解決任何事，該刪掉而不是留著"
    )


def test_hub_patterns_are_enumerated_single_files_not_globs() -> None:
    """pattern 只准是明文單檔路徑。

    WHY：`tools/lib/*_gate.py` 這種寫法會讓下一支「剛好取這個名字」的檔自動繼承放寬，
    而沒有任何人做過那個決定 —— 那就是後門的形狀。
    """
    for pat in _hub_spec()["patterns"]:
        assert pat.endswith(".py"), f"{pat!r} 不是單檔路徑（目錄前綴會整層繼承放寬）"
        assert not any(ch in pat for ch in "*?["), f"{pat!r} 含 glob 字元 ⇒ 成員面不可枚舉"
        assert pat.startswith("tools/lib/"), f"{pat!r} 不在 tools/lib/ 內 ⇒ 射程被擴大"


def test_hub_membership_only_shrinks() -> None:
    """成員數上界（只准調小）＝這個 tier 的**代價**。

    WHY：見本檔檔頭 A 段。要加第二支就必須改 `ROOT_TOOLS_HUB_MEMBER_CAP`，
    讓「有人在放寬單檔上限」成為 diff 上一望即知的事。
    """
    members = _hub_spec()["patterns"]
    assert len(members) <= clb.ROOT_TOOLS_HUB_MEMBER_CAP, (
        f"guardrail_hub 成員數 {len(members)} > 上界 {clb.ROOT_TOOLS_HUB_MEMBER_CAP}"
    )
    assert clb.ROOT_TOOLS_HUB_MEMBER_CAP <= 1, (
        "成員數上界被調大 ⇒ 方向鎖失效（只准調小；要加成員請先走"
        "拆職責／抽共用模組，確認不可壓縮後具名調整並在缺陷帳本寫理由）"
    )
    assert members, "成員清單空了 ⇒ 這個 tier 沒有分母，該連同它的 WHY 一起重新談"


def test_every_hub_member_is_mechanically_proven_to_be_a_hub() -> None:
    """「是不是 hub」由 AST 現查 fan-out 決定，不是靠自稱。

    WHY：本 tier 的正當性完全建立在「合成面 ≠ leaf helper」這個事實上。若成員只需要
    「被寫進清單」就能拿到 +100 行，那個事實就從判準裡消失了，剩下的只是一張名單。
    """
    for pat in _hub_spec()["patterns"]:
        path = clb.ROOT_TOOLS_ROOT.parent / pat
        assert path.is_file(), f"{pat} 不存在於磁碟 ⇒ 成員清單 stale"
        n, deps = _fanout(pat)
        assert n >= clb.ROOT_TOOLS_HUB_MIN_FANOUT, (
            f"{pat} 的 fan-out 只有 {n}（{deps}）< 下界 "
            f"{clb.ROOT_TOOLS_HUB_MIN_FANOUT} ⇒ 它是 leaf 而不是合成面，"
            "不該待在 guardrail_hub。leaf 貼牆的正解是拆職責／抽共用模組"
        )
    assert clb.ROOT_TOOLS_HUB_MIN_FANOUT >= 3, (
        "fan-out 下界被調小 ⇒ leaf 族的上緣會被掃進 hub（R84 實測：leaf 族 fan-out 0~1、"
        "hub 族 4~5，門檻落在兩群之間的空隙上）"
    )


def test_hub_tier_actually_wins_the_ordering_and_carries_a_reason() -> None:
    """反 vacuity：production 真的把成員分到 hub（順序敏感），且逐支帶 override_reason。

    WHY：`ROOT_TOOLS_TIERS` 是**順序敏感**的（`_matches_pattern` 先中先贏）。hub 的單檔
    pattern 若排在 `tools/lib/` 之後，整格靜默失效 —— 而上面每一條斷言都還是綠的。
    """
    for pat in _hub_spec()["patterns"]:
        tier, budget = clb.classify_root_tools_file(pat)
        assert tier == clb.ROOT_TOOLS_HUB_TIER, (
            f"{pat} 被分到 {tier} 而不是 {clb.ROOT_TOOLS_HUB_TIER} ⇒ "
            "hub 的 pattern 排在目錄 pattern 之後（順序敏感），這一格等於不存在"
        )
        assert budget == _hub_spec()["budget"]
    reason = clb._ROOT_TOOLS_TIER_REASONS.get(clb.ROOT_TOOLS_HUB_TIER, "")
    assert reason, "hub tier 沒有 override_reason ⇒ 破線者拿不到「該怎麼做」"
    emitted = [r for r in clb.root_tools_reports() if r.tier == clb.ROOT_TOOLS_HUB_TIER]
    assert emitted, "真 repo 報表裡一支 hub 成員都沒有 ⇒ 本 tier 沒有被 production 走到"
    for r in emitted:
        assert r.override_reason == reason, f"{r.rel_path} 的理由沒有接上 hub 那一格"


# ════════════════════════════════════════════════════════════════════════════
# B. SPECIAL_FILES 門檻過期側（ARCH-05）
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def isolated(monkeypatch: pytest.MonkeyPatch):
    """把 `check()` 的其餘取數面全部隔離，只留 special 這一層是受測對象。"""
    monkeypatch.setattr(clb, "load_overrides", lambda: {})
    monkeypatch.setattr(clb, "build_reports", lambda _ov: [])
    monkeypatch.setattr(clb, "check_special_files", lambda: [])
    monkeypatch.setattr(clb, "root_tools_reports", lambda: [])
    monkeypatch.setattr(clb, "read_baseline", lambda: 10_000_000)
    monkeypatch.setattr(
        clb, "write_baseline",
        lambda _v: pytest.fail("check() 不應在 baseline 已存在時寫檔"),
    )

    def _use(reports: list[clb.FileReport]) -> None:
        monkeypatch.setattr(clb, "special_file_reports", lambda: list(reports))

    return _use


#: 射程內的一個真實鍵（取 `_SPECIAL_REASONS` 的任一筆，不寫死檔名 —— 那張表會變）。
def _in_scope_key() -> str:
    keys = sorted(clb._SPECIAL_REASONS)
    assert keys, "`_SPECIAL_REASONS` 空了 ⇒ 本判準的射程為空，整段退化為恆綠"
    return keys[0]


@pytest.mark.parametrize(
    "slack,expect_stale",
    [
        (0, False),                              # 零餘裕＝本棘輪的正常態
        (clb.SPECIAL_STALE_SLACK, False),        # 恰在門檻上：容忍（`>` 而不是 `>=`）
        (clb.SPECIAL_STALE_SLACK + 1, True),     # 超過一行即咬
    ],
)
def test_stale_boundary_is_exact_and_blocking(
    slack, expect_stale, isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """邊界精確（== 門檻不咬、+1 咬），且咬的時候必須是 **rc=1**。

    WHY：這一族已經有一個非阻塞預警帶，而 R84 立案的事實正是「有訊號但沒人動作」
    （那 362 行陳舊餘裕每次 `--json` 都印得出來卻沒有任何東西會紅）。若本判準也是
    非阻塞，它落地當天就已經失效，而且失效與成功長得一模一樣。
    """
    key = _in_scope_key()
    cap = 1000
    isolated([_report(key, cap - slack, cap)])
    rc = clb.check()
    out = capsys.readouterr().out
    assert ("[SPECIAL-STALE]" in out) is expect_stale, (
        f"陳舊餘裕 {slack} 行（門檻 {clb.SPECIAL_STALE_SLACK}）時 [SPECIAL-STALE] 應"
        f"{'出現' if expect_stale else '不出現'}；實際輸出：\n{out}"
    )
    assert rc == (1 if expect_stale else 0), (
        f"陳舊餘裕 {slack} 行時 rc 應為 {1 if expect_stale else 0}，實得 {rc}\n{out}"
    )


def test_over_line_entries_do_not_also_count_as_stale(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """已破線的列只走破線段，不得同時被算成「門檻過期」。

    WHY：破線＝現值 > 門檻，陳舊餘裕是負的；若篩選漏了 `over_by == 0`，同一件事會印
    兩段互相矛盾的話（「太胖了」＋「門檻太鬆」），讀者無從判斷該往哪個方向動。
    """
    key = _in_scope_key()
    isolated([_report(key, 1200, 1000)])
    clb.check()
    out = capsys.readouterr().out
    assert "[SPECIAL-STALE]" not in out, f"破線列被算成門檻過期\n{out}"


def test_policy_budget_rows_are_out_of_scope_by_provenance(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """沒有棘輪 provenance 的列（＝政策預算）不在射程內，且那是刻意的。

    WHY：`CLAUDE.md`（ADR-SD08-001 ≤400）與兩支長文件預算（SD_09 Pre-W0 audit P0-06）
    的語意是「這份文件最多可以長到 N 行」—— 留餘裕正是它們的設計，`sprint_history.md`
    更是設計上就要被 append 的滾動窗口文件。把它們重釘成現值會與 ADR-SD08-001 直接
    對撞，且下一次 sprint 收錄就必紅：那不是治本，是把一道對的閘門改成錯的。
    """
    outsiders = [k for k in clb.SPECIAL_FILES if k not in clb._SPECIAL_REASONS]
    assert outsiders, "已無政策預算列 ⇒ 本鎖的分母消失，該連同這段 WHY 一起重新談"
    assert len(outsiders) <= 3, (
        f"射程外的列變多了（{outsiders}）⇒ 「不寫 provenance 就能逃出射程」這條路"
        "被走了；新加的棘輪列必須照體例登記 `_SPECIAL_REASONS`"
    )
    isolated([_report(outsiders[0], 10, 5000)])   # 陳舊餘裕 4990，遠超門檻
    rc = clb.check()
    out = capsys.readouterr().out
    assert "[SPECIAL-STALE]" not in out and rc == 0, (
        f"政策預算列被本判準咬到 ⇒ 射程判準（provenance）失效\n{out}"
    )


def test_stale_scope_is_derived_from_the_reason_table_not_a_second_list(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """射程必須真的讀 `_SPECIAL_REASONS`：清空它，判準就該整段失聲。

    WHY（行為版而非讀原始碼比對字面）：若射程另抄一份清單，它就不會跟著這個
    monkeypatch 一起消失 ⇒ 本鎖轉紅。「同一份知識只有一個家」在這裡的具體代價是：
    有人把某一列從理由表移走（合理的重構動作）時，那一列會靜默逃出射程。
    """
    key = _in_scope_key()
    stale = [_report(key, 100, 1000)]
    isolated(stale)
    assert clb.check() == 1
    assert "[SPECIAL-STALE]" in capsys.readouterr().out, "控制組沒紅 ⇒ 注入基底失效"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(clb, "_SPECIAL_REASONS", {})
        isolated(stale)
        rc = clb.check()
        out = capsys.readouterr().out
    assert rc == 0 and "[SPECIAL-STALE]" not in out, (
        f"射程沒有走 `_SPECIAL_REASONS` ⇒ 判準有第二個家\n{out}"
    )


def test_slack_constant_direction_is_locked() -> None:
    """`SPECIAL_STALE_SLACK` 只准調小，且必須大於上界那個預警門檻。

    WHY：調大＝把「預先發放的成長額度」再發回去（本判準的立案理由）。下界那條同樣是
    硬需求：`tools/tests/test_check_defect_log_crossref.py::
    TestActionableMessagesHaveLocHeadroom` 要求「訊息教人加一筆的那些檔」餘裕 ≥ 5，
    本門檻若 ≤ 5，兩道鎖對同一支檔的要求會**無法同時滿足**（一邊要 ≥5、一邊要 ≤K）。
    """
    assert isinstance(clb.SPECIAL_STALE_SLACK, int)
    assert clb.SPECIAL_STALE_SLACK <= 32, "門檻被調大 ⇒ 方向鎖失效（只准調小）"
    assert clb.SPECIAL_STALE_SLACK > clb.SPECIAL_WARN_MARGIN, (
        f"門檻 {clb.SPECIAL_STALE_SLACK} ≤ 預警門檻 {clb.SPECIAL_WARN_MARGIN} ⇒ "
        "「快滿了」與「太鬆了」兩帶相鄰／重疊，每一列永遠落在其中一帶＝常駐全亮"
    )


def test_stale_payload_is_machine_readable_and_matches_text_mode(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON ↔ 文字一致，且帶 `headroom`（陳舊了幾行才是唯一可行動的資訊）。"""
    key = _in_scope_key()
    reports = [_report(key, 900, 1000)]
    isolated(reports)
    clb.check()
    text_out = capsys.readouterr().out
    isolated(reports)
    clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["special_stale_slack"] == clb.SPECIAL_STALE_SLACK
    assert bool(payload["special_stale"]) is ("[SPECIAL-STALE]" in text_out)
    assert [(e["rel_path"], e["headroom"]) for e in payload["special_stale"]] == [
        (key, 100)
    ], f"special_stale 成員／陳舊餘裕不符：{payload['special_stale']}"


def test_the_message_blocks_the_wrong_exit(
    isolated, capsys: pytest.CaptureFixture[str]
) -> None:
    """訊息必須明說「重釘為現值」，並擋住「把門檻調大讓紅字消失」這個出口。

    WHY（Rule 9）：看到紅字最省事的做法就是改大常數，而本 repo 明文把那叫「砸溫度計」。
    訊息若只說「門檻過期了」而不說該往哪個方向動，它把人推向的正是那個錯誤出口。
    """
    isolated([_report(_in_scope_key(), 100, 1000)])
    clb.check()
    out = capsys.readouterr().out
    assert "重釘為現值" in out, "訊息沒有給出修法"
    assert "不得改大 SPECIAL_STALE_SLACK" in out, "訊息沒有擋住「調大門檻」這個出口"


def test_real_repo_ratchet_pins_are_all_fresh(capsys: pytest.CaptureFixture[str]) -> None:
    """真 repo 錨點：所有帶 provenance 的棘輪列現在都必須是**新鮮**的。

    刻意不寫死「哪一支多少行」（那是每輪都漂移的量測值，寫進斷言等於每次合法瘦身都把
    本鎖打紅）。守的是那批門檻與現值之間的距離有人在量 —— 這一支紅了就代表有列縮了
    卻沒重釘，修法是把該列重釘為現值，不是動本鎖。
    """
    clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)
    stale = [(e["rel_path"], e["budget"], e["loc"], e["headroom"])
             for e in payload["special_stale"]]
    assert stale == [], (
        "有棘輪列的門檻已高於現值（陳舊餘裕 > "
        f"{clb.SPECIAL_STALE_SLACK}）：{stale}\n"
        "修法＝把每一支的門檻重釘為現值（一行 diff）。"
    )
    in_scope = [k for k in clb.SPECIAL_FILES if k in clb._SPECIAL_REASONS]
    assert len(in_scope) >= 2, (
        f"射程內只有 {in_scope} ⇒ 上面那條斷言的分母幾乎為空，等於恆綠"
    )
