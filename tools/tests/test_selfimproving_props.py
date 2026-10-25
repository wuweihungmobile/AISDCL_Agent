"""SelfImproving P1 提案物件、前置檢查與卡面的驗收測試（TCS-P1 PR 檔）。

方法名含 AT 底線形。夾具全用 tmp 目錄內的合成 repo；編號於執行期組出。
"""

from __future__ import annotations

import hashlib
import json
import shutil
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p3_fixtures as f3
from _selfimproving_fixtures import (
    EVL,
    PROPS_REL,
    VNEW,
    SiTestCase,
    body_md,
    ev,
    good_prop_args,
    obs_id,
    pid,
    rid,
)

from lib.selfimproving import evwrite
from lib.selfimproving import git as si_git


def setUpModule() -> None:
    fx.setup("si_pr_")


def tearDownModule() -> None:
    fx.teardown()


def width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def ledger_bytes(repo: Path):
    p = repo / EVL
    return p.read_bytes() if p.is_file() else None


def props_of(repo: Path) -> list[dict]:
    return [e for e in fx.EV(repo) if e["kind"] == "prop"]


class PropCase(SiTestCase):
    def new(self, repo, run, cls="P", *extra, **over):
        rc, out, err = self.prop(repo, run, cls, *extra, **over)
        return rc, out, err

    def ok(self, repo, run, cls="P", **over):
        rc, out, err = self.new(repo, run, cls, **over)
        self.assertEqual(rc, 0, out + err)
        return out

    def rej(self, repo, run, codes, cls="P", msg="", **over):
        rc, out, _ = self.new(repo, run, cls, **over)
        self.rejected(rc, out, codes, msg)
        self.draft_ok(repo, out, msg)
        return out

    def card(self, repo, prop):
        rc, out, err = self.M(repo, "card", prop)
        self.assertEqual(rc, 0, out + err)
        return out.split("\n")


