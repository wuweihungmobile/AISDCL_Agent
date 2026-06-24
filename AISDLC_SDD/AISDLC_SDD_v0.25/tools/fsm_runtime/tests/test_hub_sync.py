# enforces (governance rules): R-9.12
"""ACT-030 Phase F M2 D-30.14: tests for Hub Sync Client + governance chain.

Covers:
  - Anonymizer (D-30.7) basic + allow-list behaviour
  - PII Scanner (D-30.6) L2 detection + Luhn refinement
  - Hub Sync Client (D-30.5) pull / push / dry-run / promote
  - Conflict Resolver (D-30.8) 3-way merge outcomes
  - FSM HUB_SYNC observation state (D-30.12) entry/exit
  - 20-fixture PII coverage (A-30.2)
  - Acceptance scenarios A-30.1 ~ A-30.5
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, List

import pytest
import yaml

from tools.fsm_runtime import (
    anonymizer as anon_mod,
    pii_scanner as scanner_mod,
    hub_merge as merge_mod,
    hub_sync as sync_mod,
    state_loader as state_loader_mod,
    transition_rules as tr_mod,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_PATH = (
    REPO_ROOT / "tools" / "fsm_runtime" / "tests" / "fixtures" / "pii_samples" / "fixtures.yaml"
)


@pytest.fixture
def anon_cfg():
    return anon_mod.load_rules()


@pytest.fixture
def fixtures():
    doc = yaml.safe_load(FIXTURES_PATH.read_text(encoding="utf-8"))
    return doc["samples"]


def _make_registry(tmp_path: Path, *, endpoints: List[Dict] | None = None) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    reg = tmp_path / "hub-registry.yaml"
    body = {
        "registry_version": "1.0",
        "sync_policy": {
            "pull": {
                "enabled": True,
                "cache_ttl_hours": 24,
                "auto_pull_on_session_start": True,
                "failure_mode": "non_blocking",
                "timeout_seconds": 5,
            },
            "push": {
                "enabled": False,
                "require_env_confirm": True,
                "require_pii_double_scan": True,
                "require_anonymize": True,
                "timeout_seconds": 10,
            },
        },
        "allowed_endpoints": endpoints or [],
        "deny_unlisted": True,
        "pull_cache": {
            "path": str(tmp_path / "cache"),
            "metadata": str(tmp_path / "cache" / "META.yaml"),
        },
        "push_audit_log": str(tmp_path / "PUSH-AUDIT.yaml"),
        "quarantine_dir": str(tmp_path / "hub_q"),
        "conflicts_dir": str(tmp_path / "CONFLICTS"),
        "rejected_log": str(tmp_path / "REJECTED-LOG.yaml"),
    }
    reg.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return reg


def _setup_local_hub(tmp_path: Path) -> Path:
    """Create a small file:// hub with two SLV rules."""
    hub_root = tmp_path / "hub_repo"
    rules_dir = hub_root / "rules"
    fpl_dir = hub_root / "failure-patterns"
    rules_dir.mkdir(parents=True)
    fpl_dir.mkdir(parents=True)
    (rules_dir / "SLV-100.yaml").write_text(
        yaml.safe_dump({
            "id": "SLV-100",
            "name": "remote-rule-one",
            "trust_level": "external",
            "scope": "SCG-0",
            "severity": "medium",
            "description": "remote rule pulled from hub",
        }, sort_keys=False),
        encoding="utf-8",
    )
    (rules_dir / "SLV-101.yaml").write_text(
        yaml.safe_dump({
            "id": "SLV-101",
            "name": "remote-rule-two",
            "trust_level": "external",
            "scope": "SCG-1",
            "severity": "low",
            "description": "second remote rule",
        }, sort_keys=False),
        encoding="utf-8",
    )
    (fpl_dir / "FPL-100.md").write_text("# FPL-100\nRemote failure pattern.\n", encoding="utf-8")
    return hub_root


