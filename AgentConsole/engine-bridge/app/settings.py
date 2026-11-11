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
  BRIDGE_SI_WRITE_TOKEN       SI 寫入面權杖（P2b；W1）：`POST /si/proposals/{id}:decide`、
                              `POST /si/observations`、`POST /si/observations/{id}:close`
                              須帶標頭 `X-Bridge-Token`，值與此相同（`.../observations:validate`
                              是唯讀預檢，不需權杖）。規則同 BRIDGE_SDD_WRITE_TOKEN：未設＝停用；
                              有設但短於 32 字元或仍是 `<…>` 佔位＝啟動即 SettingsError。只有
                              backend 與 Bridge 持有；Bridge 不持有稽核簽章金鑰（金鑰只在
                              console-api 與主機端 CLI）。repo 內不放真值
  BRIDGE_SI_AUDIT_DIR         稽核檔落地目錄（容器內路徑；P2b；W1）：寫入端點把 backend 簽好的
                              稽核 JSON 以 `<audit_ref>.json` 原樣寫在這裡（`app/si_audit.py` 是
                              整個 `app/` 唯一以寫入形態開 SI 路徑者），主機端 CLI 再以
                              `--carrier console` 入帳。未設＝寫入面停用；不檢查存在性（目錄缺席在
                              請求時回 503 `si_unavailable`，cause 為 audit_write_failed）、不併入
                              BRIDGE_ALLOWED_PATH_ROOTS，不可是檔案系統根。寫入面啟用＝本變數與
                              BRIDGE_SI_WRITE_TOKEN 皆有設（未啟用時三個寫入端點一律 503
                              `si_write_disabled`）。docker compose 把它以可寫 bind 掛到主機的
                              `<AUTOSDD_SI_DIR>/console_audit`（其餘 SI bind 皆唯讀）
  BRIDGE_SI_REPORT_DIR        巡邏快照目錄（容器內路徑；TCS-SiFlowVisibility W-F1、W-F2）：
                              根層巡邏器
                              把 `patrol.json` 寫在這裡，`GET /si/patrol` 只讀它
                              （`app/si_report.py`）。
                              須為絕對路徑、不可是檔案系統根、不可與 BRIDGE_SI_AUDIT_DIR 相同；
                              不檢查存在性。未設＝此部署沒有掛載（`/si/patrol` 回 503
                              `report_dir_unset`，其他 SI 端點與 `/health` 不受影響）。docker
                              compose 把它以**唯讀** bind 掛到主機的
                              `<AUTOSDD_SI_DIR>/console_report`
  BRIDGE_RESEARCH_ROOT        ResearchToPRD 研究工作區根（ADR-003 D8）。預設在 **repo 外**：
                              Windows 為家目錄（USERPROFILE）下的 .autosdd/my-project，
                              POSIX 為 ~/.autosdd/my-project（Docker 由 compose 明設
                              /workspace/my-project）。不可是檔案系統根。研究面啟用（明設
                              本變數，或設了寫入權杖）且明設了 BRIDGE_ALLOWED_PATH_ROOTS 時，
                              必須落在其中某個根之下，否則啟動即 SettingsError；啟用時並自動
                              併入允許根（`/sdd/fsm/{key}?root=<工作區>` 的路徑閘靠它放行）。
                              研究面沒啟用時不動允許根。工作區結構 `<root>/<slug>/` 下有
                              00_research、01_specs、02_governance、03_execution；
                              `GET /health/deep` 的 `research.root` 揭露解析結果
  BRIDGE_RESEARCH_WRITE_TOKEN 研究寫入面權杖（HTTP 標頭 `X-Bridge-Token`；backend 的
                              `console.bridge.research-write-token` 與它同值；與 SDD、SI 的
                              權杖是三個獨立的值）。規則同 BRIDGE_SI_WRITE_TOKEN：未設＝停用
                              （寫入端點 503 `research_write_disabled`）；有設但短於 32 字元
                              或仍是 `<…>` 佔位＝啟動即 SettingsError。研究端點另需
                              BRIDGE_DB_DSN：無 DSN 一律 503 `research_requires_db`，不降級成
                              純檔案模式。引擎、FSM、git 子行程的環境一律不含它；repo 內不放真值
  BRIDGE_RESEARCH_FETCH_ALLOWLIST
                              Bridge 原生抓取（API 層）的主機基底，逗號分隔；預設
                              export.arxiv.org、arxiv.org、api.semanticscholar.org、
                              api.github.com、api.stackexchange.com。有效清單＝本變數 ∪ 啟用中的
                              ADMIN 條目；與 BRIDGE_OUTBOUND_ALLOWLIST（模型端點）是兩份獨立清單
  BRIDGE_RESEARCH_WEB_ALLOWLIST
                              headless WebSearch／WebFetch 的網域基底，逗號分隔；**預設空＝
                              Web 層關閉**（產業層需 ADMIN 逐一加入；有效清單同上）
  BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS
                              同時 stage run 數（預設 1；額度保守）
  BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS
                              每個 stage run 的步驟牆鐘秒數（預設 1200；1～86400），寫入
                              `config_overrides.playbook.step_timeout_seconds`；請求 env 的
                              CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS 與它同源（乘 1000）
  BRIDGE_RESEARCH_CLAUDE_COMMAND
                              stage run 的 `claude.command`（未設＝引擎預設的 claude）；
                              Docker 全棧 E2E 設 aisdlc-mock-claude
  BRIDGE_RESEARCH_FETCH_MAX_BYTES
                              原生抓取單一回應的位元組上限（預設 5242880＝5 MiB）
  BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS
                              原生抓取的逾時秒數（預設 20）
  BRIDGE_SCAFFOLD_ROOT        軌道 B（新專案）的骨架根（ADR-003 D8、D-96）。**無預設**：未設
                              ＝軌道 B 停用（預演回 `route_unsupported_in_deployment`，缺項
                              `scaffold_root`）。不可是檔案系統根；設了即自動併入允許根（明設了
                              BRIDGE_ALLOWED_PATH_ROOTS 時須落在其中某個根之下，否則啟動即
                              SettingsError）。新專案根＝`<本根>/<project_name>`
  BRIDGE_WORKTREE_ROOT        軌道 A 的 git worktree 根（D-95）。預設
                              `<BRIDGE_RESEARCH_ROOT>/_worktrees`（repo 外）；每個分流在其下建
                              一個獨立 worktree，不動使用中的工作樹
  BRIDGE_REPO_ROOT            軌道 A 要寫的 monorepo 根（D-96）。未設＝`REPO_ROOT`（Bridge 所在
                              的 monorepo）；`repo_writable` 與 git 子行程的 cwd 都讀它（INT
                              載具以它指向拋棄式 clone）
  BRIDGE_ROUTE_TIMEOUT_SECONDS
                              `:route` 同步執行的牆鐘上限（預設 300；1～3600；D-105）；逾時＝
                              502 `route_step_failed`（`reason=route_timeout`）
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
#: SDD、SI、研究三個寫入面共用。
SDD_WRITE_TOKEN_MIN_LEN = 32
SI_WRITE_TOKEN_MIN_LEN = SDD_WRITE_TOKEN_MIN_LEN
RESEARCH_WRITE_TOKEN_MIN_LEN = SDD_WRITE_TOKEN_MIN_LEN

