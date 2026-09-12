"""Unit tests for ACT-024 Ledger Precision Upgrade (Phase E M2)."""
from __future__ import annotations

import datetime as _dt
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import yaml  # noqa: E402

from tools.fsm_runtime import conversation_ledger  # noqa: E402
from tools.fsm_runtime.conversation_ledger import (  # noqa: E402
    LedgerReplaceDenied,
    append_ledger_entry,
    cleanup_orphan_part_files,
    estimate_bash_command_tokens,
    estimate_conversation_overhead,
    estimate_read_tokens,
    estimate_tool_tokens,
    merge_conversation_overhead_into_ledger,
    record_calibration_sample,
    write_sidecar,
)


class LedgerPrecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_ledger(self, entries: list) -> Path:
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        doc = {
            "date": date,
            "cumulative_tokens": sum(int(e.get("tokens", 0)) for e in entries),
            "entries": entries,
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def test_read_tokens_include_line_prefix_overhead(self) -> None:
        src = self.root / "sample.txt"
        content = "line1\nline2\nline3\nline4\nline5\n"
        src.write_text(content, encoding="utf-8")
        size_only_estimate = max(1, src.stat().st_size // 4)
        precise = estimate_read_tokens(str(src))
        # Precise estimate should be >= size-only due to cat -n prefix overhead
        self.assertGreater(precise, size_only_estimate - 1)
        # And bounded — should not exceed size + 5*8 chars worth of tokens
        upper = (src.stat().st_size + 5 * 8) // 4 + 1
        self.assertLessEqual(precise, upper)

    def test_read_tokens_returns_zero_for_missing_file(self) -> None:
        self.assertEqual(estimate_read_tokens(str(self.root / "nope.txt")), 0)
        self.assertEqual(estimate_read_tokens(None), 0)
        self.assertEqual(estimate_read_tokens(""), 0)

    def test_bash_command_estimate(self) -> None:
        self.assertEqual(estimate_bash_command_tokens(None), 0)
        self.assertEqual(estimate_bash_command_tokens(""), 0)
        self.assertEqual(estimate_bash_command_tokens("ls -la"), max(1, len("ls -la") // 4))

    def test_conversation_overhead_scales_linearly(self) -> None:
        self.assertEqual(estimate_conversation_overhead(0), 0)
        self.assertEqual(estimate_conversation_overhead(1), 300)
        self.assertEqual(estimate_conversation_overhead(10), 3000)

    def test_estimate_tool_tokens_dispatches(self) -> None:
        # Task estimate must include conversation overhead (300 tokens / turn)
        # on top of the prompt tokens — see Rule 9.8.2 / ACT-024 P1-06 fix.
        prompt = "abcd" * 40
        prompt_tokens = max(1, len(prompt) // 4)
        self.assertEqual(
            estimate_tool_tokens("Task", {"prompt": prompt}),
            prompt_tokens + estimate_conversation_overhead(1),
        )
        self.assertEqual(estimate_tool_tokens("Unknown", {}), 0)

    def test_task_estimate_includes_conversation_overhead(self) -> None:
        """Pure regression for P1-06: Task without prompt still pays subagent
        overhead because the subagent system-prompt is non-trivial."""
        zero_prompt = estimate_tool_tokens("Task", {"prompt": ""})
        self.assertGreaterEqual(zero_prompt, estimate_conversation_overhead(1))
        big_prompt = estimate_tool_tokens("Task", {"prompt": "x" * 4000})
        self.assertGreaterEqual(
            big_prompt - zero_prompt, 1000 - 1,
            "prompt-driven delta should match len(prompt)//4",
        )

    def test_merge_below_threshold_noop(self) -> None:
        # 10 entries = 5 tool calls (pre+post each writes an entry).
        # Under the new entries_per_call=2 semantics this must NOT trigger
        # when merge_every=10 tool calls.
        self._write_ledger([{"tokens": 100} for _ in range(10)])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])
        self.assertEqual(res["added_tokens"], 0)

    def test_merge_at_threshold_appends_conv_overhead_entry(self) -> None:
        # P1-06 fix: merge_every=10 now means 10 tool calls = 20 entries.
        path = self._write_ledger([{"tokens": 100} for _ in range(20)])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["cumulative_tokens"], 2000 + 3000)
        self.assertEqual(doc["entries"][-1]["phase"], "conv-overhead")
        self.assertEqual(doc["entries"][-1]["messages_counted"], 10)
        self.assertEqual(doc["entries"][-1]["entries_counted"], 20)
        # A second immediate call should not double-count
        res2 = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res2["merged"])

    def test_merge_pre_post_pairs_equal_one_tool_call(self) -> None:
        """P1-06 regression: 20 entries from pre+post pairs = 10 tool calls,
        and only ONE conv-overhead entry of 3000 tokens is appended — not two
        as would happen under the old "every 10 entries" semantics."""
        path = self._write_ledger([
            {"tokens": 50, "phase": "pre" if i % 2 == 0 else "post"}
            for i in range(20)
        ])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        conv_entries = [e for e in doc["entries"] if e.get("phase") == "conv-overhead"]
        self.assertEqual(len(conv_entries), 1, "10 tool calls must emit exactly ONE merge")
        self.assertEqual(conv_entries[0]["messages_counted"], 10)

    def test_merge_entries_per_call_override(self) -> None:
        """Allow callers (tests / future hook changes) to count entries-per-call
        explicitly. With entries_per_call=1 the historical 'every 10 entries'
        semantics is preserved for backward-compat callers."""
        path = self._write_ledger([{"tokens": 100} for _ in range(10)])
        res = merge_conversation_overhead_into_ledger(
            self.root, merge_every=10, entries_per_call=1,
        )
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["entries"][-1]["messages_counted"], 10)

    def test_merge_with_no_ledger_is_safe(self) -> None:
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])

    def test_sidecar_merges_into_primary_at_tick(self) -> None:
        """QA Round-3 P2-07 — when file_lock contention routes entries to a
        `.append` sidecar, the next merge tick must fold them back into the
        primary ledger so delta_entries is accurate and sidecars don't leak.
        """
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        # 10 entries in primary; 10 more staged in sidecar. Total 20 = 10 tool
        # calls at entries_per_call=2 — exactly the merge threshold.
        self._write_ledger([{"tokens": 100, "phase": "pre"} for _ in range(10)])
        sidecar = path.with_suffix(path.suffix + ".append")
        sidecar_entries = [{"tokens": 100, "phase": "post"} for _ in range(10)]
        with sidecar.open("w", encoding="utf-8") as f:
            yaml.safe_dump(sidecar_entries, f, allow_unicode=True, sort_keys=False)

        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["sidecar_merged"], 10)
        self.assertFalse(sidecar.exists(), "sidecar must be consumed after merge")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Original 1000 + sidecar 1000 + conv overhead 3000 = 5000.
        self.assertEqual(doc["cumulative_tokens"], 5000)
        # 20 real entries + 1 conv-overhead entry = 21 entries total.
        self.assertEqual(len(doc["entries"]), 21)
        # A follow-up merge should not double count (sidecar already consumed).
        res2 = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res2["merged"])

    def test_sidecar_folded_below_threshold_is_persisted(self) -> None:
        """DEF-200-275 第四輪 G3（SD-R2-01，HEAD 既有；先紅再綠）：`_merge_locked` 先把 sidecar 併進記憶體
        doc，隨後 `delta_calls < merge_every` 早退**不寫檔** ⇒ 折回的 entries 磁碟上永久消失
        （預設 merge_every=10 ⇒ 20 個 tick 只有 1 個真的持久化，其餘 19 個折回＝刪除）。F2 讓 post hook
        逾時唯一出口是 sidecar，這條路徑因此承重；docstring 宣稱「下次 merge 折回主檔」必須為真。
        D31b-1 起 `write_sidecar` 每筆一檔，故用 glob 找家族檔名而非精確比對單一路徑。"""
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        self._write_ledger([{"tokens": 100, "phase": "pre"}])
        for tokens in (11, 22, 33):  # 3 筆共 66 tokens，遠低於 merge 門檻（10 calls × 2 entries）
            write_sidecar(self.root, {"tokens": tokens, "phase": "post"})
        sidecar_files = sorted(self.root.glob(f"{path.name}.append.*"))
        self.assertEqual(len(sidecar_files), 3, msg="D31b：每筆一檔，應有 3 份 sidecar")
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])
        self.assertEqual(res.get("sidecar_merged"), 3, msg=res)
        self.assertFalse(list(self.root.glob(f"{path.name}.append.*")), "sidecar 折回後應被消耗")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["entries"]), 4, msg=f"折回的 3 筆必須在磁碟上：{doc}")
        self.assertEqual(doc["cumulative_tokens"], 166)
        self.assertEqual(append_ledger_entry(self.root, {"tokens": 9, "phase": "pre"}), 175)

    def test_sidecar_absent_does_not_report_merge(self) -> None:
        """Regression: sidecar_merged must be 0 when sidecar file is absent."""
        self._write_ledger([{"tokens": 100} for _ in range(20)])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res.get("sidecar_merged", 0), 0)

    def test_calibration_sample_tracks_drift(self) -> None:
        out = record_calibration_sample(self.root, estimated=100, observed=110, source="unit")
        self.assertTrue(out.exists())
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["samples"]), 1)
        self.assertAlmostEqual(doc["latest_drift_pct"], (10 / 110) * 100, places=2)
        record_calibration_sample(self.root, estimated=200, observed=180, source="unit")
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["samples"]), 2)
        self.assertIn("rolling_avg_drift_pct_last10", doc)


