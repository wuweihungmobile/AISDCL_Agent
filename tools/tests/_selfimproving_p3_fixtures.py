# 受測面：tools/lib/selfimproving/mea.py（程式碼鎖，非散文）
"""SelfImproving P3 測試共用夾具（TCS-SelfImproving-P3 §5；底線開頭、不被收集）。

建在 P1、P2 夾具之上（呼叫形態不變，R134）；各 P3 測試檔的 `setUpModule` 呼叫 `fx.setup("si_p3_")`。
合成編號一律於執行期以字串相加組出（`pid()`、`obs_id()`、`def_id()`），測試原始碼不寫不存在於
真帳本的字面編號（NFR-P3-7）。夾具自行定義建構器與判準，不 import 被測模組的私有符號。
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock  # noqa: F401  （測試檔經夾具取 mock）

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_fixtures import (
    card_ev,
    dec_ev,
    freeze_ev,
    pid,
    promote_ev,
    prop_ev,
    sandbox_ev,
    verify_ev,
)

TA = "2026-10-10T00:00:00+00:00"
TP = "2026-10-20T10:00:00+00:00"
D3 = "docs/p3/area"
T1 = f"{D3}/t1.md"
T2 = f"{D3}/t2.md"
MEM = "memory/feedback_demo.md"
DEFLOG = fx.DEFLOG
LEDGER = fx.LEDGER
DROP = fx.DROP  # `ev()` 的哨兵：明示刪除該鍵（住 P1 夾具，compose 認得）


def _lines(n: int) -> str:
    return "".join(f"line {i:03d}\n" for i in range(1, n + 1))


BASE_EV = (
    fx.run_open_ev(1),
    fx.skip_ev(1),
    fx.ev("attr", "SA", id=fx.aid(1), type="root", obs=[fx.obs_id(2)],
          items=[["DOC", "docs/06_quality/"]], root_cause="docs/stale-note"),
    fx.ev("attr.confirm", "QA", att=fx.aid(1)),
)


def make_p3_repo(dest: Path, *, events=None, obs=(), defs=(), prm=None,
                 commit: bool = True) -> Path:
    """P2 基線 repo 加 P3 內容：錨 commit `C0`（committer 時間為 `TA`）、`migration_base_sha`、
    `docs/p3/area/*` 檔、基底事件帳本 `BASE-EV`；`params.json` 為 32 鍵。"""
    repo = fx2.make_p2_repo(dest, commit=False, events=[*BASE_EV, *(events or [])],
                            extra_obs=[list(r) for r in obs], defs=list(defs), prm=prm)
    for rel in ("t1.md", "t2.md"):
        fx.put(repo, f"{D3}/{rel}", _lines(100))
    fx.put(repo, f"{D3}/f.md", _lines(20))
    fx.put(repo, "docs/p3/areax/f.md", _lines(20))
    c0 = fx.commit_all(repo, "C0", when=TA)
    fx.set_params(repo, migration_base_sha=c0)
    _append(repo, LEDGER, fx.line([
        fx.obs_id(11), "2026-10-10 08:00 +00:00", "夾具", "遷移基準確認", f"sid {fx.UUID} line 1",
        "decision", "P3", f"decided：掌舵者確認遷移基準 {c0[:7]}",
        "面=流程;來源=人;回報者=掌舵者"]))
    if commit:
        fx.commit_all(repo, "C3")
    return repo


def p3_base() -> Path:
    """已建好的 P3 基線 repo 的複本（每個測試檔的快取只建一次）。"""
    if "p3_base" not in fx._CACHE:
        fx._CACHE["p3_base"] = make_p3_repo(fx.TMP / "p3baseline")
    dest = fx.new_dir("v")
    shutil.copytree(fx._CACHE["p3_base"], dest)
    return dest


class P3TestCase(fx2.P2TestCase):
    """P3 測試基底：P2 基底（`CLAUDE_CONFIG_DIR` 指 tmp）加 P3 的常用斷言輔助。"""

    def measure(self, R: Path, *extra: str):
        return self.M(R, "measure", *extra)

    def status(self, R: Path) -> dict:
        return self.MJ(R, "status")

    def folded(self, R: Path):
        from lib.selfimproving import events as si_events
        from lib.selfimproving import fold as si_fold

        evs = si_events.load_sound_events(R / si_events.LEDGER_REL) or []
        return si_fold.fold(evs, json.loads(fx.read(R, fx.PARAMS)).get("stop_after_bad"))

    def prop_state(self, R: Path, prop: str) -> str:
        return self.folded(R).props[prop].state


def win(R: Path) -> list[dict]:
    return [e for e in fx.EV(R) if e["kind"].startswith("mea.")]


def evl(R: Path) -> bytes:
    p = R / fx.EVL
    return p.read_bytes() if p.is_file() else b""


def porcelain(R: Path) -> set:
    """`git status --porcelain` 的路徑集合（狀態碼不計）。"""
    return {ln.split(None, 1)[-1] for ln in fx.git(R, "status", "--porcelain").splitlines()}


def fix_commit(R: Path, date: str) -> str:
    """以 `date`（ISO，帶 offset）為 committer 時間建空 commit 並回其 sha。"""
    stamp = fx.to_git_date(date)
    fx.git(R, "commit", "-q", "--allow-empty", "-m", "fix", when=stamp)
    return fx.head(R)


def ev3(kind: str, by: str = "main", **fields) -> dict:
    """x.ev 的別名（保留舊名）；值為 DROP 的鍵由 compose 刪去。"""
    return fx.ev(kind, by, **fields)


# mea.* 欄位壞值（選擇子, 鍵, 壞值, `check` 的碼）：消費端須視為「不可評估」而非 traceback
BAD_MEA = (("open", "w_opp", "x", "MEA-TYPE"), ("baseline", "opp", None, "MEA-TYPE"),
           ("baseline", "opp", 7, "MEA-TYPE"), ("baseline", "events", "x", "MEA-TYPE"),
           ("baseline", "pending", "x", "MEA-TYPE"), ("close", "n_opp", "x", "MEA-TYPE"),
           ("close", "at", "garbage", "MEA-TYPE"), ("close", "at", 5, "MEA-TYPE"),
           ("close", "result", "bogus", "MEA-ENUM"), ("open", "promote_seq", "x", "MEA-TYPE"))


def corrupt_mea(R: Path, which: str, key: str, value) -> None:
    """把事件帳本中第一筆 `which`（`baseline`、`open`、`close`）事件的 `key` 改成 `value`。"""
    def pick(e):
        if which == "baseline":
            return e["kind"] == "mea.report" and e.get("report") == "baseline"
        return e["kind"] == f"mea.{which}"
    fx2.rewrite_event(R, next(e["seq"] for e in fx.EV(R) if pick(e)), **{key: value})


# --------------------------------------------------------------------------- OBS 與 DEF 列
def _append(R: Path, rel: str, line: str) -> None:
    text = fx.read(R, rel)
    fx.put(R, rel, text + ("" if text.endswith("\n") else "\n") + line + "\n")


def obs_at(R: Path, n: int, when: str, path: str, *, reopens: str | None = None,
           evidence: str | None = None, disp: str = "open") -> str:
    """附加一列合法 OBS 並回其 ID；`when`＝`YYYY-MM-DD HH:MM [+00:00]`，證據座標為 `<path>:<行號>`
    （`evidence` 給了就逐字取代整格）。"""
    marks = "面=產品;來源=代理;回報者=QA" + (f";reopens={reopens}" if reopens else "")
    row = [fx.obs_id(n), when, "夾具", f"P3 夾具症狀 {n}", evidence or f"{path}:{n % 19 + 1}",
           "bug", "P3", disp, marks]
    _append(R, LEDGER, fx.line(row))
    return fx.obs_id(n)


def def_at(R: Path, n: int, date: str, path: str, *, status: str = "open",
           evidence: str | None = None) -> str:
    """附加一列缺陷帳本主檔的 DEF 列並回其 ID（`n` 為序數）。"""
    ident = fx.def_id(100 + n)
    _append(R, DEFLOG, fx.line([ident, date, "夾具", evidence or f"{path}:{n % 19 + 1}", "P3", "-",
                                status]))
    return ident


# --------------------------------------------------------------------------- attr 與 promoted
def _next(R: Path, kind: str, key: str) -> int:
    nums = [int(e[key].rsplit("-", 1)[1]) for e in fx.EV(R) if e["kind"] == kind]
    return max(nums, default=0) + 1


def root_attr(R: Path, obs_ids, key: str, *, confirm: bool = True) -> str:
    """手寫 root `attr`（提出者 `SA`）與其 `attr.confirm`（確認者 `QA`）；回 `ATT` 編號。"""
    att = fx.aid(_next(R, "attr", "id"))
    events = [fx.ev("attr", "SA", id=att, type="root", obs=list(obs_ids),
                    items=[["DOC", "docs/06_quality/"]], root_cause=key)]
    if confirm:
        events.append(fx.ev("attr.confirm", "QA", att=att))
    fx.append_events(R, events)
    return att


def link_attr(R: Path, from_id: str, reopened_id: str, *, settle: str | None = None) -> str:
    """手寫 link `attr` 與其落定（`settle`＝`confirm`、`reject` 或 None＝未落定）；回 ATT 編號。"""
    att = fx.aid(_next(R, "attr", "id"))
    events = [fx.ev("attr", "SA", id=att, type="link", **{"from": from_id}, reopens=reopened_id)]
    if settle == "confirm":
        events.append(fx.ev("attr.confirm", "QA", att=att))
    elif settle == "reject":
        events.append(fx.ev("attr.reject", "QA", att=att, note="夾具駁回"))
    fx.append_events(R, events)
    return att


def promoted(R: Path, *, cls: str = "D", action: str = "modify", target: str | list = T1,
             sources=None, t: str = TP, ack: bool = False) -> str:
    """手寫一個 promoted PROP（內容檔 `rN.patch`、`rN.md` 與事件一致；`rollback` 欄為字面
    `還原該行`）；`t`＝`app.promote.t`。回 PROP 號。"""
    n = _next(R, "prop", "id")
    sources = list(sources) if sources else [fx.obs_id(2)]
    targets = [target] if isinstance(target, str) else list(target)
    patch = fx.patch_join(*[fx.patch_add(x, ["p3 夾具"]) for x in targets])
    fields = {"rollback": "還原該行"}
    if cls == "M":
        fields["source_obs"] = sources[0]
    body = fx.body_md("M" if cls == "M" else "P", **fields)
    d = R / fx.PROPS_REL / pid(n)
    d.mkdir(parents=True, exist_ok=True)
    (d / "r1.patch").write_bytes(patch)
    (d / "r1.md").write_bytes(body.encode("utf-8"))
    touched = sorted(targets)
    extra = {"preimage": {x: fx.H(5) for x in touched}} if cls == "M" else {}
    prop = prop_ev(n, 1, cls=cls, action=action, target=targets, sources=sources,
                   touched_count=len(touched),
                   touched_sha256=fx.sha(json.dumps(touched, ensure_ascii=False,
                                                    separators=(",", ":")).encode("utf-8")),
                   patch_sha256=fx.sha(patch), body_sha256=fx.sha(body.encode("utf-8")), **extra)
    flags = ["unverified_ack"] if ack else []
    vfile = b"{}\n"
    if not ack:
        (d / "verify1.json").write_bytes(vfile)
    vkw = {} if ack else {"verify_sha256": fx.sha(vfile)}
    chain = [prop, card_ev(n), dec_ev(n, "approve"), freeze_ev(n), sandbox_ev(n),
             verify_ev(n, "NE" if ack else "PASS", **vkw),
             dec_ev(n, "promote", **({"flags": flags} if ack else {})),
             promote_ev(n, t=t, **({"unverified_ack": True} if ack else {}))]
    fx.append_events(R, chain)
    return pid(n)


def promote_seq(R: Path, prop: str) -> int:
    return next(e["seq"] for e in fx.EV(R) if e["kind"] == "app.promote" and e["prop"] == prop)


def mea_chain(R: Path, prop: str, result: str, *, ev: int = 2, opp: int = 5, n_opp: int = 5,
              at: str | None = None, amend=None, stop_at: str | None = None) -> int:
    """為已晉升的 PROP 手寫 baseline、`mea.open`、`mea.close`（與選用的 `mea.amend`）；回
    `mea.close` 的 `seq`。`stop_at` 為 `baseline` 或 `open` 時只寫到該處（回其 `seq`）。"""
    sp = promote_seq(R, prop)
    prm = json.loads(fx.read(R, fx.PARAMS))
    base = fx.ev("mea.report", "main", prop=prop, report="baseline", promote_seq=sp,
                 opp=[fx.obs_id(800 + i) for i in range(opp)], events=ev, pending=0,
                 w_opp=prm["w_opp"], w_evt=prm["w_evt"], w_min=prm["w_min"], anchor=TA)
    chain = [base]
    if stop_at != "baseline":
        chain.append(fx.ev("mea.open", "main", prop=prop, w_opp=prm["w_opp"], promote_seq=sp))
    if stop_at is None:
        chain.append(fx.ev("mea.close", "main", prop=prop, result=result, n_opp=n_opp,
                           at=at or "2026-10-25T00:00:00+00:00"))
    objs = fx.append_events(R, chain)
    seq = objs[-1]["seq"]
    if amend and stop_at is None:
        fx.append_events(R, [fx.ev("mea.amend", "main", prop=prop, window=seq,
                                   **{"from": amend[0], "to": amend[1]}, cause=amend[2])])
    return seq


# --------------------------------------------------------------------------- 情境（§5.2）
def _t(day: int, hm: str) -> str:
    return f"2026-10-{day:02d} {hm} +00:00"


def s_base(R: Path, pre=None, **promo) -> dict:
    """S-BASE：b1～b9 與單一 PROP `P`（於 `TP` 晉升）；b3、b5 的 link 已確認、b9 的未落定，
    其 `seq` 皆小於晉升的 `seq`。回 `{"P": …, "b": {1: ID…}, "att": {…}}`。"""
    s1 = fx.obs_id(2)
    spec = {1: (9, "12:00"), 2: (11, "09:00"), 3: (12, "09:00"), 4: (13, "09:00"),
            5: (14, "09:00"), 6: (15, "09:00"), 7: (16, "09:00"), 8: (17, "09:00"),
            9: (18, "09:00")}
    b = {}
    for k, (day, hm) in spec.items():
        b[k] = obs_at(R, 20 + k, _t(day, hm), f"{D3}/f.md", reopens=s1 if k in (3, 5, 9) else None)
    att = {3: link_attr(R, b[3], s1, settle="confirm"), 5: link_attr(R, b[5], s1, settle="confirm"),
           9: link_attr(R, b[9], s1)}
    if pre is not None:
        pre(R, b)
    return {"P": promoted(R, **promo), "b": b, "att": att}


def s_adopt(R: Path, upto: int = 6) -> dict:
    """S-ADOPT：a1～a6（a5 為 DEF 列，發現日期 2026-10-25）；`upto` 限制列數。"""
    a = {}
    plan = {1: (21, "09:00"), 2: (22, "09:00"), 3: (23, "08:00"), 4: (24, "09:00"),
            6: (26, "09:00")}
    for k, (day, hm) in plan.items():
        if k <= upto:
            a[k] = obs_at(R, 30 + k, _t(day, hm), f"{D3}/f.md")
    if upto >= 5:
        a[5] = def_at(R, 5, "2026-10-25", f"{D3}/f.md")
    return a


def s_rec(R: Path) -> dict:
    s = s_base(R)
    a1 = obs_at(R, 31, _t(21, "09:00"), f"{D3}/f.md")
    r1 = obs_at(R, 40, _t(23, "09:00"), f"{D3}/f.md", reopens=fx.obs_id(2))
    s.update(a={1: a1}, r1=r1, att_r1=link_attr(R, r1, fx.obs_id(2), settle="confirm"))
    return s


def s_pend(R: Path) -> dict:
    s = s_base(R)
    s["a"] = s_adopt(R, 5)
    s["c1"] = obs_at(R, 41, _t(22, "12:00"), f"{D3}/f.md", reopens=fx.obs_id(2))
    s["att_c1"] = link_attr(R, s["c1"], fx.obs_id(2))
    return s


def run_checked(self, R: Path, *argv):
    """`M` 加 rc 為 0 的斷言；回輸出。"""
    rc, out, err = self.M(R, *argv)
    self.assertEqual(rc, 0, f"{argv} -> {out}{err}")
    return out


def re_first(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    assert m, (pattern, text)
    return m.group(1)


def cap_index(entries: int, *, total_bytes: int | None = None, eol: str = "\n",
              trail: int = 0) -> bytes:
    """記憶索引位元組：2 行表頭（`# Memory` 與空行）加 `entries` 個 50 位元組（不含行尾）條目行。"""
    lines = ["# Memory", ""]
    for i in range(1, entries + 1):
        head = f"- e{i:02d} "
        lines.append(head + "x" * (50 - len(head)))
    for k in range(1, min(entries, 5) + 1 if trail else 1):
        lines[-k] += " " * trail
    out = eol.join(lines) + eol
    if total_bytes is not None and entries:
        diff = total_bytes - len(out.encode("utf-8"))
        lines[-1] = lines[-1] + "x" * diff if diff > 0 else lines[-1][:diff]
        out = eol.join(lines) + eol
    return out.encode("utf-8")


def parse_t(text: str) -> datetime:
    return datetime.fromisoformat(text)

# --------------------------------------------------------------------------- 真 CLI 的提案建構器
def _old_text(R: Path, target: str) -> str:
    if (R / target).is_file():
        return (R / target).read_text(encoding="utf-8")
    return _lines(100 if target in (T1, T2) else 20)


def try_prop(R: Path, run: str, *, cls: str = "D", action: str = "add", target: str = T1,
             sources=None, body_over=None, body_drop=(), extra_args=()):
    """以真 `prop-new` 建 PROP；回 `(rc, stdout, stderr, PROP 號或 None)`。patch 為 `add`＝新增檔、
    其餘 action＝於 `target` 第 1 行之後插入一行；本文由 `fx.body_md` 組成。"""
    patch = (fx.patch_add(target, ["p3 夾具"]) if action == "add"
             else fx.patch_insert(target, 1, ["p3 夾具"], old=_old_text(R, target)))
    body = fx.body_md("M" if cls == "M" else "P", drop=body_drop, **(body_over or {}))
    args = fx.good_prop_args(R, cls, patch=patch, target=[target], action=action,
                             sources=list(sources or [fx.obs_id(2)]), body=body)
    rc, out, err = fx2.cli(R, "prop-new", "--run", run, *args, *extra_args)
    m = re.search(r"id=(\S+)", out)
    return rc, out, err, (m.group(1) if rc == 0 and m else None)


def try_revise(R: Path, run: str, prop: str, *, body_over=None, body_drop=()):
    """對態為 `returned` 的 PROP 呼叫 `prop-revise`（patch 沿原 rev）；回 (rc, stdout, stderr)。"""
    patch = (R / fx.PROPS_REL / prop / "r1.patch").read_bytes()
    body = fx.body_md("P", drop=body_drop, **(body_over or {}))
    args = fx.revise_args(R, "P", patch=patch, body=body)
    return fx2.cli(R, "prop-revise", "--run", run, "--prop", prop, *args)


def real_promoted(R: Path, *, rollback: str = "還原該行", target: str = fx2.DEMO) -> str:
    """真 `prop-new`（D 類、`modify`、`target`）加手寫事件推到 `promoted`；回 PROP 號。"""
    run = fx2.open_run(R)
    patch = fx2._modify_patch(target)
    args = fx.good_prop_args(R, "D", patch=patch, target=[target], action="modify",
                             body=fx.body_md("P", rollback=rollback))
    rc, out, err = fx2.cli(R, "prop-new", "--run", run, *args)
    assert rc == 0, out + err
    prop = re.search(r"id=(\S+)", out).group(1)
    fx2.issue_card(R, prop)
    fx2.hand_to(R, prop, "promoted")
    return prop


def susp_events(R: Path, results=("recurred", "rolled-back")) -> list[str]:
    """S-SUSP：每個結果一個 promoted PROP 加 `mea_chain`，運轉 1 之後開運轉 2 再接其餘窗。
    回 PROP 號。"""
    out = []
    for i, res in enumerate(results):
        if i == 1:
            fx.append_events(R, [fx.run_open_ev(2), fx.skip_ev(2)])
        p = promoted(R, target=f"{D3}/s{i}.md")
        mea_chain(R, p, res, n_opp=5 if res == "clean" else 2)
        out.append(p)
    return out


# --------------------------------------------------------------------------- 事件帳本的整體改寫
def rewrite_events(R: Path, fn) -> None:
    """讀出事件帳本（事件 dict 清單）、經 `fn(list) -> list` 改寫、重排 `seq` 後寫回。"""
    evs = fn(fx.EV(R))
    for i, e in enumerate(evs, start=1):
        e["seq"] = i
    fx.put(R, fx.EVL, "".join(fx.dumps_line(e) + "\n" for e in evs))


def drop_key(R: Path, seq: int, key: str) -> None:
    """刪去事件帳本第 `seq` 行的一個鍵（保留其餘鍵序）。"""
    def fn(evs):
        for e in evs:
            if e["seq"] == seq:
                del e[key]
        return evs
    rewrite_events(R, fn)


def check_event(**over) -> dict:
    """合規的 `mea.report`（`report` 為 `check`）事件（不含 seq、t、by）；`over` 覆寫各鍵。"""
    ev = {"kind": "mea.report", "report": "check", "fingerprint": fx.H(7), "metrics_rev": 1,
          "windows": 0, "m1_n": 0, "m1": None, "m4": None, "m5_main": None, "m5_all": None,
          "m5_n": 0, "falsified": None, "missing": ["no-evaluable-window"]}
    ev.update(over)
    return ev


# ------------------------------------------------------------------------ S-PROBE-A、S-FALS、S-M23
def _hand_prop(R: Path, target: str, sources, cls: str = "D") -> str:
    """只手寫 `prop` 事件（無內容檔；用於不跑 `check` 的情境）。"""
    n = _next(R, "prop", "id")
    fx.append_events(R, [prop_ev(n, 1, cls=cls, target=[target], sources=list(sources))])
    return pid(n)


def s_probe_a(R: Path, count: int = 8) -> dict:
    """S-PROBE-A：八個 PROP（各自根因鍵 `k/p<i>`、來源 `OBS-SI-<i+2>`），窗與基線如 §5.2 表；
    `count` 小於 8 時只建前 `count` 個。"""
    spec = [("clean", 2, 5, {}), ("recurred", 3, 5, {"n_opp": 2}), ("clean", 1, 5, {}),
            ("clean", 2, 4, {}), ("pending", 2, 5, {}), ("rolled-back", 2, 5, {"n_opp": 2}),
            ("clean", 2, 5, {}), (None, 2, 5, {})]
    props = []
    for i, (res, ev, opp, kw) in enumerate(spec[:count], start=1):
        src = fx.obs_id(i + 2)
        root_attr(R, [src], f"k/p{i}")
        p = promoted(R, target=f"{D3}/p{i}.md", sources=[src], ack=(i == 6))
        if res is None:
            mea_chain(R, p, "clean", ev=ev, opp=opp, stop_at="open")
        else:
            mea_chain(R, p, res, ev=ev, opp=opp, **kw)
        if i == 6:
            fx.append_events(R, [fx.dec_ev(int(p[-3:]), "rollback",
                                           decided_at="2026-10-25T00:00:00+00:00")])
        props.append(p)
    return {"props": props}


def s_cooldown(R: Path) -> dict:
    """冷卻繞過組：被否決的 `Q1` 與其後同型的 `Q2`（`fold` 得一筆 `COOLDOWN-BYPASS-SUSPECT`）。"""
    src = fx.obs_id(9)
    root_attr(R, [src], "k/q")
    q1 = _hand_prop(R, f"{D3}/q.md", [src])
    fx.append_events(R, [fx.dec_ev(int(q1[-3:]), "reject", reason_class="證據不足")])
    q2 = _hand_prop(R, f"{D3}/q.md", [src])
    return {"q1": q1, "q2": q2}


def s_fals(R: Path, only: tuple = ()) -> list[str]:
    """S-FALS：八個窗 W1～W8（根因鍵 `k/x`、`k/y`、`k/z`）；`only` 非空時只建指定序號的窗。"""
    keys = ["k/x", "k/x", "k/x", "k/y", "k/y", "k/y", "k/z", "k/z"]
    results = ["recurred", "pending", "recurred", "recurred", "clean", "recurred", "recurred",
               "recurred"]
    out = []
    for i in range(8):
        if only and i + 1 not in only:
            continue
        src = fx.obs_id(i + 3)
        root_attr(R, [src], keys[i])
        p = promoted(R, target=f"{D3}/w{i + 1}.md", sources=[src])
        mea_chain(R, p, results[i], ev=1 if i == 6 else 2, n_opp=2 if results[i] == "recurred"
                  else 5)
        out.append(p)
    return out


def s_m23(R: Path) -> None:
    """S-M23：五個 `fixed@` DEF 列（發現日期 9/20～9/24，修復 commit 於 +3～+7 日）與一個
    `closed-by-decision` 列；發現日期皆早於錨。"""
    for k in range(5):
        found = f"2026-09-{20 + k}"
        when = datetime.fromisoformat(f"{found}T12:00:00+00:00")
        fixed = when + timedelta(days=3 + k)
        sha = fix_commit(R, fixed.isoformat())
        def_at(R, 60 + k, found, f"{D3}/f.md", status=f"fixed@{sha[:12]}")
    def_at(R, 70, "2026-09-25", f"{D3}/f.md", status="closed-by-decision")

def s_churn(R: Path, upto: int = 6, *, tr: str | None = None) -> dict:
    """S-CHURN：群（`target` 為 `T1`、根因鍵 `k/c`）的 A1、R1、A2、R2、A3、R3p 依序晉升（`upto` 限制
    個數；`tr` 覆寫 R1 的晉升時刻）與證據列 `c1`（鍵 `k/c`）、`c2`（鍵 `k/other`）、`n1`。"""
    c1 = obs_at(R, 21, "2026-10-11 09:00 +00:00", "", evidence=f"{D3}/f.md:3")
    root_attr(R, [c1], "k/c")
    c2 = obs_at(R, 22, "2026-10-11 10:00 +00:00", "", evidence=f"{D3}/f.md:4")
    root_attr(R, [c2], "k/other")
    steps = [("add", "12"), ("retire", "13"), ("add", "14"), ("retire", "15"), ("add", "16"),
             ("retire", "17")]
    props = []
    for i, (action, day) in enumerate(steps[:upto]):
        when = tr if (tr and i == 1) else f"2026-10-{day}T10:00:00+00:00"
        props.append(promoted(R, action=action, target=T1, sources=[c1], t=when))
    n1 = obs_at(R, 23, "2026-10-18 09:00 +00:00", "", evidence=f"{D3}/f.md:9")
    return {"c1": c1, "c2": c2, "n1": n1, "props": props}
