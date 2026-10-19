"""BR-27：`POST /sdd/fsm/{project}:freeze`——Console 路徑上唯一的 FSM 寫入動詞（人工閘；D-115-03）。

以假 SDD 樹真起 CLI 子行程（tests/fake_sdd.py）：斷言檢查順序、每一格錯誤碼、摘要由 CLI 寫入且與獨
立計算的值逐值相等、稽核、序列化，以及「被拒的請求一個位元組都不改狀態檔、也不起 CLI」。
ADR-XPLAT-016 §4.3、§4.4、§6.3①、§9；契約 v1.5 §3.1.4 (d)。
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from app import sdd_cli
from app.settings import Settings
from tests.fake_sdd import make_fake_sdd, read_calls, read_state, seed_state, set_control

TOKEN = "freeze-token-" + "f" * 32
TCS_REL = "docs/03_testing/contracts/TCS-Alpha-20261017.md"
TCS_TEXT = ("# TCS Alpha\n\n| AC | AT |\n|---|---|\n| AC-001-1 | AT-001-1-1 |\n\n"
            "THEN 「[AT_OK_1]」\n")
_FSM = Path("build") / "reports" / "fsm"


def _digest(text: str) -> str:
    """獨立於產品碼的算法（ADR §4.3）：換行正規化後的 UTF-8 文字的 sha256。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_sdd(tmp_path / "sdd")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """專案根（在 allowed roots 之下）：規格檔放在 docs/03_testing/contracts/，FSM 狀態在
    build/reports/fsm。"""
    path = tmp_path / "projects" / "alpha"
    (path / Path(TCS_REL).parent).mkdir(parents=True)
    (path / TCS_REL).write_text(TCS_TEXT, encoding="utf-8", newline="")
    (path / "docs" / "readme.md").write_text("# readme\n", encoding="utf-8")
    seed_state(path / _FSM, "alpha", "HUMAN_PENDING")
    return path


@pytest.fixture
def live(make_bridge, settings: Settings, fake: Path):
    return make_bridge(replace(settings, sdd_root=fake, sdd_write_token=TOKEN))


def _body(project_root: Path, **override: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"root": str(project_root), "docs": [TCS_REL], "approver": "operator",
                            "reason": "E2E 核准"}
    body.update(override)
    return {k: v for k, v in body.items() if v is not None}


def _post(live, project: str, body: dict[str, Any], *, token: str | None = TOKEN,
          trace: str | None = None) -> httpx.Response:
    headers = {}
    if token is not None:
        headers["X-Bridge-Token"] = token
    if trace is not None:
        headers["X-Trace-Id"] = trace
    return live.client.post(f"/sdd/fsm/{project}:freeze", json=body, headers=headers)


def _state_bytes(root: Path, project: str = "alpha") -> bytes:
    return (root / _FSM / f"FSM-STATE-{project}.yaml").read_bytes()


def _audit(live) -> list[dict[str, Any]]:
    path = live.settings.engine_workspace / "_audit.jsonl"
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def _assert_untouched(fake: Path, root: Path, before: bytes, project: str = "alpha") -> None:
    assert _state_bytes(root, project) == before, "被拒的請求不得改動狀態檔"
    assert read_calls(fake) == [], "被拒的請求連 CLI 子行程都不該起"


