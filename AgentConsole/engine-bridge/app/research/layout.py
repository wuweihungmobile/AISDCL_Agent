"""研究工作區的目錄佈局、路徑消毒與原子寫檔（ADR-003 D8；W-R6、W-R12）。

工作區＝`<BRIDGE_RESEARCH_ROOT>/<slug>/`，其下四個目錄 `00_research`（議題、證據、抓取原檔）、
`01_specs`（PRD 與 ADR 草稿）、`02_governance`（審查卡、決定、`state.json` 匯出）、`03_execution`；
外環 FSM 的狀態目錄也在工作區內（`build/reports/fsm`）。

本模組的每個「寫」都走 `app.fsutil.write_text_atomic`（既有的 `os.replace` 站點）——**不新增**
`os.replace`／`rename`／`move` 站點（根層 dirent 鎖；W-R10）。路徑一律先過消毒：slug 文法、
解析後仍在允許根之下（擋 `..`、符號連結與 junction 逃逸）、檔案路徑相對工作區且不得含
`..` 或絕對路徑。
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from .. import fsutil
from ..errors import ApiError, unprocessable
from ..security import is_within

#: 工作區根之下的四個目錄（順序固定）。
WORKSPACE_DIRS: tuple[str, ...] = ("00_research", "01_specs", "02_governance", "03_execution")
ISSUE_SCOPE_REL = "00_research/issue_scope.json"
STATE_JSON_REL = "02_governance/state.json"
#: 外環 FSM 的狀態目錄（相對工作區；`SDD_STATE_DIR` 取它的絕對路徑）。
FSM_DIR_REL = "build/reports/fsm"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,29}$")


class WrittenFile(NamedTuple):
    rel: str
    sha256: str
    bytes: int
    written: bool          # False＝檔案已存在且呼叫端要求不覆寫（內容與 mtime 原封不動）


def _violation(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def sanitization_failed(violations: list[dict[str, str]]) -> ApiError:
    """422 `sanitization_failed`（路徑或 slug 不合規；磁碟與 DB 零新增）。"""
    return unprocessable(violations)


def slug_violations(slug: object) -> list[dict[str, str]]:
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        return [_violation("slug", "invalid_slug",
                           "slug 須符合 ^[a-z0-9][a-z0-9-]{0,29}$（1～30 字、小寫英數與連字號）")]
    return []


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def resolve_workspace(root: Path, slug: str, allowed_roots: Iterable[Path]) -> Path:
    """`<root>/<slug>` 解析後的絕對路徑；slug 不合規、或解析後（含符號連結／junction）跑出 `root` 或
    允許根之外＝422 `sanitization_failed`。不檢查存在性、不建任何東西。"""
    violations = slug_violations(slug)
    if violations:
        raise sanitization_failed(violations)
    resolved = (root / slug).resolve()
    if not is_within(resolved, root) or not any(is_within(resolved, r) for r in allowed_roots):
        raise sanitization_failed([_violation(
            "slug", "outside_allowed_roots", f"工作區解析後不在允許的根目錄之下：{resolved}")])
    return resolved


def fsm_state_dir(workspace: Path) -> Path:
    return workspace / "build" / "reports" / "fsm"


def ensure_dirs(workspace: Path, names: Iterable[str] = WORKSPACE_DIRS) -> None:
    """建工作區根與 `names` 各目錄（冪等；已存在的目錄不動）。名稱被同名檔案占用等情形＝`OSError`
    （呼叫端標 `init_failed:workspace`）。"""
    workspace.mkdir(parents=True, exist_ok=True)
    for name in names:
        (workspace / name).mkdir(exist_ok=True)


def safe_join(workspace: Path, rel: str) -> Path:
    """相對工作區的 POSIX 路徑 → 絕對路徑；絕對路徑、空字串、NUL、`..` 片段，或解析後（含符號連結）
    跑出工作區＝422 `sanitization_failed`。"""
    text = rel.replace("\\", "/") if isinstance(rel, str) else ""
    if (not text.strip() or "\x00" in text or text.startswith("/") or re.match(r"^[A-Za-z]:", text)
            or ".." in text.split("/")):
        raise sanitization_failed([_violation(
            "path", "invalid_path", f"不合規的工作區相對路徑：{rel!r}")])
    target = workspace.joinpath(*[p for p in text.split("/") if p and p != "."])
    if not is_within(target, workspace):
        raise sanitization_failed([_violation(
            "path", "outside_workspace", f"路徑解析後不在工作區之內：{rel}")])
    return target


def write_workspace_file(workspace: Path, rel: str, text: str, *,
                         overwrite: bool = True) -> WrittenFile:
    """把 `text`（UTF-8、LF）原子寫到 `workspace/rel`，回傳位元組的 sha256。`overwrite=False`
    且檔案已存在時**不寫**（位元組與 mtime 不變），回傳既有檔案的摘要與
    `written=False`（初始化冪等）。"""
    target = safe_join(workspace, rel)
    if not overwrite and target.is_file():
        data = target.read_bytes()
        return WrittenFile(rel, sha256_bytes(data), len(data), False)
    fsutil.write_text_atomic(target, text)
    data = text.encode("utf-8")
    return WrittenFile(rel, sha256_bytes(data), len(data), True)


def file_digest(workspace: Path, rel: str) -> tuple[str, int] | None:
    """工作區檔案的 `(sha256, 位元組數)`；不存在或不是檔案回 None。"""
    target = safe_join(workspace, rel)
    if not target.is_file():
        return None
    data = target.read_bytes()
    return sha256_bytes(data), len(data)
