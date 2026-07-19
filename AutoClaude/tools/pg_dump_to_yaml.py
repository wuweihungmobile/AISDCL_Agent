"""SD_09 ADR-SD09-001 §5 rollback — PG → YAML 唯一備援匯出工具。

職責：
    1. 連線 PostgreSQL（DSN 由 ``--pg-dsn`` 提供）
    2. 對指定表 ``SELECT *`` 並序列化為 YAML（datetime / UUID / dict 處理）
    3. 輸出至 ``--output-dir``（每表一檔，``<table>.yaml``）
    4. 連線失敗或缺 sqlalchemy 時 graceful degrade：
       印警告 + 寫 ``dump_metadata.json`` 標 unable + exit 0（不阻塞 rollback drill）

支援的表（與 PgStateRepository / DualStateRepository / _pg_models.py 對齊）：
    - playbook_runs
    - checkpoints
    - knowledge_entries
    - playbook_versions
    - drift_log
    - config_audit_log
    - kb_metrics（可選；若 schema 不存在則 skip）

YAML schema：對齊 FileStateRepository 既有格式
    - PlaybookCheckpoint dataclass 欄位（snake_case；list/dict 平坦序列化）
    - datetime → ISO-8601 字串
    - UUID → str
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# 預設 dump 的表清單（與 _pg_models.py 對齊）
DEFAULT_TABLES: tuple[str, ...] = (
    "playbook_runs",
    "checkpoints",
    "knowledge_entries",
    "playbook_versions",
    "drift_log",
    "config_audit_log",
    "kb_metrics",
)


def _to_serializable(value: Any) -> Any:
    """將 SQLAlchemy row 值轉為 YAML / JSON 可序列化型別。"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_to_serializable(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _to_serializable(v) for k, v in value.items()}
    # UUID / Decimal / 其它 → str
    return str(value)


def _try_dump_table(conn, table_name: str) -> tuple[bool, list[dict[str, Any]], str]:
    """嘗試 SELECT * FROM <table>；回傳 (success, rows, message)。"""
    from sqlalchemy import text  # type: ignore[import]
    try:
        result = conn.execute(text(f"SELECT * FROM {table_name}"))
        rows: list[dict[str, Any]] = []
        for row in result.mappings():
            rows.append({k: _to_serializable(v) for k, v in dict(row).items()})
        return True, rows, ""
    except Exception as exc:  # noqa: BLE001  graceful per-table degrade
        return False, [], f"{type(exc).__name__}: {exc}"


def _write_yaml(path: Path, rows: list[dict[str, Any]]) -> None:
    """寫 YAML；若 PyYAML 不存在則回退寫 JSON（並改副檔名）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore[import]
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(rows, f, allow_unicode=True, sort_keys=False)
    except ImportError:
        # 回退到 JSON（命名加 .json，並提示）
        json_path = path.with_suffix(".json")
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2, default=str)


def _write_metadata(output_dir: Path, metadata: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "dump_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)


def _connect(pg_dsn: str):
    """嘗試建立 SQLAlchemy connection；失敗或缺依賴時 raise。"""
    from sqlalchemy import create_engine  # type: ignore[import]
    engine = create_engine(pg_dsn, future=True)
    return engine.connect()


def main(argv: list[str] | None = None) -> int:
    # DEF-82-001/DEF-101-070 家族慣例：訊息含中文/→ 等非 ASCII，Windows cp950 console
    # 直接 print 會 UnicodeEncodeError 中斷；stdout + stderr 皆強制 utf-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(
        description="SD_09 ADR-SD09-001 §5 — PG → YAML rollback dump"
    )
    parser.add_argument(
        "--pg-dsn", type=str, required=True,
        help="PostgreSQL DSN（傳空字串等同於無 PG，會 graceful degrade）",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("./yaml_export"),
        help="輸出目錄（每表一個 YAML 檔；預設 ./yaml_export/）",
    )
    parser.add_argument(
        "--tables", type=str, default=",".join(DEFAULT_TABLES),
        help="逗號分隔的表清單（預設全部）",
    )
    args = parser.parse_args(argv)

    output_dir: Path = args.output_dir
    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    metadata: dict[str, Any] = {
        "tool": "pg_dump_to_yaml",
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "pg_dsn_provided": bool(args.pg_dsn),
        "requested_tables": tables,
        "status": "pending",
        "tables": {},
    }

    # 1) 缺 DSN → graceful degrade
    if not args.pg_dsn:
        metadata["status"] = "unable"
        metadata["reason"] = "no pg-dsn provided"
        _write_metadata(output_dir, metadata)
        print(
            "[WARN] --pg-dsn 為空字串，無法連線 PG；已寫 dump_metadata.json 標 unable。"
            "graceful exit 0 不阻塞 rollback drill。",
            file=sys.stderr,
        )
        return 0

    # 2) 缺 sqlalchemy → graceful degrade
    try:
        import sqlalchemy  # noqa: F401  type: ignore[import]
    except ImportError:
        metadata["status"] = "unable"
        metadata["reason"] = "sqlalchemy not installed"
        _write_metadata(output_dir, metadata)
        print(
            "[WARN] 未安裝 sqlalchemy；請執行 pip install autoclaude[postgres]。"
            "已寫 dump_metadata.json 標 unable。graceful exit 0。",
            file=sys.stderr,
        )
        return 0

    # 3) 嘗試連線；失敗則 graceful degrade
    try:
        conn = _connect(args.pg_dsn)
    except Exception as exc:  # noqa: BLE001
        metadata["status"] = "unable"
        metadata["reason"] = f"connect failed: {type(exc).__name__}: {exc}"
        _write_metadata(output_dir, metadata)
        print(
            f"[WARN] PG 連線失敗：{exc}；已寫 dump_metadata.json 標 unable。"
            "graceful exit 0。",
            file=sys.stderr,
        )
        return 0

    # 4) per-table dump
    success_tables: list[str] = []
    skipped_tables: list[str] = []
    try:
        for table in tables:
            ok, rows, msg = _try_dump_table(conn, table)
            if ok:
                yaml_path = output_dir / f"{table}.yaml"
                _write_yaml(yaml_path, rows)
                metadata["tables"][table] = {
                    "status": "ok",
                    "row_count": len(rows),
                    "output": str(yaml_path),
                }
                success_tables.append(table)
            else:
                metadata["tables"][table] = {"status": "skip", "reason": msg}
                skipped_tables.append(table)
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    metadata["status"] = "ok" if success_tables else "partial"
    metadata["finished_at"] = datetime.now().isoformat(timespec="seconds")
    metadata["success_tables"] = success_tables
    metadata["skipped_tables"] = skipped_tables
    _write_metadata(output_dir, metadata)

    print(
        f"[OK] dumped {len(success_tables)} tables (skipped {len(skipped_tables)}); "
        f"output_dir={output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
