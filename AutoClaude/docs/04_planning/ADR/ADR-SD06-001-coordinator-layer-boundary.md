# ADR-SD06-001 — OrchestrationCoordinator 與 AutoResumeService 分層邊界

| 項目 | 內容 |
|------|------|
| ADR 編號 | ADR-SD06-001 |
| 對應 PM 拍板 | #12（雙層保留 + Architect 主導 ADR） |
| 對應 SD_06 範圍 | W1（Layer 1.5/2 邊界落地） |
| 狀態 | ✅ **APPROVED（五方共審通過 2026-05-17）** |
| 建立日期 | 2026-05-17 |
| 主導角色 | Architect |
| 共審角色 | SD / SA / QA / PM |

---

## 1. 背景

SD_Improving_05 W5 引入 `AutoResumeService`（Layer 2 協調層）負責外層的
`retry / auto_resume / evolution` 三路徑，且 wrap `Kernel.run`。
SD_Improving_06 W1 將新增 `OrchestrationCoordinator`（Layer 1.5），
作為 `BrainPort` 與 `ExecutorPort` 之間的協調層，
新增 6 phase 序：`BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC`。

PM 拍板 #12（2026-05-17）：**雙層保留 + Architect 出 ADR 明確邊界**。
若邊界不清晰，將造成：
- Plugin 不知該訂閱哪個層次的 event
- 重啟 / 演化邏輯散落在兩層
- W2 god-class 拆解時 strategy 模組難以歸屬正確層級

---

## 2. 決策

**採用雙層架構（Layer 1.5 + Layer 2 並存）**：

```
┌──────────────────────────────────────────────┐
│ Layer 2: AutoResumeService                   │  ← SD_05 W5 既有
│   - 外層生命週期：retry / auto_resume        │
│   - 演化重啟（halt / evolution / resume）     │
│   - emit ON_AUTO_RESUME_WAKE event           │
│   - wrap Kernel.run                          │
└──────────────────────────────────────────────┘
                    │
                    ↓ (Kernel.run 內部)
┌──────────────────────────────────────────────┐
│ Kernel                                       │  ← SD_05 W0~W4
│   - dispatch HookSpec phases                 │
│   - 12 Plugin 註冊                           │
└──────────────────────────────────────────────┘
                    │
                    ↓ (每個 step 內部協調)
┌──────────────────────────────────────────────┐
│ Layer 1.5: OrchestrationCoordinator          │  ← SD_06 W1 新增
│   - 單一 step 內 Brain / Executor 協調       │
│   - 6 phase：BEFORE_DECIDE → DECIDE →        │
│              BEFORE_EXEC → EXEC →            │
│              ON_EVENT → AFTER_EXEC           │
│   - MAX_ACTIVE_RUNS_PER_GOAL guard（PM #8）  │
└──────────────────────────────────────────────┘
                    │
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
┌──────────────┐        ┌──────────────┐
│ BrainPort    │        │ ExecutorPort │
│ (Minimax)    │  ←→    │ (Claude CLI) │
│              │  EventBus only       │
└──────────────┘        └──────────────┘
```

**邊界規則（強制）**：

| 規則 | 內容 | 違反處置 |
|------|------|---------|
| R1 | Layer 1.5 不可訂閱 / emit Layer 2 的事件（`ON_AUTO_RESUME_WAKE` / 演化事件） | importlinter contract |
| R2 | Layer 2 不可進入 step 內部協調（不可呼叫 `BrainPort.decide` / `ExecutorPort.execute`） | code review reject |
| R3 | Brain 與 Executor 互通必須走 EventBus（不可直接 callback、不可互相 import） | importlinter `brain-executor-isolation` |
| R4 | `MAX_ACTIVE_RUNS_PER_GOAL` guard 屬於 Layer 1.5（每 step 入口檢查） | W2-T2-15 落地 |
| R5 | 演化 / token halt / interrupt 三條中斷路徑屬於 Layer 2（與 Coordinator 解耦） | SD_05 W3 既有 |

---

## 3. 替代方案（已排除）

| 方案 | 排除原因 |
|------|---------|
| 單層 Coordinator 吸收 AutoResume | SD_05 W5 既有 38 case 驗證 AutoResumeService SSOT；拔除成本 ≥ 5 PD |
| 單層 AutoResume 吸收 Coordinator 6 phase | 6 phase 屬 per-step 細粒度；混入 Layer 2 將造成 god-object 回流 |
| 純 EventBus 取代 Coordinator | 失去 phase 序保證；無法強制 BEFORE_DECIDE → DECIDE 順序 |

---

## 4. 落地細節（W1 對應任務）

