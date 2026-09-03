# build_kernel — Kernel + 15 Plugin + MutationApplyService 組裝工廠（Phase 4）。
#
# 🔴 R86：本段由 docstring 改為 `#` 註解，**一字未刪**（`check_loc_budget` 自己印的指引：
# docstring 行會被 count_loc 計入、`#` 不會）。本輪要把配速契約的 degraded cap 從 `.env`
# 接到 `build_quota_meter`，而 total LOC 餘裕當回合實測只有 12 行 ⇒ 等量減法（R82 先例）。
#
# 對應：
#   - SD_Improving_01.md v1.1 §3.6 Layer 4 CLI 圖
#   - SD_Improving_02.md v1.1 §1.4「main.py 的 DI 組裝為唯一決定後端的位置」
#   - SD_Improving_05 W0 T0-2：抽 `_build_plugin_set()` + `_register_in_order()`
#     解決 wire_plugins_with_registry / build_kernel 兩條路徑的 SSOT 漂移（M-3）
#
# 職責：
#   - 接受 AppConfig + 必要相依，組裝完整可運行的 PlaybookKernel
#   - 註冊全部 15 個 Plugin（按 priority 自動排序）
#   - 整合 GotoCounterPlugin + CheckpointPlugin（Gap-042/048/049 計數器持久化）
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..plugins import (
    CheckpointPlugin,
    ConvergencePlugin,
    CrossStepValidatorPlugin,
    EvolutionPlugin,
    FastPathPlugin,
    GlobalGoalAnchorPlugin,
    GoalProgressPlugin,
    GoalSynthesisPlugin,
    GotoCounterPlugin,
    HotkeyPlugin,
    KnowledgeBasePlugin,
    NotificationPlugin,
    PlaybookPersistencePlugin,
    PreferenceMemoryPlugin,
    PreRunValidatorPlugin,
    RtmWritebackPlugin,
    SddGovernancePlugin,
    TokenGuardPlugin,
    TranslationLearnerPlugin,
)
from ..utils.checkpoint_manager import CheckpointManager
from ..utils.config import AppConfig
from ..utils.knowledge_base import FailureKnowledgeBase
from .event_bus import EventBus
from .kernel import PlaybookKernel
from .ports.brain import IBrain
from .ports.evaluator import IEvaluator
from .ports.executor import IExecutor
from .ports.observability import IObservabilityPort
from .ports.quota_meter import DEGRADED_CAP
from .services.mutation.service import MutationApplyService


# R82（ACQ-01）：額度水位量測器的唯一建構點。抽成函式而非 inline，是為了讓
# AutoResumeService（core/，不得 import infra）也能經由 main.py 拿到**同一種**實作，
# 而不是各自 new 一個（同一份知識住兩個家正是本 repo 反覆在治的形態）。
# R86：`degraded_cap`＝配速契約量不到時的併發地板（**不是**不設限）。預設值就是 port 那一份
# 鏡射常數，所以 main.py 既有的無參呼叫行為零變化；`_build_plugin_set` 那一個呼叫點把
# `.env` 讀出來的值（`AUTOSDD_QUOTA_DEGRADED_CAP`）傳進來，讓那個鍵真的有讀者。
def build_quota_meter(degraded_cap: int = DEGRADED_CAP) -> Any:
    from ..infra.adapters.file_quota_meter import FileQuotaMeterAdapter
    return FileQuotaMeterAdapter(degraded_cap=degraded_cap)


# 🔴 DEF-200-205：髒污工作樹救援（PRD §4.5.9）的唯一建構點。理由與 build_quota_meter 同型
# ——消費端 AutoResumeService 住 core/、依 core-purity contract 不得 import infra，於是
# 「哪一種救援實作、patch 落哪、通知走哪個通道」這幾件知識必須有唯一的家；各呼叫端自己
# new 一個就是同一份知識住兩個家（本 repo 一路在治的形態）。
# 🔴 `notifier` 必須在這裡把 `config.notification.enabled` 綁進去：`utils.notifier.notify`
# 的 `enabled` 預設 True ⇒ 不綁就等於這條路徑無視使用者的通知設定（同 build_goal_decomposer
# 那一格 R84 踩過的坑）。而 R-4.5.9-4 第 3 點要求 DIRTY_UNSAVED 走桌面通道 loud 恰好一次，
# 所以通道**必須**接上，不能因為怕吵就不傳 notifier。
def build_worktree_rescue(
    cfg: AppConfig, *, worktree: str | Path | None = None, agent_id: str = "agent",
) -> Any:
    from ..infra.adapters.dirty_worktree_rescue import (  # noqa: PLC0415
        DirtyWorktreeRescueAdapter,
    )
    from ..utils.notifier import notify  # noqa: PLC0415
    return DirtyWorktreeRescueAdapter(
        Path.cwd() if worktree is None else worktree,
        cfg.checkpoint_dir,
        agent_id=agent_id,
        notifier=lambda msg: notify(
            "AutoClaude — 髒污工作樹", msg, enabled=cfg.notification.enabled),
    )

