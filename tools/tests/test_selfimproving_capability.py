"""SelfImproving 能力登記與純度判準（TCS-SelfImproving-P1 R63、R64；P2 R105 增第四類 `exec`；
AT-143 系列）。

登記表 `CAPABILITY` 住本檔（51 個鍵：39 `ro`、8 `rw`、2 `net`、2 `exec`；P3 增 7 `ro` 與
1 `rw`；議題中心增 3 `ro`）；判準函式 `capability_problems`
取參數（套件目錄 `tools/lib/selfimproving/`、登記表、入口檔 `tools/selfimproving.py`），
故真樹與合成樹用同一份碼自證。這不是新增守衛碼：測試檔在
`tools/tests/`、不在守衛面清單、不是 hook（PRD §9.7 #47）。
"""

from __future__ import annotations

import ast
import json
import re
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
from _selfimproving_fixtures import SiTestCase, aid, obs_id, pid, rid

TOOLS = fx.TOOLS
PKG = TOOLS / "lib" / "selfimproving"
ENTRY = TOOLS / "selfimproving.py"

CAPABILITY: dict[str, str] = {
    **{
        f"{n}.py": "ro"
        for n in (
            "__init__",
            "ledger",
            "rows",
            "git",
            "refs",
            "history",
            "params",
            "check",
            "events",
            "fold",
            "evcheck",
            "paths",
            "props",
            "defs",
            "sources",
            "card",
            "status",
            "scan",
            "export",
            "transcript",
            "decgrammar",
            "decverify",
            "cooldown",
            "heldout",
            "manifest",
            "verdict",
            "consoleaudit",
            "obsrows",
            "decheck",
            "mea",
            "meaplan",
            "meastat",
            "meacheck",
            "capacity",
            "retire",
            "churn",
            "issuemap",
            "issues",
            "issues_items",
        )
    },
    **{
        f"{n}.py": "rw"
        for n in ("evwrite", "propfiles", "writeverbs", "decwrite", "sandbox", "promote",
            "obswrite", "meawrite")
    },
    **{f"{n}.py": "net" for n in ("fetch", "research")},
    **{f"{n}.py": "exec" for n in ("runner", "verify")},
}
CATEGORIES = ("ro", "rw", "net", "exec")
CLOSURE_ONLY_RO = ("check.py", "status.py", "scan.py", "export.py", "card.py")
NET_MODULES = {"socket", "urllib", "http", "ssl", "ftplib", "smtplib", "asyncio", "requests"}
WRITE_RE = re.compile(
    r"write_text|write_bytes|\.mkdir\(|os\.remove|os\.unlink|os\.rename|os\.replace|shutil\."
    r"|open\([^)]*['\"][wax]b?\+?['\"]"
)
SHELL_RE = re.compile(r"os\.(?:system|popen)\b")
FORBIDDEN = [
    r"schtasks",
    r"launchctl",
    r"crontab",
    r"ScheduleWakeup",
    r"CronCreate",
    r"Register-ScheduledTask",
    r"apscheduler",
    r"threading\.Timer",
    r"sched\.scheduler",
    r"time\.sleep",
    r"while\s+True",
    r"daemon\s*=\s*True",
    r"os\.fork",
    r"signal\.alarm",
]
FORBIDDEN_RES = [re.compile(p) for p in FORBIDDEN]
FORBIDDEN_SAMPLES = [
    "schtasks /create",
    "launchctl load",
    "crontab -e",
    "ScheduleWakeup(1)",
    "CronCreate(x)",
    "Register-ScheduledTask",
    "apscheduler.x",
    "threading.Timer(1, f)",
    "sched.scheduler()",
    "time.sleep(1)",
    "while  True:",
    "daemon = True",
    "os.fork()",
    "signal.alarm(1)",
]


def setUpModule() -> None:
    fx.setup("si_cap_")


def tearDownModule() -> None:
    fx.teardown()


def _imports(tree: ast.AST, *, top_only: bool = False):
    body = tree.body if top_only else list(ast.walk(tree))
    yield from body


