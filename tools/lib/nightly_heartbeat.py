"""nightly 去重鎖偵測＋launchd 排程查核＋心跳哨兵的本體（DEF-101-398）。

原棲身 `tools/dev_start.py`（SPECIAL_FILES raw-line 棘輪）；結構性長債 DEF-101-398 的另一半
（另一半＝`bootstrap_lock.py`）。形態照 `ci_run_status.py`（DEF-101-758 先例）：邏輯本體住本模組，
`dev_start.py` 只留同名別名與轉呼叫。

🔴 純搬移、行為逐位元不變。與搬遷前唯一的差異是**依賴注入**：原本讀 module-level `ROOT`／
`_warn`／`_flavor()`／`_pid_alive`／`_HEARTBEAT_MAX_AGE_DAYS`／`_launchd_plist_target`／
`_launchd_nightly_loaded` 的函式改收參數。`tools/tests/test_dev_start.py` 以
`mock.patch.object(dev_start, …)` 對這些名字打樁，打樁點必須留在呼叫端——`dev_start.py` 的同名
轉呼叫在**呼叫當下**才解析它們，既有打樁照舊生效。

字面量契約（改任一端必須同步另一端，否則偵測靜默失效）：
  · `NIGHTLY_MUTEX_NAME`／`NIGHTLY_POSIX_LOCK`＝nightly 腳本自己持有的去重鎖名稱／路徑
    （`AutoClaude/tools/run_local_nightly.ps1`／`.sh`）。
  · 心跳檔名 `nightly_latest.log`（Windows）／`nightly_mac_latest.log`（mac／posix）＝寫端是上列
    兩支腳本；機械鎖＝`tools/tests/test_dev_start.py::TestNightlyHeartbeatFilenameContract`。

平台分支（mac 上只能以 mock 驗證 Windows 側，Windows 真機未實跑）：`nightly_running`（Windows 走
具名 Mutex／ctypes、POSIX 走 mkdir 鎖＋pid 存活）、`launchd_nightly_loaded`（僅 darwin）、
`check_nightly_heartbeat`（flavor 決定心跳檔名與 FAIL 偵測方式）。

🔴 葉節點模組：只被 `tools/dev_start.py` import，只依賴同層共用層 `platform_utils`。
"""

from __future__ import annotations

import ctypes
import plistlib
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import platform_utils

# nightly 去重鎖的權威名稱／路徑（**非**本檔自建，是 nightly 腳本自己持有的鎖）：
#   Windows：AutoClaude/tools/run_local_nightly.ps1 的具名 Mutex
#   mac/posix：AutoClaude/tools/run_local_nightly.sh 的 mkdir atomic lock（內含 pid 檔）
# 改這兩個字面量必須同步改那兩支腳本，否則偵測靜默失效（回 False＝假「沒在跑」）。
NIGHTLY_MUTEX_NAME = "Global\\AutoClaude_Nightly_Run"
NIGHTLY_POSIX_LOCK = "AutoClaude/logs/.nightly_mac.lock"