class LedgerBookmarkAndTearingTests(unittest.TestCase):
    """DEF-200-275 第四輪根因 A／A-2 回歸鎖。

    根因 A（本場直接重現於舊 pre hook）：`_read_modify_write` 重寫整份 doc 時只保留
    `{date, cumulative_tokens, entries}`，丟掉 `conversation_overhead.last_merge_entry_index`
    ⇒ `merge_conversation_overhead_into_ledger` 每次都從 0 起算、把全部 entries 再合併一次
    ⇒ 每次工具呼叫 +(len/2)*300、單調遞增（O(n²)）；活帳本實測 conv-overhead 佔 92%、
    單筆 30000→30300→30600。任一測試轉紅＝這條灌水路徑又被打開。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.date = _dt.date.today().isoformat()
        self.path = self.root / f"CONTEXT-LEDGER-{self.date}.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed(self, n: int, *, with_bookmark: object = None, with_conv_entry: bool = False) -> None:
        entries = [{"tokens": 100, "phase": "pre" if i % 2 == 0 else "post"} for i in range(n)]
        if with_conv_entry:
            # 已合併過一次的痕跡（conv-overhead 列），但書籤不見了＝根因 A 的形狀
            entries.append({"tokens": 300, "phase": "conv-overhead", "tool": "ConversationLedger"})
        doc = {
            "date": self.date,
            "cumulative_tokens": sum(int(e["tokens"]) for e in entries),
            "entries": entries,
        }
        if with_bookmark is not None:
            doc["conversation_overhead"] = {"last_merge_entry_index": with_bookmark}
        self.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def _doc(self) -> dict:
        return yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def test_append_ledger_entry_preserves_conversation_overhead_bookmark(self) -> None:
        """【根因 A，先紅再綠】merge 後書籤=22；append 一筆後書籤必須仍是 22（不得被整份改寫吃掉）。"""
        self._seed(22)
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(self._doc()["conversation_overhead"]["last_merge_entry_index"], 22)
        append_ledger_entry(self.root, {"tokens": 1, "phase": "pre", "tool": "Bash"})
        doc = self._doc()
        self.assertIn("conversation_overhead", doc,
                      msg="append 後 conversation_overhead 鍵消失＝根因 A 重現")
        self.assertEqual(doc["conversation_overhead"]["last_merge_entry_index"], 22)

    def test_second_merge_after_append_does_not_remerge(self) -> None:
        """【根因 A】同序列後第二次 merge 不得再合併（舊碼 +3600）。

        QA-05 註明：本案是**端到端／縱深防禦鎖**，不是單點鑑別鎖——只注入「舊 _read_modify_write」
        會被 rebaseline 接住、只注入「關 rebaseline」會被保留書籤接住，兩層**同時**失守才轉紅
        （QA 第 1 輪實測：單注入 A→綠、單注入 B→綠、複合 A2→紅）。單點鑑別由前一案與
        `test_missing_bookmark_rebaselines_without_merging` 各自負責。"""
        self._seed(22)
        merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        append_ledger_entry(self.root, {"tokens": 1, "phase": "pre", "tool": "Bash"})
        res2 = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res2["merged"], msg=f"書籤遺失後立即再合併：{res2}")
        self.assertEqual(res2["added_tokens"], 0)

    def test_negative_bookmark_is_treated_as_missing(self) -> None:
        """SD-05：負整數書籤 ⇒ 視同缺失 rebaseline（`len - (-k)` 會多算 k 筆再灌水），本 tick 不合併。"""
        self._seed(22, with_bookmark=-4)
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"], msg=res)
        self.assertTrue(res.get("rebaselined"), msg=res)
        self.assertEqual(self._doc()["conversation_overhead"]["last_merge_entry_index"], 22)

    def test_missing_bookmark_rebaselines_without_merging(self) -> None:
        """【C7 防呆】帳本已有 conv-overhead 列卻無書籤（＝書籤遺失）⇒ 以 len(entries) 為新起點、
        本 tick 不合併（不得從 0 起算灌水）。全新帳本（無 conv-overhead 列）不在此列，見對照組。"""
        self._seed(22, with_conv_entry=True)  # 23 entries、無 conversation_overhead 鍵
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"], msg=f"書籤遺失後從 0 起算再合併：{res}")
        self.assertEqual(res["added_tokens"], 0)
        doc = self._doc()
        self.assertEqual(doc["conversation_overhead"]["last_merge_entry_index"], 23)
        self.assertEqual(doc["cumulative_tokens"], 2500)
        # 非整數書籤同樣 rebaseline（不論有無 conv-overhead 列）
        self._seed(22, with_bookmark="garbage")
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])
        self.assertEqual(self._doc()["conversation_overhead"]["last_merge_entry_index"], 22)

    def test_fresh_ledger_without_bookmark_still_merges_from_zero(self) -> None:
        """對照組（既有 12 支的前提）：全新帳本沒有書籤也沒有 conv-overhead 列 ⇒ 從 0 起算正常合併。"""
        self._seed(20)
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        self.assertEqual(self._doc()["conversation_overhead"]["last_merge_entry_index"], 20)

    def test_bookmark_zero_on_fresh_ledger_still_merges_normally(self) -> None:
        """對照組：書籤存在且為 0（新帳本）時，既有「每 10 次工具呼叫合併」語意不變。"""
        self._seed(20, with_bookmark=0)
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)

    def test_corrupt_ledger_is_rotated_not_raised(self) -> None:
        """【A-2】本場活帳本損毀形態（半截 `t: null` 行）⇒ append 不 raise、rotate 成 .corrupt-*.yaml、新檔可解析。"""
        self.path.write_text(
            "date: '2026-09-10'\ncumulative_tokens: 5\nentries:\n- ts: 1\n  tokens: 5\n  t: null\n"
            "  - phase: [unclosed\n",
            encoding="utf-8",
        )
        with self.assertRaises(yaml.YAMLError):
            yaml.safe_load(self.path.read_text(encoding="utf-8"))
        cumulative = append_ledger_entry(self.root, {"tokens": 7, "phase": "post", "tool": "Read"})
        self.assertEqual(cumulative, 7)
        rotated = list(self.root.glob(f"CONTEXT-LEDGER-{self.date}.corrupt-*.yaml"))
        self.assertEqual(len(rotated), 1, msg=f"損毀帳本應被改名保留：{list(self.root.iterdir())}")
        doc = self._doc()
        self.assertEqual(doc["cumulative_tokens"], 7)
        self.assertEqual(len(doc["entries"]), 1)

    @staticmethod
    def _deny_read(target: Path):
        """讓 `target` 的文字讀取拋 PermissionError、其餘 Path.open 直通。
        WHY 不用 chmod 000：root（CI 容器）讀得到 000 檔、Windows 的 chmod 對讀取權零作用（鐵律三）——
        兩個平台都會把這案變成假綠；patch 是唯一平台中性的注入點。"""
        orig = Path.open

        def _open(self, mode="r", *args, **kwargs):
            if self == target and "r" in mode and "+" not in mode:
                raise PermissionError(13, "Permission denied (simulated)", str(self))
            return orig(self, mode, *args, **kwargs)
        return patch.object(Path, "open", _open)

    def test_unreadable_ledger_is_not_overwritten_by_writers(self) -> None:
        """【G4／SD-R2-03，本輪 delta 引入】`_load_ledger_doc` 讀檔 OSError 若回 `{}`，寫入者會拿空 doc
        `_atomic_write_yaml` 整本覆寫（歷史／書籤全滅、還回報成功）。讀不到 ≠ 空帳本：該次只是不寫、不 raise 到 hook。"""
        self._seed(6, with_bookmark=6)
        before = self.path.read_bytes()
        with self._deny_read(self.path):
            self.assertEqual(append_ledger_entry(self.root, {"tokens": 7, "phase": "post"}), 0)
            res = merge_conversation_overhead_into_ledger(self.root, merge_every=1)
        self.assertFalse(res["merged"])
        self.assertIn("io_error", res, msg=res)
        self.assertEqual(self.path.read_bytes(), before, "讀不到時磁碟帳本位元組不得改變")
        self.assertFalse(list(self.root.glob("*.corrupt-*")), "讀不到不是損毀，不得 rotate")

    def test_entry_carries_session_and_observed_fields(self) -> None:
        append_ledger_entry(self.root, {
            "tokens": 3, "phase": "pre", "tool": "Bash", "session_id": "sess-1",
            "observed_used": 97184, "window": 1000000, "window_source": "查表值（…）",
        })
        entry = self._doc()["entries"][-1]
        self.assertEqual(entry["session_id"], "sess-1")
        self.assertEqual(entry["observed_used"], 97184)
        self.assertEqual(entry["window"], 1000000)
        self.assertIn("查表值", entry["window_source"])

    def test_concurrent_writers_do_not_tear(self) -> None:
        """【A-2／D31 windows-compat-ci #220／#221 回歸鎖】兩個子行程各 100 次交錯 append／merge。
        不變量＝**主檔＋sidecar 合計零遺失**（真實 entries 總數必為 200），而不是「主檔 entries 恰好
        200」——D31-1／D31-2 的降級路徑會讓瞬時 `LedgerReplaceDenied` 折進 `.append` sidecar，這是
        設計內的正確行為，不是遺失。子行程結束後先呼叫一次 `merge_conversation_overhead_into_ledger`
        把殘留的 sidecar 折回主檔，再斷言 real==200、無殘留 `.append*`／`.part.*`／`.corrupt-*`。"""
        import subprocess
        import sys as _sys

        script = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            "from pathlib import Path;"
            "from tools.fsm_runtime.conversation_ledger import append_ledger_entry, merge_conversation_overhead_into_ledger as m;"
            "d = Path(sys.argv[2]);"
            "[ (append_ledger_entry(d, {'tokens': 1, 'phase': sys.argv[3], 'tool': 'T'}), m(d)) for _ in range(100) ]"
        )
        sdd_root = str(Path(__file__).resolve().parents[3])
        procs = [
            subprocess.Popen([_sys.executable, "-c", script, sdd_root, str(self.root), phase])
            for phase in ("pre", "post")
        ]
        for proc in procs:
            self.assertEqual(proc.wait(timeout=120), 0)
        # 折回任何殘留 sidecar（正常路徑下應該沒有；D31 降級路徑下可能有），讓「合計零遺失」
        # 這個不變量可以只看主檔就驗證完。
        merge_conversation_overhead_into_ledger(self.root)
        doc = self._doc()
        entries = doc["entries"]
        real = [e for e in entries if e.get("phase") in ("pre", "post")]
        conv = [e for e in entries if e.get("phase") == "conv-overhead"]
        self.assertEqual(len(real), 200, msg="交錯寫入撕裂／遺失 entries")
        self.assertEqual(doc["cumulative_tokens"], 200 + sum(e["tokens"] for e in conv))
        self.assertFalse(list(self.root.glob("*.part.*")), msg="pid 專屬暫存檔不得殘留")
        self.assertFalse(list(self.root.glob("*.append*")), msg="sidecar 應已被折回主檔")
        self.assertFalse(list(self.root.glob("*.corrupt-*")), msg="有鎖保護下不應出現損毀 rotate")


class LedgerReplaceRetryTests(unittest.TestCase):
    """D31-5(ii)：windows-compat-ci #220／#221 回歸鎖——`os.replace` 短暫被拒絕存取時的重試／降級
    路徑。`_merge_sidecar_if_present` 本身（folding／去重／delayed-delete）的測試見
    `LedgerSidecarFoldingTests`（D31b-2 起認領改名已被複審 REJECT 並移除，見該類別 docstring）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.date = _dt.date.today().isoformat()
        self.path = self.root / f"CONTEXT-LEDGER-{self.date}.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @staticmethod
    def _always_deny_replace(_src, _dst):
        raise PermissionError(5, "Access is denied (simulated)")

    def _flaky_replace(self, deny_count: int):
        real_replace = os.replace
        calls = {"n": 0}

        def _replace(src, dst):
            if calls["n"] < deny_count:
                calls["n"] += 1
                raise PermissionError(5, "Access is denied (simulated)")
            return real_replace(src, dst)

        return _replace, calls

    def test_atomic_write_retries_transient_permission_denied(self) -> None:
        """先紅（無重試時第一次 PermissionError 就會逸出）後綠：瞬時拒絕 2 次後第 3 次成功。"""
        flaky, calls = self._flaky_replace(deny_count=2)
        with patch.object(conversation_ledger.os, "replace", side_effect=flaky):
            conversation_ledger._atomic_write_yaml(
                self.path, {"date": self.date, "cumulative_tokens": 0, "entries": []},
            )
        self.assertEqual(calls["n"], 2, "應在重試預算內於第 3 次成功，不多不少")
        self.assertTrue(self.path.exists())
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.assertEqual(doc["cumulative_tokens"], 0)

    def test_atomic_write_raises_ledger_replace_denied_when_exhausted(self) -> None:
        """永遠拋 PermissionError ⇒ 重試耗盡後拋具名 LedgerReplaceDenied（不是裸 PermissionError）。"""
        with patch.object(conversation_ledger.os, "replace", side_effect=self._always_deny_replace), \
             patch.object(conversation_ledger.time, "sleep", return_value=None):
            with self.assertRaises(LedgerReplaceDenied):
                conversation_ledger._atomic_write_yaml(
                    self.path, {"date": self.date, "cumulative_tokens": 0, "entries": []},
                )
        self.assertFalse(self.path.exists(), "永遠失敗時主檔不得被建立")
        self.assertFalse(list(self.root.glob("*.part.*")), "pid 專屬暫存檔須在 finally 被清掉")

    def test_append_ledger_entry_degrades_to_sidecar_on_replace_denied(self) -> None:
        """【D31-2】`LedgerReplaceDenied` ⇒ 主檔位元組不變＋entry 折進 sidecar（不是靜默丟成 0）。

        D31b-1 起 `_write_sidecar` 本身也走 `_replace_with_retry`（每筆一檔、寫成即不可變），故本測試
        只鎖定**主檔**檔名拒絕存取——sidecar 用全新的 pid+時間戳專屬檔名，現實中不會撞上同一個
        「另一行程持著 path 讀」的 WinError 5/32（見鐵律三「Windows 檔案鎖」列）；全域拒絕會製造一個
        不存在的複合失效情境（主檔和全新 sidecar 檔同時被拒），偏離本測試要驗的降級路徑。"""
        date = self.date
        doc = {"date": date, "cumulative_tokens": 5, "entries": [{"tokens": 5, "phase": "pre"}]}
        self.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        before = self.path.read_bytes()
        real_replace = os.replace

        def _deny_main_only(src, dst):
            if Path(dst) == self.path:
                raise PermissionError(5, "Access is denied (simulated)")
            return real_replace(src, dst)

        with patch.object(conversation_ledger.os, "replace", side_effect=_deny_main_only), \
             patch.object(conversation_ledger.time, "sleep", return_value=None):
            cumulative = append_ledger_entry(self.root, {"tokens": 9, "phase": "post", "tool": "Bash"})
        self.assertEqual(self.path.read_bytes(), before, "主檔位元組不得改變")
        self.assertEqual(cumulative, 14, "回傳值＝主檔既有 cumulative(5) + 本筆 tokens(9)")
        sidecar_files = list(self.root.glob(f"{self.path.name}.append.*"))
        self.assertEqual(len(sidecar_files), 1, "entry 必須折進 sidecar，不得靜默丟棄")
        loaded = list(yaml.load_all(sidecar_files[0].read_text(encoding="utf-8"), Loader=yaml.SafeLoader))
        flat = [item for chunk in loaded for item in (chunk if isinstance(chunk, list) else [chunk])]
        self.assertEqual(len(flat), 1)
        self.assertEqual(flat[0]["tokens"], 9)

    def test_unreadable_ledger_still_returns_zero_without_sidecar(self) -> None:
        """G4 語意不得被 D31-2 改動：讀不到（非 replace 被拒）⇒ 回 0，且不建 sidecar。"""
        doc = {"date": self.date, "cumulative_tokens": 6,
               "entries": [{"tokens": 6, "phase": "pre"}],
               "conversation_overhead": {"last_merge_entry_index": 6}}
        self.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

        # `_load_ledger_doc` 對讀不到（OSError）的既有契約是原樣拋出（G4，見該函式 docstring）；
        # 直接 patch 它，把「讀不到」與本測試組的「replace 被拒」情境隔開，避免用兩種注入手法
        # 互相污染判準。
        with patch.object(conversation_ledger, "_load_ledger_doc", side_effect=PermissionError(13, "denied")):
            result = append_ledger_entry(self.root, {"tokens": 7, "phase": "post"})
        self.assertEqual(result, 0)
        sidecar = self.path.with_suffix(self.path.suffix + ".append")
        self.assertFalse(sidecar.exists(), "G4：讀不到不得建立 sidecar")

    def test_merge_reports_io_error_on_replace_denied_without_raising(self) -> None:
        """merge 公開入口對 LedgerReplaceDenied 的處理與既有 OSError 路徑一致：回報 io_error，不 raise。"""
        self.path.write_text(
            yaml.safe_dump(
                {"date": self.date, "cumulative_tokens": 2000,
                 "entries": [{"tokens": 100, "phase": "pre" if i % 2 == 0 else "post"} for i in range(20)]},
                allow_unicode=True, sort_keys=False,
            ),
            encoding="utf-8",
        )
        with patch.object(conversation_ledger.os, "replace", side_effect=self._always_deny_replace), \
             patch.object(conversation_ledger.time, "sleep", return_value=None):
            res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])
        self.assertIn("io_error", res, msg=res)
        self.assertIn("LedgerReplaceDenied", res["io_error"])

