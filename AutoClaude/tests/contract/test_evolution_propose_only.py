"""FR-SI-28／AC-SI-28-1～3（SelfImproving P1 鍵 B）：「演化只提案不套用」的可重跑檢查。

TCS：`docs/03_testing/contracts/TCS-SelfImproving-P1-20261020.md` 的 R66、D13（AC-128-1～128-3）。
引擎碼零改動（ADR-SI-07）；本檔只唯讀 `AutoClaude/autoclaude/` 與 `AutoClaude/CLAUDE.md`。

立案事實（OBS-SI-010）
  `AutoClaude/CLAUDE.md` 宣稱演化「只提案、不套用」，但引擎裡 `apply_evolution` 仍有四個
  呼叫點、`require_evolution_signoff` 預設 False（演化版自動重載放行）。這句宣稱今天成立，
  **只因為**舊 `PlaybookRunner` 沒有生產建構點、`plugins/` 與 `core/` 沒有演化重載的生產者
  ——那是「沒人建構」，不是「被拔除」或「被擋下」。重載分支（`core/services/auto_resume.py`）
  本身沒有 signoff 閘，把 `require_evolution_signoff` 改成 True 對 Kernel 正式路徑無效（它
  只被舊 runner 讀）。所以要守的不是旗標，而是「沒有建構點、沒有生產者」這兩個事實：它們
  一旦消失，必須當場被看見。

五格（每格自帶對照組：證明掃描器在已知有生產站點的地方真的看得見，而不是壞掉才零命中）
  ① 引用格：既有 r85 檔仍含兩個鎖（`PlaybookRunner` 零生產建構點＋掃描器自證）。本檔引用、不重寫。
  ② `apply_evolution` 呼叫點恰為受檢清單 `APPLY_EVOLUTION_SITES`（以檔＋外層函式登記、不寫行號）；
     `execution/` 之外沒有模組 import 含 `steps_orchestrator`／`mutation_applier` 的路徑。
  ③ 演化重載生產者：`plugins/` 與 `core/` 內沒有帶 `evolved_playbook_path=` 的呼叫，也沒有
     `PersistenceResult(kind="evolved_playbook")`（定義與彙整檔 `PRODUCER_EXCLUDED` 除外）。
  ④ `require_evolution_signoff` 的讀取（Load 語境）只出現在 `execution/playbook_runner.py`。
  ⑤ 文件宣稱釘住：`main.py` 仍含註解字樣、`CLAUDE.md` 引該字樣而不引 `main.py:<行號>`。

AC-SI-28-3：①～④ 任一格轉紅，失敗訊息須含 OBS-SI-010、升為缺陷列、FR-SI-12（由 `assert_cell`
附上）；⑤ 只是文件宣稱，訊息只需點名問題。

🔴 誠實劃界：形態判準（AST）。`getattr`／`importlib` 等動態建構看不到；另有幾種靜態但不在判準內的
寫法同樣看不到——`PersistenceResult` 以位置引數或 `**` 展開傳 `kind`、經別名或 `replace()` 間接
產出，以及以 `getattr(cfg, "…")` 字串讀旗標。落地當回合實查：引擎內 `"evolved_playbook"` 字面只
在 `core/resolution_policy.py` 的比較式出現一次、`PersistenceResult(...)` 呼叫無位置引數與 `**`、
`require_evolution_signoff` 沒有字串形態——這些寫法現況零出現、無暴露證據（PRD 守衛面准入：無證據
取最小形態），故只在此登記、不擴搜。① 只判函式存在：r85 函式被加 skip 或改弱斷言，本格看不見，
由 r85 檔隨全套 pytest 把關。

單跑一個 AT：`python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_1_1 -q`
（cwd＝`AutoClaude/`）。本機 PG 在場時 `tests/conftest.py` 拒絕「PG 在場＋xdist worksteal」的
組合（rc=4、一支測試都不跑），須加 `-n 0` 或 `--dist loadgroup`；與本檔無關，AutoClaude 任何
pytest 皆然。
"""
from __future__ import annotations

import ast
import itertools
import re
import textwrap
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

_AUTOCLAUDE = Path(__file__).resolve().parents[2]  # AutoClaude/
_PKG = _AUTOCLAUDE / "autoclaude"
_R85_FILE = _AUTOCLAUDE / "tests" / "core" / "test_kernel_unhandled_mutation_failloud_r85.py"
_CLAUDE_MD = _AUTOCLAUDE / "CLAUDE.md"
_MAIN_PY = _PKG / "main.py"
_CONFIG_PY = _PKG / "utils" / "config.py"

#: ① r85 檔必須仍含的兩個函式（`PlaybookRunner` 零生產建構點的鎖，與掃描器的對照組）。
R85_LOCKS: tuple[str, ...] = (
    "test_playbook_runner_has_no_production_construction_site",
    "test_the_scanner_can_see_production_sites_at_all",
)

