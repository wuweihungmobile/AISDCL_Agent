# SD_Improving_03_Phase4_bug_01 — 三方審查發現彙整 + 四方審議

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.1**（四方審議 APPROVED WITH CONDITIONS，2026-05-15） |
| 建立日期 | 2026-05-15 |
| 文件類型 | Bug Report / Architecture Gap Analysis |
| 對應目錄 | `docs/04_planning/` |
| 審查來源 | SD_Improving_03 Phase 4 完成後獨立三方審查 |
| 審查角色 | **Architect / SA / SD 三方獨立審查** |
| 審議角色 | Architect / SA / SD / QA **四方審議** |
| 文件狀態 | **APPROVED WITH CONDITIONS — 四方審議通過，進入 SD_Improving_04** |
| 觸發來源 | 使用者 6 點特別關注 + playbook_runner.py 1,962 行異常 |

---

## 0. 審查背景與 6 點特別關注

SD_Improving_03（Phase 4 Facade 切換）已完成，測試基線為 **1,057 passed / 10 skipped**。  
但使用者提出 6 點特別關注，觸發本次三方獨立審查：

| # | 使用者關注點 | 審查結論 |
|---|------------|---------|
| 1 | playbook_runner.py 1,962 行遠超預期 < 150 行 | **架構問題確認（C-1, C-2, C-3）** |
| 2 | Plugin 架構合規？應疊加 Plugin，不是在單一程式累積 | **部分違規（C-1, M-5）** |
| 3 | PostgreSQL 三層架構（Project/Task/Prompt）+UI 管理 | **嚴重缺失（C-5, SD-C3）** |
| 4 | 架構與 PG 皆符合向量紀錄與搜尋（pgvector） | **骨架存在但實作不完整（C-4, M-7）** |
| 5 | 狀態保存與恢復執行機制 | **邊界條件缺測（C-6, M-8）** |
| 6 | 參數設定（/compact ?%）和 token 偵測 | **配置驗證缺失（M-3, M-4, M-6）** |

---

## 1. 三方獨立審查總表

> 各方獨立審查，不互相知曉結論，防止意見污染。

| 角色 | Critical | Major | Minor | 主要打擊點 |
|------|----------|-------|-------|-----------|
| **Architect** | 3 | 6 | 6 | 反向依賴違規、雙路由失控、LOC 13 倍超標 |
| **SA（系統分析師）** | 3 | 8 | 7 | 三層架構缺 Task/ExecutionItem、向量搜尋 SQL 注入、Checkpoint 邊界測缺失 |
| **SD（系統設計師）** | 3 | 6 | 6 | PgMemoryStore asyncio 缺陷、Checkpoint 1:1 約束錯誤、三層架構缺失 |

---

## 2. CRITICAL 嚴重問題（必修，阻擋後續規劃）

> 三方共同確認的 Critical 問題優先標注 ⭐

---

### **C-1：PlaybookRunner 1,962 行 — LOC 超標 13 倍** ⭐ 三方共識

**來源**：Architect C-3 / SA（隱含）/ SD（隱含）

**問題描述**：
- 計畫目標：`playbook_runner.py` < **150 行** thin facade
- 實際現狀：**1,962 行**（超限 13 倍）
- W5 migration 計畫「完全刪除 _runner_impl.py」，但反而將所有邏輯直接 inline 至 PlaybookRunner

```
playbook_runner.py 行數分布（實測）：
  L001~162   init + M1 shim（合理，162 行）
  L163~282   run() 外層迴圈（合理，120 行）
  L283~1097  _run_steps 核心邏輯（✗ 820 行，應遷移至 Kernel）
  L1098~1962 輔助方法（✗ 864 行，應移至 Plugin / utils）
```

**現象對應**：本該完成 Strangler Fig 重構，但業務邏輯仍全部殘留在 PlaybookRunner，Kernel 是空轉。

