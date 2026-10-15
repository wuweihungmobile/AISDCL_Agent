"""Bridge 設定：全部走環境變數（不引入 pydantic-settings，少一個相依、測試直接傳 dict）。

環境變數一覽（唯一真相源；README 的表由此而來）：
  BRIDGE_HOST                 `python -m app.main` 的綁定位址（預設 127.0.0.1）
                              （Docker CMD 另帶 0.0.0.0）
  BRIDGE_PORT                 預設 8081
  ENGINE_WORKSPACE            每個 run 的工作區根（預設 <engine-bridge>/.workspace）
  AUTOCLAUDE_ROOT             AutoClaude 原始碼根（預設 <monorepo>/AutoClaude）
                              （只供 /health 顯示）
  SDD_ROOT                    AISDLC_SDD 版本目錄，或含 AISDLC_SDD_v* 的父目錄（取數字最大者）
                              （預設 <monorepo>/AISDLC_SDD 下數字最大者）
  BRIDGE_DB_DSN               PostgreSQL DSN；未設＝純檔案模式（不寫 DB、鎖只在行程內）
  BRIDGE_DB_SCHEMA            Console 九張表所在的 schema（預設 console；SQL 一律以此限定名）
  BRIDGE_INSTANCE             本實例識別（預設 <hostname>-<pid>-<uuid8>；≤100 字）
  BRIDGE_STOP_GRACE_SECONDS   stop 送終止訊號後等多久才升級強殺（預設 30）
  BRIDGE_ALLOWED_PATH_ROOTS   execution_path／spec_dir 必須落在其下的根目錄清單，
                              以 os.pathsep 分隔（POSIX `:`／Windows `;`）；
                              預設＝工作區＋monorepo 根
  BRIDGE_OUTBOUND_ALLOWLIST   外呼 host 白名單（逗號分隔）；
                              預設 api.minimax.io,api.minimax.chat,localhost,127.0.0.1
  BRIDGE_LOG_DIR              有值時，另把日誌寫成滾動檔 <dir>/bridge.log
                              （UTC 午夜切檔、保留 7 份）；未設＝只輸出到 stderr。
                              docker compose 設 /app/logs（與 backend 共用 app_logs 卷）
"""
from __future__ import annotations

import os
import re
import socket
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTBOUND_ALLOWLIST = ("api.minimax.io", "api.minimax.chat", "localhost", "127.0.0.1")
_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_SDD_DIR_RE = re.compile(r"^AISDLC_SDD_v(\d+)\.(\d+)$")

# <monorepo>/AgentConsole/engine-bridge
BRIDGE_DIR = Path(__file__).resolve().parents[1]
# <monorepo>（容器內不是 monorepo，見 _looks_like_monorepo）
REPO_ROOT = BRIDGE_DIR.parents[1]


class SettingsError(ValueError):
    """環境變數值不合法（啟動即 fail-loud，不靜默退回預設）。"""


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    engine_workspace: Path
    autoclaude_root: Path
    sdd_root: Path | None
    db_dsn: str | None
    db_schema: str
    bridge_instance: str
    stop_grace_seconds: float
    allowed_path_roots: tuple[Path, ...]
    outbound_allowlist: tuple[str, ...]
    log_dir: Path | None = None


def _looks_like_monorepo(root: Path) -> bool:
    # 容器內 BRIDGE_DIR.parents[1] 會是 `/`：把它當白名單根等於整個檔案系統都放行，
    # 所以要先認得出來。
    return (root / "AutoClaude").is_dir() and (root / "AgentConsole").is_dir()


def discover_sdd_root(sdd_parent: Path) -> Path | None:
    """`<sdd_parent>/AISDLC_SDD_v<M>.<N>` 中**數字**最大者（字串排序會把 v0.9 排在 v0.30 後面）。"""
    best: tuple[tuple[int, int], Path] | None = None
    if sdd_parent.is_dir():
        for child in sdd_parent.iterdir():
            m = _SDD_DIR_RE.match(child.name)
            if m and child.is_dir():
                key = (int(m.group(1)), int(m.group(2)))
                if best is None or key > best[0]:
                    best = (key, child)
    return best[1].resolve() if best else None


