# enforces (governance rules): R-9.2, R-9.6
"""Unit tests for `.claude/hooks/context_ledger_pre.py`（DEF-200-275 第四輪重塑）.

被守的性質（Rule 9）：
- C1／C4：gating 分子＝本 session 逐字稿 API usage；跨 session 的日帳本估算值零決策權。
- C2：分母未確認（保守下界）只出聲永不硬擋；查表阻止對 200K 模型猜大。
- C3：量不到（無 transcript／檔不存在／全 synthetic）⇒ 零 gating。
- C5／D4：AUTO_COMPACT_PENDING 於真實 used 回落 <85% 自動出口（含 resume_state=INIT remap）。
- C6／D3：真實 950,000/1,000,000 仍擋非 compact 工具，但**不寫專案級 ESCALATION**。
- C10：ESCALATION 的 deny reason 帶一行可執行恢復指令。
- C12：每案顯式覆寫 SDD_HOOKS_DISABLE／SDD_HOOKS_DRY_RUN／SDD_MAX_CONTEXT／AUTOSDD_CONTEXT_WINDOW／
  CLAUDE_CODE_AUTO_COMPACT_WINDOW，HOME／USERPROFILE／CLAUDE_PROJECT_DIR 指到 tmp——本機
  `~/.claude/settings.json` 有 `model=claude-fable-5-1[1m]` 與 `AUTOSDD_CONTEXT_WINDOW=967000`，
  正是第三輪留下 2 紅測試的根因。
既有 P1-04（HOOKS_DISABLE 保留 subagent 注入）、P1-05（legacy Read fallback）、DEF-CLDREV-020/025/029
輸入域防護測試原樣保留；第二～三輪的 MaxContextGuard／WideContextWindowInference／
MaxContextConfirmed／NaturalClimb／ZeroTokenEscalation 各案的意圖 1:1 改寫為逐字稿夾具
（對照表見證據檔〈第四輪〉）。
"""
from __future__ import annotations

import datetime as _dt
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
    Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "context_ledger_pre.py"
)
_POLLUTING_ENVS = ("SDD_MAX_CONTEXT", "AUTOSDD_CONTEXT_WINDOW", "CLAUDE_CODE_AUTO_COMPACT_WINDOW")


def _load_hook_module(tmp_root: Path):
    """Import the hook as a module, pointing LEDGER_DIR at tmp_root."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "context_ledger_pre_test", str(HOOK_MODULE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_root
    return mod


def _isolated_env(tmp: Path, extra: dict | None = None):
    """C12：把會污染判定的環境變數與 settings 鏈全部隔離到 tmp。"""
    env = dict(os.environ)
    for key in _POLLUTING_ENVS:
        env.pop(key, None)
    home = tmp / "home"
    proj = tmp / "proj"
    home.mkdir(exist_ok=True)
    proj.mkdir(exist_ok=True)
    env.update({
        "SDD_HOOKS_DISABLE": "",
        "SDD_HOOKS_DRY_RUN": "",
        "SDD_SUBAGENT_CONTRACT": "0",
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CLAUDE_PROJECT_DIR": str(proj),
    })
    if extra:
        env.update(extra)
    return patch.dict(os.environ, env, clear=True)


def _write_transcript(
    tmp: Path, used: int | None, *, model: str = "claude-fable-5-1", peak: int | None = None,
    boundary_after: bool = False, synthetic_only: bool = False, name: str = "session-abc.jsonl",
) -> str:
    def rec(m: str, n: int) -> str:
        return json.dumps({"type": "assistant", "message": {
            "model": m, "usage": {"input_tokens": n, "cache_creation_input_tokens": 0,
                                  "cache_read_input_tokens": 0, "output_tokens": 77}}})
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
    if synthetic_only:
        lines += [rec("<synthetic>", 0), rec("<synthetic>", 0)]
    else:
        if peak is not None:
            lines.append(rec(model, peak))
        if used is not None:
            lines.append(rec(model, used))
    if boundary_after:
        lines.append(json.dumps({"type": "system", "subtype": "compact_boundary"}))
    p = tmp / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


class _MainRunner:
    """Capture stdout from mod.main() given a JSON stdin payload."""

    def __init__(self, mod):
        self.mod = mod

    def run(self, payload) -> dict:
        buf_out = StringIO()

        class _FakeStdin(StringIO):
            def isatty(self) -> bool:  # noqa: D401
                return False

        fake_stdin = _FakeStdin(json.dumps(payload))
        with patch.object(sys, "stdin", fake_stdin), patch.object(sys, "stdout", buf_out):
            rc = self.mod.main()
        assert rc == 0
        raw = buf_out.getvalue().strip()
        if not raw:
            return {}
        return json.loads(raw)


class _IsolatedFsmMixin:
    """隔離 FSM state（tmp）、Snapshot 目錄（tmp）、ledger reset 的 REPO_ROOT（tmp）。"""

    def _isolate_fsm(self, tmp: Path, current: str = "SPEC_DRAFTING"):
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        import tools.fsm_runtime.snapshot as snap_mod
        import tools.fsm_runtime.state_loader as sl_mod

        state = load_state("pre-hook-proj", path=tmp / "FSM-STATE-pre.yaml")
        state.current = current
        self._rt = FSMRuntime(state)
        self._patches = [
            patch.object(fsm_rt_mod.FSMRuntime, "bootstrap",
                         classmethod(lambda cls, project=None: self._rt)),
            patch.object(snap_mod, "SNAPSHOT_DIR", tmp / "abort"),
            patch.object(sl_mod, "REPO_ROOT", tmp / "repo"),
        ]
        for p in self._patches:
            p.start()
        return self._rt

    def _release_fsm(self) -> None:
        for p in getattr(self, "_patches", []):
            p.stop()


class HooksDisableSubagentContractTests(unittest.TestCase):
    """P1-04: HOOKS_DISABLE should keep Subagent Contract injection alive."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_hooks_disable_still_injects_subagent_hint(self) -> None:
        env = {
            "SDD_HOOKS_DISABLE": "1",
            "SDD_SUBAGENT_CONTRACT": "1",  # soft mode
        }
        payload = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "dev-senior", "prompt": "demo"},
        }
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(hook_out.get("hookEventName"), "PreToolUse")
        ctx = hook_out.get("additionalContext", "")
        self.assertIn("SDD-SUBAGENT-CONTRACT", ctx,
                      msg=f"expected subagent hint even with HOOKS_DISABLE=1, got: {ctx!r}")

    def test_hooks_disable_non_task_returns_plain_output(self) -> None:
        env = {"SDD_HOOKS_DISABLE": "1", "SDD_SUBAGENT_CONTRACT": "1"}
        payload = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertNotIn("additionalContext", hook_out)

    def test_hooks_disable_with_contract_off_skips_injection(self) -> None:
        env = {"SDD_HOOKS_DISABLE": "1", "SDD_SUBAGENT_CONTRACT": "0"}
        payload = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "dev-senior"},
        }
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        self.assertNotIn(
            "additionalContext", out.get("hookSpecificOutput", {}),
        )


