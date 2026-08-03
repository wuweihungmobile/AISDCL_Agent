#!/usr/bin/env python3
"""`tools/archive_defect_log.py` 的判準與保全行為回歸鎖。

🔴 本檔刻意寫成 `unittest.TestCase` 類別風格：根層四道閘門（`tools/run_root_unittests.py`
＋ pre-push ＋ 兩支 CI）走的是 **unittest discover**，pytest 函式風格的測試檔會被**整檔零收集**
（R60 Scan-C 的 C-01 就是這個病：一道「兩平台排程能力對等契約鎖」寫成 pytest 函式，
四道閘門全部收不到，等於從來沒跑過）。

鑑別力設計說明（R60 round 1 四方複審把本檔初版拆穿的三件事，逐條對應本檔的結構）：

  1. **SD-R60-01**：把 `ADL.check()` 整支換成 `return 0` 仍 10/10 綠——因為當時唯一
     碰到 `check()` 的斷言是 `assertIn(rc, (0, 1))`（rc 只可能是 0/1，恆真）。
     → 現在 `check()` 的鑑別力由 `TestCheckModeBugInjection` 承擔：把帳本家族
     **複製到 tmp**、`monkeypatch` `ADL._LEDGER`／`ADL._QUALITY_DIR`，逐項注入七種
     真實缺陷形態，每一項都斷言「注入後才出現的那一筆 problem 訊息」——比對的是
     **problem 集合差異**而非只看 rc，所以「恰好本來就紅」無法冒充鑑別力。
  2. **QA-R60-02**：`ADL.POINTER_RE` 零測試消費者，測試自寫了一份比生產窄的正則
     （只認 `立帳見本表 DEF-x`），6 個真實指針只驗到 1 個。
     → 現在一律呼叫 `ADL.POINTER_RE` 本體，並對**真實帳本家族**斷言「現居 archive_NN」
     與「立帳見主檔」兩種分支各至少命中一次（任一分支被改壞即紅）。
  3. **ARCH-R60-07／SD-R60-07／QA-R60-08**：`apply()` 的四項保全是裸 `assert`，
     `python -O` 下整組消失，而 `apply()` 會就地覆寫帳本主檔；當時的「SSOT 耦合鎖」
     是一行 `assertIs(x, x)` 恆真空斷言。
     → 現在 `TestConservationGuardsAreExplicitNotAssert` 以 AST 斷言本工具**全檔零
     `assert` 陳述**、以構造輸入逐條驗四項不變量、並在 `python -O` 子行程下重驗；
     SSOT 耦合改為 `TestGateSsotCouplingContract` 的顯式契約鎖。
  4. **ARCH-R60-02／QA-R60-01**：`--check` 的 rc 沒有任何閘門在看。
     → `TestCheckIsWiredIntoGates` 斷言 pre-push 守門迴圈與 root-infra-ci.yml 兩邊
     都真的執行 `python tools/archive_defect_log.py --check`。
  5. **Pkg-P12（載具假紅）**：本檔自己犯了「拿整份文件斷言某字串不出現」——標頭鎖以
     `read_text()[:4000]` 取樣，切片溢進逐字搬入的表格區，撞到某列**合法引用**作廢字樣的
     缺陷描述。被測行為是對的，紅的是取樣範圍；代價是帳本改寫了自己的缺陷描述來繞道。
     → 取樣改走 `_generated_header_of()`（結構邊界），紀律與機械自檢見
     `TestNoAssertionSamplesALiveDocumentWholesale`。

判準④（散文交棒偵測）的正樣本**用 R60 動工前真的被誤搬的那兩列原文**
（`DEF-101-517`／`DEF-101-526`，現居 `archive_30`）。這不是自己編一個一定會過的字串——
那兩列是舊判準（只看狀態欄）實際放行、而新判準必須攔下的真實案例，所以這條測試
如果哪天判準退化回「只看狀態欄」，它會轉紅。
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools"))

import archive_defect_log as ADL  # noqa: E402

_QUALITY = _REPO / "docs" / "06_quality"
_MAIN_LEDGER = _QUALITY / "AutoSDD_Defect_Log.md"
_ARCHIVE_30 = _QUALITY / "AutoSDD_Defect_Log_archive_30.md"
_ARCHIVE_35 = _QUALITY / "AutoSDD_Defect_Log_archive_35.md"
_TOOL_PATH = _REPO / "tools" / "archive_defect_log.py"
_PRE_PUSH = _REPO / "tools" / "git-hooks" / "pre-push"
_CI_YML = _REPO / ".github" / "workflows" / "root-infra-ci.yml"

#: 本工具透過 `import check_defect_log_crossref as gate` 取用的閘門 SSOT 名稱 → 期望型別。
#: 這些名稱多為**私有**（前綴底線），耦合本身可接受（判準只准有一份），但必須有一道
#: 顯式契約鎖：閘門把任一支改名/改型別時要**當場 fail-loud 並指路**，而不是等到某次
#: 歸檔跑到那行才 AttributeError（ARCH-R60-07 問的正是「這個耦合脆不脆」）。
#:
#: 🔴 後三支是 Pkg-P7 新登記的**切欄／欄位定位**入口。它們必須在這張表裡，理由與前七支
#: 不同也更重要：切欄邏輯本來在本工具內有一份**帶 bug 的複本**（`_CELL_SPLIT_RE` ＋
#: `_cells()`，`if c.strip()` 濾掉空欄 ⇒ `cells[-1]` 在狀態欄留空時位移到「分流去向」欄），
#: Pkg-P6 只修了閘門那一側、本工具沒被傳染修好。登記進契約 ＋ 下方
#: `TestGateSsotCouplingContract` 的兩道 AST 斷言，是「複本不得復活」的機制。
_GATE_SSOT_CONTRACT: dict[str, str] = {
    "_CLAIM_RE": "regex",
    "_ID_RE": "regex",
    "_ROW_RE": "regex",
    "_classify": "callable",
    "_CROSSREF_TARGETS": "sequence",
    "_LEDGER_WARN_BYTES": "int",
    "_LEDGER_FAIL_BYTES": "int",
    "_row_cells": "callable",
    "_table_layout": "callable",
    "row_arity_problems": "callable",
}


def _local_cell_split_sites(tree: ast.AST) -> list[str]:
    """AST 掃描「本地又長出一份切欄邏輯」的痕跡；回傳命中位置清單（空＝乾淨）。

    🔴 為何不能只靠 `_GATE_SSOT_CONTRACT` 的名稱比對：那張表只擋「用同一個名字再定義
    一次」。把複本改個名字（`_MY_PIPE_RE`／`_split_cells()`）就完全繞過，而 Pkg-P7 要防的
    正是「同一語意在第二個地方又寫一次」——名字不是重點，**形狀**才是。故本函式改認三種
    形狀，任一命中即視為複本：
      (i)  `re.compile(...)` 的樣式字面含反斜線＋豎線（`\\|`）＝表格欄分隔符的轉義寫法。
           本工具其餘正則（`ACTIVE_STATUS_RE`／`HANDOFF_PROSE_RE` 等）用的是**未轉義**的
           `|` 當 alternation，故此判準對它們零命中（實測）。
      (ii) 對「名稱以 `_RE` 結尾的已編譯正則」或 `re` 模組本身呼叫 `.split()`。
      (iii) `.split()` 的字面引數含 `|`（＝不用正則、手工切豎線那條路）。
           本工具既有的 `.split("\\n")`／`.split(",")` 不含豎線，零誤報（實測）。

    誠實劃界：它認的是**已知的三種形狀**，不是「任何手寫解析器」的通用偵測。一支從字元
    迴圈手刻的 parser 不會被抓到——那種東西在 code review 與本檔的行為測試前不隱形，
    而本鎖要擋的是「順手複製貼上一份」這個真實的復發路徑。
    """
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        first = node.args[0] if node.args else None
        literal = first.value if isinstance(first, ast.Constant) else None
        if (func.attr == "compile" and isinstance(func.value, ast.Name)
                and func.value.id == "re" and isinstance(literal, str)
                and "\\|" in literal):
            hits.append(f"{node.lineno}: re.compile({literal!r}) ＝自帶切欄正則")
        if func.attr != "split":
            continue
        recv = func.value
        if isinstance(recv, ast.Name) and (recv.id.endswith("_RE") or recv.id == "re"):
            hits.append(f"{node.lineno}: {recv.id}.split(...) ＝自己拿正則切欄")
        if isinstance(literal, str) and "|" in literal:
            hits.append(f"{node.lineno}: .split({literal!r}) ＝手工切豎線")
    return hits


# --------------------------------------------- 取樣範圍紀律的機械自檢（Pkg-P12 P12-3）
#: 讀檔方法名。這兩支的回傳值就是「整份文件」，是本紀律要盯的取樣起點。
_READ_ATTRS = ("read_text", "read_bytes")

#: 只做**字元正規化**、不收窄**區域**的字串方法。剝到它們底下才算看到真正的取樣來源
#: （`x.read_text().lower()` 跟 `x.read_text()` 的取樣範圍一樣寬）。
_CHAR_NORMALISERS = ("lower", "upper", "casefold", "strip", "lstrip", "rstrip", "expandtabs")


def _peel_to_source_expr(node: ast.expr) -> ast.expr:
    """剝掉「切片」與「字元正規化」外殼，回傳真正決定取樣範圍的那個運算式。

    剝除的都是**不收窄區域**的外殼；一旦遇到具名函式呼叫就停手，因為那可能是一支
    真正收窄範圍的抽取器（例如本檔的 `_generated_header_of()`、
    `test_find_git_bash_parity._code_only()`＝剝掉註解），不該被當成裸讀。
    """
    while True:
        if isinstance(node, ast.Subscript):
            node = node.value
            continue
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in _CHAR_NORMALISERS):
            node = node.func.value
            continue
        return node


def _is_bare_whole_file_read(node: ast.expr) -> bool:
    """該運算式是否＝「整份檔案內容」（可含寫死切片／字元正規化，但未經具名收窄）。"""
    root = _peel_to_source_expr(node)
    return (isinstance(root, ast.Call) and isinstance(root.func, ast.Attribute)
            and root.func.attr in _READ_ATTRS)


def wholefile_text_notin_sites(source: str) -> list[str]:
    """AST 掃描「對整份文件斷言某段**文字**不出現」的斷言；回傳命中位置（空＝乾淨）。

    認的形狀＝`assertNotIn(<文字 needle>, <整份檔案內容>)`，haystack 會往回解析同一個
    函式內的區域變數賦值（Pkg-P12 的原始缺陷正是
    `header = dest.read_text(...)[:4000]` ＋ `assertNotIn(stale, header)` 這種間接形態，
    只看斷言那一行是抓不到的）。

    刻意**不**認 bytes needle：`assertNotIn(b"\\r", raw)` 是位元組級不變量（帳本不可能
    「合法地」含 CR），不受「文件合法引用該字樣」影響，本檔第 ~1300 行就有一處。

    誠實劃界（做不到的部分，別把本掃描器當完整覆蓋）：
      1. 只解析**同一個函式內**、目標為單純 `Name` 的賦值。經 `setUpClass` 存成
         `cls.xxx` 再由 `self.xxx` 取用、或包一層自訂 helper 函式的間接形態抓不到——
         `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `self.adr` 就是這種形狀（本輪
         已列為跨包請求，不在本檔所有權內）。
      2. 一支「具名但其實沒收窄」的抽取器（例如 `def _narrow(t): return t`）會被誤放。
         那種東西在 code review 前不隱形，而本鎖要擋的是「順手拿整檔去比對」這個真實
         復發路徑。
    """
    tree = ast.parse(source)
    hits: list[str] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        bound: dict[str, ast.expr] = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        bound[target.id] = node.value
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "assertNotIn" or len(node.args) < 2:
                continue
            needle, hay = node.args[0], node.args[1]
            if isinstance(needle, ast.Constant) and not isinstance(needle.value, str):
                continue  # bytes／數值 needle ＝位元組級不變量，不在本紀律射程
            resolved = bound.get(hay.id, hay) if isinstance(hay, ast.Name) else hay
            if _is_bare_whole_file_read(resolved):
                seg = (ast.get_source_segment(source, resolved) or "?").replace("\n", " ")
                hits.append(f"{fn.name}:{node.lineno}: assertNotIn(<文字>, {seg[:80]})")
    return hits


def hardcoded_read_slice_sites(source: str) -> list[str]:
    """AST 掃描「檔案讀取結果被寫死切片」的位置（`p.read_text(...)[:4000]`）；空＝乾淨。

    這是 Pkg-P12 缺陷的另一半，且它自成一條錯誤：寫死上界等於默默假設「我要的區段一定
    短於 N」，而該假設**沒有任何機制保證**——本案的標頭是由 `CHECK_CRITERIA` 生成的，
    判準每多一項就長一段，愈接近 N 愈難察覺。邊界一律改用結構標記或生成端自己的分節點。
    """
    hits: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Subscript) or not isinstance(node.slice, ast.Slice):
            continue
        if not any(isinstance(b, ast.Constant) and isinstance(b.value, int)
                   for b in (node.slice.lower, node.slice.upper)):
            continue
        if _is_bare_whole_file_read(node.value):
            seg = (ast.get_source_segment(source, node) or "?").replace("\n", " ")
            hits.append(f"{node.lineno}: {seg[:80]}")
    return hits


def _layout_of(path: Path) -> tuple[int, int, int]:
    """該檔的 `(表頭欄數, ID 欄索引, 狀態欄索引)` —— 測試側同樣只走閘門 SSOT。

    🔴 本檔**曾**自帶 `_CELL` 正則與三處 `[c.strip() for c in _CELL.split(l) if c.strip()]`，
    也就是說連「證明生產碼沒有複本」的這支測試自己都握著一份同樣有 bug 的複本，於是
    `[-1]` 取狀態欄的錯誤語意被測試側原封不動地複製、還被用來當正樣本的期望值。
    Pkg-P7 把測試側的三處一併收斂掉：本檔全域零切欄實作。
    """
    layout = ADL.gate._table_layout(path.read_text(encoding="utf-8-sig"))
    if layout is None:
        raise AssertionError(f"{path.name} 查無合格表頭 — 本檔正樣本的前提已失效")
    return layout


def _status_cell(line: str, layout: tuple[int, int, int]) -> str:
    """該列的狀態欄原文（索引由表頭定位，**不是** `cells[-1]`）。"""
    return ADL.gate._row_cells(line)[layout[2]]


def _row_from(path: Path, def_id: str) -> str:
    """從指定帳本檔撈出某 ID 的表格列原文（找不到即 fail，不回 None 讓斷言誤過）。"""
    layout = _layout_of(path)
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if ADL._row_id(line, layout) == def_id:
            return line
    raise AssertionError(f"{path.name} 內找不到 {def_id} 的表格列")


def _generated_header_of(archive: Path) -> str:
    """該 archive 檔內「由 `apply()` **生成**的標頭」區段原文（不含逐字搬入的表格列）。

    🔴 **本函式存在的理由就是 Pkg-P12 那個假紅**（同族紀律見
    `TestNoAssertionSamplesALiveDocumentWholesale` 檔內類別 docstring）：原本這裡寫的是
    `dest.read_text(...)[:4000]`，兩個獨立缺陷疊在一起——

      (i) **寫死切片**：`4000` 假設「標頭一定短於 4000 bytes」，而標頭是由 `CHECK_CRITERIA`／
          `MOVE_CRITERIA` **生成**的，長度隨判準增減而變（判準每多一項，`criteria_sentence()`
          就長一段）。這個假設沒有任何機制保證，且愈接近就愈難察覺。
      (ii) **取樣範圍吃到別人的地盤**：`apply()` 會把已結列**逐字**搬進 archive 檔，所以
          4000 bytes 的切片會越過表頭、切進表格區。於是斷言「標頭不得出現『共七項』」
          撞到的是**某一列缺陷描述**——那一列（`DEF-101-584`）之所以寫著「共七項」，正是
          因為它在敘述「標頭殘留共七項」這個缺陷。帳本的職責就是記錄缺陷、必然逐字引用
          缺陷字樣，所以這是**帳本合法內容造成的假紅**，被測行為其實是對的。

    改法＝邊界由**結構**認定，而且用生產側同一份 SSOT：`apply()` 組出的
    `archive_body = header + 逐字搬入的列`，故「生成標頭」的結束點就是**第一列可解析的
    缺陷表格列**。判定一律走 `gate._table_layout()` ＋ `ADL._row_id()`（本檔全域零切欄
    實作的既有紀律），找不到邊界就 fail-loud——**不退回整檔**，否則假紅會靜默復活。
    """
    text = archive.read_text(encoding="utf-8-sig")
    layout = ADL.gate._table_layout(text)
    if layout is None:
        raise AssertionError(
            f"{archive.name} 查無合格表頭 ⇒ 認不出「生成標頭／逐字列」的邊界。"
            "拒絕退回整檔取樣（那正是 Pkg-P12 假紅的成因）"
        )
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if ADL._row_id(line, layout) is not None:
            return "\n".join(lines[:i])
    raise AssertionError(
        f"{archive.name} 內找不到任何可解析的缺陷表格列 ⇒ 邊界不成立。"
        f"`apply()` 拒絕產生空 archive，故這代表落地內容或欄位定位已變，請同步本函式"
    )


def _run_check() -> tuple[int, list[str], list[str]]:
    """跑 `ADL.check()` 並回傳 (rc, problem 訊息清單, 引述例外清單)。

    回傳清單而非只回 rc，是本檔鑑別力的關鍵：注入測試斷言的是「注入後**新增**了
    哪一筆 problem」，這樣即使基線本來就紅（例如帳本上尚有待修的失實指針），注入的
    因果關係仍然被坐實——只看 rc 會讓「本來就紅」冒充鑑別力。
    第三個回傳值是「動詞落在 code span、視為引述而未稽核」的清單：那是唯一的豁免口，
    必須能被測到它**有被列印**（豁免看得見才不是靜默豁免）。
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = ADL.check()
    lines = (out.getvalue() + err.getvalue()).splitlines()
    problems = [ln.strip()[2:].strip() for ln in lines if ln.strip().startswith("- ")]
    quoted = [ln.strip()[2:].strip() for ln in lines if ln.strip().startswith("· ")]
    return rc, problems, quoted


@contextlib.contextmanager
def _ledger_sandbox():
    """把帳本家族複製到 tmp 目錄，並把 `ADL` 的路徑常數指過去，離開時原樣還原。

    🔴 為何一定要沙箱：`check()` 的鑑別力只能靠「注入 → 必須轉紅」證明，而注入對象是
    **tracked 的帳本主檔與 archive**。直接改 repo 檔的風險本輪已實際付過代價（本輪一度
    有 agent 寫穿 15 支 tracked YAML），故一律 `copy2` 到 tmp 後 monkeypatch。
    """
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "06_quality"
        dst.mkdir(parents=True)
        for src in ADL._family_files():
            shutil.copy2(src, dst / src.name)
        old_quality, old_ledger = ADL._QUALITY_DIR, ADL._LEDGER
        ADL._QUALITY_DIR = dst
        ADL._LEDGER = dst / old_ledger.name
        try:
            yield dst
        finally:
            ADL._QUALITY_DIR, ADL._LEDGER = old_quality, old_ledger


def _append_to(path: Path, text: str) -> None:
    """bytes 層追加（不經 os.linesep 翻譯，避免注入本身順手製造 CRLF 假訊號）。"""
    path.write_bytes(path.read_bytes() + text.encode("utf-8"))


class TestActiveStatusRegexUsesAsciiBoundaries(unittest.TestCase):
    """判準② 必須用 ASCII 邊界，不是子字串包含。

    為何要鎖：歷輪 archive 標頭的散文把判準②寫成「狀態欄不含 open／routed／…任一字樣」，
    照字面（子字串）機械執行會把狀態欄含 `OpenMutexW` 的 DEF-101-504 誤判為活躍而擋下
    （R60 Scan-G G-refuter-4 實證）。文件所載判準必須就是被執行的那一個。
    """

    def test_windows_api_names_containing_open_are_not_flagged(self):
        for benign in ("OpenMutexW", "CreateFileW/OpenProcess", "reopened", "openssl"):
            with self.subTest(benign=benign):
                self.assertIsNone(
                    ADL.ACTIVE_STATUS_RE.search(benign),
                    f"{benign!r} 不應被判為活躍字樣（子字串包含式判準才會誤命中）",
                )

    def test_real_active_words_are_flagged(self):
        for active in ("open", "狀態 open 待驗", "routed 至 C 軌", "deferred@R57",
                       "open watch", "workaround-applied"):
            with self.subTest(active=active):
                self.assertIsNotNone(ADL.ACTIVE_STATUS_RE.search(active))

    def test_fixed_and_wontfix_are_not_flagged_as_active(self):
        for closed in ("fixed@R60", "wontfix", "closed-by-decision", "no_action_needed"):
            with self.subTest(closed=closed):
                self.assertIsNone(ADL.ACTIVE_STATUS_RE.search(closed))


class TestHandoffProseDetectionCatchesTheRowsR60MisArchived(unittest.TestCase):
    """判準④ 對「R60 動工前真的被誤搬的那兩列」必須命中。

    這兩列的狀態欄都是 `fixed@R59`（判準①②③ 全過），但散文裡帶著給下一輪的活交棒：
      - DEF-101-517：「**故正確的解鎖條件是：下一輪先評估這兩條較便宜的路徑**…」
      - DEF-101-526：「**R60 候選**：把「LOC tier 滿載檔 × lint 斷行」列為固定掃描檢查點…」
    舊判準只看狀態欄，兩列被靜默搬走、主檔零承接者（Scan-G G-01）。
    """

    def setUp(self):
        self.claimed = ADL._status_claimed_ids()

    #: 兩列散文裡各自實際存在的交棒語句（逐字取自 archive_30，用於證明命中不是巧合）。
    #: 刻意不斷言「命中哪一個 marker」——`re.search` 取的是行內最早出現者，
    #: 而這兩列都同時帶多個標記（517 同時有 `backlog` 與「解鎖條件」），
    #: 寫死單一預期值就是把測試綁在無關的字元位置上（本測試初版即因此誤紅）。
    _EXPECTED_PROSE = {
        "DEF-101-517": "下一輪先評估這兩條較便宜的路徑",
        "DEF-101-526": "**R60 候選**",
    }

    def test_def_517_and_526_are_flagged_as_handoff(self):
        layout = _layout_of(_ARCHIVE_30)
        for def_id, prose in self._EXPECTED_PROSE.items():
            with self.subTest(def_id=def_id):
                row = _row_from(_ARCHIVE_30, def_id)
                self.assertIn(prose, row,
                              f"{def_id} 應含該交棒語句；找不到代表 archive_30 內容已變，"
                              "本測試的正樣本前提失效，需重新挑選案例")
                verdict = ADL.classify_row(row, self.claimed, layout)
                self.assertEqual(verdict["blockers"], [],
                                 f"{def_id} 應該通過判準①②③（狀態欄是 fixed@R59）——"
                                 "若這裡紅了代表前三判準行為改變，本測試的前提失效")
                self.assertIsNotNone(
                    verdict["handoff_marker"],
                    f"{def_id} 散文帶活交棒，判準④ 必須命中；判準退化回「只看狀態欄」時本條轉紅",
                )
                # marker 必須是該列真實存在的片段（而非任意字串），否則報告會誤導讀者
                self.assertIn(verdict["handoff_marker"], row)

    def test_status_column_only_criterion_would_have_let_them_through(self):
        """反向坐實：若只看狀態欄（舊判準），這兩列確實會被放行。

        沒有這一條，上一條測試無法證明判準④ 帶來了新的鑑別力（可能只是恰好命中）。
        """
        layout = _layout_of(_ARCHIVE_30)
        for def_id in ("DEF-101-517", "DEF-101-526"):
            with self.subTest(def_id=def_id):
                row = _row_from(_ARCHIVE_30, def_id)
                status_cell = _status_cell(row, layout)
                self.assertIn(ADL.gate._classify(status_cell), ADL.CLOSED_CLASSES)
                self.assertIsNone(ADL.ACTIVE_STATUS_RE.search(status_cell))


class TestHandoffProseDetectionCoversAlternatePhrasing(unittest.TestCase):
    """判準④ 對「留待／承接者／改派」三種同語意但不同措辭的交棒用詞必須命中（SA-R63-01）。

    正樣本取自 `archive_35` 的 `DEF-101-614`（「…留待 R62」）與 `DEF-101-615`
    （「…承接者改派 R63」）——這兩列在 R63 動工前用**舊版** `HANDOFF_PROSE_RE`
    （只認「下一輪／下輪」「R\\d+候選」「解鎖條件」「deferred」「backlog」）跑
    `--apply` 時實際被放行歸檔（見 `archive_35.md` 標頭「判準④ 攔下、刻意未加
    `--ack-handoff` 而留在主檔者：（無）」——若舊正則曾攔下這兩列之一，該欄不會是空）。
    SA 複審人工覆核確認兩列本身標的皆已完成、不算誤歸檔，但正則本身確有此盲區。

    這不是自己編一個一定會過的字串：兩列是舊判準實際放行、新判準必須攔下的真實案例，
    所以本測試如果哪天判準又退化，會轉紅（同型鑑別力設計見模組 docstring 開頭一段）。
    """

    _EXPECTED_PROSE = {
        "DEF-101-614": "留待 R62",
        "DEF-101-615": "承接者改派 R63",
    }

    def test_def_614_and_615_are_flagged_as_handoff(self):
        layout = _layout_of(_ARCHIVE_35)
        for def_id, prose in self._EXPECTED_PROSE.items():
            with self.subTest(def_id=def_id):
                row = _row_from(_ARCHIVE_35, def_id)
                self.assertIn(prose, row,
                              f"{def_id} 應含該交棒語句；找不到代表 archive_35 內容已變，"
                              "本測試的正樣本前提失效，需重新挑選案例")
                verdict = ADL.classify_row(row, set(), layout)
                self.assertEqual(verdict["blockers"], [],
                                 f"{def_id} 應該通過判準①②③（狀態欄已結、未被 crossref 宣告）——"
                                 "若這裡紅了代表前三判準行為改變，本測試的前提失效")
                self.assertIsNotNone(
                    verdict["handoff_marker"],
                    f"{def_id} 散文帶「留待/承接者/改派」交棒字樣，判準④ 必須命中；"
                    "退回只認「下一輪/R候選/解鎖條件/deferred/backlog」五種舊詞面時本條轉紅",
                )
                self.assertIn(verdict["handoff_marker"], row)

    def test_old_keyword_set_would_have_missed_both(self):
        """反向坐實：R63 修復前的舊版 `HANDOFF_PROSE_RE`（五種詞面）確實會漏放這兩列。"""
        legacy_re = re.compile(
            r"R\d+\s*候選"
            r"|下一?輪"
            r"|解鎖條件"
            r"|(?<![A-Za-z0-9])deferred(?![A-Za-z0-9])"
            r"|(?<![A-Za-z0-9])backlog(?![A-Za-z0-9])"
        )
        for def_id in self._EXPECTED_PROSE:
            with self.subTest(def_id=def_id):
                row = _row_from(_ARCHIVE_35, def_id)
                self.assertIsNone(
                    legacy_re.search(row),
                    f"{def_id} 若被舊詞面集合命中，代表本測試選錯了正樣本（該列必須是"
                    "「新詞面獨有命中、舊詞面零命中」的案例）",
                )


class TestPlanNeverProposesActiveRows(unittest.TestCase):
    """--plan 不得把任何 open/routed/deferred 列列為可搬（R45 曾誤搬 3 筆 open 列）。"""

    def test_movable_rows_are_all_closed_and_have_no_handoff(self):
        p = ADL.plan()
        self.assertGreater(p["total_rows"], 0, "主檔零表格列 ⇒ 本測試的前提已失效")
        for v in p["movable"]:
            with self.subTest(def_id=v["id"]):
                self.assertIn(v["cls"], ADL.CLOSED_CLASSES)
                self.assertIsNone(v["handoff_marker"])
        self.assertEqual(p["total_rows"],
                         len(p["movable"]) + len(p["needs_ack"]) + len(p["blocked"]),
                         "三分類必須是主檔全部表格列的一個劃分（不重不漏）")

    def test_claimed_rows_may_be_movable_but_must_stay_resolvable(self):
        """判準③ 的 R68 改寫（DEF-101-676）：「被宣稱過」不再是 blocker，取而代之的義務是
        「搬走後那句宣稱仍解析得到」。

        🔴 本條取代舊的 `assertNotIn(v["id"], claimed)`。**為何舊斷言必須退場而不是放寬**：
        它把「有人在 ONBOARDING／CI workflow 裡提過這一列」當成永久不可搬，而那從來不是
        危害本身——危害是「搬走之後 `_scan_target()` 找不到它、報『帳本查無此 ID』」。
        R68 之前這兩件事被綁在一起，只因為 `gate._load_ledger_status()` **只讀主檔**；
        補上 `gate._load_archive_status()` 之後，帳本 SSOT 才真的是它一直宣稱的
        「主檔 ∪ archive 家族」，於是「被宣稱過」與「不可搬」解耦。
        實測代價：R68 動工前 11 筆已結列（16217 bytes）**只**因舊斷言而永久卡在主檔。

        本條的鑑別力＝正向驗證那個新義務真的成立，而不是刪掉檢查了事：對每一筆
        「被宣稱過 ＆ 被列為可搬」的列，斷言它在帳本家族內解析得到且狀態與宣稱一致。
        真正的端到端證明另由 `--check` 判準(8) 每次執行實跑（見
        `TestCriterion8VerifiesClaimsResolveAcrossFamily`）。
        """
        p = ADL.plan()
        claimed = ADL._status_claimed_ids()
        main = ADL.gate._load_ledger_status()
        arch = ADL.gate._load_archive_status()
        family = dict(arch)
        family.update(main)  # 主檔優先

        # (i) 核心不變量：**每一個**被宣稱過的 ID 都必須在帳本家族內解析得到。這是判準③
        #     由 blocker 改寫為事後條件之後，那個事後條件的單元層形態（端到端形態＝
        #     `--check` 判準(8)）。它不依賴「本輪剛好有沒有可搬的列」，故不會自我豁免。
        for def_id in sorted(claimed):
            with self.subTest(def_id=def_id):
                self.assertIn(
                    def_id, family,
                    f"{def_id} 被掃描目標宣稱過，卻在帳本家族（主檔 ∪ archive）解析不到 ⇒ "
                    "crossref 會報「查無此 ID」。判準③ 改寫的前提已破",
                )

        # (ii) 鑑別力前提：fallback 必須是**載重的**——至少有一個被宣稱過的 ID 只存在於
        #      archive。若全部被宣稱的 ID 都還在主檔，(i) 不靠 fallback 也會通過，這條會
        #      轉紅提醒讀者本測試當下沒有在驗 fallback（R68 落地後實測有 11 個這種 ID）。
        archived_claimed = sorted(d for d in claimed if d not in main and d in arch)
        self.assertTrue(
            archived_claimed,
            "沒有任何『被宣稱過且已歸檔』的 ID ⇒ 上面那條不需要 archive fallback 就會通過，"
            "本測試當下對 fallback 零鑑別力。若這是因為判準③ 又退回硬擋，那才是真問題",
        )

        # (iii) 若本輪確有「被宣稱過且可搬」的列，逐筆驗它搬走後仍解析得到且狀態一致。
        #       刻意寫成條件式而非前提斷言：可搬清單會隨每次 `--apply` 清空，寫成前提
        #       會讓這條測試在歸檔後自己轉紅（落地時實際踩到）。
        movable_claimed = [v for v in p["movable"] if v["id"] in claimed]
        self.assertEqual(p["movable_claimed"], len(movable_claimed),
                         "`plan()` 自報的 movable_claimed 與獨立重算不一致")
        for v in movable_claimed:
            with self.subTest(def_id=v["id"]):
                self.assertEqual(
                    family[v["id"]], v["cls"],
                    f"{v['id']} 在帳本家族解析出的狀態與 classify_row 判定不一致",
                )

    def test_status_claimed_ids_is_nonempty(self):
        """判準③ 的集合為空代表比對邏輯失效——工具必須拋例外而非靜默回空集合。

        R68 起該集合不再驅動 blocker，但仍是 `--plan` 報告與上面那條解析性測試的取樣依據，
        靜默回空會讓上面那條測試的 `movable_claimed` 變空而自我豁免（fail-open）。
        """
        self.assertGreater(len(ADL._status_claimed_ids()), 0)


class TestPlanRejectsRowsWithExternalResidencePointers(unittest.TestCase):
    """判準⑥（指針反向依賴，DEF-101-612）：`plan()` 不得把「有外部居所指針宣稱本列現居
    主檔」的列判為可搬。

    🔴 這是 DEF-101-612 的直接修復：R60 收尾包執行 `--apply` 搬走 `DEF-101-529`／
    `555`／`558` 後，家族與治理文件內共 **11 處**居所指針同時失實——判準①②③④⑤只看
    該列自身狀態，完全不看「有沒有別的檔指著這一列」，`--apply` 當時毫無鑑別力，
    要等下一次 `--check`（事後稽核）才抓得到。本類別逐項注入真實會撞到的三種形態
    （立帳見主檔／見主檔／已在某 archive），並反向坐實「正確的排除範圍」不會誤傷。

    正樣本一律用構造的合成 ID（`DEF-999-99x`），不用真實帳本現存列——現行帳本上暫無
    外部居所指針指向任何可搬候選（R66 Triage 評估的既有現況：`DEF-101-617`／`618` 查無
    此類指針），拿真實列當正樣本會隨帳本演化而失去代表性。
    """

    _NEW_ROW = ("| DEF-999-994 | 2026-07-31 | 構造輸入（DEF-101-612 回歸測試） | "
                "現象 | P3 | 已於上游 fixed 故不另修 | fixed |")

    def _seed_movable_row(self) -> None:
        """把合成列加進沙箱主檔（此刻不含任何外部指針，應可搬——後續測試各自疊加）。"""
        _append_to(ADL._LEDGER, "\n" + self._NEW_ROW + "\n")

    def test_control_row_is_movable_without_any_external_pointer(self):
        """控制組：合成列本身狀態已結、未交棒、未被 crossref 宣稱，理應可搬。

        沒有這一條，後面的「轉不可搬」斷言無法歸因於判準⑥——如果合成列本來就不可搬
        （例如格式構造錯誤），後面看到「不在 movable 裡」只是重複同一件事，零鑑別力。
        """
        with _ledger_sandbox():
            self._seed_movable_row()
            p = ADL.plan()
            self.assertIn("DEF-999-994", [v["id"] for v in p["movable"]],
                          "控制組本身就不可搬 ⇒ 後續注入測試的『轉紅』無法被正確歸因")

    def test_a_pointer_verb_form_claiming_main_ledger_residence_blocks_the_move(self):
        """注入『立帳見主檔』宣稱 → 該列必須從可搬轉為不可搬，且理由具名指出判準⑥。"""
        with _ledger_sandbox():
            self._seed_movable_row()
            _append_to(ADL._LEDGER, "\n> 立帳見主檔 `DEF-999-994`。\n")
            p = ADL.plan()
            self.assertNotIn(
                "DEF-999-994", [v["id"] for v in p["movable"]],
                "有『立帳見主檔』指針宣稱本列現居主檔，plan() 仍判為可搬 —— 判準⑥無牙，"
                "會重演 R60 的 11 處指針失實事故",
            )
            hit = next(v for v in p["blocked"] if v["id"] == "DEF-999-994")
            self.assertTrue(
                any("外部居所指針" in b and "DEF-101-612" in b for b in hit["blockers"]),
                f"blockers 未具名指出判準⑥／DEF-101-612：{hit['blockers']!r}",
            )

    def test_the_nonverb_scoped_form_also_blocks_the_move(self):
        """『見主檔』方言（非「立帳見」動詞）同樣要被判準⑥ 攔下（SA-R60R2-03 的居所方言）。"""
        with _ledger_sandbox():
            self._seed_movable_row()
            _append_to(ADL._LEDGER, "\n> 見主檔 `DEF-999-994`（尚待後續處理）。\n")
            p = ADL.plan()
            self.assertNotIn("DEF-999-994", [v["id"] for v in p["movable"]],
                             "『見主檔』方言的居所宣稱未被判準⑥ 攔下")

    def test_a_pointer_that_already_claims_an_archive_does_not_block(self):
        """反向坐實範圍窄度：宣稱已現居某 archive（非主檔）的指針與本次搬遷無關，不擋。

        沒有這一條，判準⑥ 可能被寫成「只要提到這個 ID 就攔下」的過寬版本，那會讓帳本
        永遠搬不動任何列（幾乎每一列都會被別處提到）。
        """
        with _ledger_sandbox():
            self._seed_movable_row()
            _append_to(ADL._LEDGER, "\n> 立帳見 `DEF-999-994`（現居 archive_01）。\n")
            p = ADL.plan()
            self.assertIn(
                "DEF-999-994", [v["id"] for v in p["movable"]],
                "宣稱已現居某 archive 的指針與『現居主檔』無關，不該被判準⑥ 攔下"
                "（範圍已被放寬到與 R60 事故無關的形態）",
            )

    def test_a_quoted_mention_inside_a_code_span_does_not_block(self):
        """反向坐實例外沿用 check() 既有的 (甲) code span 引述——逐字引述判準語法不算宣稱。

        取 `check()` 判準(4) 真實驗證過的同一種豁免形狀（見 `TestCheckModeBugInjection`
        的 `test_the_two_quotation_exceptions_are_exempt_but_always_printed`）：如果判準⑥
        自己另寫一套豁免邏輯而不是共用同一組基元，這裡就會先出現落差。
        """
        with _ledger_sandbox():
            self._seed_movable_row()
            _append_to(ADL._LEDGER, "\n> 範例語法：`立帳見主檔 DEF-999-994`（僅供說明）。\n")
            p = ADL.plan()
            self.assertIn(
                "DEF-999-994", [v["id"] for v in p["movable"]],
                "code span 內逐字引述判準語法被判準⑥ 誤判為真實宣稱 —— 未共用 check() 的"
                "豁免基元（`_quotation_kind`）",
            )


class TestGateSsotCouplingContract(unittest.TestCase):
    """判準來自閘門 SSOT（`check_defect_log_crossref`），不得在本工具內另寫第二份。

    🔴 這個類別取代 R60 round 1 那一行 `self.assertIs(ADL.gate._CLAIM_RE, ADL.gate._CLAIM_RE)`
    ——`x is x` 恆真，掛著「SSOT 耦合鎖」的名義卻零鑑別力（ARCH-R60-07 實證）。
    真正該鎖的是兩件事：
      (a) 本工具依賴的那 7 個閘門**私有**名稱確實存在且型別如預期 —— 這是把「私有名稱
          耦合」的脆弱性換成 fail-loud：閘門改名時本鎖當場紅並指出改了哪一支，
          而不是等某次真的跑歸檔才在半路 AttributeError（且 `--plan` 才會踩到）；
      (b) 本工具不得把這些名稱**自己再定義一份**（那就是判準分岔的起點）。
    """

    def test_gate_ssot_names_exist_with_expected_kind(self):
        for name, kind in _GATE_SSOT_CONTRACT.items():
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(ADL.gate, name),
                    f"閘門 check_defect_log_crossref 已無 `{name}`——"
                    f"tools/archive_defect_log.py 以它為判準 SSOT，請同步改名或加公開別名",
                )
                obj = getattr(ADL.gate, name)
                if kind == "regex":
                    self.assertIsInstance(obj, re.Pattern, f"`{name}` 應為已編譯正則")
                elif kind == "callable":
                    self.assertTrue(callable(obj), f"`{name}` 應為可呼叫")
                elif kind == "sequence":
                    self.assertGreater(len(list(obj)), 0, f"`{name}` 不得為空序列")
                else:
                    self.assertIsInstance(obj, int, f"`{name}` 應為 int")

    def test_tool_never_redefines_gate_ssot_names_locally(self):
        """AST 層斷言：契約內的名稱在本工具中只以 `gate.<name>` 出現，且不被本地定義。

        用 AST 而非文字掃描，是因為本工具的 docstring／註解**刻意**提到
        `_CLAIM_RE`／`_classify`／`_ID_RE` 這些名字（說明判準出處），純字串比對會誤報。
        """
        tree = ast.parse(_TOOL_PATH.read_text(encoding="utf-8"))
        names = set(_GATE_SSOT_CONTRACT)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in names:
                self.fail(f"tools/archive_defect_log.py:{node.lineno} 以裸名稱使用 "
                          f"`{node.id}`——判準必須走 `gate.{node.id}`（單一 SSOT）")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                self.fail(f"tools/archive_defect_log.py:{node.lineno} 自行定義了 "
                          f"`{node.name}`——判準會與閘門分岔")
            if isinstance(node, ast.Attribute) and node.attr in names:
                self.assertTrue(
                    isinstance(node.value, ast.Name) and node.value.id == "gate",
                    f"tools/archive_defect_log.py:{node.lineno} 的 `{node.attr}` "
                    f"不是從 `gate` 取用",
                )

    def test_cell_split_alias_is_the_gate_object_itself(self):
        """`ADL._CELL_SPLIT_RE` 必須**就是**閘門那個物件（再匯出，不是複本）。

        這個名字之所以還在，是因為 `tools/tests/test_adr_xplat001_c1c2_lock.py:278` 仍在
        消費它（該檔不在本包所有權內）。`assertIs` 而非 `assertEqual`：兩個內容相同但各自
        `re.compile()` 出來的物件會讓 `assertEqual` 通過，那就是複本悄悄復活的入口。
        """
        self.assertIs(
            ADL._CELL_SPLIT_RE, ADL.gate._CELL_SPLIT_RE,
            "`_CELL_SPLIT_RE` 不再是閘門那個物件 —— 它只准是再匯出（`= gate._CELL_SPLIT_RE`），"
            "一旦變成自己 `re.compile()` 一份就是複本復活",
        )

    def test_tool_has_no_local_cell_splitting_implementation(self):
        """AST 層斷言：本工具內零「自己切表格欄」的形狀（Pkg-P7 的核心收斂）。

        🔴 為何名稱契約不夠、必須另加形狀偵測：`test_tool_never_redefines_gate_ssot_names_locally`
        只擋「用 `_row_cells` 這個名字再定義一次」。而本工具原本的複本叫
        `_CELL_SPLIT_RE`／`_cells`——名字完全不同，名稱契約對它零訊號。Pkg-P7 要防的是
        「同一語意在第二個地方又寫一次」，所以鎖必須認形狀而不是認名字。
        """
        tree = ast.parse(_TOOL_PATH.read_text(encoding="utf-8"))
        hits = _local_cell_split_sites(tree)
        self.assertEqual(
            hits, [],
            "tools/archive_defect_log.py 又長出本地切欄實作：\n  - "
            + "\n  - ".join(hits)
            + "\n切欄／欄位定位只准有一份，一律走 `gate._row_cells()`／`gate._table_layout()`"
            "／`gate.row_arity_problems()`（WHY 見該檔 docstring 的 Pkg-P7 段：舊複本的"
            " `if c.strip()` 讓狀態欄留空時 `cells[-1]` 位移到「分流去向」欄，"
            "而本工具會把那一列**真的寫進 archive**）",
        )

    def test_the_shape_detector_actually_fires_on_a_revived_duplicate(self):
        """反向坐實上一條有牙：在**沙箱複本**裡把切欄邏輯本地重寫一份 → 必須被抓到。

        🔴 一律用沙箱複本（tempfile），**絕不**就地改 tracked 檔再改回：本 repo 已因
        「突變後還原」出過三次事故（其中一次是 `git checkout --` 把未提交工作一起抹掉）。
        本測試連 monkeypatch 都不需要——偵測器吃的是 AST，餵它一份字串複本即可。
        """
        original = _TOOL_PATH.read_text(encoding="utf-8")
        self.assertEqual(_local_cell_split_sites(ast.parse(original)), [],
                         "控制組：生產檔必須是乾淨的，否則本測試無法歸因")
        # 三種復活形態各驗一次（含「改名字繞過名稱契約」那條）
        revivals = {
            "原樣複製回來（同名）": '_CELL_SPLIT_RE = re.compile(r"(?<!\\\\)\\|")\n'
                              'def _cells(line):\n'
                              '    return [c.strip() for c in _CELL_SPLIT_RE.split(line)'
                              ' if c.strip()]\n',
            "改名繞過名稱契約": '_MY_PIPE_RE = re.compile(r"(?<!\\\\)\\|")\n'
                          'def _split_cells(line):\n'
                          '    return [c.strip() for c in _MY_PIPE_RE.split(line)]\n',
            "不用正則、手工切豎線": 'def _split_cells(line):\n'
                            '    return [c.strip() for c in line.split("|") if c.strip()]\n',
        }
        with tempfile.TemporaryDirectory() as td:
            for label, snippet in revivals.items():
                with self.subTest(revival=label):
                    copy = Path(td) / "revived.py"
                    copy.write_text(original + "\n\n" + snippet, encoding="utf-8")
                    hits = _local_cell_split_sites(ast.parse(
                        copy.read_text(encoding="utf-8")))
                    self.assertNotEqual(
                        hits, [],
                        f"複本形態「{label}」未被 _local_cell_split_sites 抓到 ⇒ "
                        "防復活鎖對這條路徑無牙",
                    )

    def test_name_contract_also_catches_a_locally_redefined_row_cells(self):
        """名稱契約與形狀偵測互補：把 `_row_cells` 本地定義一份 → 名稱鎖必須抓到。

        用沙箱複本重跑 `test_tool_never_redefines_gate_ssot_names_locally` 的同一段掃描
        邏輯（此處逐字重跑判定而非呼叫那支測試，因為 unittest 的 `fail()` 不可攔截）。
        """
        original = _TOOL_PATH.read_text(encoding="utf-8")
        names = set(_GATE_SSOT_CONTRACT)
        revived = original + "\n\ndef _row_cells(line):\n    return line.split()\n"
        offenders = [
            node.lineno for node in ast.walk(ast.parse(revived))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in names
        ]
        self.assertNotEqual(
            offenders, [],
            "把 `_row_cells` 本地定義一份竟未被名稱契約抓到 —— "
            "`_row_cells` 疑似沒被登記進 _GATE_SSOT_CONTRACT",
        )
        self.assertIn("_row_cells", names, "切欄入口必須登記進契約，否則改名/改型別無訊號")


class TestStatusColumnIsHeaderPositionedNotLastCell(unittest.TestCase):
    """Pkg-P7 P7-1／P7-3 的正樣本：狀態欄留空時**不得**位移到「分流去向」欄。

    構造輸入沿用 Pkg-P6 在閘門側用的那兩個（(a)(b)），差別是這裡套在**本工具**的
    `classify_row()`／`_row_id()` 上。修復前實測（同一組輸入、未動任何 tracked 檔）：

      (a) 狀態欄空白 ＋ 分流去向＝「已於上游 fixed 故不另修」
          → `_cells()` 只切出 6 欄、`cells[-1]` 取到「分流去向」
          → `classify_row()` 回 `cls='fixed'`、`blockers=[]` ⇒ **判為可搬**
      (b) 狀態欄空白 ＋ 分流去向＝「open 待下輪處理」
          → 回 `cls='open'`，恰好擋下但**擋的理由是錯的**（讀的是別欄）

    🔴 (a) 的危害比閘門那一側更重：閘門只是把狀態讀錯並印出來，本工具會依這個裁決
    **真的把該列寫進 archive** —— 一筆狀態欄空白（＝狀態不明）的缺陷就此靜默下葬，
    正是 R60 立本工具要消滅的那個病（`DEF-101-517`／`526` 誤搬）的同型復發。
    """

    _HEADER = "| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |"
    #: 兩列的**狀態欄刻意留空**，分流去向欄各放一個會被 `_classify` 認出的關鍵字。
    _CASES = {
        "(a) 分流去向以 fixed 收尾": ("DEF-999-101", "已於上游 fixed 故不另修"),
        "(b) 分流去向以 open 開頭": ("DEF-999-102", "open 待下輪處理"),
    }

    def _mini_ledger(self) -> tuple[str, dict[str, str], tuple[int, int, int]]:
        rows = {
            def_id: f"| {def_id} | 2026-07-29 | 構造輸入 | 現象 | P3 | {routing} |  |"
            for _, (def_id, routing) in self._CASES.items()
        }
        text = self._HEADER + "\n" + "\n".join(rows.values()) + "\n"
        layout = ADL.gate._table_layout(text)
        self.assertIsNotNone(layout, "構造的迷你帳本表頭無法被定位 ⇒ 本測試前提失效")
        return text, rows, layout

    def test_empty_status_cell_is_read_as_empty_not_as_the_routing_column(self):
        text, rows, layout = self._mini_ledger()
        ncols, id_idx, status_idx = layout
        self.assertEqual((ncols, id_idx, status_idx), (9, 1, 7),
                         "表頭定位結果與帳本家族實查形態不符 ⇒ 正樣本失去代表性")
        claimed: set[str] = {"DEF-000-000"}
        for label, (def_id, routing) in self._CASES.items():
            with self.subTest(case=label):
                row = rows[def_id]
                cells = ADL.gate._row_cells(row)
                self.assertEqual(len(cells), ncols, "構造列本身欄數就不對 ⇒ 前提失效")
                self.assertEqual(cells[status_idx], "",
                                 "狀態欄應為空字串（空欄被保留），實得非空 ⇒ 又在濾空欄")
                self.assertEqual(cells[status_idx - 1], routing,
                                 "分流去向欄應在狀態欄左邊一格")
                # ID 欄同樣由表頭定位（`cells[0]` 是首個空片段，不是 ID）
                self.assertEqual(ADL._row_id(row, layout), def_id)
                verdict = ADL.classify_row(row, claimed, layout)
                self.assertEqual(verdict["id"], def_id)
                self.assertIsNone(
                    verdict["cls"],
                    f"{label}：狀態欄是空的，`cls` 必須是 None。實得 {verdict['cls']!r}"
                    " ⇒ 讀到的是「分流去向」欄（位移復發）",
                )
                self.assertNotEqual(
                    verdict["blockers"], [],
                    f"{label}：狀態不明的列**必須**被擋下。`blockers==[]` 代表它會被"
                    "判為可搬而被真的寫進 archive（修復前 (a) 正是如此）",
                )

    def test_load_rows_finds_the_constructed_rows_via_the_header(self):
        """反向坐實 ID 欄也是表頭定位：`cells[0]` 在保留空欄後是首個空片段。"""
        text, rows, _ = self._mini_ledger()
        self.assertEqual(sorted(ADL.load_rows(text)), sorted(rows.values()))

    def test_reverting_row_cells_to_the_filtering_version_is_detected(self):
        """突變：把 `gate._row_cells` runtime monkeypatch 回「濾空欄」版 → 裁決必須改變。

        這一條把正樣本的鑑別力**釘在具體那一行**（`if c.strip()`）上：若有人主張「狀態欄
        本來就讀得對、跟濾不濾空欄無關」，本測試證明不是。

        🔴 實測校正（我原本的預期是錯的，記在此以免下輪重犯）：我原先預期突變後該列會像
        修復前一樣「被判可搬」。實際不會 —— 濾空欄使該列只切出 6 欄，於是**判準⑤ 的 arity
        守門（第二層縱深）當場攔下**。也就是說 Pkg-P7 對這個缺陷佈了兩道獨立防線：表頭定位
        ＋欄數守門，任一道單獨被破都還有另一道。故本測試斷言的是「突變被偵測到」（裁決改變、
        且改變成具名的欄位定位失效），而不是「突變後仍被擋下」那種恆真寫法。
        修復前**整條**管線（無 arity 守門）確實會判可搬，由姊妹測試
        `test_the_pre_p7_pipeline_would_have_judged_sample_a_movable` 逐步重建坐實。

        🔴 突變一律走 runtime monkeypatch（`try/finally` 復原），**不**就地改 tracked 檔。
        """
        _, rows, layout = self._mini_ledger()
        pristine = ADL.gate._row_cells

        def buggy(line):
            """修復前那一版：`if c.strip()` 把空欄整個濾掉（＝欄位索引隨空欄數浮動）。"""
            return [c.strip() for c in pristine(line) if c.strip()]

        row = rows[self._CASES["(a) 分流去向以 fixed 收尾"][0]]
        clean = ADL.classify_row(row, set(), layout)
        self.assertNotEqual(clean["blockers"], [], "控制組：狀態不明的列本來就該被擋下")
        ADL.gate._row_cells = buggy
        try:
            mutated = ADL.classify_row(row, set(), layout)
        finally:
            ADL.gate._row_cells = pristine
        self.assertEqual(
            ADL.gate._row_cells, pristine, "monkeypatch 未復原 —— 後續測試會受污染")
        self.assertNotEqual(
            clean["blockers"], mutated["blockers"],
            "把切欄換成濾空欄版之後裁決完全沒變 —— 代表本正樣本對『濾不濾空欄』零敏感，"
            "整套證明失去鑑別力",
        )
        self.assertTrue(
            any("欄位定位失效" in b for b in mutated["blockers"]),
            f"濾空欄版讓該列只切出 6 欄，必須被判準⑤ 攔下並具名說出理由，實得 "
            f"{mutated['blockers']!r}",
        )

    def test_the_pre_p7_pipeline_would_have_judged_sample_a_movable(self):
        """反向坐實正樣本的「牙」：修復前的整條管線確實會把樣本 (a) 判為**可搬**。

        逐步重建 Pkg-P7 前的三個動作（濾空欄切欄 → 取 `cells[-1]` 當狀態欄 → 無 arity
        守門），證明 `blockers` 當時為空 ⇒ 該列會被 `--apply` 真的寫進 archive。
        重建用的 cells 由 `gate._row_cells()` 的輸出**過濾**而得，刻意不另寫一份切欄實作
        （本檔全域零切欄實作，見 `_layout_of` docstring）。
        """
        _, rows, _ = self._mini_ledger()
        row = rows[self._CASES["(a) 分流去向以 fixed 收尾"][0]]
        legacy_status = [c for c in ADL.gate._row_cells(row) if c][-1]
        self.assertEqual(
            legacy_status, "已於上游 fixed 故不另修",
            "濾空欄後 `cells[-1]` 應落在「分流去向」欄（位移），實得別的欄 ⇒ 前提失效",
        )
        self.assertIn(ADL.gate._classify(legacy_status), ADL.CLOSED_CLASSES,
                      "判準① 會放行（誤讀成已結）")
        self.assertIsNone(ADL.ACTIVE_STATUS_RE.search(legacy_status),
                          "判準② 會放行（誤讀的那欄無活躍字樣）")
        self.assertIsNone(ADL.HANDOFF_PROSE_RE.search(row),
                          "判準④ 會放行（該列散文無交棒字樣）")


class TestRowArityIsAHardGateWithANamedBaseline(unittest.TestCase):
    """判準(7)：表格列欄數 == 該檔表頭欄數（Pkg-P7 P7-2）。

    檢查本體是閘門的純函式 `gate.row_arity_problems()`（本工具不寫第二份）。
    處置形狀＝**歷史列不追溯、新列硬擋**，比照 `test_adr_xplat001_c1c2_lock.py` 的
    `_BASELINE_WAIVERS`：archive 側 14 列既有異常（`DEF-101-560` 具名不修）走
    `_ARITY_BASELINE` 具名基線並逐檔列印；主檔與新建 archive 零豁免。
    """

    _BAD_ROW = ("| {def_id} | 2026-07-29 | 構造輸入 | 現象含未轉義的 | 豎線 | P3 "
                "| 合成分流 | fixed@R60（合成） |")

    def _run(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ADL.check()
        return rc, (out.getvalue() + err.getvalue())

    def test_baseline_matches_the_real_family_exactly(self):
        """具名基線必須與磁碟實測**逐檔相等**（多一筆＝新壞列、少一筆＝stale 未回收）。"""
        measured = {}
        for p in ADL._family_files():
            text = p.read_text(encoding="utf-8-sig")
            if ADL.gate._table_layout(text) is None:
                continue
            n = len(ADL.gate.row_arity_problems(text))
            if n:
                measured[p.name] = n
        self.assertEqual(
            measured, dict(ADL._ARITY_BASELINE),
            "_ARITY_BASELINE 與磁碟實測不符。多出來的檔／筆數＝新增的欄數異常列（請把欄內"
            "字面豎線轉義成 `\\|`，不要改大基線）；少掉的＝既有列已修好但登記沒回收（把"
            "數字改小或刪整筆）",
        )

    def test_baseline_never_covers_the_main_ledger(self):
        """主檔零豁免 —— 這是「新列硬擋」整個邊界的支點。"""
        self.assertNotIn(
            ADL._LEDGER.name, ADL._ARITY_BASELINE,
            "替主檔登記欄數豁免＝把判準(7) 的硬擋面拆掉：主檔是唯一會新增／接收表格列的檔",
        )

    def test_a_malformed_row_in_the_main_ledger_is_hard_blocked(self):
        """🔴 本輪要求的那一條：同一種壞列出現在**主檔**時必紅。"""
        with _ledger_sandbox():
            base_rc, base_out = self._run()
            self.assertEqual(base_rc, 0, f"基線應為綠，否則注入的因果不可歸屬：{base_out}")
            _append_to(ADL._LEDGER,
                       self._BAD_ROW.format(def_id="DEF-" + "999-" + "9" + "10") + "\n")
            rc, output = self._run()
        self.assertEqual(rc, 1, "主檔多一列欄數異常而 check() 仍回 0 —— 判準(7) 對主檔無牙")
        self.assertIn("實測 1 筆 > 具名基線 0 筆", output,
                      f"訊息未指出主檔零基線被突破：{output[-800:]}")
        self.assertIn(ADL._LEDGER.name, output, "訊息必須指名是哪一份檔")

    def test_a_malformed_row_in_a_brand_new_archive_is_hard_blocked(self):
        """把壞列搬進**新建** archive 一律硬擋（新檔名不在基線內＝結構上不可能被豁免）。"""
        with _ledger_sandbox():
            self.assertEqual(self._run()[0], 0, "基線應為綠")
            fake = ADL._QUALITY_DIR / "AutoSDD_Defect_Log_archive_89.md"
            header = ("| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 "
                      "| 分流去向 | 狀態 |\n|---|---|---|---|---|---|---|\n")
            fake.write_bytes(
                (header + self._BAD_ROW.format(def_id="DEF-" + "999-" + "9" + "11")
                 + "\n").encode("utf-8"))
            rc, output = self._run()
        self.assertEqual(rc, 1, "新 archive 帶欄數異常列而 check() 回 0")
        self.assertIn("archive_89", output)
        self.assertIn("實測 1 筆 > 具名基線 0 筆", output)

    def test_adding_a_row_to_a_waived_archive_is_still_caught(self):
        """具名基線**不是**整檔豁免：已登記的檔再多一列壞列仍必紅（棘輪只准往下）。"""
        victim = next(iter(ADL._ARITY_BASELINE))
        with _ledger_sandbox():
            self.assertEqual(self._run()[0], 0, "基線應為綠")
            _append_to(ADL._QUALITY_DIR / victim,
                       "\n" + self._BAD_ROW.format(def_id="DEF-" + "999-" + "9" + "12")
                       + "\n")
            rc, output = self._run()
        self.assertEqual(rc, 1, f"{victim} 再多一列壞列而 check() 回 0 —— 基線退化成整檔豁免")
        self.assertIn(victim, output)
        self.assertIn(f"實測 {ADL._ARITY_BASELINE[victim] + 1} 筆 > 具名基線", output,
                      "訊息必須指出實測數已超過登記數")
        self.assertIn("改大 _ARITY_BASELINE", output, "訊息必須明講數字只准往下改")

    def test_stale_baseline_entry_is_caught_and_names_the_shrink(self):
        """stale 自檢：登記數 > 實測數（有人修好了卻沒回收登記）→ 必紅並指名改成幾。

        豁免只准因為「還沒修」存在，不准因為「沒人記得回收」存在
        （`test_ps_engine_ssot.py::_PENDING_MIGRATION_SITES` 的判例）。
        """
        victim = next(iter(ADL._ARITY_BASELINE))
        with _ledger_sandbox():
            self.assertEqual(self._run()[0], 0, "基線應為綠")
            target = ADL._QUALITY_DIR / victim
            text = target.read_text(encoding="utf-8-sig")
            layout = ADL.gate._table_layout(text)
            fixed_lines = []
            healed = 0
            for line in text.split("\n"):
                cells = ADL.gate._row_cells(line)
                if (ADL.gate._ROW_RE.match(line) and len(cells) != layout[0]
                        and healed == 0):
                    # 把該列多出來的分隔符轉義掉（＝在沙箱裡「修好一列」）
                    fixed_lines.append(_escape_one_extra_pipe(line, layout[0]))
                    healed += 1
                    continue
                fixed_lines.append(line)
            self.assertEqual(healed, 1, "沒有找到可修的壞列 ⇒ 本測試前提失效")
            target.write_bytes("\n".join(fixed_lines).encode("utf-8"))
            rc, output = self._run()
        self.assertEqual(rc, 1, "修好一列卻沒回收登記，check() 竟回 0 —— stale 自檢無牙")
        self.assertIn("stale 自檢", output)
        self.assertIn(f"改成 {ADL._ARITY_BASELINE[victim] - 1}", output,
                      f"訊息必須指名要把數字改成幾：{output[-600:]}")

    def test_rows_with_broken_arity_never_pass_the_move_criteria(self):
        """搬遷側的另一半：欄位定位失效的列一律不判讀狀態、一律不可搬（判準⑤）。"""
        header = "| ID | 日期 | 情境 | 現象 | 嚴重度 | 分流去向 | 狀態 |"
        bad = self._BAD_ROW.format(def_id="DEF-" + "999-" + "9" + "13")
        layout = ADL.gate._table_layout(header + "\n")
        verdict = ADL.classify_row(bad, set(), layout)
        self.assertIsNone(verdict["cls"], "欄數異常的列不得被判讀狀態")
        self.assertTrue(
            any("欄位定位失效" in b for b in verdict["blockers"]),
            f"欄數異常必須是一條具名 blocker，實得 {verdict['blockers']!r}",
        )

    def test_a_file_with_rows_but_no_header_fails_loud(self):
        """有缺陷列卻查無表頭 ⇒ fail-loud（不得退回位置猜測，也不得靜默跳過）。"""
        with _ledger_sandbox():
            self.assertEqual(self._run()[0], 0, "基線應為綠")
            fake = ADL._QUALITY_DIR / "AutoSDD_Defect_Log_archive_88.md"
            fake.write_bytes(
                ("# 無表頭的 archive（沙箱）\n\n"
                 "| DEF-" + "999-" + "9" + "14 | 2026-07-29 | x | y | P3 | z | fixed |\n"
                 ).encode("utf-8"))
            rc, output = self._run()
        self.assertEqual(rc, 1, "有列卻沒表頭而 check() 回 0 —— 欄位定位失去依據卻靜默放行")
        self.assertIn("卻查無合格表頭", output)
        self.assertIn("archive_88", output)

    def test_prose_only_archives_without_a_header_are_not_false_reds(self):
        """控制組：家族內**零表格列**的純散文 archive 不得因「沒有表頭」而誤紅。

        沒有這一條，上一支測試可能被寫成「凡無表頭即紅」的寬鬆版 —— 而家族實查有
        12 支零表格列的 archive，那樣會讓閘門永紅（壞的失敗模式）。
        """
        prose_only = [
            p.name for p in ADL._family_files()
            if ADL.gate._table_layout(p.read_text(encoding="utf-8-sig")) is None
        ]
        self.assertGreater(len(prose_only), 0,
                           "家族內找不到任何零表格列的純散文 archive ⇒ 本控制組前提失效")
        rc, output = self._run()
        self.assertEqual(rc, 0, f"真實家族應為綠：{output[-600:]}")
        for name in prose_only:
            self.assertNotIn(f"{name}：檔內有", output,
                             f"{name} 零表格列卻被要求表頭 ⇒ 自製誤紅")

    def test_the_named_baseline_is_printed_on_every_run(self):
        """豁免必須看得見（同 `check_pytest_baseline_sites.py` 的 `baseline-ok:` 慣例）。"""
        _, output = self._run()
        for name, n in ADL._ARITY_BASELINE.items():
            self.assertIn(f"{name}：{n} 筆表格列欄數 ≠ 表頭欄數", output,
                          f"{name} 的具名基線未被逐檔列印 ⇒ 靜默豁免口")

    def test_arity_check_body_comes_from_the_gate_not_a_local_copy(self):
        """突變：把 `gate.row_arity_problems` monkeypatch 成恆回 `[]`。

        兩件事同時被坐實：
          (a) 判準(7) 真的在消費**閘門那支純函式**——掏空它之後，注入那一列的偵測訊息必須
              消失。若本檔偷偷自己算了一份，該訊息會照舊出現，本斷言就紅。
          (b) 掏空它**不會**讓稽核靜默轉綠：具名基線的 stale 自檢會全面翻紅（登記 N 筆、
              實測 0 筆）。這是刻意的——「把檢查關掉」必須是一個吵鬧的動作。

        🔴 實測校正（原本的預期是錯的）：我原先斷言突變後 rc 應變 0。實際是 rc 仍為 1，
        因為 stale 自檢先叫起來了。恆真式地斷言「rc 仍為 1」則毫無鑑別力，故改為比對
        **problem 訊息集合的差異**。
        """
        pristine = ADL.gate.row_arity_problems
        injected = "DEF-" + "999-" + "9" + "15"
        with _ledger_sandbox():
            _append_to(ADL._LEDGER, self._BAD_ROW.format(def_id=injected) + "\n")
            rc_before, out_before = self._run()
            ADL.gate.row_arity_problems = lambda text: []
            try:
                rc_after, out_after = self._run()
            finally:
                ADL.gate.row_arity_problems = pristine
        self.assertEqual(ADL.gate.row_arity_problems, pristine, "monkeypatch 未復原")
        self.assertEqual(rc_before, 1, "注入壞列後應紅")
        marker = "實測 1 筆 > 具名基線 0 筆"
        self.assertIn(marker, out_before, "控制組：注入的壞列必須被指名")
        self.assertNotIn(
            marker, out_after,
            "掏空閘門的 `row_arity_problems` 之後，注入那列仍被偵測到 —— 代表判準(7) 沒有"
            "真的在消費它（本檔疑似另寫了一份判定）",
        )
        self.assertEqual(rc_after, 1, "掏空檢查不得讓稽核靜默轉綠")
        self.assertIn("stale 自檢", out_after,
                      "掏空檢查應讓具名基線全面 stale 而吵起來，實得無 stale 訊號")


def _escape_one_extra_pipe(line: str, want_cols: int) -> str:
    """把某列多出來的欄分隔符逐一轉義，直到欄數等於表頭欄數（測試用的「修好一列」）。

    刻意呼叫 `ADL.gate._row_cells` 判斷收斂條件，不自己數豎線 —— 連測試輔助也不留
    第二份切欄語意（Pkg-P7）。
    """
    for pos in range(len(line) - 1, 0, -1):
        if line[pos] != "|" or line[pos - 1] == "\\":
            continue
        candidate = line[:pos] + "\\|" + line[pos + 1:]
        if len(ADL.gate._row_cells(candidate)) == want_cols:
            return candidate
        line = candidate
    return line


class TestLedgerFamilyLineEndingsAreLf(unittest.TestCase):
    """帳本家族磁碟實體不得含 CR。

    `.gitattributes` 宣告 `eol=lf`，而 `Path.write_text()` 的 newline 預設為 None，
    在 Windows 上會把 LF 譯成 CRLF——R60 動工前那支臨時歸檔腳本就是這樣把整份帳本
    從 `w/lf` 變成 `w/crlf`，還讓「位元組總量守恆」自我斷言按字面重驗為假。
    本鎖掃**帳本家族全部檔案**（R60 round 1 前只掃主檔與 archive_30 兩支）。
    """

    def test_whole_ledger_family_has_no_cr(self):
        for path in ADL._family_files():
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                self.assertNotIn(b"\r", raw,
                                 f"{path.name} 含 {raw.count(bytes([13]))} 個 CR")


class TestPointerRegexIsTheProductionOne(unittest.TestCase):
    """`ADL.POINTER_RE` 本體的形態覆蓋（QA-R60-02：前一版測試自寫了一份更窄的正則）。

    合成樣本電池覆蓋四種合法形態；同時反向坐實「無 ID 散句」**不會**被 `POINTER_RE`
    命中——這正是 `check()` 必須額外用 `POINTER_VERB` 做硬要求的理由。
    """

    _CASES = [
        ("立帳見本表 DEF-101-527。", "DEF-101-527", "本表", None),
        ("立帳見主檔 DEF-101-493 與本輪 R58 交接段。", "DEF-101-493", "主檔", None),
        ("立帳見 DEF-101-460（現居 archive_26）。", "DEF-101-460", None, "archive_26"),
        ("立帳見本表 DEF-101-520（現居 archive_30）。", "DEF-101-520", "本表", "archive_30"),
        # 🔴 帳本實際慣用 markdown 強調包住 ID。本輪實測：帳本寫入 7 處
        # `立帳見本表 `DEF-101-555`` 時，只認裸 ID 的樣式把它們全部誤判為「無 ID 散句」
        # ——硬要求一旦誤報就會逼人改寫真實的、正確的指針，比漏報更糟。
        ("立帳見本表 `DEF-101-555`。", "DEF-101-555", "本表", None),
        ("立帳見主檔 **DEF-101-491**。", "DEF-101-491", "主檔", None),
        ("立帳見 `DEF-101-493`（現居 `archive_28`）。", "DEF-101-493", None, "archive_28"),
    ]

    def test_all_four_legal_forms_are_parsed(self):
        for sample, def_id, scope, archive in self._CASES:
            with self.subTest(sample=sample):
                m = ADL.POINTER_RE.search(sample)
                self.assertIsNotNone(m, f"生產正則未命中合法形態：{sample!r}")
                self.assertEqual(m.group("id"), def_id)
                self.assertEqual(m.group("scope"), scope)
                self.assertEqual(m.group("archive"), archive)

    def test_prose_without_id_is_not_a_parseable_pointer(self):
        for sample in ("立帳見本表 R57 條目。", "立帳見主檔 R57 條目。",
                       "立帳見本輪 R59 交接段"):
            with self.subTest(sample=sample):
                self.assertIsNone(
                    ADL.POINTER_RE.search(sample),
                    f"{sample!r} 不含 DEF-ID，不該被當成可稽核指針——"
                    "它必須由 check() 的 POINTER_VERB 硬要求擋下",
                )
                self.assertIn(ADL.POINTER_VERB, sample,
                              "硬要求的偵測面是 POINTER_VERB，樣本必須含該字樣才有意義")

    def test_residence_branch_hits_the_real_ledger_family(self):
        """對**真實帳本家族**斷言「（現居 archive_NN）」分支有命中，該分支被改窄即紅。

        R60 round 1 的測試自寫正則只認 `立帳見本表 DEF-x`，真實 6 個指針只驗到 1 個，
        漏掉的 5 筆全是「（現居 archive_NN）」形態——而那正是 Scan-G 反駁者 #2 抓到的
        缺陷型。故這裡刻意以真實語料當守門樣本，而不是只靠合成樣本。

        🔴 刻意**不**在此對 `立帳見主檔` 分支下同樣的語料斷言：帳本正在把該形態逐步
        統一成「（現居 archive_NN）」（本輪 round 2 已把最後幾處改完，語料歸零），
        對「正在被淘汰的形態」下語料下限＝把鎖綁在會合法消失的東西上，那是自製誤紅。
        該分支的覆蓋改由兩處承擔且都不依賴語料：`_CASES` 的合成樣本（含 `立帳見主檔
        **DEF-101-491**`）＋ `TestCheckModeBugInjection.
        test_stale_main_scope_pointer_inside_an_archive_is_caught` 的真注入（該支另以
        「R60 前的窄樣式對同一段文字不命中」反向坐實本分支確為本輪新增）。
        """
        with_archive, total = 0, 0
        for path in ADL._family_files():
            for m in ADL.POINTER_RE.finditer(path.read_text(encoding="utf-8-sig")):
                total += 1
                if m.group("archive"):
                    with_archive += 1
                self.assertRegex(m.group("id"), r"^DEF-\d+-\d+$")
        self.assertGreaterEqual(total, 6, "帳本家族的立帳指針數異常地少——樣式疑似被改窄")
        self.assertGreaterEqual(
            with_archive, 1,
            "真實帳本家族內找不到任何「（現居 archive_NN）」形態的命中——"
            "POINTER_RE 的 archive 分支疑似被改壞（QA-R60-02 的原始缺陷型）",
        )


class TestCheckModeBugInjection(unittest.TestCase):
    """`check()` 四項稽核的鑑別力 —— 逐項注入真實缺陷形態，必須各自產生對應 problem。

    🔴 這是 SD-R60-01 的直接修復：當時 `check()` 換成 `return 0` 仍全綠。本類別每一支
    測試都會在「注入前 problem 集合」與「注入後 problem 集合」之間取差集，斷言差集裡
    含有預期的那一筆 —— 所以 `check()` 被掏空（差集空）或該項稽核被移除（差集不含預期
    訊息）都會紅。
    """

    def _first_main_row(self, cls: str | None = None) -> tuple[str, str]:
        """回傳沙箱主檔第一列（可指定狀態分類）的 (原文, ID)。

        指定 `cls` 是為了讓「跨檔矛盾」那支注入有確定的落差方向：拿一列 `fixed`
        再以 `open` 寫進 archive，兩邊分類必不同。若不挑分類，rows[0] 恰好是 open
        時注入的兩邊分類相同、注入等於沒注入（本測試初版即因此假綠）。
        """
        layout = _layout_of(ADL._LEDGER)
        rows = ADL.load_rows(ADL._LEDGER.read_text(encoding="utf-8-sig"))
        self.assertGreater(len(rows), 0, "沙箱主檔零表格列——複製或解析已壞")
        for row in rows:
            if cls is None or ADL.gate._classify(_status_cell(row, layout)) == cls:
                return row, ADL._row_id(row, layout)
        raise AssertionError(f"沙箱主檔找不到狀態分類為 {cls!r} 的表格列")

    def _assert_injection_adds_problem(self, inject, expected_fragment: str) -> None:
        with _ledger_sandbox():
            base_rc, base_problems, _ = _run_check()
            inject()
            rc, problems, _ = _run_check()
            new = [p for p in problems if p not in base_problems]
            self.assertEqual(
                rc, 1,
                f"注入 {expected_fragment!r} 形態的缺陷後 check() 仍回 {rc}——該項稽核無牙"
                f"（基線 rc={base_rc}）",
            )
            self.assertTrue(
                any(expected_fragment in p for p in new),
                f"注入後未出現預期 problem（片段 {expected_fragment!r}）。"
                f"新增的 problem={new!r}",
            )

    def test_cr_in_archive_is_caught(self):
        def inject():
            target = sorted(ADL._QUALITY_DIR.glob(ADL._ARCHIVE_GLOB))[0]
            target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n", 1))
        self._assert_injection_adds_problem(inject, "磁碟實體含 CR")

    def test_duplicate_row_for_same_id_in_main_is_caught(self):
        """SD-R60-02：前一版印「N 個 ID 無重複」卻從未檢查重複，注入後 rc 仍 0。"""
        def inject():
            row, _ = self._first_main_row()
            _append_to(ADL._LEDGER, f"\n{row}\n")
        self._assert_injection_adds_problem(inject, "內出現 2 列")

    def test_cross_file_status_contradiction_is_caught(self):
        """QA-R60-01 的注入形態：同 ID 在主檔與 archive 各說各話。"""
        def inject():
            row, _ = self._first_main_row(cls="fixed")
            layout = _layout_of(ADL._LEDGER)
            cells = ADL.gate._row_cells(row)
            cells[layout[2]] = "open（注入的矛盾狀態）"   # 狀態欄由表頭定位，非 [-2] 位置猜測
            target = sorted(ADL._QUALITY_DIR.glob(ADL._ARCHIVE_GLOB))[0]
            _append_to(target, "\n" + "|".join(cells) + "\n")
        self._assert_injection_adds_problem(inject, "兩邊各說各話")

    def test_stale_pointer_to_unknown_id_is_caught(self):
        def inject():
            _append_to(ADL._LEDGER, "\n> 立帳見本表 DEF-999-999。\n")
        self._assert_injection_adds_problem(inject, "「立帳見本表 DEF-999-999」失實")

    def test_wrong_residence_annotation_is_caught(self):
        def inject():
            _, def_id = self._first_main_row()
            _append_to(ADL._LEDGER, f"\n> 立帳見 {def_id}（現居 archive_99）。\n")
        self._assert_injection_adds_problem(inject, "（現居 archive_99）」失實")

    def test_pointer_verb_without_parseable_id_is_caught(self):
        """ARCH-R60-01 ③：無 ID 散句是永久豁免口，必須被硬要求擋下。"""
        def inject():
            _append_to(ADL._LEDGER, "\n> 立帳見本表 R99 條目。\n")
        self._assert_injection_adds_problem(inject, "後未跟可解析的 DEF-ID")

    def test_the_two_quotation_exceptions_are_exempt_but_always_printed(self):
        """硬要求的兩種例外必須①真的豁免②每次都被列印。

        🔴 這兩條是本輪自己補的洞（帳本 round 2 實際寫入時當場踩到）：
          (甲) code span 引述 —— 帳本的缺陷條目本來就要逐字引述判準語法（敘述
               ARCH-R60-01 時寫 `` `立帳見主檔 DEF-101-493` ``）；
          (乙) 術語提及 —— 本 repo 慣用「立帳見」字樣 這種中文引號寫法（本工具自己的
               錯誤訊息就是），一律誤報會逼人改寫**正確的**散文。
        硬要求若把這兩種也當宣稱，帳本永遠無法談論自己的判準；但豁免必須看得見——
        否則「用反引號夾帶一個真指針」就是新的靜默規避路徑。故同時斷言兩件事：
        豁免生效（不進 problems）＋豁免現形（進逐處列印的引述清單，且標明憑哪一條）。
        """
        payload = ("> 引述語法：`立帳見主檔 DEF-999-996`、`立帳見本表 R99 條目`；"
                   "另「立帳見」字樣本身在本行只是術語提及。")
        with _ledger_sandbox():
            _, base_problems, base_quoted = _run_check()
            _append_to(ADL._LEDGER, "\n" + payload + "\n")
            _, problems, quoted = _run_check()
            new_problems = [p for p in problems if p not in base_problems]
            self.assertEqual(
                [p for p in new_problems if "999-996" in p or "R99" in p], [],
                f"例外情形被當成指針宣稱：{new_problems!r}",
            )
            new_quoted = [q for q in quoted if q not in base_quoted]
            self.assertEqual(
                len(new_quoted), 3,
                f"三處例外（2 code span ＋ 1 術語提及）應各自被列印（實得 {new_quoted!r}）"
                "——豁免若不列印就是靜默豁免口",
            )
            self.assertEqual(
                len([q for q in new_quoted if "code span 引述" in q]), 2, f"{new_quoted!r}")
            self.assertEqual(
                len([q for q in new_quoted if "術語提及" in q]), 1, f"{new_quoted!r}")

    def test_claim_shaped_prose_in_corner_brackets_is_still_caught(self):
        """反向坐實 (乙) 例外的窄度：`「立帳見本表 R99 條目」` 仍必須被擋下。round-label-ok

        沒有這一條，(乙) 可能被寫成「凡在中文引號內就跳過」的寬鬆版，而那正是原始
        缺陷（宣稱形狀的無 ID 散句）最容易復活的地方——例外只准認「引號當場閉合、
        結構上沒有 ID 槽位」的 `立帳見」`。
        """
        def inject():
            _append_to(ADL._LEDGER, "\n> 舊寫法是「立帳見本表 R99 條目」，不可再用。\n")
        self._assert_injection_adds_problem(inject, "後未跟可解析的 DEF-ID")

    def test_a_pointer_whose_id_is_backticked_is_still_audited(self):
        """帳本慣用的 `` `DEF-xxx` `` 形態仍必須被稽核居所（不得因反引號而豁免）。

        沒有這一條，上一支「code span 豁免」測試會把整個 (4) 段掏空的行為誤放行——
        真指針的 ID 常常就是包在反引號裡的（實測帳本 7 處），必須確認豁免只認**動詞**
        落在 span 內，而不是「這行有反引號就跳過」。
        """
        def inject():
            _append_to(ADL._LEDGER, "\n> 立帳見本表 `DEF-999-995`。\n")
        self._assert_injection_adds_problem(inject, "「立帳見本表 `DEF-999-995`」失實")

    def test_stale_main_scope_pointer_inside_an_archive_is_caught(self):
        """ARCH-R60-01 的原始缺陷型（兩個洞疊加，一支測試同時鎖住兩者）：

          (a) 稽核面：指針寫在 **archive 檔**內（前一版只掃主檔）；
          (b) 樣式：用 `立帳見主檔 DEF-x` 形態（前一版樣式不認）。

        反向坐實：本測試同時斷言「前一版的窄樣式對這段注入文字不命中」，所以有人把
        樣式改回 `立帳見(?:本表)?…` 時，這條會紅並指出退化點。
        """
        legacy_re = re.compile(r"立帳見(?:本表)?\s*(DEF-\d+-\d+)(?:（現居\s*(archive_\d+)）)?")
        # 刻意用「全帳本家族查無此 ID」而非搬過家的真 ID：真 ID 的居所會隨未來歸檔漂移，
        # 構造 ID 讓本測試的失實成因永遠只有一個（指針本身），不隨帳本演化而失效。
        payload = "> 立帳見主檔 DEF-999-998。"

        def inject():
            target = sorted(ADL._QUALITY_DIR.glob(ADL._ARCHIVE_GLOB))[-1]
            _append_to(target, "\n" + payload + "\n")

        self._assert_injection_adds_problem(inject, "「立帳見主檔 DEF-999-998」失實")
        self.assertIsNone(
            legacy_re.search(payload),
            f"R60 round 1 前的窄樣式竟命中 {payload!r}——本測試的反向前提失效，"
            "請重新確認 POINTER_RE 的 `主檔` 分支是否真的是本輪新增",
        )
        self.assertIsNotNone(
            ADL.POINTER_RE.search(payload),
            f"生產樣式未命中 {payload!r}——`立帳見主檔` 分支疑似被移除",
        )


class TestCheckOnRealLedgerFamily(unittest.TestCase):
    """`--check` 對**真實帳本家族**必須回 0 —— 這是接上閘門的那一條斷言。

    🔴 ARCH-R60-02／QA-R60-01：前一版是 `assertIn(rc, (0, 1))`，rc 只可能是 0/1，
    在任何情況下都不會失敗；複審實測「稽核回報 5 筆問題、rc=1，而測試套件仍全綠」。
    一支斷言不可以同時兼「rc 合法」與「rc 正確」兩件事——那兩件當時都沒守住。
    故拆成兩件事：本類別守「真帳本必須乾淨」，`TestCheckModeBugInjection` 守鑑別力。
    """

    def test_real_ledger_family_passes_the_audit(self):
        rc, problems, _ = _run_check()
        self.assertEqual(
            rc, 0,
            "帳本家族保全稽核不通過（rc=1）。這不是測試壞了，是帳本上真有失實指針／"
            "重複列／CRLF，請照 problem 訊息逐筆修帳本文字（不是修這支測試）：\n  - "
            + "\n  - ".join(problems),
        )


class TestConservationGuardsAreExplicitNotAssert(unittest.TestCase):
    """`apply()` 的資料完整性保全不得依賴 `assert`（ARCH-R60-07／SD-R60-07／QA-R60-08）。

    `apply()` 會 `write_bytes()` **就地覆寫帳本主檔**，而 CPython 在 `python -O`／
    `PYTHONOPTIMIZE=1` 下把 `assert` 整條編譯掉 —— 一個環境變數就能讓破壞性動作在
    零保全下執行。複審實測：`python -O -c "assert False, 'x'"` rc=0、
    `python -O tools/archive_defect_log.py --plan` 可正常啟動。
    """

    #: 構造輸入必須自帶表頭：`load_rows()` 自 Pkg-P7 起由**表頭欄名**定位 ID 欄，查無表頭
    #: 一律回空清單而不做位置猜測。這不是為了配合實作而放水的改動——反過來說，一份沒有
    #: 表頭的「帳本」本來就無從判斷哪一欄是 ID／狀態，舊版能跑只是因為它在猜 `cells[0]`。
    _HEADER = "| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |"
    _ROW_A = "| DEF-999-001 | 2026-07-28 | 構造輸入 | 現象 | P3 | 主控 | fixed |"
    _ROW_B = "| DEF-999-002 | 2026-07-28 | 構造輸入 | 現象 | P3 | 主控 | fixed |"

    def test_tool_source_has_zero_assert_statements(self):
        """AST 斷言全檔零 `assert` —— 有人改回裸 assert 時當場紅。"""
        tree = ast.parse(_TOOL_PATH.read_text(encoding="utf-8"))
        lines = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        self.assertEqual(
            lines, [],
            f"tools/archive_defect_log.py 第 {lines} 行有 `assert` 陳述——"
            "本工具的保全守的是就地覆寫帳本主檔的破壞性動作，`python -O` 會把 assert "
            "整條編譯掉。請改為顯式檢查 + `return 1`／`raise`",
        )

    def test_each_conservation_invariant_has_teeth(self):
        text = f"{self._HEADER}\n{self._ROW_A}\n{self._ROW_B}\n"
        new_main = f"{self._HEADER}\n{self._ROW_B}\n"
        released = len(self._ROW_A.encode("utf-8")) + 1
        # 控制組：正確搬遷（搬走 ROW_A）→ 零問題
        self.assertEqual(
            ADL.conservation_problems(text, new_main, [self._ROW_A], 1, released), [],
            "正確的搬遷輸入竟被判為不守恆——保全會誤擋所有正常歸檔",
        )
        cases = {
            "列數不守恆": (text, new_main, [self._ROW_A], 2, released),
            "找不到逐字對應": (text, new_main, ["| DEF-999-003 | x | y | z | P3 | a | fixed |"],
                          1, released),
            "該列未從主檔移除": (text, text, [self._ROW_A], 2, released),
            "位元組總量不守恆": (text, new_main, [self._ROW_A], 1, released + 1),
        }
        for fragment, args in cases.items():
            with self.subTest(invariant=fragment):
                problems = ADL.conservation_problems(*args)
                self.assertTrue(
                    any(fragment in p for p in problems),
                    f"構造出「{fragment}」的輸入，conservation_problems 卻回 {problems!r}",
                )

    def test_conservation_guards_still_fire_under_dash_O(self):
        """在 `python -O` 子行程重驗：assert 會被編譯掉，顯式檢查不會。"""
        code = (
            "import sys;"
            f"sys.path.insert(0, r'{_REPO / 'tools'}');"
            "import archive_defect_log as A;"
            "print('PROBLEMS=%d' % len(A.conservation_problems('x', 'y', [], 5, 0)))"
        )
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        proc = subprocess.run([sys.executable, "-O", "-c", code],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              env=env, cwd=str(_REPO))
        self.assertEqual(proc.returncode, 0, f"-O 子行程失敗：{proc.stderr}")
        self.assertIn(
            "PROBLEMS=1", proc.stdout,
            f"`python -O` 下保全檢查回報 0 筆問題（stdout={proc.stdout!r}）——"
            "保全疑似又寫成 assert，在 -O 下整組消失",
        )

    def test_apply_refuses_to_write_when_invariant_is_broken(self):
        """把保全函式換成「回報問題」→ `apply()` 必須回 1 且**一個檔都不寫**。

        若有人把呼叫端改回 `assert not problems`，本測試會因 AssertionError 而紅
        （非 rc==1）；若把呼叫端整段刪掉，則 dest 會被寫出而紅。

        🔴 同姊妹測試的理由：必須先在沙箱造一列可搬列。否則歸檔剛做完（可搬列為 0）時，
        `apply()` 會在**保全檢查之前**就以「無任何可搬列」回 1——rc 湊巧仍是 1，
        但紅的是 stderr 訊息比對，而且**保全那段根本沒被執行到**，測試等於零鑑別力。
        """
        with _ledger_sandbox():
            synth_id = "DEF-" + "101-" + "9" + "96"
            _append_to(
                ADL._LEDGER,
                f"| {synth_id} | 2026-07-29 | 注入組合成列 | 合成現象 | P4 "
                "| 合成分流 | fixed@R60（合成，僅存在於沙箱） |\n",
            )
            before = ADL._LEDGER.read_bytes()
            self.assertTrue(
                any(v["id"] == synth_id for v in ADL.plan()["movable"]),
                f"合成列 {synth_id} 未被判為可搬 ⇒ 保全那段不會被執行到，本測試將零鑑別力",
            )
            dest = ADL._QUALITY_DIR / "AutoSDD_Defect_Log_archive_98.md"
            original = ADL.conservation_problems
            ADL.conservation_problems = lambda *a, **k: ["注入的不守恆"]
            try:
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = ADL.apply(98, frozenset(), "測試用")
            finally:
                ADL.conservation_problems = original
            self.assertEqual(rc, 1, "保全回報問題時 apply() 必須回 1")
            self.assertIn("注入的不守恆", err.getvalue(), "問題明細必須印到 stderr")
            self.assertFalse(dest.exists(), "保全不成立時不得寫出 archive 檔")
            self.assertEqual(ADL._LEDGER.read_bytes(), before, "保全不成立時不得改動主檔")

    def test_apply_writes_lf_only_and_conserves_bytes_on_a_faithful_copy(self):
        """控制組：對忠實複本實跑一次 `apply()`，必須成功、零 CR、位元組守恆。

        沒有這一條，上一條測試無法證明保全不是「恆擋」（恆擋一樣會讓上一條綠）。

        🔴 **不依賴 live 帳本當下是否還有可搬列**：本測試初版直接對忠實複本跑 `apply()`，
        於是主控在同輪執行 `--apply --archive-num 31` 把全部 22 筆可搬列搬走之後，
        沙箱裡的可搬列變成 0、`apply()` 正確回 1「無任何可搬列，拒絕產生空 archive」，
        這兩支測試就紅了——**紅的是測試的前提，不是被測行為**。歸檔後可搬列歸零是
        帳本的正常狀態（甚至是健康狀態），測試不該把它當失敗。故改為在沙箱主檔尾端
        自行追加一列**保證四判準全過**的合成列（狀態 `fixed@R60`、無活躍字樣、
        無交棒字樣、ID 於執行期組出以避開 `test_defect_id_reference_integrity` 的
        全庫 ID 追溯鏈掃描），讓控制組在任何帳本狀態下都有可搬列。

        🔴 **必須是「多列」（round 2 SD-R60-R2-07）**：初版只合成 1 列，於是「逐列加總 vs
        只算第一列」在數學上等價——SD 溫拷突變把 `released` 改成 `len(move_lines[0])` 後
        32 支全綠、零訊號。故本控制組固定合成**兩列**並硬斷言 `len(movable) >= 2`：
        多列時「只算第一列」必然讓位元組守恆不成立。

        🔴 **守恆算式含 `added`（round 3）**：`apply()` 自判準⑤ 起會把該次歸檔的索引
        bullet 主動寫進主檔，故恆等式是「新主檔 + 釋出 == 舊主檔 + 新增」。本測試**不重算
        bullet 內容**（那會變成第二份實作），而是從落地後的索引段反查「新出現的那一條
        bullet」量它的位元組——於是本斷言同時證明**除了那一條 bullet 之外主檔沒被偷改**。
        """
        with _ledger_sandbox():
            # 合成兩列必然可搬的列（ID 執行期組出，原始碼零 ID 字面——避開全庫 ID 追溯鏈掃描）
            synth_ids = ["DEF-" + "101-" + "9" + "97", "DEF-" + "101-" + "9" + "96"]
            for n, synth_id in enumerate(synth_ids):
                _append_to(
                    ADL._LEDGER,
                    f"| {synth_id} | 2026-07-29 | 控制組合成列 {n} | 合成現象 | P4 "
                    "| 合成分流 | fixed@R60（合成，僅存在於沙箱） |\n",
                )
            before = ADL._LEDGER.read_bytes()
            index_before = ADL.ARCHIVE_INDEX_DOC().read_bytes()
            bullets_before = {
                name for _, name in ADL.index_bullet_lines(index_before.decode("utf-8"))
            }
            plan = ADL.plan()
            movable_ids = {v["id"] for v in plan["movable"]}
            self.assertEqual(
                set(synth_ids) - movable_ids, set(),
                f"合成列 {synth_ids} 未全被判為可搬 ⇒ 本控制組前提失效（判準行為已變）",
            )
            self.assertGreaterEqual(
                len(plan["movable"]), 2,
                "控制組必須搬 ≥2 列，否則「逐列加總 vs 只算第一列」等價、守恆檢查零鑑別力"
                "（SD-R60-R2-07 以溫拷突變證明過）",
            )
            dest = ADL._QUALITY_DIR / "AutoSDD_Defect_Log_archive_97.md"
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ADL.apply(97, frozenset(), "測試用")
            self.assertEqual(rc, 0, f"忠實複本上的 apply() 失敗：{err.getvalue()}")
            self.assertTrue(dest.exists())
            self.assertNotIn(b"\r", dest.read_bytes(), "archive 落地含 CR")
            after = ADL._LEDGER.read_bytes()
            self.assertNotIn(b"\r", after, "主檔落地含 CR")
            index_after = ADL.ARCHIVE_INDEX_DOC().read_bytes()
            self.assertNotIn(b"\r", index_after, "歸檔索引檔落地含 CR")
            index_text = index_after.decode("utf-8")
            new_bullet_lines = [
                line for idx, name in ADL.index_bullet_lines(index_text)
                if name not in bullets_before
                for line in [index_text.split("\n")[idx]]
            ]
            self.assertEqual(
                len(new_bullet_lines), 1,
                f"apply() 應恰好自動註冊 1 條索引 bullet，實得 {len(new_bullet_lines)} 條",
            )
            added = len(new_bullet_lines[0].encode("utf-8")) + 1  # +1 ＝行尾 \n
            moved = sum(len(v["line"].encode("utf-8")) + 1 for v in plan["movable"])
            # 🔴 R69 DEF-101-734：bullet 改寫進歸檔索引檔，主檔守恆式回到最嚴的
            # 「新主檔 + 釋出 == 舊主檔」（`added` 對主檔恆為 0）；bullet 那一側改由
            # 索引檔自己的守恆式接住。兩條式子都在，沒有無人看守的縫。
            self.assertEqual(
                len(after) + moved, len(before),
                "主檔位元組未按「新主檔 + 釋出 == 舊主檔」守恆 —— 自 R69 起 apply() "
                "不再往主檔寫任何東西，任何差額都代表主檔被偷改了",
            )
            self.assertEqual(
                len(index_after), len(index_before) + added,
                "歸檔索引檔位元組未按「新索引 == 舊索引 + bullet」守恆"
                "——差額若不等於那條 bullet 的長度，代表索引檔還被改了別的地方",
            )


class TestArchiveIndexCoverage(unittest.TestCase):
    """判準⑤ — 歸檔索引涵蓋性（R60 round 3；四方 round 2 **全部四位獨立命中**：
    ARCH-R60R2-01／SA-R60R2-01／SD-R60-R2-01／QA2-R60-03）。

    原始缺陷：R60 收輪前人工建了 `archive_31` 卻沒登記進主檔索引段，而當時的四項判準
    完全不看索引 ⇒ `--check` 照印 rc=0，主檔標題還寫死「三十檔」。**同一支閘門在同一個
    session 印的是「32 檔」**（家族檔數）——兩個數字在同一份輸出裡自相矛盾而沒人被擋。

    根因級修法不只是「加一道檢查」，而是讓 `apply()` **自己註冊**（建 archive 的程式負責
    寫索引），於是「歸檔完忘記更新索引」不再是一條靜默路徑；判準⑤ 則守人工歸檔與事後腐化。
    """

    def _run(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ADL.check()
        return rc, (out.getvalue() + err.getvalue())

    def test_deleting_a_bullet_is_caught_and_names_the_archive(self):
        """注入①：索引段刪掉一條 bullet → 必紅並**指名**是哪一支 archive。"""
        with _ledger_sandbox():
            base_rc, _ = self._run()
            self.assertEqual(base_rc, 0, "基線應為綠，否則本注入的因果不可歸屬")
            index_doc = ADL.ARCHIVE_INDEX_DOC()
            text = index_doc.read_bytes().decode("utf-8")
            bullets = ADL.index_bullet_lines(text)
            self.assertTrue(bullets, "索引段解析不到任何 bullet ⇒ 判準⑤ 的前提已失效")
            idx, victim = bullets[-1]
            lines = text.split("\n")
            del lines[idx]
            index_doc.write_bytes("\n".join(lines).encode("utf-8"))
            rc, output = self._run()
        self.assertEqual(rc, 1, "刪掉索引 bullet 後 check() 仍回 0 —— 判準⑤ 無牙")
        self.assertIn(victim, output, "失敗訊息必須指名是哪一支 archive 沒登記")
        self.assertIn("索引段查無以它為主體的 bullet", output)

    def test_an_unregistered_archive_file_on_disk_is_caught(self):
        """注入②：磁碟多一支未登記的 archive → 必紅（雙向涵蓋的另一個方向）。"""
        with _ledger_sandbox():
            base_rc, _ = self._run()
            self.assertEqual(base_rc, 0)
            fake = ADL._QUALITY_DIR / "AutoSDD_Defect_Log_archive_95.md"
            fake.write_bytes(b"# fake archive (sandbox only)\n")
            rc, output = self._run()
        self.assertEqual(rc, 1, "磁碟多一支未登記 archive 而 check() 回 0 —— 判準⑤ 單向")
        self.assertIn("archive_95", output)

    def test_a_bullet_for_a_nonexistent_archive_is_caught(self):
        """注入③：索引登記了磁碟上不存在的 archive → 必紅（防「刪檔沒刪索引」）。"""
        with _ledger_sandbox():
            index_doc = ADL.ARCHIVE_INDEX_DOC()
            text = index_doc.read_bytes().decode("utf-8")
            bullets = ADL.index_bullet_lines(text)
            lines = text.split("\n")
            ghost = "AutoSDD_Defect_Log_archive_94.md"
            lines.insert(bullets[-1][0] + 1, f"> - **`{ghost}`**（沙箱注入的幽靈索引）：無此檔。")
            index_doc.write_bytes("\n".join(lines).encode("utf-8"))
            rc, output = self._run()
        self.assertEqual(rc, 1, "索引指向不存在的 archive 而 check() 回 0")
        self.assertIn(ghost, output)

    def test_apply_auto_registers_exactly_one_bullet(self):
        """根因級修法本身要被測到：`apply()` 落地後索引必須**恰好**多一條、且判準⑤ 轉綠。

        若只加判準⑤ 而不讓 `apply()` 自動註冊，每次歸檔都會製造一次紅燈並靠人工補
        ——那正是本輪要消滅的「靠人記得」機制。
        """
        with _ledger_sandbox():
            synth_id = "DEF-" + "101-" + "9" + "93"
            _append_to(
                ADL._LEDGER,
                f"| {synth_id} | 2026-07-29 | 判準⑤ 自動註冊測試 | 合成 | P4 "
                "| 合成分流 | fixed@R60（合成，僅存在於沙箱） |\n",
            )
            before = {n for _, n in ADL.index_bullet_lines(
                ADL.ARCHIVE_INDEX_DOC().read_bytes().decode("utf-8"))}
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc_apply = ADL.apply(93, frozenset(), "判準⑤ 測試")
            self.assertEqual(rc_apply, 0, err.getvalue())
            after = {n for _, n in ADL.index_bullet_lines(
                ADL.ARCHIVE_INDEX_DOC().read_bytes().decode("utf-8"))}
            rc_check, _ = self._run()
        self.assertEqual(
            after - before, {"AutoSDD_Defect_Log_archive_93.md"},
            "apply() 未自動註冊索引 bullet（或註冊了不只一條）",
        )
        self.assertEqual(rc_check, 0, "自動註冊後判準⑤ 仍紅 ⇒ 註冊的 bullet 樣式不被解析")

    def test_apply_refuses_to_overwrite_an_existing_archive(self):
        """SD-R60-R2-08：`if dest.exists(): return 1` 這道守門原本零回歸覆蓋。

        SD 溫拷突變把它改成 `if False:` → 32 支全綠。它守的是「覆寫既有 archive 的
        史料」這個**不可逆**動作，實務觸發面是 `--apply --archive-num N` 打錯號碼重跑。
        """
        with _ledger_sandbox():
            synth_id = "DEF-" + "101-" + "9" + "92"
            _append_to(
                ADL._LEDGER,
                f"| {synth_id} | 2026-07-29 | 覆寫守門測試 | 合成 | P4 "
                "| 合成分流 | fixed@R60（合成，僅存在於沙箱） |\n",
            )
            dest = ADL._QUALITY_DIR / "AutoSDD_Defect_Log_archive_96.md"
            sentinel = "# 既有史料，不得被覆寫\n".encode()
            dest.write_bytes(sentinel)
            main_before = ADL._LEDGER.read_bytes()
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ADL.apply(96, frozenset(), "覆寫測試")
            message = out.getvalue() + err.getvalue()
            self.assertEqual(rc, 1, "目標 archive 已存在時 apply() 必須拒絕落地")
            self.assertEqual(dest.read_bytes(), sentinel, "既有 archive 的位元組被改動了")
            self.assertEqual(ADL._LEDGER.read_bytes(), main_before,
                             "拒絕落地時主檔不得被改動（含索引 bullet）")
        self.assertIn("已存在", message, "訊息必須說清楚為何拒絕")


class TestGovernanceDocsAreInThePointerAuditSurface(unittest.TestCase):
    """判準④ 稽核面擴為「帳本家族 ∪ 具名治理文件」（ARCH-R60R2-05，方案甲）。

    裁決過程刻意記在測試裡：主控初裁方案(乙)「立帳見＝家族專用語法、家族外禁用」，
    隨後**自己推翻**——(乙) 會讓治理文件裡的指針完全失去居所稽核，而 ARCH 的證據正指出
    其中一處指向的列是待 R61 承接的**活列**，一旦被搬走該句就靜默失實（與 archive_26/27
    → `DEF-101-493` 同一劇本，而 493 正是 ARCH-R60-01 的原始案例）。**把語法禁掉＝把
    偵測面一起丟掉**，故改採擴面。
    """

    def test_third_scope_dialect_is_parseable(self):
        """`立帳見缺陷帳本 DEF-x` 必須被 `POINTER_RE` 認得（round 2 前回傳空清單）。"""
        line = "> 立帳見缺陷帳本 `DEF-101-558`。"
        found = ADL.POINTER_RE.findall(line)
        self.assertEqual(len(found), 1, f"第三種 scope 方言仍逸出 POINTER_RE：{found}")
        m = ADL.POINTER_RE.search(line)
        self.assertEqual(m.group("scope"), "缺陷帳本")
        self.assertEqual(m.group("id"), "DEF-101-558")

    def test_narrowing_scope_back_to_two_makes_the_dialect_escape(self):
        """反向證明：把 scope 群組改回 `本表|主檔`，那些指針立刻逸出 ⇒ 擴面不是裝飾。"""
        narrowed = re.compile(
            ADL.POINTER_RE.pattern.replace("本表|主檔|缺陷帳本", "本表|主檔")
        )
        line = "> 立帳見缺陷帳本 `DEF-101-558`。"
        self.assertEqual(narrowed.findall(line), [],
                         "改窄後仍能解析 ⇒ 本測試的對照組無效")
        self.assertIn(ADL.POINTER_VERB, line)  # 動詞在、卻解析不到 ⇒ 舊版的零稽核狀態

    def test_governance_docs_are_in_the_audit_surface_and_family_is_unchanged(self):
        audit = {p.name for p in ADL._pointer_audit_files()}
        family = {p.name for p in ADL._family_files()}
        governance = {p.name for p in ADL._GOVERNANCE_DOCS}
        self.assertTrue(governance, "具名治理文件集合為空 ⇒ 擴面沒有生效")
        self.assertEqual(audit, family | governance)
        self.assertEqual(governance & family, set(),
                         "治理文件不得同時被當成帳本家族（居所判定會失真）")
        for p in ADL._GOVERNANCE_DOCS:
            self.assertTrue(p.exists(), f"具名治理文件不存在：{p}")

    def test_exception_kind_ding_applies_only_to_governance_docs(self):
        """例外 (丁)（未跟 DEF-ID 的提及）只對治理文件開放；家族內維持硬錯誤。

        這一條是擴面**不得順手放寬**的邊界：ARCH-R60-01 ③ 的原始缺陷就是家族內的無 ID
        散句逸出稽核，若 (丁) 也套用到家族，等於把那個缺陷重新打開。
        """
        # 契約分工（照 `_quotation_kind` docstring）：該函式只判 (甲)(乙)(丙)；(丁) 的判定
        # 必須在呼叫端，因為只有那裡才知道這一處後面有沒有跟上可解析的 DEF-ID。
        bare = "立帳見主檔 R57 條目。"
        for governance in (True, False):
            self.assertIsNone(
                ADL._quotation_kind(bare, bare.find(ADL.POINTER_VERB),
                                    governance=governance),
                "(丁) 不得被下沉到 _quotation_kind —— 那樣它就無法區分「後面有沒有 ID」，"
                "會把家族內的無 ID 散句一起豁免掉（ARCH-R60-01 ③ 的原始缺陷型）",
            )
        # (丁) 實際生效處＝`check()`：真實治理文件裡確有這種形態，必須被列為引述而非問題。
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ADL.check()
        output = out.getvalue() + err.getvalue()
        self.assertEqual(rc, 0, f"真實家族＋治理文件的稽核應為綠：{err.getvalue()[:400]}")
        self.assertIn("(丁) 治理文件內非宣稱提及", output,
                      "(丁) 從未在真實語料上生效 ⇒ 這個例外沒有客戶，應刪掉而不是留著")
        # 反向：家族內的同形態仍是硬錯誤（由 test_pointer_verb_without_parseable_id_is_caught
        # 以沙箱注入證明）。此處只斷言判定分支確實依 `governance` 分流，不重複那支注入。
        self.assertIn("governance", ADL.check.__doc__ or "check() docstring 應說明分流",
                      "判準④ 的 docstring 必須寫明治理文件與家族的分流，否則下一輪會誤放寬")

    def test_fenced_blocks_are_exempt_because_they_reproduce_real_output(self):
        text = "前言\n```\n立帳見本表 R57 條目。\n```\n後語\n"
        fenced = ADL._fenced_line_numbers(text)
        self.assertIn(3, fenced, "``` 圍籬內的行未被辨識 ⇒ 逐字保全的工具輸出會被誤報")
        self.assertNotIn(1, fenced)
        self.assertNotIn(5, fenced)


