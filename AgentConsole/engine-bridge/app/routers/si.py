"""/si/*：SelfImproving 的唯讀鏡像（TCS-SelfImprovingMirror-P1b R5；ADR-SI-12）。

六個 GET，每個請求恰啟動一次 `si_cli.run_export` 子行程（無快取、不寫任何檔）；200 時本文是
子行程輸出**解析後的 export 物件逐值透傳**（鍵序保留、非 ASCII 不跳脫，Bridge 不增刪改任何鍵）。
沒有任何非 GET 方法（FastAPI 對已知路徑的其他方法回 405）；SI 不可用只影響 `/si/*`，
不影響 `/health` 與 `/health/deep`。

輸入驗證在**子行程之前**：清單類只收 `since`（整數 ≥0）與 `limit`（整數 ≥1），其餘任何查詢參數
（含 `/si/status` 與 `/si/proposals/{id}` 上的這兩個）一律 422 `invalid_request`
（`rule=unknown_parameter`）；`{id}` 須符 `PROP-SI-<三位以上數字>`，不符 422；符合而 export 回空＝
404 `si_not_found`。`limit` 的上限住在協定參數檔，不在此複製：超過上限時 CLI 回 rc 3，
依 `si_cli` 的判定表回 503（`cause=nonzero_rc`）。
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from .. import si_cli
from ..errors import ApiError

router = APIRouter(prefix="/si", tags=["si"])

#: ASCII 數字、整串比對：比 CLI 自己的格式略嚴（不收全形數字與結尾換行）。
_PROP_ID = re.compile(r"PROP-SI-[0-9]{3,}")
_LIST_PARAMS = frozenset({"since", "limit"})


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
