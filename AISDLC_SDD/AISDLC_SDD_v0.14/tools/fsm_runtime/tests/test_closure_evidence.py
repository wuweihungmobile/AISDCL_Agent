"""test_closure_evidence.py — improving_21 / DEF-20-001 結案證據強制重推導

廉價層（git 事實）以 tmp 真實 git repo 驗真實 cat-file/merge-base/rev-parse 行為
（非 mock，Rule 9 測 intent）；昂貴層驗 HEAD 綁定 + inconclusive fail-closed；
verdict 合成驗三分支優先序。退化即紅。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tools.fsm_runtime import closure_evidence as ce


# ─────────────────────────────────────────────────────────────
# tmp 真實 git repo fixture
# ─────────────────────────────────────────────────────────────


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("1", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c1")
    return repo


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


# ─────────────────────────────────────────────────────────────
# 契約解析
# ─────────────────────────────────────────────────────────────


def test_parse_evidence_present():
    md = "前文\n```yaml\nclosure-evidence:\n  iteration: 21\n  claimed_commits: [abc1234]\n```\n後文"
    ev = ce.parse_closure_evidence(md)
    assert ev is not None and ev["iteration"] == 21 and ev["claimed_commits"] == ["abc1234"]


def test_parse_evidence_absent():
    assert ce.parse_closure_evidence("沒有任何 yaml 區塊") is None
    # 有 yaml 但非 closure-evidence → None
    assert ce.parse_closure_evidence("```yaml\nfoo: 1\n```") is None


def test_parse_evidence_last_match_wins():
    # DEF-21-001：schema 範例（placeholder）在前、真實契約在後 → 取末尾真實契約
    md = (
        "```yaml\nclosure-evidence:\n  base_sha: <HEAD>\n  iteration: 0\n```\n"  # schema 範例
        "中間說明\n"
        "```yaml\nclosure-evidence:\n  base_sha: abcdef1234567890\n  iteration: 21\n```"  # 真實契約
    )
    ev = ce.parse_closure_evidence(md)
    assert ev["iteration"] == 21 and ev["base_sha"] == "abcdef1234567890"


# ─────────────────────────────────────────────────────────────
# 廉價層：git 事實（真實 repo）
# ─────────────────────────────────────────────────────────────


def test_real_commit_passes(git_repo: Path):
    facts = ce.verify_git_facts({"claimed_commits": [_head(git_repo)]}, git_repo)
    assert len(facts) == 1 and facts[0].status == "PASS"


def test_fabricated_commit_fails(git_repo: Path):
    # 合法格式但不存在的 hash（編造）
    facts = ce.verify_git_facts({"claimed_commits": ["deadbeef1234"]}, git_repo)
    assert facts[0].status == "FAIL" and "不存在" in facts[0].detail


def test_non_ancestor_commit_fails(git_repo: Path):
    # 在 detached 旁支建一個不在 HEAD 歷史的 commit
    main_head = _head(git_repo)
    _git(git_repo, "checkout", "-q", "-b", "side")
    (git_repo / "b.txt").write_text("2", encoding="utf-8")
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-q", "-m", "side")
    side_head = _head(git_repo)
    _git(git_repo, "checkout", "-q", "-")  # 回 main 分支（HEAD=main_head）
    assert _head(git_repo) == main_head
    facts = ce.verify_git_facts({"claimed_commits": [side_head]}, git_repo)
    assert facts[0].status == "FAIL" and "祖先" in facts[0].detail


def test_injection_hash_rejected(git_repo: Path):
    for bad in ["abc; rm -rf /", "abc1234::test", "../../etc"]:
        facts = ce.verify_git_facts({"claimed_commits": [bad]}, git_repo)
        assert facts[0].status == "FAIL" and "不合法" in facts[0].detail


def test_real_tag_passes(git_repo: Path):
    _git(git_repo, "tag", "v2026.06.16-99")
    facts = ce.verify_git_facts({"claimed_tag": "v2026.06.16-99"}, git_repo)
    assert facts[0].kind == "tag" and facts[0].status == "PASS"


def test_missing_tag_fails(git_repo: Path):
    facts = ce.verify_git_facts({"claimed_tag": "v-does-not-exist"}, git_repo)
    assert facts[0].status == "FAIL" and "不存在" in facts[0].detail


# ─────────────────────────────────────────────────────────────
# 昂貴層：HEAD 綁定 + inconclusive fail-closed
# ─────────────────────────────────────────────────────────────


def test_expensive_stale_base_sha_inconclusive(git_repo: Path):
    ev = {"base_sha": "0" * 40, "autoclaude_pytest_passed": 3112}
    claims = ce.verify_expensive_claims(ev, git_repo)
    assert claims and all(c.status == "INCONCLUSIVE" for c in claims)
    assert "過期" in claims[0].detail


def test_expensive_missing_cert_inconclusive(git_repo: Path):
    ev = {"base_sha": _head(git_repo), "autoclaude_pytest_passed": 3112}
    claims = ce.verify_expensive_claims(ev, git_repo)
    assert claims[0].status == "INCONCLUSIVE" and "證書" in claims[0].detail


def test_expensive_cert_match_verified(git_repo: Path):
    ce.write_rederive_cert(git_repo, {"autoclaude_pytest_passed": 3112})
    ev = {"base_sha": _head(git_repo), "autoclaude_pytest_passed": 3112}
    claims = ce.verify_expensive_claims(ev, git_repo)
    assert claims[0].status == "VERIFIED"


def test_expensive_cert_mismatch_fails(git_repo: Path):
    ce.write_rederive_cert(git_repo, {"autoclaude_pytest_passed": 9999})
    ev = {"base_sha": _head(git_repo), "autoclaude_pytest_passed": 3112}
    claims = ce.verify_expensive_claims(ev, git_repo)
    assert claims[0].status == "FAIL" and "造假" in claims[0].detail


# ─────────────────────────────────────────────────────────────
# verdict 合成（三分支優先序）
# ─────────────────────────────────────────────────────────────


def test_verdict_fail_takes_priority():
    facts = [ce.FactResult("commit", "x", "FAIL", "編造")]
    claims = [ce.ClaimResult("k", 1, None, "INCONCLUSIVE")]
    v = ce.synthesize_verdict({"iteration": 21}, facts, claims)
    assert v.verdict == "FAIL"


def test_verdict_inconclusive_when_no_fail():
    facts = [ce.FactResult("commit", "x", "PASS")]
    claims = [ce.ClaimResult("k", 1, None, "INCONCLUSIVE")]
    assert ce.synthesize_verdict({}, facts, claims).verdict == "INCONCLUSIVE"


def test_verdict_verified_all_pass():
    facts = [ce.FactResult("commit", "x", "PASS")]
    claims = [ce.ClaimResult("k", 1, 1, "VERIFIED")]
    assert ce.synthesize_verdict({}, facts, claims).verdict == "VERIFIED"


# ─────────────────────────────────────────────────────────────
# 端到端 + 持久化
# ─────────────────────────────────────────────────────────────


def test_evaluate_closure_no_evidence_inconclusive(git_repo: Path):
    v = ce.evaluate_closure(git_repo, md_text="無契約")
    assert v.verdict == "INCONCLUSIVE"


def test_evaluate_closure_real_commit_end_to_end(git_repo: Path):
    head = _head(git_repo)
    md = f"```yaml\nclosure-evidence:\n  iteration: 21\n  claimed_commits: [{head}]\n```"
    v = ce.evaluate_closure(git_repo, md_text=md)
    # git 事實 PASS、無昂貴項 → VERIFIED
    assert v.verdict == "VERIFIED" and v.facts[0].status == "PASS"


def test_write_verdict_report_persists(git_repo: Path):
    v = ce.ClosureVerdict(iteration=21, verdict="VERIFIED", head_sha=_head(git_repo))
    p = ce.write_verdict_report(v, git_repo)
    assert p.exists()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["verdict"] == "VERIFIED" and data["iteration"] == 21


# ─────────────────────────────────────────────────────────────
# CLI 入口（DEF-21-003：hook INCONCLUSIVE 訊息承諾的 --rederive 須真實可用）
# ─────────────────────────────────────────────────────────────


def test_cli_rederive_writes_cert(git_repo: Path):
    rc = ce._main(["--rederive", "--observed", '{"autoclaude_pytest_passed": 3112}'], repo_root=git_repo)
    assert rc == 0
    cert = ce._rederive_cert_path(git_repo, _head(git_repo))
    assert cert.exists()
    data = yaml.safe_load(cert.read_text(encoding="utf-8"))
    assert data["base_sha"] == _head(git_repo) and data["observed"]["autoclaude_pytest_passed"] == 3112


def test_cli_rederive_bad_json_returns_2(git_repo: Path):
    assert ce._main(["--rederive", "--observed", "not-json"], repo_root=git_repo) == 2


def test_cli_default_evaluates(git_repo: Path):
    # 無契約 → evaluate 回 INCONCLUSIVE，exit 0
    assert ce._main([], repo_root=git_repo) == 0
