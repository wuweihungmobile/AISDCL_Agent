"""root-infra-ci.yml ↔ pre-push root-infra leg 守門清單同步鎖（R10 ARCH-2，DEF-101-132）。

WHY（測意圖非僅行為，Rule 9）：
root-infra-ci.yml 的守門 step 與本地 pre-push dispatcher root-infra leg 的守門
清單是兩份獨立硬編碼——R11 若新增第五支守門工具進 CI 而忘改 pre-push，本地
永遠不跑新守門且無任何 diff 訊號（兩處各自綠燈）。本測試機械斷言：
  1. CI 內每個 `python3 tools/<x>.py` 具名守門呼叫，pre-push 內必有對應呼叫
     （DEF-101-112 已明文豁免的四道非 python 步驟不在此列：pwsh parse+BOM、
     EOL(.sh)、EOL(.ps1)、bash -n push 全量——它們不是 `python3 tools/*.py` 形狀，
     天然不進抽取集合；若未來以 python 工具重寫，會自動落入本鎖）。
  2. pre-push 的根層消費檔清單必須機械讀取 aisdlc-sdd-ci.yml（單一真相源），
     不得退化回手抄第二份清單（R10 ARCH-1 接線的防復發鎖）。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml"
_SDD_CI_YML = _REPO_ROOT / ".github" / "workflows" / "aisdlc-sdd-ci.yml"
_PRE_PUSH = _REPO_ROOT / "tools" / "git-hooks" / "pre-push"

_PY_TOOL_RE = re.compile(r"python3?\s+(tools/[A-Za-z0-9_]+\.py)")
# 與 pre-push 消費檔抽取管線同形狀：只認 `- "…"` 雙引號條目（bash 端 grep -E
# '^[[:space:]]*-[[:space:]]*"'）——本 regex 刻意鏡射該限制以便下方下限鎖生效。
_QUOTED_PATH_ENTRY_RE = re.compile(r'^\s*-\s*"([^"]+)"\s*$')


def _yml_python_tools() -> set[str]:
    """抽取 root-infra-ci.yml 內的 `python3 tools/<x>.py` 具名守門呼叫。

    只掃非註解行（yml 檔頭大段說明不算接線）；py_compile 走 `python3 -m`
    形狀、天然不入集合（其 pre-push 對等由 dispatcher 測試覆蓋）。
    """
    tools: set[str] = set()
    for line in _CI_YML.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        for match in _PY_TOOL_RE.finditer(line):
            tools.add(match.group(1))
    return tools


class TestRootInfraParity(unittest.TestCase):
    def test_ci_python_guards_all_wired_in_pre_push(self) -> None:
        ci_tools = _yml_python_tools()
        self.assertGreaterEqual(
            len(ci_tools), 5,
            f"root-infra-ci.yml 抽取到的具名 python 守門異常地少：{sorted(ci_tools)}——"
            f"抽取 pattern 或 yml 疑似被改壞（數量下限釘選精神）",
        )
        # R10 二審 Architect P4 硬化：只比對 pre-push 的「非註解行」——守門工具名
        # 若只殘留在註解裡不得滿足本鎖（子字串比對的假綠縫）。
        pre_push_exec_text = "\n".join(
            line for line in _PRE_PUSH.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        missing = sorted(t for t in ci_tools if t not in pre_push_exec_text)
        self.assertEqual(
            missing, [],
            f"CI 有、本地 pre-push root-infra leg 無（非註解行）：{missing}——"
            f"新增守門工具須同步接線（R9 root-infra leg 的存在理由：CI 停擺期間本地是唯一防線）",
        )

    def test_sdd_ci_yml_consumer_paths_extractable_with_floor(self) -> None:
        """R10 二審 Architect P3：pre-push 消費檔抽取只認雙引號 `- "…"` 條目——
        若真實 aisdlc-sdd-ci.yml 的 paths 條目改成單引號/裸字串（合法 YAML、GitHub
        照常解析），本地抽取靜默變空、消費檔 leg 整條蒸發且零紅燈。本鎖以同形狀
        regex 抽真實 yml，斷言非 AISDLC_SDD 消費檔條目數 ≥5（現況 5 條）——條目
        改寫引號風格或刪減時本測試翻紅，強制同步 pre-push 抽取管線。"""
        entries: set[str] = set()
        for line in _SDD_CI_YML.read_text(encoding="utf-8").splitlines():
            m = _QUOTED_PATH_ENTRY_RE.match(line)
            if m:
                entries.add(m.group(1))
        consumers = sorted(
            e for e in entries
            if not e.startswith("AISDLC_SDD/") and not e.startswith(".github/workflows/")
        )
        self.assertGreaterEqual(
            len(consumers), 5,
            f"aisdlc-sdd-ci.yml 以雙引號形狀抽出的根層消費檔僅 {consumers}——"
            f"若刻意改寫條目引號風格，必須同步 tools/git-hooks/pre-push 的抽取管線"
            f"（否則消費檔 leg 靜默蒸發）",
        )

    def test_pre_push_consumer_list_reads_sdd_ci_yml(self) -> None:
        pre_push_text = _PRE_PUSH.read_text(encoding="utf-8")
        self.assertIn(
            "aisdlc-sdd-ci.yml", pre_push_text,
            "pre-push 的根層消費檔清單必須機械讀取 aisdlc-sdd-ci.yml（單一真相源），"
            "不得退化為手抄清單（R10 ARCH-1）",
        )
        self.assertIn(
            "scripts/tests", pre_push_text,
            "消費檔命中時必須補跑 AISDLC_SDD/scripts/tests 回歸鎖（R10 ARCH-1）",
        )
        # R10 二審 SD P3 錨點：清單 SSOT 自身變更也必須觸發消費檔 leg
        self.assertIn(
            ".github/workflows/aisdlc-sdd-ci.yml) run_sdd_consumer=1", pre_push_text,
            "pre-push 必須在 push 涉 aisdlc-sdd-ci.yml 自身時觸發消費檔 leg——"
            "清單被改壞時守它的 meta 鎖住在 SDD suite，否則零機械訊號",
        )


if __name__ == "__main__":
    unittest.main()
