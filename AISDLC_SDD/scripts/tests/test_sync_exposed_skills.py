"""_rmtree_windows_safe() Windows 韌性 rmtree 意圖鎖（R15 ARCH-R15-REV-3）。

WHY：
sync_exposed_skills.py --write 模式的 `_rmtree_windows_safe()`（R15 SCAN-B-2 修復）
在真實 CI/nightly/hook 管線中從未被觸發——`--write` 只由人工手動呼叫，`--check`
（ci-gate 唯一自動路徑）不會走到這支函式；POSIX 上唯讀屬性亦很少真的讓 unlink
失敗（刪除只需父目錄可寫）。故其 chmod-retry 與 TypeError fallback 兩條防禦路徑
零測試覆蓋、零自動化訊號（R15 四方一審 Architect ARCH-R15-REV-3 揭露）。本測試
以 mock 直接驅動 shutil.rmtree 呼叫 onerror callback，模擬 Windows 唯讀/暫鎖
情境，鎖住三態：正常刪除零副作用、chmod-retry 成功、TypeError fallback 回拋
原始錯誤、最終仍失敗時包裝為帶可讀訊息的 RuntimeError。
"""
from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from scripts import sync_exposed_skills


def test_normal_deletion_has_no_side_effect(tmp_path):
    """無錯誤觸發的正常刪除路徑：與裸 shutil.rmtree 行為等價，零副作用。"""
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "file.txt").write_text("data", encoding="utf-8")
    sync_exposed_skills._rmtree_windows_safe(str(victim))
    assert not victim.exists()