# Plugin 註冊順序（SSOT — 兩條組裝路徑共用，避免 M-3 漂移）
#
# EventBus 排序規則：
#   主鍵：plugin.priority()（數值越小越先觸發）
#   tie-breaker（同 priority 才採用）：本元組的列順序
#
# SD_Improving_05 W4-5：新增 2 plugin
#   - playbook_persistence (priority=40) → priority 高低天然排序（35 < 40 < 50）
#   - fast_path (priority=50) → **tie-breaker**，需在 notification/knowledge_base/
#     goal_synthesis（皆 50）之前，確保 PRE_ATTEMPT phase 早於同優先級 plugin 觸發
#
# ⚠️ 重要：fast_path / notification / knowledge_base / goal_synthesis 4 個 plugin
# 共用 priority=50；register 順序就是 tie-breaker，重排會破壞 PRE_ATTEMPT 早觸發語意
_REGISTER_ORDER: tuple[str, ...] = (
    "pre_run_validator",
    "hotkey",
    "cross_step_validator",
    "token_guard",
    "global_goal_anchor",
    "playbook_persistence",
    # AutoSDD_improving_01 W7：sdd_governance (priority=45) 插於
    # playbook_persistence(40) 與 fast_path 等 tie-breaker 群(50) 之間
    # → SCG 閘門先於快速路徑，且不與 tie-breaker 群同優先級（迴避順序耦合）
    "sdd_governance",
    "fast_path",
    "notification",
    "knowledge_base",
    # Improving_012 Phase 1（F-C1/F-C2，priority=50 tie-breaker 群尾端；
    # 不影響 fast_path 先位語意）
    "preference_memory",
    "goal_synthesis",
    "goal_progress",
    # AutoSDD_improving_24 W-24-2：rtm_writeback (priority=52) 逆向回寫閉環，
    # 置於 goal_progress(50) 之後、convergence(65) 之前；非 SDD playbook 全程 no-op
    "rtm_writeback",
    # AutoSDD_improving_60 W-60-4：translation_learner (priority=55) A→L5 轉譯策略
    # 元學習活體化，priority 介於 rtm_writeback(52) 與 convergence(65) 之間（與 A 軌
    # 反饋族群相鄰）；非 SDD playbook 全程 no-op。POST_RUN 自跨 session history 元學習
    # 提議（proposed，apply 仍人工）。priority=55 獨佔 → dispatch 序由數值唯一決定，
    # 與 register 文字序無耦合。
    "translation_learner",
    "convergence",
    "evolution",
    "goto_counter",
    "checkpoint",
)