#: ② 受檢清單：`apply_evolution` 的呼叫點，以（相對 `autoclaude/` 的 POSIX 路徑，外層函式名）
#: 登記。不寫行號——行號會腐（這正是本檔要文件改引註解字樣、不引 `main.py:<行號>` 的同一個理由）。
#: 以多重集合比對：同一函式內多一個呼叫也算多一個呼叫點。
_ESCALATION_HANDLER = "execution/steps_orchestrator/_escalation_handler.py"
APPLY_EVOLUTION_SITES: tuple[tuple[str, str], ...] = (
    (_ESCALATION_HANDLER, "handle_convergence_escalation"),
    (_ESCALATION_HANDLER, "handle_max_retries_escalation"),
    (_ESCALATION_HANDLER, "_handle_goal_synthesis_recovery"),
    ("execution/mutation_applier/_complex_mutations.py", "_trigger_goto_escalation"),
)
#: ② 只有 `execution/`（舊 runner 的實作面）可以 import 的模組路徑片段。
_EXECUTION_ONLY_MODULES: tuple[str, ...] = ("steps_orchestrator", "mutation_applier")

#: ③ 演化重載生產者的排除檔（定義與彙整，不是生產）。`core/kernel_state.py` 定義結果欄位
#: `evolved_playbook_path`；`core/resolution_policy.py` 把各 plugin 的 `PersistenceResult`
#: 彙整成 `MergedResult(evolved_playbook_path=…)`——它讀 `kind == "evolved_playbook"`、
#: 不產出。兩檔之外，`plugins/` 與 `core/` 出現同形態＝出現了生產者。
PRODUCER_EXCLUDED: frozenset[str] = frozenset({
    "core/kernel_state.py",
    "core/resolution_policy.py",
})
_PRODUCER_DIRS: tuple[str, ...] = ("plugins", "core")
_EVOLVED_KIND = "evolved_playbook"

#: ④ 唯一准許讀取 `require_evolution_signoff` 的檔（舊 runner 的 `_evolution_signoff_granted`）。
SIGNOFF_FIELD = "require_evolution_signoff"
SIGNOFF_READER = "execution/playbook_runner.py"

#: ⑤／AC-SI-28-2：文件的演化敘述行以 `ON_ESCALATION` 為錨；改述須含四個片段並引註解字樣。
EVOLUTION_DOC_ANCHOR = "ON_ESCALATION"
REWRITE_FRAGMENTS: tuple[str, ...] = (
    "Kernel 路徑只提案", "預設放行", "無生產建構點", "無演化重載生產者",
)
W6_COMMENT = "舊 PlaybookRunner 直連模式已於 W6 拔除"
#: 行號形態。冒號含全形（繁中文件常見）：只擋半形會讓 `main.py：277` 這種改寫繞過本格。
LINE_REF_RE = re.compile(r"main\.py[:：]\d+")
#: 既有鎖 `tests/contract/test_claude_md_no_long_lines.py` 的單行上限（碼位數）。
DOC_LINE_MAX = 800

#: AC-SI-28-3：①～④ 轉紅的訊息必含這三個片段（`message_ok` 判）。
MESSAGE_FRAGMENTS: tuple[str, ...] = ("OBS-SI-010", "升為缺陷列", "FR-SI-12")
ESCALATION_HINT = (
    "AC-SI-28-3：本格轉紅代表「演化只提案不套用」賴以成立的事實變了（OBS-SI-010 再開症狀："
    "生產路徑出現 PlaybookRunner 建構點或演化重載生產者）。立即升為缺陷列，並走 FR-SI-12 的"
    "人工閘（此時暴露證據成立）；有意拔除呼叫點也走同一道閘確認後才同步受檢清單，不得只為"
    "轉綠而改清單。"
)


@dataclass(frozen=True)
class Site:
    """一個被掃描器看見的站點。"""

    path: str  # 相對 `autoclaude/` 的 POSIX 路徑
    func: str  # 最近的外層函式名；模組層級為 `<module>`
    line: int
    detail: str = ""


@dataclass
class Scan:
    """對一棵 `autoclaude/` 樹一趟 AST 普查的全部站點（各格的判準只讀這份事實）。"""

    parse_errors: list[str] = field(default_factory=list)
    apply_calls: list[Site] = field(default_factory=list)
    forbidden_imports: list[Site] = field(default_factory=list)
    path_kwargs: list[Site] = field(default_factory=list)
    persistence_calls: list[Site] = field(default_factory=list)
    evolved_kinds: list[Site] = field(default_factory=list)
    signoff_reads: list[Site] = field(default_factory=list)


def _callee(call: ast.Call) -> str | None:
    """被呼叫者的名字：`f(...)` 取 `Name.id`、`x.f(...)` 取 `Attribute.attr`（同 r85 檔判準）。"""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _kind_is_evolved(call: ast.Call) -> bool:
    """`PersistenceResult(...)` 的 keyword `kind` 是不是常數 `"evolved_playbook"`。"""
    return any(
        kw.arg == "kind" and isinstance(kw.value, ast.Constant) and kw.value.value == _EVOLVED_KIND
        for kw in call.keywords
    )


