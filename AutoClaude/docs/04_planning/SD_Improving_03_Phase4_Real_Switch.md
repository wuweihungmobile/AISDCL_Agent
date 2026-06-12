# SD_Improving_03：Phase 4 Facade 真正切換 + DAL 接通生產路徑

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.1**（依 Architect / QA / PM 三方審查 findings 修訂） |
| 建立日期 | 2026-05-08 |
| v1.1 修訂日期 | 2026-05-08 |
| v1.1 覆審日期 | 2026-05-12 |
| 文件類型 | 系統設計（System Design）— 下一階段 Sprint 提案 |
| 對應目錄 | `docs/04_planning/` |
| 前置文件 | [SD_Improving_01.md](SD_Improving_01.md) v1.1、[SD_Improving_02.md](SD_Improving_02.md) v1.2（必讀） |
| 觸發來源 | Phase 0~6 重構稽核 findings F1/F2/F3/M1/M2/M4/M6（2026-05-08） |
| 文件狀態 | **Implemented v1.1**（Sprint CLOSED 2026-05-12；G3 ✅ + G5 ✅ 全部簽核） |
| 維護者 | Chief Architect / Lead QA / PM |
| Sprint Owner | wuweihungmobile（CLOSED 2026-05-12） |
| FTE 假設 | 1.5（單人 + pair review）；總工時估計 **27~36 PD / 5 週** |

---

## v1.1 修訂摘要（v1.0 → v1.1）

依三方審查 finding 修訂以下範圍：

| 範圍 | v1.0 問題 | v1.1 修訂 |
|------|-----------|-----------|
| §0 | 缺 Alternative Considered（PM C5） | 補 §0.1 列 3 個替代方案與 trade-off |
| §2.1 main.py | 缺 try/except MinimaxError（Architect 16） | 補完 error handling |
| §2.2 facade | 雙 Kernel fallback 風險（Architect C1）；9 項 shim 未列名（Architect M6） | 改為 strict-injection + DeprecationWarning；補完整 9 項 shim 對照表 |
| §2.3 | 「剩餘 1500 行」與「≤ 600 行」自相矛盾（Architect 13） | 統一為「≤ 600 行」 |
| §2.4 byte-level | 物理不可達（QA C1/C3、Architect C8） | **降級為 semantic-level + Stage A/B 兩階段 baseline** |
| §2.5 / §3.3 | 缺 Component / Sequence Diagram（Architect C9） | 新增 |
| §3.1 F2 範例 | API 違反 SD_02 §1.2.1 leaky abstraction（Architect C2）；遺漏 3 個 API（QA C2） | 補 stem 轉換 + 完整 API 委派 + W1 拆 W1a/W1b |
| §3.2 wiring | CheckpointPlugin/KnowledgeBasePlugin 仍走具體類別（Architect M10） | 改注入 IStateRepository / IMemoryStore Port |
| §4.1 排程 | 4 週、W4 五件事 cascade fail（三方一致） | **延長至 5 週**；W4 拆分；補 Owner/FTE/PD 欄；每週末硬阻擋 |
| §4.3 風險矩陣 | 漏列 4 高機率風險、未承接 R-1~R-12 編號（三方一致） | 補 R-13~R-16 + 治理風險 + 對應 R-ID 欄 + 回滾策略 |
| §4.4 中段檢核 | 缺（PM C8） | 補 W2 末三人 review |
| §5 DoD | LOC 數字三處錯誤、缺 Stakeholder 簽核 / staging smoke / 文件 propagation / Sprint 復盤（QA C4 / PM C6） | 統一 7398；補 6 項 DoD；補 LOC delta 表 |
| §5 補測 | 9 項 shim 無自動化驗證（QA M1）；補測 10 項（QA Test Plan Gaps） | 新增 `tools/check_frozen_surface_shim.py` 規格 + 10 項補測清單 |
| §6 | 漏引 risk_log.md / gate_audit.md / Phase6_P1_Backlog（PM C9 / Architect 11） | 補完整交叉引用 |

---

## 0.2 三方覆審 v1.1 結果（2026-05-12）

| 角色 | 結論 | 主要條件（不阻擋 W0 KickOff） |
|------|------|-------------------------------|
| **Architect** | APPROVE WITH CONDITIONS | `AutoResumeService` 介面需在 W0c 前補正式規格（§2.3 Component Diagram 已足夠骨架） |
| **QA** | APPROVE WITH CONDITIONS | §5.2 item 10 `test_cli_compatibility_v2.py` 需在 W0 DoD 前釐清「mock executor vs real Claude Code」——確認後更新 DoD |
| **PM** | APPROVE WITH CONDITIONS | Q-1 Tech Lead 必須在 W0 KickOff **前 1 週**指派；FTE 1.5 需 HR / 主管確認（見 §0.3） |
| **綜合 Verdict** | **APPROVE — 無 Critical findings，不升 v1.2** | W0 KickOff §0.3 三項指派為 sprint 啟動前置條件 |

---

## 0.3 W0 KickOff 指派清單

W0 KickOff 前必須完成下列三項指派，否則 sprint 不得啟動（R-G3 / R-G4 觸發）：

| # | 指派項 | 對應問題 | 指派人 | 確認日期 |
|---|--------|----------|--------|----------|
| 1 | **Tech Lead**（Sprint Owner，W0~W5 總責）| Q-1 | wuweihungmobile | 2026-05-12 |
| 2 | **Pair Review Owner**（F1 主迴圈 W2/W3 雙人 commit）| R-G3 | wuweihungmobile | 2026-05-12 |
| 3 | **FTE 確認**（預設 1.5；單人 + pair review）| §4.1 FTE 欄 | wuweihungmobile | 2026-05-12 |

PM 在 W0 KickOff 會議上填入上表，並同步更新 §4.1 Owner / FTE 欄位與 §7 Q-1 狀態。

---

## 0. 為什麼需要 SD_Improving_03？

