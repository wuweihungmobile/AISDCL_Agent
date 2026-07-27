#!/usr/bin/env python3
"""`_sdd_versions` 的權威源 parity 鎖 + 呼叫端接線鎖（R58 發現 #8／#20）。

## 兩層鎖，缺一不可

R58 收斂把四份「AISDLC_SDD 版本目錄正則」合成一份 `tools/tests/_sdd_versions.py`。
R57 判例明載：**收斂而不鎖呼叫端＝把 N 個弱鎖換成 1 個沒有強制力的弱鎖，嚴格更差**，
故本檔同一次落地兩層鎖：

  1. **權威源 parity**（`TestAuthorityParity`）——`_sdd_versions` 自持的字面值必須與
     `AISDLC_SDD/scripts/sdd_version.py::VERSION_DIR_RE`（LATEST 解析 SSOT，
     DEF-101-133）語意等價。跨子專案邊界**不 import**（本 repo 既有裁定），改以
     `ast` 讀取權威源**檔案文字**抽出字面值——手法比照 R57 DEF-101-478「只讀不
     import 另一子專案的檔案做樣本 parity」。權威源改了而測試側沒跟＝翻紅。
  2. **呼叫端接線**（`TestSsotCallsiteLock`）——已知四支呼叫端必須真的 import 並
     使用 SSOT 符號；且 `tools/tests/` 下**任何**檔案都不得自己再寫一份版本目錄
     正則字面值（前瞻掃描，非函式名黑名單——第五份複本即使取全新名字也會被抓到）。

## 為什麼用 ast 而不是文字比對

`ast.parse()` 建樹時直接丟棄註解，且字串字面值不會變成 `ImportFrom`／`Name` 節點，
所以「把接線留在註解或 docstring 裡假裝有接」這種 R57 QA-R57-02 記載的繞過手法
在結構上不成立（`test_lock_is_immune_to_comment_or_string_only_wiring` 常駐鎖住）。

## 涵蓋面（三段式，誠實記載）

已實測涵蓋（下方 `test_reinvention_scanner_discriminates` 逐一注入驗證）：
`re.compile(r"…")` 引數、模組層／類別層賦值右側、dict／list 容器內、字串相加
（`BinOp`）與 f-string（`JoinedStr`）組出的正則、`\\d`／`(\\d`／`[0-9]` 三種數字
樣式寫法。
已實測不涵蓋（刻意，避免「提及即違規」的偽陽性）：docstring／裸字串陳述裡的散文
提及、`#` 註解（AST 根本看不到）、以及**不含**正則元字元的純字面版本名
（如 `"AISDLC_SDD_v0.01"`——`test_gha_action_versions.py` 有這種合法固定樣本，
把它們算成違規只會製造噪音）。
未窮舉：從檔案／環境變數讀進來的 pattern、`chr()`／`"".join()` 這類執行期組字串、
以及「不用正則、改用 30 個版本名硬編清單」的等價再發明。

執行：python -m pytest tools/tests/test_sdd_versions.py -v
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sdd_versions import (  # noqa: E402
    FROZEN_SDD_PATH_PATTERN,
    FROZEN_SDD_PATH_RE,
    FROZEN_VERSION_DIR_PATTERN,
    exclude_frozen_sdd_versions,
    is_frozen_version_dir_name,
)

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_AUTHORITY_PY = _REPO_ROOT / "AISDLC_SDD" / "scripts" / "sdd_version.py"
_AUTHORITY_NAME = "VERSION_DIR_RE"

_SSOT_MODULE = "_sdd_versions"
_SSOT_REL = "_sdd_versions.py"

# 收斂後的呼叫端 → 該檔必須 import 並實際使用的 SSOT 符號。
# 這份 roster 是「已知呼叫端」的強鎖；「未知的第五份複本」由下方前瞻掃描負責，
# 兩者分工互補（roster 抓退化、掃描抓增生）。
_SSOT_CALLERS: dict[str, frozenset[str]] = {
    "test_windowsapps_guard_bash_parity.py": frozenset(
        {"FROZEN_SDD_PATH_RE", "exclude_frozen_sdd_versions"}
    ),
    "test_windowsapps_guard_cross_consistency.py": frozenset({"exclude_frozen_sdd_versions"}),
    "test_component_sanitizer_shared_layer_lock.py": frozenset({"is_frozen_version_dir_name"}),
    "test_sanitize_component_frozen_sdd_versions_lock.py": frozenset(
        {"is_frozen_version_dir_name"}
    ),
}

# 「自己又寫了一份版本目錄正則」的偵測樣式：版本目錄名前綴後**緊接正則元字元**
# （`\d` / `(` / `[`）。刻意只認元字元開頭，`"AISDLC_SDD_v0.01"` 這種純字面樣本
# 不算違規（見頂部涵蓋面「已實測不涵蓋」）。
#
# 樣式本體用字串相加組出，而**不**寫成單一字面值——否則本檔自身的偵測樣式會被
# 自己掃到而恆紅（把掃描器本體加進白名單也能解，但那會在白名單裡開一個真的洞：
# 白名單檔案內的任何再發明都不再被看見）。本 repo 已記載「字串串接可繞過文字
# 掃描」是既知邊界（test_windowsapps_guard_cross_consistency.py 變體 O）；此處
# 是該手法的合法用途——本檔是掃描器，不是待掃的呼叫端。
_VERSION_PREFIX = "AISDLC_SDD" + "_v"
_REINVENTION_RE = re.compile(re.escape(_VERSION_PREFIX) + r"(?:\\d|\(|\[)")


def _authority_pattern_literal() -> str:
    """以 `ast` 從權威源檔案文字抽出 `VERSION_DIR_RE = re.compile(<字面值>)` 的字面值。

    只讀不 import（跨子專案邊界不可 import，先例見
    `tools/check_script_parity.py::_find_latest_sdd_version` 改走 subprocess CLI）。
    抽不到即 fail-loud——權威源結構變了必須有人看見，不可靜默跳過。
    """
    tree = ast.parse(_AUTHORITY_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == _AUTHORITY_NAME for t in node.targets):
            continue
        call = node.value
        if (
            isinstance(call, ast.Call)
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            return call.args[0].value
    raise AssertionError(
        f"{_AUTHORITY_PY} 找不到 `{_AUTHORITY_NAME} = re.compile(<字面值>)` 形狀的權威樣式"
        "——權威源結構已變動，測試側 SSOT 必須人工複核後同步"
    )


def _strip_capture_groups(pattern: str) -> str:
    """移除 capture group 括號（權威源為了取版號而帶 `(\\d+)`，測試側不需要取值）。

    只移除**未被反斜線轉義**的裸 `(` / `)`；`\\(` 這種要匹配字面括號的寫法保留。
    這是本鎖唯一容許的差異，其餘任何字元差異都會翻紅。
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\" and i + 1 < len(pattern):
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if ch not in "()":
            out.append(ch)
        i += 1
    return "".join(out)


