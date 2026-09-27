"""DEF-200-402 回歸鎖 — chaos_runner 裸 CLI 不得寫回 tracked governance/rules/*.yaml。

事故：本機 nightly `sdd-fsm-chaos-latest` stage（`AutoClaude/tools/run_local_nightly.ps1`）
先跑 `pytest -m chaos`（受 `conftest.py::_isolate_rule_telemetry_default` session autouse
fixture 保護，安全），再緊接著裸呼叫 `python -m tools.fsm_runtime.chaos_runner --rounds 100
--json` 子行程——這一步不是 pytest 行程，conftest 的隔離對它零作用，且四個遙測/hook 身分
env（`SDD_ENABLE_RULE_FIRE_TELEMETRY`／`SDD_ENABLE_RULE_CATCH_TELEMETRY`／
`SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK`／`SDD_FSM_HOOK_ENTRY`）在 nightly schtasks／
GitHub Actions runner 的行程樹裡從未被設定過，v0.24 起「unset → 預設 ON」的規則遙測寫回
於是真的把 19 支 tracked `R-9.*.yaml` 寫髒（2026-09-26 22:37:35～22:38:36 nightly 窗）。

修法：`chaos_runner.run_chaos_rounds()`（`_cli()` 與 `_chaos_b28_benchmark.py` 共用的唯一
入口）用 `fsm_runtime.telemetry_writeback_disabled()` context manager 包住整個 round
迴圈，強制兩個遙測 env 為 "0"，見該函式 docstring 說明為何不借用 D28 的
`SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK`／`SDD_FSM_HOOK_ENTRY` hook 身分機制。

兩層測試（對應 DEF-200-402 設計書 §4）：

1. **主鎖（子行程 CLI，對應 brief 指定形態＋nightly／雲端實際踩雷的呼叫方式）**：在
   `tmp_path` 下建一棵獨立的 `tools/fsm_runtime/` + `governance/` 複本沙盒，子行程
   `cwd=<sandbox>`、四個遙測/hook env 全數清空（模擬 nightly schtasks／GitHub Actions
   runner 的行程樹），斷言複本 `governance/rules/*.yaml` 逐檔 sha256 前後不變。子行程
   的 `rule_loader.RULES_DIR` 由**它自己**的 `__file__` 推導、解到沙盒內的
   `governance/`，全程不觸碰真實 tracked 樹。
2. **輔助鎖（in-process，沿用 `test_rule_fire_telemetry_wiring.py::_isolated_rules` 同構
   先例）**：直接呼叫 `chaos_runner.run_chaos_rounds()`，monkeypatch
   `rule_loader.RULES_DIR` 指向複本、四個 env 全數 unset，斷言複本 sha256 不變。這支覆蓋
   `_chaos_b28_benchmark.py` 的呼叫模式（直接呼叫 `run_chaos_rounds`，不經 CLI 子行程），
   跑起來比測項 1 快兩個數量級，適合當日常回歸鎖主力；子行程測試當端到端證據。

兩支測試皆含「非空洞」斷言（真的跑了 N 輪、FSM 真的轉態過），避免 rc=0 但什麼都沒跑的假綠。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import chaos_runner, rule_loader  # noqa: E402

_V030_ROOT = Path(__file__).resolve().parents[3]
_FSM_RUNTIME_SRC = _V030_ROOT / "tools" / "fsm_runtime"
_GOVERNANCE_SRC = _V030_ROOT / "governance"
# state_loader.py 透過 importlib 依 `parents[3]` 絕對路徑委派這支跨版本共用
# SSOT（R45／DEF-101-358），不經 sys.path——沙盒必須在對應相對位置放一份複本，
# 否則 import 期就 FileNotFoundError（見本檔第一次實跑紅綠自證）。
_COMPONENT_SANITIZER_SRC = _V030_ROOT.parent / "scripts" / "component_sanitizer.py"

# 四個必須全數清空以重現 nightly schtasks／GitHub Actions runner 行程樹的 env
# （D28 的兩個 hook 身分 env 亦一併清空——沒有任何一個顯式值時，若 D1 的
# telemetry_writeback_disabled() 失效，兩者的預設 unset→ON 語意會讓 fire/catch 遙測
# 真的寫回；見 fsm_runtime.py:181-206 的 _telemetry_writeback_allowed()）。
_TELEMETRY_ENVS = (
    "SDD_ENABLE_RULE_FIRE_TELEMETRY",
    "SDD_ENABLE_RULE_CATCH_TELEMETRY",
    "SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK",
    "SDD_FSM_HOOK_ENTRY",
)


def _sha256_map(rules_dir: Path) -> dict:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(rules_dir.glob("*.yaml"))
    }


# ---------- 測項 1：主鎖，子行程 CLI ----------


@pytest.fixture
def _sandbox_tree(tmp_path):
    """建一棵獨立的 `<tmp>/sandbox/{tools,governance}` 複本，讓子行程
    `python -m tools.fsm_runtime.chaos_runner` 在完全隔離於真實 tracked 樹的環境下執行。

    只複製 `tools/fsm_runtime/`（去除 `tests/`／`__pycache__/`）＋`governance/`：
    DEF-200-402 設計書已核實 `tools/fsm_runtime/*.py`（非 test）內所有絕對匯入皆落在
    `tools.fsm_runtime.*` 命名空間內，無人跨出去 import 其他頂層 `tools/` 子套件。
    """
    sandbox = tmp_path / "sandbox"
    (sandbox / "tools").mkdir(parents=True)
    (sandbox / "tools" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copytree(
        _FSM_RUNTIME_SRC,
        sandbox / "tools" / "fsm_runtime",
        ignore=shutil.ignore_patterns("tests", "__pycache__"),
    )
    shutil.copytree(_GOVERNANCE_SRC, sandbox / "governance")
    # state_loader.py 的 parents[3] 從 sandbox 內部解到 tmp_path（sandbox 的上一層）
    # ——共用淨化模組須放在這裡，不是 sandbox 裡面，見 _COMPONENT_SANITIZER_SRC 註解。
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_COMPONENT_SANITIZER_SRC, scripts_dir / "component_sanitizer.py")
    return sandbox


def test_subprocess_cli_does_not_mutate_governance_rules(_sandbox_tree):
    """子行程跑 `python -m tools.fsm_runtime.chaos_runner`（四個遙測/hook env 全數清空）
    後，沙盒複本 `governance/rules/*.yaml` 內容逐檔 sha256 不變。

    這正是 DEF-200-402 事故的實際重現形態：nightly `sdd-fsm-chaos-latest` stage／雲端
    `chaos-latest` job 都是這樣呼叫的。拿掉 `chaos_runner.run_chaos_rounds()` 裡的
    `with telemetry_writeback_disabled():` 這一行，本測試必紅（見證據檔的紅綠自證逐字
    記錄）。
    """
    rules_dir = _sandbox_tree / "governance" / "rules"
    before = _sha256_map(rules_dir)
    assert before, "sandbox 複本必須真的帶有規則檔，否則本測試對零檔案完全沒有鑑別力"

    env = os.environ.copy()
    for k in _TELEMETRY_ENVS:
        env.pop(k, None)

    proc = subprocess.run(
        [
            sys.executable, "-m", "tools.fsm_runtime.chaos_runner",
            "--rounds", "2", "--seed", "1", "--json",
        ],
        cwd=str(_sandbox_tree),
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"chaos_runner CLI 子行程未正常結束（stdout/stderr 見下）：\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )

    # 非空洞斷言：JSON 輸出真的跑了 2 輪，不是 rc=0 但什麼都沒執行的假綠。
    payload = json.loads(proc.stdout)
    assert payload["total_rounds"] == 2

    after = _sha256_map(rules_dir)
    assert after == before, (
        "governance/rules/*.yaml 被裸 CLI 子行程寫回——"
        "telemetry_writeback_disabled() 防線失效（DEF-200-402 迴歸）"
    )


# ---------- 測項 2：輔助鎖，in-process ----------


def test_run_chaos_rounds_inprocess_does_not_mutate_governance_rules(tmp_path, monkeypatch):
    """in-process 直接呼叫 `chaos_runner.run_chaos_rounds()`（沿用
    `test_rule_fire_telemetry_wiring.py::_isolated_rules` 同構先例：
    `shutil.copytree` + `monkeypatch.setattr(rule_loader, "RULES_DIR", ...)`），四個
    遙測/hook env 全數 unset，斷言複本規則檔 sha256 前後不變；同時斷言 FSM 真的跑滿 5
    輪且每輪都有實際 transition（非空洞 rc=0）。

    覆蓋 `_chaos_b28_benchmark.py` 的呼叫模式（直接呼叫 `run_chaos_rounds`，不經 CLI
    子行程）；跑起來比測項 1 快兩個數量級，適合日常回歸鎖主力，子行程測試當端到端證據。
    """
    rdir = tmp_path / "rules"
    shutil.copytree(rule_loader.RULES_DIR, rdir)
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    for k in _TELEMETRY_ENVS:
        monkeypatch.delenv(k, raising=False)

    before = _sha256_map(rdir)
    assert before, "複本必須真的帶有規則檔，否則本測試對零檔案完全沒有鑑別力"

    report = chaos_runner.run_chaos_rounds(n=5, seed=1)

    # 非空洞斷言：FSM 真的跑滿 5 輪、每輪都至少轉態一次（不是 rc=0 但空轉的假綠）。
    assert report.total == 5
    assert all(r.steps_taken > 0 for r in report.rounds), (
        "至少一輪 steps_taken==0——FSM 從未真正轉態，測試對遙測寫回沒有鑑別力"
    )

    after = _sha256_map(rdir)
    assert after == before, (
        "governance/rules 複本被 in-process 呼叫寫回——"
        "telemetry_writeback_disabled() 防線失效（DEF-200-402 迴歸）"
    )
