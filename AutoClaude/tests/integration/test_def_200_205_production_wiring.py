"""DEF-200-205 回歸鎖：§4.5.9 救援序列與 §6.2 開機自檢**真的**接上生產路徑。

立案（帳本原文）：兩支模組「機制蓋好沒接電——零生產呼叫端」。於是本檔要鎖的不是那兩支
模組自己的行為（`tests/test_r100_boot_self_check.py`／`tests/test_r100_dirty_worktree_rescue.py`
已經把 G1~G10／D1~D9 全鎖過了，而那些鎖在**零呼叫端**的狀態下照樣全綠——這正是它們接不住
本缺陷的原因），而是**生產路徑會不會走到它們**。

⇒ 本檔的每一支測試都必須在「把新加的呼叫拔掉」時轉紅。拔不紅就表示它在測別的東西。

🔴 為什麼是整合測試而不是「斷言 main.py 裡有那一行」：後者是對原始碼字面的比對，換一個
   等價寫法就假紅、而把呼叫搬到一條永遠跑不到的分支裡又假綠。這裡一律從**入口**驅動
   （`main.main()` ／ `AutoResumeService.run()`），只斷言外部可觀測的效果。
"""
from __future__ import annotations

import contextlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from autoclaude import main as main_mod
from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.ports.worktree_rescue import (
    CLEAN,
    DIRTY_UNSAVED,
    SAVED,
    IWorktreeRescue,
)
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.core.wiring import build_worktree_rescue
from autoclaude.execution.boot_self_check import BootReport
from autoclaude.infra.adapters.dirty_worktree_rescue import (
    DirtyWorktreeRescueAdapter,
    RescueResult,
)
from autoclaude.utils.config import AppConfig

_REPO_PB = Path(__file__).resolve().parents[2] / "scripts" / "example_playbook.yaml"


# 🔴 R96 先例（`tests/execution/test_r85_subtraction_locks.py` 同款）：凡「在 tempdir 裡跑
# `main()`、跑完就刪那個 tempdir」的測試都必須先把 log 的檔案握把放掉——`main()` 建的
# `RotatingFileHandler` 一直握著 `<tmp>/logs/autoclaude.log`，而 Windows 不允許刪除仍被開啟
# 的檔 ⇒ tempdir 清理拋 WinError 32，測試在**本體已經通過之後**才紅。POSIX 上結構上重現不了。
def _release_autoclaude_log_handles() -> None:
    log = logging.getLogger("autoclaude")
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                          text=True, check=True, encoding="utf-8", errors="replace")


def _status(wt: Path) -> str:
    return _git(wt, "-c", "core.quotepath=false", "status", "--porcelain").stdout


def _dirty_repo(root: Path) -> Path:
    """建一棵**同時含 tracked 變更與 untracked 新檔**的真 git 工作樹（D1／D8 的母體要求）。"""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "keep.txt").write_text("v1\n", encoding="utf-8", newline="\n")
    _git(root, "add", "-A")
    _git(root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "base")
    (root / "keep.txt").write_text("v2\n", encoding="utf-8", newline="\n")        # tracked
    (root / "brand_new.py").write_text("x = 1\n", encoding="utf-8", newline="\n")  # untracked
    return root


def _clean_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("a\n", encoding="utf-8", newline="\n")
    _git(root, "add", "-A")
    _git(root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "base")
    return root


class _HaltingKernel:
    """每次 run() 都回 halted 的假 Kernel——`AutoResumeService` 的 halt 分支唯一入口。"""

    def __init__(self) -> None:
        self.runs = 0

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.runs += 1
        return KernelResult(success=False, completed_steps=0,
                            total_steps=len(playbook.tasks), reason="token halt",
                            halted=True)


def _playbook_file(root: Path) -> str:
    """把 playbook 寫在**工作樹之外**：寫進去就會多一筆 untracked，把 D1 那一格弄成假紅。"""
    p = root / "pb.yaml"
    p.write_text(yaml.safe_dump({
        "version": "1.0", "project": "def-200-205",
        "tasks": [{"step_id": "T01", "name": "n", "prompt": "p"}],
    }, allow_unicode=True), encoding="utf-8", newline="\n")
    return str(p)


