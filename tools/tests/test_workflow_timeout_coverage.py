"""GitHub Actions 所有 job 必須宣告 timeout-minutes 的機械鎖（R14 QA-R14-RR-1）。

WHY（測意圖非僅行為，Rule 9）：
無 timeout 的 job 卡死時燒滿 GitHub 預設上限 360 分鐘 runner——帳務停擺＋額度緊縮
（CI-2 裁決主題）下風險放大。R14 SCAN-CI-5 曾以「全 repo 唯一無 timeout」人工目視
宣稱補了一個 job，複審 QA-R14-RR-1 用機械掃描打破此宣稱：實際尚有 3 個輕量 alert/
lock job 無 timeout。本測試把「所有 job 皆有 timeout-minutes」從人工數改為機械鎖，
新增 job 忘記宣告即紅、且杜絕未來同類「唯一/都有」的人工計數誤判。

以行首錨定的縮排解析抽 job（零第三方依賴，根層 unittest 環境不保證 pyyaml），
`# ` 註解態 job 天然不被匹配。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_DIR = _REPO_ROOT / ".github" / "workflows"

_JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
_TIMEOUT_RE = re.compile(r"^    timeout-minutes:\s*\d+")


def _jobs_missing_timeout(path: Path) -> list[str]:
    """回傳該 workflow 中缺 timeout-minutes 的 job 名清單。

    解析法：進入 `jobs:` 區塊後，2-space 縮排的 `<name>:` 為 job 起點，
    4-space 的 `timeout-minutes:` 屬該 job。job step 內容縮排更深不會誤匹配。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    in_jobs = False
    jobs: dict[str, bool] = {}
    cur: str | None = None
    for ln in lines:
        if re.match(r"^jobs:\s*$", ln):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        # 回到頂層 key（無縮排且非註解）即離開 jobs 區塊
        if re.match(r"^[A-Za-z]", ln):
            break
        m = _JOB_RE.match(ln)
        if m:
            cur = m.group(1)
            jobs[cur] = False
            continue
        if cur and _TIMEOUT_RE.match(ln):
            jobs[cur] = True
    return [j for j, has in jobs.items() if not has]


class TestWorkflowTimeoutCoverage(unittest.TestCase):
    def test_all_jobs_declare_timeout(self) -> None:
        workflows = sorted(_WORKFLOW_DIR.glob("*.yml"))
        self.assertTrue(workflows, "未發現任何 workflow——掃描面疑似縮小或路徑改版")
        offenders: dict[str, list[str]] = {}
        for wf in workflows:
            missing = _jobs_missing_timeout(wf)
            if missing:
                offenders[wf.name] = missing
        self.assertEqual(
            offenders, {},
            "以下 workflow job 未宣告 timeout-minutes（卡死將燒滿 GitHub 預設 360 分鐘 "
            "runner，額度風險）——請於 job 層級補 timeout-minutes：\n"
            + "\n".join(f"  {wf}: {jobs}" for wf, jobs in offenders.items()),
        )

    def test_parser_detects_missing_timeout(self) -> None:
        """自證判準紅綠（防「零命中＝解析器壞掉」）：合成有無 timeout 兩 job。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "good.yml"
            good.write_text(
                "jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps: []\n",
                encoding="utf-8",
            )
            bad = Path(td) / "bad.yml"
            bad.write_text(
                "jobs:\n  a:\n    runs-on: x\n    steps: []\n",
                encoding="utf-8",
            )
            self.assertEqual(_jobs_missing_timeout(good), [])
            self.assertEqual(_jobs_missing_timeout(bad), ["a"])


if __name__ == "__main__":
    unittest.main()