**嚴重度**：🔴 **CRITICAL**  
**修復方向**：
1. `_run_steps` 核心邏輯（L283~1097）遷移至 Kernel + 對應 Plugin（TokenGuardPlugin / EvolutionPlugin / CheckpointPlugin）
2. 輔助方法（L1098~1962）拆分至 utils/ 或對應 Plugin
3. 最終 PlaybookRunner **≤ 150 行**（init + 3 個 M1 shim + run 委派）

---

### **C-2：main.py `use_kernel_path` 二元路由——技術債陷阱** ⭐ Architect+SA

**來源**：Architect C-2

**問題描述**：
```python
# main.py:87-98（當前狀態）
if cfg.playbook.use_kernel_path:   # 新路徑：Kernel + AutoResumeService
    ...
    result = service.run(...)
else:                               # 舊路徑：PlaybookRunner legacy（仍 1,962 行）
    runner = PlaybookRunner(cfg, minimax, hotkey)
    result = runner.run(...)
```

- 兩條執行路徑長期並存，新路徑實際是走 `AutoResumeService` 但 PlaybookRunner 舊路徑仍有 1,962 行邏輯
- `use_kernel_path=True`（預設），但舊 PlaybookRunner 路徑未被刪除，形成永久隱患
- 缺乏明確的 deprecation deadline（舊路徑何時下線？）

**嚴重度**：🔴 **CRITICAL**  
**修復方向**：
1. 設定 legacy 路徑終止日期（建議 2026-07-15）
2. `use_kernel_path=False` 時發出 `DeprecationWarning`
3. C-1 解決後方可真正移除舊路徑

---

### **C-3：`_runner_compat.py` 引入架構障礙**

**來源**：Architect M-1

**問題描述**：
- 計畫刪除 `_runner_impl.py`，實際新建 `_runner_compat.py`（219 行）
- PlaybookRunner 透過 import 引用 `_evaluate_impl`、`_apply_single_mutation_impl` 等函式
- 三層結構（PlaybookRunner → `_runner_compat` → 實作）而非直接委派 Kernel

**問題**：
1. `_runner_compat.py` 沒有明確定位（永久 adapter vs 臨時過渡？）
2. 與 Kernel 內部服務（`MutationApplyService`、`IEvaluator`）邏輯重複
3. 測試割裂：`_runner_compat` 需獨立測試，簽章已被 legacy 凍結

**嚴重度**：🔴 **CRITICAL**  
**修復方向**：`_runner_compat.py` 應明確標記為臨時過渡，並與 C-1 同步排除計畫。

---

### **C-4：PgMemoryStore 異步相容性缺陷** ⭐ SD+SA

**來源**：SD C-1 / SA（隱含）

**問題描述**：
```python
# pg_memory_store.py:35-52（問題代碼）
def query(self, error_signature: str) -> Optional[dict]:
    try:
        return asyncio.run(self._query(error_signature))  # ← 裸 asyncio.run()
    except Exception:
        return None
```

- 所有公開方法使用裸 `asyncio.run()`
- `PgStateRepository` 已正確實裝 `_run_async()` 包裝（pg_state_repository.py L85-99）
- 在已有 event loop 的環境（FastAPI、未來 UI backend、測試框架）會立即拋 `RuntimeError: This event loop is already running`

**同樣問題**：`pg_playbook_repository.py` 也使用裸 `asyncio.run()`，未套用 `_make_retry()`

**嚴重度**：🔴 **CRITICAL**（影響向量搜尋、未來 UI 整合）  
**修復方向**：
```python
# 參照 pg_state_repository.py 的 _run_async() 實裝
from .pg_state_repository import _run_async, _make_retry
# 所有 asyncio.run() 改為 _run_async()
```

---

### **C-5：PostgreSQL 三層架構缺失（Project/Task/ExecutionItem）** ⭐ 三方共識

**來源**：Architect M-4 / SA C-1 / SD C-3

