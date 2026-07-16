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
_PRE_PUSH = _REPO_ROOT / "tools" / "git-hooks" / "pre-push"

_PY_TOOL_RE = re.compile(r"python3?\s+(tools/[A-Za-z0-9_]+\.py)")


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
        pre_push_text = _PRE_PUSH.read_text(encoding="utf-8")
        missing = sorted(t for t in ci_tools if t not in pre_push_text)
        self.assertEqual(
            missing, [],
            f"CI 有、本地 pre-push root-infra leg 無：{missing}——新增守門工具須同步接線"
            f"（R9 root-infra leg 的存在理由：CI 停擺期間本地是唯一防線）",
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


if __name__ == "__main__":
    unittest.main()