def _abs_imports(text: str) -> set[str]:
    mods: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def _rel_imports(text: str, pkg: str) -> set[str]:
    """套件內相對 import 的目標檔（不含 .py）。

    形態：from . import x、from .x import y、import <pkg>.x。
    """
    out: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ImportFrom):
            parts = (node.module or "").split(".")
            if node.level >= 1:
                out |= {a.name for a in node.names} if node.module is None else {parts[0]}
            elif node.module and pkg in parts:
                tail = parts[parts.index(pkg) + 1 :]
                out |= {tail[0]} if tail else {a.name for a in node.names}
        elif isinstance(node, ast.Import):
            for a in node.names:
                parts = a.name.split(".")
                if pkg in parts and parts.index(pkg) + 1 < len(parts):
                    out.add(parts[parts.index(pkg) + 1])
    return out


def capability_problems(
    pkg_dir: Path,
    registry: dict[str, str],
    entry_file: Path,
    *,
    net_file: str = "fetch.py",
    git_file: str = "git.py",
    runner_file: str = "runner.py",
    closure=CLOSURE_ONLY_RO,
) -> list[str]:
    out: list[str] = []
    files = {p.name for p in pkg_dir.glob("*.py")}
    out += [f"{n}：未登記（新檔須先登記類別）" for n in sorted(files - set(registry))]
    out += [f"{n}：登記表有鍵而檔不存在" for n in sorted(set(registry) - files)]
    out += [
        f"{n}：類別 {k!r} 不在 ro／rw／net／exec"
        for n, k in registry.items()
        if k not in CATEGORIES
    ]
    for name in sorted(files & set(registry)):
        text = (pkg_dir / name).read_bytes().decode("utf-8")
        kind = registry[name]
        mods = _abs_imports(text)
        out += [
            f"{name}：import 第三方套件 {m}"
            for m in sorted(
                m
                for m in mods
                if m not in sys.stdlib_module_names and m not in ("_stdio_utf8", "lib")
            )
        ]
        nets = mods & NET_MODULES
        if nets and name != net_file:
            out.append(f"{name}：網路模組 {sorted(nets)} 只准出現在 {net_file}")
        if kind == "ro":
            if WRITE_RE.search(text):
                out.append(f"{name}（ro）：含寫入形原語")
            if SHELL_RE.search(text):
                out.append(f"{name}（ro）：含 os.system／os.popen")
        if "subprocess" in text and name not in (git_file, runner_file):
            out.append(f"{name}（{kind}）：subprocess 字樣只准出現在 {git_file} 與 {runner_file}")
        if "runner" in _rel_imports(text, pkg_dir.name) and kind != "exec":
            out.append(f"{name}（{kind}）：②′ import runner 的檔須登記為 exec")
        if kind in ("rw", "exec") and nets:
            out.append(f"{name}（{kind}）：不得 import 網路模組")
        if kind == "ro" and name not in closure:  # P3 R132：ro 檔不得相對 import 非 ro 檔
            out += [f"{name}（ro）：相對 import 非 ro 檔 {d}.py（{registry[f'{d}.py']}）"
                    for d in sorted(_rel_imports(text, pkg_dir.name))
                    if registry.get(f"{d}.py") not in ("ro", None)]
        if "set_maturity" in {ast.unparse(n.func).split(".")[-1] for n in ast.walk(
                ast.parse(text)) if isinstance(n, ast.Call)}:
            out.append(f"{name}：含對 set_maturity 的呼叫（SDD 規則退役只經人工）")
    for name in sorted(files):
        text = (pkg_dir / name).read_bytes().decode("utf-8")
        out += [f"{name}：④ 禁字樣 {pat.replace(chr(92), '')}" for pat in forbidden_hits(text)]
        out += [f"{name}：平台守衛 {site} 須在 sys.platform 守衛內"
                for site in unguarded_sites(text)]
    out += _closure_problems(pkg_dir, registry, files, closure)
    out += _entry_problems(pkg_dir, registry, entry_file)
    return out