class TestCriteriaListIsASingleSsot(unittest.TestCase):
    """判準清單只准有一份（Pkg-P7 P7-4）。

    原始缺陷：round 2 主控推翻方案(乙)、刪掉 `check()` 的第(7)項「具名治理文件無家族專用
    語法的指針宣稱」反向鎖，卻**漏改 `apply()` 標頭裡手寫的「共七項」清單**。而 archive 是
    **零刪除的史料檔** ⇒ 每跑一次 `--apply` 就把那份失實宣稱複製成一份新的永久紀錄。
    這與本工具立帳要消滅的病（「宣稱一道機械檢查存在而它不存在」）完全同型，且是在同一輪、
    同一支工具身上復發。另一處殘留：`_fenced_line_numbers()` docstring 還寫著「判準⑦ 用」。

    根治＝**生成而非手寫**：成功訊息與 archive 標頭都由 `CHECK_CRITERIA`／`MOVE_CRITERIA`
    生成，「兩份說法」在結構上不可能出現。本類別再補三道鎖確認生成沒被繞開。
    """

    #: 從 `check()` docstring 抽 `(N) 標題 — …` 條目。手法比照
    #: `check_defect_log_crossref._prose_status_first_words`：程式常數綁死在散文上，
    #: 任一邊被改而另一邊沒跟就 fail-loud 並印出差異。
    _DOC_ITEM_RE = re.compile(r"^\s*\((\d+)\)\s+(\S.*?)\s+—\s", re.MULTILINE)

    @classmethod
    def _docstring_items(cls) -> list[tuple[int, str]]:
        return [(int(m.group(1)), m.group(2).strip())
                for m in cls._DOC_ITEM_RE.finditer(ADL.check.__doc__ or "")]

    @staticmethod
    def _constant_items() -> list[tuple[int, str]]:
        return [(i, label) for i, (label, _) in enumerate(ADL.CHECK_CRITERIA, 1)]

    def test_docstring_items_and_the_constant_agree_both_ways(self):
        self.assertEqual(
            self._docstring_items(), self._constant_items(),
            "`check()` docstring 的 `(N) 標題` 與 `CHECK_CRITERIA` 不一致 —— 兩邊必須同步"
            "（順序與編號也算）。這道雙向綁定就是本輪那個「刪了程式卻留著散文」缺陷的鎖",
        )

    def test_the_docstring_binding_is_not_vacuous(self):
        """反向坐實上一條有牙：從常數拿掉一項 → 綁定必須不成立（runtime monkeypatch）。"""
        pristine = ADL.CHECK_CRITERIA
        ADL.CHECK_CRITERIA = pristine[:-1]
        try:
            mismatched = self._docstring_items() == self._constant_items()
        finally:
            ADL.CHECK_CRITERIA = pristine
        self.assertIs(ADL.CHECK_CRITERIA, pristine, "monkeypatch 未復原")
        self.assertFalse(
            mismatched,
            "從 CHECK_CRITERIA 拿掉一項之後，docstring 綁定竟仍成立 —— "
            "該綁定是空斷言（例如 docstring 抽不到任何條目而兩邊都是空清單）",
        )
        self.assertGreater(len(self._docstring_items()), 1,
                           "docstring 抽出的條目數 ≤1 ⇒ 抽取樣式壞了，綁定形同虛設")

    def test_every_claimed_criterion_has_a_section_in_the_check_body(self):
        """宣稱一項就得有一段程式：`check()` 原始碼必須有對應的 `# (N)` 段落標記。

        這一面擋的是「往常數加一項、卻沒寫實作」——那就是本工具立帳要消滅的病的
        鏡像版（宣稱存在而不存在）。
        """
        source = _TOOL_PATH.read_text(encoding="utf-8")
        lines = source.splitlines()
        node = next(
            n for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.FunctionDef) and n.name == "check"
        )
        body = "\n".join(lines[node.lineno - 1:node.end_lineno])
        for i, (label, _) in enumerate(ADL.CHECK_CRITERIA, 1):
            with self.subTest(criterion=f"({i}) {label}"):
                self.assertIn(
                    f"# ({i})", body,
                    f"`CHECK_CRITERIA` 登記了第({i})項「{label}」，但 `check()` 內找不到 "
                    f"`# ({i})` 段落標記 —— 宣稱一項判準就必須有一段實作",
                )

    #: 被 round 2 推翻的第(7)項「方案(乙)」原標題。它必須**不再**出現在生成標頭裡，
    #: 而下方的鑑別力測試就是把它塞回 `CHECK_CRITERIA` 證明鎖真的會轉紅。
    _RETRACTED_LABEL = "具名治理文件無家族專用語法的指針宣稱"

    #: 生成標頭裡不得出現的作廢字樣（`_RETRACTED_LABEL` ＋ 兩處寫死項數）。
    _STALE_NEEDLES = ("共七項", "四項判準", _RETRACTED_LABEL)

    @staticmethod
    def _apply_into_sandbox(archive_num: int, synth_row_prose: str) -> tuple[str, Path]:
        """在沙箱裡追加一列合成已結列、跑一次 `apply()`，回傳 `(生成標頭原文, archive 路徑)`。

        `synth_row_prose` 落在「現象與證據」欄——那正是 Pkg-P12 假紅的震央（見
        `_generated_header_of` docstring）：帳本列的散文會被逐字搬進 archive，測試若把
        取樣範圍畫得太寬就會撞到它。
        """
        synth_id = "DEF-" + "999-" + "9" + str(archive_num)
        _append_to(
            ADL._LEDGER,
            f"| {synth_id} | 2026-07-29 | 標頭生成測試 | {synth_row_prose} | P4 "
            "| 合成分流 | fixed@R60（合成，僅存在於沙箱） |\n",
        )
        dest = ADL._QUALITY_DIR / f"AutoSDD_Defect_Log_archive_{archive_num:02d}.md"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ADL.apply(archive_num, frozenset(), "P7-4 標頭生成測試")
        if rc != 0:
            raise AssertionError(f"apply() 未成功落地（rc={rc}）：{err.getvalue()}")
        return _generated_header_of(dest), dest

    @classmethod
    def _retracted_claims_in(cls, header: str) -> list[str]:
        """生成標頭內出現的作廢字樣清單（空＝合格）—— 本類別主鎖的**判準本體**。

        🔴 刻意寫成回傳清單的純函式而不是直接斷言：主鎖、綠向硬驗收、紅向鑑別力**三支
        測試消費同一份判準**，「鎖還有沒有牙」才不會退化成另一套判準的宣稱（本輪反覆
        踩到的正是「鎖 A 的牙由鎖 B 的說法背書」）。回清單也讓紅向測試能斷言**恰好抓到
        哪一句**，而不是只看「有沒有紅」——後者會讓任何原因造成的紅都冒充鑑別力。
        """
        return [s for s in cls._STALE_NEEDLES if s in header]

    def test_a_new_archive_header_is_generated_and_carries_no_retracted_claim(self):
        """🔴 直接鎖住原始缺陷：`--apply` 新建的 archive 標頭不得再帶被推翻的宣稱。

        對忠實複本實跑一次 `apply()`，逐字檢查落地的 archive **生成標頭**：
          (a) `MOVE_CRITERIA`／`CHECK_CRITERIA` 的每一項都必須出現（＝標頭是生成的）；
          (b) 被推翻的方案(乙) 反向鎖字樣、以及寫死的「共七項」「四項判準」都不得出現。

        🔴 取樣範圍走 `_generated_header_of()`（結構邊界）而**不是**寫死切片：Pkg-P12
        前這裡是 `[:4000]`，會切進逐字搬入的表格區、撞到某列缺陷描述而假紅。該假紅由
        下方 `test_the_header_boundary_excludes_a_row_that_legitimately_quotes_it` 永久
        釘住，鎖的牙由 `test_the_retracted_claim_lock_has_teeth_on_a_header_borne_claim`
        釘住（兩面都在，才不是「為了消紅燈把鎖弄鈍」）。
        """
        with _ledger_sandbox():
            header, _dest = self._apply_into_sandbox(87, "合成")
        for label, _ in ADL.CHECK_CRITERIA:
            with self.subTest(criterion=label):
                self.assertIn(label, header,
                              f"標頭未含判準「{label}」⇒ 它不是由 CHECK_CRITERIA 生成的")
        for item in ADL.MOVE_CRITERIA:
            with self.subTest(move=item):
                self.assertIn(item, header,
                              f"標頭未含搬遷判準「{item}」⇒ 它不是由 MOVE_CRITERIA 生成的")
        self.assertEqual(
            self._retracted_claims_in(header), [],
            "新建的 archive 標頭仍帶作廢字樣（round 2 被推翻的方案(乙) 全稱／寫死的項數）。"
            "archive 是零刪除史料檔，這一份宣稱會成為永久紀錄",
        )

    def test_the_ledger_may_quote_the_retracted_wording_verbatim_without_a_false_red(self):
        """🔴 Pkg-P12 硬驗收（綠向）：帳本**逐字**寫回那句被作廢的字面，主鎖必須仍綠。

        為何這一條比「消掉紅燈」重要：修復前的取樣範圍讓**帳本永遠無法逐字保存自己要
        消滅的那句話**——Pkg-P11 撞到同一支紅時的處置就是把 `DEF-101-584` 的現象散文從
        逐字引用改成描述性寫法、逐字原文只留在證據檔（實測：活體主檔現在對「共七項」
        零命中）。那是**在資料側繞道**：讓帳本為了討好一支有 bug 的載具而扭曲自己的缺陷
        描述，與「原文逐字保全、零刪除」的史料紀律直接衝突。本測試解除該限制並釘死它。

        構造：合成列的「現象與證據」欄逐字含 `_STALE_NEEDLES` **全部三項**（含被推翻的
        方案(乙) 全稱）→ 跑 `apply()` → 該列被逐字搬進 archive → 主鎖判準（同一支
        `_retracted_claims_in()`，不是另寫一套）必須回**空清單**。

        雙向自證（缺一則本測試恆真）：
          (i)  整份 archive 全文**確實含**那三項字面 ⇒ 事故形狀真的被重現到；
          (ii) 取樣範圍**不是**被收成空字串／極短片段（否則 assertNotIn 廉價全過）。
        紅向由 `test_the_retracted_claim_lock_has_teeth_on_a_header_borne_claim` 負責。
        """
        canary = ("現象散文逐字引用作廢字樣「共七項」「四項判準」與方案(乙) 全稱"
                  f"「{self._RETRACTED_LABEL}」（重現 DEF-101-584 的假紅形態）")
        with _ledger_sandbox():
            header, dest = self._apply_into_sandbox(88, canary)
            whole = dest.read_text(encoding="utf-8")
        for stale in self._STALE_NEEDLES:
            with self.subTest(reproduced=stale[:14]):
                self.assertIn(
                    stale, whole,
                    f"合成列未把 {stale!r} 逐字搬進 archive ⇒ 本測試沒有重現到 Pkg-P12 的"
                    "事故形狀，下面的主鎖判準會變成恆真",
                )
        # 反恆真：取樣範圍必須仍涵蓋整段生成標頭（起首 ＋ 結尾的表頭分隔列），
        # 否則「主鎖綠」只是因為 header 幾乎是空的。
        self.assertIn("# AutoSDD Defect Log — Archive 88", header,
                      "取樣範圍連生成標頭的起首都不含 ⇒ 被收得太窄，主鎖恆真")
        self.assertTrue(
            header.rstrip("\n").endswith("|---|---|---|---|---|---|---|"),
            f"取樣範圍未涵蓋到生成標頭的最後一行（表頭分隔列）⇒ 標頭中後段的宣稱會逃過"
            f"主鎖。實得尾端：{header.rstrip()[-40:]!r}",
        )
        self.assertLess(
            len(header), len(whole),
            "生成標頭與整檔一樣長 ⇒ 邊界判定沒有生效（等於退回整檔取樣）",
        )
        # 主鎖判準本體：帳本逐字保存了那三句話，而主鎖仍然綠。
        self.assertEqual(
            self._retracted_claims_in(header), [],
            "帳本列逐字寫回作廢字面之後主鎖轉紅 ⇒ Pkg-P12 的假紅復活（取樣範圍又吃到"
            "逐字搬入的表格區），帳本再次無法完整記錄自己要消滅的那句話",
        )

    def test_the_retracted_claim_lock_has_teeth_on_a_header_borne_claim(self):
        """🔴 鎖**仍有牙**：讓 `apply()` 重新在標頭生成作廢宣稱 → 取樣範圍必須抓到它。

        突變手法＝runtime monkeypatch（不改 tracked 檔——本 repo 已因「就地改再改回」出過
        三次事故）：把被推翻的第(7)項塞回 `CHECK_CRITERIA`，`apply()` 的標頭經由
        `criteria_sentence()` 就會重新在**標頭**生成那句作廢宣稱。

        斷言主鎖判準**恰好**抓到那一句（不是「有紅就算」）：只證「假紅沒了」不夠，還要證
        「該紅的仍會紅」——否則把取樣範圍收成空字串同樣能讓紅燈消失，那是把鎖弄鈍。
        同時斷言另兩項字面**不在**回傳清單裡，坐實紅的來源就是注入本身。
        """
        pristine = ADL.CHECK_CRITERIA
        ADL.CHECK_CRITERIA = pristine + ((self._RETRACTED_LABEL, "round 2 已推翻的方案(乙)"),)
        try:
            with _ledger_sandbox():
                header, _dest = self._apply_into_sandbox(89, "合成")
        finally:
            ADL.CHECK_CRITERIA = pristine
        self.assertIs(ADL.CHECK_CRITERIA, pristine, "monkeypatch 未復原")
        self.assertEqual(
            self._retracted_claims_in(header), [self._RETRACTED_LABEL],
            "把作廢的第(7)項塞回 CHECK_CRITERIA 之後，主鎖判準竟未（或不只）抓到它 ⇒ "
            "鎖已無牙（取樣範圍被收得太窄，或標頭不再由常數生成）。"
            f"實得清單：{self._retracted_claims_in(header)}",
        )

    def test_no_stale_criterion_seven_reference_remains_in_the_tool(self):
        """P7-4 第二處殘留：`判準⑦` 這個指涉必須已無殘留（第(7)項現在是表格列欄數）。

        允許出現在**訂正說明**裡（那是刻意留的歷史紀錄），故判準是「不得作為現行指涉」：
        凡出現該字樣的行都必須同時帶「訂正」字樣。
        """
        offenders = [
            f"{i}: {line.strip()}"
            for i, line in enumerate(_TOOL_PATH.read_text(encoding="utf-8").splitlines(), 1)
            if "判準⑦" in line and "訂正" not in line
        ]
        self.assertEqual(
            offenders, [],
            "以下行仍以「判準⑦」指涉一個已不存在的判準（round 2 刪掉方案(乙) 反向鎖時的"
            "收斂殘留）：\n  - " + "\n  - ".join(offenders),
        )


