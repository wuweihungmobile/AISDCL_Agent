"""runner：開頭重放租約帳＋發現式掃描→選案例→逐案跑（前後快照、finally 必清）→末行 `REALVERIFY_VERDICT=`→
寫帳本；rc 0 全過／1 有失敗／2 環境缺件或孤兒拒跑／3 用法。"""  # noqa: E501

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from . import interactive, leases, leases_discover, ledger, sched, snapshot
from .cases import Case, CaseContext, discover
from .driver import EnvMissing
from .sandbox import REPO

CASES_JSON = REPO / "docs" / "06_quality" / "RealVerify_Protocol" / "cases.json"
#: `run --all` 不含的家族（D-19）：RV-SE03 案例內會跑 `run --all`，含自己就遞迴；兩家族只能以
#: `--family`／`--case` 指名。
EXCLUDED_FROM_ALL = ("sideeffect", "sideeffect_selftest")
LEAK_HEAD = "SIDE-EFFECT LEAK"


@dataclass
class Outcome:
    case_id: str
    status: str  # pass / fail / env
    detail: str = ""
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)  # 本案快照字樣（批次層彙整用）


def load_protocol(path: Path | None = None) -> dict:
    p = path or CASES_JSON
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def select(cases: dict[str, Case], *, case_id: str | None, family: str | None, all_: bool, long: bool) -> list[Case]:  # noqa: E501
    if case_id:
        return [cases[case_id]] if case_id in cases else []
    pool = [c for c in cases.values()
            if (all_ and c.family not in EXCLUDED_FROM_ALL) or (family and c.family == family)]
    return sorted([c for c in pool if long or not c.long], key=lambda c: c.id)


def _with_kept(detail: str, ctx: CaseContext) -> str:
    """失敗時（沙盒還沒清）先把證據複製到持久目錄，並把路徑接到失敗訊息與 notes（P3-c）。
    env 缺件沒有可判的行為，不走這裡。"""
    kept = ctx.keep_failure_evidence()
    if not kept:
        return detail
    ctx.evidences.append(f"保留證據：{kept}")  # 進帳本列，事後找得到
    return f"{detail}\n保留證據：{kept}"


def _take() -> dict | None:
    """拍快照；量不到回 None（快照是量測，不得因量不到而擋案例——但呼叫端會記一則 note）。"""
    try:
        return snapshot.take()
    except Exception:  # noqa: BLE001
        return None


