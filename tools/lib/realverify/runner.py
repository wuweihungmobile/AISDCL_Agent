"""runner：選案例→逐案跑（finally 必清）→末行 `REALVERIFY_VERDICT=`→寫帳本；rc 0 全過／1 有失敗／2 環境缺件／3 用法。"""  # noqa: E501

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from . import interactive, ledger, sched
from .cases import Case, CaseContext, discover
from .driver import EnvMissing
from .sandbox import REPO

CASES_JSON = REPO / "docs" / "06_quality" / "RealVerify_Protocol" / "cases.json"


@dataclass
class Outcome:
    case_id: str
    status: str  # pass / fail / env
    detail: str = ""
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def load_protocol(path: Path | None = None) -> dict:
    p = path or CASES_JSON
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def select(cases: dict[str, Case], *, case_id: str | None, family: str | None, all_: bool, long: bool) -> list[Case]:  # noqa: E501
    if case_id:
        return [cases[case_id]] if case_id in cases else []
    pool = [c for c in cases.values() if (all_ or (family and c.family == family))]
    return sorted([c for c in pool if long or not c.long], key=lambda c: c.id)


def _with_kept(detail: str, ctx: CaseContext) -> str:
    """失敗時（沙盒還沒清）先把證據複製到持久目錄，並把路徑接到失敗訊息與 notes（P3-c）。
    env 缺件沒有可判的行為，不走這裡。"""
    kept = ctx.keep_failure_evidence()
    if not kept:
        return detail
    ctx.evidences.append(f"保留證據：{kept}")  # 進帳本列，事後找得到
    return f"{detail}\n保留證據：{kept}"


def run_case(c: Case) -> Outcome:
    key = f"{c.fn.__module__.rsplit('.', 1)[-1]}.py::{c.fn.__name__}"
    if key in interactive.UNMIGRATED:  # R217 F5：未改走互動入口的開窗案例不跑（會跳信任框）
        return Outcome(c.id, "env", f"{key} 會開互動視窗卻未經 interactive.trusted_sandbox，拒跑以免跳信任框")  # noqa: E501
    ctx = CaseContext(c.id)
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
    out.evidence, out.notes = ctx.evidences, ctx.notes + residue
    if any(n.startswith("RESIDUE") for n in residue) and out.status == "pass":
        out.status, out.detail = "fail", "清理後仍有殘留：" + "; ".join(residue)
    return out


def run(selection: str, cases: list[Case], *, write_ledger: bool = True, ledger_path: Path | None = None) -> int:  # noqa: E501
    t0 = time.monotonic()
    outs = [run_case(c) for c in cases]
    # 只在本批含真 schtasks 案例時掃殘（避免單元測試／純 hook 批次去動別的視窗正在跑的
    # AutoSDD_RV_ 工作）
    leaked = sched.cleanup_all_rv() if any(c.uses_sched for c in cases) else []
    failed = [o.case_id for o in outs if o.status == "fail"]
    envs = [o.case_id for o in outs if o.status == "env"]
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
    print(f"REALVERIFY_VERDICT={'pass' if verdict == 'pass' else 'fail'} n={len(outs)} fail={failed + envs}")  # noqa: E501
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