**問題描述**：
使用者需求：以任務方式存取與管理，三層架構：
```
Layer 1: Project（專案主層）
Layer 2: GoalTask（目標任務次層，對應 Playbook）
Layer 3: ExecutionItem（執行項目 Prompt，對應 PlaybookTask 的每次 attempt）
```

現有 `_pg_models.py` 僅有：
- `PlaybookRun`：僅有 `project: Text`（純文字，無 Project entity）
- `CheckpointRow`：Checkpoint 快照，非業務三層
- `KnowledgeEntry`：知識庫，非業務三層
- `PlaybookVersion`：演化版本，非主業務三層

**缺失**：
1. 無 `Project` 表（主層 entity，支援 UI 按 project 過濾）
2. 無 `GoalTask` 表（次層，儲存 Playbook 的 global_goal）
3. 無 `TaskRecord` 表（記錄 PlaybookTask 定義）
4. 無 `ExecutionItem` 表（記錄每次 attempt 的詳細輸出、correction_prompt、mutation）

**影響**：
- UI 無法展示「某 step 重試 N 次」的執行歷史
- 無法統計「哪些 task 最易 escalate」
- 未來 UI 管理介面缺少基礎 schema 支撐

**嚴重度**：🔴 **CRITICAL**（UI 管理需求的架構前提）

---

### **C-6：Checkpoint 一對一唯一索引設計錯誤** ⭐ SD+SA

**來源**：SD C-2

**問題描述**：
```python
# _pg_models.py:71-73
class CheckpointRow(Base):
    __tablename__ = "checkpoints"
    ...
    __table_args__ = (
        Index("idx_ck_playbook", "playbook_id", unique=True),  # ← 問題所在
    )
```

- `playbook_id` 上的 `unique=True` 表示：**一個 playbook 只能有一個 checkpoint**
- 但 `PlaybookRun` 表允許同一個 playbook 有多個 run（不同 run_id）
- 當同一個 playbook 多次執行（e.g., 測試多個版本），第二次 save_checkpoint 會覆蓋第一次，或違反約束

**嚴重度**：🔴 **CRITICAL**（多 run 場景下資料遺失）  
**修復方向**：
```sql
-- 移除舊 unique
DROP INDEX idx_ck_playbook;
-- 改為 run_id 唯一（一個 run 一個 checkpoint）
CREATE UNIQUE INDEX idx_ck_run_id ON checkpoints(run_id);
```

---

## 3. MAJOR 重要問題（Sprint 內必須解決）

---

### **M-1：Kernel.run() 無 `start_idx` / `resume_checkpoint` 支援**

**來源**：Architect M-2

**問題描述**：
```python
# auto_resume.py:48-54（已知 stub）
def _resolve_start(self, playbook_path, fresh):
    """W2 stub：Kernel 尚不支援 start_idx，目前永遠從步驟 0 開始。"""
    return 0, [], False, None  # ← 永遠從 step 0 開始，無法恢復 checkpoint
```

- `AutoResumeService._resolve_start()` 是 stub，未讀取 checkpoint
- `Kernel.run()` 無 `start_idx` 和 `resume_checkpoint` 參數
- 新 Kernel 路徑（`use_kernel_path=True`）**無法從 checkpoint 恢復執行**

**嚴重度**：🟠 **MAJOR**（Kernel 路徑 checkpoint 恢復功能缺失）

---

### **M-2：PlaybookRepository playbook_id 計算不一致（path stem vs SHA256）**

**來源**：SD M-3

**問題描述**：
- `CheckpointManager._to_id(path)` → `Path(path).stem`（e.g., `"playbook"`）
- `PgPlaybookRepository`（推測）→ `sha256(path)[:16]`
- 兩者 ID 不同，導致 checkpoint 無法對應到正確的 playbook run

**嚴重度**：🟠 **MAJOR**（PG 模式下 checkpoint 查詢失效）

---

