"""GoalProgressLedger — 跨 playbook run 目標進度彙總（F-C2 / ADR-AGT-003 L4）。

File 實作（yaml_only 路由）：`{checkpoint_dir}/goal_progress.jsonl` append-only。
PG 對等：infra/adapters/pg_goal_progress_ledger.py（goal_progress 表，alembic 0016）。

鍵語意（SRD_AGT_Phase1_Memory §3.1）：goal_task_id 有值時用之；
無值（yaml_only 常態）以 `project:{playbook.project}` fallback，確保仍可跨 run 彙總。

JSONL 行格式：
  {"goal_task_id": "...", "playbook_id": "...", "run_id": null,
   "completed_features": [...], "progress_pct": 0.0~100.0, "ts": "<ISO8601 UTC>"}
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("autoclaude.utils.goal_progress")


class GoalProgressLedger:
    """L4 目標進度 ledger（File 後端，append-only）。"""

    def __init__(self, path: str):
        self._path = Path(path)

    def record(
        self,
        goal_task_id: str,
        *,
        playbook_id: str | None = None,
        run_id: str | None = None,
        completed_features: list[str] | None = None,
        progress_pct: float | None = None,
    ) -> None:
        """append 一筆進度紀錄；寫入失敗 warning 不中斷主流程。"""
        row = {
            "goal_task_id": goal_task_id,
            "playbook_id": playbook_id,
            "run_id": run_id,
            "completed_features": completed_features or [],
            "progress_pct": progress_pct,
            "ts": datetime.now(UTC).isoformat(),
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("goal progress 寫入失敗（warning，繼續主流程）: %s", exc)

    def summarize(self, goal_task_id: str) -> dict:
        """彙總指定 goal 的跨 run 進度。

        Returns:
            {
                "goal_task_id": str,
                "run_count": int,                # 紀錄筆數（含同 playbook 重跑）
                "completed_features": list[str], # 跨 run 聯集（保序去重）
                "progress_pct": float | None,    # 最新一筆
                "last_recorded_at": str | None,  # 最新一筆 ts
            }
        """
        features: list[str] = []
        seen: set[str] = set()
        run_count = 0
        latest_pct: float | None = None
        latest_ts: str | None = None
        for row in self._iter_rows(goal_task_id):
            run_count += 1
            for feat in row.get("completed_features", []):
                if feat not in seen:
                    seen.add(feat)
                    features.append(feat)
            if row.get("progress_pct") is not None:
                latest_pct = float(row["progress_pct"])
            latest_ts = row.get("ts", latest_ts)
        return {
            "goal_task_id": goal_task_id,
            "run_count": run_count,
            "completed_features": features,
            "progress_pct": latest_pct,
            "last_recorded_at": latest_ts,
        }

    def _iter_rows(self, goal_task_id: str):
        if not self._path.exists():
            return
        try:
            with self._path.open(encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    row = json.loads(raw)
                    if row.get("goal_task_id") == goal_task_id:
                        yield row
        except (OSError, ValueError) as exc:
            logger.warning("goal progress 讀取失敗: %s", exc)


__all__ = ["GoalProgressLedger"]
