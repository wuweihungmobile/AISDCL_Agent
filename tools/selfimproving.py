"""SelfImproving 命令列入口（薄殼：只組 argparse 與分派，判準全在 `lib/selfimproving/`）。

用法：python tools/selfimproving.py <動詞> [旗標]。P1 的 13 個動詞：`check`（唯讀檢查帳本與協定）、
`status`／`scan`／`card`／`export`（唯讀）、`run-open`／`run-close`／`attr`／`attr-confirm`／
`attr-reject`／`prop-new`／`prop-revise`／`research`（寫入事件帳本），加 P2 的 `decide` 等八個動詞
與 `card --issue`；P3 加 `measure`（寫 `mea.*`）與 `capacity`（唯讀）；議題中心加 `issues`（唯讀），
共 24 個；未列動詞 rc 3。
rc：唯讀非閘門動詞 0＝已執行、3＝無法執行；寫入動詞 0＝已寫、1＝拒收（未寫）、3＝用法或輸入錯誤，
`research --fetch` 另有 2＝事件已寫而至少一個來源失敗；`check` 沿 P0（0／1／2／3）。
規格＝docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md、…-P1-20261020.md。
`writeverbs`、`research` 只在 handler 內延遲 import：唯讀動詞行程不載入寫入與網路碼。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作，本檔不另寫
from lib.selfimproving import card, check, export, issues, scan, status
from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving.git import Git

_REPO = Path(__file__).resolve().parents[1]
_USAGE_ERROR_RC = 3
_ITEM_CLS = ("M", "P", "R", "D", "evaluator-change", "loop-self")
_HELP = {
    "check": "檢查觀察帳本、協定參數與歷史（唯讀）", "status": "啟動事件偵測與狀態摘要（唯讀）",
    "scan": "模組體檢的確定性半（唯讀、離線）", "card": "提案卡面（唯讀）",
    "export": "唯讀匯出（JSON）", "run-open": "開運轉", "run-close": "關運轉",
    "attr": "歸因", "attr-confirm": "確認歸因", "attr-reject": "駁回歸因",
    "prop-new": "新增提案", "prop-revise": "修訂被退回的提案", "research": "研究掃描或免掃",
    "decide": "把掌舵者的決定記成 DEC（自逐字稿或 Console 稽核檔驗證）",
    "heldout-freeze": "凍結 held-out 評估集（提案者以外的角色）",
    "sandbox": "核准後的提案套用到樹外的隔離沙盒",
    "verify": "三步對照驗證（RED→GREEN→突變 RED）與三態判定",
    "promote": "把已驗證且已獲晉升決定的提案合入正式面（不 commit）",
    "rollback": "把已晉升的提案逐位元還原（不 commit）",
    "obs-add": "Console 稽核檔入帳為一列 OBS（或 --dry-run 預檢）",
    "obs-close": "Console 稽核檔把一個 open 的 OBS 列關成終值",
    "measure": "採納後量測窗：基線、開窗、關窗、更正與回滾提案卡（只追加 mea.* 事件）",
    "capacity": "有上限載入面的容量與截斷風險（唯讀）",
    "issues": "議題中心：三類帳本的中文議題清單（唯讀）",
}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        sys.stderr.write(f"selfimproving: 用法錯誤：{message}\n")
        self.print_usage(sys.stderr)
        sys.exit(_USAGE_ERROR_RC)


def _verb(sub, name: str, *, json_flag: bool = True) -> argparse.ArgumentParser:
    p = sub.add_parser(name, help=_HELP[name], allow_abbrev=False)
    p.add_argument("--repo", help="repo 根目錄（預設為本檔所在 repo）")
    if json_flag:
        p.add_argument("--json", action="store_true", help="輸出 JSON")
    return p


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="selfimproving", description="SelfImproving 自我進化機制 CLI",
                     allow_abbrev=False)
    sub = parser.add_subparsers(dest="verb", required=True, metavar="<verb>", parser_class=_Parser)
    chk = _verb(sub, "check")
    chk.add_argument("--ledger", help="觀察帳本檔（相對路徑相對於 repo）")
    chk.add_argument("--params", help="params.json（相對路徑相對於 repo）")
    _verb(sub, "status")
    _verb(sub, "scan").add_argument("--since", help="起算 commit（7～40 位 hex）")
    cd = _verb(sub, "card")
    cd.add_argument("prop", help="PROP-SI-NNN")
    cd.add_argument("--issue", action="store_true", help="記 card 事件（寫入）")
    cd.add_argument("--by", default="main")
    exp = _verb(sub, "export")
    exp.add_argument("--kind", choices=export.KINDS, required=True)
    exp.add_argument("--since", type=int)
    exp.add_argument("--limit", type=int)
    exp.add_argument("--id")
    exp.add_argument("--status", help="只配 --kind issues：狀態名或「待處理」，逗號取聯集")
    exp.add_argument("--source", help="只配 --kind issues：來源名，逗號取聯集")
    iss = _verb(sub, "issues")
    iss.add_argument("--status", help="狀態名或「待處理」，逗號取聯集")
    iss.add_argument("--source", help="來源名，逗號取聯集")
    iss.add_argument("--since", type=int)
    iss.add_argument("--limit", type=int)
    ro = _verb(sub, "run-open")
    ro.add_argument("--trigger", choices=list("abcde"), required=True)
    ro.add_argument("--coord", action="append", required=True)
    ro.add_argument("--by", required=True)
    rc = _verb(sub, "run-close")
    rc.add_argument("--run", required=True)
    rc.add_argument("--by", required=True)
    at = _verb(sub, "attr")
    at.add_argument("--type", choices=("root", "link"), required=True)
    at.add_argument("--by", required=True)
    at.add_argument("--obs", action="append")
    at.add_argument("--item", action="append")
    at.add_argument("--root-cause", dest="root_cause")
    at.add_argument("--from", dest="from_obs")
    at.add_argument("--reopens")
    for name in ("attr-confirm", "attr-reject"):
        p = _verb(sub, name)
        p.add_argument("--att", required=True)
        p.add_argument("--by", required=True)
    sub.choices["attr-reject"].add_argument("--note", required=True)
    for name in ("prop-new", "prop-revise"):
        p = _verb(sub, name)
        p.add_argument("--run", required=True)
        p.add_argument("--patch-file", dest="patch_file", required=True)
        p.add_argument("--body-file", dest="body_file", required=True)
        p.add_argument("--proposer", required=True)
        p.add_argument("--reviewer")
        p.add_argument("--handoff", choices=("DEF", "R", "T1", "PRD"))
        p.add_argument("--memory-dir", dest="memory_dir")
    pn = sub.choices["prop-new"]
    pn.add_argument("--cls", choices=_ITEM_CLS, required=True)
    pn.add_argument("--action", choices=("add", "modify", "delete", "retire"), required=True)
    pn.add_argument("--target", action="append", required=True)
    pn.add_argument("--source", action="append", required=True)
    sub.choices["prop-revise"].add_argument("--prop", required=True)
    dc = _verb(sub, "decide")
    dc.add_argument("id", help="PROP-SI-NNN 或 RUN-SI-NNN")
    dc.add_argument("--kind", choices=si_events.DKINDS)
    dc.add_argument("--sid")
    dc.add_argument("--line", type=int)
    dc.add_argument("--reason-class", dest="reason_class", choices=si_events.REASON_CLASSES)
    dc.add_argument("--carrier", choices=("console",))
    dc.add_argument("--audit-ref", dest="audit_ref")
    dc.add_argument("--by", default="main")
    hf = _verb(sub, "heldout-freeze")
    hf.add_argument("prop", help="PROP-SI-NNN")
    hf.add_argument("--from", dest="src", required=True)
    hf.add_argument("--by", required=True)
    sb = _verb(sub, "sandbox")
    sb.add_argument("prop", help="PROP-SI-NNN")
    sb.add_argument("--memory-dir", dest="memory_dir")
    sb.add_argument("--by", default="main")
    vf = _verb(sub, "verify")
    vf.add_argument("prop", help="PROP-SI-NNN")
    vf.add_argument("--mutation")
    vf.add_argument("--memory-dir", dest="memory_dir")  # M 類沙盒樹重建用（R88 勘誤三）
    vf.add_argument("--by", default="main")
    for name in ("promote", "rollback"):
        pr = _verb(sub, name)
        pr.add_argument("prop", help="PROP-SI-NNN")
        pr.add_argument("--memory-dir", dest="memory_dir")
        pr.add_argument("--by", default="main")
    for name in ("obs-add", "obs-close"):
        ob = _verb(sub, name)
        ob.add_argument("--carrier", choices=("console",))
        ob.add_argument("--audit-ref", dest="audit_ref")
        ob.add_argument("--by", default="main")
    oa = sub.choices["obs-add"]
    oa.add_argument("--dry-run", dest="dry_run", action="store_true")
    oa.add_argument("--body-file", dest="body_file")
    ms = _verb(sub, "measure")
    ms.add_argument("--by", default="main")
    ms.add_argument("--record-check", dest="record_check", action="store_true")
    cp = _verb(sub, "capacity")
    cp.add_argument("--memory-index", dest="memory_index")
    cp.add_argument("--kb-metrics", dest="kb_metrics")
    cp.add_argument("--prefs")
    rs = _verb(sub, "research")
    mode = rs.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch", action="store_true")
    mode.add_argument("--skip", action="store_true")
    rs.add_argument("--run", required=True)
    rs.add_argument("--reason", choices=("quota-band", "offline", "helmsman"))
    rs.add_argument("--note")
    rs.add_argument("--band")
    rs.add_argument("--sid")
    rs.add_argument("--line", type=int)
    return parser


def _emit(text: str) -> None:
    buf = getattr(sys.stdout, "buffer", None)
    if buf is None:
        sys.stdout.write(text)
        return
    sys.stdout.flush()
    buf.write(text.encode("utf-8"))  # 位元組直寫：Windows 文字模式不把 LF 變 CRLF
    buf.flush()


def _under(repo: Path, value: str | None, default_rel: str) -> Path:
    p = Path(value) if value else Path(default_rel)
    return p if p.is_absolute() else repo / p


def _check(repo: Path, args: argparse.Namespace) -> int:
    ledger = _under(repo, args.ledger, check.LEDGER_REL)
    params_path = _under(repo, args.params, check.PARAMS_REL)
    text, size = check.read_text(ledger, "ledger")
    params = check.load_params(params_path)
    res = check.run_check(repo, ledger, params, text, size)
    _emit(check.render_json(res) if args.json else check.render_text(res))
    return res.rc


def _status(repo: Path, args: argparse.Namespace) -> int:
    from lib.selfimproving import capacity  # ro：status 的 capacity 軸只讀所需鍵（R131）

    params = check.params_for(repo, *capacity.PARAM_KEYS, *status.MEASURE_KEYS)
    obj = status.build(repo, Git(repo), params)
    _emit(status.render_json(obj) if args.json else status.render_text(obj))
    return 0


def _scan(repo: Path, args: argparse.Namespace) -> int:
    git = Git(repo)
    if args.since is not None and not (
            7 <= len(args.since) <= 40 and all(c in "0123456789abcdefABCDEF" for c in args.since)
            and git.is_commit(args.since)):
        raise check.InputError("--since 只收 commit（7～40 位 hex，且須可解析為 commit）")
    res = scan.run(repo, git, check.params_for(repo, "row_max_bytes"), args.since)
    _emit(scan.render_json(res) if args.json else scan.render_text(res))
    return 0


def _card(repo: Path, args: argparse.Namespace) -> int:
    if args.issue:
        from lib.selfimproving import decwrite

        out = decwrite.issue_card(repo, args, args.json)
        _emit(out.text)
        sys.stderr.write(out.err)
        return out.rc
    git = Git(repo)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    try:
        res = card.build(repo, git, events, si_fold.fold(events), args.prop, check.params_for(repo))
    except card.CardError as exc:
        raise check.InputError(f"{exc.code} {exc.detail}".strip()) from exc
    if args.json:
        obj = {"schema_rev": 1, "prop": res.prop, "rev": res.rev, "digest": res.digest,
               "core_lines": res.core_lines, "text": res.text, "parsed": res.parsed}
        _emit(json.dumps(obj, ensure_ascii=False) + "\n")
    else:
        _emit(res.text)
    return 0


def _export(repo: Path, args: argparse.Namespace) -> int:
    params = check.params_for(repo, "export_limit_max")
    bad = (not args.json
           or (args.since is not None and (args.since < 0 or args.kind == "status"))
           or (args.limit is not None and not 1 <= args.limit <= params["export_limit_max"]))
    if args.id is not None:
        pat = {"proposals": si_events.PROP_RE, "runs": si_events.RUN_RE,
               "issues": issues.ID_RE}.get(args.kind)
        bad = bad or pat is None or not pat.match(args.id)
    filtered = args.status is not None or args.source is not None
    if bad or (filtered and (args.kind != "issues" or args.id is not None)):
        raise check.InputError("export 旗標不合：須 --json、--kind；--since ≥0 且不與 status 併用；"
                               "--limit 介於 1 與上限；--id 只配 proposals／runs／issues；"
                               "--status／--source 只配 --kind issues 且不與 --id 併用")
    try:
        statuses, sources = issues.parse_filters(args.status, args.source)
    except ValueError as exc:
        raise check.InputError(str(exc)) from exc
    obj = export.build(repo, Git(repo), params, args.kind, args.since, args.limit, args.id,
                       statuses, sources)
    _emit(export.render(obj))
    return 0


def _issues(repo: Path, args: argparse.Namespace) -> int:
    params = check.params_for(repo, "export_limit_max")
    if (args.since is not None and args.since < 0) or (
            args.limit is not None and not 1 <= args.limit <= params["export_limit_max"]):
        raise check.InputError("issues 旗標不合：--since ≥0；--limit 介於 1 與上限")
    try:
        statuses, sources = issues.parse_filters(args.status, args.source)
    except ValueError as exc:
        raise check.InputError(str(exc)) from exc
    obj = issues.build(repo, Git(repo), params, since=args.since, limit=args.limit,
                       statuses=statuses, sources=sources)
    _emit(export.render(obj) if args.json else issues.render_text(obj, statuses))
    return 0


def _write(repo: Path, args: argparse.Namespace) -> int:
    from lib.selfimproving import writeverbs as wv

    verb, js = args.verb, args.json
    if verb == "run-open":
        out = wv.run_open(repo, args.trigger, args.coord, args.by, js)
    elif verb == "run-close":
        out = wv.run_close(repo, args.run, args.by, js)
    elif verb == "attr":
        out = wv.attr(repo, args, js)
    elif verb in ("attr-confirm", "attr-reject"):
        out = wv.attr_settle(repo, verb.replace("-", "."), args.att, args.by,
                             getattr(args, "note", None), js)
    elif verb in ("prop-new", "prop-revise"):
        out = wv.prop(repo, args, js, verb == "prop-revise")
    elif verb == "decide":
        from lib.selfimproving import decwrite

        out = decwrite.decide(repo, args, js)
    elif verb in ("sandbox", "heldout-freeze"):
        from lib.selfimproving import sandbox

        out = (sandbox.run if verb == "sandbox" else sandbox.heldout_freeze)(repo, args, js)
    elif verb == "verify":
        from lib.selfimproving import verify

        out = verify.run(repo, args, js)
    elif verb in ("promote", "rollback"):
        from lib.selfimproving import promote

        out = getattr(promote, verb)(repo, args, js)
    else:
        out = _research(repo, args, wv)
    _emit(out.text)
    sys.stderr.write(getattr(out, "err", ""))
    return out.rc


def _research(repo: Path, args: argparse.Namespace, wv):
    if args.skip:
        if args.reason is None:
            raise check.InputError("research --skip 須帶 --reason")
        return wv.research_skip(repo, args, args.json)
    if any(v is not None for v in (args.reason, args.note, args.band, args.sid, args.line)):
        raise check.InputError("research --fetch 不收 --reason／--note／--band／--sid／--line")
    from lib.selfimproving import research
    return research.run_fetch(repo, args.run, args.json)


def _obs_dry_run(repo: Path, args: argparse.Namespace) -> int:
    """`obs-add --dry-run`：唯讀預檢，只走 `ro` 模組（不載入寫入類、runner、fetch、research）。"""
    from lib.selfimproving import obsrows

    if args.carrier or args.audit_ref or not args.body_file:
        raise check.InputError("--dry-run 須搭 --body-file，且不收 --carrier／--audit-ref")
    try:
        raw = (sys.stdin.buffer.read() if args.body_file == "-"
               else Path(args.body_file).read_bytes())
        body = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise check.InputError(f"--body-file 讀不到或不是 JSON（{type(exc).__name__}）") from exc
    res = obsrows.preview(repo, body, check.params_for(repo, "row_max_bytes")["row_max_bytes"])
    if args.json:
        _emit(json.dumps(res, ensure_ascii=False) + "\n")
    else:
        lines = ["dry-run ok" if res["ok"] else "dry-run reject", f"row: {res['row']}",
                 f"row_bytes={res['row_bytes']} row_max_bytes={res['row_max_bytes']}"]
        lines += [f"  {f['code']} {f['detail']}" for f in res["findings"]]
        _emit("\n".join(lines) + "\n")
    return 0 if res["ok"] else 1


def _obs_write(repo: Path, args: argparse.Namespace) -> int:
    if args.verb == "obs-add" and args.dry_run:
        return _obs_dry_run(repo, args)
    if args.verb == "obs-add" and args.body_file:
        raise check.InputError("--body-file 只配 --dry-run")
    if args.carrier != "console" or not args.audit_ref or not si_events.valid_uuid(args.audit_ref):
        raise check.InputError(f"{args.verb} 須帶 --carrier console 與 --audit-ref（UUID）")
    if not si_events.valid_by(args.by):
        raise check.InputError("--by 須為非空、無空白、≤32 字元的標籤")
    from lib.selfimproving import obswrite

    fn = obswrite.add_console_row if args.verb == "obs-add" else obswrite.close_console_row
    rc, text = fn(repo, args.audit_ref, args.by, args.json)
    _emit(text)
    return rc


def _measure(repo: Path, args: argparse.Namespace) -> int:
    from lib.selfimproving import meawrite

    res = meawrite.measure(repo, by=args.by, record_check=args.record_check, as_json=args.json)
    _emit(res.text)
    return res.rc


def _capacity(repo: Path, args: argparse.Namespace) -> int:
    from lib.selfimproving import capacity

    _emit(capacity.run(repo, args.memory_index, args.kb_metrics, args.prefs, args.json))
    return 0


_HANDLERS = {"check": _check, "status": _status, "scan": _scan, "card": _card, "export": _export,
             "obs-add": _obs_write, "obs-close": _obs_write, "measure": _measure,
             "capacity": _capacity, "issues": _issues}


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        repo = Path(args.repo) if args.repo else _REPO
        if not repo.is_dir():
            raise check.InputError(f"--repo 不是目錄：{repo}")
        return _HANDLERS.get(args.verb, _write)(repo, args)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else _USAGE_ERROR_RC)
    except check.InputError as exc:
        sys.stderr.write(f"selfimproving: {exc}\n")
        return _USAGE_ERROR_RC


if __name__ == "__main__":
    sys.exit(main())
