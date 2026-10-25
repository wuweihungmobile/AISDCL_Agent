"""NFR-SEC-03／SEC-04：Bridge 入口的消毒鏈與外呼白名單（PRD §0.3／§0.5）。

三層（對應引擎既有防線 SddToPlaybookAdapter／CONDITIONAL，這裡是 UI 輸入進引擎前的第一道）：
  1. 路徑閘：execution_path／spec_dir 必須絕對、存在、realpath 後落在白名單根之下
     （擋 `..` 與 symlink 逃逸；Windows 不分大小寫、有磁碟機代號，比對前一律 normcase）。
  2. 指令閘：playbook 的 evaluator_command 套與 SddToPlaybookAdapter **同一組**黑名單字元集
     （`! ` > < ~ $ & ;`）；另加換行／NUL——換行在 `sh -c` 裡等同 `;`，不擋就是繞過口。
  3. 外呼閘：config_overrides／env 帶進來的任何外呼 URL，host 必須在 BRIDGE_OUTBOUND_ALLOWLIST，
     否則拒絕並寫審計 log（預設 deny）。

黑名單字元集在這裡自帶一份字面（Bridge 的閘不該因 AutoClaude 改動而無聲改變行為），
與 adapter 原始碼常數的一致性由 tests/test_security.py::TestDenyCharsParity 機械鎖住。
"""
from __future__ import annotations

import hmac
import inspect
import json
import logging
import os
import re
import threading
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from .errors import ApiError
from .tracing import trace_id_var

DENY_CHARS: frozenset[str] = frozenset("!`><~$&;")
#: 換行／回車／NUL：`sh -c` 把換行當命令分隔，不在 adapter 的集合內，但同樣是注入向量。
CONTROL_CHARS: frozenset[str] = frozenset("\n\r\x00")

_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
#: 這些變數能讓子行程在啟動前載入任意程式碼或換掉直譯器／claude 的解析路徑。
_ENV_DENY = frozenset({
    "PATH", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONBREAKPOINT",
    "PYTHONUTF8", "PYTHONIOENCODING", "PYTHONUNBUFFERED",       # 後三者由 Bridge 自己設定
    "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH", "NODE_OPTIONS", "BASH_ENV", "ENV",
    # ADR-XPLAT-016 §9：SDD 寫入面的三個名字只准 Bridge 自己設定（權杖永不進引擎；FSM 專案由
    # `sdd` 區塊伺服端注入；狀態目錄只給 CLI 子行程）。請求層 `env` 帶它們＝422
    # `forbidden_name`，大聲而非靜默覆蓋。
    "BRIDGE_SDD_WRITE_TOKEN", "SDD_PROJECT", "SDD_STATE_DIR",
})
_ENV_URL_KEYS = ("MINIMAX_BASE_URL", "MINIMAX_EMBED_BASE_URL", "TEI_URL")
_ENV_VALUE_MAX = 8192

#: config_overrides 允許的頂層區段（AppConfig 其餘頂層鍵由 Bridge 管控或不適用）。
_OVERRIDE_SECTIONS = frozenset({
    "claude", "minimax", "embedder", "loop", "playbook", "token_guard", "alert_ladder",
    "notification", "tool_invocation", "executor", "preferences",
})
#: Bridge 管控：路徑類（落在 run 工作區、不給呼叫端挑）與儲存後端（引擎狀態由 Bridge 以檔案管理）。
#: 這些鍵**合法但不被採用**：console-api 的 ConfigMaterializer 會依系統參數帶上 `storage.*`，
#: 回 422 會讓所有 run 都起不來；改為忽略並發 CONFIG_OVERRIDE_IGNORED alert
#: （見 ignored_managed_keys）。
MANAGED_KEYS = frozenset({
    "checkpoint_dir", "log_dir", "backup_dir", "scripts_dir", "workflow_search_paths", "storage",
})
#: 機密不得落進磁碟上的 config.yaml：走 `env`（MINIMAX_API_KEY、AUTOCLAUDE_DB_DSN）。
_SECRET_KEYS = frozenset({("minimax", "api_key"), ("embedder", "api_key"),
                          ("storage", "db_dsn")})
#: 設定值是外呼 URL 的位置（section, key）。
_URL_KEYS = (
    ("minimax", "base_url"), ("embedder", "base_url"), ("embedder", "bge_m3_url"),
    ("notification", "webhook_url"),
)

