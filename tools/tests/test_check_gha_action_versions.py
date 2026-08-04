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

    def test_every_actions_org_action_is_scanned_not_only_a_whitelist(self) -> None:
        """R56 訂正（原 `test_untracked_action_is_ignored` 的語意反轉）：舊版把
        「白名單以外的 action 被忽略」寫成祝福，實際上那正是 fail-open 的來源
        ——清單打錯一個字（`upload-artefact`）即靜默少守 13 處宣告卻仍 rc=0。
        現行判準改為「凡 `actions/*` 一律納入唯一性斷言」，本測試鎖住該範圍
        不得再退回白名單列舉。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/cache@v3\n      - uses: actions/checkout@v5\n",
            "b.yml": "      - uses: actions/cache@v4\n",
        })
        findings = m.scan(wf_dir)
        self.assertIn("checkout", findings)
        self.assertEqual(set(findings["cache"].keys()), {"v3", "v4"})

    def test_quoted_uses_declarations_are_scanned(self) -> None:
        """R56 回歸鎖（三名審查員各自 bug-injection 揪出）：`uses: "actions/x@v4"`
        與 `uses: 'actions/x@v4'` 都是合法 YAML／GHA 寫法，舊 regex 要求 `uses:`
        後緊接 `actions/`，加引號的宣告會**從普查中消失**（不是判為第二種版本），
        真實版本漂移完全隱形且工具仍印綠燈。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": '      - uses: "actions/checkout@v4"\n'
                     "      - uses: 'actions/setup-python@v5'\n",
        })
        findings = m.scan(wf_dir)
        self.assertEqual(set(findings["checkout"].keys()), {"v4", "v5"})
        self.assertEqual(findings["checkout"]["v4"], [".github/workflows/b.yml:1"])
        # 版本字串不得把收尾引號吃進去（`v5"` vs `v5` 會是假不一致）
        self.assertEqual(set(findings["setup-python"].keys()), {"v5"})

    def test_mixed_quoted_and_unquoted_inconsistency_is_red(self) -> None:
        """R56：引號寫法的漂移必須真的讓 main() 回 1，而非只是被 scan() 看到。"""
        rc_files = {
            "a.yml": "      - uses: actions/checkout@v5\n",
            "b.yml": '      - uses: "actions/checkout@v4"\n',
        }
        wf_dir = _fixture_workflows_dir(rc_files)
        original = m._WORKFLOWS_DIR
        m._WORKFLOWS_DIR = wf_dir
        try:
            self.assertEqual(m.main([]), 1)
        finally:
            m._WORKFLOWS_DIR = original

    def test_sha_pinned_ref_is_scanned(self) -> None:
        """R56 回歸鎖：GitHub 官方建議的供應鏈硬化寫法是以 commit SHA 釘選
        （版本不以 `v` 開頭）。舊 regex `@(v\\S+)` 對這種寫法連 action 都不登記，
        同一 action 一邊釘 SHA 一邊釘 tag 的真實漂移零訊號。"""
        sha = "11bd71901bbe5b1630ceea73d27597364c9af683"
        wf_dir = _fixture_workflows_dir({
            "a.yml": f"      - uses: actions/upload-artifact@{sha} # v4.2.0\n",
            "b.yml": "      - uses: actions/upload-artifact@v5\n",
        })
        findings = m.scan(wf_dir)
        self.assertEqual(set(findings["upload-artifact"].keys()), {sha, "v5"})

    def test_subpath_action_is_scanned_with_full_name(self) -> None:
        """R56 round 2 回歸鎖（SD fixture 探針揪出）：`actions/cache/restore` 與
        `actions/cache/save` 是 GitHub 官方文件正式提供的子路徑 action，舊 regex
        的 action 名字元類不含 `/`，這兩種宣告**從普查中消失**（不是被判為第二種
        版本），與本工具已修的引號／SHA 缺口完全同形。子路徑名須完整入 key
        （`cache/restore` 與 `cache/save`、`cache` 各自獨立——GitHub 對子路徑
        action 的版本是各自獨立的 ref，混為一 key 會產生假不一致）。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/cache/restore@v4\n"
                     "      - uses: actions/cache/save@v4\n"
                     "      - uses: actions/cache@v4\n",
            "b.yml": '      - uses: "actions/cache/restore@v3"\n',
        })
        findings = m.scan(wf_dir)
        self.assertEqual(set(findings["cache/restore"].keys()), {"v3", "v4"})
        self.assertEqual(set(findings["cache/save"].keys()), {"v4"})
        self.assertEqual(set(findings["cache"].keys()), {"v4"})
        self.assertEqual(findings["cache/restore"]["v3"], [".github/workflows/b.yml:1"])

    def test_subpath_action_version_drift_makes_main_red(self) -> None:
        """R56 round 2：子路徑 action 的版本漂移必須真的讓 main() 回 1（僅
        scan() 看得到不算——舊缺口的實害正是 rc=0 綠燈）。

        fixture 另含一個一致的 `actions/checkout@v5` 宣告，刻意讓 findings 非空
        ——否則舊 regex 下兩檔皆掃不到任何宣告，會由「掃描面整個斷掉」那道
        fail-loud（`not findings` → rc=1）湊出 rc=1 而假通過（本測試初版即如此，
        bug-injection 實測發現後補強）。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - uses: actions/checkout@v5\n"
                     "      - uses: actions/cache/restore@v4\n",
            "b.yml": "      - uses: actions/cache/restore@v3\n",
        })
        original = m._WORKFLOWS_DIR
        m._WORKFLOWS_DIR = wf_dir
        try:
            self.assertEqual(m.main([]), 1)
        finally:
            m._WORKFLOWS_DIR = original

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

    def test_unpaired_apostrophe_does_not_swallow_the_real_comment(self) -> None:
        """R56 回歸鎖：YAML plain scalar 內未成對引號（英文所有格）完全合法，
        舊版逐字元引號追蹤會讓引號狀態外溢到整行末尾，其後真實 `#` 不再被剝除
        ——被註解掉的舊版本行遂被當成現行宣告（假紅）。"""
        line = "      - name: Restore the repo's cache   # uses: actions/checkout@v1"
        stripped = m._strip_yaml_comment(line)
        self.assertEqual(stripped, "      - name: Restore the repo's cache   ")
        self.assertIsNone(m._USES_RE.search(stripped))

    def test_unpaired_apostrophe_line_does_not_leak_state_to_real_declaration(self) -> None:
        """R56 對照組：未成對引號行之後的真實 `uses:` 宣告仍必須被登記（確認上
        一條修法沒有矯枉過正把整行判成註解）。"""
        wf_dir = _fixture_workflows_dir({
            "a.yml": "      - name: it's a probe   # uses: actions/checkout@v1\n"
                     "      - uses: actions/checkout@v5\n",
        })
        findings = m.scan(wf_dir)
        self.assertEqual(set(findings["checkout"].keys()), {"v5"})

    def test_hash_without_preceding_space_is_not_a_comment(self) -> None:
        """YAML 規格：`#` 只有在行首或前接空白時才起始註解。"""
        self.assertEqual(
            m._strip_yaml_comment("      - uses: actions/checkout@abc#def"),
            "      - uses: actions/checkout@abc#def",
        )

    def test_shell_single_quoted_hash_bang_is_not_stripped(self) -> None:
        """真實 repo 形狀（windows-compat-ci.yml `printf '%s\\n' '#!/usr/bin/env bash'`）：
        `#` 位於成對單引號內，不得被當成註解剝除。"""
        line = "            printf '%s\\n' '#!/usr/bin/env bash'"
        self.assertEqual(m._strip_yaml_comment(line), line)