def unguarded_sites(text: str) -> list[str]:
    """`taskkill` 字面與 `os.killpg` 呼叫須落在條件含 `sys.platform` 的 `if` 作用域內。"""
    tree = ast.parse(text)
    parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}

    def guarded(node) -> bool:
        while node in parent:
            node = parent[node]
            if isinstance(node, ast.If) and "sys.platform" in ast.unparse(node.test):
                return True
        return False
    out = []
    for node in ast.walk(tree):
        is_kill = (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "killpg")
        is_taskkill = isinstance(node, ast.Constant) and node.value == "taskkill"
        if (is_kill or is_taskkill) and not guarded(node):
            out.append("os.killpg" if is_kill else "taskkill")
    return out


def _closure_problems(
    pkg_dir: Path, registry: dict[str, str], files: set[str], closure
) -> list[str]:
    pkg, out = pkg_dir.name, []
    for start in closure:
        if start not in files:
            continue
        seen, todo = set(), [start]
        while todo:
            cur = todo.pop()
            if cur in seen or cur not in files:
                continue
            seen.add(cur)
            if cur != start:
                continue  # 只判起點的直接 import；ro 中繼檔的相對 import 由 ro 直接 import 規則判
            deps = _rel_imports((pkg_dir / cur).read_bytes().decode("utf-8"), pkg)
            todo += [f"{d}.py" for d in deps]
        out += [
            f"{start}：唯讀動詞的 import 閉包含非 ro 檔 {n}"
            for n in sorted(seen)
            if registry.get(n) not in ("ro", None)
        ]
    return out


