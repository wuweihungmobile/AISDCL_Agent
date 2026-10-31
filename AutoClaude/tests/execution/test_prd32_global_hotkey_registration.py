"""PRD §3.2 ESC+F12 全域中斷：入口真的註冊（此前只建了 `HotkeyHandler()` 卻從不 `register()`）。

立案（PRD §16.2「§3.2 10 態 FSM」那一列）：`main()` 建了 HotkeyHandler、把 `hotkey.triggered` 接進
AutoResumeService 的 `is_interrupted`，卻沒有任何生產路徑呼叫 `register()` ⇒ 熱鍵從未被註冊，
`triggered` 永遠是 False，「ESC+F12 全域安全停止」是機制蓋好沒接電。本檔把「入口真的註冊」與
三個不註冊的場合釘成回歸：

  (a) 註冊閘：有 TTY 且非無人值守 ⇒ 註冊一次；無 TTY／無人值守 ⇒ 零次；註冊失敗只 warning。
  (b) 入口：真 `main()` 在開機自檢通過之後才註冊（自檢拒絕啟動時零次），並在結束時卸下。
"""
from __future__ import annotations

import logging
import sys
import threading

import pytest

from autoclaude import main as main_mod
from autoclaude.execution import boot_self_check as B
from tests.execution.test_prd12_permission_bypass_invariant8 import (
    _boot,
    _FakeService,
    _synthetic_config,
)

_UNATTENDED = "AUTOSDD_UNATTENDED"
_LOG = logging.getLogger("test.prd32")


class _Stdin:
    """替身 stdin：只有 isatty() 與（需要時）拋例外兩種形態。"""

    def __init__(self, tty: bool | Exception):
        self._tty = tty

    def isatty(self) -> bool:
        if isinstance(self._tty, Exception):
            raise self._tty
        return self._tty


class _Hotkey:
    triggered = False
    stop_event = threading.Event()

    def __init__(self, register_raises: Exception | None = None):
        self.register_calls = 0
        self.unregister_calls = 0
        self._raises = register_raises

    def register(self) -> None:
        self.register_calls += 1
        if self._raises is not None:
            raise self._raises

    def unregister(self) -> None:
        self.unregister_calls += 1


@pytest.fixture(autouse=True)
def _interactive_env(monkeypatch):
    monkeypatch.delenv(_UNATTENDED, raising=False)
    # 本檔守的是「註冊閘」的邏輯，用 sys.stdin 替身模擬有／無 TTY。Windows 另要求 stdin 是真
    # console（`GetConsoleMode`）：那一層有專屬測試 test_stdin_is_tty_windows_console.py。這裡
    # 讓 Windows 也走 `isatty()` 替身那條路，否則 pytest 的 NUL stdin 會讓 Windows 上「有 TTY」
    # 那幾案恆為 False。
    monkeypatch.setattr(main_mod, "is_windows", lambda: False)


# ══════════════════════════════════════════════════════════════════════════════
# (a) 註冊閘
# ══════════════════════════════════════════════════════════════════════════════
def test_a_tty_and_a_watched_session_registers_exactly_once(monkeypatch):
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    hk = _Hotkey()
    assert main_mod.register_global_hotkey(hk, _LOG) is True
    assert hk.register_calls == 1


def test_no_tty_registers_nothing_and_says_so(monkeypatch, caplog):
    monkeypatch.setattr(sys, "stdin", _Stdin(False))
    hk = _Hotkey()
    with caplog.at_level(logging.INFO, logger="test.prd32"):
        assert main_mod.register_global_hotkey(hk, _LOG) is False
    assert hk.register_calls == 0
    assert "無 TTY，略過全域熱鍵" in caplog.text


@pytest.mark.parametrize("stdin", [None, _Stdin(ValueError("I/O operation on closed file")),
                                   _Stdin(OSError("bad fd"))],
                         ids=["stdin-none", "closed-stdin", "bad-fd"])
def test_an_unusable_stdin_is_no_tty_not_a_crash(monkeypatch, stdin):
    """pythonw／被關掉的 stdin：isatty() 不可用就是「沒有人在終端機前」，不是啟動失敗。"""
    monkeypatch.setattr(sys, "stdin", stdin)
    hk = _Hotkey()
    assert main_mod.register_global_hotkey(hk, _LOG) is False
    assert hk.register_calls == 0