class LedgerSidecarFoldingTests(unittest.TestCase):
    """D31b-2／D31b-5(i)(ii)(iii)：sidecar 改「每筆一檔、寫成即不可變」後的折回語意——取代
    第一棒 D31-3 的認領改名（claim-rename）測試，該手法已被四方複審 REJECT（C3／W-1，見
    `conversation_ledger.py` 模組 docstring D31b 段）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.date = _dt.date.today().isoformat()
        self.path = self.root / f"CONTEXT-LEDGER-{self.date}.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed_primary(self, tokens: int = 5) -> None:
        doc = {"date": self.date, "cumulative_tokens": tokens,
               "entries": [{"tokens": tokens, "phase": "pre"}]}
        self.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def test_merge_sidecar_if_present_returns_files_without_deleting_them(self) -> None:
        """回傳值是「可安全刪除的清單」，不是「已刪除」——刪除時機由呼叫端（`_merge_locked`）決定，
        必須晚於主檔持久化（D31b-2 的核心正確性保證，見該函式 docstring）。"""
        self._seed_primary()
        write_sidecar(self.root, {"tokens": 7, "phase": "post"})
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 1)
        self.assertEqual(len(doc["entries"]), 2)
        self.assertEqual(doc["cumulative_tokens"], 12)
        self.assertEqual(len(to_delete), 1)
        self.assertTrue(to_delete[0].exists(),
                         "回傳的刪除清單此刻必須仍在磁碟上——尚未持久化前不得先刪來源")

    def test_c3_style_race_two_sidecars_both_survive_fold(self) -> None:
        """【C3 情境正式回歸鎖】複審 c3_race_repro.py 的思路：認領改名版本會讓後寫入者的 fd 寫進
        無目錄項的 inode 而遺失；D31b 每筆一檔沒有共用可變檔，第二個 appender 的寫入落在自己專屬
        的檔名，兩筆都必須能被合併進主檔——即使兩次 `write_sidecar` 呼叫穿插在兩輪
        `_merge_sidecar_if_present` 之間。"""
        self._seed_primary()
        write_sidecar(self.root, {"tokens": 3, "phase": "post", "who": "A"})
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged1, to_delete1 = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged1, 1)
        # 模擬「B 在 A 合併期間才寫入」——B 的 sidecar 檔名與 A 的完全不相干，落在 A 已讀完之後
        # 才出現，不受 A 的讀取／持久化影響（結構性不再有共用檔可撞，這正是 C3 的修法）。
        write_sidecar(self.root, {"tokens": 4, "phase": "post", "who": "B"})
        conversation_ledger._atomic_write_yaml(self.path, doc)
        conversation_ledger._delete_sidecar_sources(to_delete1)
        doc2 = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged2, to_delete2 = conversation_ledger._merge_sidecar_if_present(self.path, doc2)
        self.assertEqual(merged2, 1, msg="B 的 sidecar 必須在下一輪被折回，不得遺失")
        conversation_ledger._atomic_write_yaml(self.path, doc2)
        conversation_ledger._delete_sidecar_sources(to_delete2)
        final = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        whos = sorted(e.get("who") for e in final["entries"] if e.get("who"))
        self.assertEqual(whos, ["A", "B"], msg=f"兩筆都必須在主檔：{final}")

    def test_w1_style_crash_after_persist_before_delete_does_not_duplicate(self) -> None:
        """【W-1 情境正式回歸鎖】模擬「主檔已持久化、但刪除來源前行程被砍」：
        `folded_sidecar_ids` 書籤必須擋下下一次 merge 把同一個 sidecar 檔內容重複折算一次。"""
        self._seed_primary()
        write_sidecar(self.root, {"tokens": 7, "phase": "post"})
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 1)
        conversation_ledger._atomic_write_yaml(self.path, doc)
        # 刻意「不」呼叫 `_delete_sidecar_sources`——模擬持久化成功後、刪除前被砍。
        self.assertTrue(to_delete[0].exists(), "來源檔應仍在磁碟上（尚未執行刪除）")
        doc2 = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.assertEqual(len(doc2["entries"]), 2, "主檔已持久化，這一筆已經在裡面")
        merged2, to_delete2 = conversation_ledger._merge_sidecar_if_present(self.path, doc2)
        self.assertEqual(merged2, 0, msg="同一筆不得因來源檔還在就被重複折算")
        self.assertEqual(len(doc2["entries"]), 2, "doc 不得被重複 append")
        self.assertEqual(to_delete2, to_delete, "殘留的來源檔仍應被回報供下次清理")

    def test_orphaned_merging_claim_file_from_first_pass_is_folded(self) -> None:
        """相容性：第一棒 D31 認領改名留下的孤兒 `.append.merging.<pid>` 檔（行程認領後被砍、零
        清理邏輯）視同 sidecar 來源折回——相容一輪後可移除（見 `_iter_sidecar_sources`）。"""
        self._seed_primary()
        orphan = self.path.with_name(f"{self.path.name}.append.merging.54321")
        with orphan.open("w", encoding="utf-8") as f:
            yaml.safe_dump([{"tokens": 2, "phase": "post"}], f, allow_unicode=True, sort_keys=False)
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 1)
        self.assertEqual(to_delete, [orphan])

    def test_legacy_shared_append_file_is_folded(self) -> None:
        """相容性：D31b 之前的共用單檔 `<ledger>.append` 仍能被折回（部署當天可能還有殘留）。"""
        self._seed_primary()
        legacy = conversation_ledger._sidecar_path(self.path)
        with legacy.open("w", encoding="utf-8") as f:
            yaml.safe_dump([{"tokens": 1}, {"tokens": 2}], f, allow_unicode=True, sort_keys=False)
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 2)
        self.assertEqual(to_delete, [legacy])

    def test_corrupt_sidecar_is_skipped_not_deleted(self) -> None:
        """損毀的 sidecar 檔（無法解析）⇒ 跳過、不列入刪除清單，保留現場供事後查驗。"""
        self._seed_primary()
        broken = self.path.with_name(f"{self.path.name}.append.99999.1.0")
        broken.write_text("not: [valid, yaml\n", encoding="utf-8")
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 0)
        self.assertEqual(to_delete, [])
        self.assertTrue(broken.exists(), "損毀檔不得被刪除")


class LedgerSidecarPartRetentionTests(unittest.TestCase):
    """D31c-1（解複審 W-4，總架構師裁決 D31c）：`_write_sidecar` 在 `LedgerReplaceDenied` 時保留
    tmp（此刻是這筆 entry 的唯一合法副本），`_iter_sidecar_sources` 依「來源 pid 已死、或 mtime
    超過 `_SIDECAR_PART_FOLD_AGE_SEC` 秒」判準把它當一般 sidecar 折回；`cleanup_orphan_part_files`
    起不再主動清這一類殘留檔（見 `conversation_ledger.py` 模組 docstring D31c 段）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.date = _dt.date.today().isoformat()
        self.path = self.root / f"CONTEXT-LEDGER-{self.date}.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed_primary(self, tokens: int = 5) -> None:
        doc = {"date": self.date, "cumulative_tokens": tokens,
               "entries": [{"tokens": tokens, "phase": "pre"}]}
        self.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def test_replace_denied_keeps_a_valid_yaml_tmp_not_an_empty_husk(self) -> None:
        """(D31c-4(i))【先紅後綠】永遠拋 `LedgerReplaceDenied` ⇒ `_write_sidecar` 後 tmp 仍在磁碟上，
        內容是合法可解析的 YAML list（W-4 修復前：`finally: tmp.unlink()` 會在這裡把它刪掉，
        整筆 entry 無聲消失、不留殘檔）。"""
        with patch.object(conversation_ledger, "_replace_with_retry",
                           side_effect=LedgerReplaceDenied("simulated")):
            conversation_ledger._write_sidecar(self.path, {"tokens": 11, "phase": "post"})
        part_files = list(self.root.glob(f"{self.path.name}.append.part.*"))
        self.assertEqual(len(part_files), 1, "replace 被拒後 tmp 必須被保留，不得被 finally 清掉")
        loaded = yaml.safe_load(part_files[0].read_text(encoding="utf-8"))
        self.assertEqual(loaded, [{"tokens": 11, "phase": "post"}],
                         "保留的 tmp 必須是這筆 entry 的合法完整副本")

    def test_stale_part_is_folded_and_deleted_after_persist(self) -> None:
        """(D31c-4(ii) 前半) mtime 超過折回門檻 ⇒ 下次 merge 把它當 sidecar 來源折進主檔，
        持久化成功後刪除來源。"""
        self._seed_primary()
        with patch.object(conversation_ledger, "_replace_with_retry",
                           side_effect=LedgerReplaceDenied("simulated")):
            conversation_ledger._write_sidecar(self.path, {"tokens": 22, "phase": "post"})
        part_files = list(self.root.glob(f"{self.path.name}.append.part.*"))
        self.assertEqual(len(part_files), 1)
        old = time.time() - (conversation_ledger._SIDECAR_PART_FOLD_AGE_SEC + 5)
        os.utime(part_files[0], (old, old))
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 1, "夠舊的 .append.part.* 必須被當來源折回")
        self.assertEqual(to_delete, part_files)
        conversation_ledger._atomic_write_yaml(self.path, doc)
        conversation_ledger._delete_sidecar_sources(to_delete)
        self.assertFalse(part_files[0].exists(), "折回並持久化成功後，來源必須被刪除")
        final_doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.assertIn(22, [e.get("tokens") for e in final_doc["entries"]])

    def test_fresh_and_alive_part_is_not_folded_or_deleted(self) -> None:
        """(D31c-4(ii) 後半) mtime 新鮮且來源 pid（本行程自己）仍活著 ⇒ 本輪不折、不刪——
        避免讀到另一行程正在寫入中的半成品。"""
        self._seed_primary()
        with patch.object(conversation_ledger, "_replace_with_retry",
                           side_effect=LedgerReplaceDenied("simulated")):
            conversation_ledger._write_sidecar(self.path, {"tokens": 33, "phase": "post"})
        part_files = list(self.root.glob(f"{self.path.name}.append.part.*"))
        self.assertEqual(len(part_files), 1)
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 0, "新鮮且來源行程仍活著時不得折回")
        self.assertEqual(to_delete, [])
        self.assertTrue(part_files[0].exists(), "未折回的來源不得被刪除")

    def test_cleanup_orphan_part_files_leaves_append_part_alone(self) -> None:
        """(D31c-4(iii) 前半) `cleanup_orphan_part_files` 對 `.append.part.*`（即使夠舊 + pid 已死）
        一律不刪——這一類是 sidecar 的唯一副本，直接刪等於資料遺失，交由折回路徑處理。"""
        dead = LedgerOrphanPartCleanupTests._dead_pid()
        part = self.root / f"{self.path.name}.append.part.{dead}.123456789.0"
        part.write_text(yaml.safe_dump([{"tokens": 1}], allow_unicode=True), encoding="utf-8")
        old = time.time() - 700
        os.utime(part, (old, old))
        removed = cleanup_orphan_part_files(self.root)
        self.assertEqual(removed, 0)
        self.assertTrue(part.exists(), "sidecar 的 .append.part.* 不得被 cleanup_orphan_part_files 刪除")

    def test_cleanup_orphan_part_files_still_removes_dead_yaml_snapshot_part(self) -> None:
        """(D31c-4(iii) 後半) 對照組：主檔整本快照的孤兒 `.yaml.part.<dead pid>` 行為不變——
        它是可再生快照，仍會被清掉（回歸鎖：不得因本輪改動連帶弄壞既有行為）。"""
        dead = LedgerOrphanPartCleanupTests._dead_pid()
        snap = self.root / f"{self.path.name}.part.{dead}"
        snap.write_text("date: '2026-09-12'\n", encoding="utf-8")
        old = time.time() - 700
        os.utime(snap, (old, old))
        removed = cleanup_orphan_part_files(self.root)
        self.assertGreaterEqual(removed, 1)
        self.assertFalse(snap.exists())

    def test_corrupt_append_part_prints_ascii_warning_and_is_not_deleted(self) -> None:
        """YAML 半成品（解析失敗）的 `.append.part.*`：折回時跳過不刪、印一次 ASCII 警告
        （與既有「損毀 sidecar 跳過不刪」案一致，見 `_merge_sidecar_if_present`）。"""
        self._seed_primary()
        broken = self.root / f"{self.path.name}.append.part.999999.1.0"
        broken.write_text("not: [valid, yaml\n", encoding="utf-8")
        old = time.time() - (conversation_ledger._SIDECAR_PART_FOLD_AGE_SEC + 5)
        os.utime(broken, (old, old))
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        import io
        captured = io.StringIO()
        with patch.object(conversation_ledger.sys, "stderr", captured):
            merged, to_delete = conversation_ledger._merge_sidecar_if_present(self.path, doc)
        self.assertEqual(merged, 0)
        self.assertEqual(to_delete, [])
        self.assertTrue(broken.exists(), "損毀的 .append.part.* 不得被刪除")
        warning = captured.getvalue()
        self.assertIn("sidecar file failed to parse", warning)
        warning.encode("ascii")  # 必須是純 ASCII——不得在非 UTF-8 locale 下讓 print 本身 crash


