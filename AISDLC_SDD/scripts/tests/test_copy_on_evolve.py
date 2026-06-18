"""DEF-38-001 Copy-on-Evolve git-archive 版 helper 的意圖鎖（Rule 9：測 WHY 非僅 WHAT）。

WHY：
DEF-11-001 的 tar --exclude 版以「黑名單」剔除已知 runtime 產物，但 **--exclude 清單未含
`tools/fsm_runtime/formal/states/`**（TLC 每跑一次 dump 一個時間戳目錄）→ DEF-38-001：來源版
跑過 TLC 累積 states 時，tar 會把 bloat 一路搬運繼承（v0.05~v0.13 實證每版肥 19MB／5193 檔，
皆為從 v0.01 拖來的同一份副本）。系統性修復＝改用 `git archive HEAD:<path>`：結構上只輸出
git tracked（committed 於 HEAD）的內容，一切 untracked/gitignored runtime 產物
（build/reports、formal/states、arch-fitness.json、chaos-report.json、__pycache__、*.pyc）
**一律被排除**，免維護黑名單、永不因新 runtime 產物類型 bloat 回歸。tracked＝輸入、
untracked＝輸出，邊界由 git 單一事實源裁定。

本測試以 tmp 真實 git repo 鎖定該 helper 的 tracked-only 匯出意圖，退化即紅：
  1. tracked 源碼 → 匯出後必存在（防排除過頭誤殺源碼）；
  2. 未 commit 的 runtime 產物 → 結構性不在匯出（git archive 只認 HEAD tree）；
  3. **DEF-38-001 核心**：未 commit 的 `tools/fsm_runtime/formal/states/` → 不在匯出
     （tar 版正是漏了這條才 bloat）；
  4. tracked FSM-STATE-TEMPLATE.yaml（DEF-15-001 種子模板真輸入）→ 必保留（tracked⇒kept）；
  5. 拒絕覆蓋既有目標 → exit 1；來源不存在 → exit 1；參數數不對 → exit 2；
     來源存在但未 tracked 於 HEAD → exit 1（git archive 版專屬防呆）。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# scripts/tests/ → scripts/ → AISDLC_SDD
REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "copy_on_evolve.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("tar") is None or shutil.which("git") is None,
    reason="copy_on_evolve.sh 為 bash 腳本且依賴 git archive + GNU tar",
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.email=t@t.dev", "-c", "user.name=coe-test", *args],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """以 cwd=tmp repo 跑 helper；git archive 依該 repo 的 HEAD 樹匯出。

    helper 先複製進 repo 根、以**相對路徑**從 cwd 呼叫——避開 Windows 絕對路徑經
    subprocess→bash 的 drive-letter（D:/…）/ 反斜線掛載差異（沿用原測試「走相對路徑」策略）。
    helper 副本置於 repo 根、不在被匯出的版本子樹內，不影響 git archive 結果。
    """
    local = repo / "_coe.sh"
    if not local.exists():
        shutil.copy(str(HELPER), str(local))
    return subprocess.run(
        ["bash", "_coe.sh", *args],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60,
    )


@pytest.fixture
def repo():
    """與 REPO_ROOT 同碟的暫存 git repo（init + 一個 baseline commit 使 HEAD 存在）。"""
    d = Path(tempfile.mkdtemp(prefix=".coe_tmp_", dir=str(REPO_ROOT)))
    _git(d, "init", "-q")
    (d / ".seed").write_text("seed\n", encoding="utf-8")
    _git(d, "add", ".seed")
    _git(d, "commit", "-q", "-m", "baseline")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _make_committed_source(repo: Path) -> Path:
    """造合成版本目錄：tracked 真源碼先 commit；runtime 產物於 commit 後建立＝untracked。"""
    src = repo / "AISDLC_SDD_vTEST"
    # ── 真源碼（tracked，必保留）──
    (src / "agent" / "core").mkdir(parents=True)
    (src / "agent" / "core" / "foo.yaml").write_text("role: foo\n", encoding="utf-8")
    (src / "tools").mkdir(parents=True)
    (src / "tools" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (src / "build" / "planning" / "active").mkdir(parents=True)
    (src / "build" / "planning" / "active" / "rfc.md").write_text("# rfc\n", encoding="utf-8")
    (src / "build" / "logs").mkdir(parents=True)
    (src / "build" / "logs" / "README.md").write_text("# logs\n", encoding="utf-8")
    # DEF-15-001：FSM 種子模板＝真輸入，在 tracked 源碼位（v0.13+ 佈局）
    (src / "tools" / "fsm_runtime" / "templates").mkdir(parents=True)
    (src / "tools" / "fsm_runtime" / "templates" / "FSM-STATE-TEMPLATE.yaml").write_text(
        "current_state: INIT\n", encoding="utf-8"
    )
    _git(repo, "add", "AISDLC_SDD_vTEST")
    _git(repo, "commit", "-q", "-m", "framework source")
    # ── runtime 產物（commit 後才建立＝untracked，git archive 必排除）──
    (src / "build" / "reports" / "fsm").mkdir(parents=True)
    (src / "build" / "reports" / "fsm" / "FSM-STATE-x.yaml").write_text("s: 1\n", encoding="utf-8")
    (src / "build" / "reports" / "abort").mkdir(parents=True)
    (src / "build" / "reports" / "abort" / "ABORT-1.md").write_text("abort\n", encoding="utf-8")
    # DEF-38-001 核心：TLC formal/states dump（tar 版漏排除者）
    states = src / "tools" / "fsm_runtime" / "formal" / "states" / "26-01-01-00-00-00.000"
    states.mkdir(parents=True)
    (states / "dump.st").write_text("state\n", encoding="utf-8")
    (src / "arch-fitness.json").write_text("{}\n", encoding="utf-8")
    (src / "chaos-report.json").write_text("{}\n", encoding="utf-8")
    (src / "tools" / "__pycache__").mkdir(parents=True)
    (src / "tools" / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\x00")
    (src / "a" / "b").mkdir(parents=True)
    (src / "a" / "b" / "deep.pyc").write_bytes(b"\x00")
    return src


def test_helper_exists():
    assert HELPER.is_file(), f"helper 不存在：{HELPER}"


def test_archive_keeps_tracked_excludes_untracked_runtime(repo: Path):
    _make_committed_source(repo)
    proc = _run(repo, "AISDLC_SDD_vTEST", "AISDLC_SDD_vNEW")
    assert proc.returncode == 0, f"helper 非零退出：{proc.returncode}\n{proc.stderr}"
    dst = repo / "AISDLC_SDD_vNEW"

    # tracked 真源碼必保留
    assert (dst / "agent" / "core" / "foo.yaml").is_file()
    assert (dst / "tools" / "mod.py").is_file()
    assert (dst / "build" / "planning" / "active" / "rfc.md").is_file()
    assert (dst / "build" / "logs" / "README.md").is_file()

    # untracked runtime 產物結構性排除
    assert not (dst / "build" / "reports" / "fsm" / "FSM-STATE-x.yaml").exists()
    assert not (dst / "build" / "reports" / "abort").exists()
    assert not (dst / "arch-fitness.json").exists()
    assert not (dst / "chaos-report.json").exists()
    assert not (dst / "tools" / "__pycache__").exists()
    assert not (dst / "a" / "b" / "deep.pyc").exists()


def test_excludes_formal_states_def_38_001(repo: Path):
    """DEF-38-001 核心：未 commit 的 tools/fsm_runtime/formal/states/ 必不入匯出。

    tar --exclude 版正因 --exclude 清單漏了 formal/states，致 TLC dump 被一路搬運繼承
    （v0.05~v0.13 每版 19MB／5193 檔同一坨）。git archive 只認 HEAD tree → 結構性排除。
    退化（改回會搬運 untracked 的複製法）→ 本 assert 即紅。
    """
    src = _make_committed_source(repo)
    assert (src / "tools" / "fsm_runtime" / "formal" / "states").exists(), "前置：來源確有 states"
    proc = _run(repo, "AISDLC_SDD_vTEST", "AISDLC_SDD_vNEW")
    assert proc.returncode == 0, proc.stderr
    dst = repo / "AISDLC_SDD_vNEW"
    assert not (dst / "tools" / "fsm_runtime" / "formal" / "states").exists(), \
        "formal/states/ TLC dump 未被排除（DEF-38-001 bloat 回歸）"


def test_preserves_fsm_state_template(repo: Path):
    """DEF-15-001：tracked 的 FSM-STATE-TEMPLATE.yaml 種子模板（真輸入）必保留。

    git archive 版以「tracked⇒kept」自然涵蓋——無需 tar 版的「排除後補回」特例。
    退化（種子模板未 tracked / 被誤排除）→ FSM runtime 無法 bootstrap，本 assert 即紅。
    """
    _make_committed_source(repo)
    proc = _run(repo, "AISDLC_SDD_vTEST", "AISDLC_SDD_vNEW")
    assert proc.returncode == 0, proc.stderr
    tmpl = repo / "AISDLC_SDD_vNEW" / "tools" / "fsm_runtime" / "templates" / "FSM-STATE-TEMPLATE.yaml"
    assert tmpl.is_file(), "FSM-STATE-TEMPLATE.yaml 種子模板未保留（DEF-15-001 回歸）"
    assert tmpl.read_text(encoding="utf-8") == "current_state: INIT\n", "模板內容應原樣保留"


def test_refuses_existing_target(repo: Path):
    _make_committed_source(repo)
    (repo / "AISDLC_SDD_vNEW").mkdir()
    proc = _run(repo, "AISDLC_SDD_vTEST", "AISDLC_SDD_vNEW")
    assert proc.returncode == 1, "目標已存在應 exit 1（拒絕覆蓋）"
    assert "已存在" in proc.stderr


def test_missing_source(repo: Path):
    proc = _run(repo, "nope", "AISDLC_SDD_vNEW")
    assert proc.returncode == 1, "來源不存在應 exit 1"
    assert "不存在" in proc.stderr


def test_untracked_source_rejected(repo: Path):
    """git archive 版專屬防呆：來源目錄存在但未 commit 於 HEAD → exit 1（不可匯出 untracked）。"""
    (repo / "AISDLC_SDD_vUNTRACKED").mkdir()
    (repo / "AISDLC_SDD_vUNTRACKED" / "x.py").write_text("x=1\n", encoding="utf-8")
    proc = _run(repo, "AISDLC_SDD_vUNTRACKED", "AISDLC_SDD_vNEW")
    assert proc.returncode == 1, "未 tracked 來源應 exit 1"
    assert "tracked" in proc.stderr.lower() or "未被 git" in proc.stderr


def test_wrong_arg_count(repo: Path):
    proc = _run(repo, "only-one-arg")
    assert proc.returncode == 2, "參數數不對應 exit 2"
    assert "用法" in proc.stderr
