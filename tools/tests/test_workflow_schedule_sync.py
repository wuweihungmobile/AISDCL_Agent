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

R15 SCAN-C-9：`_IF_REF_RE` 無行首錨定、掃全文——若未來刪 job 時留下含
`github.event.schedule == '...'` 字樣的整行註解（本檔 dormant cron 註記慣例正是
這種形態），集合仍相等、cron 白燒 runner 而零訊號。修法：比對前先剝除「整行註解」
（`\\s*#` 起頭的行）。取捨說明：只剝整行、不剝行尾註解——(1) 行尾註解形態在受掃
workflow 現況不存在，主要風險面（刪 job 留整行註解）已被覆蓋；(2) 行尾剝法需分辨
字串常值內的 `#`（如 cron 欄位雖不含 # 但 run 指令行可能含），保守整行剝除
零誤剝風險。若未來出現行尾註解含 schedule 字樣的形態，再擴充剝法。
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


def _strip_full_line_comments(text: str) -> str:
    """剝除 YAML 整行註解（`\\s*#` 起頭的行），防註解殘骸誤入集合比對。

    R15 SCAN-C-9：不剝行尾註解——取捨理由見模組 docstring。
    """
    return "\n".join(
        ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
    )


class TestWorkflowScheduleSync(unittest.TestCase):
    def test_cron_and_if_reference_sets_are_equal(self) -> None:
        for rel in _WORKFLOWS_WITH_CRON_IF_PAIRING:
            path = _REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"workflow 缺席：{rel}（掃描面不得靜默縮小）")
            text = _strip_full_line_comments(path.read_text(encoding="utf-8"))
            crons = set(_CRON_RE.findall(text))
            refs = set(_IF_REF_RE.findall(text))
            self.assertTrue(crons, f"{rel}：未抽到任何 active cron——regex 或檔案結構疑似改版")
            self.assertEqual(
                refs, crons,
                f"{rel}：schedule cron 集合與 job if 引用字串集合不一致——"
                f"改 cron 忘 if（job 永不觸發）或加 cron 忘 job（白燒 runner）。"
                f"cron={sorted(crons)}，if 引用={sorted(refs)}",
            )

    def test_comment_residue_not_counted_as_reference(self) -> None:
        """R15 SCAN-C-9 自證：刪 job 留下的整行註解殘骸不得再被計為 if 引用。

        先前 _IF_REF_RE 掃全文含註解：真 job 刪除後只要註解殘骸仍含
        `github.event.schedule == '...'` 字樣，集合照樣相等（假綠）。
        """
        cron_and_job = (
            "on:\n"
            "  schedule:\n"
            '    - cron: "0 9 * * 1"\n'
            "jobs:\n"
            "  # 殘骸範例：if: github.event.schedule == '0 9 * * 1'\n"
            "  real:\n"
            "    if: github.event.schedule == '0 9 * * 1'\n"
        )
        stripped = _strip_full_line_comments(cron_and_job)
        # 真 job 在場：剝註解後引用仍抽得到（不誤剝有效行）
        self.assertEqual(set(_IF_REF_RE.findall(stripped)), {"0 9 * * 1"})
        self.assertEqual(set(_CRON_RE.findall(stripped)), {"0 9 * * 1"})
        # 真 job 已刪、只剩註解殘骸：引用集合須為空 → 與 cron 集合不等 → 守門紅
        job_deleted = cron_and_job.replace(
            "  real:\n    if: github.event.schedule == '0 9 * * 1'\n", ""
        )
        stripped_deleted = _strip_full_line_comments(job_deleted)
        self.assertEqual(set(_IF_REF_RE.findall(stripped_deleted)), set())
        self.assertEqual(set(_CRON_RE.findall(stripped_deleted)), {"0 9 * * 1"})


if __name__ == "__main__":
    unittest.main()
