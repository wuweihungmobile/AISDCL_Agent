# SD_Improving_01：AutoClaude 微核心化重構藍圖（Part 1／2）

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.1 |
| 建立日期 | 2026-05-07 |
| 最後更新 | 2026-05-07（v1.1：依 Architect/QA/PM 三方審查補強 ISP、ResolutionPolicy、payload schema、契約測、Frozen Surface、行數預算、Gap 不退化清單、CLI 相容性承諾） |
| 文件類型 | 系統設計（System Design） |
| 對應目錄 | `docs/02_architecture/` 之先導規劃（待最終定稿後遷移為正式 SRD） |
| 適用 AISDLC 版本 | v0.09+ |
| 依賴前置 | Evo-006（Gap-039 ~ Gap-049 已完成）、558 tests passed |
| 後續延伸 | [SD_Improving_02.md](SD_Improving_02.md)（DAL 抽象 + TDD 重構步驟） |
| 文件狀態 | Draft v1.1（已併入三方必要修改，待複審） |
| 維護者 | Chief Architect / Lead QA / PM |

---

## 0. 文件導讀

本文是 **AutoClaude Level 5 微核心化（Microkernel Refactoring）** 的第 1 份藍圖，鎖定兩件事：

1. 把 `PlaybookRunner`（2246 行的上帝物件）的「現狀痛點」量化攤開，避免後續討論流於主觀。
2. 提出**目標架構**——以微核心（Pure DAG State Machine）+ 外掛（Plugin/Hook System）為主軸的重塑方案。

DAL（資料庫抽象層）規格與 TDD 重構步驟，請見 Part 2。

> **🔴 重點承諾**：本重構的成功與否，唯一判準是 **「558 個既有 tests 必須在重構期間每一個 commit 都保持 PASS」**。任何違背此承諾的設計變更，都應直接退回。

---

## 1. 雙人架構審查 CoT 對話

### 1.1 Chief Architect 的開場觀察

<thinking>
**Architect**：我先把 `playbook_runner.py` 的事實攤開來看。

- 全檔 **2246 行**，單一 class `PlaybookRunner` 持有 **31 個方法**。
- 核心方法 `_run_steps()` 從第 278 行延伸到第 1165 行，**單方法 ≈ 888 行**。這違反了 Clean Code 一切方法應 < 50 行、單一職責的原則，已不是「需要重構」，而是「結構性失能」。
- `__init__` 在 24 行內直接 `new` 出 12 個協作者：
  ```python
  self._evaluator = Evaluator(...)
  self._detector = WorkflowDetector()
  self._checkpoint_mgr = CheckpointManager(...)
  self._error_classifier = ErrorClassifier()
  self._token_logger = TokenUsageLogger(...)
  self._token_patterns = build_patterns(...)
  self._knowledge_base = FailureKnowledgeBase(...)
  self._evolver = PlaybookEvolver()
  self._minimax_evolver = MinimaxEvolver()
  ...
  ```
  這是教科書級的 **新關鍵字耦合（new-keyword coupling）**。違反 DIP（依賴反轉），任何替換 KnowledgeBase 後端、Checkpoint 後端、Evolver 演算法的需求，都得改 `PlaybookRunner` 本身——而每改一次，2246 行的測試對齊風險就跑出來一次。
- `_run_steps` 內部混合了至少 **9 種橫切關注點**（cross-cutting concerns）：
  1. 主狀態機切換（INIT → EXECUTE → EVALUATE → CORRECTION → ESCALATION → DONE）
  2. Token Guard（compact / halt 門檻）
  3. Checkpoint 持久化（多達 3 個呼叫點：`_handle_token_halt`、`_save_interrupt_checkpoint`、`_save_evolution_resume_checkpoint`）
  4. Evolution（MinimaxEvolver + PlaybookEvolver + GOAL_SYNTHESIS 特殊分支）
  5. Step Mutation（7 種突變類型，含 batch 相容性檢查）
  6. Knowledge Base 寫入（`record_success` / `record_escalation` 散在 4 處）
  7. 桌面通知
  8. Hotkey 中斷檢查（`if self._hotkey.triggered:` 出現 3 次）
  9. 跨步驟污染偵測 / Pre-Run 驗證 / 跨 Session 計數器恢復

這個 class 的真正問題不是「太大」，而是**它要為太多方向的變化負責**——任何 Token Guard 演算法、任何 KB 後端、任何新的突變類型、任何新的中斷來源，都會逼這個 class 改一次。SRP（單一職責）已名存實亡。

我的判斷：要支撐後續的「資料庫接入」與「Plugin 化新功能」，必須做**結構級切除手術**。這不是 refactor 等級，是 **Architecture Surgery**。
</thinking>

### 1.2 Lead QA 的反擊與條件

<thinking>
**QA**：Architect，你描述的是事實沒錯，但你忽略了**測試耦合的反作用力**。我以 `rg "runner\._" tests/ -c` 重新實測（v1.1 校正）：

- **`tests/` 中對 `runner._private_*` 的直接引用實測 193 處**（先前估算 249 處未排除註解／字串內偽匹配）。
- 高密度耦合熱點（依檔案實測排序）：
  - `test_playbook_runner.py`：49 處（直接 patch `runner._evolver`、`runner._minimax_evolver`、呼叫 `runner._evaluate`、`runner._get_correction`、`runner._apply_single_mutation`、`runner._validate_batch_compatibility`、`runner._send_compact`）
  - `test_gap039_049.py`：45 處
  - `test_gap009.py`：32 處
  - `test_gap013.py`：23 處
  - `test_gap014_020.py`、`test_gap012.py`、`test_token_checkpoint.py`：合計 ≈ 44 處
- `runner._consecutive_compact_failures = 1`（直接寫入私有狀態，`test_token_checkpoint.py:908`）
- `runner._cfg.token_guard.enabled = False`（直接改 config，`test_playbook_runner.py:1114`）
- `runner._send_compact = mock_compact`（monkey patch 方法本身，`test_playbook_runner.py:1079`）

如果我們直接把 `PlaybookRunner` 拆成 Plugin 架構，那**這 193 處耦合會立即崩潰**——每次重構 commit 都不可能 green。我不會接受。

我的條件：
1. **不可一次性替換**——必須採用 Strangler Fig（絞殺者榕樹）模式：新架構長在舊架構旁邊，逐步取代。
2. **舊 `PlaybookRunner` 在過渡期必須保留為「Facade」**——對外簽章不變、`_evaluate`、`_get_correction` 這些 hot 方法在新架構長出來前，要保留薄包裝，讓 193 處測試繼續綠燈。
3. **每個重構里程碑都必須通過完整的 558 tests**。任何違反此規則的 PR 我直接 revert。
4. 我要求新增 **Equivalence Test Suite**：用同一份 Playbook，在舊 Runner 與新 Kernel 各跑一次，比對 `step_log`、`mutation_log`、`completed_step_ids`、`peak_token_pct` 必須 byte-level 相同。
5. 全程使用 **TDD**：先寫等價性測試（紅）→ 實作新 Kernel/Plugin（綠）→ 切換 Facade 內部實作（綠）→ 退役舊邏輯（綠）。
</thinking>

### 1.3 兩人共識（Convergence）

| 共識項 | 內容 |
|--------|------|
| **C1：手術範圍** | 鎖定 `autoclaude/execution/playbook_runner.py` 為主，連帶涉及 `checkpoint_manager.py`、`knowledge_base.py`、`evolution/*` 的介面化。 |
| **C2：替換策略** | Strangler Fig + Facade Preservation，禁止 Big-Bang Rewrite。 |
| **C3：測試門檻** | 每個 commit 必須 `pytest tests/ -q` 全綠（558 passed）。新增 Equivalence Test 作為硬門檻。 |
| **C4：里程碑切片** | 不少於 6 個獨立 milestone，每個 milestone 可單獨合併、單獨回滾。 |
| **C5：交付節奏** | 採 AISDLC v0.09 開發-編譯-測試循環（CLAUDE.md 強制規則）：每改一支模組立即 `pytest`，禁止累積。 |

