"""tools/hooks/check_sh_eol.py 單元測試。

守的紀律：CLAUDE.md §Nightly / CI 取證紀律 #8（SD_09 W0 P0-AUDIT-31）——CRLF 的 `.sh`
在 Linux container 內會炸，故「**存進 repo** 的 `.sh` 必須是 LF」。

本檔的核心意圖（Rule 9 — 測的是「為什麼這件事重要」）：
  ① **有牙**：作者當下寫出來的 CRLF `.sh`（新檔／repo 端真的存了 CR）必須 exit 2 擋住。
     這是本 hook 存在的唯一理由，任何「放寬」都不得把這一格一起放掉。
  ② **判準不得依賴機器**：`core.autocrlf=true` 的 Windows checkout 會在**取檔時**把
     `.sh` 轉成 CRLF 寫進工作樹（`.gitattributes text eol=lf` 只管「存進去」，不回頭
     正規化既有工作樹檔案）。若判準問磁碟，同一個 commit 就會「新 clone 一支不擋、
     舊工作樹擋掉上百支」——閘門結果變成「這台機器何時 clone 的」。②的測試就是把
     這個情境做成 fixture，讓它一旦回歸就當場紅。
  ③ **凍結版樹沒有合法修法**：AISDLC_SDD 非 LATEST 版本樹受 Copy-on-Evolve 禁止就地
     改寫，對它阻斷等於逼人違反另一條鐵律，故排除在阻斷面外（且 LATEST 版**仍要擋**
     ——排除的是「不准改的樹」，不是「整個 AISDLC_SDD」）。
  ④ **fail-open 紅線**：本 hook 註冊為 exit 2 硬阻斷，根 .claude/settings.json 記載過
     「hook 誤觸 deny 會把所有工具硬鎖死」的 P0。壞 payload／git 缺席／任何非預期例外
     都必須放行而非 deny。
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MONOREPO_ROOT = PROJECT_ROOT.parent
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "check_sh_eol.py"

_GIT = shutil.which("git")
requires_git = pytest.mark.skipif(_GIT is None, reason="需要 git 才能建 fixture repo")

# 假 SSOT：只回一個 LATEST 名字。用假的而非真的，是為了讓「凍結版 vs LATEST」的
# 對照組完全由 fixture 決定（不隨真 repo 的版本推進而漂移）。
_SSOT_STUB = "print('AISDLC_SDD_v0.99')\n"


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("_hook_check_sh_eol", HOOK_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run([str(_GIT), "-C", str(repo), *args], capture_output=True, check=True, timeout=60)


def _init_repo(root: Path) -> None:
    """建一個 fixture git 樹。

    刻意設 `core.autocrlf=false`：本機／CI 的全域值可能是 true，那會在 `git add` 時把
    CRLF 正規化成 LF，讓「blob 真的含 CR」這個對照組**做不出來**（測試會照綠，但驗的
    是別的東西）。
    """
    _git(root, "init")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


LF_BODY = b"#!/bin/bash\necho hello\n"
CRLF_BODY = b"#!/bin/bash\r\necho hello\r\n"


# ── ④ fail-open：hook 自身故障不得升級成 deny ──────────────────────────────────
def test_no_payload_fail_open():
    """無 payload → exit 0（不阻斷無關工具）。"""
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0


def test_malformed_json_payload_does_not_deny():
    """壞 JSON → exit 0。deny 類 hook 若把「讀不懂輸入」當成違規，就會把工具全鎖死。"""
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input='{"tool_input": {"file_path": ',
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_git_unavailable_fails_open(tmp_path, monkeypatch):
    """git 缺席（PATH 沒有 git／非 git 樹）→ 放行。

    此時無法區分「作者寫的 CRLF」與「checkout 轉出來的 CRLF」，而猜錯的代價不對稱：
    誤擋會鎖死 session，漏擋還有 CI 側行尾檢查接手。
    """
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    _write(tmp_path / "new.sh", CRLF_BODY)

    def _boom(_args):
        raise FileNotFoundError("git 不存在")

    monkeypatch.setattr(mod, "_run_git", _boom)
    assert mod.check_sh_eol(Path("new.sh")) == 0


def test_unexpected_exception_fails_open(tmp_path, monkeypatch):
    """判準內部任何非預期例外 → 放行（而非 deny）。"""
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    _write(tmp_path / "new.sh", CRLF_BODY)
    monkeypatch.setattr(mod, "git_repo_available", lambda: True)

    def _boom(_rel):
        raise RuntimeError("模擬非預期故障")

    monkeypatch.setattr(mod, "tracked_blob", _boom)
    assert mod.check_sh_eol(Path("new.sh")) == 0


# ── 射程：不得擴大 ────────────────────────────────────────────────────────────
def test_non_sh_file_passes():
    """非 .sh / .bash → exit 0（射程只有 shell 腳本）。"""
    result = _run({"tool_input": {"file_path": "autoclaude/main.py"}})
    assert result.returncode == 0


def test_missing_sh_passes(tmp_path, monkeypatch):
    """檔案不存在 → exit 0（可能是 Edit 後路徑變動）。"""
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    assert mod.check_sh_eol(Path("missing.sh")) == 0


def test_lf_sh_passes(tmp_path, monkeypatch):
    """純 LF 的 .sh → exit 0（且此路徑連 git 都不該被問到——mac/Linux 的常態）。"""
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    _write(tmp_path / "good.sh", LF_BODY)
    # 不用「拋例外」當探針：check_sh_eol 的 fail-open 會把例外吞掉並回 0，測試就會
    # 假綠。改記錄呼叫次數，讓「多跑了 git」這件事本身變成斷言對象。
    calls: list[list[str]] = []
    monkeypatch.setattr(mod, "_run_git", lambda args: calls.append(args) or (0, b""))
    assert mod.check_sh_eol(Path("good.sh")) == 0
    assert calls == [], "磁碟已是 LF 就該結束，不應付出 git 子行程成本"


# ── ① 有牙：真正要擋的兩種 CRLF ───────────────────────────────────────────────
@requires_git
def test_new_untracked_crlf_sh_blocks(tmp_path, monkeypatch):
    """新建（未 git add）的 CRLF .sh → exit 2。

    這是本 hook 唯一的存在理由：作者當下就寫錯了，此刻是最便宜的修復點，而磁碟上這份
    位元組就是即將被 commit 的內容。
    """
    mod = _load_hook_module()
    _init_repo(tmp_path)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    _write(tmp_path / "tools" / "bad.sh", CRLF_BODY)
    assert mod.check_sh_eol(Path("tools/bad.sh")) == 2


@requires_git
def test_bash_extension_also_checked(tmp_path, monkeypatch):
    """.bash 副檔名同樣納入（與 .gitattributes 的 `*.sh`/`*.bash` 對齊）。"""
    mod = _load_hook_module()
    _init_repo(tmp_path)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    _write(tmp_path / "lib.bash", b"#!/bin/bash\r\nexport X=1\r\n")
    assert mod.check_sh_eol(Path("lib.bash")) == 2


@requires_git
def test_tracked_blob_with_cr_still_blocks(tmp_path, monkeypatch):
    """已追蹤、但 **blob 自己含 CR** → exit 2。

    這是「CRLF 真的會被 commit 進 repo」的情形（沒有 .gitattributes 正規化接手），
    與 checkout 產物完全不同：放掉它就等於放掉紀律 #8 本身。
    """
    mod = _load_hook_module()
    _init_repo(tmp_path)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    target = tmp_path / "real_crlf.sh"
    _write(target, CRLF_BODY)
    _git(tmp_path, "add", "real_crlf.sh")
    assert mod.check_sh_eol(Path("real_crlf.sh")) == 2


# ── ② 本缺陷的回歸鎖：磁碟 CRLF 但 repo 端是 LF ───────────────────────────────
@requires_git
def test_tracked_lf_blob_with_crlf_worktree_passes(tmp_path, monkeypatch):
    """已追蹤且 blob 是 LF，磁碟卻是 CRLF → exit 0（**本缺陷的回歸鎖**）。

    為何重要：這正是 `core.autocrlf=true` 工作樹的常態——git 在 checkout 時把 LF blob
    寫成 CRLF，作者沒碰過那個檔。舊判準只看磁碟，於是同一個 commit 在新 clone 上一支
    都不擋、在舊工作樹上擋掉上百支（且大多位於不准改的凍結版樹）＝把「機器 checkout
    的時機」變成閘門結果。判準改問 blob 之後，兩台機器結論必須一致。
    """
    mod = _load_hook_module()
    _init_repo(tmp_path)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    target = tmp_path / "tools" / "checked_out.sh"
    _write(target, LF_BODY)
    _git(tmp_path, "add", "tools/checked_out.sh")
    # 模擬 checkout 期轉換：blob 已是 LF，工作樹那份被寫成 CRLF。
    target.write_bytes(CRLF_BODY)
    assert mod.has_crlf(target) is True, "fixture 前提：磁碟這份必須真的含 CR"
    assert mod.check_sh_eol(Path("tools/checked_out.sh")) == 0


# ── ③ 凍結版樹：排除阻斷，但 LATEST 仍要擋 ────────────────────────────────────
@requires_git
def test_frozen_sdd_tree_excluded_but_latest_still_blocked(tmp_path, monkeypatch):
    """非 LATEST 的 AISDLC_SDD 版本樹 → 放行；LATEST 版同樣情形 → 仍 exit 2。

    為何成對測：只驗「凍結版放行」的測試無法分辨「正確排除」與「整個 AISDLC_SDD 都不
    守了」。排除的理由是 Copy-on-Evolve 讓凍結版沒有合法修法，這個理由對 LATEST 不成立。
    """
    mod = _load_hook_module()
    _init_repo(tmp_path)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    sdd = tmp_path / "AISDLC_SDD"
    _write(sdd / "scripts" / "sdd_version.py", _SSOT_STUB.encode("utf-8"))

    frozen_rel = Path("AISDLC_SDD/AISDLC_SDD_v0.01/tools/init_project.sh")
    latest_rel = Path("AISDLC_SDD/AISDLC_SDD_v0.99/tools/init_project.sh")
    _write(tmp_path / frozen_rel, CRLF_BODY)
    _write(tmp_path / latest_rel, CRLF_BODY)

    assert mod.frozen_sdd_version(frozen_rel) == "AISDLC_SDD_v0.01"
    assert mod.frozen_sdd_version(latest_rel) is None
    assert mod.check_sh_eol(frozen_rel) == 0
    assert mod.check_sh_eol(latest_rel) == 2, "LATEST 版不在豁免面內——它是可以合法修的"


def test_frozen_classifier_asks_the_real_ssot():
    """真 repo 上的凍結／LATEST 分類必須由 SSOT 回答，且不隨機器狀態漂移。

    v0.01 是永久凍結基線（不會再變成 LATEST），故「它是凍結版」在任何 checkout 上都
    成立；LATEST 則向 tools/lib/sdd_latest.py → AISDLC_SDD/scripts/sdd_version.py 現問，
    本測試不寫死任何版本號（`DEF-101-133`：LATEST 只能有一個解析實作）。
    """
    if not (MONOREPO_ROOT / "AISDLC_SDD" / "scripts" / "sdd_version.py").is_file():
        pytest.skip("獨立 AutoClaude checkout：無 AISDLC_SDD 樹")
    mod = _load_hook_module()
    sys.path.insert(0, str(MONOREPO_ROOT / "tools" / "lib"))
    from sdd_latest import resolve_latest_name

    latest = resolve_latest_name(MONOREPO_ROOT / "AISDLC_SDD")
    assert mod.frozen_sdd_version(Path("AISDLC_SDD/AISDLC_SDD_v0.01/tools/x.sh")) == (
        "AISDLC_SDD_v0.01"
    )
    assert mod.frozen_sdd_version(Path(f"AISDLC_SDD/{latest}/tools/x.sh")) is None
    assert mod.frozen_sdd_version(Path("AutoClaude/tools/x.sh")) is None


def test_project_root_is_the_monorepo_root_without_a_dead_fallback():
    """PROJECT_ROOT 必須是 monorepo 根，且不得再出現「不成立的退路」。

    為何重要：本檔無條件 `from platform_utils import …`，而該模組只有一份、住在**根層**
    `tools/lib/`。任何「偵測不到就退回 AutoClaude 根」的分支都只能在那個 import 已經炸掉
    的世界裡被執行到＝永遠執行不到，只有註解在宣稱它存在（實測缺根層 tools/lib 時
    ModuleNotFoundError、rc=1，也就是連 hook 本體都沒開始跑）。要支援獨立 checkout 必須
    先讓共用層有降級路徑，不能靠一行註解。
    """
    mod = _load_hook_module()
    assert mod.PROJECT_ROOT == MONOREPO_ROOT, (
        f"射程基準必須是 monorepo 根（實際 {mod.PROJECT_ROOT}）——`AutoClaude/` 之外的 "
        f".sh 是本 hook 的主要守備範圍"
    )
    source = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert "else _AUTOCLAUDE_ROOT" not in source, (
        "退路分支不得復活：它在 platform_utils import 之前無法生效，只會製造假安全感"
    )


def test_hook_source_has_no_hardcoded_sdd_version():
    """本 hook 不得自帶版本號／版本 glob（`DEF-101-133`：LATEST 只有一個真相源）。

    寫死版本號的守衛會在下一次 Copy-on-Evolve 建版後靜默錯位——它不會紅，只會開始
    守錯的那棵樹。
    """
    source = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"AISDLC_SDD_v\d", source) is None, "版本解析一律問 sdd_latest 共用層"


# ── 真 repo 端到端：同一個 commit 在任何 checkout 上結論都必須一致 ─────────────
def test_real_repo_sh_files_never_block():
    """repo 內既有 `.sh` 一律不得被擋——不論這個工作樹的行尾長什麼樣。

    為何這樣寫（而非「斷言磁碟是 LF」）：磁碟行尾是 `core.autocrlf` 與 clone 時機的
    函數，斷言它等於把機器狀態寫進測試；真正的 invariant 是「已經 commit 進 repo 的
    檔案，守門不得對它們有意見」。取樣涵蓋 AutoClaude 自己的 `.sh` 與（monorepo
    checkout 時）AISDLC_SDD 凍結版樹各一批。
    """
    samples = sorted(PROJECT_ROOT.glob("tools/**/*.sh"))
    assert samples, "預期 AutoClaude/tools 底下至少有一支 .sh"
    frozen = sorted((MONOREPO_ROOT / "AISDLC_SDD").glob("AISDLC_SDD_v0.01/tools/**/*.sh"))
    for sh in samples[:6] + frozen[:3]:
        result = _run({"tool_input": {"file_path": str(sh)}})
        assert result.returncode == 0, (
            f"{sh} 被擋：{result.stderr}（已 commit 的檔案不得因工作樹行尾被擋）"
        )