class TestSourcesAndRoute(PropCase):
    def test_AT_102_1_1_internal_source_suffices(self):
        repo = fx.p1_base()
        for _ in range(5):
            self.open_run(repo)
        md = fx.memory_dir(fx.new_dir("mem"))
        plan = [
            ("M", dict(memory_dir=md)),
            ("P", {}),
            ("R", {}),
            ("D", {}),
            (
                "D",
                dict(
                    target=["docs/notes/other.md"],
                    sources=[fx.def_id(1), obs_id(10)],
                    patch=fx.patch_mod("docs/notes/other.md", {3: "改過三"}),
                ),
            ),
        ]
        for i, (cls, over) in enumerate(plan, start=1):
            over.setdefault("sources", [obs_id(1), obs_id(10)])
            self.ok(repo, rid(i), cls, **over)
        events = props_of(repo)
        self.assertEqual([e["cls"] for e in events], ["M", "P", "R", "D", "D"])
        self.assertTrue(all(e["route"] == "loop" for e in events))
        self.assertEqual(events[0]["sources"], [obs_id(1), obs_id(10)])
        self.assertEqual(events[4]["sources"], [fx.def_id(1), obs_id(10)])
        for e in events:
            self.assertEqual(e["target"], sorted(set(e["target"])))
            self.assertEqual("preimage" in e, e["cls"] == "M")

    def test_AT_102_1_E_1_external_only_and_unresolved(self):
        row = [
            obs_id(11),
            "2026-10-20 01:00",
            "情境",
            "症狀",
            "tools/lib/selfimproving/fresh.py:1",
            "bug",
            "P3",
            "open",
            "面=流程;來源=代理;回報者=研究者;外部衍生=是;src=cc-note",
        ]
        src = (
            json.dumps(
                {
                    "schema_rev": 1,
                    "sources": [
                        {
                            "id": "cc-note",
                            "url": "https://example.com/a.md",
                            "kind": "docs",
                            "extract": "讀",
                            "added_by": "T1",
                        }
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        repo = fx.make_p1_repo(fx.new_dir("er"), extra_obs=[row], sources=src)
        run = self.open_run(repo)
        snap0 = fx.snap(repo)
        md = fx.memory_dir(fx.new_dir("mem"))
        for cls in ("M", "P", "R", "D", "evaluator-change", "loop-self"):
            over = dict(sources=[obs_id(10)])
            if cls in ("evaluator-change", "loop-self"):
                over["handoff"] = "T1"
            if cls == "M":
                over.update(memory_dir=md, body=body_md("M", source_obs=obs_id(10)))
            self.rej(repo, run, {"NO-INTERNAL-SOURCE"}, cls, cls, **over)
        self.rej(repo, run, {"NO-INTERNAL-SOURCE"}, "D", "外部衍生", sources=[obs_id(11)])
        ox, dx = obs_id(900 + 4), fx.def_id(900)
        self.rej(
            repo, run, {"SOURCE-UNRESOLVED", "NO-INTERNAL-SOURCE"}, "D", "全查無", sources=[ox, dx]
        )
        self.rej(repo, run, {"SOURCE-UNRESOLVED"}, "D", "一個查無", sources=[obs_id(1), ox])
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_107_1_1_guard_surface_is_handed_off_whole(self):
        repo = fx.p1_base()
        for _ in range(4):
            self.open_run(repo)
        fx.commit_all(repo, "runs")
        snap0 = fx.snap(repo)
        ids = []
        for i, ch in enumerate(("DEF", "R", "T1", "PRD"), start=1):
            low = ch.lower()
            guard = f".claude/hooks/new_guard_{low}.py"
            patch = fx.patch_join(
                fx.patch_add(guard, ["x = 1"]),
                fx.patch_add(f"docs/notes/clean_{low}.md", ["clean"]),
            )
            self.ok(repo, rid(i), "P", action="add", target=[guard], handoff=ch, patch=patch)
            ids.append(pid(123 + i))
        events = props_of(repo)
        self.assertEqual(
            [e["route"] for e in events], ["handoff:DEF", "handoff:R", "handoff:T1", "handoff:PRD"]
        )
        self.assertEqual([e["touched_count"] for e in events], [2, 2, 2, 2])
        for p in ids:
            lines = self.card(repo, p)
            self.assertTrue(lines[0].endswith("｜僅轉交，本迴圈不套用"))
            self.assertIn("決定：轉交 ／ 不轉交＋一句理由", lines)
        files1, _ = fx.snap(repo)
        changed = {k for k in files1 if k not in snap0[0] or files1[k] != snap0[0][k]}
        self.assertTrue(all(k == EVL or k.startswith(PROPS_REL + "/") for k in changed), changed)
        self.assertFalse(list((repo / ".claude").rglob("*")) if (repo / ".claude").exists() else [])
        self.assertFalse(list((repo / "docs/notes").glob("clean_*.md")))

    def test_AT_107_1_E_1_route_and_channel_rules(self):
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        base = good_prop_args(repo, "P")
        self.usage_error(*self.M(repo, "prop-new", "--run", run, *base, "--route", "loop"))
        self.usage_error(*self.M(repo, "prop-new", "--run", run, *base, "--handoff", "X"))
        guard = fx.patch_add(".claude/hooks/new_guard_x.py", ["x"])
        self.assertIn(
            "HANDOFF-CHANNEL-MISSING",
            fx.codes_of(
                self.rej(
                    repo,
                    run,
                    {"HANDOFF-CHANNEL-MISSING"},
                    "P",
                    "守衛面缺通道",
                    action="add",
                    target=[".claude/hooks/new_guard_x.py"],
                    patch=guard,
                )
            ),
        )
        self.rej(repo, run, {"HANDOFF-CHANNEL-MISSING"}, "evaluator-change", "評估器缺通道")
        self.rej(repo, run, {"HANDOFF-CHANNEL-UNEXPECTED"}, "P", "乾淨卻給通道", handoff="T1")
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_107_3_1_touched_derivation(self):
        mod = fx.patch_mod
        cases = {
            "T01": (
                mod("docs/notes/demo.md", {1: "a", 2: "b"}),
                "docs/notes/demo.md",
                ["docs/notes/demo.md"],
            ),
            "T02": (
                fx.patch_add("docs/notes/new_a.md", ["x"]),
                "docs/notes/new_a.md",
                ["docs/notes/new_a.md"],
            ),
            "T03": (
                fx.patch_join(
                    fx.patch_del("docs/notes/tiny.md"), mod("docs/notes/demo.md", {1: "a"})
                ),
                "docs/notes/demo.md",
                ["docs/notes/demo.md", "docs/notes/tiny.md"],
            ),
            "T04": (
                fx.patch_rename("docs/notes/other.md", "docs/notes/renamed.md"),
                "docs/notes/renamed.md",
                ["docs/notes/other.md", "docs/notes/renamed.md"],
            ),
            "T05": (
                fx.patch_rename("docs/notes/f1.md", "docs/notes/f1_moved.md", {1: "z"}),
                "docs/notes/f1_moved.md",
                ["docs/notes/f1.md", "docs/notes/f1_moved.md"],
            ),
            "T06": (
                fx.patch_copy("docs/notes/f2.md", "docs/notes/f2_copy.md"),
                "docs/notes/f2_copy.md",
                ["docs/notes/f2.md", "docs/notes/f2_copy.md"],
            ),
            "T07": (
                fx.patch_add("docs/notes/dir with space/a b.md", ["x"], quote=True),
                "docs/notes/dir with space/a b.md",
                ["docs/notes/dir with space/a b.md"],
            ),
            "T08": (
                fx.patch_add("docs/notes/日本.md", ["x"], quote=True),
                "docs/notes/日本.md",
                ["docs/notes/日本.md"],
            ),
            "T09": (
                mod("docs/notes/f3.md", {1: "a"}, tab_suffix="2026-10-20 10:00:00.000000000"),
                "docs/notes/f3.md",
                ["docs/notes/f3.md"],
            ),
        }
        hashes = {}
        for key, (patch, target, expected) in cases.items():
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, "D", action="modify", target=[target], patch=patch)
            e = props_of(repo)[0]
            self.assertEqual((e["route"], e["touched_count"]), ("loop", len(expected)), key)
            blob = json.dumps(expected, ensure_ascii=False, separators=(",", ":")).encode()
            self.assertEqual(e["touched_sha256"], "sha256:" + hashlib.sha256(blob).hexdigest(), key)
            self.assertEqual((repo / PROPS_REL / e["id"] / "r1.patch").read_bytes(), patch, key)
        f4 = fx.fixture_files()["docs/notes/f4.md"]
        two_hunks = fx.patch_diff(
            "docs/notes/f4.md", f4, f4.replace("line 05", "x5").replace("line 40", "x40")
        )
        block5 = mod("docs/notes/f5.md", {1: "a"})
        for key, patch in (
            ("T10a", fx.patch_join(two_hunks, block5)),
            ("T10b", fx.patch_join(block5, two_hunks)),
        ):
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, "D", action="modify", target=["docs/notes/f4.md"], patch=patch)
            hashes[key] = props_of(repo)[0]["touched_sha256"]
        self.assertEqual(hashes["T10a"], hashes["T10b"])

    def test_AT_107_3_E_1_non_evolvable_paths_hand_off(self):
        hits = {
            "H01": "CLAUDE.md",
            "H02": "AutoClaude/CLAUDE.md",
            "H03": ".claude/hooks/new_guard_a.py",
            "H04": "AutoClaude/.claude/hooks/new_guard_b.py",
            "H05": f"AISDLC_SDD/{VNEW}/.claude/hooks/new_guard_c.py",
            "H06": "tools/guard.py",
            "H07": f"AISDLC_SDD/{fx.VOLD}/agent/a.md",
            "H08": f"AISDLC_SDD/{VNEW}/docs_template/t.md",
            "H09": "docs/06_quality/SelfImproving_Event_Ledger.jsonl",
            "H10": "docs/06_quality/SelfImproving_Proposals/PROP-SI-001/r1.md",
            "H11": "docs/06_quality/SelfImproving_Observation_Ledger.md",
            "H12": "docs/05_development/SelfImproving_Operations_SOP.md",
            "H13": "docs/01_requirements/SelfImproving_PRD.md",
            "H14a": "claude.md",
            "H14b": "AutoClaude/Claude.MD",
        }
        for key, path in hits.items():
            repo, run = self.fresh_run_repo()
            patch = fx.patch_join(
                fx.patch_add(path, ["x"]), fx.patch_add("docs/notes/clean_x.md", ["clean"])
            )
            self.ok(
                repo,
                run,
                "D",
                action="add",
                target=["docs/notes/clean_x.md"],
                handoff="T1",
                patch=patch,
            )
            e = props_of(repo)[0]
            self.assertEqual((e["route"], e["touched_count"]), ("handoff:T1", 2), key)
        repo, run = self.fresh_run_repo()
        self.ok(
            repo,
            run,
            "D",
            action="add",
            target=["docs/notes/c.md"],
            handoff="T1",
            patch=fx.patch_rename("CLAUDE.md", "docs/notes/c.md"),
        )
        e = props_of(repo)[0]
        self.assertEqual((e["route"], e["touched_count"]), ("handoff:T1", 2), "H15")
        repo, run = self.fresh_run_repo()
        self.ok(
            repo,
            run,
            "D",
            action="add",
            target=["docs/notes/clean_c.md"],
            patch=fx.patch_add("docs/notes/clean_c.md", ["clean"]),
        )
        self.assertEqual(props_of(repo)[0]["route"], "loop")

    def test_AT_107_3_E_2_alias_forms_and_numstat_superset(self):
        drive = "X" + ":/x.md"
        cases = {
            "A01": "docs/notes/../../outside.md",
            "A02": "/etc/x.md",
            "A03": drive,
            "A04": "docs/notes/f.md::$DATA",
            "A05": "docs/notes/demo.md.",
            "A06": "docs/notes/demo.md ",
            "A07": "docs/notes/nul.md",
            "A08": "docs/aux/x.md",
            "A09": "docs/notes/COM1.txt",
            "A10": "docs/n\x01.md",
            "A11": "docs\\..\\CLAUDE.md",
        }
        for key, path in cases.items():
            repo, run = self.fresh_run_repo()
            patch = fx.patch_join(
                fx.patch_add(path, ["x"], quote=key in ("A06", "A10")),
                fx.patch_add("docs/notes/clean_x.md", ["clean"]),
            )
            self.ok(
                repo,
                run,
                "D",
                action="add",
                target=["docs/notes/clean_x.md"],
                handoff="T1",
                patch=patch,
            )
            e = props_of(repo)[0]
            self.assertEqual((e["route"], e["touched_count"]), ("handoff:T1", 2), key)
        repo, run = self.fresh_run_repo()
        clean = fx.patch_add("docs/notes/clean_y.md", ["clean"])
        snap0 = fx.snap(repo)
        with mock.patch.object(
            si_git,
            "apply_numstat",
            return_value=["docs/notes/clean_y.md", "docs/notes/unlisted.md"],
        ):
            self.rej(
                repo,
                run,
                {"PATCH-PATH-MISMATCH"},
                "D",
                "git 看見而解析器漏掉",
                action="add",
                target=["docs/notes/clean_y.md"],
                patch=clean,
            )
        self.assertEqual(fx.snap(repo), snap0)
        self.ok(repo, run, "D", action="add", target=["docs/notes/clean_y.md"], patch=clean)
        for target in ("../x.md", "docs/../x.md", "/abs/x.md", drive):
            self.usage_error(
                *self.M(
                    repo, "prop-new", "--run", run, *good_prop_args(repo, "D", target=[target])
                ),
                msg=target,
            )

    def test_AT_107_3_E_4_numstat_failure_is_patch_parse(self):
        """受測 `tools/lib/selfimproving/writeverbs.py`：git 解析不了的 patch 一律 PATCH-PARSE。"""
        broken = "\n".join(
            [
                "diff --git a/docs/notes/demo.md b/docs/notes/demo.md",
                "--- a/docs/notes/demo.md",
                "+++ b/docs/notes/demo.md",
                "@@ -3,5 +3,5 @@",
                "-line 003",
                "+line 003 changed",
                "",
            ]
        ).encode()
        context = "\n".join(
            [
                "*** a/docs/notes/demo.md",
                "--- b/docs/notes/demo.md",
                "***************",
                "*** 3 ****",
                "! line 003",
                "--- 3 ----",
                "! line 003 changed",
                "",
            ]
        ).encode()
        for label, patch, fake in (
            ("損毀 hunk", broken, None),
            ("context-diff", context, None),
            ("numstat 拋錯", None, OSError("x")),
        ):
            repo, run = self.fresh_run_repo()
            snap0 = fx.snap(repo)
            over = {"patch": patch} if patch is not None else {}
            if fake is not None:
                with mock.patch.object(si_git, "apply_numstat", side_effect=fake):
                    rc, out, _ = self.new(repo, run, "D", **over)
            else:
                rc, out, _ = self.new(repo, run, "D", **over)
            self.rejected(rc, out, {"PATCH-PARSE"}, label)
            self.draft_ok(repo, out, label)
            self.assertEqual(fx.snap(repo), snap0, label)
        repo, run = self.fresh_run_repo()
        n0 = len(fx.EV(repo))
        self.ok(repo, run, "D")
        self.assertEqual(len(fx.EV(repo)), n0 + 1)

    def test_AT_107_3_E_5_diff_git_a_side_enters_the_touched_union(self):
        """受測 `tools/lib/selfimproving/paths.py`：`diff --git` 標頭 A 側路徑即使 ---／+++ 只列
        B 側也入 touched 聯集並據以導出 route（R51 (a)）。"""
        orig = fx.patch_mod("docs/notes/demo.md", {3: "改過三", 4: "改過四"})
        first, _, rest = orig.partition(b"\n")
        self.assertEqual(first, b"diff --git a/docs/notes/demo.md b/docs/notes/demo.md")
        forged = b"diff --git a/CLAUDE.md b/docs/notes/demo.md\n" + rest
        repo, run = self.fresh_run_repo()
        self.ok(repo, run, "D", target=["docs/notes/demo.md"], handoff="T1", patch=forged)
        e = props_of(repo)[0]
        paths = ["CLAUDE.md", "docs/notes/demo.md"]
        blob = json.dumps(paths, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.assertEqual((e["route"], e["touched_count"]), ("handoff:T1", 2))
        self.assertEqual(e["touched_sha256"], "sha256:" + hashlib.sha256(blob).hexdigest())
        repo, run = self.fresh_run_repo()
        self.ok(repo, run, "D", target=["docs/notes/demo.md"], patch=orig)
        e = props_of(repo)[0]
        self.assertEqual((e["route"], e["touched_count"]), ("loop", 1))

    def memory_variants(self):
        md = fx.memory_dir(fx.new_dir("mem"))
        old = (md / "demo.md").read_text(encoding="utf-8")
        return md, old, ("memory/demo.md", "Memory/demo.md", "MEMORY/demo.md")

    def test_AT_107_3_E_6_memory_root_prefix_is_casefolded(self):
        """受測 `tools/lib/selfimproving/props.py`：M 類合法根的 `memory/` 前綴比對經 casefold。"""
        md, old, paths = self.memory_variants()
        pre = {}
        for path in paths:
            repo, run = self.fresh_run_repo()
            patch = fx.patch_mod(path, {3: "改過三", 4: "改過四"}, old=old)
            self.ok(repo, run, "M", memory_dir=md, target=[path], patch=patch,
                    body=body_md("M", scope="memory 索引"))  # fmt: skip
            e = props_of(repo)[0]
            self.assertEqual((e["cls"], e["route"], e["touched_count"]), ("M", "loop", 1), path)
            self.assertEqual(e["target"], [path], path)
            self.assertEqual(set(e["preimage"]), {path}, path)
            pre[path] = e["preimage"][path]
        self.assertEqual(len(set(pre.values())), 1)

    def test_AT_107_3_E_7_memory_case_variants_obey_touch_ratio(self):
        """受測 `tools/lib/selfimproving/writeverbs.py`：M 類大小寫變體不得因找不到 base 內容而
        繞過 TOUCH-RATIO（`_mem_text` 的前綴比對須 casefold）。"""
        md, old, paths = self.memory_variants()
        edits = {n: f"不同的第 {n} 行" for n in range(1, 16)}
        for path in paths:
            repo, run = self.fresh_run_repo()
            snap0 = fx.snap(repo)
            patch = fx.patch_mod(path, edits, old=old)
            out = self.rej(repo, run, {"TOUCH-RATIO"}, "M", path, memory_dir=md, target=[path],
                           patch=patch, body=body_md("M", scope="memory 索引"))  # fmt: skip
            self.assertIn("0.750", out, path)
            self.assertEqual(fx.snap(repo), snap0, path)

    def test_AT_107_3_E_3_conditions_and_markers(self):
        def rule(n):
            return f"AISDLC_SDD/{VNEW}/governance/rules/R-9.{n}.yaml"

        def insert(path, repo):
            return fx.patch_insert(path, 1, ["extra: 1"], old=fx.read(repo, path))

        def route(setup=None, cls="D", action="modify", build=None, handoff=None, target=None):
            repo, run = self.fresh_run_repo()
            if setup:
                setup(repo)
            patch, tgt = build(repo)
            over = dict(action=action, target=target or [tgt], patch=patch)
            if handoff:
                over["handoff"] = handoff
            self.ok(repo, run, cls, **over)
            return props_of(repo)[0]

        for n, expect in ((1, "handoff:T1"), (3, "handoff:T1"), (2, "loop")):
            e = route(
                build=lambda r, n=n: (insert(rule(n), r), rule(n)),
                handoff="T1" if expect != "loop" else None,
            )
            self.assertEqual(e["route"], expect, f"R-9.{n}")
        e = route(
            cls="R",
            action="add",
            build=lambda r: (
                fx.patch_add(rule(9), ["id: R-9.9", "trust_level: proposed"]),
                rule(9),
            ),
        )
        self.assertEqual(e["route"], "loop")
        new_x = f"AISDLC_SDD/{VNEW}/agent/x.md"
        old_x = f"AISDLC_SDD/{fx.VOLD}/agent/x.md"
        e = route(action="add", build=lambda r: (fx.patch_add(new_x, ["x"]), new_x))
        self.assertEqual(e["route"], "loop")
        e = route(action="add", handoff="T1", build=lambda r: (fx.patch_add(old_x, ["x"]), old_x))
        self.assertEqual(e["route"], "handoff:T1")
        e = route(
            setup=lambda r: (r / "AISDLC_SDD/scripts/sdd_version.py").unlink(),
            action="add",
            handoff="T1",
            build=lambda r: (fx.patch_add(new_x, ["x"]), new_x),
        )
        self.assertEqual(e["route"], "handoff:T1")
        some = "docs/01_requirements/Some.md"
        e = route(action="add", handoff="T1", build=lambda r: (fx.patch_add(some, ["x"]), some))
        self.assertEqual(e["route"], "handoff:T1")
        spec = "docs/01_requirements/SPEC-PATCH-demo.md"
        e = route(action="add", build=lambda r: (fx.patch_add(spec, ["x"]), spec))
        self.assertEqual(e["route"], "loop")
        for label, kw in (
            ("P", dict(cls="P")),
            ("second", dict(second=True)),
            ("modify", dict(action="modify")),
        ):
            second = kw.pop("second", False)

            def build(r, second=second):
                patch = fx.patch_add(spec, ["x"])
                if second:
                    patch = fx.patch_join(patch, fx.patch_add("docs/notes/clean_s.md", ["c"]))
                return patch, spec

            e = route(
                action=kw.get("action", "add"), cls=kw.get("cls", "D"), handoff="T1", build=build
            )
            self.assertEqual(e["route"], "handoff:T1", label)
        params = "docs/06_quality/SelfImproving_Protocol/params.json"
        lib_new = "tools/lib/selfimproving/x.py"
        for patch_fn, want, cls in (
            (lambda r: (insert(params, r), params), "evaluator-change", "P"),
            (lambda r: (fx.patch_add(lib_new, ["x"]), lib_new), "loop-self", "P"),
            (
                lambda r: (fx.patch_join(insert(params, r), fx.patch_add(lib_new, ["x"])), params),
                "evaluator-change",
                "P",
            ),
            (
                lambda r: (fx.patch_add("docs/notes/clean_z.md", ["c"]), "docs/notes/clean_z.md"),
                "loop-self",
                "loop-self",
            ),
        ):
            e = route(
                cls=cls,
                action="add" if want == "loop-self" else "modify",
                handoff="T1",
                build=patch_fn,
            )
            self.assertEqual((e["cls"], e["route"]), (want, "handoff:T1"))
        md = fx.memory_dir(fx.new_dir("mem"))
        repo, run = self.fresh_run_repo()
        self.ok(repo, run, "M", memory_dir=md)
        self.assertEqual(props_of(repo)[0]["route"], "loop")
        repo, run = self.fresh_run_repo()
        self.ok(
            repo,
            run,
            "M",
            memory_dir=md,
            handoff="T1",
            target=["memory/demo.md"],
            patch=fx.patch_mod("docs/notes/demo.md", {3: "x"}),
        )
        self.assertEqual(props_of(repo)[0]["route"], "handoff:T1")


class TestProposalLifecycle(PropCase):
    def test_AT_108_1_1_prop_new_registers_proposed(self):
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        self.ok(repo, run, "R")
        self.ok(repo, run, "P")
        events = props_of(repo)
        want = {
            "seq",
            "t",
            "kind",
            "by",
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
        }
        self.assertTrue(all(set(e) == want for e in events))
        self.assertEqual([(e["id"], e["rev"]) for e in events], [(pid(124), 1), (pid(125), 1)])
        status = self.MJ(repo, "status")
        self.assertEqual(
            [(p["id"], p["state"]) for p in status["pending_props"]],
            [(pid(124), "proposed"), (pid(125), "proposed")],
        )
        self.assertEqual(events[0]["target"], [f"AISDLC_SDD/{VNEW}/governance/rules/R-9.9.yaml"])
        files1, _ = fx.snap(repo)
        changed = {k for k in files1 if files1[k] != snap0[0].get(k)}
        self.assertTrue(all(k == EVL or k.startswith(PROPS_REL + "/") for k in changed), changed)
        self.assertFalse((repo / f"AISDLC_SDD/{VNEW}/governance/rules/R-9.9.yaml").exists())

    def test_AT_108_1_E_1_stage_one_inputs(self):
        repo, run = self.fresh_run_repo()
        snap0, rx = fx.snap(repo), rid(900 + 6)
        tmp = fx.new_dir("in")
        tmp.mkdir()
        full = good_prop_args(repo, "P")

        def drop(flag):
            out, i = [], 0
            while i < len(full):
                if full[i] == flag:
                    i += 2
                    continue
                out.append(full[i])
                i += 1
            return out

        for flag in ("--patch-file", "--body-file", "--proposer", "--source"):
            self.usage_error(*self.M(repo, "prop-new", "--run", run, *drop(flag)), msg=flag)
        self.usage_error(
            *self.M(repo, "prop-new", "--run", run, *good_prop_args(repo, "P"), "--cls", "Z"),
            msg="--cls Z",
        )
        header = b'diff --git "a/docs/\\xyz" "b/docs/\\xyz"\n--- a/x\n+++ b/x\n'
        cases = [
            (b"", "PATCH-EMPTY"),
            (b"GIT binary patch\nliteral 3\nabc\n", "PATCH-BINARY"),
            (b"this is not a patch\n", "PATCH-PARSE"),
            (header, "PATCH-PARSE"),
            (b'diff --git "a/docs/\\377.md" "b/docs/\\377.md"\n--- a/x\n+++ b/x\n', "PATCH-PARSE"),
        ]
        for patch, code in cases:
            self.rej(repo, rx, {code}, "P", code, patch=patch)
        self.rej(
            repo,
            rx,
            {"BODY-SKELETON"},
            "P",
            "BODY-SKELETON",
            body=body_md("P", skeleton_drop=["影響面"]),
        )
        out = self.rej(
            repo,
            run,
            {"REVIEWER-IS-PROPOSER"},
            "P",
            "審查者等於提案者",
            reviewer="SA",
            proposer="SA",
        )
        self.assertIn("REVIEWER-IS-PROPOSER", fx.codes_of(out))
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_108_2_1_revise_returned(self):
        repo, run = self.fresh_run_repo()
        self.ok(repo, run, "P")
        fx.append_events(repo, [fx.dec_ev(124, "return")])
        self.ok(repo, run, "D", target=["docs/notes/demo.md"])
        self.ok(
            repo,
            run,
            "D",
            target=["docs/notes/other.md"],
            patch=fx.patch_mod("docs/notes/other.md", {3: "改過三"}),
        )
        r1 = {p.name: p.read_bytes() for p in (repo / PROPS_REL / pid(124)).iterdir()}
        args = fx.revise_args(
            repo,
            "P",
            patch=fx.patch_mod("playbooks/demo.yaml", {5: "改過五"}),
            body=body_md("P", symptom="修訂後症狀"),
        )
        rc, out, err = self.M(repo, "prop-revise", "--run", run, "--prop", pid(124), *args)
        self.assertEqual(rc, 0, out + err)
        self.assertRegex(
            out,
            rf"^ok prop seq=\d+ id={pid(124)} rev=2 route=loop cls=P "
            r"digest=[0-9a-f]{8} touched_count=1\n$",
        )
        e1, e2 = [e for e in props_of(repo) if e["id"] == pid(124)]
        self.assertEqual(e2["rev"], 2)
        for key in ("cls", "action", "target", "sources"):
            self.assertEqual(e1[key], e2[key], key)
        folder = repo / PROPS_REL / pid(124)
        self.assertTrue((folder / "r2.patch").is_file() and (folder / "r2.md").is_file())
        self.assertEqual({n: (folder / n).read_bytes() for n in r1}, r1)
        pending = {p["id"]: p for p in self.MJ(repo, "status")["pending_props"]}
        self.assertEqual((pending[pid(124)]["state"], pending[pid(124)]["rev"]), ("proposed", 2))

    def test_AT_108_2_E_1_revise_rejections(self):
        repo = fx.p1_base()
        fx.write_events(repo, fx.sc_rev(), commit=True)
        snap0, px = fx.snap(repo), pid(900 + 8)
        args = fx.revise_args(repo, "P")
        for n in (124, 125, 126, 127):
            rc, out, _ = self.M(repo, "prop-revise", "--run", rid(1), "--prop", pid(n), *args)
            self.rejected(rc, out)
            self.assertIn("TRANSITION-ILLEGAL", fx.codes_of(out), n)
            self.draft_ok(repo, out, str(n))
        rc, out, _ = self.M(repo, "prop-revise", "--run", rid(1), "--prop", pid(128), *args)
        self.rejected(rc, out)
        self.assertIn("REV-LIMIT", fx.codes_of(out))
        self.draft_ok(repo, out)
        rc, out, _ = self.M(repo, "prop-revise", "--run", rid(1), "--prop", px, *args)
        self.rejected(rc, out, {"PROP-NOT-FOUND"})
        self.draft_ok(repo, out)
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_108_3_1_rule_candidate_accepted(self):
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        target = f"AISDLC_SDD/{VNEW}/governance/rules/R-9.9.yaml"
        self.ok(
            repo,
            run,
            "R",
            action="add",
            target=[target],
            patch=fx.patch_add(target, ["id: R-9.9", "trust_level: proposed"]),
        )
        e = props_of(repo)[0]
        self.assertEqual((e["cls"], e["route"]), ("R", "loop"))
        files1, _ = fx.snap(repo)
        changed = {k for k in files1 if files1[k] != snap0[0].get(k)}
        self.assertTrue(all(k == EVL or k.startswith(PROPS_REL + "/") for k in changed), changed)
        self.assertFalse((repo / target).exists())
        self.assertFalse([p for p in repo.rglob("*") if "FSM-STATE" in p.name.upper()])

    def test_AT_108_3_E_1_rule_candidate_rejected_or_handed_off(self):
        target = f"AISDLC_SDD/{VNEW}/governance/rules/R-9.9.yaml"
        for lines in (["id: R-9.9", "name: x"], ["id: R-9.9", "trust_level: active"]):
            repo, run = self.fresh_run_repo()
            snap0 = fx.snap(repo)
            self.rej(
                repo,
                run,
                {"R-NOT-PROPOSED"},
                "R",
                str(lines),
                action="add",
                target=[target],
                patch=fx.patch_add(target, lines),
            )
            self.assertEqual(fx.snap(repo), snap0)
        repo, run = self.fresh_run_repo()
        r91 = f"AISDLC_SDD/{VNEW}/governance/rules/R-9.1.yaml"
        self.ok(
            repo,
            run,
            "R",
            action="modify",
            target=[r91],
            handoff="R",
            patch=fx.patch_insert(r91, 1, ["extra: 1"], old=fx.read(repo, r91)),
        )
        self.assertEqual(props_of(repo)[0]["route"], "handoff:R")


class TestBodyAndDelta(PropCase):
    """受測：`tools/lib/selfimproving/props.py`（提案本文形狀與差分）。"""

    def test_AT_109_1_1_body_shapes_accepted(self):
        def custom(label):
            fields = body_md("P", retire_when="r", reopen_symptom="s", verify_plan="v")
            heads = fields.split("\n## ")
            heads[0] = heads[0].replace("## ", "", 1)
            ordered = [heads[4], *heads[:4]]
            text = "\n".join(f"## {h}" for h in ordered)
            return text.replace("## 反例證據", "## 一、反例證據（帳本列）")

        bodies = {
            "失敗": body_md("P", result_label="失敗"),
            "成功": body_md("P", result_label="成功"),
            "升級": body_md("P", result_label="升級"),
            "custom": custom("custom"),
        }
        for label, body in bodies.items():
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, "P", body=body)
            e = props_of(repo)[0]
            md = (repo / PROPS_REL / e["id"] / "r1.md").read_bytes()
            self.assertEqual(md, body.replace("\r\n", "\n").encode("utf-8"), label)
            lines = self.card(repo, e["id"])
            self.assertEqual(lines[1], "一、症狀：卡面症狀一句", label)
            self.assertTrue(
                lines[3].startswith("三、風險與回滾：風險一句｜回滾：git revert 該 patch")
            )

    def test_AT_109_1_E_1_body_rejections(self):
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        for head in ("反例證據", "Before", "After", "影響面", "欄位"):
            out = self.rej(
                repo, run, {"BODY-SKELETON"}, "P", head, body=body_md("P", skeleton_drop=[head])
            )
            self.assertIn(head, out)
        for key in ("symptom", "risk", "rollback", "budget", "result_label", "scope"):
            out = self.rej(
                repo, run, {"BODY-FIELD-MISSING"}, "P", key, body=body_md("P", drop=[key])
            )
            self.assertIn(key, out)
            out = self.rej(
                repo, run, {"BODY-FIELD-MISSING"}, "P", key + "空", body=body_md("P", **{key: ""})
            )
            self.assertIn(key, out)
        self.rej(
            repo, run, {"BODY-FIELD-VALUE"}, "P", "maybe", body=body_md("P", result_label="maybe")
        )
        bad = fx.new_dir("bad")
        bad.mkdir()
        (bad / "b.md").write_bytes(b"\xff\xfe\x00bad")
        args = good_prop_args(repo, "P")
        args[args.index("--body-file") + 1] = str(bad / "b.md")
        self.usage_error(*self.M(repo, "prop-new", "--run", run, *args))
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_109_2_1_ratio_and_new_entries(self):
        other = "docs/notes/other.md"
        old = fx.fixture_files()[other]

        def replace(n):
            return fx.patch_mod(other, {i: f"改過{i}" for i in range(1, n + 1)})

        cases = {
            "R1": (replace(10), True, "0.20"),
            "R2": (replace(11), False, None),
            "R3": (
                fx.patch_join(
                    fx.patch_mod(other, {i: f"改{i}" for i in range(1, 7)}),
                    fx.patch_mod("docs/notes/f1.md", {i: f"改{i}" for i in range(1, 6)}),
                ),
                True,
                "0.11",
            ),
            "E1": (fx.patch_insert(other, 50, ["- x"] * 3), True, None),
            "E2": (fx.patch_insert(other, 50, ["- x"] * 4), False, None),
            "E3": (fx.patch_insert(other, 50, ["## h", "1. x", "- y"]), True, None),
            "E4": (fx.patch_insert(other, 50, ["## h", "1. x", "- y", "* z"]), False, None),
            "E5": (fx.patch_insert(other, 50, ["plain"] * 10 + ["- a", "- b", "- c"]), True, None),
            "E6": (
                fx.patch_join(*[fx.patch_add(f"docs/notes/n{i}.md", ["plain"]) for i in range(3)]),
                True,
                None,
            ),
            "E7": (
                fx.patch_join(*[fx.patch_add(f"docs/notes/n{i}.md", ["plain"]) for i in range(4)]),
                False,
                None,
            ),
            "E8": (
                fx.patch_join(
                    fx.patch_add("docs/notes/n1.md", ["plain"]),
                    fx.patch_add("docs/notes/n2.md", ["plain"]),
                    fx.patch_insert(other, 50, ["- a", "- b"]),
                ),
                False,
                None,
            ),
        }
        self.assertTrue(old)
        for key, (patch, accepted, ratio) in cases.items():
            repo, run = self.fresh_run_repo()
            snap0 = fx.snap(repo)
            if accepted:
                self.ok(repo, run, "D", target=[other], patch=patch)
                if ratio:
                    self.assertIn(f"觸及比例 {ratio}；", self.card(repo, pid(124))[2], key)
            else:
                code = "TOUCH-RATIO" if key == "R2" else "NEW-ENTRIES"
                self.rej(repo, run, {code}, "D", key, target=[other], patch=patch)
                self.assertEqual(fx.snap(repo), snap0)

    def test_AT_109_2_E_1_archive_exemption(self):
        def case(**kw):
            repo, run = self.fresh_run_repo()
            md = fx.memory_dir(fx.new_dir("mem"))
            patch = fx.mem_patch_archive(md, kw.pop("k", 40), kw.pop("pointers", 1))
            if kw.pop("tamper", False):  # 歸檔檔上一行與原文差一個字元：不再是逐字搬移
                patch = patch.replace("+- [條目 001]".encode(), "+- [X條目 001]".encode(), 1)
            over = dict(memory_dir=md, target=["memory/MEMORY.md"], patch=patch)
            over.update(kw)
            return repo, run, over

        repo, run, over = case(k=40)
        self.ok(repo, run, "M", **over)
        repo, run, over = case(k=50)
        self.ok(repo, run, "M", **over)
        repo, run, over = case(k=51)
        self.rej(repo, run, {"ARCHIVE-ENTRIES"}, "M", "51", **over)
        repo, run, over = case(k=40, tamper=True)
        rc, out, _ = self.new(repo, run, "M", **over)
        self.rejected(rc, out)
        self.assertIn("TOUCH-RATIO", fx.codes_of(out))
        self.draft_ok(repo, out)
        repo, run, over = case(k=40, pointers=4)
        rc, out, _ = self.new(repo, run, "M", **over)
        self.rejected(rc, out)
        self.assertIn("NEW-ENTRIES", fx.codes_of(out))
        self.draft_ok(repo, out)
        repo, run, over = case(k=40)
        over.pop("memory_dir")
        args = good_prop_args(repo, "M", **{**over, "memory_dir": fx.memory_dir(fx.new_dir("mem"))})
        args = args[:-2]
        rc, out, _ = self.M(repo, "prop-new", "--run", run, *args)
        self.rejected(rc, out, {"MEMORY-DIR-MISSING"})
        self.draft_ok(repo, out)
        plain = fx.new_dir("plain")
        plain.write_bytes(b"x")
        repo, run, over = case(k=40)
        over["memory_dir"] = plain
        rc, out, err = self.new(repo, run, "M", **over)
        self.usage_error(rc, out, err)

    def test_AT_109_3_1_m_fields_and_preimage(self):
        repo, run = self.fresh_run_repo()
        md = fx.memory_dir(fx.new_dir("mem"))
        old = (md / "demo.md").read_text(encoding="utf-8")
        new_text = old.replace("note 03\nnote 04\n", "合併一行\n")
        patch = fx.patch_join(
            fx.patch_diff("memory/demo.md", old, new_text),
            fx.patch_add("memory/new_note.md", ["內容"]),
        )
        self.ok(
            repo,
            run,
            "M",
            memory_dir=md,
            target=["memory/demo.md"],
            patch=patch,
            body=body_md("M", scope="memory 索引"),
        )
        e = props_of(repo)[0]
        self.assertEqual(set(e["preimage"]), {"memory/demo.md", "memory/new_note.md"})
        self.assertEqual(e["preimage"]["memory/demo.md"], fx.sha(b"note 03\nnote 04\n"))
        self.assertEqual(e["preimage"]["memory/new_note.md"], fx.sha(b""))
        self.ok(repo, run, "P")
        self.ok(
            repo,
            run,
            "P",
            target=["docs/notes/other.md"],
            patch=fx.patch_mod("docs/notes/other.md", {3: "改過三"}),
            body=body_md("P"),
        )
        self.assertTrue(all("preimage" not in x for x in props_of(repo)[1:]))

    def test_AT_109_3_E_1_m_field_rejections(self):
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        md = fx.memory_dir(fx.new_dir("mem"))
        for key in ("result_label", "scope", "source_obs", "retire_when"):
            for label, body in (
                ("缺", body_md("M", drop=[key])),
                ("空", body_md("M", **{key: ""})),
            ):
                out = self.rej(
                    repo, run, {"M-FIELD-MISSING"}, "M", key + label, memory_dir=md, body=body
                )
                self.assertIn(key, out)
        for value in (obs_id(3), "foo", f"{obs_id(1)}、{obs_id(3)}"):
            self.rej(
                repo,
                run,
                {"M-FIELD-MISSING"},
                "M",
                value,
                memory_dir=md,
                sources=[obs_id(1)],
                body=body_md("M", source_obs=value),
            )
        self.rej(
            repo,
            run,
            {"BODY-FIELD-VALUE"},
            "M",
            "maybe",
            memory_dir=md,
            body=body_md("M", result_label="maybe"),
        )
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_110_1_1_budget_and_duplicates(self):
        repo = fx.p1_base()
        self.open_run(repo)
        self.open_run(repo)
        plan = [
            ("P", {}),
            ("D", {}),
            (
                "D",
                dict(
                    target=["docs/notes/other.md"],
                    patch=fx.patch_mod("docs/notes/other.md", {3: "x"}),
                ),
            ),
        ]
        for cls, over in plan:
            self.ok(repo, rid(1), cls, **over)
        f1 = dict(target=["docs/notes/f1.md"], patch=fx.patch_mod("docs/notes/f1.md", {3: "x"}))
        self.rej(repo, rid(1), {"BUDGET-PROPOSALS"}, "D", "第 4 個", **f1)
        self.ok(repo, rid(2), "D", **f1)

        def dup_repo():
            r, run = self.fresh_run_repo()
            fx.set_params(r, max_proposals_per_run=99)
            return r, run

        f2 = dict(
            target=["docs/notes/f2.md"],
            patch=fx.patch_mod("docs/notes/f2.md", {3: "x"}),
            sources=[obs_id(1)],
        )
        r, run = dup_repo()
        self.ok(r, run, "D", **f2)
        self.rej(r, run, {"DUPLICATE-TYPE"}, "D", "a", **f2)
        r, run = dup_repo()
        self.ok(r, run, "D", **f2)
        fx.append_events(r, [fx.dec_ev(124, "reject"), fx.dec_ev(124, "unblock")])
        # P2 R82：被否決（含已解除）的同型再提案須附 reject_response；已解除才不被冷卻擋
        reply = fx.body_md("P", reject_response="已逐項回應否決理由")
        self.ok(r, run, "D", **{**f2, "body": reply})
        r, run = dup_repo()
        self.ok(r, run, "D", **f2)
        self.ok(
            r,
            run,
            "D",
            **{
                **f2,
                "target": ["docs/notes/f3.md"],
                "patch": fx.patch_mod("docs/notes/f3.md", {3: "x"}),
            },
        )
        r, run = dup_repo()
        self.cli_ok(r, *attr_args(obs_id(1), "tools/a-b"))
        self.cli_ok(r, *attr_args(obs_id(3), "tools/c-d"))
        self.ok(r, run, "D", **f2)
        self.ok(r, run, "D", **{**f2, "sources": [obs_id(3)]})
        r, run = dup_repo()
        self.cli_ok(r, *attr_args(obs_id(1), "tools/a-b"))
        self.ok(r, run, "D", **f2)
        self.ok(r, run, "D", **{**f2, "sources": [obs_id(3)]})
        self.rej(r, run, {"DUPLICATE-TYPE"}, "D", "f", **{**f2, "sources": [obs_id(4)]})

    def test_AT_110_1_E_1_state_rejections(self):
        def repo_with(events):
            r = fx.p1_base()
            fx.write_events(r, events, commit=True)
            return r

        r = repo_with([fx.run_open_ev(1), ev("run.close", run=rid(1), no_event=True)])
        rc, out, _ = self.new(r, rid(1), "P")
        self.rejected(rc, out)
        self.assertIn("RUN-NOT-OPEN", fx.codes_of(out))
        r = repo_with(
            [fx.run_open_ev(1), ev("run.close", run=rid(1), no_event=True), fx.run_open_ev(2)]
        )
        self.rej(r, rid(2), {"RESEARCH-MISSING"}, "P", "無研究事件")
        r = repo_with(fx.sc_susp())
        self.rej(r, rid(3), {"SUSPENDED"}, "P", "SUSPENDED")
        rc, out, _ = self.new(r, rid(900 + 5), "P")
        self.assertEqual(fx.codes_of(out), {"RUN-NOT-OPEN", "RESEARCH-MISSING", "SUSPENDED"})
        fx.append_events(r, [ev("dec", "掌舵者", dkind="resume", run=rid(1))])
        self.ok(r, rid(3), "P")

    def test_AT_110_2_1_budget_declared_on_card(self):
        repo, run = self.fresh_run_repo()
        self.ok(repo, run, "P", body=body_md("P", budget="1 次子代理、約 3000 token"))
        self.assertIn("預算宣告：1 次子代理、約 3000 token", self.card(repo, pid(124))[6])

    def test_AT_110_2_E_1_budget_required(self):
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        for body in (body_md("P", drop=["budget"]), body_md("P", budget="")):
            out = self.rej(repo, run, {"BODY-FIELD-MISSING"}, "P", "budget", body=body)
            self.assertIn("budget", out)
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_111_1_1_classes_and_group_marks(self):
        md = fx.memory_dir(fx.new_dir("mem"))
        for cls in ("M", "P", "R", "D"):
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, cls, memory_dir=md) if cls == "M" else self.ok(repo, run, cls)
            e = props_of(repo)[0]
            self.assertEqual((e["cls"], e["route"]), (cls, "loop"))
        repo, run = self.fresh_run_repo()
        patch = fx.patch_join(
            fx.patch_del("docs/notes/tiny.md"), fx.patch_mod("docs/notes/demo.md", {1: "x"})
        )
        f3.promoted(repo, target="docs/notes/tiny.md")  # R127 (c)：退役目標須在役
        self.ok(repo, run, "D", action="retire", target=["docs/notes/tiny.md"], patch=patch)
        e = props_of(repo)[-1]
        self.assertEqual((e["cls"], e["action"], e["route"]), ("D", "retire", "loop"))
        params = "docs/06_quality/SelfImproving_Protocol/params.json"
        for moved, want in ((False, "evaluator-change"), (True, "loop-self")):
            repo, run = self.fresh_run_repo()
            if moved:
                prd = fx.read(repo, "docs/01_requirements/SelfImproving_PRD.md")
                prd = prd.replace("(iii) `docs/06_quality/SelfImproving_Protocol/**`、", "(iii) ")
                prd = prd.replace(
                    "(iv) `docs/01_requirements/SelfImproving_PRD.md`",
                    "(iv) `docs/06_quality/SelfImproving_Protocol/**`、"
                    "`docs/01_requirements/SelfImproving_PRD.md`",
                )
                fx.put(repo, "docs/01_requirements/SelfImproving_PRD.md", prd)
            self.ok(
                repo,
                run,
                "P",
                handoff="T1",
                target=[params],
                patch=fx.patch_insert(params, 1, ["extra: 1"], old=fx.read(repo, params)),
            )
            e = props_of(repo)[0]
            self.assertEqual((e["cls"], e["route"]), (want, "handoff:T1"))

    def test_AT_111_1_E_1_evaluator_and_loop_self(self):
        for cls in ("evaluator-change", "loop-self"):
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, cls, handoff="T1")
            e = props_of(repo)[0]
            self.assertEqual((e["cls"], e["route"]), (cls, "handoff:T1"))
        params = "docs/06_quality/SelfImproving_Protocol/params.json"
        tools = "tools/selfimproving.py"
        for cls, parts, want in (
            ("P", [params], "evaluator-change"),
            ("P", [tools], "loop-self"),
            ("D", [params, tools], "evaluator-change"),
        ):
            repo, run = self.fresh_run_repo()
            patch = fx.patch_join(
                *[
                    fx.patch_add(p, ["x"])
                    if p == tools
                    else fx.patch_insert(p, 1, ["extra: 1"], old=fx.read(repo, p))
                    for p in parts
                ]
            )
            self.ok(repo, run, cls, handoff="T1", target=[parts[0]], patch=patch, action="modify")
            self.assertEqual(props_of(repo)[0]["cls"], want)
        repo, run = self.fresh_run_repo()
        for cls in ("Z", "m"):
            args = good_prop_args(repo, "P")
            args[args.index("--cls") + 1] = cls
            self.usage_error(*self.M(repo, "prop-new", "--run", run, *args), msg=cls)


def attr_args(obs, cause):
    """`attr` 的 CLI 引數（`tools/lib/selfimproving/writeverbs.py`）。"""
    return [
        "attr",
        "--type",
        "root",
        "--by",
        "SA",
        "--obs",
        obs,
        "--item",
        "DOC=docs/06_quality/",
        "--root-cause",
        cause,
    ]


class TestCard(PropCase):
    def make(self, cls="P", **over):
        repo, run = self.fresh_run_repo()
        self.ok(repo, run, cls, **over)
        return repo, run

    def test_AT_114_1_1_card_format(self):
        repo, run = self.make("P", sources=[obs_id(1), obs_id(2)])
        guard = ".claude/hooks/new_guard_d.py"
        self.ok(
            repo,
            run,
            "P",
            action="add",
            target=[guard],
            handoff="DEF",
            patch=fx.patch_add(guard, ["x = 1"]),
            sources=[obs_id(3)],
        )
        e = props_of(repo)[0]
        d8 = e["digest"].split(":")[1][:8]
        rc, out1, _ = self.M(repo, "card", pid(124))
        rc2, out2, _ = self.M(repo, "card", pid(124))
        self.assertEqual((rc, rc2, out1), (0, 0, out2))
        lines = out1.split("\n")
        self.assertTrue(out1.endswith("\n") and len(lines) == 8 and lines[7] == "")
        patch_rel = f"{PROPS_REL}/{pid(124)}/r1.patch"
        self.assertEqual(
            lines[:6],
            [
                f"[{pid(124)}] Playbook 片段｜modify｜目標：playbooks/demo.yaml"
                f"｜digest：{d8}｜驗證：未驗",
                "一、症狀：卡面症狀一句",
                "二、改什麼：+2／-2 行；觸及比例 0.05；觸及檔案數 1；不在 target 內的路徑：0",
                "三、風險與回滾：風險一句｜回滾：git revert 該 patch｜驗證：未驗",
                "決定：核准 ／ 否決＋一句理由 ／ 退回＋一句修改要求",
                "--- 以下不計入核心區 ---",
            ],
        )
        self.assertEqual(
            lines[6],
            f"證據座標：{obs_id(1)}、{obs_id(2)}｜預算宣告：1 次子代理、約 3000 token"
            f"｜完整 diff 座標：{patch_rel}｜冷卻狀態：無｜轉交通道：無",
        )
        hand = self.card(repo, pid(125))
        self.assertTrue(hand[0].endswith("｜僅轉交，本迴圈不套用"))
        self.assertIn("決定：轉交 ／ 不轉交＋一句理由", hand)
        self.assertTrue(hand[-2].endswith("轉交通道：DEF"))

        def variant(events):
            r = fx.new_dir("vr")
            shutil.copytree(repo, r)
            fx.append_events(r, events)
            return self.card(r, pid(124))

        for verdict in ("PASS", "FAIL", "NE"):
            lines = variant(
                [
                    fx.dec_ev(124, "approve"),
                    ev("app.sandbox", prop=pid(124)),
                    ev("app.verify", prop=pid(124), verdict=verdict),
                ]
            )
            self.assertIn(f"驗證：{verdict}", lines[0])
            self.assertIn(f"｜驗證：{verdict}", lines[3])
        self.assertIn("冷卻狀態：冷卻中", variant([fx.dec_ev(124, "reject")])[-2])
        self.assertIn(
            "冷卻狀態：無", variant([fx.dec_ev(124, "reject"), fx.dec_ev(124, "unblock")])[-2]
        )

    def test_AT_114_1_2_memory_card_shows_na_ratio(self):
        repo, run = self.make("M")
        d8 = props_of(repo)[0]["digest"].split(":")[1][:8]
        rc, out, err = self.M(repo, "card", pid(124))
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.endswith("\n"))
        lines = out.split("\n")
        self.assertEqual(len(lines), 8)
        self.assertEqual(
            lines[0],
            f"[{pid(124)}] 記憶條目｜modify｜目標：memory/demo.md｜digest：{d8}｜驗證：未驗",
        )
        self.assertEqual(
            lines[2], "二、改什麼：+2／-2 行；觸及比例 n/a；觸及檔案數 1；不在 target 內的路徑：0"
        )
        self.assertNotRegex(lines[2], r"\d\.\d\d")
        limit = fx.params_dict()["card_line_max"]
        self.assertTrue(lines[1].startswith("一、") and lines[4].startswith("決定："))
        self.assertTrue(all(width(ln) <= limit for ln in lines[1:5]))
        rc, js, err = self.M(repo, "card", pid(124), "--json")
        self.assertEqual(rc, 0, err)
        obj = json.loads(js)
        self.assertEqual(obj["core_lines"], 5)
        want = {"digest8": d8, "added": 2, "removed": 2, "touched_count": 1,
                "extra_paths": [], "verdict": "未驗"}  # fmt: skip
        self.assertEqual({k: obj["parsed"][k] for k in want}, want)
        self.assertEqual(obj["text"], out)

    def test_AT_114_1_E_1_card_ignores_free_text(self):
        repo, run = self.make(
            "P", body=body_md("P", symptom="+99／-99 行；觸及比例 0.99；觸及檔案數 9")
        )
        lines = self.card(repo, pid(124))
        self.assertIn("+99／-99", lines[1])
        self.assertEqual(
            lines[2], "二、改什麼：+2／-2 行；觸及比例 0.05；觸及檔案數 1；不在 target 內的路徑：0"
        )
        rc, out, err = self.M(repo, "card", pid(900 + 4))
        self.usage_error(rc, out, err)
        self.assertIn("PROP-NOT-FOUND", err)
        (repo / PROPS_REL / pid(124) / "r1.md").unlink()
        rc, out, err = self.M(repo, "card", pid(124))
        self.usage_error(rc, out, err)
        self.assertIn("PROP-FILE-MISSING", err)
        self.usage_error(*self.M(repo, "card"))

    def test_AT_114_2_1_parsed_matches_recomputed(self):
        repo, _ = self.make("P")
        rc, out, err = self.M(repo, "card", pid(124), "--json")
        self.assertEqual(rc, 0, err)
        obj = json.loads(out)
        self.assertEqual(
            list(obj), ["schema_rev", "prop", "rev", "digest", "core_lines", "text", "parsed"]
        )
        e = props_of(repo)[0]
        self.assertEqual((obj["schema_rev"], obj["core_lines"], obj["digest"]), (1, 5, e["digest"]))
        self.assertEqual(obj["text"], self.M(repo, "card", pid(124))[1])
        self.assertEqual(
            list(obj["parsed"]),
            ["digest8", "added", "removed", "touched_count", "extra_paths", "verdict"],
        )
        patch = (repo / PROPS_REL / pid(124) / "r1.patch").read_text(encoding="utf-8")
        added = sum(
            1 for ln in patch.split("\n") if ln.startswith("+") and not ln.startswith("+++")
        )
        removed = sum(
            1 for ln in patch.split("\n") if ln.startswith("-") and not ln.startswith("---")
        )
        self.assertEqual(
            obj["parsed"],
            {
                "digest8": e["digest"].split(":")[1][:8],
                "added": added,
                "removed": removed,
                "touched_count": 1,
                "extra_paths": [],
                "verdict": "未驗",
            },
        )

    def test_AT_114_2_E_1_tampered_card_refused(self):
        base, _ = self.make("P")
        self.assertEqual(len(self.card(base, pid(124))), 8)

        def tamper(fn):
            r = fx.new_dir("tp")
            shutil.copytree(base, r)
            fn(r)
            return r

        def edit_digest(r):
            lines = []
            for ln in fx.read(r, EVL).split("\n")[:-1]:
                o = json.loads(ln)
                if o["kind"] == "prop":
                    o["digest"] = fx.H(777)
                lines.append(fx.dumps_line(o) + "\n")
            fx.put(r, EVL, "".join(lines))

        cases = [
            lambda r: fx.putb(
                r,
                f"{PROPS_REL}/{pid(124)}/r1.patch",
                (r / PROPS_REL / pid(124) / "r1.patch").read_bytes() + b"+extra\n",
            ),
            lambda r: fx.put(
                r,
                f"{PROPS_REL}/{pid(124)}/r1.md",
                fx.read(r, f"{PROPS_REL}/{pid(124)}/r1.md").replace("卡面症狀一句", "改字"),
            ),
            edit_digest,
        ]
        for i, fn in enumerate(cases):
            r = tamper(fn)
            for extra in ([], ["--json"]):
                rc, out, err = self.M(r, "card", pid(124), *extra)
                self.usage_error(rc, out, err, msg=str(i))
                self.assertIn("CARD-INCONSISTENT", err)
                self.assertIn("digest8", err)

    def test_AT_114_3_1_layout_boundaries_accepted(self):
        files = {f"docs/notes/f{i}.md" for i in range(1, 8)}
        patch = fx.patch_join(
            fx.patch_mod("playbooks/demo.yaml", {1: "x"}),
            *[fx.patch_mod(f, {1: "x"}) for f in sorted(files)],
        )
        repo, run = self.make("P", target=["playbooks/demo.yaml"], patch=patch)
        lines = self.card(repo, pid(124))
        self.assertEqual(lines[2].split("；")[-1], "不在 target 內的路徑：7")
        extra = lines[3:10]
        self.assertEqual(extra, [f"  - {f}" for f in sorted(files)])
        self.assertTrue(lines[10].startswith("三、") and lines[11].startswith("決定："))
        core = lines[:12]
        self.assertTrue(all(width(x) <= 100 for x in core[1:]))
        for label, symptom in (("ascii", "a" * 90), ("fullwidth", "字" * 45)):
            repo, run = self.make("P", body=body_md("P", symptom=symptom))
            lines = self.card(repo, pid(124))
            self.assertEqual(width(lines[1]), 100, label)

    def test_AT_114_3_E_1_layout_rejections(self):
        files = [f"docs/notes/f{i}.md" for i in range(1, 9)]
        patch = fx.patch_join(
            fx.patch_mod("playbooks/demo.yaml", {1: "x"}),
            *[fx.patch_mod(f, {1: "x"}) for f in files],
        )
        repo, run = self.fresh_run_repo()
        snap0 = fx.snap(repo)
        self.rej(
            repo, run, {"CARD-TOO-TALL"}, "P", "8 筆", target=["playbooks/demo.yaml"], patch=patch
        )
        for label, symptom in (("91", "a" * 91), ("46 全形", "字" * 46), ("50 全形", "字" * 50)):
            self.rej(
                repo, run, {"CARD-LINE-TOO-WIDE"}, "P", label, body=body_md("P", symptom=symptom)
            )
        self.assertEqual(fx.snap(repo), snap0)