Violation = dict[str, Any]


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── 審計 log（NFR-SEC-04「全程審計」）──────────────────────────────────────────
class AuditLog:
    """append-only 的審計 JSONL（`<workspace>/_audit.jsonl`）＋ `bridge.audit` logger。

    只記**決策**（拒絕了什麼、誰簽了核），絕不記 env 的值或含憑證的 URL。
    """

    def __init__(self, path: Path | None):
        self._path = path
        self._lock = threading.Lock()
        self._logger = logging.getLogger("bridge.audit")

    def record(self, event: str, **fields: Any) -> None:
        entry = {"ts": _now(), "event": event, **fields}
        self._logger.warning("audit %s", json.dumps(entry, ensure_ascii=False, default=str))
        if self._path is None:
            return
        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:        # 審計寫不下不得讓請求崩潰，但要在 logger 留下痕跡
            self._logger.error("audit 寫入失敗：%s", exc)


# ── SDD 寫入面權杖（ADR-XPLAT-016 §9；G-09）───────────────────────────────────────────────
SDD_WRITE_TOKEN_HEADER = "X-Bridge-Token"


def require_sdd_write_token(configured: str | None, provided: str | None, *,
                            audit: AuditLog | None, verb: str, project: str | None = None,
                            approver: str | None = None, run_id: str | None = None) -> None:
    """寫入動詞（`:freeze`、含 `sdd` 區塊的 `POST /autoclaude/runs`、其 `:resume`／`/restore`）的
    入口檢查。

    Bridge 沒設權杖＝整個寫入面停用，503 `sdd_write_disabled`（fail-closed）；設了而標頭缺漏或不符＝
    403 `sdd_write_forbidden`（缺與錯同一個 reason，不給探測者區分）。以 `hmac.compare_digest`
    比對（常數時間；兩邊先編成 UTF-8 bytes，非 ASCII 字元也不會拋例外）。
    被拒的請求也記稽核（決策、不含任何權杖值——包括被拒的那個值）。這個檢查必須先於一切會碰檔案系統的檢查。"""
    def reject(error: ApiError, result: str) -> ApiError:
        if audit is not None:
            which_run = {"run_id": run_id} if run_id else {}        # 續跑類才有：被拒的是哪個 run
            audit.record("sdd_write", verb=verb, project=project,
                         approver=(approver or "")[:100] or None, result=result,
                         trace_id=trace_id_var.get(), **which_run)
        return error

    if not configured:
        raise reject(ApiError(503, "sdd_write_disabled",
                              detail="Bridge 未設定 BRIDGE_SDD_WRITE_TOKEN：SDD 寫入面停用"),
                     "rejected:sdd_write_disabled")
    if provided is None or not hmac.compare_digest(provided.encode("utf-8"),
                                                   configured.encode("utf-8")):
        raise reject(ApiError(403, "sdd_write_forbidden"), "rejected:sdd_write_forbidden")


# ── SI 寫入面權杖（P2b W3；與 SDD 寫入面同一標頭、獨立權杖）──────────────────────────────────
# 注意：本檔含 `AuditLog` 的寫檔，不可出現 s-e-l-f-i-m-p-r-o-v-i-n-g 連寫字樣——
# tests/test_si_readonly_lock.py 的判準 1 把含該字樣的模組視為「SI 相關」，寫入形態呼叫只准出現在
# si_audit.py。
def require_si_write_token(configured: str | None, audit_dir: Path | None, provided: str | None, *,
                           audit: AuditLog | None, verb: str, subject: str | None = None) -> None:
    """SI 三個寫入端點（`:decide`、`POST /si/observations`、`:close`）的入口檢查，**先於**本文的
    任何檢查。

    寫入面停用（權杖或稽核目錄任一未設）＝503 `si_write_disabled`（fail-closed；先於權杖比對）；設了
    而標頭缺漏或不符＝403 `si_write_forbidden`（缺與錯同一個回應，不給探測者區分）。以
    `hmac.compare_digest` 比 bytes（常數時間；非 ASCII 字元也不會拋例外）。被拒的請求也記稽核
    （決策：verb、subject、結果、trace_id；不含任何權杖值，包括被拒的那個值）。
    `validate`（唯讀預檢）不呼叫本函式。"""
    def reject(error: ApiError, result: str) -> ApiError:
        if audit is not None:
            audit.record("si_write", verb=verb, subject=subject, result=result,
                         trace_id=trace_id_var.get())
        return error

    if not configured or audit_dir is None:
        raise reject(ApiError(503, "si_write_disabled",
                              detail="Bridge 未設定 BRIDGE_SI_WRITE_TOKEN 或 BRIDGE_SI_AUDIT_DIR："
                                     "SI 寫入面停用"),
                     "rejected:si_write_disabled")
    if provided is None or not hmac.compare_digest(provided.encode("utf-8"),
                                                   configured.encode("utf-8")):
        raise reject(ApiError(403, "si_write_forbidden"), "rejected:si_write_forbidden")