SD_Improving_02 規劃的 6 Phase 重構（W1~W15+）已完成「結構創建」面：
- ✅ Kernel + EventBus + 12 Plugin 已建構
- ✅ Port 介面 + File / InMemory / PG 三後端 DAL 已建構
- ✅ Phase 6 PG 三段開關（yaml_only / both / db_only）已建構並四方簽核
- ✅ 944 passed / 11 skipped 測試全綠
- ✅ 行數預算 violations=0（baseline=7398, total=8148, cap=8877）

但 Phase 0~6 稽核（[gate_audit.md](../05_development/gate_audit.md) §1 G3）發現：

> **`autoclaude/main.py` 從未呼叫 `build_kernel(cfg)` / `build_state_repository(cfg, storage)`，所有新 Kernel + 12 Plugin + DAL backend 是並行死碼。 944 tests 通過僅代表「舊 PlaybookRunner 沒被破壞 + 新元件有獨立測試覆蓋」，並非「舊邏輯已成功被新邏輯等價替換」。**

本 SD 是 **Phase 4 Facade 真正切換 + DAL 接通生產** 的工程提案，目標是讓 Strangler Fig 重構真正完成。

### 0.1 Alternatives Considered（v1.1 新增，回應 PM C5）

提出本 SD 前，已評估三個替代方案：

| 方案 | 描述 | Trade-off | 結論 |
|------|------|-----------|------|
| **A. SD_02 v1.2 內補修** | 直接修訂 SD_02 v1.1，把 Phase 4 範圍改為「真正切換」 | ✗ scope 過大易混淆 Phase 4 / 5 / 6 邊界<br>✗ 既有 commit `4441a7a` / `539fa34` 已聲稱「6 Phase 完成」，文件回溯成本高 | **不採用** |
| **B. dual-write feature flag 漸進切換** | main.py 透過 env `AUTOCLAUDE_USE_KERNEL=1` 灰度切換新舊路徑；新舊並存執行對照 | ✓ 風險最低<br>✗ 雙路徑長期並存維運成本高<br>✗ byte-level / semantic-level 對照仍需做（未省驗證工） | 部分採用：W2~W4 期間以 feature flag 同行；W5 G3 簽核後預設新路徑 |
| **C. 本 SD（一次切換 + 5 週 sprint）** | 明確 4 個 Gate 阻擋（W1/W2/W3/W4 末），完成後刪舊路徑 | ✓ scope 清楚、單一文件涵蓋<br>✓ 與 G3 強制簽核機制對齊<br>⚠️ 需嚴格每週末阻擋避免 cascade fail | **採用** |

選 C 並融合 B 的 feature flag 機制：W1~W4 並存、W5 切換預設、W5+1 刪舊路徑。

---

## 1. 範圍：稽核 findings 對應

### 1.1 嚴重項（必修）

| Finding | 標題 | PD 估計（FTE 1.5） | 對應 R-ID |
|---------|------|---------------------|-----------|
| **F1** | Runner 真正委派 Kernel；`main.py` 引入 `build_kernel`，重寫 `_runner_impl.run()` 主迴圈 | 🔴 8~12 PD | R-1, R-9, R-13 |
| **F2** | `CheckpointManager` 反向委派；`FailureKnowledgeBase` 同 | 🟡 3~5 PD | R-9, R-16 |
| **F3** | `main.py` 注入 `build_state_repository(...)`；Runner 接受 `state_repository` DI 並讓 9 處 `self._checkpoint_mgr.*` 改走 Port | 🟡 2~3 PD（與 F1 同期） | R-14 |

### 1.2 中度項（重要）

| Finding | 標題 | PD 估計 | 對應 R-ID |
|---------|------|---------|-----------|
| **M1** | 9 項 Frozen Surface 真正轉為純委派 shim（`def _evaluate(self, ...): return self._kernel.evaluator.evaluate(...)`） | 1~2 PD（依賴 F1） | R-4 |
| **M2** | Kernel `__init__` 加入 `mutation_service` 參數；wiring 注入 `MutationApplyService`；`EvolutionPlugin` 透過 ctx 取得 | 1 PD | R-3 |
| **M4** | `PgStateRepository.save_checkpoint` 首次呼叫時 INSERT `playbook_runs`；schema FK 不再 nullable；新 alembic migration | 2~3 PD（依賴 F3 + DBA 預審） | R-15 |
| **M6** | F1 完成後刪 `_runner_impl.py` 大半業務邏輯（剩 ≤ 600 行純 dataclass + shim），下調 `.loc_baseline` | 1 PD（依賴 F1） | — |

### 1.3 不在本 SD 範圍

- **M3**（Phase 6 P1 backlog）：已於 [Phase6_P1_Backlog.md](../05_development/Phase6_P1_Backlog.md) 列管
- **M5**（import-linter）：已於 Pass 1 配置就緒
- **M7**（PG asyncio 限制）：已於 `pg_state_repository.py` docstring 註明
- **L1~L5**：Pass 1 已處理或已併入 backlog
- **Phase 6 P1 #1~#5**（docker-compose / CI PG service / startup smoke / retry / metrics）：阻擋 production `db_only`，但**本 SD 不順帶完成**。理由：M4（PG 寫入路徑）完成後 PG 仍處「dual-write 影子」狀態，production `db_only` 需 P1 #1~#5 全綠才能切換。本 sprint 聚焦 Kernel 接通；P1 由獨立 sprint 處理（PM C9 / PM 7 取捨論證）。

---

## 2. F1 詳細工程計畫

### 2.1 切換後的 main.py（目標）

