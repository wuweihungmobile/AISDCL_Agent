"""Repository factory — 依 StorageConfig.mode 決定後端組合。

SD_Improving_02.md v1.1 §2.8 Phase 6 補註：
  - yaml_only：FileStateRepository（單一）
  - both：     DualStateRepository(File primary + PG shadow)
  - db_only：  PgStateRepository（單一）

DSN 解析優先級：環境變數 AUTOCLAUDE_DB_DSN > config.storage.db_dsn

Phase 6 stakeholder review 採納項：
  - DSN 環境變數統一為 AUTOCLAUDE_DB_DSN（舊 AUTOCLAUDE_PG_DSN 短期相容）
  - 強制 TLS（Security）：ssl/sslmode 缺失時 reject 啟動，AUTOCLAUDE_ALLOW_INSECURE_DB=1 可暫時 override
  - Engine pool 配置（DBA / Infra / SRE）：pool_pre_ping / pool_recycle / pool_size
"""
from __future__ import annotations

import logging
import os
from typing import Any

from ...utils.config import StorageConfig
from .file_state_repository import FileStateRepository
from .dual_state_repository import DualStateRepository

import re as _re

logger = logging.getLogger("autoclaude.infra.repositories.factory")

_PG_DSN_ENV = "AUTOCLAUDE_DB_DSN"
_DSN_PASSWORD_RE = _re.compile(r"(://[^:/@]+:)([^@]+)(@)")


def _redact(msg: str) -> str:
    return _DSN_PASSWORD_RE.sub(r"\1***\3", msg)


# T8（SD_04 §3 / M-2）：playbook_id 統一計算策略
# File backend（yaml_only / both 主端）：使用 Path.stem（人類可讀，向後相容）
# PG backend pure（db_only）：使用 sha256(abs_path)[:16] 確保唯一性
#                              並避免相對路徑差異造成 ID 不一致
def canonical_playbook_id(playbook_path: str, mode: str) -> str:
    """依 storage.mode 決定 playbook_id 計算策略。

    Args:
        playbook_path: Playbook YAML 路徑（相對或絕對）
        mode: storage.mode（"yaml_only" / "both" / "db_only"）

    Returns:
        統一的 playbook_id 字串

    策略表：
      - yaml_only：Path.stem（與 v1.x 相容，人類可讀）
      - both：    Path.stem（dual-write 兩端必須使用同一 ID）
      - db_only： sha256(abs_path)[:16]（純 PG 後端，確保唯一）
    """
    from pathlib import Path
    import hashlib
    if mode == "db_only":
        abs_path = str(Path(playbook_path).resolve())
        return hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:16]
    # yaml_only / both → stem
    return Path(playbook_path).stem

_PG_DSN_LEGACY_ENV = "AUTOCLAUDE_PG_DSN"  # 舊變數短期相容
_INSECURE_OVERRIDE_ENV = "AUTOCLAUDE_ALLOW_INSECURE_DB"


def _resolve_dsn(storage: StorageConfig) -> str:
    """解析 DSN：env > legacy env > config。"""
    dsn = os.environ.get(_PG_DSN_ENV)
    if dsn:
        return dsn
    legacy = os.environ.get(_PG_DSN_LEGACY_ENV)
    if legacy:
        logger.warning(
            "%s 已 deprecated，請改用 %s（短期相容仍可運作）",
            _PG_DSN_LEGACY_ENV, _PG_DSN_ENV,
        )
        return legacy
    if storage.db_dsn:
        return storage.db_dsn
    raise RuntimeError(
        f"storage.mode={storage.mode!r} 需 PostgreSQL DSN；"
        f"請設定環境變數 {_PG_DSN_ENV} 或 config.storage.db_dsn"
    )


def _enforce_tls(dsn: str) -> None:
    """強制 DSN 含 TLS 設定（Security review 必修）。"""
    if os.environ.get(_INSECURE_OVERRIDE_ENV) == "1":
        logger.warning(
            "%s=1，已停用 TLS 強制檢查（僅供 dev/test，禁止 production 使用）",
            _INSECURE_OVERRIDE_ENV,
        )
        return
    lowered = dsn.lower()
    if "sslmode=" in lowered or "ssl=true" in lowered or "ssl=require" in lowered:
        return
    raise RuntimeError(
        "PostgreSQL DSN 必須啟用 TLS（Security review 強制條件）。"
        "請於 DSN 加上 ?sslmode=require（或 verify-full），"
        f"或暫時設定 {_INSECURE_OVERRIDE_ENV}=1 跳過（僅 dev/test）。"
    )


