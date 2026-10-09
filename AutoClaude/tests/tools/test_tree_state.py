"""tests/tools/test_tree_state.py — DEF-101-887：nightly 觀察樣本的工作樹狀態戳記。

對應 tools/tree_state.py。受測意圖（Rule 9：測的是「樣本事後能不能被正確剔除」，
不是「函式有回值」）：

  1. 髒樹／起跑時髒／中途 HEAD 變了 ⇒ `valid=False`（中間態樣本事後可被剔除）；
  2. 量不出來（git 壞了、起跑態 unknown）⇒ `valid=None`——**不冤枉也不背書**：
     冤枉＝把好樣本剔掉、觀察期永遠湊不滿；背書＝把量不出來的當乾淨、假綠；
  3. 缺 `tree` 欄的舊樣本一律保留（沒有證據就不能改判，回溯不可判定）；
  4. 永不 raise：量測工具壞掉不得讓 nightly 採集跟著壞。

git 部分一律在臨時 repo 上**真跑 git**（不 mock git 本身）；只有「git 不可用」類案例
才替換 subprocess。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import tree_state


@pytest.fixture(autouse=True)
def _isolate_git_and_start_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """清掉會讓 git 指到別的 repo 的環境變數，以及 ps1 匯出的起跑態。

    WHY：本檔從 pre-commit／pre-push hook 或 nightly 的 Stage L 底下跑時，行程環境帶
    `GIT_DIR`／`GIT_INDEX_FILE` 等變數——臨時 repo 上的 git 會被導去量**外面那個 repo**，
    案例結果於是取決於「從哪裡被啟動」。`AUTOCLAUDE_NIGHTLY_TREE_START` 同理：nightly 內跑
    本檔時它是設著的，不清掉的話每個沒顯式傳 `environ=` 的案例都會讀到真正的起跑態。
    """
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.delenv(tree_state.START_ENV, raising=False)


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """一個只有一個 commit、工作樹乾淨的臨時 git repo。"""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _start(head: str, state: str) -> dict[str, str]:
    return {tree_state.START_ENV: f"{head}|{state}"}


def _other_commit(head: str) -> str:
    """一個確定不是 `head` 前綴的 hex 縮寫（避免寫死 `deadbeef` 撞上臨時 repo 的真 head）。"""
    return ("0" if head[0] != "0" else "1") + head[1:8]


# ══════════════════════════════════════════════════════════════════════════════
# capture：當下的工作樹
# ══════════════════════════════════════════════════════════════════════════════


def test_clean_tree_is_valid(repo: Path) -> None:
    got = tree_state.capture(repo, environ={})

    assert got["state"] == "clean" and got["dirty_entries"] == 0
    assert got["head"] == _git(repo, "rev-parse", "HEAD")
    assert got["valid"] is True
    # 沒有 ps1 匯出的起跑態 ⇒ 起跑欄位全是 None，且「中途變過」不可被誤報成 False
    assert got["start_head"] is None and got["start_state"] is None
    assert got["changed_during_run"] is None


def test_capture_schema_is_fixed(repo: Path) -> None:
    """下游（兩個判準、ps1 的人讀 log）都按這七個鍵取值；鍵集與順序是契約。"""
    assert list(tree_state.capture(repo, environ={})) == [
        "head", "state", "dirty_entries", "start_head", "start_state",
        "changed_during_run", "valid",
    ]


def test_modified_tracked_file_makes_the_sample_invalid(repo: Path) -> None:
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")

    got = tree_state.capture(repo, environ={})

    assert (got["state"], got["dirty_entries"], got["valid"]) == ("dirty", 1, False)


def test_staged_only_change_is_dirty_too(repo: Path) -> None:
    """agent 做到一半 `git add` 了還沒 commit——那也是半成品樹。"""
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")

    got = tree_state.capture(repo, environ={})

    assert (got["state"], got["valid"]) == ("dirty", False)


def test_untracked_file_counts_as_dirty(repo: Path) -> None:
    """與 ps1 起跑時的 `git status --porcelain` 同口徑（untracked 也算一筆）。"""
    (repo / "new.txt").write_text("x\n", encoding="utf-8")

    got = tree_state.capture(repo, environ={})

    assert (got["state"], got["dirty_entries"], got["valid"]) == ("dirty", 1, False)


def test_dirty_entries_counts_entries_and_non_ascii_names_once(repo: Path) -> None:
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    (repo / "中文檔名.txt").write_text("x\n", encoding="utf-8")

    got = tree_state.capture(repo, environ={})

    assert got["dirty_entries"] == 2, "非 ASCII 路徑不得被 quotepath 拆成多列或漏算"


# ══════════════════════════════════════════════════════════════════════════════
# capture：git 量不出來 ⇒ unknown，永不 raise，也不能被讀成 clean
# ══════════════════════════════════════════════════════════════════════════════


def _assert_unknown(got: dict[str, Any]) -> None:
    assert got["state"] == "unknown"
    assert got["head"] is None and got["dirty_entries"] is None
    assert got["valid"] is None, "量不出來不得被背書成 True，也不得被冤枉成 False"


def test_not_a_git_repo_is_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    # 防止 git 往上找到外層（開發機上 tmp 可能剛好在某個 repo 底下）
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))

    _assert_unknown(tree_state.capture(plain, environ={}))


def test_missing_directory_is_unknown(tmp_path: Path) -> None:
    _assert_unknown(tree_state.capture(tmp_path / "nope", environ={}))


def test_git_executable_missing_is_unknown(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(repo))  # PATH 上沒有 git

    _assert_unknown(tree_state.capture(repo, environ={}))


@pytest.mark.parametrize(
    "exc",
    [subprocess.TimeoutExpired(cmd="git", timeout=1), OSError("boom"), RuntimeError("boom")],
    ids=["timeout", "oserror", "any-other-exception"],
)
def test_any_failure_inside_git_is_swallowed_into_unknown(
    repo: Path, monkeypatch: pytest.MonkeyPatch, exc: Exception
) -> None:
    """「任何例外」都不得往外冒：採集比標記重要，量測壞了 nightly 不能跟著壞。"""
    def boom(*_a: Any, **_k: Any) -> None:
        raise exc

    monkeypatch.setattr(tree_state.subprocess, "run", boom)

    _assert_unknown(tree_state.capture(repo, environ={}))


def test_git_is_called_read_only_encoded_and_console_free(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """合約：不搶 index.lock、不吃 locale 編碼、Windows 不閃 console 視窗、有逾時。"""
    calls: list[tuple[list[str], dict[str, Any]]] = []
    real_run = subprocess.run

    def spy(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((cmd, kwargs))
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(tree_state.subprocess, "run", spy)

    tree_state.capture(repo, environ={})

    assert len(calls) == 2, "一次 rev-parse＋一次 status，別多叫"
    for cmd, kwargs in calls:
        assert cmd[0] == "git"
        # nightly 長跑期間人或 agent 可能正在 git add／commit；status 預設會順手刷新 index
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        assert kwargs["encoding"] == "utf-8" and kwargs["errors"] == "replace"
        assert kwargs["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
        assert kwargs["timeout"] and kwargs["timeout"] > 0
        assert kwargs["cwd"] == repo
    status = next(cmd for cmd, _ in calls if "status" in cmd)
    assert "--porcelain" in status and "core.quotepath=false" in status


def test_default_repo_dir_is_the_monorepo_root() -> None:
    """預設口徑＝整個 monorepo（與 ps1 起跑時的 `git status` 同口徑）；搬檔會讓它悄悄指錯地方。"""
    root = tree_state._DEFAULT_REPO_DIR
    assert (root / "AutoClaude" / "tools" / "tree_state.py").is_file()


# ══════════════════════════════════════════════════════════════════════════════
# capture：ps1 起跑時匯出的起跑態（AUTOCLAUDE_NIGHTLY_TREE_START）
# ══════════════════════════════════════════════════════════════════════════════


def test_head_moved_since_run_start_invalidates_even_a_clean_tree(repo: Path) -> None:
    """跑到一半有 commit 落地：現在這棵樹乾淨，但這輪的樣本橫跨了兩個版本。"""
    head = _git(repo, "rev-parse", "HEAD")

    got = tree_state.capture(repo, environ=_start(_other_commit(head), "clean"))

    assert got["state"] == "clean"
    assert got["changed_during_run"] is True
    assert got["valid"] is False


def test_ps1_short_sha_matches_the_full_head(repo: Path) -> None:
    """ps1 匯出的是 `git rev-parse --short HEAD`；沒有前綴比對的話每個樣本都會被誤判成中途變過。"""
    head = _git(repo, "rev-parse", "HEAD")

    for spelled in (head[:7], head[:7].upper(), head[:12], head):
        got = tree_state.capture(repo, environ=_start(spelled, "clean"))
        assert got["changed_during_run"] is False, spelled
        assert got["valid"] is True, spelled


def test_dirty_at_run_start_invalidates_a_now_clean_tree(repo: Path) -> None:
    head = _git(repo, "rev-parse", "HEAD")

    got = tree_state.capture(repo, environ=_start(head[:7], "dirty"))

    assert got["state"] == "clean" and got["changed_during_run"] is False
    assert got["valid"] is False, "起跑時就髒＝這輪從頭到尾都不是 HEAD 的狀態"


def test_unknown_start_state_is_neither_endorsed_nor_condemned(repo: Path) -> None:
    head = _git(repo, "rev-parse", "HEAD")

    got = tree_state.capture(repo, environ=_start(head[:7], "unknown"))

    assert got["start_state"] == "unknown"
    assert got["valid"] is None


def test_start_state_survives_when_the_start_head_is_empty(repo: Path) -> None:
    """ps1 取不到 sha 時匯出 `|dirty`——head 缺席但 state 仍是證據，不能整串丟掉。"""
    got = tree_state.capture(repo, environ={tree_state.START_ENV: "|dirty"})

    assert got["start_head"] is None and got["start_state"] == "dirty"
    assert got["changed_during_run"] is None
    assert got["valid"] is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, (None, None)),
        ("", (None, None)),
        ("garbage", (None, None)),
        ("abc1234|bogus", (None, None)),   # 狀態不在 clean／dirty／unknown ⇒ 整串視為垃圾
        ("abc1234|", (None, None)),
        ("|", (None, None)),
        ("not-hex|dirty", (None, "dirty")),  # head 不可用，state 仍是證據
        (" ABC1234 | Clean ", ("ABC1234", "clean")),
    ],
)
def test_parse_start_accepts_only_well_formed_values(
    raw: str | None, expected: tuple[str | None, str | None]
) -> None:
    assert tree_state._parse_start(raw) == expected


def test_missing_or_garbled_start_env_never_condemns_a_clean_tree(repo: Path) -> None:
    """垃圾輸入不得讓好樣本被剔除（冤枉）：起跑態讀不懂就當沒有。"""
    for raw in ("", "garbage", "abc1234|bogus"):
        got = tree_state.capture(repo, environ={tree_state.START_ENV: raw})
        assert got["valid"] is True, raw
        assert got["changed_during_run"] is None, raw


def test_environ_defaults_to_the_process_environment(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv(tree_state.START_ENV, f"{head[:7]}|dirty")

    got = tree_state.capture(repo)  # 不傳 environ

    assert got["start_state"] == "dirty" and got["valid"] is False


def test_dirty_now_beats_a_clean_start(repo: Path) -> None:
    """起跑乾淨、head 沒變，但採樣當下有人在改檔 ⇒ 仍是中間態。"""
    head = _git(repo, "rev-parse", "HEAD")
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")

    got = tree_state.capture(repo, environ=_start(head[:7], "clean"))

    assert got["changed_during_run"] is False
    assert got["valid"] is False


# ══════════════════════════════════════════════════════════════════════════════
# is_invalid_sample / exclude_invalid：判準端的剔除述詞
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({}, False),                                  # 舊樣本：沒有 tree 欄
        ({"tree": None}, False),
        ({"tree": "dirty"}, False),                   # tree 不是物件
        ({"tree": {}}, False),                        # 沒有 valid 鍵
        ({"tree": {"valid": None}}, False),           # 量不出來 ⇒ 不冤枉
        ({"tree": {"valid": True}}, False),
        ({"tree": {"valid": False}}, True),
        ({"tree": {"valid": 0}}, False),              # 嚴格 `is False`：0 不是 False
        ({"_invalid": True, "_raw": "{bad"}, False),  # ga_check 對壞行的標記，不是中間態
    ],
)
def test_only_an_explicit_false_valid_is_invalid(record: dict[str, Any], expected: bool) -> None:
    assert tree_state.is_invalid_sample(record) is expected


def test_exclude_invalid_keeps_order_counts_and_does_not_mutate_input() -> None:
    records = [
        {"i": 0},
        {"i": 1, "tree": {"valid": False}},
        {"i": 2, "tree": {"valid": None}},
        {"i": 3, "tree": {"valid": True}},
        {"i": 4, "tree": {"valid": False}},
    ]

    kept, excluded = tree_state.exclude_invalid(records)

    assert [r["i"] for r in kept] == [0, 2, 3]
    assert excluded == 2
    assert len(records) == 5, "入參不得被改動"


def test_exclude_invalid_accepts_any_iterable_and_empty() -> None:
    assert tree_state.exclude_invalid([]) == ([], 0)
    kept, excluded = tree_state.exclude_invalid(
        r for r in ({"tree": {"valid": False}}, {"x": 1})
    )
    assert (kept, excluded) == ([{"x": 1}], 1)


# ══════════════════════════════════════════════════════════════════════════════
# 真接線：三個 collector → capture() → git；以及 nightly 實際的「腳本形態」呼叫
# ══════════════════════════════════════════════════════════════════════════════
# 其他測試檔為了 hermetic 都把 capture() 換掉了，所以「collector 真的呼叫到真的 capture」
# 這件事只有這裡守：接線斷掉（匯入名打錯、被誤刪）時，那些測試仍然全綠。


def test_the_three_collectors_stamp_the_real_tree_state(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools import ac4_nightly_collector, drift_log_snapshot, observability_snapshot

    monkeypatch.setattr(tree_state, "_DEFAULT_REPO_DIR", repo)
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    head = _git(repo, "rev-parse", "HEAD")
    args = argparse.Namespace(run_id="t", recall=0.99, p95=40.0, cb_open=0, status="pass")

    records = {
        "observability_snapshot": observability_snapshot.collect_snapshot(),
        "drift_log_snapshot": drift_log_snapshot.build_record(severity_non_info_count=0),
        "ac4_nightly_collector": ac4_nightly_collector._build_record(args, {}),
    }

    for name, record in records.items():
        assert record["tree"]["head"] == head, name
        assert (record["tree"]["state"], record["tree"]["valid"]) == ("dirty", False), name


_AUTOCLAUDE_DIR = Path(tree_state.__file__).resolve().parent.parent


def _run_script(script: str, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """以 nightly 的形態（`python tools/<script>.py`）跑，且加 `-S` 讓 `tools` 套件**不可**匯入。

    WHY：ps1 就是這樣呼叫各支腳本的（sys.path[0] 是 tools/，AutoClaude 不在 path 上），此時
    `from tools import tree_state` 會 ImportError，靠各檔的裸 import 後備才載得起來。後備壞掉
    ＝collector／判準在 nightly 啟動就崩 ＝觀察期整段凍結——而 pytest 以套件形態匯入，
    永遠測不到這條路。`-S` 把 site-packages（含把 AutoClaude 放進 path 的 editable .pth）
    一併拿掉，讓這條路在任何機器上都被實際走到。
    """
    return subprocess.run(
        [sys.executable, "-S", str(_AUTOCLAUDE_DIR / "tools" / script), *args],
        cwd=_AUTOCLAUDE_DIR,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )


def _last_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])


def test_nightly_form_scripts_stamp_and_judge_the_tree(repo: Path, tmp_path: Path) -> None:
    head = _git(repo, "rev-parse", "HEAD")
    env = {
        **os.environ,
        "GIT_DIR": str(repo / ".git"),
        "GIT_WORK_TREE": str(repo),
        tree_state.START_ENV: f"{head[:7]}|clean",  # 與 ps1 匯出的形態一致（短 sha）
    }
    collectors = {
        "ac4": ("ac4_nightly_collector.py", "--status", "pass", "--recall", "0.999",
                "--p95", "41", "--cb-open", "0"),
        "drift": ("drift_log_snapshot.py", "--severity-count", "0"),
        "obs": ("observability_snapshot.py",),
    }

    def collect(label: str) -> dict[str, Path]:
        histories = {}
        for name, (script, *rest) in collectors.items():
            history = tmp_path / f"{label}_{name}.jsonl"
            proc = _run_script(script, *rest, "--history", str(history), env=env)
            assert proc.returncode == 0, f"{script}: {proc.stderr[-400:]}"
            histories[name] = history
        return histories

    clean = collect("clean")
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")  # 採樣期間有人在改檔
    dirty = collect("dirty")

    for name in collectors:
        assert _last_record(clean[name])["tree"]["valid"] is True, name
        assert _last_record(dirty[name])["tree"]["valid"] is False, name

    judges = {
        "ac4": ("ac4_progress_check.py", "--json"),
        "drift": ("drift_log_ga_check.py", "--window", "1", "--json"),
        "obs": ("observability_ga_check.py", "--window", "1", "--json"),
    }
    for name, (script, *rest) in judges.items():
        for label, histories, want_excluded in (("clean", clean, 0), ("dirty", dirty, 1)):
            proc = _run_script(script, *rest, "--history", str(histories[name]), env=env)
            # rc 不是本案例的受測對象（obs 在 -S 下沒有 autoclaude 可 import，emit_real=False，
            # 本來就不綠）；受測的是剔除數與計入筆數——它們只取決於 tree 欄。
            payload = json.loads(proc.stdout)
            assert payload["excluded_dirty"] == want_excluded, (name, label, proc.stdout)
            assert payload["total_records"] == 1 - want_excluded, (name, label, proc.stdout)


# ── DEF-101-887 R210 QA P2-1：nightly 自寫檔不算中間態；起跑態與採樣態同一套規則 ──────────


def test_the_nightlys_own_perf_baseline_rewrite_is_not_a_mid_state(repo: Path) -> None:
    """perf-baseline 階段的 perf_baseline_lock.py 幾乎每晚回寫 tracked 的
    AutoClaude/.perf_baseline.toml，而 drift／obs 兩個 collector 排在它後面——那是 nightly
    自己的產物，不是半成品樹；判成 dirty 會讓這兩軌近乎每晚被剔除（DEF-101-887）。"""
    baseline = repo / "AutoClaude" / ".perf_baseline.toml"
    baseline.parent.mkdir()
    baseline.write_text("p95_ms = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baseline")
    baseline.write_text("p95_ms = 2\n", encoding="utf-8")  # 模擬 perf_baseline_lock 回寫

    head = _git(repo, "rev-parse", "--short", "HEAD")
    got = tree_state.capture(repo, environ=_start(head, "clean"))
    assert (got["state"], got["dirty_entries"], got["valid"]) == ("clean", 0, True)

    # 對照組：真正的 WIP（任何別的 tracked 變更）仍然要算，且子目錄當 repo_dir 也一樣
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    for where in (repo, repo / "AutoClaude"):
        got = tree_state.capture(where, environ={})
        assert (got["state"], got["dirty_entries"], got["valid"]) == ("dirty", 1, False), where


def test_start_token_uses_the_same_dirty_rules_as_capture(repo: Path) -> None:
    """起跑態不是 ps1 自己另算一套：`start_token()` 與 `capture()` 同源（含自寫檔排除），
    否則週末沒回收前一晚 baseline 時起跑態就是 dirty、整晚樣本全被剔除（QA P3-14）。"""
    head = _git(repo, "rev-parse", "HEAD")
    assert tree_state.start_token(repo) == f"{head}|clean"
    baseline = repo / "AutoClaude" / ".perf_baseline.toml"
    baseline.parent.mkdir()
    baseline.write_text("p95_ms = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baseline")
    baseline.write_text("p95_ms = 2\n", encoding="utf-8")
    head2 = _git(repo, "rev-parse", "HEAD")
    assert tree_state.start_token(repo) == f"{head2}|clean"
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    assert tree_state.start_token(repo) == f"{head2}|dirty"
    # 起跑 token 餵回 capture：乾淨起跑＋乾淨採樣＝valid True（整條鏈路同一套規則）
    (repo / "tracked.txt").write_text("v1\n", encoding="utf-8")
    token = tree_state.start_token(repo)
    got = tree_state.capture(repo, environ={tree_state.START_ENV: token})
    assert (got["start_head"], got["start_state"], got["valid"]) == (head2, "clean", True)


def test_start_token_on_a_non_repo_is_unknown_not_a_crash(tmp_path: Path) -> None:
    assert tree_state.start_token(tmp_path / "nowhere") == "|unknown"


def test_cli_start_token_matches_the_library(repo: Path) -> None:
    """ps1 真的是用 CLI 拿起跑態：子行程輸出必須與函式回傳逐字相同、rc=0。"""
    proc = subprocess.run(
        [sys.executable, str(Path(tree_state.__file__)), "--start-token", "--repo-dir", str(repo)],
        capture_output=True, encoding="utf-8", errors="replace", check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == tree_state.start_token(repo)

