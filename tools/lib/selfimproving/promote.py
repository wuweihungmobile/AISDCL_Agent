"""SelfImproving `promote`／`rollback`：已驗證的 PROP 合入正式面並可逐位元還原（TCS-P2 R91、R92）。

能力類別 `rw`：只經 `Git.run` 對正式面（或 M 類的 `--memory-dir`）做 `git apply`（帶
`-c core.autocrlf=false`），
事件只經 `wv.append`。套用與事件追加同在寫入鎖內：鎖內重驗態與決定後才動樹，事件追加失敗時由
`state.cleanups` 反向套用還原（零殘留）。不 commit、不暫存（HEAD、`git log`、index 皆不變）。
M 類以 `memory/` 為邏輯根：patch 路徑 `memory/<檔>` 對映 `<memory-dir>/<檔>`（`apply -p2`）。
"""

from __future__ import annotations

from pathlib import Path

from . import decverify, evwrite, manifest
from . import events as si_events
from . import fold as si_fold
from . import paths as si_paths
from . import props as si_props
from . import sandbox as si_sandbox
from . import writeverbs as wv
from .decwrite import UsageError, ok_out, refuse_unattended
from .git import Git

_NOCRLF = ("-c", "core.autocrlf=false")
_LOGICAL_ROOT = "memory/"
_POST_PROMOTE = ("promoted", "measuring", "closed")


class _Surface:
    """正式面（repo 工作樹）或 M 類的記憶目錄（邏輯根 `memory/`）：manifest 與套用的同一入口。"""

    def __init__(self, repo: Path, cls: str, memory_dir: str | None, touched: list[str],
                 patch: Path) -> None:
        self.memory = cls == "M"
        self.root = Path(memory_dir) if self.memory and memory_dir else repo
        self.git, self.touched, self.patch = Git(self.root), touched, patch

    def manifest(self) -> str:
        return manifest.paths_manifest(self.root, self.touched,
                                       strip=_LOGICAL_ROOT if self.memory else "")

    def apply(self, *flags: str) -> bool:
        argv = (*_NOCRLF, "apply", *(("-p2",) if self.memory else ()), *flags, str(self.patch))
        cp = self.git.run(*argv)
        return bool(cp is not None and cp.returncode == 0)

    def check_failure(self) -> tuple[str, str]:
        if self.memory:
            return ("PREIMAGE-MISMATCH", "記憶目錄的目標檔與 patch 前像不符；請重新上卡"
                                         "（prop-revise／prop-new），並貼入下方 OBS 草稿列")
        return ("APPLY-FAILED", "patch 對正式面的 git apply --check 失敗（工作樹已漂移？）")


def _usage(ns) -> None:
    if not si_events.valid_by(ns.by):
        raise UsageError("--by 須為非空、無空白、≤32 字元的標籤")
    if not si_events.PROP_RE.match(ns.prop):
        raise UsageError("位置參數須為 PROP-SI-NNN")
    if ns.memory_dir is not None and not Path(ns.memory_dir).is_dir():
        raise UsageError(f"--memory-dir 不是目錄：{ns.memory_dir}")


def _prelude(repo: Path, ns, verb: str, as_json: bool):
    """回 (params, events, folded, prop, prop 事件)；前置不成立回拒收 `Out`。"""
    _usage(ns)
    refused = refuse_unattended(repo, verb, as_json)
    if refused:
        return refused
    params = wv.params_for(repo, *wv.PROP_KEYS)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events, params["stop_after_bad"])
    p = f.props.get(ns.prop)
    if p is None:
        return wv.reject(repo, verb, [("PROP-NOT-FOUND", f"{ns.prop} 不存在")], as_json)
    ev = next(e for e in reversed(events) if e["kind"] == "prop" and e["id"] == p.id
              and e["rev"] == p.rev)
    return params, events, f, p, ev


def _unconsumed(events: list, pid: str, dkind: str, consumer: str) -> list[dict]:
    """該 PROP 尚未被消費的 `dec(dkind)`（依序消費：已有 N 筆 `consumer` 事件就略過前 N 筆）。"""
    decs = [e for e in events if e["kind"] == "dec" and e.get("prop") == pid
            and e.get("dkind") == dkind]
    used = sum(1 for e in events if e["kind"] == consumer and e.get("prop") == pid)
    return decs[used:]


def _gate(repo: Path, events: list, params: dict, dec: dict | None):
    ctx = decverify.Ctx(repo, events, Git(repo), params)
    return decverify.dec_gate(ctx, dec)


