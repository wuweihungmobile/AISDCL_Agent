"""
感知層單元測試（合併 stream_reader / strip_ansi / PtyWrapper）。

涵蓋項目：
  - NonBlockingStreamReader：背景 thread + Queue 非阻塞讀取
  - strip_ansi：ANSI 控制序列移除
  - PtyWrapper：subprocess 模式的 readline / send / 自動授權
"""
from __future__ import annotations

import io
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

import autoclaude.perception.hotkey_handler as hotkey_handler
from autoclaude.perception.hotkey_handler import HotkeyHandler
from autoclaude.perception.pty_wrapper import (
    PtyWrapper,
    _build_cmd_shim_line,
    _is_cmd_shim,
    _quote_cmd_shim_argv,
    _resolve_command,
)
from autoclaude.perception.stream_reader import NonBlockingStreamReader
from autoclaude.perception.text_utils import strip_ansi

# ──────────────────────────────────────────────
# NonBlockingStreamReader
# ──────────────────────────────────────────────

def _make_reader(lines: list[bytes]) -> NonBlockingStreamReader:
    content = b"".join(lines)
    return NonBlockingStreamReader(io.BytesIO(content))


class TestNonBlockingStreamReader:
    def test_reads_all_lines(self):
        lines = [b"line1\n", b"line2\n", b"line3\n"]
        reader = _make_reader(lines)
        time.sleep(0.05)  # 讓背景 thread 完成讀取

        results = []
        for _ in range(10):
            line = reader.readline(timeout=0.1)
            if line is None:
                break
            if line:
                results.append(line)
        assert results == lines

    def test_returns_empty_on_timeout(self):
        reader = _make_reader([])
        line = reader.readline(timeout=0.05)
        assert line == b"" or line is None

    def test_returns_none_on_eof(self):
        reader = _make_reader([b"only\n"])
        time.sleep(0.05)
        results = []
        while True:
            line = reader.readline(timeout=0.2)
            if line is None:
                break
            if line:
                results.append(line)
        assert b"only\n" in results

    def test_close_is_safe_after_eof(self):
        reader = _make_reader([b"x\n"])
        time.sleep(0.05)
        # drain
        while reader.readline(timeout=0.1) is not None:
            pass
        reader.close(timeout=0.5)  # 應安全完成


# ──────────────────────────────────────────────
# strip_ansi
# ──────────────────────────────────────────────

class TestStripAnsi:
    def test_removes_color_codes(self):
        assert strip_ansi("\x1b[32m[INIT_DONE]\x1b[0m") == "[INIT_DONE]"

    def test_removes_bold(self):
        assert strip_ansi("\x1b[1mHello\x1b[22m") == "Hello"

    def test_removes_cursor_movement(self):
        assert strip_ansi("\x1b[2Jhello") == "hello"

    def test_no_ansi_unchanged(self):
        text = "plain text [KEYWORD]"
        assert strip_ansi(text) == text

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_mixed_ansi_and_text(self):
        result = strip_ansi("\x1b[31mERROR\x1b[0m: something went wrong")
        assert result == "ERROR: something went wrong"

    def test_multiple_ansi_sequences(self):
        result = strip_ansi("\x1b[1m\x1b[32m[DONE]\x1b[0m\x1b[0m")
        assert result == "[DONE]"

    def test_keyword_survives_strip(self):
        for keyword in ["[INIT_DONE]", "[TEST_CREATED]", "[TASK_COMPLETE]", "[PONG]"]:
            assert strip_ansi(f"\x1b[32m{keyword}\x1b[0m") == keyword


# ──────────────────────────────────────────────
# HotkeyHandler.register（macOS Accessibility 授權缺失例外防護，P2 修復回歸）
# ──────────────────────────────────────────────

class TestHotkeyHandlerRegister:
    def setup_method(self):
        # register() 呼叫 _install_listener_excepthook()，會全域性修改
        # threading.excepthook（見 TestListenerExcepthook 說明）；四方複審
        # R2 SD 發現本類別先前缺此 setup/teardown，導致 hook 永久殘留污染
        # 同一 pytest 行程內後續測試。比照 TestListenerExcepthook 做法。
        self._original_hook = threading.excepthook
        hotkey_handler._excepthook_installed = False

    def teardown_method(self):
        threading.excepthook = self._original_hook
        hotkey_handler._excepthook_installed = False

    def test_register_swallows_exception_and_stays_unregistered(self):
        """macOS 無 Accessibility 授權時 keyboard.add_hotkey 可能丟例外；
        register() 須捕捉並保持物件可用，不得讓例外往呼叫端炸穿。"""
        fake_keyboard = MagicMock()
        fake_keyboard.add_hotkey.side_effect = RuntimeError("no accessibility permission")
        with patch("autoclaude.perception.hotkey_handler._KEYBOARD_AVAILABLE", True), \
             patch("autoclaude.perception.hotkey_handler.keyboard", fake_keyboard, create=True):
            handler = HotkeyHandler()
            handler.register()  # 不應拋出
            assert handler._registered is False

    def test_register_succeeds_when_add_hotkey_ok(self):
        fake_keyboard = MagicMock()
        with patch("autoclaude.perception.hotkey_handler._KEYBOARD_AVAILABLE", True), \
             patch("autoclaude.perception.hotkey_handler.keyboard", fake_keyboard, create=True):
            handler = HotkeyHandler()
            handler.register()
            assert handler._registered is True
            fake_keyboard.add_hotkey.assert_called_once()


