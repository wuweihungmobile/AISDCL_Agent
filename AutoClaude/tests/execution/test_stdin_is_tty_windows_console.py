"""`_stdin_is_tty()`：Windows 上 stdin 必須是**真 console**才算「有人在終端機前」。

立案：Windows＋Python 3.11 的 `sys.stdin.isatty()` 對 NUL（`stdin=subprocess.DEVNULL`）也回 True
（CRT 的 `_isatty` 只看「字元裝置」）。Bridge 以 DEVNULL 起的每個無頭引擎因此通過
`register_global_hotkey` 的 TTY 閘，掛上全域 ESC+F12 鍵盤 hook（`suppress=True`，會吃掉開發機的
ESC／F12；engine-1.log 逐字「全域中斷熱鍵已註冊：esc+f12」）。修法＝Windows 另問 `GetConsoleMode`：
成功才是真 console（NUL、管線、檔案皆失敗）。

本檔三層：
  (a)(b) 判準本身：`GetConsoleMode` 失敗／成功 ⇒ False／True（替身 kernel32，不依賴真 console，
         三個平台都能跑）。
  (c)    其餘平台與失效方向：非 Windows 維持 `isatty()`、判不出來＝False、不碰共用的 ctypes.windll。
  (d)    真行程證偽器：`stdin=DEVNULL` 的子行程裡 `_stdin_is_tty()` 恆為 False（Bridge 的實際起法；
         修前 Windows＋Python 3.11 為 True）。
"""
from __future__ import annotations

import ctypes
import subprocess
import sys

import pytest

from autoclaude import main as main_mod


class _Stdin:
    """替身 stdin：只有 isatty()。"""

    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class _Kernel32:
    """替身 kernel32：記錄呼叫、回預設的 GetConsoleMode 結果。函式物件允許被設 restype／argtypes
    （真的 ctypes 函式也是），所以測試能檢查 prototype 有沒有被宣告。"""

    def __init__(self, console_mode_ok: bool):
        self.calls: list[tuple] = []

        def GetStdHandle(which):
            self.calls.append(("GetStdHandle", which))
            return 7

        def GetConsoleMode(handle, mode_ptr):
            self.calls.append(("GetConsoleMode", handle))
            return 1 if console_mode_ok else 0

        self.GetStdHandle = GetStdHandle
        self.GetConsoleMode = GetConsoleMode


@pytest.fixture
def as_windows(monkeypatch):
    """假裝在 Windows：`is_windows()` 回 True、`ctypes.WinDLL("kernel32")` 回替身。非 Windows 的
    `ctypes` 上沒有 `WinDLL`，所以 `raising=False`（teardown 會還原成「不存在」）。"""
    def _install(*, console_mode_ok: bool) -> _Kernel32:
        fake = _Kernel32(console_mode_ok)
        monkeypatch.setattr(main_mod, "is_windows", lambda: True)
        monkeypatch.setattr(ctypes, "WinDLL", lambda name, *a, **kw: fake, raising=False)
        return fake
    return _install


# ══════════════════════════════════════════════════════════════════════════════
# (a)(b) 判準本身
# ══════════════════════════════════════════════════════════════════════════════
def test_windows_nul_or_pipe_stdin_is_no_tty_even_though_isatty_says_true(monkeypatch, as_windows):
    """核心那一格＝本缺陷的證偽器：拿掉 GetConsoleMode 判準 ⇒ 回 True ⇒ 紅。"""
    monkeypatch.setattr(sys, "stdin", _Stdin(True))     # NUL 的 isatty() 就是 True
    fake = as_windows(console_mode_ok=False)            # GetConsoleMode 對 NUL／管線失敗
    assert main_mod._stdin_is_tty() is False
    assert [c[0] for c in fake.calls] == ["GetStdHandle", "GetConsoleMode"], "真的問過 console"


def test_windows_real_console_stdin_is_a_tty(monkeypatch, as_windows):
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    fake = as_windows(console_mode_ok=True)
    assert main_mod._stdin_is_tty() is True
    assert fake.calls == [("GetStdHandle", -10), ("GetConsoleMode", 7)], \
        "問的是 STD_INPUT_HANDLE（-10）回來的那個 handle，不是別的"


