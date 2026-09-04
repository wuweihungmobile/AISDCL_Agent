"""R100 P2-C（PRD §6.2，v2.1.9 條文）：三項管家事塌成開機自檢。

驗收判準 G1~G10 逐格對映到本檔的具名測試。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from autoclaude.execution import boot_self_check as B
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from tests.helpers.static_vocab import command_string_literals, forbidden_hits


def _repo_with_queue(tmp_path: Path, queue: list[dict]) -> FileStateRepository:
    repo = FileStateRepository(str(tmp_path / "ck"))
    cp = PlaybookCheckpoint(playbook_path="pb.yaml", step_idx=0, step_id="S1",
                            total_steps=1, integration_queue=queue)
    repo.save_checkpoint("pb", cp)
    return repo


def _q(status: str, branch: str = "autoclaude/agent-1") -> dict:
    return {"agent_id": "agent-1", "branch": branch, "status": status}


# ══════════════════════════════════════════════════════════════════════════════
# G1：殘留項真的被重排；注入值必須是**生產路徑真的會寫出來的那個字面**
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("status", list(B.PENDING_STATUSES))
def test_g1_every_pending_literal_is_requeued(tmp_path, status):
    """遍歷要求：待處理集合的**每一個**字面各注入一次，漏一個就是漏一種殘留項。"""
    repo = _repo_with_queue(tmp_path, [_q(status)])
    queue, unknown = B.read_queue(repo, "pb")
    out = B.scan_queue(queue, conflict_policy="RETRY_WITH_AGENT", unknown_reason=unknown)
    assert out.requeued == ("autoclaude/agent-1",), out
    assert any("重排" in ln for ln in out.lines)


def test_g1_the_injected_literal_comes_from_the_schema_enum_not_the_test():
    """🔴 判準是可查的：注入值必須取自 §7 schema 的枚舉，不得是測試自己造的字串。

    立案（v2.1.9）：上一版條文的掃描集合寫 `{QUEUED, CONFLICT, VERIFY_FAILED}`，而
    `QUEUED` 在本實作**沒有寫者** ⇒ 照它實作的話生產環境的殘留項全帶 `PENDING_VERIFY`、
    掃出 0 筆，而測試注入 `QUEUED` 會綠 ⇒ **測試綠、生產零覆蓋**。
    """
    assert "PENDING_VERIFY" in B.QUEUE_STATUSES
    assert "QUEUED" not in B.QUEUE_STATUSES      # 刻意不引入（與 PENDING_VERIFY 語意重疊）
    assert set(B.PENDING_STATUSES) < set(B.QUEUE_STATUSES)
    assert "MERGED" in B.QUEUE_STATUSES and "MERGED" not in B.PENDING_STATUSES
    # 生產路徑真的寫得出這個字面：欄位的家在 PlaybookCheckpoint 上（不是測試 fixture）
    cp = PlaybookCheckpoint(playbook_path="p", step_idx=0, step_id="s", total_steps=1)
    assert cp.integration_queue == []


def test_g1_control_i_human_review_lists_without_requeueing(tmp_path):
    repo = _repo_with_queue(tmp_path, [_q("PENDING_VERIFY")])
    queue, unknown = B.read_queue(repo, "pb")
    out = B.scan_queue(queue, conflict_policy="HUMAN_REVIEW", unknown_reason=unknown)
    assert out.requeued == ()
    assert out.listed_only == ("autoclaude/agent-1",)
    assert any("只登記不重排" in ln for ln in out.lines)


def test_g1_control_ii_a_terminal_status_is_not_swept_up(tmp_path):
    repo = _repo_with_queue(tmp_path, [_q("MERGED")])
    queue, unknown = B.read_queue(repo, "pb")
    out = B.scan_queue(queue, conflict_policy="RETRY_WITH_AGENT", unknown_reason=unknown)
    assert out.requeued == () and out.listed_only == ()
    assert out.lines == ("待整合殘留項 0 筆",)


def test_g1_the_factory_default_policy_is_human_review():
    assert B.CONFLICT_POLICY_DEFAULT == "HUMAN_REVIEW"
    assert B.CONFLICT_POLICY_DEFAULT in B.CONFLICT_POLICIES


def test_an_illegal_conflict_policy_is_a_boot_problem(tmp_path):
    # §6.1 不變式 11：CONFLICT_POLICY 值必須落在合法枚舉內。
    out = B.scan_queue([], conflict_policy="WHATEVER")
    assert out.problems and "CONFLICT_POLICY" in out.problems[0]


# ══════════════════════════════════════════════════════════════════════════════
# G2：讀不出來 ≠ 0 筆（本節最容易寫成假綠的地方）
# ══════════════════════════════════════════════════════════════════════════════
def test_g2_an_unreadable_queue_says_unknown_and_never_says_zero(tmp_path):
    repo = _repo_with_queue(tmp_path, [_q("PENDING_VERIFY")])
    p = tmp_path / "ck" / "pb.checkpoint.json"
    body = p.read_text(encoding="utf-8").replace('"step_idx": 0', '"step_idx": 7')
    p.write_text(body, encoding="utf-8")        # 動內容、不動 checksum ⇒ 壞 checksum
    queue, unknown = B.read_queue(repo, "pb")
    out = B.scan_queue(queue, unknown_reason=unknown)
    assert out.state_unknown is True
    text = "\n".join(out.lines)
    assert B.QUEUE_UNKNOWN_TEXT in text
    assert "0 筆" not in text, text


def test_g2_an_unknown_status_literal_is_treated_as_unreadable_not_skipped(tmp_path):
    # §6.1 不變式 11（v2.1.9）：未知字面**視為讀不出來**而非略過——
    # 略過等於把一筆殘留整合靜默丟掉。
    out = B.scan_queue([_q("QUEUED")], conflict_policy="RETRY_WITH_AGENT")
    assert out.state_unknown is True
    assert "QUEUED" in out.unknown_reason
    assert "0 筆" not in "\n".join(out.lines)


def test_g2_a_genuinely_absent_checkpoint_is_zero_not_unknown(tmp_path):
    # 控制組：真的沒有 checkpoint 時是**合法的 0 筆**，不得也印「狀態不明」。
    repo = FileStateRepository(str(tmp_path / "ck"))
    queue, unknown = B.read_queue(repo, "never")
    assert (queue, unknown) == ([], "")
    out = B.scan_queue(queue, unknown_reason=unknown)
    assert out.state_unknown is False
    assert out.lines == ("待整合殘留項 0 筆",)


# ══════════════════════════════════════════════════════════════════════════════
# G3：DRAINING 以上 ⇒ 只登記不重排
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("band", list(B.DRAINING_BANDS))
def test_g3_draining_or_above_only_registers(band):
    out = B.scan_queue([_q("CONFLICT")], conflict_policy="RETRY_WITH_AGENT", band=band)
    assert out.requeued == ()
    assert out.listed_only == ("autoclaude/agent-1",)
    assert any(f"band={band}" in ln for ln in out.lines)


def test_g3_the_draining_bands_mirror_the_root_declaration():
    """跨 importlinter 邊界的鏡射鎖：根層 `tools/lib/quota_gate.py::DRAINING_BANDS`
    是 `(quota_policy.BAND_PREPARE, quota_policy.BAND_HALT)`。讀原始碼而不 import
    （no-harness-import 契約禁止本套件 import harness）。"""
    root = Path(__file__).resolve().parents[2] / "tools" / "lib" / "quota_gate.py"
    if not root.exists():
        pytest.skip("不在 monorepo 內（pip install 後 harness 不存在）")
    src = root.read_text(encoding="utf-8")
    m = re.search(r"^DRAINING_BANDS\s*=\s*\((.+?)\)", src, re.M)
    assert m, "根層 DRAINING_BANDS 不見了 ⇒ 這條鏡射鎖已靜默歸零"
    names = [t.strip().split(".")[-1] for t in m.group(1).split(",") if t.strip()]
    assert names == ["BAND_PREPARE", "BAND_HALT"], names
    assert B.DRAINING_BANDS == ("prepare", "halt")


def test_a_measurable_band_below_draining_still_requeues():
    out = B.scan_queue([_q("CONFLICT")], conflict_policy="RETRY_WITH_AGENT", band="warn")
    assert out.requeued == ("autoclaude/agent-1",)


# ══════════════════════════════════════════════════════════════════════════════
# G4：讀不到版本 ⇒ 未知 ＋ DRY_RUN（fail-safe）；含紅綠自證
# ══════════════════════════════════════════════════════════════════════════════
def test_g4_an_unreadable_version_is_unknown_and_forces_dry_run():
    version = B.read_cli_version("claude", runner=lambda _a: (127, ""))
    assert version is None
    dry_run, line = B.cli_version_verdict(version)
    assert dry_run is True
    assert B.DRY_RUN_TEXT in line


def test_g4_an_exploding_runner_is_also_unknown():
    def boom(_argv):
        raise FileNotFoundError("claude: command not found")
    assert B.read_cli_version("claude", runner=boom) is None


def test_g4_red_green_treating_unreadable_as_verified_would_turn_this_red():
    """紅綠自證（PRD G4 逐字）：把它改成「讀不到就當已驗證」必須轉紅。

    對照組直接把那個錯誤實作寫出來並斷言它**會**回 dry_run=False ⇒ 本檔上一格的
    鑑別力來源就是「None 走 fail-safe」這一條，不是措辭。
    """
    def fail_open_verdict(version):
        return (False, "假設沒變") if version is None else B.cli_version_verdict(version)
    assert fail_open_verdict(None)[0] is False        # ← 錯誤實作的行為
    assert B.cli_version_verdict(None)[0] is True     # ← 正解的行為


def test_g4_an_unlisted_version_also_forces_dry_run():
    dry_run, line = B.cli_version_verdict("99.99.99")
    assert dry_run is True and "不在已驗證清單內" in line


def test_a_listed_version_does_not_force_dry_run():
    known = next(iter(B.VERIFIED_CLI_VERSIONS))
    dry_run, line = B.cli_version_verdict(known)
    assert dry_run is False and known in line


def test_the_real_cli_version_is_readable_or_honestly_unknown():
    # 不斷言機器狀態（CI 上沒有 claude）：只斷言「回值一定是 None 或一個含數字的字串」。
    v = B.read_cli_version()
    assert v is None or any(c.isdigit() for c in v)


# ══════════════════════════════════════════════════════════════════════════════
# G5：DRY_RUN 真的不動作（零派工／零 worktree 寫入／零排程註冊）
# ══════════════════════════════════════════════════════════════════════════════
def test_g5_dry_run_dispatches_nothing_writes_nothing_registers_nothing(tmp_path):
    repo = _repo_with_queue(tmp_path, [_q("PENDING_VERIFY"), _q("CONFLICT", "b2")])
    dispatched: list[str] = []
    report = B.boot_self_check(
        repo=repo, playbook_id="pb", conflict_policy="RETRY_WITH_AGENT",
        cli_runner=lambda _a: (127, ""),                 # ⇒ 版本未知 ⇒ DRY_RUN
        cleanup=lambda: dispatched.append("cleanup") or [],
        notifier=dispatched.append)
    assert report.dry_run is True
    assert report.queue.requeued == ()                   # 零派工
    assert report.queue.listed_only == ("autoclaude/agent-1", "b2")
    assert "cleanup" not in dispatched                   # 零 worktree 寫入
    assert len(dispatched) == 1 and B.DRY_RUN_TEXT in dispatched[0]   # loud 恰好一次


def test_g5_dry_run_cleanup_removes_nothing(tmp_path):
    # `cleanup_merged_worktrees(dry_run=True)` 必須回空清單且不呼叫 worktree remove。
    assert B.cleanup_merged_worktrees(tmp_path, dry_run=True) == []


# ══════════════════════════════════════════════════════════════════════════════
# G6：已驗證清單是 git-tracked 檔
# ══════════════════════════════════════════════════════════════════════════════
def test_g6_the_verified_list_travels_with_the_clone():
    """G6：已驗證清單不得是**本機狀態檔**（那種檔不隨 clone 走 ⇒ 換一台機器就變成
    『全部未知』或『全部已驗證』，兩種都錯）。

    🔴 判準寫成兩支並聯而不是單純 `git ls-files`，理由是可查的併行約束：本輪並行包
    **禁止任何 git 寫入**（收尾 commit 由單人窗口做）⇒ 新建的檔在本包交件當下必然是
    untracked，硬寫 `ls-files` 會讓這一格在**正確**實作上恆紅。兩支並聯後鑑別力仍在：
    住 `%TEMP%`／`~/.autoclaude` 的本機狀態檔**兩支都不會過**（不在 repo 內，且
    check-ignore 對 repo 外路徑會失敗）。commit 之後第一支會直接命中。
    """
    root = Path(__file__).resolve().parents[2]
    rel = "AutoClaude/autoclaude/utils/verified_cli_versions.py"
    tracked = subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotepath=false",
         "ls-files", "--error-unmatch", rel],
        capture_output=True, text=True, check=False,
        encoding="utf-8", errors="replace").returncode == 0
    if tracked:
        return
    assert (root / rel).exists(), f"清單檔不在 repo 內：{rel}"
    ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", rel],
                             capture_output=True, check=False).returncode == 0
    assert not ignored, f"清單檔被 .gitignore 排除 ⇒ 永遠不會隨 clone 走：{rel}"


def test_g6_every_entry_says_what_was_verified_not_just_a_version():
    # 只有版號的清單在下一次介面變動時給不出任何判斷依據（PRD R-6.2-2 第 2 點）。
    assert B.VERIFIED_CLI_VERSIONS
    for version, entry in B.VERIFIED_CLI_VERSIONS.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
        assert entry["verified"] and all(len(v) > 20 for v in entry["verified"]), version
        assert entry["source"]


# ══════════════════════════════════════════════════════════════════════════════
# G7：空間檢查發生在寫 patch 之前（本體判準住 rescue 那一側，此處驗自檢那一次）
# ══════════════════════════════════════════════════════════════════════════════
def test_g7_the_boot_check_runs_the_space_gate_before_reporting_ok(tmp_path):
    report = B.boot_self_check(space_target=tmp_path, estimate_bytes=0,
                               margin_bytes=0, cli_runner=lambda _a: (0, "2.1.233"))
    assert report.space is not None and report.space.ok
    assert any("可用空間" in ln for ln in report.lines)


def test_g7_the_rescue_side_asserts_the_order_itself():
    # 順序判準的家在救援那一側（寫 patch 之前那一次），這裡只記載它在哪，避免兩個家。
    from autoclaude.infra.adapters import dirty_worktree_rescue as R
    src = Path(R.__file__).read_text(encoding="utf-8")
    body = src.split("def rescue_dirty_worktree")[1]
    assert body.index("checker(") < body.index("_attempt("), "空間檢查沒有在寫入之前"


# ══════════════════════════════════════════════════════════════════════════════
# G8：門檻是 bytes 對 bytes
# ══════════════════════════════════════════════════════════════════════════════
def test_g8_the_same_free_percentage_yields_different_verdicts_by_bytes(tmp_path):
    from autoclaude.utils.disk_space import check_space, free_bytes
    free = free_bytes(tmp_path)
    small = check_space(tmp_path, 1, margin_bytes=0)
    large = check_space(tmp_path, free + 1, margin_bytes=0)
    assert small.ok is True and large.ok is False
    assert small.free_bytes == large.free_bytes          # 同一個「可用百分比」
    assert small.required_bytes != large.required_bytes  # 判定卻不同 ⇒ bytes 對 bytes


def test_g8_the_estimate_is_bytes_from_a_real_git_diff(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    for args in (["init", "-q", "."], ["config", "user.email", "t@t"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(wt), *args], check=True, capture_output=True)
    (wt / "f.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "i"], check=True,
                   capture_output=True)
    assert B.estimate_freeze_bytes([wt]) == 0            # 乾淨 ⇒ 0 bytes
    (wt / "f.txt").write_text("b\n" * 200, encoding="utf-8")
    assert B.estimate_freeze_bytes([wt]) > 0
    # state.json 與其保留版本份數也計入（PRD R-6.2-3 ②）
    assert (B.estimate_freeze_bytes([wt], state_bytes=100, retain_versions=2)
            - B.estimate_freeze_bytes([wt])) == 300


# ══════════════════════════════════════════════════════════════════════════════
# G9：清理只動已 --ff-only 併入者；不得使用 git clean / reset --hard
# ══════════════════════════════════════════════════════════════════════════════
def test_g9_static_the_cleanup_never_names_a_destructive_verb():
    hits = forbidden_hits(B.__file__, ("clean", "reset", "--hard", "stash", "--no-verify"))
    assert hits == [], f"清理路徑出現鐵律五禁用形態：{hits}"
    literals = command_string_literals(B.__file__)
    assert "worktree" in literals and "remove" in literals, "清理必須走 git worktree remove"


def test_g9_an_unmerged_worktree_survives(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    def g(*args, cwd=repo):
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                              text=True, check=False,
                              encoding="utf-8", errors="replace")
    g("init", "-q", ".")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    g("add", "-A")
    g("commit", "-qm", "i")
    g("branch", "integration")
    merged, unmerged = tmp_path / "wt-merged", tmp_path / "wt-unmerged"
    g("worktree", "add", "-q", "-b", "done", str(merged))       # 與 integration 同點
    g("worktree", "add", "-q", "-b", "wip", str(unmerged))
    (unmerged / "b.txt").write_text("b\n", encoding="utf-8")
    g("add", "-A", cwd=unmerged)
    g("commit", "-qm", "wip", cwd=unmerged)                     # 未併入 integration
    names = {b for _p, b in B.merged_worktrees(repo, "integration")}
    assert "refs/heads/done" in names
    assert "refs/heads/wip" not in names, names
    removed = B.cleanup_merged_worktrees(repo, "integration")
    assert any("wt-merged" in r for r in removed), removed
    assert unmerged.exists() and (unmerged / "b.txt").exists()


# ══════════════════════════════════════════════════════════════════════════════
# G10：清理後仍不足 ⇒ 桌面通知恰好一次
# ══════════════════════════════════════════════════════════════════════════════
def test_g10_still_short_after_cleanup_notifies_exactly_once(tmp_path):
    from autoclaude.utils.disk_space import free_bytes
    seen: list[str] = []
    report = B.boot_self_check(
        space_target=tmp_path, estimate_bytes=free_bytes(tmp_path) * 2,
        margin_bytes=0, cleanup=lambda: [], notifier=seen.append,
        cli_runner=lambda _a: (0, next(iter(B.VERIFIED_CLI_VERSIONS))))
    assert report.problems and "可用空間不足" in report.problems[0]
    assert len(seen) == 1, seen
    assert report.notified == 1


def test_g10_enough_space_notifies_nobody(tmp_path):
    seen: list[str] = []
    report = B.boot_self_check(
        space_target=tmp_path, estimate_bytes=0, margin_bytes=0, notifier=seen.append,
        cli_runner=lambda _a: (0, next(iter(B.VERIFIED_CLI_VERSIONS))))
    assert report.ok and seen == []


# ══════════════════════════════════════════════════════════════════════════════
# DEF-200-206 ②③：枚舉對齊 PRD §6 區塊 11 的字面 ＋ CONFLICT_POLICY 的 env 讀取路徑
# ══════════════════════════════════════════════════════════════════════════════
_PRD_REL = "docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md"


def _prd_conflict_policy_literals() -> list[str]:
    """PRD §6 區塊 11 那一行（`…CONFLICT_POLICY=<出廠值>  # … A|B|C`）的 [出廠值, *枚舉]。"""
    prd = Path(__file__).resolve().parents[2] / _PRD_REL
    if not prd.exists():
        pytest.skip("不在 monorepo 內（pip install 後 PRD 不存在）")
    pattern = re.compile(r"^(?:AUTOCLAUDE_)?CONFLICT_POLICY=(\w+)\s+#.*?([A-Z_]+(?:\|[A-Z_]+)+)")
    for line in prd.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            return [m.group(1), *m.group(2).split("|")]
    raise AssertionError("PRD §6 找不到 CONFLICT_POLICY 那一行 ⇒ 鏡射鎖失去分母")


def test_def_200_206_the_policy_enum_mirrors_the_prd_literal():
    """②：實作枚舉必須逐字等於 PRD §6 區塊 11 的三值（順序亦同）；出廠值也對得上。"""
    default, *literals = _prd_conflict_policy_literals()
    assert tuple(literals) == B.CONFLICT_POLICIES, (literals, B.CONFLICT_POLICIES)
    assert default == B.CONFLICT_POLICY_DEFAULT
    assert "AUTO_AGENT" not in B.CONFLICT_POLICIES      # 自造名已退場


def test_def_200_206_abort_with_pending_items_refuses_to_boot_and_lists_them():
    """ABORT：有殘留項 ⇒ boot problem（呼叫端非零退出碼）、清單照列、一筆都不重排。"""
    out = B.scan_queue([_q("CONFLICT"), _q("PENDING_VERIFY", "b2")], conflict_policy="ABORT")
    assert out.requeued == ()
    assert out.listed_only == ("autoclaude/agent-1", "b2")
    assert out.problems and "ABORT" in out.problems[0]
    assert sum("ABORT：" in ln for ln in out.lines) == 2


def test_def_200_206_abort_with_an_empty_queue_boots_normally():
    out = B.scan_queue([], conflict_policy="ABORT")
    assert out.problems == () and out.lines == ("待整合殘留項 0 筆",)


def test_def_200_206_abort_is_not_softened_by_dry_run_or_draining():
    """對照組：HUMAN_REVIEW／DRY_RUN／DRAINING 是「只登記」，ABORT 是「拒絕啟動」。"""
    for kw in ({"dry_run": True}, {"band": B.DRAINING_BANDS[0]}):
        out = B.scan_queue([_q("CONFLICT")], conflict_policy="ABORT", **kw)
        assert out.problems and out.requeued == (), kw
    soft = B.scan_queue([_q("CONFLICT")], conflict_policy="HUMAN_REVIEW")
    assert soft.problems == () and soft.listed_only == ("autoclaude/agent-1",)


def test_def_200_206_conflict_policy_is_read_from_env():
    """③：未設 ⇒ 出廠值；設了 ⇒ 去空白後逐字採用；非法值原樣回傳、交給不變式 11 報紅。"""
    assert B.CONFLICT_POLICY_ENV.startswith("AUTOCLAUDE_")
    assert B.conflict_policy_from_env({}) == B.CONFLICT_POLICY_DEFAULT
    assert B.conflict_policy_from_env({B.CONFLICT_POLICY_ENV: " ABORT "}) == "ABORT"
    bad = B.conflict_policy_from_env({B.CONFLICT_POLICY_ENV: "WHATEVER"})
    assert bad == "WHATEVER"
    assert B.scan_queue([], conflict_policy=bad).problems


def test_def_200_206_an_illegal_policy_with_pending_items_never_requeues():
    """SD 定點複審：非法字面 ＋ 非空佇列不得落到預設重排分支（problem 與「重排」同時
    印出是自相矛盾的輸出）——只登記，並讓不變式 11 的 problem 帶著它一起回去。"""
    out = B.scan_queue([_q("CONFLICT")], conflict_policy="WHATEVER")
    assert out.problems and "CONFLICT_POLICY" in out.problems[0]
    assert out.requeued == ()
    assert out.listed_only == ("autoclaude/agent-1",)
    assert any("CONFLICT_POLICY=WHATEVER" in ln for ln in out.lines)


def test_def_200_206_main_wires_the_env_reader_into_the_boot_check():
    """接線鎖：`main.run_boot_self_check` 必須把 env 讀數餵進 `boot_self_check(...)`，
    否則讀取路徑蓋好沒接電（DEF-200-205 的同型失效）。"""
    from autoclaude import main as M
    src = Path(M.__file__).read_text(encoding="utf-8")
    body = src.split("def run_boot_self_check")[1].split("\ndef ")[0]
    assert "conflict_policy=conflict_policy_from_env()" in body