# ─────────────────────────────────────────────
# Anonymizer (D-30.7)
# ─────────────────────────────────────────────
class TestAnonymizer:
    def test_loads_l1_rules(self, anon_cfg):
        assert len(anon_cfg.l1_rules) >= 5
        assert all(r.pattern is not None for r in anon_cfg.l1_rules)

    def test_replaces_project_codename(self, anon_cfg):
        out = anon_mod.anonymize("We migrated proj-foo last sprint.", config=anon_cfg)
        assert "proj-foo" not in out.text
        assert re.search(r"<PROJECT_[A-Z]+>", out.text)

    def test_allow_list_preserved(self, anon_cfg):
        out = anon_mod.anonymize("PostgreSQL with Redis cache.", config=anon_cfg)
        assert "PostgreSQL" in out.text
        assert "Redis" in out.text
        assert out.changed is False

    def test_substitution_log_redacted(self, anon_cfg):
        out = anon_mod.anonymize("issue #4521 closed.", config=anon_cfg)
        for sub in out.substitutions:
            # original_redacted must NOT contain the literal full original
            assert "#4521" not in sub.original_redacted

    def test_user_mention_does_not_match_email(self, anon_cfg):
        # email content stays untouched by anonymizer (PII Scanner handles it)
        out = anon_mod.anonymize("Contact john@example.org for details.", config=anon_cfg)
        assert "<USER_" not in out.text  # @example must NOT trigger user_handle


# ─────────────────────────────────────────────
# PII Scanner (D-30.6)
# ─────────────────────────────────────────────
class TestPIIScanner:
    def test_detects_email(self):
        result = scanner_mod.scan("Email me at alice@acme.com today.")
        assert any(h.rule_id == "L2.email_named" for h in result.hits)

    def test_detects_ipv4(self):
        result = scanner_mod.scan("Server at 10.0.0.1 unreachable.")
        assert any(h.rule_id == "L2.ipv4" for h in result.hits)

    def test_luhn_refines_credit_card(self):
        # 1234567890123456 is NOT Luhn-valid → must NOT match
        clean = scanner_mod.scan("Random number 1234567890123456 in logs.")
        assert not any(h.rule_id == "L2.credit_card" for h in clean.hits)
        # 4539148803436467 (Luhn-valid Visa test) MUST match
        dirty = scanner_mod.scan("Card 4539148803436467 in logs.")
        assert any(h.rule_id == "L2.credit_card" for h in dirty.hits)

    def test_quarantine_writes_yaml(self, tmp_path):
        artifact = tmp_path / "leak.md"
        artifact.write_text("Email alice@example.corp for keys.", encoding="utf-8")
        # NB: example.corp matches L2.internal_domain (`*.corp.<tld>`)
        result = scanner_mod.scan_artifact(
            artifact, quarantine_dir=tmp_path / "qdir"
        )
        assert not result.scan.clean
        assert result.quarantine_path is not None
        loaded = yaml.safe_load(result.quarantine_path.read_text(encoding="utf-8"))
        assert loaded["resolution_status"] == "pending"
        # raw text must NOT appear in quarantine YAML
        for hit in loaded["hit_patterns"]:
            assert "alice" not in hit["matched"]

    def test_clean_text_no_hits(self):
        result = scanner_mod.scan("Phase E SCG passed; FSM stable.")
        assert result.clean


# ─────────────────────────────────────────────
# 20-fixture coverage (A-30.2)
# ─────────────────────────────────────────────
class TestFixtureCoverage:
    def test_all_20_fixtures_exist(self, fixtures):
        ids = [s["id"] for s in fixtures]
        assert len(ids) == 20, f"expected 20 fixtures, got {len(ids)}"

    def test_l2_fixtures_caught_by_scanner(self, fixtures, tmp_path, monkeypatch):
        # Provide deny_list_customers for fixture 11 via a local rules file.
        rules_yaml = tmp_path / "rules.yaml"
        original = anon_mod.DEFAULT_RULES_PATH.read_text(encoding="utf-8")
        original_doc = yaml.safe_load(original)
        original_doc["deny_list_customers"] = ["ACME 公司"]
        rules_yaml.write_text(yaml.safe_dump(original_doc, sort_keys=False, allow_unicode=True), encoding="utf-8")

        rules_tuple, _ = scanner_mod.load_l2_rules(rules_yaml)
        for sample in fixtures:
            if not sample["expect_l2"]:
                continue
            res = scanner_mod.scan(sample["text"], rules=rules_tuple)
            hit_ids = {h.rule_id for h in res.hits}
            for expected in sample["expect_l2"]:
                assert expected in hit_ids, (
                    f"fixture {sample['id']}: expected {expected} hit but got {hit_ids}"
                )

    def test_l1_fixtures_get_placeholders(self, fixtures, anon_cfg):
        for sample in fixtures:
            if not sample["expect_l1"]:
                continue
            text = sample["text"]
            res = anon_mod.anonymize(text, config=anon_cfg)
            applied_ids = {s.rule_id for s in res.substitutions}
            for expected in sample["expect_l1"]:
                assert expected in applied_ids, (
                    f"fixture {sample['id']}: expected {expected} substitution; "
                    f"applied {applied_ids}; text={text!r}"
                )

    def test_clean_fixtures_unchanged(self, fixtures, anon_cfg):
        for sample in fixtures:
            if sample["expect_l1"] or sample["expect_l2"]:
                continue
            res_anon = anon_mod.anonymize(sample["text"], config=anon_cfg)
            res_scan = scanner_mod.scan(sample["text"])
            assert res_anon.changed is False, f"fixture {sample['id']} should not anonymize"
            assert res_scan.clean is True, f"fixture {sample['id']} should not scan-hit"


