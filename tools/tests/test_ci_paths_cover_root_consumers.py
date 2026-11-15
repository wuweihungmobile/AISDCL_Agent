"""根層 `tools/` 模組被 AgentConsole engine-bridge 假 repo 消費時的「閉包三落點」結構鎖。

成因（6a229fe4）：`tools/lib/quota_policy.py` 頂層新 import `quota_pace_floor`，而 engine-bridge 的
測試夾具只把**手寫清單**內的根層檔複製進假 repo，清單漏了新檔 ⇒ agentconsole-ci 才紅；根層全套
與 pre-push 都不含這個跨子專案消費端，推送前攔不到。

本檔從入口 `tools/selfimproving.py` 加 `tools/lib/selfimproving/` 整個目錄出發，用 `ast` 算靜態
import 閉包（頂層與函式內 import 都算——寫入動詞等延後載入的路徑一樣會在真 CLI 載入），
只跟 repo 內 `tools/` 與 `tools/lib/` 的模組，再對照同一份閉包的三個落點：

1. `AgentConsole/engine-bridge/tests/si_repo_support.py` 的 `WRITE_CLOSURE`（夾具複製清單）
2. `AgentConsole/engine-bridge/tests/test_si_deploy_config.py` 的 `FULL_PATHS`（期望清單）
3. `.github/workflows/agentconsole-ci.yml` 的 `push`／`pull_request` 兩段 `paths`

新增被閉包內模組 import 的 `tools/lib` 模組時，三處要在同一個 commit 補齊（見
`docs/02_architecture/Root_Layout_and_Module_Placement.md` 新模組檢查表）。
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
LIB = TOOLS / "lib"
SUPPORT = ROOT / "AgentConsole/engine-bridge/tests/si_repo_support.py"
DEPLOY_TEST = ROOT / "AgentConsole/engine-bridge/tests/test_si_deploy_config.py"
WORKFLOW = ROOT / ".github/workflows/agentconsole-ci.yml"
ENTRY = TOOLS / "selfimproving.py"
PKG_DIR = LIB / "selfimproving"
PKG_REL = "tools/lib/selfimproving/"


def _resolve(name: str) -> Path | None:
    """裸模組名 → repo 內檔（`tools/lib/<n>.py` 優先，其次 `tools/<n>.py`）；找不到＝外部。"""
    for cand in (LIB / f"{name}.py", TOOLS / f"{name}.py"):
        if cand.is_file():
            return cand
    return None


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    left = node.test.left
    return isinstance(left, ast.Name) and left.id == "__name__"


def _module_level_imports(tree: ast.Module) -> list[ast.stmt]:
    """模組層的 import 敘述（含 try／if 內，不含 def／class 內）。函式內的延後 import 只在該路徑
    被呼叫時才載入，不屬「CLI 一啟動就需要」的閉包（寫入動詞那一路另見 WRITE_ONLY_FILES）。"""
    out: list[ast.stmt] = []
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            out.append(node)
        elif isinstance(node, ast.Try) and node.handlers:
            # `try: import x / except …: x = None` 是 fail-open 的選配依賴，缺檔不會讓 CLI 跑不起來
            stack.extend(node.orelse + node.finalbody)
            for handler in node.handlers:
                stack.extend(handler.body)
        elif _is_main_guard(node):
            continue                                 # `if __name__ == "__main__":` 只在直接執行時跑
        elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))
    return out


def _imported(path: Path) -> tuple[set[str], set[Path]]:
    """(根層裸模組名, 套件內檔)——前者交 `_resolve`，後者是 `lib.selfimproving.X` 的 X 檔。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    pkg_files: set[Path] = set()
    for node in _module_level_imports(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
            continue
        if node.level:                               # 相對 import：只出現在套件內
            base = (node.module or "").split(".")[0]
            for cand in ([base] if base else [a.name for a in node.names]):
                if (path.parent / f"{cand}.py").is_file():
                    pkg_files.add(path.parent / f"{cand}.py")
            continue
        top = (node.module or "").split(".")
        if top[0] != "lib":
            names.add(top[0])
        elif len(top) == 1:                          # from lib import x
            names.update(a.name for a in node.names)
        elif top[1] != "selfimproving":              # from lib.y import …
            names.add(top[1])
        else:                                        # from lib.selfimproving[.x] import …
            cands = [top[2]] if len(top) > 2 else [a.name for a in node.names]
            pkg_files.update(PKG_DIR / f"{c}.py" for c in cands if (PKG_DIR / f"{c}.py").is_file())
    return names, pkg_files


def root_import_closure() -> set[str]:
    """入口出發、只跟模組層 import 的 repo 內 `tools/` 檔案閉包（回傳相對 repo 根的正斜線路徑；
    套件目錄整包被複製，以 `tools/lib/selfimproving/` 一項代表，套件內檔只當走訪節點）。"""
    out: set[str] = {ENTRY.relative_to(ROOT).as_posix(), PKG_REL}
    todo = [ENTRY]
    seen: set[Path] = set()
    while todo:
        cur = todo.pop()
        if cur in seen:
            continue
        seen.add(cur)
        names, pkg_files = _imported(cur)
        todo.extend(p for p in pkg_files if p not in seen)
        for name in names:
            hit = _resolve(name)
            if hit is not None and hit not in seen:
                out.add(hit.relative_to(ROOT).as_posix())
                todo.append(hit)
    return out


def _literal_strings(path: Path, var: str) -> list[str]:
    """取模組層 `var = (...)`／`[...]` 內的字串字面（保序）；`*other` 展開的名稱遞迴取同檔常數。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        targets = [node.target] if isinstance(node, ast.AnnAssign) else (
            node.targets if isinstance(node, ast.Assign) else [])
        if any(isinstance(t, ast.Name) and t.id == var for t in targets) and node.value is not None:
            return _flatten(path, node.value)
    raise AssertionError(f"{path.name} 找不到常數 {var}")


def _flatten(path: Path, value: ast.AST) -> list[str]:
    out: list[str] = []
    for el in getattr(value, "elts", []):
        if isinstance(el, ast.Starred) and isinstance(el.value, ast.Name):
            out += _literal_strings(path, el.value.id)
        elif isinstance(el, ast.Constant) and isinstance(el.value, str):
            out.append(el.value)
    return out


def _glob_regex(glob: str) -> re.Pattern[str]:
    out: list[str] = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out))


def _covered_by_globs(item: str, globs: list[str]) -> bool:
    probes = [item + "x.py", item + "sub/deep/x.py"] if item.endswith("/") else [item]
    pos = [g for g in globs if not g.startswith("!")]
    return any(all(_glob_regex(g).fullmatch(p) for p in probes) for g in pos)


def _covered_by_list(item: str, entries: list[str]) -> bool:
    """夾具／期望清單：精確相等，或被以 `/`（或 `/**`）結尾的目錄項涵蓋。"""
    for e in entries:
        base = e[:-2] if e.endswith("/**") else e
        if item == e or item == base or (base.endswith("/") and item.startswith(base)) \
                or (e.endswith("/**") and item.startswith(base + "/")):
            return True
    return False


def missing_in_three_places(closure: set[str]) -> list[str]:
    fixture = _literal_strings(SUPPORT, "WRITE_CLOSURE")
    expected = _literal_strings(DEPLOY_TEST, "FULL_PATHS")
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = wf.get("on", wf.get(True)) or {}
    problems: list[str] = []
    for item in sorted(closure):
        if not _covered_by_list(item, fixture):
            problems.append(f"{item}：缺在 si_repo_support.py 的 CLI_CLOSURE")
        if not _covered_by_list(item, expected):
            problems.append(f"{item}：缺在 test_si_deploy_config.py 的 FULL_PATHS")
        for trig in ("push", "pull_request"):
            if not _covered_by_globs(item, (triggers.get(trig) or {}).get("paths") or []):
                problems.append(f"{item}：缺在 agentconsole-ci.yml 的 on.{trig}.paths")
    return problems


class TestBridgeClosureThreePlacesCoverRootImports(unittest.TestCase):
    def test_the_closure_walk_finds_the_known_chain(self) -> None:
        """自證：算出的閉包必含已知的 quota 鏈（算法壞掉時此處先紅，而不是下一個測試假綠）。"""
        closure = root_import_closure()
        for must in ("tools/lib/quota_policy.py", "tools/lib/quota_pace_floor.py",
                     "tools/lib/transcript_activity.py", "tools/lib/quota_pace.py"):
            self.assertIn(must, closure)

    def test_every_closure_module_is_in_fixture_expected_list_and_ci_paths(self) -> None:
        problems = missing_in_three_places(root_import_closure())
        self.assertEqual(
            problems, [],
            "根層 import 閉包新增了檔，卻沒同一個 commit 補齊三處：(1) AgentConsole/engine-bridge/"
            "tests/si_repo_support.py 的 CLI_CLOSURE；(2) 同目錄 test_si_deploy_config.py 的 "
            "FULL_PATHS；(3) .github/workflows/agentconsole-ci.yml 的 push／pull_request paths。"
            "\n" + "\n".join(problems))

    def test_the_checker_flags_a_dropped_entry(self) -> None:
        """負控：從 fixture 清單拿掉一項，檢查器必須點名（防止檢查器自己變成恆綠）。"""
        closure = root_import_closure() | {"tools/lib/zz_not_listed.py"}
        problems = missing_in_three_places(closure)
        self.assertEqual(len(problems), 4, problems)
        self.assertTrue(all(p.startswith("tools/lib/zz_not_listed.py") for p in problems))


if __name__ == "__main__":
    unittest.main()
