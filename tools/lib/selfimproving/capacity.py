"""SelfImproving `capacity`：有上限載入面的容量事件、歸檔候選與截斷風險（TCS-P3 R129）。

能力類別 `ro`、零寫入：記憶索引軸（位元組與行數兩個上限）、KB 軸（驅逐計數）、偏好軸（鍵數）。量不到
一律 `NOT-EVALUABLE` 並帶理由碼（不是 rc 3、不是零）；候選只提議、逐字取自索引檔尾、不寫任何檔
（歸檔走 M 類歸檔型 PROP，ADR-SI-06）；KB 與偏好只印容量報告與 OBS 草稿列（PRD §9.7 #23）。
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from . import check as si_check
from . import refs as si_refs
from . import rows as si_rows
from . import transcript as si_transcript
from .ledger import max_valid_id, parse_ledger

# 與引擎常數的唯讀漂移鎖：AutoClaude/autoclaude/utils/knowledge_base.py 的 `_MAX_ENTRIES`、
# AutoClaude/autoclaude/plugins/preference_memory_plugin.py 的 `_MAX_KEYS`
KB_MAX_ENTRIES = 1000
PREFS_MAX_KEYS = 10
PARAM_KEYS = ("cap_frac", "memory_index_max_lines", "memory_index_max_bytes",
              "max_archive_entries_per_card")
_EVIDENCE = "`python tools/selfimproving.py capacity`"


def _ne(reason: str) -> dict:
    return {"status": "NOT-EVALUABLE", "reason": reason}


def _axis(used: int, limit: int, over: bool) -> dict:
    return {"status": "read", "used": used, "limit": limit, "frac": used / limit, "over_cap": over}


def default_index(repo: Path) -> Path:
    return si_transcript.transcript_dir(repo) / "memory" / "MEMORY.md"


def _split(raw: bytes) -> list[bytes]:
    parts = raw.split(b"\n")
    return [p + b"\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _ratio_over(used: int, limit: int, cap) -> bool:
    return Fraction(used, limit) >= Fraction(str(cap))


def _candidates(lines: list[bytes], total: int, params: dict) -> tuple[list[dict], bool]:
    """R129 (d)：自檔尾向前逐個條目行取到「歸檔後低於 cap_frac」為止（保守估一行歸檔指標）。"""
    cap = Fraction(str(params["cap_frac"]))
    max_l, max_b = params["memory_index_max_lines"], params["memory_index_max_bytes"]
    size = sum(len(x) for x in lines)
    entries = [i for i, x in enumerate(lines) if x.startswith(b"- ")]
    taken: list[int] = []
    longest, removed = 0, 0
    ok = False
    for i in reversed(entries):
        taken.append(i)
        longest, removed = max(longest, len(lines[i])), removed + len(lines[i])
        if total - len(taken) + 1 < cap * max_l and size - removed + longest < cap * max_b:
            ok = True
            break
    taken.sort()
    per, cards = params["max_archive_entries_per_card"], []
    for k in range(0, len(taken), per):
        chunk = taken[k:k + per]
        text = b"".join(lines[i] for i in chunk).decode("utf-8", "replace")
        cards.append({"card": text, "lines": len(chunk), "first_line": chunk[0] + 1,
                      "last_line": chunk[-1] + 1})
    return cards, not ok


def truncation_risk(index_bytes: bytes, params: dict) -> dict | None:
    """R129 (f)：索引大於載入上限時，落在載入範圍之外的條目（行號或結束偏移超過上限）。"""
    lines = _split(index_bytes)
    max_l, max_b = params["memory_index_max_lines"], params["memory_index_max_bytes"]
    if len(lines) <= max_l and len(index_bytes) <= max_b:
        return None
    hits, end = [], 0
    for no, line in enumerate(lines, start=1):
        end += len(line)
        if line.startswith(b"- ") and (no > max_l or end > max_b):
            hits.append(no)
    return {"entries": len(hits), "first_line": hits[0]} if hits else None


def _memory_axis(index_bytes: bytes | None, params: dict) -> tuple[dict, list, dict | None]:
    if index_bytes is None:
        return _ne("memory-index-missing"), [], None
    lines = _split(index_bytes)
    max_l, max_b = params["memory_index_max_lines"], params["memory_index_max_bytes"]
    pairs = [(len(lines), max_l), (len(index_bytes), max_b)]
    used, limit = max(pairs, key=lambda p: Fraction(p[0], p[1]))
    over = any(_ratio_over(u, lim, params["cap_frac"]) for u, lim in pairs)
    cards: list[dict] = []
    if over:
        cards, insufficient = _candidates(lines, len(lines), params)
        if insufficient:  # 全部取完仍不足：列全部並標記
            cards = [{**c, "insufficient": True} for c in cards]
    return _axis(used, limit, over), cards, truncation_risk(index_bytes, params)


def _kb_axis(kb) -> dict:
    if isinstance(kb, str):
        return _ne(kb)
    n = kb.get("kb_cache_eviction_count")
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        return _ne("kb-metrics-unparseable")
    return {"status": "read", "used": n, "limit": KB_MAX_ENTRIES, "frac": 1.0 if n else 0.0,
            "over_cap": n >= 1}


def _prefs_axis(prefs, params: dict) -> dict:
    if isinstance(prefs, str):
        return _ne(prefs)
    n = len(prefs)
    return _axis(n, PREFS_MAX_KEYS, _ratio_over(n, PREFS_MAX_KEYS, params["cap_frac"]))


def _draft(num: int, category: str, severity: str, symptom: str) -> str:
    return si_rows.draft_row(num, "si capacity（自動草稿）", symptom, _EVIDENCE, "si-capacity",
                             category=category, severity=severity)


def evaluate(index_bytes: bytes | None, kb, prefs, params: dict, *, top: int = 0) -> dict:
    """容量報告物件（`--json` 的形態）。`kb`、`prefs`＝已解析的 JSON 物件，或量不到的理由碼
    字串（`kb-not-supplied`…）；`index_bytes` 為 None＝`memory-index-missing`；`top`＝OBS 帳本
    現有最大號。"""
    mem, cards, risk = _memory_axis(index_bytes, params)
    kb_axis = _kb_axis(kb if kb is not None else "kb-not-supplied")
    pf_axis = _prefs_axis(prefs if prefs is not None else "prefs-not-supplied", params)
    drafts, events = [], []
    for name, axis, sev in (("memory_index", mem, "P3"), ("kb", kb_axis, "P4"),
                            ("prefs", pf_axis, "P4")):
        if axis["status"] == "read" and axis["over_cap"]:
            events.append({"trigger": "e", "subject": name,
                           "detail": f"{name} 用量 {axis['used']}／{axis['limit']} 達 cap_frac"})
            drafts.append(_draft(top + len(drafts) + 1, "process", sev,
                                 f"{name} 容量達上限門檻（{axis['used']}／{axis['limit']}）"))
    if risk is not None:
        drafts.append(_draft(top + len(drafts) + 1, "bug", "P2",
                             f"截斷風險：記憶索引 {risk['entries']} 個條目落在載入範圍之外"
                             f"（首個行號 {risk['first_line']}）"))
    return {"schema_rev": 1, "cap_frac": params["cap_frac"], "memory_index": mem, "kb": kb_axis,
            "prefs": pf_axis, "retire_candidates": cards, "truncation_risk": risk,
            "obs_drafts": drafts, "events_detected": events}


def _load_json(path: str | None, missing: str, bad: str):
    if path is None:
        return missing
    try:
        obj = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        return bad
    return obj if isinstance(obj, dict) else bad


def default_summary(repo: Path, params: dict) -> tuple[dict, list]:
    """R130 (b)：對預設輸入（只有預設路徑的記憶索引）的彙總與其容量事件，供 `status` 用。"""
    rep = evaluate(_read_index(default_index(repo)), None, None, params)
    axes = {k: rep[k] for k in ("memory_index", "kb", "prefs")}
    if all(a["status"] != "read" for a in axes.values()):
        return {"status": "NOT-EVALUABLE", "reason": "no-axis-evaluable"}, []
    return {"status": "read", "axes": axes,
            "over_cap": [k for k, a in axes.items() if a["status"] == "read" and a["over_cap"]]
            }, rep["events_detected"]


def _read_index(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def run(repo: Path, memory_index: str | None, kb_metrics: str | None, prefs: str | None,
        as_json: bool) -> str:
    """`capacity` 動詞的輸出文字（唯讀）；params 鍵無效拋 `InputError`（rc 3）。"""
    params = si_check.params_for(repo, *PARAM_KEYS)
    text = si_refs.obs_ledger_text(repo)
    top = max_valid_id(parse_ledger(text)) if text else 0
    idx = _read_index(Path(memory_index) if memory_index else default_index(repo))
    kb = _load_json(kb_metrics, "kb-not-supplied", "kb-metrics-unparseable")
    pf = _load_json(prefs, "prefs-not-supplied", "prefs-unparseable")
    rep = evaluate(idx, kb, pf, params, top=top)
    if as_json:
        return json.dumps(rep, ensure_ascii=False) + "\n"
    out = []
    for name in ("memory_index", "kb", "prefs"):
        a = rep[name]
        out.append(f"{name}: NOT-EVALUABLE（{a['reason']}）" if a["status"] != "read" else
                   f"{name}: used={a['used']} limit={a['limit']} frac={a['frac']:.3f} "
                   f"over_cap={str(a['over_cap']).lower()}")
    if rep["truncation_risk"]:
        t = rep["truncation_risk"]
        out.append(f"truncation_risk: entries={t['entries']} first_line={t['first_line']}")
    for c in rep["retire_candidates"]:
        span = f"{c['first_line']}-{c['last_line']}"
        out.append(f"retire_candidate lines={span} entries={c['lines']}")
        out.append(c["card"].rstrip("\r\n"))
    if rep["obs_drafts"]:
        out += ["obs-draft:", *rep["obs_drafts"]]
    return "\n".join(out) + "\n"
