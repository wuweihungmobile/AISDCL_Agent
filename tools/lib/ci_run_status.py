"""GitHub Actions 最新 run 活性判讀（DEF-101-758 LOC 死結搬遷）。

原棲身 `tools/dev_start.py::_check_ci_liveness`——該檔為 SPECIAL_FILES raw-line
棘輪（上限 2000），本次搬遷前實測 1999／2000（僅餘 1 行），任何淨增都會撞線。
本模組即該函式的邏輯本體；`dev_start.py` 側改為薄呼叫（見該檔 `_check_ci_liveness`）。

WHY：CI 額度停擺（DEF-101-081）期間 GitHub Actions 可能長期紅/停，push 者以為
雲端有兜底其實沒有——本模組用 `gh` 的 read-only API（零 Actions 額度）查最新
run 結論。純 advisory：任何例外或無法判讀一律回 None／文字提示，不得影響
呼叫端流程或 exit code。

SD-R15-REV-1：GitHub Actions API 對尚未跑完的 run（queued/in_progress）
`conclusion` 恆為 null——先查 `status`，非 completed 一律視為正常（執行中），
不落入異常分支。

🔴 葉節點模組（R98 循環匯入教訓，見 `quota_policy.py`↔`quota_policy_env.py`）：
本模組向下 import `ci_liveness`，但**不得**被 `ci_liveness.py` 反向 import。
本模組只被 `tools/dev_start.py` import。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import ci_liveness


def check_ci_run_status(
    is_repo: bool,
    sync_summary: str,
    root: Path,
    warn: Callable[[str], None],
) -> str | None:
    """回傳 summary 片段，None＝靜默跳過。

    三道靜默跳過閘：無 `gh`／呼叫端已判定離線或跳過（重用其判定，不做第二次
    網路探測）／非 git repo。全函式 try/except 兜底：任何例外不得改變呼叫端
    行為（同心跳哨兵契約）。
    """
    try:
        if shutil.which("gh") is None:
            return None
        if sync_summary.startswith("離線") or sync_summary.startswith("跳過"):
            return None
        if not is_repo:
            return None
        # R68：逐軌陳舊度先查（與下方「最新一筆 run」是兩種粒度，缺一即有盲區——
        # 見 ci_liveness.py 檔頭的 18 天實測）。
        stale = ci_liveness.stale_schedule_tracks(root, time.monotonic() + 25)
        if stale:
            warn("GitHub 排程軌長期未成功：" + "；".join(stale)
                 + " — 週/日頻兜底軌已死（最新一次 push 的綠燈遮蔽不了它）")
        try:
            r = subprocess.run(
                ["gh", "run", "list", "--limit", "1",
                 "--json", "status,conclusion,updatedAt,workflowName"],
                timeout=15, capture_output=True, encoding="utf-8", errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired):
            r = None
        if r is None or r.returncode != 0:
            # 不入 WARNINGS：gh 未登入/網路抖動是常態，溫和一行即可
            print("    CI 活性未知（gh 不可用或未登入）")
            return "CI 活性未知"
        try:
            runs = json.loads(r.stdout or "")
        except ValueError:
            runs = None
        if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
            print("    CI 活性未知（gh 回應無可解析的 run 資料）")
            return "CI 活性未知"
        status = runs[0].get("status")
        conclusion = runs[0].get("conclusion")
        workflow = runs[0].get("workflowName", "?")
        if status != "completed":
            print(f"    CI 活性正常（最新 run：{workflow} 執行中，status={status}）")
            return "CI 活性正常（執行中）"
        if conclusion == "success":
            print(f"    ✅ GitHub CI 活性正常（最新 run：{workflow}=success）")
            return "CI 活性正常"
        warn(f"GitHub CI 最新 run {workflow}={conclusion}"
             f"（{runs[0].get('updatedAt', '?')}）——帳務停擺/失敗中，"
             f"本地 pre-push＋nightly 為唯一活體驗證（DEF-101-081/208）")
        return f"CI 活性異常（最新 run={conclusion}，見警告）"
    except Exception:
        # 兜底：哨兵絕不可改變呼叫端的 exit code 或流程
        return None
