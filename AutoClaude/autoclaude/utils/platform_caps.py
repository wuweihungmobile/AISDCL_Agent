"""平台能力抽象層 —— autoclaude/ 內平台判斷與行程樹回收的唯一收斂點。"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

# 為何在 utils/ 而不是 core/ports/ + infra/adapters/（ADR-XPLAT-002 §7 決策記錄）：
#   Port 的存在理由是「同一介面、多種可在 wiring 期抽換的實作」。作業系統不是
#   可注入的相依，它在 process 啟動時就定死；把它做成 Port 會多出 interface +
#   adapter + wiring 註冊（實測 ≥ 80 LOC），而 notifier.notify() 這類模組級函式
#   根本不在 Kernel 的建構鏈上、拿不到注入。utils/ 是既有的 shared-kernel 層
#   （core / execution / perception / plugins 皆已 import，如 utils.trace_context），
#   放這裡零新增 importlinter ignore 條目、且本模組純函式無狀態無 I/O 策略。
#
# 本模組刻意「讀 sys.platform 於呼叫時」而非模組載入時快取：測試以
# `patch("autoclaude.utils.platform_caps.sys.platform", ...)` 模擬 Windows 分支
# （Windows 零真機），快取會讓那些模擬失效。唯一的例外是呼叫端自行在
# import 期算出的 `_NEW_SESSION_KWARGS` 常數（見 execution/evaluator.py）。

#: POSIX 收殺節奏：先 SIGTERM 給緩衝，輪詢到期仍活才升級 SIGKILL。
_SIGTERM_GRACE_SECONDS = 2.0
_KILL_POLL_INTERVAL_SECONDS = 0.05


def is_windows() -> bool:
    """目前直譯器是否跑在 Windows。"""
    return sys.platform == "win32"


def is_macos() -> bool:
    """目前直譯器是否跑在 macOS。"""
    return sys.platform == "darwin"


def new_session_kwargs() -> dict:
    """`subprocess.Popen` 的行程組隔離參數。"""
    # POSIX 要整棵殺，子行程須先成為新 session 的 process group leader（PID 即
    # pgid），`kill_process_tree()` 的 killpg 才打得到整棵樹而不是打到呼叫者自己
    # 所在的 group（自殺級退化，見 tests/test_evaluator_kill_tree.py 1b 節）。
    # start_new_session 為 POSIX only，Windows 上不支援故回空 dict。
    return {} if is_windows() else {"start_new_session": True}


def kill_process_tree(proc: subprocess.Popen) -> None:
    """終結 proc 及其任意深度的孫行程（全樹唯一實作）。"""
    # 為何需要：`subprocess.run(..., timeout=)` 或 `Popen.terminate()` 只處理直接
    # 子行程（POSIX 的 /bin/sh、Windows 的 cmd.exe）；該殼再 fork 出的孫行程會變
    # 孤兒（PPID→1）續跑並寫檔，使「已判失敗」的工作仍在背景產生副作用。
    # pid 非真實整數即跳過（測試常以 MagicMock 充當 proc，其 .pid 非 int，
    # 不得因此真的去殺東西）。
    pid = getattr(proc, "pid", None)
    if not isinstance(pid, int):
        return
    # Windows：`taskkill /T`（整棵樹）`/F`（強制）。失敗一律吞掉——收殺是
    # best-effort 的清理路徑，不該讓呼叫端的錯誤處理再被二次例外蓋掉。
    if is_windows():
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return
    # POSIX：對整個 process group 送訊號（前提是 new_session_kwargs() 已讓子行程
    # 自成 group）。signal 0 為存活探測，不送實際訊號。
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        deadline = time.monotonic() + _SIGTERM_GRACE_SECONDS
        while time.monotonic() < deadline:
            try:
                os.killpg(pgid, 0)
            except OSError:
                return
            time.sleep(_KILL_POLL_INTERVAL_SECONDS)
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass
