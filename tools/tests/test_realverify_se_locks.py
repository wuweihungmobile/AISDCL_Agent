"""realverify 副作用隔離的結構鎖（AST／字面普查）：居所字面、排程撤銷單一家、`~/.claude.json`
不寫、env 鍵分類、
SITES 開窗普查、`arm_sentinel` WHY、沙盒工作樹乾淨與 worktree 外層佈局（DES §3.1／§4／§5.5；
AT-SE-01／17／18／24／25／27／30、MU-SE-13、REQ-SE-07／23／24／34／51）。

受測模組：`tools/lib/realverify/`（sandbox／interactive／leases／cases）與
`tools/lib/sandbox_scope.py`。
鎖的目的：下一個案例作者「忘記」時，是測試變紅，不是幽靈 session 再出現。
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
_REPO = _TOOLS.parent
# 逐行明寫（靜態可解析；ci_paths 鎖不解析迴圈變數）
sys.path.insert(0, str(_TOOLS))
sys.path.insert(0, str(_TOOLS / "lib"))

from lib import endurance_env, sandbox_scope  # noqa: E402
from lib.realverify import cases as rv_cases  # noqa: E402
from lib.realverify import interactive, leases, leases_undo, sandbox  # noqa: E402

RV = _TOOLS / "lib" / "realverify"
#: realverify 內 `Path.home()`／`".autosdd"`／`expanduser` 字面只准住這幾個檔（鍵→WHY；REQ-SE-23）。
HOME_LITERAL_ALLOWED = {
    "sandbox.py": "真環境位置的唯讀入口 real_home／real_autosdd／claude_home",
    "leases.py": "租約帳目錄 ~/.autosdd/realverify_leases",
    "interactive.py": "宿主 repo rv_host 與唯讀的 ~/.claude.json",
}


def _py(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py") if "__pycache__" not in p.parts
    )


def _tree(p: Path) -> ast.AST:
    return ast.parse(p.read_text(encoding="utf-8"), filename=str(p))


def home_literal_hits(root: Path) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for p in _py(root):
        for n in ast.walk(_tree(p)):
            hit = (isinstance(n, ast.Constant) and n.value == ".autosdd") or (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and (
                    (
                        n.func.attr == "home"
                        and getattr(n.func.value, "id", "") == "Path"
                    )
                    or n.func.attr == "expanduser"
                )
            )
            if hit:
                out.setdefault(p.name, []).append(n.lineno)
    return out


class ResidenceAndEnvTest(unittest.TestCase):
    """sandbox.py：7 居所單一表、env 全指家目錄、撤 real_traces／handoff_dir（AT-SE-18、
    MU-SE-23）。"""

    def test_residence_table_equals_the_job_env_residence_keys(self):
        self.assertEqual(
            tuple(sandbox.RESIDENCE_DIRS), endurance_env.RESIDENCE_KEYS
        )

    def test_env_points_every_residence_under_the_home_and_closes_notify_and_sentinel(
        self,
    ):
        sb = sandbox.Sandbox(
            root=Path(tempfile.gettempdir()) / "AutoSDD_RV_sbx_unit0001"
        )
        env = sb.env()
        for key, name in sandbox.RESIDENCE_DIRS.items():
            self.assertEqual(Path(env[key]), sb.home / name)
        self.assertEqual(
            (env["AUTOSDD_DESKTOP_NOTIFY"], env["AUTOSDD_SENTINEL_OFF"]),
            ("", "1"),
        )
        self.assertNotIn("AUTOSDD_UNATTENDED", env)

    def test_the_real_traces_escape_hatch_and_real_handoff_dir_are_gone(self):
        self.assertFalse(hasattr(sandbox, "handoff_dir"))
        bad = []
        for p in _py(RV):
            for n in ast.walk(_tree(p)):
                ident = (
                    n.id
                    if isinstance(n, ast.Name)
                    else n.arg
                    if isinstance(n, (ast.arg, ast.keyword))
                    else n.attr
                    if isinstance(n, ast.Attribute)
                    else getattr(n, "name", "")
                )
                if ident in ("real_traces", "real_trace_dir"):
                    bad.append(f"{p.name}:{getattr(n, 'lineno', 0)} {ident}")
                if (
                    isinstance(n, ast.ImportFrom)
                    and any(a.name == "handoff_dir" for a in n.names)
                    and (n.module or "").endswith("sandbox")
                ):
                    bad.append(
                        f"{p.name}:{n.lineno} from sandbox import handoff_dir"
                    )
        self.assertEqual(
            bad, [], "real_traces／真 handoff_dir 已撤（REQ-SE-23）"
        )

    def test_local_excludes_cover_every_residence_dir_bin_and_the_identity_file(
        self,
    ):
        names = set(sandbox.LOCAL_EXCLUDES)
        self.assertIn("/" + sandbox_scope.IDENTITY_NAME, names)
        self.assertTrue(
            {f"/{d}/" for d in sandbox.RESIDENCE_DIRS.values()} <= names
        )
        self.assertTrue({"bin", "fakeclaude.*"} <= {n.strip("/") for n in names})
        from lib.realverify.cases import sessionctl_park  # noqa: PLC0415

        self.assertTrue(
            set(sandbox.LOCAL_EXCLUDES)
            <= set(sessionctl_park._EXCLUDES.splitlines())
        )  # noqa: SLF001

    def test_home_literals_live_only_in_the_allowed_files(self):
        hits = home_literal_hits(RV)
        self.assertEqual(set(hits) - set(HOME_LITERAL_ALLOWED), set(), hits)

    def test_home_literal_detector_is_not_vacuous(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "case.py").write_text(
                'from pathlib import Path\nx = Path.home() / ".autosdd" / "handback"\n',
                encoding="utf-8",
            )
            self.assertEqual(set(home_literal_hits(Path(d))), {"case.py"})

    def test_arm_sentinel_true_call_sites_carry_a_why_comment_within_three_lines(
        self,
    ):
        bad = []
        for p in _py(RV):
            lines = p.read_text(encoding="utf-8").splitlines()
            for n in ast.walk(_tree(p)):
                if (
                    isinstance(n, ast.keyword)
                    and n.arg == "arm_sentinel"
                    and getattr(n.value, "value", None) is True
                ):
                    window = lines[
                        max(0, n.value.lineno - 4) : n.value.lineno
                    ]
                    if not any("# WHY" in ln for ln in window):
                        bad.append(f"{p.name}:{n.value.lineno}")
        self.assertEqual(bad, [])
        from lib.realverify.cases.sessionctl_park import ctl_env  # noqa: PLC0415

        sb = sandbox.Sandbox(
            root=Path(tempfile.gettempdir()) / "AutoSDD_RV_sbx_unit0002"
        )
        self.assertEqual(ctl_env(sb)["AUTOSDD_SENTINEL_OFF"], "1")
        self.assertNotIn(
            "AUTOSDD_SENTINEL_OFF", ctl_env(sb, arm_sentinel=True)
        )


_KEY = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")


def env_keys(fn: ast.AST) -> set[str]:
    keys: set[str] = set()
    for n in ast.walk(fn):
        if (
            isinstance(n, ast.Subscript)
            and isinstance(n.slice, ast.Constant)
            and isinstance(n.slice.value, str)
        ):
            if isinstance(n.ctx, ast.Store) and _KEY.match(n.slice.value):
                keys.add(n.slice.value)
        elif isinstance(n, ast.Dict):
            keys |= {
                k.value
                for k in n.keys
                if isinstance(k, ast.Constant)
                and isinstance(k.value, str)
                and _KEY.match(k.value)
            }
    return keys


def helper_env_keys(root: Path) -> dict[str, set[str]]:
    """`Sandbox.env` 與所有名稱以 `_env` 結尾（或叫 `env`）的案例 env 輔助函式設定的鍵。"""
    out: dict[str, set[str]] = {}
    for p in _py(root):
        for fn in ast.walk(_tree(p)):
            if isinstance(fn, ast.FunctionDef) and (
                fn.name.endswith("_env") or fn.name == "env"
            ):
                ks = env_keys(fn)
                if ks:
                    out[f"{p.name}::{fn.name}"] = ks
    return out


class EnvKeyClassificationTest(unittest.TestCase):
    """AST 鎖②：env 輔助函式設定的每一鍵 ⊆ JOB_ENV_KEYS ∪ SANDBOX_LOCAL_ONLY（REQ-SE-24、
    AT-SE-35）。"""

    def allowed(self) -> set[str]:
        return set(endurance_env.JOB_ENV_KEYS) | set(
            sandbox.SANDBOX_LOCAL_ONLY
        )

    def test_every_key_is_classified(self):
        unclassified = {
            f: sorted(ks - self.allowed())
            for f, ks in helper_env_keys(RV).items()
            if ks - self.allowed()
        }
        self.assertEqual(
            unclassified,
            {},
            "新鍵須進 JOB_ENV_KEYS（允許表）或 SANDBOX_LOCAL_ONLY（附 WHY）",
        )

    def test_an_unclassified_key_in_sandbox_env_turns_the_lock_red(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.py").write_text(
                'def my_env(sb):\n    e = {}\n    e["AUTOSDD_BRAND_NEW"] = "1"\n    return e\n',
                encoding="utf-8",
            )
            found = helper_env_keys(Path(d))
        self.assertEqual(
            {k for ks in found.values() for k in ks} - self.allowed(),
            {"AUTOSDD_BRAND_NEW"},
        )

    def test_local_only_entries_carry_a_why_and_are_not_job_env_keys(self):
        for key, why in sandbox.SANDBOX_LOCAL_ONLY.items():
            self.assertGreaterEqual(len(why), 3, key)
            self.assertNotIn(
                key, endurance_env.JOB_ENV_KEYS, f"{key} 已在允許表，不必重複"
            )


def sched_revocation_sites(root: Path) -> dict[str, list[int]]:
    """`sched.remove`／`<backend>.disarm`／以 `ps()`／`_ps()` 執行含
    `Unregister-ScheduledTask` 的呼叫。"""
    out: dict[str, list[int]] = {}
    for p in _py(root):
        tree = _tree(p)
        docs = {
            id(n.body[0].value)
            for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and n.body
            and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
        }
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if (
                    n.func.attr == "remove"
                    and getattr(n.func.value, "id", "") == "sched"
                ) or n.func.attr == "disarm":
                    out.setdefault(p.name, []).append(n.lineno)
            if (
                isinstance(n, ast.Constant)
                and isinstance(n.value, str)
                and "Unregister-ScheduledTask" in n.value
                and id(n) not in docs
                and n.value.strip().startswith(("Unregister", "f"))
                is not None
            ):
                if n.value.lstrip().startswith(
                    "Unregister-ScheduledTask -TaskName"
                ):
                    out.setdefault(p.name, []).append(n.lineno)
    return out


class SchedulerRevocationHasOneHomeTest(unittest.TestCase):
    """REQ-SE-34／AT-SE-27：realverify 內撤排程的呼叫只准在 `leases.py`（`sched.py`
    是低階原語本體）。"""

    def test_only_leases_py_and_the_sched_primitive_revoke(self):
        hits = sched_revocation_sites(RV)
        self.assertEqual(set(hits) - {"leases.py", "sched.py"}, set(), hits)

    def test_detector_catches_an_injected_second_home(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "case.py").write_text(
                'def f(sched, backend):\n    sched.remove("x")\n    backend.disarm("y")\n'
                "def g(ps):\n    ps(\"Unregister-ScheduledTask -TaskName 'n'\")\n",
                encoding="utf-8",
            )
            self.assertEqual(
                len(sched_revocation_sites(Path(d))["case.py"]), 3
            )

    def test_the_old_cleanup_entry_points_are_thin_shells_delegating_to_leases(
        self,
    ):
        import inspect  # noqa: PLC0415

        self.assertFalse(
            hasattr(
                __import__("lib.realverify.sched", fromlist=["x"]),
                "cleanup_all_rv",
            )
        )
        self.assertIn(
            "leases.revoke_oldwin",
            inspect.getsource(sandbox.Sandbox._disarm_oldwin_tasks),
        )  # noqa: SLF001
        self.assertIn(
            "leases_discover.sweep_projects",
            inspect.getsource(sandbox.sweep_orphans),
        )
        from lib.realverify.cases import sessionctl_park  # noqa: PLC0415

        self.assertIn(
            "leases.revoke_sched_like",
            inspect.getsource(sessionctl_park.remove_tasks_like),
        )
        self.assertNotIn(
            "Unregister", inspect.getsource(sessionctl_park.park_cleanup)
        )


_WRITERS = {
    "write_text",
    "write_bytes",
    "dump",
    "replace",
    "rename",
    "open",
    "unlink",
}


def claude_json_writes(files: list[Path]) -> list[str]:
    """寫檔呼叫的目標若含字面 `.claude.json`（或由它賦值的名稱）⇒ 命中。唯讀（
    `read_text`／`open(..., "r")`）不算。"""
    bad: list[str] = []
    for p in files:
        tree = _tree(p)
        tainted = {
            t.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(c, ast.Constant) and c.value == ".claude.json"
                for c in ast.walk(n.value)
            )
            for t in n.targets
            if isinstance(t, ast.Name)
        }

        def mentions(node) -> bool:
            return any(
                (isinstance(c, ast.Constant) and c.value == ".claude.json")
                or (isinstance(c, ast.Name) and c.id in tainted)
                for c in ast.walk(node)
            )

        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            name = (
                n.func.attr
                if isinstance(n.func, ast.Attribute)
                else getattr(n.func, "id", "")
            )
            if name not in _WRITERS:
                continue
            if name == "open":
                mode = next(
                    (
                        a.value
                        for a in n.args[1:2]
                        if isinstance(a, ast.Constant)
                    ),
                    "r",
                )
                mode = next(
                    (
                        k.value.value
                        for k in n.keywords
                        if k.arg == "mode"
                        and isinstance(k.value, ast.Constant)
                    ),
                    mode,
                )
                if not any(c in str(mode) for c in "wax+") or not (
                    n.args and mentions(n.args[0])
                ):
                    continue
                bad.append(f"{p.name}:{n.lineno}")
            elif (
                name in ("write_text", "write_bytes", "unlink")
                and isinstance(n.func, ast.Attribute)
                and mentions(n.func.value)
            ):
                bad.append(f"{p.name}:{n.lineno}")
            elif name in ("replace", "rename", "dump") and any(
                mentions(a) for a in n.args
            ):
                bad.append(f"{p.name}:{n.lineno}")
    return bad


class NeverWriteTheGlobalClaudeConfigTest(unittest.TestCase):
    """REQ-SE-51／AT-SE-24：tools 與 `.claude/hooks` 內任何程式都不寫 `~/.claude.json`。"""

    def surface(self) -> list[Path]:
        skip = {"tests", "__pycache__"}
        return [
            p
            for root in (_TOOLS, _REPO / ".claude" / "hooks")
            for p in sorted(root.rglob("*.py"))
            if not skip & set(p.relative_to(_REPO).parts)
        ]

    def test_real_tree_has_no_writer(self):
        files = self.surface()
        self.assertGreater(len(files), 200, "掃描面太小＝列舉壞了")
        self.assertEqual(claude_json_writes(files), [])

    def test_injected_writers_turn_it_red_and_readers_do_not(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "w.py"
            bad.write_text(
                'from pathlib import Path\nimport json, os\np = Path.home() / ".claude.json"\n'
                'p.write_text("x")\nopen(p, "w")\n'
                'json.dump({}, open(p, "a"))\nos.replace("a", p)\n',
                encoding="utf-8",
            )
            ok = Path(d) / "r.py"
            ok.write_text(
                'from pathlib import Path\np = Path.home() / ".claude.json"\n'
                'p.read_text()\nopen(p, "r")\n',
                encoding="utf-8",
            )
            self.assertGreaterEqual(len(claude_json_writes([bad])), 4)
            self.assertEqual(claude_json_writes([ok]), [])


def census_files(repo: Path) -> list[tuple[str, Path]]:
    """D-22 普查範圍：`tools/*.py`、`tools/lib/**/*.py`、`.claude/hooks/*.py`；排除
    tests／probe／realverify。"""
    tools, out = repo / "tools", []
    for p in sorted(tools.glob("*.py")):
        out.append((p.stem, p))
    for p in _py(tools / "lib"):
        if "realverify" not in p.parts:
            out.append(
                (".".join(p.relative_to(tools).with_suffix("").parts), p)
            )
    for p in sorted((repo / ".claude" / "hooks").glob("*.py")):
        out.append((p.stem, p))
    return out


def site_census(
    files: list[tuple[str, Path]],
) -> dict[tuple[str, str], set[str]]:
    """`(模組, 函式) → 形態集合`：開窗（`CREATE_NEW_CONSOLE`、`creationflags=0x10`）、
    排程登記（`backend.arm`／
    `register`、`Register-ScheduledTask`）、toast（`NotifyIcon`）與 `claude` 執行形態（
    `yields_claude`＋參數預設）。"""
    out: dict[tuple[str, str], set[str]] = {}
    for mod, p in files:
        for fn in ast.walk(_tree(p)):
            if not isinstance(fn, ast.FunctionDef):
                continue
            names = {
                t.id
                for n in ast.walk(fn)
                if isinstance(n, ast.Assign)
                and interactive.yields_claude(n.value)
                for t in n.targets
                if isinstance(t, ast.Name)
            } | interactive.claude_param_names(fn)
            hits: set[str] = set()
            for n in ast.walk(fn):
                if (
                    isinstance(n, ast.Attribute)
                    and n.attr == "CREATE_NEW_CONSOLE"
                    or (
                        isinstance(n, ast.Name)
                        and n.id == "CREATE_NEW_CONSOLE"
                    )
                ):
                    hits.add("window")
                elif isinstance(n, ast.Constant) and n.value in (
                    "CREATE_NEW_CONSOLE",
                    "Register-ScheduledTask",
                    "NotifyIcon",
                ):
                    hits.add(str(n.value))
                elif (
                    isinstance(n, ast.keyword)
                    and n.arg == "creationflags"
                    and getattr(n.value, "value", None) in (0x10, 16)
                ):
                    hits.add("flags16")
                elif isinstance(n, ast.Call):
                    f = n.func
                    if (
                        isinstance(f, ast.Attribute)
                        and f.attr in ("arm", "register")
                        and getattr(f.value, "id", "") == "backend"
                    ):
                        hits.add(f"backend.{f.attr}")
                    if (
                        n.args
                        and isinstance(n.args[0], ast.List)
                        and any(
                            interactive.yields_claude(e)
                            or (isinstance(e, ast.Name) and e.id in names)
                            for e in n.args[0].elts
                        )
                    ):
                        hits.add("claude-argv")
            if hits:
                out[(mod, fn.name)] = hits
    return out


#: 普查命中但不是「到點／spawn 站點」本身者（鍵→WHY）。
CENSUS_EXEMPT = {
    (
        "lib.openitems.drive",
        "make",
    ): "deps 工廠，只回傳 backend.register 的包裝；實際登記在 drive_item（已是 SITE）"
}


class SitesCensusTest(unittest.TestCase):
    """REQ-SE-07／AT-SE-17：開窗／排程登記／claude 執行形態的產品函式都在 `SITES`；偵測器與
    `interactive.yields_claude` 同一物件。
    誠實劃界：偵測器認**形態**（旗標、字面、`yields_claude`、參數預設）；以非字面方式組出
    claude 的無頭呼叫它看不見，
    那一半靠 SITES 的人工登記（`probe_quota` 呼叫者等）與各站點的單元測試。"""

    def registered(self) -> set[tuple[str, str]]:
        return {(s.module, s.function) for s in sandbox_scope.SITES}

    def test_current_tree_every_hit_is_a_registered_site(self):
        found = site_census(census_files(_REPO))
        self.assertGreaterEqual(
            len(census_files(_REPO)), 100, "掃描面太小＝列舉壞了"
        )
        unregistered = {
            k: sorted(v)
            for k, v in found.items()
            if k not in self.registered() and k not in CENSUS_EXEMPT
        }
        self.assertEqual(
            unregistered,
            {},
            "新的開窗／排程登記／claude 形態函式必須進 sandbox_scope.SITES 並呼叫判準",
        )
        self.assertTrue(
            {"spawn", "spawn_resume"} <= {k[1] for k in found},
            "偵測器對已知開窗站點失明",
        )

    def test_every_registered_site_exists_in_source(self):
        for s in sandbox_scope.SITES:
            path = _TOOLS / (s.module.replace(".", "/") + ".py")
            if not path.is_file():
                path = _REPO / ".claude" / "hooks" / (s.module + ".py")
            self.assertTrue(path.is_file(), s)
            self.assertIn(
                s.function,
                {
                    n.name
                    for n in ast.walk(_tree(path))
                    if isinstance(n, ast.FunctionDef)
                },
                s,
            )

    def test_five_injections_each_turn_the_census_red_and_probe_dirs_are_out_of_scope(
        self,
    ):
        inj = {
            "a": "import subprocess\ndef a():\n    return subprocess.CREATE_NEW_CONSOLE\n",
            "b": 'import subprocess\ndef b():\n'
                  '    return getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)\n',
            "c": "import subprocess\ndef c():\n    subprocess.Popen(['x'], creationflags=0x10)\n",
            "d": 'import shutil, subprocess\ndef d():\n'
                  '    subprocess.run([shutil.which("claude") or "claude", "-p", "x"])\n',
            "e": 'def e(claude="claude", runner=None):\n    runner([claude, "-p", "x"])\n',
        }
        with tempfile.TemporaryDirectory() as dd:
            repo = Path(dd)
            for sub in (
                "tools/lib",
                "tools/probe",
                "tools/tests",
                ".claude/hooks",
            ):
                (repo / sub).mkdir(parents=True)
            for name, src in inj.items():
                (repo / "tools" / "lib" / f"inj_{name}.py").write_text(
                    src, encoding="utf-8"
                )
            (repo / "tools" / "probe" / "p.py").write_text(
                inj["a"], encoding="utf-8"
            )
            (repo / "tools" / "tests" / "t.py").write_text(
                inj["a"], encoding="utf-8"
            )
            found = {k[0] for k in site_census(census_files(repo))}
        self.assertEqual(found, {f"lib.inj_{n}" for n in inj})

    def test_detector_is_the_same_function_object_as_the_window_lock_uses(
        self,
    ):
        self.assertIs(interactive.yields_claude, interactive._yields_claude)  # noqa: SLF001
        for src, want in (
            ('x or "claude"', True),
            ('shutil.which("claude") or "claude"', True),
            ("find_claude()", True),
            ("other()", False),
            ("x or y", False),
        ):
            self.assertEqual(
                interactive.yields_claude(ast.parse(src, mode="eval").body),
                want,
                src,
            )
        fn = ast.parse(
            'def f(claude="claude", other=1, *, k="claude.exe"): pass'
        ).body[0]
        self.assertEqual(interactive.claude_param_names(fn), {"claude", "k"})


class SandboxLayoutTest(unittest.TestCase):
    """真 git：身分檔先於 git、工作樹乾淨、worktree 沙盒外層佈局與帳列（AT-SE-01／30、
    REQ-SE-01／52）。"""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        for p in (
            mock.patch.object(leases, "LEASE_DIR", self.tmp / "L"),
            mock.patch.object(leases_undo, "list_procs", return_value=[]),
        ):
            p.start()
            self.addCleanup(p.stop)

    def porcelain(self, root: Path) -> str:
        return subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout

    def test_identity_before_git_and_fresh_tree_is_clean_after_baseline(
        self,
    ):
        first_git: list[bool] = []
        real = sandbox._git

        def spy(args, cwd):
            first_git.append(
                (Path(cwd) / sandbox_scope.IDENTITY_NAME).is_file()
            )
            return real(args, cwd)

        with mock.patch.object(sandbox, "_git", side_effect=spy):
            sb = sandbox.Sandbox.create(probe_hook=False)
        try:
            self.assertTrue(first_git[0], "第一次 git 呼叫時身分檔必須已存在")
            ident = sandbox_scope._read_identity(sb.root)  # noqa: SLF001
            self.assertEqual(
                (ident["owner_pid"], ident["allow_until"], ident["sid"]),
                (__import__("os").getpid(), None, sb.sid),
            )
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(sb.root),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", "base"],
                cwd=str(sb.root),
                check=True,
                capture_output=True,
            )
            for name in sandbox.RESIDENCE_DIRS.values():
                (sb.root / name).mkdir()
                (sb.root / name / "f").write_text("x", encoding="utf-8")
            (sb.root / "bin").mkdir()
            for rel in (
                "bin/claude.exe",
                "fakeclaude.mode",
                "fakeclaude.sleep",
                "fakeclaude.rc",
                "fakeclaude.projdir",
                "fakeclaude.jsonl",
            ):
                (sb.root / rel).write_text("x", encoding="utf-8")
            self.assertEqual(
                self.porcelain(sb.root),
                "",
                "沙盒工作樹在案例動作前必須是乾淨的（D-23）",
            )
            new = sandbox.RESIDENCE_DIRS["AUTOSDD_SI_DIR"] + "_new"
            (sb.root / new).mkdir()
            (sb.root / new / "f").write_text("x", encoding="utf-8")
            self.assertNotEqual(
                self.porcelain(sb.root),
                "",
                "未進 exclude 的新居所目錄必須讓工作樹變髒（鎖有鑑別力）",
            )
        finally:
            self.assertEqual(sb.cleanup(), [])

    def _trusted(self, rows: list):
        host = self.tmp / "host"
        host.mkdir()
        for args in (
            ["init", "-q"],
            ["config", "user.email", "a@b.c"],
            ["config", "user.name", "n"],
            ["commit", "-q", "--allow-empty", "-m", "h"],
        ):
            subprocess.run(
                ["git", *args], cwd=str(host), check=True, capture_output=True
            )
        cj = self.tmp / "claude.json"
        cj.write_text(
            json.dumps(
                {
                    "projects": {
                        interactive.host_key(host): {
                            "hasTrustDialogAccepted": True
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        def prober(root):
            rows.extend(
                (r["kind"], r["state"])
                for r in leases.read_rows(
                    next((self.tmp / "L").glob("*.jsonl"))
                )
            )
            return "ready", "fake"

        return interactive.trusted_sandbox(
            host=host, claude_json=cj, prober=prober, probe_hooks=False
        )

    def test_worktree_sandbox_lives_one_level_below_its_home_and_is_ledgered_before_the_actions(
        self,
    ):
        rows: list = []
        sb = self._trusted(rows)
        try:
            self.assertEqual(sb.root, sb.home / "wt")
            self.assertTrue((sb.home / sandbox_scope.IDENTITY_NAME).is_file())
            self.assertFalse(
                (sb.root / sandbox_scope.IDENTITY_NAME).exists(),
                "身分檔不在 worktree 內（工作樹不受影響）",
            )
            self.assertEqual(
                sandbox_scope.sandbox_home(sb.root),
                Path(__import__("os").path.normcase(str(sb.home.resolve()))),
            )
            self.assertIn(("worktree", "intent"), rows)
            self.assertIn(("worktree", "made"), rows)
            self.assertEqual(
                Path(sb.env()["AUTOSDD_TRACE_DIR"]), sb.home / "traces"
            )
            self.assertEqual(
                rows.index(("sandbox_root", "intent"))
                < rows.index(("worktree", "intent")),
                True,
            )
        finally:
            self.assertEqual(sb.cleanup(), [])
        self.assertFalse(sb.home.exists())

    def test_grant_side_effects_window_true_succeeds_for_a_trusted_sandbox_and_marks_the_identity(
        self,
    ):
        sb = self._trusted([])
        try:
            ctx = rv_cases.CaseContext("RV-T")
            ctx.grant_side_effects(sb, 10, window=True)
            self.assertIs(
                sandbox_scope._read_identity(sb.home)["window"], True
            )  # noqa: SLF001
            self.assertIsNotNone(
                sandbox_scope._read_identity(sb.home)["allow_until"]
            )  # noqa: SLF001
        finally:
            sb.cleanup()

    def test_open_window_ledgers_the_window_process_keyed_by_the_sandbox_sid_before_spawning(
        self,
    ):
        sb = self._trusted([])
        try:
            seen: list = []
            popen = mock.Mock(
                side_effect=lambda *a, **k: (
                    seen.append(
                        [
                            (r["kind"], r["ident"])
                            for r in leases.read_rows(
                                next((self.tmp / "L").glob("*.jsonl"))
                            )
                        ]
                    )
                    or mock.Mock(pid=1)
                )
            )
            with mock.patch.object(subprocess, "Popen", popen):
                interactive.open_window(
                    sb, ["--model", "haiku"], claude="x.exe"
                )
            self.assertIn(("process", f"sid:{sb.sid}"), seen[0])
        finally:
            sb.procs.clear()
            sb.cleanup()


class KillTreeApiStaysTest(unittest.TestCase):
    """`sandbox.kill_tree` 的名稱、所在模組與簽章不變：`openitems/drive.py` 的 console_run
    依賴它。"""

    def test_signature(self):
        import inspect  # noqa: PLC0415

        self.assertEqual(
            list(inspect.signature(sandbox.kill_tree).parameters), ["proc"]
        )
        self.assertEqual(
            sandbox.kill_tree.__module__, "lib.realverify.sandbox"
        )


if __name__ == "__main__":
    unittest.main()
