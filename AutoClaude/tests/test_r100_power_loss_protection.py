"""R100 P2-C（PRD §8-4）：斷電保護 ① os.fsync ② checksum × CORRUPT≠None。

① 為什麼 `os.replace` 不夠（R98 曾把「原子寫入已做」記為完成，發現波駁回了那個判讀）：
   `replace` 保證的是**換名這個動作**是原子的；它對「內容有沒有從 page cache 落到碟上」
   一個字都不保證。兩者正交 ⇒ 斷電時可能得到一個「目錄項已更新、內容是空的／截斷的」
   checkpoint，而缺 fsync 這一半在任何正常關機的測試裡**都不會有表徵**。
   ⇒ 判準只能掛在「有沒有真的呼叫 fsync，且在 replace 之前」。

② 為什麼 CORRUPT 必須與 None 分家：`None` 的語意是「沒有 checkpoint」，呼叫端對它的
   正確反應是從 step 0 開始 ⇒ 把損壞也回成 None，效果是靜默重跑一整份 playbook。
"""
from __future__ import annotations

import errno
import json
import os
from dataclasses import asdict
from pathlib import Path

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.state_repository import (
    CheckpointCorruptError,
    StateRepositoryError,
)
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.file_state_repository import (
    STATE_RETAIN_VERSIONS,
    FileStateRepository,
    retained_paths,
)
from autoclaude.utils.checkpoint_manager import (
    CHECKSUM_FIELD,
    PlaybookCheckpoint,
    checkpoint_digest,
)
from autoclaude.utils.config import AppConfig


def _resume_service(repo) -> AutoResumeService:
    kernel = PlaybookKernel(executor=None, evaluator=None, bus=EventBus())
    return AutoResumeService(kernel, AppConfig(), state_repository=repo)


def _cp(playbook_path: str = "pb.yaml") -> PlaybookCheckpoint:
    return PlaybookCheckpoint(playbook_path=playbook_path, step_idx=2,
                              step_id="S3", total_steps=5)


# ══════════════════════════════════════════════════════════════════════════════
# ① os.fsync
# ══════════════════════════════════════════════════════════════════════════════
def test_the_content_is_fsynced_before_the_rename(tmp_path, monkeypatch):
    order: list[str] = []
    real_fsync, real_replace = os.fsync, Path.replace

    def spy_fsync(fd):
        order.append("fsync")
        return real_fsync(fd)

    def spy_replace(self, target):
        order.append("replace")
        return real_replace(self, target)

    monkeypatch.setattr(os, "fsync", spy_fsync)
    monkeypatch.setattr(Path, "replace", spy_replace)
    FileStateRepository(str(tmp_path)).save_checkpoint("pb", _cp())

    # 這兩格就是判準本體：修法前 order 內只有 "replace"（沒有任何 fsync 呼叫）
    # ⇒ 第一格直接紅；順序寫反則第二格紅。
    assert "fsync" in order, f"save 全程沒有呼叫 os.fsync：{order}"
    assert order.index("fsync") < order.index("replace"), order


def test_the_saved_file_round_trips(tmp_path):
    # 控制組：加了 fsync／checksum 之後，正常存讀仍然逐欄相等（零退化）。
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    got = repo.load_latest_by_playbook("pb")
    assert got is not None
    assert (got.step_idx, got.step_id, got.total_steps) == (2, "S3", 5)
    assert got.checksum_sha256 != ""


# ══════════════════════════════════════════════════════════════════════════════
# ② checksum：CORRUPT ≠ None
# ══════════════════════════════════════════════════════════════════════════════
def test_a_missing_checkpoint_is_none(tmp_path):
    assert FileStateRepository(str(tmp_path)).load_latest_by_playbook("nope") is None


