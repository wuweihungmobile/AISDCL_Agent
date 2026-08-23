"""R100 P2-C（PRD §4.5.9 ／ §8-8，v2.1.9 條文）：髒污工作樹存檔救援序列。

驗收判準 D1~D9（含 D5b／D8b）逐格對映到本檔的具名測試。每一個真 worktree 都用真 git
建（沒有 mock git 的版本——本節要治的失效形態全部住在 git 自己的射程裡）。
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from autoclaude.infra.adapters import dirty_worktree_rescue as R
from autoclaude.utils.disk_space import InsufficientSpaceError
from tests.helpers.static_vocab import forbidden_hits


def _git(wt: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(wt), *args],
                       capture_output=True, text=True, check=False,
                       encoding="utf-8", errors="replace")
    assert p.returncode in (0, 1), f"git {args} rc={p.returncode}: {p.stderr}"
    return p.stdout


def _repo(tmp_path: Path, *, ignore_autoclaude: bool = True) -> Path:
    wt = tmp_path / "wt"
    wt.mkdir()
    _git(wt, "init", "-q", ".")
    _git(wt, "config", "user.email", "t@t")
    _git(wt, "config", "user.name", "t")
    (wt / "tracked.txt").write_text("a\n", encoding="utf-8")
    (wt / "staged.txt").write_text("s\n", encoding="utf-8")
    (wt / "ren.txt").write_text("r\n", encoding="utf-8")
    (wt / "del.txt").write_text("d\n", encoding="utf-8")
    if ignore_autoclaude:
        (wt / ".gitignore").write_text(".autoclaude/\n", encoding="utf-8")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "init")
    return wt


def _dirty(wt: Path) -> None:
    """把樹弄髒：tracked 修改 ＋ untracked 新檔（D1 要求兩者同時在，否則 D8 跑不到）。"""
    (wt / "tracked.txt").write_text("a2\n", encoding="utf-8")
    (wt / "brand_new.py").write_text("print('new')\n", encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# D1：不含改動工作樹的動詞；救援後 status --porcelain 逐字不變
# ══════════════════════════════════════════════════════════════════════════════
# argv 元素層級的禁用詞（判準＝非 docstring 的字串常數，見 tests/helpers/static_vocab.py）
_FORBIDDEN = ("stash", "--no-verify", "--3way", "add", "checkout", "restore",
              "clean", "switch", "--hard", "--keep", "--merge")


def test_d1_static_the_source_never_names_a_worktree_mutating_verb():
    hits = forbidden_hits(R.__file__, _FORBIDDEN)
    assert hits == [], f"救援序列出現改動工作樹／禁用的形態：{hits}"


def test_d1_the_static_scan_actually_discriminates():
    # 紅綠自證：上一格「hits == []」若是因為 helper 抓不到任何字串常數而空，它就是假綠。
    # 拿兩個**真的在指令裡**的動詞當注入項，必須被抓到。
    assert forbidden_hits(R.__file__, ("apply", "read-tree")) == ["apply", "read-tree"]


def test_d1_the_worktree_is_byte_identically_unchanged(tmp_path):
    wt = _repo(tmp_path)
    _dirty(wt)
    _git(wt, "add", "staged.txt")            # 前置：真索引裡先有 staged 變更
    (wt / "staged.txt").write_text("s2\n", encoding="utf-8")
    _git(wt, "add", "staged.txt")
    before = R.status_porcelain(wt)
    assert " M tracked.txt" in before and "?? brand_new.py" in before
    res = R.rescue_dirty_worktree(wt, tmp_path / "ck", agent_id="agent-1")
    assert res.status == R.SAVED, res.reason
    assert R.status_porcelain(wt) == before
    # 真索引也不得被動到（第二道閘走臨時索引，不吃真索引）
    assert "staged.txt" in _git(wt, "diff", "--cached", "--name-only")


def test_d1_precondition_the_checkpoint_dir_is_inside_the_exclude_surface(tmp_path):
    # R-4.5.9-1 末段的**規範性前置斷言**：不得只依賴 §6.1 在別處驗過。
    wt = _repo(tmp_path)
    assert R._selfrecursion_hazard(wt, wt / ".autoclaude" / "checkpoints") == ""


# ══════════════════════════════════════════════════════════════════════════════
# D2：落地路徑／檔名／連續兩次救援產出兩個檔
# ══════════════════════════════════════════════════════════════════════════════
def test_d2_two_consecutive_rescues_produce_two_files(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    a = R.rescue_dirty_worktree(wt, ck, agent_id="agent-1")
    b = R.rescue_dirty_worktree(wt, ck, agent_id="agent-1")
    assert a.status == b.status == R.SAVED
    assert len(list(ck.glob("dirty-*.patch"))) == 2, sorted(p.name for p in ck.iterdir())
    assert a.patch_path != b.patch_path


def test_d2_the_timestamp_carries_an_offset(tmp_path):
    # 鐵律三：naive 本地時間戳跨 DST 相減完全靜默 ⇒ 檔名裡的時間戳必須帶 offset。
    # 用 regex 而不是 split("-")：offset 本身就含 `-`（西經時區），而 agent_id 也可能含 `-`
    # ⇒ 位置索引在別台機器上會抓到別的欄位（本輪自己踩到一次）。
    name = R.patch_filename("agent-1", "abc1234")
    m = re.fullmatch(r"dirty-agent-1-(\d{8}T\d{6}[+-]\d{4})-abc1234\.patch", name)
    assert m, name


def test_d2_the_short_sha_is_the_head_taken_before_part_one(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    head = _git(wt, "rev-parse", "--short", "HEAD").strip()
    res = R.rescue_dirty_worktree(wt, ck, agent_id="agent-1")
    assert res.base_sha == head
    assert Path(res.patch_path).name.endswith(f"-{head}.patch")


# ══════════════════════════════════════════════════════════════════════════════
# D3：驗證真的重新開檔（截半 ⇒ 必須判失敗）＋ 紅綠自證
# ══════════════════════════════════════════════════════════════════════════════
def test_d3_a_truncated_patch_is_caught_because_the_check_re_reads_the_disk(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    real_write = R._write_atomically

    def truncating_write(target: Path, blob: bytes) -> int:
        # 模擬磁碟滿的典型形態：最後一個 block 寫不進去。回報的 n_written 仍是完整長度
        # （寫入端以為自己寫完了）⇒ 只有「重新開檔讀回」這一步分得出來。
        if target.suffix == ".patch":
            real_write(target, blob[: len(blob) // 2])
            return len(blob)
        return real_write(target, blob)

    R._write_atomically = truncating_write
    try:
        res = R.rescue_dirty_worktree(wt, ck, agent_id="agent-1", retries=0)
    finally:
        R._write_atomically = real_write
    assert res.status == R.DIRTY_UNSAVED
    assert res.bytes_read_back != res.bytes_written
    assert res.expected_checksum and res.actual_checksum
    assert res.expected_checksum != res.actual_checksum


def test_d3_control_group_verifying_the_write_buffer_would_pass_the_truncated_patch():
    # 紅綠自證（PRD D3 逐字要求的對照組）：「用寫入時的 buffer 算」對截半的檔會相等
    # ⇒ 上一格的鑑別力完全來自「重新開檔讀回」，不是來自 SHA-256 本身。
    import hashlib
    blob = b"x" * 100
    on_disk = blob[:50]
    assert hashlib.sha256(blob).hexdigest() == hashlib.sha256(blob).hexdigest()
    assert hashlib.sha256(on_disk).hexdigest() != hashlib.sha256(blob).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# D4：驗證失敗 ⇒ DIRTY_UNSAVED ＋ 通知恰好一次 ＋ 四個可重驗值；控制組：成功 ⇒ 無通知
# ══════════════════════════════════════════════════════════════════════════════
def test_d4_failure_notifies_exactly_once_and_carries_the_four_values(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    seen: list[str] = []
    res = R.rescue_dirty_worktree(
        wt, ck, agent_id="a", retries=0, notifier=seen.append,
        space_check=lambda _n: (_ for _ in ()).throw(InsufficientSpaceError("no space")))
    assert res.status == R.DIRTY_UNSAVED
    assert len(seen) == 1, seen
    assert "DIRTY_UNSAVED" in seen[0]
    for value in ("patch_path", "expected_checksum", "actual_checksum",
                  "bytes_written", "bytes_read_back"):
        assert hasattr(res, value)


def test_d4_control_group_success_notifies_nobody(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    seen: list[str] = []
    res = R.rescue_dirty_worktree(wt, ck, agent_id="a", notifier=seen.append)
    assert res.status == R.SAVED and seen == []


# ══════════════════════════════════════════════════════════════════════════════
# D5 / D5b：空 patch、以及「非空但內容不足」都不得被判成成功
# ══════════════════════════════════════════════════════════════════════════════
def test_d5_an_empty_patch_is_not_a_successful_rescue(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"      # 乾淨的樹 ⇒ 兩段都空
    res = R.rescue_dirty_worktree(wt, ck, agent_id="a", retries=0)
    assert res.status == R.DIRTY_UNSAVED
    assert "0 bytes" in res.reason


def test_d5b_non_empty_but_incomplete_is_not_a_successful_rescue(tmp_path):
    # 注入「① 有輸出、② 為空」：patch 非空（(c) 過了）而 untracked 那一半不見了
    # ⇒ 只有 (d) 覆蓋率擋得下來。這一格就是 (c) 與 (d) 之間那道界線的守衛。
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    real = R.build_patch_bytes

    def only_part_one(worktree):
        blob, expected = real(worktree)
        head = blob.split(b"diff --git a/brand_new.py")[0]
        return head, expected

    R.build_patch_bytes = only_part_one
    try:
        res = R.rescue_dirty_worktree(wt, ck, agent_id="a", retries=0)
    finally:
        R.build_patch_bytes = real
    assert res.status == R.DIRTY_UNSAVED
    assert res.bytes_written > 0                    # (c) 通過——非空
    assert "brand_new.py" in res.reason             # (d) 才擋下來


# ══════════════════════════════════════════════════════════════════════════════
# D6：重試上限
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("retries", [0, 1, 2])
def test_d6_permanent_failure_stops_at_retries_plus_one_attempts(tmp_path, retries):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    calls: list[int] = []

    def always_out_of_space(n: int) -> None:
        calls.append(n)
        raise InsufficientSpaceError("permanently full")

    res = R.rescue_dirty_worktree(wt, ck, agent_id="a", retries=retries,
                                  space_check=always_out_of_space)
    assert res.status == R.DIRTY_UNSAVED
    assert len(calls) == retries + 1, calls          # 總寫入嘗試 = 本值 + 1
    assert res.attempts == retries + 1


def test_d6_the_retry_ceiling_is_clamped_to_the_declared_range():
    assert R.DIRTY_SAVE_RETRIES_MAX == 3
    assert 0 <= R.DIRTY_SAVE_RETRIES_DEFAULT <= R.DIRTY_SAVE_RETRIES_MAX


def test_d6_the_space_check_runs_before_the_write(tmp_path):
    # G7 同型：以呼叫順序斷言。順序反了必須紅——這正是本條的全部價值。
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    order: list[str] = []
    real_write = R._write_atomically
    R._write_atomically = lambda t, b: (order.append("write"), real_write(t, b))[1]
    try:
        R.rescue_dirty_worktree(wt, ck, agent_id="a",
                                space_check=lambda _n: order.append("space"))
    finally:
        R._write_atomically = real_write
    assert order[0] == "space", order


# ══════════════════════════════════════════════════════════════════════════════
# D7：第二道語意閘的形態 ＋ 三道控制組（每一道都必須紅）
# ══════════════════════════════════════════════════════════════════════════════
def _rescued(tmp_path) -> tuple[Path, Path, str]:
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    _git(wt, "add", "staged.txt")
    (wt / "staged.txt").write_text("s2\n", encoding="utf-8")
    _git(wt, "add", "staged.txt")
    res = R.rescue_dirty_worktree(wt, ck, agent_id="a")
    assert res.status == R.SAVED, res.reason
    return wt, Path(res.patch_path), res.base_sha


def test_d7_the_prescribed_form_passes_even_with_staged_changes(tmp_path):
    wt, patch, base = _rescued(tmp_path)
    ok, detail = R.semantic_gate(wt, patch, base, patch.parent / ".idx")
    assert ok, detail


def test_d7_control_i_a_bare_apply_check_on_a_dirty_tree_is_structurally_red(tmp_path):
    wt, patch, _ = _rescued(tmp_path)
    p = subprocess.run(["git", "-C", str(wt), "apply", "--check", str(patch)],
                       capture_output=True, text=True, check=False,
                       encoding="utf-8", errors="replace")
    assert p.returncode != 0, "天真寫法竟然通過了 ⇒ 本控制組失去意義"


def test_d7_control_ii_the_real_index_variant_is_a_false_red(tmp_path):
    wt, patch, _ = _rescued(tmp_path)
    p = subprocess.run(["git", "-C", str(wt), "apply", "--check", "--cached", str(patch)],
                       capture_output=True, text=True, check=False,
                       encoding="utf-8", errors="replace")
    assert p.returncode != 0, "吃真索引的 --cached 在有 staged 變更時竟然通過了"


def test_d7_control_iii_three_way_fuzzes_a_non_applying_patch_green(tmp_path):
    # `--3way` 會把「套不上」fuzz 成綠 ⇒ 禁用。用一個基準錯的 patch 示範。
    wt, patch, base = _rescued(tmp_path)
    _git(wt, "commit", "-qam", "advance HEAD")      # 讓 HEAD 前進一格
    idx = patch.parent / ".idx3"
    env = {**os.environ, "GIT_INDEX_FILE": str(idx)}
    subprocess.run(["git", "-C", str(wt), "read-tree", "HEAD"], env=env, check=True)
    strict = subprocess.run(
        ["git", "-C", str(wt), "apply", "--check", "--cached", str(patch)],
        capture_output=True, env=env, check=False)
    fuzzed = subprocess.run(
        ["git", "-C", str(wt), "apply", "--check", "--cached", "--3way", str(patch)],
        capture_output=True, env=env, check=False)
    idx.unlink(missing_ok=True)
    assert strict.returncode != 0, "基準錯的 patch 竟然嚴格模式也過"
    assert fuzzed.returncode == 0, "--3way 沒有 fuzz 成綠 ⇒ 本控制組失去意義"


def test_d7_the_wrong_base_is_rejected(tmp_path):
    wt, patch, base = _rescued(tmp_path)
    _git(wt, "commit", "-qam", "advance HEAD")
    new_head = _git(wt, "rev-parse", "--short", "HEAD").strip()
    assert new_head != base
    ok, detail = R.semantic_gate(wt, patch, new_head, patch.parent / ".idx2")
    assert not ok, detail


def test_d7_a_garbage_patch_returns_a_non_zero_that_is_not_one(tmp_path):
    # 判準是 `rc == 0`，不是「rc == 1 才算失敗」：截半的 patch 實測回 rc=128。
    wt, patch, base = _rescued(tmp_path)
    raw = patch.read_bytes()
    patch.write_bytes(raw[: len(raw) // 2])
    ok, detail = R.semantic_gate(wt, patch, base, patch.parent / ".idx4")
    assert not ok
    assert "rc=" in detail and "rc=0" not in detail


def test_d7_the_temp_index_is_deleted_afterwards(tmp_path):
    wt, patch, base = _rescued(tmp_path)
    idx = patch.parent / ".idx5"
    R.semantic_gate(wt, patch, base, idx)
    assert not idx.exists()


# ══════════════════════════════════════════════════════════════════════════════
# D8：母體是 tracked ∪ untracked（＋紅綠自證）
# ══════════════════════════════════════════════════════════════════════════════
def test_d8_the_patch_covers_the_untracked_new_file(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    res = R.rescue_dirty_worktree(wt, ck, agent_id="a")
    assert res.status == R.SAVED, res.reason
    body = Path(res.patch_path).read_text(encoding="utf-8")
    assert "diff --git a/brand_new.py b/brand_new.py" in body
    assert "brand_new.py" in res.expected_paths


def test_d8_red_green_reverting_to_git_diff_head_alone_turns_d8_red(tmp_path):
    """🔴 本列的鑑別力憑證（PRD D8 逐字：不可省）。

    把實作退回「維持現行 `git diff HEAD` 單一來源」⇒ D8 必須紅。立案實測：單一來源下
    patch 非空、四道斷言（改前只有三道）全綠、`grep -c 'brand_new'` ⇒ 0。
    """
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _dirty(wt)
    real = R.build_patch_bytes

    def single_source(worktree):
        rc, part1 = R._git(worktree, "diff", "HEAD", "--binary", "--no-color")
        assert rc == 0
        return part1, R._z_paths(worktree, "diff", "HEAD", "--name-only", "-z")

    R.build_patch_bytes = single_source
    try:
        res = R.rescue_dirty_worktree(wt, ck, agent_id="a", retries=0)
        body = Path(res.patch_path).read_text(encoding="utf-8")
    finally:
        R.build_patch_bytes = real
    # 舊實作的四個「證據」逐字重現：patch 非空、SAVED、而全新檔一個字都沒有。
    assert res.status == R.SAVED           # ← 舊母體下它是「成功」
    assert res.bytes_written > 0
    assert body.count("brand_new") == 0    # ← 全新工作被靜默丟掉
    # 而同一棵樹在**新**母體下必須涵蓋它 ⇒ D8 的紅綠差就在這裡
    fresh = R.rescue_dirty_worktree(wt, ck, agent_id="a")
    assert Path(fresh.patch_path).read_text(encoding="utf-8").count("brand_new") > 0


# ══════════════════════════════════════════════════════════════════════════════
# D8b：(d) 的比對是「兩側任一」；反向控制組
# ══════════════════════════════════════════════════════════════════════════════
def test_d8b_a_rename_is_covered_although_the_two_sides_differ(tmp_path):
    wt, ck = _repo(tmp_path), tmp_path / "ck"
    _git(wt, "mv", "ren.txt", "renamed.txt")
    (wt / "del.txt").unlink()
    (wt / "tracked.txt").write_text("a2\n", encoding="utf-8")
    (wt / "brand.py").write_text("x\n", encoding="utf-8")
    res = R.rescue_dirty_worktree(wt, ck, agent_id="a")
    body = Path(res.patch_path).read_text(encoding="utf-8")
    assert "diff --git a/ren.txt b/renamed.txt" in body      # 兩側不同名（實測形態）
    assert "renamed.txt" in res.expected_paths               # --name-only 只報新名
    assert res.status == R.SAVED, res.reason


def test_d8b_the_naive_both_sides_form_would_be_a_false_red():
    # 假紅示範：寫成 `a/<p> b/<p>` 的實作對改名判失敗，而 patch 其實完整涵蓋了它。
    header = "diff --git a/ren.txt b/renamed.txt\n"
    assert R.patch_covers(header, ["renamed.txt"]) == []
    assert "a/renamed.txt b/renamed.txt" not in header      # 兩側同名的字面不存在


def test_d8b_reverse_control_a_genuinely_missing_path_is_still_red():
    # 反向控制組：「兩側任一」放寬到最後不得變成「只要 patch 非空就算涵蓋」。
    header = "diff --git a/keep.txt b/keep.txt\n"
    assert R.patch_covers(header, ["keep.txt", "gone.txt"]) == ["gone.txt"]


# ══════════════════════════════════════════════════════════════════════════════
# D9：patch 檔不得被列舉進自己
# ══════════════════════════════════════════════════════════════════════════════
def test_d9_ignored_checkpoint_dir_inside_the_repo_is_not_self_recursive(tmp_path):
    wt = _repo(tmp_path, ignore_autoclaude=True)
    _dirty(wt)
    ck = wt / ".autoclaude" / "checkpoints"
    before = R.status_porcelain(wt)
    res = R.rescue_dirty_worktree(wt, ck, agent_id="a")
    assert res.status == R.SAVED, res.reason
    body = Path(res.patch_path).read_text(encoding="utf-8")
    assert Path(res.patch_path).name not in body            # grep -c 自身檔名 ⇒ 0
    assert R.status_porcelain(wt) == before


def test_d9_an_unignored_checkpoint_dir_inside_the_repo_is_refused(tmp_path):
    wt = _repo(tmp_path, ignore_autoclaude=False)
    _dirty(wt)
    seen: list[str] = []
    res = R.rescue_dirty_worktree(wt, wt / ".autoclaude" / "checkpoints",
                                  agent_id="a", notifier=seen.append)
    assert res.status == R.DIRTY_UNSAVED
    assert ".gitignore" in res.reason
    assert len(seen) == 1
