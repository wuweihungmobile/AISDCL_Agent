"""prompt_dispatcher.py::execute_prompt_impl 的 log_path 淨化回歸鎖
（R43 SD 一審，DEF-101-352 同構第二例）。

背景：`AutoClaude/autoclaude/infra/adapters/pty_executor.py::execute()` 本輪已修復
`label`（源自 `PlaybookTask.step_id`，YAML 可控字串）未淨化即組檔名導致路徑穿越
的漏洞。SD 一審對抗式驗證抓到 `prompt_dispatcher.py::execute_prompt_impl` 的
`step_label`（`steps_orchestrator/_impl.py::207` 組 `f"{task.step_id}_attempt{n}"`
傳入，同屬 YAML 可控字串）存在完全相同的漏洞類別，且是目前實際生產呼叫鏈
（`PlaybookRunner._execute_prompt` → `execute_prompt_impl`）——本檔鎖住該修復。
R58 增補（`TestPtyStartFailureClosesLog`）：`pty.start()` 原本寫在 `try:` **之外**，
但 `PtyWrapper.__init__` 在那之前就已開啟 `RawStreamLogger` 的檔案 handle——
`start()` 拋例外時 `finally: pty.close()` 不會被執行，沒有任何人顯式釋放它。

後果的精確範圍（本輪實測訂正，勿改寫回「洩漏到行程結束」）：呼叫端一旦丟棄例外，
CPython refcount 就會回收 file 物件並關檔；但只要還有參照指向出錯的 frame
（正在執行的 except 區塊、被留存的 traceback、本測試用的 `pytest.raises`），handle
就還開著。Windows 此時不允許刪除／改名該檔（實測 PermissionError WinError 32），
POSIX 則照樣成功 → 單邊平台失效。另有與 GC 無關的一段：`close()` 是唯一會收掉子
行程樹的地方，Popen 已成功而後續才拋錯時，子行程沒人終止（行程不會被 GC 回收）。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autoclaude.perception.pty_wrapper import PtyWrapper
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


class _ExplodingStartPty(PtyWrapper):
    """真的 `PtyWrapper`（＝真的會開檔），只把 `start()` 換成拋例外。

    刻意不用 MagicMock：本測試要驗的正是「`__init__` 已開啟的真實檔案 handle 有沒有
    被關掉」，mock 不開檔就沒有 handle 可洩漏，測試會恆綠而毫無鑑別力。拋
    FileNotFoundError 是對齊真實最常見成因——`cfg.claude.command` 指到不存在的
    執行檔時 `_start_subprocess()` 的 Popen 就是拋這個。
    """

    instances: list[_ExplodingStartPty] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self).instances.append(self)

    def start(self) -> None:
        raise FileNotFoundError("模擬 claude CLI 不存在：Popen 在 start() 內拋錯")


class TestPtyStartFailureClosesLog:
    """`start()` 拋例外時，`PtyWrapper.__init__` 已開啟的 raw log handle 必須被關閉。

    載具為何用 `pytest.raises` 包住（不是可有可無的寫法）：它會在整個 with 區塊後
    持續持有 ExceptionInfo → traceback → frame → `pty`，等同於「呼叫端還在處理例外」
    的真實情境；若改成 `try/except: pass` 立刻丟棄例外，CPython refcount 會順手把檔案
    關掉，測試就變成恆綠、對本缺陷零鑑別力（本輪實測踩過，記錄以免後人「簡化」掉）。
    """

    def test_raw_log_handle_released_when_start_raises(self, tmp_path: Path):
        _ExplodingStartPty.instances.clear()
        runner = _make_runner(dry_run=False)
        runner._cfg.log_dir = str(tmp_path)

        with patch(
            "autoclaude.execution.playbook_runner.PtyWrapper", _ExplodingStartPty
        ), pytest.raises(FileNotFoundError):
            # 例外必須照舊往外拋（修法只補關檔，不吞例外）——若哪天被吞掉，
            # pytest.raises 會轉紅。
            runner._execute_prompt(
                "p", maintain_context=False, timeout=10, step_label="startfail",
            )

        assert len(_ExplodingStartPty.instances) == 1, "應真的建構了一個 PtyWrapper（含開檔）"
        log_path = tmp_path / "playbook_startfail.log"
        assert log_path.is_file(), "RawStreamLogger 應已實際建檔（否則本測試無鑑別力）"

        # 斷言一（全平台皆具鑑別力）：檔案物件本身已關閉。
        raw_logger = _ExplodingStartPty.instances[0]._raw_logger
        assert raw_logger is not None
        assert raw_logger._file.closed, (
            "start() 拋例外後 raw log 的檔案 handle 仍開著 → pty.close() 沒被呼叫"
            "（`start()` 是否又被移回 try: 之外？）"
        )

        # 斷言二（Windows 上才具鑑別力，是真實危害的直接證明）：handle 還開著時
        # Windows 不允許刪除該檔（PermissionError／WinError 32），POSIX 則照樣成功
        # ——故此斷言在 macOS/Linux 上恆綠、只在 Windows 上抓得到洩漏，刻意保留兩條
        # 斷言而非只留一條。
        log_path.unlink()
        assert not log_path.exists()
