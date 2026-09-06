# 排程後端 —— 純函式子集（截止時刻判斷／回讀差異比對／列舉解析／安全名檢查／稽核落檔）。
#
# 本檔是 `tools/lib/schedule_backend.py` 依內聚子功能拆出的一半（該檔 LOC 分級收斂：
# guardrail_lib ≤400 行棘輪，見 `check_loc_budget.py` 的 `[ROOT-TOOLS-WARN]`）。搬到這裡的
# 六支全部是**純函式**（紅綠由呼叫端注入自證），且**沒有一支依賴** `schedule_backend.py`
# 裡任何會被測試 monkeypatch 的模組層可變狀態（`_run`／`LAUNCH_AGENTS_DIR`）——那兩者
# 之所以留在原檔，是因為 `tools/tests/test_mac_endurance_r83.py` 對它們做的是
# `sb._run = fake`／`sb.LAUNCH_AGENTS_DIR = tmp` 這種**模組屬性覆寫**，而 `LaunchdBackend`
# 的方法體內用的是裸名參照——裸名在**定義它的那個模組**的全域字典裡查，搬走 `LaunchdBackend`
# 本身會讓那個查找換一個字典，monkeypatch 覆寫的是舊字典、讀的人卻已經是新字典，覆寫因此
# 靜默失效。這六支函式沒有這個問題：它們不讀任何模組層可變狀態，`schedule_backend.py` 對
# 它們一律用 `from schedule_backend_calendar import ...` 重新綁進自己的全域（與
# `tools/lib/sentinel_lifecycle_arm.py` 的既有手法同型），呼叫端（留在原檔的
# `LaunchdBackend`／`SchtasksBackend` 方法）看到的仍是同一個函式物件，簽章與行為不變。
#
# `_cal_text` 刻意**沒有**搬過來：它依賴 `schedule_backend._CAL_KEYS`，而那個常數同時被
# 留在原檔的 `LaunchdBackend._readback` 用裸名讀取。搬走 `_cal_text` 但留住 `_CAL_KEYS`
# 需要兩檔互相 import（可行但兩個家會共同持有一份知識），搬走兩者又會讓 `_readback`
# 多一層 import 只為兩行程式碼——兩種代價都大於它省下的行數，故原地不動。
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path


# label／檔名安全閘：帶路徑分隔符或空白的 label 一律拒絕。
# 理由與 planner 的 `_ps_single_quote` 同源（工作名是外部輸入，`--task-name` 由人直接
# 給）：這裡的 label 會直接變成 `~/Library/LaunchAgents/<label>.plist` 的檔名，含 `/`
# 就能寫到目錄外去。純白名單式的拒絕比跳脫簡單，且 label 本來就不需要那些字元。
def _unsafe_name(task_name: str) -> bool:
    return (not task_name or task_name in (".", "..")
            or any(ch in task_name for ch in "/\\ \t\n\r"))


# 把列舉輸出收成工作名清單。兩個後端**共用**這一支的理由是它們的輸出恰好同形：
# `launchctl list` 是 `PID\tStatus\tLabel` 三欄，`Get-ScheduledTask` 那一側一行就是一個名字
# ⇒ 取最後一欄兩邊都成立。前綴過濾在這裡做一次（不是兩份），呼叫端因此拿到的一律是名字。
def _labels_with_prefix(text: str, prefix: str) -> list[str]:
    names = [line.split("\t")[-1].strip() for line in text.splitlines()]
    return [name for name in names if name.startswith(prefix)]