def _entry_problems(pkg_dir: Path, registry: dict[str, str], entry_file: Path) -> list[str]:
    pkg, out = pkg_dir.name, []
    tree = ast.parse(entry_file.read_bytes().decode("utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            text = ast.unparse(node)
            for dep in _rel_imports(text, pkg):
                if registry.get(f"{dep}.py") not in ("ro", None):
                    out.append(f"入口模組層級 import 了非 ro 的 {dep}.py")
    return out


def forbidden_hits(text: str) -> list[str]:
    return [p for p, rx in zip(FORBIDDEN, FORBIDDEN_RES) if rx.search(text)]


def make_pkg(files: dict[str, str], registry: dict[str, str], entry: str) -> tuple[Path, Path]:
    root = fx.new_dir("pkg")
    pkg = root / "lib" / "mypkg"
    pkg.mkdir(parents=True)
    for n, text in files.items():
        (pkg / n).write_bytes(text.encode("utf-8"))
    entry_file = root / "entry.py"
    entry_file.write_bytes(entry.encode("utf-8"))
    return pkg, entry_file


LEGAL_FILES = {
    "a.py": "X = 1\n",
    "w.py": "from pathlib import Path\n\n\ndef f(p):\n    Path(p).write_text('x')\n",
    "f.py": "import urllib\n",
    "r.py": "from . import f\n",
    "check.py": "from . import a\n",
    "runner.py": "import subprocess\n",
    "v.py": "from . import runner\n",
}
LEGAL_REG = {"a.py": "ro", "w.py": "rw", "f.py": "net", "r.py": "net", "check.py": "ro",
             "runner.py": "exec", "v.py": "exec"}
LEGAL_ENTRY = (
    "from lib.mypkg import check\n\n\ndef handler():\n    from lib.mypkg import w\n    return w\n"
)


def synth(files=None, registry=None, entry=None) -> list[str]:
    pkg, entry_file = make_pkg({**LEGAL_FILES, **(files or {})}, registry, entry or LEGAL_ENTRY)
    reg = dict(LEGAL_REG if registry is None else registry)
    return capability_problems(pkg, reg, entry_file, net_file="f.py", git_file="g.py")


class TestCapabilityRegistry(unittest.TestCase):
    def test_AT_143_1_1_real_tree_matches_registry(self):
        self.assertEqual(capability_problems(PKG, CAPABILITY, ENTRY), [])
        names = {p.name for p in PKG.glob("*.py")}
        self.assertEqual(names, set(CAPABILITY))
        counts = {k: sum(1 for v in CAPABILITY.values() if v == k) for k in CATEGORIES}
        self.assertEqual(counts, {"ro": 39, "rw": 8, "net": 2, "exec": 2})
        self.assertEqual({n for n, k in CAPABILITY.items() if k == "exec"}, {"runner.py",
            "verify.py"})
        net_importers, subproc = set(), set()
        for n in names:
            text = (PKG / n).read_bytes().decode("utf-8")
            if _abs_imports(text) & NET_MODULES:
                net_importers.add(n)
            if "subprocess" in text:
                subproc.add(n)
        self.assertEqual(net_importers, {"fetch.py"})
        self.assertEqual(subproc, {"git.py", "runner.py"})
        runner_users = {n for n in names if "runner" in _rel_imports(
            (PKG / n).read_bytes().decode("utf-8"), "selfimproving")}
        self.assertTrue(all(CAPABILITY[n] == "exec" for n in runner_users), runner_users)
        for start in CLOSURE_ONLY_RO:
            seen, todo = set(), [start]
            while todo:
                cur = todo.pop()
                if cur not in seen:
                    seen.add(cur)
                    todo += [
                        f"{d}.py"
                        for d in _rel_imports(
                            (PKG / cur).read_bytes().decode("utf-8"), "selfimproving"
                        )
                        if (PKG / f"{d}.py").is_file()
                    ]
            self.assertTrue(all(CAPABILITY[n] == "ro" for n in seen), (start, seen))
        entry_tree = ast.parse(ENTRY.read_bytes().decode("utf-8"))
        top_deps = set()
        for node in entry_tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                top_deps |= _rel_imports(ast.unparse(node), "selfimproving")
        self.assertTrue(all(CAPABILITY[f"{d}.py"] == "ro" for d in top_deps), top_deps)
        lazy = ENTRY.read_bytes().decode("utf-8")
        self.assertIn("import writeverbs", lazy.split("def _write", 1)[1])
        self.assertIn("import research", lazy.split("def _research", 1)[1])

    def test_AT_143_1_E_1_synthetic_violations_are_flagged(self):
        self.assertEqual(synth(), [])
        mutations = {
            "a 多一個未登記的檔": dict(files={"x.py": "Y = 2\n"}),
            "b 登記表有鍵而檔不存在": dict(registry={**LEGAL_REG, "ghost.py": "ro"}),
            "c ro 檔含 write_text(": dict(files={"a.py": "def f(p):\n    p.write_text('x')\n"}),
            "d ro 檔含 subprocess": dict(files={"a.py": "import subprocess\n"}),
            "e ro 檔 import socket": dict(files={"a.py": "import socket\n"}),
            "f rw 檔 import urllib": dict(files={"w.py": "import urllib\n"}),
            "g rw 檔含 subprocess": dict(files={"w.py": "import subprocess\n"}),
            "h net 類 r.py 直接 import http": dict(files={"r.py": "import http\n"}),
            "i check.py 相對 import rw": dict(files={"check.py": "from . import w\n"}),
            "j status 傳遞性閉包越界": dict(
                files={"status.py": "from . import fold\n", "fold.py": "from . import w\n"},
                registry={**LEGAL_REG, "status.py": "ro", "fold.py": "ro"},
            ),
            "k 入口模組層級 import rw": dict(entry="from lib.mypkg import w\n"),
            "l import 第三方 yaml": dict(files={"a.py": "import yaml\n"}),
            "m 類別值為 xx": dict(registry={**LEGAL_REG, "a.py": "xx"}),
            "n ro 檔 import runner（②′）": dict(files={"a.py": "from . import runner\n"}),
            "o rw 檔 import runner": dict(files={"w.py": "from . import runner\n"}),
            "p exec 檔 import socket": dict(files={"v.py": "import socket\n"}),
            "q exec 的 v.py 含 subprocess（只准 runner）":
                dict(files={"v.py": "import subprocess\n"}),
            "r check 的 import 閉包含 exec": dict(files={"check.py": "from . import v\n"}),
            "s 入口模組層級 import exec": dict(entry="from lib.mypkg import v\n"),
        }
        for label, kw in mutations.items():
            with self.subTest(label):
                problems = synth(**kw)
                self.assertTrue(problems, label)
                self.assertTrue(any(re.search(r"\.py|入口|登記", p) for p in problems), problems)


class TestExecRegistry(unittest.TestCase):
    P2_RO = ("transcript", "decgrammar", "decverify", "cooldown", "heldout", "manifest", "verdict",
             "consoleaudit", "obsrows", "decheck")

    def test_AT_240_5_1_exec_registry(self):
        self.assertEqual(capability_problems(PKG, CAPABILITY, ENTRY), [])
        self.assertEqual(len(CAPABILITY), 51)
        self.assertEqual({CAPABILITY[f"{n}.py"] for n in self.P2_RO}, {"ro"})
        self.assertEqual({CAPABILITY[f"{n}.py"] for n in ("decwrite", "sandbox", "promote",
                                                          "obswrite")}, {"rw"})
        self.assertEqual({CAPABILITY[f"{n}.py"] for n in ("runner", "verify")}, {"exec"})
        texts = {p.name: p.read_bytes().decode("utf-8") for p in PKG.glob("*.py")}
        self.assertEqual({n for n, t in texts.items() if "subprocess" in t}, {"git.py",
            "runner.py"})
        self.assertEqual({n for n, t in texts.items() if "runner" in _rel_imports(t,
            "selfimproving")},
                         {"verify.py"})
        self.assertTrue(all(not forbidden_hits(t) for t in texts.values()))
        self.assertEqual(unguarded_sites(texts["runner.py"]), [])
        self.assertIn('getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)', texts["runner.py"])
        self.assertNotIn("subprocess.CREATE_NEW_PROCESS_GROUP", texts["runner.py"].replace(
            'getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)', ""))

    def test_AT_240_5_E_1_injections_are_caught(self):
        import shutil
        control = fx.new_dir("pkgc")
        shutil.copytree(PKG, control)
        self.assertEqual(capability_problems(control, CAPABILITY, ENTRY), [])

        def copy_with(**edits):
            dest = fx.new_dir("pkgi")
            shutil.copytree(PKG, dest)
            for name, fn in edits.items():
                path = dest / f"{name}.py"
                old = path.read_text(encoding="utf-8") if path.exists() else ""
                path.write_text(fn(old), encoding="utf-8")
            return dest
        add = lambda line: (lambda t: t.rstrip("\n") + "\n" + line + "\n")  # noqa: E731
        cases = [
            ("a", dict(newmod=lambda t: "X = 1\n"), "newmod.py", "未登記", None),
            ("b", dict(manifest=add("import subprocess")), "manifest.py", "subprocess", None),
            ("c", dict(decverify=add("from . import runner")), "decverify.py", "②′", None),
            ("d", dict(promote=add("from . import runner")), "promote.py", "②′", None),
            ("e", dict(check=add("from . import sandbox")), "check.py", "import 閉包", None),
            ("f", dict(runner=add("import urllib.request")), "runner.py", "網路模組", None),
            ("g", dict(runner=add("time.sleep(1)")), "runner.py", "time.sleep", None),
            ("h", dict(verify=add("while True:\n    break")), "verify.py", "while", None),
            ("i", dict(runner=add('subprocess.run(["taskkill", "/F"])')), "runner.py", "taskkill",
            None),
            ("j", dict(runner=add("os.killpg(1, 9)")), "runner.py", "os.killpg", None),
            ("k", {}, "verify.py", "②′", {**CAPABILITY, "verify.py": "rw"}),
        ]
        for label, edits, name, needle, registry in cases:
            with self.subTest(label):
                pkg = copy_with(**edits)
                problems = capability_problems(pkg, registry or CAPABILITY, ENTRY)
                hit = [p for p in problems if name in p and needle in p]
                self.assertTrue(hit, (label, problems))

    def test_AT_240_5_E_2_runner_static_invariants(self):
        import io
        texts = {n: (PKG / f"{n}.py").read_text(encoding="utf-8") for n in ("runner", "verify")}
        tree = ast.parse(texts["runner"])
        popens = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and ast.unparse(n.func).endswith("Popen")]
        self.assertTrue(popens)
        for call in popens:
            shell = [k.value for k in call.keywords if k.arg == "shell"]
            self.assertTrue(not shell or (isinstance(shell[0],
                ast.Constant) and shell[0].value is False))
        comms = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and ast.unparse(n.func).endswith("communicate")]
        self.assertTrue(any(k.arg == "timeout" for c in comms for k in c.keywords))
        for name, text in texts.items():
            consts = {n.value for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Constant)
                      and isinstance(n.value, str)}
            self.assertFalse({"-I", "-P"} & consts, name)
            self.assertNotIn("dict(os.environ)", text)
            self.assertNotIn("os.environ.copy()", text)
        import test_platform_neutral_paths as root_tests
        suite = unittest.TestSuite()
        for cls in ("TestForeignExecutableArgvIsGuarded", "TestForeignPlatformApiIsGuarded",
                    "TestForeignApiVocabularyOnlyGrows"):
            suite.addTests(unittest.TestLoader().loadTestsFromTestCase(getattr(root_tests, cls)))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        for table in ("_FOREIGN_EXE_ARGV_DEBT", "_FOREIGN_API_SCOPE_DEBT"):
            keys = getattr(root_tests, table)
            self.assertFalse([k for k in keys if "selfimproving" in str(k).lower()], table)


