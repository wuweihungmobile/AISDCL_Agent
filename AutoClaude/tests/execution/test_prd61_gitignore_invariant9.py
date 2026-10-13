"""PRD §6.1 不變式 9：引擎的狀態目錄必須在 .gitignore（`.autoclaude/` 不得進 commit）。

立案（PRD §16.2「§6.1 啟動自檢不變式」那一列）：寫「未做＝…`.autoclaude/` gitignore
檢查」，再開症狀＝狀態目錄進了 commit。現查事實：引擎實際寫入的目錄是 `checkpoint_dir`
（出廠 `checkpoints`），PRD 字面的 `.autoclaude/` 只有在使用者把 `checkpoint_dir` 指進去、
或別的工具建出它時才存在 ⇒ 判準對「引擎真的會寫的目錄」與「已存在的 `.autoclaude/`」
兩者都問一次 `git check-ignore`。

四層判準，各守一個失效方向：
  (a) 判決表：rc 0／1／128／其餘／拋例外各一格，且問的是帶尾斜線的目錄形態。
  (b) 真 git：尾斜線在目錄尚不存在時仍判對（不帶斜線的實測回 rc=1，會假紅）。
  (c) 選目錄：只問引擎真的會寫、或已存在的目錄；repo 外的目錄結構上不可能被 commit，不問。
  (d) 入口：真 `main()` 在任何 step 之前以 rc=1 拒絕；已 ignore 時照常放行。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autoclaude.execution import boot_self_check as B
from tests.execution.test_prd12_permission_bypass_invariant8 import (
    _boot,
    _FakeService,
    _synthetic_config,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]          # monorepo 根
_AUTOCLAUDE = Path(__file__).resolve().parents[2]


def _git(cwd: Path, *args: str) -> int:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, check=False,
                          encoding="utf-8", errors="replace").returncode


def _repo(path: Path, ignore: str | None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    assert _git(path, "init", "-q", ".") == 0
    if ignore is not None:
        (path / ".gitignore").write_text(ignore, encoding="utf-8", newline="\n")
    return path


def _runner(rc: int, out: str = ""):
    seen: list[list[str]] = []

    def run(argv: list[str]) -> tuple[int, str]:
        seen.append(argv)
        return rc, out
    run.seen = seen          # type: ignore[attr-defined]
    return run


# ══════════════════════════════════════════════════════════════════════════════
# (a) 判決表：每一格各有一支紅綠
# ══════════════════════════════════════════════════════════════════════════════
def test_rc0_ignored_passes_without_a_problem():
    out = B.gitignore_verdict("/repo", ".autoclaude", _runner(0))
    assert out.problems == ()
    assert any(".autoclaude/" in ln and "不變式 9" in ln for ln in out.lines)


def test_rc1_not_ignored_is_a_boot_problem_that_names_the_fix():
    out = B.gitignore_verdict("/repo", ".autoclaude", _runner(1))
    assert len(out.problems) == 1
    p = out.problems[0]
    assert ".autoclaude/" in p and ".gitignore" in p and "不變式 9" in p


def test_rc128_not_a_git_repo_passes_but_says_so():
    """128＝非 git repo：無 git 就無 commit，無從違反；通過，但不得靜默（note 留在 lines）。"""
    out = B.gitignore_verdict("/repo", ".autoclaude", _runner(128, "fatal: not a git repository"))
    assert out.problems == ()
    assert any("不是 git repo" in ln for ln in out.lines)


@pytest.mark.parametrize("rc", [2, 3, 255])
def test_any_other_rc_is_fail_loud_not_silently_green(rc):
    """`git check-ignore -q` 只定義 0／1／128；其餘代表沒量到。量不到不得讀成「已忽略」。"""
    out = B.gitignore_verdict("/repo", ".autoclaude", _runner(rc, "boom"))
    assert len(out.problems) == 1 and f"rc={rc}" in out.problems[0]


def test_a_missing_git_binary_is_noted_and_logged_not_a_crash(caplog):
    def run(argv):
        raise FileNotFoundError("git")
    with caplog.at_level("WARNING", logger="autoclaude.execution.boot_self_check"):
        out = B.gitignore_verdict("/repo", ".autoclaude", run)
    assert out.problems == ()
    assert any("git 不可用" in ln for ln in out.lines)
    assert "git 不可用" in caplog.text


def test_the_question_asked_is_the_trailing_slash_directory_form():
    """尾斜線是承重的：帶斜線＝問「這是一個目錄」。見 (b) 的真 git 對照。"""
    run = _runner(0)
    B.gitignore_verdict("/some/repo", ".autoclaude", run)
    assert run.seen == [["git", "-C", "/some/repo", "check-ignore", "-q", ".autoclaude/"]]


def test_a_dir_name_that_already_has_slashes_is_normalised_to_one_trailing_slash():
    run = _runner(0)
    B.gitignore_verdict("/r", "ckpt/state//", run)
    assert run.seen[0][-1] == "ckpt/state/"


# ══════════════════════════════════════════════════════════════════════════════
# (b) 真 git：不 mock git——這一節要治的失效形態全部住在 git 自己的射程裡
# ══════════════════════════════════════════════════════════════════════════════
def test_real_git_ignored_dir_passes_even_while_the_dir_does_not_exist_yet(tmp_path):
    repo = _repo(tmp_path / "r", ".autoclaude/\n")
    assert not (repo / ".autoclaude").exists()
    assert B.gitignore_verdict(repo, ".autoclaude").problems == ()


def test_real_git_unignored_dir_is_refused(tmp_path):
    repo = _repo(tmp_path / "r", "something_else/\n")
    out = B.gitignore_verdict(repo, ".autoclaude")
    assert len(out.problems) == 1 and "不在 .gitignore" in out.problems[0]


def test_real_git_a_nested_ignore_entry_covers_a_nested_state_dir(tmp_path):
    repo = _repo(tmp_path / "r", ".autoclaude/\n")
    assert B.gitignore_verdict(repo, ".autoclaude/checkpoints").problems == ()


def test_real_git_outside_a_repo_passes_with_a_note(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    out = B.gitignore_verdict(plain, ".autoclaude")
    assert out.problems == () and any("不是 git repo" in ln for ln in out.lines)


@pytest.mark.parametrize("shipped", [_REPO_ROOT / ".gitignore", _AUTOCLAUDE / ".gitignore"],
                         ids=["monorepo-root", "AutoClaude"])
def test_each_shipped_gitignore_alone_covers_the_prd_literal_dir(tmp_path, shipped):
    """§6.1 不變式 9 的字面：引擎可在 monorepo 根或 AutoClaude/ 任一處執行，兩份 .gitignore 必須
    **各自**涵蓋 `.autoclaude/`。刻意把檔案內容單獨放進一個空 repo 問 git：直接問真實 repo
    會被另一層的同名規則遮住（根規則不錨定、會蓋住子層），拿掉任一份都仍然綠。"""
    repo = _repo(tmp_path / "r", shipped.read_text(encoding="utf-8"))
    assert B.gitignore_verdict(repo, ".autoclaude").problems == (), shipped
    assert B.gitignore_verdict(repo, ".autoclaude/checkpoints").problems == ()


# ══════════════════════════════════════════════════════════════════════════════
# (c) 選目錄
# ══════════════════════════════════════════════════════════════════════════════
def test_a_checkpoint_dir_inside_the_repo_is_guarded_by_its_relative_posix_path(tmp_path):
    assert B.state_dirs_to_guard(tmp_path, str(tmp_path / "ckpt")) == ("ckpt",)
    assert B.state_dirs_to_guard(tmp_path, "checkpoints") == ("checkpoints",)


def test_a_checkpoint_dir_outside_the_repo_cannot_be_committed_so_it_is_not_asked(tmp_path):
    repo, elsewhere = tmp_path / "repo", tmp_path / "elsewhere"
    repo.mkdir()
    assert B.state_dirs_to_guard(repo, str(elsewhere / "ckpt")) == ()


@pytest.mark.parametrize("raw", ["", ".", "./"])
def test_the_repo_root_itself_is_not_a_guardable_state_dir(tmp_path, raw):
    assert B.state_dirs_to_guard(tmp_path, raw) == ()


def test_an_existing_dot_autoclaude_dir_is_guarded_in_addition(tmp_path):
    (tmp_path / ".autoclaude").mkdir()
    assert B.state_dirs_to_guard(tmp_path, "checkpoints") == ("checkpoints", ".autoclaude")


def test_a_checkpoint_dir_that_is_already_under_dot_autoclaude_is_not_asked_twice(tmp_path):
    (tmp_path / ".autoclaude").mkdir()
    dirs = B.state_dirs_to_guard(tmp_path, ".autoclaude/checkpoints")
    assert dirs == (".autoclaude/checkpoints", ".autoclaude")
    assert len(set(dirs)) == len(dirs)


# ══════════════════════════════════════════════════════════════════════════════
# boot_self_check：接線、零附帶面
# ══════════════════════════════════════════════════════════════════════════════
def _cli(_argv):
    return 0, "2.1.295"


def test_callers_that_predate_the_new_arguments_never_touch_git():
    def boom(argv):
        raise AssertionError("沒有傳 ignored_dirs 卻去問了 git")
    report = B.boot_self_check(cli_runner=_cli, git_runner=boom)
    assert report.ok is True


def test_a_not_ignored_state_dir_stops_the_boot_with_the_problem_in_the_report():
    report = B.boot_self_check(cli_runner=_cli, repo_root="/r", ignored_dirs=("ckpt",),
                               git_runner=_runner(1))
    assert report.ok is False
    assert any("ckpt/" in p and "不變式 9" in p for p in report.problems)


def test_every_listed_dir_is_asked_and_the_ignored_ones_leave_a_line():
    run = _runner(0)
    report = B.boot_self_check(cli_runner=_cli, repo_root="/r",
                               ignored_dirs=("ckpt", ".autoclaude"), git_runner=run)
    assert report.ok is True
    assert [a[-1] for a in run.seen] == ["ckpt/", ".autoclaude/"]
    assert sum("不變式 9" in ln for ln in report.lines) == 2


# ══════════════════════════════════════════════════════════════════════════════
# (d) 入口：真 main() 在任何 step 之前拒絕；已 ignore 時照常放行
# ══════════════════════════════════════════════════════════════════════════════
def test_symptom_main_refuses_an_unignored_checkpoint_dir_before_any_step(
        tmp_path, monkeypatch, caplog):
    """再開症狀本身：狀態目錄在 repo 內卻沒被 ignore。修前 rc=0 照跑；修後 rc=1、沒組出 service。"""
    _repo(tmp_path, None)
    with caplog.at_level("INFO", logger="autoclaude"):
        rc = _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path))
    assert rc == 1
    assert _FakeService.built is False, "已拒絕卻仍進了執行階段"
    assert "開機自檢未過" in caplog.text and "不變式 9" in caplog.text


def test_main_boots_when_the_checkpoint_dir_is_ignored(tmp_path, monkeypatch):
    """正向對照：沒有它，上一格分不出「有牙齒」與「咬所有人」。"""
    _repo(tmp_path, "ckpt/\n")
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path)) == 0
    assert _FakeService.built is True


def test_main_boots_outside_a_git_repo(tmp_path, monkeypatch):
    """既有的所有 in-tmp 啟動測試都在非 git 目錄跑：128 必須放行，否則它們全紅。"""
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path)) == 0


def test_main_refuses_an_unignored_dot_autoclaude_even_when_the_configured_dir_is_fine(
        tmp_path, monkeypatch):
    """PRD 字面：`.autoclaude/` 已存在於 repo 內就必須被 ignore（別的工具或舊版建出來的也算）。"""
    _repo(tmp_path, "ckpt/\n")
    (tmp_path / ".autoclaude").mkdir()
    assert _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path)) == 1
    assert _FakeService.built is False