class LedgerLockBudgetTests(unittest.TestCase):
    """D31b-3（解複審 W-2）：post hook 在同一個 `ledger_lock` 臨界區內 append + merge 各一次
    `_replace_with_retry`＋解鎖 `_try_unlink` 重試，合計不得逼近 `sdd_hook_router.py` 的 8s child
    timeout——必須留至少 2s 給 stdin／measure。"""

    def test_worst_case_ledger_budget_leaves_headroom_for_router_timeout(self) -> None:
        budget = conversation_ledger.worst_case_ledger_budget_sec()
        self.assertLessEqual(
            budget, conversation_ledger.HOOK_CHILD_TIMEOUT_SEC - 2.0,
            msg=f"worst_case_ledger_budget_sec()={budget}s 逼近 router {conversation_ledger.HOOK_CHILD_TIMEOUT_SEC}s "
                "child timeout，留給 stdin/measure 的餘裕 <2s",
        )


class LedgerPerformanceTests(unittest.TestCase):
    """DEF-200-275 第五輪 Dev-C：稽核帳本效能修復（現場實測 400KB 帳本單次 append 5s+ 撞 router 8s
    child timeout）。根因＝PyYAML 純 Python `safe_load`/`safe_dump` 對整份 entries 列表的解析/序列化
    成本隨帳本大小線性增長；`append_ledger_entry`／`merge_conversation_overhead_into_ledger` 各自對
    今日帳本做一次完整 read-modify-write，帳本沒有上限 ⇒ 隨一天推進單次呼叫越來越慢。
    修法＝改用 libyaml 綁定的 `CSafeLoader`/`CSafeDumper`（不可用時 fallback 回純 Python，格式與語意
    完全不變，只是換一個更快的實作）。

    D31b-4（總架構師裁決；解複審 C5／W-3）：牆鐘門檻無法可靠鑑別「libyaml 退化」——共用 CI 跑者的
    變異量級與退化的減速量級同一數量級，兩者在 CI 上分不開（複審 c5_perf_check.py 實測：1500 筆
    純 Python 0.6718s vs C 加速 0.1343s，退化後仍可能落在放寬後的門檻內而被牆鐘誤判為通過）；且
    原本靠 `os.environ.get("CI")` 放寬門檻的條件對 macOS CI 不成立——`.github/workflows/
    macos-compat-ci.yml` 對 `runs-on: macos-latest` 也設 `CI=true`（GitHub Actions 平台預設），
    而 docstring 曾宣稱「mac 仍 0.3s」，兩者互斥。修法：
    (a) 改用身分斷言（`_yaml_loader() is yaml.CSafeLoader`）直接檢查退化與否，不看牆鐘；
    (b) `LIMIT_SEC` 不再依賴 `CI` 環境變數，只依平台——Windows 放寬到 1.0s（windows-compat-ci
        #220／#221 實測 0.3027s／0.3084s，僅超出 mac 量出的 0.3s 硬門檻約 1~3%，屬共用跑者變異
        而非效能退化），其餘平台（含 macOS CI）維持原始 0.3s 緊門檻，牆鐘只負責守住「回到第五輪
        修復前的 5s+ 撞 router 8s child timeout」這條粗防線，真正的退化鑑別交給 (a)。"""

    LIMIT_SEC = 1.0 if sys.platform.startswith("win") else 0.3

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.date = _dt.date.today().isoformat()
        self.path = self.root / f"CONTEXT-LEDGER-{self.date}.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed_realistic(self, n: int) -> None:
        """夾具貼近真實帳本 entry 形狀（見 `.claude/hooks/context_ledger_post.py` 的 entry dict）。"""
        entries = []
        for i in range(n):
            entries.append({
                "ts": f"2026-09-11T{(i // 3600) % 24:02d}:{(i // 60) % 60:02d}:{i % 60:02d}+00:00",
                "phase": "post" if i % 2 else "pre",
                "tool": "Bash",
                "target": None,
                "tokens": 25 + (i % 100),
                "session_id": "8d8773f9-efc9-4513-be65-d48ca316d114",
                "observed_used": 709120,
                "window": 967000,
                "window_source": "指定值（環境變數 AUTOSDD_CONTEXT_WINDOW）",
            })
        doc = {
            "date": self.date,
            "cumulative_tokens": sum(e["tokens"] for e in entries),
            "entries": entries,
            "conversation_overhead": {
                "last_merge_entry_index": n,
                "last_merged_at": "2026-09-11T03:12:19+00:00",
                "total_conv_overhead_tokens": 397800,
            },
        }
        self.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def test_libyaml_c_bindings_are_active_when_available(self) -> None:
        """D31b-4(a)：libyaml 可用時必須真的在用（不是退化回純 Python 卻靠放寬後的牆鐘僥倖通過）。
        `hasattr` 為假時不斷言——本環境本來就沒裝 libyaml，不是本模組的缺陷；改印一行提示，讓 (b)
        的牆鐘門檻承擔這種環境下的粗防線（不 skip：測試仍正常通過並留下可見痕跡）。"""
        import yaml as _yaml

        if not hasattr(_yaml, "CSafeLoader"):
            # ASCII-only：本檔含 `if __name__ == "__main__"` 入口點，
            # tools/tests/test_subprocess_encoding_hygiene.py 的 stdio 保護判準會擋非 ASCII print。
            print(
                "[SKIP-ASSERT] no libyaml binding (yaml.CSafeLoader) in this env; "
                "degraded-loader coverage falls back to the wall-clock threshold below, "
                "not a conversation_ledger.py defect.", file=sys.stderr,
            )
            return
        self.assertIs(conversation_ledger._yaml_loader(), _yaml.CSafeLoader,
                      "libyaml 可用卻沒被用上＝C5 指出的純 Python 退化")
        self.assertIs(conversation_ledger._yaml_dumper(), _yaml.CSafeDumper)

    def test_append_ledger_entry_is_fast_at_1500_entry_scale(self) -> None:
        """硬性驗收（DEF-200-275 第五輪 Dev-C 任務書）：1500 筆／約 400KB 同等規模下 append <0.3s。"""
        self._seed_realistic(1500)
        size = self.path.stat().st_size
        self.assertGreater(size, 300_000, msg=f"夾具過小，非同等規模：{size} bytes")
        t0 = time.perf_counter()
        append_ledger_entry(self.root, {
            "ts": "2026-09-11T23:59:59+00:00", "phase": "post", "tool": "Bash",
            "target": None, "tokens": 42, "session_id": "test-sess",
            "observed_used": 700000, "window": 967000, "window_source": "test",
        })
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, self.LIMIT_SEC, msg=f"append_ledger_entry 耗時 {elapsed:.4f}s ≥ {self.LIMIT_SEC}s 上界")

    def test_merge_conversation_overhead_is_fast_at_1500_entry_scale(self) -> None:
        """post hook 在同一把鎖內緊接 append 之後呼叫 merge——兩者合計才是端到端耗時，merge 本身也不得是瓶頸。"""
        self._seed_realistic(1500)
        t0 = time.perf_counter()
        merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, self.LIMIT_SEC, msg=f"merge_conversation_overhead_into_ledger 耗時 {elapsed:.4f}s ≥ {self.LIMIT_SEC}s 上界")