class TestDynamicPurity(SiTestCase):
    def loaded_modules(self, argv, repo=None) -> list[str]:
        code = (
            "import sys, json\nsys.path.insert(0, sys.argv[1])\nimport selfimproving\n"
            "if len(sys.argv) > 2:\n    selfimproving.main(json.loads(sys.argv[2]))\n"
            "sys.stdout.write('\\n@@MODS@@' + json.dumps(sorted(m for m in sys.modules "
            "if m.startswith('lib.selfimproving.'))))\n"
        )
        args = [sys.executable, "-c", code, str(TOOLS)] + ([json.dumps(argv)] if argv else [])
        env = {**fx.genv(), "AUTOSDD_SI_DIR": str(self.home)}
        cp = subprocess.run(args, capture_output=True, encoding="utf-8", env=env, check=False)
        self.assertIn("@@MODS@@", cp.stdout, cp.stderr)
        return json.loads(cp.stdout.split("@@MODS@@")[1])

    def sc_export(self) -> Path:
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
        rc, out, err = self.prop(repo, rid(1), "P")
        self.assertEqual(rc, 0, out + err)
        fx.commit_all(repo, "sc-export")
        return repo

    def test_AT_143_1_E_2_dynamic_purity_and_forbidden_words(self):
        repo = self.sc_export()
        heavy = (
            "lib.selfimproving.evwrite",
            "lib.selfimproving.propfiles",
            "lib.selfimproving.writeverbs",
            "lib.selfimproving.fetch",
            "lib.selfimproving.research",
        )
        for argv in (
            ["check"],
            ["status"],
            ["scan"],
            ["export", "--json", "--kind", "status"],
            ["card", pid(124)],
        ):
            with self.subTest(argv=argv):
                mods = self.loaded_modules([*argv, "--repo", str(repo)])
                self.assertEqual([m for m in mods if m in heavy], [], argv)
        self.assertEqual([m for m in self.loaded_modules([]) if m in heavy], [])
        # 全部動詞零網路
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("連線")):
            run = self.cli_ok(
                repo, "run-open", "--trigger", "b", "--coord", "tools/a.py:2", "--by", "main"
            )
            rid2 = re.search(r"id=(\S+)", run).group(1)
            self.cli_ok(
                repo, "research", "--skip", "--run", rid2, "--reason", "offline", "--note", "離線"
            )
            self.cli_ok(
                repo,
                "attr",
                "--type",
                "root",
                "--by",
                "SA",
                "--obs",
                obs_id(2),
                "--item",
                "DOC=docs/06_quality/",
                "--root-cause",
                "docs/stale-two",
            )
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
            self.cli_ok(repo, "attr-confirm", "--att", aid(2), "--by", "QA")
            self.cli_ok(repo, "attr-reject", "--att", aid(3), "--by", "QA", "--note", "證據不足")
            args = fx.good_prop_args(repo, "D", sources=[obs_id(1)])
            self.cli_ok(repo, "prop-new", "--run", rid2, *args)
            real = [e for e in fx.EV(repo) if e["kind"] == "prop" and e["id"] == pid(124)][0]
            fx.append_events(repo, [fx.dec_ev(124, "return", digest=real["digest"])])  # R107 (c)
            self.cli_ok(
                repo, "prop-revise", "--run", rid2, "--prop", pid(124), *fx.revise_args(repo, "P")
            )
            for argv in (
                ["status"],
                ["scan"],
                ["card", pid(124)],
                ["check"],
                ["export", "--json", "--kind", "events"],
            ):
                rc, out, err = self.M(repo, *argv)
                self.assertIn(rc, (0, 1, 2), (argv, out, err))
            self.cli_ok(repo, "run-close", "--run", rid2, "--by", "main")
        for path in [ENTRY, *PKG.glob("*.py")]:
            self.assertEqual(forbidden_hits(path.read_bytes().decode("utf-8")), [], path.name)
        for sample, pattern in zip(FORBIDDEN_SAMPLES, FORBIDDEN):
            self.assertEqual(forbidden_hits(sample)[:1], [pattern], sample)
        settings = (fx.ROOT / ".claude/settings.json").read_bytes().decode("utf-8")
        self.assertNotIn("selfimproving", settings.lower())
        before, st0 = fx.snap(repo)
        self.cli_ok(repo, "check")
        after, st1 = fx.snap(repo)
        self.assertEqual((before, st0), (after, st1))
        res = self.check(repo)
        self.assertEqual(res["_rc"], 0)
        self.assertEqual(len(res["items"]), 33)
        calls: list[list[str]] = []
        real_run = subprocess.run

        def spy(argv, *a, **kw):
            calls.append(list(argv))
            return real_run(argv, *a, **kw)

        with mock.patch.object(subprocess, "run", side_effect=spy):
            self.check(repo)
        self.assertTrue(calls and all(c[0] == "git" for c in calls), calls[:3])




