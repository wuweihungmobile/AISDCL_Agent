# 受測面：tools/lib/selfimproving/patrolreport.py（程式碼鎖，非散文）
"""SelfImproving P7 測試共用夾具（TCS-SelfImproving-P7 §3；底線開頭、不被收集）。

建在 P1、P2、P4 夾具之上；各 P7 測試檔的 `setUpModule` 呼叫 `fx.setup("si_p7_")`。
合成編號一律於執行期
以字串相加組出（`fx.pid`、`fx.obs_id`…）。本檔供 RD（報表）棒使用的部分：手寫 PROP 事件鏈、替身
`Rig7`、黃金樣本產生器、四個範圍守衛共用的允許集合 `P7_ALLOWED`。MM、PU 棒各自追加所需建構器
（`repo_m`、`push_repo`、`run_argv_spy`）。
"""

from __future__ import annotations

import json
import re
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
from _selfimproving_p4_fixtures import P4TestCase, Rig, iso

from lib.selfimproving import manifest, patrolreport, pushguard, transcript
from lib.selfimproving import paths as si_paths

MIN = timedelta(minutes=1)
TZ8 = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 11, 12, 0, 0, tzinfo=TZ8)  # 黃金樣本的固定 now（TCS §3）
T0 = datetime(2026, 11, 10, 9, 0, 0, tzinfo=TZ8)  # 黃金樣本事件鏈的起點
GOLDEN_DIR = fx.ROOT / "tools" / "tests" / "fixtures" / "selfimproving" / "p7"
GOLDEN_PROP = fx.pid(901)

# §4 允許集合（單一來源；AT-790-4-1、AT-790-4-2 的四個範圍守衛取聯集）
P7_ALLOWED = tuple(re.compile(p) for p in (
    r"^tools/lib/selfimproving/(nextstep|propdetail|memdir|pushguard|patrolreport|patrolpush)\.py$",
    r"^tools/lib/selfimproving/(export|params|sandbox|patrol|patrolrun|patrolbrief|schedarm"
    r"|unattended|runner)\.py$",  # runner 限 AT-749-9-2 的樹終止機制（TCS-P7 E-10）
    r"^tools/selfimproving\.py$",
    r"^docs/06_quality/SelfImproving_Protocol/params\.json$",
    r"^docs/06_quality/SelfImproving_LedgerDb_P0_Baseline\.md$",
    r"^tools/tests/test_selfimproving_p7_(report|memory|push)\.py$",
    r"^tools/tests/_selfimproving_p7_fixtures\.py$",
    r"^tools/tests/fixtures/selfimproving/p7/(patrol|detail)\.golden\.json$",
    r"^tools/tests/test_selfimproving_(capability|schedule_gate|schedule_advance|schedule_patrol"
    r"|schedule_model|sandbox|check|registry|fourq_gate|backtest|export_status|events|events_p2"
    r"|p3_meta|ledgerdb_p0|issues|console_obs)\.py$",
    r"^tools/tests/_selfimproving_(fixtures|p5_fixtures|p6_fixtures)\.py$",
    r"^tools/tests/test_root_module_layout\.py$",
))
P7_FORBIDDEN = ("docs/01_requirements/SelfImproving_PRD.md",
                "docs/05_development/SelfImproving_Operations_SOP.md",
                "docs/03_testing/contracts/TCS-SelfImproving-P",
                "docs/02_architecture/Root_Layout", "tools/lib/selfimproving/fold.py",
                "tools/lib/selfimproving/writeverbs.py", ".claude/", "AgentConsole/", ".github/",
                "tools/install_windows_nightly.ps1", "tools/scheduled_task_expectations.json",
                "docs/06_quality/SelfImproving_Protocol/research_sources.json")


# --------------------------------------------------------------------------- PROP 事件鏈（手寫）
def _t(t0: datetime | None, k: int) -> dict:
    return {"t": iso(t0 + k * MIN)} if t0 is not None else {}


