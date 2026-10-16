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
_STATE_PREFIX = "FSM-STATE-"
_STATE_SUFFIX = ".yaml"
FSM_TRAIL = 5
#: `human_pending.items` 最多回幾筆（尾端）。
HUMAN_PENDING_TRAIL = 5


def _sdd_root(request: Request) -> Path:
    root = request.app.state.settings.sdd_root
    if root is None or not root.is_dir():
        raise ApiError(503, "sdd_unavailable",
                       detail="找不到 AISDLC_SDD 目錄；請設定 SDD_ROOT（Docker 需掛載）")
    return root


def _readable_state_file(fsm_dir: Path, project: str) -> Path | None:
    """`FSM-STATE-<project>.yaml`；不是檔案、或 resolve 後跑出 fsm 目錄（symlink 逃逸）＝None。
    project 必須已通過 `_PROJECT_RE`（分隔符與 `..` 在那一關就被擋掉了）。"""
    path = fsm_dir / f"{_STATE_PREFIX}{project}{_STATE_SUFFIX}"
    if not path.is_file() or not security.is_within(path.resolve().parent, fsm_dir):
        return None
    return path


def _load_state(path: Path) -> dict[str, Any]:
    """讀出 `fsm_state` 根節點；讀不動、不是 YAML、缺根節點一律 422（不是 500）。"""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, RecursionError, yaml.YAMLError) as exc:
        raise ApiError(422, "fsm_state_unreadable", detail=str(exc)) from exc
    state = doc.get("fsm_state") if isinstance(doc, dict) else None
    if not isinstance(state, dict):
        raise ApiError(422, "fsm_state_unreadable", detail="缺少 fsm_state 根節點")
    return state


@router.get("/version")
def sdd_version(request: Request) -> dict[str, str]:
    root = _sdd_root(request)
    return {"latest": root.name, "root": str(root)}


@router.get("/fsm")
def fsm_list(request: Request) -> dict[str, Any]:
    """列出 `build/reports/fsm/FSM-STATE-*.yaml`（D-16）。`project`＝檔名去掉前綴與副檔名，
    也就是 `GET /sdd/fsm/{project}` 吃的那個鍵；讀不動或名稱不合白名單的檔名放 `errors`。
    該目錄不存在（git 不追蹤它，全新 clone 沒有）不是錯：回空清單。"""
    root = _sdd_root(request)
    fsm_dir = root / "build" / "reports" / "fsm"
    projects: list[dict[str, Any]] = []
    errors: list[str] = []
    if fsm_dir.is_dir():
        files = sorted(fsm_dir.glob(f"{_STATE_PREFIX}*{_STATE_SUFFIX}"),
                       key=lambda p: p.name.casefold())
        for path in files:
            project = path.name[len(_STATE_PREFIX):-len(_STATE_SUFFIX)]
            if not _PROJECT_RE.match(project) or _readable_state_file(fsm_dir, project) is None:
                errors.append(path.name)
                continue
            try:
                state = _load_state(path)
            except ApiError:
                errors.append(path.name)
                continue
            projects.append({"project": project, "source": path.name,
                             "current_state": state.get("current_state"),
                             "updated_at": state.get("updated_at")})
    return {"root": root.name, "projects": projects, "errors": errors}


def _human_pending(tracking: Any) -> dict[str, Any]:
    """`human_pending_tracking` → `{count, items}`。

    真實檔（FSM-STATE-TEMPLATE.yaml 與各專案的狀態檔）裡它是**單一 dict**：`entered_at`（進入
    HUMAN_PENDING 的時戳，離開時清成 null）、`reminder_sent_at`、`reminder_hours`、
    `escalation_hours`。所以：`entered_at` 有值＝正在等人（count 1、items 為該 dict 原樣），
    沒有＝count 0、items 空。若哪天它改成 list，則 count＝筆數、items＝尾端 5 筆原樣。"""
    if isinstance(tracking, list):
        return {"count": len(tracking), "items": tracking[-HUMAN_PENDING_TRAIL:]}
    if isinstance(tracking, dict) and tracking.get("entered_at"):
        return {"count": 1, "items": [tracking]}
    return {"count": 0, "items": []}


def _retry_history(history: Any) -> dict[str, Any]:
    """`retry_history` → `{count, last}`。

    真實檔裡它是 **dict of dict**，以重試閘為鍵（SCG_VALIDATION、PR_REVIEW、RTM_VERIFY），每個閘
    有 `current_count`、`max_limit` 與 `history`（list；每筆 `attempt`、`date`、
    `failure_reason`、`scg_gate`）。所以：count＝三個閘 `history` 筆數的總和；last＝全部筆中
    `date` 最晚者（同時刻取後出現的），原樣再加一個 `gate` 欄標明是哪個閘。若哪天它改成
    list，則直接取筆數與尾端一筆。"""
    if isinstance(history, list):
        return {"count": len(history), "last": history[-1] if history else None}
    if not isinstance(history, dict):
        return {"count": 0, "last": None}
    count = 0
    last: dict[str, Any] | None = None
    last_stamp = ""
    for gate, entry in history.items():
        records = entry.get("history") if isinstance(entry, dict) else None
        if not isinstance(records, list):
            continue
        for record in records:
            count += 1
            row = record if isinstance(record, dict) else {"value": record}
            stamp = str(row.get("date") or "")
            if last is None or stamp >= last_stamp:
                last_stamp = stamp
                last = {"gate": str(gate), **row}
    return {"count": count, "last": last}


@router.get("/fsm/{project}")
def fsm_state(project: str, request: Request) -> dict[str, Any]:
    fsm_dir = _sdd_root(request) / "build" / "reports" / "fsm"
    if not _PROJECT_RE.match(project):
        raise not_found("fsm_not_found", project=project)
    path = _readable_state_file(fsm_dir, project)
    if path is None:
        raise not_found("fsm_not_found", project=project)
    state = _load_state(path)
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
        # D-16 新增（只增不減）。真實檔沒有 RTM 覆蓋數值，所以通常為 null；只有檔內有 `rtm_coverage`
        # 鍵時才原樣帶出。
        "human_pending": _human_pending(state.get("human_pending_tracking")),
        "retry_history": _retry_history(state.get("retry_history")),
        "rtm_coverage": state.get("rtm_coverage"),
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
