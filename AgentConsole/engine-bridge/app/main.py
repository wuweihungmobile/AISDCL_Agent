# ruff: noqa: E402  — 日誌格式必須在匯入 autoclaude 之前裝好（見下方 setup_logging(None) 的註解）
"""Engine Bridge：FastAPI 旁車（PRD §0.2）。啟動：`uvicorn app.main:app --port 8081`。

單一 worker：run 登記表、事件環與行程監督都在記憶體內，多 worker 會各自一份而互相看不到。
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from .logsetup import setup_logging

# 先裝 stderr 的日誌格式、再匯入下面會連帶匯入 autoclaude 的模組：AutoClaude 匯入時就會用
# logger 印警告（例如「keyboard 未安裝」）；那時若還沒有 handler，Python 會用 lastResort 印出
# 沒有格式、沒有 trace_id 的裸訊息，「每一行日誌都帶 trace_id」（契約 §3.1.1）就破功。
# BRIDGE_LOG_DIR 的檔案 handler 在檔案最下方補上。
setup_logging(None)

from .decompose import BrainFactory, DecomposeService, DraftStore, default_brain_factory
from .errors import ApiError
from .health import deep_health
from .locks import AdvisoryLock
from .routers import autoclaude, sdd
from .runner import RunManager
from .security import AuditLog
from .settings import Settings, load_settings
from .tracing import TraceIdMiddleware

logger = logging.getLogger("bridge.main")


class BridgeApp(FastAPI):
    """與 FastAPI 相同，但 traceId 中介層包在**最外層**（契約 §3.1.1）：連 ServerErrorMiddleware
    回的 500 也帶 `X-Trace-Id`。`add_middleware` 加的中介層在 ServerErrorMiddleware 之內，
    管不到它送出的回應。"""

    def build_middleware_stack(self) -> ASGIApp:
        return TraceIdMiddleware(super().build_middleware_stack())


def create_app(settings: Settings | None = None, *,
               brain_factory: BrainFactory = default_brain_factory) -> FastAPI:
    cfg = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 啟動時（再）裝一次日誌設定（冪等）：測試與嵌入式用法沒有走模組層級那一次；
        # 也確保 uvicorn 自己的 dictConfig 先跑完之後，最後生效的是我們這套。
        setup_logging(cfg.log_dir)
        cfg.engine_workspace.mkdir(parents=True, exist_ok=True)
        audit = AuditLog(cfg.engine_workspace / "_audit.jsonl")
        db = None
        if cfg.db_dsn:
            from .db import BridgeDb  # 延遲匯入：純檔案模式不需要 psycopg 可用

            db = BridgeDb(cfg.db_dsn, cfg.db_schema)
            db.open()
            if not await asyncio.to_thread(db.schema_ready):
                logger.warning("DB 模式已啟用，但 %s schema 的三張表不齊（後端 Flyway 跑過了嗎？）"
                               "——Bridge 的 DB 寫入會逐筆跳過", cfg.db_schema)
        locks = AdvisoryLock(cfg.db_dsn, holder_lookup=db.find_lock_holder if db else None)
        runs = RunManager(cfg, locks=locks, audit=audit, db=db)
        orphaned = await asyncio.to_thread(runs.reconcile)
        if orphaned:
            logger.warning("啟動時回收孤兒 run：%s", orphaned)
        app.state.audit = audit
        app.state.db = db
        app.state.runs = runs
        app.state.decompose = DecomposeService(
            cfg, audit, DraftStore(cfg.engine_workspace / "_drafts"), brain_factory)
        try:
            yield
        finally:
            await asyncio.to_thread(runs.shutdown)
            if db is not None:
                db.close()

    app = BridgeApp(title="AgentConsole Engine Bridge", version="0.1.0", lifespan=lifespan)
    app.state.settings = cfg

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.body)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        violations = [{"field": ".".join(str(p) for p in err["loc"][1:]) or str(err["loc"][0]),
                       "rule": err["type"], "message": err["msg"]} for err in exc.errors()]
        return JSONResponse(status_code=422, content={
            "code": 422, "reason": "invalid_request", "violations": violations})

    app.include_router(autoclaude.router)
    app.include_router(sdd.router)

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        return build_health(request)

    @app.get("/health/deep", responses={503: {"description": "至少一項檢查失敗（degraded）"}})
    def health_deep(request: Request) -> JSONResponse:
        """深度探針（契約 §3.1.1）：git／autoclaude／workspace／DB 逐項實測；免認證。"""
        status, body = deep_health(cfg, getattr(request.app.state, "db", None))
        return JSONResponse(status_code=status, content=body)

    return app


def build_health(request: Request) -> dict[str, Any]:
    cfg: Settings = request.app.state.settings
    try:
        import autoclaude

        engine_ac: dict[str, Any] = {"ok": True, "version": autoclaude.__version__,
                                     "root": str(cfg.autoclaude_root)}
    except ImportError as exc:
        engine_ac = {"ok": False, "version": None, "reason": f"無法匯入 autoclaude：{exc}"}
    sdd_ok = cfg.sdd_root is not None and cfg.sdd_root.is_dir()
    engine_sdd: dict[str, Any] = {
        "ok": sdd_ok, "latest": cfg.sdd_root.name if sdd_ok and cfg.sdd_root else None,
        "root": str(cfg.sdd_root) if sdd_ok else None}
    db = getattr(request.app.state, "db", None)
    return {
        "status": "ok",
        "bridge_instance": cfg.bridge_instance,
        "engines": {"autoclaude": engine_ac, "sdd": engine_sdd},
        "db": {"enabled": db is not None, "schema": cfg.db_schema if db else None,
               "ok": db.ping() if db is not None else None},
        "workspace": str(cfg.engine_workspace),
    }


app = create_app()
# 當成伺服器入口（`uvicorn app.main:app`）時，日誌格式必須在 uvicorn 印出第一行之前就設好：
# uvicorn 先匯入本模組、才印 `Started server process`，所以放在這裡，連啟動與關閉的行
# 也有 `trace_id=-`（契約 §3.1.1）。
setup_logging(app.state.settings.log_dir)

if __name__ == "__main__":      # `python -m app.main`：讀 BRIDGE_HOST／BRIDGE_PORT
    settings_ = app.state.settings
    # log_config=None：不讓 uvicorn 的 dictConfig 把上面設好的格式蓋掉
    uvicorn.run(app, host=settings_.host, port=settings_.port, log_config=None)