class TestCriterion6SharesTheAuditSurfaceWithCriterion4(unittest.TestCase):
    """判準(6) 的稽核面必須與判準(4) 同一份 SSOT（Pkg-P7 P7-5）。

    原始缺陷（實證，非推測）：判準(4) round 2 已擴為 `_pointer_audit_files()`＝家族 ∪ 具名
    治理文件，判準(6) 卻仍只掃 `_family_files()` ⇒ 治理文件裡的 `見主檔 DEF-x` 形態**零檢查**。
    沙箱重現：在治理文件寫一句非 code span、非圍籬的失實 `見主檔 DEF-101-481`（該 ID 實居
    archive_27）⇒ `NONVERB_RESIDENCE_RE` 命中、`check()` 仍回 rc=0、零訊號。
    """

    def _run(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ADL.check()
        return rc, (out.getvalue() + err.getvalue())

    @contextlib.contextmanager
    def _governance_sandbox(self, body: str):
        """沙箱：家族複本 ＋ 一份**沙箱內**的治理文件（不動任何 tracked 治理文件）。"""
        with _ledger_sandbox() as quality:
            gov = quality / "SandboxGovernance.md"
            gov.write_bytes(body.encode("utf-8"))
            pristine = ADL._GOVERNANCE_DOCS
            ADL._GOVERNANCE_DOCS = (gov,)
            try:
                yield gov
            finally:
                ADL._GOVERNANCE_DOCS = pristine

    #: 取一個**真的已歸檔**的 ID 當標的：宣稱它在主檔即為失實。
    def _archived_id(self) -> tuple[str, str]:
        for p in ADL._family_files():
            if p == ADL._LEDGER:
                continue
            layout = ADL.gate._table_layout(p.read_text(encoding="utf-8-sig"))
            if layout is None:
                continue
            for row in ADL.load_rows(p.read_text(encoding="utf-8-sig")):
                def_id = ADL._row_id(row, layout)
                main_rows = ADL.load_rows(ADL._LEDGER.read_text(encoding="utf-8-sig"))
                main_layout = ADL.gate._table_layout(
                    ADL._LEDGER.read_text(encoding="utf-8-sig"))
                if def_id not in {ADL._row_id(r, main_layout) for r in main_rows}:
                    return def_id, p.name
        raise AssertionError("找不到任何「只在 archive、不在主檔」的 ID ⇒ 本測試前提失效")

    def test_a_false_residence_claim_in_a_governance_doc_is_caught(self):
        with _ledger_sandbox():
            def_id, home = self._archived_id()
        payload = f"# 沙箱治理文件\n\n本段宣稱 見主檔 {def_id} 於主檔。\n"
        with self._governance_sandbox(payload) as gov:
            rc, output = self._run()
        self.assertEqual(
            rc, 1,
            "治理文件裡的失實居所宣稱竟未被擋下 —— 判準(6) 的稽核面又縮回 _family_files()"
            f"（標的 {def_id} 實居 {home}）",
        )
        self.assertIn(gov.name, output, "訊息必須指名是哪一份檔")
        self.assertIn(f"見主檔 {def_id}", output, "訊息必須引出失實的那一句")
        self.assertIn("居所指針", output)

    def test_a_truthful_claim_and_the_two_quotation_forms_stay_green(self):
        """控制組：正確宣稱 ＋ (甲) code span ＋ (丙) 圍籬三種形態都不得誤紅。

        沒有這一條，上一支測試可以被「凡治理文件出現 `見主檔` 就報錯」滿足 —— 而現行兩份
        治理文件實測 5 處命中全落在 code span／圍籬內，那樣會讓閘門當場永紅。
        """
        with _ledger_sandbox():
            def_id, home = self._archived_id()
        archive_tag = home.replace("AutoSDD_Defect_Log_", "").replace(".md", "")
        payload = (
            "# 沙箱治理文件\n\n"
            f"正確宣稱：見 {def_id}（現居 {archive_tag}）。\n\n"
            f"(甲) code span 引述：`見主檔 {def_id}` 是舊的失實寫法。\n\n"
            "(丙) 逐字重現工具輸出：\n```\n"
            f"某某.md:7：居所指針「見主檔 {def_id}」失實 — 依「主檔」scope…\n"
            "```\n"
        )
        with self._governance_sandbox(payload) as gov:
            rc, output = self._run()
        self.assertEqual(
            rc, 0,
            f"控制組誤紅 ⇒ 擴面把正確宣稱／引述也擋了（標的 {def_id} 實居 {home}）："
            f"{output[-900:]}",
        )
        self.assertIn(f"{gov.name}:", output,
                      "引述／圍籬例外必須逐處列印（豁免看得見才不是靜默豁免口）")
        self.assertIn("判準(6) 形態", output, "判準(6) 的例外必須標明是憑哪一條被豁免")

    def test_the_two_criteria_read_from_the_same_surface_function(self):
        """AST 層：判準(6) 不得再持有第二份掃描面。

        `check()` 內對 `_family_files()` 的呼叫是 (1)(2)(3)(5)(7) 在用（家族專屬判準），
        而指針類判準一律走 `_pointer_audit_files()`。本鎖斷言後者在 `check()` 內至少被
        呼叫兩次（判準(4) 與 (6) 各一），少於兩次即代表其中一項又自己另拿了一份清單。
        """
        source = _TOOL_PATH.read_text(encoding="utf-8")
        node = next(
            n for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.FunctionDef) and n.name == "check"
        )
        calls = [
            c for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
            and c.func.id == "_pointer_audit_files"
        ]
        self.assertGreaterEqual(
            len(calls), 2,
            f"`check()` 內只呼叫 `_pointer_audit_files()` {len(calls)} 次 —— "
            "判準(4) 與 (6) 應各自從這同一份 SSOT 取稽核面（P7-5）",
        )

    def test_criterion_6_has_no_ding_exception_and_that_is_deliberate(self):
        """判準(6) **刻意不設** (丁) 對等例外 —— WHY 必須寫在 docstring 裡供下輪查閱。

        (丁) 是為了「動詞在、卻沒跟 ID」這種硬要求誤報而開的；而 `NONVERB_RESIDENCE_RE`
        沒有 ID 就根本不命中（`見` 是常用單字，對它下硬要求會把整個 repo 的中文散文都
        變成錯誤），故該例外在本項無對應物可開。
        """
        self.assertIsNone(
            ADL.NONVERB_RESIDENCE_RE.search("此事詳見主檔的說明段落，不涉任何缺陷編號。"),
            "無 DEF-ID 的「見主檔…」散句竟被 NONVERB_RESIDENCE_RE 命中 ⇒ 硬要求會誤報整個"
            " repo 的中文散文，此時才需要 (丁) 對等例外，本測試的 WHY 前提失效",
        )
        self.assertIn("(丁) 對等例外", ADL.check.__doc__ or "",
                      "判準(6) 為何不設 (丁) 必須寫在 docstring，否則下一輪會誤加")


