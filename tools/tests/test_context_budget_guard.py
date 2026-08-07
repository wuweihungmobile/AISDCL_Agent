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
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "context_budget_guard.py"
_PLANNER = _REPO_ROOT / "tools" / "session_resume_planner.py"

sys.path.insert(0, str(_HOOK.parent))
import context_budget_guard as guard  # noqa: E402


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


def _isolated_env(tmp: Path) -> dict[str, str]:
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
    for flag in ("AUTOSDD_CONTEXT_WINDOW", "SDD_ACTIVE_VERSION",
                 "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "AUTOSDD_CONTEXT_GUARD_OFF",
                 "AUTOSDD_SENTINEL_OFF"):
        env.pop(flag, None)
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
        self.assertEqual(guard.scan_usage(path), (300, 900))

    def test_peak_is_not_just_the_tail(self) -> None:
        """注入：若實作改成只讀尾巴，peak 會塌成 300 ⇒ window 下界推論失去輸入。"""
        path = _write_jsonl(self.tmp / "b.jsonl", [250_001, 300])
        self.assertEqual(guard.scan_usage(path)[1], 250_001)
        self.assertEqual(guard.resolve_window(guard.scan_usage(path)[1])[0],
                         guard.WIDE_WINDOW)

    def test_broken_lines_are_skipped_not_fatal(self) -> None:
        path = _write_jsonl(self.tmp / "c.jsonl", [100, 200], junk=True)
        self.assertEqual(guard.scan_usage(path), (200, 200))

    def test_no_usage_at_all_is_unmeasurable(self) -> None:
        path = self.tmp / "d.jsonl"
        path.write_text('{"type":"user"}\n', encoding="utf-8", newline="\n")
        self.assertEqual(guard.scan_usage(path), (None, 0))

    def test_missing_file_is_unmeasurable_not_zero(self) -> None:
        self.assertEqual(guard.scan_usage(self.tmp / "nope.jsonl"), (None, 0))


class HookExitContractTest(unittest.TestCase):
    """端到端：真子行程 × 真 stdin × 真 exit code。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxguard-e2e-"))

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
        """
        settings = json.loads(
            (_REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))
        matchers = [
            str(entry.get("matcher", ""))
            for entry in settings.get("hooks", {}).get("PreToolUse", []) or []
            if any("context_budget_guard" in str(h.get("command", ""))
                   for h in entry.get("hooks") or [])
        ]
        self.assertEqual(len(matchers), 1, f"PreToolUse 註冊條目數不是 1：{matchers}")
        self.assertEqual(
            set(matchers[0].split("|")), set(guard.BLOCKING_TOOLS),
            f"註冊 matcher {matchers[0]!r} 與腳本射程 {guard.BLOCKING_TOOLS} 不一致",
        )


# ═══════════════════════════════════════ R79 續航協定（ADR-XPLAT-004）的回歸鎖
# 這一段守的性質與上面四類**不同**：上面守 context 水位，這裡守**額度**。兩者是兩個
# 分母（window vs 計費週期），混為一談是本題最常見的錯誤——額度耗盡當下水位可能只有
# 20%，阻斷模式的四道放行條件會全數放行。鎖也照這條界線分開寫。

