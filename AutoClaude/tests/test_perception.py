"""
感知層單元測試（合併 stream_reader / strip_ansi / PtyWrapper）。

涵蓋項目：
  - NonBlockingStreamReader：背景 thread + Queue 非阻塞讀取
  - strip_ansi：ANSI 控制序列移除
  - PtyWrapper：subprocess 模式的 readline / send / 自動授權
"""
from __future__ import annotations

import io
import time
from io import BytesIO
from unittest.mock import MagicMock, patch

from autoclaude.perception.stream_reader import NonBlockingStreamReader
from autoclaude.perception.text_utils import strip_ansi
from autoclaude.perception.pty_wrapper import PtyWrapper


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
            calls = [str(c) for c in proc.stdin.write.call_args_list]
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
            calls = [str(c) for c in proc.stdin.write.call_args_list]
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
            calls = [str(c) for c in proc.stdin.write.call_args_list]
            assert any("yes" in c for c in calls)
            pty.close()
