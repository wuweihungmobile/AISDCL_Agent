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
  BRIDGE_SDD_WRITE_TOKEN      SDD 寫入面權杖（ADR-XPLAT-016 §9）：`:freeze`、含 `sdd` 區塊的
                              `POST /autoclaude/runs`（及其 `:resume`／`/restore`）須帶標頭
                              `X-Bridge-Token`，值與此相同。
                              未設＝這些請求整個停用（503 `sdd_write_disabled`）；有設但短於 32
                              字元或仍是 `<…>` 佔位＝啟動即 SettingsError（不靜默退回停用）。
                              只有 backend 與 Bridge 持有；引擎子行程與 FSM CLI 子行程的環境一律
                              不含它。repo 內不放真值
  SI_ROOT                     SelfImproving 的 repo 根（其下 `tools/` 有根層 CLI，`docs/06_quality/`
                              有帳本）：`/si/*` 以子行程在此目錄呼叫唯讀 `export`（P1b）。
                              未設時，本機直跑且 `REPO_ROOT` 像 monorepo 就取 monorepo 根，否則
                              （例如容器內）為 None；不檢查存在性與內容——缺 CLI 在請求時回 503
                              `si_unavailable`（cause 為 si_script_missing）。不可是檔案系統根；
                              不併入 BRIDGE_ALLOWED_PATH_ROOTS（那是引擎 execution_path 的閘）。
                              docker compose 設 /repo 並以唯讀 bind 掛入必要子集
"""
from __future__ import annotations

import os
import re
import socket
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_OUTBOUND_ALLOWLIST = ("api.minimax.io", "api.minimax.chat", "localhost", "127.0.0.1")
_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_SDD_DIR_RE = re.compile(r"^AISDLC_SDD_v(\d+)\.(\d+)$")
#: 寫入權杖的最短長度（≥32 字元隨機；`openssl rand -hex 32` 得 64 字元）。
SDD_WRITE_TOKEN_MIN_LEN = 32

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
    #: SDD 寫入權杖；repr=False 讓 `print(settings)`／日誌不會把它帶出去。None＝寫入面停用。
    sdd_write_token: str | None = field(default=None, repr=False)
    #: SelfImproving 的 repo 根（R1）；None＝SI 面不可用（請求時回 503 `si_unavailable`，
    #: cause 為 `si_root_unset`）。
    si_root: Path | None = None


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


def _anchor_guard(path: Path, var: str,
                  why: str = "白名單根等於整個磁碟都放行") -> Path:
    resolved = path.resolve()
    if resolved == Path(resolved.anchor):
        raise SettingsError(f"{var} 不可是檔案系統根（{resolved}）：{why}")
    return resolved


def _parse_roots(raw: str) -> tuple[Path, ...]:
    roots = [_anchor_guard(Path(p), "BRIDGE_ALLOWED_PATH_ROOTS")
             for p in raw.split(os.pathsep) if p.strip()]
    if not roots:
        raise SettingsError("BRIDGE_ALLOWED_PATH_ROOTS 解析後為空")
    return tuple(roots)


def _parse_sdd_write_token(env: Mapping[str, str]) -> str | None:
    """未設（含全空白）＝None；有設但太短或是 `<…>` 佔位＝SettingsError。
    佔位當真值等於公開密鑰、太短的權杖擋不住猜測，所以啟動即大聲失敗，不退回「停用」。
    錯誤訊息不含值本身（連佔位也不回印，免得把真值寫進日誌）。"""
    raw = env.get("BRIDGE_SDD_WRITE_TOKEN", "").strip()
    if not raw:
        return None
    if (raw.startswith("<") and raw.endswith(">")) or "<YOUR_" in raw.upper():
        raise SettingsError("BRIDGE_SDD_WRITE_TOKEN 仍是 <…> 佔位符：請換成 ≥32 字元的隨機值，"
                            "或整個移除以停用 SDD 寫入面")
    if len(raw) < SDD_WRITE_TOKEN_MIN_LEN:
        raise SettingsError(f"BRIDGE_SDD_WRITE_TOKEN 太短（{len(raw)} 字元）：至少 "
                            f"{SDD_WRITE_TOKEN_MIN_LEN} 字元，或整個移除以停用 SDD 寫入面")
    return raw


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

    raw_si = e.get("SI_ROOT", "").strip()
    if raw_si:
        si_root: Path | None = _anchor_guard(
            Path(raw_si), "SI_ROOT", "子行程的 cwd 與 git safe.directory 都會放行整個磁碟")
    else:
        si_root = REPO_ROOT.resolve() if _looks_like_monorepo(REPO_ROOT) else None

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
        sdd_write_token=_parse_sdd_write_token(e),
        si_root=si_root,
    )
