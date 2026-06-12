"""SD_Improving_06 W3-T3-27 — embedding 寫入路徑整合測試（AC4-3）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-3：三觸發點皆有 embedding IS NOT NULL
      • create_goal_task → goal_tasks
      • update_goal_task → goal_tasks (UPDATE)
      • complete_execution_item → execution_items
  - SD_Improving_06.md §9.2 PM #9：embedding_status 三態 + retry 5 次告警
  - SD_Improving_06.md §9.2 PM #11：PII filter 套用

驗證項目（≥ 6 case）：
  T1 create_goal_task → INSERT 後 UPDATE 寫入 embedding_v / model_id / status='ok'
  T2 update_goal_task → 取 row 後重新 embed + UPDATE
  T3 complete_execution_item → UPDATE result + embedding 寫入
  T4 embedder fail → status='failed'、attempts++、不阻斷業務寫入
  T5 attempts 達 alert_after_attempts → 觸發 SLO observer
  T6 PII SECRET 文字 → PIIFilterViolation 中斷（不入庫）
  T7 PII PII 類欄位 → 自動 mask
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from autoclaude.core.ports.embedder import EmbedderUnavailableError
from autoclaude.infra.services.embedding_writer import (
    EMBEDDING_STATUS_FAILED,
    EMBEDDING_STATUS_OK,
    EmbeddingWriter,
    SLOAlert,
)
from autoclaude.infra.services.pii_filter import (
    FieldRegistry,
    PIIClassification,
    PIIFilter,
    PIIFilterViolation,
)


# ── 測試 fixtures ─────────────────────────────────────────

class _InMemorySql:
    """極簡 SQL fake：分表記錄 SQL + 用 dict 模擬 row。"""

    def __init__(self) -> None:
        self.goal_tasks: dict[str, dict] = {}
        self.execution_items: dict[str, dict] = {}
        self.executed: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple) -> None:
        self.executed.append((sql.strip()[:80], params))
        s = sql.strip().upper()
        if s.startswith("INSERT INTO GOAL_TASKS"):
            (gid, pid, parent, title, desc, depth, pri, snap) = params
            self.goal_tasks[gid] = {
                "goal_task_id": gid, "project_id": pid, "parent_id": parent,
                "title": title, "description": desc,
                "depth": depth, "priority": pri,
                "embedding_v": None, "embedding_model_id": None,
                "embedding_status": "pending", "embedding_attempts": 0,
                "config_snapshot": snap,
            }
        elif s.startswith("UPDATE GOAL_TASKS"):
            # 解析片段判斷哪種 update
            if "EMBEDDING_V=" in s:
                vec, model_id, gid = params
                row = self.goal_tasks.get(gid)
                if row:
                    row["embedding_v"] = vec
                    row["embedding_model_id"] = model_id
                    row["embedding_status"] = "ok"
                    row["embedding_attempts"] += 1
            elif "EMBEDDING_STATUS='FAILED'" in s:
                (gid,) = params
                row = self.goal_tasks.get(gid)
                if row:
                    row["embedding_status"] = "failed"
                    row["embedding_attempts"] += 1
            else:
                # update title/desc + status='pending'
                title, desc, gid = params
                row = self.goal_tasks.get(gid)
                if row:
                    row["title"] = title
                    row["description"] = desc
                    row["embedding_status"] = "pending"
        elif s.startswith("UPDATE EXECUTION_ITEMS"):
            if "EMBEDDING_V=" in s:
                vec, model_id, eid = params
                row = self.execution_items.get(eid)
                if row:
                    row["embedding_v"] = vec
                    row["embedding_model_id"] = model_id
                    row["embedding_status"] = "ok"
                    row["embedding_attempts"] += 1
            elif "EMBEDDING_STATUS='FAILED'" in s:
                (eid,) = params
                row = self.execution_items.get(eid)
                if row:
                    row["embedding_status"] = "failed"
                    row["embedding_attempts"] += 1
            else:
                actual_min, result, eid = params
                row = self.execution_items.get(eid)
                if row:
                    row["actual_minutes"] = actual_min
                    row["result"] = result
                    row["status"] = "ok"
                    row["embedding_status"] = "pending"

    def fetch_one(self, sql: str, params: tuple) -> dict:
        s = sql.strip().upper()
        if "FROM GOAL_TASKS" in s:
            (gid,) = params
            return self.goal_tasks.get(gid)
        if "FROM EXECUTION_ITEMS" in s:
            (eid,) = params
            return self.execution_items.get(eid)
        return None

    def fetch_all(self, sql: str, params: tuple) -> list[dict]:
        return []


class _FakeEmbedder:
    def __init__(self, *, dim: int = 1024, model_id: str = "bge-m3",
                 fail_n_times: int = 0) -> None:
        self.dimension = dim
        self.model_id = model_id
        self._fail_remaining = fail_n_times
        self.calls = 0

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise EmbedderUnavailableError("simulated")
        return [[0.1] * self.dimension for _ in texts]


@pytest.fixture
def sql():
    sql_fake = _InMemorySql()
    # 預先建立一筆 execution_item 供 T3 使用
    sql_fake.execution_items["EX1"] = {
        "exec_id": "EX1", "goal_task_id": "GT1", "action": "run-test",
        "status": "pending", "actual_minutes": None, "result": None,
        "embedding_v": None, "embedding_model_id": None,
        "embedding_status": "pending", "embedding_attempts": 0,
    }
    return sql_fake


@pytest.fixture
def embedder():
    return _FakeEmbedder()


@pytest.fixture
def writer(sql, embedder):
    return EmbeddingWriter(
        embedder=embedder,
        sql_executor=sql,
        pii_filter=PIIFilter(enabled=True),
        alert_after_attempts=5,
    )


# ── tests ────────────────────────────────────────────────

def test_create_goal_task_writes_embedding(sql, writer):
    """T1 create_goal_task：INSERT + UPDATE embedding。"""
    res = writer.create_goal_task(
        goal_task_id="GT1", project_id="P1",
        parent_id=None,
        title="Build login form", description="OAuth + form",
        depth=1, priority=3,
    )
    assert res.embedding_status == EMBEDDING_STATUS_OK
    assert sql.goal_tasks["GT1"]["embedding_v"] is not None
    assert sql.goal_tasks["GT1"]["embedding_model_id"] == "bge-m3"
    assert sql.goal_tasks["GT1"]["embedding_status"] == "ok"


def test_update_goal_task_reembeds(sql, writer):
    """T2 update_goal_task：UPDATE 後重 embed。"""
    writer.create_goal_task(
        goal_task_id="GT1", project_id="P1", parent_id=None,
        title="A", description="B", depth=1,
    )
    res = writer.update_goal_task(
        goal_task_id="GT1",
        new_title="Updated title",
    )
    assert res.embedding_status == EMBEDDING_STATUS_OK
    assert sql.goal_tasks["GT1"]["title"] == "Updated title"
    # embedding_attempts 應累加（create=1, update=1 → 2）
    assert sql.goal_tasks["GT1"]["embedding_attempts"] >= 2


def test_complete_execution_item_writes_embedding(sql, writer):
    """T3 complete_execution_item：UPDATE result + embedding。"""
    res = writer.complete_execution_item(
        exec_id="EX1",
        result_summary="all 3 tests passed",
        actual_minutes=12,
    )
    assert res.embedding_status == EMBEDDING_STATUS_OK
    row = sql.execution_items["EX1"]
    assert row["status"] == "ok"
    assert row["embedding_v"] is not None
    assert row["actual_minutes"] == 12


def test_embedder_failure_marks_status_failed(sql):
    """T4 embedder 故障時：業務列保留 + status=failed + attempts++。"""
    bad_embedder = _FakeEmbedder(fail_n_times=99)
    writer = EmbeddingWriter(
        embedder=bad_embedder,
        sql_executor=sql,
        pii_filter=PIIFilter(enabled=True),
        alert_after_attempts=5,
    )
    res = writer.create_goal_task(
        goal_task_id="GT2", project_id="P1", parent_id=None,
        title="Will fail", description="-",
    )
    assert res.embedding_status == EMBEDDING_STATUS_FAILED
    # 業務列仍在
    assert sql.goal_tasks["GT2"]["title"] == "Will fail"
    assert sql.goal_tasks["GT2"]["embedding_status"] == "failed"


def test_slo_alert_fires_after_threshold(sql):
    """T5 attempts 達 alert_after_attempts → 觸發 SLO observer（PM #9）。"""
    bad_embedder = _FakeEmbedder(fail_n_times=99)
    alerts: list[SLOAlert] = []
    writer = EmbeddingWriter(
        embedder=bad_embedder,
        sql_executor=sql,
        pii_filter=PIIFilter(enabled=True),
        alert_after_attempts=2,  # 設低門檻便於測試
        alert_observer=alerts.append,
    )
    # 第一次：attempts=1，未觸發
    writer.create_goal_task(
        goal_task_id="GT3", project_id="P1", parent_id=None,
        title="t1", description="d1",
    )
    assert alerts == []
    # 第二次：update 再 fail 一次，attempts=2 觸發告警
    writer.update_goal_task(goal_task_id="GT3", new_description="d2")
    assert len(alerts) == 1
    assert alerts[0].attempts >= 2
    assert alerts[0].namespace == "goal_tasks"