def _build_plugin_set(
    cfg: AppConfig,
    *,
    minimax_client: Any | None = None,
    hotkey: Any | None = None,
    state_repository: Any | None = None,
    observability: IObservabilityPort | None = None,
    brain: IBrain | None = None,
) -> dict[str, Any]:
    # 組裝完整的 Plugin 集合（含 MutationApplyService），回傳以 name 為 key 的 dict。
    # （R86 等量減法：docstring → 註解，一字未刪；理由見檔頭。）
    #
    # SD_Improving_05 W0 T0-2：SSOT 抽出，wire_plugins_with_registry 與 build_kernel
    # 皆改呼叫此函式，避免兩條路徑漂移（M-3）。
    #
    # 回傳 key（與 _REGISTER_ORDER 對應 + 兩個非註冊項）：
    #   註冊：pre_run_validator, hotkey?, cross_step_validator, token_guard,
    #         global_goal_anchor, playbook_persistence, sdd_governance, fast_path,
    #         notification, knowledge_base, preference_memory, goal_synthesis,
    #         goal_progress, rtm_writeback, translation_learner, convergence,
    #         evolution, goto_counter, checkpoint
    #   非註冊：mutation_service（注入 PlaybookKernel）
    # SD_04 W2 三方審查 Dev-W2-Crit-1 / Arch-W2-Maj-1：id_resolver SSOT
    # （確保 db_only / both 模式下 CheckpointPlugin 與 AutoResumeService 使用一致 ID）
    from ..infra.repositories.factory import (  # noqa: PLC0415
        build_goal_progress_ledger,
        build_kb_metric_store,
        build_preference_store,
        canonical_playbook_id,
    )

    kb_path = f"{cfg.checkpoint_dir}/failure_knowledge_base.jsonl"
    # F-C3 / ADR-SD09-006：IKbMetricStore 依 storage.mode 路由（wiring 為
    # core-purity 唯一豁免點，import infra 合法）；建構失敗不阻斷主流程
    # （KB metrics 為輔助功能，與 observability 可選注入同哲學）
    try:
        kb_metric_store = build_kb_metric_store(cfg.checkpoint_dir, cfg.storage)
    except Exception:
        kb_metric_store = None
    # F-C1：IPreferenceStore 依 storage.mode 路由 + config.preferences seed（冪等 last-wins）
    try:
        preference_store = build_preference_store(cfg.checkpoint_dir, cfg.storage)
        for _k, _v in (cfg.preferences or {}).items():
            preference_store.set(_k, str(_v), scope="global")
    except Exception:
        preference_store = None
    # F-C2：GoalProgressLedger 依 storage.mode 路由
    try:
        goal_progress_ledger = build_goal_progress_ledger(cfg.checkpoint_dir, cfg.storage)
    except Exception:
        goal_progress_ledger = None
    checkpoint_mgr = CheckpointManager(
        cfg.checkpoint_dir,
        repository=state_repository,
        id_resolver=lambda p: canonical_playbook_id(p, cfg.storage.mode),
    )

    plugins: dict[str, Any] = {
        "pre_run_validator": PreRunValidatorPlugin(),
        "cross_step_validator": CrossStepValidatorPlugin(),
        # R82（ACQ-01）：注入 QuotaMeterPort 的檔案契約實作。wiring 是 core-purity contract
        # 的唯一豁免點，import infra adapter 合法；plugin 自己拿到的只是一個 port。
        "token_guard": TokenGuardPlugin(
            token_guard_cfg=cfg.token_guard,
            quota_meter=build_quota_meter(cfg.token_guard.quota_degraded_cap),
        ),
        "global_goal_anchor": GlobalGoalAnchorPlugin(playbook_cfg=cfg.playbook),
        # SD_Improving_05 W4-3：PlaybookPersistencePlugin（ON_EVOLUTION_APPLY phase）
        "playbook_persistence": PlaybookPersistencePlugin(
            checkpoint_dir=cfg.checkpoint_dir,
        ),
        # SD_Improving_05 W4-2：FastPathPlugin（PRE_ATTEMPT phase）
        "fast_path": FastPathPlugin(),
        "notification": NotificationPlugin(
            enabled=cfg.notification.enabled, app_config=cfg
        ),
        "knowledge_base": KnowledgeBasePlugin(
            # SD_08 W4 / ADR-SD08-004 §2.4：注入 IObservabilityPort 啟用 4 metric emit
            # （未注入 observability 時為 None，metrics 純記憶體累計仍生效）
            # F-C3：注入 IKbMetricStore 啟用跨 session 持久化（POST_RUN flush）
            knowledge_base=FailureKnowledgeBase(
                kb_path, observability=observability, metric_store=kb_metric_store,
            )
        ),
        "goal_synthesis": GoalSynthesisPlugin(
            minimax_client=minimax_client,
            enabled=cfg.playbook.goal_synthesis_enabled,
            fail_closed=cfg.playbook.goal_synthesis_fail_closed,
        ),
        # Improving_012 Phase 1：F-C1 偏好注入（PRE_CORRECTION）/ F-C2 進度 ledger（POST_RUN）
        "preference_memory": PreferenceMemoryPlugin(preference_store=preference_store),
        "goal_progress": GoalProgressPlugin(ledger=goal_progress_ledger),
        # AutoSDD_improving_01 W7：SddGovernancePlugin（PRIORITY=45）。
        # ISpecSource 於 wiring 組裝注入——wiring 是 core-purity contract（#2）
        # 唯一豁免點，import infra adapter 合法。plugin 於 PRE_RUN 依
        # workflow_type ∈ {aisdlc, aisdlc_sdd} 自行啟用，非 SDD playbook 全程 no-op。
        "sdd_governance": _build_sdd_governance(brain, observability),
        # AutoSDD_improving_24 W-24-2：A 軌逆向回寫閉環。adapter（純函式）+ sink
        # 於 wiring 注入（core-purity 唯一豁免點 import infra 合法）。
        "rtm_writeback": _build_rtm_writeback(cfg, observability),
        "convergence": ConvergencePlugin(),
        # AutoSDD_improving_27 W1：A 軌 RTM 反饋讀回（flag-gated）。feedback source
        # 與 _build_rtm_writeback 的 FileRtmSink 同 base_dir 對稱；flag 預設 OFF 時
        # plugin 內 _rtm_gap_annotation 立即短路（零退化），source 不被觸碰。
        "evolution": EvolutionPlugin(
            minimax_client=minimax_client,
            rtm_feedback=_build_rtm_feedback_source(cfg),
            enable_rtm_feedback=cfg.playbook.enable_rtm_feedback,
        ),
        # AutoSDD_improving_60 W-60-4：A→L5 轉譯策略元學習活體化。sink（File-only，
        # 沿用 rtm_sink 先例）+ rtm_feedback 於 wiring 注入（core-purity 唯一豁免點）。
        # propose 預設 ON（cfg flag，env AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE opt-out）；
        # 非 SDD playbook / flag OFF → plugin 內短路 no-op（零退化）。apply 仍 🔴 人工。
        "translation_learner": TranslationLearnerPlugin(
            sink=_build_translation_learning_sink(cfg),
            rtm_feedback=_build_rtm_feedback_source(cfg),
            observability=observability,
            enabled=cfg.playbook.enable_translation_auto_propose,
            max_proposals_per_run=cfg.playbook.translation_max_proposals_per_run,
            # improving_61：第二信號 weak_regex 提議門檻（與失敗信號獨立）。
            min_weak_runs=cfg.playbook.translation_min_weak_runs,
        ),
        "goto_counter": GotoCounterPlugin(playbook_cfg=cfg.playbook),
        # W4-T17 / M-11：CheckpointPlugin 解耦；attach_bus 由 _register_in_order 處理
        "checkpoint": CheckpointPlugin(checkpoint_manager=checkpoint_mgr),
        # mutation_service 非 Plugin，不會被 register；供 PlaybookKernel 注入
        "mutation_service": MutationApplyService(),
    }
    if hotkey is not None:
        plugins["hotkey"] = HotkeyPlugin(hotkey_handler=hotkey)

    return plugins


