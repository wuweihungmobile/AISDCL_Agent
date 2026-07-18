# enforces (governance rules): R-9.17
"""install_post_commit.sh 路徑解析回歸鎖 — 一般 checkout ＋ git worktree 兩情境.

WHY（Rule 9 — 鎖意圖非僅行為）：
commit 7162959 修復 `install_post_commit.sh`／`.ps1` 在 git worktree 下的路徑解析
bug：worktree 的 `<worktree>/.git` 是指向主 repo 的純文字檔（非目錄），若沿用硬編碼
`$REPO_ROOT/.git/hooks/post-commit`（`$REPO_ROOT` 在 worktree 內＝worktree 自身
toplevel），`cat > .../post-commit` 會因路徑中途元件（`.git`）是檔案而非目錄而寫入
失敗。修復改用 `git rev-parse --path-format=absolute --git-common-dir` 正確解回
主 repo 真正共用的 `.git/hooks/`。

`.ps1` 版本已有 `.github/workflows/windows-compat-ci.yml` 的 git-worktree 實跑測試
鎖住此修復；但 `.sh` 版本完全零自動化覆蓋——`root-infra-ci.yml` 對 `.sh` 只做
`bash -n` 語法檢查（不執行邏輯），且其 `find tools -type f ...` 掃描範圍本不涵蓋
`AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.sh` 這個路徑。
兩位審查者（SA/QA）皆手動於 macOS 驗證過修復正確，但一致指出這只是一次性人工驗證、
非機器化回歸防護——下次若有人改動 `.sh` 版重新引入路徑解析 bug，不會有任何自動化
訊號攔下。本檔補上對等的機械回歸鎖。

位置說明（相對於任務原始建議路徑 `tools/tests/` 的偏離，需在此明確記錄）：
任務原始建議把本檔放在 `AISDLC_SDD_v0.30/tools/tests/`，但實測驗證（`--collect-only`）
確認該目錄**不會**被既有 CI 自動收集——`scripts/ci-gate.sh`（`aisdlc-sdd-ci.yml` 呼叫
的唯一入口）對每個框架版本只顯式跑 `python -m pytest tools/fsm_runtime/tests/
-m "not chaos" -q`，另外只跑一次版本無關的 `scripts/tests/`，兩者都不含
`AISDLC_SDD_v0.30/tools/tests/`。為了真正落實任務目標「在既有 aisdlc-sdd-ci.yml
（ubuntu-latest）上自動被收集執行、不需改動任何 CI YAML」，本檔改放在
`tools/fsm_runtime/tests/`（ci-gate.sh 對本版本顯式執行的既有路徑），零 CI/腳本
改動即可生效。`windows-compat-ci.yml` 的 `windows-nightly-full`（continue-on-error，
非阻斷）也會額外把本檔跑一遍，故加了 WSL 佔位 bash 的 skip 防線（見
`scripts/bash_probe.usable_bash`）。

三道防線：
1. `test_install_writes_hook_in_plain_checkout`：一般（非 worktree）checkout 下，
   hook 正確寫入 `.git/hooks/post-commit`、可執行、內容含兩支 advisory hook 路徑。
2. `test_install_writes_hook_to_shared_git_dir_from_worktree`：本檔核心情境——linked
   worktree 下，斷言 (a) 腳本 exit 0、(b) hook 寫入**主 repo**共用 `.git/hooks/post-commit`
   （而非 worktree 自己的 `.git`，那本來就不是目錄）、(c) hook 內容正確、非 ASCII
   路徑片段未被亂碼污染（無 U+FFFD 替代字元 / 無 `?` 替代字元）。2026-07-16 訂正：
   非 ASCII 路徑改建在**主 checkout 自身**（而非 worktree 目錄名）——P1 修復（見下方）
   之後來源路徑解回主 checkout，worktree 名稱不再出現在 hook 內容中，另補一條斷言
   鎖死「hook 內容不應含 worktree 自身路徑」以固定修復意圖。
3. 退回硬編碼寫法的回歸重現驗證：因無法對 tracked 檔案做「改壞再測」而不留痕，
   已改於 scratch 副本人工驗證（非本檔內容，見任務完成報告），確認退回舊寫法時
   `test_install_writes_hook_to_shared_git_dir_from_worktree` 會如預期失敗。
"""
from __future__ import annotations

import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

# 本檔 → fsm_runtime/tests → fsm_runtime → tools（此版本目錄下）
_TOOLS_DIR = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = _TOOLS_DIR / "install_hooks" / "install_post_commit.sh"

