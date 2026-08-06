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

R56 追加三條跨平台（macOS ⇄ Windows 11）迴歸鎖（見檔尾同名區塊的完整 WHY）：
  6. 建版產物須遵守 repo 行尾政策（`.ps1`→CRLF、`.sh`→LF），且行尾**只能是 HEAD 的函式**
     ——修法＝版本子樹自帶 `.gitattributes`（自我傳播），非 `--worktree-attributes`；
  7. 生產佈局下 LATEST 版目錄須自帶且已入庫該 `.gitattributes`（第 6 條的根因側鎖）；
  8. 共用 WindowsApps guard 的相對路徑在**真實 monorepo 佈局**下必須真的指到檔案
     （dot-source 區塊刻意 fail-open，路徑寫錯與隔離環境對腳本長得一模一樣）。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from scripts import bash_probe, sdd_version  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

# scripts/tests/ → scripts/ → AISDLC_SDD
REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "copy_on_evolve.sh"

# WSL 佔位 bash（System32）吃不下 Windows 路徑引數 → 紅燈而非 skip（第五輪 DEF-101 P3）
_BASH_PLAIN = bash_probe.usable_bash()

pytestmark = pytest.mark.skipif(
    _BASH_PLAIN is None or shutil.which("tar") is None or shutil.which("git") is None,
    reason="copy_on_evolve.sh 為 bash 腳本（需可用 bash，非 WSL 佔位）且依賴 git archive + GNU tar",
)


def _clean_git_env() -> dict[str, str]:
    """清洗 GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE 後的環境（P0 防真 repo 污染）。

    linked worktree 下 git 對 pre-push hook 注入絕對路徑 GIT_DIR（hook 又補
    GIT_WORK_TREE），若傳染進本檔的 git init/add/commit 與 helper 內的 git archive，
    cwd=tmp 會被這些 env 覆寫 → 改操作「使用者真 repo」（偷 commit WIP / 閘門假紅）。"""
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    return env


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.email=t@t.dev", "-c", "user.name=coe-test", *args],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_clean_git_env(),
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
        [_BASH_PLAIN, "_coe.sh", *args],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, env=_clean_git_env(),
    )


@pytest.fixture
def repo():
    """暫存 git repo（init + 一個 baseline commit 使 HEAD 存在）。

    建於**系統暫存目錄**（非 REPO_ROOT 內）——git-archive 版 helper 全程走相對路徑（helper 複製進
    repo、以 cwd 相對呼叫），不再需「與 REPO_ROOT 同碟」；且若 Windows 下 git handle 鎖住致
    teardown 的 rmtree 失敗而洩漏，殘留落在系統暫存（OS 自清），**絕不污染 repo 工作樹**
    （舊版用 dir=REPO_ROOT 曾洩漏 49 個 .coe_tmp_* 進 AISDLC_SDD/）。
    """
    d = Path(tempfile.mkdtemp(prefix="coe_test_"))
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


# ── DEF-58-002（P1 根因）：建版後自動同步框架版本戳記 + 父層鏡像 ──────────────────────
_PROBE_READY = "COE-BASH-READY"
# 三段皆為外部指令（非 shell builtin），任一缺席即代表該 bash 的 PATH 不含 coreutils／python
_PROBE_CMD = (
    "command -v python >/dev/null && command -v mkdir >/dev/null "
    f"&& command -v dirname >/dev/null && echo {_PROBE_READY}"
)


