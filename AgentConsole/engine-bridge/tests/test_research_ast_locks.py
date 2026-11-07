"""研究面的 AST 鎖（TCS AT-960-13-7／13-E-1／13-3 的 AST 判準／6-2；PRD §9.4 機械鎖 ②）。

判準函式 `check_source(rel, text)` 輸入原始碼文字、輸出違規清單（判準編號＋行號），所以能對
合成樣本驗證「違規被抓、良性放行」（13-E-1），再對 `app/` 全樹實跑（13-7）。判準：
  C1 寫 `FSM-STATE-*.yaml`（提到該檔名的模組不得有任何寫入形態呼叫）；
  C2 核准類呼叫（`approve_baseline`、`spec_frozen`）只准住 `routers/research.py` 的 HTTP 處理函式
     （`spec_frozen` 另准在 `fsm_ops.py` 自己的包裝內；P1 另准 `research/adopt.py::adopt_baseline`
     的 `spec_frozen`，限 `stage="Stage-1"` 且函式內有「非外環鍵」守衛，D-126）；
  C3 外環鍵的子行程環境必須固定 `SDD_ENABLE_AUTO_RECOVERY=0`（`build_research_env` 內）；
  C4 不得有未登記的研究面動詞；
  C5 子行程呼叫必須帶 `**procutil.popen_platform_kwargs()`，且只准出現在登記的 exec 模組；
  C6 不得 `shell=True`；
  C7 `gate SCG_VALIDATION` 只要不是靜態的 FAIL，呼叫就必須位於「現態不為 HUMAN_PENDING」的守衛分支內
     （D-50：HUMAN_PENDING 下 PASS 會以 rc 1 結束；人工退回走 FAIL）。
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from app import main as main_module
from app import sdd_cli
from tests.test_sdd_integration_parity import write_shaped_calls

APP_DIR = Path(sdd_cli.__file__).resolve().parent
#: 子行程只准出現在這些模組（皆帶 procutil 旗標）；研究面新模組要起子行程＝先登記於此並說明 WHY。
EXEC_MODULES = frozenset({"runner.py", "sdd_cli.py", "si_cli.py", "health.py", "routers/sdd.py",
                          "research/gitops.py"})      # P1：git／gh 子行程的唯一出口（ADR-003 D16）
_SPAWN_NAMES = {"Popen", "run", "check_output", "check_call", "call"}


@dataclass(frozen=True)
class Hit:
    rule: str
    line: int


def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def call_name(node: ast.Call) -> str:
    func = node.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(
        func, ast.Attribute) else ""


def owner_name(node: ast.Call) -> str:
    func = node.func
    return func.value.id if isinstance(func, ast.Attribute) and isinstance(
        func.value, ast.Name) else ""


def enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.FunctionDef | None:
    cur: ast.AST | None = parents.get(node)
    while cur is not None:
        if isinstance(cur, ast.FunctionDef | ast.AsyncFunctionDef):
            return cur  # type: ignore[return-value]
        cur = parents.get(cur)
    return None


def is_router_decorator(dec: ast.expr) -> bool:
    target = dec.func if isinstance(dec, ast.Call) else dec
    return (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
            and target.value.id == "router" and target.attr in {"get", "post", "put", "patch",
                                                                "delete"})


def _guard_test(test: ast.expr, *, in_body: bool) -> bool:
    text = ast.unparse(test)
    if "HUMAN_PENDING" not in text:
        return False
    if in_body:
        return any(op in text for op in ("!=", "not in", "is not"))
    return "==" in text and "!=" not in text


def is_guarded(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    child, cur = node, parents.get(node)
    while cur is not None:
        if isinstance(cur, ast.If):
            if child in cur.body and _guard_test(cur.test, in_body=True):
                return True
            if child in cur.orelse and _guard_test(cur.test, in_body=False):
                return True
        child, cur = cur, parents.get(cur)
    return False


def _kw(node: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in node.keywords if k.arg == name), None)


def _is_const(value: ast.expr | None, *texts: str) -> bool:
    return isinstance(value, ast.Constant) and isinstance(value.value, str) and (
        value.value.upper() in {t.upper() for t in texts})


def gate_needs_guard(node: ast.Call) -> bool:
    """`fsm_ops.gate(..., gate=<SCG_VALIDATION 或非字面>, result=<非靜態 FAIL>)`。"""
    if call_name(node) != "gate" or _kw(node, "result") is None:
        return False
    gate = _kw(node, "gate")
    if isinstance(gate, ast.Constant) and gate.value != "SCG_VALIDATION":
        return False
    return not _is_const(_kw(node, "result"), "FAIL")


def is_baseline_adoption(rel: str, name: str, node: ast.Call,
                         fn: ast.FunctionDef | None) -> bool:
    """P1（D-126）：C2 唯一的新例外——`research/adopt.py` 的 `adopt_baseline` 以字面 `Stage-1`
    呼叫 `spec_frozen`，且函式內有 `is_outer_key` 守衛（外環鍵一律拒）。`approve_baseline` 永遠
    不在內。"""
    if rel != "research/adopt.py" or name != "spec_frozen" or fn is None:
        return False
    guard = any(isinstance(n, ast.Call) and call_name(n) == "is_outer_key" for n in ast.walk(fn))
    return fn.name == "adopt_baseline" and _is_const(_kw(node, "stage"), "Stage-1") and guard


def check_source(rel: str, text: str, *, exec_modules: frozenset[str] = EXEC_MODULES,
                 verbs: frozenset[str] | None = None) -> list[Hit]:
    verbs = sdd_cli.RESEARCH_VERBS if verbs is None else verbs
    tree, hits = ast.parse(text), []
    parents = parent_map(tree)
    if "FSM-STATE" in text:                                                      # C1
        hits += [Hit("C1", line) for line, _label in write_shaped_calls(tree)]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_research_env":   # C3
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            consts = {n.value for n in ast.walk(node) if isinstance(n, ast.Constant)}
            if not ({"RESEARCH_AUTO_RECOVERY_ENV"} & names or
                    "SDD_ENABLE_AUTO_RECOVERY" in consts) or "0" not in consts:
                hits.append(Hit("C3", node.lineno))
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id.startswith("RESEARCH_VERB") for t in node.targets):
            if isinstance(node.value, ast.Constant) and node.value.value not in verbs:   # C4
                hits.append(Hit("C4", node.lineno))
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        if name in {"approve_baseline", "spec_frozen"}:                          # C2
            fn = enclosing_function(node, parents)
            http = fn is not None and any(is_router_decorator(d) for d in fn.decorator_list)
            ok = (rel == "routers/research.py" and http) or (
                rel == "research/fsm_ops.py" and name == "spec_frozen") or (
                is_baseline_adoption(rel, name, node, fn))
            if not ok:
                hits.append(Hit("C2", node.lineno))
        if name in {"run_research_verb", "check_research_allowed", "build_research_argv"} and (
                node.args and isinstance(node.args[0], ast.Constant)
                and node.args[0].value not in verbs):                            # C4
            hits.append(Hit("C4", node.lineno))
        if name in _SPAWN_NAMES and (owner_name(node) == "subprocess" or name == "Popen"):   # C5
            flags = any(k.arg is None and isinstance(k.value, ast.Call)
                        and call_name(k.value) == "popen_platform_kwargs" for k in node.keywords)
            if not flags or rel not in exec_modules:
                hits.append(Hit("C5", node.lineno))
        if _kw(node, "shell") is not None and isinstance(_kw(node, "shell"), ast.Constant) and (
                _kw(node, "shell").value is True):                               # type: ignore[union-attr]
            hits.append(Hit("C6", node.lineno))
        if gate_needs_guard(node) and not is_guarded(node, parents):             # C7
            hits.append(Hit("C7", node.lineno))
    return hits


def app_sources() -> dict[str, str]:
    return {p.relative_to(APP_DIR).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(APP_DIR.rglob("*.py"))}


# ══ AT-960-13-E-1：判準函式的負控（合成違規逐一被回報、良性回空）═══════════════════════════════
VIOLATIONS = {
    "writes an FSM state file": (
        "research/x.py", "C1",
        "from pathlib import Path\n\ndef f(d):\n"
        "    Path(d / 'FSM-STATE-x.yaml').write_text('x', encoding='utf-8')\n"),
    "the orchestrator approves": (
        "research/orchestrator.py", "C2",
        "def run(ctx):\n    fsm_ops.approve_baseline(ctx, docs=[], root='', reason='r', "
        "approver='a')\n"),
    "a handler outside the router approves": (
        "research/gates.py", "C2",
        "@router.post('/x')\ndef h():\n    fsm_ops.approve_baseline(ctx)\n"),
    "recovery is not switched off": (
        "sdd_cli.py", "C3",
        "def build_research_env(base):\n    env = dict(base)\n    env['PYTHONPATH'] = 'x'\n"
        "    return env\n"),
    "an unregistered verb is called": (
        "research/x.py", "C4",
        "def f():\n    sdd_cli.run_research_verb('audit-log', [], sdd_root=r, state_dir=s, "
        "project='research-x')\n"),
    "an unregistered verb constant": ("sdd_cli.py", "C4", "RESEARCH_VERB_NEW = 'audit-log'\n"),
    "Popen without the platform flags": (
        "sdd_cli.py", "C5", "import subprocess\nsubprocess.Popen(argv, cwd=c)\n"),
    "Popen in a module that is not an exec module": (
        "research/orchestrator.py", "C5",
        "import subprocess\nsubprocess.Popen(argv, **procutil.popen_platform_kwargs())\n"),
    "shell=True": (
        "sdd_cli.py", "C6",
        "import subprocess\nsubprocess.run('echo', shell=True, "
        "**procutil.popen_platform_kwargs())\n"),
    "adopt.py freezes a Gate-0 stage": (
        "research/adopt.py", "C2",
        "def adopt_baseline(ctx):\n    if sdd_cli.is_outer_key(ctx.key):\n"
        "        raise ValueError\n"
        "    fsm_ops.spec_frozen(fctx, stage=\"Gate-0\", docs=[], root=\"r\", reason=\"x\", "
        "approver=\"a\")\n"),
    "adopt.py freezes without the inner-key guard": (
        "research/adopt.py", "C2",
        "def adopt_baseline(ctx):\n    fsm_ops.spec_frozen(fctx, stage=\"Stage-1\", docs=[], "
        "root=\"r\", reason=\"x\", approver=\"a\")\n"),
    "adopt.py freezes outside adopt_baseline": (
        "research/adopt.py", "C2",
        "def other(ctx):\n    if sdd_cli.is_outer_key(ctx.key):\n        raise ValueError\n"
        "    fsm_ops.spec_frozen(fctx, stage=\"Stage-1\", docs=[], root=\"r\", reason=\"x\", "
        "approver=\"a\")\n"),
    "adopt.py approves the baseline": (
        "research/adopt.py", "C2",
        "def adopt_baseline(ctx):\n    fsm_ops.approve_baseline(fctx)\n"),
    "another P1 module freezes Stage-1": (
        "research/route.py", "C2",
        "def run(ctx):\n    fsm_ops.spec_frozen(fctx, stage=\"Stage-1\", docs=[], root=\"r\", "
        "reason=\"x\", approver=\"a\")\n"),
    "gate SCG_VALIDATION PASS without a state guard": (
        "research/orchestrator.py", "C7",
        "def judge(ctx):\n    fsm_ops.gate(ctx, gate='SCG_VALIDATION', result='PASS', "
        "reason='x')\n"),
    "gate SCG_VALIDATION with a variable result and no guard": (
        "research/orchestrator.py", "C7",
        "def judge(ctx, verdict):\n    fsm_ops.gate(ctx, gate='SCG_VALIDATION', "
        "result=verdict, reason='x')\n"),
}
BENIGN = {
    "a guarded PASS": (
        "research/orchestrator.py",
        "def judge(ctx, state):\n    if state != 'HUMAN_PENDING':\n"
        "        fsm_ops.gate(ctx, gate='SCG_VALIDATION', result='PASS', reason='x')\n"),
    "a PASS in the else branch of an equality guard": (
        "research/orchestrator.py",
        "def judge(ctx, state):\n    if state == 'HUMAN_PENDING':\n        return\n    else:\n"
        "        fsm_ops.gate(ctx, gate='SCG_VALIDATION', result='PASS', reason='x')\n"),
    "a static FAIL needs no guard": (
        "research/orchestrator.py",
        "def judge(ctx):\n    fsm_ops.gate(ctx, gate='SCG_VALIDATION', result='FAIL', "
        "reason='x')\n"),
    "an inner-key gate is not subject": (
        "research/orchestrator.py",
        "def judge(ctx):\n    fsm_ops.gate(ctx, gate='PR_REVIEW', result='PASS', reason='x')\n"),
    "Popen with the flags in an exec module": (
        "runner.py",
        "import subprocess\nsubprocess.Popen(argv, **procutil.popen_platform_kwargs())\n"),
    "approve inside a router handler": (
        "routers/research.py",
        "@router.post('/x')\ndef h():\n    fsm_ops.approve_baseline(ctx)\n"),
    "adopt_baseline freezes Stage-1 behind the inner-key guard": (
        "research/adopt.py",
        "def adopt_baseline(ctx):\n    if sdd_cli.is_outer_key(ctx.key):\n"
        "        raise ValueError\n"
        "    fsm_ops.spec_frozen(fctx, stage=\"Stage-1\", docs=[], root=\"r\", reason=\"x\", "
        "approver=\"a\")\n"),
    "a registered verb": (
        "research/x.py", "def f():\n    sdd_cli.run_research_verb('show', [], sdd_root=r, "
                         "state_dir=s, project='research-x')\n"),
    "an env builder that disables recovery": (
        "sdd_cli.py",
        "def build_research_env(base):\n    env = dict(base)\n"
        "    env[RESEARCH_AUTO_RECOVERY_ENV] = '0'\n    return env\n"),
    "a read-only mention of a state file": (
        "research/x.py", "from pathlib import Path\n\ndef f(d):\n"
        "    return Path(d / 'FSM-STATE-x.yaml').read_text(encoding='utf-8')\n"),
}


@pytest.mark.parametrize("label", list(VIOLATIONS))
def test_AT_960_13_E_1_each_synthetic_violation_is_reported_with_its_rule(label: str) -> None:
    rel, rule, source = VIOLATIONS[label]
    assert rule in {h.rule for h in check_source(rel, source)}, label


@pytest.mark.parametrize("label", list(BENIGN))
def test_AT_960_13_E_1_each_benign_sample_is_clean(label: str) -> None:
    rel, source = BENIGN[label]
    assert check_source(rel, source) == [], label


def test_AT_960_13_E_1_the_scan_has_a_non_empty_scope() -> None:
    sources = app_sources()
    assert len(sources) > 20
    assert {"research/fsm_ops.py", "routers/research.py", "sdd_cli.py",
            "research/db.py"} <= set(sources)


# ══ AT-960-13-7：app/ 全樹實跑 ═══════════════════════════════════════════════════════════════
def test_AT_960_13_7_the_whole_app_tree_satisfies_every_rule() -> None:
    found = {rel: check_source(rel, text) for rel, text in app_sources().items()}
    assert {rel: hits for rel, hits in found.items() if hits} == {}, \
        "Bridge 不寫 FSM 狀態檔、不自行核准、子行程只經 procutil、gate PASS 有現態守衛"


def test_AT_960_13_7_the_approver_validator_refuses_what_the_contract_refuses() -> None:
    for bad in ("bridge", "BRIDGE", "agent", "System", "", "a b", "a+b", "x" * 101, "-rf",
                "tab\there"):
        with pytest.raises(Exception) as caught:
            sdd_cli.validate_research_approver(bad)
        assert getattr(caught.value, "body", {}).get("reason") == "invalid_request", repr(bad)
    for good in ("alice@example.com", "ops_01", "a" * 100, "a.b-c"):
        assert sdd_cli.validate_research_approver(good) == good


def test_AT_960_13_7_approver_validation_and_argv_assembly_share_one_function() -> None:
    tree = ast.parse(app_sources()["sdd_cli.py"])
    for name in ("research_freeze_args", "research_refreeze_args"):
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        calls = {call_name(n) for n in ast.walk(fn) if isinstance(n, ast.Call)}
        consts = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)}
        assert "validate_research_approver" in calls and "--approver" in consts, name


def test_AT_960_13_7_the_gate_pass_call_site_is_unique_and_lives_in_the_research_package() -> None:
    sites = []
    for rel, text in app_sources().items():
        sites += [(rel, n.lineno) for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.Call) and gate_needs_guard(n)]
    assert len(sites) <= 1, f"gate SCG_VALIDATION PASS 的呼叫點只有 evaluator 判定處一處：{sites}"
    assert all(rel.startswith("research/") for rel, _line in sites)


def test_AT_960_13_7_spawning_is_confined_to_the_registered_exec_modules() -> None:
    spawners = set()
    for rel, text in app_sources().items():
        for n in ast.walk(ast.parse(text)):
            if isinstance(n, ast.Call) and call_name(n) in _SPAWN_NAMES and (
                    owner_name(n) == "subprocess" or call_name(n) == "Popen"):
                spawners.add(rel)
    assert spawners <= EXEC_MODULES, spawners - EXEC_MODULES
    assert "research/fsm_ops.py" not in spawners, "研究面的 FSM 呼叫只經 sdd_cli 的入口"


# ══ AT-960-13-3 的 AST 判準：show 建檔只有一個 helper、呼叫者受限 ══════════════════════════════
def _calls_with_enclosing(name_test: object) -> list[tuple[str, str]]:
    out = []
    for rel, text in app_sources().items():
        tree = ast.parse(text)
        parents = parent_map(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and name_test(n):  # type: ignore[operator]
                fn = enclosing_function(n, parents)
                out.append((rel, fn.name if fn else "<module>"))
    return out


def test_AT_960_13_3_only_one_helper_builds_a_show_without_must_exist() -> None:
    creators = _calls_with_enclosing(
        lambda n: isinstance(_kw(n, "create"), ast.Constant) and _kw(n, "create").value is True)  # type: ignore[union-attr]
    assert set(creators) == {("research/fsm_ops.py", "create_key")}
    callers = _calls_with_enclosing(lambda n: call_name(n) == "create_key")
    # P1（AT-961-8-6）：呼叫者終點為 P0 三處（經 _ensure_fsm_key）加分流的 adopt.adopt_baseline＝4
    assert set(callers) == {("routers/research.py", "_ensure_fsm_key"),
                            ("research/adopt.py", "adopt_baseline")}
    ensure = _calls_with_enclosing(lambda n: call_name(n) == "_ensure_fsm_key")
    assert set(ensure) == {("routers/research.py", "_fsm_init_step")}
    init = _calls_with_enclosing(lambda n: call_name(n) == "_fsm_init_step")
    # P1 BR-D2：MAJOR SCR 的新研究專案（同 create_project 的初始化流程；`research_scr.make`）
    assert set(init) == {("routers/research.py", "create_project"),
                         ("routers/research.py", "_retry_init"),
                         ("routers/research.py", "_abandon_and_reinit"),
                         ("routers/research_scr.py", "make")}, \
        "建檔的呼叫者只有專案初始化（含重試初始化）、:reinit 換世代與 MAJOR SCR 的新專案"


# ══ AT-960-6-2：沒有 steps:advance 與寫游標的捷徑 ═══════════════════════════════════════════════
def test_AT_960_6_2_no_advance_endpoint_exists_on_the_bridge() -> None:
    spec = main_module.app.openapi()
    paths = set(spec["paths"])
    operations = {op.get("operationId", "") for item in spec["paths"].values()
                  for op in item.values() if isinstance(op, dict)}
    research_paths = {p for p in paths if p.startswith("/research")}
    assert len(research_paths) >= 10, "鎖要有標的"
    assert not [p for p in research_paths | operations if "advance" in p.lower()]


_CURSOR_UPDATE = frozenset({"flow_step", "flow_phase", "flow_status", "flow_detail"})
_SET_RE = re.compile(r"UPDATE\s+\{s\}\.research_projects\s+SET\s+(.+?)\s+WHERE",
                     re.IGNORECASE | re.DOTALL)


def _sets_a_cursor_column(sql: str) -> bool:
    match = _SET_RE.search(sql)
    return bool(match) and bool(_CURSOR_UPDATE & set(re.findall(r"(?:^|,)\s*(\w+)\s*=",
                                                                match.group(1))))


def test_AT_960_6_2_cursor_updates_live_only_in_the_research_package_beside_an_event_insert(
) -> None:
    found = 0
    for rel, text in app_sources().items():
        tree = ast.parse(text)
        constants = {t.id: n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name)
                     if isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
        updating = {name for name, sql in constants.items() if _sets_a_cursor_column(sql)}
        mentions = any(_sets_a_cursor_column(v) for v in constants.values())
        if mentions or re.search(r"UPDATE[^\n]{0,80}research_projects[^\n]{0,200}flow_", text):
            assert rel.startswith("research/"), f"{rel}：游標欄位的 UPDATE 只准出現在 app/research/"
        parents = parent_map(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and n.id in updating and isinstance(n.ctx, ast.Load):
                fn = enclosing_function(n, parents)
                assert fn is not None, rel
                inserts = {call_name(c) for c in ast.walk(fn) if isinstance(c, ast.Call)}
                assert "append_event" in inserts, \
                    f"{rel}:{fn.name} 更新游標卻沒有在同一個交易函式內寫 research_events"
                found += 1
    assert found >= 2, "鎖要有標的：至少兩處游標 UPDATE（一般更新與換世代）"

# ══ P1：分流新模組的 FSM 單一寫入面與 git／gh 唯一出口（TCS AT-961-8-5／8-6）══════════════════════
_FSM_WRITER_WORDS = ("spec-frozen", "spec-refreeze", "underspecified", "FSM-STATE")
#: P1 新模組中「不得是 FSM 寫入面」的檔（BR-D2 的 scr 等檔到位後自動納入）。
_NO_FSM_WRITE_MODULES = ("research/route.py", "research/scr.py", "research/decompose_plan.py",
                         "routers/research_route.py", "routers/research_scr.py",
                         # P2（BR-P2）：交付與自癒零 FSM 寫入；RELEASE 轉態住 inner_gates
                         "research/delivery.py", "research/healing.py")


def test_AT_961_8_6_new_p1_modules_do_not_import_the_fsm_runtime_or_name_its_write_verbs() -> None:
    sources = app_sources()
    present = [rel for rel in _NO_FSM_WRITE_MODULES if rel in sources]
    assert "research/route.py" in present and "routers/research_route.py" in present
    for rel in present:
        tree = ast.parse(sources[rel])
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        modules = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not any("fsm_runtime" in m for m in imported | modules), rel
        literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                    and isinstance(n.value, str)}
        for word in _FSM_WRITER_WORDS:
            assert not any(word in text for text in literals), f"{rel} 含字面值 {word!r}"


def test_AT_961_8_6_the_create_key_callers_end_at_four_places() -> None:
    callers = _calls_with_enclosing(lambda n: call_name(n) == "create_key")
    assert len(set(callers)) == 2, "create_key 的直接呼叫點：_ensure_fsm_key 與 adopt_baseline"
    init = _calls_with_enclosing(lambda n: call_name(n) == "_fsm_init_step")
    # P0 三處（create_project、_retry_init、_abandon_and_reinit）＋BR-D2 的 MAJOR SCR 新專案＝四處
    assert len(set(init)) == 4, "經 _ensure_fsm_key 的終點：P0 三處加 MAJOR SCR 的新研究專案"


def test_AT_961_8_6_only_adopt_py_freezes_a_stage_outside_the_router_and_fsm_ops() -> None:
    sites = []
    for rel, text in app_sources().items():
        sites += [(rel, call_name(n)) for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.Call) and call_name(n) in {"spec_frozen", "approve_baseline"}
                  and rel not in {"routers/research.py", "research/fsm_ops.py"}]
    assert set(sites) == {("research/adopt.py", "spec_frozen")}, sites


def test_AT_961_8_5_git_and_gh_subprocesses_live_only_in_gitops() -> None:
    spawners = set()
    for rel, text in app_sources().items():
        for n in ast.walk(ast.parse(text)):
            if isinstance(n, ast.Call) and call_name(n) in _SPAWN_NAMES and (
                    owner_name(n) == "subprocess" or call_name(n) == "Popen"):
                spawners.add(rel)
    assert "research/gitops.py" in spawners and "research/gitops.py" in EXEC_MODULES
    for rel in ("research/route.py", "research/adopt.py", "research/scaffold.py",
                "routers/research_route.py"):
        assert rel not in spawners, f"{rel} 不得自己 spawn（只經 gitops 與 fsm_ops）"


def test_AT_961_8_5_scaffold_templates_hold_no_python_files_under_app() -> None:
    """範本內的 Python 檔一律 `.tmpl`：否則 `app/` 全樹的 AST 鎖與能力登記會掃到它。"""
    tpl = APP_DIR / "research" / "scaffold_templates"
    assert any(tpl.rglob("*.tmpl")), "鎖要有標的：範本目錄有 .tmpl 檔"
    assert not list(tpl.rglob("*.py")), "範本目錄內不得有 .py 檔"


# ══ P2（PKG-BR-P2；AT-962-5-1～5-4、5-E-1、5-E-2）：內環登錄的 AST 規則 ══════════════════
_INNER_FORBIDDEN_CALLS = frozenset({"spec_frozen", "approve_baseline", "spec_refreeze",
                                    "create_key", "bring_to_agent_load"})
INNER_GATE_LITERALS = {"PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"}


def fsm_ops_calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and call_name(n) == name
            and owner_name(n) == "fsm_ops"]


def inner_gates_violations(text: str) -> list[str]:
    """`inner_gates.py` 的專屬規則：只呼叫 `fsm_ops.gate`／`fsm_ops.transition`（不凍結、不核准、不
    重凍、不建檔）；`gate=` 與 `to=` 必須是字面常數；三個 gate 字面各在一個 `if` 分支內。"""
    tree, found = ast.parse(text), []
    parents = parent_map(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and owner_name(node) == "fsm_ops":
            if call_name(node) in _INNER_FORBIDDEN_CALLS:
                found.append(f"forbidden:{call_name(node)}")
            if call_name(node) == "gate":
                value = _kw(node, "gate")
                if not (isinstance(value, ast.Constant) and value.value in INNER_GATE_LITERALS):
                    found.append("gate-not-literal")
                cur, in_if = parents.get(node), False
                while cur is not None and not isinstance(cur, ast.FunctionDef):
                    in_if = in_if or isinstance(cur, ast.If)
                    cur = parents.get(cur)
                if not in_if:
                    found.append("gate-not-in-branch")
            if call_name(node) == "transition" and not isinstance(_kw(node, "to"), ast.Constant):
                found.append("transition-to-not-literal")
    return found


def inner_gates_source() -> str:
    return app_sources()["research/inner_gates.py"]


def test_AT_962_5_1_inner_gates_has_three_literal_gate_calls_each_in_a_branch() -> None:
    tree = ast.parse(inner_gates_source())
    calls = fsm_ops_calls(tree, "gate")
    assert len(calls) == 3
    assert {_kw(c, "gate").value for c in calls} == INNER_GATE_LITERALS    # type: ignore[union-attr]
    assert not any(gate_needs_guard(c) for c in calls)
    assert check_source("research/inner_gates.py", inner_gates_source()) == []
    assert inner_gates_violations(inner_gates_source()) == []


def test_AT_962_5_2_inner_gates_only_calls_gate_and_transition() -> None:
    tree = ast.parse(inner_gates_source())
    written = {call_name(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
               and owner_name(n) == "fsm_ops"}
    assert not (written & _INNER_FORBIDDEN_CALLS)
    assert {"gate", "transition"} <= written
    assert inner_gates_violations(inner_gates_source()) == []


def test_AT_962_5_3_delivery_and_healing_have_no_fsm_writes_and_release_lives_in_inner_gates(
) -> None:
    sources = app_sources()
    for rel in ("research/delivery.py", "research/healing.py"):
        assert rel in _NO_FSM_WRITE_MODULES
        tree = ast.parse(sources[rel])
        names = {call_name(n) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert not names & {"transition", "gate", "spec_frozen", "spec_refreeze",
                            "approve_baseline"}, rel
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        modules = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not any("fsm_runtime" in m for m in imported | modules), rel
    tree = ast.parse(sources["research/inner_gates.py"])
    release = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "release_transition")
    transitions = [c for c in ast.walk(release) if isinstance(c, ast.Call)
                   and call_name(c) == "transition"]
    assert len(transitions) == 1 and _is_const(_kw(transitions[0], "to"), "RELEASE")
    all_to = [_kw(c, "to") for rel, text in sources.items() for c in ast.walk(ast.parse(text))
              if isinstance(c, ast.Call) and call_name(c) == "transition"
              and owner_name(c) == "fsm_ops" and rel != "research/inner_gates.py"]
    assert not [t for t in all_to if _is_const(t, "RELEASE")], "RELEASE 只住 inner_gates"


def test_AT_962_5_4_the_new_modules_never_spawn_and_exec_modules_stay_at_six() -> None:
    spawners = set()
    for rel, text in app_sources().items():
        for n in ast.walk(ast.parse(text)):
            if isinstance(n, ast.Call) and call_name(n) in _SPAWN_NAMES and (
                    owner_name(n) == "subprocess" or call_name(n) == "Popen"):
                spawners.add(rel)
    assert len(EXEC_MODULES) == 6 and spawners <= EXEC_MODULES
    assert not spawners & {"research/delivery.py", "research/healing.py",
                           "research/inner_gates.py", "routers/research_deliver.py"}


def test_AT_962_5_E_1_the_new_rules_bite_on_synthetic_violations_and_pass_clean_samples() -> None:
    variable_gate = ("def f(ctx, g):\n    fsm_ops.gate(ctx, gate=g, result='PASS', reason='x')\n")
    assert "C7" in {h.rule for h in check_source("research/inner_gates.py", variable_gate)}
    assert "gate-not-literal" in inner_gates_violations(variable_gate)
    freeze = ("def f(ctx):\n    fsm_ops.spec_frozen(ctx, stage='Stage-1', docs=[], root='r',"
              " reason='x', approver='a')\n")
    assert "C2" in {h.rule for h in check_source("research/delivery.py", freeze)}
    assert "forbidden:spec_frozen" in inner_gates_violations(freeze)
    spawn = "import subprocess\nsubprocess.Popen(argv, **procutil.popen_platform_kwargs())\n"
    assert "C5" in {h.rule for h in check_source("research/healing.py", spawn)}
    clean = ("def f(ctx, s):\n    if s == 'a':\n        fsm_ops.gate(ctx, gate='PR_REVIEW',"
             " result='PASS', reason='x')\n    else:\n        fsm_ops.transition(ctx, to='RELEASE',"
             " reason='x')\n")
    assert check_source("research/inner_gates.py", clean) == []
    assert inner_gates_violations(clean) == []
    no_branch = "def f(ctx):\n    fsm_ops.gate(ctx, gate='PR_REVIEW', result='PASS', reason='x')\n"
    assert "gate-not-in-branch" in inner_gates_violations(no_branch)


def test_AT_962_5_E_2_the_delivery_record_op_writes_an_event_beside_every_cursor_write() -> None:
    tree = ast.parse(app_sources()["research/db.py"])
    op = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_op_delivery_record")
    assert "append_event" in {call_name(c) for c in ast.walk(op) if isinstance(c, ast.Call)}
    test_AT_960_6_2_cursor_updates_live_only_in_the_research_package_beside_an_event_insert()