class TestListenerExcepthook:
    """四方複審 R1 Architect 發現（keyboard==0.13.5 原始碼＋本機重現實證）：
    keyboard.add_hotkey() 把 listen() 丟進背景 daemon thread，macOS 缺
    Accessibility 授權的真實失敗（os.geteuid() 檢查）在該執行緒內非同步拋出，
    包住 add_hotkey() 呼叫本身的 try/except 攔不到。此類測試改驗證
    threading.excepthook 是否正確轉為 warning log、且不吞掉不相關執行緒的例外。
    """

    def setup_method(self):
        # threading.excepthook 為全域可變狀態；模組層 _excepthook_installed
        # 旗標會讓 _install_listener_excepthook() 只裝一次——每個測試前重置，
        # 避免測試間互相污染（前一測試裝好的 hook 殘留到下一測試）。
        self._original_hook = threading.excepthook
        hotkey_handler._excepthook_installed = False

    def teardown_method(self):
        threading.excepthook = self._original_hook
        hotkey_handler._excepthook_installed = False

    def test_async_listener_thread_failure_logs_warning(self, caplog):
        fake_keyboard = MagicMock()
        fake_listener = MagicMock()
        fake_thread = threading.Thread(target=lambda: None)
        fake_listener.listening_thread = fake_thread
        fake_keyboard._listener = fake_listener
        with patch("autoclaude.perception.hotkey_handler._KEYBOARD_AVAILABLE", True), \
             patch("autoclaude.perception.hotkey_handler.keyboard", fake_keyboard, create=True):
            handler = HotkeyHandler()
            handler.register()
            args = threading.ExceptHookArgs(
                (OSError, OSError("Error 13 - Must be run as administrator"), None, fake_thread)
            )
            with caplog.at_level(logging.WARNING, logger="autoclaude.perception"):
                threading.excepthook(args)
        assert any("背景監聽執行緒失敗" in r.message for r in caplog.records)

    def test_unrelated_thread_exception_is_chained_not_swallowed(self):
        """非 keyboard 監聽執行緒的例外必須照舊鏈給前一個 hook，不可被誤吞。"""
        fake_keyboard = MagicMock()
        fake_listener = MagicMock()
        fake_listener.listening_thread = threading.Thread(target=lambda: None)
        fake_keyboard._listener = fake_listener
        previous_hook_calls = []
        threading.excepthook = lambda args: previous_hook_calls.append(args)
        with patch("autoclaude.perception.hotkey_handler._KEYBOARD_AVAILABLE", True), \
             patch("autoclaude.perception.hotkey_handler.keyboard", fake_keyboard, create=True):
            handler = HotkeyHandler()
            handler.register()
            unrelated_thread = threading.Thread(target=lambda: None)
            args = threading.ExceptHookArgs(
                (RuntimeError, RuntimeError("unrelated"), None, unrelated_thread)
            )
            threading.excepthook(args)
        assert previous_hook_calls == [args]


# ──────────────────────────────────────────────
# _resolve_command（Windows npm .cmd/.bat shim 解析，P0 修復回歸）
# ──────────────────────────────────────────────

