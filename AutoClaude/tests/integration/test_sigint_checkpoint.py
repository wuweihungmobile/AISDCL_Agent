"""AC5-4「SIGINT checkpoint SLA」的真斷言落點——門檻逐字＝**≤ 2s 寫入完成**。

指標登記於 `tests/contract/test_ac_matrix_scaffolding.py::AC_MATRIX["AC5-4"]`
（上游 [SD_Improving_06.md](../../docs/04_planning/SD_Improving_06.md) §6.5 該列
逐字指名本檔）。此前本檔不存在，於是 AC5-4 是一筆「指標指不到任何東西」的欠債。

WHY 這一支非補不可（Rule 9 — 一支不可能失敗的測試是壞測試）：
既有的 `tests/integration/test_multi_run_resume_e2e.py::test_sigint_checkpoint_under_2s`
量的是 `InMemoryStateRepository.save_checkpoint`＝**一次 dict 賦值**，它在任何退化下都
不可能超過 2s ⇒ 那支測試裡的「2s」是一個裝飾數字，SLA 這件事實際上零覆蓋。真正會慢、
會失敗、會在中斷那一刻決定「這個 run 的進度保不保得住」的是**持久化路徑**：
`FileStateRepository.save_checkpoint` 的 `tmp 檔 → json.dump → replace()` 三段落盤。
本檔把量測搬到那條路徑上，並且**在真實的 signal handler 內**執行——因為 SLA 的語意是
「行程被中斷、隨時可能被殺掉的那個瞬間，寫入能不能完成」，而 handler 內的執行環境
（可重入限制、pending call 邊界）與正常呼叫並不等價。

誠實劃界（本檔**不**宣稱涵蓋的東西，逐條可查）：
  · **AutoClaude 引擎自己沒有註冊 SIGINT handler**（實查：全庫唯一的
    `signal.signal(signal.SIGINT, ...)` 站點在 `tools/c6_staging_validator.py`，那是工具
    不是引擎）。⇒ 本檔量的是「checkpoint 寫入在 signal 情境下的 SLA」，**不是**
    「Kernel 收到 SIGINT 會存 checkpoint」。後者要成立需要先有 Kernel 層的接線
    （引擎現行的中斷入口是 ESC+F12 hotkey 與 TOKEN_HALT，兩者皆非 signal 路徑）；
    那條接線一旦落地，本檔應加一支「送 SIGINT 給真實 run，checkpoint 必落盤」的
    端到端案例。這個缺口刻意寫在這裡而不是包成一個 skip——一個 skip 只會把同一筆
    欠債換個地方掛著，而本檔存在的理由就是清掉那種掛法。
  · 只量 File 後端（`storage.mode` 的預設）。PG 後端的中斷寫入 SLA 不在射程內。
  · `signal.raise_signal(SIGINT)` 是同行程自送訊號，不涉及終端 Ctrl-C 的 console
    傳遞路徑（Windows 上那條路徑另有 `perception/hotkey` 一族在管）。
"""
from __future__ import annotations

import json
import signal
import time
import uuid

import pytest

from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint

#: AC5-4 門檻：中斷時 checkpoint 寫入必須在此秒數內完成。
_SLA_SECONDS = 2.0

#: `_save_under_sigint()` 等待 handler 真的被呼叫的上限（遠大於 SLA，只為避免無限等待）。
_HANDLER_WAIT_SECONDS = 10.0

_PLAYBOOK_ID = "interrupted_run"


def _checkpoint(run_id: str, *, step_idx: int = 3) -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path="interrupted.yaml",
        step_idx=step_idx,
        step_id=f"T{step_idx + 1:02d}",
        total_steps=8,
        project="ac5_4_sigint_sla",
        run_id=run_id,
        completed_step_ids=[f"T{i + 1:02d}" for i in range(step_idx)],
    )


def _save_under_sigint(repo, checkpoint: PlaybookCheckpoint) -> float:
    """在真實 SIGINT handler 內存 checkpoint，回傳**該次寫入**耗時（秒）。

    量測窗口刻意只包住 `save_checkpoint` 本身（不含 handler 派送與等待迴圈）：
    SLA 管的是寫入，把排程延遲算進去會讓門檻變成量測噪音的函式。

    handler 沒被呼叫時**不回傳假值**——直接讓呼叫端斷言失敗（`float("nan")` 之類的
    哨兵值會讓 `< 2.0` 悄悄變成 False，而那個紅指不出真正的原因）。
    """
    box: dict[str, float] = {}

    def _handler(signum, frame):  # noqa: ARG001 — signal handler 簽名固定
        t0 = time.perf_counter()
        repo.save_checkpoint(_PLAYBOOK_ID, checkpoint)
        box["elapsed"] = time.perf_counter() - t0

    previous = signal.signal(signal.SIGINT, _handler)
    try:
        signal.raise_signal(signal.SIGINT)
        # pending signal 在下一個 bytecode 邊界才派送 ⇒ 必須讓出控制權等它跑完。
        # handler 全程仍掛著，所以這個迴圈裡不可能漏接（漏接會讓 pending SIGINT 在
        # 還原 handler 之後才炸，直接殺掉整個 pytest session）。
        deadline = time.perf_counter() + _HANDLER_WAIT_SECONDS
        while "elapsed" not in box and time.perf_counter() < deadline:
            time.sleep(0.001)
    finally:
        signal.signal(signal.SIGINT, previous)
    assert "elapsed" in box, (
        f"SIGINT handler 在 {_HANDLER_WAIT_SECONDS}s 內未被呼叫——"
        "訊號沒送到，本次量測無效（不是 SLA 超時）"
    )
    return box["elapsed"]


