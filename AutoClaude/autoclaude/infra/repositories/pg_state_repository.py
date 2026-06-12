"""PgStateRepository — IQueryableStateRepository 的 PostgreSQL 後端（Phase 6 選配）。

⚠️ 需安裝：pip install autoclaude[postgres]

使用範例：
    import os
    from sqlalchemy.ext.asyncio import create_async_engine
    # 設定環境變數：AUTOCLAUDE_DB_DSN="postgresql+asyncpg://${PG_USER}:${PG_PASS}@host/db?sslmode=require"
    engine = create_async_engine(os.environ["AUTOCLAUDE_DB_DSN"])
    repo = PgStateRepository(engine)

P1 #7（Security）：_save() 呼叫前以 _scrub_sensitive() 擦除
  last_correction_prompt 中的 Bearer token / API key。

P1 #8（asyncio 相容）：所有同步方法改用 _run_async() 取代 asyncio.run()，
  支援 FastAPI / aiohttp 等已有 running event loop 的執行環境。

M4（SD_03 §1.2）：save_checkpoint 首次呼叫時自動 INSERT playbook_runs；
  checkpoints.run_id 為 NOT NULL FK，由 _ensure_run_id() 維護。

P1 #4（tenacity retry）：_save / _load / _clear 加 OperationalError retry（max 3, backoff）。
"""
from __future__ import annotations

import logging
import re
from collections import OrderedDict  # Dev-3：移至模組頂部，避免每次 fallback 重複 import
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ...core.ports.state_repository import StateRepositoryError
from ...utils.checkpoint_manager import PlaybookCheckpoint

logger = logging.getLogger("autoclaude.infra.repositories.pg")

# 延遲 import：未安裝 sqlalchemy 時 raise 友善訊息
_SQLALCHEMY_AVAILABLE = False
try:
    from sqlalchemy import select, delete, func
    from sqlalchemy.exc import OperationalError, ProgrammingError, InterfaceError
    from sqlalchemy.ext.asyncio import AsyncEngine
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from ._pg_models import CheckpointRow, PlaybookRun, PlaybookVersion
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    OperationalError = ProgrammingError = InterfaceError = Exception  # type: ignore

# Arch-M2（W1P0 三方審查）：tenacity import 已移至 pg_async_utils._make_retry，
# 本檔不再直接使用，故移除原死碼 try/except block。


_DSN_PASSWORD_RE = re.compile(r"(://[^:/@]+:)([^@]+)(@)")


def _redact(msg: str) -> str:
    """從訊息中移除 DSN 密碼欄位（Security review 要求）。"""
    return _DSN_PASSWORD_RE.sub(r"\1***\3", msg)


# P1 #7：last_correction_prompt 敏感資訊擦除（Security review 要求）
_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"),   # Bearer tokens
    re.compile(r"sk-[A-Za-z0-9\-_]{20,}"),                   # Anthropic / OpenAI API keys
    re.compile(r"(?i)authorization:\s*\S+"),                  # Authorization headers
]


def _scrub_sensitive(text: str) -> str:
    """移除 last_correction_prompt 中的 Bearer token / API key 等敏感資訊。"""
    if not text:
        return text
    for pat in _SENSITIVE_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


# P1 #8：asyncio running-event-loop 相容包裝（共用實作移至 pg_async_utils，C-4 修復）
from .pg_async_utils import _run_async, _make_retry


# T6（SD_04 §3）：_run_cache TTL 防記憶體洩漏
# 主路徑使用 cachetools.TTLCache（maxsize=256, ttl=3600s）
# Fallback：cachetools 未安裝時用 _BoundedLRUCache（純標準庫實作）
_TTLCACHE_AVAILABLE = False
try:
    from cachetools import TTLCache as _TTLCache
    _TTLCACHE_AVAILABLE = True
except ImportError:
    pass


