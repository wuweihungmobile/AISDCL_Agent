#!/usr/bin/env python3
"""GitHub Actions「逐軌」活性偵測（R68，tools/dev_start.py 的 CI 活性哨兵用）。

🔴 為何獨立成模組而不是留在 dev_start.py：
  ① **粒度缺陷本身**——原哨兵只跑 `gh run list --limit 1`（跨 workflow 取最新一筆），
     任何一次 push 的綠燈都會遮蔽週頻／日頻兜底軌的長期死亡。實測 2026-08-01：該哨兵
     印「✅ GitHub CI 活性正常」的同一刻，windows-compat-ci／macos-compat-ci 的
     schedule 軌已死 18 天。這是結構性偵測不到（週頻軌永遠不可能是「最新一筆」），
     不是機率問題，故必須改為逐軌查。
  ② **LOC**——dev_start.py 已逼近 DEF-101-271/274 的 2000 行「該輪必修」門檻
     （R68 現查 1918 行、餘裕 82 行）。把這段 ~70 行的新邏輯留在該檔會當場推過門檻，
     等於自己製造一筆必修債。行數守門見 AutoClaude/tools/check_loc_budget.py 的
     SPECIAL_FILES（R68 新增 `../tools/dev_start.py` 棘輪）。

期望軌與週期一律**現查** `.github/workflows/*.yml` 的 `on.schedule.cron`，不存第二份
會腐化的字面清單（DEF-101-289/515「文件寫死機器算得出的數字」同一家族）。
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

# 只匹配「未被註解掉」的 cron 行：行首 `#` 的 dormant 軌不會被誤列為期望軌。
_CRON_LINE_RE = re.compile(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']", re.M)

# 陳舊判準：超過「cron 週期 × 本倍數」仍無成功 run 即視為該軌已死。取 2 是為了容忍
# 一次跳過（單次 runner 排隊／額度抖動不該一跑出來就吵）。
STALE_PERIOD_FACTOR = 2.0


def cron_period_days(expr: str) -> float:
    """粗估 cron 週期（天）：dow 指定→週頻 7、dom 指定→月頻 30、否則日頻 1。"""
    fields = expr.split()
    if len(fields) < 5:
        return 1.0
    return 7.0 if fields[4] != "*" else (30.0 if fields[2] != "*" else 1.0)


def scheduled_workflow_periods(root: Path) -> dict[str, float]:
    """{workflow 檔名: 期望間隔天數}；同檔多條 cron 取最短（最嚴）。"""
    out: dict[str, float] = {}
    for f in sorted((root / ".github" / "workflows").glob("*.yml")):
        try:
            crons = _CRON_LINE_RE.findall(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if crons:
            out[f.name] = min(cron_period_days(c) for c in crons)
    return out


# 計入活性的事件：排程觸發，**加上**手動補跑。
# 🔴 R69（DEF-101-703）：原版只查 `schedule`，與「陳舊時該怎麼辦」的唯一處置
# （`gh workflow run <wf>.yml`，產生的是 `event=workflow_dispatch` 的 run）**實證互斥**
# ——照著處置做，哨兵仍看不到任何成功紀錄、照樣天天喊陳舊，於是它會被當成狼來了而被
# 忽略，正好複製它要消滅的那個病（root-infra-ci.yml 第 15 道同一處訂正）。
# 語意上兩事件也等價：兩者都會把 `*-nightly-full` 這個 job 真的拉起來跑（該 job 的
# `if:` 逐字就是 `schedule || workflow_dispatch`），對「這條通道還活著嗎」是等價證據。
_LIVENESS_EVENTS = ("schedule", "workflow_dispatch")


def _latest_success_run(workflow: str) -> str | None:
    """該 workflow 最近一次成功 run 的 updatedAt（ISO8601）；查不到回 None。

    掃 `_LIVENESS_EVENTS` 每個事件各取最近一筆成功，取其中**最新**者。ISO8601 的
    `...Z` 字串字典序即時序，故可直接 `max()`。
    任一事件查得到（含「查得到但零筆」＝空字串）就不算無訊號；**全部**事件都查失敗
    才回 None（無訊號 ≠ 壞訊號，見 `stale_schedule_tracks` docstring）。
    """
    stamps: list[str] = []
    saw_signal = False
    for event in _LIVENESS_EVENTS:
        try:
            r = subprocess.run(
                ["gh", "run", "list", "--workflow", workflow, "--event", event,
                 "--status", "success", "--limit", "1", "--json", "updatedAt"],
                timeout=10, capture_output=True, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode != 0:
            continue
        try:
            runs = json.loads(r.stdout or "[]")
        except ValueError:
            continue
        saw_signal = True
        try:
            if runs:
                stamps.append(runs[0]["updatedAt"])
        except (TypeError, KeyError, IndexError):
            continue
    if not saw_signal:
        return None
    return max(stamps) if stamps else ""


def stale_schedule_tracks(root: Path, deadline: float,
                          now: datetime | None = None) -> list[str]:
    """逐軌查活性，回傳陳舊軌的人類可讀描述清單（空 list＝全部新鮮／全部查不到）。

    `deadline`＝`time.monotonic()` 基準的總預算上限（多次 gh 呼叫可能各約 1 秒），
    超時即中止掃描——本哨兵是 advisory，寧可少報也不可拖住開工流程。
    查不到（gh 失敗／逾時／回應無法解析）一律**跳過而非報陳舊**：無訊號 ≠ 壞訊號。
    """
    ref = now or datetime.now(UTC)
    stale: list[str] = []
    for wf, period in scheduled_workflow_periods(root).items():
        if time.monotonic() > deadline:
            break
        ts = _latest_success_run(wf)
        if ts is None:
            continue
        if ts == "":
            stale.append(f"{wf}（查無任何成功的 schedule run）")
            continue
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        age = (ref - when).total_seconds() / 86400.0
        if age > STALE_PERIOD_FACTOR * period:
            stale.append(f"{wf}（最近成功於 {age:.0f} 天前，cron 週期 {period:.0f} 天）")
    return stale
