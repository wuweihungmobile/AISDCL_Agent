"""FSM-STATE-{project}.yaml 讀寫器。

Source of truth: tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml
（DEF-15-001 深層：FSM 種子模板＝真輸入，移出 runtime 輸出目錄 build/reports/fsm/
至 tracked 源碼位，與 loader 同層；runtime 狀態檔輸出仍在 build/reports/fsm/。）
"""
from __future__ import annotations

import copy
import datetime as _dt
import importlib.util as _importlib_util
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip install pyyaml"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[2]
# DEF-15-001 深層：種子模板（真輸入）移至與 loader 同層的 tracked 源碼位，與 runtime
# 狀態檔輸出目錄（DEFAULT_STATE_DIR=build/reports/fsm）分離，杜絕「輸入寄居輸出目錄」
# 結構異味（免 copy_on_evolve 特例 + .gitignore negate idiom）。
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "FSM-STATE-TEMPLATE.yaml"
DEFAULT_STATE_DIR = REPO_ROOT / "build" / "reports" / "fsm"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")



# R45 架構最佳化（DEF-101-358）：本函式改為薄委派 AISDLC_SDD/scripts/
# component_sanitizer.py 這個跨版本共用 SSOT（importlib 依絕對路徑載入，不
# 污染 sys.path），不再是 LATEST 獨有的一份實作。29 個凍結版本（v0.01~v0.29）
# 原本各自留著只擋路徑分隔符的弱化版，現在也改為委派同一份共用原始碼，往後同類淨化
# 強化只需改共用模組一處、30 個版本立即同步生效，不必再逐版例外補丁（沿革見
# component_sanitizer.py 模組 docstring 與
# docs/06_quality/AutoSDD_Defect_Log.md::DEF-101-358）。
#
# 覆蓋強度比照 AutoClaude 側 autoclaude/utils/logger.py::_sanitize_log_filename()
# （交叉一致性見根層 tools/tests/test_windows_forbidden_filename_parity.py::
# TestSddSanitizeComponentVsLoggerSecurityParity：比較「危險輸入是否被同等程度
# 擋下」，不要求輸出完全一致。R69 自本目錄的 test_state_component_sanitizer_
# parity.py 搬遷至根層整合層——原檔在 AISDLC_SDD 側 import autoclaude，CI 相依
# 缺 pydantic 時被 try/except 收成「8 支永遠 skip」）。AISDLC_SDD 與 AutoClaude 是兩個獨立
# 可發布子專案（各自 releases/ 打包發布機制），依既有先例（
# bootstrap_core.py::_is_windows_apps_stub() 語言邊界獨立實作）不可跨子專案
# import，故本模組獨立實作、不與 logger.py 共用同一顆函式物件。
_SHARED_COMPONENT_SANITIZER_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "component_sanitizer.py"
)


def _load_shared_component_sanitizer():
    spec = _importlib_util.spec_from_file_location(
        "_aisdlc_sdd_shared_component_sanitizer", _SHARED_COMPONENT_SANITIZER_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"無法載入共用淨化模組：{_SHARED_COMPONENT_SANITIZER_PATH}")
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_shared_component_sanitizer = _load_shared_component_sanitizer()
_sanitize_component = _shared_component_sanitizer.sanitize_component
_MAX_COMPONENT_LEN = _shared_component_sanitizer._MAX_COMPONENT_LEN


def _default_state_path(project: str) -> Path:
    return DEFAULT_STATE_DIR / f"FSM-STATE-{_sanitize_component(project)}.yaml"


# Phase I M5 / ACT-070：艦隊並行的 track 維度 state key。
# 單軌時 track_id=None → FSM-STATE-{project}.yaml（向後相容）；
# 多 feature 並行時每軌獨立 FSM-STATE-{project}-{track_id}.yaml，互不污染。
def track_state_path(project: str, track_id: Optional[str] = None) -> Path:
    if not track_id:
        return _default_state_path(project)
    safe = _sanitize_component(track_id)
    return DEFAULT_STATE_DIR / f"FSM-STATE-{_sanitize_component(project)}-{safe}.yaml"


def load_track_state(
    project: str,
    track_id: Optional[str] = None,
    *,
    create_if_missing: bool = True,
) -> "FSMState":
    """載入指定 track 的 FSM 狀態（ACT-070）。track_id=None 等同單軌 load_state。"""
    return load_state(project, path=track_state_path(project, track_id),
                      create_if_missing=create_if_missing)