def _build_sdd_governance(
    brain: IBrain | None, observability: IObservabilityPort | None,
) -> SddGovernancePlugin:
    """組裝 SddGovernancePlugin + SddToPlaybookAdapter（ISpecSource 實作）。

    延遲 import infra adapter（wiring 為 core-purity 唯一豁免點，與
    build_kernel 內 LocalLogger 既有先例同模式）。
    """
    from ..infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter  # noqa: PLC0415
    from ..infra.adapters.sdd_topology_dashboard_adapter import (  # noqa: PLC0415
        SddTopologyDashboardAdapter,
    )
    return SddGovernancePlugin(
        brain=brain,
        observability=observability,
        spec_source=SddToPlaybookAdapter(observability=observability),
        # AutoSDD_improving_14 A 軌（W-14-2）：注入拓樸儀表板來源（read-only 消費 SDD 渲染產物）。
        topology_dashboard_source=SddTopologyDashboardAdapter(observability=observability),
    )


def _build_rtm_writeback(
    cfg: AppConfig, observability: IObservabilityPort | None,
) -> RtmWritebackPlugin:
    """組裝 RtmWritebackPlugin + PlaybookToRtmAdapter + FileRtmSink（AutoSDD_improving_24 W-24-2）。

    延遲 import infra adapter（wiring 為 core-purity 唯一豁免點）。報告寫到
    run 工作區 build/reports/rtm/（base_dir=checkpoint_dir/rtm）；非 SDD playbook
    時 plugin 於 POST_RUN 自行 no-op，sink 不會被觸碰。
    """
    from ..infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter  # noqa: PLC0415
    from ..infra.adapters.rtm_file_sink import FileRtmSink  # noqa: PLC0415

    return RtmWritebackPlugin(
        adapter=PlaybookToRtmAdapter(observability=observability),
        sink=FileRtmSink(f"{cfg.checkpoint_dir}/rtm", observability=observability),
    )