def prop_files(R: Path, n: int, *, rev: int = 1, target: str = "docs/notes/demo.md",
               patch: bytes | None = None, body: str | None = None) -> None:
    """提案目錄的 `r<rev>.patch`、`r<rev>.md`（內容固定；digest 不與事件綁定，卡面因此量不到）。
    供 tools/lib/selfimproving/propdetail.py 的測試使用。"""
    patch = patch if patch is not None else fx.patch_insert(
        target, 50, ["FIXED-LINE"], old=fx.fixture_files()[target])
    fx.putb(R, f"{fx.PROPS_REL}/{fx.pid(n)}/r{rev}.patch", patch)
    fx.putb(R, f"{fx.PROPS_REL}/{fx.pid(n)}/r{rev}.md",
            (body if body is not None else fx.body_md("P")).encode("utf-8"))


def prop_chain(n: int, state: str, *, run: int = 1, cases: int = 5, verdict: str = "PASS",
               sources=None, route: str = "loop", carded: bool = True, rollback: bool = False,
               sandbox: dict | None = None, verify: dict | None = None, t0=None,
               digest: str | None = None) -> list[dict]:
    """單一 PROP 到 `state` 的事件鏈（不含 `run.open`）。`state`：`proposed`、`approved`（未凍結）、
    `frozen`（已凍結、尚未沙盒）、`sandboxed`、`verified`、`decided`（verified＋晉升決定）、
    `promoted`、`measuring`、`closed`、`rejected`、`returned`。時間給 `t0` 才明寫（確定性用）。
    供 tools/lib/selfimproving/nextstep.py 與 propdetail.py 的測試使用。"""
    pid = fx.pid(n)
    src = list(sources) if sources is not None else [fx.obs_id(1), fx.obs_id(2)]
    k = iter(range(1, 99))
    ev = [fx.prop_ev(n, run, target=[f"docs/notes/n{n}.md"], sources=src, route=route,
                     **_t(t0, next(k)))]
    if state in ("rejected", "returned"):
        return [*ev, fx.dec_ev(n, "reject" if state == "rejected" else "return",
                               **_t(t0, next(k)))]
    stages = ("proposed", "approved", "frozen", "sandboxed", "verified", "decided", "promoted",
              "measuring", "closed")
    at = stages.index(state)
    if at >= 1:
        ev += [fx.card_ev(n, **_t(t0, next(k))), fx.dec_ev(n, "approve", **_t(t0, next(k)))]
    if at >= 2:
        ev.append(fx.ev("heldout.freeze", "FZ", prop=pid, n=cases, digest=digest or fx.H(7),
                        **_t(t0, next(k))))
    if at >= 3:
        ev.append(fx.sandbox_ev(n, **(sandbox or {}), **_t(t0, next(k))))
    if at >= 4:
        ev.append(fx.verify_ev(n, verdict, **(verify or {}), **_t(t0, next(k))))
        if carded:
            ev.append(fx.card_ev(n, **_t(t0, next(k))))
    if at >= 5:
        flags = {"flags": ["unverified_ack"]} if verdict == "NE" else {}
        ev.append(fx.dec_ev(n, "promote", **flags, **_t(t0, next(k))))
    if at >= 6:
        ev.append(fx.promote_ev(n, unverified_ack=verdict == "NE", **_t(t0, next(k))))
    if at >= 7:
        ev.append(fx.ev("mea.open", "main", prop=pid, **_t(t0, next(k))))
    if at >= 8:
        ev.append(fx.ev("mea.close", "main", prop=pid, **_t(t0, next(k))))
    if rollback:
        ev.append(fx.dec_ev(n, "rollback", **_t(t0, next(k))))
    return ev


def add_prop(R: Path, n: int, state: str, *, with_run: bool = True, run: int = 1, **kw) -> str:
    """把一個 PROP 的事件鏈與內容檔寫進 `R`（工作樹；不 commit）；回 PROP 號。"""
    events = []
    have = {e["run"] for e in fx.EV(R) if e["kind"] == "run.open"}
    if with_run and fx.rid(run) not in have:
        events += [fx.run_open_ev(run), fx.skip_ev(run)]
    events += prop_chain(n, state, run=run, **kw)
    fx.append_events(R, events)
    prop_files(R, n)
    return fx.pid(n)


