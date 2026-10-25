"""Console 簽出的稽核檔被**真 CLI** 收下（TCS-SelfImprovingDecide-P2b：AT-933-1-5、AT-933-1-E-4、
AT-935-1-4、AT-935-1-E-4、AT-935-2-4、AT-935-2-E-3、AT-950-3-3、AT-950-4-3、AT-950-11-E-2）。

這一組測試證明「逐位元被收」：黃金檔 G1～G5（backend 簽章器在固定輸入下的輸出）被根層 CLI 的
`decide`／`obs-add`／`obs-close --carrier console` 驗簽入帳，事件與帳本列逐值如 TCS §5.3；篡改變形
與 CLI 才判得出的違規逐一被拒收（rc 1＋對應碼），且拒收前後兩本帳的位元組完全不變。全部只在 tmp
倉（`make_si_repo(closure=WRITE_CLOSURE)`）與 tmp 家目錄內寫，不碰真帳本與真 `~/.autosdd/`。
AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.settings import Settings
from tests import si_repo_support as sup

K0, T0 = sup.K0, sup.T0
D0 = "sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c"
GOLDEN_TIME = "2026-10-24T22:30:15+08:00"
DEC_BASE_KEYS = {"seq", "t", "kind", "by", "id", "dkind", "prop", "digest", "carrier", "audit_ref",
                 "audit_sha256", "key_id", "decider", "decided_at"}
OBS_EVENT_KEYS = {"seq", "t", "kind", "by", "obs", "audit_ref", "audit_sha256", "key_id", "decider",
                  "carrier"}


# ── 共用小工具 ───────────────────────────────────────────────────────────────────────────────
def new_repo(tmp_path: Path, tag: str) -> tuple[Path, Path]:
    """全新的狀態 A 倉（寫入閉包）與自己的家目錄（內有空的 `console_audit/`）。"""
    root = sup.make_si_repo(tmp_path, "A", name=f"si-repo-{tag}", closure=sup.WRITE_CLOSURE)
    home = tmp_path / f"home-{tag}"
    (home / "console_audit").mkdir(parents=True)
    return root, home


def place(home: Path, raw: bytes) -> str:
    """把稽核檔放進 `home/console_audit/<audit_ref>.json`，回傳 ref。"""
    ref = json.loads(raw.decode("utf-8"))["audit_ref"]
    (home / "console_audit" / f"{ref}.json").write_bytes(raw)
    return ref


def ledgers(root: Path) -> tuple[bytes, bytes]:
    """（OBS 帳本位元組，事件帳本位元組）。"""
    return (root / sup.OBS_LEDGER_REL).read_bytes(), (root / sup.EVENT_LEDGER_REL).read_bytes()


def decide(root: Path, home: Path, ref: str, key: str | None = K0,
           target: str = "PROP-SI-004") -> tuple[int, dict[str, Any], str]:
    rc, out, err = sup.ingest_run(root, home, key, "decide", target, "--carrier", "console",
                                  "--audit-ref", ref, "--json")
    return rc, json.loads(out), err


def obs_verb(root: Path, home: Path, verb: str, ref: str,
             key: str | None = K0) -> tuple[int, dict[str, Any], str]:
    rc, out, err = sup.ingest_run(root, home, key, verb, "--carrier", "console", "--audit-ref", ref,
                                  "--json")
    return rc, json.loads(out), err


def fail_set(check_json: dict[str, Any]) -> set[tuple[str, str, str]]:
    """`check --json` 的失敗集合：（項目 id，finding 對象，碼）。"""
    out: set[tuple[str, str, str]] = set()
    for item in check_json["items"]:
        findings = item.get("findings") or []
        out |= {(item["id"], str(f.get("subject")), f["code"])
                for f in findings if f.get("level") == "fail"}
        if item["status"] == "FAIL" and not findings:
            out.add((item["id"], "", "FAIL"))
    return out


def check_fails(root: Path, home: Path) -> set[tuple[str, str, str]]:
    rc, out, err = sup.ingest_run(root, home, K0, "check", "--json")
    assert rc in (0, 1), f"check rc={rc}：{err[-300:]}"
    return fail_set(json.loads(out))


def codes_of(result: dict[str, Any]) -> list[str]:
    return [c["code"] for c in result["codes"]]


def events_items(root: Path) -> list[dict[str, Any]]:
    return sup.cli_export(root, "events")["items"]


def row_cells(line: str) -> list[str]:
    return line[2:-2].split(" | ")


def obs_body(ref: str, **over: Any) -> dict[str, Any]:
    """obs-add 的 body 物件（鍵序同 backend 簽章器）；`over` 的值為 `...` 表示刪掉該鍵。"""
    body: dict[str, Any] = {
        "schema_rev": 1, "audit_ref": ref, "kind": "obs-add", "user": "admin", "role": "ADMIN",
        "time": GOLDEN_TIME, "context": "Console・自我進化頁",
        "symptom": "待入帳徽章在入帳後仍顯示",
        "evidence": "AgentConsole/frontend/components/domain/si/SiView.tsx:88",
        "category": "bug", "severity": "P3", "face": "產品", "external_derived": False}
    for key, value in over.items():
        if value is ...:
            body.pop(key, None)
        else:
            body[key] = value
    return body


def close_body(ref: str, obs_id: str, disposition: str) -> dict[str, Any]:
    return {"schema_rev": 1, "audit_ref": ref, "kind": "obs-close", "user": "admin",
            "role": "ADMIN", "time": GOLDEN_TIME, "obs_id": obs_id, "disposition": disposition}


# ── AT-933-1-5：G1、G2 被真 `decide --carrier console` 收下 ─────────────────────────────────────
@pytest.mark.parametrize("code,dkind,state", [("G1", "approve", "approved"),
                                              ("G2", "reject", "rejected")])
def test_AT_933_1_5_golden_decide_files_are_ingested_by_the_real_cli(
        tmp_path: Path, code: str, dkind: str, state: str) -> None:
    root, home = new_repo(tmp_path, code)
    raw = sup.read_audit_golden(code)
    body = json.loads(json.loads(raw.decode("utf-8"))["body"])
    ref = place(home, raw)
    events_before = events_items(root)
    fails_before = check_fails(root, home)
    rc, result, err = decide(root, home, ref)
    assert rc == 0, f"{code}：rc={rc} {result} {err[-300:]}"
    assert (result["ok"], result["kind"], result["prop"], result["dkind"], result["digest8"]) == (
        True, "dec", "PROP-SI-004", dkind, "d21ae6f5"), result
    assert result["id"].startswith("DEC-SI-") and result["seq"] == 7
    events_after = events_items(root)
    assert events_after[:-1] == events_before and len(events_after) == len(events_before) + 1
    event = events_after[-1]
    want_keys = DEC_BASE_KEYS | ({"reason", "reason_class"} if code == "G2" else set())
    assert set(event) == want_keys, f"{code}：事件鍵集合 {sorted(event)}"
    assert (event["kind"], event["dkind"], event["prop"], event["digest"]) == (
        "dec", dkind, "PROP-SI-004", D0)
    assert event["carrier"] == "console" and event["audit_ref"] == ref
    assert event["audit_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert (event["key_id"], event["decider"], event["decided_at"]) == (
        sup.K0_ID, "admin", body["time"])
    assert not {"quote", "sid", "line", "card_seq"} & set(event)
    if code == "G2":
        assert (event["reason"], event["reason_class"]) == ("證據座標不足，無法判定", "證據不足")
    prop = sup.cli_export(root, "proposals", "--id", "PROP-SI-004")["items"][0]
    assert prop["state"] == state
    if code == "G2":
        assert (prop["cooldown"]["reason_class"], prop["cooldown"]["rejected_seq"]) == (
            "證據不足", 7)
    assert check_fails(root, home) <= fails_before, "check 的失敗集合不得因入帳而新增"


# ── AT-933-1-E-4：八種篡改變形被真 CLI 拒收，兩本帳位元組不變 ─────────────────────────────────
TAMPERS: list[tuple[str, Any, str | None, str]] = [
    # (名稱, 由 G1 位元組造變形, 金鑰環, 期望碼)
    ("1-body-one-char", lambda raw: sup.audit_variant(
        raw, body_replace=('"user":"admin"', '"user":"admiN"')), K0, "AUDIT-MAC-MISMATCH"),
    ("2-digest-last-char", lambda raw: sup.audit_variant(
        raw, body_replace=('1419cec9c"', '1419cec90"'), sign_with=K0), K0, "STALE-CARD"),
    ("3-time-z", lambda raw: sup.audit_variant(
        raw, body_replace=('+08:00"', 'Z"'), sign_with=K0), K0, "AUDIT-TIME-FORMAT"),
    ("4-extra-outer-key", lambda raw: sup.audit_variant(raw, extra_outer={"x": 1}), K0,
     "AUDIT-SCHEMA"),
    ("5-key-ring-unset", lambda raw: raw, None, "AUDIT-KEY-MISSING"),
    ("7-mac-signed-with-key-plus-x", lambda raw: sup.audit_variant(raw, sign_with=K0 + "x"), K0,
     "AUDIT-MAC-MISMATCH"),
    ("8-key-id-not-in-ring", lambda raw: sup.audit_variant(raw, key_id="deadbeef"), K0,
     "AUDIT-KEY-UNKNOWN"),
]


@pytest.mark.parametrize("name,build,key,want", TAMPERS, ids=[t[0] for t in TAMPERS])
def test_AT_933_1_E_4_tampered_audit_files_are_rejected_and_the_ledgers_stay_byte_identical(
        tmp_path: Path, name: str, build: Any, key: str | None, want: str) -> None:
    root, home = new_repo(tmp_path, name)
    raw = build(sup.read_audit_golden("G1"))
    assert raw != sup.read_audit_golden("G1") or name == "5-key-ring-unset", \
        "變形必須真的改了位元組"
    ref = place(home, raw)
    before = ledgers(root)
    rc, result, err = decide(root, home, ref, key)
    assert rc == 1, f"{name}：rc={rc} {result} {err[-300:]}"
    assert result["ok"] is False and codes_of(result) == [want], f"{name}：{result['codes']}"
    assert ledgers(root) == before, f"{name}：拒收不得改動任何一本帳"


def test_AT_933_1_E_4_the_same_audit_ref_cannot_be_ingested_twice(tmp_path: Path) -> None:
    root, home = new_repo(tmp_path, "6-ref-reused")
    ref = place(home, sup.read_audit_golden("G1"))
    rc, result, _err = decide(root, home, ref)
    assert rc == 0 and result["ok"] is True
    between = ledgers(root)
    rc, result, err = decide(root, home, ref)
    assert rc == 1, f"第二次入帳 rc={rc} {result} {err[-300:]}"
    assert result["ok"] is False and codes_of(result) == ["AUDIT-REF-REUSED"], result["codes"]
    assert ledgers(root) == between, "第二次入帳被拒，兩本帳不得再變"


# ── AT-935-1-4：G3、G4 被真 obs-add 收下 ────────────────────────────────────────────────────────
G3_ROW = ("| OBS-SI-013 | 2026-10-24 22:30 +08:00 | Console・自我進化頁 | "
          "待入帳徽章在入帳後仍顯示 | "
          "AgentConsole/frontend/components/domain/si/SiView.tsx:88 | bug | P3 | open | "
          "面=產品;來源=人;回報者=admin;carrier=console;audit_ref=a1000000-0000-4000-8000-"
          "000000000003 |")
G4_ROW = G3_ROW.replace("面=產品;來源=人", "面=產品;rel=corrects:OBS-SI-001;來源=人").replace(
    "a1000000-0000-4000-8000-000000000003", "a1000000-0000-4000-8000-000000000004")


@pytest.mark.parametrize("code,row,row_bytes", [("G3", G3_ROW, 287), ("G4", G4_ROW, 311)])
def test_AT_935_1_4_golden_obs_add_files_are_ingested_as_one_row(
        tmp_path: Path, code: str, row: str, row_bytes: int) -> None:
    root, home = new_repo(tmp_path, code)
    raw = sup.read_audit_golden(code)
    ref = place(home, raw)
    obs_before, _ev = ledgers(root)
    events_before = events_items(root)
    fails_before = check_fails(root, home)
    rc, result, err = obs_verb(root, home, "obs-add", ref)
    assert rc == 0, f"{code}：rc={rc} {result} {err[-300:]}"
    assert result == {"ok": True, "kind": "obs.add", "seq": 7, "id": "OBS-SI-013",
                      "audit_ref": ref}, result
    obs_after, _ev = ledgers(root)
    assert obs_after.decode("utf-8") == obs_before.decode("utf-8") + row + "\n", \
        f"{code}：帳本只准在尾端多一列，且文字逐字如 §5.3"
    assert len(row.encode("utf-8")) == row_bytes
    events_after = events_items(root)
    assert events_after[:-1] == events_before
    event = events_after[-1]
    assert set(event) == OBS_EVENT_KEYS, f"{code}：事件鍵集合 {sorted(event)}"
    assert (event["kind"], event["obs"], event["audit_ref"], event["carrier"]) == (
        "obs.add", "OBS-SI-013", ref, "console")
    assert event["audit_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert (event["key_id"], event["decider"]) == (sup.K0_ID, "admin")
    assert check_fails(root, home) <= fails_before, "check 的失敗集合不得因入帳而新增"


# ── AT-935-1-E-4：CLI 拒收碼與 validate 一致 ────────────────────────────────────────────────────
BIG = "壹" * 100                  # 300 位元組：兩欄就 600，加上固定開銷必超過 700
#: 帳本上不存在的 OBS 號：刻意在執行期組字串、不寫成字面值（根層 `ref.obs` 判準掃整個 repo 的
#: `OBS-SI-<數字>` 字面並要求它們存在於觀察帳本）。
ABSENT_OBS = "OBS-SI-" + "999"
OBS_REJECTS: list[tuple[str, dict[str, Any], str]] = [
    ("pipe-in-field", {"symptom": "症狀含|豎線"}, "PIPE-IN-FIELD"),
    ("coord-none", {"evidence": "這段證據沒有任何可定位座標"}, "COORD-NONE"),
    ("row-bytes-over", {"context": BIG, "symptom": BIG}, "ROW-BYTES-OVER"),
    ("corrects-not-found", {"corrects": ABSENT_OBS}, "CORRECTS-NOT-FOUND"),
    ("guard-without-exposure", {"face": "守衛"}, "EXPOSURE-REQUIRED"),
    ("exposure-on-non-guard", {"exposure": "a"}, "EXPOSURE-UNEXPECTED"),
]


def post_validate(live: Any, payload: bytes) -> Any:
    return live.client.post("/si/observations:validate", content=payload,
                            headers={"Content-Type": "application/json"})


def test_AT_935_1_E_4_cli_rejection_codes_match_what_validate_reports(
        tmp_path: Path, settings: Settings, make_bridge: Any,
        monkeypatch: pytest.MonkeyPatch) -> None:
    sup.isolate_home(monkeypatch, tmp_path)
    root, home = new_repo(tmp_path, "obs-rejects")
    audit_dir = tmp_path / "audit-dir"
    audit_dir.mkdir()
    live = make_bridge(replace(settings, si_root=root, si_write_token=T0, si_audit_dir=audit_dir))
    before = ledgers(root)
    assert len(OBS_REJECTS) == 6
    for i, (name, over, want) in enumerate(OBS_REJECTS, start=1):
        ref = f"b5000000-0000-4000-8000-00000000000{i}"
        body = obs_body(ref, **over)
        place(home, sup.signed_audit("obs-add", None, body))
        rc, result, err = obs_verb(root, home, "obs-add", ref)
        assert rc == 1, f"{name}：rc={rc} {result} {err[-300:]}"
        assert result["ok"] is False and codes_of(result) == [want], f"{name}：{result['codes']}"
        assert ledgers(root) == before, f"{name}：拒收不得改動任何一本帳"
        resp = post_validate(live, json.dumps(body, ensure_ascii=False).encode("utf-8"))
        assert resp.status_code == 200, f"{name}：{resp.status_code} {resp.text[:200]}"
        verdict = resp.json()
        assert verdict["ok"] is False, f"{name}：validate 必須同樣判不過"
        assert {f["code"] for f in verdict["findings"]} == {want}, f"{name}：{verdict['findings']}"
    good = post_validate(live, json.dumps(obs_body("b5000000-0000-4000-8000-0000000000aa"),
                                          ensure_ascii=False).encode("utf-8"))
    assert good.status_code == 200 and good.json()["ok"] is True and good.json()["findings"] == []


# ── AT-935-2-4：G5 被真 obs-close 收下，只動處置欄 ─────────────────────────────────────────────
def test_AT_935_2_4_golden_obs_close_changes_only_the_disposition_cell(tmp_path: Path) -> None:
    root, home = new_repo(tmp_path, "G5")
    raw = sup.read_audit_golden("G5")
    ref = place(home, raw)
    obs_before = (root / sup.OBS_LEDGER_REL).read_text(encoding="utf-8").split("\n")
    events_before = events_items(root)
    fails_before = check_fails(root, home)
    rc, result, err = obs_verb(root, home, "obs-close", ref)
    assert rc == 0, f"rc={rc} {result} {err[-300:]}"
    assert (result["ok"], result["kind"], result["id"], result["audit_ref"]) == (
        True, "obs.close", "OBS-SI-005", ref), result
    obs_after = (root / sup.OBS_LEDGER_REL).read_text(encoding="utf-8").split("\n")
    assert len(obs_after) == len(obs_before), "行數不得變"
    changed = [(a, b) for a, b in zip(obs_before, obs_after, strict=True) if a != b]
    assert len(changed) == 1, f"只准一行改變：{changed}"
    old, new = row_cells(changed[0][0]), row_cells(changed[0][1])
    assert old[0] == new[0] == "OBS-SI-005" and len(old) == len(new) == 9
    assert [i for i in range(9) if old[i] != new[i]] == [7], "只有第八欄（處置）可以不同"
    assert old[7] == "open" and new[7] == "decided：夾具關閉"
    events_after = events_items(root)
    assert events_after[:-1] == events_before
    event = events_after[-1]
    assert set(event) == OBS_EVENT_KEYS | {"disposition"}, f"事件鍵集合 {sorted(event)}"
    assert (event["kind"], event["obs"], event["disposition"], event["carrier"]) == (
        "obs.close", "OBS-SI-005", "decided：夾具關閉", "console")
    assert event["audit_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert check_fails(root, home) <= fails_before, "check 的失敗集合不得因入帳而新增"


# ── AT-935-2-E-3：CLI 拒收關閉 ─────────────────────────────────────────────────────────────────
CLOSE_REJECTS: list[tuple[str, str, str, str]] = [
    ("not-open", "OBS-SI-006", "decided：重複關閉", "NOT-OPEN"),
    ("obs-not-found", ABSENT_OBS, "decided：不存在的列", "OBS-NOT-FOUND"),
    ("retired-without-coordinate", "OBS-SI-005", "retired：沒有任何座標的說明",
     "DISPOSITION-TEXT-MISSING"),
]


def test_AT_935_2_E_3_the_real_cli_rejects_bad_closes_without_touching_the_ledgers(
        tmp_path: Path) -> None:
    root, home = new_repo(tmp_path, "close-rejects")
    before = ledgers(root)
    for i, (name, obs_id, disposition, want) in enumerate(CLOSE_REJECTS, start=1):
        ref = f"b6000000-0000-4000-8000-00000000000{i}"
        place(home, sup.signed_audit("obs-close", obs_id, close_body(ref, obs_id, disposition)))
        rc, result, err = obs_verb(root, home, "obs-close", ref)
        assert rc == 1, f"{name}：rc={rc} {result} {err[-300:]}"
        assert result["ok"] is False and codes_of(result) == [want], f"{name}：{result['codes']}"
        assert ledgers(root) == before, f"{name}：拒收不得改動任何一本帳"


# ── AT-950-3-3：validate 與真 CLI dry-run 逐值相等 ──────────────────────────────────────────────
def dry_run(root: Path, payload: bytes) -> dict[str, Any]:
    """基準：直接以真 CLI 跑 `obs-add --dry-run --body-file - --json`（stdin 餵位元組）。"""
    done = subprocess.run(
        [sys.executable, str(root / sup.SCRIPT_REL), "obs-add", "--dry-run", "--body-file", "-",
         "--json"], cwd=str(root), env=sup.cli_env(root), input=payload, capture_output=True,
        timeout=120, check=False)
    assert done.returncode in (0, 1), done.stderr.decode("utf-8", errors="replace")[-300:]
    return json.loads(done.stdout.decode("utf-8"))


def test_AT_950_3_3_validate_equals_the_real_dry_run_and_previews_the_ingested_row(
        tmp_path: Path, settings: Settings, make_bridge: Any,
        monkeypatch: pytest.MonkeyPatch) -> None:
    sup.isolate_home(monkeypatch, tmp_path)
    root, home = new_repo(tmp_path, "validate")
    audit_dir = tmp_path / "audit-dir"
    audit_dir.mkdir()
    live = make_bridge(replace(settings, si_root=root, si_write_token=T0, si_audit_dir=audit_dir))
    raw = sup.read_audit_golden("G3")
    body_text = json.loads(raw.decode("utf-8"))["body"]
    payload = body_text.encode("utf-8")
    status_before = sup.git(root, "status", "--porcelain")
    home_before = sup.tree_listing(home)
    resp = post_validate(live, payload)
    assert resp.status_code == 200, resp.text[:300]
    got = resp.json()
    assert got == dry_run(root, payload), "validate 必須與直接跑 CLI dry-run 逐值相等"
    assert got["ok"] is True and got["findings"] == []
    assert got["row"] == G3_ROW, "受控輸入（帶同一個 audit_ref 與 time）下預覽列逐字等於將入帳的列"
    assert got["row_bytes"] == len(got["row"].encode("utf-8")) == 287
    assert got["row_max_bytes"] == 700
    body = json.loads(body_text)
    no_ref = {k: v for k, v in body.items() if k != "audit_ref"}
    resp2 = post_validate(live, json.dumps(no_ref, ensure_ascii=False).encode("utf-8"))
    assert resp2.status_code == 200 and resp2.json()["ok"] is True
    assert resp2.json()["row_bytes"] == 287, "audit_ref 以等長的全零 UUID 佔位，位元組數不變"
    assert sup.git(root, "status", "--porcelain") == status_before
    assert sup.tree_listing(home) == home_before, "validate 不得在家目錄留任何東西"
    ref = place(home, raw)
    rc, result, err = obs_verb(root, home, "obs-add", ref)
    assert rc == 0, f"rc={rc} {result} {err[-300:]}"
    obs_text = (root / sup.OBS_LEDGER_REL).read_text(encoding="utf-8").rstrip("\n")
    assert obs_text.split("\n")[-1] == got["row"], "入帳後新增的列逐字等於 validate 的預覽列"


# ── AT-950-4-3：黃金檔鏈 ───────────────────────────────────────────────────────────────────────
#: TCS §5.3 的 sha256 與 mac（逐檔）。
GOLDEN_TABLE: dict[str, tuple[str, str]] = {
    "decide-approve.json": ("831acfcd69993cee663ded3ab6d5ac6305a90631d3c55259bdaa452b3e87b337",
                            "18f299d249ab36dfe28975fc61fff8a15a1c20fa9602af66fadd26e4af5917aa"),
    "decide-reject.json": ("9d81e866542ae0c84331861671f7780de91a328c19b487b3a23a45c85d06d046",
                           "ae47199c39cad71546f64170c885b7545c4f77a8a32b5a39b7f0a10933858c8b"),
    "obs-add.json": ("fc3917fa5c1d3b0dad7c258de028130981e5ac63ed1c0e991919054a9ffd3c1f",
                     "7505ec8a9eb60f7b6b168d2c659dbe77ed6fad2c103b0238396b42fc70accf09"),
    "obs-add-corrects.json": ("faba0eed8cfe1cee1087a291c385011160d5fcca2406c8eb84889c3a1fc646c7",
                              "ccbc3e7aa73925b976a553dc2e062b758d556c7e5d27a2ded8202334b7b012b9"),
    "obs-close.json": ("4c5985a35c6da9189ab0277149c67f745c9977b5b5694f229e03c95910af5b57",
                       "fb9c251546f9f40bbe303579c40c39ea2a3e53e09acea60317a0e72533e24410"),
}
BACKEND_AUDIT_DIR = (sup.MONOREPO / "AgentConsole" / "backend" / "src" / "test" / "resources" / "si"
                     / "audit")
OUTER_KEYS = ["schema_rev", "kind", "audit_ref", "subject", "body", "key_id", "mac"]


def golden_problems(label: str, directory: Path) -> list[str]:
    """一份黃金檔目錄的問題清單（空＝合格）：檔名集合、sha256、外層鍵與鍵序、body 為字串、以標準庫
    重算 mac 與 key_id。訊息一律帶 `label`，指出是哪一份。"""
    out: list[str] = []
    names = {p.name for p in directory.glob("*.json")} if directory.is_dir() else set()
    if names != set(GOLDEN_TABLE):
        out.append(f"{label}：檔名集合 {sorted(names)} 不等於 {sorted(GOLDEN_TABLE)}")
    for name, (sha, mac) in GOLDEN_TABLE.items():
        path = directory / name
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            out.append(f"{label}/{name}：sha256 與 §5.3 不同")
        outer = json.loads(raw.decode("utf-8"))
        if list(outer) != OUTER_KEYS:
            out.append(f"{label}/{name}：外層鍵或鍵序不合 {list(outer)}")
            continue
        if not isinstance(outer["body"], str):
            out.append(f"{label}/{name}：body 不是字串")
            continue
        if outer["mac"] != sup.hmac_hex(K0, outer["body"]) or outer["mac"] != mac:
            out.append(f"{label}/{name}：mac 以 K0 重算不相等")
        if outer["key_id"] != sup.key_id_of(K0) or outer["key_id"] != sup.K0_ID:
            out.append(f"{label}/{name}：key_id 不是 K0 的")
    return out


def test_AT_950_4_3_the_golden_chain_is_byte_identical_and_recomputable() -> None:
    assert golden_problems("Bridge 副本", sup.AUDIT_GOLDEN_DIR) == []
    assert golden_problems("backend 資源", BACKEND_AUDIT_DIR) == []
    for name in GOLDEN_TABLE:
        bridge = (sup.AUDIT_GOLDEN_DIR / name).read_bytes()
        backend = (BACKEND_AUDIT_DIR / name).read_bytes()
        assert bridge == backend, f"{name}：Bridge 副本與 backend 資源的位元組不同"
    # 負控：單點改動必被指出是哪一份
    bad = sup.AUDIT_GOLDEN_DIR.parent / "si_audit_probe_does_not_exist"
    assert any("檔名集合" in p for p in golden_problems("不存在的目錄", bad))


def test_AT_950_4_3_the_checker_names_the_copy_that_drifted(tmp_path: Path) -> None:
    drift = tmp_path / "drift"
    drift.mkdir()
    for name in GOLDEN_TABLE:
        (drift / name).write_bytes((sup.AUDIT_GOLDEN_DIR / name).read_bytes())
    victim = drift / "obs-close.json"
    victim.write_bytes(victim.read_bytes().replace("夾具".encode(), "夾俱".encode()))
    problems = golden_problems("漂移的那份", drift)
    assert problems and all(p.startswith("漂移的那份") for p in problems)
    assert any("obs-close.json" in p and "sha256" in p for p in problems)
    assert any("obs-close.json" in p and "mac" in p for p in problems)


# ── AT-950-11-E-2：寫入閉包缺檔時大聲失敗 ──────────────────────────────────────────────────────
@pytest.mark.parametrize("missing", ["tools/lib/apply_lock.py", "tools/lib/sdd_latest.py"])
def test_AT_950_11_E_2_a_write_closure_missing_a_file_fails_loudly_and_never_falls_back(
        tmp_path: Path, missing: str) -> None:
    closure = tuple(item for item in sup.WRITE_CLOSURE if item != missing)
    with pytest.raises(sup.SiFixtureError) as caught:
        sup.make_si_repo(tmp_path, "A", closure=closure)
    message = str(caught.value)
    assert "WRITE_CLOSURE" in message, message
    assert missing in message, f"訊息須指出缺的檔名 {missing}：{message}"


def test_AT_950_11_E_2_a_complete_write_closure_builds_and_ingests(tmp_path: Path) -> None:
    root, home = new_repo(tmp_path, "complete-closure")
    ref = place(home, sup.read_audit_golden("G1"))
    rc, result, err = decide(root, home, ref)
    assert rc == 0 and result["ok"] is True, f"{result} {err[-300:]}"
