"""研究面設定：`BRIDGE_RESEARCH_*` 的讀取與驗證，以及能力資訊（ADR-003 D2／D7／D8／D10）。

環境變數一覽的唯一真相源是 `app/settings.py` 檔頭（README 的環境表與它同步；
`tests/test_research_settings.py` 逐一核對）。本模組只做三件事：
  1. `parse_research_env`：把環境映射解成研究面欄位，驗證後由 `load_settings` 併入 `Settings`
     的 `research_*` 欄位；
  2. 工作區根的預設與允許根的處置（見該函式）；
  3. `research_info`：`GET /research/capabilities` 與 `GET /health/deep` 共用的八個資訊欄；
     `research_capabilities`：capabilities 端點另加的五個契約鍵（D-76(1)）。

預設值（`RESEARCH_DEFAULT_*`）住 `app/settings.py`（與 `DEFAULT_OUTBOUND_ALLOWLIST` 同處），測試與
產品碼共用同一份，本模組只 import、不複製。
"""
from __future__ import annotations

import math
import os
import re
import shutil
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..security import is_within
from ..settings import (
    REPO_ROOT,
    RESEARCH_DEFAULT_FETCH_ALLOWLIST,
    RESEARCH_DEFAULT_FETCH_MAX_BYTES,
    RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS,
    RESEARCH_DEFAULT_MAX_CONCURRENT_RUNS,
    RESEARCH_DEFAULT_ROUTE_TIMEOUT_SECONDS,
    RESEARCH_DEFAULT_STEP_TIMEOUT_SECONDS,
    SettingsError,
    _anchor_guard,
    _looks_like_monorepo,
    _parse_write_token,
)

if TYPE_CHECKING:
    from ..settings import Settings

#: 本模組讀取的全部環境變數名（README 與 `app/settings.py` 檔頭必須逐一列出；測試核對）。
RESEARCH_ENV_VARS: tuple[str, ...] = (
    "BRIDGE_RESEARCH_ROOT",
    "BRIDGE_RESEARCH_WRITE_TOKEN",
    "BRIDGE_RESEARCH_FETCH_ALLOWLIST",
    "BRIDGE_RESEARCH_WEB_ALLOWLIST",
    "BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS",
    "BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS",
    "BRIDGE_RESEARCH_CLAUDE_COMMAND",
    "BRIDGE_RESEARCH_FETCH_MAX_BYTES",
    "BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS",
    "BRIDGE_SCAFFOLD_ROOT",
    "BRIDGE_WORKTREE_ROOT",
    "BRIDGE_REPO_ROOT",
    "BRIDGE_ROUTE_TIMEOUT_SECONDS",
)

#: 量不到的資訊一律標這個字樣，不省略鍵（TCS AT-960-2-7）。
NOT_EVALUABLE = "NOT-EVALUABLE"
#: `research_info` 的鍵集合（固定；`/health/deep` 的 `research` 與 capabilities 都含這八個鍵）。
INFO_KEYS: tuple[str, ...] = (
    "mode", "root", "db", "claude_cli", "gh_cli", "git", "web_layer_enabled", "scaffold_templates")
#: `GET /research/capabilities` 在 `INFO_KEYS` 之上多帶的契約鍵（API 契約 §2.1；D-76(1)）。只有
#: capabilities 端點帶（`/health/deep` 只當資訊、不查資料庫，鍵集合維持八個）。
CAPABILITY_EXTRA_KEYS: tuple[str, ...] = (
    "sdd_root", "research_root", "scaffold_root", "repo_writable", "fetch_hosts")

_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
#: 一個 stage 步驟牆鐘的上界（秒）：一天。再長的值只會是誤設。
_STEP_TIMEOUT_MAX = 86_400
#: 分流同步執行牆鐘的上界（秒）：一小時（console-api 的讀逾時另有 330 s，設更大只會被讀逾時截掉）。
_ROUTE_TIMEOUT_MAX = 3_600
#: 軌道 B 範本的登記目錄（P1 僅 `python-fastapi`）；測試以 monkeypatch 換成夾具樹（證明清單取自
#: 目錄掃描、不是常數）。
TEMPLATES_DIR = Path(__file__).resolve().parent / "scaffold_templates"
_TEMPLATE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ResearchEnv:
    """`parse_research_env` 的結果；`allowed_roots` 是併入工作區根之後的允許根。"""

    root: Path
    write_token: str | None = field(repr=False)
    fetch_allowlist: tuple[str, ...]
    web_allowlist: tuple[str, ...]
    max_concurrent_runs: int
    step_timeout_seconds: int
    claude_command: str | None
    fetch_max_bytes: int
    fetch_timeout_seconds: float
    allowed_roots: tuple[Path, ...]
    scaffold_root: Path | None = None
    worktree_root: Path | None = None
    repo_root: Path | None = None
    route_timeout_seconds: int = RESEARCH_DEFAULT_ROUTE_TIMEOUT_SECONDS