class FSMState:
    """Thin wrapper over the FSM state YAML document."""

    def __init__(self, doc: Dict[str, Any], path: Path):
        self._doc = doc
        self.path = path

    # ---------- convenience accessors ----------
    @property
    def root(self) -> Dict[str, Any]:
        return self._doc.setdefault("fsm_state", {})

    @property
    def current(self) -> str:
        return self.root.get("current_state", "INIT")

    @current.setter
    def current(self, value: str) -> None:
        self.root["current_state"] = value
        self.root["updated_at"] = _now()

    def retry(self, gate: str) -> Dict[str, Any]:
        return self.root.setdefault("retry_history", {}).setdefault(gate, {})

    def cumulative(self) -> Dict[str, Any]:
        return self.root.setdefault("cumulative_history", {})

    def implementation_budget(self) -> Dict[str, Any]:
        return self.root.setdefault("implementation_budget", {})

    # Phase E / ACT-025：Decision Trace accessor
    def decision_trace(self) -> list:
        return self.root.setdefault("decision_trace", [])

    def append_decision_trace(
        self,
        *,
        from_state: str,
        to_state: str,
        reason: str = "",
        spec_refs: Optional[list] = None,
        agents_consulted: Optional[list] = None,
        trigger: str = "transition",
        max_keep: int = 50,
    ) -> Dict[str, Any]:
        """Append one decision trace entry; keep the latest max_keep (default 50).

        Older entries are flushed to cold tier via move-into 'decision_trace_flushed'
        so the active list remains bounded without losing history.
        """
        trace = self.decision_trace()
        entry: Dict[str, Any] = {
            "ts": _now(),
            "from": from_state,
            "to": to_state,
            "reason": reason or f"auto transition {from_state}->{to_state}",
            "spec_refs": spec_refs or [],
            "agents_consulted": agents_consulted or [],
            "trigger": trigger,
        }
        trace.append(entry)
        if len(trace) > max_keep:
            flushed = self.root.setdefault("decision_trace_flushed", [])
            overflow = len(trace) - max_keep
            flushed.extend(trace[:overflow])
            self.root["decision_trace"] = trace[overflow:]
        self.root["updated_at"] = _now()
        return entry

    # ---------- mutations ----------
    def increment_retry(self, gate: str, failure_reason: str, scg_gate: Optional[str] = None) -> int:
        # ACT-029 P1-01: tamper defence.
        # Attackers (or corrupted state) may set `current_count` to a negative
        # number to earn free retries, or to an absurdly large number to skip
        # retries entirely. Defend both ends:
        #   1. `max(0, prior)` floors negative values at zero so they cannot
        #      silently buy back retries.
        #   2. If the prior value is outside the legal band [0, limit), snap
        #      the new count directly to `limit` so the very next gate check
        #      escalates — it is safer to stop once than to over-retry.
        #   3. Record the tamper detection in history.failure_reason for
        #      audit so reviewers can see the original poisoned value.
        from .transition_rules import RETRY_LIMITS  # local to avoid cycles
        entry = self.retry(gate)
        prior_raw = entry.get("current_count", 0)
        try:
            prior = int(prior_raw)
        except (TypeError, ValueError):
            prior = 0
        limit = RETRY_LIMITS.get(gate)
        tamper = False
        tamper_note = ""
        if prior < 0:
            tamper = True
            tamper_note = f"(tamper detected: prior_count={prior_raw}, floored to 0)"
            sanitized = 0
        elif limit is not None and prior >= limit:
            tamper = True
            tamper_note = f"(tamper detected: prior_count={prior_raw} ≥ limit={limit})"
            sanitized = prior  # keep as-is; current will be snapped to limit below
        else:
            sanitized = prior
        current = sanitized + 1
        # When tamper detected and we know the gate's limit, snap to limit so
        # the very next escalation check triggers regardless of the poisoned
        # starting value.
        if tamper and limit is not None:
            current = limit
        entry["current_count"] = current
        history = entry.setdefault("history", []) or []
        recorded_reason = failure_reason
        if tamper_note:
            recorded_reason = f"{failure_reason} {tamper_note}".strip()
        history.append(
            {
                "attempt": current,
                "date": _now(),
                "failure_reason": recorded_reason,
                "scg_gate": scg_gate,
            }
        )
        entry["history"] = history
        cum = self.cumulative()
        if gate == "SCG_VALIDATION":
            cum["total_scg_retries_all_time"] = int(cum.get("total_scg_retries_all_time", 0)) + 1
        elif gate == "PR_REVIEW":
            cum["total_pr_review_retries"] = int(cum.get("total_pr_review_retries", 0)) + 1
        self.root["updated_at"] = _now()
        return current

    def reset_retry(self, gate: str) -> None:
        entry = self.retry(gate)
        entry["current_count"] = 0
        entry.setdefault("history", [])

    def record_spec_frozen(self, stage: str, spec_docs: list[str], compaction_report: Optional[str] = None) -> None:
        stages = self.root.setdefault("frozen_stages", []) or []
        stages.append(
            {
                "stage": stage,
                "frozen_at": _now(),
                "compaction_report": compaction_report,
                "spec_docs": spec_docs,
            }
        )
        self.root["frozen_stages"] = stages
        cum = self.cumulative()
        cum["total_spec_frozen_count"] = int(cum.get("total_spec_frozen_count", 0)) + 1
        # Reset current_count for every gate but keep cumulative_history.
        for gate_name in ("SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY"):
            self.reset_retry(gate_name)

    def record_escalation(self, reason: str, *, details: Optional[Dict[str, Any]] = None,
                          rule_id: Optional[str] = None, source: Optional[str] = None) -> None:
        # DEF-200-275 第四輪（D6b）：`details` 讓 escalation 紀錄帶上來源 session_id／used／window／
        # window_source／compact_boundaries，供 recovery_hint 印出「這個 ESCALATION 來自哪個 session、
        # 是 context budget 還是結構性」。None 時鍵集合與此前逐字相同（96 個既有呼叫端零改動）；
        # 既有四鍵在前且不被 details 覆寫。
        #
        # D17（DEF-200-275 第六輪／DEF-200-283）：F-ARCH-01／QA-C1 指出——任一原因（不只 context
        # budget）寫入的 project-level ESCALATION，都會讓全新視窗第一次工具呼叫被無條件擋下，且
        # 訊息答不出「這是不是我這個 session 觸發的」。
        #
        # 🔴 ARCH-R6-01 訂正（同輪複審抓到；訂正協議：不靜默覆寫，原文與此區隔）：本函式此前
        # 自稱是 fsm_runtime.py 全部生產落點「唯一」寫入 current="ESCALATION" 的地方，但當時
        # exit_learning_commit（兩分支）／exit_trajectory_predicted 的 abort_early／
        # record_dispatch_rejection／exit_autoclaude_delegated 的 failed 這 4 個函式仍直接呼叫
        # self.transition("ESCALATION", ...) 繞過本函式，完全不落 escalation_provenance／
        # escalation_history，使 recovery_hint() 誤印前一次（可能已解決）事件的舊溯源。本輪已把
        # 這 4 處全部改為先呼叫本函式。現在 fsm_runtime.py 全部生產落點——R-9.1／R-9.2(*)／R-9.3／
        # R-9.7／R-9.15.2／R-9.19.3／R-9.21／R-9.22／R-9.24.1／R-9.24.2／R-SELF-STRIDE／
        # implementation-budget／spec_patch-no-draft／learning-review-rejected／
        # autoclaude-delegated-failed——都在轉態前呼叫本函式（(*) R-9.2 的 cap_exceeded 是唯一
        # 例外：那條路徑刻意不呼叫本函式、也不轉態，見 trigger_auto_compact 附近註解，D13）。
        # 呼叫端多半會在本函式之後**再呼叫一次** self.transition("ESCALATION", ...) 完成
        # decision_trace／save_state／規則遙測——那次重覆寫 current 是 no-op（本函式已寫過），
        # 但會讓 decision_trace 該筆的 from_state 顯示 "ESCALATION"（本函式已改寫 current）而非
        # 轉態前的真實來源狀態；這是 sandbox_hardening／spec_patch_proposal 等既有落點就有的既有
        # 行為（非本輪引入的新缺陷），recovery_hint() 不依賴 decision_trace.from 判斷觸發者，故
        # 不受影響。ESCALATION_FINAL 一律從已在 ESCALATION 的狀態經 transition() 轉出，天然繼承
        # 這裡寫的 provenance，不需要另一個落點。
        # 落一份「最新快照」到 self.root["escalation_provenance"]，供 recovery_hint() 回答上述問題。
        # session_id／rule_id／source 三者任一缺席一律老實寫 "unknown"（不臆測），rule_id 沿用呼叫端
        # 已算好的 R-9.x 編號（與 `_record_escalation_catches` 同一份字面值，不重新推導）；
        # 兩個新關鍵字參數皆 optional，96 個既有呼叫端（含 chaos_runner／tests）零改動。
        history = self.root.setdefault("escalation_history", []) or []
        entry: Dict[str, Any] = {
            "triggered_at": _now(),
            "trigger_reason": reason,
            "resolved_at": None,
            "resolution": None,
        }
        if details is not None:
            entry.update({k: v for k, v in dict(details).items() if k not in entry})
        history.append(entry)
        self.root["escalation_history"] = history
        cum = self.cumulative()
        cum["escalation_count"] = int(cum.get("escalation_count", 0)) + 1
        self.current = "ESCALATION"
        prov_session_id = details.get("session_id") if details is not None else None
        self.root["escalation_provenance"] = {
            "session_id": prov_session_id or "unknown",
            "at": entry["triggered_at"],
            "reason": reason,
            "rule_id": rule_id or "unknown",
            "source": source or "unknown",
        }

    # QA Round-3 P2-02: `add_pending_ci_event` / `remove_pending_ci_event` were
    # unused (event_reconciler relies on `ci_event_seen_hashes`, not the pending
    # list). The `ci_events_pending` field is retained in state because snapshot
    # renders it, but the mutators were dead code and have been removed.

    # ---------- serialization ----------
    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._doc)