def run_case(c: Case) -> Outcome:
    key = f"{c.fn.__module__.rsplit('.', 1)[-1]}.py::{c.fn.__name__}"
    if key in interactive.UNMIGRATED:  # R217 F5：未改走互動入口的開窗案例不跑（會跳信任框）
        return Outcome(c.id, "env", f"{key} 會開互動視窗卻未經 interactive.trusted_sandbox，拒跑以免跳信任框")  # noqa: E501
    ctx = CaseContext(c.id, lease_minutes=c.lease_minutes)
    before = _take()
    try:
        if c.uses_sched:
            with sched.sched_lock():
                c.fn(ctx)
        else:
            c.fn(ctx)
        out = Outcome(c.id, "pass")
    except EnvMissing as e:
        out = Outcome(c.id, "env", str(e))
    except AssertionError as e:
        out = Outcome(c.id, "fail", _with_kept(str(e), ctx))
    except Exception as e:  # noqa: BLE001 - 案例內任何例外都是失敗，不是 skip
        out = Outcome(c.id, "fail", _with_kept(
            f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}", ctx))
    finally:
        residue = ctx.close()
    after = _take()  # 一定在 `ctx.close()` 之後（MU-SE-12）：案例自己清掉的東西不算洩漏
    out.evidence, out.notes, out.tokens = ctx.evidences, ctx.notes + residue, ctx.tokens()
    if any(n.startswith("RESIDUE") for n in residue) and out.status == "pass":
        out.status, out.detail = "fail", "清理後仍有殘留：" + "; ".join(residue)
    if before is None or after is None:
        out.notes.append("SNAPSHOT-UNAVAILABLE 快照量不到，本案未做洩漏比對")
        return out
    items = snapshot.diff(before, after, out.tokens)
    bad = snapshot.leaks(items)
    if bad:
        lines = [snapshot.fmt(i) for i in bad]
        out.status = "fail"
        out.detail = f"{LEAK_HEAD}\n" + "\n".join(lines) + (f"\n原判定：{out.detail}" if out.detail else "")  # noqa: E501
        out.notes += [f"LEAK {ln}" for ln in lines]
    elif items:
        out.notes.append(f"SNAPSHOT-NOISE n={len(items)}（不含本案字樣，真環境同時有別人在動；不判）")  # noqa: E501
    return out


def _preflight() -> tuple[list[str], int | None]:
    """開頭：重放租約帳＋發現式掃描。回（要印的行, 拒跑 rc 或 None）。有撤不掉者（不含 abandoned）
    ⇒ 寫 handback＋入通知佇列、rc 2（REQ-SE-33／37）。"""
    lines, stuck = leases_discover.preflight()
    if not stuck:
        return lines, None
    path = leases_discover.refusal_handback(leases.current_run_id(), stuck)
    lines.append(f"❌ 有撤不掉的孤兒，整批拒跑（{len(stuck)} 項）；handback＝{path}")
    lines += [f"   {ident}：{why}" for ident, why in stuck.items()]
    return lines, 2


def run(selection: str, cases: list[Case], *, write_ledger: bool = True, ledger_path: Path | None = None) -> int:  # noqa: E501
    t0 = time.monotonic()
    head, refuse = _preflight()
    for ln in head:
        print(ln)
    if refuse is not None:
        print("REALVERIFY_VERDICT=fail reason=orphans n=0 fail=['orphans']")
        return refuse
    batch_before = _take()
    outs = [run_case(c) for c in cases]
    # 本批結束：收帳（依帳判斷，不動別的視窗〔主人存活〕的合法排程）；含真 schtasks 案例才額外掃殘
    uses_sched = any(c.uses_sched for c in cases)
    leaked = (leases.revoke_run() + leases.discover_sweep(own_run_id=leases.current_run_id())) if uses_sched else []  # noqa: E501
    failed = [o.case_id for o in outs if o.status == "fail"]
    envs = [o.case_id for o in outs if o.status == "env"]
    reason = ""
    batch_after = _take()
    if batch_before is not None and batch_after is not None:
        items = snapshot.diff(batch_before, batch_after, [t for o in outs for t in o.tokens])
        bad = snapshot.leaks(items)
        if bad:
            failed.append("leak:" + ";".join(snapshot.fmt(i) for i in bad[:5]))
            reason = " reason=leak"
        elif items:
            print(f"note: 批次 SNAPSHOT-NOISE n={len(items)}（不含本批字樣，不判）")
    for o in outs:
        print(f"[{o.status.upper():4}] {o.case_id} {o.detail.splitlines()[0] if o.detail else ''}")
        for e in o.evidence:
            print(f"        evidence: {e}")
        for n in o.notes:
            print(f"        note: {n}")
    if leaked:
        failed.append("sched-leak:" + ",".join(leaked))
    verdict = "pass" if not failed and not envs else ("env" if not failed else "fail")
    ev = [e for o in outs for e in o.evidence] + ([f"ENV-MISSING {','.join(envs)}"] if envs else [])
    if write_ledger and outs:
        ledger.append_row(selection, verdict, len(outs), failed + envs, ev, time.monotonic() - t0, ledger_path)  # noqa: E501
    print(f"REALVERIFY_VERDICT={'pass' if verdict == 'pass' else 'fail'}{reason} n={len(outs)} fail={failed + envs}")  # noqa: E501
    return 0 if verdict == "pass" else (1 if failed else 2)


def list_cases() -> str:
    cases = discover()
    proto = load_protocol().get("cases", {})
    lines = []
    for cid in sorted(set(cases) | set(proto)):
        c = cases.get(cid)
        meta = proto.get(cid, {})
        state = ("long" if c and c.long else "ready") if c else "planned"
        refs = ",".join(meta.get("refs", c.refs if c else ()))
        lines.append(f"{cid:8} {state:8} {meta.get('family', c.family if c else '?'):22} {refs}")
    return "\n".join(lines)


def main_run(case_id: str | None, family: str | None, all_: bool, long: bool) -> int:
    cases = discover()
    chosen = select(cases, case_id=case_id, family=family, all_=all_, long=long)
    if not chosen:
        print("REALVERIFY_VERDICT=fail n=0 fail=['no-case-selected']")
        return 3
    sel = case_id or (f"family={family}" if family else "all") + (" +long" if long else "")
    return run(sel, chosen)
