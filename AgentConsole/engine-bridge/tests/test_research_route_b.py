"""軌道 B：複製工作區、初始 commit、gh、token 零外洩（TCS AT-961-6-4～6-8、6-E-1、6-E-2）。

真 git 只在 `tmp_path`；gh 一律假夾具（`FAKE_GH_MODE`）；token 是假值
`ghp_FAKE_R2P1_TOKEN_000000000000000000`。內環鍵建檔需要 B1 補丁（交卷「需主控處理」）。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.research import gitops, route, scaffold
from app.research.orchestrator import BASELINE_REL
from app.settings import load_settings
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
TOKEN = rgs.FAKE_TOKEN


@pytest.fixture
def calls() -> Iterator[list[gitops.CallRecord]]:
    log: list[gitops.CallRecord] = []
    gitops.OBSERVERS.append(log.append)
    try:
        yield log
    finally:
        gitops.OBSERVERS.remove(log.append)


def sha_tree(root: Path) -> dict[str, tuple[str, int]]:
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(),
                                             p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def workspace_of(renv: rgs.RouteEnv, rid: str) -> Path:
    return Path(renv.env.db.get_project(rid)["workspace_path"])


def new_root(renv: rgs.RouteEnv, name: str = "demo-app") -> Path:
    return renv.scaffold / name


def route_status(renv: rgs.RouteEnv, rid: str) -> tuple[str, str | None, str]:
    row = renv.rdb.one("SELECT status, failure_step, id::text FROM "
                       "console.research_route_decisions WHERE research_id = %s", rid)
    assert row is not None
    return row[0], row[1], row[2]


def steps_of(renv: rgs.RouteEnv, route_id: str) -> dict[str, str]:
    return {s: st for s, st in renv.rdb.q(
        "SELECT step, status FROM console.research_route_steps WHERE route_id = %s ORDER BY "
        "step_no", route_id)}


# ── AT-961-6-4 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_4_the_workspace_copy_is_verified_per_file_and_the_source_is_untouched(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    ws = workspace_of(renv, rid)
    (ws / "00_research" / "raw").mkdir(parents=True, exist_ok=True)
    (ws / "00_research" / "raw" / "page.html").write_text("<html>raw</html>\n", encoding="utf-8")
    before = sha_tree(ws)
    resp = rgs.confirm(renv, rid, rgs.body_b(renv))
    assert resp.status_code == 200, resp.text
    copy = new_root(renv) / "my-project" / "demo"
    numbered = {k: v for k, v in before.items() if k.split("/")[0] in scaffold.WORKSPACE_DIRS}
    copied = {k: v[0] for k, v in sha_tree(copy).items()}
    assert copied == {k: v[0] for k, v in numbered.items()}, "四個編號目錄逐檔 sha256 與來源相同"
    assert (copy / "00_research" / "raw" / "page.html").is_file(), "副本含 raw（D-117）"
    after = sha_tree(ws)
    untouched = {k: v for k, v in numbered.items() if k.split("/")[0] != "02_governance"}
    assert all(after[k] == v for k, v in untouched.items()), "來源檔案位元組與 mtime 不變"


def test_AT_961_6_4_a_corrupted_copy_fails_the_step(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    real = scaffold.shutil.copyfile

    def corrupt(src: Any, dst: Any) -> Any:
        out = real(src, dst)
        if str(src).endswith("PRD-v1.0.0.md"):
            with open(dst, "ab") as fh:
                fh.write(b"X")
        return out

    monkeypatch.setattr(scaffold.shutil, "copyfile", corrupt)
    resp = rgs.confirm(renv, rid, rgs.body_b(renv))
    assert (resp.status_code, resp.json()["details"]["failure_step"]) == (502, "COPY_WORKSPACE")
    assert "copy_verify_failed" in resp.json()["details"]["steps"][-1]["stderr_tail"]


# ── AT-961-6-5 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_5_the_initial_commit_excludes_raw_and_env_and_equals_the_preview(
        renv: rgs.RouteEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text("[user]\n\tname = someone\n", encoding="utf-8")
    config_hash = hashlib.sha256((home / ".gitconfig").read_bytes()).hexdigest()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    rid = rgs.seed_gate0(renv)
    ws = workspace_of(renv, rid)
    (ws / "00_research" / "raw").mkdir(parents=True, exist_ok=True)
    (ws / "00_research" / "raw" / "x.html").write_text("raw\n", encoding="utf-8")
    (ws / "03_execution" / ".env").write_text("SECRET=1\n", encoding="utf-8")
    body = rgs.body_b(renv)
    previewed = rgs.preview(renv, rid, body)
    assert previewed.status_code == 200, previewed.text
    expected = sorted(previewed.json()["expected_tracked_files"])
    resp = rgs.confirm(renv, rid, body)
    assert resp.status_code == 200, resp.text
    root = new_root(renv)
    tracked = sorted(rgs.git(root, "ls-files").split())
    assert tracked == expected
    assert not [t for t in tracked if "00_research/raw/" in t or t.split("/")[-1] == ".env"]
    assert ".env.example" in tracked and ".github/workflows/ci.yml" in tracked
    assert "docker-compose.yml" in tracked
    log = rgs.git(root, "log", "--format=%s%n%an").splitlines()
    assert len(rgs.git(root, "log", "--oneline").splitlines()) == 1
    assert "ResearchToPRD" in log[0] and log[1] == gitops.DEFAULT_IDENTITY[0]
    assert "AC-001" not in log[0] and "背景" not in log[0], "訊息取自模板、不含 PRD 原文"
    assert hashlib.sha256((home / ".gitconfig").read_bytes()).hexdigest() == config_hash
    assert sorted(p.name for p in home.iterdir()) == [".gitconfig"], "不在家目錄寫任何東西"
    assert BASELINE_REL.split("/")[-1] in "".join(tracked)


# ── AT-961-6-6 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_6_gh_receives_a_precise_argv_and_the_token_only_in_its_environment(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh, calls: list[gitops.CallRecord]) -> None:
    rid = rgs.seed_gate0(renv, "alpha")
    body = rgs.body_b(renv, project_name="app-one", create_github=True, repo_name="app-one")
    resp = rgs.confirm(renv, rid, body, github_token=TOKEN)
    assert resp.status_code == 200, resp.text
    logged = fake_gh.calls()
    assert [c["argv"] for c in logged] == [
        ["auth", "status"],
        ["auth", "status"],
        ["repo", "create", "octocat/app-one", "--private", "--source", ".", "--push"]], logged
    assert all(c["has_gh_token"] for c in logged[1:])
    pub = rgs.seed_gate0(renv, "beta")
    resp = rgs.confirm(renv, pub, rgs.body_b(
        renv, project_name="app-two", create_github=True, repo_name="app-two",
        visibility="PUBLIC", confirm_repo_name="app-two"), github_token=TOKEN)
    assert resp.status_code == 200, resp.text
    assert fake_gh.calls()[-1]["argv"][3] == "--public"
    gh_calls = [c for c in calls if c.argv[0] == "gh"]
    git_calls = [c for c in calls if c.argv[0] == "git"]
    assert gh_calls and git_calls
    assert not [c for c in git_calls if c.has_gh_token], "GH_TOKEN 不得進 git 子行程環境"
    for record in calls:
        assert not [k for k in record.env_keys if k.startswith(("BRIDGE_", "SDD_"))
                    or k == "PYTHONPATH"], record.argv
        assert {"GIT_TERMINAL_PROMPT", "GCM_INTERACTIVE"} <= set(record.env_keys)
        assert TOKEN not in " ".join(record.argv)
    caps = renv.env.get("/research/capabilities").json()
    assert caps["gh_cli"]["authenticated"] == "NOT-EVALUABLE"


# ── AT-961-6-7 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_7_the_token_appears_on_no_surface_even_when_gh_leaks_it(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh) -> None:
    fake_gh.mode("leak")
    texts: list[str] = []
    rid = rgs.seed_gate0(renv, "alpha")
    ok = rgs.confirm(renv, rid, rgs.body_b(renv, project_name="app-one", create_github=True),
                     github_token=TOKEN)
    texts.append(ok.text)
    assert ok.status_code == 200, ok.text
    fake_gh.mode("fail-create")
    rid2 = rgs.seed_gate0(renv, "beta")
    bad = rgs.confirm(renv, rid2, rgs.body_b(renv, project_name="app-two", create_github=True),
                      github_token=TOKEN)
    texts.append(bad.text)
    assert bad.status_code == 502, bad.text
    assert not [t for t in texts if rgs.contains_secret(t, TOKEN)]
    cells = list(rgs.all_text_columns(renv.rdb))
    assert len(cells) > 100 and len({t for t, _c, _v in cells}) > 5, "掃描範圍非空"
    assert not [(t, c) for t, c, v in cells if v and rgs.contains_secret(str(v), TOKEN)]
    roots = [renv.scaffold, Path(renv.env.settings.research_root), Path(
        renv.env.settings.engine_workspace)]
    assert any(any(r.rglob("*")) for r in roots if r.exists())
    assert not [h for r in roots for h in rgs.scan_files(r, TOKEN)]
    steps = renv.rdb.q("SELECT argv_redacted, stdout_tail, stderr_tail FROM "
                       "console.research_route_steps")
    assert steps and not [s for s in steps if any(rgs.contains_secret(c, TOKEN) for c in s)]
    assert rgs.contains_secret("x " + TOKEN, TOKEN), "掃描器負控"
    leaked = renv.rdb.one("SELECT stdout_tail FROM console.research_route_steps WHERE step = "
                          "'GH_REPO_CREATE' AND status = 'OK'")
    assert leaked is not None and "***" in leaked[0], "洩漏的 token 已被遮罩"


# ── AT-961-6-8 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_6_8_gh_failures_keep_the_local_steps_and_a_retry_only_redoes_the_remote_step(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh, calls: list[gitops.CallRecord],
        monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    body = rgs.body_b(renv, create_github=True)
    project = renv.console_project("keep")
    fake_gh.mode("fail-create")
    failed = renv.env.post(f"/research/projects/{rid}:route", {
        **body, "console_project_id": project, "github_token": TOKEN})
    assert failed.status_code == 502, failed.text
    status, step, route_id = route_status(renv, rid)
    assert (status, step) == ("FAILED", "GH_REPO_CREATE")
    done = steps_of(renv, route_id)
    assert done["GH_REPO_CREATE"] == "FAILED" and all(
        done[s] == "OK" for s in ("SCAFFOLD_FILES", "COPY_WORKSPACE", "GIT_INIT", "GIT_COMMIT"))
    tail = renv.rdb.one("SELECT stderr_tail FROM console.research_route_steps WHERE step = "
                        "'GH_REPO_CREATE'")
    assert tail is not None and "gh_permission_denied" in tail[0] and TOKEN not in tail[0]
    root = new_root(renv)
    commit = rgs.git(root, "rev-parse", "HEAD").strip()
    fake_gh.mode("ok")
    calls.clear()
    retried = renv.env.post(f"/research/projects/{rid}:route", {
        **body, "console_project_id": project, "github_token": TOKEN, "retry": True})
    assert retried.status_code == 200, retried.text
    verbs = [c.argv[1] if c.argv[0] == "git" else "gh" for c in calls]
    assert "init" not in verbs and "add" not in verbs and "commit" not in verbs
    assert "gh" in verbs and rgs.git(root, "rev-parse", "HEAD").strip() == commit
    assert route_status(renv, rid)[0] == "SUCCEEDED"


def test_AT_961_6_8_a_missing_token_and_a_vanished_gh_have_readable_causes(
        renv: rgs.RouteEnv, fake_gh: rgs.FakeGh, monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv, "alpha")
    monkeypatch.setenv("FAKE_GH_REQUIRE_TOKEN", "1")
    no_token = rgs.confirm(renv, rid, rgs.body_b(renv, project_name="app-one",
                                                 create_github=True))
    assert no_token.status_code == 422, "gh 未登入：預演與確認都在副作用前回缺項 gh_auth"
    assert {"item": "gh_auth"}.items() <= no_token.json()["details"]["missing"][0].items()
    monkeypatch.delenv("FAKE_GH_REQUIRE_TOKEN")
    rid2 = rgs.seed_gate0(renv, "beta")

    def vanish(phase: str, step: str) -> None:
        if (phase, step) == ("before", "GH_REPO_CREATE"):
            rgs.hide_gh(monkeypatch)             # 連本機真 gh 一起藏起來（hermetic）

    monkeypatch.setattr(route, "STEP_HOOK", vanish)
    gone = rgs.confirm(renv, rid2, rgs.body_b(renv, project_name="app-two", create_github=True),
                       github_token=TOKEN)
    assert gone.status_code == 502 and gone.json()["details"]["failure_step"] == "GH_REPO_CREATE"
    assert "gh_not_found" in json.dumps(gone.json()["details"]["steps"], ensure_ascii=False)


# ── AT-961-6-E-1 ───────────────────────────────────────────────────────────────────────────
def test_AT_961_6_E_1_the_scaffold_root_is_required_and_derived_paths_stay_inside_it(
        renv: rgs.RouteEnv, make_env: Any, route_db: Any, real_tree: Path, tmp_path: Path) -> None:
    rid = rgs.seed_gate0(renv)
    for bad in ("../escape", "a/b", "..", "a\\b"):
        resp = rgs.preview(renv, rid, rgs.body_b(renv, project_name=bad))
        assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed"), bad
    ok = rgs.preview(renv, rid, rgs.body_b(renv))
    assert ok.status_code == 200
    assert ok.json()["execution_path"] == str(renv.scaffold / "demo-app")
    cfg = load_settings({"ENGINE_WORKSPACE": str(tmp_path / "e"),
                         "BRIDGE_SCAFFOLD_ROOT": str(tmp_path / "sc")})
    assert (tmp_path / "sc").resolve() in cfg.allowed_path_roots, "自動併入允許根（D8）"
    unset = load_settings({"ENGINE_WORKSPACE": str(tmp_path / "e2")})
    assert unset.research_scaffold_root is None


# ── AT-961-6-E-2 ───────────────────────────────────────────────────────────────────────────
def test_AT_961_6_E_2_redaction_covers_split_cut_encoded_and_multiple_tokens() -> None:
    # 刻意以片段拼出 fine-grained PAT 的形狀：原始碼不留權杖字面（根層機密掃描閘會擋 commit），
    # 執行期的值仍是 gitops 去敏樣式 `github_pat_[A-Za-z0-9_]{16,}` 的真命中。
    other = "github_" + "pat_" + "ABCDEFGHIJKLMNOPQRSTUV" + "_0123456789"
    secrets = (TOKEN, other)
    cases = [
        f"before {TOKEN} after",
        f"{TOKEN[:12]}\n{TOKEN[12:]}",
        "x" * 1990 + TOKEN,
        f"url=https://x/?t={TOKEN.replace('_', '%5F')}",
        f"{TOKEN} and {other} twice {TOKEN}",
    ]
    for text in cases:
        out = gitops.tail(gitops.redact(text, secrets))
        for secret in secrets:
            assert secret not in out and secret[:8] not in out, text[:40]
    kept = gitops.redact("fatal: repository not found (exit 128)", secrets)
    assert kept == "fatal: repository not found (exit 128)", "未知形態不誤遮罩"
    assert len(gitops.tail("y" * 5000)) == 2000
    masked = gitops.tail(gitops.redact("z" * 1999 + TOKEN, secrets))
    assert masked.count("*") <= 3 and TOKEN[:4] not in masked.replace("***", "")
