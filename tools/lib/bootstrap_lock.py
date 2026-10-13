"""venv bootstrap 互斥鎖＋行程存活判斷＋Windows 孫行程追蹤的本體（DEF-101-398）。

原棲身 `tools/dev_start.py`（SPECIAL_FILES raw-line 棘輪）；結構性長債 DEF-101-398 要求把
這組與整備七步驟本身無關、可獨立驗證的「行程／鎖原語」拆出，本模組是其中一半（另一半＝
`nightly_heartbeat.py`）。形態照 `ci_run_status.py`（DEF-101-758 先例）：邏輯本體住本模組，
`dev_start.py` 只留同名別名與轉呼叫。

🔴 純搬移、行為逐位元不變。與搬遷前唯一的差異是**依賴注入**：原本讀 module-level `LOCK_FILE`／
`_warn` 的三個函式（`acquire_bootstrap_lock`／`release_bootstrap_lock`／`peek_bootstrap_lock`）
改收參數。`tools/tests/test_dev_start.py` 以 `mock.patch.object(dev_start, "LOCK_FILE", …)`
打樁，打樁點必須留在呼叫端——`dev_start.py` 的同名轉呼叫在**呼叫當下**才解析 `LOCK_FILE`／
`_warn`，既有打樁照舊生效。docstring 內提到的 `step_venv()`／`_stream()`／`_run_bootstrap()`／
`_ensure_venv_shape()` 仍住 `tools/dev_start.py`。

平台分支（mac 上只能以 mock 驗證 Windows 側，Windows 真機未實跑）：`pid_alive`（Windows 走
`OpenProcess`、POSIX 走 `os.kill(pid, 0)`）、`lock_target_alive`（POSIX 另以 `os.killpg` 補查）、
`list_pid_ppid_pairs_windows`（Toolhelp32，僅 Windows）、`DescendantWatcher`（僅 Windows 使用）。

🔴 葉節點模組：只被 `tools/dev_start.py` import，只依賴同層共用層 `platform_utils`。
"""

from __future__ import annotations

import ctypes
import json
import os
import threading
from collections.abc import Callable
from pathlib import Path

import platform_utils