class _BoundedLRUCache(dict):
    """LRU + maxsize 限制的標準庫 fallback（無 TTL，但有 maxsize 防無限增長）。

    僅用於 cachetools 未安裝時的相容方案；行為與 dict 相容（__setitem__ /
    __getitem__ / pop / __contains__ / __len__），超過 maxsize 時驅逐最舊項目。
    """
    def __init__(self, maxsize: int = 256):
        super().__init__()
        self._maxsize = maxsize
        self._order: OrderedDict = OrderedDict()

    def __setitem__(self, key, value):
        if key in self._order:
            self._order.move_to_end(key)
        else:
            self._order[key] = None
            if len(self._order) > self._maxsize:
                oldest, _ = self._order.popitem(last=False)
                super().pop(oldest, None)
        super().__setitem__(key, value)

    def __getitem__(self, key):
        # Dev-5：__getitem__ 命中保證 key 在 super dict 內，
        # 由 __setitem__ 不變式保證亦同步存在於 _order；無需條件守衛
        v = super().__getitem__(key)
        self._order.move_to_end(key)
        return v

    def pop(self, key, *args):
        self._order.pop(key, None)
        return super().pop(key, *args)


def _make_run_cache():
    """工廠函式：依 cachetools 可用性回傳 TTLCache 或 BoundedLRUCache。"""
    if _TTLCACHE_AVAILABLE:
        return _TTLCache(maxsize=256, ttl=3600)
    return _BoundedLRUCache(maxsize=256)