def _service(cfg: AppConfig, rescue) -> AutoResumeService:
    """組一個「halt → 想要 auto-resume」的 service（不注入 state repo：本檔不測持久化）。"""
    cfg.token_guard.auto_resume = True
    cfg.token_guard.max_auto_resumes = 1
    cfg.token_guard.resume_delay_minutes = 0
    return AutoResumeService(_HaltingKernel(), cfg, state_repository=None,
                             worktree_rescue=rescue)


# ══════════════════════════════════════════════════════════════════════════════
# 一、§4.5.9 救援序列接上「halt → 凍結」那條路
# ══════════════════════════════════════════════════════════════════════════════
class TestRescueIsWiredIntoTheFreezePath:
    """halt 之後、轉入等待之前，救援序列必須**真的**在生產路徑上被跑到。

    為什麼這件事值得一支鎖：這個接點的失效方向是**完全靜默**的。救援沒接上時，
    `AutoResumeService` 照樣存 checkpoint、照樣排喚醒、照樣印
    `AUTO_RESUME #1/1 | 等待 0s 後繼續`——log 一切正常，而使用者未提交的工作在下一次
    喚醒被覆蓋前沒有任何一份備份。這正是帳本說的「交付的是機制，不是可用功能」。
    """

    def test_a_halt_really_writes_a_patch_for_the_dirty_worktree(self, tmp_path):
        """真 adapter ＋ 真髒工作樹：跑完 `run()` 後 checkpoint 目錄裡必須多出一份 patch。

        🔴 斷言的是**磁碟上的產物**（patch 檔存在、且內容涵蓋 untracked 新檔），不是
        「某個 mock 被呼叫了」——後者在「呼叫端存在但傳錯工作樹」時照樣綠。
        """
        wt = _dirty_repo(tmp_path / "wt")
        ck = tmp_path / "ckpt"
        svc = _service(AppConfig(checkpoint_dir=str(ck)),
                       DirtyWorktreeRescueAdapter(wt, ck, agent_id="a1"))
        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(_playbook_file(tmp_path))
        patches = sorted(ck.glob("dirty-a1-*.patch"))
        assert patches, f"halt 之後沒有任何 patch 落地 ⇒ 救援序列沒被生產路徑走到（{ck}）"
        body = patches[0].read_text(encoding="utf-8", errors="replace")
        assert "brand_new.py" in body, (
            "patch 沒涵蓋 untracked 新檔 ⇒ 接上的是只看 `git diff HEAD` 的半套母體（D8）")
        assert "keep.txt" in body, "patch 沒涵蓋 tracked 變更"

    def test_the_worktree_is_byte_for_byte_unchanged_by_the_rescue(self, tmp_path):
        """D1 在**生產路徑**上的那一格：救援後 `git status --porcelain` 逐字不變。

        單元測試已鎖過救援函式本身；這裡鎖的是「接上去之後也還是不變」——接點若把
        工作樹當暫存區用（例如順手 `git add`），使用者的 index 就被生產路徑改掉了。
        """
        wt = _dirty_repo(tmp_path / "wt")
        ck = tmp_path / "ckpt"
        pb = _playbook_file(tmp_path)
        before = _status(wt)
        svc = _service(AppConfig(checkpoint_dir=str(ck)),
                       DirtyWorktreeRescueAdapter(wt, ck))
        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(pb)
        assert _status(wt) == before, (
            f"救援改動了工作樹\nbefore={before!r}\nafter={_status(wt)!r}")

    def test_the_rescue_resolves_the_worktree_root_not_the_cwd_it_was_handed(self, tmp_path):
        """從**子目錄**指進去也必須救得到：路徑語意要求 worktree 是 repo 頂層。

        為什麼這一格不是多餘的：`git -C <子目錄> diff HEAD --name-only` 回**根相對**路徑，
        而 `ls-files --others` 回**cwd 相對**路徑 ⇒ 從子目錄跑會讓 ② 那半的
        `diff --no-index -- /dev/null <path>` 找不到檔（rc>1 → _GitError → DIRTY_UNSAVED）。
        失效形態＝一個「工作目錄剛好不是 repo 根」的使用者永遠救不起來，而且是靜默的。
        """
        wt = _dirty_repo(tmp_path / "wt")
        sub = wt / "pkg" / "deep"
        sub.mkdir(parents=True)
        ck = tmp_path / "ckpt"
        outcome = DirtyWorktreeRescueAdapter(sub, ck, agent_id="sub").rescue()
        assert outcome.status == SAVED, f"從子目錄救援失敗：{outcome.reason}"
        body = Path(outcome.patch_path).read_text(encoding="utf-8", errors="replace")
        assert "brand_new.py" in body and "keep.txt" in body

    def test_dirty_unsaved_refuses_the_auto_resume(self, tmp_path):
        """R-4.5.9-4 絕不 fail-open：救援回 DIRTY_UNSAVED ⇒ 不得轉入等待／自動喚醒。

        兩個可觀測後果一起斷言：① 完全沒有 sleep（沒有進入 WAITING_RESET 的等待）；
        ② Kernel 只被跑過一次（沒有續跑）。只斷言其中一個都留得下另一半的假綠。
        """
        class _Failing:
            def rescue(self) -> RescueResult:
                return RescueResult(status=DIRTY_UNSAVED, reason="注入：救援失敗",
                                    patch_path="x.patch", bytes_written=1,
                                    bytes_read_back=0, attempts=2)

        svc = _service(AppConfig(checkpoint_dir=str(tmp_path / "ckpt")), _Failing())
        with patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            result = svc.run(_playbook_file(tmp_path))
        assert result.halted is True
        assert slept.call_count == 0, "救援失敗卻還是睡了 ⇒ fail-open（工作沒保全就轉入等待）"
        assert svc.kernel.runs == 1, "救援失敗卻還是自動續跑 ⇒ 違反『禁止自動喚醒』"

    def test_a_rescue_that_raises_is_also_treated_as_unsafe(self, tmp_path):
        """fail-closed 的另一半：救援自己拋錯時「工作有沒有保全」是**不知道**。

        把例外讀成「沒事」＝把「量不到」讀成「量到零」，而那是本 repo 通篇在治的形態。
        """
        class _Boom:
            def rescue(self):
                raise OSError("注入：磁碟不見了")

        svc = _service(AppConfig(checkpoint_dir=str(tmp_path / "ckpt")), _Boom())
        with patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
            svc.run(_playbook_file(tmp_path))
        assert slept.call_count == 0 and svc.kernel.runs == 1

    def test_a_clean_worktree_does_not_look_like_a_failed_rescue(self, tmp_path):
        """控制組（本接點最貴的假紅方向）：工作樹乾淨時必須照常續跑。

        乾淨工作樹若被送進救援序列，patch 會是 0 bytes ⇒ (c) 斷言判 DIRTY_UNSAVED ⇒
        每一次乾淨的 halt 都被讀成「工作沒保全」而拒絕續跑。那是假紅，而假紅會讓整道
        判準被關掉（比沒有判準更糟）。所以 adapter 必須先問過 `status --porcelain`。
        """
        wt = _clean_repo(tmp_path / "clean")
        ck = tmp_path / "ckpt"
        adapter = DirtyWorktreeRescueAdapter(wt, ck)
        assert adapter.rescue().status == CLEAN
        svc = _service(AppConfig(checkpoint_dir=str(ck)), adapter)
        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(_playbook_file(tmp_path))
        assert svc.kernel.runs == 2, "乾淨工作樹被當成救援失敗 ⇒ auto-resume 被假紅擋掉"
        assert not list(ck.glob("*.patch")), "乾淨工作樹不該產生 patch"

    def test_no_rescue_port_keeps_the_old_behaviour_bit_for_bit(self, tmp_path):
        """未注入 Port 時（舊測試／dry-run 組態）行為必須與修前相同：照樣 auto-resume。"""
        svc = _service(AppConfig(checkpoint_dir=str(tmp_path / "ckpt")), None)
        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(_playbook_file(tmp_path))
        assert svc.kernel.runs == 2