---

## 2. 現狀痛點分析（Architecture Smells）

### 2.1 量化指標

| 指標 | 現值 | 業界基準 | 嚴重度 |
|------|------|----------|--------|
| `PlaybookRunner` 總行數 | 2246 | < 300 | 🔴 Critical |
| 單一最大方法 `_run_steps` 行數 | 888 | < 50 | 🔴 Critical |
| `PlaybookRunner` 公開＋私有方法總數 | 31 | < 10 | 🔴 Critical |
| `__init__` 中直接 `new` 的協作者 | 12 | 0（注入） | 🔴 Critical |
| 測試對私有屬性／方法的直接引用 | **193**（v1.1 實測校正） | 0 | 🔴 Critical |
| `_run_steps` 內 `if/elif` 分支層級最深處 | 7 層 | ≤ 3 層 | 🟠 High |
| 重複的 GOAL_SYNTHESIS 分支邏輯 | 2 處（行 660 + 行 813） | 0 | 🟠 High |
| Checkpoint 儲存呼叫點 | 3 處 | 1 處 | 🟠 High |
| 單一檔案匯入的 internal modules | 18 | < 7 | 🟡 Medium |

### 2.2 Smell 清單（Code Smell + Design Smell）

#### Smell #1: God Object（上帝物件）

`PlaybookRunner` 同時擔任：

- **Orchestrator**（協調 12 個協作者）
- **State Machine Driver**（INIT/EXECUTE/EVALUATE/...）
- **Persistence Coordinator**（直接呼叫 `CheckpointManager.save`）
- **Mutation Applier**（`_apply_single_mutation` 含 7 種突變的 246 行 if-elif 鏈）
- **Evolution Trigger**（直接判定何時 escalate、何時演化）
- **Token Policy Engine**（compact/halt 門檻邏輯散在執行流內）
- **Anchor Builder**（`_send_compact` 內組裝 `[GLOBAL_GOAL]` / `[ACTIVE_TASK]`）
- **Notifier Adapter**（直接呼叫 `notify` / `notify_escalation`）

**結果**：任何方向的變化都打到同一個 class。違反 OCP（開放封閉原則）。

#### Smell #2: New-keyword Coupling（具體類別耦合）

```python
# autoclaude/execution/playbook_runner.py:138-149
self._evaluator = Evaluator(timeout=...)            # ← 具體類別
self._checkpoint_mgr = CheckpointManager(...)        # ← 具體類別
self._knowledge_base = FailureKnowledgeBase(...)    # ← 具體類別（檔案後端寫死）
self._evolver = PlaybookEvolver()                    # ← 具體類別
```

無法替換 `FailureKnowledgeBase` 為 PostgreSQL 後端，除非改 `PlaybookRunner` 本身。違反 DIP。

#### Smell #3: Long Method（超長方法）

`_run_steps` 單體 888 行，內含至少 25 個獨立邏輯區段（從 CONTEXT_NEGOTIATION → loop attempt → EVALUATE → CORRECTION → ESCALATION → MUTATION → CHECKPOINT 全部塞在一個 while 迴圈）。

**衝擊**：
- 讀者無法在合理時間內理解控制流。
- 修改時極易遺漏 7 處「if hotkey.triggered」之一。
- Cyclomatic Complexity 推估 > 100（健康值 < 10）。

#### Smell #4: Shotgun Surgery（散彈式修改）

新增一個 Token 監控行為（例：`/compact` 後驗證），需要同時修改：

1. `_should_compact_now`（compact 觸發判定）
2. `_send_compact`（compact 後驗證）
3. `_handle_token_halt`（halt 處理）
4. `_get_dynamic_compact_threshold`（動態門檻）
5. `_run_steps` 內的 5 個 token guard 檢查點

> **Architect**：這在 Evo-005 加 Gap-039（compact MEMORY ANCHOR）時就已經痛過——必須同時改 `_send_compact` 和 `config.py` 的 `global_goal_anchor_chars`，加上注入點分散在 `_send_compact` 與 `_prepend_global_goal_brief` 兩處，光對齊 anchor 字數就花掉一個 commit。

#### Smell #5: Feature Envy（特徵依戀）

`_apply_single_mutation`（306 行）對 `Playbook`、`PlaybookTask`、`StepMutation` 三個 model 的內部欄位有極深操作：

- 直接 `playbook.tasks.insert(...)`
- 直接 `task.prompt = mutation.revised_prompt`
- 直接 `del playbook.tasks[_del_idx]`

這些都是 model 自身的職責，應由 model 提供 `apply_mutation()` 方法，而非 Runner 越俎代庖。

#### Smell #6: Duplicated Branch Logic（重複分支）

GOAL_SYNTHESIS ESCALATION 分支同時出現在：

- `_run_steps`（行 660 ~ 700）：收斂評估觸發路徑
- `_run_steps`（行 813 ~ 853）：重試耗盡觸發路徑

兩段邏輯近乎完全一致，只差「觸發原因字串」。任何修正必須兩處同步改，極易出錯。

#### Smell #7: Leaky Abstraction（抽象洩漏）

- `CheckpointManager` 內部直接 `json.dump` 並寫檔，**無 Repository 介面**。要換 PostgreSQL 必須整段重寫。
- `FailureKnowledgeBase` 內部直接 `JSONL` 讀寫，**無查詢介面**——`get_strategy_priority` 等查詢直接掃 `_cache` dict。
- `_persist_mutated_playbook` 直接 `yaml.safe_dump` 寫檔——演化版 Playbook 的版本控制完全失控。

#### Smell #8: Test Coupling（測試耦合）

193 處 `runner._private_*` 引用是**最危險的 smell**。它意味著：

- 測試在驗證**實作**而不是**行為**。
- 任何重構（即使是純 rename）都會炸測試。
- Plugin 化重構幾乎不可能無痛——除非導入 Strangler Fig + Facade Preservation。

> **QA**：193 處引用裡，有 **>60% 是用來繞過 Claude Code CLI 真實執行的 test stub**（patch `runner._evolver.propose_evolution`）。這部分其實是合理的 Seam，但被誤用為「測試入口」。重構後應改為注入 Mock Plugin 而非 patch 私有屬性。

### 2.3 痛點優先級矩陣

| Smell | 影響範圍 | 修復成本 | 優先級 |
|-------|----------|----------|--------|
| #1 God Object | 全系統 | 🔴 極高 | **P0**（必修，但分階段） |
| #2 New-keyword Coupling | DAL 接入阻擋 | 🟡 中 | **P0**（首批執行） |
| #3 Long Method | 可讀性／可維護性 | 🟠 高 | **P1** |
| #4 Shotgun Surgery | 新功能成本 | 🟠 高 | **P1** |
| #5 Feature Envy | Mutation 擴展性 | 🟡 中 | **P2** |
| #6 Duplicated Branch | Bug 風險 | 🟢 低 | **P2** |
| #7 Leaky Abstraction | DAL 接入阻擋 | 🟠 高 | **P0**（與 #2 連動） |
| #8 Test Coupling | 重構安全性 | 🔴 極高 | **P0**（先解，否則卡死全部） |

---

## 3. 目標架構藍圖（Microkernel + Plugin System）

### 3.1 核心設計哲學

> **Architect**：我們參考三個成熟案例：
>
> 1. **pytest 的 pluggy**：以 hookspec / hookimpl 解構 plugin。優點是社群驗證、語義清晰；缺點是運行期 hook 解析有 overhead，且 stack trace 較難追。
> 2. **VS Code Extension Host**：`extensions/` 目錄下每個擴展自管生命週期，主程式只暴露 API。對 AutoClaude 過於重量。
> 3. **Linux Kernel Microkernel**：核心只做 process scheduling 與 IPC，其餘交給 modules。**這是我們的目標**。
>
> 結論：**自建輕量 Hook System**（仿 pluggy 的 spec/impl 概念，但不引入 pluggy 套件依賴），優點是 zero-cost、stack trace 直觀、與 Pydantic models 完美整合。

