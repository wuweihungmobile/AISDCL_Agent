"""/sdd/*：AISDLC_SDD 查詢（版本、FSM 狀態）、唯一的 FSM 寫入動詞 `:freeze`、規格編譯
（SddToPlaybookAdapter）。

寫入面（ADR-XPLAT-016）：`POST /sdd/fsm/{project}:freeze` 是 Console 路徑上唯一的人工閘寫入動詞——
帶 `X-Bridge-Token`（`security.require_sdd_write_token`）、經 FSMRuntime CLI 子行程
（`sdd_cli.run_verb`，固定環境、動詞白名單、`(狀態目錄, 專案鍵)` 互斥）。本檔**不開寫
`FSM-STATE-*.yaml`**（Rule 9 絕對
禁令 #1；
AST 鎖在 tests/test_sdd_integration_parity.py）；讀取一律在 `state_guard` 之內。
專案名一律先過 `fsm_names.fsm_component`（原名與淨化後的鍵等價）。
"""
from __future__ import annotations

import dataclasses
import os
import posixpath
import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, Query, Request

from .. import procutil, sdd_adapter, security, spec_digest
from ..errors import ApiError, fsm_state_conflict, spec_digest_changed, unprocessable
from ..fsm_names import fsm_component, is_fsm_project_name
from ..fsm_phase import phase_of
from ..models import SddCompileIn, SddFreezeIn
from ..sdd_cli import (
    VERB_SPEC_FROZEN,
    freeze_args,
    run_verb,
    state_guard,
)
from ..sdd_state import (
    ESCALATION_STATES,
    STATE_PREFIX,
    STATE_SUFFIX,
    TRAIL,
    frozen_stage_count,
    load_state,
    read_state,
    readable_state_file,
    recovery_commands,
    state_dir_of,
    tail,
)
from ..sdd_sync import clean_approver, clean_user_reason, default_stage, reason_freeze
from ..tracing import trace_id_var

router = APIRouter(prefix="/sdd", tags=["sdd"])

FSM_TRAIL = TRAIL
#: `human_pending.items` 最多回幾筆（尾端）。
HUMAN_PENDING_TRAIL = 5
#: 官方 TCS 命名（與 adapter 的 `_EXACT_CONTRACT_SPEC_RE` 同形）：`TEST-CONTRACT-SPEC-*`｜`TCS-*`。
_TCS_NAME = re.compile(r"^(TEST-CONTRACT-SPEC-|TCS-)", re.IGNORECASE)
_ABSOLUTE_DOC = re.compile(r"^(?:/|[A-Za-z]:)")
_GIT_CHECK_TIMEOUT_SECONDS = 5.0


def _sdd_root(request: Request) -> Path:
    root = request.app.state.settings.sdd_root
    if root is None or not root.is_dir():
        raise ApiError(503, "sdd_unavailable",
                       detail="找不到 AISDLC_SDD 目錄；請設定 SDD_ROOT（Docker 需掛載）")
    return root


def _project_root(request: Request, root: str | None) -> Path:
    """專案根：`root` 省略＝SDD 版本目錄（v1.4 行為）；有給＝過 `BRIDGE_ALLOWED_PATH_ROOTS` 的
    realpath。"""
    if root is None:
        return _sdd_root(request)
    resolved, violations = security.check_path(
        root, request.app.state.settings.allowed_path_roots, field="root")
    if violations or resolved is None:
        raise unprocessable(violations)
    return resolved


def _fsm_dir(request: Request, root: str | None) -> Path:
    """`<root>/build/reports/fsm`（取代預設的 `<SDD_ROOT>/build/reports/fsm`）。
    不論有沒有 `root`，`SDD_ROOT` 無效一律先 503（CLI 與版本資訊仍需要它）。"""
    sdd_root = _sdd_root(request)
    return state_dir_of(sdd_root if root is None else _project_root(request, root))


@router.get("/version")
def sdd_version(request: Request) -> dict[str, str]:
    root = _sdd_root(request)
    return {"latest": root.name, "root": str(root)}


