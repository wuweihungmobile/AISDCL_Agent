# enforces (governance rules): R-9.2, R-9.6
"""Unit tests for QA patches on `.claude/hooks/context_ledger_post.py`.

Covers:
- DEF-CLDREV-002: SDD_MAX_CONTEXT=0 / negative must NOT crash the :140 ratio
  calculation (cumulative / MAX_CONTEXT) with ZeroDivisionError — symmetric with
  the floor guard already present in context_ledger_pre.py:31-35.
"""
from __future__ import annotations

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

HOOK_MODULE_PATH = (
    Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "context_ledger_post.py"
)


def _load_hook_module(tmp_root: Path):
    """Import the post hook fresh so module-level MAX_CONTEXT reflects the env
    set by the caller (it is read at import time, like the pre hook)."""
    spec = importlib.util.spec_from_file_location("context_ledger_post_test", str(HOOK_MODULE_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_root
    return mod


class _MainRunner:
    def __init__(self, mod):
        self.mod = mod

    def run(self, payload: dict) -> dict:
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


class MaxContextFloorTests(unittest.TestCase):
    """DEF-CLDREV-002: zero / negative SDD_MAX_CONTEXT must degrade gracefully."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_with_env(self, max_ctx: str) -> dict:
        # A non-empty tool_response → _estimate_result_tokens > 0 → cumulative > 0
        # → the :140 `ratio = cumulative / MAX_CONTEXT` line is exercised.
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x"},
            "tool_response": "x" * 4000,
        }
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": max_ctx}, clear=False):
            mod = _load_hook_module(self.root)
            return _MainRunner(mod).run(payload)

    def test_zero_max_context_does_not_crash(self) -> None:
        """Pre-fix: MAX_CONTEXT=0 → ZeroDivisionError at :140 → hook crashes.
        Post-fix: floored to 200000, ratio computed, hook returns cleanly."""
        out = self._run_with_env("0")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_negative_max_context_does_not_crash(self) -> None:
        out = self._run_with_env("-5")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_floor_applied_value(self) -> None:
        """Intent (Rule 9): the floor must land on 200000, matching the pre hook,
        so a misconfigured operator gets the same graceful budget — not an
        arbitrary value or a crash."""
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "0"}, clear=False):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 200000)
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "50000"}, clear=False):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 50000)  # valid value preserved

    def test_non_numeric_max_context_does_not_crash(self) -> None:
        """DEF-CLDREV-012: a non-numeric SDD_MAX_CONTEXT (operator typo) must NOT
        raise ValueError at import time. Pre-fix: `int("abc")` crashes the whole
        hook → the context-budget gate is silently disabled. Post-fix: falls back
        to the 200000 default and the hook runs cleanly."""
        out = self._run_with_env("abc")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")
        out = self._run_with_env("1.5")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_non_numeric_falls_back_to_default(self) -> None:
        """Intent (Rule 9): a non-numeric value must land on the same 200000 floor
        as 0/negative, so the gate keeps a sane budget rather than vanishing."""
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "abc"}, clear=False):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 200000)


class MaxContextConfirmedUnitTests(unittest.TestCase):
    """Direct unit coverage for `_max_context_confirmed` (DEF-200-275 第二輪),
    symmetric with the pre hook's test of the same name."""

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
        """DEF-200-275 第三輪（symmetric with the pre hook's test of the same
        name）：SDD_MAX_CONTEXT 設成解析失敗或非正整數的壞值（操作者打錯字）
        不得被誤判為「已釘住」。壞值集合沿用 MaxContextFloorTests 既有測資
        （"abc"/"1.5"/"12k"/空字串/"0"/"-5"）——這些值都會讓 _RAW_MAX_CONTEXT
        正確 fallback 回 200000，但修復前 _SDD_MAX_CONTEXT_PINNED 只問「環境
        變數是否存在」，錯誤地讀作 True，導致 190000（真實 1,000,000 視窗下
        僅 19% 用量）被誤判為已確認分母而硬鎖 AUTO_COMPACT/CRIT。"""
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
    """DEF-200-275 第二輪（四方獨立複審 REJECT 後訂正）：symmetric with
    context_ledger_pre.py 的同名測試類別。post hook 自己的 AUTO_COMPACT 觸發點
    是保守預設分母的 90%＝180000（對真實 1,000,000 視窗僅 18% 用量），第一版
    修復同樣會在這裡把 FSM 提前鎖進 AUTO_COMPACT_PENDING（甚至在 per-stage 上限
    超過時進一步鎖進 ESCALATION）。本測試模擬 cumulative 依序爬過 170000 →
    180000 → 190000 → 199999 → 200000 → 200001 → 250000（SDD_MAX_CONTEXT 未
    顯式設定），驗證整條路徑上 FSM state 都不會被鎖住；並保留對照組：操作者
    顯式設定 SDD_MAX_CONTEXT=200000 時，180000/200000=90% 仍應正常觸發
    AUTO_COMPACT_PENDING——那是操作者自己選的小視窗，不是誤判。
    """

    _PATH = (170000, 180000, 190000, 199999, 200000, 200001, 250000)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        self._fsm_state_path = self.root / "FSM-STATE-climb-post.yaml"
        state = load_state("climb-post-proj", path=self._fsm_state_path)
        state.current = "SPEC_DRAFTING"  # benign state
        self._isolated_rt = FSMRuntime(state)

        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._boot_patch = patch.object(
            fsm_rt_mod.FSMRuntime, "bootstrap",
            classmethod(lambda cls, project=None: self._isolated_rt),
        )
        self._boot_patch.start()

        # 每次工具呼叫只讓 cumulative 精準走到目標值——conv-overhead merge 每
        # 10 次呼叫（entries_per_call=2）才會 tick 一次，本測試遠低於門檻，
        # 但仍顯式 stub 掉以免未來調參讓這條路徑意外偷渡額外 token。
        self._overhead_patch = patch(
            "tools.fsm_runtime.conversation_ledger.merge_conversation_overhead_into_ledger",
            lambda *_a, **_k: {"merged": False, "added_tokens": 0, "cumulative": 0},
        )
        self._overhead_patch.start()

    def tearDown(self) -> None:
        self._overhead_patch.stop()
        self._boot_patch.stop()
        self._tmp.cleanup()

    def _seed_ledger(self, cumulative: int) -> None:
        import datetime as _dt
        import yaml  # noqa: WPS433

        path = self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
        doc = {
            "date": _dt.date.today().isoformat(),
            "cumulative_tokens": cumulative,
            "entries": [{"tokens": cumulative, "phase": "post", "tool": "Seed"}],
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

    def test_natural_climb_never_locks_fsm_when_denominator_unconfirmed(self) -> None:
        env_no_pin = dict(os.environ)
        env_no_pin.pop("SDD_MAX_CONTEXT", None)
        # This dev environment's ambient shell sets SDD_HOOKS_DISABLE=1 (see repo
        # memory note on zshrc leakage) — override explicitly so the hook's own
        # logic is actually exercised, not silently no-op'd via the disable path.
        env_no_pin["SDD_HOOKS_DISABLE"] = ""
        with patch.dict(os.environ, env_no_pin, clear=True):
            mod = _load_hook_module(self.root)
            self.assertFalse(mod._SDD_MAX_CONTEXT_PINNED)  # sanity: truly unset
            runner = _MainRunner(mod)
            prev = 0
            for target in self._PATH:
                delta = target - prev
                prev = target
                payload = {
                    "tool_name": "Read",
                    "tool_input": {"file_path": "/tmp/x"},
                    "tool_response": "x",
                }
                with patch.object(
                    mod, "_estimate_result_tokens", lambda *_a, tokens=delta, **_k: tokens
                ):
                    out = runner.run(payload)
                hook_out = out.get("hookSpecificOutput", {})
                self.assertNotIn(
                    "ESCALATION", hook_out.get("additionalContext", "") or "",
                    msg=f"cumulative={target}: {hook_out}",
                )
                self.assertEqual(
                    self._isolated_rt.state.current, "SPEC_DRAFTING",
                    msg=(
                        f"cumulative={target}: FSM state unexpectedly transitioned to "
                        f"{self._isolated_rt.state.current!r} while the denominator was "
                        "still an unconfirmed guess (DEF-200-275 regression reproduced)"
                    ),
                )

    def test_explicit_pin_still_triggers_auto_compact_at_180000(self) -> None:
        """Control group: SDD_MAX_CONTEXT=200000 explicit ⇒ confirmed denominator
        ⇒ 180000/200000 = 90% must still trigger real AUTO_COMPACT_PENDING."""
        self._seed_ledger(179000)  # next +1000 lands exactly on 180000
        env = dict(os.environ)
        env["SDD_MAX_CONTEXT"] = "200000"
        env["SDD_HOOKS_DISABLE"] = ""  # see note in the sibling test above
        with patch.dict(os.environ, env, clear=False):
            mod = _load_hook_module(self.root)
            self.assertTrue(mod._SDD_MAX_CONTEXT_PINNED)
            runner = _MainRunner(mod)
            payload = {
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/x"},
                "tool_response": "x",
            }
            with patch.object(mod, "_estimate_result_tokens", lambda *_a, **_k: 1000):
                out = runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertIn("AUTO-COMPACT", hook_out.get("additionalContext", ""))
        self.assertEqual(self._isolated_rt.state.current, "AUTO_COMPACT_PENDING")


class MalformedPayloadTests(unittest.TestCase):
    """DEF-CLDREV-025: symmetric with the pre hook — a JSON-valid but non-dict
    top-level payload (`[1,2,3]`) or non-dict tool_input must NOT crash the post
    hook with AttributeError at `inp.get(...)` / `tool_input.get(...)`. Both must
    normalize to {}."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_top_level_list_does_not_crash(self) -> None:
        out = self.runner.run([1, 2, 3])  # type: ignore[arg-type]
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_list_tool_input_does_not_crash(self) -> None:
        out = self.runner.run(
            {"tool_name": "Read", "tool_input": [1, 2, 3], "tool_response": "x"}  # type: ignore[dict-item]
        )
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")


if __name__ == "__main__":
    unittest.main()