def test_chmod_retry_succeeds_after_permission_error(tmp_path):
    """onerror 觸發後 chmod 清唯讀 + func(p) 重試成功 → 正常返回，不拋例外。"""
    target = str(tmp_path / "locked_file.txt")
    retry_func = mock.Mock()  # 呼叫不拋例外＝模擬重試成功

    def fake_rmtree(path, onerror):
        exc_info = (PermissionError, PermissionError("denied"), None)
        onerror(retry_func, target, exc_info)

    with mock.patch.object(sync_exposed_skills.shutil, "rmtree",
                            side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod") as fake_chmod:
        sync_exposed_skills._rmtree_windows_safe(str(tmp_path))
    fake_chmod.assert_called_once_with(target, sync_exposed_skills.stat.S_IWRITE)
    retry_func.assert_called_once_with(target)


def test_typeerror_from_fd_based_rmtree_reraises_original_error(tmp_path):
    """R15 沙盒煙測實證：Python 3.11 POSIX fd-based rmtree 的 func 可能是
    os.open（簽名不符）→ func(p) 重試拋 TypeError；須回拋「原始」錯誤（非
    TypeError 本身），外層再包裝為可讀 RuntimeError，不洩漏裸 TypeError。
    """
    target = str(tmp_path / "x")

    def retry_func_raises_typeerror(p):
        raise TypeError("os.open() missing required argument: 'flags'")

    def fake_rmtree(path, onerror):
        exc_info = (PermissionError, PermissionError("original failure"), None)
        onerror(retry_func_raises_typeerror, target, exc_info)

    with mock.patch.object(sync_exposed_skills.shutil, "rmtree",
                            side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod"):
        with pytest.raises(RuntimeError, match="無法刪除舊父層鏡像"):
            sync_exposed_skills._rmtree_windows_safe(str(tmp_path))


def test_persistent_failure_wrapped_with_readable_message(tmp_path):
    """chmod 後重試仍 OSError（檔案遭編輯器/防毒暫鎖）→ 外層包裝為帶路徑與
    可讀提示訊息的 RuntimeError，不留裸 traceback。
    """
    target = str(tmp_path / "still_locked")

    def retry_func_raises_oserror(p):
        raise OSError("still locked by another process")

    def fake_rmtree(path, onerror):
        exc_info = (PermissionError, PermissionError("original"), None)
        onerror(retry_func_raises_oserror, target, exc_info)

    outer_path = str(tmp_path)
    with mock.patch.object(sync_exposed_skills.shutil, "rmtree",
                            side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod"):
        with pytest.raises(RuntimeError) as exc_info:
            sync_exposed_skills._rmtree_windows_safe(outer_path)
    msg = str(exc_info.value)
    assert "請關閉佔用該目錄的編輯器/防毒後重試" in msg
    # 外層錯誤訊息引用的是 _rmtree_windows_safe 的最外層參數（呼叫者傳入的
    # 鏡像根目錄），不是 onerror 內部觸發失敗的個別檔案路徑（target）。
    assert outer_path in msg


def test_rmtree_failure_message_names_the_mirror_it_was_deleting(tmp_path):
    """整合輪 116：AutoClaude 目標刪不掉時，訊息要指名 AutoClaude 鏡像而不是「父層」；
    預設 label 仍是「父層」（上面兩個既有測試鎖的就是那個舊訊息，逐字不變）。"""
    def retry_func_raises_oserror(p):
        raise OSError("still locked")

    def fake_rmtree(path, onerror):
        onerror(retry_func_raises_oserror, str(tmp_path / "f"), (PermissionError, PermissionError("x"), None))

    with mock.patch.object(sync_exposed_skills.shutil, "rmtree", side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod"):
        with pytest.raises(RuntimeError, match="無法刪除舊AutoClaude鏡像"):
            sync_exposed_skills._rmtree_windows_safe(str(tmp_path), label="AutoClaude")


# ── 整合輪 116／G-116-13／DEF-200-549：多目標鏡像（parent＋autoclaude）──────────────────────────
#
# WHY：Claude Code 對 skills 採「最具體者優先」，在 `AutoClaude/` 的檔案上，`AutoClaude/.claude/skills`
# （曾是 AISDLC v0.09 的 33 支舊版）壓過 `AISDLC_SDD:` 前綴，叫到的是缺 sdd-gate 等的非 SDD 版。
# 它因此必須和父層一樣是 LATEST 的機械鏡像、同被 `--check` 守。以下全用 tmp 造的假 repo，不碰真實樹。

_LATEST = {"alpha/SKILL.md": "alpha v2\n", "beta/SKILL.md": "beta v2\n", "README.md": "readme v2\n"}
_STALE = {"alpha/SKILL.md": "alpha v1\n", "old-only/SKILL.md": "legacy\n"}


def _put(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _fake_repo(tmp_path: Path, *, parent=_LATEST, autoclaude=_LATEST, with_autoclaude_dir=True) -> tuple[Path, Path]:
    """回 `(repo_root＝<tmp>/AISDLC_SDD, autoclaude 專案目錄)`；parent／autoclaude＝該鏡像的現況內容
    （None＝不建 `.claude/skills`）；`with_autoclaude_dir=False`＝獨立 checkout（連 AutoClaude 目錄都沒有）。"""
    repo = tmp_path / "AISDLC_SDD"
    _put(repo / "AISDLC_SDD_v0.01" / ".claude" / "skills", {"alpha/SKILL.md": "ancient\n"})  # 較舊版，不得被選
    _put(repo / "AISDLC_SDD_v0.02" / ".claude" / "skills", _LATEST)
    if parent is not None:
        _put(repo / ".claude" / "skills", parent)
    ac = tmp_path / "AutoClaude"
    if with_autoclaude_dir:
        ac.mkdir()
        if autoclaude is not None:
            _put(ac / ".claude" / "skills", autoclaude)
    return repo, ac


def test_check_green_when_both_targets_mirror_latest(tmp_path, capsys):
    repo, _ = _fake_repo(tmp_path)
    assert sync_exposed_skills.check(str(repo)) == 0
    out = capsys.readouterr().out
    assert "OK：父層 .claude/skills == LATEST(AISDLC_SDD_v0.02)（3 檔一致）" in out
    assert "OK：AutoClaude/.claude/skills == LATEST(AISDLC_SDD_v0.02)（3 檔一致）" in out


def test_check_red_when_autoclaude_is_stale_and_message_names_the_fix(tmp_path, capsys):
    repo, _ = _fake_repo(tmp_path, autoclaude=_STALE)
    assert sync_exposed_skills.check(str(repo)) == 1
    cap = capsys.readouterr()
    assert "OK：父層 .claude/skills" in cap.out          # 父層仍是綠的，不被 AutoClaude 的紅遮蔽
    assert "STALE：AutoClaude/.claude/skills 與 LATEST(AISDLC_SDD_v0.02) 不一致" in cap.err
    assert "缺少（LATEST 有）：beta/SKILL.md" in cap.err
    assert "多餘（LATEST 無）：old-only/SKILL.md" in cap.err
    assert "內容漂移：alpha/SKILL.md" in cap.err
    assert "修復：scripts/sync_exposed_skills.py --write --target autoclaude" in cap.err


def test_check_red_when_parent_is_stale_and_message_names_the_parent_fix(tmp_path, capsys):
    repo, _ = _fake_repo(tmp_path, parent=_STALE)
    assert sync_exposed_skills.check(str(repo)) == 1
    cap = capsys.readouterr()
    assert "STALE：父層 .claude/skills 與 LATEST(AISDLC_SDD_v0.02) 不一致" in cap.err
    assert "修復：scripts/sync_exposed_skills.py --write --target parent" in cap.err


def test_check_skips_autoclaude_when_the_project_dir_is_absent(tmp_path, capsys):
    """獨立 checkout（沒有 AutoClaude 專案）：說一行、略過、不紅；父層照常驗。"""
    repo, ac = _fake_repo(tmp_path, with_autoclaude_dir=False)
    assert sync_exposed_skills.check(str(repo)) == 0
    out = capsys.readouterr().out
    assert "略過 autoclaude 目標" in out and str(ac) in out
    assert "OK：父層 .claude/skills" in out
    assert not ac.exists(), "check 不得替不存在的專案造目錄"


def test_check_autoclaude_dir_present_but_no_skills_dir_is_stale_not_skipped(tmp_path, capsys):
    repo, _ = _fake_repo(tmp_path, autoclaude=None)
    assert sync_exposed_skills.check(str(repo)) == 1
    err = capsys.readouterr().err
    assert "STALE：AutoClaude/.claude/skills" in err
    assert "缺少（LATEST 有）：alpha/SKILL.md" in err


@pytest.mark.parametrize("target, expected_rc", [("parent", 0), ("autoclaude", 1), ("all", 1)])
def test_check_target_selects_which_mirror_is_judged(tmp_path, target, expected_rc):
    """AutoClaude 是 stale、父層是綠的：`--target parent` 不看它（0）；`autoclaude`／`all` 都該紅。"""
    repo, _ = _fake_repo(tmp_path, autoclaude=_STALE)
    assert sync_exposed_skills.check(str(repo), target) == expected_rc


def test_check_target_autoclaude_ignores_a_stale_parent(tmp_path):
    repo, _ = _fake_repo(tmp_path, parent=_STALE)
    assert sync_exposed_skills.check(str(repo), "autoclaude") == 0
    assert sync_exposed_skills.check(str(repo), "parent") == 1


def test_write_all_regenerates_both_mirrors_and_drops_extras(tmp_path, capsys):
    repo, ac = _fake_repo(tmp_path, parent=_STALE, autoclaude=_STALE)
    assert sync_exposed_skills.write(str(repo)) == 0
    out = capsys.readouterr().out
    assert "重生父層鏡像（3 檔）" in out and "重生AutoClaude鏡像（3 檔）" in out
    want = {k: v.encode("utf-8") for k, v in _LATEST.items()}
    assert _tree(repo / ".claude" / "skills") == want
    assert _tree(ac / ".claude" / "skills") == want
    assert sync_exposed_skills.check(str(repo)) == 0


def test_write_target_parent_leaves_autoclaude_byte_identical(tmp_path):
    """`--write --target parent` 絕不能順手動 AutoClaude 鏡像（那是淨減法，要在收尾單人窗口明確執行）。"""
    repo, ac = _fake_repo(tmp_path, parent=_STALE, autoclaude=_STALE)
    before = _tree(ac / ".claude" / "skills")
    assert sync_exposed_skills.write(str(repo), "parent") == 0
    assert _tree(ac / ".claude" / "skills") == before
    assert _tree(repo / ".claude" / "skills") == {k: v.encode("utf-8") for k, v in _LATEST.items()}


def test_write_target_autoclaude_leaves_parent_untouched(tmp_path):
    repo, ac = _fake_repo(tmp_path, parent=_STALE, autoclaude=_STALE)
    before = _tree(repo / ".claude" / "skills")
    assert sync_exposed_skills.write(str(repo), "autoclaude") == 0
    assert _tree(repo / ".claude" / "skills") == before
    assert _tree(ac / ".claude" / "skills") == {k: v.encode("utf-8") for k, v in _LATEST.items()}


def test_write_skips_a_missing_autoclaude_project_without_creating_it(tmp_path, capsys):
    repo, ac = _fake_repo(tmp_path, parent=_STALE, with_autoclaude_dir=False)
    assert sync_exposed_skills.write(str(repo)) == 0
    assert "略過 autoclaude 目標" in capsys.readouterr().out
    assert not ac.exists()
    assert sync_exposed_skills.write(str(repo), "autoclaude") == 0   # 明指該目標也一樣略過、不建
    assert not ac.exists()


def test_write_autoclaude_creates_the_skills_dir_when_only_the_project_exists(tmp_path):
    repo, ac = _fake_repo(tmp_path, autoclaude=None)
    assert sync_exposed_skills.write(str(repo), "autoclaude") == 0
    assert _tree(ac / ".claude" / "skills") == {k: v.encode("utf-8") for k, v in _LATEST.items()}


def test_main_defaults_to_all_targets_and_rejects_unknown_target(tmp_path, capsys):
    repo, _ = _fake_repo(tmp_path, autoclaude=_STALE)
    assert sync_exposed_skills.main(["--repo-root", str(repo)]) == 1                       # 預設＝--check＋all
    assert sync_exposed_skills.main(["--repo-root", str(repo), "--target", "parent"]) == 0
    assert sync_exposed_skills.main(["--repo-root", str(repo), "--write"]) == 0            # 預設寫全部
    assert sync_exposed_skills.main(["--repo-root", str(repo), "--check"]) == 0
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc_info:
        sync_exposed_skills.main(["--repo-root", str(repo), "--target", "nonsense"])
    assert exc_info.value.code == 2