class _Collector(ast.NodeVisitor):
    """走一個模組，把五格要的站點記進 `Scan`；外層函式名以進出 `def` 維護。"""

    def __init__(self, rel: str, scan: Scan) -> None:
        self._rel, self._scan, self._scope = rel, scan, ["<module>"]

    def _site(self, node: ast.AST, detail: str = "") -> Site:
        return Site(self._rel, self._scope[-1], node.lineno, detail)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _imports(self, node: ast.AST, names: Iterable[str], dots: str = "") -> None:
        for name in names:
            if any(part in name for part in _EXECUTION_ONLY_MODULES):
                self._scan.forbidden_imports.append(self._site(node, dots + name))
                return

    def visit_Import(self, node: ast.Import) -> None:
        self._imports(node, [a.name for a in node.names])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # `from a.b import c` 與 `from . import steps_orchestrator` 兩種都要看：模組路徑與被引名。
        names = [node.module or "", *(a.name for a in node.names)]
        self._imports(node, names, "." * node.level)

    def visit_Call(self, node: ast.Call) -> None:
        name = _callee(node)
        if name == "apply_evolution":
            self._scan.apply_calls.append(self._site(node))
        for kw in node.keywords:
            if kw.arg == "evolved_playbook_path":
                self._scan.path_kwargs.append(self._site(kw, "evolved_playbook_path="))
        if name == "PersistenceResult":
            self._scan.persistence_calls.append(self._site(node))
            if _kind_is_evolved(node):
                self._scan.evolved_kinds.append(self._site(node, 'kind="evolved_playbook"'))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == SIGNOFF_FIELD and isinstance(node.ctx, ast.Load):
            self._scan.signoff_reads.append(self._site(node))
        self.generic_visit(node)


def scan_package(root: Path) -> Scan:
    """AST 普查 `root`（`autoclaude/` 套件根）：一趟解析，蒐集五格需要的全部站點。

    解析不了的檔不得被略過：掃描器對它失明＝零命中不可信，記入 `parse_errors` 由各格回報。
    """
    scan = Scan()
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root).as_posix()
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            scan.parse_errors.append(f"{rel}（{type(exc).__name__}：{exc}）")
            continue
        _Collector(rel, scan).visit(tree)
    return scan


def _as_scan(src: Path | Scan) -> Scan:
    return src if isinstance(src, Scan) else scan_package(src)


def count_under(sites: Iterable[Site], prefix: str) -> int:
    """站點中路徑以 `prefix` 起頭者的數量（目錄前綴或單一檔皆可）。"""
    return sum(1 for s in sites if s.path.startswith(prefix))


def _ordered(sites: Iterable[Site]) -> list[Site]:
    return sorted(sites, key=lambda s: (s.path, s.line))


def _blind(scan: Scan) -> list[str]:
    return [f"掃描器無法解析 {e}：對它失明，零命中不可信" for e in scan.parse_errors]