# ── 成功路徑：摘要由 CLI 寫入、reason 固定組字、稽核對得上 ───────────────────────────────────
def test_freeze_records_the_stage_with_independently_computed_digests(
        live, fake: Path, root: Path) -> None:
    resp = _post(live, "alpha", _body(root), trace="freeze-trace-1")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_state"] == "SPEC_FROZEN"
    assert body["stage"] == "Stage-1", "省略 stage＝Stage-<n>，n＝已凍結階段數（不含重記條目）＋1"
    assert body["spec_doc_digests"] == {TCS_REL: _digest(TCS_TEXT)}
    assert body["fsm_project"] == "alpha"
    assert body["phase"] == {"name": "FROZEN", "order": 4, "blocking": False,
                             "observation": False}, "凍結後重讀的狀態＝SPEC_FROZEN→FROZEN／4"
    on_disk = read_state(root / _FSM, "alpha")
    stage = on_disk["frozen_stages"][-1]
    assert stage["stage"] == "Stage-1" and stage["spec_docs"] == [TCS_REL]
    assert stage["spec_doc_digests"] == {TCS_REL: _digest(TCS_TEXT)}, "摘要由 CLI 寫進凍結階段"
    assert stage["approved_by"] == "operator"
    trace = on_disk["decision_trace"][-1]
    assert (trace["trigger"], trace["to"]) == ("spec_frozen", "SPEC_FROZEN")
    assert trace["reason"] == "console-freeze approver=operator; reason=E2E 核准"
    assert body["frozen_stages"][-1]["stage"] == "Stage-1", "回應＝凍結後重讀的狀態（與 GET 同形）"
    assert body["decision_trace"][-1]["reason"] == trace["reason"]


def test_freeze_sends_exactly_one_whitelisted_verb_with_the_fixed_argv(
        live, fake: Path, root: Path) -> None:
    assert _post(live, "alpha", _body(root, stage="SCG-0.v2")).status_code == 200
    (call,) = read_calls(fake)
    assert call["verb"] == "spec-frozen"
    assert call["argv"] == [
        "spec-frozen", "--project", "alpha", "--must-exist", "--stage", "SCG-0.v2",
        "--doc", TCS_REL, "--digest", "--root", str(root.resolve()), "--reason",
        "console-freeze approver=operator; reason=E2E 核准", "--approver", "operator", "--json"]
    assert call["env"]["SDD_STATE_DIR"] == str((root / _FSM).resolve())
    assert not [k for k in call["env"] if k.upper().startswith("BRIDGE_")]
    assert TOKEN not in json.dumps(call), "權杖只存在 backend 與 Bridge，不進 CLI 子行程"


def test_freeze_is_audited_as_a_decision_with_the_request_trace_id_and_no_token(
        live, fake: Path, root: Path) -> None:
    resp = _post(live, "alpha", _body(root), trace="freeze-trace-77")
    assert resp.headers["X-Trace-Id"] == "freeze-trace-77"
    entries = _audit(live)
    request_level = [e for e in entries if e["event"] == "sdd_write"]
    cli_level = [e for e in entries if e["event"] == "sdd_cli"]
    (summary,) = request_level
    assert (summary["verb"], summary["project"], summary["approver"], summary["result"]) == (
        "freeze", "alpha", "operator", "ok")
    assert summary["trace_id"] == "freeze-trace-77"
    assert summary["stage"] == "Stage-1" and summary["docs"] == [TCS_REL]
    assert [e["trace_id"] for e in cli_level] == ["freeze-trace-77"], \
        "CLI 級與請求級以 trace_id 對得上"
    assert cli_level[0]["verb"] == "spec-frozen" and cli_level[0]["result"] == "ok"
    raw = (live.settings.engine_workspace / "_audit.jsonl").read_text(encoding="utf-8")
    assert TOKEN not in raw and TOKEN not in resp.text


def test_the_response_has_the_same_shape_as_get_plus_stage_and_digests(
        live, root: Path) -> None:
    posted = _post(live, "alpha", _body(root)).json()
    got = live.client.get("/sdd/fsm/alpha", params={"root": str(root)}).json()
    assert {k: v for k, v in posted.items() if k not in ("stage", "spec_doc_digests")} == got


def test_stage_defaults_to_the_next_number_and_an_explicit_valid_stage_is_kept(
        live, fake: Path, root: Path) -> None:
    seed_state(root / _FSM, "alpha", "HUMAN_PENDING",
               frozen_stages=[{"stage": "Stage-1"}, {"stage": "custom"}])
    assert _post(live, "alpha", _body(root)).json()["stage"] == "Stage-3"
    seed_state(root / _FSM, "alpha", "HUMAN_PENDING")
    assert _post(live, "alpha", _body(root, stage="A.b_c-1")).json()["stage"] == "A.b_c-1"


