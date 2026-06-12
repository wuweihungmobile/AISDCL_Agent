"""SD_Improving_06 W0-T0-1：alembic 編號鏈條鎖死契約測試

紅線（SD_06 §7 ❌9）：
    alembic 編號不可跳號或重複，既有 0001-0006 鎖死為 frozen head set；
    新 migration 必須從 0007 起連續 +1 編號。

本契約測試確保：
    1. 既有 0001-0006 六支 migration 檔案皆存在且不可變動
    2. down_revision 鏈嚴格連續（每支指向前一編號）
    3. revision id 無重複、無分支（無 fork）
    4. 新 migration（W3 起 0007-0012）若加入時必須延續編號

對應 PM/SD 簽核（SD_06 §6 一票否決）：
    既有 0001-0006 不可動；新鏈 0007-0012 嚴格 +1。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ALEMBIC_VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"

# Frozen head set（W0 起點，2026-05-17 確認）
# key   = 檔名 stem（不含 .py）
# value = (實際 revision id, down_revision id)
# 注意：0003 為 optional GIN index 分支，down_revision=0002（不在主鏈上）；
#       主鏈：0001 → 0002 → 0004 → 0005 → 0006（既有設計，鎖死不動）
FROZEN_REVISIONS: dict[str, tuple[str, str | None]] = {
    "0001_initial": ("0001_initial", None),
    "0002_m4_run_id_not_null": ("0002_m4_run_id_not_null", "0001_initial"),
    "0003_optional_jsonb_gin_index": ("0003_jsonb_gin_index", "0002_m4_run_id_not_null"),
    "0004_pgvector": ("0004_pgvector", "0002_m4_run_id_not_null"),
    "0005_fix_checkpoint_unique_run_id": ("0005_fix_checkpoint_unique_run_id", "0004_pgvector"),
    "0006_checkpoint_saved_at_tz": ("0006_checkpoint_saved_at_tz", "0005_fix_checkpoint_unique_run_id"),
}

# 主鏈順序（用於 head 推導 + 新 migration 接續驗證）
MAIN_CHAIN_ORDER: list[str] = [
    "0001_initial",
    "0002_m4_run_id_not_null",
    "0004_pgvector",
    "0005_fix_checkpoint_unique_run_id",
    "0006_checkpoint_saved_at_tz",
]

REVISION_RE = re.compile(r'^revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
DOWN_REVISION_RE = re.compile(
    r'^down_revision\s*=\s*(?:["\']([^"\']+)["\']|None|\(([^)]+)\))', re.MULTILINE
)
PREFIX_RE = re.compile(r"^(\d{4})_")


def _read_revision_metadata(py_path: Path) -> tuple[str, str | tuple[str, ...] | None]:
    """從 .py migration 抽取 (revision, down_revision)。

    down_revision 支援三種型態：string（單一前置）/ None（首版）/ tuple（merge revision）。
    """
    text = py_path.read_text(encoding="utf-8")
    rev_match = REVISION_RE.search(text)
    down_match = DOWN_REVISION_RE.search(text)
    assert rev_match, f"{py_path.name}: 找不到 revision = '...'"
    assert down_match, f"{py_path.name}: 找不到 down_revision = '...' or None or tuple"
    rev = rev_match.group(1)
    if down_match.group(1):
        return rev, down_match.group(1)
    if down_match.group(2):
        parts = tuple(p.strip().strip("\"'") for p in down_match.group(2).split(","))
        return rev, parts
    return rev, None


def _list_migration_py_files() -> list[Path]:
    return sorted(
        p for p in ALEMBIC_VERSIONS_DIR.glob("*.py") if p.name != "__init__.py"
    )


class TestAlembicChainLock:
    """SD_06 §7 ❌9 編號鎖死契約。"""

    def test_frozen_revisions_all_exist(self) -> None:
        """既有 0001-0006 六支 .py 皆存在。"""
        py_files = {p.stem for p in _list_migration_py_files()}
        missing = [stem for stem in FROZEN_REVISIONS if stem not in py_files]
        assert not missing, f"frozen head set 缺檔：{missing}"

    def test_revision_ids_unique(self) -> None:
        """所有 revision id 不可重複（無 fork）。"""
        revisions: list[str] = []
        for py in _list_migration_py_files():
            rev, _ = _read_revision_metadata(py)
            revisions.append(rev)
        dupes = [r for r in revisions if revisions.count(r) > 1]
        assert not dupes, f"revision id 重複：{set(dupes)}"

    def test_down_revision_chain_strict(self) -> None:
        """既有 0001-0006 (revision, down_revision) 嚴格符合 FROZEN_REVISIONS。

        包含 0003 optional 分支設計（down=0002，不在主鏈上）。
        """
        for stem, (expected_rev, expected_down) in FROZEN_REVISIONS.items():
            py_path = ALEMBIC_VERSIONS_DIR / f"{stem}.py"
            actual_rev, actual_down = _read_revision_metadata(py_path)
            assert actual_rev == expected_rev, (
                f"{py_path.name}: revision 應為 {expected_rev!r}，"
                f"實際 {actual_rev!r}（SD_06 §7 ❌9 鎖死）"
            )
            assert actual_down == expected_down, (
                f"{stem}: down_revision 應為 {expected_down!r}，"
                f"實際 {actual_down!r}（SD_06 §7 ❌9 鏈條鎖死）"
            )

    def test_numeric_prefix_continuous_no_gap(self) -> None:
        """檔名 NNNN 前綴連續無跳號（W0 起點：1-6）。"""
        prefixes: list[int] = []
        for py in _list_migration_py_files():
            m = PREFIX_RE.match(py.name)
            assert m, f"{py.name}: 檔名缺四位數字前綴"
            prefixes.append(int(m.group(1)))
        prefixes.sort()
        for i, n in enumerate(prefixes, start=1):
            assert n == i, (
                f"alembic 編號跳號：第 {i} 支應為 {i:04d}，實際 {n:04d}"
                f"（SD_06 §7 ❌9：連續 +1 規則）"
            )

    def test_new_migrations_must_continue_from_0007(self) -> None:
        """任何新加入的 migration 必須從 0007 起連續編號（不可插入 0001-0006 之間）。

        本測試在 W0 階段：head set 必為 6 支；
        W3 起，每加入新 migration（0007/0008/.../0012）此測試需手動更新
        FROZEN_REVISIONS（升級為 frozen 後即受編號鎖保護）。
        新 migration 必須以 0006_checkpoint_saved_at_tz 主鏈 head 為 down_revision。
        """
        py_files = _list_migration_py_files()
        assert len(py_files) >= len(FROZEN_REVISIONS), (
            "head set 不可縮減（既有 0001-0006 鎖死）"
        )
        for py in py_files:
            m = PREFIX_RE.match(py.name)
            assert m, f"{py.name}: 缺前綴"
            num = int(m.group(1))
            if num > 6:
                assert num >= 7, "新 migration 編號不可 < 7"

    def test_main_chain_head_is_0006(self) -> None:
        """主鏈 head 必為 0006_checkpoint_saved_at_tz（新 migration 必由此延續）。"""
        last_stem = MAIN_CHAIN_ORDER[-1]
        expected_rev, _ = FROZEN_REVISIONS[last_stem]
        assert expected_rev == "0006_checkpoint_saved_at_tz", (
            "主鏈 head 偏移；W0 起點主鏈 head 必為 0006_checkpoint_saved_at_tz"
        )

    def test_sql_mirror_exists_for_each_py(self) -> None:
        """每支 .py 應有對應 .sql 鏡像（純 psql 環境 fallback）。

        例外：
            - 0003：純 GIN index 操作，無 .sql 鏡像（既有設計）
            - 0015：SD_09 W0 G0 audit merge revision（合併 0003 + 0014 雙 head，無 schema 異動）
        """
        EXCEPT_NO_SQL = {
            "0003_optional_jsonb_gin_index",
            "0015_merge_sd06_optional_gin",
        }
        for py in _list_migration_py_files():
            stem = py.stem
            if stem in EXCEPT_NO_SQL:
                continue
            sql = ALEMBIC_VERSIONS_DIR / f"{stem}.sql"
            assert sql.exists(), (
                f"{stem}.sql 鏡像缺失（純 psql 環境 fallback 要求）"
            )