class TestResolveCommand:
    def test_posix_returns_command_unchanged(self):
        with patch("autoclaude.utils.platform_caps.sys.platform", "darwin"):
            assert _resolve_command("claude") == ["claude"]

    def test_windows_cmd_shim_wrapped_with_cmd_c(self):
        """npm 全域安裝在 Windows 上是 claude.cmd；CreateProcess 無法直接執行批次檔，
        須改經 cmd /c 呼叫，否則 WinError 2（DEF 回歸）。"""
        with patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which",
                   return_value=r"C:\Users\x\AppData\Roaming\npm\claude.cmd"):
            assert _resolve_command("claude") == [
                "cmd", "/c", r"C:\Users\x\AppData\Roaming\npm\claude.cmd"
            ]

    def test_windows_exe_used_directly(self):
        with patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which",
                   return_value=r"C:\tools\claude.exe"):
            assert _resolve_command("claude") == [r"C:\tools\claude.exe"]

    def test_windows_not_found_falls_back_to_original_string(self):
        """找不到時保留原字串，讓錯誤自然浮現（不吞例外、不靜默改行為）。"""
        with patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which", return_value=None):
            assert _resolve_command("claude") == ["claude"]

    def test_windows_subprocess_start_uses_cmd_shim_line(self):
        """_start_subprocess 端到端：解析到 .cmd 時 Popen 收到 _build_cmd_shim_line()
        組出的單一命令列字串（非 list），見 R1 QA 發現的 cmd.exe 多引號 token 回歸。"""
        proc = _make_mock_proc([])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which",
                   return_value=r"C:\npm\claude.cmd"), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen",
                   return_value=proc) as mock_popen:
            pty = _make_pty(command="claude", args=["-p", "hi"])
            pty.start()
            argv = mock_popen.call_args.args[0]
            assert argv == 'cmd /d /s /c "C:\\npm\\claude.cmd -p hi"'
            pty.close()

    def test_windows_cmd_shim_bypasses_wexpect_even_when_available(self):
        """四方複審 R3 回歸（Architect/SD/QA 三方獨立驗證確認的結構性限制）：
        即使 wexpect 可用，.cmd/.bat shim 一律改走 _start_subprocess()，
        wexpect.spawn 完全不應被呼叫。

        根因：wexpect 內部（host.py 啟動 console-reader + __main__.py 轉發）
        用自己天真的 join_args() 逐 token 加引號，兩層轉發後把結果交給
        `cmd /d /s /c`；但 cmd.exe 對 `/C` 之後的內容有非標準 CRT 的特例
        解析規則（見 `cmd /?`）：只有「命令列恰好含兩個引號字元」時才完整
        保留引號，否則一律剝除第一個與最後一個引號字元、放任中間孤兒引號
        殘留。shim_path 與 args 只要同時含空白（如 `C:\\Program Files\\...`
        安裝路徑 + 多字 prompt），remainder 就會超過兩個引號字元，觸發腰斬。
        R2 曾嘗試「不預先加引號、讓 wexpect 逐 token 處理」（比照 DEF-72-001
        既有慣例），但 R3 SD 用官方 cmd 文件＋wexpect 原始碼＋真實 Node.js
        同類 bug 報告三方交叉驗證，證實這依然會腰斬——因為 wexpect 的
        join_args() 逐 token 加引號、不會產生 cmd.exe 這個特例規則所需的
        「單一整體外層引號」結構（唯有 _build_cmd_shim_line 的合併＋外層
        包一層引號技巧才做得到，而該技巧經證實對 wexpect 路徑無效）。
        結論：不透過 wexpect 的 args-list 機制啟動 .cmd/.bat shim 是目前
        唯一確認可行的方案。"""
        proc = _make_mock_proc([])
        fake_wexpect = MagicMock()
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True), \
             patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which",
                   return_value=r"C:\Program Files\npm\claude.cmd"), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen",
                   return_value=proc) as mock_popen:
            pty = _make_pty(command="claude", args=["-p", "fix the bug"])
            pty.start()
            fake_wexpect.spawn.assert_not_called()
            mock_popen.assert_called_once()
            argv = mock_popen.call_args.args[0]
            assert argv == (
                'cmd /d /s /c "'
                + subprocess.list2cmdline([r"C:\Program Files\npm\claude.cmd", "-p", "fix the bug"])
                + '"'
            )
            pty.close()

    def test_windows_non_shim_command_still_uses_wexpect_when_available(self):
        """對照組：非 .cmd/.bat shim（一般 .exe 或裸命令）時，wexpect 可用仍應
        優先使用（PTY 模擬不因本輪 shim 修復而被誤波及）。"""
        fake_wexpect = MagicMock()
        fake_wexpect.spawn.return_value = MagicMock()
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True), \
             patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which",
                   return_value=r"C:\tools\claude.exe"):
            pty = _make_pty(command="claude", args=["-p", "hi"])
            pty.start()
        fake_wexpect.spawn.assert_called_once()
        call = fake_wexpect.spawn.call_args
        assert call.args[0] == r"C:\tools\claude.exe"
        assert call.kwargs["args"] == ["-p", "hi"]

    def test_windows_subprocess_start_handles_path_and_arg_with_spaces(self):
        """R1 QA 發現的核心回歸案例：npm 預設安裝路徑常含空白
        （如 `C:\\Program Files\\...`），且 prompt 幾乎必然含空白。修復前用
        plain argv list 會被 Python list2cmdline 對每個 token 個別加引號，
        觸發 cmd.exe `/C` 舊式剝引號規則（cmd /? 記載：只有『恰好兩個引號
        字元』時才保留引號）把路徑腰斬。此測鎖定：組出的命令列字串本身
        對路徑與 prompt 都正確加了引號，且用 `/S` 停用該舊式捷徑。"""
        proc = _make_mock_proc([])
        shim_path = r"C:\Program Files\npm\claude.cmd"
        prompt = "fix the bug"
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
             patch("autoclaude.perception.pty_wrapper.shutil.which", return_value=shim_path), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen",
                   return_value=proc) as mock_popen:
            pty = _make_pty(command="claude", args=["-p", prompt])
            pty.start()
            argv = mock_popen.call_args.args[0]
            assert isinstance(argv, str)  # 字串型 args：Windows 上繞過 Popen 的二次加引號
            assert argv == f'cmd /d /s /c "{subprocess.list2cmdline([shim_path, "-p", prompt])}"'
            # 路徑與 prompt 各自被正確引號包住，且未被腰斬成兩個獨立 token
            assert '"C:\\Program Files\\npm\\claude.cmd"' in argv
            assert '"fix the bug"' in argv
            pty.close()


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="[WINDOWS-NATIVE-ONLY] cmd shim 孤兒孫行程問題僅存在於 Windows（R44 "
    "DEF-101-348 標籤，供 conftest.py::pytest_terminal_summary 彙整可見度）",
)
class TestCloseKillsCmdShimGrandchild:
    """P1 回歸（真實子行程重現）：.cmd/.bat shim 啟動時，close() 若只 terminate
    外層 cmd.exe，真正執行 CLI 的孫行程會變孤兒繼續跑（見 close() 內註解）。"""

    def test_close_kills_grandchild_spawned_via_cmd_shim(self, tmp_path):
        # 意圖鎖：本 fixture 的 write_text/read_text 刻意用預設編碼——.cmd shim 由
        # cmd.exe 以系統碼頁解讀、marker 由子行程以預設編碼寫入，內容皆 ASCII-only，
        # 勿「好心」補 encoding="utf-8"（R13 DEF-101-121 家族審查裁定維持現狀）。
        marker = tmp_path / "child_pid.txt"
        child_script = tmp_path / "child_sleep.py"
        child_script.write_text(
            "import os, time, pathlib\n"
            f"pathlib.Path(r'{marker}').write_text(str(os.getpid()))\n"
            "time.sleep(30)\n"
        )
        shim = tmp_path / "fake_claude.cmd"
        shim.write_text(f'@echo off\r\npython "{child_script}"\r\n')

        pty = PtyWrapper(command=str(shim), args=[], auth_patterns=[], auth_response="y")
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.shutil.which", return_value=str(shim)):
            pty.start()
        try:
            deadline = time.time() + 10
            while not marker.exists() and time.time() < deadline:
                time.sleep(0.1)
            assert marker.exists(), "孫行程未在時限內啟動（測試環境問題，非本次修復範圍）"
            child_pid = int(marker.read_text().strip())

            pty.close()

            # 修復前：外層 cmd.exe 已死，但孫行程（真正執行 CLI 者）仍存活；
            # 修復後 taskkill /T 應遞迴一併終止整棵行程樹。
            deadline = time.time() + 5
            alive = True
            while time.time() < deadline:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {child_pid}"],
                    capture_output=True,
                )
                stdout = result.stdout.decode(errors="replace")
                alive = str(child_pid) in stdout
                if not alive:
                    break
                time.sleep(0.2)
            assert not alive, f"孫行程 PID {child_pid} 於 close() 後仍存活（P1 缺陷回歸）"
        finally:
            # 測試安全網：即使斷言失敗也不留下背景行程
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pty._proc.pid)],
                capture_output=True,
            )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process-group 孤兒防護僅適用於 POSIX")
