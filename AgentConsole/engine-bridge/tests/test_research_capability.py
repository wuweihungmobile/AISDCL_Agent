"""研究面的能力登記（TCS AT-960-8-8；PRD §9.4 機械鎖 ④；AC-R2P-04-4）。

登記表 `CAPABILITY` 住本檔：鍵＝相對 `app/` 的 posix 路徑，值＝四類之一（體例同根層
`tools/tests/test_selfimproving_capability.py`）：
  ro    不寫任何東西（無寫檔與建目錄形態），不碰子行程與網路
  rw    可寫檔案與資料庫；不碰子行程與網路
  net   可用網路庫；只准住在 `research/fetch/` 之下（PKG-BR-B 補登記列）
  exec  可驅動子行程（自己 Popen，或經 FSM 子行程的門 `sdd_cli`／`fsm_ops`／`orchestrator`／
        `gitops`）；也可寫檔
  vcs   git／gh 子行程的**唯一出口**（P1；只有 `research/gitops.py` 可登記）：可 Popen
        （經 procutil）、可寫檔、不碰網路庫；git／gh 的 argv 字面只准出現在這一類
        （ADR-003 D16＋D-99）

掃描範圍＝`app/research/**` 與 `app/routers/research.py`（研究面的全部原始碼）。判準函式
`capability_problems(app_dir, registry)` 取參數，所以真樹與合成違規樹用同一份碼自證。這不是
新增守衛碼：測試檔不在守衛面清單、不是 hook。

新增研究面模組的人（BR-B 的 `fetch/`；BR-C 的 `orchestrator`、`compile/`、`gates/`、
`gate_cli`）必須在 `CAPABILITY` 加一列——未登記就是紅，這是設計、不是誤報。

誠實劃界（AST 只看字面）：
  · `git`／`gh` 只認 argv 字面（list／tuple 首元素；整個元素都是工具名的清單不算），以變數
    組 argv 的繞法由「非 exec 模組不得有 subprocess」那條擋；`shutil.which("git")` 是 PATH
    查詢、不是子行程，不算。
  · `urllib` 整個族群（含 `urllib.parse`）都算網路庫（TCS 字面）；要解析網址請放 `fetch/`。
  · 這裡的 exec 登記與 `test_research_ast_locks.py` 的 `EXEC_MODULES` 是兩件事：前者＝「可
    驅動子行程」（含經門），後者＝「可 Popen 的模組」（只有真的 Popen 的）。新增會 Popen 的研究
    面模組要兩處都登記。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.test_research_ast_locks import call_name, owner_name
from tests.test_sdd_integration_parity import write_shaped_calls

APP_DIR = Path(__file__).resolve().parents[1] / "app"
SURFACE_GLOBS = ("research/**/*.py", "routers/research*.py")
FETCH_AREA = "research/fetch/"
CATEGORIES = ("ro", "rw", "net", "exec", "vcs")
VCS_MODULE = "research/gitops.py"

#: fsm_ops 與路由骨架自己不 Popen，而是經 `sdd_cli` 的研究面入口驅動 FSM CLI 子行程 ⇒ exec。
CAPABILITY: dict[str, str] = {
    "research/__init__.py": "ro",
    "research/settings.py": "ro",
    "research/export.py": "ro",
    "research/layout.py": "rw",
    "research/outbox.py": "rw",
    "research/db.py": "rw",
    "research/fsm_ops.py": "exec",
    "routers/research.py": "exec",
    # PKG-BR-B：抓取器。`__init__` 只落地原文檔（寫檔、無網路庫）＝rw；其餘模組用 httpx／socket／
    # urllib（連 `urllib.parse` 的字串解析也算，TCS 字面）＝net，且只准住在 fetch/ 之下。
    "research/fetch/__init__.py": "rw",
    "research/fetch/allowlist.py": "net",
    "research/fetch/http.py": "net",
    "research/fetch/arxiv.py": "net",
    "research/fetch/semantic_scholar.py": "net",
    "research/fetch/github.py": "net",
    "research/fetch/stackexchange.py": "net",
    # PKG-BR-C：編譯層與 gate evaluator 是純函式（只讀框架 YAML 與工作區檔案；寫檔、建 run、
    # 驅動 FSM 都在 orchestrator）＝ro；`gate_cli` 是引擎的 evaluator 子行程入口，只讀檔、印出違規。
    "research/compile/__init__.py": "ro",
    "research/compile/personas.py": "ro",
    "research/compile/playbooks.py": "ro",
    "research/compile/prompts.py": "ro",
    "research/gates/__init__.py": "ro",
    "research/gates/schemas.py": "ro",
    "research/gates/evidence.py": "ro",
    "research/gates/prd_schema.py": "ro",
    "research/gates/review_card.py": "ro",
    "research/gates/aggregate.py": "ro",
    "research/gate_cli.py": "ro",
    "research/gates/ingest.py": "ro",
    "research/gates/reconcile.py": "ro",
    # D-78／INT-06：劇本模式與 mock-only 的前置抓取離線夾具——只讀劇本與夾具檔、組成 `FetchBatch`，
    # 不 import 任何網路庫、不寫檔（原文落地與入庫仍在 orchestrator 的同一條路徑）。
    "research/offline.py": "ro",
    # orchestrator 不自己 Popen（引擎由 `RunManager` 起、FSM 由 `fsm_ops`→`sdd_cli` 起），但它是驅動
    # 這兩條子行程路徑的門：import fsm_ops 的模組一律須登記為 exec。
    "research/orchestrator.py": "exec",
    # P1 分流（BR-D1）：`gitops` 是 git／gh 的唯一出口（vcs）；`route`／`adopt` 經它與 fsm_ops
    # 驅動子行程（自己不 Popen）＝exec；`scaffold` 只寫檔（範本展開與工作區複製；無網路、無子行程）
    # ＝rw。
    "research/gitops.py": "vcs",
    "research/route.py": "exec",
    "research/adopt.py": "exec",
    "research/scaffold.py": "rw",
    "routers/research_route.py": "exec",
}

NET_ROOTS = frozenset({"socket", "ssl", "urllib", "urllib3", "httpx", "requests", "aiohttp",
                       "ftplib", "smtplib", "websockets"})
NET_DOTTED = ("http.client",)
NET_CALLS = frozenset({"urlopen", "open_connection", "create_connection", "getaddrinfo",
                       "start_server", "create_datagram_endpoint"})
SPAWN_MODULES = frozenset({"subprocess", "pty"})
SPAWN_FUNCS = frozenset({"Popen", "run", "call", "check_call", "check_output", "getoutput",
                         "getstatusoutput"})
OS_SPAWN = frozenset({"system", "popen", "startfile", "execl", "execle", "execlp", "execlpe",
                      "execv", "execve", "execvp", "execvpe", "spawnl", "spawnle", "spawnlp",
                      "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn",
                      "posix_spawnp"})
ASYNC_SPAWN = frozenset({"create_subprocess_exec", "create_subprocess_shell"})
COMMAND_CALLS = SPAWN_FUNCS | OS_SPAWN | ASYNC_SPAWN
GIT_GH = frozenset({"git", "gh", "git.exe", "gh.exe"})
EXEC_DOORS = frozenset({"sdd_cli", "fsm_ops", "orchestrator", "gitops"})
EXTRA_WRITE_NAMES = frozenset({"write_text_atomic", "mkdir", "makedirs", "rmdir", "rmtree"})

Target = tuple[int, str, bool]       # (行號, 點名, 是否絕對 import)


# ══ 判準函式（真樹與合成樹共用）═══════════════════════════════════════════════════════════
def import_targets(tree: ast.AST) -> list[Target]:
    """每個 import 敘述涉及的點名；`from a.b import c` 同時回 `a.b` 與 `a.b.c`（c 可能是子模組）。

    相對 import 只用來判「門」，不會被當成網路庫（本地模組可以叫 `http`）。
    """
    out: list[Target] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(node.lineno, alias.name, True) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base, absolute = node.module or "", node.level == 0
            if base:
                out.append((node.lineno, base, absolute))
            out += [(node.lineno, f"{base}.{alias.name}" if base else alias.name, absolute)
                    for alias in node.names]
    return out


def is_net_import(dotted: str) -> bool:
    return dotted.split(".")[0] in NET_ROOTS or any(
        dotted == name or dotted.startswith(name + ".") for name in NET_DOTTED)


def net_hits(tree: ast.AST, targets: list[Target]) -> list[str]:
    imported = {dotted for _, dotted, absolute in targets if absolute and is_net_import(dotted)}
    called = {call_name(node) for node in ast.walk(tree)
              if isinstance(node, ast.Call) and call_name(node) in NET_CALLS}
    return sorted(imported | called)


def uses_subprocess(tree: ast.AST, targets: list[Target]) -> bool:
    if any(absolute and dotted.split(".")[0] in SPAWN_MODULES for _, dotted, absolute in targets):
        return True
    return any((isinstance(node, ast.Name) and node.id == "Popen")
               or (isinstance(node, ast.Attribute) and node.attr == "Popen")
               for node in ast.walk(tree))


def forbidden_spawns(tree: ast.AST, targets: list[Target]) -> list[tuple[int, str]]:
    """任何模組（含 exec）都不准用的子行程形態：`os.system` 族與 asyncio 子行程。"""
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = call_name(node)
            if (owner_name(node) == "os" and name in OS_SPAWN) or name in ASYNC_SPAWN:
                out.append((node.lineno, name))
    out += [(line, dotted) for line, dotted, absolute in targets
            if absolute and dotted.startswith("os.") and dotted[3:] in OS_SPAWN]
    return out


def spawn_calls(tree: ast.AST) -> list[ast.Call]:
    """`subprocess.<spawn>(…)`（含 `import subprocess as sp` 與 `from subprocess import run`）。"""
    owners, bare = {"subprocess"}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            owners |= {alias.asname for alias in node.names
                       if alias.name == "subprocess" and alias.asname}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "subprocess":
            bare |= {alias.asname or alias.name for alias in node.names
                     if alias.name in SPAWN_FUNCS}
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and (
        (owner_name(node) in owners and call_name(node) in SPAWN_FUNCS)
        or (isinstance(node.func, ast.Name) and node.func.id in bare))]


def via_procutil(call: ast.Call) -> bool:
    return any(kw.arg is None and isinstance(kw.value, ast.Call)
               and call_name(kw.value) == "popen_platform_kwargs" for kw in call.keywords)


def _text(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def git_gh_lines(tree: ast.AST) -> list[int]:
    """git／gh 的 argv 字面：list／tuple 的首元素是工具名且整個清單不只有工具名；
    或把 `git …` 命令字串交給子行程呼叫。"""
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.List | ast.Tuple) and node.elts:
            words = [_text(elt) for elt in node.elts]
            only_names = all(w is not None and w.lower() in GIT_GH for w in words)
            if words[0] is not None and words[0].lower() in GIT_GH and not only_names:
                lines.append(node.lineno)
        elif isinstance(node, ast.Call) and node.args and call_name(node) in COMMAND_CALLS:
            head = (_text(node.args[0]) or "").split()[:1]
            if head and head[0].lower() in GIT_GH:
                lines.append(node.lineno)
    return sorted(lines)


def write_lines(tree: ast.AST) -> list[int]:
    """寫入形態（共用 `write_shaped_calls`）再加本專案的原子寫檔與建刪目錄原語。"""
    lines = {line for line, _label in write_shaped_calls(tree)}
    lines |= {node.lineno for node in ast.walk(tree)
              if isinstance(node, ast.Call) and call_name(node) in EXTRA_WRITE_NAMES}
    return sorted(lines)


def door_imports(targets: list[Target]) -> list[str]:
    return sorted({part for _, dotted, _absolute in targets for part in dotted.split(".")
                   if part in EXEC_DOORS})


def surface(app_dir: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for pattern in SURFACE_GLOBS:
        for path in app_dir.glob(pattern):
            if path.is_file():
                found[path.relative_to(app_dir).as_posix()] = path
    return found


def module_problems(rel: str, kind: str, tree: ast.AST) -> list[str]:
    out: list[str] = []
    targets = import_targets(tree)
    nets = net_hits(tree, targets)
    if nets and not (kind == "net" and rel.startswith(FETCH_AREA)):
        out.append(f"{rel}（{kind}）：網路能力 {nets} 只准出現在 {FETCH_AREA} 下標為 net 的模組")
    if kind == "net" and not rel.startswith(FETCH_AREA):
        out.append(f"{rel}：類別 net 的模組須住在 {FETCH_AREA} 之下")
    if kind not in ("exec", "vcs") and uses_subprocess(tree, targets):
        out.append(f"{rel}（{kind}）：subprocess／Popen 只准出現在標為 exec 的模組")
    if kind == "vcs" and rel != VCS_MODULE:
        out.append(f"{rel}：類別 vcs 只准登記給 {VCS_MODULE}（git／gh 子行程的唯一出口）")
    out += [f"{rel}:{line}：{what} 一律禁止（子行程只經 subprocess 加 procutil）"
            for line, what in forbidden_spawns(tree, targets)]
    if kind in ("exec", "vcs"):
        out += [f"{rel}:{call.lineno}（{kind}）：子行程呼叫缺 **procutil.popen_platform_kwargs()"
                for call in spawn_calls(tree) if not via_procutil(call)]
    if kind != "vcs":
        out += [f"{rel}:{line}：git／gh 的 argv 字面（只准出現在 {VCS_MODULE}）"
                for line in git_gh_lines(tree)]
    doors = door_imports(targets)
    if doors and kind != "exec":
        out.append(f"{rel}（{kind}）：import {doors}（FSM 子行程的門）的模組須登記為 exec")
    if kind == "ro" and (lines := write_lines(tree)):
        out.append(f"{rel}（ro）：含寫入形態（行 {lines}）")
    return out


def capability_problems(app_dir: Path, registry: dict[str, str]) -> list[str]:
    files = surface(app_dir)
    out = [f"{rel}：未登記（新模組須先在 CAPABILITY 登記類別；鍵＝相對 app/ 的路徑）"
           for rel in sorted(set(files) - set(registry))]
    out += [f"{rel}：登記表有鍵而檔不存在" for rel in sorted(set(registry) - set(files))]
    out += [f"{rel}：類別 {kind!r} 不在 ro／rw／net／exec"
            for rel, kind in sorted(registry.items()) if kind not in CATEGORIES]
    for rel in sorted(set(files) & set(registry)):
        tree = ast.parse(files[rel].read_text(encoding="utf-8"))
        out += module_problems(rel, registry[rel], tree)
    return out


# ══ 真樹 ═════════════════════════════════════════════════════════════════════════════════
def real_trees() -> dict[str, ast.Module]:
    return {rel: ast.parse(path.read_text(encoding="utf-8"))
            for rel, path in surface(APP_DIR).items()}


def test_AT_960_8_8_the_real_tree_is_registered_one_to_one_and_has_no_problems() -> None:
    files = surface(APP_DIR)
    assert len(files) >= 8, "鎖要有標的：BR-A 的七個套件模組加路由骨架至少八個"
    assert sorted(set(files) ^ set(CAPABILITY)) == [], "實樹與登記表必須一對一、每個模組恰登記一次"
    assert set(CAPABILITY.values()) <= set(CATEGORIES)
    assert CAPABILITY["research/fsm_ops.py"] == "exec", "fsm_ops 是研究面驅動 FSM 子行程的門"
    assert capability_problems(APP_DIR, CAPABILITY) == []


def test_AT_960_8_8_network_libraries_appear_only_in_net_modules_under_fetch() -> None:
    offenders = {}
    for rel, tree in real_trees().items():
        hits = net_hits(tree, import_targets(tree))
        if hits and not (CAPABILITY[rel] == "net" and rel.startswith(FETCH_AREA)):
            offenders[rel] = hits
    assert offenders == {}, "網路外呼只准在 app/research/fetch/ 下標為 net 的模組"
    assert all(rel.startswith(FETCH_AREA) for rel, kind in CAPABILITY.items() if kind == "net")


def test_AT_960_8_8_subprocess_and_popen_appear_only_in_exec_modules_through_procutil() -> None:
    for rel, tree in real_trees().items():
        targets = import_targets(tree)
        if uses_subprocess(tree, targets):
            assert CAPABILITY[rel] in ("exec", "vcs"), f"{rel} 用了 subprocess 卻不是 exec／vcs"
        assert forbidden_spawns(tree, targets) == [], rel
        assert all(via_procutil(call) for call in spawn_calls(tree)), rel
    # 非空證明：掃描器認得專案真正的子行程入口形態（`**procutil.popen_platform_kwargs()`）
    real_spawn = spawn_calls(ast.parse((APP_DIR / "sdd_cli.py").read_text(encoding="utf-8")))
    assert real_spawn and all(via_procutil(call) for call in real_spawn)


def test_AT_960_8_8_git_and_gh_argv_literals_live_only_in_gitops() -> None:
    """P1（AT-961-8-5）：原「研究面不呼叫 git 或 gh」改寫為「git／gh 的 argv 字面只准出現在
    `research/gitops.py`」；該檔須在實樹內真的有字面（鎖要有標的）。"""
    found = {rel for rel, tree in real_trees().items() if git_gh_lines(tree)}
    assert found == {VCS_MODULE}, found


# ══ 合成樹：同一份判準碼對違規逐一回報、對良性放行 ═══════════════════════════════════════════
def src(*lines: str) -> str:
    return "\n".join(lines) + "\n"


def spawner(call: str, *imports: str) -> str:
    """exec 模組的合成原始碼：函式 `go` 回傳 `call`。"""
    return src(*imports, "", "", "def go(argv):", f"    return {call}")


POPEN_OK = "subprocess.Popen(argv, **procutil.popen_platform_kwargs())"
GIT_CMD = "subprocess.run('git status', shell=True, **procutil.popen_platform_kwargs())"
USE_PROCUTIL = ("import subprocess", "from .. import procutil")

LEGAL_FILES: dict[str, str | None] = {
    "research/__init__.py": src('"""研究面。"""'),
    "research/settings.py": src("import shutil", "", "GIT = shutil.which('git')",
                                "TOOLS = ('git', 'gh')", "INFO = {'git': 1}"),
    "research/layout.py": src("from pathlib import Path", "", "", "def put(p: Path) -> None:",
                              "    p.parent.mkdir(parents=True, exist_ok=True)",
                              "    p.write_text('x', encoding='utf-8')"),
    "research/fetch/__init__.py": src('"""抓取。"""'),
    "research/fetch/client.py": src("import socket", "from urllib import request", "import httpx"),
    "research/fsm_ops.py": src("from .. import sdd_cli"),
    "research/orchestrator.py": spawner(POPEN_OK, *USE_PROCUTIL),
    "routers/research.py": src("import asyncio", "", "from ..research import fsm_ops"),
}
LEGAL_REGISTRY: dict[str, str | None] = {
    "research/__init__.py": "ro", "research/settings.py": "ro", "research/layout.py": "rw",
    "research/fetch/__init__.py": "ro", "research/fetch/client.py": "net",
    "research/fsm_ops.py": "exec", "research/orchestrator.py": "exec",
    "routers/research.py": "exec",
}


def synth(tmp_path: Path, files: dict[str, str | None] | None = None,
          registry: dict[str, str | None] | None = None) -> list[str]:
    """合法的合成樹套上補丁（值 None＝移除該鍵）後跑判準函式。"""
    app = tmp_path / "app"
    for rel, text in {**LEGAL_FILES, **(files or {})}.items():
        if text is not None:
            path = app / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    reg = {k: v for k, v in {**LEGAL_REGISTRY, **(registry or {})}.items() if v is not None}
    return capability_problems(app, reg)


# (id, 檔案補丁, 登記表補丁, 問題清單必含的字樣)
VIOLATIONS: list[tuple[str, dict[str, str | None], dict[str, str | None], str]] = [
    # 登記表與實樹不一致
    ("unregistered-module", {"research/extra.py": src("X = 1")}, {}, "未登記"),
    ("registry-misses-a-module", {}, {"research/layout.py": None}, "未登記"),
    ("registry-key-without-file", {}, {"research/ghost.py": "ro"}, "檔不存在"),
    ("registered-file-was-removed", {"research/layout.py": None}, {}, "檔不存在"),
    ("category-outside-the-four", {}, {"research/settings.py": "xx"}, "不在 ro"),
    # 網路
    ("httpx-outside-fetch", {"research/settings.py": src("import httpx")}, {}, "網路能力"),
    ("socket-in-a-fetch-module-registered-ro",
     {"research/fetch/__init__.py": src("import socket")}, {}, "網路能力"),
    ("net-category-outside-fetch", {}, {"research/settings.py": "net"}, "須住在"),
    ("urllib-request", {"research/settings.py": src("import urllib.request")}, {}, "網路能力"),
    ("http-client-by-from-import",
     {"research/settings.py": src("from http import client")}, {}, "網路能力"),
    ("requests", {"research/layout.py": src("import requests")}, {}, "網路能力"),
    ("aiohttp-in-an-exec-module", {"research/fsm_ops.py": src("import aiohttp")}, {}, "網路能力"),
    ("asyncio-open-connection", {"research/settings.py": spawner(
        "await asyncio.open_connection('x', 1)", "import asyncio")}, {}, "網路能力"),
    # 子行程
    ("popen-in-a-non-exec-module", {"research/layout.py": spawner(
        "subprocess.Popen(argv)", "import subprocess")}, {}, "只准出現在標為 exec"),
    ("subprocess-import-only", {"research/settings.py": src("import subprocess")}, {},
     "只准出現在標為 exec"),
    ("from-subprocess-import-run", {"research/settings.py": src("from subprocess import run")},
     {}, "只准出現在標為 exec"),
    ("popen-without-procutil", {"research/orchestrator.py": spawner(
        "subprocess.Popen(argv)", "import subprocess")}, {}, "popen_platform_kwargs"),
    ("run-without-procutil", {"research/orchestrator.py": spawner(
        "subprocess.run(argv, check=False)", "import subprocess")}, {}, "popen_platform_kwargs"),
    ("bare-run-without-procutil", {"research/orchestrator.py": spawner(
        "run(argv)", "from subprocess import run")}, {}, "popen_platform_kwargs"),
    ("aliased-subprocess-without-procutil", {"research/orchestrator.py": spawner(
        "sp.check_output(argv)", "import subprocess as sp")}, {}, "popen_platform_kwargs"),
    ("os-system-even-in-exec", {"research/orchestrator.py": spawner(
        "os.system(argv)", "import os")}, {}, "一律禁止"),
    ("asyncio-subprocess-even-in-exec", {"research/orchestrator.py": spawner(
        "await asyncio.create_subprocess_exec(argv)", "import asyncio")}, {}, "一律禁止"),
    ("from-os-import-system", {"research/orchestrator.py": src("from os import system")}, {},
     "一律禁止"),
    # git／gh
    ("git-argv-list", {"research/settings.py": src("CMD = ['git', 'status']")}, {}, "git／gh"),
    ("gh-argv-tuple", {"research/settings.py": src("CMD = ('gh', 'pr', 'list')")}, {}, "git／gh"),
    ("git-exe-argv", {"research/settings.py": src("CMD = ['GIT.EXE', 'log']")}, {}, "git／gh"),
    ("git-command-string-to-a-spawn",
     {"research/orchestrator.py": spawner(GIT_CMD, *USE_PROCUTIL)}, {}, "git／gh"),
    # ro 不寫
    ("ro-write-text", {"research/settings.py": src(
        "def f(p):", "    p.write_text('x', encoding='utf-8')")}, {}, "寫入形態"),
    ("ro-write-text-atomic", {"research/settings.py": src(
        "from .. import fsutil", "", "", "def f(p):", "    fsutil.write_text_atomic(p, 'x')")},
     {}, "寫入形態"),
    ("ro-mkdir", {"research/settings.py": src("def f(p):", "    p.mkdir(parents=True)")}, {},
     "寫入形態"),
    ("ro-open-for-write", {"research/settings.py": src(
        "def f(p):", "    return open(p, 'w', encoding='utf-8')")}, {}, "寫入形態"),
    # FSM 子行程的門
    ("non-exec-imports-sdd_cli", {"research/layout.py": src("from .. import sdd_cli")}, {},
     "須登記為 exec"),
    ("router-registered-rw-imports-fsm_ops", {}, {"routers/research.py": "rw"}, "須登記為 exec"),
    ("non-exec-imports-orchestrator",
     {"research/settings.py": src("from .orchestrator import go")}, {}, "須登記為 exec"),
]

# 良性變體：以下全部必須維持零問題（掃描器不得誤報）
BENIGN: list[tuple[str, dict[str, str | None]]] = [
    ("http-status-is-not-network", {"research/settings.py": src("from http import HTTPStatus")}),
    ("asyncio-sleep-is-not-network", {"research/settings.py": src(
        "import asyncio", "", "", "async def f():", "    await asyncio.sleep(0)")}),
    ("which-is-a-path-probe", {"research/settings.py": src(
        "import shutil", "", "A = shutil.which('git')", "B = shutil.which('gh')")}),
    ("tool-name-lists-are-not-argv", {"research/settings.py": src(
        "NAMES = ('git', 'gh')", "KEYS = ('mode', 'git', 'gh')", "INFO = {'git': 1, 'gh': 2}")}),
    ("ro-may-read", {"research/settings.py": src(
        "def f(p):", "    return p.read_text(encoding='utf-8')", "", "",
        "def g(p):", "    return open(p, encoding='utf-8')")}),
    ("exec-may-write", {"research/fsm_ops.py": src(
        "from .. import sdd_cli", "", "", "def f(p):", "    p.write_text('x', encoding='utf-8')")}),
    ("relative-module-named-http", {"research/settings.py": src("from . import http")}),
    ("aliased-popen-through-procutil", {"research/orchestrator.py": spawner(
        "sp.Popen(argv, **procutil.popen_platform_kwargs())",
        "import subprocess as sp", "from .. import procutil")}),
]


# P1（AT-961-8-5）：vcs 類別與 git／gh 字面的新規則
VIOLATIONS.extend([
    ("vcs-category-outside-gitops", {}, {"research/settings.py": "vcs"}, "只准登記給"),
    ("vcs-popen-without-procutil", {"research/gitops.py": spawner(
        "subprocess.Popen(argv)", "import subprocess")}, {"research/gitops.py": "vcs"},
     "popen_platform_kwargs"),
    ("git-literal-in-an-exec-module", {"research/orchestrator.py": src("CMD = ['git', 'status']")},
     {}, "只准出現在"),
    ("a-module-importing-gitops-must-be-exec", {"research/layout.py": src("from . import gitops")},
     {}, "須登記為 exec"),
    ("net-library-inside-gitops", {"research/gitops.py": src("import httpx")},
     {"research/gitops.py": "vcs"}, "網路能力"),
])


def test_AT_961_8_5_the_vcs_module_may_spawn_and_hold_git_literals(tmp_path: Path) -> None:
    gitops_src = src("import subprocess", "from .. import procutil", "", "", "def go(argv):",
                     "    return subprocess.Popen(['git', 'status'],",
                     "                            **procutil.popen_platform_kwargs())")
    assert synth(tmp_path, {"research/gitops.py": gitops_src},
                 {"research/gitops.py": "vcs"}) == []


def test_AT_961_8_5_an_unregistered_new_p1_module_is_reported(tmp_path: Path) -> None:
    problems = synth(tmp_path, {"research/route.py": src("X = 1"), "research/adopt.py": None})
    assert any("research/route.py：未登記" in p for p in problems), problems


def test_AT_960_8_8_the_legal_synthetic_tree_is_clean(tmp_path: Path) -> None:
    assert synth(tmp_path) == []


@pytest.mark.parametrize(
    ("files", "registry", "expect"),
    [pytest.param(files, registry, expect, id=case_id)
     for case_id, files, registry, expect in VIOLATIONS])
def test_AT_960_8_8_each_synthetic_violation_is_reported(
        tmp_path: Path, files: dict[str, str | None], registry: dict[str, str | None],
        expect: str) -> None:
    problems = synth(tmp_path, files, registry)
    assert any(expect in problem for problem in problems), (expect, problems)


@pytest.mark.parametrize(("files",), [pytest.param(files, id=case_id)
                                      for case_id, files in BENIGN])
def test_AT_960_8_8_benign_variants_are_not_reported(
        tmp_path: Path, files: dict[str, str | None]) -> None:
    assert synth(tmp_path, files) == []
