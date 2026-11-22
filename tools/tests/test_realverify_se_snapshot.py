"""realverify 每案副作用快照、假 claude 替身判定表、runner 洩漏判決與 CLI 動詞（DES §4.4／§6；
AT-SE-21／22／23／29／33／42／46／47、MU-SE-11／12／19／27／31）。

受測模組：`tools/lib/realverify/snapshot.py`、`fakeclaude.py`、`runner.py`、`cli.py`、
`sweep_legacy.py`、
`cases/__init__.py`。全部在假家目錄內跑，不碰真環境。
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib import sandbox_scope  # noqa: E402
from lib.realverify import cases as rv_cases  # noqa: E402
from lib.realverify import (  # noqa: E402
    cli,
    fakeclaude,
    leases,
    leases_discover,
    leases_undo,
    runner,
    snapshot,
    sweep_legacy,
)
from lib.realverify.sandbox import Sandbox  # noqa: E402


class _Home(unittest.TestCase):
    """假家目錄：`~/.autosdd`、`~/.claude`、`~/.claude.json` 都在 tmp。"""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.home = Path(self._td.name)
        self.autosdd, self.claude = (
            self.home / ".autosdd",
            self.home / ".claude",
        )
        for sub in (
            "handoff",
            "handback",
            "plans",
            "traces/park",
            "context_feed",
            "selfimproving",
        ):
            (self.autosdd / sub).mkdir(parents=True)
        (self.claude / "projects").mkdir(parents=True)
        (self.claude / "sessions").mkdir()
        (self.home / ".claude.json").write_text(
            json.dumps({"projects": {"a": {"x": 1}}}), encoding="utf-8"
        )
        self.loc = snapshot.Locations(
            self.autosdd, self.claude, self.home / ".claude.json", self.home
        )
        self.sched: dict[str, str] = {}
        self.procs: list[list] = []

    def take(self):
        return snapshot.take(
            self.loc, sched_procs=lambda: (dict(self.sched), list(self.procs))
        )


class SnapshotDiffTest(_Home):
    """snapshot.py：含本案字樣的差異＝洩漏；其餘只是雜訊；`~/.claude.json` 新增鍵一律洩漏。"""

    def test_noise_without_a_token_is_not_a_leak_but_a_token_hit_is(self):
        before = self.take()
        (self.autosdd / "handoff" / "someone-else.md").write_text(
            "x", encoding="utf-8"
        )
        (self.autosdd / "handback" / "SBXSID123_park_failed.md").write_text(
            "x", encoding="utf-8"
        )
        after = self.take()
        items = snapshot.diff(before, after, ["SBXSID123"])
        self.assertEqual(len(items), 2)
        self.assertEqual(
            [i["item"] for i in snapshot.leaks(items)],
            ["SBXSID123_park_failed.md"],
        )

    def test_s10_changed_file_content_is_searched_for_the_token(self):
        f = self.autosdd / "context_feed" / "x.json"
        f.write_text("aaaaaaaa", encoding="utf-8")
        g = self.autosdd / "context_feed" / "y.json"
        g.write_text("bbbbbbbb", encoding="utf-8")
        before = self.take()
        f.write_text("SBXSID123", encoding="utf-8")  # 同大小、內容含字樣
        g.write_text("unrelated", encoding="utf-8")
        leaked = snapshot.leaks(
            snapshot.diff(before, self.take(), ["SBXSID123"])
        )
        self.assertEqual([i["item"] for i in leaked], ["x.json"])

    def test_claude_json_new_key_is_always_a_leak_and_values_are_never_read(
        self,
    ):
        before = self.take()
        (self.home / ".claude.json").write_text(
            json.dumps(
                {
                    "projects": {
                        "a": 1,
                        "unrelated-key": {"secret": "SENTINEL-VALUE"},
                    }
                }
            ),
            encoding="utf-8",
        )
        after = self.take()
        self.assertNotIn("SENTINEL-VALUE", json.dumps(after))
        self.assertEqual(
            [
                i["item"]
                for i in snapshot.leaks(
                    snapshot.diff(before, after, ["nomatch"])
                )
            ],
            ["unrelated-key"],
        )

    def test_scheduler_process_and_jsonl_faces(self):
        (self.autosdd / "traces" / "autosdd_session_switch.jsonl").write_text(
            "old\n", encoding="utf-8"
        )
        before = self.take()
        self.sched["AutoSDD_HandoffSpawn_x"] = (
            r"pythonw C:\T\AutoSDD_RV_sbx_zzzz\x.py"
        )
        self.sched["AutoSDD_OpenItem_OI-1"] = "pythonw other"
        self.procs.append([5, "claude.exe -r SBXSID123"])
        with (self.autosdd / "traces" / "autosdd_session_switch.jsonl").open(
            "a", encoding="utf-8"
        ) as fh:
            fh.write('{"sid":"SBXSID123"}\n')
        items = snapshot.diff(
            before, self.take(), ["AutoSDD_RV_sbx_zzzz", "SBXSID123"]
        )
        self.assertEqual(
            {(i["face"], i["token"] != "") for i in items},
            {
                ("sched", True),
                ("sched", False),
                ("procs", True),
                ("jsonl", True),
            },
        )

    def test_tokens_for_uses_this_cases_identifiers_only(self):
        sb = mock.Mock(
            root=Path(tempfile.gettempdir()) / "AutoSDD_RV_sbx_abcd1234",
            home=Path(tempfile.gettempdir()) / "AutoSDD_RV_sbx_abcd1234",
            sid="SID-1",
        )
        toks = snapshot.tokens_for([sb], "RID-1")
        self.assertIn("SID-1", toks)
        self.assertIn("RID-1", toks)
        self.assertNotIn(
            sandbox_scope.SBX_PREFIX,
            toks,
            "泛用前綴會把別的視窗的沙盒誤判成本案洩漏（見模組 docstring）",
        )

    def test_dump_load_roundtrip_and_cli_diff(self):
        before = self.take()
        (self.autosdd / "handback" / "SBXSID123.md").write_text(
            "x", encoding="utf-8"
        )
        (self.autosdd / "handback" / "other.md").write_text(
            "x", encoding="utf-8"
        )
        a, b, tok = (
            self.home / "a.json",
            self.home / "b.json",
            self.home / "t.txt",
        )
        snapshot.dump(before, a)
        snapshot.dump(self.take(), b)
        tok.write_text("# 字樣\nSBXSID123\n", encoding="utf-8")
        for args, shown in (([str(a), str(b)], 2), ([str(a), str(b)], 1)):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.snapshot_cmd(
                    out=None,
                    diff=args,
                    tokens=str(tok) if shown == 1 else None,
                )
            self.assertEqual(rc, 0)
            self.assertIn(f"shown={shown}", buf.getvalue())


class RunnerLeakVerdictTest(_Home):
    """runner.run_case：前快照→案例→close→後快照；後快照取在 close 之後（AT-SE-21／23、
    MU-SE-11／12／19）。"""

    def setUp(self):
        super().setUp()
        for p in (
            mock.patch.object(leases, "LEASE_DIR", self.home / "L"),
            mock.patch.object(leases_undo, "list_procs", return_value=[]),
            mock.patch.object(runner, "_take", side_effect=self.take),
        ):
            p.start()
            self.addCleanup(p.stop)

    def run_fn(self, fn):
        return runner.run_case(
            rv_cases.Case("RV-T-leak", "fake", fn, (), False, False)
        )

    def test_leak_with_a_case_token_fails_with_the_documented_head(self):
        def fn(ctx):
            ctx.extra_tokens.append("SBXSID123")
            (self.autosdd / "handoff" / "SBXSID123.checked").write_text(
                "x", encoding="utf-8"
            )

        out = self.run_fn(fn)
        self.assertEqual(out.status, "fail")
        self.assertEqual(out.detail.splitlines()[0], "SIDE-EFFECT LEAK")

    def test_unrelated_change_is_noise_and_the_case_still_passes(self):
        def fn(ctx):
            (self.autosdd / "handoff" / "master-session.md").write_text(
                "x", encoding="utf-8"
            )

        out = self.run_fn(fn)
        self.assertEqual(out.status, "pass")
        self.assertTrue(
            any(n.startswith("SNAPSHOT-NOISE") for n in out.notes)
        )

    def test_what_the_case_cleans_up_itself_is_not_a_leak_because_the_after_snapshot_follows_close(
        self,
    ):
        def fn(ctx):
            ctx.extra_tokens.append("SBXSID123")
            p = self.autosdd / "handoff" / "SBXSID123.md"
            p.write_text("x", encoding="utf-8")
            ctx.sched_names.append("n")  # 讓 close 走撤排程路徑
            self.cleaned = p
            original = ctx.close

            def close():
                p.unlink()
                return original()

            ctx.close = close

        self.assertEqual(self.run_fn(fn).status, "pass")

    def test_close_revokes_the_lease_before_anything_else(self):
        order: list[str] = []

        def fn(ctx):
            ctx.sandboxes.append(Sandbox.create(probe_hook=False))

        with (
            mock.patch.object(
                sandbox_scope,
                "revoke",
                side_effect=lambda h: order.append("revoke"),
            ),
            mock.patch.object(
                leases,
                "revoke_run_kinds",
                side_effect=lambda *a, **k: order.append("kinds") or [],
            ),
            mock.patch.object(
                leases,
                "revoke_items",
                side_effect=lambda *a, **k: order.append("items") or [],
            ),
        ):
            self.assertEqual(self.run_fn(fn).status, "pass")
        self.assertEqual(order[0], "revoke", order)

    def test_batch_layer_counts_only_token_hits_as_leak(self):
        outs = {"n": 0}
        snaps = [self.take()]

        def case_fn(ctx):
            ctx.extra_tokens.append("SBXSID123")

        with mock.patch.object(
            leases_discover, "preflight", return_value=([], {})
        ):
            (self.autosdd / "handoff").mkdir(exist_ok=True)
            rc = runner.run(
                "t",
                [rv_cases.Case("RV-T-b", "fake", case_fn, (), False, False)],
                write_ledger=False,
            )
            self.assertEqual(rc, 0)
            (self.autosdd / "handback" / "unrelated.md").write_text(
                "x", encoding="utf-8"
            )
            outs["n"] += len(snaps)
        self.assertEqual(outs["n"], 1)

    def test_select_all_excludes_the_sideeffect_families(self):
        cases = {
            "RV-A": rv_cases.Case("RV-A", "park", lambda c: None),
            "RV-SE1": rv_cases.Case("RV-SE1", "sideeffect", lambda c: None),
            "RV-SE2": rv_cases.Case(
                "RV-SE2", "sideeffect_selftest", lambda c: None
            ),
        }
        self.assertEqual(
            [
                c.id
                for c in runner.select(
                    cases, case_id=None, family=None, all_=True, long=True
                )
            ],
            ["RV-A"],
        )
        self.assertEqual(
            [
                c.id
                for c in runner.select(
                    cases,
                    case_id=None,
                    family="sideeffect",
                    all_=False,
                    long=False,
                )
            ],
            ["RV-SE1"],
        )
        self.assertEqual(
            [
                c.id
                for c in runner.select(
                    cases,
                    case_id="RV-SE2",
                    family=None,
                    all_=False,
                    long=False,
                )
            ],
            ["RV-SE2"],
        )


class GrantSideEffectsTest(unittest.TestCase):
    """cases/__init__.py：`grant_side_effects`（AT-SE-25、MU-SE-13）。"""

    def test_window_true_requires_a_trusted_sandbox_and_leaves_identity_untouched_otherwise(
        self,
    ):
        from lib.realverify import interactive  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            plain = mock.Mock(spec=Sandbox, home=home)
            ctx = rv_cases.CaseContext("RV-T")
            with self.assertRaises(interactive.NotTrusted):
                ctx.grant_side_effects(plain, 10, window=True)

    def test_lease_minutes_declaration_raises_the_cap_up_to_lease_cap(self):
        from datetime import datetime, timedelta  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            now = datetime.now().astimezone()
            sandbox_scope.write_identity(
                home, run_id="r", sid="s", owner_pid=1, now=now
            )
            sb = mock.Mock(spec=Sandbox, home=home)
            ctx = rv_cases.CaseContext("RV-T", lease_minutes=300)
            got1 = ctx.grant_side_effects(sb, 200, window=False)
            got2 = ctx.grant_side_effects(sb, 400, window=False)
            self.assertAlmostEqual(
                (got1 - now).total_seconds() / 60, 200, delta=1
            )
            self.assertAlmostEqual(
                (got2 - now).total_seconds() / 60, 300, delta=1
            )
            self.assertLessEqual(
                got2 - now,
                timedelta(minutes=sandbox_scope.LEASE_CAP, seconds=5),
            )


class FakeClaudeTableTest(unittest.TestCase):
    """fakeclaude.py 的判定表與 C# 原始碼同表（AT-SE-46、MU-SE-31）。"""

    SID = "11111111-2222-4333-8444-555555555555"

    def test_full_matrix(self):
        argvs = {
            "resume": ["-r", self.SID, "P"],
            "fresh": ["P"],
            "fork": ["-r", self.SID, "--fork-session", "P"],
        }
        for mode in ("resume_ok", "fresh_ok", "fail", None):
            for name, argv in argvs.items():
                for projdir in ("proj", ""):
                    for rcfile in (None, "0", "3"):
                        cfg = {
                            "mode": mode,
                            "projdir": projdir,
                            "rc": rcfile,
                            "sleep": "7",
                        }
                        act = fakeclaude.decide(argv, cfg)
                        want_ok = bool(projdir) and (
                            (mode == "resume_ok" and name == "resume")
                            or (
                                mode == "fresh_ok"
                                and name in ("fresh", "fork")
                            )
                        )
                        if not want_ok:
                            self.assertEqual(
                                (act.kind, act.rc),
                                ("exit", int(rcfile) if rcfile else 1),
                                (mode, name, projdir, rcfile),
                            )
                        elif mode == "resume_ok":
                            self.assertEqual(
                                (act.kind, Path(act.path).name, act.sleep),
                                ("append", f"{self.SID}.jsonl", 7),
                            )
                        else:
                            self.assertEqual(
                                (act.kind, Path(act.path).suffix, act.sleep),
                                ("new", ".jsonl", 7),
                            )

    def test_csharp_is_generated_from_the_same_table(self):
        src = fakeclaude.csharp_source()
        for n, (mode, shape, kind) in enumerate(fakeclaude.TABLE):
            self.assertIn(
                f"// ROW {n}: mode={mode} shape={shape} action={kind}", src
            )
        for token in (
            "fakeclaude.jsonl",
            'Cfg("mode"',
            'Cfg("projdir"',
            'Cfg("rc"',
            'Cfg("sleep"',
            "--fork-session",
        ):
            self.assertIn(token, src)

    def test_build_registers_the_temp_file_before_compiling_and_passes_the_gui_flag(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.object(leases, "LEASE_DIR", Path(d) / "L"),
        ):
            seen: list = []

            def runner_(script):
                seen.append(
                    (
                        script,
                        [
                            r["state"]
                            for r in leases.read_rows(
                                next((Path(d) / "L").glob("*.jsonl"))
                            )
                        ],
                    )
                )
                (Path(d) / "bin" / "claude.exe").write_bytes(b"MZ")
                return 0, ""

            exe = fakeclaude.build(Path(d), runner=runner_)
            self.assertEqual(exe, Path(d) / "bin" / "claude.exe")
            self.assertIn("-OutputType WindowsApplication", seen[0][0])
            self.assertEqual(seen[0][1], ["intent"])
            self.assertEqual(
                leases.read_rows(next((Path(d) / "L").glob("*.jsonl")))[-1][
                    "state"
                ],
                "made",
            )

    def test_real_executable_obeys_the_table_on_windows_and_is_an_env_gap_elsewhere(
        self,
    ):
        """真編出 GUI 子系統 exe（PowerShell 5.1 Add-Type）並真執行：
        四種模式的結束碼與逐字稿落點與判定表一致；
        非 Windows 沒有這個載具，必須回 EnvMissing（不是靜默通過）。"""
        import os  # noqa: PLC0415
        import subprocess  # noqa: PLC0415

        from lib.realverify.driver import EnvMissing  # noqa: PLC0415

        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.object(leases, "LEASE_DIR", Path(d) / "L"),
        ):
            home = Path(d) / "AutoSDD_RV_sbx_fake0001"
            if os.name != "nt":
                with self.assertRaises(EnvMissing):
                    fakeclaude.build(home)
                return
            exe = fakeclaude.build(home)
            proj = home / "proj"
            fakeclaude.configure(home, "resume_ok", sleep=0, projdir=proj)
            self.assertEqual(
                subprocess.run(
                    [str(exe), "-r", self.SID, "P"],
                    cwd=d,
                    timeout=60,
                    check=False,
                ).returncode,
                0,
            )
            self.assertEqual(
                [p.name for p in proj.iterdir()], [f"{self.SID}.jsonl"]
            )
            fakeclaude.configure(home, "fresh_ok", sleep=0)
            self.assertEqual(
                subprocess.run(
                    [str(exe), "P"], cwd=d, timeout=60, check=False
                ).returncode,
                0,
            )
            self.assertEqual(len(list(proj.iterdir())), 2)
            fakeclaude.configure(home, "fail", rc=3)
            self.assertEqual(
                subprocess.run(
                    [str(exe), "-r", self.SID], cwd=d, timeout=60, check=False
                ).returncode,
                3,
            )
            fakeclaude.configure(
                home, "resume_ok", sleep=0
            )  # 成功模式遇不適用 argv ⇒ 照 fail（rc 檔＝3）
            self.assertEqual(
                subprocess.run(
                    [str(exe), "P"], cwd=d, timeout=60, check=False
                ).returncode,
                3,
            )
            calls = fakeclaude.calls(home)
            self.assertEqual(len(calls), 4)
            self.assertEqual(calls[0]["argv"], ["-r", self.SID, "P"])

    def test_configure_registers_the_transcript_dir_before_writing_projdir(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.object(leases, "LEASE_DIR", Path(d) / "L"),
        ):
            fakeclaude.configure(
                Path(d),
                "resume_ok",
                sleep=3,
                projdir=Path(d) / "AutoSDD_RV_sbx_x" / "proj",
            )
            rows = leases.read_rows(next((Path(d) / "L").glob("*.jsonl")))
            self.assertEqual(
                (rows[0]["kind"], rows[0]["state"]),
                ("transcript_dir", "intent"),
            )
            self.assertEqual(
                (Path(d) / "fakeclaude.mode").read_text(encoding="utf-8"),
                "resume_ok",
            )
            with self.assertRaises(ValueError):
                fakeclaude.configure(Path(d), "bogus")