def _build_rtm_feedback_source(cfg: AppConfig):
    """組裝 FileRtmFeedbackSource（AutoSDD_improving_27 W1）。

    base_dir 與 _build_rtm_writeback 的 FileRtmSink 對稱（checkpoint_dir/rtm），
    讀回 sink 寫出的 RTM-COVERAGE-*.yaml / HISTORY.jsonl。延遲 import infra
    （wiring core-purity 唯一豁免點）。建構零副作用（僅持 base_dir，不建目錄），
    故 flag OFF 時建了也不觸碰檔案系統。
    """
    from ..infra.adapters.rtm_file_feedback_source import (  # noqa: PLC0415
        FileRtmFeedbackSource,
    )
    return FileRtmFeedbackSource(f"{cfg.checkpoint_dir}/rtm")


def _build_translation_learning_sink(cfg: AppConfig):
    """組裝 FileTranslationLearningSink（AutoSDD_improving_60 W-60-2）。

    沿用 FileRtmFeedbackSource 先例（File-only，無 PG 後端）；延遲 import infra
    （wiring core-purity 唯一豁免點）。建構零副作用（僅持 base_dir，不建目錄），
    故 flag OFF 時建了也不觸碰檔案系統。
    """
    from ..infra.adapters.translation_learning_sink import (  # noqa: PLC0415
        FileTranslationLearningSink,
    )
    return FileTranslationLearningSink(f"{cfg.checkpoint_dir}/translation_learning")


def _register_in_order(bus: EventBus, plugins: dict[str, Any]) -> None:
    """按 _REGISTER_ORDER 註冊 Plugin 並對 CheckpointPlugin attach_bus。

    SD_Improving_05 W0 T0-2：SSOT 抽出，兩條組裝路徑共用此註冊邏輯。

    W4 三方審查 Arch-W4-Maj-2：CheckpointPlugin 的 attach_bus 緊跟 register 後立即
    執行，避免未來新增 PRE_RUN dispatch hook 時的順序依賴。
    """
    for name in _REGISTER_ORDER:
        plugin = plugins.get(name)
        if plugin is None:
            continue
        bus.register(plugin)
        if isinstance(plugin, CheckpointPlugin) and hasattr(plugin, "attach_bus"):
            plugin.attach_bus(bus)


def wire_plugins_with_registry(
    bus: EventBus,
    *,
    config: AppConfig,
    minimax_client: Any | None = None,
    hotkey: Any | None = None,
    state_repository: Any | None = None,
    observability: IObservabilityPort | None = None,
    brain: IBrain | None = None,
) -> dict[str, Any]:
    """組裝 Plugin 並回傳 dict（供測試斷言 plugin state）。

    SD_Improving_05 W0 T0-2：改呼叫 _build_plugin_set + _register_in_order，
    與 build_kernel 共用唯一 SSOT 來源。

    SD_Improving_05 W0 三方審查 Arch-M3 / SD-M7：補 state_repository 參數，
    與 build_kernel 對稱，消除「test 路徑 CheckpointManager 永遠 repository=None」
    的隱性不等價問題。

    SD_09 Pre-W0 audit P0-03：補 observability 參數與 build_kernel 對稱；
    未注入時 KnowledgeBasePlugin 仍 fallback 記憶體累計（不破壞測試）。
    """
    plugins = _build_plugin_set(
        config,
        minimax_client=minimax_client,
        hotkey=hotkey,
        state_repository=state_repository,
        observability=observability,
        brain=brain,
    )
    _register_in_order(bus, plugins)
    return plugins


