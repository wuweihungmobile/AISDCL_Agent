# 受測面：tools/lib/selfimproving/sched.py（程式碼鎖，非散文）
"""SelfImproving P4 測試共用夾具（TCS-SelfImproving-P4 §5；底線開頭、不被收集）。

建在 P1、P2 夾具之上（呼叫形態不變，R163）；各 P4 測試檔的 `setUpModule` 呼叫 `fx.setup("si_p4_")`。
合成編號一律於執行期以字串相加組出；測試金鑰於執行期以 `secrets.token_hex` 組出、只經環境變數餵入。
本棒（PKG-ROOT-SCHED）只提供排程模型、稽核檔與事件建構器；巡邏心跳的替身（`Deps`、`STUB`）由
PKG-ROOT-PATROL 於同檔追加。
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import secrets
import shutil
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2

from lib.selfimproving import events as si_events
from lib.selfimproving import evwrite, patrol, runner, sched, schedwrite

O = datetime(2026, 11, 2, 8, 0, 0, tzinfo=UTC)  # noqa: E741  # 預設 origin（TCS §2 簡寫 O）
D1 = timedelta(days=1)
HB = 15
H = timedelta(hours=1)
MIN = timedelta(minutes=1)
TEST_KEY = secrets.token_hex(16)  # 執行期組出，不寫進任何檔案字面
PERIOD_KEYS = ("sched_period_minutes_default", "sched_period_minutes_min",
               "sched_period_minutes_max", "sched_heartbeat_minutes")


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


SOP_REL = "docs/05_development/SelfImproving_Operations_SOP.md"


def make_p4_repo(dest: Path, *, events=None, prm=None, commit: bool = True,
                 sop: bool = True) -> Path:
    """P2 基線 repo（params.json 已含九個 sched 鍵）＋真 SOP 的〈無人運轉任務書範本〉節位元組
    複本（巡邏器自 `--repo` 讀任務書範本）；不複製整份 SOP：它引用的 OBS 編號不在夾具帳本內，
    `check` 的 `ref.obs` 會因此紅。`events` 為手寫事件（時間以 `t` 明給）。"""
    repo = fx2.make_p2_repo(dest, events=events, prm=prm, commit=commit)
    if sop and commit:
        real = fx.REAL_SOP.read_bytes()
        fx.putb(repo, SOP_REL, real[real.index("## 無人運轉任務書範本".encode()):])
        fx.commit_all(repo, "C4")
    return repo


def p4_base(events=None, prm=None) -> Path:
    """每次呼叫建一個全新的 P4 repo 複本（事件各測試不同，不走快取）。"""
    return make_p4_repo(fx.new_dir("p4"), events=events, prm=prm)


def params() -> dict:
    return fx.params_dict()


# --------------------------------------------------------------------------- 事件建構器（手寫）
def sched_set_ev(t: datetime, *, enabled: bool = True, period: int = 1440,
                 carrier: str | None = None, by: str = "main", **kw) -> dict:
    """預設載體：停用＝`host`（免引言）、啟用＝`transcript`（須人的引言，R138）。"""
    carrier = carrier or ("transcript" if enabled else "host")
    body = {"enabled": enabled, "period_minutes": period, "carrier": carrier}
    if carrier == "transcript":
        body.update(sid=fx.UUID, line=1)
    elif carrier == "console":
        body.update(audit_ref=fx2.new_uuid(), audit_sha256=fx.H(7), key_id="00000000",
                    decider="admin")
    body.update(kw)
    return fx.ev("sched.set", by, t=iso(t), **body)


def run_open_f_ev(n: int, t: datetime, *, due_at: datetime | None = None, by: str = "patrol",
                  **kw) -> dict:
    body = {"trigger": "f"}
    if due_at is not None:
        body["due_at"] = iso(due_at)
    body.update(kw)
    return fx.ev("run.open", by, t=iso(t), run=fx.rid(n), **body)


def run_close_ev(n: int, t: datetime) -> dict:
    return fx.ev("run.close", "main", t=iso(t), run=fx.rid(n), no_event=True)


def sched_skip_ev(t: datetime, reason: str, *, due_at: datetime, detail: str = "x",
                  audit_ref: str | None = None) -> dict:
    body = {"due_at": iso(due_at), "reason": reason, "detail": detail}
    if audit_ref is not None:
        body.update(carrier="console", audit_ref=audit_ref)
    return fx.ev("sched.skip", "patrol", t=iso(t), **body)


def ledger(R: Path) -> list[dict]:
    return fx.EV(R)


def snapshot(R: Path):
    """倉內檔案雜湊加 `git status` 加家目錄樹（位元組）；零殘留的判準面。"""
    home = Path(os.environ["AUTOSDD_SI_DIR"])
    tree = {p.relative_to(home).as_posix(): p.read_bytes() for p in sorted(home.rglob("*"))
            if p.is_file() and p.suffix != ".lock" and "locks" not in p.parts}
    return fx.snap(R), tree


# --------------------------------------------------------------------------- Console 稽核檔（§5.2）
def body_sched_set(ref: str, enabled, period, *, reason=None, user: str = "admin",
                   time: str = fx2.AUDIT_TIME, drop=(), **over) -> dict:
    b = fx2._common(ref, "sched-set", user, time)
    b.update(enabled=enabled, period_minutes=period)
    if reason is not None:
        b["reason"] = reason
    b.update(over)
    return {k: v for k, v in b.items() if k not in drop}


def body_run_request(ref: str, *, note=None, user: str = "admin", time: str = fx2.AUDIT_TIME,
                     **over) -> dict:
    b = fx2._common(ref, "run-request", user, time)
    if note is not None:
        b["note"] = note
    b.update(over)
    return b


def audit_file(home: Path, kind: str, body_fn, *, ref: str | None = None, key: str = TEST_KEY,
               subject=None, tamper: str | None = None, **kw) -> str:
    """依 `kind` 建構稽核檔（`body_fn(ref)` 回 body dict）並簽章；`tamper` 指名對位元組的改動
    （`swap`＝body 首兩鍵對調書寫序、`flip`＝改一個字元），MAC 沿用改動前者供 MAC 負控。"""
    ref = ref or fx2.new_uuid()
    body = body_fn(ref)
    text = fx2._jdump(body)
    mac = None
    if tamper:
        import hashlib
        import hmac

        mac = hmac.new(key.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()
        keys = list(body)
        if tamper == "swap":
            keys[0], keys[1] = keys[1], keys[0]
            text = fx2._jdump({k: body[k] for k in keys})
        else:
            text = text.replace('"admin"', '"admiN"', 1)
    fx2.write_audit(home, kind=kind, ref=ref, subject=subject, body=text, key=key, mac=mac, **kw)
    return ref


def with_key(key: str = TEST_KEY):
    """`AUTOSDD_SI_AUDIT_KEY` 只在 with 區塊內存在（用畢即還原）。"""
    return mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": key})


# --------------------------------------------------------------------------- 測試基底
class P4TestCase(fx2.P2TestCase):  # 名稱含 TestCase：discover 守門不解析跨檔基底鏈（OBS-SI-162）
    def at(self, when: datetime):
        return mock.patch.object(schedwrite, "current_time", return_value=when)

    def loaded(self, R: Path) -> list[dict]:
        return si_events.load_sound_events(R / si_events.LEDGER_REL) or []

    def snap(self, R: Path):
        return snapshot(R)

    def refused(self, R: Path, argv, codes, *, env=None) -> None:
        before = self.snap(R)
        with mock.patch.dict(os.environ, env or {}):
            rc, out, _ = self.M(R, *argv)
        self.rejected(rc, out, codes, str(argv))
        self.assertEqual(self.snap(R), before, str(argv))

    def ingest(self, R: Path, ref: str, *, verb: str = "sched"):
        if verb == "sched":
            argv = ["sched", "set", "--carrier", "console", "--audit-ref", ref, "--by", "main"]
        else:
            argv = ["run-open", "--trigger", "a", "--carrier", "console", "--audit-ref", ref,
                    "--coord", f"console_audit/{ref}.json", "--by", "console"]
        with with_key(fx2.AUDIT_KEY):
            return self.M(R, *argv)

    def status(self, R: Path) -> dict:
        with mock.patch.object(runner, "run_argv", return_value=types.SimpleNamespace(
                rc=0, out="ABSENT", err="", timed_out=False)):
            return self.MJ(R, "status")

    def audit(self, kind: str, body_fn, **kw) -> str:
        return audit_file(self.home, kind, body_fn, key=fx2.AUDIT_KEY, **kw)

    def beat(self, R: Path, now: datetime, rig: Rig | None = None, *args: str, hm: str = "12:00"):
        """`HEARTBEAT`（TCS §2 B 節）：回 (rc, out, err)；`now`、事件 `t`、本機時分三者一律注入。"""
        rig = rig or getattr(self, "rig", None) or Rig()
        self.rig, rig.now = rig, now
        out, err = io.StringIO(), io.StringIO()
        with (mock.patch.object(schedwrite, "current_time", return_value=now),
              mock.patch.object(evwrite, "now_iso", return_value=iso(now)),
              mock.patch.object(sched, "local_hm", return_value=hm),
              contextlib.redirect_stdout(out), contextlib.redirect_stderr(err)):
            rc = patrol.main(["--now", iso(now), "--repo", str(R), *args], rig.deps(R))
        return rc, out.getvalue(), err.getvalue()

    def stub_env(self, key: str = TEST_KEY):
        return mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": key})

    def enabled_repo(self, *extra, prm=None) -> Path:
        """S-CELL：啟用、週期 1440、origin 為 `O`；其餘手寫事件由 `extra` 給。"""
        return p4_base(events=[sched_set_ev(O), *extra], prm=prm)

    def logs(self) -> list[str]:
        return log_lines(self.home)


# --------------------------------------------------------------------------- 巡邏心跳替身
# （PKG-ROOT-PATROL）
#: 替身 `claude` 路徑：`Deps.which` 原樣回傳、`patrolrun` 原樣放進 argv[0]，全程不經 Path 渲染，
#: 故測試以同一常數比對（不是 POSIX 絕對路徑字面值比對 Path 產物）。
STUB = "/stub/claude"


class Spawner:
    """`runner.spawn_detached` 的替身：記錄 argv／env／cwd 並回假 pid；前 `fail` 次呼叫拋
    `PermissionError`
    （模擬脫離旗標被任務 job 拒絕）。"""

    def __init__(self, *, fail: int = 0, base: int = 424200) -> None:
        self.calls: list[dict] = []
        self.attempts, self.fail, self.base = 0, fail, base

    def __call__(self, argv, *, env, cwd=None, out_dir=None) -> int:
        self.attempts += 1
        if self.attempts <= self.fail:
            raise PermissionError("breakaway denied")
        self.calls.append({"argv": list(argv), "env": dict(env), "cwd": str(cwd),
                           "out_dir": None if out_dir is None else Path(out_dir)})
        return self.base + len(self.calls)


class Rig:
    """心跳替身包：額度帶、對話靜默、`claude` 路徑、動詞呼叫記錄、spawn 記錄、存活 pid
    集合與殺行程記錄；
    `research --fetch` 以預設 rc 序列替身（rc 0／2 另落一筆 `research.scan`，rc 1 回拒收）。"""

    def __init__(self, *, band: str = "free", quiet: bool = True,
        which: str | None = STUB,
                 preflight: str | None = None, fetch_rcs=(0,), changed: bool = True) -> None:
        self.band, self.quiet, self.which, self.preflight = band, quiet, which, preflight
        self.fetch_rcs, self.changed = list(fetch_rcs), changed
        self.verbs_log: list[list[str]] = []
        self.spawner, self.live, self.killed = Spawner(), set(), []
        self.now = O
        self.boom: Exception | None = None
        self.scan_rows: list[str] | None = None
        self.write_source = True

    def deps(self, R: Path):
        def verbs(argv):
            self.verbs_log.append(list(argv))
            if self.boom is not None:
                err, self.boom = self.boom, None
                raise err
            return self._run(R, list(argv))
        return patrol.Deps(
            quota=lambda now: types.SimpleNamespace(band=self.band),
            driver_quiet=lambda: self.quiet, which=lambda name: self.which,
            preflight=lambda: self.preflight, verbs=verbs, spawn_detached=self.spawner,
            pid_alive=lambda pid, started: pid in self.live, kill_tree=self.killed.append)

    def _run(self, R: Path, argv: list[str]):
        if argv[0] == "scan" and self.scan_rows is not None:
            return 0, json.dumps({"candidates": [{"row": r} for r in self.scan_rows]}), ""
        if argv[:2] != ["research", "--fetch"]:
            return patrol._real_verbs(argv)
        rc = self.fetch_rcs.pop(0) if len(self.fetch_rcs) > 1 else self.fetch_rcs[0]
        if rc in (0, 2):
            run = argv[argv.index("--run") + 1]
            src = {"id": "src-a", "sha256": fx.H(11), "bytes": 10, "changed": self.changed,
                   "http_status": 200}
            if self.changed and self.write_source:  # 真 fetch 會落原檔（D-IMP-12 複製來源）
                from lib.selfimproving import events as si_events
                sha12 = src["sha256"].split(":")[1][:12]
                f = si_events.si_dir() / "research" / "src-a" / f"{sha12}.txt"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"source-bytes \x00\xff " + run.encode())
            fx.append_events(R, [fx.ev("research.scan", "researcher", t=iso(self.now), run=run,
                                       sources=[src], sources_sha256=fx.H(12),
                                       fetched_at=iso(self.now))])
            return rc, f"ok research.scan run={run}\n", ""
        return 1, "reject research ZERO-SUCCESS\n", ""

    def verbs_named(self, *head: str) -> list[list[str]]:
        return [a for a in self.verbs_log if a[:len(head)] == list(head)]


def ledger_text(R: Path) -> bytes:
    return (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""


def log_lines(home: Path) -> list[str]:
    path = home / "patrol" / "patrol.log"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


# --------------------------------------------------------------------------- 雜項
def ledger_line_of(R: Path, seq: int) -> int:
    """事件 `seq` 在帳本中的 1 起算實體行號。"""
    for no, ln in enumerate((R / fx.EVL).read_bytes().decode("utf-8").split("\n"), start=1):
        if ln.strip() and json.loads(ln)["seq"] == seq:
            return no
    raise AssertionError(f"seq {seq} 不在帳本")


def clone(R: Path) -> Path:
    dest = fx.new_dir("cp")
    shutil.copytree(R, dest)
    return dest