def _an_archived_id() -> tuple[str, str]:
    """回傳一個「只在 archive、不在主檔」的 `(DEF-ID, 檔名)`——真實已歸檔標的。

    與 `TestCriterion6SharesTheAuditSurfaceWithCriterion4._archived_id()` 同語意，抽成模組
    層函式供 round 3 新增的裸「現居」測試共用；刻意**不**去改那支既有方法（本包只擴充、
    不重構鄰近既有測試）。
    """
    main_text = ADL._LEDGER.read_text(encoding="utf-8-sig")
    main_layout = ADL.gate._table_layout(main_text)
    main_ids = {ADL._row_id(r, main_layout) for r in ADL.load_rows(main_text)}
    for p in ADL._family_files():
        if p == ADL._LEDGER:
            continue
        text = p.read_text(encoding="utf-8-sig")
        layout = ADL.gate._table_layout(text)
        if layout is None:
            continue
        for row in ADL.load_rows(text):
            def_id = ADL._row_id(row, layout)
            if def_id not in main_ids:
                return def_id, p.name
    raise AssertionError("找不到任何「只在 archive、不在主檔」的 ID ⇒ 本測試前提失效")


class TestGovernanceDocsAreOneSharedSsotObject(unittest.TestCase):
    """B1 / SA-R60R3-01（BLOCKING）：具名治理文件清單全 repo 只准有一份。

    🔴 原始缺陷（主控親自複驗 CONFIRMED）：兩支工具**同名而成員不同**——
      · `check_defect_log_crossref._GOVERNANCE_DOCS` = (Evidence.md, Evidence_r3.md)  ← 體積守門
      · `archive_defect_log._GOVERNANCE_DOCS`       = (Evidence.md, Scan_Dimensions.md) ← 指針稽核
    各缺對方一支。實測 `r3 in _pointer_audit_files()` 為 **False** ⇒ 本輪新生的姊妹證據檔
    進了體積閘門卻**完全不在指針稽核面**，其中十餘處指針方言零檢查。
    這是 `DEF-101-587`「搬到另一支檔就繞過守門」的同型復發，只是繞過的是指針鎖；
    而「同名常數各寫一份」本身，就是本輪反覆立帳要消滅的複本型缺陷長在守門程式自己身上。

    修法＝單一 SSOT：閘門那側定義，本工具**再匯出同一個物件**（`= gate._GOVERNANCE_DOCS`），
    形狀沿用既有的 `_CELL_SPLIT_RE` 先例。本類別鎖住「它真的是同一個物件」＋「稽核面真的
    收得進去」＋「複本不得復活」三件事。
    """

    def test_the_two_tools_share_the_very_same_tuple_object(self):
        """`assertIs` 而非 `assertEqual`：兩份內容相同的 tuple 各寫一份也會讓 == 通過，
        而本筆缺陷的下一個形狀正是「先抄成一樣，再各自漂移」。"""
        self.assertIs(
            ADL._GOVERNANCE_DOCS, ADL.gate._GOVERNANCE_DOCS,
            "`_GOVERNANCE_DOCS` 不再是閘門那個物件 —— 它只准是再匯出"
            "（`= gate._GOVERNANCE_DOCS`）。一旦本工具自己列一份 Path tuple，"
            "SA-R60R3-01 的「同名而成員不同」就會原地復活",
        )

    def test_the_tool_source_does_not_build_its_own_governance_tuple(self):
        """AST 層：本工具對 `_GOVERNANCE_DOCS` 的唯一賦值必須是 `gate.<同名>`。

        名稱契約（`_GATE_SSOT_CONTRACT`）擋的是「用同一個名字再定義一次」；本鎖擋的是
        「用同一個名字賦一個**自己組出來的值**」——後者才是缺陷當時的實際形狀
        （右邊是一串 `_REPO_ROOT / ... ` 的 Path 字面）。
        """
        tree = ast.parse(_TOOL_PATH.read_text(encoding="utf-8"))
        assigns = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "_GOVERNANCE_DOCS"
                    for t in n.targets)
        ]
        self.assertEqual(len(assigns), 1,
                         f"本工具對 `_GOVERNANCE_DOCS` 賦值 {len(assigns)} 次，只准一次（再匯出）")
        value = assigns[0].value
        self.assertTrue(
            isinstance(value, ast.Attribute) and value.attr == "_GOVERNANCE_DOCS"
            and isinstance(value.value, ast.Name) and value.value.id == "gate",
            f"tools/archive_defect_log.py:{assigns[0].lineno} 的 `_GOVERNANCE_DOCS` 不是"
            "從 `gate` 再匯出 —— 自己組一份清單就是 SA-R60R3-01 的原始形狀",
        )

    def test_the_sibling_evidence_file_is_now_in_both_surfaces(self):
        """回歸鎖：本輪新生的姊妹證據檔必須**同時**在體積守門與指針稽核面內。

        缺陷當時 `r3 in _pointer_audit_files()` 為 False（主控實測），
        而 `Scan_Dimensions.md` 則反向缺席於體積守門的涵蓋面。兩個方向各鎖一次。
        """
        audit = {p.name for p in ADL._pointer_audit_files()}
        sized = {p.name for p in ADL.gate._GOVERNANCE_DOCS}
        for name in ("CrossPlatform_R60_Fix_Evidence_r3.md",
                     "CrossPlatform_Scan_Dimensions.md"):
            with self.subTest(doc=name):
                self.assertIn(name, audit, f"{name} 不在指針稽核面 ⇒ 其中的指針方言零檢查")
                self.assertIn(name, sized, f"{name} 不在體積守門涵蓋面 ⇒ 可無聲長過 Read 上限")

    def test_an_unregistered_sibling_escapes_the_pointer_audit_entirely(self):
        """🔴 紅綠實測：把稽核面縮回「漏收姊妹檔」的形狀 → 失實宣稱零訊號；收進來 → 轉紅。

        這一支同時是**缺陷重現**與**修復驗收**：注入的內容一字不改，只切換稽核面。
        全程在沙箱複本上進行，不動任何 tracked 治理文件。
        """
        with _ledger_sandbox() as quality:
            def_id, home = _an_archived_id()
            registered = quality / "SandboxGovernance.md"
            registered.write_bytes("# 已登記的治理文件\n\n（無指針）\n".encode())
            sibling = quality / "SandboxGovernance_r3.md"
            sibling.write_bytes(
                f"# 姊妹治理文件\n\n本段宣稱 見主檔 {def_id} 於主檔。\n".encode()
            )
            pristine = ADL._GOVERNANCE_DOCS
            try:
                # 控制組＝缺陷當時的形狀：姊妹檔沒被收進稽核面。
                ADL._GOVERNANCE_DOCS = (registered,)
                rc_before, problems_before, _ = _run_check()
                # 修復後的形狀：單一 SSOT 把姊妹檔一起收進來。
                ADL._GOVERNANCE_DOCS = (registered, sibling)
                rc_after, problems_after, _ = _run_check()
            finally:
                ADL._GOVERNANCE_DOCS = pristine
        self.assertIs(ADL._GOVERNANCE_DOCS, pristine, "monkeypatch 未復原")
        self.assertEqual(
            rc_before, 0,
            f"控制組（姊妹檔未收進稽核面）竟已轉紅 ⇒ 紅的來源不是注入本身，"
            f"本測試無鑑別力。problems={problems_before[:3]}",
        )
        self.assertEqual(
            rc_after, 1,
            f"姊妹檔收進稽核面後仍未擋下失實宣稱（標的 {def_id} 實居 {home}）⇒ "
            f"擴面沒有生效。problems={problems_after[:3]}",
        )
        new = [p for p in problems_after if p not in problems_before]
        self.assertTrue(
            any(sibling.name in p and f"見主檔 {def_id}" in p for p in new),
            f"轉紅了，但沒有逐字指出是姊妹檔裡的那一句 ⇒ 訊息不可行動。新增 problem={new!r}",
        )