def build_kernel(
    cfg: AppConfig,
    *,
    executor: IExecutor,
    evaluator: IEvaluator,
    brain: IBrain | None = None,
    hotkey: Any | None = None,
    minimax_client: Any | None = None,
    state_repository: Any | None = None,
    observability: IObservabilityPort | None = None,
) -> PlaybookKernel:
    # 組裝完整的 PlaybookKernel。（R86 等量減法：docstring → 註解，一字未刪；理由見檔頭。）
    #
    # 註冊所有 15 個 Plugin 並注入相應依賴。Plugin 的 priority 由各 Plugin 類別
    # 本身的 ``PRIORITY`` 常數決定（W4-T15 m-6），EventBus 在 register 時透過
    # ``hook.priority()`` 自動排序，此處不再硬編碼數值。
    #
    # SD_Improving_05 W0 T0-2：改呼叫 _build_plugin_set + _register_in_order，
    # 與 wire_plugins_with_registry 共用唯一 SSOT 來源，杜絕 M-3 漂移。
    #
    # PRIORITY 對照表（來源：各 plugins/*.py 內 `PRIORITY` 常數，僅供讀者參考）：
    #   5  PreRunValidatorPlugin
    #   10 HotkeyPlugin
    #   15 CrossStepValidatorPlugin
    #   30 TokenGuardPlugin
    #   35 GlobalGoalAnchorPlugin
    #   40 PlaybookPersistencePlugin（SD_05 W4-3）
    #   45 SddGovernancePlugin（AutoSDD W6）
    #   50 FastPathPlugin / NotificationPlugin / KnowledgeBasePlugin / GoalSynthesisPlugin
    #      （SD_05 W4-2：FastPathPlugin tie-breaker register 在 notification 前）
    #   65 ConvergencePlugin
    #   70 EvolutionPlugin
    #   85 GotoCounterPlugin
    #   90 CheckpointPlugin
    # SD_08 W4 / ADR-SD08-004 §2.1：build_kernel 預設注入 LocalLogger
    # （唯一 W4 Adapter；caller 可顯式傳 observability 覆寫，例如 NullObservability for tests）
    if observability is None:
        from ..infra.adapters.observability import LocalLogger  # noqa: PLC0415
        observability = LocalLogger()

    bus = EventBus()
    plugins = _build_plugin_set(
        cfg,
        minimax_client=minimax_client,
        hotkey=hotkey,
        state_repository=state_repository,
        observability=observability,
        brain=brain,
    )
    _register_in_order(bus, plugins)

    return PlaybookKernel(
        executor=executor,
        evaluator=evaluator,
        bus=bus,
        brain=brain,
        mutation_service=plugins["mutation_service"],
        observability=observability,
    )


def build_goal_decomposer(
    cfg: AppConfig,
    *,
    brain: IBrain,
    observability: IObservabilityPort | None = None,
) -> Any:
    """組裝 GoalDecomposer（F-A1 / ADR-AGT-002）並注入 F-A2 ToolInvocationAdapter。

    Improving_012 Phase 3：F-A2 adapter 先前無消費者（避免 dead code），於此處
    經 wiring 注入 GoalDecomposer——拆解出之步驟若需工具，經 allowlist 安全閘查可用性。
    wiring 為 core-purity contract（#2）唯一豁免點，import infra adapter / execution 合法。

    安全閘以 config.tool_invocation 驅動（預設 enabled=False 全 deny，flag-off 零行為變更）。
    """
    from ..execution.goal_decomposer import GoalDecomposer  # noqa: PLC0415
    from ..infra.adapters.goal_freeze_gate import (  # noqa: PLC0415
        BoundedGoalFreezeGate,
    )
    from ..infra.adapters.tool_invocation_adapter import (  # noqa: PLC0415
        ToolInvocationAdapter,
    )
    # 🔴 R84（W9 交棒）：`notification_enabled` 必須在這裡注入——adapter 的 send_message 走
    # `utils.notifier.notify`，而它的 `enabled` 預設 True ⇒ 不注入就等於這條路徑無視
    # `config.notification.enabled`（兩個開關各說各話）。回歸鎖：
    # `tests/test_tool_invocation.py::test_send_message_respects_notification_enabled_from_wiring`
    tool = ToolInvocationAdapter(
        enabled=cfg.tool_invocation.enabled,
        allowlist=list(cfg.tool_invocation.allowlist),
        observability=observability,
        notification_enabled=cfg.notification.enabled,
    )
    # improving_57 A 軌 L4：有界自動凍結 signoff 閘（fail-closed 回退人工）
    freeze_gate = BoundedGoalFreezeGate()
    return GoalDecomposer(
        brain, observability=observability, tool_invocation=tool,
        freeze_gate=freeze_gate,
    )