### **M-3：TokenGuardConfig 缺乏 Pydantic 驗證**

**來源**：SA M-1 / SD M-1

**問題描述**：
```python
# config.py:57-79（當前）
class TokenGuardConfig(BaseModel):
    compact_threshold_pct: float = 80.0   # 無驗證
    halt_threshold_pct: float = 90.0      # 無驗證
```

- 使用者可配置 `compact=95%, halt=85%`（倒序），邏輯矛盾，靜默失效
- `storage.mode=db_only` 但 `db_dsn=None`，無驗證
- `context_patterns` regex 語法錯誤，無驗證

**嚴重度**：🟠 **MAJOR**（配置錯誤導致核心保護機制靜默失效）  
**修復方向**：
```python
@field_validator('halt_threshold_pct')
@classmethod
def halt_greater_than_compact(cls, v, info):
    compact = info.data.get('compact_threshold_pct', 80.0)
    if v <= compact:
        raise ValueError(f"halt_threshold_pct({v}%) 必須 > compact_threshold_pct({compact}%)")
    return v
```

---

### **M-4：context_patterns Regex 覆蓋不完整**

**來源**：SD M-6 / SA M-4

**問題描述**：
現有 4 個預設 regex 未能覆蓋部分 Claude Code 實際輸出格式：
```
# 可能無法匹配
"Context window: 45000 / 200000 tokens"   ← 分子/分母格式
"[STATS: usage 75.2%]"                    ← STATS tag
"Token usage: 123456 tokens / max 200000" ← 自然語言格式
```

- Parse 失敗時 token_pct 默認 0.0，token guard 靜默失效

**嚴重度**：🟠 **MAJOR**（token 保護機制失效）

---

### **M-5：Token Guard 邏輯分散（Plugin vs Runner 雙重實作）**

**來源**：Architect M-6

**問題描述**：
Token 偵測和 compact 邏輯散落多處：
1. `PlaybookRunner._execute_prompt()`（L1470~1543）— 執行後 token 偵測
2. `TokenGuardPlugin`— ON_TOKEN_USAGE 事件處理
3. `PlaybookRunner._should_compact_now()`（L1544~1561）— 動態閾值
4. `PlaybookRunner._send_compact()`（L1562~1625）— /compact 執行邏輯

Plugin 架構的原則：橫切關注點應 **完全** 在 Plugin 中，但 compact 邏輯大部分仍在 PlaybookRunner。

**嚴重度**：🟠 **MAJOR**（Plugin 架構違規，與 C-1 同根）

---

### **M-6：PgMemoryStore 向量搜尋 SQL 字串拼接（潛在注入風險）**

**來源**：SA C-2

**問題描述**：
```python
# pg_memory_store.py:123-131（問題代碼）
vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
# 直接字串插值拼接到 SQL：
# WHERE ... embedding <=> '{vec_str}'::vector  ← ✗ 字串拼接
```

雖然 embedding 來自內部，不是使用者輸入，但：
1. 不符合參數化查詢最佳實踐
2. 若 embedding 來源被污染（如惡意 embedding model output），有注入風險

**嚴重度**：🟠 **MAJOR**  
**修復方向**：改用 SQLAlchemy text() bindparams

---

### **M-7：pgvector 向量索引缺失（HNSW index）**

**來源**：SA C-2 / SD M-5

**問題描述**：
- `KnowledgeEntry.embedding` 有 `Vector(1536)` 欄位，但無對應向量索引
- 大量知識庫記錄時，線性 ANN 掃描效能極差
- `alembic/versions/0004_pgvector.sql` 有 HNSW index，但參數文件說明不足

**嚴重度**：🟠 **MAJOR**（向量搜尋效能無保障）

---

### **M-8：Checkpoint 恢復邊界條件未測試**

**來源**：SA C-3