def _anchor_guard(path: Path, var: str) -> Path:
    resolved = path.resolve()
    if resolved == Path(resolved.anchor):
        raise SettingsError(f"{var} 不可是檔案系統根（{resolved}）：白名單根等於整個磁碟都放行")
    return resolved


def _parse_roots(raw: str) -> tuple[Path, ...]:
    roots = [_anchor_guard(Path(p), "BRIDGE_ALLOWED_PATH_ROOTS")
             for p in raw.split(os.pathsep) if p.strip()]
    if not roots:
        raise SettingsError("BRIDGE_ALLOWED_PATH_ROOTS 解析後為空")
    return tuple(roots)


def _parse_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name}={raw!r} 不是數字") from exc
    if value <= 0:
        raise SettingsError(f"{name} 必須 > 0，實際 {value}")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    e: Mapping[str, str] = os.environ if env is None else env

    raw_port = e.get("BRIDGE_PORT", "").strip() or "8081"
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise SettingsError(f"BRIDGE_PORT={raw_port!r} 不是整數") from exc
    if not 1 <= port <= 65535:
        raise SettingsError(f"BRIDGE_PORT 超出範圍：{port}")

    workspace = Path(e.get("ENGINE_WORKSPACE", "").strip() or BRIDGE_DIR / ".workspace").resolve()
    autoclaude_root = Path(
        e.get("AUTOCLAUDE_ROOT", "").strip() or REPO_ROOT / "AutoClaude").resolve()

    raw_sdd = e.get("SDD_ROOT", "").strip()
    if raw_sdd:
        given = Path(raw_sdd).resolve()
        # 可給版本目錄本身，或含 AISDLC_SDD_v* 的父目錄（Docker 把整個 AISDLC_SDD 唯讀掛成 /sdd
        # 時，掛載點的目錄名是 `sdd`，不是版本名——取數字最大者才能讓 /sdd/version 回正確版號）。
        sdd_root = given if _SDD_DIR_RE.match(given.name) else (discover_sdd_root(given) or given)
    else:
        sdd_root = discover_sdd_root(REPO_ROOT / "AISDLC_SDD")

    schema = e.get("BRIDGE_DB_SCHEMA", "").strip() or "console"
    if not _SCHEMA_RE.match(schema):
        # schema 名會進 SQL（以 Identifier 引用，但仍在入口擋掉怪名字，免得靜默連到別的 schema）。
        raise SettingsError(f"BRIDGE_DB_SCHEMA={schema!r} 不是合法的 SQL 識別字")

    instance = e.get("BRIDGE_INSTANCE", "").strip() or (
        f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}")

    raw_roots = e.get("BRIDGE_ALLOWED_PATH_ROOTS", "").strip()
    if raw_roots:
        roots = _parse_roots(raw_roots)
    else:
        defaults = [workspace]
        if _looks_like_monorepo(REPO_ROOT):
            defaults.append(REPO_ROOT.resolve())
        roots = tuple(defaults)

    raw_allow = e.get("BRIDGE_OUTBOUND_ALLOWLIST", "").strip()
    allowlist = tuple(h.strip().lower().rstrip(".") for h in raw_allow.split(",") if h.strip()) \
        if raw_allow else DEFAULT_OUTBOUND_ALLOWLIST

    raw_log_dir = e.get("BRIDGE_LOG_DIR", "").strip()

    return Settings(
        host=e.get("BRIDGE_HOST", "").strip() or "127.0.0.1",
        port=port,
        engine_workspace=workspace,
        autoclaude_root=autoclaude_root,
        sdd_root=sdd_root,
        db_dsn=e.get("BRIDGE_DB_DSN", "").strip() or None,
        db_schema=schema,
        bridge_instance=instance[:100],
        stop_grace_seconds=_parse_float(e, "BRIDGE_STOP_GRACE_SECONDS", 30.0),
        allowed_path_roots=roots,
        outbound_allowlist=allowlist,
        log_dir=Path(raw_log_dir).resolve() if raw_log_dir else None,
    )