def repo_m(case, state: str = "frozen", *, n: int = 910, mem: str = "ok", prm=None, **kw):
    """M 類版本（TCS §3）：啟用排程的基線 repo＋一個 M 類 PROP（`prop_chain` 的任一態）；
    `transcript.claude_home` 以 `mock.patch` 指向暫存（隨 `case` 清理），其下
    `projects/<slug>/memory/`
    依 `mem` 造：`ok`（含 `MEMORY.md`）、`nomd`（有目錄、無 `MEMORY.md`）、`file`（路徑是一般檔）、
    `none`（不存在）。回 `(R, 記憶目錄 Path)`；patch 取 `fx.default_patch("M")`
    （觸及 `memory/demo.md`）。"""
    R = case.enabled_repo(prm=prm)
    home = fx.new_dir("ch")
    home.mkdir()
    case.enterContext(mock.patch.object(transcript, "claude_home", return_value=home))
    base = transcript.transcript_dir(R)
    mem_dir = base / "memory"
    if mem in ("ok", "nomd"):
        fx.memory_dir(base)
        if mem == "nomd":
            (mem_dir / "MEMORY.md").unlink()
    elif mem == "file":
        base.mkdir(parents=True)
        mem_dir.write_bytes(b"not a directory")
    patch = fx.default_patch("M", fx.memory_dir(fx.new_dir("mp")))[0]
    chain = prop_chain(n, state, **kw)
    chain[0].update(cls="M", target=["memory/demo.md"], preimage={"memory/demo.md": fx.H(1)})
    have = {e["run"] for e in fx.EV(R) if e["kind"] == "run.open"}
    head = [] if fx.rid(1) in have else [fx.run_open_ev(1), fx.skip_ev(1)]
    fx.append_events(R, [*head, *chain])
    prop_files(R, n, patch=patch)
    fx.commit_all(R, "p7 m-class")
    return R, mem_dir


def base_repo(*, prm=None) -> Path:
    """P4 基線 repo（含真 SOP 範本節、九個 sched 鍵）的全新複本；PROP 另以 `add_prop` 加入。"""
    return fx4.p4_base(prm=prm)


def export_item(case, R: Path, ident: str) -> dict:
    """`export --kind proposals --id <ident> --json` 的整份物件（`case` 為 SiTestCase）。"""
    rc, out, err = case.M(R, "export", "--kind", "proposals", "--id", ident, "--json")
    case.assertEqual(rc, 0, out + err)
    return json.loads(out)


# --------------------------------------------------------------------------- 心跳替身
class Rig7(Rig):
    """`Rig` 加：推進類動詞預設回 rc 0（不真的沙盒、驗證、晉升——這些由事件夾具直接給狀態）；
    `script[verb]` 可覆寫為 `(rc, out, err)`。入帳與運轉相關動詞仍走真入口。"""

    STUBBED = ("sandbox", "verify", "promote", "rollback", "card", "measure", "run-close")

    def __init__(self, *a, script: dict | None = None, **kw) -> None:
        super().__init__(*a, **kw)
        self.script = dict(script or {})

    def _run(self, R: Path, argv: list[str]):
        if argv[0] in self.script:
            return self.script[argv[0]]
        if argv[0] in self.STUBBED:
            return 0, "", ""
        return super()._run(R, argv)


class P7TestCase(P4TestCase):
    """P7 測試基底：P4 心跳基底＋讀快照的輔助。名稱含 TestCase（discover 守門不解析跨檔基底鏈）。"""

    def report_path(self) -> Path:
        return self.home / patrolreport.REPORT_DIR / patrolreport.REPORT_NAME

    def report(self) -> dict:
        return json.loads(self.report_path().read_text(encoding="utf-8"))

    def beat7(self, R: Path, now: datetime, rig: Rig | None = None, *args: str, hm: str = "12:00"):
        return self.beat(R, now, rig or Rig7(), *args, hm=hm)