class TestMain(unittest.TestCase):
    def _run_main_with(self, files: dict[str, str]) -> int:
        wf_dir = _fixture_workflows_dir(files)
        original = m._WORKFLOWS_DIR
        m._WORKFLOWS_DIR = wf_dir
        try:
            return m.main([])
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
        self.assertEqual(m.main([]), 0)

    def test_real_repo_scan_coverage_does_not_silently_shrink(self) -> None:
        """R56 新增（QA bug-injection：舊版唯一斷言是 `main() == 0`，把
        `_TRACKED_ACTIONS` 內 `upload-artifact` 打成 `upload-artefact` 後 13 處
        宣告完全脫離監控，工具印 ✅ rc=0、496 個 root unittest 全綠、零訊號）。

        本鎖以「覆蓋面下限」而非「精確等值」釘選：現況 4 個 `actions/*` action
        共 56 處宣告；合法新增 workflow/step 只會讓數字上升，**下降**代表掃描
        面（regex／glob／範圍判準）被靜默縮小。四個 action 名稱另作為存在性
        釘選——任一從普查中消失即紅。"""
        findings = m.scan(m._WORKFLOWS_DIR)
        total = sum(len(sites) for versions in findings.values() for sites in versions.values())
        self.assertGreaterEqual(
            total, 56,
            f"真實 repo `uses: actions/…` 命中數 {total} < 56（R56 現況）——"
            f"掃描面疑似被靜默縮小；實際命中：{ {a: sorted(v) for a, v in findings.items()} }",
        )
        self.assertLessEqual(
            {"checkout", "setup-python", "upload-artifact", "github-script"},
            set(findings),
            f"下列 action 曾實際發生跨檔版本落差（R54 DEF-101-420/424），不得從"
            f"普查中消失；現行命中：{sorted(findings)}",
        )


if __name__ == "__main__":
    unittest.main()
