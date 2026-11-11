"""SelfImproving run-scoped 無人值守授權閘（TCS-SelfImproving-P4 R153；取代 P2 R70 的一律拒收）。

能力類別 `ro`：單一實作——整個套件讀 `AUTOSDD_UNATTENDED` 的站點只有本檔
（`decwrite.refuse_unattended` 與各動詞、入口都改呼叫 `gate`／`check`）。「有設」＝存在且值非空
（字面 `0` 算有設，空字串算未設）。真值表：未設＝全部放行；有設時 ① A 類須
`AUTOSDD_SI_PATROL_RUN` 與所屬運轉相等；② `decide` 只准 `console` 載體；③ C 類一律拒；④ 唯讀
動詞放行。誠實劃界：環境變數是行程自述，持有者可自設；偵測靠 `check` 的
`run.trigger_f_has_patrol_by` 與 git 歷史對 DEC 對帳，不是被擋。
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from . import events as si_events
from . import fold as si_fold

UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
PATROL_RUN_ENV = "AUTOSDD_SI_PATROL_RUN"
A_CLASS = ("research", "attr", "attr-confirm", "attr-reject", "prop-new", "prop-revise",
           "heldout-freeze", "card-issue", "fourq")
C_CLASS = ("run-open", "run-close", "obs-add", "obs-close", "sched-set", "sched-arm",
           "sched-disarm", "sandbox", "verify", "promote", "rollback", "measure", "patrol",
           "registry-ingest", "backtest", "push-run")
READONLY = ("check", "status", "scan", "card", "export", "capacity", "issues", "sched-show",
            "fourq-corpus")


def is_set(env: Mapping) -> bool:
    return bool(env.get(UNATTENDED_ENV))


def without_run_scope(env: Mapping) -> dict:
    """子行程環境：去掉無人值守自述與運轉範圍兩個變數（`push-run` 給 git 的環境用；單一實作的
    一部分——整個套件讀這兩個名字的站點只有本檔）。"""
    return {k: v for k, v in env.items() if k not in (UNATTENDED_ENV, PATROL_RUN_ENV)}


def _refuse(why: str) -> list[tuple[str, str]]:
    return [("UNATTENDED-REFUSED", f"{UNATTENDED_ENV} 有設：{why}")]


def gate(verb: str, run: str | None, env: Mapping, *, carrier: str | None = None
         ) -> list[tuple[str, str]]:
    """（碼, 說明）清單；空＝放行。`verb` 以連字號正規形（`sched set` 也收）；`run`＝該次寫入所屬的
    運轉（A 類）；`carrier` 只供 `decide`。"""
    verb = verb.replace(" ", "-")
    if not is_set(env):
        return []
    if verb == "decide":
        return [] if carrier == "console" else _refuse("decide 只准 --carrier console")
    if verb in A_CLASS:
        patrol = env.get(PATROL_RUN_ENV)
        if patrol and run == patrol:
            return []
        return _refuse(f"{verb} 須在 {PATROL_RUN_ENV} 所指運轉內寫入（所屬運轉 {run}）")
    if verb in READONLY:
        return []
    return _refuse(f"{verb} 一律拒收（C 類或未登記動詞）")


def _open_run_at(events: list[dict], seq: int) -> str | None:
    """seq 當下開著的運轉（ATT 沒有 run 欄：以其落帳當下未關的最近一個運轉為所屬）。"""
    cur = None
    for e in events:
        if e["seq"] >= seq:
            break
        if e["kind"] == "run.open":
            cur = e["run"]
        elif e["kind"] == "run.close" and e["run"] == cur:
            cur = None
    return cur


def owner_runs(repo: Path, verb: str, ns, env: Mapping) -> list[str | None]:
    """A 類動詞要比對的運轉清單：`--run`、所屬 PROP 的 `run`、所屬 ATT 當下開著的運轉；新 `attr`
    沒有現成所屬，取 `AUTOSDD_SI_PATROL_RUN` 若其為目前未關運轉。解不出者為 None（fail-closed）。"""
    verb = verb.replace(" ", "-")
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events)
    out: list[str | None] = []
    if getattr(ns, "run", None):
        out.append(ns.run)
    prop_id = getattr(ns, "prop", None)
    if verb in ("heldout-freeze", "card-issue", "prop-revise") and prop_id:
        p = f.props.get(prop_id)
        out.append(p.run if p else None)
    att = getattr(ns, "att", None)
    if verb in ("attr-confirm", "attr-reject") and att:
        a = f.atts.get(att)
        out.append(_open_run_at(events, a.seq) if a else None)
    if verb == "attr":
        patrol = env.get(PATROL_RUN_ENV)
        run = f.runs.get(patrol) if patrol else None
        out.append(patrol if run is not None and run.closed_seq is None else None)
    return out or [None]


def check(repo: Path, verb: str, ns, env: Mapping) -> list[tuple[str, str]]:
    """動詞層的授權判定（含運轉解析）：未設 `AUTOSDD_UNATTENDED` 時不讀任何帳本。"""
    if not is_set(env):
        return []
    carrier = getattr(ns, "carrier", None) if verb == "decide" else None
    if verb.replace(" ", "-") not in A_CLASS:
        return gate(verb, None, env, carrier=carrier)
    for run in owner_runs(repo, verb, ns, env):
        bad = gate(verb, run, env)
        if bad:
            return bad
    return []