class LegacyReadFallbackTests(unittest.TestCase):
    """P1-05: legacy Read fallback must add cat -n line overhead."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fallback_read_includes_line_overhead(self) -> None:
        src = self.root / "sample.txt"
        src.write_text("\n".join(f"l{i}" for i in range(10)) + "\n", encoding="utf-8")
        size = src.stat().st_size

        from tools.fsm_runtime import conversation_ledger as cl

        def _boom(*_a, **_k):
            raise RuntimeError("simulated import failure")

        with patch.object(cl, "estimate_tool_tokens", _boom):
            legacy = self.mod._estimate_tokens("Read", {"file_path": str(src)})

        size_only = max(1, size // 4)
        self.assertGreater(
            legacy, size_only,
            msg=f"legacy fallback ignored line overhead: legacy={legacy} size_only={size_only}",
        )
        self.assertLessEqual(legacy, (size + 10 * 8) // 4 + 1)

    def test_fallback_read_missing_file_returns_zero(self) -> None:
        from tools.fsm_runtime import conversation_ledger as cl

        with patch.object(cl, "estimate_tool_tokens", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))):
            self.assertEqual(self.mod._estimate_tokens("Read", {"file_path": str(self.root / "nope.txt")}), 0)
            self.assertEqual(self.mod._estimate_tokens("Read", {"file_path": None}), 0)


class RealUsageGatingTests(_IsolatedFsmMixin, unittest.TestCase):
    """C1／C6／D3：分子＝逐字稿 API usage；≥95% 擋非 compact 工具但不寫專案級 ESCALATION。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def _run(self, used, tool="Write", target="src/app.py", **kw) -> dict:
        transcript = _write_transcript(self.root, used, **kw)
        payload = {"tool_name": tool, "tool_input": {"file_path": target, "content": "x"},
                   "transcript_path": transcript, "session_id": "sess-42"}
        if tool == "Bash":
            payload["tool_input"] = {"command": ""}
        return self.runner.run(payload).get("hookSpecificOutput", {})

    def test_isolation_fixture_hides_real_user_settings(self) -> None:
        """C12 自證：隔離後 settings 鏈與環境變數都看不到本機真值。"""
        from tools.fsm_runtime.context_window import window_evidence
        ev = window_evidence("claude-fable-5-1")
        self.assertIsNone(ev["autosdd_raw"])
        self.assertIsNone(ev["sdd_raw"])
        self.assertIsNone(ev["settings_window"])
        self.assertIsNone(ev["model_hint"])

    def test_real_950000_of_1000000_denies_without_project_escalation(self) -> None:
        out = self._run(950_000)
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("[SDD-CTX][CRIT]", reason)
        self.assertIn("來源=", reason)
        self.assertIn("used=950,000", reason)
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0,
                         msg="95% 不得寫專案級 ESCALATION（根因 C）")
        snap = self._rt.state.root["auto_compact_state"]["snapshot_path"]
        self.assertTrue(Path(snap).exists(), msg=f"Snapshot 應落盤：{snap}")
        self.assertEqual(self._rt.state.root["auto_compact_state"]["trigger_details"]["session_id"], "sess-42")

    def test_real_950000_allows_compact_whitelist_tool(self) -> None:
        out = self._run(950_000, tool="Read", target="docs/x.md")
        self.assertNotIn("permissionDecision", out)
        self.assertIn("[SDD-CTX][CRIT]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")

    def test_real_900000_triggers_auto_compact_pending(self) -> None:
        out = self._run(900_000)
        self.assertNotIn("permissionDecision", out)
        self.assertIn("[SDD-CTX][AUTO-COMPACT]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        details = self._rt.state.root["auto_compact_state"]["trigger_details"]
        self.assertEqual(details["session_id"], "sess-42")
        self.assertEqual(details["window"], 1_000_000)

    def _cap_out(self) -> None:
        # QA-02：直接把 per-stage 計數設到上限（用 complete_auto_compact(observed_effective) 逼會被歸零）。
        # D18（DEF-200-275 第六輪；SD-01）：cap 判定改依逐 session 分桶——`_run()` 固定用
        # session_id="sess-42"，必須同步預置 `count_per_stage_by_session={"sess-42": 3}`，
        # 否則新判準會讀到空桶、誤判成這個 session 才第一次觸發（不會撞 cap）。
        self._rt.state.root["auto_compact_state"] = {
            "stage_key": "initial", "count_per_stage": 3, "max_per_stage": 3,
            "count_per_stage_by_session": {"sess-42": 3},
        }

    def test_per_stage_cap_exceeded_at_950000_denies_session_level(self) -> None:
        """D13（DEF-200-275 第五輪／ARCH-02／SD-02／QA P0）：per-stage cap 超限只拒絕本 session
        的非 compact 工具（pre L373 附近的 `[CRIT][CAP]` 分支），**不再**寫專案級 ESCALATION——
        改名自 test_per_stage_cap_exceeded_at_950000_denies_with_project_escalation。"""
        self._cap_out()
        out = self._run(950_000)
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("[SDD-CTX][CRIT][CAP]", reason)
        self.assertNotIn("[ESCALATION]", reason, msg="不得再有舊式 [CRIT][ESCALATION]/[AUTO-COMPACT][ESCALATION] 標籤")
        self.assertNotIn("resume-from-escalation --to", reason)
        self.assertNotEqual(self._rt.state.current, "ESCALATION",
                            msg="cap 超限不得把 FSM 轉進專案級 ESCALATION（D13）")
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0,
                         msg="cap 超限不得寫 escalation_history（D13）")
        marker = self._rt.state.root["auto_compact_state"]["cap_exceeded"]
        self.assertEqual(marker["session_id"], "sess-42")

    def test_per_stage_cap_exceeded_at_900000_denies_session_level(self) -> None:
        """D13：pre L407 附近 `[AUTO-COMPACT][CAP]` 分支——同一語意，改名自
        test_per_stage_cap_exceeded_at_900000_denies_with_project_escalation。"""
        self._cap_out()
        out = self._run(900_000)
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("[CAP]", reason)
        self.assertNotIn("[ESCALATION]", reason, msg="不得再有舊式 [CRIT][ESCALATION]/[AUTO-COMPACT][ESCALATION] 標籤")
        self.assertNotIn("resume-from-escalation --to", reason)
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0)

    def test_cap_exceeded_does_not_block_a_brand_new_low_usage_session(self) -> None:
        """D13 新增：另一個全新 session（低/零 usage）在 cap 標記落下後照常放行——cap_exceeded 是
        「本 session 自己的 ratio 又衝到門檻」才會查驗的旗標，不是專案級全鎖（不影響其他視窗）。"""
        self._cap_out()
        out = self._run(950_000)  # 先把 cap_exceeded 標記打上（sess-42）
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        self.assertTrue(self._rt.state.root["auto_compact_state"].get("cap_exceeded"))
        # 全新 session、低 usage（5%）：走同一支 hook，但自己的 ratio 遠低於門檻。
        transcript = _write_transcript(self.root, 50_000, name="session-new.jsonl")
        payload = {"tool_name": "Write", "tool_input": {"file_path": "src/other.py", "content": "y"},
                   "transcript_path": transcript, "session_id": "sess-brand-new"}
        out2 = self.runner.run(payload).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out2, msg=out2)

    def test_release_state_noop_does_not_claim_pending(self) -> None:
        """ARCH-06／SD-06：RELEASE 下 90% 的 trigger 是 no-op ⇒ [NOOP]，不得說 FSM → AUTO_COMPACT_PENDING；
        95% 的 deny 句依狀態分句（不講「回落即恢復 resume_state」）。"""
        self._rt.state.current = "RELEASE"
        out = self._run(900_000)
        self.assertNotIn("permissionDecision", out)
        self.assertIn("[SDD-CTX][AUTO-COMPACT][NOOP]", out.get("additionalContext", ""), msg=out)
        self.assertNotIn("FSM → AUTO_COMPACT_PENDING", out.get("additionalContext", ""))
        out = self._run(950_000)
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        self.assertIn("FSM=RELEASE 不進 PENDING", out.get("permissionDecisionReason", ""))
        self.assertEqual(self._rt.state.current, "RELEASE")

    def test_real_860000_only_warns(self) -> None:
        out = self._run(860_000)
        self.assertNotIn("permissionDecision", out)
        self.assertIn("[SDD-CTX][WARN]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")

    def test_real_430000_passes_silently(self) -> None:
        """本 session 實測值（430,428 / 1,000,000 ≈ 43%）：放行、不出聲。"""
        out = self._run(430_428)
        self.assertNotIn("permissionDecision", out)
        self.assertNotIn("additionalContext", out)

    def test_known_haiku_window_blocks_at_192000(self) -> None:
        """方向鎖：查表使 200K 模型在 peak 未過 200K 時就拿到正確分母（不得猜大成 1M）。"""
        out = self._run(192_000, model="claude-haiku-4-5")
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        self.assertIn("model=claude-haiku-4-5", out.get("permissionDecisionReason", ""))

    def test_new_session_ignores_inherited_day_ledger(self) -> None:
        """C4／根因 B 重現：日帳本繼承 2,500,000 估算值，真實 used 只有 50,000 ⇒ 放行。"""
        date = _dt.date.today().isoformat()
        (self.root / f"CONTEXT-LEDGER-{date}.yaml").write_text(yaml.safe_dump({
            "date": date, "cumulative_tokens": 2_500_000,
            "entries": [{"tokens": 2_500_000, "phase": "post", "tool": "OtherSession"}],
        }), encoding="utf-8")
        out = self._run(50_000)
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertNotIn("additionalContext", out)
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        doc = yaml.safe_load((self.root / f"CONTEXT-LEDGER-{date}.yaml").read_text(encoding="utf-8"))
        last = doc["entries"][-1]
        self.assertEqual(last["session_id"], "sess-42")
        self.assertEqual(last["observed_used"], 50_000)
        self.assertEqual(last["window"], 1_000_000)