class TestBareResidenceTokenHasAHardRequirement(unittest.TestCase):
    """B3 / SA-R60R3-05：裸「現居 archive_NN」的第三種方言必須有對等硬要求。

    🔴 結構論證（SA 完整方言普查）：`立帳見` 有 `POINTER_VERB` 硬要求（動詞在、後面沒跟
    可解析 ID 即紅），但**真正承載居所語意的 token 是「現居」，而它先前沒有對等硬要求**。
    不帶 `見` 動詞的裸 `現居 archive_NN` 於是兩道正則皆不命中 ⇒ 注入失實宣稱時 rc=0、零訊號。
    磁碟現況此形態零命中（latent，非已發生），但結構上一直開著——這正是「還沒出事」與
    「不會出事」的差別，本 repo 對前者的處置一律是補鎖而不是記一筆觀察。
    """

    def test_the_gap_was_real_neither_existing_regex_matched(self):
        """控制組（缺陷前提）：兩道既有正則對裸形態確實零命中，否則本鎖無標的。"""
        # ID 用 `DEF-999-999`（本檔既有的「刻意不存在」慣例，見
        # `test_stale_pointer_to_unknown_id_is_caught`）：`DEF-101-NNN` 形態受
        # `test_defect_id_reference_integrity` 管，寫一個空號會讓那道鎖紅——實測踩到一次。
        line = "本列的完整記錄 DEF-999-999 現居 archive_99。"
        self.assertEqual(ADL.POINTER_RE.findall(line), [],
                         "POINTER_RE 竟命中裸形態 ⇒ SA-R60R3-05 的前提不成立")
        self.assertEqual(
            [m.group(0) for m in ADL.NONVERB_RESIDENCE_RE.finditer(line)], [],
            "NONVERB_RESIDENCE_RE 竟命中裸形態 ⇒ 該缺口本來就不存在，本鎖是裝飾",
        )
        self.assertTrue(ADL.BARE_RESIDENCE_RE.search(line),
                        "新樣式對裸形態不命中 ⇒ 補的鎖沒有接到真正的缺口")

    def test_a_false_bare_residence_claim_is_caught(self):
        def inject():
            layout = _layout_of(ADL._LEDGER)
            row = ADL.load_rows(ADL._LEDGER.read_text(encoding="utf-8-sig"))[0]
            def_id = ADL._row_id(row, layout)
            _append_to(ADL._LEDGER, f"\n> {def_id} 的完整記錄現居 archive_99。\n")
        TestCheckModeBugInjection._assert_injection_adds_problem(
            self, inject, "居所註記「現居 archive_99」失實")

    def test_a_bare_residence_claim_without_any_id_is_caught(self):
        """對等於 `POINTER_VERB` 的硬要求：宣稱了居所卻無物可稽核＝失實時零訊號。"""
        def inject():
            _append_to(ADL._LEDGER, "\n> 本輪已結的那一批現居 archive_99。\n")
        TestCheckModeBugInjection._assert_injection_adds_problem(
            self, inject, "前方同一行")

    def test_a_truthful_bare_residence_claim_stays_green(self):
        """控制組：沒有這一條，上面兩支可以被「凡出現『現居』就報錯」滿足。"""
        with _ledger_sandbox():
            def_id, home = _an_archived_id()
            tag = home.replace("AutoSDD_Defect_Log_", "").replace(".md", "")
            base_rc, base_problems, _ = _run_check()
            _append_to(ADL._LEDGER, f"\n> {def_id} 的完整記錄現居 {tag}。\n")
            rc, problems, _ = _run_check()
        self.assertEqual(base_rc, 0, f"沙箱基線就是紅的 ⇒ 控制組無意義：{base_problems[:2]}")
        self.assertEqual(
            rc, 0,
            f"屬實的裸居所註記被誤紅（{def_id} 確實在 {home}）⇒ 硬要求下得太寬："
            f"{[p for p in problems if p not in base_problems]!r}",
        )

    def test_a_complete_form_is_not_reported_twice(self):
        """`立帳見 DEF-x（現居 archive_NN）` 由判準④ 全權管，裸形態掃描不得重複報同一處。

        少了這道「已涵蓋即跳過」，每一處合法的完整形態都會被算兩次、錯的也報兩筆 —— 那會
        讓訊息可信度下降，也讓既有的 `test_wrong_residence_annotation_is_caught` 從「恰好
        一筆」變成「兩筆」而語意漂移。
        """
        with _ledger_sandbox():
            layout = _layout_of(ADL._LEDGER)
            row = ADL.load_rows(ADL._LEDGER.read_text(encoding="utf-8-sig"))[0]
            def_id = ADL._row_id(row, layout)
            base_rc, base_problems, _ = _run_check()
            _append_to(ADL._LEDGER, f"\n> 立帳見 {def_id}（現居 archive_99）。\n")
            _rc, problems, _ = _run_check()
            new = [p for p in problems if p not in base_problems]
        self.assertEqual(base_rc, 0, "沙箱基線就是紅的 ⇒ 差集不可解讀")
        self.assertEqual(
            len(new), 1,
            f"同一處完整形態被報了 {len(new)} 筆 ⇒ 裸形態掃描沒有跳過判準④ 已涵蓋的區間："
            f"{new!r}",
        )

    def test_the_bare_form_is_latent_on_disk_not_already_present(self):
        """誠實劃界的機械化：磁碟現況此形態應為零命中。

        若哪天不再是零，代表有人真的用了這種寫法——那時本鎖會逐處驗它，而不是靜默放行。
        本測試只是把「latent」這個宣稱釘成可驗證的事實，避免它變成一句沒人核對的散文。
        """
        hits = []
        for p in ADL._pointer_audit_files():
            text = p.read_text(encoding="utf-8-sig")
            for lineno, line in enumerate(text.splitlines(), 1):
                covered = [(mm.start(), mm.end()) for mm in
                           list(ADL.POINTER_RE.finditer(line))
                           + list(ADL.NONVERB_RESIDENCE_RE.finditer(line))]
                for mm in ADL.BARE_RESIDENCE_RE.finditer(line):
                    if not any(s <= mm.start() < e for s, e in covered):
                        hits.append(f"{p.name}:{lineno} {mm.group(0)!r}")
        self.assertEqual(
            hits, [],
            "稽核面上出現了未被完整形態涵蓋的裸「現居」——本鎖會逐處驗它，"
            "請確認那幾處都跟得上可解析 DEF-ID 且居所屬實：\n  " + "\n  ".join(hits),
        )


