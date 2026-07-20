"""GitHub Actions schedule cron ↔ job if 比對字串同步機械鎖（R14 QA-R14-REV-2）。

WHY（測意圖非僅行為，Rule 9）：
`autoclaude-ci.yml` 的 nightly job 以 `github.event.schedule == '<cron>'` 過濾自身
cron（DEF-01-004 修復模式）——代價是 cron 與 if 字串**逐字耦合**：改 cron 忘改 if
＝該 job 從此永不觸發且零告警（R14 降頻時三處 if 同步改，變更註記自承此風險；
本 repo 先前對此零機械鎖，只靠人工記得）。本測試把耦合鎖成雙向集合相等：

  1. 每個被 if 引用的 cron 字串必須存在於 schedule 區塊（防「改 cron 忘 if」）。
  2. 每個 schedule cron 必須被至少一個 if 引用（防「加 cron 忘 job / 刪 job 忘 cron」
     ——未被引用的 cron 會觸發整個 workflow 卻無對應 nightly job，push 閘四 job 又
     已 `!= 'schedule'` 過濾，等於白燒 runner 冷啟動）。

以 regex 抽取而非 yaml 解析：零第三方依賴（根層 unittest 環境不保證 pyyaml），
且 `# - cron:` 註解態（dormant）天然不被行首錨定匹配吸入。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 目前唯一「多 cron × per-job if 過濾」形態的 workflow；新增同形態檔時加入此清單。
_WORKFLOWS_WITH_CRON_IF_PAIRING = [".github/workflows/autoclaude-ci.yml"]

_CRON_RE = re.compile(r'^\s*- cron: "([^"]+)"', re.MULTILINE)
_IF_REF_RE = re.compile(r"github\.event\.schedule == '([^']+)'")


class TestWorkflowScheduleSync(unittest.TestCase):
    def test_cron_and_if_reference_sets_are_equal(self) -> None:
        for rel in _WORKFLOWS_WITH_CRON_IF_PAIRING:
            path = _REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"workflow 缺席：{rel}（掃描面不得靜默縮小）")
            text = path.read_text(encoding="utf-8")
            crons = set(_CRON_RE.findall(text))
            refs = set(_IF_REF_RE.findall(text))
            self.assertTrue(crons, f"{rel}：未抽到任何 active cron——regex 或檔案結構疑似改版")
            self.assertEqual(
                refs, crons,
                f"{rel}：schedule cron 集合與 job if 引用字串集合不一致——"
                f"改 cron 忘 if（job 永不觸發）或加 cron 忘 job（白燒 runner）。"
                f"cron={sorted(crons)}，if 引用={sorted(refs)}",
            )


if __name__ == "__main__":
    unittest.main()