class TestTheRescuePortIsARealBoundary:
    """接電要走 Port 注入，而不是讓 core/ 直接 import infra（core-purity contract #2）。"""

    def test_the_adapter_satisfies_the_port(self):
        assert isinstance(DirtyWorktreeRescueAdapter(".", "."), IWorktreeRescue)

    def test_the_status_literals_have_exactly_one_home(self):
        """字面留兩份時漂移方向是「消費端那份沒跟著改」⇒ 比不中 ⇒ fail-open。

        判準＝兩邊拿到的必須是**同一個物件**，不是「長得一樣的兩個字串」。
        """
        from autoclaude.infra.adapters import dirty_worktree_rescue as R
        assert R.SAVED is SAVED and R.DIRTY_UNSAVED is DIRTY_UNSAVED

    def test_wiring_binds_the_notification_flag(self, tmp_path):
        """`config.notification.enabled` 必須在 wiring 就綁進 notifier。

        `utils.notifier.notify` 的 `enabled` 預設 True ⇒ 不綁就等於這條路徑無視使用者
        的通知設定（R84 在 build_goal_decomposer 踩過同一格）。

        🔴 patch 必須在 `build_worktree_rescue` **之前**：那支 builder 是 lazy import
        （wiring 的既有體例），closure 捕捉的是**呼叫當下**解析到的那個函式物件 ⇒ 事後
        patch 模組屬性改不到它。本輪首跑就是踩這一格（spy.call_args is None）。
        """
        cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
        cfg.notification.enabled = False
        with patch("autoclaude.utils.notifier.notify") as spy:
            build_worktree_rescue(cfg, worktree=tmp_path)._notifier("訊息")
        assert spy.call_args is not None, "notifier 沒有走 utils.notifier.notify"
        assert spy.call_args.kwargs["enabled"] is False

    def test_wiring_reads_dirty_save_retries_from_env(self, tmp_path, monkeypatch):
        """DEF-200-206 ③：PRD §6 區塊 12 的 DIRTY_SAVE_RETRIES 必須在 wiring 就接進 adapter，
        否則讀取路徑蓋好沒接電（本檔上方 DEF-200-205 的同型）。"""
        from autoclaude.infra.adapters import dirty_worktree_rescue as R
        cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
        monkeypatch.delenv(R.DIRTY_SAVE_RETRIES_ENV, raising=False)
        assert build_worktree_rescue(cfg, worktree=tmp_path)._retries is None
        monkeypatch.setenv(R.DIRTY_SAVE_RETRIES_ENV, "3")
        assert build_worktree_rescue(cfg, worktree=tmp_path)._retries == 3