def pid_alive(pid: int) -> bool:
    """判斷 PID 是否仍存活（P1-3：venv bootstrap 互斥鎖用來辨識陳舊鎖）。

    POSIX：`os.kill(pid, 0)` 送訊號 0 不會真的送出訊號，只探測目標是否存在／
    呼叫者是否有權限對其送訊號。ProcessLookupError＝PID 不存在（真的已死，
    陳舊鎖可安全清除）；PermissionError＝PID 存在但呼叫者無權限對它送訊號
    （常見於不同使用者擁有的行程）——這種情況代表行程仍存活，不可誤判為
    陳舊鎖去清除別人正在使用的鎖，兩者語意相反、必須分開處理。
    Windows：os.kill 不支援訊號 0 的存活探測語意，改以 OpenProcess 是否能
    成功開啟該 PID 判斷；開啟失敗時再以 GetLastError()==ERROR_ACCESS_DENIED(5)
    區分「行程存在但無權限探測」（視為存活，比照 POSIX PermissionError 分支）
    與其他失敗（如 ERROR_INVALID_PARAMETER，行程真的已死）——P2（Architect/
    SA/QA 三方複審交叉印證）：過去把任何 OpenProcess 失敗都當作「已死」，
    未區分這兩種語意相反的情況。
    """
    if platform_utils.is_windows():
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        except OSError:
            return False
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        err = ctypes.windll.kernel32.GetLastError()
        return err == 5  # ERROR_ACCESS_DENIED：行程存在但無權限探測，視為存活
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def lock_target_alive(x: int, pid_alive_fn=None) -> bool:
    """判斷鎖檔中記錄的識別碼是否仍有人存活（MUST FIX A：POSIX 改用 process
    group 追蹤後，鎖檔內同一個整數欄位隨情境橫跨兩種語意，本函式統一判斷）。

    鎖檔內容橫跨本工具生命週期兩種不同語意，且無法單從數字本身分辨是哪一種：
    ①`acquire_bootstrap_lock()` 剛取得鎖、尚未決定是否需要 bootstrap 時，
    寫入的是 orchestrator（dev_start.py 自己）的一般 PID——這不是它自己的
    process group id（實測：一般由 shell job control 啟動的行程，pid 與自身
    pgid 通常不同），只能用 `pid_alive()` 判斷；②POSIX 上一旦真的開始執行
    bootstrap，`step_venv()` 記錄的是其直接子行程 PID——因
    `_stream(..., new_process_group=True)` 對其呼叫 `start_new_session=True`
    （`setsid()`），此 PID 同時也是該 process group 的 pgid，直接子行程死亡
    後仍可能有孫行程存活，只有 `os.killpg()` 才能正確判斷（`pid_alive()` 對
    已死的直接子行程只會回報 False，正是本輪要修的舊 bug）。

    做法：先用 `pid_alive()` 檢查（涵蓋①，也涵蓋②『直接子行程本身尚存活』
    的情況）；仍判定為死時，POSIX 上再用 `os.killpg()` 補check 一次（涵蓋②
    『直接子行程已死但 process group 內仍有孫行程存活』）。兩者任一回報存活
    即視為存活——寧可保守誤判仍忙碌，也不可誤判陳舊而讓另一個 dev_start 搶
    進場競態寫入，與本工具一貫的 fail-loud 安全哲學一致。
    """
    if (pid_alive_fn or pid_alive)(x):  # DI：dev_start 傳自己的 _pid_alive（打樁點保全）
        return True
    if platform_utils.is_windows():
        return False
    try:
        os.killpg(x, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def list_pid_ppid_pairs_windows() -> list[tuple[int, int]] | None:
    """列舉 Windows 系統目前所有行程的 (pid, ppid) 對照（同上，P1）。

    比照 pid_alive() 現有的 ctypes + kernel32 風格：不新增外部依賴、不 shell
    out 到 wmic/PowerShell，改用 CreateToolhelp32Snapshot + Process32First/Next
    列舉全系統行程建立對照表。
    """
    th32cs_snapprocess = 0x00000002

    class _PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("cntUsage", ctypes.c_uint32),
            ("th32ProcessID", ctypes.c_uint32),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.c_uint32),
            ("cntThreads", ctypes.c_uint32),
            ("th32ParentProcessID", ctypes.c_uint32),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_uint32),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    try:
        snapshot = kernel32.CreateToolhelp32Snapshot(th32cs_snapprocess, 0)
    except OSError:
        return None
    if not snapshot or snapshot == -1:
        return None
    pairs: list[tuple[int, int]] = []
    try:
        entry = _PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
        if kernel32.Process32First(snapshot, ctypes.pointer(entry)):
            while True:
                pairs.append((entry.th32ProcessID, entry.th32ParentProcessID))
                if not kernel32.Process32Next(snapshot, ctypes.pointer(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return pairs


def collect_descendant_pids(root_pid: int, pairs: list[tuple[int, int]]) -> set[int]:
    """從 (pid, ppid) 對照表遞迴算出 root_pid 的所有後代 PID（不含自己）。"""
    children_of: dict[int, list[int]] = {}
    for pid, ppid in pairs:
        children_of.setdefault(ppid, []).append(pid)
    descendants: set[int] = set()
    frontier = [root_pid]
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, []):
            if child not in descendants:
                descendants.add(child)
                frontier.append(child)
    return descendants


class DescendantWatcher:
    """背景輪詢並累積目標行程存活期間出現過的後代 PID（P1：孫行程孤兒防護）。

    MUST FIX A（Architect 第三輪複審後改版）：**本機制自本輪起僅供 Windows
    使用**（`step_venv()` 只在 `os.name == "nt"` 分支建構本類別）。POSIX 已改
    用 `_stream(new_process_group=True)` + `os.killpg()`（見 `lock_target_alive`
    docstring）——Architect 用真實 subprocess + SIGKILL 實驗證實：POSIX 行程
    死亡時，其子行程會被核心立即過繼給 subreaper（PID 1），ppid 連結在死亡
    當下就已斷裂；事後才用「目前 ps 快照」回溯死亡行程的後代注定撲空。這正是
    本類別存在的理由（存活期間持續採樣，而非事後回溯），但 process group 語意
    讓 POSIX 不再需要「持續採樣＋事後回溯」這整套機制——`os.killpg()` 天生就
    不受 ppid 過繼影響，一次查詢即可涵蓋任意深度的孫行程。

    Windows 維持本機制不變：實測查證（見 dev_start.py 模組頂層設計說明／
    最終報告）顯示 Windows 的 `th32ParentProcessID` 只是行程建立當下的靜態
    快照，父行程死亡時系統不會重寫它（不像 POSIX 的 ppid 會被動態過繼）——
    故「事後回溯行程樹」在 Windows 上不像在 POSIX 上那樣『因果上必然太晚』，
    背景輪詢＋事後補採樣的既有設計繼續有效，不隨本輪 POSIX 重做而變動。
    """

    def __init__(self, pid: int, poll_interval: float = 0.3) -> None:
        self._pid = pid
        self._poll_interval = poll_interval
        self._seen: set[int] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while True:
            pairs = list_pid_ppid_pairs_windows()
            if pairs is not None:
                self._seen |= collect_descendant_pids(self._pid, pairs)
            if self._stop.wait(self._poll_interval):
                return

    def stop_and_collect(self) -> set[int]:
        """停止輪詢並回傳存活期間觀察到的後代 PID 聯集（呼叫端仍須自行以
        pid_alive() 檢查其中哪些現在仍存活——本函式只負責『曾經看過誰』）。

        MUST FIX #3（SA + Architect 各自獨立重現的 P2，Windows 適用）：`_run()`
        迴圈是「採樣 → wait(poll_interval)」，過去 `stop_and_collect()` 只 set
        stop event 讓 wait() 提前醒來、不會在醒來時多做最後一次採樣——從
        「最後一次排定採樣」到「本函式被呼叫」之間，有最多一個 poll_interval
        長的空窗，若孫行程恰好在這個空窗內誕生且仍存活，會被完全漏記。這裡在
        背景執行緒停止後，自己再同步做一次採樣並 union 進 `_seen`，用一次廉價
        的同步呼叫換掉這個結構性空窗（而非單純縮小 poll_interval——那只降低
        機率、不消除本質問題）。
        """
        self._stop.set()
        self._thread.join(timeout=12)  # 對齊單次 Toolhelp32 逾時(10s)+緩衝
        pairs = list_pid_ppid_pairs_windows()
        if pairs is not None:
            self._seen |= collect_descendant_pids(self._pid, pairs)
        return set(self._seen)


def acquire_bootstrap_lock(lock_file: Path, warn: Callable[[str], None]) -> int | None:
    """嘗試取得 venv bootstrap 互斥鎖（P1-3）。

    背景（SA 審查以真實並行執行 + kill 重跑實測證實）：兩個並行 dev_start
    呼叫、或 bootstrap 執行到一半被 SIGKILL 後使用者本能重跑，都會讓兩個
    bootstrap 行程競態寫入同一個 .venv，且雙方都回報「✅ 完成」——其中一方
    的環境其實已被覆蓋。以 O_CREAT|O_EXCL 原子建立鎖檔＋寫入自身 PID；鎖檔
    已存在時讀出其中 PID 判斷是否仍存活：存活 → 回傳 None（拿不到鎖，呼叫端
    須中止，不可靜默略過，否則使用者會誤以為環境是新的）；已死（陳舊鎖，
    如上次執行被 SIGKILL）→ 清除後重試一次。

    MUST FIX #2（SA + QA 各自獨立重現的 P1）：鎖檔可能記錄多個 PID（JSON
    陣列，見 `parse_lock_pids`）——只要其中「任一」PID 仍存活就視為忙碌；
    必須「全部」PID 皆已死透，才視為真正陳舊、可安全清除重試。

    MUST FIX A：存活判斷改用 `lock_target_alive()` 而非單純 `pid_alive()`——
    鎖檔內容可能是 orchestrator 自己的一般 PID，也可能是 POSIX 上 bootstrap
    直接子行程的 pgid（其死亡不代表 process group 內孫行程也死了），見該函式
    docstring。
    回傳值為鎖檔 fd，呼叫端須以 try/finally 搭配 release_bootstrap_lock 釋放。
    """
    for _attempt in range(2):
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                text = lock_file.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                warn(f"venv bootstrap 鎖檔（{lock_file.name}）內容無法辨識（{e}）— "
                     f"為安全起見視為仍被持有，本次中止；請確認無其他 dev_start 執行中"
                     f"後手動刪除該檔")
                return None
            pids = parse_lock_pids(text)
            if pids is None:
                warn(f"venv bootstrap 鎖檔（{lock_file.name}）內容無法辨識（非合法 PID/PID"
                     f"清單）— 為安全起見視為仍被持有，本次中止；請確認無其他 dev_start "
                     f"執行中後手動刪除該檔")
                return None
            alive = [p for p in pids if lock_target_alive(p)]
            if alive:
                warn(f"偵測到另一個 dev_start 正在整備 venv（PID {sorted(alive)}），"
                     f"本次中止以避免競態寫入，請稍後重試")
                return None
            try:
                lock_file.unlink()
            except OSError as e:
                warn(f"清除陳舊 venv bootstrap 鎖檔失敗（{e}）— 本次中止，"
                     f"請手動刪除 {lock_file.name}")
                return None
            continue
        except OSError as e:
            warn(f"建立 venv bootstrap 鎖檔失敗（{e}）— 本次中止")
            return None
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
        except OSError:
            pass  # 互斥語意已靠 O_EXCL 原子建立達成，寫入 PID 失敗不影響本次持鎖
        return fd
    return None


def release_bootstrap_lock(fd: int, lock_file: Path) -> None:
    """釋放 venv bootstrap 互斥鎖（P1-3）；釋放失敗不該讓整體流程失敗，故吞 OSError。"""
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        lock_file.unlink()
    except OSError:
        pass


def parse_lock_pids(text: str) -> list[int] | None:
    """解析鎖檔內容為 PID 清單（MUST FIX #2：SA + QA 各自獨立重現的 P1 ——多孫
    行程同時存活時，鎖檔若只記錄單一 PID，其中一個死亡就會讓整把鎖被誤判陳舊，
    即使其他孫行程仍存活繼續寫 .venv）。

    鎖檔格式改為 JSON 陣列（如 `[123, 456]`），取代先前的單一整數純文字。純
    整數本身即合法 JSON scalar，故舊格式（單一 PID 純文字，如首次
    `acquire_bootstrap_lock()` 寫入 orchestrator PID 時）天然可被本函式解析
    為單元素清單，不需要額外的雙格式分支。解析失敗或內容並非 int / int 陣列
    時回傳 None，呼叫端須視為「無法辨識」（比照修復前對非數字內容的處理，不
    可裸崩潰也不可誤判為可清除）。
    """
    try:
        data = json.loads(text.strip())
    except (ValueError, AttributeError):
        return None
    if isinstance(data, bool):
        return None  # bool 是 int 子類別，明確排除避免誤判
    if isinstance(data, int):
        return [data]
    if isinstance(data, list) and all(
            isinstance(x, int) and not isinstance(x, bool) for x in data):
        return data
    return None


def record_lock_pids(fd: int, pids: list[int]) -> None:
    """bootstrap 子行程啟動後（或偵測到存活孫行程後），把鎖檔內容改寫成目前
    需要追蹤存活的 PID 清單（MUST FIX #2）。

    背景：先前 `_record_lock_pid(fd, pid)` 只能記錄單一 PID——orchestrator
    被 SIGKILL 後子行程變孤兒仍會寫入 .venv 是前一輪修的問題；本輪 SA/QA 各自
    重現的是「直接子行程一次 fork 出多個孫行程（如真實 uv 內部平行化下載/
    建置），只記錄 min(live) 其中一個」——短命的那個一死，鎖就被誤判全數陳舊。
    改為記錄完整清單，任一仍存活都要能被 `peek_bootstrap_lock()` /
    `acquire_bootstrap_lock()` 偵測為忙碌。
    """
    try:
        payload = json.dumps(sorted(pids)).encode("utf-8")
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, payload)
    except OSError:
        pass  # 寫入失敗最壞情況退回記錄先前內容，不影響鎖的原子建立語意


