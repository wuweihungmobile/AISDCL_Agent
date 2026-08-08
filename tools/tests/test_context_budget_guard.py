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

    def test_sessionstart_is_registered_and_points_at_this_guard(self) -> None:
        """🔴 本包的重點不是工具、是**接電**。沒有這個註冊條目，哨兵就永遠只是一支
        「要人記得去按」的指令——而那正是 R77『機制蓋好沒接電』的第三次復發。
        """
        commands = [argv for _, argv in _hook_invocations("SessionStart")]
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
            self.skipTest("[WINDOWS-NATIVE-ONLY] schtasks 武裝只在 Windows 成立（鐵律三：單平台判準不外推）")
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
            self.skipTest("[WINDOWS-NATIVE-ONLY] 同上：本分支只在 Windows 有行為")
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

#: 掃描面檔數下限。現值＝R80 實測（1 支 planner ＋ 4 支 hook）。只准上修。
_CONSOLE_FREE_FLOOR = 5


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
        for call in _spawn_calls(tree):
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
        paths = {"tools/session_resume_planner.py": _PLANNER}
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


if __name__ == "__main__":
    unittest.main()
