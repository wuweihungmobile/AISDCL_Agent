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


def evaluate(
    expectations: dict[str, dict[str, str]],
    actuals: dict[str, dict[str, str] | None],
    *,
    require_installed: bool = False,
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
    report: dict[str, Any] = {"status": STATUS_OK, "tasks": {}, "drifts": [], "absent": []}
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
        report["tasks"][task] = {"present": True, "drifts": task_drifts}
        for d in task_drifts:
            report["drifts"].append({"task": task, **d})
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
    return report


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
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        # 非 Windows 沒有 Task Scheduler——這裡 SKIP 不是放水，是「這台機器上不存在
        # 這個受測對象」。把它判紅會讓 macos-compat-ci / root-infra-ci(ubuntu) 必紅，
        # 而那是 DEF-101-766 那個「單平台判準無條件外推」教訓的原形。
        payload = {"status": STATUS_SKIP, "reason": f"非 Windows 平台（{sys.platform}）"}
        print(json.dumps(payload, ensure_ascii=False) if args.json
              else f"[schedule-drift] SKIP — {payload['reason']}")
        return 0

    expectations = load_expectations(args.expectations)
    actuals: dict[str, dict[str, str] | None] = {}
    try:
        for task in expectations:
            xml_text = export_task_xml(task)
            actuals[task] = parse_task_xml(xml_text) if xml_text is not None else None
    except (RuntimeError, ValueError, ET.ParseError, OSError) as exc:
        payload = {"status": STATUS_ERROR, "reason": str(exc)}
        print(json.dumps(payload, ensure_ascii=False) if args.json
              else f"[schedule-drift] ERROR — {exc}")
        return 1  # fail-closed：量不出來不得當成沒問題

    report = evaluate(expectations, actuals, require_installed=args.require_installed)
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
        if report["status"] == STATUS_TASK_MISSING:
            print(f"  原因：{report['reason']}")
        if report["status"] in (STATUS_DRIFT, STATUS_TASK_MISSING):
            installer = "tools\\install_windows_nightly.ps1"
            print("  修法（需「以系統管理員身分執行」）：")
            print(f"    powershell -ExecutionPolicy Bypass -File {installer}")
            print(f"    powershell -ExecutionPolicy Bypass -File {installer} -Status")
            print("  ⚠️ 安裝器會 Unregister→Register，觸發時刻取自 param 預設值——"
                  "要保留現行時刻請顯式傳 -NightlyAt/-SmokeAt（見該檔 param 區塊）")
    return 1 if report["status"] in (STATUS_DRIFT, STATUS_ERROR, STATUS_TASK_MISSING) else 0


if __name__ == "__main__":
    sys.exit(main())
