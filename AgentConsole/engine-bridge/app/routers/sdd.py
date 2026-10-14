"""/sdd/*：AISDLC_SDD 唯讀查詢（版本、FSM 狀態）與規格編譯（SddToPlaybookAdapter）。"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Request

from .. import security
from ..errors import ApiError, not_found, unprocessable
from ..models import SddCompileIn

router = APIRouter(prefix="/sdd", tags=["sdd"])

_PROJECT_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
FSM_TRAIL = 5


def _sdd_root(request: Request) -> Path:
    root = request.app.state.settings.sdd_root
    if root is None or not root.is_dir():
        raise ApiError(503, "sdd_unavailable",
                       detail="找不到 AISDLC_SDD 目錄；請設定 SDD_ROOT（Docker 需掛載）")
    return root


@router.get("/version")
def sdd_version(request: Request) -> dict[str, str]:
    root = _sdd_root(request)
    return {"latest": root.name, "root": str(root)}


@router.get("/fsm/{project}")
def fsm_state(project: str, request: Request) -> dict[str, Any]:
    fsm_dir = _sdd_root(request) / "build" / "reports" / "fsm"
    if not _PROJECT_RE.match(project):
        raise not_found("fsm_not_found", project=project)
    path = fsm_dir / f"FSM-STATE-{project}.yaml"
    # 路徑已由白名單 regex 擋掉分隔符；再確認 resolve 後仍在 fsm 目錄內（防 symlink 逃逸）。
    if not path.is_file() or not security.is_within(path.resolve().parent, fsm_dir):
        raise not_found("fsm_not_found", project=project)
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ApiError(422, "fsm_state_unreadable", detail=str(exc)) from exc
    state = doc.get("fsm_state") if isinstance(doc, dict) else None
    if not isinstance(state, dict):
        raise ApiError(422, "fsm_state_unreadable", detail="缺少 fsm_state 根節點")
    trace = state.get("decision_trace") or []
    return {
        "project": state.get("project", project),
        "current_state": state.get("current_state"),
        "current_sprint": state.get("current_sprint"),
        "session_id": state.get("session_id"),
        "updated_at": state.get("updated_at"),
        "frozen_stages": state.get("frozen_stages") or [],
        "decision_trace": trace[-FSM_TRAIL:] if isinstance(trace, list) else [],
        "source": path.name,
    }


@router.post("/compile")
def compile_spec(body: SddCompileIn, request: Request) -> dict[str, Any]:
    from autoclaude.core.ports.spec_source import (
        SpecFormatVersionError,
        SpecNotFrozenError,
        SpecTaintedError,
    )
    from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter

    settings = request.app.state.settings
    spec_dir, violations = security.check_path(
        body.spec_dir, settings.allowed_path_roots, field="spec_dir")
    if violations or spec_dir is None:
        raise unprocessable(violations)
    adapter = SddToPlaybookAdapter()
    try:
        spec = adapter.load_spec(str(spec_dir))
        tasks = adapter.compile_tasks(spec)
    except SpecNotFrozenError as exc:
        raise ApiError(422, "spec_not_frozen", detail=str(exc)) from exc
    except SpecTaintedError as exc:
        raise ApiError(422, "spec_tainted", detail=str(exc)) from exc
    except SpecFormatVersionError as exc:
        raise ApiError(422, "spec_format_version_unsupported", detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise ApiError(422, "spec_not_found", detail=str(exc)) from exc
    except ValueError as exc:
        raise ApiError(422, "spec_ambiguous", detail=str(exc)) from exc
    return {
        "tasks": [t.model_dump(exclude_none=True) for t in tasks],
        "scenario": spec.scenario,
        "contracts": [dataclasses.asdict(c) for c in spec.contracts],
        "spec_path": spec.spec_path,
        "digest": spec.digest,
        "spec_format_version": spec.spec_format_version,
    }