class TestCloseKillsPosixGrandchild:
    """R16 P2（Mac/Windows 相容性掃描）：POSIX 側 close() 修復前只呼叫
    self._proc.terminate()（只殺直接子行程 sh），若 sh 再背景 fork 出孫行程
    （如底層 CLI 經 shell wrapper 啟動），孫行程會變孤兒不被回收——跟 Windows
    側已修的 cmd shim 孤兒孫行程問題（見 TestCloseKillsCmdShimGrandchild）同一類。
    修復後 _start_subprocess() 用 start_new_session=True 令直接子行程獨立成新
    process group，close() 改用 os.killpg() 連同孫行程一併終止。"""

    def test_close_kills_grandchild_spawned_via_shell_background_job(self, tmp_path):
        marker = tmp_path / "grandchild_pid.txt"
        # sh 直接子行程背景啟動 sleep 30（= 孫行程，因由 sh fork 而非 Python），
        # 寫入 $!（背景工作 PID）後 wait 阻塞，模擬 shell wrapper fork 出真正工作
        # 行程的情境。
        script = f"sleep 30 & echo $! > '{marker}'; wait"
        pty = PtyWrapper(command="sh", args=["-c", script], auth_patterns=[], auth_response="y")
        pty.start()
        try:
            deadline = time.time() + 10
            while not marker.exists() and time.time() < deadline:
                time.sleep(0.1)
            assert marker.exists(), "孫行程未在時限內啟動（測試環境問題，非本次修復範圍）"
            grandchild_pid = int(marker.read_text().strip())
            assert _pid_alive(grandchild_pid), "孫行程應已啟動存活"

            pty.close()

            deadline = time.time() + 5
            alive = _pid_alive(grandchild_pid)
            while alive and time.time() < deadline:
                time.sleep(0.1)
                alive = _pid_alive(grandchild_pid)
            assert not alive, f"孫行程 PID {grandchild_pid} 於 close() 後仍存活（P2 缺陷回歸）"
        finally:
            # 測試安全網：即使斷言失敗也不留下背景行程
            try:
                os.kill(grandchild_pid, signal.SIGKILL)
            except (NameError, OSError):
                pass


