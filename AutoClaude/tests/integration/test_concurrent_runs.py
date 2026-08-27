"""AC3-4「多 run 並存」的真斷言落點——門檻逐字＝**5 run × abort 互不影響**。

指標登記於 `tests/contract/test_ac_matrix_scaffolding.py::AC_MATRIX["AC3-4"]`
（上游 [SD_Improving_06.md](../../docs/04_planning/SD_Improving_06.md) §6.5 該列
逐字指名本檔）。此前本檔不存在，於是 AC3-4 是一筆「指標指不到任何東西」的欠債。

WHY 這一支非補不可，而不是拿既有測試充數（Rule 9 — 測意圖非僅行為）：
`tests/integration/test_multi_run_resume_e2e.py::TestConcurrentRuns` 表面上寫著同一件事，
但它 ①**循序**執行、②只跑 `InMemoryStateRepository`（一個以 playbook_id 當 key 的 dict）。
那個後端**結構上不可能**表現出這條 AC 要防的失效：
  · 5 個 run 的持久化位置互相踩（File 後端一個 playbook_id 對應一個檔案，
    檔名還經過 `_sanitize_log_filename` 正規化 ⇒ 兩個 id 正規化後撞名就會互相覆寫）；
  · abort 一個 run 之後，`load_by_run_id()` 對**已消失的那個 run_id** 回別人的 checkpoint
    （File 後端的 `load_by_run_id` 是 O(n) 掃檔比對，一個「回第一個掃到的檔」的退化
    寫法在 InMemory 後端上永遠看不出來）；
  · 併發寫入留下 `.tmp` 殘檔（atomic write 的 tmp 命名是 per-playbook_id 推導的）。
而 `storage.mode` 的**預設值是 `yaml_only`＝File 後端**（見 CLAUDE.md〈DAL 三後端〉），
所以此前被量測的是非預設路徑，預設路徑零覆蓋。

誠實劃界（本檔不宣稱涵蓋的東西）：
  · 只測 File 後端。PG 後端的並發語意（advisory lock）另有
    `tests/integration/test_advisory_lock_concurrent.py`／`tests/contract/
    test_alembic_0012_advisory_lock.py`，本檔刻意不重複那一面。
  · 「abort」在本檔的操作定義＝`clear_checkpoint(playbook_id)`（Port 契約裡唯一的
    終止原語）；Kernel 層的中止流程（ESC+F12／TOKEN_HALT）不在本檔射程內。
  · 併發以 `threading.Barrier` 逼出重疊，但**不宣稱**這能證明無鎖安全——它證的是
    「重疊發生時仍互不影響」這個可觀測結果，不是形式化的並發正確性。
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from unittest import mock

import pytest

from autoclaude.infra.repositories.file_state_repository import (
    _STALE_TMP_SECONDS,
    FileStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint

#: AC3-4 門檻裡的「5 run」——並存 run 數，全檔共用（不得散寫魔術數字）。
_RUNS = 5

#: 被 abort 的那一個 run 的索引（刻意取中間值：取 0 或 4 會讓「掃到第一個/最後一個就回」
#: 這類退化寫法有機會偶然通過）。
_ABORTED = 2


def _playbook_id(idx: int) -> str:
    return f"concurrent_run_{idx}"


def _checkpoint(idx: int, *, run_id: str, goal_task_id: str,
                step_idx: int | None = None) -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path=f"{_playbook_id(idx)}.yaml",
        step_idx=idx if step_idx is None else step_idx,
        step_id=f"T{idx:02d}",
        total_steps=_RUNS,
        project="ac3_4_concurrent_runs",
        run_id=run_id,
        goal_task_id=goal_task_id,
    )


@pytest.fixture()
def repo(tmp_path) -> FileStateRepository:
    """真實 File 後端（`storage.mode=yaml_only` 的生產路徑），落在測試專屬暫存目錄。"""
    return FileStateRepository(checkpoint_dir=str(tmp_path / "checkpoints"))


@pytest.fixture()
def five_runs(repo) -> tuple[str, list[str]]:
    """5 個共享同一 goal_task_id 的 run，**併發**寫入後回傳 `(goal_task_id, run_ids)`。

    以 `Barrier` 讓 5 個 thread 在同一瞬間進入 `save_checkpoint`——循序寫入量不到
    「同時落盤」這件事，而那正是 AC3-4 的字面情境。
    """
    goal_task_id = str(uuid.uuid4())
    run_ids = [str(uuid.uuid4()) for _ in range(_RUNS)]
    barrier = threading.Barrier(_RUNS)
    errors: list[BaseException] = []

    def _writer(idx: int) -> None:
        try:
            barrier.wait(timeout=10)
            repo.save_checkpoint(
                _playbook_id(idx),
                _checkpoint(idx, run_id=run_ids[idx], goal_task_id=goal_task_id),
            )
        except BaseException as exc:  # noqa: BLE001 — thread 內例外必須帶回主執行緒
            errors.append(exc)

    threads = [threading.Thread(target=_writer, args=(i,)) for i in range(_RUNS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "有 writer thread 未在 30s 內結束"
    assert errors == [], f"併發寫入拋出例外：{errors!r}"
    return goal_task_id, run_ids


def _residue(repo: FileStateRepository) -> list[str]:
    """atomic write 的 `.tmp` 殘檔（正常路徑一律 `replace()` 掉，殘檔＝寫入半途失敗）。"""
    return sorted(p.name for p in repo._dir.glob("*.tmp"))  # noqa: SLF001 — 取證需看真實目錄


def test_five_concurrent_runs_each_keep_their_own_row(repo, five_runs):
    """5 個 run 同時落盤後，每一個 run_id 都解析回**自己**那一筆，且無 tmp 殘檔。

    鑑別力來源：斷言的是「5 個 step_idx 恰好是 {0..4} 的集合」而不是逐筆比對就好——
    互相覆寫的失效表徵是**重複值**（有人被別人的內容蓋掉），逐筆比對在覆寫後也會
    有一筆是對的，只有集合等式抓得到「5 筆裡有兩筆一樣」。
    """
    goal_task_id, run_ids = five_runs

    files = sorted(p.name for p in repo._dir.glob("*.checkpoint.json"))  # noqa: SLF001
    assert len(files) == _RUNS, f"5 run 併發寫入後只有 {len(files)} 個持久化位置：{files}"
    assert _residue(repo) == [], "併發 atomic write 留下 .tmp 殘檔"

    restored = [repo.load_by_run_id(rid) for rid in run_ids]
    missing = [rid for rid, cp in zip(run_ids, restored) if cp is None]
    assert not missing, f"有 run_id 解析不到 checkpoint：{missing}"
    assert {cp.step_idx for cp in restored} == set(range(_RUNS)), (
        f"step_idx 集合＝{sorted(cp.step_idx for cp in restored)}，"
        "應為 0~4 各一筆——出現重複值即代表 run 之間互相覆寫"
    )
    assert {cp.run_id for cp in restored} == set(run_ids), "run_id 對不上（讀到別人的列）"
    assert {cp.goal_task_id for cp in restored} == {goal_task_id}, (
        "5 個 run 應共享同一 goal_task_id（三層任務模型：同 GoalTask 底下多 run 並存）"
    )


def test_aborting_one_run_neither_deletes_nor_reveals_another(repo, five_runs):
    """abort 一個 run：它自己兩條查詢路徑都要回 None，其餘 4 個逐欄不變。

    🔴 這一支的核心是 `load_by_run_id(<已 abort 的 run_id>) is None`：File 後端的
    該方法是「掃目錄逐檔比對 run_id」，一個「掃到第一個檔就回」的退化實作會在這裡
    回**別人的** checkpoint——那是 abort 之後最危險的失效（續跑會接到別的 run 的
    step_idx，看起來完全正常），而它在 InMemory 後端上結構上重現不了。
    """
    goal_task_id, run_ids = five_runs
    before = {
        idx: repo.load_latest_by_playbook(_playbook_id(idx))
        for idx in range(_RUNS) if idx != _ABORTED
    }

    repo.clear_checkpoint(_playbook_id(_ABORTED))

    assert repo.load_latest_by_playbook(_playbook_id(_ABORTED)) is None, "abort 後仍讀得到"
    leaked = repo.load_by_run_id(run_ids[_ABORTED])
    assert leaked is None, (
        f"已 abort 的 run_id 竟解析到 checkpoint（run_id={leaked.run_id}／"
        f"step_idx={leaked.step_idx}）——那是別的 run 的列被當成它的"
    )

    files = sorted(p.name for p in repo._dir.glob("*.checkpoint.json"))  # noqa: SLF001
    assert len(files) == _RUNS - 1, f"abort 一個 run 後應剩 4 個持久化位置，實得 {files}"

    for idx, snapshot in before.items():
        after = repo.load_by_run_id(run_ids[idx])
        assert after is not None, f"run {idx} 在別人被 abort 後消失了"
        assert (after.step_idx, after.step_id, after.run_id, after.goal_task_id) == (
            snapshot.step_idx, snapshot.step_id, snapshot.run_id, snapshot.goal_task_id
        ), f"run {idx} 的欄位在別人被 abort 後改變了"
        assert after.goal_task_id == goal_task_id


def test_a_concurrent_abort_does_not_disturb_the_other_four_writers(repo, five_runs):
    """abort 與其餘 4 個 run 的寫入**同時**發生時，4 個 run 仍各自推進到新 step。

    與上一支的差別是時序：上一支的 abort 發生在所有寫入之後（靜態），本支讓 abort
    與 4 筆 `save_checkpoint` 擠在同一個 Barrier 上。File 後端的 abort 是 `unlink`、
    寫入是 `tmp → replace`，兩者同時作用在**同一個目錄**上；`load_by_run_id` 的掃檔
    迴圈若遇到寫入半途的檔案就炸，這一支才會紅（該方法對損毀檔的容錯有
    `except → continue`，本支同時是那條容錯路徑的活體回歸）。
    """
    _goal_task_id, run_ids = five_runs
    advanced = {idx: idx + 10 for idx in range(_RUNS) if idx != _ABORTED}
    barrier = threading.Barrier(_RUNS)
    errors: list[BaseException] = []

    def _advance(idx: int) -> None:
        try:
            barrier.wait(timeout=10)
            repo.save_checkpoint(
                _playbook_id(idx),
                _checkpoint(idx, run_id=run_ids[idx],
                            goal_task_id=_goal_task_id, step_idx=advanced[idx]),
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def _abort() -> None:
        try:
            barrier.wait(timeout=10)
            repo.clear_checkpoint(_playbook_id(_ABORTED))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_advance, args=(i,)) for i in advanced]
    threads.append(threading.Thread(target=_abort))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "有 thread 未在 30s 內結束"
    assert errors == [], f"併發 abort ＋ 寫入拋出例外：{errors!r}"

    assert repo.load_by_run_id(run_ids[_ABORTED]) is None
    for idx, want in advanced.items():
        cp = repo.load_by_run_id(run_ids[idx])
        assert cp is not None, f"run {idx} 在併發 abort 後消失"
        assert cp.step_idx == want, (
            f"run {idx} 的 step_idx＝{cp.step_idx}，應為 {want}"
            "——併發 abort 期間的寫入被吞掉或被別人覆寫"
        )
    assert _residue(repo) == [], "併發 abort ＋ 寫入留下 .tmp 殘檔"


def test_isolation_survives_a_fresh_repository_over_the_same_directory(repo, five_runs):
    """換一個 repository 實例讀同一個目錄，隔離結果不變（＝隔離真的落在磁碟上）。

    意圖：這一支守的是「不得靠行程內狀態達成隔離」。今天 File 後端無任何快取，所以
    它現在是綠的；日後有人為了效能加上一層寫入快取而忘了 flush，上面三支（同一個
    實例讀寫）會照樣全綠，只有本支會紅——續跑是**新行程**讀舊目錄，本支就是那個情境。
    """
    goal_task_id, run_ids = five_runs
    repo.clear_checkpoint(_playbook_id(_ABORTED))

    reopened = FileStateRepository(checkpoint_dir=str(repo._dir))  # noqa: SLF001
    assert reopened.load_by_run_id(run_ids[_ABORTED]) is None
    survivors = {
        idx: reopened.load_by_run_id(run_ids[idx])
        for idx in range(_RUNS) if idx != _ABORTED
    }
    assert all(cp is not None for cp in survivors.values()), (
        f"新實例讀不到倖存的 run：{[i for i, cp in survivors.items() if cp is None]}"
    )
    assert {cp.step_idx for cp in survivors.values()} == set(range(_RUNS)) - {_ABORTED}
    assert {cp.goal_task_id for cp in survivors.values()} == {goal_task_id}


def test_two_concurrent_writers_to_the_same_playbook_id_do_not_share_a_tmp_file(repo):
    """DEF-200-043：`.tmp` 命名此前只由 `playbook_id` 推導，同一個 `playbook_id`
    的兩個行程／執行緒併發 `save_checkpoint` 會共用同一份 tmp 檔——其中一邊的
    `open("w")` truncate 掉另一邊尚未寫完的內容，先完成 `replace()` 的那邊會讓
    tmp 檔案消失，另一邊隨後的 `replace()` 因此 `FileNotFoundError`；更壞的是
    量測到「回報失敗」的那次寫入內容反而可能是最後留在磁碟上的那份（R103 收尾  round-label-ok
    重現實測：`ok` 回報的是 idx=2，最終落盤卻是拋例外的 idx=1）。

    本測試把兩支 writer 用 `Barrier` 逼到同時在 `open("w")` 之後停留，強迫兩邊
    的 tmp 檔案生命週期真的重疊，斷言：① 兩次呼叫算出的 tmp 路徑必須不同（修法
    本體）；② 兩邊都不拋例外；③ 事後無 `.tmp` 殘檔；④ 最終檔案是合法 JSON 且
    step_idx 落在兩邊寫入值之一（last-write-wins，容許順序不定，但不容許被①
    的競態污染成第三種值或整檔壞掉）。
    """
    playbook_id = "same_pb_concurrent_write"
    tmp_paths_opened: list[str] = []
    orig_open = Path.open
    barrier = threading.Barrier(2)

    def _synced_open(self, *args, **kwargs):
        f = orig_open(self, *args, **kwargs)
        if self.suffix == ".tmp":
            tmp_paths_opened.append(str(self))
            barrier.wait(timeout=10)  # 逼兩邊的 tmp 檔案生命週期真的重疊
        return f

    results: list[tuple[str, int]] = []

    def _writer(idx: int) -> None:
        try:
            repo.save_checkpoint(playbook_id, _checkpoint(idx, run_id=str(idx),
                                                            goal_task_id="gt"))
            results.append(("ok", idx))
        except BaseException as exc:  # noqa: BLE001 — 競態失敗也要能被斷言到
            results.append(("err", idx))
            raise AssertionError(f"idx={idx} 因競態拋出例外：{exc!r}") from exc

    with mock.patch.object(Path, "open", _synced_open):
        threads = [threading.Thread(target=_writer, args=(1,)),
                   threading.Thread(target=_writer, args=(2,))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert not any(t.is_alive() for t in threads), "有 writer thread 未在 30s 內結束"

    assert len(tmp_paths_opened) == 2, f"應各自開一次 tmp 檔：{tmp_paths_opened}"
    assert tmp_paths_opened[0] != tmp_paths_opened[1], (
        "DEF-200-043 回歸：兩個併發呼叫算出**同一個** tmp 檔名——"
        f"{tmp_paths_opened}"
    )
    assert {r[0] for r in results} == {"ok"}, f"併發寫入不應拋例外：{results}"
    assert _residue(repo) == [], "併發寫入同一 playbook_id 留下 .tmp 殘檔"

    final = repo.load_latest_by_playbook(playbook_id)
    assert final is not None, "同一 playbook_id 併發寫入後主檔消失"
    assert final.step_idx in (1, 2), f"落盤內容被競態污染：step_idx={final.step_idx}"


def test_a_stale_orphan_tmp_is_swept_on_the_next_save(repo):
    """DEF-200-226：`.tmp` 命名帶 pid+uuid4 後，寫入中途崩潰（OOM／SIGKILL）留下的
    孤兒 tmp 不再被「下一次同 playbook_id 寫入」自然覆蓋清理，需由清理邏輯主動清掉
    ——但只清「夠舊」的（見 `_STALE_TMP_SECONDS`），避免誤刪正在進行中的併發寫入。
    """
    playbook_id = "orphan_tmp_cleanup"
    p = repo._path(playbook_id)  # noqa: SLF001 — 取證需算出真實路徑
    orphan = p.with_suffix(".12345.deadbeef.tmp")
    orphan.write_bytes(b"{}")
    stale_at = time.time() - _STALE_TMP_SECONDS - 1
    os.utime(orphan, (stale_at, stale_at))

    repo.save_checkpoint(playbook_id, _checkpoint(
        0, run_id=str(uuid.uuid4()), goal_task_id=str(uuid.uuid4())))

    assert not orphan.exists(), "夠舊的孤兒 tmp 檔在下一次同 playbook_id 寫入時應被清掉"


def test_a_fresh_tmp_is_not_mistaken_for_an_orphan(repo):
    """對照組：年輕的 tmp 檔（可能是另一個併發寫入尚在進行中）不得被誤刪。"""
    playbook_id = "orphan_tmp_no_false_positive"
    p = repo._path(playbook_id)  # noqa: SLF001
    fresh = p.with_suffix(".99999.cafef00d.tmp")
    fresh.write_bytes(b"{}")

    repo.save_checkpoint(playbook_id, _checkpoint(
        0, run_id=str(uuid.uuid4()), goal_task_id=str(uuid.uuid4())))

    assert fresh.exists(), "年輕的 tmp 檔（可能是併發寫入中）不該被清理誤刪"
    fresh.unlink()


def test_cleanup_does_not_delete_another_playbooks_orphan_tmp_on_stem_prefix_collision(repo):
    """SD 於本輪複審重現：`_cleanup_orphan_tmp` 的 glob 是**前綴**匹配，不是精確匹配。

    playbook A 的 sanitized 檔名（`nightly_run` → stem `nightly_run.checkpoint`）恰好是
    playbook B 的 sanitized 檔名（`nightly_run.checkpoint.retry` → 檔名
    `nightly_run.checkpoint.retry.checkpoint.json`）的前綴，於是 A 呼叫 `save_checkpoint`
    觸發的 `_cleanup_orphan_tmp(A 的路徑)` 若沿用 `glob(f"{stem}.*.tmp")` 當唯一判準，
    會把 B 的孤兒 tmp 也掃進候選集合並誤刪——即使兩者理論上互不相干，只是恰巧共用
    同一個 `checkpoint_dir`。本測試把 B 的孤兒 tmp 刻意設為「夠舊」（超過
    `_STALE_TMP_SECONDS`），確保它落在會被清理的年齡帶內，藉此把「前綴匹配」與
    「年齡不足」兩種可能的假陰性原因分開：若修復失敗，本測試會因為 B 的孤兒被誤刪而紅；
    若只是年齡判準的問題，這裡的設定已排除該可能。
    """
    a_id = "nightly_run"
    b_id = "nightly_run.checkpoint.retry"
    a_path = repo._path(a_id)  # noqa: SLF001
    b_path = repo._path(b_id)  # noqa: SLF001
    assert b_path.name.startswith(a_path.stem + "."), (
        "測試前提不成立：B 的檔名須以 A 的 stem 為前綴，本測試才能重現該缺陷"
    )

    b_orphan = b_path.with_suffix(".54321.feedface.tmp")
    b_orphan.write_bytes(b"{}")
    stale_at = time.time() - _STALE_TMP_SECONDS - 1
    os.utime(b_orphan, (stale_at, stale_at))

    repo.save_checkpoint(a_id, PlaybookCheckpoint(
        playbook_path=f"{a_id}.yaml", step_idx=0, step_id="T00", total_steps=1,
        run_id=str(uuid.uuid4()), goal_task_id=str(uuid.uuid4()),
    ))

    assert b_orphan.exists(), (
        "A 的 _cleanup_orphan_tmp 誤刪了 B 的孤兒 tmp——glob 前綴碰撞導致跨 playbook 誤刪"
    )
    b_orphan.unlink()