class SweepLegacyTest(_Home):
    """sweep_legacy.py／cli.sweep：`--legacy` 只列、`--apply` 才刪、永不觸及 X6／X8（AT-SE-29）。"""

    def seed(self):
        files = [
            self.autosdd / "handoff" / "aab03328-aaaa.checked",
            self.autosdd / "context_feed" / "57d0ccad-x.json",
            self.autosdd / "traces" / "park" / "57d0ccad-x.json",
        ]
        keep = [
            self.autosdd / "handoff" / "someone-else.md",
            self.autosdd / "traces" / "autosdd_session_switch.jsonl",
            self.home / ".claude.json",
        ]
        for p in files + keep:
            p.write_text(
                "x" if p.suffix != ".jsonl" else "57d0ccad\n",
                encoding="utf-8",
            )
        x7 = self.claude / "projects" / "C--T-AutoSDD-RV-sbx-78znhvop"
        x7.mkdir()
        return files, keep, x7

    def test_listing_changes_nothing_apply_removes_only_the_fixed_set(self):
        files, keep, x7 = self.seed()
        digest = lambda: {str(p): p.read_bytes() for p in keep}  # noqa: E731
        before = digest()
        with (
            mock.patch(
                "lib.realverify.sandbox.real_autosdd",
                lambda *a: self.autosdd.joinpath(*a),
            ),
            mock.patch(
                "lib.realverify.sandbox.projects_dir",
                lambda: self.claude / "projects",
            ),
        ):
            found = sweep_legacy.items()
            self.assertEqual({it.path for it in found}, {*files, x7})
            self.assertTrue(all(p.exists() for p in files))
            self.assertEqual(sweep_legacy.apply(found), [])
        self.assertFalse(any(p.exists() for p in files) or x7.exists())
        self.assertEqual(digest(), before, "X6／X8／別人的檔位元組不變")

    def test_apply_without_legacy_is_a_usage_error(self):
        self.assertEqual(cli.sweep(apply=True), cli.RC_USAGE)

    def test_dry_run_prints_a_verdict_and_never_returns_nonzero_for_findings(
        self,
    ):
        buf = io.StringIO()
        with (
            redirect_stdout(buf),
            mock.patch.object(
                leases, "orphan_rows", return_value=[("sandbox_root", "x")]
            ),
            mock.patch.object(leases_discover, "scan", return_value=[]),
        ):
            rc = cli.sweep(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertEqual(
            buf.getvalue().strip().splitlines()[-1],
            "SWEEP_VERDICT=revoked n=1 dry_run=1",
        )


if __name__ == "__main__":
    unittest.main()
