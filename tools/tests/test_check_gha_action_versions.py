#!/usr/bin/env python3
"""tools/check_gha_action_versions.py 的單元測試（R55：GitHub Actions 版本跨
workflow 一致性機械鎖——R54 round 1/2〔DEF-101-420/424〕連續兩輪靠人工比對才
發現落差後落地）。

全部案例以 tmp fixture 目錄注入（`scan()` 收明確 `workflows_dir` 路徑），**不
依賴真實 repo `.github/workflows/` 現況**（比照既有
`test_check_pytest_baseline_sites.py` 同款慣例）——工具對真實 repo 的現況驗證
交給 `tools/run_root_unittests.py` 之外的實際 CI 執行（`main()` 本身也在
`test_main_against_real_repo_workflows_is_green` 跑一次，確認目前 11 支
workflow 確實一致）。

執行：python3 -m unittest tools.tests.test_check_gha_action_versions -v
（亦由 tools/run_root_unittests.py discover 納入）
"""
from __future__ import annotations

import atexit
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_gha_action_versions as m  # noqa: E402

_TMP_DIR = Path(tempfile.mkdtemp(prefix="gha_action_versions_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))
_tmp_counter = [0]


def _fixture_workflows_dir(files: dict[str, str]) -> Path:
    """建一個 `<root>/.github/workflows/` fixture 目錄結構（scan() 以父目錄的
    父目錄為相對化基準，須具備同構層級才能驗證輸出的 file:line 格式）。"""
    _tmp_counter[0] += 1
    root = _TMP_DIR / f"fixture_{_tmp_counter[0]}"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (wf_dir / name).write_text(text, encoding="utf-8")
    return wf_dir


class TestScan(unittest.TestCase):
    def test_consistent_versions_across_files_no_violation(self) -> None:
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": "      - uses: actions/checkout@v5\n      - uses: actions/setup-python@v6\n",
        })
        findings = m.scan(wf_dir)
        self.assertEqual(set(findings["checkout"].keys()), {"v5"})
        self.assertEqual(set(findings["setup-python"].keys()), {"v6"})

    def test_inconsistent_version_detected_with_file_and_line(self) -> None:
        """核心回歸鎖：兩份 workflow 對同一 action 宣告不同版本，findings 須同時
        列出兩個版本各自的 file:line 站點（不只是布林紅燈，須可指路排障）。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": "\n      - uses: actions/checkout@v4\n",
        })
        findings = m.scan(wf_dir)
        checkout = findings["checkout"]
        self.assertEqual(set(checkout.keys()), {"v4", "v5"})
        self.assertEqual(checkout["v5"], [".github/workflows/a.yml:1"])
        self.assertEqual(checkout["v4"], [".github/workflows/b.yml:2"])

    def test_untracked_action_is_ignored(self) -> None:
        """只掃 _TRACKED_ACTIONS 登記的四個 action；其餘（如 actions/cache）不比對，
        不應出現在 findings 中——避免對無跨檔漂移事故史的 action 做無邊界掃描。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/cache@v3\n      - uses: actions/checkout@v5\n",
        })
        findings = m.scan(wf_dir)
        self.assertNotIn("cache", findings)
        self.assertIn("checkout", findings)

    def test_action_absent_from_all_files_yields_empty_dict(self) -> None:
        wf_dir = _fixture_workflows_dir({"a.yml": "      - run: echo hi\n"})
        findings = m.scan(wf_dir)
        self.assertEqual(findings.get("github-script"), None)

    def test_yaml_extension_is_scanned_not_silently_dropped(self) -> None:
        """回歸鎖：`.yaml` 副檔名的 workflow 檔須與 `.yml` 同等被掃描——
        本工具存在的理由正是防「新增 workflow 沿用舊版本卻沒被發現」，若
        `.yaml` 被漏掃，該情境會完全看不到（R55 SD finding）。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yaml": "      - uses: actions/checkout@v4\n",
        })
        findings = m.scan(wf_dir)
        checkout = findings["checkout"]
        self.assertEqual(set(checkout.keys()), {"v4", "v5"})
        self.assertEqual(checkout["v4"], [".github/workflows/b.yaml:1"])

    def test_commented_out_uses_line_is_not_treated_as_current_declaration(self) -> None:
        """回歸鎖：被 `#` 註解掉的舊版本 `uses:` 行不應被當成現行宣告——避免
        升版過渡期保留備援註解行時產生假性版本不一致紅燈（R55 SD finding）。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": "      # - uses: actions/checkout@v4\n      - uses: actions/checkout@v5\n",
        })
        findings = m.scan(wf_dir)
        checkout = findings["checkout"]
        self.assertEqual(set(checkout.keys()), {"v5"})


class TestStripYamlComment(unittest.TestCase):
    def test_strips_trailing_comment(self) -> None:
        self.assertEqual(
            m._strip_yaml_comment("      - uses: actions/checkout@v5  # pinned"),
            "      - uses: actions/checkout@v5  ",
        )

    def test_hash_inside_quotes_is_not_a_comment(self) -> None:
        self.assertEqual(m._strip_yaml_comment('run: echo "a#b"'), 'run: echo "a#b"')

    def test_whole_line_comment_becomes_empty(self) -> None:
        self.assertEqual(m._strip_yaml_comment("# - uses: actions/checkout@v4"), "")


class TestMain(unittest.TestCase):
    def _run_main_with(self, files: dict[str, str]) -> int:
        wf_dir = _fixture_workflows_dir(files)
        original = m._WORKFLOWS_DIR
        m._WORKFLOWS_DIR = wf_dir
        try:
            return m.main()
        finally:
            m._WORKFLOWS_DIR = original

    def test_main_returns_zero_when_all_consistent(self) -> None:
        rc = self._run_main_with({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": "      - uses: actions/checkout@v5\n",
        })
        self.assertEqual(rc, 0)

    def test_main_returns_one_when_inconsistent(self) -> None:
        rc = self._run_main_with({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": "      - uses: actions/checkout@v4\n",
        })
        self.assertEqual(rc, 1)

    def test_main_against_real_repo_workflows_is_green(self) -> None:
        """對真實 repo `.github/workflows/` 現況跑一次 main()——本輪四方複審已
        人工核實 11 支 workflow 現行版本一致（無違規），此測試把該次人工核實
        轉為可重複執行的機械回歸鎖（往後任一輪破壞一致性即紅，不必再靠人工
        grep 才能發現）。"""
        self.assertEqual(m.main(), 0)


if __name__ == "__main__":
    unittest.main()
