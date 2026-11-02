"""研究面設定：`BRIDGE_RESEARCH_*` 的讀取與驗證，以及能力資訊（ADR-003 D2／D7／D8／D10）。

環境變數一覽的唯一真相源是 `app/settings.py` 檔頭（README 的環境表與它同步；
`tests/test_research_settings.py` 逐一核對）。本模組只做三件事：
  1. `parse_research_env`：把環境映射解成研究面欄位，驗證後由 `load_settings` 併入 `Settings`
     的 `research_*` 欄位；
  2. 工作區根的預設與允許根的處置（見該函式）；
  3. `research_info`：`GET /research/capabilities` 與 `GET /health/deep` 共用的資訊欄。

預設值（`RESEARCH_DEFAULT_*`）住 `app/settings.py`（與 `DEFAULT_OUTBOUND_ALLOWLIST` 同處），測試與
產品碼共用同一份，本模組只 import、不複製。
"""
from __future__ import annotations

import math
import re
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..security import is_within
from ..settings import (
    RESEARCH_DEFAULT_FETCH_ALLOWLIST,
    RESEARCH_DEFAULT_FETCH_MAX_BYTES,
    RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS,
    RESEARCH_DEFAULT_MAX_CONCURRENT_RUNS,
    RESEARCH_DEFAULT_STEP_TIMEOUT_SECONDS,
    SettingsError,
    _anchor_guard,
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
)

#: 量不到的資訊一律標這個字樣，不省略鍵（TCS AT-960-2-7）。
NOT_EVALUABLE = "NOT-EVALUABLE"
#: `research_info` 的鍵集合（固定；`/health/deep` 的 `research` 與 capabilities 逐鍵相同）。
INFO_KEYS: tuple[str, ...] = (
    "mode", "root", "db", "claude_cli", "gh_cli", "git", "web_layer_enabled", "scaffold_templates")

_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
#: 一個 stage 步驟牆鐘的上界（秒）：一天。再長的值只會是誤設。
_STEP_TIMEOUT_MAX = 86_400


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
    )


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
        "scaffold_templates": [],
    }
