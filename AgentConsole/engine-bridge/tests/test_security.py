"""NFR-SEC-03／SEC-04：消毒鏈與外呼白名單（不需引擎、不需 DB）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.security import (
    DENY_CHARS,
    AuditLog,
    check_outbound_url,
    check_path,
    forbidden_chars,
    ignored_managed_keys,
    is_within,
    validate_config_overrides,
    validate_env,
    validate_playbook,
)

ALLOW = ("api.minimax.io", "localhost", "127.0.0.1")


class TestDenyCharsParity:
    """Bridge 自帶的黑名單字面必須等於 AutoClaude 引擎實際使用的那一組（任一邊漂移即紅）。"""

    def test_equals_the_shared_constant_the_engine_defines(self) -> None:
        from autoclaude.utils.shell_deny_chars import BASE_DENY_CHARS

        assert DENY_CHARS == BASE_DENY_CHARS

    def test_equals_the_constant_inside_the_adapter_source(self) -> None:
        from autoclaude.infra.adapters import sdd_to_playbook_adapter as adapter

        assert DENY_CHARS == adapter._DENY
        assert DENY_CHARS == frozenset("!`><~$&;"), "PRD §0.3 逐字列的八個字元"

    @pytest.mark.parametrize("ch", sorted(DENY_CHARS))
    def test_the_adapter_really_rejects_each_char_we_reject(self, ch: str) -> None:
        # 行為對照：不只常數相等，adapter 的 _sanitize 對每個字元也真的拒絕。
        from autoclaude.core.ports.spec_source import SpecTaintedError
        from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter

        with pytest.raises(SpecTaintedError):
            SddToPlaybookAdapter()._sanitize(f"a{ch}b")

    def test_newline_is_an_extra_rule_beyond_the_adapter_set(self) -> None:
        assert forbidden_chars("pytest -q\nrm -rf /") == ["\\n"]
        assert forbidden_chars("ok pytest tests -k foo -q") == []

    def test_forbidden_chars_reports_each_char_once_sorted(self) -> None:
        assert forbidden_chars("a;b;$(c)`d`") == ["$", ";", "`"]


class TestPlaybookGate:
    @staticmethod
    def _pb(**task_fields) -> SimpleNamespace:
        task = SimpleNamespace(step_id="T01", evaluator_command=None, command=None,
                               expected_output_regex=None)
        for k, v in task_fields.items():
            setattr(task, k, v)
        return SimpleNamespace(tasks=[task])

    @pytest.mark.parametrize("cmd", ["pytest -q; rm -rf /", "pytest $(whoami)", "pytest `id`",
                                     "pytest > out", "a && b", "pytest ~", "echo !x", "a\nb"])
    def test_dangerous_evaluator_command_is_listed(self, cmd: str) -> None:
        violations = validate_playbook(self._pb(evaluator_command=cmd))
        assert len(violations) == 1
        assert violations[0]["rule"] == "deny_chars"
        assert violations[0]["step_id"] == "T01"
        assert violations[0]["field"] == "playbook.tasks[0].evaluator_command"

    def test_clean_command_passes(self) -> None:
        assert validate_playbook(self._pb(evaluator_command='pytest tests -k "AT_001" -q')) == []

    def test_invalid_regex_is_a_violation(self) -> None:
        violations = validate_playbook(self._pb(expected_output_regex="(unclosed"))
        assert [v["rule"] for v in violations] == ["invalid_regex"]

    def test_the_mock_command_field_is_screened_too(self) -> None:
        violations = validate_playbook(self._pb(command="step1; rm"))
        assert violations[0]["field"] == "playbook.tasks[0].command"


class TestPathGate:
    def test_a_directory_under_the_root_is_accepted_and_realpathed(self, tmp_path: Path) -> None:
        proj = tmp_path / "proj"
        proj.mkdir()
        resolved, violations = check_path(str(proj), [tmp_path], field="execution_path")
        assert violations == []
        assert resolved == proj.resolve()

    def test_relative_path_is_rejected(self, tmp_path: Path) -> None:
        _, v = check_path("proj", [tmp_path], field="execution_path")
        assert v[0]["rule"] == "not_absolute"

    def test_dotdot_escape_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        (root / "sub").mkdir(parents=True)
        escape = f"{root}{os.sep}sub{os.sep}..{os.sep}..{os.sep}"
        _, v = check_path(escape, [root], field="execution_path")
        assert v[0]["rule"] == "contains_dotdot"

    def test_a_sibling_directory_outside_the_root_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        other = tmp_path / "rootx"            # 前綴相同但不是子目錄：字串 startswith 會誤放行
        root.mkdir()
        other.mkdir()
        _, v = check_path(str(other), [root], field="execution_path")
        assert v[0]["rule"] == "outside_allowed_roots"

    def test_missing_path_and_files_are_rejected(self, tmp_path: Path) -> None:
        _, v = check_path(str(tmp_path / "nope"), [tmp_path], field="execution_path")
        assert v[0]["rule"] == "not_found"
        f = tmp_path / "a.txt"
        f.write_text("x", encoding="utf-8")
        _, v = check_path(str(f), [tmp_path], field="execution_path")
        assert v[0]["rule"] == "not_a_directory"

    def test_symlink_escape_is_rejected_after_realpath(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        outside = tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        link = root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
        _, v = check_path(str(link), [root], field="execution_path")
        assert v[0]["rule"] == "outside_allowed_roots"

    def test_case_sensitivity_follows_the_platform_convention(self, tmp_path: Path) -> None:
        upper, lower = Path(str(tmp_path).upper()), Path(str(tmp_path).lower())
        if sys.platform == "win32":
            # Windows 行為＝路徑不分大小寫（normcase 轉小寫），大小寫不同仍視為同一處。
            assert is_within(upper, lower)
        else:
            # POSIX 行為＝區分大小寫；不確定時判為「不在其下」＝安全方向（拒絕）。
            assert not is_within(upper, lower)

    def test_is_within_does_not_confuse_prefix_siblings(self, tmp_path: Path) -> None:
        (tmp_path / "ab").mkdir()
        (tmp_path / "abc").mkdir()
        assert is_within(tmp_path / "ab", tmp_path / "ab")
        assert not is_within(tmp_path / "abc", tmp_path / "ab")


class TestOutboundAllowlist:
    @pytest.mark.parametrize("url", [
        "https://api.minimax.io/v1/text/chatcompletion_v2",
        "http://localhost:9100/v1/chat/completions",
        "http://127.0.0.1:9100/",
        "https://API.MINIMAX.IO./v1",
    ])
    def test_allowed_hosts_pass(self, url: str) -> None:
        ok, host, reason = check_outbound_url(url, ALLOW)
        assert ok, (host, reason)

    @pytest.mark.parametrize(("url", "reason"), [
        ("http://evil.example", "host_not_allowed"),
        ("http://localhost.evil.example/", "host_not_allowed"),
        ("http://evil.example/http://localhost/", "host_not_allowed"),
        ("http://api.minimax.io@evil.example/", "userinfo_not_allowed"),
        ("http://evil.example\\@localhost/", "malformed_url"),
        ("http://localhost\\.evil.example/", "malformed_url"),
        ("http://local host/", "malformed_url"),
        ("http://localhost%00.evil.example/", "host_not_allowed"),
        ("http://2130706433/", "host_not_allowed"),           # 127.0.0.1 的十進位寫法
        ("http://0x7f.0.0.1/", "host_not_allowed"),
        ("ftp://localhost/", "scheme_not_allowed"),
        ("file:///etc/passwd", "scheme_not_allowed"),
        ("//evil.example/", "scheme_not_allowed"),
        ("http://localhost:notaport/", "malformed_url"),
        ("", "empty_url"),
    ])
    def test_bypass_attempts_are_denied(self, url: str, reason: str) -> None:
        ok, _host, got = check_outbound_url(url, ALLOW)
        assert not ok
        assert got == reason

    @pytest.mark.parametrize("url", [
        "http://\uff4cocalhost/",                      # 全形 l：urllib 與 httpx 對 host 的認定不同
        "http://evil.example#@localhost/",
        "http://evil.example?@localhost/",
        "http://evil.example:80\\@localhost/",
    ])
    def test_parser_differentials_never_reach_an_allowed_host(self, url: str) -> None:
        assert check_outbound_url(url, ALLOW)[0] is False

    def test_non_string_is_denied(self) -> None:
        assert check_outbound_url(None, ALLOW)[0] is False
        assert check_outbound_url(123, ALLOW)[0] is False


class TestConfigOverrides:
    def test_empty_and_plain_values_pass(self) -> None:
        assert validate_config_overrides({}, ALLOW) == []
        ok = {"claude": {"command": "/x/aisdlc-mock-claude"},
              "playbook": {"step_timeout_seconds": 5},
              "token_guard": {"auto_resume": False}}
        assert validate_config_overrides(ok, ALLOW) == []

    def test_evil_base_url_is_denied_and_audited(self, tmp_path: Path) -> None:
        audit = AuditLog(tmp_path / "audit.jsonl")
        v = validate_config_overrides(
            {"minimax": {"base_url": "http://evil.example/v1"}}, ALLOW, audit=audit,
            context={"run_id": "r1"})
        assert [x["rule"] for x in v] == ["outbound_not_allowed"]
        assert v[0]["field"] == "config_overrides.minimax.base_url"
        line = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip()
        assert "outbound_denied" in line
        assert "evil.example" in line
        assert "/v1" not in line, "審計只記 host，不記整條 URL（可能夾帶憑證）"

    def test_localhost_mock_brain_is_allowed(self) -> None:
        assert validate_config_overrides(
            {"minimax": {"base_url": "http://localhost:9100/v1/chat/completions"}}, ALLOW) == []

    @pytest.mark.parametrize("section", ["embedder", "notification"])
    def test_other_outbound_urls_are_screened(self, section: str) -> None:
        key = {"embedder": "bge_m3_url", "notification": "webhook_url"}[section]
        v = validate_config_overrides({section: {key: "http://evil.example/"}}, ALLOW)
        assert v and v[0]["rule"] == "outbound_not_allowed"

    def test_bridge_managed_keys_are_valid_but_reported_as_ignored(self) -> None:
        # console-api 的 ConfigMaterializer 會依系統參數帶 storage.*：回 422 會讓所有 run 起不來。
        managed = {"checkpoint_dir": "/x", "log_dir": "/y", "backup_dir": "/z", "scripts_dir": "/s",
                   "workflow_search_paths": ["/w"],
                   "storage": {"mode": "both", "dual_read_resolution": "db_wins"}}
        assert validate_config_overrides(managed, ALLOW) == []
        assert ignored_managed_keys(managed) == [
            "backup_dir", "checkpoint_dir", "log_dir", "scripts_dir", "workflow_search_paths",
            "storage"]
        assert ignored_managed_keys({"storage": {"mode": "yaml_only"}}) == []
        assert ignored_managed_keys({"storage": {}}) == []
        assert ignored_managed_keys({"claude": {"command": "x"}}) == []

    def test_a_storage_section_still_gets_its_structure_and_secrets_checked(self) -> None:
        typo = validate_config_overrides({"storage": {"modee": "both"}}, ALLOW)
        assert typo[0]["rule"] == "unknown_key"
        dsn = validate_config_overrides({"storage": {"db_dsn": "postgresql://u:p@h/db"}}, ALLOW)
        assert [v["rule"] for v in dsn] == ["secret_in_config"]

    def test_secrets_must_come_through_env_not_config(self) -> None:
        v = validate_config_overrides({"minimax": {"api_key": "sk-secret"}}, ALLOW)
        assert [x["rule"] for x in v] == ["secret_in_config"]

    def test_unknown_keys_are_loud_not_silently_dropped(self) -> None:
        v = validate_config_overrides({"claude": {"comand": "x"}}, ALLOW)
        assert v[0]["rule"] == "unknown_key"
        assert validate_config_overrides({"nonsense": {}}, ALLOW)[0]["rule"] == "unknown_key"

    def test_engine_invariants_are_enforced_through_its_own_model(self) -> None:
        v = validate_config_overrides(
            {"token_guard": {"compact_threshold_pct": 90, "halt_threshold_pct": 80}}, ALLOW)
        assert v and v[0]["rule"] == "invalid_value"

    def test_tool_invocation_hosts_must_also_be_allowlisted(self) -> None:
        bad = {"tool_invocation": {"enabled": True, "allowlist": ["evil.example", "send_message"]}}
        v = validate_config_overrides(bad, ALLOW)
        assert v and v[0]["rule"] == "outbound_not_allowed"
        good = {"tool_invocation": {"enabled": True, "allowlist": ["localhost", "send_message"]}}
        assert validate_config_overrides(good, ALLOW) == []


class TestEnvGate:
    def test_plain_env_passes(self) -> None:
        assert validate_env({"MINIMAX_API_KEY": "k", "MOCK_CLAUDE_DELAY": "0.1"}, ALLOW) == []

    @pytest.mark.parametrize("name", ["PATH", "PYTHONPATH", "LD_PRELOAD", "NODE_OPTIONS", "path"])
    def test_loader_injection_names_are_refused(self, name: str) -> None:
        assert validate_env({name: "x"}, ALLOW)[0]["rule"] == "forbidden_name"

    def test_bad_names_and_values_are_refused(self) -> None:
        assert validate_env({"A=B": "x"}, ALLOW)[0]["rule"] == "invalid_name"
        assert validate_env({"A": "x\x00y"}, ALLOW)[0]["rule"] == "invalid_value"

    def test_env_url_that_the_engine_prefers_over_config_is_screened(self) -> None:
        # 引擎 main.py：env MINIMAX_BASE_URL 優先於 config——只擋 config 會被 env 繞過。
        v = validate_env({"MINIMAX_BASE_URL": "http://evil.example/"}, ALLOW)
        assert v[0]["rule"] == "outbound_not_allowed"


def test_audit_log_survives_unwritable_path(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    AuditLog(blocker / "sub" / "audit.jsonl").record("x", a=1)    # 不得拋例外
