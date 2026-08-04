#!/usr/bin/env python3
"""線上 schtasks 排程設定漂移偵測器（R74 / ADR-SD09-012 §8.2 的機械化）。

為何存在（Rule 9 — 這支不是美化，是補一個結構性失明）：
    ADR-SD09-012 §8.2 於 2026-08-03 就實測列出五項排程設定落差，而它連續三輪
    （R71/R72/R73）原封不動存活且**沒有任何東西轉紅**。機械成因不是沒人細心：
    線上排程只以「機器狀態」存在，repo 裡沒有任何一份檔案是它們，於是也就沒有
    任何檢查器有對照組可比。本檔＝比對器，對照組＝tools/scheduled_task_expectations.json。

判準（刻意設計成 CI 安全）：
    · 非 Windows              → SKIP，rc=0（macos/ubuntu CI 不得因此轉紅）
    · 兩支任務都不存在        → SKIP，rc=0（本機未安裝排程／CI runner 的正常狀態）
    · 任務存在但設定不符期望  → DRIFT，rc=1  ← 這才是要偵測的東西
    · 任務存在但讀不到設定    → rc=1（fail-closed：量不出來不得當成沒問題）

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
) -> dict[str, Any]:
    """純函式判定（可單元測試，不碰真實排程）。

    actuals[task] is None ⇒ 該任務不存在。全部不存在 ⇒ skip。
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
    if present == 0:
        report["status"] = STATUS_SKIP
        report["reason"] = "本機未安裝任何受管排程任務（CI runner／未安裝的開發機屬正常）"
    elif report["drifts"]:
        report["status"] = STATUS_DRIFT
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="比對線上 schtasks 設定 vs 期望值 SSOT")
    parser.add_argument("--expectations", type=Path, default=_DEFAULT_EXPECTATIONS)
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
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

    report = evaluate(expectations, actuals)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[schedule-drift] status={report['status']}")
        for task, info in report["tasks"].items():
            if not info["present"]:
                print(f"  - {task}: 不存在（未安裝）")
                continue
            if not info["drifts"]:
                print(f"  - {task}: 全部 {len(expectations[task])} 項設定符合期望")
                continue
            print(f"  - {task}: {len(info['drifts'])} 項漂移")
            for d in info["drifts"]:
                print(f"      {d['setting']}: 實機={d['actual']} 期望={d['expected']}")
        if report["status"] == STATUS_DRIFT:
            installer = "tools\\install_windows_nightly.ps1"
            print("  修法（需「以系統管理員身分執行」）：")
            print(f"    powershell -ExecutionPolicy Bypass -File {installer}")
            print(f"    powershell -ExecutionPolicy Bypass -File {installer} -Status")
            print("  ⚠️ 安裝器會 Unregister→Register，觸發時刻取自 param 預設值——"
                  "要保留現行時刻請顯式傳 -NightlyAt/-SmokeAt（見該檔 param 區塊）")
    return 1 if report["status"] in (STATUS_DRIFT, STATUS_ERROR) else 0


if __name__ == "__main__":
    sys.exit(main())
