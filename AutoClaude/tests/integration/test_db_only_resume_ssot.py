"""tests/integration/test_db_only_resume_ssot.py
SD_Improving_04 W2 三方審查 Dev-W2-Crit-1 / Arch-W2-Maj-1 修復驗證。

目的：
    驗證 db_only 模式下 CheckpointPlugin（透過 CheckpointManager）
    與 AutoResumeService._resolve_start 使用一致 playbook_id（SSOT）。

問題背景：
    修復前 wiring.build_kernel 未注入 id_resolver，CheckpointManager
    預設用 canonical_playbook_id(p, "yaml_only") → Path.stem，
    但 AutoResumeService 用 canonical_playbook_id(p, cfg.storage.mode)。
    db_only 模式下兩者 ID 不一致 → auto-resume 永遠讀不到 checkpoint。

修復方式：
    wiring.build_kernel / wire_plugins_with_registry 注入
    id_resolver=lambda p: canonical_playbook_id(p, cfg.storage.mode)
    使 CheckpointManager 與 AutoResumeService 使用同一演算法（SSOT）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.factory import canonical_playbook_id
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"
PLAYBOOK_PATH = str(FIXTURES_DIR / "01_simple_2_step.yaml")


class _NoopKernel:
    """測試用 kernel stub；本測試只關注 _resolve_start 的 ID 解析。"""

    def run(self, playbook, start_idx: int = 0):  # noqa: ARG002
        from autoclaude.core.kernel_state import KernelResult
        return KernelResult(
            success=True, completed_steps=2, total_steps=2, reason="noop",
        )


class TestDbOnlyResumeSSOT:
    """驗 CheckpointManager 與 AutoResumeService 使用一致 playbook_id（SSOT）。"""

    @pytest.fixture(autouse=True)
    def _set_dummy_dsn(self, monkeypatch):
        """db_only 模式 StorageConfig validator 需要 DSN 環境變數；
        本測試不真的連 PG，僅驗證 ID 計算邏輯。
        """
        monkeypatch.setenv(
            "AUTOCLAUDE_DB_DSN",
            "postgresql+asyncpg://x:y@localhost/test?sslmode=require",
        )
        yield

    def test_auto_resume_and_checkpoint_plugin_use_same_id_in_db_only_mode(
        self, tmp_path
    ):
        """db_only 模式下：
          - CheckpointManager 用注入的 id_resolver=canonical_playbook_id(p, "db_only")
          - AutoResumeService 用 canonical_playbook_id(p, cfg.storage.mode="db_only")
          兩者 ID 必須一致，且 AutoResumeService._resolve_start 能讀到 CheckpointManager 寫入的資料。
        """
        cfg = AppConfig()
        cfg.storage.mode = "db_only"
        cfg.checkpoint_dir = str(tmp_path / "checkpoints")

        # InMemoryStateRepository 模擬 db_only PG backend 的儲存層。
        # PG 與本 fixture 都遵守 IStateRepository 契約（save/load by playbook_id），
        # 因此可代替 PgStateRepository 驗證 ID-routing。
        repo = InMemoryStateRepository()

        # CheckpointManager 模擬 wiring.build_kernel 注入的 id_resolver（修復後行為）
        ckpt_mgr = CheckpointManager(
            cfg.checkpoint_dir,
            repository=repo,
            id_resolver=lambda p: canonical_playbook_id(p, cfg.storage.mode),
        )

        # 透過 CheckpointManager 寫入 checkpoint（模擬 CheckpointPlugin._save_token_halt）
        ckpt_mgr.save(
            PlaybookCheckpoint(
                playbook_path=PLAYBOOK_PATH,
                step_idx=1,
                step_id="T02",
                total_steps=2,
                completed_step_log=["[T01] done"],
            ),
            PLAYBOOK_PATH,
        )

        # AutoResumeService 透過 _resolve_start 載入
        svc = AutoResumeService(_NoopKernel(), cfg, state_repository=repo)
        start_idx, step_log, has_ck, sched = svc._resolve_start(
            PLAYBOOK_PATH, fresh=False,
        )

        # SSOT 核心斷言：兩端使用同一 ID → 能讀到對方寫入的 checkpoint
        assert has_ck is True, (
            "SSOT 失效：AutoResumeService 讀不到 CheckpointManager 寫入的 checkpoint；"
            "可能是 id_resolver 未正確注入 → ID 不一致"
        )
        assert start_idx == 1
        assert step_log == ["[T01] done"]

    def test_id_resolver_returns_sha256_for_db_only(self):
        """直接驗 canonical_playbook_id 在 db_only 模式回傳 sha256[:16]，
        與 yaml_only 的 Path.stem 不同。
        """
        path_str = PLAYBOOK_PATH
        yaml_id = canonical_playbook_id(path_str, "yaml_only")
        db_id = canonical_playbook_id(path_str, "db_only")
        assert yaml_id == "01_simple_2_step"  # Path.stem
        assert len(db_id) == 16
        assert db_id != yaml_id
        # 確保 wiring 修復後 CheckpointManager 在 db_only 模式拿到的是 sha256
        ckpt_mgr = CheckpointManager(
            "checkpoints",
            id_resolver=lambda p: canonical_playbook_id(p, "db_only"),
        )
        assert ckpt_mgr._to_id(path_str) == db_id