def _bash_with_python() -> str | None:
    """解析一個「PATH 同時含 python 與 coreutils」的 bash。

    WHY：本測試的 auto-sync 步驟需在 bash 內呼叫 python，而 `copy_on_evolve.sh` 自己要用
    `mkdir`／`dirname` 等 coreutils；Windows 上裸 `bash` 常解析到 WSL bash（環境隔離、無
    Windows python）。**候選順序與驗活條件都是本函式曾經踩過的坑**：

    - 本輪實測，Git 安裝樹下 `usr/bin/bash.exe` 與 `bin/bash.exe` **兩支都存在**，但只有後者
      會把 Git 的 `/usr/bin` 併進 PATH。前者繼承 Windows PATH ⇒ `command -v python` 照樣成功，
      於是舊版「只探 python、且把 `usr/bin` 排在前面」的邏輯必然選中它，腳本一跑到
      `mkdir` 就 rc=127（`mkdir: command not found`），三支 DEF 意圖鎖同時假紅。
    - 修法＝**先用 SSOT** `scripts/bash_probe.usable_bash()` 的結果（它已驗過 coreutils，
      DEF-101-275），再以 git 相鄰候選補位、且 `bin/` 優先於 `usr/bin/`；每個候選都必須同時
      通過 python 與 coreutils 探測才回傳。同一份「哪支 bash 能用」的知識不再有第二個家。

    皆無則 None（→ 環境 gated skip，對齊既有 bash/tar/git skipif 慣例）。
    CI（Linux）裸 bash 即含 python 與 coreutils。
    """
    candidates: list[str] = []
    # 裸 bash 只在非 WSL 佔位（System32）時列為候選——WSL bash 的 python 是 WSL 側的，
    # 跑不了 Windows 路徑引數（第五輪 DEF-101 P3）。此處直接吃 bash_probe 的裁決，不重寫判準。
    if _BASH_PLAIN is not None:
        candidates.append(_BASH_PLAIN)
    git = shutil.which("git")
    if git:
        gp = Path(git).resolve()
        for up in list(gp.parents)[:4]:
            for sub in ("bin/bash.exe", "usr/bin/bash.exe"):
                c = up / sub
                if c.exists() and str(c) not in candidates:
                    candidates.append(str(c))
    for b in candidates:
        try:
            r = subprocess.run([b, "-c", _PROBE_CMD], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=15)
            if r.returncode == 0 and r.stdout.strip() == _PROBE_READY:
                return b
        except Exception:
            continue
    return None


_SYNC_SCRIPTS = (
    "copy_on_evolve.sh",
    "skill_header_sync.py",
    "sync_exposed_skills.py",
    "rfc_lifecycle_lint.py",  # skill_header_sync / sync_exposed / framework_status 皆 import discover_frozen_versions
    "framework_status_snapshot.py",  # DEF-96-001：建版後重生 FRAMEWORK_STATUS.md SSOT
)


def _setup_version_repo_with_scripts(repo: Path) -> None:
    """於 tmp repo 佈署真實 scripts/ 4 腳本 + 一個 v0.01 版本目錄（含帶 v0.01 戳記的 SKILL.md），
    全部 commit。版本目錄採真實 `AISDLC_SDD_v0.0X` 樣式（discover_frozen_versions 之 VERSION_RE
    要求數字版），使 skill_header_sync/sync_exposed 能在 tmp 基底辨識 LATEST。"""
    (repo / "scripts").mkdir()
    for name in _SYNC_SCRIPTS:
        shutil.copy(str(REPO_ROOT / "scripts" / name), str(repo / "scripts" / name))
    skill_dir = repo / "AISDLC_SDD_v0.01" / ".claude" / "skills" / "foo"
    skill_dir.mkdir(parents=True)
    # footer 戳記須對齊所在版本目錄；建版繼承後應被自動改寫為新版
    (skill_dir / "SKILL.md").write_text(
        "# Foo Skill\n\n內容\n\n---\n**基於**: AISDLC-SDD v0.01\n", encoding="utf-8"
    )
    _git(repo, "add", "scripts", "AISDLC_SDD_v0.01")
    _git(repo, "commit", "-q", "-m", "scripts + v0.01 framework")