**問題描述**：
現有測試僅驗證 happy path，缺少：
- **邊界 1**：resumed playbook 中途再次 halt（多層 rescue 迴圈）
- **邊界 2**：PG 連線失敗時 `storage=both` 模式 fallback 至 file
- **邊界 3**：`scheduled_resume_at` 已過期時應立即繼續，不等待
- **邊界 4**：同一 playbook_id 多個 run 競態恢復

**嚴重度**：🟠 **MAJOR**（狀態恢復可靠性無保障）

---

### **M-9：PlaybookCheckpoint 欄位設計雜亂**

**來源**：SA M-3

**問題描述**：
PlaybookCheckpoint dataclass 有 **16 個欄位**，其中：
- 4 個 `*_counter` dict（`goto_counter`、`inject_before_counter`、`skip_to_counter`、`step_evolution_counter`）語意相近，應合併
- 但 PG schema 已用 JSONB `counters` dict 合併
- Python dataclass 與 PG schema 不對齊，轉換邏輯複雜

**嚴重度**：🟠 **MAJOR**（維護性差）

---

### **M-10：PgStateRepository `_run_cache` 無 TTL（記憶體洩漏）**

**來源**：SA m3

**問題描述**：
```python
# pg_state_repository.py:136
self._run_cache: dict[str, str] = {}  # playbook_id → run_id
```

長期運行時無限增長，無清理機制。

**嚴重度**：🟠 **MAJOR**（生產環境記憶體洩漏）  
**修復方向**：改用 `cachetools.TTLCache` 或 `maxsize` LRU cache

---

### **M-11：CheckpointPlugin 與 GotoCounterPlugin Push 模式耦合**

**來源**：SA M-6

**問題描述**：
`CheckpointPlugin` 直接呼叫 `self._goto_counter.restore(snap)`，與 Plugin 應透過 EventBus 解耦的原則衝突。Plugin 間優先級順序改變時會靜默失效。

**嚴重度**：🟠 **MAJOR**（Plugin 間耦合違規）

---

## 4. MINOR 輕微問題（可計入下一 Sprint）

| # | 問題 | 來源 | 修復成本 |
|---|------|------|---------|
| m-1 | PlaybookRun.metadata_ Python 屬性名稱混淆（非必要 underscore） | SD m2 | 0.5h |
| m-2 | Factory TLS 強制檢查可被環境變數完全繞過，無環境區分 | SD m3 | 1h |
| m-3 | CheckpointRow `saved_at` 時間戳序列化為秒精度，毫秒遺失 | SD m4 | 0.5h |
| m-4 | PlaybookVersion 無版本鏈連續性驗證（v0→v1→v3 可靜默） | SD m5 | 1h |
| m-5 | ImportLinter 規則未涵蓋 execution → core services 反向依賴 | Architect Mi-3 | 1h |
| m-6 | Plugin priority 常數硬編碼於 wiring.py，未定義在 Plugin 類別 | Architect Mi-4 | 1h |
| m-7 | PgStateRepository retry 失敗時無 before_sleep 日誌（排障困難） | SA M-5 | 1h |
| m-8 | `config.yaml.example` 缺失，使用者無配置範例 | SA M-8 | 2h |
| m-9 | Alembic migration 無 seed data 腳本 | SA m2 | 2h |
| m-10 | KernelResult W0b 欄位 docstring 說明不清 | Architect Mi-2 | 0.5h |

---

## 4b. Architect 補充隱患（X-1~X-5）

> 四方審議時 Architect 獨立發現，已納入 SD_Improving_04 修復範圍。

