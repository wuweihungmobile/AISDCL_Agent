"""SD_09 W3 Round 9 audit P2-R9-1 修復（紀律 #4「驗證鏡子自身要被驗證」）：

ps1 (tools/run_local_nightly.ps1 line 415-441) F2 區塊解析 ac4_progress_check.py
混雜 stdout(JSON)+stderr(warning) 輸出 → 區分 F2 OK / F2 ALERT / F2 stderr / F2 WARN
4 條分支。Round 9 audit 指出此 ps1 邏輯缺單元測試覆蓋。

本 helper 為 ps1 邏輯之 Python pure-function 同構樣板（SSOT）— 任何 ps1 F2 區塊邏輯
變動須同步更新本 helper + 重跑 tests/tools/test_ac4_nightly_alert_parser.py。

ps1 端維持原狀（穩定 nightly 不破壞 A- 治理），本 helper 提供：
1. 4 條分支邏輯的單元測試覆蓋（防迴歸）
2. W1+ 若選擇遷移 ps1 至 helper-driven 模式，可直接 import 使用
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlertDecision:
    """F2 區塊解析結果（4 條分支對應 ps1 line 415-441）。"""

    level: str  # "OK" | "ALERT" | "WARN"
    log_message: str  # 寫入 nightly_latest.log 的訊息（不含 [F2 xxx] 前綴）
    stderr_lines: tuple[str, ...]  # 攔截到的 stderr 警告行（無 → 空 tuple）
    parsed_json: dict[str, Any] | None  # 成功解析的 JSON 物件；None = 解析失敗


def split_stdout_stderr(raw_output: str) -> tuple[list[str], list[str]]:
    """模擬 ps1 line 422-431 的 stderr/JSON 拆分邏輯。

    規則（與 ps1 同構；ac4_progress_check.py --json 永遠回 dict）：
        - 逐行掃描 raw_output
        - 空行（JSON 起點前）直接跳過
        - 第一個以 `{` 開頭的行視為 JSON 起點（不接受 `[` 因 ps1 stderr warning
          常含 `[ac4_progress_check] WARN: ...` 字面）
        - JSON 起點之前的非空行 → stderr_lines（去頭尾空白）
        - JSON 起點之後的所有行（含空行）→ json_lines（保留以利後續 json.loads）

    回傳：(json_lines, stderr_lines)
    """
    lines = raw_output.split("\n")
    json_lines: list[str] = []
    stderr_lines: list[str] = []
    json_started = False
    for line in lines:
        trim = line.strip()
        if not json_started and trim.startswith("{"):
            json_started = True
        if json_started:
            json_lines.append(line)
            continue
        if trim == "":
            continue
        stderr_lines.append(trim)
    return json_lines, stderr_lines


def parse(raw_output: str) -> AlertDecision:
    """主入口：解析 ac4_progress_check.py --json 輸出並決定 alert level。

    對應 ps1 4 條分支：
        1. F2 OK   — JSON 解析成功且 ready_for_labeled_pr=False（觀察期累計中）
        2. F2 ALERT — JSON 解析成功且 ready_for_labeled_pr=True（需 PM 確認）
        3. F2 stderr — JSON 起點之前的非空行（warning）— 為附加項，與 OK/ALERT 並存
        4. F2 WARN  — JSON 解析失敗（exception 路徑）
    """
    json_lines, stderr_lines = split_stdout_stderr(raw_output)
    json_text = "\n".join(json_lines).strip()

    if not json_text:
        return AlertDecision(
            level="WARN",
            log_message="AC4 readiness 解析失敗：empty JSON output",
            stderr_lines=tuple(stderr_lines),
            parsed_json=None,
        )

    try:
        parsed = json.loads(json_text)
    except (json.JSONDecodeError, ValueError) as e:
        return AlertDecision(
            level="WARN",
            log_message=f"AC4 readiness 解析失敗：{type(e).__name__}: {e}",
            stderr_lines=tuple(stderr_lines),
            parsed_json=None,
        )

    if not isinstance(parsed, dict):
        return AlertDecision(
            level="WARN",
            log_message=f"AC4 readiness 解析失敗：top-level non-dict ({type(parsed).__name__})",
            stderr_lines=tuple(stderr_lines),
            parsed_json=None,
        )

    ready = parsed.get("ready_for_labeled_pr", False)
    # SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED 拍板實作落地）：
    # ps1 端 [F2 ALERT/OK] 改用 tolerant_streak + observation_streak 雙欄位；
    # helper 同構同步（紀律 #4 SSOT）。向下相容 fallback：缺欄位時用 green_streak。
    tolerant_streak = parsed.get("tolerant_streak", parsed.get("green_streak", 0))
    observation_streak = parsed.get("observation_streak", 0)
    status = parsed.get("status", "?")
    observation_days = parsed.get("observation_days", "?")
    reasons_list = parsed.get("reasons") or []
    if not isinstance(reasons_list, list):
        reasons_list = [str(reasons_list)]
    reasons = "; ".join(str(r) for r in reasons_list)

    if ready is True:
        message = (
            f"AC4 觀察期 #2 已達標 ready_for_labeled_pr=true "
            f"(tolerant<60ms streak={tolerant_streak}/14 "
            f"observation<50ms streak={observation_streak}/14; "
            f"ADR-SD09-008 v0.4 ACCEPTED) — "
            f"需 PM 確認啟用 pg-e2e-on-label.yml workflow 並紀錄至 "
            f"docs/06_quality/SD09_AC4_Activation_Approval.md"
        )
        return AlertDecision(
            level="ALERT",
            log_message=message,
            stderr_lines=tuple(stderr_lines),
            parsed_json=parsed,
        )

    message = (
        f"AC4 觀察期 #2 累計中 status={status} "
        f"tolerant<60ms streak={tolerant_streak} "
        f"observation<50ms streak={observation_streak} "
        f"days={observation_days} reasons={reasons}"
    )
    return AlertDecision(
        level="OK",
        log_message=message,
        stderr_lines=tuple(stderr_lines),
        parsed_json=parsed,
    )
