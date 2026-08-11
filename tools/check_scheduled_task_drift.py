#!/usr/bin/env python3
"""線上 schtasks 排程設定漂移偵測器（R74 / ADR-SD09-012 §8.2 的機械化）。

為何存在（Rule 9 — 這支不是美化，是補一個結構性失明）：
    ADR-SD09-012 §8.2 於 2026-08-03 就實測列出五項排程設定落差，而它連續三輪
    （R71/R72/R73）原封不動存活且**沒有任何東西轉紅**。機械成因不是沒人細心：
    線上排程只以「機器狀態」存在，repo 裡沒有任何一份檔案是它們，於是也就沒有
    任何檢查器有對照組可比。本檔＝比對器，對照組＝tools/scheduled_task_expectations.json。

判準（刻意設計成 CI 安全，但「任務不見了」必須非綠）：
    · 非 Windows                → SKIP，rc=0（macos/ubuntu CI 不得因此轉紅）
    · 受管任務**全部**不存在    → SKIP，rc=0（本機未安裝排程／CI runner 的正常狀態）；
                                   帶 --require-installed 則改判 TASK_MISSING、rc=1
    · **部分**存在、部分不存在  → TASK_MISSING，rc=1  ← R75 補登記的一格
    · 任務存在但設定不符期望    → DRIFT，rc=1
    · 任務存在但讀不到設定      → ERROR，rc=1（fail-closed：量不出來不得當成沒問題）

🔴 R75：為何要多一個狀態字，而不是把「部分缺席」折進 DRIFT（SD 複審 blocking）：
    落地首版只登記了「全缺席＝skip」與「存在但設定不符＝drift」兩格，「部分存在」
    這一格**沒有登記、沒有判準、也沒有測試**——實測「一支設定完美 ＋ 一支整支不存在」
    回 status=ok、rc=0、drifts=[]，人類可讀輸出還照實印「不存在（未安裝）」，
    也就是**印得出來卻判它綠**。本偵測器要守的是「排程會不會漏跑」，而「任務不見了」
    是漏跑的最強形態（R71 就真的從本機移除過一支 AutoClaude* 任務），卻是它唯一
    看不到的形態。
    不折進 DRIFT 的理由是**接線層的處置不同**：run_local_nightly.ps1 對 `status=drift`
    設了一條具名豁免（DEF-101-794 那五項設定的修法需系統管理員提權，故只 WARN、
    不計入 finalFailures），而該豁免的射程是「設定值不對」。任務整支不見的修法完全
    不同（重跑安裝器註冊回來，不需要等提權），不該搭那條豁免的便車——那等於把最強
    的漏跑訊號從 exit code 上拿掉，缺陷只是往上搬一層。該接線層對狀態字採**白名單
    fail-closed**（`-notin @('drift','ok','skip')` 即計失敗，明文寫「含未來新增的
    狀態字」），所以新狀態字自動落在「計失敗」那一側——這是它設計好的擴充點。

🔴 R75：「全缺席＝skip」為何**維持**預設 skip（同一次複審的第二問）：
    偵測器在「全缺席」這個 vantage point 上沒有任何證據能區分「這台機器從沒裝過」
    與「兩支都被移除了」——把它判紅會讓每個 CI runner 與每個 fresh clone 永久紅，
    而人的反應是把檢查關掉（＝把剛補上的偵測管道又拆了）。而且這一格在**自動偵測上
    本來就是空的**：受管的兩支任務裡有一支就是 nightly 自己，兩支都不見時已經沒有
    任何排程載具會跑到本偵測器。故正解不是改預設，而是給「知道自己該有排程」的機器
    一個顯式開關：`--require-installed`（人工／push 前閘門可用），把這個無法由預設值
    關閉的缺口變成可被顯式關閉的缺口，而不是只劃界結案（DEF-101-757）。

實際值一律取 `Export-ScheduledTask` 的 XML，不用 `Get-ScheduledTask | Select ...`：
    後者對 MultipleInstances=StopExisting（enum 值 3）會印**空白**，空白極易被讀成
    「沒設定」（install_windows_nightly.ps1 內有同一坑的實測記載）。XML 是 Task
    Scheduler 自己的 schema，七項期望值全在同一份輸出裡，不需要拼湊多個 cmdlet。

用法：
    python tools/check_scheduled_task_drift.py            # 人類可讀
    python tools/check_scheduled_task_drift.py --json     # 機器可讀
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端印中文/✅ 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_EXPECTATIONS = Path(__file__).resolve().parent / "scheduled_task_expectations.json"

STATUS_OK = "ok"
STATUS_DRIFT = "drift"
STATUS_SKIP = "skip"
STATUS_ERROR = "error"
# R75：受管任務有一支以上整支不存在（見檔頭判準表；刻意不叫 partial——
# 該狀態字在本 repo 另有既定的窄語意，R64 有誤用紀錄）。
STATUS_TASK_MISSING = "task_missing"
# 本輪新增：受管任務**很久沒有真的跑過**（排程沒有觸發）。與 task_missing 分開：
# 任務還在、設定也對，但它沒有在跑——這是「漏跑」的第二強形態，修法也不同
# （查 powercfg 喚醒計時器／機器整段離線／MultipleInstances 把後續觸發吃掉），
# 不是重跑安裝器。
STATUS_STALE_RUN = "stale_run"

#: 「多久沒跑算漂移」。兩支受管任務都是**每日**觸發，故 1 天內必有一次；取 3 天＝
#: 容許「機器整個週末關機 + StartWhenAvailable 補跑」這種正常情形，又不至於讓一整週
#: 的漏跑靜默。刻意不取 1：那會讓任何一次正常的關機夜變紅（永紅的閘門會被關掉，
#: 見 tools/check_defect_log_crossref.py 的 ARCH-R59-NB4 判例）。
STALE_RUN_DAYS_DEFAULT = 3

#: 觸發時刻在 Task XML 裡的位置。兩種 trigger 型別都收，取先命中者。
_TRIGGER_XML_PATHS = (
    "Triggers/CalendarTrigger/StartBoundary",
    "Triggers/TimeTrigger/StartBoundary",
)

#: `LastTaskResult` 的**已知良性值**——這些不代表排程壞了，不得據以判紅。
#:   0x00000000 成功
#:   0x00041301 (267009) 任務正在執行中
#:   0x00041303 (267011) 任務尚未執行過
_LAST_RESULT_OK = 0
_LAST_RESULT_RUNNING = 267009
_LAST_RESULT_NEVER_RAN = 267011


def load_expectations(path: Path) -> dict[str, dict[str, str]]:
    """讀期望值 SSOT → {task_name: {xml_path: expected_value}}。"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {name: dict(spec["expected"]) for name, spec in raw["tasks"].items()}


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_task_xml(xml_text: str) -> dict[str, str]:
    """Task Scheduler XML → {'Settings/WakeToRun': 'true', …}（去命名空間、路徑不含根）。

    值一律小寫化布林（XML 寫 `true`/`false`，但不同來源可能出現 `True`），其餘原樣。
    """
    # Export-ScheduledTask 會在最前面塞 UTF-16 BOM／宣告，先切到第一個 `<`。
    start = xml_text.find("<?xml")
    if start < 0:
        start = xml_text.find("<Task")
    if start < 0:
        raise ValueError("輸出裡找不到 Task XML")
    root = ET.fromstring(xml_text[start:])
    found: dict[str, str] = {}

    def walk(node: ET.Element, prefix: str) -> None:
        for child in node:
            name = _strip_ns(child.tag)
            path = f"{prefix}/{name}" if prefix else name
            text = (child.text or "").strip()
            if text:
                found[path] = text.lower() if text.lower() in ("true", "false") else text
            walk(child, path)

    walk(root, "")
    return found


