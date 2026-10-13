"""ARCH-03：`--max-turns` 是 Claude CLI 的原生旗標（只是不列在 `--help`）——回合數軸的預算上限。

驗證意圖（Rule 9）：PRD §4.4.3 的 agent 硬性預算曾以「help 查無 `--max-turns`」為由退役，而
help 不列 ≠ 旗標不存在（`claude -p --max-turns 3 </dev/null` 回的是 `Input must be provided`，
未知旗標回 `unknown option`）。`claude.max_turns_per_step` 把這一軸接進兩條 argv 組裝路徑；本檔守：
  1. 預設 None ⇒ 兩條路徑的 argv 與修前逐位元相同（零行為變更）；
  2. 設了就在兩條路徑都出現 `--max-turns <N>`，且 `-p <prompt>` 仍在尾端；
  3. 邊界（≥1）與出廠範本有說明；兩條路徑共用同一個家（`ClaudeConfig.base_args`），不各抄一份。
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from autoclaude.infra.adapters import PtyExecutor
from autoclaude.utils.config import ClaudeConfig, LoopConfig, load_config
from tests.test_playbook_runner import _make_runner

REPO = Path(__file__).resolve().parent.parent


def _pty_args(cfg: ClaudeConfig, **kw) -> list[str]:
    with patch("autoclaude.infra.adapters.pty_executor.PtyWrapper") as wrapper:
        wrapper.return_value = MagicMock(is_alive=False, readline=MagicMock(return_value=None))
        PtyExecutor(cfg, LoopConfig()).execute("PROMPT", timeout=5, label="t", **kw)
    return list(wrapper.call_args.kwargs["args"])


def _dispatcher_args(max_turns) -> list[str]:
    runner = _make_runner(dry_run=False)
    runner._cfg.claude.max_turns_per_step = max_turns
    with patch("autoclaude.execution.playbook_runner.PtyWrapper") as wrapper:
        wrapper.return_value = MagicMock(is_alive=False, readline=MagicMock(return_value=None))
        runner._execute_prompt("PROMPT", maintain_context=False, timeout=5, step_label="s")
    return list(wrapper.call_args.kwargs["args"])


class TestTheConfigField:
    def test_the_default_adds_nothing(self):
        assert ClaudeConfig().max_turns_per_step is None
        assert ClaudeConfig().base_args() == [], "預設不得多送任何旗標（否則出廠行為被改）"

    def test_a_set_value_appends_the_flag_pair_after_extra_args(self):
        cfg = ClaudeConfig(extra_args=["--model", "haiku"], max_turns_per_step=7)
        assert cfg.base_args() == ["--model", "haiku", "--max-turns", "7"]

    @pytest.mark.parametrize("bad", [0, -3])
    def test_a_non_positive_limit_is_rejected_at_load_time(self, bad):
        with pytest.raises(ValidationError):
            ClaudeConfig(max_turns_per_step=bad)

    def test_the_shipped_example_documents_the_key_and_still_loads(self):
        example = REPO / "config.yaml.example"
        assert "max_turns_per_step" in example.read_text(encoding="utf-8")
        assert load_config(str(example)).claude.max_turns_per_step is None


class TestBothArgvBuildersHonourIt:
    def test_the_pty_executor_unset_is_unchanged_and_set_adds_the_pair(self):
        base = _pty_args(ClaudeConfig())
        assert "--max-turns" not in base and base[-2:] == ["-p", "PROMPT"]
        got = _pty_args(ClaudeConfig(max_turns_per_step=5))
        assert got[got.index("--max-turns") + 1] == "5" and got[-2:] == ["-p", "PROMPT"]

    def test_the_prompt_dispatcher_unset_is_unchanged_and_set_adds_the_pair(self):
        base = _dispatcher_args(None)
        assert "--max-turns" not in base and base[-2:] == ["-p", "PROMPT"]
        got = _dispatcher_args(4)
        assert got[got.index("--max-turns") + 1] == "4" and got[-2:] == ["-p", "PROMPT"]

    def test_neither_builder_keeps_its_own_copy_of_the_flag_logic(self):
        """兩條路徑只准呼叫 `base_args()`：各自再寫一份 `--max-turns` 字面＝同一份知識兩個家。"""
        for rel in ("autoclaude/infra/adapters/pty_executor.py",
                    "autoclaude/execution/prompt_dispatcher.py"):
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
            literals = [n.value for n in ast.walk(tree)
                        if isinstance(n, ast.Constant) and n.value == "--max-turns"]
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                     and n.attr == "base_args"]
            assert literals == [] and calls, f"{rel}：應只經由 ClaudeConfig.base_args()"