def test_a_truncated_file_is_corrupt_not_none(tmp_path):
    # 「檔在、內容截斷」——正是 ① 要防的斷電形態留下的殘骸。
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    p = tmp_path / "pb.checkpoint.json"
    raw = p.read_text(encoding="utf-8")
    p.write_text(raw[: len(raw) // 2], encoding="utf-8")
    with pytest.raises(CheckpointCorruptError):
        repo.load_latest_by_playbook("pb")


def test_a_tampered_body_is_corrupt_even_though_the_json_still_parses(tmp_path):
    # 🔴 這一格是 checksum 存在的理由：JSON 仍然合法、欄位仍然齊全、大小相近
    # ⇒ 只靠 `json.load` 成功／檔案大小都判不出來。
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    p = tmp_path / "pb.checkpoint.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["step_idx"] = 999                      # 動內容、不動 checksum
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CheckpointCorruptError):
        repo.load_latest_by_playbook("pb")


def test_a_legacy_file_without_a_checksum_still_loads(tmp_path, caplog):
    # 誠實劃界：R100 之前寫的檔沒有這一欄，驗不了。照載入，但必須出聲——
    # 若改成「沒有 checksum 就算 CORRUPT」，升級當下所有既有 checkpoint 一次全腐。
    p = tmp_path / "pb.checkpoint.json"
    payload = asdict(_cp())
    payload.pop(CHECKSUM_FIELD)
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with caplog.at_level("WARNING"):
        got = FileStateRepository(str(tmp_path)).load_latest_by_playbook("pb")
    assert got is not None and got.step_idx == 2
    assert CHECKSUM_FIELD in caplog.text


def test_the_digest_ignores_the_checksum_field_itself(tmp_path):
    # PRD §7 逐字：「除本欄位外之序列化內容的 SHA-256」。若把本欄也算進去，
    # 寫入時算出的值與讀回時算出的值結構上永不相等 ⇒ 每一個檔都會被判 CORRUPT。
    payload = asdict(_cp())
    a = checkpoint_digest({**payload, CHECKSUM_FIELD: ""})
    b = checkpoint_digest({**payload, CHECKSUM_FIELD: "deadbeef"})
    assert a == b


# ══════════════════════════════════════════════════════════════════════════════
# 呼叫端 fail-loud（PRD §8-4 ②：「不是靜默重跑」）
# ══════════════════════════════════════════════════════════════════════════════
def test_the_resume_path_does_not_swallow_a_corrupt_checkpoint(tmp_path):
    # AutoResumeService 既有的 except 清單是 (FileNotFoundError, ValueError, OSError)；
    # CheckpointCorruptError 刻意**不在**其中 ⇒ 它會穿出去，而不是變成 (0, [], False, None)
    # 那個「從頭跑」的回值。這一格釘住的就是「不得靜默重跑」。
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp("pb.yaml"))
    p = tmp_path / "pb.checkpoint.json"
    p.write_text("NOT JSON", encoding="utf-8")
    svc = _resume_service(repo)
    with pytest.raises(CheckpointCorruptError):
        svc._resolve_start("pb.yaml", fresh=False)


def test_the_resume_path_still_starts_from_zero_when_there_is_no_checkpoint(tmp_path):
    # 控制組：真的沒有 checkpoint 時行為完全不變（零退化）。
    svc = _resume_service(FileStateRepository(str(tmp_path)))
    assert svc._resolve_start("pb.yaml", fresh=False) == (0, [], False, None)


# ══════════════════════════════════════════════════════════════════════════════
# ③ STATE_RETAIN_VERSIONS（PRD §8-4 第 4 列：checksum 失敗 → 回退到最近的有效版本）
# ══════════════════════════════════════════════════════════════════════════════
def test_saving_twice_keeps_the_previous_version(tmp_path):
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    second = _cp()
    second.step_idx = 4
    repo.save_checkpoint("pb", second)
    kept = retained_paths(tmp_path / "pb.checkpoint.json")
    assert [q.name for q in kept] == ["pb.checkpoint.json.v1"]
    assert repo.load_latest_by_playbook("pb").step_idx == 4


def test_a_corrupt_primary_falls_back_to_the_most_recent_valid_version(tmp_path, caplog):
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())                 # step_idx=2 ⇒ 之後成為 .v1
    newer = _cp()
    newer.step_idx = 4
    repo.save_checkpoint("pb", newer)
    (tmp_path / "pb.checkpoint.json").write_text("NOT JSON", encoding="utf-8")
    with caplog.at_level("ERROR"):
        got = repo.load_latest_by_playbook("pb")
    assert got is not None and got.step_idx == 2       # 退回**最近的有效**版本
    # 退版是降級不是正常路徑：靜默退版會讓人以為讀到的是最新進度。
    assert "退回保留版本" in caplog.text


def test_when_every_retained_version_is_also_corrupt_it_still_fails_loud(tmp_path):
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    repo.save_checkpoint("pb", _cp())
    for q in [tmp_path / "pb.checkpoint.json", *retained_paths(tmp_path / "pb.checkpoint.json")]:
        q.write_text("NOT JSON", encoding="utf-8")
    with pytest.raises(CheckpointCorruptError):
        repo.load_latest_by_playbook("pb")


