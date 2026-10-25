"""/si/*：SelfImproving 的唯讀鏡像（TCS-SelfImprovingMirror-P1b R5；ADR-SI-12）與 Console 寫入載體
的稽核檔落地、唯讀預檢（TCS-SelfImprovingDecide-P2b W3、W4；PRD §9.5 ADR-SI-03′）。

**六個 GET**（P1b），每個請求恰啟動一次 `si_cli.run_export` 子行程（無快取、不寫任何檔）；200 時
本文是子行程輸出**解析後的 export 物件逐值透傳**（鍵序保留、非 ASCII 不跳脫，Bridge 不增刪改任何
鍵）。SI 不可用只影響 `/si/*`，不影響 `/health` 與 `/health/deep`。

輸入驗證在**子行程之前**：清單類只收 `since`（整數 ≥0）與 `limit`（整數 ≥1），其餘任何查詢參數
（含 `/si/status` 與 `/si/proposals/{id}` 上的這兩個）一律 422 `invalid_request`
（`rule=unknown_parameter`）；`{id}` 須符 `PROP-SI-<三位以上數字>`，不符 422；符合而 export 回空＝
404 `si_not_found`。`limit` 的上限住在協定參數檔，不在此複製：超過上限時 CLI 回 rc 3，
依 `si_cli` 的判定表回 503（`cause=nonzero_rc`）。

**三個寫入 POST**：`/si/proposals/{id}:decide`、`/si/observations`、`/si/observations/{id}:close`。
Bridge **不寫帳本、不呼叫寫入型 CLI**；它只把 backend 簽好的稽核 JSON 原樣落成
`BRIDGE_SI_AUDIT_DIR/<audit_ref>.json`（`si_audit.store_audit`），由主機端 CLI 驗簽入帳。檢查順序
（先中者定案；W3）：①寫入面停用＝503 `si_write_disabled`（先於權杖與本文）②`X-Bridge-Token` 缺或
錯＝403 `si_write_forbidden`③本文須為單一 UTF-8 JSON 物件且 ≤`SI_WRITE_BODY_MAX_BYTES`（超過即
422，不讀完）④外層恰七鍵、`schema_rev` 為整數 1、`kind` 等於端點、`audit_ref` 為小寫正規 UUID、
`subject` 與路徑 `{id}` 相符（obs-add 為 null）、`body`／`key_id`／`mac` 為字串，違規一律 422
`invalid_request`（`violations[{field,rule,message}]`；**不解內層 `body`、不驗簽**）⑤落檔
⑥201 `{"audit_ref","stored"}`。

**一個預檢 POST**：`/si/observations:validate`——不需權杖、不看寫入設定、不落檔，本文須為單一 JSON
物件且 ≤65536 位元組（否則 422，不啟動子行程），以子行程 `obs-add --dry-run` 回預覽（`ok` 為 false
仍是 200）。

其餘方法（DELETE、PUT、PATCH）對所有 `/si/` 路徑一律 405（FastAPI 對已知路徑的其他方法回 405）。
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from .. import security, si_audit, si_cli
from ..errors import ApiError
from ..tracing import trace_id_var

router = APIRouter(prefix="/si", tags=["si"])

#: ASCII 數字、整串比對：比 CLI 自己的格式略嚴（不收全形數字與結尾換行）。
_PROP_ID = re.compile(r"PROP-SI-[0-9]{3,}")
_DECIDE_ID = re.compile(r"(?:PROP|RUN)-SI-[0-9]{3,}")
_OBS_ID = re.compile(r"OBS-SI-[0-9]{3,}")
_LIST_PARAMS = frozenset({"since", "limit"})
#: 寫入類與預檢請求本文的上限（位元組）。
SI_WRITE_BODY_MAX_BYTES = 65536
#: 稽核 JSON 的外層鍵集合（恰此七個；W3、W7）。
_OUTER_KEYS = ("schema_rev", "kind", "audit_ref", "subject", "body", "key_id", "mac")


def _reject_unknown_params(request: Request, allowed: frozenset[str]) -> None:
    unknown = [name for name in request.query_params if name not in allowed]
    if unknown:
        raise ApiError(422, "invalid_request", violations=[
            {"field": name, "rule": "unknown_parameter", "message": f"不收查詢參數 {name!r}"}
            for name in unknown])


def _export(request: Request, kind: str, *, since: int | None = None,
            limit: int | None = None, ident: str | None = None) -> dict[str, Any]:
    return si_cli.run_export(request.app.state.settings.si_root, kind, since=since, limit=limit,
                             ident=ident)


@router.get("/status")
def si_status(request: Request) -> JSONResponse:
    _reject_unknown_params(request, frozenset())
    return JSONResponse(_export(request, "status"))


@router.get("/observations")
def si_observations(request: Request, since: int | None = Query(default=None, ge=0),
                    limit: int | None = Query(default=None, ge=1)) -> JSONResponse:
    _reject_unknown_params(request, _LIST_PARAMS)
    return JSONResponse(_export(request, "observations", since=since, limit=limit))


@router.get("/events")
def si_events(request: Request, since: int | None = Query(default=None, ge=0),
              limit: int | None = Query(default=None, ge=1)) -> JSONResponse:
    _reject_unknown_params(request, _LIST_PARAMS)
    return JSONResponse(_export(request, "events", since=since, limit=limit))


@router.get("/proposals")
def si_proposals(request: Request, since: int | None = Query(default=None, ge=0),
                 limit: int | None = Query(default=None, ge=1)) -> JSONResponse:
    _reject_unknown_params(request, _LIST_PARAMS)
    return JSONResponse(_export(request, "proposals", since=since, limit=limit))


@router.get("/proposals/{id}",
            responses={404: {"description": "格式合法但查無此提案（si_not_found）"}})
def si_proposal(request: Request, id: str) -> JSONResponse:
    ident = id                          # 參數名必須是路徑模板的 `id`；內文改用 ident 免遮蔽內建
    _reject_unknown_params(request, frozenset())
    if not _PROP_ID.fullmatch(ident):
        raise ApiError(422, "invalid_request", violations=[
            {"field": "id", "rule": "invalid_format", "message": "id 須為 PROP-SI-<三位以上數字>"}])
    obj = _export(request, "proposals", ident=ident)
    if not obj["items"]:
        raise ApiError(404, "si_not_found", id=ident)
    return JSONResponse(obj)


@router.get("/runs")
def si_runs(request: Request, since: int | None = Query(default=None, ge=0),
            limit: int | None = Query(default=None, ge=1)) -> JSONResponse:
    _reject_unknown_params(request, _LIST_PARAMS)
    return JSONResponse(_export(request, "runs", since=since, limit=limit))


# ── P2b：稽核檔落地（三個寫入 POST）與唯讀預檢 ──────────────────────────────────────────────────
def _violation(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def _invalid(violations: list[dict[str, str]]) -> ApiError:
    return ApiError(422, "invalid_request", violations=violations)


async def _read_limited_body(request: Request) -> bytes:
    """讀請求本文，超過 `SI_WRITE_BODY_MAX_BYTES` 即 422 `too_large` 而**不讀完**：先看宣告的
    Content-Length，再逐塊累計（分塊上傳沒有 Content-Length）。"""
    too_large = _invalid([_violation(
        "$", "too_large", f"本文超過 {SI_WRITE_BODY_MAX_BYTES} 位元組")])
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > SI_WRITE_BODY_MAX_BYTES:
        raise too_large
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > SI_WRITE_BODY_MAX_BYTES:
            raise too_large
    return bytes(buf)


def _parse_object(raw: bytes) -> dict[str, Any]:
    """本文須為單一 UTF-8 JSON 物件（兩份相連、垃圾、BOM、陣列、純量都不收）。"""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise _invalid([_violation("$", "not_utf8", "本文不是 UTF-8")]) from None
    try:
        obj = json.loads(text)
    except ValueError:
        raise _invalid([_violation("$", "not_json", "本文不是單一 JSON 文件")]) from None
    if not isinstance(obj, dict):
        raise _invalid([_violation("$", "not_object", "本文須為 JSON 物件")])
    return obj


def _outer_violations(obj: dict[str, Any], kind: str, path_id: str | None,
                      id_pattern: re.Pattern[str] | None) -> list[dict[str, str]]:
    """W3 ④：外層形態（不解內層 `body`、不驗簽、不驗 `key_id`／`mac` 的形態）。`path_id` 為 None
    ＝obs-add（`subject` 須為 null）；否則 `subject` 須為字串且等於路徑 `{id}`，`{id}` 另須合
    `id_pattern`。一次全列。"""
    out: list[dict[str, str]] = []
    if path_id is not None and (id_pattern is None or not id_pattern.fullmatch(path_id)):
        out.append(_violation("id", "invalid_format", "路徑 id 格式不合"))
    out += [_violation(name, "required", f"缺少外層鍵 {name}")
            for name in _OUTER_KEYS if name not in obj]
    out += [_violation(name, "unknown_key", f"不收外層鍵 {name}")
            for name in sorted(set(obj) - set(_OUTER_KEYS))]
    rev = obj.get("schema_rev")
    if "schema_rev" in obj and not (type(rev) is int and rev == 1):      # bool／浮點／字串都不收
        out.append(_violation("schema_rev", "must_be_1", "schema_rev 須為整數 1"))
    if "kind" in obj and obj["kind"] != kind:
        out.append(_violation("kind", "kind_mismatch", f"kind 須為 {kind}"))
    if "audit_ref" in obj and not si_audit.is_audit_ref(obj["audit_ref"]):
        out.append(_violation("audit_ref", "invalid_format", "audit_ref 須為小寫正規 UUID"))
    if "subject" in obj:
        if path_id is None:
            if obj["subject"] is not None:
                out.append(_violation("subject", "must_be_null", "obs-add 的 subject 須為 null"))
        elif not isinstance(obj["subject"], str) or obj["subject"] != path_id:
            out.append(_violation("subject", "subject_mismatch", "subject 須為字串且等於路徑 id"))
    out += [_violation(name, "must_be_string", f"{name} 須為字串")
            for name in ("body", "key_id", "mac") if name in obj and not isinstance(obj[name], str)]
    return out


async def _store_signed_audit(request: Request, token: str | None, *, verb: str, kind: str,
                              path_id: str | None, id_pattern: re.Pattern[str] | None
                              ) -> JSONResponse:
    audit = getattr(request.app.state, "audit", None)
    cfg = request.app.state.settings
    security.require_si_write_token(cfg.si_write_token, cfg.si_audit_dir, token, audit=audit,
                                    verb=verb, subject=path_id)

    def record(result: str, **extra: Any) -> None:
        if audit is not None:
            audit.record("si_write", verb=verb, subject=path_id, result=result,
                         trace_id=trace_id_var.get(), **extra)

    ref: str | None = None
    try:
        raw = await _read_limited_body(request)
        obj = _parse_object(raw)
        violations = _outer_violations(obj, kind, path_id, id_pattern)
        if violations:
            raise _invalid(violations)
        ref = obj["audit_ref"]
        await run_in_threadpool(si_audit.store_audit, cfg.si_audit_dir, ref, raw)
    except ApiError as exc:
        record(f"rejected:{exc.body['reason']}", **({"audit_ref": ref} if ref else {}))
        raise
    record("ok", audit_ref=ref)
    return JSONResponse({"audit_ref": ref, "stored": True}, status_code=201)


@router.post("/proposals/{id}:decide", status_code=201)
async def si_decide(request: Request, id: str,
                    x_bridge_token: str | None = Header(default=None)) -> JSONResponse:
    """決定的稽核檔落地（`dec`）；`{id}` 為 PROP 號，resume 為 RUN 號。"""
    ident = id                          # 參數名必須是路徑模板的 `id`；內文改用 ident 免遮蔽內建
    return await _store_signed_audit(request, x_bridge_token, verb="decide", kind="decide",
                                     path_id=ident, id_pattern=_DECIDE_ID)


@router.post("/observations", status_code=201)
async def si_observation_add(request: Request,
                             x_bridge_token: str | None = Header(default=None)) -> JSONResponse:
    """新增觀察列的稽核檔落地（`obs.add`）；外層 `subject` 須為 null。"""
    return await _store_signed_audit(request, x_bridge_token, verb="obs-add", kind="obs-add",
                                     path_id=None, id_pattern=None)


@router.post("/observations/{id}:close", status_code=201)
async def si_observation_close(request: Request, id: str,
                               x_bridge_token: str | None = Header(default=None)) -> JSONResponse:
    """關閉觀察列（處置終值）的稽核檔落地（`obs.close`）。"""
    ident = id
    return await _store_signed_audit(request, x_bridge_token, verb="obs-close", kind="obs-close",
                                     path_id=ident, id_pattern=_OBS_ID)


@router.post("/observations:validate")
async def si_observation_validate(request: Request) -> JSONResponse:
    """唯讀預檢（`obs-add --dry-run`）：不需權杖、不看寫入設定、不落檔。
    本文違規＝422，且不啟動子行程。"""
    raw = await _read_limited_body(request)
    _parse_object(raw)
    result = await run_in_threadpool(si_cli.run_validate, request.app.state.settings.si_root, raw)
    return JSONResponse(result)