def default_research_root(env: Mapping[str, str], *, windows: bool | None = None) -> Path:
    """預設工作區根＝家目錄下的 `.autosdd/my-project`（**repo 外**；ADR-003 D8）。

    Windows 行為＝家目錄取 `USERPROFILE`，結果形如 `%USERPROFILE%\\.autosdd\\my-project`；POSIX 取
    `HOME`，結果 `~/.autosdd/my-project`。取不到（環境映射沒給）時退回 `Path.home()`。Docker 沒有
    獨立的預設：映像內只有 `/workspace` 可寫，compose 明設
    `BRIDGE_RESEARCH_ROOT=/workspace/my-project`。
    `windows` 只供測試替換平台；省略時看 `sys.platform`。"""
    win = (sys.platform == "win32") if windows is None else windows
    raw = ((env.get("USERPROFILE") if win else env.get("HOME")) or "").strip()
    home = Path(raw) if raw else Path.home()
    return home / ".autosdd" / "my-project"


def _parse_hosts(env: Mapping[str, str], name: str,
                 default: tuple[str, ...]) -> tuple[str, ...]:
    """逗號分隔的主機清單（小寫、去尾端 `.`、去重、保序）。空白或全空項＝用預設；任一項不是
    合法主機名（含 scheme、埠、路徑、userinfo、空白）＝啟動即 `SettingsError`，不靜默丟掉。"""
    raw = env.get(name, "").strip()
    hosts: list[str] = []
    for item in raw.split(","):
        host = item.strip().lower().rstrip(".")
        if not host:
            continue
        if not _HOST_RE.match(host):
            raise SettingsError(f"{name} 含不合法的主機名 {host!r}：只收小寫主機名"
                                "（不含 scheme、埠、路徑與 userinfo）")
        if host not in hosts:
            hosts.append(host)
    return tuple(hosts) if hosts else default


def _parse_int(env: Mapping[str, str], name: str, default: int, *, minimum: int,
               maximum: int | None = None) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name}={raw!r} 不是整數") from exc
    if value < minimum or (maximum is not None and value > maximum):
        bound = f"{minimum}～{maximum}" if maximum is not None else f"≥ {minimum}"
        raise SettingsError(f"{name} 必須 {bound}，實際 {value}")
    return value


def _parse_positive_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name}={raw!r} 不是數字") from exc
    if not math.isfinite(value) or value <= 0:
        raise SettingsError(f"{name} 必須是 > 0 的有限數字，實際 {raw!r}")
    return value


