"""prompt_dispatcher.py::execute_prompt_impl 的 log_path 淨化回歸鎖
（R43 SD 一審，DEF-101-352 同構第二例）。

背景：`AutoClaude/autoclaude/infra/adapters/pty_executor.py::execute()` 本輪已修復
`label`（源自 `PlaybookTask.step_id`，YAML 可控字串）未淨化即組檔名導致路徑穿越
的漏洞。SD 一審對抗式驗證抓到 `prompt_dispatcher.py::execute_prompt_impl` 的
`step_label`（`steps_orchestrator/_impl.py::207` 組 `f"{task.step_id}_attempt{n}"`
傳入，同屬 YAML 可控字串）存在完全相同的漏洞類別，且是目前實際生產呼叫鏈
（`PlaybookRunner._execute_prompt` → `execute_prompt_impl`）——本檔鎖住該修復。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.test_playbook_runner import _make_runner


class TestExecutePromptImplLabelSanitization:
    @patch("autoclaude.execution.playbook_runner.PtyWrapper")
    def test_path_traversal_step_label_does_not_escape_log_dir(self, mock_pty_class):
        pty = MagicMock()
        pty.is_alive = False
        pty.readline.return_value = None
        mock_pty_class.return_value = pty

        runner = _make_runner(dry_run=False)
        runner._execute_prompt(
            "p", maintain_context=False, timeout=10, step_label="../../../evil_attempt1",
        )

        raw_log_path = mock_pty_class.call_args.kwargs["raw_log_path"]
        assert ".." not in raw_log_path.parts

    @patch("autoclaude.execution.playbook_runner.PtyWrapper")
    def test_reserved_device_name_step_label_not_written_bare(self, mock_pty_class):
        pty = MagicMock()
        pty.is_alive = False
        pty.readline.return_value = None
        mock_pty_class.return_value = pty

        runner = _make_runner(dry_run=False)
        runner._execute_prompt(
            "p", maintain_context=False, timeout=10, step_label="CON",
        )

        raw_log_path = mock_pty_class.call_args.kwargs["raw_log_path"]
        assert raw_log_path.stem != "playbook_CON"

    @patch("autoclaude.execution.playbook_runner.PtyWrapper")
    def test_empty_step_label_falls_back_to_untitled(self, mock_pty_class):
        pty = MagicMock()
        pty.is_alive = False
        pty.readline.return_value = None
        mock_pty_class.return_value = pty

        runner = _make_runner(dry_run=False)
        runner._execute_prompt(
            "p", maintain_context=False, timeout=10, step_label="",
        )

        raw_log_path = mock_pty_class.call_args.kwargs["raw_log_path"]
        assert raw_log_path.name == "playbook_untitled.log"
