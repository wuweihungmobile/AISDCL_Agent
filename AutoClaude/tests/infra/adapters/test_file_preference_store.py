"""FilePreferenceStore 單元測試（F-C1）。

驗證意圖：凍結計畫 Phase 1 驗收條件二「偏好可寫可讀」— 偏好必須跨實例
（重啟）存活且 scope 覆寫語意正確（playbook 覆寫 global）。
"""
from __future__ import annotations

from autoclaude.core.ports.preference_store import IPreferenceStore
from autoclaude.infra.adapters.file_preference_store import FilePreferenceStore


def _store(tmp_path) -> FilePreferenceStore:
    return FilePreferenceStore(str(tmp_path / "preferences.jsonl"))


class TestProtocolCompliance:
    def test_satisfies_ipreferencestore(self, tmp_path):
        assert isinstance(_store(tmp_path), IPreferenceStore)


class TestGetSetList:
    def test_set_then_get(self, tmp_path):
        s = _store(tmp_path)
        s.set("correction_strategy", "SPLIT_STEP first")
        assert s.get("correction_strategy") == "SPLIT_STEP first"

    def test_get_missing_returns_none(self, tmp_path):
        assert _store(tmp_path).get("nope") is None

    def test_last_wins_overwrite(self, tmp_path):
        s = _store(tmp_path)
        s.set("k", "v1")
        s.set("k", "v2")
        assert s.get("k") == "v2"

    def test_scope_isolation(self, tmp_path):
        s = _store(tmp_path)
        s.set("k", "global-v", scope="global")
        s.set("k", "pb-v", scope="playbook:MyProj")
        assert s.get("k", scope="global") == "global-v"
        assert s.get("k", scope="playbook:MyProj") == "pb-v"

    def test_list_merged_playbook_overrides_global(self, tmp_path):
        s = _store(tmp_path)
        s.set("k", "global-v")
        s.set("only_global", "g")
        s.set("k", "pb-v", scope="playbook:MyProj")
        merged = s.list()
        assert merged["k"] == "pb-v"
        assert merged["only_global"] == "g"

    def test_list_specific_scope(self, tmp_path):
        s = _store(tmp_path)
        s.set("a", "1", scope="global")
        s.set("b", "2", scope="playbook:X")
        assert s.list("playbook:X") == {"b": "2"}


class TestPersistenceAcrossRestart:
    def test_preferences_survive_restart(self, tmp_path):
        path = tmp_path / "preferences.jsonl"
        s1 = FilePreferenceStore(str(path))
        s1.set("report_format", "markdown")
        s1.set("report_format", "json")  # last-wins

        s2 = FilePreferenceStore(str(path))
        assert s2.get("report_format") == "json"

    def test_corrupted_file_starts_empty_without_raising(self, tmp_path):
        path = tmp_path / "preferences.jsonl"
        path.write_text("not-json\n", encoding="utf-8")
        assert FilePreferenceStore(str(path)).list() == {}


class TestRewriteCompact:
    """P1-6：>_MAX_LINES_BEFORE_COMPACT 觸發整檔去重重寫 —— 唯一會覆寫
    使用者偏好檔的路徑，寫壞 = 偏好全失，必須有測試守住。"""

    def test_rewrite_dedupes_and_preserves_data(self, tmp_path, monkeypatch):
        from autoclaude.infra.adapters import file_preference_store as mod

        monkeypatch.setattr(mod, "_MAX_LINES_BEFORE_COMPACT", 3)
        path = tmp_path / "preferences.jsonl"
        s = mod.FilePreferenceStore(str(path))
        for i in range(5):  # 同 key 重複寫，超過閾值觸發 _rewrite
            s.set("k", f"v{i}")
        s.set("other", "x")

        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        assert len(lines) <= 3  # 已 compact（cache 僅 2 鍵 + 可能 1 行新 append）

        s2 = mod.FilePreferenceStore(str(path))
        assert s2.get("k") == "v4"
        assert s2.get("other") == "x"