class TestDingExceptionRequiresCornerQuotes(unittest.TestCase):
    """B4 / SA-R60R3-06：例外 (丁) 收窄為「必須落在同一行的「」或『』內」。

    🔴 **三方判斷不一致，主控裁決採納收窄**（勿改寫成「四方一致認為」）：
      · Architect：撤回「(丁) 重開了 ARCH-R60-01③」的疑慮。
      · SD：以四發注入判定 **(丁) 沒有重開** ARCH-R60-01③——它只豁免「無 ID 因而無物可
        稽核」的提及（家族內同句仍 RED、治理文件內帶真實 ID 的失實指針仍 RED）。
      · SA：判定**重開**，理由是例外開得比需要寬、形態級模糊仍在。
    **事實三方一致**（治理文件內未加引號的無 ID 散句 → rc=0），分歧純在價值判斷。
    主控裁決理由：代價僅一行判準，而現存唯一 (丁) 用例本就落在「」內 ⇒ 零誤紅。
    """

    def _run_with_governance(self, body: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with _ledger_sandbox() as quality:
            gov = quality / "SandboxGovernance.md"
            gov.write_bytes(body.encode("utf-8"))
            pristine = ADL._GOVERNANCE_DOCS
            ADL._GOVERNANCE_DOCS = (gov,)
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = ADL.check()
            finally:
                ADL._GOVERNANCE_DOCS = pristine
        return rc, out.getvalue() + err.getvalue()

    #: 未加引號、非 code span、非圍籬的無 ID 散句 —— SA 注入用的正是這個形狀。
    _BARE_MENTION = "本輪的訂正把舊寫法 立帳見主檔 R57 條目 改成帶 ID 的形態。"

    def test_an_unquoted_bare_mention_in_a_governance_doc_is_now_caught(self):
        rc, output = self._run_with_governance(f"# 沙箱治理文件\n\n{self._BARE_MENTION}\n")
        self.assertEqual(
            rc, 1,
            f"未加引號的無 ID 散句仍被 (丁) 放行 ⇒ 收窄沒有落地（SA-R60R3-06）：{output[-600:]}",
        )
        self.assertIn("後未跟可解析的 DEF-ID", output)
        self.assertIn("「」或『』", output, "訊息必須告訴人怎麼改，不能只說『不行』")

    def test_the_same_mention_inside_corner_quotes_stays_exempt(self):
        """控制組：加上引號即回到 (丁)，且**每次執行都被列印**（豁免看得見）。"""
        quoted = "本輪的訂正把舊寫法「立帳見主檔 R57 條目」改成帶 ID 的形態。"
        rc, output = self._run_with_governance(f"# 沙箱治理文件\n\n{quoted}\n")
        self.assertEqual(rc, 0, f"落在「」內的提及被誤紅 ⇒ 收窄下手過重：{output[-600:]}")
        self.assertIn("(丁) 治理文件內非宣稱提及", output)
        self.assertIn("落在「」／『』內", output,
                      "(丁) 的列印必須標明是憑「引號」被豁免，而不只是『沒跟 ID』")

    def test_single_corner_quotes_are_accepted_too(self):
        """『』與「」同級：本 repo 的巢狀引號習慣（(乙) 例外當初補 `』` 是同一個理由）。"""
        rc, _ = self._run_with_governance(
            "# 沙箱治理文件\n\n巢狀引述：『立帳見主檔 R57 條目』只是舉例。\n")
        self.assertEqual(rc, 0, "『』未被 (丁) 接受 ⇒ 與 (乙) 例外的處理不對稱")

    def test_the_family_still_hard_fails_regardless_of_quotes(self):
        """🔴 收窄不得順手放寬另一邊：家族內的無 ID 散句**即使加了引號**仍是硬錯誤。

        ARCH-R60-01③ 的原始缺陷就在家族內；(丁) 從來不適用於家族，加引號也不行。
        """
        def inject():
            _append_to(ADL._LEDGER, "\n> 舊寫法「立帳見本表 R99 條目」已作廢。\n")
        TestCheckModeBugInjection._assert_injection_adds_problem(
            self, inject, "後未跟可解析的 DEF-ID")

    def test_the_sole_real_usage_is_still_exempt_zero_false_red(self):
        """主控裁決的成立前提：現存唯一 (丁) 用例本就落在「」內 ⇒ 收窄零誤紅。

        直接對**真實** repo 跑一次 `--check`：rc 必須為 0，且 (丁) 仍有客戶（否則這條
        例外就該刪掉而不是留著）。
        """
        rc, problems, quoted = _run_check()
        self.assertEqual(
            rc, 0,
            f"真實 repo 的 --check 因收窄而轉紅 ⇒ 裁決前提「零誤紅」不成立：{problems[:3]}",
        )
        self.assertTrue(
            any("(丁)" in q for q in quoted),
            "(丁) 在真實語料上已無客戶 ⇒ 這個例外應該刪掉，而不是留著當未來的豁免口",
        )

    def test_the_narrowing_records_the_dissenting_verdicts(self):
        """誠實紀律：程式註解必須留下 ARCH／SD 的相反判斷與主控裁決理由。

        本 repo 反覆踩到的是「把裁決寫成共識」——下一輪讀者會以為沒有人反對過，
        於是失去重新檢視的線索。這道鎖把那段紀錄釘在原始碼裡。
        """
        lines = _TOOL_PATH.read_text(encoding="utf-8").splitlines()
        source = "\n".join(lines)
        for needle in ("SA-R60R3-06", "主控裁決", "SD：", "Architect："):
            with self.subTest(needle=needle):
                self.assertIn(needle, source,
                              f"(丁) 收窄處未記載 {needle!r} —— 三方判斷不一致的事實必須留痕")
        # 🔴 逐行判定 ＋ 為「明文禁止該寫法」的那一行留出口，**不是** `assertNotIn(整份檔)`：
        # 後者會在本檔合法地談論這個禁令時假紅（Pkg-P12 的事故形狀，且
        # `TestNoAssertionSamplesALiveDocumentWholesale` 會當場攔下——實測它真的攔了一次）。
        offenders = [
            f"{i}: {line.strip()}"
            for i, line in enumerate(lines, 1)
            if "四方一致" in line and "不得" not in line
        ]
        self.assertEqual(
            offenders, [],
            "以下行把主控裁決寫成四方一致 —— ARCH／SD 對本筆的判定與 SA 相反：\n  - "
            + "\n  - ".join(offenders),
        )


class TestCheckIsWiredIntoGates(unittest.TestCase):
    """`--check` 的 rc 必須真的被閘門看（ARCH-R60-02 ②／QA-R60-01 (a)）。

    🔴 立此鎖的理由：`tools/` 下 7 支 `check_*.py` 全部有執行點（pre-push 守門迴圈 ＋
    root-infra-ci.yml 具名 step），唯一破例就是本輪新增的這支——它兩處出現都只在
    compat-ci 的 `paths:` 過濾器（觸發條件，不是執行 step）。`tools/tests/
    test_root_infra_parity.py` 已守「CI 與 pre-push 兩份清單互為鏡射」，但它守不到
    「兩邊同時被拿掉」，故本鎖補上「兩邊都必須有」這一面。
    """

    _INVOCATION = "tools/archive_defect_log.py --check"

    def test_pre_push_guard_loop_runs_check(self):
        text = _PRE_PUSH.read_text(encoding="utf-8")
        exec_text = "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        )
        loop = re.search(r"for guard in\s+(.*?);\s*do", exec_text, re.DOTALL)
        self.assertIsNotNone(loop, "pre-push 找不到 root-infra 守門迴圈")
        self.assertIn(
            self._INVOCATION, loop.group(1),
            "pre-push 的 root-infra 守門迴圈未執行 "
            f"`python {self._INVOCATION}`——帳本體積硬閘已在 pre-push、保全稽核不在，"
            "這個落差沒有理由（ARCH-R60-02）",
        )

    @staticmethod
    def _ci_run_scripts() -> str:
        """root-infra-ci.yml 全部 step 的 `run:` 腳本內容（不含 step 名稱、不含註解）。

        🔴 為何不能拿「非註解行全文」比對：step 的 `- name:` 本來就寫著工具名與參數，
        比對全文時把 `run:` 換成 `echo skipped`、名稱留著，本鎖仍會綠——本輪注入實測
        當場踩到（拔掉 run 之後本鎖沒轉紅，只有既有的 parity 鎖紅了）。這正是本輪
        ARCH-R60-02 的病在**新鎖自己身上**復發，故本函式只認真正會執行的那一段。
        """
        lines = _CI_YML.read_text(encoding="utf-8").splitlines()
        run_re = re.compile(r"^(?P<indent>[ \t]*)run:[ \t]*(?P<inline>.*)$")
        out: list[str] = []
        i = 0
        while i < len(lines):
            m = run_re.match(lines[i])
            if m is None or lines[i].lstrip().startswith("#"):
                i += 1
                continue
            indent = len(m.group("indent"))
            inline = m.group("inline").strip()
            if inline not in ("|", ">", "|-", ">-", "|+", ">+", ""):
                out.append(inline)
            i += 1
            while i < len(lines):  # 收該 run: 的 block scalar 內容（縮排更深的行）
                nxt = lines[i]
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                if not nxt.lstrip().startswith("#"):
                    out.append(nxt)
                i += 1
        return "\n".join(out)

    def test_root_infra_ci_has_an_executing_step(self):
        runs = self._ci_run_scripts()
        self.assertGreater(len(runs), 500, "root-infra-ci.yml 抽不到 run: 內容——抽取管線壞了")
        self.assertIn(
            self._INVOCATION, runs,
            f"root-infra-ci.yml 沒有任何 `run:` 執行 `{self._INVOCATION}`——"
            "只出現在 step 名稱或 `paths:` 觸發清單等同零接線（QA-R60-01）",
        )

    def test_bare_invocation_without_subcommand_is_an_error(self):
        """反向坐實接線形狀：少了 `--check` 就不是有效呼叫（argparse 必需互斥組）。

        沒有這一條，上面兩條可以被「把 `--check` 拿掉、只留檔名」滿足而仍全綠。
        """
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        proc = subprocess.run([sys.executable, str(_TOOL_PATH)],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              env=env, cwd=str(_REPO))
        self.assertNotEqual(proc.returncode, 0,
                            "不帶子指令的呼叫竟成功——閘門可能在跑一個什麼都不做的指令")


class TestNoAssertionSamplesALiveDocumentWholesale(unittest.TestCase):
    """🔴 取樣範圍紀律（Pkg-P12 P12-3）——本檔所有「某字串不得出現」斷言的共通約束。

    **紀律**：斷言「某字串不得出現」時，取樣範圍必須**排除「合法引用該字串的區域」**。
    讀活體治理文件（缺陷帳本、archive、ADR、ONBOARDING）的鎖尤其如此，因為**那些文件的
    職責就是引用缺陷字樣**——帳本存在的目的是記錄缺陷，而記錄一個「某處寫了 X」的缺陷，
    必然要逐字寫出 X。把整份文件當 haystack，等於要求文件永遠不准談論自己要消滅的東西。

    **本輪實際付過的代價**（不是假想風險）：
      - 主鎖 `TestCriteriaListIsASingleSsot` 曾以 `dest.read_text(...)[:4000]` 取樣，切片
        溢進逐字搬入的表格區，撞到 `DEF-101-584` 那一列的現象散文——那一列之所以寫著
        「共七項」，正是因為它在敘述「標頭殘留共七項」這個缺陷。**被測行為是對的，紅的是
        取樣範圍。**
      - 後果不只是一次假紅：Pkg-P11 撞到同一支紅時的處置是**在資料側繞道**——把該列的
        現象散文從逐字引用改寫成描述性寫法（實測：活體主檔現在對「共七項」零命中）。
        載具的 bug 讓**帳本扭曲了自己的缺陷描述**，與「原文逐字保全、零刪除」的史料紀律
        直接衝突。**假紅的真正代價是資料被改去討好載具，而不是紅燈本身。**

    **同族**：與本輪已立帳的「載具量測 production 盲區」（載具只認棄用路徑的 marker，
    真跑恆 0）、「驗證載具本身要被驗證」是同一族——**問題都在量測面而非被測面**，而綠燈／
    紅燈都無法自己指出這件事。判定一處是否屬本族，問兩個問題：
      (i)  haystack 是否含「該字串會合法出現」的區域？
      (ii) 那個區域是否**不是**被測對象？兩者皆是 ⇒ 取樣範圍畫錯了。

    **既有的正確做法**（本 repo 已有先例，不必另創）：
      - 結構收窄：`_generated_header_of()`（切到第一列可解析缺陷列之前）、
        `test_nightly_interpreter_determinism` 只取「零命中分支」的 body、
        `test_ps_engine_ssot` 取 `ast.unparse` 後的函式本體（不含 docstring／註解）、
        `test_find_git_bash_parity._code_only()`（剝掉註解）。
      - 逐行 ＋ 例外出口：`test_no_stale_criterion_seven_reference_remains_in_the_tool`
        允許「判準⑦」出現在**帶『訂正』字樣的行**——歷史紀錄與現行指涉分開判。
      - 生產側同型解法：`check()` 判準(4)(6) 的 (甲) code span ／ (丙) ``` 圍籬例外，
        存在的理由一模一樣（帳本條目本來就會逐字引述判準語法）。

    本類別把上述紀律機械化，並用**合成違規片段**自證掃描器真的會說話（否則「掃描面乾淨」
    與「掃描器壞了」在綠燈上長得一樣）。
    """

    #: 掃描面＝本檔所在的根層測試目錄（非遞迴）。刻意**不**擴到整個 monorepo：
    #: 子專案測試不在本包所有權內，把它們納入等於用一支新鎖去紅別人的檔。
    #: 目錄不存在時 fail-loud（掃描面靜默縮成空集合是本輪反覆處理的病）。
    _SCAN_DIR = _HERE.parent

    @classmethod
    def _scan_targets(cls) -> list[Path]:
        paths = sorted(cls._SCAN_DIR.glob("test_*.py"))
        if not paths:
            raise AssertionError(
                f"掃描面 {cls._SCAN_DIR} 下找不到任何 `test_*.py` —— 目錄搬移或命名慣例"
                "已變，請同步 _SCAN_DIR（掃描面不得靜默縮成空集合）"
            )
        return paths

    def test_no_root_test_asserts_absence_against_a_whole_live_document(self):
        """紀律本體：不得拿「整份文件」當 haystack 去斷言某段文字不出現。"""
        offenders = [
            f"{p.name}::{hit}"
            for p in self._scan_targets()
            for hit in wholefile_text_notin_sites(p.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            offenders, [],
            "以下斷言拿整份文件當 haystack 去斷言某段文字不出現——文件只要**合法地**提到"
            "該字樣就假紅（Pkg-P12 已實際發生，並導致帳本改寫自己的缺陷描述）。"
            "請改以結構標記收窄取樣範圍，或改逐行判定並為合法引用留出口：\n  - "
            + "\n  - ".join(offenders),
        )

    def test_no_root_test_slices_a_file_read_with_a_hardcoded_bound(self):
        """紀律的另一半：檔案讀取結果不得用寫死數字切片（邊界必須是結構性的）。"""
        offenders = [
            f"{p.name}:{hit}"
            for p in self._scan_targets()
            for hit in hardcoded_read_slice_sites(p.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            offenders, [],
            "以下位置以寫死數字切檔案內容——該數字默默假設「我要的區段一定短於 N」，"
            "而生成內容的長度會隨判準／清單增減而變（Pkg-P12 的 `[:4000]`）。"
            "請改用結構邊界（標記、生成端的分節點）：\n  - " + "\n  - ".join(offenders),
        )

    #: 合成違規片段＝Pkg-P12 修復前的**真實形狀**逐字重建（含間接變數綁定 ＋ 寫死切片）。
    #: 兩支掃描器都必須對它說話，否則上面兩條「掃描面乾淨」是恆真的。
    _SYNTHETIC_OFFENDER = (
        "class T:\n"
        "    def test_x(self):\n"
        "        header = dest.read_text(encoding='utf-8')[:4000]\n"
        "        self.assertNotIn('作廢字樣', header)\n"
        "        self.assertNotIn(b'\\r', dest.read_bytes())\n"
    )

    def test_the_wholefile_detector_speaks_on_a_synthetic_offender(self):
        """反恆真①：對合成違規片段，文字型掃描器必須**恰好**命中那一處。

        同一段裡刻意放一條 `assertNotIn(b"\\r", dest.read_bytes())`：bytes needle 屬位元組
        級不變量、不在本紀律射程，掃描器把它也算進去就是過度擴張（會逼真實的 CR 鎖改寫）。
        故此處斷言命中數**恰為 1**，不是「≥1」。
        """
        hits = wholefile_text_notin_sites(self._SYNTHETIC_OFFENDER)
        self.assertEqual(
            len(hits), 1,
            f"文字型掃描器對 Pkg-P12 的原始形狀命中 {len(hits)} 處（期望恰好 1）⇒ "
            f"要嘛抓不到間接變數綁定、要嘛把 bytes needle 也算進來。實得：{hits}",
        )
        self.assertIn("assertNotIn(<文字>", hits[0])

    def test_the_hardcoded_slice_detector_speaks_on_a_synthetic_offender(self):
        """反恆真②：對合成違規片段，寫死切片掃描器必須指名那一處並印出實際寫法。"""
        hits = hardcoded_read_slice_sites(self._SYNTHETIC_OFFENDER)
        self.assertEqual(len(hits), 1,
                         f"寫死切片掃描器對 `read_text(...)[:4000]` 命中 {len(hits)} 處"
                         f"（期望恰好 1）。實得：{hits}")
        self.assertIn("[:4000]", hits[0], "訊息未印出實際的寫死切片，讀者無從定位")

    def test_a_named_narrowing_extractor_is_not_flagged(self):
        """控制組：經**具名收窄抽取器**取樣的斷言不得被誤報（否則正確做法反而被罰）。

        兩個真實形狀：本檔的 `_generated_header_of(dest)`，以及
        `test_find_git_bash_parity._code_only(...)`（剝掉註解後再 `.lower()`）——後者含
        字元正規化外殼，用來坐實「剝殼只剝到具名呼叫為止」這個邊界。
        """
        benign = (
            "class T:\n"
            "    def test_x(self):\n"
            "        header = _generated_header_of(dest)\n"
            "        self.assertNotIn('作廢字樣', header)\n"
            "        code = self._code_only(p.read_text(encoding='utf-8')).lower()\n"
            "        self.assertNotIn('system32', code)\n"
        )
        self.assertEqual(
            wholefile_text_notin_sites(benign), [],
            "經具名收窄抽取器（`_generated_header_of` / `_code_only`）取樣的斷言被誤報 ⇒ "
            "本鎖會逼所有正確做法改寫，等於紀律反向",
        )

    def test_this_file_is_inside_the_scanned_surface(self):
        """前提坐實：本檔自己必須在掃描面內（否則上面兩條對本檔零效力）。"""
        self.assertIn(_HERE, self._scan_targets(),
                      f"{_HERE.name} 不在掃描面內 —— 命名慣例或 _SCAN_DIR 已偏移")


# ============================================================================
# R68 帳本容量政策（DEF-101-676）機械鎖 —— 併入本檔而非另開檔
# ============================================================================
# 🔴 為何併進來：`DEF-101-561③` 對 `tools/tests` 的鎖檔數立了 **shrink-only 棘輪**
# （`test_adr_xplat001_c1c2_lock.TestGuardFileCountShrinkOnlyRatchet`），只准合併／刪除、
# 不准新增。落地時實測撞到（53→54 當場轉紅），故改為併入判準最相關的本檔。
#
# R68 帳本容量政策（DEF-101-676）的機械鎖 — 新政策必須自己可被驗證。
#
# 背景（R68 動工前實測）：主檔 260747 bytes、硬線 262144，餘裕 1397 bytes；
# `--plan` 印「可搬 0 筆／0 bytes」、不可搬 106 筆 ⇒ **往帳本加任何一列缺陷就撞 rc=1
# 硬閘，整輪無法收輪**。DEF-101-676 列內載三條候選方向，至 R67 收輪皆未評估。
#
# R68 的裁決與落地（逐條）：
#   ① 判準③「被 crossref 掃描目標做過狀態宣稱」——**採納並改寫成根因解**。真正的缺口在
#      `check_defect_log_crossref._load_ledger_status()` 只讀主檔，故歸檔一筆被宣稱過的
#      列就會讓 `_scan_target()` 報「查無此 ID」；歷輪用「不准搬」去繞「搬了會假紅」。
#      R68 補 `_load_archive_status()`，帳本 SSOT 成為它一直宣稱的「主檔 ∪ archive」，
#      判準③ 遂由 blocker 改寫為事後條件並由 `--check` 判準(8) 實跑驗證。
#      實測釋放：11 筆／16217 bytes（原本**只**被判準③ 擋著）。
#   ② open-backlog 專用 archive——**駁回**。見 `TestOpenBacklogArchiveIsRejected`。
#   ③ 檢討硬線本身——**駁回**。見 `TestHardLineIsToolFact`（附 R68 當日實測探針）。
#   ④（不在原三條內，R68 現查新增）判準② 是全欄裸子字串掃描，把 Python 內建函式
#      `open(` 與「本列自己被推翻的舊狀態引述」都當成活躍訊號，16 筆已結列／39705 bytes
#      因此永久卡住。收窄為「排除程式碼片段與角引號引述後仍命中」，釋放 6 筆／18637 bytes。
#
# 本檔的每一條都刻意帶**反向鑑別力**（把修復拿掉就會轉紅），而不是只斷言現況為真。
# ============================================================================

def _tmpdir():
    return tempfile.TemporaryDirectory()


class TestHardLineIsToolFact(unittest.TestCase):
    """方向③（調高硬線）駁回鎖：262144 綁的是 Read 工具事實，不是政策自由度。

    🔴 **為何這不是「把溫度計砸掉」的相反面 —— 為何連「調高一點點」都不行**：
    2026-08-01 於 macOS 26.5.2 arm64 真機對 Read 工具實跑探針（R67 的認知不被採信、
    當場重驗），兩發皆在**還沒讀到任何內容**時就被工具本身拒絕：

        Read(probe_2m.txt   / 2097152 bytes)
          → File content (2MB) exceeds maximum allowed size (256KB).
        Read(probe_300k.txt /  307200 bytes)
          → File content (300KB) exceeds maximum allowed size (256KB).

    錯誤訊息逐字載明上限 256KB ⇒ R67 帳本內「現值 262144 綁的是 Read 工具單次讀取上限」
    於 R68 仍成立、未過期。把 `_LEDGER_FAIL_BYTES` 調高的後果不是「閘門變寬鬆」而是
    **主檔變成任何 agent 都讀不完整的檔**：Read 會直接拒絕，被迫改用 offset/limit 分段
    讀，而分段讀的讀者不會知道自己漏了哪些列——「讀不完整的 SSOT」比「撞閘門」壞得多，
    因為前者是靜默失效。容量問題的正解是提高輪替**吞吐**，不是提高上限。
    """

    def test_fail_line_equals_measured_read_tool_limit(self):
        self.assertEqual(
            ADL.gate._LEDGER_FAIL_BYTES, ADL.gate._READ_TOOL_MAX_BYTES,
            "帳本硬線必須恰等於 Read 工具實測上限。調高＝主檔將無法被單次完整讀取"
            "（靜默失效）；調低＝政策與工具事實脫鉤，下一輪讀者無從判斷哪個數字為真。"
            "若確認工具上限已改變，請連同本測試 docstring 的探針取證一起更新",
        )

    def test_measured_limit_is_the_documented_256kb(self):
        self.assertEqual(ADL.gate._READ_TOOL_MAX_BYTES, 256 * 1024,
                         "R68 探針實測值為 256KB；改動此常數必須附新的實跑取證")

    def test_warn_line_is_below_fail_line(self):
        """warn 必須嚴格早於 fail，否則預警等於沒有（撞線當下才第一次出聲）。"""
        self.assertLess(ADL.gate._LEDGER_WARN_BYTES, ADL.gate._LEDGER_FAIL_BYTES)


class TestArchiveFallbackResolvesClaims(unittest.TestCase):
    """方向① 的落地鎖：帳本 SSOT ＝ 主檔 ∪ archive 家族。

    正向：已歸檔的 ID 必須解析得到（否則判準③ 的改寫前提不成立）。
    反向：真正不存在的 ID 仍須報錯（否則這就不是補齊解析面，而是把一致性檢查放水）。
    """

    @classmethod
    def setUpClass(cls):
        cls.main_status = ADL.gate._load_ledger_status()
        cls.arch_status = ADL.gate._load_archive_status()

    def test_archive_status_map_is_substantial(self):
        """空 map 會讓 fallback 靜默無效、而 `_scan_target` 行為看起來完全正常。"""
        self.assertGreater(
            len(self.arch_status), 100,
            "archive 解析面近乎為空 ⇒ glob 或表頭解析已失效，fallback 名存實亡",
        )

    def test_archive_ids_are_disjoint_from_or_consistent_with_main(self):
        """同 ID 兩邊都有時，狀態分類不得矛盾（主檔優先只是查找序，不是掩蓋矛盾的藉口）。"""
        for def_id, arch_cls in self.arch_status.items():
            if def_id in self.main_status:
                with self.subTest(def_id=def_id):
                    self.assertEqual(
                        self.main_status[def_id], arch_cls,
                        f"{def_id} 在主檔與 archive 的狀態分類不一致（--check 判準(3) 同守）",
                    )

    def test_claim_about_archived_id_resolves_instead_of_erroring(self):
        """正向鑑別力：構造一句對「已歸檔且不在主檔」的 ID 的宣稱。

        不給 archive map（＝R68 之前的行為）必須報「查無此 ID」；給了才放行。
        兩者對照才證明 fallback 真的是它讓這句話通過的。
        """
        archived_only = {k: v for k, v in self.arch_status.items()
                         if k not in self.main_status and v is not None}
        self.assertTrue(archived_only, "找不到「只存在於 archive」的 ID ⇒ 前提失效")
        def_id, cls = sorted(archived_only.items())[0]
        target = Path(self.enterContext(_tmpdir())) / "claim.md"
        target.write_text(f"**{def_id}**（{cls}）\n", encoding="utf-8")

        without = ADL.gate._scan_target(target, self.main_status)
        self.assertTrue(
            without and "查無此 ID" in without[0],
            f"控制組：不啟用 fallback 時 {def_id} 本應報「查無此 ID」，實得 {without!r}"
            "——若這裡是空的，本測試的對照組不成立",
        )
        with_fb = ADL.gate._scan_target(target, self.main_status, self.arch_status)
        self.assertEqual(with_fb, [],
                         f"啟用 fallback 後 {def_id} 仍有問題：{with_fb!r}")

    def test_unknown_id_is_still_rejected_with_fallback_enabled(self):
        """反向鑑別力：fallback 不得退化成「什麼都放行」。"""
        target = Path(self.enterContext(_tmpdir())) / "claim.md"
        target.write_text("**DEF-999-99999**（fixed）\n", encoding="utf-8")
        problems = ADL.gate._scan_target(target, self.main_status, self.arch_status)
        self.assertTrue(problems, "從未立帳的 ID 仍必須報錯，否則一致性檢查已被掏空")
        self.assertIn("查無此 ID", problems[0])
        self.assertIn("主檔 ∪ archive", problems[0],
                      "訊息須載明實際查找範圍，否則讀者無從判斷它查了哪裡")

    def test_wrong_status_claim_about_archived_id_is_still_caught(self):
        """反向鑑別力：回退到 archive 之後，**狀態仍要逐筆比對**，不是查到就算過。"""
        archived_only = {k: v for k, v in self.arch_status.items()
                         if k not in self.main_status and v == "fixed"}
        self.assertTrue(archived_only, "找不到 archive 內 cls=fixed 的樣本 ⇒ 前提失效")
        def_id = sorted(archived_only)[0]
        target = Path(self.enterContext(_tmpdir())) / "claim.md"
        target.write_text(f"**{def_id}**（wontfix）\n", encoding="utf-8")
        problems = ADL.gate._scan_target(target, self.main_status, self.arch_status)
        self.assertTrue(problems,
                        f"{def_id} 實為 fixed，宣稱 wontfix 卻未被抓到 ⇒ fallback 放水")
        self.assertIn("實際狀態為", problems[0])


class TestCriterion2Narrowing(unittest.TestCase):
    """判準② 收窄鎖（R68）：排除誤報面，但三道鑑別力不得流失。

    收窄的**動機是實測**而非美觀：R68 動工前 16 筆已結列（39705 bytes）只被判準② 擋著，
    逐筆檢視命中的字元後，全部落在「Python `open(` 呼叫」「引述本列自己被推翻的舊狀態」
    「在講別的 DEF-ID」三類。這與判準② 當初為了消滅 `OpenMutexW` 誤報而加 ASCII 邊界
    完全同型，只是逸出面從「英文字母相鄰」換成「反引號／角引號內」。
    """

    def test_python_open_call_in_code_span_is_not_flagged(self):
        """DEF-101-391 的真實形態（逐字取自主檔）。"""
        cell = ('fixed@R48：`python3 -c "import yaml; '
                'yaml.safe_load(open(\'.github/workflows/windows-compat-ci.yml\'))"` 語法合法')
        self.assertIsNotNone(
            ADL.ACTIVE_STATUS_RE.search(cell),
            "前提：裸正則本來就會命中這個 `open`（否則本條沒在驗任何東西）",
        )
        self.assertIsNone(
            ADL.active_status_hit(cell),
            "程式碼片段內的 Python 內建函式 `open` 不得被判為活躍狀態",
        )

    def test_quoted_superseded_status_is_not_flagged(self):
        """DEF-101-554／581 的真實形態：引述的目的正是宣告它**已不成立**。"""
        for cell in (
            'fixed@R60（污染已還原）：本欄原文為「`open`（待主控還原）」，現已無需動作',
            'fixed@R60 r3（Pkg-P11 訂正：原記狀態 `open（未指派）`、修法記為改引用）',
        ):
            with self.subTest(cell=cell[:30]):
                self.assertIsNotNone(ADL.ACTIVE_STATUS_RE.search(cell), "前提")
                self.assertIsNone(ADL.active_status_hit(cell))

    def test_bare_prose_active_word_is_still_flagged(self):
        """🔴 鑑別力保留 (a)：沒有反引號／角引號包起來的活躍字樣照樣命中。

        收窄若不慎變成「只要出現過反引號就整欄放行」，這一條會轉紅。
        """
        for cell in (
            "fixed@R60（① 已修）；② 殘項 open，尚未處理",
            "fixed@R60，但 `check_loc_budget` 那半邊 routed 給別人做",
            "wontfix；此項 deferred 至有需求時再議",
        ):
            with self.subTest(cell=cell[:30]):
                self.assertIsNotNone(
                    ADL.active_status_hit(cell),
                    "裸散文裡的活躍字樣必須照樣命中 —— 收窄不得擴大成整欄豁免",
                )

    def test_masking_preserves_offsets(self):
        """遮罩必須等長置換：報告會引用命中位置，長度一變位置就對不上。"""
        cell = "fixed@R60（`open(x)`）；殘項 open 未處理"
        hit = ADL.active_status_hit(cell)
        self.assertIsNotNone(hit)
        self.assertEqual(cell[hit.start():hit.end()], "open",
                         "命中 offset 必須仍能在**原字串**上取回同一個詞")

    def test_ascii_boundary_semantics_survive_the_narrowing(self):
        """🔴 鑑別力保留 (b)：R60 G-refuter-4 的 `OpenMutexW` 不得因收窄而復發或改變結論。"""
        for benign in ("OpenMutexW", "CreateFileW/OpenProcess", "reopened", "openssl"):
            with self.subTest(benign=benign):
                self.assertIsNone(ADL.active_status_hit(f"fixed@R60：{benign} 已處理"))

    # 判準④ 安全網的具名樣本（散文帶交棒字樣、`--plan` 應判 needs_ack）。
    # 樣本會隨帳本歸檔逐筆離開主檔，故另設存活下限（見下方測試的 R69 段落）。
    #
    # 🔴 R71 補樣本（**這正是下限機制設計時預期的動作**）：本輪歸檔 `DEF-101-521` 後
    # 存活樣本掉到 1 筆（`524` 早於 R69 隨 `archive_47` 離開主檔），觸發 fail-loud 下限。
    # 依測試訊息的指路「從現行主檔挑一筆散文帶交棒字樣、且 `--plan` 判為 needs_ack 的
    # DEF 補進本表」補入 `652`／`710` ⇒ 存活回到 3 筆。兩筆均為 `--plan` 現跑實查
    # （2026-08-03）：`cls='fixed'`、`blockers=[]`（判準①②③ 全過）、`handoff_marker='改派'`
    # 且該字樣確實逐字存在於各自列內——即「本會被判可搬、全靠判準④ 攔下」的樣本形態，
    # 與原三筆同型。散文實據：`652`＝「…Windows 對等缺口仍在，改派為：未指派（解鎖條件
    # ＝有 Windows 真機可實跑驗證的一輪）」；`710`＝「…超出本輪授權面），改派為：未指派。
    # 解鎖條件＝回讀 `DEF-101-432` 全欄…」。
    # 🔴 補樣本是唯一正解，**不得**改用 skip／下修 `_MIN_LIVE_HANDOFF_SAMPLES` 讓紅燈變綠
    # ——那兩條路都是把「安全網已無驗證對象」這個真訊號消音，正是 R69 付過學費的形態。
    _HANDOFF_SAMPLE_IDS = ("DEF-101-521", "DEF-101-524", "DEF-101-554",
                           "DEF-101-652", "DEF-101-710")
    _MIN_LIVE_HANDOFF_SAMPLES = 2

    def test_handoff_net_is_untouched_by_the_narrowing(self):
        """🔴 鑑別力保留 (c)：判準④ 掃**整列**、且不套遮罩，真交棒仍會被攔下要求具名承認。

        實測坐實：本次因收窄而通過判準② 的 6 筆中，521／524／554 三筆隨即落在判準④
        手上（`--plan` 把它們列在「需具名承認」而非「可搬」）。

        🔴 R69：原版對「樣本已被歸檔」的處置是 `self.skipTest(...)`，實測後果是
        `archive_47` 搬走 DEF-101-524 之後，根層多出**第 16 支 skip、且是唯一未標籤
        的樣本流失型 skip**（`run_root_unittests.py` 的明細印為
        `[未標籤] …(def_id='DEF-101-524')`）。silent skip 正是本 repo 反覆付學費的形態
        （R68「122 支迴歸鎖一支都沒跑」）：安全網樣本一支支被歸檔搬走，這條鎖會**無聲
        地**縮到零樣本，而輸出上只是多一行 skipped。改為：對「仍在主檔」的樣本照跑，
        並對存活樣本數設 fail-loud 下限——樣本掉到下限以下即紅，逼人補新樣本而不是
        讓鎖靜默退化。
        """
        p = ADL.plan()
        needs_ack_ids = {v["id"] for v in p["needs_ack"]}
        movable_ids = {v["id"] for v in p["movable"]}
        in_main = needs_ack_ids | movable_ids
        live = [d for d in self._HANDOFF_SAMPLE_IDS if d in in_main]
        archived = [d for d in self._HANDOFF_SAMPLE_IDS if d not in in_main]
        self.assertGreaterEqual(
            len(live), self._MIN_LIVE_HANDOFF_SAMPLES,
            f"判準④ 安全網的存活樣本只剩 {len(live)} 筆（下限 "
            f"{self._MIN_LIVE_HANDOFF_SAMPLES}）：仍在主檔={live}／已歸檔={archived}。"
            "樣本被歸檔搬光後本鎖就沒有驗證對象了——請從現行主檔挑一筆散文帶交棒字樣、"
            "且 `--plan` 判為 needs_ack 的 DEF 補進 _HANDOFF_SAMPLE_IDS，"
            "**不要**改用 skip 讓它靜默退化（R69 已為此付過一支未標籤 skip 的學費）",
        )
        for def_id in live:
            with self.subTest(def_id=def_id):
                self.assertIn(
                    def_id, needs_ack_ids,
                    f"{def_id} 散文帶交棒字樣，判準② 收窄後必須由判準④ 接手攔下；"
                    "它若直接落進可搬清單，代表安全網真的破了",
                )


class TestCriterion8VerifiesClaimsResolveAcrossFamily(unittest.TestCase):
    """判準(8) 端到端鎖：`--check` 必須真的實跑跨檔宣稱解析，而不是宣稱它跑了。

    本工具立帳要消滅的病就是「宣稱一道機械檢查存在而它不存在」（見 `CHECK_CRITERIA`
    上方 P7-4 的 WHY）。判準③ 改寫成事後條件之後，那個事後條件若只是散文，就正好是
    同一種病在同一支工具身上復發。
    """

    def test_criterion_8_is_registered_in_the_ssot(self):
        labels = [label for label, _ in ADL.CHECK_CRITERIA]
        self.assertIn("跨檔宣稱可解析", labels)

    def test_check_actually_runs_criterion_8_and_reports_counts(self):
        r = subprocess.run(
            [sys.executable, str(_REPO / "tools" / "archive_defect_log.py"), "--check"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(_REPO),
        )
        self.assertEqual(r.returncode, 0, f"--check 應 rc=0\nstderr:\n{r.stderr[-3000:]}")
        self.assertIn("判準(8) 實算：", r.stdout,
                      "判準(8) 必須每次執行都印出實算結果 —— 講不出數字就不算跑過")
        self.assertIn("帳本家族解析面", r.stdout)
        self.assertIn("(8)跨檔宣稱可解析", r.stdout,
                      "成功訊息須由 CHECK_CRITERIA 生成並含第(8)項")


class TestUnlockConditionIsMechanicallyChecked(unittest.TestCase):
    """DEF-101-676 的解鎖判準（R67 round 4 訂）必須每跑一次 `--plan` 就當場現算。

    原始解鎖條件「`--plan` 的可搬筆數 > 0」是 **fail-open**：它量的是「有沒有可搬的列」
    而不是「輪替還買不買得到餘裕」，當輪多寫一列已結列就自己變 True。R67 改為
    「`--plan` 印出的『搬後主檔約 N bytes』距 fail 線 ≥ 10240」。本條把那句判準綁進程式，
    讓它不是靠人記得去翻帳本對數字。
    """

    def test_plan_prints_headroom_and_the_verdict(self):
        r = subprocess.run(
            [sys.executable, str(_REPO / "tools" / "archive_defect_log.py"), "--plan"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(_REPO),
        )
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertIn("距 fail 線", r.stdout)
        self.assertIn("DEF-101-676 解鎖判準", r.stdout)

    def test_unlock_threshold_constant_matches_the_ledger_wording(self):
        self.assertEqual(ADL._UNLOCK_HEADROOM_BYTES, 10240,
                         "門檻改動必須同步 DEF-101-676 列的解鎖條件散文")

    @staticmethod
    def _def676_status_cell() -> str:
        """DEF-101-676 在主檔的狀態欄原文（找不到即空字串）。"""
        text = ADL._LEDGER.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("| DEF-101-676 |"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                return cells[-1] if cells else ""
        return ""

    def test_headroom_matches_what_def676_claims(self):
        """解鎖判準本體，但問的是**宣稱與現況是否一致**，不是「餘裕必須永遠健康」。

        🔴 R68 訂正（本鎖原形態會逼出它自己要防的行為）：原斷言是「餘裕恆 ≥ 門檻」。
        它在 R68 當場失效——本輪十二維掃描 9 列入帳後，兩次合法輪替仍只買回約 8000
        bytes 餘裕。此時原鎖給的**唯一**轉綠路徑是「再具名承認幾列去湊過線」，而那
        正是 DEF-101-676 立這條判準要防的事（R67 round 4 已因「量測快照當判準」被四方
        交叉命中過一次）。一個只能靠做壞事才能轉綠的鎖，不是護欄。

        改為對帳型斷言（形狀取自 DEF-101-689「修復包自報 status ↔ 帳本狀態欄」）：
          · DEF-101-676 宣稱**已結** ⇒ 判準必須當場成立（抓的是假宣稱，這才是重點）；
          · 宣稱**未結** ⇒ 餘裕不足是誠實揭露、不轉紅，但仍強制它帶承接指派
            （硬規則② 後半句），不得變成沒人接的永久停車位。
        兩個方向都留了牙：把狀態改回 `fixed` 卻不解決容量 → 紅；改成未結卻不寫承接
        → 紅。唯一的綠燈路徑是「要嘛真的解決、要嘛誠實掛帳並指名承接」。
        """
        p = ADL.plan()
        after = p["ledger_bytes"] - sum(v["bytes"] for v in p["movable"])
        headroom = ADL.gate._LEDGER_FAIL_BYTES - after
        status = self._def676_status_cell()
        self.assertTrue(status, "DEF-101-676 不在主檔 ⇒ 本鎖失去掃描標的")
        claims_resolved = ADL.gate._classify(status) not in ADL.gate._UNRESOLVED_CLASSES
        if claims_resolved:
            self.assertGreaterEqual(
                headroom, ADL._UNLOCK_HEADROOM_BYTES,
                f"DEF-101-676 狀態欄宣稱已結（首詞判為已結），但搬後主檔約 {after} "
                f"bytes、距 fail 線僅 {headroom} < {ADL._UNLOCK_HEADROOM_BYTES} ⇒ "
                "宣稱與現況不符。請勿調高硬線（見 TestHardLineIsToolFact），也勿為了"
                "湊過線而具名承認未經逐字複核的列；正解是提高輪替吞吐，或據實下修狀態",
            )
        else:
            self.assertTrue(
                ADL.gate._UNASSIGNED_LITERAL in status
                or ADL.gate._handover_rounds(status),
                "DEF-101-676 未結卻既無承接輪號也無字面「未指派」⇒ 硬規則② 後半句："
                "容量問題不得變成沒人接的永久停車位",
            )


class TestOpenBacklogArchiveIsRejected(unittest.TestCase):
    """方向②（讓長期未結的 known-gap 列搬進 open-backlog archive、主檔只留指針）駁回鎖。

    🔴 **駁回理由不是「工作量大」，是它會讓兩條既有硬規則同時瞎掉**：

      (甲) `check_defect_log_crossref.orphan_backlog_problems()`（硬規則②，R67 才落地）
           的輸入是 `ledger_text` ＝ **主檔全文**。它逐列檢查「未結案列指名的承接輪次不得
           早於當前輪」。未結列一旦搬出主檔，這道閘門對它們就是零檢查——而未結列正是
           唯一需要孤兒偵測的那一群。等於為了容量，把 R67 剛補上的孤兒偵測整個關掉。
      (乙) `current_round()` 由主檔「發現情境」欄推得當前輪次。主檔只剩指針之後，
           輪次推導的樣本面同步縮小。
      (丙) 「帳本是 SSOT」在讀者面失效：未結項才是每輪開工必讀的那一半，把它搬走
           只留指針，等於要求每個讀者多讀一支檔才知道現在有哪些活；而容量問題的成因
           恰恰是「一次讀不完」——把必讀內容搬到第二支檔並沒有解決它，只是換個地方。

    量化對照（R68 動工前實測）：方向② 的標的是 78 筆 open/routed 列共 155615 bytes，
    看似最大宗；但實際採納的 ①＋判準② 收窄合計釋放 19486 bytes 已使餘裕達標，且**不
    破壞任何不變量**。以「破壞兩條硬規則」換取暫時更大的數字不划算。

    本測試鎖的是：孤兒偵測的輸入面**必須**仍是主檔全文，且主檔**必須**仍實際承載未結列。
    哪天有人把未結列搬走，這裡會轉紅。
    """

    def test_orphan_detection_input_is_the_main_ledger_text(self):
        import inspect
        sig = inspect.signature(ADL.gate.orphan_backlog_problems)
        self.assertIn("ledger_text", sig.parameters,
                      "孤兒偵測必須吃主檔全文；改吃別的來源前請先讀本測試 docstring")

    def test_main_ledger_still_carries_the_unclosed_rows(self):
        text = ADL.gate._DEFECT_LOG.read_text(encoding="utf-8-sig")
        layout = ADL.gate._table_layout(text)
        self.assertIsNotNone(layout)
        rows = ADL.load_rows(text)
        claimed = ADL._status_claimed_ids()
        unclosed = [r for r in rows
                    if ADL.classify_row(r, claimed, layout)["cls"] not in ADL.CLOSED_CLASSES]
        self.assertGreater(
            len(unclosed), 0,
            "主檔已無任何未結列 ⇒ 未結列很可能被搬進 open-backlog archive。"
            "那會讓硬規則②（孤兒承接輪次）對它們零檢查，見本類 docstring (甲)",
        )
        # 孤兒偵測確實看得到它們（不是只是「檔案裡有」而閘門讀不到）
        self.assertEqual(ADL.gate.orphan_backlog_problems(text), [],
                         "主檔未結列存在孤兒承接輪次問題")


class TestArchiveIndexDocIsExternalized(unittest.TestCase):
    """R69 `DEF-101-734` — 歸檔索引段外移的三條結構不變量。

    **原始缺陷**：索引 bullet 是**單調增長且永遠無法靠歸檔回收**的一段（每次 `--apply`
    往主檔多寫約 0.9KB，近幾輪每輪建 3~5 支 archive），卻與缺陷總表共用主檔那條
    262,144 bytes 硬線。R69 動工時主檔距硬線只剩 250 bytes 而 `--plan` 可搬 **0 筆**
    ——把單調增長項放進有硬上限的檔，數學上保證撞牆，而歸檔吞吐再高也救不了它。

    **本鎖要守的是「搬出去之後守門沒有變弱」**，因為那才是這次外移的前提：
      (甲) 索引檔仍屬**帳本家族** ⇒ 指針稽核（判準④⑥）、體積守門、compat-CI 的
           `AutoSDD_Defect_Log_archive_*.md` `paths:` glob、沙箱複製面**全部零改動即涵蓋**。
           若有人把它改名成家族 glob 外的形態（例如 `..._INDEX.md` 不帶 `archive_`），
           這四道守門會同時、靜默地漏掉它 —— 正是 `DEF-101-587`「搬到另一支檔就繞過
           守門」的形狀，故用測試把「它必須在家族內」釘住。
      (乙) 索引檔**自己不需要 bullet**（它是目錄不是史料檔），判準⑤ 對它具名排除；
           排除若寫成「零表格列就跳過」這種模糊判準，真正忘記登記的史料檔也會被吞掉。
      (丙) 主檔內**不得再殘留**任何索引 bullet：殘留＝兩份索引並存，判準⑤ 只讀其中
           一份，另一份腐化零訊號。
    """

    def test_index_doc_is_inside_the_ledger_family(self):
        """(甲) 索引檔必須落在家族 glob 內，且家族＝指針稽核面的子集。"""
        family = {p.name for p in ADL._family_files()}
        self.assertIn(
            ADL._ARCHIVE_INDEX_NAME, family,
            f"{ADL._ARCHIVE_INDEX_NAME} 不在帳本家族（glob {ADL._ARCHIVE_GLOB}）內 —— "
            "指針稽核／體積守門／compat-CI paths 會同時漏掉它",
        )
        self.assertIn(
            ADL._ARCHIVE_INDEX_NAME,
            {p.name for p in ADL._pointer_audit_files()},
            "索引檔逸出指針稽核面 —— 它內含「立帳見 …」居所指針，逸出即零檢查",
        )

    def test_index_doc_is_excluded_from_criterion5_by_name_not_by_emptiness(self):
        """(乙) 索引檔不替自己登記 bullet，且 `--check` 仍綠；排除是具名的。

        反向證明排除**不是**靠「零表格列」：在沙箱裡給索引檔補上一列合成表格列，
        判準⑤ 仍不得要求它有 bullet（若排除寫成「零列就跳過」，這一注入會讓它翻紅）。
        """
        with _ledger_sandbox():
            index_doc = ADL.ARCHIVE_INDEX_DOC()
            listed = {n for _, n in ADL.index_bullet_lines(
                index_doc.read_bytes().decode("utf-8"))}
            self.assertNotIn(ADL._ARCHIVE_INDEX_NAME, listed,
                             "索引檔替自己登記了一條 bullet ⇒ 自我指涉的假需求")
            _append_to(
                index_doc,
                "\n| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 "
                "| 分流去向 | 狀態 |\n|---|---|---|---|---|---|---|\n"
                "| DEF-999-991 | 2026-08-02 | 沙箱 | 合成 | P4 "
                "| 合成 | fixed@R69（合成） |\n",
            )
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ADL.check()
        self.assertEqual(
            rc, 0,
            "索引檔帶了表格列之後判準⑤ 轉紅 ⇒ 排除是靠『零表格列』的模糊判準，"
            f"不是具名比對 {ADL._ARCHIVE_INDEX_NAME}：{err.getvalue()}",
        )

    def test_main_ledger_carries_no_leftover_index_bullet(self):
        """(丙) 主檔零殘留 bullet；且 `--apply` 把新 bullet 寫進索引檔而非主檔。"""
        self.assertEqual(
            ADL.index_bullet_lines(ADL._LEDGER.read_text(encoding="utf-8-sig")), [],
            "主檔仍殘留歸檔索引 bullet ⇒ 兩份索引並存，判準⑤ 只讀索引檔那一份，"
            "主檔那份腐化零訊號",
        )
        with _ledger_sandbox():
            synth_id = "DEF-" + "101-" + "9" + "92"
            _append_to(
                ADL._LEDGER,
                f"| {synth_id} | 2026-08-02 | 外移落點測試 | 合成 | P4 "
                "| 合成分流 | fixed@R69（合成，僅存在於沙箱） |\n",
            )
            main_before = ADL._LEDGER.read_bytes()
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ADL.apply(92, frozenset(), "外移落點測試")
            self.assertEqual(rc, 0, err.getvalue())
            main_after = ADL._LEDGER.read_bytes()
            index_names = {n for _, n in ADL.index_bullet_lines(
                ADL.ARCHIVE_INDEX_DOC().read_bytes().decode("utf-8"))}
        self.assertEqual(
            ADL.index_bullet_lines(main_after.decode("utf-8")), [],
            "apply() 把 bullet 寫回主檔了 —— 外移等於沒做，單調增長項又回到硬線內",
        )
        self.assertLess(
            len(main_after), len(main_before),
            "apply() 之後主檔沒有變小 ⇒ 主檔不再是「只減不增」",
        )
        self.assertIn("AutoSDD_Defect_Log_archive_92.md", index_names,
                      "新 archive 未登記進索引檔")


if __name__ == "__main__":
    unittest.main()