# ── 1. 路徑閘 ──────────────────────────────────────────────────────────────────
def is_within(child: Path, root: Path) -> bool:
    """`child` 是否位於 `root` 之下（含相等）。兩邊都先 resolve，再 normcase 後比對。

    Windows 行為＝normcase 把路徑轉小寫並統一分隔符（不分大小寫、有磁碟機代號）；
    POSIX 的 normcase 是恆等，區分大小寫。刻意用字串前綴＋分隔符而非 relative_to：
    不同磁碟機時 relative_to／commonpath 會拋例外，這裡要的是乾淨的 False。
    """
    c = os.path.normcase(str(child.resolve()))
    r = os.path.normcase(str(root.resolve())).rstrip("\\/")
    return c == r or c.startswith(r + os.sep)


def check_path(raw: Any, roots: Iterable[Path], *,
               field: str) -> tuple[Path | None, list[Violation]]:
    """回傳 (realpath, 違規清單)。違規非空時 realpath 為 None。"""
    def bad(rule: str, message: str) -> tuple[None, list[Violation]]:
        return None, [{"field": field, "rule": rule, "message": message}]

    if not isinstance(raw, str) or not raw.strip():
        return bad("empty", f"{field} 不可為空")
    if "\x00" in raw:
        return bad("invalid_chars", f"{field} 含 NUL 字元")
    if not os.path.isabs(raw):
        return bad("not_absolute", f"{field} 必須是絕對路徑：{raw}")
    path = Path(raw)
    if ".." in path.parts:
        return bad("contains_dotdot", f"{field} 不接受 `..` 片段：{raw}")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:     # RuntimeError＝symlink 迴圈（3.13 前的行為）
        return bad("not_found", f"{field} 不存在或無法解析：{raw}（{type(exc).__name__}）")
    if not resolved.is_dir():
        return bad("not_a_directory", f"{field} 不是目錄：{resolved}")
    if not any(is_within(resolved, root) for root in roots):
        return bad("outside_allowed_roots", f"{field} 不在允許的根目錄之下：{resolved}")
    return resolved, []


def check_spec_file(spec_dir: Path, raw: Any, *, field: str) -> tuple[Path | None, list[Violation]]:
    """`spec_file`（ADR-XPLAT-016 §7.3、§8.3）：相對 `spec_dir` 或絕對（須在 `spec_dir` 之下）、
    不含 `..`、副檔名 `.md`（不分大小寫）、是既有檔案。回傳 (realpath, 違規)。
    副檔名限制是縱深防禦：檔案內容會進 prompt 與摘要，不能讓路徑指到 `spec_dir` 內任意檔。
    規則碼：empty、invalid_chars、contains_dotdot、outside_spec_dir、not_markdown、not_found
    （呼叫端可把單一 `not_found` 轉成 `spec_not_found`）。`spec_dir` 須已是 realpath（`check_path`
    的輸出）。"""
    def bad(rule: str, message: str) -> tuple[None, list[Violation]]:
        return None, [{"field": field, "rule": rule, "message": message}]

    if not isinstance(raw, str) or not raw.strip():
        return bad("empty", f"{field} 不可為空")
    if "\x00" in raw:
        return bad("invalid_chars", f"{field} 含 NUL 字元")
    text = raw.replace("\\", "/")           # 檔案路徑一律以 POSIX 形傳遞；Windows 的反斜線形也接受
    if ".." in Path(text).parts:
        return bad("contains_dotdot", f"{field} 不接受 `..` 片段：{raw}")
    candidate = Path(text) if os.path.isabs(raw) or os.path.isabs(text) else spec_dir / text
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        return bad("not_found", f"{field} 無法解析：{raw}（{type(exc).__name__}）")
    if not is_within(resolved, spec_dir):
        return bad("outside_spec_dir", f"{field} 不在 spec_dir 之下：{raw}")
    if resolved.suffix.lower() != ".md":
        return bad("not_markdown", f"{field} 必須是 .md 檔：{raw}")
    if not resolved.is_file():
        return bad("not_found", f"{field} 不是既有檔案：{raw}")
    return resolved, []