def _string_literals(tree: ast.AST) -> list[tuple[int, str]]:
    """樹中所有「非散文」字串字面值（行號, 值）。

    散文＝docstring／裸字串陳述（`ast.Expr` 底下的 `Constant`）——說明文字大量提到
    版本目錄名，納入只會製造偽陽性而無鑑別力（判準比照
    `test_ci_scan_anchors.py::_prose_string_nodes` 既有先例）。
    """
    prose = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in prose
        ):
            hits.append((node.lineno, node.value))
        elif isinstance(node, (ast.BinOp, ast.JoinedStr)):
            # 字串相加／f-string 組出的樣式：把子樹裡的字面值無縫接起來還原
            # （手法同 `test_ci_scan_anchors.py::_joined_literal_text`；
            # f-string 插值部分無法靜態求值，故是「片段即算」的較鬆判準）。
            joined = "".join(
                sub.value
                for sub in ast.walk(node)
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
            )
            if joined:
                hits.append((node.lineno, joined))
    return hits


def _reinvented_patterns(source: str) -> list[str]:
    """該檔案內「自寫版本目錄正則」的可疑字面值（空清單＝乾淨）。"""
    try:
        # 掃「別人的」檔案時把 tokenizer 的 DeprecationWarning 關掉：本 repo 現存
        # 至少一支測試檔的 docstring 帶未轉義的 `\\s`（已實測：tools/tests/
        # test_ps51_compat.py），若不關，那支檔案的既有問題會變成本鎖每跑一次就
        # 噴一行噪音、看起來像是本鎖出錯。那是該檔自己的技術債，不在本包修改範圍。
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - 語法壞掉由別的閘門負責
        return []
    return sorted(
        {
            f"L{lineno}: {value[:60]!r}"
            for lineno, value in _string_literals(tree)
            if _REINVENTION_RE.search(value)
        }
    )


def _ssot_wiring(source: str) -> dict[str, set[str]]:
    """該檔案對 `_sdd_versions` 的接線：import 了哪些符號、實際引用了哪些 identifier。"""
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _SSOT_MODULE:
            imported |= {alias.asname or alias.name for alias in node.names}
    used = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    return {"imported": imported, "used": used}