| # | 隱患描述 | 嚴重度 | 對應已知問題 |
|---|----------|--------|------------|
| **X-1** | PlaybookRunner run() 迴圈（L170-250）與 AutoResumeService run() 迴圈（L56-96）高度重複邏輯 | MAJOR | 與 C-1 同根 |
| **X-2** | AutoResumeService._resolve_start() 永遠回傳 (0,[],False,None)，新 Kernel 路徑完全無法恢復 checkpoint | CRITICAL | M-1 確認強化 |
| **X-3** | config.py storage.mode=db_only + db_dsn=None 組合無驗證，靜默失效 | MAJOR | M-3 補充範圍 |
| **X-4** | CheckpointRow unique index 應改為 (run_id, playbook_id) 複合索引，而非單 run_id | MAJOR | C-6 補充細節 |
| **X-5** | PgPlaybookRepository 與 PgMemoryStore 的 asyncio.run() 未套用 _run_async()（PgStateRepository 已修正但兩者未同步） | CRITICAL | C-4 確認強化 |

---

## 5. 問題優先級彙整矩陣

| 問題 ID | 嚴重度 | 與使用者 6 點關注對應 | 解決週期 | 是否阻擋後續 Sprint |
|--------|--------|----------------------|---------|-------------------|
| **C-1** | 🔴 Critical | 關注 1, 2 | W1~W3 | ✅ 是 |
| **C-2** | 🔴 Critical | 關注 1, 2 | W1 | ✅ 是 |
| **C-3** | 🔴 Critical | 關注 1 | W1 | ✅ 是 |
| **C-4** | 🔴 Critical | 關注 4 | W1 | ✅ 是（UI 整合前提） |
| **C-5** | 🔴 Critical | 關注 3, 4 | W2~W4 | ✅ 是（UI 前提） |
| **C-6** | 🔴 Critical | 關注 5 | W1 | ✅ 是（多 run 場景） |
| **M-1** | 🟠 Major | 關注 5 | W2 | ⚠️ 部分 |
| **M-2** | 🟠 Major | 關注 5 | W1 | ⚠️ 部分 |
| **M-3** | 🟠 Major | 關注 6 | W1 | ❌ 否 |
| **M-4** | 🟠 Major | 關注 6 | W1 | ❌ 否 |
| **M-5** | 🟠 Major | 關注 2 | W2~W3 | ❌ 否 |
| **M-6** | 🟠 Major | 關注 4 | W1 | ❌ 否 |
| **M-7** | 🟠 Major | 關注 4 | W1 | ❌ 否 |
| **M-8** | 🟠 Major | 關注 5 | W2 | ❌ 否 |
| **M-9** | 🟠 Major | 關注 5 | W2 | ❌ 否 |
| **M-10** | 🟠 Major | 關注 5 | W1 | ❌ 否 |
| **M-11** | 🟠 Major | 關注 2 | W2 | ❌ 否 |
| m-1~m-10 | 🟡 Minor | — | W3~W4 | ❌ 否 |

---

## 6. 建議下一步行動（Next Sprint 提案骨架）

### Phase 5 Sprint 提案方向（待 SD_Improving_04 詳細設計）

```
W1（P0 修復，2 週）：
  C-4: PgMemoryStore + PgPlaybookRepository asyncio 修復
  C-6: Checkpoint unique 索引改 run_id
  M-2: playbook_id 統一計算邏輯
  M-3: TokenGuardConfig + AppConfig Pydantic 驗證
  M-4: context_patterns regex 補全 + 測試
  M-6: 向量搜尋 SQL 改參數化
  M-7: pgvector HNSW index
  M-10: _run_cache TTL

W2~W3（架構修復，4 週）：
  C-1: PlaybookRunner 瘦身至 ≤ 150 行（遷移核心邏輯至 Kernel + Plugin）
  C-2: 制定 legacy 路徑 deprecation timeline
  C-3: _runner_compat.py 明確化（或刪除）
  M-1: AutoResumeService._resolve_start() 實裝（checkpoint restore）
  M-5: Token Guard 邏輯完全遷移至 TokenGuardPlugin
  M-8: Checkpoint 邊界條件測試補全

W4（三層架構，4 週）：
  C-5: 新增 Project / GoalTask / TaskRecord / ExecutionItem 表
      對應 alembic migration + repository 層
      三層外鍵設計 + pgvector embedding 欄位（TaskRecord / ExecutionItem）
  UI 管理介面設計文件（docs/07_design/）
```