# --------------------------------------------------------------------------- 黃金樣本（裁決 11）
def dump(obj) -> bytes:
    """黃金樣本序列化：`json.dumps(ensure_ascii=False, separators=(",", ":"))`＋LF。"""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _detail_repo() -> Path:
    R = base_repo()
    t0 = T0
    events = [fx.run_open_ev(1, t=iso(t0)), fx.skip_ev(1, t=iso(t0 + MIN))]
    chain = prop_chain(901, "verified", cases=4, verdict="NE", t0=t0 + 2 * MIN,
                       digest="sha256:abcd" + "0123456789abcdef" * 3 + "0123456789ab",
                       sources=[fx.obs_id(1), fx.obs_id(11)],
                       sandbox={"applied": False, "fail_code": "SANDBOX-APPLY-TIMEOUT"},
                       verify={"probes_n": 1, "baseline_red": None, "patched_green": None,
                               "mutated_red": None, "carrier_proof": True,
                               "verify_sha256": fx.H(9), "heldout_digest": fx.H(7),
                               "reasons": ["SANDBOX-APPLY-TIMEOUT"]})
    fx.append_events(R, [*events, *chain])
    prop_files(R, 901)
    fx.commit_all(R, "p7 detail golden")
    return R


def golden_detail(case) -> bytes:
    """`export --kind proposals --id PROP-SI-901` 的 `items[0]`（固定夾具、確定性）。"""
    R = _detail_repo()
    return dump(export_item(case, R, GOLDEN_PROP)["items"][0])


def _golden_events() -> list[dict]:
    """patrol 樣本的帳本：啟用排程、一個本格已啟動的 (f) 運轉（存活）、一個等著的 Console 運轉、
    三個 PROP（verified／已凍結待沙盒／未凍結）與一筆帶稽核編號的 `sched.skip`。"""
    o = fx4.O
    ref_skip = "6f1c2a3e-8b4d-4e5f-9a7b-000000000901"
    t = T0
    ev = [fx4.sched_set_ev(o),
          fx4.sched_skip_ev(NOW - 20 * MIN, "run-open", due_at=NOW - 20 * MIN,
                            detail="已有未關運轉 " + fx.rid(5), audit_ref=ref_skip),
          fx4.run_open_f_ev(5, NOW - 120 * MIN, due_at=o + 9 * timedelta(days=1)),
          fx.skip_ev(5, t=iso(NOW - 119 * MIN)),
          fx.ev("run.open", "console", run=fx.rid(6), trigger="a", carrier="console",
                audit_ref="6f1c2a3e-8b4d-4e5f-9a7b-000000000902", audit_sha256=fx.H(6),
                key_id="00000000", decider="admin", coords=["console_audit/x.json"],
                t=iso(NOW - 30 * MIN))]
    ev += prop_chain(902, "verified", run=5, t0=t) + prop_chain(903, "frozen", run=5, t0=t) \
        + prop_chain(904, "approved", run=5, t0=t) + prop_chain(905, "proposed", run=5, t0=t)
    return ev


def _golden_audits(home: Path, R: Path) -> None:
    """兩個被拒的稽核檔：①`decide` 帶舊 digest（STALE-CARD，永久）②金鑰不明的 `obs-add`（延後）。"""
    ref1, ref2 = "6f1c2a3e-8b4d-4e5f-9a7b-000000000911", "6f1c2a3e-8b4d-4e5f-9a7b-000000000912"
    fx2.write_audit(home, kind="decide", ref=ref1, subject=fx.pid(905), key=fx2.AUDIT_KEY,
                    body=fx2.body_decide(ref1, fx.pid(905), fx.H(5), "approve"))
    fx2.write_audit(home, kind="obs-add", ref=ref2, subject=None, key=fx2.AUDIT_KEY,
                    key_id="deadbeef", body=fx2.body_obs_add(ref2))


def golden_patrol(case) -> bytes:
    """一次固定心跳後的 `patrol.json`（`push` 區塊以守門「有待推送、尚無 tick」輸入組出）。"""
    R = base_repo()
    fx.append_events(R, _golden_events())
    for n in (902, 903, 904, 905):
        prop_files(R, n)
    fx.commit_all(R, "p7 patrol golden")
    home = case.home
    _golden_audits(home, R)
    spawn = home / "patrol" / fx.rid(5) / "spawn.json"
    spawn.parent.mkdir(parents=True, exist_ok=True)
    spawn.write_bytes(json.dumps({"pid": 4242, "started_at": iso(NOW - 118 * MIN),
                                  "wall_due_at": iso(NOW + 60 * MIN)}).encode("utf-8") + b"\n")
    rig = Rig7()
    rig.live.add(4242)
    with fx4.with_key(fx2.AUDIT_KEY):
        rc, out, err = case.beat(R, NOW, rig)
    case.assertEqual(rc, 0, out + err)
    report = case.report()
    guard = {"ahead": 1, "head": "a" * 40, "code": None, "detail": None}
    report["push"] = patrolreport.push_block(home, {"sched_heartbeat_minutes": 15}, NOW, True,
                                             guard, lambda pid, started: False)
    return dump(report)