sys.path.insert(0, str(_REPO_ROOT / "tools"))
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
        self.assertNotIn("Write-Output", outside,
                         "payload 逃出單引號字串、成為一段會被真的執行的獨立指令")

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
        把它改回 `python.exe` 就是那個缺陷本身，故本條必須紅。"""
        script = planner.endurance_schtasks_script(_A_PLAN, "T", "'09:00'")
        self.assertIn("pythonw.exe", script)

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
        for name in ("classify_limit", "parse_reset_at", "latest_limit_event"):
            with self.subTest(name=name):
                self.assertNotIn(name, body, f"`{name}` 被接進阻斷路徑了")


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
        """🔴 沒有這一條，哨兵會**每次醒來都探測一次**同一筆早就解決掉的撞線。

        成本是實的：15 分鐘一次 × 每次約 32K tokens。判準＝事件時間戳嚴格大於狀態塊裡
        的 `handled_through`；武裝當下把「現存最後一筆」記成已處理，理由是可證的——
        我們此刻跑得動武裝指令，就證明額度是通的。
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

    def test_the_patrol_interval_fits_inside_the_shortest_observed_window(self) -> None:
        """🔴 巡邏間隔是**量出來的常數**，這一條就是它的量測。

        全庫實測那次真實撞線：08:44 撞、訊息逐字 `resets 9am` ⇒ hit→reset 只有 16 分鐘。
        間隔一旦大於它，「reset 未到 ⇒ 精確重排」那一支在最短窗下**結構上不可達**，
        整個機制退化成只會事後補救。把 `SENTINEL_INTERVAL_SECONDS` 調到 16 分鐘以上即紅。
        """
        hit = datetime(2026, 8, 7, 0, 44, tzinfo=UTC).astimezone(_TAIPEI)
        shortest = (guard.parse_reset_at(_REAL_SESSION_LIMIT, hit) - hit).total_seconds()
        self.assertEqual(shortest, 16 * 60, "語料變了 ⇒ 這個常數的立案量測要重做")
        self.assertLess(planner.SENTINEL_INTERVAL_SECONDS, shortest)

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

    def test_sessionstart_is_registered_and_points_at_this_guard(self) -> None:
        """🔴 本包的重點不是工具、是**接電**。沒有這個註冊條目，哨兵就永遠只是一支
        「要人記得去按」的指令——而那正是 R77『機制蓋好沒接電』的第三次復發。
        """
        settings = json.loads(
            (_REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))
        commands = [str(h.get("command", ""))
                    for entry in settings.get("hooks", {}).get("SessionStart", []) or []
                    for h in entry.get("hooks") or []]
        # 比對**完整路徑**而不是裸檔名：`tools/tests/test_context_budget_guard.py`
        # 也含後者，裸檔名判準會被一個不相干的字串滿足（本輪注入實測踩到這一格）。
        self.assertTrue(
            [c for c in commands if ".claude/hooks/context_budget_guard.py" in c],
            f"SessionStart 沒有掛上哨兵武裝 ⇒ 沒有任何東西會自動武裝它：{commands}")

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

    def test_sessionstart_actually_spawns_the_arming_run(self) -> None:
        """🔴 端到端的**接線**證明：hook 真的把 planner 叫起來，且帶著 --arm-sentinel。

        只斷言 rc=0 會恆綠（fail-open 的守衛對任何輸入都回 0）。這裡改看**副作用**：
        替身被執行後留下的 argv。這一條在把 `arm_sentinel()` 從 `main()` 拿掉時會紅。
        """
        if os.name != "nt":
            self.skipTest("schtasks 武裝只在 Windows 成立（鐵律三：單平台判準不外推）")
        marker = self.tmp / "argv.json"
        proc = self._sessionstart(self._fake_repo(marker))
        self.assertEqual((proc.returncode, proc.stderr), (0, ""),
                         "SessionStart 這一支必須恆靜默、恆 exit 0")
        self.assertTrue(_wait_for(marker, 30.0),
                        "武裝子行程根本沒被起起來（30s 內沒有痕跡）")
        argv = json.loads(marker.read_text(encoding="utf-8"))
        self.assertIn("--arm-sentinel", argv)
        self.assertIn("--transcript", argv)
        self.assertIn(str(self.tmp / "live.jsonl"), argv)

    def test_the_off_switch_really_stops_it(self) -> None:
        """人的逃生口。與 context 阻斷那一個刻意分開：兩者關掉的是不同的東西。"""
        if os.name != "nt":
            self.skipTest("同上：本分支只在 Windows 有行為")
        marker = self.tmp / "argv_off.json"
        proc = self._sessionstart(self._fake_repo(marker),
                                  {"AUTOSDD_SENTINEL_OFF": "1"})
        self.assertEqual((proc.returncode, proc.stderr), (0, ""))
        self.assertFalse(_wait_for(marker, 5.0), "逃生口沒有真的擋住武裝")

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


if __name__ == "__main__":
    unittest.main()
