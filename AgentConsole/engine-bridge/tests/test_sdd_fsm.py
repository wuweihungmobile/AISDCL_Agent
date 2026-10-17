"""D-16：`GET /sdd/fsm`（清單）與 `GET /sdd/fsm/{project}` 新增的三個欄位；v1.5：選填 `root`、
`phase`／`escalation_history`／`escalation_provenance`／`fsm_project`／`recovery`、專案名規則（S-10）。

結構以 AISDLC_SDD 真實的 FSM 狀態檔為準（`tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`、
`state_loader.py`）：`retry_history` 是 **dict of dict**（以重試閘為鍵，每個閘有 `history` list），
`human_pending_tracking` 是**單一 dict**（`entered_at`／`reminder_sent_at`／`reminder_hours`／
`escalation_hours`）——不是 list。合成夾具照這個形狀造；另有一支對真實檔、一支對「假如它改成 list」。
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from app import sdd_cli
from app.fsm_names import fsm_component
from app.settings import Settings

_FSM_REL = Path("build") / "reports" / "fsm"
_OLD_KEYS = {"project", "current_state", "current_sprint", "session_id", "updated_at",
             "frozen_stages", "decision_trace", "source"}
_D16_KEYS = {"human_pending", "retry_history", "rtm_coverage"}
#: v1.5（ADR-XPLAT-016 §5.3、§7.2、§7.4）：`phase` 永遠出現、是 current_state 的純函式投影
#: （app/fsm_phase.py；W4 dogfood 產物）；`recovery` 只在 ESCALATION／ESCALATION_FINAL 時出現、
#: 其餘情形鍵缺席（契約 §3.1.4 (c)），所以不在常態鍵集合裡。
_V15_KEYS = {"phase", "escalation_history", "escalation_provenance", "fsm_project"}
_NEW_KEYS = _D16_KEYS | _V15_KEYS
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
    """v1.5（S-10）：空白與 CJK 的專案名不再被拒（見下一支）；仍進 errors 的是「不在淨化輸出域」的
    名稱（以 `.` 結尾、前導空白、非 NFC、超過 80 字）與讀不動的檔。"""
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "good")
    _write(fsm_dir, "broken", "this: [is: not valid yaml")
    _write(fsm_dir, "noroot", "something_else: 1\n")
    _write(fsm_dir, "binary", b"\xff\xfe\x00\x01 not utf-8 \x80\x81")
    _write(fsm_dir, "dot.")                                   # 以 . 結尾：sanitizer 不會產生
    _write(fsm_dir, " lead")                                  # 前導空白：同上
    _write(fsm_dir, "e\N{COMBINING ACUTE ACCENT}cole")                            # NFD：不是 NFC
    _write(fsm_dir, "x" * 81)                                 # 超過 80 字
    (fsm_dir / "FSM-STATE-adir.yaml").mkdir()                 # 同名但是目錄
    (fsm_dir / "FSM-STATE-good.yaml.bak").write_text("ignored", encoding="utf-8")
    (fsm_dir / "FSM-STATE-other.yml").write_text("ignored", encoding="utf-8")
    (fsm_dir / "OTHER.yaml").write_text("ignored", encoding="utf-8")
    body = live_sdd.client.get("/sdd/fsm").json()
    assert [p["project"] for p in body["projects"]] == ["good"]
    assert sorted(body["errors"]) == sorted([
        "FSM-STATE-broken.yaml", "FSM-STATE-noroot.yaml", "FSM-STATE-binary.yaml",
        "FSM-STATE-dot..yaml", "FSM-STATE- lead.yaml",
        "FSM-STATE-e\N{COMBINING ACUTE ACCENT}cole.yaml",
        f"FSM-STATE-{'x' * 81}.yaml", "FSM-STATE-adir.yaml"])


S10_NAMES = ("訂單系統", "Order System", "proj(v2)", "a+b", "名稱含@符號")


def test_the_five_s10_names_are_listed_and_readable_by_their_original_names(
        live_sdd, sdd_tree: Path) -> None:
    """體檢 S-10：SDD 側能產生這五個專案名的狀態檔，舊白名單把它們全拒（清單進 errors、讀取 404）。
    新規則以 `sanitize_component` 的輸出域為準：全部列得出、點得進去（F-8 的 E2E 面）。"""
    fsm_dir = sdd_tree / _FSM_REL
    for name in S10_NAMES:
        _write(fsm_dir, fsm_component(name), state="IMPLEMENTATION")
    listing = live_sdd.client.get("/sdd/fsm").json()
    assert listing["errors"] == []
    assert sorted(p["project"] for p in listing["projects"]) == sorted(S10_NAMES)
    for name in S10_NAMES:
        resp = live_sdd.client.get(f"/sdd/fsm/{name}")
        assert resp.status_code == 200, (name, resp.text)
        body = resp.json()
        assert body["current_state"] == "IMPLEMENTATION"
        assert body["fsm_project"] == name and body["source"] == f"FSM-STATE-{name}.yaml"


def test_a_name_and_its_sanitized_key_reach_the_same_state_file(
        live_sdd, sdd_tree: Path) -> None:
    """進入 Bridge 的專案名一律先過 `fsm_component`（ADR §7.4）：傳原名與傳鍵等價；
    `fsm_project` 回的是狀態檔名裡淨化後的鍵（寫回綁定與唯一性檢查用它，不是檔內的 `project` 原
    名）。"""
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "a_b", state="SPEC_DRAFTING")
    by_original = live_sdd.client.get("/sdd/fsm/a:b")           # SDD 側 `a:b` → 檔名 `a_b`
    by_encoded = live_sdd.client.get("/sdd/fsm/a%3Ab")
    by_key = live_sdd.client.get("/sdd/fsm/a_b")
    for resp in (by_original, by_encoded, by_key):
        assert resp.status_code == 200, resp.text
        assert resp.json()["fsm_project"] == "a_b"
    assert by_original.json() == by_key.json()
    missing = live_sdd.client.get("/sdd/fsm/x:y")               # 404 回報的是使用者問的名稱
    assert (missing.status_code, missing.json()["reason"], missing.json()["project"]) == (
        404, "fsm_not_found", "x:y")


def test_a_name_with_a_slash_is_not_addressable_by_url_but_its_key_is(
        live_sdd, sdd_tree: Path) -> None:
    """D-115-18 ②：路徑參數只收淨化後的 FSM 鍵（`{project}` 不改成 `{project:path}`）。原名含 `/`
    的專案（`x/y` → 檔名 `x_y`）無法由 URL 定址——不論寫成兩段路徑或編碼的 `%2F`；清單與每個回應
    都帶 `fsm_project`（＝鍵），呼叫端改用它定址。請求本文裡的 `fsm_project`（compile、sdd 區塊）
    不受此限。"""
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "x_y", state="IMPLEMENTATION")
    for address in ("/sdd/fsm/x/y", "/sdd/fsm/x%2Fy", "/sdd/fsm/x%2fy"):
        resp = live_sdd.client.get(address)
        assert resp.status_code == 404, address
        assert "reason" not in resp.json(), "路由根本對不到：框架預設 404，不是 Bridge 的錯誤封包"
    assert fsm_component("x/y") == "x_y"
    listing = live_sdd.client.get("/sdd/fsm").json()
    assert [p["project"] for p in listing["projects"]] == ["x_y"], "清單給的名稱就是可定址的鍵"
    by_key = live_sdd.client.get(f"/sdd/fsm/{listing['projects'][0]['project']}")
    assert by_key.status_code == 200
    got = by_key.json()
    assert (got["fsm_project"], got["current_state"]) == ("x_y", "IMPLEMENTATION")


def test_traversal_shaped_names_never_leave_the_fsm_directory(
        live_sdd, sdd_tree: Path, tmp_path: Path) -> None:
    """`..` 與分隔符在淨化時被換掉或退成 `untitled`；就算同名檔存在，也只讀得到 fsm 目錄內的檔。"""
    (tmp_path / "FSM-STATE-outside.yaml").write_text(
        "fsm_state: {current_state: LEAKED}", encoding="utf-8")
    for name in ("..", "../x", "..%2F..%2Foutside", "a%2F..%2Fb", "%2E%2E", "a\\..\\b"):
        resp = live_sdd.client.get(f"/sdd/fsm/{name}")
        assert resp.status_code == 404, (name, resp.text)
        assert "LEAKED" not in resp.text


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


# ── GET /sdd/fsm/{project}：既有欄位不動、只增不減 ─────────────────────────────────────────
def test_the_detail_keeps_every_existing_field_and_adds_only_the_documented_ones(
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


# ── v1.5：選填 `root`（狀態目錄＝<root>/build/reports/fsm）────────────────────────────────
@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "projects" / "proj-a"
    (root / _FSM_REL).mkdir(parents=True)
    return root


def test_root_redirects_both_endpoints_to_the_project_state_directory(
        live_sdd, sdd_tree: Path, project_root: Path) -> None:
    _write(sdd_tree / _FSM_REL, "framework-own", state="INIT")
    _write(project_root / _FSM_REL, "alpha", state="HUMAN_PENDING")
    plain = live_sdd.client.get("/sdd/fsm").json()
    assert [p["project"] for p in plain["projects"]] == ["framework-own"], "省略 root＝v1.4 行為"
    scoped = live_sdd.client.get("/sdd/fsm", params={"root": str(project_root)}).json()
    assert [p["project"] for p in scoped["projects"]] == ["alpha"]
    assert scoped["root"] == plain["root"] == sdd_tree.name, \
        "清單的 root 欄位語意不變（SDD 版本目錄名）"
    detail = live_sdd.client.get("/sdd/fsm/alpha", params={"root": str(project_root)})
    assert detail.status_code == 200 and detail.json()["current_state"] == "HUMAN_PENDING"
    assert live_sdd.client.get("/sdd/fsm/alpha").status_code == 404, "沒帶 root 就看不到專案根的檔"
    assert live_sdd.client.get("/sdd/fsm/framework-own",
                               params={"root": str(project_root)}).status_code == 404


def test_root_is_checked_against_the_allowed_roots_like_every_other_path(
        live_sdd, tmp_path: Path) -> None:
    outside = tmp_path / "not-allowed"
    (outside / _FSM_REL).mkdir(parents=True)
    for url in ("/sdd/fsm", "/sdd/fsm/alpha"):
        resp = live_sdd.client.get(url, params={"root": str(outside)})
        assert resp.status_code == 422 and resp.json()["reason"] == "sanitization_failed"
        violation = resp.json()["violations"][0]
        assert (violation["field"], violation["rule"]) == ("root", "outside_allowed_roots")
        relative = live_sdd.client.get(url, params={"root": "projects/proj-a"})
        assert relative.json()["violations"][0]["rule"] == "not_absolute"
        dotdot = live_sdd.client.get(url, params={"root": str(tmp_path / "projects" / ".." / "x")})
        assert dotdot.json()["violations"][0]["rule"] == "contains_dotdot"
        blank = live_sdd.client.get(url, params={"root": ""})
        assert blank.json()["violations"][0]["rule"] == "empty"


def test_a_root_without_a_state_directory_is_an_empty_list_and_a_404_like_v14(
        live_sdd, tmp_path: Path) -> None:
    bare = tmp_path / "projects" / "bare"
    bare.mkdir(parents=True)
    listing = live_sdd.client.get("/sdd/fsm", params={"root": str(bare)})
    assert (listing.status_code, listing.json()["projects"], listing.json()["errors"]) == (
        200, [], [])
    assert live_sdd.client.get("/sdd/fsm/any", params={"root": str(bare)}).status_code == 404


def test_root_still_needs_a_usable_sdd_tree_503_before_anything_else(
        make_bridge, settings: Settings, project_root: Path, tmp_path: Path) -> None:
    live = make_bridge(replace(settings, sdd_root=None))
    for url in ("/sdd/fsm", "/sdd/fsm/alpha"):
        resp = live.client.get(url, params={"root": str(project_root)})
        assert (resp.status_code, resp.json()["reason"]) == (503, "sdd_unavailable")


# ── v1.5：新欄位（phase／escalation_history／escalation_provenance／fsm_project／recovery）──────
@pytest.mark.parametrize(("state", "phase"), [
    ("INIT", ("INTAKE", 1, False, False)),
    ("HUMAN_PENDING", ("HUMAN_GATE", 3, False, False)),
    ("SPEC_FROZEN", ("FROZEN", 4, False, False)),
    ("IMPLEMENTATION", ("IMPLEMENTATION", 5, False, False)),
    ("RELEASE", ("RELEASE", 8, False, False)),
    ("AUTOCLAUDE_DELEGATED", ("IMPLEMENTATION", 5, False, True)),    # 觀測態：回歸階段＋旗標
    ("HUB_SYNC", ("OBSERVATION", 0, False, True)),                   # 回歸點不可靜態判定
    ("AUTO_COMPACT_PENDING", ("TRANSIENT", 0, False, False)),
    ("ESCALATION", ("BLOCKED", 0, True, False)),
    ("NOT_A_STATE", ("UNKNOWN", 0, False, False)),
])
def test_phase_is_the_projection_of_current_state_never_null(
        state: str, phase: tuple[str, int, bool, bool], live_sdd, sdd_tree: Path) -> None:
    """契約 §3.1.5：`phase` 永遠是 `{name, order, blocking, observation}` 物件（W4 dogfood 的
    T-G 純函式 app/fsm_phase.py 接線後不再恆 null）；不認得的狀態是 UNKNOWN／0，不是 null。"""
    key = f"p-{state.lower()}"
    _write(sdd_tree / _FSM_REL, key, state=state)
    body = live_sdd.client.get(f"/sdd/fsm/{key}").json()
    name, order, blocking, observation = phase
    assert body["phase"] == {"name": name, "order": order, "blocking": blocking,
                             "observation": observation}, state


@pytest.mark.parametrize("bad", [None, ["INIT"], {"state": "INIT"}, 42, "", "   ", " INIT "])
def test_a_malformed_current_state_gives_an_unknown_phase_and_never_a_500(
        bad: Any, live_sdd, sdd_tree: Path) -> None:
    """壞檔的 current_state 不是字串（None、list、dict、數字）或是空白／前後帶空白：GET 仍是
    200，phase 是 UNKNOWN／0，沒有 recovery；清單也照常列出（list／dict 不可 hash，不能讓 500
    漏出去）。"""
    _write(sdd_tree / _FSM_REL, "weird", current_state=bad)
    resp = live_sdd.client.get("/sdd/fsm/weird")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_state"] == bad
    assert body["phase"] == {"name": "UNKNOWN", "order": 0, "blocking": False,
                             "observation": False}
    assert "recovery" not in body
    assert live_sdd.client.get("/sdd/fsm").status_code == 200


def test_the_list_items_do_not_carry_phase_or_the_v15_fields(live_sdd, sdd_tree: Path) -> None:
    _write(sdd_tree / _FSM_REL, "alpha")
    item = live_sdd.client.get("/sdd/fsm").json()["projects"][0]
    assert set(item) == _LIST_KEYS


def test_escalation_history_is_the_last_five_entries_oldest_first(
        live_sdd, sdd_tree: Path) -> None:
    history = [{"triggered_at": f"t{i}", "trigger_reason": f"r{i}", "resolved_at": None,
                "resolution": None} for i in range(8)]
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "many", state="ESCALATION", escalation_history=history)
    _write(fsm_dir, "few", escalation_history=history[:2])
    _write(fsm_dir, "missing", escalation_history=None)
    _write(fsm_dir, "weird", escalation_history="not a list")
    get = live_sdd.client.get
    assert [h["triggered_at"] for h in get("/sdd/fsm/many").json()["escalation_history"]] == [
        "t3", "t4", "t5", "t6", "t7"]
    assert get("/sdd/fsm/few").json()["escalation_history"] == history[:2]
    assert get("/sdd/fsm/missing").json()["escalation_history"] == []
    assert get("/sdd/fsm/weird").json()["escalation_history"] == []


def test_escalation_provenance_is_passed_through_so_a_delegation_failure_can_be_recognised(
        live_sdd, sdd_tree: Path) -> None:
    provenance = {"session_id": "unknown", "at": "2026-10-17T01:00:00+00:00", "reason": "r",
                  "rule_id": "unknown", "source": "autoclaude_delegated_failed"}
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "failed", state="ESCALATION", escalation_provenance=provenance)
    _write(fsm_dir, "clean")
    _write(fsm_dir, "odd", escalation_provenance="nope")
    get = live_sdd.client.get
    assert get("/sdd/fsm/failed").json()["escalation_provenance"] == provenance
    assert get("/sdd/fsm/clean").json()["escalation_provenance"] is None
    assert get("/sdd/fsm/odd").json()["escalation_provenance"] is None


def test_recovery_commands_appear_only_in_escalation_states(
        live_sdd, sdd_tree: Path, project_root: Path) -> None:
    fsm_dir = project_root / _FSM_REL
    for state in ("ESCALATION", "ESCALATION_FINAL"):
        _write(fsm_dir, state.lower(), state=state)
    _write(fsm_dir, "fine", state="IMPLEMENTATION")

    def get(name: str) -> dict[str, Any]:
        resp = live_sdd.client.get(f"/sdd/fsm/{name}", params={"root": str(project_root)})
        return resp.json()

    assert "recovery" not in get("fine"), "非 ESCALATION 類：鍵缺席（契約 §3.1.4 (c)），不是 null"
    for name in ("escalation", "escalation_final"):
        recovery = get(name)["recovery"]
        assert set(recovery) == {"target", "powershell", "posix"}


def test_the_recovery_command_follows_the_adr_template_for_both_shells(
        live_sdd, sdd_tree: Path, project_root: Path) -> None:
    """ADR §5.3：PowerShell 用 `Push-Location … -ErrorAction Stop; …; Pop-Location` 同一句內成對、
    不裸 cd；POSIX 的 `VAR=值 指令` 前綴只作用於該指令。委派失敗的目標是 IMPLEMENTATION（與
    tracking.resume_state 一致）。"""
    failed = {"source": "autoclaude_delegated_failed", "reason": "r", "rule_id": "unknown",
              "session_id": "unknown", "at": "t"}
    tracking = {"entered_at": "t", "resume_state": "IMPLEMENTATION", "playbook_ref": "run:R1"}
    _write(project_root / _FSM_REL, "alpha", state="ESCALATION", escalation_provenance=failed,
           autoclaude_delegated_tracking=tracking)
    recovery = live_sdd.client.get("/sdd/fsm/alpha", params={"root": str(project_root)}).json()[
        "recovery"]
    assert recovery["target"] == "IMPLEMENTATION"
    fsm_dir = (project_root / _FSM_REL).resolve()
    powershell, posix = recovery["powershell"], recovery["posix"]
    assert powershell.startswith(f"Push-Location '{sdd_tree}' -ErrorAction Stop; ")
    assert f"$env:SDD_STATE_DIR = '{fsm_dir}'; " in powershell
    assert ("-m tools.fsm_runtime.fsm_runtime resume-from-escalation --project 'alpha' "
            '--to IMPLEMENTATION --reason "<人工原因>"; ') in powershell
    assert powershell.endswith("Remove-Item Env:SDD_STATE_DIR; Pop-Location")
    assert not powershell.lstrip().lower().startswith(("cd ", "set-location"))
    assert posix.startswith("cd ") and " && SDD_STATE_DIR=" in posix
    assert posix.endswith('resume-from-escalation --project alpha --to IMPLEMENTATION '
                          '--reason "<人工原因>"')
    assert str(fsm_dir) in posix and "Pop-Location" not in posix


def test_the_recovery_target_falls_back_like_the_sdd_recovery_hint(
        live_sdd, sdd_tree: Path, project_root: Path) -> None:
    fsm_dir = project_root / _FSM_REL
    _write(fsm_dir, "plain", state="ESCALATION")                              # 無任何線索
    _write(fsm_dir, "compact", state="ESCALATION_FINAL",
           auto_compact_state={"resume_state": "PR_REVIEW"})
    _write(fsm_dir, "badresume", state="ESCALATION",
           auto_compact_state={"resume_state": "HUMAN_PENDING"})              # 不在 RESUME_TARGETS
    _write(fsm_dir, "delegfail", state="ESCALATION",
           escalation_provenance={"source": "autoclaude_delegated_failed"},
           autoclaude_delegated_tracking={"resume_state": "not-a-target"})
    targets = {name: live_sdd.client.get(f"/sdd/fsm/{name}", params={"root": str(project_root)})
               .json()["recovery"]["target"]
               for name in ("plain", "compact", "badresume", "delegfail")}
    assert targets == {"plain": "SPEC_DRAFTING", "compact": "PR_REVIEW",
                       "badresume": "SPEC_DRAFTING", "delegfail": "IMPLEMENTATION"}


def test_the_recovery_command_quotes_hostile_names_so_the_shell_cannot_expand_them(
        live_sdd, sdd_tree: Path, project_root: Path) -> None:
    name = "o'brien $(whoami) `x` & y"
    _write(project_root / _FSM_REL, fsm_component(name), state="ESCALATION")
    body = live_sdd.client.get(f"/sdd/fsm/{name}", params={"root": str(project_root)}).json()
    key = body["fsm_project"]
    assert "'" in key and "$(whoami)" in key
    powershell, posix = body["recovery"]["powershell"], body["recovery"]["posix"]
    assert "--project '" + key.replace("'", "''") + "'" in powershell
    assert "--project 'o'\"'\"'brien" in posix, "POSIX 以 shlex 的單引號形引用，$()、反引號不被展開"


# ── 互斥鎖：讀取與 CLI 寫入同一把（ADR §3.5）──────────────────────────────────────────────
def test_a_get_waits_while_the_same_project_is_being_written(
        live_sdd, sdd_tree: Path) -> None:
    fsm_dir = sdd_tree / _FSM_REL
    _write(fsm_dir, "busy", state="IMPLEMENTATION")
    other = _write(fsm_dir, "other", state="INIT")
    assert other.is_file()
    finished: dict[str, float] = {}

    def fetch(name: str) -> None:
        resp = live_sdd.client.get(f"/sdd/fsm/{name}")
        assert resp.status_code == 200
        finished[name] = time.monotonic()

    began = time.monotonic()
    with sdd_cli.state_guard(fsm_dir, "busy"):                 # 扮演「CLI 正在改這個專案」
        blocked = threading.Thread(target=fetch, args=("busy",))
        free = threading.Thread(target=fetch, args=("other",))
        blocked.start()
        free.start()
        free.join(10)
        time.sleep(0.5)
        assert "other" in finished, "別的專案不受影響"
        assert "busy" not in finished, "同一個 (狀態目錄, 專案鍵) 的讀取要等寫入結束"
    blocked.join(10)
    assert "busy" in finished and finished["busy"] >= began + 0.5


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
        escalated = state["current_state"] in ("ESCALATION", "ESCALATION_FINAL")
        assert set(body) == _OLD_KEYS | _NEW_KEYS | ({"recovery"} if escalated else set())
        tracking = state.get("human_pending_tracking")
        assert body["human_pending"]["count"] == _expected_human_pending_count(tracking)
        assert len(body["human_pending"]["items"]) <= 5
        assert body["retry_history"]["count"] == _expected_retry_count(state.get("retry_history"))
        assert (body["retry_history"]["last"] is None) == (body["retry_history"]["count"] == 0)
        assert body["rtm_coverage"] == state.get("rtm_coverage")      # 真實檔沒有這個鍵 → None
