"""git／gh 的唯一出口（TCS AT-961-8-1～8-4、8-7、8-E-1、8-E-2；PKG-BR-D1；ADR-003 D16＋D-99）。

全部是 Unit：允許集合與禁止形態以表驅動；子行程以替身驗證「拒絕＝零 spawn」與環境重建。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from app import procutil, sdd_cli
from app.research import gitops
from tests import research_git_support as rgs

TOKEN = "ghp_FAKE_R2P1_TOKEN_000000000000000000"
fake_gh = rgs.fake_gh
MSG_PUBLISH = gitops.commit_message("publish", "RP-0007", "0123456789ab")
MSG_SCAFFOLD = gitops.commit_message("scaffold", "RP-0007")


class Spawns:
    """`gitops._spawn` 的替身：記錄每次 spawn（拒絕的呼叫不會出現）。"""

    def __init__(self, out: str = "", err: str = "", rc: int = 0) -> None:
        self.calls: list[tuple[list[str], str, dict[str, str]]] = []
        self.out, self.err, self.rc = out, err, rc

    def __call__(self, argv: Any, cwd: Path, env: Any, timeout: float) -> tuple[int, str, str]:
        self.calls.append((list(argv), str(cwd), dict(env)))
        return self.rc, self.out, self.err


@pytest.fixture
def spawns(monkeypatch: pytest.MonkeyPatch) -> Spawns:
    fake = Spawns()
    monkeypatch.setattr(gitops, "_spawn", fake)
    return fake


@pytest.fixture
def dirs(tmp_path: Path) -> dict[str, Path]:
    out = {"scaffold": tmp_path / "scaffold", "worktrees": tmp_path / "wt",
           "tree": tmp_path / "wt" / "rp-0007-x", "project": tmp_path / "scaffold" / "demo-app"}
    for path in out.values():
        path.mkdir(parents=True)
    return out


def ops(dirs: dict[str, Path]) -> gitops.Gitops:
    return gitops.Gitops(scaffold_root=dirs["scaffold"], worktree_root=dirs["worktrees"])


# ── AT-961-8-1 ─────────────────────────────────────────────────────────────────────────────
def allowed_cases(d: dict[str, Path]) -> list[tuple[list[str], Path]]:
    wt = str(d["worktrees"] / "rp-0007-new")
    return [
        (["status", "--porcelain"], d["tree"]),
        (["rev-parse", "--verify", "main"], d["tree"]),
        (["rev-parse", "--show-toplevel"], d["tree"]),
        (["diff", "--name-only", "main..feature/issue-0007"], d["tree"]),
        (["ls-files"], d["project"]), (["ls-files", "-s"], d["project"]),
        (["branch", "--list", "feature/issue-0007"], d["tree"]),
        (["worktree", "list", "--porcelain"], d["tree"]),
        (["-c", "core.longpaths=true", "worktree", "add", "-b", "feature/issue-0007", wt, "main"],
         d["tree"]),
        (["init", "-b", "main"], d["project"]),
        (["add", "-A"], d["project"]),
        (["add", "--", "docs/a.md", "docs/b.md"], d["tree"]),
        (["commit", "-m", MSG_PUBLISH], d["tree"]), (["commit", "-m", MSG_SCAFFOLD], d["project"]),
        (["remote", "add", "origin", "https://github.com/octocat/demo-app"], d["project"]),
        (["push", "-u", "origin", "feature/issue-0007"], d["project"]),
    ]


def test_AT_961_8_1_every_allowed_form_builds_an_argv_list(dirs: dict[str, Path]) -> None:
    for tokens, cwd in allowed_cases(dirs):
        argv = gitops.parse_git(tokens, cwd=cwd, scaffold_root=dirs["scaffold"],
                                worktree_root=dirs["worktrees"])
        assert isinstance(argv, list) and argv[0] == "git", tokens
        assert not [a for a in argv if any(c in a for c in ";|&`$\n")], tokens
    for args in (["auth", "status"],
                 ["repo", "create", "octocat/demo-app", "--private", "--source", ".", "--push"],
                 ["repo", "create", "octocat/demo-app", "--public", "--source", ".", "--push"]):
        assert gitops.build_argv("gh", args)[0] == "gh"
    assert gitops.build_argv("status", ["--porcelain"]) == ["git", "status", "--porcelain"]


def test_AT_961_8_1_add_dash_a_and_add_paths_are_confined(dirs: dict[str, Path]) -> None:
    kw = {"scaffold_root": dirs["scaffold"], "worktree_root": dirs["worktrees"]}
    for bad_cwd in (dirs["tree"], dirs["scaffold"].parent):
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_git(["add", "-A"], cwd=bad_cwd, **kw)
    nested = dirs["scaffold"] / "wt-inside"
    nested.mkdir()
    with pytest.raises(gitops.GitopsDenied):       # worktree 根巢在 scaffold 內：worktree 仍禁 -A
        gitops.parse_git(["add", "-A"], cwd=nested, scaffold_root=dirs["scaffold"],
                         worktree_root=nested)
    for bad in ("../x", str(dirs["scaffold"] / "elsewhere.txt"), "-x"):
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_git(["add", "--", "docs/a.md", bad], cwd=dirs["tree"], **kw)


def test_AT_961_8_1_only_the_longpaths_option_and_template_commit_messages_pass(
        dirs: dict[str, Path]) -> None:
    kw = {"scaffold_root": dirs["scaffold"], "worktree_root": dirs["worktrees"]}
    wt = str(dirs["worktrees"] / "p")
    with pytest.raises(gitops.GitopsDenied):
        gitops.parse_git(["-c", "core.longpaths=false", "worktree", "add", "-b", "feature/x", wt,
                          "main"], **kw)
    with pytest.raises(gitops.GitopsDenied):
        gitops.parse_git(["commit", "-m", "任意自由文字"], cwd=dirs["tree"], **kw)
    for tokens in (["tag", "-a", "v1", "-m", "x"], ["pr", "create"], ["release", "create"]):
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_git(tokens, cwd=dirs["tree"], **kw)
    for args in (["pr", "create"], ["release", "create", "v1"]):
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_gh(args)


# ── AT-961-8-2 ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN = [
    ["push", "--force"], ["push", "-f"], ["push", "--force-with-lease"], ["push", "--FORCE"],
    ["push", "--force=x"], ["push", "origin", "+main"], ["push", "-u", "origin", "+main"],
    ["reset", "--hard"], ["reset", "--merge"], ["reset", "--keep"], ["clean", "-fd"], ["stash"],
    ["stash", "push"], ["stash", "pop"], ["checkout", "--", "x"], ["checkout", "-f"],
    ["restore", "x"], ["switch", "-f"], ["switch", "--discard-changes"],
    ["config", "--global", "user.name", "x"], ["config", "--system", "x"], ["config", "x", "y"],
    ["-c", "core.hooksPath=x", "status"], ["worktree", "remove"], ["branch", "-D", "x"]]


@pytest.mark.parametrize("tokens", FORBIDDEN, ids=lambda t: " ".join(t))
def test_AT_961_8_2_every_destructive_form_is_refused_before_spawning(
        tokens: list[str], spawns: Spawns, dirs: dict[str, Path]) -> None:
    with pytest.raises(gitops.GitopsDenied) as caught:
        ops(dirs).git(tokens, cwd=dirs["tree"])
    assert caught.value.verb in (tokens[0], "-c", "path") or tokens[0] in str(caught.value)
    assert spawns.calls == [], "在 spawn 之前拒絕"
    assert TOKEN not in str(caught.value) and "PATH" not in str(caught.value)


# ── AT-961-8-3 ─────────────────────────────────────────────────────────────────────────────
INJECTIONS = ["-x", "--upload-pack=x", "a;b", "a|b", "a&b", "$(id)", "`id`", "a\nb", "a b",
              "a\x00b", "--orphan", ""]


@pytest.mark.parametrize("bad", INJECTIONS)
def test_AT_961_8_3_option_injection_and_shell_metacharacters_never_reach_a_process(
        bad: str, spawns: Spawns, dirs: dict[str, Path]) -> None:
    g, wt = ops(dirs), str(dirs["worktrees"] / "p")
    attempts = [
        ["worktree", "add", "-b", bad, wt, "main"], ["worktree", "add", "-b", "feature/x", wt, bad],
        ["rev-parse", "--verify", bad], ["push", "-u", "origin", bad],
        ["branch", "--list", bad], ["diff", "--name-only", f"{bad}..main"]]
    for tokens in attempts:
        with pytest.raises(gitops.GitopsDenied):
            g.git(tokens, cwd=dirs["tree"])
    for args in (["repo", "create", f"{bad}/demo", "--private", "--source", ".", "--push"],
                 ["repo", "create", f"octocat/{bad}", "--private", "--source", ".", "--push"]):
        with pytest.raises(gitops.GitopsDenied):
            g.gh(args, cwd=dirs["tree"])
    assert spawns.calls == []


def test_AT_961_8_3_owner_visibility_and_path_rules(spawns: Spawns, dirs: dict[str, Path]) -> None:
    g = ops(dirs)
    for owner in ("a/b", "..", "-a", "a_b", "o" * 40):
        with pytest.raises(gitops.GitopsDenied):
            g.gh(["repo", "create", f"{owner}/demo", "--private", "--source", ".", "--push"],
                 cwd=dirs["tree"])
    with pytest.raises(gitops.GitopsDenied):
        g.gh(["repo", "create", "octocat/demo", "--internal", "--source", ".", "--push"],
             cwd=dirs["tree"])
    with pytest.raises(gitops.GitopsDenied):
        g.git(["add", "--", "../escape"], cwd=dirs["tree"])
    assert spawns.calls == []
    for ok in ("feature/issue-0007",):
        assert gitops.valid_branch(ok)
    assert gitops.valid_ref("main") and gitops.valid_repo_name("demo-app")
    assert gitops.valid_owner("octocat") and "PRIVATE" in gitops.VISIBILITIES


# ── AT-961-8-4 ─────────────────────────────────────────────────────────────────────────────
class FakeProc:
    returncode = 0
    pid = 1

    def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
        return b"", b""


def test_AT_961_8_4_the_child_process_is_shaped_by_the_whitelist_not_the_parent(
        dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    launched: list[tuple[list[str], dict[str, Any]]] = []

    def popen(argv: Any, **kwargs: Any) -> FakeProc:
        launched.append((list(argv), kwargs))
        return FakeProc()

    monkeypatch.setattr(gitops.subprocess, "Popen", popen)
    monkeypatch.setattr(gitops.shutil, "which", lambda name, path=None: f"/fake/{name}")
    for name, value in (("BRIDGE_X", "1"), ("SDD_Y", "1"), ("PYTHONPATH", "x"),
                        ("GH_TOKEN", "parent-token"), ("HOME", str(dirs["scaffold"]))):
        monkeypatch.setenv(name, value)
    g = gitops.Gitops(scaffold_root=dirs["scaffold"], worktree_root=dirs["worktrees"], token=TOKEN)
    g.git(["status", "--porcelain"], cwd=dirs["tree"])
    g.git(["init", "-b", "main"], cwd=dirs["project"])
    g.gh(["auth", "status"], cwd=dirs["project"])
    (git_ro, git_rw, gh_call) = launched
    for argv, kwargs in launched:
        assert isinstance(argv, list) and kwargs["shell"] is False
        assert all(kwargs[k] == v for k, v in procutil.popen_platform_kwargs().items())
        env = kwargs["env"]
        assert not [k for k in env if k.startswith(("BRIDGE_", "SDD_")) or k == "PYTHONPATH"]
        assert env["GIT_TERMINAL_PROMPT"] == "0" and env["GCM_INTERACTIVE"] == "never"
        assert env["GIT_AUTHOR_NAME"] == env["GIT_COMMITTER_NAME"]
        assert env["GIT_CONFIG_GLOBAL"] == os.devnull == env["GIT_CONFIG_SYSTEM"]
    assert "GH_TOKEN" not in git_ro[1]["env"] and "GH_TOKEN" not in git_rw[1]["env"]
    assert gh_call[1]["env"]["GH_TOKEN"] == TOKEN
    assert git_ro[1]["env"]["GIT_OPTIONAL_LOCKS"] == "0"
    assert "GIT_OPTIONAL_LOCKS" not in git_rw[1]["env"]
    if sys.platform == "win32":
        assert git_ro[1]["creationflags"] & getattr(gitops.subprocess, "CREATE_NO_WINDOW", 0)


def test_AT_961_8_4_no_token_means_no_gh_token_in_the_environment(
        dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "parent-token")
    env = gitops.child_env("gh", token=None)
    assert "GH_TOKEN" not in env and "GITHUB_TOKEN" not in env
    assert gitops.child_env("gh", token=TOKEN)["GH_TOKEN"] == TOKEN
    assert "GH_TOKEN" not in gitops.child_env("git", token=TOKEN)


# ── AT-961-8-7 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_8_7_the_verb_sets_are_unchanged() -> None:
    assert sdd_cli.RESEARCH_VERBS == {"show", "transition", "gate", "spec-frozen",
                                      "spec-refreeze"}
    assert "resume-from-escalation" not in sdd_cli.RESEARCH_VERBS
    assert "resume-from-escalation" not in sdd_cli.ALLOWED_VERBS
    assert len(sdd_cli.ALLOWED_VERBS) == 5


# ── AT-961-8-E-1／E-2 ──────────────────────────────────────────────────────────────────────
def test_AT_961_8_E_1_output_is_redacted_then_tail_cut(dirs: dict[str, Path],
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    noisy = f"token={TOKEN}\n" + "x" * 3000 + f"\nGH_TOKEN={TOKEN}"
    fake = Spawns(out=noisy, err=f"HOME=/root PATH=/bin {TOKEN}", rc=1)
    monkeypatch.setattr(gitops, "_spawn", fake)
    g = gitops.Gitops(scaffold_root=dirs["scaffold"], worktree_root=dirs["worktrees"],
                      secrets=(TOKEN,), token=TOKEN)
    result = g.git(["status", "--porcelain"], cwd=dirs["tree"])
    assert TOKEN not in result.stdout and TOKEN not in result.stderr
    assert len(result.stdout) <= 2000 and "***" in result.stdout
    assert TOKEN not in result.argv_redacted
    assert [k for k in fake.calls[0][2] if k == "GH_TOKEN"] == []


@pytest.mark.parametrize("tokens", [
    ["push", "-u", "origin", "feature/issue-0007"]])
def test_AT_961_8_E_2_only_origin_with_a_verified_branch_is_pushed(
        tokens: list[str], spawns: Spawns, dirs: dict[str, Path]) -> None:
    ops(dirs).git(tokens, cwd=dirs["project"])
    assert spawns.calls[0][0][:4] == ["git", "push", "-u", "origin"]
    spawns.calls.clear()
    for bad in (["push", "upstream", "x"], ["push", "https://evil.example/x.git"],
                ["push", "origin", "HEAD:refs/heads/x"], ["push", "origin", "+x"],
                ["push", "-u", "origin", "+x"], ["push", "origin"],
                ["push", "-u", "origin", "HEAD:refs/heads/x"]):
        with pytest.raises(gitops.GitopsDenied):
            ops(dirs).git(bad, cwd=dirs["project"])
    assert spawns.calls == []


# ── D-134 第 7 條：tcs／scr 兩模板（BR-D3）────────────────────────────────────────────────────
def test_D_134_tcs_and_scr_templates_are_exact_and_pass_the_commit_whitelist(
        dirs: dict[str, Path]) -> None:
    tcs = gitops.commit_message("tcs", "RP-0007", "0123456789ab")
    scr = gitops.commit_message("scr", "RP-0007", "0123456789ab")
    assert tcs == "docs: 發佈 RP-0007 TCS（sha256 0123456789ab）"
    assert scr == "docs: SCR 發佈 RP-0007 PRD 新版（sha256 0123456789ab）"
    kw = {"scaffold_root": dirs["scaffold"], "worktree_root": dirs["worktrees"]}
    for message in (tcs, scr):
        argv = gitops.parse_git(["commit", "-m", message], cwd=dirs["tree"], **kw)
        assert argv[:3] == ["git", "commit", "-m"] and argv[3] == message


def test_D_134_tcs_and_scr_templates_reject_bad_sha_bad_rp_no_and_unknown_kind() -> None:
    for kind in ("tcs", "scr"):
        for sha in (None, "", "xyz", "0123456789AB", "0123456789abc"):
            with pytest.raises(gitops.GitopsDenied):
                gitops.commit_message(kind, "RP-0007", sha)
        with pytest.raises(gitops.GitopsDenied):
            gitops.commit_message(kind, "bad", "0123456789ab")
    with pytest.raises(gitops.GitopsDenied):
        gitops.commit_message("tcs2", "RP-0007", "0123456789ab")
    with pytest.raises(gitops.GitopsDenied):       # 自由文字仍擋（白名單只多兩條固定句型）
        gitops.parse_git(["commit", "-m", "docs: 發佈 RP-0007 TCS（sha256 zz）"],
                         cwd=Path("."), scaffold_root=Path("."), worktree_root=Path("."))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# P2（PKG-BR-P2；TCS AT-962-2-*）：tag 與 PR 的白名單形態。以下 append-only，上方既有測試一字未動
# （`test_AT_961_8_1_…` 的 `tag -a v1 -m x`、缺旗標 `pr create`、`release create` 仍是拒絕案：
# `v1` 不是 semver、`x` 不是模板訊息，所以那三項負控原封不動仍成立）。
# ══════════════════════════════════════════════════════════════════════════════════════════════
TAG = "v1.2.3"
TAG_MSG = gitops.release_message(TAG, "RP-0007", "0123456789ab")
P2_TOKEN = "ghp_FAKE_R2P2_TOKEN_000000000000000000"
REPO_ROOT = Path(__file__).resolve().parents[3]
TCS_P2 = REPO_ROOT / "AgentConsole" / "docs" / "03_testing" / "contracts" / (
    "TCS-ResearchToPRD-P2-20261107.md")
PR_CREATE = ["pr", "create", "--title", "feat: RP-0007 x（1 FR／2 AC）", "--body", "## 摘要\n內文",
             "--base", "main", "--head", "feature/x"]


def p2_kw(d: dict[str, Path]) -> dict[str, Any]:
    return {"scaffold_root": d["scaffold"], "worktree_root": d["worktrees"], "cwd": d["tree"]}


def test_AT_962_2_1_the_six_git_forms_for_tags_build_an_argv_list(dirs: dict[str, Path]) -> None:
    forms = [["tag", "--list", TAG], ["tag", "-a", TAG, "-m", TAG_MSG], ["push", "origin", TAG],
             ["ls-remote", "--tags", "origin", TAG], ["remote", "get-url", "origin"],
             ["rev-parse", "--verify", f"refs/tags/{TAG}"]]
    for tokens in forms:
        assert gitops.parse_git(tokens, **p2_kw(dirs)) == ["git", *tokens], tokens
    for tokens in (["tag", "-a", "v1", "-m", "x"], ["tag", "-a", TAG, "-m", "任意自由文字"],
                   ["tag", "-a", "v9.9.9", "-m", TAG_MSG], ["release", "create"],
                   ["pr", "create"]):          # 非模板訊息、訊息與 tag 不同名、其他動詞：仍拒
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_git(tokens, **p2_kw(dirs))


def test_AT_962_2_2_gh_pr_create_and_pr_list_pass_other_gh_forms_stay_refused() -> None:
    assert gitops.parse_gh(PR_CREATE) == ["gh", *PR_CREATE]
    assert gitops.parse_gh(["pr", "list", "--head", "feature/x", "--json", "url"]) == [
        "gh", "pr", "list", "--head", "feature/x", "--json", "url"]
    swapped = ["pr", "create", "--body", "b", "--title", "t", "--base", "main", "--head", "x"]
    for args in (["pr", "merge"], ["pr", "close"], ["release", "create", "v1"],
                 ["repo", "delete"], ["pr", "create"], PR_CREATE[:-2], swapped,
                 ["pr", "list", "--json", "url", "--head", "feature/x"],
                 ["pr", "list", "--head", "feature/x"]):
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_gh(args)


MESSAGE_CASES = [
    (TAG_MSG, True),
    (f"release: {TAG}（RP-12345，追溯快照 sha256 0123456789ab）", True),
    (f"release: {TAG}（追溯快照 sha256 0123456789ab）", False),                  # 缺 RP 號
    (f"release: {TAG}（RP-007，追溯快照 sha256 0123456789ab）", False),          # RP 號 3 位
    (f"release: {TAG}（RP-0007，追溯快照 sha256 0123456789a）", False),          # sha 11 碼
    (f"release: {TAG}（RP-0007，追溯快照 sha256 0123456789abc）", False),        # sha 13 碼
    (f"release: {TAG}（RP-0007，追溯快照 sha256 0123456789AB）", False),         # 大寫
    (TAG_MSG + "\n", False), (TAG_MSG + " ", False), (TAG_MSG + "\nx", False),   # 換行／尾隨空白
    (TAG_MSG.replace("（", "(").replace("）", ")"), False),                      # 半形括號
    ("release: 1.2（RP-0007，追溯快照 sha256 0123456789ab）", False),            # semver 不合
]


@pytest.mark.parametrize(("message", "ok"), MESSAGE_CASES, ids=range(len(MESSAGE_CASES)))
def test_AT_962_2_3_the_tag_message_template_is_fullmatched(message: str, ok: bool,
                                                            dirs: dict[str, Path]) -> None:
    tokens = ["tag", "-a", TAG, "-m", message]
    if ok:
        assert gitops.parse_git(tokens, **p2_kw(dirs))[-1] == message
    else:
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_git(tokens, **p2_kw(dirs))


def test_AT_962_2_3_existing_commit_templates_do_not_regress(dirs: dict[str, Path]) -> None:
    for message in (MSG_PUBLISH, MSG_SCAFFOLD):
        assert gitops.parse_git(["commit", "-m", message], **p2_kw(dirs))[-1] == message
    assert not gitops._tag_message_ok(TAG, MSG_PUBLISH)


def test_AT_962_2_4_valid_semver_boundaries_and_the_contract_constant() -> None:
    good = ["1.2.3", "v1.2.3", "1.2.3-rc.1", "1.2.3+b.5", "1.2.3-rc.1+b.5", "0.0.0",
            "v1.2.3-" + "a" * 57]
    assert len(good[-1]) == 64
    bad = ["v1.2.3-" + "a" * 58, "1.2", "01.2.3", "1.2.3.4", "v", "", "-x", "1.2.3 ", "1.2.3;x",
           "../1.2.3", "1.2.3\n", None, 123]
    assert len(bad[0]) == 65
    assert all(gitops.valid_semver(t) for t in good)
    assert not any(gitops.valid_semver(t) for t in bad)
    text = TCS_P2.read_text(encoding="utf-8")
    start = text.index("| `tagName` 正規式 | `") + len("| `tagName` 正規式 | `")
    assert text[start:text.index("`，長度至多 64", start)] == gitops.SEMVER_PATTERN, \
        "Bridge 與契約（console-api 同源）的 tagName 正規式須逐字相同"
    assert gitops.TAG_MAX_CHARS == 64


def test_AT_962_2_5_push_origin_tag_is_a_separate_form_and_does_not_loosen_dash_u(
        dirs: dict[str, Path]) -> None:
    kw = p2_kw(dirs)
    assert gitops.parse_git(["push", "-u", "origin", "feature/x"], **kw)[-1] == "feature/x"
    assert gitops.parse_git(["push", "origin", TAG], **kw) == ["git", "push", "origin", TAG]
    for tokens in (["push", "origin", "feature/x"], ["push", "origin", "refs/heads/x"],
                   ["push", "--tags"], ["push", "origin", f"+{TAG}"], ["push", "origin", f":{TAG}"],
                   ["push", "-f", "origin", TAG], ["push", "-u", "origin", TAG, "x"],
                   ["push", "origin", TAG, "--force"]):
        with pytest.raises(gitops.GitopsDenied):
            gitops.parse_git(tokens, **kw)


def test_AT_962_2_6_git_children_never_get_the_gh_token(spawns: Spawns,
                                                       dirs: dict[str, Path]) -> None:
    git_ops = gitops.Gitops(scaffold_root=dirs["scaffold"], worktree_root=dirs["worktrees"],
                            secrets=(P2_TOKEN,), token=P2_TOKEN)
    git_ops.git(["tag", "-a", TAG, "-m", TAG_MSG], cwd=dirs["tree"])
    argv, _cwd, env = spawns.calls[-1]
    assert "GH_TOKEN" not in env and P2_TOKEN not in " ".join(argv)
    assert set(env) >= {"GIT_TERMINAL_PROMPT", "GIT_CONFIG_GLOBAL", "GIT_AUTHOR_NAME"}
    assert gitops.child_env("git", token=P2_TOKEN, base={}).keys() == gitops.child_env(
        "gh", base={}).keys() - {"GH_TOKEN"}, "環境白名單鍵集合與 P1 相同"


def test_AT_962_2_6_a_leaking_gh_prints_the_token_but_every_returned_text_is_redacted(
        tmp_path: Path, fake_gh: Any) -> None:
    git_ops = gitops.Gitops(secrets=(P2_TOKEN,), token=P2_TOKEN)
    fake_gh.mode("leak")
    result = git_ops.gh(PR_CREATE, cwd=tmp_path)
    assert result.returncode == 0 and "debug token=" in result.stdout, "leak 模式確實有印"
    assert P2_TOKEN not in result.stdout + result.stderr + result.argv_redacted
    last = fake_gh.calls()[-1]
    assert last["has_gh_token"] is True and P2_TOKEN not in json.dumps(last["argv"])

FORBIDDEN_P2 = [["push", "--force", "origin", "v1"], ["push", "origin", "v1", "--force"],
                ["push", "--tags"], ["tag", "-d", "v1"], ["tag", "-f", "v1"],
                ["tag", "-a", "v1"], ["branch", "-D", "x"]]
FORBIDDEN_GH = [["release", "create", "v1"], ["pr", "merge", "1"], ["pr", "close", "1"]]


@pytest.mark.parametrize("tokens", FORBIDDEN_P2, ids=lambda t: " ".join(t))
def test_AT_962_2_E_1_destructive_tag_and_push_forms_are_refused_before_spawning(
        tokens: list[str], spawns: Spawns, dirs: dict[str, Path]) -> None:
    with pytest.raises(gitops.GitopsDenied) as caught:
        ops(dirs).git(tokens, cwd=dirs["tree"])
    assert spawns.calls == [] and P2_TOKEN not in str(caught.value)


@pytest.mark.parametrize("args", FORBIDDEN_GH, ids=lambda t: " ".join(t))
def test_AT_962_2_E_1_destructive_gh_forms_are_refused_before_spawning(
        args: list[str], spawns: Spawns, dirs: dict[str, Path]) -> None:
    with pytest.raises(gitops.GitopsDenied):
        ops(dirs).gh(args, cwd=dirs["tree"])
    assert spawns.calls == []


@pytest.mark.parametrize("bad", ["-v1.2.3", "--exec=x", "v1 2", "v1\t2", "v1\n2"])
def test_AT_962_2_E_2_tag_names_with_option_shapes_never_reach_a_process(
        bad: str, spawns: Spawns, dirs: dict[str, Path]) -> None:
    g = ops(dirs)
    for tokens in (["tag", "--list", bad], ["tag", "-a", bad, "-m", TAG_MSG],
                   ["push", "origin", bad], ["ls-remote", "--tags", "origin", bad]):
        with pytest.raises(gitops.GitopsDenied):
            g.git(tokens, cwd=dirs["tree"])
    assert spawns.calls == []


@pytest.mark.parametrize("head", ["-x", "a b", "a..b", "a\nb", ""])
def test_AT_962_2_E_2_pr_heads_with_option_shapes_never_reach_a_process(
        head: str, spawns: Spawns, dirs: dict[str, Path]) -> None:
    g = ops(dirs)
    for args in ([*PR_CREATE[:-1], head], ["pr", "list", "--head", head, "--json", "url"]):
        with pytest.raises(gitops.GitopsDenied):
            g.gh(args, cwd=dirs["tree"])
    assert spawns.calls == []


def test_AT_962_2_E_3_git_and_gh_argv_literals_live_only_in_gitops_and_exec_modules_are_unchanged(
) -> None:
    import ast

    from tests import test_research_ast_locks as locks
    from tests import test_research_capability as capability

    assert locks.EXEC_MODULES == frozenset({
        "runner.py", "sdd_cli.py", "si_cli.py", "health.py", "routers/sdd.py",
        "research/gitops.py"})
    for rel in ("research/delivery.py", "research/healing.py", "research/inner_gates.py",
                "routers/research_deliver.py"):
        tree = ast.parse((capability.APP_DIR / rel).read_text(encoding="utf-8"))
        assert capability.git_gh_lines(tree) == [], f"{rel} 含 git／gh 的 argv 字面"
    assert [rel for rel, kind in capability.CAPABILITY.items() if kind == "vcs"] == [
        "research/gitops.py"]