def test_windows_prototypes_are_declared_so_a_64bit_handle_is_not_truncated(
        monkeypatch, as_windows):
    """ctypes 預設回傳型別是 c_int（32 位元）：不宣告 `restype=c_void_p`，64 位元的 HANDLE 會被截斷
    或帶符號。這格釘「prototype 有宣告」，而不是只看最後的真假值（替身看不出截斷）。"""
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    fake = as_windows(console_mode_ok=True)
    assert main_mod._stdin_is_tty() is True
    assert fake.GetStdHandle.restype is ctypes.c_void_p
    assert fake.GetConsoleMode.argtypes[0] is ctypes.c_void_p


def test_the_probe_leaves_the_shared_ctypes_windll_alone(monkeypatch, as_windows):
    """prototype 若設在 `ctypes.windll.kernel32` 上，會改到行程內所有人共用的函式物件（例如
    keyboard 套件）——「呼叫前後不改其他行為」。絆線被碰就拋；拋出的例外會被「判不出來＝False」吞掉，
    所以這裡斷言的是**回 True**：碰了共用物件 ⇒ 變 False ⇒ 紅。"""
    class _Tripwire:
        def __getattr__(self, name):
            raise AssertionError(f"碰了共用的 ctypes.windll.{name}")

    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    as_windows(console_mode_ok=True)
    monkeypatch.setattr(ctypes, "windll", _Tripwire(), raising=False)
    assert main_mod._stdin_is_tty() is True


# ══════════════════════════════════════════════════════════════════════════════
# (c) 其餘平台與失效方向
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("tty", [True, False])
def test_non_windows_keeps_the_isatty_answer_and_never_loads_kernel32(monkeypatch, tty):
    loaded: list = []
    monkeypatch.setattr(main_mod, "is_windows", lambda: False)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **kw: loaded.append(a), raising=False)
    monkeypatch.setattr(sys, "stdin", _Stdin(tty))
    assert main_mod._stdin_is_tty() is tty
    assert loaded == [], "非 Windows 不得載入 kernel32"


def test_windows_with_isatty_false_never_reaches_the_console_probe(monkeypatch, as_windows):
    monkeypatch.setattr(sys, "stdin", _Stdin(False))
    fake = as_windows(console_mode_ok=True)
    assert main_mod._stdin_is_tty() is False
    assert fake.calls == [], "isatty() 已經說沒有 TTY：不必也不該再問 console"


@pytest.mark.parametrize(
    "exc", [OSError("kernel32 載入失敗"), AttributeError("沒有 GetConsoleMode")],
    ids=["kernel32-unloadable", "function-missing"])
def test_windows_probe_failure_means_no_tty_not_a_crash(monkeypatch, exc):
    """判不出來＝False：失效方向偏向「不裝全域鍵盤 hook」，且不得讓引擎起不來
    （`register_global_hotkey` 沒有為 `_stdin_is_tty()` 包 try）。"""
    def _raise(*a, **kw):
        raise exc

    monkeypatch.setattr(main_mod, "is_windows", lambda: True)
    monkeypatch.setattr(ctypes, "WinDLL", _raise, raising=False)
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    assert main_mod._stdin_is_tty() is False


# ══════════════════════════════════════════════════════════════════════════════
# (d) 真行程證偽器
# ══════════════════════════════════════════════════════════════════════════════
_CHILD = ("import sys\n"
          "from autoclaude.main import _stdin_is_tty\n"
          "sys.stdout.write('\\nTTY=' + str(_stdin_is_tty()))\n")


def test_a_child_started_with_stdin_devnull_is_never_a_tty():
    """Bridge 起無頭引擎的實際形狀（`stdin=subprocess.DEVNULL`）。不依賴任何替身：Windows＋
    Python 3.11 上修前這裡是 True（NUL 是字元裝置，isatty() 不分辨），POSIX 上本來就是 False。
    刻意不斷言「isatty() 在 Windows 上為 True」這個直譯器行為：新版 Python 可能已修，
    斷言它會讓本測試隨直譯器版本變脆。"""
    done = subprocess.run([sys.executable, "-c", _CHILD], stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=180, check=False)
    out = done.stdout.decode("utf-8", errors="replace")
    assert done.returncode == 0, done.stderr.decode("utf-8", errors="replace")
    assert out.splitlines()[-1] == "TTY=False", out
