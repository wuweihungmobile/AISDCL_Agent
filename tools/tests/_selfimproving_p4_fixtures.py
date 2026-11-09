# 受測面：tools/lib/selfimproving/sched.py（程式碼鎖，非散文）
"""SelfImproving P4 測試共用夾具（TCS-SelfImproving-P4 §5；底線開頭、不被收集）。

建在 P1、P2 夾具之上（呼叫形態不變，R163）；各 P4 測試檔的 `setUpModule` 呼叫 `fx.setup("si_p4_")`。
合成編號一律於執行期以字串相加組出；測試金鑰於執行期以 `secrets.token_hex` 組出、只經環境變數餵入。
本棒（PKG-ROOT-SCHED）只提供排程模型、稽核檔與事件建構器；巡邏心跳的替身（`Deps`、`STUB`）由
PKG-ROOT-PATROL 於同檔追加。
"""

from __future__ import annotations

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
from lib.selfimproving import runner, schedwrite

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


def make_p4_repo(dest: Path, *, events=None, prm=None, commit: bool = True) -> Path:
    """P2 基線 repo（params.json 已含九個 sched 鍵）；`events` 為手寫事件（時間以 `t` 明給）。"""
    return fx2.make_p2_repo(dest, events=events, prm=prm, commit=commit)


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
class P4Case(fx2.P2TestCase):
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