class UnmeteredAndUnconfirmedTests(_IsolatedFsmMixin, unittest.TestCase):
    """C3：量不到零 gating；C2：保守下界只出聲。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)
        date = _dt.date.today().isoformat()
        (self.root / f"CONTEXT-LEDGER-{date}.yaml").write_text(yaml.safe_dump({
            "date": date, "cumulative_tokens": 5_000_000,
            "entries": [{"tokens": 5_000_000, "phase": "post", "tool": "Seed"}],
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def test_unmetered_session_never_gates(self) -> None:
        cases = {
            "no_transcript": None,
            "missing_file": str(self.root / "nope.jsonl"),
            "all_synthetic": _write_transcript(self.root, None, synthetic_only=True),
            "stale_after_compact": _write_transcript(self.root, 990_000, boundary_after=True, name="s2.jsonl"),
        }
        for name, transcript in cases.items():
            payload = {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"}}
            if transcript is not None:
                payload["transcript_path"] = transcript
            out = self.runner.run(payload).get("hookSpecificOutput", {})
            self.assertNotIn("permissionDecision", out, msg=f"{name}: {out}")
            self.assertNotIn("additionalContext", out, msg=f"{name}: {out}")
            self.assertEqual(self._rt.state.current, "SPEC_DRAFTING", msg=name)

    def test_floor_window_only_warns(self) -> None:
        """未知 model、peak<200K、used=195,000 ⇒ 保守下界 97.5%：只出 UNCONFIRMED-DENOM，不擋、不 trigger。"""
        transcript = _write_transcript(self.root, 195_000, model="claude-unknown-9")
        out = self.runner.run({"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"},
                               "transcript_path": transcript}).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertIn("UNCONFIRMED-DENOM", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0)

    def test_inferred_wide_window_after_peak_passes(self) -> None:
        """peak=250,000 變體：下界推論 1M、may_block=True，195,000 只有 19.5% ⇒ 放行且不出聲。"""
        transcript = _write_transcript(self.root, 195_000, model="claude-unknown-9", peak=250_000)
        out = self.runner.run({"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"},
                               "transcript_path": transcript}).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertNotIn("additionalContext", out, msg=out)


class PinnedWindowTests(_IsolatedFsmMixin, unittest.TestCase):
    """承接 ZeroTokenEscalationTests／explicit-pin 各案意圖：SDD_MAX_CONTEXT=1000 顯式釘住，
    Bash 空 command（估算 0 tokens）仍受真實 used 的 gating。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root, {"SDD_MAX_CONTEXT": "1000"})
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def _run(self, used: int) -> dict:
        transcript = _write_transcript(self.root, used, model="claude-unknown-9")
        return self.runner.run({"tool_name": "Bash", "tool_input": {"command": ""},
                                "transcript_path": transcript}).get("hookSpecificOutput", {})

    def test_pinned_window_1000_with_used_960_denies(self) -> None:
        # Bash 在 AUTO_COMPACT 白名單內（跑 compaction 需要它）⇒ 這裡以 Write 驗 deny、以 Bash 驗 CRIT 訊息。
        out = self._run(960)
        self.assertNotIn("permissionDecision", out)
        self.assertIn("[SDD-CTX][CRIT]", out.get("additionalContext", ""))
        self.assertIn("SDD_MAX_CONTEXT", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        transcript = _write_transcript(self.root, 960, model="claude-unknown-9")
        out = self.runner.run({"tool_name": "Write", "tool_input": {"file_path": "src/a.py", "content": "x"},
                               "transcript_path": transcript}).get("hookSpecificOutput", {})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        self.assertEqual(len(self._rt.state.root.get("escalation_history") or []), 0)

    def test_pinned_920_of_1000_auto_compact(self) -> None:
        out = self._run(920)
        self.assertIn("[SDD-CTX][AUTO-COMPACT]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")

    def test_pinned_300_of_1000_passes(self) -> None:
        out = self._run(300)
        self.assertNotIn("permissionDecision", out)
        self.assertNotIn("additionalContext", out)

    def test_malformed_pin_is_not_pinned(self) -> None:
        """第三輪意圖搬入：壞值（abc/1.5/12k/空/0/-5）不算釘住 ⇒ 未知 model、190,000 只示警。"""
        for bad in ("abc", "1.5", "12k", "", "0", "-5"):
            with patch.dict(os.environ, {"SDD_MAX_CONTEXT": bad}, clear=False):
                transcript = _write_transcript(self.root, 190_000, model="claude-unknown-9")
                out = self.runner.run({"tool_name": "Write", "tool_input": {"file_path": "src/a.py", "content": "x"},
                                       "transcript_path": transcript}).get("hookSpecificOutput", {})
                self.assertNotIn("permissionDecision", out, msg=f"value={bad!r}: {out}")
                self.assertIn("UNCONFIRMED-DENOM", out.get("additionalContext", ""), msg=repr(bad))
                self.assertEqual(self._rt.state.current, "SPEC_DRAFTING", msg=repr(bad))


class AutoCompactPendingExitTests(_IsolatedFsmMixin, unittest.TestCase):
    """C5／D4：PENDING 於真實 used 回落 <85% 自動完成（含 Claude Code 自動 compact）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def _enter_pending(self, resume_state: str, session_id: str | None = None) -> None:
        self._rt.state.current = resume_state
        details = {"session_id": session_id} if session_id else None
        res = self._rt.trigger_auto_compact(900_000, 0.9, details=details)
        self.assertFalse(res.get("escalated"))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")

    def _run(self, used: int, tool: str = "Write", target: str = "src/app.py",
            session_id: str | None = None) -> dict:
        transcript = _write_transcript(self.root, used, peak=900_000)
        payload = {"tool_name": tool, "tool_input": {"file_path": target, "content": "x"},
                  "transcript_path": transcript}
        if session_id is not None:
            payload["session_id"] = session_id
        return self.runner.run(payload).get("hookSpecificOutput", {})

    def test_pending_exits_when_used_drops_below_85pct(self) -> None:
        self._enter_pending("SPEC_DRAFTING")
        out = self._run(120_000)
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertIn("[DONE]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertEqual(self._rt.state.root["auto_compact_state"]["count_per_stage"], 0)
        self.assertEqual(self._rt.state.root["decision_trace"][-1]["trigger"], "auto_compact_complete")

    def test_pending_hysteresis(self) -> None:
        self._enter_pending("SPEC_DRAFTING")
        out = self._run(890_000, tool="Read", target="docs/x.md")
        self.assertNotIn("[DONE]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        out = self._run(840_000, tool="Read", target="docs/x.md")
        self.assertIn("[DONE]", out.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")

    def test_pending_with_illegal_resume_state_remaps_to_spec_drafting(self) -> None:
        self._enter_pending("INIT")
        out = self._run(100_000)
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertIn("remap", self._rt.state.root["decision_trace"][-1]["reason"])
        self.assertIn("remap", out.get("additionalContext", ""))

    def test_pending_non_compact_tool_still_denied_while_high(self) -> None:
        self._enter_pending("SPEC_DRAFTING")
        out = self._run(920_000)
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        self.assertIn("AUTO_COMPACT_PENDING", out.get("permissionDecisionReason", ""))

    def test_pending_deny_reason_has_real_numbers_and_trigger_session(self) -> None:
        """D12（DEF-200-275 第五輪 SA-01）：PENDING 且量得到仍 deny 時，reason 必含
        used=/window=/來源=/session=/觸發時間，以及解除規則一句。

        D19（DEF-200-275 第六輪；SD-02）：這裡驗證的是「PENDING 的 owner 自己再次呼叫、usage
        仍高」這個情境——所以呼叫端必須是同一個 session_id，否則 D19 的 owner-scope 判準會把它當
        非 owner 而放行（那正是 D19 要修的行為，不是這支測試要驗證的行為，兩者不衝突）。"""
        self._enter_pending("SPEC_DRAFTING", session_id="sess-trigger")
        out = self._run(920_000, session_id="sess-trigger")
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("used=920,000", reason)
        self.assertIn("window=", reason)
        self.assertIn("來源=", reason)
        self.assertIn("session=sess-trigger", reason)
        self.assertIn("真實 usage 回落 <85% 後下一次工具呼叫自動恢復 resume_state", reason)


class PendingUnmeteredTests(_IsolatedFsmMixin, unittest.TestCase):
    """D11（C3 補齊；DEF-200-275 第五輪 F2）：AUTO_COMPACT_PENDING 且本次量不到 usage（新 session
    首擊／compact 後尚無新 usage）⇒ 放行一次＋[UNMETERED] notice；不得讓
    `_assert_allowed_under_auto_compact` 白名單擋下這次呼叫——否則就是「新視窗一開就被擋」（F2）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def _enter_pending(self) -> None:
        self._rt.state.current = "SPEC_DRAFTING"
        res = self._rt.trigger_auto_compact(900_000, 0.9, details={"session_id": "sess-trigger"})
        self.assertFalse(res.get("escalated"))
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")

    def _run_unmetered(self, tool: str, tool_input: dict, session_id: str = "sess-new") -> dict:
        # 無 transcript_path ⇒ measure() 回 None（新 session 首擊，逐字稿裡尚無這次 tool_use 的 usage）。
        payload = {"tool_name": tool, "tool_input": tool_input, "session_id": session_id}
        return self.runner.run(payload).get("hookSpecificOutput", {})

    def test_write_passes_once_when_pending_and_unmetered(self) -> None:
        self._enter_pending()
        out = self._run_unmetered("Write", {"file_path": "src/app.py", "content": "x"})
        self.assertNotIn("permissionDecision", out, msg=out)
        ctx = out.get("additionalContext", "")
        self.assertIn("[SDD-CTX][AUTO-COMPACT][UNMETERED]", ctx)
        self.assertIn("session=sess-trigger", ctx)
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING",
                         msg="D11 不改變 PENDING 狀態，只放行這一次呼叫")

    def test_task_passes_once_when_pending_and_unmetered(self) -> None:
        self._enter_pending()
        out = self._run_unmetered("Task", {"subagent_type": "dev-senior", "prompt": "demo"})
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertIn("[SDD-CTX][AUTO-COMPACT][UNMETERED]", out.get("additionalContext", ""))

    def test_second_call_same_session_with_low_usage_completes(self) -> None:
        """同 session 第二次帶 usage<85% ⇒ [DONE]（既有 D4/C5 語意；D11 只補齊第一次量不到那一擊）。"""
        self._enter_pending()
        out1 = self._run_unmetered("Write", {"file_path": "src/app.py", "content": "x"})
        self.assertNotIn("permissionDecision", out1, msg=out1)
        self.assertIn("[UNMETERED]", out1.get("additionalContext", ""))
        transcript = _write_transcript(self.root, 120_000, peak=900_000)
        out2 = self.runner.run({"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"},
                                "transcript_path": transcript, "session_id": "sess-new"}
                               ).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out2, msg=out2)
        self.assertIn("[DONE]", out2.get("additionalContext", ""))
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")

    def test_spec_target_write_denied_when_pending_and_unmetered(self) -> None:
        """複審 R-D11（DEF-200-275 第五輪）：D11 的『量不到 usage 放行一次』只及於非規格檔——
        Write 命中 `docs/01_requirements/`（Rule 9.6 絕對禁令 #3）時，即使量不到 usage 仍須 deny，
        不得被 D11 的 C3 放行短路成後門。原缺陷：D11 分支在 `assert_tool_allowed()` 之前提前
        return，連 spec 前綴保護一起跳過（實測：PENDING＋零 usage＋此 Write ⇒ 放行）。"""
        self._enter_pending()
        out = self._run_unmetered(
            "Write", {"file_path": "docs/01_requirements/PRD-review.md", "content": "x"})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("量不到 usage 放行只及於非規格檔", reason)
        self.assertIn("session=sess-trigger", reason)
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")

    def test_spec_target_edit_also_denied_when_pending_and_unmetered(self) -> None:
        """同上，Edit 工具、`02_architecture/` 前綴同樣受保護（不只 Write／不只 01_requirements）。"""
        self._enter_pending()
        out = self._run_unmetered(
            "Edit", {"file_path": "docs/02_architecture/SRD.md", "old_string": "a", "new_string": "b"})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)

    def test_non_spec_write_still_passes_once_when_pending_and_unmetered(self) -> None:
        """對照組（防止過度收斂）：非規格前綴目標仍照 D11 放行一次，不因新增的 spec 例外連坐。"""
        self._enter_pending()
        out = self._run_unmetered("Write", {"file_path": "src/app.py", "content": "x"})
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertIn("[SDD-CTX][AUTO-COMPACT][UNMETERED]", out.get("additionalContext", ""))

    def test_pending_deny_reason_with_m_none_does_not_raise(self) -> None:
        """複審 R-D11 補防禦：`_pending_deny_reason` 對 `m is None` 不得拋 AttributeError（原本
        `else` 分支直接讀 `m.used`，假設呼叫端保證非 None；補上防呆讓量測面未來變動也不會炸
        hook）。應老實印「量不到」，不得猜數字。"""
        self._enter_pending()
        reason = self.mod._pending_deny_reason(self._rt, None, None, None)
        self.assertIn("量不到", reason)
        self.assertIn("session=sess-trigger", reason)


