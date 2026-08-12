# policy.py — TokenGuardPlugin 主類（SD_06 W2-T2-13 拆 5 子模組組合層）。
#
# 🔴 R86：本段由 docstring 改為 `#` 註解，**一字未刪**（同本檔既有兩處相同處置，見
# `subscribed_phases` 與 `_evaluate_post_compact` 上方的 R82 註記）。理由是
# `check_loc_budget` 自己印的指引：docstring 行會被 count_loc 計入、`#` 不會，而本輪要把
# 配速契約接進 `evaluate_quota`，total LOC 餘裕當回合實測只有 12 行。
#
# 對應：
#   - SD_Improving_01.md v1.1 §3.5 表格第 1 列（priority=30）
#   - SD_Improving_06.md v1.2 §6.5 AC1-3（token_guard package 5 子模組）
#
# 訂閱 phase：
#   - POST_ATTEMPT / ON_TOKEN_USAGE：策略決定（compact/halt）
#
# 公開 API（與原 token_guard_plugin.py 100% 等價，30+ 既有測試 patch path 維持）：
#   - get_dynamic_compact_threshold / should_compact / should_halt
#   - record_compact_failure / reset_compact_failure / is_compact_failure_critical
#   - compact_failure_count（property）
#   - verify_correction_applied
#   - build_compact_prompt / process_compact_result
#   - observe_token_line
#   - resolve_per_step_cfg
from __future__ import annotations

from typing import Any

from ...core.hookspec import HookContext, KernelPhase, ResourceRequest
from ...core.ports.quota_meter import (
    BAND_HALT,
    BAND_PREPARE,
    BAND_UNMEASURED,
    is_quota_limit_text,
)
from ...utils.config import TokenGuardConfig
from .compactor import CompactFailureState
from .compactor import build_compact_prompt as _build_compact_prompt
from .compactor import process_compact_result as _process_compact_result
from .git_verifier import verify_correction_applied as _verify_correction_applied
from .thresholds import get_dynamic_compact_threshold as _get_dynamic_compact_threshold
from .thresholds import should_compact_decision, should_halt_decision
from .watcher import observe_token_line as _observe_token_line
from .watcher import resolve_per_step_cfg as _resolve_per_step_cfg


