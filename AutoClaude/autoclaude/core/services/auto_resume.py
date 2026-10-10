"""AutoResumeService — Layer 2 Coordinator（SD_03 §2.3 W3）。

外層自動恢復迴圈，從 _runner_impl.run():136~250 搬移而來。

職責：
  - 載入 Playbook（from path）
  - 呼叫 PlaybookKernel.run(playbook, start_idx)
  - 處理 evolution restart（切換至演化版 Playbook）
  - 處理 Token HALT → 等待排程時間後自動恢復（auto_resume 迴圈）
  - 等待一律走分片休眠（utils/sliced_sleep，PRD §4.5.2）；>max_inprocess_wait_seconds 的等待
    拒絕行程內長睡、回非零結果要求外部續跑（PRD §4.5.5；improving_113）
  - W2-T9（SD_04）：從 checkpoint 解析 start_idx（_resolve_start 實裝）
  - 成功完整跑完後清除該 playbook 的 checkpoint（DEF-200-510；非成功收尾一律保留）

設計原則：
  - 不持有步驟級業務邏輯（全在 Kernel + Plugin）
  - 行數 ≤ 250（行數預算 CI 強制）
  - 與 PlaybookKernel 解耦：僅透過 run() 介面通訊
  - core/ 不可 import infra/：state_repository 透過建構式注入；
    canonical_playbook_id 在使用點 lazy import，避免破壞分層
"""
from __future__ import annotations

import logging
import math
import os
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ...models.playbook import Playbook
from ...utils.resume_clock import seconds_until as resume_clock_seconds_until
from ...utils.sliced_sleep import sliced_sleep
from ..kernel_state import KernelResult
from ..ports.worktree_rescue import UNSAFE_TO_FREEZE
from ._auto_resume_metrics import AutoResumeMetrics, record_wake_and_emit

if TYPE_CHECKING:
    from ...utils.config import AppConfig
    from ..kernel import PlaybookKernel

logger = logging.getLogger("autoclaude.core.services.auto_resume")

# SD_05 W5 批3-C / M-9：對外 re-export AutoResumeMetrics 維持向後相容
__all__ = ["AutoResumeService", "AutoResumeMetrics", "load_playbook", "seconds_until_resume"]


# 🔴 R69（DEF-101-702／R68-01）：checkpoint 是否真的屬於 `playbook_path`。
# WHY：checkpoint 檔名來自 `Path(p).stem`，於是 ① 大小寫不敏感檔案系統（macOS APFS／
# Windows NTFS）上 `Foo.yaml` 與 `foo.yaml` 共用同一個檔案；② 不同目錄下的同名 playbook
# 也共用（平台無關）。兩種情形修前都會**靜默**從別支 playbook 的 step_idx 續跑。
# 判定順序：① checkpoint 沒記路徑（舊檔／PG 後端缺欄）→ 無從判定即放行，不製造回歸；
# ② `os.path.samefile` 為準（唯一能正確處理大小寫不敏感 APFS 的判準）；③ 檔案不存在
# （演化版產物已清掉等）退回 `normcase(realpath())` 字面正規化比對。
def _checkpoint_matches_playbook(ck: Any, playbook_path: str) -> bool:
    recorded = getattr(ck, "playbook_path", None)
    if not recorded:
        return True
    try:
        return os.path.samefile(recorded, playbook_path)
    except OSError:
        return (os.path.normcase(os.path.realpath(recorded))
                == os.path.normcase(os.path.realpath(playbook_path)))


