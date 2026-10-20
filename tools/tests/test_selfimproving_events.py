"""SelfImproving P1 事件帳本、運轉、歸因、`check` 追加項、介面與 SOP 條文的驗收測試。

對應 TCS-P1 的 EV 檔。

方法名含 AT 底線形，`pytest -k AT_110_3_1` 可單跑。夾具全用 tmp 目錄內的合成 repo（hermetic 環境，
不碰真帳本、不上網）；只唯讀存取真 repo 的 params／來源表／SOP／PRD。合成編號於執行期組出。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
from _selfimproving_fixtures import (
    EVL,
    LEDGER,
    P0_ITEMS21,
    P1_ITEMS7,
    SiTestCase,
    aid,
    ev,
    obs_id,
    pid,
    rid,
)

from lib import apply_lock
from lib.selfimproving import events as si_events
from lib.selfimproving import evwrite

TOOLS = fx.TOOLS
HEX40 = r"[0-9a-f]{40}"


def setUpModule() -> None:
    fx.setup("si_ev_")


def tearDownModule() -> None:
    fx.teardown()


def run_open_args(trigger="a", coord="tools/a.py:1", by="main"):
    return ["run-open", "--trigger", trigger, "--coord", coord, "--by", by]


def attr_root_args(obs=None, root_cause="docs/stale-note", item="DOC=docs/06_quality/", by="SA"):
    """`attr --type root` 的 CLI 引數（`tools/lib/selfimproving/writeverbs.py`）。"""
    return [
        "attr",
        "--type",
        "root",
        "--by",
        by,
        "--obs",
        obs or obs_id(1),
        "--item",
        item,
        "--root-cause",
        root_cause,
    ]


def append_raw(repo: Path, text: str) -> None:
    with (repo / EVL).open("ab") as fh:
        fh.write(text.encode("utf-8"))


def ledger_bytes(repo: Path) -> bytes | None:
    p = repo / EVL
    return p.read_bytes() if p.is_file() else None


class TestRunsAndAttribution(SiTestCase):
    def test_AT_110_3_1_run_open_five_triggers(self):
        repo = fx.p1_base()
        head = fx.head(repo)
        for i, trig in enumerate("abcde", start=1):
            rc, out, err = self.M(repo, *run_open_args(trig, "tools/lib/selfimproving/check.py:10"))
            self.assertEqual(rc, 0, err)
            self.assertRegex(out, rf"^ok run\.open seq={i} id={rid(i)} head_sha={head}\n$")
        rc, out, err = self.M(
            repo,
            "run-open",
            "--trigger",
            "a",
            "--by",
            "main",
            "--json",
            "--coord",
            "tools/a.py:1",
            "--coord",
            "`python tools/selfimproving.py check` rc=1",
        )
        self.assertEqual(rc, 0, err)
        obj = json.loads(out)
        self.assertEqual(list(obj), ["ok", "kind", "seq", "id", "head_sha"])
        self.assertEqual((obj["id"], obj["seq"]), (rid(6), 6))
        events = fx.EV(repo)
        self.assertEqual(len(events), 6)
        for i, e in enumerate(events, start=1):
            self.assertEqual(
                set(e), {"seq", "t", "kind", "by", "run", "trigger", "coords", "head_sha"}
            )
            self.assertEqual(
                (e["kind"], e["seq"], e["by"], e["head_sha"]), ("run.open", i, "main", head)
            )
        self.assertEqual([e["trigger"] for e in events], list("abcde") + ["a"])
        self.assertEqual([len(e["coords"]) for e in events], [1, 1, 1, 1, 1, 2])
        self.assertEqual(len(self.MJ(repo, "status")["open_runs"]), 6)
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "events.structure"), self.S(res, "events.transitions")), ("PASS", "PASS")
        )

    def test_AT_110_3_E_1_usage_and_state_errors(self):
        repo = fx.p1_base()
        snap0, home0 = fx.snap(repo), fx.tree_files(self.home)
        rx = rid(900 + 7)
        usage = [
            run_open_args("f"),
            ["run-open", "--trigger", "a", "--by", "main"],
            ["run-open", "--trigger", "a", "--coord", "tools/a.py:1"],
            run_open_args(by="含 空白"),
            run_open_args(by="x" * 33),
        ]
        for argv in usage:
            with self.subTest(argv=argv):
                self.usage_error(*self.M(repo, *argv), msg=str(argv))
        rc, out, _ = self.M(repo, *run_open_args(coord="本檔時間欄"))
        self.rejected(rc, out, {"COORD-NONE"}, "座標不可定位")
        self.assertIn("本檔時間欄", out)
        self.draft_ok(repo, out)
        nogit = fx.new_dir("nogit")
        shutil.copytree(repo, nogit, ignore=shutil.ignore_patterns(".git"))
        rc, out, _ = self.M(nogit, *run_open_args())
        self.rejected(rc, out, {"GIT-UNAVAILABLE"}, "非 git 目錄")
        self.draft_ok(repo, out)
        rc, out, _ = self.M(repo, "prop-new", "--run", rx, *fx.good_prop_args(repo, "P"))
        self.rejected(rc, out)
        self.assertIn("RUN-NOT-OPEN", fx.codes_of(out))
        self.draft_ok(repo, out)
        rc, out, _ = self.M(
            repo, "research", "--skip", "--run", rx, "--reason", "offline", "--note", "離線"
        )
        self.rejected(rc, out)
        self.assertIn("RUN-NOT-OPEN", fx.codes_of(out))
        self.assertEqual(fx.snap(repo), snap0)
        self.assertEqual(fx.tree_files(self.home), home0)

    def test_AT_103_2_1_run_close_records_no_event_or_outcomes(self):
        repo = fx.p1_base()
        fx.write_events(repo, fx.sc_close(), commit=True)
        rc, out, err = self.M(repo, "run-close", "--run", rid(1), "--by", "main")
        self.assertEqual(rc, 0, err)
        self.assertRegex(out, rf"^ok run\.close seq=\d+ run={rid(1)} no_event=true\n$")
        rc, out, err = self.M(repo, "run-close", "--run", rid(2), "--by", "main", "--json")
        self.assertEqual(rc, 0, err)
        obj = json.loads(out)
        self.assertEqual((obj["run"], obj["outcomes"]), (rid(2), 2))
        closes = [e for e in fx.EV(repo) if e["kind"] == "run.close"]
        self.assertEqual(set(closes[0]), {"seq", "t", "kind", "by", "run", "no_event"})
        self.assertIs(closes[0]["no_event"], True)
        self.assertEqual(set(closes[1]), {"seq", "t", "kind", "by", "run", "outcomes"})
        self.assertEqual(closes[1]["outcomes"], {pid(124): "approved", pid(125): "rejected"})
        self.assertEqual(self.MJ(repo, "status")["open_runs"], [])
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "events.structure"), self.S(res, "events.transitions")), ("PASS", "PASS")
        )

    def test_AT_103_2_E_1_run_close_rejections(self):
        repo = fx.p1_base()
        fx.write_events(
            repo, [fx.run_open_ev(1), ev("run.close", run=rid(1), no_event=True)], commit=True
        )
        n0, snap0 = len(fx.EV(repo)), fx.snap(repo)
        for argv in (["--run", rid(1)], ["--run", rid(901)]):
            rc, out, _ = self.M(repo, "run-close", *argv, "--by", "main")
            self.rejected(rc, out, {"RUN-NOT-OPEN"})
            self.draft_ok(repo, out)
        for argv in (["--run", "bad-id", "--by", "main"], ["--by", "main"]):
            self.usage_error(*self.M(repo, "run-close", *argv), msg=str(argv))
        self.assertEqual((len(fx.EV(repo)), fx.snap(repo)), (n0, snap0))

    def test_AT_105_1_1_attr_seven_kinds(self):
        repo = fx.p1_base()
        items = [
            f"DEF={fx.def_id(1)}",
            f"OBS={obs_id(2)}",
            f"RULE=AISDLC_SDD/{fx.VNEW}/governance/rules/R-9.1.yaml",
            "PLAYBOOK_STEP=tools/x.py:3",
            "DOC=docs/05_development/SelfImproving_Operations_SOP.md:5",
            "MEMORY_ENTRY=memory/foo.md:3",
            "NONE=無法歸因：缺少逐字稿",
        ]
        for i, item in enumerate(items, start=1):
            rc, out, err = self.M(repo, *attr_root_args(item=item, root_cause="tools/lock-race"))
            self.assertEqual(rc, 0, err)
            self.assertRegex(out, rf"^ok attr seq={i} id={aid(i)} type=root\n$")
        rc, out, err = self.M(
            repo,
            "attr",
            "--type",
            "root",
            "--by",
            "SA",
            "--obs",
            obs_id(1),
            "--obs",
            obs_id(4),
            "--item",
            "DOC=docs/06_quality/",
            "--item",
            f"OBS={obs_id(2)}",
            "--root-cause",
            "docs/stale-note",
            "--json",
        )
        self.assertEqual(rc, 0, err)
        obj = json.loads(out)
        self.assertEqual(list(obj), ["ok", "kind", "seq", "id", "type"])
        self.assertEqual(obj["id"], aid(8))
        events = fx.EV(repo)
        self.assertEqual([e["kind"] for e in events], ["attr"] * 8)
        for e in events:
            self.assertEqual(
                set(e), {"seq", "t", "kind", "by", "id", "type", "obs", "items", "root_cause"}
            )
        self.assertEqual(events[6]["items"], [["NONE", "無法歸因：缺少逐字稿"]])
        self.assertEqual(events[7]["obs"], [obs_id(1), obs_id(4)])
        self.assertEqual(len(events[7]["items"]), 2)
        self.assertEqual(self.S(self.check(repo), "events.structure"), "PASS")

    def test_AT_105_1_E_1_attr_rejections(self):
        repo = fx.p1_base()
        snap0 = fx.snap(repo)
        ox = obs_id(900 + 5)
        base = [
            "--by",
            "SA",
            "--obs",
            obs_id(1),
            "--item",
            "DOC=docs/06_quality/",
            "--root-cause",
            "tools/lock-race",
        ]
        usage = [
            [
                "attr",
                "--type",
                "root",
                "--by",
                "SA",
                "--obs",
                obs_id(1),
                "--item",
                "FOO=tools/x.py:1",
                "--root-cause",
                "tools/a-b",
            ],
            [
                "attr",
                "--type",
                "root",
                "--by",
                "SA",
                "--obs",
                obs_id(1),
                "--item",
                "DOC=docs/06_quality/",
            ],
            [
                "attr",
                "--type",
                "root",
                "--by",
                "SA",
                "--obs",
                obs_id(1),
                "--root-cause",
                "tools/a-b",
            ],
            ["attr", "--type", "bogus", *base],
            [
                "attr",
                "--type",
                "link",
                "--by",
                "SA",
                "--obs",
                obs_id(1),
                "--from",
                obs_id(9),
                "--reopens",
                obs_id(2),
            ],
        ]
        for argv in usage:
            with self.subTest(argv=argv):
                self.usage_error(*self.M(repo, *argv), msg=str(argv))
        cases = [
            (["--item", "NONE=猜測是網路問題"], "ATTR-NONE-TEXT"),
            (["--item", "DEF=本檔時間欄"], "COORD-NONE"),
            (["--root-cause", "Tools/Lock"], "ROOT-CAUSE-FORMAT"),
            (["--root-cause", "tools"], "ROOT-CAUSE-FORMAT"),
            (["--root-cause", "tools/Lock_race"], "ROOT-CAUSE-FORMAT"),
            (["--obs", ox], "OBS-NOT-FOUND"),
        ]
        for over, code in cases:
            args = {
                "obs": obs_id(1),
                "item": "DOC=docs/06_quality/",
                "root_cause": "tools/lock-race",
            }
            for k, v in zip(over[::2], over[1::2]):
                args[k.lstrip("-").replace("-", "_")] = v
            rc, out, _ = self.M(repo, *attr_root_args(**args))
            self.rejected(rc, out, {code}, str(over))
            self.draft_ok(repo, out, str(over))
            if code == "OBS-NOT-FOUND":
                self.assertIn(ox, out)
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_105_2_1_attr_only_touches_event_ledger(self):
        repo = fx.p1_base()
        files0, status0 = fx.snap(repo)
        rc, out, err = self.M(
            repo,
            "attr",
            "--type",
            "root",
            "--by",
            "SA",
            "--obs",
            obs_id(1),
            "--item",
            "DOC=docs/05_development/SelfImproving_Operations_SOP.md:5",
            "--root-cause",
            "docs/stale-note",
        )
        self.assertEqual(rc, 0, err)
        e = fx.EV(repo)[0]
        self.assertEqual(
            set(e), {"seq", "t", "kind", "by", "id", "type", "obs", "items", "root_cause"}
        )
        self.assertFalse([k for k in e if re.search(r"conf|score|rating|prob", k)])
        files1, status1 = fx.snap(repo)
        self.assertEqual({k: v for k, v in files1.items() if k != EVL}, files0)
        self.assertEqual(set(status1.split("\n")) - set(status0.split("\n")), {f"?? {EVL}"})

    def test_AT_105_2_E_1_no_self_assessment(self):
        repo = fx.p1_base()
        snap0 = fx.snap(repo)
        for flag in (["--confidence", "0.9"], ["--score", "3"]):
            self.usage_error(
                *self.M(repo, *attr_root_args(item="DOC=docs/06_quality/"), *flag), msg=str(flag)
            )
        self.assertEqual(fx.snap(repo), snap0)
        fx.write_events(
            repo,
            [
                ev(
                    "attr",
                    "SA",
                    id=aid(1),
                    type="root",
                    obs=[obs_id(1)],
                    items=[["DOC", "docs/06_quality/"]],
                    root_cause="docs/stale-note",
                    confidence=0.9,
                )
            ],
        )
        res = self.check(repo)
        self.assertEqual(self.S(res, "events.structure"), "FAIL")
        self.assertEqual(self.F(res, "events.structure"), {("seq=1", "EVENT-KEY-UNKNOWN")})

    def test_AT_106_1_1_confirm_and_root_cause_changes(self):
        repo = fx.p1_base()
        self.cli_ok(repo, *attr_root_args(root_cause="tools/a-b"))
        self.cli_ok(repo, *attr_root_args(root_cause="tools/c-d"))
        rc, out, err = self.M(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, f"ok attr.confirm seq=3 att={aid(1)}\n")
        e = fx.EV(repo)[2]
        self.assertEqual(set(e), {"seq", "t", "kind", "by", "att"})
        self.assertEqual(e["by"], "QA")
        self.assertEqual(self.MJ(repo, "status")["root_cause_changes"], 1)
        self.assertEqual(self.S(self.check(repo), "events.transitions"), "PASS")

    def test_AT_106_1_E_1_confirm_rejections(self):
        repo = fx.p1_base()
        self.cli_ok(repo, *attr_root_args())
        self.cli_ok(repo, *attr_root_args(root_cause="docs/other-one"))
        snap0, ax = fx.snap(repo), aid(900 + 9)
        rc, out, _ = self.M(repo, "attr-confirm", "--att", aid(1), "--by", "SA")
        self.rejected(rc, out, {"CONFIRMER-IS-PROPOSER"})
        self.draft_ok(repo, out)
        rc, out, _ = self.M(repo, "attr-confirm", "--att", ax, "--by", "QA")
        self.rejected(rc, out, {"ATT-NOT-FOUND"})
        self.draft_ok(repo, out)
        self.assertEqual(fx.snap(repo), snap0)
        self.cli_ok(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
        for argv in (
            ["attr-confirm", "--att", aid(1), "--by", "QA"],
            ["attr-reject", "--att", aid(1), "--by", "QA", "--note", "另有看法"],
        ):
            rc, out, _ = self.M(repo, *argv)
            self.rejected(rc, out, {"ALREADY-SETTLED"}, str(argv))
        other = fx.p1_base()
        fx.write_events(
            other,
            [
                ev(
                    "attr",
                    "SA",
                    id=aid(1),
                    type="root",
                    obs=[obs_id(1)],
                    items=[["DOC", "docs/x/"]],
                    root_cause="docs/stale-note",
                ),
                ev("attr.confirm", "SA", att=aid(1)),
                ev("attr.confirm", "QA", att=aid(1)),
            ],
        )
        res = self.check(other)
        self.assertEqual(self.S(res, "events.transitions"), "FAIL")
        self.assertTrue(
            {(aid(1), "CONFIRMER-IS-PROPOSER"), (aid(1), "TRANSITION-ILLEGAL")}
            <= self.F(res, "events.transitions")
        )

    def test_AT_106_2_1_link_and_settle(self):
        repo = fx.p1_base()
        for frm, reopens in ((9, obs_id(2)), (10, obs_id(6)), (1, fx.def_id(1))):
            self.cli_ok(
                repo,
                "attr",
                "--type",
                "link",
                "--by",
                "SA",
                "--from",
                obs_id(frm),
                "--reopens",
                reopens,
            )
        u0 = self.MJ(repo, "status")["reopen_candidates"]["unsettled"]
        self.cli_ok(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
        self.cli_ok(repo, "attr-reject", "--att", aid(2), "--by", "QA", "--note", "證據不足")
        u1 = self.MJ(repo, "status")["reopen_candidates"]["unsettled"]
        self.assertEqual((u0, u1), (3, 1))
        events = fx.EV(repo)
        for e in events[:3]:
            self.assertEqual(set(e), {"seq", "t", "kind", "by", "id", "type", "from", "reopens"})
        self.assertEqual(set(events[4]), {"seq", "t", "kind", "by", "att", "note"})
        self.assertEqual(events[4]["note"], "證據不足")
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "events.structure"), self.S(res, "events.transitions")), ("PASS", "PASS")
        )

    def test_AT_106_2_E_1_link_rejections(self):
        repo = fx.p1_base()
        self.cli_ok(repo, *attr_root_args())
        snap0 = fx.snap(repo)
        ox, dx = obs_id(900 + 5), fx.def_id(900)
        link = ["attr", "--type", "link", "--by", "SA"]
        cases = [
            ([*link, "--from", obs_id(9), "--reopens", obs_id(1)], "REOPENS-NOT-CLOSED"),
            ([*link, "--from", obs_id(9), "--reopens", obs_id(4)], "REOPENS-NOT-CLOSED"),
            ([*link, "--from", obs_id(9), "--reopens", ox], "REOPENS-NOT-FOUND"),
            ([*link, "--from", obs_id(9), "--reopens", dx], "REOPENS-NOT-FOUND"),
            ([*link, "--from", ox, "--reopens", obs_id(2)], "OBS-NOT-FOUND"),
        ]
        for argv, code in cases:
            rc, out, _ = self.M(repo, *argv)
            self.rejected(rc, out, {code}, str(argv))
            self.draft_ok(repo, out, str(argv))
        base = ["attr-reject", "--att", aid(1), "--by", "QA"]
        for extra in ([], ["--note", ""], ["--note", "x" * 121], ["--note", "第一行\n第二行"]):
            self.usage_error(*self.M(repo, *base, *extra), msg=str(extra))
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_106_2_E_2_reopen_candidate_hint(self):
        closed = [
            obs_id(21),
            "2026-10-19 01:00",
            "情境",
            "症狀",
            "tools/lib/selfimproving/zz.py:7",
            "decision",
            "P3",
            "decided：掌舵者裁決",
            "面=流程;來源=人;回報者=掌舵者",
        ]
        defs = [
            (fx.def_id(20), "2026-09-01", "P2", "fixed@abc1234", "tools/lib/selfimproving/zz.py:99")
        ]

        def new_row(**kw):
            row = [
                obs_id(40),
                "2026-10-20 01:00",
                "情境",
                "新症狀",
                "tools/lib/selfimproving/zz.py:40",
                "bug",
                "P3",
                "open",
                "面=產品;來源=代理;回報者=SA",
            ]
            for k, v in kw.items():
                row[fx.COLS.index(k)] = v
            return row

        def build(*, extra=(), commit_new=False, **kw):
            repo = fx.make_p1_repo(fx.new_dir("rc"), extra_obs=[closed, *extra], defs=defs)
            fx.put(
                repo,
                LEDGER,
                fx.read(repo, LEDGER).rstrip("\n") + "\n" + fx.line(new_row(**kw)) + "\n",
            )
            if commit_new:
                fx.commit_all(repo, "new row")
            return repo

        res = self.check(build())
        self.assertEqual(self.S(res, "row.markers"), "PASS")
        hits = [
            f for f in res["_item"]["row.markers"]["findings"] if f["code"] == "REOPEN-CANDIDATE"
        ]
        self.assertEqual([f["subject"] for f in hits], [obs_id(40)])
        self.assertTrue(hits[0]["detail"].startswith("[warn]"))
        self.assertTrue(obs_id(21) in hits[0]["detail"] and fx.def_id(20) in hits[0]["detail"])
        self.assertEqual((res["_rc"], res["overall"]), (0, "PASS"))
        variants = {
            "a 已提交": build(commit_new=True),
            "b reopens": build(標記="面=產品;來源=代理;回報者=SA;reopens=" + obs_id(21)),
            "c 處置非 open": build(處置="deferred；再開症狀：同一症狀再現"),
            "d 路徑無交集": build(證據座標="tools/lib/selfimproving/other.py:3"),
        }
        for label, repo in variants.items():
            with self.subTest(label):
                self.assertNotIn(
                    "REOPEN-CANDIDATE", {c for _, c in self.F(self.check(repo), "row.markers")}
                )
        many = [[obs_id(21 + i), *closed[1:]] for i in range(7)]
        repo = fx.make_p1_repo(fx.new_dir("rc"), extra_obs=many)
        fx.put(repo, LEDGER, fx.read(repo, LEDGER).rstrip("\n") + "\n" + fx.line(new_row()) + "\n")
        detail = next(
            f["detail"]
            for f in self.check(repo)["_item"]["row.markers"]["findings"]
            if f["code"] == "REOPEN-CANDIDATE"
        )
        listed = re.findall(r"OBS-SI-\d{3}", detail)
        self.assertEqual(listed, [obs_id(21 + i) for i in range(5)])
        self.assertTrue(detail.endswith("…+2"), detail)
        nogit = fx.new_dir("nogit")
        shutil.copytree(build(), nogit, ignore=shutil.ignore_patterns(".git"))
        self.assertNotIn(
            "REOPEN-CANDIDATE", {c for _, c in self.F(self.check(nogit), "row.markers")}
        )


class TestEventLedger(SiTestCase):
    """受測：`tools/lib/selfimproving/events.py`／`evwrite.py`（事件帳本列形狀與追加）。"""

    def test_AT_141_1_1_event_line_shape(self):
        repo = fx.p1_base()
        sizes: list[tuple[int, int]] = []

        def step(*argv):
            before = ledger_bytes(repo) or b""
            out = self.cli_ok(repo, *argv)
            after = ledger_bytes(repo)
            sizes.append((before.count(b"\n"), after.count(b"\n")))
            return out

        step(*run_open_args())
        step("research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "離線驗證")
        step(*attr_root_args())
        step("attr", "--type", "link", "--by", "SA", "--from", obs_id(9), "--reopens", obs_id(2))
        step("attr-confirm", "--att", aid(1), "--by", "QA")
        step("attr-reject", "--att", aid(2), "--by", "QA", "--note", "證據不足")
        step("prop-new", "--run", rid(1), *fx.good_prop_args(repo, "P"))
        step("run-close", "--run", rid(1), "--by", "main")
        self.assertTrue(all(b - a == 1 for a, b in sizes), sizes)
        raw = ledger_bytes(repo)
        text = raw.decode("utf-8")
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw)
        self.assertTrue(text.endswith("\n"))
        lines = text.split("\n")[:-1]
        self.assertEqual(len(lines), 8)
        kinds = set(fx_kinds())
        for i, ln in enumerate(lines, start=1):
            obj = json.loads(ln)
            self.assertEqual(ln, fx.dumps_line(obj))
            self.assertEqual(list(obj)[:4], ["seq", "t", "kind", "by"])
            self.assertEqual(obj["seq"], i)
            self.assertRegex(obj["t"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
            self.assertIsNotNone(datetime.fromisoformat(obj["t"]).utcoffset())
            self.assertIn(obj["kind"], kinds)
            self.assertLessEqual(len(ln.encode("utf-8")), 2000)
        objs = [json.loads(ln) for ln in lines]
        order = {
            "run.open": ["run", "trigger", "coords", "head_sha"],
            "research.skip": ["run", "reason", "note"],
            "attr.confirm": ["att"],
            "attr.reject": ["att", "note"],
            "run.close": ["run", "outcomes"],
            "prop": [
                "id",
                "rev",
                "run",
                "base",
                "cls",
                "action",
                "route",
                "target",
                "touched_count",
                "touched_sha256",
                "patch_sha256",
                "body_sha256",
                "digest",
                "sources",
                "proposer",
                "reviewer",
            ],
        }
        for o in objs:
            if o["kind"] == "attr":
                want = (
                    ["id", "type", "obs", "items", "root_cause"]
                    if o["type"] == "root"
                    else ["id", "type", "from", "reopens"]
                )
            else:
                want = order[o["kind"]]
            self.assertEqual(list(o)[4:], want, o["kind"])
        self.assertEqual(
            [o["by"] for o in objs], ["main", "main", "SA", "SA", "QA", "QA", "SA", "main"]
        )
        self.assertIn("證據不足", lines[5])

    def test_AT_141_1_E_1_numbering_and_boundaries(self):
        events, seqs = fx.sc_seq()
        repo = fx.p1_base()
        fx.write_events(repo, events, seqs=seqs, commit=True)
        out = self.cli_ok(repo, *run_open_args())
        self.assertIn(f"seq=11 id={rid(8)}", out)
        out = self.cli_ok(repo, *attr_root_args())
        self.assertIn(f"seq=12 id={aid(13)}", out)
        out = self.cli_ok(repo, "prop-new", "--run", rid(7), *fx.good_prop_args(repo, "P"))
        self.assertIn(f"seq=13 id={pid(131)}", out)
        for label in ("empty", "absent"):
            r = fx.p1_base()
            if label == "empty":
                fx.put(r, EVL, "")
            out = self.cli_ok(r, *run_open_args())
            self.assertIn(f"seq=1 id={rid(1)}", out)
            self.cli_ok(
                r, "research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "離線"
            )
            out = self.cli_ok(r, "prop-new", "--run", rid(1), *fx.good_prop_args(r, "P"))
            self.assertIn(f"id={pid(124)}", out, label)
        calib = fx.p1_base()
        fx.set_params(calib, event_max_bytes=5000)
        rc, _, err = self.M(
            calib,
            "run-open",
            "--trigger",
            "a",
            "--by",
            "main",
            "--coord",
            "tools/a.py:1",
            "--coord",
            "tools/b.py:2",
        )
        self.assertEqual(rc, 0, err)
        length = len(fx.read(calib, EVL).rstrip("\n").encode("utf-8"))
        for limit, expect in ((length, 0), (length - 1, 1)):
            r = fx.p1_base()
            fx.set_params(r, event_max_bytes=limit)
            before = ledger_bytes(r)
            rc, out, err = self.M(
                r,
                "run-open",
                "--trigger",
                "a",
                "--by",
                "main",
                "--coord",
                "tools/a.py:1",
                "--coord",
                "tools/b.py:2",
            )
            self.assertEqual(rc, expect, out + err)
            if expect == 0:
                self.assertEqual(len(ledger_bytes(r).rstrip(b"\n")), length)
            else:
                self.rejected(rc, out, {"EVENT-BYTES-OVER"})
                self.assertEqual(ledger_bytes(r), before)
        good = fx.dumps_line(fx.compose([fx.run_open_ev(1)], "0" * 40)[0])
        for label, content in (("torn", good), ("garbled", good + "\nnot json\n")):
            r = fx.p1_base()
            fx.put(r, EVL, content)
            home0, before = fx.tree_files(self.home), ledger_bytes(r)
            rc, out, _ = self.M(r, *run_open_args())
            self.rejected(rc, out, {"LEDGER-TORN"}, label)
            self.assertEqual((ledger_bytes(r), fx.tree_files(self.home)), (before, home0))
            self.draft_ok(r, out, label)
        r = fx.p1_base()
        fx.set_params(r, event_max_bytes=KeyError)
        rc, out, err = self.M(r, *run_open_args())
        self.usage_error(rc, out, err)
        self.assertIn("event_max_bytes", err)
        self.assertIsNone(ledger_bytes(r))

    def test_AT_141_2_1_lock_serialises_writers(self):
        repo = fx.p1_base()
        ledger = repo / EVL
        si = self.home
        evwrite.ensure_home(si)
        lock = evwrite.lock_path_for(si, ledger)

        def build(state):
            return {
                "kind": "run.open",
                "by": "main",
                "run": rid(state.last_seq + 1),
                "trigger": "a",
                "coords": ["tools/a.py:1"],
                "head_sha": "0" * 40,
            }

        barrier = threading.Barrier(2, timeout=10)

        def fence():
            barrier.wait()  # 兩者都已讀完末行、配好號
            if threading.current_thread().name == "t1":
                time.sleep(0.3)  # Windows 的 O_APPEND 並非原子：讓兩次寫入錯開，只留下撞號這個變因

        ts = [
            threading.Thread(target=evwrite.append_event, args=(ledger, None, build), name=f"t{i}")
            for i in range(2)
        ]
        with mock.patch.object(evwrite, "PAUSE_HOOK", fence):
            for t in ts:
                t.start()
            for t in ts:
                t.join(20)
        seqs = [json.loads(ln)["seq"] for ln in fx.read(repo, EVL).split("\n") if ln]
        self.assertEqual(seqs, [1, 1], "無鎖對照組必須撞號")
        ledger.unlink()
        arrivals, release, seen = [], threading.Event(), []

        def hook():
            arrivals.append(threading.current_thread().name)
            if len(arrivals) == 1:
                release.wait(15)

        def build2(state):
            seen.append(state.last_seq)
            return build(state)

        ts = [
            threading.Thread(target=evwrite.append_event, args=(ledger, lock, build2), name=f"t{i}")
            for i in range(2)
        ]
        with mock.patch.object(evwrite, "PAUSE_HOOK", hook):
            for t in ts:
                t.start()
            time.sleep(1.0)
            self.assertEqual(len(arrivals), 1, "第二個執行緒不得在放行前到達鉤子")
            release.set()
            for t in ts:
                t.join(20)
        seqs = [json.loads(ln)["seq"] for ln in fx.read(repo, EVL).split("\n") if ln]
        self.assertEqual(seqs, [1, 2])
        self.assertEqual(seen, [0, 1])
        ledger.unlink()
        code = (
            "import sys\nsys.path.insert(0, sys.argv[1])\nimport selfimproving\n"
            "rcs = [selfimproving.main(['attr','--type','root','--by','SA','--obs',sys.argv[3],"
            "'--item','DOC=docs/06_quality/','--root-cause','docs/stale-note','--repo',"
            "sys.argv[2]]) for _ in range(10)]\nsys.exit(0 if all(r == 0 for r in rcs) else 1)\n"
        )
        env = {**fx.genv(), "AUTOSDD_SI_DIR": str(si)}
        t0 = time.monotonic()
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", code, str(TOOLS), str(repo), obs_id(1)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            for _ in range(8)
        ]
        rcs = [p.wait(120) for p in procs]
        self.assertEqual(rcs, [0] * 8, [p.stderr.read()[:200] for p in procs])
        self.assertLess(time.monotonic() - t0, 60)
        rows = [json.loads(ln) for ln in fx.read(repo, EVL).split("\n") if ln]
        self.assertEqual([r["seq"] for r in rows], list(range(1, 81)))
        self.assertEqual(sorted(r["id"] for r in rows), [aid(i) for i in range(1, 81)])
        self.assertTrue(all(len(ln.encode()) <= 2000 for ln in fx.read(repo, EVL).split("\n")))
        self.assertEqual(self.S(self.check(repo), "events.structure"), "PASS")

    def test_AT_141_2_E_1_lock_failure_modes(self):
        repo = fx.p1_base()
        si = self.home
        locks = evwrite.ensure_home(si)
        lock = evwrite.lock_path_for(si, repo / EVL)
        self.assertEqual(lock.parent, locks)
        lock.write_text("999999\n2026-01-01T00:00:00+00:00\n", encoding="utf-8")
        old = time.time() - 1000
        os.utime(lock, (old, old))
        self.cli_ok(repo, *run_open_args())
        self.assertEqual(len(fx.EV(repo)), 1)
        self.assertFalse(lock.exists())
        before = ledger_bytes(repo)
        with apply_lock.acquire(lock, 5, 300):
            with mock.patch.object(evwrite, "LOCK_TIMEOUT_SECONDS", 1):
                rc, out, _ = self.M(repo, *run_open_args())
        self.rejected(rc, out, {"LOCK-BUSY"})
        self.assertIn(str(os.getpid()), out)
        self.assertEqual(ledger_bytes(repo), before)
        self.draft_ok(repo, out)
        self.cli_ok(repo, *run_open_args())
        bad_root = fx.new_dir("notdir")
        bad_root.write_bytes(b"x")
        r2 = fx.p1_base()

        def tmp_listing():
            return sorted(
                n for n in os.listdir(tempfile.gettempdir()) if "selfimproving" in n or "locks" in n
            )

        names0 = tmp_listing()
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(bad_root / "si")}):
            rc, out, err = self.M(r2, *run_open_args())
            self.usage_error(rc, out, err)
            self.assertIn("HOME-UNWRITABLE", err)
            self.assertIsNone(ledger_bytes(r2))
            for argv in (
                ["check"],
                ["status", "--json"],
                ["scan"],
                ["export", "--json", "--kind", "status"],
            ):
                rc, out, err = self.M(r2, *argv)
                self.assertEqual(rc, 0, (argv, out, err))
        self.assertEqual(tmp_listing(), names0)


def non_note(findings):
    """去掉「引言回查未建」那則提示（SC-LEGAL 含 dec，故每次重放都會帶它）。"""
    return [f for f in findings if f["code"] != "QUOTE-VERIFIER-NOT-ESTABLISHED"]


def fx_kinds():
    from lib.selfimproving import events as si_events

    return si_events.KINDS


class TestCheckReplay(SiTestCase):
    """受測：`tools/lib/selfimproving/evcheck.py`（check 的事件帳本重放判定碼）。"""

    def test_AT_108_4_1_transitions_replay(self):
        def base_with(*extra):
            repo = fx.p1_base()
            fx.write_events(repo, fx.sc_legal())
            if extra:
                fx.append_events(repo, list(extra))
            return repo

        res = self.check(base_with())
        self.assertEqual(
            (self.S(res, "events.transitions"), self.S(res, "events.structure")), ("PASS", "PASS")
        )
        self.assertEqual(
            self.F(res, "events.transitions"), {("-", "QUOTE-VERIFIER-NOT-ESTABLISHED")}
        )
        illegal = {
            "a": ev("app.sandbox", prop=pid(129)),
            "b": fx.dec_ev(134, "approve"),
            "c1": fx.prop_ev(135, 1, rev=3, target=["docs/notes/n135.md"]),
            "c2": fx.prop_ev(129, 1, rev=2, target=["docs/notes/n129.md"]),
            "d": ev("app.promote", prop=pid(131)),
            "e1": fx.dec_ev(132, "promote"),
            "e2": fx.dec_ev(133, "promote"),
            "f": ev("mea.open", prop=pid(130)),
            "g": fx.prop_ev(124, 1, target=["docs/notes/n124.md"]),
        }
        subject = {
            "a": 129,
            "b": 134,
            "c1": 135,
            "c2": 129,
            "d": 131,
            "e1": 132,
            "e2": 133,
            "f": 130,
            "g": 124,
        }
        n0 = len(fx.EV(base_with()))
        for key, event in illegal.items():
            with self.subTest(key):
                res = self.check(base_with(event))
                self.assertEqual(self.S(res, "events.transitions"), "FAIL", key)
                fs = non_note(res["_item"]["events.transitions"]["findings"])
                self.assertEqual(
                    [(f["subject"], f["code"]) for f in fs],
                    [(pid(subject[key]), "TRANSITION-ILLEGAL")],
                    key,
                )
                self.assertIn(f"seq={n0 + 1}", fs[0]["detail"])
                self.assertIn(f"kind={event['kind']}", fs[0]["detail"])
                self.assertIn("state=", fs[0]["detail"])
        orphans = [
            fx.dec_ev(990, "approve"),
            ev("attr.confirm", "QA", att=aid(990)),
            ev("card", prop=pid(990)),
            ev("dec", "掌舵者", dkind="resume", run=rid(990)),
        ]
        for event in orphans:
            res = self.check(base_with(event))
            fs = non_note(res["_item"]["events.transitions"]["findings"])
            self.assertEqual(
                [(f["subject"], f["code"]) for f in fs],
                [(f"seq={n0 + 1}", "TRANSITION-ORPHAN")],
                event["kind"],
            )
        runs = {
            "未開": [ev("run.close", run=rid(77), no_event=True)],
            "已關": [
                ev("run.close", run=rid(1), no_event=True),
                ev("run.close", run=rid(1), no_event=True),
            ],
            "prop 的 run 不 open": [fx.prop_ev(190, 77, target=["docs/notes/n190.md"])],
        }
        for label, events in runs.items():
            res = self.check(base_with(*events))
            fs = non_note(res["_item"]["events.transitions"]["findings"])
            self.assertEqual([f["code"] for f in fs], ["TRANSITION-ILLEGAL"], label)
            self.assertIn(f"seq={n0 + len(events)}", fs[0]["detail"], label)

    def test_AT_108_4_E_1_append_only(self):
        evs = [fx.run_open_ev(1), fx.skip_ev(1), fx.run_open_ev(2), fx.skip_ev(2)]
        base = fx.p1_base()
        fx.write_events(base, evs)
        fx.commit_all(base, "C1")
        fx.append_events(base, [fx.run_open_ev(3)])
        c2 = fx.commit_all(base, "C2")

        def variant(mutate, commit=True):
            repo = fx.new_dir("m")
            shutil.copytree(base, repo)
            lines = fx.read(repo, EVL).split("\n")[:-1]
            new = mutate(lines)
            fx.put(repo, EVL, "".join(x + "\n" for x in new) if isinstance(new, list) else new)
            sha = fx.commit_all(repo, "C3") if commit else None
            return repo, sha

        res = self.check(base)
        self.assertEqual(self.S(res, "events.mutated"), "PASS")

        def change_by(lines):
            obj = json.loads(lines[1])
            obj["by"] = "other"
            return [lines[0], fx.dumps_line(obj), *lines[2:]]

        repo, sha = variant(change_by)
        res = self.check(repo)
        self.assertEqual(self.F(res, "events.mutated"), {("seq=2", "ROW-MUTATED")})
        d = res["_item"]["events.mutated"]["findings"][0]["detail"]
        self.assertTrue("cause=changed" in d and f"commit={sha[:7]}" in d and "掌舵者" in d, d)
        repo, _ = variant(lambda ls: ls[:-1])
        res = self.check(repo)
        self.assertEqual(self.F(res, "events.mutated"), {("seq=5", "ROW-MUTATED")})
        self.assertIn("cause=deleted", res["_item"]["events.mutated"]["findings"][0]["detail"])
        repo, _ = variant(lambda ls: ls[:2] + ls[3:])
        fs = self.check(repo)["_item"]["events.mutated"]["findings"]
        self.assertEqual(
            [(f["subject"], f["code"]) for f in fs],
            [("seq=3", "ROW-MUTATED"), ("seq=4", "ROW-MUTATED"), ("seq=5", "ROW-MUTATED")],
        )
        self.assertEqual(
            [("cause=changed" in f["detail"], "cause=deleted" in f["detail"]) for f in fs],
            [(True, False), (True, False), (False, True)],
        )
        repo, _ = variant(change_by, commit=False)
        res = self.check(repo)
        self.assertEqual(self.F(res, "events.mutated"), {("seq=2", "ROW-MUTATED")})
        self.assertIn("commit=WORKTREE", res["_item"]["events.mutated"]["findings"][0]["detail"])
        repo, _ = variant(
            lambda ls: [*ls, fx.dumps_line(fx.compose([fx.run_open_ev(4)], "0" * 40, [6])[0])],
            commit=False,
        )
        self.assertEqual(self.S(self.check(repo), "events.mutated"), "PASS")
        repo, _ = variant(lambda ls: ls, commit=False)
        self.assertEqual(self.S(self.check(repo), "events.mutated"), "PASS")
        repo, _ = variant(lambda ls: "\r\n".join(ls) + "\r\n")
        self.assertEqual(self.S(self.check(repo), "events.mutated"), "PASS")
        fresh = fx.p1_base()
        fx.write_events(fresh, evs)
        res = self.check(fresh)
        self.assertEqual(
            (self.S(res, "events.mutated"), res["_item"]["events.mutated"]["detail"]),
            ("PASS", "no-history"),
        )
        nogit = fx.new_dir("nogit")
        shutil.copytree(base, nogit, ignore=shutil.ignore_patterns(".git"))
        res = self.check(nogit)
        item = res["_item"]["events.mutated"]
        self.assertEqual(
            (item["status"], item["blocking"], item["findings"][0]["code"]),
            ("NE", True, "GIT-UNAVAILABLE"),
        )
        self.assertTrue(c2)

    def test_AT_108_4_E_2_structure_floor_and_dec_note(self):
        def with_extra(extra_text: str, events=None, prm=None):
            repo = fx.p1_base()
            fx.write_events(repo, events or [fx.run_open_ev(1), fx.skip_ev(1)])
            if prm:
                fx.set_params(repo, **prm)
            append_raw(repo, extra_text)
            return self.check(repo)

        def good(n, **over):
            obj = fx.compose([fx.run_open_ev(n)], "0" * 40, [n])[0]
            obj.update(over)
            return obj

        def jl(obj):
            return fx.dumps_line(obj) + "\n"

        for label, text in (("空白行", "\n"), ("[1]", "[1]\n"), ("非 JSON", "oops\n")):
            res = with_extra(text)
            self.assertEqual(self.S(res, "events.structure"), "FAIL", label)
            self.assertEqual(self.F(res, "events.structure"), {("L3", "EVENT-PARSE")}, label)
        obj = good(3)
        del obj["by"]
        res = with_extra(jl(obj))
        self.assertEqual(self.F(res, "events.structure"), {("seq=3", "EVENT-KEY-MISSING")})
        obj = good(3)
        del obj["head_sha"]
        res = with_extra(jl(obj))
        self.assertEqual(self.F(res, "events.structure"), {("seq=3", "EVENT-KEY-MISSING")})
        res = with_extra(jl(good(3, kind="bogus.kind")))
        self.assertEqual(self.F(res, "events.structure"), {("seq=3", "EVENT-KIND")})
        type_cases = {
            "seq 布林": (good(3, seq=True), "L3"),
            "seq 0": (good(3, seq=0), "seq=0"),
            "t naive": (good(3, t="2026-10-20T10:00:00"), "seq=3"),
            "by 空白": (good(3, by="a b"), "seq=3"),
            "by 33": (good(3, by="x" * 33), "seq=3"),
        }
        close_both = fx.compose(
            [fx.ev("run.close", run=rid(1), outcomes={}, no_event=True)], "0" * 40, [3]
        )[0]
        close_none = fx.compose([fx.ev("run.close", run=rid(1))], "0" * 40, [3])[0]
        skip_nb = fx.compose(
            [fx.ev("research.skip", run=rid(1), reason="quota-band", note="x")], "0" * 40, [3]
        )[0]
        skip_free = fx.compose(
            [fx.ev("research.skip", run=rid(1), reason="quota-band", note="x", band="Free")],
            "0" * 40,
            [3],
        )[0]
        prop_m = fx.compose([fx.prop_ev(124, 1, cls="M")], "0" * 40, [3])[0]
        prop_p = fx.compose([fx.prop_ev(124, 1, cls="P", preimage={"a": fx.H(1)})], "0" * 40, [3])[
            0
        ]
        type_cases.update(
            {
                "close 兩者": (close_both, "seq=3"),
                "close 皆無": (close_none, "seq=3"),
                "skip 缺 band": (skip_nb, "seq=3"),
                "skip Free": (skip_free, "seq=3"),
                "M 缺 preimage": (prop_m, "seq=3"),
                "P 有 preimage": (prop_p, "seq=3"),
            }
        )
        for label, (o, subj) in type_cases.items():
            res = with_extra(jl(o))
            fs = res["_item"]["events.structure"]["findings"]
            self.assertEqual([(f["subject"], f["code"]) for f in fs], [(subj, "EVENT-TYPE")], label)
        obj = good(3)
        obj["extra"] = 1
        res = with_extra(jl(obj))
        self.assertEqual(self.F(res, "events.structure"), {("seq=3", "EVENT-KEY-UNKNOWN")})
        res = self.check(self._seq_repo([1, 2, 2, 1]))
        self.assertEqual(
            self.F(res, "events.structure"), {("seq=2", "EVENT-SEQ"), ("seq=1", "EVENT-SEQ")}
        )
        self.assertEqual(self.S(self.check(self._seq_repo([1, 3, 7])), "events.structure"), "PASS")
        huge = good(3)
        huge["coords"] = ["x" * 2100]
        res = with_extra(jl(huge))
        self.assertEqual(self.F(res, "events.structure"), {("seq=3", "EVENT-BYTES-OVER")})
        repo = fx.p1_base()
        raw = "".join(jl(o) for o in fx.compose([fx.run_open_ev(1), fx.skip_ev(1)], "0" * 40))
        fx.putb(repo, EVL, b"\xef\xbb\xbf" + raw.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(self.S(self.check(repo), "events.structure"), "PASS")
        for n, expect in ((2, "NE"), (3, "PASS")):
            events = [fx.run_open_ev(i) for i in range(1, n + 1)]
            res = self.check(self._events_repo(events, min_events=3))
            self.assertEqual(self.S(res, "events.vacuity"), expect, n)
            if expect == "NE":
                item = res["_item"]["events.vacuity"]
                self.assertEqual(
                    (item["blocking"], item["findings"][0]["code"]), (True, "EVENTS-BELOW-FLOOR")
                )
        empty = fx.p1_base()
        fx.set_params(empty, min_events=3)
        fx.put(empty, EVL, "")
        res = self.check(empty)
        self.assertEqual(
            (self.S(res, "events.vacuity"), res["_item"]["events.vacuity"]["blocking"]),
            ("NE", True),
        )
        res = self.check(self._events_repo([ev("card"), ev("mea.report")]))
        self.assertEqual(self.S(res, "events.structure"), "PASS")
        repo = fx.p1_base()
        run = self.open_run(repo)
        self.cli_ok(repo, "prop-new", "--run", run, *fx.good_prop_args(repo, "P"))
        self.cli_ok(
            repo, "prop-new", "--run", run, *fx.good_prop_args(repo, "D", sources=[obs_id(3)])
        )
        fx.append_events(repo, [fx.dec_ev(124, "approve"), fx.dec_ev(125, "approve")])
        res = self.check(repo)
        item = res["_item"]["events.transitions"]
        self.assertEqual(item["status"], "PASS")  # nonblocking 提示不改狀態（AT-108-4-E-2）
        self.assertEqual(
            [(f["subject"], f["code"]) for f in item["findings"]],
            [("-", "QUOTE-VERIFIER-NOT-ESTABLISHED")],
        )
        self.assertIn("2", item["findings"][0]["detail"])
        self.assertIn("引言回查屬 P2", item["findings"][0]["detail"])
        self.assertEqual((res["overall"], res["_rc"]), ("PASS", 0))

    def _seq_repo(self, seqs):
        repo = fx.p1_base()
        fx.write_events(repo, [fx.run_open_ev(i) for i in range(1, len(seqs) + 1)], seqs=seqs)
        return repo

    def _events_repo(self, events, **prm):
        repo = fx.p1_base()
        fx.set_params(repo, **prm)
        fx.write_events(repo, events)
        return repo


class TestCheckAdditions(SiTestCase):
    def test_AT_142_1_1_p1_items_on_p0_baseline_and_after_a_round(self):
        repo = fx.p1_base()
        res = self.check(repo)
        self.assertEqual((res["_rc"], res["overall"], res["rows"]), (0, "PASS", 10))
        ids = [i["id"] for i in res["items"]]
        self.assertEqual((ids[:21], ids[21:]), (P0_ITEMS21, P1_ITEMS7))
        for item in res["items"][21:]:
            self.assertEqual((item["status"], item["blocking"]), ("NE", False))
            self.assertEqual([f["code"] for f in item["findings"]], ["CARRIER-NOT-ESTABLISHED"])
        for item in res["items"][:21]:
            if item["id"] == "ref.carrier_families":
                self.assertEqual((item["status"], item["blocking"]), ("NE", False))
            else:
                self.assertEqual((item["status"], item["findings"]), ("PASS", []), item["id"])
        self.assertEqual(res["fingerprint_parts"]["check_rules_rev"], 2)
        keys = list(res["items"][0])
        self.assertTrue(all(list(i) == keys for i in res["items"]))
        rc, text, _ = self.M(repo, "check")
        lines = text.split("\n")
        self.assertEqual(lines[0], "si-check rows=10 items=28")
        self.assertRegex(
            [x for x in lines if x.strip()][-1], r"^overall=PASS rc=0 fingerprint=sha256:"
        )
        self.assertNotIn("obs-draft:", text)
        for item in res["items"]:
            tag = (
                "NE" + (" blocking" if item["blocking"] else " nonblocking")
                if item["status"] == "NE"
                else item["status"]
            )
            self.assertIn(f"{tag.split(' ')[0]} {item['id']}", text)
        run = self.open_run(repo)
        self.cli_ok(repo, *attr_root_args())
        self.cli_ok(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
        self.cli_ok(repo, "prop-new", "--run", run, *fx.good_prop_args(repo, "P"))
        self.cli_ok(repo, "run-close", "--run", run, "--by", "main")
        fx.commit_all(repo, "round")
        res = self.check(repo)
        self.assertEqual((res["_rc"], res["overall"]), (0, "PASS"))
        for item in P1_ITEMS7[:6]:
            self.assertEqual(
                (self.S(res, item), res["_item"][item]["findings"]), ("PASS", []), item
            )
        item = res["_item"]["research.sources"]
        self.assertEqual((item["status"], item["blocking"]), ("NE", False))
        self.assertEqual(self.S(res, "ref.carrier_families"), "NE")

    def test_AT_142_1_E_1_prop_files_and_sources_table(self):
        base = fx.p1_base()
        run = self.open_run(base)
        self.cli_ok(base, "prop-new", "--run", run, *fx.good_prop_args(base, "P"))
        fx.commit_all(base, "prop")
        sub = f"{pid(124)} r1"
        patch_rel, md_rel = (
            f"{fx.PROPS_REL}/{pid(124)}/r1.patch",
            f"{fx.PROPS_REL}/{pid(124)}/r1.md",
        )

        def mutated(fn):
            repo = fx.new_dir("pf")
            shutil.copytree(base, repo)
            fn(repo)
            return self.check(repo)

        def edit_event(repo, key, fn):
            lines = fx.read(repo, EVL).split("\n")[:-1]
            out = []
            for ln in lines:
                obj = json.loads(ln)
                if obj["kind"] == "prop":
                    obj[key] = fn(obj[key])
                out.append(fx.dumps_line(obj) + "\n")
            fx.put(repo, EVL, "".join(out))

        cases = {
            "a": (lambda r: (r / patch_rel).unlink(), "PROP-FILE-MISSING"),
            "b": (lambda r: (r / md_rel).unlink(), "PROP-FILE-MISSING"),
            "c": (
                lambda r: fx.putb(r, patch_rel, (r / patch_rel).read_bytes() + b"+x\n"),
                "PROP-PATCH-SHA-MISMATCH",
            ),
            "d": (
                lambda r: fx.put(r, md_rel, fx.read(r, md_rel).replace("卡面症狀一句", "改字了")),
                "PROP-BODY-SHA-MISMATCH",
            ),
            "f": (
                lambda r: fx.putb(
                    r, patch_rel, (r / patch_rel).read_bytes().replace(b"\n", b"\r\n")
                ),
                "PROP-PATCH-SHA-MISMATCH",
            ),
            "g": (
                lambda r: edit_event(r, "touched_sha256", lambda v: fx.H(5)),
                "PROP-TOUCHED-MISMATCH",
            ),
            "h": (
                lambda r: edit_event(r, "touched_count", lambda v: v + 1),
                "PROP-TOUCHED-MISMATCH",
            ),
        }
        for key, (fn, code) in cases.items():
            with self.subTest(key):
                res = mutated(fn)
                self.assertEqual(self.F(res, "events.prop_files"), {(sub, code)}, key)
        res = mutated(
            lambda r: fx.putb(r, md_rel, (r / md_rel).read_bytes().replace(b"\n", b"\r\n"))
        )
        self.assertEqual(
            (self.S(res, "events.prop_files"), self.F(res, "events.prop_files")), ("PASS", set())
        )
        table = {
            "schema_rev": 1,
            "sources": [
                {
                    "id": "a-src",
                    "url": "https://example.com/x.md",
                    "kind": "docs",
                    "extract": "讀",
                    "added_by": "T1",
                }
            ],
        }

        def with_table(text=None, raw=None):
            repo = fx.new_dir("st")
            shutil.copytree(base, repo)
            payload = (
                raw if raw is not None else (text or json.dumps(table, indent=2) + "\n").encode()
            )
            fx.putb(repo, fx.SRC_REL, payload)
            fx.commit_all(repo, "src")
            return self.check(repo)

        self.assertEqual(self.S(with_table(), "research.sources"), "PASS")
        res = with_table(json.dumps({**table, "schema_rev": 2}, indent=2) + "\n")
        self.assertEqual({c for _, c in self.F(res, "research.sources")}, {"SRC-SCHEMA"})
        raw = b"\xef\xbb\xbf" + (json.dumps(table, indent=2) + "\n").encode()
        self.assertIn(
            "SRC-FILE-FORMAT", {c for _, c in self.F(with_table(raw=raw), "research.sources")}
        )

    def test_AT_142_1_E_2_researcher_rows(self):
        entries = [
            {
                "id": "cc-note",
                "url": "https://example.com/a.md",
                "kind": "docs",
                "extract": "讀",
                "added_by": "T1",
            },
            {
                "id": "old-src",
                "url": "https://example.com/b.md",
                "kind": "docs",
                "extract": "讀",
                "added_by": "T1",
                "retired": True,
            },
        ]
        text = json.dumps({"schema_rev": 1, "sources": entries}, indent=2) + "\n"
        base = fx.make_p1_repo(fx.new_dir("src"), sources=text)

        def row(marks, delete_table=False):
            repo = fx.new_dir("rw")
            shutil.copytree(base, repo)
            line = [
                obs_id(11),
                "2026-10-20 01:00",
                "情境",
                "症狀",
                "tools/lib/selfimproving/fresh.py:1",
                "bug",
                "P3",
                "open",
                marks,
            ]
            fx.put(repo, LEDGER, fx.read(repo, LEDGER).rstrip("\n") + "\n" + fx.line(line) + "\n")
            if delete_table:
                (repo / fx.SRC_REL).unlink()
            return self.check(repo)

        m = "面=流程;來源=代理;"
        r11 = obs_id(11)
        for label, marks in (
            ("a", m + "回報者=研究者;外部衍生=是;src=cc-note"),
            ("e", m + "回報者=SA;src=old-src"),
        ):
            res = row(marks)
            for item in ("row.provenance", "row.markers"):
                self.assertEqual({s for s, _ in self.F(res, item)} & {r11}, set(), label)
        self.assertEqual(
            self.F(row(m + "回報者=研究者;src=cc-note"), "row.provenance"),
            {(r11, "RESEARCHER-NOT-EXTERNAL")},
        )
        self.assertEqual(
            self.F(row(m + "回報者=研究者;外部衍生=是"), "row.provenance"),
            {(r11, "RESEARCHER-NO-SRC")},
        )
        self.assertEqual(
            self.F(row(m + "回報者=SA;src=zz-unknown"), "row.markers"), {(r11, "SRC-UNKNOWN")}
        )
        res = row(m + "回報者=SA;src=Bad_Id")
        self.assertIn((r11, "MARK-VALUE"), self.F(res, "row.markers"))
        self.assertNotIn((r11, "SRC-UNKNOWN"), self.F(res, "row.markers"))
        self.assertEqual(
            self.F(row(m + "回報者=SA;foo=1"), "row.markers"), {(r11, "MARK-UNKNOWN-KEY")}
        )
        res = row(m + "回報者=SA;src=cc-note", delete_table=True)
        item = res["_item"]["row.markers"]
        self.assertEqual((item["status"], item["blocking"]), ("NE", True))
        self.assertIn("SOURCE-UNAVAILABLE", {f["code"] for f in item["findings"]})

    def test_AT_142_2_1_p0_items_unchanged(self):
        repo = fx.p1_base()
        res = self.check(repo)
        self.assertEqual((res["_rc"], res["overall"]), (0, "PASS"))
        self.assertEqual([i["id"] for i in res["items"][:21]], P0_ITEMS21)
        for item in res["items"][:21]:
            if item["id"] == "ref.carrier_families":
                self.assertEqual((item["status"], item["blocking"]), ("NE", False))
                self.assertEqual(
                    [(f["code"], f["detail"]) for f in item["findings"]],
                    [("CARRIER-NOT-ESTABLISHED", "families=PROP-SI count=1")],
                )
            else:
                self.assertEqual((item["status"], item["findings"]), ("PASS", []), item["id"])
        self.assertEqual(res["_item"]["history.migration"]["detail"], "claim=none")
        crlf = fx.new_dir("crlf")
        shutil.copytree(repo, crlf)
        fx.putb(crlf, LEDGER, fx.read(crlf, LEDGER).replace("\n", "\r\n").encode("utf-8"))
        res2 = self.check(crlf)
        self.assertEqual((res2["_rc"], res2["overall"]), (0, "PASS"))
        self.assertEqual(
            [i["status"] for i in res2["items"][:21]], [i["status"] for i in res["items"][:21]]
        )

    def test_AT_142_2_E_1_p0_negatives_unchanged(self):
        base = fx.p1_base()

        def variant(fn):
            repo = fx.new_dir("p0")
            shutil.copytree(base, repo)
            fn(repo)
            return self.check(repo)

        def set_cell(repo, n, col, value):
            lines = []
            for ln in fx.read(repo, LEDGER).split("\n"):
                if ln.startswith(f"| {obs_id(n)} |"):
                    cells = ln[2:-2].split(" | ")
                    cells[fx.COLS.index(col)] = value
                    ln = fx.line(cells)
                lines.append(ln)
            fx.put(repo, LEDGER, "\n".join(lines))

        res = variant(
            lambda r: fx.put(
                r, LEDGER, fx.read(r, LEDGER).replace("<!-- si-ledger: tz=+08:00 -->\n", "")
            )
        )
        self.assertEqual(
            {s for s, c in self.F(res, "ledger.time_tz") if c == "TIME-NO-TZ"},
            {obs_id(n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 10)},
        )
        self.assertEqual(
            self.F(variant(lambda r: set_cell(r, 3, "分類", "")), "row.required"),
            {(obs_id(3), "FIELD-EMPTY")},
        )
        self.assertIn(
            (obs_id(4), "ENUM-SEVERITY"),
            self.F(variant(lambda r: set_cell(r, 4, "嚴重度", "P0")), "row.enums"),
        )
        self.assertEqual(
            self.F(variant(lambda r: set_cell(r, 4, "證據座標", "本檔時間欄")), "row.coordinates"),
            {(obs_id(4), "COORD-NONE")},
        )
        res = variant(lambda r: set_cell(r, 5, "症狀", "改字了"))
        self.assertEqual(self.F(res, "history.row_mutated"), {(obs_id(5), "ROW-MUTATED")})
        detail = res["_item"]["history.row_mutated"]["findings"][0]["detail"]
        self.assertTrue("commit=WORKTREE" in detail and "掌舵者" in detail)
        res = variant(lambda r: fx.set_params(r, row_max_bytes=KeyError))
        self.assertIn(("row_max_bytes", "PARAM-MISSING"), self.F(res, "params.keys"))
        item = res["_item"]["row.bytes"]
        self.assertEqual(
            (item["status"], item["blocking"], item["findings"][0]["code"]),
            ("NE", True, "SOURCE-UNAVAILABLE"),
        )
        nogit = fx.new_dir("nogit")
        shutil.copytree(base, nogit, ignore=shutil.ignore_patterns(".git"))
        res = self.check(nogit)
        self.assertEqual(res["_rc"], 2)
        first, rest = res["items"][:21], res["items"][21:]
        self.assertEqual(sum(1 for i in first if i["status"] == "PASS"), 17)
        self.assertEqual(sum(1 for i in first if i["status"] == "NE" and i["blocking"]), 4)
        self.assertTrue(all(i["status"] == "NE" and not i["blocking"] for i in rest))
        rc, out, err = self.run_main(["check", "--repo", str(base), "--ledger", "no/such.md"])
        self.usage_error(rc, out, err)
        src = (TOOLS / "tests" / "test_selfimproving_check.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

        def strings(name):
            return {
                c.value
                for c in ast.walk(fns[name])
                if isinstance(c, ast.Constant) and isinstance(c.value, str)
            }

        self.assertTrue(any("items=28" in s for s in strings("test_AT_001_1_1_baseline_is_green")))
        self.assertFalse(any("items=21" in s for s in strings("test_AT_001_1_1_baseline_is_green")))
        s3 = strings("test_AT_003_1_1_no_resident_mechanism")
        self.assertTrue({"decide", "promote"} <= s3 and "prop-new" not in s3)
        self.assertIn("decide", strings("test_AT_030_1_E_1_usage_errors"))
        keys = {
            k.value
            for k in ast.walk(fns["params_dict"])
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        self.assertTrue(
            {
                "research_fetch_max",
                "research_bytes_max",
                "research_timeout_seconds",
                "min_events",
                "export_limit_max",
            }
            <= keys
        )
        names = {n.id for n in ast.walk(fns["test_AT_030_2_1_purity"]) if isinstance(n, ast.Name)}
        self.assertIn("CAPABILITY", names)


class TestInterface(SiTestCase):
    VERBS = [
        "check",
        "status",
        "scan",
        "card",
        "export",
        "run-open",
        "run-close",
        "attr",
        "attr-confirm",
        "attr-reject",
        "prop-new",
        "prop-revise",
        "research",
    ]

    def test_AT_140_1_1_thirteen_verbs(self):
        repo = fx.p1_base()
        rc, out, _ = self.run_main(["--help"])
        self.assertEqual(rc, 0)
        self.assertTrue(all(v in out for v in self.VERBS))
        for verb in self.VERBS:
            rc, out, _ = self.run_main([verb, "--help"])
            self.assertEqual(rc, 0, verb)
        self.assertIn("--patch-file", self.run_main(["prop-new", "--help"])[1])
        self.assertIn("--kind", self.run_main(["export", "--help"])[1])
        helptext = self.run_main(["research", "--help"])[1]
        self.assertTrue("--fetch" in helptext and "--skip" in helptext)
        snap0 = fx.snap(repo)
        run = self.open_run(repo)
        self.cli_ok(repo, *attr_root_args())
        self.cli_ok(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
        self.cli_ok(
            repo,
            "attr",
            "--type",
            "link",
            "--by",
            "SA",
            "--from",
            obs_id(9),
            "--reopens",
            obs_id(2),
        )
        self.cli_ok(repo, "attr-reject", "--att", aid(2), "--by", "QA", "--note", "證據不足")
        self.cli_ok(repo, "prop-new", "--run", run, *fx.good_prop_args(repo, "P"))
        fx.append_events(repo, [fx.dec_ev(124, "return")])
        self.cli_ok(
            repo, "prop-revise", "--run", run, "--prop", pid(124), *fx.revise_args(repo, "P")
        )
        mid = fx.snap(repo)
        for argv in (
            ["status"],
            ["scan"],
            ["card", pid(124)],
            ["export", "--json", "--kind", "status"],
        ):
            self.cli_ok(repo, *argv)
        self.assertEqual(fx.snap(repo), mid)
        self.cli_ok(repo, "check")
        self.cli_ok(repo, "run-close", "--run", run, "--by", "main")
        self.assertNotEqual(snap0, mid)
        plain = fx.new_dir("plain")
        plain.write_bytes(b"x")
        missing = fx.new_dir("missing")
        flags = {
            "check": ["check"],
            "status": ["status"],
            "scan": ["scan"],
            "card": ["card", pid(124)],
            "export": ["export", "--json", "--kind", "status"],
            "run-open": run_open_args(),
            "run-close": ["run-close", "--run", rid(1), "--by", "main"],
            "attr": attr_root_args(),
            "attr-confirm": ["attr-confirm", "--att", aid(1), "--by", "QA"],
            "attr-reject": ["attr-reject", "--att", aid(2), "--by", "QA", "--note", "x"],
            "prop-new": ["prop-new", "--run", rid(1), *fx.good_prop_args(repo, "P")],
            "prop-revise": [
                "prop-revise",
                "--run",
                rid(1),
                "--prop",
                pid(124),
                *fx.revise_args(repo, "P"),
            ],
            "research": [
                "research",
                "--skip",
                "--run",
                rid(1),
                "--reason",
                "offline",
                "--note",
                "x",
            ],
        }
        for verb, argv in flags.items():
            for bad in (plain, missing):
                with self.subTest(verb=verb, repo=bad.name):
                    self.usage_error(*self.run_main([*argv, "--repo", str(bad)]), msg=verb)

    def test_AT_140_1_E_1_unimplemented_verbs_and_reject_grammar(self):
        repo = fx.p1_base()
        snap0 = fx.snap(repo)
        today = datetime.now().strftime("%Y-%m-%d")
        calls = [
            [v]
            for v in (
                "decide",
                "heldout-freeze",
                "sandbox",
                "verify",
                "promote",
                "rollback",
                "capacity",
                "frobnicate",
            )
        ]
        calls += [
            ["card", pid(124), "--issue"],
            ["status", "--bogus"],
            ["scan", "--since", today],
            ["scan", "--count", "5"],
        ]
        for argv in calls:
            with self.subTest(argv=argv):
                self.usage_error(*self.M(repo, *argv), msg=str(argv))
        self.assertEqual(fx.snap(repo), snap0)
        rx = rid(900 + 3)
        rc, out, _ = self.M(repo, "run-close", "--run", rx, "--by", "main")
        lines = out.split("\n")
        self.assertEqual(rc, 1)
        self.assertEqual(lines[0], "reject run-close RUN-NOT-OPEN")
        self.assertRegex(lines[1], r"^  RUN-NOT-OPEN \S")
        self.assertEqual(lines[2], "obs-draft:")
        self.assertTrue(lines[3].startswith("| OBS") and lines[4:] == [""])
        rc2, out2, _ = self.M(repo, "run-close", "--run", rx, "--by", "main", "--json")
        obj = json.loads(out2)
        self.assertEqual(list(obj), ["ok", "rc", "verb", "codes", "obs_draft"])
        self.assertEqual((obj["ok"], obj["rc"], obj["verb"]), (False, 1, "run-close"))
        self.assertEqual([c["code"] for c in obj["codes"]], ["RUN-NOT-OPEN"])
        cells = [c.strip() for c in lines[3].strip("|").split("|")]
        self.assertEqual(len(cells), 9)
        self.assertEqual(cells[0], obs_id(11))
        self.assertEqual(cells[2], "si run-close（自動草稿）")
        self.assertTrue(
            cells[3].startswith("si run-close 拒收（rc=1）：") and "RUN-NOT-OPEN" in cells[3]
        )
        self.assertEqual(cells[5:9], ["bug", "P3", "open", "面=流程;來源=工具;回報者=si-run-close"])
        self.assertTrue(
            "`python tools/selfimproving.py run-close`" in cells[4] and "rc=1" in cells[4]
        )
        self.draft_ok(repo, out)
        self.draft_ok(repo, "obs-draft:\n" + obj["obs_draft"] + "\n")
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_145_1_1_real_protocol_files(self):
        raw = fx.REAL_PARAMS.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw)
        self.assertTrue(raw.endswith(b"\n"))
        obj = json.loads(raw.decode("utf-8"))
        self.assertEqual(list(obj), sorted(obj, key=lambda k: k.encode("utf-8")))
        for key in (
            "research_fetch_max",
            "research_bytes_max",
            "research_timeout_seconds",
            "min_events",
            "export_limit_max",
        ):
            self.assertTrue(
                isinstance(obj[key], int) and not isinstance(obj[key], bool) and obj[key] >= 1
            )
        res = self.check(fx.ROOT)
        for item in ("params.keys", "params.globs", "params.coupling", "research.sources"):
            self.assertEqual(self.S(res, item), "PASS", item)
        from lib.selfimproving import sources as si_sources

        src = (fx.ROOT / fx.SRC_REL).read_bytes()
        self.assertEqual(si_sources.validate_table(src, si_sources.DEFAULT_POLICY), [])
        entries = json.loads(src.decode("utf-8"))["sources"]
        ids = [e["id"] for e in entries]
        self.assertEqual(ids, sorted(ids, key=lambda k: k.encode("utf-8")))
        self.assertTrue(all(e["added_by"] for e in entries))
        self.assertLessEqual(
            sum(1 for e in entries if not e.get("retired")), obj["research_fetch_max"]
        )

    def test_AT_145_1_E_1_new_param_keys(self):
        repo = fx.p1_base()
        keys = (
            "research_fetch_max",
            "research_bytes_max",
            "research_timeout_seconds",
            "min_events",
            "export_limit_max",
        )
        for key in keys:
            for value, code in (
                (KeyError, "PARAM-MISSING"),
                ("x", "PARAM-TYPE"),
                (1.5, "PARAM-TYPE"),
                (True, "PARAM-TYPE"),
                (0, "PARAM-RANGE"),
            ):
                fx.set_params(repo, **{key: value})
                res = self.check(repo)
                self.assertEqual(self.S(res, "params.keys"), "FAIL", (key, value))
                self.assertEqual(self.F(res, "params.keys"), {(key, code)}, (key, value))
            fx.set_params(repo, **{key: 5})
        e = fx.p1_base()
        fx.set_params(e, export_limit_max=KeyError)
        rc, out, err = self.M(e, "export", "--json", "--kind", "status")
        self.usage_error(rc, out, err)
        self.assertIn("export_limit_max", err)
        r = fx.p1_base()
        self.open_run(r)
        fx.commit_all(r, "run")
        fx.set_params(r, research_fetch_max=KeyError)
        before = ledger_bytes(r)
        import socket

        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("連線")):
            rc, out, err = self.M(r, "research", "--fetch", "--run", rid(1))
        self.usage_error(rc, out, err)
        self.assertIn("research_fetch_max", err)
        self.assertEqual(ledger_bytes(r), before)
        v = fx.p1_base()
        fx.write_events(v, [fx.run_open_ev(1)])
        fx.set_params(v, min_events=0)
        res = self.check(v)
        item = res["_item"]["events.vacuity"]
        self.assertEqual(
            (item["status"], item["blocking"], item["findings"][0]["code"]),
            ("NE", True, "SOURCE-UNAVAILABLE"),
        )
        self.assertEqual(self.S(res, "params.keys"), "FAIL")


def real_sop() -> str:
    return fx.REAL_SOP.read_bytes().decode("utf-8").replace("\r\n", "\n")


def real_prd() -> str:
    return fx.REAL_PRD.read_bytes().decode("utf-8").replace("\r\n", "\n")


def tmpl_fragments() -> list[str]:
    start = [i for i, (k, f) in enumerate(fx.FRAGMENTS) if f == "AutoClaude"][0]
    return [f for _, f in fx.FRAGMENTS[start : start + 13]]


def mutated_copies(text: str):
    """（標籤, 變異副本）：每個片段在其所屬節（模組體檢片段在範本子節）首次出現處刪去。"""
    tmpl = set(tmpl_fragments())
    for key, frag in fx.FRAGMENTS:
        sub = "模組體檢" if key == "歸因者" and frag in tmpl else None
        yield f"{key}節缺 {frag}", fx.remove_in_section(text, key, frag, sub)


class TestSopArticles(SiTestCase):
    def test_AT_145_2_1_sop_is_final(self):
        text, prd = real_sop(), real_prd()
        self.assertEqual(fx.sop_problems(text, prd), [])
        for key in ("歸因者", "提案者", "審查者", "凍結者"):
            sec = fx.sop_section(text, key)
            self.assertIn("P1 定稿", sec)
            rest = "".join(ln for ln in sec.split("\n")[1:] if "P1 定稿" not in ln)
            self.assertTrue(rest.strip(), key)
        self.assertTrue(fx.sop_section(text, "研究者"))
        entry = fx.prd_entry_fragments(prd)
        self.assertGreaterEqual(len(entry), 10)
        tmpl = fx.sop_section(text, "歸因者")
        self.assertTrue(all(f in tmpl for f in entry))

    def test_AT_145_2_E_1_criteria_are_not_vacuous(self):
        text, prd = real_sop(), real_prd()
        self.assertEqual(fx.sop_problems(text, prd), [])
        for label, copy in mutated_copies(text):
            with self.subTest(label):
                probs = fx.sop_problems(copy, prd)
                self.assertTrue(probs, label)
                self.assertIn(label.split("節缺 ")[1], " ".join(probs), label)
        groups = list(fx.SAME_LINE_GROUPS) + [("全文", f) for f in fx.RESEARCH_EVENT_LINES]
        for key, frags in fx.SAME_LINE_GROUPS:
            copy = fx.split_last_to_next_line(text, key, frags)
            self.assertTrue(fx.sop_problems(copy, prd), f"{key} {frags}")
        for frags in fx.RESEARCH_EVENT_LINES:
            copy = fx.split_last_to_next_line(text, "研究者", frags)
            self.assertTrue(fx.sop_problems(copy, prd), f"研究事件 {frags}")
        self.assertTrue(groups)
        renamed = [
            text.replace("## 研究者", "## 探索員", 1),
            *[
                text.replace("P1 定稿", "", 1)
                if False
                else fx.remove_in_section(text, k, "P1 定稿")
                for k in ("歸因者", "提案者", "審查者", "凍結者")
            ],
            text.replace("### 模組體檢任務書範本", "### 任務書範本", 1),
        ]
        for copy in renamed:
            self.assertTrue(fx.sop_problems(copy, prd))

    def _group_checks(self, key, frags, other):
        text = real_sop()
        sec = fx.sop_section(text, key)
        self.assertTrue(fx.line_has_all(sec, *frags))
        copies = []
        s, e = fx.same_line(text, key, frags)
        for frag in frags:
            ln = text[s:e]
            copies.append(text[:s] + ln.replace(frag, "") + text[e:])
        copies.append(fx.split_last_to_next_line(text, key, frags))
        copies.append(fx.move_line(text, key, frags, other))
        for i, copy in enumerate(copies):
            self.assertEqual(fx.line_has_all(fx.sop_section(copy, key), *frags), [], i)

    def test_AT_107_2_1_theory_hole_clause(self):
        sec = fx.sop_section(real_sop(), "歸因者")
        self.assertTrue(fx.line_has_all(sec, "理論洞", "P4", "暴露證據", "不立案"))

    def test_AT_107_2_E_1_theory_hole_criteria(self):
        self._group_checks("歸因者", ("理論洞", "P4", "暴露證據", "不立案"), "審查者")

    def test_AT_111_2_1_evaluator_change_clause(self):
        sec = fx.sop_section(real_sop(), "歸因者")
        self.assertTrue(
            fx.line_has_all(
                sec,
                "evaluator-change",
                "evaluator_command",
                "expected_output_regex",
                "OBS",
                "不得轉送沙盒",
            )
        )

    def test_AT_111_2_E_1_evaluator_change_criteria(self):
        self._group_checks(
            "歸因者",
            (
                "evaluator-change",
                "evaluator_command",
                "expected_output_regex",
                "OBS",
                "不得轉送沙盒",
            ),
            "凍結者",
        )


WEIRD_STATUS_KEYS = [
    "events_detected", "unavailable", "open_runs", "pending_props", "suspended", "cooldowns",
    "skip_reasons", "capacity", "root_cause_changes", "reopen_candidates", "pending_windows",
    "friction_reconcile", "no_event",
]  # fmt: skip


def weird_events() -> dict[str, dict]:
    """SC-WEIRD：欄位值為陣列的四型事件（`tools/lib/selfimproving/events.py` 的讀取側防禦）。"""
    attr = {"id": aid(1), "items": [["DOC", "docs/x"]], "root_cause": "a/b"}
    return {
        "W1": fx.skip_ev(1, reason=["a"]),
        "W2": ev("attr", "SA", type=["root"], obs=[obs_id(1)], **attr),
        "W3": ev("attr", "SA", type="root", obs=[[obs_id(1)]], **attr),
        "W4": ev("attr.confirm", "QA", att=["a"]),
    }


class TestWeirdEvents(SiTestCase):
    """受測：`tools/lib/selfimproving/events.py`／`fold.py`／`evcheck.py`（型別怪異事件不崩潰）。"""

    def weird_repo(self, label: str) -> Path:
        repo = fx.p1_base()
        fx.write_events(repo, [fx.run_open_ev(1), weird_events()[label]])
        return repo

    def test_AT_108_4_E_3_weird_events_are_event_type_only(self):
        for label in weird_events():
            with self.subTest(label):
                repo = self.weird_repo(label)
                res = self.check(repo)
                self.assertEqual(res["_rc"], 1, label)
                self.assertEqual(len(res["items"]), 28)
                self.assertTrue(all("status" in i for i in res["items"]))
                self.assertEqual(self.S(res, "events.structure"), "FAIL")
                self.assertEqual(self.F(res, "events.structure"), {("seq=2", "EVENT-TYPE")})
                bad = {c for _, c in self.F(res, "events.transitions")}
                self.assertFalse(bad & {"TRANSITION-ILLEGAL", "TRANSITION-ORPHAN"}, label)
                self.assertIn("status", res["_item"]["events.research"])
                self.assertIn("status", res["_item"]["events.vacuity"])

    def test_AT_140_1_E_2_verbs_survive_weird_events(self):
        for label in weird_events():
            repo = self.weird_repo(label)
            lines0 = ledger_bytes(repo).split(b"\n")[:2]
            att = aid(1)
            for argv in (["status"], ["status", "--json"]):
                rc, out, _ = self.M(repo, *argv)
                self.assertEqual(rc, 0, (label, argv, out))
                if "--json" in argv:
                    self.assertEqual(list(json.loads(out)), WEIRD_STATUS_KEYS)
            for kind in ("events", "runs", "proposals", "status"):
                rc, out, _ = self.M(repo, "export", "--json", "--kind", kind)
                self.assertEqual(rc, 0, (label, kind, out))
                items = json.loads(out)["items"]
                if kind == "events":
                    self.assertEqual(items[1], json.loads(lines0[1]), label)
            copy = fx.new_dir("wc")
            shutil.copytree(repo, copy)
            rc, out, _ = self.M(copy, "run-close", "--run", rid(1), "--by", "main")
            self.assertEqual(
                (rc, out), (0, "ok run.close seq=3 run=RUN-SI-001 no_event=true\n"), label
            )
            self.assertEqual(ledger_bytes(copy).split(b"\n")[:2], lines0)
            copy = fx.new_dir("wc")
            shutil.copytree(repo, copy)
            rc, out, _ = self.M(copy, "attr-confirm", "--att", att, "--by", "QA")
            self.assertEqual((rc, fx.codes_of(out)), (1, {"ATT-NOT-FOUND"}), (label, out))
            copy = fx.new_dir("wc")
            shutil.copytree(repo, copy)
            rc, out, _ = self.M(
                copy, "research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "x"
            )
            self.assertEqual(rc, 0, (label, out))
            self.assertEqual(ledger_bytes(copy).split(b"\n")[:2], lines0)


class TestValueDomains(SiTestCase):
    """受測：`tools/lib/selfimproving/events.py`／`evcheck.py`（值域邊界與引言回查提示）。"""

    def structure(self, events, **prm):
        repo = fx.p1_base()
        fx.set_params(repo, **prm)
        fx.write_events(repo, [fx.run_open_ev(1), *events])
        res = self.check(repo)
        return self.S(res, "events.structure"), self.F(res, "events.structure")

    def expect(self, events, want, msg):
        status, found = self.structure(events)
        self.assertEqual(found, want, msg)
        self.assertEqual(status, "FAIL" if want else "PASS", msg)

    def test_AT_108_4_E_4_value_domains(self):
        bad = {("seq=2", "EVENT-TYPE")}
        for n, want in ((120, set()), (121, bad)):
            note = "字" * n
            self.expect([fx.skip_ev(1, note=note)], want, f"skip note {n}")
            self.expect([ev("attr.reject", "QA", att=aid(1), note=note)], want, f"reject {n}")
        when = fx.T0().isoformat(timespec="seconds")
        for code, want in ((199, bad), (200, set()), (299, set()), (300, bad)):
            src = {"id": "s-live", "sha256": fx.H(9), "bytes": 3, "changed": True,
                   "http_status": code}  # fmt: skip
            scan = ev("research.scan", "researcher", run=rid(1), sources=[src],
                      sources_sha256=fx.H(5), fetched_at=when)  # fmt: skip
            self.expect([scan], want, f"http_status {code}")
        for by, want in (("main", set()), ("researcher", bad), ("SA", bad)):
            self.expect([fx.ev("research.skip", by, run=rid(1), reason="offline", note="x")],
                        want, f"skip by {by}")  # fmt: skip
        sids = (
            (fx.UUID, set()),
            (fx.UUID.replace("-", ""), bad),
            ("{" + fx.UUID + "}", bad),
            ("urn:uuid:" + fx.UUID, bad),
        )
        for sid, want in sids:
            skip = fx.skip_ev(1, reason="helmsman", sid=sid, line=3)
            self.expect([skip], want, f"sid {sid}")
        repo = fx.p1_base()
        fx.write_events(repo, [fx.run_open_ev(1)])
        size = len(ledger_bytes(repo).rstrip(b"\n"))
        for limit, want in ((size, set()), (size - 1, {("seq=1", "EVENT-BYTES-OVER")})):
            fx.set_params(repo, event_max_bytes=limit)
            res = self.check(repo)
            self.assertEqual(self.F(res, "events.structure"), want, limit)
            self.assertEqual(self.S(res, "events.structure"), "FAIL" if want else "PASS")

    def test_AT_108_4_E_5_quote_verifier_warn_boundary(self):
        base = [fx.run_open_ev(1), fx.skip_ev(1)]
        prop = fx.prop_ev(124, 1)
        cases = {
            "a": [*base, prop, fx.dec_ev(124, "approve")],
            "b": [*base, prop],
            "c": [fx.run_open_ev(1), fx.skip_ev(1, reason="helmsman", sid=fx.UUID, line=3)],
            "d": [fx.run_open_ev(1), fx.skip_ev(1)],
        }
        out = {}
        for key, events in cases.items():
            repo = fx.p1_base()
            fx.write_events(repo, events)
            out[key] = self.check(repo)
        quote = ("-", "QUOTE-VERIFIER-NOT-ESTABLISHED")
        item = out["a"]["_item"]["events.transitions"]
        self.assertEqual(item["status"], "PASS")
        self.assertEqual({(f["subject"], f["code"]) for f in item["findings"]}, {quote})
        (finding,) = item["findings"]
        self.assertEqual(finding["level"], "warn")
        self.assertTrue(finding["detail"].startswith("[warn]"))
        self.assertIn("1", finding["detail"])
        self.assertIn("引言回查屬 P2", finding["detail"])
        self.assertEqual(self.F(out["b"], "events.transitions"), set())
        item = out["c"]["_item"]["events.research"]
        self.assertEqual(item["status"], "PASS")
        self.assertEqual({(f["subject"], f["code"]) for f in item["findings"]}, {quote})
        self.assertEqual(item["findings"][0]["level"], "warn")
        self.assertEqual(self.F(out["d"], "events.research"), set())
        self.assertFalse(out["a"]["_item"]["events.transitions"]["blocking"])
        self.assertFalse(item["blocking"])
        for key in ("c", "d"):
            self.assertEqual((out[key]["overall"], out[key]["_rc"]), ("PASS", 0), key)


class TestProposalNumberingAndLock(SiTestCase):
    """受測：`tools/lib/selfimproving/writeverbs.py`／`evwrite.py`（配號在鎖內、鎖檔命名）。"""

    def test_AT_141_1_E_2_prop_number_is_read_inside_the_lock(self):
        px = "PROP-SI-" + "140"
        got = {}
        for label in ("control", "late"):
            repo, run = self.fresh_run_repo()
            real = evwrite.append_event

            def wrapper(*a, _repo=repo, **kw):
                with (_repo / LEDGER).open("ab") as fh:
                    fh.write(f"| 補記 | {px} |\n".encode())
                return real(*a, **kw)

            if label == "late":
                with mock.patch.object(evwrite, "append_event", wrapper):
                    rc, out, err = self.prop(repo, run, "P")
            else:
                rc, out, err = self.prop(repo, run, "P")
            self.assertEqual(rc, 0, out + err)
            got[label] = re.search(r"id=(PROP-SI-\d+)", out).group(1)
            self.assertEqual(fx.EV(repo)[-1]["id"], got[label])
        self.assertEqual(got, {"control": pid(124), "late": pid(141)})
        self.assertTrue((repo / fx.PROPS_REL / pid(141)).is_dir())

    def test_AT_141_2_E_2_lock_file_is_named_after_the_ledger_realpath(self):
        wants = []
        for _ in range(2):
            repo = fx.p1_base()
            seen = []
            locks = self.home / "locks"
            hook = lambda: seen.append(sorted(p.name for p in locks.iterdir()))  # noqa: E731
            with mock.patch.object(evwrite, "PAUSE_HOOK", hook):
                self.cli_ok(repo, *run_open_args())
            key = hashlib.sha256(os.path.realpath(repo / EVL).encode("utf-8")).hexdigest()[:16]
            want = key + ".lock"
            self.assertEqual(seen, [[want]])
            self.assertRegex(want, r"^[0-9a-f]{16}\.lock$")
            self.assertEqual([p.name for p in locks.glob("*.lock")], [])
            wants.append(want)
        self.assertNotEqual(*wants)

    def test_AT_141_2_E_3_home_exists_but_is_not_writable(self):
        repo = fx.p1_base()
        for sub in ("locks", "research"):
            (self.home / sub).mkdir()
        probe = self.home / "locks" / f".probe-{os.getpid()}"
        probe.mkdir()
        snap0, home0 = fx.snap(repo), fx.tree_files(self.home)
        rc, out, err = self.M(repo, *run_open_args())
        self.usage_error(rc, out, err)
        self.assertIn("HOME-UNWRITABLE", err)
        self.assertIsNone(ledger_bytes(repo))
        self.assertEqual((fx.snap(repo), fx.tree_files(self.home)), (snap0, home0))
        for argv in (["check"], ["status", "--json"], ["scan"], ["export", "--json", "--kind",
                                                                 "status"]):
            rc, out, err = self.M(repo, *argv)
            self.assertEqual(rc, 0, (argv, out, err))
        probe.rmdir()
        self.cli_ok(repo, *run_open_args())
        self.assertEqual(len(fx.EV(repo)), 1)


class TestDraftCodeCap(SiTestCase):
    """受測：`tools/lib/selfimproving/writeverbs.py`（OBS 草稿列症狀至多 5 個碼）。"""

    def test_AT_140_1_E_3_draft_symptom_lists_at_most_five_codes(self):
        repo, _ = self.fresh_run_repo()
        rx, sx = rid(77), obs_id(777)
        want6 = [
            "RUN-NOT-OPEN", "RESEARCH-MISSING", "SOURCE-UNRESOLVED", "NO-INTERNAL-SOURCE",
            "REVIEWER-IS-PROPOSER", "HANDOFF-CHANNEL-UNEXPECTED",
        ]  # fmt: skip
        cases = (
            (dict(reviewer="SA", handoff="T1"), 6),
            (dict(reviewer="SA"), 5),
            (dict(), 4),
        )
        for over, count in cases:
            args = fx.good_prop_args(repo, "P", sources=[sx], proposer="SA", **over)
            rc, out, _ = self.M(repo, "prop-new", "--run", rx, *args)
            self.assertEqual(rc, 1, out)
            head = out.split("obs-draft:")[0]
            names = list(dict.fromkeys(re.findall(r"(?m)^  ([A-Z][A-Z0-9-]+) ", head)))
            self.assertEqual(len(names), count, out)
            if count == 6:
                self.assertEqual(fx.codes_of(out), set(want6))
            self.draft_ok(repo, out, f"{count} 個碼")
            (row,) = [r for r in out.split("\n") if r.startswith("| OBS")]
            symptom = [c.strip() for c in row.strip().strip("|").split("|")][3]
            tail = "…等 6 項" if count == 6 else ""
            self.assertEqual(
                symptom, "si prop-new 拒收（rc=1）：" + "、".join(names[:5]) + tail, count
            )
            self.assertEqual("…等" in symptom, count == 6)


class TestSopCriteriaConstants(SiTestCase):
    """受測：夾具常數 `SAME_LINE_GROUPS`／`RESEARCH_EVENT_LINES`（R65 判準常數的獨立釘選）。"""

    def test_AT_145_2_E_2_same_line_constants_are_pinned(self):
        want_groups = {
            ("歸因者", frozenset({"理論洞", "P4", "暴露證據", "不立案"})),
            ("歸因者", frozenset({"evaluator-change", "evaluator_command",
                                   "expected_output_regex", "OBS", "不得轉送沙盒"})),
            ("提案者", frozenset({"抽象化", "結果標籤", "原始軌跡全文"})),
            ("提案者", frozenset({"不得再派", "提案者", "審查者"})),
        }  # fmt: skip
        want_lines = {
            frozenset({"研究事件", "research.scan", "research.skip", "prop-new", "拒收"}),
            frozenset({"quota-band", "offline", "helmsman"}),
        }

        def groups(cs):
            return {(k, frozenset(f)) for k, f in cs}

        def lines(cs):
            return {frozenset(f) for f in cs}

        self.assertEqual(len(fx.SAME_LINE_GROUPS), 4)
        self.assertEqual(len(fx.RESEARCH_EVENT_LINES), 2)
        self.assertEqual(groups(fx.SAME_LINE_GROUPS), want_groups)
        self.assertEqual(lines(fx.RESEARCH_EVENT_LINES), want_lines)
        gs, ls = list(fx.SAME_LINE_GROUPS), list(fx.RESEARCH_EVENT_LINES)
        mutants = []
        for i in range(len(gs)):
            mutants.append(gs[:i] + gs[i + 1:])
            key, frags = gs[i]
            for j in range(len(frags)):
                dropped = (key, tuple(f for k, f in enumerate(frags) if k != j))
                mutants.append(gs[:i] + [dropped] + gs[i + 1:])
                changed = (key, tuple(f + "x" if k == j else f for k, f in enumerate(frags)))
                mutants.append(gs[:i] + [changed] + gs[i + 1:])
            other = "審查者" if key != "審查者" else "提案者"
            mutants.append(gs[:i] + [(other, frags)] + gs[i + 1:])
        for mutant in mutants:
            self.assertNotEqual(groups(mutant), want_groups)
        for i in range(len(ls)):
            self.assertNotEqual(lines(ls[:i] + ls[i + 1:]), want_lines)
            for j in range(len(ls[i])):
                dropped = tuple(f for k, f in enumerate(ls[i]) if k != j)
                changed = tuple(f + "x" if k == j else f for k, f in enumerate(ls[i]))
                for variant in (dropped, changed):
                    self.assertNotEqual(lines(ls[:i] + [variant] + ls[i + 1:]), want_lines)


CORRUPT_T = "2026-10-20T08:00:00+08:00"
_TY, _MI, _OR = "EVENT-TYPE", "EVENT-KEY-MISSING", "TRANSITION-ORPHAN"


def raw_line(seq: int, kind: str, by: str, body: dict) -> str:
    """手寫損壞事件：原始 JSON 行、不經 `compose`（不補任何預設鍵）。"""
    obj = {"seq": seq, "t": CORRUPT_T, "kind": kind, "by": by, **body}
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"


def corrupt_cases(p: str) -> dict[str, tuple]:
    """TCS §5.3 `CORRUPT-CASES`：案 → (kind, by, 鍵, structure 碼集, transitions 碼集)。"""
    dec = {"prop": p, "dkind": "approve"}
    return {
        "K01": ("dec", "x", {**dec, "flags": ["a", ["b"]]}, {_TY}, set()),
        "K02": ("dec", "x", {**dec, "flags": ["a", 1]}, {_TY}, set()),
        "K03": ("dec", "x", {**dec, "flags": [{"k": 1}]}, {_TY}, set()),
        "K04": ("dec", "x", {"prop": p, "dkind": ["x"]}, {_TY}, set()),
        "K05": ("dec", "x", {"prop": ["x"], "dkind": "approve"}, {_TY}, set()),
        "K06": ("mea.amend", "x", {"prop": p, "window": [1], "to": [2]}, {_TY}, set()),
        "K07": ("app.verify", "x", {"prop": p, "verdict": ["PASS"]}, {_TY}, set()),
        "K08": ("prop", "x", {"id": p, "rev": 1}, {_MI}, set()),
        "K09": ("prop", "x", {"rev": 1, "run": rid(1)}, {_MI}, set()),
        "K10": ("prop", "x", {"id": ["a"], "rev": 1, "run": rid(1)}, {_MI, _TY}, set()),
        "K11": ("research.scan", "researcher", {"run": rid(1), "sources": 5}, {_MI, _TY}, set()),
        "K12": ("research.skip", "main", {"run": rid(1), "reason": ["a"], "note": "x"},
                {_TY}, set()),
        "K13": ("attr", "x", {"id": aid(99), "type": ["root"]}, {_TY}, set()),
        "K14": ("attr", "x", {"id": aid(1), "type": "root", "obs": [["x"]],
                              "items": [["DOC", "a.md"]], "root_cause": "a/b"}, {_TY}, set()),
        "K15": ("attr.confirm", "x", {"att": ["x"]}, {_TY}, set()),
        "K16": ("run.open", "x", {"run": ["x"], "trigger": "a", "coords": 5}, {_MI, _TY}, set()),
        "K17": ("run.close", "x", {"run": rid(1), "outcomes": [1]}, {_TY}, set()),
        "K18": ("card", "x", {}, set(), {_OR}),
    }


def consumed_keys(p: str) -> dict[str, tuple]:
    """TCS §5.3 `CONSUMED-KEYS`：列 → (kind, 鍵)；V 列判 EVENT-TYPE、L 列為合法對照。"""
    bad = ["x"]
    v = {
        "V01": ("card", {"prop": bad}), "V02": ("heldout.freeze", {"prop": bad}),
        "V03": ("app.sandbox", {"prop": bad}),
        "V04": ("app.verify", {"prop": bad, "verdict": "PASS"}),
        "V05": ("app.promote", {"prop": bad}), "V06": ("app.rollback", {"prop": bad}),
        "V07": ("mea.open", {"prop": bad}),
        "V08": ("mea.close", {"prop": bad, "result": "clean"}),
        "V09": ("mea.amend", {"prop": bad, "window": 1, "to": "clean"}),
        "V10": ("mea.report", {"prop": bad}),
        "V11": ("dec", {"prop": bad, "dkind": "approve"}),
        "V12": ("dec", {"prop": p, "dkind": bad}),
        "V13": ("dec", {"dkind": "resume", "run": bad}),
        "V14": ("app.verify", {"prop": p, "verdict": ["PASS"]}),
        "V15": ("mea.close", {"prop": p, "result": ["clean"]}),
        "V16": ("mea.amend", {"prop": p, "window": [1], "to": "clean"}),
        "V17": ("mea.amend", {"prop": p, "window": 1, "to": ["clean"]}),
        "V18": ("mea.amend", {"prop": p, "window": True, "to": "clean"}),
        "V19": ("mea.amend", {"prop": p, "window": 0, "to": "clean"}),
    }  # fmt: skip
    legal = {
        "L01": ("dec", {"dkind": "resume", "run": rid(1)}),
        "L02": ("mea.amend", {"prop": p, "window": 1, "to": "clean"}),
        "L03": ("card", {"prop": p}),
    }
    return {**v, **legal}


class CorruptLedgerTestCase(SiTestCase):
    """損壞事件測試的共用基底：SC-CORRUPT 基底（每個測試檔快取一份樣板）與案例複本。"""

    def corrupt_base(self) -> Path:
        key = "corrupt_base"
        if key not in fx._CACHE:
            repo = fx.p1_base()
            self.cli_ok(repo, *run_open_args())
            self.cli_ok(
                repo, "research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "x"
            )
            self.cli_ok(repo, *attr_root_args())
            self.cli_ok(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
            self.cli_ok(repo, "prop-new", "--run", rid(1), *fx.good_prop_args(repo, "P"))
            fx.commit_all(repo, "corrupt-base")
            fx._CACHE[key] = repo
        return fx._CACHE[key]

    def case_repo(self, event: tuple | None = None) -> Path:
        dest = fx.new_dir("cc")
        shutil.copytree(self.corrupt_base(), dest)
        if event is not None:
            kind, by, body = event[:3]
            append_raw(dest, raw_line(6, kind, by, body))
        return dest


class TestDecFlagsAndConsumedKeys(CorruptLedgerTestCase):
    """受測：`tools/lib/selfimproving/events.py`（P2 起種類被消費的鍵逐鍵判型別，R37）。"""

    def check_case(self, repo: Path):
        res = self.check(repo)
        self.assertEqual(len(res["items"]), 28)
        self.assertTrue(all("status" in i for i in res["items"]))
        return res

    def test_AT_108_4_E_6_dec_flags_must_be_a_string_array(self):
        p = base_prop(self.corrupt_base())
        forms = {
            "F1": ["a", ["b"]], "F2": ["a", 1], "F3": [{"k": 1}], "F4": "unverified_ack",
            "F5": ["unverified_ack"], "F6": [],
        }  # fmt: skip
        for label, flags in forms.items():
            with self.subTest(label):
                repo = self.case_repo(("dec", "x", {"prop": p, "dkind": "approve", "flags": flags}))
                res = self.check_case(repo)
                if label in ("F5", "F6"):
                    self.assertEqual((res["_rc"], self.S(res, "events.structure")), (0, "PASS"))
                    self.assertEqual(
                        self.F(res, "events.transitions"),
                        {("-", "QUOTE-VERIFIER-NOT-ESTABLISHED")},
                    )
                    continue
                self.assertEqual(res["_rc"], 1)
                self.assertEqual(self.S(res, "events.structure"), "FAIL")
                self.assertEqual(self.F(res, "events.structure"), {("seq=6", "EVENT-TYPE")})
                self.assertEqual(self.S(res, "events.transitions"), "PASS")
                self.assertEqual(self.F(res, "events.transitions"), set())
                for argv in verb16(self.corrupt_base()):
                    work = fx.new_dir("cw")
                    shutil.copytree(repo, work)
                    rc, out, err = self.M(work, *argv)
                    self.assertIn(rc, (0, 1, 2, 3), (label, argv, out, err))
                    self.assertNotIn("Traceback", err)

    def test_AT_108_4_E_7_every_consumed_key_is_type_checked(self):
        for label, (kind, body) in consumed_keys(base_prop(self.corrupt_base())).items():
            with self.subTest(label):
                res = self.check_case(self.case_repo((kind, "x", body)))
                if label.startswith("V"):
                    self.assertEqual(res["_rc"], 1)
                    self.assertEqual(self.S(res, "events.structure"), "FAIL")
                    self.assertEqual(self.F(res, "events.structure"), {("seq=6", "EVENT-TYPE")})
                    self.assertEqual(self.S(res, "events.transitions"), "PASS")
                    self.assertEqual(self.F(res, "events.transitions"), set())
                    continue
                self.assertEqual((res["_rc"], self.S(res, "events.structure")), (0, "PASS"))
                want = {("-", "QUOTE-VERIFIER-NOT-ESTABLISHED")} if label == "L01" else set()
                self.assertEqual(self.F(res, "events.transitions"), want)


def base_prop(base: Path) -> str:
    """SC-CORRUPT 基底的 PROP ID（執行期取自帳本末行，不寫死號碼）。"""
    return fx.EV(base)[-1]["id"]


def verb16(base: Path) -> list[list[str]]:
    """TCS §5.2 `VERB16`：餵 `tools/lib/selfimproving/` 的十六個呼叫（不含 `--repo`）。"""
    prop_new = fx.good_prop_args(
        base, "D", target=["docs/notes/other.md"],
        patch=fx.patch_mod("docs/notes/other.md", {3: "改過三"}), sources=[obs_id(3)],
    )  # fmt: skip
    return [
        ["check", "--json"], ["status"], ["scan"], ["card", base_prop(base)],
        ["export", "--json", "--kind", "events"], ["export", "--json", "--kind", "proposals"],
        ["export", "--json", "--kind", "runs"], ["export", "--json", "--kind", "status"],
        run_open_args(), ["run-close", "--run", rid(1), "--by", "main"],
        attr_root_args(obs=obs_id(2)),
        ["attr-confirm", "--att", aid(1), "--by", "zz"],
        ["attr-reject", "--att", aid(1), "--by", "zz", "--note", "x"],
        ["research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "x"],
        ["prop-new", "--run", rid(1), *prop_new],
        ["prop-revise", "--run", rid(1), "--prop", base_prop(base), *fx.revise_args(base, "P")],
    ]  # fmt: skip


VERB16_K00_RC = [0] * 11 + [1, 1, 1, 0, 1]  # (12)～(14) 與 (16) 對照案即為 rc 1
_WRITING = (8, 9, 10, 14)  # run-open、run-close、attr、prop-new（0 起算）


class TestCorruptEventMatrix(CorruptLedgerTestCase):
    """受測：`tools/lib/selfimproving/evwrite.py`／`fold.py`／`card.py`／`props.py`（R37、R32）。"""

    def test_AT_140_1_E_4_corrupt_events_times_every_verb(self):
        base = self.corrupt_base()
        argvs = verb16(base)
        protos = base / si_events.PROPOSALS_REL
        keep = {d.name for d in protos.iterdir()} if protos.is_dir() else set()
        p = base_prop(base)
        cases = {"K00": None, **corrupt_cases(p)}
        k00_out: dict[int, str] = {}
        for label, case in cases.items():
            with self.subTest(label):
                repo = self.case_repo(case)
                orig = (repo / EVL).read_bytes()
                for i, argv in enumerate(argvs):
                    (repo / EVL).write_bytes(orig)
                    if protos.is_dir():
                        for d in (repo / si_events.PROPOSALS_REL).iterdir():
                            if d.name not in keep:
                                shutil.rmtree(d)
                    rc, out, err = self.M(repo, *argv)
                    where = (label, i + 1, argv[0], rc, out, err)
                    self.assertIn(rc, (0, 1, 2, 3), where)
                    self.assertNotIn("Traceback", err, where)
                    if i == 0:
                        self.assert_check_matches(label, case, rc, out)
                        continue
                    self.assertEqual(rc, VERB16_K00_RC[i], where)
                    if i in (1, 2, 3):
                        if label == "K00":
                            k00_out[i] = out
                        self.assertEqual(out, k00_out[i], where)
                    if i == 4:
                        lines = [json.loads(x) for x in orig.decode("utf-8").splitlines()]
                        self.assertEqual(json.loads(out)["items"], lines, where)
                    if i in _WRITING and rc == 0:
                        after = (repo / EVL).read_bytes()
                        self.assertTrue(after.startswith(orig), where)
                        self.assertEqual(
                            json.loads(after[len(orig):].splitlines()[-1])["seq"],
                            6 if label == "K00" else 7, where)  # R32 (a)：損壞事件即使被忽略也佔號
                (repo / EVL).write_bytes(orig)
                for extra in (["status", "--json"], ["card", p, "--json"]):
                    rc, out, err = self.M(repo, *extra)
                    self.assertEqual(rc, 0, (label, extra, out, err))
                    self.assertNotIn("Traceback", err)
                    key = ("x", extra[0], len(extra))
                    if label == "K00":
                        k00_out[key] = out
                    self.assertEqual(out, k00_out[key], (label, extra))

    def assert_check_matches(self, label, case, rc, out):
        res = json.loads(out)
        items = {i["id"]: i for i in res["items"]}
        got_s = {(f["subject"], f["code"]) for f in items["events.structure"]["findings"]}
        got_t = {(f["subject"], f["code"]) for f in items["events.transitions"]["findings"]}
        want_s = {("seq=6", c) for c in case[3]} if case else set()
        want_t = {("seq=6", c) for c in case[4]} if case else set()
        self.assertEqual((rc, got_s, got_t), (1 if case else 0, want_s, want_t), (label, out))
        for key in ("events.mutated", "events.vacuity", "events.prop_files", "events.research"):
            self.assertEqual(items[key]["status"], "PASS", (label, key))

    def test_AT_140_1_E_5_corrupt_prop_and_scan_do_not_reach_consumers(self):
        p = base_prop(self.corrupt_base())
        control = self.case_repo()
        card0 = [self.M(control, "card", p)[1], self.M(control, "card", p, "--json")[1]]
        prop_args = verb16(self.corrupt_base())[14][3:]
        work = fx.new_dir("cw")
        shutil.copytree(control, work)
        self.assertEqual(self.M(work, "prop-new", "--run", rid(1), *prop_args)[0], 0)
        want_new = fx.EV(work)[-1]
        self.assertEqual(want_new["seq"], 6)
        for label in ("K08", "K09", "K10"):
            with self.subTest(label):
                repo = self.case_repo(corrupt_cases(p)[label])
                for argv, want in zip((["card", p], ["card", p, "--json"]), card0):
                    rc, out, err = self.M(repo, *argv)
                    self.assertEqual((rc, out, err), (0, want, ""), label)
                rc, out, err = self.M(repo, "prop-new", "--run", rid(1), *prop_args)
                self.assertEqual(rc, 0, (label, out, err))
                new = fx.EV(repo)[-1]
                self.assertEqual((new["id"], new["seq"]), (want_new["id"], 7), label)
        self.fetch_corrupt_scan()

    def fetch_corrupt_scan(self):
        srv = fx.serve({"/a": (200, {"Content-Type": "text/plain"}, b"hello")})
        self.addCleanup(srv.close)
        tpl = fx.p1_base()
        self.cli_ok(tpl, *run_open_args())
        fx.write_table(tpl, srv, [("a-src", "/a")])
        sources = {"S0": None, "S1": 5, "S2": [1, 2], "S3": [{"id": "a-src"}]}
        for label, bad in sources.items():
            with self.subTest(label):
                repo = fx.new_dir("fc")
                shutil.copytree(tpl, repo)
                if bad is not None:
                    append_raw(repo, raw_line(2, "research.scan", "researcher",
                                              {"run": rid(1), "sources": bad}))
                before = (repo / EVL).read_bytes()
                with fx.relaxed():
                    rc, out, err = self.M(repo, "research", "--fetch", "--run", rid(1))
                self.assertEqual(rc, 0, (label, out, err))
                seq = 2 if label == "S0" else 3
                self.assertIn("source a-src ok", out)
                self.assertIn("changed=true", out)
                self.assertIn(f"ok research.scan seq={seq} run=RUN-SI-001", out)
                after = (repo / EVL).read_bytes()
                self.assertTrue(after.startswith(before), label)
                (new,) = [json.loads(x) for x in after[len(before):].splitlines()]
                self.assertEqual(len(new["sources"]), 1, label)
                self.assertIs(new["sources"][0]["changed"], True, label)
                if label == "S0":
                    continue
                res = self.check(repo)
                self.assertEqual(self.S(res, "events.structure"), "FAIL")
                self.assertEqual({s for s, _ in self.F(res, "events.structure")}, {"seq=2"})
                self.assertEqual(self.S(res, "events.research"), "PASS")


if __name__ == "__main__":
    unittest.main()