def parse_research_env(env: Mapping[str, str], *, allowed_roots: tuple[Path, ...],
                       roots_explicit: bool, windows: bool | None = None) -> ResearchEnv:
    """解析 `BRIDGE_RESEARCH_*`。`allowed_roots`＝`BRIDGE_ALLOWED_PATH_ROOTS`（或預設根）解析後的
    結果；`roots_explicit`＝該變數是否由使用者明設。

    工作區根的處置（ADR-003 D8；「研究面啟用」＝明設了 `BRIDGE_RESEARCH_ROOT` 或設了寫入權杖）：
      · 根不可是檔案系統根（`SettingsError`）；
      · 研究面啟用且 `BRIDGE_ALLOWED_PATH_ROOTS` 明設時，根必須落在其中某個根之下，否則
        `SettingsError`（不靜默放行、也不靜默併入——操作者自己劃的圍欄由操作者改）；
      · 研究面啟用時，根自動併入允許根（`/sdd/fsm/{key}?root=<工作區>` 等路徑閘靠它放行工作區）；
      · 研究面沒啟用（兩者皆未設）時一律不動允許根——Bridge 對沒用研究面的部署行為與此前逐位元相同。
    寫入權杖規則同 `BRIDGE_SI_WRITE_TOKEN`：未設或全空白＝`None`（停用）；短於 32 字元或 `<…>`
    佔位＝`SettingsError`。"""
    raw_root = env.get("BRIDGE_RESEARCH_ROOT", "").strip()
    token = _parse_write_token(env, "BRIDGE_RESEARCH_WRITE_TOKEN", "研究寫入面")
    explicit = bool(raw_root)
    if explicit:
        root = _anchor_guard(Path(raw_root), "BRIDGE_RESEARCH_ROOT",
                             "工作區會建在這個目錄之下，檔案系統根等於整個磁碟都可寫")
    else:
        root = default_research_root(env, windows=windows).resolve()
    merged = allowed_roots
    if explicit or token is not None:
        if roots_explicit and not any(is_within(root, allowed) for allowed in allowed_roots):
            origin = "BRIDGE_RESEARCH_ROOT" if explicit else "預設工作區根"
            raise SettingsError(
                f"{origin}（{root}）不在 BRIDGE_ALLOWED_PATH_ROOTS 之下：請明設"
                " BRIDGE_RESEARCH_ROOT 於允許根之內，或把它加進 BRIDGE_ALLOWED_PATH_ROOTS")
        if root not in allowed_roots:
            merged = (*allowed_roots, root)
    command = env.get("BRIDGE_RESEARCH_CLAUDE_COMMAND", "").strip() or None
    scaffold_root = _optional_root(env, "BRIDGE_SCAFFOLD_ROOT", "新專案會建在這個目錄之下")
    worktree_root = _optional_root(env, "BRIDGE_WORKTREE_ROOT", "worktree 會建在這個目錄之下")
    repo_root = _optional_root(env, "BRIDGE_REPO_ROOT", "git 子行程的 cwd 與 repo 可寫探測都讀它")
    for var, extra in (("BRIDGE_SCAFFOLD_ROOT", scaffold_root),
                       ("BRIDGE_WORKTREE_ROOT", worktree_root)):
        if extra is None:
            continue
        if roots_explicit and not any(is_within(extra, allowed) for allowed in allowed_roots):
            raise SettingsError(
                f"{var}（{extra}）不在 BRIDGE_ALLOWED_PATH_ROOTS 之下：請明設於允許根之內，"
                "或把它加進 BRIDGE_ALLOWED_PATH_ROOTS")
        if extra not in merged and not any(is_within(extra, m) for m in merged):
            merged = (*merged, extra)
    return ResearchEnv(
        root=root,
        write_token=token,
        fetch_allowlist=_parse_hosts(env, "BRIDGE_RESEARCH_FETCH_ALLOWLIST",
                                     RESEARCH_DEFAULT_FETCH_ALLOWLIST),
        web_allowlist=_parse_hosts(env, "BRIDGE_RESEARCH_WEB_ALLOWLIST", ()),
        max_concurrent_runs=_parse_int(env, "BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS",
                                       RESEARCH_DEFAULT_MAX_CONCURRENT_RUNS, minimum=1),
        step_timeout_seconds=_parse_int(env, "BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS",
                                        RESEARCH_DEFAULT_STEP_TIMEOUT_SECONDS, minimum=1,
                                        maximum=_STEP_TIMEOUT_MAX),
        claude_command=command,
        fetch_max_bytes=_parse_int(env, "BRIDGE_RESEARCH_FETCH_MAX_BYTES",
                                   RESEARCH_DEFAULT_FETCH_MAX_BYTES, minimum=1),
        fetch_timeout_seconds=_parse_positive_float(
            env, "BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS", RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS),
        allowed_roots=merged,
        scaffold_root=scaffold_root,
        worktree_root=worktree_root,
        repo_root=repo_root,
        route_timeout_seconds=_parse_int(env, "BRIDGE_ROUTE_TIMEOUT_SECONDS",
                                         RESEARCH_DEFAULT_ROUTE_TIMEOUT_SECONDS, minimum=1,
                                         maximum=_ROUTE_TIMEOUT_MAX),
    )


def _optional_root(env: Mapping[str, str], name: str, why: str) -> Path | None:
    """選填的目錄設定：未設（含全空白）＝None；有設則解析並擋檔案系統根。"""
    raw = env.get(name, "").strip()
    return _anchor_guard(Path(raw), name, why) if raw else None


