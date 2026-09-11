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

from tools.fsm_runtime.conversation_ledger import (  # noqa: E402
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
        doc 並 unlink，隨後 `delta_calls < merge_every` 早退**不寫檔** ⇒ 折回的 entries 磁碟上永久消失
        （預設 merge_every=10 ⇒ 20 個 tick 只有 1 個真的持久化，其餘 19 個折回＝刪除）。F2 讓 post hook
        逾時唯一出口是 sidecar，這條路徑因此承重；docstring 宣稱「下次 merge 折回主檔」必須為真。"""
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        self._write_ledger([{"tokens": 100, "phase": "pre"}])
        for tokens in (11, 22, 33):  # 3 筆共 66 tokens，遠低於 merge 門檻（10 calls × 2 entries）
            write_sidecar(self.root, {"tokens": tokens, "phase": "post"})
        sidecar = path.with_suffix(path.suffix + ".append")
        self.assertTrue(sidecar.exists())
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])
        self.assertEqual(res.get("sidecar_merged"), 3, msg=res)
        self.assertFalse(sidecar.exists(), "sidecar 折回後應被消耗")
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
        """【A-2】兩個子行程各 100 次交錯 append／merge ⇒ 最終檔可解析、entries 數＝寫入總數（含 conv-overhead 列）。"""
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
        doc = self._doc()
        entries = doc["entries"]
        real = [e for e in entries if e.get("phase") in ("pre", "post")]
        conv = [e for e in entries if e.get("phase") == "conv-overhead"]
        self.assertEqual(len(real), 200, msg="交錯寫入撕裂／遺失 entries")
        self.assertEqual(doc["cumulative_tokens"], 200 + sum(e["tokens"] for e in conv))
        self.assertFalse(list(self.root.glob("*.part.*")), msg="pid 專屬暫存檔不得殘留")
        self.assertFalse(list(self.root.glob("*.corrupt-*")), msg="有鎖保護下不應出現損毀 rotate")


class LedgerPerformanceTests(unittest.TestCase):
    """DEF-200-275 第五輪 Dev-C：稽核帳本效能修復（現場實測 400KB 帳本單次 append 5s+ 撞 router 8s
    child timeout）。根因＝PyYAML 純 Python `safe_load`/`safe_dump` 對整份 entries 列表的解析/序列化
    成本隨帳本大小線性增長；`append_ledger_entry`／`merge_conversation_overhead_into_ledger` 各自對
    今日帳本做一次完整 read-modify-write，帳本沒有上限 ⇒ 隨一天推進單次呼叫越來越慢。
    修法＝改用 libyaml 綁定的 `CSafeLoader`/`CSafeDumper`（不可用時 fallback 回純 Python，格式與語意
    完全不變，只是換一個更快的實作）。"""

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
        self.assertLess(elapsed, 0.3, msg=f"append_ledger_entry 耗時 {elapsed:.4f}s ≥ 0.3s 上界")

    def test_merge_conversation_overhead_is_fast_at_1500_entry_scale(self) -> None:
        """post hook 在同一把鎖內緊接 append 之後呼叫 merge——兩者合計才是端到端耗時，merge 本身也不得是瓶頸。"""
        self._seed_realistic(1500)
        t0 = time.perf_counter()
        merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.3, msg=f"merge_conversation_overhead_into_ledger 耗時 {elapsed:.4f}s ≥ 0.3s 上界")


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