@pytest.fixture()
def repo(tmp_path) -> FileStateRepository:
    """真實 File 後端（`storage.mode=yaml_only` 的生產落盤路徑）。"""
    return FileStateRepository(checkpoint_dir=str(tmp_path / "checkpoints"))


def test_checkpoint_write_inside_a_sigint_handler_meets_the_two_second_sla(repo):
    """AC5-4 門檻本體：signal handler 內的持久化寫入 ≤ 2s，且寫的是真的檔案。

    兩個斷言必須同時成立才算通過門檻——只斷言耗時的話，一個「什麼都沒寫」的退化
    實作會拿到 0.0s 的完美成績（那是本 AC 最容易出現的假綠形態）。
    """
    run_id = str(uuid.uuid4())
    elapsed = _save_under_sigint(repo, _checkpoint(run_id))

    assert elapsed <= _SLA_SECONDS, (
        f"中斷時 checkpoint 寫入耗時 {elapsed:.3f}s，超過 AC5-4 的 {_SLA_SECONDS}s SLA"
    )
    on_disk = sorted(p.name for p in repo._dir.glob("*.checkpoint.json"))  # noqa: SLF001
    assert on_disk == [f"{_PLAYBOOK_ID}.checkpoint.json"], (
        f"SLA 達標但磁碟上沒有 checkpoint：{on_disk}——耗時 0 的原因是根本沒寫"
    )


def test_the_interrupted_checkpoint_is_readable_by_a_fresh_process_view(repo):
    """落盤內容必須完整可還原——「寫入完成」不能只是「呼叫回來了」。

    以**新的** repository 實例（＝續跑時新行程的視角）讀回，逐欄比對關鍵欄位。
    半途中斷的 JSON 會讓 `json.load` 失敗，而 File 後端對載入失敗的處置是
    「warn 後回 None、從頭開始」——那正是這條 SLA 要避免的結果（進度靜默歸零），
    所以 `is not None` 在這裡不是形式檢查，它就是 AC 的實質。
    """
    run_id = str(uuid.uuid4())
    _save_under_sigint(repo, _checkpoint(run_id, step_idx=5))

    restored = FileStateRepository(
        checkpoint_dir=str(repo._dir)  # noqa: SLF001
    ).load_latest_by_playbook(_PLAYBOOK_ID)
    assert restored is not None, "新行程視角讀不回 checkpoint（落盤內容不完整）"
    assert restored.step_idx == 5, f"step_idx 應為 5，實得 {restored.step_idx}"
    assert restored.step_id == "T06"
    assert restored.run_id == run_id
    assert restored.completed_step_ids == ["T01", "T02", "T03", "T04", "T05"]
    assert restored.saved_at, "saved_at 未被寫入 ⇒ 無法判斷這筆是哪一刻的中斷"


def test_the_write_is_atomic_no_partial_file_is_left_behind(repo):
    """原子性：中斷寫入不得留下 `.tmp` 殘檔，且目的檔必是合法 JSON。

    意圖：SLA 與原子性是同一件事的兩面——寫得快但留下半套檔案，續跑時一樣拿不回
    進度。`.tmp` 殘檔是 `tmp → replace()` 這條路徑失敗時唯一看得見的痕跡。
    """
    _save_under_sigint(repo, _checkpoint(str(uuid.uuid4())))

    residue = sorted(p.name for p in repo._dir.glob("*.tmp"))  # noqa: SLF001
    assert residue == [], f"中斷寫入留下 .tmp 殘檔：{residue}"
    target = repo._dir / f"{_PLAYBOOK_ID}.checkpoint.json"  # noqa: SLF001
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["step_idx"] == 3 and payload["step_id"] == "T04"


def test_the_sla_stopwatch_really_wraps_the_write(repo):
    """🔴 本檔的自證：量測窗口真的包住 `save_checkpoint`，不是回一個好看的常數。

    WHY 非有這一支不可：上面三支只能證明「今天的實作夠快」。若哪天有人把
    `_save_under_sigint` 的計時改壞（例如量到 handler 之外、或直接回 0.0），三支
    全部照樣綠 ⇒ 門檻退化成裝飾。本支包一層**故意慢**的 repository，斷言量到的
    秒數不小於那個已知的延遲：計時器一旦不再包住寫入，這裡就抓不到那段延遲。

    刻意用遠小於 SLA 的延遲（不是 > 2s 的真慢）：這一支要證的是「計時器有牙」，
    不是「超時會紅」——後者若靠真的睡 2s 來證，代價是每次跑測試都多 2s。
    """
    delay = 0.05

    class _SlowRepo:
        def __init__(self, inner):
            self._inner = inner
            self.calls = 0

        def save_checkpoint(self, playbook_id, checkpoint):
            self.calls += 1
            time.sleep(delay)
            self._inner.save_checkpoint(playbook_id, checkpoint)

    slow = _SlowRepo(repo)
    elapsed = _save_under_sigint(slow, _checkpoint(str(uuid.uuid4())))

    assert slow.calls == 1, f"handler 內的寫入被呼叫 {slow.calls} 次，應恰好 1 次"
    assert elapsed >= delay, (
        f"注入了 {delay}s 延遲卻只量到 {elapsed:.4f}s——計時窗口沒有包住寫入，"
        "SLA 斷言已失去鑑別力"
    )