class LedgerOrphanPartCleanupTests(unittest.TestCase):
    """孤兒 `.part.<pid>` 清理（現場證據：router 砍 8s child 留下的半寫暫存檔，7 個 0～530KB 不等，
    今日帳本目錄裡永久殘留）。判準：mtime > 10 分鐘**且** pid 已不存在才清；活著的 pid／太新的檔一律留著
    （避免誤刪正在寫入中的兄弟行程暫存檔）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.date = _dt.date.today().isoformat()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_part(self, pid: int, *, age_sec: float) -> Path:
        p = self.root / f"CONTEXT-LEDGER-{self.date}.yaml.part.{pid}"
        p.write_text("date: '2026-09-11'\n", encoding="utf-8")
        old = time.time() - age_sec
        os.utime(p, (old, old))
        return p

    @staticmethod
    def _dead_pid() -> int:
        """找一個保證不存在的 pid：從 PID_MAX 往下找第一個 os.kill(pid, 0) 拋 ProcessLookupError 的值。"""
        import errno

        for candidate in (2**31 - 1, 999999, 888888, 777777):
            try:
                os.kill(candidate, 0)
            except ProcessLookupError:
                return candidate
            except PermissionError:
                continue
            except OSError as exc:
                if exc.errno == errno.ESRCH:
                    return candidate
        raise unittest.SkipTest("找不到保證不存在的 pid，本機環境無法安全驗證")

    def test_stale_dead_pid_part_is_removed(self) -> None:
        dead = self._dead_pid()
        stale = self._make_part(dead, age_sec=700)  # >10 分鐘
        removed = cleanup_orphan_part_files(self.root)
        self.assertGreaterEqual(removed, 1)
        self.assertFalse(stale.exists(), "逾 10 分鐘且 pid 已死的 .part 檔應被清掉")

    def test_fresh_dead_pid_part_is_kept(self) -> None:
        dead = self._dead_pid()
        fresh = self._make_part(dead, age_sec=5)  # <10 分鐘：可能還在寫，不清
        cleanup_orphan_part_files(self.root)
        self.assertTrue(fresh.exists(), "未滿 10 分鐘的 .part 檔即使 pid 已死也不應被清（可能剛好撞名）")

    def test_stale_alive_pid_part_is_kept(self) -> None:
        alive = os.getpid()
        stale_but_alive = self._make_part(alive, age_sec=700)
        cleanup_orphan_part_files(self.root)
        self.assertTrue(stale_but_alive.exists(), "pid 仍活著的 .part 檔不得被清（可能仍在寫入）")

    def test_append_ledger_entry_triggers_orphan_cleanup(self) -> None:
        """整合面：呼叫公開入口 `append_ledger_entry` 時應順手清掉孤兒檔，不需另外手動呼叫。"""
        dead = self._dead_pid()
        stale = self._make_part(dead, age_sec=700)
        append_ledger_entry(self.root, {"tokens": 1, "phase": "pre", "tool": "Bash"})
        self.assertFalse(stale.exists(), "append_ledger_entry 應在寫入端啟動時清掉孤兒 .part 檔")


if __name__ == "__main__":
    unittest.main()