```python
# autoclaude/main.py（重寫後 ~ 60 行）
from .core.wiring import build_kernel
from .core.services.auto_resume import AutoResumeService  # Layer 2 wrapper（v1.1 新增說明）
from .infra.repositories.factory import build_state_repository
from .infra.repositories.factory import build_memory_store          # F2 配套
from .infra.adapters import PtyExecutor, ShellEvaluator, MinimaxBrain
from .execution.playbook_runner import PlaybookRunner

def main() -> int:
    args = _parse_args()
    _validate_playbook_format(args.playbook)
    cfg = load_config(args.config)
    setup_logger(cfg.log_dir)
    logger = logging.getLogger("autoclaude")

    api_key = os.environ.get("MINIMAX_API_KEY") or cfg.minimax.api_key

    # v1.1 修正（Architect 16）：保留既有 try/except 結構
    try:
        minimax = MinimaxClient(
            api_key=api_key, base_url=cfg.minimax.base_url,
            model=cfg.minimax.model, timeout=cfg.minimax.timeout_seconds,
        )
    except MinimaxError as exc:
        logger.error("初始化失敗: %s", exc)
        return 1

    hotkey = HotkeyHandler()

    # Phase 4 真正切換：所有外部世界 adapter + DAL backend 在此注入
    state_repo = build_state_repository(cfg.checkpoint_dir, cfg.storage)
    memory_store = build_memory_store(cfg.checkpoint_dir, cfg.storage)
    executor = PtyExecutor(cfg)
    evaluator = ShellEvaluator(cfg)
    brain = MinimaxBrain(minimax)

    kernel = build_kernel(
        cfg,
        executor=executor, evaluator=evaluator, brain=brain,
        hotkey=hotkey, minimax_client=minimax,
        state_repository=state_repo,        # Phase 6 三段開關真正啟用
        memory_store=memory_store,          # F2 配套
    )

    # AutoResumeService 屬 Layer 2，wrap kernel.run 提供外層 retry / auto_resume / evolution
    # 為什麼不放 Kernel 內部：保持 Kernel 純粹「單次 playbook 執行」，外層恢復迴圈為 Kernel 之上的協調層
    orchestrator = AutoResumeService(kernel, cfg)

    runner = PlaybookRunner(cfg, minimax, hotkey, kernel=orchestrator)  # facade strict-injection
    result = runner.run(args.playbook, fresh=args.fresh)
    logger.info("Playbook 結束 | %s", result)
    return 0 if result.success else 1
```

### 2.2 PlaybookRunner facade strict-injection（v1.1 修正：Architect C1 雙 Kernel 風險）

```python
# autoclaude/execution/playbook_runner.py（瘦身後 < 150 行）
import warnings
from typing import Optional
from ..core.services.auto_resume import AutoResumeService

class PlaybookRunner:
    """Frozen Surface facade（193 處 mock.patch 維持向後相容）。

    v1.1 修正：strict-injection — 不再 fallback 自建 Kernel，避免雙 Kernel 副作用。
    """

    def __init__(
        self, config, minimax_client, hotkey_handler,
        *,
        kernel: Optional[AutoResumeService] = None,  # v1.1：Optional 但 fallback 走 deprecation
        ...,
    ):
        if kernel is None:
            warnings.warn(
                "PlaybookRunner without injected kernel is deprecated; v2.0 will require kernel=. "
                "fallback path 僅供 193 處 mock.patch 測試耦合。",
                DeprecationWarning, stacklevel=2,
            )
            kernel = self._build_default_orchestrator(config, minimax_client, hotkey_handler)
        self._kernel = kernel    # 唯一 Kernel 來源；不再有 fallback 內部建構

    def run(self, playbook_path, fresh=False) -> "PlaybookResult":
        playbook = self._load_playbook(playbook_path)
        kernel_result = self._kernel.run(playbook, fresh=fresh)
        return self._adapt_result(kernel_result)  # KernelResult → PlaybookResult（含 5 缺欄補完，見 §2.6）
```

#### Frozen Surface 9 項對照表（v1.1 補完，Architect M6）

對照 SD_01 v1.1 §3.10 / SD_02 v1.1 §2.6 line 826：

| # | shim method / attribute | 對應 Kernel 內部目標 | mock.patch 引用次數估 | 預計行數 |
|---|--------------------------|----------------------|------------------------|----------|
| 1 | `_evaluate(task, output)` | `self._kernel.evaluator.evaluate(task, output)` | ~30 | 1 |
| 2 | `_apply_single_mutation(m, **kw)` | `self._kernel.mutation_service.apply(m, **kw)` | ~15 | 1 |
| 3 | `_validate_batch_compatibility(ms)` | `self._kernel.mutation_service.validate_batch(ms)` | ~5 | 1 |
| 4 | `_consecutive_compact_failures` | `self._kernel.token_guard.consecutive_compact_failures` | ~8 | 1 |
| 5 | `_step_counter` | `self._kernel.state.step_counter` | ~12 | 1 |
| 6 | `_evolver` | `self._kernel.evolution.rule_evolver` | ~6 | 1 |
| 7 | `_minimax_evolver` | `self._kernel.evolution.minimax_evolver` | ~6 | 1 |
| 8 | `_escalation_history` | `self._kernel.escalation.history` | ~3 | 1 |
| 9 | `_knowledge_base` | `self._kernel.knowledge_base.store` | ~10 | 1 |

合計 ~95 處 mock.patch 直接耦合（剩餘 ~98 處走 `self._cfg` / `self._minimax` / `self._hotkey` 等構造參數），總計約 193 處（與 SD_02 §2.6 紀錄一致）。

### 2.3 主迴圈搬移範圍（`_runner_impl.run()` → Kernel/Plugin/Service）

| 範圍 | 原位置 | 新位置 | 規模 | Plugin emit 順序對齊（Architect 8） |
|------|--------|--------|------|----------------------------------------|
| 外層自動恢復迴圈（`while True` + auto_resume） | `_runner_impl.py:136~250` | **`AutoResumeService`（Layer 2 wrapper，新檔）** | ~120 行 | n/a（Kernel 之上） |
| Token HALT 偵測與 checkpoint 排程 | `_runner_impl.py:1240~1340` | `TokenGuardPlugin.on_post_attempt`（priority=30） | ~100 行 | 必須在 KnowledgeBasePlugin (priority=50) 之前 emit |
| 演化重啟與 evolution_count 管理 | `_runner_impl.py:1180~1230` | `EvolutionPlugin.on_post_attempt`（priority=70） | ~50 行 | 在 ConvergencePlugin (65) 之後 |
| Mutation 套用 | `_runner_impl.py:1883~2191` | `Kernel._apply_mutation` 委派 `MutationApplyService` | ~310 行（**重新呼叫既有 service，淨增量 ~30 行**） | n/a |
| Checkpoint load / save / clear | 9 處 `self._checkpoint_mgr.*` | `CheckpointPlugin`（priority=90）+ `IStateRepository` | ~30 行 | 必須在所有業務 Plugin emit 之後 |
| Plugin emit 順序契約 | hardcoded inline 順序 | `wiring.py` priority + 文件化 emit ordering 約束 | n/a | 補測 `test_plugin_emit_order.py` 驗證 |

