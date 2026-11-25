"""單一權威額度判決的取數、CLI 與 `--pace` 區塊（QVD §3.4、§3.5 C1／C3／C19；PRD §4.1.6）。

判準住扁平 `quota_ruling`（純函式）；本檔只做 I/O：讀快取（逾 TTL 經**既有單一站點**補量一次，
halt 標記不得壓住補量，R-4.1.6-6）→ 以同一份 `state` 呼叫 `quota_gate.dispatch_decision()`
與 `qw_plan.plan()` → `quota_ruling.ruling()`，回不可變快照；呼叫端不得再讀第二次快取拼湊。
`pace_report()` 自 `quota_gate` 搬入（QVD §9：hub 成員只縮不長），首行＝判決行。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import quota_gate as qg
import quota_policy
import quota_ruling as QR

from . import keepwarm, qw_calc, qw_plan, roster, switch

USAGE_RC = 2


@dataclass(frozen=True)
class Snapshot:
    """一次取數的全部輸入與判決（不可變；`ruling.line()` 即判決行）。"""

    state: object
    decision: object
    plan: object
    policy: object
    ruling: QR.Ruling


def _posture(path: Path) -> dict | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data.get("posture") if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def default_next_est(plan, env, n_plan: int | None = None) -> float:
    """§5：`next_est` 缺省＝`cal_agent × max(1, n_plan)`（缺 n_plan＝在飛數）。"""
    agent = qw_calc.calibrated_value(env, qw_calc.KEY_AGENT, qw_calc.AGENT_EST_DEFAULT_PP)[0]
    n = n_plan if n_plan is not None else (getattr(plan, "n_live", None) or 0)
    return float(agent) * max(1, int(n))


def _no_carrier(env) -> bool:
    off = str(env.get("AUTOSDD_KEEPWARM_OFF", "")).strip()
    return switch.switch_mode(env) != "auto" or bool(off)


def compose(state, decision, now: datetime, *, sid: str = "", transcript=None, env=None,
            model=None, next_est: float | None = None, plan=None,
            plan_seams: dict | None = None) -> Snapshot:
    """同一份 `state`／`decision` 組判決（hook 端 C1 與 `gather` 共用；不再取數）。
    `plan_seams`＝`qw_plan.plan` 的其餘縫（`ledger`／`live_fn`；測試用）。缺 `env` ⇒ `policy_env()`
    （檔案層＋真環境＋趕工戳記疊加，AT-QP-55：政策一律經它，不得只讀 `os.environ`）。"""
    env = qg.policy_env() if env is None else env
    policy = quota_policy.load_policy(env)[0]
    if plan is None:
        plan = qw_plan.plan(sid or "", transcript, env, now, read_quota=lambda _n: state,
                            refresh=lambda _n: state, **(plan_seams or {}))
    markers = [m for m in (qg.read_halt_marker(sid),) if m] if sid else []
    r = QR.ruling(state, decision, model=model, policy=policy, now=now, markers=markers,
                  plan=plan, next_est=next_est, wait_min=QR.wait_reset_min(env),
                  ttl=qg.QUOTA_CACHE_TTL_SECONDS,
                  billing=QR.billing_from_posture(_posture(qg.quota_cache_path())),
                  no_carrier=_no_carrier(env))
    return Snapshot(state, decision, plan, policy, r)


def gather(sid: str = "", transcript=None, *, env=None, now: datetime | None = None,
           model=None, next_est: float | None = None, payload: dict | None = None,
           event: str = "PostToolUse") -> Snapshot:
    """QVD §3.4：讀快取；不可用（含逾 TTL）⇒ 既有 `pace_state()` 補量一次（每 TTL 至多一次）；
    量不到且有 payload ⇒ L3 地板。halt 標記**不**壓住補量。"""
    env = qg.policy_env() if env is None else env
    now = now or datetime.now().astimezone()
    state = qg.pace_state(now)
    if not state.usable() and payload:
        state = qg.quota_floor_reading(payload, now) or state
    decision = qg.dispatch_decision(state, now, env, model, event, peek=True)
    return compose(state, decision, now, sid=sid, transcript=transcript, env=env, model=model,
                   next_est=next_est)


def current(sid: str, transcript, env, now: datetime, *, read_quota=None, plan=None,
            model=None, plan_seams: dict | None = None) -> Snapshot:
    """消費端的當下判決：縫 `read_quota(now)` 換讀數（同一條派工閘管線、唯讀一步組 cap）；
    缺＝`gather`（真取數，逾 TTL 補量一次）。"""
    if read_quota is None:
        return gather(sid, transcript, now=now, model=model)
    run_env = dict(qg.policy_env())
    run_env.update(env or {})
    state = read_quota(now)
    dec = qg.dispatch_decision(state, now, run_env, model, peek=True)
    return compose(state, dec, now, sid=sid, transcript=transcript, env=run_env, model=model,
                   plan=plan, plan_seams=plan_seams)


def _file_live(sid: str, transcript) -> tuple[int, bool]:
    """在飛數只取名冊（純讀檔）、不列行程（零子行程）；第二值 False＝背景 claude 行程那半沒量。"""
    try:
        slug = Path(transcript).parent if transcript is not None else None
        return len(roster.running(sid, projects_dir=slug)), False
    except Exception:  # noqa: BLE001 — 量不到＝不加燒量（同 qw_plan.live_count）
        return 0, False


def cached(sid: str = "", transcript=None, *, now: datetime | None = None,
           model=None) -> Snapshot:
    """只讀快取的判決（零網路、零子行程、不補量）：SessionStart 簡報（C10）、手動排程時刻、哨兵
    巡邏（C11／C15：零 token 巡邏契約＝巡邏期間零 HTTP、零子行程）與 `--check` 用——這些站點的
    既有契約都是「只讀快取」；快取逾 TTL ⇒ 量不到 ⇒ 判決照實帶 `deg=unmeasured`，不猜。"""
    now = now or datetime.now().astimezone()
    env = qg.policy_env()
    state = qg.read_quota(now)
    dec = qg.dispatch_decision(state, now, env, model, peek=True)
    return compose(state, dec, now, sid=sid, transcript=transcript, env=env, model=model,
                   plan_seams={"live_fn": _file_live})


def rule_from_decision(state, decision, now: datetime, payload: dict, model=None):
    """派工閘（C1）的注入依賴：hook 端把它交給 `quota_gate(rule=…)`；扁平 hub 不 import 本套件。"""
    raw = payload.get("transcript_path") if isinstance(payload, dict) else None
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    sid = transcript.stem if transcript is not None else str(payload.get("session_id") or "")
    return compose(state, decision, now, sid=sid, transcript=transcript, model=model).ruling


#: 哨兵維持撞線等待的判決動作（QVD §3.5 C11；無人窗口的 WAIT_RESET 交哨兵，§3.6）。
SENTINEL_WAIT_ACTIONS = ("HALT_WEEKLY", "PARK", "WAIT_RESET")


def sentinel_halt(sid: str, transcript, now: datetime, env=None) -> dict | None:
    """哨兵巡邏的 halt 輸入（C11）：以**判決**調整撞線等待——
    · 有同帳號（或舊格式）halt 標記且判決仍要等（`HALT_WEEKLY｜PARK｜WAIT_RESET`、reset 已知）⇒
      reset 取判決的 win／wk，維持撞線等待；
    · 有標記但判決已不要等（reset 已過、讀數已回）⇒ 原標記交 `halt_verdict` 判 probe／patrol
      （到點續跑的既有路徑；判決不得把它吞掉）；
    · 無標記：只有無人窗口的 `WAIT_RESET` 交哨兵武裝（QVD §3.6 第二列）；其餘 None（不等）。
    帳號不符的標記不當輸入（交 §7 作廢流程）。"""
    env = os.environ if env is None else env
    r = cached(sid, transcript, now=now).ruling  # 零 token 巡邏：只讀快取、零子行程
    marker = qg.read_halt_marker(sid) or {}
    if marker.get("account") and r.acct and marker["account"] != r.acct:
        marker = {}
    reset = r.wk if r.action == "HALT_WEEKLY" else r.win
    tag = {"ruling": r.action, "vid": r.vid}
    waiting = r.action in SENTINEL_WAIT_ACTIONS and bool(reset)
    if marker:
        return {**marker, **({"reset_at": reset} if waiting else {}), **tag}
    if waiting and r.action == QR.WAIT_RESET and env.get("AUTOSDD_UNATTENDED"):
        return {"reset_at": reset, "at": now.isoformat(), **tag}
    return None


def sentinel_halt_verdict(halt, idle_seconds, now: datetime, superseded_by=None):
    """`sentinel_decide` 的 halt 分支（C11）：判讀住判決家，planner 只接線。"""
    return qg.halt_verdict(halt, idle_seconds, now, superseded_by)


def check_halted_line(sid: str, now: datetime) -> str | None:
    """`--check` 的 halted 行（C3）：只在判決 `HALT_WEEKLY` 且同帳號標記時出現；標記檔不存在不取數
    （`--check` 不寫檔的既有契約，`quota_halt_marker.halt_marker_probe_path` 只讀不建）。"""
    import quota_halt_marker  # noqa: PLC0415

    if not quota_halt_marker.halt_marker_probe_path(sid).is_file():
        return None
    marker = qg.read_halt_marker(sid)
    r = cached(sid, now=now).ruling  # `--check`：只讀、不補量
    same = marker and (not marker.get("account") or marker.get("account") == r.acct)
    return qg.halted_band_line(marker, now) if same and r.action == "HALT_WEEKLY" else None


def fresh_or_recompute(text: str, now: datetime, sid: str = "", transcript=None, **kw):
    """QVD §4：消費端拿到判決行先看 `expires_at`；過期 ⇒ 重算並落 `stale_verdict_recomputed`，
    舊 vid 只進痕跡、不據以行動。回 `(fields, Ruling|None)`：未過期時 Ruling 為 None。"""
    fields = QR.parse(text)
    if fields is not None and not QR.expired(fields, now):
        return fields, None
    r = gather(sid, transcript, now=now, **kw).ruling
    old_at = QR._aware((fields or {}).get("measured_at"))  # noqa: SLF001
    switch.trace("stale_verdict_recomputed", sid=sid, old_vid=(fields or {}).get("vid"),
                 new_vid=r.vid, age_s=None if old_at is None
                 else int((now - old_at).total_seconds()))
    return QR.parse(QR.head(r)), r


# ─────────────────────────────────────────────────────────────── --pace（自 quota_gate 搬入）
def pace_report(now: datetime | None = None, model: str | None = None,
                sid: str | None = None, transcript=None) -> str:
    """`--pace` 全文：**首行＝判決行**（C3），第二行起為診斷段（逐軸明細、攤提、配速床、
    帳號姿態、扇出視窗、`QUOTAWALL_PLAN=` 等；只供人讀，判斷看首行）。halt 標記不再短路取數
    （R-4.1.6-6）；halted 行只在 `HALT_WEEKLY` 且同帳號標記時出現。"""
    now = now or datetime.now().astimezone()
    env = qg.policy_env()
    policy, problems = quota_policy.load_policy(env)
    hatch = qg.session_brief.escape_hatch_note(env)
    snap = gather(sid or "", transcript, env=env, now=now, model=model)
    r, state = snap.ruling, snap.state
    head = QR.line(r) + "\n"
    marker = qg.read_halt_marker(sid or "")
    same = marker and (not marker.get("account") or marker.get("account") == r.acct)
    halted = qg.halted_band_line(marker, now) if same and r.action == QR.HALT_WEEKLY else None
    if halted:
        head += qg.quota_messages.halted_pace_text(halted, state, r, policy)
    bd = qg.quota_burndown.active(state, now, env, qg.core_signature)  # DEF-200-528
    root = qg.fanout_ledger_path()
    qg.record_burn(state, live := qg.live_dispatches(root, now), bd and bd.id)
    window = qg.fanout_window_left(root, now)
    ratio, ratio_note, plan_note = qg.burn_ratio(state)
    decision = quota_policy.decide(state, now, policy, ratio, ratio_note, active_model=model,
                                   burndown=bd)
    qg.quota_burndown.log_decision(decision, now)
    # 引擎側配速契約（R86／R102）：pace 那把尺的平穩機制，不改守衛的執法狀態（DEF-200-437）。
    avail = qg.quota_availability.evaluate(
        now, state.usable(), exit_streak=policy.availability_exit_streak,
        min_dwell_seconds=policy.availability_min_dwell_seconds)
    stabilized = qg.quota_stability.evaluate(
        decision.cap, decision.band, now, scope=model, ruler=qg.quota_stability.RULER_PACE,
        min_dwell_seconds=policy.min_dwell_seconds,
        unmeasured=avail.availability == qg.quota_availability.AVAILABILITY_UNMEASURED,
        reset_at=qg.halt_resets_at(decision))
    if stabilized != decision.cap:
        decision = qg.replace(decision, cap=stabilized,
                              recommended_fanout=min(decision.recommended_fanout, stabilized))
    qg.pace_contract.write(decision, state, policy.max_fanout, policy.halt_pct, model=model)
    tail = f"\n⚠️ env.shared（跨機）或本機 .env 有設錯：{'；'.join(problems)}" if problems else ""
    horizon = ("" if decision.cap is None
               else qg.throttle_horizon_line(decision, now, state.measured_at))
    return (head
            + f"{qg.pace_line(decision, live, policy.max_fanout)}\n"
            f"  {quota_policy.describe(decision, burndown=False)}\n"
            f"{qg.quota_burndown.full_line(decision)}"
            f"  {qg.quota_pace.explain(decision.amort, policy.converge_pct)}\n"
            f"{qg.quota_pace_floor.line(decision.pace)}"
            f"  {qg.posture_line(qg.quota_cache_path())}\n"
            f"{qg.fanout_window_line(window, live, qg.FANOUT_WINDOW_SECONDS)}"
            f"{horizon}{qg.quota_messages.model_lines(decision, env)}"
            f"  來源={state.source} 量測於={state.measured_at or '(無)'}{tail}\n{plan_note}{hatch}")


def pace_block(args, deps) -> int:
    """planner `--pace` 區塊（QVD §9 自 planner `main()` 抽出；`deps`＝planner 模組）。"""
    print(deps.endurance_env.unattended_outcome_banner(), end="")
    aim, source = deps.resolve_transcript_source(args.session_id, args.transcript)
    guard = deps.guard
    model = args.model or deps.harness_feed.active_model_of(aim, guard)
    sid = guard.session_id_of(aim) if aim else None
    print(pace_report(model=model, sid=sid, transcript=aim), end="")
    print(deps.quota_reconcile.ledger_gap_line(), end="")
    print(deps.modelmix.pace_line(qg, guard.model_family(model) or None), end="")
    print(deps.qw_cli.pace_line(sid, aim), end="")
    if aim:
        print(deps.harness_feed.session_line(source, sid), file=sys.stderr)
        if (liveness := deps.sentinel_lifecycle.liveness_line(sid)):
            print(liveness, file=sys.stderr)
    return 0


# ─────────────────────────────────────────────────────────────── `sessionctl quota`（C19）
def cli(argv: list[str], env=None, *, now: datetime | None = None, out=None) -> int:
    """`python tools/sessionctl.py quota [--json] [--next-est <pp>] [--model <family>] [--sid]`。
    印判決行（＋理由）；`--json` 印一個 JSON 物件（含 `band`／`reason`／`billing`）。rc 0。"""
    out = out or sys.stdout
    ap = argparse.ArgumentParser(prog="sessionctl quota")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--next-est", type=float, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--sid", default=None)
    ap.add_argument("--projects-dir", default=None)
    args = ap.parse_args(argv)
    run_env = qg.policy_env() if env is None else env
    sid = args.sid or str(os.environ.get("CLAUDE_CODE_SESSION_ID", "")).strip()
    sid = sid if roster._ID_RE.match(sid or "") else ""
    transcript = keepwarm.find_transcript(sid, args.projects_dir) if sid else None
    snap = gather(sid, transcript, env=run_env, now=now, model=args.model,
                  next_est=args.next_est)
    if args.json:
        print(json.dumps(QR.as_json(snap.ruling), ensure_ascii=False), file=out)
    else:
        print(QR.line(snap.ruling), file=out)
    return 0


__all__ = ["Snapshot", "gather", "cached", "compose", "rule_from_decision", "fresh_or_recompute",
           "pace_report", "pace_block", "cli", "default_next_est", "USAGE_RC"]