def cell1_problems(r85_text: str | None, required: Iterable[str] = R85_LOCKS) -> list[str]:
    """① 引用格：r85 檔（文字；檔不存在傳 `None`）仍含兩個鎖。空清單＝通過。"""
    if r85_text is None:
        return ["① r85 檔不存在（被移動或刪除）：它所守的鎖是否仍在不可判"]
    try:
        tree = ast.parse(r85_text)
    except SyntaxError as exc:
        return [f"① r85 檔無法解析（{exc.msg}）：它所守的鎖是否仍在不可判"]
    defined = {
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return [
        f"① r85 檔缺函式 {name}（`PlaybookRunner` 零生產建構點的鎖被移除或改名）"
        for name in required
        if name not in defined
    ]


def cell2_problems(
    src: Path | Scan, sites: Iterable[tuple[str, str]] = APPLY_EVOLUTION_SITES
) -> list[str]:
    """② `apply_evolution` 呼叫點恰為受檢清單，且 `execution/` 之外無人 import 其實作面。"""
    scan = _as_scan(src)
    found = Counter((s.path, s.func) for s in scan.apply_calls)
    want = Counter(sites)
    first_line = {(s.path, s.func): s.line for s in reversed(_ordered(scan.apply_calls))}
    problems = _blind(scan)
    for key in sorted(found - want):
        problems.append(
            f"② 受檢清單之外多出 apply_evolution 呼叫點：{key[0]} 的函式 {key[1]}"
            f"（現有 {found[key]}、登記 {want[key]}，首個在第 {first_line[key]} 行）"
        )
    for key in sorted(want - found):
        problems.append(
            f"② 受檢清單登記的 apply_evolution 呼叫點不見了：{key[0]} 的函式 {key[1]}"
            f"（現有 {found[key]}、登記 {want[key]}）"
        )
    problems += [
        f"② execution/ 之外的模組 import 了 {s.detail}：{s.path}:{s.line}"
        for s in _ordered(scan.forbidden_imports)
        if not s.path.startswith("execution/")
    ]
    return problems


def cell3_problems(src: Path | Scan, excluded: Iterable[str] = PRODUCER_EXCLUDED) -> list[str]:
    """③ `plugins/` 與 `core/`（排除檔除外）沒有演化重載生產者。"""
    scan = _as_scan(src)
    skip = set(excluded)
    problems = _blind(scan)
    for s in _ordered([*scan.path_kwargs, *scan.evolved_kinds]):
        if s.path.split("/", 1)[0] in _PRODUCER_DIRS and s.path not in skip:
            problems.append(f"③ 演化重載生產者 {s.detail} 出現在 {s.path}:{s.line}（{s.func}）")
    return problems


def cell4_problems(src: Path | Scan, allowed: str = SIGNOFF_READER) -> list[str]:
    """④ `require_evolution_signoff` 的讀取（Load 語境）只出現在 `allowed`。"""
    scan = _as_scan(src)
    return _blind(scan) + [
        f"④ {SIGNOFF_FIELD} 的讀取點出現在 {s.path}:{s.line}（只准 {allowed}）"
        for s in _ordered(scan.signoff_reads)
        if s.path != allowed
    ]


def anchor_lines(doc_text: str, anchor: str = EVOLUTION_DOC_ANCHOR) -> list[str]:
    return [ln for ln in doc_text.splitlines() if anchor in ln]


def cell5_problems(
    main_py_text: str, doc_text: str, anchor: str = EVOLUTION_DOC_ANCHOR
) -> list[str]:
    """⑤ 文件宣稱釘住：`main.py` 含註解字樣；文件引該字樣、不引 `main.py:<行號>`。"""
    problems = []
    if W6_COMMENT not in main_py_text:
        problems.append(f"⑤ main.py 已不含註解字樣「{W6_COMMENT}」：文件所引的依據消失了")
    lines = anchor_lines(doc_text, anchor)
    if not lines:
        problems.append(f"⑤ 文件中找不到含 {anchor} 的演化敘述行")
    elif not any(W6_COMMENT in ln for ln in lines):
        problems.append(f"⑤ 含 {anchor} 的敘述行都沒有引註解字樣「{W6_COMMENT}」")
    for ln in lines:
        hit = LINE_REF_RE.search(ln)
        if hit:
            problems.append(
                f"⑤ 文件引了行號形態 {hit.group(0)}（行號會再腐，改引註解字樣）：{ln.strip()[:60]}…"
            )
    return problems


def _default_value(expr: ast.expr | None) -> object:
    """欄位預設值的字面常數；`Field(default=…)` 取其 `default`；其餘回標記字串。"""
    if isinstance(expr, ast.Call) and _callee(expr) == "Field":
        expr = next((kw.value for kw in expr.keywords if kw.arg == "default"), None)
    if isinstance(expr, ast.Constant):
        return expr.value
    return "<非字面常數，無法以 AST 判定>"


def config_default_problems(config_src: str, field_name: str = SIGNOFF_FIELD) -> list[str]:
    """AC-SI-28-2：`field_name` 欄位的預設值仍為 `False`（AST 讀欄位預設，零退化）。"""
    tree = ast.parse(config_src)
    decls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        and n.target.id == field_name
    ]
    if not decls:
        return [f"AC-SI-28-2：找不到欄位 {field_name} 的宣告（AnnAssign）"]
    return [
        f"AC-SI-28-2：{field_name} 的預設值是 {_default_value(d.value)!r}（第 {d.lineno} 行），"
        "不是 False——零退化被破壞（演化版自動重載的放行姿態變了）"
        for d in decls
        if _default_value(d.value) is not False
    ]


def doc_rewrite_problems(
    doc_text: str,
    fragments: Iterable[str] = REWRITE_FRAGMENTS,
    anchor: str = EVOLUTION_DOC_ANCHOR,
) -> list[str]:
    """AC-SI-28-2：至少一行含 `anchor` 的敘述行同時含全部改述片段；缺的片段逐一點名。"""
    need = tuple(fragments)
    lines = anchor_lines(doc_text, anchor)
    if not lines:
        return [f"AC-SI-28-2：文件中找不到含 {anchor} 的演化敘述行"]
    if any(all(f in ln for f in need) for ln in lines):
        return []
    best = max(lines, key=lambda ln: sum(f in ln for f in need))
    return [f"AC-SI-28-2：演化敘述行缺改述片段「{f}」" for f in need if f not in best]


def doc_length_problems(
    doc_text: str, limit: int = DOC_LINE_MAX, anchor: str = EVOLUTION_DOC_ANCHOR
) -> list[str]:
    """AC-SI-28-2：每個含 `anchor` 的行長度（碼位數）不超過 `limit`。"""
    return [
        f"AC-SI-28-2：含 {anchor} 的敘述行（第 {n} 行）長 {len(ln)} 個碼位，超過 {limit}"
        for n, ln in enumerate(doc_text.splitlines(), start=1)
        if anchor in ln and len(ln) > limit
    ]


def message_ok(text: str) -> bool:
    """AC-SI-28-3：訊息是否同時含 `MESSAGE_FRAGMENTS` 三個片段。"""
    return all(fragment in text for fragment in MESSAGE_FRAGMENTS)


