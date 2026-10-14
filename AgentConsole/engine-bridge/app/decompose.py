"""目標拆解：包 AutoClaude 的 GoalDecomposer（三道有界閘 ＋ 🔴 人工 signoff 硬閘）。

引擎的 `DecompositionError` 只帶中文訊息、沒有結構化代碼，但 GoalDecomposer 每次拒絕都會經
IObservabilityPort 記一筆 `decomposition_rejected{reason}`——這裡用一個記錄用的 port 接住它，
再對照到契約的 `gate`（max_steps／cycle／empty_prompt／brain_unsupported／brain_failed）。
契約只列五種 gate，引擎另有幾種拒絕原因，歸併如下（decompose 回應的 `detail` 保留原訊息）：
  duplicate_step_id、dangling_dependency → cycle（DAG 結構閘）；empty_goal → empty_prompt；
  no_steps、brain_returned_none → brain_failed。
草稿存檔在 `<workspace>/_drafts/<draft_id>.json`，Bridge 重啟後仍可 approve。
"""
from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autoclaude.core.ports.brain import BrainCapabilities, IBrain, RetryPolicy
from autoclaude.core.ports.observability import NullObservability
from autoclaude.execution.goal_decomposer import (
    MAX_DECOMPOSITION_STEPS,
    DecompositionDraft,
    DecompositionError,
    GoalDecomposer,
)
from autoclaude.models.playbook import Playbook

from . import security
from .errors import ApiError
from .fsutil import read_json, write_json_atomic
from .models import ApproveIn, DecomposeIn
from .security import AuditLog

GATE_BY_REASON = {
    "too_many_steps": "max_steps",
    "cycle_detected": "cycle",
    "duplicate_step_id": "cycle",
    "dangling_dependency": "cycle",
    "empty_prompt": "empty_prompt",
    "empty_goal": "empty_prompt",
    "brain_unsupported": "brain_unsupported",
    "brain_returned_none": "brain_failed",
    "no_steps": "brain_failed",
}
BrainFactory = Callable[[dict[str, Any]], IBrain]


def default_brain_factory(minimax: dict[str, Any]) -> IBrain:
    """真 Brain：MinimaxClient ＋ MinimaxBrainAdapter（缺金鑰時 MinimaxClient 自己會拒絕）。"""
    from autoclaude.decision.minimax_client import MinimaxClient
    from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter

    client = MinimaxClient(api_key=minimax["api_key"], base_url=minimax["base_url"],
                           model=minimax["model"], timeout=minimax["timeout"])
    return MinimaxBrainAdapter(client)


class _Recorder(NullObservability):
    """接住 GoalDecomposer 的稽核事件：拒絕原因用來對照 gate，所有 decomposition_* 進審計 log。"""

    def __init__(self, audit: AuditLog, draft_id: str | None = None):
        self._audit = audit
        self._draft_id = draft_id
        self.rejections: list[str] = []

    def record_event(self, name: str, attributes: Mapping[str, object] | None = None) -> None:
        attrs = {k: (v[:200] if isinstance(v, str) else v) for k, v in (attributes or {}).items()}
        if name == "decomposition_rejected":
            self.rejections.append(str(attrs.get("reason", "")))
        if name.startswith("decomposition_"):
            self._audit.record(name, draft_id=self._draft_id, **attrs)


class _NoBrain:
    """approve() 不會用到 Brain；GoalDecomposer 的建構式要有一個，給它一個永不被呼叫的替身。"""

    def capabilities(self) -> BrainCapabilities:
        return BrainCapabilities(max_context_tokens=0, supports_streaming=False,
                                 retry_policy=RetryPolicy(), model_id="none", dimension=0)


class DraftStore:
    def __init__(self, directory: Path):
        self._dir = directory
        self._mutex = threading.Lock()

    def _path(self, draft_id: str) -> Path | None:
        """draft_id 必須是 UUID（有無連字號皆可）；檔名只用解析後的 hex，絕不拼呼叫端字串。"""
        try:
            return self._dir / f"{uuid.UUID(draft_id).hex}.json"
        except (ValueError, AttributeError, TypeError):
            return None

    def create(self, doc: dict[str, Any]) -> str:
        draft_id = str(uuid.uuid4())
        with self._mutex:
            write_json_atomic(self._dir / f"{uuid.UUID(draft_id).hex}.json",
                              {"draft_id": draft_id, **doc})
        return draft_id

    def load(self, draft_id: str) -> dict[str, Any] | None:
        path = self._path(draft_id)
        doc = read_json(path) if path else None
        return doc if isinstance(doc, dict) else None

    def save(self, draft_id: str, doc: dict[str, Any]) -> None:
        path = self._path(draft_id)
        if path is not None:
            with self._mutex:
                write_json_atomic(path, doc)


def _playbook_dict(playbook: Playbook) -> dict[str, Any]:
    return playbook.model_dump(exclude_none=True)