# 可用 bash 偵測（Windows 上常見的 WSL 佔位 `System32\bash.exe` 視為不可用）改用
# AISDLC_SDD/scripts/bash_probe.py 共用 helper（DEF-101-068(c) 樣板去重，非本檔獨立重寫）。
# 本檔 → fsm_runtime/tests(0) → fsm_runtime(1) → tools(2) → AISDLC_SDD_v0.30(3) → AISDLC_SDD(4)。
# 官方閘門（ci-gate.sh）以 `cd AISDLC_SDD_v0.30 && pytest tools/fsm_runtime/tests/` 執行，
# cwd 不含 AISDLC_SDD/ 根，故不能仰賴 `from scripts import bash_probe`（僅 cwd=AISDLC_SDD/
# 時可行，見 scripts/tests/test_copy_on_evolve.py），須顯式 sys.path 插入（比照根
# `AISDLC_SDD/conftest.py` 對 `scripts/cross_version_guard.py` 的既有做法）。
_AISDLC_SDD_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_AISDLC_SDD_ROOT / "scripts"))
from bash_probe import usable_bash as _usable_bash  # noqa: E402

_BASH = _usable_bash()

pytestmark = pytest.mark.skipif(
    _BASH is None, reason="install_post_commit.sh 為 bash 腳本，需可用 bash（非 WSL 佔位）"
)


def _git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=check,
    )


def _make_fake_monorepo(
    base: Path, version_name: str = "AISDLC_SDD_v0.99", repo_name: str = "repo"
) -> Path:
    """建立最小化假 monorepo：`AISDLC_SDD/<version>/.claude/hooks/{drift,closure}.py` 並 commit。

    `install_post_commit.sh` 只在存在性檢查與 LATEST 版本解析階段依賴這兩支檔案；
    本測試不觸發真實 commit hook 執行，只驗證安裝腳本本身的寫入行為，故內容用 dummy
    placeholder 即可，不需可執行的真實 hook 邏輯。`repo_name` 可指定非 ASCII 目錄名，
    供 worktree 測試重現編碼驗證情境（見下方 P1 修復訂正說明）。

    R11（DEF-101-133）：install_post_commit.sh 的 LATEST 解析改委派
    `AISDLC_SDD/scripts/sdd_version.py` SSOT，故 fixture 須比照真實 monorepo checkout
    放入一份真 resolver（scripts/ 恆隨 checkout 存在）並隨 `git add -A` 進 tracked
    （resolver 的 tracked 過濾語意才成立——版本目錄已 commit，符合選版條件）。
    """
    repo = base / repo_name
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    scripts_dir = repo / "AISDLC_SDD" / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy(
        _AISDLC_SDD_ROOT / "scripts" / "sdd_version.py",
        scripts_dir / "sdd_version.py",
    )
    hooks_dir = repo / "AISDLC_SDD" / version_name / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "post_commit_drift.py").write_text(
        "# dummy drift hook (test fixture)\n", encoding="utf-8"
    )
    (hooks_dir / "closure_evidence_verify.py").write_text(
        "# dummy closure hook (test fixture)\n", encoding="utf-8"
    )
    _git("add", "-A", cwd=repo)
    _git(
        "-c", "user.email=test@example.com", "-c", "user.name=Test",
        "commit", "-q", "-m", "init",
        cwd=repo,
    )
    return repo