### 3.2 微核心職責邊界

```
┌─────────────────────────────────────────────────────────────────┐
│                     PlaybookKernel（< 200 行）                   │
│  - 純粹的 DAG 狀態機（INIT → STEP → DONE / ESCALATED）          │
│  - 透過 IExecutor.execute(prompt) 取得結果                       │
│  - 透過 IEvaluator.evaluate(task, output) 取得 verdict           │
│  - 透過 EventBus.emit(event) 觸發 hook                           │
│  - 不做：token 監控、checkpoint、evolution、knowledge base       │
│            ↓                                                     │
│       EventBus（dispatcher）                                     │
│            ↓                                                     │
└─────┬───────┬────────┬─────────┬──────────┬──────────┬──────────┘
      │       │        │         │          │          │
      ▼       ▼        ▼         ▼          ▼          ▼
 ┌──────┐ ┌──────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
 │Token │ │Check-│ │Evolution│ │Knowledge│ │Conver-│ │Notif./   │
 │Guard │ │point │ │ Plugin  │ │  Base   │ │gence  │ │Hotkey    │
 │Plugin│ │Plugin│ │         │ │ Plugin  │ │Plugin │ │Plugin    │
 └──────┘ └──────┘ └─────────┘ └────────┘ └────────┘ └─────────┘
      │       │        │         │
      ▼       ▼        ▼         ▼
   IStateRepository / IMemoryStore / IPlaybookRepository
   （DAL 抽象，後端可為 File｜PostgreSQL｜Redis，詳 Part 2）
```

### 3.3 模組分層（Layered Architecture）

依賴方向：上層 → 下層；下層**不可**反向依賴上層。

```
┌──────────────────────────────────────────────────────┐
│  Layer 4: CLI / Entry Point（autoclaude.main）        │
│           - 組裝 Plugin、注入 Repository              │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Layer 3: Plugins（autoclaude.plugins.*）             │
│           - TokenGuardPlugin / CheckpointPlugin / ...│
│           - 訂閱 EventBus，呼叫 Layer 2 介面          │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Layer 2: Core / Domain（autoclaude.core.*）          │
│  - PlaybookKernel（純狀態機）                          │
│  - EventBus（事件分派）+ DefaultResolutionPolicy       │
│  - HookSpec（contract 介面，v1.1 拆 4 個 Protocol）   │
│  - IExecutor / IEvaluator / IBrain（Port 介面）       │
│  - MutationApplyService（Domain Service，v1.1 修正）  │
│    含 7 個 IMutationStrategy（REVISE/INJECT_AFTER/    │
│    INJECT_BEFORE/GOTO/SKIP_TO/DELETE/NO_OP）          │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Layer 1: Infrastructure（autoclaude.infra.*）        │
│  - PtyExecutor（PtyWrapper 包裝）                      │
│  - ShellEvaluator                                     │
│  - MinimaxBrain                                       │
│  - FileStateRepository / PgStateRepository（DAL）     │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Layer 0: Models（autoclaude.models.*）               │
│  - Playbook / PlaybookTask / StepMutation 等          │
│  - 純資料結構，無 IO                                  │
└──────────────────────────────────────────────────────┘
```

### 3.4 Hook System 規格（自建輕量 EventBus）

#### 3.4.1 HookSpec 定義（Contract）

```python
# autoclaude/core/hookspec.py（新檔案，目標 < 150 行）
from __future__ import annotations
from typing import Protocol, Optional
from dataclasses import dataclass
from enum import Enum

class KernelPhase(str, Enum):
    PRE_RUN = "pre_run"                  # Playbook 開始前（PreRunValidator 接此）
    POST_RUN = "post_run"                # Playbook 結束後（GOAL_SYNTHESIS 接此）
    PRE_STEP = "pre_step"                # 步驟開始前（CrossStepValidator 接此）
    POST_STEP = "post_step"              # 步驟結束後（KB record_success 接此）
    PRE_ATTEMPT = "pre_attempt"          # 每次 attempt 前（注入 global_goal）
    POST_ATTEMPT = "post_attempt"        # 每次 attempt 後（評估失敗轉 CORRECTION）
    PRE_EVALUATE = "pre_evaluate"        # Evaluator 執行前
    POST_EVALUATE = "post_evaluate"      # Evaluator 執行後
    PRE_CORRECTION = "pre_correction"    # Minimax 諮詢前
    POST_CORRECTION = "post_correction"  # Minimax 諮詢後（含 step_mutation 處理）
    ON_TOKEN_USAGE = "on_token_usage"    # TokenGuardPlugin 接此
    ON_FAILURE = "on_failure"            # KB record_escalation 接此
    ON_SUCCESS = "on_success"            # KB record_success / completed_step_ids
    ON_ESCALATION = "on_escalation"      # EvolutionPlugin 接此
    ON_EVOLUTION = "on_evolution"        # 通知 + checkpoint 持久化
    ON_INTERRUPT = "on_interrupt"        # ESC+F12 / SIGINT
    ON_STATE_TRANSITION = "on_state_transition"  # 通用觀察點


# ──────────────────────────────────────────────────────────────
# v1.1：HookContext.payload 採 per-phase TypedDict（QA 必要修改 #2）
# 解決原 dict payload 缺乏型別契約、難以做 contract test 的問題。
# ──────────────────────────────────────────────────────────────
from typing import TypedDict, Union

class TokenUsagePayload(TypedDict):
    """ON_TOKEN_USAGE phase 專用。"""
    token_pct: float
    raw_match: str
    consecutive_compact_failures: int

class FailurePayload(TypedDict):
    """ON_FAILURE / POST_ATTEMPT phase 專用。"""
    error_class: str            # ErrorClass enum value
    error_signature: str
    failed_output: str
    convergence_trend: str      # converging / stuck / oscillating / cycling

class CorrectionPayload(TypedDict):
    """PRE_CORRECTION / POST_CORRECTION phase 專用。"""
    decision: dict              # CorrectionDecision dump
    correction_prompt: str
    minimax_latency_ms: int

class EvolutionPayload(TypedDict):
    """ON_ESCALATION / ON_EVOLUTION phase 專用。"""
    proposal: dict              # PlaybookEvolutionProposal dump
    evolution_metadata: dict
    escalated_step_ids: list[str]

# 其餘 phase 的 payload 為空 dict（無需訂閱者直接取得 mutable state）
PhasePayload = Union[TokenUsagePayload, FailurePayload, CorrectionPayload,
                     EvolutionPayload, dict]


@dataclass(frozen=True)  # ← 不可變，避免 Plugin 互改 ctx
class HookContext:
    """所有 hook 共用的執行上下文。"""
    phase: KernelPhase
    playbook: "Playbook"
    task: Optional["PlaybookTask"] = None
    step_idx: Optional[int] = None
    attempt: Optional[int] = None
    payload: PhasePayload = None  # ← v1.1：型別化
    # mutable state 一律透過 Repository / 注入服務取得，不放在 ctx


class IHook(Protocol):
    """Plugin 必須實作的契約。"""
    def name(self) -> str: ...
    def priority(self) -> int: ...               # ← v1.1：執行序明確化（Architect 必要修改 #3）
    def subscribed_phases(self) -> list[KernelPhase]: ...
    def on_event(self, ctx: HookContext) -> Optional["IHookResult"]: ...


# ──────────────────────────────────────────────────────────────
# v1.1：HookResult 依 ISP 拆為 4 個獨立 Protocol（Architect 必要修改 #1）
# 原單一 dataclass 塞 7 種異質意圖 = god struct，Plugin 被迫認識所有欄位。
# ──────────────────────────────────────────────────────────────
class IHookResult(Protocol):
    """所有 result 的標記介面。"""
    contributor: str  # Plugin name，用於追蹤合併來源


@dataclass(frozen=True)
class VetoResult(IHookResult):
    """中止當前 phase（如 PreRunValidator block 不安全的 step）。"""
    contributor: str
    reason: str


@dataclass(frozen=True)
class PromptInjectionResult(IHookResult):
    """注入 prompt prefix（如 global_goal / cross_step_hint）。"""
    contributor: str
    prefix: str
    position: str = "top"   # top / before_anchor / after_anchor


@dataclass(frozen=True)
class ResourceRequest(IHookResult):
    """請求 Kernel 執行資源管理動作（compact / halt / escalation）。"""
    contributor: str
    request_compact: bool = False
    request_halt: bool = False
    request_escalation: bool = False
    reason: str = ""


@dataclass(frozen=True)
class MutationProposal(IHookResult):
    """提議步驟突變（MinimaxBrain / EvolutionPlugin 使用）。"""
    contributor: str
    mutation: "StepMutation"
    rationale: str = ""


# 每個 phase 限定可回傳的 result 型別（強制契約）：
PHASE_RESULT_CONTRACT: dict[KernelPhase, set[type]] = {
    KernelPhase.PRE_RUN: {VetoResult},
    KernelPhase.PRE_STEP: {VetoResult},
    KernelPhase.PRE_ATTEMPT: {PromptInjectionResult, VetoResult},
    KernelPhase.POST_ATTEMPT: {ResourceRequest, MutationProposal},
    KernelPhase.PRE_CORRECTION: {PromptInjectionResult},
    KernelPhase.POST_CORRECTION: {MutationProposal},
    KernelPhase.ON_TOKEN_USAGE: {ResourceRequest},
    KernelPhase.ON_ESCALATION: {MutationProposal, ResourceRequest},
    # 其餘為純觀察 phase，回傳 None
}
```

