"""GitHub Actions 所有 job 必須宣告 timeout-minutes 的機械鎖（R14 QA-R14-RR-1）。

WHY（測意圖非僅行為，Rule 9）：
無 timeout 的 job 卡死時燒滿 GitHub 預設上限 360 分鐘 runner——帳務停擺＋額度緊縮
（CI-2 裁決主題）下風險放大。R14 SCAN-CI-5 曾以「全 repo 唯一無 timeout」人工目視
宣稱補了一個 job，複審 QA-R14-RR-1 用機械掃描打破此宣稱：實際尚有 3 個輕量 alert/
lock job 無 timeout。本測試把「所有 job 皆有 timeout-minutes」從人工數改為機械鎖，
新增 job 忘記宣告即紅、且杜絕未來同類「唯一/都有」的人工計數誤判。

以行首錨定的縮排解析抽 job（零第三方依賴，根層 unittest 環境不保證 pyyaml），
`# ` 註解態 job 天然不被匹配。

R15 SCAN-C-3 fail-open 硬化：合成樣本曾證實 `jobs:  # comment`、4-space 縮排 job、
`  a:  # comment` 三種合法 YAML 寫法讓解析器整檔靜默掃出 0 job 而綠燈通過。修法：
(1) regex 容忍行尾註解；(2) 每檔「至少 1 個 job」下限斷言——縮排/風格逸出解析器
（如 4-space 縮排）時 fail-closed 判紅而非靜默放行；(3) glob 加掃 `*.yaml`；
(4) 全 repo workflow 檔數下限釘選，防掃描面（目錄/副檔名）漂移後守門空轉。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_DIR = _REPO_ROOT / ".github" / "workflows"

# R15 SCAN-C-3：行尾註解為合法 YAML（`jobs:  # x`／`  a:  # x`），不得使解析器靜默 0 命中。
_JOBS_HEADER_RE = re.compile(r"^jobs:\s*(#.*)?$")
_JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(#.*)?$")
_TIMEOUT_RE = re.compile(r"^    timeout-minutes:\s*\d+")

# R15 SCAN-C-3：全 repo workflow 檔數下限釘選（2026-07-20 實查 11 檔）。
# 低於下限＝掃描面疑似漂移（目錄改名/檔案搬遷/副檔名逸出 glob）→ 紅燈要求人工確認，
# 合併/刪除 workflow 時同步下修並於 commit 說明。
_MIN_WORKFLOW_COUNT = 11


def _parse_jobs(path: Path) -> dict[str, bool]:
    """解析該 workflow 的 {job 名: 是否已宣告 timeout-minutes}。

    解析法：進入 `jobs:` 區塊後，2-space 縮排的 `<name>:` 為 job 起點，
    4-space 的 `timeout-minutes:` 屬該 job。job step 內容縮排更深不會誤匹配。
    掃出 0 job 的檔案由呼叫端 fail-closed 判紅（勿在此靜默回傳空）。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    in_jobs = False
    jobs: dict[str, bool] = {}
    cur: str | None = None
    for ln in lines:
        if _JOBS_HEADER_RE.match(ln):
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
    return jobs


def _jobs_missing_timeout(path: Path) -> list[str]:
    """回傳該 workflow 中缺 timeout-minutes 的 job 名清單。"""
    return [j for j, has in _parse_jobs(path).items() if not has]


class TestWorkflowTimeoutCoverage(unittest.TestCase):
    def test_all_jobs_declare_timeout(self) -> None:
        # R15 SCAN-C-3：glob 加掃 *.yaml（GitHub Actions 兩種副檔名皆讀）。
        workflows = sorted(
            p for pat in ("*.yml", "*.yaml") for p in _WORKFLOW_DIR.glob(pat)
        )
        self.assertGreaterEqual(
            len(workflows), _MIN_WORKFLOW_COUNT,
            f"workflow 檔數 {len(workflows)} 低於釘選下限 {_MIN_WORKFLOW_COUNT}——"
            "掃描面疑似縮小（目錄改名/檔案搬遷/副檔名逸出）；若確為合併/刪除 workflow，"
            "請同步下修 _MIN_WORKFLOW_COUNT 並於 commit 說明",
        )
        offenders: dict[str, list[str]] = {}
        for wf in workflows:
            jobs = _parse_jobs(wf)
            # R15 SCAN-C-3：0 job fail-closed——先前 4-space 縮排/行尾註解等合法寫法
            # 會讓解析器整檔靜默 0 命中而綠燈（fail-open）。
            self.assertTrue(
                jobs,
                f"{wf.name}：掃出 0 個 job——該檔縮排/風格疑似逸出本解析器"
                "（如 job 用 4-space 縮排），請改回 2-space 慣例或擴充解析器",
            )
            missing = [j for j, has in jobs.items() if not has]
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

    def test_parser_not_fooled_by_legal_yaml_styles(self) -> None:
        """R15 SCAN-C-3 自證：三種曾靜默 0 job 通過的合法寫法，現在必有紅燈訊號。

        1. `jobs:  # comment`　　→ 修復後正常進入區塊，缺 timeout 的 job 被抓出。
        2. `  a:  # comment`　　 → 修復後 job 行正常匹配，缺 timeout 被抓出。
        3. job 用 4-space 縮排　 → 解析器不支援（維持行首錨定簡單性），改由
           「掃出 0 job」fail-closed 斷言判紅（見 test_all_jobs_declare_timeout）。
        """
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            jobs_comment = Path(td) / "jobs_comment.yml"
            jobs_comment.write_text(
                "jobs:  # push 閘\n  a:\n    runs-on: x\n    steps: []\n",
                encoding="utf-8",
            )
            job_comment = Path(td) / "job_comment.yml"
            job_comment.write_text(
                "jobs:\n  a:  # 主 job\n    runs-on: x\n    steps: []\n",
                encoding="utf-8",
            )
            four_space = Path(td) / "four_space.yml"
            four_space.write_text(
                "jobs:\n    a:\n        runs-on: x\n        steps: []\n",
                encoding="utf-8",
            )
            # 寫法 1/2：修復後解析成功且抓到缺 timeout（先前是 0 job 假綠）
            self.assertEqual(_jobs_missing_timeout(jobs_comment), ["a"])
            self.assertEqual(_jobs_missing_timeout(job_comment), ["a"])
            # 寫法 3：0 job → 主測試的 assertTrue(jobs) fail-closed 判紅
            self.assertEqual(_parse_jobs(four_space), {})


if __name__ == "__main__":
    unittest.main()
