# enforces (governance rules): R-9.2, R-9.6
"""Unit tests for QA patches on `.claude/hooks/context_ledger_pre.py`.

Covers:
- P1-04: SDD_HOOKS_DISABLE=1 must NOT silence Subagent Contract injection.
- P1-05: Legacy Read fallback must include cat -n line overhead.
- P2-08: tokens==0 early-return must still run ESCALATION / AUTO_COMPACT checks.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Re-import the hook module with the repo root on sys.path. The module does
# its own path manipulation; we wrap it in a helper so each test gets a
# fresh module-level state (LEDGER_DIR, MAX_CONTEXT).
HOOK_MODULE_PATH = (
    Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "context_ledger_pre.py"
)


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


class _MainRunner:
    """Capture stdout from mod.main() given a JSON stdin payload."""

    def __init__(self, mod):
        self.mod = mod

    def run(self, payload: dict) -> dict:
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
        """Sanity check: HOOKS_DISABLE for non-Task tool still returns empty
        additionalContext (no false-positive injection)."""
        env = {"SDD_HOOKS_DISABLE": "1", "SDD_SUBAGENT_CONTRACT": "1"}
        payload = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertNotIn("additionalContext", hook_out)

    def test_hooks_disable_with_contract_off_skips_injection(self) -> None:
        """If subagent contract is explicitly off, HOOKS_DISABLE path stays
        quiet — the fix only preserves injection when the contract is ON."""
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
        # Write 10 short lines so line-count overhead is material relative to size.
        src.write_text("\n".join(f"l{i}" for i in range(10)) + "\n", encoding="utf-8")
        size = src.stat().st_size

        # Force the legacy fallback path by making estimate_tool_tokens raise.
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
        # Upper bound — should not exceed (size + 10*8)/4 + 1
        self.assertLessEqual(legacy, (size + 10 * 8) // 4 + 1)

    def test_fallback_read_missing_file_returns_zero(self) -> None:
        from tools.fsm_runtime import conversation_ledger as cl

        with patch.object(cl, "estimate_tool_tokens", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))):
            self.assertEqual(self.mod._estimate_tokens("Read", {"file_path": str(self.root / "nope.txt")}), 0)
            self.assertEqual(self.mod._estimate_tokens("Read", {"file_path": None}), 0)


class ZeroTokenEscalationTests(unittest.TestCase):
    """P2-08: zero-delta tool calls must still trigger TOKEN_BUDGET_CRITICAL
    / AUTO_COMPACT when cumulative ratio is already past threshold."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        # Small MAX_CONTEXT so we can cross thresholds easily
        self.mod.MAX_CONTEXT = 1000
        self.runner = _MainRunner(self.mod)

        # Isolate FSM state from the repo's real FSM-STATE-*.yaml so the hook
        # doesn't see a live ESCALATION / HUMAN_PENDING from another session.
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        self._fsm_state_path = self.root / "FSM-STATE-zerotoken.yaml"
        state = load_state("zerotoken-proj", path=self._fsm_state_path)
        state.current = "SPEC_DRAFTING"  # benign state; Bash is allowed
        self._isolated_rt = FSMRuntime(state)

        # Patch FSMRuntime.bootstrap used by the hook to return our isolated rt.
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._boot_patch = patch.object(
            fsm_rt_mod.FSMRuntime, "bootstrap",
            classmethod(lambda cls, project=None: self._isolated_rt),
        )
        self._boot_patch.start()

    def tearDown(self) -> None:
        self._boot_patch.stop()
        self._tmp.cleanup()

    def _seed_ledger(self, cumulative: int) -> None:
        """Write a minimal daily ledger with `cumulative` already spent."""
        import datetime as _dt
        import yaml  # noqa: WPS433

        path = self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
        doc = {
            "date": _dt.date.today().isoformat(),
            "cumulative_tokens": cumulative,
            "entries": [{"tokens": cumulative, "phase": "pre", "tool": "Seed"}],
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

    def test_zero_token_tool_still_denies_at_crit_ratio(self) -> None:
        # Cumulative already 96% of 1000 = 960. A Bash with empty command
        # estimates to 0 tokens → should hit TOKEN_BUDGET_CRITICAL branch.
        self._seed_ledger(960)
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(
            hook_out.get("permissionDecision"), "deny",
            msg=f"expected deny for tokens==0 at 96%, got: {hook_out}",
        )
        self.assertIn("TOKEN_BUDGET_CRITICAL", hook_out.get("permissionDecisionReason", ""))

    def test_zero_token_tool_triggers_auto_compact_at_90pct(self) -> None:
        """90-94% range with tokens==0 must trigger AUTO_COMPACT_PENDING
        via the new early-return branch (not silent pass-through)."""
        self._seed_ledger(920)  # 92%
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        ctx = hook_out.get("additionalContext", "")
        self.assertIn("AUTO-COMPACT", ctx,
                      msg=f"expected AUTO-COMPACT notice at 92% with tokens==0, got: {hook_out}")

    def test_zero_token_tool_under_warn_passes_through(self) -> None:
        """Sanity: tokens==0 below WARN_RATIO must NOT raise a warning."""
        self._seed_ledger(300)  # 30%
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", hook_out)
        self.assertNotIn("AUTO-COMPACT", hook_out.get("additionalContext", ""))


class MaxContextGuardTests(unittest.TestCase):
    """DEF-CLDREV-002 (symmetric) + DEF-CLDREV-012: a misconfigured
    SDD_MAX_CONTEXT (zero / negative / non-numeric) must NOT crash the pre hook
    at import time. A crash here silently disables the entire context-budget gate
    (cumulative tokens stop recording, 85% warn / 95% deny / auto-compact never
    fire) — the opposite of the hook's purpose."""

    def test_zero_floors_to_default(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "0"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertEqual(mod.MAX_CONTEXT, 200000)

    def test_negative_floors_to_default(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "-5"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertEqual(mod.MAX_CONTEXT, 200000)

    def test_non_numeric_falls_back_to_default(self) -> None:
        """Pre-fix: `int("abc")` raises ValueError at import → hook crashes.
        Post-fix: falls back to 200000, matching the 0/negative floor."""
        for bad in ("abc", "1.5", "12k"):
            with patch.dict(os.environ, {"SDD_MAX_CONTEXT": bad}, clear=False):
                mod = _load_hook_module(Path(tempfile.gettempdir()))
                self.assertEqual(mod.MAX_CONTEXT, 200000, msg=f"value={bad!r}")

    def test_valid_value_preserved(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "50000"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertEqual(mod.MAX_CONTEXT, 50000)


class WideContextWindowInferenceTests(unittest.TestCase):
    """DEF-200-275: SDD_MAX_CONTEXT unset (real-world default) must NOT treat
    the stale 200000 (old Claude-3-era context window) as the true ceiling
    once cumulative has actually exceeded it — that misread the real 2026-09
    incident (cumulative=200994, ratio=1.00 reported) as 100% full while the
    session's real /context reading was 378.8k/1,000,000 (38%)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        # Isolate FSM state from the repo's real FSM-STATE-*.yaml so the hook
        # doesn't see a live ESCALATION / HUMAN_PENDING from another session.
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        self._fsm_state_path = self.root / "FSM-STATE-widectx.yaml"
        state = load_state("widectx-proj", path=self._fsm_state_path)
        state.current = "SPEC_DRAFTING"  # benign state; Bash is allowed
        self._isolated_rt = FSMRuntime(state)

        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._boot_patch = patch.object(
            fsm_rt_mod.FSMRuntime, "bootstrap",
            classmethod(lambda cls, project=None: self._isolated_rt),
        )
        self._boot_patch.start()

    def tearDown(self) -> None:
        self._boot_patch.stop()
        self._tmp.cleanup()

    def _seed_ledger(self, cumulative: int) -> None:
        import datetime as _dt
        import yaml  # noqa: WPS433

        path = self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
        doc = {
            "date": _dt.date.today().isoformat(),
            "cumulative_tokens": cumulative,
            "entries": [{"tokens": cumulative, "phase": "pre", "tool": "Seed"}],
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

    def test_real_incident_cumulative_does_not_falsely_escalate(self) -> None:
        """Reproduces the 2026-09-10 incident exactly: cumulative=200994 with
        SDD_MAX_CONTEXT unset (guaranteed absent at import time via clear=True,
        not just ambient-environment luck). Pre-fix this computed ratio=1.00
        (>= CRIT_RATIO) and denied every tool call. Post-fix, 200994 is
        inferred to be under a 1,000,000-token window (ratio ≈ 0.20) — well
        under WARN_RATIO — so no deny and no AUTO-COMPACT notice should fire."""
        self._seed_ledger(200994)
        env_no_pin = dict(os.environ)
        env_no_pin.pop("SDD_MAX_CONTEXT", None)
        env_no_pin.update({
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        })
        with patch.dict(os.environ, env_no_pin, clear=True):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 200000)  # sanity: floor unchanged
            runner = _MainRunner(mod)
            payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
            out = runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertNotIn(
            "permissionDecision", hook_out,
            msg=f"expected no deny for real-incident cumulative, got: {hook_out}",
        )
        self.assertNotIn("AUTO-COMPACT", hook_out.get("additionalContext", ""))

    def test_explicit_sdd_max_context_pin_still_denies_at_200k(self) -> None:
        """An operator who explicitly sets SDD_MAX_CONTEXT=200000 (e.g. testing
        against a genuinely small-window model) must still get the strict
        200000 ceiling enforced — the DEF-200-275 inference must not silently
        override an explicit operator choice."""
        self._seed_ledger(200994)
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
            "SDD_MAX_CONTEXT": "200000",
        }, clear=False):
            mod = _load_hook_module(self.root)
            runner = _MainRunner(mod)
            payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
            out = runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(
            hook_out.get("permissionDecision"), "deny",
            msg=f"expected deny when SDD_MAX_CONTEXT is explicitly pinned to 200000, got: {hook_out}",
        )
        self.assertIn("TOKEN_BUDGET_CRITICAL", hook_out.get("permissionDecisionReason", ""))


class MaxContextConfirmedUnitTests(unittest.TestCase):
    """Direct unit coverage for `_max_context_confirmed` (DEF-200-275 第二輪) —
    the gate that decides whether the current denominator is trustworthy
    enough to drive CRIT/AUTO_COMPACT, mirroring the sister guard's
    `may_block(source) != SOURCE_INFERRED_FLOOR` semantics."""

    def test_unpinned_at_or_below_conservative_default_is_unconfirmed(self) -> None:
        env_no_pin = dict(os.environ)
        env_no_pin.pop("SDD_MAX_CONTEXT", None)
        with patch.dict(os.environ, env_no_pin, clear=True):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            for cum in (0, 170000, 180000, 190000, 199999, 200000):
                self.assertFalse(mod._max_context_confirmed(cum), msg=f"cumulative={cum}")

    def test_unpinned_above_conservative_default_is_confirmed(self) -> None:
        env_no_pin = dict(os.environ)
        env_no_pin.pop("SDD_MAX_CONTEXT", None)
        with patch.dict(os.environ, env_no_pin, clear=True):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            for cum in (200001, 250000, 500000, 999999):
                self.assertTrue(mod._max_context_confirmed(cum), msg=f"cumulative={cum}")

    def test_pinned_is_always_confirmed_even_at_the_default_value(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "200000"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            for cum in (0, 100000, 190000, 200000, 500000):
                self.assertTrue(mod._max_context_confirmed(cum), msg=f"cumulative={cum}")

    def test_malformed_pin_at_190000_is_unconfirmed(self) -> None:
        """DEF-200-275 第三輪（四方複審 QA/SA 各自獨立發現、SA 判 REJECT 後
        訂正）：SDD_MAX_CONTEXT 設成解析失敗或非正整數的壞值（操作者打錯字）
        不得被誤判為「已釘住」。壞值集合沿用 MaxContextGuardTests 既有測資
        （"abc"/"1.5"/"12k"/空字串/"0"/"-5"）——這些值都會讓 _RAW_MAX_CONTEXT
        正確 fallback 回 200000（MaxContextGuardTests 已驗證這一半），但修復前
        _SDD_MAX_CONTEXT_PINNED 只問「環境變數是否存在」，錯誤地讀作 True，
        導致 190000（真實 1,000,000 視窗下僅 19% 用量）被誤判為已確認分母而
        硬鎖 ESCALATION——本測試釘住 `_max_context_confirmed(190000)` 在這組
        壞值下必須是 False（未確認，不應硬鎖）。"""
        for bad in ("abc", "1.5", "12k", "", "0", "-5"):
            with patch.dict(os.environ, {"SDD_MAX_CONTEXT": bad}, clear=False):
                mod = _load_hook_module(Path(tempfile.gettempdir()))
                self.assertFalse(mod._SDD_MAX_CONTEXT_PINNED, msg=f"value={bad!r}")
                self.assertFalse(
                    mod._max_context_confirmed(190000), msg=f"value={bad!r}"
                )

    def test_valid_pin_at_190000_is_confirmed(self) -> None:
        """對照組：SDD_MAX_CONTEXT 設成有效正整數（"200000"）時，190000 仍應
        正確回傳 True（已確認）——修復不能連帶修壞這個正常情境。"""
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "200000"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertTrue(mod._SDD_MAX_CONTEXT_PINNED)
            self.assertTrue(mod._max_context_confirmed(190000))


class DEF200275NaturalClimbTests(unittest.TestCase):
    """DEF-200-275 第二輪（四方獨立複審 REJECT 後訂正）：SA／QA 兩位審查員實測
    證實第一版修復（只在 cumulative > 200000 才切分母）留了一個區間性回歸——
    CRIT_RATIO(0.95) × 200000 = 190000，比切換點 200001 早一萬。cumulative
    單調爬升，任何 session 必然先經過 190000~200000 才可能到 200001，因此在
    切換生效之前就已經在 190000 被 ratio=0.95 鎖進 ESCALATION（對真實
    1,000,000 視窗而言僅 19% 用量）——同一個缺陷只是把觸發點從 ~100% 移到
    ~95%，本質重演。

    本測試模擬 cumulative 依序爬過 170000 → 180000 → 190000 → 199999 →
    200000 → 200001 → 250000（SDD_MAX_CONTEXT 未顯式設定的真實情境，非單點
    seed），驗證整條路徑上 FSM state 都不會被鎖進 ESCALATION；並保留對照組：
    操作者顯式設定 SDD_MAX_CONTEXT=200000 時，190000（ratio=0.95）仍應正常
    觸發 CRIT／ESCALATION——那是操作者自己選的小視窗，不是誤判。
    """

    _PATH = (170000, 180000, 190000, 199999, 200000, 200001, 250000)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        # Isolate FSM state so the natural-climb assertions observe only this
        # test's transitions, not a live ESCALATION from another session.
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        self._fsm_state_path = self.root / "FSM-STATE-climb.yaml"
        state = load_state("climb-proj", path=self._fsm_state_path)
        state.current = "SPEC_DRAFTING"  # benign state; Bash is allowed
        self._isolated_rt = FSMRuntime(state)

        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._boot_patch = patch.object(
            fsm_rt_mod.FSMRuntime, "bootstrap",
            classmethod(lambda cls, project=None: self._isolated_rt),
        )
        self._boot_patch.start()

    def tearDown(self) -> None:
        self._boot_patch.stop()
        self._tmp.cleanup()

    def _seed_ledger(self, cumulative: int) -> None:
        import datetime as _dt
        import yaml  # noqa: WPS433

        path = self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
        doc = {
            "date": _dt.date.today().isoformat(),
            "cumulative_tokens": cumulative,
            "entries": [{"tokens": cumulative, "phase": "pre", "tool": "Seed"}],
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

    def test_natural_climb_never_escalates_when_denominator_unconfirmed(self) -> None:
        env_no_pin = dict(os.environ)
        env_no_pin.pop("SDD_MAX_CONTEXT", None)
        env_no_pin.update({
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        })
        with patch.dict(os.environ, env_no_pin, clear=True):
            mod = _load_hook_module(self.root)
            self.assertFalse(mod._SDD_MAX_CONTEXT_PINNED)  # sanity: truly unset
            runner = _MainRunner(mod)
            prev = 0
            for target in self._PATH:
                delta = target - prev
                prev = target
                # Fix the per-step token delta deterministically so cumulative
                # lands exactly on each checkpoint — real /context growth is
                # continuous, this pins it to the exact reported incident values.
                with patch.object(mod, "_estimate_tokens", lambda *_a, tokens=delta, **_k: tokens):
                    out = runner.run({"tool_name": "Bash", "tool_input": {"command": "x"}})
                hook_out = out.get("hookSpecificOutput", {})
                self.assertNotEqual(
                    hook_out.get("permissionDecision"), "deny",
                    msg=f"cumulative={target}: unexpectedly denied — {hook_out}",
                )
                self.assertEqual(
                    self._isolated_rt.state.current, "SPEC_DRAFTING",
                    msg=(
                        f"cumulative={target}: FSM state unexpectedly transitioned to "
                        f"{self._isolated_rt.state.current!r} while the denominator was "
                        "still an unconfirmed guess (DEF-200-275 regression reproduced)"
                    ),
                )

    def test_explicit_pin_still_escalates_at_190000(self) -> None:
        """Control group: an operator who explicitly sets SDD_MAX_CONTEXT=200000
        (a genuinely small-window session) must still get real CRIT/ESCALATION
        protection at 190000/200000 = 95% — the unconfirmed-denominator downgrade
        must never silently swallow a deliberate small-window configuration."""
        self._seed_ledger(189000)  # next +1000 lands exactly on 190000
        env = {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
            "SDD_MAX_CONTEXT": "200000",
        }
        with patch.dict(os.environ, env, clear=False):
            mod = _load_hook_module(self.root)
            self.assertTrue(mod._SDD_MAX_CONTEXT_PINNED)
            runner = _MainRunner(mod)
            with patch.object(mod, "_estimate_tokens", lambda *_a, **_k: 1000):
                out = runner.run({"tool_name": "Bash", "tool_input": {"command": "x"}})
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(
            hook_out.get("permissionDecision"), "deny",
            msg=f"expected deny at 190000/200000=95% with SDD_MAX_CONTEXT pinned, got: {hook_out}",
        )
        self.assertIn("TOKEN_BUDGET_CRITICAL", hook_out.get("permissionDecisionReason", ""))
        self.assertEqual(self._isolated_rt.state.current, "ESCALATION")


class NonStringSubagentTypeTests(unittest.TestCase):
    """DEF-CLDREV-020: a non-string subagent_type/agent (list / dict / int) on a
    Task payload must NOT crash the pre hook. Pre-fix `_build_subagent_notice`
    called `.strip()` on the raw value → AttributeError → hook exits non-zero,
    silently dropping the PreToolUse JSON. This path became reachable only after
    DEF-CLDREV-017 added `Task` to the PreToolUse matcher, so it is the input-domain
    sibling of DEF-CLDREV-012 (non-numeric SDD_MAX_CONTEXT)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_non_string_subagent_type_does_not_crash(self) -> None:
        # contract ON (soft) so the code path reaches the agent_name extraction.
        env = {"SDD_SUBAGENT_CONTRACT": "1"}
        for bad in ([{"a": 1}], {"x": 1}, 123, ["a", "b"]):
            payload = {"tool_name": "Task", "tool_input": {"subagent_type": bad}}
            with patch.dict(os.environ, env, clear=False):
                # _MainRunner.run asserts rc == 0; pre-fix this raised AttributeError.
                out = self.runner.run(payload)
            hook_out = out.get("hookSpecificOutput", {})
            self.assertEqual(hook_out.get("hookEventName"), "PreToolUse",
                             msg=f"value={bad!r}")
            # non-string ⇒ treated as no agent ⇒ no contract injection (graceful).
            self.assertNotIn("additionalContext", hook_out, msg=f"value={bad!r}")

    def test_non_string_agent_key_does_not_crash(self) -> None:
        env = {"SDD_SUBAGENT_CONTRACT": "1"}
        payload = {"tool_name": "Task", "tool_input": {"agent": {"nested": True}}}
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        self.assertEqual(
            out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")


class MalformedPayloadTests(unittest.TestCase):
    """DEF-CLDREV-025: a JSON-valid but non-dict top-level payload (`[1,2,3]`)
    does NOT raise json.JSONDecodeError, so the except branch never fires and the
    subsequent `inp.get(...)` / `tool_input.get(...)` raised AttributeError →
    hook exits non-zero and the PreToolUse JSON is dropped. Same input-domain
    class as DEF-CLDREV-012 (non-numeric SDD_MAX_CONTEXT) / DEF-CLDREV-020
    (non-string subagent_type). Both `inp` and `tool_input` must normalize to {}."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_top_level_list_does_not_crash(self) -> None:
        # _MainRunner.run asserts rc == 0; pre-fix this raised AttributeError at
        # `inp.get("tool_name")`. _FakeStdin serializes via json.dumps so a list
        # payload reaches main() exactly as Claude Code would deliver malformed JSON.
        out = self.runner.run([1, 2, 3])  # type: ignore[arg-type]
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")

    def test_list_tool_input_does_not_crash(self) -> None:
        out = self.runner.run({"tool_name": "Read", "tool_input": [1, 2, 3]})  # type: ignore[dict-item]
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")

    def test_str_tool_input_does_not_crash(self) -> None:
        out = self.runner.run({"tool_name": "Read", "tool_input": "abc"})  # type: ignore[dict-item]
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PreToolUse")


class NonStringToolNameTests(unittest.TestCase):
    """DEF-CLDREV-029 (SA 鏡 F-03): a non-string tool_name (list / dict / int)
    must be normalized to "" BEFORE reaching the FSM guardrail. Pre-fix it reached
    `assert_tool_allowed([...], target)` → TypeError → caught by the broad except →
    degraded to a "guardrail unavailable" warn-pass, silently bypassing FSM
    enforcement for that call. Same input-domain class as DEF-CLDREV-020/025."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        state = load_state("toolname-proj", path=self.root / "FSM-STATE-toolname.yaml")
        state.current = "SPEC_DRAFTING"  # benign state
        self._isolated_rt = FSMRuntime(state)

        # Spy on assert_tool_allowed to capture the exact `tool` argument it receives.
        self._seen_tools: list = []
        _orig = self._isolated_rt.assert_tool_allowed

        def _spy(tool, target=None):  # noqa: ANN001
            self._seen_tools.append(tool)
            return _orig(tool, target)

        self._isolated_rt.assert_tool_allowed = _spy  # type: ignore[method-assign]

        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._boot_patch = patch.object(
            fsm_rt_mod.FSMRuntime, "bootstrap",
            classmethod(lambda cls, project=None: self._isolated_rt),
        )
        self._boot_patch.start()

    def tearDown(self) -> None:
        self._boot_patch.stop()
        self._tmp.cleanup()

    def _run(self, bad_tool_name) -> dict:  # noqa: ANN001
        payload = {"tool_name": bad_tool_name, "tool_input": {}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            return self.runner.run(payload)  # type: ignore[arg-type]

    def test_list_tool_name_normalized_before_guardrail(self) -> None:
        out = self._run(["Bash"])
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(hook_out.get("hookEventName"), "PreToolUse")
        # Non-hollow: the guardrail must have been reached with a *string* tool
        # (normalized ""), not the raw list — proving no TypeError bypass.
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