#: 研究面（ResearchToPRD；ADR-003 D7／D8、Architecture §9.4）的預設值——唯一一份，產品碼與測試共用
#: （解析邏輯在 `app/research/settings.py`，它從這裡 import）。
RESEARCH_DEFAULT_FETCH_ALLOWLIST = (
    "export.arxiv.org", "arxiv.org", "api.semanticscholar.org", "api.github.com",
    "api.stackexchange.com")
RESEARCH_DEFAULT_MAX_CONCURRENT_RUNS = 1
# D-75：對齊引擎 Kernel 路徑固定的步驟逾時（kernel.py:196），看門狗才會先於引擎響
RESEARCH_DEFAULT_STEP_TIMEOUT_SECONDS = 600
RESEARCH_DEFAULT_FETCH_MAX_BYTES = 5 * 1024 * 1024
RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS = 20.0
#: D-105：`:route` 同步執行的牆鐘（秒）；console-api 的讀逾時（330 s）必須大於它。
RESEARCH_DEFAULT_ROUTE_TIMEOUT_SECONDS = 300

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
    #: ResearchToPRD 研究面（`BRIDGE_RESEARCH_*`；解析與驗證見 `app/research/settings.py`）。
    #: 這幾個欄位刻意放在 `log_dir` 之前：末尾五欄的相對順序是既有測試釘住的
    #: （`test_si_cli.py`），新欄位不往後加。
    #: `research_root` 是已 resolve 的工作區根（`load_settings` 一律給值）；`research_write_token`
    #: repr=False 同其他權杖，None＝研究寫入面停用。
    research_root: Path
    research_write_token: str | None = field(default=None, repr=False)
    research_fetch_allowlist: tuple[str, ...] = RESEARCH_DEFAULT_FETCH_ALLOWLIST
    research_web_allowlist: tuple[str, ...] = ()
    research_max_concurrent_runs: int = RESEARCH_DEFAULT_MAX_CONCURRENT_RUNS
    research_step_timeout_seconds: int = RESEARCH_DEFAULT_STEP_TIMEOUT_SECONDS
    research_claude_command: str | None = None
    research_fetch_max_bytes: int = RESEARCH_DEFAULT_FETCH_MAX_BYTES
    research_fetch_timeout_seconds: float = RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS
    #: P1 分流（D-95／D-96／D-105）：軌道 B 骨架根（None＝停用）、軌道 A worktree 根（None＝
    #: `<research_root>/_worktrees`，見 `worktree_root`）、monorepo 根覆寫（None＝`REPO_ROOT`，見
    #: `repo_root`）、同步執行的牆鐘秒數。
    research_scaffold_root: Path | None = None
    research_worktree_root: Path | None = None
    research_repo_root: Path | None = None
    research_route_timeout_seconds: int = RESEARCH_DEFAULT_ROUTE_TIMEOUT_SECONDS
    log_dir: Path | None = None
    #: SDD 寫入權杖；repr=False 讓 `print(settings)`／日誌不會把它帶出去。None＝寫入面停用。
    sdd_write_token: str | None = field(default=None, repr=False)
    #: SelfImproving 的 repo 根（R1）；None＝SI 面不可用（請求時回 503 `si_unavailable`，
    #: cause 為 `si_root_unset`）。
    si_root: Path | None = None
    #: SelfImproving 寫入面權杖（P2b W1）；repr=False 同 sdd_write_token。None＝寫入面停用。
    si_write_token: str | None = field(default=None, repr=False)
    #: 稽核檔落地目錄（P2b W1；已 resolve、不檢查存在性、不併入 allowed_path_roots）。
    #: None＝寫入面停用。
    si_audit_dir: Path | None = None
    #: 巡邏快照目錄（TCS-SiFlowVisibility W-F1；已 resolve、不檢查存在性、**唯讀**、不併入
    #: allowed_path_roots、不得與稽核目錄相同）。None＝此部署沒有掛載（`/si/patrol` 回 503
    #: `report_dir_unset`，其他 SI 功能不受影響）。
    si_report_dir: Path | None = None

    @property
    def si_write_enabled(self) -> bool:
        """SI 寫入面啟用＝權杖與稽核目錄兩者皆已設定（W1）；任一缺＝三個寫入端點一律 503。"""
        return self.si_write_token is not None and self.si_audit_dir is not None

    @property
    def worktree_root(self) -> Path:
        """軌道 A 的 worktree 根（D-95）：明設值，否則 `<研究工作區根>/_worktrees`。"""
        return self.research_worktree_root or (self.research_root / "_worktrees")

    @property
    def repo_root(self) -> Path:
        """軌道 A 要寫的 monorepo 根（D-96）：明設值，否則 Bridge 所在的 `REPO_ROOT`。"""
        return self.research_repo_root or REPO_ROOT

    @property
    def research_write_enabled(self) -> bool:
        """研究寫入面啟用＝已設寫入權杖；未設＝寫入端點一律 503 `research_write_disabled`。
        （資料庫另算：無 `db_dsn` 時研究端點 503 `research_requires_db`，與權杖互相獨立。）"""
        return self.research_write_token is not None


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