def test_a_refreeze_entry_does_not_advance_the_default_stage_number(
        live, fake: Path, root: Path) -> None:
    """SDD `spec-refreeze`（F-17）只在 `frozen_stages` 追加 `kind: refreeze` 的條目，不是新階段：
    Stage-1 ＋ 一次重記之後，下一次凍結的預設名是 Stage-2，不是跳號的 Stage-3。"""
    seed_state(root / _FSM, "alpha", "HUMAN_PENDING",
               frozen_stages=[{"stage": "Stage-1"}, {"stage": "Stage-1", "kind": "refreeze"}])
    assert _post(live, "alpha", _body(root)).json()["stage"] == "Stage-2"


@pytest.mark.parametrize("stage", ["", "has space", "a/b", "x" * 65, "名稱", "bad!"])
def test_an_invalid_stage_is_a_body_format_error(
        stage: str, live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root, stage=stage))
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert resp.json()["violations"][0]["field"] == "stage"
    _assert_untouched(fake, root, before)


# ── ① 本文格式 ② 權杖：停用／缺／錯，且先於一切會碰檔案系統的檢查 ─────────────────────────────
def test_a_bridge_without_a_token_refuses_the_freeze_with_503_and_touches_nothing(
        make_bridge, settings: Settings, fake: Path, root: Path) -> None:
    disabled = make_bridge(replace(settings, sdd_root=fake, sdd_write_token=None))
    before = _state_bytes(root)
    for header in (None, "", "anything", TOKEN):
        resp = _post(disabled, "alpha", _body(root), token=header)
        assert (resp.status_code, resp.json()["reason"]) == (503, "sdd_write_disabled"), header
    _assert_untouched(fake, root, before)
    # 唯讀不需權杖：GET 照常
    assert disabled.client.get("/sdd/fsm/alpha", params={"root": str(root)}).status_code == 200


@pytest.mark.parametrize("header", [None, "", "wrong", TOKEN[:-1], TOKEN + "x", TOKEN.upper()])
def test_a_missing_or_wrong_token_is_403_and_touches_nothing(
        header: str | None, live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root), token=header)
    assert (resp.status_code, resp.json()) == (403, {"code": 403, "reason": "sdd_write_forbidden"})
    assert TOKEN not in resp.text
    _assert_untouched(fake, root, before)
    rejections = [e for e in _audit(live) if e["event"] == "sdd_write"]
    assert rejections[-1]["result"] == "rejected:sdd_write_forbidden"
    assert TOKEN not in json.dumps(rejections)


def test_the_token_check_comes_before_every_filesystem_check(
        live, fake: Path, root: Path, tmp_path: Path) -> None:
    """壞 root、不存在的專案、不存在的文件：帶錯權杖一律 403，不洩漏「這個路徑／專案存不存在」。"""
    for project, body in (
            ("alpha", _body(tmp_path / "outside-allowed-roots")),
            ("nope", _body(root)),
            ("alpha", _body(root, docs=["docs/does-not-exist.md"])),
            ("alpha", _body(root, approver="bad;approver"))):
        resp = _post(live, project, body, token="wrong")
        assert resp.status_code == 403, (project, resp.text)
    assert read_calls(fake) == []


def test_a_malformed_body_is_422_even_without_a_token(live, root: Path) -> None:
    """契約順序：①本文格式先於②權杖（格式錯是呼叫端 bug，與權限無關）。"""
    for body in ({}, {"root": str(root)}, _body(root, docs=[]), _body(root, docs=["x"] * 21),
                 {**_body(root), "unknown_field": 1}):
        resp = _post(live, "alpha", body, token=None)
        assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request"), body