#### 3.4.2 EventBus 實作（v1.1：注入 IResolutionPolicy + priority 排序）

> **Architect 必要修改 #2 / #3 已併入**：原 `MergedResult.from_list` 內寫死的合併邏輯違反 DIP（Bus 不該知道 mutation/compact 的優先級）。v1.1 抽出為 `IResolutionPolicy` Strategy 介面，並要求 Plugin 自報 `priority(): int` 以決定執行序。

```python
# autoclaude/core/event_bus.py（新檔案，目標 < 150 行）
import logging
from collections import defaultdict
from typing import Iterable, Protocol

logger = logging.getLogger("autoclaude.core.bus")


# ──────────────────────────────────────────────────────────────
# v1.1：合併規則抽為 Strategy（DIP）。Bus 不再知道優先級，
# 由 ResolutionPolicy 決定。預設 policy 為 DefaultResolutionPolicy。
# ──────────────────────────────────────────────────────────────
class IResolutionPolicy(Protocol):
    """合併多個 IHookResult 的策略介面。"""
    def merge(
        self,
        phase: KernelPhase,
        results: list[IHookResult],
    ) -> "MergedResult": ...


class DefaultResolutionPolicy:
    """v1.1 預設合併策略，所有規則明文化、可重現。

    決定性順序（QA 必要修改 #2）：
      1. 先依 phase 的 PHASE_RESULT_CONTRACT 過濾不合法的 result
      2. 再依 hook.priority() 排序（小者先；同 priority 依 register 順序）
      3. VetoResult：任一存在即整體 veto，accumulate veto reasons
      4. PromptInjectionResult：依排序後順序串接 prefix（穩定）
      5. ResourceRequest：or 邏輯（任一 plugin 提出即生效），紀錄第一個觸發者
      6. MutationProposal：取「priority 最低」的提案；同 priority 取「最早 register」
    """
    def merge(self, phase, results):
        results = sorted(results, key=lambda r: (
            getattr(r, "_priority", 50), getattr(r, "_register_idx", 0)
        ))
        ...  # 套上述規則，全部規則皆由本 class 明文實現
        return MergedResult(...)


class EventBus:
    """同步 dispatcher。刻意不引入 async／threading，保持狀態機可預測。"""

    def __init__(self, policy: IResolutionPolicy | None = None):
        self._subscribers: dict[KernelPhase, list[IHook]] = defaultdict(list)
        self._policy = policy or DefaultResolutionPolicy()
        self._register_seq = 0

    def register(self, hook: IHook) -> None:
        seq = self._register_seq
        self._register_seq += 1
        for phase in hook.subscribed_phases():
            # 將 priority + register_idx 附在 hook 上以供 policy 排序
            hook._priority = hook.priority()  # type: ignore[attr-defined]
            hook._register_idx = seq          # type: ignore[attr-defined]
            self._subscribers[phase].append(hook)
            logger.debug("Plugin %s 訂閱 %s（priority=%d, seq=%d）",
                         hook.name(), phase, hook._priority, seq)

    def emit(self, ctx: HookContext) -> "MergedResult":
        results: list[IHookResult] = []
        # 依 priority 排序後依序呼叫
        ordered = sorted(self._subscribers.get(ctx.phase, []),
                         key=lambda h: (h._priority, h._register_idx))
        for hook in ordered:
            r = hook.on_event(ctx)
            if r is None:
                continue
            # v1.1：契約檢查——不合法 result 即拋例外（fail-fast）
            allowed = PHASE_RESULT_CONTRACT.get(ctx.phase, set())
            if allowed and type(r) not in allowed:
                raise HookContractViolation(
                    f"Plugin {hook.name()} 在 {ctx.phase} 回傳不合法型別 {type(r)}"
                )
            r._priority = hook._priority         # type: ignore[attr-defined]
            r._register_idx = hook._register_idx # type: ignore[attr-defined]
            results.append(r)
        return self._policy.merge(ctx.phase, results)


@dataclass(frozen=True)
class MergedResult:
    veto: bool
    veto_reasons: list[str]
    accumulated_prefix: str
    request_compact: bool
    request_halt: bool
    request_escalation: bool
    request_mutation: Optional["StepMutation"]
    contributors: list[str]  # 依排序後順序記錄
```

**Plugin priority 約定表（v1.1 新增，文件化執行序）**：

| Priority | 用途 | 範例 Plugin |
|----------|------|-------------|
| 0 ~ 9    | 系統級 veto / 中斷檢查 | HotkeyPlugin（10）、PreRunValidatorPlugin（5） |
| 10 ~ 29  | 安全 / 一致性 guards | CrossStepValidatorPlugin（15） |
| 30 ~ 49  | Prompt 注入 / 資源管理 | TokenGuardPlugin（30）、GlobalGoalAnchorPlugin（35） |
| 50（預設） | 一般觀察者 | KnowledgeBasePlugin、NotificationPlugin |
| 60 ~ 79  | 演化 / 突變提議 | EvolutionPlugin（70）、ConvergencePlugin（65） |
| 80 ~ 99  | 持久化（最後執行） | CheckpointPlugin（90）、GotoCounterPlugin（85） |

> **Architect**：priority 只決定**呼叫順序**，不決定**合併規則**——後者一律由 `IResolutionPolicy` 控制。任何兩個 Plugin 若需互相依賴，必須在文件中明示其 priority 關係（避免隱性耦合）。

> ✅ **SD_03 補完（2026-05-12）**：HookContext.payload TypedDict 及 IResolutionPolicy 於 SD_03 W2 完全實作；`test_token_halt_payload_contract.py` 已驗證；Plugin emit 優先級契約於 `test_plugin_emit_order.py` 鎖定。

#### 3.4.3 微核心主循環（PlaybookKernel）