def peek_bootstrap_lock(lock_file: Path) -> int | None:
    """非破壞性檢查：鎖是否被目前仍存活的行程持有（不嘗試取鎖/不清理陳舊鎖，
    純讀取判斷）。回傳其中一個存活 PID（供警告訊息沿用既有格式）或 None。

    P1（Architect + SA 複審實測重現）：`acquire_bootstrap_lock()` 只在
    `reason is not None`（需要跑 bootstrap）時才會被呼叫，但 `prev is None`
    （既有 .venv 沿用、只記首次依賴基準）分支完全不設 reason、也就完全不會
    取鎖——orchestrator 被 SIGKILL 後孤兒子行程仍在寫 .venv，使用者重跑若
    恰好落入這個分支，鎖形同虛設。本函式在 step_venv() 最開頭無條件檢查，
    不論後續走哪個分支都能攔下。

    MUST FIX #2：鎖檔內容改為 PID 清單，只要其中任一 PID 仍存活就視為忙碌，
    不可只看清單中的某一個。

    MUST FIX A：存活判斷改用 `lock_target_alive()`（見該函式 docstring）——
    POSIX 上鎖檔可能記錄的是一個 process group id（直接子行程已死但孫行程
    仍存活時，單純 `pid_alive()` 會誤判為陳舊）。
    """
    try:
        text = lock_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    pids = parse_lock_pids(text)
    if pids is None:
        return None
    alive = sorted(p for p in pids if lock_target_alive(p))
    return alive[0] if alive else None
