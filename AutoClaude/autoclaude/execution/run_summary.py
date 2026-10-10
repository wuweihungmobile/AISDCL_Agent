"""F-LRS-001：最近一次執行摘要（`python -m autoclaude --last-run-summary`）。

三塊職責，彼此獨立、都不碰引擎核心（core／plugins 零改動）：
  1. 落檔側：`RunSummaryRecorder` 由 `main()` 在 `service.run()` 前後各呼叫一次。兩階段——
     先寫 `status=running` 開始標記，結束時原子覆寫成 `finished`；崩潰、Ctrl+C、kill 時
     `finish` 沒機會執行，檔案停在 `running`，查詢端據此說「本次執行未正常結束」。
  2. 讀檔側：`load_summary`（schema v1 驗證）＋ `format_summary`（逐字版型）。
  3. CLI 入口：`show_last_run_summary`，唯讀、零副作用（不呼叫 setup_logger、不建目錄）。

設計全文與驗收準則：docs/01_requirements/FRD_Last_Run_Summary.md。
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..utils.config import load_config

if TYPE_CHECKING:
    from ..core.kernel_state import KernelResult

logger = logging.getLogger("autoclaude.execution.run_summary")

SCHEMA_VERSION = 1
SUMMARY_FILENAME = "last_run_summary.json"
REASON_MAX_CHARS = 500


class RunSummaryMissingError(Exception):
    """`last_run_summary.json` 不存在（尚未執行過 playbook，或 log_dir 指到別處）。"""


class RunSummaryCorruptError(Exception):
    """檔案存在但讀不了或不合格（損毀、編碼錯誤、schema 不符）；訊息為單行人話。"""


def summary_path(log_dir: str | os.PathLike[str]) -> Path:
    return Path(log_dir) / SUMMARY_FILENAME


def outcome_of(result: KernelResult) -> str:
    """判定順序固定 success → escalated → halted → failed（vetoed 等其餘一律歸 failed）。"""
    if result.success:
        return "success"
    if result.escalated:
        return "escalation"
    if result.halted:
        return "token_halt"
    return "failed"


def _one_line(value: object, limit: int = REASON_MAX_CHARS) -> str:
    """空白（含換行）折成單一空格；超過 `limit` 字以 `…` 收尾（含 `…` 在內不超過 `limit`）。"""
    text = " ".join(str("" if value is None else value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _iso(moment: datetime | str) -> str:
    """時刻 → aware UTC 的 ISO 字串（秒精度）；已是字串者原樣放行（測試可餵固定值）。"""
    if isinstance(moment, str):
        return moment
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def build_started_record(playbook: str, started_at: datetime | str) -> dict[str, Any]:
    """`running` 記錄：與 `finished` 共用同一組鍵，未知值為 None（`veto_reasons` 為空串列）。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "running",
        "playbook": playbook,
        "started_at": _iso(started_at),
        "finished_at": None,
        "duration_seconds": None,
        "outcome": None,
        "success": None,
        "escalated": None,
        "halted": None,
        "reason": None,
        "total_steps": None,
        "completed_steps": None,
        "halt_step_idx": None,
        "peak_token_pct": None,
        "scheduled_resume_at": None,
        "veto_reasons": [],
    }


def build_finished_record(
    started: dict[str, Any],
    result: KernelResult,
    finished_at: datetime | str,
    duration_seconds: float,
) -> dict[str, Any]:
    """在 `started` 之上填入 `KernelResult` 的結果欄位（不改動傳入的 `started`）。"""
    return {
        **started,
        "status": "finished",
        "finished_at": _iso(finished_at),
        "duration_seconds": round(float(duration_seconds), 1),
        "outcome": outcome_of(result),
        "success": bool(result.success),
        "escalated": bool(result.escalated),
        "halted": bool(result.halted),
        "reason": _one_line(result.reason),
        "total_steps": result.total_steps,
        "completed_steps": result.completed_steps,
        "halt_step_idx": result.halt_step_idx,
        "peak_token_pct": round(float(result.peak_token_pct), 2),
        "scheduled_resume_at": result.scheduled_resume_at,
        "veto_reasons": [str(item) for item in result.veto_reasons],
    }


def _discard(tmp: Path) -> None:
    with suppress(OSError):
        tmp.unlink(missing_ok=True)