```python
# autoclaude/core/kernel.py（新檔案，目標 < 250 行）
class PlaybookKernel:
    """純粹的 DAG 狀態機。不持有任何業務邏輯。"""

    def __init__(
        self,
        executor: "IExecutor",
        evaluator: "IEvaluator",
        brain: "IBrain",
        bus: "EventBus",
        state_repo: "IStateRepository",
        playbook_repo: "IPlaybookRepository",
    ):
        self._exec = executor
        self._eval = evaluator
        self._brain = brain
        self._bus = bus
        self._state = state_repo
        self._pb_repo = playbook_repo

    def run(self, playbook_path: str, fresh: bool = False) -> "KernelResult":
        playbook = self._pb_repo.load(playbook_path)
        checkpoint = None if fresh else self._state.load_checkpoint(playbook_path)

        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=playbook, payload={})
        merged = self._bus.emit(ctx)
        if merged.veto:
            return KernelResult.vetoed(merged.veto_reasons)

        step_idx = checkpoint.step_idx if checkpoint else 0
        while step_idx < len(playbook.tasks):
            outcome = self._run_step(playbook, step_idx, checkpoint)
            if outcome.action == StepAction.ADVANCE:
                step_idx += 1
            elif outcome.action == StepAction.GOTO:
                step_idx = outcome.goto_idx
            elif outcome.action == StepAction.ESCALATE:
                return KernelResult.escalated(outcome)
            elif outcome.action == StepAction.HALT:
                return KernelResult.halted(outcome)
            checkpoint = None  # 後續步驟不再用 checkpoint

        merged_post = self._bus.emit(HookContext(phase=KernelPhase.POST_RUN, ...))
        return KernelResult.success(merged_post)

    def _run_step(self, playbook, step_idx, checkpoint) -> "StepOutcome":
        """單一步驟的 attempt loop，目標 < 80 行。
        - 不再內嵌 token guard 邏輯（交給 TokenGuardPlugin）
        - 不再內嵌 mutation 應用邏輯（交給 MutationApplier service）
        - 不再內嵌 evolution（交給 EvolutionPlugin）
        """
        # ... 約 60-80 行
```

> **Architect**：這個 Kernel 的設計目標是「**讀者 5 分鐘內看完 `kernel.py` 全文，能完整理解狀態機**」。所有變化點都透過 `bus.emit()` 委外。

### 3.5 Plugin 拆解與職責矩陣（v1.1：補 GotoCounterPlugin、明確 MutationApplyService 歸屬）

**重要修正（Architect 必要修改 #4 / #5）**：
- 原 v1.0 的 12 Plugin 矩陣**未承接 Gap-042 / Gap-048 的 `goto_counter` / `inject_before_counter` / `skip_to_counter` / `step_evolution_counter`**，恐回流 Kernel；v1.1 新增 **GotoCounterPlugin** 明確承接。
- `MutationApplyService` 在 v1.0 同時被列在「Plugin 矩陣」與「Domain Service」兩處，歸屬不清；v1.1 明確歸至 **Layer 2 Core Domain Service**（非 Plugin），其於 EventBus 之外被 Kernel 直接呼叫。

| # | 元件 | 類型 | 訂閱 Phase / Priority | 取代原 PlaybookRunner 中的程式碼區段 | 行數估計 |
|---|------|------|------------------------|--------------------------------------|----------|
| 1 | `TokenGuardPlugin` | Plugin (Layer 3) | `POST_ATTEMPT`(30), `ON_TOKEN_USAGE`(30) | `_should_compact_now`, `_send_compact`, `_get_dynamic_compact_threshold`, `_handle_token_halt` 中的 token 邏輯 | ~250 |
| 2 | `CheckpointPlugin` | Plugin (Layer 3) | `POST_STEP`(90), `ON_INTERRUPT`(90), `ON_TOKEN_USAGE`(90), `ON_EVOLUTION`(90) | `_save_interrupt_checkpoint`, `_save_evolution_resume_checkpoint` | ~180 |
| 3 | `GotoCounterPlugin`（**v1.1 新增**） | Plugin (Layer 3) | `POST_ATTEMPT`(85), `ON_INTERRUPT`(85) | Gap-042 / Gap-048 跨 Session 計數器（`goto_counter` / `inject_before_counter` / `skip_to_counter` / `step_evolution_counter`）持久化與上限檢查 | ~120 |
| 4 | `ConvergencePlugin` | Plugin (Layer 3) | `POST_ATTEMPT`(65) | `monitor.evaluate(tracker)` 整段、ESCALATE 判定 | ~150 |
| 5 | `EvolutionPlugin` | Plugin (Layer 3) | `ON_ESCALATION`(70) | `_minimax_evolver` + `_evolver` fallback 邏輯、GOAL_SYNTHESIS 補完（去重複） | ~220 |
| 6 | `KnowledgeBasePlugin` | Plugin (Layer 3) | `ON_SUCCESS`(50), `ON_FAILURE`(50), `ON_ESCALATION`(50) | `record_success` / `record_escalation` 散在 4 處的呼叫 | ~80 |
| 7 | `NotificationPlugin` | Plugin (Layer 3) | `ON_ESCALATION`(50), `ON_EVOLUTION`(50), `POST_RUN`(50) | `_notify` / `notify_escalation` 散在 7 處的呼叫 | ~50 |
| 8 | `HotkeyPlugin` | Plugin (Layer 3) | `PRE_STEP`(10), `PRE_ATTEMPT`(10) | `if self._hotkey.triggered:` 散在 3 處的檢查 | ~60 |
| 9 | `PreRunValidatorPlugin` | Plugin (Layer 3) | `PRE_RUN`(5), `PRE_ATTEMPT`(5) | `PreRunValidator().validate_step(...)` 區段 | ~70 |
| 10 | `CrossStepValidatorPlugin` | Plugin (Layer 3) | `PRE_STEP`(15) | `CrossStepStateValidator()` 區段 | ~60 |
| 11 | `GlobalGoalAnchorPlugin` | Plugin (Layer 3) | `PRE_ATTEMPT`(35), `ON_TOKEN_USAGE`(35) | `_prepend_global_goal` / `_prepend_global_goal_brief` / `_send_compact` 中的 anchor 注入（Gap-039 / Gap-013-H） | ~90 |
| 12 | `GoalSynthesisPlugin` | Plugin (Layer 3) | `POST_RUN`(50) | `_validate_global_goal_achievement` + GOAL_SYNTHESIS 步驟注入 | ~120 |
| — | `MutationApplyService`（**v1.1 改歸 Layer 2**） | **Core Domain Service** | （非 Plugin，由 Kernel 直接呼叫） | `_apply_single_mutation`（306 行）拆分為 7 個 Strategy class（REVISE_CURRENT / INJECT_AFTER / INJECT_BEFORE / GOTO_STEP / SKIP_TO / DELETE_STEP / NO_OP） | ~350（拆分後總和） |

**v1.1 Plugin 總計：12 個 Plugin + 1 個 Domain Service**（行數預算詳 §3.13）。

**對照前後**：

```
Before:                          After:
┌─────────────────────┐         ┌──────────────┐
│ PlaybookRunner      │         │PlaybookKernel│ < 250 行
│   2246 行           │   →     └──────┬───────┘
│   31 個方法         │                │
│   12 個 new()       │                ▼
└─────────────────────┘         ┌─────────────────┐
                                │ 12 個 Plugin    │ 每個 < 250 行
                                │ 1 個 Kernel     │
                                │ 1 個 EventBus   │
                                │ 7 個 Mutation   │
                                │   Strategy     │
                                └─────────────────┘
                                Total: ~2400 行（總量持平，但 SRP 達成）
```

### 3.6 類別圖（PlantUML 概念圖，文字版）

