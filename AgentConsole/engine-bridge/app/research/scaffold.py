"""軌道 B 的範本展開與研究工作區複製（ADR-003 D8、D14；TCS AC-961-6；D-117、D-118）。

三件事，**全部確定性、無網路、無子行程、不用 LLM**：
  · `expand`：把 `scaffold_templates/<id>/` 的範本以 `{{var}}` 代換展開到新專案根。範本檔一律以
    `.tmpl` 後綴存放、展開時去後綴（⚖P1-18：範本內的 Python 檔若以 `.py` 存放，會被 `app/`
    全樹 AST 鎖與能力登記掃到）。變數值只准 `[A-Za-z0-9_-]`；每個輸出路徑 `resolve()` 後須在
    新根之下；整批先在記憶體算好並逐一驗證、通過才落地，落地中途失敗即把已寫的檔與目錄清掉
    （不留半套）。
  · `copy_workspace`：研究工作區的四個編號目錄逐檔 `shutil.copyfile`＋sha256 驗證（含
    `00_research/raw/**`，D-117）；原工作區原地保留。不新增 `os.replace`／`rename`／`move`。
  · `tracked_files`：預測初始 commit 會追蹤的檔案集合（範本檔＋副本去掉 `.gitignore` 排除者），
    預演的 `expected_tracked_files` 與執行時 `git ls-files` 對拍（AC-13-5）。

範本登記制（D-32）：清單取自目錄掃描（`settings.list_template_ids`），不是常數；範本 id 不符
`[A-Za-z0-9_-]` 或不在清單＝`ScaffoldError("unknown_template")`，不做任何正規化。
"""
from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .. import fsutil
from ..security import is_within
from . import settings as research_settings
from .layout import WORKSPACE_DIRS

#: 範本變數值的字元集（PRD AC-R2P-13-8）；輸出路徑另須 `resolve()` 後落在新根之下。
TEMPLATE_VAR_PATTERN = "[A-Za-z0-9_-]"
_VAR_VALUE_RE = re.compile(rf"^{TEMPLATE_VAR_PATTERN}+$")
_PLACEHOLDER_RE = re.compile(r"\{\{([a-z_]+)\}\}")
TEMPLATE_SUFFIX = ".tmpl"
#: 範本來源檔名 → 展開後檔名（只換檔名）。`.env.example` 的來源不能叫 `.env.example.tmpl`：根層
#: `.gitignore` 的 `.env.*` 會把它擋在版控之外。
RENAMED_SOURCES: dict[str, str] = {"env.example": ".env.example"}
#: 選用檔：相對路徑 → 控制它的旗標（`ci`、`docker_compose`；旗標為假就不產生該檔）。
OPTIONAL_FILES: dict[str, str] = {
    ".github/workflows/ci.yml": "ci",
    "docker-compose.yml": "docker_compose",
}
#: 範本 `.gitignore` 排除的樣式（與範本內容同源；`tracked_files` 的預測以它為準）。
#: 含斜線的樣式只相對新專案根（`build/reports/`）；`**/…` 形態在任何深度皆生效
#: （`00_research/raw/`）。
GITIGNORE_ROOT_DIRS: tuple[tuple[str, ...], ...] = (("build", "reports"),)
GITIGNORE_ANYWHERE_DIRS: tuple[tuple[str, ...], ...] = (("00_research", "raw"),)
GITIGNORE_DIR_NAMES = frozenset({"__pycache__", ".venv"})
GITIGNORE_FILE_NAMES = frozenset({".env"})
GITIGNORE_SUFFIXES = (".pyc",)
#: 副本在新專案根下的位置：`my-project/<slug>/`。
WORKSPACE_COPY_ROOT = "my-project"


class ScaffoldError(Exception):
    """範本或複製失敗；`rule` 是機器可讀碼（對外映射 422 `sanitization_failed`／步驟 FAILED）。"""

    def __init__(self, rule: str, message: str = "") -> None:
        super().__init__(f"{rule}: {message}" if message else rule)
        self.rule = rule
        self.message = message


@dataclass(frozen=True)
class PlannedFile:
    rel: str            # 相對新專案根的 POSIX 路徑（已去 .tmpl、已代換）
    data: bytes


@dataclass(frozen=True)
class CopiedFile:
    rel: str            # 相對副本根（`my-project/<slug>`）的 POSIX 路徑
    sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ── 範本登記 ────────────────────────────────────────────────────────────────────────────────
def list_templates() -> list[str]:
    """登記的範本 id（目錄掃描、字母序；測試可 monkeypatch `settings.TEMPLATES_DIR`）。"""
    return research_settings.list_template_ids()


def template_dir(template_id: str) -> Path:
    if not isinstance(template_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", template_id) or (
            template_id not in list_templates()):
        raise ScaffoldError("unknown_template", f"範本 {template_id!r} 不在登記清單")
    return research_settings.TEMPLATES_DIR / template_id


def _check_variables(variables: Mapping[str, str]) -> None:
    for name, value in variables.items():
        if not isinstance(value, str) or not _VAR_VALUE_RE.fullmatch(value):
            raise ScaffoldError("invalid_variable",
                                f"變數 {name} 的值只准 {TEMPLATE_VAR_PATTERN}")


def _render(text: str, variables: Mapping[str, str], where: str) -> str:
    def sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise ScaffoldError("unknown_variable", f"{where} 用到未提供的變數 {{{{{name}}}}}")
        return variables[name]

    out = _PLACEHOLDER_RE.sub(sub, text)
    if "{{" in out or "}}" in out:
        raise ScaffoldError("unrendered_marker", f"{where} 仍含 {{{{ 或 }}}} 標記")
    return out


