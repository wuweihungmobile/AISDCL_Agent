"""Bridge 對 SelfImproving 的唯讀不變量：原始碼的 AST 鎖（TCS-SelfImprovingMirror-P1b R6；
AT-932-2-1、AT-932-2-E-1）。

邊界型 M（形態判準）：`getattr`、動態拼接、`importlib` 以變數載入看不到；唯讀的「行為面」另由
test_si_export_differential.py 的操作序列前後零變動覆蓋。五項判準都是純函式（輸入是原始碼文字或
可呼叫物件，輸出是違規清單），對真原始碼必須回空、對各違規樣本必須逐一回非空並指出判準編號：
  判準 1 寫入形態呼叫：`si_cli.py`、`routers/si.py` 與原始碼含 `selfimproving`（不分大小寫）字樣的
         其他 `app/` 模組，零個寫入形態呼叫（掃描器自 test_sdd_integration_parity 匯入，不複製）
  判準 2 `app/` 全樹：不得 import `lib`／`tools`（含 `importlib` 對這兩名的字面呼叫），不得有任何
         對 `sys.path` 的變更（呼叫、賦值、增量賦值）
  判準 3 CLI 腳本的檔名字面在 `app/` 只出現在 `si_cli.py`
  判準 4 argv 動詞形態：`si_cli.py` 中組 argv 的函式恰一個、唯一 `return` 為列表字面值、索引 2 起
         的動詞落在白名單內；`Popen` 呼叫恰一處且其 argv 引數來自該函式
  判準 5 動態對照：對五個 kind 與全部旗標組合呼叫該函式，動詞位置恆在白名單內且不含 `--repo`
AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import ast
import importlib.util
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import app as app_package
from app import si_cli
from tests.test_sdd_integration_parity import write_shaped_calls

APP_DIR = Path(app_package.__file__).resolve().parent
SCRIPT_LITERAL = "selfimproving.py"
#: 動詞白名單（住在鎖的測試檔內）：`export` 是 P1b 唯一的動詞；`obs-add --dry-run` 為 P2b 預留，
#: P1b 的 `si_cli.py` 不得組出它。
ALLOWED_VERBS: frozenset[tuple[str, ...]] = frozenset({("export",), ("obs-add", "--dry-run")})
P1B_VERBS: frozenset[tuple[str, ...]] = frozenset({("export",)})
BANNED_ROOTS = frozenset({"lib", "tools"})
PATH_MUTATORS = frozenset(
    {"insert", "append", "extend", "remove", "pop", "clear", "sort", "reverse"})
KINDS = ("observations", "events", "proposals", "runs", "status")
FLAG_COMBOS: list[dict[str, Any]] = [
    {}, {"since": 3}, {"limit": 7}, {"since": 3, "limit": 7}, {"ident": "PROP-SI-004"}]


# ── 判準 1：寫入形態 ────────────────────────────────────────────────────────────────────────
def is_si_related(rel: str, source: str) -> bool:
    return rel in ("si_cli.py", "routers/si.py") or "selfimproving" in source.lower()


def crit1_writes(rel: str, source: str) -> list[str]:
    if not is_si_related(rel, source):
        return []
    return [f"判準1 {rel}:{line} 寫入形態呼叫 {what}"
            for line, what in write_shaped_calls(ast.parse(source))]


# ── 判準 2：import 與 sys.path ──────────────────────────────────────────────────────────────
def _is_sys_path(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "path"
            and isinstance(node.value, ast.Name) and node.value.id == "sys")


def crit2_imports(rel: str, source: str) -> list[str]:
    out: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            out += [f"判準2 {rel}:{node.lineno} import {a.name}" for a in node.names
                    if a.name.split(".")[0] in BANNED_ROOTS]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] in BANNED_ROOTS:
                out.append(f"判準2 {rel}:{node.lineno} from {node.module} import …")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            first = node.args[0] if node.args else None
            if (name in ("import_module", "__import__") and isinstance(first, ast.Constant)
                    and isinstance(first.value, str)
                    and first.value.split(".")[0] in BANNED_ROOTS):
                out.append(f"判準2 {rel}:{node.lineno} {name}({first.value!r})")
            if (isinstance(func, ast.Attribute) and _is_sys_path(func.value)
                    and func.attr in PATH_MUTATORS):
                out.append(f"判準2 {rel}:{node.lineno} sys.path.{func.attr}")
        elif isinstance(node, ast.Assign | ast.AugAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                base = target.value if isinstance(target, ast.Subscript) else target
                if _is_sys_path(base):
                    out.append(f"判準2 {rel}:{node.lineno} 變更 sys.path（賦值）")
    return out


# ── 判準 3：CLI 腳本檔名字面的位置 ───────────────────────────────────────────────────────────
def crit3_literal(rel: str, source: str) -> list[str]:
    if rel != "si_cli.py" and SCRIPT_LITERAL in source.lower():
        return [f"判準3 {rel} 含 CLI 腳本的檔名字面（只准 si_cli.py 出現）"]
    return []


# ── 判準 4：argv 動詞形態 ───────────────────────────────────────────────────────────────────
def _is_sys_executable(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "executable"
            and isinstance(node.value, ast.Name) and node.value.id == "sys")


def argv_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """組 argv 的函式：含有「首元素為 sys.executable 的列表字面值」者。"""
    return [fn for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
            and any(isinstance(n, ast.List) and n.elts and _is_sys_executable(n.elts[0])
                    for n in ast.walk(fn))]


def verb_of(elts: list[ast.expr]) -> tuple[str, ...] | None:
    """列表字面值索引 2 起的動詞：索引 2 須是字串常數；緊接其後的 `--dry-run` 常數併入動詞。"""
    if len(elts) < 3 or not (isinstance(elts[2], ast.Constant) and isinstance(elts[2].value, str)):
        return None
    verb = [elts[2].value]
    if (len(elts) > 3 and isinstance(elts[3], ast.Constant) and elts[3].value == "--dry-run"):
        verb.append("--dry-run")
    return tuple(verb)


def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and (
        (isinstance(n.func, ast.Attribute) and n.func.attr == name)
        or (isinstance(n.func, ast.Name) and n.func.id == name))]


def _is_call_to(node: ast.AST | None, name: str) -> bool:
    return isinstance(node, ast.Call) and getattr(node.func, "id", None) == name


def _popen_is_fed_by(tree: ast.Module, popen: ast.Call, name: str) -> bool:
    """`Popen` 的第一個引數是對 `name` 的呼叫，或是同一個函式內由 `name(...)` 賦值而來的變數。"""
    first = popen.args[0] if popen.args else None
    if _is_call_to(first, name):
        return True
    if not isinstance(first, ast.Name):
        return False
    for scope in (s for s in ast.walk(tree) if isinstance(s, ast.FunctionDef)):
        if popen in list(ast.walk(scope)):
            return any(isinstance(n, ast.Assign) and _is_call_to(n.value, name)
                       and any(isinstance(t, ast.Name) and t.id == first.id for t in n.targets)
                       for n in ast.walk(scope))
    return False


def crit4_argv(rel: str, source: str,
               allowed: frozenset[tuple[str, ...]] = ALLOWED_VERBS) -> list[str]:
    tree = ast.parse(source)
    out: list[str] = []
    funcs = argv_functions(tree)
    if len(funcs) != 1:
        return [f"判準4 {rel} 組 argv 的函式必須恰一個，實際 {len(funcs)}"]
    fn = funcs[0]
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
    if len(returns) != 1 or not isinstance(returns[0].value, ast.List):
        return [f"判準4 {rel}:{fn.name} 必須恰一個 return 且為列表字面值"]
    verb = verb_of(returns[0].value.elts)
    if verb is None or verb not in allowed:
        out.append(f"判準4 {rel}:{fn.name} 動詞 {verb!r} 不在白名單 {sorted(allowed)}")
    popens = _calls(tree, "Popen")
    if len(popens) != 1:
        return [*out, f"判準4 {rel} 的 Popen 呼叫必須恰一處，實際 {len(popens)}"]
    if not _popen_is_fed_by(tree, popens[0], fn.name):
        out.append(f"判準4 {rel} 的 Popen argv 引數不是來自 {fn.name}")
    return out


# ── 判準 5：動態對照 ────────────────────────────────────────────────────────────────────────
def crit5_dynamic(builder: Callable[..., list[str]],
                  allowed: frozenset[tuple[str, ...]] = ALLOWED_VERBS) -> list[str]:
    out: list[str] = []
    for kind in KINDS:
        for combo in FLAG_COMBOS:
            argv = builder(Path("repo-root"), kind, **combo)
            label = f"{kind} {combo}"
            if not any(tuple(argv[2:2 + len(v)]) == v for v in allowed):
                out.append(f"判準5 {label}：動詞位置為 {argv[2:4]}，不在白名單")
            if "--repo" in argv:
                out.append(f"判準5 {label}：argv 含 --repo")
    return out


# ── AT-932-2-1：真原始碼 ────────────────────────────────────────────────────────────────────
def app_sources() -> dict[str, str]:
    return {p.relative_to(APP_DIR).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(APP_DIR.rglob("*.py"))}


def test_AT_932_2_1_the_real_app_tree_passes_all_five_criteria() -> None:
    sources = app_sources()
    assert {"si_cli.py", "routers/si.py"} <= set(sources), "鎖要有標的：兩個 SI 檔必須存在"
    assert len(sources) >= 20, "掃描範圍異常小"
    violations: list[str] = []
    for rel, text in sources.items():
        violations += crit1_writes(rel, text) + crit2_imports(rel, text) + crit3_literal(rel, text)
    violations += crit4_argv("si_cli.py", sources["si_cli.py"], P1B_VERBS)
    violations += crit5_dynamic(si_cli.build_argv, P1B_VERBS)
    assert violations == [], "\n".join(violations)
    tree = ast.parse(sources["si_cli.py"])
    funcs = argv_functions(tree)
    assert [f.name for f in funcs] == ["build_argv"]
    returns = [n for n in ast.walk(funcs[0]) if isinstance(n, ast.Return)]
    assert len(returns) == 1 and isinstance(returns[0].value, ast.List)
    assert verb_of(returns[0].value.elts) == ("export",)
    assert len(KINDS) * len(FLAG_COMBOS) >= 15
    for rel, text in sources.items():
        assert crit2_imports(rel, text) == [], f"{rel}：sys.path 變更與 lib／tools import 須為零"
        assert SCRIPT_LITERAL not in text.lower() or rel == "si_cli.py", rel
    for rel in ("si_cli.py", "routers/si.py"):
        assert "obs-add" not in sources[rel], f"{rel}：P2b 預留的動詞配對在 P1b 不得被組出"


# ── AT-932-2-E-1：違規樣本逐一回非空並指出判準，良性樣本回空 ───────────────────────────────────
SI_TAG = "# selfimproving module\n"
CRIT1_BAD = {
    "open-w": 'open(p, "w")', "open-append": 'open(p, mode="a")',
    "write_text": 'Path(p).write_text("x")', "os.replace": "os.replace(a, b)",
    "json.dump": "json.dump(d, fh)"}
CRIT1_OK = ["open(p)", 'open(p, "rb")', "Path(p).read_text()", "json.dumps(d)"]
CRIT2_BAD = {
    "import-lib": "import lib", "from-lib": "from lib.selfimproving import x",
    "from-tools": "from tools import y", "path-insert": "import sys\nsys.path.insert(0, p)",
    "path-append": "import sys\nsys.path.append(p)",
    "path-augassign": "import sys\nsys.path += [p]", "path-assign": "import sys\nsys.path = [p]",
    "importlib-lib": 'import importlib\nimportlib.import_module("lib.selfimproving")',
    "importlib-tools": 'import importlib\nimportlib.import_module("tools")'}
CRIT2_OK = ["from . import procutil", "from .errors import ApiError", "import json",
            "from fastapi import APIRouter", "sys_path = []"]
SI_CLI_TEMPLATE = textwrap.dedent('''\
    import subprocess
    import sys


    def build_argv(root, kind, *, since=None, limit=None, ident=None):
        return [sys.executable, str(root / "tools" / "x.py"), {verb}, "--json", "--kind", kind,
                *(["--since", str(since)] if since is not None else []){tail}]


    def run(root, kind):
        argv = build_argv(root, kind)
        return subprocess.Popen(argv)
''')


def variant(verb: str = '"export"', tail: str = "") -> str:
    return SI_CLI_TEMPLATE.format(verb=verb, tail=tail)


TWO_POPENS = variant() + (
    "\n\ndef again(root):\n    return subprocess.Popen(build_argv(root, 'x'))\n")
CRIT4_BAD = {
    "verb-check": variant('"check"'), "verb-decide": variant('"decide"'),
    "verb-obs-add-without-dry-run": variant('"obs-add"'), "verb-run-open": variant('"run-open"'),
    "verb-promote": variant('"promote"'), "two-popens": TWO_POPENS,
    "argv-from-another-function": SI_CLI_TEMPLATE.format(verb='"export"', tail="").replace(
        "argv = build_argv(root, kind)", "argv = other(root, kind)") + textwrap.dedent('''

        def other(root, kind):
            return ["x"]
    ''')}
CRIT4_OK = {"export": variant(), "obs-add-with-dry-run": variant('"obs-add", "--dry-run"')}


def load_variant(tmp_path: Path, source: str, name: str) -> Any:
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", list(CRIT1_BAD))
def test_AT_932_2_E_1_criterion_1_flags_every_write_shaped_sample(name: str) -> None:
    hits = crit1_writes("x.py", SI_TAG + CRIT1_BAD[name])
    assert hits and all(h.startswith("判準1") for h in hits), f"{name}：{hits}"
    assert crit1_writes("unrelated.py", CRIT1_BAD[name]) == [], "與 SI 無關的模組不在判準 1 的範圍"


@pytest.mark.parametrize("sample", CRIT1_OK)
def test_AT_932_2_E_1_criterion_1_lets_read_shaped_samples_through(sample: str) -> None:
    assert crit1_writes("x.py", SI_TAG + sample) == []


@pytest.mark.parametrize("name", list(CRIT2_BAD))
def test_AT_932_2_E_1_criterion_2_flags_banned_imports_and_sys_path_changes(name: str) -> None:
    hits = crit2_imports("x.py", CRIT2_BAD[name])
    assert hits and all(h.startswith("判準2") for h in hits), f"{name}：{hits}"


@pytest.mark.parametrize("sample", CRIT2_OK)
def test_AT_932_2_E_1_criterion_2_lets_benign_imports_through(sample: str) -> None:
    assert crit2_imports("x.py", sample) == []


def test_AT_932_2_E_1_criterion_3_flags_a_second_module_with_the_script_literal() -> None:
    hits = crit3_literal("other.py", 'PATH = "tools/selfimproving.py"')
    assert hits and hits[0].startswith("判準3")
    assert crit3_literal("si_cli.py", 'PATH = "tools/selfimproving.py"') == []
    assert crit3_literal("other.py", 'NAME = "self improving"') == []


@pytest.mark.parametrize("name", list(CRIT4_BAD))
def test_AT_932_2_E_1_criterion_4_flags_wrong_verbs_and_wrong_shapes(name: str) -> None:
    hits = crit4_argv("si_cli.py", CRIT4_BAD[name])
    assert hits and all(h.startswith("判準4") for h in hits), f"{name}：{hits}"


@pytest.mark.parametrize("name", list(CRIT4_OK))
def test_AT_932_2_E_1_criterion_4_accepts_the_whitelisted_verb_shapes(name: str) -> None:
    assert crit4_argv("si_cli.py", CRIT4_OK[name]) == []
    p1b = crit4_argv("si_cli.py", CRIT4_OK[name], P1B_VERBS)
    if name == "export":
        assert p1b == []
    else:
        assert p1b, "P1b 的真檔不得組出 P2b 預留的配對"


def test_AT_932_2_E_1_criterion_5_flags_a_dynamic_repo_flag_and_a_wrong_verb(
        tmp_path: Path) -> None:
    with_repo = variant(tail=', "--repo", str(root)')
    assert crit4_argv("si_cli.py", with_repo) == [], "靜態形態看不到尾端的 --repo，要靠動態對照"
    hits = crit5_dynamic(load_variant(tmp_path, with_repo, "with_repo").build_argv)
    assert hits and all(h.startswith("判準5") for h in hits) and any("--repo" in h for h in hits)
    wrong_verb = crit5_dynamic(load_variant(tmp_path, variant('"check"'), "wrong_verb").build_argv)
    assert wrong_verb and all(h.startswith("判準5") for h in wrong_verb)
    clean = crit5_dynamic(load_variant(tmp_path, variant(), "clean").build_argv)
    assert clean == []
