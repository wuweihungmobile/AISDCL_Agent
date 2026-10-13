"""ARCH-01：引擎拒絕行程內長睡後，唯一的承接＝操作者掛的外部續跑指令
（環境變數 AUTOCLAUDE_EXTERNAL_RESUME_CMD）。

驗證意圖（Rule 9）：修前「需外部續跑」只有一行 ERROR 日誌、沒有任何元件重啟引擎——無人值守時整場 run
在第一次撞週額度就停死（PRD §4.5.2）。本檔守的是這個交棒會不會**悄悄消失**，不是子行程怎麼起：
  1. 變數未設／空白＝逐位元不變（零子行程）；
  2. 設了就恰好一次，範本先切字再代入佔位——路徑含空白／殼特殊字元仍是單一 argv 項、不經殼；
  3. 交棒失敗（找不到執行檔／非零 rc／逾時／範本壞掉）只出聲，不改引擎回傳；
  4. checkpoint 未確認落地時不交棒（從頭重跑不是續跑）；
  5. 操作者殼層 export 的該變數不得漏進測試（conftest 隔離＋自證，不然跑測試會真的掛排程）。
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.ports.quota_meter import QuotaReading
from autoclaude.core.services import external_resume as ext
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.in_memory_state_repository import InMemoryStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig

TESTS_DIR = Path(__file__).resolve().parent.parent
SIMPLE_PB = str(TESTS_DIR / "equivalence" / "fixtures" / "01_simple_2_step.yaml")
_RUN = "autoclaude.core.services.external_resume.subprocess.run"


class _Halting:
    """每次都 halt（halt_step_idx=1 ⇒ 服務先存 checkpoint）；`with_idx=False` 則不存。"""

    def __init__(self, with_idx: bool = True):
        self._idx = 1 if with_idx else None

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        return KernelResult.halted_(
            completed_steps=1, total_steps=2, step_log=["[T01] done"],
            completed_step_ids=["T01"], halt_step_idx=self._idx, peak_token_pct=93.0)


class _LongQuota:
    def read(self):
        return QuotaReading(96.0, "session", (datetime.now(UTC) + timedelta(hours=2)).isoformat())


class _Run:
    """替身 subprocess.run：記下每次呼叫，回預設結果或拋預設例外。"""

    def __init__(self, rc: int = 0, out: str = "ok\n", exc: Exception | None = None):
        self.calls: list[tuple[list[str], dict]] = []
        self._res = subprocess.CompletedProcess([], rc, out, "boom\n" if rc else "")
        self._exc = exc

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        if self._exc is not None:
            raise self._exc
        return self._res


def _cfg() -> AppConfig:
    cfg = AppConfig()
    cfg.notification.enabled = False
    cfg.token_guard.auto_resume = True
    cfg.token_guard.max_auto_resumes = 1
    cfg.token_guard.resume_delay_minutes = 5
    cfg.token_guard.max_inprocess_wait_seconds = 60        # 5 分鐘的等待 > 60s ⇒ 拒絕長睡
    return cfg


def _refuse(template: str | None, run: _Run, *, pb: str = SIMPLE_PB, kernel=None, quota=None):
    env = {} if template is None else {ext.EXTERNAL_RESUME_CMD_ENV: template}
    svc = AutoResumeService(kernel or _Halting(), _cfg(), quota_meter=quota,
                            state_repository=InMemoryStateRepository())
    with patch.dict(os.environ, env), patch(_RUN, run), \
            patch("autoclaude.core.services.auto_resume.time.sleep") as slept:
        result = svc.run(pb, fresh=True)
    assert slept.call_count == 0 and result.reason == "external_resume_required"
    return result


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone()      # naive 視為本地時間（同 resume_clock）


class TestTheHandOffIsOptInAndExact:
    @pytest.mark.parametrize("template", [None, "", "   "])
    def test_unset_or_blank_spawns_nothing(self, template):
        run = _Run()
        _refuse(template, run)
        assert run.calls == [], "變數缺席／空白卻仍起了子行程 ⇒ 預設不再逐位元不變"

    def test_set_calls_exactly_once_with_the_real_resume_instant(self):
        run = _Run()
        result = _refuse("hook {playbook} --at {resume_at} --cwd {cwd}", run)
        assert len(run.calls) == 1
        argv, kw = run.calls[0]
        assert argv[0] == "hook" and argv[1] == os.path.abspath(SIMPLE_PB)
        assert argv[2] == "--at" and argv[4:] == ["--cwd", os.getcwd()]
        assert datetime.fromisoformat(argv[3]).tzinfo is not None, "交棒時刻必須帶 offset"
        assert _instant(argv[3]) == _instant(result.scheduled_resume_at), (
            "交棒的時刻必須就是 checkpoint／結果裡那個真實續跑時刻")
        assert kw["timeout"] == 60 and kw["encoding"] == "utf-8" and kw["errors"] == "replace"
        assert not kw.get("shell"), "不得經殼：路徑／時刻是資料，不是指令"

    def test_a_relative_playbook_path_is_handed_over_absolute(self, tmp_path, monkeypatch):
        shutil.copy(SIMPLE_PB, tmp_path / "rel.yaml")
        monkeypatch.chdir(tmp_path)
        run = _Run()
        _refuse("hook {playbook}", run, pb="rel.yaml")
        assert run.calls[0][0][1] == os.path.join(os.getcwd(), "rel.yaml")

    def test_a_path_with_spaces_and_shell_characters_stays_one_argv_item(self, tmp_path):
        pb = tmp_path / "a b;c $(x) {cwd}.yaml"             # 含 `{cwd}` 字面：代入必須單趟
        shutil.copy(SIMPLE_PB, pb)
        run = _Run()
        _refuse("hook {playbook} tail", run, pb=str(pb))
        assert run.calls[0][0] == ["hook", os.path.abspath(pb), "tail"]

    def test_the_quota_axis_refusal_hands_over_the_pinned_two_hour_instant(self):
        run = _Run()
        result = _refuse("hook {resume_at}", run, quota=_LongQuota())
        lag = (_instant(run.calls[0][0][1]) - datetime.now().astimezone()).total_seconds()
        assert 7100 < lag < 7300 and _instant(run.calls[0][0][1]) == _instant(
            result.scheduled_resume_at)


class TestAFailedHandOffNeverChangesTheEngineResult:
    @pytest.mark.parametrize("run", [
        _Run(exc=FileNotFoundError("no such hook")),
        _Run(exc=subprocess.TimeoutExpired("hook", 60)),
        _Run(rc=3),
    ], ids=["missing-exe", "timeout", "nonzero-rc"])
    def test_it_only_speaks(self, run, caplog):
        with caplog.at_level(logging.WARNING, logger="autoclaude"):
            result = _refuse("hook {playbook}", run)
        assert len(run.calls) == 1 and result.success is False and result.halted is True
        assert result.scheduled_resume_at, "失敗的交棒不得連帶吃掉續跑時刻"
        assert "外部續跑" in caplog.text

    def test_a_broken_template_is_a_warning_not_a_crash(self, caplog):
        run = _Run()
        with caplog.at_level(logging.WARNING, logger="autoclaude"):
            _refuse('hook "unterminated {playbook}', run)
        assert run.calls == [] and "外部續跑" in caplog.text


class TestAnUnconfirmedCheckpointIsNeverHandedOver:
    def test_without_a_landed_checkpoint_there_is_nothing_to_resume(self, caplog):
        run = _Run()
        with caplog.at_level(logging.WARNING, logger="autoclaude"):
            _refuse("hook {playbook}", run, kernel=_Halting(with_idx=False), quota=_LongQuota())
        assert run.calls == [], "checkpoint 沒落地卻交棒 ⇒ 外部續跑會從頭重跑"
        assert "未確認落地" in caplog.text and "不交棒" in caplog.text

    def test_the_second_wait_site_hands_over_the_checkpoints_own_instant(self):
        """第二處等待（checkpoint 續跑）同樣交棒，時刻＝checkpoint 自己的那個。"""
        cfg, repo, run = _cfg(), InMemoryStateRepository(), _Run()
        sched = (datetime.now() + timedelta(minutes=10, seconds=17)).isoformat(timespec="seconds")
        from autoclaude.infra.repositories.factory import canonical_playbook_id
        repo.save_checkpoint(canonical_playbook_id(SIMPLE_PB, mode=cfg.storage.mode),
                             PlaybookCheckpoint(playbook_path=SIMPLE_PB, step_idx=1, step_id="T02",
                                                total_steps=2, scheduled_resume_at=sched))
        with patch.dict(os.environ, {ext.EXTERNAL_RESUME_CMD_ENV: "hook {resume_at}"}), \
                patch(_RUN, run), patch("autoclaude.core.services.auto_resume.time.sleep"):
            result = AutoResumeService(_Halting(), cfg, state_repository=repo).run(
                SIMPLE_PB, fresh=False)
        assert result.reason == "external_resume_required" and len(run.calls) == 1
        assert _instant(run.calls[0][0][1]) == _instant(sched)


class TestTheTemplateSplitterHonoursBothShellFamilies:
    def test_posix_and_windows_quoting_both_keep_paths_intact(self):
        """Windows 路徑的反斜線在 posix 切字下會被吃掉：非 posix 模式必須原樣保留並去掉成對引號。"""
        tmpl = r'C:\py\python.exe "C:\a b\x.py" --at {resume_at}'  # platform-ok: 純字串切字
        assert ext.split_template(tmpl, posix=False) == [
            r"C:\py\python.exe", r"C:\a b\x.py", "--at", "{resume_at}"]  # platform-ok: 同上
        assert ext.split_template("/p/py 'a b' x", posix=True) == ["/p/py", "a b", "x"]


class TestTheOperatorsShellVariableNeverLeaksIntoTheTestRun:
    """conftest 的 autouse 隔離＋自證（體例同 ALLOW_PERMISSION_BYPASS 那一族）：探針只斷言變數
    不在環境；兩支子行程各帶變數跑它一次——有 conftest 必綠、`--noconftest` 對照組必紅，否則
    那次綠是空洞的。"""

    _PROBE = ("tests/core/test_auto_resume_external_resume_cmd.py::"
              "TestTheOperatorsShellVariableNeverLeaksIntoTheTestRun::test_probe_the_variable_is_absent")

    def test_probe_the_variable_is_absent(self):
        assert ext.EXTERNAL_RESUME_CMD_ENV not in os.environ

    def _probe(self, *extra):
        return subprocess.run(
            [sys.executable, "-m", "pytest", self._PROBE, "-q", "-p", "no:xdist", "-o", "addopts=",
             "-p", "no:cacheprovider", *extra], cwd=TESTS_DIR.parent, capture_output=True,
            text=True, encoding="utf-8", timeout=120,
            env={**os.environ, ext.EXTERNAL_RESUME_CMD_ENV: "echo leaked"})

    def test_the_variable_exported_by_the_caller_is_invisible_to_tests(self):
        proc = self._probe()
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_control_without_conftest_the_variable_is_visible(self):
        proc = self._probe("--noconftest")
        assert proc.returncode != 0 and ext.EXTERNAL_RESUME_CMD_ENV in proc.stdout, proc.stdout