**總搬移規模約 600~700 行**；剩餘 `_runner_impl.py` **依 §5 DoD 必須瘦身至 ≤ 600 行**（v1.1 修正：v1.0「剩餘 1500 行」描述自相矛盾）；剩餘僅保留 dataclass、9 項 shim、helper（如 `_load_playbook`）。

#### HookContext payload 契約（v1.1 補，回應 QA M5）

`TokenGuardPlugin.on_post_attempt` 收到的 `ctx.payload` 必須含：

```python
{
    "tracker": FailureTracker,
    "attempt": int,
    "goto_counter": dict,
    "inject_before_counter": dict,
    "skip_to_counter": dict,
    "completed_step_ids": set[str],
    "step_evolution_counter": dict,
}
```

對應補測項：`tests/integration/test_token_halt_payload_contract.py`。

### 2.4 Equivalence 驗證計畫（v1.1 重大修正：QA C1/C3/M3）

#### v1.0 → v1.1 修訂理由

QA 證實 byte-level snapshot 一致**物理上不可達**：
- `_runner_impl.py:586` 用 `f"[{task.step_id}] {task.name} ✓ (attempt {attempt + 1})"`
- `kernel.py:159` 用 `f"[OK] {task.step_id} (attempt={attempt})"` — **string format 從根本不同**
- snapshot baseline 由 dry_run 模式產生（`_StepOutput(text=f"[dry-run] {keyword}")`），Kernel 路徑無同等短路
- `KernelResult` 缺 5 個欄位（`workflow / halt_for_token / scheduled_resume_at / evolved_playbook_path / evolution_fresh_required`）— 見 §2.6

#### 兩階段 baseline + semantic-level 比對

| Stage | 範圍 | 自動化 | 嚴格度 |
|-------|------|--------|--------|
| **Stage A（CI 強制）** | fake executor + 真 Kernel snapshot；新建 `tests/equivalence/snapshots_kernel/`（與 dry_run snapshot 並存） | ✅ CI 每 PR | **semantic-level**：`completed_steps / completed_step_ids / 各 counter / failure_history / halt_for_token / evolved_playbook_path` 完全一致；`step_log` 行數一致 + 每行可由共通 regex `^\[\w+\] [\w_-]+.*attempt[ =]\d+` 解析、step_id 集合相同 |
| **Stage B（manual smoke）** | 真實 Claude Code 跑 `scripts/example_playbook.yaml`；記錄至 `docs/05_development/G3_smoke_log.md` | ✗ manual（W4 驗收會議） | PM 簽核 G3 須附此檔；step_log + counter 對照舊路徑語意一致 |

#### Snapshot 重新生成決策權（v1.1 補，回應 QA Minor 12）

繼承 SD_02 §7「Equivalence test snapshot 不允許因『行為改進』而修改——除非經過 PM 與 Architect 雙簽」。本 SD 補：

> Stage A snapshot 重新生成需 **PM + Architect 雙簽 commit message**（格式：`Approved-By: PM <name>`、`Approved-By: Architect <name>` trailer）；commit 須附差異說明文件 `docs/05_development/snapshot_regen_W{N}.md`。

#### Prerequisites（v1.1 新增，QA C1 建議的 W0a/W0b/W0c）

W1 啟動前**必須**完成下列 prerequisite，否則整個 Equivalence 計畫不成立：

| W0 prereq | 內容 | DoD | PD |
|-----------|------|-----|----|
| **W0a** | 對齊 Kernel 與 _runner_impl 的 `step_log` 字串格式（修改 `kernel.py:159 / 193`），重新生成 baseline | 文字格式統一；既有 13 fixture 全綠 | 1 PD |
| **W0b** | 擴充 `KernelResult` 加入缺漏 5 個欄位（v1.1 §2.6 mapping table） | 補測 `test_result_mapping.py` 5 欄位 round-trip 全綠 | 1 PD |
| **W0c** | 為 Kernel 路徑加 `dry_run=True` 短路，或重新以「真實 Kernel + fake executor」生成新 baseline 並覆蓋 13 份 snapshot 至 `snapshots_kernel/` | 13 fixture 在 Kernel 路徑下全綠 | 2 PD |

### 2.5 Component Diagram（v1.1 新增，Architect C9）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Layer 0: External World                                                  │
│   wexpect/subprocess │ Minimax HTTP API │ PostgreSQL │ filesystem         │
└──────────┬─────────────────┬──────────────────┬──────────────┬───────────┘
           │                 │                  │              │
┌──────────▼─────────────────▼──────────────────▼──────────────▼───────────┐
│ Layer 1: Adapters (autoclaude/infra/adapters/)                           │
│   PtyExecutor  │  MinimaxBrain  │  PgStateRepository  │  FileStateRepo   │
│   (IExecutor)  │  (IBrain)      │  (IStateRepository) │  (IStateRepo)    │
└──────────┬─────────────────┬──────────────────┬──────────────────────────┘
           │                 │                  │
┌──────────▼─────────────────▼──────────────────▼──────────────────────────┐
│ Layer 2: Core Services + Ports (autoclaude/core/)                        │
│   AutoResumeService (NEW v1.1) ─wraps→ PlaybookKernel                    │
│   PlaybookKernel ─uses→ MutationApplyService ─dispatches→ 7 strategies   │
│   IExecutor / IBrain / IStateRepository / IMemoryStore (Ports)           │
└──────────┬───────────────────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────────────────┐
│ Layer 3: Plugins (autoclaude/plugins/) — 12 plugins                      │
│   priority 5: PreRunValidator   priority 30: TokenGuard                  │
│   priority 50: KnowledgeBase / Notification / GoalSynthesis              │
│   priority 65: Convergence      priority 70: Evolution                   │
│   priority 85: GotoCounter      priority 90: Checkpoint                  │
└──────────┬───────────────────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────────────────┐
│ Layer 4: Facade (autoclaude/execution/playbook_runner.py)                │
│   PlaybookRunner — strict-injection facade（193 處 mock.patch 相容）      │
└──────────┬───────────────────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────────────────┐
│ Layer 5: CLI Entry (autoclaude/main.py)                                  │
│   build_state_repository → build_kernel → AutoResumeService → Runner     │
└──────────────────────────────────────────────────────────────────────────┘