class TestAuthorityParity(unittest.TestCase):
    """測試側樣式必須與 `sdd_version.py::VERSION_DIR_RE` 語意等價。"""

    def test_literal_equals_authority_after_dropping_capture_groups(self) -> None:
        expected = _strip_capture_groups(_authority_pattern_literal())
        self.assertEqual(
            FROZEN_VERSION_DIR_PATTERN, expected,
            "測試側版本目錄樣式已與權威源 "
            f"{_AUTHORITY_PY.relative_to(_REPO_ROOT).as_posix()}::{_AUTHORITY_NAME} 分歧"
            f"（權威源去 capture group 後＝{expected!r}）——兩邊必須同時改，"
            "否則會出現『測試側認、權威源不認』的合法版本目錄",
        )

    def test_semantics_agree_with_authority_on_adversarial_names(self) -> None:
        """字面比對之外再加一層行為等價：對抗性樣本上兩邊判讀必須逐一相同。

        字面鎖的盲區是 `_strip_capture_groups` 的正規化本身可能有誤；行為鎖不依賴
        正規化，直接用權威源字面值編一顆 regex 對照（同樣只讀不 import）。
        """
        authority = re.compile(_authority_pattern_literal())
        samples = (
            "AISDLC_SDD_v0.01",
            "AISDLC_SDD_v0.30",
            "AISDLC_SDD_v1.00",
            "AISDLC_SDD_v0.9",
            "AISDLC_SDD_v0.10",
            "AISDLC_SDD_v1.0.1",  # 三段版號：權威源不認，測試側也不得認
            "AISDLC_SDD_v1",
            "AISDLC_SDD_v0.30.bak",
            "AISDLC_SDD_v0.30 - Copy",
            "aisdlc_sdd_v0.1",
            "AISDLC_SDD",
            "",
        )
        for name in samples:
            with self.subTest(name=name):
                self.assertEqual(
                    is_frozen_version_dir_name(name),
                    authority.fullmatch(name) is not None,
                    f"{name!r} 在測試側與權威源的判讀不一致",
                )

    def test_path_projection_is_derived_from_dir_projection(self) -> None:
        """路徑投影必須是目錄投影機械推導的結果，不得是第二份手寫字面值。"""
        core = FROZEN_VERSION_DIR_PATTERN.removeprefix("^").removesuffix("$")
        self.assertEqual(FROZEN_SDD_PATH_PATTERN, "^AISDLC_SDD/(" + core + ")/")


class TestSsotBehaviour(unittest.TestCase):
    """SSOT 函式本身的行為（收斂前四份呼叫端各自依賴的語意都必須保住）。"""

    def test_exclude_keeps_latest_and_non_sdd_paths(self) -> None:
        latest = "AISDLC_SDD_v0.30"
        paths = [
            "tools/lib/windowsapps_guard.sh",
            "AISDLC_SDD/scripts/ci-gate.sh",
            f"AISDLC_SDD/{latest}/tools/x.sh",
            "AISDLC_SDD/AISDLC_SDD_v0.01/tools/x.sh",
            "AISDLC_SDD/AISDLC_SDD_v0.29/tools/x.sh",
        ]
        self.assertEqual(
            exclude_frozen_sdd_versions(paths, latest),
            [
                "tools/lib/windowsapps_guard.sh",
                "AISDLC_SDD/scripts/ci-gate.sh",
                f"AISDLC_SDD/{latest}/tools/x.sh",
            ],
        )

    def test_path_re_requires_trailing_slash_after_version_dir(self) -> None:
        """`AISDLC_SDD/AISDLC_SDD_v0.30.bak/...` 這種近似名不得被當成版本目錄前綴
        （否則 `.bak` 備份樹會被誤排除，掃描面靜默縮小）。"""
        self.assertIsNone(FROZEN_SDD_PATH_RE.match("AISDLC_SDD/AISDLC_SDD_v0.30.bak/x.sh"))
        self.assertIsNotNone(FROZEN_SDD_PATH_RE.match("AISDLC_SDD/AISDLC_SDD_v0.30/x.sh"))

    def test_dir_name_rejects_trailing_newline(self) -> None:
        """`is_frozen_version_dir_name` 用 fullmatch 而非 match：收斂前的 `.match()`
        會因 `$` 允許尾隨換行而誤中（防守性對齊權威源，見 SSOT docstring）。"""
        self.assertFalse(is_frozen_version_dir_name("AISDLC_SDD_v0.30\n"))


