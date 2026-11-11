# 受測面：tools/lib/selfimproving/memdir.py（程式碼鎖，非散文）
"""SelfImproving P7 MM 半：巡邏器對 M 類（記憶）提案自動推進（TCS-SelfImproving-P7 §1 的
AC-SI-48-1～48-5；受測 `memdir.py` 與 `patrolrun._advance_prop` 的 M 類接線）。

夾具 `_selfimproving_p7_fixtures.py`（`p7x`）的 `repo_m`：M 類 PROP＋暫存的 `claude_home`。
動詞一律由
替身 `Rig7` 承接（`Deps.verbs` 記錄 argv）；需要真實後像者以 `AppRig` 模擬 `promote`／`rollback`
對記憶目錄的效果並落 `app.*` 事件。每條 AT 的測試名帶編號（`AT_748_<AC>_<序>`）。
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p7_fixtures as p7x
from _selfimproving_p4_fixtures import MIN, H, O
from _selfimproving_p7_fixtures import P7TestCase, Rig7, add_prop

from lib.selfimproving import manifest, memdir, nextstep, patrol, transcript

ROOT = fx.ROOT
PKG = ROOT / "tools" / "lib" / "selfimproving"
MEM_VERBS = ("sandbox", "verify", "promote", "rollback")
NO_AUTO_COMMIT = {"sched_auto_commit": False}


def setUpModule() -> None:
    fx.setup("si_p7m_")


def tearDownModule() -> None:
    fx.teardown()


def argv_of(R: Path, verb: str, pid: str, *extra: str) -> list[str]:
    """巡邏器呼叫動詞的完整 argv（`ctx.verb` 於末端補 `--repo`）。"""
    return [verb, pid, *extra, "--by", "patrol", "--repo", str(R)]


def commits(R: Path) -> int:
    return int(subprocess.run(["git", "-C", str(R), "rev-list", "--count", "HEAD"], check=True,
                              capture_output=True, encoding="utf-8", errors="replace",
                              env=fx.genv()).stdout.strip())


class AppRig(Rig7):
    """`promote`／`rollback` 替身：對記憶目錄做可見的改動並落 `app.*` 事件（`post_sha256` 取當下的
    manifest）；`tamper`＝落事件之後立即再改一次記憶檔（TCS AT-748-4-2 的注入點）；`bad_rollback`＝
    `app.rollback` 記不對的 `post_sha256`。"""

    def __init__(self, n: int, mem: Path, *, tamper: bool = False, bad_rollback: bool = False,
                 **kw) -> None:
        super().__init__(**kw)
        self.n, self.mem, self.tamper, self.bad_rollback = n, mem, tamper, bad_rollback

    def _run(self, R: Path, argv: list[str]):
        verb = argv[0]
        if verb not in ("promote", "rollback"):
            return super()._run(R, argv)
        demo = self.mem / "demo.md"
        if verb == "promote":
            demo.write_bytes(demo.read_bytes() + b"promoted line\n")
        sha = manifest.paths_manifest(self.mem, ["memory/demo.md"], strip="memory/")
        if self.tamper:
            demo.write_bytes(demo.read_bytes() + b"someone else edited\n")
        if verb == "promote":
            ev = fx.promote_ev(self.n, post_sha256=sha)
        else:
            ev = fx.rollback_ev(self.n, post_sha256=fx.H(1) if self.bad_rollback else sha)
        fx.append_events(R, [ev])
        return 0, f"ok app.{verb}\n", ""


class ChainRig(AppRig):
    """完整鏈替身：`sandbox`／`verify`／`card`／`measure` 各落一筆對應事件
    （模擬真動詞的帳本效果）。"""

    def _run(self, R: Path, argv: list[str]):
        steps = {"sandbox": lambda: fx.sandbox_ev(self.n), "verify": lambda: fx.verify_ev(self.n),
                 "card": lambda: fx.card_ev(self.n),
                 "measure": lambda: fx.ev("mea.open", "main", prop=fx.pid(self.n))}
        if argv[0] in steps:
            fx.append_events(R, [steps[argv[0]]()])
            return 0, f"ok {argv[0]}\n", ""
        return super()._run(R, argv)


class MemoryTestCase(P7TestCase):
    """M 類心跳測試基底（名稱含 TestCase：discover 守門不解析跨檔基底鏈）。"""

    def beat_spy(self, R: Path, rig: Rig7, *args: str, at=None):
        """一次心跳；回 `(rc, 本心跳的 ctx.note 呼叫 [(pid, code, detail)])`。"""
        notes, orig = [], patrol.Ctx.note

        def spy(ctx, pid, code, detail=""):
            notes.append((pid, code, detail))
            return orig(ctx, pid, code, detail)

        with mock.patch.object(patrol.Ctx, "note", spy):
            rc, out, err = self.beat7(R, at or O + H, rig, *args)
        self.assertEqual(rc, 0, out + err)
        return notes

    def coded(self, code: str) -> list[str]:
        return [ln for ln in self.logs() if f"code={code}" in ln]

    def prop_row(self, pid: str) -> dict | None:
        return next((r for r in self.report()["props"] if r["id"] == pid), None)


class TestMemoryFlag(MemoryTestCase):
    """AC-SI-48-1：M 類帶 `--memory-dir`。"""

    def test_AT_748_1_1_every_memory_verb_carries_the_flag_and_card_does_not(self):
        n, pid = 910, fx.pid(910)
        table = (("frozen", {}, "sandbox", True), ("sandboxed", {}, "verify", True),
                 ("decided", {}, "promote", True),
                 ("promoted", {"rollback": True}, "rollback", True),
                 ("verified", {"carded": False}, "card", False))
        for state, kw, verb, flagged in table:
            with self.subTest(state=state):
                R, mem = p7x.repo_m(self, state, n=n, prm=NO_AUTO_COMMIT, **kw)
                rig = Rig7()
                self.beat_spy(R, rig)
                calls = rig.verbs_named(verb, pid)
                self.assertTrue(calls, rig.verbs_log)
                extra = ("--memory-dir", str(mem)) if flagged else ()
                tail = ("--issue",) if verb == "card" else ()
                want = argv_of(R, verb, pid, *tail, *extra)
                if verb == "card":  # card 的旗標序：`--issue` 在 `--by` 之前、不含記憶目錄
                    self.assertNotIn("--memory-dir", calls[0])
                self.assertEqual(calls[0], want)
                self.assertTrue(all(c == want for c in calls), calls)

    def test_AT_748_1_2_resolve_is_transcript_dir_memory_with_a_memory_index(self):
        R, mem = p7x.repo_m(self, "frozen")
        self.assertEqual(memdir.resolve(R), str(transcript.transcript_dir(R) / "memory"))
        self.assertEqual(memdir.resolve(R), str(mem))
        self.assertEqual(memdir.target(R), str(mem))
        # 換一個注入的 claude_home（含空白與非英數的路徑）：解析式仍跟著 transcript_dir 走
        other = fx.new_dir("ch 家")
        (other / "projects").mkdir(parents=True)
        with mock.patch.object(transcript, "claude_home", return_value=other):
            self.assertEqual(memdir.resolve(R), None)  # 新家目錄下沒有記憶目錄
            fx.memory_dir(transcript.transcript_dir(R))
            self.assertEqual(memdir.resolve(R), str(transcript.transcript_dir(R) / "memory"))
        # slug 與 `transcript_dir` 同式：repo 路徑的非英數一律轉 `-`
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(R.resolve()))
        self.assertEqual(transcript.transcript_dir(R).name, slug)
        # 沒有 MEMORY.md、是檔案、不存在 ⇒ None
        for kind in ("nomd", "file", "none"):
            with self.subTest(kind=kind):
                R2, _ = p7x.repo_m(self, "frozen", mem=kind, n=911)
                self.assertIsNone(memdir.resolve(R2))
        # 不自寫 slug 規則：memdir 原始碼不含 re／slug／claude_home
        text = (PKG / "memdir.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertNotIn("re", imported)
        self.assertNotIn("slug", text.replace("slug 規則", ""))
        self.assertEqual([ln for ln in text.splitlines() if "claude_home" in ln], [])

    def test_AT_748_1_E_1_p_class_never_gets_the_flag_and_idle_m_class_is_not_resolved(self):
        R = self.enabled_repo(prm=NO_AUTO_COMMIT)
        pid = add_prop(R, 124, "frozen")
        fx.commit_all(R, "p class")
        rig = Rig7()
        with mock.patch.object(memdir, "resolve", wraps=memdir.resolve) as spy:
            self.beat_spy(R, rig)
        self.assertTrue(rig.verbs_named("sandbox", pid))
        self.assertFalse([a for a in rig.verbs_log if "--memory-dir" in a], rig.verbs_log)
        self.assertEqual(spy.call_count, 0)
        for state in ("proposed", "returned", "rejected"):
            with self.subTest(state=state):
                R2, _ = p7x.repo_m(self, state, n=912)
                rig2 = Rig7()
                with mock.patch.object(memdir, "resolve", wraps=memdir.resolve) as spy2:
                    self.beat_spy(R2, rig2)
                self.assertEqual(spy2.call_count, 0)
                self.assertEqual([a for a in rig2.verbs_log if a[0] in (*MEM_VERBS, "card")], [])


class TestUnresolved(MemoryTestCase):
    """AC-SI-48-2：解析不到記原因碼、不推進。"""

    def test_AT_748_2_1_unresolvable_directory_blocks_every_memory_verb(self):
        pid = fx.pid(910)
        for kind in ("none", "nomd", "file"):
            with self.subTest(kind=kind):
                R, mem = p7x.repo_m(self, "frozen", mem=kind)
                rig = Rig7()
                notes = self.beat_spy(R, rig)
                self.assertEqual([a for a in rig.verbs_log if a[0] in MEM_VERBS], [])
                self.assertEqual(notes, [(pid, "MEMORY-DIR-UNRESOLVED", str(mem))])
                row = self.prop_row(pid)
                self.assertEqual((row["code"], row["who"]), ("MEMORY-DIR-UNRESOLVED", "主機管理者"))
                self.assertIn(nextstep.sanitize(str(mem)), row["text"])
                self.assertEqual(len(self.coded("MEMORY-DIR-UNRESOLVED")), 1, self.logs())
                (self.home / "patrol" / "patrol.log").unlink()

    def test_AT_748_2_1_b_every_pending_step_is_blocked_not_only_sandbox(self):
        table = (("sandboxed", {}), ("decided", {}), ("promoted", {"rollback": True}))
        for state, kw in table:
            with self.subTest(state=state):
                R, _ = p7x.repo_m(self, state, mem="none", **kw)
                rig = Rig7()
                notes = self.beat_spy(R, rig)
                self.assertEqual([a for a in rig.verbs_log if a[0] in MEM_VERBS], [])
                self.assertEqual([c for _, c, _ in notes], ["MEMORY-DIR-UNRESOLVED"])

    def test_AT_748_2_E_1_the_old_code_is_gone_from_patrolrun(self):
        tree = ast.parse((PKG / "patrolrun.py").read_text(encoding="utf-8"))
        consts = [n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertNotIn("MEMORY-DIR", consts)
        R, _ = p7x.repo_m(self, "frozen", mem="none")
        old = self.home / "patrol" / "patrol.log"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("2026-11-01T00:00:00+08:00 step=推進 rc=0 code=MEMORY-DIR 舊日誌行\n",
                       encoding="utf-8")
        self.beat_spy(R, Rig7())
        self.assertEqual(self.prop_row(fx.pid(910))["code"], "MEMORY-DIR-UNRESOLVED")
        self.assertNotIn("MEMORY-DIR", {r["code"] for r in self.report()["props"]})


class TestNoQuietGate(MemoryTestCase):
    """AC-SI-48-3：不加互動視窗安靜前置。"""

    def test_AT_748_3_1_m_class_promote_ignores_other_driver(self):
        results = {}
        for cls, quiet in (("M", False), ("P", False), ("M", True)):
            if cls == "M":
                R, mem = p7x.repo_m(self, "decided", prm=NO_AUTO_COMMIT)
                pid = fx.pid(910)
            else:
                R = self.enabled_repo(prm=NO_AUTO_COMMIT)
                pid = add_prop(R, 124, "decided")
                fx.commit_all(R, "p class")
            rig = Rig7(quiet=quiet)
            self.beat_spy(R, rig)
            results[(cls, quiet)] = [a[0] for a in rig.verbs_log if a[1:2] == [pid]]
            if cls == "M":
                self.assertEqual(rig.verbs_named("promote", pid)[0],
                                 argv_of(R, "promote", pid, "--memory-dir", str(mem)))
            self.assertFalse([r for r in self.report()["props"] if "OTHER-DRIVER" in r["code"]])
        self.assertEqual(results[("M", False)], results[("P", False)])
        self.assertEqual(results[("M", False)], results[("M", True)])
        self.assertNotIn("OTHER-DRIVER-M", nextstep.REASON)


class TestImages(MemoryTestCase):
    """AC-SI-48-4：前像與後像。"""

    def test_AT_748_4_1_preimage_mismatch_is_noted_and_never_retried(self):
        pid = fx.pid(910)
        R, _ = p7x.repo_m(self, "decided", prm={"sched_auto_commit": True})
        before = commits(R)
        rig = Rig7(script={"promote": (1, "reject promote PREIMAGE-MISMATCH\n", "")})
        for k in (1, 2):  # 無狀態：下一心跳記憶仍不符 ⇒ 同碼
            notes = self.beat_spy(R, rig, at=O + H + (2 * k) * MIN)
            self.assertEqual([(p, c) for p, c, _ in notes], [(pid, "PREIMAGE-MISMATCH")])
            row = self.prop_row(pid)
            self.assertEqual((row["code"], row["who"]), ("PREIMAGE-MISMATCH", "主機管理者"))
            self.assertIn("重新上卡", row["text"])
        self.assertEqual(len(rig.verbs_named("promote", pid)), 2)  # 每心跳一次，心跳內不重試
        self.assertEqual([e for e in fx.EV(R) if e["kind"] == "app.promote"
                          and e["prop"] == pid and e.get("by") == "patrol"], [])
        self.assertEqual(commits(R), before)

    def test_AT_748_4_2_postimage_mismatch_notes_but_neither_rolls_back_nor_stops(self):
        pid = fx.pid(910)
        R, mem = p7x.repo_m(self, "decided", prm={"sched_auto_commit": True})
        before = commits(R)
        rig = AppRig(910, mem, tamper=True)
        notes = self.beat_spy(R, rig)
        self.assertIn((pid, "POSTIMAGE-MISMATCH", ""), notes)
        self.assertEqual(len(self.coded("POSTIMAGE-MISMATCH")), 1, self.logs())
        row = self.prop_row(pid)
        self.assertEqual((row["code"], row["who"]), ("POSTIMAGE-MISMATCH", "主機管理者"))
        self.assertEqual(rig.verbs_named("rollback"), [])  # 不自動回滾
        self.assertTrue(rig.verbs_named("measure"))  # measure 照做
        self.assertEqual(commits(R), before + 1)  # commit 照做

    def test_AT_748_4_2_b_a_matching_postimage_is_silent(self):
        pid = fx.pid(910)
        R, mem = p7x.repo_m(self, "decided", prm={"sched_auto_commit": True})
        rig = AppRig(910, mem)
        notes = self.beat_spy(R, rig)
        self.assertEqual([c for _, c, _ in notes], [])
        self.assertEqual(self.coded("POSTIMAGE-MISMATCH"), [])
        events = fx.EV(R)
        self.assertIsNone(memdir.post_image_problems(R, events, pid, str(mem)))
        (mem / "demo.md").write_bytes(b"changed afterwards\n")
        self.assertEqual(memdir.post_image_problems(R, events, pid, str(mem)), "POSTIMAGE-MISMATCH")
        self.assertEqual(memdir.post_image_problems(R, [], pid, str(mem)), "POSTIMAGE-MISMATCH")

    def test_AT_748_4_E_1_p_class_is_never_checked_and_m_rollback_is(self):
        R = self.enabled_repo(prm=NO_AUTO_COMMIT)
        add_prop(R, 124, "decided")
        fx.commit_all(R, "p class")
        with mock.patch.object(memdir, "post_image_problems") as spy:
            self.beat_spy(R, Rig7())
        self.assertEqual(spy.call_count, 0)
        pid = fx.pid(910)
        for bad in (False, True):
            with self.subTest(bad=bad):
                R2, mem = p7x.repo_m(self, "promoted", rollback=True, prm=NO_AUTO_COMMIT)
                rig = AppRig(910, mem, bad_rollback=bad)
                notes = self.beat_spy(R2, rig)
                self.assertEqual(len(rig.verbs_named("rollback", pid)), 1)
                self.assertEqual([c for _, c, _ in notes],
                                 ["POSTIMAGE-MISMATCH"] if bad else [])
                self.assertEqual(rig.verbs_named("rollback", pid)[0],
                                 argv_of(R2, "rollback", pid, "--memory-dir", str(mem)))


class TestRegression(MemoryTestCase):
    """AC-SI-48-5：回歸與完整鏈。"""

    def test_AT_748_5_1_finished_m_class_is_silent_and_verified_gets_exactly_one_card(self):
        pid = fx.pid(910)
        for state in ("promoted", "measuring", "closed"):
            with self.subTest(state=state):
                R, _ = p7x.repo_m(self, state)
                rig = Rig7()
                with mock.patch.object(memdir, "resolve", wraps=memdir.resolve) as spy:
                    notes = self.beat_spy(R, rig)
                self.assertEqual((notes, spy.call_count), ([], 0))
                self.assertEqual([a for a in rig.verbs_log if a[0] in (*MEM_VERBS, "card")], [])
                self.assertIsNone(self.prop_row(pid))
                self.assertFalse([ln for ln in self.logs() if pid in ln and "code=-" not in ln])
                (self.home / "patrol" / "patrol.log").unlink()
        R, mem = p7x.repo_m(self, "verified", carded=False)
        rig = Rig7()
        self.beat_spy(R, rig)
        self.assertEqual(rig.verbs_named("card"), [argv_of(R, "card", pid, "--issue")])
        self.assertEqual(self.coded("MEMORY-DIR-UNRESOLVED"), [])
        R2, _ = p7x.repo_m(self, "verified", n=913)  # 已發卡、無決定 ⇒ 零動作
        rig2 = Rig7()
        self.beat_spy(R2, rig2)
        self.assertEqual([a for a in rig2.verbs_log if a[0] in (*MEM_VERBS, "card")], [])

    def test_AT_748_5_2_the_whole_chain_runs_from_approve_to_measure(self):
        pid = fx.pid(910)
        R, mem = p7x.repo_m(self, "frozen", prm={"sched_auto_commit": True})
        rig = ChainRig(910, mem)
        self.beat_spy(R, rig, at=O + H)
        flag = ("--memory-dir", str(mem))
        self.assertEqual(rig.verbs_named("sandbox", pid), [argv_of(R, "sandbox", pid, *flag)])
        self.assertEqual(rig.verbs_named("verify", pid), [argv_of(R, "verify", pid, *flag)])
        self.assertEqual(rig.verbs_named("card", pid), [argv_of(R, "card", pid, "--issue")])
        self.assertEqual(self.prop_row(pid)["code"], "WAIT-PROMOTE-DECISION")
        fx.append_events(R, [fx.dec_ev(910, "promote")])
        before = commits(R)
        self.beat_spy(R, rig, at=O + H + 3 * MIN)
        self.assertEqual(rig.verbs_named("promote", pid), [argv_of(R, "promote", pid, *flag)])
        self.assertEqual(commits(R), before + 1)
        # commit 訊息末段恰兩個 trailer（TCS AT-748-5-2「trailer 兩行」；AC-SI-49-2），APP 為本次
        # app.promote
        app = [e for e in fx.EV(R) if e["kind"] == "app.promote"][-1]["id"]
        msg = subprocess.run(["git", "-C", str(R), "log", "-1", "--format=%B"], check=True,
                             capture_output=True, encoding="utf-8", errors="replace",
                             env=fx.genv()).stdout
        tail = msg.strip("\n").split("\n\n")[-1].split("\n")
        self.assertEqual(tail, [f"SI-Patrol-App: {app}", f"SI-Patrol-Prop: {pid}"])
        self.assertTrue(rig.verbs_named("measure"))
        self.assertIsNone(self.prop_row(pid))  # measuring 且無待回滾 ⇒ 離開 props[]


if __name__ == "__main__":
    sys.exit(unittest.main())