相依方向：上層僅相依下層；同層之間嚴禁互引用（import-linter 強制）。
```

### 2.6 KernelResult ↔ PlaybookResult 欄位映射表（v1.1 新增，QA M7）

| PlaybookResult 欄位 | KernelResult v1.0 | v1.1 修正 | 來源 |
|---------------------|---------------------|-----------|------|
| `success` | ✅ 已有 | — | KernelResult.success |
| `completed_steps` | ✅ 已有 | — | KernelResult.completed_steps |
| `total_steps` | ✅ 已有 | — | KernelResult.total_steps |
| `reason` | ✅ 已有 | — | KernelResult.reason |
| `step_log` | ✅ 已有 | — | KernelResult.step_log |
| `completed_step_ids` | ✅ 已有 | — | KernelResult.completed_step_ids |
| `workflow` | ❌ 缺 | **W0b 補入 KernelResult.workflow** | WorkflowDetector 偵測結果 |
| `halt_for_token` | ❌ 缺 | **W0b 補入 KernelResult.halted（重命名統一）** | TokenGuardPlugin payload |
| `scheduled_resume_at` | ❌ 缺 | **W0b 補入 KernelResult.scheduled_resume_at** | TokenGuardPlugin emit 結果 |
| `evolved_playbook_path` | ❌ 缺 | **W0b 補入 KernelResult.evolved_playbook_path** | EvolutionPlugin emit 結果 |
| `evolution_fresh_required` | ❌ 缺 | **W0b 補入 KernelResult.evolution_fresh_required** | EvolutionPlugin emit 結果 |

PlaybookRunner facade `_adapt_result()` 為 1:1 trivial copy；不允許副通道從 plugin state 撈值。

---

## 3. F2 詳細工程計畫（v1.1 重大修正）

### 3.1 反向委派目標（v1.1 補完整 API + stem 轉換）

```python
# autoclaude/utils/checkpoint_manager.py（重寫後 ~ 60 行）
import os
import warnings
from pathlib import Path
from ..infra.repositories.file_state_repository import FileStateRepository

class CheckpointManager:
    """⚠️ Deprecated（v2.0 將移除）：請改用 FileStateRepository。

    v1.1 修正（Architect C2）：API 對 IStateRepository 必須做 path → playbook_id (stem) 轉換，
    避免違反 SD_02 §1.2.1 leaky abstraction 禁令。
    """
    def __init__(self, checkpoint_dir: str):
        if os.environ.get("AUTOCLAUDE_DEPRECATION_WARN") == "1":
            warnings.warn(
                "CheckpointManager is deprecated; use FileStateRepository directly.",
                DeprecationWarning, stacklevel=2,
            )
        self._dir = Path(checkpoint_dir)              # 對既有測試保留 _dir 屬性可見性
        self._repo = FileStateRepository(checkpoint_dir)

    @staticmethod
    def _to_id(playbook_path: str) -> str:
        """v1.1：path → playbook_id 轉換（避免 leaky abstraction）。"""
        return Path(playbook_path).stem

    # 既有完整 public API 對外契約不變（v1.1 補：QA C2 漏列 3 項）
    def save(self, cp, playbook_path):
        return self._repo.save_checkpoint(self._to_id(playbook_path), cp)
    def load(self, playbook_path):
        return self._repo.load_checkpoint(self._to_id(playbook_path))
    def clear(self, playbook_path):
        return self._repo.clear_checkpoint(self._to_id(playbook_path))
    def schedule_resume(self, cp, delay_min):
        return self._repo.schedule_resume(self._to_id(cp.playbook_path), delay_min)
    def checkpoint_path(self, playbook_path) -> Path:
        return self._dir / f"{self._to_id(playbook_path)}.checkpoint.json"
    def exists(self, playbook_path) -> bool:
        return self.checkpoint_path(playbook_path).exists()

    @staticmethod
    def seconds_until_resume(cp) -> int:
        return FileStateRepository.seconds_until_resume(cp)
```

`FailureKnowledgeBase` 同樣改寫委派至 `FileMemoryStore`（或 PG 對應 `PgMemoryStore`）。

### 3.2 wiring.py 對應修改（v1.1 新增，Architect M10）

```python
# autoclaude/core/wiring.py（v1.1 修正後 diff）
def build_kernel(
    cfg, *,
    executor, evaluator, brain=None, hotkey=None, minimax_client=None,
    state_repository: Optional[IStateRepository] = None,    # v1.1 新增
    memory_store: Optional[IMemoryStore] = None,            # v1.1 新增
):
    bus = EventBus()
    goto_counter = GotoCounterPlugin(playbook_cfg=cfg.playbook)

    # v1.1 修正：Plugin 收 Port 而非具體類別
    state_repo = state_repository or FileStateRepository(cfg.checkpoint_dir)  # default file
    mem_store = memory_store or FileMemoryStore(f"{cfg.checkpoint_dir}/failure_knowledge_base.jsonl")

    plugins = [
        ...
        KnowledgeBasePlugin(memory_store=mem_store),         # was: knowledge_base=FailureKnowledgeBase
        CheckpointPlugin(
            state_repository=state_repo,                      # was: checkpoint_manager=CheckpointManager
            goto_counter_plugin=goto_counter,
        ),
    ]
    ...