class TestSsotCallsiteLock(unittest.TestCase):
    """收斂必配呼叫端鎖（R57 判例）：四支呼叫端要真接線，全 tests 目錄不得再發明。"""

    def test_every_known_caller_imports_and_uses_the_ssot(self) -> None:
        for name, symbols in _SSOT_CALLERS.items():
            with self.subTest(caller=name):
                path = _TESTS_DIR / name
                self.assertTrue(path.is_file(), f"{name} 不存在——roster 已過期，請同步")
                w = _ssot_wiring(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    symbols - w["imported"], set(),
                    f"{name} 未從 {_SSOT_MODULE} import "
                    f"{sorted(symbols - w['imported'])}——SSOT 被繞過",
                )
                self.assertEqual(
                    symbols - w["used"], set(),
                    f"{name} import 了 {sorted(symbols - w['used'])} 卻沒實際引用"
                    "——載入不等於接線",
                )

    def test_no_file_under_tests_reinvents_the_version_dir_regex(self) -> None:
        """前瞻掃描：`tools/tests/` 下只有 SSOT 本身可以持有版本目錄正則字面值。

        刻意掃整個目錄（含 `_*.py` 輔助模組）而非只掃 roster 內四支——第五份複本
        取任何新名字、放任何新檔案都會被抓到。
        """
        offenders: dict[str, list[str]] = {}
        for path in sorted(_TESTS_DIR.glob("*.py")):
            if path.name in (_SSOT_REL, Path(__file__).name):
                continue
            hits = _reinvented_patterns(path.read_text(encoding="utf-8"))
            if hits:
                offenders[path.name] = hits
        self.assertEqual(
            offenders, {},
            f"以下測試檔又自己寫了一份版本目錄正則：{offenders}——"
            f"一律改 `from {_SSOT_MODULE} import …`（R58 發現 #8／#20 的收斂決策）",
        )

    def test_ssot_holds_exactly_one_version_pattern_literal(self) -> None:
        """SSOT 自身只能有一份字面值——否則「唯一真相源」內部就先分裂了。

        （本檔自己被上一條掃描排除，因為它是掃描器本體；其偵測樣式以字串相加組出
        以避免自我命中，見 `_VERSION_PREFIX` 上方註解。此處補上對 SSOT 的正向計數，
        讓排除不變成盲區。）
        """
        hits = _reinvented_patterns((_TESTS_DIR / _SSOT_REL).read_text(encoding="utf-8"))
        self.assertEqual(
            len(hits), 1,
            f"{_SSOT_REL} 內的版本目錄正則字面值有 {len(hits)} 份（預期恰 1）：{hits}",
        )

    def test_reinvention_scanner_discriminates(self) -> None:
        """掃描器鑑別力：五種再發明形狀必抓、兩種散文提及必不抓。

        沒有這條，掃描器被悄悄弱化（例如樣式被改成只認 `re.compile`）時上面兩條
        會全綠零訊號——R57 `_ci_scan_anchors` 那次就是這樣被弱化的。
        """
        pre = _VERSION_PREFIX
        for label, body in (
            ("re.compile 引數", f'import re\nR = re.compile(r"^{pre}' + r'\d+\.\d+$")' + "\n"),
            ("模組層賦值字面值", f'P = r"^{pre}' + r'\d+\.\d+$"' + "\n"),
            ("capture group 寫法", f'P = r"^{pre}' + r'(\d+)\.(\d+)$"' + "\n"),
            ("字元類別寫法", f'P = r"^{pre}' + r'[0-9]+\.[0-9]+$"' + "\n"),
            ("dict 容器內", f'D = {{"ver": r"^{pre}' + r'\d+"}' + "\n"),
            ("字串相加組出", f'P = "^{pre}" + r"' + r'\d+\.\d+$"' + "\n"),
        ):
            with self.subTest(case=label):
                self.assertNotEqual(
                    _reinvented_patterns(body), [], f"{label}：再發明未被偵測到"
                )
        for label, body in (
            ("docstring 散文提及", f'"""沿革：舊版各自寫 ^{pre}' + r'\d+\.\d+$ 這份正則。"""' + "\n"),
            ("# 註解提及", f"# 舊版：^{pre}" + r"\d+\.\d+$" + "\n" + "X = 1\n"),
            ("純字面版本名", f'S = "{pre}0.01"\n'),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    _reinvented_patterns(body), [], f"{label}：不該被判為再發明（偽陽性）"
                )

    def test_lock_is_immune_to_comment_or_string_only_wiring(self) -> None:
        """把接線留在註解／docstring 裡假裝有接，對本鎖無效（R57 QA-R57-02 手法）。"""
        fake = (
            f'"""from {_SSOT_MODULE} import exclude_frozen_sdd_versions"""\n'
            f"# from {_SSOT_MODULE} import is_frozen_version_dir_name\n"
            f'X = "from {_SSOT_MODULE} import FROZEN_SDD_PATH_RE"\n'
        )
        w = _ssot_wiring(fake)
        self.assertEqual(w["imported"], set())
        self.assertNotIn("exclude_frozen_sdd_versions", w["used"])


if __name__ == "__main__":
    unittest.main()
