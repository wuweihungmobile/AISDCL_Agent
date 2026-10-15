"""procutil：行程樹的快照／終止／強殺與 pid 身分判定（真行程，不是 mock）。"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import time

import psutil

from app import procutil

_PARENT = textwrap.dedent("""
    import subprocess, sys, time
    child = subprocess.Popen([sys.executable, "-c", {child_code!r}])
    print(child.pid, flush=True)
    time.sleep(60)
""")
_SLEEPER = "import time; time.sleep(60)"
_STUBBORN = ("import signal, sys, time\n"
             "if sys.platform != 'win32':\n"
             "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
             "print('ready', flush=True)\ntime.sleep(60)")


def _spawn_tree(child_code: str) -> tuple[subprocess.Popen, int]:
    parent = subprocess.Popen(
        [sys.executable, "-c", _PARENT.format(child_code=child_code)],
        stdout=subprocess.PIPE, text=True, **procutil.popen_platform_kwargs())
    assert parent.stdout is not None
    return parent, int(parent.stdout.readline())


def _wait_until(pred, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return False


def test_terminate_takes_the_grandchild_too() -> None:
    parent, child_pid = _spawn_tree(_SLEEPER)
    try:
        procs = procutil.begin_terminate(parent.pid)
        snapshot = {p.pid for p in procs}
        if sys.platform == "win32":
            # Windows 行為＝venv 的 python.exe 是啟動器（venvlauncher），會再 spawn 真正的
            # 直譯器當子行程，所以樹裡除了 parent／child 還有啟動器子行程（Windows 實測
            # 4 個 python.exe）；快照必須「涵蓋」parent 與 child，而不是恰好等於它們。
            assert {parent.pid, child_pid} <= snapshot
        else:
            assert snapshot == {parent.pid, child_pid}
        parent.wait(timeout=10)
        assert _wait_until(lambda: not procutil.survivors(procs, exclude_pid=parent.pid))
        assert not procutil.pid_alive(child_pid)
    finally:
        parent.kill()
        parent.wait()


def test_a_child_that_ignores_the_terminate_signal_is_force_killed() -> None:
    parent, child_pid = _spawn_tree(_STUBBORN)
    try:
        assert _wait_until(lambda: procutil.pid_alive(child_pid))
        time.sleep(0.5)                    # 讓子行程裝好 SIGTERM 忽略
        procs = procutil.begin_terminate(parent.pid)
        parent.wait(timeout=10)
        time.sleep(0.3)
        left = procutil.survivors(procs, exclude_pid=parent.pid)
        if sys.platform != "win32":
            # POSIX 行為＝SIGTERM 被忽略，行程仍在，必須升級強殺。
            # Windows 行為＝terminate 即 TerminateProcess，無法被忽略，所以這裡不會有倖存者。
            assert [p.pid for p in left] == [child_pid]
        killed = procutil.force_kill(left)
        assert killed == [p.pid for p in left]
        assert _wait_until(lambda: not procutil.pid_alive(child_pid))
    finally:
        parent.kill()
        parent.wait()


def test_begin_terminate_on_a_gone_pid_is_a_noop() -> None:
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    assert procutil.begin_terminate(done.pid) == []


def test_pid_alive_checks_identity_not_just_existence() -> None:
    proc = subprocess.Popen([sys.executable, "-c", _SLEEPER])
    try:
        created = procutil.process_create_time(proc.pid)
        assert created is not None
        assert procutil.pid_alive(proc.pid)
        assert procutil.pid_alive(proc.pid, created)
        assert not procutil.pid_alive(proc.pid, created - 3600), "create_time 對不上＝pid 被重用"
    finally:
        proc.kill()
        proc.wait()
    assert not procutil.pid_alive(proc.pid)
    assert not procutil.pid_alive(None)
    assert not procutil.pid_alive(0)
    assert not procutil.pid_alive(-5)


def test_platform_kwargs_match_the_platform() -> None:
    kwargs = procutil.popen_platform_kwargs()
    if sys.platform == "win32":
        assert set(kwargs) == {"creationflags"}
    else:
        assert kwargs == {"start_new_session": True}


def test_psutil_is_what_the_module_uses() -> None:
    assert procutil.psutil is psutil


def test_a_failing_descendant_listing_still_terminates_the_root(monkeypatch) -> None:
    proc = subprocess.Popen([sys.executable, "-c", _SLEEPER])
    try:
        def boom(self, recursive=False):
            raise psutil.AccessDenied(self.pid)

        monkeypatch.setattr(psutil.Process, "children", boom)
        procs = procutil.begin_terminate(proc.pid)
        assert [p.pid for p in procs] == [proc.pid]
        proc.wait(timeout=10)
    finally:
        monkeypatch.undo()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