class DecomposeService:
    def __init__(self, settings: Any, audit: AuditLog, drafts: DraftStore,
                 brain_factory: BrainFactory = default_brain_factory):
        self._settings = settings
        self._audit = audit
        self._drafts = drafts
        self._brain_factory = brain_factory

    def _effective_minimax(self, overrides: dict[str, Any]) -> dict[str, Any]:
        """優先序與引擎 main.py 相同：env ＞ config（＝請求的 config_overrides）＞ 預設。"""
        from autoclaude.utils.config import AppConfig

        base = AppConfig().minimax
        section = overrides.get("minimax") or {}
        return {
            "api_key": os.environ.get("MINIMAX_API_KEY", ""),
            "base_url": (os.environ.get("MINIMAX_BASE_URL") or section.get("base_url")
                         or base.base_url),
            "model": os.environ.get("MINIMAX_MODEL") or section.get("model") or base.model,
            "timeout": section.get("timeout_seconds") or base.timeout_seconds,
        }

    def _sanitize(self, body: DecomposeIn, minimax: dict[str, Any]) -> None:
        allow = self._settings.outbound_allowlist
        violations = security.validate_config_overrides(
            body.config_overrides, allow, audit=self._audit, context={"endpoint": "decompose"})
        if not violations:
            violations = security._check_url_field(
                minimax["base_url"], "effective.minimax.base_url", allow, self._audit,
                {"endpoint": "decompose"})
        if violations:
            raise ApiError(422, "sanitization_failed", gate="brain_unsupported",
                           detail="Brain 設定未通過消毒（外呼白名單／設定檢查）",
                           violations=violations)

    def decompose(self, body: DecomposeIn) -> dict[str, Any]:
        minimax = self._effective_minimax(body.config_overrides)
        self._sanitize(body, minimax)
        recorder = _Recorder(self._audit)
        try:
            brain = self._brain_factory(minimax)
        except Exception as exc:                                  # noqa: BLE001
            # 最常見：沒設 MINIMAX_API_KEY（MinimaxClient 建構即拒絕）。是「這個 Brain 用不了」。
            raise ApiError(422, "brain_unsupported", gate="brain_unsupported",
                           detail=f"無法建立 Brain：{exc}") from exc
        decomposer = GoalDecomposer(
            brain, max_steps=min(body.max_steps, MAX_DECOMPOSITION_STEPS), observability=recorder)
        try:
            draft = decomposer.decompose(body.goal, context=body.context, project=body.project)
        except DecompositionError as exc:
            reason = recorder.rejections[-1] if recorder.rejections else ""
            gate = GATE_BY_REASON.get(reason, "brain_failed")
            raise ApiError(422, reason or "decomposition_rejected", gate=gate,
                           detail=str(exc)) from exc
        playbook = _playbook_dict(draft.playbook)
        draft_id = self._drafts.create({
            "goal": draft.goal, "goal_hash": draft.goal_hash, "reasoning": draft.reasoning,
            "playbook": playbook, "signed_off": False, "approver": "", "approved_at": "",
            "created_at": datetime.now(UTC).isoformat(),
        })
        return {"draft_id": draft_id, "goal_hash": draft.goal_hash, "reasoning": draft.reasoning,
                "playbook": playbook, "signed_off": False}

    def approve(self, draft_id: str, body: ApproveIn) -> dict[str, Any]:
        approver = (body.approver or "").strip()
        if not approver:
            raise ApiError(400, "approver_required",
                           detail="signoff 需要 approver（人工棘輪不可匿名）")
        doc = self._drafts.load(draft_id)
        if doc is None:
            raise ApiError(404, "draft_not_found", draft_id=draft_id)
        if doc.get("signed_off"):
            if doc.get("approver") == approver:               # 同一人重送：冪等
                return self._approved_body(doc)
            raise ApiError(409, "already_signed_off", draft_id=draft_id,
                           approver=doc.get("approver"), approved_at=doc.get("approved_at"))
        draft = DecompositionDraft(
            playbook=Playbook(**doc["playbook"]), goal=doc["goal"], goal_hash=doc["goal_hash"],
            reasoning=doc.get("reasoning", ""))
        recorder = _Recorder(self._audit, draft_id)
        decomposer = GoalDecomposer(_NoBrain(), observability=recorder)  # type: ignore[arg-type]
        try:
            signed = decomposer.approve(draft, approver=approver)
        except DecompositionError as exc:
            raise ApiError(400, "approver_required", detail=str(exc)) from exc
        doc.update(signed_off=True, approver=signed.approver, approved_at=signed.approved_at)
        self._drafts.save(draft_id, doc)
        return self._approved_body(doc)

    @staticmethod
    def _approved_body(doc: dict[str, Any]) -> dict[str, Any]:
        return {"signed_off": True, "approver": doc["approver"], "approved_at": doc["approved_at"],
                "playbook": doc["playbook"]}