def assert_cell(label: str, problems: list[str], *, escalate: bool = True) -> None:
    """有問題就丟 `AssertionError`。`escalate`＝附上 AC-SI-28-3 的人工閘指示（①～④ 用）。"""
    if problems:
        head = f"{label} 轉紅（{len(problems)} 項）：\n  " + "\n  ".join(problems)
        raise AssertionError(f"{head}\n{ESCALATION_HINT}" if escalate else head)


def real_tree_control_problems(scan: Scan) -> list[str]:
    """對照組：掃描器必須在已知有生產站點的地方真的看得見它們，否則各格的零命中不可信。

    門檻取現況值的下緣（④ 取恰等於）；掃描器退化或站點被改寫時才會紅。
    """
    checks = (
        ("② execution/ 內的 apply_evolution 呼叫",
         count_under(scan.apply_calls, "execution/"), 4, False),
        ("② execution/ 內對 steps_orchestrator／mutation_applier 的 import",
         count_under(scan.forbidden_imports, "execution/"), 1, False),
        ("③ execution/ 內的 evolved_playbook_path= keyword",
         count_under(scan.path_kwargs, "execution/"), 3, False),
        ("③ core/resolution_policy.py 內的 evolved_playbook_path= keyword",
         count_under(scan.path_kwargs, "core/resolution_policy.py"), 1, False),
        ("③ plugins/ 內的 PersistenceResult(...) 呼叫",
         count_under(scan.persistence_calls, "plugins/"), 1, False),
        (f"④ {SIGNOFF_READER} 內的 {SIGNOFF_FIELD} 讀取",
         count_under(scan.signoff_reads, SIGNOFF_READER), 1, True),
    )
    return [
        f"對照組失敗：{label} 掃到 {seen}，應{'恰為' if exact else '不少於'} {want}"
        "——掃描器可能壞了（或站點被改寫），此時各格的零命中不可信"
        for label, seen, want, exact in checks
        if (seen != want if exact else seen < want)
    ]


