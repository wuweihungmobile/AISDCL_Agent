"""Bridge 六端點對拍真 CLI 的差分測試（TCS-SelfImprovingMirror-P1b：AT-932-1-1、AT-932-1-2、
AT-932-1-E-1、AT-932-1-E-2、AT-932-2-2、AT-932-3-3、AT-940-7-1、AT-940-7-E-1）。

「真 CLI」＝把根層 `export` 的 import 閉包複製進 tmp 倉、提交一次的狀態 A（追加一列一事件再提交＝
狀態 B）；基準＝同一時刻直接以 `sys.executable` 跑 `export --json --kind <k>`。差分只證明回應＝
`export` 輸出，不證明 `export` 的折疊邏輯正確（那是根層 TCS 的事）。全程 hermetic：tmp 倉、tmp
家目錄、loopback 上的 uvicorn；真帳本、真事件帳本一律不碰。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.settings import Settings
from tests import si_repo_support as sup

SIX = [("status", "/si/status", ()), ("observations", "/si/observations", ()),
       ("events", "/si/events", ()), ("proposals", "/si/proposals", ()),
       ("proposals", "/si/proposals/PROP-SI-004", ("--id", "PROP-SI-004")),
       ("runs", "/si/runs", ())]
BACKEND_COPY = sup.MONOREPO / "AgentConsole" / "backend" / "src" / "test" / "resources" / "si"
FRONTEND_COPY = sup.MONOREPO / "AgentConsole" / "frontend" / "tests" / "fixtures" / "si"
REGEN_HINT = "重產指令：在 AgentConsole/engine-bridge 下執行 `python tests/si_golden_regen.py`"


def sans_generated_at(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in obj.items() if k != "generated_at"}


def start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings, make_bridge: Any,
          state: str = "A") -> tuple[Path, Any, Path]:
    home = sup.isolate_home(monkeypatch, tmp_path)
    root = sup.make_si_repo(tmp_path, state)
    return root, make_bridge(replace(settings, si_root=root)), home


# ── AT-932-1-1：狀態 A 的六個回應逐值等於真 CLI ─────────────────────────────────────────────
def test_AT_932_1_1_state_a_responses_equal_the_real_cli_output(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    bodies: dict[str, dict[str, Any]] = {}
    for kind, path, flags in SIX:
        resp = live.client.get(path)
        assert resp.status_code == 200, f"{path}：{resp.status_code} {resp.text[:300]}"
        baseline = sup.cli_export(root, kind, *flags)
        assert sans_generated_at(resp.json()) == sans_generated_at(baseline), \
            f"{path}：回應與真 CLI 的輸出不逐值相等"
        assert list(resp.json()) == list(baseline), f"{path}：鍵序必須保留"
        assert "\\u" not in resp.text, f"{path}：非 ASCII 必須以原字元出現、不跳脫"
        bodies[path] = resp.json()
    counts = {path: len(body["items"]) for path, body in bodies.items()}
    assert counts == {"/si/status": 1, "/si/observations": 12, "/si/events": 6,
                      "/si/proposals": 1, "/si/proposals/PROP-SI-004": 1, "/si/runs": 1}
    items = bodies["/si/observations"]["items"]
    assert sum(1 for i in items if i.get("valid") is False) == 1
    assert bodies["/si/observations"]["problems"], "壞列必須在 problems 內"
    card_cli = sup.cli_card(root, "PROP-SI-004")
    listed, single = (bodies["/si/proposals"]["items"][0], bodies["/si/proposals/PROP-SI-004"][
        "items"][0])
    assert listed["id"] == single["id"] == "PROP-SI-004"
    assert card_cli and listed["card"] == card_cli == single["card"], \
        "卡面必須逐位元組等於 `si card` 的 stdout（含全形字元、box 字元、空行與結尾換行）"


# ── AT-932-1-2：since／limit／next_since／truncated 對映真 CLI 的游標分頁 ───────────────────────
def pages(live: Any, kind: str, limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    url = f"/si/{kind}?limit={limit}"
    while True:
        resp = live.client.get(url)
        assert resp.status_code == 200, resp.text[:300]
        out.append(resp.json())
        if not out[-1]["truncated"]:
            return out
        url = f"/si/{kind}?since={out[-1]['next_since']}&limit={limit}"
        assert len(out) < 20, "分頁沒有收斂"


def test_AT_932_1_2_cursor_pages_match_the_real_cli_and_concatenate_without_gaps(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    spawned = sup.record_si_popen(monkeypatch)
    obs = pages(live, "observations", 5)
    assert [len(p["items"]) for p in obs] == [5, 5, 2]
    assert [p["truncated"] for p in obs] == [True, True, False]
    assert isinstance(obs[0]["next_since"], int) and isinstance(obs[1]["next_since"], int)
    assert obs[2]["next_since"] is None
    since = [None, obs[0]["next_since"], obs[1]["next_since"]]
    for page, cursor in zip(obs, since, strict=True):
        flags = ["--limit", "5"] if cursor is None else ["--since", str(cursor), "--limit", "5"]
        baseline = sup.cli_export(root, "observations", *flags)
        assert sans_generated_at(page) == sans_generated_at(baseline)
    full = sup.cli_export(root, "observations")["items"]
    assert [i for p in obs for i in p["items"]] == full, "三頁串接必須等於不分頁（不漏不重）"
    ev = pages(live, "events", 4)
    assert [len(p["items"]) for p in ev] == [4, 2]
    assert [i for p in ev for i in p["items"]] == sup.cli_export(root, "events")["items"]
    for kind in ("runs", "proposals"):
        only = pages(live, kind, 1)
        assert len(only) == 1 and only[0]["truncated"] is False, kind
    assert len(spawned) == 3 + 2 + 2, "每個請求恰啟動一次子行程"
    expected_tail = [["--limit", "5"], ["--since", str(since[1]), "--limit", "5"],
                     ["--since", str(since[2]), "--limit", "5"], ["--limit", "4"],
                     ["--since", str(ev[0]["next_since"]), "--limit", "4"], ["--limit", "1"],
                     ["--limit", "1"]]
    kinds = ["observations"] * 3 + ["events"] * 2 + ["runs", "proposals"]
    for argv, kind, tail in zip(spawned, kinds, expected_tail, strict=True):
        assert argv[2:6] == ["export", "--json", "--kind", kind], argv
        assert argv[6:] == tail, argv


# ── AT-932-1-E-1：帳本推進後回應隨之改變，仍與真 CLI 一致、無快取 ──────────────────────────
def test_AT_932_1_E_1_the_responses_follow_the_ledger_and_nothing_is_cached(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    spawned = sup.record_si_popen(monkeypatch)
    kinds = ("observations", "events", "runs", "status")
    before = {k: live.client.get(f"/si/{k}").json() for k in kinds}
    sup.advance_to_b(root)
    after = {k: live.client.get(f"/si/{k}").json() for k in kinds}
    assert len(spawned) == 8, "兩批請求共 8 個、各啟動一次子行程（無快取）"
    for kind in kinds:
        fresh = sup.cli_export(root, kind)
        assert sans_generated_at(after[kind]) == sans_generated_at(fresh), kind
        assert sans_generated_at(after[kind]) != sans_generated_at(before[kind]), kind
        assert after[kind]["head_sha"] != before[kind]["head_sha"], f"{kind}：頂層 head_sha 要變"
    assert len(after["observations"]["items"]) == len(before["observations"]["items"]) + 1
    assert after["observations"]["items"][-1]["id"] == "OBS-SI-013"
    assert len(after["events"]["items"]) == len(before["events"]["items"]) + 1
    assert after["events"]["items"][-1]["seq"] == 7
    assert [r["id"] for r in after["runs"]["items"]] == ["RUN-SI-001", "RUN-SI-002"]
    assert after["runs"]["items"][-1]["closed_seq"] is None
    assert after["runs"]["items"][-1]["head_sha"] == sup.FIXED_RUN_HEAD
    assert "RUN-SI-002" in [r["run"] for r in after["status"]["items"][0]["open_runs"]]


# ── AT-932-1-E-2：黃金檔鏈（真輸出子集、camelCase 參考轉換、三份副本、無 sha 衍生值）──────────
def golden(state: str, flavour: str, base: Path = sup.GOLDEN_DIR) -> dict[str, Any]:
    return json.loads((base / f"{state}.{flavour}.json").read_text(encoding="utf-8"))


def test_AT_932_1_E_2_the_golden_chain_is_a_real_subset_and_the_three_copies_agree(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sup.isolate_home(monkeypatch, tmp_path)
    repo_a = sup.make_si_repo(tmp_path, "A")
    head_a = sup.head_of(repo_a)
    out_a = sup.collect_state_outputs(repo_a, with_one=True)
    repo_b = sup.advance_to_b(repo_a)
    head_b = sup.head_of(repo_b)
    out_b = sup.collect_state_outputs(repo_b, with_one=False)
    # 一、snake_case 黃金檔是真輸出的子集（容忍根層日後加欄位；缺鍵或值不同即紅）
    for state, outputs in (("A", out_a), ("B", out_b)):
        diffs = sup.golden_subset_diffs(golden(state, "snake"), outputs)
        assert diffs == [], f"{state}.snake.json 不是真輸出的子集：{diffs[:5]}。{REGEN_HINT}"
    # 二、camelCase 版逐值等於參考轉換；參考實作自帶邊界鍵表
    for key, want in {"http_status": "httpStatus", "touched_sha256": "touchedSha256",
                      "marks_kv": "marksKv", "digest8": "digest8", "PROP-SI-004": "PROP-SI-004",
                      "quota-band": "quota-band", "來源": "來源", "a__b": "a__b", "_x": "_x",
                      "x_": "x_", "Http_status": "Http_status", "sha_256": "sha256"}.items():
        assert sup.camel(key) == want, key
    for state in ("A", "B"):
        assert golden(state, "camel") == sup.camel_keys(golden(state, "snake")), \
            f"{state}.camel.json 不等於 snake 版的參考轉換。{REGEN_HINT}"
    # 三、backend 與 frontend 的副本與本目錄逐位元組相同
    copies_of = {"snake": (BACKEND_COPY,), "camel": (BACKEND_COPY, FRONTEND_COPY)}
    for state in ("A", "B"):
        for flavour, copies in copies_of.items():
            source = sup.GOLDEN_DIR / f"{state}.{flavour}.json"
            for copy_dir in copies:
                copy = copy_dir / source.name
                assert copy.is_file(), f"副本缺檔：{copy}。{REGEN_HINT}"
                assert copy.read_bytes() == source.read_bytes(), \
                    f"副本漂移：{copy} 與 {source} 不同。{REGEN_HINT}"
    # 四、黃金檔不含任何由 commit sha 衍生的值；可重現性負控
    texts = [p.read_text(encoding="utf-8") for d in (sup.GOLDEN_DIR, BACKEND_COPY, FRONTEND_COPY)
             for p in sorted(d.glob("*.json"))]
    assert len(texts) == 4 + 4 + 2
    for head in (head_a, head_b):
        assert re.fullmatch(r"[0-9a-f]{40}", head)
        assert all(head not in text for text in texts), "黃金檔含建倉所得的 HEAD"
    for state in ("A", "B"):
        for resp in golden(state, "snake").values():
            assert resp["head_sha"] == sup.ZERO_SHA and resp["generated_at"] == sup.DATE_A
    runs_b = {r["id"]: r for r in golden("B", "snake")["runs"]["items"]}
    assert runs_b["RUN-SI-002"]["head_sha"] == sup.FIXED_RUN_HEAD
    assert [e["head_sha"] for e in golden("B", "snake")["events"]["items"]
            if e["seq"] == 7] == [sup.FIXED_RUN_HEAD]

    def touch_a_closure_copy(root: Path) -> None:
        with (root / "tools" / "selfimproving.py").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("# 可重現性負控：追加一行註解，樹內容改變、HEAD 隨之改變\n")

    other = sup.make_si_repo(tmp_path, "B", name="si-repo-B-touched",
                             before_commit=touch_a_closure_copy)
    assert sup.head_of(other) != head_b, "追加註解後建倉所得 HEAD 必須不同"
    redo = sup.collect_state_outputs(other, with_one=False)
    assert sup.golden_subset_diffs(golden("B", "snake"), redo) == [], \
        "HEAD 不同，但對黃金檔的比對結果必須相同（黃金檔不依賴 commit sha）"


# ── AT-932-2-2：任意讀取操作序列之後，repo 與家目錄零變動 ──────────────────────────────────────
def test_AT_932_2_2_reads_leave_the_repo_and_the_home_directory_untouched(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, home = start(tmp_path, monkeypatch, settings, make_bridge)
    before = sup.repo_snapshot(root)
    home_before = sup.tree_listing(home)
    assert before["status"] == "" and home_before == []
    statuses: list[tuple[str, int]] = []

    def hit(path: str) -> None:
        statuses.append((path, live.client.get(path).status_code))

    paths = [p for _kind, p, _flags in SIX]
    for _ in range(3):
        for path in paths:
            hit(path)
    for query in ("since=0", "since=3&limit=2", "limit=1", "limit=500", "since=11&limit=1"):
        for kind in ("observations", "events", "proposals", "runs"):
            hit(f"/si/{kind}?{query}")
    for _ in range(10):
        hit("/si/proposals/PROP-SI-004")
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in range(8):
            for _ in range(2):
                for path in paths:
                    pool.submit(hit, path)
    blocked = [("/si/observations?since=abc", 422), ("/si/proposals/PROP-SI-998", 404),
               ("/si/status?x=1", 422)]
    for path, _want in blocked:
        hit(path)
    ok = [(p, c) for p, c in statuses if (p, c) not in [(b, 422) for b, _ in blocked]
          and (p, c) != ("/si/proposals/PROP-SI-998", 404)]
    assert all(code == 200 for _p, code in ok), [x for x in ok if x[1] != 200][:5]
    assert [c for p, c in statuses if p == blocked[0][0]] == [422]
    assert [c for p, c in statuses if p == blocked[1][0]] == [404]
    assert not [x for x in statuses if x[1] >= 500], "不得有任何 5xx"
    after = sup.repo_snapshot(root)
    assert after == before, [k for k in before if before[k] != after[k]]
    assert sup.tree_listing(home) == home_before == [], "家目錄不得有任何新項目"
    assert [p for p in root.rglob("__pycache__")] == [], "子行程不得在 repo 內留下 __pycache__"


# ── AT-932-3-3：缺件（無 .git、無家目錄）時真 CLI 回 NOT-EVALUABLE，不是失敗 ───────────────────
def _make_writable_then_retry(func: Any, path: str, _excinfo: Any) -> None:
    os.chmod(path, stat.S_IWRITE)             # Windows：git 物件檔是唯讀的，rmtree 前要先放行
    func(path)


def test_AT_932_3_3_missing_git_and_home_degrade_to_not_evaluable_not_to_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, home = start(tmp_path, monkeypatch, settings, make_bridge)
    with_git = {kind: sup.cli_export(root, kind, *flags) for kind, _p, flags in SIX}
    shutil.rmtree(root / ".git", onerror=_make_writable_then_retry)
    shutil.rmtree(home)
    monkeypatch.setenv("HOME", str(tmp_path / "no-such-home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "no-such-home"))
    got: dict[str, dict[str, Any]] = {}
    for kind, path, flags in SIX:
        resp = live.client.get(path)
        assert resp.status_code == 200, f"{path}：{resp.status_code} {resp.text[:300]}"
        body = resp.json()
        assert body["head_sha"] is None, path
        assert {"field": "head_sha", "reason": "git-unavailable"} in body["ne"], (path, body["ne"])
        assert set(body) == set(with_git[kind]), f"{path}：頂層鍵集合必須與有 .git 時相同"
        got[path] = body
    def keep(obj: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in obj.items() if k not in ("head_sha", "ne", "generated_at")}

    assert len(got["/si/observations"]["items"]) == 12
    assert keep(got["/si/observations"]) == keep(with_git["observations"])
    status = got["/si/status"]["items"][0]
    assert status["friction_reconcile"] == {"status": "NOT-EVALUABLE",
                                            "reason": "transcript-unavailable"}
    assert {"trigger": "c", "reason": "ledger-missing"} in status["unavailable"]
    for path in ("/si/proposals", "/si/proposals/PROP-SI-004"):
        assert isinstance(got[path]["items"][0]["card"], str), "M 類提案的卡面不需 git"


# ── AT-940-7-1：夾具建構器產出可用的狀態 A 與 B（反空轉前提）──────────────────────────────────
def test_AT_940_7_1_the_builder_makes_a_complete_closure_and_a_non_vacuous_fixture(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sup.isolate_home(monkeypatch, tmp_path)
    repo_a = sup.make_si_repo(tmp_path, "A")
    for rel in sup.CLI_CLOSURE:
        assert (repo_a / rel.rstrip("/")).exists(), f"閉包項目沒有複製進 tmp 倉：{rel}"
    assert not list(repo_a.rglob("__pycache__")), "複本與真 CLI 的執行都不得留下 __pycache__"
    outputs = {kind: sup.cli_run(repo_a, "export", "--json", "--kind", kind) for kind in sup.KINDS}
    assert {k: v.returncode for k, v in outputs.items()} == dict.fromkeys(sup.KINDS, 0)
    for kind, done in outputs.items():
        assert json.loads(done.stdout.decode("utf-8"))["kind"] == kind
    head_a = sup.head_of(repo_a)
    assert re.fullmatch(r"[0-9a-f]{40}", head_a)
    assert sup.git(repo_a, "status", "--porcelain") == ""
    obs = sup.cli_export(repo_a, "observations")
    items = obs["items"]
    assert (len(items), sum(1 for i in items if i.get("valid") is False)) == (12, 1)
    valid = [i for i in items if i.get("valid") is not False]

    def column(key: str) -> list[str]:
        return [i[key] for i in valid]

    assert any(re.search(r"[！-～　-〿]", s) for s in column("symptom")), "缺全形字元列"
    assert any("`" in s for s in column("evidence")) and any('"' in s for s in column("marks")), \
        "缺反引號與雙引號列"
    assert any("<script>" in s for s in column("symptom"))
    assert any("**" in s and "](" in s for s in column("symptom")), "缺 Markdown 粗體與連結列"
    assert any("&lt;" in s for s in column("symptom")), "缺 HTML 實體字樣列"
    assert any("carrier=console;audit_ref=" in s for s in column("marks")), "缺載體標記列"
    events = sup.cli_export(repo_a, "events")["items"]
    proposals = sup.cli_export(repo_a, "proposals")["items"]
    runs = sup.cli_export(repo_a, "runs")["items"]
    status = sup.cli_export(repo_a, "status")["items"][0]
    assert len(events) == 6 and len(runs) == 1 and len(proposals) == 1
    assert isinstance(proposals[0]["card"], str) and proposals[0]["card"]
    assert proposals[0]["state"] == "proposed"
    assert [p["id"] for p in status["pending_props"]] == ["PROP-SI-004"]
    repo_b = sup.advance_to_b(repo_a)
    obs_b = sup.cli_export(repo_b, "observations")
    assert obs_b["items"][:12] == items and obs_b["items"][12]["id"] == "OBS-SI-013"
    ev_b = sup.cli_export(repo_b, "events")["items"]
    assert ev_b[:6] == events and (ev_b[6]["seq"], ev_b[6]["run"], ev_b[6]["kind"]) == (
        7, "RUN-SI-002", "run.open")
    assert ev_b[6]["head_sha"] == sup.FIXED_RUN_HEAD
    runs_b = sup.cli_export(repo_b, "runs")["items"]
    assert runs_b[:1] == runs and [r["id"] for r in runs_b] == ["RUN-SI-001", "RUN-SI-002"]
    assert runs_b[1]["closed_seq"] is None and runs_b[1]["head_sha"] == sup.FIXED_RUN_HEAD
    assert sup.cli_export(repo_b, "proposals")["items"] == proposals
    assert sup.head_of(repo_b) != head_a
    assert sup.cli_export(repo_b, "status")["head_sha"] == sup.head_of(repo_b) != head_a


# ── AT-940-7-E-1：閉包缺檔時建構器大聲失敗，不退回假 CLI ──────────────────────────────────────
@pytest.mark.parametrize("missing,needle", [
    ("tools/lib/platform_utils.py", "platform_utils"), ("tools/_stdio_utf8.py", "_stdio_utf8")])
def test_AT_940_7_E_1_an_incomplete_closure_fails_loudly(
        missing: str, needle: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sup.isolate_home(monkeypatch, tmp_path)
    reduced = [rel for rel in sup.CLI_CLOSURE if rel != missing]
    assert len(reduced) == len(sup.CLI_CLOSURE) - 1
    with pytest.raises(sup.SiFixtureError) as caught:
        sup.make_si_repo(tmp_path, "A", name="broken", closure=reduced)
    message = str(caught.value)
    assert "CLI_CLOSURE" in message and needle in message, message
    ok = sup.make_si_repo(tmp_path, "A", name="complete", closure=sup.CLI_CLOSURE)
    assert sup.cli_export(ok, "status")["kind"] == "status"
