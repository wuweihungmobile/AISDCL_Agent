"""Phase H / ACT-045~058 — Generative-Adversarial Execution Layer tests."""
from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import (
    TransitionError,
    OBSERVATION_STATES,
    _HAPPY_PATH,
)


def _rt(tmp_path, state_name, current):
    p = tmp_path / f"FSM-STATE-{state_name}.yaml"
    st = load_state(state_name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


# ---------- M1: EXECUTION_EVALUATION ----------

def test_execution_evaluation_pass(tmp_path):
    rt = _rt(tmp_path, "ee-pass", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    assert rt.state.current == "EXECUTION_EVALUATION"
    rt.exit_execution_evaluation("pass")
    assert rt.state.current == "PR_REVIEW"


def test_execution_evaluation_runtime_fail(tmp_path):
    rt = _rt(tmp_path, "ee-fail", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    rt.exit_execution_evaluation("runtime_fail")
    assert rt.state.current == "IMPLEMENTATION"


def test_execution_evaluation_spec_defect(tmp_path):
    rt = _rt(tmp_path, "ee-spec", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    rt.exit_execution_evaluation("spec_defect")
    assert rt.state.current == "SPEC_AUDIT"


def test_execution_evaluation_bad_verdict(tmp_path):
    rt = _rt(tmp_path, "ee-bad", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    with pytest.raises(ValueError):
        rt.exit_execution_evaluation("definitely-not-a-verdict")


# ---------- M2: TEST_CONTRACT_NEGOTIATED ----------

def test_test_contract_agreed(tmp_path):
    rt = _rt(tmp_path, "tc-ok", "SPEC_FROZEN")
    rt.enter_test_contract_negotiated(contract_ref="API_Order.yaml")
    assert rt.state.current == "TEST_CONTRACT_NEGOTIATED"
    rt.exit_test_contract_negotiated("agreed")
    assert rt.state.current == "IMPLEMENTATION"


def test_test_contract_underspecified(tmp_path):
    rt = _rt(tmp_path, "tc-no", "SPEC_FROZEN")
    rt.enter_test_contract_negotiated()
    rt.exit_test_contract_negotiated("underspecified")
    assert rt.state.current == "SPEC_DRAFTING"


def test_record_test_standard_agreement(tmp_path):
    from tools.fsm_runtime import subagent_contract as sc
    rec = sc.record_test_standard_agreement(
        contract_ref="API_Order.yaml",
        acceptance_criteria=["AC-001-1: HTTP 200 + P95<200ms"],
        generator_signed=True,
        out_dir=tmp_path,
    )
    assert rec["ready_for_implementation"] is True
    assert Path(rec["path"]).exists()
    # 未簽署 → 不得進入 IMPLEMENTATION
    rec2 = sc.record_test_standard_agreement(
        contract_ref="x", acceptance_criteria=["AC"], generator_signed=False, out_dir=tmp_path,
    )
    assert rec2["ready_for_implementation"] is False


# ---------- M5: SCAFFOLD_GC ----------

def test_scaffold_gc_observation_state():
    assert "SCAFFOLD_GC" in OBSERVATION_STATES


def test_scaffold_gc_enter_exit_continue(tmp_path):
    rt = _rt(tmp_path, "gc-ok", "RELEASE")
    rt.enter_scaffold_gc()
    assert rt.state.current == "SCAFFOLD_GC"
    rt.exit_scaffold_gc("continue")
    assert rt.state.current == "RELEASE"


def test_scaffold_gc_respec(tmp_path):
    rt = _rt(tmp_path, "gc-respec", "RELEASE")
    rt.enter_scaffold_gc()
    rt.exit_scaffold_gc("respec")
    assert rt.state.current == "SPEC_DRAFTING"


def test_scaffold_gc_illegal_source(tmp_path):
    rt = _rt(tmp_path, "gc-bad", "IMPLEMENTATION")
    with pytest.raises(TransitionError):
        rt.enter_scaffold_gc()


# ---------- M1: Output Quality Scorer ----------

def test_oqs_pass():
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    obs = ExecutionObservation(tests_total=10, tests_passed=10, ui_assertions_total=4, ui_assertions_passed=4)
    r = score(obs)
    assert r.passed and r.verdict == "pass" and r.score >= 0.8


def test_oqs_runtime_fail():
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    obs = ExecutionObservation(tests_total=10, tests_passed=4, nonzero_exit=True)
    r = score(obs)
    assert not r.passed and r.verdict == "runtime_fail"


def test_oqs_spec_defect_forced():
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    obs = ExecutionObservation(tests_total=10, tests_passed=10)
    r = score(obs, spec_defect=True)
    assert r.verdict == "spec_defect" and not r.passed


def test_oqs_inconclusive_on_zero_observation():
    # H-1：完全無觀測（den 全 0）不得 pass，必為 inconclusive。
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    r = score(ExecutionObservation())
    assert r.verdict == "inconclusive" and r.passed is False


def test_oqs_failure_signal_counts_as_observation():
    # 只有失敗訊號（非零 exit）也算「跑過」→ runtime_fail，非 inconclusive。
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    r = score(ExecutionObservation(nonzero_exit=True))
    assert r.verdict == "runtime_fail" and r.passed is False


# ---------- M1: Sandbox Runner ----------

def test_sandbox_local_stub_is_inconclusive_not_pass():
    # H-4 + H-1：stub 零觀測「絕不可」放行 pass — 鎖死執行接地契約。
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    res = evaluate(SandboxSpec(app_id="demo"), backend="local")
    assert res.backend == "local-stub"
    assert res.oqs.verdict == "inconclusive"
    assert res.oqs.passed is False


def test_sandbox_override_observation():
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation
    obs = ExecutionObservation(tests_total=5, tests_passed=5)
    res = evaluate(SandboxSpec(app_id="demo"), observation_override=obs)
    assert res.oqs.verdict == "pass"


def test_sandbox_playwright_backend_not_configured():
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    with pytest.raises(NotImplementedError):
        evaluate(SandboxSpec(app_id="demo"), backend="playwright")


# ---------- ACT-046: Docker backend real execution-grounding ----------

def test_parse_test_output_pass():
    from tools.fsm_runtime.sandbox_runner import parse_test_output
    obs = parse_test_output("10 passed, 0 failed in 1.2s", "", 0)
    assert obs.tests_total == 10 and obs.tests_passed == 10
    assert obs.nonzero_exit is False and obs.runtime_errors == 0


def test_parse_test_output_fail():
    from tools.fsm_runtime.sandbox_runner import parse_test_output
    obs = parse_test_output("7 passed, 3 failed", "Traceback: boom", 1)
    assert obs.tests_total == 10 and obs.tests_passed == 7
    assert obs.nonzero_exit is True and obs.runtime_errors >= 1


# DEF-200-364 B 包第二棒：三態判斷已下沉到 production 面
# （`sandbox_runner.resolve_docker_available()`），`docker_available()` 現在
# 自己讀 `SDD_DOCKER_AVAILABLE_ENV`（由 conftest.py::pytest_configure 在
# controller 端探測恰一次並寫入）。本模組頂層因而與訂正前逐字相同：呼叫一次
# `docker_available()` 即可，不需要在測試層重覆一份三態邏輯——production
# 呼叫路徑（`_docker_factory()`）與這裡讀的是同一個函式、同一個 env。
_DOCKER = None
try:
    from tools.fsm_runtime.sandbox_runner import docker_available as _da
    _DOCKER = _da()
except Exception:  # noqa: BLE001
    _DOCKER = False

requires_docker = pytest.mark.skipif(not _DOCKER, reason="docker daemon 不可用")

# 2026-07 Mac/Windows 相容性四方複審實測：windows-latest GitHub-hosted runner 的
# Docker Linux 容器支援本身不穩定——同一支未變動的 docker_available()（含完整安全
# 旗標的真實 DockerBackend 探測）在連續三次真實 CI run 中，探測與正式測試的實際
# 執行結果不一致（1 次成功、2 次失敗），而非本框架程式碼可控的確定性 bug。這類
# 「需要容器真的成功跑完並正確回傳輸出」的測試在此環境下無法穩定重現；只驗證
# 「容器執行失敗」的 test_docker_backend_real_runtime_fail 不受影響（環境不穩定本身
# 也會產生 nonzero_exit，恰好符合該測試預期，故不需要排除）。見 DEF-101-062。
#
# 🔴 R60 F-02 訂正：原判準是 `sys.platform.startswith("win")`，把**全部** Windows
# 一起掃掉，排除面遠大於證據面。DEF-101-062 的不穩定證據全部來自 GitHub-hosted
# windows-latest 的 runner（LCOW 那一套堆疊）；本機 Windows 11 + Docker Desktop
# WSL2（`docker info` → OSType=linux）是完全不同的堆疊，實測 docker_available()
# 為 True、被排除的兩支測試連跑 4 次全 PASSED 零 flaky。疊上 CI 帳務停擺
# （DEF-101-081），「容器實跑成功 → OQS pass」這條路在 Windows 上等於零活體覆蓋。
# 改法：排除條件從「平台名稱」換成「能力偵測（docker_available，本身就是用
# DockerBackend 的完整安全 profile 實跑一次容器）」＋僅保留「Windows CI runner」
# 這個確有證據的窄例外。另把 reason 拆成互斥兩段——原本是一個 `or` 選言，讀者
# 無法分辨到底哪個限語觸發（在本機恆為第二個），DEF-101-515 就是因此需要人工
# 考古才解釋得出 v0.30 −4。


# 🔴 R60 round 2 SD-R60-05 訂正：原實作是 `bool(os.environ.get("CI"))`，而
# `bool("false") is True` —— 開發機若設 `CI=false`（前端工具鏈如 Vite/CRA/Jest 常見
# 於 .env 或 shell profile 明示關閉 CI 模式）會被判成 CI runner，於是靜默回到本輪剛
# 移除的「Windows 全平台排除」狀態，正是本輪要消滅的「靜默零活體覆蓋」。改為明確
# 真值集合；`GITHUB_ACTIONS` 一併套用同一判準（GitHub-hosted runner 實際永遠給
# 字面 `"true"`，故不損既有覆蓋，但可擋 `GITHUB_ACTIONS=false` 這個同構回退面）。
_CI_TRUTHY = frozenset({"1", "true", "yes"})


def _env_flag_true(name: str) -> bool:
    """環境變數是否為明確真值（`1`/`true`/`yes`，大小寫與前後空白不敏感）。

    刻意**不**把「非空字串」當真：`false`／`0`／`no` 這些明確否定值必須判 False。
    """
    return os.environ.get(name, "").strip().lower() in _CI_TRUTHY


def _windows_ci_runner() -> bool:
    """是否為「Windows 上的 CI runner」——DEF-101-062 不穩定證據的唯一來源環境。

    GITHUB_ACTIONS 為 GitHub-hosted runner 的權威旗標（不穩定實測即在此）；另收
    通用 CI 旗標作為保守兜底，避免任何 Windows CI 載具因本次放寬而出現不確定紅燈。
    兩者皆須為**明確真值**（見 `_env_flag_true`／SD-R60-05）。
    本機開發環境兩者皆無值 → 覆蓋恢復。
    """
    if not sys.platform.startswith("win"):
        return False
    return _env_flag_true("GITHUB_ACTIONS") or _env_flag_true("CI")


# marker 於 import 時定版，故 production 條件的回歸鎖必須拿 import 當時的環境判定
# 來比對（測試內 monkeypatch 過的 env 不能用來推論 import 時的 marker）。
_WINDOWS_CI_AT_IMPORT = _windows_ci_runner()

if not _DOCKER:
    _DOCKER_SUCCESS_SKIP_REASON = (
        "docker 不可用：docker_available() 為 False（CLI 不存在／daemon 不可連線／"
        "DockerBackend 完整安全旗標組合下的探測容器跑不起來）"
    )
elif _WINDOWS_CI_AT_IMPORT:
    _DOCKER_SUCCESS_SKIP_REASON = (
        "Windows CI runner 的 Docker Linux 容器支援不穩定（DEF-101-062：連續三次"
        "真實 CI run 1 成功/2 失敗，非本框架程式碼可控）—— docker_available() 為 "
        "True，純環境例外；本機 Windows（非 CI）不受此排除，見 R60 F-02"
    )
else:
    _DOCKER_SUCCESS_SKIP_REASON = ""

requires_docker_success = pytest.mark.skipif(
    bool(_DOCKER_SUCCESS_SKIP_REASON),
    reason=_DOCKER_SUCCESS_SKIP_REASON or "（不排除）",
)


# DEF-200-367：三支 docker 測試（real_pass／real_runtime_fail／e2e_through_fsm）
# 原本都用 `SandboxSpec(app_id="demo", ...)`、未設 `track_id`。
# `sandbox_runner.track_container_name(app_id, track_id)` 未帶 track_id 時只用
# app_id 組出容器名（`sdd-{app_id}`），三者因而算出**相同**容器名 `sdd-demo`；
# pytest-xdist `-n 13` 下三者若被排到不同 worker 併發執行，`docker run --name
# sdd-demo` 撞名，其中一次容器實跑失敗（exit 非 0 或輸出被搶佔）⇒ OQS verdict
# ≠ pass（單檔 `-n 13` 3/3 次重現；全套跑法因負載稀釋、排程較少讓三者同時執行
# 而看不到）。修法：三者各帶不同 `track_id`，讓
# `track_container_name(spec.app_id, spec.track_id)` 兩兩相異——這正是
# `track_id` 這個既有欄位本來就存在的用途（ACT-070 艦隊並行 N 軌不撞名），只是
# 這三支測試原本沒有使用它；不改生產面命名規則。
#
# 三支測試與回歸鎖（見檔尾 `TestDockerTestContainerNamesDoNotCollide`）共用本
# helper 建構 spec，確保鎖驗證的 spec 與測試實際執行的 spec 是同一份定義，不會
# 因兩處各自維護一份而彼此漂移。
_DOCKER_TEST_KINDS = ("real-pass", "real-runtime-fail", "e2e-fsm")


def _docker_spec(kind: str):
    """建構 DEF-200-367 三支 docker 測試共用的 SandboxSpec，各自帶不同 track_id。"""
    from tools.fsm_runtime.sandbox_runner import SandboxSpec
    if kind == "real-pass":
        return SandboxSpec(
            app_id="demo", image="busybox",
            test_cmd=["sh", "-c", "echo '10 passed, 0 failed'; exit 0"],
            timeout_sec=60, track_id="h-real-pass",
        )
    if kind == "real-runtime-fail":
        return SandboxSpec(
            app_id="demo", image="busybox",
            test_cmd=["sh", "-c", "echo 'error: boom' >&2; exit 1"],
            timeout_sec=60, track_id="h-runtime-fail",
        )
    if kind == "e2e-fsm":
        return SandboxSpec(
            app_id="demo", image="busybox",
            test_cmd=["sh", "-c", "echo '5 passed, 0 failed'; exit 0"],
            timeout_sec=60, track_id="h-e2e-fsm",
        )
    raise ValueError(f"unknown docker spec kind: {kind!r}")


@requires_docker_success
def test_docker_backend_real_pass():
    # 真實執行接地：容器實跑成功 → OQS pass。
    from tools.fsm_runtime.sandbox_runner import evaluate
    spec = _docker_spec("real-pass")
    res = evaluate(spec, backend="docker")
    assert res.backend == "docker"
    assert res.observation.tests_passed == 10
    assert res.oqs.verdict == "pass" and res.oqs.passed is True


@requires_docker
def test_docker_backend_real_runtime_fail():
    # R3 四方複審 QA 發現（P2）：本測試在 Windows 上不受 requires_docker_success 排除，
    # 依賴的假設是「windows-latest 環境不穩定本身也會產生 nonzero_exit，恰好符合此測試
    # 預期」——此假設目前僅有經驗證據支持（5 次真實失敗 run 皆只出現另兩個測試失敗、
    # 從未出現本測試失敗），並非程式碼層面強制保證。若未來 LCOW 不穩定改以其他形式
    # （如 subprocess 逾時、非 nonzero_exit 的例外）呈現，本測試會直接把不確定性暴露成
    # CI 紅燈且無防護。暫不變更行為（證據仍支持現況），僅記錄此脆弱點供後續留意。
    # 真實執行接地：容器實跑失敗（exit 1 + stderr）→ OQS runtime_fail。
    from tools.fsm_runtime.sandbox_runner import evaluate
    spec = _docker_spec("real-runtime-fail")
    res = evaluate(spec, backend="docker")
    assert res.observation.nonzero_exit is True
    assert res.oqs.verdict == "runtime_fail" and res.oqs.passed is False


@requires_docker_success
def test_docker_backend_e2e_through_fsm(tmp_path):
    # 端到端：IMPLEMENTATION → enter_execution_evaluation → 容器實跑 verdict → exit 路由。
    from tools.fsm_runtime.sandbox_runner import evaluate
    rt = _rt(tmp_path, "ee-docker", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    spec = _docker_spec("e2e-fsm")
    res = evaluate(spec, backend="docker")
    rt.exit_execution_evaluation(res.oqs.verdict)
    assert rt.state.current == "PR_REVIEW"


def test_docker_success_exclusion_is_ci_scoped_not_platform_blanket(monkeypatch):
    """R60 F-02 回歸鎖：排除面必須是「Windows CI runner」而非「全部 Windows」。

    原判準 `sys.platform.startswith("win")` 把本機 Windows 一起掃掉（本機 Docker
    Desktop WSL2 實測兩支測試 4/4 PASSED、零 flaky），使「容器實跑成功 → OQS pass」
    在 Windows 上零活體覆蓋。

    🔴 R60 round 2 SD-R60-04 訂正（本測試自己是假綠）：舊版只斷言 helper
    `_windows_ci_runner()`，**完全沒碰 production 的 marker 條件**——實測把
    `requires_docker_success` 改回 `not _DOCKER or sys.platform.startswith("win")`
    後本測試照樣 PASSED，即「鎖保護的東西不是它宣稱保護的東西」，而那正是最可能的
    回退形狀（直接改運算式、helper 原封不動）。現在分兩段：

      ① **production 條件**（真正的鑑別力來源）：在「docker 可用且 import 當時不是
         Windows CI runner」的環境下，`requires_docker_success` 的 skipif 條件必須
         為 False、skip reason 必須為空字串 —— 只要有人把 marker 改回平台硬排除，
         本機（Windows + Docker Desktop）立刻翻紅。其餘環境（docker 不可用／
         Windows CI）則反向斷言 reason 非空且成因與旗標一致，本測試在任何環境都
         有實質斷言、不會靜默空轉。
      ② helper 語意：`CI`/`GITHUB_ACTIONS` 清空 → False；`GITHUB_ACTIONS=true`
         → 僅 Windows 為 True。此段**不涵蓋 marker 回退**，僅鎖 helper 本身。
    """
    # ① production marker 條件（import 時定版）
    if _DOCKER and not _WINDOWS_CI_AT_IMPORT:
        assert requires_docker_success.args[0] is False, (
            "docker 可用且非 Windows CI runner，production 的 skipif 條件必須為 "
            f"False（實際 {requires_docker_success.args[0]!r}）——條件退化成平台硬"
            "排除（R60 F-02 的原始缺陷形狀）會讓「容器實跑成功 → OQS pass」在本機"
            " Windows 上零活體覆蓋"
        )
        assert _DOCKER_SUCCESS_SKIP_REASON == "", (
            f"不應有任何排除理由，實際: {_DOCKER_SUCCESS_SKIP_REASON!r}"
        )
    else:
        assert _DOCKER_SUCCESS_SKIP_REASON != "", (
            "docker 不可用或身處 Windows CI runner 時必須有明確排除理由（互斥兩段"
            "之一），不得為空字串"
        )
        assert requires_docker_success.args[0] is True, (
            "有排除理由時 skipif 條件必須為 True"
        )
        expected_marker = "docker 不可用" if not _DOCKER else "Windows CI runner"
        assert _DOCKER_SUCCESS_SKIP_REASON.startswith(expected_marker), (
            f"排除理由必須指出真正成因（預期以 {expected_marker!r} 起頭，"
            f"實際 {_DOCKER_SUCCESS_SKIP_REASON!r}）——互斥兩段不得混用"
        )

    # ② helper 語意（不涵蓋 marker 回退，見上方 docstring）
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    assert _windows_ci_runner() is False, (
        "非 CI 環境不得被排除——排除條件退化成平台硬排除（R60 F-02 的原始缺陷形狀）"
    )
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert _windows_ci_runner() is sys.platform.startswith("win"), (
        "DEF-101-062 的 Windows CI runner 窄例外必須保留（放寬不得擴及 CI）"
    )


@pytest.mark.parametrize(
    "value,expect_ci",
    [
        ("false", False), ("FALSE", False), ("0", False), ("no", False),
        ("", False), ("   ", False),
        ("true", True), ("True", True), (" true ", True), ("1", True), ("yes", True),
    ],
)
def test_windows_ci_runner_only_accepts_truthy_flag_values(monkeypatch, value, expect_ci):
    """R60 SD-R60-05 回歸鎖：`CI`/`GITHUB_ACTIONS` 必須以**真值**判定，不可用
    「非空字串」。

    舊實作 `bool(os.environ.get("CI"))` 讓 `CI=false`（前端工具鏈明示關閉 CI 模式的
    常見寫法）判成 True → Windows 開發機被靜默排除 →「容器實跑成功 → OQS pass」零
    活體覆蓋，等於把本輪 F-02 的修復悄悄退回去。若有人改回 `bool(...)`，本測試的
    `false`/`0`/`no`/空白 四組參數會立刻翻紅。

    🔴 兩平台皆有鑑別力：`_windows_ci_runner()` 依設計在非 Windows 上恆為 False，若只
    斷言它，本鎖在 macOS 上會退化成恆綠（本輪是 Mac/Windows 相容性輪，這種單平台鎖
    正是要避免的形狀）。故第一段直接斷言與平台無關的 `_env_flag_true()`。
    """
    for flag in ("CI", "GITHUB_ACTIONS"):
        monkeypatch.setenv(flag, value)
        assert _env_flag_true(flag) is expect_ci, (
            f"{flag}={value!r} 的真值判定應為 {expect_ci}（此段與平台無關，macOS 上"
            f"同樣具鑑別力）；非空字串≠真值"
        )
        monkeypatch.delenv(flag, raising=False)

    expected = expect_ci and sys.platform.startswith("win")
    for flag in ("CI", "GITHUB_ACTIONS"):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setenv(flag, value)
        assert _windows_ci_runner() is expected, (
            f"{flag}={value!r} 應判定 CI runner={expected}（平台 {sys.platform}）；"
            f"非空字串≠真值，`false`/`0`/`no` 必須為 False"
        )


# ---------- M4: Observability Query ----------

def test_logql_lite(tmp_path):
    from tools.fsm_runtime import observability_query as oq
    (tmp_path / "logs.ndjson").write_text(
        '{"level":"error","msg":"deadlock on tx-42"}\n'
        '{"level":"info","msg":"started"}\n'
        '{"level":"error","msg":"timeout"}\n',
        encoding="utf-8",
    )
    hits = oq.logql_lite('{level="error"} |= "deadlock"', obs_dir=tmp_path)
    assert len(hits) == 1 and "deadlock" in hits[0]["msg"]


def test_promql_lite(tmp_path):
    from tools.fsm_runtime import observability_query as oq
    (tmp_path / "metrics.ndjson").write_text(
        '{"name":"http_p95_ms","value":120,"labels":{"route":"/login"}}\n'
        '{"name":"http_p95_ms","value":200,"labels":{"route":"/login"}}\n'
        '{"name":"http_p95_ms","value":50,"labels":{"route":"/health"}}\n',
        encoding="utf-8",
    )
    assert oq.promql_lite("http_p95_ms", agg="max", labels={"route": "/login"}, obs_dir=tmp_path) == 200.0
    assert oq.promql_lite("http_p95_ms", agg="count", obs_dir=tmp_path) == 3.0


def test_obs_dir_accepts_str_path(tmp_path):
    # robustness：obs_dir 接受 str（非僅 Path）— 防 str/str 例外。
    from tools.fsm_runtime import observability_query as oq
    (tmp_path / "logs.ndjson").write_text('{"level":"error","msg":"x"}\n', encoding="utf-8")
    assert oq.logql_lite('{level="error"}', obs_dir=str(tmp_path)) == [{"level": "error", "msg": "x"}]


# ---------- M3: Rule Loader ----------

def test_rule_loader_load_for_state():
    from tools.fsm_runtime import rule_loader
    rules = rule_loader.load_for_state("EXECUTION_EVALUATION")
    assert any(r.id == "R-9.20" for r in rules)
    # ESCALATION 不應命中 phase-h gate 規則
    esc = rule_loader.load_for_state("ESCALATION")
    assert any(r.id == "R-9.14" for r in esc)
    assert not any(r.id == "R-9.20" for r in esc)


def _seed_rule(tmp_path):
    import yaml
    d = tmp_path / "rules"
    d.mkdir()
    (d / "R-9.99-test.yaml").write_text(yaml.safe_dump({
        "id": "R-9.99", "title": "t", "trigger_states": ["IMPLEMENTATION"],
        "severity": "low", "maturity": "active", "spec": "x", "test_ref": "x",
        "scaffold_roi": {"fire_count": 0, "catch_count": 0, "false_positive_count": 0},
    }, allow_unicode=True), encoding="utf-8")
    return d


def test_rule_loader_record_fire_and_graduation(tmp_path):
    from tools.fsm_runtime import rule_loader
    d = _seed_rule(tmp_path)
    for _ in range(rule_loader.GRADUATION_MIN_FIRES):
        rule_loader.record_fire("R-9.99", caught=False, rules_dir=d)
    r = [x for x in rule_loader.load_all(d) if x.id == "R-9.99"][0]
    assert r.scaffold_roi["fire_count"] == rule_loader.GRADUATION_MIN_FIRES
    assert rule_loader.propose_graduation(r) == "audit-only"


def test_rule_loader_set_maturity_requires_reviewer(tmp_path):
    from tools.fsm_runtime import rule_loader
    d = _seed_rule(tmp_path)
    with pytest.raises(rule_loader.RuleOverwriteProtected):
        rule_loader.set_maturity("R-9.99", "audit-only", reviewed_by="", rules_dir=d)
    r = rule_loader.set_maturity("R-9.99", "audit-only", reviewed_by="human@x", rules_dir=d)
    assert r.maturity == "audit-only"


# ---------- M5: Scaffold GC ----------

def test_scaffold_gc_run_report(tmp_path):
    from tools.fsm_runtime import scaffold_gc, rule_loader
    d = _seed_rule(tmp_path)
    for _ in range(rule_loader.GRADUATION_MIN_FIRES):
        rule_loader.record_fire("R-9.99", caught=False, rules_dir=d)
    res = scaffold_gc.run_gc(rules_dir=d, out_dir=tmp_path / "gc", today="2026-05-31")
    assert res.rules_scanned == 1
    assert any(p.rule_id == "R-9.99" for p in res.proposals)
    assert Path(res.report_path).exists()


def test_scaffold_gc_audit_decision_trace(tmp_path):
    # H-5：驗證具體分類語意，而非恆真集合成員檢查。
    from tools.fsm_runtime import scaffold_gc
    rt = _rt(tmp_path, "gc-trace", "IMPLEMENTATION")
    rt.transition("PR_REVIEW", reason="impl done", trigger="impl_complete")
    rt.transition("SPEC_AUDIT", reason="audit", trigger="impl_complete")
    rt.state.current = "ESCALATION"
    rt.transition("TERMINATED", reason="abort", trigger="escalation_abort")
    entries = scaffold_gc.audit_decision_trace(rt.state)
    outcomes = {e.trigger: e.outcome for e in entries}
    # escalation/abort trigger 必歸類 led_to_escalation
    assert outcomes.get("escalation_abort") == "led_to_escalation"
    # 一般 impl_complete 必歸類 productive
    assert "productive" in {e.outcome for e in entries}


# ---------- M6: Steersman Renderer + abort report ----------

def test_steersman_render_spec_conflict():
    from tools.fsm_runtime.steersman_renderer import render_markdown
    from tools.fsm_runtime.diagnostic import diagnose
    d = diagnose("SLV-004 FAIL: AC-003 conflicts INV-002", spec_refs=["AC-003", "INV-002"])
    md = render_markdown(d, slv_contradiction="AC-003-1「P95 < 0ms」與 INV-002 物理矛盾")
    assert "舵手" in md
    assert "sa-analyst" in md
    assert "AC-003-1" in md


def test_save_abort_report_includes_steersman(tmp_path):
    from tools.fsm_runtime.snapshot import save_abort_report
    from tools.fsm_runtime.diagnostic import diagnose
    rt = _rt(tmp_path, "abort", "ESCALATION")
    d = diagnose("SLV-004 FAIL: AC-003 conflicts INV-002", spec_refs=["AC-003", "INV-002"])
    p = save_abort_report(
        rt.state, reason="spec conflict", category="spec-conflict-test",
        diagnostic=d, slv_contradiction="AC-003-1 與 INV-002 物理矛盾",
        out_dir=tmp_path,
    )
    text = Path(p).read_text(encoding="utf-8")
    assert "舵手" in text and "sa-analyst" in text


def test_save_abort_report_backward_compatible(tmp_path):
    """無 diagnostic 時，舊呼叫端不受影響（向後相容）。"""
    from tools.fsm_runtime.snapshot import save_abort_report
    rt = _rt(tmp_path, "abort-bc", "ESCALATION")
    p = save_abort_report(rt.state, reason="x", category="bc-test", out_dir=tmp_path)
    assert Path(p).exists()


def test_act056_structural_escalation_fsm_writes_diagnostic_abort(tmp_path, monkeypatch):
    """ACT-056 / §G8 wiring：structural ESCALATION_FINAL 須由 FSM 直接產出
    含 diagnostic 的舵手級 abort 報告，而非僅回傳 diagnostic 讓 caller 自理。

    DEF-200-274 D6（pytest-xdist 導入時發現的既有測試隔離缺口）：`enter_auto_
    recovery()` 經 `save_abort_report()` 寫入**共用**的
    `build/reports/abort/ABORT-{date}-auto-recovery-refused.md`（同日同 category
    覆寫為既有設計，見 snapshot.py docstring）。多個 xdist worker 並行時，任何
    另一支測試同時觸發同一 category 都會在讀回前把內容覆寫掉，造成間歇性失敗
    （實測：`-n auto --dist worksteal` 連續多次必現）。本檔同層 `test_save_abort_
    report_backward_compatible` 與 `test_recovery_hint.py`／`test_auto_compact_
    rate_limit.py`／`test_e2e_smoke.py` 皆已把 `SNAPSHOT_DIR` 導向隔離目錄，本支
    唯獨漏了，跟進同一既有慣例即可（不是新發明的隔離手法）。
    """
    import tools.fsm_runtime.snapshot as snap_mod
    monkeypatch.setattr(snap_mod, "SNAPSHOT_DIR", tmp_path / "abort")
    rt = _rt(tmp_path, "g8-wire", "ESCALATION")
    outcome = rt.enter_auto_recovery(
        escalation_reason="SLV-004 FAIL: AC-003-1 P95<0ms 與 INV-002 矛盾",
        resume_state="PR_REVIEW",
    )
    assert outcome["entered"] is False
    assert outcome["next_state"] == "ESCALATION_FINAL"
    path = outcome.get("abort_report_path")
    assert path, "structural ESCALATION_FINAL 未產出 abort 報告（§G8 未接線）"
    content = Path(path).read_text(encoding="utf-8")
    # 證明 diagnostic 真的流入報告（舵手交棒，而非僅 retry exhausted）
    assert "sa-analyst" in content
    assert "舵手" in content or "steersman" in content.lower()


# ---------- DEF-200-364: docker 探測 controller-once 回歸鎖 ----------

class TestDockerProbeIsResolvedOnceByController(unittest.TestCase):
    """DEF-200-364 回歸鎖：pytest-xdist 每個 worker 各自 import 本模組時各自
    重新探測 docker（`docker info` timeout=10 起探測容器），`-n 13` 造成 13 路
    併發探測、部分 worker 探測失準 ⇒ 平行模式下 docker-gated 測試被誤判 skip、
    序列模式卻能通過（單檔 `-n 13` 2/2 次重現 3 skipped）。

    B 包第二棒（覆核發現的殘餘缺口）：只在測試層擋下重複探測不夠——
    production 呼叫路徑（`_docker_factory()` 經 `get_backend("docker")`）在
    測試*執行*時會獨立再呼叫一次 `docker_available()`，同樣受 13 路併發影響
    而失準。修法因而下沉：三態判斷（`resolve_docker_available()`）與唯一原始
    探測（`_probe_docker_available()`）都搬進 `sandbox_runner.py`，
    `docker_available()` 本身改讀 `SDD_DOCKER_AVAILABLE_ENV`；
    `conftest.py::pytest_configure` 在 controller 端探測恰一次並寫入該 env。
    測試模組頂層（`_DOCKER = docker_available()`）與 production 呼叫路徑現在
    讀的是**同一個**函式、**同一個** env，不再各自繞過。

    本 class 鎖住三層：
      1. `sandbox_runner.resolve_docker_available()` 本身的三態判斷（純函式，
         不依賴 docker，import 自生產面）。
      2. `conftest.py::pytest_configure` 的三分支（worker 端不探測／env 已設
         不重探／controller 端探測一次並寫回 env），以 `importlib` 動態載入
         該檔成獨立模組物件、monkeypatch 探測函式後直接呼叫，同樣不依賴真實
         docker。
      3. production 呼叫路徑（`get_backend("docker")` → `_docker_factory()`）
         確實經 `docker_available()` 讀 env 短路，不再重新探測——直接
         monkeypatch `sandbox_runner._probe_docker_available` 為會
         `self.fail()` 的 stub，若探測被重新呼叫（不論 env="0" 或 "1"）本鎖
         立刻失敗，白盒證明「同一真相源」而非僅巧合行為一致。
    """

    # ---- 1. sandbox_runner.resolve_docker_available 純函式三態判斷 ----

    def test_env_value_1_short_circuits_true_without_calling_probe(self):
        from tools.fsm_runtime.sandbox_runner import resolve_docker_available
        calls = []

        def probe():
            calls.append(1)
            return False  # 刻意回 False：驗證 "1" 分支完全不理會 probe 回傳值

        self.assertTrue(resolve_docker_available("1", probe))
        self.assertEqual(calls, [])

    def test_env_value_0_short_circuits_false_without_calling_probe(self):
        from tools.fsm_runtime.sandbox_runner import resolve_docker_available
        calls = []

        def probe():
            calls.append(1)
            return True  # 刻意回 True：驗證 "0" 分支完全不理會 probe 回傳值

        self.assertFalse(resolve_docker_available("0", probe))
        self.assertEqual(calls, [])

    def test_env_value_none_calls_probe_exactly_once_and_returns_its_result(self):
        from tools.fsm_runtime.sandbox_runner import resolve_docker_available
        calls = []

        def probe_true():
            calls.append(1)
            return True

        self.assertTrue(resolve_docker_available(None, probe_true))
        self.assertEqual(len(calls), 1)

        calls2 = []

        def probe_false():
            calls2.append(1)
            return False

        self.assertFalse(resolve_docker_available(None, probe_false))
        self.assertEqual(len(calls2), 1)

    def test_illegal_env_value_falls_back_to_probe(self):
        from tools.fsm_runtime.sandbox_runner import resolve_docker_available
        for bad_value in ("yes", "true", "2", "", " ", "TRUE", "no"):
            with self.subTest(bad_value=bad_value):
                calls = []

                def probe():
                    calls.append(1)
                    return True

                self.assertTrue(resolve_docker_available(bad_value, probe))
                self.assertEqual(len(calls), 1)

    # ---- 2. conftest.py::pytest_configure 三分支（動態載入獨立模組物件） ----

    @staticmethod
    def _load_conftest_module():
        conftest_path = Path(__file__).resolve().parent / "conftest.py"
        spec = importlib.util.spec_from_file_location(
            "sdd_def200364_conftest_dynamic", conftest_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_pytest_configure_worker_端不探測且不改動env(self):
        from tools.fsm_runtime.sandbox_runner import SDD_DOCKER_AVAILABLE_ENV
        module = self._load_conftest_module()
        calls = []
        module._controller_probe_docker_available = lambda: (calls.append(1) or True)
        fake_config = types.SimpleNamespace(workerinput={"workerid": "gw0"})
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SDD_DOCKER_AVAILABLE_ENV, None)
            module.pytest_configure(fake_config)
            self.assertEqual(calls, [], "worker 端不得呼叫 probe")
            self.assertNotIn(
                SDD_DOCKER_AVAILABLE_ENV, os.environ,
                "worker 端不得自行寫入 env（應沿用 controller 已注入的值）",
            )

    def test_pytest_configure_controller端探測一次_結果為True時寫入1(self):
        from tools.fsm_runtime.sandbox_runner import SDD_DOCKER_AVAILABLE_ENV
        module = self._load_conftest_module()
        calls = []
        module._controller_probe_docker_available = lambda: (calls.append(1) or True)
        fake_config = types.SimpleNamespace()  # 無 workerinput 屬性 == controller
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SDD_DOCKER_AVAILABLE_ENV, None)
            module.pytest_configure(fake_config)
            self.assertEqual(len(calls), 1, "controller 端必須探測恰一次")
            self.assertEqual(os.environ.get(SDD_DOCKER_AVAILABLE_ENV), "1")

    def test_pytest_configure_controller端探測一次_結果為False時寫入0(self):
        from tools.fsm_runtime.sandbox_runner import SDD_DOCKER_AVAILABLE_ENV
        module = self._load_conftest_module()
        calls = []
        module._controller_probe_docker_available = lambda: (calls.append(1) or False)
        fake_config = types.SimpleNamespace()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SDD_DOCKER_AVAILABLE_ENV, None)
            module.pytest_configure(fake_config)
            self.assertEqual(len(calls), 1, "controller 端必須探測恰一次")
            self.assertEqual(os.environ.get(SDD_DOCKER_AVAILABLE_ENV), "0")

    def test_pytest_configure_env已預設時尊重覆寫不重探(self):
        from tools.fsm_runtime.sandbox_runner import SDD_DOCKER_AVAILABLE_ENV
        module = self._load_conftest_module()
        calls = []
        module._controller_probe_docker_available = lambda: (calls.append(1) or True)
        fake_config = types.SimpleNamespace()
        with patch.dict(os.environ, {}, clear=False):
            os.environ[SDD_DOCKER_AVAILABLE_ENV] = "0"
            module.pytest_configure(fake_config)
            self.assertEqual(calls, [], "呼叫端已顯式設定時不得重探")
            self.assertEqual(os.environ.get(SDD_DOCKER_AVAILABLE_ENV), "0")

    # ---- 3. production 呼叫路徑（get_backend("docker")）讀 env 短路，不重探 ----

    def test_docker_factory_reads_env_without_reprobing(self):
        """DEF-200-364 覆核發現的殘餘缺口白盒證明：`_docker_factory()` 經
        `get_backend("docker")` 呼叫 `docker_available()` 時，必須直接讀
        `SDD_DOCKER_AVAILABLE_ENV` 短路，**不得**再次呼叫
        `_probe_docker_available()`——monkeypatch 成會 `self.fail()` 的 stub，
        若探測被重新觸發本測試立刻失敗（而非僅比對行為輸出）。
        """
        import tools.fsm_runtime.sandbox_runner as sr

        def _must_not_be_called():
            self.fail("_docker_factory() 不應在 env 已設時重新呼叫探測函式")

        with patch.dict(os.environ, {sr.SDD_DOCKER_AVAILABLE_ENV: "0"}, clear=False):
            with patch.object(sr, "_probe_docker_available", _must_not_be_called):
                with self.assertRaises(NotImplementedError):
                    sr.get_backend("docker")

        with patch.dict(os.environ, {sr.SDD_DOCKER_AVAILABLE_ENV: "1"}, clear=False):
            with patch.object(sr, "_probe_docker_available", _must_not_be_called):
                backend = sr.get_backend("docker")
                self.assertIsInstance(backend, sr.DockerBackend)


# ---------- DEF-200-367: 三支 docker 測試容器名不得撞名 ----------

class TestDockerTestContainerNamesDoNotCollide(unittest.TestCase):
    """DEF-200-367 回歸鎖：`test_docker_backend_real_pass`／
    `test_docker_backend_real_runtime_fail`／`test_docker_backend_e2e_through_fsm`
    三支測試原本都用 `SandboxSpec(app_id="demo", ...)`、未設 `track_id`。

    WHY：`sandbox_runner.track_container_name(app_id, track_id)` 在 `track_id`
    為 `None`（falsy）時只用 `app_id` 組出容器名（`sdd-{app_id}`），三支測試因而
    對 `docker run --name` 算出**相同**的容器名 `sdd-demo`。pytest-xdist
    `-n 13` 下三者若被排到不同 worker 併發執行，`docker run --name sdd-demo`
    對同一個名字撞名，其中一次容器實跑因而失敗（exit 非 0 或輸出被搶佔）
    ⇒ OQS verdict ≠ pass、FSM 未轉移到預期狀態（單檔 `-n 13` 3/3 次重現；全套
    跑法因負載稀釋、排程通常不會讓這三者剛好同時執行而看不到）。

    修法（DEF-200-364 B 包第三棒）：三支測試改經 `_docker_spec(kind)`
    （模組層 helper，測試本體與本鎖共用同一份定義）建構 spec，各自帶不同
    `track_id`（`"h-real-pass"`／`"h-runtime-fail"`／`"h-e2e-fsm"`），讓
    `track_container_name(app_id, track_id)` 兩兩相異——這正是 `track_id`
    這個既有欄位本來就存在的用途（ACT-070 艦隊並行 N 軌不撞名），不改生產面
    命名規則本身。本鎖不依賴真實 docker：純粹核對三個 spec 算出的容器名字串
    兩兩相異，失敗時印出完整撞名分組供除錯。
    """

    def test_three_docker_test_specs_have_distinct_container_names(self):
        from tools.fsm_runtime.sandbox_runner import track_container_name

        names = {}
        for kind in _DOCKER_TEST_KINDS:
            spec = _docker_spec(kind)
            names[kind] = track_container_name(spec.app_id, spec.track_id)

        distinct = set(names.values())
        if len(distinct) != len(_DOCKER_TEST_KINDS):
            groups: dict = {}
            for kind, name in names.items():
                groups.setdefault(name, []).append(kind)
            collisions = {name: kinds for name, kinds in groups.items() if len(kinds) > 1}
            self.fail(
                "三支 docker 測試的容器名應兩兩相異，但偵測到撞名："
                f"{collisions!r}（完整對照：{names!r}）"
            )