---

## 7. 四方審議決策表

> **審議程序**：各方閱讀本文件後，獨立填寫 Verdict 欄。
> 4 方皆 APPROVE（含 with conditions）方可通過。任一方 REJECT 需修訂後重審。

| 角色 | Verdict | 主要條件 / 意見 | 簽核日期 |
|------|---------|----------------|---------|
| **Architect** | ✅ APPROVE WITH CONDITIONS | 1. C-1 修復時須明確 _runner_compat.py 終點（臨時過渡 W4 末刪除）；2. C-2 deprecation 須加測試驗證 DeprecationWarning；3. W1 工作量應分 P0/P1 梯次，C-1 遷移評估需 4 週 | 2026-05-15 |
| **SA** | ✅ APPROVE WITH CONDITIONS | 1. C-5 三層架構決策前置：推延至 SD_Improving_05；2. M-1 新路徑 checkpoint 恢復須於 W2 同步實裝，舊路徑保留至完整測試；3. 若 C-5 推延，M-8 現有 4 邊界列表充分 | 2026-05-15 |
| **SD** | ✅ APPROVE WITH CONDITIONS | 1. C-4 建立 pg_async_utils.py 共用 _run_async()+_make_retry() 供三個 repository；2. C-6 migration 採 CREATE UNIQUE INDEX CONCURRENTLY 避免全表鎖；3. M-2 需設置 storage.mode 決定 dual-id mapping 層 | 2026-05-15 |
| **QA** | ✅ APPROVE WITH CONDITIONS | 1. C-4 須新增 test_pg_async_compat.py（FastAPI 上下文 + pytest-asyncio 場景）；2. C-6 migration 驗證前須確認 0002_m4_run_id_not_null.py 是否已刪舊 index；3. C-5 高風險，三層架構對 repository interface 影響評估須完成後才能排入 Sprint | 2026-05-15 |

### QA 預審查重點（供 QA 填寫）

QA 審查時請特別核查以下項目：

1. **C-4**（PgMemoryStore asyncio）：是否有已存在的 asyncio runtime 測試場景？
2. **C-6**（Checkpoint 1:1 約束）：alembic `0001_initial.sql` 實際的 constraint 定義是否確認？
3. **M-3**（TokenGuardConfig 驗證）：現有測試是否會因新增 validator 而破壞？
4. **M-8**（邊界條件測試）：補測估計工期是否與 M-1 ~M-11 整體 test budget 衝突？
5. **C-5**（三層架構）：新增 4 張 table + alembic migration 對現有 1,057 tests 的影響評估？

---

## 8. 本文件參考的計畫/文件

| 文件 | 狀態 | 關聯 |
|------|------|------|
| [SD_Improving_03_Phase4_Real_Switch.md](SD_Improving_03_Phase4_Real_Switch.md) v1.1 | Implemented | 本文件是其稽核後審查 |
| [SD_Improving_03_Retrospective.md](../05_development/SD_Improving_03_Retrospective.md) | Closed | Sprint 復盤，基線 1,006 passed |
| [SD_Improving_03_v1.0_Triple_Review.md](../05_development/SD_Improving_03_v1.0_Triple_Review.md) | 歷史 | v1.0 三方 REJECT 參考 |
| [gate_audit.md](../05_development/gate_audit.md) | Active | G3/G5 已通過 |
| [risk_log.md](../05_development/risk_log.md) | Active | R-1~R-16 風險追蹤 |

---

**文件元數據**：
- 審查日期：2026-05-15
- 三方審查：Architect（獨立）/ SA（獨立）/ SD（獨立）
- 彙整人：Claude Code（工程助理）
- 四方審議：待排期（建議 2026-05-16~2026-05-17）
- 下一步：四方審議通過 → 產出 SD_Improving_04（Phase 5 Sprint 規劃）