class TokenGuardPlugin:
    """Token / Context 用量保護 Plugin（組合層）。"""

    PRIORITY = 30

    def __init__(self, token_guard_cfg: TokenGuardConfig | None = None,
                 quota_meter: Any | None = None):
        self._cfg = token_guard_cfg or TokenGuardConfig()
        self._compact_state = CompactFailureState()
        # R82（ACQ-01）：QuotaMeterPort（可選）。None＝這一軸不存在，行為與修前位元級相同。
        self._quota = quota_meter

    def name(self) -> str:
        return "token_guard"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        # improving_79 W-78-2（DEF-78-001）：新增 POST_COMPACT——production Kernel 送 /compact
        # 後 emit，本 plugin 判 Gap-008-E（連續 compact 失敗 → 強制 HALT）。
        # 🔴 本輪收斂：本檔多處把單一運算式攤成多行。收合是 R82 已用過的**等量減法**手法
        # （該輪把一段 docstring 改成 `#` 註解讓出預算），為的是替 C3 的選軸修法騰出
        # total LOC——`check_loc_budget` 當回合實測餘裕只有 1 行。零語意變更。
        return [KernelPhase.POST_ATTEMPT, KernelPhase.ON_TOKEN_USAGE,
                KernelPhase.POST_COMPACT]

    def on_event(self, ctx: HookContext) -> Any | None:
        if not self._cfg.enabled:
            return None
        if ctx.phase in (KernelPhase.POST_ATTEMPT, KernelPhase.ON_TOKEN_USAGE):
            return self._evaluate_resources(ctx)
        return (self._evaluate_post_compact(ctx)
                if ctx.phase == KernelPhase.POST_COMPACT else None)

    # ──────────────────────────────────────────────
    # 公開 API（與原 token_guard_plugin.py 100% 等價）
    # ──────────────────────────────────────────────
    def get_dynamic_compact_threshold(self, attempt: int, max_retries: int) -> float:
        return _get_dynamic_compact_threshold(
            base_threshold=self._cfg.compact_threshold_pct, attempt=attempt,
            max_retries=max_retries)

    def should_compact(self, token_pct: float, attempt: int = 0, max_retries: int = 3,
                       in_correction_loop: bool = False,
                       correction_history_len: int = 0) -> bool:
        return should_compact_decision(
            token_pct=token_pct,
            threshold=self.get_dynamic_compact_threshold(attempt, max_retries),
            in_correction_loop=in_correction_loop,
            correction_history_len=correction_history_len)

    def should_halt(self, token_pct: float) -> bool:
        return should_halt_decision(token_pct=token_pct,
                                    halt_threshold=self._cfg.halt_threshold_pct)

    def record_compact_failure(self) -> int:
        return self._compact_state.record_failure()

    def reset_compact_failure(self) -> None:
        self._compact_state.reset()

    def is_compact_failure_critical(self) -> bool:
        return self._compact_state.is_critical()

    @property
    def compact_failure_count(self) -> int:
        """SD_05 W2 SD-M1：唯讀公開 property。"""
        return self._compact_state.count

    @property
    def _compact_failure_count(self) -> int:
        """SD_05 W2 backward-compat alias（既有測試直接讀 _compact_failure_count）。"""
        return self._compact_state.count

    @_compact_failure_count.setter
    def _compact_failure_count(self, value: int) -> None:
        self._compact_state.count = int(value)

    def resolve_per_step_cfg(self, task: Any | None = None) -> TokenGuardConfig:
        return _resolve_per_step_cfg(global_cfg=self._cfg, task=task)

    def observe_token_line(self, pct: float | None, peak_pct: float,
                           triggered_compact: bool,
                           triggered_halt: bool) -> tuple[float, bool, bool]:
        return _observe_token_line(
            pct=pct, peak_pct=peak_pct, cfg=self._cfg,
            triggered_compact=triggered_compact, triggered_halt=triggered_halt)

    def build_compact_prompt(self, *, task: Any | None = None, attempt: int = 0,
                             failure_summary: str = "", global_goal: str | None = None,
                             global_goal_anchor_chars: int = 200) -> str:
        return _build_compact_prompt(
            task=task, attempt=attempt, failure_summary=failure_summary,
            global_goal=global_goal, global_goal_anchor_chars=global_goal_anchor_chars)

    def process_compact_result(self, triggered_compact: bool,
                               peak_token_pct: float) -> bool:
        return _process_compact_result(state=self._compact_state,
                                       triggered_compact=triggered_compact)

    def verify_correction_applied(self, attempt: int) -> str | None:
        return _verify_correction_applied(attempt)

    # ──────────────────────────────────────────────
    # 內部
    # ──────────────────────────────────────────────
    # R82（ACQ-01／ACQ-04）：**額度**那一軸的判定（分母＝帳號方案，不是 context window）。
    # 三個觸發條件都導向同一個動作＝立刻 halt，因為它們都代表「再打一次 claude 只會更快
    # 燒完額度」：
    #   ① pct ≥ quota_halt_pct（預設 95＝根層 halt）：硬水位、安全線。
    #   ② 步驟失敗訊息本身就是撞線（ACQ-04）：修前這會被當成一般失敗、被 CORRECTION 迴圈
    #      重試——而每一次重試都是再打一次 claude，**反而加速燒額度**。
    #   ③ pct ≥ quota_throttle_pct（預設 70＝根層 converge「開始收斂」）且正在 CORRECTION
    #      迴圈裡：重試是「可選支出」，收斂帶就先停掉可選的那一半（正常步驟仍放行）。
    # 🔴 R82（C3）：讀的是 `read_worst_pct()`（水位最高那條線）而**不是** `read()`
    # （最先 reset 那條線）。這裡問的是「還剩多少可燒」，那是最緊的一條說了算；
    # `read()` 服務的是 AutoResumeService 的「要等多久」，兩者是相反的問題。
    # 這個等式讓 halt 與根層**恰好等價**：任一軸 ≥95 ⇒ max(pct) ≥95 ⇒ 兩邊同時 halt；
    # 反之根層 halt ⇒ 某軸 cap=0 ⇒ 該軸 ≥95 ⇒ max(pct) ≥95。回歸鎖＝
    # `tests/test_r82_quota_axis_and_shipped_defaults.py::TestBandParityWithTheHarness`。
    # 🔴 誠實劃界：本判定掛在 POST_ATTEMPT，而 Kernel 先算 correction 才 emit POST_ATTEMPT
    # ⇒ 撞線那一輪仍會多一次 Brain 呼叫；擋掉的是**其後**所有重試，不是當次。
    # 說明寫成 # 而非 docstring：docstring 會被 count_loc 計入（見 check_loc_budget 提示）。
    # 🔴 R86（第四個觸發條件）：`band` 來自**根層算好的配速契約**，不是引擎自己再算一次。
    # 為什麼需要它——上面 ①③ 兩條只看 `max(pct)` 對兩個門檻，對「距 reset 幾分鐘」這一軸
    # 結構上失明；根層的 `decide()` 才是完整演算法（逐軸帶別 × 期程帶 → cap，跨軸聚合，
    # 單調性不變式）。引擎照抄一份就是本 repo 的頭號病，所以改成**讀它的結論**。
    # 🔴 只可能更嚴，不可能更寬：這是在既有 `or` 鏈上**加項**，`hard`／`soft` 兩個布林只會
    # 由 False 翻成 True，不會反向。而契約量不到時 band＝unmeasured ⇒ 兩項都不成立 ⇒
    # 行為與修前完全相同（**不對一個沒量到的值 halt**，同根層「量不到永不 halt」）。
    # `getattr` 而不是直接呼叫：既有測試與外部注入的 meter 只實作 read()/read_worst_pct()，
    # 直接呼叫會讓一個少一支方法的 port 把整條額度軸炸掉（fail-closed 到不能跑）。
    def evaluate_quota(self, payload: dict) -> ResourceRequest | None:
        reading = self._quota.read_worst_pct() if self._quota is not None else None
        pct = reading.pct if reading is not None else None
        read_pace = getattr(self._quota, "read_pace", None)
        band = read_pace().band if read_pace is not None else BAND_UNMEASURED
        limit_hit = is_quota_limit_text(payload.get("failure_reason"))
        hard = (pct is not None and pct >= self._cfg.quota_halt_pct) or band == BAND_HALT
        soft = ((pct is not None and pct >= self._cfg.quota_throttle_pct)
                or band == BAND_PREPARE)
        if not (hard or limit_hit or (soft and payload.get("in_correction_loop"))):
            return None
        return ResourceRequest(
            contributor=self.name(), request_halt=True,
            reason=f"quota_pct={pct} kind={getattr(reading, 'kind', None)} band={band} "
                   f"limit_text={limit_hit} resets_at={getattr(reading, 'resets_at', None)}",
        )

    def _evaluate_resources(self, ctx: HookContext) -> ResourceRequest | None:
        payload = ctx.payload or {}
        quota = self.evaluate_quota(payload)
        if quota is not None:
            return quota
        token_pct = float(payload.get("token_pct", 0.0))
        attempt = int(ctx.attempt or 0)
        max_retries = int(payload.get("max_retries", 3))
        in_correction = bool(payload.get("in_correction_loop", False))
        history_len = int(payload.get("correction_history_len", 0))

        if self.should_halt(token_pct):
            return ResourceRequest(
                contributor=self.name(),
                request_halt=True,
                reason=f"token_pct={token_pct:.1f}% >= halt_threshold "
                       f"{self._cfg.halt_threshold_pct:.0f}%",
            )

        if self.should_compact(
            token_pct=token_pct, attempt=attempt, max_retries=max_retries,
            in_correction_loop=in_correction, correction_history_len=history_len,
        ):
            return ResourceRequest(
                contributor=self.name(),
                request_compact=True,
                reason=f"token_pct={token_pct:.1f}% >= dynamic_compact_threshold "
                       f"{self.get_dynamic_compact_threshold(attempt, max_retries):.1f}%",
            )

        return None

    # improving_79 W-78-2（DEF-78-001 / Gap-008-E）：compact 後重觀測判連續失敗。
    # Kernel 送 /compact 後 emit POST_COMPACT 帶壓縮後真實 token%（post_pct）。
    # compact 後仍達 compact 門檻 ＝ 本次 compact 失敗（未把 context 壓下來）；
    # 經 CompactFailureState（SSOT）累計，連續達上限（預設 2 次）→ request_halt
    # （對齊棄用路徑 compact_controller.send_compact_impl 的 Gap-008-E 語意）。
    # 失敗訊號來源差異（誠實註記）：棄用路徑以 `compact_out.triggered_compact`
    # （compact 執行期間 TOKEN_COMPACT marker 是否再現）判失敗；本路徑以
    # `should_compact(post_pct)`（compact 後峰值是否仍 ≥ 動態門檻）判失敗——
    # 兩者語意一致（「context 沒壓下來」）但非同一信號源，本路徑為較乾淨的重導。
    # compact 成功（降到門檻下）→ 重設計數器、回 None（Kernel 續評估原 output）。
    # 🔴 R82：本段由 docstring 改為 `#` 註解，**一字未刪**。理由是 check_loc_budget 自己印的
    # 指引逐字：「說明文字請寫成 # 註解而非 docstring——docstring 行會被 count_loc 計入」。
    # 這是把說明留下、把預算讓給 R82 額度軸（ACQ-03 的等量減法之一），不是刪文件。
    def _evaluate_post_compact(self, ctx: HookContext) -> ResourceRequest | None:
        payload = ctx.payload or {}
        post_pct = float(payload.get("token_pct", 0.0))
        attempt = int(ctx.attempt or 0)
        max_retries = int(payload.get("max_retries", 3))
        still_high = self.should_compact(token_pct=post_pct, attempt=attempt,
                                         max_retries=max_retries)
        ok = self.process_compact_result(triggered_compact=still_high,
                                         peak_token_pct=post_pct)
        if not ok:
            return ResourceRequest(
                contributor=self.name(),
                request_halt=True,
                reason=f"Gap-008-E: 連續 compact 失敗 {self.compact_failure_count} 次，"
                       f"強制 TOKEN_HALT（post_compact token_pct={post_pct:.1f}%）",
            )
        return None
