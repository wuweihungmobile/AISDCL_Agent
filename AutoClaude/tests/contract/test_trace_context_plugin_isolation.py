"""tests/contract/test_trace_context_plugin_isolation.py — F-09 / ADR-SD09-004 §3.1 紅線 ❌23-B。

設計動機：
  ADR-SD09-004 §3 拍板「Rule 8 取消新增」（保持 importlinter 7 kept），改以
  contract test 覆蓋 plugin 對 `utils.observability_helpers` 系列模組的隔離。
  本 test 為紅線 ❌23-B 的唯一程式化柵欄。

驗證目標：
  Case 1：以 AST 掃描所有 `autoclaude/plugins/*.py`（含 sub-package），確認**沒有**直接
          `import autoclaude.utils.knowledge_base_metrics` 或
          `from autoclaude.utils.trace_context import ...`（必須走 IObservabilityPort 注入）
  Case 2：驗證 `IObservabilityPort.emit_counter` 介面 contract — 簽名固定、duck-typing
          相容、`NullObservability` 為合法 fallback
  Case 3：驗證 `propagate_to_subprocess_env()` 不洩漏 trace_id 為 None 至 env
          （ADR-SD09-004 §4.1 路徑 a 路徑安全性）

例外白名單：
  - 與 `.importlinter` Rule 7 對齊：
    1. `autoclaude.utils.knowledge_base` → `autoclaude.utils.knowledge_base_metrics`
       （aggregator pattern；非 plugin 業務邏輯）
    2. `autoclaude.core.event_bus` → `autoclaude.utils.trace_context`
       （框架層 lazy import；非 plugin）

對應：
  - ADR-SD09-004 §3.1 紅線 ❌23-B
  - ADR-SD08-004 §2.1 邊界劃分 + §2.2 IObservabilityPort 簽名
  - .importlinter Rule 7 plugin-no-utils-observability-direct-import
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PLUGINS_DIR = _ROOT / "autoclaude" / "plugins"

_FORBIDDEN_MODULES = {
    "autoclaude.utils.knowledge_base_metrics",
    "autoclaude.utils.trace_context",
}


# ──────────────────────────────────────────────────────────────
# Case 1：AST 掃描 plugin 模組禁直接 import
# ──────────────────────────────────────────────────────────────
def _collect_imports(path: Path) -> set[str]:
    """以 ast 抽出檔案內所有 import / from import 的 fully qualified module path。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def _iter_plugin_files() -> list[Path]:
    """列舉所有 plugin 模組（含 sub-package 如 checkpoint/ token_guard/）。

    排除：__pycache__、__init__.py（純 re-export，不含業務邏輯）
    """
    files: list[Path] = []
    for p in _PLUGINS_DIR.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        if p.name == "__init__.py":
            continue
        files.append(p)
    return files


class TestPluginAstScanIsolation:
    """Case 1：AST 掃描全 plugin 樹禁直接 import observability helpers。"""

    def test_plugin_dir_exists(self):
        assert _PLUGINS_DIR.exists(), f"plugin 目錄不存在：{_PLUGINS_DIR}"

    def test_no_plugin_imports_forbidden_modules(self):
        """所有 plugin 模組不可直接 import knowledge_base_metrics / trace_context。"""
        violations: dict[str, set[str]] = {}
        for plugin_file in _iter_plugin_files():
            imports = _collect_imports(plugin_file)
            bad = imports & _FORBIDDEN_MODULES
            if bad:
                rel = plugin_file.relative_to(_ROOT).as_posix()
                violations[rel] = bad
        assert not violations, (
            "違反 ADR-SD09-004 §3.1 紅線 ❌23-B / Rule 7：以下 plugin 直接 import "
            f"observability helpers 模組：{violations}。請改走 IObservabilityPort 注入。"
        )

    def test_trace_context_is_in_utils_layer(self):
        """trace_context 屬 utils/ 但 Plugin 不可直接 import（純 ContextVar helper）。"""
        trace_ctx = _ROOT / "autoclaude" / "utils" / "trace_context.py"
        assert trace_ctx.exists(), "utils/trace_context.py 必須存在於 utils/ 層"


# ──────────────────────────────────────────────────────────────
# Case 2：IObservabilityPort.emit_counter 介面 contract
# ──────────────────────────────────────────────────────────────
class TestObservabilityPortContract:
    """Case 2：IObservabilityPort 簽名穩定 + NullObservability 為合法 fallback。"""

    def test_observability_port_importable(self):
        from autoclaude.core.ports.observability import (
            IObservabilityPort,
            NullObservability,
        )
        assert IObservabilityPort is not None
        assert NullObservability is not None

    def test_emit_counter_signature(self):
        """emit_counter(name, value=1, tags=None) 簽名必須穩定。"""
        from autoclaude.core.ports.observability import NullObservability

        sig = inspect.signature(NullObservability.emit_counter)
        params = list(sig.parameters)
        # self 之外，必須有 name / value / tags 三參數
        assert params[0] == "self"
        assert "name" in params
        assert "value" in params
        assert "tags" in params

    def test_null_observability_satisfies_protocol(self):
        """NullObservability 必須能合法被當作 IObservabilityPort fallback。"""
        from autoclaude.core.ports.observability import (
            IObservabilityPort,
            NullObservability,
        )
        obs = NullObservability()
        assert isinstance(obs, IObservabilityPort)  # runtime_checkable Protocol
        # 不應 raise
        obs.emit_counter("test_metric", value=1, tags={"kind": "unit"})
        obs.emit_histogram("test_histogram_ms", 12.34)
        obs.record_event("test_event")
        with obs.start_span("test_span") as span:
            span.set_attribute("k", "v")


# ──────────────────────────────────────────────────────────────
# Case 3：propagate_to_subprocess_env 不洩漏 None
# ──────────────────────────────────────────────────────────────
class TestPropagateToSubprocessEnv:
    """Case 3：trace_id 為 None 時不可寫入 env（避免 'None' 字串污染）。"""

    def test_propagate_when_no_trace_id_does_not_set_env(self):
        """無 active trace_id 時，env 中不應出現 AUTOCLAUDE_TRACE_ID key。"""
        from autoclaude.utils.trace_context import propagate_to_subprocess_env

        # 用空 env 起點，避免被外部環境干擾
        env = propagate_to_subprocess_env({})
        assert "AUTOCLAUDE_TRACE_ID" not in env, (
            "trace_id 為 None 時不可注入 env（避免 'None' 字串污染子 process）；"
            f"實際：{env.get('AUTOCLAUDE_TRACE_ID')!r}"
        )

    def test_propagate_with_active_trace_id_sets_env(self):
        """有 active trace_id 時，env 應正確帶入 AUTOCLAUDE_TRACE_ID。"""
        from autoclaude.utils.trace_context import (
            propagate_to_subprocess_env,
            with_trace_id,
        )

        with with_trace_id("abc123def456") as tid:
            env = propagate_to_subprocess_env({})
            assert env.get("AUTOCLAUDE_TRACE_ID") == tid
            assert tid == "abc123def456"

    def test_propagate_preserves_existing_env(self):
        """既有 env key 不可被本 helper 覆寫（除了 AUTOCLAUDE_TRACE_ID 自身）。"""
        from autoclaude.utils.trace_context import (
            propagate_to_subprocess_env,
            with_trace_id,
        )

        with with_trace_id("x" * 12):
            env = propagate_to_subprocess_env({"MY_KEY": "preserved", "PATH": "/x"})
            assert env["MY_KEY"] == "preserved"
            assert env["PATH"] == "/x"
            assert env["AUTOCLAUDE_TRACE_ID"] == "x" * 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