class PendingExitLockContentionTests(_IsolatedFsmMixin, unittest.TestCase):
    """DEF-200-275 第四輪 G1（QA-R2-01／ARCH-R2-01／SD-R2-02 三方獨立實測 ≈10s）：AUTO_COMPACT_PENDING
    出口路徑在他人持鎖時，pre hook 先 `complete_auto_compact`→`_reset_today_ledger`（取鎖）再 `_record_audit`
    →`append_ledger_entry`（再取同一把鎖）——兩段各等 5s ⇒ 10s > `sdd_hook_router.py` child timeout 8s
    ⇒ router 砍子行程、hook fail-open、稽核 entry 一起丟（F2 同一失效類別在另一條路徑重開）。

    WHY 同目錄：生產環境 hook 的 LEDGER_DIR 與 `_reset_today_ledger` 的 `REPO_ROOT/build/reports/fsm`
    是同一個目錄、同一把鎖；測試必須讓兩者指同處才量得到這條路徑。修法＝reset 只等 1s（帳本零決策權，
    歸零失敗誠實回 `lock_timeout=True`），單支 hook 最壞 5+1=6s < 8s。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)
        # 與 `_reset_today_ledger` 讀的 REPO_ROOT/build/reports/fsm 同一目錄（生產環境如此）
        self.ledger_dir = self.root / "repo" / "build" / "reports" / "fsm"
        self.mod.LEDGER_DIR = self.ledger_dir
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        date = _dt.date.today().isoformat()
        (self.ledger_dir / f"CONTEXT-LEDGER-{date}.yaml").write_text(yaml.safe_dump(
            {"date": date, "cumulative_tokens": 10, "entries": [{"tokens": 10, "phase": "post"}]}),
            encoding="utf-8")
        self.lock = self.ledger_dir / f"CONTEXT-LEDGER-{date}.yaml.lock"
        self.lock.write_text("pid=0 host=test ts=fresh\n", encoding="utf-8")  # fresh sentinel＝他人正持鎖

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def test_pending_exit_under_foreign_lock_stays_within_router_budget(self) -> None:
        import time
        self._rt.trigger_auto_compact(900_000, 0.9, details={"session_id": "sess-A"})
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        transcript = _write_transcript(self.root, 120_000, peak=900_000)
        t0 = time.monotonic()
        out = self.runner.run({"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"},
                               "transcript_path": transcript, "session_id": "sess-42"}
                              ).get("hookSpecificOutput", {})
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 8.0, msg=f"PENDING 出口路徑耗時 {elapsed:.2f}s ≥ router child timeout 8s")
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        self.assertIn("[DONE]", out.get("additionalContext", ""), msg=out)
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertTrue(self.lock.exists(), msg="不得偷拆別人的 fresh sentinel")


class EscalationRecoveryHintTests(_IsolatedFsmMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def test_escalation_deny_reason_contains_recovery_hint(self) -> None:
        self._rt.state.record_escalation("TOKEN_BUDGET_CRITICAL: legacy", details={"session_id": "old-1"})
        transcript = _write_transcript(self.root, 50_000)
        out = self.runner.run({"tool_name": "Read", "tool_input": {"file_path": "docs/x.md"},
                               "transcript_path": transcript}).get("hookSpecificOutput", {})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("resume-from-escalation --to", reason)
        self.assertIn("session=old-1", reason)
        self.assertIn("SDD_HOOKS_DRY_RUN=1", reason)

    def test_dry_run_softens_escalation_deny(self) -> None:
        self._rt.state.record_escalation("x")
        with patch.dict(os.environ, {"SDD_HOOKS_DRY_RUN": "1"}, clear=False):
            out = self.runner.run({"tool_name": "Read", "tool_input": {"file_path": "docs/x.md"}}
                                  ).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out)
        self.assertIn("[SDD-DRY-RUN] would deny", out.get("additionalContext", ""))

    def test_first_strike_no_usage_escalation_deny_has_full_provenance(self) -> None:
        """D17（DEF-200-275 第六輪／DEF-200-283；F-ARCH-01／QA-C1）：全新視窗第一次工具呼叫
        （無 transcript_path ⇒ m=None）撞上『別的 session 因非 auto-compact 原因寫入的
        project-level ESCALATION』（此案比照 R-9.7 human-pending timeout 語意）時，deny 訊息
        仍必須含溯源四欄（來源 session／時間／原因／rule_id）＋一行可複製恢復指令——此前
        `EscalationRecoveryHintTests` 只覆蓋『量得到 usage』的情境（見 D16 docstring 自陳）。"""
        self._rt.state.record_escalation(
            "HUMAN_PENDING 逾時 200h (≥168h)，自動進入 ESCALATION (ACT-023)",
            details={"session_id": "old-session"}, rule_id="R-9.7", source="human_pending_timeout",
        )
        out = self.runner.run({"tool_name": "Read", "tool_input": {"file_path": "docs/x.md"},
                               "session_id": "brand-new-session"}).get("hookSpecificOutput", {})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("溯源：此 ESCALATION 由 session=old-session", reason)
        self.assertIn("rule_id=R-9.7", reason)
        self.assertIn("本 session=brand-new-session", reason)
        self.assertIn("不是觸發者", reason)
        self.assertIn("resume-from-escalation --to", reason)

    def test_same_session_triggering_own_escalation_is_named_trigger(self) -> None:
        """對稱驗證：provenance 的 session_id 與本次呼叫的 session_id 相同時，訊息明說
        『是觸發者』，而非籠統地說『不知道』——D17 的核心承諾是誠實回答『是不是我』，不是
        永遠印一句安全但無資訊量的話。"""
        self._rt.state.record_escalation(
            "gate retry exhausted", details={"session_id": "same-sess"},
            rule_id="R-9.1", source="gate_retry_budget:SCG_VALIDATION",
        )
        out = self.runner.run({"tool_name": "Read", "tool_input": {"file_path": "docs/x.md"},
                               "session_id": "same-sess"}).get("hookSpecificOutput", {})
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("本 session=same-sess（是觸發者）", reason)

    def test_terminated_state_also_gets_recovery_hint_now(self) -> None:
        """D17 point 3（F-ARCH-04）：`_ESCALATION_STATES` 擴到 TOKEN_BUDGET_CRITICAL／TERMINATED
        ——deny 訊息『一律帶真實數字＋恢復指令』（D12/D16）的精神不該因為卡在哪個 blocking 狀態
        而不同；此前只有 ESCALATION／ESCALATION_FINAL 兩態會附恢復指令，TERMINATED 只有光禿禿一句
        `state TERMINATED blocks all tool calls...`。"""
        self._rt.state.current = "TERMINATED"
        out = self.runner.run({"tool_name": "Read", "tool_input": {"file_path": "docs/x.md"}}
                              ).get("hookSpecificOutput", {})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        reason = out.get("permissionDecisionReason", "")
        self.assertIn("resume-from-escalation --to", reason)


class PendingOwnerScopeTests(_IsolatedFsmMixin, unittest.TestCase):
    """D19（DEF-200-275 第六輪；SD-02；DEF-200-279 殘餘路徑之二）：AUTO_COMPACT_PENDING 是專案級
    狀態，但『只准 compact 工具』這個限制、以及『誰能釋放它』這兩件事都改成只看 owner——否則任何
    全新視窗第一次工具呼叫，只要專案裡*任何* session 曾進過 PENDING，就會被卡死（F-ARCH-01／
    QA-C1 指出的殘餘路徑）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def _run(self, transcript: str, session_id: str, tool: str = "Write",
            target: str = "src/app.py") -> dict:
        payload = {"tool_name": tool, "tool_input": {"file_path": target, "content": "x"},
                  "transcript_path": transcript, "session_id": session_id}
        return self.runner.run(payload).get("hookSpecificOutput", {})

    def _enter_pending_as(self, owner_transcript: str, owner_sid: str) -> None:
        """讓 owner session 走真正的 hook 路徑觸發 PENDING，讓 `pending_owner` 被正確記錄
        （直接呼叫 `rt.trigger_auto_compact()` 也能進 PENDING，但那樣繞過了 hook 的
        `_details()`／`transcript_path` 透傳，測不到 D19 真正要驗證的路徑）。"""
        out = self._run(owner_transcript, owner_sid)
        self.assertNotIn("permissionDecision", out, msg=out)  # 90% 觸發只出聲，不 deny
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")
        owner = self._rt.state.root["auto_compact_state"].get("pending_owner")
        self.assertIsInstance(owner, dict, msg="trigger_auto_compact 必須落一份 pending_owner")
        self.assertEqual(owner["session_id"], owner_sid)
        self.assertEqual(owner["transcript_path"], owner_transcript)

    def test_non_owner_low_usage_passes_without_releasing_project_pending(self) -> None:
        """非 owner、自己量得到 ratio 遠低於門檻 ⇒ 放行，但不釋放專案 PENDING（決策 D19 item 2；
        owner 仍新鮮，不符陳舊條件，item 3 的例外不適用）。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner.jsonl")
        self._enter_pending_as(owner_transcript, "owner-sess")

        other_transcript = _write_transcript(self.root, 5_000, name="brand-new.jsonl")
        out = self._run(other_transcript, "brand-new-session", target="src/other.py")
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertEqual(
            self._rt.state.current, "AUTO_COMPACT_PENDING",
            msg="非 owner 的低用量不得順便釋放別人觸發的 PENDING（D19 item 2）",
        )

    def test_owner_itself_is_still_restricted_to_compact_tools(self) -> None:
        """owner 自己再次呼叫、usage 仍高 ⇒ 只准 compact 工具（D19 沒有弱化既有 D12 行為，
        只是把它的適用範圍從『整個專案』收斂到『owner 自己』）。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner2.jsonl")
        self._enter_pending_as(owner_transcript, "owner-sess-2")
        out = self._run(owner_transcript, "owner-sess-2", target="src/other.py")
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)

    def test_non_owner_spec_write_is_still_blocked_by_rule_9_6(self) -> None:
        """D19 只鬆綁『只准 compact 工具』這條，不鬆綁 Rule 9.6 絕對禁令——非 owner 也不得趁機
        寫規格文件（決策 D19 item 2 明文：『Rule 9.6 規格檔仍擋』）。

        訊息文字沿用既有的 `_pending_deny_reason()` 通用 PENDING 訊息（不是
        `_is_blocked_spec_write` 在 core 層拋出的那句話）——`context_ledger_pre.py` 的
        `except TransitionError` 只要 `rt.state.current == "AUTO_COMPACT_PENDING"` 就一律改印
        通用訊息，這是既有行為（owner 自己寫規格檔命中的也是同一句，非本輪改動），本測試只斷言
        deny 這個結果本身，不糾結訊息文字出處。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner3.jsonl")
        self._enter_pending_as(owner_transcript, "owner-sess-3")
        other_transcript = _write_transcript(self.root, 5_000, name="brand-new2.jsonl")
        out = self._run(other_transcript, "brand-new-session-2",
                        target="docs/01_requirements/PRD.md")
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)
        self.assertIn("AUTO_COMPACT_PENDING", out.get("permissionDecisionReason", ""))

    def test_fresh_owner_blocks_non_owner_release_even_when_non_owner_usage_has_dropped(self) -> None:
        """owner 仍新鮮（transcript 剛寫入、遠在陳舊窗口內）時，非 owner 即使自己量到真實回落，
        也不得釋放專案 PENDING（決策 D19 item 3；被否決的替代案是維持 ARCH-03『任何 session 都可
        釋放』不分陳舊與否）。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner-fresh.jsonl")
        self._enter_pending_as(owner_transcript, "owner-fresh-sess")
        other_transcript = _write_transcript(self.root, 50_000, name="other-low.jsonl")
        out = self._run(other_transcript, "other-session", tool="Read", target="docs/x.md")
        self.assertNotIn("[DONE]", out.get("additionalContext", ""), msg=out)
        self.assertEqual(self._rt.state.current, "AUTO_COMPACT_PENDING")

    def test_stale_owner_missing_transcript_lets_a_different_session_release(self) -> None:
        """owner 的逐字稿已從磁碟消失（模擬那個視窗早就關掉、暫存被清）⇒ 陳舊；非 owner 這次量到
        真實回落時可以釋放，取代 ARCH-03 的無條件釋放，但不讓 PENDING 因 owner 消失而永遠卡死
        （決策 D19 item 3）。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner-to-vanish.jsonl")
        self._enter_pending_as(owner_transcript, "owner-vanish-sess")
        Path(owner_transcript).unlink()

        other_transcript = _write_transcript(self.root, 50_000, name="rescuer.jsonl")
        out = self._run(other_transcript, "rescuer-session", tool="Read", target="docs/x.md")
        self.assertIn("[DONE]", out.get("additionalContext", ""), msg=out)
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")

    def test_stale_owner_by_old_mtime_lets_a_different_session_release(self) -> None:
        """owner 的逐字稿檔案還在，但 mtime 已超過 `SDD_PENDING_OWNER_STALE_SECONDS`（預設 1800s）
        ⇒ 同樣判定陳舊（決策 D19 item 3 的兩個陳舊判準之一：mtime，另一是檔案不存在，見上一案）。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner-old-mtime.jsonl")
        self._enter_pending_as(owner_transcript, "owner-old-sess")
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=2)).timestamp()
        os.utime(owner_transcript, (old_ts, old_ts))

        other_transcript = _write_transcript(self.root, 50_000, name="rescuer2.jsonl")
        out = self._run(other_transcript, "rescuer-session-2", tool="Read", target="docs/x.md")
        self.assertIn("[DONE]", out.get("additionalContext", ""), msg=out)
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")

    def test_env_override_shrinks_the_stale_window(self) -> None:
        """`SDD_PENDING_OWNER_STALE_SECONDS` 可用環境變數覆寫成更短的陳舊窗口（決策 D19 明文
        『可 env 覆寫』；不得寫死 1800 常數本身無法調整）。"""
        owner_transcript = _write_transcript(self.root, 900_000, name="owner-shrink.jsonl")
        self._enter_pending_as(owner_transcript, "owner-shrink-sess")
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=10)).timestamp()
        os.utime(owner_transcript, (old_ts, old_ts))

        other_transcript = _write_transcript(self.root, 50_000, name="rescuer3.jsonl")
        with patch.dict(os.environ, {"SDD_PENDING_OWNER_STALE_SECONDS": "5"}, clear=False):
            out = self._run(other_transcript, "rescuer-session-3", tool="Read", target="docs/x.md")
        self.assertIn("[DONE]", out.get("additionalContext", ""), msg=out)