class TestP3Registry(unittest.TestCase):
    """P3 的能力登記（TCS-P3 R132；AT-340-4-2、AT-340-4-E-2）。"""

    P3_RO = ("mea", "meastat", "meacheck", "capacity", "retire", "churn")

    def test_AT_340_4_2_p3_registry_closure_and_load_surface(self):
        self.assertEqual(capability_problems(PKG, CAPABILITY, ENTRY), [])
        names = {p.name for p in PKG.glob("*.py")}
        self.assertEqual(names, set(CAPABILITY))
        counts = tuple(sum(1 for v in CAPABILITY.values() if v == k) for k in CATEGORIES)
        optional = (PKG / "meaplan.py").exists()
        self.assertEqual((len(CAPABILITY), counts),
                         (51, (39, 8, 2, 2)) if optional else (50, (38, 8, 2, 2)))
        for n in (*self.P3_RO, *(("meaplan",) if optional else ())):
            self.assertEqual(CAPABILITY[f"{n}.py"], "ro", n)
        self.assertEqual(CAPABILITY["meawrite.py"], "rw")
        self.assertEqual({n for n, k in CAPABILITY.items() if k == "exec"}, {"runner.py",
                                                                              "verify.py"})
        self.assertEqual(sorted(p for p, _ in forbid_calls(PKG, ENTRY)), [])
        loaded = {
            "status": ["status", "--repo"], "export": ["export", "--kind", "events", "--json",
                                                       "--repo"],
            "check": ["check", "--repo"], "card": ["card", fx.pid(1), "--repo"],
            "scan": ["scan", "--repo"], "capacity": ["capacity", "--repo"],
        }
        tmp = fx.new_dir("surf")
        tmp.mkdir()
        for label, argv in loaded.items():
            mods = importtime_modules([*argv, str(tmp)], ENTRY)
            self.assertFalse(mods & {"meawrite", "runner", "verify"}, (label, mods))
        probe = fx.ROOT / "tools" / "probe" / "selfimproving_measure.py"
        mods = importtime_modules(["--repo", str(tmp)], probe)
        self.assertFalse(mods & {"meawrite", "runner", "verify"}, mods)
        for path in [*PKG.glob("*.py"), ENTRY]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for fn_or_mod in [tree, *[n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]]:
                if fn_or_mod is tree:
                    for node in tree.body:
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            self.assertNotIn("meawrite", ast.unparse(node), path.name)

    def test_AT_340_4_E_2_registry_check_has_teeth(self):
        def copy_pkg(**edits):
            root = fx.new_dir("q")
            pkg = root / "lib" / "selfimproving"
            pkg.mkdir(parents=True)
            for p in PKG.glob("*.py"):
                text = p.read_text(encoding="utf-8")
                pkg.joinpath(p.name).write_text(edits.get(p.stem, text) if p.stem not in edits
                                                else text + edits[p.stem], encoding="utf-8")
            for k, v in edits.items():
                if not (pkg / f"{k}.py").exists():
                    (pkg / f"{k}.py").write_text(v, encoding="utf-8")
            entry = root / "entry.py"
            entry.write_bytes(ENTRY.read_bytes())
            return pkg, entry

        reg = dict(CAPABILITY)
        pkg, entry = copy_pkg()
        self.assertEqual(capability_problems(pkg, reg, entry), [])
        injections = {
            "mea": ("\nfrom . import meawrite\n", "mea.py", "meawrite"),
            "capacity": ("\nimport subprocess\n", "capacity.py", "subprocess"),
            "retire": ("\n\ndef _x():\n    set_maturity('a')\n", "retire.py", "set_maturity"),
            "extra": ("X = 1\n", "extra.py", "未登記"),
            "status": ("\nfrom . import meawrite\n", "status.py", "meawrite"),
            "churn": ("\nimport rule_loader\n", "churn.py", "rule_loader"),
        }
        for key, (code, fname, cause) in injections.items():
            with self.subTest(key):
                pkg, entry = copy_pkg(**{key: code})
                got = capability_problems(pkg, reg, entry)
                self.assertEqual(len(got), 1, got)
                self.assertIn(fname, got[0])
                self.assertIn(cause, got[0])