# ══════════════════════════════════════════════════════════════════════════════
# 二、CLI 啟動路徑（§6.2 開機自檢 ＋ 救援 Port 的注入）
# ══════════════════════════════════════════════════════════════════════════════
class _FakeService:
    """替身 AutoResumeService：本節鎖的是**組裝**，不是 playbook 執行本身。"""

    last_kwargs: dict = {}

    def __init__(self, kernel, cfg, **kwargs):
        type(self).last_kwargs = kwargs

    def run(self, path: str, fresh: bool = False) -> KernelResult:
        return KernelResult(success=True, completed_steps=0, total_steps=0, reason="fake")


class _NoopExecutor:
    def run(self, *a, **k):
        raise AssertionError("本節不應該真的執行 playbook（service 已被替身取代）")


def _run_main(tmp: Path, *extra_patches):
    """在 `tmp` 裡以真 `main()` 跑一次啟動流程；回 rc。"""
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO_PB, tmp / "scripts" / "example_playbook.yaml")
    cfgp = tmp / "config.yaml"
    cfgp.write_text(f"log_dir: {tmp.as_posix()}/logs\n"
                    f"checkpoint_dir: {tmp.as_posix()}/ckpt\n",
                    encoding="utf-8", newline="\n")
    argv = ["autoclaude", "scripts/example_playbook.yaml", "--config", str(cfgp), "--fresh"]
    origin = Path.cwd()
    os.chdir(tmp)
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(main_mod, "build_executor",
                                             lambda *a, **k: _NoopExecutor()))
            stack.enter_context(patch.object(main_mod, "AutoResumeService", _FakeService))
            stack.enter_context(patch.object(sys, "argv", argv))
            for cm in extra_patches:
                stack.enter_context(cm)
            return main_mod.main()
    finally:
        os.chdir(origin)
        _release_autoclaude_log_handles()


