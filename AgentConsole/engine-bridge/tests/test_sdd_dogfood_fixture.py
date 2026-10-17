"""W4 dogfood 的 CI 夾具：同一條全鏈，AI 換成確定性替身，每次都能重跑（improving_115 §4.5 D-5；
契約 E2E-17 第 15、19 列；ADR-XPLAT-016 §5.3、§10）。

真 claude 的真跑花額度、要數分鐘、結果因模型而異；CI 要的是「不靠 AI、每次都能重跑」的全鏈證據。
所以這裡只把 AI 換成 `aisdlc-mock-claude`（只回放 prompt 內的 `[KEYWORD]` 字樣、不寫檔），
其餘全是真的：
  人在 SDD session 用真 CLI 子行程把 FSM 走到 HUMAN_PENDING → Bridge `:freeze`（核准人）
  → 真 adapter 編譯 TCS → 真引擎＋真 pytest 評估指令（專案根預置會通過的測試檔）
  → 委派同步（談判／委派／交還）→ RTM 回寫。
失敗夾具再多走：引擎升級 → FSM 進 ESCALATION → Bridge 顯示恢復指令 → 照那條指令恢復 → 下一個批次
可啟動。成功夾具的 Then 引號字面值取替身必然輸出的 `[AT_OK_n]`；失敗夾具取替身必不輸出的
`NEVER_PRINTED_n`（沒有方括號）。真 SDD CLI 在此環境 import 不了才略過（略過會印出原因）。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.fsm_phase import phase_of
from tests.conftest import TERMINAL, read_trace
from tests.sdd_run_support import (
    CONTRACTS_REL,
    FSM_REL,
    TOKEN,
    contracts_dir,
    digest_of,
    events_of,
    fsm_state,
    post,
    sdd_block,
    wait_fsm,
    workspace_has,
)

OK_TCS = "TCS-DogfoodOk-20261017.md"
FAIL_TCS = "TCS-DogfoodFail-20261017.md"

#: (AC ID, AT ID, 測試類型, Then 的引號字面值)。AT-001-2-E-1 是 ADR §8.1 的邊界尾綴命名。
OK_ROWS = [
    ("AC-001-1", "AT-001-1-1", "Unit", "[AT_OK_1]"),
    ("AC-001-1", "AT-001-1-2", "Integration", "[AT_OK_2]"),
    ("AC-001-2", "AT-001-2-1", "Unit", "[AT_OK_3]"),
    ("AC-001-2", "AT-001-2-E-1", "Unit", "[AT_OK_4]"),
]
#: E2E 類 AT 走 SCG-5（重試上限 2）；Then 的字面值替身永遠不會輸出 ⇒ 驗收 regex 必敗。
FAIL_ROWS = [("AC-001-1", "AT-001-1-1", "E2E", "NEVER_PRINTED_1")]

#: 契約 §3.1.5 的字面值（獨立於 app/fsm_phase.py 手寫）：ESCALATION→BLOCKED／0、IMPLEMENTATION→
#: IMPLEMENTATION／5。
BLOCKED_PHASE = {"name": "BLOCKED", "order": 0, "blocking": True, "observation": False}
IMPLEMENTATION_PHASE = {"name": "IMPLEMENTATION", "order": 5, "blocking": False,
                        "observation": False}


def assert_phase(view: dict[str, Any], expected: dict[str, Any]) -> None:
    """T-G（app/fsm_phase.py）已接線：phase 必須是 `{name, order, blocking, observation}` 物件
    （不得是 null），四欄型別與值合契約 §3.1.5，且等於 `phase_of(current_state)` 的回傳。"""
    phase = view["phase"]
    assert isinstance(phase, dict), f"phase 不得是 null／非物件：{phase!r}"
    assert set(phase) == {"name", "order", "blocking", "observation"}, phase
    assert type(phase["name"]) is str and type(phase["order"]) is int, phase
    assert type(phase["blocking"]) is bool and type(phase["observation"]) is bool, phase
    assert phase == expected == phase_of(view["current_state"]), (view["current_state"], phase)

#: SDD v0.24 起規則遙測預設 ON：沒有這兩個 0 的 CLI 驅動會把 fire／catch 計數寫回 tracked 的
#: `governance/rules/*.yaml`（fsm_runtime.py D28 註解），測試不得弄髒 SDD 樹。Bridge 自己呼叫 CLI
#: 時已帶（app/sdd_cli.py）；這裡是「人」那一側的子行程。
NO_TELEMETRY = {"SDD_ENABLE_RULE_FIRE_TELEMETRY": "0", "SDD_ENABLE_RULE_CATCH_TELEMETRY": "0"}


# ── 夾具內容 ────────────────────────────────────────────────────────────────────────────
def tcs_text(rows: list[tuple[str, str, str, str]], title: str) -> str:
    """官方模板格式的最小 TCS（形狀同 tests/sdd_run_support.TCS_TEXT）。"""
    head = (f"# Test Contract Specification — {title}\n\n"
            "**spec-format-version**: 1.0\n**scenario**: greenfield\n\n"
            "## 1. AC → AT 映射表\n\n"
            "| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |\n"
            "|-------|---------|-------|---------|-------|---------|------|\n")
    table = "".join(f"| {ac} | 夾具驗收 | {at} | 夾具 | ✅ | {kind} | □ |\n"
                    for ac, at, kind, _ in rows)
    blocks = "".join(
        f"```gherkin\n# {at}\nScenario: 夾具 {at}\n  Given 系統就緒\n  When 執行\n"
        f"  Then 輸出 \"{lit}\"\n```\n\n" for _ac, at, _kind, lit in rows)
    return head + table + "\n## 2. AT 格式\n\n" + blocks


def build_project(tmp_path: Path, key: str, text: str, tcs_name: str,
                  rows: list[tuple[str, str, str, str]]) -> Path:
    """專案根（allowed roots 之下）：TCS 放 contracts；`tests/` 預置會通過的測試檔，函式名含 AT
    的底線化 token，使評估指令 `pytest tests -k "<AT>"` 不依賴 AI 也能選到恰好一個測試。"""
    root = tmp_path / "projects" / key
    (root / CONTRACTS_REL).mkdir(parents=True)
    (root / CONTRACTS_REL / tcs_name).write_text(text, encoding="utf-8", newline="")
    (root / "tests").mkdir()
    for _ac, at, _kind, _lit in rows:
        token = at.replace("-", "_")
        (root / "tests" / f"test_{token}.py").write_text(
            f"def test_{token}_basic():\n    assert True\n", encoding="utf-8", newline="\n")
    return root


# ── 扮演「人在 SDD session」：真 CLI 子行程（外部專案模式，狀態檔住專案根） ──────────────────
def session_env(sdd_root: Path, state_dir: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("BRIDGE_", "SDD_")) and k.upper() != "PYTHONPATH"}
    env.update({"SDD_STATE_DIR": str(state_dir), "PYTHONPATH": str(sdd_root), "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1", **NO_TELEMETRY})
    return env


def run_python(sdd_root: Path, state_dir: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-W", "ignore::RuntimeWarning", *argv], cwd=str(sdd_root),
        env=session_env(sdd_root, state_dir), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180, stdin=subprocess.DEVNULL, check=False)


def sdd_session(sdd_root: Path, root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    """人在專案根的 SDD session 執行一個 FSMRuntime CLI 動詞。"""
    return run_python(sdd_root, root / FSM_REL, "-m", "tools.fsm_runtime.fsm_runtime", *argv)


_PROBE: list[str | None] = []                      # 快取：None＝真 CLI 可用；字串＝不可用的原因


def real_cli_problem(sdd_root: Path) -> str | None:
    """真 CLI 在這個環境 import 得了嗎。樹不存在是環境錯誤、直接失敗；只有 import 失敗（缺相依套件）
    才回原因讓 fixture 略過。整個 session 只探測一次。"""
    if not _PROBE:
        assert (sdd_root / "tools" / "fsm_runtime" / "fsm_runtime.py").is_file(), sdd_root
        with tempfile.TemporaryDirectory() as scratch:
            done = run_python(sdd_root, Path(scratch), "-c", "import tools.fsm_runtime.fsm_runtime")
        last = (done.stderr.strip().splitlines() or ["（無 stderr）"])[-1]
        _PROBE.append(None if done.returncode == 0 else f"rc={done.returncode}：{last}")
    return _PROBE[0]


def walk_to_human_pending(sdd_root: Path, root: Path, key: str) -> None:
    """SCG 閘門走到 HUMAN_PENDING（SDD_SPEC_FIRST_GATE.md〈FSM 寫入指令〉：逐步 transition，最後一個
    `gate --result PASS`；不手改任何 FSM-STATE 檔——Rule 9.6）。"""
    for to, why in (("SCENARIO_DETECT", "夾具：建立 FSM 專案"), ("AGENT_LOAD", "夾具：載入角色"),
                    ("SPEC_DRAFTING", "夾具：規格撰寫"), ("SCG_VALIDATION", "夾具：SCG 驗證開始")):
        done = sdd_session(sdd_root, root, "transition", "--project", key, "--to", to,
                           "--reason", why)
        assert done.returncode == 0, (to, done.stdout, done.stderr)
    done = sdd_session(sdd_root, root, "gate", "--project", key, "--gate", "SCG_VALIDATION",
                       "--result", "PASS", "--reason", "夾具：SCG 通過")
    assert done.returncode == 0, (done.stdout, done.stderr)
    assert fsm_state(root, key)["current_state"] == "HUMAN_PENDING"


def run_displayed_command(recovery: dict[str, str],
                          reason: str) -> subprocess.CompletedProcess[str]:
    """照 Console 卡片顯示的指令字串原樣執行（只把 `<人工原因>` 佔位換成真理由）：Windows 跑
    PowerShell 形、其餘跑 POSIX 形。要驗的不只是 `--to` 目標對，而是「顯示的那條指令本身能用」。"""
    placeholder = '"<人工原因>"'
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("BRIDGE_", "SDD_"))}
    env.update({"PYTHONUTF8": "1", **NO_TELEMETRY})
    if sys.platform == "win32":                        # Windows 行為：5.1 的 powershell.exe 跑 .ps1
        script = recovery["powershell"]
        assert placeholder in script, script
        with tempfile.TemporaryDirectory() as scratch:
            ps1 = Path(scratch) / "recover.ps1"
            # 5.1 讀無 BOM 的 .ps1 會當 ANSI；顯示的字串含路徑，一律 BOM＋CRLF
            ps1.write_text(script.replace(placeholder, f'"{reason}"'), encoding="utf-8-sig",
                           newline="\r\n")
            return subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=180, stdin=subprocess.DEVNULL, check=False)
    posix = recovery["posix"]
    assert placeholder in posix, posix
    return subprocess.run(["sh", "-c", posix.replace(placeholder, f'"{reason}"')], env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=180, stdin=subprocess.DEVNULL, check=False)


# ── 共用 fixture ─────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def venv_scripts_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """評估指令是裸 `pytest`：引擎子行程繼承測試行程的 PATH，把目前直譯器所在目錄放最前面，才會解析
    到同一個 venv 的 pytest（開發機的 PATH 可能先命中 pyenv shim；契約 E2E-17 前置）。"""
    monkeypatch.setenv(
        "PATH", f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}")


@pytest.fixture
def dogfood_live(make_bridge: Any, settings: Any) -> Any:
    """寫入面啟用、指向**真的** SDD 樹的 Bridge。"""
    assert settings.sdd_root is not None, "找不到真的 AISDLC_SDD 樹"
    problem = real_cli_problem(settings.sdd_root)
    if problem is not None:
        pytest.skip(f"真 SDD CLI 在此環境啟動不了（缺相依套件？）：{problem}")
    return make_bridge(replace(settings, sdd_write_token=TOKEN))


def prepare_frozen_project(live: Any, tmp_path: Path, key: str, tcs_name: str, title: str,
                           rows: list[tuple[str, str, str, str]]) -> tuple[Path, str, str]:
    """專案根 → SDD session 走到 HUMAN_PENDING → Bridge 核准凍結。回傳 (專案根, TCS 相對路徑,
    摘要)。"""
    text = tcs_text(rows, title)
    root = build_project(tmp_path, key, text, tcs_name, rows)
    walk_to_human_pending(live.settings.sdd_root, root, key)
    tcs_rel = f"{CONTRACTS_REL.as_posix()}/{tcs_name}"
    digest = digest_of(text)
    frozen = live.client.post(
        f"/sdd/fsm/{key}:freeze", headers={"X-Bridge-Token": TOKEN},
        json={"root": str(root), "docs": [tcs_rel], "approver": "operator",
              "reason": "夾具：核准凍結", "expected_digests": {tcs_rel: digest}})
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["current_state"] == "SPEC_FROZEN"
    assert frozen.json()["spec_doc_digests"] == {tcs_rel: digest}
    stage = fsm_state(root, key)["frozen_stages"][-1]
    assert (stage["approved_by"], stage["spec_doc_digests"]) == ("operator", {tcs_rel: digest})
    return root, tcs_rel, digest


def compile_fixture(live: Any, root: Path, key: str, tcs_name: str,
                    digest: str) -> list[dict[str, Any]]:
    resp = live.client.post("/sdd/compile", json={"spec_dir": str(contracts_dir(root)),
                                                  "fsm_project": key})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unmapped_at_ids"] == [] and body["frozen_digest"] == "verified"
    assert (body["scenario"], body["digest"], body["fsm_project"], body["spec_file"]) == (
        "greenfield", digest, key, tcs_name)
    assert all(t["spec_digest"] == digest for t in body["tasks"]), "每個任務帶凍結的摘要"
    return body["tasks"]


def batch_body(run_body: Any, root: Path, key: str, tcs_name: str, tasks: list[dict[str, Any]],
               *, trace: Path | None = None) -> dict[str, Any]:
    """編譯出的任務原樣當 playbook 的 tasks（`PlaybookTaskIn` 就是為此多收那幾欄），再加 `sdd` 區塊
    （與 Console 一致：明指規格檔，所以 workflow_path 是檔案本身）。"""
    playbook = {"version": "1.0", "project": key, "global_goal": f"dogfood 夾具 {key}",
                "global_invariants": {"max_retries_per_step": 1, "auto_compact_interval": 0},
                "tasks": tasks}
    body = run_body(playbook=playbook, delay="0.1", execution_path=root, project=key, trace=trace)
    body["sdd"] = sdd_block(root, key=key, spec_file=tcs_name)
    return body


# ── 成功夾具：全鏈走通，終態把控制權交還（done） ─────────────────────────────────────────────────
def test_the_success_fixture_walks_the_whole_loop_and_hands_control_back(
        dogfood_live: Any, tmp_path: Path, run_body: Any) -> None:
    live, key = dogfood_live, "dogfood-ok"
    root, tcs_rel, digest = prepare_frozen_project(live, tmp_path, key, OK_TCS, "DogfoodOk",
                                                   OK_ROWS)
    tasks = compile_fixture(live, root, key, OK_TCS, digest)
    assert [t["step_id"] for t in tasks] == [
        "sdd-greenfield-at-001-1-1", "sdd-greenfield-at-001-1-2", "sdd-greenfield-at-001-2-1",
        "sdd-greenfield-at-001-2-e-1"], "邊界尾綴 AT-001-2-E-1 也要被編成任務（ADR §8.1）"
    assert [t["max_retries"] for t in tasks] == [5, 5, 5, 5], "Unit／Integration 走 SCG-4"
    assert [t["maintain_context"] for t in tasks] == [False, True, False, True], \
        "同一 AC 內連續 AT 維持脈絡、跨 AC 隔離"
    assert [t["expected_output_regex"] for t in tasks] == [re.escape(r[3]) for r in OK_ROWS]
    assert [t["evaluator_command"] for t in tasks] == [
        f'pytest tests -k "{r[1].replace("-", "_")}" -q' for r in OK_ROWS]
    assert not any(t["weak_regex"] for t in tasks), "字面值取自 Then 的引號：不是弱 regex"

    trace = tmp_path / "mock-trace.jsonl"
    created = post(live, batch_body(run_body, root, key, OK_TCS, tasks, trace=trace))
    assert created.status_code == 201, created.text
    rid, workspace = created.json()["run_id"], Path(created.json()["workspace"])
    assert not created.json().get("warnings")
    assert live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"

    # FSM：談判（簽核人）→ 委派 → 交還控制權；reason 逐字（ADR §4.4）
    final = wait_fsm(root, "IMPLEMENTATION", key=key)
    assert [(t["from"], t["to"], t["reason"]) for t in final["decision_trace"][-5:]] == [
        ("HUMAN_PENDING", "SPEC_FROZEN", "console-freeze approver=operator; reason=夾具：核准凍結"),
        ("SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED",
         f"console-signoff approver=operator; run={rid}"),
        ("TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION",
         f"console-signoff approver=operator; oracle={tcs_rel}@{digest}; "
         "basis=import-draft-signoff; r9.20.3=not-satisfied"),
        ("IMPLEMENTATION", "AUTOCLAUDE_DELEGATED", f"console-run run={rid} START"),
        ("AUTOCLAUDE_DELEGATED", "IMPLEMENTATION", f"console-run run={rid} COMPLETED")]
    assert final["autoclaude_delegated_tracking"]["playbook_ref"] == f"run:{rid}"
    assert final["escalation_history"] == [], "完成不是阻塞態"

    # 引擎被餵的是凍結的規格檔；它的子行程環境只有 SDD_PROJECT（沒有狀態目錄指標、沒有權杖）
    playbook = yaml.safe_load((workspace / "playbook.yaml").read_text(encoding="utf-8"))
    assert playbook["workflow_type"] == "aisdlc_sdd"
    assert Path(playbook["workflow_path"]) == (contracts_dir(root) / OK_TCS).resolve()
    calls = [r for r in read_trace(trace) if r["keywords"]]
    assert len(calls) == 4, "四個 AT 各一次替身呼叫（第一次就通過）"
    assert {(r["sdd_env"]["SDD_PROJECT"], r["sdd_env"]["SDD_STATE_DIR"],
             r["sdd_env"]["has_write_token"]) for r in calls} == {(key, None, False)}

    # RTM（諮詢）：四個 AT、兩個 AC 全覆蓋，摘要＝凍結摘要
    rtm = live.client.get(f"/autoclaude/runs/{rid}/rtm")
    assert rtm.status_code == 200, rtm.text
    assert rtm.json() == {
        "scenario": "greenfield", "spec_digest": digest,
        "at": {"passed": 4, "total": 4, "pct": 100.0, "unmapped": 0},
        "ac": {"covered": 2, "total": 2, "pct": 100.0}, "failed_at_ids": [],
        "weak_regex_at_ids": [], "unmapped_at_ids": [], "fully_covered": True, "advisory": True}

    # Console 卡片讀的 Bridge 視圖：回 IMPLEMENTATION、沒有恢復指令；phase 是 T-G 純函式的投影
    view = live.client.get(f"/sdd/fsm/{key}", params={"root": str(root)}).json()
    assert view["current_state"] == "IMPLEMENTATION" and view["fsm_project"] == key
    assert view["escalation_history"] == [] and "recovery" not in view
    assert_phase(view, IMPLEMENTATION_PHASE)


# ── 失敗夾具：重試耗盡 → 引擎升級 → ESCALATION → 人工恢復 → 下一批次可啟動 ──────────────────
def test_the_failure_fixture_escalates_and_is_recovered_by_the_displayed_command(
        dogfood_live: Any, tmp_path: Path, run_body: Any) -> None:
    live, key = dogfood_live, "dogfood-fail"
    root, _tcs_rel, digest = prepare_frozen_project(live, tmp_path, key, FAIL_TCS, "DogfoodFail",
                                                    FAIL_ROWS)
    tasks = compile_fixture(live, root, key, FAIL_TCS, digest)
    assert [t["max_retries"] for t in tasks] == [2], "E2E 類 AT 走 SCG-5（重試上限 2）"
    assert tasks[0]["expected_output_regex"] == "NEVER_PRINTED_1"

    trace = tmp_path / "mock-trace.jsonl"
    created = post(live, batch_body(run_body, root, key, FAIL_TCS, tasks, trace=trace))
    assert created.status_code == 201, created.text
    rid = created.json()["run_id"]
    final = live.wait_status(rid, TERMINAL)
    assert final["status"] == "FAILED" and final["reason"].startswith("引擎升級（ESCALATION）")
    # 引擎先重試、才升級（不是一失敗就放棄）；實際嘗試次數由引擎的語意預算決定、不在此釘死，只釘
    # 不變式：升級前至少重試過一次、總嘗試數不超過上限＋1、替身被呼叫的次數＝嘗試次數
    steps = [(e["status"], e["attempt"]) for e in events_of(live, rid, "step")]
    attempts = max(attempt for _status, attempt in steps)
    assert steps[0] == ("STARTED", 1) and ("RETRYING", 2) in steps, steps
    assert steps[-1] == ("FAILED", attempts), steps
    assert 2 <= attempts <= tasks[0]["max_retries"] + 1, steps
    assert len(read_trace(trace)) == attempts, "每次嘗試替身都沒輸出 NEVER_PRINTED_1"

    # FSM：引擎升級型失敗才進阻塞態；哪個 run、為什麼，都留在檔裡
    state = wait_fsm(root, "ESCALATION", key=key)
    assert state["escalation_provenance"]["source"] == "autoclaude_delegated_failed"
    assert state["escalation_history"][-1]["resolved_at"] is None
    assert state["autoclaude_delegated_tracking"]["playbook_ref"] == f"run:{rid}"
    # 不斷言 `from`：`record_escalation` 先把 current 寫成 ESCALATION，這一筆的 from 因此是
    # "ESCALATION" 而非真實來源 AUTOCLAUDE_DELEGATED（state_loader.py 自己註解的既有行為）
    last = state["decision_trace"][-1]
    assert (last["to"], last["trigger"]) == ("ESCALATION", "autoclaude_delegated_exit")
    assert last["reason"].startswith(
        f"console-run run={rid} ENGINE-ESCALATION step=sdd-greenfield-at-001-1-1: ")
    assert "NEVER_PRINTED_1" in last["reason"], "人看檔就知道為什麼升級：失敗的 regex 在 reason 裡"

    # Console 卡片：阻塞態、provenance、可複製的恢復指令（兩種殼各一條）
    view = live.client.get(f"/sdd/fsm/{key}", params={"root": str(root)}).json()
    assert view["current_state"] == "ESCALATION"
    assert_phase(view, BLOCKED_PHASE)
    assert view["escalation_provenance"]["source"] == "autoclaude_delegated_failed"
    assert view["escalation_history"][-1]["resolved_at"] is None
    recovery = view["recovery"]
    assert recovery["target"] == "IMPLEMENTATION"
    for form in ("powershell", "posix"):
        assert "resume-from-escalation" in recovery[form] and f"--to {recovery['target']}" in (
            recovery[form]), recovery[form]
        assert str(root / FSM_REL) in recovery[form] and "<人工原因>" in recovery[form]

    # 恢復前，下一個批次被擋（Bridge 沒有恢復動詞，也不碰 ESCALATION）：零副作用
    refused_body = batch_body(run_body, root, key, FAIL_TCS, tasks)
    refused = post(live, refused_body)
    assert (refused.status_code, refused.json()["reason"], refused.json()["current_state"]) == (
        409, "fsm_state_conflict", "ESCALATION")
    assert not workspace_has(live, refused_body["run_id"])

    # 人在 SDD session 執行「卡片顯示的那條指令」恢復
    done = run_displayed_command(recovery, "dogfood fixture human recovery")
    assert done.returncode == 0, (done.stdout, done.stderr)
    healed = fsm_state(root, key)
    assert healed["current_state"] == "IMPLEMENTATION"
    assert healed["escalation_history"][-1]["resolved_at"], "歷史末筆回填 resolved_at"
    assert healed["escalation_history"][-1]["resolution"].startswith("human_resume")
    assert healed["escalation_provenance"]["source"] == "autoclaude_delegated_failed", \
        "恢復後 provenance 不清除：有沒有未解的失敗要看 current_state 與歷史末筆"
    again = live.client.get(f"/sdd/fsm/{key}", params={"root": str(root)}).json()
    assert_phase(again, IMPLEMENTATION_PHASE)
    assert "recovery" not in again

    # 下一個批次可直接啟動（這個夾具的規格仍必敗，所以再升級一次：歷史多一筆未解的）
    second = post(live, batch_body(run_body, root, key, FAIL_TCS, tasks))
    assert second.status_code == 201, second.text
    assert live.wait_status(second.json()["run_id"], TERMINAL)["status"] == "FAILED"
    state = wait_fsm(root, "ESCALATION", key=key)
    assert [h["resolved_at"] is None for h in state["escalation_history"]] == [False, True]