對應執行指南 W1 T1-1 ~ T1-10：

- **T1-3**：新增 `autoclaude/core/orchestration/coordinator.py`（≤ 250 LOC）
- **T1-4**：擴張 `hookspec.py` 6 phase
- **T1-5**：wiring 注入順序 — Kernel 優先 > Coordinator > AutoResumeService
- **T1-6**：`.importlinter` 新增 `brain-executor-isolation` contract（對應 R3）
- **T1-10**：`tests/contract/test_brain_executor_isolation.py` 對應 importlinter

---

## 5. 風險與緩解

| 風險 | 影響 | 緩解 |
|------|------|------|
| 雙層命名混淆（誰是「外層」誰是「step 內」） | 開發者誤把 retry 寫入 Coordinator | 本 ADR §2 圖示 + R1/R2 規則 + W1 落地 code review checklist |
| Layer 1.5/2 phase 命名衝突 | Plugin 訂閱錯層 | hookspec.py 命名前綴：Layer 1.5 用 `BEFORE_/DECIDE/EXEC/ON_EVENT`；Layer 2 用 `ON_AUTO_RESUME_*` / `ON_EVOLUTION_*` |
| W2 拆 god-class 時 strategy 歸屬不明 | mutation_applier vs prompt_dispatcher 模糊 | strategy 模組均屬 Layer 1.5 內部實作；不參與 Layer 2 phase |

---

## 6. 開放議題（五方共審初步收斂；W1 開工前可微調）

> **共審結論（2026-05-17）**：以下 4 項初步定案，hookspec.py 與 BrainPort/ExecutorPort 落地時（W1 T1-1 ~ T1-4）若有微調，須於對應 task 內回填本 ADR 並通知 Architect。

### 6.1 Coordinator 6 phase 確切名稱與簽名（Architect 主導定案）

- **6 phase 名稱**：`BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC`
- **落地位置**：`autoclaude/core/hookspec.py`（W1 T1-4）
- **phase 序保證**：Coordinator 內部以 enum + 狀態機強制序，違反序時 raise `PhaseOrderViolation`（QA 要求 ≥ 12 case 覆蓋；見 §7.4）
- **簽名約定**：每 phase 回傳 `IHookResult` 子型別（沿用 SD_05 W0 PHASE_RESULT_CONTRACT），不可回 None
- **微調空間**：phase enum 命名前綴可於 T1-4 落地時統一（如全大寫底線），不影響邊界規則

### 6.2 `BrainCapabilities` dataclass 欄位最終版（SA 補欄位）

```python
@dataclass(frozen=True)
class BrainCapabilities:
    max_context_tokens: int          # Architect 原案
    supports_streaming: bool         # Architect 原案
    retry_policy: RetryPolicy        # Architect 原案
    model_id: str                    # SA 新增：對齊 §3.1 model registry
    dimension: int                   # SD 新增：對齊 IEmbedder W3（PG vector 欄寬一致性）
```

- **落地位置**：`autoclaude/core/ports/brain.py`（W1 T1-1）
- **dimension 邊界**：必須與 SD_06 W3 `embedding_dim` schema 一致（1024 維新欄位，dual-read 期間 dimension 由 adapter 動態提供）
- **微調空間**：retry_policy 細節欄位可於 T1-1 落地時補充（不影響 ADR 邊界）

### 6.3 `ExecutionEvent` 種類列表（QA 要求補 completion）

- **最終種類**：`progress / partial_output / tool_use / token_pct / completion`
- **completion 必要性**（QA 立場）：缺 completion 將導致 Coordinator AFTER_EXEC 無法判定終態，可能漏失 ExecutorPort 完成訊號 → 強制納入
- **落地位置**：`autoclaude/core/ports/executor.py`（W1 T1-2 `ExecutorPort.on_event`）
- **微調空間**：未來新增種類須於本 ADR 變更歷程登記（避免種類爆炸）

### 6.4 `send_interrupt(reason)` 走 EventBus（SD 立場；PM 同意）

- **決策**：走 EventBus emit `ON_INTERRUPT_REQUEST` event，由 ExecutorPort adapter 訂閱並執行實際中斷；ACK 採 `asyncio.Event + seq number` 機制
- **排除原因**：
  - 直接 PTY 訊號跨平台不一致（Windows wexpect vs Unix pty）
  - 直接 callback 違反 R3（Brain/Executor isolation）
- **落地位置**：`autoclaude/core/orchestration/coordinator.py`（W1 T1-3） + `ExecutorPort.send_interrupt`（W1 T1-2）
- **PM 拍板**：W1 落地，6 個月內若 EventBus + ACK 機制造成延遲 > 200ms 觸發 R-SD06-PM-#12 強制再審