class TestBootSelfCheckIsWiredIntoStartup:
    """`main()` 必須在跑 playbook 之前做一次 §6.2 自檢，且 problems 非空時以非零 rc 停機。"""

    def test_main_calls_the_boot_self_check_exactly_once(self):
        """核心那一格：`main()` 真的呼叫 `boot_self_check`，而且只呼叫一次。

        🔴 這支測試就是本缺陷的證偽器：把 `main()` 裡那一行拔掉 ⇒ `calls == []` ⇒ 紅。
        「恰好一次」也一起鎖：自檢是**啟動**時判一次，不是每輪迴圈重判。
        """
        calls: list[dict] = []
        real = main_mod.boot_self_check

        def _spy(**kwargs):
            calls.append(kwargs)
            return real(**kwargs)

        with tempfile.TemporaryDirectory() as td:
            rc = _run_main(Path(td), patch.object(main_mod, "boot_self_check", _spy))
        assert len(calls) == 1, f"§6.2 開機自檢沒有被啟動路徑呼叫（rc={rc}, calls={len(calls)}）"

    def test_the_self_check_is_fed_the_real_production_inputs(self):
        """接上去了，但餵的必須是**生產路徑真的會用到的那些值**。

        三個都曾是這一族缺陷的實際失效面：
          · `repo` 為 None ⇒ `read_queue` 永遠回 0 筆（G1 在生產上零覆蓋）；
          · `playbook_id` 不是 canonical ⇒ 讀到別支 playbook 的佇列或讀不到；
          · `space_target` 不是 checkpoint 目錄 ⇒ 量錯磁碟（R-6.2-3 ②）。
        """
        calls: list[dict] = []
        real = main_mod.boot_self_check

        def _spy(**kwargs):
            calls.append(kwargs)
            return real(**kwargs)

        with tempfile.TemporaryDirectory() as td:
            _run_main(Path(td), patch.object(main_mod, "boot_self_check", _spy))
        kw = calls[0]
        assert kw["repo"] is not None, "repo=None ⇒ 佇列自檢在生產上恆掃 0 筆"
        assert kw["playbook_id"] == "example_playbook", (
            f"playbook_id 不是 canonical_playbook_id 的產出：{kw['playbook_id']!r}")
        assert Path(kw["space_target"]).name == "ckpt", (
            f"空間檢查量錯檔案系統：{kw['space_target']!r} 不是 checkpoint 目錄")
        assert kw["cleanup"] is not None and kw["notifier"] is not None

    def test_boot_problems_stop_the_startup_with_a_nonzero_rc(self):
        """`problems` 非空 ⇒ 非零退出碼，而且**不跑 playbook**。

        自檢只印一行 warning 而照樣往下跑，等於把不變式 11~13 降級成裝飾品。
        """
        _FakeService.last_kwargs = {}
        with tempfile.TemporaryDirectory() as td:
            rc = _run_main(Path(td), patch.object(
                main_mod, "boot_self_check",
                lambda **k: BootReport(problems=("注入：可用空間不足",))))
        assert rc == 1, "開機自檢判失敗卻仍以 rc=0 啟動 ⇒ 不變式 11~13 沒有牙齒"
        assert _FakeService.last_kwargs == {}, "自檢已判失敗卻仍組出 service 去跑 playbook"

    def test_a_clean_self_check_does_not_block_startup(self):
        """控制組：自檢通過時必須照常啟動（否則上一格分不出「有牙齒」與「咬所有人」）。"""
        with tempfile.TemporaryDirectory() as td:
            rc = _run_main(Path(td), patch.object(main_mod, "boot_self_check",
                                                  lambda **k: BootReport(lines=("ok",))))
        assert rc == 0, "自檢無 problems 卻擋下啟動 ⇒ 這種守衛會被整個關掉"


class TestRescuePortIsInjectedByTheCli:
    """`main()` 是唯一決定後端的 DI 組裝點 ⇒ 救援 Port 必須在那裡被注進 AutoResumeService。

    這一格與 §4.5.9 那一節互補：那一節證明「service 拿到 Port 就會用」，這一格證明
    「production 真的把 Port 給了它」。少任何一半，缺陷都還在（機制蓋好沒接電）。
    """

    def test_the_service_receives_a_worktree_rescue_port(self):
        _FakeService.last_kwargs = {}
        with tempfile.TemporaryDirectory() as td:
            rc = _run_main(Path(td), patch.object(main_mod, "boot_self_check",
                                                  lambda **k: BootReport()))
        assert rc == 0
        rescue = _FakeService.last_kwargs.get("worktree_rescue")
        assert isinstance(rescue, IWorktreeRescue), (
            f"main() 沒有把 IWorktreeRescue 注入 AutoResumeService：{rescue!r}")

    def test_the_quota_meter_is_shared_not_rebuilt(self):
        """同一次啟動只能有一份額度讀數來源（自檢與 halt 等待各 new 一個＝兩個家）。"""
        built: list[object] = []
        real = main_mod.build_quota_meter

        def _spy(*a, **k):
            m = real(*a, **k)
            built.append(m)
            return m

        _FakeService.last_kwargs = {}
        with tempfile.TemporaryDirectory() as td:
            _run_main(Path(td),
                      patch.object(main_mod, "build_quota_meter", _spy),
                      patch.object(main_mod, "boot_self_check", lambda **k: BootReport()))
        assert len(built) == 1, f"額度量測器被建了 {len(built)} 次"
        assert _FakeService.last_kwargs.get("quota_meter") is built[0]


