#!/usr/bin/env python3
"""PowerShell 註解剝除器 vs 真 parser ground truth 的離線差分鎖（R58 落地）。

## 這支測試在守什麼

`_ps_source.strip_ps_comments()` 是**近似法**（前導字元白名單），有結構性 fail-open：
PowerShell 的 `#` 是否為註解取決於 tokenizer 的解析模式，前導字元白名單原理上不可能完備
（R57 實測 FAIL_OPEN=27/64，其中 20 案是完全合法的日常寫法如 `$a = 1#c`）。方向為 fail-open
＝註解冒充功能碼 ⇒ 所有「錨點只認功能碼」的靜態鎖（見 `_at_risk_consumers()`）會假綠：
有人把功能碼刪掉、只在註解裡留下字樣，那些鎖照樣全綠。

R57 判定「不在該輪修」的依據是「全語料實測洩漏數為 0 ⇒ 屬 latent」，並明文禁止再往字元集合
補字元（whack-a-mole），指定 R58 的正解為**把真 parser 對全語料的 Comment token 凍結成 golden
做離線差分**。本檔即該差分。它不改變近似法的行為，而是把「latent（今天剛好沒人踩到）」轉成
**「踩到的那一刻立刻翻紅」**——即 R57 那個前提失效的瞬間。

## 三層斷言與各自的方向

| 層 | 斷言 | 需要 PowerShell？ | 失效方向 |
|----|------|------------------|---------|
| ① 新鮮度 | 每支 tracked `.ps1` 都有 golden 條目、sha256 相符、無 stale 條目 | 否 | fail-closed |
| ② 差分 | 近似法輸出 == ground truth 輸出（逐檔） | 否 | fail-closed |
| ③ golden 真實性 | 現場重新 parse 的 span 與 golden 相符 | **是**（有才跑） | fail-closed |

🔴 **關於第 ③ 層的 skip，必須誠實揭露的非對稱性**（本輪 DEF-101-507 正是在修「守門在目標平台
出廠組態下永遠 skip」這一類缺陷，故此處不能重犯）：第 ③ 層在**沒有任何 PowerShell 的機器上會
skip**（實務上＝Linux CI runner）。這與本輪修掉的 pwsh-only 缺陷**不同類**，理由是：
  * 真正的保護是第 ①②，它們**離線、無條件、每個平台都跑**——這正是把 ground truth 凍結成
    golden 的目的（CI 不裝 PowerShell 也能守）。
  * 第 ③ 層只驗「golden 自己有沒有被手改／跨引擎是否分歧」，且它在**兩個有 PowerShell 的平台
    都會跑**：Windows（出廠 `powershell.exe`）與 macOS 開發機（`pwsh`），涵蓋目標平台。
  * 若哪天第 ①② 也變成需要 PowerShell，那就是真的重犯了——故第 ①② 刻意不 import 任何
    PowerShell 相依。
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TESTS_DIR))
from _platform_helpers import powershell_exe  # noqa: E402
from _ps_source import (  # noqa: E402
    GOLDEN_PATH,
    load_golden,
    normalize_ps_source,
    strip_by_comment_spans,
    strip_ps_comments,
)

_GEN_PATH = _REPO_ROOT / "tools" / "gen_ps_comment_golden.py"


def _load_generator():
    """以檔案路徑載入產生器模組（它在 `tools/` 而非 `tools/tests/`，不走一般 import）。"""
    spec = importlib.util.spec_from_file_location("gen_ps_comment_golden", _GEN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tracked_ps1() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.ps1"],
        cwd=_REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return sorted(ln.strip() for ln in out.splitlines() if ln.strip())


def _at_risk_consumers() -> list[str]:
    """機械掃出「會受這個 fail-open 影響」的靜態鎖檔名（凡 import `_ps_source` 剝除函式者）。

    刻意用 AST 掃描而非寫死清單：寫死的名冊會過期，而過期的名冊會讓差分翻紅時的訊息指向
    錯誤的檔案——那比沒有訊息更糟（本 repo 反覆抓到「名冊 stale」形態）。
    """
    consumers: list[str] = []
    for path in sorted(_TESTS_DIR.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - 語法壞掉由別的閘門負責
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "_ps_source"
                and any(a.name in ("strip_ps_comments", "strip_by_comment_spans")
                        for a in node.names)
            ):
                consumers.append(path.name)
                break
    return consumers


class GoldenFreshnessTest(unittest.TestCase):
    """第 ① 層：golden 必須涵蓋現況全語料且未過期（fail-closed，不需要 PowerShell）。"""

    def test_golden_covers_every_tracked_ps1_with_matching_sha(self) -> None:
        golden = load_golden()
        recorded = golden["files"]
        problems: list[str] = []
        for rel in _tracked_ps1():
            entry = recorded.get(rel)
            if entry is None:
                problems.append(f"新增的 .ps1 未登記：{rel}")
                continue
            actual = hashlib.sha256(
                normalize_ps_source((_REPO_ROOT / rel).read_bytes()).encode("utf-8")
            ).hexdigest()
            if actual != entry["sha256"]:
                problems.append(f"內容已變動但 golden 未重生：{rel}")
        for rel in sorted(set(recorded) - set(_tracked_ps1())):
            problems.append(f"golden 仍登記已不存在／已不 tracked 的檔案：{rel}")
        self.assertEqual(
            problems, [],
            "PowerShell 註解 golden 已過期——請在有 PowerShell 的機器上跑 "
            "`python tools/gen_ps_comment_golden.py` 重生後一併提交。"
            "（Windows 出廠的 powershell.exe 即可，不需要 pwsh 7）\n"
            + "\n".join(f"  - {p}" for p in problems),
        )

    def test_all_tracked_ps1_parse_with_zero_errors(self) -> None:
        """全語料在真 parser 下必須零 parse error（由 golden 凍結，離線可驗）。

        這條順帶補上了一個此前只有「有 pwsh 才跑」的守門面：R58 動工時
        `test_install_windows_nightly.py` 的語法解析在 Windows 11 出廠組態（只有 PS 5.1）下
        恆 skip（DEF-101-507）。本斷言把「能不能 parse」對**全 137 支**做成離線事實，
        任何平台都會驗，且涵蓋面遠大於原本的單一檔案。
        """
        golden = load_golden()
        bad = {k: v["parseErrors"] for k, v in golden["files"].items() if v["parseErrors"]}
        self.assertEqual(
            bad, {},
            f"以下 .ps1 在真 PowerShell parser 下有語法錯誤（引擎 {golden['engine']}）："
            f"{bad}——語法錯誤的腳本在使用者機器上會直接失敗",
        )


class GoldenDiffTest(unittest.TestCase):
    """第 ② 層：近似法 vs ground truth 的逐檔差分（fail-closed，不需要 PowerShell）。"""

    def test_approximation_matches_ground_truth_on_whole_corpus(self) -> None:
        """逐檔差分。

        🔴 **只比對 sha256 相符的檔案**（R58 落地當下就踩到、故留痕）：golden 的 span 是
        offset，一旦檔案內容變動而 golden 未重生，舊 offset 套在新內容上必然切錯位置 →
        差分會報出**誤導性的「分歧」**，讓人以為近似法有 fail-open，實際只是 golden 過期。
        過期本身由 `GoldenFreshnessTest` 負責翻紅（訊息會指路重生），此處刻意讓位、不重複
        報，並把跳過的檔案數寫進失敗訊息，避免「跳過」變成靜默縮小掃描面。
        """
        golden = load_golden()
        diverged: list[str] = []
        stale: list[str] = []
        for rel, entry in sorted(golden["files"].items()):
            path = _REPO_ROOT / rel
            if not path.is_file():  # 檔案已消失：同樣由 GoldenFreshnessTest 負責報
                stale.append(rel)
                continue
            text = normalize_ps_source(path.read_bytes())
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != entry["sha256"]:
                stale.append(rel)
                continue
            spans = [(s, e) for s, e in entry["commentSpans"]]
            if strip_ps_comments(text) != strip_by_comment_spans(text, spans):
                diverged.append(rel)
        stale_note = (
            f"\n（另有 {len(stale)} 支檔案因 golden 過期而未參與本次差分：{stale}——"
            "請先依 GoldenFreshnessTest 的指示重生 golden，再回頭看本測試）" if stale else ""
        )
        self.assertEqual(
            diverged, [],
            "近似法 `_ps_source.strip_ps_comments()` 與真 PowerShell parser 對下列檔案的判定"
            f"已分歧：{diverged}\n"
            "這代表這些檔案裡出現了近似法漏剝（或多剝）的註解形態。**方向通常是 fail-open**"
            "（漏剝＝註解冒充功能碼），受影響的靜態鎖會假綠——即「功能碼被刪掉、只在註解裡"
            f"留下字樣」也照樣全綠。目前依賴該剝除器的靜態鎖：{_at_risk_consumers()}。\n"
            "🔴 修法**不是**往 `_ps_source._PS_COMMENT_LEAD` 補字元（那是 whack-a-mole，"
            "R57 已定案禁止，理由見該常數上方註解），而是：①改寫那支 `.ps1` 避開該形態"
            "（成本最低、且那些形態多半可讀性也差），或②若該形態確實必要，則讓受影響的"
            "靜態鎖改吃 golden 的 span（`strip_by_comment_spans`）而非近似法，"
            "並把此決策記入缺陷帳本。" + stale_note,
        )


class Utf16OffsetConversionTest(unittest.TestCase):
    """鎖住產生器最容易被誤刪的一段：UTF-16 code unit → code point 換算。

    R58 實測：不做換算時 137 支中 62 支長度不符、逾半數 span 切出來不是註解（量測取自落地前
    語料，僅證明現象存在；span 總數不在此寫死，唯一真相源是 `ps_comment_golden.json`）。
    這種錯位是**靜默**的（golden 看起來很正常、只是內容全錯），故必須有直接的單元測試，
    不能只靠「產生器跑得起來」。
    """

    def test_astral_plane_char_shifts_offsets(self) -> None:
        gen = _load_generator()
        # 🔴 是 U+1F534（星體平面）：.NET 算 2 個 UTF-16 單位、Python 算 1 個 code point。
        text = '$a = "🔴"  # note\n'
        mapping = gen.utf16_to_codepoint(text)
        self.assertEqual(len(mapping), len(text.encode("utf-16-le")) // 2 + 1)
        # 真 parser 會回報註解起點在 UTF-16 offset 12（emoji 佔兩格）；code point 應為 11。
        utf16_comment_start = len('$a = "'.encode("utf-16-le")) // 2 + 2 + len('"  '.encode("utf-16-le")) // 2
        self.assertEqual(text[mapping[utf16_comment_start]], "#")
        # 反向對照：直接把 UTF-16 offset 當 code point 索引用會切錯（本坑的實證）。
        self.assertNotEqual(text[utf16_comment_start], "#")

    def test_pure_ascii_mapping_is_identity(self) -> None:
        gen = _load_generator()
        text = "$a = 1  # note\n"
        mapping = gen.utf16_to_codepoint(text)
        self.assertEqual(mapping, list(range(len(text) + 1)))


class TestGoldenSerializationIsStable(unittest.TestCase):
    """鎖住 `_dump()` 的手工序列化（每檔一行）：可被 `json.loads` 還原、且冪等。

    手工組裝 JSON 的風險是「產生了無法解析或不穩定的檔案」，那會讓 golden 在某次重生後
    悄悄壞掉。故直接對磁碟上的實體檔做往返比對。
    """

    def test_disk_golden_roundtrips_through_dump(self) -> None:
        gen = _load_generator()
        raw = GOLDEN_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(
            gen._dump(data), raw,
            "磁碟上的 golden 與 `_dump()` 的輸出不一致——golden 可能被手工編輯過，"
            "或序列化格式已變更而未重生。請跑 `python tools/gen_ps_comment_golden.py`",
        )

    def test_every_span_is_an_ordered_pair(self) -> None:
        golden = load_golden()
        for rel, entry in golden["files"].items():
            for span in entry["commentSpans"]:
                with self.subTest(file=rel, span=span):
                    self.assertEqual(len(span), 2)
                    self.assertLess(span[0], span[1])


class DiffDetectorSelfTest(unittest.TestCase):
    """偵測器自驗：差分邏輯真的抓得到 fail-open，而不是恆綠。

    這是本 repo 既有慣例（見 `test_python_c_percent_shim.py` 的偵測器自驗）：一支「掃全語料
    都沒發現問題」的測試，必須自己證明它在有問題時會翻紅，否則無從分辨「乾淨」與「壞掉」。
    """

    def test_known_fail_open_form_is_detected(self) -> None:
        """`$a = 1#c` 是 R57 量測到的 fail-open 形態之一：真 parser 認定 `#c` 是註解，
        近似法因 `1` 不在 `_PS_COMMENT_LEAD` 內而整段保留。"""
        text = "$a = 1#c\n"
        ground_truth_spans = [(6, 8)]  # `#c`
        self.assertEqual(strip_by_comment_spans(text, ground_truth_spans), "$a = 1")
        self.assertEqual(strip_ps_comments(text), "$a = 1#c")
        self.assertNotEqual(
            strip_ps_comments(text), strip_by_comment_spans(text, ground_truth_spans),
            "差分邏輯必須能分辨這兩者，否則整支差分測試恆綠、零鑑別力",
        )

    def test_agreeing_form_produces_no_divergence(self) -> None:
        """反向：近似法處理得對的形態不得被誤報成分歧（避免偽陽性癱瘓這道鎖）。"""
        text = "$a = 1  # c\n"
        self.assertEqual(
            strip_ps_comments(text), strip_by_comment_spans(text, [(8, 11)])
        )

    def test_at_risk_consumer_list_is_not_empty(self) -> None:
        """受影響消費端名冊由 AST 掃出；空清單代表掃描壞了（或剝除器已無人使用）。

        兩種情況都必須有人知道：前者是鎖壞了，後者代表整套機制可以退休。
        """
        self.assertTrue(
            _at_risk_consumers(),
            "掃不到任何 import `_ps_source` 剝除函式的靜態鎖——若剝除器真的已無消費端，"
            "本檔與 golden 機制應一併評估退休；若不是，則本掃描已失效",
        )


# R58 round 2 ARCH-R58R2-05：本條原自寫 `which("powershell") is None and which("pwsh") is None`
# ——那是同一輪內第四份手寫的 PowerShell 可用性判定，而本輪才剛把 `powershell_exe()` 立為 SSOT。
# 行為等價（`powershell_exe() is None` ⇔ 兩名皆 None），但重複本身就是下一輪漂移的來源。
@unittest.skipUnless(
    powershell_exe(),
    "本機無 powershell 也無 pwsh，跳過 golden 真實性複驗（第 ①② 層離線斷言仍會跑，"
    "見本檔 docstring 對此非對稱性的說明）",
)
class GoldenAuthenticityTest(unittest.TestCase):
    """第 ③ 層：現場重新 parse，確認 golden 沒被手改、且本機引擎與產生它的引擎不分歧。

    這是唯一需要 PowerShell 的一層；為何它的 skip 不構成「守門在目標平台失效」，見本檔
    docstring 的三層表格與紅字說明。
    """

    def test_live_parser_reproduces_golden_spans(self) -> None:
        """現場 parse vs golden。

        與 `GoldenDiffTest` 同一個讓位規則：**只比對 sha256 相符的檔案**。內容變動而 golden
        未重生時，現場 parse 的 span 當然與 golden 不同——那是「過期」不是「不真實」，若在此
        翻紅會把讀者導向錯誤的兩個假設（手改／引擎分歧），實際原因卻是第三個。過期由
        `GoldenFreshnessTest` 專責。
        """
        gen = _load_generator()
        golden = load_golden()
        fresh = [
            rel for rel, entry in golden["files"].items()
            if (_REPO_ROOT / rel).is_file()
            and hashlib.sha256(
                normalize_ps_source((_REPO_ROOT / rel).read_bytes()).encode("utf-8")
            ).hexdigest() == entry["sha256"]
        ]
        skipped = sorted(set(golden["files"]) - set(fresh))
        if not fresh:
            self.skipTest("golden 全數過期，無可比對對象（見 GoldenFreshnessTest）")
        rebuilt, engine = gen.collect_spans(sorted(fresh))
        mismatched = [
            rel for rel in sorted(fresh)
            if rebuilt[rel]["commentSpans"] != golden["files"][rel]["commentSpans"]
        ]
        skip_note = (
            f"\n（另有 {len(skipped)} 支因 golden 過期未參與比對：{skipped}）" if skipped else ""
        )
        self.assertEqual(
            mismatched, [],
            f"現場以 {engine} 重新 parse 的 comment span 與 golden（產生引擎 "
            f"{golden['engine']}）不符：{mismatched}\n"
            "兩種可能：①golden 被手工編輯過 → 重生即可；②本機 PowerShell 引擎與產生 golden "
            "的引擎對這些檔案的 tokenize 結果真的不同 → 這本身是重要發現，請記入缺陷帳本"
            "並決定以哪個引擎為權威（判準：這些 .ps1 的目標執行環境是使用者的 "
            "Windows PowerShell 5.1）" + skip_note,
        )


if __name__ == "__main__":
    unittest.main()