# --------------------------------------------------------------------------- 推送守門夾具（PU；TCS
# §3）
APP_BASE = 500  # 夾具自造 APP 編號的起點（`PushRepo.app_id`）
DEC_ID = "DEC" + "-SI-001"  # 執行期拼出（帳本編號字面掃描）


class PushRepo:
    """`p7x.push_repo()`：真 git 的暫存 repo（基線＋一個 `decided` 的 PROP）＋本機 bare 遠端
    `origin`，
    `main` 追蹤 `origin/main`、基線已推上去；之後 `patrol`／`human`／`commit` 造「領先遠端」的提交。
    巡邏提交＝改 touched（P 類）＋追加該 APP 的事件行＋兩個 trailer＋`commits.jsonl` 紀錄，皆合規；
    負向案例以基本動作（`write_touched`、`event`、`commit`、`record`）自行組。
    供 tools/lib/selfimproving/pushguard.py、patrolpush.py 的測試使用。"""

    def __init__(self, case, *, cls: str = "D", n: int = 1, other_prop: bool = False,
                 dangling_app: bool = False) -> None:
        self.case, self.n, self.cls, self.prop = case, n, cls, fx.pid(n)
        self.R, self.si, self.k = base_repo(), case.home, 0
        have = {e["run"] for e in fx.EV(self.R) if e["kind"] == "run.open"}
        head = [] if fx.rid(1) in have else [fx.run_open_ev(1), fx.skip_ev(1)]
        chain, patch = prop_chain(n, "decided"), None
        if cls == "M":
            chain[0].update(cls="M", target=["memory/demo.md"],
                            preimage={"memory/demo.md": fx.H(1)})
            patch = fx.default_patch("M", fx.memory_dir(fx.new_dir("mp")))[0]
        fx.append_events(self.R, [*head, *chain])
        prop_files(self.R, n, patch=patch)
        if other_prop:
            add_prop(self.R, n + 1, "proposed", with_run=False)
        # 帳本裡先有一個沒人提交過的 app.promote（供「照抄 trailer、無帳本差分」案例）
        if dangling_app:
            fx.append_events(self.R, [fx.promote_ev(n, id=self.dangling)])
        fx.commit_all(self.R, "p7 push base")
        fx.git(self.R, "branch", "-M", "main")
        self.bare = fx.new_dir("bare")
        fx.git(fx.TMP, "init", "-q", "--bare", str(self.bare))
        fx.git(self.R, "remote", "add", "origin", str(self.bare))
        fx.git(self.R, "push", "-q", "-u", "origin", "main")
        patch_raw = (self.R / fx.PROPS_REL / self.prop / "r1.patch").read_bytes()
        self.touched = [] if cls == "M" else si_paths.touched_of(patch_raw)

    dangling = "APP" + "-SI-777"

    # ---- 基本動作
    def app_id(self) -> str:
        self.k += 1
        return f"APP-SI-{APP_BASE + self.k:03d}"

    def event(self, kind: str, app: str, *, post: str | None = None) -> None:
        make = {"promote": lambda: fx.promote_ev(self.n, id=app, post_sha256=post or fx.H(11)),
                "rollback": lambda: fx.rollback_ev(self.n, id=app, post_sha256=post or fx.H(10))}
        fx.append_events(self.R, [make[kind.removeprefix("app.")]()])

    def write_touched(self, text: str | None = None) -> None:
        rel = self.touched[0]
        cur = fx.read(self.R, rel)
        fx.put(self.R, rel, text if text is not None else cur + f"patrol {self.k}\n")

    def post(self) -> str:
        return manifest.paths_manifest(self.R, self.touched) if self.touched else fx.H(11)

    def record(self, sha: str, app: str, prop: str | None = None) -> None:
        patrolreport.record_commit(self.si, sha, app, prop or self.prop, NOW)

    def raw_record(self, data: bytes) -> None:
        path = self.si / "push" / patrolreport.COMMITS_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as fh:
            fh.write(data)

    def commit(self, paths, *, app: str, prop: str | None = None, record: bool = True,
               rec: tuple[str, str] | None = None, message: str | None = None,
               empty: bool = False) -> str:
        """提交 `paths`（已存在於工作樹；可空）；預設帶合規 trailer 並寫紀錄；
        `rec`＝(app, prop) 覆寫紀錄。"""
        if paths:
            fx.git(self.R, "add", "--", *paths)
        msg = message if message is not None else pushguard.commit_message(
            "promote", prop or self.prop, DEC_ID, app)
        fx.git(self.R, "commit", "-q", *(["--allow-empty"] if empty else []), "-m", msg)
        sha = fx.git(self.R, "rev-parse", "HEAD")
        if record:
            self.record(sha, *(rec or (app, prop or self.prop)))
        return sha

    def patrol(self, kind: str = "promote", *, extra: dict | None = None, tamper: str | None = None,
               **kw) -> types.SimpleNamespace:
        """一個合規的巡邏提交；`extra`＝{路徑: 內容} 一併提交；`tamper`＝算完 post_sha256
        之後再多寫進
        touched 的文字（造「內容與結果摘要不符」）。"""
        app = kw.pop("app", None) or self.app_id()
        if self.touched:
            self.write_touched()
        self.event(kind, app, post=self.post())
        if tamper is not None and self.touched:
            fx.put(self.R, self.touched[0], fx.read(self.R, self.touched[0]) + tamper)
        for rel, text in (extra or {}).items():
            fx.put(self.R, rel, text)
        paths = [fx.EVL, *self.touched, *(extra or {})]
        return types.SimpleNamespace(sha=self.commit(paths, app=app, **kw), app=app)

    def human(self, rel: str = "README.md", text: str = "人工改動\n") -> str:
        fx.put(self.R, rel, text)
        fx.git(self.R, "add", "--", rel)
        fx.git(self.R, "commit", "-q", "-m", "docs: 人工改動")
        return fx.git(self.R, "rev-parse", "HEAD")

    def push(self) -> None:
        fx.git(self.R, "push", "-q", "origin", "main")

    def evaluate(self, *, enabled: bool = True, alive=None, now: datetime = NOW) -> dict:
        return pushguard.evaluate(self.R, {"sched_auto_push": enabled}, self.si, now, alive=alive)


