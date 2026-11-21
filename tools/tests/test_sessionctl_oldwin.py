"""舊視窗有條件自動關閉（DES §7.1；TCS REQ-WP-54～59、98、101／AT-WP-70～78、85～89／MU-WP-20～24、
28～30、34）。

全用注入縫：假 api（假行程樹）、假排程器、假登記檔目錄、tmp 痕跡目錄；**不碰真行程、不起真排程**
（真行程樹與真沙盒視窗另由 `tests/test_sessionctl_oldwin_real.py` 與 RealVerify 的 RV-WP52～54
負責）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import (  # noqa: E402
    handoff,
    oldwin,
    oldwin_park,
    oldwin_sched,
    park,
    park_cli,
    procstop,
    winproc,
)

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
OLD = "d4ed2654-9181-4df1-a6e6-2d712956e23b"
NEW = "c3d4e5f6-0000-4000-8000-000000000001"
PID = 15660
FT = winproc.epoch_to_filetime(NOW.timestamp() - 7200)  # 舊視窗兩小時前建立


def _iso(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def _human(minutes_ago: float, text: str = "繼續") -> dict:
    return {
        "type": "user",
        "timestamp": _iso(minutes_ago),
        "origin": {"kind": "human"},
        "message": {"role": "user", "content": text},
    }


def _bg_call(tid: str, command: str, minutes_ago: float = 20) -> dict:
    return {
        "type": "assistant",
        "timestamp": _iso(minutes_ago),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tid,
                    "name": "PowerShell",
                    "input": {"command": command, "run_in_background": True},
                }
            ]
        },
    }


def _done(tid: str) -> dict:
    return {
        "type": "queue-operation",
        "timestamp": _iso(5),
        "content": (
            f"<task-notification>\n<tool-use-id>{tid}</tool-use-id>\n"
            "<status>completed</status>\n"
        ),
    }


class FakeApi:
    """假行程表：`procs[pid] = {created, image, ppid, alive}`。handle 綁在 open 當下那個行程物件上
    （模擬真 handle：之後 pid 被換成別的行程，handle 指的仍是原行程）。`hook` 在 snapshot 時觸發一次
    （＝判準與第一個終止之間的注入點）。"""

    def __init__(self, procs, *, hook=None, ancestors=()) -> None:
        self.procs, self.hook, self._anc = procs, hook, set(ancestors)
        self.handles: dict[int, tuple[int, dict]] = {}
        self.terminated: list[int] = []
        self.intent_seen_at_first_terminate: bool | None = None

    def open(self, pid):
        rec = self.procs.get(pid)
        if rec is None or not rec["alive"]:
            return None
        self.handles[len(self.handles) + 1000] = (pid, rec)
        return len(self.handles) + 999

    def created(self, handle):
        return self.handles[handle][1]["created"]

    def image(self, handle):
        return self.handles[handle][1]["image"]

    def terminate(self, handle):
        if self.intent_seen_at_first_terminate is None:
            self.intent_seen_at_first_terminate = bool(oldwin.events("oldwin_close_intent"))
        pid, rec = self.handles[handle]
        rec["alive"] = False
        self.terminated.append(pid)
        return True

    def running(self, handle):
        return self.handles[handle][1]["alive"]

    def close(self, handle):
        return None

    def snapshot(self):
        if self.hook is not None:
            hook, self.hook = self.hook, None
            hook()
        return [(p, r["ppid"]) for p, r in self.procs.items() if r["alive"]]

    def ancestors(self, pid):
        return set(self._anc)


def _tree(**over) -> dict:
    """父 100（claude.exe）＋2 子（101、102）＋孫 104（101 的子）＋103（parent 同為 100、
    但建立時刻早於父）。"""

    def proc(pid, ppid, created, image="claude.exe"):
        return {"created": created, "image": image, "ppid": ppid, "alive": True}

    procs = {
        PID: proc(PID, 1, FT),
        101: proc(101, PID, FT + 10, "powershell.exe"),
        102: proc(102, PID, FT + 20, "node.exe"),
        104: proc(104, 101, FT + 30, "sleep.exe"),
        103: proc(103, PID, FT - 5, "unrelated.exe"),
    }
    procs.update(over)
    return procs


class Base(unittest.TestCase):
    """每個測試一套 tmp 世界：登記檔目錄、逐字稿、交接包、痕跡目錄。"""

    status, entrypoint, human_minutes = "idle", "cli", 10.0

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="oldwin-")
        self.addCleanup(holder.cleanup)
        self.dir = Path(holder.name)
        for name in ("sessions", "projects", "handoff", "trace"):
            (self.dir / name).mkdir()
        patcher = unittest.mock.patch.dict(
            os.environ, {"AUTOSDD_TRACE_DIR": str(self.dir / "trace")}
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.dir / "handoff")}
        self.pkg = self.dir / "handoff" / f"{OLD}_20261119T110000Z.md"
        self.pkg.write_text(f"sid={OLD}\n", encoding="utf-8")
        self.set_ack(True)
        self.registry()
        self.write_transcript(OLD, [_human(self.human_minutes)])
        self.write_transcript(NEW, [{"type": "assistant", "timestamp": _iso(1)}])

    # ---- 世界的各個旋鈕 ----
    def set_ack(self, on: bool) -> None:
        ack = self.pkg.with_suffix(".ack")
        ack.write_text(f"acked {_iso(2)} sid={NEW}\n", encoding="utf-8") if on else ack.unlink(
            missing_ok=True
        )

    def registry(self, **over) -> None:
        row = {
            "pid": PID,
            "sessionId": OLD,
            "procStart": FT,
            "entrypoint": self.entrypoint,
            "status": self.status,
            "cwd": "sandbox-x",
        }
        row.update(over)
        row = {k: v for k, v in row.items() if v is not None}
        (self.dir / "sessions" / f"{PID}.json").write_text(json.dumps(row), encoding="utf-8")

    def write_transcript(self, sid: str, recs: list[dict], append: bool = False) -> Path:
        path = self.dir / "projects" / f"{sid}.jsonl"
        with path.open("a" if append else "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
        return path

    def kw(self, **over) -> dict:
        base = {
            "env": self.env,
            "now": NOW,
            "sessions_dir": self.dir / "sessions",
            "projects_dir": self.dir / "projects",
            "platform_name": "win32",
            "created_of": lambda pid: FT,
            "roster_running": lambda *a, **k: [],
        }
        base.update(over)
        return base

    def eligible(self, **over) -> dict:
        return oldwin.eligible(OLD, self.pkg, new_sid=NEW, **self.kw(**over))

    def close(self, api=None, schedule=None, **over) -> dict:
        sched_calls: list = []

        def fake_schedule(old, new, pkg, when, **_kw):
            sched_calls.append(when)
            return 0, f"NextRunTime={len(sched_calls)}"

        self.sched_calls = sched_calls
        return oldwin.close_if_eligible(
            OLD,
            NEW,
            self.pkg,
            api=api or FakeApi(_tree()),
            self_pid=999,
            schedule=schedule or fake_schedule,
            sleep=lambda s: None,
            wait=0.2,
            **self.kw(**over),
        )


class R217FiveConditionsTest(Base):
    def test_at_wp_72_every_condition_flips_the_verdict_and_names_itself(self) -> None:
        """MU-WP-21：拿掉任何一條都會有一格翻不動。①procStart 差 1／只剩 CIM；②busy／有 running
        子代理；
        ③最後真人記錄 4 分前；④無 .ack／有 .ack 但新 sid 無 assistant 記錄；⑤darwin。"""
        self.assertTrue(self.eligible()["ok"], "對照組：五條件全成立")
        cases = [
            (1, {"created_of": lambda pid: FT + 1}),  # ① procStart 差 1（100ns）
            (1, {"created_of": lambda pid: None}),  # ① 只有 CIM 可用（取不到 GetProcessTimes）
            (2, {"roster_running": lambda *a, **k: [{"id": "a1"}]}),  # ② 名冊有 running 子代理
            (5, {"platform_name": "darwin"}),  # ⑤
        ]
        for cond, over in cases:
            res = self.eligible(**over)
            self.assertEqual((res["ok"], res["cond"]), (False, cond), over)
        self.registry(status="busy")
        self.assertEqual(self.eligible()["cond"], 2)  # ② busy
        self.registry()
        self.write_transcript(OLD, [_human(4)])  # ③ 4 分前
        third = self.eligible()
        self.assertEqual((third["cond"], third["reason"]), (3, "recent_human_prompt"))
        self.assertAlmostEqual(third["retry_at"], (NOW - timedelta(minutes=4)).timestamp() + 360)
        self.write_transcript(
            OLD,
            [
                _human(6),
                {
                    "type": "user",
                    "timestamp": _iso(1),
                    "origin": {"kind": "human"},
                    "message": {"content": "<task-notification>\nx"},
                },
            ],
        )
        self.assertTrue(
            self.eligible()["ok"], "最後一筆是 task-notification 不算真人（6 分前那筆才算）"
        )
        self.set_ack(False)
        self.assertEqual(self.eligible()["cond"], 4)  # ④ 無 .ack
        self.set_ack(True)
        self.write_transcript(
            NEW, [{"type": "user", "timestamp": _iso(1), "message": {"content": "assistant"}}]
        )
        self.assertEqual(
            self.eligible()["cond"],
            4,
            "新 sid 逐字稿沒有 assistant 記錄（字面含 assistant 的 user 不算）",
        )

    def test_at_wp_72_same_sid_skips_condition_four(self) -> None:
        """park 同 sid 續跑：④ 是事後驗證（關閉後 `claude -r` 寫出新記錄），判準階段不查 .ack。"""
        self.set_ack(False)
        self.assertTrue(oldwin.eligible(OLD, self.pkg, same_sid=True, **self.kw())["ok"])

    def test_at_wp_87_condition_two_and_the_target_filter(self) -> None:
        """(a) 無 status 欄；(b) status＝waiting；(c) idle＋running 的 runlong 背景 shell；(d) 只有
        keepwarm 與
        watch shell；(e) entrypoint＝sdk-cli；(f) entrypoint 缺欄。MU-WP-30／34。"""
        self.registry(status=None)
        self.assertEqual(
            (self.eligible()["ok"], self.eligible()["cond"]), (False, 2), "(a) 缺欄不當 idle"
        )
        self.registry(status="waiting")
        self.assertEqual(self.eligible()["cond"], 2, "(b) 不認得的值")
        self.registry()
        runlong = "python tools/sessionctl.py runlong --out x.txt -- python -c pass"
        self.write_transcript(OLD, [_human(10), _bg_call("t1", runlong)])
        res = self.eligible()
        self.assertEqual((res["ok"], res["cond"]), (False, 2), "(c) 非保溫背景 shell 在跑")
        self.write_transcript(
            OLD,
            [
                _human(10),
                _bg_call("t2", "python tools/sessionctl.py keepwarm --sid x"),
                _bg_call("t3", "python tools/sessionctl.py watch --sid x"),
            ],
        )
        self.assertTrue(self.eligible()["ok"], "(d) 純保溫／監督 shell 不算忙")
        self.write_transcript(OLD, [_human(10), _bg_call("t1", runlong), _done("t1")])
        self.assertTrue(self.eligible()["ok"], "收到完成通知的背景 shell 不算 running")
        for entry in ("sdk-cli", None):
            self.registry(entrypoint=entry)
            res = self.eligible()
            self.assertEqual((res["ok"], res["cond"], res["terminal"]), (False, 1, True), entry)

    def test_the_off_switches_and_unattended_only_remind(self) -> None:
        """AT-WP-76／MU-WP-24：`AUTOSDD_OLDWIN_AUTOCLOSE_OFF`、模式 notify、`AUTOSDD_UNATTENDED`、
        非 Windows
        一律不關；只出提醒文字（舊視窗 pid）。"""
        for extra in (
            {"AUTOSDD_OLDWIN_AUTOCLOSE_OFF": "1"},
            {"AUTOSDD_SESSION_SWITCH_MODE": "notify"},
            {"AUTOSDD_UNATTENDED": "1"},
        ):
            api = FakeApi(_tree())
            res = self.close(api=api, env={**self.env, **extra})
            self.assertEqual((res["closed"], api.terminated), (False, []), extra)
        self.assertEqual(self.close(api=FakeApi(_tree()), platform_name="darwin")["closed"], False)
        lines = oldwin.reminder_lines(self.env, self.dir / "sessions", lambda pid: FT)
        self.assertEqual(len(lines), 1)
        self.assertIn(f"pid={PID}", lines[0])


class R217CloseProcedureTest(Base):
    def test_at_wp_73_kills_the_tree_leaf_first_and_only_real_descendants(self) -> None:
        """父＋2 子＋孫；另有一個 parent pid 相同但建立時刻早於父的行程。MU-WP-22：
        只砍父會讓孫殘留。
        只砍父與其真子孫、由葉往根、本體最後；`oldwin_close_intent` 一定先於任何終止動作寫入。"""
        api = FakeApi(_tree())
        res = self.close(api=api)
        self.assertTrue(res["closed"], res)
        self.assertEqual(sorted(api.terminated), sorted([PID, 101, 102, 104]))
        self.assertEqual(api.terminated[-1], PID, "本體最後")
        self.assertLess(api.terminated.index(104), api.terminated.index(101), "孫先於它的父")
        self.assertNotIn(103, api.terminated, "建立時刻早於父者只是碰巧同 parent pid")
        self.assertTrue(api.procs[103]["alive"])
        self.assertTrue(api.intent_seen_at_first_terminate, "intent 痕跡先於第一個終止動作")
        intent = oldwin.events("oldwin_close_intent")[0]
        self.assertEqual(
            (intent["pid"], intent["proc_start"], sorted(intent["descendants"])),
            (PID, FT, [101, 102, 104]),
        )
        self.assertIn("evidence", intent, "intent 帶五條件的證據")
        self.assertEqual(oldwin.events("oldwin_closed")[0]["handoff"], str(self.pkg))

    def test_at_wp_73_pid_reuse_is_defeated_by_working_through_the_handle(self) -> None:
        """MU-WP-23：驗證後、終止前把父 pid 換成另一個行程 ⇒ 砍的仍是原行程，新行程毫髮無傷。
        另一變體
        ：handle 上的建立時刻與登記檔 procStart 不符 ⇒ 中止、`oldwin_close_refused`、什麼都不砍。"""
        tree = _tree()
        newcomer = {"created": FT + 999, "image": "claude.exe", "ppid": 1, "alive": True}
        api = FakeApi(tree, hook=lambda: tree.__setitem__(PID, newcomer))
        self.assertTrue(self.close(api=api)["closed"])
        self.assertTrue(newcomer["alive"], "被換進來的行程不得被砍")
        mismatch = _tree()
        mismatch[PID]["created"] = FT + 1
        api2 = FakeApi(mismatch)
        res = self.close(api=api2)
        self.assertEqual(
            (res["closed"], api2.terminated, res["reason"]), (False, [], "procstart_mismatch")
        )
        self.assertTrue(oldwin.events("oldwin_close_refused"))

    def test_at_wp_74_guards_refuse_and_say_so(self) -> None:
        """映像名 python.exe／目標是呼叫者祖先／目標 sessionId＝呼叫者 sid／登記檔不存在 ⇒
        全部不關並寫
        `oldwin_close_refused`。"""
        python = _tree()
        python[PID]["image"] = "python.exe"
        cases = {
            "image_not_allowed": (FakeApi(python), {}),
            "target_is_caller_or_ancestor": (FakeApi(_tree(), ancestors=[PID]), {}),
        }
        for reason, (api, over) in cases.items():
            res = self.close(api=api, **over)
            self.assertEqual((res["closed"], res["reason"], api.terminated), (False, reason, []))
        self.write_transcript(OLD, [_human(10), {"type": "assistant", "timestamp": _iso(9)}])
        same = oldwin.close_if_eligible(
            OLD, OLD, self.pkg, api=FakeApi(_tree()), self_pid=999, **self.kw()
        )
        self.assertEqual((same["closed"], same["reason"]), (False, "target_is_caller_session"))
        (self.dir / "sessions" / f"{PID}.json").unlink()
        api = FakeApi(_tree())
        gone = self.close(api=api)
        self.assertEqual(
            (gone["closed"], api.terminated, gone["reason"]), (False, [], "identity_unverified")
        )
        self.assertGreaterEqual(len(oldwin.events("oldwin_close_refused")), 4)

    def test_at_wp_86_toctou_each_change_between_judgement_and_kill_aborts(self) -> None:
        """MU-WP-29：登記檔 status 改 busy／逐字稿追加真人 user 記錄／追加
        run_in_background／否決檔出現
        ⇒ 四格皆中止、TerminateProcess 呼叫 0 次、`oldwin_close_refused(reason=toctou_<項>)`，
        且重試計數
        ＋1；無變化的對照組照常關閉。"""
        runlong = "python tools/sessionctl.py runlong --out x -- y"
        injections = {
            "toctou_registry": lambda: self.registry(status="busy"),
            "toctou_prompt": lambda: self.write_transcript(
                OLD, [_human(0.1, "等一下")], append=True
            ),
            "toctou_bg": lambda: self.write_transcript(
                OLD, [_bg_call("tx", runlong, 0.1)], append=True
            ),
            "toctou_veto": lambda: (
                oldwin.record_keep_veto(OLD, "x", self.env, NOW) or self.fail("否決檔沒寫出來")
            ),
        }
        self.pkg.with_suffix(".sealed").write_text(NOW.isoformat(), encoding="utf-8")
        for reason, inject in injections.items():
            with self.subTest(reason):
                self.setUp()
                self.pkg.with_suffix(".sealed").write_text(NOW.isoformat(), encoding="utf-8")
                api = FakeApi(_tree(), hook=inject)
                before = oldwin.retry_count(self.pkg)
                res = self.close(api=api)
                self.assertEqual(
                    (res["closed"], api.terminated, res["reason"]), (False, [], reason)
                )
                self.assertEqual(oldwin.events("oldwin_close_refused")[-1]["reason"], reason)
                if reason != "toctou_veto":  # 否決是「永不重試」，不計次也不排程
                    self.assertEqual(len(self.sched_calls), 1)
                    self.assertEqual(oldwin.retry_count(self.pkg), before + 1)
        self.setUp()
        self.assertTrue(self.close(api=FakeApi(_tree()))["closed"], "對照組：無變化照常關閉")


class R217RetryTest(Base):
    human_minutes = 2.0

    def test_at_wp_75_the_retry_fires_at_last_prompt_plus_quiet_plus_one_minute(self) -> None:
        """③不成立（最後真人記錄 2 分前）⇒ 登記重試，觸發＝最後真人記錄＋5 分＋1 分；憑證回讀不到 ⇒
        rc≠0；
        第 3 次之後不再登記、寫放棄痕跡、新 session 出聲「舊窗保留」。"""
        res = self.close()
        self.assertEqual(res["scheduled"], "NextRunTime=1")
        self.assertAlmostEqual(self.sched_calls[0], (NOW - timedelta(minutes=2)).timestamp() + 360)
        self.close()
        self.close()
        again = self.close()
        self.assertEqual(
            (again["abandoned"], len(self.sched_calls), oldwin.retry_count(self.pkg)),
            (True, 0, 3),
            "第 4 次：不再登記（本次沒有呼叫排程器）、放棄",
        )
        self.assertTrue(oldwin.events("oldwin_retry_abandoned"))
        self.assertIn("請手動關閉舊視窗", oldwin.take_unread_notice(NEW))  # R217 F7：白話＋指名 pid

    def test_the_real_scheduler_path_reads_back_a_credential_or_fails_loudly(self) -> None:
        """`schedule_retry` 本體（假排程器）：同舊 sid 前綴的既有工作先刪、新名字含 HHmm；憑證空 ⇒
        rc≠0。
        AT-WP-75（SCH 回空 ⇒ rc≠0）、AT-WP-89（登記新重試前舊前綴工作被刪、最後恰 1 個）。"""

        class Backend:
            name = "fake"

            def __init__(self) -> None:
                self.jobs = [
                    f"AutoSDD_OldWinClose_{OLD[:8]}_1100",
                    "AutoSDD_OldWinClose_other0000_1100",
                ]

            def list_jobs(self, prefix):
                return [j for j in self.jobs if j.startswith(prefix)]

            def disarm(self, name):
                self.jobs.remove(name)
                return 0

        be, armed = Backend(), []

        def arm(label, argv, cwd, fire, **_kw):
            armed.append((label, argv, fire))
            be.jobs.append(label)
            return 0, f"NextRunTime {fire.isoformat()}"

        when = (NOW + timedelta(minutes=6)).timestamp()
        rc, cred = oldwin_sched.schedule_retry(
            OLD, NEW, self.pkg, when, env={}, now=NOW, arm=arm, backend=be
        )
        label = armed[0][0]
        self.assertEqual(rc, 0)
        self.assertIn("NextRunTime", cred)
        self.assertTrue(label.startswith(f"AutoSDD_OldWinClose_{OLD[:8]}_"))
        self.assertEqual([j for j in be.jobs if OLD[:8] in j], [label], "同舊 sid 前綴最後恰 1 個")
        self.assertIn("other0000_1100", " ".join(be.jobs), "別的舊 sid 的工作不得被刪")
        argv = armed[0][1]
        self.assertEqual(
            Path(argv[argv.index("--trace-dir") + 1]).resolve(),
            Path(os.environ["AUTOSDD_TRACE_DIR"]).resolve(),
            "排程不帶環境變數：痕跡目錄隨 argv 帶過去",
        )
        failed = self.close(schedule=lambda *a, **k: (1, ""))
        self.assertIsNone(failed["scheduled"])
        self.assertEqual(oldwin.retry_count(self.pkg), 0, "憑證取不到不得記成已重試")

    def test_the_sandbox_prefix_comes_from_the_trace_dir_data_file(self) -> None:
        """REQ-WP-101：前綴讀 `trace_dir()/oldwin/task_prefix`（不開環境變數鉤）；缺檔＝出廠前綴。
        """
        self.assertEqual(oldwin_sched.task_prefix(), "AutoSDD_OldWinClose_")
        folder = self.dir / "trace" / "oldwin"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "task_prefix").write_text("AutoSDD_OldWinCloseSbx_abcd1234_\n", encoding="utf-8")
        self.assertEqual(oldwin_sched.task_prefix(), "AutoSDD_OldWinCloseSbx_abcd1234_")


class R217VetoTest(Base):
    def test_at_wp_85_the_keep_prefix_vetoes_forever_and_only_that_package(self) -> None:
        """MU-WP-28：(a) 已封存／已 spawn／已 ack 的包所屬 sid 收到 `留：` ⇒ 寫否決檔與事件；(b)
        名下無交接包
        ⇒ 不寫；(c) 之後五條件全成立 `eligible()` 仍 false（kept_by_user）；(d) 重試行程見否決 ⇒
        刪自己、
        不再登記、新 session 出聲一次；(f) 新交接包不受舊否決影響；`--sweep` 不碰否決檔。"""
        path = oldwin.record_keep_veto(OLD, "t.jsonl", self.env, NOW)
        self.assertTrue(path and path.is_file(), "(a)")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["handoff"], str(self.pkg))
        self.assertEqual(len(oldwin.events("oldwin_keep_veto")), 1)
        self.assertIsNone(
            oldwin.record_keep_veto("no-package-sid", "t.jsonl", self.env, NOW), "(b)"
        )
        res = self.eligible()
        self.assertEqual((res["ok"], res["reason"]), (False, "kept_by_user"), "(c)")
        removed: list = []

        class Backend:
            def list_jobs(self, prefix):
                return []

            def disarm(self, name):
                removed.append(name)
                return 0

        opts = argparse.Namespace(
            retry=OLD, pkg=str(self.pkg), new_sid=NEW, job="J1", trace_dir=None, quiet=None
        )
        rc = oldwin_sched.run_retry(
            opts,
            env=self.env,
            now=NOW,
            backend=Backend(),
            **{k: v for k, v in self.kw().items() if k not in ("env", "now")},
        )
        self.assertEqual((rc, removed, oldwin.retry_count(self.pkg)), (0, ["J1"], 0), "(d)")
        self.assertIn("留：", oldwin.take_unread_notice(NEW))
        self.assertEqual(oldwin_sched.sweep(backend=Backend(), info=lambda label: {}), [])
        self.assertTrue(path.is_file(), "sweep 不碰否決檔")
        newer = self.dir / "handoff" / f"{OLD}_20261119T130000Z.md"
        newer.write_text(f"sid={OLD}\n", encoding="utf-8")
        self.assertFalse(oldwin.vetoed(newer), "(f) 新交接包不受舊否決影響")

    def test_at_wp_85_the_forward_escape_prefix_writes_the_veto_via_the_hook_path(self) -> None:
        """`forward.prompt_verdict` 的 `留：`／`留:` 分支寫否決（hook 檔不改，只多一行呼叫）。"""
        from lib.sessionctl import forward  # noqa: PLC0415

        payload = {
            "session_id": OLD,
            "prompt": "留：先留著",
            "transcript_path": str(self.dir / "t.jsonl"),
        }
        verdict = forward.prompt_verdict(payload, self.env, now=NOW)
        self.assertEqual(verdict["kind"], "pass")
        self.assertTrue(oldwin.vetoed(self.pkg))


class R217ParkGateTest(Base):
    """park 到點：先關再開、`skip(spawned)`、重排與放棄、否決、sdk-cli。AT-WP-70／71／88；
    MU-WP-20。"""

    def marker(self, label: str = "AutoSDD_HandoffSpawn_d4ed2654_202611191200") -> dict:
        stamp = NOW.isoformat()
        marker = {
            "schema": park.SCHEMA,
            "sid": OLD,
            "route": park.ROUTE_H,
            "status": "armed",
            "parked_at": stamp,
            "reset_at": None,
            "fire_at": stamp,
            "axis": None,
            "pkg": str(self.pkg),
            "why": "測試用原因文字",
            "valid_until": (NOW + timedelta(hours=1)).isoformat(),
            "jobs": [{"label": label, "role": "primary", "fire_at": stamp, "credential": "c"}],
            "reason": "r",
            "outcome": None,
        }
        self.assertTrue(park.write_marker(marker)[0])
        return marker

    def seams(self, api, armed: list | None = None, **extra) -> dict:
        def arm(label, argv, cwd, fire, **_kw):
            (armed if armed is not None else []).append((label, fire))
            return 0, f"NextRunTime {fire.isoformat()}"

        S = {
            "arm": arm,
            "sessions_dir": self.dir / "sessions",
            "created_of": lambda pid: FT,
            "oldwin": {
                "api": api,
                "self_pid": 999,
                "sleep": lambda s: None,
                "wait": 0.2,
                "projects_dir": self.dir / "projects",
                "platform_name": "win32",
                "roster_running": lambda *a, **k: [],
                "sessions_dir": self.dir / "sessions",
                "created_of": lambda pid: FT,
            },
        }
        S.update(extra)
        return S

    def test_at_wp_71_close_before_resume_and_a_busy_window_is_never_doubled(self) -> None:
        """(a) 五條件成立 ⇒ 關閉並回 go（呼叫端接著才 resume，順序＝先關後開）；(b) ② 不成立（busy）
        ⇒ 不關、
        不 resume、park 自己的到點排程重排（retry）。MU-WP-20：不查就會在舊窗還活著時開第二個同 sid
        視窗。"""
        self.marker()
        api = FakeApi(_tree())
        gate = oldwin_park.resume_gate(OLD, self.pkg, self.env, NOW, self.seams(api))
        self.assertEqual(
            (gate["act"], sorted(api.terminated)), ("go", sorted([PID, 101, 102, 104]))
        )
        self.setUp()
        self.registry(status="busy")
        self.marker()
        armed: list = []
        api2 = FakeApi(_tree())
        gate2 = oldwin_park.resume_gate(OLD, self.pkg, self.env, NOW, self.seams(api2, armed))
        self.assertEqual((gate2["act"], api2.terminated, len(armed)), ("retry", [], 1))
        self.assertEqual(oldwin.retry_count(self.pkg), 1)
        self.assertEqual(len(park.read_marker(OLD)["jobs"]), 1)

    def test_at_wp_88_four_blocked_attempts_rearm_exactly_three_times_then_fail(self) -> None:
        """(b) ② 連續不成立 4 次：park 重排恰 3 次、第 4 次到點回 fail（呼叫端寫 failed handback）、
        不再重排。"""
        self.registry(status="busy")
        self.marker()
        armed: list = []
        acts = []
        for n in range(4):
            if n:  # 每次到點都是新的排程名（含觸發分鐘）；模擬 park 把標記的 job 換成最新那個
                self.marker(label=armed[-1][0])
            acts.append(
                oldwin_park.resume_gate(
                    OLD, self.pkg, self.env, NOW, self.seams(FakeApi(_tree()), armed)
                )["act"]
            )
        self.assertEqual((acts, len(armed)), (["retry", "retry", "retry", "fail"], 3))

    def test_at_wp_88_a_live_sdk_cli_process_is_a_live_driver_and_a_veto_skips(self) -> None:
        """(d) 同 sid 有活著的 `entrypoint=sdk-cli` 行程 ⇒ skip（不關不開）；(e) 否決成立 ⇒
        `skip(kept_by_user)`、
        不 resume、不重排、寫 handback 說明。"""
        self.registry(entrypoint="sdk-cli")
        self.marker()
        api = FakeApi(_tree())
        self.assertEqual(
            oldwin_park.resume_gate(OLD, self.pkg, self.env, NOW, self.seams(api)),
            {"act": "skip", "reason": "live_driver"},
        )
        self.assertEqual(api.terminated, [])
        self.registry()
        self.pkg.with_suffix(".sealed").write_text(NOW.isoformat(), encoding="utf-8")
        oldwin.record_keep_veto(OLD, "x", self.env, NOW)
        armed: list = []
        with unittest.mock.patch(
            "resume_route.handback_report", lambda name: self.dir / f"{name}.md"
        ):
            gate = oldwin_park.resume_gate(OLD, self.pkg, self.env, NOW, self.seams(api, armed))
        self.assertEqual(
            (gate, armed, api.terminated), ({"act": "skip", "reason": "kept_by_user"}, [], [])
        )
        self.assertTrue((self.dir / f"{OLD}_park_kept.md").is_file())

    def test_at_wp_70_a_package_that_was_already_spawned_skips_without_resume(self) -> None:
        """park 到點：交接包已有 spawn 痕跡（未 ack）⇒ `skip(spawned)`；不呼叫 `claude -r`（同型洞：
        forward 或
        `--spawn` 已開出新 session、對方還沒 ack，park 不得再開舊 sid）。"""
        self.set_ack(False)
        marker = self.marker()
        label = marker["jobs"][0]["label"]
        trace = self.dir / "trace" / "autosdd_session_switch.jsonl"
        trace.write_text(
            json.dumps(
                {
                    "event": "session_switch_spawned",
                    "handoff": str(self.pkg),
                    "at": _iso(1),
                    "pid": 4321,
                    "ok": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        transcript = self.write_transcript(OLD, [_human(60)])
        resumed: list = []
        S = {
            "transcript": lambda sid: transcript,
            "alive": lambda pid: False,
            "resume": lambda *a, **k: resumed.append(1) or 0,
            "disarm": lambda name: 0,
            "jobs": lambda prefix: [],
            "spawn": lambda pkg: self.fail("不得走到 spawn"),
        }
        rc = park_cli.run(
            [
                "park",
                "--fire",
                "--job",
                label,
                "--session-id",
                OLD,
                "--pkg",
                str(self.pkg),
                "--fire-at",
                NOW.isoformat(),
            ],
            env=self.env,
            now=NOW,
            seams=S,
        )
        self.assertEqual((rc, resumed), (0, []))
        self.assertEqual(park.read_marker(OLD)["outcome"]["event"], "spawned")

    def test_the_park_cli_fire_runs_the_gate_before_resume(self) -> None:
        """`_cmd_fire` 整條：舊窗可關 ⇒ 先關（假 api 的 terminate）再 resume（呼叫順序斷言）。"""
        marker = self.marker()
        label = marker["jobs"][0]["label"]
        self.set_ack(False)
        usage = {
            "input_tokens": 100,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 50_000,
        }
        transcript = self.write_transcript(
            OLD,
            [_human(60), {"type": "assistant", "timestamp": _iso(59), "message": {"usage": usage}}],
        )
        calls: list = []
        api = FakeApi(_tree())
        original = api.terminate
        api.terminate = lambda h: (calls.append("close"), original(h))[1]
        S = self.seams(
            api,
            transcript=lambda sid: transcript,
            alive=lambda pid: False,
            resume=lambda *a, **k: calls.append("resume") or 0,
            spawn=lambda pkg: calls.append("SPAWN") or 0,
            disarm=lambda name: 0,
            jobs=lambda prefix: [],
        )
        rc = park_cli.run(
            [
                "park",
                "--fire",
                "--job",
                label,
                "--session-id",
                OLD,
                "--pkg",
                str(self.pkg),
                "--fire-at",
                NOW.isoformat(),
            ],
            env=self.env,
            now=NOW,
            seams=S,
        )
        self.assertEqual(rc, 0)
        self.assertEqual([c for c in calls if c in ("close", "resume")][-1], "resume")
        self.assertEqual(calls[0], "close", f"先關後開：{calls}")


class R217PidReuseSpawnTest(Base):
    def test_at_wp_78_a_reused_pid_no_longer_blocks_a_legitimate_spawn(self) -> None:
        """spawn 痕跡的 pid 對應的現行行程建立時刻晚於痕跡 `at`（pid 重用），且痕跡已逾
        SPAWN_DEDUP_SECONDS
        ⇒ 不拒絕；pid 與建立時刻相符時照舊拒絕。"""
        self.set_ack(False)
        at = NOW - timedelta(hours=1)
        trace = self.dir / "trace" / "autosdd_session_switch.jsonl"
        trace.write_text(
            json.dumps(
                {
                    "event": "session_switch_spawned",
                    "handoff": str(self.pkg),
                    "at": at.isoformat(),
                    "pid": 4321,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        reused = winproc.epoch_to_filetime((NOW - timedelta(minutes=10)).timestamp())
        genuine = winproc.epoch_to_filetime((at - timedelta(seconds=10)).timestamp())
        self.assertEqual(
            handoff._duplicate_refusals(self.pkg, NOW, lambda pid: True, lambda pid: reused), []
        )
        refused = handoff._duplicate_refusals(self.pkg, NOW, lambda pid: True, lambda pid: genuine)
        self.assertEqual(len(refused), 1)
        self.assertTrue(
            handoff._duplicate_refusals(self.pkg, NOW, lambda pid: True, lambda pid: None),
            "取不到建立時刻 ⇒ 偏安全：照舊拒絕",
        )


class R217RealProcessTreeTest(unittest.TestCase):
    """真行程（不是假 api）：自己 spawn 一棵沙盒行程樹，驗 `terminate_tree_verified` 真的以 handle
    砍樹。
    E2E-WP-54 的「真行程」半（沙盒視窗那半是 RealVerify 的 RV-WP52～54）。只終止本測試自己開的行程。
    非 Windows：`WinApi` 取不到 handle ⇒ 拒絕且什麼都不砍——兩個分支都斷言，不 skip。"""

    PARENT = (
        "import subprocess, sys, time\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        "print(kid.pid, flush=True)\n"
        "time.sleep(120)\n"
    )

    def _spawn(self, code: str):
        import subprocess  # noqa: PLC0415

        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.addCleanup(self._reap, proc)
        return proc

    @staticmethod
    def _reap(proc) -> None:
        import subprocess  # noqa: PLC0415

        if sys.platform == "win32" and proc.poll() is None:  # 只砍自己開的 pid 的樹
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        proc.stdout.close()

    def test_a_real_tree_dies_leaf_first_and_a_bystander_survives(self) -> None:
        import time  # noqa: PLC0415

        api = winproc.WinApi()
        tree = self._spawn(self.PARENT)
        tree.stdout.readline()  # 等孫行程起來（它印出 pid）
        bystander = self._spawn("import time; time.sleep(120)")
        time.sleep(0.5)
        handle = api.open(tree.pid)
        born = api.created(handle)
        api.close(handle)
        res = oldwin.procstop.terminate_tree_verified(
            tree.pid, born or 0, api=api, images=frozenset({"python.exe", "pythonw.exe"}), wait=10
        )
        if sys.platform == "win32":
            self.assertTrue(res["ok"], res)
            self.assertGreaterEqual(len(res["killed"]), 2, "至少父與孫都被砍")
            self.assertIsNotNone(tree.poll(), "樹根已結束")
            self.assertIsNone(bystander.poll(), "無關行程不受影響")
            for pid in res["pids"]:
                probe = api.open(pid)
                self.assertTrue(probe is None or not api.running(probe), f"pid {pid} 應已結束")
                api.close(probe)
        else:
            self.assertEqual((res["ok"], res["reason"]), (False, "open_failed"))
            self.assertIsNone(tree.poll(), "非 Windows：什麼都不砍")

    def test_a_stale_proc_start_aborts_without_killing_anything(self) -> None:
        """procStart 差 1（pid 重用的樣子）⇒ handle 上驗不過、中止，行程仍活。MU-WP-23
        的真行程版。"""
        api = winproc.WinApi()
        proc = self._spawn("import time; print(1, flush=True); time.sleep(120)")
        proc.stdout.readline()
        handle = api.open(proc.pid)
        born = api.created(handle)
        api.close(handle)
        res = oldwin.procstop.terminate_tree_verified(
            proc.pid, (born or 0) + 1, api=api, images=frozenset({"python.exe"}), wait=2
        )
        self.assertFalse(res["ok"])
        self.assertEqual(
            res["reason"], "procstart_mismatch" if sys.platform == "win32" else "open_failed"
        )
        self.assertIsNone(proc.poll(), "驗證失敗不得砍任何東西")

    def test_the_image_allowlist_protects_a_python_sleeper_from_the_real_close_path(self) -> None:
        """預設白名單是 `claude.exe`／`node.exe`：真的 python 行程即使 procStart 全對也不會被砍。"""
        api = winproc.WinApi()
        proc = self._spawn("import time; print(1, flush=True); time.sleep(120)")
        proc.stdout.readline()
        handle = api.open(proc.pid)
        born = api.created(handle)
        api.close(handle)
        res = oldwin.procstop.terminate_tree_verified(proc.pid, born or 0, api=api, wait=2)
        self.assertFalse(res["ok"])
        self.assertIsNone(proc.poll())


class R217RealSleeperIsNeverKilledTest(Base):
    """E2E-WP-54（真行程半）：一支無關的真 python sleeper，其 pid 出現在沙盒登記檔與 spawn 痕跡裡，
    但 procStart 故意差 1／映像不在白名單／建立時刻晚於痕跡 `at` ⇒ close 不砍、spawn 前置不誤拒，
    sleeper 全程活著。非 Windows 取不到 handle ⇒ 以平台理由拒絕，同樣不砍（兩個分支都斷言）。"""

    def _sleeper(self):
        import subprocess  # noqa: PLC0415

        code = "import time; print(1, flush=True); time.sleep(120)"
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.addCleanup(lambda: (proc.kill(), proc.wait(timeout=10), proc.stdout.close()))
        proc.stdout.readline()
        api = winproc.WinApi()
        handle = api.open(proc.pid)
        born = api.created(handle)
        api.close(handle)
        return proc, born or 0

    def test_a_wrong_proc_start_or_a_non_claude_image_never_kills_the_sleeper(self) -> None:
        proc, born = self._sleeper()
        for start, why in ((born + 1, "procStart 差 1"), (born, "映像不在白名單")):
            self.registry(pid=proc.pid, procStart=start)
            res = oldwin.close_if_eligible(
                OLD,
                NEW,
                self.pkg,
                **self.kw(created_of=procstop.created_filetime, platform_name=None),
            )
            self.assertFalse(res["closed"], why)
            self.assertIsNone(proc.poll(), f"{why}：sleeper 必須仍活著")
            if sys.platform == "win32":
                expect = "identity_unverified" if start != born else "image_not_allowed"
                self.assertEqual(res["reason"], expect, why)
            else:
                self.assertEqual(res["reason"], "platform_not_windows")
        self.assertTrue(oldwin.events("oldwin_close_refused") or sys.platform != "win32")

    def test_at_wp_78_a_real_reused_pid_does_not_block_a_legitimate_spawn(self) -> None:
        """spawn 前置（`_duplicate_refusals`）用真 GetProcessTimes：痕跡 `at` 在 sleeper 建立之前 1
        小時 ⇒ pid
        被重用 ⇒ 不拒絕；`at` 緊貼建立時刻（age < SPAWN_DEDUP_SECONDS）⇒ 照舊拒絕。"""
        proc, _born = self._sleeper()
        self.set_ack(False)
        real_now = datetime.now().astimezone()
        trace = self.dir / "trace" / "autosdd_session_switch.jsonl"

        def refusals(at: datetime) -> list:
            rec = {
                "event": "session_switch_spawned",
                "handoff": str(self.pkg),
                "at": at.isoformat(),
                "pid": proc.pid,
            }
            trace.write_text(json.dumps(rec) + "\n", encoding="utf-8")
            return handoff._duplicate_refusals(self.pkg, real_now, handoff._alive)

        self.assertEqual(refusals(real_now - timedelta(hours=1)), [])
        self.assertEqual(len(refusals(real_now - timedelta(seconds=5))), 1)


class R217StatusAndSweepTest(Base):
    def test_at_wp_89_status_lists_pending_and_stale_and_sweep_deletes_only_stale(self) -> None:
        """`SCH` 列出 3 個工作：待觸發／已執行且 NextRunTime 空／對應已否決交接包。status 排程區 3
        列、狀態
        pending／stale／stale；`oldwin --sweep` 刪 2 留 1；否決檔不被刪。"""
        labels = [f"AutoSDD_OldWinClose_{OLD[:8]}_{t}" for t in ("1210", "1100", "1220")]
        vetoed = self.dir / "handoff" / f"{NEW}_20261119T100000Z.md"
        vetoed.write_text(f"sid={NEW}\n", encoding="utf-8")
        oldwin_sched._index(
            {labels[0]: {"handoff": str(self.pkg)}, labels[2]: {"handoff": str(vetoed)}}
        )
        oldwin.veto_path(vetoed, True).parent.mkdir(parents=True, exist_ok=True)
        oldwin.veto_path(vetoed, True).write_text("{}", encoding="utf-8")
        infos = {
            labels[0]: {"next": "2026-11-19T12:10:00", "last": ""},
            labels[1]: {"next": "", "last": "2026-11-19T11:00:00"},
            labels[2]: {"next": "x", "last": ""},
        }

        class Backend:
            jobs = list(labels)

            def list_jobs(self, prefix):
                return [j for j in self.jobs if j.startswith(prefix)]

            def disarm(self, name):
                self.jobs.remove(name)
                return 0

        be = Backend()
        rows = oldwin_sched.schedule_rows(backend=be, info=infos.get)
        self.assertEqual(
            {r["label"]: r["status"] for r in rows},
            {labels[0]: "pending", labels[1]: "stale", labels[2]: "stale"},
        )
        text = oldwin_sched.status_text(
            backend=be, info=infos.get, env=self.env, sessions_dir=self.dir / "sessions"
        )
        self.assertEqual(text.count("舊窗重試排程："), 3)
        removed = oldwin_sched.sweep(backend=be, info=infos.get)
        self.assertEqual((sorted(removed), be.jobs), (sorted(labels[1:]), [labels[0]]))
        self.assertTrue(oldwin.vetoed(vetoed), "否決檔不被刪")


class R217NoticeTest(Base):
    def test_a_notice_is_voiced_once_then_marked_read(self) -> None:
        """AT-WP-77（儲存層）：notice 有 1 筆未讀 ⇒ 第一次取到全文（含 pid）、之後標已讀、不重複。
        """
        oldwin.notice(NEW, f"已關閉舊視窗 pid={PID}（sid {OLD}）。{oldwin._GONE_NOTE}。")
        first = oldwin.take_unread_notice(NEW)
        self.assertIn(f"pid={PID}", first)
        self.assertIn("未送出的文字不會保留", first)
        self.assertEqual(oldwin.take_unread_notice(NEW), "")
        oldwin.notice(NEW, "第二筆")
        self.assertEqual(oldwin.take_unread_notice(NEW), "第二筆")


def _started(tool_use_id: str, task_id: str) -> dict:
    """背景 shell 啟動的 tool_result（真逐字稿形態：`Command running in background with ID`）。"""
    text = (
        f"Command running in background with ID: {task_id}. Output is being written to: "
        f"C:\\tmp\\{task_id}.output. You will be notified."  # platform-ok: 純文字
    )
    return {
        "type": "user",
        "timestamp": _iso(19),
        "message": {
            "role": "user",
            "content": [{"tool_use_id": tool_use_id, "type": "tool_result", "content": text}],
        },
    }


def _task_stop_result(task_id: str, command: str) -> dict:
    """`TaskStop` 的 tool_result（真逐字稿形態：JSON 字串，含 `Successfully stopped task`）。"""
    body = json.dumps(
        {
            "message": f"Successfully stopped task: {task_id} ({command})",
            "task_id": task_id,
            "task_type": "local_bash",
            "command": command,
        }
    )
    return {
        "type": "user",
        "timestamp": _iso(15),
        "message": {
            "role": "user",
            "content": [{"tool_use_id": "toolu_stop", "type": "tool_result", "content": body}],
        },
    }


class R218F7TaskStopIsNotRunningTest(Base):
    """R217 F7（掌舵者 2026-11-21 真機：舊視窗被「已被 TaskStop 的計時 shell」誤判成仍在跑，三次
    重試後放棄）。TaskStop 結束沒有 `<task-notification>`，要認 tool_result 的
    `Successfully stopped task: <task_id>`，並以啟動 tool_result 把 task_id 對回 tool_use_id。"""

    sleeper = 'Start-Sleep -Seconds 305; "timer-done"'

    def _transcript(self, *, stop: bool, other_task: bool = False) -> Path:
        recs = [
            _human(self.human_minutes),
            _bg_call("toolu_bg", self.sleeper),
            _started("toolu_bg", "b53oeig8w"),
        ]
        if stop:
            recs.append(_task_stop_result("zzz9other" if other_task else "b53oeig8w", self.sleeper))
        return self.write_transcript(OLD, recs)

    def test_a_stopped_background_shell_no_longer_blocks_condition_2(self) -> None:
        path = self._transcript(stop=False)
        self.assertEqual(
            list(oldwin.bg_shells(path)[0].values()), [self.sleeper], "對照：沒停＝在跑"
        )
        self.assertEqual(self.eligible()["reason"], "agents_or_shell_running")
        path = self._transcript(stop=True)
        running, every = oldwin.bg_shells(path)
        self.assertEqual(
            (running, every), ({}, {"toolu_bg"}), "停了＝不在跑；呼叫 id 仍留給 TOCTOU"
        )
        self.assertTrue(self.eligible()["ok"])

    def test_stopping_some_other_task_does_not_clear_this_shell(self) -> None:
        """MU：task_id 對不上就不得放行（不是「出現 stopped 字樣就清空」）。"""
        self._transcript(stop=True, other_task=True)
        self.assertEqual(self.eligible()["reason"], "agents_or_shell_running")

    def test_a_shell_without_a_start_record_stays_running(self) -> None:
        """看不懂就不關：沒有啟動 tool_result（對不回 task_id）時，TaskStop 字樣不能放行它。"""
        self.write_transcript(
            OLD,
            [
                _human(10),
                _bg_call("toolu_bg", self.sleeper),
                _task_stop_result("b53oeig8w", self.sleeper),
            ],
        )
        self.assertEqual(self.eligible()["reason"], "agents_or_shell_running")


class R218F7ImageFamilyTest(unittest.TestCase):
    """QuotaWall DES §9 D-I：映像家族比對。自動更新把執行中的 claude.exe 改名成
    `claude.exe.old.<數字>.<pid>`，精確比對會擋掉。"""

    def test_family_members(self) -> None:
        for name in ("claude.exe", "CLAUDE.EXE", "node.exe", "claude.exe.old.1795116108051.41752"):
            self.assertTrue(procstop.image_allowed(name), name)

    def test_non_members(self) -> None:
        for name in (
            "",
            "python.exe",
            "pythonw.exe",
            "claude.exe.old",
            "claude.exe.old.1.x",
            "claude.exe.old.1795116108051",
            "xclaude.exe",
            "claude.exe.bak.1.2",
            "claude.exe.old.1.2.3",
            "claude.exe.old.1.2.exe",
        ):
            self.assertFalse(procstop.image_allowed(name), name)

    def test_the_renamed_image_closes_but_identity_checks_stay_strict(self) -> None:
        renamed = _tree()
        renamed[PID]["image"] = "claude.exe.old.1795116108051.41752"
        api = FakeApi(renamed)
        res = procstop.terminate_tree_verified(
            PID, FT, api=api, self_pid=999, sleep=lambda s: None, wait=0.2
        )
        self.assertEqual((res["ok"], res["reason"]), (True, ""))
        wrong = _tree()
        wrong[PID]["image"] = "claude.exe.old.1795116108051.41752"
        res = procstop.terminate_tree_verified(PID, FT + 1, api=FakeApi(wrong), self_pid=999)
        self.assertEqual(res["reason"], "procstart_mismatch", "procStart 不符仍不砍")


class R218F7AbandonIsNeverSilentTest(Base):
    def test_degraded_close_says_pid_and_manual_close_and_does_not_retry(self) -> None:
        """image_not_allowed／open_failed＝關不了：不排重試死路，記 `oldwin_close_degraded`，新
        session
        出聲（白話、指名 pid、請手動關閉舊視窗）。"""
        python = _tree()
        python[PID]["image"] = "python.exe"
        res = oldwin.close_if_eligible(
            OLD,
            NEW,
            self.pkg,
            api=FakeApi(python),
            self_pid=999,
            sleep=lambda s: None,
            wait=0.2,
            **self.kw(),
        )
        self.assertFalse(res["closed"])
        self.assertIn(f"pid={PID}", res["text"])
        self.assertIn("請手動關閉舊視窗", res["text"])
        self.assertTrue(oldwin.events("oldwin_close_degraded"))
        self.assertEqual(oldwin.retry_count(self.pkg), 0)
        self.assertIn("請手動關閉舊視窗", oldwin.take_unread_notice(NEW))

    def test_abandon_notice_names_pid_and_keeps_reminding_until_the_window_closes(self) -> None:
        self.write_transcript(OLD, [_human(self.human_minutes), _bg_call("toolu_bg", "sleep 99")])
        for _ in range(oldwin.MAX_RETRIES + 1):
            res = self.close()
        self.assertTrue(res["abandoned"])
        self.assertIn(f"pid={PID}", res["text"])
        self.assertIn("請手動關閉舊視窗", res["text"])
        self.assertIn("請手動關閉舊視窗", oldwin.take_unread_notice(NEW))
        kw = {"sessions_dir": self.dir / "sessions", "created_of": lambda pid: FT}
        first = oldwin.pending_manual_close(NEW, **kw)
        self.assertIn(f"pid={PID}", first)
        self.assertEqual(oldwin.pending_manual_close(NEW, **kw), first, "不是一次性：每回合都提醒")
        (self.dir / "sessions" / f"{PID}.json").unlink()  # 視窗被人關掉
        self.assertEqual(oldwin.pending_manual_close(NEW, **kw), "")
        self.assertEqual(oldwin.pending_manual_close("someone-else", **kw), "")


class R218F7HandoverClosingRuleTest(unittest.TestCase):
    def test_spawn_output_tells_the_old_window_to_only_point_to_the_new_one(self) -> None:
        self.assertIn("決定請到新視窗回答", handoff.HANDOVER_CLOSING_RULE)
        self.assertIn("不要重列待決事項", handoff.HANDOVER_CLOSING_RULE)


if __name__ == "__main__":
    unittest.main()
