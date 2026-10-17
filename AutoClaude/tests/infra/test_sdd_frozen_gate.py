"""improving_115（ADR-XPLAT-016 §6／§7.1）：_sdd_frozen_gate 純函式單測。

這支測試守的是兩個結構性 fail-open：
  1. 選檔——舊版取字母序第一份 FSM-STATE，他專案已凍結即可放行未凍結的專案（G-02／S-05）；
  2. 摘要——舊版只驗「有凍結」，不驗「凍結的就是這份」（G-06）。
每個案例的 WHY 寫在 docstring：拿掉對應修法，該案例必須變紅（反向對照）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from autoclaude.core.ports.spec_source import SpecDigestMismatchError, SpecNotFrozenError
from autoclaude.infra.adapters import _sdd_frozen_gate as gate

_AUTOCLAUDE_DIR = Path(__file__).resolve().parents[2]


def _state(fsm_dir: Path, key: str, *, project: str | None = None,
           current: str = "IMPLEMENTATION", stages: list | None = None) -> Path:
    fsm_dir.mkdir(parents=True, exist_ok=True)
    doc = {"fsm_state": {"project": key if project is None else project,
                         "current_state": current, "frozen_stages": stages or []}}
    path = fsm_dir / f"FSM-STATE-{key}.yaml"
    path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return path


def _fsm_dir(root: Path) -> Path:
    return root / "build" / "reports" / "fsm"


class TestResolveProjectKey:
    """建構子 fsm_project 的三態語意（None 讀環境／空字串不讀環境／其餘照用）。"""

    def test_none_reads_the_environment(self, monkeypatch):
        monkeypatch.setenv(gate.SDD_PROJECT_ENV, "  alpha ")
        assert gate.resolve_project_key(None) == "alpha"

    def test_empty_string_means_explicitly_no_key_and_never_reads_the_environment(
            self, monkeypatch):
        """Bridge 行程內一律顯式傳值：開發機匯出 SDD_PROJECT 是常態，不得左右 Bridge 的選檔。"""
        monkeypatch.setenv(gate.SDD_PROJECT_ENV, "alpha")
        assert gate.resolve_project_key("") == ""

    def test_an_explicit_value_wins_over_the_environment(self, monkeypatch):
        monkeypatch.setenv(gate.SDD_PROJECT_ENV, "alpha")
        assert gate.resolve_project_key("zeta") == "zeta"

    def test_blank_values_are_no_key(self, monkeypatch):
        monkeypatch.setenv(gate.SDD_PROJECT_ENV, "   ")
        assert gate.resolve_project_key(None) == ""
        assert gate.resolve_project_key("  ") == ""

    def test_unset_environment_is_no_key(self):
        assert gate.resolve_project_key(None) == ""


class TestFindFsmState:
    def test_single_state_file_without_a_key_is_used(self, tmp_path):
        only = _state(_fsm_dir(tmp_path), "demo")
        assert gate.find_fsm_state(tmp_path / "docs") == only

    def test_several_state_files_without_a_key_fail_closed(self, tmp_path):
        """框架自己的狀態目錄現有 8 個檔：不指定專案就不能通過凍結閘（刻意），不依字母序猜。"""
        _state(_fsm_dir(tmp_path), "alpha", current="SPEC_FROZEN")
        _state(_fsm_dir(tmp_path), "zeta", current="INIT")
        with pytest.raises(SpecNotFrozenError, match="不唯一") as info:
            gate.find_fsm_state(tmp_path / "docs")
        assert "alpha" in str(info.value) and "zeta" in str(info.value)  # 列出現有專案鍵供對照

    def test_the_named_project_is_the_only_one_that_counts(self, tmp_path):
        _state(_fsm_dir(tmp_path), "alpha", current="SPEC_FROZEN")
        zeta = _state(_fsm_dir(tmp_path), "zeta", current="INIT")
        assert gate.find_fsm_state(tmp_path, project_key="zeta") == zeta

    def test_a_missing_project_is_not_searched_for_in_parent_directories(self, tmp_path):
        """往上找會撞到別的專案：最近的 build/reports/fsm 沒有該專案就拒絕，不再往上。"""
        _state(_fsm_dir(tmp_path), "alpha", current="SPEC_FROZEN")  # 外層：有 alpha
        inner = tmp_path / "inner"
        _state(_fsm_dir(inner), "zeta", current="INIT")              # 內層：只有 zeta
        with pytest.raises(SpecNotFrozenError, match="找不到專案 'alpha'.*zeta"):
            gate.find_fsm_state(inner / "docs", project_key="alpha")

    def test_an_unnamed_search_still_walks_up_past_directories_without_state_files(
            self, tmp_path):
        only = _state(_fsm_dir(tmp_path), "demo")
        (tmp_path / "inner" / "build" / "reports" / "fsm").mkdir(parents=True)  # 空目錄
        assert gate.find_fsm_state(tmp_path / "inner" / "docs") == only

    def test_the_original_name_resolves_through_the_project_field(self, tmp_path):
        """鍵是未淨化的原名（含 ':'）時檔名幹是淨化後的字串：以檔內 project 欄位反查。"""
        _state(_fsm_dir(tmp_path), "other")
        wanted = _state(_fsm_dir(tmp_path), "a_b", project="a:b")
        assert gate.find_fsm_state(tmp_path, project_key="a:b") == wanted

    def test_the_project_field_lookup_must_be_unique(self, tmp_path):
        _state(_fsm_dir(tmp_path), "a_b", project="a:b")
        _state(_fsm_dir(tmp_path), "a_b-track2", project="a:b")  # 同專案的另一軌
        with pytest.raises(SpecNotFrozenError, match="找不到專案"):
            gate.find_fsm_state(tmp_path, project_key="a:b")

    @pytest.mark.parametrize("key", [
        pytest.param("a/b", id="forward-slash"),
        pytest.param("a\\b", id="backslash"),
        pytest.param("..", id="dotdot"),
        pytest.param(".", id="dot"),
        pytest.param("a\x00b", id="nul"),
        pytest.param("a\nb", id="newline"),
        pytest.param("a\x7fb", id="del"),
        pytest.param("..\\evil", id="dotdot-backslash"),
        pytest.param("../evil", id="dotdot-slash"),
    ])
    def test_illegal_project_keys_are_rejected(self, tmp_path, key):
        """防路徑穿越：分隔符、NUL／控制字元、`.`／`..` 一律不得拿來組檔名。"""
        _state(_fsm_dir(tmp_path), "demo")
        with pytest.raises(SpecNotFrozenError, match="非法"):
            gate.find_fsm_state(tmp_path, project_key=key)

    def test_an_explicit_state_path_is_the_highest_priority_and_ignores_the_key(
            self, tmp_path):
        explicit = _state(tmp_path / "elsewhere", "chosen")
        _state(_fsm_dir(tmp_path), "demo")
        assert gate.find_fsm_state(
            tmp_path, explicit_path=str(explicit), project_key="whatever") == explicit

    def test_a_missing_explicit_state_path_yields_none(self, tmp_path):
        _state(_fsm_dir(tmp_path), "demo")
        assert gate.find_fsm_state(
            tmp_path, explicit_path=str(tmp_path / "nope.yaml")) is None

    def test_no_state_directory_anywhere_yields_none(self, tmp_path):
        assert gate.find_fsm_state(tmp_path / "docs") is None

    def test_state_key_is_the_file_name_stem(self):
        assert gate.state_key(Path("x/FSM-STATE-訂單系統.yaml")) == "訂單系統"
        assert gate.state_key(Path("x/notes.yaml")) == "notes"


class TestReadFrozenStages:
    @pytest.mark.parametrize("current", sorted(gate.POST_FROZEN_STATES))
    def test_post_frozen_states_count_as_frozen_even_without_frozen_stages(
            self, tmp_path, current):
        path = _state(_fsm_dir(tmp_path), "demo", current=current)
        assert gate.read_frozen_stages(path) == []

    def test_autoclaude_delegated_is_a_post_frozen_state(self):
        """Bridge 在 spawn 前已 delegate-enter：引擎 PRE_RUN 讀到的 current_state 就是它。
        舊狀態檔 frozen_stages 為空時，缺這一項會讓委派一啟動就被 veto。"""
        assert "AUTOCLAUDE_DELEGATED" in gate.POST_FROZEN_STATES

    @pytest.mark.parametrize("current", ["INIT", "SPEC_DRAFTING", "HUMAN_PENDING", "ESCALATION"])
    def test_pre_frozen_states_without_frozen_stages_are_rejected(self, tmp_path, current):
        path = _state(_fsm_dir(tmp_path), "demo", current=current)
        with pytest.raises(SpecNotFrozenError, match=current):
            gate.read_frozen_stages(path)

    def test_non_empty_frozen_stages_win_over_the_current_state(self, tmp_path):
        path = _state(_fsm_dir(tmp_path), "demo", current="SPEC_DRAFTING",
                      stages=[{"stage": "SCG-0"}])
        assert gate.read_frozen_stages(path) == [{"stage": "SCG-0"}]

    def test_unreadable_state_files_fail_closed_with_the_gate_exception(self, tmp_path):
        """壞 YAML 不得丟出與凍結無關的例外（呼叫端各自 catch 才會漏）：一律當無法判定。"""
        bad = _fsm_dir(tmp_path) / "FSM-STATE-bad.yaml"
        bad.parent.mkdir(parents=True)
        bad.write_text("fsm_state: [unclosed\n  - x: : :", encoding="utf-8")
        with pytest.raises(SpecNotFrozenError, match="讀不出來"):
            gate.read_frozen_stages(bad)

    def test_a_file_that_is_not_a_mapping_is_not_frozen(self, tmp_path):
        odd = _fsm_dir(tmp_path) / "FSM-STATE-odd.yaml"
        odd.parent.mkdir(parents=True)
        odd.write_text("- just\n- a list\n", encoding="utf-8")
        with pytest.raises(SpecNotFrozenError):
            gate.read_frozen_stages(odd)


_D1 = "sha256:" + "1" * 64
_D2 = "sha256:" + "2" * 64
_D3 = "sha256:" + "3" * 64


def _spec(root: Path, rel: str = "docs/03_testing/contracts/TCS-Demo.md") -> Path:
    path = root / Path(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    return path


class TestCheckDigest:
    """ADR §6.2 判定表四列＋聯集後者勝＋尾段比對。"""

    KEY = "docs/03_testing/contracts/TCS-Demo.md"

    def test_no_digest_in_any_stage_is_absent_and_allowed(self, tmp_path):
        spec = _spec(tmp_path)
        assert gate.check_digest([], spec, _D1) == "absent"
        assert gate.check_digest([{"stage": "S"}, {"stage": "T", "spec_doc_digests": {}}],
                                 spec, _D1) == "absent"

    def test_a_matching_digest_is_verified(self, tmp_path):
        spec = _spec(tmp_path)
        assert gate.check_digest(
            [{"spec_doc_digests": {self.KEY: _D1}}], spec, _D1) == "verified"

    def test_a_changed_file_is_a_digest_mismatch_and_still_a_not_frozen_error(self, tmp_path):
        """子類關係是契約：既有 `except SpecNotFrozenError`（plugin PRE_RUN veto、sdd_compile rc 2）
        自動 fail-closed；要區分的呼叫端先接子類。"""
        spec = _spec(tmp_path)
        with pytest.raises(SpecDigestMismatchError, match="與凍結時不同") as info:
            gate.check_digest([{"spec_doc_digests": {self.KEY: _D1}}], spec, _D2)
        assert isinstance(info.value, SpecNotFrozenError)

    def test_a_file_missing_from_the_frozen_list_is_not_a_digest_mismatch(self, tmp_path):
        """「根本不在清單」與「內容變了」是兩個原因：Bridge 分別回 422／409，不得混成同一個例外。"""
        spec = _spec(tmp_path, "docs/other/TCS-Other.md")
        with pytest.raises(SpecNotFrozenError, match="不在凍結清單") as info:
            gate.check_digest([{"spec_doc_digests": {self.KEY: _D1}}], spec, _D1)
        assert not isinstance(info.value, SpecDigestMismatchError)

    def test_the_union_of_all_stages_is_used_and_the_later_stage_wins(self, tmp_path):
        """同一鍵在多個階段出現＝以最近一次凍結為準；較早階段獨有的鍵仍然有效。"""
        spec = _spec(tmp_path)
        older = {"spec_doc_digests": {self.KEY: _D1, "docs/README.md": _D3}}
        newer = {"spec_doc_digests": {self.KEY: _D2}}
        assert gate.check_digest([older, newer], spec, _D2) == "verified"
        with pytest.raises(SpecDigestMismatchError):
            gate.check_digest([older, newer], spec, _D1)   # 舊摘要已被後一階段取代
        readme = _spec(tmp_path, "docs/README.md")
        assert gate.check_digest([older, newer], readme, _D3) == "verified"

    def test_the_tail_of_the_path_matches_so_the_project_root_may_differ(self, tmp_path):
        """鍵是相對專案根的 POSIX 路徑；Docker 與主機的絕對根不同，比對只看尾段。"""
        spec = _spec(tmp_path / "some" / "other" / "mount")
        assert gate.check_digest([{"spec_doc_digests": {self.KEY: _D1}}], spec, _D1) == "verified"

    def test_posix_relative_keys_match_on_every_platform(self, tmp_path):
        """🔴 Windows 的 normcase 會把 `/` 換成 `\\`：對 as_posix() 字串直接 normcase 的寫法
        會讓尾段比對恆不成立（ADR §6.1 原型第一版全數誤判「不在清單」）。本案例在 Windows 上
        是那個寫法的回歸鎖；POSIX 上本來就成立。"""
        spec = _spec(tmp_path, "a/b/c/TCS-Deep.md")
        assert gate.check_digest(
            [{"spec_doc_digests": {"a/b/c/TCS-Deep.md": _D1}}], spec, _D1) == "verified"
        assert gate.check_digest(
            [{"spec_doc_digests": {"b/c/TCS-Deep.md": _D1}}], spec, _D1) == "verified"

    def test_case_folding_follows_the_platform(self, tmp_path):
        """大小寫：Windows 折疊（檔案系統不分大小寫）、POSIX 不折疊——斷言跟著平台走，不 skip。"""
        spec = _spec(tmp_path, "docs/TCS-Case.md")
        stages = [{"spec_doc_digests": {"DOCS/tcs-case.md": _D1}}]
        folds = os.path.normcase("A") == "a"
        if folds:
            assert gate.check_digest(stages, spec, _D1) == "verified"
        else:
            with pytest.raises(SpecNotFrozenError, match="不在凍結清單"):
                gate.check_digest(stages, spec, _D1)

    def test_a_key_must_align_with_a_path_segment_boundary(self, tmp_path):
        """鍵 `x.md` 不得因為 `xx.md` 以它結尾而吻合：尾段比對要對齊分段（os.sep＋鍵）。"""
        spec = _spec(tmp_path, "docs/xx.md")
        with pytest.raises(SpecNotFrozenError, match="不在凍結清單"):
            gate.check_digest([{"spec_doc_digests": {"x.md": _D1}}], spec, _D1)

    def test_the_longest_matching_key_wins(self, tmp_path):
        spec = _spec(tmp_path, "docs/TCS-Same.md")
        digests = {"TCS-Same.md": _D1, "docs/TCS-Same.md": _D2}
        assert gate.check_digest([{"spec_doc_digests": digests}], spec, _D2) == "verified"
        with pytest.raises(SpecDigestMismatchError):
            gate.check_digest([{"spec_doc_digests": digests}], spec, _D1)

    def test_malformed_digest_maps_fail_closed(self, tmp_path):
        spec = _spec(tmp_path)
        with pytest.raises(SpecNotFrozenError, match="不是映射"):
            gate.check_digest([{"spec_doc_digests": [self.KEY]}], spec, _D1)

    def test_an_empty_key_never_matches_anything(self, tmp_path):
        spec = _spec(tmp_path)
        with pytest.raises(SpecNotFrozenError, match="不在凍結清單"):
            gate.check_digest([{"spec_doc_digests": {"": _D1}}], spec, _D1)


class TestSddProjectEnvIsHermeticInTests:
    """開發機殼層 export 的 `SDD_PROJECT` 不得影響測試結果（同 `_hermetic_*` 家族）。

    adapter 建構時讀 `SDD_PROJECT`；在 SDD session 的殼層（匯出它是常態）跑測試時，所有
    「單檔、無專案鍵」的凍結閘測試會改去找 `FSM-STATE-<那個專案>.yaml` 而紅，失敗訊息卻只說
    「找不到專案」、不提環境變數。探針＝本類第一支；下面兩支以子行程帶該變數各跑它一次：
    有 conftest 必須綠，`--noconftest` 對照組必須紅（否則探針對該變數失去敏感度、綠就是空洞的）。
    """

    _PROBE = ("tests/infra/test_sdd_frozen_gate.py::TestSddProjectEnvIsHermeticInTests::"
              "test_probe_the_variable_is_not_visible")

    def test_probe_the_variable_is_not_visible(self):
        assert gate.SDD_PROJECT_ENV not in os.environ

    def _run_probe(self, *extra):
        return subprocess.run(
            [sys.executable, "-m", "pytest", self._PROBE, "-q", "-p", "no:xdist",
             "-o", "addopts=", "-p", "no:cacheprovider", *extra],
            cwd=_AUTOCLAUDE_DIR, env={**os.environ, gate.SDD_PROJECT_ENV: "leaky-project"},
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )

    def test_the_variable_exported_by_the_caller_is_invisible_to_tests(self):
        result = self._run_probe()
        assert result.returncode == 0, result.stdout + result.stderr

    def test_control_without_conftest_the_variable_is_visible(self):
        result = self._run_probe("--noconftest")
        assert result.returncode != 0 and gate.SDD_PROJECT_ENV in result.stdout, (
            "探針對該變數不再敏感（或因別的原因紅）：上一條綠是空洞的\n"
            + result.stdout + result.stderr)