```

### 3.3 W1 拆 W1a / W1b（v1.1 修正：QA C2 / Architect C3）

| Sprint Slot | 範圍 | DoD |
|-------------|------|-----|
| **W1a（前 3 日）** | 把 `tests/equivalence/test_runner_snapshot.py:77`、`tests/equivalence/test_counter_persistence.py`、`tests/integration/test_kernel_facade.py` 等 24 個含 mock 的測試檔的 `runner._checkpoint_mgr` / `runner._knowledge_base` 改走 test helper（不依賴 internal alias）；補 `tests/equivalence/test_no_internal_alias.py` 嚴格阻擋未來再加 | 944 tests 全綠；新阻擋測試上線 |
| **W1b（後 2 日）** | `CheckpointManager` 反向委派；`__init__` 的 `DeprecationWarning` 預設關閉、由 env `AUTOCLAUDE_DEPRECATION_WARN=1` 啟用；CI 在 W4 才開 strict 模式 | 944 tests 維持綠；6 個既有 API（save/load/clear/schedule_resume/checkpoint_path/exists/seconds_until_resume）契約測試全綠 |

---

## 4. Sprint 排程與 Gate（v1.1 重大修正）

### 4.1 排程（v1.1 修正：4 → 5 週、補 Owner/FTE/PD、W4 拆分）

| 週 | 範圍 | Owner | FTE | PD | DoD（每週末硬阻擋） |
|----|------|-------|-----|-----|----------------------|
| **W0** | KickOff + W0a/W0b/W0c prerequisite（§2.4） | wuweihungmobile | 1.0 | 4 PD | (1) Kernel step_log 字串格式對齊 (2) KernelResult 補 5 欄位 (3) Kernel 路徑 dry_run 短路；13 fixture 在 `snapshots_kernel/` 全綠 |
| **W1** | F2 反向委派（W1a 測試解耦 + W1b 委派） | wuweihungmobile | 1.5 | 4~6 PD | 944 tests 全綠；6 個 CheckpointManager API 契約測全綠；`test_no_internal_alias.py` 阻擋上線 |
| **W2** | F1 主迴圈搬移 part 1：Token HALT + 演化重啟 → 對應 Plugin（含 HookContext payload 契約 §2.3）；M2 mutation_service 注入（前移自 W4） | wuweihungmobile | 1.5 | 6~8 PD | Stage A snapshot semantic-level 一致；補測 `test_token_halt_payload_contract.py` / `test_plugin_emit_order.py` 全綠 |
| **W3** | F1 主迴圈搬移 part 2：mutation 委派 service + auto_resume → AutoResumeService（Layer 2 wrapper） | wuweihungmobile | 1.5 | 5~7 PD | Stage A snapshot semantic-level 一致；補測 `test_dry_run_kernel_path.py` 全綠 |
| **W4** | F3（main.py 注入 build_state_repository / build_memory_store）+ M1（9 項 Frozen Surface shim 純委派）+ M6（_runner_impl.py 瘦身至 ≤ 600 行）+ G3 PM 強制簽核 | wuweihungmobile | 1.5 | 5~7 PD | (1) `tools/check_frozen_surface_shim.py` exit 0 (2) `_runner_impl.py` 行數 ≤ 600 (3) Stage A semantic-level 全綠 (4) 9 subprocess CLI 全綠 (5) Stage B manual smoke 完成 (6) `gate_audit.md` §1 G3 ✅ + git tag `gate/G3-passed` |
| **W5** | M4（PG playbook_runs INSERT + alembic migration + DBA 預審）+ feature flag 切換預設新路徑 + Sprint 復盤 | wuweihungmobile | 1.0 | 3~4 PD | (1) DBA 簽核 alembic migration (2) staging dual-write 24h drift counter=0 (3) `Sprint_Retrospective.md` 完成 (4) M4 不阻擋 G3 簽核（G3 在 W4 末已通過） |

**總計**：5 週 / 27~36 PD / FTE 1.5；對應 SD_02 §2.1 Phase 4 (W12 4~6 PD) 嚴重低估之修正。

### 4.2 Gate 簽核

#### G3（Phase 4 Facade 切換 — PM 強制簽核）

- **時點**：W4 末
- **簽核條件**（每項都必驗）：
  1. Stage A snapshot 在 13 fixture semantic-level 一致
  2. 9 subprocess CLI 全綠
  3. LOC budget violations=0（baseline 視 W4 末重新評估，見 §5）
  4. `tools/check_frozen_surface_shim.py` exit 0
  5. `_runner_impl.py` 行數 ≤ 600
  6. Architect / QA / PM **三方** ✅（v1.1：明確列入 DoD §5）
  7. Stage B manual smoke log（`G3_smoke_log.md`）由 PM 簽名
- **簽核時程上限**：W4 末 + 3 工作日內必簽 OR 必 revert（v1.1：PM C3 治理風險回應）
- 通過後在 git tag `gate/G3-passed`，更新 [gate_audit.md](../05_development/gate_audit.md) §1 G3 列

### 4.3 風險矩陣（v1.1 重寫：補 R-13~R-16 + 治理風險 + 對應 R-ID 欄）

| R-ID | 風險 | 嚴重度 | 機率 | 觸發條件 | 緩解策略 | 回滾 |
|------|------|--------|------|----------|----------|------|
| **R-1**（承自 risk_log） | byte-level Equivalence 跑不出（snapshot diff） | 🔴 高 | 🟡 中 | Stage A semantic-level 連續 2 工作天 fail | 降級 semantic-level；Plugin priority canonical sort；補 `test_plugin_emit_order.py` | revert 整週 commit；觸發 Tech Lead + PM 雙簽延期決策 |
| **R-9**（承自 risk_log） | 193 處 mock 耦合測試破 | 🔴 高 | 🟡 中 | 連續 2 工作天無法綠燈（SD_02 R-9 既定條件） | W1a 先解耦 internal alias；M1 9 項 shim 維持 noqa F401 等 | revert 該週；保留舊路徑 feature flag 一週 |
| **R-13**（v1.1 新增） | Plugin priority 排序破 byte-level snapshot | 🔴 高 | 🟢 高 | Stage A `step_log` 行排序與舊 _runner_impl inline 順序不一致 | 補 §2.3 emit ordering 契約 + `test_plugin_emit_order.py` | 該 Plugin priority 微調；snapshot regen（PM+Architect 雙簽） |
| **R-14**（v1.1 新增） | `storage.mode="both"` silent drop（F1 完成但 F3 未完成） | 🟡 中 | 🟢 高 | DualStateRepository 注入但 facade 仍走舊 `self._checkpoint_mgr` | F3 / F1 必須在同一 sprint；補 `test_dual_repository_smoke.py` 整合測試 | feature flag 強制走舊路徑 |
| **R-15**（v1.1 新增） | 跨 Plugin state 共享需求違反 SD_02 §5 | 🟡 中 | 🟡 中 | TokenGuardPlugin 與 EvolutionPlugin 需共享 `auto_resume_count / _evolution_count` | 透過 HookContext.payload 通訊（§2.3 契約）；嚴禁 plugin-to-plugin import | AutoResumeService 拉到 Layer 2 持有跨 Plugin state |
| **R-16**（v1.1 新增） | W1 反向委派失敗連鎖 | 🔴 高 | 🟡 中 | W1b 末 944 tests 紅 ≥ 50 個 | W1a 先解耦 + DeprecationWarning 預設關閉 | feature flag 走舊 CheckpointManager；W1 延一週 |
| **R-G1（治理）** | 時程延期：byte-level 連續 2 工作天 fail | 🟡 中 | 🟡 中 | Stage A 黃綠燈連續 2 天紅 | Tech Lead + PM 雙簽決定 delay / revert / 降級 | n/a |
| **R-G2（治理）** | 品質降級：byte-level 不可達需降為 semantic-level | 🟡 中 | 🟢 高 | W2 末 byte-level 仍不可達 | 已預先降級（§2.4 v1.1） | 重簽 G3 條件 |
| **R-G3（治理）** | 人力單點：bus factor=1 | 🟡 中 | 🟡 中 | Owner 請假 / 離職 | pair review F1 主迴圈；W2/W3 必雙人 commit | sprint 暫停一週 |
| **R-G4（治理）** | PM 簽核時程 | 🟡 中 | 🟡 中 | W4 末 + 3 工作日內未簽 | 升級至 Architect 拒絕 merge；revert | 整 sprint 標 incomplete |

### 4.4 中段檢核點（v1.1 新增，PM C8）

- **W2 末強制 30 分鐘三人 review**（Tech Lead + Architect + QA + PM）：
  - 若 Stage A semantic-level fixture pass 率 < 50% → 啟動延期決策
  - Pass 率 ≥ 50% 但 Plugin emit ordering 失敗 → 強制 W3 補 `test_plugin_emit_order.py` 修正前不繼續
- **每週末硬阻擋**：13 fixture semantic-level + 9 CLI subprocess + LOC budget violations=0 全綠才能 merge 到 main，否則 revert 該週所有 commit
- **QA Daily Smoke**（v1.1 新增，QA m2）：每日早會 QA 跑 944 tests / 13 fixture / 9 subprocess / counter_persistence；全綠才能進下一日，PM 在 `gate_audit.md` 留每日打卡紀錄

---

## 5. Acceptance Criteria（v1.1 重寫：QA C4 LOC 修正、補 6 項 DoD、補測 10 項）

當以下全部達成時，Phase 4 Facade 真正切換完成、Strangler Fig 重構達成 SD_Improving_02 原始承諾：

### 5.1 程式碼 DoD

- [ ] `autoclaude/main.py` 包含 `build_kernel()` 與 `build_state_repository()` + `build_memory_store()` 三個 DI 呼叫
- [ ] `autoclaude/execution/_runner_impl.py` 行數 ≤ **600**（從目前 2224 行下降至少 73%）
- [ ] 9 項 Frozen Surface shim **每支 ≤ 2 statements**（`tools/check_frozen_surface_shim.py` AST 驗證 exit 0）
- [ ] CheckpointManager / FailureKnowledgeBase 變成 deprecated alias，class body ≤ 60 行；6 個既有 API 契約測全綠
- [ ] PgStateRepository 首次寫入時 INSERT playbook_runs，schema FK 不再 nullable；alembic migration 經 DBA 簽核
- [ ] Kernel 持有 `mutation_service`，EvolutionPlugin 透過 ctx 取得（不直接 import）
- [ ] `KernelResult` 含 5 個新欄位（workflow / halted / scheduled_resume_at / evolved_playbook_path / evolution_fresh_required）；PlaybookResult adapter 1:1 trivial copy
- [ ] 設定 `storage.mode = "both"` 時，CheckpointPlugin 真實透過 DualStateRepository 雙寫（`test_dual_repository_smoke.py` 整合測試全綠）

### 5.2 測試 DoD

- [ ] `tests/equivalence/snapshots_kernel/` 13 fixture **semantic-level** snapshot 一致（非 dry_run baseline）
- [ ] `tests/cli/` 9 subprocess 場景全綠（含 exit code 0/1/2/3）
- [ ] 既有 944 tests 維持綠（**不可有任何 skip 增量**）
- [ ] 新增 10 個補測（v1.1 QA Test Plan Gaps）：
  1. `tests/equivalence/test_runner_snapshot_kernel.py`（Stage A baseline）
  2. `tests/equivalence/test_no_internal_alias.py`（W1a 阻擋未來耦合）
  3. `tools/check_frozen_surface_shim.py` + `tests/tools/test_shim_check.py`
  4. `tests/integration/test_dual_repository_smoke.py`
  5. `tests/integration/test_plugin_emit_order.py`
  6. `tests/integration/test_token_halt_payload_contract.py`
  7. `tests/integration/test_result_mapping.py`
  8. `tests/integration/test_dry_run_kernel_path.py`
  9. `tests/integration/test_evolved_playbook_deterministic_filename.py`
  10. `tests/cli/test_cli_compatibility_v2.py`（subprocess 跑 fixture 01 至成功）

### 5.3 LOC budget DoD（v1.1 修正：QA C4）

- [ ] `tools/check_loc_budget.py` exit 0
- [ ] `.loc_baseline` 在 W4 末視結果重新寫入：
  - 若 `_runner_impl.py` 真實削減至 ≤ 600 行 → baseline **下調至 6500~6800**（具體值依實際 commit 計算）
  - 否則維持目前值 7398
- [ ] LOC delta 表（v1.1 新增）：

| 檔案 | before | after（預估） | delta |
|------|--------|---------------|-------|
| `_runner_impl.py` | 2224 | ≤ 600 | -1624 |
| `playbook_runner.py` | 121 | ~150 | +29 |
| `core/services/auto_resume.py`（新） | 0 | ~120 | +120 |
| `core/kernel.py` | 203 | ~250 | +47 |
| `core/wiring.py` | 107 | ~120 | +13 |
| `core/services/mutation/service.py` | 67 | ~80 | +13 |
| `plugins/token_guard_plugin.py` | (現值) | +100 | +100 |
| `plugins/evolution_plugin.py` | (現值) | +50 | +50 |
| `plugins/checkpoint_plugin.py` | (現值) | +30 | +30 |
| `utils/checkpoint_manager.py` | 198 | ~60 | -138 |
| `main.py` | 87 | ~60 | -27 |
| 補測新增（10 檔） | 0 | ~600 | +600（不計入 prod baseline） |
| **prod 淨變動（v1.1 估）** | — | — | **-1387**（≈ 削減 19% 總 LOC） |

### 5.4 Stakeholder 簽核 DoD（v1.1 新增，PM C6）

- [ ] **Architect + QA + PM 三方** ✅（commit message 含 `Approved-By:` trailer 三筆）
- [ ] G3 PM 強制簽核通過，git tag `gate/G3-passed` 建立
- [ ] DBA 簽核 alembic migration（W5 / M4）
- [ ] Stage B manual smoke log 由 PM 簽名

### 5.5 文件 DoD（v1.1 新增，PM C6）

- [ ] [gate_audit.md](../05_development/gate_audit.md) §1 G3 狀態更新為 ✅ 已簽核 + commit hash
- [ ] [gate_audit.md](../05_development/gate_audit.md) §5 Commit 對應表新增 SD_03 sprint 完成行
- [ ] [risk_log.md](../05_development/risk_log.md) §1 R-1/R-4/R-9 緩解狀態更新；新增 R-13~R-16
- [ ] **CLAUDE.md** 「AutoClaude 專案架構」段落同步更新（補 AutoResumeService、KernelResult 欄位）
- [ ] **SD_Improving_02.md 升 v1.2**：§2.6 與 §4 加 banner「⚠️ Phase 4 實際完成由 SD_03 補完」
- [ ] **SD_Improving_01.md 同步 banner**：§3.10 / §3.4 註明 SD_03 補完
- [ ] **release notes / README**（如有）同步說明
- [x] 本 SD_03 文件狀態更新為 `Implemented`（2026-05-12）

### 5.6 Operations DoD（v1.1 新增，PM C6）

- [ ] **staging 環境跑 ≥ 24h** `storage.mode=both`，drift counter = 0（W5 末驗收）
- [ ] **Sprint 復盤文件** `docs/05_development/SD_03_Sprint_Retrospective.md` 完成

---

## 6. 與既有 SD 的關係（v1.1 補完整交叉引用）

- **SD_Improving_01.md v1.1**：原藍圖（10 層架構），本 SD 不修改架構，只完成原藍圖 §3.4 Layer 4 Kernel 真正接通生產
- **SD_Improving_02.md v1.1**：6 Phase 計畫，本 SD 是 Phase 4 的「真正執行」（原 Phase 4 實際只完成「Frozen Surface API 鎖定 + Runner 切兩檔」，未完成 Kernel 委派）
- **[gate_audit.md](../05_development/gate_audit.md)**：本 SD 完成後 §1 G3 狀態移轉至 ✅；§5 Commit 對應表 row「待 commit / SD_Improving_03 sprint 完成」更新為實際 commit hash
- **[risk_log.md](../05_development/risk_log.md)**：本 SD §4.3 風險矩陣承接 R-1 / R-4 / R-9 既定觸發條件，並新增 R-13~R-16 + R-G1~R-G4
- **[Phase6_PG_Stakeholder_Signoff.md](../08_deployment/Phase6_PG_Stakeholder_Signoff.md)**：本 SD 完成 F3 後，`storage.mode` 開關才從「設定可寫但無效」變為「實際可切換 backend」
- **[Phase6_P1_Backlog.md](../05_development/Phase6_P1_Backlog.md)**：本 SD 完成後仍**不**滿足 production `db_only` 切換條件（P1 #1~#5 未完成；見 §1.3 取捨論證）

---

## 7. 待解問題（v1.1 新增，對應 SD_02 §6 風格）

| Q-ID | 問題 | Owner | 決策時限 | 升級條件 |
|------|------|-------|----------|----------|
| Q-1 | Sprint Tech Lead 指派 | PM | **W0 KickOff 前 1 週**（由 §0.3 指派清單追蹤） | 無人選 → 整 sprint 順延 |
| Q-2 | `_runner_impl.py` 600 行硬上限是否包含 dataclass + shim？ | Architect | W0 末 | 預設「包含」，DoD 第 5.1.2 條成立 |
| Q-3 | byte-level 不可達後 snapshot regen 的雙簽流程 | PM + Architect | W2 末 | 雙簽流程 SOP 缺 → 升級至 SD_03 v1.2 |
| Q-4 | M4 staging dual-write 24h 是否能 CI 自動化 | Infra | W4 末 | 無自動化 → 留 manual smoke + Operations DoD |
| Q-5 | feature flag `AUTOCLAUDE_USE_KERNEL` 預設值切換時機 | Tech Lead + PM | W5 末 | 預設「W5 末切換新路徑」；異議升級至 G3 簽核會議 |

---

**文檔元數據**：
- 撰寫者：Phase 0~6 重構稽核（Pass 2b — SD 列管） + 三方審查 v1.1 修訂
- 三方審查紀錄：[SD_Improving_03_v1.0_Triple_Review.md](../05_development/SD_Improving_03_v1.0_Triple_Review.md)
- 三方覆審 v1.1：2026-05-12 APPROVE WITH CONDITIONS（§0.2）；無 Critical findings
- 對應稽核 findings：F1 / F2 / F3 / M1 / M2 / M4 / M6
- 對應風險：R-1 / R-4 / R-9（承接）+ R-13 / R-14 / R-15 / R-16 / R-G1~R-G4（v1.1 新增）
- 下次審查觸發：W0 KickOff 指派完成（§0.3）→ W2 中段檢核（§4.4）→ W4 G3 PM 強制簽核
