"""D-16：`GET /sdd/fsm`（清單）與 `GET /sdd/fsm/{project}` 新增的三個欄位。

結構以 AISDLC_SDD 真實的 FSM 狀態檔為準（`tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`、
`state_loader.py`）：`retry_history` 是 **dict of dict**（以重試閘為鍵，每個閘有 `history` list），
`human_pending_tracking` 是**單一 dict**（`entered_at`／`reminder_sent_at`／`reminder_hours`／
`escalation_hours`）——不是 list。合成夾具照這個形狀造；另有一支對真實檔、一支對「假如它改成 list」。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.settings import Settings

_FSM_REL = Path("build") / "reports" / "fsm"
_OLD_KEYS = {"project", "current_state", "current_sprint", "session_id", "updated_at",
             "frozen_stages", "decision_trace", "source"}
_NEW_KEYS = {"human_pending", "retry_history", "rtm_coverage"}
_LIST_KEYS = {"project", "source", "current_state", "updated_at"}


def _state_doc(project: str, *, state: str = "INIT", **fsm: Any) -> dict[str, Any]:
    """照真實檔的形狀（TEMPLATE）造一份 `fsm_state`；`fsm` 覆寫或新增頂層鍵。"""
    body: dict[str, Any] = {
        "project": project, "session_id": "sid-1", "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-16T00:00:00+00:00", "current_state": state, "current_sprint": 2,
        "retry_history": {
            "SCG_VALIDATION": {"current_count": 0, "max_limit": 3, "history": []},
            "PR_REVIEW": {"current_count": 0, "max_limit": 5, "spec_audit_count": 0,
                          "history": [], "patterns": []},
            "RTM_VERIFY": {"current_count": 0, "max_limit": 2, "history": []},
        },
        "human_pending_tracking": {"entered_at": None, "reminder_sent_at": None,
                                   "reminder_hours": 72, "escalation_hours": 168},
        "decision_trace": [], "frozen_stages": [], "escalation_history": [],
    }
    body.update(fsm)
    return {"fsm_state": body}


def _write(fsm_dir: Path, project: str, doc: dict[str, Any] | str | bytes | None = None,
           **fsm: Any) -> Path:
    fsm_dir.mkdir(parents=True, exist_ok=True)
    path = fsm_dir / f"FSM-STATE-{project}.yaml"
    content = _state_doc(project, **fsm) if doc is None else doc
    if isinstance(content, bytes):
        path.write_bytes(content)
    elif isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    return path


@pytest.fixture
def sdd_tree(tmp_path: Path) -> Path:
    root = tmp_path / "AISDLC_SDD_v9.99"
    (root / _FSM_REL).mkdir(parents=True)
    return root


@pytest.fixture
def live_sdd(make_bridge: Callable[..., Any], settings: Settings, sdd_tree: Path) -> Any:
    return make_bridge(replace(settings, sdd_root=sdd_tree))


# ── GET /sdd/fsm ─────────────────────────────────────────────────────────────────────
def test_the_list_names_every_state_file_with_its_state_and_timestamp(
        live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "beta", state="INIT", updated_at="2026-10-01T01:00:00+00:00")
    _write(fsm_dir, "alpha", state="IMPLEMENTATION", updated_at="2026-10-02T02:00:00+00:00")
    _write(fsm_dir, "gamma.v2_x-1", state="RELEASE_READY")
    _write(fsm_dir, "Zulu", state="SPEC_DRAFTING")
    resp = live_sdd.client.get("/sdd/fsm")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"root", "projects", "errors"}
    assert body["root"] == "AISDLC_SDD_v9.99" and body["errors"] == []
    assert all(set(item) == _LIST_KEYS for item in body["projects"])
    listed = [(p["project"], p["source"], p["current_state"]) for p in body["projects"]]
    assert listed == [      # 依名稱排序（不分大小寫：Zulu 排在最後，不是最前）
        ("alpha", "FSM-STATE-alpha.yaml", "IMPLEMENTATION"),
        ("beta", "FSM-STATE-beta.yaml", "INIT"),
        ("gamma.v2_x-1", "FSM-STATE-gamma.v2_x-1.yaml", "RELEASE_READY"),
        ("Zulu", "FSM-STATE-Zulu.yaml", "SPEC_DRAFTING")]
    assert body["projects"][0]["updated_at"] == "2026-10-02T02:00:00+00:00"
    # 清單裡的 project 就是 /sdd/fsm/{project} 吃的鍵：每一筆都點得進去
    for item in body["projects"]:
        detail = live_sdd.client.get(f"/sdd/fsm/{item['project']}")
        assert detail.status_code == 200 and detail.json()["source"] == item["source"]


def test_unreadable_and_badly_named_files_go_to_errors_and_the_rest_still_list(
        live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "good")
    _write(fsm_dir, "broken", "this: [is: not valid yaml")
    _write(fsm_dir, "noroot", "something_else: 1\n")
    _write(fsm_dir, "binary", b"\xff\xfe\x00\x01 not utf-8 \x80\x81")
    _write(fsm_dir, "bad name")                               # 空白不在白名單
    _write(fsm_dir, "中文專案")                                # 非 ASCII 不在白名單
    (fsm_dir / "FSM-STATE-adir.yaml").mkdir()                 # 同名但是目錄
    (fsm_dir / "FSM-STATE-good.yaml.bak").write_text("ignored", encoding="utf-8")
    (fsm_dir / "FSM-STATE-other.yml").write_text("ignored", encoding="utf-8")
    (fsm_dir / "OTHER.yaml").write_text("ignored", encoding="utf-8")
    body = live_sdd.client.get("/sdd/fsm").json()
    assert [p["project"] for p in body["projects"]] == ["good"]
    assert sorted(body["errors"]) == sorted([
        "FSM-STATE-broken.yaml", "FSM-STATE-noroot.yaml", "FSM-STATE-binary.yaml",
        "FSM-STATE-bad name.yaml", "FSM-STATE-中文專案.yaml", "FSM-STATE-adir.yaml"])


def test_a_pathologically_nested_state_file_is_an_error_not_a_crash(
        live_sdd, sdd_tree: Path) -> None:
    """PyYAML 的組合階段是遞迴的：巢狀夠深時丟的是 RecursionError，不是 YAMLError。清單把它放進
    `errors`、detail 回 422，兩者都不能變成 500。"""
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "good")
    _write(fsm_dir, "nested", "fsm_state: " + "[" * 6000 + "]" * 6000)
    body = live_sdd.client.get("/sdd/fsm").json()
    assert [p["project"] for p in body["projects"]] == ["good"]
    assert body["errors"] == ["FSM-STATE-nested.yaml"]
    detail = live_sdd.client.get("/sdd/fsm/nested")
    assert detail.status_code == 422 and detail.json()["reason"] == "fsm_state_unreadable"
    assert live_sdd.client.get("/sdd/fsm/good").status_code == 200


def test_the_project_name_whitelist_is_one_to_128_safe_characters() -> None:
    """名稱長度的邊界：Windows 的路徑長度上限讓 129 字元的檔名建不出來，所以直接驗規則。"""
    from app.routers.sdd import _PROJECT_RE

    assert _PROJECT_RE.match("a" * 128) and not _PROJECT_RE.match("a" * 129)
    assert _PROJECT_RE.match("A.b_c-1") and not _PROJECT_RE.match("")
    for bad in ("a b", "a/b", "a\\b", "..\\x", "a%2Fb", "中文", "a\nb"):
        assert not _PROJECT_RE.match(bad), bad


def test_a_symlinked_state_file_that_points_outside_is_an_error_not_a_listing(
        live_sdd, sdd_tree: Path, tmp_path: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "good")
    secret = tmp_path / "elsewhere"
    secret.mkdir()
    (secret / "real.yaml").write_text("fsm_state: {current_state: LEAKED}", encoding="utf-8")
    try:
        (fsm_dir / "FSM-STATE-evil.yaml").symlink_to(secret / "real.yaml")
    except (OSError, NotImplementedError):
        pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
    body = live_sdd.client.get("/sdd/fsm").json()
    assert [p["project"] for p in body["projects"]] == ["good"]
    assert body["errors"] == ["FSM-STATE-evil.yaml"]
    assert "LEAKED" not in live_sdd.client.get("/sdd/fsm").text


def test_a_valid_sdd_tree_without_the_fsm_directory_lists_nothing_and_is_not_an_error(
        make_bridge, settings: Settings, tmp_path: Path) -> None:
    """build/reports/ 被 git 忽略（AISDLC_SDD/.gitignore）：全新 clone 沒有 fsm 目錄 → 空清單，
    不是 503。"""
    root = tmp_path / "AISDLC_SDD_v9.98"
    root.mkdir()
    live = make_bridge(replace(settings, sdd_root=root))
    resp = live.client.get("/sdd/fsm")
    assert resp.status_code == 200
    assert resp.json() == {"root": "AISDLC_SDD_v9.98", "projects": [], "errors": []}
    assert live.client.get("/sdd/fsm/anything").status_code == 404


def test_without_a_usable_sdd_tree_the_list_is_503_like_the_other_sdd_endpoints(
        make_bridge, settings: Settings, tmp_path: Path) -> None:
    for sdd_root in (None, tmp_path / "does-not-exist"):
        live = make_bridge(replace(settings, sdd_root=sdd_root))
        resp = live.client.get("/sdd/fsm")
        assert (resp.status_code, resp.json()["reason"]) == (503, "sdd_unavailable"), sdd_root


def test_the_sdd_endpoints_never_write_into_the_sdd_tree_including_the_list(
        live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "demo")
    _write(fsm_dir, "broken", "this: [is: not valid yaml")

    def snapshot() -> dict[str, int]:
        return {str(p.relative_to(sdd_tree)): p.stat().st_mtime_ns for p in sdd_tree.rglob("*")}

    before = snapshot()
    for url in ("/sdd/fsm", "/sdd/fsm/demo", "/sdd/fsm/broken", "/sdd/fsm/nope", "/sdd/version"):
        live_sdd.client.get(url)
    assert snapshot() == before, "唯讀：不得新增、改動任何檔案或目錄"


# ── GET /sdd/fsm/{project}：既有欄位不動、新增三個 ─────────────────────────────────────────
def test_the_detail_keeps_every_existing_field_and_adds_exactly_three(
        live_sdd, sdd_tree: Path) -> None:
    trace = [{"ts": f"t{i}", "from": f"S{i}", "to": f"S{i + 1}"} for i in range(8)]
    _write(sdd_tree / _FSM_REL, "demo", state="IMPLEMENTATION", decision_trace=trace,
           frozen_stages=[{"stage": "SCG-0"}])
    body = live_sdd.client.get("/sdd/fsm/demo").json()
    assert set(body) == _OLD_KEYS | _NEW_KEYS
    assert (body["project"], body["current_state"], body["current_sprint"]) == (
        "demo", "IMPLEMENTATION", 2)
    assert (body["session_id"], body["source"]) == ("sid-1", "FSM-STATE-demo.yaml")
    assert [d["ts"] for d in body["decision_trace"]] == ["t3", "t4", "t5", "t6", "t7"]
    assert body["frozen_stages"] == [{"stage": "SCG-0"}]


def test_human_pending_follows_the_real_dict_structure(live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "idle")                                    # entered_at 為 null＝沒有在等人
    waiting = {"entered_at": "2026-10-15T08:00:00+00:00", "reminder_sent_at": None,
               "reminder_hours": 72, "escalation_hours": 168}
    _write(fsm_dir, "waiting", state="HUMAN_PENDING", human_pending_tracking=waiting)
    _write(fsm_dir, "missing", human_pending_tracking=None)
    _write(fsm_dir, "weird", human_pending_tracking="not a record")
    get = live_sdd.client.get
    assert get("/sdd/fsm/idle").json()["human_pending"] == {"count": 0, "items": []}
    assert get("/sdd/fsm/waiting").json()["human_pending"] == {"count": 1, "items": [waiting]}
    assert get("/sdd/fsm/missing").json()["human_pending"] == {"count": 0, "items": []}
    assert get("/sdd/fsm/weird").json()["human_pending"] == {"count": 0, "items": []}


def test_human_pending_also_understands_a_list_and_keeps_the_last_five_as_is(
        live_sdd, sdd_tree: Path) -> None:
    items = [{"entered_at": f"2026-10-{day:02d}T00:00:00+00:00", "n": day} for day in range(1, 9)]
    _write(sdd_tree / _FSM_REL, "listy", human_pending_tracking=items)
    got = live_sdd.client.get("/sdd/fsm/listy").json()["human_pending"]
    assert got == {"count": 8, "items": items[-5:]}


def test_retry_history_counts_every_gate_and_returns_the_latest_entry_with_its_gate(
        live_sdd, sdd_tree: Path) -> None:
    def record(attempt: int, date: str, reason: str, scg: str | None = None) -> dict[str, Any]:
        return {"attempt": attempt, "date": date, "failure_reason": reason, "scg_gate": scg}

    history = {
        "SCG_VALIDATION": {"current_count": 2, "max_limit": 3, "history": [
            record(1, "2026-10-10T01:00:00+00:00", "FRD 缺 NFR", "SCG-0"),
            record(2, "2026-10-12T01:00:00+00:00", "AC 無法測", "SCG-0")]},
        "PR_REVIEW": {"current_count": 1, "max_limit": 5, "patterns": [{"attempt": 1}], "history": [
            record(1, "2026-10-11T01:00:00+00:00", "p95 超標")]},
        "RTM_VERIFY": {"current_count": 1, "max_limit": 2, "history": [
            record(1, "2026-10-13T09:30:00+00:00", "RTM 缺 TC")]},
    }
    _write(sdd_tree / _FSM_REL, "demo", retry_history=history)
    got = live_sdd.client.get("/sdd/fsm/demo").json()["retry_history"]
    assert got["count"] == 4, "三個閘 history 筆數的總和（patterns 不算）"
    newest = record(1, "2026-10-13T09:30:00+00:00", "RTM 缺 TC")
    assert got["last"] == {"gate": "RTM_VERIFY", **newest}, "date 最晚的那筆原樣，另加所屬的閘"


def test_retry_history_picks_the_latest_date_not_the_last_gate_in_file_order(
        live_sdd, sdd_tree: Path) -> None:
    history = {
        "SCG_VALIDATION": {"history": [{"attempt": 3, "date": "2026-10-20T00:00:00+00:00"}]},
        "RTM_VERIFY": {"history": [{"attempt": 1, "date": "2026-10-01T00:00:00+00:00"}]},
    }
    _write(sdd_tree / _FSM_REL, "demo", retry_history=history)
    last = live_sdd.client.get("/sdd/fsm/demo").json()["retry_history"]["last"]
    assert (last["gate"], last["attempt"]) == ("SCG_VALIDATION", 3)


def test_retry_history_without_any_entries_or_in_odd_shapes_is_count_zero(
        live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "fresh")                                   # 三個閘的 history 都是空 list
    _write(fsm_dir, "gone", retry_history=None)
    _write(fsm_dir, "odd", retry_history={"SCG_VALIDATION": "nope", "PR_REVIEW": {"history": "x"}})
    for name in ("fresh", "gone", "odd"):
        got = live_sdd.client.get(f"/sdd/fsm/{name}").json()["retry_history"]
        assert got == {"count": 0, "last": None}, name


def test_retry_history_also_understands_a_plain_list(live_sdd, sdd_tree: Path) -> None:
    rows = [{"attempt": n} for n in range(1, 4)]
    _write(sdd_tree / _FSM_REL, "listy", retry_history=rows)
    assert live_sdd.client.get("/sdd/fsm/listy").json()["retry_history"] == {
        "count": 3, "last": {"attempt": 3}}


def test_rtm_coverage_is_null_unless_the_file_carries_it(live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "plain")
    _write(fsm_dir, "scalar", rtm_coverage=87.5)
    _write(fsm_dir, "structured", rtm_coverage={"covered": 41, "total": 43})
    get = live_sdd.client.get
    assert get("/sdd/fsm/plain").json()["rtm_coverage"] is None
    assert get("/sdd/fsm/scalar").json()["rtm_coverage"] == 87.5
    assert get("/sdd/fsm/structured").json()["rtm_coverage"] == {"covered": 41, "total": 43}


# ── 對真實檔（AISDLC_SDD 不存在或沒有狀態檔時 skip）──────────────────────────────────────
def _real_state_files(sdd_root: Path | None) -> list[Path]:
    if sdd_root is None:
        return []
    return sorted((sdd_root / _FSM_REL).glob("FSM-STATE-*.yaml"))


def _expected_human_pending_count(tracking: Any) -> int:
    if isinstance(tracking, list):
        return len(tracking)
    return 1 if isinstance(tracking, dict) and tracking.get("entered_at") else 0


def _expected_retry_count(history: Any) -> int:
    if isinstance(history, list):
        return len(history)
    if not isinstance(history, dict):
        return 0
    return sum(len(v["history"]) for v in history.values()
               if isinstance(v, dict) and isinstance(v.get("history"), list))


def test_against_the_real_state_files_of_the_latest_sdd_version(bridge) -> None:
    """用真實檔對照：不重寫一份解析邏輯，而是從原始 YAML 另外算出期望值再比。
    `build/reports/` 被 git 忽略（AISDLC_SDD/.gitignore）：全新 clone 沒有這些檔，沒有就 skip。"""
    files = _real_state_files(bridge.settings.sdd_root)
    if not files:
        pytest.skip("AISDLC_SDD 的 build/reports/fsm 下沒有 FSM-STATE-*.yaml（目錄被 git 忽略，"
                    "全新 clone 沒有；跑過 SDD runtime 才會產生）")
    listing = bridge.client.get("/sdd/fsm").json()
    assert listing["root"] == bridge.settings.sdd_root.name
    assert len(listing["projects"]) + len(listing["errors"]) == len(files), "每個檔都有去處"
    raw_by_source: dict[str, Any] = {}
    for path in files:
        try:
            raw_by_source[path.name] = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, yaml.YAMLError):
            pass                                             # 壞檔應該在 errors 裡，不在 projects
    for item in listing["projects"]:
        state = raw_by_source[item["source"]]["fsm_state"]
        assert item["current_state"] == state["current_state"]
        assert item["updated_at"] == state["updated_at"]
        detail = bridge.client.get(f"/sdd/fsm/{item['project']}")
        assert detail.status_code == 200, (item, detail.text)
        body = detail.json()
        assert set(body) == _OLD_KEYS | _NEW_KEYS
        tracking = state.get("human_pending_tracking")
        assert body["human_pending"]["count"] == _expected_human_pending_count(tracking)
        assert len(body["human_pending"]["items"]) <= 5
        assert body["retry_history"]["count"] == _expected_retry_count(state.get("retry_history"))
        assert (body["retry_history"]["last"] is None) == (body["retry_history"]["count"] == 0)
        assert body["rtm_coverage"] == state.get("rtm_coverage")      # 真實檔沒有這個鍵 → None
