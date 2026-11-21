"""prd_px 家族（long：每次 `--pace` 間隔 > 快取 TTL 180 s，真等待）：RV-PX02／03／06／16。

TTL 是常數（`quota_gate.QUOTA_CACHE_TTL_SECONDS`＝180，無環境鍵可縮），所以這幾案必須真等；
只在 `--long`／nightly 跑，長時間跑法一律 `sessionctl runlong`＋`waitfor`。"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

from . import CaseContext
from .prd_px_lib import ORG_HEADERS, ev, px, reset_iso, t5, t5_sandbox_env, usage_payload
from .prd_px_pace import env_default, halt_markers, pace

GAP = 185  # > TTL 180 s


def _rows(sb) -> list[dict]:
    p = sb.root / "traces" / "quota_burn.jsonl"
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _cap(out) -> int | None:
    m = re.search(r"cap=(\d+|None)", out.stdout)
    ctx_cap = m.group(1) if m else None
    return None if ctx_cap in (None, "None") else int(ctx_cap)


@px("RV-PX02", "P＋E", ("rollover_seen", "row_resets_at"), refs=("§4.1.3",), long=True, min_wall=GAP)  # noqa: E501
def px02(ctx: CaseContext) -> None:
    """§4.1.3：替身讀數 80%→3%、`resets_at` 前移約 5 小時，兩次 `--pace` 間隔 > TTL ⇒ 痕跡出現新窗段
    （同欄位 pct 驟降、resets_at 前移）、新窗列的 `resets_at` 等於替身值。"""
    sb = ctx.sandbox(probe_hooks=False)
    at1, at2 = reset_iso(20), reset_iso(300)
    pays = [{"five_hour": {"utilization": 80, "resets_at": at1}, "seven_day": {"utilization": 40, "resets_at": reset_iso(5000)}},  # noqa: E501
            {"five_hour": {"utilization": 3, "resets_at": at2}, "seven_day": {"utilization": 40, "resets_at": reset_iso(5000)}}]  # noqa: E501
    with t5(sb, lambda n, r: (200, dict(ORG_HEADERS), pays[min(n, 1)])) as stub:
        env = t5_sandbox_env(sb, stub)
        a = pace(sb, env)
        time.sleep(GAP)
        b = pace(sb, env)
        ctx.check(a.returncode == 0 and b.returncode == 0 and stub.count() == 2, f"應共 2 次取數：{stub.count()}")  # noqa: E501
    rows = _rows(sb)
    ctx.check(len(rows) == 2, f"帳本應 2 列：{len(rows)}")
    p1, p2 = rows[0]["pct"]["five_hour"], rows[1]["pct"]["five_hour"]
    r1, r2 = (datetime.fromisoformat(x["resets_at"]["five_hour"]) for x in rows)
    ctx.check(p1 == 80 and p2 == 3 and (r2 - r1).total_seconds() > 3600, f"未見新窗段：{p1}→{p2} {r1}→{r2}")  # noqa: E501
    ev(ctx, "rollover_seen", f"five_hour pct {p1}→{p2}、resets_at {r1:%H:%M}→{r2:%H:%M}（前移 {(r2 - r1).total_seconds() / 3600:.1f} h）兩列相隔 {GAP}s")  # noqa: E501
    ctx.check(datetime.fromisoformat(rows[1]["resets_at"]["five_hour"]) == datetime.fromisoformat(at2), "新窗列 resets_at 不等於替身值")  # noqa: E501
    ev(ctx, "row_resets_at", f"row={rows[1]['resets_at']['five_hour']} stub={at2}")


@px("RV-PX03", "P＋E", ("account_change_seen", "ledger_split"), refs=("§4.1.4",), long=True, min_wall=GAP)  # noqa: E501
def px03(ctx: CaseContext) -> None:
    """§4.1.4：替身兩次回應的 `anthropic-organization-id` 標頭不同、間隔 > TTL
    ⇒ `--pace` 出聲帳號變更、帳本出現兩個帳號鍵且舊鍵最後讀數未被新讀數覆寫。"""
    sb = ctx.sandbox(probe_hooks=False)

    def resp(n, r):
        h = {"anthropic-organization-id": "rv-org-A" if n == 0 else "rv-org-B", "anthropic-workspace-id": "rv-ws-1"}  # noqa: E501
        pct, mins = (80, 20) if n == 0 else (3, 300)
        return 200, h, usage_payload(five_hour=(pct, mins), seven_day=(40, 5000))

    with t5(sb, resp) as stub:
        env = t5_sandbox_env(sb, stub)
        pace(sb, env)
        time.sleep(GAP)
        b = pace(sb, env)
        ctx.check(stub.count() == 2, f"應共 2 次取數：{stub.count()}")
    m = re.search(r"偵測到帳號軸組合改變（(.*?)）", b.stdout)
    ctx.check(bool(m), f"第二次 --pace 應出聲帳號變更：\n{b.stdout[-500:]}")
    ev(ctx, "account_change_seen", f"pace 輸出：偵測到帳號軸組合改變（{m.group(1)}）")
    rows = _rows(sb)
    keys = [next((f for f in r["fp"] if f.startswith("account=")), None) for r in rows]
    ctx.check(len(set(keys)) == 2 and None not in keys, f"帳本應有兩個帳號鍵：{keys}")
    ctx.check(rows[0]["pct"]["five_hour"] == 80.0, f"舊鍵最後讀數被覆寫：{rows[0]['pct']}")
    ev(ctx, "ledger_split", f"account_keys={keys} 舊鍵讀數 five_hour={rows[0]['pct']['five_hour']}（未被新讀數 3 覆寫）")  # noqa: E501


@px("RV-PX16", "P", ("degraded_sustained", "never_halt"), refs=("§8-6",), long=True, min_wall=2 * GAP)  # noqa: E501
def px16(ctx: CaseContext) -> None:
    """§8-6：遙測永久失效（沙盒無憑證），每隔 > TTL 跑 `--pace` 共 3 次 ⇒ 三次皆量不到、cap ≤ prepare cap、永不 halt。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    prepare = int(env_default("AUTOSDD_QUOTA_CAP_PREPARE", sb))
    caps = []
    for i in range(3):
        if i:
            time.sleep(GAP)
        out = pace(sb, t5_sandbox_env(sb, None, creds=False))
        ctx.check(out.returncode == 0 and "band=unmeasured" in out.stdout, f"第 {i + 1} 次應量不到：\n{out.stdout[:400]}")  # noqa: E501
        c = _cap(out)
        ctx.check(c is not None and c <= prepare, f"第 {i + 1} 次 cap={c} 應 ≤ prepare={prepare}")
        caps.append(c)
    ev(ctx, "degraded_sustained", f"3 次（間隔 {GAP}s）皆 unmeasured，caps={caps} <= prepare_cap={prepare}")  # noqa: E501
    ctx.check(not halt_markers(sb), f"不得 halt：{halt_markers(sb)}")
    ev(ctx, "never_halt", f"halt_markers={len(halt_markers(sb))}")