def plan_files(template_id: str, variables: Mapping[str, str], *, ci: bool = True,
               docker_compose: bool = True) -> list[PlannedFile]:
    """範本展開的完整結果（記憶體內，字母序）；不寫任何東西。變數非法或有未代換標記即拋。"""
    _check_variables(variables)
    root = template_dir(template_id)
    flags = {"ci": ci, "docker_compose": docker_compose}
    out: list[PlannedFile] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if not rel.endswith(TEMPLATE_SUFFIX):
            raise ScaffoldError("untemplated_file", f"範本檔 {rel} 缺 {TEMPLATE_SUFFIX} 後綴")
        target = _render(rel[: -len(TEMPLATE_SUFFIX)], variables, f"路徑 {rel}")
        head, sep, name = target.rpartition("/")
        target = head + sep + RENAMED_SOURCES.get(name, name)
        if OPTIONAL_FILES.get(target) and not flags[OPTIONAL_FILES[target]]:
            continue
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        out.append(PlannedFile(target, _render(text, variables, rel).encode("utf-8")))
    return out


def expand(template_id: str, variables: Mapping[str, str], dest: Path, *, ci: bool = True,
           docker_compose: bool = True) -> list[str]:
    """展開範本到 `dest`（不存在或為空的目錄）；回寫出的相對路徑（POSIX、字母序）。

    先把全部輸出算好並驗證（路徑 `resolve()` 後須在 `dest` 之下、不得逃逸），才開始落地；落地中途
    失敗＝清掉已寫的檔與這次建出的目錄再拋，目的目錄回到展開前的樣子。"""
    planned = plan_files(template_id, variables, ci=ci, docker_compose=docker_compose)
    if dest.exists() and any(dest.iterdir()):
        raise ScaffoldError("target_not_empty", "展開目的目錄非空")
    base = dest.resolve()
    targets: list[tuple[Path, PlannedFile]] = []
    for item in planned:
        target = (base / item.rel).resolve()
        if item.rel.startswith("/") or ".." in item.rel.split("/") or not is_within(target, base):
            raise ScaffoldError("path_escape", f"輸出路徑 {item.rel} 解析後不在新專案根之下")
        targets.append((target, item))
    created_dirs: list[Path] = []
    written: list[Path] = []
    try:
        for target, item in targets:
            missing = [p for p in reversed(target.parents) if not p.exists() and is_within(p, base)]
            target.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.extend(missing)
            fsutil.write_text_atomic(target, item.data.decode("utf-8"))
            written.append(target)
    except BaseException:
        for path in written:
            path.unlink(missing_ok=True)
        for directory in sorted(set(created_dirs), key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return sorted(item.rel for _t, item in targets)


# ── 研究工作區複製 ─────────────────────────────────────────────────────────────────────────
def workspace_files(src: Path, dirs: Sequence[str] = WORKSPACE_DIRS) -> list[str]:
    """工作區四個編號目錄內的一般檔案（相對 `src`、POSIX、字母序；略過符號連結）。"""
    found: list[str] = []
    for name in dirs:
        root = src / name
        if not root.is_dir():
            continue
        found += [p.relative_to(src).as_posix() for p in root.rglob("*")
                  if p.is_file() and not p.is_symlink()]
    return sorted(found)


def copy_workspace(src: Path, dst: Path, dirs: Sequence[str] = WORKSPACE_DIRS) -> list[CopiedFile]:
    """逐檔複製＋sha256 驗證；驗證不符＝`ScaffoldError("copy_verify_failed")`（已複製的檔不刪，由人
    處置，與「失敗不補償到破壞態」一致）。原工作區不被改動。"""
    out: list[CopiedFile] = []
    for rel in workspace_files(src, dirs):
        source, target = src / rel, dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        expected, actual = sha256_file(source), sha256_file(target)
        if expected != actual:
            raise ScaffoldError("copy_verify_failed", f"{rel} 複製後的 sha256 與來源不符")
        out.append(CopiedFile(rel, actual))
    return out


# ── 初始 commit 的預測 ─────────────────────────────────────────────────────────────────────
def is_ignored(rel: str) -> bool:
    """依範本 `.gitignore` 的樣式（`GITIGNORE_*`）判斷 `rel` 是否被排除（不依賴 git）。"""
    parts = rel.split("/")
    if parts[-1] in GITIGNORE_FILE_NAMES or parts[-1].endswith(GITIGNORE_SUFFIXES):
        return True
    if any(p in GITIGNORE_DIR_NAMES for p in parts[:-1]):
        return True
    for pattern in GITIGNORE_ROOT_DIRS:
        if tuple(parts[: len(pattern)]) == pattern and len(parts) > len(pattern):
            return True
    for pattern in GITIGNORE_ANYWHERE_DIRS:
        width = len(pattern)
        for i in range(len(parts) - width):
            if tuple(parts[i: i + width]) == pattern:
                return True
    return False


def tracked_files(template_rels: Sequence[str], slug: str, copied_rels: Sequence[str]) -> list[str]:
    """初始 commit 預期追蹤的檔案集合（字母序）：範本展開檔加副本（`my-project/<slug>/…`）去掉被
    `.gitignore` 排除者；與 `git ls-files` 逐項對拍。"""
    prefix = f"{WORKSPACE_COPY_ROOT}/{slug}/"
    kept = [r for r in template_rels if not is_ignored(r)]
    kept += [prefix + r for r in copied_rels if not is_ignored(r)]
    return sorted(set(kept))