@router.get("/fsm")
def fsm_list(request: Request, root: str | None = Query(default=None)) -> dict[str, Any]:
    """列出 `<狀態目錄>/FSM-STATE-*.yaml`（D-16）。`project`＝檔名去掉前綴與副檔名，也就是
    `GET /sdd/fsm/{project}` 吃的那個鍵；讀不動或名稱不在淨化輸出域（`is_fsm_project_name`）的檔名放
    `errors`。目錄不存在（git 不追蹤它，全新 clone 沒有）不是錯：回空清單。`root` 選填（v1.5）。"""
    sdd_root = _sdd_root(request)
    fsm_dir = _fsm_dir(request, root)
    projects: list[dict[str, Any]] = []
    errors: list[str] = []
    if fsm_dir.is_dir():
        files = sorted(fsm_dir.glob(f"{STATE_PREFIX}*{STATE_SUFFIX}"),
                       key=lambda p: p.name.casefold())
        for path in files:
            project = path.name[len(STATE_PREFIX):-len(STATE_SUFFIX)]
            if not is_fsm_project_name(project):
                errors.append(path.name)
                continue
            with state_guard(fsm_dir, project):
                if readable_state_file(fsm_dir, project) is None:
                    errors.append(path.name)
                    continue
                try:
                    state = load_state(path)
                except ApiError:
                    errors.append(path.name)
                    continue
            projects.append({"project": project, "source": path.name,
                             "current_state": state.get("current_state"),
                             "updated_at": state.get("updated_at")})
    return {"root": sdd_root.name, "projects": projects, "errors": errors}


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


def _state_view(state: dict[str, Any], *, source: str, key: str, sdd_root: Path,
                fsm_dir: Path) -> dict[str, Any]:
    """`GET /sdd/fsm/{project}` 與 `:freeze` 成功回應的共同形狀。既有欄位一個都不動，只增不減。"""
    trace = state.get("decision_trace") or []
    provenance = state.get("escalation_provenance")
    current = state.get("current_state")
    # 壞檔的 current_state 可能是 list／dict（不可 hash）：先判型別，不能直接 `in` frozenset
    # （會 500）。
    escalated = isinstance(current, str) and current in ESCALATION_STATES
    view: dict[str, Any] = {
        "project": state.get("project", key),
        "current_state": current,
        "current_sprint": state.get("current_sprint"),
        "session_id": state.get("session_id"),
        "updated_at": state.get("updated_at"),
        "frozen_stages": state.get("frozen_stages") or [],
        "decision_trace": trace[-FSM_TRAIL:] if isinstance(trace, list) else [],
        "source": source,
        # D-16 新增：真實檔沒有 RTM 覆蓋數值，所以通常為 null；只有檔內有 `rtm_coverage` 鍵時才原
        # 樣帶出。
        "human_pending": _human_pending(state.get("human_pending_tracking")),
        "retry_history": _retry_history(state.get("retry_history")),
        "rtm_coverage": state.get("rtm_coverage"),
        # v1.5：`phase`＝current_state 的純函式投影（app/fsm_phase.py，契約 §3.1.5；W4 dogfood
        # 產物）。欄位永遠出現；缺值、非字串、不認得的狀態回 UNKNOWN／0 物件（不是 null）。
        "phase": phase_of(current),
        "escalation_history": tail(state.get("escalation_history")),
        # 辨識「這是委派失敗」要讀 provenance.source（trace 那筆是 ESCALATION→ESCALATION，不可靠）。
        # 🔴 provenance 與 `autoclaude_delegated_tracking` 在人工恢復後都**不會被清除**：判斷「現
        # 在有沒有未解的委派失敗」要看 current_state 屬 ESCALATION 類且
        # escalation_history[-1].resolved_at
        # 為空。
        "escalation_provenance": provenance if isinstance(provenance, dict) else None,
        # 狀態檔名裡淨化後的鍵（`project` 是檔內原名，兩者可能不同；寫回綁定與唯一性檢查要用這個）。
        "fsm_project": key,
    }
    # ESCALATION／ESCALATION_FINAL 時的可複製恢復指令（恢復只有人能做、留在 SDD session）；其餘
    # 情形**鍵缺席**（契約 v1.5 §3.1.4 (c)：「或鍵缺席」，不是 null）。
    if escalated:
        view["recovery"] = recovery_commands(state, sdd_root=sdd_root, fsm_dir=fsm_dir, key=key)
    return view


