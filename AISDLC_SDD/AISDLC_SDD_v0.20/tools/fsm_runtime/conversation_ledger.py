"""Conversation overhead estimator + ledger calibration (ACT-024, Phase E M2).

The pre/post hooks count tokens for file I/O (Read/Write/Edit/Bash), but the
real conversation context also carries:

- `cat -n` prefix on Read results (~8 chars per line)
- Bash stdout/stderr bytes (captured by post hook already)
- Tool-use / tool-result JSON overhead per exchange
- System reminders, additionalContext strings, assistant prose

This module provides:

1. `estimate_read_tokens(path)` — size + line-count-aware Read estimate
2. `estimate_bash_command_tokens(cmd)` — command-only pre estimate
3. `estimate_conversation_overhead(n)` — per-message JSON overhead
4. `merge_conversation_overhead_into_ledger()` — tick conversation cost into
   today's CONTEXT-LEDGER every N tool calls
5. `record_calibration_sample()` — persist estimated vs. observed delta so we
   can tune the multiplier over time

Design goals (per SDD_improving_Automation_04.md §ACT-024):

- < 10% drift on a full Stage (~50 tool calls)
- Never break on missing file / missing PyYAML (best-effort, silent fallback)
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_CHARS_PER_TOKEN = 4
_CAT_N_PREFIX_CHARS = 8  # "NNNN\t" padded + margin
# Overhead per Claude message (tool_use + tool_result JSON wrappers, system reminders).
# Empirical midpoint of the 100~500-token band documented in §E-05.
_CONVERSATION_OVERHEAD_PER_MESSAGE = 300
_DEFAULT_MERGE_EVERY = 10


def estimate_read_tokens(file_path: Optional[str]) -> int:
    """Return size + line-count-aware estimate for a Read call.

    Adds the cat -n prefix overhead (~8 chars per line). Falls back to the
    plain size/4 estimate if the file is unreadable.
    """
    if not file_path:
        return 0
    path = Path(file_path)
    try:
        if not path.exists() or not path.is_file():
            return 0
        size = path.stat().st_size
        try:
            with path.open("rb") as f:
                line_count = sum(1 for _ in f)
        except Exception:  # noqa: BLE001
            line_count = 0
        total_chars = size + line_count * _CAT_N_PREFIX_CHARS
        return max(1, total_chars // _CHARS_PER_TOKEN)
    except Exception:  # noqa: BLE001
        return 0


def estimate_bash_command_tokens(command: Optional[str]) -> int:
    """Pre-hook estimate for a Bash call — command text only.

    The post hook captures stdout/stderr size via tool_response.
    """
    if not command:
        return 0
    return max(1, len(command) // _CHARS_PER_TOKEN)


def estimate_conversation_overhead(message_count: int) -> int:
    """Per-message JSON / system-reminder overhead estimate.

    `message_count` = number of tool-use/tool-result pairs since last merge.
    """
    if message_count <= 0:
        return 0
    return int(message_count) * _CONVERSATION_OVERHEAD_PER_MESSAGE


def _ledger_path(ledger_dir: Path) -> Path:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    return ledger_dir / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"


def _merge_sidecar_if_present(path: Path, doc: Dict[str, Any]) -> int:
    """Fold a `.append` sidecar back into the main ledger document.

    QA Round-3 P2-07: when `file_lock` timed out during pre/post hook writes,
    entries are staged into `{ledger}.append` instead of the primary ledger.
    If we skip reconciliation, `last_merge_entry_index` counts only the
    primary's `entries`, which silently undercounts tool calls and
    over-merges conversation overhead on the next tick. This helper appends
    sidecar entries into ``doc['entries']`` and bumps cumulative tokens,
    then removes the sidecar. Returns the number of entries merged.
    """
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return 0
    sidecar = path.with_suffix(path.suffix + ".append")
    if not sidecar.exists():
        return 0
    merged = 0
    try:
        with sidecar.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load_all(f)
            for chunk in raw:
                if not chunk:
                    continue
                # Each YAML document in the sidecar is a list[dict] per
                # context_ledger_pre.py's degraded-fallback path.
                if isinstance(chunk, list):
                    for item in chunk:
                        if isinstance(item, dict):
                            doc.setdefault("entries", []).append(item)
                            doc["cumulative_tokens"] = int(doc.get("cumulative_tokens", 0)) + int(item.get("tokens", 0))
                            merged += 1
                elif isinstance(chunk, dict):
                    doc.setdefault("entries", []).append(chunk)
                    doc["cumulative_tokens"] = int(doc.get("cumulative_tokens", 0)) + int(chunk.get("tokens", 0))
                    merged += 1
    except Exception:  # noqa: BLE001 — sidecar is best-effort
        return merged
    if merged > 0:
        try:
            sidecar.unlink()
        except FileNotFoundError:
            pass
    return merged


def merge_conversation_overhead_into_ledger(
    ledger_dir: Path,
    *,
    merge_every: int = _DEFAULT_MERGE_EVERY,
    entries_per_call: int = 2,
    clock=None,
) -> Dict[str, Any]:
    """Tick conversation overhead into the daily ledger.

    Counts entries since last merge; translates them into tool calls using
    `entries_per_call` (default 2 — pre-hook + post-hook each append an entry,
    so 2 entries = 1 real tool call). When `delta_calls` reaches `merge_every`
    appends one `phase=conv-overhead` entry per tool call and bumps
    cumulative_tokens.

    P1-06 fix (§CLAUDE.md Rule 9.8.2): before this patch we merged every 10
    ledger *entries*, which was in fact every 5 tool calls — overcounting
    conversation overhead by 2×. The new `entries_per_call` parameter keeps
    the "every 10 tool calls" guarantee promised in Rule 9.8.2.

    Returns a dict summarising action taken:
      {"merged": bool, "added_tokens": int, "cumulative": int}
    """
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return {"merged": False, "added_tokens": 0, "cumulative": 0}

    if entries_per_call < 1:
        entries_per_call = 1

    path = _ledger_path(ledger_dir)
    if not path.exists():
        return {"merged": False, "added_tokens": 0, "cumulative": 0}
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    # QA Round-3 P2-07: fold any pending sidecar (degraded-fallback writes
    # from pre/post hooks under lock contention) into the primary ledger
    # before computing delta_entries. Without this, entries stuck in the
    # sidecar would not count toward the 10-call conv-overhead tick and
    # we'd overmerge on the next cycle.
    sidecar_merged = _merge_sidecar_if_present(path, doc)
    entries = doc.get("entries") or []
    if not entries:
        return {"merged": False, "added_tokens": 0, "cumulative": int(doc.get("cumulative_tokens", 0))}

    conv_meta = doc.setdefault("conversation_overhead", {})
    last_merged_at_idx = int(conv_meta.get("last_merge_entry_index", 0))
    delta_entries = max(0, len(entries) - last_merged_at_idx)
    delta_calls = delta_entries // entries_per_call
    if delta_calls < merge_every:
        return {"merged": False, "added_tokens": 0, "cumulative": int(doc.get("cumulative_tokens", 0))}

    add = estimate_conversation_overhead(delta_calls)
    now_fn = clock or (lambda: _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))
    entries.append({
        "ts": now_fn(),
        "phase": "conv-overhead",
        "tool": "ConversationLedger",
        "target": None,
        "tokens": add,
        "messages_counted": delta_calls,
        "entries_counted": delta_entries,
    })
    doc["entries"] = entries
    cumulative = int(doc.get("cumulative_tokens", 0)) + add
    doc["cumulative_tokens"] = cumulative
    # Advance index by the *consumed* entry count, not raw len(entries), so
    # any tail entry that didn't form a complete pair carries over to the
    # next merge. The newly-appended conv-overhead entry is metadata only
    # and must not be counted as a real tool-call entry.
    conv_meta["last_merge_entry_index"] = last_merged_at_idx + delta_calls * entries_per_call
    conv_meta["last_merged_at"] = now_fn()
    conv_meta["total_conv_overhead_tokens"] = int(conv_meta.get("total_conv_overhead_tokens", 0)) + add

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)
    return {
        "merged": True,
        "added_tokens": add,
        "cumulative": cumulative,
        "sidecar_merged": sidecar_merged,
    }


def record_calibration_sample(
    ledger_dir: Path,
    *,
    estimated: int,
    observed: int,
    source: str = "manual",
) -> Path:
    """Persist an estimated-vs-observed sample for drift analysis.

    Writes/updates `build/reports/fsm/LEDGER-CALIBRATION-{date}.yaml` with a
    running list of samples. Tests and future tuning scripts consume this.
    """
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return Path()

    ledger_dir.mkdir(parents=True, exist_ok=True)
    date = _dt.date.today().isoformat()
    path = ledger_dir / f"LEDGER-CALIBRATION-{date}.yaml"
    doc: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    samples = doc.get("samples") or []
    delta = observed - estimated
    drift_pct = (abs(delta) / observed * 100) if observed > 0 else 0.0
    samples.append({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "estimated": int(estimated),
        "observed": int(observed),
        "delta": int(delta),
        "drift_pct": round(drift_pct, 2),
        "source": source,
    })
    doc["samples"] = samples
    doc["date"] = date
    doc["latest_drift_pct"] = round(drift_pct, 2)
    # Rolling average of last 10 samples
    recent = samples[-10:]
    if recent:
        avg = sum(s.get("drift_pct", 0.0) for s in recent) / len(recent)
        doc["rolling_avg_drift_pct_last10"] = round(avg, 2)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)
    return path


def estimate_tool_tokens(tool: str, tool_input: Dict[str, Any]) -> int:
    """Unified entry used by context_ledger_pre.py after ACT-024.

    Delegates to the specific estimators above. Kept stateless; all calibration
    bookkeeping lives in the ledger file on disk.
    """
    try:
        if tool == "Read":
            return estimate_read_tokens(tool_input.get("file_path"))
        if tool in {"Write", "Edit"}:
            text = tool_input.get("content") or tool_input.get("new_string") or ""
            return max(1, len(text) // _CHARS_PER_TOKEN) if text else 0
        if tool == "Bash":
            return estimate_bash_command_tokens(tool_input.get("command"))
        if tool == "NotebookEdit":
            text = tool_input.get("new_source") or tool_input.get("content") or ""
            return max(1, len(text) // _CHARS_PER_TOKEN) if text else 0
        if tool == "Task":
            # Each Task spawns a subagent — count one conversation overhead unit
            # (subagent system prompt / tool registry / wrapper) on top of the
            # caller-visible prompt. Post hook adds agent output later.
            prompt = tool_input.get("prompt") or ""
            prompt_tokens = max(1, len(prompt) // _CHARS_PER_TOKEN) if prompt else 0
            return prompt_tokens + estimate_conversation_overhead(1)
    except Exception:  # noqa: BLE001
        return 0
    return 0