def test_auto_syncs_skill_stamps_on_evolve_def_58_002(repo: Path):
    """DEF-58-002 意圖鎖：copy_on_evolve 建出 v0.02 後，必自動同步 skill 戳記至 v0.02。

    WHY：git archive 逐字繼承來源 v0.01 的 `**基於**: AISDLC-SDD v0.01` 戳記；若不自動
    skill_header_sync --write，戳記停在 v0.01 → ci-gate 之 skill_header_sync --check 必紅
    （DEF-CLDREV-007@v0.19、DEF-58-001@v0.22 兩度實證人工漏跑帶紅入庫）。本測試鎖「建版即
    同步」——移除硬化（auto-sync 區塊）→ 新版戳記停 v0.01，本 assert 立即轉紅。
    """
    bash = _bash_with_python()
    if bash is None:
        pytest.skip("找不到 PATH 內含 python 的 bash（WSL bash 無 Windows python）")
    _setup_version_repo_with_scripts(repo)
    proc = subprocess.run(
        [bash, "scripts/copy_on_evolve.sh", "AISDLC_SDD_v0.01", "AISDLC_SDD_v0.02"],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, env=_clean_git_env(),
    )
    assert proc.returncode == 0, f"建版+同步應 exit 0\nstdout:{proc.stdout}\nstderr:{proc.stderr}"
    new_skill = repo / "AISDLC_SDD_v0.02" / ".claude" / "skills" / "foo" / "SKILL.md"
    assert new_skill.is_file(), "新版 SKILL.md 應存在"
    body = new_skill.read_text(encoding="utf-8")
    assert "**基於**: AISDLC-SDD v0.02" in body, \
        f"戳記未自動同步至 v0.02（仍停 v0.01＝DEF-58-001 帶紅入庫回歸）\n{body}"
    assert "v0.01" not in body, "v0.01 戳記不應殘留"
    # 父層鏡像（sync_exposed_skills --write）亦應重生
    mirror = repo / ".claude" / "skills" / "foo" / "SKILL.md"
    assert mirror.is_file(), "父層曝光 skills 鏡像應隨建版重生"
    assert "**基於**: AISDLC-SDD v0.02" in mirror.read_text(encoding="utf-8")


def test_auto_appends_gitignore_block_on_evolve_def_59_001(repo: Path):
    """DEF-59-001 意圖鎖：copy_on_evolve 建出 v0.02 後，必自動補 v0.02 的 .gitignore runtime 產物 block。

    WHY：新版 build/reports/ / arch-fitness.json / chaos-report.json 為 untracked runtime 產物；
    若不自動補 BASE/.gitignore 排除 block，ci-gate 的 gitignore 覆蓋 lint（DEF-37-001，
    test_gitignore_coverage_lint.py::test_real_repo_latest_covered）對 LATEST 失效報紅
    （improving_59 建 v0.23 即實證人工漏補帶紅）。與 DEF-58-002 戳記同步**同根因家族**。
    移除硬化（auto-append 區塊）→ 新版 block 不存在，本 assert 立即轉紅。並驗 block 不重複。
    """
    bash = _bash_with_python() or _BASH_PLAIN
    if bash is None:
        pytest.skip("找不到可用 bash")
    _setup_version_repo_with_scripts(repo)
    gitignore = repo / ".gitignore"
    gitignore.write_text(
        "# tmp gitignore\nAISDLC_SDD_v0.01/build/reports/\n", encoding="utf-8"
    )
    proc = subprocess.run(
        [bash, "scripts/copy_on_evolve.sh", "AISDLC_SDD_v0.01", "AISDLC_SDD_v0.02"],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, env=_clean_git_env(),
    )
    assert proc.returncode == 0, f"建版應 exit 0\nstdout:{proc.stdout}\nstderr:{proc.stderr}"
    gi = gitignore.read_text(encoding="utf-8")
    assert "AISDLC_SDD_v0.02/build/reports/" in gi, \
        f"未自動補 v0.02 .gitignore block（DEF-59-001 帶紅入庫回歸）\n{gi}"
    assert "AISDLC_SDD_v0.02/arch-fitness.json" in gi
    assert "AISDLC_SDD_v0.02/chaos-report.json" in gi
    assert gi.count("AISDLC_SDD_v0.02/build/reports/") == 1, "block 不應重複 append"


