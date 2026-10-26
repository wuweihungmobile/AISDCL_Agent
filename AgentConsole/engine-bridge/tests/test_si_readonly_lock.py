"""Bridge 對 SelfImproving 的寫入面不變量：原始碼的 AST 鎖（TCS-SelfImprovingDecide-P2b W5；
AT-933-1-6、AT-933-1-E-3；由 P1b 的唯讀鎖〔TCS-SelfImprovingMirror-P1b R6〕改寫，判準 1′～5′）。

P1b 的前提是「Bridge 零寫入」；P2b 改寫為「SelfImproving 帳本只有根層 CLI 能寫；Bridge 只把 backend
簽好的稽核 JSON 原樣落在稽核目錄，並以唯讀 `obs-add --dry-run` 預檢」。邊界型 M（形態判準）：
`getattr`、動態拼接、`importlib` 以變數載入看不到；行為面另由 test_si_write_routes.py 的落檔清單與
test_si_console_ingest.py 的真 CLI 入帳覆蓋。五項判準都是純函式（輸入是原始碼文字或可呼叫物件，
輸出是違規清單），對真原始碼必須回空、對各違規樣本必須逐一回非空並指出判準編號：
  判準 1′ 寫入形態呼叫：「SI 相關」模組（`si_cli.py`、`routers/si.py`、`si_audit.py`，及原始碼含
          `selfimproving`〔不分大小寫〕字樣的其他 `app/` 模組）的寫入形態呼叫（沿
          `write_shaped_calls`，自 test_sdd_integration_parity 匯入、不複製）只准出現在
          `si_audit.py`；該檔每個寫入形態呼叫的路徑引數須源自函式參數 `audit_dir`（`os.write` 的
          fd 須源自同函式的 `os.open`），且整檔不得有 `Path.home`、`expanduser`、`os.environ`、
          `os.getenv`；
          `routers/si.py` 呼叫 `store_audit` 時第一引數須是以 `.si_audit_dir` 結尾的屬性存取。
          唯一的例外是 `si_cli.py` 把請求本文餵進子行程 stdin 的那一個 `.write`（管道寫入，不是檔案
          寫入）：它必須在函式 `_feed_stdin` 內、接收者是參數 `stream`，且該函式只被
          `Thread(target=_feed_stdin, args=(<子行程>.stdin, …))` 引用一次
  判準 2 `app/` 全樹：不得 import `lib`／`tools`（含 `importlib` 對這兩名的字面呼叫），不得有任何
         對 `sys.path` 的變更（呼叫、賦值、增量賦值）
  判準 3 CLI 腳本的檔名字面在 `app/` 只出現在 `si_cli.py`
  判準 4′ argv 動詞形態：`si_cli.py` 中組 argv 的函式（含「首元素 `sys.executable` 的列表字面值」
          者）恰兩個：`build_argv`（動詞 `export`）與 `build_validate_argv`（動詞 `obs-add` 接
          `--dry-run`），各恰一個 `return`（列表字面值）；`Popen` 呼叫恰一處，其 argv 引數來自這兩個
          函式之一（直接呼叫、同函式內由其賦值的變數，或「該函式的參數，且檔內每個呼叫點都傳入前述
          兩種形態」）；動詞白名單＝{`export`、`obs-add --dry-run`}
  判準 5′ 動態對照：對兩個函式實際呼叫，動詞位置恆在白名單、與函式配對、不含 `--repo`
AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import ast
import importlib.util
import textwrap
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

import app as app_package
from app import si_cli
from tests.test_sdd_integration_parity import write_shaped_calls

APP_DIR = Path(app_package.__file__).resolve().parent
SCRIPT_LITERAL = "selfimproving.py"
AUDIT_MODULE = "si_audit.py"
STDIN_FEEDER = "_feed_stdin"
#: 動詞白名單（住在鎖的測試檔內）：`export` 與 `obs-add --dry-run`（唯讀預檢）。
ALLOWED_VERBS: frozenset[tuple[str, ...]] = frozenset({("export",), ("obs-add", "--dry-run")})
#: 組 argv 的函式與其動詞配對。
BUILDERS: dict[str, tuple[str, ...]] = {
    "build_argv": ("export",), "build_validate_argv": ("obs-add", "--dry-run")}
BANNED_ROOTS = frozenset({"lib", "tools"})
PATH_MUTATORS = frozenset(
    {"insert", "append", "extend", "remove", "pop", "clear", "sort", "reverse"})
#: 稽核檔模組整檔禁用：路徑只准源自參數，不讀環境、不取家目錄。
FORBIDDEN_ATTRS = frozenset({"home", "expanduser", "environ", "getenv", "getenvb"})
FORBIDDEN_NAMES = frozenset({"expanduser", "environ", "getenv", "getenvb"})
#: 稽核檔模組內一律不准的寫入形態：串流寫入（沒有「路徑」可驗），以及會改動目錄項的原語
#: （`replace`／`rename`／`move`…；W2：不使用它們，根層站點普查才不增站點；半成品清除只准
#: `unlink`）。
NEVER_IN_AUDIT_MODULE = frozenset({
    "writelines", "dump", "safe_dump", "write_json_atomic", "replace", "rename", "move", "copy",
    "copy2", "copyfile", "copytree", "rmtree"})
KINDS = ("observations", "events", "proposals", "runs", "status", "issues")
FLAG_COMBOS: list[dict[str, Any]] = [
    {}, {"since": 3}, {"limit": 7}, {"since": 3, "limit": 7}, {"ident": "PROP-SI-004"},
    {"status": "待處理"}, {"source": "系統缺陷"},
    {"since": 3, "limit": 7, "status": "待解,延後", "source": "使用者提案"}]
FUNC_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)


# ── 共用的 AST 小工具 ────────────────────────────────────────────────────────────────────────
def _owners(tree: ast.AST) -> dict[ast.AST, Any]:
    """每個節點 → 包住它的最內層函式（模組層為 None）。"""
    owner: dict[ast.AST, Any] = {}

    def visit(node: ast.AST, current: Any) -> None:
        for child in ast.iter_child_nodes(node):
            owner[child] = current
            visit(child, child if isinstance(child, FUNC_TYPES) else current)

    visit(tree, None)
    return owner


def _names_in(expr: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(
        func, ast.Attribute) else None


def _is_os_call(call: ast.Call) -> bool:
    return (isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "os")


def _calls_at(tree: ast.AST, line: int) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.lineno == line]


def _match_hit(call: ast.Call, what: str) -> bool:
    """`write_shaped_calls` 的命中說明與呼叫節點是否同一個（它只回行號與說明文字）。"""
    name = _call_name(call)
    return name is not None and (what == name or what.endswith("." + name)
                                 or (name == "open" and what.startswith("open(")))


def _hit_nodes(tree: ast.AST) -> tuple[list[ast.Call], list[tuple[int, str]]]:
    """（寫入形態呼叫的節點, 找不到對應節點的命中）。"""
    nodes: list[ast.Call] = []
    lost: list[tuple[int, str]] = []
    for line, what in write_shaped_calls(tree):
        found = [n for n in _calls_at(tree, line) if _match_hit(n, what)]
        if found:
            nodes += [n for n in found if n not in nodes]
        else:
            lost.append((line, what))
    return nodes, lost


# ── 判準 1′：寫入形態 ───────────────────────────────────────────────────────────────────────
def is_si_related(rel: str, source: str) -> bool:
    return rel in ("si_cli.py", "routers/si.py", AUDIT_MODULE) or "selfimproving" in source.lower()


def _tainted_names(fn: Any) -> set[str]:
    """函式內「源自參數 `audit_dir`」的名稱：參數本身，加上其後以含這些名稱的運算式賦值的變數。"""
    params = {a.arg for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)}
    tainted = {"audit_dir"} & params
    changed = True
    while changed:
        changed = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                targets, value = list(node.targets), node.value
            elif isinstance(node, ast.AnnAssign | ast.AugAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            if _names_in(value) & tainted:
                for target in targets:
                    for name in _names_in(target) - tainted:
                        tainted.add(name)
                        changed = True
    return tainted


def _fd_from_os_open(fn: Any, name: str) -> bool:
    return any(
        isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and _is_os_call(n.value)
        and n.value.func.attr == "open"                                    # type: ignore[attr-defined]
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
        for n in ast.walk(fn))


def _path_expr(call: ast.Call) -> ast.expr | None:
    """寫入形態呼叫的「路徑」運算式：`os.`／`shutil.` 形態與裸函式取第一個引數；方法呼叫
    （`p.unlink()`、`p.write_text()`）取接收者。"""
    func = call.func
    if isinstance(func, ast.Attribute) and not (
            isinstance(func.value, ast.Name) and func.value.id in ("os", "shutil", "json", "yaml")):
        return func.value
    return call.args[0] if call.args else None


def _audit_module_violations(rel: str, tree: ast.AST) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            out.append(f"判準1 {rel}:{node.lineno} 稽核檔模組不得使用 {node.attr}"
                       "（路徑只能源自參數 audit_dir）")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            out.append(f"判準1 {rel}:{node.lineno} 稽核檔模組不得使用 {node.id}"
                       "（路徑只能源自參數 audit_dir）")
    owner = _owners(tree)
    nodes, lost = _hit_nodes(tree)
    out += [f"判準1 {rel}:{line} 寫入形態呼叫 {what} 對不上呼叫節點" for line, what in lost]
    for node in nodes:
        name = _call_name(node)
        fn = owner.get(node)
        where = f"判準1 {rel}:{node.lineno} 寫入形態呼叫 {name}"
        if fn is None:
            out.append(f"{where} 出現在模組層（只准在以 audit_dir 為參數的函式內）")
            continue
        if name in NEVER_IN_AUDIT_MODULE:
            out.append(f"{where} 在稽核檔模組內不准（只准 os.open 取 fd 再 os.write）")
            continue
        if name == "write":
            first = node.args[0] if node.args else None
            if not (_is_os_call(node) and isinstance(first, ast.Name)
                    and _fd_from_os_open(fn, first.id)):
                out.append(f"{where} 的對象不是同函式 os.open 取得的 fd")
            continue
        path = _path_expr(node)
        if path is None or not (_names_in(path) & _tainted_names(fn)):
            out.append(f"{where} 的路徑引數不是源自函式參數 audit_dir")
    return out


def _is_feeder_write(call: ast.Call, fn: Any) -> bool:
    func = call.func
    return (isinstance(func, ast.Attribute) and func.attr == "write"
            and isinstance(func.value, ast.Name) and func.value.id == "stream"
            and fn is not None and fn.name == STDIN_FEEDER)


def _feeder_wiring_violations(rel: str, tree: ast.AST) -> list[str]:
    refs = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == STDIN_FEEDER]
    sites = []
    for call in (c for c in ast.walk(tree) if isinstance(c, ast.Call)):
        kws = {k.arg: k.value for k in call.keywords}
        target, args = kws.get("target"), kws.get("args")
        if (_call_name(call) == "Thread" and isinstance(target, ast.Name)
                and target.id == STDIN_FEEDER and isinstance(args, ast.Tuple) and args.elts
                and isinstance(args.elts[0], ast.Attribute) and args.elts[0].attr == "stdin"):
            sites.append(call)
    if len(refs) == 1 and len(sites) == 1:
        return []
    return [f"判準1 {rel} 的 {STDIN_FEEDER} 必須恰一處引用，且是 "
            f"Thread(target={STDIN_FEEDER}, args=(<子行程>.stdin, …))"
            f"（引用 {len(refs)}、合格 {len(sites)}）"]


def _cli_module_violations(rel: str, tree: ast.AST) -> list[str]:
    owner = _owners(tree)
    nodes, lost = _hit_nodes(tree)
    out = [f"判準1 {rel}:{line} 寫入形態呼叫 {what} 對不上呼叫節點" for line, what in lost]
    exempt = []
    for node in nodes:
        if _is_feeder_write(node, owner.get(node)):
            exempt.append(node)
        else:
            out.append(f"判準1 {rel}:{node.lineno} 寫入形態呼叫 {_call_name(node)}"
                       f"（只准出現在 {AUDIT_MODULE}；唯一例外是 {STDIN_FEEDER} 的 stdin "
                       "管道寫入）")
    if len(exempt) > 1:
        out.append(f"判準1 {rel} 的 stdin 管道寫入只准一處，實際 {len(exempt)}")
    if exempt:
        out += _feeder_wiring_violations(rel, tree)
    return out


def _store_audit_arg_violations(rel: str, tree: ast.AST) -> list[str]:
    """`routers/si.py` 對 `store_audit` 的每個引用：直接呼叫（第一引數）或交給執行緒池呼叫（第二個
    引數起才是它的第一引數）時，該引數須是以 `.si_audit_dir` 結尾的屬性存取；其他用法（別名賦值…）
    一律違規。"""
    parent = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    out: list[str] = []
    refs = [n for n in ast.walk(tree)
            if (isinstance(n, ast.Attribute) and n.attr == "store_audit")
            or (isinstance(n, ast.Name) and n.id == "store_audit")]
    for ref in refs:
        up = parent.get(ref)
        first: ast.expr | None
        if isinstance(up, ast.Call) and up.func is ref:
            first = up.args[0] if up.args else None
        elif isinstance(up, ast.Call) and up.args and up.args[0] is ref:
            first = up.args[1] if len(up.args) > 1 else None
        else:
            out.append(f"判準1 {rel}:{ref.lineno} store_audit 只准被直接呼叫或交給執行緒池呼叫")
            continue
        if not (isinstance(first, ast.Attribute) and first.attr == "si_audit_dir"):
            out.append(f"判準1 {rel}:{ref.lineno} store_audit 的第一引數須是以 .si_audit_dir "
                       "結尾的屬性存取")
    return out


def crit1_writes(rel: str, source: str) -> list[str]:
    if not is_si_related(rel, source):
        return []
    tree = ast.parse(source)
    if rel == AUDIT_MODULE:
        out = _audit_module_violations(rel, tree)
    elif rel == "si_cli.py":
        out = _cli_module_violations(rel, tree)
    else:
        out = [f"判準1 {rel}:{line} 寫入形態呼叫 {what}（只准出現在 {AUDIT_MODULE}）"
               for line, what in write_shaped_calls(tree)]
    if rel == "routers/si.py":
        out += _store_audit_arg_violations(rel, tree)
    return out


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


# ── 判準 4′：argv 動詞形態 ──────────────────────────────────────────────────────────────────
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
    if len(elts) > 3 and isinstance(elts[3], ast.Constant) and elts[3].value == "--dry-run":
        verb.append("--dry-run")
    return tuple(verb)


def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _call_name(n) == name]


def _calls_to_any(node: ast.AST | None, names: Iterable[str]) -> bool:
    wanted = set(names)
    return isinstance(node, ast.Call) and getattr(node.func, "id", None) in wanted


def _fed_in_scope(scope: Any, expr: ast.AST | None, names: Iterable[str]) -> bool:
    """`expr` 是對 builder 的呼叫，或是 `scope` 內由 builder 呼叫賦值而來的變數。"""
    if _calls_to_any(expr, names):
        return True
    if isinstance(expr, ast.Name) and scope is not None:
        return any(isinstance(n, ast.Assign) and _calls_to_any(n.value, names)
                   and any(isinstance(t, ast.Name) and t.id == expr.id for t in n.targets)
                   for n in ast.walk(scope))
    return False


def _popen_is_fed_by(tree: ast.Module, popen: ast.Call, names: Iterable[str]) -> bool:
    """`Popen` 的第一個引數：builder 的呼叫、同函式內由 builder 賦值的變數，或是該函式的參數且檔內
    每個呼叫點（至少一個）同位置的引數都符合前兩種形態。"""
    names = set(names)
    owner = _owners(tree)
    first = popen.args[0] if popen.args else None
    scope = owner.get(popen)
    if _fed_in_scope(scope, first, names):
        return True
    if isinstance(first, ast.Name) and scope is not None:
        params = [a.arg for a in scope.args.args]
        if first.id in params:
            index = params.index(first.id)
            sites = [c for c in ast.walk(tree) if isinstance(c, ast.Call)
                     and getattr(c.func, "id", None) == scope.name]
            return bool(sites) and all(
                len(site.args) > index and _fed_in_scope(owner.get(site), site.args[index], names)
                for site in sites)
    return False


def crit4_argv(rel: str, source: str,
               pairing: dict[str, tuple[str, ...]] | None = None) -> list[str]:
    pairing = BUILDERS if pairing is None else pairing
    tree = ast.parse(source)
    out: list[str] = []
    funcs = argv_functions(tree)
    names = sorted(f.name for f in funcs)
    if names != sorted(pairing):
        return [f"判準4 {rel} 組 argv 的函式必須恰為 {sorted(pairing)}，實際 {names}"]
    for fn in funcs:
        returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
        if len(returns) != 1 or not isinstance(returns[0].value, ast.List):
            out.append(f"判準4 {rel}:{fn.name} 必須恰一個 return 且為列表字面值")
            continue
        verb = verb_of(returns[0].value.elts)
        if verb is None or verb not in ALLOWED_VERBS:
            out.append(f"判準4 {rel}:{fn.name} 動詞 {verb!r} 不在白名單 {sorted(ALLOWED_VERBS)}")
        elif verb != pairing[fn.name]:
            out.append(f"判準4 {rel}:{fn.name} 動詞 {verb!r} 與配對 {pairing[fn.name]!r} 不符")
    popens = _calls(tree, "Popen")
    if len(popens) != 1:
        return [*out, f"判準4 {rel} 的 Popen 呼叫必須恰一處，實際 {len(popens)}"]
    if not _popen_is_fed_by(tree, popens[0], pairing):
        out.append(f"判準4 {rel} 的 Popen argv 引數不是來自 {sorted(pairing)} 之一")
    return out


# ── 判準 5′：動態對照 ───────────────────────────────────────────────────────────────────────
def dynamic_argvs(module: Any) -> list[tuple[str, str, list[str]]]:
    """對模組（或載入的變體）的兩個 argv 函式實際呼叫：`(函式名, 說明, argv)`；缺的函式不呼叫。"""
    out: list[tuple[str, str, list[str]]] = []
    build = getattr(module, "build_argv", None)
    if build is not None:
        for kind in KINDS:
            for combo in FLAG_COMBOS:
                argv = build(Path("repo-root"), kind, **combo)
                out.append(("build_argv", f"{kind} {combo}", argv))
    validate = getattr(module, "build_validate_argv", None)
    if validate is not None:
        out.append(("build_validate_argv", "預檢", validate(Path("repo-root"))))
    return out


def crit5_dynamic(argvs: Iterable[tuple[str, str, list[str]]],
                  pairing: dict[str, tuple[str, ...]] | None = None) -> list[str]:
    pairing = BUILDERS if pairing is None else pairing
    out: list[str] = []
    for name, label, argv in argvs:
        head = f"判準5 {name} {label}"
        if not any(tuple(argv[2:2 + len(v)]) == v for v in ALLOWED_VERBS):
            out.append(f"{head}：動詞位置為 {argv[2:4]}，不在白名單")
        elif name in pairing and tuple(argv[2:2 + len(pairing[name])]) != pairing[name]:
            out.append(f"{head}：動詞位置為 {argv[2:4]}，與配對 {pairing[name]} 不符")
        if "--repo" in argv:
            out.append(f"{head}：argv 含 --repo")
    return out


# ── AT-933-1-6：真原始碼 ────────────────────────────────────────────────────────────────────
def app_sources() -> dict[str, str]:
    return {p.relative_to(APP_DIR).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(APP_DIR.rglob("*.py"))}


def string_constants(source: str) -> list[str]:
    return [n.value for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_AT_933_1_6_the_real_app_tree_passes_the_five_p2b_criteria() -> None:
    sources = app_sources()
    assert {"si_audit.py", "si_cli.py", "routers/si.py"} <= set(sources), \
        "鎖要有標的：三個 SI 檔必須存在"
    assert len(sources) >= 20, "掃描範圍異常小"
    violations: list[str] = []
    for rel, text in sources.items():
        violations += crit1_writes(rel, text) + crit2_imports(rel, text) + crit3_literal(rel, text)
    violations += crit4_argv("si_cli.py", sources["si_cli.py"])
    argvs = dynamic_argvs(si_cli)
    violations += crit5_dynamic(argvs)
    assert violations == [], "\n".join(violations)
    assert len(argvs) == len(KINDS) * len(FLAG_COMBOS) + 1, "動態對照必須涵蓋兩個函式的全部組合"
    # 正面事實一：恰兩個組 argv 的函式，動詞集合恰為 export 與 obs-add 加 dry-run
    tree = ast.parse(sources["si_cli.py"])
    funcs = argv_functions(tree)
    assert sorted(f.name for f in funcs) == ["build_argv", "build_validate_argv"]
    verbs = set()
    for fn in funcs:
        returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
        assert len(returns) == 1 and isinstance(returns[0].value, ast.List), fn.name
        verbs.add(verb_of(returns[0].value.elts))
    assert verbs == {("export",), ("obs-add", "--dry-run")} == set(ALLOWED_VERBS)
    # 正面事實二：寫入形態呼叫只出現在 si_audit.py（加 si_cli.py 唯一的 stdin 管道寫入）
    with_writes = {rel: write_shaped_calls(ast.parse(text)) for rel, text in sources.items()
                   if is_si_related(rel, text) and write_shaped_calls(ast.parse(text))}
    assert set(with_writes) == {"si_audit.py", "si_cli.py"}, sorted(with_writes)
    assert [what for _line, what in with_writes["si_cli.py"]] == ["write"], \
        "si_cli.py 只准有 _feed_stdin 的那一個管道寫入"
    # 正面事實三：Bridge 永遠不組出會寫帳本的 CLI 動詞
    for banned in ("decide", "obs-close", "promote", "rollback", "sandbox", "verify"):
        assert banned not in string_constants(sources["si_cli.py"]), banned
    assert string_constants(sources["si_cli.py"]).count("obs-add") == 1
    # 正面事實四：路由確實呼叫 store_audit，且第一引數取自 .si_audit_dir
    assert "store_audit" in sources["routers/si.py"]
    assert crit1_writes("routers/si.py", sources["routers/si.py"]) == []
    for rel, text in sources.items():
        assert crit2_imports(rel, text) == [], f"{rel}：sys.path 變更與 lib／tools import 須為零"
        assert SCRIPT_LITERAL not in text.lower() or rel == "si_cli.py", rel


# ── AT-933-1-E-3：違規樣本逐一回非空並指出判準，良性樣本回空 ─────────────────────────────────
SI_TAG = "# selfimproving module\n"
#: 判準 1′（一般 SI 相關模組＝零寫入形態呼叫）
CRIT1_BAD = {
    "open-w": 'open(p, "w")', "open-append": 'open(p, mode="a")',
    "write_text": 'Path(p).write_text("x")', "os.replace": "os.replace(a, b)",
    "json.dump": "json.dump(d, fh)", "os.open": "os.open(p, os.O_WRONLY)",
    "handle.write": 'fh.write("x")'}
CRIT1_OK = ["open(p)", 'open(p, "rb")', "Path(p).read_text()", "json.dumps(d)"]
#: 判準 1′（稽核檔模組：路徑須源自參數 audit_dir）
AUDIT_OK = textwrap.dedent('''\
    import os


    def store_audit(audit_dir, audit_ref, raw):
        target = audit_dir / f"{audit_ref}.json"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            try:
                os.write(fd, raw)
            finally:
                os.close(fd)
        except OSError:
            os.unlink(target)
''')
AUDIT_BAD = {
    "literal-path-open": AUDIT_OK.replace("os.open(target,", 'os.open("/etc/si-audit.json",'),
    "path-home": AUDIT_OK.replace("audit_dir / f", "Path.home() / f"),
    "reads-environ": AUDIT_OK.replace("audit_dir / f", 'os.environ["SI_DIR"] + f'),
    "getenv": AUDIT_OK.replace("audit_dir / f", 'os.getenv("SI_DIR") + f'),
    "expanduser": AUDIT_OK.replace("audit_dir / f", 'os.path.expanduser("~") + f'),
    "path-not-from-parameter": AUDIT_OK.replace("audit_dir / f", 'Path("/var/lib") / f'),
    "unlink-of-a-literal": AUDIT_OK.replace("os.unlink(target)", 'os.unlink("/tmp/x")'),
    "fd-not-from-os-open": AUDIT_OK.replace("os.write(fd, raw)", "os.write(1, raw)"),
    "stream-write": AUDIT_OK.replace("os.write(fd, raw)", "fh.write(raw)"),
    "module-level-write": AUDIT_OK + 'os.open("/etc/x", os.O_WRONLY)\n',
    "replace-call": AUDIT_OK.replace("os.unlink(target)", "os.replace(target, audit_dir)"),
    "shutil-move": AUDIT_OK.replace("os.unlink(target)", "shutil.move(target, audit_dir)"),
}
#: 判準 1′（routers/si.py：store_audit 的第一引數；其他寫入形態一律違規）
ROUTER_OK = [
    "async def h(cfg, ref, raw):\n    si_audit.store_audit(cfg.si_audit_dir, ref, raw)\n",
    "async def h(cfg, ref, raw):\n"
    "    await run_in_threadpool(si_audit.store_audit, cfg.si_audit_dir, ref, raw)\n",
    "def h(request, ref, raw):\n"
    "    store_audit(request.app.state.settings.si_audit_dir, ref, raw)\n",
]
ROUTER_BAD = {
    "writes-in-router": SI_TAG + 'open("/tmp/x", "w")\n',
    "literal-dir": 'def h(ref, raw):\n    si_audit.store_audit(Path("/tmp"), ref, raw)\n',
    "other-attribute": "def h(cfg, ref, raw):\n    si_audit.store_audit(cfg.si_root, ref, raw)\n",
    "bare-name-dir": "def h(d, ref, raw):\n    si_audit.store_audit(d, ref, raw)\n",
    "threadpool-literal": 'async def h(ref, raw):\n'
                          '    await run_in_threadpool(si_audit.store_audit, "x", ref, raw)\n',
    "threadpool-no-dir": "async def h():\n    await run_in_threadpool(si_audit.store_audit)\n",
    "alias": "def h():\n    f = si_audit.store_audit\n    return f\n",
    "no-arguments": "def h():\n    si_audit.store_audit()\n",
}
#: 判準 1′（si_cli.py：stdin 管道寫入的唯一例外）
CLI_FEEDER_OK = textwrap.dedent('''\
    import threading

    def _feed_stdin(stream, data):
        stream.write(data)

    def go(proc, data):
        threading.Thread(target=_feed_stdin, args=(proc.stdin, data)).start()
''')
CLI_FEEDER_BAD = {
    "write-outside-the-feeder": CLI_FEEDER_OK + "\ndef other(fh):\n    fh.write('x')\n",
    "feeder-named-differently": CLI_FEEDER_OK.replace("_feed_stdin", "_pump"),
    "feeder-receiver-not-stream": CLI_FEEDER_OK.replace("stream.write", "other.write"),
    "feeder-fed-by-a-file": CLI_FEEDER_OK.replace("args=(proc.stdin, data)", "args=(fh, data)"),
    "feeder-called-directly": CLI_FEEDER_OK + "\ndef again(fh, d):\n    _feed_stdin(fh, d)\n",
    "two-feeders": CLI_FEEDER_OK.replace(
        "stream.write(data)", "stream.write(data)\n    stream.write(data)"),
    "unlink-in-the-cli": CLI_FEEDER_OK + "\ndef clean(p):\n    p.unlink()\n",
    "write_text-in-the-cli": CLI_FEEDER_OK + "\ndef save(p):\n    p.write_text('x')\n",
}
CRIT2_BAD = {
    "import-lib": "import lib", "from-lib": "from lib.selfimproving import x",
    "from-tools": "from tools import y", "path-insert": "import sys\nsys.path.insert(0, p)",
    "path-append": "import sys\nsys.path.append(p)",
    "path-augassign": "import sys\nsys.path += [p]", "path-assign": "import sys\nsys.path = [p]",
    "importlib-lib": 'import importlib\nimportlib.import_module("lib.selfimproving")',
    "importlib-tools": 'import importlib\nimportlib.import_module("tools")'}
CRIT2_OK = ["from . import procutil", "from .errors import ApiError", "import json",
            "from fastapi import APIRouter", "sys_path = []"]
#: 判準 4′／5′ 的樣板：與真 si_cli.py 同形（兩個 argv 函式、單一 Popen 在 `_execute`、
#: argv 由參數轉手）
SI_CLI_TEMPLATE = textwrap.dedent('''\
    import subprocess
    import sys


    def build_argv(root, kind, *, since=None, limit=None, status=None, source=None, ident=None):
        return [sys.executable, str(root / "tools" / "x.py"), {export_verb}, "--json", "--kind",
                kind, *(["--since", str(since)] if since is not None else []){export_tail}]


    def build_validate_argv(root):
        return [sys.executable, str(root / "tools" / "x.py"), {validate_verb}, "--json"
                {validate_tail}]


    def _execute(argv, root):
        return subprocess.Popen(argv, cwd=str(root))


    def run_export(root, kind):
        argv = build_argv(root, kind)
        return _execute(argv, root)


    def run_validate(root):
        return _execute(build_validate_argv(root), root)
''')


def variant(export_verb: str = '"export"', validate_verb: str = '"obs-add", "--dry-run"',
            export_tail: str = "", validate_tail: str = "") -> str:
    return SI_CLI_TEMPLATE.format(export_verb=export_verb, validate_verb=validate_verb,
                                  export_tail=export_tail, validate_tail=validate_tail)


CRIT4_BAD = {
    "export-verb-check": variant(export_verb='"check"'),
    "export-verb-decide": variant(export_verb='"decide"'),
    "validate-verb-decide": variant(validate_verb='"decide"'),
    "validate-verb-obs-close": variant(validate_verb='"obs-close"'),
    "validate-obs-add-without-dry-run": variant(validate_verb='"obs-add"'),
    "validate-verb-promote": variant(validate_verb='"promote"'),
    "pairing-swapped": variant(export_verb='"obs-add", "--dry-run"', validate_verb='"export"'),
    "third-argv-function": variant() + textwrap.dedent('''

        def build_third_argv(root):
            return [sys.executable, "x.py", "export"]
    '''),
    "second-popen": variant() + "\n\ndef again(root):\n    return subprocess.Popen(['x'])\n",
    "popen-fed-by-another-function": variant().replace(
        "return _execute(build_validate_argv(root), root)", "return _execute(other(root), root)"
    ) + "\n\ndef other(root):\n    return ['x']\n",
    "popen-has-no-call-site": variant().replace(
        "return _execute(argv, root)", "return None").replace(
        "return _execute(build_validate_argv(root), root)", "return None"),
    "builder-with-two-returns": variant().replace(
        "def build_validate_argv(root):\n",
        "def build_validate_argv(root):\n    if root is None:\n        return []\n"),
}
CRIT4_OK = {"real-shape": variant()}


def load_variant(tmp_path: Path, source: str, name: str) -> Any:
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_flagged(label: str, hits: list[str], criterion: str) -> None:
    assert hits and all(h.startswith(criterion) for h in hits), f"{label}：{hits}"


@pytest.mark.parametrize("name", list(CRIT1_BAD))
def test_AT_933_1_E_3_criterion_1_flags_every_write_shaped_sample_in_an_si_module(
        name: str) -> None:
    assert_flagged(name, crit1_writes("x.py", SI_TAG + CRIT1_BAD[name]), "判準1")
    assert crit1_writes("unrelated.py", CRIT1_BAD[name]) == [], "與 SI 無關的模組不在判準 1 的範圍"


@pytest.mark.parametrize("sample", CRIT1_OK)
def test_AT_933_1_E_3_criterion_1_lets_read_shaped_samples_through(sample: str) -> None:
    assert crit1_writes("x.py", SI_TAG + sample) == []


def test_AT_933_1_E_3_criterion_1_accepts_the_compliant_audit_module_shape() -> None:
    assert crit1_writes(AUDIT_MODULE, AUDIT_OK) == []
    real = (APP_DIR / AUDIT_MODULE).read_text(encoding="utf-8")
    assert crit1_writes(AUDIT_MODULE, real) == [], "真的 si_audit.py 就是合規形態"


@pytest.mark.parametrize("name", list(AUDIT_BAD))
def test_AT_933_1_E_3_criterion_1_flags_an_audit_module_whose_paths_do_not_come_from_audit_dir(
        name: str) -> None:
    assert AUDIT_BAD[name] != AUDIT_OK, f"{name}：樣本必須真的改了合規形態"
    assert_flagged(name, crit1_writes(AUDIT_MODULE, AUDIT_BAD[name]), "判準1")


@pytest.mark.parametrize("index", range(len(ROUTER_OK)))
def test_AT_933_1_E_3_criterion_1_accepts_routers_that_pass_the_configured_audit_dir(
        index: int) -> None:
    assert crit1_writes("routers/si.py", ROUTER_OK[index]) == []


@pytest.mark.parametrize("name", list(ROUTER_BAD))
def test_AT_933_1_E_3_criterion_1_flags_routers_that_write_or_pass_another_directory(
        name: str) -> None:
    assert_flagged(name, crit1_writes("routers/si.py", ROUTER_BAD[name]), "判準1")


def test_AT_933_1_E_3_criterion_1_accepts_only_the_stdin_pipe_feeder_in_the_cli() -> None:
    assert crit1_writes("si_cli.py", CLI_FEEDER_OK) == []
    assert crit1_writes("si_cli.py", "def f():\n    return 1\n") == []


@pytest.mark.parametrize("name", list(CLI_FEEDER_BAD))
def test_AT_933_1_E_3_criterion_1_flags_every_other_write_in_the_cli_module(name: str) -> None:
    assert CLI_FEEDER_BAD[name] != CLI_FEEDER_OK
    assert_flagged(name, crit1_writes("si_cli.py", CLI_FEEDER_BAD[name]), "判準1")


@pytest.mark.parametrize("name", list(CRIT2_BAD))
def test_AT_933_1_E_3_criterion_2_flags_banned_imports_and_sys_path_changes(name: str) -> None:
    assert_flagged(name, crit2_imports("x.py", CRIT2_BAD[name]), "判準2")


@pytest.mark.parametrize("sample", CRIT2_OK)
def test_AT_933_1_E_3_criterion_2_lets_benign_imports_through(sample: str) -> None:
    assert crit2_imports("x.py", sample) == []


def test_AT_933_1_E_3_criterion_3_flags_a_second_module_with_the_script_literal() -> None:
    hits = crit3_literal("other.py", 'PATH = "tools/selfimproving.py"')
    assert hits and hits[0].startswith("判準3")
    assert crit3_literal("si_cli.py", 'PATH = "tools/selfimproving.py"') == []
    assert crit3_literal("other.py", 'NAME = "self improving"') == []


@pytest.mark.parametrize("name", list(CRIT4_BAD))
def test_AT_933_1_E_3_criterion_4_flags_wrong_verbs_and_wrong_shapes(name: str) -> None:
    assert_flagged(name, crit4_argv("si_cli.py", CRIT4_BAD[name]), "判準4")


@pytest.mark.parametrize("name", list(CRIT4_OK))
def test_AT_933_1_E_3_criterion_4_accepts_the_whitelisted_two_builder_shape(name: str) -> None:
    assert crit4_argv("si_cli.py", CRIT4_OK[name]) == []
    # 單一 builder 的檔（P1b 的形態）不再合格：判準 4′ 要求恰兩個
    one = textwrap.dedent('''\
        import subprocess, sys
        def build_argv(root, kind):
            return [sys.executable, "x.py", "export", "--json", "--kind", kind]
        def run(root, kind):
            return subprocess.Popen(build_argv(root, kind))
    ''')
    assert_flagged("single-builder", crit4_argv("si_cli.py", one), "判準4")


def test_AT_933_1_E_3_criterion_5_flags_a_dynamic_repo_flag_a_wrong_verb_and_swapped_pairing(
        tmp_path: Path) -> None:
    with_repo = variant(export_tail=', "--repo", str(root)')
    assert crit4_argv("si_cli.py", with_repo) == [], "靜態形態看不到尾端的 --repo，要靠動態對照"
    hits = crit5_dynamic(dynamic_argvs(load_variant(tmp_path, with_repo, "with_repo")))
    assert_flagged("repo-in-export", hits, "判準5")
    assert any("--repo" in h for h in hits)
    repo_in_validate = variant(validate_tail=', "--repo", str(root)')
    hits = crit5_dynamic(dynamic_argvs(load_variant(tmp_path, repo_in_validate, "repo_validate")))
    assert_flagged("repo-in-validate", hits, "判準5")
    assert any("--repo" in h and "build_validate_argv" in h for h in hits)
    wrong = crit5_dynamic(dynamic_argvs(load_variant(tmp_path, variant(export_verb='"check"'),
                                                     "wrong_verb")))
    assert_flagged("wrong-verb", wrong, "判準5")
    swapped = variant(export_verb='"obs-add", "--dry-run"', validate_verb='"export"')
    hits = crit5_dynamic(dynamic_argvs(load_variant(tmp_path, swapped, "swapped")))
    assert_flagged("swapped", hits, "判準5")
    assert any("與配對" in h for h in hits), "動詞都在白名單內，但與函式配對不符也要被指出"
    clean = crit5_dynamic(dynamic_argvs(load_variant(tmp_path, variant(), "clean")))
    assert clean == []