def _now_hits(repo: Path, f, p, ev: dict, params: dict, patch: bytes, touched: list[str]) -> list:
    """`NON-EVOLVABLE-NOW`：與 `prop-new` 同一函式、以當下 params.json 與 LATEST 重驗全部路徑。"""
    git = Git(repo)
    ctx = si_props.Ctx(
        cls=p.cls, action=p.action, targets=list(p.target), sources=[], run="", proposer="",
        reviewer=None, handoff=None, fields={}, blocks=si_paths.parse_patch(patch), params=params,
        folded=f, repo_real=str(repo.resolve()), latest_name=wv.latest_name(repo), groups={},
        base_lines={}, base_text=lambda path: git.show(ev["base"], path), resolve=lambda _i: True)
    hit, globs = si_props.reverify_paths(ctx, touched)
    if not hit:
        return []
    where = "、".join(globs) or "合法根／別名／規格"
    return [("NON-EVOLVABLE-NOW", f"路徑 {'、'.join(touched)} 在當下參數與 LATEST 下命中不可進化面"
                                  f"（glob：{where}），改走轉交")]


def _promote_codes(repo: Path, ns, events: list, f, p, ev: dict, params: dict) -> tuple:
    """R91 前置依序判；回 (碼清單, 所消費的 dec(promote))。"""
    if p.state != "verified":
        return [("STATE-NOT-VERIFIED", f"{p.id} 為 {p.state}，只收 verified")], None
    if p.route.startswith("handoff:"):
        return [("ROUTE-HANDOFF", "handoff 路由的 PROP 不進晉升，只能轉交")], None
    pend = _unconsumed(events, p.id, "promote", "app.promote")
    if not pend:
        return [("NO-PROMOTE-DEC", "沒有尚未消費的 dec(promote)")], None
    dec = pend[-1]
    ack = "unverified_ack" in (dec.get("flags") or [])
    if not ((p.verdict == "PASS" and not ack) or (p.verdict == "NE" and ack)):
        return [("PROMOTE-FORM-MISMATCH", f"verdict {p.verdict} 與晉升式（ack={ack}）不符；"
                                          "PASS 前式、NE 後式、FAIL 不收")], None
    approve = next((e for e in reversed(events) if e["kind"] == "dec" and e.get("prop") == p.id
                    and e.get("dkind") == "approve"), None)
    now = decverify.recompute_digest(repo, ev)
    if now is None or now != ev["digest"] or any(d is not None and d.get("digest") != now
                                                 for d in (approve, dec)):
        return [("DIGEST-MISMATCH", "自 rN.patch、rN.md 重算的 digest 不同於事件或決定時者")], None
    prem = [("PROMOTE-PREMISE-ROLLBACK", "最近一筆 app.sandbox 的 rollback_ok 不為 true")] \
        if p.rollback_ok is not True else []
    prem += [("PROMOTE-PREMISE-TOUCHED", "最近一筆 app.sandbox 的 touched_ok 不為 true")] \
        if p.touched_ok is not True else []
    if prem:
        return prem, None
    patch, touched = si_sandbox.prop_context(repo, ev)
    hits = _now_hits(repo, f, p, ev, params, patch.read_bytes(), touched)
    if hits:
        return hits, None
    for each in (approve, dec):  # 引言回查放在純帳本類判準之後：其卡面重建依賴同一份事件前綴
        gate = _gate(repo, events, params, each)
        if gate:
            return [gate], None
    if p.cls == "M" and not ns.memory_dir:
        return [("MEMORY-DIR-MISSING", "M 類須給 --memory-dir")], None
    surface = _Surface(repo, p.cls, ns.memory_dir, touched, patch)
    return ([surface.check_failure()] if not surface.apply("--check") else []), dec


def _app_id(events: list) -> str:
    nums = [int(e["id"].rsplit("-", 1)[1]) for e in events if e["kind"].startswith("app.")]
    return f"APP-SI-{max(nums, default=0) + 1:03d}"