def test_auto_regens_framework_status_on_evolve_def_96_001(repo: Path):
    """DEF-96-001 意圖鎖：copy_on_evolve 建出 v0.02 後，必自動重生 FRAMEWORK_STATUS.md 並指向 v0.02 為 LATEST。

    WHY：framework_status_snapshot.py 算「最新演化版（LATEST＝rfc_lifecycle_lint 磁碟掃描語意，
    剛建的未 add 新版亦被選中）」版本號/計數生成
    SSOT；新版一建立 LATEST 即變 → 既有 FRAMEWORK_STATUS.md stale → ci-gate 之
    framework_status_snapshot --check 必紅（improving_96 建 v0.29 即實證人工漏跑帶紅、手動 --write
    後才綠）。與 DEF-58-002 戳記、DEF-59-001 .gitignore **同根因家族**「人工後步驟＝必然遺忘」。
    本測試鎖「建版即重生 SSOT」——移除硬化（第三 auto-sync 區塊）→ 新版不被認列為 LATEST，本
    assert 立即轉紅。
    """
    bash = _bash_with_python()
    if bash is None:
        pytest.skip("找不到 PATH 內含 python 的 bash（WSL bash 無 Windows python）")
    _setup_version_repo_with_scripts(repo)
    proc = subprocess.run(
        [bash, "scripts/copy_on_evolve.sh", "AISDLC_SDD_v0.01", "AISDLC_SDD_v0.02"],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, env=_clean_git_env(),
    )
    assert proc.returncode == 0, f"建版+重生 SSOT 應 exit 0\nstdout:{proc.stdout}\nstderr:{proc.stderr}"
    status = repo / "FRAMEWORK_STATUS.md"
    assert status.is_file(), "建版後 FRAMEWORK_STATUS.md 應於 BASE 自動重生（DEF-96-001 帶紅入庫回歸）"
    body = status.read_text(encoding="utf-8")
    # render() 的「最新演化版」行格式：`...最新演化版（...）**：`AISDLC_SDD_v0.02``
    assert "AISDLC_SDD_v0.02" in body, \
        f"FRAMEWORK_STATUS.md 未認列新版 v0.02 為 LATEST（SSOT 未隨建版重生）\n{body}"
    # idempotent 兼證：腳本輸出確有重生步驟（非靜默略過）
    assert "framework_status_snapshot" in proc.stdout or "FRAMEWORK_STATUS" in proc.stdout, \
        f"建版輸出應含 SSOT 重生步驟\n{proc.stdout}"


# ── R56（跨平台複審 Architect）：行尾政策由「版本子樹自帶 .gitattributes」達成 ────────
def test_archive_applies_eol_policy_head_pure(repo: Path):
    """R56 意圖鎖：建版產物的 `.ps1` 必為 CRLF、`.sh` 必為 LF，**且行尾只能是 HEAD 的函式**。

    WHY（缺陷本體）：`git archive HEAD:<subtree>` 的 attribute 查找基準是**被匯出的那棵樹**。
    版本目錄若不自帶 `.gitattributes`，父層 `AISDLC_SDD/.gitattributes` 的
    `*.ps1 text eol=crlf` 完全不參與 → 直接吐 blob 原始 LF：本 repo 的**官方版本產生器**
    每次都產出違反自家政策的 LF `.ps1`（v0.30 實測 4 支），Windows 原生 PowerShell 取到的
    新版腳本行尾與工作樹其餘 `.ps1` 不一致。雙端失明：本機 `git status` 因 checkin 正規化
    （CRLF→LF blob）看不出差異、CI 是全新 checkout（smudge 已套用）也結構性看不到。

    WHY（為何是這個修法，而非 `--worktree-attributes`）：修法＝讓版本子樹**自帶**
    `.gitattributes`（隨 git archive 自我傳播到每個新版，永久免旗標）。`--worktree-attributes`
    的語意正是「改以**工作樹**的 .gitattributes 查找」，會把匯出行尾變成工作樹狀態的函式，
    與 copy_on_evolve.sh 第 15/23 行明文宣告、並由 `HEAD:$FROM_REL` 硬閘強制的核心不變式
    「匯出＝HEAD 的純函式」直接衝突（而該腳本對 .gitattributes 是否已 commit 毫無對應的閘）。

    鑑別力（兩種退化各自轉紅）：
      * 版本子樹的 `.gitattributes` 遺失／未 commit → 匯出退回 LF → CRLF 斷言紅；
      * `--worktree-attributes` 回歸 → 改讀下方**刻意未 commit 的敵意根層 .gitattributes**
        （`*.ps1 eol=lf`）→ 匯出變 LF → 同一條 CRLF 斷言紅。
    另斷言匯出含 `.gitattributes` 本體＝自我傳播鏈不斷（新版仍免旗標）。
    """
    src = repo / "AISDLC_SDD_vTEST"
    (src / "tools").mkdir(parents=True)
    # 版本子樹自帶行尾政策（＝生產修法的最小同構：AISDLC_SDD_v0.30/.gitattributes）
    (src / ".gitattributes").write_text(
        "* text=auto eol=lf\n*.sh        text eol=lf\n*.ps1       text eol=crlf\n",
        encoding="utf-8",
    )
    # 以工作樹政策形狀寫入（.ps1 CRLF / .sh LF）；git add 會把 blob 正規化為 LF，
    # 故「匯出後 .ps1 是否為 CRLF」純由 archive 的 attribute 查找決定。
    (src / "tools" / "w.ps1").write_bytes(b"Write-Host 'hi'\r\n")
    (src / "tools" / "u.sh").write_bytes(b"echo hi\n")
    _git(repo, "add", "AISDLC_SDD_vTEST")
    _git(repo, "commit", "-q", "-m", "eol policy source")
    # 敵意工作樹狀態：**刻意不 commit**（HEAD 不含之）。無旗標時 archive 完全看不到它；
    # 一旦 --worktree-attributes 回歸即會讀到並把 .ps1 改成 LF ⇒ 純函式不變式的注入探針。
    (repo / ".gitattributes").write_text(
        "* text=auto eol=lf\n*.ps1       text eol=lf\n", encoding="utf-8"
    )

    proc = _run(repo, "AISDLC_SDD_vTEST", "AISDLC_SDD_vNEW")
    assert proc.returncode == 0, f"helper 非零退出：{proc.returncode}\n{proc.stderr}"
    new = repo / "AISDLC_SDD_vNEW"
    ps1 = (new / "tools" / "w.ps1").read_bytes()
    sh = (new / "tools" / "u.sh").read_bytes()
    assert b"\r\n" in ps1, (
        "建版產物 .ps1 為 LF，違反 `*.ps1 text eol=crlf`——兩種退化之一："
        "(a) 版本子樹的 .gitattributes 遺失/未 commit（HEAD:<subtree> 查不到政策）；"
        "(b) git archive 被加回 --worktree-attributes（改讀未 commit 的工作樹政策，"
        "匯出不再是 HEAD 的純函式）"
    )
    assert b"\r" not in sh, (
        "建版產物 .sh 混入 CR，違反 `*.sh text eol=lf`"
        "（Linux/Docker/act 下 CRLF 會噴 `bash: $'\\r': command not found`）"
    )
    assert (new / ".gitattributes").is_file(), (
        "新版未繼承 .gitattributes ⇒ 自我傳播鏈斷裂，下一輪 Copy-on-Evolve 會退回 LF .ps1"
    )


