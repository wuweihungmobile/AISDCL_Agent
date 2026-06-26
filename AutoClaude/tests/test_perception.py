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
        self._timeout_rounds = timeout_rounds  # 前 N 次 expect 回 index==1（TIMEOUT），不 pop line（improving_74 W-74-1）
        self.sent = []                         # 記錄 sendline 自動回應內容（improving_74 W-74-2）
        self._raise_on_expect = raise_on_expect  # expect 拋此例外（improving_74 W-74-4 except 分支）

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
        with patch("autoclaude.perception.pty_wrapper._WEXPECT_AVAILABLE", True), \
             patch("autoclaude.perception.pty_wrapper.wexpect", fake_wexpect, create=True):
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
        fake_child = _FakeWexpectChild([], raise_on_expect=RuntimeError("simulated wexpect failure"))
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
