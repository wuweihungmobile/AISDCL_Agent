"""測試等待用的時間常數（單一真相源；OBS-SI-329）。

為什麼不能是「固定牆鐘 60 秒」：E2E 引擎測試每跑一個 run，就要起一整棵行程樹——引擎（Windows 的
venv 啟動器會再 re-exec 一層）、PID 一致性探針、`claude --version` 探針、每個步驟一支 mock claude，
約 12 次行程建立，而且每支 Python 行程都要整套匯入 autoclaude。成本不在 CPU 算力，在「行程建立＋匯
入」的吞吐量：同時活著的行程樹一多（xdist 的 worker 數、另一個同時在跑的 pytest／Gradle／突變），
它比 CPU 使用率惡化得更快。

2026-10-31 本機（i5-14600K，20 邏輯核）實測同一支 3 步 run 的耗時：
  · `-n auto`（14 worker）、機器閒置：約 3 秒；全套 92 秒全綠。
  · 3 個 pytest session × 12 worker 同時跑（36 worker）：COMPLETED 的 run 耗時 p50 32 秒、
    p90 59 秒、p99 64～70 秒（兩個 session 各 99 筆）；全綠，但最慢的 70 秒已超過舊的 60 秒。
  · 60 個 CPU 空轉行程＋`-n 18 --dist worksteal`（約 4 倍超載）：29 失敗／1230 通過，其中 19 個失敗
    區段是「60s 內沒有到達…最後狀態 RUNNING」；部分 run 在 60 秒時連第一個步驟都還沒開始。

結論：舊的固定 60 秒，閒置時有 20 倍餘裕、1.8 倍超載時餘裕歸零、4 倍超載時直接逾時。逾時值只是
「卡死偵測器」，綠燈時不花任何時間，所以改量**停滯**而不是量牆鐘：run 只要還在產生事件就繼續等，
真的卡住（STALL_TIMEOUT 內 status 與事件序號都沒動）才判死；絕對上限 WAIT_CAP 擋住「一直有事件卻永
遠到不了目標」的活鎖。沒有進度可看的等待（等 mock claude 第一次被呼叫、等 FSM／稽核檔落地）用
SPAWN_TIMEOUT。

同一個道理也適用於「行程剛退出就斷言 pid 已不在行程表」：Windows 上 `Popen.wait()` 已回來（行程物件
已 signaled），`psutil.pid_exists()` 仍可能在極短時間內回 True（行程表的移除落後於退出通知；另一個
worker 正大量建立／結束行程時才看得到）。2026-10-31 第三次 `-n auto` 全套就在
`test_procutil.py::test_pid_alive_checks_identity_not_just_existence` 紅過一次（前兩次全綠）。
這類斷言一律改成有界輪詢 `wait_until`：成立時零成本，不成立才花時間，而且仍然會在 REAP_TIMEOUT
內抓到真的沒被殺掉的行程。
"""
from __future__ import annotations

import time
from collections.abc import Callable

#: 等一個 run 時，連續這麼久 status 與事件序號都沒有前進才判死（秒）。4 倍超載下，引擎從 spawn 到第
#: 一個步驟開始實測超過 60 秒，取 4 倍。
STALL_TIMEOUT = 240.0

#: 單次等待 run 的絕對上限（秒）：只擋「一直有事件、卻永遠到不了目標」的活鎖，不是常態會碰到的值。
WAIT_CAP = 900.0

#: 沒有進度可看的「等行程樹起來／等子行程落地」類等待（秒）：mock claude 第一次被呼叫、FSM 終態
#: 同步、稽核檔到齊。閒置時 1～3 秒、4 倍超載實測超過 60 秒，取 3 倍餘裕。
SPAWN_TIMEOUT = 180.0

#: 行程退出後，等它從作業系統行程表消失的上限（秒）。正常情況下是 0 秒；這個值只是卡死偵測器。
REAP_TIMEOUT = 30.0


def wait_until(predicate: Callable[[], bool], timeout: float = REAP_TIMEOUT,
               interval: float = 0.05) -> bool:
    """輪詢到 `predicate()` 為真或逾時；回最後一次的判定（呼叫端自己斷言並帶訊息）。"""
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)
