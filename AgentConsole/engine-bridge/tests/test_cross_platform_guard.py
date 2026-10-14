"""跨平台守則的機械鎖（掌舵者 2026-10-14：本輪做完會切到 Windows 11 繼續）。

以 AST 掃 `app/` 全套件（不是文字 grep——docstring 提到 os.kill 不算違規）：
不得出現只在 POSIX 存在的 API。新增的模組自動納入，不需回來改這支測試。
"""
from __future__ import annotations

import ast
from pathlib import Path

import app

_APP_DIR = Path(app.__file__).resolve().parent
_POSIX_ONLY_MODULES = frozenset({"fcntl", "pty", "termios", "resource", "pwd", "grp", "tty"})
_POSIX_ONLY_OS_ATTRS = frozenset({
    "kill", "killpg", "fork", "forkpty", "setsid", "getpgid", "setpgid", "geteuid",
    "getuid", "chown", "fchmod", "mkfifo", "wait3", "wait4",
})
#: mock_claude 只在 `sys.platform != "win32"` 守衛內使用 signal（見該檔註解）。
_SIGNAL_ALLOWED_IN = frozenset({"mock_claude.py"})


def _violations(py: Path) -> list[str]:
    tree = ast.parse(py.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [f"import {a.name}" for a in node.names
                    if a.name.split(".")[0] in _POSIX_ONLY_MODULES]
            if py.name not in _SIGNAL_ALLOWED_IN:
                out += [f"import {a.name}" for a in node.names if a.name == "signal"]
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            signal_banned = top == "signal" and py.name not in _SIGNAL_ALLOWED_IN
            if top in _POSIX_ONLY_MODULES or signal_banned:
                out.append(f"from {node.module} import …")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in _POSIX_ONLY_OS_ATTRS:
                out.append(f"os.{node.attr}")
            if node.value.id == "socket" and node.attr == "AF_UNIX":
                out.append("socket.AF_UNIX")
        elif isinstance(node, ast.keyword) and node.arg == "preexec_fn":
            out.append("preexec_fn=")
    return [f"{py.name}:{v}" for v in out]


def test_no_posix_only_api_in_the_app_package() -> None:
    files = sorted(_APP_DIR.rglob("*.py"))
    assert len(files) >= 5, "掃描面異常小"
    found = [v for py in files for v in _violations(py)]
    assert found == [], f"發現只在 POSIX 存在的 API（Windows 會炸）：{found}"


def test_the_scanner_itself_catches_what_it_claims_to_catch(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(
        "import os, signal, fcntl, socket, subprocess\n"
        "os.kill(1, signal.SIGTERM)\nos.killpg(1, 9)\nsocket.AF_UNIX\n"
        "subprocess.Popen(['x'], preexec_fn=lambda: None)\n", encoding="utf-8")
    got = _violations(bad)
    for needle in ("os.kill", "os.killpg", "import fcntl", "import signal", "socket.AF_UNIX",
                   "preexec_fn="):
        assert any(needle in v for v in got), (needle, got)
