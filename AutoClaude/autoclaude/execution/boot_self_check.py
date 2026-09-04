# 開機自檢：把「長駐管家才做得到的事」塌成「醒來時做一次」（PRD §6.2；掛 §6.1 不變式 11~13）。
#
# 立案：§8-11／§8-13／§8-14 三列的原條文都以「長駐 Daemon ＋ 多 worktree 生命週期管理」
# 為前提，而本 repo **刻意不做 Daemon**（§15.3 薄治理層 ＋ 採用原生能力；喚醒改由 OS 排程
# 重啟）⇒ 那個前提在本實作裡不存在。三項的**意圖全部保留、只換實現**——不得標成
# 「架構性不適用」而刪掉，那是把意圖跟實現一起丟掉。
#
# 為什麼「醒來時做一次」覆蓋面不弱於長駐管家：本實作的執行單位就是「一次被排程叫起來的
# 行程」。這三項要處置的事（沒做完的整合、CLI 換版、磁碟滿）**下一次派工之前處置就夠了**。
# 真正必須即時的那一類（撞線喚醒）走的是哨兵巡邏，不在本節射程。
from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..core.ports.quota_meter import BAND_HALT, BAND_PREPARE
from ..core.ports.state_repository import CheckpointCorruptError
from ..utils.disk_space import DEFAULT_MARGIN_BYTES, SpaceVerdict, check_space
from ..utils.verified_cli_versions import VERIFIED_CLI_VERSIONS

logger = logging.getLogger("autoclaude.execution.boot_self_check")

# 🔴 §7 schema 的枚舉（PRD v2.1.9 訂正）。**枚舉必須有單一的家**：§6.2 的掃描集合、
# §6.1 不變式 11 與 §11.6 的驗收都以它為分母，分母若沒有一個家，各處各抄一份的漂移
# 方向是**漏抄**——上一版就是因此把不存在的 `QUEUED` 寫進掃描集合。
QUEUE_STATUSES = ("PENDING_VERIFY", "CONFLICT", "VERIFY_FAILED", "MERGED")
# 待處理集合＝前三者；`MERGED` 是終態（補齊枚舉才使「不在集合內」有意義）。
PENDING_STATUSES = QUEUE_STATUSES[:3]
# 🔴 本次**不引入** `QUEUED`：它與 `PENDING_VERIFY` 語意重疊，而 §7 已經有後者
# ⇒ 引入前者等於給同一個狀態開第二個家，並需要一次沒有必要的資料遷移。

# 🔴 DEF-200-206 ②：枚舉對齊 PRD §6 區塊 11 的字面 `ABORT|RETRY_WITH_AGENT|HUMAN_REVIEW`。
# 原實作的 `AUTO_AGENT` 是同一語意（重排給 agent 重試）的自造名，更名為 PRD 的
# `RETRY_WITH_AGENT`；`ABORT` 補入＝有殘留整合項就拒絕啟動（列出清單並回非零退出碼）。
# 鏡射鎖＝`tests/test_r100_boot_self_check.py` 讀 PRD §6 那一行的註解字面比對本 tuple。
CONFLICT_POLICIES = ("ABORT", "RETRY_WITH_AGENT", "HUMAN_REVIEW")
POLICY_ABORT, POLICY_RETRY_WITH_AGENT, POLICY_HUMAN_REVIEW = CONFLICT_POLICIES
CONFLICT_POLICY_DEFAULT = POLICY_HUMAN_REVIEW   # §6 出廠值
# 🔴 DEF-200-206 ③：PRD §6 的鍵此前**零 env 讀取路徑**（改設定不生效）。鍵名跟隨全庫
# `AUTOCLAUDE_*` 慣例（同 ① 對 `STATE_RETAIN_VERSIONS` 的修憲方向），PRD 同批對齊。
CONFLICT_POLICY_ENV = "AUTOCLAUDE_CONFLICT_POLICY"


def conflict_policy_from_env(environ: Mapping[str, str] | None = None) -> str:
    """`CONFLICT_POLICY` 的讀取路徑。未設 ⇒ 出廠值；設了非法值**原樣回傳**——讓
    `scan_queue()` 的不變式 11 把它報成 boot problem（fail-loud、非零退出碼），而不是
    在這裡靜默退回出廠值（那會讓「設錯」與「沒設」外觀相同）。"""
    env = os.environ if environ is None else environ
    raw = (env.get(CONFLICT_POLICY_ENV) or "").strip()
    return raw or CONFLICT_POLICY_DEFAULT