# ── ③ approver／reason 清理（§4.4）：不靜默截斷、不替換，違反即 422 sdd_invalid_argument ─────────
@pytest.mark.parametrize(("field", "value", "rule"), [
    ("approver", "a;b", "semicolon"), ("approver", "", "empty"), ("approver", "   ", "empty"),
    ("approver", " lead", "surrounding_whitespace"),
    ("approver", "trail ", "surrounding_whitespace"),
    ("approver", "x" * 101, "too_long"), ("approver", "a\nb", "control_chars"),
    ("approver", "a\x00b", "control_chars"),
    ("reason", "", "empty"), ("reason", "   \t ", "empty"), ("reason", "x" * 501, "too_long"),
    ("reason", "line1\nline2", "control_chars"), ("reason", "a\rb", "control_chars"),
])
def test_approver_and_reason_violations_are_422_sdd_invalid_argument(
        field: str, value: str, rule: str, live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root, **{field: value}))
    assert (resp.status_code, resp.json()["reason"]) == (422, "sdd_invalid_argument")
    assert (resp.json()["field"], resp.json()["rule"]) == (field, rule)
    _assert_untouched(fake, root, before)
    assert _audit(live)[-1]["result"] == "rejected:sdd_invalid_argument"


def test_the_limits_themselves_are_accepted_and_the_reason_is_stripped_not_truncated(
        live, fake: Path, root: Path) -> None:
    resp = _post(live, "alpha", _body(root, approver="a" * 100, reason="  " + "理" * 500 + "  "))
    assert resp.status_code == 200, resp.text
    reason = read_state(root / _FSM, "alpha")["decision_trace"][-1]["reason"]
    assert reason == f"console-freeze approver={'a' * 100}; reason={'理' * 500}"


# ── ④ root ⑤ 專案與狀態檔 ──────────────────────────────────────────────────────────────────
def test_root_must_pass_the_allowed_roots_gate(
        live, fake: Path, root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    resp = _post(live, "alpha", _body(outside))
    assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed")
    assert resp.json()["violations"][0]["field"] == "root"
    assert resp.json()["violations"][0]["rule"] == "outside_allowed_roots"
    rel = _post(live, "alpha", _body(root, root="projects/alpha"))
    assert rel.json()["violations"][0]["rule"] == "not_absolute"
    assert read_calls(fake) == []


def test_an_unknown_project_is_404_and_a_broken_state_file_is_422(
        live, fake: Path, root: Path) -> None:
    unknown = _post(live, "nope", _body(root))
    assert (unknown.status_code, unknown.json()["reason"], unknown.json()["project"]) == (
        404, "fsm_not_found", "nope")
    (root / _FSM / "FSM-STATE-broken.yaml").write_text("this: [is: not valid", encoding="utf-8")
    broken = _post(live, "broken", _body(root))
    assert (broken.status_code, broken.json()["reason"]) == (422, "fsm_state_unreadable")
    assert read_calls(fake) == []


def test_a_project_name_and_its_sanitized_key_freeze_the_same_state_file(
        live, fake: Path, root: Path) -> None:
    seed_state(root / _FSM, "a_b", "HUMAN_PENDING")                  # SDD 側 `a:b` 的檔名鍵
    resp = _post(live, "a:b", _body(root))
    assert resp.status_code == 200 and resp.json()["fsm_project"] == "a_b"
    (call,) = read_calls(fake)
    assert call["argv"][:3] == ["spec-frozen", "--project", "a_b"], "CLI 收到的是淨化後的鍵"
    assert read_state(root / _FSM, "a_b")["current_state"] == "SPEC_FROZEN"


# ── ⑥ docs[] 逐項檢查（規則碼：absolute／contains_dotdot／outside_root／not_found）＋含 TCS ─────
@pytest.mark.parametrize(("doc", "rule"), [
    ("/etc/passwd", "absolute"), ("C:/Windows/system.md", "absolute"),
    ("C:\\Windows\\system.md", "absolute"), ("\\\\server\\share\\x.md", "absolute"),
    ("../escape.md", "contains_dotdot"), ("docs/../../x.md", "contains_dotdot"),
    ("docs\\..\\..\\x.md", "contains_dotdot"),
    ("docs/missing.md", "not_found"), ("docs", "not_found"), ("docs/03_testing", "not_found"),
    ("   ", "invalid"),
])
def test_each_bad_doc_is_a_violation_with_its_index_and_rule(
        doc: str, rule: str, live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root, docs=[TCS_REL, doc]))
    assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed")
    violation = resp.json()["violations"][0]
    assert (violation["field"], violation["rule"]) == ("docs[1]", rule)
    _assert_untouched(fake, root, before)