class TestDryRunDoesNotWriteWorktrees:
    """G5 的一格：未知 CLI 版本（DRY_RUN）時，空間清理不得真的移除 worktree。

    `cleanup` 對 `boot_self_check` 是 opaque callable ⇒ 「要不要 dry-run」只有組裝端
    決定得了。組裝端漏傳 `dry_run=` 的失效形態是：一台磁碟快滿的機器在 CLI 剛升版
    （＝版本未知、本該什麼都不做）的那一刻，反而真的去拆掉 worktree。
    """

    def test_the_cleanup_closure_honours_the_dry_run_verdict(self, tmp_path, monkeypatch):
        removed: list[tuple] = []
        monkeypatch.setattr(main_mod, "cleanup_merged_worktrees",
                            lambda repo, **kw: removed.append((repo, kw)) or [])
        monkeypatch.setattr(main_mod, "read_cli_version", lambda *a, **k: None)  # 版本未知
        monkeypatch.setattr(main_mod, "estimate_freeze_bytes", lambda *a, **k: 0)

        def _spy(**kwargs):
            kwargs["cleanup"]()                       # 逼出那個 closure 真正帶的參數
            return BootReport()

        monkeypatch.setattr(main_mod, "boot_self_check", _spy)
        cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
        rc = main_mod.run_boot_self_check(
            cfg, state_repo=None, playbook_path=str(tmp_path / "pb.yaml"),
            quota_meter=None, logger=logging.getLogger("test"))
        assert rc == 0
        assert removed and removed[0][1].get("dry_run") is True, (
            "DRY_RUN 下 cleanup 沒帶 dry_run=True ⇒ 版本未知時仍會真的拆 worktree（G5）")

    def test_the_cli_version_is_read_exactly_once_per_startup(self, tmp_path, monkeypatch):
        """兩次 spawn 之間版本若不同，自檢輸出與 cleanup 的依據就會各說各話。"""
        reads: list[str] = []
        monkeypatch.setattr(main_mod, "read_cli_version",
                            lambda cmd, *a, **k: reads.append(cmd) or "2.1.233")
        monkeypatch.setattr(main_mod, "estimate_freeze_bytes", lambda *a, **k: 0)
        cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
        main_mod.run_boot_self_check(cfg, state_repo=None,
                                     playbook_path=str(tmp_path / "pb.yaml"),
                                     quota_meter=None, logger=logging.getLogger("test"))
        assert reads == ["claude"], f"CLI 版本被讀了 {len(reads)} 次：{reads}"


