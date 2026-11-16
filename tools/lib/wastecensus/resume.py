"""續航量測 M-R1～M-R4（ADR-XPLAT-004 §2.17.7；量測探針，不接閘門 rc）。

WHY：2026-11-15 事故——停工後 reset 已過 294 分鐘才有人回來說「繼續」，舊視窗上下文已冷，一開口整份
重寫。`park` 上線後要能重跑量出：停工到下一次真工作隔多久（M-R1）、是不是又靠人叫醒（M-R2）、
醒來第一回合重寫多少快取（M-R3）、停工前有沒有續航憑證（M-R4）。
判準全是純函式（輸入皆已讀入的 list／dict，不自己讀家目錄）；`run` 才讀檔。
M-R2 用結構判準（reset 後第一筆對話記錄是真人提示且非機器提示前綴），不用「字數 ≤30」：
事故那則提示有 443 字，字數判準對事故事例不成立。
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime
from pathlib import Path

STOP_GAP_S = 30 * 60  # 相鄰對話記錄間隔 ≥ 此值才算候選停點
BURN_LOOKBACK_S = 15 * 60  # 間隔起點前這麼久內找 quota_burn 樣本
TRACE_NEAR_S = 10 * 60  # M-R4：停點前後這麼久內找 park_armed／park_done
MACHINE_PROMPT_PREFIXES = ("按交接包繼續：", "按磁碟任務書繼續：")
SHORT_KINDS = ("five_hour", "session")
COEF_WRITE_PP = 5.5e-5  # §2.15：Fable 寫入係數（n=2）：每個 cache_creation token 約占五小時窗幾 pp
_SYNTHETIC = "<synthetic>"


def _epoch(raw) -> float | None:
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    try:
        return datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _pct(raw) -> float | None:
    return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None


def find_stops(records: list[dict], burn: list[dict],
               prepare_pct: float) -> tuple[list[dict], int]:
    """回 `(停點列表, unmeasured 件數)`。records＝`{ts, kind, text, cc}`（ts 為 epoch）；
    burn＝quota_burn.jsonl 列（ts、pct{kind}、resets_at{kind}）。停點＝gap ≥ STOP_GAP_S ∧ 起點前
    BURN_LOOKBACK_S 內有樣本 ∧ 樣本短窗 pct ≥ prepare_pct ∧ 該軸 resets_at > 起點；
    兩軸皆達標取較晚。
    間隔夠長但缺樣本者計 unmeasured，不丟棄。"""
    recs = sorted(records, key=lambda r: r["ts"])
    samples = sorted(((_epoch(b.get("ts")), b) for b in burn if _epoch(b.get("ts")) is not None),
                     key=lambda x: x[0])
    stops, unmeasured = [], 0
    for cur, nxt in zip(recs, recs[1:]):
        if nxt["ts"] - cur["ts"] < STOP_GAP_S:
            continue
        near = [b for t, b in samples if cur["ts"] - BURN_LOOKBACK_S <= t <= cur["ts"]]
        if not near:
            unmeasured += 1
            continue
        pcts, resets = near[-1].get("pct") or {}, near[-1].get("resets_at") or {}
        hits = [_epoch(resets.get(k)) for k in SHORT_KINDS
                if (_pct(pcts.get(k)) or 0.0) >= prepare_pct]
        hits = [h for h in hits if h is not None and h > cur["ts"]]
        if hits:
            stops.append({"start": cur["ts"], "reset": max(hits), "next": nxt["ts"]})
    return stops, unmeasured


def _quantiles(values: list[float]) -> dict:
    ordered = sorted(values)
    p90 = ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))] if ordered else None
    return {"n": len(ordered), "median": statistics.median(ordered) if ordered else None,
            "p90": p90, "values": [round(v, 1) for v in ordered]}


def metrics(stops: list[dict], records: list[dict], traces: list[dict]) -> dict:
    """M-R1：stop.reset → 之後第一筆 assistant（分鐘；reset 落在間隔內者才計）；M-R2：reset 後第一筆
    對話記錄為真人提示（非機器前綴）；M-R3：該記錄之後第一個帶 usage 的 assistant 的
    cache_creation tokens 與 pp；M-R4：park_stop_block 件數與無憑證停點（前後 TRACE_NEAR_S 內
    無 park_armed／park_done）。"""
    recs = sorted(records, key=lambda r: r["ts"])
    waits, by_human, rewrite = [], 0, 0
    for stop in stops:
        if stop["reset"] >= stop["next"]:
            continue  # 續跑發生在 reset 之前，不是「reset 之後等人」
        after = [r for r in recs if r["ts"] > stop["reset"]]
        first = next((r for r in after if r["kind"] == "assistant"), None)
        if first is not None:
            waits.append((first["ts"] - stop["reset"]) / 60.0)
        if after and after[0]["kind"] == "human" and not str(after[0].get("text") or "").startswith(
                MACHINE_PROMPT_PREFIXES):
            by_human += 1
        hit = next((r for r in after[1:] if r["kind"] == "assistant" and r.get("cc") is not None),
                   None)
        rewrite += int(hit["cc"]) if hit else 0
    armed = [t for t in (_epoch(x.get("at")) for x in traces
                         if x.get("event") in ("park_armed", "park_done")) if t is not None]
    bare = [s for s in stops if not any(abs(a - s["start"]) <= TRACE_NEAR_S for a in armed)]
    return {"stops": len(stops), "m_r1": _quantiles(waits), "m_r2": by_human,
            "m_r3": {"tokens": rewrite, "pp": round(rewrite * COEF_WRITE_PP, 1)},
            "m_r4": {"stop_block": sum(1 for t in traces if t.get("event") == "park_stop_block"),
                     "stops_without_credential": len(bare)}}


def _text_of(message) -> str:
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content or [] if isinstance(b, dict))


def load_records(base: Path, since_days: float) -> list[dict]:
    """專案逐字稿（主檔）→ 對話記錄 `{ts, kind, text, cc}`；`kind`＝assistant（非合成）或 user 的
    origin.kind（human／auto-continuation／sdk…）。壞行略過。"""
    import time  # noqa: PLC0415

    floor, out = time.time() - since_days * 86400, []
    for path in sorted(base.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if '"assistant"' not in line and '"origin"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            ts, msg = _epoch(rec.get("timestamp")), rec.get("message")
            if ts is None or ts < floor or not isinstance(rec, dict):
                continue
            if rec.get("type") == "assistant":
                if isinstance(msg, dict) and msg.get("model") == _SYNTHETIC:
                    continue
                usage = msg.get("usage") if isinstance(msg, dict) else None
                cc = usage.get("cache_creation_input_tokens") if isinstance(usage, dict) else None
                out.append({"ts": ts, "kind": "assistant", "text": "", "cc": cc})
            elif rec.get("type") == "user" and isinstance(rec.get("origin"), dict) \
                    and not rec.get("isMeta"):
                out.append({"ts": ts, "kind": str(rec["origin"].get("kind")),
                            "text": _text_of(msg), "cc": None})
    return out


def _load_jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def run(base: Path, since_days: float, trace_file: Path, burn_file: str | None,
        out: str | None) -> int:
    """`--resume-metrics`：讀逐字稿＋quota_burn＋痕跡，印表（含 unmeasured）；`out` 才寫 jsonl。"""
    import endurance_env  # noqa: PLC0415 — lazy
    import quota_gate  # noqa: PLC0415
    import quota_policy  # noqa: PLC0415

    prepare = quota_policy.load_policy(quota_gate.policy_env())[0].prepare_pct
    burn_path = (Path(burn_file) if burn_file
                 else endurance_env.trace_dir_peek()[0] / "quota_burn.jsonl")
    records = load_records(base, since_days)
    stops, unmeasured = find_stops(records, _load_jsonl(burn_path), prepare)
    got = metrics(stops, records, _load_jsonl(trace_file))
    got["unmeasured"] = unmeasured
    r1 = got["m_r1"]
    print(f"== 續航量測 M-R1～M-R4（近 {since_days:g} 天；停點 {got['stops']}；"
          f"unmeasured={unmeasured}）==")
    print(f"   M-R1 reset→下一次真工作（分）：n={r1['n']} 中位={r1['median']} p90={r1['p90']}")
    print(f"   M-R2 reset 後第一筆是真人叫醒：{got['m_r2']} 件")
    print(f"   M-R3 醒來第一回合重寫：{got['m_r3']['tokens']:,} tok（約 {got['m_r3']['pp']}pp）")
    print(f"   M-R4 park_stop_block {got['m_r4']['stop_block']} 件；"
          f"無憑證停點 {got['m_r4']['stops_without_credential']} 個")
    if out:
        Path(out).write_text(json.dumps({"kind": "resume_metrics", **got}, ensure_ascii=False)
                             + "\n", encoding="utf-8", newline="\n")
    return 0