# 🔴 「DRAINING 以上」在本實作的等價述詞。根層唯一對映登記在
# `tools/lib/quota_gate.py::DRAINING_BANDS = (BAND_PREPARE, BAND_HALT)`；`.importlinter`
# 的 no-harness-import 契約禁止 import 它 ⇒ 跨這條邊界的**字面**只能兩側各自持有，
# 縫由鏡射鎖縫起來（體例＝字面多個家、判準一個家，同 FALLBACK_KINDS／PACE_SCHEMA）。
DRAINING_BANDS = (BAND_PREPARE, BAND_HALT)

QUEUE_UNKNOWN_TEXT = "佇列狀態不明"
DRY_RUN_TEXT = "本次以 DRY_RUN 執行"


@dataclass(frozen=True)
class QueueOutcome:
    requeued: tuple[str, ...] = field(default_factory=tuple)
    listed_only: tuple[str, ...] = field(default_factory=tuple)
    unknown_reason: str = ""
    lines: tuple[str, ...] = field(default_factory=tuple)
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def state_unknown(self) -> bool:
        return bool(self.unknown_reason)


def read_queue(repo, playbook_id: str) -> tuple[list[dict], str]:
    """回 (queue, unknown_reason)。unknown_reason 非空＝**讀不出來**，不是「0 筆」。

    🔴 「掃一次」不得變成靜默的「掃 0 筆」：讀不出來（檔不存在／schema 不符／checksum
    失敗）與「佇列是空的」必須分開回報（同本 repo 通篇「量不到 ≠ 量到零」）。
    """
    try:
        cp = repo.load_latest_by_playbook(playbook_id)
    except CheckpointCorruptError as exc:
        return [], f"checkpoint 讀不回來：{exc}"
    if cp is None:
        return [], ""                     # 真的沒有 checkpoint ⇒ 真的沒有佇列（合法的 0 筆）
    queue = getattr(cp, "integration_queue", None)
    if queue is None or not isinstance(queue, list):
        return [], f"integration_queue 欄位型別不符（{type(queue).__name__}）"
    return queue, ""


def scan_queue(queue: Sequence[dict], *, conflict_policy: str = CONFLICT_POLICY_DEFAULT,
               band: str = "", unknown_reason: str = "",
               dry_run: bool = False) -> QueueOutcome:
    """啟動自檢掃一次殘留整合項並依 CONFLICT_POLICY 重排（PRD R-6.2-1）。純函式。"""
    problems: list[str] = []
    if conflict_policy not in CONFLICT_POLICIES:
        problems.append(f"CONFLICT_POLICY={conflict_policy!r} 不在合法枚舉 "
                        f"{CONFLICT_POLICIES} 內（§6.1 不變式 11）")
    if unknown_reason:
        # G2：這一格是本節最容易寫成假綠的地方——輸出必須說「狀態不明」，**不得**印「0 筆」。
        return QueueOutcome(unknown_reason=unknown_reason, problems=tuple(problems),
                            lines=(f"{QUEUE_UNKNOWN_TEXT}：{unknown_reason}",))
    pending: list[str] = []
    for item in queue:
        status = str(item.get("status", ""))
        if status not in QUEUE_STATUSES:
            # 🔴 §6.1 不變式 11（v2.1.9）：未知字面**視為讀不出來**而非略過——
            # 略過等於把一筆殘留整合靜默丟掉。
            reason = (f"integration_queue 有未知 status={status!r}"
                      f"（合法枚舉 {QUEUE_STATUSES}）")
            return QueueOutcome(unknown_reason=reason, problems=tuple(problems),
                                lines=(f"{QUEUE_UNKNOWN_TEXT}：{reason}",))
        if status in PENDING_STATUSES:
            pending.append(str(item.get("branch") or item.get("agent_id") or "?"))
    lines = [f"待整合殘留項 {len(pending)} 筆"]
    # 🔴 重排必須先過額度閘：重排會派工、派工會燒額度。啟動當下已在 DRAINING 以上
    # ⇒ **只登記不重排**（§4.4.2 逐字既有的「DRAINING 以上禁止啟動衝突解決任務」，
    # 此處只是把它接到開機這一刻）。DRY_RUN 同樣只登記（G5：真的不動作）。
    # 非法字面已由上方不變式 11 記成 problem ⇒ 這裡把它當 hold（只登記）：不得落到預設的
    # 重排分支去派工（SD 定點複審：問題與「重排：X」同時印出是自相矛盾的輸出）。
    hold = (band in DRAINING_BANDS or dry_run or conflict_policy == POLICY_HUMAN_REVIEW
            or conflict_policy not in CONFLICT_POLICIES)
    if not pending:
        return QueueOutcome(lines=tuple(lines), problems=tuple(problems))
    if conflict_policy == POLICY_ABORT:
        # PRD §6 區塊 11 的第三值：有殘留整合項就**拒絕啟動**——不重排（那是派工）、
        # 也不只是登記（那是 HUMAN_REVIEW）；清單照列，讓人知道要清什麼。band／DRY_RUN
        # 不改變這個判決：拒絕啟動不派工、不寫 worktree，與兩者的守則相容。
        lines += [f"ABORT：{b}" for b in pending]
        problems.append(
            f"CONFLICT_POLICY=ABORT 且有 {len(pending)} 筆待整合殘留項 ⇒ 拒絕啟動"
            "（先清掉佇列，或改 RETRY_WITH_AGENT／HUMAN_REVIEW）")
        return QueueOutcome(listed_only=tuple(pending), lines=tuple(lines),
                            problems=tuple(problems))
    if hold:
        why = ("band=" + band if band in DRAINING_BANDS else
               "DRY_RUN" if dry_run else f"CONFLICT_POLICY={conflict_policy}")
        lines += [f"只登記不重排（{why}）：{b}" for b in pending]
        return QueueOutcome(listed_only=tuple(pending), lines=tuple(lines),
                            problems=tuple(problems))
    lines += [f"重排：{b}" for b in pending]
    return QueueOutcome(requeued=tuple(pending), lines=tuple(lines),
                        problems=tuple(problems))