@pytest.mark.parametrize("value", ["1", "true", "anything"])
def test_an_unattended_round_never_registers_even_with_a_tty(monkeypatch, value, caplog):
    """無人值守回合沒有人會按鍵；全域鍵盤 hook 在那種環境只有副作用（suppress 會吃掉按鍵）。
    判準同 `evaluator.unattended_refusal`：變數有設（非空）即是。"""
    monkeypatch.setenv(_UNATTENDED, value)
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    hk = _Hotkey()
    with caplog.at_level(logging.INFO, logger="test.prd32"):
        assert main_mod.register_global_hotkey(hk, _LOG) is False
    assert hk.register_calls == 0
    assert _UNATTENDED in caplog.text


def test_an_empty_unattended_variable_counts_as_unset(monkeypatch):
    monkeypatch.setenv(_UNATTENDED, "")
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    hk = _Hotkey()
    assert main_mod.register_global_hotkey(hk, _LOG) is True and hk.register_calls == 1


def test_a_failing_register_only_warns_and_never_stops_the_engine(monkeypatch, caplog):
    """keyboard 未裝／macOS listener 非 root 失敗的判準住 `HotkeyHandler.register()` 自己；
    這裡守的是更外一層：它即使拋例外，引擎也要照常啟動。"""
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    hk = _Hotkey(register_raises=RuntimeError("listener died"))
    with caplog.at_level(logging.WARNING, logger="test.prd32"):
        assert main_mod.register_global_hotkey(hk, _LOG) is False
    assert hk.register_calls == 1
    assert "listener died" in caplog.text and "ESC+F12" in caplog.text


# ══════════════════════════════════════════════════════════════════════════════
# (b) 入口：真 main()
# ══════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def hotkeys(monkeypatch):
    made: list[_Hotkey] = []

    def _factory():
        made.append(_Hotkey())
        return made[-1]
    monkeypatch.setattr(main_mod, "HotkeyHandler", _factory)
    return made


def test_main_registers_once_under_a_tty_and_unregisters_when_the_run_ends(
        tmp_path, monkeypatch, hotkeys):
    """核心那一格＝本缺陷的證偽器：拿掉入口的註冊呼叫 ⇒ register_calls == 0 ⇒ 紅。"""
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path)) == 0
    assert len(hotkeys) == 1
    assert (hotkeys[0].register_calls, hotkeys[0].unregister_calls) == (1, 1)


@pytest.mark.parametrize("tty, env, expected", [
    pytest.param(True, {}, 1, id="tty-interactive"),
    pytest.param(False, {}, 0, id="no-tty"),
    pytest.param(True, {_UNATTENDED: "1"}, 0, id="unattended"),
])
def test_main_drives_the_real_handler_class_register_per_the_gate(
        tmp_path, monkeypatch, tty, env, expected):
    """不換掉 HotkeyHandler 類別、只攔它的 `register`：入口建出的就是生產那個類別的實例。"""
    from autoclaude.perception.hotkey_handler import HotkeyHandler
    calls: list = []
    monkeypatch.setattr(HotkeyHandler, "register", lambda self: calls.append(self))
    monkeypatch.setattr(sys, "stdin", _Stdin(tty))
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path), env=env) == 0
    assert len(calls) == expected
    assert all(isinstance(c, HotkeyHandler) for c in calls)


def test_main_without_a_tty_never_registers(tmp_path, monkeypatch, hotkeys):
    monkeypatch.setattr(sys, "stdin", _Stdin(False))
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path)) == 0
    assert hotkeys[0].register_calls == 0


def test_main_in_an_unattended_round_never_registers(tmp_path, monkeypatch, hotkeys):
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path), env={_UNATTENDED: "1"}) == 0
    assert hotkeys[0].register_calls == 0


def test_a_boot_self_check_refusal_leaves_the_keyboard_alone(tmp_path, monkeypatch, hotkeys):
    """拒絕啟動的 run 不得先把全域鍵盤 hook 掛上去：return 之前沒有 finally 會替它卸下。"""
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    cfg = _synthetic_config(tmp_path, '["--permission-mode", "bypassPermissions"]')
    rc = _boot(tmp_path, monkeypatch, cfg, isolation=B.IsolationEvidence())
    assert rc == 1 and _FakeService.built is False
    assert hotkeys[0].register_calls == 0


def test_the_hook_is_released_even_when_the_run_itself_blows_up(tmp_path, monkeypatch, hotkeys):
    monkeypatch.setattr(sys, "stdin", _Stdin(True))

    def _boom(self, path, fresh=False):
        raise RuntimeError("run exploded")
    monkeypatch.setattr(_FakeService, "run", _boom)
    with pytest.raises(RuntimeError, match="run exploded"):
        _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path))
    assert (hotkeys[0].register_calls, hotkeys[0].unregister_calls) == (1, 1)