class NonStringSubagentTypeTests(_IsolatedFsmMixin, unittest.TestCase):
    """DEF-CLDREV-020: a non-string subagent_type/agent (list / dict / int) on a
    Task payload must NOT crash the pre hook."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def test_non_string_subagent_type_does_not_crash(self) -> None:
        env = {"SDD_SUBAGENT_CONTRACT": "1"}
        for bad in ([{"a": 1}], {"x": 1}, 123, ["a", "b"]):
            payload = {"tool_name": "Task", "tool_input": {"subagent_type": bad}}
            with patch.dict(os.environ, env, clear=False):
                out = self.runner.run(payload)
            hook_out = out.get("hookSpecificOutput", {})
            self.assertEqual(hook_out.get("hookEventName"), "PreToolUse", msg=f"value={bad!r}")
            self.assertNotIn("additionalContext", hook_out, msg=f"value={bad!r}")

    def test_non_string_agent_key_does_not_crash(self) -> None:
        env = {"SDD_SUBAGENT_CONTRACT": "1"}
        payload = {"tool_name": "Task", "tool_input": {"agent": {"nested": True}}}
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")


class MalformedPayloadTests(_IsolatedFsmMixin, unittest.TestCase):
    """DEF-CLDREV-025: non-dict top-level payload / tool_input must normalize to {}."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def test_top_level_list_does_not_crash(self) -> None:
        out = self.runner.run([1, 2, 3])
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")

    def test_list_tool_input_does_not_crash(self) -> None:
        out = self.runner.run({"tool_name": "Read", "tool_input": [1, 2, 3]})
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")

    def test_str_tool_input_does_not_crash(self) -> None:
        out = self.runner.run({"tool_name": "Read", "tool_input": "abc"})
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")

    def test_non_string_transcript_path_does_not_crash(self) -> None:
        out = self.runner.run({"tool_name": "Read", "tool_input": {}, "transcript_path": [1, 2]})
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")