@px("RV-PX06", "P＋E", ("hysteresis", "no_skip_level", "dwell_respected"), refs=("§4.2.4",), long=True,  # noqa: E501
    min_wall=10 * GAP)
def px06(ctx: CaseContext) -> None:
    """§4.2.4（TCS:590）：替身讀數在 converge 門檻（70%）±1pp 來回、每次間隔 > TTL ⇒ cap 變動次數 ≤ 穿越次數÷2、
    每次放寬只升 1 級、相鄰兩次放寬間隔 ≥ 最短停留秒數（現查 `AUTOSDD_QUOTA_MIN_DWELL_SECONDS`）。

    讀數幅度（WHY）：帶界隨 reset 距離而動（距 reset 200 分時 69／71 都落 prepare、cap 恆 1，遲滯機制根本
    沒被踩到＝證據偏弱）。短窗改取距 reset 60 分：69％＝notice（cap 8）、71％＝converge（cap 4）——
    收緊 8→4 立即到位、放寬 4→5 必須等停留滿 300 s，讓「放寬事件」非空集合才驗得出 no_skip_level／dwell。
    TCS 寫「來回 10 次」＝10 次穿越，故取 11 筆讀數（10 個間隔）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    dwell = float(env_default("AUTOSDD_QUOTA_MIN_DWELL_SECONDS", sb))
    seq = [69, 71, 69, 71, 69, 71, 69, 71, 69, 71, 69]
    state = {"i": 0}

    def resp(n, r):
        pct = seq[min(state["i"], len(seq) - 1)]
        return 200, dict(ORG_HEADERS), usage_payload(five_hour=(pct, 60), seven_day=(20, 5000))

    caps, stamps = [], []
    with t5(sb, resp) as stub:
        env = t5_sandbox_env(sb, stub)
        for i in range(len(seq)):
            state["i"] = i
            if i:
                time.sleep(GAP)
            out = pace(sb, env)
            ctx.check(out.returncode == 0, f"--pace rc={out.returncode}")
            caps.append(_cap(out))
            stamps.append(time.time())
        ctx.check(stub.count() == len(seq), f"每次都應真的取數：{stub.count()}")
    ctx.check(all(c is not None for c in caps), f"讀數落在有數字 cap 的帶才有遲滯可驗：{caps}")
    changes = sum(1 for a, b in zip(caps, caps[1:]) if a != b)
    crossings = len(seq) - 1
    ctx.check(changes <= crossings // 2, f"cap 變動 {changes} 次 > 穿越次數 {crossings}÷2：{caps}")
    ev(ctx, "hysteresis", f"caps={caps} 變動={changes} <= 穿越 {crossings}//2={crossings // 2}")
    ups = [i for i, (a, b) in enumerate(zip(caps, caps[1:]), 1) if b > a]
    ctx.check(len(ups) >= 2, f"放寬事件須非空集合（>=2 次才能驗相鄰間隔）：ups={ups} caps={caps}")
    ctx.check(all(caps[i] - caps[i - 1] == 1 for i in ups), f"放寬應每次只升 1 級：{[(i, caps[i - 1], caps[i]) for i in ups]}")  # noqa: E501
    ev(ctx, "no_skip_level", f"放寬事件(索引,前→後)={[(i, caps[i - 1], caps[i]) for i in ups]}（每次升幅皆為 1）")  # noqa: E501
    gaps = [stamps[b] - stamps[a] for a, b in zip(ups, ups[1:])]
    last_change = 0
    since = []
    for i in range(1, len(caps)):
        if caps[i] != caps[i - 1]:
            if i in ups:
                since.append(stamps[i] - stamps[last_change])
            last_change = i
    ctx.check(all(g >= dwell for g in gaps) and all(s >= dwell for s in since),
              f"放寬間隔 {gaps}／距上次變更 {since} 不滿足最短停留 {dwell}s")
    ev(ctx, "dwell_respected", f"相鄰放寬間隔={[round(g) for g in gaps]}s、每次放寬距上次變更={[round(s) for s in since]}s >= dwell {dwell:.0f}s")  # noqa: E501
