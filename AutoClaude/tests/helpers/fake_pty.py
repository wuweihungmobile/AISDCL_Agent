"""FakePty — 讓 `dry_run=False` 的 PlaybookRunner 路徑 hermetic（R90／DEF-200-127）。

## 為什麼是 `PtyWrapper` 這個接縫，而不是 `PlaybookRunner(executor=…)`

`PlaybookRunner.__init__` 曾經廣告過 `executor=` / `evaluator=` / `brain=` 三個
kwarg，任何人想讓 runner 測試 hermetic 時**第一個會試的就是那招**——而它是個陷阱：
R90 實測（DEF-200-126）那三個屬性只寫不讀（AST 掃 502 檔，三筆全為 `ctx=Store`、
零 `Load`），運行時 `__getattribute__` 攔截在整場 `run()` 期間讀取 **0 次**，
A/B 對照組（注入 fake executor vs 完全不注入）行為**逐字相同**。該三個死接縫已於
R90 拆除，本 docstring 保留這段推導，避免下一輪有人重新「發明」它。

runner 真正取得執行器的路徑是模組全域查詢：

    PlaybookRunner._execute_prompt
      → prompt_dispatcher.execute_prompt_impl
      → `_pr().PtyWrapper(...)`        # prompt_dispatcher.py:44,56
      → sys.modules["autoclaude.execution.playbook_runner"].PtyWrapper

所以接縫是 `patch("autoclaude.execution.playbook_runner.PtyWrapper", …)`。這不是本檔
發明的慣例——全庫既有 26 個站點都 patch 這裡（`test_token_checkpoint.py`、
`test_prompt_dispatcher.py`、`test_playbook_runner.py`），那些檔的 `dry_run=False`
測試因此一支都不用 skip。

## 這支 fixture 取代了什麼

`test_gap014_020.py` / `test_gap039_049.py` 原本有 11 支測試掛
`requires_claude_cli = pytest.mark.skipif(shutil.which("claude") is None or
os.environ.get("CLAUDECODE") == "1", …)`，理由是 `run()` 會真的去 spawn `claude`
CLI。那 11 支的 skip reason 登記的「治本方向」是**改用 `make_service` fake-executor
重寫**，R90 判定那條路是錯的：`make_service` 組的是 `AutoResumeService`+`PlaybookKernel`
＝**另一條程式路徑**，而這 11 支的斷言全部落在 Runner 路徑專屬語意上
（`runner._get_correction` / `runner._evaluate` / `runner._minimax_evolver` /
`result.step_log` 的 `[SKIPPED]` / batch 截斷至 3），Kernel 路徑一項都沒有
⇒ 照那條路做等於**換掉受測單元**，不是解除 skip。

改用本 fixture 後 11 支全部在兩平台跑得到，且**斷言與測試本體一個字都沒改**。

## 誠實劃界（不要把本檔讀成「那個問題解決了」）

原 skip reason 記載「macOS 側 R85 實測 `env -u CLAUDECODE pytest` 逾 600s 未完成，
成因**未知且未歸因**」（Windows 側則已歸因為 wexpect pty spawn 掛住不回，
DEF-101-913）。本 fixture **繞過**了那個現象（不再 spawn 任何東西），**沒有解釋它**。
若日後有人要歸因那個 600s，本檔不是證據，DEF-101-913 與 DEF-200-127 才是。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

#: 假 PTY 吐出的唯一一行輸出。刻意選一個**不匹配任何 expected_output_regex** 的字面：
#: 掛這支 fixture 的測試多數要的是「步驟失敗 → CORRECTION / ESCALATION 路徑」，
#: 給它一個會通過的輸出會讓那些斷言靜默失去意義（而測試照樣是綠的）。
#: 需要「步驟成功」的測試一律自己 patch `runner._evaluate`——現有 11 支就是這樣寫的。
FAKE_PTY_LINE = "R90_FAKE_PTY_NO_MATCH\n"


def make_fake_pty_class() -> MagicMock:
    """回傳一個可當 `PtyWrapper` 用的假類別（每次建構給一個新的假實例）。

    形態對齊全庫既有慣例（`test_token_checkpoint.py:287+`）：`readline` 依序吐行、
    最後回 `None` 讓 `execute_prompt_impl` 的讀取迴圈退出；`is_alive` 是 MagicMock
    （truthy），迴圈由 `readline() is None` 終止。
    """
    def _make(**kwargs):
        pty = MagicMock()
        pty.readline.side_effect = [FAKE_PTY_LINE, None]
        return pty

    cls = MagicMock()
    cls.side_effect = _make
    return cls


@pytest.fixture
def fake_pty():
    """把 `autoclaude.execution.playbook_runner.PtyWrapper` 換成假 PTY。

    yield 出去的是那個假類別本身，測試可以據以斷言「PTY 被建構了幾次」
    （`/compact` 會造成第二次建構，見 `test_token_checkpoint.py` 的用法）。
    """
    cls = make_fake_pty_class()
    with patch("autoclaude.execution.playbook_runner.PtyWrapper", cls):
        yield cls


#: 掛在 test function 或 test class 上皆可、且**不會多注入位置參數**
#: （`@patch` 裝在 class 上會改每個方法的簽章，那會讓這次改動從 7 行變成 11 處改簽章）。
hermetic_runner = pytest.mark.usefixtures("fake_pty")
