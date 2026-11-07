"""自癒監視器（ResearchToPRD P2；TCS AC-962-6、7、8；IFACE §3）。

資料流：引擎的 `execution_steps`（RETRYING／FAILED）→ 唯讀視圖 `v_research_healing_attempts` →
本模組導出 R10 欄位並追加到工作區的 `03_execution/healing_history.log`（JSON Lines；衍生檔，不是任何
流程的輸入）。三件事、都不寫 FSM、不起子行程：

  · `mask`／`excerpt`：研究面**恆遮蔽**（疊用 `autoclaude.utils.redaction.redact_secrets` 與
    `gitops.redact`；不讀任何環境開關），先遮蔽再截尾（避免留下半截 token）；
  · `sync`：視圖列 → log 行，key＝`(run_id, step_number)`，只追加缺的（冪等）、單檔
    `HEALING_LOG_MAX_BYTES` 為上限（越界寫一次截斷行並告警）、持專案鎖序列化；
  · `detect_spec_change`：對「已凍結規格文件」逐檔重算 sha256（唯讀）。偵測只記錄與告警；
    本模組**不還原檔案、不呼叫任何破壞性版控動作**，也不聲稱補丁被拒絕——「被拒」屬框架 hooks。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoclaude.utils.redaction import redact_secrets

from .. import fsutil
from ..errors import ApiError
from . import gitops, layout
from .db import ResearchDb
from .outbox import DurableWriter, Op

HEALING_LOG_REL = "03_execution/healing_history.log"
#: 單檔上限（位元組）；測試以 monkeypatch 縮小，另有一個測試釘正式值。
HEALING_LOG_MAX_BYTES = 2_097_152
EXCERPT_CHARS = 300
LOG_KEYS = ("run_id", "task_id", "step_number", "attempt", "status", "excerpt", "occurred_at")
_TRUNCATED_LINE = '{"truncated":true}'
ALERT_SPEC_CHANGE = "SPEC_CHANGE_FORBIDDEN"
ALERT_LOG_TRUNCATED = "HEALING_LOG_TRUNCATED"
MISSING = "missing"


# ── 遮蔽與截尾 ─────────────────────────────────────────────────────────────────────────────
def mask(text: str) -> str:
    """兩套規則疊用（`redact_secrets` 先、`gitops.redact` 後）；空值與非字串原樣處理為字串。"""
    if not text:
        return ""
    return gitops.redact(redact_secrets(str(text)))


def excerpt(text: str | None) -> str:
    """遮蔽後取尾端 300 **字元**（不是位元組；多位元組字元不會被切半）。"""
    masked = mask(text or "")
    return masked if len(masked) <= EXCERPT_CHARS else masked[-EXCERPT_CHARS:]


# ── 視圖列 → R10 欄位 ──────────────────────────────────────────────────────────────────────
def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def derive_entries(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """`attempt`＝同 `(run_id, task_id)` 內依 `step_number` 升冪的第 n 筆（跨 run 不累加）。回傳依
    `(run_number, step_number)` 排序的 log 條目（鍵見 `LOG_KEYS`；excerpt 已遮蔽截尾）。"""
    ordered = sorted(rows, key=lambda r: (int(r.get("run_number") or 0), int(r["step_number"]),
                                          str(r.get("run_id"))))
    counters: dict[tuple[str, str], int] = {}
    out: list[dict[str, Any]] = []
    for r in ordered:
        slot = (str(r["run_id"]), str(r["task_id"]))
        counters[slot] = counters.get(slot, 0) + 1
        out.append({"run_id": str(r["run_id"]), "task_id": str(r["task_id"]),
                    "step_number": int(r["step_number"]), "attempt": counters[slot],
                    "status": str(r["status"]), "excerpt": excerpt(r.get("error_message")),
                    "occurred_at": _iso(r["occurred_at"])})
    return out


def _line(obj: Mapping[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ── 規格漂移偵測 ───────────────────────────────────────────────────────────────────────────
def union_digests(frozen_stages: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """各已凍結階段 `spec_doc_digests` 的聯集（重疊路徑只留一筆；後凍結者覆蓋先凍結者）。"""
    merged: dict[str, str] = {}
    for stage in frozen_stages:
        digests = stage.get("spec_doc_digests") if isinstance(stage, Mapping) else None
        for rel, value in (digests or {}).items():
            merged[str(rel)] = str(value).removeprefix("sha256:")
    return merged


def detect_spec_change(frozen_digests: Mapping[str, str], root: Path) -> list[dict[str, str]]:
    """逐檔重算 sha256（唯讀）；不符或檔案缺席（`missing`）都是漂移，不拋例外。路徑依字母序。"""
    drift: list[dict[str, str]] = []
    for rel in sorted(frozen_digests):
        expected = str(frozen_digests[rel]).removeprefix("sha256:")
        try:
            target = layout.safe_join(root, rel)
            actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() \
                else MISSING
        except (OSError, ApiError):
            actual = MISSING
        if actual != expected:
            drift.append({"path": rel, "expected": expected, "actual": actual})
    return drift


def _signature(drift: Sequence[Mapping[str, str]]) -> str:
    return hashlib.sha256(_line([[d["path"], d["expected"], d["actual"]] for d in drift]).encode(
        "utf-8")).hexdigest()


def drift_line(drift: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    return {"spec_change": True, "paths": [d["path"] for d in drift],
            "expected": {d["path"]: d["expected"] for d in drift},
            "actual": {d["path"]: d["actual"] for d in drift}}


# ── 同步 ───────────────────────────────────────────────────────────────────────────────────
@dataclass
class HealingEnv:
    db: ResearchDb
    writer: DurableWriter


def _scan_log(text: str) -> tuple[set[tuple[str, int]], bool, set[str], int]:
    """既有 log 的 `(已有 key, 是否已有截斷行, 已告警的漂移簽章, 條目行數)`。壞行略過。"""
    keys: set[tuple[str, int]] = set()
    truncated, signatures, entries = False, set(), 0
    for raw in text.splitlines():
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("truncated") is True:
            truncated = True
        elif obj.get("spec_change") is True:
            signatures.add(_signature([{"path": p, "expected": obj["expected"].get(p, ""),
                                        "actual": obj["actual"].get(p, "")}
                                       for p in obj.get("paths", [])]))
        elif "run_id" in obj and "step_number" in obj:
            keys.add((str(obj["run_id"]), int(obj["step_number"])))
            entries += 1
    return keys, truncated, signatures, entries


def _alert(env: HealingEnv, rid: str, actor: str, kind: str, detail: str, ref: str) -> None:
    env.writer.persist(Op("event.append", rid, {
        "research_id": rid, "event_type": "research.alert", "actor": actor[:100],
        "payload": {"kind": kind, "detail": detail[:500]},
        "ref_kind": "healing", "ref_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"healing:{ref}"))}))


def sync(env: HealingEnv, row: Mapping[str, Any], *, frozen_digests: Mapping[str, str],
                 root: Path | None, actor: str = "system") -> dict[str, Any]:
    """`:healing-sync` 的本體。順序：讀視圖（DB 阻塞＝例外、尚未寫任何檔）→對 log 求差→追加→（有
    漂移才）寫一行並告警。回 `{view_rows, log_lines, appended, spec_change}`。"""
    rid, ws = str(row["id"]), Path(row["workspace_path"])
    with env.writer.project_lock(rid):
        view = derive_entries(env.db.list_healing_attempts(rid)) if row.get(
            "console_project_id") else []
        drift = detect_spec_change(frozen_digests, root) if root is not None else []
        target = layout.safe_join(ws, HEALING_LOG_REL)
        old = target.read_text(encoding="utf-8") if target.is_file() else ""
        keys, truncated, signatures, entries = _scan_log(old)
        text, appended, hit_limit = old, 0, False
        limit = HEALING_LOG_MAX_BYTES

        def room(extra: str) -> bool:
            return len((text + extra).encode("utf-8")) <= limit

        if not truncated:
            for entry in view:
                if (entry["run_id"], entry["step_number"]) in keys:
                    continue
                line = _line(entry) + "\n"
                if not room(line):
                    hit_limit = True
                    break
                text, appended = text + line, appended + 1
        new_signature = _signature(drift) if drift else None
        write_drift = bool(drift) and not truncated and not hit_limit \
            and new_signature not in signatures
        if write_drift:
            line = _line(drift_line(drift)) + "\n"
            if room(line):
                text += line
            else:
                hit_limit, write_drift = True, False
        if hit_limit:
            text += _TRUNCATED_LINE + "\n"
        if text != old:
            fsutil.write_text_atomic(target, text)
        if hit_limit:
            _alert(env, rid, actor, ALERT_LOG_TRUNCATED,
                   f"{HEALING_LOG_REL} 超過 {limit} 位元組，停止追加", f"truncated:{rid}")
        if write_drift:
            _alert(env, rid, actor, ALERT_SPEC_CHANGE,
                   json.dumps(drift_line(drift), ensure_ascii=False),
                   f"spec_change:{new_signature}")
    return {"view_rows": len(view), "log_lines": entries + appended, "appended": appended,
            "spec_change": drift}
