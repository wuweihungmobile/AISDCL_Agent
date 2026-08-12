#!/usr/bin/env python3
"""`.claude/hooks/context_budget_guard.py` ＋ `tools/session_resume_planner.py` 的回歸鎖。

WHY 這支鎖必須有鑑別力（而不只是「有測試」）
--------------------------------------------
本 repo 最大宗的缺陷形態是**鎖存在但沒有鑑別力**（R77 重跑分群：約四成，遠高於
「選錯載具」那一桶）。所以本檔每一條都成對寫：一個控制組（現況應為某值）＋一個
注入組（把被守的性質弄壞 ⇒ 必須紅）。只斷言「現況是對的」會在判準被改壞時照樣綠。

被守的四類性質
--------------
1. **算式**：當前佔用＝`input + cache_creation + cache_read`，`output_tokens`
   **不計**（它是這一則吐出來的量，下一回合才以 input 形式回到 context，重複計會高估）。
2. **window 判定的誠實性**：指定值／推斷值必須分得開，且推斷的保守方向不得被翻過來。
   猜小只是早喊（成本＝一次多餘的 compact），猜大則到 90% 時真實水位已 450%＝根本
   喊不到。方向錯的代價不對稱，所以它是被鎖的性質而不是實作細節。
3. **exit code 契約**：<75 靜默 0／≥75 出聲 0／≥90 出聲 2；退化輸入一律 0（fail-open，
   `.claude/settings.json` 記載過的 P0：hook 誤觸會把所有工具硬鎖死）。
4. **去重**：同一門檻同一 session 只喊一次。少了它，≥90% 之後每次工具呼叫都 exit 2，
   而被關掉的守衛比沒有守衛更糟。

🔴 為何新增一支檔案而不是併進既有鎖檔（照實寫）
------------------------------------------------
`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 是逐檔行數棘輪，
**任何**淨行數上升都會紅（不論新檔或擴充既有檔），合法出口只有「同一次變更刪等量的
行」或「重釘基準並在交件回報寫出淨額」。本包不刪別人的行，故走後者；而該棘輪自己
的紀律是「重釘一律由收尾包在所有包停工後做一次」⇒ **重釘不在本包射程內**，交由收尾者。
本檔因此可能讓該棘輪暫時紅，這是已知且已回報的狀態，不是漏看。
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "context_budget_guard.py"
_PLANNER = _REPO_ROOT / "tools" / "session_resume_planner.py"
_QUOTA_GATE = _REPO_ROOT / "tools" / "lib" / "quota_gate.py"

sys.path.insert(0, str(_HOOK.parent))
import context_budget_guard as guard  # noqa: E402

# R82／Q2-02：額度水位那把尺整條搬進 `tools/lib/quota_gate.py`（見該檔檔頭）。本檔
# 對它的引用刻意用**裸名 import**——`from lib import quota_gate` 會讓同一份原始碼在
# 同一行程裡有兩個模組物件，於是 monkeypatch 打在其中一個上、受測碼讀的是另一個
# （`ModuleIdentityIsSingleTest` 在守這一條）。
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import quota_criteria  # noqa: E402  # R86：判準本體的家（本檔只做斷言）
import quota_gate as qg  # noqa: E402
import quota_meter  # noqa: E402  # R82／HELM-02：`NO_WINDOW` 相等鎖的另一端
import quota_policy  # noqa: E402  # R82：門檻／階梯的唯一的家，本檔不再持有任何數字
import schedule_backend as sb  # noqa: E402  # R83：取證指引的家（見 halt 訊息接線鎖）
import sentinel_lifecycle  # noqa: E402  # R82／HELM-02：哨兵生命週期判準


def setUpModule() -> None:  # noqa: N802 — unittest 的固定名稱
    """🔴 R84／C3-P4c：整個測試模組**一律不准碰真的排程器**（in-process 那一半）。

    立案是實測到的：本機 `launchctl list` 長期掛著一支 `AutoSDD_Sentinel_s`，每 15 分鐘
    醒來一次；Windows 上那就是掌舵者看到的黑框。逐步歸因（在 `LaunchdBackend.arm` 插探針
    實跑本模組）指到 `QuotaGateIsWiredToTheBurnPathTest
    ::test_the_halt_side_effects_run_exactly_once_per_reset_window`——它以**同行程**呼叫
    `_gate()`，走真的 `quota_halt_actions` → `guard.arm_quota_wakeup` → `spawn_sentinel`，
    於是在開發者自己的機器上註冊了一支 launchd job，session 結束後永遠沒有人來收。
    探針逐字：`TMPDIR` 是真的那個、`AUTOSDD_SENTINEL_OFF` 為 `None`。

    🔴 為什麼 `_isolated_env` 治不了它：那支 helper 造的是**子行程**的環境，而這一條走的是
    同行程呼叫 ⇒ 兩者結構上不相交。子行程那一半由 `_isolated_env(real_scheduler=False)`
    負責（預設值），本函式負責同行程那一半；兩層合起來才是「本模組不留移動零件」。
    沿用既有逃生口而不新開測試專用旗標：它已經是「不要武裝」的唯一真相源。

    🔴 R84／SA84-01 訂正 pin 的**生命週期歸屬**：第一版把還原動作交給
    `unittest.addModuleCleanup`，而那個堆疊是**載具**的，不是本模組的——本檔自己有一支
    測試（見 `_run_nested_suite` 的 WHY）會起巢狀 runner 跑同模組的測試，那個 suite 收尾
    時觸發 module fixture teardown ⇒ `doModuleCleanups()` 把還原動作**提前 flush**，pin
    當場消失。後果不是「一支測試紅」，而是**在那之後本模組就沒有這道保護了**。
    ⇒ 捕捉原值只做一次（`_SENTINEL_PIN_CAPTURED`）：巢狀 runner 會再叫一次本函式，
    那時 pin 已經是 `"1"`，再捕捉一次就會把 `"1"` 記成「原值」而永久留在行程環境裡。
    """
    global _SENTINEL_PIN_ORIGINAL, _SENTINEL_PIN_CAPTURED
    if not _SENTINEL_PIN_CAPTURED:
        _SENTINEL_PIN_ORIGINAL = os.environ.get(guard.SENTINEL_OFF_ENV)
        _SENTINEL_PIN_CAPTURED = True
    _pin_sentinel_off()
    unittest.addModuleCleanup(_unpin_sentinel_off)


#: `setUpModule` 進來之前 `AUTOSDD_SENTINEL_OFF` 的值（只捕捉一次，理由見該函式）。
_SENTINEL_PIN_ORIGINAL: str | None = None
_SENTINEL_PIN_CAPTURED = False


def _pin_sentinel_off() -> None:
    """釘上「本行程一律不准武裝真排程器」。冪等 ⇒ 補釘幾次都不會改變語意。"""
    os.environ[guard.SENTINEL_OFF_ENV] = "1"


def _unpin_sentinel_off() -> None:
    """還原成 `setUpModule` 進來前的值。**冪等**：被 flush 兩次也不會留下錯的值。

    冪等是必要條件不是客氣——`_run_nested_suite` 會在巢狀 runner 沖掉堆疊之後把本函式
    重新掛回去，於是它有可能被登記兩次；讀 `_SENTINEL_PIN_ORIGINAL`（而不是閉包裡的
    某個當下值）讓第二次執行與第一次結果完全相同。
    """
    os.environ.pop(guard.SENTINEL_OFF_ENV, None)
    if _SENTINEL_PIN_ORIGINAL is not None:
        os.environ[guard.SENTINEL_OFF_ENV] = _SENTINEL_PIN_ORIGINAL


def _run_nested_suite(suite: unittest.TestSuite) -> unittest.TestResult:
    """跑一個**本模組自己的**巢狀 suite，收尾把 pin 補回去。唯一准起巢狀 runner 的地方。

    🔴 立案（R84／SA84-01，複審實測）：`pytest tools/tests/test_context_budget_guard.py`
    rc=1、唯一失敗者是 `SentinelArmingCriterionTest
    ::test_this_module_never_reaches_the_real_scheduler`（`AssertionError: None != '1'`），
    而 `python -m unittest tools.tests.test_context_budget_guard` 對同一份原始碼 rc=0。
    兩者差別**只有執行順序**：unittest 依類別名字母序（`S` 早於 `T`）、pytest 依定義順序
    （巢狀 runner 那一支在前）。機制：巢狀 suite 收尾會走 `_handleModuleTearDown` →
    `unittest.case.doModuleCleanups()`，把 `setUpModule` 註冊的還原動作提前執行掉。
    最小重現（本輪實跑，逐字）：同模組三個類別、中間那個起巢狀 runner ⇒
    `PIN-AFTER-NESTED: None`、`PIN-IN-LATER-CLASS: None`。
    ⇒ 官方閘門（`run_root_unittests.py`＝unittest 載具）當時是綠的，但那是**字母序的運氣**；
    真正的損失是 C3-P4c 要防的「同行程測試在開發者機器上註冊真 launchd job」在
    `TraceIsolationTest` 之後全程失效——掌舵者機器上那支 22:40 移除、22:58 又重生的
    `AutoSDD_Sentinel_s` 正是這個形狀。
    `addModuleCleanup` 也一併補掛回去：堆疊已被沖乾淨，不補的話真正的 module teardown
    不會還原，pin 會漏到同一個行程裡的後續測試模組。
    """
    try:
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        _pin_sentinel_off()
        unittest.addModuleCleanup(_unpin_sentinel_off)


def _gate(payload: dict, event: str = "PreToolUse") -> int:
    """跑額度閘，且**注入的是 hook 端真正會傳的那五個能力**。

    🔴 R82／Q2-02：閘搬出 hook 之後，「hook 有沒有把正確的東西接上去」變成一個可以
    獨立壞掉的面。所有測試一律走本函式、不自己捏假依賴——捏假的會讓「接線接錯」
    在整套測試裡完全看不見（分母 0 的鎖恆綠，本 repo 判過四成的那一桶）。
    """
    return qg.quota_gate(payload, blocking=guard.BLOCKING_TOOLS,
                         latch_read=guard.announced_latches,
                         latch_write=guard.remember_latch,
                         plan_writer=guard.write_resume_plan,
                         waker=guard.arm_quota_wakeup, event=event)


def _usage(inp: int, creation: int, read: int, out: int = 999_999) -> dict:
    """一筆 usage。`output_tokens` 預設給一個很大的值——若有人把它加進算式，
    每一條數字斷言都會當場爆掉（這是刻意的注入設計，不是隨手填的常數）。"""
    return {"input_tokens": inp, "cache_creation_input_tokens": creation,
            "cache_read_input_tokens": read, "output_tokens": out}


def _write_jsonl(path: Path, useds: list[int], *, junk: bool = False) -> Path:
    """把每一筆 `used` 寫成一列 assistant 記錄（拆成 2 + 3 + 其餘三個欄位）。"""
    lines: list[str] = ['{"type":"user","message":{"role":"user"}}']
    for used in useds:
        rec = {"type": "assistant",
               "message": {"model": "claude-opus-5", "usage": _usage(2, 3, used - 5)}}
        lines.append(json.dumps(rec, ensure_ascii=False))
    if junk:
        # 逐字稿常有半截尾行（正在寫入時被讀到）＋ 帶 usage 但型別全錯的行。
        lines.insert(1, '{"type":"assistant","message":{"usage":')
        lines.append('{"type":"assistant","message":{"usage":"not-a-dict"}}')
        lines.append('{"type":"assistant","message":{"usage":{"input_tokens":"x"}}}')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def _hook_invocations(event: str) -> list[tuple[str, str]]:
    """根 `.claude/settings.json` 內某事件的 `(matcher, 這個 hook 的完整呼叫字串)`。

    🔴 呼叫字串＝`command` **加上** `args` 全部串起來，不是只看 `command`。
    立案（R80 當回合實測）：並行的另一包把註冊面改成經 `_hook_launcher.py` 轉呼叫，
    於是實體腳本路徑從 `command` 搬到了 `args` ⇒ 只看 `command` 的判準當場回空清單，
    兩支既有接線鎖同時紅。**那是判準太脆，不是接線壞了**——被鎖的性質是「這支 hook
    有沒有被註冊在這個事件上」，而它與「是誰去啟動它」無關。這裡把兩處重複的讀法
    收成一份，順帶讓它對未來再換一次啟動器免疫。

    🔴 R80 收尾：上一段的判斷完全正確，但那份讀法**同一輪內長出了第二個家**——
    另一包為同一件事建了唯一真相源 `tools/lib/hook_wiring.py`（該包實測：repo 內原有的
    「只讀 command 找腳本名」解析器會在 exec form 下**全部**掃出空集合而恆綠。🔴 R80
    二審 `NEW-ARCH-R80B-07`：此處原本寫死支數，而同一個數字在三個家有兩個值——支數是
    量測值不是常數，現查指令見 `hook_wiring.py` 檔頭）。
    兩個家各自正確、卻只有一個會被下一次形態變更改到，那正是本 repo 的頭號病。
    這裡改為委派，回傳形狀逐字不變（呼叫端不受影響）。
    """
    return [(str(entry.get("matcher", "")), " ".join(_wiring().hook_entry_argv(hook)))
            for entry in _root_settings().get("hooks", {}).get(event, []) or []
            for hook in entry.get("hooks") or []]


def _root_settings() -> dict:
    return json.loads(
        (_REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))


def _wiring():
    """hook 佈線解析的唯一真相源（延後 import，不進本檔 import 期路徑）。"""
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import hook_wiring  # noqa: PLC0415

    return hook_wiring


def _isolated_env(tmp: Path, *, real_scheduler: bool = False) -> dict[str, str]:
    """乾淨的子行程環境：暫存、settings 鏈、旗標全部由本測試決定。

    🔴 `USERPROFILE`／`HOME`／`HOMEPATH` 一起改指到 `tmp` 是 R79 補的隔離（不是裝飾）：
    window 判定新增了「settings 鏈的 `model` 欄帶 1m 標記 ⇒ 1,000,000」這一階，而
    本機 `~/.claude/settings.json` 的 `model` 實測就是 `opus[1m]` ⇒ 沒有這道隔離時，
    下面每一條餵 190,000 期待 95% 的 e2e 會在**開發者自己的機器上**變成 19% 而靜默，
    在別人的機器上又是綠的。測試讀到誰的設定，必須由測試自己決定。
    `TMPDIR`／`TEMP`／`TMP` 同理：閂鎖 state 檔住在那裡，不隔離的話測試互相污染，
    而污染的方向正好是「看起來通過」。
    `CLAUDE_PROJECT_DIR` 反而必須指向**真的 repo 根**：hook 要靠它找到
    `tools/session_resume_planner.py` 去產任務書骨架。
    """
    env = dict(os.environ)
    env.update({
        "TMPDIR": str(tmp), "TEMP": str(tmp), "TMP": str(tmp),
        "USERPROFILE": str(tmp), "HOME": str(tmp), "HOMEPATH": str(tmp),
        "CLAUDE_PROJECT_DIR": str(_REPO_ROOT),
    })
    # 🔴 R81：額度那兩個旗標也要清。少清它們時，開發者自己機器上設過 `AUTOSDD_QUOTA_
    # GUARD_OFF=1` 就會讓下面所有 quota e2e **靜默轉綠**（守衛整支被關掉，rc 一律 0），
    # 而在 CI 上又是紅的——「污染的方向正好是看起來通過」同一條紀律。
    for flag in ("AUTOSDD_CONTEXT_WINDOW", "SDD_ACTIVE_VERSION",
                 "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "AUTOSDD_CONTEXT_GUARD_OFF",
                 "AUTOSDD_SENTINEL_OFF", "AUTOSDD_QUOTA_GUARD_OFF",
                 "AUTOSDD_QUOTA_FANOUT_CAP"):
        env.pop(flag, None)
    # 🔴 R84／C3-P4c：**預設不准碰真的排程器**，要碰得自己具名（`real_scheduler=True`）。
    # 立案是實測到的：本機 `launchctl list` 長期掛著一支 `AutoSDD_Sentinel_s`，session id
    # 就是 `s`——那是 `QuotaGateIsWiredToTheBurnPathTest` 的 fixture 檔名（`s.jsonl`）。
    # 它每 15 分鐘醒來一次，在 Windows 上就是掌舵者看到的那個黑框；而它的 session
    # 早就不存在，所以永遠不會有人來收它。
    # 🔴 上面那組 `TMPDIR`／`HOME` 隔離**結構上擋不住這件事**：`launchctl bootstrap` 進的是
    # 真正的 `gui/<uid>` 網域，與 plist 落在哪個目錄無關 ⇒「把暫存改掉」這一招在排程器
    # 這一軸沒有對應物。唯一能擋的位置就是「根本不要走到武裝那一步」。
    # 🔴 為什麼沿用 `AUTOSDD_SENTINEL_OFF` 而不是新開一個測試專用旗標：它已經是「不要
    # 武裝」的唯一真相源，新開一個等於同一件事兩個家。上面那個 `pop` 仍然必要且不衝突
    # ——它治的是「開發者機器上設過就靜默轉綠」，這裡治的是「測試不得留下真實副作用」，
    # 兩者方向相反地作用在同一個變數上，所以順序是先 pop 再由本測試決定。
    if not real_scheduler:
        env["AUTOSDD_SENTINEL_OFF"] = "1"
    return env


def _run_hook(payload: object, tmp: Path) -> tuple[int, str]:
    """以子行程真跑 hook，回 `(rc, stderr)`。

    走子行程而非 import＋呼叫 `main()`：hook 的契約是「被 Claude Code 以獨立行程呼叫、
    讀 stdin、以 exit code 表態」，import 進來會繞過 stdin 與 exit code 這兩個契約面
    （本 repo「驗證載具必須對齊 production 真正執行路徑」的既有紀律）。
    """
    env = _isolated_env(tmp)
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    proc = subprocess.run(
        [sys.executable, str(_HOOK)], input=text, env=env, capture_output=True,
        encoding="utf-8", errors="replace", timeout=180, check=False,
    )
    return proc.returncode, proc.stderr


class UsageArithmeticTest(unittest.TestCase):
    """性質 1：算式。控制組 ＋ 「把 output_tokens 算進去」的注入組。"""

    def test_sums_the_three_context_fields_only(self) -> None:
        self.assertEqual(guard.used_of(_usage(2, 817, 118_333)), 119_152)

    def test_output_tokens_is_excluded(self) -> None:
        """注入：同一筆只改 `output_tokens` ⇒ 結果**不得**變。改壞即紅。"""
        base = guard.used_of(_usage(2, 817, 118_333, out=0))
        self.assertEqual(base, guard.used_of(_usage(2, 817, 118_333, out=500_000)))

    def test_missing_fields_count_as_zero_but_empty_means_unmeasurable(self) -> None:
        """「量到零」與「量不到」必須分得開——混同是本 repo 反覆踩到的 fail-open。"""
        self.assertEqual(guard.used_of({"input_tokens": 7}), 7)
        self.assertIsNone(guard.used_of({}))
        self.assertIsNone(guard.used_of({"output_tokens": 5}))
        self.assertIsNone(guard.used_of("nope"))

    def test_bool_is_not_counted_as_int(self) -> None:
        """`True` 是 `int` 子類；不排除的話它會被算成 1 而讓整筆從「量不到」變成 0。"""
        self.assertIsNone(guard.used_of({"input_tokens": True}))


class WindowResolutionTest(unittest.TestCase):
    """性質 2：window 判定的誠實性與方向。"""

    def test_env_override_wins_and_is_labelled_pinned(self) -> None:
        window, source = guard.resolve_window(999_999, "123456")
        self.assertEqual(window, 123_456)
        self.assertIn("指定", source)

    def test_env_garbage_or_nonpositive_falls_through(self) -> None:
        """注入：壞值不得被當成 window（0 會讓 `tier_of` 永遠沉默＝靜默失效）。"""
        for dud in ("abc", "0", "-1", "", "1.5"):
            window, source = guard.resolve_window(0, dud)
            self.assertEqual(window, guard.CONSERVATIVE_WINDOW, f"{dud!r} 不該被採用")
            self.assertIn("推斷", source)

    def test_peak_above_200k_proves_a_wider_window(self) -> None:
        window, source = guard.resolve_window(guard.CONSERVATIVE_WINDOW + 1)
        self.assertEqual(window, guard.WIDE_WINDOW)
        self.assertIn("推斷", source)

    def test_boundary_is_strictly_greater_not_greater_equal(self) -> None:
        """恰好等於 200,000 **不**構成「大於 200K」的證據 ⇒ 仍取保守值。"""
        self.assertEqual(
            guard.resolve_window(guard.CONSERVATIVE_WINDOW)[0], guard.CONSERVATIVE_WINDOW)

    def test_default_direction_is_conservative(self) -> None:
        """注入：把預設改成 WIDE_WINDOW（猜大）即紅。方向錯的代價不對稱，見檔頭。"""
        self.assertEqual(guard.resolve_window(0)[0], guard.CONSERVATIVE_WINDOW)
        self.assertLess(guard.CONSERVATIVE_WINDOW, guard.WIDE_WINDOW)

    def test_inferred_sources_never_claim_to_be_pinned(self) -> None:
        """把推斷寫成已知，就是本 repo 判過的「假事實」——標籤必須互斥。"""
        for source in (guard.SOURCE_INFERRED_WIDE, guard.SOURCE_INFERRED_FLOOR):
            self.assertIn("推斷", source)
            self.assertNotIn("指定", source)
        self.assertNotIn("推斷", guard.SOURCE_PINNED)

    def test_message_always_carries_the_window_source(self) -> None:
        """使用者看到的那一行必須說得出分母是哪來的，否則誠實劃界只活在原始碼裡。

        同時驗 `MEASURE_LABEL`：SDD `context_ledger` 也有一條 90% 線但分子分母都不同，
        不標示的話讀者拿到兩個不同的百分比會以為其中一個壞了。
        """
        warn = guard.warn_message(80, 100, guard.SOURCE_INFERRED_FLOOR)
        hard = guard.hard_message(95, 100, guard.SOURCE_PINNED, "")
        self.assertIn(guard.SOURCE_INFERRED_FLOOR, warn)
        self.assertIn(guard.SOURCE_PINNED, hard)
        for text in (warn, hard):
            self.assertIn(guard.MEASURE_LABEL, text)


class TierBoundaryTest(unittest.TestCase):
    """性質 3 的判定面（exit code 由 e2e 那一組守）。"""

    def test_three_bands(self) -> None:
        self.assertIsNone(guard.tier_of(74_999, 100_000))
        self.assertEqual(guard.tier_of(75_000, 100_000), guard.TIER_WARN)
        self.assertEqual(guard.tier_of(89_999, 100_000), guard.TIER_WARN)
        self.assertEqual(guard.tier_of(90_000, 100_000), guard.TIER_HARD)

    def test_nonpositive_window_never_divides_by_zero(self) -> None:
        for window in (0, -1):
            self.assertIsNone(guard.tier_of(1, window))

    def test_hard_message_only_mentions_stage_compaction_in_sdd_context(self) -> None:
        """SDD 的 Stage Summary 手法綁 FSM 閉環，無條件推薦＝給純 AutoClaude session
        一條它執行不了的指引。控制組／注入組成對。"""
        self.assertNotIn("stage-compaction", guard.hard_message(95, 100, "s", ""))
        self.assertIn("stage-compaction",
                      guard.hard_message(95, 100, "s", "", sdd_active=True))


class ScanUsageTest(unittest.TestCase):
    """逐行掃描：最後一筆 ＋ 歷來最大，且壞行不得讓整支守衛崩潰。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-scan-"))

    def test_last_wins_and_peak_is_the_max(self) -> None:
        path = _write_jsonl(self.tmp / "a.jsonl", [100, 900, 300])
        self.assertEqual(guard.scan_transcript(path)[:2], (300, 900))

    def test_peak_is_not_just_the_tail(self) -> None:
        """注入：若實作改成只讀尾巴，peak 會塌成 300 ⇒ window 下界推論失去輸入。"""
        path = _write_jsonl(self.tmp / "b.jsonl", [250_001, 300])
        self.assertEqual(guard.scan_transcript(path)[1], 250_001)
        self.assertEqual(guard.resolve_window(guard.scan_transcript(path)[1])[0],
                         guard.WIDE_WINDOW)

    def test_broken_lines_are_skipped_not_fatal(self) -> None:
        path = _write_jsonl(self.tmp / "c.jsonl", [100, 200], junk=True)
        self.assertEqual(guard.scan_transcript(path)[:2], (200, 200))

    def test_no_usage_at_all_is_unmeasurable(self) -> None:
        path = self.tmp / "d.jsonl"
        path.write_text('{"type":"user"}\n', encoding="utf-8", newline="\n")
        self.assertEqual(guard.scan_transcript(path)[:2], (None, 0))

    def test_missing_file_is_unmeasurable_not_zero(self) -> None:
        self.assertEqual(guard.scan_transcript(self.tmp / "nope.jsonl")[:2], (None, 0))


class HookExitContractTest(unittest.TestCase):
    """端到端：真子行程 × 真 stdin × 真 exit code。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-e2e-"))
        # 🔴 R83：本類量的是 **context** 那把尺，而接電讓額度那把尺也跑在 PostToolUse 上 ⇒
        # 不種快取時額度軸會在這裡回報「量不到」並出聲，三條「必須完全靜默」當場紅，而**紅的
        # 原因與被測性質無關**：`_isolated_env` 把 `HOME` 指到沙箱、Keychain 讀不到憑證
        # （source=no-credentials-darwin）＝fixture 產物，不是 production 狀態（本機真跑
        # `quota_meter.py --json` 為 session 42%／rc=0）。種一份 free 帶健康快取把被測世界
        # 收斂回「額度正常時，低 context 必須靜默」；斷言一個字都沒放寬（`err == ""` 仍逐字
        # 成立，額度軸若誤出聲照樣紅）。
        _quota_cache(self.tmp, 20.0)

    def _payload(self, used: int, name: str) -> dict:
        return {"hook_event_name": "PostToolUse", "tool_name": "Read",
                "transcript_path": str(_write_jsonl(self.tmp / name, [used]))}

    def test_below_warn_is_silent_and_zero(self) -> None:
        rc, err = _run_hook(self._payload(100_000, "low.jsonl"), self.tmp)
        self.assertEqual((rc, err), (0, ""), "低水位必須完全靜默——常亮的燈等於沒有燈")

    def test_warn_band_speaks_but_does_not_block(self) -> None:
        rc, err = _run_hook(self._payload(160_000, "warn.jsonl"), self.tmp)
        self.assertEqual(rc, 0)
        self.assertIn("80.0%", err)
        self.assertIn("/compact", err)  # posix-abs-ok: 這是 Claude Code 的 slash 指令，不是路徑

    def test_hard_band_exits_two_with_numbers_and_plan(self) -> None:
        rc, err = _run_hook(self._payload(190_000, "hard.jsonl"), self.tmp)
        self.assertEqual(rc, 2, f"≥90% 必須 exit 2 才會回饋給模型。stderr={err[:400]}")
        self.assertIn("95.0%", err)
        self.assertIn("190,000", err)
        self.assertIn("200,000", err)
        self.assertIn("claude -r", err)
        plans = list(self.tmp.glob(f"{guard.PLAN_PREFIX}*.md"))
        self.assertEqual(len(plans), 1, f"任務書骨架沒被產出：{sorted(self.tmp.iterdir())}")
        body = plans[0].read_text(encoding="utf-8")
        for section in ("已驗證什麼", "還沒做什麼", "下一步的確切指令", "禁止事項"):
            self.assertIn(section, body, "根 CLAUDE.md 要求的四項缺一不可")
        self.assertIn("TODO:", body, "無法自動得知的欄位必須留佔位，不得代填")

    def test_same_tier_fires_once_per_session(self) -> None:
        """控制組（不同 session ⇒ 各自都喊）／注入組（同 session 第二次 ⇒ 不喊）。"""
        first = self._payload(190_000, "dedup.jsonl")
        rc1, err1 = _run_hook(first, self.tmp)
        rc2, err2 = _run_hook(first, self.tmp)
        self.assertEqual((rc1, rc2), (2, 0), f"去重失效或過度：{err1[:200]}|{err2[:200]}")
        self.assertEqual(err2, "")
        rc3, _ = _run_hook(self._payload(190_000, "other.jsonl"), self.tmp)
        self.assertEqual(rc3, 2, "換一個 session 仍不喊 ⇒ 去重把整個機制關掉了")

    def test_warn_then_hard_both_fire(self) -> None:
        """去重是**逐門檻**的：先喊過 75% 不得吃掉後來的 90%。"""
        path = self.tmp / "grow.jsonl"
        base = {"hook_event_name": "PostToolUse", "transcript_path": str(path)}
        _write_jsonl(path, [160_000])
        self.assertEqual(_run_hook(base, self.tmp)[0], 0)
        _write_jsonl(path, [190_000])
        self.assertEqual(_run_hook(base, self.tmp)[0], 2)

    def test_unreadable_payload_is_loud_but_never_blocking(self) -> None:
        """「輸入壞掉」不得靜默：rc=1（出聲但不阻斷），**不得**是 0，也不得是 2。

        判準出處：`test_check_hooks_liveness.py::degraded_payload_verdict`——rc=0
        ＝「送壞 payload 就能讓守衛整支消失，而且沒人看得見」；rc=2 ＝硬擋，爆炸半徑
        由註冊面的 matcher 決定。rc=1 兩者皆非。這一條與下一條刻意分開寫：把「輸入
        壞掉」和「量測不可得」混成同一個桶，正是本 repo 反覆踩到的 fail-open 形狀。
        """
        for label, text in {"壞 JSON": "{not json", "空 stdin": ""}.items():
            with self.subTest(label):
                rc, err = _run_hook(text, self.tmp)
                self.assertEqual(rc, 1, f"{label} 的 rc 應為 1（出聲但不阻斷），實得 {rc}")
                self.assertNotEqual(err.strip(), "", f"{label} 靜默失效了")

    def test_unmeasurable_state_stays_silent_and_zero(self) -> None:
        """「量測暫時不可得」是正常狀態（session 剛開場必經），一律 rc=0 且靜默。"""
        cases = {
            "缺 transcript_path": json.dumps({"tool_name": "Read"}),
            "transcript_path 指向不存在的檔": json.dumps(
                {"transcript_path": str(self.tmp / "ghost.jsonl")}),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertEqual(_run_hook(text, self.tmp), (0, ""))

    def test_env_override_reaches_the_running_hook(self) -> None:
        """指定值必須真的傳得到 production 路徑（不是只有純函式吃得到）。"""
        env = _isolated_env(self.tmp)
        env["AUTOSDD_CONTEXT_WINDOW"] = "1000000"
        payload = json.dumps(self._payload(190_000, "pinned.jsonl"))
        proc = subprocess.run(
            [sys.executable, str(_HOOK)], input=payload, env=env, capture_output=True,
            encoding="utf-8", errors="replace", timeout=180, check=False,
        )
        self.assertEqual((proc.returncode, proc.stderr), (0, ""),
                         "window 被指定為 1M 後 190K 只有 19%，不該有任何輸出")


class PlannerCliTest(unittest.TestCase):
    """交付物 B 的 CLI 契約：`--check` 不寫檔、排程指令只印不執行。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-cli-"))
        self.transcript = _write_jsonl(self.tmp / "s.jsonl", [123_456])

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(_PLANNER), "--transcript", str(self.transcript), *args],
            env=_isolated_env(self.tmp), capture_output=True,
            encoding="utf-8", errors="replace", timeout=180, check=False,
        )

    def test_check_prints_usage_and_writes_nothing(self) -> None:
        before = sorted(p.name for p in self.tmp.iterdir())
        proc = self._run("--check")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("123,456", proc.stdout)
        self.assertIn("61.7%", proc.stdout)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), before)

    def test_plan_is_written_and_prints_the_restart_command(self) -> None:
        out = self.tmp / "plan.md"
        proc = self._run("--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("claude -r s", proc.stdout)
        self.assertTrue(out.is_file())

    def test_unknown_flag_is_rejected_not_silently_ignored(self) -> None:
        """`--check-typo` 靜默掉進預設路徑並 rc=0 正是 R67-D20 的假綠原型。"""
        self.assertEqual(self._run("--chec").returncode, 2)

    def test_schtasks_command_is_printed_never_executed(self) -> None:
        out = self.tmp / "p2.md"
        proc = self._run("--out", str(out), "--print-schtasks-command")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Register-ScheduledTask", proc.stdout)
        self.assertIn("NextRunTime", proc.stdout, "沒有取證指令＝在教人做事後諸葛")
        for flag in ("-WakeToRun", "-StartWhenAvailable",
                     "-AllowStartIfOnBatteries", "-DontStopIfGoingOnBatteries"):
            self.assertIn(flag, proc.stdout, "四項補跑保護缺一即漏跑（DEF-101-249）")

    def test_it_never_claims_a_schedule_was_created(self) -> None:
        """反「事後諸葛」：輸出裡不得有「排程已成立」這類完成式宣稱。

        🔴 判準的邊界（誠實劃界，第一版就踩到）：最初寫的是 `assertNotIn("已排程")`，
        當場紅——因為那三個字也出現在**禁令**裡（「才准宣稱『已排程』」）。裸子字串
        分不出「宣稱」與「禁止宣稱」，而放寬成「只要有免責聲明就算過」等於沒有判準。
        改成**列舉完成式片語**：抓得到「把沒發生的事寫成發生了」，抓不到換句話說的
        同義宣稱——那半邊仍是人審責任，此處不宣稱涵蓋。
        """
        claims = ("會自動繼續", "已建立排程", "排程已建立", "已為你排程", "已排入")
        text = self._run("--out", str(self.tmp / "p3.md"),
                         "--print-schtasks-command").stdout
        self.assertEqual([c for c in claims if c in text], [])
        self.assertIn("沒有執行", text)
        self.assertIn("沒有建立任何排程", text)
        # 判準自證：合成一則真宣稱必須被抓到（否則上面那條恆綠）。
        self.assertTrue([c for c in claims if c in "✅ 已建立排程，會自動繼續"])


class WindowSourceOrderTest(unittest.TestCase):
    """R79：window 判定的五階優先序與交叉否決（純函式，紅綠由注入自證）。

    立案實測（掌舵者自己的機器）：user 層 settings 的 `model` 是 `opus[1m]`＝1,000,000，
    而 R78 版守衛拿 200,000 當分母 ⇒ 真實 15%／18% 各誤喊一次，之後到 99.9% 全靜默。
    「分母錯五倍」不是精度問題，是讓整支守衛在它唯一要防的那一刻失聲。
    """

    def test_the_five_sources_are_ordered_high_to_low(self) -> None:
        every = {"cc_window_raw": "300000", "settings_window": 400_000,
                 "model_hint": "opus[1m]", "observed_model": "claude-opus-5"}
        self.assertEqual(guard.resolve_window(999_999, "123456", **every)[0], 123_456)
        self.assertEqual(guard.resolve_window(999_999, None, **every)[0], 300_000)
        self.assertEqual(
            guard.resolve_window(999_999, None, **{**every, "cc_window_raw": None})[0],
            400_000)
        window, source = guard.resolve_window(
            0, None, **{**every, "cc_window_raw": None, "settings_window": None})
        self.assertEqual(window, guard.WIDE_WINDOW)
        self.assertEqual(source, guard.SOURCE_MODEL_MARKER)

    def test_the_harness_knobs_are_labelled_pinned_not_inferred(self) -> None:
        """分母若來自 harness 自己的旋鈕，訊息不得說它是推斷的（假事實同型）。"""
        for source in (guard.SOURCE_PINNED_CC_ENV, guard.SOURCE_PINNED_CC_SETTING):
            self.assertIn("指定", source)
            self.assertNotIn("推斷", source)
        self.assertIn("推斷", guard.SOURCE_MODEL_MARKER)

    def test_wide_marker_is_narrow_on_purpose(self) -> None:
        """注入：放寬成模糊比對 ⇒ `claude-opus-4-1` 會被讀成 1M＝往危險方向錯。"""
        for yes in ("opus[1m]", "claude-opus-5[1m]", "OPUS[1M]", "some-model-1m"):
            self.assertTrue(guard.carries_wide_marker(yes), yes)
        for no in ("opus", "claude-opus-4-1", "sonnet", "", None, "1m-ish-name"):
            self.assertFalse(guard.carries_wide_marker(no), repr(no))

    def test_a_different_model_actually_ran_vetoes_the_settings_hint(self) -> None:
        """`--model sonnet` 覆寫時，設定寫的 opus[1m] 不得把分母撐大五倍。"""
        self.assertIsNone(guard.window_from_model("opus[1m]", "claude-sonnet-4-5"))
        self.assertEqual(guard.window_from_model("opus[1m]", "claude-opus-5"),
                         guard.WIDE_WINDOW)

    def test_an_unrecognisable_observed_model_never_vetoes(self) -> None:
        """認不出家族就不敢否決——`<synthetic>` 這類佔位值實測會出現在逐字稿裡。"""
        for observed in (None, "", "<synthetic>", "unknown-model"):
            self.assertEqual(guard.window_from_model("opus[1m]", observed),
                             guard.WIDE_WINDOW, repr(observed))

    def test_the_r79_defect_state_is_reproduced_and_fixed(self) -> None:
        """本輪那筆缺陷的狀態逐字重建：1M session、used 190,000。

        修之前：window 判定拿不到 model 標記 ⇒ 200,000 ⇒ tier=hard（真實 19% 誤喊）。
        修之後：window=1,000,000 ⇒ tier=None（不喊）。兩側都斷言，缺一就沒有鑑別力。
        """
        blind, _ = guard.resolve_window(190_000)  # R78 版拿得到的全部證據
        self.assertEqual(guard.tier_of(190_000, blind), guard.TIER_HARD)
        fixed, source = guard.resolve_window(
            190_000, None, model_hint="opus[1m]", observed_model="claude-opus-5")
        self.assertEqual(fixed, guard.WIDE_WINDOW)
        self.assertIsNone(guard.tier_of(190_000, fixed), f"仍在誤喊；來源＝{source}")

    def test_garbage_knob_values_fall_through_instead_of_zeroing_the_window(self) -> None:
        """注入：壞值被採用 ⇒ window=0 ⇒ `tier_of` 永遠 None＝整支守衛靜默失效。"""
        for dud in ("abc", "0", "-1", "", "1.5", {}, []):
            window, source = guard.resolve_window(0, None, cc_window_raw=dud)
            self.assertEqual(window, guard.CONSERVATIVE_WINDOW, repr(dud))
            self.assertIn("推斷", source)

    def test_may_block_refuses_a_guessed_denominator(self) -> None:
        """只有保守下界不夠格硬擋——拿猜的分母鎖工具＝把本輪缺陷換方向再犯一次。"""
        self.assertFalse(guard.may_block(guard.SOURCE_INFERRED_FLOOR))
        for ok in (guard.SOURCE_PINNED, guard.SOURCE_PINNED_CC_ENV,
                   guard.SOURCE_PINNED_CC_SETTING, guard.SOURCE_MODEL_MARKER,
                   guard.SOURCE_INFERRED_WIDE):
            self.assertTrue(guard.may_block(ok), ok)


class SettingsChainTest(unittest.TestCase):
    """settings 鏈的讀取順序，以及本檔 e2e 隔離所依賴的那個前提。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-settings-"))

    def _write(self, name: str, body: dict) -> Path:
        path = self.tmp / name
        path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8",
                        newline="\n")
        return path

    def test_first_file_carrying_the_key_wins(self) -> None:
        high = self._write("high.json", {"model": "opus[1m]"})
        low = self._write("low.json", {"model": "sonnet"})
        self.assertEqual(guard.settings_value("model", [high, low]), "opus[1m]")
        self.assertEqual(guard.settings_value("model", [low, high]), "sonnet")

    def test_missing_or_broken_files_are_skipped_not_fatal(self) -> None:
        broken = self.tmp / "broken.json"
        broken.write_text("{not json", encoding="utf-8", newline="\n")
        good = self._write("good.json", {"model": "opus[1m]"})
        self.assertEqual(
            guard.settings_value("model", [self.tmp / "ghost.json", broken, good]),
            "opus[1m]")
        self.assertIsNone(guard.settings_value("nope", [good]))

    def test_the_repo_settings_carries_neither_window_key(self) -> None:
        """本檔 e2e 的隔離前提：repo 層 settings 不帶 `model`／`autoCompactWindow`。

        這不是可有可無的斷言。上面每一條 e2e 都靠「隔離掉 user 層之後 window 落回
        200,000」才成立；哪天有人把這兩個鍵之一寫進 repo settings，那些 e2e 會整批
        變成在量另一個東西——而那種漂移不會有任何訊息告訴你。此處讓它當場說話。
        """
        repo_settings = _REPO_ROOT / ".claude" / "settings.json"
        data = json.loads(repo_settings.read_text(encoding="utf-8-sig"))
        for key in (guard.CC_MODEL_KEY, guard.CC_WINDOW_KEY):
            self.assertNotIn(
                key, data,
                f"{repo_settings} 出現了 `{key}` ⇒ 本檔的 e2e 隔離前提破了。"
                "要嘛把它拿掉，要嘛同時改掉 _isolated_env 並在該處寫明新的前提",
            )


class LatchRearmTest(unittest.TestCase):
    """R79：分母被修正之後，硬線必須重新武裝。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-latch-"))

    def test_a_corrected_window_re_arms_the_hard_tier(self) -> None:
        """本輪缺陷的另一半，逐字重建。

        R78 版閂鎖鍵只有 tier：拿 200,000 當分母誤喊一次 hard 之後，等 peak 越過
        200,000、分母翻成 1,000,000、真的到 90% 時，**閂鎖還鎖著** ⇒ 唯一該出聲的
        那一次被前面那次誤報吃掉，從此到 99.9% 全靜默。
        把 `latch_key` 改回只含 tier（`return tier`）即可讓本條轉紅。
        """
        path = self.tmp / "grow.jsonl"
        base = {"hook_event_name": "PostToolUse", "transcript_path": str(path)}
        _write_jsonl(path, [190_000])          # window 200,000（下界）⇒ 95%
        self.assertEqual(_run_hook(base, self.tmp)[0], 2, "第一次硬線沒喊")
        _write_jsonl(path, [900_001])          # peak > 200,000 ⇒ window 1,000,000 ⇒ 90%
        rc, err = _run_hook(base, self.tmp)
        self.assertEqual(rc, 2, "分母修正後的真 90% 被前一次誤報的閂鎖吃掉了")
        self.assertIn("900,001", err)
        self.assertIn("1,000,000", err)

    def test_the_same_tier_and_window_still_only_fires_once(self) -> None:
        """控制組：重新武裝**不得**退化成「每次都喊」——那種守衛會被整個關掉。"""
        path = self.tmp / "same.jsonl"
        base = {"hook_event_name": "PostToolUse", "transcript_path": str(path)}
        _write_jsonl(path, [190_000])
        self.assertEqual(_run_hook(base, self.tmp)[0], 2)
        self.assertEqual(_run_hook(base, self.tmp), (0, ""))
        _write_jsonl(path, [195_000])  # 同一個 window、同一個 tier ⇒ 仍不得再喊
        self.assertEqual(_run_hook(base, self.tmp), (0, ""))


class PreToolUseBlockTest(unittest.TestCase):
    """R79 交付物 A：≥90% 時**真的擋下來**，而不是印一段話請模型自己記得。

    立案理由是本 repo 的實證：「純文件約束對當下的模型零攔阻力」。
    每一條放行條件都成對寫（會擋 ／ 不會擋），否則這支守衛可能只是恆綠。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-block-"))
        # 🔴 R81 收斂：種一份**新鮮且健康**的額度快取。本類量的是 context 那把尺，而
        # 額度那把尺現在會在「量不到」時出聲（SD-B2 的修法本體）——沙箱裡沒有憑證檔
        # ⇒ 不種的話每一條 `Task` e2e 都會多收到一行額度降級告警，而下面好幾條的判準是
        # `stderr == ""`。用「關掉額度守衛」來擺平會讓這幾條連帶失去對額度誤擋的鑑別力，
        # 所以這裡是把額度**量得到而且很寬鬆**，不是把它關掉。
        _quota_cache(self.tmp, 10.0)

    def _payload(self, used: int, name: str, tool: str) -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": tool,
                "transcript_path": str(_write_jsonl(self.tmp / name, [used]))}

    def test_expanding_tool_above_the_hard_line_is_blocked(self) -> None:
        rc, err = _run_hook(self._payload(900_001, "b1.jsonl", "Task"), self.tmp)
        self.assertEqual(rc, 2, f"展開型工具沒被擋下。stderr={err[:300]}")
        self.assertIn("Task", err)
        self.assertIn("/compact", err)  # posix-abs-ok: Claude Code 的 slash 指令，不是路徑

    def test_converging_tools_stay_allowed(self) -> None:
        """收斂還得做得完（寫任務書、跑 git）——擋到無法收斂的守衛會被整個關掉。"""
        for tool in ("Read", "Edit", "Write", "PowerShell", "Bash", "Grep"):
            with self.subTest(tool=tool):
                self.assertEqual(
                    _run_hook(self._payload(900_001, f"c-{tool}.jsonl", tool), self.tmp),
                    (0, ""))

    def test_a_guessed_denominator_never_blocks(self) -> None:
        """🔴 最重要的一條：分母是保守下界時**不得**硬擋。

        少了它，本輪修的那個缺陷會換個方向再犯一次——1M session 的真實 18% 會被當成
        90%，然後把展開型工具整組鎖死。控制組（同樣 90%、但分母可證）在上面那條。
        """
        rc, err = _run_hook(self._payload(190_000, "floor.jsonl", "Task"), self.tmp)
        self.assertEqual((rc, err), (0, ""), "拿猜出來的分母去硬擋工具了")

    def test_below_the_hard_line_is_allowed(self) -> None:
        self.assertEqual(
            _run_hook(self._payload(700_000, "warn.jsonl", "Task"), self.tmp), (0, ""))

    def test_the_human_escape_hatch_releases_everything(self) -> None:
        env = _isolated_env(self.tmp)
        env["AUTOSDD_CONTEXT_GUARD_OFF"] = "1"
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(self._payload(900_001, "off.jsonl", "Task")),
            env=env, capture_output=True, encoding="utf-8", errors="replace",
            timeout=180, check=False,
        )
        self.assertEqual((proc.returncode, proc.stderr), (0, ""))

    def test_blocking_does_not_latch(self) -> None:
        """擋一次就放行的東西不是阻斷。它必須一直擋到水位掉下來為止。"""
        payload = self._payload(900_001, "again.jsonl", "WebFetch")
        self.assertEqual(_run_hook(payload, self.tmp)[0], 2)
        self.assertEqual(_run_hook(payload, self.tmp)[0], 2, "第二次就放行＝閂鎖把阻斷吃掉了")

    def test_the_registered_matcher_matches_the_scripts_own_scope(self) -> None:
        """註冊面的 matcher 必須恰好是 `BLOCKING_TOOLS`。

        兩個方向都會出事：matcher 比射程寬 ⇒ 付了 python 啟動成本卻什麼也沒做；
        比射程窄 ⇒ 腳本自以為在守某個工具，實際上根本不會被觸發（靜默失效）。

        🔴 R80 訂正計數面（**條目數 ≠ 註冊數**）：exec form 之後，每個邏輯 hook 佔
        **兩個條目**——「Windows 載具（pythonw.exe）」與「POSIX 載具（帶 shebang 的
        啟動器）」各一，各平台恰好一條 spawn 得起來、另一條必定失敗，而 CC 對 spawn
        失敗是 **fail-open**（只記一行 ERROR、工具照跑）。所以那**不是重複註冊、也
        不會雙跑**；production 實測佐證：一次 Bash 呼叫命中兩個 PreToolUse block，
        `EFTYPE`（POSIX 半邊）出現 2 次，而 `Hook denied tool use for Bash` 只有 **1** 次。
        🔴 反過來說，把其中一條刪掉才是真缺陷：那會讓該 hook 在**另一個平台**整支
        消失，而且因為 fail-open，不會有任何東西轉紅（`tools/lib/hook_wiring.py` 的
        判準 E 就是為這件事存在的）。
        故本案改數**註冊（block）數**而不是條目數——被鎖的性質是「這個 matcher 底下
        有沒有註冊到這支腳本」，與「有幾個載具去啟動它」無關。
        """
        entries = _wiring().entries_launching(
            _root_settings(), "context_budget_guard", event="PreToolUse")
        matchers = [str(e.get("matcher", "")) for e in entries]
        self.assertEqual(len(matchers), 1, f"PreToolUse 註冊 block 數不是 1：{matchers}")
        self.assertEqual(
            set(matchers[0].split("|")), set(guard.BLOCKING_TOOLS),
            f"註冊 matcher {matchers[0]!r} 與腳本射程 {guard.BLOCKING_TOOLS} 不一致",
        )

    # 🔴 SA-R80-02：上面那條把 matcher 與射程釘成**相等**，於是它保證的是「兩個都寫錯
    # 時也一致」——鑑別力的方向錯了。掃描 S7-02 實測：`Task`／`WebFetch`／`WebSearch`
    # 這三個名字在本 harness 的 **8,106 次 tool_use 裡出現 0 次**（派子代理叫 `Agent`、
    # 批次編排叫 `Workflow`）⇒ S1「不要爆」的阻斷臂命中面是 0，蓋好了卻永遠不會觸發。
    # 下面三條補的是**有效性**那一向：圈了一組永遠不出現的名字必須當場轉紅。
    def test_the_expanding_tools_this_harness_actually_uses_are_blocked(self) -> None:
        """本 harness 真正在用的兩個展開型工具名必須真的被擋（端到端，不是看常數）。"""
        for tool in ("Agent", "Workflow"):
            with self.subTest(tool=tool):
                rc, err = _run_hook(
                    self._payload(900_001, f"reach-{tool}.jsonl", tool), self.tmp)
                self.assertEqual(rc, 2, f"`{tool}` 沒被擋下。stderr={err[:200]}")

    def test_a_blocking_set_that_never_occurs_is_caught(self) -> None:
        """注入自證（純函式，不依賴這台機器有沒有逐字稿）：圈一組不存在的名字必須紅，
        圈得到的必須綠，而**量不到**（空集合）時不得判紅——「量不到 ≠ 量到零」。"""
        observed = {"Read", "Edit", "Agent", "Workflow", "PowerShell"}
        self.assertTrue(guard.blocking_reach_problems(
            ("Task", "WebFetch", "WebSearch"), observed),
            "命中面為 0 的阻斷組沒有被抓出來（這就是 SA-R80-02 的本體）")
        self.assertEqual(guard.blocking_reach_problems(guard.BLOCKING_TOOLS, observed), [])
        self.assertEqual(guard.blocking_reach_problems(("Nope",), set()), [],
                         "量不到就判紅 ⇒ 這條鎖在沒有逐字稿的機器上是恆紅的噪音")

    def test_the_shipped_blocking_set_reaches_this_machines_real_traffic(self) -> None:
        """接到真語料：本機逐字稿裡出現過的工具名，必須與 `BLOCKING_TOOLS` 有交集。

        沒有逐字稿的環境（CI／fresh clone）量不到 ⇒ 依上一條的契約不判紅，但**分母會
        被印出來**，讓「這次其實沒量到」與「量到而且有交集」在輸出上分得開。
        """
        names: set[str] = set()
        base = planner.project_transcript_dir(_REPO_ROOT)
        paths = sorted((p for p in base.glob("*.jsonl") if p.is_file()),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:6] \
            if base.is_dir() else []
        for path in paths:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if '"tool_use"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    message = rec.get("message")
                    for block in (message or {}).get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            names.add(str(block.get("name") or ""))
        self.assertEqual(
            guard.blocking_reach_problems(guard.BLOCKING_TOOLS, names), [],
            f"實測 {len(paths)} 支逐字稿共 {len(names)} 種工具名：{sorted(names)}")


# ═══════════════════════════════════════ R79 續航協定（ADR-XPLAT-004）的回歸鎖
# 這一段守的性質與上面四類**不同**：上面守 context 水位，這裡守**額度**。兩者是兩個
# 分母（window vs 計費週期），混為一談是本題最常見的錯誤——額度耗盡當下水位可能只有
# 20%，阻斷模式的四道放行條件會全數放行。鎖也照這條界線分開寫。

sys.path.insert(0, str(_REPO_ROOT / "tools"))
# R81 缺口 A／B 的落地處；R84／ARCH-10 把它改成裸名 import（原行超出 line-length，折開）。
import quota_escalation as escalation  # noqa: E402

import session_resume_planner as planner  # noqa: E402

#: 全庫逐字稿實測到的**真實字面**（1,180 支檔掃出：session limit 151 筆／
#: monthly spend limit 71 筆）。語料是鎖的地基：判準改壞時要靠它轉紅。
_REAL_SESSION_LIMIT = "You've hit your session limit \u00b7 resets 9am (Asia/Taipei)"
_REAL_SESSION_LIMIT_MM = "You've hit your session limit \u00b7 resets 12:20pm (Asia/Taipei)"
_REAL_SPEND_LIMIT = ("You've hit your monthly spend limit \u00b7 "
                     "raise it at claude.ai/settings/billing")

#: \u4efb\u610f\u4e00\u500b\u4efb\u52d9\u66f8\u8def\u5f91\uff08\u8173\u672c\u7522\u751f\u5668\u662f\u7d14\u5b57\u4e32\u62fc\u63a5\uff0c\u4e0d\u78b0\u78c1\u789f\uff09\u3002\u523b\u610f\u7531 `tempfile` \u63a8\u5c0e\u800c\u4e0d\u662f
#: \u5beb `C:\tmp\...` \u5b57\u9762\u2014\u2014`test_platform_neutral_paths` \u6709\u4e00\u9053\u300c\u4e0d\u5f97\u51fa\u73fe\u5047\u7684 Windows
#: \u78c1\u789f\u6a5f\u8def\u5f91\u300d\u5224\u6e96\uff0c\u800c\u5b83\u662f\u5c0d\u7684\uff1a\u5beb\u6b7b\u78c1\u789f\u6a5f\u7684\u6e2c\u8a66\u5728 mac/Linux \u4e0a\u8b80\u8d77\u4f86\u662f\u5047\u4e8b\u5be6\u3002
_A_PLAN = str(Path(tempfile.gettempdir()) / "a_plan.md")


def _quota_transcript(path: Path, text: str, *, real_usage: int = 178_604) -> Path:
    """一支「撞線當下」的逐字稿：正常記錄 ＋ harness 寫的合成錯誤記錄。

    合成記錄的 usage **三欄都在、都是 0**（全庫 135 筆皆然），這正是水位盲區的成因。
    """
    rows = [
        {"type": "assistant", "timestamp": "2026-08-07T00:44:00.000Z",
         "message": {"model": "claude-opus-5[1m]",
                     "usage": _usage(12, 40_000, real_usage - 40_012)}},
        {"type": "assistant", "timestamp": "2026-08-07T00:44:01.000Z",
         "isApiErrorMessage": True,
         "message": {"model": guard.SYNTHETIC_MODEL,
                     "content": [{"type": "text", "text": text}],
                     "usage": {"input_tokens": 0, "cache_creation_input_tokens": 0,
                               "cache_read_input_tokens": 0, "output_tokens": 0}}},
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


class SyntheticUsageBlindnessTest(unittest.TestCase):
    """🔴 R79 P1：水位計在**額度耗盡的那一刻**讀成 0%，於是守衛整支靜默。

    為什麼這一條是 P1 而不是精度問題：90% 那條路正是負責寫「可重啟點任務書」的
    （`write_resume_plan`）。最需要任務書的那一刻，恰好是它結構上不會被產生的那一刻。
    成因是「量不到 ≠ 量到零」在上游又犯一次——合成記錄的 0 不是用量，是佔位。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_the_synthetic_record_must_not_zero_the_water_line(self) -> None:
        path = _quota_transcript(self.tmp / "hit.jsonl", _REAL_SESSION_LIMIT)
        used, peak, model = guard.scan_transcript(path)
        self.assertEqual(used, 178_604,
                         "最後一筆是合成記錄 ⇒ 修復前 used 會被它覆寫成 0，"
                         "水位掉成 0.0%、tier 變 None、守衛靜默")
        self.assertEqual(peak, 178_604)
        self.assertEqual(model, "claude-opus-5[1m]",
                         "合成記錄不得污染 model（window 交叉否決的輸入）")

    def test_a_transcript_of_only_synthetic_records_is_unmeasurable_not_zero(self) -> None:
        """全是合成記錄時要回「量不到」（None），不是「量到零」。

        這兩者混同就是本缺陷的形狀本身；修法若寫成「合成記錄算 0」而不是「整筆跳過」，
        這一條會紅。
        """
        rows = [{"type": "assistant", "message": {
            "model": guard.SYNTHETIC_MODEL,
            "content": [{"type": "text", "text": _REAL_SESSION_LIMIT}],
            "usage": {"input_tokens": 0, "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 0, "output_tokens": 0}}}]
        path = self.tmp / "only.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        self.assertIsNone(guard.scan_transcript(path)[0])


class QuotaClassifierTest(unittest.TestCase):
    """S1（可等）與 S2（等再久都沒用）必須分得開——本協定最貴的一種誤判。"""

    def test_the_four_real_literals_land_in_the_right_bucket(self) -> None:
        self.assertEqual(guard.classify_limit(_REAL_SESSION_LIMIT), guard.LIMIT_SESSION)
        self.assertEqual(guard.classify_limit(_REAL_SPEND_LIMIT), guard.LIMIT_SPEND)
        self.assertEqual(guard.classify_limit("API Error: 529 Overloaded"),
                         guard.LIMIT_TRANSIENT)
        self.assertEqual(guard.classify_limit("something nobody has seen"),
                         guard.LIMIT_UNKNOWN)

    def test_a_prefix_only_classifier_would_be_caught(self) -> None:
        """兩句話的前綴都是 `You've hit your `。只比對前綴的分類器會把 71 筆
        「等待無效」判成可等待 ⇒ 排一支永遠不會成功的工作、每次觸發燒一次探測，
        而真正該做的事（叫人提額）一直沒發生。"""
        self.assertTrue(_REAL_SESSION_LIMIT.startswith("You've hit your "))
        self.assertTrue(_REAL_SPEND_LIMIT.startswith("You've hit your "))
        self.assertNotEqual(guard.classify_limit(_REAL_SESSION_LIMIT),
                            guard.classify_limit(_REAL_SPEND_LIMIT),
                            "兩者被判成同一類＝分類器只看了共同前綴")

    def test_spend_wins_over_session_when_both_words_appear(self) -> None:
        """優先序不是任意的：`monthly spend limit` 必須先判，否則含 `limit` 的
        共同字樣會讓它落進可等待那一桶（fail-open 方向）。"""
        self.assertEqual(
            guard.classify_limit("session ended. " + _REAL_SPEND_LIMIT),
            guard.LIMIT_SPEND)

    def test_unknown_is_fail_closed_by_contract(self) -> None:
        """認不出來時走 `LIMIT_UNKNOWN`，而 `tick_plan` 對它**不重排**。
        寧可叫人，也不要排一支永遠不成的工作。"""
        verdict = {"open": False, "kind": guard.classify_limit("???"),
                   "rc": 1, "text": "???"}
        decision = planner.tick_plan(
            {"attempts": 0, "max_attempts": 5}, verdict, _NOON)
        self.assertEqual(decision["action"], "stop")


_TAIPEI = timezone(timedelta(hours=8))  # 釘死時區：CI runner 是 UTC、本機 +8 ⇒ 差 8 小時
_NOON = datetime(2026, 8, 7, 8, 44, 0, tzinfo=UTC).astimezone(_TAIPEI)


class ResetArithmeticTest(unittest.TestCase):
    """`resets 9am` **不帶日期也不帶年**，所以「下一個尚未發生的該時刻」是唯一正確規則。

    天真解成「今天的 9am」在下午跑會得到一個已經過去的時刻 ⇒ 觸發時刻算成負值 ⇒
    立刻探測、立刻再撞，把剛回來的額度再吃光。實測值裡已有 `11pm` 與 `3:50am`，
    跨午夜這條路徑真的會走到。
    """

    def _at(self, hour: int, minute: int = 0) -> datetime:
        return datetime(2026, 8, 7, hour, minute, tzinfo=UTC).astimezone(_TAIPEI)

    def test_the_real_incident_is_sixteen_minutes_not_five_hours(self) -> None:
        """實測那次：08:44 撞線、訊息說 9am ⇒ 只要等 16 分鐘。
        而 `DEFAULT_AT_EXPR` 的「+5 小時」會排到 13:44——晚 4 小時 44 分。"""
        now = self._at(0, 44)  # UTC 00:44 == Asia/Taipei 08:44
        reset = guard.parse_reset_at(_REAL_SESSION_LIMIT, now)
        self.assertIsNotNone(reset)
        self.assertEqual((reset - now).total_seconds() / 60, 16.0)

    def test_an_already_passed_hour_rolls_to_tomorrow(self) -> None:
        now = self._at(7, 0)  # 15:00 台北
        reset = guard.parse_reset_at(_REAL_SESSION_LIMIT, now)
        self.assertGreater(reset, now, "解成今天的 9am ⇒ 觸發時刻在過去 ⇒ 立刻再撞")
        self.assertEqual(reset.hour, 9)

    def test_across_midnight(self) -> None:
        now = self._at(15, 5)  # 23:05 台北
        reset = guard.parse_reset_at("resets 1am (Asia/Taipei)", now)
        self.assertEqual((reset.hour, reset.minute), (1, 0))
        self.assertGreater(reset, now)

    def test_both_observed_formats_parse(self) -> None:
        """全庫實測到的 7 個值含 `4am` 與 `12:20pm` 兩種格式，都要吃得下。"""
        self.assertEqual(guard.parse_reset_at(_REAL_SESSION_LIMIT_MM, _NOON).minute, 20)
        self.assertEqual(guard.parse_reset_at("resets 4am", _NOON).hour, 4)

    def test_noon_and_midnight_are_not_off_by_twelve(self) -> None:
        self.assertEqual(guard.parse_reset_at("resets 12am", _NOON).hour, 0)
        self.assertEqual(guard.parse_reset_at("resets 12pm", _NOON).hour, 12)

    def test_unparseable_returns_none_so_callers_cannot_guess(self) -> None:
        """`None` 是「我不知道」，呼叫端必須據此拒絕武裝——**不准**退回固定 5 小時。
        猜出來的時刻會讓排程成立、NextRunTime 也拿得到，取證規則照樣綠，但它醒在
        錯的時間：「憑證存在、但憑證不回答那個問題」是最難看見的假綠。"""
        self.assertIsNone(guard.parse_reset_at(_REAL_SPEND_LIMIT, _NOON))
        self.assertIsNone(guard.parse_reset_at("resets 25am", _NOON))
        self.assertIsNone(guard.parse_reset_at("", _NOON))

    def test_five_hours_is_not_a_valid_substitute(self) -> None:
        """觀測到的 7 個 reset 值（3:50am／4am／9am／11pm／12:20pm／12:30pm／6pm）
        **沒有一個**落在 5 小時的固定格點上 ⇒ reset 是滾動視窗，只能觀測不能算。
        這一條就是 `DEFAULT_AT_EXPR` 那個 `AddHours(5)` 是缺陷的證據。"""
        observed = ("3:50am", "4am", "9am", "11pm", "12:20pm", "12:30pm", "6pm")
        minutes = {guard.parse_reset_at(f"resets {v}", _NOON).minute for v in observed}
        self.assertNotEqual(minutes, {0},
                            "全部整點才有可能是固定間隔；實測含 :20/:30/:50")


class LimitEventScanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_the_authoritative_record_is_found(self) -> None:
        path = _quota_transcript(self.tmp / "a.jsonl", _REAL_SESSION_LIMIT)
        event = guard.latest_limit_event(path)
        self.assertEqual(event["kind"], guard.LIMIT_SESSION)
        self.assertIn("resets 9am", event["text"])
        self.assertEqual(event["timestamp"], "2026-08-07T00:44:01.000Z")

    def test_echoes_in_other_record_types_are_ignored(self) -> None:
        """同一句話會被 `queue-operation`／`user`／`attachment` 各複述一份（實測
        同一次撞線在 4 種記錄型別各留一份）。只有 assistant 合成記錄是權威版本；
        把回音也算進來會讓計數與時間戳都失真。"""
        path = self.tmp / "echo.jsonl"
        rows = [
            {"type": "queue-operation", "timestamp": "2026-08-07T00:00:00.000Z",
             "message": {"model": guard.SYNTHETIC_MODEL,
                         "content": [{"type": "text", "text": _REAL_SPEND_LIMIT}]}},
            {"type": "user", "timestamp": "2026-08-07T00:00:01.000Z",
             "content": _REAL_SPEND_LIMIT},
        ]
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        self.assertIsNone(guard.latest_limit_event(path))

    def test_no_event_is_none_not_a_fabricated_default(self) -> None:
        path = self.tmp / "clean.jsonl"
        path.write_text(json.dumps(
            {"type": "assistant",
             "message": {"model": "claude-opus-5", "usage": _usage(1, 2, 3)}}) + "\n",
            encoding="utf-8")
        self.assertIsNone(guard.latest_limit_event(path))


class RelayStateTest(unittest.TestCase):
    """狀態塊是整條續航鏈的**地板**：它壞掉時必須大聲，不得靜默補預設。"""

    GOOD = {
        "schema": planner.RELAY_SCHEMA, "session_id": "s", "plan_path": "p",
        "state": "armed", "kind": guard.LIMIT_SESSION, "reset_at": "2026-08-07T09:00:00",
        "reset_source": "transcript-verbatim", "attempts": 0, "max_attempts": 5,
        "allow_resume": False, "task_name": "T", "next_run_time": "2026/8/7 09:02:00",
    }

    def test_round_trip_through_a_human_readable_plan(self) -> None:
        """一份檔、兩個面：人讀六節、機器讀這一塊，沒有第二個家。"""
        doc = "# 可重啟點任務書\n\n## 3. 下一步\n\n內文\n\n" + planner.render_relay(self.GOOD)
        self.assertEqual(planner.parse_relay(doc), self.GOOD)

    def test_broken_block_and_absent_block_are_distinguishable(self) -> None:
        """「沒有武裝過」與「武裝過但狀態壞了」是兩件事，後者要大聲。
        兩者都回 `None` 時必須靠 `has_relay()` 分辨——這是「量不到 ≠ 量到零」
        在狀態檔這一層的形態。"""
        broken = planner.RELAY_BEGIN + "\n{ not json\n" + planner.RELAY_END
        self.assertIsNone(planner.parse_relay(broken))
        self.assertTrue(planner.has_relay(broken))
        self.assertIsNone(planner.parse_relay("沒有任何區塊"))
        self.assertFalse(planner.has_relay("沒有任何區塊"))

    def test_a_healthy_state_has_no_problems(self) -> None:
        self.assertEqual(planner.relay_problems(self.GOOD), [])

    def test_every_required_key_is_actually_required(self) -> None:
        for key in planner.RELAY_REQUIRED:
            with self.subTest(key=key):
                self.assertTrue(
                    planner.relay_problems({k: v for k, v in self.GOOD.items()
                                            if k != key}),
                    f"少了 `{key}` 卻仍判健康 ⇒ 缺鍵會被靜默補預設")

    def test_claiming_armed_without_evidence_is_a_problem(self) -> None:
        """🔴 反事後諸葛在狀態檔這一層：`NextRunTime` 這個**值**才是憑證，
        rc 不是（`Get-ScheduledTask` 對不存在的工作回 rc=0 ⇒ 只讀 rc 是假綠）。"""
        self.assertTrue(planner.relay_problems({**self.GOOD, "next_run_time": ""}))
        self.assertTrue(planner.relay_problems({**self.GOOD, "next_run_time": "   "}))

    def test_a_guessed_reset_may_not_arm(self) -> None:
        self.assertTrue(planner.relay_problems({**self.GOOD, "reset_source": "assumed-5h"}))
        for source in ("transcript-verbatim", "probe-verbatim", "operator"):
            with self.subTest(source=source):
                self.assertEqual(
                    planner.relay_problems({**self.GOOD, "reset_source": source}), [])

    def test_terminal_states_need_no_evidence(self) -> None:
        """已放棄／已續跑的狀態不再宣稱有排程，故不受憑證條款約束。"""
        self.assertEqual(
            planner.relay_problems({**self.GOOD, "state": "resumed",
                                    "next_run_time": ""}), [])


class TickDecisionTest(unittest.TestCase):
    """醒來之後**該做什麼**的唯一判定。這裡是整條鏈的大腦，五個分支逐一釘死。"""

    BASE = {"attempts": 0, "max_attempts": 5, "task_name": "T", "plan_path": "P"}

    def _tick(self, kind: str, text: str, *, is_open: bool = False, **over):
        return planner.tick_plan(
            {**self.BASE, **over},
            {"open": is_open, "kind": kind, "rc": 0 if is_open else 1, "text": text},
            _NOON)

    def test_quota_open_resumes(self) -> None:
        decision = self._tick(guard.LIMIT_UNKNOWN, "ok", is_open=True)
        self.assertEqual((decision["action"], decision["state"]), ("resume", "resumed"))

    def test_spend_limit_never_reschedules(self) -> None:
        """等再久都不會回來。重排等於每次觸發燒一次探測，而該做的事一直沒做。"""
        decision = self._tick(guard.LIMIT_SPEND, _REAL_SPEND_LIMIT)
        self.assertEqual(decision["action"], "stop")
        self.assertIn("提額", decision["reason"])

    def test_transient_retries_without_spending_an_attempt(self) -> None:
        """壞的是別的東西，不是額度。計入 attempts 的話幾次 502 就把重試預算吃光。"""
        decision = self._tick(guard.LIMIT_TRANSIENT, "API Error: 500 Internal server error")
        self.assertEqual(decision["action"], "rearm")
        self.assertEqual((decision["at"] - _NOON).total_seconds(),
                         planner.TRANSIENT_RETRY_SECONDS)

    def test_still_closed_rearms_from_the_newly_observed_reset(self) -> None:
        """自我校正：新的 reset 從**新訊息**讀，不是固定退避。"""
        decision = self._tick(guard.LIMIT_SESSION, "resets 10am (Asia/Taipei)")
        self.assertEqual(decision["action"], "rearm")
        self.assertEqual(decision["at"].hour, 10)
        self.assertEqual(decision["at"].minute, planner.RESET_SKEW_SECONDS // 60)

    def test_still_closed_without_a_parseable_reset_refuses_to_guess(self) -> None:
        decision = self._tick(guard.LIMIT_SESSION, "session limit, no time given")
        self.assertEqual(decision["action"], "stop")
        self.assertIn("拒絕", decision["reason"])

    def test_the_attempt_cap_actually_stops(self) -> None:
        """沒有硬上限的重排會在額度最緊的時候持續燒。上界＝5 × 一次探測 ≈ 16 萬 tokens。"""
        decision = self._tick(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT,
                              attempts=planner.MAX_PROBE_ATTEMPTS - 1)
        self.assertEqual(decision["action"], "stop")
        self.assertEqual(decision["state"], "abandoned")

    def test_one_below_the_cap_still_rearms(self) -> None:
        """雙邊帶：上限要真的在那一格才生效，不能提前一格就放棄（那是另一種失效）。"""
        decision = self._tick(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT,
                              attempts=planner.MAX_PROBE_ATTEMPTS - 2)
        self.assertEqual(decision["action"], "rearm")


def _outside_single_quoted(script: str) -> tuple[str, bool]:
    """把 PowerShell 單引號字串的內容剝掉，回傳（落在字串**外**的殘餘, 全部閉合與否）。

    PowerShell 單引號字串的文法很小且完整：`'` 進入字串；字串內 `''` 是一個字面單引號、
    仍在字串內；落單的 `'` 結束字串。這裡刻意自己走一遍而**不外呼 `powershell.exe`**——
    根層 unittest 在 mac／Linux 也要跑，多一支平台 skip 就是多一個沒人在跑的判準
    （而「沒人在跑的判準」正是本輪 S3 在治的東西）。

    🔴 這支掃描器與**真** tokenizer 的一致性由 R79 收輪當回合兩地對照證過：同一份腳本
    餵給 `powershell.exe` 的 `[Parser]::ParseFile`，健康版 `errors=0`、把 `_ps_single_quote`
    改成恆等後 `errors=4` 且 `Write-Output` 以獨立 token 出現——與本函式的判讀一致。
    """
    out: list[str] = []
    i, n, in_str = 0, len(script), False
    while i < n:
        ch = script[i]
        if not in_str:
            if ch == "'":
                in_str = True
            else:
                out.append(ch)
            i += 1
        elif ch == "'" and i + 1 < n and script[i + 1] == "'":
            i += 2                      # 跳脫過的字面單引號，仍在字串內
        elif ch == "'":
            in_str = False
            i += 1
        else:
            i += 1
    return "".join(out), not in_str


class EnduranceWiringTest(unittest.TestCase):
    """武裝路徑的接線：schtasks Action 必須叫回 runner，不是內嵌一份任務書全文。"""

    #: 含撇號的**合法** Windows 路徑（`O'Brien` 是真實會出現的使用者名）。刻意由
    #: `tempfile` 推導而不寫死磁碟機字面——`test_platform_neutral_paths` 有一道
    #: 「不得出現假的 Windows 磁碟機路徑」判準，而它是對的。
    _NASTY_PLAN = str(Path(tempfile.gettempdir()) / "O'Brien" / "a_plan.md")
    #: 惡意 `--task-name`：閉合前一個單引號、插一段自己的指令、再開一個新字串。
    _NASTY_TASK = "AutoSDD'; Write-Output PWNED; '"

    def test_an_apostrophe_in_the_plan_path_stays_inside_the_string(self) -> None:
        """🔴 R79 複審（ARCH nonblocking）修的缺陷：五個內插點把外部字串直接塞進
        PowerShell 單引號字串而未跳脫。`O'Brien` 這種**合法**使用者名就足以讓整段
        註冊腳本語法錯——而失效發生在 `powershell.exe` 那一端，本行程只看得到一個 rc。

        判準刻意不看「有沒有呼叫某個函式」（那種鎖改個名字就瞎），而是看**產出**：
        路徑的任何一段都不得落到單引號字串之外，且所有字串必須閉合。
        把 `_ps_single_quote` 改成恆等即紅（收輪當回合實測）。
        """
        script = planner.endurance_schtasks_script(self._NASTY_PLAN, "T", "'09:00'")
        outside, closed = _outside_single_quoted(script)
        self.assertTrue(closed, "含撇號的合法路徑讓某個單引號字串沒有閉合 ⇒ 整段腳本語法錯")
        self.assertNotIn("Brien", outside,
                         "路徑的一部分逃出單引號字串，會被 PowerShell 當成指令解析")

    def test_a_task_name_cannot_escape_the_string_and_become_a_command(self) -> None:
        """同一個缺陷的**注入**那一維，必須與上一題分開跑。

        🔴 兩者放同一份腳本會互相遮蔽：路徑那個撇號會開一個永不閉合的字串把 payload
        整段吞進去，於是注入這一維量到 0（HANDOFF 包第一版實測 A_TOKENS 由 70 崩到 22）。
        分兩題是判準的一部分，不是風格。
        """
        script = planner.endurance_schtasks_script(_A_PLAN, self._NASTY_TASK, "'09:00'")
        outside, closed = _outside_single_quoted(script)
        self.assertTrue(closed, "惡意 task-name 讓某個單引號字串沒有閉合")
        # 🔴 R84／C3-P1：判準由 `Write-Output` 換成 `PWNED`——**不是放寬，是換成唯一標記**。
        # `Write-Output` 是 PowerShell 的普通動詞，腳本自己也會**合法地**用它（本輪 P1 在
        # Principal 回退分支加了 `Write-Output 'PRINCIPAL-FALLBACK=…'` 留痕跡）⇒ 舊判準對
        # 「腳本裡本來就有一個 Write-Output」與「payload 逃出來了」無法區分，那是假紅。
        # `PWNED` 只住在 `_NASTY_TASK` 裡，兩者在 payload 中相鄰 ⇒ 逃出去一定一起逃出去，
        # 鑑別力不減。把 `_ps_single_quote` 改成恆等即紅（本輪實測，見收輪回報）。
        self.assertNotIn("PWNED", outside,
                         "payload 逃出單引號字串、成為一段會被真的執行的獨立指令")

    def test_the_principal_fallback_leaves_a_trace(self) -> None:
        """🔴 R84／C3-P1：S4U → 預設 Principal 的回退分支**必須留痕跡**。

        修前它是靜默的：`catch { Register-ScheduledTask @common }` 什麼都不印，而取證段
        （`_EVIDENCE_TEMPLATE`）只印 TaskName/LastRunTime/LastTaskResult/NextRunTime，
        一個字都不提 Principal ⇒「S4U 生效」與「已回退成 InteractiveToken」在憑證上
        **長得一模一樣**。而回退後有互動桌面，載具那一層若同時也退回 console 版就會彈窗
        ——兩層一起失效、零痕跡，正是掌舵者看到「黑框每 15 分鐘一次」而工具側查不到的原因。
        """
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        catch = next(line for line in script.splitlines()
                     if line.startswith("catch {"))
        self.assertIn("PRINCIPAL-FALLBACK", catch,
                      "回退分支又變回靜默 ⇒ 事後無從得知這台機器到底跑在哪個 Principal")
        self.assertIn("Format-List LogonType,RunLevel,UserId", script,
                      "憑證沒有印出實際生效的 Principal ⇒ 回退是不可觀測的")

    def test_the_new_evidence_lines_do_not_break_the_next_run_time_credential(self) -> None:
        """🔴 上一條加的輸出**絕不可**動到 `next_run_time()`——它是本 repo 反〈事後諸葛〉
        取證規則的機械形態（拿不到非空字串就不准宣稱已排程），弄壞它比彈窗嚴重得多。

        判準看的是**產出**：把新增的兩段輸出接在真實形態的取證輸出上，取回的值必須逐字
        不變。`LogonType`／`RunLevel`／`UserId` 三個欄名都不以 `nextruntime` 開頭，所以
        這件事在設計上就成立——但「設計上成立」正是需要被釘住的那種宣稱。
        """
        evidence = ("TaskName       : AutoSDD_Sentinel_x\n"
                    "LastRunTime    : 2026/8/11 10:00:00\n"
                    "LastTaskResult : 0\n"
                    "NextRunTime    : 2026/8/11 10:15:00\n")
        principal = "\nLogonType : InteractiveToken\nRunLevel  : Limited\nUserId    : W\\me\n"
        self.assertEqual(planner.next_run_time(evidence), "2026/8/11 10:15:00")
        self.assertEqual(planner.next_run_time(evidence + principal), "2026/8/11 10:15:00")
        self.assertEqual(
            planner.next_run_time("PRINCIPAL-FALLBACK=default-interactive\n"
                                  + evidence + principal), "2026/8/11 10:15:00")

    def test_the_escaper_doubles_every_apostrophe(self) -> None:
        """跳脫函式本身的直接判準——上面兩題是產出面，這一題讓「被改成恆等」當場點名。"""
        self.assertEqual(planner._ps_single_quote("a'b''c"), "a''b''''c")
        self.assertEqual(planner._ps_single_quote("no quotes"), "no quotes")

    def test_the_evidence_template_escapes_its_task_name_too(self) -> None:
        """取證指令與註冊腳本是**兩個**內插點：只修其中一個＝另一個仍可被注入。"""
        rendered = planner._EVIDENCE_TEMPLATE.format(
            task=planner._ps_single_quote(self._NASTY_TASK))
        outside, closed = _outside_single_quoted(rendered)
        self.assertTrue(closed)
        self.assertNotIn("Write-Output", outside)

    def test_the_action_calls_the_runner_not_a_model_turn(self) -> None:
        """🔴 R79 修的缺陷：舊 Action 把整份任務書內嵌進 `-Command` 當 prompt
        ⇒ 任務書一長就撞命令列長度上限，且骨架裡的 `TODO:` 佔位會被當成指令
        餵給無人看管的那一跑。改成叫回本檔後，醒來的第一段是確定性的 Python。"""
        argument = planner.runner_action_argument(_A_PLAN, "T")
        self.assertIn("--resume-tick", argument)
        self.assertIn("session_resume_planner.py", argument)
        self.assertNotIn("-p -r", argument, "Action 不該直接開一個模型回合")

    def test_the_script_refuses_to_register_without_the_plan(self) -> None:
        """「任務書不存在就中止」必須寫在 **Action 自己**裡——任務書不存在時，
        沒有人讀得到寫在它裡面的規則。"""
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        self.assertIn("Test-Path", script)
        self.assertIn("throw", script)

    def test_registration_always_carries_its_own_evidence_step(self) -> None:
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        self.assertIn("Get-ScheduledTaskInfo", script)
        self.assertIn("NextRunTime", script)

    def test_the_four_wake_settings_are_all_present(self) -> None:
        """四項缺一即漏跑（`schtasks-wake-to-run`）。建構 cmdlet 的參數名與物件屬性名
        極性相反，所以這裡比對的是**參數名**那一組。"""
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        for flag in ("-StartWhenAvailable", "-WakeToRun",
                     "-AllowStartIfOnBatteries", "-DontStopIfGoingOnBatteries"):
            with self.subTest(flag=flag):
                self.assertIn(flag, script)

    def test_the_action_uses_a_no_console_interpreter(self) -> None:
        """🔴 R79 續修的回歸鎖（掌舵者當場回報：哨兵每 15 分鐘彈一個 console 視窗）。

        鎖的是**載具**而不是只鎖 LogonType，理由是射程：S4U 註冊需要提權，而哨兵的
        主要武裝路徑（SessionStart hook）一律非提權——本輪真機實測 `Register-ScheduledTask
        ... -LogonType S4U` 在非提權下回「存取被拒」且工作根本沒建立。在那條路上唯一
        還成立的「不彈視窗」保證就是載具：`python.exe` 是 console 子系統、Interactive
        下必定配一個視窗；`pythonw.exe` 是同一個直譯器的 GUI 子系統版本，不配置 console。

        🔴 **R80 訂正判準（act 在 Linux 容器實跑抓到的紅；本機 Windows 結構上看不見）**：
        原判準逐字斷言字面 `pythonw.exe`，而 **POSIX 上根本沒有 `pythonw`**——
        `guard.quiet_python()` 在那裡依約回 `sys.executable`，於是這條在容器裡必紅
        （逐字：`'pythonw.exe' not found in '... -Execute '/opt/.../bin/python3' ...'`）。
        這正是鐵律三「這在另一個平台是什麼值」，而它被寫成了一個平台常數。
        改法**不是**加平台守衛（那會多一個 skip 站點、也讓 POSIX 上零判準），而是把問題
        換成兩平台同一條：**Action 的載具必須是「本 repo 唯一那支不配置 console 的解析器」**
        ——即 `guard.quiet_python()`，而不是某個字面。三格判準各自獨立：
          ① 產生的腳本裡真的用了那個值（行為面，兩平台皆成立）；
          ② 來源面：planner 必須**呼叫**那支唯一真相源，不得自己算一份（同一份知識三個家
             正是 R80 收掉的缺陷之一）——這一格讓「改回 `sys.executable`」在 POSIX 上
             （兩者恰好同值、行為面看不出來）照樣紅；
          ③ Windows 上那支解析器必須真的解析到 `pythonw.exe`（缺陷本體所在的平台）。
        `if os.name == "nt"` 是**平台條件斷言**、不是 skip 站點：本條在兩個平台都會跑、
        都有判準，只是第三格的斷言只在 Windows 上有意義。
        """
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        self.assertIn(planner._ps_single_quote(guard.quiet_python()), script)
        self.assertIn("guard.quiet_python()", _PLANNER.read_text(encoding="utf-8"),
                      "載具解析必須委派給唯一真相源 guard.quiet_python()，不得自己算一份")
        if os.name == "nt":
            self.assertTrue(guard.quiet_python().lower().endswith("pythonw.exe"),
                            f"Windows 上的無 console 載具解析錯了：{guard.quiet_python()}")

    def test_the_principal_is_s4u_first_with_a_non_elevated_fallback(self) -> None:
        """與 `tools/install_windows_nightly.ps1` 的兩支既有工作對齊（該檔 R69 S-5 段）：
        Interactive 的工作在使用者未登入時整輪不跑，且視窗開在使用者桌面上。

        兩個方向都要鎖：① S4U 必須是**先試的**那一支（回退分支才有意義，否則等於沒改）；
        ② 回退分支必須存在（非提權下 S4U 會被拒，只掛 S4U 會讓哨兵整條武裝斷掉——
        那是把一個干擾缺陷換成一個功能缺陷，不是修好）。"""
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        self.assertIn("-LogonType S4U", script)
        self.assertNotIn("-LogonType Interactive", script)
        self.assertLess(script.index("-Principal $principal"),
                        script.index("catch { Register-ScheduledTask"),
                        "S4U 必須是 try 的那一支，回退才有意義")

    def test_the_audit_trail_has_exactly_one_home(self) -> None:
        """🔴 本輪端到端實測抓到的真缺陷：稽核痕跡分裂成兩個檔。

        `--resume-tick` 必須在讀任何東西**之前**就寫下「我被叫起來了」——那一刻它手上
        只有 `--plan`（session id 還躺在沒讀的狀態塊裡）。舊寫法用 session id 當鍵，
        於是開場那一行落在 `..._<plan 檔名>.jsonl`、其餘落在 `..._<session id>.jsonl`；
        而「觸發了但早期就失敗」那一行剛好寫進沒有人會去看的那個檔 ⇒ 這道機制唯一要
        守的東西（讓「沒觸發」可偵測）自己漏掉。鍵只能是任務書路徑。
        """
        plan = Path(tempfile.mkdtemp()) / "some_plan.md"
        self.assertEqual(planner.endurance_log_path(plan),
                         planner.endurance_log_path(Path(str(plan))))
        self.assertIn("some_plan", planner.endurance_log_path(plan).name)
        source = _PLANNER.read_text(encoding="utf-8")
        tick = source[source.index("def _resume_tick"):]
        first = tick.index('append_log(log, "woken"')
        self.assertNotIn("parse_relay", tick[:first],
                         "開場留痕之前就去讀狀態塊 ⇒ 讀不出來時那一行永遠不會被寫")

    def test_quota_is_not_wired_into_the_context_blocking_path(self) -> None:
        """🔴 額度 ≠ context 水位。額度耗盡時水位可能只有 ~18%（本輪實測），
        阻斷模式的四道放行條件會全數放行——把額度掛進那支守衛就是讓一個東西
        假裝能做兩件事。這一條釘住「沒有掛上去」。"""
        source = _HOOK.read_text(encoding="utf-8")
        body = source[source.index("def block_verdict"):]
        # 🔴 R81 擴一組：額度那條路徑**也**不得從 `block_verdict()` 內被觸發。
        # 立案是本包當回合的注入實測——把 `quota_gate(payload)` 塞進 `block_verdict()` 的
        # 早退分支時，這條鎖與新增那條**都判綠**（注入 rc=0）。而那個形態正是 SA-B1 描述的
        # 死碼：`block_verdict()` 只在 context ≥90% 才到得了，額度耗盡時 context 只有 ~18%。
        # 「額度看起來有人守，實際上那段程式跑不到」比沒有機制更糟。
        for name in ("classify_limit", "parse_reset_at", "latest_limit_event",
                     "quota_gate", "read_quota", "quota_tier_of"):
            with self.subTest(name=name):
                self.assertNotIn(name, body, f"`{name}` 被接進阻斷路徑了")

    def test_the_quota_axis_is_a_separate_path_not_a_missing_one(self) -> None:
        """🔴 R81 補上這條鎖**反向的那一半**（SA-B1 抓到的形態）。

        上一條只釘住「額度沒有被掛進 context 阻斷路徑」，於是「額度根本沒有人在守」
        與「額度有自己的路徑」兩種狀態它**都判綠**——分母 0 的鎖恆綠，正是本 repo
        判過四成的那一桶。這一條要求 quota 必須有一條**存在且獨立**的路徑：
        `quota_gate()` 存在、被 `main()` 呼叫、且它自己不碰 context 那三個早退符號。

        🔴 R82／Q2-02 擴射程：那條路徑現在住 `tools/lib/quota_gate.py`，所以「存在」
        這件事的掃描面必須跟著搬——否則本鎖會因為 hook 裡再也找不到 `def quota_gate(`
        而變成**恆紅**（那與恆綠一樣沒有鑑別力，而且會被人順手刪掉）。
        """
        source = _HOOK.read_text(encoding="utf-8")
        gate_src = _QUOTA_GATE.read_text(encoding="utf-8")
        self.assertIn("def quota_gate(", gate_src, "額度軸連一條路徑都沒有")
        gate = gate_src[gate_src.index("def quota_gate("):]
        # 剝註解 ＋ 用詞界比對：不剝時「解釋為什麼不用 may_block」的那行註解自己會命中；
        # 不用詞界時 `quota_tier_of(` 會被 `tier_of(` 掃到。兩個都是掃描器把文字當程式碼。
        gate = "\n".join(ln for ln in gate.splitlines() if not ln.lstrip().startswith("#"))
        for name in (r"\btier_of\(", r"\bmay_block\(", r"\bscan_transcript\("):
            with self.subTest(name=name):
                self.assertIsNone(re.search(name, gate),
                                  f"`{name}` 被接進額度路徑了 ⇒ 兩把尺又共用早退條件")
        body = source[source.index("def main("):source.index("def block_verdict")]
        self.assertIn("quota_gate.quota_gate(", body, "hook 沒有呼叫額度閘 ⇒ 蓋好沒接電")
        self.assertLess(body.index("quota_gate.quota_gate("), body.index("transcript_path"),
                        "額度那一呼叫落在 context 的五道早退之後 ⇒ 撞額度時 context 只有 "
                        "~18%，那一支一次都不會被執行（SA-B1 判過的死碼）")

    def test_the_quota_module_boundary_is_one_way_and_fail_open(self) -> None:
        """🔴 R82／Q2-02 的兩個**安全條件**，逐條釘住（拆分做錯時它們是靜默失效的）。

        ①**單向**：`tools/lib/quota_gate.py` 不得 import 這支 hook。反向 import 會在
          `runpy` 以 `__main__` 起 hook 時把它整支再載入一次（兩個模組物件、兩份模組層
          副作用），而症狀是「偶爾怪怪的」而不是當場爆掉。
        ②**fail-open**：hook 對它的 import 必須是 `try/except`，缺席時符號為 `None`。
          hard import 會讓「額度模組不見了」把 **context 阻斷也一起帶走**——那道守衛的
          爆炸半徑是所有工具，而失效的表徵（不再有人出聲）與「修好了」相同。
        """
        gate_src = _QUOTA_GATE.read_text(encoding="utf-8")
        code = "\n".join(ln for ln in gate_src.splitlines()
                         if not ln.lstrip().startswith("#"))
        self.assertIsNone(re.search(r"^\s*(import|from)\s+context_budget_guard", code,
                                    re.MULTILINE),
                          "額度閘反向 import 了 hook ⇒ hook 會被載入第二次")
        source = _HOOK.read_text(encoding="utf-8")
        head = source[:source.index("\ndef ")]
        self.assertRegex(head, r"try:\s*\n\s*import quota_gate.*\n\s*except Exception.*"
                               r"\n\s*quota_gate = None",
                         "hook 對額度閘是 hard import ⇒ 該模組缺席會連 context 阻斷一起帶走")
        self.assertIn("quota_gate is not None", source,
                      "import 是 fail-open 但呼叫端沒有守 None ⇒ 缺席時改成 AttributeError")


# ══════════════════════════ R79 補洞包：預防性哨兵（ADR-XPLAT-004 §2.6）的回歸鎖
# 🔴 這一段守的是**觸發層**，與上面那一段（判定層）不同。上一段證明了「撞線之後怎麼
# 等」是對的，但整條鏈仍然要人手動去按 `--arm-endurance`——而撞線那一刻沒有人在。
# 本段的每一條都對著同一個問題：**沒有人按的時候，這個機制還會不會動**。


def _sentinel_event(kind: str, text: str, stamp: str = "2026-08-07T00:44:01.000Z") -> dict:
    return {"kind": kind, "timestamp": stamp, "text": text}


def _wait_for(path: Path, seconds: float) -> bool:
    """等一個檔案出現；回「有沒有等到」。detached 子行程沒有可 join 的 handle，
    只能靠副作用取證——所以這裡輪詢而不是 `proc.wait()`（那是刻意的非同步）。"""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.is_file():
            return True
        time.sleep(0.1)
    return path.is_file()


class SentinelDecisionTest(unittest.TestCase):
    """哨兵四分支的唯一判定。每一支單獨可注入，且兩個閾值的**方向**各自被釘住。"""

    def _now(self, hour: int, minute: int = 0) -> datetime:
        return datetime(2026, 8, 7, hour, minute, tzinfo=UTC).astimezone(_TAIPEI)

    def test_a_pending_hit_with_a_future_reset_rearms_to_that_moment(self) -> None:
        """分支①：撞線了、reset 還沒到 ⇒ 重排到 reset+skew，**本次不花任何 token**。

        這一支是哨兵存在的理由：它把「撞線」與「排到正確時刻」之間那段本來需要人的
        空白補起來，而且補的過程完全不需要問伺服器。
        """
        now = self._now(0, 45)  # 08:45 台北；訊息說 9am ⇒ 還有 15 分鐘
        decision = planner.sentinel_decide(
            _sentinel_event(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT), "", 10.0, now)
        self.assertEqual(decision["action"], "arm_reset")
        self.assertEqual(decision["reset_source"], "transcript-verbatim")
        self.assertEqual((decision["at"] - decision["reset_at"]).total_seconds(),
                         planner.RESET_SKEW_SECONDS)
        self.assertEqual((decision["reset_at"].hour, decision["reset_at"].minute), (9, 0))

    def test_a_pending_hit_whose_reset_already_passed_spends_one_probe(self) -> None:
        """分支②：撞線了、reset 已過 ⇒ 這是**唯一**會花額度的一支。

        為什麼不能直接宣告「額度回來了」：reset 是滾動視窗，過了那個時刻不蘊含額度
        真的通了（醒來只要一動就重新起算）。只有問伺服器才知道，所以這一支必須探測。
        """
        # 事件錨在 08:44（台北），訊息說 9am ⇒ reset=09:00；現在已是 15:00。
        decision = planner.sentinel_decide(
            _sentinel_event(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT), "",
            10.0, self._now(7, 0))
        self.assertEqual(decision["action"], "probe")
        self.assertIsNone(decision["at"])

    def test_an_already_handled_hit_is_never_reacted_to_twice(self) -> None:
        """🔴 **R80 訂正：這是一支「保留舊介面」的相容性測試，不是現行語意的判準。**

        原 docstring 逐字保留了那句已被本輪判定為假的立案理由（「武裝當下把現存最後一筆
        記成已處理，因為我們此刻跑得動武裝指令就證明額度是通的」）。武裝是**純本機
        subprocess、零 API 呼叫**，證明不了額度——那句話正是哨兵整晚失明的 P0 根因，
        而它同輪只在 planner 的一處被改掉、在這裡原文留著 ⇒ 讀這支測試的人會拿到已被
        推翻的規格，而綠燈替那句假話背書。同一份知識三個家只改一個，是本 repo 的頭號病。

        現行語意：`handled_through` **已降為稽核欄位**，`_sentinel_tick` 一律傳空字串
        ⇒ 本條走的是 production 走不到的那條分支，它「不可能因為業務邏輯改變而失敗」
        （Rule 9）。留著它只為了兩件事：①舊狀態塊仍帶該欄位、讀得回來時語意不得漂移；
        ②若有人把它改回「唯一的已處理判準」，這支的斷言仍描述它該有的行為。
        **真正守現行語意的判準在 `UnhandledLimitDetectionTest`**（事件晚於全域最後一次
        成功 API 回應 ⇒ 未處理；早於 ⇒ 已處理），那一組才是接在 production 路徑上的。
        """
        event = _sentinel_event(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT)
        decision = planner.sentinel_decide(event, event["timestamp"], 10.0, self._now(7))
        self.assertEqual(decision["action"], "patrol", "同一筆事件被重複反應")
        newer = _sentinel_event(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT,
                                "2026-08-07T00:44:02.000Z")
        self.assertEqual(
            planner.sentinel_decide(newer, event["timestamp"], 10.0, self._now(7))["action"],
            "probe", "**新**的一筆撞線被 handled_through 一起吃掉了 ⇒ 哨兵永久失聰")

    def test_a_live_session_keeps_patrolling_for_free(self) -> None:
        """分支③：沒有未處理的撞線、session 還在動 ⇒ 續巡。零 token。"""
        now = self._now(7)
        decision = planner.sentinel_decide(None, "", 60.0, now)
        self.assertEqual(decision["action"], "patrol")
        self.assertEqual((decision["at"] - now).total_seconds(),
                         planner.SENTINEL_INTERVAL_SECONDS)

    def test_an_idle_session_disarms_itself(self) -> None:
        """分支④：工作結束了就下班。留著死哨兵會讓 `Get-ScheduledTask` 給出過期事實
        （本 repo 對「查詢載具給出過期事實」有判例）。"""
        decision = planner.sentinel_decide(
            None, "", planner.SENTINEL_IDLE_SECONDS + 1, self._now(7))
        self.assertEqual((decision["action"], decision["at"]), ("disarm", None))

    def test_the_idle_boundary_is_two_sided(self) -> None:
        """雙邊帶：門檻要真的在那一格才生效。提前一秒下班與永不下班是兩種不同的失效。"""
        self.assertEqual(planner.sentinel_decide(
            None, "", planner.SENTINEL_IDLE_SECONDS - 1, self._now(7))["action"], "patrol")

    def test_a_spend_limit_escalates_instead_of_waiting(self) -> None:
        """本協定最貴的誤判在哨兵這一層的形態：月度上限等到天荒地老都不會回來。"""
        decision = planner.sentinel_decide(
            _sentinel_event(guard.LIMIT_SPEND, _REAL_SPEND_LIMIT), "", 10.0, self._now(7))
        self.assertEqual(decision["action"], "escalate")
        self.assertIn("提額", decision["reason"])

    def test_an_unparseable_reset_refuses_to_guess(self) -> None:
        """解不出時刻就叫人，**不准**退回固定間隔——猜出來的排程會醒在錯的時間，
        而 `NextRunTime` 照樣拿得到＝取證規則全綠的假綠。"""
        decision = planner.sentinel_decide(
            _sentinel_event(guard.LIMIT_SESSION, "session limit, no time given"),
            "", 10.0, self._now(7))
        self.assertEqual(decision["action"], "escalate")
        self.assertIn("拒絕用猜的", decision["reason"])

    def test_the_patrol_interval_bounds_the_post_reset_dead_time(self) -> None:
        """🔴 R80 訂正：這一條原名／原文宣稱「間隔小於**最短觀測窗**」，那句話已被證偽。

        原文的依據是單一事件（08:44 撞、`resets 9am` ⇒ 16 分鐘）。R80 以全庫 1,433 支
        逐字稿重量（`tools/probe/reset_window_distribution.py`，14 個相異 episode）：
        最短窗是 **0.5 分鐘**，4/14 個 episode ≤16 分 ⇒ 900 秒**並不**小於最短觀測窗，
        原本的測試名是一句假話。**留著一句假話比沒有測試更糟**（本 repo 反覆判過的形態），
        所以這裡改成釘住那個真正成立的性質。

        真正的性質：間隔決定「reset 之後最壞多久才會有人動作」。窗比間隔短時，那一次走的
        是 `probe` 而不是 `arm_reset` ⇒ **代價是一次探測（~32K tokens），不是失效**。
        故判準是**上界＋shrink-only 方向**：調大即紅（死等變長），調小照樣綠（巡邏零 token，
        這一側沒有需要權衡的量）。取捨全文見 ADR-XPLAT-004 §2.7。
        """
        self.assertLessEqual(
            planner.SENTINEL_INTERVAL_SECONDS, 900,
            "巡邏間隔被調大 ⇒ reset 之後的最壞死等時間跟著變長，而巡邏本身零 token、"
            "調大換不到任何東西。特別是**不得**改成 50 分鐘：那個數字是 ScheduleWakeup "
            "`delaySeconds` 上限外溢出來的，schtasks 沒有那個上限（ADR §2.7）")
        # 語料自檢保留：那一筆真實事件的算術仍必須成立，否則上面引的量測失去出處。
        hit = datetime(2026, 8, 7, 0, 44, tzinfo=UTC).astimezone(_TAIPEI)
        window = (guard.parse_reset_at(_REAL_SESSION_LIMIT, hit) - hit).total_seconds()
        self.assertEqual(window, 16 * 60, "語料變了 ⇒ 這個常數的立案量測要重做")

    def test_the_audit_timestamp_cannot_be_overwritten_by_a_caller(self) -> None:
        """🔴 R79 補洞包端到端實測抓到的真缺陷（既有 `_resume_tick` 也中招）。

        `append_log(..., at=decision["at"])` 那個 kwarg 直接覆寫了記錄自己的時間戳
        ⇒ 痕跡上寫著一個**未來**的時刻（實測：事件發生在 21:24、記錄寫成 23:26）。
        「這件事何時發生」正是整條稽核痕跡唯一在回答的問題——讓「觸發了但失敗」與
        「根本沒觸發」分得開的那一格。把 `at`／`event` 移回 `**fields` 之前即紅。
        """
        log = Path(tempfile.mkdtemp()) / "trail.jsonl"
        before = datetime.now(UTC)
        planner.append_log(log, "rearmed", at="2099-01-01T00:00:00+08:00",
                           fire_at="2099-01-01T00:00:00+08:00")
        row = json.loads(log.read_text(encoding="utf-8").strip())
        self.assertEqual(row["event"], "rearmed", "呼叫端蓋掉了事件名")
        written = datetime.fromisoformat(row["at"])
        self.assertLessEqual(before - timedelta(seconds=2), written)
        self.assertLessEqual(written, datetime.now(UTC) + timedelta(seconds=2))
        self.assertEqual(row["fire_at"], "2099-01-01T00:00:00+08:00",
                         "非保留鍵仍須原樣寫進去（不得因為修這個缺陷而變成靜默丟棄）")

    def test_no_caller_passes_the_reserved_keys_any_more(self) -> None:
        """上一條擋住了後果，這一條擋住成因：呼叫端不得再寫 `at=`／`event=`。

        兩條都要有——只擋後果的話，下一個人仍會寫出讀起來像在設定時間戳、實際被
        默默忽略的呼叫；只擋成因的話，`append_log` 自己被改回去時沒有人會知道。

        🔴 判準走 AST 而不是整份原始碼的字串搜尋：後者只要註解或 docstring
        **合法地**提到那個字樣就假紅（`test_archive_defect_log` 有一條同名紀律在守
        這件事，Pkg-P12 已實際發生過並導致帳本改寫自己的缺陷描述）。
        """
        tree = ast.parse(_PLANNER.read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and getattr(n.func, "attr", getattr(n.func, "id", "")) == "append_log"]
        bad = [f"{n.lineno}:{kw.arg}=" for n in calls for kw in n.keywords
               if kw.arg in {"at", "event"}]
        self.assertEqual(bad, [], "呼叫端把保留鍵當 kwarg 傳給 append_log——那會被記錄"
                                  "自己的時間戳／事件名覆寫，讀起來像在設定、實際被靜默忽略")
        fire = sum(1 for n in calls for kw in n.keywords if kw.arg == "fire_at")
        self.assertEqual(fire, 2,
                         "兩個重排站點都要用 fire_at（是「下次何時響」，不是「現在幾點」）")

    def test_the_idle_threshold_outlives_a_whole_quota_window(self) -> None:
        """自我解除門檻必須大於一個完整額度視窗（5 小時）：等額度那段逐字稿本來就
        不會更新，門檻若短於視窗，哨兵會在最需要它的時候把自己拆掉。"""
        self.assertGreater(planner.SENTINEL_IDLE_SECONDS, 5 * 3600)


class SentinelWiringTest(unittest.TestCase):
    """接線：Action 叫得回哨兵、工作名不互相覆蓋、SessionStart 真的會按下去。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="sentinel-wire-"))

    def test_the_action_calls_the_sentinel_tick_not_the_resume_tick(self) -> None:
        """兩支 tick 的差別只有一件事：要不要花額度。掛錯就是每 15 分鐘燒一次探測。"""
        argument = planner.runner_action_argument(_A_PLAN, "T", planner.SENTINEL_TICK)
        self.assertIn("--sentinel-tick", argument)
        self.assertNotIn("--resume-tick", argument)
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'",
                                                   planner.SENTINEL_TICK)
        self.assertIn("--sentinel-tick", script)

    def test_the_default_tick_is_unchanged_for_the_existing_path(self) -> None:
        """控制組：既有續航路徑的預設不得因為多了一個參數而漂掉。"""
        self.assertIn("--resume-tick", planner.runner_action_argument(_A_PLAN, "T"))

    def test_the_task_name_carries_the_session_id(self) -> None:
        """🔴 哨兵是 per-session 的。共用一個工作名時，開第二個 session 會用 `-Force`
        靜默覆蓋掉第一個 session 還在等的那一支——而覆蓋不會有任何訊息。"""
        self.assertNotEqual(planner.sentinel_task_name("aaa"),
                            planner.sentinel_task_name("bbb"))
        for sid in ("aaa", "bbb"):
            self.assertIn(sid, planner.sentinel_task_name(sid))
        self.assertEqual(planner.sentinel_task_name("aaa", "MyOwnName"), "MyOwnName")

    def test_an_operator_interval_is_an_acceptable_reset_source(self) -> None:
        """哨兵的觸發時刻是**巡邏間隔**，不是任何 reset 時刻 ⇒ 它沒有在宣稱 reset，
        故不受「猜出來的 reset 不得武裝」那條禁令約束。但憑證那一條仍然管它。"""
        armed = {**RelayStateTest.GOOD, "kind": "sentinel", "reset_source": "operator",
                 "reset_at": ""}
        self.assertEqual(planner.relay_problems(armed), [])
        self.assertTrue(planner.relay_problems({**armed, "next_run_time": ""}),
                        "哨兵拿不到 NextRunTime 卻仍寫成 armed ⇒ 憑證閘對它失效")

    def test_the_guard_is_registered_on_both_events_that_the_sentinel_needs(self) -> None:
        """🔴 本包的重點不是工具、是**接電**。沒有這兩個註冊條目，哨兵就永遠只是一支
        「要人記得去按」的指令——而那正是 R77『機制蓋好沒接電』的第三次復發。

        🔴 R82／HELM-02 起是**兩個**事件，缺一即斷：SessionStart 清閂鎖（`claude -r`
        續接時能重新武裝）、PostToolUse 才是真正會註冊排程的那一個。此前只驗前者，
        而武裝已經搬到後者 ⇒ 只驗一個等於把接線的一半交給運氣。
        """
        for event in ("SessionStart", "PostToolUse"):
            commands = [argv for _, argv in _hook_invocations(event)]
            # 比對**完整路徑**而不是裸檔名：`tools/tests/test_context_budget_guard.py`
            # 也含後者，裸檔名判準會被一個不相干的字串滿足（本輪注入實測踩到這一格）。
            self.assertTrue(
                [c for c in commands if ".claude/hooks/context_budget_guard.py" in c],
                f"{event} 沒有掛上本守衛 ⇒ 哨兵那一段接線斷了：{commands}")

    def _sessionstart(self, root: Path, extra: dict[str, str] | None = None):
        env = _isolated_env(self.tmp)
        env["CLAUDE_PROJECT_DIR"] = str(root)
        env.update(extra or {})
        payload = json.dumps({"hook_event_name": "SessionStart", "source": "startup",
                              "transcript_path": str(self.tmp / "live.jsonl")})
        return subprocess.run(
            [sys.executable, str(_HOOK)], input=payload, env=env, capture_output=True,
            encoding="utf-8", errors="replace", timeout=180, check=False)

    def _fake_repo(self, marker: Path) -> Path:
        """一個假 repo 根，`tools/session_resume_planner.py` 換成只寫 argv 的替身。

        用替身而不是真 planner 是刻意的：真的跑下去會在**開發者的機器上**註冊一支
        schtasks，而測試不該有那種副作用。要驗的是接線（有沒有真的被叫起來、參數對不對），
        不是註冊本身——註冊由端到端手工實證負責。
        """
        root = Path(tempfile.mkdtemp(prefix="fake-repo-"))
        (root / "tools").mkdir()
        (root / "tools" / "session_resume_planner.py").write_text(
            "import json,sys,pathlib\n"
            f"pathlib.Path(r'{marker}').write_text(json.dumps(sys.argv[1:]),"
            " encoding='utf-8')\n",
            encoding="utf-8", newline="\n")
        return root

    def _posttooluse(self, root: Path, transcript: Path,
                     extra: dict[str, str] | None = None):
        """跑一次 PostToolUse（＝R82／HELM-02 之後**真正**會武裝的那個事件）。"""
        env = _isolated_env(self.tmp)
        env["CLAUDE_PROJECT_DIR"] = str(root)
        env.update(extra or {})
        payload = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Read",
                              "transcript_path": str(transcript)})
        return subprocess.run(
            [sys.executable, str(_HOOK)], input=payload, env=env, capture_output=True,
            encoding="utf-8", errors="replace", timeout=180, check=False)

    def test_sessionstart_no_longer_spawns_the_arming_run(self) -> None:
        """🔴 R82／HELM-02 的**成因面**：SessionStart 那一刻不得再註冊任何排程。

        這一條原本斷言相反的事（「SessionStart 真的把 planner 叫起來」）。它當時是對的，
        但那個形狀的代價是掌舵者當場截圖的東西：排程器裡三支哨兵，兩支屬於活了 5 秒與
        12 秒的 session。餵的逐字稿刻意是**夠格**的那一種——所以這條紅不了的唯一方式，
        是武裝真的不在這個事件上發生，而不是「這次剛好不夠格」。
        """
        if os.name != "nt":
            self.skipTest("[WINDOWS-NATIVE-ONLY] schtasks 武裝只在 Windows 成立（鐵律三：單平台判準不外推）")
        marker = self.tmp / "argv_ss.json"
        _transcript(self.tmp, "live.jsonl", 40, 900.0)
        proc = self._sessionstart(self._fake_repo(marker))
        self.assertEqual((proc.returncode, proc.stderr), (0, ""),
                         "SessionStart 這一支必須恆靜默、恆 exit 0")
        self.assertFalse(_wait_for(marker, 8.0),
                         "SessionStart 又在武裝了 ⇒ 每一支短命探針都會留一支排程")

    def test_an_earned_session_actually_spawns_the_arming_run(self) -> None:
        """🔴 端到端的**接線**證明：夠格的 session 在 PostToolUse 上真的把 planner 叫起來。

        只斷言 rc=0 會恆綠（fail-open 的守衛對任何輸入都回 0）。這裡改看**副作用**：
        替身被執行後留下的 argv。把 `arm_when_earned()` 從 `main()` 拿掉時這條會紅——
        而少了它，上一條（SessionStart 不武裝）可以靠「哪裡都不武裝」滿足，那是把
        續航整個關掉，且外觀與修好完全相同。
        """
        if os.name != "nt":
            self.skipTest("[WINDOWS-NATIVE-ONLY] 同上：本分支只在 Windows 有行為")
        marker = self.tmp / "argv_earned.json"
        live = _transcript(self.tmp, "earned.jsonl", 40, 900.0)
        proc = self._posttooluse(self._fake_repo(marker), live)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(_wait_for(marker, 30.0),
                        "夠格的 session 也沒被武裝 ⇒ 續航整條斷掉")
        argv = json.loads(marker.read_text(encoding="utf-8"))
        self.assertIn("--arm-sentinel", argv)
        self.assertIn("--transcript", argv)
        self.assertIn(str(live), argv)

    def test_a_short_lived_session_never_spawns(self) -> None:
        """本輪立案那六支的形狀（2 回合 / 12 秒）⇒ 端到端也不得留下任何排程。"""
        if os.name != "nt":
            self.skipTest("[WINDOWS-NATIVE-ONLY] 同上：本分支只在 Windows 有行為")
        marker = self.tmp / "argv_short.json"
        live = _transcript(self.tmp, "short.jsonl", 2, 12.0)
        self.assertEqual(self._posttooluse(self._fake_repo(marker), live).returncode, 0)
        self.assertFalse(_wait_for(marker, 8.0), "短命 session 仍然被武裝了")

    def test_the_off_switch_really_stops_it(self) -> None:
        """人的逃生口。與 context 阻斷那一個刻意分開：兩者關掉的是不同的東西。

        🔴 R82／HELM-02 把這一條從 SessionStart 移到 PostToolUse：留在原處的話它會被
        「反正這個事件已經不武裝了」白白滿足——鎖還在、鑑別力沒了，本 repo 最大宗的形態。
        """
        if os.name != "nt":
            self.skipTest("[WINDOWS-NATIVE-ONLY] 同上：本分支只在 Windows 有行為")
        marker = self.tmp / "argv_off.json"
        live = _transcript(self.tmp, "off.jsonl", 40, 900.0)
        proc = self._posttooluse(self._fake_repo(marker), live,
                                 {"AUTOSDD_SENTINEL_OFF": "1"})
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(_wait_for(marker, 8.0), "逃生口沒有真的擋住武裝")

    def test_a_missing_planner_is_fail_open_not_a_crash(self) -> None:
        """`.claude/settings.json` 記載過的 P0：hook 誤觸會把所有工具硬鎖死。
        武裝失敗最多是少一層保護，絕不可反過來變成故障源。"""
        empty = Path(tempfile.mkdtemp(prefix="no-planner-"))
        self.assertEqual(self._sessionstart(empty).returncode, 0)

    def test_arming_accepts_a_transcript_that_does_not_exist_yet(self) -> None:
        """🔴 SessionStart 那一刻逐字稿檔案往往還沒被建立。既有入口一律 fail-loud
        （定位不到 session 的任務書會綁錯 id），而哨兵這一個入口必須放行——否則
        「開場自動武裝」在**每一個全新 session** 上都會失敗，剛好等於沒有接電。

        判準看的是**分岔**：同一條不存在的路徑，武裝入口收得下、預設入口仍拒絕。
        """
        ghost = self.tmp / "not-created-yet.jsonl"
        common = [sys.executable, str(_PLANNER), "--transcript", str(ghost),
                  "--out", str(self.tmp / "p.md")]
        env = _isolated_env(self.tmp)
        plain = subprocess.run(common, env=env, capture_output=True, encoding="utf-8",
                               errors="replace", timeout=180, check=False)
        self.assertEqual(plain.returncode, 1, "既有入口不該因為本包而變寬")
        self.assertIn("找不到逐字稿", plain.stderr)
        # 這一跑在 Windows 上會**真的**註冊一支排程（本測試唯一的機器副作用）。
        # 用一個不會與任何真哨兵撞名的工作名，並無條件收掉——測試不得留下移動零件。
        task = "AutoSDD_Sentinel_UNITTEST_GHOST"
        self.addCleanup(planner._schtasks_remove, task)
        armed = subprocess.run([*common, "--arm-sentinel", "--task-name", task],
                               env=env, capture_output=True, encoding="utf-8",
                               errors="replace", timeout=180, check=False)
        self.assertNotIn("找不到逐字稿", armed.stderr,
                         "武裝入口仍被『逐字稿還不存在』擋下 ⇒ 全新 session 一律武裝不了")
        self.assertTrue((self.tmp / "p.md").is_file(), "任務書骨架沒被寫出來")


# ══════════════════════════════════════════════════════════════════════════
# R79 Auto Pilot：`--allow-resume` 預設翻成開，以及它必須付的代價
# ══════════════════════════════════════════════════════════════════════════
# 掌舵者逐字裁決：「現在開，但禁止 commit/push」。**兩件事必須綁在同一組鎖裡**——
# 只鎖前者會讓「開了但護欄沒接上」全程綠，而那正是本 repo 判過三次的
# 「機制蓋好沒接電」（R77 PKG-GUARD）。所以下面兩個 class 是一組：
#   ① 預設真的是開，且兩個關閉出口都真的關得掉；
#   ② 那一跑的 spawn **真的**帶著無人看管訊號（漏注入是靜默的——護欄不會出聲說
#      自己沒被掛上，被守的那一跑也不會知道自己沒被守）。
# hook 那一端讀同一個字面，由 `tools/tests/test_check_hooks_liveness.py` 自證。
_UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
_RESUME_OFF_ENV = "AUTOSDD_RESUME_OFF"


class AllowResumeDefaultTest(unittest.TestCase):
    """`--allow-resume` 的預設與它的兩個關閉出口。"""

    def _parse(self, argv: list[str], *, off: str | None) -> bool:
        # 預設是在 `build_parser()` 當下讀環境變數算出來的 ⇒ 必須先改環境再建 parser。
        before = os.environ.pop(_RESUME_OFF_ENV, None)
        if off is not None:
            os.environ[_RESUME_OFF_ENV] = off
        try:
            return bool(planner.build_parser().parse_args(argv).allow_resume)
        finally:
            os.environ.pop(_RESUME_OFF_ENV, None)
            if before is not None:
                os.environ[_RESUME_OFF_ENV] = before

    def test_default_is_on(self) -> None:
        self.assertTrue(
            self._parse([], off=None),
            "R79 拍板 Auto Pilot 預設開；關著的話哨兵等到額度回來也只會通知，"
            "而『通知了但沒人在』正是這條協定要消滅的狀態")

    def test_explicit_flag_still_turns_it_on(self) -> None:
        self.assertTrue(self._parse(["--allow-resume"], off=None),
                        "既有呼叫點（人手打的、文件抄的）不得因為改預設而失效")

    def test_the_negated_flag_turns_it_off(self) -> None:
        self.assertFalse(self._parse(["--no-allow-resume"], off=None),
                         "沒有關閉出口的預設＝不可逆的決定")

    def test_the_env_var_turns_it_off(self) -> None:
        """🔴 環境變數才是實務上有用的那個出口：哨兵由 SessionStart hook 武裝，
        沒有人會去改它的參數，但環境變數是模型改不到、人改得到的那一層。"""
        self.assertFalse(self._parse([], off="1"),
                         f"{_RESUME_OFF_ENV} 關不掉 ⇒ 排程／hook 路徑上沒有出口")

    def test_the_explicit_flag_beats_the_env_var(self) -> None:
        """顯式旗標壓過環境變數：那是 argparse 的既有語意，也是人當場的意圖。"""
        self.assertTrue(self._parse(["--allow-resume"], off="1"))


class ResumeSpawnCarriesTheUnattendedSignalTest(unittest.TestCase):
    """續跑那一跑的 spawn 必須帶 `AUTOSDD_UNATTENDED=1`（掌舵者開 Auto Pilot 的條件）。

    走 `subprocess.run` 的攔截而不是真的 spawn 一個 `claude`：這裡要證的是
    **注入有沒有發生**，那是本檔這一端的責任；「訊號送到之後 hook 會不會擋」是另一端
    的責任，由那一端自己的注入證明負責。兩端各證各的，中間靠共同的字面對上。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.calls: list[dict] = []

        class _Done:
            returncode, stdout, stderr = 0, "ok", ""

        def _fake_run(argv, **kwargs):
            self.calls.append({"argv": argv, **kwargs})
            return _Done()

        real = planner.subprocess.run
        planner.subprocess.run = _fake_run
        self.addCleanup(setattr, planner.subprocess, "run", real)

    def _run(self) -> dict:
        args = planner.build_parser().parse_args(["--probe-command", "claude"])
        state = {"plan_path": str(self.tmp / "p.md"), "session_id": "sid-1"}
        planner._run_resume(args, state, self.tmp / "log.jsonl")
        self.assertEqual(len(self.calls), 1, "續跑應該只 spawn 一次")
        return self.calls[0]

    def test_the_signal_is_injected(self) -> None:
        env = self._run().get("env") or {}
        self.assertEqual(
            env.get(_UNATTENDED_ENV), "1",
            "續跑那一跑沒有帶無人看管訊號 ⇒ PreToolUse 守衛在那一跑上整支靜默，"
            "而它靜默的樣子與『有在守』一模一樣")

    def test_the_rest_of_the_environment_survives(self) -> None:
        """只加一個鍵，不換掉整個環境：`PATH`／`APPDATA` 沒了那一跑根本起不來。"""
        env = self._run().get("env") or {}
        missing = [k for k in os.environ if k not in env]
        self.assertEqual(missing, [], f"spawn 環境掉了 {missing[:5]} 等鍵")

    def test_it_still_resumes_the_right_session(self) -> None:
        argv = self._run()["argv"]
        self.assertEqual(argv[:4], ["claude", "-p", "-r", "sid-1"],
                         f"續跑指令的形狀被改掉了：{argv[:4]}")

    def test_the_resumed_run_lands_in_the_repo_not_system32(self) -> None:
        """🔴 R80 P0。沒有這一格時，續跑那一跑的 cwd 繼承排程行程＝`C:\\Windows\\System32`，
        而 Claude Code 用 cwd 決定「本 session 允許的工作目錄」⇒ 那一跑**結構上做不了任何
        事**。實測逐字（今天 01:55 那一跑自己的回報）：`Read` 任務書 → 權限未授予；
        `Get-Content` 同一份 → 「本 session 允許的工作目錄只有 C:\\WINDOWS\\system32」。

        五段流程（巡邏→偵測→重排→探測→續跑）全部觸發成功、稽核痕跡齊備，最後一步空轉
        ——所以這一條斷言的是**能不能做事**，不是「有沒有被叫起來」。
        """
        self.assertEqual(
            self._run().get("cwd"), str(_REPO_ROOT),
            "續跑 spawn 沒有帶 cwd ⇒ 它會落在排程行程的 cwd（system32），"
            "而那一跑對 repo 的每一個檔都是「不在允許的工作目錄內」")

    def test_the_resumed_run_can_reach_the_plan_outside_the_repo(self) -> None:
        """任務書住 `%TEMP%`（刻意不進 repo），所以光有 cwo=repo 根還讀不到它。

        `--add-dir` 是實查 `claude --help` 得到的旗標（`Additional directories to allow
        tool access to`），不是憑印象。判準要求它指向**任務書所在的那個目錄**——傳別的
        目錄照樣讓那一跑讀不到自己該讀的東西，而失敗的樣子與「沒帶」一模一樣。
        """
        argv = self._run()["argv"]
        self.assertIn("--add-dir", argv, "續跑沒有把任務書所在目錄加進允許目錄")
        self.assertEqual(argv[argv.index("--add-dir") + 1], str(self.tmp),
                         f"--add-dir 指到了別的地方：{argv}")

    def test_the_variadic_add_dir_does_not_swallow_the_prompt(self) -> None:
        """🔴 R80 端到端實測踩到的真缺陷，不是理論風險。

        `--add-dir <directories...>` 的值是**變長的**：把它排在 prompt 前面時，它會把
        prompt 也吃進去當成一個目錄 ⇒ `claude` 認為這一跑根本沒有 prompt。實測逐字
        `Error: No deferred tool marker found in the resumed session. …Provide a prompt
        to continue the conversation.`（rc=1、stdout 全空）；把 prompt 移到前面同一條
        指令 rc=0。

        失效方式最惡劣的地方：**五段流程與稽核痕跡全都是綠的**——woken／probed／resumed
        三筆齊備、`quota_open=true`、排程也被正確收掉，只有那一跑什麼都沒做。所以這一條
        鎖的是 argv 的**順序**，而順序在既有的「有沒有帶這個旗標」判準下是隱形的。
        """
        argv = self._run()["argv"]
        idx = argv.index("--add-dir")
        prompt_at = [i for i, a in enumerate(argv) if "第 3 節" in a]
        self.assertTrue(prompt_at, f"argv 裡找不到 prompt：{argv}")
        self.assertLess(
            prompt_at[0], idx,
            "prompt 排在 --add-dir 後面 ⇒ 會被那個變長參數吃掉，那一跑會拿不到 prompt")
        self.assertEqual(
            len(argv) - idx, 2,
            f"--add-dir 後面必須**只有**一個目錄值，否則多出來的東西會被它吃掉：{argv}")

    def test_the_resumed_run_does_not_pop_a_console_window(self) -> None:
        """無人看管的那一跑不該在使用者桌面上開一個視窗（旗標語意見 guard.NO_WINDOW）。"""
        self.assertEqual(self._run().get("creationflags"), guard.NO_WINDOW)


# ────────────────── R80：無 console 父行程下的 spawn（類級機械物，不是逐站點補丁）
# 🔴 為何是**類級**而不是「把漏掉的兩站補上就好」：R79 治這件事時只改了排程 Action 的
# 載具（python.exe → pythonw.exe），而同一條路上還有三個 spawn 站點沒帶旗標——本 repo
# 已反覆判過「同一份知識住多個家、只鎖一個」的形態（R73 `Find-GitBash`、R79 的 3 站鎖 1
# 站）。所以這裡鎖的是**一整類檔案的一整類呼叫**：宣告集合內每一個 subprocess spawn 都
# 必須顯式帶 no-window 旗標，漏掉任何一站當場紅，不靠人記得。
#
# 集合語意＝「這支檔可能在**無 console 的父行程**下被執行」：
#   · `.claude/hooks/*.py`      由 Claude Code 起（實測其 hook 子行程會自帶 conhost）
#   · `tools/session_resume_planner.py`  由 schtasks 以 `pythonw.exe` 起（無 console）
# 在那個條件下 spawn 一個 console 子系統應用（`python.exe`／`powershell.exe`／
# `claude.exe`）時，Windows 必定新配置一個 console ＝跳到使用者臉上的視窗。
#
# 🔴 分母是**覆蓋率棘輪**（鐵律三的體例）：`_CONSOLE_FREE_FLOOR` 只准升。新增一支 hook
# 卻沒進掃描面時，掃描面會縮到下限以下而轉紅——「射程靜默縮小」是本 repo 記載過的
# 失效方式（`MIN_TESTS` 腐化 11 輪），不能只靠 glob 看起來會自己長大。
_SPAWN_FUNCS = frozenset({"run", "Popen", "call", "check_call", "check_output"})

#: 掃描面檔數下限。R82／HELM-02 上修：射程由「planner ＋ hooks ＋ 一支具名的
#: `quota_escalation`」擴成「planner ＋ hooks ＋ `tools/lib/` 全部 `quota_*.py`／
#: `sentinel_*.py`」。🔴 立案不是預防性的，是**實測漏掉了一支**：`tools/lib/quota_meter.py`
#: 的 `subprocess.run` 一直沒有 `creationflags`，而它對本鎖完全隱形——因為射程是一份
#: 手寫清單，而清單只列了當時想到的那一支。改成 glob 之後，同族新檔自動進來。
#: 現值＝本輪實測，只准上修（射程靜默縮小是本 repo 記載過的失效方式）。
#: R84／C3-A 上修 10→11：具名納入 `tools/lib/schedule_backend.py`（兩個 glob 都罩不到，
#: 理由見 `ConsoleFreeSpawnTest._sources`）。
_CONSOLE_FREE_FLOOR = 11

#: 🔴 合法例外的**名字**與**上限**。
#: 本 repo 判例：沒有上限的逃生口會變成預設關法——豁免標記一多，這支鎖就等於被關掉。
#: 用法：在 spawn 呼叫的**任一行**行尾寫 `# no-window-ok: <為什麼這支真的需要視窗>`；
#: **理由留空無效**（正規式要求至少一個非空白字元）——「有標記」不等於「有理由」，
#: 那是本檔另一條判準（`creationflags` 有設 ≠ 設對）在豁免這一側的同一個形狀。
#: 今天實測用掉 **0** 個。要調大這個上限請在缺陷帳本具名理由；方向是只准調小。
_NO_WINDOW_EXEMPTION_CAP = 2
_NO_WINDOW_EXEMPT_RE = re.compile(r"#\s*no-window-ok:\s*(\S.*)$")


def _spawn_calls(tree: ast.AST) -> list[ast.Call]:
    """`subprocess.<run|Popen|…>(...)` 的呼叫節點。"""
    found = []
    for node in ast.walk(tree):
        func = getattr(node, "func", None)
        if (isinstance(node, ast.Call) and isinstance(func, ast.Attribute)
                and func.attr in _SPAWN_FUNCS
                and isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
            found.append(node)
    return found


def _creationflags_text(call: ast.Call) -> str | None:
    """該呼叫的 `creationflags=` 原始表達式（沒帶回 `None`）。"""
    for keyword in call.keywords:
        if keyword.arg == "creationflags":
            return ast.unparse(keyword.value)
    return None


def _exemption_of(lines: list[str], call: ast.Call) -> str | None:
    """該 spawn 呼叫有沒有掛具名豁免；回理由字串（沒有／理由空白皆回 `None`）。

    掃的是**呼叫的整個行範圍**而不是只有第一行：`subprocess.run(` 常被斷成多行，
    只認第一行會逼人把標記擠到一個難讀的位置，而難用的逃生口會被繞過（改成整段
    不呼叫 subprocess 之類），那比留一個看得見的標記更糟。
    """
    for idx in range(call.lineno - 1, min(call.end_lineno or call.lineno, len(lines))):
        found = _NO_WINDOW_EXEMPT_RE.search(lines[idx])
        if found:
            return found.group(1).strip()
    return None


def no_window_exemptions(sources: dict[str, str]) -> list[str]:
    """所有已使用的具名豁免（`檔:行 理由`）。上限判準的分子——它必須是**量出來的**。"""
    used: list[str] = []
    for name, src in sorted(sources.items()):
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        used += [f"{name}:{call.lineno} {why}" for call in _spawn_calls(tree)
                 if (why := _exemption_of(lines, call))]
    return used


def no_window_problems(sources: dict[str, str]) -> list[str]:
    """宣告集合內每一個 spawn 站點都必須顯式帶 no-window 旗標。純函式（紅綠可注入）。

    判準刻意只認**字面出現 `NO_WINDOW`**（涵蓋 `guard.NO_WINDOW` 與
    `getattr(subprocess, "CREATE_NO_WINDOW", 0)` 兩種寫法），不去解析數值：
    數值解析要跟著 Windows 常數表跑，而這裡要問的只是「作者有沒有顯式表態」。
    解析失敗一律計為違規——掃不到的檔靜默放行，正是本 repo 通篇在防的 fail-open。
    """
    problems: list[str] = []
    for name, src in sorted(sources.items()):
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            problems.append(f"{name}：AST 解析失敗（{exc}）——掃不到的檔不得靜默放行")
            continue
        lines = src.splitlines()
        for call in _spawn_calls(tree):
            if _exemption_of(lines, call):
                continue  # 具名豁免（有上限，見 `_NO_WINDOW_EXEMPTION_CAP`）
            text = _creationflags_text(call)
            where = f"{name}:{call.lineno}"
            if text is None:
                problems.append(
                    f"{where}：subprocess spawn 沒有 `creationflags=`。本檔可能在無 console"
                    " 的父行程下執行 ⇒ console 子行程會替使用者開一個視窗。"
                    "修法：`creationflags=guard.NO_WINDOW`（受零相依契約的 hook 寫"
                    ' `getattr(subprocess, "CREATE_NO_WINDOW", 0)`）')
            elif "NO_WINDOW" not in text:
                problems.append(
                    f"{where}：`creationflags={text}` 不含任何 no-window 旗標")
    return problems


def detached_conflict_problems(sources: dict[str, str]) -> list[str]:
    """全庫規則：`DETACHED_PROCESS` 不得與 `CREATE_NO_WINDOW` 同時出現在一個 creationflags。

    🔴 **R80 訂正本條的理由**（原文逐字宣稱「`DETACHED_PROCESS` 會把 `CREATE_NO_WINDOW`
    抵銷掉」，那句話同輪已被重量證偽，故不複述它——本 repo 判過「訂正註記逐字引述假話
    ＝製造新假話」，而這一段假話原本就住在**未來工程師唯一會讀到的那段文字**裡：紅燈訊息）。

    真正成立的理由是**載具效應，不是旗標語意**。重量矩陣（pythonw 當無 console 父行程、
    子行程自報 `GetConsoleWindow()`；`0`＝沒有 console）：
      · **真直譯器**（base `python.exe`）那一列，`DET|CNW` 是 **0** ⇒ 旗標本身沒有互斥。
      · 本 repo 的 venv 由 **uv** 建立（`pyvenv.cfg` 有 `uv = 0.8.22`），其 `python.exe`
        是 **trampoline**（274,712 bytes vs 真直譯器 103,192 bytes）：它 re-spawn 真的
        直譯器，而**不把 creationflags 轉傳下去** ⇒ 穿過它時 `DET|CNW` 才翻成「可見」。
      · `CNW` 與 `NEWGRP|CNW` 是**唯二在四種載具上全部為 0** 的組合。
    ⇒ 本規則守的是「在**本 repo 的載具上**這個組合實測會彈視窗」，不是「這兩個旗標語意
    互斥」。要脫離父行程請用 `CREATE_NEW_PROCESS_GROUP`。

    射程誠實劃界：上述重現依賴「venv 由 uv 建立」。走 `python -m venv` 回退路徑的 venv
    是否同樣翻面，**未驗**——所以這條是本 repo 的載具規則，不得寫成平台常數。
    """
    problems: list[str] = []
    for name, src in sorted(sources.items()):
        if "DETACHED_PROCESS" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for call in _spawn_calls(tree):
            text = _creationflags_text(call) or ""
            if "DETACHED_PROCESS" in text and "CREATE_NO_WINDOW" in text:
                problems.append(
                    f"{name}:{call.lineno}：`creationflags={text}` 同時帶 DETACHED_PROCESS"
                    " 與 CREATE_NO_WINDOW——在**本 repo 的載具上**實測會彈視窗（uv 建的"
                    " venv `python.exe` 是 trampoline，不轉傳 creationflags；這是載具效應，"
                    "不是旗標語意——真直譯器那一列 `DET|CNW` 是 0）。`CNW` 與 `NEWGRP|CNW`"
                    " 是唯二四載具全 0 的組合，要脫離父行程請改用 CREATE_NEW_PROCESS_GROUP")
    return problems


class ConsoleFreeSpawnTest(unittest.TestCase):
    """宣告集合內每一個 spawn 都帶 no-window 旗標 ＋ 全庫禁 `DETACHED|CNW`。"""

    @staticmethod
    def _sources() -> dict[str, str]:
        """掃描面＝所有**可能被無 console 的父行程叫到**的檔。

        🔴 R82／HELM-02 把 `tools/lib/` 那一半由手寫清單換成 glob。舊寫法只具名了
        `quota_escalation.py`（R81 新增 spawn 站點的那一支），於是同一層的
        `quota_meter.py` 帶著一個**沒有 `creationflags` 的 `subprocess.run`** 一直對本鎖
        隱形——本鎖照跑、照綠。這正是本類 docstring 自己寫著要防的事，只是缺口不在
        「有沒有掃」而在「掃誰是誰決定的」：手寫清單的分母由記憶決定，glob 的不會。
        射程限定 `quota_*`／`sentinel_*` 兩族而不是整個 `tools/lib`：那一層還有純資料與
        純判準模組，把它們全拉進來只會製造要逐一辯護的假紅（本 repo 判過那種鎖活不過一輪）。
        """
        # 🔴 R84／C3-A：`schedule_backend.py` **具名**加入。它不叫 `quota_*`／`sentinel_*`
        # 所以上面兩個 glob 一條都罩不到它，而它正是哨兵路徑上僅存的兩個裸 spawn 的家
        # （`_run()` 每 tick 跑 schtasks 查詢／註冊、`_defer()` 起延後的 `/bin/sh`）——
        # 掃描面是 glob 決定的那一刻起，這支就對本鎖隱形，與 R82 漏掉 `quota_meter.py`
        # 逐字同構。刻意具名而不是再放寬 glob：放寬會把同層純資料模組一起拉進來，
        # 製造要逐一辯護的假紅（本 repo 判過那種鎖活不過一輪）。
        paths = {
            "tools/session_resume_planner.py": _PLANNER,
            "tools/lib/schedule_backend.py": _REPO_ROOT / "tools" / "lib" / "schedule_backend.py",
        }
        lib = _REPO_ROOT / "tools" / "lib"
        for pattern in ("quota_*.py", "sentinel_*.py"):
            for mod in sorted(lib.glob(pattern)):
                paths[f"tools/lib/{mod.name}"] = mod
        for hook in sorted((_REPO_ROOT / ".claude" / "hooks").glob("*.py")):
            paths[f".claude/hooks/{hook.name}"] = hook
        return {rel: path.read_text(encoding="utf-8") for rel, path in paths.items()}

    @staticmethod
    def _live_python_sources() -> dict[str, str]:
        """全庫規則的掃描面：活的 Python 樹（不含凍結版、快取、venv）。

        以**文字預篩**（`DETACHED_PROCESS` 不在檔內就跳過）換掉全樹 AST——那條規則要抓的
        東西必然帶這個字面，預篩不會漏，而全樹 parse 會讓這支鎖慢到有人想關掉它。
        """
        skip = {"__pycache__", ".venv", "venv", "node_modules", ".git",
                ".pytest_cache", ".ruff_cache", ".mypy_cache"}
        out: dict[str, str] = {}
        for tree in ("tools", ".claude", "AutoClaude/autoclaude", "AutoClaude/tools"):
            base = _REPO_ROOT / tree
            if not base.is_dir():
                continue
            for path in base.rglob("*.py"):
                if skip & set(path.relative_to(base).parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "DETACHED_PROCESS" in text:
                    out[path.relative_to(_REPO_ROOT).as_posix()] = text
        return out

    def test_the_scan_surface_has_not_silently_shrunk(self) -> None:
        """分母棘輪。新增一支 hook 而沒進掃描面 ⇒ 它的 spawn 站點對本鎖隱形。"""
        sources = self._sources()
        self.assertGreaterEqual(
            len(sources), _CONSOLE_FREE_FLOOR,
            f"掃描面只有 {len(sources)} 支 < 下限 {_CONSOLE_FREE_FLOOR}（射程疑似縮小）："
            f"{sorted(sources)}")
        self.assertIn("tools/session_resume_planner.py", sources)
        self.assertIn(".claude/hooks/context_budget_guard.py", sources)
        # 🔴 R82／HELM-02：這一支是本輪實測漏掉的那一個。具名斷言而不是只靠 glob——
        # 有人把 glob 改窄時，「射程縮小」必須指名道姓地紅，而不是只讓總數少一。
        self.assertIn("tools/lib/quota_meter.py", sources)

    def test_the_escape_hatch_budget_is_not_blown(self) -> None:
        """具名豁免有上限。沒有上限的逃生口會變成預設關法（本 repo 判例）。"""
        used = no_window_exemptions(self._sources())
        self.assertLessEqual(
            len(used), _NO_WINDOW_EXEMPTION_CAP,
            f"具名豁免用掉 {len(used)} 個 > 上限 {_NO_WINDOW_EXEMPTION_CAP}：{used}")

    def test_an_exemption_needs_an_actual_reason(self) -> None:
        """注入自證⑤：豁免標記**理由留空無效**（「有標記」≠「有理由」）。"""
        bare = "import subprocess\nsubprocess.run(['a'])  # no-window-ok:\n"
        self.assertTrue(no_window_problems({"x.py": bare}))
        good = "import subprocess\nsubprocess.run(['a'])  # no-window-ok: 要給人看的 TUI\n"
        self.assertEqual(no_window_problems({"x.py": good}), [])
        self.assertEqual(len(no_window_exemptions({"x.py": good})), 1)

    def test_the_duplicated_no_window_expression_still_equals_the_ssot(self) -> None:
        """`NO_WINDOW` 被複製了兩份（import 會成環，見各檔註解）⇒ 相等鎖守著不漂開。

        🔴 為什麼是**值**相等而不是文字比對：兩份的意義是「同一組 Windows 旗標」，
        而那件事只有值說得準；文字比對會在有人換個等價寫法時給出假紅。

        🔴 **`sentinel_lifecycle` 已於 R83／PD 由兩份名冊移除**（不是鎖被放寬）：該檔那兩個
        常數的唯一消費者（`_powershell`）在 A-01 收斂時整支刪掉 ⇒ 常數成了零消費者的死碼，
        本輪連同它們一起刪除（該檔留有墓碑段記載沿革與判準）。名冊是**複製品清單**，複製品
        不存在了就必須離開清單——留著會 `AttributeError`，而那是假紅不是牙。仍在守的兩端
        （`quota_meter`／`console_spawn_watch`）逐一具名，射程縮小時會指名道姓地紅。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import console_spawn_watch  # noqa: PLC0415 — probe 不在 import 面，隨用隨載
        # 🔴 R84／C3-P2 新增第三份：`schedule_backend`（哨兵路徑上僅存的兩個裸 spawn，
        # 見該檔常數上方）。它同樣不得 import guard——依賴方向是 tools → .claude/hooks，
        # 而本檔正是被 hook 那一側 import 的一方，反向 import 會成環。
        for name, mod in (("quota_meter", quota_meter),
                          ("console_spawn_watch", console_spawn_watch),
                          ("schedule_backend", sb)):
            self.assertEqual(
                mod.NO_WINDOW, guard.NO_WINDOW,
                f"{name}.NO_WINDOW 與 guard.NO_WINDOW 漂開了——複製品的存在條件就是"
                "「有東西守著它們相等」，這一條紅就代表那個條件不再成立")
        # 🔴 同一族的第二個複製面：送進 powershell.exe(5.1) 的 UTF-8 前置行。它守的是
        # 「取證憑證不會降解成 `?`」——而降解過的憑證仍然非空，取證閘照樣判綠（假綠）。
        self.assertEqual(console_spawn_watch.PS_UTF8_PRELUDE, guard.PS_UTF8_PRELUDE,
                         "console_spawn_watch.PS_UTF8_PRELUDE 與 guard 漂開了")
        # 🔴 反向釘：死碼刪掉之後，**不准有人把它加回來而不進名冊**（那正是這道鎖的分母
        # 靜默縮小的方式——複本在、沒人守它相等）。加回來就必須連同名冊一起加。
        for gone in ("NO_WINDOW", "PS_UTF8_PRELUDE"):
            self.assertFalse(
                hasattr(sentinel_lifecycle, gone),
                f"sentinel_lifecycle.{gone} 又出現了，卻沒有進上面的名冊 ⇒ 一份無人守的複本")

    def test_the_planner_actually_prepends_the_utf8_prelude(self) -> None:
        """接線鎖：常數存在 ≠ 有人用它（本 repo 判過三次的「機制蓋好沒接電」）。

        判準綁在 `run_powershell` 這個**唯一**把腳本寫進磁碟的地方——繞過它另寫一個
        writer 才是真正該紅的事，而那正好也會讓這一條紅。
        """
        body = ast.unparse(next(
            n for n in ast.walk(ast.parse(_PLANNER.read_text(encoding="utf-8")))
            if isinstance(n, ast.FunctionDef) and n.name == "run_powershell"))
        self.assertIn("PS_UTF8_PRELUDE", body,
                      "planner 沒有把 UTF-8 前置行加進送給 powershell.exe 的腳本 ⇒ "
                      "`NextRunTime` 裡的『下午』會降解成 `?`，而降解過的憑證仍然非空 ⇒ "
                      "取證閘照樣判綠（假綠）")

    def test_the_prelude_really_stops_the_evidence_from_degrading(self) -> None:
        """🔴 行為鎖（非字面）：同一段會印中文的 PS 輸出，沒有前置行時必須降解、有時必須完整。

        兩個方向都驗是刻意的：只驗「有前置行時是好的」，在前置行變成 no-op 時照樣綠。
        立案是實測值——哨兵稽核 jsonl 逐字記著 `"next_run_time": "2026/8/9 ?? 07:14:19"`。
        """
        if os.name != "nt":
            self.skipTest("[WINDOWS-NATIVE-ONLY] powershell.exe 5.1 的主控台 codepage 行為"
                          "只在 Windows 成立（鐵律三：單平台判準不外推）")
        body = ("$d = Get-Date -Date '2026-08-09 19:14:19'\n"
                "[pscustomobject]@{ NextRunTime = $d } | Format-List NextRunTime\n")
        outs = {}
        for label, script in (("bare", body), ("fixed", guard.PS_UTF8_PRELUDE + body)):
            holder = Path(tempfile.mkdtemp(prefix=f"psenc-{label}-")) / "run.ps1"
            holder.write_text(script, encoding="utf-8-sig", newline="\r\n")
            outs[label] = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(holder)],
                capture_output=True, encoding="utf-8", errors="replace", timeout=90,
                check=False, creationflags=guard.NO_WINDOW).stdout
        if "�" not in outs["bare"]:
            self.skipTest("本機 codepage 已是 UTF-8（或 PS 的算繪不含非 ASCII）⇒ "
                          "缺陷在這台機器上重現不了；不得把『重現不了』讀成『已修好』")
        self.assertNotIn("�", outs["fixed"],
                         "加了 UTF-8 前置行仍然降解 ⇒ 這個修法對本機無效")

    def test_autoclaude_shell_true_does_not_pop_a_cmd_window(self) -> None:
        """🔴 **實測歸因**出來的 repo 側 `cmd.exe` 來源，釘成行為鎖。

        本輪 17 分鐘量測窗（`tools/probe/console_spawn_watch.py`）抓到 3 筆 `cmd.exe`，
        父行程一律是 `python -m pytest tests/ -q`，子命令列是
        `cmd.exe /c "pytest tests -k …"`／`cmd.exe /c "python -c …"`——那正是
        `execution/evaluator.py` 與 `mutation_applier/_conditional.py` 的 `shell=True`
        在 Windows 上的形狀（`shell=True` ⇒ `cmd.exe /c`）。父行程沒有 console 時
        （schtasks 的 pythonw、GUI 啟動器），**每一個 playbook 步驟就是一個黑框**。

        判準是**行為**不是字面：直接載入 `platform_caps.py`（純 stdlib，可獨立載入）、
        模擬兩個平台各呼叫一次。字面判準會被一個等價改寫繞過，而這一格的失效方向是
        「黑框回來了」——而黑框回來時沒有任何測試會轉紅，只有使用者看得到。
        """
        import importlib.util  # noqa: PLC0415 — 只有這一條測試需要
        path = (_REPO_ROOT / "AutoClaude" / "autoclaude" / "utils" / "platform_caps.py")
        spec = importlib.util.spec_from_file_location("_probe_platform_caps", path)
        caps = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(caps)
        with unittest.mock.patch.object(caps.sys, "platform", "win32"):
            win = caps.new_session_kwargs()
        with unittest.mock.patch.object(caps.sys, "platform", "linux"):
            posix = caps.new_session_kwargs()
        self.assertIn("creationflags", win,
                      "Windows 分支沒有帶 creationflags ⇒ shell=True 的 cmd.exe 會在無"
                      " console 的父行程下彈視窗（本輪實測到 3 筆）")
        self.assertEqual(win["creationflags"],
                         getattr(subprocess, "CREATE_NO_WINDOW", 0) or win["creationflags"])
        # 🔴 反向：POSIX 那一格**不得**出現 creationflags（那個 kwarg 在 POSIX 的
        # Popen 上會 TypeError ⇒ 整個 evaluator 在 mac/Linux 上炸掉，鐵律三判例）。
        self.assertNotIn("creationflags", posix)
        self.assertIn("start_new_session", posix)

    def test_every_declared_spawn_site_carries_the_flag(self) -> None:
        """現況控制組。R80 修前這一條會列出三站：planner 的 probe_quota／續跑、
        以及 `sdd_hook_router` 的轉交（三者都由無 console 的父行程起）。"""
        self.assertEqual(no_window_problems(self._sources()), [])

    def test_a_missing_flag_is_actually_caught(self) -> None:
        """注入自證①：拿掉旗標必須紅。少了這一條，上一條在判準被改壞時照樣綠。"""
        self.assertTrue(no_window_problems(
            {"x.py": "import subprocess\nsubprocess.run(['a'], check=False)\n"}))

    def test_a_flag_that_is_not_a_no_window_flag_is_caught(self) -> None:
        """注入自證②：帶了 `creationflags=` 但內容無關 ⇒ 仍然紅（「有設」≠「設對」）。"""
        self.assertTrue(no_window_problems(
            {"x.py": "import subprocess\nsubprocess.run(['a'], "
                     "creationflags=subprocess.HIGH_PRIORITY_CLASS)\n"}))

    def test_an_unparsable_file_is_not_silently_skipped(self) -> None:
        """注入自證③：解析失敗算違規（fail-closed），不是「掃不到就算過」。"""
        self.assertTrue(no_window_problems({"x.py": "def broken(:\n"}))

    def test_a_correct_spawn_is_accepted(self) -> None:
        """反向控制組：本鎖要人改成的那個樣子必須綠，否則它會逼人繞過。"""
        self.assertEqual(no_window_problems(
            {"x.py": "import subprocess\nsubprocess.run(['a'], check=False,\n"
                     "               creationflags=guard.NO_WINDOW)\n"}), [])

    def test_no_live_file_cancels_no_window_with_detached(self) -> None:
        """全庫規則的現況控制組（R80 修前 `context_budget_guard.py` 會在這裡紅）。"""
        self.assertEqual(detached_conflict_problems(self._live_python_sources()), [])

    def test_the_detached_conflict_is_actually_caught(self) -> None:
        """注入自證④：把「在本 repo 載具上實測會彈視窗」的那個組合寫回去，必須紅。

        （措辭已隨 `detached_conflict_problems` 的理由一起訂正：被證偽的是「旗標語意
        互斥」那個說法，不是這個組合會彈視窗這件事——後者仍是實測值。）"""
        self.assertTrue(detached_conflict_problems(
            {"x.py": "import subprocess\nsubprocess.Popen(['a'], creationflags=("
                     'getattr(subprocess, "DETACHED_PROCESS", 0)\n'
                     '    | getattr(subprocess, "CREATE_NO_WINDOW", 0)))\n'}))

    def test_the_recommended_replacement_is_accepted(self) -> None:
        """`CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW` 必須放行（實測 hwnd=0）。"""
        self.assertEqual(detached_conflict_problems(
            {"x.py": "import subprocess\nsubprocess.Popen(['a'], creationflags=("
                     'getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)\n'
                     '    | getattr(subprocess, "CREATE_NO_WINDOW", 0)))\n'}), [])


#: 行為鎖的內層腳本。由 `pythonw.exe` 執行 ⇒ 本行程**沒有 console**，這正是 production
#: 的條件（schtasks 的 Action 載具、以及 Claude Code 起 hook 的那一層）。
#: 子行程**自報** `GetConsoleWindow()`。
#: 🔴 刻意**不用 conhost 行程計數當判準**：那個判準在沒有桌面的環境（雲端／CI）上恆為
#: 「沒有視窗」＝假綠，而假綠的方向剛好是「看起來已經修好了」。
_BEHAVIOUR_PROBE = '''import ctypes, json, subprocess, sys
from pathlib import Path
CHILD = "import ctypes,sys;sys.stdout.write(str(ctypes.windll.kernel32.GetConsoleWindow()))"
out, combos = Path(sys.argv[1]), json.loads(sys.argv[2])
# argv[3]＝被測載具（省略時用 console 子系統的 python.exe——那是唯一「不帶旗標會真的
# 開視窗」的載具，也就是唯一驗得出旗標效果的被測對象）。
exe = sys.argv[3] if len(sys.argv) > 3 else str(Path(sys.executable).with_name("python.exe"))
res = {"parent_has_no_console": ctypes.windll.kernel32.GetConsoleWindow() == 0, "cases": {}}
for name, flags in combos.items():
    p = subprocess.run([exe, "-c", CHILD], capture_output=True, encoding="utf-8",
                       errors="replace", timeout=120, check=False, creationflags=flags)
    res["cases"][name] = {"hwnd": (p.stdout or "").strip(), "rc": p.returncode,
                          "stderr": (p.stderr or "")[:200]}
out.write_text(json.dumps(res), encoding="utf-8")
'''


@unittest.skipUnless(
    os.name == "nt",
    "[WINDOWS-NATIVE-ONLY] console 配置是 Windows 專屬概念（POSIX 上 creationflags 恆為 0，"
    "本鎖的判準在那裡沒有標的）——鐵律三：單平台判準不外推")
class NoWindowBehaviourTest(unittest.TestCase):
    """🔴 **行為**鎖，不是靜態掃描：真的從無 console 父行程 spawn，看子行程有沒有 console。

    為何靜態掃描不夠：`ConsoleFreeSpawnTest` 只證「作者寫了那個旗標」，證不到「那個旗標
    真的有效」。而 R80 的缺陷本體恰恰是**旗標有寫但被抵銷掉**（`DETACHED|CNW`）——那個
    形態對任何「有沒有寫」的判準都是綠的。所以這一層量的是結果，不是意圖。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="nowin-behaviour-"))
        self.pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not self.pythonw.is_file():
            self.skipTest(f"[TOOL-ABSENCE] 這個直譯器旁沒有 pythonw.exe（{self.pythonw}）"
                          "——無 console 父行程這個實驗條件建不起來，跳過比假綠正確")

    def _measure(self, combos: dict[str, int]) -> dict:
        out = self.tmp / "r.json"
        script = self.tmp / "probe.py"
        script.write_text(_BEHAVIOUR_PROBE, encoding="utf-8", newline="\n")
        proc = subprocess.run(
            [str(self.pythonw), str(script), str(out), json.dumps(combos)],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=300, check=False, creationflags=guard.NO_WINDOW)
        self.assertTrue(out.is_file(),
                        f"內層探針沒有產出結果（rc={proc.returncode}）：{proc.stderr[:300]}")
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(data["parent_has_no_console"],
                        "父行程竟然有 console ⇒ 整個實驗條件不成立，這一組數字沒有意義")
        return data["cases"]

    def test_the_shipped_flag_really_suppresses_the_console(self) -> None:
        """本體：`guard.NO_WINDOW` 之下子行程 `GetConsoleWindow()` 必須是 0。

        控制組（不帶旗標）必須**有** console，否則本載具量不到這個缺陷，上一條斷言
        就沒有鑑別力——一個永遠回 0 的壞載具看起來與修好一模一樣。

        🔴 **子行程刻意用 `python.exe` 而不是 `pythonw.exe`**：後者是 GUI 子系統，在
        六種旗標下**全部**都是 0（見 `guard.NO_WINDOW` 的矩陣第三、四列）⇒ 拿它當被測
        對象，控制組也會是 0，整條測試恆綠。要驗「旗標那一層」就必須挑一個沒有旗標
        時**真的會開視窗**的載具。
        """
        cases = self._measure({"shipped": guard.NO_WINDOW, "none": 0})
        self.assertEqual(
            cases["shipped"]["hwnd"], "0",
            f"帶了 guard.NO_WINDOW 的子行程仍有 console（{cases['shipped']}）⇒ 會彈視窗")
        self.assertNotEqual(
            cases["none"]["hwnd"], "0",
            f"控制組（不帶旗標）竟然也沒有 console：{cases['none']}——那表示本載具"
            "量不到這個缺陷，上一條斷言沒有鑑別力")

    def test_the_quiet_carrier_needs_no_flags_at_all(self) -> None:
        """第二層（載具）**獨立於**第一層（旗標）成立：`pythonw.exe` 不帶任何旗標也是 0。

        兩層各自成立才是本修復的設計：任一層被未來的人改掉，另一層仍撐得住。
        🔴 這一條同時是 R80 訂正的憑據——我第一版把「`DETACHED_PROCESS` 抵銷
        `CREATE_NO_WINDOW`」寫成旗標語意，實際上翻面的是**載具**（uv trampoline），
        真直譯器那一列 `DET|CNW` 是 0。
        """
        quiet = Path(guard.quiet_python())
        if quiet.name.lower() != "pythonw.exe":
            self.skipTest(f"[TOOL-ABSENCE] 這個直譯器旁沒有 pythonw.exe（解析到 {quiet}）")
        out = self.tmp / "q.json"
        script = self.tmp / "probe_q.py"
        script.write_text(_BEHAVIOUR_PROBE, encoding="utf-8", newline="\n")
        proc = subprocess.run(
            [str(self.pythonw), str(script), str(out), json.dumps({"bare": 0}),
             str(quiet)],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=300, check=False, creationflags=guard.NO_WINDOW)
        self.assertTrue(out.is_file(), f"探針沒有產出（rc={proc.returncode}）{proc.stderr[:200]}")
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["cases"]["bare"]["hwnd"], "0",
                         f"安靜載具在零旗標下仍有 console：{data['cases']['bare']}")

    def test_suppressing_the_window_does_not_cost_observability(self) -> None:
        """抑制視窗不得以「拿不到 rc／stderr」為代價——否則排程那一跑會變成黑箱。"""
        cases = self._measure({"shipped": guard.NO_WINDOW})
        self.assertEqual(cases["shipped"]["rc"], 0)


class UnhandledLimitDetectionTest(unittest.TestCase):
    """🔴 R80 P0：哨兵整晚失明那一格的回歸鎖（事故見 `unhandled_limit_event` 上方 WHY）。

    被守的性質有三條，每一條都對應一個**已實際發生過**的失效：
      ① 「已處理」必須是**證據**（事後真的有成功 API 回應），不是推論。舊判準的推論
         逐字是「我跑得動武裝指令 ⇒ 額度是通的」，而武裝是零 API 呼叫的本機 subprocess
         ⇒ 那句話恆真、與額度無關。實證：撞線後 2 分鐘就被標成已解決。
      ② 偵測面必須含 subagent（扇出模式下撞線主要打在那裡）。
      ③ 必須看**所有**未處理事件，不是只看最後一筆——本次事故裡最後一筆是 `quota_spend`，
         把更早、仍未解決的 `quota_session` 整個蓋掉。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unhandled-"))
        self.main = self.tmp / "sid.jsonl"

    @staticmethod
    def _limit(ts: str, text: str) -> str:
        return json.dumps({"type": "assistant", "timestamp": ts,
                           "message": {"model": guard.SYNTHETIC_MODEL,
                                       "content": [{"text": text}]}})

    @staticmethod
    def _ok(ts: str) -> str:
        """一則成功回應＝真 model ＋ 有 usage（伺服器真的計費回來的證據）。"""
        return json.dumps({"type": "assistant", "timestamp": ts,
                           "message": {"model": "claude-opus-5",
                                       "usage": {"input_tokens": 5}}})

    def _write(self, path: Path, lines: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    def test_an_event_with_no_later_success_is_unhandled(self) -> None:
        """基本方向：撞線之後再也沒有成功回應 ⇒ 未處理。"""
        self._write(self.main, [self._ok("2026-08-07T18:00:00Z"),
                                self._limit("2026-08-07T18:36:53Z", _REAL_SESSION_LIMIT)])
        event = guard.unhandled_limit_event(self.main)
        self.assertIsNotNone(event, "撞線後零成功回應，卻判成已處理")
        self.assertEqual(event["kind"], guard.LIMIT_SESSION)

    def test_a_later_success_marks_it_handled(self) -> None:
        """反向：撞線之後有成功回應 ⇒ 已解決，不得再叫醒任何人。
        這一條就是 0% 假陽性的來源（歷史 257 筆事件全數落在這一格）。"""
        self._write(self.main, [self._limit("2026-08-07T18:36:53Z", _REAL_SESSION_LIMIT),
                                self._ok("2026-08-07T19:00:00Z")])
        self.assertIsNone(guard.unhandled_limit_event(self.main))

    def test_a_subagent_transcript_is_in_scope(self) -> None:
        """②：撞線只打在 subagent 身上時也要看得見。

        `latest_limit_event`（舊來源）只吃主逐字稿一支檔 ⇒ 這一條在它身上必然失敗。
        """
        self._write(self.main, [self._ok("2026-08-07T18:00:00Z")])
        self._write(self.main.with_suffix("") / "subagents" / "workflows" / "wf_1"
                    / "agent-x.jsonl",
                    [self._limit("2026-08-07T18:36:53Z", _REAL_SESSION_LIMIT)])
        event = guard.unhandled_limit_event(self.main)
        self.assertIsNotNone(event, "subagent 逐字稿裡的撞線沒被看見（扇出模式全盲）")
        self.assertEqual(event["source"], "agent-x.jsonl")
        self.assertIsNone(guard.latest_limit_event(self.main),
                          "控制組：舊來源理應看不到它——看得到就表示本測試沒有鑑別力")

    def test_a_spend_event_does_not_mask_an_earlier_session_event(self) -> None:
        """③：本次事故的逐字重建。主逐字稿最後一筆是月度上限，而更早那筆 session
        額度仍未解決；只看最後一筆會回 spend ⇒ 走 escalate，而真正該做的是等 6:50am。"""
        self._write(self.main, [
            self._ok("2026-08-07T18:30:00Z"),
            self._limit("2026-08-07T18:36:53Z", _REAL_SESSION_LIMIT),
            self._limit("2026-08-07T18:40:00Z", _REAL_SPEND_LIMIT)])
        event = guard.unhandled_limit_event(self.main)
        self.assertEqual(event["kind"], guard.LIMIT_SESSION,
                         "取到的是最後一筆（spend）而不是最早那筆未處理的 session 額度")
        self.assertEqual(guard.latest_limit_event(self.main)["kind"], guard.LIMIT_SPEND,
                         "控制組：舊來源確實會被 spend 蓋掉（這就是事故本體）")

    def test_success_evidence_requires_real_usage_not_just_a_record(self) -> None:
        """①的鑑別力：合成錯誤訊息本身**不算**成功回應，否則撞線會自己證明自己已解決。"""
        self._write(self.main, [
            self._limit("2026-08-07T18:36:53Z", _REAL_SESSION_LIMIT),
            self._limit("2026-08-07T18:40:00Z", _REAL_SESSION_LIMIT)])
        self.assertEqual(guard.latest_success_at([self.main]), "",
                         "把合成記錄當成功證據 ⇒ 每次撞線都會立刻自我標記為已解決")
        self.assertIsNotNone(guard.unhandled_limit_event(self.main))

    def test_liveness_looks_at_subagent_activity_too(self) -> None:
        """存活判準：扇出時主逐字稿可能很久沒被寫，只看它會把狂跑中的 session 誤判成
        閒置，而閒置到門檻就會**自我解除**（哨兵在最忙的時候把自己拆掉）。"""
        self._write(self.main, [self._ok("2026-08-07T18:00:00Z")])
        sub = self.main.with_suffix("") / "subagents" / "agent-y.jsonl"
        self._write(sub, [self._ok("2026-08-07T18:10:00Z")])
        old = time.time() - 5000
        os.utime(self.main, (old, old))
        paths = guard.session_transcripts(self.main)
        self.assertIn(sub, paths, "subagent 檔沒進掃描面")
        self.assertGreater(guard.newest_activity_at(paths), old + 1,
                           "存活判準只看主逐字稿 ⇒ 忙碌的 session 會被判成閒置")

    def test_the_age_gate_is_a_cost_gate_not_a_judgement(self) -> None:
        """成本閘的雙邊帶：預設窗（24h）遠大於一個額度視窗（實測最長 3.6h），所以它
        不會濾掉真的未處理事件；但把窗縮到 0 就該濾掉——證明那個參數真的在作用。"""
        self._write(self.main, [self._limit("2026-08-07T18:36:53Z", _REAL_SESSION_LIMIT)])
        self.assertIsNotNone(guard.unhandled_limit_event(self.main))
        far = time.time() + 10 * 86400
        self.assertEqual(guard.session_transcripts(self.main, 1.0, far), [self.main],
                         "成本閘對主逐字稿不生效（它一律納入，否則整條鏈沒有地板）")

    # 🔴 R80-SD-01：P0 修復自己引入的**反向**靜默自毀。
    # `<synthetic>` 是 harness 對**所有**合成訊息的共同標記，不是額度事件的指紋——
    # `API Error` 與 `[Request interrupted by user]` 都長這樣。第一版把任何沒有後續成功
    # 回應的合成記錄都登記成候選 ⇒ 一個以中斷／API 錯誤收尾的 session（常態，不是例外）
    # 會被判成未處理撞線 → `sentinel_decide` 解不出 reset → `escalate` → **哨兵自我刪除**。
    # 舊病是「該醒不醒」，新病是「不該死卻自我刪除」，兩者同樣靜默：痕跡只多一行
    # `sentinel_escalate`，`Get-ScheduledTask` 查不到那支工作，與正常下班外觀相同。
    # 註解裡那個 0.0% 假陽性是**橫斷面**（單一時點 257 支檔），量不到這個**縱向**情境。
    def test_a_non_quota_synthetic_message_is_not_a_hit(self) -> None:
        """注入自證：整支逐字稿只有 API 錯誤／使用者中斷 ⇒ 必須回 `None`。

        把 `unhandled_limit_event` 裡的 kind 篩選拿掉，這一條當場紅（實測：拿掉後
        回傳 kind=`transient` 的候選，`_sentinel_tick` 隨即走 escalate 並刪掉哨兵）。
        """
        self._write(self.main, [
            self._ok("2026-08-07T18:00:00Z"),
            self._limit("2026-08-07T18:36:53Z", "API Error: Connection error."),
            self._limit("2026-08-07T18:40:00Z", "[Request interrupted by user]")])
        self.assertIsNone(
            guard.unhandled_limit_event(self.main),
            "非額度的合成訊息被當成撞線 ⇒ 哨兵會走 escalate 把自己刪掉（反向自毀）")

    def test_that_corpus_makes_the_sentinel_patrol_not_escalate(self) -> None:
        """把上一條接到**決策**那一層：同一份語料下哨兵必須續巡，而不是自我解除。

        只鎖偵測層不夠——SD-01 的傷害發生在 `sentinel_decide` 之後（`escalate` 會
        `_schtasks_remove`）。這一條釘住那條路徑整條不得被走到。
        """
        self._write(self.main, [
            self._ok("2026-08-07T18:00:00Z"),
            self._limit("2026-08-07T18:40:00Z", "[Request interrupted by user]")])
        decision = planner.sentinel_decide(
            guard.unhandled_limit_event(self.main), "", 10.0,
            datetime(2026, 8, 7, 19, 0, tzinfo=UTC).astimezone(_TAIPEI))
        self.assertEqual(decision["action"], "patrol",
                         f"一則中斷訊息就讓哨兵下班了：{decision['reason']}")

    def test_a_real_quota_hit_in_the_same_shape_still_fires(self) -> None:
        """鑑別力反證：篩選不是靠「一律回 None」拿到上面兩條的綠。

        同一個形狀、只把文字換成真實的 session limit 語料 ⇒ 必須抓得到。
        """
        self._write(self.main, [
            self._ok("2026-08-07T18:00:00Z"),
            self._limit("2026-08-07T18:36:53Z", "API Error: Connection error."),
            self._limit("2026-08-07T18:40:00Z", _REAL_SESSION_LIMIT)])
        event = guard.unhandled_limit_event(self.main)
        self.assertIsNotNone(event, "篩選把真的撞線一起濾掉了（過度修正）")
        self.assertEqual(event["kind"], guard.LIMIT_SESSION)
        self.assertEqual(event["timestamp"], "2026-08-07T18:40:00Z",
                         "取到的是被濾掉的那筆 transient，而不是真的撞線")


# ═══════ R81：續航協定的兩個**設計缺口**（R80 四次真實撞線的驗屍，improving_104 §4.5）
# 兩個都不是 bug——機制照著規格跑，而規格漏了一種情況。鎖也照這條界線寫：守的是
# 「規格現在涵蓋了那一種情況」，不是「某支函式回傳什麼」。
#   缺口 A：額度有兩條線（`session limit` 等得到、`monthly spend limit` 等不到），
#           而下游動作只有一種。R80 第 3 次撞線就是這一類，協定全程零反應。
#   缺口 B：協定救的單位是 session，而四次撞線裡主迴圈**一次都沒死**——死的是扇出。


class SpendLimitReachesAHumanTest(unittest.TestCase):
    """缺口 A。🔴 注意：`escalate`／`stop` 這兩個判定**本來就不排程**，缺的不是那個。

    缺的是「通知」有沒有載體：兩支的理由逐字寫著「只有人去 claude.ai 提額才會回來」
    「硬停並通知人」，而全部的反應是 `print(..., file=sys.stderr)`——這兩支都由
    schtasks 以 `pythonw.exe`（GUI 子系統、**沒有 console**）起，那行 stderr 沒有任何
    終端收得到。⇒ 「不排程」成立、「叫人」結構上不可能成立，而兩者留下的痕跡完全同形
    （狀態 abandoned、工作被刪、jsonl 多一行）。**最難發現的失效形態**正是這一種。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r81-alert-"))
        self.plan = self.tmp / "plan.md"
        self.plan.write_text("# 可重啟點任務書\n", encoding="utf-8", newline="\n")
        self.note = self.tmp / "AUTOSDD_ATTENTION.md"
        self.log = self.tmp / "trail.jsonl"
        self.removed: list[str] = []
        self.notified: list[tuple[str, str]] = []
        self.registered: list[str] = []
        self._swap(escalation, "note_path", lambda: self.note)
        self._swap(escalation, "fanout_path", lambda sid: self.tmp / f"fanout_{sid}.json")
        self._swap(escalation, "notify", self._notify)
        # 🔴 殘骸回收的掃描面導進沙箱：production 掃的是系統暫存，而一支會真的去刪開發者
        # `%TEMP%` 的單元測試，就是把驗證載具做成了副作用來源（本 repo 對此有判例）。
        real_gc = escalation.gc_plans
        self._swap(escalation, "gc_plans",
                   lambda current=None, age=escalation.PLAN_GC_AGE_SECONDS, root=None:
                   real_gc(current, age, self.tmp))
        self._swap(planner, "endurance_log_path", lambda plan: self.log)
        self._swap(planner, "_schtasks_remove", self._remove)
        # 🔴 排程註冊必須被攔下來：這一組測試若真的去建 schtasks，它就成了一支會在
        # 開發者機器上留下垃圾工作、且在 CI（Linux）上必紅的測試。攔下來同時也讓
        # 「有沒有排程」變成一個**可斷言的值**——這正是缺口 A 要分辨的那件事。
        self._swap(planner, "_register_and_record", self._register)

    def _swap(self, module: object, name: str, value: object) -> None:
        old = getattr(module, name)
        setattr(module, name, value)
        self.addCleanup(setattr, module, name, old)

    def _notify(self, title: str, body: str) -> int:
        self.notified.append((title, body))
        return 0

    def _remove(self, task: str) -> int:
        self.removed.append(task)
        return 0

    def _register(self, plan: Path, state: dict, at: object, tick: str) -> tuple[int, str]:
        self.registered.append(str(at))
        state["next_run_time"] = "FAKE-NEXT-RUN"
        return 0, "FAKE-NEXT-RUN"

    def _tick(self, transcript: Path) -> int:
        planner.write_relay(self.plan, {
            **RelayStateTest.GOOD, "kind": "sentinel", "reset_source": "operator",
            "reset_at": "", "plan_path": str(self.plan), "task_name": "T_R81",
            "session_id": transcript.stem, "transcript": str(transcript),
            "log_path": str(self.log)})
        return planner._sentinel_tick(planner.build_parser().parse_args(
            ["--sentinel-tick", "--plan", str(self.plan)]))

    def _rows(self) -> list[dict]:
        return [json.loads(line) for line
                in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _dead_agent(self, transcript: Path, run: str = "wf_zzz") -> None:
        """在該 session 底下種一個**被撞線打死的扇出 agent**（＝「有東西要救」）。"""
        agent = (transcript.with_suffix("") / "subagents" / "workflows" / run
                 / "agent-dead.jsonl")
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(UnhandledLimitDetectionTest._limit(
            "2026-08-07T00:44:01.000Z", _REAL_SESSION_LIMIT) + "\n",
            encoding="utf-8", newline="\n")

    def test_a_monthly_spend_limit_alerts_a_human_and_never_schedules(self) -> None:
        """等不到的那一條線：**不排程**（等到天亮它還是滿的）＋ 真的把人叫來。

        🔴 R82／HELM-01 收緊了「敲人」的門檻，所以這一條的語料也跟著補上第二個合取項：
        **有未處理撞線 且 有扇出待救**。理由是使用者三度收到彈窗的那件事——「敲人」是
        整條協定裡唯一會打斷人的動作，而唯一只有人做得到、又真的等不了的情形，是有一批
        被打死的 agent 等著他去按 `resumeFromRunId`。沒有東西要救時仍然寫紙（零打擾），
        那一半由 `test_a_spend_limit_with_nothing_to_rescue_never_taps_a_human` 守。
        """
        transcript = _quota_transcript(self.tmp / "sid_spend.jsonl", _REAL_SPEND_LIMIT)
        self._dead_agent(transcript)
        rc = self._tick(transcript)
        self.assertEqual(rc, 1)
        self.assertEqual(self.registered, [],
                         "月度支出上限被排了一支永遠不會成功的工作 ⇒ 協定在一個永遠不會"
                         "變的狀態上空轉，而痕跡看起來一切正常")
        self.assertTrue(self.note.is_file(), "「叫人」沒有留下任何人看得到的載體")
        body = self.note.read_text(encoding="utf-8")
        self.assertIn(escalation.USAGE_URL, body, "紙上沒寫唯一能讓額度回來的那個動作")
        self.assertIn("排程等待對它無效", body, "紙上沒說清楚「等」對這一類是錯的動作")
        self.assertEqual(len(self.notified), 1, "只寫了紙、沒有敲人——人不在電腦前就永遠不知道")
        self.assertEqual(self.removed, ["T_R81"], "終態沒有把排程收掉（會留下過期事實）")

    def test_a_spend_limit_with_nothing_to_rescue_never_taps_a_human(self) -> None:
        """🔴 HELM-01 的合取項②：撞線是真的，但**沒有任何扇出在等人救** ⇒ 只寫紙、不敲。

        鑑別力全在這裡：把上一條的綠拿到手最省事的方法就是「一律敲」，而那正是使用者
        三度回報的那個行為。兩條合起來才釘得住「敲人＝有未處理撞線 **且** 有扇出待救」。
        """
        rc = self._tick(_quota_transcript(self.tmp / "sid_spend.jsonl", _REAL_SPEND_LIMIT))
        self.assertEqual(rc, 1, "終態語意不變：這一條仍然是「人不來就過不去」")
        self.assertTrue(self.note.is_file(), "沒有東西要救不等於不用留紙——紙是零打擾的")
        self.assertEqual(self.notified, [],
                         "沒有任何扇出在等人救，卻仍然主動敲了人 ⇒ 這正是 HELM-01 的形態")
        told = [row for row in self._rows() if "notify_rc" in row]
        self.assertEqual(told[-1]["notify_rc"], escalation.NOTIFY_NO_RESCUE_RC,
                         "痕跡裡讀不出「這一次刻意沒敲」與「敲了但失敗」的差別")

    def test_a_session_that_never_wrote_a_transcript_disarms_in_silence(self) -> None:
        """🔴 **HELM-01 本體**（使用者 2026-08-09 三度回報的模態彈窗，真凶就是這一格）。

        SessionStart 無條件武裝哨兵，而**開了沒做事就結束的 session 根本不會產生
        `.jsonl`**（R82 開場實查：那支逐字稿在整個 `~/.claude/projects` 遞迴搜尋零命中，
        不是路徑解析 bug）。舊實作在 `transcript.is_file()` 為 False 時硬編 `escalate`
        ——理由逐字寫著「哨兵已瞎，自我解除並叫人」，於是**一個正常結束的 session 換來
        一個杵十分鐘的模態對話框**。設計把「session 沒留下逐字稿」與「哨兵失明」混為
        一談，而前者是常態。

        本條釘住四件事：靜默（不敲人）、不留紙、排程仍要收掉（不留過期事實）、
        以及**理由句子仍與「正常下班」分得開**——後者正是當初把它做成 fail-loud 的
        唯一正當理由，收斂時不得連它一起丟掉。
        """
        missing = self.tmp / "sid_never_started.jsonl"
        self.assertFalse(missing.exists(), "語料自檢：這支逐字稿必須真的不存在")
        rc = self._tick(missing)
        self.assertEqual(rc, 0, "正常結束的 session 讓哨兵回了非零 rc（＝被當成故障）")
        self.assertEqual(self.notified, [], "🔴 逐字稿不存在竟然敲了人 ⇒ HELM-01 復發")
        self.assertFalse(self.note.is_file(), "🔴 逐字稿不存在竟然留了一張「需要你動手」")
        self.assertEqual(self.removed, ["T_R81"], "沒收掉排程 ⇒ 這支哨兵會一直醒來重演")
        decided = [row for row in self._rows() if row.get("event") == "sentinel_decided"]
        self.assertEqual(decided[-1]["action"], "disarm")
        self.assertIn("從來沒有被建立出來", decided[-1]["reason"],
                      "與「工作已結束」共用同一句理由 ⇒ 瞎掉的哨兵與正常下班的哨兵同形")
        self.assertNotIn("叫人", decided[-1]["reason"].removesuffix("不叫人"))

    def test_the_silent_disarm_takes_its_own_plan_file_with_it(self) -> None:
        """殘骸：`%TEMP%` 開場實測 26 份 `autosdd_resume_plan_*.md`，沒有人負責收。

        每一份都對應一支已經下班（或從來沒開始）的哨兵 ⇒ 下一個人用 `Get-ChildItem`
        看 `%TEMP%` 時拿到的是一堆過期事實（本 repo 對「查詢載具給出過期事實」有判例）。
        """
        self._tick(self.tmp / "sid_never_started.jsonl")
        self.assertFalse(self.plan.is_file(), "終態沒有把自己的任務書收掉 ⇒ 殘骸繼續累積")
        gone = [row for row in self._rows() if "gc_plans" in row]
        self.assertTrue(gone and gone[-1]["gc_plans"] >= 1, "痕跡裡看不出收了幾份")

    def test_the_audit_trail_can_tell_alerted_from_never_alerted(self) -> None:
        """🔴 通知的失效是**靜默**的：沒有人會因為「沒收到通知」而去查。

        所以 rc 必須落在稽核痕跡上——這是本協定「觸發了但失敗 vs 根本沒觸發」那條
        既有紀律在通知這一層的形態。少了它，`notify` 回 127（這台機器上沒有那條管道）
        與「通知成功」在事後完全分不出來。
        """
        self._tick(_quota_transcript(self.tmp / "sid_spend.jsonl", _REAL_SPEND_LIMIT))
        told = [row for row in self._rows() if "notify_rc" in row]
        self.assertTrue(told, "痕跡裡看不出叫過人沒有")
        self.assertEqual(told[-1]["note"], str(self.note))
        self.assertTrue(told[-1]["note_written"], "紙沒寫成功卻沒有留下這個事實")

    def test_the_hit_path_really_records_the_fanout_casualties(self) -> None:
        """🔴 缺口 B 的**接線**（判定層綠不代表接上了電——R77『機制蓋好沒接電』第三次
        復發就是這個形態）。這一條走真的 `_sentinel_tick`，證明扇出清單是在**撞線的那
        一次醒來**被寫出來的，而不是只有直接呼叫函式庫時才會發生。
        """
        transcript = self.tmp / "sid_spend.jsonl"
        _quota_transcript(transcript, _REAL_SPEND_LIMIT)
        agent = (transcript.with_suffix("") / "subagents" / "workflows" / "wf_zzz"
                 / "agent-dead.jsonl")
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(UnhandledLimitDetectionTest._limit(
            "2026-08-07T00:44:01.000Z", _REAL_SESSION_LIMIT) + "\n",
            encoding="utf-8", newline="\n")
        self._tick(transcript)
        decided = [row for row in self._rows() if row.get("event") == "sentinel_decided"]
        self.assertEqual(decided[-1]["runs"], ["wf_zzz"],
                         "撞線那一次醒來沒有把扇出死者記下來 ⇒ 清單只存在於單元測試裡")
        self.assertEqual(decided[-1]["dead_agents"], 1)
        self.assertTrue(Path(decided[-1]["fanout"]).is_file())

    def test_a_session_limit_still_takes_the_scheduling_branch(self) -> None:
        """🔴 控制組（不得回歸）：等得到的那一條線必須**還是**排程，而且不打擾人。

        判準的價值全在這裡——一個「把兩類都叫人」的實作會讓上面兩條全綠，卻把每一次
        普通的 session 撞線都變成一次騷擾，於是護欄很快就會被關掉。

        語料刻意**不帶** `(Asia/Taipei)` 後綴：帶了的話 `declared_zone` 在有 tz 資料庫的
        機器（Linux／macOS）上會把時刻換到台北框架、在 Windows 上回 `None` 而沿用機器
        時區 ⇒ 同一份語料在兩種機器上落在不同分支。這是本 repo act 實跑抓過的形態。
        """
        soon = datetime.now().astimezone() + timedelta(minutes=45)
        hour = soon.hour % 12 or 12
        text = (f"You've hit your session limit · resets "
                f"{hour}:{soon.minute:02d}{'pm' if soon.hour >= 12 else 'am'}")
        transcript = self.tmp / "sid_session.jsonl"
        transcript.write_text(
            UnhandledLimitDetectionTest._ok("2000-01-01T00:00:00Z") + "\n"
            + json.dumps({"type": "assistant",
                          "timestamp": datetime.now(UTC).isoformat(
                              timespec="milliseconds").replace("+00:00", "Z"),
                          "message": {"model": guard.SYNTHETIC_MODEL,
                                      "content": [{"text": text}]}}) + "\n",
            encoding="utf-8", newline="\n")
        self.assertEqual(self._tick(transcript), 0)
        self.assertEqual(len(self.registered), 1, "可等待的撞線沒有被排程 ⇒ 協定的主線壞了")
        self.assertFalse(self.note.is_file(), "普通的 session 撞線也去騷擾人")
        self.assertEqual(self.notified, [], "普通的 session 撞線也敲了桌面通知")


class FanoutCasualtyRecordTest(unittest.TestCase):
    """缺口 B：可續跑的工作單位從 session **降到 workflow run**。

    R80 四次撞線主迴圈一次都沒死，死的是 subagent（42／55／1 個）⇒ 續跑那一段永遠不會
    觸發、也**不該**觸發（session 還活著時再起一個 headless 回合只會互相干擾）。真正
    需要被記下來的是「哪一個 run、哪幾個 agent 被打死」，而那件事讀檔就知道、成本為零。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r81-fanout-"))
        self.main = self.tmp / "sid.jsonl"
        self.main.write_text(UnhandledLimitDetectionTest._ok("2026-08-07T18:00:00Z") + "\n",
                             encoding="utf-8", newline="\n")
        self.out = self.tmp / "fanout.json"
        old = escalation.fanout_path
        escalation.fanout_path = lambda sid: self.out
        self.addCleanup(setattr, escalation, "fanout_path", old)

    def _agent(self, run: str, name: str, lines: list[str]) -> Path:
        path = self.main.with_suffix("") / "subagents" / "workflows" / run / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return path

    def _script(self, run: str, workflow: str) -> None:
        folder = self.main.with_suffix("") / "workflows" / "scripts"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{workflow}-{run}.js").write_text("//", encoding="utf-8", newline="\n")

    @staticmethod
    def _hit() -> dict:
        return {"kind": guard.LIMIT_SESSION, "timestamp": "2026-08-07T18:36:53Z",
                "text": _REAL_SESSION_LIMIT}

    def test_a_dead_agent_is_attributed_to_its_run_and_workflow(self) -> None:
        """核心：撞線那一刻，`runId` 與未完成的 agent 集合真的被寫到磁碟上。"""
        self._agent("wf_abc", "agent-dead",
                    [UnhandledLimitDetectionTest._limit("2026-08-07T18:36:53Z",
                                                        _REAL_SESSION_LIMIT)])
        self._script("wf_abc", "r81-scan")
        audit = escalation.snapshot_fanout(self.main, self._hit())
        self.assertEqual(audit["runs"], ["wf_abc"])
        self.assertEqual(audit["dead_agents"], 1)
        record = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(record["runs"][0]["workflow"], "r81-scan",
                         "只記了 runId 沒記 workflow 名 ⇒ 人拿到一串亂碼，重派不了")
        self.assertEqual(record["runs"][0]["dead"][0]["agent"], "agent-dead")

    def test_a_finished_agent_is_not_listed(self) -> None:
        """鑑別力：不是「把整個 run 都算成死者」拿到上面那條綠。

        撞線之後**自己這支檔裡**還有成功回應 ⇒ 它活過來了，不該進重派清單。
        """
        self._agent("wf_abc", "agent-alive",
                    [UnhandledLimitDetectionTest._limit("2026-08-07T18:36:53Z",
                                                        _REAL_SESSION_LIMIT),
                     UnhandledLimitDetectionTest._ok("2026-08-07T18:40:00Z")])
        self.assertEqual(escalation.snapshot_fanout(self.main, self._hit()), {})
        self.assertFalse(self.out.exists(), "沒有死者卻仍寫出一份空清單")

    def test_the_same_file_criterion_is_deliberate_not_a_copy_of_the_global_one(self) -> None:
        """🔴 這一條釘住的是「為什麼判準不一樣」，不是行為（Rule 9）。

        `guard.unhandled_limit_event` 用**全域**復原證據，本模組用**同檔**證據——因為
        它們問的是不同的問題。R80 量到同檔證據對「帳號額度通不通」假陽性 81.3%，成因
        是「被打死的 subagent 在自己的檔裡永遠不會再有下一則成功回應」；而對「這一個
        agent 死了沒」，那個性質正是唯一正確的判準。把本模組改成沿用全域判準，這一條
        會紅：整個 session 已經復原（主逐字稿有更晚的成功回應），死掉的 agent 仍必須
        留在重派清單上——它不會因為別人活過來就自己活過來。
        """
        self._agent("wf_abc", "agent-dead",
                    [UnhandledLimitDetectionTest._limit("2026-08-07T18:36:53Z",
                                                        _REAL_SESSION_LIMIT)])
        self.main.write_text(
            UnhandledLimitDetectionTest._ok("2026-08-07T18:00:00Z") + "\n"
            + UnhandledLimitDetectionTest._ok("2026-08-07T23:00:00Z") + "\n",
            encoding="utf-8", newline="\n")
        self.assertIsNone(guard.unhandled_limit_event(self.main),
                          "控制組：以全域證據看，這個 session 已經復原了")
        self.assertEqual(escalation.snapshot_fanout(self.main, self._hit())["dead_agents"], 1,
                         "session 復原就把死掉的扇出從清單上抹掉 ⇒ 沒有人會再去重派它們")

    def test_the_run_is_found_from_the_live_layout_not_the_end_of_run_summary(self) -> None:
        """🔴 R81 當回合實查：`<sid>/workflows/wf_<runId>.json`（run 的總結）**只有跑完
        才寫**——活體 run 的 `workflows/` 底下只有 `scripts/`。撞線發生在**跑到一半**，
        所以判準若走那支 json，在唯一需要它的時刻永遠是空的。本條釘住「沒有那支 json
        也找得到 run」。
        """
        self._agent("wf_live", "agent-dead",
                    [UnhandledLimitDetectionTest._limit("2026-08-07T18:36:53Z",
                                                        _REAL_SESSION_LIMIT)])
        self.assertFalse((self.main.with_suffix("") / "workflows" / "wf_live.json").exists())
        self.assertEqual(escalation.snapshot_fanout(self.main, self._hit())["runs"],
                         ["wf_live"])

    def test_the_patrol_path_touches_nothing(self) -> None:
        """成本閘：沒有撞線就零 I/O。哨兵 99% 的醒來走這一支，它必須比免費還便宜。"""
        self._agent("wf_abc", "agent-dead",
                    [UnhandledLimitDetectionTest._limit("2026-08-07T18:36:53Z",
                                                        _REAL_SESSION_LIMIT)])
        self.assertEqual(escalation.snapshot_fanout(self.main, None), {})
        self.assertFalse(self.out.exists())

    def test_the_record_admits_the_same_session_only_constraint(self) -> None:
        """🔴 誠實劃界寫進**產物本身**，不是只寫在註解裡。

        `resumeFromRunId` 是同 session only，而排程器是一個 OS 行程、沒有任何管道把
        工具呼叫注入進一個活著的 session ⇒ 「自動續跑」在結構上不成立。讀這份檔的人
        （或 AutoClaude）必須當場看到這件事，否則它會被當成一個沒被按下的按鈕，而
        「宣稱全自動卻不會動」比沒有功能更糟。
        """
        self._agent("wf_abc", "agent-dead",
                    [UnhandledLimitDetectionTest._limit("2026-08-07T18:36:53Z",
                                                        _REAL_SESSION_LIMIT)])
        escalation.snapshot_fanout(self.main, self._hit())
        hint = " ".join(json.loads(self.out.read_text(encoding="utf-8"))["how_to_resume"])
        self.assertIn("resumeFromRunId", hint)
        self.assertIn("同 session only", hint, "沒把那條硬約束寫進產物 ⇒ 讀的人會以為它會自己跑")
        self.assertIn("不會", hint, "沒說清楚它不會自動發生 ⇒ 會被當成一個壞掉的按鈕")


# ════════════════════ R80：時區框架（act 在 Linux 容器抓到、Windows 本機看不見的兩個紅）
# 缺陷本體：`resets 9am` 是一個**牆上時刻**，舊實作拿**機器的**本地時區去解它，而
# `now` 由呼叫端給 ⇒ 同一份語料有兩個框架。act 實跑逐字：
#   FAIL: SentinelDecisionTest.test_a_pending_hit_whose_reset_already_passed_spends_one_probe
#         AssertionError: 'arm_reset' != 'probe'
# 容器是 UTC、本機是 UTC+8，「reset 過了沒」整個翻面。修法是把框架收成**一個**，
# 且優先採用**訊息自報**的時區（`… (Asia/Taipei)`）——那是資料自己回答的，與機器無關。
class ResetFrameIsNotTheMachineClockTest(unittest.TestCase):
    """同一份語料 ＋ 同一個**絕對時刻** ⇒ 判定必須一致，不論它被表示成哪個時區。"""

    #: 三個框架（同一個瞬間的三種寫法）。production 傳的是
    #: `datetime.now().astimezone()`＝機器時區的那一種寫法，所以「換一台時區不同的機器」
    #: 在這一層就等於「換一個 tzinfo 來表示同一個瞬間」。
    _FRAMES = (UTC, timezone(timedelta(hours=8)), timezone(timedelta(hours=-4)))

    #: 語料固定：事件錨在 `2026-08-07T00:44:01Z`、訊息說 `resets 9am (Asia/Taipei)`。
    #: 觀測時刻刻意取得夠早（Aug 6 中午 UTC），讓三個框架**都**落在 `arm_reset` 那一支
    #: ——這樣 `reset_at` 在每一格都存在，判準才比得到「框架是誰」而不是撞上 KeyError。
    _INSTANT = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)

    def _decisions(self) -> list[dict]:
        event = _sentinel_event(guard.LIMIT_SESSION, _REAL_SESSION_LIMIT)
        return [planner.sentinel_decide(event, "", 10.0, self._INSTANT.astimezone(frame))
                for frame in self._FRAMES]

    def test_the_frame_is_a_function_of_the_message_and_now_only(self) -> None:
        """🔴 核心判準（兩平台都有牙）：`reset_at` 的框架只能來自①訊息自報的時區，
        或②`now` 的時區——**絕不能**來自這台機器的時鐘。

        優先序在兩個平台上會走到不同的那一格，所以期望值也照著算，而不是寫死一個數字：
          · 有 tz 資料庫（Linux／macOS 容器）⇒ 三格都該是 `Asia/Taipei`；
          · 沒有（Windows，本機實測 `ZoneInfoNotFoundError`，且不得為此新增 `tzdata`
            相依）⇒ 每一格該是**該格 `now` 的時區**。
        注入自證：把 `sentinel_decide` 裡的 `local_time(event["timestamp"], now.tzinfo)`
        改回 `local_time(event["timestamp"])`（＝讀機器時區），本機（UTC+8）的 UTC 那一格
        會由 `09:00+00:00` 變回 `09:00+08:00` ⇒ 當場紅。這就是 act 在 UTC 容器抓到、
        而本機結構上看不見的那個缺陷。
        """
        declared = guard.declared_zone(_REAL_SESSION_LIMIT)
        for frame, decision in zip(self._FRAMES, self._decisions(), strict=True):
            with self.subTest(frame=str(frame)):
                self.assertEqual(decision["action"], "arm_reset")
                want = self._INSTANT.astimezone(declared or frame).utcoffset()
                self.assertEqual(
                    decision["reset_at"].utcoffset(), want,
                    "reset 的時區框架不是「訊息自報／now」而是機器時鐘——同一份語料"
                    "換一台機器就會得到不同的絕對時刻（act 逐字：'arm_reset' != 'probe'）")

    def test_the_declared_zone_makes_three_machines_agree(self) -> None:
        """訊息自報時區可解析時，三個框架必須給出**完全相同的絕對時刻**（機器無關）。

        🔴 誠實劃界（不粉飾）：Windows 上沒有 tz 資料庫，這一條走 else 分支，斷言的是
        **已載明的退路**——框架退回 `now` 的時區（那正是 harness 算繪那個字串時用的時區），
        於是三格本來就不會一致。兩個分支都有斷言、都會跑，沒有一格是靜默放行；
        上一條測試才是在兩個平台都咬得住的那一支。
        """
        moments = {d["reset_at"] for d in self._decisions()}
        if guard.declared_zone(_REAL_SESSION_LIMIT) is not None:
            self.assertEqual(len(moments), 1,
                             f"同一個瞬間換個時區寫法就得到不同的 reset：{moments}")
        else:
            self.assertEqual(len(moments), 3,
                             "無 tz 資料庫時三格本該各自落在自己的框架——若已一致，"
                             "代表框架其實來自別的地方（很可能又是機器時鐘）")

    def test_the_returned_moment_always_carries_an_offset(self) -> None:
        """「讓時刻一律帶 offset」：naive 進來也必須 aware 出去。

        naive 的牆上時刻一旦被 `isoformat()` 持久化就再也分不出它屬於哪個框架，讀回來
        相減會在 DST 跳點上整整差 3600 秒（掃描 S4-07）。這裡連 naive 入口一起堵住。
        """
        naive = datetime(2026, 8, 7, 8, 44)
        self.assertIsNotNone(guard.parse_reset_at(_REAL_SESSION_LIMIT, naive).tzinfo,
                             "naive 進 naive 出 ⇒ 持久化之後框架就永久遺失了")

    def test_the_schedule_string_is_converted_before_the_offset_is_dropped(self) -> None:
        """`strftime` 會無聲丟掉 offset，而 schtasks 一律以**機器本地**解讀那個字串。

        所以送出去之前必須先換算到本機框架。注入自證：拿掉 `at.astimezone()`，
        以非本機時區的 `at` 呼叫時註冊出去的牆上時刻會差掉時差（排程醒在錯的時刻，
        而 `NextRunTime` 照樣拿得到＝取證規則全綠的假綠）。
        """
        seen: list[str] = []
        original = planner._register_at_expr
        planner._register_at_expr = lambda *a: (seen.append(a[2]), (0, "x"))[1]
        try:
            at = datetime(2026, 8, 7, 1, 0, tzinfo=UTC)
            planner.register_endurance({"plan_path": "p", "task_name": "t"}, at)
        finally:
            planner._register_at_expr = original
        self.assertEqual(seen, [f"'{at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}'"],
                         "註冊出去的牆上時刻不是本機框架的 ⇒ 排程會醒在錯的時刻")


# ════════════════════ R81 額度軸（訴求 a／b）：quota 是第二把尺，不是 context 的分支
# 🔴 本段每一條都對著一筆**已被獨立審查者實測坐實**的失效，而不是對著實作細節：
#   SA-B1 quota 分支掛在 `block_verdict()` 內 ⇒ 低 context × 高 quota 那個唯一場景到不了
#   SA-B2 分母不是散文，payload 自己帶 `*_dollars`
#   SA-B3 有真值卻不在 `limits[]` 的桶（實測 `nimbus_quill`）
#   SA-B4 utilization 非單調（視窗翻頁驟降 48pp）⇒ 過期快取不得被判為 normal
#   SA-B6 被擋下的呼叫若留在帳上 ⇒ 永久過度節流
#   SA-B7 mac/Linux 上「不排程」與「排不了」外觀相同
#   SD-B1 `Workflow` 在扇出開始前就返回 ⇒ in-flight 恆讀 ≈0
# 🔴 R82：本檔那份寫死的 quota schema 複本已刪除（見 `_quota_cache` 的 WHY）。要 schema
# 的地方一律 `_meter().SCHEMA`——契約字面只有一個家，而那個家在 meter。
# （刻意**不**以反引號逐字寫出那個已死的常數名：幽靈符號鎖對它必紅，而下一個人 grep
#  到它會以為那是現行說法——同 `check_loc_budget.py` 對已死常數名的既有處置。）


def _quota_axis(now: datetime, kind: str, pct: float, resets_in: float | None) -> dict:
    """一條計費線。`resets_in is None`＝這條線**沒有 reset 可以等**（實測 spend 就是）。"""
    return {"kind": kind, "pct": pct, "group": None, "via": "limits[].percent",
            "resets_at": None if resets_in is None
            else (now + timedelta(seconds=resets_in)).isoformat()}


def _quota_cache(tmp: Path, pct: float | None, kind: str = "session",
                 resets_in: float | None = 3600.0, age: float = 0.0,
                 extra: tuple[tuple[str, float, float | None], ...] = ()) -> Path:
    """種一份合成快取（`autosdd.quota/2` 的**逐軸**形狀）。

    `resets_in`＝距 reset 幾秒；`age`＝這份讀數幾秒前量的；`extra`＝再加幾條
    `(kind, pct, resets_in)` 軸——多軸是 R82 之後才**表達得出來**的東西：舊形狀只有
    頂層一組 `{pct, kind, resets_at}`，於是「session 90%@34min ＋ weekly 20%@6d」與
    「session 10%@34min ＋ weekly 90%@6d」在快取裡根本寫不出差別。

    🔴 schema **跟著 meter 走、不寫死字面**（R82 接線階段的實測教訓）：此處原本是一份
    寫死的 `"autosdd.quota/1"` 複本，meter 升版到 `/2` 之後每一份合成快取都被判
    schema-mismatch ⇒ 額度軸整條靜默退化成「量不到」⇒ 16 條測試同時紅，而**紅的原因
    與被測的性質無關**。同一份契約字面第二個家的代價，這一次是在測試側現形。
    """
    now = datetime.now(UTC).astimezone()
    axes = ([] if pct is None else [_quota_axis(now, kind, pct, resets_in)])
    axes += [_quota_axis(now, *e) for e in extra]
    body = {"schema": _meter().SCHEMA, "axes": axes, "source": "endpoint",
            "measured_at": (now - timedelta(seconds=age)).isoformat(timespec="seconds")}
    path = tmp / "autosdd_quota.json"
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8", newline="\n")
    return path


def _decision(axes: tuple[tuple[str, float, float | None], ...],
              env: dict | None = None) -> quota_policy.Decision:
    """對合成軸跑**真的**判讀層，回 `Decision`＝訊息與 reset 分支的唯一輸入。

    每一格是 `(kind, pct, 距 reset 幾秒)`；秒數 `None`＝這條線沒有 reset 可以等。
    """
    now = datetime.now(UTC).astimezone()
    state = quota_policy.QuotaState(
        tuple(quota_policy.Axis(kind, pct, None if secs is None
                                else (now + timedelta(seconds=secs)).isoformat())
              for kind, pct, secs in axes), now.isoformat(), "test")
    return quota_policy.decide(state, now, quota_policy.load_policy(env or {})[0])


def _meter():
    """`tools/lib/quota_meter.py`（延後 import，與 `_wiring()` 同一形態）。"""
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import quota_meter  # noqa: PLC0415

    return quota_meter


def _ledger():
    """`tools/lib/quota_ledger.py`（跨行程原語的唯一的家）。"""
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import quota_ledger  # noqa: PLC0415

    return quota_ledger


def _capture_stderr(call, tmp: Path) -> str:
    """跑 `call()`，回它寫進 stderr 的東西；順便把降級閂鎖與痕跡導進 `tmp`。

    🔴 導進 tmp 不是裝飾：`note_degraded()` 的 per-source 閂鎖住在系統暫存、TTL 180 秒
    ⇒ 不隔離的話「上一次跑測試留下的 stamp」會讓這一次**靜默**，而靜默的方向正好是綠。
    """
    buf = io.StringIO()
    saved = (sys.stderr, qg.degraded_stamp_path, qg.quota_trace_path)
    sys.stderr = buf
    qg.degraded_stamp_path = lambda source: tmp / f"stamp-{source}"
    qg.quota_trace_path = lambda: tmp / "trace.jsonl"
    try:
        call()
    finally:
        sys.stderr, qg.degraded_stamp_path, qg.quota_trace_path = saved
    return buf.getvalue()


class QuotaUnitNormalizationTest(unittest.TestCase):
    """M1：四種寫法必須產出**同一個**內部值。這是唯一抓得到「差 100 倍」的東西。

    `0.3` 拿去比 `80` 永遠不觸發（閘門恆綠）、`30.0` 拿去比 `0.8` 永遠觸發（閘門恆紅），
    兩個方向都在 rc=0 的外觀下失效，沒有任何東西會轉紅——所以它必須被單獨釘住。
    """

    def test_four_channels_agree_on_one_internal_value(self) -> None:
        meter = _meter()
        for label, raw, scale in (
                ("REST utilization(float 0..100)", 56.0, meter.SCALE_PERCENT),
                ("limits[].percent(int 0..100)", 56, meter.SCALE_PERCENT),
                ("stream-json utilization(0..1)", 0.56, meter.SCALE_FRACTION),
                ("statusLine used_percentage(0..100)", 56, meter.SCALE_PERCENT)):
            with self.subTest(label):
                self.assertAlmostEqual(meter.normalize_pct(raw, scale), 56.0, places=6)

    def test_reading_a_fraction_channel_as_percent_is_caught(self) -> None:
        """反向自證：故意把 0..1 那條通道當 0..100 讀 ⇒ 值差 100 倍，且會落在最寬鬆的帶。"""
        meter, policy = _meter(), quota_policy.DEFAULT_POLICY
        wrong = meter.normalize_pct(0.96, meter.SCALE_PERCENT)
        self.assertAlmostEqual(wrong, 0.96, places=6)
        self.assertEqual(quota_policy.pct_band(wrong, policy), quota_policy.BAND_FREE,
                         "單位讀錯的後果就是：真實 96% 被判成 free 帶 ⇒ 閘門恆綠")
        self.assertEqual(quota_policy.pct_band(
            meter.normalize_pct(0.96, meter.SCALE_FRACTION), policy),
            quota_policy.BAND_HALT)

    def test_non_numbers_and_negatives_are_unmeasurable(self) -> None:
        meter = _meter()
        for raw in (None, "56", True, float("nan"), -1.0, {}):
            with self.subTest(raw=raw):
                self.assertIsNone(meter.normalize_pct(raw, meter.SCALE_PERCENT))


class QuotaUnmeasurableTest(unittest.TestCase):
    """M2：**量不到 ≠ 量到零**。四種失敗輸入都必須是 `None`，且都不得節流。"""

    def test_measure_returns_none_on_every_failure_shape(self) -> None:
        meter = _meter()
        original = meter.fetch_usage
        shapes = {"HTTP 401": (401, None), "HTTP 429": (429, None),
                  "連線層失敗": (0, None), "200 但不是 dict": (200, "nope"),
                  "200 但沒有任何桶": (200, {"limits": [], "five_hour": {}})}
        try:
            for label, result in shapes.items():
                meter.fetch_usage = lambda *a, _r=result, **k: _r
                with self.subTest(label):
                    reading = meter.measure()
                    self.assertIsNone(reading, f"{label} 竟然回了讀數：{reading!r}")
        finally:
            meter.fetch_usage = original

    def test_unmeasurable_is_its_own_band_and_is_capped_not_unlimited(self) -> None:
        """🔴 R82 具名改寫（裁決 D-8，駁回本條 R81 版的「量不到 ⇒ 不設限」）。

        R81 版逐字斷言 `fanout_cap(None) is None`＝**不設限**，理由是「斷網時自動降併發
        會讓『網路壞了』與『額度滿了』外觀相同」。那個理由只成立到 R81 複審探針量出它的
        淨效果為止：**快取過期 600s ＋ 額度 99% 時，42 次 `Agent` 派發放行 42、擋下 0**。
        裁決把它拆成兩層——守衛**行程**仍然 fail-open（不得崩、不得誤 deny），但**節流
        決策**不得靜默全放行 ⇒ 量不到時 `cap = degraded_cap`（>0，所以不會鎖死；
        且**永不** halt，因為絕不對一個沒量到的值開火）。狀態字仍必須與任何水位帶分得開。
        """
        now = datetime.now(UTC).astimezone()
        policy = quota_policy.DEFAULT_POLICY
        blind = quota_policy.decide(qg.read_quota(now, Path("nope-nowhere.json")),
                                    now, policy)
        self.assertEqual(blind.band, quota_policy.BAND_UNMEASURED)
        self.assertNotIn(blind.band, (quota_policy.BAND_FREE, quota_policy.BAND_HALT))
        self.assertIsNotNone(blind.cap, "量不到又回到「不設限」＝ R81 那個 42/42 缺口復活")
        self.assertTrue(0 < blind.cap <= policy.degraded_cap)

    def test_a_missing_or_corrupt_cache_reads_as_none_not_zero(self) -> None:
        now = datetime.now(UTC).astimezone()
        tmp = Path(tempfile.mkdtemp())
        self.assertFalse(qg.read_quota(now, tmp / "nope.json").usable())
        bad = tmp / "bad.json"
        for text in ("{", '{"schema":"other","axes":[{"kind":"s","pct":99}]}',
                     f'{{"schema":"{_meter().SCHEMA}"}}',
                     f'{{"schema":"{_meter().SCHEMA}","axes":[{{"pct":"99"}}]}}'):
            bad.write_text(text, encoding="utf-8", newline="\n")
            with self.subTest(text=text):
                self.assertFalse(qg.read_quota(now, bad).usable())


class FanoutCapLadderTest(unittest.TestCase):
    """M3：cap 的**方向**（不是數值）——隨 quota 單調不增，且 halt 帶必須恰為 0。

    🔴 R82：階梯本體已搬到 `quota_policy`，本類改由**閘實際會走的那條路**取 cap
    （`decide()`），而不是呼叫一支已刪除的純量函式。判準本身一個字都沒放寬。
    """

    def _cap(self, pct: float, resets_in: float = 3600.0,
             env: dict | None = None) -> float:
        now = datetime.now(UTC).astimezone()
        policy, problems = quota_policy.load_policy(env or {})
        self.assertEqual(problems, [], f"注入的 env 自己就不合法：{problems}")
        state = quota_policy.QuotaState(
            (quota_policy.Axis("session", pct,
                               (now + timedelta(seconds=resets_in)).isoformat()),),
            now.isoformat(), "test")
        cap = quota_policy.decide(state, now, policy).cap
        return float("inf") if cap is None else float(cap)  # None＝不設限

    def test_cap_never_rises_as_quota_rises(self) -> None:
        sweep = [self._cap(p / 2) for p in range(0, 201)]
        for lower, upper in zip(sweep, sweep[1:]):
            self.assertGreaterEqual(lower, upper, "cap 隨水位上升了 ⇒ 方向反了")

    def test_halt_band_is_exactly_zero_and_ignores_overrides(self) -> None:
        override = {"AUTOSDD_QUOTA_FANOUT_CAP": "99"}
        self.assertEqual(self._cap(95.0, env=override), 0)
        self.assertEqual(self._cap(100.0, env=override), 0)
        # 🔴 覆寫的方向鎖（R82 收緊）：`AUTOSDD_QUOTA_FANOUT_CAP` 是**上限**，只收緊不
        # 放寬。R81 版斷言它把 85% 的 cap 抬到 99——一個名字叫 CAP 的旋鈕給出比預設**更鬆**
        # 的值，那正是判讀層落地時被改掉的形狀（舊實作拿它當乘法的 base，`=8` 在 near 檔
        # 實得 16）。這裡改斷言「覆寫不會讓它變鬆」，方向與名字一致。
        self.assertLessEqual(self._cap(85.0, env=override), self._cap(85.0))
        self.assertEqual(self._cap(85.0, env={"AUTOSDD_QUOTA_FANOUT_CAP": "1"}), 1)

    def test_the_two_thresholds_are_tunable_because_the_helm_asked_for_that(self) -> None:
        """🔴 R82 具名改寫（掌舵者裁定：訴求 6c 是使用者原文，優先於本條的舊宣稱）。

        本條的 R81 版是另一個名字（**刻意不逐字反引號寫出**：那支 test 已不存在，指名它
        會被幽靈符號鎖判紅，而 grep 到的人會以為它還在——同 `check_loc_budget.py` 對已死
        符號名的既有處置），逐字註解「掌舵者訴求 b 的兩個數字是規格，**不是可調參數**」
        並把 80／95 釘死。
        訴求 6c 逐字要求「有參數設定 .env.example」⇒ 這是**一道鎖在守一個與需求矛盾的
        宣稱**（本 repo 判過的形態，比沒有鎖更難看見）。裁決見合議規格 D-6（裁 SA）。
        改寫後守的性質換成兩條**仍然有鑑別力**的：① 出廠預設就是使用者原文的四個錨點；
        ② 設定真的會生效（忽略設定值即紅），而非法設定不得靜默採用。
        """
        default = quota_policy.DEFAULT_POLICY
        self.assertEqual((default.notice_pct, default.converge_pct,
                          default.prepare_pct, default.halt_pct), (50.0, 70.0, 85.0, 95.0))
        tuned, problems = quota_policy.load_policy({"AUTOSDD_QUOTA_HALT_PCT": "88"})
        self.assertEqual((problems, tuned.halt_pct), ([], 88.0), "設了沒生效＝6c 假交付")
        self.assertEqual(quota_policy.pct_band(89, tuned), quota_policy.BAND_HALT)
        self.assertEqual(quota_policy.pct_band(89, default), quota_policy.BAND_PREPARE)
        _, bad = quota_policy.load_policy({"AUTOSDD_QUOTA_HALT_PCT": "abc"})
        self.assertTrue(bad, "壞值被靜默吞掉了 ⇒ 「設了沒生效」而沒有人知道")

    def test_quota_thresholds_are_not_the_context_thresholds(self) -> None:
        """M10 的同構：同名不同義是本 repo 反覆判過的形態，**數字接近才更危險**。"""
        policy = quota_policy.DEFAULT_POLICY
        self.assertNotEqual(policy.prepare_pct / 100, guard.WARN_RATIO)
        self.assertNotEqual(policy.halt_pct / 100, guard.HARD_RATIO)


class QuotaBucketUnionTest(unittest.TestCase):
    """M7＋SA-B3：桶名一律動態列舉，且判定取**兩個來源的聯集**。"""

    def test_a_bucket_with_a_real_value_outside_limits_can_win(self) -> None:
        """本包實測：`nimbus_quill` 有 `utilization` 真值卻不在 `limits[]` 裡。

        只讀 `limits[]` 時這一條當場紅——那正是它存在的理由：哪天是代號桶先滿，
        取 `max(limits[].percent)` 會讀到一個低值而**永不節流**，且沒有東西轉紅。

        🔴 R82 改判準（`meter.worst()` 已刪除，見該檔的墓碑）：舊版問「挑出來的那一桶
        是不是它」，而「挑桶」這個動作本身就是本輪要拆掉的缺陷。現在問的是**取數層有沒有
        把它交出去**——判讀層對全部軸求值，所以「它在不在 axes 裡」才是取數層的責任邊界。
        """
        meter = _meter()
        payload = {"limits": [{"kind": "session", "percent": 12},
                              {"kind": "weekly_all", "percent": 30}],
                   "five_hour": {"utilization": 12.0},
                   "nimbus_quill": {"utilization": 97.0},   # ← 不在 limits[] 裡
                   "seven_day": {"utilization": 30.0}}
        axes = meter.bucket_readings(payload)
        self.assertIn(("nimbus_quill", 97.0), [(a["kind"], a["pct"]) for a in axes])
        # 只讀 `limits[]` 的版本 max 只到 30 ⇒ 這一行是「它真的會影響判定」的憑證。
        self.assertEqual(max(a["pct"] for a in axes), 97.0)
        # 逐軸自帶自己的 `resets_at`：這一格就是 R82 的缺陷本體——舊形狀只留下被挑中那
        # 一桶的期程，其餘每一桶的「還有多久 reset」在投影那兩行被丟掉。
        for axis in axes:
            self.assertIn("resets_at", axis)

    def test_an_unknown_codename_bucket_does_not_raise(self) -> None:
        meter = _meter()
        payload = {"limits": [{"kind": "session", "percent": 5}],
                   "brand_new_bucket_2027": {"utilization": 42.0},
                   "member_dashboard_available": False, "seven_day_opus": None}
        kinds = {r["kind"] for r in meter.bucket_readings(payload)}
        self.assertIn("brand_new_bucket_2027", kinds)

    def test_the_source_carries_no_hardcoded_bucket_roster(self) -> None:
        """禁止寫死桶名清單：live payload 當回合 17 個頂層鍵，二進位內嵌名單只有 8 個。"""
        source = (_REPO_ROOT / "tools" / "lib" / "quota_meter.py").read_text(
            encoding="utf-8")
        code = "\n".join(ln for ln in source.splitlines() if not ln.lstrip().startswith("#"))
        for name in ("nimbus_quill", "amber_ladder", "seven_day_opus", "cinder_cove"):
            with self.subTest(name=name):
                self.assertNotIn(name, code, "桶名被寫死進**程式碼**了（註解裡舉例可以）")

    def test_spend_is_reachable_because_it_only_has_percent(self) -> None:
        """`spend` 沒有 `utilization` 只有 `percent` ⇒ 少了第三條規則它整條線失明。"""
        meter = _meter()
        readings = meter.bucket_readings({"limits": [], "spend": {"percent": 96}})
        self.assertEqual([(r["kind"], r["pct"]) for r in readings], [("spend", 96.0)])


class QuotaKindBranchTest(unittest.TestCase):
    """M6＋SA-B7：三條線走不同分支，而分支由**資料**（reset 有多遠）決定、不由桶名決定。"""

    def _now(self) -> datetime:
        return datetime(2026, 8, 8, 22, 0, tzinfo=UTC)

    def test_a_near_reset_may_be_armed(self) -> None:
        soon = (self._now() + timedelta(hours=4)).isoformat()
        self.assertEqual(qg.reset_branch(soon, self._now()), qg.QUOTA_BRANCH_ARM)

    def test_a_weekly_reset_must_not_be_armed(self) -> None:
        """七天後才響的排程＋全綠的痕跡＝R59 事故同形，所以這一條是硬斷言。"""
        far = (self._now() + timedelta(days=6)).isoformat()
        self.assertEqual(qg.reset_branch(far, self._now()), qg.QUOTA_BRANCH_NOTIFY)

    def test_no_reset_at_all_escalates(self) -> None:
        for raw in (None, "", "not-a-time", 12345):
            with self.subTest(raw=raw):
                self.assertEqual(qg.reset_branch(raw, self._now()),
                                 qg.QUOTA_BRANCH_ESCALATE)

    def test_a_naive_timestamp_is_refused(self) -> None:
        """不帶 offset 的字串不得被當成時刻（跨 DST 相減會靜默差 3600 秒）。"""
        self.assertEqual(qg.reset_branch("2026-08-08T23:00:00", self._now()),
                         qg.QUOTA_BRANCH_ESCALATE)

    def test_each_branch_says_something_different(self) -> None:
        """三支分支＋兩種「沒武裝」的訊息必須**互不相同**。

        SA-B7 的射程：mac/Linux 上武裝入口本身就有 `os.name != 'nt'` 早退 ⇒ 沿用
        weekly 那支靜默的「不排程」路徑時，「不排程」與「排不了」長得一模一樣，
        而合成注入的判準在 mac 上照樣全綠。
        """
        decision = _decision((("session", 96.0, 3600.0),))
        base = {"plan": "P", "kind": "session", "sentinel_off": False, "posix": False}
        texts = {
            "armed": qg.quota_halt_message(
                decision, {**base, "branch": qg.QUOTA_BRANCH_ARM, "armed": True}),
            "weekly": qg.quota_halt_message(
                decision, {**base, "branch": qg.QUOTA_BRANCH_NOTIFY, "armed": False}),
            "spend": qg.quota_halt_message(
                decision, {**base, "branch": qg.QUOTA_BRANCH_ESCALATE, "armed": False}),
            "posix": qg.quota_halt_message(
                decision, {**base, "branch": qg.QUOTA_BRANCH_ARM, "armed": False,
                           "posix": True}),
            "sentinel_off": qg.quota_halt_message(
                decision, {**base, "branch": qg.QUOTA_BRANCH_ARM, "armed": False,
                           "sentinel_off": True}),
        }
        self.assertEqual(len(set(texts.values())), len(texts),
                         "有兩支分支的訊息一樣 ⇒ 讀者分不出「沒排」與「排不了」")
        self.assertIn("沒有排程載具", texts["posix"])
        self.assertIn("提額", texts["spend"])


# ═══════════════════════════════════════════════════════════════════════════
# R83／F2-② 的**接線面**：使用者看到的那則 halt 訊息，指的是本機那個載具的指令
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 立案（獨立複驗補的那一半）：F2-② 把取證指引下沉到 `schedule_backend.<後端>.
# evidence_hint()`，而「三句話彼此不同、mac 那句不含 Windows cmdlet」已由
# `test_mac_endurance_r83.BackendInterfaceIsSymmetricTest` 在**後端層**守住。但那是
# 判定層——「那三句話真的出現在使用者讀到的那則訊息裡」是另一件事，而本 repo 的
# 「機制蓋好沒接電」已三度復發。複驗當回合實測：把 cmdlet 字面貼回 `quota_halt_message`
# （＝本輪修掉的缺陷原形，且 `evidence_hint()` 仍留在原處被別人叫）時，全庫**沒有任何
# 東西會轉紅**——後端那三句仍然正確，只是沒有人在讀它。缺陷 ② 的本體是「訊息說了假話」,
# 所以判準必須讀訊息本身。
def halt_hint_problems(text: str, must: str, forbidden: str) -> list[str]:
    """halt 訊息必須帶本機載具的取證指令，且不得帶別的平台的。純函式，紅綠由注入自證。"""
    problems = []
    if must not in text:
        problems.append(f"halt 訊息沒有本機載具的取證指令（缺 `{must}`）"
                        "⇒ 讀者拿不到憑證的查法")
    if forbidden in text:
        problems.append(f"halt 訊息印了本平台不存在的 `{forbidden}`"
                        "⇒ 武裝是真的、憑證是真的，**指路是假的**")
    return problems


class QuotaHaltMessagePointsAtThisPlatformTest(unittest.TestCase):
    """halt／armed 那一支的取證指令必須來自 `select()` 選中的那個後端。"""

    #: 兩欄都在**任何**主機上跑（注入 `select()`，不讀本機平台）——單平台判準不可外推，
    #: 而這個缺陷的方向正是「在另一個平台印了一句不存在的指令」。
    _COLUMNS = ((sb.SchtasksBackend, "Get-ScheduledTask", "launchctl"),
                (sb.LaunchdBackend, "launchctl", "Get-ScheduledTask"))

    def _armed_message(self, backend: type) -> str:
        stub = unittest.mock.Mock()
        stub.select.return_value = backend()
        old = qg.schedule_backend
        qg.schedule_backend = stub
        self.addCleanup(setattr, qg, "schedule_backend", old)
        return qg.quota_halt_message(
            _decision((("session", 96.0, 600.0),)),
            {"plan": "P", "kind": "session", "branch": qg.QUOTA_BRANCH_ARM,
             "armed": True, "sentinel_off": False, "posix": False})

    def test_each_carrier_gets_its_own_evidence_command(self) -> None:
        for backend, must, forbidden in self._COLUMNS:
            with self.subTest(carrier=backend.name):
                self.assertEqual(
                    halt_hint_problems(self._armed_message(backend), must, forbidden), [])

    def test_red_the_hardcoded_windows_cmdlet_would_be_caught(self) -> None:
        """注入＝修前原形（mac 那條路印 Windows cmdlet）⇒ 兩個方向都必須紅。"""
        problems = halt_hint_problems(
            "   ✅ 已武裝喚醒。憑證是 `NextRunTime` 這個**值**：Get-ScheduledTask "
            "| Where-Object TaskName -like 'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo\n",
            "launchctl", "Get-ScheduledTask")
        self.assertEqual(len(problems), 2, problems)

    def test_a_correct_mac_message_is_not_flagged(self) -> None:
        """控制組：對的訊息不得被判紅（假紅的鎖活不過一輪）。"""
        self.assertEqual(halt_hint_problems(
            "   ✅ 已武裝喚醒。launchctl print gui/501/<label>\n",
            "launchctl", "Get-ScheduledTask"), [])

    def test_the_import_failure_fallback_never_invents_a_command(self) -> None:
        """`schedule_backend` 不可達時只能說「說不出取證指令」，不得印任何一個平台的指令。

        fail-open 的方向必須是「少說一句話」而不是「說一句本平台不存在的話」——後者
        與這個缺陷同型（憑證真、指路假），只是成因換成 import 失敗。
        """
        old = qg.schedule_backend
        qg.schedule_backend = None
        self.addCleanup(setattr, qg, "schedule_backend", old)
        hint = qg.evidence_hint()
        for command in ("Get-ScheduledTask", "launchctl", "schtasks"):
            self.assertNotIn(command, hint)
        self.assertIn("說不出", hint)


class QuotaStaleCacheTest(unittest.TestCase):
    """SA-B4：過期的舊值**不得**被直接採信為 normal。"""

    def test_a_stale_78_is_not_taken_at_face_value(self) -> None:
        """注入 SA 指名的那一組：快取值 78、stale 超 TTL ⇒ 不得被直接採信。

        方向刻意選「量不到」而不是「上調一個安全邊際」：這個量非單調（視窗翻頁時
        實測驟降 48pp）也非等速，任何邊際都是猜的。
        """
        tmp = Path(tempfile.mkdtemp())
        now = datetime.now(UTC).astimezone()
        path = _quota_cache(tmp, 78.0, age=qg.QUOTA_CACHE_TTL_SECONDS + 60)
        state = qg.read_quota(now, path)
        self.assertFalse(state.usable())
        self.assertEqual(state.source, "stale-cache")
        self.assertEqual(quota_policy.decide(state, now, quota_policy.DEFAULT_POLICY).band,
                         quota_policy.BAND_UNMEASURED)

    def test_a_fresh_78_is_used_as_measured(self) -> None:
        """控制組：只測「過期不採信」而不測「新鮮的照用」的鎖沒有鑑別力。"""
        tmp = Path(tempfile.mkdtemp())
        now = datetime.now(UTC).astimezone()
        state = qg.read_quota(now, _quota_cache(tmp, 78.0, age=1))
        self.assertEqual([a.pct for a in state.axes], [78.0])
        self.assertEqual(quota_policy.decide(state, now, quota_policy.DEFAULT_POLICY).band,
                         quota_policy.BAND_CONVERGE)

    def test_a_stale_high_value_also_stops_throttling(self) -> None:
        """誠實劃界的反面：過期就是量不到，**連 96% 都不例外**。

        這是刻意的取捨，不是漏洞：斷網時保留一個舊的高值會讓守衛在網路壞掉時
        無限期停機，而那與「額度真的滿了」外觀完全相同。地板由逐字稿撞線偵測提供。
        （「量不到」本身仍有 `degraded_cap`，見 `QuotaUnmeasurableTest`——不採信舊值
        與不設限是兩件事，R82 只推翻了後者。）
        """
        tmp = Path(tempfile.mkdtemp())
        state = qg.read_quota(datetime.now(UTC).astimezone(),
                              _quota_cache(tmp, 96.0, age=99_999))
        self.assertFalse(state.usable())


class QuotaCacheContractHomeTest(unittest.TestCase):
    """🔴 R81 收斂（Architect-B2）：快取的檔案契約（檔名＋schema）只能有**一個家**。

    立案的形狀不是「兩處現在不一致」，而是**那個綁定從來沒有被測過**：meter 是唯一寫者、
    hook 是唯一讀者，而所有既有快取測試都傳明確 `path` 給 `read_quota()` ⇒ 改掉 meter 的
    `CACHE_NAME`，meter 寫新檔、hook 讀不到 → `pct=None` → **永遠不節流**，而全套照綠。
    """

    def test_the_hook_follows_the_meter_instead_of_copying_it(self) -> None:
        """紅綠自證：把 meter 的兩個常數改掉，hook 必須**跟著動**；持有複本者當場紅。"""
        meter = _meter()
        self.assertEqual(qg.quota_cache_path(), meter.cache_path())
        self.assertEqual(qg.quota_schema(), meter.SCHEMA)
        old_name, old_schema = meter.CACHE_NAME, meter.SCHEMA
        try:
            meter.CACHE_NAME, meter.SCHEMA = "autosdd_q_INJ.json", "autosdd.quota/INJ"
            self.assertEqual(qg.quota_cache_path().name, meter.CACHE_NAME,
                             "hook 持有一份檔名複本 ⇒ meter 改名後兩邊寫讀不同檔，"
                             "而 pct=None 的淨效果是永遠不節流（且全套測試照綠）")
            self.assertEqual(qg.quota_schema(), meter.SCHEMA)
            # 同一次注入下，hook 必須認得 meter **現在**會寫出來的 schema。
            tmp = Path(tempfile.mkdtemp())
            path = _quota_cache(tmp, 91.0)
            state = qg.read_quota(datetime.now(UTC).astimezone(), path)
            self.assertEqual([(a.kind, a.pct) for a in state.axes], [("session", 91.0)])
        finally:
            meter.CACHE_NAME, meter.SCHEMA = old_name, old_schema

    def test_the_hook_source_carries_no_second_copy(self) -> None:
        """靜態那一半：hook 的**程式碼**裡不得再出現契約字面（註解裡舉例可以）。"""
        code = "\n".join(ln for ln in _HOOK.read_text(encoding="utf-8").splitlines()
                         if not ln.lstrip().startswith("#"))
        for literal in (_meter().CACHE_NAME, _meter().SCHEMA):
            with self.subTest(literal=literal):
                self.assertNotIn(literal, code, "契約字面又長出第二個家")


# ═══════════════════════════════════════════════════════════════════════════
# R83／F2-①：跑測試不得寫進**生產的**降級觀測面
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 立案是實測，不是衛生偏好。本輪在 mac 真機的 `%TMPDIR%` 撈到
# `autosdd_quota_degraded.jsonl` 有 **17 列** `source=no-cache`，逐列時間戳與
# `mkdtemp(prefix="degraded-")`／`"quota-gate-"` 這些**測試自己**的暫存目錄一一對上；
# 二分定位（逐類別跑、量該檔行數增減）得到逐字證據：
#     QuotaUnmeasurableFanoutTest: trace +1  新 stamp=1
#     其餘四個 quota 類別:          trace +0  新 stamp=0
# 成因：上面那兩個類別把 `quota_cache_path`／`fanout_ledger_path`／`quota_latch_path`
# 換成沙箱，卻**沒有換** `quota_trace_path`／`degraded_stamp_path` ⇒ `note_degraded()`
# 寫的是真的那兩個檔。
#
# 為什麼這比「檔案變髒」嚴重得多，兩層：
#   ① 那個 jsonl **就是** SD-B2 要的那個觀測面——人要靠它回答「額度軸是不是正在靜默地
#      不節流」。17/17 是假的，於是真事件在裡面讀不出來（訊噪比被測試自己毀掉）。
#   ② 更硬的一層：`note_degraded()` 出聲帶 per-source TTL 閂鎖，而測試**消耗掉了真的那個
#      閂鎖**。跑完測試後的 180 秒內，production 真的降級時 `note_degraded()` 回 `""`
#      ——一聲都不出。「不節流 ≠ 不出聲」這條不變量在那個視窗裡是假的，而它完全靜默。
#      這正是任務書 F2-① 觀察到的症狀（no-cache ⇒ 量不到 ⇒ 不節流且無聲），只是成因
#      不是它推測的 `TMPDIR` 分裂（該推測已被三組實測否證，見交付報告）。
def _TRACE_ISOLATION(test: unittest.TestCase) -> tuple:  # noqa: N802 — 與同檔 setUp 表對齊
    """要接在 `setUp` 那張 swap 表後面的兩格：把降級痕跡與閂鎖也關進沙箱。

    做成**共用的一格**而不是各類別自己抄一份：抄的那個形態正是這個缺陷的成因（兩個
    類別各抄了四格、各漏了同樣的兩格）。漏用它會被下面那道鎖抓到。
    """
    # 🔴 R84：第三格（`refresh_stamp_path`）。它與上面兩格同構——額度軸落在生產暫存的
    # 檔——而它此前在 `claim_refresh_slot()` 裡是寫死路徑、沒有注入點 ⇒ 任何走到刷新
    # 路徑的測試都會吃掉真的那個 180 秒名額，此後真的需要補量時靜默不補。
    # 🔴 R86：第四格（`burn_ledger_path`）。它住**持久**目錄（`~/.autosdd/traces`）⇒ 漏關
    # 的代價比前三格更大：合成讀數會被 `burn_ratio()` 當真觀測拿去推換算比，汙染的是
    # **下一次真的派工決策**（理由全文見具名證據檔 `CrossPlatform_R86_Pace_Calibration.md`
    # ——刻意不寫它的目錄前綴：分桶棘輪把「提到散文樹」的整塊歸進 shrink-only 的 `prose`
    # 桶，而本塊守的是沙箱隔離、不是散文，寫全路徑會讓 61 行被誤記進那一桶）。
    return (("quota_trace_path", lambda: test.tmp / "trace.jsonl"),
            ("degraded_stamp_path", lambda source: test.tmp / f"stamp-{source}"),
            ("refresh_stamp_path", lambda: test.tmp / "refresh.stamp"),
            ("burn_ledger_path", lambda: test.tmp / "burn.jsonl"))


def trace_isolation_problems(source: str) -> list[str]:
    """哪些 TestCase 把額度快取關進沙箱、卻把降級痕跡留在生產路徑上。純函式判準。

    判準取「同一個類別裡有沒有提到這幾個名字」而不是解析 swap 呼叫的形狀：後者會隨
    `setUp` 的寫法（for 迴圈／逐行 patch／`mock.patch.object`）漂移，而漂移的方向是
    **漏抓**。名字有出現就算數——`_TRACE_ISOLATION` 這個間接層也算（它的 body 裡有）。
    """
    needed = ("quota_trace_path", "degraded_stamp_path")
    helper = "_TRACE_ISOLATION"
    problems = []
    for cls in [n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)]:
        seen = {c.value for c in ast.walk(cls)
                if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        seen |= {c.id for c in ast.walk(cls) if isinstance(c, ast.Name)}
        if "quota_cache_path" not in seen or helper in seen:
            continue
        missing = sorted(n for n in needed if n not in seen)
        if missing:
            problems.append(
                f"{cls.name}（第 {cls.lineno} 行）把快取關進沙箱卻沒關 {missing}"
                " ⇒ 跑一次測試就往生產的 autosdd_quota_degraded.jsonl 寫一列假紀錄，"
                "並吃掉真的那個 180 秒閂鎖（此後真降級一聲不出）")
    return problems


class TraceIsolationTest(unittest.TestCase):
    """本檔自己的隔離不變量：**測試不得寫進生產的降級觀測面**（見上方 WHY）。"""

    def test_no_quota_test_leaks_into_the_production_trace(self) -> None:
        self.assertEqual(trace_isolation_problems(
            Path(__file__).read_text(encoding="utf-8")), [])

    def test_red_the_two_classes_this_round_fixed_would_be_caught(self) -> None:
        """注入＝修前的 `setUp` 原形（四格 swap、漏兩格）⇒ 必紅。"""
        injected = ("class Leaky(unittest.TestCase):\n"
                    "    def setUp(self):\n"
                    "        for name, value in (('quota_cache_path', None),\n"
                    "                            ('quota_latch_path', None)):\n"
                    "            self._swap(qg, name, value)\n")
        problems = trace_isolation_problems(injected)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("quota_trace_path", problems[0])

    def test_the_shared_helper_counts_as_isolation(self) -> None:
        """對照組：走 `_TRACE_ISOLATION` 的類別必須放行，否則沒有人會用那個共用格。"""
        self.assertEqual(trace_isolation_problems(
            "class Fine(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        for n, v in (('quota_cache_path', None), *_TRACE_ISOLATION(self)):\n"
            "            self._swap(qg, n, v)\n"), [])

    def test_a_class_that_never_touches_the_cache_is_out_of_scope(self) -> None:
        """射程控制組：沒有碰額度快取的類別不得被這道鎖波及（假紅會讓它被關掉）。"""
        self.assertEqual(trace_isolation_problems(
            "class Unrelated(unittest.TestCase):\n"
            "    def test_x(self):\n        pass\n"), [])

    def test_the_real_production_trace_is_untouched_by_this_module(self) -> None:
        """行為面（靜態判準之外的那一半）：現在跑一遍那兩個類別，真檔一行都不准長。

        🔴 這一條刻意讀**真的**路徑（不是沙箱）——它問的正是「生產那一份有沒有被寫到」，
        而那件事只有真路徑回答得出來。它只讀不寫。

        🔴 R84／SA84-01：巢狀 runner 一律走 `_run_nested_suite`（見該函式的 WHY——這一支
        就是把整個模組的哨兵 pin 沖掉的那一支）。
        """
        real = qg.quota_trace_path()
        before = real.read_bytes() if real.exists() else b""
        suite = unittest.TestLoader().loadTestsFromNames(
            [f"{__name__}.QuotaUnmeasurableFanoutTest",
             f"{__name__}.QuotaDecisionEntryIsSingleTest"])
        _run_nested_suite(suite)
        after = real.read_bytes() if real.exists() else b""
        self.assertEqual(after, before,
                         f"跑測試把紀錄寫進了生產痕跡 {real}（多了 "
                         f"{len(after) - len(before)} bytes）")
        self.assertEqual(os.environ.get(guard.SENTINEL_OFF_ENV), "1",
                         "巢狀 runner 把哨兵 pin 沖掉了 ⇒ 本模組**在這一支之後**就再也"
                         "擋不住「同行程測試註冊真 launchd job」（SA84-01 的本體）")


class ZSentinelPinOutlivesEveryNestedRunnerTest(unittest.TestCase):
    """🔴 R84／SA84-01：把「同行程不准碰真排程器」這條 pin 的**順序不變式**寫成顯式斷言。

    `SentinelArmingCriterionTest::test_this_module_never_reaches_the_real_scheduler`
    也斷言同一件事，但它落在哪裡是**運氣**：兩種載具對**類別**的排序規則不同——unittest
    依類名字母序（`SentinelArmingCriterionTest` 的 `S` 早於 `TraceIsolationTest` 的 `T`
    ⇒ 那支守衛跑在巢狀 runner 之前，量到的是「還沒被沖掉」的狀態），pytest 依**定義
    順序**（`TraceIsolationTest` 定義在前 ⇒ 它先跑，pin 當場消失，那支守衛才紅）。
    本類的兩個座標刻意同時滿足兩種規則：類名以 `Z` 開頭、定義位置緊接在
    `TraceIsolationTest` 之後 ⇒ 不論誰跑，這一格都真的落在巢狀 runner 的下游。

    🔴 **方法名也是判準的一部分**：兩種載具對**方法**都是字母序（本輪實測，不是查文件
    得來的）。下面那支紅端自證會在 `finally` 裡把 pin 補回去，所以「pin 還在不在」這一
    格必須排在它**之前**才量得到真東西——第一版把它取名 `test_the_pin_...`（`t` > `r`）
    ⇒ 在拿掉修法的紅端演練裡它照樣是綠的（實測），也就是那一格當時什麼都沒守。
    現名 `test_after_the_nested_runner_the_pin_is_still_up` 以 test_after_ 起頭正是為了
    這件事，改名等於改判準。
    """

    def test_after_the_nested_runner_the_pin_is_still_up(self) -> None:
        self.assertEqual(os.environ.get(guard.SENTINEL_OFF_ENV), "1",
                         "巢狀 runner 之後 pin 不見了 ⇒ 本模組後半段的每一支測試都可能"
                         "在開發者機器上註冊一支永遠沒人收的 launchd job")

    def test_red_a_raw_nested_runner_really_does_flush_the_module_cleanups(self) -> None:
        """自證有牙 ＋ 根因的可執行證據：**不**經 `_run_nested_suite` 就真的會被沖掉。

        載荷刻意就用上面那一格（字母序在本格**之前**，所以它量到的是真狀態）：它在巢狀
        suite 執行**當下**仍然是綠的（flush 發生在 suite 收尾，不是執行中）⇒ 這一條同時
        釘住「失效的時間點在 teardown」這個機制。
        本條若哪天轉紅，代表載具的 module fixture 語意變了，`_run_nested_suite` 的立案
        前提消失——那時要重讀它的 WHY 再決定它還要不要存在，而不是把這一格刪掉。
        """
        suite = unittest.TestLoader().loadTestsFromNames(
            [f"{__name__}.{type(self).__name__}"
             ".test_after_the_nested_runner_the_pin_is_still_up"])
        try:
            unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
            self.assertIsNone(os.environ.get(guard.SENTINEL_OFF_ENV),
                              "巢狀 runner 竟然沒有 flush module cleanup")
        finally:
            _pin_sentinel_off()
            unittest.addModuleCleanup(_unpin_sentinel_off)

    def test_every_nested_runner_in_this_module_goes_through_the_helper(self) -> None:
        """機械物而非自律：下一個人再開一個巢狀 runner 而沒走 helper 時，這一格會紅。

        只靠上面兩格是不夠的——它們量的是「今天這一支」，而缺陷的形狀正是「**任何人都
        可以再開一個**」（同 C3-B 把排程 Action 的射程由一份手寫路徑改成全庫掃描的判例）。
        """
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        owners = [fn.name for fn in ast.walk(tree)
                  if isinstance(fn, ast.FunctionDef)
                  and any(isinstance(c, ast.Call)
                          and getattr(c.func, "attr", "") == "TextTestRunner"
                          for c in ast.walk(fn))]
        self.assertTrue(owners, "一個巢狀 runner 都掃不到 ⇒ 判準空轉（錨漂掉了）")
        allowed = {"_run_nested_suite",       # 唯一的正門
                   # 上面那支紅端自證：它的**主題**就是「不走正門會怎樣」。
                   "test_red_a_raw_nested_runner_really_does_flush_the_module_cleanups"}
        self.assertEqual(
            sorted(set(owners) - allowed), [],
            "有巢狀 runner 沒走 `_run_nested_suite` ⇒ 它會把整個模組的哨兵 pin 沖掉，"
            "而表徵是「某一支不相干的測試在 pytest 下紅、在 unittest 下綠」")


class QuotaUnmeasurableFanoutTest(unittest.TestCase):
    """🔴 R81 收斂（Architect-B1）：「量不到」時**不得**對任意規模的扇出全數放行。

    複審探針實測的缺口（跑 `quota_gate()` 真碼、沙箱 cache/ledger）：快取過期 600s／
    額度 99% ⇒ 42 次 `Agent` 派發**放行 42、擋下 0**；完全沒有快取亦然。成因是唯一的
    刷新呼叫點就在這條「已經量不到」的支線上、且 fire-and-forget 不等它 ⇒ 本次仍判
    「量不到」⇒ 放行。而「過期」是**常態**不是罕見：哨兵巡邏一次都不刷快取、TTL 只有
    180 秒 ⇒ 任何 ≥3 分鐘的非扇出工作之後，下一波扇出整批通過。

    本類的四條刻意涵蓋**兩個方向**：量得到就要擋（前三條），真的量不到又沒有任何證據
    時仍然放行（最後一條）。只鎖前者會讓下一個人用「一律 fail-closed」滿足它，而那正是
    L4 當初被否決的形態（斷網與額度滿了外觀相同）。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="quota-gate-"))
        self.calls: list[int] = []
        for name, value in (("quota_cache_path", lambda: self.tmp / "c.json"),
                            ("fanout_ledger_path", lambda: self.tmp / "l.jsonl"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json"),
                            ("claim_refresh_slot", lambda: True),
                            *_TRACE_ISOLATION(self)):
            self._swap(qg, name, value)
        sink = open(os.devnull, "w", encoding="utf-8")
        self.addCleanup(sink.close)
        self._swap(sys, "stderr", sink)

    def _swap(self, obj: object, name: str, value: object) -> None:
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def _endpoint(self, pct: float | None) -> None:
        """假端點：不碰網路，但把真取數器會做的事做完（寫進 `quota_cache_path()`）。"""
        # R83：簽章要跟著 production 走（多了 `event`）。假的比真的窄時，**受測碼會 TypeError
        # 而不是回答錯**，而那個紅的原因與被測性質無關（同 `_quota_cache` 的 schema 教訓）。
        def fake(timeout: int = qg.QUOTA_SYNC_TIMEOUT_SECONDS, *, event: str = "") -> bool:
            self.calls.append(timeout)
            if pct is None:
                return False
            _quota_cache(self.tmp, pct).replace(qg.quota_cache_path())
            return True
        self._swap(qg, "refresh_quota_blocking", fake)

    def _burst(self, n: int = 42, transcript: str = "") -> int:
        """回「被擋下幾次」。"""
        return sum(_gate({"hook_event_name": "PreToolUse", "tool_name": "Agent",
                          "transcript_path": transcript}) == 2 for _ in range(n))

    def test_a_stale_cache_is_not_a_blanket_allow(self) -> None:
        _quota_cache(self.tmp, 99.0, age=600).replace(qg.quota_cache_path())
        self._endpoint(99.0)
        self.assertEqual(self._burst(), 42, "快取過期 ⇒ 42 個扇出整批通過（缺口原形）")
        self.assertEqual(len(self.calls), 1,
                         "成本必須是「一次呼叫」不是「每次派發一次」——量測是有代價的，"
                         "而 42 次同步網路呼叫會讓這道閘自己被關掉")

    def test_a_missing_cache_is_not_a_blanket_allow(self) -> None:
        self._endpoint(99.0)
        self.assertEqual(self._burst(), 42, "沒有快取 ⇒ 42 個扇出整批通過（缺口原形）")

    def test_a_fresh_cache_never_reaches_for_the_network(self) -> None:
        """控制組：新鮮就直接判，一次都不准碰端點（否則 TTL 這個概念就沒有意義了）。"""
        _quota_cache(self.tmp, 99.0, age=1).replace(qg.quota_cache_path())
        self._endpoint(99.0)
        self.assertEqual((self._burst(), self.calls), (42, []))

    def test_a_dead_endpoint_falls_through_to_the_transcript_floor(self) -> None:
        """L3 地板：ADR §2.1 與 Quota_Review D03 都拿它替 L4 不節流辯護，而
        `quota_gate()` **一次都沒呼叫過** `unhandled_limit_event()` ⇒ 那層地板當時只
        存在於文件裡。這一條是它真的接上的憑證。"""
        main = self.tmp / "sid.jsonl"
        main.write_text("\n".join([
            json.dumps({"type": "assistant", "timestamp": "2026-08-07T18:00:00Z",
                        "message": {"model": "claude-opus-5", "usage": {"input_tokens": 5}}}),
            json.dumps({"type": "assistant", "timestamp": "2026-08-07T18:36:53Z",
                        "message": {"model": guard.SYNTHETIC_MODEL,
                                    "content": [{"text": _REAL_SESSION_LIMIT}]}}),
        ]) + "\n", encoding="utf-8", newline="\n")
        self._endpoint(None)
        self.assertEqual(self._burst(transcript=str(main)), 42)

    def test_a_dead_endpoint_with_no_evidence_falls_back_to_the_degraded_cap(self) -> None:
        """🔴 R82 具名改寫（裁決 D-8，駁回本條 R81 版的斷言）。

        R81 版逐字斷言「真的量不到、又沒有任何撞線證據 ⇒ **仍然放行**」（`_burst() == 0`
        ＝ 42 次全過），理由是「斷網時自動降併發會讓『網路壞了』與『額度真的滿了』外觀
        完全相同」。裁決把那個矛盾拆成三層，各自的失效方向不同：
          · 守衛**行程**：永遠不得崩、不得誤 deny ⇒ fail-open（**這一層一行都沒動**）；
          · **節流決策**：不得靜默全放行 ⇒ 量不到時 `cap = degraded_cap`；
          · **halt 決策**：絕不對沒量到的值開火 ⇒ 量不到時**永不** halt。
        R81 複審探針量到的淨效果就是本條在守的東西反了：過期 600s／額度 99% 時 42 次
        派發放行 42。改判之後 cap 之內仍然全放行（所以「網路壞了 ≠ 停機」還在），
        超出 cap 才擋——而且它**永遠不會變成 0**（`decide` 保證 `>=1`，禁止靜默鎖死）。
        """
        self._endpoint(None)
        cap = quota_policy.DEFAULT_POLICY.degraded_cap
        blocked = self._burst()
        self.assertEqual(blocked, 42 - cap,
                         f"量不到時放行了 {42 - blocked} 次（cap 應為 {cap}）")
        self.assertGreater(42 - blocked, 0, "量不到不得變成靜默鎖死（cap 必須 >0）")


# ═══════════ R81 收斂：**多行程** barrier 回歸鎖（B1／B3）——為什麼不是 Pool.map
# 這一段每一條都 spawn 真的獨立行程，並用**壁鐘 barrier** 把它們對齊到同一瞬間。
# 這不是講究，是量出來的判準差異：
#   · `Pool.map` 的 worker 是**依序**被啟動的（本機實測彼此錯開數十毫秒）⇒「同時碰同
#     一個檔」那件事根本沒發生。SD 對 `claim_refresh_slot` 兩種量法：Pool.map 得到
#     CLAIM=1（看起來完全正確），壁鐘 barrier 得到 **CLAIM=16**（設計意圖 1）。
#     同一支程式、兩個相反的結論——量法選錯就是一條恆綠的鎖。
#   · 執行緒也不行：這兩個缺陷的本體是**跨行程**的檔案語意（Windows CRT 的 append 是
#     使用者態的 seek＋write），同一個行程內的執行緒共用檔案物件，結構上量不到。
#   · 本檔原本的 `FanoutLedgerTest` 是單行程序列呼叫 ⇒ 對這兩個缺陷零鑑別力，而它全綠。
_BARRIER_WORKER = '''\
import json, sys, time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
import context_budget_guard as guard
import quota_gate as qg
def gate(payload):
    return qg.quota_gate(payload, blocking=guard.BLOCKING_TOOLS,
                         latch_read=guard.announced_latches,
                         latch_write=guard.remember_latch,
                         plan_writer=guard.write_resume_plan,
                         waker=guard.arm_quota_wakeup)
job, target, start, count = sys.argv[3], sys.argv[4], float(sys.argv[5]), int(sys.argv[6])
while time.time() < start:      # 壁鐘 barrier：所有行程在同一瞬間被放行
    pass
if job == "dispatch":
    now = datetime.now().astimezone()
    made = sum(qg.claim_dispatch(Path(target), now) is not None for _ in range(count))
    print(made)
elif job == "claim":
    print("CLAIM" if qg.claim_refresh_slot() else "SKIP")
elif job == "gate":
    print(gate({"hook_event_name": "PreToolUse", "tool_name": "Agent",
                "transcript_path": target}))
'''


def _barrier_run(tmp: Path, job: str, target: str, procs: int, each: int = 1,
                 lead: float = 2.0) -> list[str]:
    """`procs` 個獨立行程、壁鐘對齊，回每一個的 stdout（已 strip）。"""
    worker = tmp / "_barrier_worker.py"
    worker.write_text(_BARRIER_WORKER, encoding="utf-8", newline="\n")
    env = _isolated_env(tmp)
    start = str(time.time() + lead)
    argv = [sys.executable, str(worker), str(_HOOK.parent),
            str(_REPO_ROOT / "tools" / "lib"), job, target, start, str(each)]
    running = [subprocess.Popen(argv, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, encoding="utf-8",
                                errors="replace") for _ in range(procs)]
    return [proc.communicate(timeout=180)[0].strip() for proc in running]


class FanoutLedgerConcurrencyTest(unittest.TestCase):
    """🔴 SD-B1：派發帳在併發下掉行／撕行 ⇒ 節流器兩個方向都會錯。

    落地前以同一支 barrier 探針實測（8 行程 × 40 筆＝320）：
      · 舊實作 `path.open("a")`             lines=221 **LOST=99（30.9%）**
      · `os.open` 帶 `os.O_APPEND` ＋單次 `os.write`   lines=281 **LOST=39（12.2%）**
        （SD 建議的修法本身治不好——Windows 的 CRT 把那個旗標實作成使用者態的 seek＋write）
      · `msvcrt.locking(LK_LOCK)`           N=8 時 0，**N=20 時 10 個行程直接死在
        `OSError: Resource deadlock avoided`**（它只重試 10×1 秒）⇒ 鎖自己變成故障源
      · 現行（目錄項＋`O_CREAT|O_EXCL`）     8×40／20×40／42×10 三組皆 **LOST=0 torn=0**
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ledger-mp-"))
        self.root = self.tmp / "dispatch.d"
        self.now = datetime.now(UTC).astimezone()

    def test_a_barrier_aligned_burst_loses_nothing(self) -> None:
        """本鎖的主牙：8 行程 × 40 筆同時寫，一筆都不准掉、一筆都不准撕。"""
        made = sum(int(line) for line in
                   _barrier_run(self.tmp, "dispatch", str(self.root), 8, 40))
        live, unreadable = _ledger().count_dispatches(self.root, 0.0)
        self.assertEqual((made, live, unreadable), (320, 320, 0),
                         f"併發下掉帳／撕帳（記了 {made}、讀回 {live}、讀不懂 {unreadable}）")

    def test_the_counter_is_actually_sensitive_to_a_lost_record(self) -> None:
        """注入組：證明上一條不是恆綠——真的掉了 K 筆時，計數必須跟著少 K。

        刻意用「刪掉 K 個目錄項」而不是「跑一次舊實作看它掉多少」：舊實作的掉行率是
        **平台相依**的（POSIX 的 `O_APPEND` 是核心層原子的，同一段程式在 Linux 上
        LOST=0）⇒ 拿它當注入組會讓這支鎖在 CI 上必紅。判準要綁被守的性質，不要綁一台
        機器的偶然行為（鐵律三）。
        """
        for _ in range(10):
            _ledger().claim_dispatch(self.root, self.now.timestamp())
        for entry in sorted(self.root.iterdir())[:3]:
            entry.unlink()
        self.assertEqual(_ledger().count_dispatches(self.root, 0.0)[0], 7)

    def test_an_unreadable_entry_is_counted_and_announced(self) -> None:
        """SD-B1 required_change ②：讀不懂的記錄不得被靜默跳過。

        舊版 `live_dispatches` 對解析失敗的行 `except ValueError: continue` ⇒ 撕行被
        丟掉、帳目變小，而變小的方向正好是「看起來還有預算」。
        """
        _ledger().claim_dispatch(self.root, self.now.timestamp())
        (self.root / "not-one-of-ours.txt").write_text("x", encoding="utf-8", newline="\n")
        self.assertEqual(_ledger().count_dispatches(self.root, 0.0), (1, 1))
        spoken = _capture_stderr(
            lambda: qg.live_dispatches(self.root, self.now), self.tmp)
        self.assertIn("讀不懂", spoken, "撕帳被靜默吞掉了")

    def test_a_denied_call_hands_its_budget_straight_back(self) -> None:
        """SA-B6 的新形態：撤銷是 `unlink` 自己那一個目錄項，不是第二次 append。"""
        kept = [_ledger().claim_dispatch(self.root, self.now.timestamp())
                for _ in range(2)]
        for _ in range(20):
            entry = _ledger().claim_dispatch(self.root, self.now.timestamp())
            self.assertTrue(_ledger().release_dispatch(entry))
        self.assertEqual(qg.live_dispatches(self.root, self.now), len(kept))

    def test_the_window_rolls_and_prunes(self) -> None:
        old = self.now.timestamp() - qg.FANOUT_WINDOW_SECONDS - 10
        for _ in range(9):
            _ledger().claim_dispatch(self.root, old)
        self.assertEqual(qg.live_dispatches(self.root, self.now), 0)
        self.assertEqual(list(self.root.iterdir()), [],
                         "滾出視窗的目錄項沒有被清掉 ⇒ append-only 會永遠長大")


class PhantomCountNoLongerBlocksTest(unittest.TestCase):
    """🔴 SD-B1 的**端到端**那一半：幽靈計數會把遠低於 cap 的一次派發擋下來。

    SD 實測（合成 90% 快取、20 個平行 Agent）：帳本 `try=20 undo=17`（各應為 20）⇒
    `live_dispatches()` 讀回 **3**，而 cap=2、設計意圖 0 ⇒ 接著單獨派 1 個 Agent
    （遠低於 cap）拿到 **rc=2**。這正是 SA-B6 要治的永久過度節流換了成因復發。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="phantom-"))
        self.transcript = str(_write_jsonl(self.tmp / "s.jsonl", [36_000]))
        _quota_cache(self.tmp, 90.0)

    def test_the_ledger_matches_exactly_what_got_through(self) -> None:
        codes = [int(x) for x in
                 _barrier_run(self.tmp, "gate", self.transcript, 20)]
        allowed = codes.count(0)
        self.assertEqual(len(codes), 20)
        live = qg.live_dispatches(self.tmp / qg.FANOUT_LEDGER_NAME,
                                     datetime.now(UTC).astimezone())
        self.assertEqual(live, allowed,
                         f"帳上 {live} 筆、實際放行 {allowed} 次 ⇒ 幽靈計數／掉帳")
        lone = int(_barrier_run(self.tmp, "gate", self.transcript, 1)[0])
        cap = _decision((("session", 90.0, 3600.0),)).cap
        self.assertEqual(lone == 0, live + 1 <= cap,
                         "單獨派 1 個 Agent 的判定與帳上實數不一致 ⇒ 被幽靈計數擋下")


class RefreshSlotConcurrencyTest(unittest.TestCase):
    """🔴 SD-B3：成本節流器在它**唯一要治的情境**下完全失效。

    落地前實測（16 個獨立行程、壁鐘 barrier）：**CLAIM=16 SKIP=0**，設計意圖 1
    ⇒ 一則訊息平行派 42 個 Agent、快取剛過期時，42 個 hook 各自同步打一次端點。
    根因是 check-then-act（先 `is_file()`＋比 mtime，再 `write_text`），零原子性。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="claim-mp-"))

    def test_exactly_one_of_sixteen_wins_the_ttl_slot(self) -> None:
        out = _barrier_run(self.tmp, "claim", str(self.tmp / "unused"), 16)
        self.assertEqual((out.count("CLAIM"), out.count("SKIP")), (1, 15),
                         f"同一個 TTL 視窗內有 {out.count('CLAIM')} 個行程同時打端點")

    def test_the_slot_reopens_after_the_ttl(self) -> None:
        """反向對照：只鎖「搶不到」不鎖「到期換屆」，會做出一個永遠不再刷新的節流器。"""
        stamp = self.tmp / "s.stamp"
        self.assertTrue(_ledger().claim_once(stamp, 60.0, now=1000.0))
        self.assertFalse(_ledger().claim_once(stamp, 60.0, now=1000.0))
        self.assertTrue(_ledger().claim_once(stamp, 60.0, now=1e12),
                        "TTL 過了還搶不到 ⇒ 這個節流器會把刷新永久關掉")


class FanoutLedgerTest(unittest.TestCase):
    """SA-B6：帳是 per-account 的一份，且壞掉的帳不得被讀成「擋下來」。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.ledger = self.tmp / "ledger.jsonl"
        self.now = datetime.now(UTC).astimezone()

    def test_the_ledger_has_no_session_id_in_it(self) -> None:
        """額度是 per-account 的單一池；per-sid 的帳等於 N 個載體各拿一份 cap。"""
        self.assertEqual(qg.fanout_ledger_path().name, qg.FANOUT_LEDGER_NAME)
        self.assertNotIn("{", qg.FANOUT_LEDGER_NAME)
        # R82／Q2-02：掃描面跟著實作搬到 `tools/lib/quota_gate.py`——留在 hook 上會讓
        # `source.index(...)` 直接 ValueError，而那是**恆紅**，與恆綠一樣沒有鑑別力。
        source = _QUOTA_GATE.read_text(encoding="utf-8")
        body = source[source.index("def fanout_ledger_path"):]
        body = body[:body.index("\ndef ", 1)]
        self.assertNotIn("session_id", body, "帳檔名帶了 session id ⇒ 單位與額度不匹配")

    def test_a_corrupt_ledger_reads_as_zero_not_as_a_block(self) -> None:
        self.ledger.write_text("{\nnot json\n", encoding="utf-8", newline="\n")
        self.assertEqual(qg.live_dispatches(self.ledger, self.now), 0)


class QuotaGateIsIndependentOfContextTest(unittest.TestCase):
    """🔴 SA-B1：本包唯一存在理由的那個場景——**低 context × 高 quota**。

    ADR 原設計把 quota 分支放進 `block_verdict()`，而 `main()` 在呼叫它之前有五道
    context 語意的早退（`tier_of` 在 context <75% 回 `None` ⇒ `return 0`）。撞額度那
    一刻 context 只有 ~18~20% ⇒ 那段程式**永遠跑不到**。沒有下面這組低-context 注入，
    任何「80% 擋得住」的判準在真實故障場景下都恆綠。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        # 18% context：遠低於 WARN_RATIO(0.75) ⇒ 走 context 那條路一定 `return 0`。
        self.transcript = _write_jsonl(self.tmp / "s.jsonl", [36_000])

    def _call(self, tool: str = "Agent") -> tuple[int, str]:
        return _run_hook({"hook_event_name": "PreToolUse", "tool_name": tool,
                          "transcript_path": str(self.transcript)}, self.tmp)

    def test_the_context_axis_alone_would_let_this_through(self) -> None:
        """控制組：先證明這份逐字稿在 context 那把尺下確實是「什麼都不做」。"""
        used, peak, _ = guard.scan_transcript(self.transcript)
        self.assertLess(used / guard.CONSERVATIVE_WINDOW, guard.WARN_RATIO)
        self.assertIsNone(guard.tier_of(used, guard.CONSERVATIVE_WINDOW))
        _quota_cache(self.tmp, 50.0)
        self.assertEqual(self._call()[0], 0)

    def test_quota_85_blocks_a_fanout_call_at_18_percent_context(self) -> None:
        _quota_cache(self.tmp, 85.0)
        for _ in range(_decision((("session", 85.0, 3600.0),)).cap):
            self.assertEqual(self._call()[0], 0, "節流帶的前幾次派發應該放行")
        rc, err = self._call()
        self.assertEqual(rc, 2, "quota=85 × 超出預算 ⇒ 那次工具呼叫必須不發生")
        self.assertIn("少派 agent", err)

    def test_quota_20_never_blocks_however_many_times(self) -> None:
        """反向對照：只測「擋得住」不測「不亂擋」的鎖沒有鑑別力。

        🔴 R82 把水位由 50 改成 20：50 現在**恰好是** notice 帶的下緣（使用者原文
        「50% 就要開始注意、少派」），拿邊界值當「絕不擋」的對照組會讓這一條同時在測
        兩件事。20 落在 free 帶正中央，cap 是 `None`＝真的不設限，鑑別力沒有變。
        """
        _quota_cache(self.tmp, 20.0)
        self.assertIsNone(_decision((("session", 20.0, 3600.0),)).cap)
        for i in range(8):
            self.assertEqual(self._call()[0], 0, f"第 {i + 1} 次被誤擋了")

    def test_quota_96_blocks_the_very_first_call(self) -> None:
        _quota_cache(self.tmp, 96.0, kind="weekly_all", resets_in=6 * 86400)
        rc, err = self._call()
        self.assertEqual(rc, 2)
        self.assertIn("停止派發", err)
        self.assertIn("刻意不排程", err, "週額度那一條被排程了 ⇒ 七天後才響")

    def test_halt_writes_a_resume_plan_to_disk(self) -> None:
        """95% 的動作要**真的發生**：任務書落磁碟，不是印一行字給模型看。"""
        _quota_cache(self.tmp, 97.0, kind="weekly_all", resets_in=6 * 86400)
        self.assertEqual(self._call()[0], 2)
        plans = list(self.tmp.glob(f"{guard.PLAN_PREFIX}*.md"))
        self.assertTrue(plans, "95% 閂鎖沒有把任務書寫到磁碟上")
        self.assertIn("可重啟點任務書", plans[0].read_text(encoding="utf-8"))

    def test_denied_calls_do_not_leak_into_the_real_ledger(self) -> None:
        """🔴 SA-B6 的**端到端**版（純函式版對這個缺陷零鑑別力，本包注入實測坐實）。

        `FanoutLedgerTest` 那幾條是自己呼叫 `append_dispatch` 造帳，所以把 deny 路徑上
        那一行 `undo` 拿掉時它們照樣全綠——鎖在守的是輔助函式，不是**真的走過的那條路**。
        這一條改成真跑 hook：節流帶裡先用滿預算、再被擋 K 次，然後直接量真實帳檔。
        洩漏時它會讀到 cap+K（＝一旦到 cap 就永遠回不來，即使 quota 掉回 50）。
        """
        _quota_cache(self.tmp, 85.0)
        cap = _decision((("session", 85.0, 3600.0),)).cap
        for _ in range(cap):
            self.assertEqual(self._call()[0], 0)
        denied = 5
        for _ in range(denied):
            self.assertEqual(self._call()[0], 2)
        live = qg.live_dispatches(self.tmp / qg.FANOUT_LEDGER_NAME,
                                     datetime.now(UTC).astimezone())
        self.assertEqual(live, cap,
                         f"被擋下的 {denied} 次留在帳上了（讀到 {live}）⇒ 永久過度節流")

    def test_non_fanout_tools_are_never_touched(self) -> None:
        """收斂（讀檔／寫檔／跑 git）必須還做得到——擋到讓人無法收斂的守衛會被整個關掉。"""
        _quota_cache(self.tmp, 99.0)
        for tool in ("Read", "Edit", "PowerShell", "Write"):
            with self.subTest(tool=tool):
                self.assertEqual(self._call(tool)[0], 0)

    def test_the_escape_hatch_is_its_own_switch(self) -> None:
        """三個逃生口關掉的是三件不同的事，共用一個會讓人順手關掉另外兩層。"""
        self.assertNotIn(qg.QUOTA_OFF_ENV, (guard.GUARD_OFF_ENV, guard.SENTINEL_OFF_ENV))
        _quota_cache(self.tmp, 99.0)
        env_payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent",
                       "transcript_path": str(self.transcript)}
        env = _isolated_env(self.tmp)
        env[qg.QUOTA_OFF_ENV] = "1"
        proc = subprocess.run([sys.executable, str(_HOOK)],
                              input=json.dumps(env_payload), env=env, capture_output=True,
                              encoding="utf-8", errors="replace", timeout=180, check=False)
        self.assertEqual(proc.returncode, 0)

    def test_the_gate_is_evaluated_before_the_context_early_returns(self) -> None:
        """原始碼級的釘子：`quota_gate` 的呼叫必須排在那五道早退**之前**。

        沒有這一條時，未來有人把它往下搬一行就會讓整段變成死碼，而所有 e2e 仍然綠
        （因為合成逐字稿可以剛好走得到）——那正是 SA-B1 抓到的形態。
        """
        source = _HOOK.read_text(encoding="utf-8")
        body = source[source.index("def main()"):source.index("def block_verdict")]
        # 🔴 先剝掉註解行再找位置。第一版沒剝，於是**我自己寫在那一行上方解釋這件事的
        # 註解**（裡面逐字提到 `tier_of()`）就成了第一個命中點，判準當場誤紅。
        # 這正是本 repo 反覆判過的「掃描器把說明文字當程式碼」——只是這次它抓到的是我。
        body = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("#"))
        self.assertLess(body.index("quota_gate("), body.index("transcript_path"),
                        "quota_gate 被排到 context 早退之後了 ⇒ 低 context 時是死碼")
        # `may_block(` 刻意不在這一組：它住在 `block_verdict()` 裡、根本不在 `main()` 的
        # 射程內，硬塞進來只會讓判準因為「找不到子字串」而 ValueError（＝一條分母為 0 的鎖）。
        for marker in (r"\btier_of\(", r"\bused is None"):
            with self.subTest(marker=marker):
                hit = re.search(marker, body)
                self.assertIsNotNone(hit, f"main() 裡找不到 context 早退標記 {marker}")
                self.assertLess(body.index("quota_gate("), hit.start())


class QuotaDenominatorTest(unittest.TestCase):
    """SA-B2：口徑**從 payload 推導**，不得是一句對所有帳號都宣稱為真的散文。"""

    def test_the_denominator_is_read_out_of_the_payload(self) -> None:
        meter = _meter()
        disclosed = meter.denominator_of(
            {"five_hour": {"limit_dollars": 200.0, "used_dollars": 50.0,
                           "utilization": 25.0}})
        self.assertEqual(disclosed["kind"], "usd")
        self.assertIn("200.0", disclosed["text"])
        self.assertTrue(disclosed["cross_check"]["agrees"])

    def test_a_null_denominator_says_so_instead_of_claiming_none_exists(self) -> None:
        meter = _meter()
        undisclosed = meter.denominator_of(
            {"five_hour": {"limit_dollars": None, "used_dollars": None}})
        self.assertEqual(undisclosed["kind"], "undisclosed")
        self.assertIsNone(undisclosed["cross_check"])

    def test_a_disagreeing_utilization_is_detectable(self) -> None:
        """交叉核對存在的理由：讓 utilization 壞掉／過期變成**可偵測**而非靜默採信。"""
        meter = _meter()
        checked = meter.denominator_of(
            {"five_hour": {"limit_dollars": 100.0, "used_dollars": 90.0,
                           "utilization": 12.0}})
        self.assertFalse(checked["cross_check"]["agrees"])

    def test_schema_drift_is_recorded(self) -> None:
        """SA-N09：新桶滿了而我們看不到是靜默的 ⇒ 頂層鍵集合的變動必須被記下來。"""
        meter = _meter()
        self.assertEqual(
            meter.drift_against({"schema_keys": ["a", "b"]}, {"schema_keys": ["a", "b", "z"]}),
            ["z"])
        self.assertEqual(meter.drift_against(None, {"schema_keys": ["a"]}), [])


class WorkflowFanoutIsOutOfReachTest(unittest.TestCase):
    """🔴 SD-B1：把量到的失明面釘成政策，而不是留一句「擋得住」的假話。

    本包當回合實測（`~/.claude/projects/d--CursorProject-AISDCL-Agent/`）：
      · `Workflow` 的 tool_result **47/47** 是「Workflow launched in background」
        ⇒ 那次呼叫在內部 agent 生出來之前就結束，用 Pre/Post 配對算 in-flight 恆讀 ≈0；
      · `%TEMP%` 的 19 支 `autosdd_sentinel_boot_*.log` **沒有一支**的 sid 長得像 subagent
        ⇒ SessionStart 對 workflow 內部 agent 一次都沒觸發過；
      · 但 subagent 逐字稿裡 `PreToolUse:` 命中 136 次 ⇒ 那些 agent **自己的**工具呼叫會跑本 hook。
    ⇒ 一次 `Workflow` 啟動是事後界不住的扇出，節流帶唯一誠實的處置是不讓它啟動。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.transcript = _write_jsonl(self.tmp / "s.jsonl", [36_000])

    def test_workflow_is_denied_in_the_throttle_band_even_on_the_first_call(self) -> None:
        _quota_cache(self.tmp, 85.0)
        rc, err = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Workflow",
                             "transcript_path": str(self.transcript)}, self.tmp)
        self.assertEqual(rc, 2)
        self.assertIn("數不到", err, "訊息必須說出理由是『界不住』而不是『太多』")

    def test_agent_is_still_allowed_up_to_the_cap(self) -> None:
        """對照組：政策只針對**界不住**的那一個，不是把節流帶變成全面停機。"""
        _quota_cache(self.tmp, 85.0)
        rc, _ = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Agent",
                           "transcript_path": str(self.transcript)}, self.tmp)
        self.assertEqual(rc, 0)

    def test_the_unbounded_set_is_a_subset_of_the_blocking_set(self) -> None:
        self.assertTrue(set(qg.UNBOUNDED_FANOUT_TOOLS) <= set(guard.BLOCKING_TOOLS))


# ══════════════════════ R82／HELM-04：判讀層接線（M1／M7／M10 ＋ 訴求 6c 的 .env）
class QuotaDecisionEntryIsSingleTest(unittest.TestCase):
    """🔴 M10：「函式對了但沒人叫它」＝本 repo 反覆記載的『機制蓋好沒接電』。

    判讀層（`quota_policy`）自己的 90 條測試對這個形態**零鑑別力**：把 `quota_gate()`
    改回一支自己推導 cap 的私有函式，那 90 條照樣全綠。所以接線那一半只能在這裡鎖。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="quota-entry-"))
        self.transcript = str(_write_jsonl(self.tmp / "s.jsonl", [36_000]))
        for name, value in (("quota_cache_path", lambda: self.tmp / "c.json"),
                            ("fanout_ledger_path", lambda: self.tmp / "l.d"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json"),
                            ("claim_refresh_slot", lambda: False),
                            *_TRACE_ISOLATION(self)):
            self._swap(qg, name, value)
        sink = open(os.devnull, "w", encoding="utf-8")
        self.addCleanup(sink.close)
        self._swap(sys, "stderr", sink)

    def _swap(self, obj: object, name: str, value: object) -> None:
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def _payload(self, tool: str = "Agent") -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": tool,
                "transcript_path": self.transcript}

    def test_the_gate_calls_decide_exactly_once(self) -> None:
        """注入自證：把 `quota_gate` 改回 `fanout_cap(reading["pct"])` ⇒ spy 0 次即紅。

        「恰好一次」兩個方向都有意義：0 次＝判讀層根本沒接電；≥2 次＝同一次工具呼叫
        有兩條各自求值的路徑，而它們遲早會給出不同答案（本 repo 的「兩個家」頭號病）。
        """
        _quota_cache(self.tmp, 85.0).replace(qg.quota_cache_path())
        calls = []
        real = quota_policy.decide

        def spy(state, now, policy):
            calls.append(state)
            return real(state, now, policy)

        self._swap(quota_policy, "decide", spy)
        _gate(self._payload())
        self.assertEqual(len(calls), 1, f"decide 被呼叫 {len(calls)} 次")

    def test_reset_branch_is_fed_the_binding_axis_not_the_loudest_one(self) -> None:
        """🔴 M10 下半：`reset_branch` 吃錯軸 ⇒ 排程動作與訊息一起錯，而痕跡全綠。

        注入的是規格點名的那一組：`session 96%@+10min`（近在眼前、該 `arm`）＋
        `weekly_all 30%@+6d`。修前餵的是 `worst()` 挑的那一桶；若改餵 weekly 的
        `resets_at`，分支會翻成 `notify`（「等沒有意義」）而喚醒**不會被武裝**。
        """
        decision = _decision((("session", 96.0, 600.0), ("weekly_all", 30.0, 6 * 86400.0)))
        self.assertEqual(decision.binding.kind, "session")
        now = datetime.now(UTC).astimezone()
        self.assertEqual(qg.reset_branch(qg.binding_resets_at(decision), now),
                         qg.QUOTA_BRANCH_ARM)
        # 反證：餵另一軸就會翻面 ⇒ 上面那一行不是恆真。
        weekly = next(r.axis for r in decision.per_axis if r.axis.kind == "weekly_all")
        self.assertEqual(qg.reset_branch(weekly.resets_at, now), qg.QUOTA_BRANCH_NOTIFY)

    def test_two_opposite_shapes_reach_the_gate_with_different_caps(self) -> None:
        """🔴 M1 的**端到端**半：A/B 兩組必須在**穿過快取檔之後**仍然分得開。

        判讀層測得到 `cap(A) > cap(B)`，但那證明不了快取有把兩條軸都帶過來——舊形狀
        只寫得下一組頂層 `{pct, kind, resets_at}`，A 與 B 在磁碟上會長得一模一樣。
        """
        now = datetime.now(UTC).astimezone()
        caps = {}
        # 🔴 兩組刻意都用 90（prepare 帶）而不是 96：96 ≥ halt 門檻，兩組會**同時**拿到
        # cap 0，於是 `A > B` 恆假——那不是缺陷，是把注入點放到了「halt 一票否決」那一格
        # 上，判準對 horizon 就再也沒有鑑別力（第一版實測 `0 not greater than 0`）。
        for label, (main, other) in {
                "A": ((90.0, 34 * 60.0), (20.0, 6 * 86400.0)),
                "B": ((10.0, 34 * 60.0), (90.0, 6 * 86400.0))}.items():
            path = _quota_cache(self.tmp, main[0], kind="session", resets_in=main[1],
                                extra=(("weekly_all", other[0], other[1]),))
            state = qg.read_quota(now, path)
            self.assertEqual(len(state.axes), 2, "快取只留下一條軸 ⇒ 二元組又被壓成純量")
            caps[label] = quota_policy.decide(state, now, quota_policy.DEFAULT_POLICY)
        self.assertGreater(caps["A"].cap, caps["B"].cap,
                           "短期程高水位與長期程高水位拿到同一個 cap ⇒ 6b 沒有接上")
        self.assertEqual((caps["A"].binding.kind, caps["B"].binding.kind),
                         ("session", "weekly_all"))

    def test_a_notice_band_never_locks_workflow_out(self) -> None:
        """🔴 訴求 6b 的副作用鎖：`Workflow` 的判準不得退化成「不是 free 帶就擋」。

        舊判準是「tier != normal ⇒ 擋」。新階梯下 55% 已經不是 free 帶了，照舊判準會
        在一個**還很寬鬆**的水位把批次編排整個鎖死。判準改成「cap 已收斂到 converge
        檔以下才擋」，所以這一條與下一條必須方向相反。
        """
        _quota_cache(self.tmp, 55.0).replace(qg.quota_cache_path())
        self.assertEqual(_gate(self._payload("Workflow")), 0)

    def test_the_prepare_band_still_stops_workflow(self) -> None:
        """對照組：真的收斂到 prepare 帶時仍然擋——只鎖「不亂擋」會做出一道空轉的閘。"""
        _quota_cache(self.tmp, 88.0).replace(qg.quota_cache_path())
        self.assertEqual(_gate(self._payload("Workflow")), 2)


class QuotaMessagesNameTheAxisTest(unittest.TestCase):
    """🔴 M7：每一個印出去的百分比都必須指名桶名與剩餘分鐘。

    裸的「額度水位 54%」正是掌舵者當場誤讀的**那個**形狀——它之所以會被誤讀，就是因為
    那個數字沒有說自己是哪一桶、什麼時候 reset。本類掃訊息裡的每一個 `\\d+%`。
    """

    _PCT = re.compile(r"\d+(?:\.\d+)?\s*%")

    def _assert_every_pct_is_qualified(self, text: str) -> None:
        self.assertTrue(self._PCT.search(text), f"這則訊息一個百分比都沒有：{text[:120]}")
        for segment in re.split(r"[；\n]", text):
            if not self._PCT.search(segment):
                continue
            self.assertIn("kind=", segment, f"裸百分比（沒說是哪一桶）：{segment}")
            self.assertTrue("分鐘" in segment or "reset 距離不明" in segment,
                            f"裸百分比（沒說還有多久 reset）：{segment}")

    def test_the_halt_message_qualifies_every_percentage(self) -> None:
        decision = _decision((("session", 96.0, 600.0), ("weekly_all", 57.0, 6 * 86400.0)))
        text = qg.quota_halt_message(decision, {
            "plan": "P", "kind": "session", "branch": qg.QUOTA_BRANCH_ARM,
            "armed": True, "sentinel_off": False, "posix": False})
        self._assert_every_pct_is_qualified(text)

    def test_the_throttle_message_qualifies_every_percentage(self) -> None:
        decision = _decision((("session", 88.0, 3600.0), ("weekly_all", 57.0, 6 * 86400.0)))
        for tool in ("Agent", "Workflow"):
            with self.subTest(tool=tool):
                self._assert_every_pct_is_qualified(
                    qg.quota_throttle_message(decision, tool, 2,
                                              datetime.now(UTC).astimezone()))

    def test_every_axis_is_mentioned_not_only_the_binding_one(self) -> None:
        """加碼：兩軸同時 halt 時**兩軸都要說**（舊訊息只渲染 `worst()` 那一格）。"""
        decision = _decision((("session", 99.0, 600.0), ("weekly_all", 97.0, 6 * 86400.0)))
        text = qg.quota_halt_message(decision, {
            "plan": "P", "kind": "session", "branch": qg.QUOTA_BRANCH_ARM,
            "armed": True, "sentinel_off": False, "posix": False})
        for kind in ("session", "weekly_all"):
            self.assertIn(f"kind={kind}", text, "只說了最緊的那一軸 ⇒ 讀者看不到全貌")

    def test_the_judge_catches_a_bare_percentage(self) -> None:
        """判準自證：貼回舊形狀的第一行 ⇒ 必紅（否則這一類只是在數 `%` 這個字）。"""
        with self.assertRaises(AssertionError):
            self._assert_every_pct_is_qualified("🔴 額度水位 54.0%（≥95%）⇒ 停止派發。")


class QuotaEnvFileIsActuallyLoadedTest(unittest.TestCase):
    """🔴 訴求 6c：`.env.example` 列出來的鍵必須**真的生效**。

    立案（複驗鏡實測）：全 repo 沒有任何 `.env` 載入器 ⇒ 使用者照著範例把值寫進 `.env`
    之後沒有東西會去讀它，而「設了沒生效」與「設了而且生效」在行為上完全相同。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="quota-env-"))

    def _with_dotenv(self, body: str) -> dict:
        """把 `policy_env()` 指到沙箱裡的一份 `.env`，回它讀出來的 mapping。"""
        env_file = self.tmp / ".env"
        env_file.write_text(body, encoding="utf-8", newline="\n")
        real_open = Path.read_text

        def fake(this: Path, *a, **kw):
            return real_open(env_file if this.name == ".env" else this, *a, **kw)

        with unittest.mock.patch.object(Path, "read_text", fake):
            return qg.policy_env()

    def test_a_value_written_into_dotenv_reaches_the_policy(self) -> None:
        merged = self._with_dotenv("# 註解不算\nAUTOSDD_QUOTA_HALT_PCT=88\n\n")
        self.assertEqual(merged.get("AUTOSDD_QUOTA_HALT_PCT"), "88")
        policy, problems = quota_policy.load_policy(merged)
        self.assertEqual((problems, policy.halt_pct), ([], 88.0))
        self.assertEqual(quota_policy.pct_band(89, policy), quota_policy.BAND_HALT)

    def test_the_real_environment_wins_over_the_file(self) -> None:
        """優先序（env > 檔案）：否則一份忘了改的 `.env` 會靜默吃掉臨時覆寫。"""
        with unittest.mock.patch.dict(os.environ,
                                      {"AUTOSDD_QUOTA_HALT_PCT": "77"}, clear=False):
            merged = self._with_dotenv("AUTOSDD_QUOTA_HALT_PCT=88\n")
        self.assertEqual(merged.get("AUTOSDD_QUOTA_HALT_PCT"), "77")

    def test_a_missing_dotenv_is_not_a_failure(self) -> None:
        """額度守衛不得因為缺一個**選配**檔就變成故障源（fail-open 是 P0）。"""
        self.assertEqual(qg.policy_env().get("PATH"), os.environ.get("PATH"))

    def test_a_bad_value_is_loud_not_silent(self) -> None:
        """設錯必須出聲一次：`load_policy` 退回預設，而退回本身是完全看不見的。"""
        _, problems = quota_policy.load_policy(
            self._with_dotenv("AUTOSDD_QUOTA_HALT_PCT=abc\n"))
        self.assertTrue(problems, "壞值被靜默吞掉 ⇒ 使用者以為設定生效了")

    def test_the_shipped_example_is_the_generated_one(self) -> None:
        """`.env.example` 是**生成物**：手寫一份就是讓同一份知識住兩個家（R73 判例）。"""
        text = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertEqual(quota_policy.env_example_problems(text), [])

    def test_every_key_in_the_example_is_one_the_code_reads(self) -> None:
        """雙向鎖的另一半：範例檔的每個鍵都必須真的有讀取點（防幽靈鍵）。

        `AutoClaude/.env.example` 檔內自己記載過 improving_92 清掉一批「宣告了但程式
        從未讀取」的鍵——那正是這一條在防的形態。
        """
        declared = {spec.name for spec in quota_policy.ENV_SPEC}
        text = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        keys = {ln.split("=", 1)[0].strip() for ln in text.splitlines()
                if ln.strip() and not ln.strip().startswith("#") and "=" in ln}
        self.assertEqual(keys - declared, set(), "範例檔有 ENV_SPEC 沒有的幽靈鍵")
        # 🔴 判準刻意**不**掃 `quota_policy.py` 自己：ENV_SPEC 就住在那裡，拿它當「有人讀」
        # 的證據會讓這一條對每一個鍵恆真（分母 = 全集的鎖恆綠）。要的是**消費者**存在。
        consumers = "".join(p.read_text(encoding="utf-8") for p in (
            _QUOTA_GATE, _HOOK, _REPO_ROOT / "tools" / "session_resume_planner.py"))
        fields = set(quota_policy.Policy.__dataclass_fields__)
        for spec in quota_policy.ENV_SPEC:
            with self.subTest(key=spec.name):
                if spec.attr is not None:
                    self.assertIn(spec.attr, fields,
                                  f"{spec.name} 對應的 Policy 欄位不存在 ⇒ 讀了也沒有用")
                else:
                    self.assertIn(spec.name, consumers,
                                  f"{spec.name} 是逃生口卻沒有任何讀取點（幽靈鍵）")


class _FakeMeter:
    """`quota_meter` 的替身：只回答 `measure_detail`，不碰網路。"""

    SCHEMA = _meter().SCHEMA   # 契約字面只有一個家（見 `_quota_cache` 的 WHY）

    def __init__(self, reason: str, reading: dict | None = None) -> None:
        self.reason, self.reading, self.cache = reason, reading, Path()

    def measure_detail(self, timeout: int = 4) -> tuple[dict | None, str]:
        return self.reading, self.reason

    def write_cache(self, reading: dict, path: Path) -> bool:
        path.write_text(json.dumps(reading), encoding="utf-8", newline="\n")
        return True

    def cache_path(self) -> Path:
        return self.cache


class QuotaDegradationIsAudibleTest(unittest.TestCase):
    """🔴 SD-B2：額度軸「量不到」時**完全靜默**，`QUOTA_UNMEASURABLE` 在 production 是死碼。

    落地前實測（同一支注入探針，四種失效各注入一次；控制組在第一列）：
        (a) 99% 快取 ＋ meter 正常          → rc=2  stderr 173b   痕跡 —
        (b) meter 不可達                    → rc=0  stderr **0b**  痕跡 **無**
        (c) schema 被 bump                  → rc=0  stderr **0b**  痕跡 **無**
        (d) 快取過期 600s                   → rc=0  stderr **0b**  痕跡 **無**
        (e) 完全沒有快取                    → rc=0  stderr **0b**  痕跡 **無**
    根因：`quota_gate()` 在 `pct is None` 且無地板時直接 `return 0`，**而且是在
    `quota_tier_of()` 被呼叫之前** ⇒ 全 repo `QUOTA_UNMEASURABLE` 只出現在常數定義／
    `quota_tier_of`／測試三處，production 一次都到不了。四種失效與「額度很健康」外觀
    完全一致 ⇒ B3／B4 都變成不可偵測。

    🔴 本類**兩個方向都鎖**：量不到要出聲（前幾條），量得到就不准吵（最後兩條）。
    只鎖前者的話，下一個人用「每次都印一行」滿足它，而每次都出聲的守衛會被整個關掉。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="degraded-"))
        self.trace = self.tmp / "trace.jsonl"
        for name, value in (("quota_cache_path", lambda: self.tmp / "c.json"),
                            ("fanout_ledger_path", lambda: self.tmp / "l.d"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json"),
                            ("claim_refresh_slot", lambda: True),
                            ("quota_trace_path", lambda: self.trace),
                            ("degraded_stamp_path",
                             lambda source: self.tmp / f"stamp-{source}")):
            self._swap(qg, name, value)

    def _swap(self, obj: object, name: str, value: object) -> None:
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def _gate(self, reason: str = "meter-unreachable") -> tuple[int, str, list[dict]]:
        """跑真的 `quota_gate()`，回 `(rc, stderr, 這次新增的痕跡列)`。"""
        self._swap(qg, "quota_meter", _FakeMeter(reason))
        before = len(self._trace_lines())
        buf = io.StringIO()
        saved, sys.stderr = sys.stderr, buf
        try:
            rc = _gate({"hook_event_name": "PreToolUse",
                        "tool_name": "Agent", "transcript_path": ""})
        finally:
            sys.stderr = saved
        return rc, buf.getvalue(), self._trace_lines()[before:]

    def _trace_lines(self) -> list[dict]:
        if not self.trace.is_file():
            return []
        return [json.loads(ln) for ln in
                self.trace.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def test_a_dead_meter_with_no_cache_says_so(self) -> None:
        rc, err, trace = self._gate()
        self.assertEqual(rc, 0, "L4 的方向沒有變：真的量不到仍然不節流")
        self.assertIn("量不到", err, "斷網與「額度很寬鬆」外觀相同 ⇒ B3/B4 不可偵測")
        self.assertTrue(trace, "沒有留下任何可稽核的痕跡")
        self.assertEqual({r["state"] for r in trace}, {quota_policy.BAND_UNMEASURED},
                         "狀態字沒有進到 production 的痕跡裡 ⇒ 它仍然是死碼")

    def test_each_failure_shape_names_itself(self) -> None:
        """四種失效必須**分得開**——混成一句話等於沒說（ADR §6.3 要求留 `source`）。"""
        cases = {
            "no-cache": (None, "meter-unreachable"),
            # schema 對、但一條軸都讀不出來（`pct` 是字串）⇒ `bad-cache`。刻意**不**用舊
            # 的 `/1` 字面當種子：那會走 `schema-mismatch`，於是這一格其實在測另一件事。
            "bad-cache": (f'{{"schema": "{_meter().SCHEMA}", "axes": [{{"pct": "x"}}]}}',
                          "http-401"),
            "stale-cache": ("stale", "http-500"),
        }
        for expect, (seed, reason) in cases.items():
            with self.subTest(source=expect):
                cache = self.tmp / "c.json"
                cache.unlink(missing_ok=True)
                if seed == "stale":
                    _quota_cache(self.tmp, 99.0, age=600).replace(cache)
                elif seed:
                    cache.write_text(seed, encoding="utf-8", newline="\n")
                _, err, trace = self._gate(reason)
                sources = {r["source"] for r in trace}
                self.assertIn(expect, sources, f"沒說出快取那一端的理由（{sources}）")
                self.assertIn(reason, sources, f"沒說出取數那一端的理由（{sources}）")
                self.assertIn(reason, err)

    def test_a_bumped_schema_is_not_mistaken_for_a_healthy_account(self) -> None:
        """schema 升版時舊快取整份作廢——那是對的，但它必須**說出來**。"""
        (self.tmp / "c.json").write_text(
            json.dumps({"schema": "autosdd.quota/999",
                        "axes": [{"kind": "session", "pct": 99.0, "resets_at": None}],
                        "measured_at": datetime.now(UTC).astimezone().isoformat()}),
            encoding="utf-8", newline="\n")
        rc, err, trace = self._gate("no-buckets")
        self.assertEqual(rc, 0)
        self.assertTrue(trace and err, "schema 升版與『額度很健康』外觀完全相同")

    def test_a_healthy_reading_never_speaks(self) -> None:
        """控制組①：量得到就一個字都不准吵，否則這道守衛會被整個關掉。"""
        _quota_cache(self.tmp, 40.0).replace(self.tmp / "c.json")
        rc, err, trace = self._gate()
        self.assertEqual((rc, err, trace), (0, "", []))

    def test_the_throttle_message_is_not_the_degraded_message(self) -> None:
        """控制組②：真的滿了要走節流那條路（有 pct 的訊息），不是降級那條。"""
        _quota_cache(self.tmp, 99.0).replace(self.tmp / "c.json")
        rc, err, trace = self._gate()
        self.assertEqual((rc, trace), (2, []))
        self.assertIn("停止派發", err)
        self.assertNotIn("量不到", err)

    def test_the_same_source_does_not_shout_on_every_call(self) -> None:
        """出聲要有閂鎖：每次工具呼叫都吵的守衛會被關掉（同 90% 那道的既有判例）。"""
        first, _, _ = self._gate()[0], None, None
        spoken = [self._gate()[1] for _ in range(3)]
        self.assertEqual(first, 0)
        self.assertEqual([s for s in spoken if s], [], "同一個 source 每次都在吵")


#: 憑證來源的**雙欄登記表**（R83）。ONBOARDING §7 那兩欄基線是同一個體例：不把「這台
#: 機器上憑證住哪裡」寫成常數，而是把**每個平台各自的答案**登記下來，兩欄在**任何**主機
#: 上都跑。`platform` 是 `sys.platform` 的字面（`quota_meter.access_token` 的分支讀它）。
#:
#: 🔴 為什麼不是「在 mac 上跳過檔案欄／在 Windows 上跳過 Keychain 欄」：那等於那個平台
#: 的憑證來源永遠沒有覆蓋，而本組要守的性質（「憑證讀不到」與「憑證讀得到但 401」是兩個
#: 分得開的答案）**兩個平台都必須成立**——它正是排程器判斷「要不要繼續等額度回來」的
#: 依據，一邊沒守住就等於那半邊的節流演算法建立在假數字上。
_CRED_COLUMNS = ("win32", "darwin")

#: 形態像真 OAuth token（base64url、無空白、>=20 字元）⇒ 通過 `_keychain_token` 的
#: 裸 token 判準。刻意不是 `"t"`：那個長度連判準的門檻都到不了，會讓 Keychain 欄
#: 「讀得到」那一格其實在測「讀不到」。
_FAKE_TOKEN = "sk-ant-oat01-" + "R82fake" * 5


def _cred_kwargs(test: unittest.TestCase, meter: object, platform: str,
                 readable: bool) -> dict:
    """把 `platform` 那一欄的憑證鋪成「讀得到／讀不到」，回 `measure_detail` 的注入參數。

    兩欄都**不碰主機真正的憑證**：檔案欄一律指到 `mkdtemp` 下的路徑，Keychain 欄一律
    走注入的 runner。這不只是衛生問題——R83 修這一組之前，`darwin` 主機上這組測試每跑
    一次就真的 `security find-generic-password` 讀一次使用者的 login Keychain，於是
    「401 這條臂綠不綠」取決於這台機器有沒有登入過 Claude Code（本機實測：Keychain
    rc=0、有真 token ⇒ 401 那條臂僥倖是綠的；換一台沒登入的 mac 就會紅在
    `no-credentials-darwin`）。判準去讀一個會隨機器變的外部狀態，本身就是缺陷。
    """
    old_creds = meter.CREDENTIALS
    test.addCleanup(setattr, meter, "CREDENTIALS", old_creds)
    missing = Path(tempfile.mkdtemp(prefix="nocreds-")) / "nope.json"

    def trap(argv: list) -> tuple:
        raise AssertionError(f"非 darwin 平台不得去問 Keychain：{argv}")

    if platform == "darwin":
        # 🔴 檔案一律指到不存在的路徑，這**不是佈景而是控制組**：哪天 darwin 分支被改
        # 成（或退回成）讀檔，這一欄的「讀得到」那一格會當場翻成 no-credentials-darwin。
        meter.CREDENTIALS = missing
        blob = json.dumps({"claudeAiOauth": {"accessToken": _FAKE_TOKEN}})
        return {"platform": "darwin",
                "runner": (lambda argv: (0, blob)) if readable
                else (lambda argv: (1, ""))}
    if readable:
        tmp = Path(tempfile.mkdtemp(prefix="creds-")) / "c.json"
        tmp.write_text(json.dumps({"claudeAiOauth": {"accessToken": _FAKE_TOKEN}}),
                       encoding="utf-8", newline="\n")
        meter.CREDENTIALS = tmp
    else:
        meter.CREDENTIALS = missing
    # runner 是**陷阱**：非 mac 那條路一個外部行程都不准起。踩到就是「每次取數多一次
    # subprocess」，而且在沒有 `security` 的機器上那會變成一個只在 CI 上出現的失效。
    return {"platform": "win32", "runner": trap}


def _expected_missing_reason(meter: object, platform: str) -> str:
    """該欄「憑證讀不到」時**應該**叫什麼名字。兩個字面刻意不同，見 `REASON_*` 的 WHY。"""
    return (meter.REASON_NO_CREDENTIALS_DARWIN if platform == "darwin"
            else meter.REASON_NO_CREDENTIALS)


class MeterFailureShapesTest(unittest.TestCase):
    """🔴 SD-B4：`fetch_usage()` 分得出 401 與斷網，而它唯一的呼叫端把 status 丟掉了。

    `quota_meter` 檔頭 §S1-08 逐字要求「401 與『額度真的沒回來』必須在痕跡裡分得開」，
    理由是 OAuth token 4 小時到期、而無人看管那條路上沒有人在 refresh ⇒ 混在一起會讓
    排程器把認證失敗誤判成額度未恢復而一直等下去（R80 哨兵整晚失明同形）。
    落地前實測：憑證讀不到 → `None`；HTTP 401（真連線、0.30s）→ `None`。**同一個答案。**

    🔴 **R83 訂正本 docstring 原本的「誠實劃界」段（不逐字留著當現行說法）**：那段寫
    「`CREDENTIALS` 仍然只有一個來源、零平台分支」，而 R82 同輪就把 darwin 分支落地了
    （`access_token()` 的平台分支，見 `git show HEAD:tools/lib/quota_meter.py`）
    ⇒ 這段自陳從落地當回合起就是假的，且它假在**會讓人以為這裡已經沒有平台問題**的方向。
    真正的缺口是另一件事、而且沒有任何東西在守：`measure_detail()` 當時**沒有憑證來源的
    注入點** ⇒ 本組只能靠改主機自己的憑證存放處來構造那兩條臂，於是每條臂只在一個平台
    成立。mac 真機實測（**R83**＝mac 真機首輪）：把 `CREDENTIALS` 指到不存在的檔，
    darwin 完全不讀它 ⇒ 期望 `no-credentials`、實得 `http-401`，該臂在 mac 上結構性量不到。
    現在改成**雙欄矩陣**（見 `_CRED_COLUMNS`）：兩個平台的憑證來源在任何一台機器上都跑。

    🔴 **上一段的輪號本身被獨立驗證者訂正過一次（R83／PD 複驗，此段留為判例）**：它原本
    把訂正與 mac 真機實測都署名 **R82**，而 R82 收輪 commit（`7975140`）裡這支檔的同一段
    逐字寫著「**我手上沒有 mac 真機**…」，  # stale-premise-ok: R82 原話
    （原話全文：「…非 Windows 的憑證來源未驗，已登記交由下一輪承接」）
    且 `_CRED_COLUMNS`／`_cred_kwargs`／`_FAKE_TOKEN` 在該 commit 內 grep 命中皆為 **0**
    ⇒ 雙欄矩陣與真機實測**都是 R83 的產出**，署名 R82 是把「還沒驗」講成「上一輪驗過了」。
    最難看見的一點：`quota_meter.KEYCHAIN_SERVICE` 上方在 R82 就留了一句預先警告，逐字寫
    「改寫成 R82 就把『還沒在 mac 上驗過』講成『本輪驗過了』，那正是本段在防的假宣稱」
    ——而它預言的事在**下一輪**就真的發生了，只是發生在**另一支檔**，於是那個警告的射程
    （它只寫在 quota_meter 那一行的括號裡）看不到這裡。守輪號的既有鎖
    （`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）判準是 `> current_round()`
    ⇒ **落後方向零覆蓋**，把 R83 的工作署名 R82 一行都不會紅（QA／F-5 同一筆）。
    """

    def _with_fetch(self, status: int, payload: object,
                    platform: str = "win32", readable: bool = True):
        """回 `(meter, kwargs)`；`kwargs` 直接展進 `measure_detail(4, **kwargs)`。"""
        meter = _meter()
        old = meter.fetch_usage
        meter.fetch_usage = lambda token, timeout=10: (status, payload)
        self.addCleanup(setattr, meter, "fetch_usage", old)
        return meter, _cred_kwargs(self, meter, platform, readable)

    def test_unreadable_credentials_and_http_401_are_different_answers(self) -> None:
        """**兩欄都跑**：每個平台各自的憑證來源，兩條臂都要真的量到（見類 docstring）。"""
        for platform in _CRED_COLUMNS:
            with self.subTest(platform=platform):
                meter, creds = self._with_fetch(401, None, platform, readable=True)
                self.assertEqual(meter.measure_detail(4, **creds), (None, "http-401"),
                                 "憑證讀得到卻沒走到 HTTP ⇒ 這一欄的 401 臂量不到")
                _, gone = self._with_fetch(401, None, platform, readable=False)
                missing = _expected_missing_reason(meter, platform)
                self.assertEqual(meter.measure_detail(4, **gone), (None, missing))
                self.assertNotEqual(missing, "http-401")

    def test_a_connection_failure_is_not_an_http_code(self) -> None:
        """`fetch_usage` 用 status 0 表示「連線層就失敗」⇒ 不得被印成 `http-0`。"""
        for platform in _CRED_COLUMNS:
            with self.subTest(platform=platform):
                meter, creds = self._with_fetch(0, None, platform)
                self.assertEqual(meter.measure_detail(4, **creds),
                                 (None, meter.REASON_UNREACHABLE))

    def test_every_http_code_survives_into_the_reason(self) -> None:
        for platform in _CRED_COLUMNS:
            for status in (403, 429, 500, 503):
                with self.subTest(platform=platform, status=status):
                    meter, creds = self._with_fetch(status, None, platform)
                    self.assertEqual(meter.measure_detail(4, **creds)[1],
                                     f"http-{status}")

    def test_a_200_with_no_readable_bucket_is_its_own_shape(self) -> None:
        """200 但一個桶都讀不到，與 401 是不同的病（一個是認證、一個是 schema）。"""
        for platform in _CRED_COLUMNS:
            with self.subTest(platform=platform):
                meter, creds = self._with_fetch(200, {"five_hour": {}}, platform)
                self.assertEqual(meter.measure_detail(4, **creds),
                                 (None, meter.REASON_NO_BUCKETS))

    def test_a_good_reading_carries_ok_and_the_narrow_measure_is_unchanged(self) -> None:
        """既有呼叫端的窄介面不得被改壞——`measure()` 仍然回 dict／None。

        🔴 R82：讀數形狀由頂層 `pct` 純量換成 `axes[]`，斷言跟著換到**每一軸自帶**
        `resets_at` 那一層——那正是該輪的缺陷本體（舊形狀在投影時把它丟掉）。
        🔴 R82：最後那一行驗的是**窄介面**（`measure()` 只吃 timeout、仍回 dict／None，
        新參數沒有改掉它）。它刻意把 `access_token` 換成替身而不是走預設路徑：預設路徑
        在 darwin 上會去讀主機真正的 login Keychain，而判準不得依賴一台機器的登入狀態
        （憑證來源本身的覆蓋在上面的雙欄矩陣，不在這一行）。
        """
        payload = {"five_hour": {"utilization": 61.0, "resets_at": None},
                   "limits": [{"kind": "session", "percent": 61,
                               "resets_at": "2026-08-09T04:59:59+00:00"}]}
        for platform in _CRED_COLUMNS:
            with self.subTest(platform=platform):
                meter, creds = self._with_fetch(200, payload, platform)
                reading, reason = meter.measure_detail(4, **creds)
                self.assertEqual(reason, "ok")
                self.assertEqual(
                    {(a["kind"], a["pct"], a["resets_at"]) for a in reading["axes"]},
                    {("session", 61.0, "2026-08-09T04:59:59+00:00"),
                     ("five_hour", 61.0, None)})
        old_token = meter.access_token
        meter.access_token = lambda *a, **k: _FAKE_TOKEN
        self.addCleanup(setattr, meter, "access_token", old_token)
        self.assertEqual(len(meter.measure(4)["axes"]), 2)

    def test_the_two_platform_columns_are_not_the_same_column(self) -> None:
        """後設鎖：把矩陣退化成「兩欄其實走同一條路」時必紅。

        沒有這一條，上面那些 `for platform in _CRED_COLUMNS` 可以在**兩欄都走檔案**
        （例如有人把 `platform` 參數接掉、或 `_cred_kwargs` 兩欄回同一份 kwargs）
        的情況下全部照樣綠——迴圈跑了兩次、判準沒有鑑別力，這是本 repo 判過的假綠形態。
        """
        meter = _meter()
        mac = _cred_kwargs(self, meter, "darwin", readable=True)
        pc = _cred_kwargs(self, meter, "win32", readable=True)
        self.assertNotEqual(mac["platform"], pc["platform"])
        # Keychain 欄真的會呼叫 runner（拿得到 token）；檔案欄的 runner 是會炸的陷阱，
        # 所以「檔案欄沒有炸」本身就是「它一次都沒去問 Keychain」的證據。
        self.assertEqual(meter.access_token(**mac), _FAKE_TOKEN)
        self.assertEqual(meter.access_token(**pc), _FAKE_TOKEN)
        # 兩欄的「讀不到」必須叫不同的名字，否則 mac 上真正的原因永遠說不出口。
        self.assertNotEqual(_expected_missing_reason(meter, "darwin"),
                            _expected_missing_reason(meter, "win32"))


class ThrottleBandSaysHowLongItLastsTest(unittest.TestCase):
    """SD 非 blocking ①：halt 帶用 `reset_branch` 分得出三支，**throttle 帶完全不分**。

    週額度越 80% 時 cap 會連續套用**好幾天**，與 five_hour 80%（最多 5 小時）代價差一個
    數量級，而訊息裡讀不出差別。本輪只把差別說出來，**不動 cap 的階梯**（那是掌舵者訂的
    政策，挑一個數字塞進來就是本檔一路在治的「挑的不是量出來的」）——已登記交由下一輪
    承接（輪號寫在帳本那一列）。
    """

    def _msg(self, resets_in: float | None) -> str:
        return qg.quota_throttle_message(
            _decision((("weekly_all", 85.0, resets_in),)), "Agent", 2,
            datetime.now(UTC).astimezone())

    def test_the_three_horizons_read_differently(self) -> None:
        near, far, none_at_all = self._msg(3600), self._msg(5 * 86400), self._msg(None)
        self.assertNotEqual({near, far, none_at_all}, {near},
                            "三種 reset 距離的訊息一模一樣 ⇒ 讀者分不出代價差一個數量級")
        self.assertIn("好幾天", far)
        self.assertIn("很快就會自己解除", near)
        self.assertIn("沒有 reset 可以等", none_at_all)

    def test_the_cap_ladder_now_moves_with_the_reset_distance(self) -> None:
        """🔴 R82 具名改寫（本條的 R81 版斷言的正是本輪要拆掉的性質）。

        R81 版是另一個名字（**刻意不逐字反引號寫出**，理由同上一條：那支 test 已不存在，
        指名它會被幽靈符號鎖判紅，而讀者會以為它還在），逐字宣告「本輪刻意**沒有**改階梯：
        訊息變了、政策沒變」，並把 85% 釘死成一個與 reset 距離無關的常數。
        本輪的整件事就是把那個「無關」拿掉（訴求 6b）：同一個 85%，reset 在 1 小時後
        與在 5 天後拿到的 cap 必須不同，且方向是「近的比較寬鬆」。
        halt 帶仍然恰為 0（那一格沒有變，也不吃 horizon 乘數）。

        🔴 **R86 只動中間那一個取樣點（1 小時 → 20 小時），斷言與方向一字未改**：對一個
        **7 天**窗來說「1 小時前」與「10 分鐘前」是同一件事（都 <0.6% 窗長），它們此前被
        讀成兩格只因門檻是絕對分鐘數——那正是缺陷 A。逐項實測與辯護見具名證據檔
        `CrossPlatform_R86_Pace_Calibration.md` §七末段（同上：刻意不寫目錄前綴）。
        """
        near = _decision((("weekly_all", 85.0, 600.0),)).cap
        mid = _decision((("weekly_all", 85.0, 20 * 3600.0),)).cap
        far = _decision((("weekly_all", 85.0, 5 * 86400.0),)).cap
        self.assertGreater(near, mid, "reset 近在眼前卻沒有比較寬鬆 ⇒ 6b 沒有接上")
        self.assertGreater(mid, far, "reset 遠在五天後卻沒有比較緊 ⇒ 6b 沒有接上")
        self.assertEqual(_decision((("weekly_all", 96.0, 3600.0),)).cap, 0)
        self.assertEqual(_decision((("weekly_all", 96.0, 600.0),)).cap, 0,
                         "halt 帶吃了 horizon 乘數 ⇒ 「停止」變成可以被時間放寬")


# ════════════════════════════ R82：HELM-01 載具面／L4-02／L4-03／Q2-01
_ESCALATION_SRC = _REPO_ROOT / "tools" / "lib" / "quota_escalation.py"


def modal_channel_problems(source: str) -> list[str]:
    """通知載具的**形態**判準（空＝通過）。純函式，紅綠由注入自證。

    判的是「這份原始碼裡有沒有任何一條奪焦／要求點擊／會杵在螢幕上的管道」。
    `msg.exe` 是 Windows 上唯一一個會這樣做的內建 CLI 管道，而 R81 版正是用它——
    使用者三度收到的那個十分鐘模態對話框就是 `msg.exe * /TIME:600`。
    """
    problems: list[str] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        code = line.split("#", 1)[0]
        for needle in ("msg.exe", "/TIME:", "MessageBox", "-Confirm:$true"):
            if needle in code:
                problems.append(f"{lineno}: 出現模態管道字面 `{needle}` ⇒ 會奪焦／要求點擊")
    return problems


class NotifyIsNeverModalTest(unittest.TestCase):
    """🔴 HELM-01 的**載具面**：使用者逐字要求「請確認並修正**無彈窗**執行」。

    三件事各自獨立成立，缺一都會讓彈窗以另一種形式回來：①模態管道整條不在原始碼裡；
    ②整條桌面通道**預設關閉**；③開啟時走的是非模態管道（托盤氣球，不奪焦、不要求點擊）。
    """

    def setUp(self) -> None:
        self.calls: list[list[str]] = []
        old = escalation.subprocess.run
        escalation.subprocess.run = self._run
        self.addCleanup(setattr, escalation.subprocess, "run", old)
        os.environ.pop(escalation.NOTIFY_ENV, None)
        self.addCleanup(os.environ.pop, escalation.NOTIFY_ENV, None)

    def _run(self, argv, **kwargs):  # noqa: ANN001, ANN202
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def test_the_modal_channel_is_gone_from_the_source(self) -> None:
        self.assertEqual(
            modal_channel_problems(_ESCALATION_SRC.read_text(encoding="utf-8")), [],
            "模態管道又回到通知載具裡了 ⇒ HELM-01 復發")

    def test_the_scanner_would_actually_catch_it(self) -> None:
        """合成注入（紅）：把 R81 那一行原封不動注回去，判準必須指著它。

        少了這一支，上面那條綠只證明「今天沒有」，不證明「有的時候會被抓到」——
        本 repo 判過的「鎖在、但沒有鑑別力」正是這個形態。
        """
        injected = 'argv = ["msg.exe", "*", "/TIME:600", text]\n'
        problems = modal_channel_problems(injected)
        self.assertTrue(problems, "把模態管道注回去竟然放行 ⇒ 本判準沒有牙齒")
        self.assertIn("msg.exe", problems[0])
        self.assertEqual(modal_channel_problems('# 舊版走的是 msg.exe /TIME:600\n'), [],
                         "註解裡合法地提到它也被判紅 ⇒ 假紅會讓下一個人把判準關掉")

    def test_the_desktop_channel_is_off_by_default(self) -> None:
        """預設就不敲——這是使用者的直接指令，不是可調的偏好。"""
        rc = escalation.notify("t", "b")
        self.assertEqual(rc, escalation.NOTIFY_OFF_RC)
        self.assertEqual(self.calls, [], "開關關著卻仍然起了一支通知行程")

    def test_when_explicitly_enabled_the_channel_is_still_non_modal(self) -> None:
        """開關打開時也不得回到模態：Windows 走托盤氣球（`ShowBalloonTip`）。"""
        os.environ[escalation.NOTIFY_ENV] = "1"
        escalation.notify("AutoSDD 需要你", "月度支出上限")
        self.assertEqual(len(self.calls), 1)
        argv = " ".join(self.calls[0])
        if sys.platform == "win32":
            self.assertIn("ShowBalloonTip", argv)
            self.assertIn("-WindowStyle Hidden", argv)
        self.assertNotIn("msg.exe", argv)

    def test_the_three_silent_outcomes_stay_distinguishable(self) -> None:
        """「開關關著」「沒東西要救」「管道不存在」三者的 rc 必須互不相同。

        混成同一個值時，通知的失效就回到 R81 立案時那個「靜默且事後查不出來」的狀態。
        """
        self.assertEqual(len({escalation.NOTIFY_OFF_RC, escalation.NOTIFY_NO_RESCUE_RC,
                              127, 0}), 4)


class PlanGarbageCollectionTest(unittest.TestCase):
    """HELM-01 的殘骸面：終態收掉自己那一份，另加一個可重跑的年齡門檻。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r82-gc-"))

    def _plan(self, name: str, age_days: float) -> Path:
        path = self.tmp / f"{guard.PLAN_PREFIX}{name}.md"
        path.write_text("# 任務書\n", encoding="utf-8", newline="\n")
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
        return path

    def test_only_the_stale_ones_and_the_current_one_go(self) -> None:
        fresh, stale = self._plan("fresh", 0.0), self._plan("stale", 30.0)
        current = self._plan("current", 0.0)
        audit = escalation.gc_plans(current, root=self.tmp)
        self.assertEqual(audit["gc_plans"], 2)
        self.assertFalse(current.is_file(), "終態沒有收掉自己那一份")
        self.assertFalse(stale.is_file(), "30 天前的殘骸還留著")
        self.assertTrue(fresh.is_file(),
                        "🔴 把還在等的哨兵的任務書一起刪了 ⇒ 續航鏈的地板被自己拆掉")

    def test_a_waiting_sentinel_outlives_a_whole_quota_window(self) -> None:
        """門檻的**方向**：一支還在等額度的哨兵，任務書可能整整 5 小時沒被寫過。

        門檻若短於一個額度視窗，回收器會在最需要那份檔的時候把它刪掉。
        """
        self.assertGreater(escalation.PLAN_GC_AGE_SECONDS, 5 * 3600)

    def test_an_unwritable_victim_never_becomes_a_failure(self) -> None:
        """刪不掉最多是留著：終態路徑上的清理不得反過來變成故障源。"""
        self.assertEqual(escalation.gc_plans(self.tmp / "nope.md", root=self.tmp),
                         {"gc_plans": 0})


class QuotaDegradationReachesTheModelTest(unittest.TestCase):
    """🔴 L4-02：降級**有出聲，但出在一個沒有讀者的通道上**。

    立案（讀碼＋本輪實跑）：`note_degraded()` 寫 stderr，而它唯一的 production 呼叫鏈
    （`quota_gate()` 的 L4 分支）在那之後 `return 0`＝放行 ⇒ 依本 repo 自己記載的行為
    契約（`context_budget_guard.py` 模組 docstring 逐字：「PostToolUse 的 exit 2 會把
    stderr 回饋給模型」），那段話一個字都到不了模型面前。而 L4 **必須**不節流（斷網
    與「額度真的滿了」不可混為一談）⇒ 不能改用 exit 2 去換能見度。
    ⇒ 換通道不換 rc：`hookSpecificOutput.additionalContext` 是 exit 0 下唯一送得進
    模型上下文的管道。螢幕上「量不到」與「水位很低」從此分得開。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r82-l4-02-"))
        self.buf = io.StringIO()
        saved = (sys.stdout, qg.degraded_stamp_path, qg.quota_trace_path)
        sys.stdout = self.buf
        qg.degraded_stamp_path = lambda source: self.tmp / f"stamp-{source}"
        qg.quota_trace_path = lambda: self.tmp / "trace.jsonl"
        self.addCleanup(self._restore, saved)

    def _restore(self, saved) -> None:  # noqa: ANN001
        sys.stdout, qg.degraded_stamp_path, qg.quota_trace_path = saved

    def test_the_degraded_message_goes_out_on_the_channel_the_model_reads(self) -> None:
        qg.note_degraded("meter-unreachable", "同步取數失敗")
        payload = json.loads(self.buf.getvalue().strip())
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("量不到", context)
        self.assertIn("meter-unreachable", context,
                      "訊息裡沒有 source ⇒ 四種失效又塌回同一句話")

    def test_the_ttl_latch_still_governs_the_new_channel(self) -> None:
        """反向：閂鎖住的那幾次**不得**在新通道上再喊一次。

        少了這一條，「同一個 source 每 180 秒只說一次」這條節制只剩半邊；而每次工具
        呼叫都出聲的守衛會被整個關掉，那是本 repo 反覆判過的形態。
        """
        qg.note_degraded("meter-unreachable", "第一次")
        first = self.buf.getvalue()
        qg.note_degraded("meter-unreachable", "第二次")
        self.assertEqual(self.buf.getvalue(), first, "閂鎖住了卻仍在 stdout 喊了第二次")

    def test_a_muted_call_returns_the_empty_string(self) -> None:
        """回傳值就是「這一次到底說了沒」——呼叫端要靠它才分得出來。"""
        self.assertTrue(qg.note_degraded("no-credentials", "憑證讀不到"))
        self.assertEqual(qg.note_degraded("no-credentials", "憑證讀不到"), "")

    def test_the_notice_declares_the_event_it_was_actually_called_from(self) -> None:
        """🔴 R83／D3：事件名此前**硬寫** `"PreToolUse"`，靠的是「本閘只由 PreToolUse 呼叫」
        那句射程宣稱；接上 PostToolUse 的那一刻它就是假的。失效外觀與「額度很健康」相同：
        `hookEventName` 不符時 CC 丟掉整個 `additionalContext` ⇒ 降級通報靜默失效。"""
        for event in ("PreToolUse", "PostToolUse"):
            with self.subTest(event=event):
                qg.note_degraded(f"src-{event}", "同步取數失敗", event=event)
                emitted = [json.loads(ln)["hookSpecificOutput"]["hookEventName"]
                           for ln in self.buf.getvalue().splitlines() if ln.startswith("{")]
                self.assertEqual(emitted[-1], event, "事件名又被寫死 ⇒ 通報進不了模型上下文")


class MacCredentialSourceTest(unittest.TestCase):
    """🔴 L4-03：mac 的 Claude Code 憑證在 login Keychain，不在檔案系統上。

    R81 版是**單一硬編碼檔案路徑、零平台分支**，而代價是量出來的（本輪 Windows 模擬：
    把 `CREDENTIALS` 指到不存在的檔＝等價於 mac 上該檔缺席 ⇒ `measure_detail` 回
    `no-credentials`、`quota_gate` rc=0、`fanout_cap(None) is None`）：切到 mac 之後
    整條額度軸永久 `unmeasurable`，R81 落地的 80%／95% 兩道門**結構上一次都到不了**，
    而外觀與「水位很低、很健康」完全相同。

    🔴 **獨立複驗訂正本段的「誠實劃界」（原文今天起是假的，故不留著當現行說法）**：
    原文寫「本組**沒有 mac 真機**」，並把「`security` 的 service 名與輸出形態在真 mac
    上對不對」列為交棒項——而 **R83（mac 真機首輪）**已在真機上把那一半驗完。
    🔴 這一行的輪號由獨立驗證者訂正過（原文署名 **R82**）：R82 收輪 commit 內這支檔逐字
    寫著「我手上沒有 mac 真機…交由下一輪承接」⇒ 署名 R82 等於把交棒項講成上一輪已結清，
    而那正是 `quota_meter.KEYCHAIN_SERVICE` 上方 R82 就寫下的那句預先警告在防的形態。
    實測值的**唯一的家**
    是 `quota_meter.KEYCHAIN_SERVICE` 的註解；本段刻意**不複寫**那幾個數字，複寫一份
    就是再開一個會漂移的第二個家（R73 `Find-GitBash` 把一台機器的事實寫成常數，同型）。
    這一段之所以會變假，正是「同一份知識住兩個家、只有一個家被改」：訂正落在 quota_meter
    那一份，這一份留在原地說反話，而假在**會讓人以為這條路仍未驗**的方向。

    🔴 順帶訂正這一行的輪號：原文把交棒輪號從承接輪改寫成**本批輪號**，而該行自己的
    括號逐字寫著「交棒指名承接輪，非自稱本批輪號」⇒ 句子與它自己的判準相矛盾。而且那次
    改寫**不必要**：該行同行本來就帶著 `round-label-ok` 具名豁免，輪號超前鎖
    （`test_check_defect_log_crossref.TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）
    對它從來不成立（本回合實掃：違規清單裡沒有本檔）。交棒項既已結清，整個輪號標籤連同
    那個豁免一併移除——留著一個沒有標的的豁免，下一個人只會再花一次力氣去讀它。

    本組今天守得住的仍然是「判定邏輯」：平台分支選對了路、取不到時回一個**分得出來的**
    理由字面、`security` 吐出來的垃圾不得變成 token。**仍然守不住**的是「一台**沒有**
    Keychain 條目的 mac」——本機構造不出來（清掉條目等於把使用者登出），那一半只由
    `_runner` 注入覆蓋，屬於模擬而非真機。
    """

    def setUp(self) -> None:
        self.meter = _meter()
        self.seen: list[list[str]] = []

    def _runner(self, rc: int, out: str):  # noqa: ANN202
        def call(argv: list[str]) -> tuple[int, str]:
            self.seen.append(argv)
            return rc, out
        return call

    def test_darwin_asks_the_keychain_not_the_filesystem(self) -> None:
        token = self.meter.access_token(
            "darwin", self._runner(0, '{"claudeAiOauth":{"accessToken":"T-OK"}}'))
        self.assertEqual(token, "T-OK")
        self.assertEqual(self.seen[0][:2], ["security", "find-generic-password"])
        self.assertIn(self.meter.KEYCHAIN_SERVICE, self.seen[0])

    def test_a_non_darwin_platform_never_shells_out(self) -> None:
        """控制組：Windows／Linux 那條路一個外部行程都不准起（它讀的是檔案）。"""
        self.meter.access_token("win32", self._runner(0, "should-not-be-used"))
        self.assertEqual(self.seen, [],
                         "非 mac 平台也去問 Keychain ⇒ 每次取數多一次 subprocess")

    def test_a_missing_keychain_entry_is_loud_not_silent(self) -> None:
        """取不到就必須有一個**mac 專屬**的理由字面。

        與 `no-credentials` 混成一個時，「這台 mac 的 Keychain 沒接上」與「憑證檔不在」
        讀起來一模一樣——而後者在 mac 上恆真，於是真正的原因永遠說不出口。
        """
        self.assertEqual(self.meter.access_token("darwin", self._runner(1, "")), "")
        self.assertNotEqual(self.meter.REASON_NO_CREDENTIALS_DARWIN,
                            self.meter.REASON_NO_CREDENTIALS)

    def test_the_darwin_reason_really_reaches_measure_detail(self) -> None:
        """接線（判定層綠不代表接上了電——本 repo『機制蓋好沒接電』已三度復發）。

        🔴 R83／F2-③ 改寫載具：原版把 `meter.access_token` 換成替身、並改寫
        `meter.sys.platform`。那個形態在本輪的重構下**失去了鑑別力**——平台分支收斂進
        `_fetch_token()` 之後，`access_token` 不再在 `measure_detail` 的路徑上，於是替身
        換了也不影響結果（實測：本測試當場紅在 `http-401`，因為它其實走到了真網路）。
        改走兩個**生產注入點**（`platform`／`runner`）：不改任何模組狀態、走的就是
        production 那條路，而且順帶不再需要碰 `meter.sys`。
        🔴 輪號訂正（原文寫「R82 就為此加的」）：`access_token(platform, runner)` 那一組
        確實是 R82 加的，但本斷言走的是 **`measure_detail(timeout, platform, runner)`**
        ——它在 R82 收輪 commit 內的簽章只有 `timeout` 一個參數（`_fetch_token` 那時整支
        還不存在）⇒ 這裡用到的那兩個注入點是 R83 加的。同一組名字掛在兩支函式上，
        署名錯的代價是下一個人會去 R82 的 diff 裡找一個不在那裡的東西。
        """
        self.assertEqual(
            self.meter.measure_detail(1, platform="darwin", runner=self._runner(1, ""))[1],
            self.meter.REASON_NO_CREDENTIALS_DARWIN)

    def test_a_keychain_prompt_nobody_answers_is_not_a_missing_entry(self) -> None:
        """🔴 R83／F2-③：**逾時與「沒有條目」必須是兩個字面。**

        兩者要做的事完全相反：沒有條目＝這台 mac 沒登入過（人要 `claude login`，等下去
        沒有意義）；逾時＝Keychain 跳了鎖定／授權提示而沒有人在螢幕前按（`security` 阻塞
        到 `KEYCHAIN_TIMEOUT_SECONDS`），憑證其實在、解鎖後下一次就量得到。修前兩者都回
        `no-credentials-darwin` ⇒ 痕跡讀起來一模一樣，而「量不到」在本 repo 的語意是
        **不節流** ⇒ 一個無人看管的排程會在「其實只要解鎖」的情況下永久不節流且完全靜默。
        """
        def blocked(argv: list[str]) -> tuple[int, str]:
            raise subprocess.TimeoutExpired(argv, self.meter.KEYCHAIN_TIMEOUT_SECONDS)

        timed_out = self.meter.measure_detail(1, platform="darwin", runner=blocked)[1]
        absent = self.meter.measure_detail(
            1, platform="darwin", runner=self._runner(1, ""))[1]
        self.assertEqual(timed_out, self.meter.REASON_KEYCHAIN_TIMEOUT)
        self.assertNotEqual(timed_out, absent)
        # 逾時**不得**被寬的那條 `except Exception` 吃掉（`TimeoutExpired` 是
        # `SubprocessError` 的子類，攔截順序寫反就會靜默退回修前的行為，且全套照綠）。
        self.assertEqual(self.meter.token_detail("darwin", blocked),
                         ("", self.meter.REASON_KEYCHAIN_TIMEOUT))
        # 控制組：其他例外仍然是「沒有條目」，不得被一起升級成逾時（那是反方向的假話）。
        def boom(argv: list[str]) -> tuple[int, str]:
            raise OSError("security 不在這台機器上")

        self.assertEqual(self.meter.token_detail("darwin", boom)[1], absent)

    def test_garbage_from_the_keychain_never_becomes_a_token(self) -> None:
        """`security` 可能吐錯誤訊息而不是 JSON ⇒ 不得把它當 token 送出去。

        送出去的話會變成一個**永遠 401** 的假綠：取數看起來有在跑，只是永遠失敗。

        🔴 R83 補第三種形態（輪號經獨立驗證者訂正：原文署名 R82，而該形態在 R82 收輪
        commit 內 grep「第三種形態」命中 **0**——被守的 `_run_security` 是 R82 的，
        這一條斷言不是）：`_run_security` 帶 `errors="replace"`，所以**非 UTF-8
        位元組會降解成一串 U+FFFD**，而那串東西不含任何空白、長度也遠超過 20
        ⇒ 舊判準（只看「夠長且不含空白」）照樣放行（實測 `True`）。守衛與它自己上一段
        註解宣稱要防的東西之間差一個字，而後果正是那句話寫的「永遠 401 的假 token」：
        額度軸從此恆為 `unmeasurable`，80%／95% 兩道門一次都到不了。
        """
        self.assertEqual(self.meter.access_token(
            "darwin", self._runner(0, "security: SecKeychainSearchCopyNext: not found\n")),
            "")
        self.assertEqual(self.meter.access_token("darwin", self._runner(0, "  ")), "")
        self.assertEqual(self.meter.access_token(
            "darwin", self._runner(0, "�" * 40)), "",
            "降解成 U+FFFD 的位元組被當成 token ⇒ 每一次取數都是永遠 401 的假綠")
        self.assertEqual(self.meter.access_token(
            "darwin", self._runner(0, "abcdefghij\x00klmnopqrstuvwxyz")), "",
            "控制字元不算 isspace()，只靠空白判準擋不掉它")
        # 控制組：真 token 形態（base64url、純 ASCII 可列印）**必須**通得過，否則這道
        # 收緊會把整條 mac 取數路變成恆空——那是把假綠換成假紅，同樣是靜默失能。
        # 取 `_FAKE_TOKEN` 而不是在這裡再拼一份同樣的字面：那個常數上方寫著「為什麼必須
        # 長成這樣」（要通得過裸 token 判準的長度門檻），複寫一份就是第二個會漂開的家。
        self.assertEqual(
            self.meter.access_token("darwin", self._runner(0, _FAKE_TOKEN)), _FAKE_TOKEN)


def dual_identity_problems(modules: object) -> list[str]:
    """同一支 `tools/lib` 模組有沒有被載成兩個模組物件（空＝通過）。純函式。

    🔴 Q2-01：`tools/lib` 既可以裸名 import（hook 那一側唯一走得通的形態），也可以
    `from lib import X`（planner／測試那一側走得通）。兩種寫法在同一個行程裡會產生
    **兩個相異的模組物件**——後果不是效能而是假綠：測試 monkeypatch `lib.quota_limits.X`
    不會影響 hook 用的 `quota_limits.X`，而兩邊的常數從此可以無聲地分岔。
    """
    names = set(modules)
    return [f"`{n}` 與 `lib.{n}` 同時在 sys.modules 裡 ⇒ 同一份原始碼有兩個模組物件"
            for n in sorted(names) if f"lib.{n}" in names]


class ModuleIdentityIsSingleTest(unittest.TestCase):
    """Q2-01：`tools/lib/*` 在 production 的 import 圖裡只准有**一個**模組身分。"""

    _PROBE = (
        "import json, sys\n"
        "sys.path.insert(0, r'{tools}')\n"
        "sys.path.insert(0, r'{hooks}')\n"
        "import session_resume_planner\n"
        "{extra}"
        "print(json.dumps(sorted(m for m in sys.modules if 'quota' in m)))\n"
    )

    def _modules(self, extra: str = "") -> list[str]:
        code = self._PROBE.format(tools=_REPO_ROOT / "tools",
                                  hooks=_REPO_ROOT / ".claude" / "hooks", extra=extra)
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, check=False, cwd=str(_REPO_ROOT),
                              encoding="utf-8", errors="replace",
                              env={**os.environ, "PYTHONUTF8": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_the_production_import_graph_has_one_object_per_module(self) -> None:
        self.assertEqual(dual_identity_problems(self._modules()), [])

    def test_the_check_would_actually_catch_a_split(self) -> None:
        """合成注入（紅）：多寫一行 `from lib import quota_limits` 就該轉紅。

        沒有這一支，上面那條綠只說明「今天沒有人這樣寫」，而 Q2-01 的整個立案就是
        「這種寫法今天成立、而且 repo 裡到處都是」。
        """
        # 🔴 `F401` 與 `\n` 之間那個空白不是排版：`test_no_invalid_escape_sequences.py::
        # TestNoqaDirectivesAreWellFormed` 判「規則碼後緊接非空白字元」＝ruff 眼中的非法
        # 豁免指令（該行實際完全沒被豁免）。本行是注入用的合成模組原始碼，少那個空白就會
        # 被那道鎖抓到。另注意本段刻意不讓指令名落在井號後第一個 token——ruff 會讀成指令。
        split = self._modules("from lib import quota_limits  # noqa: F401 \n")
        problems = dual_identity_problems(split)
        self.assertTrue(problems, f"雙身分注入竟然放行：{split}")
        self.assertIn("quota_limits", problems[0])

    def test_the_planner_takes_the_reexport_route_not_a_second_import(self) -> None:
        """成因面：planner 不得自己 `from lib import quota_limits`（那就是注入那一行）。

        🔴 只掃**剝掉註解之後**的程式碼：該檔的 WHY 註解裡合法地寫出了這個字面（它正在
        解釋為什麼不准這樣寫）。掃整份原始碼會把那段解釋判成違規——本 repo 判過的假紅
        形態，而假紅會讓下一個人把判準整個關掉。
        """
        code = "\n".join(line.split("#", 1)[0]
                         for line in _PLANNER.read_text(encoding="utf-8").splitlines())
        self.assertNotIn("from lib import quota_limits", code)


# ─────────────────────────────── 哨兵生命週期（R82／HELM-02；立案＝掌舵者當場截圖的三支 JOB）
def _transcript(tmp: Path, name: str, turns: int, span_seconds: float) -> Path:
    """合成一份逐字稿：`turns` 個 assistant 回合，首尾相距 `span_seconds`。

    刻意用真的 jsonl 而不是 monkeypatch `session_evidence`：被守的性質是「**從逐字稿**
    量得出這兩個數」，把量測換成假的就只剩下 `a >= b` 這個沒有人會弄壞的比較。
    """
    base = datetime(2026, 8, 9, 10, 0, 0, tzinfo=UTC)
    lines = []
    for i in range(max(turns, 1)):
        at = base + timedelta(seconds=(span_seconds * i / max(turns - 1, 1)))
        lines.append(json.dumps({
            "type": "assistant" if i < turns else "user",
            "timestamp": at.isoformat().replace("+00:00", "Z"),
            "message": {"model": "claude-opus-5", "usage": {"input_tokens": 10}}}))
    path = tmp / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


class SentinelArmingCriterionTest(unittest.TestCase):
    """🔴 被守的性質：**短命 session 不得留下一支每 15 分鐘醒來的 schtasks**。

    立案是量出來的，不是推測：掌舵者截圖的三支哨兵裡有兩支屬於活了 5 秒與 12 秒的
    session；本輪把該逐字稿目錄全部 83 支逐支量過 `(回合數, 首尾跨度)`——六支元凶一律
    **2 回合 / ≤12 秒**，真正在做事的最少 **38 回合 / 853 秒**。門檻取在那道縫裡。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.spawned: list[tuple[str, str]] = []

    def _spawn(self, transcript: str, plan: str) -> bool:
        self.spawned.append((transcript, plan))
        return True

    def test_the_six_offenders_measured_this_round_would_not_arm(self) -> None:
        """現況控制組：實測到的那六支（2 回合、4~12 秒）一支都不得武裝。"""
        for span in (4, 5, 7, 7, 11, 12):
            self.assertFalse(should_arm := sentinel_lifecycle.should_arm(2, float(span)),
                             f"2 回合 / {span}s 竟然夠格武裝（{should_arm}）")

    def test_a_real_working_session_does_arm(self) -> None:
        """反向控制組：最小的真實 session（38 回合 / 853 秒）必須武裝。

        少了這一條，把門檻設成無限大也會全綠——而那等於把續航整個關掉，
        且失效方向是「排程器很乾淨」＝看起來像修好了。
        """
        self.assertTrue(sentinel_lifecycle.should_arm(38, 853.0))

    def test_both_measures_are_load_bearing(self) -> None:
        """AND 不是 OR：任一軸單獨達標都不得武裝（注入自證）。"""
        self.assertFalse(sentinel_lifecycle.should_arm(200, 10.0))   # 回合多但只活 10 秒
        self.assertFalse(sentinel_lifecycle.should_arm(2, 99999.0))  # 開著沒動一整天

    def test_evidence_comes_out_of_a_real_transcript(self) -> None:
        """量測面：回合數與跨度真的是從 jsonl 掃出來的。"""
        turns, span = sentinel_lifecycle.session_evidence(
            _transcript(self.tmp, "s.jsonl", 30, 1200.0))
        self.assertEqual(turns, 30)
        self.assertAlmostEqual(span, 1200.0, delta=1.0)

    def test_a_synthetic_quota_record_is_not_a_turn(self) -> None:
        """額度耗盡時 harness 寫進逐字稿的那筆佔位**不是**一次模型呼叫。

        它與 `guard.scan_transcript` 對同一筆的處置必須一致，否則「撞線很多次」會被
        算成「做了很多事」——而那正好是最需要判斷準確的那一刻。
        """
        path = self.tmp / "syn.jsonl"
        path.write_text("\n".join(json.dumps({
            "type": "assistant", "timestamp": f"2026-08-09T10:00:0{i}Z",
            "message": {"model": guard.SYNTHETIC_MODEL, "usage": {}}}) for i in range(5))
            + "\n", encoding="utf-8", newline="\n")
        self.assertEqual(sentinel_lifecycle.session_evidence(path)[0], 0)

    def test_maybe_arm_does_not_spawn_for_a_short_session(self) -> None:
        """端到端（注入 spawn）：短命 session ⇒ 一次都不 spawn、不留閂鎖。"""
        path = _transcript(self.tmp, "short.jsonl", 2, 12.0)
        why = sentinel_lifecycle.maybe_arm(path, "short", plan_path="p.md",
                                           spawn=self._spawn, tmp_dir=str(self.tmp))
        self.assertEqual(self.spawned, [])
        self.assertIn("below-threshold", why)
        self.assertFalse(sentinel_lifecycle.arm_marker_path("short", str(self.tmp)).exists())

    def test_maybe_arm_spawns_once_and_then_latches(self) -> None:
        """真 session ⇒ 武裝一次，之後每次工具呼叫都只讀閂鎖（不得重複註冊）。"""
        path = _transcript(self.tmp, "long.jsonl", 40, 900.0)
        first = sentinel_lifecycle.maybe_arm(path, "long", plan_path="p.md",
                                             spawn=self._spawn, tmp_dir=str(self.tmp))
        second = sentinel_lifecycle.maybe_arm(path, "long", plan_path="p.md",
                                              spawn=self._spawn, tmp_dir=str(self.tmp))
        self.assertEqual((first, second), ("armed", "latched"))
        self.assertEqual(len(self.spawned), 1, "重複武裝＝每次工具呼叫都外呼 powershell")

    def test_session_start_clears_the_latch_so_resume_can_rearm(self) -> None:
        """`claude -r` 續接已下班的 session：閂鎖必須清得掉，否則續航靜默弄丟。"""
        path = _transcript(self.tmp, "long.jsonl", 40, 900.0)
        sentinel_lifecycle.maybe_arm(path, "long", plan_path="p.md",
                                     spawn=self._spawn, tmp_dir=str(self.tmp))
        self.assertTrue(sentinel_lifecycle.clear_arm_latch("long", str(self.tmp)))
        sentinel_lifecycle.maybe_arm(path, "long", plan_path="p.md",
                                     spawn=self._spawn, tmp_dir=str(self.tmp))
        self.assertEqual(len(self.spawned), 2)

    # ── R84／C3-C：每一條「醒來之後」的路徑都必須處置掉自己的排程 ──────────────
    #: 允許的處置：拆掉自己（`_schtasks_remove`）、重排下一次（`_register_and_record`），
    #: 或把整件事**交棒**給另一支同樣受本判準約束的 tick（`_resume_tick`）。
    #: 三者以外的 return＝那一跑醒來、做了點事、然後把排程留在原地 ⇒ 下一個間隔它會
    #: 再醒一次、再走同一條路，永遠不會停。Windows 上那就是每 15 分鐘一個黑框。
    #: 🔴 R84／C8：第四個名字是**委派**而非新語意——`_abort_and_unregister` 是那四條
    #: abort 路徑收成一份之後的唯一實作，它在函式體第一行就無條件 `_schtasks_remove`。
    #: 直接把名字加進本表會讓判準退化成「呼叫了一個名字好聽的函式」，所以同輪補
    #: `test_the_abort_delegate_really_disposes`：委派自己不處置時當場紅（兩條合起來
    #: 才等價於原判準的強度，缺任一條都比原判準弱）。
    _TICK_DISPOSALS = ("_schtasks_remove", "_register_and_record", "_resume_tick",
                       "_abort_and_unregister")
    #: 受判準約束的 tick 函式。兩支都要判：`_sentinel_tick` 的 probe 分支會交棒給
    #: `_resume_tick`，只判前者等於把一半的路徑交給運氣。
    _TICK_FUNCS = ("_sentinel_tick", "_resume_tick")

    @staticmethod
    def _returns_with_dominators(fn: ast.FunctionDef) -> list[tuple[int, set[str]]]:
        """每一個 `return` 的**支配呼叫集合**（同一條直線路徑上先於它的呼叫名）。

        分支體內的呼叫**不算**其他分支的支配者——那正是「支配」與「函式體內出現過」
        的差別，而後者是沒有鑑別力的（`_sentinel_tick` 隨便哪一支分支呼叫過一次
        `_schtasks_remove`，全部 return 就一起被判成安全）。

        🔴 R84／SD-09 訂正**射程**：舊版靠 `isinstance(sub, ast.stmt)` 決定要不要往下走，
        而 `ast.ExceptHandler`／`ast.match_case` **不是** `ast.stmt` ⇒ 寫在 `except:`／
        `case:` 裡的 `return` 連進分母都沒有進，判準對它完全隱形（掃描器照跑、照綠、
        照回報命中數，只是那條路徑從來不在分母裡——本 repo 判過的「失明是靜默的」）。
        `ast.TryStar`／`ast.AsyncFor`／`ast.AsyncWith` 是同一個洞的另一半：型別根本不在
        舊的 isinstance 名單上 ⇒ 落到最後那一格「直線陳述式」，return 被吞掉、而且體內
        的呼叫還會被當成後續 return 的支配者（往**放行**的方向錯）。
        今日 `_sentinel_tick`／`_abort_and_unregister` 實測 0 個 try/except ⇒ 存量命中 0，
        但那是運氣不是設計：任何人補一段 `try/except` 進去就整條失明。

        分支拆法逐條對齊「真的先跑過」這件事，而不是求方便：迴圈的 `orelse` 只拿到
        **迴圈之前**的支配集合（迴圈可能一次都沒跑）；`except` handler 同理只拿到
        `try` **之前**的（body 可能在任何一行拋出）——兩者都往「判紅」的保守方向站。
        """
        out: list[tuple[int, set[str]]] = []
        try_types = (ast.Try, getattr(ast, "TryStar", ast.Try))

        def names_in(node: ast.AST) -> set[str]:
            return {c.func.id for c in ast.walk(node)
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}

        def branches(stmt: ast.stmt):
            """`(在進分支前就跑掉的呼叫, 各條獨立子路徑)`；回 `None` ＝這不是容器。"""
            if isinstance(stmt, ast.If):
                return names_in(stmt.test), [stmt.body, stmt.orelse]
            if isinstance(stmt, (ast.For, ast.AsyncFor)):
                return names_in(stmt.iter), [stmt.body, stmt.orelse]
            if isinstance(stmt, ast.While):
                return names_in(stmt.test), [stmt.body, stmt.orelse]
            if isinstance(stmt, (ast.With, ast.AsyncWith)):
                return ({n for item in stmt.items for n in names_in(item.context_expr)},
                        [stmt.body])
            if isinstance(stmt, try_types):
                return set(), [stmt.body, stmt.orelse, stmt.finalbody,
                               *(h.body for h in stmt.handlers)]
            if isinstance(stmt, ast.Match):
                return names_in(stmt.subject), [case.body for case in stmt.cases]
            return None

        def walk(body: list[ast.stmt], seen: set[str]) -> None:
            seen = set(seen)
            for stmt in body:
                if isinstance(stmt, ast.Return):
                    out.append((stmt.lineno, set(seen) | names_in(stmt)))
                    continue
                found = branches(stmt)
                if found is not None:
                    pre, bodies = found
                    seen |= pre
                    for sub in bodies:
                        walk(sub, seen)        # 各分支各拿一份副本
                    continue
                seen |= names_in(stmt)         # 直線陳述式：真的支配後面所有 return

        walk(fn.body, set())
        return out

    def test_every_tick_return_disposes_of_its_own_schedule(self) -> None:
        tree = ast.parse(_PLANNER.read_text(encoding="utf-8"))
        checked = 0
        for name in self._TICK_FUNCS:
            fn = next(n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name == name)
            rets = self._returns_with_dominators(fn)
            self.assertTrue(rets, f"{name} 一個 return 都掃不到 ⇒ 判準空轉")
            for lineno, dominators in rets:
                checked += 1
                self.assertTrue(
                    dominators & set(self._TICK_DISPOSALS),
                    f"{name} 第 {lineno} 行的 return 沒有先處置排程"
                    f"（支配集合={sorted(dominators)}）⇒ 這一跑醒來、做了事、"
                    "然後把排程原封不動留著，下一個間隔還會再來一次")
        self.assertGreaterEqual(checked, 8, f"只掃到 {checked} 條 return 路徑 ⇒ 分母塌了")

    def test_the_abort_delegate_really_disposes(self) -> None:
        """委派名進了 `_TICK_DISPOSALS` ⇒ 必須釘住它**真的**拆排程（否則那個名字是空頭）。

        判準取「函式體的直線路徑上支配全部 return」而不是「體內出現過」——與上面那條
        判準同一把尺；委派哪天被改成「只在某個分支拆」時，四條 abort 路徑會一起悄悄
        失效，而表徵與現在完全相同（訊息照印、rc 照 1、排程留著）。
        """
        tree = ast.parse(_PLANNER.read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_abort_and_unregister")
        rets = self._returns_with_dominators(fn)
        self.assertTrue(rets, "_abort_and_unregister 一個 return 都掃不到 ⇒ 判準空轉")
        for lineno, dominators in rets:
            self.assertIn(
                "_schtasks_remove", dominators,
                f"_abort_and_unregister 第 {lineno} 行的 return 沒有先拆排程"
                f"（支配集合={sorted(dominators)}）⇒ `_TICK_DISPOSALS` 裡的這個名字"
                "只是好聽，四條 abort 路徑實際上一條都沒有處置自己的排程")

    def test_the_dominator_criterion_is_not_satisfied_by_a_sibling_branch(self) -> None:
        """🔴 注入自證：處置動作寫在**另一個分支**時必須紅（否則判準退化成「檔內出現過」）。"""
        src = ("def _sentinel_tick(args):\n"
               "    if a:\n"
               "        _schtasks_remove(x)\n"
               "        return 1\n"
               "    return 2\n")
        fn = ast.parse(src).body[0]
        rets = dict(self._returns_with_dominators(fn))
        good = next(d for ln, d in rets.items() if ln == 4)
        bad = next(d for ln, d in rets.items() if ln == 5)
        self.assertIn("_schtasks_remove", good)
        self.assertNotIn("_schtasks_remove", bad,
                         "兄弟分支的呼叫被算成支配者 ⇒ 判準沒有鑑別力")

    def test_a_return_inside_an_except_handler_is_not_invisible(self) -> None:
        """🔴 R84／SD-09 注入自證：`except:` 內不處置就 return ⇒ 必須抓得到。

        舊版 walk 以 `isinstance(sub, ast.stmt)` 決定要不要下探，而 `ast.ExceptHandler`
        不是 `stmt` ⇒ 這條 return 路徑**連分母都沒進**（不是判錯，是看不見）。
        """
        src = ("def _sentinel_tick(args):\n"
               "    try:\n"
               "        _schtasks_remove(x)\n"
               "        return 0\n"
               "    except OSError:\n"
               "        return 1\n")
        rets = dict(self._returns_with_dominators(ast.parse(src).body[0]))
        self.assertEqual(sorted(rets), [4, 6], f"except 內的 return 沒進分母：{rets}")
        self.assertIn("_schtasks_remove", rets[4])
        self.assertNotIn("_schtasks_remove", rets[6],
                         "handler 拿到了 try body 的呼叫當支配者 ⇒ 沒有鑑別力："
                         "body 可能在那一行之前就拋了，那次根本沒拆到排程")

    def test_the_other_containers_that_are_not_plain_statements(self) -> None:
        """同一個洞的其餘幾半：`match` 的 case、`async for`／`async with` 的 body。

        三者的共同形態都是「型別不在舊名單上 ⇒ 落進『直線陳述式』那一格」——return 被
        吞掉，而且體內的呼叫還會被記成後續 return 的支配者（往**放行**的方向錯）。
        """
        for label, src in (
            ("match", "def _sentinel_tick(a):\n"
                      "    match a:\n        case 1:\n            return 1\n"),
            ("async for", "async def _sentinel_tick(a):\n"
                          "    async for x in a:\n        return 2\n"),
            ("async with", "async def _sentinel_tick(a):\n"
                           "    async with a as x:\n        return 3\n"),
        ):
            with self.subTest(container=label):
                fn = ast.parse(src).body[0]
                self.assertTrue(self._returns_with_dominators(fn),
                                f"{label} 容器內的 return 對判準隱形")

    def test_this_module_never_reaches_the_real_scheduler(self) -> None:
        """🔴 R84／C3-P4c 的回歸鎖：兩條路都必須被關起來，而它們**結構上不相交**。

        本機實測留下的證據：`launchctl list` 長期掛著一支 `AutoSDD_Sentinel_s`
        （session id 就是本模組某個 fixture 的檔名 `s.jsonl`），每 15 分鐘醒一次、
        session 早就不存在 ⇒ 永遠沒有人來收。Windows 上它就是那個黑框。
        兩條路：① 子行程走 `_isolated_env`（預設 `real_scheduler=False`）；
        ② 同行程走 `setUpModule` 設在**本行程**環境上的同一個旗標。
        """
        self.assertEqual(os.environ.get(guard.SENTINEL_OFF_ENV), "1",
                         "setUpModule 沒生效 ⇒ 同行程呼叫那一半又碰得到真排程器")
        self.assertEqual(_isolated_env(self.tmp).get(guard.SENTINEL_OFF_ENV), "1",
                         "_isolated_env 預設又放行真排程器 ⇒ 子行程那一半的洞回來了")
        self.assertIsNone(
            _isolated_env(self.tmp, real_scheduler=True).get(guard.SENTINEL_OFF_ENV),
            "具名開關失效 ⇒ 真的要驗武裝的測試沒有出口，逃生口會被改成預設關法")

    def test_the_hook_no_longer_arms_on_session_start(self) -> None:
        """成因面：SessionStart 那條路上不得再有 spawn（那就是增生的來源）。

        以 AST 掃 hook 的 `arm_sentinel`：它**不得呼叫** `spawn_sentinel`。
        比對靜態結構而不是行為，是因為行為那一半在非 Windows 上恆早退＝測不到（本 repo
        判過的「單平台判準」形狀），而這個性質在任何平台都該成立。

        🔴 R84／C3-P4b 把判準由「unparse 之後的**子字串**比對」換成「**被呼叫的函式名**
        逐一相等比對」——不是放寬，是把假紅拿掉。子字串比對會把任何**名字以它為前綴**
        的別的函式一起判紅（本輪的 `spawn_sentinel_gc`：它做的是相反的事——收掉別人留下
        的孤兒哨兵，正是 SessionStart 該做的清理）。而「名字長得像」與「真的在武裝」是
        兩件事，鎖只能守後者。判準同時**變嚴**了一面：舊寫法對 `x = spawn_sentinel`
        這種不呼叫、只取參照再由別處呼叫的繞法也只是碰巧命中，新寫法把「取名字」與
        「呼叫」分開看，落點明確。
        """
        tree = ast.parse(_HOOK.read_text(encoding="utf-8"))
        body = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "arm_sentinel")
        called = {n.func.id for n in ast.walk(body)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertNotIn("spawn_sentinel", called,
                         "SessionStart 又直接武裝了 ⇒ 每一支 5 秒探針都會留一支排程")


# 🔴 WMI `Win32_Process` 欄位的**逐字語料**（`classify()` 對它們只做字串比對，不經任何
# pathlib join）⇒ 磁碟機字面值在這裡是被測資料本身，不是「假路徑」，故走 `platform-ok`
# 具名豁免而非 `ABS_FAKE_REPO`（換成後者會讓 repo 根與命令列裡的路徑在 POSIX 上對不上，
# 判準會從「比對命令列」變成「永遠不命中」＝把回歸鎖靜默掏空）。集中成常數的第二個理由
# 是它們被多支測試共用，散寫時每一處都要各自帶一個豁免標記。
_WMI_REPO = r"D:\repo"  # platform-ok: WMI 語料
_WMI_PARENT = '"C:\\Users\\x\\python.exe" -m pytest tests/ -q'  # platform-ok: WMI 語料
_WMI_SCHTASKS = r'pythonw.exe "C:\T\autosdd_schtasks_ab\run.ps1"'  # platform-ok: WMI 語料
_WMI_CMD = ('C:\\WINDOWS\\system32\\cmd.exe'  # platform-ok: WMI 語料
            ' /c "pytest tests -k \\"AT_001\\" -q"')
_WMI_FOREIGN = (r'C:\WINDOWS\system32\cmd.exe'  # platform-ok: WMI 語料
                r' /c "D:\Other\run_backup.bat"')  # platform-ok: WMI 語料


class ConsoleSpawnAttributionTest(unittest.TestCase):
    """`tools/probe/console_spawn_watch.py` 的歸因判準。

    🔴 被守的性質是**「無法歸因」必須是一等公民**。掌舵者兩度回報黑框，而第一輪的處置是
    純推論（逐一檢查我們自己的 spawn 站點）——那種做法對「我們不知道的那條路」結構上失明。
    量測器的價值全押在「它把說不清楚的東西誠實放進第三格」上：一旦那些被硬塞進
    `foreign`，報表就會給出「本 repo 側乾淨」這個看起來很好、但沒有支撐的結論。
    """

    @staticmethod
    def _watch():
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import console_spawn_watch  # noqa: PLC0415 — probe 不在 import 面，隨用隨載
        return console_spawn_watch

    def test_a_process_with_no_command_line_is_not_guessed(self) -> None:
        """命令列與父命令列都空 ⇒ `unattributable`，不得倒向任何一邊。"""
        watch = self._watch()
        kind, why = watch.classify({"Name": "cmd.exe"}, _WMI_REPO)
        self.assertEqual(kind, "unattributable", why)

    def test_our_own_spawns_are_attributed_to_the_repo(self) -> None:
        watch = self._watch()
        for cmd in (r"powershell.exe -File D:\repo\tools\x.ps1",
                    _WMI_SCHTASKS,
                    r"bash.exe C:\T\tmpx\tools\git-hooks/pre-commit"):
            kind, why = watch.classify({"CommandLine": cmd}, _WMI_REPO)
            self.assertEqual(kind, "repo", why)

    def test_the_measured_shell_true_cmd_is_not_written_off_as_foreign(self) -> None:
        """🔴 回歸鎖：本輪實測抓到的那 3 筆 `cmd.exe`，逐字餵回判準。

        首版把它們判成「非本 repo」（命令列沒有 repo 路徑），而它們其實是 AutoClaude
        `shell=True` 的產物 ⇒ **低報我方命中**，報表會給出「本 repo 側乾淨」這個假結論。
        現在它們落在獨立的 `shell-hop` 格：不宣稱是我們的，也不宣稱不是。
        """
        watch = self._watch()
        kind, why = watch.classify({
            "Name": "cmd.exe",
            "CommandLine": _WMI_CMD,
            "ParentName": "python.exe",
            "ParentCommandLine": _WMI_PARENT,
        }, _WMI_REPO)
        self.assertEqual(kind, "shell-hop", why)
        self.assertIn("evaluator", why)
        # 🔴 那 3 筆裡最短命的一筆連自己的 `CommandLine` 都沒有（WMI 抓到時已經沒了）。
        # 判準若要求命令列裡出現 `/c`，最像黑框的那一個剛好會掉出這一格。
        kind2, why2 = watch.classify({
            "Name": "cmd.exe", "CommandLine": None, "ParentName": "python.exe",
            "ParentCommandLine": _WMI_PARENT,
        }, _WMI_REPO)
        self.assertEqual(kind2, "shell-hop", why2)

    def test_a_foreign_scheduled_task_is_not_claimed_as_ours(self) -> None:
        """🔴 反向控制組：不得為了交差把外人的黑框算到自己頭上（也不得反過來）。

        `run_backup.bat` 是本機**非本 repo** 的排程工作，掌舵者的黑框有一部分來自它。
        把它歸進 `repo` 會讓我們去修一個不存在的缺陷；歸進 `unattributable` 則會讓
        「有幾個是外人的」這個數字失真。
        """
        watch = self._watch()
        kind, why = watch.classify({"CommandLine": _WMI_FOREIGN}, _WMI_REPO)
        self.assertEqual(kind, "foreign", why)

    def test_the_probe_never_becomes_the_thing_it_measures(self) -> None:
        """量測器自己 spawn `powershell.exe` 時必須帶 no-window 旗標。

        少了這一條，它每量一次就自己彈一個框——量測器成為它要量的那個現象的來源，
        而報表會把那一筆算進命中數。這是本 repo「驗證載具本身要被驗證」的同一條紀律。
        """
        watch = self._watch()
        self.assertEqual(watch.NO_WINDOW, guard.NO_WINDOW)
        source = (_REPO_ROOT / "tools" / "probe" / "console_spawn_watch.py").read_text(
            encoding="utf-8")
        self.assertEqual(no_window_problems({"probe": source}), [])


class SentinelReapVerdictTest(unittest.TestCase):
    """GC 的判準。🔴 被守的第一性質是**不許誤收**：誤收一支活著的哨兵＝那個 session 的
    續航被靜默弄丟，而「弄丟了」在螢幕上與「一切正常」完全同形。"""

    def test_a_protected_session_is_never_reaped(self) -> None:
        """最保守的那一條擋在最前面——即使逐字稿不見了也不收。"""
        reap, why = sentinel_lifecycle.reap_verdict(
            transcript_exists=False, idle_seconds=None, state=None, protected=True)
        self.assertFalse(reap)
        self.assertIn("protected", why)

    def test_an_active_session_is_never_reaped(self) -> None:
        """逐字稿還在寫（閒置未達門檻）⇒ 不收。這是當前 session 的保護傘。"""
        reap, _ = sentinel_lifecycle.reap_verdict(
            transcript_exists=True, idle_seconds=60.0, state="sentinel", protected=False)
        self.assertFalse(reap)

    def test_a_session_waiting_for_quota_is_never_reaped(self) -> None:
        """🔴 最貴的誤收：等額度那段期間逐字稿本來就不會更新（額度視窗 5 小時）。

        只看閒置就會把「正在等」誤判成「已結束」，而那正好是哨兵唯一有價值的時刻。
        """
        reap, why = sentinel_lifecycle.reap_verdict(
            transcript_exists=True, idle_seconds=99 * 3600.0, state="waiting",
            protected=False)
        self.assertFalse(reap, why)

    def test_an_unknown_state_is_never_reaped(self) -> None:
        """未列舉的狀態一律不收（未知 ⇒ 不動）。少了它，可收清單會退化成
        「不是 waiting 就收」，而日後長出新的等待型狀態時會被靜默收掉。"""
        reap, why = sentinel_lifecycle.reap_verdict(
            transcript_exists=True, idle_seconds=99 * 3600.0, state="brand-new-state",
            protected=False)
        self.assertFalse(reap, why)

    def test_a_finished_session_is_reaped(self) -> None:
        """反向控制組：閒置夠久 ＋ 狀態在可收清單內 ⇒ 收。否則這支工具沒有用途。

        `armed` 一定要在裡面：本輪實跑 dry-run 才發現第一版只認終態，而現實中**每一支
        巡邏中的哨兵狀態都是 `armed`** ⇒ 那個版本對真正要收的東西一支都收不到，
        而它的外觀是「很保守、很安全」。
        """
        for state in ("disarmed", "abandoned", "armed", "sentinel", None):
            reap, _ = sentinel_lifecycle.reap_verdict(
                transcript_exists=True, idle_seconds=10 * 3600.0, state=state,
                protected=False)
            self.assertTrue(reap, f"state={state} 竟然不收")

    def test_a_vanished_transcript_is_reaped(self) -> None:
        reap, _ = sentinel_lifecycle.reap_verdict(
            transcript_exists=False, idle_seconds=None, state=None, protected=False)
        self.assertTrue(reap)

    def test_an_unlocatable_transcript_dir_reaps_nothing(self) -> None:
        """🔴 本輪 dry-run 當場抓到的自產缺陷，釘成回歸鎖。

        第一版把「逐字稿目錄定位不到」（planner import 失敗 ⇒ `_transcript_dir()` 回
        `None`）與「這個 session 的檔真的被刪了」擠進同一個 `False` ⇒ **實跑時三支哨兵
        全被判為可收，包含當下正在跑的那一支**。同一條紀律（量不到 ≠ 量到零）本 repo
        寫了很多輪，而它在最貴的地方仍然被犯了一次——所以它需要的是鎖，不是提醒。
        """
        reap, why = sentinel_lifecycle.reap_verdict(
            transcript_exists=None, idle_seconds=None, state=None, protected=False)
        self.assertFalse(reap, why)
        self.assertIn("量不到", why)

    def test_gc_never_collapses_unknown_into_missing(self) -> None:
        """成因面：`gc()` 在目錄定位不到時必須傳 `None` 而不是 `False`。

        判準看的是**行為**（注入一個定位不到的環境，跑真的 `gc()`），不是原始碼字面：
        字面判準會被一個等價改寫繞過，而這一格的失效方向是「把活著的哨兵拆掉」。
        """
        with unittest.mock.patch.object(sentinel_lifecycle, "_transcript_dir",
                                        return_value=None), \
             unittest.mock.patch.object(sentinel_lifecycle, "sentinel_task_names",
                                        return_value=["AutoSDD_Sentinel_whoever"]):
            rows = sentinel_lifecycle.gc()
        self.assertEqual([r["reap"] for r in rows], [False], rows)

    def test_gc_defaults_to_dry_run(self) -> None:
        """預設不動任何東西：這支工具的失手不可逆，而它的價值 dry-run 就兌現了。"""
        source = (_REPO_ROOT / "tools" / "lib" / "sentinel_lifecycle.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        func = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "gc")
        default = dict(zip([a.arg for a in func.args.kwonlyargs],
                           func.args.kw_defaults))["apply"]
        self.assertIs(default.value, False)

    def _apply_once(self, sid: str):  # noqa: ANN202
        """跑一次真的 `gc(apply=True)`，但**不碰排程器**（`_remove_task` 換替身）。

        逐字稿目錄刻意「定位得到、那支檔不存在」＝可收那一條路；殘骸也真的落在磁碟上，
        所以掃殘骸與寫痕跡的先後順序是被真的走過一次的，不是靠讀原始碼推論的。
        """
        tmp = Path(tempfile.mkdtemp(prefix="gc-trace-"))
        plan = tmp / f"autosdd_resume_plan_{sid}.md"
        plan.write_text("state: disarmed\n", encoding="utf-8", newline="\n")
        trace = planner.endurance_log_path(plan)
        self.addCleanup(lambda: trace.unlink(missing_ok=True))
        with unittest.mock.patch.object(
                sentinel_lifecycle, "sentinel_task_names",
                return_value=[sentinel_lifecycle.TASK_PREFIX + sid]), \
             unittest.mock.patch.object(
                sentinel_lifecycle, "_transcript_dir",
                return_value=Path(tempfile.mkdtemp(prefix="gc-tx-"))), \
             unittest.mock.patch.object(sentinel_lifecycle, "_remove_task",
                                        return_value=0):
            return sentinel_lifecycle.gc(apply=True, tmp_dir=str(tmp))[0], trace

    def test_reaping_a_sentinel_leaves_an_audit_trace(self) -> None:
        """🔴 回收**不得靜默**——這是本輪實機觀測到的那個病徵的另一半。

        `_sweep_artifacts` 把任務書／閂鎖／boot log／水位 state 四件全刪、`_remove_task`
        又把排程本體拆掉 ⇒ 少了這一行痕跡，`--apply` 跑完之後的磁碟狀態與「哨兵自己靜默
        消失」（判過四次 `arm_reset`、log 某刻起空白、`launchctl` 零命中）**完全同形**，
        事後連「是被收掉還是自己死了」都分不出來。根 CLAUDE.md〈反事後諸葛取證規則〉要的
        是「沒觸發＝可偵測」，而回收是排程生命週期的另一半——武裝那半一直有痕跡，這半沒有。
        斷言逐項對應那個歸因問題：誰（`task`／`session_id`）、為什麼（`why`）、
        排程真的拆掉了嗎（`unregister_rc`）、殘骸掃了幾件（`swept`）、何時（`at`）。
        """
        row, trace = self._apply_once("r83-gc-trace")
        self.assertTrue(row["reap"], row)
        self.assertEqual(row["trace"], str(trace), "回收沒有回報痕跡落在哪裡")
        self.assertTrue(trace.is_file(), f"痕跡檔根本沒生出來：{trace}")
        record = json.loads(trace.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(record["event"], "gc_reaped")
        self.assertEqual(record["session_id"], "r83-gc-trace")
        self.assertEqual(record["task"], sentinel_lifecycle.TASK_PREFIX + "r83-gc-trace")
        self.assertEqual(record["unregister_rc"], 0)
        for key in ("why", "swept", "at"):
            self.assertIn(key, record, record)

    def test_a_trace_that_never_landed_is_not_reported_as_landed(self) -> None:
        """🔴 上一條的**牙**：判準是「那個檔變大了」，不是「寫入沒有拋例外」。

        注入的是真實形態而不是合成例外：`planner.append_log` 對寫不進去是**刻意吞掉**的
        （留不下痕跡不得升級成回收失敗），所以「靜默沒寫成」是這條路上真的會發生的事。
        少了這條斷言，`_record_reap` 可以無條件回傳路徑字串而全綠——那就變成「回報說留了
        痕跡，磁碟上沒有」，比完全不留痕跡更難看見（本 repo 對「憑證裡混一句假話」的判例）。
        """
        with unittest.mock.patch.object(planner, "append_log",
                                        lambda *a, **k: None):
            row, trace = self._apply_once("r83-gc-trace-mute")
        self.assertTrue(row["reap"], row)
        self.assertEqual(row["trace"], "", "痕跡沒寫成，卻回報成寫好了")
        self.assertFalse(trace.is_file(), f"對照組本身壞了：{trace} 竟然存在")


# ═══════════════════════════════════════════════════════════════════════════
# R82／C2：`.env` 裡設的逃生口必須真的算數
# ═══════════════════════════════════════════════════════════════════════════
#
# 病（複審鏡實測）：`.env.example` 逐字宣稱「生效路徑① 本檔（repo 根 .env）」，而三個
# 逃生口（`AUTOSDD_QUOTA_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF`／`AUTOSDD_CONTEXT_GUARD_OFF`）
# 全部直讀 `os.environ`、一律不經 `policy_env()` ⇒ 在 `.env` 裡設 `AUTOSDD_QUOTA_GUARD_OFF=1`
# → **rc=2（沒放行）**；設成真環境變數 → rc=0。「安全逃生口靜默失效」比沒有文件更糟：
# 人以為關掉了、守衛照擋，而兩者外觀完全相同。
#
# 修法是**一次前置填充**（`quota_gate.apply_env_defaults`，由 hook 的 `main()` 呼叫），
# 不是把每個讀取點改寫成 `policy_env()`。理由是射程：`SENTINEL_OFF_ENV` 有一個讀取點
# 住在 `arm_sentinel()` 裡，逐點改寫必然留下一個改不到的縫，而那個縫**正是本條在治的
# 靜默失效**。填充之後，每一個 `os.environ.get(<ENV_SPEC 宣告過的鍵>)` 都看得到 `.env`。
class EnvFileReachesEveryEscapeHatchTest(unittest.TestCase):
    _FLAGS = ("AUTOSDD_QUOTA_GUARD_OFF", "AUTOSDD_SENTINEL_OFF",
              "AUTOSDD_CONTEXT_GUARD_OFF")

    def setUp(self) -> None:
        # 🔴 開發機的 shell 真的會帶著這些鍵（落地當回合實測：`AUTOSDD_SENTINEL_OFF=1`
        # 就在環境裡）。不刷掉的話本組會拿「環境剛好有沒有設」當判準 ⇒ 在別人的機器上
        # 紅、在自己的機器上綠，而兩者都不是它要測的東西。
        patcher = unittest.mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for spec in quota_policy.ENV_SPEC:
            os.environ.pop(spec.name, None)

    def _tmpdir(self) -> Path:
        """🔴 R84／SA84-06：夾具**自己收自己的垃圾**。

        立案是量出來的：`ls $TMPDIR | grep -c autosdd_dotenv` ＝ **265**（複審當下的
        量測值，不是常數——落地時同一條指令已經 295，因為它每跑一次就漲）。本類每跑一次
        就在使用者的暫存區留下數個目錄，而它們永遠沒有人收。與哨兵孤兒 job 同一個病
        （測試在開發者機器上留下真實副作用），只是這一種安靜得多。
        落地驗證：接上本 cleanup 後，同一支模組跑完一輪的 delta ＝ **0**。
        """
        root = Path(tempfile.mkdtemp(prefix="autosdd_dotenv_"))
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def _dotenv(self, body: str) -> Path:
        root = self._tmpdir()
        (root / ".env").write_text(body, encoding="utf-8", newline="\n")
        return root

    def test_every_escape_hatch_in_the_example_reaches_the_process_env(self) -> None:
        """把 `.env.example` **原封不動**複製成 `.env`、只把三個開關填 1 ⇒ 三個都要生效。"""
        text = quota_policy.render_env_example()  # 逐字複製，不做任何清理
        for flag in self._FLAGS:
            text = text.replace(f"{flag}=", f"{flag}=1")
        root = self._dotenv(text)
        env: dict[str, str] = {}
        filled = qg.apply_env_defaults(env, root=root)
        for flag in self._FLAGS:
            with self.subTest(flag=flag):
                self.assertIn(flag, filled)
                self.assertEqual(env[flag], "1")

    def test_a_real_environment_variable_still_wins(self) -> None:
        """優先序 env > 檔案：已在行程 env 裡的鍵**不得**被檔案蓋掉。"""
        root = self._dotenv("AUTOSDD_QUOTA_HALT_PCT=60\n")
        env = {"AUTOSDD_QUOTA_HALT_PCT": "99"}
        self.assertEqual(qg.apply_env_defaults(env, root=root), [])
        self.assertEqual(env["AUTOSDD_QUOTA_HALT_PCT"], "99")

    def test_only_our_own_keys_are_filled(self) -> None:
        """🔴 `.env` 也是本 repo 放機密的地方（api_key／DSN）。白名單＝`ENV_SPEC`。

        整份灌進 `os.environ` 會讓機密隨 `Popen` 繼承到子行程——那是完全不同的授權面。
        """
        root = self._dotenv("MINIMAX_API_KEY=sk-secret\nAUTOSDD_SENTINEL_OFF=1\n")
        env: dict[str, str] = {}
        self.assertEqual(qg.apply_env_defaults(env, root=root), ["AUTOSDD_SENTINEL_OFF"])
        self.assertNotIn("MINIMAX_API_KEY", env)

    def test_red_without_the_prefill_the_hatch_is_invisible(self) -> None:
        """合成注入（缺陷本體）：不做前置填充時，`.env` 裡的開關對 `os.environ` 零影響。"""
        root = self._dotenv("AUTOSDD_QUOTA_GUARD_OFF=1\n")
        env: dict[str, str] = {}
        self.assertIsNone(env.get("AUTOSDD_QUOTA_GUARD_OFF"))
        qg.apply_env_defaults(env, root=root)     # ← 有它才看得到
        self.assertEqual(env.get("AUTOSDD_QUOTA_GUARD_OFF"), "1")

    def test_a_missing_env_file_is_not_a_fault(self) -> None:
        """額度守衛不得因為缺一個選配檔就變成故障源。"""
        self.assertEqual(qg.apply_env_defaults({}, root=self._tmpdir()), [])

    def test_the_quota_gate_itself_reads_the_hatch_through_the_merged_view(self) -> None:
        """端到端半：`quota_gate()` 對扇出型工具的放行必須真的吃 `.env` 的那個開關。"""
        root = self._dotenv("AUTOSDD_QUOTA_GUARD_OFF=1   # 我自己關掉\n")
        payload = {"tool_name": "Agent", "hook_event_name": "PreToolUse"}
        real = qg.policy_env   # 🔴 先抓住真的那一支，否則 patch 進去的 lambda 會自我遞迴
        with unittest.mock.patch.object(qg, "policy_env",
                                        lambda *_a, **_k: real(root)):
            with unittest.mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("AUTOSDD_QUOTA_GUARD_OFF", None)
                rc = qg.quota_gate(payload, blocking=("Agent",),
                                   latch_read=lambda _p: set(),
                                   latch_write=lambda _p, _k: None,
                                   plan_writer=lambda _t: "", waker=lambda _t, _p: {})
        self.assertEqual(rc, 0)

    def test_the_hook_main_really_calls_the_prefill(self) -> None:
        """🔴 接線鎖（「機制蓋好沒接電」是本 repo 反覆記載的形態）。

        判準讀 AST 而不是字串比對：`main()` 裡必須真的有 `apply_env_defaults` 這個呼叫，
        而且必須在 `arm_sentinel` 之前——`arm_sentinel` 是本輪唯一改不到的讀取點，
        它靠的就是「前面已經填好了」。
        """
        tree = ast.parse(_HOOK.read_text(encoding="utf-8"))
        main = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [(getattr(n.func, "attr", getattr(n.func, "id", "")), n.lineno)
                 for n in ast.walk(main) if isinstance(n, ast.Call)]
        prefill = [ln for name, ln in calls if name == "apply_env_defaults"]
        armed = [ln for name, ln in calls if name == "arm_sentinel"]
        self.assertEqual(len(prefill), 1, "main() 沒有（或重複）呼叫 apply_env_defaults")
        self.assertTrue(armed, "main() 找不到 arm_sentinel 呼叫 ⇒ 這條鎖的錨已經漂掉")
        self.assertLess(prefill[0], min(armed),
                        "前置填充必須在 arm_sentinel 之前，否則那個讀取點仍然看不到 .env")


class QuotaGateIsWiredToTheBurnPathTest(unittest.TestCase):
    """🔴 R83：額度那把尺造好了，卻接在一條**幾乎不通電**的線上——本類守的就是那條線。

    呼叫點條件此前是 `if blocking and …`，而 `blocking` 只在 PreToolUse 為真 ⇒ 額度只在
    「我要扇出」那一刻被問一次。R83 實測：配額 5%→90% 的整段，主 session 派完最後一波之後
    再也沒呼叫任何扇出型工具（後續全是全樹跑、agent 回傳、大量讀檔）⇒ 本閘一次都沒被叫到。
    它守的是「我要不要多派人」，燒掉額度的卻是「我自己在做事」。
    紅端（接電前實跑）：PostToolUse×{Read,Bash,Grep,Glob,Task} 一律 rc=0、stderr 0 位元組、
    零任務書、`decide()` 呼叫 0 次。⇒ 判例 #3「機制蓋好沒接電」已復發三次，故本類不驗
    「程式碼在不在」，只驗「它真的做了動作」。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="wired-burn-"))
        # 18% context：遠低於 WARN_RATIO ⇒ context 那把尺全程靜默，rc 只可能來自額度軸。
        self.transcript = _write_jsonl(self.tmp / "s.jsonl", [36_000])
        for name, value in (("quota_cache_path", lambda: self.tmp / quota_meter.CACHE_NAME),
                            ("fanout_ledger_path", lambda: self.tmp / "l.jsonl"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json"),
                            *_TRACE_ISOLATION(self)):
            old = getattr(qg, name)
            setattr(qg, name, value)
            self.addCleanup(setattr, qg, name, old)

    def _post(self, tool: str) -> dict:
        return {"hook_event_name": "PostToolUse", "tool_name": tool,
                "transcript_path": str(self.transcript)}

    def test_the_post_tool_use_matcher_covers_the_burn_path(self) -> None:
        matchers = [m for m, argv in _hook_invocations("PostToolUse")
                    if ".claude/hooks/context_budget_guard.py" in argv]
        self.assertTrue(matchers, "PostToolUse 上沒有本守衛 ⇒ 燒額度那條路零觀測者")
        for matcher in matchers:
            for tool in ("Read", "Bash"):
                self.assertIn(tool, matcher.split("|"),
                              f"matcher 被改窄、少了 {tool}：{matcher}")

    def test_the_quota_call_is_no_longer_gated_on_the_fanout_edge(self) -> None:
        """AST：呼叫點不得再被 `blocking` 罩住（那是紅端），且必須把 `event` 傳下去。"""
        main = next(n for n in ast.walk(ast.parse(_HOOK.read_text(encoding="utf-8")))
                    if isinstance(n, ast.FunctionDef) and n.name == "main")
        holders = [n for n in ast.walk(main) if isinstance(n, ast.If) and any(
            isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "quota_gate"
            for c in ast.walk(n.test))]
        self.assertEqual(len(holders), 1, "額度判定入口不是恰好一個 ⇒ 這條鎖的錨漂掉了")
        self.assertNotIn("blocking", {n.id for n in ast.walk(holders[0].test)
                                      if isinstance(n, ast.Name)},
                         "呼叫點又被 `blocking` 罩住 ⇒ 額度回到只在扇出邊緣被問一次")
        call = next(c for c in ast.walk(holders[0].test) if isinstance(c, ast.Call)
                    and getattr(c.func, "attr", "") == "quota_gate")
        self.assertIn("event", [kw.arg for kw in call.keywords],
                      "沒把事件名傳下去 ⇒ 射程與 D3 的事件名兩者同時失效")

    def test_post_tool_use_at_halt_writes_a_plan_and_says_so(self) -> None:
        """紅端這裡是 rc=0／stderr 0B／零任務書——那正是訴求 6c 至今沒生效的那一格。"""
        _quota_cache(self.tmp, 96.0)
        rc, err = _run_hook(self._post("Read"), self.tmp)
        self.assertEqual(rc, 2, "PostToolUse 在 halt 帶沒出聲 ⇒ stderr 到不了模型")
        self.assertIn("停止派發", err)
        self.assertTrue(list(self.tmp.glob(f"{guard.PLAN_PREFIX}*.md")),
                        "halt 帶沒把任務書寫到磁碟上（訴求 6c 的「記錄所有狀態」）")

    def test_the_halt_side_effects_run_exactly_once_per_reset_window(self) -> None:
        """副作用（寫任務書＋spawn 武裝）必須在閂鎖**之內**：否則 95% 之後每一次
        Read／Bash 都 spawn 一支 planner，而那會一直持續到 reset。"""
        _quota_cache(self.tmp, 96.0).replace(qg.quota_cache_path())
        calls, real = [], qg.quota_halt_actions

        def counted(*a: object, **k: object) -> dict:
            calls.append(1)
            return real(*a, **k)

        qg.quota_halt_actions = counted
        self.addCleanup(setattr, qg, "quota_halt_actions", real)
        sink = open(os.devnull, "w", encoding="utf-8")
        self.addCleanup(sink.close)
        old_err, sys.stderr = sys.stderr, sink
        self.addCleanup(setattr, sys, "stderr", old_err)
        rcs = {_gate(self._post("Read"), event="PostToolUse") for _ in range(20)}
        self.assertEqual(rcs, {2}, "halt 帶有幾次沒回 2 ⇒ 訊號斷斷續續")
        self.assertEqual(len(calls), 1, f"halt 副作用跑了 {len(calls)} 次 ⇒ spawn 風暴")

    def test_quota_halt_does_not_preempt_the_context_sentinel(self) -> None:
        """Δ13＝接電**引入**的新缺陷（不是既有債）：halt 帶每次都回 2 ⇒ hook 提早 return ⇒
        整個 halt 期間 `arm_when_earned` 一次都不執行；而額度那層的喚醒武裝只在閂鎖第一次
        觸發時試一次、失敗不重試 ⇒ 兩層續航都沒了。紅端實測：武裝次數由 5 掉到 0。"""
        _quota_cache(self.tmp, 96.0).replace(qg.quota_cache_path())
        armed: list[object] = []
        for name, value in (("read_payload", lambda: self._post("Read")),
                            ("arm_when_earned", armed.append),
                            ("write_resume_plan", lambda t: str(self.tmp / "p.md")),
                            ("arm_quota_wakeup", lambda t, p: {"armed": True})):
            old = getattr(guard, name)
            setattr(guard, name, value)
            self.addCleanup(setattr, guard, name, old)
        sink = open(os.devnull, "w", encoding="utf-8")
        self.addCleanup(sink.close)
        old_err, sys.stderr = sys.stderr, sink
        self.addCleanup(setattr, sys, "stderr", old_err)
        self.assertEqual(guard.main(), 2, "halt 帶沒回 2 ⇒ 這條測的前提就不成立")
        self.assertTrue(armed, "halt 帶下 context 哨兵一次都沒被武裝（Δ13 復發）")
        self.assertEqual(guard.main(), 2)
        self.assertEqual(len(armed), 2,
                         "只有閂鎖那一次武裝 ⇒ halt 期間其餘每一次呼叫都沒有續航保護")

    def test_post_tool_use_never_charges_the_dispatch_ledger(self) -> None:
        """同一個 `Task` 會先觸發 Pre 再觸發 Post；兩邊都記帳＝一次派發記兩次，滾動視窗
        預算當場少一半。對照組在同一條測試裡：Pre 必須記到 1。"""
        _quota_cache(self.tmp, 60.0).replace(qg.quota_cache_path())
        now = datetime.now(UTC).astimezone()
        self.assertEqual(_gate(self._post("Task"), event="PostToolUse"), 0)
        self.assertEqual(qg.live_dispatches(qg.fanout_ledger_path(), now), 0,
                         "PostToolUse 記了派發帳 ⇒ 同一次派發被記兩次")
        self.assertEqual(_gate({"hook_event_name": "PreToolUse", "tool_name": "Task",
                                "transcript_path": str(self.transcript)}), 0)
        self.assertEqual(qg.live_dispatches(qg.fanout_ledger_path(), now), 1,
                         "對照組也沒記帳 ⇒ 上一條的 0 是恆 0，沒有鑑別力")


# ═══════════════════════════════════════════════════════════════════════════
# R84：`ConsoleFreeSpawnTest` 的掃描面擴到 `AutoClaude/tools/hooks/**`
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 立案（Windows 彈窗窮舉的實測結論）：全庫 80 個 spawn 站點只有 10 個帶旗標，而本鎖的
# 宣告集合只有 14 支檔——`AutoClaude/**` **整片在射程外**。而那一層裡有一族與根層 hook
# 完全同構的東西：`AutoClaude/tools/hooks/*.py` 是子專案 session 的 Claude Code hook，
# 跑在**同一種無 console 的父行程**下 ⇒ 同一個危害、同一個修法、零判準。
#
# 🔴 為什麼是「擴面＋登記存量」而不是「擴面就好」：實測擴面後命中 **1 筆**，逐筆判讀是
# **真陽性**（`claude_md_freshness.py::check_snapshot_drift` 起一支 console 的
# `sys.executable`，無 `creationflags`），而那支檔不在本包的所有權內。兩個都不可接受的
# 選項：讓閘門紅著交件／把射程縮回去。第三條路＝本 repo 既有的 **shrink-only 存量棘輪**：
# 新站點一律紅，已登記的那一筆放行**但必須仍然真的違規**——有人修好了它，這張表就會
# stale 而轉紅，逼人把它拿掉。分子只准降。
# 🔴 錨用**函式名**不用行號：行號會隨那支檔的任何一次編輯漂掉，而漂掉的方向是靜默放行。
_AUTOCLAUDE_HOOK_NO_WINDOW_DEBT = frozenset({
    ("AutoClaude/tools/hooks/claude_md_freshness.py", "check_snapshot_drift"),
})


def _enclosing_function(src: str, lineno: int) -> str:
    """`lineno` 落在哪一支 `def` 裡（取最內層）。找不到回 `""`。"""
    best = ("", -1)
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):  # 3.9 相容形態
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end and node.lineno > best[1]:
                best = (node.name, node.lineno)
    return best[0]


class AutoClaudeHookSpawnIsInScopeTest(unittest.TestCase):
    """子專案 hook 的 spawn 也必須不開視窗——它們與根層 hook 是同一種父行程。"""

    @staticmethod
    def _sources() -> dict[str, str]:
        base = _REPO_ROOT / "AutoClaude" / "tools" / "hooks"
        return {f"AutoClaude/tools/hooks/{p.name}": p.read_text(encoding="utf-8")
                for p in sorted(base.glob("*.py"))}

    def _violations(self) -> set[tuple[str, str]]:
        sources = self._sources()
        found = set()
        for problem in no_window_problems(sources):
            where = problem.split("：")[0]
            name, _, lineno = where.rpartition(":")
            found.add((name, _enclosing_function(sources[name], int(lineno))))
        return found

    def test_the_surface_is_not_empty(self) -> None:
        """分母自檢：掃到 0 支檔＝這道鎖靜默歸零（本 repo 判過的形態）。"""
        self.assertGreaterEqual(len(self._sources()), 5, "子專案 hook 掃描面疑似縮小")

    def test_no_unregistered_site_spawns_a_console(self) -> None:
        """新站點一律紅。已登記的存量放行——但只有這一筆。"""
        unregistered = self._violations() - _AUTOCLAUDE_HOOK_NO_WINDOW_DEBT
        self.assertEqual(unregistered, set(),
                         f"子專案 hook 新增了會開視窗的 spawn：{sorted(unregistered)}"
                         "（修法：`creationflags=getattr(subprocess, \"CREATE_NO_WINDOW\", 0)`）")

    def test_the_debt_registry_only_shrinks(self) -> None:
        """棘輪的另一半：登記的每一筆都必須**仍然真的違規**，否則這張表在放行空氣。"""
        stale = _AUTOCLAUDE_HOOK_NO_WINDOW_DEBT - self._violations()
        self.assertEqual(stale, set(),
                         f"這幾筆存量已經修好了，請把它們從登記表刪掉：{sorted(stale)}")

    def test_red_an_injected_flagless_spawn_is_caught(self) -> None:
        """🔴 合成注入：一支沒有旗標的新 hook ⇒ 判準必須指名它。"""
        injected = {"AutoClaude/tools/hooks/zz_new_hook.py":
                    "import subprocess\ndef main():\n    subprocess.run(['git', 'status'])\n"}
        problems = no_window_problems(injected)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("zz_new_hook.py:3", problems[0])
        self.assertEqual(
            _enclosing_function(injected["AutoClaude/tools/hooks/zz_new_hook.py"], 3), "main")
        # 綠端對照：同一支檔帶上旗標即放行（否則這條鎖鎖的是「有沒有 spawn」）
        self.assertEqual(no_window_problems({"z.py": (
            "import subprocess\ndef main():\n    subprocess.run(['git'], creationflags="
            'getattr(subprocess, "CREATE_NO_WINDOW", 0))\n')}), [])


# ═══════════════════════════════════════════════════════════════════════════
# R84／6C：prepare 帶（85~95%）真的要做準備動作 —— SA-03
# ═══════════════════════════════════════════════════════════════════════════
class QuotaPrepareBandActuallyPreparesTest(unittest.TestCase):
    """🔴 紅端（本輪落地前對 HEAD 實跑，逐字）：合成 86% 快取走真閘 ⇒
    `event=PostToolUse tool=Read rc=0 stderr_bytes=0 plan_writer_calls=0`；
    `event=PreToolUse tool=Read rc=0 stderr_bytes=0`。對照 96%：`rc=2 stderr_bytes=607`。

    也就是 85% 這一帶唯一真的會發生的事，是 PreToolUse×`Workflow` 被擋
    （`UNBOUNDED_FANOUT_TOOLS` 只有這一個成員）；`Read`／`Task` 全部靜默放行，
    而訴求 6C 要的「提前準備下一次 reset」一份任務書都沒有——外觀與「額度很健康」相同。
    R83 交棒書把射程記成只有 PostToolUse，實測**兩個事件都靜默**。

    本類刻意不驗「程式碼在不在」，只驗它真的做了那三件事（出聲／落磁碟／一個視窗一次），
    以及**沒有**做第四件事（改 rc）——85% 擋下收斂型工作會讓人連收斂都做不完。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="prepare-band-"))
        self.transcript = _write_jsonl(self.tmp / "s.jsonl", [36_000])
        for name, value in (("quota_cache_path", lambda: self.tmp / quota_meter.CACHE_NAME),
                            ("fanout_ledger_path", lambda: self.tmp / "l.d"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json"),
                            *_TRACE_ISOLATION(self)):
            old = getattr(qg, name)
            setattr(qg, name, value)
            self.addCleanup(setattr, qg, name, old)
        self.plans: list[object] = []
        self.err = io.StringIO()

    def _gate_with_spy(self, event: str, tool: str = "Read", pct: float = 86.0) -> int:
        _quota_cache(self.tmp, pct)
        payload = {"hook_event_name": event, "tool_name": tool,
                   "transcript_path": str(self.transcript)}

        def plan_writer(transcript: object) -> str:
            self.plans.append(transcript)
            path = self.tmp / "prepare_plan.md"
            path.write_text("# 可重啟點骨架\n", encoding="utf-8", newline="\n")
            return str(path)

        with contextlib.redirect_stderr(self.err):
            return qg.quota_gate(payload, blocking=guard.BLOCKING_TOOLS,
                                 latch_read=guard.announced_latches,
                                 latch_write=guard.remember_latch,
                                 plan_writer=plan_writer,
                                 waker=guard.arm_quota_wakeup, event=event)

    def test_both_events_speak_and_leave_a_restart_point(self) -> None:
        """射程是**兩個**事件（R83 交棒書只記了 PostToolUse 那一半）；各自要出聲＋落任務書。

        🔴 誠實劃界（SA-03 的紅端證據裡混了一格治不了的）：`PreToolUse` 只在**扇出邊緣**
        被叫（`tool not in blocking` 就早退，那是刻意的——收斂型工具不受額度節流），
        所以 `PreToolUse×Read` 在 86% 仍然是零位元組，而且**應該是**。那一格由
        `PostToolUse`（射程是註冊面上的每一個工具）覆蓋 ⇒ 兩者合起來的性質才是本輪要的：
        「進了 prepare 帶之後，**第一次**工具呼叫就會出聲並留下可重啟點」。
        """
        for event, tool in (("PostToolUse", "Read"), ("PreToolUse", "Task")):
            with self.subTest(event=event, tool=tool):
                self.err, self.plans = io.StringIO(), []
                (self.tmp / "latch.json").unlink(missing_ok=True)
                rc = self._gate_with_spy(event, tool)
                said = self.err.getvalue()
                self.assertEqual(rc, 0, "prepare 帶擋下了收斂型工具 ⇒ 人連收斂都做不完")
                self.assertGreater(len(said.encode("utf-8")), 0,
                                   f"{event} 在 86% 仍是零位元組 ⇒ 與「額度很健康」同形")
                self.assertIn("準備", said)
                self.assertEqual(len(self.plans), 1, "沒有產出可重啟點任務書骨架")
                self.assertTrue((self.tmp / "prepare_plan.md").is_file())

    def test_pre_tool_use_on_a_convergent_tool_is_still_silent_by_design(self) -> None:
        """對照組（守住上一支那句劃界不是藉口）：`PreToolUse×Read` 必須維持零位元組——
        收斂型工具不受額度節流，這一帶的出聲責任在 `PostToolUse` 那一側。"""
        self.assertEqual(self._gate_with_spy("PreToolUse", "Read"), 0)
        self.assertEqual(self.err.getvalue(), "")
        self.assertEqual(self.plans, [])

    def test_it_speaks_once_per_reset_window_not_once_per_tool_call(self) -> None:
        """去重沿用 halt 那套閂鎖鍵：否則 85% 之後每一次 Read 都 spawn 一支 planner。"""
        first = self._gate_with_spy("PostToolUse")
        for _ in range(9):
            self._gate_with_spy("PostToolUse")
        self.assertEqual(first, 0)
        self.assertEqual(len(self.plans), 1,
                         f"prepare 帶寫了 {len(self.plans)} 份任務書 ⇒ spawn 風暴")

    def test_the_other_bands_stay_silent(self) -> None:
        """鑑別力：這一段不得把 notice／free 帶也變吵（那會讓守衛被整個關掉）。"""
        for pct in (20.0, 55.0):
            with self.subTest(pct=pct):
                self.err, self.plans = io.StringIO(), []
                (self.tmp / "latch.json").unlink(missing_ok=True)
                self.assertEqual(self._gate_with_spy("PostToolUse", pct=pct), 0)
                self.assertEqual(self.err.getvalue(), "")
                self.assertEqual(self.plans, [])

    def test_red_the_early_return_order_matters(self) -> None:
        """🔴 合成注入：把 prepare 段挪到那道早退**之後** ⇒ `PostToolUse` 一行都到不了。

        這一支守的是位置而不是存在——本缺陷的原形就是「函式對了但沒人叫它」，而
        `if decision.cap is None or event != "PreToolUse": return 0` 對 PostToolUse
        是無條件早退。
        """
        src = (_REPO_ROOT / "tools" / "lib" / "quota_gate.py").read_text(encoding="utf-8")
        body = next(n for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.FunctionDef) and n.name == "quota_gate").body
        def line_of(pred) -> int:
            return next(n.lineno for n in body if pred(n))
        prepare = line_of(lambda n: "BAND_PREPARE" in ast.dump(n))
        early = line_of(lambda n: isinstance(n, ast.If)
                        and "event !=" in ast.unparse(n.test)
                        and "PreToolUse" in ast.unparse(n.test))
        self.assertLess(prepare, early, "prepare 段落在早退之後 ⇒ PostToolUse 到不了")


# ═══════════════════════════════════════════════════════════════════════════
# R84／6b 第二半：「我現在能派幾個 agent」必須有一個人問得到的出口 —— SA-02／SA-06
# ═══════════════════════════════════════════════════════════════════════════
class QuotaPaceOutletIsReachableTest(unittest.TestCase):
    """🔴 紅端：`python tools/lib/quota_policy.py` → rc=2 只印用法；
    `quota_meter.py --from-cache --json` → rc=0 但全文無 band／cap／pace／recommended；
    `describe()` 的唯一呼叫端是被擋下時的三個 stderr 寫入點 ⇒ 舵手要拿到那個數字，
    今天唯一的途徑是**先被守衛擋下**。訴求 6a「隨時監控」在人機介面這一側等於不存在。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pace-outlet-"))
        for name, value in (("quota_cache_path", lambda: self.tmp / quota_meter.CACHE_NAME),
                            *_TRACE_ISOLATION(self)):
            old = getattr(qg, name)
            setattr(qg, name, value)
            self.addCleanup(setattr, qg, name, old)

    def test_the_one_line_carries_all_five_facts(self) -> None:
        """一行內要有：可派幾個／cap／band／最緊那一軸具名／它距 reset 幾分鐘。"""
        _quota_cache(self.tmp, 35.0, kind="weekly_all", resets_in=99 * 3600,
                     extra=(("nimbus_quill", 0.0, None), ("session", 20.0, 20 * 60)))
        line = qg.pace_report().splitlines()[0]
        for token in ("可派", "cap=", "band=", "最緊的一條＝", "分鐘"):
            self.assertIn(token, line, f"`--pace` 第一行少了 {token}：{line}")
        # SA-06：binding 必須是**真的在消耗**的那一軸，不是 0%／reset 不明那一個
        self.assertIn("weekly_all", line, f"binding 又指向零消耗的軸：{line}")
        self.assertNotIn("nimbus_quill", line)

    def test_it_reads_the_cache_and_does_not_touch_the_network(self) -> None:
        """🔴 零 token 是硬要求：舵手每次派工前查一次，不能因此付一次額度。"""
        _quota_cache(self.tmp, 35.0)
        calls: list[object] = []
        old = quota_meter.measure_detail
        quota_meter.measure_detail = lambda *a, **k: calls.append(a) or (None, "spy")
        self.addCleanup(setattr, quota_meter, "measure_detail", old)
        self.assertIn("可派", qg.pace_report())
        self.assertEqual(calls, [], "快取新鮮卻還是去打端點 ⇒ 查一次就花一次")

    def test_an_unusable_cache_costs_at_most_one_measurement_per_ttl(self) -> None:
        """快取不可用時可以補量，但**每 TTL 至多一次**（否則它變成一個成本放大器）。"""
        calls: list[object] = []
        old = quota_meter.measure_detail
        quota_meter.measure_detail = lambda *a, **k: calls.append(a) or (None, "spy")
        self.addCleanup(setattr, quota_meter, "measure_detail", old)
        for _ in range(5):
            qg.pace_report()
        self.assertEqual(len(calls), 1, f"補量 {len(calls)} 次 ⇒ TTL 名額沒生效")

    def test_the_cli_flag_exists_and_needs_no_transcript(self) -> None:
        """CLI 掛在既有人機入口；且**不依賴逐字稿**——找不到 session 不該連額度都查不到。"""
        args = planner.build_parser().parse_args(["--pace"])
        self.assertTrue(args.pace)
        main_src = ast.unparse(next(
            n for n in ast.walk(ast.parse(
                (_REPO_ROOT / "tools" / "session_resume_planner.py").read_text(
                    encoding="utf-8")))
            if isinstance(n, ast.FunctionDef) and n.name == "main"))
        pace_at = main_src.index("args.pace")
        resolve_at = main_src.index("resolve_transcript")
        self.assertLess(pace_at, resolve_at,
                        "--pace 掛在逐字稿解析之後 ⇒ 找不到 session 的機器上查不到額度")

    def test_it_says_why_an_empty_short_window_still_cannot_be_burned(self) -> None:
        """🔴 R86：掌舵者看到「短窗還很空、卻只能派 2 個」時，畫面必須自己回答為什麼。

        他當時看到的只有 `binding=seven_day` ⇒ 讀起來像程式抓錯。同一次呼叫也必須落款
        一列（換算比只能從歷時差分推估）。判準本體＝`quota_criteria.pace_line_problems`。
        """
        _quota_cache(self.tmp, 75.0, kind="seven_day", resets_in=72 * 3600,
                     extra=(("five_hour", 16.0, 42 * 60),))
        report = qg.pace_report()
        self.assertEqual(quota_criteria.pace_line_problems(report), [], report)
        ledger = qg.burn_ledger_path()
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1,
                         "查了一次卻沒有落款 ⇒ 樣本永不累積")
        qg.pace_report()   # 同一份快取再查一次：不得寫出第二列重複觀測
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_the_unmeasurable_case_says_so_instead_of_looking_healthy(self) -> None:
        """量不到時**不得**印一個看起來很寬鬆的數字（那正是本 repo 判過的假綠形態）。"""
        old = quota_meter.measure_detail
        quota_meter.measure_detail = lambda *a, **k: (None, "spy")
        self.addCleanup(setattr, quota_meter, "measure_detail", old)
        report = qg.pace_report()
        self.assertIn("量不到", report, f"量不到卻沒說：{report}")


if __name__ == "__main__":
    unittest.main()
