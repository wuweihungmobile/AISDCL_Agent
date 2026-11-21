"""AC-7 配速床回放 `--replay-pace-floor`（ADR-XPLAT-004 §2.15.7；TCS-TokenWaste AT-QP-62／V-P6）。
把每一列真實 `quota_burn.jsonl` 各跑兩次判定（有床／無床），回答「床會不會擋掉正常工作」。
判準＝直接呼叫 `quota_policy.decide(..., pace_floor=True／False)`，不另寫第二份算式；
全程不呼叫網路、不讀真實 home（路徑一律由呼叫端傳入）。零 token、不接閘門 rc。

「會開床」＝有床那次有軸 `lifted`，且 cap 或 band 與無床那次不同（`lifted` 但水位本來就比床高
者，例如 99pp，結果逐位元相同，不算——床沒有改變任何決策）。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import quota_policy as qp
from quota_pace_floor import STATE_LIFTED

from .pace_metrics import epoch, hour_key, load_jsonl


def _state(row: dict) -> qp.QuotaState | None:
    """burn 列 → 判定輸入；缺 `resets_at`／水位全非數字回 None（呼叫端計 skipped）。"""
    pcts, resets = row.get("pct") or {}, row.get("resets_at")
    if not isinstance(resets, dict) or not resets:
        return None
    axes = tuple(qp.Axis(k, float(v), resets.get(k)) for k, v in pcts.items()
                 if isinstance(v, (int, float)) and not isinstance(v, bool))
    return qp.QuotaState(axes, str(row.get("ts")), "replay") if axes else None


def replay(burn: list[dict], policy: qp.Policy) -> dict:
    """逐列有床／無床對照。回 `{rows, opened, skipped, table}`；`table` 只列會開床的列。"""
    table, rows, skipped = [], 0, 0
    for row in burn:
        state, ts = _state(row), epoch(row.get("ts"))
        if state is None or ts is None:
            skipped += 1
            continue
        rows += 1
        now = datetime.fromtimestamp(ts).astimezone()
        with_bed = qp.decide(state, now, policy, pace_floor=True)
        without = qp.decide(state, now, policy, pace_floor=False)
        lifted = [f for f in with_bed.pace if f.state == STATE_LIFTED]
        if lifted and (with_bed.cap != without.cap or with_bed.band != without.band):
            table.append({"ts": row.get("ts"), "epoch": ts, "kind": lifted[0].kind,
                          "pct": lifted[0].pct, "minutes": lifted[0].minutes,
                          "cap_with": with_bed.cap, "cap_without": without.cap,
                          "band_with": with_bed.band, "band_without": without.band,
                          "short_key": hour_key((row.get("resets_at") or {}).get(lifted[0].kind))})
    return {"rows": rows, "opened": len(table), "skipped": skipped, "table": table}


def hit_windows(table: list[dict], halts: list[dict]) -> list[dict]:
    """每個 halt 標記：同一五小時窗（reset 取整到小時）內、halt 之前最早的開床時刻（無則 None）。"""
    out = []
    for marker in halts:
        key, at = hour_key(marker.get("reset_at")), epoch(marker.get("at"))
        early = sorted(r["epoch"] for r in table
                       if key is not None and r["short_key"] == key
                       and (at is None or r["epoch"] <= at))
        lead = round((at - early[0]) / 60.0, 1) if early and at is not None else None
        out.append({"halt_at": marker.get("at"), "binding": marker.get("binding"),
                    "earliest_open": (datetime.fromtimestamp(early[0]).astimezone().isoformat()
                                      if early else None), "lead_minutes": lead})
    return out


def run(burn_path: Path, halt_dir: Path, since_days: float, out: str | None) -> int:
    import time  # noqa: PLC0415

    import quota_gate  # noqa: PLC0415 — lazy：與 resume.run 同源取 policy

    floor = time.time() - since_days * 86400
    burn = [r for r in load_jsonl(burn_path) if (epoch(r.get("ts")) or 0.0) >= floor]
    policy = qp.load_policy(quota_gate.policy_env())[0]
    got = replay(burn, policy)
    markers = []
    for path in sorted(halt_dir.glob("halt_*.json")) if halt_dir.is_dir() else ():
        try:
            marker = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(marker, dict) and (epoch(marker.get("at")) or 0.0) >= floor:
            markers.append(marker)
    windows = hit_windows(got["table"], markers)
    print(f"== 配速床回放 AC-7（近 {since_days:g} 天；burn {len(burn)} 列；可回放 {got['rows']}；"
          f"缺 resets_at 等 skipped={got['skipped']}）==")
    print(f"   會開床的列數＝{got['opened']}")
    for r in got["table"][:30]:
        print(f"   {r['ts']} {r['kind']} {r['pct']:.0f}pp 剩 {r['minutes']:.0f} 分："
              f"cap_with={r['cap_with']} cap_without={r['cap_without']}"
              f"（{r['band_without']}→{r['band_with']}）")
    for w in windows:
        print(f"   撞牆窗 {w['halt_at']} binding={w['binding']}：最早開床 {w['earliest_open']}"
              f"（早於撞牆 {w['lead_minutes']} 分）")
    print("   （只回放、不判通過數字；交 QA 判讀「床會不會擋掉正常工作」）")
    if out:
        Path(out).write_text(json.dumps({"kind": "pace_replay", "rows": got["rows"],
                                         "opened": got["opened"], "skipped": got["skipped"],
                                         "table": got["table"], "halt_windows": windows},
                                        ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0