@pytest.fixture
def make_tree(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """`make_tree({相對路徑: 原始碼})`：在 tmp 下建一棵合成 `autoclaude/` 樹並回傳其根。

    每次呼叫各用獨立目錄（同一個測試要並排比較多棵樹）；原始碼會先 `dedent`。
    """
    counter = itertools.count()

    def _make(files: dict[str, str]) -> Path:
        root = tmp_path / f"tree{next(counter)}" / "autoclaude"
        for rel, text in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(textwrap.dedent(text), encoding="utf-8")
        return root

    return _make


# ── 合成樹的素材（注入負控用；全是原始碼文字，不會被執行）──────────────────────────
_SYN_SITES = ((_ESCALATION_HANDLER, "f1"), (_ESCALATION_HANDLER, "f2"))
_TWO_CALLS = textwrap.dedent("""\
    def f1(runner):
        return runner._evolver.apply_evolution(1)

    def f2(runner):
        return runner._evolver.apply_evolution(2)
""")
_EXTRA_CALL = "\n\ndef f3(runner):\n    return runner._evolver.apply_evolution(3)\n"
_R85_TEXT = textwrap.dedent("""\
    class TestLocks:
        def test_playbook_runner_has_no_production_construction_site(self): ...
        def test_the_scanner_can_see_production_sites_at_all(self): ...
""")
_PRODUCER_PATH_KW = 'def g():\n    return Foo(evolved_playbook_path="p")\n'
_RUNNER_READ = textwrap.dedent("""\
    class Runner:
        def granted(self):
            return self._cfg.playbook.require_evolution_signoff
""")
_CONFIG_DECL = textwrap.dedent("""\
    class PlaybookConfig:
        require_evolution_signoff: bool = False
""")
_SIGNOFF_READ = "def g(cfg):\n    return cfg.playbook.require_evolution_signoff\n"


class TestRealTree:
    """真樹：五格皆綠，且每格的掃描器在已知有生產站點的地方看得見它們。"""

    def test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites(self):
        scan = scan_package(_PKG)
        r85_text = _R85_FILE.read_text(encoding="utf-8") if _R85_FILE.is_file() else None
        assert_cell("格 ①", cell1_problems(r85_text))
        assert_cell("格 ②", cell2_problems(scan))
        assert_cell("格 ③", cell3_problems(scan))
        assert_cell("格 ④", cell4_problems(scan))
        main_py_text = _MAIN_PY.read_text(encoding="utf-8")
        doc_text = _CLAUDE_MD.read_text(encoding="utf-8")
        assert_cell("格 ⑤", cell5_problems(main_py_text, doc_text), escalate=False)
        # 對照組放在各格之後：它只負責替「綠」作保（零命中是看見了才零、不是瞎了才零）；
        # 真有站點被增刪時，要先由上面各格以精確訊息點名，而不是被「掃描器壞了」蓋過去。
        controls = real_tree_control_problems(scan)
        assert not controls, "\n".join(controls)


class TestInjectedViolations:
    """合成樹注入：違規時各格真的轉紅並點名違規處；合法對照樹為對照（鎖不可恆紅）。"""

    def test_AT_128_1_E_1_missing_lock_and_stray_apply_sites_turn_cells_1_and_2_red(
        self, make_tree
    ):
        base = {_ESCALATION_HANDLER: _TWO_CALLS}
        # 對照：合法樹的 ① ② 皆綠（兩個鎖函式都在、兩個呼叫點恰為登記）
        assert cell1_problems(_R85_TEXT) == []
        assert cell2_problems(make_tree(base), _SYN_SITES) == []
        # 情境一（①）：兩個鎖函式各缺一個，各自被點名、且只點名缺的那個
        for lost in R85_LOCKS:
            kept = next(name for name in R85_LOCKS if name != lost)
            problems = cell1_problems(_R85_TEXT.replace(f"def {lost}", "def renamed_helper"))
            assert len(problems) == 1, problems
            assert lost in problems[0] and kept not in problems[0], problems
        # r85 檔本身不存在（被移動或刪除）也是 ① 轉紅，不是例外
        assert any("不存在" in p for p in cell1_problems(None))
        # 情境二（②）：(a)～(e) 各自轉紅並點名
        cases = {
            "a 同檔多一個呼叫（f3）": ({_ESCALATION_HANDLER: _TWO_CALLS + _EXTRA_CALL}, "f3"),
            "b 移除 f2 內的呼叫": (
                {_ESCALATION_HANDLER: _TWO_CALLS.replace("apply_evolution(2)", "other(2)")}, "f2"),
            "c plugins/ 內多一個呼叫": (
                {**base, "plugins/x.py": "def g(e):\n    return e.apply_evolution(0)\n"},
                "plugins/x.py"),
            "d plugins/ import steps_orchestrator": (
                {**base, "plugins/y.py":
                    "from autoclaude.execution.steps_orchestrator import run_steps_impl\n"},
                "plugins/y.py"),
            "e core/ import mutation_applier": (
                {**base, "core/z.py":
                    "from autoclaude.execution.mutation_applier import apply_single_mutation\n"},
                "core/z.py"),
            "f 登記函式 f1 內多一個呼叫（多重集合才抓得到）": (
                {_ESCALATION_HANDLER: _TWO_CALLS.replace(
                    "return runner._evolver.apply_evolution(1)",
                    "runner._evolver.apply_evolution(0)\n    "
                    "return runner._evolver.apply_evolution(1)")},
                "f1"),
        }
        for label, (files, named) in cases.items():
            problems = cell2_problems(make_tree(files), _SYN_SITES)
            assert problems and any(named in p for p in problems), (label, problems)
        self._scanner_edge_cases(make_tree)

    @staticmethod
    def _scanner_edge_cases(make_tree):
        """補強 E-1：import 的三種寫法都要被看見、execution/ 內放行且掃得到、解析不了的檔要回報。"""
        forms = {
            "import 並取別名": "import autoclaude.execution.steps_orchestrator as so\n",
            "從套件取子模組": "from autoclaude.execution import mutation_applier\n",
            "相對 import": "from ..execution.mutation_applier import apply_single_mutation\n",
        }
        for label, source in forms.items():
            problems = cell2_problems(make_tree({"plugins/v.py": source}), ())
            assert any("plugins/v.py" in p for p in problems), (label, problems)
        inside = scan_package(make_tree({"execution/inner.py":
                                         "from .steps_orchestrator import run_steps_impl\n"}))
        assert cell2_problems(inside, ()) == []
        assert count_under(inside.forbidden_imports, "execution/") == 1
        # 解析不了的檔不得被當成「沒有命中」：掃描器對它失明，各格都要回報
        broken = make_tree({"plugins/broken.py": "def broken(:\n"})
        for cell in (cell2_problems(broken, ()), cell3_problems(broken), cell4_problems(broken)):
            assert any("plugins/broken.py" in p for p in cell), cell

    def test_AT_128_1_E_2_injected_producers_turn_cell_3_red_excluded_files_do_not(
        self, make_tree
    ):
        base = {
            "plugins/a.py": "def f():\n    return 1\n",
            "core/c.py": "X = 1\n",
            "core/resolution_policy.py": _PRODUCER_PATH_KW,  # 排除檔：彙整處的合法同形態
            "execution/p1.py": _PRODUCER_PATH_KW,
            "execution/p2.py": _PRODUCER_PATH_KW,
            "execution/p3.py": _PRODUCER_PATH_KW,
        }
        # 對照：合法樹 ③ 綠；掃描器在 execution/ 找到 3 個、在排除檔 resolution_policy 找到 1 個
        scan = scan_package(make_tree(base))
        assert cell3_problems(scan) == []
        assert count_under(scan.path_kwargs, "execution/") == 3
        assert count_under(scan.path_kwargs, "core/resolution_policy.py") == 1
        injected = {
            "a plugins/ 帶 evolved_playbook_path=": ({"plugins/x.py": _PRODUCER_PATH_KW},
                                                    "plugins/x.py"),
            "b core/ 的 PersistenceResult(kind=evolved_playbook)": (
                {"core/other.py":
                    'def g():\n    return PersistenceResult(kind="evolved_playbook")\n'},
                "core/other.py"),
            "e 屬性形態 hookspec.PersistenceResult(...)": (
                {"plugins/h.py":
                    'def g():\n    return hookspec.PersistenceResult(kind="evolved_playbook")\n'},
                "plugins/h.py"),
        }
        for label, (files, named) in injected.items():
            problems = cell3_problems(make_tree({**base, **files}))
            assert any(named in p for p in problems), (label, problems)
        # (c) 不同常數：掃描器看得見該呼叫、只是常數不是 evolved_playbook ⇒ 放行
        other_kind = scan_package(make_tree(
            {**base, "plugins/y.py": 'def g():\n    return PersistenceResult(kind="other")\n'}))
        assert cell3_problems(other_kind) == []
        assert count_under(other_kind.persistence_calls, "plugins/y.py") == 1
        # (d) 排除檔內的同形態不判
        excluded = make_tree({**base, "core/kernel_state.py": _PRODUCER_PATH_KW})
        assert cell3_problems(excluded) == []

    def test_AT_128_1_E_3_extra_signoff_read_turns_cell_4_red_store_context_does_not(
        self, make_tree
    ):
        base = {SIGNOFF_READER: _RUNNER_READ, "utils/config.py": _CONFIG_DECL}
        # 對照：合法樹 ④ 綠；欄位宣告（AnnAssign）不算讀取，runner 內恰一個讀取
        legit = scan_package(make_tree(base))
        assert cell4_problems(legit) == []
        assert len(legit.signoff_reads) == 1
        assert count_under(legit.signoff_reads, SIGNOFF_READER) == 1
        for label, files, named in (
            ("a execution/ 內另一處讀取", {"execution/other.py": _SIGNOFF_READ},
             "execution/other.py"),
            ("b plugins/ 讀取", {"plugins/p.py": _SIGNOFF_READ}, "plugins/p.py"),
        ):
            problems = cell4_problems(make_tree({**base, **files}))
            assert any(named in p for p in problems), (label, problems)
        # (c) Store 語境的賦值不是讀取
        store = {"plugins/q.py": "def h(cfg):\n    cfg.require_evolution_signoff = True\n"}
        assert cell4_problems(make_tree({**base, **store})) == []

    def test_AT_128_1_E_4_doc_pin_rejects_missing_phrase_line_numbers_and_stale_main(self):
        doc_ok = f"- ESCALATION：再發 `ON_ESCALATION`；依據＝`main.py` 註解字樣「{W6_COMMENT}」\n"
        main_ok = f"    # {W6_COMMENT}（DeprecationWarning 期已結束）。\n"
        assert cell5_problems(main_ok, doc_ok) == []  # 對照
        # (a) 文件改成含 main.py:277 的形態：保留字樣者只剩行號一項；以行號取代字樣者兩項都報
        kept = doc_ok.rstrip("\n") + "，見 main.py:277\n"
        problems = cell5_problems(main_ok, kept)
        assert len(problems) == 1 and "main.py:277" in problems[0], problems
        swapped = "- ESCALATION：再發 `ON_ESCALATION`；依據＝main.py:277\n"
        problems = cell5_problems(main_ok, swapped)
        assert any("main.py:277" in p for p in problems), problems
        assert any("沒有引註解字樣" in p for p in problems), problems
        fullwidth = doc_ok.rstrip("\n") + "，見 main.py：277\n"
        assert cell5_problems(main_ok, fullwidth), "全形冒號的行號形態被放行"
        # (b) 含 ON_ESCALATION 的行都不含字樣
        problems = cell5_problems(main_ok, "- ESCALATION：再發 `ON_ESCALATION`；只提案\n")
        assert any("沒有引註解字樣" in p for p in problems), problems
        # (c) 兩行含 ON_ESCALATION，其一合規、其一含 main.py:12 ⇒ 只點名含行號的那一行
        mixed = doc_ok + "- 另一行 `ON_ESCALATION` 見 main.py:12\n"
        problems = cell5_problems(main_ok, mixed)
        assert len(problems) == 1 and "main.py:12" in problems[0], problems
        assert "依據＝" not in problems[0], problems
        # (d) main.py 缺註解字樣；文件缺錨行
        problems = cell5_problems("x = 1\n", doc_ok)
        assert any("main.py 已不含註解字樣" in p for p in problems), problems
        assert any("找不到含 ON_ESCALATION" in p for p in cell5_problems(main_ok, "沒有錨行\n"))


class TestDefaultAndRewrite:
    """AC-SI-28-2：預設值零退化，文件改述為「只提案、預設放行、無建構點、無生產者」。"""

    def test_AT_128_2_1_default_still_false_and_doc_rewritten_within_line_budget(self):
        config_src = _CONFIG_PY.read_text(encoding="utf-8")
        doc_text = _CLAUDE_MD.read_text(encoding="utf-8")
        assert_cell("AC-SI-28-2 預設值", config_default_problems(config_src), escalate=False)
        assert_cell("AC-SI-28-2 改述片段", doc_rewrite_problems(doc_text), escalate=False)
        assert_cell("AC-SI-28-2 行長", doc_length_problems(doc_text), escalate=False)

    def test_AT_128_2_E_1_flipped_default_deleted_fragment_and_overlong_line_are_caught(self):
        decl = "class PlaybookConfig:\n    require_evolution_signoff: bool = {}\n"
        # 對照：預設 False（含 pydantic 的 Field(default=False) 寫法）綠
        assert config_default_problems(decl.format("False")) == []
        assert config_default_problems(decl.format("Field(default=False, description='x')")) == []
        # (a) 預設被改成 True（兩種寫法）、欄位消失、預設不是字面常數，皆紅
        assert config_default_problems(decl.format("True"))
        assert config_default_problems(decl.format("Field(default=True)"))
        assert config_default_problems(decl.format("compute()"))
        assert config_default_problems("class PlaybookConfig:\n    other: bool = False\n")
        # 對照：四個片段齊全、含錨、長度恰 800 個碼位的行，文件判準與長度判準皆綠
        head = f"{EVOLUTION_DOC_ANCHOR}：" + "；".join(REWRITE_FRAGMENTS)
        line = head + "。" * (DOC_LINE_MAX - len(head))
        assert len(line) == DOC_LINE_MAX
        assert doc_rewrite_problems(line) == []
        assert doc_length_problems(line) == []
        # (b) 四個片段各刪一個的副本：各自紅並點名被刪的片段（且只點名它）
        for fragment in REWRITE_FRAGMENTS:
            problems = doc_rewrite_problems(line.replace(fragment, ""))
            assert len(problems) == 1 and fragment in problems[0], (fragment, problems)
        # (c) 同一行補長到 801 個碼位：長度判準紅；文件判準仍綠（兩者各管一件事）
        assert doc_length_problems(line + "。")
        assert doc_rewrite_problems(line + "。") == []

    def test_AT_128_2_E_2_rewrite_fragments_constant_is_pinned_independently(self):
        # 期望值以字面獨立寫出（取自 R66；不由常數衍生）：常數被自己的負控迴圈引用，改常數會
        # 讓負控一起改判而全綠，所以要在常數之外另釘一次。
        expected = {"Kernel 路徑只提案", "預設放行", "無生產建構點", "無演化重載生產者"}
        assert len(REWRITE_FRAGMENTS) == 4 and set(REWRITE_FRAGMENTS) == expected
        frags = list(REWRITE_FRAGMENTS)
        mutants = [frags[:i] + frags[i + 1 :] for i in range(len(frags))]
        mutants += [frags[:i] + [frags[i] + "x"] + frags[i + 1 :] for i in range(len(frags))]
        mutants.append([*frags, "多出來的片段"])
        assert len(mutants) == 9
        for mutant in mutants:
            assert set(mutant) != expected, mutant


class TestHumanGate:
    """AC-SI-28-3：①～④ 轉紅的失敗訊息指向人工閘；訊息判準自己不是恆真。"""

    def test_AT_128_3_1_cells_1_to_4_failure_messages_point_to_the_human_gate(self, make_tree):
        injections = {
            "①": lambda: assert_cell("格 ①", cell1_problems(
                _R85_TEXT.replace("def test_the_scanner_can_see_production_sites_at_all",
                                  "def renamed_helper"))),
            "①（r85 檔不存在）": lambda: assert_cell("格 ①", cell1_problems(None)),
            "②": lambda: assert_cell("格 ②", cell2_problems(
                make_tree({_ESCALATION_HANDLER: _TWO_CALLS + _EXTRA_CALL}), _SYN_SITES)),
            "③": lambda: assert_cell("格 ③", cell3_problems(
                make_tree({"plugins/x.py": _PRODUCER_PATH_KW}))),
            "④": lambda: assert_cell("格 ④", cell4_problems(
                make_tree({SIGNOFF_READER: _RUNNER_READ, "execution/other.py": _SIGNOFF_READ}))),
        }
        for cell, run in injections.items():
            with pytest.raises(AssertionError) as caught:
                run()
            message = str(caught.value)
            for fragment in MESSAGE_FRAGMENTS:
                assert fragment in message, (cell, fragment, message)
            assert message_ok(message), (cell, message)

    def test_AT_128_3_E_1_message_check_is_not_vacuous_and_cell_5_is_exempt(self):
        compliant = "OBS-SI-010 再開；立即升為缺陷列，並走 FR-SI-12 的人工閘"
        assert message_ok(compliant)
        for fragment in MESSAGE_FRAGMENTS:  # 缺任一片段的訊息都不合格
            assert not message_ok(compliant.replace(fragment, "")), fragment
        # 格 ⑤ 只是文件宣稱：轉紅時訊息只需點名問題，不要求含人工閘字樣（判準只套用在 ①～④）
        main_ok = f"# {W6_COMMENT}\n"
        doc_bad = "- ESCALATION：再發 `ON_ESCALATION`，依據 main.py:277\n"
        with pytest.raises(AssertionError) as caught:
            assert_cell("格 ⑤", cell5_problems(main_ok, doc_bad), escalate=False)
        assert "main.py:277" in str(caught.value)