def _write_atomic(path: Path, record: dict[str, Any]) -> None:
    """tmp → fsync → os.replace；任何例外（含 Ctrl+C）都先清掉 tmp 再原樣往外拋。

    吞不吞由呼叫端決定（recorder 只吞 Exception，Ctrl+C 這類 BaseException 照常往外傳）。
    tmp 檔名帶 pid＋uuid4：兩個行程同時寫同一個目的檔時不共用 tmp。UTF-8（LF 行尾）。
    """
    # 先過一次 utf-8 replace：reason／路徑可能夾帶 lone surrogate；缺這一步會在 tmp 已建立
    # 之後才炸 UnicodeEncodeError（不是 OSError），清不到 tmp、留下孤兒檔。
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    payload = payload.encode("utf-8", "replace").decode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        _discard(tmp)
        raise
    except BaseException:
        # Ctrl+C／SystemExit 落在 fsync 前後也不得留下孤兒 tmp，清完照樣往外傳。與上一支分開寫
        # 是刻意的：根層 TestDirEntryPrimitivesAreAccountedFor 以 AST 判「os.replace 站點是否被
        # 字面含 OSError／PermissionError 的 except 處置」，併成單一 BaseException 會多一筆欠債。
        _discard(tmp)
        raise


class RunSummaryRecorder:
    """兩階段落檔器：`start()` 寫 running 開始標記、`finish(result)` 原子覆寫成 finished。

    建構子不做 I/O。`start`／`finish` 都是 best-effort、不拋 Exception：本功能只是附屬便利，
    任何失敗（磁碟滿、權限、result 缺欄位的測試替身）都不得影響引擎流程與 rc；失敗時記
    WARNING（含 `last_run_summary` 與後果）並回 False。Ctrl+C 這類 BaseException 不吞、
    照常往外傳（tmp 已由 `_write_atomic` 清掉）。`now`／`monotonic` 為可注入時鐘。
    """

    def __init__(
        self,
        log_dir: str | os.PathLike[str],
        playbook: str,
        *,
        now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._path = summary_path(log_dir)
        self._playbook = os.path.abspath(playbook)    # 不解 symlink：與使用者輸入一致
        self._clock = now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic
        self._started: dict[str, Any] | None = None
        self._t0 = 0.0

    def start(self) -> bool:
        return self._persist("start", self._begin)

    def finish(self, result: KernelResult) -> bool:
        def build() -> dict[str, Any]:
            started = self._begin()
            return build_finished_record(
                started, result, self._clock(), self._monotonic() - self._t0)

        return self._persist("finish", build)

    def _begin(self) -> dict[str, Any]:
        """開始標記只建一次（`finish` 在 `start` 失敗或沒呼叫時也能補建，不會 AttributeError）。"""
        if self._started is None:
            self._t0 = self._monotonic()
            self._started = build_started_record(self._playbook, self._clock())
        return self._started

    def _persist(self, stage: str, build: Callable[[], dict[str, Any]]) -> bool:
        try:
            _write_atomic(self._path, build())
        except Exception as exc:
            logger.warning(
                "last_run_summary 寫入失敗（%s 階段，%s）：%s: %s；"
                "`--last-run-summary` 將顯示過期或缺少的紀錄",
                stage, self._path, type(exc).__name__, exc)
            return False
        logger.debug("last_run_summary 已寫入（%s 階段）：%s", stage, self._path)
        return True


# ──────────────────────────────────────────────────────────────────────────
# 讀檔側：schema v1 驗證
# ──────────────────────────────────────────────────────────────────────────
_OUTCOMES = ("success", "escalation", "token_halt", "failed")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_aware_iso(value: object) -> bool:
    """可被 `fromisoformat` 解析、且帶時區偏移的字串（naive 時刻無法表達寫入當下的 offset）。"""
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except ValueError:
        return False


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


_ISO_NEED = "帶時區偏移的 ISO 8601 字串"
# (欄位, 判準, 人話型別說明)；順序即問題字串的出現順序
_COMMON_FIELDS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("status", lambda v: v in ("running", "finished"), "running 或 finished"),
    ("playbook", lambda v: isinstance(v, str) and bool(v), "非空 str"),
    ("started_at", _is_aware_iso, _ISO_NEED),
)
_FINISHED_FIELDS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("finished_at", _is_aware_iso, _ISO_NEED),
    ("duration_seconds", lambda v: _is_number(v) and v >= 0, "非負數"),
    ("outcome", lambda v: v in _OUTCOMES, "／".join(_OUTCOMES) + " 之一"),
    ("success", lambda v: isinstance(v, bool), "bool"),
    ("escalated", lambda v: isinstance(v, bool), "bool"),
    ("halted", lambda v: isinstance(v, bool), "bool"),
    ("reason", lambda v: v is None or isinstance(v, str), "str 或 null"),
    ("total_steps", lambda v: _is_int(v) and v >= 0, "非負 int"),
    ("completed_steps", lambda v: _is_int(v) and v >= 0, "非負 int"),
    ("halt_step_idx", lambda v: v is None or _is_int(v), "int 或 null"),
    ("peak_token_pct", lambda v: _is_number(v) and v >= 0, "非負數"),
    ("scheduled_resume_at", lambda v: v is None or isinstance(v, str), "str 或 null"),
    ("veto_reasons", _is_str_list, "list[str]"),
)