class TestDef200264StateBytesReachTheSpaceEstimate:
    """R-6.2-3 ② 的「state.json ×（1＋保留份數）」必須真的進到空間預估。

    立案時的失效形態不是崩潰，是**靜默低估**：呼叫端沒傳這兩個參數，
    `estimate_freeze_bytes` 的預設值讓那一項恆為 0 ⇒ `STATE_RETAIN_VERSIONS`
    怎麼調都不影響預估，一台快滿的磁碟會先通過自檢、再在凍結那一刻寫不下去。
    拔掉 `main.run_boot_self_check` 的那兩個 kwarg 即轉紅。`DEF-200-264`。
    """

    @staticmethod
    def _spy(monkeypatch, seen: dict) -> None:
        monkeypatch.setattr(main_mod, "read_cli_version", lambda *a, **k: "2.1.233")
        monkeypatch.setattr(main_mod, "estimate_freeze_bytes",
                            lambda *a, **kw: seen.update(kw) or 0)
        monkeypatch.setattr(main_mod, "boot_self_check", lambda **kw: BootReport())

    def test_the_estimate_receives_the_state_size_and_the_retain_count(
            self, tmp_path, monkeypatch):
        seen: dict = {}
        self._spy(monkeypatch, seen)

        class _Repo:
            def state_bytes(self, playbook_id: str) -> int:
                seen["asked_id"] = playbook_id
                return 4096

        cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
        main_mod.run_boot_self_check(
            cfg, state_repo=_Repo(), playbook_path=str(tmp_path / "pb.yaml"),
            quota_meter=None, logger=logging.getLogger("test"))
        assert seen.get("state_bytes") == 4096, (
            f"state 檔大小沒進到預估（收到 {seen.get('state_bytes')!r}）"
            " ⇒ R-6.2-3 ② 那一項恆為 0")
        assert seen.get("retain_versions") == main_mod.STATE_RETAIN_VERSIONS, (
            "保留份數沒進到預估 ⇒ STATE_RETAIN_VERSIONS 的出廠值對預估零效果")
        assert seen.get("asked_id"), "沒有拿 canonical playbook_id 去問 repo"

    def test_a_backend_without_state_files_is_zero_not_a_crash(
            self, tmp_path, monkeypatch):
        """PG／InMemory 後端不留本機 state 檔 ⇒ 0 是正確值，不是降級、也不該爆。"""
        seen: dict = {}
        self._spy(monkeypatch, seen)
        cfg = AppConfig(checkpoint_dir=str(tmp_path / "ckpt"))
        rc = main_mod.run_boot_self_check(
            cfg, state_repo=None, playbook_path=str(tmp_path / "pb.yaml"),
            quota_meter=None, logger=logging.getLogger("test"))
        assert rc == 0 and seen.get("state_bytes") == 0

    def test_the_file_backend_measures_the_real_file_and_zero_when_absent(self, tmp_path):
        """量的必須是 `_path()` 正規化後的那個檔——呼叫端自己拼路徑就會恆回 0。"""
        from autoclaude.infra.repositories.file_state_repository import (
            FileStateRepository,
        )
        repo = FileStateRepository(checkpoint_dir=str(tmp_path))
        assert repo.state_bytes("nope") == 0, "檔不存在時要回 0，不是丟例外"
        # 刻意經 `_path()` 落檔：正是要證明公開方法與私有路徑規則同源。
        repo._path("pb").write_bytes(b"x" * 123)
        assert repo.state_bytes("pb") == 123

    def test_the_dual_backend_forwards_to_its_file_primary(self, tmp_path):
        """`both` 模式的主端就是 File backend ⇒ 漏轉發會讓那一份靜默不計。

        本支由本輪 Architect 鏡實查補上：原本三支只用自製 stub 與 `state_repo=None`
        兩種情境，對「一個**真的** backend 漏了這個方法」零射程——而
        `DualStateRepository` 逐一手寫委派、沒有 `__getattr__`，正是會漏的那一種。
        """
        from autoclaude.infra.repositories.dual_state_repository import (
            DualStateRepository,
        )
        from autoclaude.infra.repositories.file_state_repository import (
            FileStateRepository,
        )
        primary = FileStateRepository(checkpoint_dir=str(tmp_path))
        dual = DualStateRepository(primary=primary, shadow=None)
        assert dual.state_bytes("pb") == 0, "檔不存在時 `both` 也要回 0"
        primary._path("pb").write_bytes(b"y" * 77)
        assert dual.state_bytes("pb") == 77, (
            "`both` 模式漏轉發 state_bytes ⇒ 主端磁碟上真的有 state.json 卻被算成 0")


@pytest.mark.parametrize("status,expect_safe", [(SAVED, True), (CLEAN, True),
                                                (DIRTY_UNSAVED, False)])
def test_freeze_gate_truth_table(status: str, expect_safe: bool):
    """判準的兩個方向一起鎖：只有 DIRTY_UNSAVED 擋，SAVED／CLEAN 都放行。

    寫成 `status == SAVED` 的實作會在 CLEAN 那一格轉紅（假紅）；寫成「永遠 True」的
    實作會在 DIRTY_UNSAVED 那一格轉紅（fail-open）。單一格的測試接不住其中一邊。
    """
    class _Fixed:
        def rescue(self):
            return RescueResult(status=status)

    svc = AutoResumeService(_HaltingKernel(), AppConfig(), worktree_rescue=_Fixed())
    assert svc._freeze_is_safe() is expect_safe