```
[Layer 0] Models（不變）
  Playbook   PlaybookTask   StepMutation   EvolutionMetadata
            ↑     ↑     ↑
            │     │     └────────────────────────┐
[Layer 1] Infrastructure                          │
  ┌───────────────┐  ┌────────────────┐  ┌──────┴───────────┐
  │ PtyExecutor   │  │ ShellEvaluator │  │ MinimaxBrain     │
  │ implements    │  │ implements     │  │ implements       │
  │ IExecutor     │  │ IEvaluator     │  │ IBrain           │
  └───────────────┘  └────────────────┘  └──────────────────┘

  ┌────────────────────────┐  ┌────────────────────────┐
  │ FileStateRepository    │  │ FileMemoryStore        │
  │ implements             │  │ implements             │
  │ IStateRepository       │  │ IMemoryStore           │
  └────────────────────────┘  └────────────────────────┘
  ┌────────────────────────┐  ┌────────────────────────┐
  │ PgStateRepository      │  │ PgMemoryStore          │
  │ (Phase 6 + 將實作)     │  │ (Phase 6+ 將實作)      │
  └────────────────────────┘  └────────────────────────┘

[Layer 2] Core
  ┌────────────────┐                 ┌──────────────────────────┐
  │ PlaybookKernel │ ─── uses ──→    │ MutationApplyService     │
  │ < 250 行       │ ─ direct call → │   IMutationStrategy × 7  │
  └────────────────┘                 └──────────────────────────┘
        │ uses                       (REVISE / INJECT_AFTER /
        │                             INJECT_BEFORE / GOTO_STEP /
        ▼                             SKIP_TO / DELETE / NO_OP)
  ┌────────────────────────────────┐
  │ EventBus + IResolutionPolicy   │   ← v1.1：Strategy 注入
  │ (DefaultResolutionPolicy)      │
  └────────────────────────────────┘
        │ dispatch (依 priority 排序)
        ▼
[Layer 3] Plugins（皆 implements IHook，宣告 priority + subscribed_phases）
  HotkeyPlugin(10)            PreRunValidatorPlugin(5)
  CrossStepValidatorPlugin(15) TokenGuardPlugin(30)
  GlobalGoalAnchorPlugin(35)   KnowledgeBasePlugin(50)
  NotificationPlugin(50)       GoalSynthesisPlugin(50)
  ConvergencePlugin(65)        EvolutionPlugin(70)
  GotoCounterPlugin(85)        CheckpointPlugin(90)
  ──────────────────────────────────────────────────
  共 12 Plugin（v1.1 新增 GotoCounterPlugin 承接 Gap-042/048）

[Layer 4] CLI
  ┌──────────────────────────────────────────────────┐
  │ main.py                                          │
  │   - 讀 config                                    │
  │   - 組裝 Repository（File or Pg, by config）      │
  │   - 註冊所有 Plugin（順序由 config 控制）         │
  │   - kernel.run(playbook_path)                    │
  └──────────────────────────────────────────────────┘
```

### 3.7 為什麼選微核心而不是其他模式？

| 候選方案 | 優點 | 缺點 | 結論 |
|----------|------|------|------|
| **Microkernel + Plugin（採用）** | SRP、OCP 達成；Plugin 可獨立測試；支援動態組裝 | Hook 順序需明確設計；初期重構成本高 | ✅ |
| Hexagonal（Ports & Adapters） | 介面隔離乾淨 | 對「橫切關注點」（Token/Checkpoint）支援弱，要再加 Decorator | ❌ 弱於微核心 |
| Event Sourcing | 完美的審計鏈 | 過度工程，對 AutoClaude 規模不必要 | ❌ |
| Pipeline / Chain of Responsibility | 簡單 | 無法處理「同時訂閱多個 phase」的 plugin | ❌ |
| 純 Strategy Pattern | 容易實作 | 無法解決「橫切關注點」散在 9 處的問題 | ❌ |

> **Architect**：微核心的關鍵價值在於——**未來的所有新功能都應該是新增一個 Plugin，而不是修改 Kernel**。這就是 OCP 的具體實踐。如果做不到這點，這次重構就失敗了。

### 3.8 微核心 + Plugin 的「驗收條件」

未來任何新功能（例如：「新增遠端 Webhook 通知」、「新增 LangSmith 追蹤」、「新增 PR 自動評論」）必須能透過**「新增一個 Plugin 檔案」**完成，禁止修改 `PlaybookKernel`。

**反例**（若違反此條件，代表重構未達標）：

- ❌ 若新增「Slack 通知」需要改 `PlaybookKernel`，代表 NotificationPlugin 的訂閱機制設計失敗。
- ❌ 若新增「Redis 後端」需要改 `PlaybookKernel`，代表 IStateRepository 抽象失敗（DAL 設計詳 Part 2）。
- ❌ 若新增「自定義 Convergence 策略」需要改 `PlaybookKernel`，代表 ConvergencePlugin 解耦失敗。

**正例**：

- ✅ 新增 Plugin → 在 `autoclaude/plugins/your_plugin.py` 寫一個 `class YourPlugin(IHook)` → 在 `main.py` 加一行 `bus.register(YourPlugin())` → 完成。

### 3.9 Port 契約測 Suite（v1.1 新增｜QA 必要修改 #3）

**動機**：`IExecutor` / `IEvaluator` / `IBrain` / `IStateRepository` / `IMemoryStore` 等 Port 介面有多後端實作（File 後端、未來 PG 後端、Mock 後端），若無 LSP 驗證骨架，多後端切換時極易出現「介面相同但行為不同」的退化。

**設計**：以 abstract pytest base class 強制所有 Adapter 通過同一組契約測。

```python
# tests/contract/test_state_repository_contract.py
import pytest
from abc import ABC, abstractmethod

class IStateRepositoryContract(ABC):
    """所有 IStateRepository 實作的共通行為驗證骨架。
    任何新後端（PgStateRepository、RedisStateRepository、...）
    必須繼承此 class 並實作 _make_repo()，否則 CI 阻擋合併。
    """

    @abstractmethod
    def _make_repo(self, tmp_path) -> "IStateRepository": ...

    def test_save_load_roundtrip(self, tmp_path):
        repo = self._make_repo(tmp_path)
        cp = make_sample_checkpoint()
        repo.save_checkpoint("pb_001", cp)
        loaded = repo.load_checkpoint("pb_001")
        assert loaded == cp                      # ← 行為等價

    def test_concurrent_save_is_atomic(self, tmp_path):
        # 多 process 同時 save 不應產生 partial write
        ...

    def test_load_missing_returns_none(self, tmp_path):
        repo = self._make_repo(tmp_path)
        assert repo.load_checkpoint("nonexistent") is None

    def test_clear_idempotent(self, tmp_path):
        repo = self._make_repo(tmp_path)
        repo.clear("pb_001")
        repo.clear("pb_001")                     # ← 重複 clear 不應拋例外

    def test_counter_persistence_round_trip(self, tmp_path):
        # Gap-042 / Gap-048 計數器必須跨 save/load 完整保留
        ...


class TestFileStateRepositoryContract(IStateRepositoryContract):
    def _make_repo(self, tmp_path):
        return FileStateRepository(checkpoint_dir=str(tmp_path))


class TestPgStateRepositoryContract(IStateRepositoryContract):
    """Phase 6 接入時自動繼承同一組測試，零額外撰寫成本。"""
    def _make_repo(self, tmp_path):
        return PgStateRepository(dsn=os.environ["TEST_PG_DSN"])
```

**Adapter LSP 驗收標準**：
- 任一新後端 PR 必須通過 `pytest tests/contract/ -v` 全綠
- 不得跳過測試（`@pytest.mark.skip` 視為 PR fail）
- 對 contract 不適用的測試需以 `pytest.skip("此後端不支援 X 行為")` 並在 PR 描述中說明

### 3.10 Frozen Private Surface 清單（v1.1 新增｜QA 必要修改 #4）

**動機**：193 處測試直接引用 `runner._private_*`，重構期間若不凍結這些「私有 API surface」，任何 rename / refactor 都會炸測試。

**過渡期承諾（Phase 1 ~ Phase 4 期間，凍結期 8 ~ 12 週）**：以下「private surface」**簽章不可變，內部實作可改**：

| 凍結成員 | 凍結原因 | 解凍時機（Phase） |
|---------|----------|--------------------|
| `runner._evaluate(task, output) -> (success, msg)` | 41 處測試直接呼叫 | Phase 4 Facade 切換完成後 |
| `runner._get_correction(task, output, msg) -> CorrectionDecision` | 28 處測試直接呼叫 | Phase 4 |
| `runner._send_compact() -> bool` | 17 處測試 monkey-patch | Phase 4 |
| `runner._apply_single_mutation(mutation, ...) -> bool` | 22 處測試直接呼叫 | Phase 4 |
| `runner._validate_batch_compatibility(mutations) -> bool` | 8 處測試直接呼叫 | Phase 4 |
| `runner._evolver`（屬性） | 14 處測試 patch | Phase 3 EvolutionPlugin 完成後 |
| `runner._minimax_evolver`（屬性） | 9 處測試 patch | Phase 3 EvolutionPlugin 完成後 |
| `runner._consecutive_compact_failures`（屬性） | `test_token_checkpoint.py:908` 等直接寫入 | Phase 3 TokenGuardPlugin 完成後 |
| `runner._cfg.token_guard.enabled`（屬性鏈） | 多處直接改 config | Phase 4 |

