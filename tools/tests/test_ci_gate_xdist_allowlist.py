"""DEF-200-274 第十輪批評缺口 2：`ci-gate.sh` xdist 判準必須是「允許清單」（只有 LATEST 保證
帶 `_atomic_write_text` 修法才開 xdist；凍結基線與中間歷史版一律序列）；DEF-200-289／318／
326：`ci-gate.ps1` fallback 兩處呼叫（凍結基線不得帶 xdist、LATEST 軌必須帶）與三處
orchestrator 的 cpu_budget 匯出段接線（含路徑真解得到）。完整 WHY 與安家理由見
docs/06_quality/CrossPlatform_Guard_Line_History.md
〈test_ci_gate_xdist_allowlist 模組 WHY（2026-09-19 搬遷）〉。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

# tools/tests → tools → 根目錄（REPO_ROOT）；ci-gate.sh 位於 AISDLC_SDD/scripts/ 下。
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_GATE = REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.sh"
CI_GATE_PS1 = REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.ps1"
PRE_PUSH = REPO_ROOT / "tools" / "git-hooks" / "pre-push"

#: DEF-200-289：三處 orchestrator 匯出段的共同錨點字面值（存在即視為已接線；
#: 三份檔案各自的變數命名慣例不同——bash 用 `"$PY"`／`$TOPLEVEL`，PowerShell 用
#: `python`／`$repo`——故只鎖「呼叫 cpu_budget.py --legs」這個共同錨點，不逐字
#: 比對整段程式碼，避免對三種殼語法各寫一份脆弱的逐字鎖）。
_CPU_BUDGET_EXPORT_ANCHOR = "cpu_budget.py"

# 只認允許清單這一種寫法；排除清單（無論寫成 `!=` 或反過來的 `not ==`）都不合格。
_ALLOWLIST_CONDITION = '"${VER}" == "${LATEST}"'
_EXCLUDELIST_CONDITION = '"${VER}" != "${FROZEN_BASELINE}"'

# DEF-200-315（2026-09-19）：ci-gate.sh／ci-gate.ps1 的 python 呼叫改優先釘死
# repo 根層 .venv（`"$PY"` / `& $py`），不再是裸 `python`——下面兩個判準各自的
# 錨點正則須同時接受舊裸字面值與新直譯器變數兩種形態，語意不變（只是「認得出
# 呼叫端」這一步要跟著消費端的改法走）。
_PY_INVOKE_SH_RE = re.compile(r'^(?:python\b|"\$PY")')
_PY_INVOKE_PS1_FSM_CALL_RE = re.compile(r'^(?:python|& \$py) -m pytest tools/fsm_runtime/tests/')


def _ci_gate_text() -> str:
    assert CI_GATE.is_file(), f"ci-gate.sh 不存在：{CI_GATE}"
    return CI_GATE.read_text(encoding="utf-8")


def _xdist_args_block(text: str) -> str:
    """擷取「宣告 XDIST_ARGS → if 判準 → 賦值成多 worker 旗標」這一整塊原文。

    以 `local XDIST_ARGS=""` 為起點、`XDIST_ARGS="-n auto --dist worksteal"` 為訖點，
    中間必須恰好是一句 `if [[ <條件> ]]; then`——比對嵌入本檔而非重新發明正則，
    是為了讓斷言貼著 ci-gate.sh 的真實原文，結構一旦被改寫（例如拆成多個 if/elif）
    本鎖會直接找不到區塊而 fail-loud，不會誤判為「條件仍合格」。
    """
    m = re.search(
        r'local XDIST_ARGS=""\s*\n'
        r'\s*if \[\[ (?P<cond>.*?) \]\]; then\s*\n'
        r'\s*XDIST_ARGS="-n auto --dist worksteal"\s*\n'
        r'\s*fi',
        text,
    )
    assert m, (
        "ci-gate.sh 找不到 FSM runtime 段落的 XDIST_ARGS 判準區塊——結構已變動，"
        "請同步本鎖"
    )
    return m.group("cond")


class CiGateXdistAllowlistTest(unittest.TestCase):
    """`ci-gate.sh` xdist 判準必須是允許清單，且姊妹段落必須無條件帶 xdist。"""

    def test_xdist_allowlist_condition_gates_on_latest_only(self) -> None:
        """FSM runtime 段落的 XDIST_ARGS 判準必須逐字是允許清單 `VER == LATEST`。"""
        cond = _xdist_args_block(_ci_gate_text())
        self.assertEqual(
            cond, _ALLOWLIST_CONDITION,
            f"ci-gate.sh 的 XDIST_ARGS 判準應為允許清單 {_ALLOWLIST_CONDITION!r}"
            f"（只有 LATEST 保證帶 _atomic_write_text 修法），實得 {cond!r}——"
            "疑似退回排除清單寫法，會誤幫未修競態的中間歷史版開多 worker（判準退化復發）",
        )

    def test_xdist_excludelist_condition_does_not_reappear(self) -> None:
        """反向鎖：舊排除清單條件字面值不得出現在 XDIST_ARGS 判準區塊內。

        刻意只掃區塊本身、不對整份 ci-gate.sh 做全文禁字——`"${LATEST}" != "${FROZEN_
        BASELINE}"` 是版本迴圈另一段（決定 FW_VERSIONS 是否納入 LATEST）的合法既有寫法，
        對整檔禁字會誤傷那一句無關的既有邏輯。
        """
        block_cond = _xdist_args_block(_ci_gate_text())
        self.assertNotIn(
            _EXCLUDELIST_CONDITION, block_cond,
            f"XDIST_ARGS 判準區塊內出現排除清單字面值 {_EXCLUDELIST_CONDITION!r}"
            "——即使不是唯一條件，只要排除清單重新混入判準就已是同型缺陷復發",
        )

    def test_shared_infra_pytest_call_always_carries_xdist(self) -> None:
        """`scripts/tests/`（共享 CI infra）呼叫端必須無條件帶 `-n auto --dist worksteal`。

        與 FSM runtime 段落不同：`scripts/tests/` 不含 `snapshot.py` 那段共享 tmp 檔
        競態（ci-gate.sh 本檔第三個呼叫端註解已現查記載），版本無關，故不套用上面的
        允許清單判準——它應恆帶 xdist 旗標，不因 VER/LATEST 而異。
        """
        text = _ci_gate_text()
        calls = [
            ln for ln in text.splitlines()
            if "-m pytest scripts/tests/" in ln
            and _PY_INVOKE_SH_RE.match(ln.lstrip())
        ]
        self.assertTrue(calls, "ci-gate.sh 找不到呼叫 scripts/tests/ 的 pytest 陳述式——結構已變動")
        self.assertEqual(
            len(calls), 1,
            f"預期恰有 1 處呼叫 scripts/tests/ 的 pytest（本鎖的姊妹段落假設），實得 "
            f"{len(calls)} 處：{calls}",
        )
        self.assertIn(
            "-n auto --dist worksteal", calls[0],
            f"scripts/tests/ 的 pytest 呼叫應無條件帶 `-n auto --dist worksteal`，"
            f"實得：{calls[0].strip()!r}",
        )


def _ci_gate_ps1_text() -> str:
    assert CI_GATE_PS1.is_file(), f"ci-gate.ps1 不存在：{CI_GATE_PS1}"
    return CI_GATE_PS1.read_text(encoding="utf-8")


class CiGatePs1FallbackXdistTest(unittest.TestCase):
    """GAP-D（DEF-200-289）＋ DEF-200-318（A3）：`ci-gate.ps1` fallback 恰兩處 FSM
    runtime pytest 呼叫——凍結基線（不得帶 xdist，複製會撞已修掉的共享 tmp 檔
    競態）與新補的 LATEST 軌（`sdd_version.py` 解析，必須帶 xdist）。"""

    def _calls_by_xdist(self) -> dict[str, str]:
        text = _ci_gate_ps1_text()
        calls = [ln for ln in text.splitlines() if _PY_INVOKE_PS1_FSM_CALL_RE.match(ln.lstrip())]
        self.assertEqual(len(calls), 2, f"預期恰 2 處 FSM runtime pytest 呼叫，實得：{calls}")
        with_xdist = [c for c in calls if "-n auto" in c]
        no_xdist = [c for c in calls if "-n auto" not in c]
        self.assertEqual(len(with_xdist), 1, f"預期恰 1 處帶 xdist，實得：{with_xdist}")
        self.assertEqual(len(no_xdist), 1, f"預期恰 1 處不帶 xdist，實得：{no_xdist}")
        return {"with_xdist": with_xdist[0], "no_xdist": no_xdist[0]}

    def test_frozen_baseline_call_has_no_xdist_flags(self) -> None:
        no_xdist = self._calls_by_xdist()["no_xdist"]
        self.assertNotIn("-n auto", no_xdist)
        self.assertNotIn("--dist worksteal", no_xdist)

    def test_latest_track_call_carries_xdist(self) -> None:
        with_xdist = self._calls_by_xdist()["with_xdist"]
        self.assertIn("-n auto", with_xdist)
        self.assertIn("--dist worksteal", with_xdist)

    def test_fallback_resolves_latest_via_sdd_version_script(self) -> None:
        """不得硬寫死版本號，否則升版後 fallback 又跟丟 LATEST。"""
        self.assertIn("sdd_version.py", _ci_gate_ps1_text())


class CpuBudgetExportWiringTest(unittest.TestCase):
    """DEF-200-289／DEF-200-320：五處呼叫端都必須接上 `cpu_budget.py --legs`；
    前三者另需匯出 `AUTOSDD_PARALLEL_TESTS_WORKERS`；兩支 nightly-full workflow
    只需帶 `cpu_budget.py --legs 1` 與 `PYTEST_XDIST_AUTO_NUM_WORKERS`（xdist
    原生讀取該環境變數，見兩檔 DEF-200-320 註解，不需額外匯出前者）。"""

    _WF_DIR = REPO_ROOT / ".github" / "workflows"
    _TARGETS = (  # (顯示名, 路徑, 是否須匯出 AUTOSDD_PARALLEL_TESTS_WORKERS)
        ("ci-gate.sh", CI_GATE, True),
        ("ci-gate.ps1", CI_GATE_PS1, True),
        ("pre-push", PRE_PUSH, True),
        ("windows-compat-ci.yml", _WF_DIR / "windows-compat-ci.yml", False),
        ("macos-compat-ci.yml", _WF_DIR / "macos-compat-ci.yml", False),
    )

    def test_orchestrators_export_cpu_budget(self) -> None:
        for name, path, needs_workers in self._TARGETS:
            with self.subTest(target=name):
                assert path.is_file(), f"{name} 不存在：{path}"
                text = path.read_text(encoding="utf-8")
                self.assertIn(_CPU_BUDGET_EXPORT_ANCHOR, text, f"{name} 缺 cpu_budget.py 匯出段")
                self.assertIn("--legs", text, f"{name} 的 cpu_budget.py 呼叫缺 --legs 參數")
                self.assertIn("PYTEST_XDIST_AUTO_NUM_WORKERS", text)
                if needs_workers:
                    self.assertIn("AUTOSDD_PARALLEL_TESTS_WORKERS", text)

    def test_orchestrators_broadcast_success_path(self) -> None:
        """2026-09-20（DEF-200-348，QA F-QA-02／SD F-SD-02）：三個 shell
        廣播站點（`ci-gate.sh`／`ci-gate.ps1`／`pre-push`；不含兩支 nightly-full
        workflow——它們不是本輪 scope）的成功路徑過去全靜默，只有缺檔的 fail-open
        分支才出聲，審查者只能靠旁證推斷 worker 數。三站點都必須同時含「算出來並
        匯出」與「呼叫端已預設而跳過」兩條成功路徑各自的可稽核字面（開發期已用
        `git show HEAD:<路徑>` 核對修前文字對本斷言必定紅，見 DEF-200-348 修復
        紀錄，本測試只鎖現行工作樹內容）。"""
        for name, path, _ in self._TARGETS[:3]:  # 只取三個 shell 站點，不含 workflow yml
            with self.subTest(target=name):
                assert path.is_file(), f"{name} 不存在：{path}"
                text = path.read_text(encoding="utf-8")
                self.assertIn(
                    "[cpu_budget] broadcast", text,
                    f"{name} 缺成功路徑可稽核字面 `[cpu_budget] broadcast`",
                )
                self.assertIn(
                    "broadcast workers=", text,
                    f"{name} 缺「算出來並匯出」分支的可稽核字面 `broadcast workers=`",
                )
                self.assertIn(
                    "broadcast skipped:", text,
                    f"{name} 缺「呼叫端已預設而跳過」分支的可稽核字面 `broadcast skipped:`",
                )

    def test_ci_gate_broadcasts_target_monorepo_root(self) -> None:
        """DEF-200-326：兩檔住 `AISDLC_SDD/scripts/`，到 monorepo 根還多一層
        ——舊文字直接拼 REPO_ROOT（＝AISDLC_SDD/）是死碼（該路徑不存在，紅綠自證
        見 scratchpad 的 DevA 證據檔）。以各自根算法獨立重算，斷言路徑真實存在。"""
        sh_line = next(
            (ln for ln in _ci_gate_text().splitlines() if "cpu_budget.py" in ln and "=" in ln),
            None,
        )
        self.assertIsNotNone(sh_line, "ci-gate.sh 找不到組出 cpu_budget.py 路徑的賦值行")
        self.assertIn(
            "MONOREPO_ROOT", sh_line,
            f"ci-gate.sh 組 cpu_budget.py 路徑應以 MONOREPO_ROOT 為底，實得：{sh_line.strip()!r}",
        )
        sh_root = (CI_GATE.parent / ".." / "..").resolve()
        self.assertTrue(
            (sh_root / "tools" / "lib" / "cpu_budget.py").is_file(),
            f"ci-gate.sh 自身根算法（scripts/../..）重算出的路徑不存在：{sh_root}",
        )

        ps1_line = next(
            (ln for ln in _ci_gate_ps1_text().splitlines() if "cpu_budget.py" in ln and "=" in ln),
            None,
        )
        self.assertIsNotNone(ps1_line, "ci-gate.ps1 找不到組出 cpu_budget.py 路徑的賦值行")
        self.assertIn(
            "'..'", ps1_line,
            f"ci-gate.ps1 路徑應含 monorepo 根層跳升 '..'，實得：{ps1_line.strip()!r}",
        )
        ps1_root = (CI_GATE_PS1.parent / ".." / "..").resolve()
        self.assertTrue(
            (ps1_root / "tools" / "lib" / "cpu_budget.py").is_file(),
            f"ci-gate.ps1 自身根算法（Split-Path 兩層）重算出的路徑不存在：{ps1_root}",
        )


# ── DEF-200-368 系列：pytest 呼叫站點普查（掃描器共用 helper；WHY 見類 docstring）──
def _p(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


_WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
_CENSUS_TARGETS: tuple[tuple[str, Path], ...] = (
    *((f"workflows/{p.name}", p) for p in sorted(_WORKFLOWS_DIR.glob("*.yml"))),
    ("tools/git-hooks/pre-push", PRE_PUSH),
    ("AutoClaude/tools/git-hooks/pre-push", _p("AutoClaude", "tools", "git-hooks", "pre-push")),
    ("AISDLC_SDD/scripts/ci-gate.sh", CI_GATE),
    ("AISDLC_SDD/scripts/ci-gate.ps1", CI_GATE_PS1),
    ("AutoClaude/tools/local_ci_gate.py", _p("AutoClaude", "tools", "local_ci_gate.py")),
    ("AutoClaude/tools/run_local_nightly.ps1",
     _p("AutoClaude", "tools", "run_local_nightly.ps1")),
    ("AutoClaude/tools/run_local_nightly.sh", _p("AutoClaude", "tools", "run_local_nightly.sh")),
)

#: 吃 shell/ps1/yml 的 `-m pytest`，也吃 Python list 呼叫 `"-m", "pytest"`（逗號分隔
#: 非連續子字串——`local_ci_gate.py` 全部站點皆此形態，只用前者會漏掉整支檔）。
_PYTEST_INVOKE_RE = re.compile(r'-m\s+pytest\b|"-m",\s*"pytest"')
#: 呼叫**目標路徑**含此關鍵字 ⇒ SDD／根層層級（需明示旗標才算 PARALLEL）；判準用
#: 目標路徑而非宿主檔案路徑（`run_local_nightly.ps1` 住 AutoClaude/ 卻呼叫 SDD 目標，
#: 反之 workflows/*.yml 呼叫 AutoClaude 測試時宿主檔案不住 AutoClaude/，兩邊都會被
#: 「按宿主路徑判」誤判）。
_SDD_TARGET_MARKERS = ("fsm_runtime/tests", "AISDLC_SDD")
_SERIAL_MARK = "no:xdist"
_PARALLEL_MARKS = ("-n auto", "--dist", "XDIST_ARGS", "AUTOSDD_PARALLEL_TESTS")


def _pytest_call_windows(text: str) -> list[tuple[int, str]]:
    """`(命中行號, 視窗文字)` 列表；視窗＝命中行起最多 6 行（吃跨行旗標）；跳過
    整行皆注解（`#` 開頭）的命中——那是散文提及，不是呼叫。"""
    lines = text.splitlines()
    hits: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#") or not _PYTEST_INVOKE_RE.search(line):
            continue
        hits.append((idx + 1, "\n".join(lines[idx:idx + 6])))
    return hits


def _classify_site(window: str) -> str:
    """`"SERIAL"`／`"PARALLEL"`／`"UNGOVERNED"`（分類規則見本段頂端常數 WHY）。"""
    if _SERIAL_MARK in window:
        return "SERIAL"
    if any(marker in window for marker in _SDD_TARGET_MARKERS):
        return "PARALLEL" if any(m in window for m in _PARALLEL_MARKS) else "UNGOVERNED"
    return "PARALLEL"  # 非 SDD 目標：AutoClaude／共用 ini addopts 治理


def _all_sites() -> list[tuple[str, int, str, str]]:
    """`(display_name, lineno, window, verdict)` 列表（現查磁碟）。"""
    sites: list[tuple[str, int, str, str]] = []
    for display_name, path in _CENSUS_TARGETS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, window in _pytest_call_windows(text):
            sites.append((display_name, lineno, window, _classify_site(window)))
    return sites


#: 理由詞彙：pg_real 單一 DB／perf 計時純度／mutmut runner hash／chaos／凍結基線
#: snapshot 競態，v0.01 不可原地修／單檔／窄範圍呼叫，平行無收益。
_JUSTIFIED_SERIAL_SITES: tuple[tuple[str, str, str], ...] = (
    ("workflows/autoclaude-ci.yml", "test_pgvector_real_recall.py", "pg_real 單一 DB"),
    ("workflows/autoclaude-ci.yml", "test_pgvector_recall_perf.py",
     "pg_real 單一 DB／perf 計時純度"),
    ("workflows/autoclaude-ci.yml", "tests/plugins/token_guard", "mutmut runner hash"),
    ("workflows/autoclaude-ci.yml", "test_goal_synthesis_plugin.py", "mutmut runner hash"),
    ("workflows/autoclaude-ci.yml", "tests/core/orchestration", "mutmut runner hash"),
    ("workflows/autoclaude-ci.yml", "tests/perf/ -v --tb=short -m perf", "perf 計時純度"),
    ("workflows/autoclaude-mutation-on-change.yml", "tests/plugins/token_guard",
     "mutmut runner hash"),
    ("workflows/autoclaude-pg-e2e-on-label.yml", "test_pgvector_real_recall.py",
     "pg_real 單一 DB"),
    ("AutoClaude/tools/local_ci_gate.py", "test_claude_md_no_long_lines.py",
     "單檔／窄範圍呼叫，平行無收益"),
    ("AutoClaude/tools/local_ci_gate.py", "*pytest_args", "單檔／窄範圍呼叫，平行無收益"),
    ("AutoClaude/tools/local_ci_gate.py", "test_pg_state_repository_contract.py",
     "pg_real 單一 DB／單檔／窄範圍呼叫，平行無收益"),
    ("AutoClaude/tools/run_local_nightly.ps1", "test_pgvector_real_recall.py",
     "pg_real 單一 DB／單檔／窄範圍呼叫，平行無收益"),
    ("AutoClaude/tools/run_local_nightly.ps1", "test_pgvector_hnsw_recall.py",
     "單檔／窄範圍呼叫，平行無收益"),
    ("AutoClaude/tools/run_local_nightly.ps1", "@contractFiles",
     "單檔／窄範圍呼叫，平行無收益"),
    ("AutoClaude/tools/run_local_nightly.ps1", "tests/perf/ -v --tb=short -m perf",
     "perf 計時純度"),
    ("AISDLC_SDD/scripts/ci-gate.ps1", '-m "not chaos" -q -rs -p no:xdist',
     "chaos／凍結基線 snapshot 競態，v0.01 不可原地修"),
    ("workflows/aisdlc-sdd-fsm-chaos-nightly.yml", "-m chaos -v -p no:xdist",
     "chaos／凍結基線 snapshot 競態，v0.01 不可原地修"),
    ("AutoClaude/tools/run_local_nightly.ps1", "-m chaos -q -p no:xdist",
     "chaos／凍結基線 snapshot 競態，v0.01 不可原地修"),
)


def _registry_diagnostics(
        sites: list[tuple[str, int, str, str]],
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """一次掃描算出兩件事：`(未登記 SERIAL 站點座標, 死列＝比對不到任何站點的登記列)`。"""
    unregistered: list[str] = []
    live = {k: False for k in _JUSTIFIED_SERIAL_SITES}
    for name, lineno, window, verdict in sites:
        if verdict != "SERIAL":
            continue
        matched = [k for k in _JUSTIFIED_SERIAL_SITES if k[0] == name and k[1] in window]
        if not matched:
            unregistered.append(f"{name}:{lineno}")
        for k in matched:
            live[k] = True
    return unregistered, [k for k, seen in live.items() if not seen]


class PytestInvocationSiteCensusTest(unittest.TestCase):
    """pytest 呼叫站點普查：SERIAL 須登記理由，PARALLEL 須 ini 或明示旗標可查，不得
    有「沒人知道是序列還是平行」的 UNGOVERNED 站點（分類規則見 `_classify_site()`）。"""

    def test_every_serial_site_is_registered(self) -> None:
        unregistered, _dead = _registry_diagnostics(_all_sites())
        self.assertEqual(
            unregistered, [],
            f"以下 SERIAL 站點未登記進 _JUSTIFIED_SERIAL_SITES：{unregistered}")

    def test_no_dead_registry_rows(self) -> None:
        _unreg, dead = _registry_diagnostics(_all_sites())
        self.assertEqual(dead, [], f"以下登記列比對不到任何現況站點（死列）：{dead}")

    def test_zero_ungoverned_sites(self) -> None:
        ungoverned = [f"{n}:{ln}" for n, ln, _w, v in _all_sites() if v == "UNGOVERNED"]
        self.assertEqual(
            ungoverned, [],
            f"以下站點無法辨識平行度意圖（補 -p no:xdist 或登記理由）：{ungoverned}")

    def test_negative_self_proof_unregistered_serial_site_is_caught(self) -> None:
        """合成片段（含未登記的 `-p no:xdist`）證明「未登記」判準真的會紅——不碰
        磁碟，純函式，驗證 `_registry_diagnostics()` 本身有鑑別力。"""
        synthetic = [(
            "workflows/does-not-exist.yml", 1,
            "python -m pytest foo/ -p no:xdist -o addopts=\n", "SERIAL",
        )]
        unregistered, dead = _registry_diagnostics(synthetic)
        self.assertEqual(unregistered, ["workflows/does-not-exist.yml:1"])
        self.assertEqual(dead, list(_JUSTIFIED_SERIAL_SITES),
                          "合成片段不含任何既有登記列，全部應判死列")


if __name__ == "__main__":
    unittest.main()