def _load_template() -> Dict[str, Any]:
    with TEMPLATE_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _classify_state_file(path: Path) -> tuple[Optional[Dict[str, Any]], str]:
    """Parse a state file and return (doc_or_none, reason_code).

    P2-03: reason codes let load_state build a specific ValueError instead
    of a generic "unreadable" message, so operators can tell parse errors
    apart from schema mismatches.

    Reason codes:
        ok            — parsed into a valid FSMState doc
        read_error    — IOError / permission / decoding failure
        yaml_error    — YAML syntax / parse failure
        non_dict      — parsed to something other than a mapping
        missing_root  — dict but no top-level ``fsm_state`` key (or not dict)
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except (UnicodeDecodeError, OSError):
        return None, "read_error"
    except yaml.YAMLError:
        return None, "yaml_error"
    if not isinstance(doc, dict):
        return None, "non_dict"
    if "fsm_state" not in doc or not isinstance(doc.get("fsm_state"), dict):
        return None, "missing_root"
    return doc, "ok"


def _try_parse_state_file(path: Path) -> Optional[Dict[str, Any]]:
    """Backwards-compatible shim: return the parsed doc or None."""
    doc, _reason = _classify_state_file(path)
    return doc


def load_state(project: str, path: Optional[Path] = None, create_if_missing: bool = True) -> FSMState:
    """Load an FSM state document; initialize from template when missing.

    ACT-029 chaos recovery: if the primary YAML is corrupted (parse error /
    non-dict / missing `fsm_state`), fall back to the sibling `.bak` snapshot
    written by :func:`save_state`. The recovered document is copied back over
    the primary so subsequent reads are consistent.
    """
    target = path or _default_state_path(project)
    if target.exists():
        primary_doc, primary_reason = _classify_state_file(target)
        if primary_doc is not None:
            return FSMState(primary_doc, target)
        bak = target.with_suffix(target.suffix + ".bak")
        bak_reason = "absent"
        if bak.exists():
            bak_doc, bak_reason = _classify_state_file(bak)
            if bak_doc is not None:
                shutil.copy2(bak, target)
                return FSMState(bak_doc, target)
        # P2-03: Primary unparseable and no usable backup — surface both
        # failure reasons so operators triaging RESUME_VERIFICATION can
        # tell "corrupt YAML" from "schema drift" at a glance.
        raise ValueError(
            f"FSM-STATE unreadable and no usable .bak (primary={primary_reason}, "
            f"bak={bak_reason}): {target}"
        )
    if not create_if_missing:
        raise FileNotFoundError(f"FSM-STATE file not found: {target}")
    doc = _load_template()
    root = doc.setdefault("fsm_state", {})
    root["project"] = project
    root["session_id"] = str(uuid.uuid4())
    now = _now()
    root["created_at"] = now
    root["updated_at"] = now
    root["current_state"] = "INIT"
    target.parent.mkdir(parents=True, exist_ok=True)
    state = FSMState(doc, target)
    save_state(state)
    return state


def save_state(state: FSMState) -> None:
    """Atomically persist state to disk (backup the previous file).

    P2-02: the `.bak` rotation is now atomic too. We copy the existing
    primary to `{suffix}.bak.tmp` and then `os.replace` it into `.bak`, so
    a crash between copy and replace leaves the previous `.bak` intact
    rather than a half-written file. Without this, a mid-copy crash could
    corrupt `.bak` and defeat the ACT-029 chaos recovery path.

    QA Round-3 P2-08: reap any stale `.bak.tmp` / `.tmp` left by a prior
    interrupted save before starting a new one. Without this, repeated
    crashes during `shutil.copy2` could leak tmp files on disk-full
    volumes; the next `save_state` call now always starts clean.
    """
    target = state.path
    target.parent.mkdir(parents=True, exist_ok=True)
    bak_tmp = target.with_suffix(target.suffix + ".bak.tmp")
    tmp = target.with_suffix(target.suffix + ".tmp")
    # Reap leftovers from a crashed prior save (QA Round-3 P2-08).
    for stale in (bak_tmp, tmp):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass
    if target.exists():
        bak = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, bak_tmp)
        os.replace(bak_tmp, bak)
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(state.to_dict(), f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, target)


def project_from_env(default: str = "default") -> str:
    """Resolve project name from env; fall back to repo folder name."""
    override = os.environ.get("SDD_PROJECT")
    if override:
        return override
    return REPO_ROOT.parent.name or default
