"""配速床量測 M-P1／P3／P4／P7／M-C1（ADR-XPLAT-004 §2.15.7；TCS-TokenWaste AT-QP-56～61）。
量測探針，零 token、不接閘門 rc；判準全是純函式（輸入皆已讀入），`run` 才讀檔。

窗長一律以桶名文法判（`quota_pace.window_minutes`），不寫桶名白名單；reset 時刻取整到小時分組——
伺服器在 `:59:59.9`／`:00:00.1` 之間抖動，不取整會把同一窗拆成兩窗（AT-QP-58）。
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import quota_pace

SHORT_KINDS = ("five_hour", "session")  # 同一條底層限制被回報兩次（reset 逐字相同），取第一個有值者
EARLY_FRAC, EARLY_PCT, MIN_SAMPLES = 0.4, 70.0, 3  # M-P3：窗前 40% 時間內水位 ≥70、窗內 ≥3 樣本
WEEK_MINUTES, LAST_READ_S = 10080.0, 86400.0  # M-P4：長窗軸、reset 前最後讀數的距離上限
FLOOR_PCT = 90.0  # M-P4 不退化線（ADR §2.15.7 基線中位 90）


def epoch(raw) -> float | None:
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    try:
        return datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def hour_key(raw) -> float | None:
    """reset 時刻取整到最近整點的 epoch；解不出回 None。"""
    value = epoch(raw)
    return None if value is None else round(value / 3600.0) * 3600.0


def load_jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def short_samples(burn: list[dict], floor: float = 0.0) -> tuple[dict, int]:
    """五小時窗樣本：`({窗鍵: [(ts, pct)]}, skipped)`。缺 `resets_at`／ts 解不出的列計 skipped。"""
    windows: dict = {}
    skipped = 0
    for row in burn:
        pcts, resets, ts = row.get("pct") or {}, row.get("resets_at") or {}, epoch(row.get("ts"))
        kind = next((k for k in SHORT_KINDS if isinstance(pcts.get(k), (int, float))), None)
        if kind is None or ts is None or ts < floor:
            continue
        key = hour_key(resets.get(kind))
        if key is None:
            skipped += 1
            continue
        windows.setdefault(key, []).append((ts, float(pcts[kind])))
    return windows, skipped


def m_p1(halt_dir: Path, since_days: float, now: float | None = None) -> dict:
    """撞牆次數：窗長為五小時的軸被 halt 的標記件數／週；壞 JSON 計 skipped，範圍外不計。"""
    floor = (now if now is not None else time.time()) - since_days * 86400
    count = skipped = 0
    for path in sorted(halt_dir.glob("halt_*.json")) if halt_dir.is_dir() else ():
        try:
            marker = json.loads(path.read_text(encoding="utf-8"))
            at = epoch(marker["at"])
            win = quota_pace.window_minutes(str(marker.get("binding")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            skipped += 1
            continue
        if at is not None and at >= floor and win == 300.0:
            count += 1
    return {"count": count, "per_week": round(count / (since_days / 7.0), 2), "skipped": skipped}


def m_p3(burn: list[dict], floor: float = 0.0) -> dict:
    """窗內早燒：窗前 40% 時間內水位 ≥70 的窗占比；樣本不足 3 的窗不入分母（落款稀疏）。"""
    windows, skipped = short_samples(burn, floor)
    usable = {k: v for k, v in windows.items() if len(v) >= MIN_SAMPLES}
    early = 0
    for reset, samples in usable.items():
        start = reset - 300.0 * 60.0
        if any(p >= EARLY_PCT and (ts - start) <= EARLY_FRAC * 300.0 * 60.0 for ts, p in samples):
            early += 1
    n = len(usable)
    return {"windows": n, "early_burn": early, "share": round(early / n, 3) if n else 0.0,
            "thin_windows": len(windows) - n, "skipped": skipped}


def m_p4(burn: list[dict], pace_events: list[dict], floor: float = 0.0) -> dict:
    """週用滿護欄：長窗軸 reset 前最後讀數（末列距 reset ≤24 小時者）。每軸回 weeks／median／
    min／values；`withdraw`＝讀數低於不退化線且該週 reset 前 24 小時內有 `pace_floor` 落款者。"""
    last: dict = {}
    for row in burn:
        resets, pcts, ts = row.get("resets_at") or {}, row.get("pct") or {}, epoch(row.get("ts"))
        if ts is None or ts < floor:
            continue
        for kind, raw in resets.items():
            win, key = quota_pace.window_minutes(kind), hour_key(raw)
            if win is None or win < WEEK_MINUTES or key is None \
                    or not isinstance(pcts.get(kind), (int, float)):
                continue
            if 0.0 <= key - ts <= LAST_READ_S and ts >= last.get((kind, key), (0.0, 0.0))[0]:
                last[(kind, key)] = (ts, float(pcts[kind]))
    floors = [epoch(e.get("at")) for e in pace_events if e.get("event") == "pace_floor"]
    by_kind: dict = {}
    withdraw = []
    for (kind, key), (_ts, pct) in sorted(last.items()):
        by_kind.setdefault(kind, []).append(pct)
        if pct < FLOOR_PCT and any(f is not None and key - LAST_READ_S <= f <= key for f in floors):
            withdraw.append({"kind": kind, "reset": key, "pct": pct})
    return {"by_kind": {k: {"weeks": len(v), "median": statistics.median(v), "min": min(v),
                            "values": sorted(v)} for k, v in by_kind.items()},
            "withdraw": withdraw}


def m_p7(burn: list[dict], pace_events: list[dict], floor: float = 0.0) -> dict:
    """趕工使用率：與任一 `pace_rush_on`（`at`～`until`）重疊的五小時窗占比；無資料回全 0。"""
    windows, _skipped = short_samples(burn, floor)
    spans = [(epoch(e.get("at")), epoch(e.get("until"))) for e in pace_events
             if e.get("event") == "pace_rush_on"]
    spans = [(a, b) for a, b in spans if a is not None and b is not None]
    hit = sum(1 for reset in windows
              if any(a < reset and b > reset - 300.0 * 60.0 for a, b in spans))
    n = len(windows)
    return {"windows": n, "rush_windows": hit, "share": round(hit / n, 3) if n else 0.0,
            "on_events": len(spans)}


def m_c1(base: Path, since_days: float) -> dict:
    """主控每請求新增寫入：主檔（不含子代理）assistant 的 cache_creation；同 message id 算一次。"""
    floor, per_request = time.time() - since_days * 86400, {}
    for path in sorted(base.glob("*.jsonl")) if base.is_dir() else ():
        for rec in load_jsonl(path):
            msg = rec.get("message")
            ts = epoch(rec.get("timestamp"))
            if rec.get("type") != "assistant" or not isinstance(msg, dict) \
                    or msg.get("model") == "<synthetic>" or ts is None or ts < floor:
                continue
            usage = msg.get("usage")
            cc = usage.get("cache_creation_input_tokens") if isinstance(usage, dict) else None
            if isinstance(cc, (int, float)):
                per_request[msg.get("id") or f"{path.name}:{len(per_request)}"] = float(cc)
    vals = list(per_request.values())
    return {"n": len(vals), "mean": round(statistics.mean(vals), 1) if vals else None,
            "median": statistics.median(vals) if vals else None}


def run(base: Path, since_days: float, halt_dir: Path, burn_path: Path, pace_file: Path,
        out: str | None) -> int:
    floor = time.time() - since_days * 86400
    burn, events = load_jsonl(burn_path), load_jsonl(pace_file)
    got = {"m_p1": m_p1(halt_dir, since_days), "m_p3": m_p3(burn, floor),
           "m_p4": m_p4(burn, events, floor), "m_p7": m_p7(burn, events, floor),
           "m_c1": m_c1(base, since_days)}
    print(f"== 配速床量測 M-P1／P3／P4／P7／M-C1（近 {since_days:g} 天；burn {len(burn)} 列、"
          f"落款事件 {len(events)} 列）==")
    if not burn and not events and not got["m_p1"]["count"] and not got["m_c1"]["n"]:
        print("   無資料（quota_burn／落款事件／halt 標記／逐字稿皆空）")
    p1, p3, p7, c1 = got["m_p1"], got["m_p3"], got["m_p7"], got["m_c1"]
    print(f"   M-P1 撞牆（五小時窗軸 halt）：{p1['count']} 件、{p1['per_week']}／週"
          f"（壞標記 {p1['skipped']}）")
    print(f"   M-P3 窗內早燒：{p3['early_burn']}／{p3['windows']} 窗（占比 {p3['share']}；"
          f"樣本不足 {p3['thin_windows']} 窗不入分母；缺 resets_at {p3['skipped']} 列）")
    for kind, v in got["m_p4"]["by_kind"].items():
        print(f"   M-P4 {kind} reset 前最後讀數：{v['weeks']} 週，中位 {v['median']} "
              f"最小 {v['min']}（不退化線 {FLOOR_PCT:g}）")
    hits = len(got["m_p4"]["withdraw"])
    print(f"   M-P4 撤回條件命中（<{FLOOR_PCT:g} 且 24h 內有 pace_floor 落款）：{hits} 週")
    print(f"   M-P7 趕工使用率：{p7['rush_windows']}／{p7['windows']} 窗（{p7['share']}；"
          f">0.5 代表床太緊）")
    print(f"   M-C1 主控每請求新增寫入：n={c1['n']} 平均 {c1['mean']} 中位 {c1['median']}"
          "（目標平均 ≤2500）")
    if out:
        Path(out).write_text(json.dumps({"kind": "pace_metrics", **got}, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")
    return 0
