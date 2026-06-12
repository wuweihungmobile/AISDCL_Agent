"""W5（AutoSDD_improving_01 §1.2）：PlaybookCheckpoint.sdd_governance additive 欄位
三後端 round-trip 等價 + 舊格式相容契約測試。

證明義務（計畫 §1.2）：
  1. 含 sdd_governance 之 checkpoint 在 File / InMemory 後端 round-trip 等價
     （PG 後端沿用既有 test_pg_state_repository_contract 的 DSN 條件式機制；
      本檔以 dict 序列化對稱性涵蓋 JSONB blob 路徑——三後端 checkpoint 皆走
      整體序列化，additive dict 欄位不需 alembic schema 變更）
  2. 舊格式（無此欄位）載入相容：default_factory 補空 dict，零遷移破壞
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from autoclaude.infra.repositories import (
    FileStateRepository,
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint

_SDD_GOV = {
    "scg_gate": "SCG-3",
    "fsm_state": "IMPLEMENTATION",
    "contract_violations": [
        {"step_id": "sdd-brownfield-at-001-1-1", "at_id": "AT-001-1-1",
         "ts": "2026-06-12T10:00:00"},
    ],
    "spec_digest": "sha256:abcdef0123456789",
}


def _cp(**overrides) -> PlaybookCheckpoint:
    defaults = dict(
        playbook_path="sdd_bridge.yaml",
        step_idx=1,
        step_id="sdd-brownfield-at-001-1-2",
        total_steps=3,
        project="sdd-roundtrip",
        sdd_governance=dict(_SDD_GOV),
    )
    defaults.update(overrides)
    return PlaybookCheckpoint(**defaults)


class _RoundTripContract:
    def _make_repo(self, tmp_path: Path):
        raise NotImplementedError

    def test_sdd_governance_roundtrip_equivalent(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        cp = _cp()
        repo.save_checkpoint("pb_sdd", cp)
        loaded = repo.load_checkpoint("pb_sdd")
        assert loaded.sdd_governance == _SDD_GOV
        # 巢狀 list[dict] 結構完整保留（非僅頂層 key）
        assert loaded.sdd_governance["contract_violations"][0]["at_id"] == "AT-001-1-1"

    def test_default_empty_when_not_set(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        cp = _cp(sdd_governance={})
        repo.save_checkpoint("pb_plain", cp)
        assert repo.load_checkpoint("pb_plain").sdd_governance == {}


class TestFileBackendSddRoundTrip(_RoundTripContract):
    def _make_repo(self, tmp_path: Path):
        return FileStateRepository(checkpoint_dir=str(tmp_path))

    def test_legacy_checkpoint_without_field_loads(self, tmp_path: Path):
        """舊格式相容：磁碟上無 sdd_governance 鍵的 checkpoint 載入零破壞。"""
        repo = FileStateRepository(checkpoint_dir=str(tmp_path))
        legacy = asdict(_cp())
        legacy.pop("sdd_governance")  # 模擬 W5 之前寫出的舊 JSON
        path = tmp_path / "legacy.checkpoint.json"
        path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
        loaded = repo.load_checkpoint("legacy")
        assert loaded is not None
        assert loaded.sdd_governance == {}  # default_factory 補空 dict
        assert loaded.step_id == "sdd-brownfield-at-001-1-2"


class TestInMemoryBackendSddRoundTrip(_RoundTripContract):
    def _make_repo(self, tmp_path: Path):
        return InMemoryStateRepository()


class TestSerializationSymmetry:
    """三後端皆走整體序列化（YAML / JSON / JSONB blob）：
    asdict → json → 還原 必須與原 dataclass 等價（PG JSONB 路徑的等價性錨點）。"""

    def test_asdict_json_roundtrip_identity(self):
        cp = _cp()
        restored = PlaybookCheckpoint(**json.loads(json.dumps(asdict(cp))))
        assert restored.sdd_governance == cp.sdd_governance
        assert asdict(restored) == asdict(cp)

    def test_field_is_additive_last_position(self):
        """additive 紀律：新欄位不改變既有欄位序（舊位置參數呼叫不受影響）。"""
        fields = list(PlaybookCheckpoint.__dataclass_fields__)
        assert fields[-1] == "sdd_governance"
        assert fields.index("goal_task_id") == len(fields) - 2