# ── 2. 指令閘 ──────────────────────────────────────────────────────────────────
def forbidden_chars(text: str) -> list[str]:
    """`text` 內命中的禁止字元（去重、排序，換行以可讀形式回報）。"""
    hits = sorted(ch for ch in set(text) if ch in DENY_CHARS or ch in CONTROL_CHARS)
    return [{"\n": "\\n", "\r": "\\r", "\x00": "\\x00"}.get(ch, ch) for ch in hits]


def validate_playbook(playbook: Any) -> list[Violation]:
    """檢查 playbook 每個步驟：evaluator_command／command 的禁止字元、regex 能否編譯。"""
    out: list[Violation] = []
    for idx, task in enumerate(playbook.tasks):
        base = f"playbook.tasks[{idx}]"
        for attr in ("evaluator_command", "command"):
            text = getattr(task, attr, None)
            if not text:
                continue
            chars = forbidden_chars(text)
            if chars:
                out.append({
                    "field": f"{base}.{attr}", "step_id": task.step_id, "rule": "deny_chars",
                    "chars": chars,
                    "message": f"步驟 {task.step_id} 的 {attr} 含禁止字元 {' '.join(chars)}",
                })
        regex = getattr(task, "expected_output_regex", None)
        if regex:
            try:
                re.compile(regex)
            except re.error as exc:
                out.append({
                    "field": f"{base}.expected_output_regex", "step_id": task.step_id,
                    "rule": "invalid_regex", "message": f"不是合法 regex：{exc}",
                })
    return out


# ── 3. 外呼閘 ──────────────────────────────────────────────────────────────────
def check_outbound_url(url: Any, allowlist: Iterable[str]) -> tuple[bool, str, str]:
    """回傳 (放行?, host, 理由碼)。

    SSRF／畸形 URL 防線：兩個獨立的 URL 解析器（urllib 與 httpx——引擎實際用的是 httpx）必須對
    host 達成一致，否則拒絕（`http://allowed\\@evil` 這類 parser 差異是經典的白名單繞過）。
    userinfo、空白、控制字元、反斜線一律拒絕；host 只認**完全相等**（`localhost.evil.example`
    與 `localhost` 不同），尾端的 `.` 先剝掉。
    """
    if not isinstance(url, str) or not url.strip():
        return False, "", "empty_url"
    if any(ord(ch) <= 0x20 or ord(ch) == 0x7F for ch in url) or "\\" in url:
        return False, "", "malformed_url"
    try:
        parts = urlsplit(url)
        port = parts.port                       # 順便驗埠（非數字會拋 ValueError）
        httpx_host = httpx.URL(url).host
    except (ValueError, httpx.InvalidURL):
        return False, "", "malformed_url"
    del port
    if parts.scheme not in ("http", "https"):
        return False, parts.hostname or "", "scheme_not_allowed"
    if "@" in parts.netloc:
        return False, parts.hostname or "", "userinfo_not_allowed"
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or host != (httpx_host or "").lower().rstrip("."):
        return False, host, "parser_mismatch"
    if host not in {h.lower().rstrip(".") for h in allowlist}:
        return False, host, "host_not_allowed"
    return True, host, "ok"


def _check_url_field(url: Any, field: str, allowlist: Iterable[str],
                     audit: AuditLog | None, context: Mapping[str, Any]) -> list[Violation]:
    ok, host, reason = check_outbound_url(url, allowlist)
    if ok:
        return []
    if audit is not None:
        # 審計只記 host 與理由碼；原 URL 可能夾帶憑證，一律不寫。
        audit.record("outbound_denied", field=field, host=host, reason=reason, **context)
    return [{
        "field": field, "rule": "outbound_not_allowed", "host": host, "reason": reason,
        "message": f"{field} 的外呼目標不在白名單（host={host or '?'}，{reason}）",
    }]


# ── env／config_overrides ─────────────────────────────────────────────────────
def validate_env(env: Mapping[str, Any], allowlist: Iterable[str], *,
                 audit: AuditLog | None = None,
                 context: Mapping[str, Any] | None = None) -> list[Violation]:
    out: list[Violation] = []
    ctx = dict(context or {})
    for name, value in env.items():
        if not isinstance(name, str) or not _ENV_NAME_RE.match(name):
            out.append({"field": f"env.{name}", "rule": "invalid_name",
                        "message": "環境變數名稱只允許 [A-Za-z_][A-Za-z0-9_]*"})
            continue
        if name.upper() in _ENV_DENY:
            out.append({"field": f"env.{name}", "rule": "forbidden_name",
                        "message": f"{name} 會改變子行程的載入／解析路徑，不接受由請求設定"})
            continue
        if not isinstance(value, str) or "\x00" in value or len(value) > _ENV_VALUE_MAX:
            out.append({"field": f"env.{name}", "rule": "invalid_value",
                        "message": f"{name} 的值必須是不含 NUL、長度 ≤ {_ENV_VALUE_MAX} 的字串"})
            continue
        if name.upper() in _ENV_URL_KEYS and value:
            out.extend(_check_url_field(value, f"env.{name}", allowlist, audit, ctx))
    return out