class AutoResumeService:
    """外層自動恢復協調器（Layer 2，Kernel 之上）。"""

    def __init__(
        self,
        kernel: PlaybookKernel,
        config: AppConfig,
        *,
        state_repository: Any | None = None,
        quota_meter: Any | None = None,
        worktree_rescue: Any | None = None,
        is_interrupted: Callable[[], bool] | None = None,
    ):
        """初始化 AutoResumeService。

        Args:
            kernel: PlaybookKernel 實例
            config: AppConfig
            state_repository: 可選的 IStateRepository 實例（W2-T9 新增）；
                              未提供時 _resolve_start 永遠回 (0, [], False, None)
                              以維持向後相容（舊測試 / dry-run）
            worktree_rescue: 可選的 IWorktreeRescue（DEF-200-205）；未注入時
                              `_freeze_is_safe` 恆回 True，行為與修前位元級相同
            is_interrupted: 可選的「是否被中斷」判斷（improving_113）。等待在片與片之間檢查它；
                              中斷事件由呼叫端注入（main 傳入 hotkey 的 `triggered`，但入口目前
                              未呼叫 hotkey.register()，故該事件實際不會被設定）；未注入＝永不中斷
        """
        self._kernel = kernel
        self._cfg = config
        self._state_repo = state_repository
        # R82（ACQ-05）：QuotaMeterPort（可選）。None＝額度那一軸不存在，行為與修前相同。
        self._quota = quota_meter
        # DEF-200-205：IWorktreeRescue（可選）。None＝救援那一軸不存在，行為與修前相同。
        self._rescue = worktree_rescue
        self._is_interrupted = is_interrupted or (lambda: False)
        # SD_05 W5 批3-C / M-9：metrics observability
        self._metrics = AutoResumeMetrics()

    @property
    def metrics(self) -> dict:
        """供測試 / monitoring 取得 metrics snapshot（dict，防外部污染）。

        W5 三方審查 Major-A1：原本回 _metrics 物件參照導致外部可寫入，
        改回 snapshot() 淺拷貝以強制封裝。
        """
        return self._metrics.snapshot()

    @property
    def _metrics_object(self) -> AutoResumeMetrics:
        """internal helper：取得 mutable AutoResumeMetrics 物件（供測試斷言內部狀態）。"""
        return self._metrics

    def _emit_auto_resume_wake(
        self,
        scheduled_at: str | None,
        kind: str,
        wait_secs: float,
    ) -> None:
        """SD_05 W5 批3-C / M-9：委派至 _auto_resume_metrics.record_wake_and_emit。

        kernel 無 bus 屬性時（如測試用 _FakeKernel）跳過 EventBus emit，
        仍記錄 metrics（observability 不應受測試 fake 影響）。
        """
        bus = getattr(self._kernel, "bus", None)
        record_wake_and_emit(
            self._metrics, bus,
            kind=kind, scheduled_at=scheduled_at, wait_secs=wait_secs,
        )

    @property
    def kernel(self) -> PlaybookKernel:
        """供 PlaybookRunner M1 shim 存取底層 Kernel。"""
        return self._kernel

    def _resolve_start(
        self, playbook_path: str, fresh: bool
    ) -> tuple[int, list[str], bool, str | None]:
        """從 checkpoint 解析下次執行起點。

        Args:
            playbook_path: Playbook YAML 路徑
            fresh: True = 忽略 checkpoint 從步驟 0 開始

        Returns:
            (start_idx, step_log, has_checkpoint, scheduled_resume_at)

        策略：
          - fresh=True → (0, [], False, None)
          - state_repository=None → (0, [], False, None)（向後相容）
          - checkpoint 不存在 → (0, [], False, None)
          - checkpoint 存在 → (ck.step_idx, ck.completed_step_log, True,
                              ck.scheduled_resume_at)
        """
        if fresh:
            return 0, [], False, None
        if self._state_repo is None:
            return 0, [], False, None

        # lazy import 避免 core/ → infra/ 反向依賴；
        # canonical_playbook_id 為純函式，不引入 infra 重型依賴
        from ...infra.repositories.factory import canonical_playbook_id
        playbook_id = canonical_playbook_id(
            playbook_path, mode=self._cfg.storage.mode
        )
        try:
            ck = self._state_repo.load_checkpoint(playbook_id)
        except (FileNotFoundError, ValueError, OSError) as exc:
            # SD_04 W2 三方審查 Dev-W2-Min-1：將 except Exception 收斂為
            # 具體可預期型別，避免吞噬非預期錯誤（如 KeyboardInterrupt / TypeError）
            logger.warning(
                "AutoResumeService | load_checkpoint 失敗（視為無 checkpoint）: %s", exc
            )
            return 0, [], False, None
        if ck is None:
            return 0, [], False, None
        if not _checkpoint_matches_playbook(ck, playbook_path):
            # 🔴 R69（DEF-101-702／R68-01）：checkpoint 檔名來自 `Path(p).stem`，於是
            # ① 大小寫不敏感檔案系統（macOS APFS／Windows NTFS）上 `Foo.yaml` 與
            # `foo.yaml` 共用同一個檔案；② 不同目錄下的同名 playbook 也共用（平台無關）。
            # 兩種情形修前都會**靜默**載入別支 playbook 的執行狀態，從別人的 step_idx
            # 續跑——零校驗、零訊號。checkpoint 自己記著 `playbook_path`，比對它即可把
            # 靜默錯配變成可見降級：視為無 checkpoint 從頭跑（安全方向），並 warn 出兩邊
            # 路徑。刻意不拋例外——「從頭跑一次」比「中止使用者的執行」代價低得多。
            logger.warning("AutoResumeService | checkpoint 屬於別支 playbook（id 撞名），"
                           "視為無 checkpoint 從頭：ck=%r，本次=%r",
                           ck.playbook_path, playbook_path)
            return 0, [], False, None
        return (
            ck.step_idx,
            list(ck.completed_step_log),
            True,
            ck.scheduled_resume_at,
        )

    def run(self, playbook_path: str, fresh: bool = False) -> KernelResult:
        """執行含自動恢復的完整 Playbook 生命週期。"""
        _current_path = playbook_path
        # DEF-200-510：本次 run 經手過的 playbook 路徑（演化重載會換路徑），成功收尾時一併清
        _visited = [playbook_path]
        _evolution_count = 0
        _max_evolutions = self._cfg.playbook.max_evolutions
        auto_resume_count = 0
        max_resumes = self._cfg.token_guard.max_auto_resumes
        _fresh = fresh

        while True:
            # W2-T9：每輪迴圈重新解析 start_idx（演化重載後 path 變更需重新計算）
            start_idx, _step_log, has_ck, sched = self._resolve_start(
                _current_path, _fresh
            )
            # DEF-200-511：--fresh 只管「這一輪不採信啟動前就存在的 checkpoint」，解析完即歸
            # False，halt 後的續跑輪才讀得到剛存的 checkpoint（修前一路帶著 True ⇒ 續跑輪
            # 無視它、從 0 重來）。演化重載分支稍後會把它設成 evolution_fresh_required（那一輪
            # 照該值），下一輪經這裡再歸 False。舊 PlaybookRunner 在 _resolve_start 之後同樣
            # `fresh = False`，service 移植時漏了。
            _fresh = False

            # improving_113：playbook 提前到等待之前載入——壞檔／缺檔不必先睡完才報錯，
            # 拒絕長睡／被中斷而就地返回時，結果也才帶得出 total_steps。
            playbook = load_playbook(_current_path)

            # W2-T10 邊界 3：若 checkpoint 帶有 scheduled_resume_at，
            # 計算剩餘秒數；過期或 ≤ 0 立即執行，未過期則分片休眠後繼續
            if has_ck and sched:
                wait_secs = seconds_until_resume(sched)
                if wait_secs > 0:
                    logger.info(
                        "AutoResumeService | checkpoint scheduled_resume_at "
                        "距今 %.0fs", wait_secs,
                    )
                else:
                    logger.info(
                        "AutoResumeService | checkpoint scheduled_resume_at 已過期，立即繼續"
                    )
                # SD_05 W5 / M-9：checkpoint resume 也記錄一筆 metrics（在 _wait 內）
                stop = self._wait("checkpoint_resume", sched, wait_secs, _current_path)
                if stop:
                    stalled = KernelResult.halted_(start_idx, len(playbook.tasks), _step_log, [])
                    return replace(stalled, reason=stop[0], scheduled_resume_at=stop[1],
                                   halt_step_idx=start_idx)

            result = self._kernel.run(playbook, start_idx=start_idx)

            # 演化後自動重載演化版 Playbook
            if result.evolved_playbook_path and _evolution_count < _max_evolutions:
                _evolution_count += 1
                logger.info(
                    "AutoResumeService | 自動重載演化版 Playbook #%d: %s",
                    _evolution_count, result.evolved_playbook_path,
                )
                # SD_05 W5 / M-9 / Major-A3：evolution restart metrics
                # wait_secs 由 result.scheduled_resume_at 計算（演化也可能帶恢復時間）；
                # 若無則為 0（立即重啟）
                evo_wait = seconds_until_resume(result.scheduled_resume_at)
                self._emit_auto_resume_wake(
                    result.scheduled_resume_at, "evolution", evo_wait,
                )
                _current_path = result.evolved_playbook_path
                _visited.append(_current_path)
                _fresh = result.evolution_fresh_required
                auto_resume_count = 0
                continue

            # improving_78 W-78-1（DEF-78-001）：token HALT → 先存 path-aware checkpoint，
            # 使下輪 _resolve_start（與日後手動重跑）能從 halt_step_idx 續跑。
            # Kernel 為純 DAG 不持有 path，故持久化落在握 path 的本協調層。
            # 🔴 僅對「本輪新接線的 token-observer halt 路徑」生效（必帶 halt_step_idx）；
            # halt_step_idx is None（既有/其他 halt 路徑已自存 checkpoint）→ 不覆蓋（防退化）。
            halt_sched: str | None = None
            if result.halted and result.halt_step_idx is not None:
                halt_sched = self._persist_halt_checkpoint(
                    _current_path, playbook, result
                )

            # 🔴 DEF-200-205（PRD §4.5.9 R-4.5.9-4）：halt ＝ 即將凍結，而凍結前必須先把
            # 髒污工作樹保全。救援失敗（DIRTY_UNSAVED）時**絕不 fail-open**——不得往下走
            # 到等待／自動喚醒，因為那兩個狀態的語意是「工作已保全，可以安全睡」，而此刻
            # 工作沒有保全。順序刻意排在 `_persist_halt_checkpoint` **之後**：state.json
            # 是診斷用的索引，patch 是工作本體，索引先落地才有東西指向 patch。
            if result.halted and not self._freeze_is_safe():
                return result

            # Token HALT → 等待排程時間後自動恢復
            if (
                result.halted
                and self._cfg.token_guard.auto_resume
                and auto_resume_count < max_resumes
            ):
                auto_resume_count += 1
                # R81：`result.scheduled_resume_at` 在 Kernel 路徑上恆為 None（見
                # _persist_halt_checkpoint 內的說明與實測），故以本輪剛排定的時刻兜底。
                sched = result.scheduled_resume_at or halt_sched
                wait_secs = self._halt_wait_seconds(sched)
                logger.info(
                    "AutoResumeService | AUTO_RESUME #%d/%d | 排定等待 %.0fs",
                    auto_resume_count, max_resumes, wait_secs,
                )
                # SD_05 W5 / M-9：halt resume metrics + ON_AUTO_RESUME_WAKE（在 _wait 內）
                stop = self._wait("halt", sched, wait_secs, _current_path)
                if stop:
                    return replace(result, reason=stop[0], scheduled_resume_at=stop[1])
                # halt 後下輪 _resolve_start 讀剛存的 checkpoint（_fresh 已於上方歸 False，
                # DEF-200-511）
                continue

            # DEF-200-510：只有整條 run 真的走完才清 checkpoint（HALT／ESCALATION／中斷／
            # 演化重載留下的都是續跑點）。success 與 halted／escalated 由工廠方法保證互斥，
            # 這裡仍雙重確認旗標——清除使用者的進度不可逆，不能只信單一旗標。
            if result.success and not (result.halted or result.escalated):
                self._clear_finished_checkpoints(_visited)
            return result

    # improving_113（PRD §4.5.2／§4.5.5）：兩處等待的唯一出口。回傳非 None ＝ 本次不再等，
    # 內容為 (reason, 續跑時刻)，呼叫端就地返回 success=False 的結果（main 據此回非零 rc）：
    #   · external_resume_required：等待 > max_inprocess_wait_seconds ⇒ 拒絕行程內長睡。此時
    #     checkpoint 已由上游落地（halt 路徑＝_persist_halt_checkpoint；續跑路徑＝剛讀到的那份）；
    #     這裡再讀回一次確認，讀不回來就在訊息裡說「未確認落地」而不是謊報。🔴 本版沒有任何元件
    #     自動承接被拒絕的等待（本層也刻意不自己蓋排程器，免得同一份知識住兩個家）：
    #     引擎以 rc=1 退出，須由外部（人工／自備排程器）在續跑時刻後重啟。
    #   · interrupted_during_wait：等待中被中斷（呼叫端注入的 is_interrupted）；發生在等待之中，
    #     故 emit 已記錄。
    # 拒絕在 emit 之前判：根本沒開始的等待不得記成一次喚醒。
    def _wait(self, kind: str, sched: str | None, wait_secs: float,
              path: str) -> tuple[str, str | None] | None:
        tg = self._cfg.token_guard
        if wait_secs > tg.max_inprocess_wait_seconds:
            saved = self._state_repo is not None and self._resolve_start(path, False)[2]
            # halt 路徑的 checkpoint 時刻是 resume_delay 推算的，額度軸上與要等的 wait_secs 無關
            # ⇒ 外部續跑者若以它為準會早醒重啟：拒絕時改寫成真實的等待終點（失敗＝None，不充數）。
            at = sched
            if kind == "halt":
                at = self._pin_resume_time(path, wait_secs) if saved else None
            logger.error(
                "AutoResumeService | 需外部續跑：需等 %.0fs（續跑時刻 %s）> "
                "max_inprocess_wait_seconds=%ds ⇒ 拒絕行程內長睡（checkpoint %s）；"
                "請於該時刻後由外部（OS 排程器／人工）重啟",
                wait_secs, at or "未排定", tg.max_inprocess_wait_seconds,
                "已落地" if saved else "未確認落地",
            )
            return "external_resume_required", at
        self._emit_auto_resume_wake(sched, kind, wait_secs)
        out = sliced_sleep(
            wait_secs, tg.sleep_slice_seconds, tg.clock_jump_tolerance_seconds,
            wall=time.time, mono=time.monotonic, sleep=time.sleep, stop=self._is_interrupted,
        )
        return ("interrupted_during_wait", sched) if out.interrupted else None

    # 把既有 checkpoint 的 scheduled_resume_at 改寫成 now + wait_secs（沿用 _persist_halt_checkpoint
    # 同一支 schedule_resume；向上取整到分鐘，寧晚勿早）。尚存的拒絕結果比崩潰有用 ⇒ 任何失敗都
    # 只出聲、回 None。
    def _pin_resume_time(self, path: str, wait_secs: float) -> str | None:
        from ...infra.repositories.factory import canonical_playbook_id
        try:
            at = self._state_repo.schedule_resume(
                canonical_playbook_id(path, mode=self._cfg.storage.mode), math.ceil(wait_secs / 60),
            )
        except Exception as exc:                     # noqa: BLE001 — 見上方註解
            logger.warning("AutoResumeService | 改寫 checkpoint 續跑時刻失敗: %s", exc)
            return None
        return at.isoformat(timespec="seconds")

    # 🔴 DEF-200-205：「敢不敢睡」這個判斷。回 False ＝ 工作沒保全 ⇒ 呼叫端必須就地返回，
    # 不得轉入 WAITING_RESET／LONG_HIBERNATE（R-4.5.9-4 逐字：絕不 fail-open）。
    # 🔴 判準是「status ∈ UNSAFE_TO_FREEZE」而不是「status == SAVED」：後者會把 adapter 的
    # `CLEAN`（工作樹本來就乾淨、沒東西要救）判成不安全 ⇒ 每一次乾淨的 halt 都拒絕續跑，
    # 那是假紅，而假紅會讓整道判準被關掉。兩個方向都要對，所以判準收在「明確不安全」那一側。
    # 🔴 例外一律當成不安全（fail-closed）：救援自己拋錯時「工作有沒有保全」是**不知道**，
    # 而 R-4.5.9-4 的整段出發點就是不准把「量不到」讀成「量到零」。
    def _freeze_is_safe(self) -> bool:
        if self._rescue is None:
            return True
        try:
            outcome = self._rescue.rescue()
        except Exception as exc:                     # noqa: BLE001 — 見上方 fail-closed 註解
            logger.error(
                "AutoResumeService | 髒污工作樹救援拋錯（%s: %s）⇒ 工作是否保全不明，"
                "禁止自動喚醒", type(exc).__name__, exc,
            )
            return False
        status = getattr(outcome, "status", "")
        if status in UNSAFE_TO_FREEZE:
            logger.error(
                "AutoResumeService | %s：髒污工作樹未保全 ⇒ 禁止自動喚醒（patch=%s，"
                "expected=%s，actual=%s，bytes=%s/%s，attempts=%s）：%s",
                status, getattr(outcome, "patch_path", ""),
                getattr(outcome, "expected_checksum", ""),
                getattr(outcome, "actual_checksum", ""),
                getattr(outcome, "bytes_written", 0),
                getattr(outcome, "bytes_read_back", 0),
                getattr(outcome, "attempts", 0),
                getattr(outcome, "reason", ""),
            )
            return False
        logger.info("AutoResumeService | 凍結前工作樹保全：status=%s patch=%s",
                    status, getattr(outcome, "patch_path", ""))
        return True

    # 🔴 R82（ACQ-05／ACA-01）：halt 之後「等多久」。
    # 修前一律讀寫死的 `resume_delay_minutes=30`，而實測額度視窗 min 0.5 分／max 253 分
    # ——**沒有一段等於 30 分**。reset 時刻只能觀測不能算（R79 全庫逐字稿掃出 7 個相異值、
    # 沒有一個落在 5 小時格點上＝滾動視窗），所以這裡只採信量測到的 `resets_at`。
    # 三分支（ADR-XPLAT-005 §2.3）：
    #   session / five_hour → 等到 resets_at（+ 已由 resume_wait_seconds 夾 0 下界）
    #   weekly / spend      → resume_wait_seconds 回 None ⇒ 落回既有 context 路徑的排程；
    #                         那類「沒有 reset 可等」，排程是錯的動作（見下方 WARNING）
    #   量不到               → 同上，行為與修前位元級相同
    # 🔴 誠實劃界：這一段只在**行程還活著**時成立。行程一死（Ctrl+C／關機／額度撞線把
    # subagent 全殺）就沒有人會回來——那一半屬於 OS 級喚醒：
    # 本版無自動承接者；拒絕長睡時以 rc=1 退出並明示需外部重啟（improving_113）。
    # 🔴 水位低於 quota_throttle_pct 時**完全不碰**額度那一軸：這一支同時服務 context halt，
    # 而 context halt 與額度無關——不設這道門的話，每一次 context halt 都會印一行
    # 「額度 kind=weekly_all 沒有等得到的 reset」，那是與本次 halt 無關的假訊號。
    def _halt_wait_seconds(self, sched: str | None) -> float:
        reading = self._quota.read() if self._quota is not None else None
        if reading is None or reading.pct < self._cfg.token_guard.quota_throttle_pct:
            return seconds_until_resume(sched)
        from ..ports.quota_meter import resume_wait_seconds
        quota_wait = resume_wait_seconds(reading)
        if quota_wait is None:
            logger.warning(
                "AutoResumeService | 額度 kind=%s 沒有等得到的 reset（resets_at=%s）"
                "——不以額度時刻排程，落回既有排程；請人工決定何時重啟",
                reading.kind, reading.resets_at,
            )
            return seconds_until_resume(sched)
        logger.info(
            "AutoResumeService | 依觀測到的額度 reset 排程：kind=%s resets_at=%s 等待 %.0fs",
            reading.kind, reading.resets_at, quota_wait,
        )
        return quota_wait

    # improving_78 W-78-1（DEF-78-001）：存最小 token HALT checkpoint。
    # resume 點 = `result.halt_step_idx`（Kernel HALT 當下步驟）。Kernel 為純 DAG 不持有
    # path，故 path-aware 持久化落在本協調層（握 _current_path）。
    # state_repository=None（dry-run / 舊測試）→ no-op，維持向後相容。
    # 🔴 誠實限制：跨 session 計數器（goto/inject/skip/evolution）不隨此最小 checkpoint
    # 持久化（預設空 dict）；核心 resume 資料（step_idx/peak/已完成）齊備。
    # 🔴 R82：本段由 docstring 改 `#` 註解，**一字未刪**——理由同 policy.py 內同型註記
    # （check_loc_budget 自己印的指引：說明寫 # 註解，docstring 會被 count_loc 計入）。
    def _persist_halt_checkpoint(
        self, playbook_path: str, playbook: Playbook, result: KernelResult,
    ) -> str | None:
        if self._state_repo is None:
            return
        step_idx = result.halt_step_idx if result.halt_step_idx is not None else 0
        _halt_task = (
            playbook.tasks[step_idx] if 0 <= step_idx < len(playbook.tasks) else None
        )
        step_id = _halt_task.step_id if _halt_task else ""
        # lazy import 避免 core/ → infra/ 反向依賴（與 _resolve_start 既有作法一致）
        from ...infra.repositories.factory import canonical_playbook_id
        from ...utils.checkpoint_manager import PlaybookCheckpoint
        playbook_id = canonical_playbook_id(playbook_path, mode=self._cfg.storage.mode)
        cp = PlaybookCheckpoint(
            playbook_path=playbook_path,
            step_idx=step_idx,
            step_id=step_id,
            total_steps=result.total_steps,
            project=playbook.project,
            # DEF-101-051：HALT 點 task 之 goal_task_id（三層來源時非 None）
            goal_task_id=getattr(_halt_task, "goal_task_id", None),
            completed_step_log=list(result.step_log),
            completed_step_ids=list(result.completed_step_ids),
            peak_token_pct=result.peak_token_pct,
        )
        try:
            self._state_repo.save_checkpoint(playbook_id, cp)
            logger.info(
                "AutoResumeService | 已存 token HALT checkpoint（step_idx=%d, peak=%.0f%%）",
                step_idx, result.peak_token_pct,
            )
        # 誠實劃界（QA-03，2026-10-10）：File／Pg 後端把 OSError 包成 StateRepositoryError
        # （file_state_repository.py／pg_state_repository.py），不在下面的攔截集合內 ⇒
        # 真實後端存檔失敗會往外傳（fail-loud）；本分支只攔原生 OSError／ValueError
        # （InMemory／自訂 repo）。刻意不擴攔：存不下 HALT checkpoint 卻繼續等待續跑，
        # 醒來會從 0 或舊斷點重跑——崩潰比靜默重跑好。
        except (OSError, ValueError) as exc:
            logger.warning("AutoResumeService | 存 HALT checkpoint 失敗: %s", exc)
            return None
        # R81（HLM-S1-02 端到端實測）：`token_guard.resume_delay_minutes` 在 Kernel 路徑上
        # 從未被套用過。CheckpointPlugin 的 `save_token_halt` 確實會呼叫 schedule_resume，
        # 但它第一行就要 `payload["request_halt"]`，而 Kernel emit ON_TOKEN_USAGE 時
        # 送的 payload 只有 token_pct / step_id / max_retries ⇒ 那支 handler 在 Kernel
        # 路徑上直接 return None（「機制蓋好沒接電」）。於是 `result.scheduled_resume_at`
        # 恆為 None、`seconds_until_resume(None)` 恆回 0.0。
        # 端到端實測（PG 後端、halt 門檻 90%、設定 resume_delay_minutes: 2）：
        #   `AUTO_RESUME #7/10 | 等待 0s 後繼續` … `#10/10`，10 次全部發生在**同一秒**，
        #   然後整場 run 以 halted 結束——正是「不等就續跑、連燒 max_auto_resumes 次」。
        # 排程交給 state repo 自己做：各後端的時間形態（File naive／Pg aware）由它決定，
        # 消費端已收斂成單一時鐘（utils/resume_clock.py），兩種形態都算得對。
        delay = self._cfg.token_guard.resume_delay_minutes
        if delay <= 0:
            return None
        try:
            resume_at = self._state_repo.schedule_resume(playbook_id, delay)
        except (OSError, ValueError) as exc:
            logger.warning("AutoResumeService | 排程 HALT 恢復時間失敗: %s", exc)
            return None
        return resume_at.isoformat(timespec="seconds")

    # DEF-200-510：checkpoint 生命週期的「清」。讀（_resolve_start）、寫
    # （_persist_halt_checkpoint）、清三件事住同一層（握 path 的協調層）。清的這一件原本在
    # 生產路徑零呼叫——`clear_checkpoint` 契約寫「步驟完成或 --fresh 時呼叫」，唯一呼叫者在
    # 已無建構點的舊 PlaybookRunner——於是 HALT 留下的 checkpoint 在續跑成功後原封不動，
    # 下一次不加 --fresh 的執行從舊斷點重跑（T01 被靜默跳過）。
    # 為什麼不放 CheckpointPlugin 訂閱 POST_RUN：Kernel 是純 DAG、不持有 path，POST_RUN
    # payload 只有 completed_step_ids／total_steps，plugin 算不出 playbook_id
    # （CheckpointManager 要 path 才算得出 id）；硬塞 path 要改 Kernel 簽名，而演化重載鏈上
    # 經手的多個路徑、下方的撞名判準，也都只有握 path 的本層看得到。
    # 🔴 只清「屬於本 playbook」的那一份（沿用 `_resolve_start` 的 R69 判準）：id 撞名時那份
    # 是別支 playbook 的續跑點，本次執行本來就不採信它，成功收尾更不能順手刪掉。
    # 🔴 清不掉是降級、不是失敗：此刻 playbook 已經成功，rc 不得因善後失敗而變——任何例外
    # 只出聲（與 _pin_resume_time 同款理由；DualStateRepository strict 會重拋任意型別，
    # 故不縮窄）。
    def _clear_finished_checkpoints(self, paths: list[str]) -> None:
        if self._state_repo is None:
            return
        from ...infra.repositories.factory import canonical_playbook_id
        for path in dict.fromkeys(paths):
            try:
                playbook_id = canonical_playbook_id(path, mode=self._cfg.storage.mode)
                ck = self._state_repo.load_checkpoint(playbook_id)
                if ck is not None and _checkpoint_matches_playbook(ck, path):
                    self._state_repo.clear_checkpoint(playbook_id)
                    logger.info(
                        "AutoResumeService | playbook 成功完成，已清除 checkpoint: %s", playbook_id,
                    )
            except Exception as exc:                     # noqa: BLE001 — 見上方「降級不是失敗」
                logger.warning(
                    "AutoResumeService | 成功收尾後清除 checkpoint 失敗（降級，結果不變）: %s", exc,
                )


def load_playbook(path: str) -> Playbook:
    """從 YAML 路徑載入 Playbook。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Playbook 不存在: {path}")
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Playbook(**data)


# 例外處理沿革：SD_04 W2 三方審查 Arch-W2-Min-1 把 except 擴大到
# ValueError + TypeError（後者涵蓋外部傳入 list / dict / int 等無 fromisoformat
# 介面的型別），統一回退 0.0 並 warning——該行為由 `resume_clock.seconds_until`
# 原樣承接。R81（HLM-S1-02）改為委派：這段邏輯原有三份複本，而三份都只會算
# naive，切到 Pg 後端（產出 aware）時會靜默回 0.0＝不等就續跑。
def seconds_until_resume(scheduled_resume_at: str | None) -> float:
    """回傳距排程恢復的剩餘秒數；未設定或已過期則回傳 0.0。"""
    return resume_clock_seconds_until(scheduled_resume_at)