def research_info(cfg: Settings) -> dict[str, Any]:
    """能力資訊（`GET /research/capabilities` 與 `GET /health/deep` 的 `research` 共用；鍵集合
    ＝`INFO_KEYS`）。只看 PATH 與設定、不起任何子行程（能力登記鎖：研究套件無 git／gh 子行程），所以
    版本與 gh 的登入狀態量不到，一律標 `NOT-EVALUABLE`，不省略。

    `mode`：PATH 上找得到 `claude` 與 `git`＝`local`（可跑真研究）；找不到 `claude`＝`mock-only`
    （Docker 全棧只跑 mock claude；UI 停用「啟動深研」，伺服器端不拒絕）。`db`＝是否設了
    `BRIDGE_DB_DSN`（研究端點需要它；連線健康看 `/health/deep` 的 `checks.db`）。"""
    claude = shutil.which("claude") is not None
    git = shutil.which("git") is not None
    gh = shutil.which("gh") is not None
    return {
        "mode": "local" if claude and git else "mock-only",
        "root": str(cfg.research_root),
        "db": cfg.db_dsn is not None,
        "claude_cli": {"ok": claude, "version": NOT_EVALUABLE},
        "gh_cli": {"ok": gh, "authenticated": NOT_EVALUABLE},
        "git": {"ok": git, "version": NOT_EVALUABLE},
        "web_layer_enabled": bool(cfg.research_web_allowlist),
        # P1（D-96）：軌道 B 停用（未設 BRIDGE_SCAFFOLD_ROOT）時不列範本；否則取目錄掃描結果。
        "scaffold_templates": (list_template_ids()
                               if cfg.research_scaffold_root is not None else []),
    }


def list_template_ids(base: Path | None = None) -> list[str]:
    """範本登記目錄的掃描結果（字母序）：只認名稱合 `[A-Za-z0-9_-]` 且內含至少一個檔案的子目錄
    （空目錄與非法名稱不列；新增合法目錄即出現、刪除即消失）。`base` 省略取 `TEMPLATES_DIR`。"""
    root = TEMPLATES_DIR if base is None else base
    if not root.is_dir():
        return []
    found = [child.name for child in root.iterdir()
             if child.is_dir() and _TEMPLATE_ID_RE.fullmatch(child.name)
             and any(p.is_file() for p in child.rglob("*"))]
    return sorted(found)


def repo_writable(cfg: Settings | None = None) -> bool:
    """軌道 A（分流到既有模組）需要寫 monorepo：容器內（`REPO_ROOT` 不像 monorepo、或唯讀）＝假。
    只做權限探測（`os.access`），不寫任何東西。`BRIDGE_REPO_ROOT` 明設（D-96）時讀它：目錄存在且
    可寫即為真（INT 載具指向拋棄式 clone，不要求它像 monorepo）；未設＝Bridge 所在的 `REPO_ROOT`
    須像 monorepo 且可寫。"""
    override = None if cfg is None else cfg.research_repo_root
    if override is not None:
        return override.is_dir() and os.access(override, os.W_OK)
    return _looks_like_monorepo(REPO_ROOT) and os.access(REPO_ROOT, os.W_OK)


def research_capabilities(cfg: Settings, *, fetch_hosts: Sequence[str]) -> dict[str, Any]:
    """`GET /research/capabilities` 的本文：`research_info` 的八個鍵，加上契約 §2.1 的五個
    （`CAPABILITY_EXTRA_KEYS`）。`fetch_hosts` 由呼叫端給（有效 FETCH 清單＝部署基底 ∪ 啟用中的
    ADMIN 條目；後者在資料庫，這裡不查）。`scaffold_root` 取 `BRIDGE_SCAFFOLD_ROOT`（P1；無預設，
    未設＝`None`＝軌道 B 停用）。"""
    return {
        **research_info(cfg),
        "sdd_root": None if cfg.sdd_root is None else str(cfg.sdd_root),
        "research_root": str(cfg.research_root),
        "scaffold_root": (None if cfg.research_scaffold_root is None
                          else str(cfg.research_scaffold_root)),
        "repo_writable": repo_writable(cfg),
        "fetch_hosts": list(fetch_hosts),
    }