# ──────────────────────────────────────────────
# _build_cmd_shim_line / _is_cmd_shim（純字串邏輯，R1 QA 回歸）
# ──────────────────────────────────────────────

class TestBuildCmdShimLine:
    def test_is_cmd_shim_true_for_resolved_shim(self):
        assert _is_cmd_shim(["cmd", "/c", r"C:\npm\claude.cmd"]) is True

    def test_is_cmd_shim_false_for_plain_command(self):
        assert _is_cmd_shim(["claude"]) is False
        assert _is_cmd_shim([r"C:\tools\claude.exe"]) is False

    def test_build_cmd_shim_line_wraps_with_slash_s_and_outer_quotes(self):
        """`/S` 讓 cmd.exe 停用僅在『恰好兩個引號字元』時才保留引號的舊式
        剝引號捷徑（見 _quote_cmd_shim_argv docstring），改用一般解析。"""
        line = _build_cmd_shim_line(r"C:\Program Files\npm\claude.cmd", ["-p", "fix the bug"])
        assert line.startswith('cmd /d /s /c "')
        assert line.endswith('"')
        assert line == (
            'cmd /d /s /c "'
            + subprocess.list2cmdline([r"C:\Program Files\npm\claude.cmd", "-p", "fix the bug"])
            + '"'
        )

    def test_build_cmd_shim_line_no_args(self):
        line = _build_cmd_shim_line(r"C:\npm\claude.cmd", [])
        assert line == 'cmd /d /s /c "C:\\npm\\claude.cmd"'

    def test_quote_cmd_shim_argv_excludes_cmd_prefix(self):
        """_quote_cmd_shim_argv 只回傳 list2cmdline 結果，不含 cmd /d /s /c
        前綴——這是 _start_wexpect 之前重複套用 _build_cmd_shim_line 導致
        前綴出現兩次那個 bug 的直接回歸鎖。"""
        result = _quote_cmd_shim_argv(r"C:\npm\claude.cmd", ["-p", "hi"])
        assert result == r"C:\npm\claude.cmd -p hi"
        assert "cmd /d /s /c" not in result


# ──────────────────────────────────────────────
# PtyWrapper（subprocess 模式）
# ──────────────────────────────────────────────

def _make_mock_proc(stdout_lines: list[bytes]):
    proc = MagicMock()
    proc.poll.return_value = None
    proc.stdin = MagicMock()
    proc.stdin.closed = False
    proc.stdout = BytesIO(b"".join(stdout_lines))
    return proc


def _make_pty(**kwargs) -> PtyWrapper:
    defaults = dict(
        command="python", args=["-u", "dummy.py"],
        auth_patterns=[], auth_response="y",
    )
    defaults.update(kwargs)
    return PtyWrapper(**defaults)