def _field_problems(
    data: dict[str, Any], fields: tuple[tuple[str, Callable[[Any], bool], str], ...],
) -> list[str]:
    problems: list[str] = []
    for name, is_valid, expected in fields:
        if name not in data:
            problems.append(f"缺少必要欄位：{name}")
        elif not is_valid(data[name]):
            problems.append(f"欄位型別錯誤：{name} 需為 {expected}")
    return problems


def summary_problems(data: object) -> list[str]:
    """schema v1 驗證（純函式）：空清單＝有效。多餘的未知鍵一律忽略（向前相容）。

    `schema_version` 先判且不符即短路：版本不同代表其餘欄位的語意可能不同，繼續逐欄檢查
    只會印出一串誤導的型別錯誤。
    """
    if not isinstance(data, dict):
        return [f"根節點必須是物件（實際為 {type(data).__name__}）"]
    if "schema_version" not in data:
        return ["缺少必要欄位：schema_version"]
    version = data["schema_version"]
    if not _is_int(version):
        return ["欄位型別錯誤：schema_version 需為 int"]
    if version != SCHEMA_VERSION:
        return [f"schema_version={version} 不受支援（本版只認 {SCHEMA_VERSION}）"]
    problems = _field_problems(data, _COMMON_FIELDS)
    if data.get("status") == "finished":
        problems += _field_problems(data, _FINISHED_FIELDS)
    return problems


def load_summary(path: str | os.PathLike[str]) -> dict[str, Any]:
    """讀並驗證記錄檔。不存在 ⇒ `RunSummaryMissingError`；其餘一切讀不了或不合格 ⇒
    `RunSummaryCorruptError`（訊息為單行人話，絕不讓 traceback 外洩給使用者）。"""
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8")      # 一次讀完即關：縮短與寫端換名的握把重疊
    except FileNotFoundError as exc:
        raise RunSummaryMissingError(str(target)) from exc
    except OSError as exc:
        raise RunSummaryCorruptError(f"無法讀取檔案：{_one_line(exc)}") from exc
    except UnicodeDecodeError as exc:
        raise RunSummaryCorruptError(f"檔案不是有效的 UTF-8：{_one_line(exc)}") from exc
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        # JSONDecodeError 是 ValueError 的子類；另有兩種解析失敗不是 JSONDecodeError：超長整數
        # （Exceeds the limit (4300 digits)）拋純 ValueError、極深巢狀拋 RecursionError。
        raise RunSummaryCorruptError(f"JSON 解析失敗：{_one_line(exc)}") from exc
    problems = summary_problems(data)
    if problems:
        raise RunSummaryCorruptError("；".join(problems))
    return data


# ──────────────────────────────────────────────────────────────────────────
# 讀檔側：版型（逐字契約見 FRD §2.2／§2.6；各行以單一換行分隔，尾端換行由 print 補）
# ──────────────────────────────────────────────────────────────────────────
_LOG_FILENAME = "autoclaude.log"
_HALT_NOTES = {
    "halted": "context 用量達 halt 門檻，已存檢查點",
    "external_resume_required": "等待時間超過行程內上限，需於可續跑時刻後由外部重啟",
    "interrupted_during_wait": "等待期間被中斷",
}
_PEAK_NOT_CARRIED = "未記錄（此結果型態不攜帶 token 峰值）"
_PEAK_NOT_OBSERVED = "未觀測（本次無 token 訊號）"


def _shown_time(value: str, tz: tzinfo | None) -> str:
    """ISO 字串 → 目標時區的 `YYYY-MM-DD HH:MM:SS+HH:MM`；解析不了就原樣顯示（不拋）。

    `tz=None` ＝ 本機時區；naive 字串（舊 checkpoint 形態）依 Python 慣例視為本機時間。
    """
    try:
        return datetime.fromisoformat(value).astimezone(tz).isoformat(sep=" ", timespec="seconds")
    except (ValueError, OverflowError):
        return value