def push_repo(case, **kw) -> PushRepo:
    return PushRepo(case, **kw)


class RunArgvSpy:
    """`runner.run_argv` 的替身（TCS §3）：記錄每次呼叫的 argv／env／timeout／cwd，回注入的結果；
    `on_call`
    於回傳前執行（造「推送期間工作樹變動」）；`raises` 非 None 則拋出。"""

    def __init__(self, rc=0, out="", err="", timed_out=False, on_call=None, raises=None) -> None:
        self.calls: list[dict] = []
        self.result = types.SimpleNamespace(rc=rc, out=out, err=err, timed_out=timed_out)
        self.on_call, self.raises = on_call, raises

    def __call__(self, argv, *, env, timeout, cwd=None):
        self.calls.append({"argv": list(argv), "env": dict(env), "timeout": timeout, "cwd": cwd})
        if self.on_call is not None:
            self.on_call()
        if self.raises is not None:
            raise self.raises
        return self.result


def run_argv_spy(**kw) -> RunArgvSpy:
    return RunArgvSpy(**kw)


def write_golden(case) -> dict[str, bytes]:
    """（再）產生兩份黃金樣本到 `GOLDEN_DIR`；回 {檔名: 位元組}。只在規格勘誤後由人重產。"""
    out = {"patrol.golden.json": golden_patrol(case), "detail.golden.json": golden_detail(case)}
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name, raw in out.items():
        (GOLDEN_DIR / name).write_bytes(raw)
    return out
