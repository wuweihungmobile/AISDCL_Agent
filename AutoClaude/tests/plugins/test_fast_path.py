"""FastPathPlugin 單元測試（SD_Improving_05 W4-2）。

驗證：
  - PRE_ATTEMPT phase 訂閱與 priority
  - regex 偵測 pytest FAILED / ERROR collecting 中的 test 檔案
  - regex 偵測 fallback：純路徑模式
  - py_compile 失敗 → PromptInjectionResult（含檔案路徑 + stderr 截斷）
  - py_compile 成功 → None
  - attempt != 0 → None（fast path 僅在首次嘗試）
  - eval_output 為空或缺失 → None
  - 異常 phase 觸發 → None
  - subprocess 失敗（FileNotFoundError）→ 預設 compiler 視為通過
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch

from autoclaude.core.hookspec import (
    HookContext,
    KernelPhase,
    PromptInjectionResult,
)
from autoclaude.plugins.fast_path_plugin import FastPathPlugin, _default_compiler
from tests.plugins._template import make_ctx, sample_playbook, sample_task


def _make_ctx(eval_output: str = "", attempt: int = 0):
    return make_ctx(
        phase=KernelPhase.PRE_ATTEMPT,
        playbook=sample_playbook(),
        task=sample_task("T01"),
        step_idx=0,
        attempt=attempt,
        payload={"eval_output": eval_output},
    )


class TestFastPathPluginBasics:
    def test_name_and_priority(self):
        p = FastPathPlugin()
        # wiring SSOT 對齊 _REGISTER_ORDER（"fast_path"）
        assert p.name() == "fast_path"
        assert p.priority() == FastPathPlugin.PRIORITY

    def test_subscribed_phases_only_pre_attempt(self):
        p = FastPathPlugin()
        assert p.subscribed_phases() == [KernelPhase.PRE_ATTEMPT]

    def test_returns_none_on_other_phase(self):
        # 防呆：即使誤接其他 phase 也不應動作
        p = FastPathPlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT,
            playbook=sample_playbook(),
            task=sample_task(),
            step_idx=0,
            attempt=0,
            payload={"eval_output": "ERROR collecting tests/test_a.py"},
        )
        assert p.on_event(ctx) is None


class TestFastPathRegexDetection:
    def test_primary_pattern_failed_marker(self):
        # 注入 fake compiler：模擬語法錯誤
        p = FastPathPlugin(compiler=lambda f, t: (1, "SyntaxError: invalid syntax"))
        ctx = _make_ctx("FAILED tests/test_foo.py::test_x - assert 1==2")
        result = p.on_event(ctx)
        assert isinstance(result, PromptInjectionResult)
        assert "tests/test_foo.py" in result.prefix
        assert "硬性約束" in result.prefix
        assert "SyntaxError" in result.prefix
        assert result.position == "top"
        assert result.contributor == "fast_path"

    def test_primary_pattern_error_collecting(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, "boom"))
        ctx = _make_ctx("ERROR collecting tests/sub/test_bar.py")
        result = p.on_event(ctx)
        assert isinstance(result, PromptInjectionResult)
        assert "tests/sub/test_bar.py" in result.prefix

    def test_fallback_pattern_when_primary_missing(self):
        # 沒有 FAILED/ERROR 字樣，但路徑符合 fallback
        p = FastPathPlugin(compiler=lambda f, t: (1, "syntax broken"))
        ctx = _make_ctx("some random output mentioning tests/test_z.py somewhere")
        result = p.on_event(ctx)
        assert isinstance(result, PromptInjectionResult)
        assert "tests/test_z.py" in result.prefix

    def test_no_match_returns_none(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, ""))
        ctx = _make_ctx("totally unrelated output without any test file path")
        assert p.on_event(ctx) is None

    def test_path_normalizes_backslash_to_forward_slash(self):
        # Windows 路徑 → 正規化
        p = FastPathPlugin(compiler=lambda f, t: (1, "x"))
        ctx = _make_ctx("FAILED tests\\sub\\test_win.py")
        result = p.on_event(ctx)
        assert isinstance(result, PromptInjectionResult)
        assert "tests/sub/test_win.py" in result.prefix

    def test_windows_absolute_path_not_matched_documented(self):
        # SD-m7：記錄當前行為 — Windows 絕對路徑（C:\...）首字非 _FALLBACK_PATTERN
        # 起點允許字元，將被略過；W6 hardening 階段補錨點
        p = FastPathPlugin(compiler=lambda f, t: (1, "X"))
        ctx = _make_ctx("FAILED C:\\Users\\me\\tests\\test_abs.py")
        # 主 pattern 要求 tests?|src 開頭，不會匹配 C:；fallback 要求路徑首字
        # 為 [/\\\w-]，'C' 雖在 \w 中可被起點匹配，會抓到 'tests/test_abs.py' 子串
        result = p.on_event(ctx)
        # 預期 fallback 匹配到尾段 "tests/test_abs.py"
        assert isinstance(result, PromptInjectionResult)
        assert "tests/test_abs.py" in result.prefix


class TestFastPathCompileBehavior:
    def test_compile_success_returns_none(self):
        # 真實場景：偵測到 test 檔但 py_compile 通過 → 不注入
        p = FastPathPlugin(compiler=lambda f, t: (0, ""))
        ctx = _make_ctx("FAILED tests/test_ok.py::test_x")
        assert p.on_event(ctx) is None

    def test_stderr_truncated_to_200_chars(self):
        long_err = "X" * 500
        p = FastPathPlugin(compiler=lambda f, t: (1, long_err))
        ctx = _make_ctx("FAILED tests/test_long.py")
        result = p.on_event(ctx)
        # 200 字元截斷
        assert "X" * 200 in result.prefix
        # 整段 500 不應全部出現（截到 200）
        assert "X" * 201 not in result.prefix

    def test_default_compiler_handles_filenotfound(self):
        # subprocess.run 拋 FileNotFoundError → 預設 compiler 視為 returncode=0
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            rc, err = _default_compiler("tests/test_missing.py", timeout=5)
            assert rc == 0
            assert err == ""

    def test_default_compiler_handles_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=5)):
            rc, err = _default_compiler("tests/test_slow.py", timeout=5)
            assert rc == 0
            assert err == ""

    def test_default_compiler_handles_oserror(self):
        # SD-M3 假陰性風險：OSError → 視為通過但 log warning
        with patch("subprocess.run", side_effect=OSError("disk error")):
            rc, err = _default_compiler("tests/test_a.py", timeout=5)
            assert rc == 0
            assert err == ""

    def test_default_compiler_handles_permissionerror(self):
        with patch("subprocess.run", side_effect=PermissionError("denied")):
            rc, err = _default_compiler("tests/test_a.py", timeout=5)
            assert rc == 0
            assert err == ""

    def test_default_compiler_real_invocation(self, tmp_path):
        # 真實呼叫 py_compile：寫一個語法錯誤的測試檔，預期 returncode != 0
        bad = tmp_path / "test_bad.py"
        bad.write_text("def broken(:\n  pass\n", encoding="utf-8")
        rc, err = _default_compiler(str(bad), timeout=10)
        assert rc != 0
        assert err  # stderr 應非空


class TestFastPathAttemptGuard:
    def test_attempt_nonzero_returns_none(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, "err"))
        ctx = _make_ctx("FAILED tests/test_a.py", attempt=1)
        assert p.on_event(ctx) is None

    def test_attempt_zero_triggers(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, "err"))
        ctx = _make_ctx("FAILED tests/test_a.py", attempt=0)
        assert isinstance(p.on_event(ctx), PromptInjectionResult)

    def test_attempt_none_treated_as_first(self):
        # 邊界：attempt 缺失（未傳）視同首次
        p = FastPathPlugin(compiler=lambda f, t: (1, "err"))
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT,
            playbook=sample_playbook(),
            task=sample_task(),
            step_idx=0,
            attempt=None,
            payload={"eval_output": "FAILED tests/test_q.py"},
        )
        assert isinstance(p.on_event(ctx), PromptInjectionResult)


class TestFastPathEmptyEvalOutput:
    def test_empty_string_returns_none(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, "err"))
        ctx = _make_ctx("")
        assert p.on_event(ctx) is None

    def test_missing_eval_output_returns_none(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, "err"))
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT,
            playbook=sample_playbook(),
            task=sample_task(),
            step_idx=0,
            attempt=0,
            payload={},
        )
        assert p.on_event(ctx) is None

    def test_none_payload_returns_none(self):
        p = FastPathPlugin(compiler=lambda f, t: (1, "err"))
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT,
            playbook=sample_playbook(),
            task=sample_task(),
            step_idx=0,
            attempt=0,
            payload={},
        )
        assert p.on_event(ctx) is None