# 「這個時刻值不值得一個 `StartCalendarInterval`」＝本檔唯一的判準點。回 `None` 表示
# 「巡邏底盤已經夠了」，回 dict 表示「這是一個真的截止時刻」。純函式 ⇒ 紅綠可注入自證。
#
# 🔴 門檻取 `> interval` 而不是「有時刻就寫」，理由是**風險**不是美感：寫進 calendar 就
# 代表下一次 `arm()` 的回讀會不符 ⇒ 要走一輪 bootout+bootstrap，而那是整條鏈上唯一會讓
# 哨兵消失的動作。巡邏那一支的 `at` 恆為 `now + interval`（`sentinel_decide` 建構它），
# 落在門檻之外 ⇒ 巡邏永遠走冪等路徑、一次都不動排程器。`TRANSIENT_RETRY_SECONDS`（300s）
# 也落在門檻之外，代價（重試慢最多 10 分鐘）已登記在 `schedule_backend.py` 檔頭。
#
# 🔴 `Month`／`Day` 一起釘住，不是只寫 Hour/Minute：只給時分的 `StartCalendarInterval`
# 是**每天**都會觸發的（`install_mac_nightly.sh` 的 nightly 正是要那個語意），而這裡要的是
# 「某一個特定時刻」。多釘兩個鍵讓它退化成一年一次，殘留的那一次也落在哨兵早已解除之後。
#
# 🔴 **只往後取整，絕不提早**（`+59s` 再切掉秒）：calendar 是分鐘粒度，而截止時刻的語意是
# 「在這之前額度還沒回來」⇒ 提早觸發會白燒一次探測，而探測是這整套唯一花 token 的動作。
#
# 🔴 DEF-200-268（2026-09-05 17:57:03 實跡）——`<= interval ⇒ None` 這條捷徑在**截止前最後
# 一格**是錯的：前七個 tick 已把 18:02 排進 calendar（launchd 六次自報 descriptor），最後一格
# 距截止 297s ≤ 900 ⇒ 本函式回 None ⇒ `_descriptor_problems` 判「要求無、回讀有」不符 ⇒
# bootout+bootstrap 把 18:02 拆掉、`StartInterval` 從 17:57:04 重計 ⇒ 18:12:04 才醒（死等
# 12 分 4 秒）。本函式**刻意不改**（TRANSIENT 300s 省 relaunch 的意圖仍成立）；那一格由
# `LaunchdBackend.arm()` 以 `_calendar_still_ahead` 保留 live calendar 補上——「最壞死等
# ≤60 秒」（`schedule_backend.py` 檔頭）的適用條件因此是兩格合起來才成立：截止距今 > interval
# 時由本函式寫 calendar 保證；≤ interval 的最後一格由 `arm()` 不拆已排時刻保證。
def _calendar_of(at: datetime | None, interval: int) -> dict | None:
    if at is None or (at - datetime.now(at.tzinfo)).total_seconds() <= interval:
        return None
    at = (at + timedelta(seconds=59)).replace(second=0, microsecond=0)
    return {"Month": at.month, "Day": at.day, "Hour": at.hour, "Minute": at.minute}


def _calendar_still_ahead(cal: dict | None, interval: int, now: datetime | None = None) -> bool:
    """launchd 回讀的 calendar 是否**仍在未來、且距今 ≤ interval**（＝截止前最後一格）。

    純函式（`now` 可注入）。descriptor 沒有年份：先取今年，落在過去就試明年（跨年那一格
    ≤ interval 才可能為真）。已過去／> interval／缺鍵／無效日期一律 False ⇒ 呼叫端照舊
    走「殘留 ⇒ 不符 ⇒ 重載」（`test_red_a_stale_moment_left_behind_is_not_a_credential`
    的方向不變）。
    """
    if not cal or any(key not in cal for key in ("Month", "Day", "Hour", "Minute")):
        return False
    now = datetime.now().astimezone() if now is None else now
    try:
        moment = now.replace(month=int(cal["Month"]), day=int(cal["Day"]), hour=int(cal["Hour"]),
                             minute=int(cal["Minute"]), second=0, microsecond=0)
        if moment < now:
            moment = moment.replace(year=now.year + 1)
    except ValueError:
        return False
    return 0 < (moment - now).total_seconds() <= interval


def _first_int(text: str) -> int | None:
    for token in text.replace("=", " ").split():
        if token.isdigit():
            return int(token)
    return None


def _descriptor_problems(live: dict, want_argv: list[str], want_interval: int,
                         want_path: str | None = None,
                         want_cal: dict | None = None) -> list[str]:
    """回讀值與請求值的差異清單（空＝憑證的第 ② 件成立）。純函式，紅綠由注入自證。"""
    problems = []
    # 🔴 calendar 這一格**雙向**都要判。少了「要求沒有、回讀卻有」那一向，一支殘留著舊
    # 截止時刻的 job 會被判成相符 ⇒ 憑證說「參數就是我要的那組」，而它其實還會在去年的
    # 那個時刻醒來。單向判準在這裡就是 R83 `verify_cli` 那個「憑證不回答那個問題」的重演。
    if dict(live.get("calendar") or {}) != dict(want_cal or {}):
        problems.append(f"StartCalendarInterval 回讀 {live.get('calendar')!r}，請求 {want_cal!r}")
    if live.get("interval") != want_interval:
        problems.append(f"run interval 回讀 {live.get('interval')!r}，請求 {want_interval}")
    if list(live.get("argv") or []) != list(want_argv):
        problems.append(f"argv 回讀 {live.get('argv')!r} 與請求不符")
    path = str(live.get("path") or "").strip()
    if not path:
        problems.append("launchd 沒有回報 plist path ⇒ 無法證明它已持久化")
    elif want_path is not None and path != want_path:
        # launchd 載入的來源不是我們剛寫的那一份 ⇒ 這支 job 是別的東西建的，我們對它的
        # 內容一無所知。**不接受**：憑證第 ③ 件說的是「這一份已持久化」，不是「有一份」。
        problems.append(f"launchd 載入的 plist 是 {path!r}，不是 {want_path!r}")
    return problems


def _append_trace(path: Path, record: dict) -> None:
    record = {**record, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
