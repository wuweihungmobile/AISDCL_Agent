"""SDD governance checkpoint 後端等價（AutoSDD_improving_01 §1.2 字面落實）。

三專家審查 P2-5：計畫 §1.2 寫明 `PlaybookCheckpoint.sdd_governance` 欄位
「掛入既有 equivalence job」。本檔以 File vs InMemory 兩後端對含
sdd_governance（巢狀 contract_violations list[dict]）之 checkpoint 做
round-trip，斷言 asdict 後完全等價（巢狀結構不因 JSON 序列化 / deepcopy
路徑差異而漂移）。

對比基準：tests/contract/test_checkpoint_sdd_roundtrip.py 驗單後端 round-trip
契約；本檔驗「兩後端互為等價」（DAL 三後端等價紀律的 File/InMemory 軸）。
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint

_SDD_GOVERNANCE = {
    "scg_gate": "SCG-4",
    "fsm_state": "IMPLEMENTATION",
    "contract_violations": [
        {"step_id": "sdd-brownfield-at-001-1-1", "at_id": "AT-001-1-1",
         "ts": "2026-06-12T00:00:00"},
        {"step_id": "sdd-brownfield-at-002-1-1", "at_id": "AT-002-1-1",
         "ts": "2026-06-12T00:05:00"},
    ],
    "spec_digest": "sha256:" + "ab" * 32,
}


def _make_checkpoint() -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path="fake/sdd_equivalence.yaml",
        step_idx=1,
        step_id="sdd-brownfield-at-001-1-2",
        total_steps=3,
        project="sdd_equivalence_test",
        goto_counter={"T01": 1},
        sdd_governance={
            **_SDD_GOVERNANCE,
            # 巢狀 list[dict] 必須深拷貝隔離（與單後端契約測試同前提）
            "contract_violations": [dict(v) for v in
                                    _SDD_GOVERNANCE["contract_violations"]],
        },
    )


def _normalized(cp: PlaybookCheckpoint) -> dict:
    """asdict 後抹平 saved_at 與 checksum_sha256（兩者皆非語意欄位）。

    R100 P2-C：`checksum_sha256`（PRD §8-4 ②／§7）是**磁碟完整性產物**，與 saved_at
    同族——File 後端寫檔時算出來、載回來時帶著它；InMemory 後端沒有磁碟，結構上就沒有
    這個值。抹平它**不是**放寬 DAL 等價紀律：那道紀律守的是「同一份語意在兩個後端
    round-trip 後相等」，而 checksum 描述的是載體不是語意。
    """
    d = asdict(cp)
    d["saved_at"] = "<normalized>"
    d["checksum_sha256"] = "<normalized>"
    return d


class TestSddCheckpointBackendEquivalence:
    def test_file_vs_inmemory_round_trip_asdict_equal(self, tmp_path: Path) -> None:
        """同一 checkpoint 經 File / InMemory round-trip 後 asdict 完全等價。"""
        pid = "sdd-equivalence"
        file_repo = FileStateRepository(checkpoint_dir=str(tmp_path))
        mem_repo = InMemoryStateRepository()

        file_repo.save_checkpoint(pid, _make_checkpoint())
        mem_repo.save_checkpoint(pid, _make_checkpoint())

        cp_file = file_repo.load_latest_by_playbook(pid)
        cp_mem = mem_repo.load_latest_by_playbook(pid)
        assert cp_file is not None and cp_mem is not None

        assert _normalized(cp_file) == _normalized(cp_mem), (
            "File vs InMemory 後端對 sdd_governance checkpoint 的 round-trip "
            "結果不等價（DAL 等價紀律破缺）"
        )

    def test_nested_contract_violations_survive_both_backends(
        self, tmp_path: Path,
    ) -> None:
        """巢狀 contract_violations list[dict] 兩後端皆與原始輸入逐欄一致。"""
        pid = "sdd-equivalence-nested"
        backends = (
            FileStateRepository(checkpoint_dir=str(tmp_path)),
            InMemoryStateRepository(),
        )
        for repo in backends:
            repo.save_checkpoint(pid, _make_checkpoint())
            cp = repo.load_latest_by_playbook(pid)
            assert cp is not None
            sdd = cp.sdd_governance
            assert sdd["scg_gate"] == "SCG-4"
            assert sdd["fsm_state"] == "IMPLEMENTATION"
            assert sdd["spec_digest"] == _SDD_GOVERNANCE["spec_digest"]
            assert sdd["contract_violations"] == \
                _SDD_GOVERNANCE["contract_violations"], type(repo).__name__

    def test_empty_sdd_governance_equivalent_default(self, tmp_path: Path) -> None:
        """非 SDD playbook（sdd_governance 預設空 dict）兩後端亦等價。"""
        pid = "sdd-equivalence-empty"
        plain = PlaybookCheckpoint(
            playbook_path="fake/plain.yaml", step_idx=0, step_id="T01",
            total_steps=1, project="plain",
        )
        file_repo = FileStateRepository(checkpoint_dir=str(tmp_path))
        mem_repo = InMemoryStateRepository()
        file_repo.save_checkpoint(pid, plain)
        mem_repo.save_checkpoint(pid, PlaybookCheckpoint(
            playbook_path="fake/plain.yaml", step_idx=0, step_id="T01",
            total_steps=1, project="plain",
        ))
        cp_file = file_repo.load_latest_by_playbook(pid)
        cp_mem = mem_repo.load_latest_by_playbook(pid)
        assert cp_file.sdd_governance == {} == cp_mem.sdd_governance
        assert _normalized(cp_file) == _normalized(cp_mem)
