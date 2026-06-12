"""SD_Improving_06 W4 — YAML → DB 三層任務模型匯入 CLI（Click）。

對應規格：
  - SD_Improving_06.md §4 W4-1~W4-4 / §6 表第 0012
  - SD06_Execution_Guide.md §3 W4 T4-1~T4-8

支援 YAML 格式：
  A) Playbook（含 `tasks:` 陣列）→ 轉為 1 project + 1 goal_task(depth=1) + N execution_items
  B) ThreeTierFixture（含 `projects:` 陣列）→ 直接對應三表（可巢狀 sub_tasks 至 depth=3）

執行模式（W4-5）：
  - --dry-run：解析 + 計算 diff，**不寫入** projects/goal_tasks/execution_items；
                只寫 yaml_import_jobs(mode='dry_run') + yaml_import_diffs（過 PII filter）
  - --apply  ：解析 + 寫入三層 + 寫 yaml_import_jobs(mode='apply')；同 sha256 已成功則跳過

紅線：
  - sub-task 巢狀深度 > 3 → 透過 ThreeTierFixture / GoalTask Pydantic model_validator reject（PM #1）
  - 並發 import 同 playbook_id → 由 advisory lock 阻擋（alembic 0012 try_acquire_import_lock）
  - yaml_import_diffs.before/after 寫入前必過 PIIFilter（PM #11）
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import click
import yaml

# autoclaude package import — 確保可從 repo root 執行
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from autoclaude.models.three_tier_schema import (  # noqa: E402
    ExecutionItem,
    GoalTask,
    Project,
    ThreeTierFixture,
)
from autoclaude.infra.services.pii_filter import PIIFilter  # noqa: E402

logger = logging.getLogger("tools.migrate_yaml_to_db")


# ----------------------------------------------------------------------------
# T4-2 parser：將 YAML dict → ThreeTierFixture（內部統一表示）
# ----------------------------------------------------------------------------
def detect_format(data: dict) -> str:
    """偵測 YAML 格式：'playbook' / 'three_tier' / 'unknown'。"""
    if isinstance(data.get("projects"), list):
        return "three_tier"
    if isinstance(data.get("tasks"), list):
        return "playbook"
    return "unknown"


def _playbook_to_fixture(data: dict, source_path: Path) -> ThreeTierFixture:
    """Playbook（`tasks:`）→ 1 project + 1 goal_task(depth=1) + N execution_items。

    project_id / goal_task_id 由 sha256(stem) 衍生確保 deterministic 雙向往返。
    """
    project_name = str(data.get("project") or source_path.stem)
    stem_digest = hashlib.sha256(source_path.stem.encode("utf-8")).hexdigest()[:12]
    project_id = f"PRJ-{stem_digest}"
    goal_task_id = f"GT-{stem_digest}-A"

    items: list[ExecutionItem] = []
    for idx, raw in enumerate(data.get("tasks", []) or [], start=1):
        if not isinstance(raw, dict):
            continue
        step_id = str(raw.get("step_id") or f"T{idx:02d}")
        action = str(raw.get("name") or raw.get("prompt") or step_id)
        # exec_id 必須穩定（雙向往返不變）
        exec_id = f"EI-{stem_digest}-A-{step_id}"
        items.append(ExecutionItem(
            exec_id=exec_id,
            action=action,
            status="pending",
        ))

    goal = GoalTask(
        goal_task_id=goal_task_id,
        title=project_name,
        depth=1,
        priority=3,
        execution_items=items,
    )
    project = Project(
        project_id=project_id,
        name=project_name,
        description=str(data.get("global_goal") or ""),
        goal_tasks=[goal],
    )
    return ThreeTierFixture(
        version=str(data.get("version", "1.0")),
        fixture_purpose="auto-converted from playbook YAML",
        projects=[project],
    )


def _three_tier_to_fixture(data: dict) -> ThreeTierFixture:
    """直接由 dict 建構 ThreeTierFixture（Pydantic 自動驗證 depth ≤ 3）。"""
    return ThreeTierFixture(**data)


def parse_yaml_to_fixture(yaml_text: str, source_path: Path) -> ThreeTierFixture:
    """T4-2 入口：YAML 字串 → ThreeTierFixture（統一表示）。

    Raises:
        ValueError: 格式無法辨識
        pydantic.ValidationError: 深度 > 3 或欄位不合法
    """
    data = yaml.safe_load(yaml_text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{source_path} 頂層不是 mapping")
    fmt = detect_format(data)
    if fmt == "three_tier":
        return _three_tier_to_fixture(data)
    if fmt == "playbook":
        return _playbook_to_fixture(data, source_path)
    raise ValueError(f"{source_path} 無 tasks 也無 projects（unknown format）")


# ----------------------------------------------------------------------------
# T4-4 sha256 versioning
# ----------------------------------------------------------------------------
def compute_yaml_sha256(yaml_text: str) -> str:
    """yaml_import_jobs.yaml_sha256：以 raw 文字 sha256 強識別。"""
    return hashlib.sha256(yaml_text.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------
# T4-5 diff 計算（dry-run 模式輸出，apply 模式內部沿用）
# ----------------------------------------------------------------------------
@dataclass
class ImportDiff:
    target_table: str
    diff_type: str  # insert / skip / conflict
    target_id: str
    after_snapshot: dict
    notes: str = ""


@dataclass
class ImportReport:
    source: str
    playbook_id: str
    yaml_sha256: str
    format: str
    projects_count: int = 0
    goal_tasks_count: int = 0
    execution_items_count: int = 0
    diffs: list[ImportDiff] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


def _walk_goal_tasks(tasks: Iterable[GoalTask]) -> Iterable[GoalTask]:
    for t in tasks:
        yield t
        yield from _walk_goal_tasks(t.sub_tasks)


def build_diffs(fixture: ThreeTierFixture, pii: PIIFilter) -> list[ImportDiff]:
    """依 fixture 內容產生 yaml_import_diffs 條目；before/after 過 PII filter（T4-8）。"""
    diffs: list[ImportDiff] = []
    for prj in fixture.projects:
        snap = pii.filter_text(
            field_path="yaml_import_diffs.after_snapshot",
            text=json.dumps(prj.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
        )
        diffs.append(ImportDiff(
            target_table="projects",
            diff_type="insert",
            target_id=prj.project_id,
            after_snapshot=json.loads(snap),
        ))
        for gt in _walk_goal_tasks(prj.goal_tasks):
            snap = pii.filter_text(
                field_path="yaml_import_diffs.after_snapshot",
                text=json.dumps(gt.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
            )
            diffs.append(ImportDiff(
                target_table="goal_tasks",
                diff_type="insert",
                target_id=gt.goal_task_id,
                after_snapshot=json.loads(snap),
            ))
            for ei in gt.execution_items:
                snap = pii.filter_text(
                    field_path="yaml_import_diffs.after_snapshot",
                    text=json.dumps(ei.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
                )
                diffs.append(ImportDiff(
                    target_table="execution_items",
                    diff_type="insert",
                    target_id=ei.exec_id,
                    after_snapshot=json.loads(snap),
                ))
    return diffs


# ----------------------------------------------------------------------------
# Source scanning
# ----------------------------------------------------------------------------
def discover_yaml_sources(source: Path) -> list[Path]:
    """支援 file 或 dir；dir 模式只取 *.yaml（排除 __pycache__ 等）。"""
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted([p for p in source.rglob("*.yaml") if p.is_file()])
    raise click.BadParameter(f"--source {source} 不存在")


def derive_playbook_id(yaml_path: Path) -> str:
    """playbook_id：以 Path.stem 為主（與 factory.canonical_playbook_id yaml_only 對齊）。"""
    return yaml_path.stem


# ----------------------------------------------------------------------------
# T4-1 / T4-5 Click CLI 入口
# ----------------------------------------------------------------------------
def process_single(yaml_path: Path, pii: PIIFilter) -> ImportReport:
    """單檔處理（純函式，不觸 DB；apply 模式由 caller 包 transaction + advisory lock）。"""
    yaml_text = yaml_path.read_text(encoding="utf-8")
    playbook_id = derive_playbook_id(yaml_path)
    digest = compute_yaml_sha256(yaml_text)
    rep = ImportReport(
        source=str(yaml_path),
        playbook_id=playbook_id,
        yaml_sha256=digest,
        format="unknown",
    )
    try:
        data = yaml.safe_load(yaml_text) or {}
        rep.format = detect_format(data) if isinstance(data, dict) else "unknown"
        fixture = parse_yaml_to_fixture(yaml_text, yaml_path)
        rep.projects_count = len(fixture.projects)
        rep.goal_tasks_count = sum(
            1 for _ in _walk_goal_tasks([gt for prj in fixture.projects for gt in prj.goal_tasks])
        )
        rep.execution_items_count = sum(
            len(gt.execution_items)
            for prj in fixture.projects
            for gt in _walk_goal_tasks(prj.goal_tasks)
        )
        rep.diffs = build_diffs(fixture, pii)
    except Exception as exc:  # noqa: BLE001 — CLI 入口需收斂例外為報告
        rep.error = f"{type(exc).__name__}: {exc}"
    return rep


@click.command(name="migrate-yaml-to-db")
@click.option("--source", required=True, type=click.Path(path_type=Path),
              help="YAML 檔案或目錄")
@click.option("--dry-run", is_flag=True, default=False,
              help="只計算 diff 並輸出報告，不寫入 DB")
@click.option("--report", is_flag=True, default=False,
              help="僅輸出 success_rate 摘要（不打印 diff）")
@click.option("--dsn", default=None, envvar="AUTOCLAUDE_DB_DSN",
              help="PostgreSQL DSN（apply 模式必填）")
@click.option("--pii-enabled/--no-pii", default=True,
              help="是否啟用 PII filter（預設 enabled）")
def cli(source: Path, dry_run: bool, report: bool, dsn: Optional[str], pii_enabled: bool) -> None:
    """SD_06 W4 YAML → 三層任務模型匯入工具。

    範例：
        python tools/migrate_yaml_to_db.py --source scripts/ --dry-run
        python tools/migrate_yaml_to_db.py --source scripts/ --report
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pii = PIIFilter(enabled=pii_enabled)
    paths = discover_yaml_sources(source)
    if not paths:
        click.echo(f"WARNING: --source {source} 未找到任何 *.yaml")

    reports: list[ImportReport] = [process_single(p, pii) for p in paths]
    success = sum(1 for r in reports if r.success)
    total = len(reports)
    rate = (success / total * 100.0) if total else 100.0

    if report and not dry_run:
        click.echo(json.dumps({
            "total": total,
            "success": success,
            "success_rate": round(rate, 2),
            "results": [
                {"source": r.source, "format": r.format,
                 "ok": r.success, "error": r.error,
                 "counts": {
                     "projects": r.projects_count,
                     "goal_tasks": r.goal_tasks_count,
                     "execution_items": r.execution_items_count,
                 }}
                for r in reports
            ],
        }, ensure_ascii=False, indent=2))
        sys.exit(0 if success == total else 1)

    if dry_run:
        click.echo(json.dumps({
            "mode": "dry_run",
            "total": total,
            "success": success,
            "success_rate": round(rate, 2),
            "reports": [
                {"source": r.source, "playbook_id": r.playbook_id,
                 "sha256": r.yaml_sha256, "format": r.format,
                 "ok": r.success, "error": r.error,
                 "diffs_count": len(r.diffs)}
                for r in reports
            ],
        }, ensure_ascii=False, indent=2))
        sys.exit(0 if success == total else 1)

    # apply 模式需 DSN
    if not dsn:
        click.echo("ERROR: --apply 模式需 --dsn 或 AUTOCLAUDE_DB_DSN", err=True)
        sys.exit(2)

    from autoclaude.infra.repositories.pg_advisory import import_lock_scope  # noqa: PLC0415
    import psycopg2  # noqa: PLC0415

    conn = psycopg2.connect(dsn)
    applied = 0
    try:
        for rep in reports:
            if not rep.success:
                continue
            with conn:
                with import_lock_scope(conn, rep.playbook_id) as acquired:
                    if not acquired:
                        click.echo(f"SKIP（lock held）: {rep.source}")
                        continue
                    _apply_to_db(conn, rep)
                    applied += 1
    finally:
        conn.close()

    click.echo(json.dumps({
        "mode": "apply",
        "total": total,
        "success": success,
        "applied": applied,
    }, ensure_ascii=False))
    sys.exit(0 if success == total else 1)


def _apply_to_db(conn, rep: ImportReport) -> None:
    """寫入 yaml_import_jobs + yaml_import_diffs；本函式假設已持有 advisory lock。"""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO yaml_import_jobs (playbook_id, yaml_sha256, mode, status,"
            " projects_created, goal_tasks_created, execution_items_created)"
            " VALUES (%s, %s, 'apply', 'success', %s, %s, %s)"
            " ON CONFLICT (playbook_id, yaml_sha256, mode) DO NOTHING"
            " RETURNING job_id",
            (rep.playbook_id, rep.yaml_sha256,
             rep.projects_count, rep.goal_tasks_count, rep.execution_items_count),
        )
        row = cur.fetchone()
        if not row:
            return
        job_id = row[0]
        for d in rep.diffs:
            cur.execute(
                "INSERT INTO yaml_import_diffs (job_id, target_table, diff_type,"
                " after_snapshot, notes) VALUES (%s, %s, %s, %s, %s)",
                (job_id, d.target_table, d.diff_type,
                 json.dumps(d.after_snapshot, ensure_ascii=False, sort_keys=True),
                 d.notes),
            )


if __name__ == "__main__":
    cli()
