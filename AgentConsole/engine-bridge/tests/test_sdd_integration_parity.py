"""BR-31／BR-32／BR-33：跨專案一致性對拍（契約 v1.5 §5〈跨專案一致性對拍測試清單〉F-1～F-12）。

Bridge 是唯一同時看得到兩個引擎的元件，所以這些斷言放在這裡（不碰根層 tools/tests）。前半用**真的
adapter（行程內）**加假 SDD 樹的假 CLI；檔尾〈真的 SDD CLI〉改用**真的 SDD CLI（子行程）**，狀態目錄
在暫存目錄。真 CLI（Dev-SDD-RT）已由主控親驗並 commit，那組測試預設就跑；唯一的略過條件是它在這個
環境 import 不了（缺相依套件），略過時會印出原因。

對拍編號與檔案的對應：
  本檔：F-1 欄位對拍、F-2 只認指定者、F-3 凍結後改檔、F-4 只經 CLI（AST 鎖）、F-6 摘要演算法、
        F-7 權杖與環境不外洩、F-9／F-10 的缺口列、F-11 AT 文法與歸屬、唯讀端點不動狀態檔；
        F-5 phase 表是 W4 dogfood 的產物，現為略過。
  F-8 名稱規則：tests/test_fsm_names.py（與 SDD sanitize_component 以路徑載入逐一對拍）＋
  tests/test_sdd_fsm.py。
  F-9／F-10 其餘列：tests/test_sdd_run.py、tests/test_sdd_run_lifecycle.py、tests/test_sdd_sync.py。
  F-12 CLI rc→HTTP：tests/test_sdd_cli.py（假 CLI）與本檔檔尾（真 CLI 對拍）。
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

import app as app_package
from app import sdd_cli, sdd_sync, spec_digest
from tests.conftest import TERMINAL
from tests.fake_sdd import read_calls, seed_state, set_control
from tests.sdd_run_support import (
    FSM_REL,
    TCS_NAME,
    TCS_REL,
    TCS_TEXT,
    TOKEN,
    alert_codes,
    argv_of,
    audit_entries,
    build_handle,
    contracts_dir,
    digest_of,
    flag,
    fsm_state,
    make_project,
    post,
    sdd_body,
    sdd_context,
    seed_frozen,
    trace_calls,
    verbs,
    wait_fsm,
    workspace_has,
)

APP_DIR = Path(app_package.__file__).resolve().parent

RICH_TCS = """# Test Contract Specification — Parity

**spec-format-version**: 1.0
**scenario**: brownfield

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 登入成功 | AT-001-1-1 | 正常登入 | ✅ | Unit | □ |
| AC-001-1 | 登入成功 | AT-001-1-2 | 錯誤密碼 | ✅ | Integration | □ |
| AC-002-1 | 餘額警示 | AT-002-1-1 | 回應時間 | ✅ | E2E | □ |
| AC-002-1 | 餘額警示 | AT-002-1-E-1 | 邊界 | ✅ | Unit | □ |

## 2. AT 格式

```gherkin
# AT-001-1-1
Scenario: 正常登入
  Given 使用者在登入頁面
  When 輸入正確帳密
  Then 回傳 201 Created
```

```gherkin
# AT-001-1-2
Scenario: 錯誤密碼
  Given 使用者在登入頁面
  When 輸入錯誤密碼
  Then 顯示錯誤訊息「密碼錯誤」
```

```gherkin
# AT-002-1-1
Scenario: 回應時間
  Given 系統在尖峰負載
  When 查詢餘額
  Then 回應時間 < 200ms
```