def test_the_retention_count_is_clamped_to_a_declared_range():
    assert 0 <= STATE_RETAIN_VERSIONS <= 9


def test_retained_versions_do_not_show_up_as_separate_checkpoints(tmp_path):
    # `.v1` 刻意不進 `*.checkpoint.json` 的 glob 面 ⇒ 列舉面不會把它當獨立條目。
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    repo.save_checkpoint("pb", _cp())
    assert len(repo.list_recent_checkpoints()) == 1


# ══════════════════════════════════════════════════════════════════════════════
# ④ 保留版本的輪替時序（R100 收尾 blocker，DEF-200-217 §E 同輪）
#
# 修法前 `save_checkpoint` 的順序是「先把現行主檔推成 .v1、再 os.replace(tmp, 主檔)」。
# 兩個換名之間有一個**主檔目錄項不存在**的視窗；replace 在那裡失敗（ENOSPC 不需斷電
# 就到得了）或斷電，主檔就此消失 ⇒ `load_latest_by_playbook` 走 `not p.exists()` 回
# None ＝「沒有 checkpoint」，呼叫端靜默從 step 0 重跑整份 playbook，而旁邊那份剛被推
# 過去的**有效** .v1 一個字都不會被讀到。這正是同輪 ② 修好的「CORRUPT ≠ None」被繞過
# 的第二條路：損壞與沒有分家了，「有效的舊版本」卻仍然變成「沒有」。
# ⇒ 判準掛在「換名失敗之後主檔還在不在」，不是掛在寫法上。
# ══════════════════════════════════════════════════════════════════════════════
def _enospc_when(pred):
    """回傳一個 `Path.replace` 的替身：`pred(self)` 為真時拋 ENOSPC，否則照做。"""
    real = Path.replace

    def spy(self, target):
        if pred(self):
            raise OSError(errno.ENOSPC, "No space left on device")
        return real(self, target)
    return spy


def test_a_failed_main_swap_never_makes_the_checkpoint_look_absent(tmp_path, monkeypatch):
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())                  # 已有一份有效主檔（step_idx=2）
    p = tmp_path / "pb.checkpoint.json"

    newer = _cp()
    newer.step_idx = 4
    monkeypatch.setattr(Path, "replace", _enospc_when(lambda q: q.suffix == ".tmp"))
    with pytest.raises(StateRepositoryError):          # 儲存失敗必須 loud，這一格不變
        repo.save_checkpoint("pb", newer)
    monkeypatch.undo()

    # 🔴 判準本體：換名失敗後主檔仍在，且讀回來是**上一份有效的進度**——不是 None。
    # 修法前這一格拿到 None（主檔已被推成 .v1），呼叫端會從 step 0 重跑。
    got = repo.load_latest_by_playbook("pb")
    assert got is not None, "主檔在換名失敗後消失了 ⇒ 呼叫端會靜默從 step 0 重跑"
    assert got.step_idx == 2
    # 第二個獨立判準：失敗的儲存**一份既有版本都不准動**（修法前這裡會多一個 .v1）。
    assert retained_paths(p) == [], "換名還沒成功就已經動了保留版本 ⇒ 輪替跑在 replace 之前"


def test_a_failed_retention_degrades_loudly_instead_of_failing_the_save(
        tmp_path, monkeypatch, caplog):
    """輪替**自己**失敗時的 fail-safe 方向：保留版本是主檔的補網、不是主線。

    主檔此刻已就位且內容已 fsync ⇒ 讓儲存跟著失敗會把一次成功的落盤變成例外；
    但靜默吞掉會讓人以為「還有退版可用」。所以是「降級 ＋ 出聲」。
    """
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb", _cp())
    monkeypatch.setattr(
        Path, "write_bytes",
        lambda self, data: (_ for _ in ()).throw(OSError(errno.ENOSPC, "No space")))
    newer = _cp()
    newer.step_idx = 4
    with caplog.at_level("WARNING"):
        repo.save_checkpoint("pb", newer)              # 不得拋
    monkeypatch.undo()

    assert repo.load_latest_by_playbook("pb").step_idx == 4   # 主檔就是新的那一份
    assert "保留版本輪替失敗" in caplog.text                   # 降級必須看得見
    # 半套的暫存檔不得留在原地（它若叫 `.v*` 會讓 retained_paths 的 int() 當場炸）。
    assert not (tmp_path / "pb.checkpoint.json.prev.tmp").exists()
    assert retained_paths(tmp_path / "pb.checkpoint.json") == []