def _result_line(record: dict[str, Any]) -> str:
    outcome = record["outcome"]
    reason = record.get("reason") or ""
    if outcome == "success":
        return "成功（SUCCESS）"
    if outcome == "escalation":
        return f"失敗（ESCALATION）；原因：{reason}"
    if outcome == "token_halt":
        text = f"暫停（TOKEN_HALT）；{_HALT_NOTES.get(reason, reason)}"
        idx = record.get("halt_step_idx")
        return text if idx is None else f"{text}；停在第 {idx + 1} 步"
    text = f"失敗（FAILED）；原因：{reason}"
    vetoes = record.get("veto_reasons") or []
    return f"{text}；否決原因：{'；'.join(vetoes)}" if vetoes else text


def _peak_line(record: dict[str, Any]) -> str:
    peak = record["peak_token_pct"]
    if peak > 0:
        return f"{peak:.1f}%"
    if record["outcome"] in ("escalation", "failed"):
        return _PEAK_NOT_CARRIED
    return _PEAK_NOT_OBSERVED


def format_summary(
    record: dict[str, Any], *, tz: tzinfo | None = None, log_dir: str = "logs",
) -> str:
    """把（已通過 `summary_problems`）的記錄排成人話；`tz` 供測試固定時區。"""
    started = _shown_time(record["started_at"], tz)
    lines = ["最近一次執行摘要", f"Playbook：{record['playbook']}"]
    if record["status"] == "running":
        lines += [
            f"開始時間：{started}",
            "結果：未完成（本次執行未正常結束）；可能仍在執行、被中斷（Ctrl+C／kill），"
            f"或行程崩潰；詳見 {os.path.join(log_dir, _LOG_FILENAME)}",
        ]
        return "\n".join(lines)
    completed, total = record["completed_steps"], record["total_steps"]
    resumed = record["outcome"] == "success" and 0 <= completed < total
    note = f"（本次為續跑：其餘 {total - completed} 步已於先前執行完成）" if resumed else ""
    lines += [
        f"開始時間：{started}（耗時 {record['duration_seconds']:.1f} 秒）",
        f"結果：{_result_line(record)}",
        f"步驟：通過 {completed} / 共 {total} 步{note}",
        f"token 峰值：{_peak_line(record)}",
        f"ESCALATION：{'是' if record['escalated'] else '否'}",
    ]
    if record["outcome"] == "token_halt" and record.get("scheduled_resume_at"):
        lines.append(f"可續跑時刻：{_shown_time(record['scheduled_resume_at'], tz)}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# CLI 入口（唯讀）
# ──────────────────────────────────────────────────────────────────────────
def _fail(message: str) -> int:
    print(f"錯誤：{message}", file=sys.stderr)
    return 1


def _escape_unencodable(stream: object) -> None:
    """讓 `stream` 遇到編不出的字元時降級成 `\\uXXXX` 跳脫字面，而不是 UnicodeEncodeError。

    Windows 重導向時預設 code page 可能編不出中文。刻意只改 errors、不強制 encoding：強制 UTF-8
    是另一件事（會改變下游讀者看到的位元組），其唯一實作住在 monorepo 根層 tools/，而
    importlinter 第 9 條禁止套件 import 它。沒有 `reconfigure` 的串流（StringIO 等）或已關閉的
    串流一律略過。
    """
    with suppress(AttributeError, OSError, ValueError):
        stream.reconfigure(errors="backslashreplace")    # type: ignore[attr-defined]


def show_last_run_summary(config_path: str) -> int:
    """`--last-run-summary`：印出最近一次執行摘要。rc：0＝有記錄（含 running）；1＝其餘。

    唯讀、零副作用：不呼叫 `setup_logger`、不建任何目錄或檔案（`load_config` 對不存在的
    檔案回預設值，故 `--config` 指到不存在的檔等同用預設 `log_dir`）。
    """
    _escape_unencodable(sys.stdout)
    try:
        cfg = load_config(config_path)
    except Exception as exc:        # YAMLError／ValidationError／OSError／UnicodeDecodeError…
        return _fail(f"設定檔讀取失敗：{config_path}（{type(exc).__name__}：{_one_line(exc)}）")
    path = summary_path(cfg.log_dir)
    shown = os.path.abspath(path)
    try:
        record = load_summary(path)
    except RunSummaryMissingError:
        return _fail(f"尚無執行紀錄：找不到 {shown}"
                     "（請先執行過一次 playbook；紀錄位置由 --config 的 log_dir 決定）")
    except RunSummaryCorruptError as exc:
        return _fail(f"最近一次執行紀錄損毀或無法讀取：{shown}（{exc}）。"
                     "可刪除該檔，下次執行 playbook 會重建。")
    print(format_summary(record, log_dir=cfg.log_dir))
    return 0