def _run_install(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_BASH, str(INSTALL_SCRIPT)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def test_install_script_exists():
    assert INSTALL_SCRIPT.is_file(), f"install_post_commit.sh 不存在：{INSTALL_SCRIPT}"


def test_install_writes_hook_in_plain_checkout(tmp_path):
    """一般（非 worktree）checkout：hook 正確寫入 `.git/hooks/post-commit`。"""
    repo = _make_fake_monorepo(tmp_path)

    result = _run_install(repo)
    assert result.returncode == 0, (
        f"install_post_commit.sh 於一般 checkout 下應成功執行：\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )

    hook_path = repo / ".git" / "hooks" / "post-commit"
    assert hook_path.is_file(), "post-commit hook 未寫入 .git/hooks/"

    if not sys.platform.startswith("win"):
        # Windows（NTFS）沒有真正的 POSIX 執行位元；Git Bash 下 chmod +x 的效果
        # 不會反映在 Python os.stat().st_mode 上（Windows 上 st_mode 是由唯讀屬性
        # 合成的，不是真實的 owner/group/other 權限位元），故此斷言僅在 POSIX 平台
        # 有意義。腳本本身（含路徑解析邏輯）仍在 Windows 上實際執行並被下方斷言驗證。
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR, "post-commit hook 未被 chmod +x"

    content = hook_path.read_text(encoding="utf-8")
    assert "post_commit_drift.py" in content, "hook 內容缺 drift hook 路徑"
    assert "closure_evidence_verify.py" in content, "hook 內容缺 closure hook 路徑"
    # 用 as_posix() 而非 str()：install_post_commit.sh 透過 Git Bash（MSYS2）呼叫
    # `git rev-parse` 取得的路徑一律是正斜線形式（即使在 Windows 上），但
    # `pathlib.WindowsPath.__str__()` 會渲染成反斜線，兩者永遠不會相符——
    # 這正是 Windows 上真實 CI 才會現形的路徑分隔符假設錯誤（chmod +x 之後
    # 由 windows-compat-ci 真實跑出的第二個回歸）。
    assert repo.as_posix() in content, "hook 內容未含正確解析的 REPO_ROOT 路徑"


def test_install_writes_hook_to_shared_git_dir_from_worktree(tmp_path):
    """核心回歸鎖：linked git worktree 下，hook 必須寫入主 repo 共用的 .git/hooks/。

    2026-07-16 四方複審 R8 訂正（Architect 二審發現 P1 修復的連帶回歸，本檔原斷言
    會實際 FAIL）：`install_post_commit.sh`/`.ps1` 的 P1 修復把來源路徑（`HOOK_SRC_DRIFT`/
    `HOOK_SRC_CLOSURE`）從「呼叫端 worktree 自身根目錄」（`--show-toplevel`，worktree
    刪除後失效的 bug 根因）改為「主 checkout 根目錄」（`dirname(--git-common-dir)`）。
    這代表 hook 內嵌路徑**不再**含呼叫端 worktree 的目錄名——這正是修復的重點，而非
    退化。原本用「worktree 路徑含非 ASCII 字元」重現編碼驗證的手法因此失效（來源路徑
    不再含 worktree 名稱可供斷言）。改為讓「主 checkout 本身」建在非 ASCII 路徑下
    延續驗證編碼正確性（比照 `windows-compat-ci.yml` 對 `.ps1` 版本已改用「獨立 clone
    到中文路徑」的同款訂正邏輯），並新增一條斷言鎖死修復意圖本身：hook 內容不應含
    worktree 自己的路徑片段（若含，代表來源路徑解析退回呼叫端 worktree、P1 bug 復發）。
    """
    repo = _make_fake_monorepo(tmp_path, repo_name="主檢出目錄")

    worktree_dir = tmp_path / "worktree_checkout"
    _git("worktree", "add", "--detach", str(worktree_dir), "HEAD", cwd=repo)

    # sanity：worktree 的 .git 必須是「指向主 repo 的純文字檔」而非目錄——這正是原 bug
    # 的觸發前提。若此斷言不成立，代表測試環境未重現真實 worktree 語意，後續斷言無意義。
    worktree_git_entry = worktree_dir / ".git"
    assert worktree_git_entry.is_file(), "worktree 的 .git 應為純文字檔（非目錄）——測試前提未成立"

    result = _run_install(worktree_dir)
    assert result.returncode == 0, (
        f"install_post_commit.sh 在 git worktree 下應成功執行（DEF 修復點）：\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )

    # hook 必須寫入主 repo 共用 .git/hooks/，而非 worktree 自身（worktree 沒有自己的
    # hooks/ 目錄；舊硬編碼寫法會嘗試寫入 <worktree>/.git/hooks/post-commit，因
    # <worktree>/.git 是檔案而非目錄，寫入本應失敗）。
    shared_hook = repo / ".git" / "hooks" / "post-commit"
    assert shared_hook.is_file(), (
        "post-commit hook 未寫入主 repo 共用 .git/hooks/——"
        "疑似退回硬編碼 $REPO_ROOT/.git/hooks/（worktree 下路徑解析 bug 復發）"
    )

    raw = shared_hook.read_bytes()
    assert b"\xef\xbf\xbd" not in raw, "hook 內容含 U+FFFD 替代字元——非 ASCII 路徑遭編碼損毀"

    text = raw.decode("utf-8")
    assert "?" not in text, "hook 內容含 '?' 替代字元——非 ASCII 路徑疑似遭編碼損毀"
    assert "主檢出目錄" in text, (
        "hook 內容遺失非 ASCII 主 checkout 路徑片段——P1 修復後來源路徑應解回主"
        "checkout（含其非 ASCII 目錄名），而非呼叫端 worktree 自身"
    )
    assert "worktree_checkout" not in text, (
        "hook 內容不應包含呼叫端 worktree 自己的路徑片段——若出現代表來源路徑解析"
        "又退回 --show-toplevel（P1 bug 復發：worktree 刪除後路徑將失效）"
    )
    assert "post_commit_drift.py" in text, "hook 內容缺 drift hook 路徑"
    assert "closure_evidence_verify.py" in text, "hook 內容缺 closure hook 路徑"

    if not sys.platform.startswith("win"):
        # 見 test_install_writes_hook_in_plain_checkout 的同款註解：Windows 上
        # chmod +x 不會反映在 Python os.stat().st_mode，此斷言僅在 POSIX 平台有意義。
        mode = shared_hook.stat().st_mode
        assert mode & stat.S_IXUSR, "post-commit hook 未被 chmod +x"

    # 反向 sanity：worktree 自己底下絕不應該出現一份 hooks/post-commit（若出現，代表
    # 腳本用了某種「兩邊都寫」的取巧邏輯，掩蓋了真正的路徑解析問題）。
    assert not (worktree_dir / ".git" / "hooks").exists(), (
        "worktree 的 .git 是檔案，理論上不可能有 .git/hooks/ 子路徑；"
        "若存在代表測試環境或腳本行為與預期不符"
    )