class NonStringToolNameTests(_IsolatedFsmMixin, unittest.TestCase):
    """DEF-CLDREV-029 (SA 鏡 F-03): a non-string tool_name must be normalized to ""
    BEFORE reaching the FSM guardrail."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm(self.root)
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)
        self._seen_tools: list = []
        _orig = self._rt.assert_tool_allowed

        # D19（DEF-200-275 第六輪；SD-02）：生產碼呼叫端現在多帶一個 `session_id=` 關鍵字引數
        # （owner-scope 判準要用）；spy 簽名須同步接住，否則呼叫會在綁定引數這一步就拋
        # TypeError（比 `_orig` 的函式體還早），`self._seen_tools.append` 永遠不會執行到——
        # 這不是本測試要驗證的行為，是 monkeypatch 落後生產簽名的純技術性斷線。
        def _spy(tool, target=None, *, session_id=None):  # noqa: ANN001
            self._seen_tools.append(tool)
            return _orig(tool, target, session_id=session_id)

        self._rt.assert_tool_allowed = _spy  # type: ignore[method-assign]

    def tearDown(self) -> None:
        self._env.stop()
        self._release_fsm()
        self._tmp.cleanup()

    def _run(self, bad_tool_name) -> dict:  # noqa: ANN001
        return self.runner.run({"tool_name": bad_tool_name, "tool_input": {}})

    def test_list_tool_name_normalized_before_guardrail(self) -> None:
        out = self._run(["Bash"])
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(hook_out.get("hookEventName"), "PreToolUse")
        self.assertEqual(self._seen_tools, [""],
                         msg=f"guardrail saw {self._seen_tools!r}, expected normalized ['']")
        self.assertNotIn("guardrail unavailable", hook_out.get("additionalContext", ""))

    def test_dict_tool_name_normalized(self) -> None:
        out = self._run({"nested": True})
        self.assertEqual(self._seen_tools, [""])
        self.assertNotIn(
            "guardrail unavailable",
            out.get("hookSpecificOutput", {}).get("additionalContext", ""),
        )


if __name__ == "__main__":
    unittest.main()