def _run_powershell(command: str) -> tuple[int, str]:
    """跑一段 PowerShell 並回 (rc, stdout)。stderr 併入 stdout 供取證。

    刻意用 powershell.exe（5.1）而不是 pwsh：兩支排程任務的 Action 跑的就是它，
    載具對齊＝驗證條件對齊。ScheduledTasks 模組在 5.1 一律可用。
    """
    proc = subprocess.run(  # noqa: S603 — 固定字串命令，無使用者輸入拼接
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def export_task_xml(task_name: str) -> str | None:
    """取單一任務的 XML；任務不存在回 None。"""
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", task_name):
        raise ValueError(f"任務名稱含非預期字元，拒絕代入命令：{task_name!r}")
    rc, out = _run_powershell(
        "$ErrorActionPreference='Stop'; "
        f"if (-not (Get-ScheduledTask -TaskName '{task_name}' "
        "-ErrorAction SilentlyContinue)) { exit 9 }; "
        f"Export-ScheduledTask -TaskName '{task_name}'"
    )
    if rc == 9:
        return None
    if rc != 0 or "<Task" not in out:
        raise RuntimeError(f"Export-ScheduledTask 失敗（rc={rc}）：{out.strip()[:400]}")
    return out


def query_task_info(task_name: str) -> dict[str, Any] | None:
    """取單一任務的執行史（LastRunTime／LastTaskResult／NumberOfMissedRuns）。

    刻意**不**走 `Export-ScheduledTask`：那份 XML 是**定義**，不含任何執行結果——
    這正是本檔此前看不到「昨晚跑失敗了」的機械原因（對照組只有定義、沒有履歷）。

    `LastRunTime` 顯式格式化成 ISO-8601 UTC 字串再交給 JSON：PS 5.1 的
    `ConvertTo-Json` 會把 `DateTime` 序列化成 `/Date(…)/`，那個形狀在 Python 端解析
    要多一層正則，而且不同 PS 版本行為不同（本 repo 對「同一份輸出兩種形狀」有前例教訓）。
    """
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", task_name):
        raise ValueError(f"任務名稱含非預期字元，拒絕代入命令：{task_name!r}")
    rc, out = _run_powershell(
        "$ErrorActionPreference='Stop'; "
        f"$i = Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
        "if (-not $i) { exit 9 }; "
        "[pscustomobject]@{ "
        "LastRunTime = $(if ($i.LastRunTime) "
        "{ $i.LastRunTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') } else { '' }); "
        "LastTaskResult = $i.LastTaskResult; "
        "NumberOfMissedRuns = $i.NumberOfMissedRuns "
        "} | ConvertTo-Json -Compress"
    )
    if rc == 9:
        return None
    if rc != 0:
        return None  # 讀不到履歷不阻斷設定比對；classify_last_result 會標成 unmeasured
    start = out.find("{")
    if start < 0:
        return None
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError:
        return None


def load_trigger_expectations(path: Path) -> dict[str, str]:
    """讀期望觸發時刻 SSOT → {task_name: 'HH:mm'}；未登記者不列入。

    刻意放在 `expected` **之外**（任務層的 sibling 欄位）：`expected` 那組的每一個鍵
    都受 `tools/tests/test_install_windows_nightly.py::TestScheduledTaskExpectationsSsot::
    test_every_expected_value_is_actually_applied_by_the_installer` 的「欄位集合必須
    逐字等於安裝器套用手段對照表」約束，塞進去會當場讓那道鎖紅。
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for name, spec in raw["tasks"].items():
        want = spec.get("expected_trigger_time")
        if want:
            out[name] = str(want)
    return out


def trigger_time_of(actual: dict[str, str]) -> str | None:
    """從已解析的 Task XML 取觸發時刻的 `HH:mm`（不比日期）。

    WHY 只比 HH:mm：`StartBoundary` 是完整時間戳（例 `2026-08-05T21:30:00+08:00`），
    其中的**日期**是註冊當天、每次重跑安裝器都會變 ⇒ 整串拿去等值比對必然天天漂移，
    而真正被治理的不變量只有「每天幾點跑」。
    """
    for key in _TRIGGER_XML_PATHS:
        raw = actual.get(key)
        if not raw:
            continue
        m = re.search(r"T(\d{2}:\d{2})", raw)
        if m:
            return m.group(1)
    return None


def classify_last_result(info: dict[str, Any] | None) -> tuple[str, str]:
    """把 `LastTaskResult` 翻成 `(類別, 人話)`。純函式，可單元測試。

    🔴 這裡是本檔此前**結構性失明**的那一格：偵測器驗了 7 項設定卻從不看
    「上一次到底跑成功了沒」，於是 2026-08-06 兩支任務雙雙 `LastTaskResult=1`，
    它照樣印 `status=ok` / rc=0。

    🔴 為什麼 `failed` 這一類**不得**升級成頂層 status（設計上最要緊的一句）：
    `AutoClaude_Nightly` 的工作就是「抓到問題時回 1」。若把 rc≠0 一律判紅，本偵測器
    會在**nightly 正常發揮作用的每一個晚上**轉紅，而它自己又是由那支 nightly 呼叫的
    （run_local_nightly.ps1 對狀態字採白名單 fail-closed）⇒ nightly 失敗 → 隔夜偵測器
    報紅 → nightly 再失敗，形成**自我維持的永紅迴圈**。永紅的閘門會被整個關掉，比沒有
    鎖更糟（ARCH-R59-NB4 判例）。故本類別一律「大聲印、進 JSON、不動 rc」——
    要治的是**靜默**，不是要多一個紅燈。
    """
    if info is None:
        return "unmeasured", "讀不到 Get-ScheduledTaskInfo（量不出來）"
    rc = info.get("LastTaskResult")
    if rc is None:
        return "unmeasured", "Get-ScheduledTaskInfo 沒有 LastTaskResult 欄位"
    rc = int(rc)
    if rc == _LAST_RESULT_OK:
        return "ok", "上次執行成功（rc=0）"
    if rc == _LAST_RESULT_RUNNING:
        return "running", "任務正在執行中（0x00041301）"
    if rc == _LAST_RESULT_NEVER_RAN:
        return "never_ran", "任務尚未執行過（0x00041303）"
    return "failed", (
        f"上次執行回報失敗 rc={rc}（0x{rc & 0xFFFFFFFF:08X}）"
        "——這代表**那支工作自己**判定失敗，不代表排程設定漂移；"
        "請看該任務的 log（nightly＝AutoClaude/logs/nightly_latest.log）"
    )


def _parse_iso_utc(text: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.UTC)
    except (TypeError, ValueError):
        return None


def stale_run_days(info: dict[str, Any] | None, now: _dt.datetime) -> float | None:
    """距離上次真的跑過幾天；沒跑過／讀不到回 None（**不算 stale**）。

    「沒跑過」刻意不判紅：fresh clone／剛裝好還沒到第一次觸發的機器都是這一格，
    判紅等於讓新機器開箱即紅（同本檔「全缺席＝skip」那一段的理由）。
    """
    if not info:
        return None
    last = _parse_iso_utc(str(info.get("LastRunTime") or ""))
    if last is None:
        return None
    return (now - last).total_seconds() / 86400.0


def evaluate(
    expectations: dict[str, dict[str, str]],
    actuals: dict[str, dict[str, str] | None],
    *,
    require_installed: bool = False,
    infos: dict[str, dict[str, Any] | None] | None = None,
    trigger_expectations: dict[str, str] | None = None,
    stale_days: float = STALE_RUN_DAYS_DEFAULT,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """純函式判定（可單元測試，不碰真實排程）。

    actuals[task] is None ⇒ 該任務不存在。狀態格對照見檔頭判準表：
        全部存在 + 全符期望            → ok
        全部存在 + 有一項不符          → drift
        **部分**存在（其餘整支不見）   → task_missing（R75 補登記）
        全部不存在                     → skip；require_installed=True 時改判 task_missing

    `require_installed` 的用途見檔頭「全缺席」段：預設 False 讓 CI runner／未安裝的
    開發機保持綠，True 給「知道自己該有排程」的機器把那一格關上。
    """
    infos = infos or {}
    trigger_expectations = trigger_expectations or {}
    now = now or _dt.datetime.now(_dt.UTC)
    report: dict[str, Any] = {
        "status": STATUS_OK, "tasks": {}, "drifts": [], "absent": [],
        "health": [], "stale": [],
    }
    present = 0
    for task, expected in expectations.items():
        actual = actuals.get(task)
        if actual is None:
            report["absent"].append(task)
            report["tasks"][task] = {"present": False, "drifts": []}
            continue
        present += 1
        task_drifts = []
        for key, want in expected.items():
            got = actual.get(key)
            want_norm = want.lower() if want.lower() in ("true", "false") else want
            if got != want_norm:
                task_drifts.append(
                    {"setting": key, "expected": want_norm, "actual": got if got else "<missing>"}
                )
        # 觸發時刻＝與那 7 項同一類（「排程契約被改掉了」），故併入 drifts 而非另立狀態字。
        # 實證這一格非補不可：2026-08-06 實查 AutoClaude_WindowsSmoke 觸發在 21:30，
        # 而掌舵者記得自己設的是 23:30 —— install_windows_nightly.ps1 的 `-SmokeAt`
        # **預設值就是 21:30**，任何一次不帶參數重跑安裝器都會 Unregister→Register 把它
        # 改回預設，而本偵測器當時看不到觸發時刻 ⇒ 整個改動靜默失效。
        want_time = trigger_expectations.get(task)
        if want_time:
            got_time = trigger_time_of(actual)
            if got_time != want_time:
                task_drifts.append({
                    "setting": "Triggers/StartBoundary(HH:mm)",
                    "expected": want_time,
                    "actual": got_time or "<missing>",
                })
        report["tasks"][task] = {"present": True, "drifts": task_drifts}
        for d in task_drifts:
            report["drifts"].append({"task": task, **d})

        info = infos.get(task)
        kind, human = classify_last_result(info)
        days = stale_run_days(info, now)
        report["tasks"][task]["last_result"] = {
            "kind": kind,
            "message": human,
            "last_run_time": (info or {}).get("LastRunTime") or "",
            "last_task_result": (info or {}).get("LastTaskResult"),
            "missed_runs": (info or {}).get("NumberOfMissedRuns"),
            "days_since_last_run": None if days is None else round(days, 2),
        }
        report["health"].append({"task": task, "kind": kind, "message": human})
        # 「很久沒真的跑過」＝排程沒觸發，這**才**是本偵測器的射程（會判紅）。
        # 與上面的 `failed` 相反：那個是工作自己失敗（工作在做事），這個是工作沒被叫起來。
        if days is not None and days > stale_days:
            report["stale"].append({
                "task": task, "days_since_last_run": round(days, 2), "threshold_days": stale_days,
            })
    report["present_count"] = present
    report["expected_count"] = len(expectations)
    if present == 0:
        if require_installed:
            report["status"] = STATUS_TASK_MISSING
            report["reason"] = (
                "受管排程任務全部不存在，而 --require-installed 宣告本機應已安裝"
                f"（缺席：{', '.join(report['absent'])}）"
            )
        else:
            report["status"] = STATUS_SKIP
            report["reason"] = "本機未安裝任何受管排程任務（CI runner／未安裝的開發機屬正常）"
    elif present < len(expectations):
        # 🔴 R75 補登記的一格。刻意排在 drifts 判定**之前**：兩者同時成立時（有任務不見
        # 了、剩下的那支設定也不對）以 task_missing 為主狀態——它的修法（重跑安裝器）
        # 涵蓋另一者，而反過來不成立。drifts 清單仍照實回報，不因主狀態改變而丟資訊。
        report["status"] = STATUS_TASK_MISSING
        report["reason"] = (
            f"受管排程任務部分缺席（{present}/{len(expectations)} 存在）："
            f"{', '.join(report['absent'])} 整支不存在 ⇒ 該任務不可能觸發，"
            "＝漏跑的最強形態，不得判綠"
        )
    elif report["drifts"]:
        report["status"] = STATUS_DRIFT
    elif report["stale"]:
        # 排在 drift 之後：設定不對時 drift 的修法（重跑安裝器）通常也會把觸發重新排上，
        # 兩者同時成立時先講 drift。
        report["status"] = STATUS_STALE_RUN
        report["reason"] = "；".join(
            f"{s['task']} 已 {s['days_since_last_run']} 天沒有真的執行過"
            f"（> {s['threshold_days']} 天門檻）⇒ 排程沒有觸發，觀察期當日零進帳"
            for s in report["stale"]
        )
    return report


#: 哨兵工作名的前綴（唯一的家＝`tools/lib/sentinel_lifecycle.TASK_PREFIX`；本檔不 import
#: 它，因為那條相依會把本檔綁進哨兵的相依鏈，而本檔要能在只有 Task Scheduler 的環境下跑）。
SENTINEL_PREFIX = "AutoSDD_Sentinel_"
#: 哨兵 Action 的載具**必須**是 GUI 子系統的 `pythonw.exe`。這是防彈窗兩層裡的第二層，
#: 而它失效時**零痕跡**：`quiet_python()` 找不到 pythonw 就靜默退回 console 版
#: （R84／C3-P1b 已讓它出聲，但那一行只有武裝當下的人看得到，事後查不到）。
SENTINEL_CARRIER_SUFFIX = "pythonw.exe"


def sentinel_task_names() -> list[str]:
    """排程器裡現存的哨兵工作名；量不到回空清單（呼叫端自己分辨，見 `--sentinels`）。"""
    rc, out = _run_powershell(
        "$ErrorActionPreference='SilentlyContinue'; "
        f"Get-ScheduledTask | Where-Object {{ $_.TaskName -like '{SENTINEL_PREFIX}*' }} "
        "| Select-Object -ExpandProperty TaskName")
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def sentinel_problems(actual: dict[str, str]) -> list[str]:
    """單一哨兵的判準。**只判載具**，`LogonType` 只回報不判紅。

    🔴 為什麼 `LogonType` 不判紅：S4U 註冊需要提權，而哨兵的武裝路徑（SessionStart／
    PostToolUse hook）一律非提權 ⇒ 回退成 `InteractiveToken` 是**合法且常見**的結果。
    把它判紅會讓每一台非提權機器的這道檢查永紅，而本 repo 已判過「擋到讓人無法工作的
    守衛會被整個關掉，而被關掉的守衛比沒有守衛更糟」。載具那一層不同：它與提權無關，
    只要 venv 裡有 `pythonw.exe` 就必然成立 ⇒ 它不成立就是真的有東西壞了。
    """
    carrier = actual.get("Actions/Exec/Command", "")
    if not carrier:
        return ["Actions/Exec/Command 讀不到 ⇒ 無法判斷載具（量不到 ≠ 量到零）"]
    if not carrier.lower().rstrip('"\'').endswith(SENTINEL_CARRIER_SUFFIX):
        return [f"Action 載具＝{carrier} ⇒ 不是 GUI 子系統的 {SENTINEL_CARRIER_SUFFIX}，"
                "每次 tick 都會配置一個 console 視窗（掌舵者回報的「黑框一閃即消」）"]
    return []


def _report_sentinels() -> int:
    """`--sentinels`：對每一支現存哨兵取 XML，判載具、印 Principal。回 rc。"""
    names = sentinel_task_names()
    if not names:
        print(f"[sentinel-drift] 排程器裡沒有 {SENTINEL_PREFIX}* 工作（或列舉失敗）。"
              "🔴 這一行**不區分**「量到零」與「量不到」——要確認請現查："
              f"`Get-ScheduledTask | Where-Object TaskName -like '{SENTINEL_PREFIX}*'`")
        return 0
    bad = 0
    for task in names:
        try:
            xml_text = export_task_xml(task)
        except (RuntimeError, ValueError) as exc:
            print(f"  ❌ {task}: 取 XML 失敗 ⇒ {exc}")
            bad += 1
            continue
        if xml_text is None:
            print(f"  • {task}: 列舉時在、取 XML 時不在（剛被收掉）")
            continue
        actual = parse_task_xml(xml_text)
        problems = sentinel_problems(actual)
        # Principal 一律印、一律不判紅（理由見 `sentinel_problems`）。
        principal = ("Principals/Principal/LogonType", "Principals/Principal/RunLevel",
                     "Principals/Principal/UserId")
        detail = "／".join(f"{p.rsplit('/', 1)[-1]}={actual.get(p, 'n/a')}"
                           for p in principal)
        print(f"  {'❌' if problems else '✅'} {task}: {detail}")
        for problem in problems:
            print(f"      {problem}")
        bad += bool(problems)
    print(f"[sentinel-drift] status={'drift' if bad else 'ok'}"
          f"（{len(names)} 支，{bad} 支載具不合格）")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="比對線上 schtasks 設定 vs 期望值 SSOT")
    parser.add_argument("--expectations", type=Path, default=_DEFAULT_EXPECTATIONS)
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help=(
            "宣告本機應已安裝受管排程：全缺席由 SKIP 改判 task_missing（rc=1）。"
            "預設關閉的理由見檔頭「全缺席」段（CI runner／fresh clone 不得因此永久紅）"
        ),
    )
    parser.add_argument(
        "--stale-days", type=float, default=STALE_RUN_DAYS_DEFAULT,
        help=f"上次真的執行過超過幾天算漂移（預設 {STALE_RUN_DAYS_DEFAULT}；WHY 見該常數）",
    )
    parser.add_argument(
        "--sentinels", action="store_true",
        help=("改判哨兵面（`AutoSDD_Sentinel_*`）：對每一支取 XML，**只判**"
              "Action 載具必須以 pythonw.exe 結尾；LogonType 只回報不判紅"
              "（非提權回退是合法的，判紅會製造永紅閘門而被整個關掉）"),
    )
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        # 非 Windows 沒有 Task Scheduler——這裡 SKIP 不是放水，是「這台機器上不存在
        # 這個受測對象」。把它判紅會讓 macos-compat-ci / root-infra-ci(ubuntu) 必紅，
        # 而那是 DEF-101-766 那個「單平台判準無條件外推」教訓的原形。
        payload = {"status": STATUS_SKIP, "reason": f"非 Windows 平台（{sys.platform}）"}
        print(json.dumps(payload, ensure_ascii=False) if args.json
              else f"[schedule-drift] SKIP — {payload['reason']}")
        return 0

    if args.sentinels:
        # 哨兵面與受管排程面是**兩個不同的受測對象**（前者由 session 動態生滅、名字帶
        # session id，不可能寫進期望值 SSOT）⇒ 走自己的路徑，不共用 `evaluate()`。
        return _report_sentinels()

    expectations = load_expectations(args.expectations)
    trigger_expectations = load_trigger_expectations(args.expectations)
    actuals: dict[str, dict[str, str] | None] = {}
    infos: dict[str, dict[str, Any] | None] = {}
    try:
        for task in expectations:
            xml_text = export_task_xml(task)
            actuals[task] = parse_task_xml(xml_text) if xml_text is not None else None
            infos[task] = query_task_info(task) if xml_text is not None else None
    except (RuntimeError, ValueError, ET.ParseError, OSError) as exc:
        payload = {"status": STATUS_ERROR, "reason": str(exc)}
        print(json.dumps(payload, ensure_ascii=False) if args.json
              else f"[schedule-drift] ERROR — {exc}")
        return 1  # fail-closed：量不出來不得當成沒問題

    report = evaluate(
        expectations, actuals,
        require_installed=args.require_installed,
        infos=infos,
        trigger_expectations=trigger_expectations,
        stale_days=args.stale_days,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[schedule-drift] status={report['status']}")
        for task, info in report["tasks"].items():
            if not info["present"]:
                # R75：缺席行必須自己說出它算綠還是算紅。原文一律只印「不存在（未安裝）」
                # ——同一句話在「全缺席＝skip、rc=0」與「部分缺席＝rc=1」兩種相反結論下
                # 都會出現，讀者無從分辨自己看到的是哪一種。
                verdict = (
                    "判定為失敗（該任務不可能觸發）"
                    if report["status"] == STATUS_TASK_MISSING
                    else "本機未安裝受管排程，整體判 SKIP"
                )
                print(f"  - {task}: 不存在 ⇒ {verdict}")
                continue
            if not info["drifts"]:
                print(f"  - {task}: 全部 {len(expectations[task])} 項設定符合期望")
                continue
            print(f"  - {task}: {len(info['drifts'])} 項漂移")
            for d in info["drifts"]:
                print(f"      {d['setting']}: 實機={d['actual']} 期望={d['expected']}")
        # 🔴 執行履歷一律印，**與 rc 無關**——本檔要治的缺陷是「兩支任務昨晚都
        # LastTaskResult=1 而它印 status=ok」，也就是**靜默**，不是少一個紅燈。
        # 為何 kind=failed 不動 rc：見 classify_last_result 的 docstring（永紅迴圈）。
        print("  執行履歷（LastTaskResult／LastRunTime — 本段不影響 rc，見下方說明）：")
        for task, info in report["tasks"].items():
            lr = info.get("last_result")
            if not lr:
                continue
            mark = {"ok": "✅", "failed": "❌", "running": "⏳",
                    "never_ran": "•", "unmeasured": "❓"}.get(lr["kind"], "•")
            age = lr["days_since_last_run"]
            age_txt = "（從未執行）" if age is None else f"（{age} 天前）"
            print(f"    {mark} {task}: {lr['message']} — 上次執行 "
                  f"{lr['last_run_time'] or 'n/a'} {age_txt}"
                  f"，錯過次數 {lr['missed_runs']}")
        if any(h["kind"] == "failed" for h in report["health"]):
            print("    ⚠️ 上面有工作自報失敗。**這不會讓本檢查轉紅**——那代表該工作"
                  "自己抓到問題（它在做事），而不是排程漂移；把它判紅會讓本檢查在"
                  "nightly 每次發揮作用的晚上都紅，且本檢查正是由 nightly 呼叫的"
                  "（＝自我維持的永紅迴圈）。請直接看該工作的 log。")
        if report["stale"]:
            print(f"  ❌ 排程未觸發：{report['reason']}")
            print("     排查：powercfg 喚醒計時器是否關閉／機器整段離線／"
                  "MultipleInstances 把後續觸發吃掉／WakeToRun 未生效")
        if report["status"] == STATUS_TASK_MISSING:
            print(f"  原因：{report['reason']}")
        if report["status"] in (STATUS_DRIFT, STATUS_TASK_MISSING):
            installer = "tools\\install_windows_nightly.ps1"
            print("  修法（需「以系統管理員身分執行」）：")
            print(f"    powershell -ExecutionPolicy Bypass -File {installer}")
            print(f"    powershell -ExecutionPolicy Bypass -File {installer} -Status")
            print("  ⚠️ 安裝器會 Unregister→Register，觸發時刻取自 param 預設值——"
                  "要保留現行時刻請顯式傳 -NightlyAt/-SmokeAt（見該檔 param 區塊）")
    return 1 if report["status"] in (
        STATUS_DRIFT, STATUS_ERROR, STATUS_TASK_MISSING, STATUS_STALE_RUN
    ) else 0


if __name__ == "__main__":
    sys.exit(main())