def test_every_violation_is_reported_at_once_and_duplicates_are_refused(
        live, fake: Path, root: Path) -> None:
    resp = _post(live, "alpha", _body(root, docs=["/abs.md", TCS_REL, "gone.md", "./" + TCS_REL]))
    got = [(v["field"], v["rule"]) for v in resp.json()["violations"]]
    assert got == [("docs[0]", "absolute"), ("docs[2]", "not_found"), ("docs[3]", "duplicate")]


def test_a_symlink_that_escapes_root_is_outside_root(
        live, fake: Path, root: Path, tmp_path: Path) -> None:
    secret = tmp_path / "secret.md"
    secret.write_text("# secret\n", encoding="utf-8")
    try:
        (root / "docs" / "link.md").symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
    resp = _post(live, "alpha", _body(root, docs=[TCS_REL, "docs/link.md"]))
    violation = resp.json()["violations"][0]
    assert (violation["field"], violation["rule"]) == ("docs[1]", "outside_root")


def test_docs_must_include_an_officially_named_tcs(live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root, docs=["docs/readme.md"]))
    assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed")
    assert resp.json()["violations"][0]["rule"] == "missing_tcs"
    _assert_untouched(fake, root, before)
    sub = root / "docs" / "sub"
    sub.mkdir()
    (sub / "TEST-CONTRACT-SPEC-Other.md").write_text("# x\n", encoding="utf-8")
    (sub / "tcs-lower.md").write_text("# y\n", encoding="utf-8")
    for name in ("TEST-CONTRACT-SPEC-Other.md", "tcs-lower.md"):
        seed_state(root / _FSM, "alpha", "HUMAN_PENDING")
        assert _post(live, "alpha", _body(root, docs=["docs/readme.md", f"docs/sub/{name}"])
                     ).status_code == 200, name


# ── ⑦ 前置狀態 ───────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("state", ["INIT", "SPEC_DRAFTING", "SPEC_FROZEN", "IMPLEMENTATION",
                                   "AUTOCLAUDE_DELEGATED", "ESCALATION"])
def test_a_state_other_than_human_pending_is_409_and_nothing_changes(
        state: str, live, fake: Path, root: Path) -> None:
    seed_state(root / _FSM, "alpha", state)
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root))
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    body = resp.json()
    assert body["current_state"] == state and body["expected_state"] == "HUMAN_PENDING"
    assert body["detail"]["current_state"] == state, "ADR 形狀（detail 物件）與契約形狀（頂層）並存"
    _assert_untouched(fake, root, before)


def test_a_frozen_spec_cannot_be_frozen_twice(live, fake: Path, root: Path) -> None:
    assert _post(live, "alpha", _body(root)).status_code == 200
    again = _post(live, "alpha", _body(root))
    assert (again.status_code, again.json()["current_state"]) == (409, "SPEC_FROZEN")
    assert len(read_state(root / _FSM, "alpha")["frozen_stages"]) == 1
    assert len(read_calls(fake)) == 1, "第二次請求在前置檢查就被擋，沒有再起 CLI"


# ── ⑧ expected_digests：核准人看到的版本＝凍結的版本（TOCTOU）─────────────────────────────────
def test_expected_digests_that_match_pass_even_when_the_file_is_crlf(
        live, fake: Path, root: Path) -> None:
    (root / TCS_REL).write_bytes(TCS_TEXT.replace("\n", "\r\n").encode("utf-8"))
    resp = _post(live, "alpha", _body(root, expected_digests={TCS_REL: _digest(TCS_TEXT)}))
    assert resp.status_code == 200, "換行不同不得造成假性不符（F-6）"
    assert resp.json()["spec_doc_digests"] == {TCS_REL: _digest(TCS_TEXT)}