def test_latest_version_carries_own_gitattributes():
    """R56 意圖鎖（生產佈局）：LATEST 版目錄須**自帶且已入庫**的 `.gitattributes`。

    WHY：上一條測試證明「子樹自帶政策 ⇒ 匯出行尾正確」，但那是在 tmp repo 內自造的；
    真實建版的行尾正確性取決於**真實 LATEST 版目錄裡有這個檔且進得了 HEAD tree**
    （`git archive HEAD:<subtree>` 只認 committed 內容）。缺了它，建版靜默退回 LF `.ps1`
    而所有既有閘門全綠（雙端失明，見上一條 WHY）。此鎖即針對該根因：檔案被刪、
    或新版目錄以別的方式（非 Copy-on-Evolve 自我傳播）建立而漏帶，立即轉紅。
    """
    latest = sdd_version.latest_version_name(REPO_ROOT, warn=lambda _m: None)
    assert latest, "無法解析 LATEST 版本目錄（sdd_version SSOT）"
    rel = f"{latest}/.gitattributes"
    ga = REPO_ROOT / rel
    assert ga.is_file(), (
        f"LATEST 版目錄缺 .gitattributes：{ga}——git archive 'HEAD:<版本子樹>' 的 attribute "
        "查找基準是該子樹，缺此檔則父層 `*.ps1 text eol=crlf` 完全不參與，建版產物的 .ps1 "
        "靜默退回 LF（Windows 原生 PowerShell 端行尾不一致）"
    )
    tracked = _git(REPO_ROOT, "ls-files", "--error-unmatch", "--", rel)
    assert tracked.returncode == 0, (
        f"{rel} 未被 git tracked ⇒ 進不了 HEAD tree ⇒ git archive 看不到它，"
        f"行尾政策等同不存在：\n{tracked.stderr}"
    )
    body = ga.read_text(encoding="utf-8")
    assert re.search(r"^\*\.ps1\s+text\s+eol=crlf\s*$", body, re.MULTILINE), \
        f"{rel} 缺 `*.ps1 text eol=crlf`（Windows 原生 PowerShell 行尾政策）"
    assert re.search(r"^\*\.sh\s+text\s+eol=lf\s*$", body, re.MULTILINE), \
        f"{rel} 缺 `*.sh text eol=lf`（Linux/Docker/act 下 CRLF 會噴 $'\\r' 錯誤）"