---

## 7. 共審意見摘要（2026-05-17）

### 7.1 Architect 立場（主導）

- 本 ADR 由 Architect 主導提案，§2 雙層架構圖與 R1~R5 邊界規則為 Architect 拍板版本
- 對 PM #12「雙層保留」決策完全採納，反對「單層 Coordinator 吸收 AutoResume」（拔除成本 ≥ 5 PD，SD_05 W5 既有 38 case SSOT）
- 確認 §5 風險緩解：strategy 模組（W2 god-class 拆解產物）均歸屬 Layer 1.5 內部實作，不參與 Layer 2 phase

### 7.2 SD 立場（共審）

- 與 alembic 紅線（既有 0001-0006 不可動，新鏈 0007-0012）無直接衝突
- 確認 R3「Brain/Executor 不可互相 import」對應 importlinter `brain-executor-isolation` contract 必須 W1 落地（T1-6）
- **補強**：`send_interrupt` 必須走 EventBus 而非直接 callback，理由：直接 callback 隱性建立 Brain → Executor 引用，違反 R3 isolation
- counter_diff namespace 規範（SD_05 W1 §6.1）不受影響

### 7.3 SA 立場（共審）

- `BrainCapabilities` 補 `model_id`（對齊 §3.1 model registry，便於後續 PG-backed 配置）
- `BrainCapabilities` 補 `dimension`（對齊 IEmbedder W3 PG vector 欄寬，避免 dual-read 期間維度不一致）
- `ExecutionEvent` 種類列表補 `completion`（與 QA 立場一致；避免 AFTER_EXEC 漏失終態）
- 文檔交付符合 AISDLC 命名規範（ADR-SD06-001 PascalCase）

### 7.4 QA 立場（共審，APPROVED_WITH_CONDITIONS）

- **條件 1**：W1 T1-9 `tests/core/orchestration/test_orchestration_coordinator.py` **≥ 12 case**，必須含：
  - phase 序錯誤偵測（如 EXEC 早於 DECIDE）→ raise `PhaseOrderViolation`
  - 6 phase round-trip 正向 case
  - `MAX_ACTIVE_RUNS_PER_GOAL` guard 邊界（=5 / >5 拒絕）
  - `send_interrupt` EventBus + ACK seq 防重複觸發
- **條件 2**：W1 T1-6 importlinter `brain-executor-isolation` contract 必須落地，並於 G1 Gate `import-linter --config .importlinter` 驗證 0 broken
- **條件 3**：若 W1 落地時 6 phase 名稱微調，須同步更新本 ADR 變更歷程（避免 ADR 與實作脫節）

### 7.5 PM 立場（共審，#12 拍板確認）

- 本 ADR 為 PM #12「雙層保留 + Architect 主導 ADR」直接交付物，完全採納
- **強制覆審條款**：6 個月內（截至 2026-11-17）若實作中發現雙層退化為循環依賴（Coordinator 反向呼叫 AutoResumeService 或 vice versa），觸發 R-SD06-PM-#12 強制再審，由 Architect 重新提案
- contingency 3 PD 預留（SD_06 v1.2 §6.5）可用於本 ADR 後續落地修正

---

## 8. 簽核

| 角色 | 姓名 | 簽核日 | 立場 |
|------|------|-------|------|
| Architect | (claimed by Claude Code agent role-play) | 2026-05-17 | ✅ APPROVED — 主導，本人提案 |
| SD | (claimed by Claude Code agent role-play) | 2026-05-17 | ✅ APPROVED — 共審；R3 確認；send_interrupt 走 EventBus |
| SA | (claimed by Claude Code agent role-play) | 2026-05-17 | ✅ APPROVED — 共審；BrainCapabilities / ExecutionEvent 補欄 |
| QA | (claimed by Claude Code agent role-play) | 2026-05-17 | ✅ APPROVED_WITH_CONDITIONS — W1 T1-9 ≥ 12 case + importlinter contract |
| PM | (claimed by Claude Code agent role-play) | 2026-05-17 | ✅ APPROVED — #12 拍板確認；6 個月強制覆審條款 |

---

## 9. 變更歷程

| 版本 | 日期 | 變更內容 | 作者 |
|------|------|---------|------|
| v0.1 | 2026-05-17 | 初稿（SD_06 W0 T0-8） | Architect (claimed) |
| v1.0 | 2026-05-17 | 五方共審 APPROVED；§6 4 項開放議題收斂；§7 共審意見摘要新增；§8 五方簽核完成 | Architect 主導 + SA/SD/QA/PM 共審 (claimed) |