def forbid_calls(pkg: Path, entry: Path) -> list[tuple[str, str]]:
    """套件與入口對 `set_maturity` 的呼叫、對 `rule_loader`／`fsm_runtime` 的 import（AST）。"""
    out = []
    for p in [*pkg.glob("*.py"), entry]:
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and ast.unparse(n.func).split(".")[-1] == "set_maturity":
                out.append((p.name, "set_maturity"))
            mods = ([a.name for a in n.names] if isinstance(n, ast.Import)
                    else [n.module or ""] if isinstance(n, ast.ImportFrom) else [])
            out += [(p.name, m) for m in mods if m.split(".")[0] in ("rule_loader", "fsm_runtime")]
    return out


def importtime_modules(argv: list[str], script: Path) -> set[str]:
    """`python -X importtime <script> <argv>` 載入的 `selfimproving.<名>` 模組集合。"""
    cp = subprocess.run([sys.executable, "-X", "importtime", str(script), *argv],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env={**__import__("os").environ, **fx.hermetic(), "PYTHONUTF8": "1"})
    names = set()
    for ln in cp.stderr.splitlines():
        if ln.startswith("import time:") and "|" in ln:
            parts = ln.rsplit("|", 1)[1].strip().split(".")
            if len(parts) >= 2 and parts[-2] == "selfimproving":
                names.add(parts[-1])
    return names

if __name__ == "__main__":
    unittest.main()