def _parse_write_token(env: Mapping[str, str], name: str, surface: str) -> str | None:
    """未設（含全空白）＝None；有設但太短或是 `<…>` 佔位＝SettingsError。
    佔位當真值等於公開密鑰、太短的權杖擋不住猜測，所以啟動即大聲失敗，不退回「停用」。
    錯誤訊息不含值本身（連佔位也不回印，免得把真值寫進日誌）。`name`＝環境變數名、
    `surface`＝被停用的寫入面名稱（只進訊息）。"""
    raw = env.get(name, "").strip()
    if not raw:
        return None
    if (raw.startswith("<") and raw.endswith(">")) or "<YOUR_" in raw.upper():
        raise SettingsError(f"{name} 仍是 <…> 佔位符：請換成 ≥32 字元的隨機值，"
                            f"或整個移除以停用 {surface}")
    if len(raw) < SDD_WRITE_TOKEN_MIN_LEN:
        raise SettingsError(f"{name} 太短（{len(raw)} 字元）：至少 "
                            f"{SDD_WRITE_TOKEN_MIN_LEN} 字元，或整個移除以停用 {surface}")
    return raw


def _parse_sdd_write_token(env: Mapping[str, str]) -> str | None:
    return _parse_write_token(env, "BRIDGE_SDD_WRITE_TOKEN", "SDD 寫入面")


