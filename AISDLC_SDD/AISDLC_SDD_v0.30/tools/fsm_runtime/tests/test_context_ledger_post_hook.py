# enforces (governance rules): R-9.2, R-9.6
"""Unit tests for `.claude/hooks/context_ledger_post.py`（DEF-200-275 第四輪對稱重塑）.

被守的性質（Rule 9）：SOFT／WARN／AUTO_COMPACT／CRIT 以本 session 逐字稿 API usage 的真實 ratio
判級；CRIT 只出聲不 deny（deny 是 PreToolUse 的事）；量不到零輸出（C3）；跨 session 日帳本零決策權
（C4）；PENDING 於 used 回落自動完成（C5）；帳本損毀不讓 hook crash 且 gating 訊息仍輸出（A-2）。
第二～三輪 MaxContextFloor／MaxContextConfirmed／NaturalClimb 各案意圖搬至 test_context_window.py
與本檔 RealRatioTierTests（對照表見證據檔〈第四輪〉）；DEF-CLDREV-025 MalformedPayloadTests 保留。
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import yaml  # noqa: E402

HOOK_MODULE_PATH = (
    Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "context_ledger_post.py"
)
_POLLUTING_ENVS = ("SDD_MAX_CONTEXT", "AUTOSDD_CONTEXT_WINDOW", "CLAUDE_CODE_AUTO_COMPACT_WINDOW")


def _load_hook_module(tmp_root: Path):
    spec = importlib.util.spec_from_file_location("context_ledger_post_test", str(HOOK_MODULE_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_root
    return mod


def _isolated_env(tmp: Path, extra: dict | None = None):
    env = dict(os.environ)
    for key in _POLLUTING_ENVS:
        env.pop(key, None)
    home = tmp / "home"
    proj = tmp / "proj"
    home.mkdir(exist_ok=True)
    proj.mkdir(exist_ok=True)
    env.update({"SDD_HOOKS_DISABLE": "", "SDD_HOOKS_DRY_RUN": "", "SDD_SUBAGENT_CONTRACT": "0",
                "HOME": str(home), "USERPROFILE": str(home), "CLAUDE_PROJECT_DIR": str(proj)})
    if extra:
        env.update(extra)
    return patch.dict(os.environ, env, clear=True)


def _write_transcript(tmp: Path, used: int | None, *, model: str = "claude-fable-5-1",
                      peak: int | None = None, name: str = "session-post.jsonl") -> str:
    def rec(m: str, n: int) -> str:
        return json.dumps({"type": "assistant", "message": {
            "model": m, "usage": {"input_tokens": n, "cache_creation_input_tokens": 0,
                                  "cache_read_input_tokens": 0, "output_tokens": 5}}})
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
    if peak is not None:
        lines.append(rec(model, peak))
    if used is not None:
        lines.append(rec(model, used))
    p = tmp / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


class _MainRunner:
    def __init__(self, mod):
        self.mod = mod

    def run(self, payload) -> dict:
        buf_out = StringIO()

        class _FakeStdin(StringIO):
            def isatty(self) -> bool:
                return False

        fake_stdin = _FakeStdin(json.dumps(payload))
        with patch.object(sys, "stdin", fake_stdin), patch.object(sys, "stdout", buf_out):
            rc = self.mod.main()
        assert rc == 0
        raw = buf_out.getvalue().strip()
        return json.loads(raw) if raw else {}


class _IsolatedBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        import tools.fsm_runtime.snapshot as snap_mod
        import tools.fsm_runtime.state_loader as sl_mod

        state = load_state("post-hook-proj", path=self.root / "FSM-STATE-post.yaml")
        state.current = "SPEC_DRAFTING"
        self._rt = FSMRuntime(state)
        self._patches = [
            patch.object(fsm_rt_mod.FSMRuntime, "bootstrap",
                         classmethod(lambda cls, project=None: self._rt)),
            patch.object(snap_mod, "SNAPSHOT_DIR", self.root / "abort"),
            patch.object(sl_mod, "REPO_ROOT", self.root / "repo"),
        ]
        for p in self._patches:
            p.start()
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _run(self, used: int | None, **kw) -> dict:
        payload = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"},
                   "tool_response": "x" * 4000, "session_id": "sess-post"}
        if used is not None or kw:
            payload["transcript_path"] = _write_transcript(self.root, used, **kw)
        return self.runner.run(payload).get("hookSpecificOutput", {})

    def _ledger(self) -> dict:
        path = self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))


class RealRatioTierTests(_IsolatedBase):
    def test_soft_warn_crit_messages_follow_real_ratio(self) -> None:
        for used, marker in ((700_000, "[SDD-CTX] context ratio 70%"),
                             (860_000, "[SDD-CTX][WARN]"),
                             (950_000, "[SDD-CTX][CRIT]")):
            out = self._run(used)
            self.assertIn(marker, out.get("additionalContext", ""), msg=f"used={used}: {out}")
            self.assertNotIn("permissionDecision", out)
            self.assertIn("來源=", out.get("additionalContext", ""))
        # CRIT 只出聲：FSM 狀態不變、不寫 ESCALATION
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0)

    def test_confirmed_900000_triggers_real_auto_compact(self) -> None:
        out = self._run(900_000)
        self.assertIn("[SDD-CTX][AUTO-COMPACT]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        self.assertEqual(self._rt.state.root["auto_compact_state"]["trigger_details"]["session_id"], "sess-post")
        out = self._run(910_000)
        self.assertIn("已處於 AUTO_COMPACT_PENDING", out.get("additionalContext", ""))

    def test_below_soft_is_silent(self) -> None:
        out = self._run(430_428)
        self.assertNotIn("additionalContext", out)

    def test_per_stage_cap_exceeded_at_900000_reports_session_level_cap(self) -> None:
        """D13（DEF-200-275 第五輪）：per-stage cap 超限改為 session 級 `[CAP]` 通知（PostToolUse
        只出聲，deny 是 PreToolUse 的事），**不再**寫專案級 ESCALATION——改名自
        test_per_stage_cap_exceeded_at_900000_reports_project_escalation。
        直接把 count 設到上限（complete_auto_compact(observed_effective) 會歸零，不能用它逼）。"""
        self._rt.state.root["auto_compact_state"] = {"stage_key": "initial", "count_per_stage": 3,
                                                     "max_per_stage": 3}
        out = self._run(900_000)
        ctx = out.get("additionalContext", "")
        self.assertIn("[SDD-CTX][AUTO-COMPACT][CAP]", ctx, msg=out)
        self.assertNotIn("[ESCALATION]", ctx, msg=out)
        self.assertNotIn("permissionDecision", out)  # post 只出聲
        self.assertNotEqual(self._rt.state.current, "ESCALATION")
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0)
        marker = self._rt.state.root["auto_compact_state"]["cap_exceeded"]
        self.assertEqual(marker["session_id"], "sess-post")

    def test_release_state_noop_is_said_out_loud(self) -> None:
        """ARCH-06／SD-06：FSM=RELEASE 時 trigger 是 no-op，訊息不得宣稱已進 PENDING。"""
        self._rt.state.current = "RELEASE"
        out = self._run(900_000)
        ctx = out.get("additionalContext", "")
        self.assertIn("[SDD-CTX][AUTO-COMPACT][NOOP]", ctx, msg=out)
        self.assertNotIn("FSM → AUTO_COMPACT_PENDING", ctx)
        self.assertEqual(self._rt.state.current, "RELEASE")

    def test_unconfirmed_floor_only_warns_at_180000(self) -> None:
        """第二輪 NaturalClimb 意圖：未知 model、180,000/200,000=90% 保守下界 ⇒ 只示警、不進 PENDING。"""
        for used in (170_000, 180_000, 190_000, 199_999):
            out = self._run(used, model="claude-unknown-9")
            self.assertEqual(self._rt.state.current, "SPEC_DRAFTING", msg=f"used={used}: {out}")
        self.assertIn("UNCONFIRMED-DENOM", out.get("additionalContext", ""))
        # 越過 200,000 後下界推論成立（1M）⇒ 250,000 = 25% 靜默放行
        out = self._run(250_000, model="claude-unknown-9")
        self.assertNotIn("additionalContext", out, msg=out)

    def test_explicit_pin_180000_of_200000_still_triggers(self) -> None:
        """第二輪對照組意圖：操作者顯式 SDD_MAX_CONTEXT=200000 ⇒ 180,000 真的進 AUTO_COMPACT_PENDING。"""
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "200000"}, clear=False):
            out = self._run(180_000, model="claude-unknown-9")
        self.assertIn("[SDD-CTX][AUTO-COMPACT]", out.get("additionalContext", ""))
        self.assertIn("SDD_MAX_CONTEXT", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")


class UnmeteredAndLedgerTests(_IsolatedBase):
    def test_unmetered_is_silent_and_still_records_audit(self) -> None:
        """C3：無 transcript ⇒ 空輸出；帳本仍記稽核 entry（observed_used=None）。"""
        out = self._run(None)
        self.assertNotIn("additionalContext", out)
        entry = self._ledger()["entries"][-1]
        self.assertEqual(entry["session_id"], "sess-post")
        self.assertIsNone(entry["observed_used"])
        self.assertEqual(entry["phase"], "post")

    def test_inherited_day_ledger_has_no_say(self) -> None:
        """C4：日帳本 cumulative=5,000,000 但真實 used=50,000 ⇒ 靜默。"""
        date = _dt.date.today().isoformat()
        (self.root / f"CONTEXT-LEDGER-{date}.yaml").write_text(yaml.safe_dump({
            "date": date, "cumulative_tokens": 5_000_000,
            "entries": [{"tokens": 5_000_000, "phase": "post", "tool": "Seed"}],
        }), encoding="utf-8")
        out = self._run(50_000)
        self.assertNotIn("additionalContext", out, msg=out)
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        doc = self._ledger()
        self.assertEqual(doc["entries"][-1]["observed_used"], 50_000)

    def test_pending_exits_when_used_drops(self) -> None:
        """C5：PENDING 而真實 used 回落 <85% ⇒ complete_auto_compact，DONE 訊息。"""
        self._rt.trigger_auto_compact(900_000, 0.9)
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        out = self._run(120_000, peak=900_000)
        self.assertIn("[DONE]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertEqual(self._rt.state.root["auto_compact_state"]["count_per_stage"], 0)

    def test_pending_released_by_another_session_is_labelled(self) -> None:
        """ARCH-03：PENDING 由 session A 觸發、session B（本 hook 的 sess-post）觀測到回落即釋放——
        現行取捨刻意釘住；DONE 訊息與 decision_trace 必須點名兩個 session。"""
        self._rt.trigger_auto_compact(900_000, 0.9, details={"session_id": "sess-A"})
        out = self._run(120_000, peak=900_000)
        ctx = out.get("additionalContext", "")
        self.assertIn("[DONE]", ctx)
        self.assertIn("released_by_session=sess-post", ctx)
        self.assertIn("triggered_by_session=sess-A", ctx)
        self.assertIn("released_by_session=sess-post", self._rt.state.root["decision_trace"][-1]["reason"])
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")

    def test_corrupt_ledger_does_not_crash_hook(self) -> None:
        """A-2：活帳本損毀形態 ⇒ rc=0、gating 訊息仍輸出、檔被 rotate、新帳本可解析。"""
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        path.write_text("date: x\nentries:\n- t: null\n  - [broken\n", encoding="utf-8")
        out = self._run(950_000)
        self.assertIn("[SDD-CTX][CRIT]", out.get("additionalContext", ""))
        rotated = list(self.root.glob(f"CONTEXT-LEDGER-{date}.corrupt-*.yaml"))
        self.assertEqual(len(rotated), 1, msg=list(self.root.iterdir()))
        doc = self._ledger()
        self.assertEqual(len(doc["entries"]), 1)

    def test_bookmark_survives_post_hook_append(self) -> None:
        """根因 A 端到端：post hook 的 append＋merge 不得吃掉 conversation_overhead 書籤。"""
        # merge_every=10 工具呼叫 × entries_per_call=2 ⇒ 20 entries 才 tick 一次；post 單獨每呼叫寫 1 筆。
        for _ in range(21):
            self._run(50_000)
        doc = self._ledger()
        conv = [e for e in doc["entries"] if e.get("phase") == "conv-overhead"]
        self.assertGreaterEqual(len(conv), 1)
        self.assertIn("conversation_overhead", doc)
        bookmark = doc["conversation_overhead"]["last_merge_entry_index"]
        self._run(50_000)
        doc2 = self._ledger()
        self.assertEqual(doc2["conversation_overhead"]["last_merge_entry_index"], bookmark)
        self.assertEqual(len([e for e in doc2["entries"] if e.get("phase") == "conv-overhead"]), len(conv))


class LockTimeoutDegradationTests(_IsolatedBase):
    """DEF-200-275 第四輪 F2（SD-01／ARCH-02）：他人持鎖時 post hook 的降級路徑不得再取第二次鎖。

    WHY（Rule 9）：`ledger_lock` 逾時 5s 後若退回 `append_ledger_entry()`，它會**再**取一次同一把鎖再等
    5s ⇒ 最壞 10s > `sdd_hook_router.py` 對 Pre/Post child 的 8s timeout ⇒ router 砍掉子行程、hook
    fail-open、稽核 entry 全丟（SD-01 實測 10.08s）。降級路徑必須直接寫 sidecar（零取鎖）。
    """

    def test_lock_timeout_degrades_within_router_budget(self) -> None:
        import time
        date = _dt.date.today().isoformat()
        lock = self.root / f"CONTEXT-LEDGER-{date}.yaml.lock"
        # fresh sentinel（mtime＝現在）＝模擬另一支 hook 正持鎖；30s 內不會被當 stale 清掉。
        lock.write_text("pid=0 host=test ts=fresh\n", encoding="utf-8")
        t0 = time.monotonic()
        out = self._run(50_000)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 8.0, msg=f"降級路徑耗時 {elapsed:.2f}s ≥ router child timeout 8s")
        sidecar = self.root / f"CONTEXT-LEDGER-{date}.yaml.append"
        self.assertTrue(sidecar.exists(), msg=f"逾時後 entry 必須落 sidecar：{sorted(p.name for p in self.root.iterdir())}")
        self.assertNotIn("permissionDecision", out)
        self.assertTrue(lock.exists(), msg="降級路徑不得偷拆別人的 fresh sentinel")
        # G3（SD-R2-01）：sidecar 不是終點——鎖釋放後的下一次 merge 必須把降級 entry **持久化到主檔**
        # （修前：折回只發生在記憶體、`delta_calls < merge_every` 早退不寫檔 ⇒ sidecar 被 unlink、entry 永久消失）。
        lock.unlink()
        self._run(50_000)
        self.assertFalse(sidecar.exists(), "sidecar 折回後應被消耗")
        doc = self._ledger()
        self.assertEqual(len(doc["entries"]), 2, msg=f"降級 entry 必須在下一次 merge 後真的在磁碟上：{doc}")

    def test_pending_exit_under_foreign_lock_stays_within_router_budget(self) -> None:
        """G1（QA-R2-01／ARCH-R2-01／SD-R2-02）：post 先 `_record_audit_and_merge` 逾時 5s→sidecar，再
        `complete_auto_compact`→`_reset_today_ledger` 又等 5s ⇒ 修前實測 10.06s > 8s。LEDGER_DIR 與
        REPO_ROOT/build/reports/fsm 指同處（生產環境如此）才量得到這條路徑。"""
        import time
        date = _dt.date.today().isoformat()
        ledger_dir = self.root / "repo" / "build" / "reports" / "fsm"
        self.mod.LEDGER_DIR = ledger_dir
        ledger_dir.mkdir(parents=True, exist_ok=True)
        (ledger_dir / f"CONTEXT-LEDGER-{date}.yaml").write_text(yaml.safe_dump(
            {"date": date, "cumulative_tokens": 10, "entries": [{"tokens": 10, "phase": "post"}]}),
            encoding="utf-8")
        lock = ledger_dir / f"CONTEXT-LEDGER-{date}.yaml.lock"
        lock.write_text("pid=0 host=test ts=fresh\n", encoding="utf-8")
        self._rt.trigger_auto_compact(900_000, 0.9, details={"session_id": "sess-A"})
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        t0 = time.monotonic()
        out = self._run(120_000, peak=900_000)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 8.0, msg=f"PENDING 出口路徑耗時 {elapsed:.2f}s ≥ router child timeout 8s")
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertIn("[DONE]", out.get("additionalContext", ""), msg=out)
        self.assertTrue((ledger_dir / f"CONTEXT-LEDGER-{date}.yaml.append").exists(), "逾時後 entry 必須落 sidecar")
        self.assertTrue(lock.exists(), msg="不得偷拆別人的 fresh sentinel")


class MalformedPayloadTests(_IsolatedBase):
    """DEF-CLDREV-025: symmetric with the pre hook — non-dict payload / tool_input must NOT crash."""

    def test_top_level_list_does_not_crash(self) -> None:
        out = self.runner.run([1, 2, 3])
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_list_tool_input_does_not_crash(self) -> None:
        out = self.runner.run({"tool_name": "Read", "tool_input": [1, 2, 3], "tool_response": "x"})
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_disabled_returns_plain_output(self) -> None:
        with patch.dict(os.environ, {"SDD_HOOKS_DISABLE": "1"}, clear=False):
            out = self._run(950_000)
        self.assertNotIn("additionalContext", out)


if __name__ == "__main__":
    unittest.main()
