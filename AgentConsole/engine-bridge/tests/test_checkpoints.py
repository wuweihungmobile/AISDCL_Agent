"""checkpoint 歷史快照與「寫成引擎格式」：用引擎自己的 repository 讀回來驗證。"""
from __future__ import annotations

import uuid
from pathlib import Path

from app.checkpoints import (
    CheckpointHistory,
    build_checkpoint_state,
    load_engine_checkpoint,
    write_engine_checkpoint,
)
from app.fsutil import read_json, write_json_atomic, write_text_atomic
from app.logparse import StepDef

STEPS = [StepDef("T01", "初始化", "p1", "g1"), StepDef("T02", "測試", "p2"),
         StepDef("T03", "Ping", "p3")]


def _state(tmp_path: Path, idx: int = 1) -> dict:
    return build_checkpoint_state(
        playbook_path=tmp_path / "playbook.yaml", project="demo", steps=STEPS, step_idx=idx,
        completed_ids=[s.step_id for s in STEPS[:idx]],
        completed_log=[f"[{s.step_id}] {s.name} ✓ (attempt 1)" for s in STEPS[:idx]],
        peak_token_pct=0.6)


def test_state_points_at_the_next_step_in_the_engines_own_shape(tmp_path: Path) -> None:
    st = _state(tmp_path, 1)
    assert (st["step_idx"], st["step_id"], st["total_steps"]) == (1, "T02", 3)
    assert st["completed_step_ids"] == ["T01"]
    assert st["completed_step_log"] == ["[T01] 初始化 ✓ (attempt 1)"]
    done = _state(tmp_path, 3)
    assert (done["step_idx"], done["step_id"]) == (3, ""), "全部完成＝沒有下一步"


def test_an_engine_checkpoint_written_by_us_is_readable_by_the_engine(tmp_path: Path) -> None:
    pb = tmp_path / "playbook.yaml"
    pb.write_text("x", encoding="utf-8")
    ckpt = tmp_path / "engine" / "checkpoints"
    assert load_engine_checkpoint(ckpt, pb) is None
    write_engine_checkpoint(ckpt, pb, _state(tmp_path, 2))
    loaded = load_engine_checkpoint(ckpt, pb)
    assert loaded is not None
    assert (loaded.step_idx, loaded.step_id) == (2, "T03")
    assert loaded.completed_step_ids == ["T01", "T02"]
    assert loaded.playbook_path == str(pb), "引擎用它判斷『這份 checkpoint 屬不屬於這支 playbook』"
    on_disk = read_json(ckpt / "playbook.checkpoint.json")
    assert on_disk is not None
    # 有 checksum＝確實經過引擎自己的 writer（手寫檔不會有），且引擎讀回時已驗證通過。
    assert len(on_disk["checksum_sha256"]) == 64


def test_the_history_is_append_only_ordered_and_contract_shaped(tmp_path: Path) -> None:
    hist = CheckpointHistory(tmp_path / "history")
    assert hist.list_meta() == []
    a = hist.add(name="after-T01", step_idx=1, step_id="T02", state=_state(tmp_path, 1))
    b = hist.add(name="after-T02", step_idx=2, step_id="T03", state=_state(tmp_path, 2))
    metas = hist.list_meta()
    assert [m["name"] for m in metas] == ["after-T01", "after-T02"]
    assert set(metas[0]) == {"checkpoint_id", "name", "created_at", "step_idx", "step_id",
                             "is_automatic"}
    assert metas[0]["created_at"].endswith("+00:00")
    assert a["checkpoint_id"] != b["checkpoint_id"]
    full = hist.get(b["checkpoint_id"])
    assert full is not None
    assert full["state"]["step_idx"] == 2
    assert hist.latest()["checkpoint_id"] == b["checkpoint_id"]


def test_ids_are_canonical_uuids_and_both_spellings_are_accepted_on_input(
        tmp_path: Path) -> None:
    hist = CheckpointHistory(tmp_path / "history")
    meta = hist.add(name="x", step_idx=0, step_id="T01", state=_state(tmp_path, 0))
    cid = meta["checkpoint_id"]
    assert str(uuid.UUID(cid)) == cid, "API 回正規（有連字號）UUID，與 PG checkpoints.id 同一個值"
    assert hist.get(cid)["checkpoint_id"] == cid
    assert hist.get(cid.replace("-", ""))["checkpoint_id"] == cid
    assert hist.get(cid.upper())["checkpoint_id"] == cid


def test_get_rejects_ids_that_are_not_uuids(tmp_path: Path) -> None:
    hist = CheckpointHistory(tmp_path / "history")
    hist.add(name="x", step_idx=0, step_id="T01", state=_state(tmp_path, 0))
    for bad in ("../../etc/passwd", "*", "", "A" * 32, "0" * 31, "0" * 33, None, 7):
        assert hist.get(bad) is None  # type: ignore[arg-type]
    assert hist.get("0" * 32) is None, "格式合法但不存在"


def test_atomic_writers_roundtrip_and_tolerate_missing_files(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "run.json"
    write_json_atomic(target, {"status": "RUNNING", "中文": "值"})
    assert read_json(target) == {"status": "RUNNING", "中文": "值"}
    write_text_atomic(target, "{壞掉")
    assert read_json(target) is None
    assert read_json(tmp_path / "missing.json") is None
    assert not list((tmp_path / "sub").glob("*.tmp")), "暫存檔必須清乾淨"