# ══════════════════════════════════════════════════════════════════════════════
# R-6.2-2：CLI 版本相容性在啟動時判一次
# ══════════════════════════════════════════════════════════════════════════════
def read_cli_version(command: str = "claude",
                     runner: Callable[[list[str]], tuple[int, str]] | None = None,
                     ) -> str | None:
    """`claude --version`（唯讀、零 token）。讀不到版本字串 ⇒ 回 None＝**未知版本**。

    🔴 不得因為讀不到就當成已驗證——那是 fail-open，而它的失效外觀與「版本沒變」相同。
    """
    run = runner or _default_runner
    try:
        rc, out = run([command, "--version"])
    except Exception as exc:                      # 找不到執行檔／權限／逾時皆為「未知」
        logger.warning("讀不到 CLI 版本（%s）⇒ 視為未知版本", exc)
        return None
    if rc != 0 or not out.strip():
        logger.warning("讀不到 CLI 版本（rc=%s, out=%r）⇒ 視為未知版本", rc, out)
        return None
    token = out.strip().split()[0]
    return token if any(ch.isdigit() for ch in token) else None


def _default_runner(argv: list[str]) -> tuple[int, str]:
    p = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def cli_version_verdict(version: str | None) -> tuple[bool, str]:
    """回 (dry_run, 自檢輸出一行)。未知版本 → DRY_RUN，但**不阻止啟動**。

    🔴 阻止啟動＝CLI 一升版就整套停擺，那種守衛會被整個關掉，比沒有守衛更糟。
    """
    if version is None:
        return True, (f"CLI 版本未知（`claude --version` 讀不到）⇒ {DRY_RUN_TEXT}；"
                      "確認方式：人工核實介面後把版號與『核實過什麼』寫入 "
                      "autoclaude/utils/verified_cli_versions.py")
    entry = VERIFIED_CLI_VERSIONS.get(version)
    if entry is None:
        return True, (f"CLI 版本 {version} 不在已驗證清單內 ⇒ {DRY_RUN_TEXT}；"
                      "確認方式同上（清單須帶『這一版核實過什麼』）")
    return False, f"CLI 版本 {version} 在已驗證清單內（核實項 {len(entry['verified'])} 條）"


# ══════════════════════════════════════════════════════════════════════════════
# R-6.2-3：可用空間在啟動與凍結前各檢一次（bytes 對 bytes）
# ══════════════════════════════════════════════════════════════════════════════
def estimate_freeze_bytes(worktrees: Sequence[str | Path], state_bytes: int = 0,
                          retain_versions: int = 0) -> int:
    """預估來源＝各 worktree `git diff HEAD --binary` 的位元組數（唯讀、零 token）
    ＋ state.json 與其 `STATE_RETAIN_VERSIONS` 份保留版本的大小（PRD R-6.2-3 ②）。"""
    total = 0
    for wt in worktrees:
        p = subprocess.run(["git", "-C", str(wt), "diff", "HEAD", "--binary"],
                           capture_output=True, check=False)
        total += len(p.stdout)
    return total + max(0, int(state_bytes)) * (1 + max(0, int(retain_versions)))