@router.get("/fsm/{project}")
def fsm_state(project: str, request: Request,
              root: str | None = Query(default=None)) -> dict[str, Any]:
    sdd_root = _sdd_root(request)
    fsm_dir = _fsm_dir(request, root)
    key = fsm_component(project)            # 傳原名與傳淨化後的鍵等價（ADR §7.4）
    with state_guard(fsm_dir, key):
        path, state = read_state(fsm_dir, key, display_name=project)
    return _state_view(state, source=path.name, key=key, sdd_root=sdd_root, fsm_dir=fsm_dir)


# ── POST /sdd/fsm/{project}:freeze ───────────────────────────────────────────────────────
def _doc_violation(index: int, rule: str, message: str) -> dict[str, Any]:
    return {"field": f"docs[{index}]", "rule": rule, "message": message}


def normalize_doc(raw: str) -> str | None:
    """`docs[]`／`expected_digests` 鍵的 POSIX 正規形；絕對路徑或含 `..` 片段＝None（呼叫端另判規
    則碼）。"""
    text = raw.replace("\\", "/")
    if _ABSOLUTE_DOC.match(text) or ".." in text.split("/"):
        return None
    return posixpath.normpath(text)


def _check_docs(root: Path, docs: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """逐項檢查（規則碼 absolute／contains_dotdot／outside_root／not_found，另有 duplicate／
    invalid）。"""
    normalized: list[str] = []
    violations: list[dict[str, Any]] = []
    for index, raw in enumerate(docs):
        text = raw.replace("\\", "/")
        if not raw.strip() or "\x00" in raw:
            violations.append(_doc_violation(index, "invalid", "路徑不可為空白或含 NUL"))
        elif _ABSOLUTE_DOC.match(text) or os.path.isabs(raw):
            violations.append(_doc_violation(index, "absolute", f"必須是相對 root 的路徑：{raw}"))
        elif ".." in text.split("/"):
            violations.append(_doc_violation(index, "contains_dotdot", f"不接受 `..` 片段：{raw}"))
        else:
            rel = posixpath.normpath(text)
            resolved = (root / rel).resolve()
            if not security.is_within(resolved, root):
                violations.append(_doc_violation(index, "outside_root", f"不在 root 之下：{raw}"))
            elif not resolved.is_file():
                violations.append(_doc_violation(index, "not_found", f"不是既有檔案：{raw}"))
            elif rel in normalized:
                violations.append(_doc_violation(index, "duplicate", f"重複的文件：{raw}"))
            else:
                normalized.append(rel)
    return normalized, violations


def _check_expected_digests(root: Path, docs: list[str], expected: dict[str, str] | None) -> None:
    """核准人當時看到的摘要 vs 現檔：不符＝409 `spec_digest_changed`
    （`detail.pair=expected_vs_file`）。"""
    if not expected:
        return
    violations: list[dict[str, Any]] = []
    checks: list[tuple[str, str]] = []
    for raw_key, digest in expected.items():
        key = normalize_doc(raw_key)
        if key is None or key not in docs:
            violations.append({"field": f"expected_digests.{raw_key}", "rule": "not_in_docs",
                               "message": "expected_digests 的鍵必須是 docs[] 內的文件"})
        else:
            checks.append((key, digest))
    if violations:
        raise unprocessable(violations)
    for key, digest in checks:
        try:
            current = spec_digest.file_digest(root / key)
        except spec_digest.DocTooLargeError as exc:
            raise unprocessable(
                [{"field": "docs", "rule": "too_large", "message": str(exc)}]) from exc
        except spec_digest.DocNotUtf8Error as exc:
            raise unprocessable(
                [{"field": "docs", "rule": "not_utf8", "message": str(exc)}]) from exc
        except OSError as exc:
            raise unprocessable([{"field": "docs", "rule": "not_found",
                                  "message": f"{key} 無法讀取（{type(exc).__name__}）"}]) from exc
        if current != digest:
            raise spec_digest_changed("expected_vs_file", doc=key, expected_digest=digest,
                                      current_digest=current)


def _freeze(project: str, key: str, body: SddFreezeIn, request: Request, *, approver: str,
            user_reason: str) -> dict[str, Any]:
    settings = request.app.state.settings
    sdd_root = _sdd_root(request)
    root, violations = security.check_path(body.root, settings.allowed_path_roots, field="root")
    if violations or root is None:
        raise unprocessable(violations)
    fsm_dir = state_dir_of(root)
    with state_guard(fsm_dir, key):
        _, state = read_state(fsm_dir, key, display_name=project)             # 404／422
        docs, violations = _check_docs(root, body.docs)
        if violations:
            raise unprocessable(violations)
        if not any(_TCS_NAME.match(posixpath.basename(d)) for d in docs):
            raise unprocessable([{
                "field": "docs", "rule": "missing_tcs",
                "message": "docs[] 必須含官方命名的 TCS（TEST-CONTRACT-SPEC-*｜TCS-*）"}])
        if state.get("current_state") != "HUMAN_PENDING":
            raise fsm_state_conflict(state.get("current_state"), expected_state="HUMAN_PENDING")
        _check_expected_digests(root, docs, body.expected_digests)
        stage = body.stage or default_stage(frozen_stage_count(state))
        out = run_verb(
            VERB_SPEC_FROZEN,
            freeze_args(stage=stage, docs=docs, root=str(root),
                        reason=reason_freeze(approver, user_reason), approver=approver),
            sdd_root=sdd_root, state_dir=fsm_dir, project=key,
            audit=request.app.state.audit, approver=approver,
            context={"stage": stage, "docs": docs})
        path, state = read_state(fsm_dir, key, display_name=project)           # 凍結後重讀
    view = _state_view(state, source=path.name, key=key, sdd_root=sdd_root, fsm_dir=fsm_dir)
    digests = out.get("spec_doc_digests")
    view["stage"] = stage
    view["spec_doc_digests"] = digests if isinstance(digests, dict) else {}
    return view


@router.post("/fsm/{project}:freeze")
def freeze(project: str, body: SddFreezeIn, request: Request,
           x_bridge_token: str | None = Header(default=None)) -> dict[str, Any]:
    """核准凍結（人工閘；`HUMAN_PENDING`→`SPEC_FROZEN`）。檢查順序（固定；契約 §3.1.4 (d)＋ADR
    §6.3①）：①本文格式（422 invalid_request）②權杖（503／403）③approver／reason 清理（422
    sdd_invalid_argument）④`root`（422 sanitization_failed）⑤專案與狀態檔（404／422）⑥`docs[]` 逐
    項（422 sanitization_failed）＋含 TCS（422 `missing_tcs`）⑦前置狀態 HUMAN_PENDING（409
    fsm_state_conflict）⑧`expected_digests`比對（409 spec_digest_changed）⑨CLI 記錄凍結（摘要由
    CLI 算並寫進
    `frozen_stages[].spec_doc_digests`）。
    成功與被拒都記一筆稽核 `sdd_write`（決策：project、approver、stage、docs、結果、trace_id；不含
    權杖）。"""
    audit = request.app.state.audit
    key = fsm_component(project)
    security.require_sdd_write_token(
        request.app.state.settings.sdd_write_token, x_bridge_token, audit=audit,
        verb="freeze", project=key, approver=body.approver)
    approver_shown = body.approver[:100]
    try:
        approver = clean_approver(body.approver)
        user_reason = clean_user_reason(body.reason)
        result = _freeze(project, key, body, request, approver=approver, user_reason=user_reason)
    except ApiError as exc:
        audit.record("sdd_write", verb="freeze", project=key, approver=approver_shown,
                     result=f"rejected:{exc.body['reason']}", trace_id=trace_id_var.get())
        raise
    audit.record("sdd_write", verb="freeze", project=key, approver=approver, result="ok",
                 stage=result["stage"], docs=body.docs, trace_id=trace_id_var.get())
    return result


# ── POST /sdd/compile ────────────────────────────────────────────────────────────────────
def _state_dir_ignored(root: Path) -> bool | None:
    """`git -C <root> check-ignore -q -- build/reports/fsm/FSM-STATE-x.yaml`：rc 0＝已忽略、1＝未
    忽略、其餘（128＝非 git 工作樹、找不到 git、逾時）＝None（略過，只警告不擋）。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--",
             "build/reports/fsm/FSM-STATE-x.yaml"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=_GIT_CHECK_TIMEOUT_SECONDS, check=False, **procutil.popen_platform_kwargs())
    except (OSError, subprocess.SubprocessError):
        return None
    return {0: True, 1: False}.get(proc.returncode)


def _state_root_of(spec_dir: Path) -> Path | None:
    """自 `spec_dir` 向上找第一個含 `build/reports/fsm` 的目錄（與 adapter 找狀態檔同一個走法）。"""
    for candidate in (spec_dir, *spec_dir.parents):
        if state_dir_of(candidate).is_dir():
            return candidate
    return None


def _relative_posix(path: str, base: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), base)).as_posix()


@router.post("/compile")
def compile_spec(body: SddCompileIn, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    spec_dir, violations = security.check_path(
        body.spec_dir, settings.allowed_path_roots, field="spec_dir")
    if violations or spec_dir is None:
        raise unprocessable(violations)
    spec_file: Path | None = None
    if body.spec_file is not None:
        spec_file, violations = security.check_spec_file(
            spec_dir, body.spec_file, field="spec_file")
        if violations:
            if violations[0]["rule"] == "not_found":
                raise ApiError(422, "spec_not_found", detail=violations[0]["message"])
            raise unprocessable(violations)
    if body.fsm_project is not None and not body.fsm_project.strip():
        raise unprocessable([{"field": "fsm_project", "rule": "empty",
                              "message": "fsm_project 不可為空白（省略即不指定）"}])
    # 顯式傳值、含空字串：空字串＝明確不指定、不讀 Bridge 自己的環境（開發機匯出 SDD_PROJECT 是常
    # 態）。
    fsm_key = "" if body.fsm_project is None else fsm_component(body.fsm_project)
    adapter = sdd_adapter.build_adapter(fsm_key)
    try:
        spec = sdd_adapter.load_spec(adapter, spec_dir, spec_file)
        tasks = adapter.compile_tasks(spec)
    except (RuntimeError, ValueError, OSError) as exc:
        sdd_adapter.raise_for_spec_error(exc)
        raise                                    # 到不了：raise_for_spec_error 必丟
    warnings: list[dict[str, Any]] = []
    state_root = _state_root_of(spec_dir)
    if state_root is not None and _state_dir_ignored(state_root) is False:
        warnings.append({
            "code": "state_dir_not_ignored",
            "detail": f"{state_root}／build/reports/fsm/ 未被 git 忽略：FSM 狀態檔是執行期產物，"
                      "請把 build/reports/ 加進 .gitignore（不入庫）"})
    return {
        "tasks": [t.model_dump(exclude_none=True) for t in tasks],
        "scenario": spec.scenario,
        "contracts": [dataclasses.asdict(c) for c in spec.contracts],
        "spec_path": spec.spec_path,
        "digest": spec.digest,
        "spec_format_version": spec.spec_format_version,
        # v1.5：綁定回填（路徑 A）與出聲用的欄位
        "spec_file": _relative_posix(spec.spec_path, spec_dir),
        "fsm_project": getattr(spec, "fsm_project", None) or (fsm_key or None),
        "frozen_digest": sdd_adapter.frozen_digest_status(spec),
        "unmapped_at_ids": list(getattr(spec, "unmapped_at_ids", ()) or ()),
        "warnings": warnings,
    }