# ── R56（跨平台複審 QA）：WindowsApps guard 接線在「生產形狀」下的路徑迴歸鎖 ────────
def test_windowsapps_guard_path_resolves_in_production_layout():
    """R56 意圖鎖：copy_on_evolve.sh 頭部算出的共用 guard 路徑，在真實 monorepo 佈局下
    必須真的指到檔案。

    WHY：該 dot-source 區塊是**刻意 fail-open** 的降級設計（隔離 harness 無完整 monorepo
    `tools/lib/` 結構時只 warn 不中止；此設計本身正確，不在此質疑）。但代價是「路徑寫錯」
    與「隔離環境」對腳本而言長得一模一樣——把 `../../` 誤寫成 `../../../`（scripts/ 搬家或
    monorepo 層級調整的最寫實形狀，字面值 `windowsapps_guard.sh` 完好無損）時 guard 靜默
    失守，腳本照常走到 `_PY="${PYTHON:-python}"`；Windows 11 上 WindowsApps 空殼排 PATH
    前面即直接執行 Store 別名空殼，建版後三個同步 block 產物靜默毀損。

    既有防護對此形狀全數失明（R56 QA bug-injection 實測五組全綠）：本檔其餘測試一律在
    隔離 tmp repo 內跑（恆走 fail-open 分支，對真實路徑零鑑別力）；根層
    `tools/tests/test_windowsapps_guard_bash_parity.py` 的 `_has_ssot_guard` 是**文字**掃描
    （只認關鍵字出現在非註解行，不解析路徑是否可解析）。

    本測試以**生產形狀**（真實檔案位置、如檔頭用法般以 repo 根相對路徑呼叫）跑腳本並停在
    參數數檢查（早於任何 git 操作＝零副作用、不建任何目錄），斷言 stderr 不含 fail-open
    降級警告。

    🔴 路徑一律走 **posix 相對**形狀（＝copy_on_evolve.sh 檔頭第 5 行的官方用法，亦與本檔
    `_run()` / ci-gate.ps1 慣例一致），**不可**改成 `str(HELPER)`：Windows 上那是反斜線絕對
    路徑，Git Bash 的 `dirname`（純字彙比對、只認 `/`）會回 `.` → 腳本第 36 行的
    `cd "$(dirname "${BASH_SOURCE[0]}")" && pwd` 解析成 cwd（＝AISDLC_SDD）而非 scripts/ →
    `../../tools/lib/` 指到 monorepo 根**的上一層** → 反而觸發本測試要抓的 fail-open 警告，
    以「看似 guard 失守」的假紅打紅 windows-smoke 閘門（R56 SA 機械取證）。
    """
    guard = REPO_ROOT.parent / "tools" / "lib" / "windowsapps_guard.sh"
    assert guard.is_file(), (
        f"共用 guard 不在預期位置：{guard}"
        "——monorepo 佈局變動時必須同步 copy_on_evolve.sh 內的相對路徑"
    )
    proc = subprocess.run(
        [_BASH_PLAIN, "scripts/copy_on_evolve.sh"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, env=_clean_git_env(),
    )
    assert proc.returncode == 2, (
        f"零引數應停在參數數檢查 exit 2（確保本測試零副作用）：rc={proc.returncode}\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
    assert "windowsapps_guard.sh" not in proc.stderr and "略過 WindowsApps" not in proc.stderr, (
        "copy_on_evolve.sh 在真實 monorepo 佈局下仍落入 fail-open 降級分支＝共用 WindowsApps "
        f"guard 路徑失效（guard 靜默失守，Windows 11 上會直接執行 Store 空殼）：\n{proc.stderr}"
    )