def _walk_sections(model: type[BaseModel], data: Mapping[str, Any], path: str,
                   out: list[Violation]) -> None:
    """逐鍵比對 AppConfig 的欄位：引擎的 pydantic 預設 extra=ignore，打錯字會被靜默丟掉。"""
    fields = model.model_fields
    for key, value in data.items():
        where = f"{path}.{key}" if path else key
        if key not in fields:
            out.append({"field": f"config_overrides.{where}", "rule": "unknown_key",
                        "message": f"未知設定鍵 {where}（引擎會靜默忽略它）"})
            continue
        ann = fields[key].annotation
        if inspect.isclass(ann) and issubclass(ann, BaseModel):
            if not isinstance(value, Mapping):
                out.append({"field": f"config_overrides.{where}", "rule": "invalid_type",
                            "message": f"{where} 必須是物件"})
            else:
                _walk_sections(ann, value, where, out)


def ignored_managed_keys(overrides: Mapping[str, Any]) -> list[str]:
    """呼叫端帶了、但 Bridge 不會採用的設定鍵（供 CONFIG_OVERRIDE_IGNORED alert）。

    `storage` 只有在請求的內容與 Bridge 強制的 `{"mode": "yaml_only"}` 不同時才列出。"""
    out = sorted(k for k in overrides if k in MANAGED_KEYS and k != "storage")
    storage = overrides.get("storage")
    if isinstance(storage, Mapping) and dict(storage) not in ({}, {"mode": "yaml_only"}):
        out.append("storage")
    return out


def validate_config_overrides(overrides: Mapping[str, Any], allowlist: Iterable[str], *,
                              audit: AuditLog | None = None,
                              context: Mapping[str, Any] | None = None) -> list[Violation]:
    """結構／機密／外呼 URL／型別與不變式（halt > compact 等，交給引擎自己的模型驗）。
    管控鍵（見 MANAGED_KEYS）合法但會被忽略，不產生違規。"""
    from autoclaude.utils.config import AppConfig

    out: list[Violation] = []
    ctx = dict(context or {})
    for key in overrides:
        if key not in _OVERRIDE_SECTIONS and key not in MANAGED_KEYS:
            out.append({"field": f"config_overrides.{key}", "rule": "unknown_key",
                        "message": f"不支援的頂層設定鍵 {key}"})
    if out:
        return out
    _walk_sections(AppConfig, overrides, "", out)
    for section, key in _SECRET_KEYS:
        if isinstance(overrides.get(section), Mapping) and key in overrides[section]:
            out.append({"field": f"config_overrides.{section}.{key}", "rule": "secret_in_config",
                        "message": "機密不得放進 config_overrides（會落地成檔案），請改用 env"})
    for section, key in _URL_KEYS:
        sect = overrides.get(section)
        if isinstance(sect, Mapping) and sect.get(key):
            out.extend(_check_url_field(
                sect[key], f"config_overrides.{section}.{key}", allowlist, audit, ctx))
    tool = overrides.get("tool_invocation")
    if isinstance(tool, Mapping) and tool.get("enabled"):
        # 引擎的自主工具（web_search／http_request）只比對它自己的 allowlist；Bridge 要求其中
        # 每個「長得像 host」的項目也在外呼白名單內（不含 `.`／`:` 的視為通道名，不是 host）。
        for entry in tool.get("allowlist") or []:
            if isinstance(entry, str) and re.search(r"[.:/]", entry):
                probe = entry if "://" in entry else f"http://{entry}"
                out.extend(_check_url_field(
                    probe, "config_overrides.tool_invocation.allowlist", allowlist, audit, ctx))
    if out:
        return out
    effective = {k: v for k, v in overrides.items() if k not in MANAGED_KEYS}
    try:
        AppConfig.model_validate(effective)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            out.append({"field": f"config_overrides.{loc}", "rule": "invalid_value",
                        "message": err["msg"]})
    return out