def test_pii_secret_blocks_write(sql, embedder):
    """T6 SECRET 欄位嘗試入庫 → PIIFilterViolation（拒絕）。"""
    pii = PIIFilter(
        registry=FieldRegistry(rules={
            "goal_tasks.description": PIIClassification.SECRET,
        }),
        enabled=True,
    )
    writer = EmbeddingWriter(embedder=embedder, sql_executor=sql, pii_filter=pii)
    with pytest.raises(PIIFilterViolation):
        writer.create_goal_task(
            goal_task_id="GT4", project_id="P1", parent_id=None,
            title="ok", description="leaked key",
        )


def test_pii_class_masks_email(sql, embedder):
    """T7 PII 類 → 自動 mask（不阻斷寫入，原 email 不出現於 row）。"""
    pii = PIIFilter(
        registry=FieldRegistry(rules={
            "goal_tasks.description": PIIClassification.PII,
        }),
        enabled=True,
    )
    writer = EmbeddingWriter(embedder=embedder, sql_executor=sql, pii_filter=pii)
    writer.create_goal_task(
        goal_task_id="GT5", project_id="P1", parent_id=None,
        title="contact",
        description="reach me at alice@example.com",
    )
    row = sql.goal_tasks["GT5"]
    assert "alice@example.com" not in row["description"]
    assert "<masked:" in row["description"] or "***" in row["description"]


def test_writer_does_not_swallow_unknown_exception(sql):
    """T8 非 EmbedderError 的例外不被 swallow。"""
    class _Bomb(_FakeEmbedder):
        def embed_one(self, text: str) -> list[float]:
            raise RuntimeError("unexpected")

    writer = EmbeddingWriter(embedder=_Bomb(), sql_executor=sql,
                             pii_filter=PIIFilter(enabled=True))
    with pytest.raises(RuntimeError):
        writer.create_goal_task(
            goal_task_id="GT6", project_id="P1", parent_id=None,
            title="x", description="y",
        )
