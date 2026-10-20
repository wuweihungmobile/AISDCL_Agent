"""SelfImproving 寫入動詞：run-open／run-close／attr*／prop-new／prop-revise／research --skip
（TCS-SelfImproving-P1 R27～R33、R47～R57）。

能力類別 `rw`：判準呼叫 `ro` 模組（`props`、`card`、`fold`…）、寫入只經 `evwrite`／`propfiles`；
一次成功寫入恰追加一行事件。每個動詞回 `Out(rc, text)`，用法錯誤（rc 3）拋 `UsageError`。
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from lib import sdd_latest

from . import card as si_card
from . import check as si_check
from . import events as si_events
from . import evwrite, propfiles
from . import fold as si_fold
from . import git as si_git
from . import params as si_params
from . import paths as si_paths
from . import props as si_props
from . import refs as si_refs
from . import rows as si_rows
from .git import Git
from .ledger import max_valid_id, parse_ledger

_EVENT_KEY = "event_max_bytes"
PROP_KEYS = ("max_proposals_per_run", "max_revisions", "stop_after_bad", _EVENT_KEY,
             "non_evolvable_globs", "spec_body_globs", "max_touch_ratio", "max_new_entries",
             "max_archive_entries_per_card", "card_line_max")
_MAX_CODES = 5


# 用法或輸入格式錯誤（rc 3；stdout 空、stderr 以 selfimproving: 起頭、零寫入）
UsageError = si_check.InputError
params_for = si_check.params_for


@dataclass
class Out:
    rc: int
    text: str


def ok_text(kind: str, seq: int, ident: str | None, extras: list, as_json: bool) -> str:
    if as_json:
        obj = {"ok": True, "kind": kind, "seq": seq, "id": ident, **dict(extras)}
        return json.dumps(obj, ensure_ascii=False) + "\n"

    def fmt(v) -> str:
        return "true" if v is True else str(v)
    parts = [f"ok {kind} seq={seq}"] + ([f"id={ident}"] if ident else [])
    return " ".join(parts + [f"{k}={fmt(v)}" for k, v in extras]) + "\n"


def obs_top(repo: Path) -> int:
    text = si_refs.obs_ledger_text(repo)
    return max_valid_id(parse_ledger(text)) if text else 0


def draft_for(repo: Path, verb: str, codes: list, num: int | None = None, rc: int = 1,
              symptom: str | None = None) -> str:
    names = list(dict.fromkeys(c for c, _ in codes))
    shown = "、".join(names[:_MAX_CODES]) + (f"…等 {len(names)} 項" if len(names) > _MAX_CODES
                                           else "")
    return si_rows.draft_row(
        num if num is not None else obs_top(repo) + 1, f"si {verb}（自動草稿）",
        symptom or f"si {verb} 拒收（rc={rc}）：{shown}",
        f"`python tools/selfimproving.py {verb}` rc={rc}", f"si-{verb}")


def reject(repo: Path, verb: str, codes: list, as_json: bool, drafts: list | None = None,
           extra: dict | None = None) -> Out:
    drafts = drafts or [draft_for(repo, verb, codes)]
    if as_json:
        obj = {"ok": False, "rc": 1, "verb": verb,
               "codes": [{"code": c, "detail": d} for c, d in codes], "obs_draft": drafts[0],
               **(extra or {})}
        return Out(1, json.dumps(obj, ensure_ascii=False) + "\n")
    names = ",".join(dict.fromkeys(c for c, _ in codes))
    lines = [f"reject {verb} {names}"] + [f"  {c} {' '.join(d.split())}".rstrip() for c, d in codes]
    return Out(1, "\n".join(lines + ["obs-draft:"] + drafts) + "\n")


def append(repo: Path, verb: str, build, params: dict, as_json: bool, render) -> Out:
    """寫入鎖內追加一筆事件：Reject／LockBusy 轉 rc 1 的拒收輸出；成功依 render(event) 輸出。"""
    ledger = repo / si_events.LEDGER_REL
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    try:
        ev = evwrite.append_event(ledger, evwrite.lock_path_for(si, ledger), build,
                                  max_bytes=params[_EVENT_KEY])
    except evwrite.Reject as exc:
        return reject(repo, verb, exc.codes, as_json)
    except evwrite.LockBusyError as exc:
        return reject(repo, verb, [("LOCK-BUSY", str(exc))], as_json)
    except OSError as exc:
        raise UsageError(f"事件追加失敗（{exc.__class__.__name__}），帳本未變動") from exc
    return Out(0, render(ev))


def _next_num(events: list, kind: str, key: str, prefix: str) -> int:
    nums = [int(e[key][len(prefix):]) for e in events if e.get("kind") == kind
            and isinstance(e.get(key), str) and e[key].startswith(prefix)
            and e[key][len(prefix):].isascii() and e[key][len(prefix):].isdigit()]
    return max(nums, default=0) + 1


def _label(value: str, what: str) -> None:
    if not si_events.valid_by(value):
        raise UsageError(f"{what} 須為非空、無空白、≤32 字元的標籤")


def run_open(repo: Path, trigger: str, coords: list[str], by: str, as_json: bool) -> Out:
    _label(by, "--by")
    params = params_for(repo, _EVENT_KEY)
    bad = [(("COORD-NONE", c)) for c in coords if not si_rows.has_coord(c)]
    head = Git(repo).head()
    if head is None:
        bad.append(("GIT-UNAVAILABLE", "git 不可用或無 commit，無法記 head_sha"))
    if bad:
        return reject(repo, "run-open", bad, as_json)

    def build(state):
        rid = f"RUN-SI-{_next_num(state.events, 'run.open', 'run', 'RUN-SI-'):03d}"
        return {"kind": "run.open", "by": by, "run": rid, "trigger": trigger, "coords": coords,
                "head_sha": head}
    return append(repo, "run-open", build, params, as_json,
                  lambda e: ok_text("run.open", e["seq"], e["run"], [("head_sha", head)], as_json))


def run_close(repo: Path, run: str, by: str, as_json: bool) -> Out:
    _label(by, "--by")
    if not si_events.RUN_RE.match(run):
        raise UsageError("--run 須為 RUN-SI-NNN")
    params = params_for(repo, _EVENT_KEY)

    def build(state):
        f = si_fold.fold(state.events)
        r = f.runs.get(run)
        if r is None or r.closed_seq is not None:
            raise evwrite.Reject([("RUN-NOT-OPEN", f"{run} 不是已開未關的運轉")])
        ev = {"kind": "run.close", "by": by, "run": run}
        if r.prop_ids:
            ev["outcomes"] = {pid: f.props[pid].state for pid in r.prop_ids}
        else:
            ev["no_event"] = True
        return ev

    def render(e):
        extra = [("no_event", True)] if "no_event" in e else [("outcomes", len(e["outcomes"]))]
        return ok_text("run.close", e["seq"], None, [("run", run), *extra], as_json)
    return append(repo, "run-close", build, params, as_json, render)


def _known_ids(repo: Path) -> tuple[dict, set]:
    return si_refs.obs_rows(repo), si_refs.def_ids(repo)


def _item_codes(items: list[tuple[str, str]]) -> list:
    out = []
    for kind, coord in items:
        if kind == "NONE":
            if not coord.startswith("無法歸因"):
                out.append(("ATTR-NONE-TEXT", "NONE 的值須以「無法歸因」起頭，不得猜測補位"))
        elif not si_rows.has_coord(coord):
            out.append(("COORD-NONE", f"座標不可定位：{coord}"))
    return out


def attr(repo: Path, ns, as_json: bool) -> Out:
    _label(ns.by, "--by")
    params = params_for(repo, _EVENT_KEY)
    obs, defs_known = _known_ids(repo)
    codes: list = []
    if ns.type == "root":
        if ns.from_obs or ns.reopens or not (ns.obs and ns.item and ns.root_cause):
            raise UsageError("attr root 須帶 --obs／--item／--root-cause，不得帶 --from／--reopens")
        items = []
        for raw in ns.item:
            kind, sep, coord = raw.partition("=")
            if not sep or kind not in si_events.ITEM_KINDS:
                raise UsageError(f"--item 須為 <種類>=<座標>，種類∈{list(si_events.ITEM_KINDS)}")
            items.append((kind, coord))
        codes += [("OBS-NOT-FOUND", f"{o} 不在 OBS 帳本") for o in ns.obs if o not in obs]
        codes += _item_codes(items)
        if not si_events.ROOT_CAUSE_RE.match(ns.root_cause):
            codes.append(("ROOT-CAUSE-FORMAT", "根因鍵須為 <面>/<機制>（小寫連字號）"))
        body = {"type": "root", "obs": ns.obs, "items": [list(i) for i in items],
                "root_cause": ns.root_cause}
    else:
        if ns.obs or ns.item or ns.root_cause or not (ns.from_obs and ns.reopens):
            raise UsageError("attr link 須帶 --from／--reopens，不得帶 --obs／--item／--root-cause")
        closed = si_refs.closed_rows(repo, si_refs.obs_ledger_text(repo) or "")
        if ns.from_obs not in obs:
            codes.append(("OBS-NOT-FOUND", f"{ns.from_obs} 不在 OBS 帳本"))
        if ns.reopens not in closed:
            known = ns.reopens in obs or ns.reopens in defs_known
            codes.append(("REOPENS-NOT-CLOSED" if known else "REOPENS-NOT-FOUND",
                          f"{ns.reopens} 不是已結列"))
        body = {"type": "link", "from": ns.from_obs, "reopens": ns.reopens}
    if codes:
        return reject(repo, "attr", codes, as_json)

    def build(state):
        aid = f"ATT-SI-{_next_num(state.events, 'attr', 'id', 'ATT-SI-'):03d}"
        return {"kind": "attr", "by": ns.by, "id": aid, **body}
    return append(repo, "attr", build, params, as_json,
                  lambda e: ok_text("attr", e["seq"], e["id"], [("type", e["type"])], as_json))


def attr_settle(repo: Path, kind: str, att: str, by: str, note: str | None, as_json: bool) -> Out:
    _label(by, "--by")
    if not si_events.ATT_RE.match(att):
        raise UsageError("--att 須為 ATT-SI-NNN")
    if kind == "attr.reject" and not (note and 1 <= len(note) <= 120 and "\n" not in note):
        raise UsageError("attr-reject 的 --note 須為 1～120 字元、無換行的一句理由")
    params = params_for(repo, _EVENT_KEY)

    def build(state):
        a = si_fold.fold(state.events).atts.get(att)
        if a is None:
            raise evwrite.Reject([("ATT-NOT-FOUND", f"{att} 不存在")])
        codes = []
        if a.settled is not None:
            codes.append(("ALREADY-SETTLED", f"{att} 已落定"))
        if by == a.by:
            codes.append(("CONFIRMER-IS-PROPOSER", "確認者不得等於提出者"))
        if codes:
            raise evwrite.Reject(codes)
        return {"kind": kind, "by": by, "att": att, **({"note": note} if note else {})}
    return append(repo, "attr-" + kind.split(".")[1], build, params, as_json,
                  lambda e: ok_text(kind, e["seq"], None, [("att", att)], as_json))


def research_skip(repo: Path, ns, as_json: bool) -> Out:
    note = ns.note or ""
    if not (1 <= len(note) <= 120 and "\n" not in note and "\r" not in note):
        raise UsageError("--note 須為 1～120 字元、無換行的一行")
    extra = {"quota-band": {"band"}, "helmsman": {"sid", "line"}, "offline": set()}[ns.reason]
    given = {k for k in ("band", "sid", "line") if getattr(ns, k) is not None}
    if given != extra:
        raise UsageError(f"--reason {ns.reason} 的附帶旗標須恰為 {sorted(extra) or '無'}")
    if ns.band is not None and ns.band.strip().lower() in ("", "free"):
        raise UsageError("--band 不得為 free")
    if ns.sid is not None and not si_events.valid_uuid(ns.sid):
        raise UsageError("--sid 須為 UUID")
    if ns.line is not None and ns.line < 1:
        raise UsageError("--line 須為整數 ≥1")
    params = params_for(repo, _EVENT_KEY)

    def build(state):
        f = si_fold.fold(state.events)
        r = f.runs.get(ns.run)
        if r is None or r.closed_seq is not None:
            raise evwrite.Reject([("RUN-NOT-OPEN", f"{ns.run} 不是已開未關的運轉")])
        if any(run == ns.run for _, _, run, _ in f.research_events):
            raise evwrite.Reject([("RESEARCH-ALREADY", f"{ns.run} 已有研究事件")])
        ev = {"kind": "research.skip", "by": "main", "run": ns.run, "reason": ns.reason,
              "note": note}
        ev.update({k: getattr(ns, k) for k in ("band", "sid", "line") if k in extra})
        return ev
    return append(repo, "research", build, params, as_json, lambda e: ok_text(
        "research.skip", e["seq"], None, [("run", ns.run), ("reason", ns.reason)], as_json))


def latest_name(repo: Path) -> str | None:
    """LATEST 版本名；解析失敗＝None＝整個 `AISDLC_SDD_v*/**` 視為凍結（fail-closed，不當機）。"""
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # 不在 repo 內留 __pycache__
    try:
        return sdd_latest.resolve_latest_name_fast(repo / "AISDLC_SDD")
    except Exception:  # noqa: BLE001  # fail-closed：任何解析失敗皆視為凍結
        return None
    finally:
        sys.dont_write_bytecode = keep


def _line_count(text: str | None) -> int | None:
    return None if text is None else len(text.split("\n")) - (1 if text.endswith("\n") else 0)


def _prop_stage1(repo: Path, git: Git, ns, cls: str) -> tuple[list, dict, list, bytes, str]:
    try:
        patch = Path(ns.patch_file).read_bytes()
        body = Path(ns.body_file).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError(f"patch／本文讀不到或非 UTF-8（{type(exc).__name__}）") from exc
    codes, fields, blocks = si_props.input_problems(patch, body, cls)
    if not git.available or git.head() is None:
        codes.append(("GIT-UNAVAILABLE", "git 不可用或無 commit，無法取 base"))
    elif blocks:
        try:
            seen = si_git.apply_numstat(repo, Path(ns.patch_file))
        except OSError:  # git 自己解析不了＝超集檢查無從進行：fail-closed，不當成「git 沒看到路徑」
            codes.append(("PATCH-PARSE", "git apply --numstat 無法解析此 patch（超集檢查失敗）"))
        else:
            mine = {p.replace("\\", "/") for b in blocks for p in b.paths}
            miss = sorted({p.replace("\\", "/") for p in seen} - mine)
            if miss:
                codes.append(("PATCH-PATH-MISMATCH", "git 看見而解析器漏掉：" + "、".join(miss)))
    return codes, fields, blocks, patch, body


def prop(repo: Path, ns, as_json: bool, revise: bool) -> Out:
    verb = "prop-revise" if revise else "prop-new"
    params = params_for(repo, *PROP_KEYS)
    _label(ns.proposer, "--proposer")
    if ns.reviewer is not None:
        _label(ns.reviewer, "--reviewer")
    targets = sorted(set(getattr(ns, "target", None) or []))
    for t in targets:
        if not t or si_paths.alias_reason(t):
            raise UsageError(f"--target 不得為別名形態或空：{t!r}")
    if ns.memory_dir is not None and not Path(ns.memory_dir).is_dir():
        raise UsageError(f"--memory-dir 不是目錄：{ns.memory_dir}")
    git = Git(repo)
    cls = ns.cls if not revise else None
    if revise:
        pre = si_fold.fold(si_events.load_sound_events(repo / si_events.LEDGER_REL) or [])
        if ns.prop not in pre.props:
            return reject(repo, verb, [("PROP-NOT-FOUND", f"{ns.prop} 不存在")], as_json)
        cls = pre.props[ns.prop].cls
    codes, fields, blocks, patch, body = _prop_stage1(repo, git, ns, cls)
    if codes:
        return reject(repo, verb, codes, as_json)
    head = git.head()
    obs, defs_known = _known_ids(repo)
    prd = repo / si_params.PRD_REL
    groups = si_props.glob_groups(prd.read_text(encoding="utf-8") if prd.is_file() else "")
    latest = latest_name(repo)
    touched = sorted({p for b in blocks for p in b.paths})

    def resolve(ident: str):
        if ident in obs:
            return "外部衍生" not in si_rows.row_marks(obs[ident])
        return True if ident in defs_known else None

    def base_lines() -> dict:
        if cls == "M":
            return {t: _line_count(_mem_text(ns.memory_dir, t)) for t in touched}
        return {t: _line_count(git.show(head, t)) for t in touched if not si_paths.alias_reason(t)}

    def build(state):
        f = si_fold.fold(state.events, params["stop_after_bad"])
        out: list = []
        p0 = f.props.get(ns.prop) if revise else None
        if revise:
            if p0 is None:
                raise evwrite.Reject([("PROP-NOT-FOUND", f"{ns.prop} 不存在")])
            if p0.state != "returned":
                out.append(("TRANSITION-ILLEGAL", f"{p0.id} 為 {p0.state}，只收 returned"))
            if p0.rev + 1 > params["max_revisions"] + 1:
                out.append(("REV-LIMIT", f"修訂已達上限（rev {p0.rev}，max_revisions "
                                         f"{params['max_revisions']}）"))
        cur_cls = p0.cls if revise else ns.cls
        ctx = si_props.Ctx(
            cls=cur_cls, action=p0.action if revise else ns.action,
            targets=list(p0.target) if revise else targets,
            sources=list(p0.sources) if revise else list(ns.source), run=ns.run,
            proposer=ns.proposer, reviewer=ns.reviewer, handoff=ns.handoff, fields=fields,
            blocks=blocks, params=params, folded=f, repo_real=str(repo.resolve()),
            latest_name=latest, groups=groups, base_lines=base_lines(),
            base_text=lambda path: git.show(head, path), resolve=resolve,
            memory_dir_ok=(ns.memory_dir is not None) or cur_cls != "M",
            self_prop=ns.prop if revise else None, events=state.events)
        d = si_props.evaluate(ctx)
        out += d.codes
        if revise:
            pid, rev = p0.id, p0.rev + 1
        else:
            nums = [int(e["id"].rsplit("-", 1)[1]) for e in state.events
                    if e.get("kind") == "prop" and isinstance(e.get("id"), str)
                    and si_events.PROP_RE.match(e["id"])]
            pid, rev = f"PROP-SI-{max([_obs_prop_max(repo), *nums]) + 1:03d}", 1
        patch_rel, body_rel = propfiles.rel_paths(pid, rev)
        if (repo / patch_rel).exists() or (repo / body_rel).exists():
            out.append(("PROP-FILE-EXISTS", f"{pid} r{rev} 的內容檔已存在，不得覆寫"))
        p_sha, b_sha = si_props.sha256_of(patch), si_props.body_sha256(body)
        digest = si_props.compute_digest(
            pid=pid, rev=rev, cls=d.cls, action=ctx.action, target=ctx.targets,
            touched=d.touched, base=head, preimage=d.preimage, patch_sha=p_sha, body_sha=b_sha,
            fields=fields)
        sim = si_fold.Prop(id=pid, rev=rev, state="proposed", route=d.route, cls=d.cls,
                           action=ctx.action, target=ctx.targets, sources=ctx.sources, run=ns.run,
                           digest=digest, created_seq=0, last_seq=0)
        card = si_card.assemble(
            repo, git, f, {"cls": d.cls, "action": ctx.action, "target": ctx.targets,
                           "digest": digest, "touched_count": len(d.touched), "route": d.route,
                           "sources": ctx.sources, "base": head},
            sim, blocks, d.touched, fields, patch, body, params, check=False)
        out += si_card.layout_problems(card.core, params["card_line_max"])
        event = {"kind": "prop", "by": ns.proposer, "id": pid, "rev": rev, "run": ns.run,
                 "base": head, "cls": d.cls, "action": ctx.action, "route": d.route,
                 "target": ctx.targets, "touched_count": len(d.touched),
                 "touched_sha256": si_paths.touched_sha256(d.touched), "patch_sha256": p_sha,
                 "body_sha256": b_sha, "digest": digest, "sources": ctx.sources,
                 "proposer": ns.proposer, "reviewer": ns.reviewer,
                 **({"preimage": d.preimage} if d.cls == "M" else {})}
        line = evwrite.render_line(state.last_seq + 1, event)
        if len(line.encode("utf-8")) > params[_EVENT_KEY]:
            size = len(line.encode("utf-8"))
            out.append(("EVENT-BYTES-OVER", f"prop 事件行 {size} 位元組超過上限，請拆分提案"))
        if out:
            raise evwrite.Reject(out)
        created = propfiles.write(repo, pid, rev, patch, body)
        state.cleanups.append(lambda: propfiles.remove(created))
        return event

    def render(e):
        dig = e["digest"] if as_json else e["digest"].split(":", 1)[1][:8]
        extra = [("rev", e["rev"]), ("route", e["route"]), ("cls", e["cls"]), ("digest", dig),
                 ("touched_count", e["touched_count"])]
        if as_json:
            extra.append(("files", list(propfiles.rel_paths(e["id"], e["rev"]))))
        return ok_text("prop", e["seq"], e["id"], extra, as_json)
    return append(repo, verb, build, params, as_json, render)


def _obs_prop_max(repo: Path) -> int:
    """觀察帳本（含 archive）引用過的最大 PROP 號；配號時在寫入鎖內讀（R32 (c)）。"""
    obs_text = "\n".join(
        (repo / "docs/06_quality" / n).read_text(encoding="utf-8", errors="replace")
        for n in _obs_files(repo))
    return max((int(m) for m in re.findall(r"PROP-SI-(\d+)", obs_text)), default=0)


def _obs_files(repo: Path) -> list[str]:
    q = repo / "docs/06_quality"
    if not q.is_dir():
        return []
    names = ["SelfImproving_Observation_Ledger.md"] + sorted(
        p.name for p in q.glob("SelfImproving_Observation_Ledger_archive*.md"))
    return [n for n in names if (q / n).is_file()]


def _mem_text(memory_dir: str | None, logical: str) -> str | None:
    if memory_dir is None or logical[:7].casefold() != "memory/":  # 合法根比對亦 casefold（R52）
        return None
    p = Path(memory_dir) / logical[len("memory/"):]
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