def test_a_file_changed_after_the_approver_looked_is_409_with_both_digests(
        live, fake: Path, root: Path) -> None:
    seen = _digest(TCS_TEXT)
    (root / TCS_REL).write_text(TCS_TEXT + "\nTHEN 「[CHANGED]」\n", encoding="utf-8")
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root, expected_digests={"./" + TCS_REL: seen}))
    assert (resp.status_code, resp.json()["reason"]) == (409, "spec_digest_changed")
    body = resp.json()
    assert body["pair"] == "expected_vs_file" and body["doc"] == TCS_REL
    assert body["expected_digest"] == seen and body["current_digest"] != seen
    assert body["detail"]["pair"] == "expected_vs_file"
    _assert_untouched(fake, root, before)


def test_expected_digest_keys_must_be_documents_of_this_freeze(
        live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root, expected_digests={"docs/readme.md": _digest("x"),
                                                              "../x.md": _digest("y")}))
    assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed")
    assert {v["rule"] for v in resp.json()["violations"]} == {"not_in_docs"}
    _assert_untouched(fake, root, before)


# ── ⑨ CLI 失敗的共同對映；狀態不變、重試安全 ──────────────────────────────────────────────────
@pytest.mark.parametrize(("control", "status", "reason"), [
    ({"rc": {"spec-frozen": 1}}, 502, "sdd_cli_failed"),
    ({"rc": {"spec-frozen": 4}}, 422, "sdd_invalid_argument"),
    ({"rc": {"spec-frozen": 5}}, 422, "fsm_state_unreadable"),
    ({"raw_stdout": {"spec-frozen": "not json"}}, 502, "sdd_cli_failed"),
])
def test_a_failing_cli_surfaces_as_the_documented_error_and_the_same_request_can_retry(
        control: dict, status: int, reason: str, live, fake: Path, root: Path) -> None:
    before = _state_bytes(root)
    set_control(fake, **control)
    resp = _post(live, "alpha", _body(root))
    assert (resp.status_code, resp.json()["reason"]) == (status, reason)
    assert _state_bytes(root) == before
    set_control(fake)
    assert _post(live, "alpha", _body(root)).status_code == 200, "狀態沒被動過，重試安全"


def test_a_hung_cli_is_504_and_the_state_is_untouched(
        live, fake: Path, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sdd_cli, "DEFAULT_TIMEOUT_SECONDS", 4.0)
    set_control(fake, sleep={"spec-frozen": 60})
    before = _state_bytes(root)
    resp = _post(live, "alpha", _body(root))
    assert (resp.status_code, resp.json()["reason"]) == (504, "sdd_cli_timeout")
    assert _state_bytes(root) == before
    assert _audit(live)[-1]["result"] == "rejected:sdd_cli_timeout"


# ── 序列化：同一專案的並行凍結只有一個成功 ─────────────────────────────────────────────────────
def test_two_concurrent_freezes_of_one_project_produce_exactly_one_freeze(
        live, fake: Path, root: Path) -> None:
    set_control(fake, sleep={"spec-frozen": 1.5})
    results: list[httpx.Response] = []

    def go() -> None:
        results.append(_post(live, "alpha", _body(root)))

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert sorted(r.status_code for r in results) == [200, 409]
    loser = next(r for r in results if r.status_code == 409)
    assert loser.json()["current_state"] == "SPEC_FROZEN"
    assert len(read_state(root / _FSM, "alpha")["frozen_stages"]) == 1
    assert [c["verb"] for c in read_calls(fake)] == ["spec-frozen"], \
        "輸家在鎖內讀到已凍結，沒有起 CLI"


def test_the_freeze_never_calls_any_other_verb(live, fake: Path, root: Path) -> None:
    assert _post(live, "alpha", _body(root)).status_code == 200
    assert {c["verb"] for c in read_calls(fake)} == {"spec-frozen"}


def test_the_sdd_tree_itself_is_never_written_by_a_freeze(live, fake: Path, root: Path) -> None:
    """版本目錄只有假 CLI 自己的紀錄檔會變（那是測試替身的副作用）；沒有 __pycache__、沒有遙測
    檔。"""
    before = {p.relative_to(fake).as_posix() for p in fake.rglob("*")}
    assert _post(live, "alpha", _body(root)).status_code == 200
    added = {p.relative_to(fake).as_posix() for p in fake.rglob("*")} - before
    assert added == {"fake_calls.jsonl"}, added
