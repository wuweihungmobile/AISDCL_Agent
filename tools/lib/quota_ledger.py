"""額度軸的**跨行程原語**：派發帳、TTL 名額、降級痕跡。

WHY 新開這一支檔（本 repo 判過「護欄層自我增殖是最大缺陷來源」，新檔必須辯護）
------------------------------------------------------------------------------
① **消費端塞不下**。`.claude/hooks/context_budget_guard.py` 落地當回合 raw 1,634 行、
   `check_loc_budget.py` 的 `SPECIAL_FILES` 棘輪門檻也是 1,634（餘裕 0）⇒ 那是硬牆。
   本檔搬走的是**實作**（原地留委派），淨效果是消費端變短，不是變長。
   🔴 R84／ARCH-03 訂正這兩個數字的**性質**（結論不變）：1,634 是**立案當時**的量測值，
   本段此前把它寫成現況 ⇒ 已過期（R84 實測：該檔 raw 1,089、棘輪門檻同輪重釘為 1,089，
   餘裕仍是 0 ⇒ 牆一樣硬，只是位置往下移了）。一律現查：
   `python AutoClaude/tools/check_loc_budget.py --json` 的 `special_files` 那一格。
② **這一層的失效模式與消費端不同**。hook 的判讀要快、要確定性；本檔處理的是
   「N 個行程同時碰同一個檔」，它的失效是**機率性**的、只在併發下出現、而且靜默。
   兩種東西混在一個檔裡的代價已經量到了（見下方 R81 那段實測）。
③ ~~**它有第二個消費者**。`tools/session_resume_planner.py`（哨兵巡邏）與未來的
   AutoClaude adapter 需要同一組原語；複製一份就是本 repo 的頭號病。~~
   🔴 **R84／ARCH-03：這一條當時是預測，今天是假的，故劃掉而不是留著當理由。**
   實測（`grep -rn "import quota_ledger" tools .claude AutoClaude`）唯一的生產消費者是
   `tools/lib/quota_gate.py`；planner 一次都沒 import 它，AutoClaude adapter 也沒有
   （它走的是**檔案契約**，見 `AutoClaude/.importlinter` 明文禁止引擎 import 根層護欄層
   ⇒ 那個「第二個消費者」在架構上結構性地不會出現）。
   ⇒ 本檔今天的存在理由**只剩 ①②**（消費端硬牆 ＋ 併發失效模式不同），而那兩條仍然成立
   且各自有實測支撐。把一條已被證偽的理由留在檔頭的代價已經發生：R84 的架構複審據此
   提出「合併 quota_ledger 進 planner」的選項 (ii)，而那個合併會製造一條新的跨層邊
   （planner→ledger 今天不存在）＝以減法為名的加法。
   誠實劃界：本條被證偽**不等於**本檔該被合併掉——① 那道牆今天仍在（現查上一格）。

🔴 R81 收斂立案（SD-B1／SD-B3，兩支多行程 barrier 探針實測）
-------------------------------------------------------------
舊實作用 `path.open("a")` 一行一行 append，並以 `try`／`undo` 兩筆記錄對消。
**Windows CRT 的 append 是「seek 到檔尾再寫」，跨行程不是原子的**，代價當回合量到：

    8 行程 × 40 筆（壁鐘 barrier 對齊）
      舊實作 `path.open("a")`            expected=320 lines=221 LOST=99 (30.9%)
      `os.open(O_APPEND)` ＋單次 os.write expected=320 lines=281 LOST=39 (12.2%)
      `msvcrt.locking(LK_LOCK)`          N=8 時 LOST=0，**N=20 時 10 個行程直接死在
                                         `OSError: Resource deadlock avoided`**（它內建
                                         只重試 10 次 × 1 秒，超過就拋）
      本檔（目錄項）                      8×40／20×40／42×10 三組皆 **LOST=0 torn=0**

⇒ 三個結論，每一個都與「照 SD 的 required_change 直接做」不同，故照實寫下：
  · `os.O_APPEND` ＋單次 `os.write` **治不好**這件事（少掉一半，仍掉 12%）——Windows 的
    CRT 把那個旗標實作成使用者態的 seek＋write，不是核心層的原子 append。
  · 檔案鎖能治，但它自己會變成**新的故障源**（高併發下整個行程死掉），而這支東西
    住在 hook 的關鍵路徑上、`.claude/settings.json` 記載過 P0「hook 誤觸會把所有工具
    硬鎖死」⇒ 一個會在忙的時候拋例外的鎖是不能收的。
  · **一次派發＝一次目錄項建立**才是這台機器上真的原子的東西（`O_CREAT|O_EXCL`）。
    順帶治掉三件事：記錄沒有內部結構 ⇒ 結構上不可能「撕行」；撤銷＝`unlink` 自己那一個
    目錄項（不是第二次 append，不必依賴另一次寫入成功）；計數不必開檔（時刻寫在名字裡）。

誠實劃界
--------
`append_record()`（降級痕跡那一支）**仍然**是 `O_APPEND` ＋單次 `os.write`，也就是說
它在同一瞬間 N 個行程同時寫時仍可能掉行。這是刻意的取捨而不是漏看：痕跡檔要能被人
`Get-Content` 直接讀，做成目錄就不可讀了；而「出聲」這件事**不依賴它**——stderr 是
per-process 的，結構上掉不了。痕跡是事後可稽核的那一半，不是唯一那一半。
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

_T = TypeVar("_T")

#: `O_BINARY` 只有 Windows 的 `os` 有（鐵律三：「這在另一個平台是什麼值」）。
#: POSIX 取 0 ＝不加任何旗標，那正是 POSIX 上正確的值。
_BINARY = getattr(os, "O_BINARY", 0)

#: 目錄項的副檔名。名字的形狀是 `<毫秒>-<pid>-<亂數>.dispatch`，**時刻寫在名字裡**
#: ⇒ 計數只要 `scandir`，一個檔都不必開。
ENTRY_SUFFIX = ".dispatch"

#: 目錄項建立的重試次數。撞名只會來自「同一毫秒、同一 pid、4 bytes 亂數也撞」，
#: 機率極低；給 8 次是為了讓「撞了」有可觀測的上界，而不是無限迴圈。
_MAX_NAME_ATTEMPTS = 8


def _entry_name(when: float) -> str:
    return (f"{int(when * 1000):015d}-{os.getpid()}-"
            f"{os.urandom(4).hex()}{ENTRY_SUFFIX}")


def entry_moment(name: str) -> float | None:
    """從目錄項名字讀回它的時刻（epoch 秒）；`None`＝這個名字不是本模組寫的。

    回 `None` 的東西**不得被靜默丟掉**（見 `count_dispatches` 的第二個回傳值）：
    「讀不懂的記錄」與「沒有記錄」混同，正是本 repo 通篇在防的 fail-open 形狀。
    """
    head = name.split("-", 1)[0]
    if not name.endswith(ENTRY_SUFFIX) or not head.isdigit():
        return None
    return int(head) / 1000.0


def claim_dispatch(root: Path, when: float) -> Path | None:
    """記一筆派發，回它自己的那一個目錄項；`None`＝寫不進去（不得升級為守衛失敗）。"""
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    for _ in range(_MAX_NAME_ATTEMPTS):
        path = root / _entry_name(when)
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY, 0o600))
        except FileExistsError:
            continue
        except OSError:
            return None
        return path
    return None


def release_dispatch(entry: Path | None) -> bool:
    """把自己那一筆撤掉；回「撤成功了沒」。

    被擋下的呼叫不得在帳上留下永久佔位（SA-B6），而**這一次撤銷刪的是自己剛剛用
    `O_EXCL` 建出來、沒有第二個行程碰得到的目錄項** ⇒ 與舊版「再 append 一筆 undo」
    不同，它不會被別人的寫入覆蓋掉。刪失敗時最壞情況同舊版：那一格隨視窗滾動自癒。
    """
    if entry is None:
        return False
    try:
        entry.unlink()
    except OSError:
        return False
    return True


def count_dispatches(root: Path, floor: float) -> tuple[int, int]:
    """`(視窗內還算數的筆數, 讀不懂的目錄項數)`。目錄不存在＝`(0, 0)`。

    第二個回傳值是 SD-B1 required_change ② 的落點：舊版 `live_dispatches` 對解析
    失敗的行 `except ValueError: continue`，於是**撕行被靜默丟棄**——帳目變小的方向
    正好是「看起來還有預算」。這裡把它算出來交給呼叫端去出聲。
    """
    live = unreadable = 0
    try:
        entries = list(os.scandir(root))
    except OSError:
        return 0, 0
    for entry in entries:
        moment = entry_moment(entry.name)
        if moment is None:
            unreadable += 1
        elif moment >= floor:
            live += 1
    return live, unreadable


def prune_dispatches(root: Path, floor: float) -> int:
    """清掉已經滾出視窗的目錄項；回清掉幾個。append-only 不等於永遠長大。

    刻意**只刪滾出視窗的**（不刪讀不懂的）：讀不懂的那些是唯一還看得見「有東西壞掉」
    的證據，清掉它等於把 `count_dispatches` 的第二個回傳值歸零，那就是自己把訊號抹掉。
    """
    gone = 0
    try:
        entries = list(os.scandir(root))
    except OSError:
        return 0
    for entry in entries:
        moment = entry_moment(entry.name)
        if moment is None or moment >= floor:
            continue
        try:
            os.unlink(entry.path)
        except OSError:
            continue
        gone += 1
    return gone


def claim_once(stamp: Path, ttl: float, now: float | None = None) -> bool:
    """本 TTL 視窗內**第一個到的人**回 `True`，其餘一律 `False`。

    🔴 SD-B3：舊實作是 check-then-act（先 `is_file()` ＋ 比 mtime，再 `write_text`），
    零原子性 ⇒ 16 個 barrier 對齊的行程實測 **CLAIM=16 SKIP=0**（設計意圖 1）。
    用 `Pool.map` 量會得到 1，因為行程啟動被錯開了——那正是既有測試看不到它的原因。

    正解是把「佔位」這件事本身變成一次 `O_CREAT|O_EXCL`：
      · 沒有 stamp ⇒ N 個行程一起 `O_EXCL` 建，核心保證恰好一個成功。
      · 有 stamp 且還新鮮 ⇒ 直接 `False`，一個系統呼叫都不多花。
      · 有 stamp 但已過期 ⇒ 先 `unlink`；**只有 unlink 成功的那一個**有資格往下建，
        其餘會拿到 `FileNotFoundError` 而退出 ⇒ 過期換屆時同樣恰好一個。
    """
    now = time.time() if now is None else now
    try:
        age: float | None = now - stamp.stat().st_mtime
    except OSError:
        age = None
    if age is not None:
        if age < ttl:
            return False
        try:
            stamp.unlink()
        except OSError:
            return False  # 別人先把它刪掉了 ⇒ 這一屆不是我的
    try:
        os.close(os.open(stamp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY, 0o600))
    except OSError:
        return False
    return True


def append_record(path: Path, record: dict) -> bool:
    """把一筆記錄以**單次 `os.write`** append 上去；回「寫進去了沒」。

    單次 write 是這裡做得到的最好的一件事（見模組 docstring 的〈誠實劃界〉：它仍會在
    密集併發下掉行）。`newline` 由我們自己控制成 `\\n`——本 repo 判過「Python 寫檔不
    指定 newline，Windows 會寫出 CRLF」，而這個檔會被 `json.loads` 逐行讀。
    """
    try:
        data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    except (TypeError, ValueError):
        return False
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | _BINARY, 0o600)
    except OSError:
        return False
    try:
        os.write(fd, data)
    except OSError:
        return False
    finally:
        os.close(fd)
    return True


#: 鎖檔多久沒人碰就視為孤兒（持有者中途死掉、沒機會 `unlink`）——同 `claim_once()` 的
#: TTL 判斷精神，不會讓一個死掉的持有者把鎖永久卡死。
LOCK_STALE_AFTER_SECONDS = 5.0
#: 等鎖的總時限（壁鐘秒）。過了這個時限仍拿不到 ⇒ fail-open 直接跑 `fn()`（見
#: `with_lock` docstring：一個會讓 hook 卡死的鎖比沒有鎖更糟，同本檔 R81 對
#: `msvcrt.locking` 的既有判定）。
_LOCK_MAX_WAIT_SECONDS = 10.0
_LOCK_POLL_SECONDS = 0.005


def with_lock(lock_path: Path, fn: Callable[[], _T], *,
              stale_after: float = LOCK_STALE_AFTER_SECONDS,
              max_wait: float = _LOCK_MAX_WAIT_SECONDS) -> _T:
    """在 `lock_path` 這個互斥點上 serialize 呼叫 `fn()`；回 `fn()` 的回傳值。

    🔴 立案（R102／PRD §4.2.4 R7 明文：「多個 hook 行程並行是已觀測輸入形態……⇒  round-label-ok
    **不得**自己寫 check-then-act」）：`quota_availability.evaluate()`／
    `quota_stability.evaluate()` 都是「讀狀態 → 算下一步 → 寫回」——寫入本身已經是
    原子換名（`tmp → fsync → replace`），但**整段**讀-算-寫之間沒有互斥：兩個行程可以
    同時讀到同一份舊值、各自算完，後寫的覆蓋先寫的（遺失更新），與本模組 docstring
    引用的 `claim_refresh_slot()` 事故同型（`CLAIM=16 SKIP=0`）。

    🔴 為什麼不用 `fcntl.flock`／`msvcrt.locking`（本檔 R81 立案已經測過、且判定不收）：
    那兩支在高併發下會直接把行程拋例外弄死（`msvcrt` 實測 N=20 時 10 個行程直接死在
    `Resource deadlock avoided`）——落在 hook 的關鍵路徑上，一個會讓行程掛掉的鎖比沒有
    鎖更糟。改用與 `claim_once()` 同款的 `O_CREAT|O_EXCL` 目錄項當互斥點：拿不到就短睡
    重試；持有者若中途死掉沒機會 `unlink`，鎖檔會變成孤兒——用 `stale_after` 把它視為
    過期並強制回收，不會永久卡死。等到 `max_wait` 仍拿不到（理論上只會發生在
    `stale_after`／`max_wait` 設反或系統時鐘異常這類設定錯誤）⇒ **fail-open**：不加鎖
    直接跑 `fn()`，寧可偶爾遺失一次更新也不讓整個工具呼叫卡住（同本 repo 對
    `append_record()` 掉行的既有取捨：「痕跡是事後可稽核的那一半，不是唯一那一半」，
    這裡的等價說法是「多數時候被鎖治好，極端情況下退回舊風險，不是新增一個更糟的
    故障源」）。
    """
    deadline = time.time() + max_wait
    while True:
        try:
            age = time.time() - lock_path.stat().st_mtime
        except OSError:
            age = None
        if age is not None and age >= stale_after:
            try:
                lock_path.unlink()
            except OSError:
                pass
        try:
            os.close(os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY, 0o600))
        except OSError:
            if time.time() >= deadline:
                return fn()  # fail-open：見上方 WHY，等鎖等到超時也不能讓呼叫端卡死
            time.sleep(_LOCK_POLL_SECONDS)
            continue
        try:
            return fn()
        finally:
            try:
                lock_path.unlink()
            except OSError:
                pass
