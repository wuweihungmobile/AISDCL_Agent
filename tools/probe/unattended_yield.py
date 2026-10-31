"""無人窗口產出率帳（ADR-XPLAT-004 §7 第 8 項的機械物；唯讀、零 token）。

此前「每窗的 bg_ceiling_kill、handback 四節齊備與否、燒掉的 pp 數」只能人工從三處對讀：
``$TMPDIR/autosdd_resume_log_*.jsonl``（planner 的稽核痕跡）、
``~/.autosdd/traces/autosdd_resume_cost.jsonl``（續跑成本帳）、
``~/.autosdd/traces/autosdd_unattended_outcome.jsonl``（結局檔）。本探針把三處
依 session 對起來，每個結局一列，末尾印彙總；累積 ≥5 窗後拿這張表裁「要不要接成 `--pace` 的一欄」。

用法：``python tools/probe/unattended_yield.py [--json]``（兩平台同一條指令；
stdout／stderr 由 ``_stdio_utf8`` 釘成 UTF-8）。
不接任何閘門的 rc：量測值會漂，恆 rc 0；三處任一缺席就在該欄印 ``-``，不猜。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TOOLS))
sys.path.insert(0, str(_TOOLS / "lib"))
import endurance_env  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  # 非 UTF-8 終端 print（中文／→）防崩潰保護

HANDBACK_SECTIONS = ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步")
RESUME_LOG_GLOB = "autosdd_resume_log_*.jsonl"
MIN_WINDOWS_FOR_DECISION = 5  # ADR-XPLAT-004 §7 第 8 項：累積 ≥5 窗再裁 --pace 欄


def _jsonl(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    rows: list[dict] = []
    for line in text.splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _resume_events(tmp: Path, sid: str) -> list[dict]:
    out: list[dict] = []
    for path in sorted(tmp.glob(RESUME_LOG_GLOB)):
        if sid in path.name:
            out.extend(_jsonl(path))
    return out


def _handback_sections(path_text: str) -> str:
    if not path_text:
        return "-"
    try:
        text = Path(path_text).read_text(encoding="utf-8")
    except OSError:
        return "missing"
    return f"{sum(1 for h in HANDBACK_SECTIONS if h in text)}/{len(HANDBACK_SECTIONS)}"


def _last(events: list[dict], kind: str, before: str) -> dict:
    """同 session 在結局時刻（含）之前的最後一筆該事件；沒有就空 dict。"""
    hits = [e for e in events if e.get("event") == kind and str(e.get("at") or "") <= before]
    return hits[-1] if hits else {}


def rows(trace_dir: Path, tmp: Path) -> list[dict]:
    outcomes = _jsonl(trace_dir / endurance_env.UNATTENDED_OUTCOME_NAME)
    costs = _jsonl(trace_dir / "autosdd_resume_cost.jsonl")
    table: list[dict] = []
    for o in outcomes:
        sid, at = str(o.get("session") or ""), str(o.get("at") or "")
        events = _resume_events(tmp, sid)
        resumed, stopped = _last(events, "resumed", at), _last(events, "relay_stopped", at)
        mine = [c for c in costs
                if c.get("session_id") == sid and str(c.get("recorded_at") or "") <= at]
        cost = mine[-1] if mine else {}
        pct = (cost.get("pct_before"), cost.get("pct_after"))
        table.append({
            "at": at, "session": sid[:8], "reason": o.get("reason"),
            "strategy": resumed.get("strategy", "-"),
            "rc": resumed.get("rc", "-"), "bg_ceiling_kill": resumed.get("bg_ceiling_kill", "-"),
            "files_changed": stopped.get("files_changed", "-"), "stop_why": stopped.get("why", "-"),
            "model": cost.get("model") or "-", "measured": cost.get("measured", "-"),
            "pp": f"{pct[0]}→{pct[1]}" if pct[0] is not None and pct[1] is not None else "-",
            "cache_creation_tokens": cost.get("cache_creation_input_tokens", "-"),
            "handback_sections": _handback_sections(str(o.get("handback") or "")),
        })
    return table


def main(argv: list[str]) -> int:
    table = rows(endurance_env.trace_dir(), Path(tempfile.gettempdir()))
    if "--json" in argv:
        print(json.dumps(table, ensure_ascii=False))
        return 0
    cols = ("at", "session", "reason", "strategy", "rc", "bg_ceiling_kill", "files_changed",
            "model", "pp", "cache_creation_tokens", "handback_sections")
    print(" | ".join(cols))
    for r in table:
        print(" | ".join(str(r[c]) for c in cols))
    n = len(table)
    kills = sum(1 for r in table if r["bg_ceiling_kill"] is True)
    done = sum(1 for r in table if r["reason"] == "done")
    print(f"[unattended_yield] windows={n} done={done} bg_ceiling_kill={kills} "
          f"decision_threshold={MIN_WINDOWS_FOR_DECISION} "
          f"{'可裁 --pace 欄' if n >= MIN_WINDOWS_FOR_DECISION else '樣本未達門檻，只累積不裁'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