class TestDigestAndFiles(PropCase):
    """受測：`tools/lib/selfimproving/propfiles.py`／`props.py`（提案檔與 digest）。"""

    def test_AT_144_1_1_files_and_digest(self):
        outs = []
        for crlf in (True, False):
            repo, run = self.fresh_run_repo()
            body = body_md("P")
            self.ok(repo, run, "P", body=body.replace("\n", "\r\n") if crlf else body)
            e = props_of(repo)[0]
            folder = repo / PROPS_REL / e["id"]
            patch, md = (folder / "r1.patch").read_bytes(), (folder / "r1.md").read_bytes()
            self.assertNotIn(b"\r", md)
            self.assertEqual(md, body.encode("utf-8"))
            self.assertEqual(e["patch_sha256"], fx.sha(patch))
            self.assertEqual(e["body_sha256"], fx.sha(md))
            touched = ["playbooks/demo.yaml"]
            blob = json.dumps(touched, ensure_ascii=False, separators=(",", ":")).encode()
            self.assertEqual(e["touched_sha256"], fx.sha(blob))
            fields = {"rollback": "git revert 該 patch", "budget": "1 次子代理、約 3000 token",
                      "retire_when": "該段連續兩個運轉無人引用",
                      "reopen_symptom": "同一條提示再度被研究者重寫"}
            core = {
                "id": e["id"],
                "rev": 1,
                "cls": "P",
                "action": "modify",
                "target": touched,
                "touched": touched,
                "touched_count": 1,
                "base": e["base"],
                "preimage": e["base"],
                "patch_sha256": e["patch_sha256"],
                "body_sha256": e["body_sha256"],
                "rollback": fields["rollback"],
                "retire_when": fields["retire_when"],
                "reopen_symptom": fields["reopen_symptom"],
                "budget": fields["budget"],
            }
            canon = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            self.assertEqual(e["digest"], fx.sha(canon.encode("utf-8")))
            outs.append((e["body_sha256"], e["digest"], e["base"]))
        self.assertEqual(outs[0], outs[1])

    def test_AT_144_1_E_1_digest_sensitivity_and_failures(self):
        digests = []
        for targets in (["playbooks/demo.yaml"], ["playbooks/demo.yaml", "docs/notes/other.md"]):
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, "P", target=targets)
            digests.append(props_of(repo)[0])
        a, b = digests
        for key in ("patch_sha256", "body_sha256", "touched_sha256"):
            self.assertEqual(a[key], b[key], key)
        self.assertNotEqual(a["digest"], b["digest"])
        seen = []
        for when in ("原字", "差一字"):
            repo, run = self.fresh_run_repo()
            self.ok(repo, run, "P", body=body_md("P", retire_when=f"症狀不再出現{when}"))
            seen.append(props_of(repo)[0]["digest"])
        self.assertNotEqual(*seen)
        repo, run = self.fresh_run_repo()
        folder = repo / PROPS_REL / pid(124)
        folder.mkdir(parents=True)
        (folder / "r1.md").write_bytes(b"pre-existing")
        before = ledger_bytes(repo)
        rc, out, _ = self.new(repo, run, "P")
        self.rejected(rc, out)
        self.assertIn("PROP-FILE-EXISTS", fx.codes_of(out))
        self.assertEqual((folder / "r1.md").read_bytes(), b"pre-existing")
        self.assertFalse((folder / "r1.patch").exists())
        self.assertEqual(ledger_bytes(repo), before)
        repo, run = self.fresh_run_repo()
        before = ledger_bytes(repo)

        def boom():
            raise OSError("模擬追加失敗")

        with mock.patch.object(evwrite, "PAUSE_HOOK", boom):
            rc, out, err = self.new(repo, run, "P")
        self.assertNotEqual(rc, 0)
        self.assertEqual(ledger_bytes(repo), before)
        self.assertFalse((repo / PROPS_REL / pid(124)).exists())


class TestProposerArticles(unittest.TestCase):
    @staticmethod
    def sop() -> str:
        return fx.REAL_SOP.read_bytes().decode("utf-8").replace("\r\n", "\n")

    def _group(self, frags, other):
        text = self.sop()
        self.assertTrue(fx.line_has_all(fx.sop_section(text, "提案者"), *frags))
        s, e = fx.same_line(text, "提案者", frags)
        copies = [text[:s] + text[s:e].replace(f, "") + text[e:] for f in frags]
        copies.append(fx.split_last_to_next_line(text, "提案者", frags))
        copies.append(fx.move_line(text, "提案者", frags, other))
        for i, copy in enumerate(copies):
            self.assertEqual(fx.line_has_all(fx.sop_section(copy, "提案者"), *frags), [], i)

    def test_AT_109_1_2_abstraction_clause(self):
        self._group(("抽象化", "結果標籤", "原始軌跡全文"), "審查者")

    def test_AT_110_2_2_zero_recursion_clause(self):
        self._group(("不得再派", "提案者", "審查者"), "凍結者")


if __name__ == "__main__":
    unittest.main()
