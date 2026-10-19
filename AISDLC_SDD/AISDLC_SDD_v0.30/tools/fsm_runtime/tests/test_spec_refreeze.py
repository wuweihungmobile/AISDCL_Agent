# enforces (governance rules): R-9.1, R-9.6
"""OBS-SI-108（F-17）：`spec-refreeze` 的守護測試。

為什麼有這個動詞：功能鍵在 `IMPLEMENTATION→SPEC_AUDIT` 修訂規格後只能出邊到 `PR_REVIEW`，而 `spec-frozen` 只在
HUMAN_PENDING 合法，所以 `frozen_stages[*].spec_doc_digests` 永遠停在修訂前的值——之後每個消費凍結摘要的面
（AutoClaude adapter 的 `check_digest` 實證拋 `SpecDigestMismatchError`、人讀狀態檔）都判不符。`spec-refreeze`
在 SPEC_AUDIT／RELEASE_READY／RELEASE 以**追加**一筆 `kind: refreeze` 條目重記摘要，不新增狀態、不新增邊。

每一組都編碼「拿掉修法會怎樣」（Rule 9）：改寫舊條目 ⇒ 「舊條目逐位元不變」案紅；重記偷偷歸零 retry 計數
⇒ 「不碰計數」案紅（那會變成洗掉 R-9.1 重試預算的後門）；重記換了 stage ⇒ 「stage key 不變」案紅（那會洗掉
每階段 auto-compact 上限）；先算摘要才驗狀態 ⇒ 「狀態不對時不讀檔」案紅；改了就存、失敗留半套 ⇒ 「失敗時
位元組不變」案紅。
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest
import yaml

_V_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_V_ROOT))

from tools.fsm_runtime import snapshot  # noqa: E402
from tools.fsm_runtime import state_loader as sl  # noqa: E402
from tools.fsm_runtime import transition_rules as tr  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.transition_rules import TransitionError  # noqa: E402

_PROJECT = "refreeze-proj"
_ALLOWED = ("SPEC_AUDIT", "RELEASE_READY", "RELEASE")
_ILLEGAL = sorted(set(tr.all_states()) - set(_ALLOWED))
_DOC_A = "docs/03_testing/contracts/TCS-A.md"
_DOC_B = "docs/01_requirements/FRD-B.md"
_OLD = {_DOC_A: "sha256:" + "a" * 64, _DOC_B: "sha256:" + "b" * 64}
_NEW_A = "sha256:" + "c" * 64
_README = _V_ROOT / "tools" / "fsm_runtime" / "README.md"
_CLI = [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "tools.fsm_runtime.fsm_runtime"]


# ───────────────────────────── 共用小工具 ─────────────────────────────
def _frozen_runtime(tmp_path: Path, current: str = "SPEC_AUDIT") -> FSMRuntime:
    """「已凍結過一次（Stage-1、兩份文件、帶摘要與核准人）、現在處於 `current`」的真 runtime（已存檔）。
    重點是被測的重記，不是怎麼走到 `current`，所以凍結後直接改狀態再存檔。"""
    state = sl.load_state(_PROJECT, path=tmp_path / "FSM-STATE-refreeze.yaml")
    state.current = "HUMAN_PENDING"
    runtime = FSMRuntime(state)
    runtime.record_spec_frozen(
        "Stage-1", [_DOC_A, _DOC_B], spec_doc_digests=dict(_OLD), approved_by="alice", reason="freeze"
    )
    state.current = current
    sl.save_state(state)
    return runtime


def _effective_digests(frozen_stages: list) -> dict:
    """文件化的讀端契約：全部條目的 `spec_doc_digests` 取聯集、同鍵後者勝出。AutoClaude
    `_sdd_frozen_gate.check_digest` 與 Bridge `frozen_digest_of` 都是這條規則；本專案不得 import 它們
    （ADR-XPLAT-010 §2.1），所以在這裡用三行重述這份契約——讀 `[-1]` 單筆是錯的（見下方測試）。"""
    merged: dict = {}
    for entry in frozen_stages:
        merged.update(entry.get("spec_doc_digests") or {})
    return merged


# ───────────────────────────── API 層：只追加、欄位、不轉態 ─────────────────────────────
def test_refreeze_appends_one_entry_and_leaves_the_original_freeze_untouched(tmp_path: Path) -> None:
    runtime = _frozen_runtime(tmp_path)
    state = runtime.state
    original = copy.deepcopy(state.root["frozen_stages"][0])
    reason = "SPEC_AUDIT 期間改了 TCS §3 路徑字面（commit abc123）"

    result = runtime.record_spec_refreeze(
        [_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason=reason, approved_by="bob"
    )

    stages = state.root["frozen_stages"]
    assert len(stages) == 2
    assert stages[0] == original, "只追加：舊條目逐欄不變（留作歷史），不是原地改寫"
    entry = stages[1]
    assert set(entry) == {"stage", "frozen_at", "spec_docs", "spec_doc_digests", "approved_by",
                          "kind", "supersedes", "reason"}
    assert entry["stage"] == "Stage-1", "stage 取最近一筆凍結的 stage——重記不是新階段"
    assert entry["kind"] == "refreeze" and entry["supersedes"] == original["frozen_at"]
    assert entry["spec_docs"] == [_DOC_A] and entry["spec_doc_digests"] == {_DOC_A: _NEW_A}
    assert entry["approved_by"] == "bob" and entry["reason"] == reason
    assert result == {"refrozen": True, "stage": "Stage-1", "supersedes": original["frozen_at"],
                      "spec_doc_digests": {_DOC_A: _NEW_A}}
    assert state.current == "SPEC_AUDIT", "不轉態：重記是一筆稽核資料，不是狀態轉移"
    on_disk = sl.load_state(_PROJECT, path=state.path, create_if_missing=False)
    assert on_disk.root["frozen_stages"] == stages, "必須存檔：記憶體裡的重記對下一個行程等於沒發生"


def test_refreeze_writes_a_trace_entry_with_from_equal_to_and_the_verbatim_reason(tmp_path: Path) -> None:
    runtime = _frozen_runtime(tmp_path)
    reason = "  勘誤：路徑字面  "  # 前後空白也原樣進稽核憑證
    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason=reason)
    trace = runtime.state.decision_trace()[-1]
    assert (trace["from"], trace["to"], trace["trigger"]) == ("SPEC_AUDIT", "SPEC_AUDIT", "spec_refreeze")
    assert trace["reason"] == reason and trace["spec_refs"] == [_DOC_A]


def test_approver_is_optional_and_only_present_when_given(tmp_path: Path) -> None:
    runtime = _frozen_runtime(tmp_path)
    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")
    assert "approved_by" not in runtime.state.root["frozen_stages"][-1]


def test_a_second_refreeze_supersedes_the_first_refreeze_not_the_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """supersedes 串成鏈（被取代的是「最近一筆」，不論它是凍結還是重記）。時間戳是秒級——不固定時鐘的話
    同一秒內的條目 frozen_at 會相同，這個斷言就沒有鑑別力。"""
    ticks = itertools.count()
    monkeypatch.setattr(sl, "_now", lambda: f"tick-{next(ticks):06d}")  # 不透明但嚴格遞增的時間戳
    runtime = _frozen_runtime(tmp_path)
    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: "sha256:" + "1" * 64}, reason="first")
    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: "sha256:" + "2" * 64}, reason="second")
    first, second, third = runtime.state.root["frozen_stages"]
    assert len({first["frozen_at"], second["frozen_at"], third["frozen_at"]}) == 3, "前提：三筆時間戳互異"
    assert second["supersedes"] == first["frozen_at"]
    assert third["supersedes"] == second["frozen_at"]
    assert "kind" not in first, "原凍結條目不得被補寫 kind：舊格式條目沒有 kind＝凍結"


def test_refreeze_never_touches_retry_counts_or_the_freeze_counter(tmp_path: Path) -> None:
    """重記不是新的 SPEC_FROZEN 里程碑。若它偷偷歸零 retry 計數，就成了洗掉 R-9.1 重試預算的後門
    （spec-frozen 會歸零那三個 gate，正是因為它是新週期的起點）。"""
    runtime = _frozen_runtime(tmp_path)
    for gate, count in (("SCG_VALIDATION", 2), ("PR_REVIEW", 3), ("RTM_VERIFY", 1), ("RELEASE_READY", 1)):
        runtime.state.retry(gate)["current_count"] = count
    cumulative_before = copy.deepcopy(runtime.state.cumulative())
    retry_before = copy.deepcopy(runtime.state.root["retry_history"])

    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")

    assert runtime.state.root["retry_history"] == retry_before
    assert runtime.state.cumulative() == cumulative_before
    assert runtime.state.cumulative()["total_spec_frozen_count"] == 1


def test_refreeze_keeps_the_stage_key_so_the_auto_compact_cap_is_not_reset(tmp_path: Path) -> None:
    """`current_stage_key()` 讀 `frozen_stages[-1].stage`，而每階段 auto-compact 上限（Rule 9.9）以它為界：
    重記若換了 stage，就等於替自己洗掉一次上限。"""
    runtime = _frozen_runtime(tmp_path)
    before = runtime.current_stage_key()
    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")
    assert runtime.current_stage_key() == before == "Stage-1"


# ───────────────────────────── 合法／非法狀態（正控＋窮舉負控） ─────────────────────────────
@pytest.mark.parametrize("current", _ALLOWED)
def test_refreeze_is_allowed_in_the_three_legal_states(tmp_path: Path, current: str) -> None:
    runtime = _frozen_runtime(tmp_path, current)
    result = runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="erratum")
    assert result["refrozen"] is True and runtime.state.current == current


def test_the_legal_state_set_is_exactly_the_three_the_ruling_names() -> None:
    assert FSMRuntime.SPEC_REFREEZE_ALLOWED_STATES == frozenset(_ALLOWED)
    assert set(_ALLOWED) <= set(tr.all_states()), "狀態更名時這裡要大聲失敗，而不是讓白名單悄悄指向不存在的狀態"


@pytest.mark.parametrize("current", _ILLEGAL)
def test_every_other_state_refuses_a_refreeze_and_changes_nothing(tmp_path: Path, current: str) -> None:
    """窮舉負控：全部狀態扣掉三個合法的，一個都不准。SPEC_DRAFTING／HUMAN_PENDING 的修訂之後本來就要走
    `spec-frozen` 人工閘；IMPLEMENTATION 起 R-9.6 禁止改規格，沒有「合法修訂」可重記。"""
    runtime = _frozen_runtime(tmp_path, current)
    before_bytes = runtime.state.path.read_bytes()
    before_memory = copy.deepcopy(runtime.state.to_dict())
    with pytest.raises(TransitionError) as caught:
        runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")
    for legal in _ALLOWED:
        assert legal in str(caught.value), "訊息要指出合法狀態"
    assert runtime.state.path.read_bytes() == before_bytes
    assert runtime.state.to_dict() == before_memory, "失敗時連記憶體都不得改動"


def test_refreeze_without_any_prior_freeze_is_refused(tmp_path: Path) -> None:
    """重記是「重新背書一次既有的凍結」；從沒凍結過的檔沒有東西可取代，第一次凍結走 `spec-frozen`。"""
    state = sl.load_state(_PROJECT, path=tmp_path / "FSM-STATE-never-frozen.yaml")
    state.current = "RELEASE"
    sl.save_state(state)
    before = state.path.read_bytes()
    with pytest.raises(TransitionError, match="no entry to supersede"):
        FSMRuntime(state).record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")
    assert state.path.read_bytes() == before


@pytest.mark.parametrize("bad", [{"reason": ""}, {"reason": "   "}, {"digests": {}}])
def test_blank_reason_or_empty_digests_are_refused_without_touching_anything(tmp_path: Path, bad: dict) -> None:
    runtime = _frozen_runtime(tmp_path)
    before = runtime.state.path.read_bytes()
    memory = copy.deepcopy(runtime.state.to_dict())
    with pytest.raises(ValueError):
        runtime.record_spec_refreeze(
            [_DOC_A], spec_doc_digests=bad.get("digests", {_DOC_A: _NEW_A}), reason=bad.get("reason", "ok")
        )
    assert runtime.state.path.read_bytes() == before and runtime.state.to_dict() == memory


# ───────────────────────────── 讀端相容與讀端契約 ─────────────────────────────
def test_entries_without_a_kind_key_read_as_freeze() -> None:
    """舊格式條目沒有 kind 鍵＝凍結：真機狀態檔不必手改，所有讀端一律走 freeze_entry_kind。"""
    assert sl.freeze_entry_kind({"stage": "S"}) == "freeze"
    assert sl.freeze_entry_kind({"stage": "S", "kind": None}) == "freeze"
    assert sl.freeze_entry_kind({"kind": "refreeze"}) == "refreeze"
    assert sl.freeze_entry_kind("garbage") == "freeze"


def test_a_refreeze_on_top_of_a_minimal_legacy_entry_still_works(tmp_path: Path) -> None:
    """最老的狀態檔只有 `{"stage": ...}`（沒有 frozen_at／digests）：重記照樣成立，supersedes 老實記 None。"""
    runtime = _frozen_runtime(tmp_path)
    runtime.state.root["frozen_stages"] = [{"stage": "Legacy-1"}]
    result = runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")
    assert result["stage"] == "Legacy-1" and result["supersedes"] is None


def test_readers_taking_the_union_with_later_wins_get_the_latest_digest_and_keep_the_other_docs(
    tmp_path: Path,
) -> None:
    """F-17 的症狀與修法在讀端的樣子：修訂後原條目的 A 摘要過期（讀端判不符）；重記後聯集裡 A 是新值、B 沿用舊值。
    重記條目只含被點名的文件，所以讀 `[-1]` 單筆會漏掉 B——這就是模板與 README 要求「取全部條目聯集」的原因。"""
    runtime = _frozen_runtime(tmp_path)
    assert _effective_digests(runtime.state.root["frozen_stages"]) == _OLD

    runtime.record_spec_refreeze([_DOC_A], spec_doc_digests={_DOC_A: _NEW_A}, reason="x")

    stages = runtime.state.root["frozen_stages"]
    assert _effective_digests(stages) == {_DOC_A: _NEW_A, _DOC_B: _OLD[_DOC_B]}
    assert stages[-1]["spec_doc_digests"] == {_DOC_A: _NEW_A}, "刻意只含被重新背書的文件（誠實的稽核軌跡）"


def test_the_context_snapshot_marks_refreeze_rows_instead_of_reading_them_as_a_new_stage() -> None:
    rows = snapshot._fmt_frozen_stages([
        {"stage": "Stage-1", "frozen_at": "T1", "compaction_report": None},
        {"stage": "Stage-1", "frozen_at": "T2", "kind": "refreeze"},
    ]).splitlines()
    assert rows[0] == "| Stage-1 | T1 | — |"
    assert rows[1] == "| Stage-1（refreeze） | T2 | — |"


# ───────────────────────────── CLI 層：真子行程、真磁碟 ─────────────────────────────
class _Run:
    def __init__(self, proc: subprocess.CompletedProcess) -> None:
        self.rc, self.stdout, self.stderr = proc.returncode, proc.stdout, proc.stderr

    @property
    def out_lines(self) -> list[str]:
        return [ln for ln in self.stdout.splitlines() if ln.strip()]

    @property
    def err_lines(self) -> list[str]:
        return [ln for ln in self.stderr.splitlines() if ln.strip()]

    @property
    def payload(self) -> dict:
        return json.loads(self.out_lines[-1])


def _run(state_dir: Path, *argv: str, env_extra: Optional[dict] = None) -> _Run:
    env = {k: v for k, v in os.environ.items() if k not in ("SDD_STATE_DIR", "SDD_PROJECT", "PYTHONPATH")}
    env.update({"SDD_STATE_DIR": str(state_dir), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(_V_ROOT), "COLUMNS": "10000"})
    env.update(env_extra or {})
    return _Run(subprocess.run([*_CLI, *argv], cwd=str(_V_ROOT), env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120))


@pytest.fixture()
def sdd_dir(tmp_path: Path) -> Path:
    """慣例形狀的狀態目錄 `<專案根>/build/reports/fsm`（專案根＝`sdd_dir.parents[2]`）。"""
    path = tmp_path / "proj" / "build" / "reports" / "fsm"
    path.mkdir(parents=True)
    return path


def _state_path(sdd_dir: Path) -> Path:
    return sdd_dir / f"FSM-STATE-{sl._sanitize_component(_PROJECT)}.yaml"


def _state_at(sdd_dir: Path, current: str) -> Path:
    """在 CLI 的狀態目錄造一個處於 `current`、從未凍結過的狀態檔。"""
    path = _state_path(sdd_dir)
    state = sl.load_state(_PROJECT, path=path)
    state.current = current
    sl.save_state(state)
    return path


def _frozen_state_file(sdd_dir: Path, current: str) -> Path:
    """在 CLI 的狀態目錄造一個「已凍結一次、現在處於 `current`」的狀態檔（用 API 造，省去多餘的子行程）。"""
    path = _state_at(sdd_dir, "HUMAN_PENDING")
    state = sl.load_state(_PROJECT, path=path, create_if_missing=False)
    FSMRuntime(state).record_spec_frozen(
        "Stage-1", [_DOC_A, _DOC_B], spec_doc_digests=dict(_OLD), approved_by="alice", reason="freeze"
    )
    state.current = current
    sl.save_state(state)
    return path


def _read(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["fsm_state"]


def _doc(sdd_dir: Path, name: str = "TCS-X.md", raw: bytes = b"# AT-001-1-1\r\nline\r\n") -> Path:
    doc = sdd_dir.parents[2] / "docs" / "03_testing" / "contracts" / name
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(raw)
    return doc


def _lf_digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def _assert_single_line_ascii_json(result: _Run) -> dict:
    assert len(result.out_lines) == 1, f"stdout 不是恰好一行：{result.stdout!r}"
    result.stdout.encode("ascii")
    assert result.out_lines[0] == json.dumps(result.payload, ensure_ascii=True, separators=(",", ":"))
    return result.payload


def _assert_failure(result: _Run, *, rc: int, error: str) -> dict:
    assert result.rc == rc, (result.rc, result.stdout, result.stderr)
    payload = _assert_single_line_ascii_json(result)
    assert payload["ok"] is False and payload["error"] == error, payload
    assert len(result.err_lines) == 1 and result.err_lines[0].startswith(f"[SDD-FSM] spec-refreeze failed: {error}: ")
    return payload


def test_cli_the_real_f17_route_ends_with_a_current_digest(sdd_dir: Path) -> None:
    """F-17 的真實路徑（每一步都是獨立行程）：HUMAN_PENDING →`spec-frozen --digest`→ SPEC_FROZEN → IMPLEMENTATION
    → SPEC_AUDIT（此時改規格）→ `spec-refreeze`。修訂後、重記前，讀端的有效摘要＝舊值（≠檔案現況＝判不符）；
    重記後＝檔案現況。再走 `transition --to PR_REVIEW` 證明這個動詞沒有擾動流程。"""
    path = _state_at(sdd_dir, "HUMAN_PENDING")
    key = "docs/03_testing/contracts/TCS-X.md"
    doc = _doc(sdd_dir, raw=b"# AT-001-1-1\r\nold\r\n")
    frozen = _run(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "Stage-1", "--digest", "--json",
                  "--approver", "alice", "--reason", "freeze", "--doc", key)
    assert frozen.rc == 0, (frozen.stdout, frozen.stderr)
    for target in ("IMPLEMENTATION", "SPEC_AUDIT"):
        assert _run(sdd_dir, "transition", "--project", _PROJECT, "--to", target, "--reason", "walk").rc == 0
    revised = b"# AT-001-1-1\r\nrevised path literal\r\n"
    doc.write_bytes(revised)
    stale = _effective_digests(_read(path)["frozen_stages"])
    assert stale == {key: _lf_digest(b"# AT-001-1-1\r\nold\r\n")} and stale[key] != _lf_digest(revised), "前提：F-17 症狀"

    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--doc", key, "--approver", "bob",
                  "--root", str(sdd_dir.parents[2]), "--reason", "SPEC_AUDIT: revised path literal in TCS (commit abc123)")

    assert result.rc == 0 and result.err_lines == [], (result.rc, result.stdout, result.stderr)
    payload = _assert_single_line_ascii_json(result)
    state_after = _read(path)
    assert payload == {
        "ok": True, "verb": "spec-refreeze", "project": _PROJECT, "from_state": "SPEC_AUDIT",
        "current_state": "SPEC_AUDIT", "refrozen": True, "stage": "Stage-1",
        "supersedes": state_after["frozen_stages"][0]["frozen_at"], "spec_doc_digests": {key: _lf_digest(revised)},
    }
    assert len(state_after["frozen_stages"]) == 2 and state_after["current_state"] == "SPEC_AUDIT"
    assert state_after["frozen_stages"][1]["kind"] == "refreeze"
    assert state_after["frozen_stages"][1]["approved_by"] == "bob"
    assert _effective_digests(state_after["frozen_stages"]) == {key: _lf_digest(revised)}
    assert state_after["decision_trace"][-1]["trigger"] == "spec_refreeze"
    assert _run(sdd_dir, "transition", "--project", _PROJECT, "--to", "PR_REVIEW", "--reason", "continue").rc == 0


@pytest.mark.parametrize("current", _ALLOWED)
def test_cli_refreeze_succeeds_in_each_legal_state(sdd_dir: Path, current: str) -> None:
    path = _frozen_state_file(sdd_dir, current)
    _doc(sdd_dir)
    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--reason", "erratum",
                  "--doc", "docs/03_testing/contracts/TCS-X.md")
    assert result.rc == 0, (result.stdout, result.stderr)
    assert result.payload["from_state"] == result.payload["current_state"] == current
    assert _read(path)["frozen_stages"][-1]["kind"] == "refreeze"


@pytest.mark.parametrize("current", ["HUMAN_PENDING", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW", "ESCALATION"])
def test_cli_refreeze_in_the_wrong_state_is_rc3_even_when_the_doc_is_also_bad(sdd_dir: Path, current: str) -> None:
    """優先序：前置狀態先於摘要——狀態不對時根本不該去讀檔（也不洩漏檔案存在與否），狀態檔位元組不變。"""
    path = _frozen_state_file(sdd_dir, current)
    before = path.read_bytes()
    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--reason", "x", "--doc", "docs/missing.md")
    payload = _assert_failure(result, rc=3, error="transition_not_allowed")
    assert payload["current_state"] == current and "SPEC_AUDIT" in payload["detail"]
    assert path.read_bytes() == before


def test_cli_refreeze_without_a_prior_freeze_is_rc3(sdd_dir: Path) -> None:
    path = _state_at(sdd_dir, "RELEASE")
    before = path.read_bytes()
    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--reason", "x", "--doc", "docs/x.md")
    payload = _assert_failure(result, rc=3, error="transition_not_allowed")
    assert "supersede" in payload["detail"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("case", ["missing", "outside_root", "directory"])
def test_cli_refreeze_with_a_bad_doc_is_rc4_and_leaves_the_state_byte_identical(sdd_dir: Path, case: str) -> None:
    """先驗前置、再算摘要、最後才改狀態：好文件排在前面也不得「部分成功」。"""
    path = _frozen_state_file(sdd_dir, "SPEC_AUDIT")
    before = path.read_bytes()
    root = sdd_dir.parents[2]
    (root.parent / "outside.md").write_text("outside", encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    _doc(sdd_dir)
    bad, error = {
        "missing": ("docs/03_testing/contracts/NOPE.md", "doc_not_found"),
        "outside_root": ("../outside.md", "doc_outside_root"),
        "directory": ("docs", "doc_not_found"),
    }[case]
    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--reason", "x",
                  "--doc", "docs/03_testing/contracts/TCS-X.md", "--doc", bad)
    _assert_failure(result, rc=4, error=error)
    assert path.read_bytes() == before


def test_cli_refreeze_argument_errors_are_rc4_and_leave_the_file_untouched(sdd_dir: Path) -> None:
    path = _frozen_state_file(sdd_dir, "SPEC_AUDIT")
    _doc(sdd_dir)
    before = path.read_bytes()
    doc = ("--doc", "docs/03_testing/contracts/TCS-X.md")
    for argv in (
        ["--reason", "", *doc],                       # 缺理由
        ["--reason", "   ", *doc],                    # 空白理由
        ["--reason", "x"],                            # 沒給 --doc
        ["--reason", "x", "--approver", "   ", *doc],  # 核准人空白
        ["--reason", "x", "--approver", "a" * 101, *doc],
        ["--reason", "x", "--root", "relative/root", *doc],
        ["--reason", "x", "--root", str(sdd_dir.parents[2] / "does-not-exist"), *doc],
    ):
        _assert_failure(_run(sdd_dir, "spec-refreeze", "--project", _PROJECT, *argv), rc=4, error="invalid_argument")
    assert path.read_bytes() == before


def test_cli_refreeze_requires_an_explicit_project_and_refuses_a_stage(sdd_dir: Path) -> None:
    """缺 `--project` 會退回 SDD_PROJECT／目錄名推導的專案鍵（框架自身的專案鍵也是合法專案）——一次手滑
    就改到別的專案，所以比照橋接動詞要求顯式。`--stage` 靜默忽略會讓人以為自己指定了 stage，所以拒絕。"""
    _frozen_state_file(sdd_dir, "SPEC_AUDIT")
    no_project = _run(sdd_dir, "spec-refreeze", "--reason", "x", "--doc", "docs/x.md",
                      env_extra={"SDD_PROJECT": _PROJECT})
    assert no_project.rc == 2 and no_project.stdout == "" and "--project" in no_project.stderr
    with_stage = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--stage", "Stage-9", "--reason", "x",
                      "--doc", "docs/x.md")
    assert with_stage.rc == 2 and with_stage.stdout == "" and "--stage" in with_stage.stderr


def test_cli_refreeze_state_file_problems_are_rc5_and_never_create_a_file(sdd_dir: Path) -> None:
    ghost = _run(sdd_dir, "spec-refreeze", "--project", "no-such-project", "--reason", "x", "--doc", "docs/x.md")
    _assert_failure(ghost, rc=5, error="state_not_found")
    assert list(sdd_dir.iterdir()) == [], "恆視為已帶 --must-exist：不得替不存在的專案建檔"
    _state_path(sdd_dir).write_text("fsm_state: [not, a, mapping\n", encoding="utf-8")
    unreadable = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--reason", "x", "--doc", "docs/x.md")
    _assert_failure(unreadable, rc=5, error="state_unreadable")


def test_cli_refreeze_with_two_docs_records_posix_keys_and_ignores_the_no_op_flags(sdd_dir: Path) -> None:
    """`--digest`／`--json` 對 spec-refreeze 是不需要的（摘要恆算、輸出恆為單行 JSON），給了也無妨；
    兩份文件（一相對、一絕對）都以 POSIX 相對 root 的鍵記，順序照 --doc。"""
    path = _frozen_state_file(sdd_dir, "SPEC_AUDIT")
    a = _doc(sdd_dir, "TCS-A.md", b"a\r\n")
    b = _doc(sdd_dir, "TCS-B.md", b"b\n")
    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--reason", "x", "--digest", "--json",
                  "--doc", "docs/03_testing/contracts/TCS-A.md", "--doc", str(b))
    assert result.rc == 0, (result.stdout, result.stderr)
    keys = ["docs/03_testing/contracts/TCS-A.md", "docs/03_testing/contracts/TCS-B.md"]
    entry = _read(path)["frozen_stages"][-1]
    assert entry["spec_docs"] == keys
    assert entry["spec_doc_digests"] == {keys[0]: _lf_digest(a.read_bytes()), keys[1]: _lf_digest(b.read_bytes())}


def test_cli_refreeze_round_trips_a_non_ascii_reason_and_approver_with_ascii_only_stdout(sdd_dir: Path) -> None:
    """實際使用者會用中文寫理由與核准人：stdout／stderr 只能是 ASCII（CLI 入口無 UTF-8 stdio 保護，cp950 下
    非 ASCII 會 UnicodeEncodeError），但中文必須原樣進 YAML 的 decision_trace 與重記條目。"""
    path = _frozen_state_file(sdd_dir, "RELEASE")
    _doc(sdd_dir)
    reason = "規格勘誤二：TCS 搬遷後殘留舊路徑字面（commit abc123）"
    result = _run(sdd_dir, "spec-refreeze", "--project", _PROJECT, "--approver", "主控", "--reason", reason,
                  "--doc", "docs/03_testing/contracts/TCS-X.md")
    assert result.rc == 0 and result.err_lines == [], (result.rc, result.stdout, result.stderr)
    _assert_single_line_ascii_json(result)
    state = _read(path)
    assert state["frozen_stages"][-1]["reason"] == reason and state["frozen_stages"][-1]["approved_by"] == "主控"
    assert state["decision_trace"][-1]["reason"] == reason


# ───────────────────────────── README 與 CLI 不得各說各話 ─────────────────────────────
def test_readme_subcommand_table_and_count_match_the_cli_choices() -> None:
    """README 宣稱「子命令（共 N 個）」並逐一列表；新增動詞卻忘了改文件是這類缺陷的老樣子。
    以 `--help` 的 positional 選項為實況（COLUMNS 開很寬，避免 argparse 折行）。"""
    help_text = _run(Path(_V_ROOT), "--help").stdout
    positional = help_text.split("positional arguments:", 1)[1]
    choices = set(re.search(r"\{([a-z,\-]+)\}", positional).group(1).split(","))  # type: ignore[union-attr]
    readme = _README.read_text(encoding="utf-8")
    claims = [int(n) for n in re.findall(r"子命令（共 (\d+) 個）", readme)]
    claims += [int(n) for n in re.findall(r"CLI（(\d+) 個子命令）", readme)]  # 「檔案結構」段的第二個宣稱站點
    section = readme.split("### 子命令", 1)[1].split("\n### ", 1)[0]
    listed = set(re.findall(r"^\| `([a-z\-]+)` \|", section, flags=re.MULTILINE))
    assert listed == choices, f"README 表與 CLI 不一致：只在 README={sorted(listed - choices)}、只在 CLI={sorted(choices - listed)}"
    assert len(claims) >= 2, "README 的兩個宣稱站點（子命令表標題、檔案結構）有一個消失了"
    assert set(claims) == {len(choices)}, f"README 宣稱 {claims}，CLI 實有 {len(choices)} 個"