class _FakeWexpectChild:
    """精準可控的 fake wexpect child（DEF-73-001 回歸用）。

    刻意**不提供** logfile_read callback 行為——複刻 wexpect 4.0.0 實況（callback 於 expect()
    不觸發，零成本探針實證捕獲 0 字元）。每呼叫 expect 吐一行設於 self.after、index=0；行盡回 EOF
    index=2。據此驗證 raw 擷取必由 readline 顯式寫入、不依賴 callback。
    """

    def __init__(self, lines, eof_tail=None, timeout_rounds=0, raise_on_expect=None):
        self._lines = list(lines)
        self.after = None
        self.before = None
        self._eof_tail = eof_tail
        # 前 N 次 expect 回 index==1（TIMEOUT），不 pop line（improving_74 W-74-1）
        self._timeout_rounds = timeout_rounds
        self.sent = []  # 記錄 sendline 自動回應內容（improving_74 W-74-2）
        # expect 拋此例外（improving_74 W-74-4 except 分支）
        self._raise_on_expect = raise_on_expect

    def expect(self, patterns, timeout=None):
        if self._raise_on_expect is not None:
            raise self._raise_on_expect
        if self._timeout_rounds > 0:
            self._timeout_rounds -= 1
            return 1  # 對應 patterns[1] == wexpect.TIMEOUT（不碰 after/before、不消耗 line）
        if self._lines:
            self.after = self._lines.pop(0)
            self.before = ""
            return 0
        self.before = self._eof_tail or ""  # EOF 前未換行殘留（模擬 wexpect child.before）
        return 2  # 對應 patterns[2] == wexpect.EOF

    def sendline(self, text):
        self.sent.append(text)

    def close(self, force=False):
        pass

    def isalive(self):
        return bool(self._lines)