```gherkin
# AT-002-1-E-1
Scenario: 邊界
  Given 餘額為零
  When 查詢餘額
  Then 不應顯示「內部錯誤」
```
"""

#: 有 Gherkin 標頭、卻沒有 §1 映射列的 AT：adapter 的 `unmapped_at_ids`（no_row）。
GHOST_BLOCK = """
```gherkin
# AT-009-1-1
Scenario: 沒有映射列的孤兒
  Given 某前置
  Then 輸出 "[AT_OK_9]"
```
"""

COMPARED_FIELDS = ("step_id", "name", "expected_output_regex", "evaluator_command", "max_retries",
                   "maintain_context", "spec_digest", "weak_regex")


def project(tmp_path: Path, *, text: str = TCS_TEXT, name: str = "p",
            state: str | None = "IMPLEMENTATION", digests: bool = True, key: str = "alpha",
            frozen_text: str | None = None) -> Path:
    """專案根（在 allowed roots 下）：規格 `text` 放在 contracts 目錄；`state` 給了就以
    `frozen_text`（預設＝
    `text`）的摘要凍結成該狀態（`None`＝完全沒有狀態目錄）。"""
    root = make_project(tmp_path / "projects", name, text)
    if state is not None:
        seed_frozen(root, state, key=key, digests=digests, text=frozen_text or text)
    return root


def compile_http(live, root: Path, **body: Any):
    return live.client.post("/sdd/compile", json={"spec_dir": str(contracts_dir(root)), **body})


def run_compile_cli(spec_dir: Path, out: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """`python -m autoclaude.tools.sdd_compile`（子行程）；環境不帶 `SDD_PROJECT`／`SDD_STATE_DIR`，
    專案鍵一律由 `--fsm-project` 顯式給（與 Bridge 的呼叫約定同一條）。"""
    env = {k: v for k, v in os.environ.items() if k not in ("SDD_PROJECT", "SDD_STATE_DIR")}
    env.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    return subprocess.run(
        [sys.executable, "-m", "autoclaude.tools.sdd_compile", "--spec-dir", str(spec_dir),
         "--out", str(out), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, env=env,
        stdin=subprocess.DEVNULL, check=False)


# ── F-1：同一份 TCS，Console 路徑與 sdd_compile CLI 逐任務欄位相等（G-08）─────────────────────────
def test_compile_endpoint_and_the_compile_cli_agree_task_for_task(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS)
    out = tmp_path / "out" / "playbook.yaml"
    done = run_compile_cli(contracts_dir(root), out, "--fsm-project", "alpha")
    assert done.returncode == 0, done.stderr
    cli = yaml.safe_load(out.read_text(encoding="utf-8"))
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    http_tasks = [{k: v for k, v in t.items() if k != "prompt"} for t in body["tasks"]]
    cli_tasks = [{k: v for k, v in t.items() if k != "prompt"} for t in cli["tasks"]]
    assert len(http_tasks) == 4 and http_tasks == cli_tasks
    for name in COMPARED_FIELDS:                      # 契約 F-1 指名的八欄（prompt 不比）逐欄相等
        assert [t.get(name) for t in http_tasks] == [t.get(name) for t in cli_tasks], name
    assert any(t.get("weak_regex") for t in http_tasks), "樣本要真的涵蓋 weak_regex 這一欄"
    assert {t.get("max_retries") for t in http_tasks} == {2, 5}, \
        "E2E 走 SCG-5（2）、其餘 SCG-4（5）"
    assert [t["maintain_context"] for t in http_tasks] == [False, True, False, True]
    digest8 = body["digest"].split(":")[-1][:8]
    goal = (f"完成 {body['scenario']} 場景全部 {len(body['tasks'])} 條 AT 契約"
            f"（規格 digest {digest8}）")
    assert cli["global_goal"] == goal, "場景、步驟數與摘要兩邊相同"
    assert body["scenario"] == "brownfield" and body["unmapped_at_ids"] == []


def test_a_named_spec_file_is_chosen_the_same_way_on_both_paths(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS, digests=False)
    other = contracts_dir(root) / "TCS-Other.md"
    other.write_text(TCS_TEXT, encoding="utf-8", newline="")
    out = tmp_path / "out.yaml"
    done = run_compile_cli(contracts_dir(root), out, "--spec-file", "TCS-Other.md",
                           "--fsm-project", "alpha")
    assert done.returncode == 0, done.stderr
    cli = yaml.safe_load(out.read_text(encoding="utf-8"))
    resp = compile_http(bridge, root, spec_file="TCS-Other.md", fsm_project="alpha")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [t["step_id"] for t in body["tasks"]] == [t["step_id"] for t in cli["tasks"]]
    assert body["spec_file"] == "TCS-Other.md" and Path(body["spec_path"]) == other.resolve()
    assert Path(cli["workflow_path"]) == other.resolve(), "指定了規格檔：workflow_path 是檔案路徑"
    assert len(body["tasks"]) == 2, "沒指定時 adapter 會因兩份官方命名而拒絕；指定後只編那一份"


def build_failure_case(case: str, tmp_path: Path) -> Path:
    if case == "unfrozen":
        return project(tmp_path, text=RICH_TCS, state=None)
    if case == "digest-changed":
        root = project(tmp_path, text=RICH_TCS, state=None)
        seed_frozen(root, "IMPLEMENTATION", text=RICH_TCS + "\n<!-- 凍結之後才加的一行 -->\n")
        return root
    if case == "unsupported-format-version":
        text = RICH_TCS.replace("**spec-format-version**: 1.0", "**spec-format-version**: 2.0")
        return project(tmp_path, text=text)
    if case == "ambiguous-spec":
        root = project(tmp_path, text=RICH_TCS)
        (contracts_dir(root) / "TEST-CONTRACT-SPEC-Other.md").write_text(
            TCS_TEXT, encoding="utf-8", newline="")
        return root
    root = tmp_path / "projects" / "p"                  # no-spec-at-all
    contracts_dir(root).mkdir(parents=True)
    return root


FAILURE_CASES = [
    ("unfrozen", 2, 422, "spec_not_frozen"),
    ("digest-changed", 2, 409, "spec_digest_changed"),
    ("unsupported-format-version", 5, 422, "spec_format_version_unsupported"),
    ("ambiguous-spec", 4, 422, "spec_ambiguous"),
    ("no-spec-at-all", 4, 422, "spec_not_found"),
]


@pytest.mark.parametrize(("case", "rc", "status", "reason"), FAILURE_CASES,
                         ids=[c[0] for c in FAILURE_CASES])
def test_the_cli_exit_code_and_the_http_error_say_the_same_thing(
        case: str, rc: int, status: int, reason: str, bridge, tmp_path: Path) -> None:
    root = build_failure_case(case, tmp_path)
    out = tmp_path / "o.yaml"
    cli = run_compile_cli(contracts_dir(root), out, "--fsm-project", "alpha")
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert (cli.returncode, resp.status_code, resp.json()["reason"]) == (rc, status, reason), (
        cli.stderr, resp.text)
    assert not out.exists(), "CLI 失敗時不寫輸出檔"


def test_an_unmapped_at_is_rc6_for_the_cli_but_a_listed_200_for_the_bridge(
        bridge, tmp_path: Path) -> None:
    """刻意的不對稱（ADR §8.2）：CLI 是編譯期硬閘（fail-closed、不寫檔）；Bridge 是消費端，回 200
    並列出，是否阻擋由 Backend／人決定（匯入解析結果的 `warnings[]`）。"""
    root = project(tmp_path, text=RICH_TCS + GHOST_BLOCK)
    out = tmp_path / "o.yaml"
    cli = run_compile_cli(contracts_dir(root), out, "--fsm-project", "alpha")
    assert cli.returncode == 6 and "AT-009-1-1" in cli.stderr and not out.exists()
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert resp.status_code == 200, resp.text
    assert resp.json()["unmapped_at_ids"] == ["AT-009-1-1"]
    assert len(resp.json()["tasks"]) == 4, "已編成的 AT 照常產出任務"


# ── F-2：只認指定者（G-02）──────────────────────────────────────────────────────────────────
def test_only_the_named_project_decides_whether_the_spec_is_frozen(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS, state=None)
    seed_state(root / FSM_REL, "m-alpha", "INIT")                      # 另一個專案，尚未凍結
    seed_frozen(root, "SPEC_FROZEN", key="m-zeta", text=RICH_TCS)
    refused = compile_http(bridge, root, fsm_project="m-alpha")
    assert (refused.status_code, refused.json()["reason"]) == (422, "spec_not_frozen"), \
        "m-zeta 已凍結不得讓 m-alpha 放行"
    accepted = compile_http(bridge, root, fsm_project="m-zeta")
    assert accepted.status_code == 200, accepted.text
    found = accepted.json()
    assert (found["fsm_project"], found["frozen_digest"]) == ("m-zeta", "verified")
    ambiguous = compile_http(bridge, root)
    assert (ambiguous.status_code, ambiguous.json()["reason"]) == (422, "spec_not_frozen")
    assert "不唯一" in ambiguous.json()["detail"]
    nope = compile_http(bridge, root, fsm_project="nope")
    assert nope.status_code == 422 and "m-alpha" in nope.json()["detail"], "訊息列出現有專案鍵"
    assert "m-zeta" in nope.json()["detail"]


def test_a_directory_with_a_single_state_file_needs_no_project_key(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS, key="solo")
    resp = compile_http(bridge, root)
    assert resp.status_code == 200, resp.text
    assert resp.json()["fsm_project"] == "solo" and resp.json()["frozen_digest"] == "verified"


def test_an_original_project_name_finds_the_sanitized_state_file(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS, key="a_b")                 # SDD 側 `a:b` → 檔名 `a_b`
    for original in ("a:b", "a_b"):
        resp = compile_http(bridge, root, fsm_project=original)
        assert resp.status_code == 200, (original, resp.text)
        assert resp.json()["fsm_project"] == "a_b", "回應帶淨化後的鍵（寫回綁定用）"


def test_a_missing_project_file_never_falls_back_to_a_parent_directorys_state(
        bridge, tmp_path: Path) -> None:
    """找不到時**不再往上層目錄找**：子專案目錄有自己的狀態檔（別的專案），父目錄有 x 的已凍結狀態——
    對子專案的規格問 x，不得穿過去借用父目錄的 x。"""
    parent = project(tmp_path, text=RICH_TCS, key="x")
    child = make_project(parent, "sub", RICH_TCS)
    seed_state(child / FSM_REL, "y", "INIT")
    resp = compile_http(bridge, child, fsm_project="x")
    assert (resp.status_code, resp.json()["reason"]) == (422, "spec_not_frozen")
    assert compile_http(bridge, parent, fsm_project="x").status_code == 200, \
        "對照：父專案自己讀得到"


# ── F-3：凍結後改檔（G-06）——adapter 面（真 CLI 凍結的那一面在檔尾〈真的 SDD CLI〉）───────────────
def test_editing_a_frozen_spec_turns_compile_into_409_until_the_content_is_restored(
        bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS)
    path = contracts_dir(root) / TCS_NAME
    ok = compile_http(bridge, root, fsm_project="alpha")
    assert (ok.status_code, ok.json()["frozen_digest"]) == (200, "verified")
    path.write_text(RICH_TCS.replace("正常登入", "正常登入（改）"), encoding="utf-8", newline="")
    changed = compile_http(bridge, root, fsm_project="alpha")
    assert changed.status_code == 409, changed.text
    body = changed.json()
    assert body["reason"] == "spec_digest_changed" and body["pair"] == "frozen_vs_file"
    assert body["detail"]["pair"] == "frozen_vs_file", "頂層與 detail 兩處同形"
    path.write_text(RICH_TCS, encoding="utf-8", newline="")
    assert compile_http(bridge, root, fsm_project="alpha").status_code == 200, "還原內容後恢復"


def test_a_spec_that_is_not_in_the_freeze_list_is_422_not_frozen(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS, state=None)
    seed_state(root / FSM_REL, "alpha", "IMPLEMENTATION", frozen_stages=[{
        "stage": "S", "spec_docs": ["docs/other.md"],
        "spec_doc_digests": {"docs/other.md": "sha256:" + "0" * 64}}])
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert (resp.status_code, resp.json()["reason"]) == (422, "spec_not_frozen")
    assert "不在凍結清單" in resp.json()["detail"]


def test_an_old_state_file_without_digests_passes_with_frozen_digest_absent(
        bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=RICH_TCS, digests=False)
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert (resp.status_code, resp.json()["frozen_digest"]) == (200, "absent")


# ── F-4：只經 CLI——對 app/ 原始碼的 AST 鎖（Rule 9 絕對禁令 #1；D-115-01）────────────────────────
_ATTR_WRITES = frozenset({"write_text", "write_bytes", "unlink", "touch", "rename", "write",
                          "writelines", "truncate"})
_OS_WRITES = frozenset({"replace", "rename", "remove", "unlink", "truncate", "open", "write"})
_SHUTIL_WRITES = frozenset({"move", "copy", "copy2", "copyfile", "copytree", "rmtree"})
_STREAM_DUMPS = frozenset({("json", "dump"), ("yaml", "dump"), ("yaml", "safe_dump")})


def _mode_node(call: ast.Call, positional: int) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == "mode":
            return keyword.value
    return call.args[positional] if len(call.args) > positional else None


def write_shaped_calls(tree: ast.AST) -> list[tuple[int, str]]:
    """寫入形態呼叫（契約 F-4）：`open` 寫／附加／獨佔／更新模式（模式不是字面值也算）、
    `write_text`／
    `write_bytes`／`unlink`／`touch`／`rename`／`write*`、`os.replace` 等、`shutil` 複製移動、
    `json.dump`／`yaml.dump`（寫進串流）、本專案自己的 `write_json_atomic`。"""
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(
            func, ast.Attribute) else None
        owner = func.value.id if isinstance(func, ast.Attribute) and isinstance(
            func.value, ast.Name) else None
        if name is None:
            continue
        if name == "open" and owner != "os":
            mode = _mode_node(node, 1 if isinstance(func, ast.Name) else 0)
            if mode is None:
                continue
            literal = mode.value if isinstance(mode, ast.Constant) and isinstance(
                mode.value, str) else None
            if literal is None or set(literal) & set("wax+"):
                hits.append((node.lineno, f"open(mode={literal!r})"))
        elif ((owner == "os" and name in _OS_WRITES)
              or (owner == "shutil" and name in _SHUTIL_WRITES)):
            hits.append((node.lineno, f"{owner}.{name}"))
        elif (owner, name) in _STREAM_DUMPS:
            hits.append((node.lineno, f"{owner}.{name}"))
        elif name in _ATTR_WRITES or name == "write_json_atomic":
            hits.append((node.lineno, name))
    return hits


def app_modules() -> dict[str, tuple[str, ast.Module]]:
    modules: dict[str, tuple[str, ast.Module]] = {}
    for path in sorted(APP_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        modules[path.relative_to(APP_DIR).as_posix()] = (text, ast.parse(text))
    return modules


VIOLATING_SAMPLES = {
    "open-w": 'open(p, "w")', "open-mode-keyword": 'open(p, mode="a")',
    "path-open-x": 'p.open("x")', "open-update": 'open(p, "r+")',
    "open-dynamic-mode": "open(p, mode_from_somewhere)", "write_text": 'p.write_text("x")',
    "write_bytes": 'p.write_bytes(b"x")', "os.replace": "os.replace(a, b)",
    "os.rename": "os.rename(a, b)", "path.rename": "p.rename(q)",
    "shutil.move": "shutil.move(a, b)",
    "shutil.copy2": "shutil.copy2(a, b)", "unlink": "p.unlink()", "os.remove": "os.remove(p)",
    "touch": "p.touch()", "handle.write": 'fh.write("x")',
    "yaml.safe_dump": "yaml.safe_dump(d, fh)",
    "json.dump": "json.dump(d, fh)", "write_json_atomic": "write_json_atomic(p, d)",
}
BENIGN_SAMPLES = ["open(p)", 'open(p, "r")', 'open(p, "rb")', 'open(p, mode="r", encoding="utf-8")',
                  "p.read_text()", "yaml.safe_load(t)", 'text.replace("a", "b")', "json.dumps(d)"]


@pytest.mark.parametrize("sample", list(VIOLATING_SAMPLES), ids=list(VIOLATING_SAMPLES))
def test_the_write_scanner_turns_red_on_each_deliberately_violating_sample(sample: str) -> None:
    assert write_shaped_calls(ast.parse(VIOLATING_SAMPLES[sample])), "掃描器必須抓得到這個寫入形態"


@pytest.mark.parametrize("sample", BENIGN_SAMPLES)
def test_the_write_scanner_lets_read_only_calls_through(sample: str) -> None:
    assert write_shaped_calls(ast.parse(sample)) == []


def test_no_module_that_names_a_state_file_contains_a_write_shaped_call() -> None:
    named = {rel: tree for rel, (text, tree) in app_modules().items() if "FSM-STATE" in text}
    assert {"sdd_state.py", "sdd_cli.py", "routers/sdd.py"} <= set(named), \
        "鎖要有標的：這些模組都提到 FSM-STATE 檔名，必須在掃描範圍內"
    violations = {rel: write_shaped_calls(tree) for rel, tree in named.items()}
    assert {rel: hits for rel, hits in violations.items() if hits} == {}, \
        ("Rule 9 絕對禁令 #1：Bridge 原始碼不得直接寫 FSM-STATE-*.yaml；"
         "狀態變更一律經 FSMRuntime CLI")


def test_only_sdd_cli_names_the_cli_module() -> None:
    mentions = sorted(rel for rel, (text, _tree) in app_modules().items()
                      if "tools.fsm_runtime" in text)
    assert mentions == ["sdd_cli.py"], "子行程呼叫處只有一個，且受 ALLOWED_VERBS 限制"
    assert sdd_cli.CLI_MODULE == "tools.fsm_runtime.fsm_runtime"


def _run_verb_sites(rel: str, tree: ast.Module) -> list[tuple[str, str]]:
    """(外層函式限定名, 第一個引數的種類)：`const`＝`VERB_*` 常數、`literal`＝字串字面值、
    `other`。"""
    sites: list[tuple[str, str]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def _scoped(self, node: ast.AST, name: str) -> None:
            self.stack.append(name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._scoped(node, node.name)

        visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(
                func, ast.Attribute) else None
            if name == "run_verb" and rel != "sdd_cli.py":
                first = node.args[0] if node.args else None
                ident = first.id if isinstance(first, ast.Name) else first.attr if isinstance(
                    first, ast.Attribute) else None
                if ident is not None and ident.startswith("VERB_"):
                    kind = "const"
                elif isinstance(first, ast.Constant) and isinstance(first.value, str):
                    kind = "literal"
                else:
                    kind = "other"
                sites.append((".".join(self.stack), kind))
            self.generic_visit(node)

    Visitor().visit(tree)
    return sites


def test_every_cli_call_site_passes_a_whitelisted_verb_constant() -> None:
    found = {(rel, qualname, kind) for rel, (_text, tree) in app_modules().items()
             for qualname, kind in _run_verb_sites(rel, tree)}
    assert found == {
        ("routers/sdd.py", "_freeze", "const"),
        ("sdd_run.py", "exit_delegation", "const"),
        ("sdd_run.py", "execute_delegation.call", "other"),
    }, f"新增或改動 CLI 呼叫處必須同步審這張表（字串字面值的動詞一律不收）：{sorted(found)}"
    assert sdd_cli.ALLOWED_VERBS == {
        "spec-frozen", "negotiate-enter", "negotiate-exit", "delegate-enter", "delegate-exit"}


def test_the_one_indirect_call_site_can_only_be_fed_whitelisted_non_freeze_verbs() -> None:
    """`execute_delegation.call(verb, …)` 的 verb 來自預檢表與回收點：表裡只有白名單內、且不含
    spec-frozen 的動詞。"""
    from_table = {verb for steps in sdd_sync.PREFLIGHT_STEPS.values() for verb in steps}
    assert from_table <= sdd_cli.ALLOWED_VERBS - {sdd_cli.VERB_SPEC_FROZEN}
    _text, tree = app_modules()["sdd_run.py"]
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id.startswith("VERB_")}
    assert "VERB_SPEC_FROZEN" not in used and used, \
        "sdd_run.py 只用 negotiate／delegate 四個動詞常數"


def test_spec_frozen_is_reachable_only_from_the_freeze_route() -> None:
    """`spec-frozen` 是唯一能寫入「人已核准的內容」的動詞：HTTP 上只有 `:freeze` 一條路到它。"""
    modules = app_modules()
    referencing = sorted(rel for rel, (_t, tree) in modules.items() if any(
        (isinstance(n, ast.Name) and n.id in ("VERB_SPEC_FROZEN", "freeze_args"))
        or (isinstance(n, ast.Attribute) and n.attr in ("VERB_SPEC_FROZEN", "freeze_args"))
        or (isinstance(n, ast.alias) and n.name in ("VERB_SPEC_FROZEN", "freeze_args"))
        for n in ast.walk(tree)))
    assert referencing == ["routers/sdd.py", "sdd_cli.py"]
    literal = sorted(rel for rel, (_t, tree) in modules.items() if any(
        isinstance(n, ast.Constant) and n.value == "spec-frozen" for n in ast.walk(tree)))
    assert literal == ["sdd_cli.py"], "字串字面值 'spec-frozen' 只准在常數定義處出現"


def test_no_module_can_build_a_negotiate_exit_other_than_agreed() -> None:
    for rel, (_text, tree) in app_modules().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "underspecified":
                pytest.fail(f"{rel}:{node.lineno} 出現 'underspecified' 字面值"
                            "——Bridge 一律不呼叫它")
    assert sdd_cli.negotiate_exit_args(reason="r")[:2] == ["--outcome", "agreed"]
    with pytest.raises(Exception) as caught:
        sdd_cli.check_allowed("negotiate-exit", ["--outcome", "underspecified", "--reason", "r"])
    assert getattr(caught.value, "body", {}).get("reason") == "sdd_cli_usage"


# ── 唯讀端點前後，FSM 狀態檔的 mtime 與大小完全相同（契約 E2E-17 第 24 列） ────────────────────
def _snapshot(directory: Path) -> dict[str, tuple[int, int]]:
    return {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(directory.glob("*"))}


def test_read_only_endpoints_leave_every_state_file_untouched(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    seed_state(sdd_proj / FSM_REL, "other", "INIT")
    rid = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1")).json()["run_id"]
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    before, calls = _snapshot(sdd_proj / FSM_REL), len(read_calls(sdd_fake))
    client = sdd_live.client
    params = {"root": str(sdd_proj)}
    for path in ("/sdd/version", "/sdd/fsm", "/sdd/fsm/alpha", "/sdd/fsm/other",
                 f"/autoclaude/runs/{rid}", f"/autoclaude/runs/{rid}/rtm",
                 f"/autoclaude/runs/{rid}/events", f"/autoclaude/runs/{rid}/checkpoints"):
        query = params if path.startswith("/sdd/fsm") else None
        assert client.get(path, params=query).status_code in (200, 404, 503), path
    assert compile_http(sdd_live, sdd_proj, fsm_project="alpha").status_code == 200
    assert _snapshot(sdd_proj / FSM_REL) == before, "讀取類端點不得改動任何狀態檔（含 mtime）"
    assert len(read_calls(sdd_fake)) == calls, "讀取類端點連 CLI 子行程都不該起"


# ── F-5：phase 表（W4 dogfood 的產物；本輪 `phase` 恆為 null） ────────────────────
@pytest.mark.skip(reason="W4：T-G phase 純函式與表尚未落地"
                         "（本輪 GET /sdd/fsm/{project} 的 phase 恆 null）")
def test_the_phase_table_matches_the_sdd_latest_state_sets() -> None:
    raise AssertionError("W4 落地後實作：OBSERVATION_STATES／_BLOCKING_STATES／_HAPPY_PATH 對拍")


# ── F-6：摘要演算法對拍（G-06）——adapter 與 Bridge 面（CLI 凍結寫入的那一面在〈真的 SDD CLI〉）
_BOM = b"\xef\xbb\xbf"
DIGEST_VARIANTS: dict[str, tuple[bytes, bool]] = {
    # 名稱 → (檔案 bytes, 是否帶 BOM)；內容含非 ASCII（TCS_TEXT 的中文）
    "lf": (TCS_TEXT.encode("utf-8"), False),
    "crlf": (TCS_TEXT.replace("\n", "\r\n").encode("utf-8"), False),
    "cr": (TCS_TEXT.replace("\n", "\r").encode("utf-8"), False),
    "bom-lf": (_BOM + TCS_TEXT.encode("utf-8"), True),
    "bom-crlf": (_BOM + TCS_TEXT.replace("\n", "\r\n").encode("utf-8"), True),
}


def expected_digest(bom: bool) -> str:
    """獨立實作的期望摘要：換行正規化、BOM 不剝（BOM 以 chr(0xFEFF) 組出，原始碼裡不放隱形字
    元）。"""
    return digest_of((chr(0xFEFF) if bom else "") + TCS_TEXT)


@pytest.mark.parametrize("variant", list(DIGEST_VARIANTS))
def test_adapter_digest_equals_the_bridge_digest_for_all_five_byte_variants(
        variant: str, bridge, tmp_path: Path) -> None:
    raw, bom = DIGEST_VARIANTS[variant]
    root = project(tmp_path, digests=False)
    path = contracts_dir(root) / TCS_NAME
    path.write_bytes(raw)
    expected = expected_digest(bom)          # 獨立實作：正規化換行、BOM 不剝
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert resp.status_code == 200, resp.text
    assert resp.json()["digest"] == spec_digest.file_digest(path) == expected
    raw_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if b"\r" in raw:
        assert raw_digest != expected, \
            "反向對照：含 CR 的檔，原始 bytes 的摘要必須不同（否則實作退回了原始 bytes）"
    else:
        assert raw_digest == expected, "LF 與 BOM+LF 的原始 bytes 恰好等於正規化後的文字"


@pytest.mark.parametrize("variant", list(DIGEST_VARIANTS))
def test_freeze_accepts_the_normalized_digest_as_expected_for_every_variant(
        variant: str, sdd_live, sdd_fake: Path, sdd_proj: Path) -> None:
    raw, bom = DIGEST_VARIANTS[variant]
    (contracts_dir(sdd_proj) / TCS_NAME).write_bytes(raw)
    seed_state(sdd_proj / FSM_REL, "alpha", "HUMAN_PENDING")
    expected = expected_digest(bom)
    resp = sdd_live.client.post(
        "/sdd/fsm/alpha:freeze", headers={"X-Bridge-Token": TOKEN},
        json={"root": str(sdd_proj), "docs": [TCS_REL], "approver": "operator", "reason": "核准",
              "expected_digests": {TCS_REL: expected}})
    assert resp.status_code == 200, resp.text
    assert resp.json()["spec_doc_digests"] == {TCS_REL: expected}, \
        "Bridge 預檢重算的現檔摘要＝CLI 寫入的摘要，換行與 BOM 差異不造成假性不符"


# ── F-7：權杖與環境不外洩（G-09）──────────────────────────────────────────────────────────────
def test_a_polluted_bridge_environment_never_reaches_the_engine_or_the_cli_children(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_SDD_WRITE_TOKEN", TOKEN)
    monkeypatch.setenv("SDD_STATE_DIR", str(tmp_path / "somewhere-else"))
    monkeypatch.setenv("SDD_PROJECT", "exported-by-a-developer")
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    plain_trace, sdd_trace = tmp_path / "plain.jsonl", tmp_path / "sdd.jsonl"
    plain = sdd_live.post_run(run_body(delay="0.1", trace=plain_trace)).json()["run_id"]
    resp = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.1",
                                   env={"MOCK_CLAUDE_TRACE": str(sdd_trace)}))
    assert resp.status_code == 201, resp.text
    for rid in (plain, resp.json()["run_id"]):
        assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    clean = {"SDD_PROJECT": None, "SDD_STATE_DIR": None, "has_write_token": False}
    assert {str(r["sdd_env"]) for r in trace_calls(plain_trace)} == {str(clean)}, \
        "不含 sdd 區塊的 run：子行程環境三者皆無"
    expected_env = str({**clean, "SDD_PROJECT": "alpha"})
    assert {str(r["sdd_env"]) for r in trace_calls(sdd_trace)} == {expected_env}, \
        "含 sdd 區塊的 run：只有 SDD_PROJECT，值是本批次的鍵"
    for call in read_calls(sdd_fake):
        assert call["env"]["SDD_STATE_DIR"] == str((sdd_proj / FSM_REL).resolve())
        assert call["env"]["SDD_PROJECT"] == "alpha" or "SDD_PROJECT" not in call["env"]
        assert not [k for k in call["env"] if k.upper().startswith("BRIDGE_")]
    blob = (str(read_calls(sdd_fake)) + sdd_trace.read_text(encoding="utf-8")
            + plain_trace.read_text(encoding="utf-8"))
    for leaked in ("exported-by-a-developer", "somewhere-else", TOKEN):
        assert leaked not in blob, leaked


def test_no_error_response_or_header_ever_contains_the_configured_token(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body,
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_SDD_WRITE_TOKEN", TOKEN)
    seed_frozen(sdd_proj, "ESCALATION")
    client = sdd_live.client
    good, bad = {"X-Bridge-Token": TOKEN}, {"X-Bridge-Token": "definitely-not-the-token"}
    body = sdd_body(run_body, sdd_proj)
    nowhere = {**body["sdd"], "spec_dir": str(sdd_proj / "nowhere")}
    bad_path = sdd_body(run_body, sdd_proj, sdd=nowhere)
    freeze = {"root": str(sdd_proj), "docs": [TCS_REL], "approver": "op", "reason": "r"}
    responses = [
        client.post("/autoclaude/runs", json=body, headers=bad),                  # 403
        # 409（ESCALATION）
        client.post("/autoclaude/runs", json=body, headers=good),
        client.post("/autoclaude/runs", json=bad_path, headers=good),             # 422（路徑閘）
        client.post("/autoclaude/runs", content=b"{not json", headers=good),      # 422（本文壞）
        client.post("/sdd/fsm/alpha:freeze", json=freeze, headers=bad),           # 403
        client.post("/sdd/fsm/alpha:freeze", json=freeze, headers=good),          # 409（狀態不符）
        client.post("/sdd/fsm/alpha:freeze", json={"docs": []}, headers=good),    # 422
        client.post(f"/autoclaude/runs/{body['run_id']}:resume", headers=good),   # 404
        client.get("/sdd/fsm/alpha", params={"root": str(sdd_proj)}),
        client.get("/sdd/fsm/nope", params={"root": str(sdd_proj)}),              # 404
    ]
    codes = [r.status_code for r in responses]
    assert codes == [403, 409, 422, 422, 403, 409, 422, 404, 200, 404], codes
    for resp in responses:
        assert TOKEN not in resp.text and TOKEN not in str(resp.headers), resp.request.url
    audit_file = sdd_live.settings.engine_workspace / "_audit.jsonl"
    assert TOKEN.encode("utf-8") not in audit_file.read_bytes()


# ── F-9：同步與補償——缺口列（其餘列見 test_sdd_run.py／test_sdd_run_lifecycle.py） ──────────────
SYNC_CASES = [
    # 名稱, run 終態, 引擎升級訊息, stop_requested, shutting_down, orphan, 預期對 FSM 的動作
    ("completed", "COMPLETED", "", False, False, False, "done"),
    ("cancelled", "CANCELLED", "", True, False, False, "done"),
    ("cancelled-while-paused", "CANCELLED", "", False, False, False, "done"),
    ("engine-escalation", "FAILED", "retries exhausted", False, False, False, "failed"),
    ("quota-halt-crash-or-signal-kill", "FAILED", "", False, False, False, None),
    ("escalation-racing-a-cancel", "FAILED", "retries exhausted", True, False, False, None),
    ("bridge-shutdown", "FAILED", "", True, True, False, None),
    ("bridge-shutdown-with-escalation", "FAILED", "retries exhausted", True, True, False, None),
    ("orphan-failed", "FAILED", "", False, False, True, None),
    ("orphan-cancelled", "CANCELLED", "", False, False, True, None),
    ("paused", "PAUSED", "", False, False, False, None),
    ("still-running", "RUNNING", "", False, False, False, None),
    ("cancelling", "CANCELLING", "", True, False, False, None),
]


@pytest.mark.parametrize(("case", "status", "escalation", "stop", "shutdown", "orphan", "decision"),
                         SYNC_CASES, ids=[c[0] for c in SYNC_CASES])
def test_the_terminal_sync_matrix_calls_the_cli_exactly_as_the_adr_table_says(
        case: str, status: str, escalation: str, stop: bool, shutdown: bool, orphan: bool,
        decision: str | None, settings, sdd_fake: Path, sdd_proj: Path, tmp_path: Path) -> None:
    cfg = replace(settings, sdd_root=sdd_fake, sdd_write_token=TOKEN)
    _mgr, handle = build_handle(cfg, tmp_path, sdd=sdd_context(sdd_proj).record(), status=status)
    run_id = handle.rec.run_id
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED", autoclaude_delegated_tracking={
        "entered_at": "t", "resume_state": "IMPLEMENTATION", "playbook_ref": f"run:{run_id}"})
    handle._escalation, handle._escalation_step = escalation, "T02" if escalation else ""
    handle.stop_requested, handle.shutting_down = stop, shutdown
    handle._sdd_sync_terminal(orphan=orphan)
    assert handle.rec.status == status, "同步不改 run 自己的狀態"
    if decision is None:
        assert read_calls(sdd_fake) == [], "這一列對 FSM 零呼叫（留給下一個批次的回收點）"
        assert handle.rec.sdd["sync"] is None
        assert fsm_state(sdd_proj)["current_state"] == "AUTOCLAUDE_DELEGATED"
        return
    assert verbs(sdd_fake) == ["delegate-exit"]
    expected_reason = {
        "COMPLETED": f"console-run run={run_id} COMPLETED",
        "CANCELLED": f"console-run run={run_id} CANCELLED",
        "FAILED": f"console-run run={run_id} ENGINE-ESCALATION step=T02: retries exhausted"}[status]
    exit_argv = argv_of(sdd_fake, "delegate-exit")
    sent = (flag(exit_argv, "--decision"), flag(exit_argv, "--reason"))
    assert sent == (decision, expected_reason)
    assert (handle.rec.sdd["sync"]["exit"], handle.rec.sdd["sync"]["ok"]) == (decision, True)
    assert fsm_state(sdd_proj)["current_state"] == ("IMPLEMENTATION" if decision == "done"
                                                    else "ESCALATION")


EXIT_FAILURES = [
    # 名稱, 假 CLI 控制, 預期 alert, 同步結果是否 ok, 是否記 drift
    ("rc1-traceback", {"rc": {"delegate-exit": 1}}, "SDD_FSM_SYNC_FAILED", False, False),
    ("rc2-usage", {"rc": {"delegate-exit": 2}}, "SDD_FSM_SYNC_FAILED", False, False),
    ("rc3-already-moved-by-a-human", {"rc": {"delegate-exit": 3},
                                      "rc_extra": {"current_state": "IMPLEMENTATION"}},
     "SDD_SYNC_STATE_DRIFT", True, True),
    ("rc4-invalid-argument", {"rc": {"delegate-exit": 4}}, "SDD_FSM_SYNC_FAILED", False, False),
    ("rc5-state-file-gone", {"rc": {"delegate-exit": 5}}, "SDD_FSM_SYNC_FAILED", False, False),
    ("stdout-is-not-json", {"raw_stdout": {"delegate-exit": "not json"}}, "SDD_FSM_SYNC_FAILED",
     False, False),
]


@pytest.mark.parametrize(("case", "control", "alert", "ok", "drift"), EXIT_FAILURES,
                         ids=[c[0] for c in EXIT_FAILURES])
def test_a_failing_terminal_sync_only_raises_an_alert_and_never_changes_the_run(
        case: str, control: dict, alert: str, ok: bool, drift: bool, settings, sdd_fake: Path,
        sdd_proj: Path, tmp_path: Path) -> None:
    cfg = replace(settings, sdd_root=sdd_fake, sdd_write_token=TOKEN)
    _mgr, handle = build_handle(cfg, tmp_path, sdd=sdd_context(sdd_proj).record(),
                                status="COMPLETED")
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED", autoclaude_delegated_tracking={
        "entered_at": "t", "resume_state": "IMPLEMENTATION",
        "playbook_ref": f"run:{handle.rec.run_id}"})
    set_control(sdd_fake, **control)
    handle._sdd_sync_terminal()                                      # 不得丟例外
    assert handle.rec.status == "COMPLETED" and handle.rec.exit_code is None
    sync = handle.rec.sdd["sync"]
    assert sync["ok"] is ok and bool(sync.get("drift")) is drift, sync
    assert alert_codes(handle) == [alert]
    assert verbs(sdd_fake) == ["delegate-exit"], "不重試"


def test_a_timed_out_terminal_sync_is_an_alert_not_a_hang(
        settings, sdd_fake: Path, sdd_proj: Path, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sdd_cli, "DEFAULT_TIMEOUT_SECONDS", 1.0)
    cfg = replace(settings, sdd_root=sdd_fake, sdd_write_token=TOKEN)
    _mgr, handle = build_handle(cfg, tmp_path, sdd=sdd_context(sdd_proj).record(),
                                status="COMPLETED")
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED", autoclaude_delegated_tracking={
        "entered_at": "t", "resume_state": "IMPLEMENTATION",
        "playbook_ref": f"run:{handle.rec.run_id}"})
    set_control(sdd_fake, sleep={"delegate-exit": 30})
    handle._sdd_sync_terminal()
    assert alert_codes(handle) == ["SDD_FSM_SYNC_FAILED"]
    sync = handle.rec.sdd["sync"]
    assert (sync["ok"], sync["error"]) == (False, "sdd_cli_timeout")
    assert handle.rec.status == "COMPLETED"


# ── F-10：回收兩步之間 `delegate-enter` 失敗（其餘列見 test_sdd_run.py／
# test_sdd_run_lifecycle.py）────
def test_a_failing_enter_between_the_two_reclaim_steps_leaves_the_fsm_in_implementation(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    ghost = "00000000-0000-4000-8000-0000000000bb"
    seed_frozen(sdd_proj, "AUTOCLAUDE_DELEGATED", autoclaude_delegated_tracking={
        "entered_at": "t", "resume_state": "IMPLEMENTATION", "playbook_ref": f"run:{ghost}"})
    set_control(sdd_fake, rc={"delegate-enter": 1})
    body = sdd_body(run_body, sdd_proj, delay="0.1")
    resp = post(sdd_live, body)
    assert (resp.status_code, resp.json()["reason"]) == (502, "sdd_cli_failed")
    assert verbs(sdd_fake) == ["delegate-exit", "delegate-enter"], \
        "第一步（回收）做完、第二步（進入）失敗"
    assert fsm_state(sdd_proj)["current_state"] == "IMPLEMENTATION", \
        "停在「沒有進行中委派」，不需人工"
    assert not workspace_has(sdd_live, body["run_id"]), "不 spawn、不留 run 目錄"
    set_control(sdd_fake)
    assert post(sdd_live, body).status_code == 201, "重試從常態進入，不再走回收"
    sdd_live.wait_status(body["run_id"], TERMINAL)
    wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert verbs(sdd_fake)[2:] == ["delegate-enter", "delegate-exit"]
    audited = [e for e in audit_entries(sdd_live) if e.get("verb") == "reclaim"]
    assert [e["old_status"] for e in audited] == ["missing"], \
        "回收那一步有留稽核（失敗的第一次也算）"


# ── F-11：AT 文法與歸屬（D-115-16；ADR §8.1／§8.2／§8.5）────────────────────────────────────────
ACCEPTED_ATS = {"AT-001-1-1": "AC-001-1", "AT-001-1": "AC-001-1", "AT-001-12-3-a": "AC-001-12",
                "AT-001-1-E1": "AC-001-1", "AT-001-1-E-1": "AC-001-1", "AT-029-1-1-1-1": "AC-029-1"}
REJECTED_ATS = ["AT-14-1-1", "AT-123", "AT-001", "AT-001-E-1", "AT-0001-1-1", "AT-001-1-",
                "AT-001--1", "at-001-1-1", "AT-001-1-1_a", "AT-001-1-1 x", "AT-{NNN}-1-1"]


def test_the_seventeen_adr_samples_are_judged_by_one_shared_pattern() -> None:
    from autoclaude.core.ports.spec_source import AT_ID_PATTERN, ac_id_of_at
    from autoclaude.infra.adapters import playbook_to_rtm_adapter as reverse
    from autoclaude.infra.adapters import sdd_to_playbook_adapter as forward

    assert len(ACCEPTED_ATS) + len(REJECTED_ATS) == 17
    for at_id, ac_id in ACCEPTED_ATS.items():
        assert re.fullmatch(AT_ID_PATTERN, at_id), at_id
        assert ac_id_of_at(at_id) == ac_id, "前兩段數字＝所屬 AC，多段尾綴不影響歸屬"
    for at_id in REJECTED_ATS:
        assert not re.fullmatch(AT_ID_PATTERN, at_id), at_id
        assert ac_id_of_at(at_id) is None
    assert forward.AT_ID_PATTERN == reverse.AT_ID_PATTERN == AT_ID_PATTERN, \
        "正向與逆向由同一個常數組 regex，不得各寫一份"
    assert forward.ac_id_of_at is reverse.ac_id_of_at is ac_id_of_at


UNMAPPED_PROBE = """# Test Contract Specification — Probe

