#!/usr/bin/env python3
"""ONBOARDING.md ↔ check_script_parity 單邊豁免清單機械互鎖（R15 DEF-101-204）。

WHY：ONBOARDING.md 的人工對照敘述（§6 bash-only 工具清單、§8 ops 排程家族
清單）與 `tools/check_script_parity.py` 的 `_SINGLE_SIDED_EXEMPT` 機械清單
互相宣稱同一件事，但 R15 前零互鎖——單邊增刪（文件加了一支 bash-only 工具
而 parity 未登記、或 parity 移了豁免而文件仍宣稱）無任何機械訊號。本測試
以抽取式互鎖（手法鏡射 test_smoke_ci_sync.py）比對兩側集合相等。

範圍刻意縮至兩條明文清單（全集合相等會誤傷——_SINGLE_SIDED_EXEMPT 尚有
smoke 異名對等品等不對應 ONBOARDING 行內清單的條目）：
  抽取①：ONBOARDING §6「bash-only 工具」行內反引號 `*.sh` 路徑集合
    （「各版 `tools/verify_traceability.sh`」正規化為 parity 的
    LATEST/tools/… key 格式）＝＝ _SINGLE_SIDED_EXEMPT 中 rationale 含
    「bash-only」的鍵集合。判準取「bash-only」而非「ONBOARDING §6」：
    LATEST/tools/verify_traceability.sh 的 rationale 寫「bash-only legacy…」
    未引 §6 字樣，但 ONBOARDING §6 行以「各版」明文涵蓋之——以家族語意
    「bash-only」取鍵恰為兩側同一集合（親讀鍵格式後定案）。
  抽取②：ONBOARDING §8「ops 排程家族」行內反引號 `*.ps1` 檔名集合
    ＝＝ _SINGLE_SIDED_EXEMPT 中 .ps1 鍵且 rationale 含「schtasks」或「§8」
    的鍵集合（鍵帶 `AutoClaude/tools/` 前綴，比對時正規化為檔名；
    install_mac_nightly.sh 的 rationale 亦含 schtasks 但為 .sh 鍵，
    以副檔名過濾排除）。

抽取數量下限釘選（＝2026-07-20 實測值：①6、②3）：宣告 pattern 漂移
（措辭改寫/反引號拆掉）時 0 命中即紅、fail-loud 不縮面（比照
check_script_parity._MIN_EXTRACT_COUNTS 慣例）；錨定行數量亦鎖恰一行，
文件改組時紅燈指路同步本案。
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"

sys.path.insert(0, str(_REPO_ROOT / "tools"))
import check_script_parity as _parity  # noqa: E402

# 抽取數量下限釘選＝2026-07-20 實測值；刻意刪減清單條目時同步下修。
_MIN_EXTRACT = {"bash_only": 6, "sched_family": 3}
# 反引號 token（含可選「各版」前綴——§6 以此指涉隨版繼承的 LATEST 工具）
_TOKEN_RE = re.compile(r"(各版\s*)?`([^`]+)`")


def _anchor_line(text: str, needle: str) -> str:
    """取唯一錨定行；0 行或多行皆 fail-loud（文件改組須同步本案）。"""
    lines = [line for line in text.splitlines() if needle in line]
    if len(lines) != 1:
        raise AssertionError(
            f"ONBOARDING.md 錨定行「{needle}」命中 {len(lines)} 行（預期恰 1）——"
            f"文件敘述已改組，請同步更新本互鎖的錨定與抽取規則"
        )
    return lines[0]


def extract_bash_only_keys(text: str) -> set[str]:
    """抽取①：§6 bash-only 行的 `*.sh` 路徑集合（正規化為 parity 鍵格式）。

    過濾規則：token 須以 .sh 結尾且不含空白（排除「`bash xxx.sh`」示例指令）；
    帶「各版」前綴者正規化為 LATEST/<path>（對齊 _SINGLE_SIDED_EXEMPT 的
    LATEST/tools/… 鍵慣例）。
    """
    line = _anchor_line(text, "bash-only 工具")
    keys: set[str] = set()
    for m in _TOKEN_RE.finditer(line):
        tok = m.group(2)
        if not tok.endswith(".sh") or " " in tok or tok == ".sh":
            continue
        keys.add(f"LATEST/{tok}" if m.group(1) else tok)
    if len(keys) < _MIN_EXTRACT["bash_only"]:
        raise AssertionError(
            f"§6 bash-only 行僅抽取到 {len(keys)} 個 .sh token < 下限 "
            f"{_MIN_EXTRACT['bash_only']}——宣告 pattern 疑似漂移（靜默縮面）；"
            f"刻意刪減請同步下修 _MIN_EXTRACT['bash_only']"
        )
    return keys


def extract_sched_ps1_names(text: str) -> set[str]:
    """抽取②：§8 ops 排程家族行的 `*.ps1` 檔名集合。"""
    line = _anchor_line(text, "ops 排程家族")
    names = {
        m.group(2)
        for m in _TOKEN_RE.finditer(line)
        if m.group(2).endswith(".ps1") and " " not in m.group(2) and m.group(2) != ".ps1"
    }
    if len(names) < _MIN_EXTRACT["sched_family"]:
        raise AssertionError(
            f"§8 ops 排程家族行僅抽取到 {len(names)} 個 .ps1 token < 下限 "
            f"{_MIN_EXTRACT['sched_family']}——宣告 pattern 疑似漂移（靜默縮面）；"
            f"刻意刪減請同步下修 _MIN_EXTRACT['sched_family']"
        )
    return names


def parity_bash_only_keys() -> set[str]:
    """機械側①：_SINGLE_SIDED_EXEMPT 中 rationale 含「bash-only」的鍵集合。

    R63（ADR-XPLAT-002 Phase 1-C (b)）：值由純字串升級為 `(tier, reason)` 二元組，
    取 `why[1]`（reason）做字串比對——語意與升級前不變。"""
    return {
        key
        for key, why in _parity._SINGLE_SIDED_EXEMPT.items()
        if "bash-only" in why[1]
    }


def parity_sched_ps1_names() -> set[str]:
    """機械側②：.ps1 鍵且 rationale 含 schtasks/§8 的鍵集合（正規化為檔名）。"""
    return {
        key.rsplit("/", 1)[-1]
        for key, why in _parity._SINGLE_SIDED_EXEMPT.items()
        if key.endswith(".ps1") and ("schtasks" in why[1] or "§8" in why[1])
    }


class TestOnboardingParityInterlock(unittest.TestCase):
    def test_bash_only_claims_match_parity_exemptions(self) -> None:
        """§6 bash-only 工具清單 == parity 單邊豁免 bash-only 鍵集合。"""
        doc = extract_bash_only_keys(_ONBOARDING.read_text(encoding="utf-8-sig"))
        mech = parity_bash_only_keys()
        self.assertEqual(
            doc,
            mech,
            f"ONBOARDING §6 bash-only 清單與 check_script_parity._SINGLE_SIDED_EXEMPT "
            f"（rationale 含 bash-only）不一致——單邊改動請同步另一側：\n"
            f"  僅文件有：{sorted(doc - mech)}\n  僅機械清單有：{sorted(mech - doc)}",
        )

    def test_sched_family_claims_match_parity_exemptions(self) -> None:
        """§8 ops 排程家族 .ps1 清單 == parity 單邊豁免 schtasks 家族鍵集合。"""
        doc = extract_sched_ps1_names(_ONBOARDING.read_text(encoding="utf-8-sig"))
        mech = parity_sched_ps1_names()
        self.assertEqual(
            doc,
            mech,
            f"ONBOARDING §8 排程家族清單與 check_script_parity._SINGLE_SIDED_EXEMPT "
            f"（.ps1 且 rationale 含 schtasks/§8）不一致——單邊改動請同步另一側：\n"
            f"  僅文件有：{sorted(doc - mech)}\n  僅機械清單有：{sorted(mech - doc)}",
        )

    # ── 以下以合成文本自證抽取器紅綠（不落 repo 樹內、不碰 ONBOARDING.md）──

    def test_missing_anchor_fails_loud(self) -> None:
        """錨定行消失（文件改組）→ fail-loud，不得靜默 0 命中假綠。"""
        with self.assertRaisesRegex(AssertionError, "命中 0 行"):
            extract_bash_only_keys("# 無關內容\n沒有錨定字樣的段落\n")

    def test_duplicate_anchor_fails_loud(self) -> None:
        """錨定行重複（新增第二處敘述）→ fail-loud，防抽錯行。"""
        line = "ops 排程家族：`a.ps1`、`b.ps1`、`c.ps1`"
        with self.assertRaisesRegex(AssertionError, "命中 2 行"):
            extract_sched_ps1_names(f"{line}\n{line}\n")

    def test_pattern_drift_zero_hits_fails_loud(self) -> None:
        """錨定行仍在但反引號 token 被改寫（0/不足額命中）→ 下限釘選紅燈。"""
        with self.assertRaisesRegex(AssertionError, "下限"):
            extract_bash_only_keys("bash-only 工具：清單改寫成無反引號敘述\n")

    def test_extraction_normalizations(self) -> None:
        """合成行驗證正規化規則：各版→LATEST/、含空白示例與非 .sh 排除。"""
        keys = extract_bash_only_keys(
            "bash-only 工具（無 `.ps1` 對等）：`A/x.sh`、`B/y.sh`、`C/z.sh`、"
            "`D/w.sh`、`E/v.sh`、各版 `tools/u.sh`（`bash xxx.sh` 執行）\n"
        )
        self.assertEqual(
            keys,
            {"A/x.sh", "B/y.sh", "C/z.sh", "D/w.sh", "E/v.sh", "LATEST/tools/u.sh"},
        )


if __name__ == "__main__":
    unittest.main()