class TestPtyWrapper:
    def test_readline_returns_decoded_line(self):
        proc = _make_mock_proc([b"hello world\n"])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty()
            pty.start()
            time.sleep(0.1)
            line = pty.readline(timeout=1.0)
            assert line is not None
            assert "hello world" in line
            pty.close()

    def test_readline_returns_none_on_eof(self):
        proc = _make_mock_proc([])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty()
            pty.start()
            time.sleep(0.1)
            result = None
            for _ in range(20):
                result = pty.readline(timeout=0.1)
                if result is None:
                    break
            assert result is None
            pty.close()

    def test_wexpect_spawn_passes_args_as_list_not_shell_joined(self):
        """DEF-72-001 回歸：複雜 prompt（反引號/換行/分號）須以 args=list 傳 wexpect.spawn，
        嚴禁 ' '.join 成單一 shell 字串。

        Rule 9 意圖：shell-join 會讓反引號被當命令替換、換行斷句 → claude 收到殘缺指令、
        raw log 0 bytes（pty-vs-sdk 真跑揭露的執行器層真實缺陷）。此測直接守 spawn 呼叫形態：
        command 為第一參數、完整 prompt 以 args list 原樣傳遞，且 command 字串不得吞進 prompt。
        wexpect 為 Windows-only（CI 在 Linux 無此模組）→ create=True 跨平台 patch。
        """
        complex_prompt = "請建立 `t.py`; assert add(2,3)==5\n完成後輸出 [TEST_READY]"
        fake_wexpect = MagicMock()
        fake_wexpect.spawn.return_value = MagicMock()
        # Mac/Windows 四方複審實機發現：命令是否解析成「原樣字串」還是「已解析
        # 絕對路徑」取決於本機 PATH 上是否真的裝了 claude CLI（shutil.which 結果），
        # 讓斷言值隨開發機器現況飄動——本測真正要守的是「args 以 list 傳、不被
        # shell-join 成單一字串」，command 本身是否已被解析為絕對路徑無關，故明確
        # patch shutil.which 回傳 None，固定為「找不到→原樣回傳 command」分支。
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True), \
             patch("autoclaude.perception.pty_wrapper.shutil.which", return_value=None):
            pty = _make_pty(command="claude", args=["-p", complex_prompt])
            pty.start()
        call = fake_wexpect.spawn.call_args
        assert call.args[0] == "claude"               # command 為第一參數（非長字串）
        assert call.kwargs["args"] == ["-p", complex_prompt]  # prompt 原樣以 list 傳
        assert complex_prompt not in call.args[0]      # 防回歸：未被 join 進 command 字串

    def test_wexpect_raw_log_captured_explicitly(self, tmp_path):
        """DEF-73-001 回歸：wexpect 路徑讀到行時須**顯式**寫 raw_logger。

        Rule 9 意圖：improving_72 真跑觀測 pty raw log 0 bytes，根因＝原碼僅靠
        child.logfile_read callback 擷取，而 wexpect 4.0.0 該 callback 於 expect() 不觸發。
        若退回「只靠 callback」此測必紅（fake child 永不呼叫 callback → raw 檔為空）。
        """
        raw_path = tmp_path / "raw.log"
        fake_child = _FakeWexpectChild(["CLAUDE_OUT_LINE\r\n"])
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty(raw_log_path=raw_path)
            pty.start()
            assert pty.readline(timeout=0.1) == "CLAUDE_OUT_LINE\r\n"
            pty.close()
        assert raw_path.read_bytes() == b"CLAUDE_OUT_LINE\r\n"

    def test_wexpect_raw_log_accumulates_and_no_logfile_read_dependency(self, tmp_path):
        """DEF-73-001 回歸：多行跨 readline 累積；且 start() 不再掛載 logfile_read callback。

        `assert not hasattr(fake_child, "logfile_read")` 守住死碼移除——若有人重新引入
        `self._child.logfile_read = ...` 此測立即紅，固化「不依賴從不觸發的 callback」決策。
        """
        raw_path = tmp_path / "raw.log"
        fake_child = _FakeWexpectChild(["L1\r\n", "L2\r\n"])
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty(raw_log_path=raw_path)
            pty.start()
            assert not hasattr(fake_child, "logfile_read")
            assert pty.readline(timeout=0.1) == "L1\r\n"
            assert pty.readline(timeout=0.1) == "L2\r\n"
            assert pty.readline(timeout=0.1) is None
            pty.close()
        assert raw_path.read_bytes() == b"L1\r\nL2\r\n"

    def test_wexpect_raw_log_captures_eof_residual_without_newline(self, tmp_path):
        """DEF-73-001 回歸（audit_73 SA-SD 發現）：EOF 前未換行尾段（child.before）須擷取。

        Rule 9 意圖：子程序最後吐一段不帶換行的尾段時，wexpect 放進 child.before、index==2
        分支若直接 return None 會讓尾段從 raw log 遺失，與 subprocess 路徑（會回傳 EOF 前最後
        chunk）不對稱。本測守「EOF 殘留也擷取」，使兩後端 raw 擷取真正一致。
        """
        raw_path = tmp_path / "raw.log"
        fake_child = _FakeWexpectChild(["L1\r\n"], eof_tail="TAIL_NO_NL")
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty(raw_log_path=raw_path)
            pty.start()
            assert pty.readline(timeout=0.1) == "L1\r\n"
            assert pty.readline(timeout=0.1) is None  # EOF，擷取殘留尾段
            pty.close()
        assert raw_path.read_bytes() == b"L1\r\nTAIL_NO_NL"

    def test_wexpect_readline_timeout_returns_empty_not_none(self, tmp_path):
        """improving_74 R-74-1：wexpect readline TIMEOUT（index==1）須回 '' 非 None、
        不寫 raw、不終止串流。

        Rule 9 意圖：TIMEOUT 是「本輪暫無輸出」非「結束」。若退回 return None，上層讀取迴圈
        會誤判 EOF 提前終止串流 → TIMEOUT 之後真正吐的輸出行永遠讀不到。本測先令 expect 回
        TIMEOUT 確認得 ''，再確認 TIMEOUT 後仍能讀到後續行（守「不終止串流」），且 raw log
        不含任何空寫入（守「TIMEOUT 不寫 raw」）。wexpect 為 Windows-only → create=True patch。
        """
        raw_path = tmp_path / "raw.log"
        fake_child = _FakeWexpectChild(["AFTER_TIMEOUT\r\n"], timeout_rounds=1)
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty(raw_log_path=raw_path)
            pty.start()
            assert pty.readline(timeout=0.1) == ""                   # TIMEOUT → '' 非 None
            assert pty.readline(timeout=0.1) == "AFTER_TIMEOUT\r\n"   # 串流未被終止
            pty.close()
        assert raw_path.read_bytes() == b"AFTER_TIMEOUT\r\n"          # TIMEOUT 未寫空 raw

    def test_wexpect_auto_respond_via_sendline_on_pattern_match(self):
        """improving_74 R-74-2：wexpect 模式偵測授權提示須經 child.sendline 自動回應。

        Rule 9 意圖：既有三個 _auto_respond 測試全 patch _WEXPECT_AVAILABLE=False，只驗
        subprocess 的 proc.stdin.write 分支；wexpect 模式 send()→child.sendline 分支零覆蓋。
        若該分支壞掉（如 send() 漏掉 wexpect 分支），既有測試抓不到。本測直接守 child.sendline
        被以 auth_response 呼叫。
        """
        fake_child = _FakeWexpectChild(["This action requires authorization. Proceed? (Y/n)\r\n"])
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty(auth_patterns=[r"Proceed\?\s*\(Y/n\)"], auth_response="y")
            pty.start()
            pty.readline(timeout=0.1)
            pty.close()
        assert fake_child.sent == ["y"]   # 經 wexpect child.sendline 回應，非 subprocess stdin

    def test_wexpect_no_auto_respond_on_normal_line(self):
        """improving_74 R-74-3：wexpect 模式正常行不誤觸發自動回應（對稱 subprocess 的
        test_no_auth_on_normal_line）。pattern 不匹配 → child.sendline 不被呼叫。
        """
        fake_child = _FakeWexpectChild(["[INIT_DONE]\r\n"])
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty(auth_patterns=[r"Proceed\?\s*\(Y/n\)"], auth_response="y")
            pty.start()
            pty.readline(timeout=0.1)
            pty.close()
        assert fake_child.sent == []      # 正常行不誤觸發

    def test_wexpect_readline_returns_empty_on_expect_exception(self):
        """improving_74 R-74-6（audit_74 SA-SD 鏡發現）：_readline_wexpect 的 expect 拋例外時
        須由 except 接住、回 '' 不崩潰（fail-soft），與既有四出口一致。

        Rule 9 意圖：wexpect expect() 偶發拋例外（如底層 pipe 異常）不應讓讀取迴圈整個炸掉；
        production 以 `except Exception: logger.debug(...); return ""` 吞錯回 ''。此分支本輪前
        零覆蓋。若退回 `raise`（或回 None），本測轉紅。
        """
        fake_child = _FakeWexpectChild(
            [], raise_on_expect=RuntimeError("simulated wexpect failure")
        )
        fake_wexpect = MagicMock()
        fake_wexpect.TIMEOUT = object()
        fake_wexpect.EOF = object()
        fake_wexpect.spawn.return_value = fake_child
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
            pty = _make_pty()
            pty.start()
            assert pty.readline(timeout=0.1) == ""   # 例外被 except 接住、回 '' 不崩潰
            pty.close()

    def test_send_writes_to_stdin(self):
        proc = _make_mock_proc([])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty()
            pty.start()
            pty.send("step1")
            proc.stdin.write.assert_called_once_with(b"step1\n")
            proc.stdin.flush.assert_called_once()
            pty.close()

    def test_auth_auto_respond_on_pattern_match(self):
        auth_line = b"This action requires authorization. Proceed? (Y/n)\n"
        proc = _make_mock_proc([auth_line])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty(auth_patterns=[r"Proceed\?\s*\(Y/n\)"], auth_response="y")
            pty.start()
            time.sleep(0.1)
            pty.readline(timeout=1.0)
            # R69：取 print/write 的**實際引數**，不是 `mock.call` 物件的 repr——
            # repr 會轉義反斜線與換行，令任何路徑／多行斷言在 Windows 假紅。
            calls = [str(a) for c in proc.stdin.write.call_args_list for a in c.args]
            assert any("y" in c for c in calls)
            pty.close()

    def test_no_auth_on_normal_line(self):
        normal_line = b"[INIT_DONE]\n"
        proc = _make_mock_proc([normal_line])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty(auth_patterns=[r"Proceed\?\s*\(Y/n\)"])
            pty.start()
            time.sleep(0.1)
            pty.readline(timeout=1.0)
            proc.stdin.write.assert_not_called()
            pty.close()

    def test_auth_auto_respond_strips_ansi(self):
        """ANSI 包裹的授權提示也應正確觸發自動回應。"""
        auth_line = b"\x1b[32mThis action requires authorization. Proceed? (Y/n)\x1b[0m\n"
        proc = _make_mock_proc([auth_line])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty(auth_patterns=[r"Proceed\?\s*\(Y/n\)"], auth_response="y")
            pty.start()
            time.sleep(0.1)
            pty.readline(timeout=1.0)
            # R69：取 print/write 的**實際引數**，不是 `mock.call` 物件的 repr——
            # repr 會轉義反斜線與換行，令任何路徑／多行斷言在 Windows 假紅。
            calls = [str(a) for c in proc.stdin.write.call_args_list for a in c.args]
            assert any("y" in c for c in calls)
            pty.close()

    def test_is_alive_true_when_running(self):
        proc = _make_mock_proc([])
        proc.poll.return_value = None
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty()
            pty.start()
            assert pty.is_alive is True
            pty.close()

    def test_is_alive_false_when_ended(self):
        proc = _make_mock_proc([])
        proc.poll.return_value = 0
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty()
            pty.start()
            assert pty.is_alive is False
            pty.close()

    def test_close_terminates_process(self):
        proc = _make_mock_proc([])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty()
            pty.start()
            pty.close()
            proc.terminate.assert_called_once()

    def test_custom_auth_pattern(self):
        custom_line = b"CUSTOM_AUTH_REQUEST: do you agree?\n"
        proc = _make_mock_proc([custom_line])
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", False), \
             patch("autoclaude.perception.pty_wrapper.subprocess.Popen", return_value=proc):
            pty = _make_pty(auth_patterns=[r"CUSTOM_AUTH_REQUEST"], auth_response="yes")
            pty.start()
            time.sleep(0.1)
            pty.readline(timeout=1.0)
            # R69：取 print/write 的**實際引數**，不是 `mock.call` 物件的 repr——
            # repr 會轉義反斜線與換行，令任何路徑／多行斷言在 Windows 假紅。
            calls = [str(a) for c in proc.stdin.write.call_args_list for a in c.args]
            assert any("yes" in c for c in calls)
            pty.close()
