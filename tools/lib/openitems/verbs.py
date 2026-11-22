"""`tools/openitems.py` 的動詞實作（A1：open／close／convert／retire／list／check／scan）。

入口檔只分派；判準與輸出格式在這裡。rc：0＝已執行；1＝`check`／`close` 的檢查不成立（帳本不變）；
2＝輸入不合 schema／範圍／證據（帳本不變）；3＝環境（params.json 讀不到等）。
`--root` 指向含 `docs/06_quality/` 的根（預設＝本 repo；沙盒 E2E 與單元測試用，真行程照常跑）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from lib import endurance_env

from . import drive, driver_run, evidence, liveness, scan, schedcache
from . import ledger as oi_ledger
from . import params as oi_params
from .fold import fold

sched_isolation = drive.sched_isolation  # 同一個模組物件（tools/lib 的 sys.path 由 drive 備妥）
_REPO = Path(__file__).resolve().parents[3]
_ENV_RC = 3
_DRIVE_RC = 4  # 排程沒有成立（載具缺／憑證空）：帳本不變


def _by(raw: str | None) -> str:
    if raw:
        return raw
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    return f"sid:{sid}" if sid else "human"


def _find(events: list[dict], params: dict, item_id: str) -> dict:
    item = fold(events, params, datetime.now().astimezone()).items.get(item_id)
    if item is None:
        raise oi_ledger.Reject([f"找不到 {item_id}"])
    return item


def _live(item: dict) -> dict:
    if item["state"] in ("closed", "retired"):
        raise oi_ledger.Reject([f"{item['id']} 已是 {item['state']}，不可再操作"])
    return item


def _json_arg(raw: str | None, name: str):
    try:
        return json.loads(raw) if raw else None
    except ValueError as exc:
        raise oi_ledger.Reject([f"--{name} 不是合法 JSON"]) from exc


def _do_open(a, params, now) -> list[dict]:
    def make(events: list[dict]) -> list[dict]:
        ev = {"ev": "open", "id": oi_ledger.next_id(events), "by": _by(a.by), "title": a.title,
              "source": a.source, "scope": a.scope, "kind": a.kind}
        for key, val in (("check", _json_arg(a.check, "check")), ("due", a.due),
                         ("why_not_auto", a.why_not_auto)):
            if val is not None:
                ev[key] = val
        return [ev]
    return oi_ledger.append(a.root, make)


def _do_close(a, params, now) -> list[dict]:
    def make(events: list[dict]) -> list[dict]:
        item = _live(_find(events, params, a.id))
        if item["kind"] in ("human", "k1"):
            if a.by != "human":
                raise oi_ledger.Reject([f"{item['kind']} 項目只能 --by human 結案"])
            ok, why = evidence.human_proof(a.evidence or "", a.projects_dir)
            if not ok:
                raise oi_ledger.Reject([why])
            proof = why
        else:
            ok, proof = evidence.run_check(item, a.root, now)
            if not ok:
                raise _CheckFailed(proof)
            proof = a.evidence or proof
        return [{"ev": "close", "id": a.id, "by": _by(a.by), "evidence": proof}]
    return oi_ledger.append(a.root, make)


class _CheckFailed(Exception):
    pass


def _do_convert(a, params, now) -> list[dict]:
    def make(events: list[dict]) -> list[dict]:
        item = _live(_find(events, params, a.id))
        ev = {"ev": "convert", "id": a.id, "by": _by(a.by), "kind": a.kind, "why": a.why}
        check, due = _json_arg(a.check, "check"), a.due
        if check is not None:
            ev["check"] = check
        if due is not None:
            ev["due"] = due
        if a.kind in ("auto", "observe") and not (check or item["check"]):
            raise oi_ledger.Reject([f"轉成 {a.kind} 必須給 --check（原項目沒有）"])
        if a.kind == "observe" and not (due or item["due"]):
            raise oi_ledger.Reject(["轉成 observe 必須給 --due"])
        if a.kind == "human" and len((a.why or "").strip()) < oi_ledger.WHY_MIN_CHARS:
            raise oi_ledger.Reject([f"轉成 human 的 --why 至少 {oi_ledger.WHY_MIN_CHARS} 字"])
        return [ev]
    return oi_ledger.append(a.root, make)


def _do_retire(a, params, now) -> list[dict]:
    def make(events: list[dict]) -> list[dict]:
        _live(_find(events, params, a.id))
        return [{"ev": "retire", "id": a.id, "by": _by(a.by), "why": a.why, "basis": a.basis}]
    return oi_ledger.append(a.root, make)


def _waited_windows(events: list[dict], item_id: str) -> int:
    """資訊欄：這列因 window_cap 排隊過幾個窗（DES §3.3 末；不作閘門）。"""
    return sum(1 for e in events if e["id"] == item_id and e["ev"] == "attempt"
               and e.get("reason") == "window_cap")


def _do_list(a, params, now) -> int:
    events, bad = oi_ledger.read_events(oi_params.ledger_path(a.root))
    if a.verify and schedcache.refresh(params, schedcache.select_backend(), now) is None:
        sys.stderr.write("list --verify：排程列舉量不到（依帳本判定，不覆蓋舊快取）\n")
    folded = fold(events, params, now, sched_exists=schedcache.exists_fn(params, now),
                  run_alive=liveness.default_run_alive(now))
    rows = [i for i in folded.items.values() if i["undriven"] or not a.undriven]
    if a.json:
        sys.stdout.write(json.dumps(rows, ensure_ascii=False, default=str, indent=1) + "\n")
    else:
        for i in rows:
            flag = f" undriven({i['undriven_reason']})" if i["undriven"] else ""
            queued = _waited_windows(events, i["id"])
            wait = f" queued_windows={queued}" if queued else ""
            head = f"{i['id']}  {i['state']:<9} {i['kind']:<7} {i['title']}"
            sys.stdout.write(f"{head}{flag}{wait}\n")
    sys.stdout.write(f"OPENITEMS_LIST total={len(folded.items)} "
                     f"undriven={len(folded.undriven())} bad={bad} orphans={folded.orphans}\n")
    return 0


def _do_check(a, params, now) -> int:
    events, bad = oi_ledger.read_events(oi_params.ledger_path(a.root))
    if not a.id:  # 無 --id＝帳本體檢
        sys.stdout.write(f"OPENITEMS_CHECK bad={bad}\n")
        return 0 if bad == 0 else 1
    item = fold(events, params, now).items.get(a.id)
    if item is None:
        sys.stderr.write(f"找不到 {a.id}\n")
        return 2
    if item["state"] == "closed":
        sys.stdout.write(f"OPENITEMS_CHECK id={a.id} result=closed\n")
        return 0
    ok, why = evidence.run_check(item, a.root, now)
    sys.stdout.write(f"OPENITEMS_CHECK id={a.id} result={'pass' if ok else 'fail'} {why}\n")
    return 0 if ok else 1


def _do_drive(a, params, now) -> int:
    at = oi_ledger.parse_ts(a.at) if a.at else None
    if a.at and at is None:
        sys.stderr.write("--at 必須是帶 offset 的 ISO 時間\n")
        return 2
    try:
        ev = drive.drive_item(a.root, params, a.id, backend=schedcache.select_backend(), now=now,
                              by=_by(a.by), at=at)
    except oi_ledger.Reject as exc:
        sys.stderr.write("拒收（帳本未變動）：" + "；".join(exc.problems) + "\n")
        return 2
    except drive.DriveRefused as exc:  # 副作用隔離拒絕登記：理由已由 register_gate 印出並落痕跡
        return exc.rc
    except drive.DriveFailed as exc:
        sys.stderr.write(f"驅動器沒有掛上（帳本未變動）：{exc}\n")
        return _DRIVE_RC
    sys.stdout.write(f"drive {a.id} task={ev['task']} at={ev['at']}\n"
                     f"OPENITEMS_DRIVE=ok id={a.id} credential={ev['credential']}\n")
    return 0


def _do_run_driver(a, params, now) -> int:
    deps = driver_run.Deps(backend=schedcache.select_backend())
    # DES S3 到點首判（REQ-SE-14）：沙盒租約過期／主人已死／家已刪 ⇒ 不執行案例、自拆排程、落痕跡
    if (refused := sched_isolation.tick_gate(a.root, "openitems.run_driver", a.task,
                                             sched_isolation.jsonl_trace())) is not None:
        if a.task and deps.backend is not None:
            deps.backend.unregister(a.task)
        return refused
    if Path(a.root).resolve() == _REPO:  # stale-pass 只對真 repo 有意義（沙盒根沒有案例 SOURCES）
        deps.stale = drive.stale_pass
    line = driver_run.run_driver(a.root, params, a.id, a.task, deps)
    if sys.stdout is not None:  # pythonw（排程載具）沒有 stdout；判決已寫進帳本與 driver log
        sys.stdout.write(line + "\n")
    return 0


def _do_scan(a, params, now) -> int:
    if a.stale_pass:
        for new_id in drive.stale_pass(a.root, params, now):
            sys.stdout.write(f"stale-pass 開列 {new_id}\n")
        return 0
    hits = scan.scan(a.root, params)
    for h in hits:
        sys.stdout.write(f"{'mapped  ' if h.mapped else 'UNMAPPED'} {h.path}:{h.line}: {h.text}\n")
    sys.stdout.write(scan.summary_line(hits) + "\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="openitems", description="未結項登記簿 OIR")
    ap.add_argument("--root", type=Path, default=_REPO, help="根目錄（預設本 repo）")
    ap.add_argument("--trace-dir", dest="trace_dir", help="覆寫 AUTOSDD_TRACE_DIR")
    sub = ap.add_subparsers(dest="verb", required=True)
    o = sub.add_parser("open", help="立案")
    for flag in ("title", "source", "scope"):
        o.add_argument(f"--{flag}", required=True)
    o.add_argument("--kind", required=True)
    o.add_argument("--check", help='JSON：{"realverify":"RV-x"} 或 {"argv":[…],"pass":"rc0"}')
    o.add_argument("--due")
    o.add_argument("--why-not-auto", dest="why_not_auto")
    c = sub.add_parser("close", help="結案")
    c.add_argument("id")
    c.add_argument("--evidence")
    c.add_argument("--projects-dir", type=Path, dest="projects_dir")
    v = sub.add_parser("convert", help="改型")
    v.add_argument("id")
    v.add_argument("--kind", required=True)
    v.add_argument("--why", required=True)
    v.add_argument("--check")
    v.add_argument("--due")
    r = sub.add_parser("retire", help="依設計不做")
    r.add_argument("id")
    r.add_argument("--why", required=True)
    r.add_argument("--basis", required=True)
    for p in (o, c, v, r):
        p.add_argument("--by", help="human｜sid:<id>｜driver:<名>（預設取 CLAUDE_CODE_SESSION_ID）")
    ls = sub.add_parser("list", help="列出現態")
    ls.add_argument("--undriven", action="store_true")
    ls.add_argument("--json", action="store_true")
    ls.add_argument("--verify", action="store_true", help="先做一次批次排程列舉並刷新快取")
    ck = sub.add_parser("check", help="評估 check（--id）或帳本體檢")
    ck.add_argument("--id")
    sc = sub.add_parser("scan", help="掃待驗標記是否帶 OI id（唯讀）；--stale-pass 才會開列")
    sc.add_argument("--stale-pass", action="store_true", dest="stale_pass")
    dv = sub.add_parser("drive", help="替 auto／observe 項目掛一次性排程驅動器（回讀憑證）")
    dv.add_argument("id")
    dv.add_argument("--at", help="期望觸發時刻（帶 offset 的 ISO；預設現在＋2 分，observe＝due）")
    dv.add_argument("--by")
    rd = sub.add_parser("run-driver", help="（排程呼叫）執行一次驅動器")
    rd.add_argument("id")
    rd.add_argument("--task", help="觸發本次執行的排程工作名（用完即刪）")
    return ap


_WRITERS = {"open": _do_open, "close": _do_close, "convert": _do_convert, "retire": _do_retire}
_READERS = {"list": _do_list, "check": _do_check, "scan": _do_scan, "drive": _do_drive,
            "run-driver": _do_run_driver}


def main(argv: list[str] | None = None) -> int:
    # DES S3 REQ-SE-22：入口最先套用 `--job-env`（排程 job 不繼承登記者環境，居所靠它過邊界）
    a = _parser().parse_args(endurance_env.apply_job_env_or_exit(
        list(sys.argv[1:] if argv is None else argv)))
    a.root = Path(a.root)
    if a.trace_dir:
        os.environ["AUTOSDD_TRACE_DIR"] = a.trace_dir
    now = datetime.now().astimezone()
    try:
        params = oi_params.load(a.root)
    except oi_params.ParamError as exc:
        sys.stderr.write(f"{exc}\n")
        return _ENV_RC
    if a.verb in _READERS:
        return _READERS[a.verb](a, params, now)
    try:
        written = _WRITERS[a.verb](a, params, now)
    except oi_ledger.Reject as exc:
        sys.stderr.write("拒收（帳本未變動）：" + "；".join(exc.problems) + "\n")
        return 2
    except _CheckFailed as exc:
        sys.stderr.write(f"check 不成立，未結案：{exc}\n")
        return 1
    for ev in written:
        sys.stdout.write(f"{ev['ev']} {ev['id']}\n")
    return 0