def merged_worktrees(repo: str | Path, integration_ref: str = "integration",
                     ) -> list[tuple[str, str]]:
    """回「已 `--ff-only` 併入 integration」的 (worktree_path, branch)。

    🔴 判準是「該分支已併入」（`merge-base --is-ancestor` rc==0），**不是** mtime、
    **不是**目錄大小——後兩者會刪掉還沒併入的工作。
    """
    p = subprocess.run(["git", "-C", str(repo), "worktree", "list", "--porcelain"],
                       capture_output=True, text=True, check=False,
                       encoding="utf-8", errors="replace")
    out: list[tuple[str, str]] = []
    path = ""
    for line in (p.stdout or "").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch ") and path:
            branch = line[len("branch "):]
            anc = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor",
                 branch, integration_ref], capture_output=True, check=False)
            if anc.returncode == 0 and Path(path).resolve() != Path(repo).resolve():
                out.append((path, branch))
            path = ""
    return out


def cleanup_merged_worktrees(repo: str | Path, integration_ref: str = "integration",
                             *, dry_run: bool = False) -> list[str]:
    """移除已併入的 worktree。動詞只有 `git worktree remove`（§4.4.2 步驟 5 的既有出口）。

    🔴 清理動作本身受鐵律五管：不得用 `git clean`／`git reset --hard`——那兩個會毀掉
    工作樹內容，而本函式要做的只是拆掉一個**已經沒有未併入內容**的掛載點。
    """
    removed: list[str] = []
    for path, _branch in merged_worktrees(repo, integration_ref):
        if dry_run:                           # G5：DRY_RUN 真的不動作
            continue
        p = subprocess.run(["git", "-C", str(repo), "worktree", "remove", path],
                           capture_output=True, check=False)
        if p.returncode == 0:
            removed.append(path)
    return removed


@dataclass(frozen=True)
class BootReport:
    problems: tuple[str, ...] = field(default_factory=tuple)
    lines: tuple[str, ...] = field(default_factory=tuple)
    dry_run: bool = False
    cli_version: str | None = None
    queue: QueueOutcome = field(default_factory=QueueOutcome)
    space: SpaceVerdict | None = None
    notified: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems


def boot_self_check(
    *,
    repo=None,
    playbook_id: str = "",
    conflict_policy: str = CONFLICT_POLICY_DEFAULT,
    band: str = "",
    cli_command: str = "claude",
    cli_runner: Callable[[list[str]], tuple[int, str]] | None = None,
    space_target: str | Path | None = None,
    estimate_bytes: int = 0,
    margin_bytes: int = DEFAULT_MARGIN_BYTES,
    cleanup: Callable[[], list[str]] | None = None,
    notifier: Callable[[str], None] | None = None,
) -> BootReport:
    """§6.1 不變式 11~13 的一次性自檢。違反 → problems 非空（呼叫端須非零退出碼）。"""
    lines: list[str] = []
    problems: list[str] = []
    notified = 0
    # 不變式 12（CLI 版本）先跑：它決定 dry_run，而 dry_run 決定 11 敢不敢重排。
    version = read_cli_version(cli_command, cli_runner)
    dry_run, line = cli_version_verdict(version)
    lines.append(line)
    if dry_run and notifier is not None:
        notifier(line)                        # 未知版本不阻止啟動，但必須 loud 一次
        notified += 1
    # 不變式 11（待整合佇列）
    queue, unknown = ([], "") if repo is None else read_queue(repo, playbook_id)
    outcome = scan_queue(queue, conflict_policy=conflict_policy, band=band,
                         unknown_reason=unknown, dry_run=dry_run)
    lines.extend(outcome.lines)
    problems.extend(outcome.problems)
    # 不變式 13（可用空間；bytes 對 bytes）
    verdict = None
    if space_target is not None:
        verdict = check_space(space_target, estimate_bytes, margin_bytes=margin_bytes)
        if not verdict.ok and cleanup is not None:
            removed = cleanup()               # 只清「已 --ff-only 併入」者
            lines.append(f"空間不足，已清理 {len(removed)} 個已併入 worktree")
            verdict = check_space(space_target, estimate_bytes, margin_bytes=margin_bytes)
        if not verdict.ok:
            # 🔴 清理後仍不足 ⇒ 這是 R-4.5.9 驗證失敗的**前置警報**，走 DIRTY_UNSAVED
            # 那條路的桌面通知通道 loud 一次，不得只印一行 log。
            msg = (f"可用空間不足：free={verdict.free_bytes} < "
                   f"required={verdict.required_bytes} bytes（缺 "
                   f"{verdict.shortfall_bytes}）")
            problems.append(msg)
            if notifier is not None:
                notifier(msg)
                notified += 1
        else:
            lines.append(f"可用空間 {verdict.free_bytes} ≥ 需求 {verdict.required_bytes} bytes")
    for text in lines:
        logger.info("開機自檢 | %s", text)
    return BootReport(problems=tuple(problems), lines=tuple(lines), dry_run=dry_run,
                      cli_version=version, queue=outcome, space=verdict,
                      notified=notified)
