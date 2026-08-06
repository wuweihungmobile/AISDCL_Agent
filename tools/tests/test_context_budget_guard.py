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

import json
import os
import subprocess
import sys
import tempfile
import unittest
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


def _run_hook(payload: object, tmp: Path) -> tuple[int, str]:
    """以子行程真跑 hook，回 `(rc, stderr)`。

    走子行程而非 import＋呼叫 `main()`：hook 的契約是「被 Claude Code 以獨立行程呼叫、
    讀 stdin、以 exit code 表態」，import 進來會繞過 stdin 與 exit code 這兩個契約面
    （本 repo「驗證載具必須對齊 production 真正執行路徑」的既有紀律）。
    `TMPDIR`／`TEMP`／`TMP` 三個都指向本測試自己的目錄：去重 state 檔住在那裡，
    不隔離的話測試之間會互相污染，而污染的方向正好是「看起來通過」。
    """
    env = dict(os.environ)
    env.update({"TMPDIR": str(tmp), "TEMP": str(tmp), "TMP": str(tmp)})
    env.pop("AUTOSDD_CONTEXT_WINDOW", None)
    env.pop("SDD_ACTIVE_VERSION", None)
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

    def test_degenerate_inputs_all_fail_open(self) -> None:
        """P0：守衛自身絕不可成為故障源。四種退化輸入一律 rc=0。"""
        cases = {
            "壞 JSON": "{not json",
            "空 stdin": "",
            "缺 transcript_path": json.dumps({"tool_name": "Read"}),
            "transcript_path 指向不存在的檔": json.dumps(
                {"transcript_path": str(self.tmp / "ghost.jsonl")}),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertEqual(_run_hook(text, self.tmp), (0, ""))

    def test_env_override_reaches_the_running_hook(self) -> None:
        """指定值必須真的傳得到 production 路徑（不是只有純函式吃得到）。"""
        env = dict(os.environ)
        env.update({"TMPDIR": str(self.tmp), "TEMP": str(self.tmp), "TMP": str(self.tmp),
                    "AUTOSDD_CONTEXT_WINDOW": "1000000"})
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
            capture_output=True,
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


if __name__ == "__main__":
    unittest.main()