**棄用流程（Deprecation Cycle）**：
1. Phase 4 完成、Equivalence Test 全綠後，標記為 `@deprecated(version="2.0")`
2. 對應測試開始改寫為 Plugin 注入式（每改一個 PR）
3. 測試全部遷移完成後（預估 Phase 5 末），刪除 private surface
4. 解凍前任一變更 = QA 直接 revert

**v1.1 強制規則**：在 §3.10 凍結期內，禁止修改上述任一簽章；如必須變更，需 QA + Architect 雙方書面批准。

> ✅ **SD_03 補完（2026-05-12）**：Frozen Surface 凍結期 Phase 4 已完成；9 項 shim 轉純委派（W4）；`_runner_impl.py`（2,236 行）已刪除（SD_Delete_RunnerImpl G6，2026-05-14）；193 處測試耦合遷移進行中（v2.0 長期項）。

### 3.11 CLI 100% 向後相容承諾（v1.1 新增｜PM 必要修改 #2）

**承諾範圍**：以下 CLI 介面在整個重構期間（Phase 0 ~ Phase 6）**完全不變**：

| 介面 | 承諾 |
|------|------|
| `python -m autoclaude <playbook.yaml>` | 完全相容 |
| `python -m autoclaude <playbook.yaml> --config <path>` | 完全相容 |
| `python -m autoclaude <playbook.yaml> --fresh` | 完全相容 |
| `python -m autoclaude <playbook.yaml> --dry-run` | 完全相容 |
| `autoclaude` entrypoint（pip install 後） | 完全相容 |
| `config.yaml` 全部欄位 | 不刪除、不改名；新增欄位皆可選且具預設值 |
| `playbook.yaml` schema | 不變更必填欄位；新增欄位皆可選 |
| Exit code（0=success, 1=failure, 2=escalated, 3=halted） | 完全不變 |
| `checkpoint.json` 檔案格式 | 向前相容（新欄位可缺，舊欄位保留） |

**驗證方式**：
- Phase 0 建立 `tests/cli/test_cli_compatibility.py`，固化 9 個 CLI 場景的輸入／輸出 snapshot
- 每階段 PR 必須通過 CLI 相容性測試（CI gate）
- 任何破壞性變更 = 直接 revert

### 3.12 Gap-009 ~ Gap-049 不退化清單（v1.1 新增｜PM 必要修改 #2）

**承諾**：所有 Level 5 已交付 Gap 能力在重構期間**逐項保留**，每項對應一個專屬測試案例（無一可繞過）：

| Gap | 能力 | 對應測試（凍結） | 重構後承接 |
|-----|------|------------------|-----------|
| Gap-009 | StepMutation 基礎 | `test_gap009.py` 全 32 處 | MutationApplyService |
| Gap-010-A~F | ErrorBudget / KB 元學習 | `test_gap009.py` | KnowledgeBasePlugin |
| Gap-011-A | global_goal 注入 | `test_gap012.py` | GlobalGoalAnchorPlugin |
| Gap-011-B | 動態步驟突變 | `test_gap012.py` | EvolutionPlugin + MutationApplyService |
| Gap-012 | INJECT_AFTER / DELETE_STEP | `test_gap012.py` | MutationApplyService |
| Gap-013-H | compact MEMORY ANCHOR (400 字元) | `test_gap013.py` | GlobalGoalAnchorPlugin |
| Gap-014~020 | 自動演化 + GOAL_SYNTHESIS | `test_gap014_020.py` | EvolutionPlugin / GoalSynthesisPlugin |
| Gap-021~028 | Pre-Run / Cross-Step / Convergence | `test_gap021_028.py` | PreRunValidatorPlugin / CrossStepValidatorPlugin / ConvergencePlugin |
| Gap-029~038 | CONDITIONAL 突變、conditional_evaluator | `test_gap029_038.py` | MutationApplyService |
| Gap-039 | compact MEMORY ANCHOR 持久化 | `test_gap039_049.py` | GlobalGoalAnchorPlugin + CheckpointPlugin |
| Gap-040 | 演化版 playbook 持久化 | `test_gap039_049.py` | CheckpointPlugin |
| Gap-041 | completed_step_ids 跨 Session | `test_gap039_049.py` | CheckpointPlugin |
| **Gap-042** | **goto/inject_before/skip_to 計數器持久化** | `test_gap039_049.py` | **GotoCounterPlugin（v1.1 新增）** |
| Gap-043~047 | KB 預播種 + 兜底查詢 | `test_gap039_049.py` | KnowledgeBasePlugin |
| **Gap-048** | **per-step 演化次數跨 Session** | `test_gap039_049.py` | **GotoCounterPlugin（v1.1 新增）** |
| **Gap-049** | **`max_goto_per_step` 可配置** | `test_gap039_049.py` | GotoCounterPlugin（讀 `PlaybookConfig.max_goto_per_step`） |

**驗收門檻**：每個 Phase 結束的 PR 必須通過 `pytest tests/test_gap*.py -v` 全綠（共 17 個 Gap 測試檔，558 cases 中佔約 280 cases）。任一退化 = QA 直接 revert。

### 3.13 行數預算上限 + Stakeholder Gate（v1.1 新增｜PM 必要修改 #3 / #4）

#### 3.13.1 行數預算（DoD）

| 元件 | 上限 | 違反處置 |
|------|------|---------|
| `PlaybookKernel` | ≤ 250 行 | PR 阻擋合併 |
| 單一 Plugin | ≤ 250 行 | PR 阻擋合併 |
| 單一 IMutationStrategy | ≤ 80 行 | PR 阻擋合併 |
| `EventBus` + `DefaultResolutionPolicy` | ≤ 200 行 | PR 阻擋合併 |
| 重構後 `autoclaude/` 總行數 | ≤ **Phase 4 末段 baseline** × 1.20（**最終 cap**，v1.1 §3.13.1 補註） | 需 Architect 簽核才可超出 |

> **🔴 v1.1 補註（Phase 4 Gate G3 PM 簽核時加入）：分階段 baseline 規則**
>
> 重構期間 baseline 在「結構穩定點」重新校正：
> - **Phase 0 baseline**：原始程式碼（4810 行）
> - **Phase 2 baseline**：Kernel + EventBus + MutationApplyService 骨架建立後（5872 行）
> - **Phase 4 末段 baseline**：Plugin 全數遷移 + Facade 工廠就緒（7031 行）— **此為最終 cap 計算基準**
> - **Phase 5 baseline**：DAL 介面 + Repository Adapter 抽出後（再次校正）
> - **Phase 6 末段（最終形態）**：須回歸至 Phase 4 baseline × 1.20 = 8437 行（含選配 PG backend）
>
> **「淨減行優先」適用於 Phase 5 末以後**：當測試耦合解凍後，舊 PlaybookRunner 內邏輯逐步刪除，最終 LOC 應下降。Phase 5 期間引入 DAL 抽出基礎設施屬合理峰值。

**自動化檢查**：CI 加入 `tools/check_loc_budget.py`，超預算直接 fail。

#### 3.13.2 Stakeholder Gate（PM 簽核點）

