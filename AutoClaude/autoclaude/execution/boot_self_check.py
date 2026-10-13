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
from ..utils.platform_caps import is_linux
from ..utils.verified_cli_versions import VERIFIED_CLI_VERSIONS, family_verdict

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
    🔴 家族級（major.minor）只豁免 patch 差異（判定住 `family_verdict`）：Claude Code 每週自動
    升 patch，逐版精確比對會讓每次升版都 loud＋DRY_RUN，loud 天天響就失去鑑別力；讀不到版本、
    新 minor、新 major 照舊 DRY_RUN＋loud（掌舵者 2026-10-10 T1 立案）。
    """
    if version is None:
        return True, (f"CLI 版本未知（`claude --version` 讀不到）⇒ {DRY_RUN_TEXT}；"
                      "確認方式：人工核實介面後把版號與『核實過什麼』寫入 "
                      "autoclaude/utils/verified_cli_versions.py")
    kind, ref = family_verdict(version)
    if kind == "exact":
        entry = VERIFIED_CLI_VERSIONS[version]
        return False, f"CLI 版本 {version} 在已驗證清單內（核實項 {len(entry['verified'])} 條）"
    if kind == "family":
        return False, (f"CLI {version} 不在逐版清單、同家族 {ref.rsplit('.', 1)[0]}.x 已驗證至 "
                       f"{ref} ⇒ 視為已驗證（patch 級差異不進 DRY_RUN）；要更新逐版事實請補 "
                       "autoclaude/utils/verified_cli_versions.py")
    return True, (f"CLI 版本 {version} 不在已驗證清單內 ⇒ {DRY_RUN_TEXT}；"
                  "確認方式同上（清單須帶『這一版核實過什麼』）")


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


# ══════════════════════════════════════════════════════════════════════════════
# §6.1 不變式 8（PRD §12 權限旗標／§4.5.4）：完全跳過權限只准「容器＋使用者明確開旗標」
# ══════════════════════════════════════════════════════════════════════════════
# 立案（T4，PRD §16.2 該列的再開症狀）：F-SBR-001 真跑在 macOS 主機以
# `--permission-mode bypassPermissions` 跑了巢狀 claude；兩條設定路徑（SDK 後端的
# `executor.permission_mode`、PTY 後端的 `claude.extra_args`）此前都沒有任何守門。
# 🔴 只判**引擎設定面**：`--settings` 檔或使用者層 settings 內的 `defaultMode:
#    bypassPermissions` 引擎看不到（誠實劃界，不是「已涵蓋」）。
# 🔴 隔離偵測防的是「誤開」不是惡意：能設旗標的人也能偽造 env，檔案類訊號（.dockerenv／
#    cgroup）才是較硬的證據。只認 Linux——macOS 行程不可能在 Linux 容器內（Docker Desktop 的
#    容器跑在它自己的 Linux VM 裡），darwin 上的 `container=`／KUBERNETES_* 只會是雜訊或偽造，
#    不得因此放行。VM 沒有行程內的可靠標記，不偵測：VM 內要 bypass 目前須進容器（PRD 條文寫
#    「容器／VM」，缺口登記在這裡，不假裝已涵蓋）。
ALLOW_BYPASS_ENV = "ALLOW_PERMISSION_BYPASS"  # PRD §6 區塊 13 原名（憲法字面，不加前綴）
BYPASS_MODE = "bypassPermissions"
SKIP_PERMISSIONS_FLAG = "--dangerously-skip-permissions"
_TRUTHY = frozenset({"1", "true", "yes", "on"})  # 與 AUTOCLAUDE_DESKTOP_NOTIFY 同一組真值字面
_CGROUP_MARKERS = ("docker", "containerd", "kubepods", "lxc")
_BYPASS_HOW = (
    "改用 `--permission-mode acceptEdits` 加 `--allowedTools` 工具白名單（範例："
    "scripts/bridge_e2e/wordcount/config.template.yaml）；確實需要 bypass 時，"
    f"在容器內執行並設 {ALLOW_BYPASS_ENV}=true")


@dataclass(frozen=True)
class IsolationEvidence:
    sources: tuple[str, ...] = field(default_factory=tuple)

    @property
    def detected(self) -> bool:
        return bool(self.sources)


@dataclass(frozen=True)
class BypassOutcome:
    lines: tuple[str, ...] = field(default_factory=tuple)
    problems: tuple[str, ...] = field(default_factory=tuple)


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:                       # 權限／I/O 讀不到＝沒有證據，不是例外
        return False


def detect_isolation_env(*, environ: Mapping[str, str] | None = None,
                         on_linux: bool | None = None,
                         dockerenv: Path = Path("/.dockerenv"),
                         cgroup: Path = Path("/proc/1/cgroup")) -> IsolationEvidence:
    """行程是否在容器內（唯讀、零 token）。路徑／env／平台皆可注入，測試不碰真實 `/proc`。"""
    env = os.environ if environ is None else environ
    if not (is_linux() if on_linux is None else on_linux):
        return IsolationEvidence()
    found: list[str] = []
    if _exists(dockerenv):
        found.append("dockerenv")
    try:
        cg = cgroup.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        cg = ""
    found += [f"cgroup:{m}" for m in _CGROUP_MARKERS if m in cg]
    if kind := (env.get("container") or "").strip():
        found.append(f"env:container={kind}")
    if (env.get("KUBERNETES_SERVICE_HOST") or "").strip():
        found.append("env:KUBERNETES_SERVICE_HOST")
    return IsolationEvidence(sources=tuple(found))


def permission_bypass_requests(permission_mode: str | None,
                               extra_args: Sequence[str] = ()) -> tuple[str, ...]:
    """設定面有哪幾處要求「完全跳過權限」（空＝不相干）。純函式。

    兩條路各自獨立生效所以都要看：SDK 後端讀 `executor.permission_mode`，PTY／subprocess
    後端（出廠預設，F-SBR-001 實際走的那條）讀 `claude.extra_args`——只守前者會整條漏掉。
    只判**真的把 bypass 打開**的字面；`--allow-dangerously-skip-permissions` 只是「允許日後
    切過去」的選項、本身不跳過任何檢查，不在此列。
    """
    found: list[str] = []
    if (permission_mode or "").strip().lower() == BYPASS_MODE.lower():
        found.append(f"executor.permission_mode={BYPASS_MODE}")
    args = [str(a) for a in extra_args]
    for i, arg in enumerate(args):
        if arg == "--permission-mode" and i + 1 < len(args):
            value = args[i + 1]
        elif arg.startswith("--permission-mode="):
            value = arg.split("=", 1)[1]
        else:
            value = ""
        if value.strip().lower() == BYPASS_MODE.lower():
            found.append(f"claude.extra_args 的 --permission-mode {BYPASS_MODE}")
        if arg == SKIP_PERMISSIONS_FLAG:
            found.append(f"claude.extra_args 的 {SKIP_PERMISSIONS_FLAG}")
    return tuple(dict.fromkeys(found))


def permission_bypass_allowed_from_env(environ: Mapping[str, str] | None = None,
                                       ) -> tuple[bool, str]:
    """回 (旗標是否為真, 原始字面)。只讀行程環境（同 `conflict_policy_from_env`）；
    不讀 `.env` 檔：這是安全閘，要由啟動方式（如 `docker run -e`）明確注入。

    🔴 fail-closed：只有明確的真值才算開；打錯字（`treu`）算關，原始字面回給呼叫端放進訊息，
    讓「設了卻沒生效」看得見，而不是靜默。
    """
    env = os.environ if environ is None else environ
    raw = (env.get(ALLOW_BYPASS_ENV) or "").strip()
    return raw.lower() in _TRUTHY, raw


def permission_bypass_verdict(requested_by: Sequence[str], *, allow_flag: bool,
                              flag_raw: str = "",
                              isolation: IsolationEvidence) -> BypassOutcome:
    """§6.1 不變式 8 的判決（純函式）。兩個要件缺一不可：旗標明確為真、且偵測到容器。

    · 設定要求 bypass ＋ 旗標非真 ⇒ 拒絕（容器內也一樣：PRD 要「使用者明確設定」）；
    · 旗標為真 ＋ 未偵測到容器 ⇒ 拒絕（不論設定有沒有要求 bypass：旗標字面條文如此）；
    · 設定要求 bypass ＋ 旗標為真 ＋ 容器 ⇒ 放行並留一行含隔離證據的 log；
    · 其餘（沒人要 bypass、旗標也沒開）⇒ 不相干，無輸出。
    """
    asked = "、".join(requested_by)
    problems: list[str] = []
    lines: list[str] = []
    if requested_by and not allow_flag:
        problems.append(
            f"設定要求完全跳過權限（{asked}），但 {ALLOW_BYPASS_ENV} 不是 true"
            f"（目前＝{flag_raw or '未設'}）⇒ 拒絕啟動（PRD §12／§4.5.4）。{_BYPASS_HOW}")
    elif allow_flag and not isolation.detected:
        head = (f"設定要求完全跳過權限（{asked}）、{ALLOW_BYPASS_ENV}=true 也已設"
                if requested_by else f"{ALLOW_BYPASS_ENV}=true")
        fix = _BYPASS_HOW if requested_by else f"請取消 {ALLOW_BYPASS_ENV}，或改在容器內執行"
        problems.append(
            f"{head}，但未偵測到容器環境（偵測項：/.dockerenv、/proc/1/cgroup、"
            "env container／KUBERNETES_SERVICE_HOST；macOS 一律視為主機）"
            f" ⇒ 拒絕啟動（PRD §6.1 不變式 8）。{fix}")
    elif requested_by:
        lines.append(f"bypass 已顯式允許（{asked}），隔離證據＝{'、'.join(isolation.sources)}")
    return BypassOutcome(lines=tuple(lines), problems=tuple(problems))


# ══════════════════════════════════════════════════════════════════════════════
# §6.1 不變式 9（PRD §4.5.9 R-4.5.9-1 末段）：引擎的狀態目錄必須在 .gitignore
# ══════════════════════════════════════════════════════════════════════════════
# 現查事實：引擎**實際**寫入的目錄是 `checkpoint_dir`（出廠值見 `utils/config.py`，本檔不複寫）；
# PRD 字面的 `.autoclaude/` 只在使用者把 checkpoint_dir 指進去、或別的工具建出它時才存在。
# ⇒ 判準問兩類目錄：設定的 checkpoint_dir（在 repo 內才問）與**已經存在**的 `.autoclaude/`。
# 🔴 不是「每個 repo 都必須有這一行」：從不用 `.autoclaude/` 的專案會因此無端拒絕啟動，
#    而被關掉的守衛比沒有守衛更糟。
# 🔴 問法是 `git check-ignore -q <dir>/`（帶尾斜線）：實測 `.gitignore` 寫 `.autoclaude/` 時，
#    不帶斜線的 `check-ignore .autoclaude` 在目錄尚不存在時回 rc=1（git 把不存在的路徑當檔案）
#    ⇒ 對一棵已正確 ignore 的 repo 假紅；帶斜線則 rc=0。同型教訓：
#    `infra/adapters/dirty_worktree_rescue.py::_selfrecursion_hazard`。
DOT_AUTOCLAUDE = ".autoclaude"


@dataclass(frozen=True)
class GitignoreOutcome:
    lines: tuple[str, ...] = field(default_factory=tuple)
    problems: tuple[str, ...] = field(default_factory=tuple)


def state_dirs_to_guard(repo_root: str | Path, checkpoint_dir: str | Path) -> tuple[str, ...]:
    """不變式 9 要問的目錄（相對 repo_root 的 posix 路徑）。純路徑運算，不呼叫 git。"""
    root = Path(repo_root)
    dirs: list[str] = []
    raw = str(checkpoint_dir).strip()
    if raw:
        ck = Path(raw)
        try:
            rel = (ck if ck.is_absolute() else root / ck).resolve().relative_to(root.resolve())
        except ValueError:                    # repo 外的目錄結構上不可能被這個 repo commit
            rel = None
        if rel is not None and rel.parts:     # parts 為空＝repo 根本身，無從 ignore
            dirs.append(rel.as_posix())
    if (root / DOT_AUTOCLAUDE).is_dir() and DOT_AUTOCLAUDE not in dirs:
        dirs.append(DOT_AUTOCLAUDE)
    return tuple(dirs)


def gitignore_verdict(repo_root: str | Path, dir_name: str,
                      runner: Callable[[list[str]], tuple[int, str]] | None = None,
                      ) -> GitignoreOutcome:
    """§6.1 不變式 9 的判決。rc：0＝已忽略；1＝未忽略（problem）；128＝非 git repo（通過並 note）；
    其餘＝沒量到（problem——量不到不得讀成「已忽略」）；runner 拋例外（無 git）＝note＋warning。"""
    run = runner or _default_runner
    target = dir_name.rstrip("/") + "/"
    try:
        rc, out = run(["git", "-C", str(repo_root), "check-ignore", "-q", target])
    except Exception as exc:                  # 找不到 git／逾時：沒有 git 就沒有 commit，但不得靜默
        logger.warning("§6.1 不變式 9：git 不可用（%s）⇒ 略過 %s 的 .gitignore 檢查", exc, target)
        return GitignoreOutcome(lines=(f"不變式 9：git 不可用（{exc}）⇒ 略過 `{target}` 的檢查",))
    if rc == 0:
        return GitignoreOutcome(lines=(f"不變式 9：`{target}` 已在 .gitignore",))
    if rc == 128:
        return GitignoreOutcome(lines=(
            f"不變式 9：{repo_root} 不是 git repo（git check-ignore rc=128）"
            f"⇒ `{target}` 無從被 commit，視為通過",))
    if rc == 1:
        return GitignoreOutcome(problems=(
            f"`{target}` 位於 {repo_root} 內但不在 .gitignore ⇒ 檢查點／patch／狀態檔可能被 "
            "commit，且救援 patch 會把自己列舉進自己（PRD §6.1 不變式 9）。"
            f"請先把 `{target}` 加入 .gitignore",))
    return GitignoreOutcome(problems=(
        f"不變式 9：`git check-ignore -q {target}` 回非預期 rc={rc}（{out.strip()[:200]}）"
        f"⇒ 無法確認 `{target}` 已被忽略",))


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
    permission_mode: str | None = None,
    extra_args: Sequence[str] = (),
    environ: Mapping[str, str] | None = None,
    isolation: IsolationEvidence | None = None,
    repo_root: str | Path | None = None,
    ignored_dirs: Sequence[str] = (),
    git_runner: Callable[[list[str]], tuple[int, str]] | None = None,
) -> BootReport:
    """§6.1 不變式 8、9、11~13 的一次性自檢。違反 → problems 非空（呼叫端須非零退出碼）。"""
    lines: list[str] = []
    problems: list[str] = []
    notified = 0
    # 不變式 8（權限旗標）：安全閘先判。偵測是惰性的——沒人要 bypass、旗標也沒開時完全不碰
    # `/proc`（每次啟動多讀一個檔、跨平台多一個變因，卻換不到任何判決）。
    requested = permission_bypass_requests(permission_mode, extra_args)
    allow_flag, flag_raw = permission_bypass_allowed_from_env(environ)
    if requested or allow_flag:
        evidence = isolation if isolation is not None else detect_isolation_env(environ=environ)
        bypass = permission_bypass_verdict(requested, allow_flag=allow_flag,
                                           flag_raw=flag_raw, isolation=evidence)
        lines.extend(bypass.lines)
        problems.extend(bypass.problems)
    # 不變式 9（狀態目錄在 .gitignore）：沒傳 ignored_dirs＝不問 git，舊呼叫端零附帶面。
    for dir_name in ignored_dirs:
        ignored = gitignore_verdict(Path.cwd() if repo_root is None else repo_root,
                                    dir_name, git_runner)
        lines.extend(ignored.lines)
        problems.extend(ignored.problems)
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
