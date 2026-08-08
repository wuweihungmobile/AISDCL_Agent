"""R68 回歸鎖：perception 層的兩筆平台誠實性/韌性缺陷。

[A] HotkeyHandler.register()（macOS，真機取證）
    keyboard.add_hotkey() 把 listen() 丟進背景 daemon thread 後立即返回；macOS
    非 root 時 `_darwinkeyboard.listen()` 首行 `os.geteuid() != 0` 即 raise
    OSError 13（**與 TCC「輔助使用」授權無關**，授權了也一樣失敗；是 10/10
    確定性失敗，不是 race）。修復前 register() 在該執行緒已死的情況下仍印
    「已註冊」並把 _registered 設 True ＝ 靜默失效。

[B] _build_cmd_shim_line 長度守門（Windows，靜態分析）
    .cmd/.bat shim 路徑把整個 prompt 組進單一 `cmd /d /s /c "…"` 字串，撞
    cmd.exe 8191 字元硬上限；POSIX 側走 argv（本機 ARG_MAX 實測 1048576）無此
    界線。修復前全樹零長度守門，超限只會拿到難以歸因的
    "The input line is too long."。⚠️ 本輪無 Windows 真機，8191 為文件層知識，
    未取得機器證據——本鎖驗的是「守門存在且會 fail-loud」，不是 cmd.exe 行為。
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

from autoclaude.perception import hotkey_handler
from autoclaude.perception import pty_wrapper as pw
from autoclaude.perception.hotkey_handler import HotkeyHandler
from autoclaude.perception.pty_wrapper import (
    _CMD_LINE_MAX_CHARS,
    CmdLineTooLongError,
    PtyWrapper,
    _build_cmd_shim_line,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────
# [A] Hotkey：背景執行緒已死 → 不得宣稱已註冊
# ──────────────────────────────────────────────

class TestHotkeyRegisterHonesty:
    def setup_method(self):
        self._original_hook = threading.excepthook
        hotkey_handler._excepthook_installed = False

    def teardown_method(self):
        threading.excepthook = self._original_hook
        hotkey_handler._excepthook_installed = False

    def test_dead_listener_thread_must_not_report_registered(self, caplog):
        fake_keyboard = MagicMock()
        dead_thread = threading.Thread(target=lambda: None)
        dead_thread.start()
        dead_thread.join()
        assert dead_thread.is_alive() is False
        fake_keyboard._listener.listening_thread = dead_thread
        with patch.object(hotkey_handler, "_KEYBOARD_AVAILABLE", True), \
             patch.object(hotkey_handler, "keyboard", fake_keyboard, create=True), \
             caplog.at_level("INFO", logger="autoclaude.perception"):
            handler = HotkeyHandler()
            handler.register()
        assert handler._registered is False, (
            "背景監聽執行緒已死卻回報已註冊 ＝ 靜默失效（R68 缺陷復發）"
        )
        messages = [r.getMessage() for r in caplog.records]
        assert not any("已註冊" in m for m in messages), f"不得宣稱已註冊：{messages}"
        assert any("不可用" in m for m in messages), f"必須誠實自報不可用：{messages}"

    def test_live_listener_thread_still_registers(self):
        """有牙的鎖不能把正常路徑一起打死：執行緒存活時仍須註冊成功。"""
        fake_keyboard = MagicMock()
        stop = threading.Event()
        live = threading.Thread(target=stop.wait, daemon=True)
        live.start()
        fake_keyboard._listener.listening_thread = live
        try:
            with patch.object(hotkey_handler, "_KEYBOARD_AVAILABLE", True), \
                 patch.object(hotkey_handler, "keyboard", fake_keyboard, create=True):
                handler = HotkeyHandler()
                handler.register()
            assert handler._registered is True
        finally:
            stop.set()
            live.join(timeout=2)


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="[MAC-NATIVE-ONLY] macOS 真機專屬（非 Darwin 上 skip 而非恆綠）",
)
@pytest.mark.skipif(
    not hotkey_handler._KEYBOARD_AVAILABLE,
    # 🔴 標籤必須掛在**這一層**（R76 四方複審 SD-03）：pytest 疊多層 skipif 時只印最上
    # 層命中的那個 reason，而 R76 把 `keyboard` 移進 `[hotkey]` extra 之後，實際命中的
    # 就是這一層（不是上面那個 darwin 層）。沒有標籤 ⇒ 這支從 skip 盤點的反方向摘要裡
    # 整個消失，「本輪唯一一筆淨覆蓋損失」會靜默發生。
    reason="[MAC-NATIVE-ONLY] keyboard 套件未安裝（需 `.[hotkey]` extra；macOS CI 已裝）",
)
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root 下 keyboard 可正常監聽"
)
def test_macos_non_root_register_reports_unavailable_for_real():
    """非 mock 常駐測試：macOS 非 root 時 register() 必須自報不可用。

    keyboard 0.13.5 `_darwinkeyboard.listen()` 首行即 `os.geteuid() != 0` →
    OSError 13，故此處為確定性行為，非 flaky。
    """
    original_hook = threading.excepthook
    hotkey_handler._excepthook_installed = False
    try:
        handler = HotkeyHandler()
        handler.register()
        assert handler._registered is False, (
            "macOS 非 root 下 keyboard 監聽執行緒必定死亡，register() 不得宣稱成功"
        )
    finally:
        threading.excepthook = original_hook
        hotkey_handler._excepthook_installed = False


# ──────────────────────────────────────────────
# [B] cmd.exe 8191 字元守門
# ──────────────────────────────────────────────

class TestCmdShimLineLengthGuard:
    def test_oversized_prompt_fails_loud_before_hitting_cmd_limit(self):
        prompt = "x" * (_CMD_LINE_MAX_CHARS + 100)
        with pytest.raises(RuntimeError) as exc:
            _build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", prompt])
        msg = str(exc.value)
        assert "8191" in msg and str(_CMD_LINE_MAX_CHARS) in msg, msg
        assert "stdin" in msg or "檔案" in msg, f"錯誤訊息必須指路可行解法：{msg}"

    def test_guard_threshold_is_below_the_hard_limit(self):
        assert 0 < _CMD_LINE_MAX_CHARS < 8191, (
            "守門閾值必須嚴格低於 cmd.exe 8191 硬上限，才能在超限前攔下"
        )

    def test_line_at_threshold_still_builds(self):
        """邊界內不得誤擋（否則守門本身變成新的缺陷）。

        🔴 overhead 以**非空** prompt 量：空字串參數在組行時不佔它自己的位置
        （實測差 2 字元），拿它當基準會讓「剛好等於閾值」的斷言恆差 2——那是量法
        的 off-by-N，不是守門的行為。改以 1 字元 prompt 取基準再回推，基準與目標
        用同一條路徑組出來，量法本身就不會引入偏差。
        """
        base = len(_build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", "x"]))
        prompt = "x" * (_CMD_LINE_MAX_CHARS - base + 1)
        line = _build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", prompt])
        assert len(line) == _CMD_LINE_MAX_CHARS
        assert line.startswith('cmd /d /s /c "') and line.endswith('"')


# ──────────────────────────────────────────────
# [C] 超長 prompt 不得讓整場 run 崩潰（R69；DEF 見回報）
# ──────────────────────────────────────────────
# WHY：[B] 的守門是 `raise`，而全樹**零呼叫端承接**——`PtyWrapper.start()` 由
# `PtyExecutor.execute()` 與 `execution/prompt_dispatcher.execute_prompt_impl()`
# 直呼，兩者上游（Coordinator.run_step / steps_orchestrator 主迴圈）都沒有
# try/except，例外會一路穿到 `__main__` ⇒ Windows 上一支超長 prompt 由「單步失敗
# 可進 CORRECTION／ESCALATION」惡化成「整場 run 崩潰、其餘步驟全不執行」。
# 本鎖驗的是「啟動期長度守門降級為單步失敗訊號」，不是 cmd.exe 行為（無 Windows
# 真機；以 monkeypatch 讓 start() 拋出該例外，平台無關）。


class _ExplodingPty:
    """start() 必拋 CmdLineTooLongError 的假 PTY（模擬 Windows 超長 prompt）。"""

    instances: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        _ExplodingPty.instances.append(self)
        self.closed = False

    def start(self):
        raise CmdLineTooLongError(
            "cmd.exe 命令列長度 9000 字元超過保守上限 7800（硬上限 8191）："
            ".cmd/.bat shim 無法傳遞這麼長的 prompt。請縮短 prompt，或改以檔案／stdin 傳遞內容。"
        )

    def close(self):
        self.closed = True

    @property
    def is_alive(self):
        return False

    def readline(self, timeout=None):
        return None


class TestOversizedPromptDoesNotKillTheWholeRun:
    """兩條真實呼叫鏈各一鎖：例外不得逃出 executor／dispatcher 邊界。"""

    def setup_method(self):
        _ExplodingPty.instances = []

    def test_exception_type_is_catchable_and_still_a_runtimeerror(self):
        # 既有 [B] 鎖以 RuntimeError 斷言；專用子類別必須維持該相容性，
        # 否則本輪修復會靜默廢掉上面那條鎖。
        assert issubclass(CmdLineTooLongError, RuntimeError)
        prompt = "x" * (_CMD_LINE_MAX_CHARS + 100)
        with pytest.raises(CmdLineTooLongError):
            _build_cmd_shim_line(r"C:\npm\claude.cmd", ["-p", prompt])

    def test_pty_executor_degrades_to_a_failed_step_output(self):
        from autoclaude.infra.adapters import pty_executor as pe
        from autoclaude.utils.config import ClaudeConfig, LoopConfig

        ex = pe.PtyExecutor(ClaudeConfig(), LoopConfig(), log_dir="logs")
        with patch.object(pe, "PtyWrapper", _ExplodingPty):
            out = ex.execute("x" * 99999, timeout=1, label="step_a")
        assert out.completed is False, "啟動期失敗必須標記為未完成（可被 CORRECTION 承接）"
        assert out.exit_code != 0, "必須以非零 exit_code 表達失敗，不得偽裝成成功"
        assert "7800" in out.text and "prompt" in out.text, out.text

    def test_prompt_dispatcher_degrades_to_a_failed_step_output(self):
        from autoclaude.execution import playbook_runner as pr
        from autoclaude.execution import prompt_dispatcher as pd

        runner = MagicMock()
        runner._cfg.claude.extra_args = []
        runner._cfg.claude.continue_flag = ""
        runner._cfg.claude.encoding = "utf-8"
        runner._cfg.log_dir = "logs"
        runner._cfg.loop.auth_patterns = []
        runner._cfg.loop.auth_response = ""

        # `execute_prompt_impl` 內是 late import（`from .playbook_runner import _pr`），
        # 故 patch 點必須是 playbook_runner 模組屬性，不是 prompt_dispatcher。
        fake_pr = MagicMock()
        fake_pr.PtyWrapper = _ExplodingPty
        with patch.object(pr, "_pr", lambda: fake_pr):
            out = pd.execute_prompt_impl(
                runner, prompt="x" * 99999, maintain_context=False,
                timeout=1, step_label="step_a",
            )
        assert "7800" in out.text and "prompt" in out.text, out.text
        assert out.triggered_halt is False and out.triggered_compact is False


# ──────────────────────────────────────────────
# [C] R81（HLM-S1-01）：PtyWrapper.start() 必須回返
#
# 缺陷：wexpect 的 host 以 `CreateProcess` 回報的 PID 組 pipe 名，console-reader
# 卻以自己的 `os.getpid()` 組名。venv 的 python.exe 是 trampoline（會把真直譯器
# 再 spawn 成子行程）⇒ 兩個 PID 不同 ⇒ host 的 `connect_to_child()` 那個**沒有
# 逾時**的 `while True` 永遠等不到 pipe，`start()` 靜默不回返。
#
# 為何這一組鎖必須存在：`start()` 的回返性此前**零覆蓋**，所以這個 P0 可以潛伏
# 四輪——它不報錯、不逾時（逾時判斷在 start() 之後的迴圈裡），表徵只有「整場
# run 不動」。下面第一組驗判準本身（含失效方向），第二組在 Windows 真機上把
# 「不回返」變成一個會紅的量測值。
# ──────────────────────────────────────────────

class TestWexpectPidHandshakeProbe:
    """探針量的是『父看到的 PID == 子自報的 PID』，不是『是不是 venv』。"""

    def setup_method(self):
        pw._launcher_reports_consistent_pid.cache_clear()

    def teardown_method(self):
        pw._launcher_reports_consistent_pid.cache_clear()

    def test_mismatched_pid_means_the_pipe_handshake_can_never_complete(self):
        fake = MagicMock()
        fake.pid = 111
        fake.communicate.return_value = (b"222\n", b"")
        with patch("subprocess.Popen", return_value=fake):
            assert pw._launcher_reports_consistent_pid() is False

    def test_matching_pid_keeps_wexpect_available(self):
        # 反向鎖：判準若退化成「一律回 False」，PTY 模擬會在所有平台被靜默廢掉，
        # 而表徵（程式跑得動）與修好完全相同。
        fake = MagicMock()
        fake.pid = 4242
        fake.communicate.return_value = (b"4242\n", b"")
        with patch("subprocess.Popen", return_value=fake):
            assert pw._launcher_reports_consistent_pid() is True

    def test_unmeasurable_falls_back_to_the_path_known_to_return(self):
        # 量不到時必須偏向 subprocess——那是唯一已實證會回返的路。
        with patch("subprocess.Popen", side_effect=OSError("boom")):
            assert pw._launcher_reports_consistent_pid() is False


class TestStartBranchHonoursTheProbe:
    def _wrapper(self):
        return PtyWrapper(
            command="claude", args=["--version"], auth_patterns=[], auth_response="",
        )

    def test_unusable_wexpect_routes_to_subprocess(self):
        w = self._wrapper()
        with patch.object(pw, "_WEXPECT_AVAILABLE", True), \
             patch.object(pw, "_launcher_reports_consistent_pid", return_value=False), \
             patch.object(pw, "_resolve_command", return_value=[r"C:\bin\claude.exe"]), \
             patch.object(w, "_start_wexpect") as wex, \
             patch.object(w, "_start_subprocess") as sub:
            w.start()
        assert wex.call_count == 0, "wexpect 在此形態下會永久卡住，不得被呼叫"
        assert sub.call_count == 1

    def test_usable_wexpect_is_still_preferred(self):
        w = self._wrapper()
        with patch.object(pw, "_WEXPECT_AVAILABLE", True), \
             patch.object(pw, "_launcher_reports_consistent_pid", return_value=True), \
             patch.object(pw, "_resolve_command", return_value=[r"C:\bin\claude.exe"]), \
             patch.object(w, "_start_wexpect") as wex, \
             patch.object(w, "_start_subprocess") as sub:
            w.start()
        assert wex.call_count == 1, "PTY 模擬不得被無條件廢掉（那與修好長得一樣）"
        assert sub.call_count == 0


_START_BOUNDEDNESS_CHILD = """
import sys, time
from autoclaude.perception.pty_wrapper import PtyWrapper
w = PtyWrapper(command="cmd", args=["/c", "echo", "hi"], auth_patterns=[], auth_response="")
t0 = time.time()
w.start()
print("ELAPSED=%.2f" % (time.time() - t0))
w.close()
"""


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="[WINDOWS-NATIVE-ONLY] wexpect 僅 Windows 可用；"
           "非 Windows 上 start() 本來就只有 subprocess 一條路",
)
def test_start_returns_within_a_bound_on_windows(tmp_path):
    """`start()` 必須在有界時間內回返（修復前本機實測 25s／45s 皆不回返）。"""
    proc = subprocess.run(
        [sys.executable, "-c", _START_BOUNDEDNESS_CHILD],
        capture_output=True, text=True, timeout=90,
        cwd=str(_REPO_ROOT), encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr[-2000:]!r}"
    elapsed = [
        float(ln.split("=", 1)[1])
        for ln in proc.stdout.splitlines() if ln.startswith("ELAPSED=")
    ]
    assert elapsed, f"子行程沒印出量測值：stdout={proc.stdout!r}"
    assert elapsed[0] < 15.0, f"start() 花了 {elapsed[0]}s，回返性已退化"