| Gate | 條件 | 簽核者 |
|------|------|--------|
| **Gate G1**：進入 Phase 1 抽介面 | SD_Improving_01.md / 02.md 三方批准 + Phase 0 Equivalence Test 全綠 | Architect + QA + PM |
| **Gate G2**：進入 Phase 3 Plugin 遷移 | EventBus / Kernel skeleton 通過契約測 + 558 tests 全綠 | Architect + QA |
| **Gate G3**：進入 Phase 4 Facade 切換 | 12 Plugin 全部遷移完成 + Equivalence Test byte-level 等價 + 558 tests 全綠 | **PM 強制簽核**（高風險變更） |
| **Gate G4**：進入 Phase 5 DAL 抽出 | Facade 切換穩定執行 ≥ 2 週、無回歸 issue | Architect + QA |
| **Gate G5**：進入 Phase 6 PG 後端（選配） | DAL Port 通過契約測 + 商業需求確認 | PM + Stakeholder |

> **PM**：任一 Gate 未通過即不得進入下一 Phase；Gate G3 為最高風險點，QA 退回時 PM 必須與 Architect 重新評估時程，禁止「為趕進度跳 Gate」。

---

## 4. 連動到 Part 2 的議題清單

以下議題交給 [SD_Improving_02.md](SD_Improving_02.md) 詳述：

1. **DAL（Data Access Layer）抽象規格**
   - `IStateRepository`（Checkpoint 存取）
   - `IMemoryStore`（FailureKnowledgeBase 存取）
   - `IPlaybookRepository`（Playbook YAML / 演化版本管理）
   - PostgreSQL 接入路線（SQLAlchemy 2.0 async + Alembic）
   - schema 設計（含 PG-friendly 的 JSONB 欄位）
   - 後端切換機制（config-driven，無需改 Kernel）

2. **TDD 重構步驟（Strangler Fig 6 階段）**
   - Phase 0：補齊 Equivalence Test（基準線）
   - Phase 1：抽出介面（IExecutor / IEvaluator / IBrain）
   - Phase 2：建立 EventBus + Kernel skeleton（與舊 Runner 並存）
   - Phase 3：逐一搬遷 Plugin（每個 Plugin 一個 PR）
   - Phase 4：Facade 切換（PlaybookRunner 內部呼叫新 Kernel）
   - Phase 5：DAL 抽象抽出
   - Phase 6：PostgreSQL 接入（選配）

3. **風險矩陣與回滾策略**
   - 每階段的 fail-safe（git tag + checkpoint backup）
   - 558 tests 的 monitoring policy

4. **里程碑與驗收條件**
   - 每個 milestone 的 DoD（Definition of Done）
   - QA 簽核點

---

## 5. 本份文件的審查 Checklist（給 Reviewer，v1.1 擴充）

請依下列項目逐一勾選：

**架構面（Architect）**：
- [ ] 痛點分析是否量化？（量化 Smell ≥ 8 項）
- [ ] 微核心職責是否單一？（Kernel ≤ 250 行為硬性目標，§3.13）
- [ ] Plugin 拆解是否覆蓋所有原 Runner 邏輯？（**12 Plugin + 1 Domain Service + 7 IMutationStrategy**，v1.1）
- [ ] HookResult 是否依 ISP 拆分？（4 個 Protocol：Veto / PromptInjection / ResourceRequest / MutationProposal，§3.4.1）
- [ ] Plugin 執行序是否文件化？（priority 約定表，§3.4.2）
- [ ] 合併規則是否抽離 EventBus？（IResolutionPolicy + DefaultResolutionPolicy，§3.4.2）
- [ ] Gap-042 / Gap-048 計數器是否有 Plugin 承接？（GotoCounterPlugin，§3.5）
- [ ] MutationApplyService 是否明確歸屬 Layer 2？（Domain Service，§3.5）
- [ ] 是否提供類別圖／Layer 圖？（已含 ASCII art，§3.3 / §3.6）
- [ ] 是否定義「重構成功」的驗收條件？（§3.8 反例 / 正例）

**測試面（QA）**：
- [ ] 是否回應了 QA 的 5 個條件？（Strangler Fig + Facade + 558 tests + Equivalence + TDD）
- [ ] HookContext.payload 是否型別化？（per-phase TypedDict，§3.4.1）
- [ ] MergedResult 合併是否決定性？（DefaultResolutionPolicy 明文規則，§3.4.2）
- [ ] Port 介面是否有 LSP 契約測？（§3.9）
- [ ] Frozen Private Surface 清單是否清楚？（§3.10，含 9 項凍結成員）
- [ ] Gap-009~049 是否逐項列出對應測試？（§3.12）
- [ ] Equivalence Test 是否含 mutation_log + step_evolution_counter byte-level 比對？（待 Part 2 §2.2 落實）

**商業／落地面（PM）**：
- [ ] CLI 介面是否承諾 100% 向後相容？（§3.11，9 項 CLI 場景）
- [ ] Gap-009~049 不退化是否有專屬清單？（§3.12，17 個 Gap）
- [ ] 行數預算上限是否明文？（§3.13.1，Kernel ≤ 250、Plugin ≤ 250、總量 ≤ +20%）
- [ ] Stakeholder Gate 是否定義？（§3.13.2，G1~G5 含 PM 簽核點）
- [ ] Phase 時程估算是否在 Part 2 落實？（指引給 Part 2，待 Part 2 §4 Milestones 提供）

**通過門檻**：以上 22 項逐一勾選；任一未勾選則 v1.1 不予批准。

---

## 6. 三人結語（v1.1）

**Architect**：v1.1 已併入 ISP 拆分（HookResult → 4 個 Protocol）、IResolutionPolicy 注入、GotoCounterPlugin 承接 Gap-042/048、MutationApplyService 歸屬 Layer 2 等必要修改。核心 commitment 不變：「**Kernel 必須瘦身到能在一頁螢幕讀完**」。任何理由都不能讓 Kernel 重新長成 god object。

**QA**：v1.1 已補上 per-phase TypedDict payload schema、DefaultResolutionPolicy 決定性合併規則、Port 契約測 Suite (§3.9)、Frozen Private Surface 清單 (§3.10)。我保留 Part 2 中「TDD 步驟」的最終否決權——任何階段若無法保持 558 tests green，必須重新設計步驟切片。**我們不接受 partial-green commit**。

**PM**：v1.1 已補上 CLI 100% 向後相容承諾 (§3.11)、Gap-009~049 不退化清單 (§3.12)、行數預算上限與 Stakeholder Gate G1~G5 (§3.13)。我保留 Gate G3（Facade 切換）的強制簽核權；任何試圖跳 Gate 趕進度的 PR 將被直接退回。Phase 時程估算交由 Part 2 §4 Milestones 提供具體區間。

---

**下一步**：請繼續閱讀 [SD_Improving_02.md](SD_Improving_02.md)，內容涵蓋 DAL 抽象規格、TDD 6 階段細節、風險矩陣與里程碑驗收。

---

**文件元數據**：

- 建立日期：2026-05-07
- 文件版本：**v1.1**（Draft，已併入三方必要修改）
- 預估閱讀時間：45 分鐘
- 適用團隊：核心架構組 + QA 組 + PM
- Review 截止：待專案 PM 排期

**v1.1 變更摘要**（vs v1.0）：
- §1.2 / §2.1：統計校正 249 → 193 處（實測）
- §3.4.1：HookResult 依 ISP 拆為 4 Protocol、HookContext.payload 型別化
- §3.4.2：抽出 IResolutionPolicy + DefaultResolutionPolicy（DIP），新增 priority 約定表
- §3.5：新增 GotoCounterPlugin（承接 Gap-042/048）；MutationApplyService 改歸 Layer 2
- §3.3 / §3.6：Layer 圖補上 MutationApplyService 與 priority 標註
- **§3.9 新增**：Port 契約測 Suite（LSP）
- **§3.10 新增**：Frozen Private Surface 清單（9 項 + 凍結期）
- **§3.11 新增**：CLI 100% 向後相容承諾
- **§3.12 新增**：Gap-009~049 不退化清單（17 項）
- **§3.13 新增**：行數預算上限 + Stakeholder Gate G1~G5
- §5：Reviewer Checklist 擴為 22 項
- §6：升級為 Architect + QA + PM 三人結語