**spec-format-version**: 1.0
**scenario**: greenfield

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 正常 | AT-001-1-1 | 正常 | ✅ | Unit | □ |
| AC-003-1 | 舊編號 | AT-14-1-1 | 舊編號不合文法 | ✅ | Unit | □ |
| AC-004-1 | 列的 AC 與 AT 前兩段不一致 | AT-005-1-1 | 不一致 | ✅ | Unit | □ |
| AC-{NNN}-1 | 模板佔位 | AT-{NNN}-1-1 | 佔位 | ✅ | Unit | □ |

## 2. AT 格式

```gherkin
# AT-001-1-1
Scenario: 正常
  Then 輸出 "[AT_OK_1]"
```

```gherkin
# AT-001-9-9
Scenario: 有標頭、沒有映射列
  Then 輸出 "[AT_OK_9]"
```

## 3. AT 清單

| AT ID | 說明 |
|-------|------|
| AT-777-1-1 | 清單表的第一欄是 AT，不是宣告位置 |

## 4. 邊界

| 場景類型 | 編號 | 說明 |
|---------|------|------|
| 邊界 | AT-888-E-1 | 第一欄不是 AC，不是宣告位置 |

內文提到 AT-555-5-5 也不是宣告位置。
"""


def test_only_declaration_sites_are_scanned_for_unmapped_ats(bridge, tmp_path: Path) -> None:
    root = project(tmp_path, text=UNMAPPED_PROBE)
    resp = compile_http(bridge, root, fsm_project="alpha")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [t["name"] for t in body["tasks"]] == ["AT-001-1-1"], "只有合文法且列的 AC 一致者被編成"
    assert body["unmapped_at_ids"] == ["AT-14-1-1", "AT-005-1-1", "AT-001-9-9"], \
        "依首見順序；§3／§4 的表格、散文與 AT-{NNN} 模板佔位都不出聲"


def test_the_reverse_report_keeps_unmapped_ats_in_the_totals_and_never_fully_covers() -> None:
    from autoclaude.infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter

    def task(step_suffix: str, name: str) -> SimpleNamespace:
        return SimpleNamespace(step_id=f"sdd-greenfield-at-{step_suffix}", name=name,
                               weak_regex=False)

    adapter = PlaybookToRtmAdapter()
    tasks = [task("001-12-3-a", "AT-001-12-3-a"), task("001-12-3-b", "AT-001-12-3-b"),
             task("14-1-1", "AT-14-1-1")]
    done = ["sdd-greenfield-at-001-12-3-a", "sdd-greenfield-at-001-12-3-b"]
    report = adapter.compile_report(tasks, done, spec_digest="sha256:" + "a" * 64)
    assert report.total_at == 3 and report.passed_at == 2, "無法歸屬的 AT 仍計入 AT 級分母"
    assert report.failed_at_ids == ("AT-14-1-1",) and report.unmapped_at_ids == ("AT-14-1-1",)
    assert report.ac_coverage == (("AC-001-12", 2, 2),), \
        "多段尾綴歸 AC-001-12；不合文法者不進任何 AC 桶"
    assert report.is_fully_covered is False, "有無法歸屬的 AT 時不得宣稱全覆蓋"
    doc = yaml.safe_load(adapter.render_yaml(report))
    assert doc["summary"]["unmapped_at"] == 1 and doc["unmapped_at_ids"] == ["AT-14-1-1"]
    clean = adapter.compile_report(tasks[:2], done)
    assert clean.is_fully_covered is True and clean.unmapped_at_ids == ()
    legacy_doc = yaml.safe_load(adapter.render_yaml(clean))
    assert legacy_doc["summary"]["unmapped_at"] == 0 and legacy_doc["unmapped_at_ids"] == []


# ══ 真的 SDD CLI（子行程）══════════════════════════════════════════════════════════════════════
# W2 整合步驟：Dev-SDD-RT 的 CLI 已由主控親驗並 commit（HEAD 302aefd9），這組測試預設就跑。
# 狀態目錄在暫存目錄（`<專案根>/build/reports/fsm`），不碰 repo 真實的 build/reports；測試行程自己
# 不 import AISDLC_SDD——造狀態檔也是子行程呼叫（與 SDD 自己的 test_cli_bridge_verbs.py 同一手
# 法）。唯一的略過條件是「真 CLI 在這個環境 import 不了」（缺相依套件）：略過會印出原因，不是靜默
# 放行。
_MAKE_STATE = """
import sys
from pathlib import Path
from tools.fsm_runtime import state_loader as sl
state_dir, project, current = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
path = state_dir / ("FSM-STATE-%s.yaml" % sl._sanitize_component(project))
state = sl.load_state(project, path=path)
state.current = current
sl.save_state(state)
print(path)
"""


def _real_cli_env(sdd_root: Path, state_dir: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("BRIDGE_", "SDD_")) and k.upper() != "PYTHONPATH"}
    env.update({"SDD_STATE_DIR": str(state_dir), "PYTHONPATH": str(sdd_root), "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def run_real_python(
        sdd_root: Path, state_dir: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *argv], cwd=str(sdd_root), env=_real_cli_env(sdd_root, state_dir),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        stdin=subprocess.DEVNULL, check=False)


def make_real_state(sdd_root: Path, state_dir: Path, project: str, current: str) -> Path:
    """用真的 `load_state`／`save_state` 在暫存目錄造一個處於 `current` 的狀態檔（扮演「人在 SDD
    session把專案推到某個狀態」）。"""
    done = run_real_python(sdd_root, state_dir, "-c", _MAKE_STATE, str(state_dir), project, current)
    assert done.returncode == 0, done.stderr
    return Path(done.stdout.strip().splitlines()[-1])


_REAL_CLI_PROBE: list[str | None] = []                  # 快取：None＝可用；字串＝不可用的原因


def real_cli_problem(sdd_root: Path) -> str | None:
    """真 CLI 能否在這個環境啟動（import 得了）。樹不存在是環境錯誤、直接讓測試失敗；只有 import
    失敗（缺相依套件）才回原因讓 fixture 略過。整個 session 只探測一次。"""
    if not _REAL_CLI_PROBE:
        assert (sdd_root / "tools" / "fsm_runtime" / "fsm_runtime.py").is_file(), sdd_root
        with tempfile.TemporaryDirectory() as scratch:
            done = run_real_python(sdd_root, Path(scratch), "-W", "ignore::RuntimeWarning", "-c",
                                   "import tools.fsm_runtime.fsm_runtime")
        last = (done.stderr.strip().splitlines() or ["（無 stderr）"])[-1]
        _REAL_CLI_PROBE.append(None if done.returncode == 0 else f"rc={done.returncode}：{last}")
    return _REAL_CLI_PROBE[0]


@pytest.fixture
def real_live(make_bridge, settings):
    """寫入面啟用、指向**真的** SDD 樹的 Bridge（`settings.sdd_root` ＝ 現行 LATEST 版本目錄）。"""
    assert settings.sdd_root is not None, "找不到真的 AISDLC_SDD 樹"
    problem = real_cli_problem(settings.sdd_root)
    if problem is not None:
        pytest.skip(f"真 SDD CLI 在此環境啟動不了（缺相依套件？）：{problem}")
    return make_bridge(replace(settings, sdd_write_token=TOKEN))


def real_freeze(live, root: Path, project: str = "alpha", **over: Any):
    body = {"root": str(root), "docs": [TCS_REL], "approver": "operator",
            "reason": "W2 真 CLI 核准", **over}
    return live.client.post(f"/sdd/fsm/{project}:freeze", json=body,
                            headers={"X-Bridge-Token": TOKEN})


def test_the_real_cli_carries_a_project_from_freeze_through_a_batch_and_back(
        real_live, sdd_proj: Path, run_body) -> None:
    """F-3 的 E2E 面：真 CLI 凍結（含 spec_doc_digests）→ 編譯 → 第一個批次（談判＋委派）→ 終態交
    還；再改檔：編譯與預檢皆 409 frozen_vs_file，還原後恢復。reason 六種固定組字逐字落進真的
    decision_trace。"""
    make_real_state(real_live.settings.sdd_root, sdd_proj / FSM_REL, "alpha", "HUMAN_PENDING")
    digest = digest_of(TCS_TEXT)
    frozen = real_freeze(real_live, sdd_proj, expected_digests={TCS_REL: digest})
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["current_state"] == "SPEC_FROZEN"
    assert frozen.json()["spec_doc_digests"] == {TCS_REL: digest}
    stage = fsm_state(sdd_proj)["frozen_stages"][-1]
    assert (stage["approved_by"], stage["spec_doc_digests"]) == ("operator", {TCS_REL: digest})
    compiled = compile_http(real_live, sdd_proj, fsm_project="alpha")
    assert (compiled.status_code, compiled.json()["frozen_digest"]) == (200, "verified")

    created = post(real_live, sdd_body(run_body, sdd_proj, delay="0.2"))
    assert created.status_code == 201, created.text
    rid = created.json()["run_id"]
    assert real_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    final = wait_fsm(sdd_proj, "IMPLEMENTATION")
    assert [(t["to"], t["reason"]) for t in final["decision_trace"]] == [
        ("SPEC_FROZEN", "console-freeze approver=operator; reason=W2 真 CLI 核准"),
        ("TEST_CONTRACT_NEGOTIATED", f"console-signoff approver=operator; run={rid}"),
        ("IMPLEMENTATION", f"console-signoff approver=operator; oracle={TCS_REL}@{digest}; "
                           "basis=import-draft-signoff; r9.20.3=not-satisfied"),
        ("AUTOCLAUDE_DELEGATED", f"console-run run={rid} START"),
        ("IMPLEMENTATION", f"console-run run={rid} COMPLETED")]
    assert final["autoclaude_delegated_tracking"]["playbook_ref"] == f"run:{rid}"

    spec = contracts_dir(sdd_proj) / TCS_NAME
    spec.write_text(TCS_TEXT + "\n<!-- 凍結後被改 -->\n", encoding="utf-8", newline="")
    edited = compile_http(real_live, sdd_proj, fsm_project="alpha")
    assert (edited.status_code, edited.json()["pair"]) == (409, "frozen_vs_file")
    refused = post(real_live, sdd_body(run_body, sdd_proj, delay="0.2"))
    assert (refused.status_code, refused.json()["reason"], refused.json()["pair"]) == (
        409, "spec_digest_changed", "frozen_vs_file")
    spec.write_text(TCS_TEXT, encoding="utf-8", newline="")
    assert compile_http(real_live, sdd_proj, fsm_project="alpha").status_code == 200


def test_the_real_cli_answers_every_whitelisted_verb_the_way_the_bridge_parses_it(
        real_live, sdd_proj: Path) -> None:
    """F-12 的對拍面：Bridge 實際送的五個動詞（含 noop 與各種 rc）對真 CLI 的回應都解得出來、對映
    正確。"""
    from app.errors import ApiError

    sdd_root, state_dir = real_live.settings.sdd_root, sdd_proj / FSM_REL
    make_real_state(sdd_root, state_dir, "alpha", "SPEC_FROZEN")

    def call(verb: str, args: list[str], project: str = "alpha") -> dict[str, Any]:
        return sdd_cli.run_verb(verb, args, sdd_root=sdd_root, state_dir=state_dir, project=project)

    entered = call("negotiate-enter", sdd_cli.negotiate_enter_args(reason="談判開始"))
    assert entered["ok"] is True and entered["current_state"] == "TEST_CONTRACT_NEGOTIATED"
    agreed = call("negotiate-exit", sdd_cli.negotiate_exit_args(reason="雙方同意"))
    assert agreed["ok"] is True and agreed["current_state"] == "IMPLEMENTATION"
    delegated = call("delegate-enter",
                     sdd_cli.delegate_enter_args(reason="開跑", playbook_ref="run:r1"))
    assert delegated["current_state"] == "AUTOCLAUDE_DELEGATED" and not delegated.get("noop")
    again = call("delegate-enter", sdd_cli.delegate_enter_args(reason="重複進入"))
    assert again["ok"] is True and again.get("noop") is True, "已在委派中再進入＝noop，不是錯誤"
    left = call("delegate-exit", sdd_cli.delegate_exit_args(decision="done", reason="交還"))
    assert left["current_state"] == "IMPLEMENTATION"
    with pytest.raises(ApiError) as conflict:                    # rc 3：前置狀態不符
        call("delegate-exit", sdd_cli.delegate_exit_args(decision="done", reason="再交還一次"))
    assert (conflict.value.status_code, conflict.value.body["reason"],
            conflict.value.body["current_state"]) == (409, "fsm_state_conflict", "IMPLEMENTATION")
    with pytest.raises(ApiError) as missing:                     # rc 5：狀態檔不存在
        call("delegate-enter", sdd_cli.delegate_enter_args(reason="x"), project="no-such-project")
    assert (missing.value.status_code, missing.value.body["reason"]) == (404, "fsm_not_found")
    assert not (state_dir / "FSM-STATE-no-such-project.yaml").exists(), "--must-exist：不建檔"
    call("delegate-enter", sdd_cli.delegate_enter_args(reason="再開一次"))
    failed = call("delegate-exit", sdd_cli.delegate_exit_args(decision="failed", reason="引擎升級"))
    assert failed["current_state"] == "ESCALATION"
    state = fsm_state(sdd_proj)
    assert state["escalation_provenance"]["source"] == "autoclaude_delegated_failed"
    assert state["escalation_history"][-1]["trigger_reason"] == "引擎升級"


def test_the_recovery_hint_shown_for_an_escalation_is_accepted_by_the_real_cli(
        real_live, sdd_proj: Path, run_body) -> None:
    sdd_root, state_dir = real_live.settings.sdd_root, sdd_proj / FSM_REL
    make_real_state(sdd_root, state_dir, "alpha", "HUMAN_PENDING")
    assert real_freeze(real_live, sdd_proj).status_code == 200      # 真實專案一定凍結過
    rid = post(real_live, sdd_body(run_body, sdd_proj, fail_step=2, delay="0.2")).json()["run_id"]
    assert real_live.wait_status(rid, TERMINAL)["status"] == "FAILED"
    wait_fsm(sdd_proj, "ESCALATION")
    view = real_live.client.get("/sdd/fsm/alpha", params={"root": str(sdd_proj)}).json()
    assert view["escalation_provenance"]["source"] == "autoclaude_delegated_failed"
    target = view["recovery"]["target"]
    blocked = post(real_live, sdd_body(run_body, sdd_proj))
    assert (blocked.status_code, blocked.json()["reason"]) == (409, "fsm_state_conflict")
    resumed = run_real_python(
        sdd_root, state_dir, "-W", "ignore::RuntimeWarning", "-m",
        "tools.fsm_runtime.fsm_runtime", "resume-from-escalation", "--project", "alpha",
        "--to", target, "--reason", "人工確認後恢復")
    assert resumed.returncode == 0, (resumed.stdout, resumed.stderr)
    assert fsm_state(sdd_proj)["current_state"] == target, "Console 顯示的恢復目標，真 CLI 接受"
    again = post(real_live, sdd_body(run_body, sdd_proj, delay="0.1"))
    assert again.status_code == 201, "人工恢復後，下一個批次可直接啟動"
    assert real_live.wait_status(again.json()["run_id"], TERMINAL)["status"] == "COMPLETED"


@pytest.mark.parametrize("variant", list(DIGEST_VARIANTS))
def test_the_real_cli_writes_the_same_digest_as_the_adapter_and_the_bridge(
        variant: str, real_live, tmp_path: Path) -> None:
    """F-6 的完整面：CLI 凍結寫入的摘要＝adapter 的 SddSpec.digest＝Bridge 重算的現檔摘要，五種檔
    全部相等。"""
    raw, bom = DIGEST_VARIANTS[variant]
    root = make_project(tmp_path / "projects", "v", TCS_TEXT)
    path = contracts_dir(root) / TCS_NAME
    path.write_bytes(raw)
    make_real_state(real_live.settings.sdd_root, root / FSM_REL, "alpha", "HUMAN_PENDING")
    expected = expected_digest(bom)
    frozen = real_freeze(real_live, root)
    assert frozen.status_code == 200, frozen.text
    written = fsm_state(root)["frozen_stages"][-1]["spec_doc_digests"][TCS_REL]
    compiled = compile_http(real_live, root, fsm_project="alpha")
    assert compiled.status_code == 200 and compiled.json()["frozen_digest"] == "verified"
    assert written == compiled.json()["digest"] == spec_digest.file_digest(path) == expected
    if b"\r" in raw:
        assert "sha256:" + hashlib.sha256(raw).hexdigest() != expected


@pytest.mark.parametrize(("label", "code"), [("not-utf8", "doc_not_utf8"),
                                             ("too-large", "doc_too_large")])
def test_the_real_cli_refuses_a_non_utf8_or_oversized_document_with_rc4(
        label: str, code: str, real_live, tmp_path: Path) -> None:
    """酬載在測試內才產生（不當參數值：pytest 會把 16 MiB 的 bytes 逐字塞進測試 id 與日誌）。"""
    payload = {"not-utf8": b"\xff\xfe\x00 not utf-8 \x80",
               "too-large": b"a" * (16 * 1024 * 1024 + 1)}[label]
    root = make_project(tmp_path / "projects", "bad")
    (root / "docs" / "extra.md").write_bytes(payload)
    make_real_state(real_live.settings.sdd_root, root / FSM_REL, "alpha", "HUMAN_PENDING")
    before = (root / FSM_REL / "FSM-STATE-alpha.yaml").read_bytes()
    resp = real_freeze(real_live, root, docs=[TCS_REL, "docs/extra.md"])
    assert resp.status_code == 422, f"{label}：{resp.text}"
    assert (resp.json()["reason"], resp.json()["error"]) == ("sdd_invalid_argument", code)
    assert (root / FSM_REL / "FSM-STATE-alpha.yaml").read_bytes() == before, "被拒不得動狀態檔"


def test_the_real_cli_state_files_are_selected_by_project_key_only(
        real_live, tmp_path: Path) -> None:
    """F-2 的真檔面：狀態檔由真的 `load_state`／`save_state` 造出（m-alpha 尚未凍結、m-zeta 經
    Bridge 的
    `:freeze` 由真 CLI 凍結）；只認指定者，未指認即拒，原名反查找得到、也不往上層目錄找。"""
    sdd_root = real_live.settings.sdd_root
    root = project(tmp_path, text=RICH_TCS, name="multi", state=None)
    state_dir = root / FSM_REL
    make_real_state(sdd_root, state_dir, "m-alpha", "INIT")
    make_real_state(sdd_root, state_dir, "m-zeta", "HUMAN_PENDING")
    assert real_freeze(real_live, root, "m-zeta").status_code == 200
    refused = compile_http(real_live, root, fsm_project="m-alpha")
    assert (refused.status_code, refused.json()["reason"]) == (422, "spec_not_frozen"), \
        "m-zeta 已凍結不得讓 m-alpha 放行"
    accepted = compile_http(real_live, root, fsm_project="m-zeta")
    assert accepted.status_code == 200, accepted.text
    found = accepted.json()
    assert (found["fsm_project"], found["frozen_digest"]) == ("m-zeta", "verified")
    ambiguous = compile_http(real_live, root)
    assert ambiguous.status_code == 422 and "不唯一" in ambiguous.json()["detail"]
    nope = compile_http(real_live, root, fsm_project="nope")
    assert nope.status_code == 422 and "m-alpha" in nope.json()["detail"]

    # 原名反查：SDD 側 `a:b` 的檔名是 `a_b`、檔內 project 欄是原名；Bridge 先淨化成鍵，adapter 直
    # 呼也找得到
    other = project(tmp_path, text=RICH_TCS, name="named", state=None)
    path = make_real_state(sdd_root, other / FSM_REL, "a:b", "IMPLEMENTATION")
    assert path.name == "FSM-STATE-a_b.yaml" and fsm_state(other, "a_b")["project"] == "a:b"
    for original in ("a:b", "a_b"):
        found = compile_http(real_live, other, fsm_project=original)
        assert found.status_code == 200, (original, found.text)
        assert found.json()["fsm_project"] == "a_b"
    from app import sdd_adapter

    spec = sdd_adapter.load_spec(sdd_adapter.build_adapter("a:b"), contracts_dir(other), None)
    assert spec.fsm_project == "a_b", "adapter 以檔內 project 欄位反查原名（鍵不是現成檔名時）"

    # 不往上層目錄找：子專案自己有狀態檔（別的專案），父目錄有 x 的已凍結狀態
    parent = project(tmp_path, text=RICH_TCS, name="outer", state=None)
    make_real_state(sdd_root, parent / FSM_REL, "x", "HUMAN_PENDING")
    assert real_freeze(real_live, parent, "x").status_code == 200
    child = make_project(parent, "sub", RICH_TCS)
    make_real_state(sdd_root, child / FSM_REL, "y", "INIT")
    climbing = compile_http(real_live, child, fsm_project="x")
    assert (climbing.status_code, climbing.json()["reason"]) == (422, "spec_not_frozen")