def _parse_si_write_token(env: Mapping[str, str]) -> str | None:
    return _parse_write_token(env, "BRIDGE_SI_WRITE_TOKEN", "SI 寫入面")


def _parse_si_report_dir(env: Mapping[str, str], audit_dir: Path | None) -> Path | None:
    """`BRIDGE_SI_REPORT_DIR`：未設（含全空白）＝None；須為絕對路徑（Windows 的 `/x` 這種「無磁碟機
    代號但有根」也算，故以 `anchor` 判斷）、不可是檔案系統根、不可與稽核目錄相同（兩個目錄一個唯讀
    一個可寫，同一個就等於把稽核目錄當快照來源）。不檢查存在性、不建立目錄。"""
    raw = env.get("BRIDGE_SI_REPORT_DIR", "").strip()
    if not raw:
        return None
    if Path(raw).anchor == "":
        raise SettingsError(f"BRIDGE_SI_REPORT_DIR 須為絕對路徑（實際 {raw!r}）")
    resolved = _anchor_guard(Path(raw), "BRIDGE_SI_REPORT_DIR",
                             "快照目錄是唯讀來源，檔案系統根等於把整個磁碟當作回報目錄")
    if audit_dir is not None and os.path.normcase(str(resolved)) == os.path.normcase(
            str(audit_dir)):
        raise SettingsError("BRIDGE_SI_REPORT_DIR 不得與 BRIDGE_SI_AUDIT_DIR 相同"
                            "（一個唯讀的回報目錄、一個可寫的稽核目錄，必須是兩個目錄）")
    return resolved


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

    # 研究面（ADR-003 D8）：延遲 import——`app.research.settings` 自己也 import 本模組的常數
    # 與錯誤型別，頂層 import 會成環。
    from .research.settings import parse_research_env

    research = parse_research_env(e, allowed_roots=roots, roots_explicit=bool(raw_roots))

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

    raw_audit = e.get("BRIDGE_SI_AUDIT_DIR", "").strip()
    si_audit_dir: Path | None = _anchor_guard(
        Path(raw_audit), "BRIDGE_SI_AUDIT_DIR",
        "稽核檔會寫在這個目錄之下，檔案系統根等於整個磁碟都可寫") if raw_audit else None

    si_report_dir = _parse_si_report_dir(e, si_audit_dir)

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
        allowed_path_roots=research.allowed_roots,
        outbound_allowlist=allowlist,
        research_root=research.root,
        research_write_token=research.write_token,
        research_fetch_allowlist=research.fetch_allowlist,
        research_web_allowlist=research.web_allowlist,
        research_max_concurrent_runs=research.max_concurrent_runs,
        research_step_timeout_seconds=research.step_timeout_seconds,
        research_claude_command=research.claude_command,
        research_fetch_max_bytes=research.fetch_max_bytes,
        research_fetch_timeout_seconds=research.fetch_timeout_seconds,
        research_scaffold_root=research.scaffold_root,
        research_worktree_root=research.worktree_root,
        research_repo_root=research.repo_root,
        research_route_timeout_seconds=research.route_timeout_seconds,
        log_dir=Path(raw_log_dir).resolve() if raw_log_dir else None,
        sdd_write_token=_parse_sdd_write_token(e),
        si_root=si_root,
        si_write_token=_parse_si_write_token(e),
        si_audit_dir=si_audit_dir,
        si_report_dir=si_report_dir,
    )
