#!/usr/bin/env python3
"""程式碼／文件裡的 `DEF-101-NNN` 引用「必須真的存在於缺陷帳本家族」機械鎖
（R60 SA-R60-02／QA-R60-03 家族的**可機械化那一半**）。

WHY（為何非得有這道鎖）：
  R60 有 21 處 tracked 檔（生產腳本／測試／CI workflow）引用的 DEF-ID 與帳本實際
  條目不符——並行修復包在還沒配號時用了暫用號，書面請求主控收尾替換，主控漏辦。
  **三個被誤引的號都真實存在但內容完全不同**，於是
  `tools/check_defect_log_crossref.py` rc=0（它只在「ID 緊接括號且括號內含狀態
  關鍵字」時比對，那些括號裡是「Scan-C C-02」「R60 實測」等非狀態詞 ⇒ 靜默放行），
  四道閘門全綠，最後是靠 SA 與 QA 兩位複審者人工逐處對帳才抓出來。
  同族的另一半（引用了**不存在**的號）此前也零覆蓋：任何一次打錯字、複製貼上
  改錯位數、或帳本歸檔時搬檔搬掉，追溯鏈就靜默斷掉且沒有任何訊號。

🔴 判準邊界（誠實劃界——這道鎖能抓什麼、抓不到什麼）：
  ✅ 能抓：引用的 `DEF-101-NNN` 在帳本家族（主檔 ＋ 全部 `*_archive_NN.md` ＋
     姊妹帳本 `AutoSDD_External_Blocked_Log.md`／`AutoSDD_Structural_Debt_Log.md`，
     見 DEF-200-015 四方複審續與 `_SISTER_LEDGER_RELS` 註解）裡
     **找不到對應列**。判準＝該 ID 出現在某檔某列的**第一欄**（表格主鍵位置），
     即「有一列以它為主鍵」，而不是隨便被別列的內文提到。
  ❌ 抓不到：引用的號**存在但內容不對**（＝R60 那 21 處的實際形態）。判斷「這段
     程式在講的事情是不是那一列描述的缺陷」需要語意理解，機器做不到；本輪那 21 處
     是人工逐處比對帳本「發現情境／現象」欄才判定的。**這半邊永遠是人審責任**，
     不要因為本鎖存在就以為引用號已被機械保證正確——這正是本鎖存在時仍必須在
     複審清單保留「DEF-ID 引用逐處對帳」的原因。
  ❌ 抓不到：非 `DEF-101-*` 家族的號（`DEF-62-*`／`DEF-76-*`／`DEF-100-*` 等屬
     AutoClaude 子專案自己的 `docs/` 帳本，不住在 `docs/06_quality/AutoSDD_*`）。
     刻意不納管：那些帳本的列格式與檔案位置未經本鎖驗證，硬掃會製造假紅。
  ⚪ 刻意放行：`DEF-101-Nxx`（尾碼為字母）這種**家族占位式**寫法，指「N 開頭那一
     批」而非某一列。實查全 repo 僅 2 處（v0.30 的 `test_phase_i.py`、
     `test_production_monitor.py`），其規模由下方一支測試釘住不得擴散。

掃描面：`git grep -I --untracked`（tracked ＋ 未被 .gitignore 排除的未追蹤檔），
  故本輪新建、還沒 commit 的檔也在守門範圍內——暫用號正是在這個時間窗產生的。
  帳本家族自身排除在掃描面外（它是 ID 的定義處，不是引用處）。

🔴 本檔為何沒有「自我豁免」條目（刻意的設計）：本檔的合成樣本一律**在執行期由
  `_syn()` 組出**（`"DEF-101-" + "999"`），原始碼裡不存在任何 ID 字面，因此本檔
  自然落在掃描面內而不會自我誤命中——不需要檔案級豁免。這是刻意避開 R46
  `_has_ssot_guard`／R60 `_PENDING_MIGRATION_SITES` 兩次踩過的坑：**掃描器一旦為
  自己開豁免，那個豁免就永遠不會退場**。

反空轉自檢（本鎖自己的鑑別力保護）：帳本主鍵數與掃描到的引用數各有下限；
  任一邊崩塌（正則寫壞／`git grep` 失敗／掃描面被縮成空集合）即 fail-loud，
  不會靜默「零違規」假綠——R60 四方複審抓到的三個假綠全都是這個形狀
  （鎖存在、但掃不到東西或斷言恆真）。

執行：python tools/run_root_unittests.py
      python -m unittest tools.tests.test_defect_id_reference_integrity -v
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_LEDGER_DIR = _REPO_ROOT / "docs" / "06_quality"
_LEDGER_GLOB = "AutoSDD_Defect_Log*.md"
_LEDGER_PREFIX = "docs/06_quality/AutoSDD_Defect_Log"
# 🔴 DEF-200-015 四方複審續：`AutoSDD_External_Blocked_Log.md` 是主帳本以外**另一份
# 真的以 DEF-ID 為主鍵**的姊妹帳本（拆自主帳本、專記外部條件阻塞項），此前不在
# `_LEDGER_GLOB` 掃描面內 ⇒ 拆過去的號（如 DEF-200-185／186）對本鎖結構上必為懸空。
# 🔴 結構性長債軌（掌舵者 2026-08-30 核准分軌）：同為以 DEF-ID 為主鍵的姊妹帳本，
# 不納管則遷入的列對「懸空引用」鎖結構上必紅（DEF-200-227 同型判例），故一併列入。
_SISTER_LEDGER_RELS = (
    "docs/06_quality/AutoSDD_External_Blocked_Log.md",
    "docs/06_quality/AutoSDD_Structural_Debt_Log.md",
)

# 帳本「某一列以此 ID 為主鍵」＝該 ID 出現在 markdown 表格第一欄。
_LEDGER_ROW_RE = re.compile(r"^\s*\|\s*(DEF-\d+-\d+)\s*\|")

# 引用形態。DEF-200-015：101 家族滿號後改配的 200 家族原本零覆蓋，一併納管。
# 尾碼 lookahead 排除家族占位寫法（見 docstring ⚪ 項）。
_REF_RE = re.compile(r"DEF-(?:101|200)-\d+(?![0-9A-Za-z])")
_PLACEHOLDER_RE = re.compile(r"DEF-101-\d+[A-Za-z]")

# 反空轉下限（保守留裕度；只在「掃描面崩塌」時說話，不是精確計數釘選）。
# 實測值（R60 收尾）：帳本主鍵 666、引用行 1949。
_MIN_LEDGER_IDS = 500
_MIN_REF_LINES = 800

# 占位寫法站點數上限（實查 2 處；留 2 的裕度給正當的歷史敘述，超出即代表擴散）。
_MAX_PLACEHOLDER_SITES = 4


def _syn(number: str) -> str:
    """執行期組出合成 ID——本檔原始碼因此不含任何 ID 字面（見 docstring 🔴 段）。"""
    return "DEF-101-" + number


def ledger_primary_ids(ledger_dir: Path = _LEDGER_DIR) -> set[str]:
    """帳本家族（主檔＋全部 archive＋外部阻塞姊妹帳本）中「以該 ID 為主鍵的列」

    所定義的 ID 全集。"""
    ids: set[str] = set()
    paths = sorted(ledger_dir.glob(_LEDGER_GLOB))
    for rel in _SISTER_LEDGER_RELS:
        sister = ledger_dir / Path(rel).name
        if sister.is_file():
            paths.append(sister)
    for path in paths:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = _LEDGER_ROW_RE.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def parse_grep_output(text: str) -> list[tuple[str, str, str]]:
    """把 `git grep -n` 輸出解析為 (檔, 行號, ID) 三元組（純函式，供合成樣本自證）。

    刻意不在此過濾帳本家族——過濾規則由 `scan_references()` 負責，讓「解析」與
    「決定掃描面」兩件事分開可各自被測。
    """
    hits: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        # git grep -n 格式：<path>:<lineno>:<內容>
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, lineno, content = parts
        for m in _REF_RE.finditer(content):
            hits.append((path, lineno, m.group(0)))
    return hits


def _git_grep(repo_root: Path) -> str:
    """跑 `git grep`；rc=0（有命中）與 rc=1（無命中）皆正常，其餘 fail-loud。"""
    proc = subprocess.run(
        ["git", "grep", "-I", "-n", "--untracked", "-E", r"DEF-(101|200)-[0-9]+"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo_root),
    )
    if proc.returncode not in (0, 1):
        raise AssertionError(
            f"git grep 失敗（rc={proc.returncode}）——掃描面取不到就不得當成「零違規」，"
            f"故此處 fail-loud。\nstderr: {proc.stderr[-800:]}"
        )
    return proc.stdout


def is_ledger_path(path: str) -> bool:
    """該路徑是否屬帳本家族（ID 的定義處，不計為引用）。"""
    posix = path.replace("\\", "/")
    return posix.startswith(_LEDGER_PREFIX) or posix in _SISTER_LEDGER_RELS


def scan_references(repo_root: Path = _REPO_ROOT) -> tuple[list[tuple[str, str, str]], int]:
    """回傳 (排除帳本家族後的引用三元組, 原始命中行數)。"""
    raw = _git_grep(repo_root)
    ref_lines = len([ln for ln in raw.splitlines() if ln.strip()])
    hits = [h for h in parse_grep_output(raw) if not is_ledger_path(h[0])]
    return hits, ref_lines


def placeholder_sites(raw: str) -> list[str]:
    """列出家族占位寫法（`DEF-101-Nxx`）的 檔:行（供規模釘選）。"""
    sites: list[str] = []
    for line in raw.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and _PLACEHOLDER_RE.search(parts[2]):
            sites.append(f"{parts[0]}:{parts[1]}")
    return sites


class TestDefectIdReferenceIntegrity(unittest.TestCase):
    """真實 repo × 真實帳本的引用完整性（本鎖的正職）。"""

    def test_every_referenced_defect_id_exists_in_ledger_family(self) -> None:
        """每一個被引用的 `DEF-101-NNN` 都必須在帳本家族有一列以它為主鍵。"""
        known = ledger_primary_ids()
        hits, _ = scan_references()
        dangling = sorted(
            {f"{path}:{lineno} -> {ref}" for path, lineno, ref in hits if ref not in known}
        )
        self.assertEqual(
            dangling,
            [],
            "以下引用指向帳本家族裡不存在的缺陷編號（追溯鏈斷掉，且讀者會被導向空號）：\n"
            + "\n".join(f"  {d}" for d in dangling)
            + "\n修法二選一：①訂正為正確編號（**必須逐處回帳本核對『發現情境／現象』欄，"
            "本鎖只驗『存在』、不驗『內容對不對』——見本檔 docstring 判準邊界**）；"
            "②若該號應該存在卻不在帳本，補立條目。",
        )

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """反空轉：帳本主鍵數與引用命中行數都必須在下限之上（掃不到 ≠ 沒違規）。"""
        known = ledger_primary_ids()
        _, ref_lines = scan_references()
        self.assertGreaterEqual(
            len(known),
            _MIN_LEDGER_IDS,
            f"帳本家族只解析到 {len(known)} 個主鍵 ID（下限 {_MIN_LEDGER_IDS}）——"
            f"列格式改動或 archive 檔搬移會讓本鎖把所有引用誤判為 dangling；"
            f"請先修解析規則（{_LEDGER_ROW_RE.pattern}）再談違規",
        )
        self.assertGreaterEqual(
            ref_lines,
            _MIN_REF_LINES,
            f"git grep 只掃到 {ref_lines} 行 DEF-101 引用（下限 {_MIN_REF_LINES}）——"
            f"掃描面崩塌時「零 dangling」是假綠，故此處 fail-loud",
        )

    def test_family_placeholder_form_does_not_proliferate(self) -> None:
        """占位寫法（`DEF-101-Nxx`）是本鎖唯一的放行後門，其站點規模必須被釘住。

        WHY 這一支存在：若後門靜默長大（有人開始以占位號取代真號），追溯鏈就會以
        合法外觀腐化，而正職那支測試永遠不會紅。實查 R60 收尾為 2 處。
        """
        sites = placeholder_sites(_git_grep(_REPO_ROOT))
        self.assertLessEqual(
            len(sites),
            _MAX_PLACEHOLDER_SITES,
            "家族占位寫法的站點數超出既有規模——它是本鎖的放行後門，"
            f"擴散即代表有人以占位號取代真號：{sites}",
        )

    # ── 以下以合成文本自證判定器紅綠（不落 repo 樹內、不碰任何真實檔）──

    def test_parse_extracts_path_lineno_and_id(self) -> None:
        sample = _syn("531")
        self.assertEqual(
            parse_grep_output(f"tools/x.py:12:WHY（R60 A-01／{sample}）：說明"),
            [("tools/x.py", "12", sample)],
        )

    def test_parse_extracts_multiple_ids_on_one_line(self) -> None:
        a, b = _syn("527"), _syn("528")
        self.assertEqual(
            parse_grep_output(f"a.md:3:{a}／{b} 兩列"),
            [("a.md", "3", a), ("a.md", "3", b)],
        )

    def test_parse_ignores_lines_without_lineno_form(self) -> None:
        """非 `path:lineno:content` 形態（如 grep 的檔名摘要行）不得被誤收。"""
        self.assertEqual(parse_grep_output(f"{_syn('531')}\nonly:two\n"), [])

    def test_placeholder_form_is_not_collected_as_reference(self) -> None:
        """占位形態不得被誤收為引用（否則會被判 dangling ⇒ 假紅）。"""
        self.assertEqual(parse_grep_output(f"f.py:1:見 {_syn('3')}xx 系列同類缺陷"), [])
        self.assertEqual(placeholder_sites(f"f.py:1:見 {_syn('3')}xx 系列"), ["f.py:1"])

    def test_ledger_primary_id_requires_first_column(self) -> None:
        """只有「表格第一欄」算主鍵；被別列內文提到不算（否則存在性判定失去意義）。"""
        self.assertIsNotNone(_LEDGER_ROW_RE.match(f"| {_syn('531')} | 2026-07-28 | x |"))
        self.assertIsNone(
            _LEDGER_ROW_RE.match(f"| {_syn('999')} 相關 | 說明含 {_syn('531')} |")
        )

    def test_dangling_detection_on_synthetic_input(self) -> None:
        """合成情境：已知集合缺該號 ⇒ 必須被判為 dangling（判定式本身的紅綠）。"""
        good, bad = _syn("531"), _syn("999")
        hits = parse_grep_output(f"t.py:1:見 {good}\nt.py:2:見 {bad}\n")
        dangling = [f"{p}:{n} -> {r}" for p, n, r in hits if r not in {good}]
        self.assertEqual(dangling, [f"t.py:2 -> {bad}"])

    def test_ledger_scope_is_excluded_from_reference_surface(self) -> None:
        """帳本家族自身是 ID 的定義處，不得被算成引用（否則每一列都自我引用）。"""
        text = (
            f"{_LEDGER_PREFIX}.md:5:| {_syn('999')} | x |\n"
            f"{_LEDGER_PREFIX}_archive_30.md:5:| {_syn('998')} | x |\n"
            f"tools/x.py:1:見 {_syn('997')}\n"
        )
        kept = [h for h in parse_grep_output(text) if not is_ledger_path(h[0])]
        self.assertEqual(kept, [("tools/x.py", "1", _syn("997"))])

    def test_windows_backslash_paths_are_normalised_for_ledger_scope(self) -> None:
        """git 一律回 posix 路徑，但若呼叫端傳入反斜線形態也不得漏判帳本範圍。"""
        self.assertTrue(is_ledger_path(_LEDGER_PREFIX.replace("/", "\\") + ".md"))
        self.assertFalse(is_ledger_path("tools\\tests\\x.py"))


if __name__ == "__main__":
    unittest.main()
