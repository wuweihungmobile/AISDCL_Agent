"""SelfImproving P1 能力登記與純度判準（TCS-SelfImproving-P1 R63、R64；AT-143 系列）。

登記表 `CAPABILITY` 住本檔（24 個鍵：19 `ro`、3 `rw`、2 `net`）；判準函式 `capability_problems`
取參數（套件目錄、登記表、入口檔），故真樹與合成樹用同一份碼自證。這不是新增守衛碼：測試檔在
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
        )
    },
    **{f"{n}.py": "rw" for n in ("evwrite", "propfiles", "writeverbs")},
    **{f"{n}.py": "net" for n in ("fetch", "research")},
}
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
    closure=CLOSURE_ONLY_RO,
) -> list[str]:
    out: list[str] = []
    files = {p.name for p in pkg_dir.glob("*.py")}
    out += [f"{n}：未登記（新檔須先登記類別）" for n in sorted(files - set(registry))]
    out += [f"{n}：登記表有鍵而檔不存在" for n in sorted(set(registry) - files)]
    out += [
        f"{n}：類別 {k!r} 不在 ro／rw／net"
        for n, k in registry.items()
        if k not in ("ro", "rw", "net")
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
        if "subprocess" in text and (kind == "rw" or (kind == "ro" and name != git_file)):
            out.append(f"{name}（{kind}）：subprocess 字樣只准出現在 {git_file}")
        if kind == "rw" and nets:
            out.append(f"{name}（rw）：不得 import 網路模組")
    out += _closure_problems(pkg_dir, registry, files, closure)
    out += _entry_problems(pkg_dir, registry, entry_file)
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
}
LEGAL_REG = {"a.py": "ro", "w.py": "rw", "f.py": "net", "r.py": "net", "check.py": "ro"}
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
        counts = {k: sum(1 for v in CAPABILITY.values() if v == k) for k in ("ro", "rw", "net")}
        self.assertEqual(counts, {"ro": 19, "rw": 3, "net": 2})
        net_importers, subproc = set(), set()
        for n in names:
            text = (PKG / n).read_bytes().decode("utf-8")
            if _abs_imports(text) & NET_MODULES:
                net_importers.add(n)
            if "subprocess" in text:
                subproc.add(n)
        self.assertEqual(net_importers, {"fetch.py"})
        self.assertEqual(subproc, {"git.py"})
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
        }
        for label, kw in mutations.items():
            with self.subTest(label):
                problems = synth(**kw)
                self.assertTrue(problems, label)
                self.assertTrue(any(re.search(r"\.py|入口|登記", p) for p in problems), problems)


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
            fx.append_events(repo, [fx.dec_ev(124, "return")])
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
        self.assertEqual(len(res["items"]), 28)
        calls: list[list[str]] = []
        real_run = subprocess.run

        def spy(argv, *a, **kw):
            calls.append(list(argv))
            return real_run(argv, *a, **kw)

        with mock.patch.object(subprocess, "run", side_effect=spy):
            self.check(repo)
        self.assertTrue(calls and all(c[0] == "git" for c in calls), calls[:3])


if __name__ == "__main__":
    unittest.main()
