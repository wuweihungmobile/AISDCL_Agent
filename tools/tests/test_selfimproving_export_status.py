"""SelfImproving P1 `status`、`export` 與輸出穩定性的驗收測試。

對應 TCS-P1 的 ES 檔：AT-103-1、AT-132-5、AT-140-2。

方法名含 AT 底線形。合成 repo 於 tmp 目錄；`status`／`export` 的逐字稿目錄一律隔離（HOME 與
USERPROFILE 指向空 tmp、移除 CLAUDE_CONFIG_DIR），使 friction_reconcile 恆為 NOT-EVALUABLE。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
from _selfimproving_fixtures import EVL, LEDGER, PROPS_REL, SiTestCase, aid, ev, obs_id, pid, rid

TOOLS = fx.TOOLS
ENTRY = TOOLS / "selfimproving.py"
STATUS_KEYS = [
    "events_detected",
    "unavailable",
    "open_runs",
    "pending_props",
    "suspended",
    "cooldowns",
    "skip_reasons",
    "capacity",
    "root_cause_changes",
    "reopen_candidates",
    "pending_windows",
    "friction_reconcile",
    "no_event",
    "console_pending",
    "measure",
]
EXPORT_KEYS = [
    "schema_rev",
    "kind",
    "generated_at",
    "head_sha",
    "items",
    "next_since",
    "truncated",
    "ne",
    "problems",
]


def setUpModule() -> None:
    fx.setup("si_es_")


def tearDownModule() -> None:
    fx.teardown()


def ledger_bytes(repo: Path):
    p = repo / EVL
    return p.read_bytes() if p.is_file() else None


class StatusCase(SiTestCase):
    def setUp(self) -> None:
        super().setUp()
        iso = fx.new_dir("emptyhome")
        iso.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(iso), "USERPROFILE": str(iso)})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def anchor(self):
        return (datetime.now().astimezone() - timedelta(days=1)).replace(microsecond=0)

    def defect_rows(self, ta, which):
        utc = ta.astimezone(UTC)

        def day(k):
            return (utc + timedelta(days=k)).strftime("%Y-%m-%d")

        table = {
            "Q1": (fx.def_id(11), day(0), "P2", "open"),
            "Q2": (fx.def_id(12), day(0), "P1", "open（workaround-applied）"),
            "Q3": (fx.def_id(13), day(0), "P3", "open"),
            "Q4": (fx.def_id(14), day(0), "P2", "fixed@abc1234"),
            "Q5": (fx.def_id(15), day(-1), "P2", "open"),
            "Q6": (fx.def_id(16), day(1), "P2", "open"),
        }
        return [(*table[k], f"tools/a{k[1]}.py:1") for k in which]

    def status_repo(self, extra=()):
        ta = self.anchor()

        def t(seq):
            return (ta + timedelta(minutes=seq - 9)).isoformat(timespec="seconds")

        E = fx.ev
        events = [
            fx.run_open_ev(1),
            fx.skip_ev(1),
            fx.prop_ev(
                124, 1, cls="P", target=["playbooks/demo.yaml"], sources=[obs_id(2), obs_id(3)]
            ),
            fx.dec_ev(124, "approve"),
            E("app.sandbox", prop=pid(124)),
            E("app.verify", prop=pid(124), verdict="PASS"),
            fx.dec_ev(124, "promote"),
            E("app.promote", prop=pid(124)),
            E("run.close", run=rid(1), outcomes={pid(124): "promoted"}),
            fx.run_open_ev(2),
            fx.skip_ev(2, reason="quota-band", band="high", note="夾具"),
            E("attr", "SA", id=aid(1), type="link", **{"from": obs_id(9)}, reopens=obs_id(2)),
            E("attr.confirm", "QA", att=aid(1)),
            E("attr", "SA", id=aid(2), type="link", **{"from": obs_id(10)}, reopens=obs_id(6)),
            fx.prop_ev(
                125,
                2,
                cls="D",
                target=["docs/notes/demo.md"],
                route="handoff:DEF",
                sources=[obs_id(1)],
            ),
            fx.prop_ev(126, 2, cls="D", target=["docs/notes/other.md"], sources=[obs_id(4)]),
            fx.dec_ev(126, "reject"),
            E(
                "attr",
                "SA",
                id=aid(3),
                type="root",
                obs=[obs_id(4)],
                items=[["DOC", "docs/x/"]],
                root_cause="tools/a-b",
            ),
            E(
                "attr",
                "SA",
                id=aid(4),
                type="root",
                obs=[obs_id(4)],
                items=[["DOC", "docs/x/"]],
                root_cause="tools/c-d",
            ),
        ]
        for i, e in enumerate(events, start=1):
            e["t"] = t(i)
        repo = fx.make_p1_repo(
            fx.new_dir("ss"),
            events=events + list(extra),
            defs=self.defect_rows(ta, ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]),
        )
        return repo

    def quiet_repo(self):
        ta = self.anchor()
        events = [
            fx.run_open_ev(1),
            ev("run.close", run=rid(1), no_event=True, t=ta.isoformat(timespec="seconds")),
        ]
        return fx.make_p1_repo(
            fx.new_dir("sq"), events=events, defs=self.defect_rows(ta, ["Q3", "Q4", "Q5"])
        )

    def sc_export(self):
        repo = fx.p1_base()
        self.cli_ok(repo, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main")
        self.cli_ok(
            repo, "research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "離線驗證"
        )
        self.cli_ok(
            repo,
            "attr",
            "--type",
            "root",
            "--by",
            "SA",
            "--obs",
            obs_id(1),
            "--item",
            "DOC=docs/06_quality/",
            "--root-cause",
            "docs/stale-note",
        )
        self.cli_ok(repo, "attr-confirm", "--att", aid(1), "--by", "QA")
        self.cli_ok(repo, "prop-new", "--run", rid(1), *fx.good_prop_args(repo, "P"))
        guard = ".claude/hooks/new_guard_e.py"
        patch = fx.patch_join(
            fx.patch_add(guard, ["x = 1"]), fx.patch_add("docs/notes/clean_e.md", ["clean"])
        )
        self.cli_ok(
            repo,
            "prop-new",
            "--run",
            rid(1),
            *fx.good_prop_args(
                repo,
                "D",
                action="add",
                target=["docs/notes/clean_e.md", guard],
                patch=patch,
                handoff="T1",
                sources=[obs_id(3)],
            ),
        )
        self.cli_ok(repo, "run-open", "--trigger", "b", "--coord", "tools/a.py:2", "--by", "main")
        self.cli_ok(repo, "run-close", "--run", rid(2), "--by", "main")
        fx.commit_all(repo, "sc-export")
        return repo


class TestStatus(StatusCase):
    """受測：`tools/lib/selfimproving/status.py`（status 摘要）。"""

    def test_AT_103_1_1_status_summary(self):
        repo = self.status_repo()
        snap0 = fx.snap(repo)
        rc, out, err = self.M(repo, "status", "--json")
        self.assertEqual(rc, 0, err)
        obj = json.loads(out)
        self.assertEqual(list(obj), STATUS_KEYS)
        got = {(e["trigger"], e["subject"]) for e in obj["events_detected"]}
        self.assertEqual(
            got,
            {
                ("b", aid(1)),
                ("c", fx.def_id(11)),
                ("c", fx.def_id(12)),
                ("c", fx.def_id(16)),
                ("d", pid(124)),
            },
        )
        self.assertEqual((obj["unavailable"], obj["no_event"]), ([], False))
        run = obj["open_runs"]
        self.assertEqual(len(run), 1)
        self.assertEqual(
            (run[0]["run"], run[0]["opened_seq"], run[0]["research"], run[0]["props"]),
            (rid(2), 10, {"kind": "research.skip", "seq": 11}, [pid(125), pid(126)]),
        )
        events = fx.EV(repo)
        d125 = next(e for e in events if e["kind"] == "prop" and e["id"] == pid(125))["digest"]
        self.assertEqual(
            obj["pending_props"],
            [
                {
                    "id": pid(125),
                    "rev": 1,
                    "state": "proposed",
                    "route": "handoff:DEF",
                    "digest8": d125.split(":")[1][:8],
                }
            ],
        )
        self.assertIsNone(obj["suspended"])
        self.assertEqual(
            obj["cooldowns"],
            [
                {
                    "prop": pid(126),
                    "cls": "D",
                    "target": ["docs/notes/other.md"],
                    "root_cause": ["tools/a-b", "tools/c-d"],
                    "rejected_seq": 17,
                    "reason_class": "未說明",  # P2 R75：冷卻欄末鍵（夾具 dec 預設）
                }
            ],
        )
        self.assertEqual(obj["skip_reasons"], {"quota-band": 1, "offline": 1, "helmsman": 0})
        self.assertEqual(
            obj["capacity"], {"status": "NOT-EVALUABLE", "reason": "no-axis-evaluable"}
        )
        self.assertEqual(
            (obj["root_cause_changes"], obj["reopen_candidates"], obj["pending_windows"]),
            (1, {"unsettled": 1}, []),
        )
        self.assertEqual(
            obj["friction_reconcile"],
            {"status": "NOT-EVALUABLE", "reason": "transcript-unavailable"},
        )
        rc, text, _ = self.M(repo, "status")
        for needle in ("capacity NOT-EVALUABLE", "suspended", "skip_reasons"):
            self.assertIn(needle, text)
        self.assertNotIn("無事件", text)
        for e in obj["events_detected"]:
            self.assertIn(e["subject"], text)
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_103_1_E_2_suspended_needs_consecutive_bad_windows(self):
        mixes = {
            "a": (["clean", "recurred"], None),
            "b": (["recurred", "clean"], None),
            "c": (["recurred", "rolled-back"], {"run": rid(1)}),
            "d": (["recurred", "pending", "rolled-back"], {"run": rid(1)}),
        }
        for label, (results, want) in mixes.items():
            events = [fx.run_open_ev(1), fx.skip_ev(1)]
            for n, res in zip(range(124, 130), results):
                events += fx._chain(
                    n,
                    [
                        *fx._verify(n, "PASS"),
                        fx.dec_ev(n, "promote"),
                        ev("app.promote", prop=pid(n)),
                        ev("mea.open", prop=pid(n)),
                        ev("mea.close", prop=pid(n), result=res),
                    ],
                )
            repo = fx.p1_base()
            fx.set_params(repo, stop_after_bad=2)
            fx.write_events(repo, events)
            self.assertEqual(self.MJ(repo, "status")["suspended"], want, label)

    def test_AT_103_1_E_3_pending_detection_window_and_friction(self):
        repo = fx.p1_base()
        fx.write_events(repo, fx.sc_legal())
        pending = {(p["id"], p["state"]) for p in self.MJ(repo, "status")["pending_props"]}
        want = {(pid(n), "proposed") for n in (128, 129, 134)}
        want |= {(pid(n), "verified") for n in (131, 132, 133)}
        self.assertEqual(pending, want)
        link = {"type": "link"}
        window = [
            fx.run_open_ev(1),
            fx.skip_ev(1),
            ev("attr", "SA", id=aid(1), **link, **{"from": obs_id(9)}, reopens=obs_id(2)),
            ev("attr.confirm", "QA", att=aid(1)),
            ev("run.close", run=rid(1), no_event=True),
            fx.run_open_ev(2),
            fx.skip_ev(2),
            ev("attr", "SA", id=aid(2), **link, **{"from": obs_id(10)}, reopens=obs_id(6)),
            ev("attr.confirm", "QA", att=aid(2)),
        ]
        repo = fx.p1_base()
        fx.write_events(repo, window[:5])
        obj = self.MJ(repo, "status")
        self.assertEqual((obj["events_detected"], obj["no_event"]), ([], True))
        fx.append_events(repo, window[5:])
        obj = self.MJ(repo, "status")
        got = [(e["trigger"], e["subject"]) for e in obj["events_detected"]]
        self.assertEqual((got, obj["no_event"]), ([("b", aid(2))], False))
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
        config = fx.new_dir("cfg")
        (config / "projects" / slug).mkdir(parents=True)
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}):
            found = self.MJ(repo, "status")["friction_reconcile"]
            (config / "projects" / slug).rmdir()
            gone = self.MJ(repo, "status")["friction_reconcile"]
        self.assertEqual(
            found, {"status": "NOT-EVALUABLE", "reason": "transcript-parser-not-established"}
        )
        self.assertEqual(gone, {"status": "NOT-EVALUABLE", "reason": "transcript-unavailable"})

    def test_AT_103_1_E_1_status_edges(self):
        repo = fx.p1_base()
        obj = self.MJ(repo, "status")
        self.assertEqual((obj["events_detected"], obj["no_event"]), ([], True))
        self.assertEqual(obj["unavailable"], [{"trigger": "c", "reason": "anchor-unavailable"}])
        self.assertIn("無事件（1 個來源量不到）", self.M(repo, "status")[1])
        self.assertEqual((obj["open_runs"], obj["pending_props"], obj["cooldowns"]), ([], [], []))
        repo = self.quiet_repo()
        obj = self.MJ(repo, "status")
        self.assertEqual((obj["no_event"], obj["unavailable"]), (True, []))
        text = self.M(repo, "status")[1]
        self.assertIn("無事件", text)
        self.assertNotIn("無事件（", text)
        self.assertFalse("通過" in text or "通過" in json.dumps(obj, ensure_ascii=False))
        repo = fx.p1_base()
        fx.write_events(repo, fx.sc_susp())
        self.assertEqual(self.MJ(repo, "status")["suspended"], {"run": rid(1)})
        fx.append_events(repo, [ev("dec", "掌舵者", dkind="resume", run=rid(1))])
        self.assertIsNone(self.MJ(repo, "status")["suspended"])
        repo = self.status_repo(extra=[fx.dec_ev(126, "unblock")])
        self.assertEqual(self.MJ(repo, "status")["cooldowns"], [])
        repo = fx.p1_base()
        e = [fx.run_open_ev(1), fx.skip_ev(1)]
        for n in (124, 125):
            e += [
                fx.prop_ev(n, 1, target=[f"docs/notes/n{n}.md"]),
                fx.dec_ev(n, "approve"),
                ev("app.sandbox", prop=pid(n)),
                ev("app.verify", prop=pid(n), verdict="PASS"),
                fx.dec_ev(n, "promote"),
                ev("app.promote", prop=pid(n)),
                ev("mea.open", prop=pid(n)),
            ]
        e124 = len(e) + 1
        e += [ev("mea.close", prop=pid(124), result="pending")]
        e125 = len(e) + 1
        e += [
            ev("mea.close", prop=pid(125), result="pending"),
            ev("mea.amend", prop=pid(125), window=e125, **{"from": "pending", "to": "clean"}),
        ]
        fx.write_events(repo, e)
        self.assertEqual(
            self.MJ(repo, "status")["pending_windows"], [{"prop": pid(124), "close_seq": e124}]
        )
        repo = self.quiet_repo()
        fx.append_events(repo, [])
        with (repo / EVL).open("ab") as fh:
            fh.write("這不是 JSON\n".encode())
        rc, out, err = self.M(repo, "status", "--json")
        self.assertEqual(rc, 0, err)
        self.assertEqual(list(json.loads(out)), STATUS_KEYS)


class TestExport(StatusCase):
    def export(self, repo, *argv):
        rc, out, err = self.M(repo, "export", "--json", *argv)
        self.assertEqual(rc, 0, out + err)
        self.assertTrue(out.endswith("\n") and out.count("\n") == 1)
        return json.loads(out)

    def test_AT_132_5_1_five_kinds(self):
        repo = self.sc_export()
        snap0, head = fx.snap(repo), fx.head(repo)
        objs = {
            k: self.export(repo, "--kind", k)
            for k in ("observations", "events", "proposals", "runs", "status")
        }
        for k, o in objs.items():
            self.assertEqual(list(o), EXPORT_KEYS, k)
            self.assertEqual((o["schema_rev"], o["kind"], o["head_sha"]), (1, k, head))
            self.assertIsNotNone(datetime.fromisoformat(o["generated_at"]).utcoffset())
        obs = objs["observations"]["items"]
        self.assertEqual(len(obs), 10)
        self.assertEqual(
            list(obs[0]),
            [
                "id",
                "time",
                "context",
                "symptom",
                "evidence",
                "category",
                "severity",
                "disposition",
                "marks",
                "marks_kv",
                "line",
                "buckets",
            ],
        )
        lines = fx.read(repo, LEDGER).split("\n")
        for item in obs:
            self.assertTrue(lines[item["line"] - 1].startswith(f"| {item['id']} |"))
        self.assertEqual(objs["events"]["items"], fx.EV(repo))
        props = objs["proposals"]["items"]
        self.assertEqual(len(props), 2)
        self.assertEqual(
            list(props[0]),
            [
                "id",
                "state",
                "route",
                "cls",
                "action",
                "run",
                "rev",
                "digest",
                "target",
                "touched",
                "touched_count",
                "sources",
                "created_seq",
                "last_seq",
                "verdict",
                "flags",
                "cooldown",
                "card",
                "window",
            ],
        )
        for p in props:
            patch = (repo / PROPS_REL / p["id"] / f"r{p['rev']}.patch").read_text(encoding="utf-8")
            want = sorted(
                {x for m in re.findall(r"(?m)^diff --git a/(\S+) b/(\S+)$", patch) for x in m}
            )
            self.assertEqual(p["touched"], want)
        runs = objs["runs"]["items"]
        self.assertEqual(
            list(runs[0]),
            [
                "id",
                "opened_seq",
                "closed_seq",
                "trigger",
                "head_sha",
                "research",
                "prop_ids",
                "outcome",
            ],
        )
        self.assertEqual((runs[0]["outcome"], runs[1]["outcome"]), (None, "no_event"))
        self.assertEqual(len(objs["status"]["items"]), 1)
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_132_5_E_3_truncated_only_when_more_than_limit(self):
        for count in (3, 4):
            repo = fx.p1_base()
            fx.write_events(repo, [fx.run_open_ev(i) for i in range(1, count + 1)])
            obj = self.export(repo, "--kind", "events", "--limit", "3")
            seqs = [e["seq"] for e in obj["items"]]
            want = (3, False, None) if count == 3 else (3, True, 3)
            self.assertEqual((len(seqs), obj["truncated"], obj["next_since"]), want, count)
            self.assertEqual(seqs, [1, 2, 3])
        repo = fx.p1_base()
        fx.write_events(repo, [fx.run_open_ev(i) for i in range(1, 4)])
        for limit, want in ((4, (3, False, None)), (2, (2, True, 2))):
            obj = self.export(repo, "--kind", "events", "--limit", str(limit))
            got = (len(obj["items"]), obj["truncated"], obj["next_since"])
            self.assertEqual(got, want, limit)

    def test_AT_132_5_E_1_usage_pages_and_carriers(self):
        repo = self.sc_export()
        n = len(fx.EV(repo))
        bad = [
            [],
            ["--kind", "status"],
            ["--json"],
            ["--json", "--kind", "bogus"],
            ["--json", "--kind", "events", "--limit", "0"],
            ["--json", "--kind", "events", "--limit", "501"],
            ["--json", "--kind", "events", "--since", "-1"],
            ["--json", "--kind", "events", "--since", "abc"],
            ["--json", "--kind", "status", "--since", "1"],
            ["--json", "--kind", "events", "--id", "X"],
            ["--json", "--kind", "observations", "--id", "X"],
            ["--json", "--kind", "status", "--id", "X"],
            ["--json", "--kind", "proposals", "--id", "bad"],
            ["--json", "--kind", "runs", "--id", "bad"],
        ]
        calls = [argv for argv in bad if argv != ["--kind", "status"]]
        calls.append(["--kind", "status"])
        for argv in calls:
            with self.subTest(argv=argv):
                self.usage_error(*self.M(repo, "export", *argv), msg=str(argv))
        seen, since, last = [], None, None
        for _ in range(n):
            extra = ["--since", str(since)] if since is not None else []
            page = self.export(repo, "--kind", "events", "--limit", "3", *extra)
            seen += [e["seq"] for e in page["items"]]
            if page["truncated"]:
                self.assertEqual(page["next_since"], page["items"][-1]["seq"])
                since = page["next_since"]
            else:
                last = page
                break
        self.assertEqual(seen, list(range(1, n + 1)))
        self.assertEqual((last["truncated"], last["next_since"]), (False, None))
        one = self.export(repo, "--kind", "proposals", "--id", pid(124))
        self.assertEqual([p["id"] for p in one["items"]], [pid(124)])
        self.assertEqual(
            self.export(repo, "--kind", "proposals", "--id", pid(900 + 5))["items"], []
        )
        r0 = fx.p1_base()
        for kind in ("events", "proposals", "runs", "status"):
            o = self.export(r0, "--kind", kind)
            self.assertIn({"field": "events", "reason": "carrier-not-established"}, o["ne"])
            self.assertEqual(len(o["items"]), 1 if kind == "status" else 0)

    def test_AT_132_5_E_2_differential_and_isolation(self):
        repo = self.sc_export()
        sentinel = self.home / "research" / "sentinel.txt"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_bytes(b"SENTINEL-DO-NOT-LEAK")
        snap0, home0 = fx.snap(repo), fx.tree_files(self.home)
        outs = []
        st = self.export(repo, "--kind", "status")
        outs.append(json.dumps(st))
        same = lambda o: {  # noqa: E731
            k: v for k, v in o.items() if k not in ("console_pending", "capacity")
        }
        self.assertEqual(same(st["items"][0]), same(self.MJ(repo, "status")))  # R99 (b)
        self.assertEqual(st["items"][0]["console_pending"]["reason"], "export-reads-no-home")
        props = self.export(repo, "--kind", "proposals")
        outs.append(json.dumps(props))
        for p in props["items"]:
            self.assertEqual(p["card"], self.M(repo, "card", p["id"])[1])
        self.assertFalse(any("SENTINEL" in o for o in outs))
        self.assertEqual((fx.snap(repo), fx.tree_files(self.home)), (snap0, home0))
        bad = fx.new_dir("bd")
        shutil.copytree(repo, bad)
        cells = fx.read(bad, LEDGER).split("\n")
        fx.put(
            bad,
            LEDGER,
            "\n".join(cells).rstrip("\n")
            + "\n| "
            + obs_id(50)
            + " | 只有 | 八欄 | 的 | 壞 | 列 | P3 | open |\n",
        )
        with (bad / EVL).open("ab") as fh:
            fh.write(b"not json at all\n")
        obs = self.export(bad, "--kind", "observations")
        broken = [i for i in obs["items"] if i.get("valid") is False]
        self.assertEqual([list(i) for i in broken], [["line", "raw", "valid"]])
        self.assertIn("ROW-ARITY", {p["code"] for p in obs["problems"]})
        evs = self.export(bad, "--kind", "events")
        self.assertEqual(len(evs["items"]), len(fx.EV(repo)))
        self.assertTrue(evs["problems"])
        tam = fx.new_dir("tm")
        shutil.copytree(repo, tam)
        patch = tam / PROPS_REL / pid(124) / "r1.patch"
        patch.write_bytes(patch.read_bytes() + b"+extra\n")
        o = self.export(tam, "--kind", "proposals")
        cards = {p["id"]: p["card"] for p in o["items"]}
        self.assertIsNone(cards[pid(124)])
        self.assertIsNotNone(cards[pid(125)])
        self.assertIn(
            {"field": f"proposals.{pid(124)}.card", "reason": "CARD-INCONSISTENT"}, o["ne"]
        )


class TestStability(StatusCase):
    def env(self, **extra):
        iso = fx.new_dir("iso")
        iso.mkdir()
        env = {
            **fx.genv(),
            "AUTOSDD_SI_DIR": str(self.home),
            "HOME": str(iso),
            "USERPROFILE": str(iso),
            **extra,
        }
        env.pop("CLAUDE_CONFIG_DIR", None)
        return env

    def run_cli(self, argv, env, cwd=None):
        cp = subprocess.run(
            [sys.executable, str(ENTRY), *argv], capture_output=True, env=env, cwd=cwd, check=False
        )
        self.assertEqual(cp.returncode, 0, cp.stderr.decode("utf-8", "replace"))
        return cp.stdout

    @staticmethod
    def strip_gen(raw: bytes) -> bytes:
        return re.sub(rb'"generated_at": "[^"]*"', b'"generated_at": ""', raw)

    def test_AT_140_2_1_outputs_are_stable(self):
        repo = self.sc_export()
        env = self.env(PYTHONIOENCODING="cp950")
        cmds = [
            ["status", "--json"],
            ["scan", "--json"],
            ["card", pid(124), "--json"],
            *[
                ["export", "--json", "--kind", k]
                for k in ("observations", "events", "proposals", "runs", "status")
            ],
        ]
        for argv in cmds:
            a = self.run_cli([*argv, "--repo", str(repo)], env)
            b = self.run_cli([*argv, "--repo", str(repo)], env)
            self.assertEqual(self.strip_gen(a), self.strip_gen(b), argv)
            text = a.decode("utf-8")
            self.assertFalse(a.startswith(b"\xef\xbb\xbf") or b"\r" in a)
            keys = json.loads(text, object_pairs_hook=lambda pairs: [k for k, _ in pairs])
            if argv[0] == "status":
                self.assertEqual(keys, STATUS_KEYS)
            elif argv[0] == "scan":
                self.assertEqual(
                    keys,
                    [
                        "schema_rev",
                        "status",
                        "unavailable_count",
                        "anchor",
                        "sources",
                        "candidates",
                        "buckets",
                    ],
                )
            elif argv[0] == "card":
                self.assertEqual(
                    keys, ["schema_rev", "prop", "rev", "digest", "core_lines", "text", "parsed"]
                )
            else:
                self.assertEqual(keys, EXPORT_KEYS)
            if argv[0] != "status":
                self.assertEqual(json.loads(text)["schema_rev"], 1)

    def test_AT_140_2_E_1_no_unstable_sources(self):
        repo = self.sc_export()
        decoy = fx.new_dir("decoy")
        decoy.mkdir()
        (decoy / "tools").mkdir()
        (decoy / "tools" / "selfimproving.py").write_bytes(b"raise SystemExit(99)\n")
        env_a = self.env(PYTHONHASHSEED="0", TZ="UTC")
        env_b = self.env(PYTHONHASHSEED="12345", TZ="Pacific/Auckland")
        cmds = [
            ["status", "--json"],
            ["scan", "--json"],
            ["card", pid(124)],
            ["export", "--json", "--kind", "proposals"],
            ["export", "--json", "--kind", "events"],
        ]
        for argv in cmds:
            a = self.run_cli([*argv, "--repo", str(repo)], env_a, cwd=str(repo))
            b = self.run_cli([*argv, "--repo", str(repo)], env_b, cwd=str(decoy))
            self.assertEqual(self.strip_gen(a), self.strip_gen(b), argv)
            text = a.decode("utf-8")
            for secret in (str(repo), str(self.home), str(repo).replace("\\", "/")):
                self.assertNotIn(secret, text, argv)

    def test_AT_140_2_E_2_json_is_written_as_utf8_not_escaped(self):
        env = self.env(PYTHONIOENCODING="cp950")
        cjk = re.compile("[\u4e00-\u9fff]")
        review = fx.p1_base()
        fx.write_events(review, [ev("run.open", "主控", run=rid(1), trigger="a",
                                    coords=["tools/a.py:1"], head_sha="0" * 40)])  # fmt: skip
        link = {"type": "link", "from": obs_id(9), "reopens": obs_id(2)}
        window = fx.p1_base()
        fx.write_events(window, [
            fx.run_open_ev(1), fx.skip_ev(1), ev("attr", "SA", id=aid(1), **link),
            ev("attr.confirm", "QA", att=aid(1)),
        ])  # fmt: skip
        edge = self.quiet_repo()
        ta = datetime.fromisoformat(
            next(e for e in fx.EV(edge) if e["kind"] == "run.close")["t"]
        )
        fx.put(edge, "AISDLC_SDD/z.md", "K\n")
        fx.commit_all(edge, "K", when=(ta + timedelta(seconds=1)).isoformat(timespec="seconds"))
        cases = [
            ("a", review, ["export", "--json", "--kind", "events"], "主控", 0),
            ("b", fx.p1_base(), ["export", "--json", "--kind", "observations"], None, 0),
            ("c", window, ["status", "--json"], "同一症狀", 0),
            ("d", edge, ["scan", "--json"], "自動草稿", 0),
            ("e", self.sc_export(), ["card", pid(124), "--json"], "一、症狀", 0),
            ("f", fx.p1_base(), ["run-close", "--run", rid(99), "--by", "main", "--json"],
             "自動草稿", 1),
        ]  # fmt: skip
        for label, repo, argv, needle, rc_want in cases:
            cp = subprocess.run(
                [sys.executable, str(ENTRY), *argv, "--repo", str(repo)],
                capture_output=True, env=env, check=False,
            )  # fmt: skip
            raw = cp.stdout
            err = cp.stderr.decode("utf-8", "replace")
            self.assertEqual(cp.returncode, rc_want, (label, err))
            text = raw.decode("utf-8")
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw, label)
            self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n"), label)
            json.loads(text)
            self.assertNotRegex(text, r"\\u[0-9a-f]{4}", label)
            if needle is None:
                self.assertRegex(text, cjk, label)
            else:
                self.assertIn(needle.encode("utf-8"), raw, label)


if __name__ == "__main__":
    unittest.main()