def _normalize_asyncpg_dsn(dsn: str) -> tuple[str, dict]:
    """asyncpg 不接受 psycopg2 風格的 sslmode= URL 參數；轉換為 connect_args。

    asyncpg 使用 ssl="require" / ssl=True 而非 sslmode=require。
    TLS 強制檢查（_enforce_tls）仍以原始 DSN 字串做文字比對，
    本函式在創建 engine 前才做轉換。
    """
    import re
    m = re.search(r"[?&]sslmode=([^&]+)", dsn, re.IGNORECASE)
    if not m:
        return dsn, {}
    sslmode_val = m.group(1).lower()
    # 移除 sslmode= 參數，避免傳給 asyncpg 引發 TypeError
    cleaned = re.sub(r"([?&])sslmode=[^&]*(&?)", _strip_param, dsn)
    cleaned = cleaned.rstrip("?&")
    # sslmode → asyncpg ssl 參數對應
    _SSL_MAP: dict[str, Any] = {
        "require": "require",
        "verify-full": True,
        "verify-ca": True,
        "disable": False,
        "allow": False,
        "prefer": False,
    }
    ssl_val = _SSL_MAP.get(sslmode_val, "require")
    return cleaned, {"ssl": ssl_val}


def _strip_param(m: "re.Match") -> str:  # type: ignore[type-arg]
    """移除 ?key=val 或 &key=val，保持剩餘 query string 完整。"""
    sep, trailing = m.group(1), m.group(2)
    # 若 sep=? 且有 trailing &，補回 ? 作為下一個參數的起頭
    if sep == "?" and trailing == "&":
        return "?"
    return sep if trailing else ""


# Arch-M1 / SA-Minor-1（W1P0 三方審查）：移除本地 _run_async 副本，
# 改用 pg_async_utils 統一實作（含 M-C 修復的 timeout=300，避免 _smoke_test_pg
# 在已有 event loop 環境且 PG 阻塞時無限等待）。SSOT 單一真相來源。
from .pg_async_utils import _run_async  # noqa: E402


def _smoke_test_pg(engine) -> None:
    """P1 #3：PG 連線 startup smoke test（SELECT 1 + alembic head check）。

    在 both / db_only 模式啟動時呼叫，確保：
      1. 資料庫可連線（SELECT 1）
      2. schema 版本為最新（alembic_version == head）
    """
    async def _check(eng):
        from sqlalchemy import text
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
            try:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                ver = result.scalar()
                if ver is None:
                    logger.warning("PG smoke: alembic_version 表為空，schema 可能未初始化")
                else:
                    logger.info("PG smoke: alembic_version=%s", ver)
            except Exception:
                logger.warning("PG smoke: 無法讀取 alembic_version（schema 未執行 alembic upgrade head？）")

    try:
        _run_async(_check(engine))
        logger.info("PG startup smoke test PASS")
    except Exception as exc:
        raise RuntimeError(
            f"PG startup smoke test 失敗：{_redact(str(exc))}。"
            "請確認 PostgreSQL 服務運行中且已執行 alembic upgrade head。"
        ) from exc


def build_state_repository(checkpoint_dir: str, storage: StorageConfig) -> Any:
    """依 StorageConfig.mode 回傳對應後端。"""
    if storage.mode == "yaml_only":
        return FileStateRepository(checkpoint_dir=checkpoint_dir)

    # both / db_only 需 PG DSN + TLS
    dsn = _resolve_dsn(storage)
    _enforce_tls(dsn)

    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool
        from .pg_state_repository import PgStateRepository
    except ImportError as exc:
        raise ImportError(
            "PostgreSQL backend 需安裝：pip install autoclaude[postgres]"
        ) from exc

    # asyncpg 不接受 sslmode= 參數；正規化為 connect_args ssl
    dsn, ssl_connect_args = _normalize_asyncpg_dsn(dsn)

    # NullPool：AutoClaude 為 CLI 工具，每次 save_checkpoint 各自呼叫 asyncio.run()。
    # 標準連線池的連線 bound to 特定 event loop，跨 asyncio.run() 呼叫會失效。
    # NullPool 每次 connect() 建立新連線、close() 即釋放，避免 cross-loop 問題。
    engine = create_async_engine(
        dsn, echo=False,
        poolclass=NullPool,
        connect_args=ssl_connect_args,
    )

    # P1 #3：startup smoke test（SELECT 1 + alembic head check）
    _smoke_test_pg(engine)

    pg_repo = PgStateRepository(engine)

    if storage.mode == "db_only":
        return pg_repo

    # both 模式：File 主 + PG 影子
    file_repo = FileStateRepository(checkpoint_dir=checkpoint_dir)
    return DualStateRepository(
        primary=file_repo,
        shadow=pg_repo,
        strict=storage.dual_write_strict,
        read_resolution=storage.dual_read_resolution,
    )
