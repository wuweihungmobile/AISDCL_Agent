"""PlaybookPersistencePlugin 單元測試（SD_Improving_05 W4-3）。

驗證：
  - subscribed_phases / priority / name
  - ON_EVOLUTION_APPLY 訂閱位 NO-OP（logger.info）
  - persist_mutated_playbook 成功寫入 .mutated.yaml
  - persist_mutated_playbook 容錯（mkdir 失敗 / yaml 失敗）
  - load_mutated_if_exists 偵測檔案 + checkpoint_exists guard
  - cleanup_mutated_for_paths 清理 + 不存在跳過 + OSError 容錯
  - mutated_path stem 命名一致（path 不影響 stem 推導）
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from autoclaude.core.hookspec import HookContext, KernelPhase, PersistenceResult
from autoclaude.plugins.playbook_persistence_plugin import PlaybookPersistencePlugin
from tests.plugins._template import sample_playbook, sample_task


def _ctx(phase: KernelPhase = KernelPhase.ON_EVOLUTION_APPLY):
    return HookContext(
        phase=phase,
        playbook=sample_playbook(),
        task=sample_task(),
        step_idx=0,
        attempt=1,
        payload={},
    )


class TestBasics:
    def test_name_priority_phases(self):
        p = PlaybookPersistencePlugin()
        # wiring SSOT 對齊 _REGISTER_ORDER（"playbook_persistence"）
        assert p.name() == "playbook_persistence"
        assert p.priority() == PlaybookPersistencePlugin.PRIORITY
        assert p.subscribed_phases() == [KernelPhase.ON_EVOLUTION_APPLY]

    def test_on_event_noop_returns_persistence_result(self, caplog):
        # SA-M4 / Arch-M2：對齊 PHASE_RESULT_CONTRACT，回 PersistenceResult NO-OP
        p = PlaybookPersistencePlugin()
        with caplog.at_level(logging.INFO):
            result = p.on_event(_ctx())
        assert isinstance(result, PersistenceResult)
        assert result.succeeded is True
        assert result.kind == "no_op"
        assert result.contributor == "playbook_persistence"
        assert any("ON_EVOLUTION_APPLY" in r.message for r in caplog.records)

    def test_on_event_other_phase_returns_none_silently(self, caplog):
        p = PlaybookPersistencePlugin()
        with caplog.at_level(logging.INFO):
            result = p.on_event(_ctx(KernelPhase.POST_STEP))
        assert result is None
        # 非訂閱 phase 不該觸發 audit log
        assert not any("ON_EVOLUTION_APPLY" in r.message for r in caplog.records)

    def test_callable_resolver_dynamic_dir(self, tmp_path):
        # SD_05 W4 三方審查修復：callable resolver 動態解析
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        dir_b = tmp_path / "b"
        dir_b.mkdir()
        current = {"dir": str(dir_a)}
        p = PlaybookPersistencePlugin(checkpoint_dir=lambda: current["dir"])
        out1 = p.persist_mutated_playbook(sample_playbook(), "test.yaml")
        assert out1 is not None
        assert dir_a in out1.parents
        current["dir"] = str(dir_b)
        out2 = p.persist_mutated_playbook(sample_playbook(), "test.yaml")
        assert out2 is not None
        assert dir_b in out2.parents


class TestPersistMutated:
    def test_writes_mutated_yaml_with_correct_stem(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        pb = sample_playbook()
        out = p.persist_mutated_playbook(pb, "some/dir/origin.yaml")
        assert out is not None
        assert out.name == "origin.mutated.yaml"
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        # YAML 內含 project 名稱
        assert "TEST" in content

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        p = PlaybookPersistencePlugin(checkpoint_dir=str(nested))
        out = p.persist_mutated_playbook(sample_playbook(), "origin.yaml")
        assert out is not None
        assert nested.exists()
        assert out.exists()

    # ── R56 迴歸鎖（DEF-101-442）：checkpoint_dir 檔名家族第三個 sibling ──────
    # _mutated_path_for() 與 FileStateRepository._path()（DEF-101-384 / R47）、
    # CheckpointManager.checkpoint_path()（DEF-101-390 / R48）同屬「以使用者提供的
    # playbook_path 衍生檔名寫進 checkpoint_dir」家族；另兩支已收斂到 SSOT
    # _sanitize_log_filename，本支此前裸用 Path().stem。Windows 上 NTFS 保留裝置名
    # 與禁用字元會讓 open("w") 直接 OSError，而 persist_mutated_playbook() 的 except
    # 只 logger.warning → 突變後 playbook 靜默遺失。下面兩支鎖「必須經 SSOT 淨化」。

    def test_mutated_path_sanitizes_windows_reserved_device_name(self, tmp_path):
        """stem 為 NTFS 保留裝置名（CON/AUX/…）時，檔名必須被 SSOT 淨化。"""
        from autoclaude.utils.logger import _sanitize_log_filename

        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        out = p._mutated_path_for("some/dir/CON.yaml")
        assert out.name != "CON.mutated.yaml", (
            "保留裝置名 CON 未淨化——Windows 上 open() 必 OSError 且被 except 吞掉"
        )
        assert out.name == f"{_sanitize_log_filename('CON')}.mutated.yaml", (
            "淨化必須委派 SSOT _sanitize_log_filename（與 R47/R48 兩個 sibling 等價）"
        )

    def test_mutated_path_sanitizes_forbidden_chars_and_roundtrips(self, tmp_path):
        """禁用字元 / 尾隨空白經淨化後，persist→load→cleanup 三路檔名仍一致。

        三路都經同一支 _mutated_path_for()，故此鎖同時保證不會出現「寫入檔名 A、
        讀取檔名 B」的分歧（正是 DEF-101-390 當年在 sibling 上修掉的病灶）。
        """
        from autoclaude.utils.logger import _WIN_FORBIDDEN_CHARS

        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        raw = "some/dir/my<proj|v2 .yaml"
        out = p.persist_mutated_playbook(sample_playbook(), raw)
        assert out is not None and out.exists()
        for ch in _WIN_FORBIDDEN_CHARS:
            assert ch not in out.name, f"禁用字元 {ch!r} 洩漏進 .mutated.yaml 檔名 {out.name!r}"
        assert p.load_mutated_if_exists(raw) == out, "load 算出的路徑必須與 persist 落地一致"
        assert p.cleanup_mutated_for_paths([raw]) == [out], "cleanup 必須能命中同一檔案"
        assert not out.exists()

    def test_persist_failure_returns_none(self, tmp_path, caplog):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        # 模擬 yaml.dump 例外
        with patch(
            "autoclaude.plugins.playbook_persistence_plugin.yaml.dump",
            side_effect=RuntimeError("disk full"),
        ):
            with caplog.at_level(logging.WARNING):
                out = p.persist_mutated_playbook(sample_playbook(), "origin.yaml")
        assert out is None
        assert any("突變持久化失敗" in r.message for r in caplog.records)


class TestLoadMutated:
    def test_returns_none_when_file_missing(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        assert p.load_mutated_if_exists("origin.yaml") is None

    def test_returns_path_when_present_and_checkpoint_exists(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        mutated_path = tmp_path / "origin.mutated.yaml"
        mutated_path.write_text("dummy: x\n", encoding="utf-8")
        result = p.load_mutated_if_exists("origin.yaml", checkpoint_exists=True)
        assert result == mutated_path

    def test_returns_none_when_checkpoint_missing_even_if_file_exists(self, tmp_path):
        # 防呆：避免誤用過期突變狀態
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        (tmp_path / "origin.mutated.yaml").write_text("x: 1", encoding="utf-8")
        result = p.load_mutated_if_exists("origin.yaml", checkpoint_exists=False)
        assert result is None

    def test_resolves_stem_correctly_from_full_path(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        target = tmp_path / "playbook_a.mutated.yaml"
        target.write_text("x: 1", encoding="utf-8")
        # 任意目錄 + 同 stem 即可命中
        assert p.load_mutated_if_exists("any/where/playbook_a.yaml") == target


class TestCleanupMutated:
    def test_removes_existing_files(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        f1 = tmp_path / "a.mutated.yaml"
        f2 = tmp_path / "b.mutated.yaml"
        f1.write_text("x", encoding="utf-8")
        f2.write_text("y", encoding="utf-8")
        removed = p.cleanup_mutated_for_paths(["a.yaml", "b.yaml"])
        assert set(removed) == {f1, f2}
        assert not f1.exists()
        assert not f2.exists()

    def test_skips_nonexistent_paths(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        removed = p.cleanup_mutated_for_paths(["never.yaml", "ghost.yaml"])
        assert removed == []

    def test_skips_empty_and_none_paths(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        removed = p.cleanup_mutated_for_paths(["", None])  # type: ignore[list-item]
        assert removed == []

    def test_oserror_during_unlink_is_silent(self, tmp_path, caplog):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        f = tmp_path / "locked.mutated.yaml"
        f.write_text("x", encoding="utf-8")
        with patch.object(Path, "unlink", side_effect=OSError("locked")):
            removed = p.cleanup_mutated_for_paths(["locked.yaml"])
        assert removed == []  # 無法移除，回傳空清單
        # OSError 走 logger.debug，不會出現在 WARNING 等級
        assert all(r.levelno != logging.WARNING for r in caplog.records)


class TestRoundTrip:
    def test_persist_then_load(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        pb = sample_playbook()
        persisted = p.persist_mutated_playbook(pb, "test.yaml")
        assert persisted is not None
        loaded = p.load_mutated_if_exists("test.yaml", checkpoint_exists=True)
        assert loaded == persisted

    def test_persist_then_cleanup(self, tmp_path):
        p = PlaybookPersistencePlugin(checkpoint_dir=str(tmp_path))
        persisted = p.persist_mutated_playbook(sample_playbook(), "test.yaml")
        assert persisted and persisted.exists()
        removed = p.cleanup_mutated_for_paths(["test.yaml"])
        assert removed == [persisted]
        assert not persisted.exists()