class PgStateRepository:
    """PostgreSQL backend for IQueryableStateRepository。

    所有方法皆同步介面（與既有 IStateRepository 簽章一致）；
    內部以 pg_async_utils._run_async() 包裝 SQLAlchemy 2.0 async 呼叫，
    支援 FastAPI / aiohttp 等已有 running event loop 的環境
    （C-4 / X-5 / Arch-M3 修復）。

    M4：_run_cache 維護 playbook_id → run_id 對應，
    確保 save_checkpoint 首次呼叫時自動建立 playbook_runs 記錄。
    """

    def __init__(self, engine: "Any"):
        if not _SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "PgStateRepository 需 sqlalchemy + asyncpg；"
                "請執行：pip install autoclaude[postgres]"
            )
        self._engine = engine
        # M4：playbook_id → run_id（str UUID）對應快取
        #   - playbook_id 在 yaml_only / both 模式為 Path.stem
        #   - playbook_id 在 db_only 模式為 sha256(abs_path)[:16]
        #   （由 canonical_playbook_id() 產出，T8 / SD_04 §3 M-2）
        # T6（SD_04 §3 / M-10）：改用 TTLCache（maxsize=256, ttl=3600s）防記憶體洩漏
        # cachetools 未安裝時 fallback 至 _BoundedLRUCache（限 256 項，無 TTL）
        self._run_cache = _make_run_cache()
        # W4 三方審查 Dev-W4-Maj-2：sampling 計數器，避免熱點驗證
        self._save_count: int = 0

    # ──────────────────────────────────────────────
    def save_checkpoint(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        try:
            _run_async(self._save(playbook_id, checkpoint))
        except Exception as exc:
            raise StateRepositoryError(
                f"PgStateRepository.save_checkpoint 失敗 (playbook_id={playbook_id}): "
                f"{_redact(str(exc))}"
            ) from exc

    def load_checkpoint(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        """⚠️ Deprecated（SD_06 W5-T5-8）：請改用 load_latest_by_playbook。"""
        import os, warnings  # noqa: E401
        if os.environ.get("AUTOCLAUDE_DEPRECATION_WARN") == "1":
            warnings.warn(
                "load_checkpoint(playbook_id) is deprecated since SD_06 W5; "
                "use load_latest_by_playbook(playbook_id) instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return self.load_latest_by_playbook(playbook_id)

    def load_latest_by_playbook(
        self, playbook_id: str,
    ) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：載入 playbook_id 最新一筆 checkpoint（order_by saved_at desc）。

        OperationalError / InterfaceError 降級回 None；ProgrammingError（schema 錯誤）
        上拋以避免 silent data loss（DBA/SRE review）。
        """
        try:
            return _run_async(self._load(playbook_id))
        except (OperationalError, InterfaceError) as exc:
            logger.warning(
                "PgStateRepository.load_latest_by_playbook | 暫時性失敗 fallback 至 None "
                "(playbook_id=%s): %s", playbook_id, _redact(str(exc)),
            )
            return None
        except ProgrammingError as exc:
            raise StateRepositoryError(
                f"PgStateRepository.load_latest_by_playbook schema 錯誤 (playbook_id={playbook_id}): "
                f"{_redact(str(exc))}"
            ) from exc

    def load_by_run_id(self, run_id: str) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：以 run_id 索引查詢對應 checkpoint。

        對應 checkpoints.run_id (UUID FK)；找不到回 None。
        """
        if not run_id:
            return None
        try:
            return _run_async(self._load_by_run_id(run_id))
        except (OperationalError, InterfaceError) as exc:
            logger.warning(
                "PgStateRepository.load_by_run_id | 暫時性失敗 fallback 至 None "
                "(run_id=%s): %s", run_id, _redact(str(exc)),
            )
            return None
        except ProgrammingError as exc:
            raise StateRepositoryError(
                f"PgStateRepository.load_by_run_id schema 錯誤 (run_id={run_id}): "
                f"{_redact(str(exc))}"
            ) from exc

    def clear_checkpoint(self, playbook_id: str) -> None:
        try:
            _run_async(self._clear(playbook_id))
        except (OperationalError, InterfaceError) as exc:
            logger.warning(
                "PgStateRepository.clear_checkpoint | 暫時性失敗忽略 (playbook_id=%s): %s",
                playbook_id, _redact(str(exc)),
            )

    def schedule_resume(self, playbook_id: str, delay_minutes: int) -> datetime:
        resume_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        cp = self.load_checkpoint(playbook_id) or PlaybookCheckpoint(
            playbook_path=playbook_id, step_idx=0, step_id="", total_steps=0,
        )
        cp.scheduled_resume_at = resume_at.isoformat(timespec="seconds")
        self.save_checkpoint(playbook_id, cp)
        return resume_at

    def list_recent_checkpoints(
        self, since: Optional[datetime] = None, limit: int = 50,
    ) -> list[PlaybookCheckpoint]:
        try:
            return _run_async(self._list(since, limit))
        except (OperationalError, InterfaceError) as exc:
            logger.warning(
                "PgStateRepository.list_recent_checkpoints | 暫時性失敗 fallback 至 []: %s",
                _redact(str(exc)),
            )
            return []

    def close(self) -> None:
        """釋放底層 AsyncEngine（Infra review 要求 lifecycle hook）。"""
        try:
            _run_async(self._engine.dispose())
        except Exception as exc:
            logger.warning("PgStateRepository.close | dispose 失敗: %s", _redact(str(exc)))

    # ──────────────────────────────────────────────
    # 內部 async 實作（P1 #4：retry on OperationalError）
    # AsyncSession 用於 ORM entity 查詢（AsyncConnection 不自動反序列化 ORM entity）
    # ──────────────────────────────────────────────
    @_make_retry()
    async def _save(self, playbook_id: str, cp: PlaybookCheckpoint) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(self._engine) as session:
            async with session.begin():
                # M4：確保 playbook_runs 記錄存在，取得 run_id
                run_id = await self._ensure_run_id(session, playbook_id, cp.project)
                # W4-T15 m-4：PlaybookVersion 連續性驗證（warning-only，不影響 save）
                await self._validate_version_continuity(session, playbook_id)
                counters = {
                    "goto": cp.goto_counter,
                    "inject_before": cp.inject_before_counter,
                    "skip_to": cp.skip_to_counter,
                    "step_evolution": cp.step_evolution_counter,
                }
                stmt = pg_insert(CheckpointRow).values(
                    run_id=run_id,
                    playbook_id=playbook_id,
                    step_idx=cp.step_idx,
                    step_id=cp.step_id,
                    total_steps=cp.total_steps,
                    scheduled_resume_at=cp.scheduled_resume_at,
                    peak_token_pct=cp.peak_token_pct,
                    counters=counters,
                    completed_step_log=list(cp.completed_step_log),
                    completed_step_ids=list(cp.completed_step_ids),
                    failure_history=list(cp.failure_history),
                    active_step_attempt=cp.active_step_attempt,
                    last_correction_prompt=_scrub_sensitive(cp.last_correction_prompt or ""),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["run_id"],  # C-6 修復：改用 run_id 唯一索引
                    set_={
                        "step_idx": stmt.excluded.step_idx,
                        "step_id": stmt.excluded.step_id,
                        "total_steps": stmt.excluded.total_steps,
                        "counters": stmt.excluded.counters,
                        "completed_step_log": stmt.excluded.completed_step_log,
                        "completed_step_ids": stmt.excluded.completed_step_ids,
                        "failure_history": stmt.excluded.failure_history,
                        "active_step_attempt": stmt.excluded.active_step_attempt,
                        "last_correction_prompt": stmt.excluded.last_correction_prompt,
                        "scheduled_resume_at": stmt.excluded.scheduled_resume_at,
                        "peak_token_pct": stmt.excluded.peak_token_pct,
                        "saved_at": func.now(),
                    },
                )
                await session.execute(stmt)

    @_make_retry()
    async def _load(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import desc
        async with AsyncSession(self._engine) as session:
            result = await session.execute(
                # C-D 修復：加 order_by(desc) 確保多個 run_id 時取最新 checkpoint
                select(CheckpointRow)
                .where(CheckpointRow.playbook_id == playbook_id)
                .order_by(desc(CheckpointRow.saved_at))
                .limit(1)
            )
            r = result.scalars().first()
        if r is None:
            return None
        return self._row_to_checkpoint(r)

    @_make_retry()
    async def _load_by_run_id(self, run_id: str) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：以 run_id 索引查詢對應 checkpoint。"""
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(self._engine) as session:
            result = await session.execute(
                select(CheckpointRow).where(CheckpointRow.run_id == run_id).limit(1)
            )
            r = result.scalars().first()
        if r is None:
            return None
        return self._row_to_checkpoint(r)

    @_make_retry()
    async def _clear(self, playbook_id: str) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(self._engine) as session:
            async with session.begin():
                await session.execute(
                    delete(CheckpointRow).where(CheckpointRow.playbook_id == playbook_id)
                )
        self._run_cache.pop(playbook_id, None)

    @_make_retry()  # M-A 修復：補加 retry decorator，與 _save/_load/_clear 一致
    async def _list(self, since, limit) -> list:
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(self._engine) as session:
            stmt = select(CheckpointRow).order_by(CheckpointRow.saved_at.desc()).limit(limit)
            if since:
                stmt = stmt.where(CheckpointRow.saved_at >= since)
            result = await session.execute(stmt)
            return [self._row_to_checkpoint(r) for r in result.scalars().all()]

    # ──────────────────────────────────────────────
    # M4：playbook_runs 記錄確保
    # ──────────────────────────────────────────────
    async def _ensure_run_id(self, session, playbook_id: str, project: str) -> str:
        """確保 playbook_runs 中存在對應記錄，回傳 run_id（str UUID）。

        查找順序：
        1. 內存快取 (_run_cache)
        2. 查詢 checkpoints.run_id（process 重啟後恢復）
        3. INSERT playbook_runs（首次呼叫）
        """
        # 1. 快取命中
        if playbook_id in self._run_cache:
            return self._run_cache[playbook_id]
        # 2. DB 查找（process 重啟後 checkpoint 已存在）
        # C-D 修復：多 run_id 時取最新一筆（order_by saved_at desc，limit 1）
        from sqlalchemy import desc
        existing = await session.execute(
            select(CheckpointRow.run_id)
            .where(CheckpointRow.playbook_id == playbook_id)
            .order_by(desc(CheckpointRow.saved_at))
            .limit(1)
        )
        existing_run_id = existing.scalar()
        if existing_run_id is not None:
            run_id_str = str(existing_run_id)
            self._run_cache[playbook_id] = run_id_str
            return run_id_str
        # 3. 首次呼叫：INSERT playbook_runs
        result = await session.execute(
            pg_insert(PlaybookRun).values(
                playbook_id=playbook_id,
                project=project or playbook_id,
                status="running",
            ).returning(PlaybookRun.run_id)
        )
        run_id_str = str(result.scalar())
        self._run_cache[playbook_id] = run_id_str
        return run_id_str

    # ──────────────────────────────────────────────
    # W4-T15 m-4：PlaybookVersion 連續性驗證（gap detection）
    # ──────────────────────────────────────────────
    async def _validate_version_continuity(self, session, playbook_id: str) -> None:
        """檢查 playbook_versions.generation 是否有 gap，若有則 warn（不 raise）。

        對應 W4-T15 m-4：在 save_checkpoint 內部呼叫，警告而非阻擋。
        當 playbook_versions 表不存在或無法查詢時靜默忽略（best-effort）。

        **W4 三方審查 Dev-W4-Maj-2 sampling 策略**：
        - 每 10 次 save 才實際驗證一次（self._save_count % 10 == 0），避免熱點查詢。
        - 第一次 save（_save_count == 1）跳過；第 10、20、30… 次執行驗證。

        **W4 三方審查 Dev-W4-Maj-1 exception 嚴重度區分**：
        - `ProgrammingError`：schema 問題（欄位不存在、表被誤改），記 warning（不靜默）。
        - `OperationalError` / `InterfaceError`：暫時性連線失敗，記 debug（靜默）。
        """
        # sampling：每 10 次 save 才驗證一次（避免熱點）
        self._save_count = getattr(self, "_save_count", 0) + 1
        if self._save_count % 10 != 0:
            return
        try:
            result = await session.execute(
                select(PlaybookVersion.generation)
                .where(PlaybookVersion.original_playbook_id == playbook_id)
                .order_by(PlaybookVersion.generation)
            )
            generations = sorted({int(g) for g in result.scalars().all()})
            if len(generations) < 2:
                return
            expected = list(range(generations[0], generations[-1] + 1))
            missing = sorted(set(expected) - set(generations))
            if missing:
                logger.warning(
                    "PgStateRepository | PlaybookVersion 連續性異常 "
                    "(playbook_id=%s) | 已存在 generation=%s | 缺失=%s",
                    playbook_id, generations, missing,
                )
        except ProgrammingError as exc:
            # schema 問題不該靜默：可能 playbook_versions 欄位被誤改
            logger.warning(
                "PgStateRepository | PlaybookVersion 連續性驗證失敗 (schema, playbook_id=%s): %s",
                playbook_id, _redact(str(exc)),
            )
        except (OperationalError, InterfaceError) as exc:
            # 暫時性連線 / 介面失敗：best-effort，靜默忽略
            logger.debug(
                "PgStateRepository | PlaybookVersion 連續性驗證跳過 (transient, playbook_id=%s): %s",
                playbook_id, _redact(str(exc)),
            )

    @staticmethod
    def _row_to_checkpoint(r) -> PlaybookCheckpoint:
        """M2 修正：補全所有 CheckpointRow 欄位。

        SD_06 W5-T5-7：補 run_id 欄位回填至 PlaybookCheckpoint.run_id。
        """
        c = r.counters or {}
        return PlaybookCheckpoint(
            playbook_path=r.playbook_id,
            step_idx=r.step_idx,
            step_id=r.step_id,
            total_steps=r.total_steps,
            saved_at=r.saved_at.isoformat(timespec="seconds") if r.saved_at else "",
            scheduled_resume_at=(
                r.scheduled_resume_at.isoformat(timespec="seconds")
                if r.scheduled_resume_at else None
            ),
            peak_token_pct=r.peak_token_pct,
            goto_counter=dict(c.get("goto", {})),
            inject_before_counter=dict(c.get("inject_before", {})),
            skip_to_counter=dict(c.get("skip_to", {})),
            step_evolution_counter=dict(c.get("step_evolution", {})),
            completed_step_ids=list(r.completed_step_ids or []),
            completed_step_log=list(r.completed_step_log or []),
            failure_history=list(r.failure_history or []),
            active_step_attempt=r.active_step_attempt,
            last_correction_prompt=r.last_correction_prompt,
            run_id=str(r.run_id) if r.run_id is not None else None,
        )