# ─────────────────────────────────────────────
# Hub Sync Client (D-30.5)
# ─────────────────────────────────────────────
class TestHubSyncClient:
    def test_a30_4_endpoint_allowlist(self, tmp_path):
        """A-30.4: non-allow-list endpoint must be rejected."""
        reg = _make_registry(tmp_path)  # empty allowed_endpoints
        client = sync_mod.HubSyncClient(reg)
        with pytest.raises(sync_mod.HubConfigError):
            client.pull("rogue-endpoint")

    def test_pull_from_local_file_endpoint(self, tmp_path):
        hub_root = _setup_local_hub(tmp_path)
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "local-test",
            "url": f"file://{hub_root}",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        result = client.pull("local-test")
        assert result.error is None
        assert any("SLV-100.yaml" in f for f in result.pulled_files)
        # second pull within ttl → cache_was_fresh
        again = client.pull("local-test")
        assert again.cache_was_fresh is True

    def test_pull_stamps_external_trust_level(self, tmp_path):
        """QA Round-2 P1 (G-30.4): pull MUST overwrite trust_level → external,
        even when upstream hub yaml declares verified/proposed. Protects against
        a misconfigured (or hostile) hub from slipping through advisory gating.
        """
        # Build a hub where rule yaml carries trust_level: verified — the
        # exact case that would bypass G-30.4 if pull() did not stamp.
        hub_root = tmp_path / "hub_with_verified_rules"
        rules_dir = hub_root / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "SLV-200.yaml").write_text(
            yaml.safe_dump({
                "id": "SLV-200",
                "name": "upstream-claims-verified",
                "trust_level": "verified",
                "scope": "SCG-0",
                "severity": "high",
                "description": "must be downgraded to external on pull",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (rules_dir / "SLV-201.yaml").write_text(
            yaml.safe_dump({
                "id": "SLV-201",
                "name": "upstream-claims-proposed",
                "trust_level": "proposed",
                "scope": "SCG-1",
                "severity": "low",
                "description": "must be downgraded to external on pull",
            }, sort_keys=False),
            encoding="utf-8",
        )
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "verified-test",
            "url": f"file://{hub_root}",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        result = client.pull("verified-test")
        assert result.error is None

        cache_root = result.cache_path
        for slv_id, original in [("SLV-200", "verified"), ("SLV-201", "proposed")]:
            cached = cache_root / "rules" / f"{slv_id}.yaml"
            assert cached.exists(), f"{slv_id} should be present in cache"
            doc = yaml.safe_load(cached.read_text(encoding="utf-8"))
            assert doc["trust_level"] == "external", (
                f"G-30.4 violated: {slv_id} cached at trust_level={doc['trust_level']!r}"
            )
            assert doc["hub_origin"]["original_trust_level"] == original
            assert doc["hub_origin"]["stamped_at"]

        # cache meta records how many files we stamped
        meta = client._read_cache_meta()
        assert meta["verified-test"]["trust_level_stamped"] == 2

    def test_pull_idempotent_for_already_external(self, tmp_path):
        """Already-external rules should pass through unchanged on second pull."""
        hub_root = _setup_local_hub(tmp_path)  # both rules are external
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "local-test",
            "url": f"file://{hub_root}",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        client.pull("local-test", force=True)
        cached = client._endpoint_cache_dir(client._resolve_endpoint("local-test"))
        for fname in ("SLV-100.yaml", "SLV-101.yaml"):
            doc = yaml.safe_load((cached / "rules" / fname).read_text(encoding="utf-8"))
            assert doc["trust_level"] == "external"
            # No stamp metadata should be added when already-external
            assert "hub_origin" not in doc

    def test_dry_run_never_writes(self, tmp_path):
        hub_root = _setup_local_hub(tmp_path)
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "local-test",
            "url": f"file://{hub_root}",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        artifact = tmp_path / "clean_rule.md"
        artifact.write_text("Phase E framework note; uses PostgreSQL.", encoding="utf-8")
        result = client.dry_run([artifact])
        assert result.all_clean is True
        assert all(it.would_push is False for it in result.items)
        # No outbox should be created
        assert not (tmp_path / "build" / "reports" / "hub" / "push-outbox").exists()

    def test_push_blocked_without_env_confirm(self, tmp_path, monkeypatch):
        hub_root = _setup_local_hub(tmp_path)
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "local-test",
            "url": f"file://{hub_root}",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        monkeypatch.delenv("SDD_HUB_PUSH_CONFIRMED", raising=False)
        artifact = tmp_path / "rule.md"
        artifact.write_text("Phase F framework lessons.", encoding="utf-8")
        res = client.push([artifact], endpoint_id="local-test")
        assert res.confirmed is False
        # All items would_push=False because force_dry=True (env not set)
        assert all(it.would_push is False for it in res.items)

    def test_push_pii_quarantines(self, tmp_path, monkeypatch):
        hub_root = _setup_local_hub(tmp_path)
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "local-test",
            "url": f"file://{hub_root}",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        artifact = tmp_path / "leaky.md"
        artifact.write_text(
            "Customer alice@acme.com hit the bug; rotate sk-ABCDE0123456789FGHIJ.",
            encoding="utf-8",
        )
        monkeypatch.setenv("SDD_HUB_PUSH_CONFIRMED", "test_push")
        with pytest.raises(sync_mod.HubPushBlocked):
            client.push([artifact], endpoint_id="local-test")
        # Quarantine YAML was written
        qdir = Path(client.registry["quarantine_dir"])
        files = list(qdir.glob("QUARANTINE-*.yaml"))
        assert len(files) >= 1

    def test_promote_external_to_verified(self, tmp_path):
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "local-test",
            "url": f"file://{tmp_path}/dummy",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        rule = tmp_path / "SLV-200.yaml"
        rule.write_text(yaml.safe_dump({
            "id": "SLV-200",
            "name": "to-be-promoted",
            "trust_level": "external",
            "scope": "SCG-0",
            "severity": "high",
            "description": "test rule for promotion",
        }, sort_keys=False), encoding="utf-8")
        result = client.promote(rule, reviewer="tester", notes="approved during M2 test")
        assert result.from_trust == "external"
        assert result.to_trust == "verified"
        loaded = yaml.safe_load(rule.read_text(encoding="utf-8"))
        assert loaded["trust_level"] == "verified"
        assert loaded["reviewed_by"] == "tester"
        assert loaded["reviewed_at"]
        assert loaded["review_history"][-1]["decision"] == "approve"

    def test_promote_refuses_non_external(self, tmp_path):
        reg = _make_registry(tmp_path, endpoints=[])
        client = sync_mod.HubSyncClient(reg)
        rule = tmp_path / "SLV-201.yaml"
        rule.write_text(yaml.safe_dump({
            "id": "SLV-201",
            "name": "already-verified",
            "trust_level": "verified",
            "scope": "SCG-0",
            "severity": "high",
            "description": "already verified",
            "reviewed_by": "someone",
            "reviewed_at": "2026-04-25T00:00:00+00:00",
        }, sort_keys=False), encoding="utf-8")
        with pytest.raises(ValueError):
            client.promote(rule, reviewer="other")


# ─────────────────────────────────────────────
# Conflict Resolver (D-30.8)
# ─────────────────────────────────────────────
class TestConflictResolver:
    @staticmethod
    def _write_rule(path: Path, body: dict) -> Path:
        path.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path

    def test_fast_forward_when_local_missing(self, tmp_path):
        remote = self._write_rule(tmp_path / "remote.yaml", {
            "id": "SLV-300", "name": "n", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "d",
        })
        report = merge_mod.detect_conflict(
            "SLV-300", local=None, base=None, remote=remote,
            conflicts_dir=tmp_path / "CONFLICTS",
        )
        assert report.outcome == merge_mod.MergeOutcome.BASE_MISSING_NEW_RULE

    def test_no_op_when_same_content(self, tmp_path):
        body = {
            "id": "SLV-301", "name": "n", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "d",
        }
        local = self._write_rule(tmp_path / "local.yaml", body)
        remote = self._write_rule(tmp_path / "remote.yaml", body)
        base = self._write_rule(tmp_path / "base.yaml", body)
        report = merge_mod.detect_conflict(
            "SLV-301", local=local, base=base, remote=remote,
            conflicts_dir=tmp_path / "CONFLICTS",
        )
        assert report.outcome == merge_mod.MergeOutcome.NO_OP

    def test_a30_3_verified_conflict_blocked(self, tmp_path):
        """A-30.3: local verified rule must NEVER be auto-overwritten."""
        local = self._write_rule(tmp_path / "local.yaml", {
            "id": "SLV-302", "name": "verified-rule", "trust_level": "verified",
            "scope": "SCG-0", "severity": "high", "description": "old",
            "reviewed_by": "user", "reviewed_at": "2026-04-25T00:00:00+00:00",
        })
        remote = self._write_rule(tmp_path / "remote.yaml", {
            "id": "SLV-302", "name": "verified-rule", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "new",
        })
        report = merge_mod.detect_conflict(
            "SLV-302", local=local, base=None, remote=remote,
            conflicts_dir=tmp_path / "CONFLICTS",
        )
        assert report.outcome == merge_mod.MergeOutcome.BLOCKED_VERIFIED
        assert report.written_path is not None and report.written_path.exists()

    def test_conflict_when_both_diverged(self, tmp_path):
        base = self._write_rule(tmp_path / "base.yaml", {
            "id": "SLV-303", "name": "n", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "base-text",
        })
        local = self._write_rule(tmp_path / "local.yaml", {
            "id": "SLV-303", "name": "n", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "local-edit",
        })
        remote = self._write_rule(tmp_path / "remote.yaml", {
            "id": "SLV-303", "name": "n", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "remote-edit",
        })
        report = merge_mod.detect_conflict(
            "SLV-303", local=local, base=base, remote=remote,
            conflicts_dir=tmp_path / "CONFLICTS",
        )
        assert report.outcome == merge_mod.MergeOutcome.CONFLICT
        assert report.written_path is not None and report.written_path.exists()


# ─────────────────────────────────────────────
# FSM HUB_SYNC observation state (D-30.12)
# ─────────────────────────────────────────────
class TestFSMHubSync:
    def test_hub_sync_in_observation_set(self):
        assert "HUB_SYNC" in tr_mod.OBSERVATION_STATES

    def test_transition_table_has_hub_sync(self):
        from tools.fsm_runtime.transition_rules import _HAPPY_PATH
        assert "HUB_SYNC" in _HAPPY_PATH
        # outbound set must include all legitimate resume targets + HUMAN_PENDING
        outbound = _HAPPY_PATH["HUB_SYNC"]
        assert "HUMAN_PENDING" in outbound
        assert "SPEC_DRAFTING" in outbound
        assert "RELEASE" in outbound

    def _bootstrap_runtime(self, tmp_path, monkeypatch, *, initial_state: str = "RELEASE"):
        # Use isolated state file for the test (load_state takes positional `path`).
        state_path = tmp_path / "FSM-STATE-test.yaml"
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        rt = FSMRuntime(state_loader_mod.load_state("test", state_path))
        rt.state.current = initial_state
        return rt

    def test_enter_hub_sync_from_release(self, tmp_path, monkeypatch):
        rt = self._bootstrap_runtime(tmp_path, monkeypatch, initial_state="RELEASE")
        result = rt.enter_hub_sync(direction="pull", endpoint="local-test")
        assert result["entered"] is True
        assert rt.state.current == "HUB_SYNC"
        tracking = rt.state.root.get("hub_sync_tracking", {})
        assert tracking["resume_state"] == "RELEASE"
        assert tracking["direction"] == "pull"

    def test_enter_hub_sync_blocks_from_escalation(self, tmp_path, monkeypatch):
        rt = self._bootstrap_runtime(tmp_path, monkeypatch, initial_state="ESCALATION")
        with pytest.raises(tr_mod.TransitionError):
            rt.enter_hub_sync(direction="pull")

    def test_exit_success_returns_to_resume_state(self, tmp_path, monkeypatch):
        rt = self._bootstrap_runtime(tmp_path, monkeypatch, initial_state="SPEC_DRAFTING")
        rt.enter_hub_sync(direction="pull")
        rt.exit_hub_sync("success")
        assert rt.state.current == "SPEC_DRAFTING"

    def test_exit_partial_routes_to_human_pending(self, tmp_path, monkeypatch):
        rt = self._bootstrap_runtime(tmp_path, monkeypatch, initial_state="SPEC_DRAFTING")
        rt.enter_hub_sync(direction="pull")
        rt.exit_hub_sync("partial")
        assert rt.state.current == "HUMAN_PENDING"

    def test_exit_failed_does_not_escalate(self, tmp_path, monkeypatch):
        rt = self._bootstrap_runtime(tmp_path, monkeypatch, initial_state="SPEC_FROZEN")
        rt.enter_hub_sync(direction="push")
        rt.exit_hub_sync("failed")
        assert rt.state.current == "SPEC_FROZEN"


# ─────────────────────────────────────────────
# A-30.1 / A-30.5 end-to-end
# ─────────────────────────────────────────────
class TestAcceptanceE2E:
    def test_a30_1_two_project_flow(self, tmp_path, monkeypatch):
        """A-30.1: A push 3 rules (1 with PII), B pull and review."""
        # === Project A: prepares 3 artifacts ===
        a_root = tmp_path / "project_a"
        a_root.mkdir()
        clean1 = a_root / "FPL-A.md"
        clean1.write_text("# FPL-A\nFailure pattern: temporal mismatch in proj-foo.\n", encoding="utf-8")
        clean2 = a_root / "FPL-B.md"
        clean2.write_text("# FPL-B\nUntestable AC pattern observed.\n", encoding="utf-8")
        leaky = a_root / "FPL-C.md"
        leaky.write_text(
            "# FPL-C\nLeaked alice@acme.com and key sk-AAAABBBBCCCCDDDDEEEEFFFF.\n",
            encoding="utf-8",
        )

        a_reg = _make_registry(tmp_path / "a", endpoints=[{
            "id": "shared-hub",
            "url": f"file://{tmp_path}/hub_repo",
            "protocol": "file",
        }])
        # Hub repo exists but starts empty.
        (tmp_path / "hub_repo" / "rules").mkdir(parents=True, exist_ok=True)
        (tmp_path / "hub_repo" / "failure-patterns").mkdir(parents=True, exist_ok=True)

        a_client = sync_mod.HubSyncClient(a_reg)
        monkeypatch.setenv("SDD_HUB_PUSH_CONFIRMED", "a30_1_e2e")

        # PII Scanner blocks the leaky one.
        with pytest.raises(sync_mod.HubPushBlocked):
            a_client.push([clean1, clean2, leaky], endpoint_id="shared-hub")
        # Push the two clean ones — should write outbox.
        res = a_client.push([clean1, clean2], endpoint_id="shared-hub")
        assert res.all_clean is True
        outbox = REPO_ROOT / "build" / "reports" / "hub" / "push-outbox" / "shared-hub"
        assert outbox.exists()
        assert (outbox / "FPL-A.md").exists()
        assert (outbox / "FPL-B.md").exists()

        # Simulate B pulling a SLV rule from the hub.
        rules_dir = tmp_path / "hub_repo" / "rules"
        (rules_dir / "SLV-X.yaml").write_text(yaml.safe_dump({
            "id": "SLV-X", "name": "x", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "from-A",
        }, sort_keys=False), encoding="utf-8")

        b_reg = _make_registry(tmp_path / "b", endpoints=[{
            "id": "shared-hub",
            "url": f"file://{tmp_path}/hub_repo",
            "protocol": "file",
        }])
        b_client = sync_mod.HubSyncClient(b_reg)
        pull_res = b_client.pull("shared-hub")
        assert pull_res.error is None
        assert any("SLV-X.yaml" in f for f in pull_res.pulled_files)
        # Ensure pulled rule retains trust_level=external.
        cached = pull_res.cache_path / "rules" / "SLV-X.yaml"
        loaded = yaml.safe_load(cached.read_text(encoding="utf-8"))
        assert loaded["trust_level"] == "external"

        # B copies & promotes locally.
        local_rule = tmp_path / "b" / "SLV-X.yaml"
        local_rule.write_text(cached.read_text(encoding="utf-8"), encoding="utf-8")
        b_client.promote(local_rule, reviewer="user-b", notes="e2e a30.1")
        verified = yaml.safe_load(local_rule.read_text(encoding="utf-8"))
        assert verified["trust_level"] == "verified"
        assert verified["reviewed_by"] == "user-b"

        # Cleanup outbox to avoid side-effects across tests
        shutil.rmtree(outbox, ignore_errors=True)

    def test_a30_5_failure_non_blocking(self, tmp_path, monkeypatch):
        """A-30.5: Hub failure (missing path) returns error but doesn't escalate."""
        reg = _make_registry(tmp_path, endpoints=[{
            "id": "broken-hub",
            "url": f"file://{tmp_path}/does_not_exist",
            "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        result = client.pull("broken-hub")
        # Non-blocking: error is reported but no exception raised
        assert result.error is not None
        assert result.cache_was_fresh is False
        # FSM is not auto-touched; check that the runtime entry/exit also
        # tolerates a failed-outcome exit gracefully.
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        rt = FSMRuntime(state_loader_mod.load_state("a30_5_test", tmp_path / "FSM-STATE-a30_5_test.yaml"))
        rt.state.current = "SPEC_DRAFTING"
        rt.enter_hub_sync(direction="pull")
        rt.exit_hub_sync("failed", reason="hub unreachable")
        assert rt.state.current == "SPEC_DRAFTING"
        # The runtime did NOT promote to ESCALATION.
        assert rt.state.current != "ESCALATION"


# ─────────────────────────────────────────────
# External/cached file size cap (DEF-CLDREV-030)
# ─────────────────────────────────────────────
def _make_registry_with_cap(
    tmp_path: Path, *, max_file_bytes: int, endpoints: List[Dict] | None = None
) -> Path:
    """Registry carrying sync_policy.pull.max_file_bytes (override path)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    reg = tmp_path / "hub-registry.yaml"
    body = {
        "registry_version": "1.0",
        "sync_policy": {
            "pull": {
                "enabled": True,
                "cache_ttl_hours": 24,
                "auto_pull_on_session_start": True,
                "failure_mode": "non_blocking",
                "timeout_seconds": 5,
                "max_file_bytes": max_file_bytes,
            },
            "push": {"enabled": False},
        },
        "deny_unlisted": True,
        "allowed_endpoints": endpoints or [],
        "pull_cache": {
            "path": "build/reports/hub/pull-cache",
            "metadata": "build/reports/hub/pull-cache/META.yaml",
        },
        "push_audit_log": "build/reports/hub/PUSH-AUDIT.yaml",
        "quarantine_dir": "build/reports/hub",
    }
    reg.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    return reg


def _oversize_rule_yaml(rule_id: str, *, trust_level: str, pad_bytes: int) -> str:
    """A *valid* YAML rule whose serialized size exceeds pad_bytes — so that the
    PRE-fix code path would happily safe_load + stamp it (proving the size cap,
    not a parse error, is what changes behaviour)."""
    return yaml.safe_dump({
        "id": rule_id,
        "name": "oversize-upstream-rule",
        "trust_level": trust_level,
        "scope": "SCG-0",
        "severity": "high",
        "description": "x" * pad_bytes,
    }, sort_keys=False)


class TestHubFileSizeCap:
    """DEF-CLDREV-030: bound memory when reading untrusted external/cached hub
    content before yaml.safe_load (oversized / billion-laughs DoS from a hostile
    or misconfigured hub). Trusted PR-gated registry + self-written accumulating
    audit ledger remain deliberately uncapped."""

    def test_default_max_file_bytes_constant(self):
        assert sync_mod.MAX_HUB_FILE_BYTES == 1024 * 1024  # 1 MiB

    def test_client_default_cap_from_constant(self, tmp_path):
        reg = _make_registry(tmp_path)  # no max_file_bytes key
        client = sync_mod.HubSyncClient(reg)
        assert client._max_file_bytes == sync_mod.MAX_HUB_FILE_BYTES

    def test_registry_overrides_max_file_bytes(self, tmp_path):
        reg = _make_registry_with_cap(tmp_path, max_file_bytes=4096)
        client = sync_mod.HubSyncClient(reg)
        assert client._max_file_bytes == 4096

    def test_invalid_cap_falls_back_to_default(self, tmp_path):
        reg = _make_registry_with_cap(tmp_path, max_file_bytes=-1)
        client = sync_mod.HubSyncClient(reg)
        # non-positive override is rejected → fall back to constant default
        assert client._max_file_bytes == sync_mod.MAX_HUB_FILE_BYTES

    def test_read_text_bounded_enforces_cap(self, tmp_path):
        reg = _make_registry_with_cap(tmp_path, max_file_bytes=1024)
        client = sync_mod.HubSyncClient(reg)
        small = tmp_path / "small.yaml"
        small.write_text("a: 1\n", encoding="utf-8")
        assert client._read_text_bounded(small) == "a: 1\n"  # under cap → returned
        big = tmp_path / "big.yaml"
        big.write_text("a: " + "x" * 2000 + "\n", encoding="utf-8")
        with pytest.raises(sync_mod.HubContentTooLarge):
            client._read_text_bounded(big)

    def test_pull_skips_oversize_external_yaml(self, tmp_path):
        """An oversized rule from the hub must NOT be safe_load'd/stamped (it is
        skipped fail-soft + audited); a normal-sized rule in the same hub is
        still stamped external. PRE-fix this oversize file would be loaded and
        stamped → trust_level 'external' + hub_origin (the assertions below fail
        on old code = Rule 9 can fail)."""
        hub_root = tmp_path / "hostile_hub"
        rules_dir = hub_root / "rules"
        rules_dir.mkdir(parents=True)
        # oversize (>2048B) but valid yaml, declares verified
        (rules_dir / "SLV-900.yaml").write_text(
            _oversize_rule_yaml("SLV-900", trust_level="verified", pad_bytes=3000),
            encoding="utf-8",
        )
        # normal-sized rule, declares verified → must still be downgraded
        (rules_dir / "SLV-901.yaml").write_text(
            yaml.safe_dump({
                "id": "SLV-901", "name": "normal", "trust_level": "verified",
                "scope": "SCG-1", "severity": "low", "description": "small rule",
            }, sort_keys=False),
            encoding="utf-8",
        )
        reg = _make_registry_with_cap(tmp_path, max_file_bytes=2048, endpoints=[{
            "id": "hostile", "url": f"file://{hub_root}", "protocol": "file",
        }])
        client = sync_mod.HubSyncClient(reg)
        # Hermetic isolation: pull() otherwise writes cache/meta/audit under
        # REPO_ROOT, which persists across runs (24h TTL → a fresh cache from a
        # prior run would short-circuit re-stamping and mask a regression).
        # Redirect all three to tmp + force=True so every run re-fetches+stamps.
        client.cache_root = tmp_path / "cache"
        client.cache_meta_path = tmp_path / "cache" / "META.yaml"
        client.audit_log_path = tmp_path / "audit.yaml"
        result = client.pull("hostile", force=True)
        assert result.error is None  # non-blocking, no crash

        cache_root = result.cache_path
        # oversize file: skipped → NOT stamped (retains upstream value, no hub_origin)
        big_doc = yaml.safe_load((cache_root / "rules" / "SLV-900.yaml").read_text(encoding="utf-8"))
        assert big_doc["trust_level"] == "verified", "oversize file must be skipped, not stamped"
        assert "hub_origin" not in big_doc
        # normal file: still stamped external (cap does not affect normal path)
        small_doc = yaml.safe_load((cache_root / "rules" / "SLV-901.yaml").read_text(encoding="utf-8"))
        assert small_doc["trust_level"] == "external"
        # audit ledger recorded the oversize skip with a size-related reason
        audit = yaml.safe_load(client.audit_log_path.read_text(encoding="utf-8"))
        errs = [e for e in audit.get("events", []) if e.get("kind") == "hub_pull_stamp_error"]
        assert any("SLV-900" in str(e.get("file", "")) and "max read size" in str(e.get("error", ""))
                   for e in errs), "oversize skip must be audited with a size reason"

    def test_promote_rejects_oversize_cached_rule(self, tmp_path):
        """promote() reads via the bounded helper → an oversize (possibly cached)
        rule cannot be promoted into the trust ladder. PRE-fix it would parse and
        raise a *different* error (or proceed) — new raises HubContentTooLarge."""
        reg = _make_registry_with_cap(tmp_path, max_file_bytes=2048)
        client = sync_mod.HubSyncClient(reg)
        rule = tmp_path / "SLV-902.yaml"
        rule.write_text(_oversize_rule_yaml("SLV-902", trust_level="external", pad_bytes=3000),
                        encoding="utf-8")
        with pytest.raises(sync_mod.HubContentTooLarge):
            client.promote(rule, reviewer="alice")

    def test_promote_allows_normal_size_rule(self, tmp_path):
        """Regression: a normal-sized external rule still promotes fine."""
        reg = _make_registry_with_cap(tmp_path, max_file_bytes=2048)
        client = sync_mod.HubSyncClient(reg)
        rule = tmp_path / "SLV-903.yaml"
        rule.write_text(yaml.safe_dump({
            "id": "SLV-903", "name": "ok", "trust_level": "external",
            "scope": "SCG-0", "severity": "low", "description": "small",
        }, sort_keys=False), encoding="utf-8")
        res = client.promote(rule, reviewer="bob")
        assert res.to_trust == "verified"
        assert res.from_trust == "external"