def nightly_running(
    root: Path,
    mutex_name: str,
    posix_lock: str,
    pid_alive: Callable[[int], bool],
) -> bool | None:
    """本機是否有 nightly 正在跑：True＝在跑／False＝沒在跑／None＝無法判定。

    WHY（DEF-101-504，2026-07-27 Windows 實機事故）：本機 nightly 走 schtasks 補跑
    （StartWhenAvailable／WakeToRun），機器一喚醒就補跑——而那正是使用者開工、
    照 useMacWin.md 提示詞做 `git merge --ff-only` 的同一分鐘。當天實測：merge
    在 18:41:26 落在 nightly local-ci-gate 的 pytest 執行區間（18:41:10~18:42:50）
    中間，113 個檔案在測試跑到一半時被抽換 → 5 支測試假紅（事後單獨重跑 10
    passed 全綠）。假紅還會被寫進 nightly_latest.log，讓**之後每天早上**的心跳
    哨兵都報「上一輪 nightly 有失敗」，把人導去追不存在的迴歸。

    偵測方式刻意查「nightly 腳本自己持有的去重鎖」而非猜 log mtime：鎖是
    nightly 行程存活期間才成立的權威訊號，行程結束（含 crash）由 OS 自動回收
    （Windows Mutex）或由 pid 存活判定排除（posix 陳舊鎖目錄）。

    回 None（無法判定）時呼叫端一律當作「沒偵測到」處理——本機制是防呆提醒，
    不該因為自己失敗就把 dev_start 弄壞或誤擋同步。
    """
    if platform_utils.is_windows():
        synchronize = 0x00100000
        try:
            handle = ctypes.windll.kernel32.OpenMutexW(
                synchronize, False, mutex_name)
        except (OSError, AttributeError):
            return None
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        # ERROR_FILE_NOT_FOUND(2)＝具名物件不存在＝確定沒在跑；其餘（如
        # ERROR_ACCESS_DENIED(5)：跨權限層級 session 開同名 Global 物件）無從
        # 判定，回 None 而非 False，避免冒充「確定沒在跑」。
        return False if ctypes.windll.kernel32.GetLastError() == 2 else None

    lock_dir = root / posix_lock
    try:
        if not lock_dir.is_dir():
            return False
        pid = int((lock_dir / "pid").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        # 鎖目錄在但 pid 檔讀不到/壞掉：可能是 .sh 剛 mkdir 完還沒寫 pid 的
        # 競態窗口，也可能是陳舊殘留——兩者無法區分，不冒充判定。
        return None
    return pid_alive(pid)


def launchd_plist_target(label: str) -> Path | None:
    """自 ~/Library/LaunchAgents/<label>.plist 取 ProgramArguments 內的 nightly 腳本路徑。

    R68：label 全機唯一，第二個 clone／搬過家的 repo 會「命中 label 但排程其實指向
    別份 checkout」。取值語意與 tools/install_mac_nightly.sh 的 `_plist_raw
    ProgramArguments.1` 相同，此處用標準庫 plistlib 直讀（不 spawn PlistBuddy）。
    """
    p = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    try:
        with p.open("rb") as f:
            args = plistlib.load(f).get("ProgramArguments") or []
    except (OSError, ValueError, AttributeError, plistlib.InvalidFileException):
        return None
    for a in args:
        if isinstance(a, str) and a.endswith("run_local_nightly.sh"):
            return Path(a)
    return None


def launchd_nightly_loaded(
    root: Path,
    label: str,
    plist_target: Callable[[str], Path | None],
) -> bool | str | None:
    """launchctl 精確查核 nightly 排程是否已載入（DEF-101-203②，純 advisory）。

    四態（R68 由三態擴充）：True＝已載入且指向本 checkout；**str＝已載入但指向
    另一份 checkout（值為該路徑）**；False＝未載入；None＝查不到（非 darwin／
    launchctl 失敗或逾時，或 plist 讀不到而無法鑑別）。launchctl list 輸出格式為
    「PID Status Label」三欄（PID 可為 `-`），第 3 欄用精確等值比對——防前綴誤中
    （如 com.autoclaude.nightly2）。
    """
    if not platform_utils.is_macos():
        return None
    try:
        r = subprocess.run(["launchctl", "list"], timeout=10, capture_output=True,
                           encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    for line in (r.stdout or "").splitlines():
        cols = line.split()
        if len(cols) >= 3 and cols[2] == label:
            target = plist_target(label)
            if target is None:
                return None  # 讀不到 plist ⇒ 無鑑別力，不得謊報「正常」
            mine = root / "AutoClaude" / "tools" / "run_local_nightly.sh"
            return True if target.resolve() == mine.resolve() else str(target)
    return False


def heartbeat_fail_count(hb: Path) -> int | None:
    """自心跳檔前 3 行抽取 FAIL 計數（ARCH-R15-1）；讀不到/無錨點回 None。

    FAIL=（heartbeat 時戳行之後的「彙總 PASS=… FAIL=…」行）恆為固定第 2 行契約；
    第 3 行僅 FAIL>0 時才存在（失敗 stage 行）。讀前 3 行足夠涵蓋兩態、且防未來
    檔案膨脹（SA-R15-REV-1 訂正：非「3 行恆存在」，regex 對缺席的第 3 行無害）。
    任何 OSError 靜默跳過——本哨兵是 advisory，絕不影響 dev_start 行為。
    """
    try:
        with hb.open(encoding="utf-8", errors="replace") as f:
            head = "".join(next(f, "") for _ in range(3))
    except OSError:
        return None
    m = re.search(r"FAIL=(\d+)", head)
    return int(m.group(1)) if m else None


# Windows 側 FAIL 內容偵測（DEF-101-200 rider ARCH-R15-1，R23 補完）：
# nightly_latest.log 是全量 log（含完整 pytest/mutmut 輸出，可能數 MB），不像
# mac 側是固定前 3 行心跳契約，故不能沿用 heartbeat_fail_count 的「讀前 3 行」
# 作法。但 run_local_nightly.ps1 收尾處本已穩定寫入一行機械可讀的終審結論
# （R9 複審 (c) 既有設計，非本輪新增）：
#   `Log 'END exit decision: exit=0 (no failed stages; SKIP/WARN 不計失敗)'`
#   `Log ("END exit decision: exit=1 (failed stages: {0})" -f (...))`
# 此行在檔案「尾端」附近（其後只剩 pointer 更新／14 天輪替兩行 advisory log），
# 故用 tail 位元組窗格讀取（避免整檔載入大型全量 log）+ regex 擷取。
WINDOWS_NIGHTLY_TAIL_BYTES = 16384
# R23 SD/QA 補完：兩邊字面量（本正則 vs run_local_nightly.ps1 的 Log(...) 呼叫）
# 目前一致，但只是巧合式耦合、沒有機械鎖——任何一方未來格式微幅漂移（多一個
# 空白、大小寫變化）都會讓本正則零比對，靜默回傳 None（假陰性：nightly 其實
# 記錄了失敗，卻不發警告，違反 fail-loud）。SD 實測命中三種偏離：冒號後多一
# 空白、`END`→`end` 小寫、`END` 後多一空白。用 `\s+`（取代固定單一空白）+
# `re.IGNORECASE`（取代大小寫敏感）換取對這類偏離的容忍度，屬 advisory 偵測用
# 途、非正式契約比對，寬容不影響本函式既有語意（仍要求完整字串結構存在）。
# R25 訂正（DEF-101-263⑤）：上述放寬移除了原本大小寫敏感字面 END 帶來的隱性
# 單字邊界效果，end 前若無邊界防護會讓任何以 end 結尾的單字（append/weekend/
# backend...）緊接 exit decision: exit=N 字面文字誤觸發。四方一審 SA 二審複核時
# 指出單純 \b 仍留一個縫：連字號結尾單字（high-end/front-end，"-" 非 \w，\b 在
# 字母與 "-" 之間仍算邊界）會被誤傷。改用負向後顧 (?<![\w-])（排除單字字元與
# 連字號兩種前置字元）一併收斂兩類假陽性；不影響任何真實 log 行命中（真實輸出
# 中 END/end 前恆為換行或空白，兩者皆不在排除集合內）。
WINDOWS_EXIT_DECISION_RE = re.compile(
    r"(?<![\w-])end\s+exit\s+decision:\s*exit=(\d+)(?:\s*\(failed\s+stages:\s*([^)]*)\))?",
    re.IGNORECASE,
)


def windows_heartbeat_fail_note(hb: Path) -> str | None:
    """Windows nightly 心跳 FAIL 內容偵測；tail 掃描既有 `END exit decision` 行。

    讀不到/無錨點 → None（advisory，絕不影響 dev_start 行為）。取最後一次命中
    （同一次 run 的 log 本只會寫入一次，多次命中純屬防禦）。exit=0 → None
    （視為全綠，不入警告）。"""
    try:
        size = hb.stat().st_size
        with hb.open("rb") as f:
            f.seek(max(0, size - WINDOWS_NIGHTLY_TAIL_BYTES))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    matches = WINDOWS_EXIT_DECISION_RE.findall(tail)
    if not matches:
        return None
    exit_code, failed_stages = matches[-1]
    if exit_code == "0":
        return None
    stages = failed_stages.strip() or "未知"
    return f"最近一輪 exit={exit_code}（failed stages: {stages}）"


def check_nightly_heartbeat(
    flavor: str,
    root: Path,
    warn: Callable[[str], None],
    max_age_days: int,
    launchd_loaded: Callable[[], bool | str | None],
) -> str:
    """nightly 心跳哨兵（R12 ARCH-R12-2，純 advisory）——回傳 summary 片段。

    WHY：launchd/schtasks 排程是否真的在跑過去零機械查核（DEF-101-164 ARCH-8），
    而 CI 停擺（DEF-101-081）期間本地 nightly 是唯一每日兜底層。nightly 腳本結尾
    寫心跳檔（windows→.ps1 既有 nightly_latest.log；mac/posix→run_local_nightly.sh
    R12 起寫 nightly_mac_latest.log），此處只做純 mtime 三態比對：
      缺席   → 提示行＋summary（不入 WARNINGS——排程未啟用是可接受狀態，但要可見）
      >8 天  → warn（advisory，不阻擋、不改 exit code）
      新鮮   → 一行 OK
    任何 OSError（外接碟抖動等）都不得讓 dev_start 失敗。"""
    name = "nightly_latest.log" if flavor == "windows" else "nightly_mac_latest.log"
    hb = root / "AutoClaude" / "logs" / name
    try:
        mtime = hb.stat().st_mtime
    except OSError:  # 缺席或不可讀 → 提示（不入 WARNINGS）
        # R15 DEF-101-203②：mac 側缺席不再停留於「雙可能」猜測——launchctl list
        # 是 read-only 精確查核，三態消歧：已載入尚未首跑＝正常／未載入＝要裝／
        # 查不到（None）＝維持下方既有雙可能文案。長解釋不再造第三份完整三態
        # 措辭，指向 install_mac_nightly.sh --status。Windows 分支完全不動
        # （schtasks 精確查核路由 DEF-101-200 Windows 輪）。
        if flavor != "windows":
            loaded = launchd_loaded()
            if isinstance(loaded, str):  # R68 四態之四：label 命中但指向另一份 checkout
                print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— "
                      f"launchd 已載入，但指向另一份 checkout（{loaded}）— 本 repo 無 "
                      f"nightly，請跑 bash tools/install_mac_nightly.sh")
                return "nightly 心跳未偵測（launchd 指向另一份 checkout，見上）"
            if loaded is True:
                print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— "
                      f"launchd 已載入、尚未跑過第一輪（正常；首輪 02:00 後產生心跳，"
                      f"詳見 bash tools/install_mac_nightly.sh --status）")
                return "nightly 心跳未偵測（launchd 已載入，尚未首跑—正常）"
            if loaded is False:
                print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— "
                      f"launchd 未載入——安裝：bash tools/install_mac_nightly.sh"
                      f"（見 ONBOARDING §8）")
                return "nightly 心跳未偵測（launchd 未載入，見 ONBOARDING §8）"
        # R14 OPT-3：補「或已安裝但尚未首跑」——launchd/schtasks 剛安裝、首輪 02:00 未到
        # 前心跳檔必然缺席，舊文案只說「未啟用」會誤導剛裝完的人（文案語意對齊
        # install_mac_nightly.sh --status）。查證指令依 flavor 給對等物（R14 一審
        # SD-R14-REV-4＋ARCH-R14-REV-5：勿讓 Windows 使用者拿到 mac-only 指令）。
        verify_cmd = (
            "schtasks /query /tn AutoClaude_Nightly"
            if flavor == "windows"
            else "bash tools/install_mac_nightly.sh --status"
        )
        print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— 排程可能未啟用，"
              f"或已安裝但尚未跑過第一輪（查證：{verify_cmd}），設定見 ONBOARDING §8；"
              f"CI 停擺期間本地 nightly 為唯一每日兜底")
        return "nightly 心跳未偵測（排程未啟用？或尚未首跑？見 ONBOARDING §8）"
    # R67-M40：先收斂為「整數秒差」再換算天數，與 installer 秒級語意對齊（1 秒窗口
    # 確定性分歧實測沿革見 CrossPlatform_Guard_Line_History.md〈dev_start 史料搬遷〉節）。
    age_days = (int(time.time()) - int(mtime)) / 86400.0
    # ARCH-R15-1：mtime 只證明「在跑」不證明「在綠」——CI 停擺期間 nightly 是唯一
    # 每日活體，連續全紅時晨間 dev_start 仍 ✅ 是盲區。心跳存在（新鮮或過期皆檢查）
    # 時依平台分讀：mac 是固定前 3 行心跳契約（heartbeat_fail_count）；Windows
    # 側 nightly_latest.log 是全量 log 非 3 行契約，改 tail 掃描既有
    # `END exit decision` 收尾行（R23 補完，見 windows_heartbeat_fail_note）。
    fail_note = ""
    if flavor != "windows":
        fail_n = heartbeat_fail_count(hb)
        if fail_n is not None and fail_n > 0:
            warn(f"nightly 最近一輪有 FAIL={fail_n}（AutoClaude/logs/{name}）——"
                 f"排程在跑但驗證未全綠，請查 AutoClaude/logs/ 最新 nightly_mac log"
                 f"（ARCH-R15-1）")
            fail_note = f"；最近一輪 FAIL={fail_n}（見警告）"
    else:
        win_fail = windows_heartbeat_fail_note(hb)
        if win_fail is not None:
            warn(f"nightly 最近一輪有失敗（AutoClaude/logs/{name}）——{win_fail}，"
                 f"排程在跑但驗證未全綠，請查 AutoClaude/logs/ 最新 nightly log"
                 f"（ARCH-R15-1）")
            fail_note = f"；{win_fail}（見警告）"
    if age_days > max_age_days:
        # R67-M39：文案不再內嵌不等式。`{age_days:.1f}` 只有一位小數，判定卻是秒級，
        # 年齡落在 [8.0, 8.05) 天時舊文案會印出「8.0 天 > 8 天」這種數學上為偽的句子
        # （install_mac_nightly.sh 同型窗口更寬達 24 小時）。改為敘述句後，顯示精度
        # 與判定精度不一致就不會再讓文案自相矛盾。兩站點同步改，維持語意對齊。
        warn(f"nightly 心跳過期（AutoClaude/logs/{name} 距今 {age_days:.1f} 天，"
             f"已超過 {max_age_days} 天門檻）— 排程可能已停擺，"
             f"請檢查 launchd/schtasks（ONBOARDING §8）")
        return f"nightly 心跳過期（{age_days:.1f} 天，見警告）{fail_note}"
    print(f"    ✅ nightly 心跳新鮮（AutoClaude/logs/{name}，距今 {age_days:.1f} 天）")
    return f"nightly 心跳新鮮{fail_note}"
