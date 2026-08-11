"""R84 / AC-(c)：「session 已經結束、Windows 11 上還會彈出警示視窗」的回歸鎖。

掌舵者第三輪重提的訴求語意是「**session 結束後不該還有東西彈出來**」。它拆成兩件
彼此獨立、會各自失效的事，本檔各給一組有牙的判準：

  (a) `enabled=False` 時**任何分支**都不得碰到平台通知後端 —— 包含「失敗／警示」那條
      路徑。掌舵者用的詞是「警示」，而「錯誤時強制通知」正是這類 gating 最常見的破口；
      本檔把四個訂閱 phase（含 POST_RUN success=False 與 ON_ESCALATION）全部驅動一遍。
      🔴 判準刻意下沉到 `utils.notifier` 的**平台後端**（`_try_plyer` / `_try_osascript` /
      `_try_win10toast` / `subprocess.run`）而不是 patch `notification_plugin.notify`：
      後者只證明「plugin 沒呼叫那個名字」，證不到「`enabled` 有沒有被傳下去」——而
      `notify()` 的 `enabled` 預設是 **True**（fail-open），漏傳就會彈。

  (b) 「彈窗在 session 結束後才冒出來」的字面原因是**行程還沒真的退場**：plyer 的
      Windows 後端在一個沒帶 `daemon=` 的執行緒裡 `time.sleep(timeout)`，而 CPython 對
      未指定者逐字「inherited from the creating thread」⇒ 從主執行緒（daemon=False）呼叫
      就會吊住 process exit。實測同構探針：主執行緒直呼 → 內層 daemon=False、行程
      wall=3.049s；改由 daemon 執行緒呼叫 → 內層 daemon=True、wall=0.247s。
      本檔鎖住「後端確實在 daemon 執行緒內被呼叫」與「join 有上界」。

  (c) 降級路徑不得改成模態視窗（`MessageBox` / `msg.exe`）——那是**更糟**的彈窗。
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import NotificationPlugin
from autoclaude.utils import notifier

_NF = "autoclaude.utils.notifier"


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


@contextmanager
def _backend_spies():
    """把每一個「真的會讓螢幕上出現東西」的出口換成間諜。

    回傳值刻意 return_value=True：若 gating 有破口，鏈上第一個間諜就會被呼叫並回報
    「已送出」，於是斷言看得到的是**第一個**破口而不是最後一個。
    """
    with patch(f"{_NF}._try_plyer", return_value=True) as plyer, \
         patch(f"{_NF}._try_osascript", return_value=True) as osa, \
         patch(f"{_NF}._try_win10toast", return_value=True) as toast, \
         patch(f"{_NF}.subprocess.run") as run:
        yield (plyer, osa, toast, run)


#: 四個訂閱 phase × 會發出「警示」的 payload 形態。
#: POST_RUN success=False 與 ON_ESCALATION 是掌舵者所述「警示」最貼合的兩條。
_ALERT_CONTEXTS: list[tuple[str, KernelPhase, dict]] = [
    ("post_run_failure", KernelPhase.POST_RUN, {"success": False}),
    ("post_run_success", KernelPhase.POST_RUN, {"success": True}),
    ("escalation_plain", KernelPhase.ON_ESCALATION, {"title": "T", "message": "M"}),
    ("evolution", KernelPhase.ON_EVOLUTION, {"evolution_count": 3}),
    ("auto_resume_wake", KernelPhase.ON_AUTO_RESUME_WAKE,
     {"kind": "halt", "wait_seconds": 30.0}),
]


class TestDisabledMeansNothingReachesTheScreen:
    @pytest.mark.parametrize(
        "label,phase,payload", _ALERT_CONTEXTS, ids=[c[0] for c in _ALERT_CONTEXTS],
    )
    def test_no_backend_is_reached_when_disabled(self, label, phase, payload):
        plugin = NotificationPlugin(enabled=False)
        ctx = HookContext(phase=phase, playbook=_pb(), task=_task(), payload=payload)
        with _backend_spies() as spies:
            plugin.on_event(ctx)
        for spy in spies:
            assert not spy.called, f"{label}: {spy} 在 enabled=False 下仍被呼叫"

    def test_escalation_with_dump_path_stays_quiet_even_if_config_says_yes(self, tmp_path):
        """plugin 關、config 開（不一致）⇒ 仍不得彈。

        WHY 這一格獨立存在：`ON_ESCALATION` + `dump_path` 是唯一會改走
        `notify_escalation(cfg)` 的分支，它的 enabled 讀的是 **cfg**、不是 plugin 旗標。
        若哪天有人把 plugin 那道 `if not self._enabled` 拿掉，其餘 parametrize 案例會因為
        兩邊都是 False 而照樣綠——本格把兩個來源刻意調成相反，鑑別力才在 plugin 那道門上。
        """
        from autoclaude.utils.config import AppConfig
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        cfg.notification.enabled = True
        plugin = NotificationPlugin(enabled=False, app_config=cfg)
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(), task=_task(),
            payload={"dump_path": str(tmp_path / "d.md"), "title": "T", "message": "M"},
        )
        with _backend_spies() as spies:
            plugin.on_event(ctx)
        for spy in spies:
            assert not spy.called
        # 刻意同時斷言：關掉的只有「彈窗」，escalation_alert.log 這條稽核路徑本來就不該
        # 被本輪順手關掉——而 plugin 這道門擋在它前面，所以這裡也不該有檔案產生。
        assert not (tmp_path / "escalation_alert.log").exists()

    def test_constructor_default_is_quiet(self):
        """建構式漏傳 enabled 時必須是「不彈」。

        production 唯一建構點（core/wiring.py）顯式傳 cfg 值 ⇒ 這個預設只在「新開建構點
        卻忘了傳」時生效，而那一刻的表徵就是彈窗回來、沒有任何東西轉紅。
        """
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb(),
                          payload={"success": False})
        with _backend_spies() as spies:
            NotificationPlugin().on_event(ctx)
        for spy in spies:
            assert not spy.called


class TestEveryBranchPassesEnabledExplicitly:
    @pytest.mark.parametrize(
        "label,phase,payload", _ALERT_CONTEXTS, ids=[c[0] for c in _ALERT_CONTEXTS],
    )
    def test_enabled_kwarg_is_always_explicit(self, label, phase, payload):
        """每一條分支都必須**顯式**把 enabled 傳進 notify()。

        `notify()` 的簽章預設是 `enabled=True`（fail-open）⇒ 漏傳的分支會在使用者設了
        `enabled: false` 之後照樣彈窗，而且 plugin 這一側的所有測試都還是綠的。
        本鎖直接讀 call kwargs：漏傳 ⇒ KeyError ⇒ 紅。
        """
        plugin = NotificationPlugin(enabled=True)
        ctx = HookContext(phase=phase, playbook=_pb(), task=_task(), payload=payload)
        with patch(f"{_NF}._try_plyer", return_value=True), \
             patch("autoclaude.plugins.notification_plugin.notify") as spy:
            plugin.on_event(ctx)
        assert spy.called, f"{label}: 本 phase 應該要發通知"
        assert spy.call_args.kwargs["enabled"] is True


class TestSessionEndIsNotHeldHostageByThePopup:
    def test_platform_backend_runs_inside_a_daemon_thread(self):
        """後端必須在 daemon 執行緒內被呼叫（否則它 spawn 的內層執行緒會吊住 process exit）。

        機制：plyer 那個內層 `Thread(...)` 沒帶 `daemon=`，CPython 對未指定者
        「inherited from the creating thread」⇒ 呼叫者是誰決定了它擋不擋 exit。
        """
        seen: dict[str, object] = {}

        def _spy(title: str, message: str, duration: int) -> bool:
            cur = threading.current_thread()
            seen["daemon"] = cur.daemon
            seen["is_main"] = cur is threading.main_thread()
            return True

        with patch(f"{_NF}._try_plyer", side_effect=_spy):
            notifier.notify("T", "M", enabled=True)
        assert seen["daemon"] is True
        assert seen["is_main"] is False

    def test_join_is_bounded_so_a_wedged_backend_cannot_block_the_caller(self):
        """join 有上界：卡住的後端不得把 notify() 變成不定時阻塞。

        上界取 `duration`（彈窗停留秒數）——後端最壞情況就是自己 sleep 完那麼久。
        """
        started = threading.Event()

        def _slow(title: str, message: str, duration: int) -> bool:
            started.set()
            time.sleep(0.5)
            return True

        with patch(f"{_NF}._try_plyer", side_effect=_slow):
            t0 = time.monotonic()
            notifier.notify("T", "M", duration=0, enabled=True)
            elapsed = time.monotonic() - t0
        assert started.wait(timeout=5), "後端根本沒被呼叫，本測試就不是在量 join 上界"
        assert elapsed < 0.3, f"notify() 被吊住 {elapsed:.3f}s，join 上界失效"


class TestDegradationNeverEscalatesToAModalWindow:
    def test_no_modal_dialog_api_anywhere_in_the_notification_path(self):
        """降級不得改成模態視窗：那比氣球提示更難關掉，且會阻塞行程直到有人按下確定。"""
        from pathlib import Path
        forbidden = ("MessageBox", "msg.exe", "user32", "ctypes")
        for mod in (notifier, __import__(
            "autoclaude.plugins.notification_plugin", fromlist=["x"],
        )):
            text = Path(mod.__file__).read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"{mod.__name__} 出現模態視窗 API：{token}"

    def test_windows_with_no_toast_backend_degrades_to_log_only(self, caplog):
        """Windows 上 plyer／win10toast 都不可用 ⇒ 只寫 log，不改走別的視窗。"""
        with patch(f"{_NF}._try_plyer", return_value=False), \
             patch(f"{_NF}._try_win10toast", return_value=False), \
             patch(f"{_NF}.is_macos", return_value=False), \
             patch(f"{_NF}.is_windows", return_value=True), \
             patch(f"{_NF}.subprocess.run") as run:
            with caplog.at_level(logging.INFO, logger=_NF):
                notifier.notify("T", "M", enabled=True)
        run.assert_not_called()
        assert any("[NOTIFY]" in r.message for r in caplog.records)
