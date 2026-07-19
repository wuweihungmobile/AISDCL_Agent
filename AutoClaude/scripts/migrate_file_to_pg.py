#!/usr/bin/env python
"""一次性遷移工具：File backend → PostgreSQL backend（Phase 6 選配）。

對應 SD_Improving_02.md v1.1 §1.5 P-6 接入路線。
P1 #9：新增 --skip-existing flag + KB 遷移迴圈 + transaction batch。

使用：
  pip install autoclaude[postgres]
  export AUTOCLAUDE_DB_DSN="postgresql+asyncpg://${PG_USER}:${PG_PASS}@host:5432/autoclaude?sslmode=require"
  python scripts/migrate_file_to_pg.py --checkpoint-dir checkpoints/
  python scripts/migrate_file_to_pg.py --checkpoint-dir checkpoints/ --skip-existing
  python scripts/migrate_file_to_pg.py --checkpoint-dir checkpoints/ --batch-size 20

流程：
  1. 從 File backend 讀取所有 checkpoint / KB 記錄
  2. 依 --batch-size 批次透過 PG backend 寫入 PostgreSQL
  3. --skip-existing：跳過 PG 端已存在的 playbook_id（不覆寫）
  4. 報告成功 / 跳過 / 失敗計數
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("migrate_file_to_pg")


def _build_pg_repo(dsn: str):
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        from autoclaude.infra.repositories.pg_state_repository import PgStateRepository
    except ImportError:
        logger.error("缺少相依套件，請執行：pip install autoclaude[postgres]")
        sys.exit(1)
    engine = create_async_engine(
        dsn, echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=3,
        max_overflow=5,
    )
    return PgStateRepository(engine), engine


def _migrate_checkpoints(
    checkpoint_dir: Path,
    pg_state,
    skip_existing: bool,
    batch_size: int,
    dry_run: bool,
) -> tuple[int, int, int]:
    """回傳 (migrated, skipped, failed)。"""
    from autoclaude.infra.repositories.file_state_repository import FileStateRepository

    file_state = FileStateRepository(str(checkpoint_dir))
    cp_files = sorted(checkpoint_dir.glob("*.checkpoint.json"))
    logger.info("[scan] 發現 %d 個 checkpoint", len(cp_files))

    if dry_run:
        for p in cp_files:
            print(f"  (dry-run) {p.name}")
        return 0, 0, 0

    migrated = skipped = failed = 0
    for batch_start in range(0, len(cp_files), batch_size):
        batch = cp_files[batch_start: batch_start + batch_size]
        logger.info(
            "批次 %d/%d（%d 筆）",
            batch_start // batch_size + 1,
            (len(cp_files) + batch_size - 1) // batch_size,
            len(batch),
        )
        for p in batch:
            playbook_id = p.stem.replace(".checkpoint", "")
            try:
                cp = file_state.load_checkpoint(playbook_id)
                if cp is None:
                    logger.warning("SKIP（無法讀取）: %s", playbook_id)
                    skipped += 1
                    continue
                if skip_existing:
                    existing = pg_state.load_checkpoint(playbook_id)
                    if existing is not None:
                        logger.debug(
                            "SKIP（PG 已存在）: %s  step_idx=%s", playbook_id, existing.step_idx
                        )
                        skipped += 1
                        continue
                pg_state.save_checkpoint(playbook_id, cp)
                logger.info("OK: %s  step_idx=%s", playbook_id, cp.step_idx)
                migrated += 1
            except Exception as exc:
                logger.error("FAIL: %s — %s", playbook_id, exc)
                failed += 1

    return migrated, skipped, failed


def _migrate_kb(
    checkpoint_dir: Path,
    pg_state,
    skip_existing: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """遷移 FailureKnowledgeBase JSONL → PG memory store。
    回傳 (migrated, skipped, failed)。
    """
    kb_path = checkpoint_dir / "failure_knowledge_base.jsonl"
    if not kb_path.exists():
        logger.info("[KB] 無 failure_knowledge_base.jsonl，跳過 KB 遷移")
        return 0, 0, 0

    try:
        from autoclaude.infra.repositories.file_memory_store import FileMemoryStore
        from autoclaude.infra.repositories.pg_memory_store import PgMemoryStore
    except ImportError:
        logger.warning("[KB] FileMemoryStore / PgMemoryStore 匯入失敗，跳過 KB 遷移")
        return 0, 0, 0

    file_kb = FileMemoryStore(str(kb_path))
    records = list(file_kb.get_all()) if hasattr(file_kb, "get_all") else []
    if not records:
        logger.info("[KB] 無 KB 記錄可遷移")
        return 0, 0, 0

    logger.info("[KB] 發現 %d 筆 KB 記錄", len(records))

    if dry_run:
        for r in records:
            print(f"  (dry-run KB) {getattr(r, 'error_signature', r)[:60]}")
        return 0, 0, 0

    try:
        pg_kb = PgMemoryStore(getattr(pg_state, "_engine", None))
    except Exception as exc:
        logger.warning("[KB] PgMemoryStore 初始化失敗：%s", exc)
        return 0, 0, 0

    migrated = skipped = failed = 0
    for record in records:
        try:
            key = getattr(record, "error_signature", None) or str(record)
            if skip_existing and hasattr(pg_kb, "exists") and pg_kb.exists(key):
                skipped += 1
                continue
            pg_kb.save(record)
            migrated += 1
        except Exception as exc:
            logger.error("[KB] FAIL: %s — %s", getattr(record, "error_signature", "?"), exc)
            failed += 1

    return migrated, skipped, failed


def main() -> int:
    # R13 DEF-101-168 家族：Windows 主控台預設碼頁（如 cp950）印 ❌/中文會
    # UnicodeEncodeError，守護式 reconfigure 為 UTF-8（慣例同 tools/seed_kb.py）。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(
        description="File backend → PostgreSQL 一次性遷移工具（P1 #9）"
    )
    parser.add_argument(
        "--checkpoint-dir", default="checkpoints",
        help="File backend 的 checkpoints 目錄（預設：checkpoints/）",
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN", ""),
        help="PG DSN（預設讀 AUTOCLAUDE_DB_DSN 環境變數）",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="PG 端已存在相同 playbook_id 時跳過（不覆寫）",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="每批次遷移筆數（預設：50）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="僅列出將被遷移的記錄，不實際寫入 PG",
    )
    parser.add_argument(
        "--migrate-kb", action="store_true",
        help="同時遷移 failure_knowledge_base.jsonl → PG memory store",
    )
    args = parser.parse_args()

    if not args.dsn and not args.dry_run:
        parser.error("需提供 --dsn 或設定環境變數 AUTOCLAUDE_DB_DSN")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine  # noqa
    except ImportError:
        print("❌ sqlalchemy 未安裝。請先執行：pip install autoclaude[postgres]", file=sys.stderr)
        return 1

    checkpoint_dir = Path(args.checkpoint_dir)
    if not checkpoint_dir.exists():
        print(f"❌ checkpoint 目錄不存在: {checkpoint_dir}", file=sys.stderr)
        return 1

    pg_state, _engine = (_build_pg_repo(args.dsn) if not args.dry_run
                         else (None, None))

    # ── checkpoint 遷移 ──────────────────────────────
    cp_migrated, cp_skipped, cp_failed = _migrate_checkpoints(
        checkpoint_dir=checkpoint_dir,
        pg_state=pg_state,
        skip_existing=args.skip_existing,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    print(f"\n[checkpoint] migrated={cp_migrated}  skipped={cp_skipped}  failed={cp_failed}")

    # ── KB 遷移（需 --migrate-kb 明確啟用）────────────
    kb_migrated = kb_skipped = kb_failed = 0
    if args.migrate_kb:
        kb_migrated, kb_skipped, kb_failed = _migrate_kb(
            checkpoint_dir=checkpoint_dir,
            pg_state=pg_state,
            skip_existing=args.skip_existing,
            dry_run=args.dry_run,
        )
        print(f"[KB]         migrated={kb_migrated}  skipped={kb_skipped}  failed={kb_failed}")

    total_failed = cp_failed + kb_failed
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