def promote(repo: Path, ns, as_json: bool):
    got = _prelude(repo, ns, "promote", as_json)
    if isinstance(got, wv.Out):
        return got
    params, events, f, p, ev = got
    codes, dec = _promote_codes(repo, ns, events, f, p, ev, params)
    if codes:
        return wv.reject(repo, "promote", codes, as_json)
    patch, touched = si_sandbox.prop_context(repo, ev)
    surface = _Surface(repo, p.cls, ns.memory_dir, touched, patch)
    ack = "unverified_ack" in (dec.get("flags") or [])

    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        cur, pend = f2.props.get(p.id), _unconsumed(state.events, p.id, "promote", "app.promote")
        if (cur is None or cur.state != "verified" or cur.digest != p.digest or not pend
                or pend[-1]["seq"] != dec["seq"]):
            raise evwrite.Reject([("STATE-CHANGED", "鎖內重驗：PROP 態、digest 或決定已變")])
        head = Git(repo).head()
        if head is None:
            raise evwrite.Reject([("GIT-UNAVAILABLE", "git 不可用或無 commit，無法記 head_sha")])
        pre = surface.manifest()
        if not surface.apply():
            raise evwrite.Reject([surface.check_failure()])
        state.cleanups.append(lambda: surface.apply("-R"))
        return {"kind": "app.promote", "by": ns.by, "id": _app_id(state.events), "prop": p.id,
                "rev": ev["rev"], "head_sha": head, "pre_sha256": pre,
                "post_sha256": surface.manifest(), "unverified_ack": ack}

    return wv.append(repo, "promote", build, params, as_json, lambda e: ok_out(
        "app.promote", e["seq"], e["id"], [("prop", p.id), ("unverified_ack", ack),
                                           ("head_sha", e["head_sha"])], as_json).text)


def _rollback_codes(repo: Path, ns, events: list, p, params: dict) -> tuple:
    """R92 前置；回 (碼清單, 所消費的 dec(rollback), 最近一筆 app.promote)。"""
    if p.state not in _POST_PROMOTE:
        return [("STATE-NOT-PROMOTED", f"{p.id} 為 {p.state}，只收 promoted／measuring／closed")], \
            None, None
    pend = _unconsumed(events, p.id, "rollback", "app.rollback")
    if not pend:
        return [("NO-ROLLBACK-DEC", "沒有尚未消費的 dec(rollback)")], None, None
    gate = _gate(repo, events, params, pend[0])
    if gate:
        return [gate], None, None
    if p.cls == "M" and not ns.memory_dir:
        return [("MEMORY-DIR-MISSING", "M 類須給 --memory-dir")], None, None
    promoted = next((e for e in reversed(events) if e["kind"] == "app.promote"
                     and e.get("prop") == p.id), None)
    return [], pend[0], promoted


def rollback(repo: Path, ns, as_json: bool):
    got = _prelude(repo, ns, "rollback", as_json)
    if isinstance(got, wv.Out):
        return got
    params, events, _f, p, ev = got
    codes, dec, promoted = _rollback_codes(repo, ns, events, p, params)
    if not codes and promoted is None:
        codes = [("STATE-NOT-PROMOTED", f"{p.id} 沒有 app.promote 事件")]
    if codes:
        return wv.reject(repo, "rollback", codes, as_json)
    patch, touched = si_sandbox.prop_context(repo, ev)
    surface = _Surface(repo, p.cls, ns.memory_dir, touched, patch)
    if surface.manifest() != promoted["post_sha256"]:
        return wv.reject(repo, "rollback", [("TREE-CHANGED", "touched 現況不等於 app.promote 的 "
                                                             "post_sha256（樹已被他處改動），改人工處理")],
                         as_json)

    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        cur, pend = f2.props.get(p.id), _unconsumed(state.events, p.id, "rollback", "app.rollback")
        if (cur is None or cur.state not in _POST_PROMOTE or not pend
                or pend[0]["seq"] != dec["seq"]):
            raise evwrite.Reject([("STATE-CHANGED", "鎖內重驗：PROP 態或決定已變")])
        before = surface.manifest()
        if before != promoted["post_sha256"]:
            raise evwrite.Reject([("TREE-CHANGED", "鎖內重驗：樹已被他處改動")])
        if not surface.apply("-R"):
            raise evwrite.Reject([("APPLY-FAILED", "反向 patch 套用失敗（零變更）")])
        after = surface.manifest()
        if after != promoted["pre_sha256"]:
            surface.apply()  # 把剛套用的反向 patch 還原回去：零變更
            raise evwrite.Reject([("ROLLBACK-NOT-EXACT", "反向套用的結果不等於 app.promote 的 "
                                                         "pre_sha256；已還原，樹仍為晉升後")])
        state.cleanups.append(lambda: surface.apply())
        return {"kind": "app.rollback", "by": ns.by, "id": _app_id(state.events), "prop": p.id,
                "rev": ev["rev"], "pre_sha256": before, "post_sha256": after}

    return wv.append(repo, "rollback", build, params, as_json, lambda e: ok_out(
        "app.rollback", e["seq"], e["id"], [("prop", p.id)], as_json).text)


__all__ = ["promote", "rollback"]
