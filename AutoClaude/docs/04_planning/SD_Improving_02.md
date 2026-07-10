# SD_Improving_02：DAL 抽象、TDD 重構步驟與里程碑（Part 2／2）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.2** |
| 建立日期 | 2026-05-07 |
| 最後更新 | 2026-05-12（v1.2：§2.6 / §4 加 Phase 4 補完 banner；Phase 4 實際工程由 SD_03 v1.1 承接） |
| v1.1 更新 | 2026-05-07（對齊 SD_Improving_01.md v1.1，補 GotoCounterPlugin、Gate G1~G5、Frozen Surface 9 項、Port 契約測 ABC、snapshot 7 欄擴增、CLI/LOC budget CI、Q1~Q5 owner+時限） |
| 文件類型 | 系統設計（System Design） |
| 對應目錄 | `docs/04_planning/` |
| 適用 AISDLC 版本 | v0.09+ |
| 前置文件 | [SD_Improving_01.md](SD_Improving_01.md) **v1.1**（必讀）、[SD_Improving_03.md](SD_Improving_03_Phase4_Real_Switch.md) v1.1（Phase 4 補完） |
| 文件狀態 | Active v1.2（Phase 4 由 SD_03 完成；G3 ✅ 三方簽核 2026-05-12） |
| 維護者 | Chief Architect / Lead QA / PM |

---

## 0. 文件導讀

本文是 **AutoClaude 微核心化重構** 的第 2 份藍圖，承接 Part 1 的微核心藍圖，鎖定 4 件事：

1. **DAL（Data Access Layer）抽象規格**：為未來 PostgreSQL 接入鋪路。
2. **TDD 6 階段重構步驟**：以 Strangler Fig 模式逐步替換，全程 558 tests 保持 green。
3. **風險矩陣與回滾策略**：每階段的 fail-safe。
4. **里程碑驗收條件**：定義「重構完成」的具體 DoD。

---

## 1. 雙人續論：DAL 介面設計

### 1.1 為什麼需要 DAL？

<thinking>
**Architect**：當前 AutoClaude 有 3 個獨立的持久化來源，全部寫死在本地檔案：

1. **Checkpoint**（`{checkpoint_dir}/{stem}.checkpoint.json`）——`CheckpointManager` 直接 `json.dump`。
2. **Knowledge Base**（`{checkpoint_dir}/failure_knowledge_base.jsonl`）——`FailureKnowledgeBase` 直接 JSONL append。
3. **Evolved Playbook**（`evolved_{原檔名}.yaml`）——`PlaybookEvolver` 直接 `yaml.safe_dump`。

問題是：

- **無交易（Transaction）保證**：演化版 Playbook 寫入一半時崩潰，會留下半截 YAML。
- **無查詢能力**：要查「過去 30 天哪個 step_id 最常 escalate」必須掃 `escalation_dump_*.md` 檔案系統。
- **無多 Session 並發保護**：兩個 AutoClaude 實例同時跑同一個 Playbook（雖罕見但可能）會 race。
- **無時序索引**：所有歷史紀錄是檔案散落，分析必須手寫 grep 腳本。
- **不適合雲端部署**：未來若要把 AutoClaude 跑在 GitHub Actions / Cloud Run 上，本地檔案系統是無狀態的——重啟即遺失。

接 PostgreSQL 是必然的，但**現在不能直接接**——因為目前邏輯與檔案 IO 緊耦合（`CheckpointManager.save()` 直接 `tmp_p.replace(p)`）。

**結論**：先抽出 Repository 介面，讓 Kernel 與 Plugin 都依賴介面而非具體實作。後端是 File 還是 Postgres，由 `main.py` 的 DI 注入決定。
</thinking>

<thinking>
**QA**：DAL 抽象我支持，但有兩個必須鎖死的條件：

**條件 A：介面契約必須是「行為對等」而非「IO 對等」**

不要把 `CheckpointManager.save(checkpoint, path)` 直接抄成 `IStateRepository.save(checkpoint, path)`——`path` 是檔案系統概念，PostgreSQL 沒有 path。介面應該是 `save_checkpoint(playbook_id, checkpoint)`，由實作層決定如何路由到檔案 or row。

**條件 B：介面測試必須跑兩遍（File backend + In-Memory backend）**

我堅持每個 IStateRepository 的測試都要跑兩個 fixture：

1. `FileStateRepository`（真實檔案，與舊 CheckpointManager 行為等價）
2. `InMemoryStateRepository`（測試用，純 dict）

如果這兩個 backend 在同一份測試下都能 pass，代表抽象是穩的。將來 PostgreSQL backend 接入時，新增第 3 個 fixture 跑同一份測試即可——這就是 **Liskov Substitution Principle** 的測試保證。
</thinking>

### 1.2 DAL 三大介面契約

#### 1.2.1 IStateRepository（取代 CheckpointManager）

```python
# autoclaude/core/ports/state_repository.py
from __future__ import annotations
from typing import Protocol, Optional
from datetime import datetime
from ..models import PlaybookCheckpoint  # 不變，仍用既有 dataclass


class IStateRepository(Protocol):
    """Checkpoint 持久化的抽象 Port。

    後端可為：
    - FileStateRepository（過渡期，行為等價於 CheckpointManager）
    - InMemoryStateRepository（單元測試用）
    - PgStateRepository（Phase 6+ 接入 PostgreSQL）
    """

    def save_checkpoint(
        self, playbook_id: str, checkpoint: PlaybookCheckpoint
    ) -> None:
        """原子性儲存 checkpoint。
        Raises:
            StateRepositoryError: 持久化失敗（呼叫方應 fallback 至 fresh=True）。
        """
        ...

    def load_checkpoint(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        """載入 checkpoint。檔案不存在 / 損毀 / schema 不相容時回傳 None。"""
        ...

    def clear_checkpoint(self, playbook_id: str) -> None:
        """清除 checkpoint（步驟完成或 --fresh 時呼叫）。
        若不存在不視為錯誤。
        """
        ...

    def schedule_resume(
        self, playbook_id: str, delay_minutes: int
    ) -> datetime:
        """設定排程繼續時間，回傳預計恢復時刻。"""
        ...



# ── v1.1：拆出 IQueryableStateRepository 子介面（ISP / LSP 修正）─────
# 原 v1.0 將 list_recent_checkpoints 放在 IStateRepository 並允許 File
# backend 拋 NotImplementedError，這違反 LSP（subtype 不能拒絕基底承諾）。
# v1.1 改為「核心介面只放最小必要操作；查詢能力另設子介面」，避免破壞契約測。
class IQueryableStateRepository(IStateRepository, Protocol):
    """提供進階查詢能力的擴展介面。

    任何實作 IQueryableStateRepository 的後端，必須實作 list_recent_checkpoints；
    僅實作 IStateRepository 的後端則無此承諾——呼叫端透過 isinstance 判斷。

    範例：
      - FileStateRepository: 實作 IQueryableStateRepository（掃目錄即可，O(n) 但可接受）
      - PgStateRepository: 實作 IQueryableStateRepository（一行 SELECT，極快）
      - InMemoryStateRepository: 僅實作 IStateRepository（測試夾具，不需查詢）
    """

    def list_recent_checkpoints(
        self, since: Optional[datetime] = None, limit: int = 50
    ) -> list[PlaybookCheckpoint]:
        """列出近期 checkpoint，依 saved_at 倒序排列。"""
        ...


class StateRepositoryError(Exception):
    """持久化失敗的統一例外。"""
```

**playbook_id 設計原則**：

- 過渡期：`playbook_id = Path(playbook_path).stem`（與舊 `CheckpointManager` 命名一致）。
- PostgreSQL 期：`playbook_id = sha256(canonical_yaml(playbook))[:16]`（內容尋址，避免重命名導致 checkpoint 遺失）。
- **介面不暴露 path**——這是 leaky abstraction 的根源。

#### 1.2.2 IMemoryStore（取代 FailureKnowledgeBase）

```python
# autoclaude/core/ports/memory_store.py
from __future__ import annotations
from typing import Protocol, Optional


class IMemoryStore(Protocol):
    """跨 Session 失敗知識庫的抽象 Port。"""

    def query(self, error_signature: str) -> Optional[dict]:
        """查詢已知錯誤模式。"""
        ...

    def query_strategy_priority(self, error_class: str) -> list[str]:
        """根據歷史成功率回傳策略優先序。"""
        ...

    def record_success(
        self, error_signature: str, strategy: str,
        step_id: str, error_class: str = "unknown",
    ) -> None:
        """記錄成功修正。"""
        ...

    def record_escalation(
        self, error_signature: str, tried_strategies: list[str], step_id: str,
    ) -> None:
        """記錄 ESCALATION（所有策略都失敗）。"""
        ...

    # ── 進階查詢（為未來 dashboard 鋪路）──
    def stats_by_error_class(self) -> dict[str, dict]:
        """各 error_class 的成功率統計。"""
        ...
```

#### 1.2.3 IPlaybookRepository（取代直接 yaml.safe_load/dump）

```python
# autoclaude/core/ports/playbook_repository.py
from __future__ import annotations
from typing import Protocol, Optional
from ..models import Playbook


class IPlaybookRepository(Protocol):
    """Playbook 與其演化版本的持久化 Port。"""

    def load(self, playbook_id: str) -> Playbook:
        """載入原始 Playbook。"""
        ...

    def persist_mutation(
        self, playbook_id: str, playbook: Playbook,
    ) -> None:
        """儲存突變後的 Playbook（覆寫原檔，作為「事實當前快照」）。"""
        ...

    def persist_evolution(
        self, original_id: str, evolved: Playbook,
        generation: int, mutation_log: list[str],
    ) -> str:
        """儲存演化版本，回傳新 playbook_id。
        File backend：寫成 evolved_{generation}_{原檔名}.yaml
        Postgres backend：插入 playbook_versions 表，回傳 UUID
        """
        ...

    def list_evolution_history(
        self, playbook_id: str
    ) -> list[tuple[int, str, str]]:
        """回傳演化歷史 [(generation, evolved_id, timestamp), ...]。"""
        ...
```

### 1.3 PostgreSQL Schema 設計（前瞻規格）

```sql
-- 為 PostgreSQL backend 預先設計的 schema（Phase 6+ 才落地）
-- 不在當前重構範圍內，但 IStateRepository 介面必須兼容此 schema

CREATE TABLE playbook_runs (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id     TEXT NOT NULL,
    project         TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN
                      ('running', 'success', 'escalated', 'halted', 'interrupted')),
    -- JSONB 保留彈性，避免欄位爆炸
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX idx_runs_playbook ON playbook_runs(playbook_id);
CREATE INDEX idx_runs_status   ON playbook_runs(status);

CREATE TABLE checkpoints (
    checkpoint_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               UUID NOT NULL REFERENCES playbook_runs(run_id),
    playbook_id          TEXT NOT NULL,
    step_idx             INT NOT NULL,
    step_id              TEXT NOT NULL,
    total_steps          INT NOT NULL,
    saved_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    scheduled_resume_at  TIMESTAMPTZ,
    peak_token_pct       FLOAT NOT NULL DEFAULT 0,
    -- 計數器（Gap-042 / Gap-048）
    counters             JSONB NOT NULL DEFAULT '{
        "goto": {}, "inject_before": {}, "skip_to": {}, "step_evolution": {}
    }'::jsonb,
    completed_step_log   TEXT[] NOT NULL DEFAULT '{}',
    completed_step_ids   TEXT[] NOT NULL DEFAULT '{}',
    failure_history      JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_step_attempt  INT NOT NULL DEFAULT 0,
    last_correction_prompt TEXT NOT NULL DEFAULT ''
);
-- 同一 playbook_id 只保留最新 checkpoint（UPSERT）
CREATE UNIQUE INDEX idx_ck_playbook ON checkpoints(playbook_id);

CREATE TABLE knowledge_entries (
    entry_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_class     TEXT NOT NULL,
    error_signature TEXT NOT NULL,
    -- 一個 signature 可能對應多筆成功記錄（不同策略都成功）
    successful_strategy TEXT,
    tried_strategies    TEXT[] NOT NULL DEFAULT '{}',
    step_id         TEXT NOT NULL,
    outcome         TEXT NOT NULL CHECK (outcome IN ('success', 'escalation')),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_kb_signature ON knowledge_entries(error_class, error_signature);
CREATE INDEX idx_kb_recent    ON knowledge_entries(recorded_at DESC);

CREATE TABLE playbook_versions (
    version_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_playbook_id TEXT NOT NULL,
    generation          INT NOT NULL,
    yaml_content        TEXT NOT NULL,
    mutation_log        TEXT[] NOT NULL DEFAULT '{}',
    parent_version_id   UUID REFERENCES playbook_versions(version_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_pv_playbook ON playbook_versions(original_playbook_id, generation);
```

### 1.4 後端切換機制（Config-Driven DI）

```python
# autoclaude/utils/config.py（新增段落）
class StorageConfig(BaseModel):
    backend: Literal["file", "postgres"] = "file"  # 預設 file，向後相容
    file_dir: str = "checkpoints"                   # file backend 用
    postgres_dsn: Optional[str] = None              # postgres backend 用
    postgres_pool_size: int = 5

class AppConfig(BaseModel):
    # ... 既有欄位 ...
    storage: StorageConfig = Field(default_factory=StorageConfig)
```

```python
# autoclaude/main.py（重構後）
def build_kernel(cfg: AppConfig) -> PlaybookKernel:
    # DI 組裝點：唯一決定後端的位置
    if cfg.storage.backend == "file":
        state_repo = FileStateRepository(cfg.storage.file_dir)
        memory = FileMemoryStore(Path(cfg.storage.file_dir) / "kb.jsonl")
        pb_repo = FilePlaybookRepository(cfg.scripts_dir)
    elif cfg.storage.backend == "postgres":
        engine = create_async_engine(cfg.storage.postgres_dsn, ...)
        state_repo = PgStateRepository(engine)
        memory = PgMemoryStore(engine)
        pb_repo = PgPlaybookRepository(engine)
    else:
        raise ValueError(f"Unsupported backend: {cfg.storage.backend}")

    bus = EventBus()
    # 註冊所有 Plugin（順序由 config 控制）
    bus.register(TokenGuardPlugin(cfg.token_guard))
    bus.register(CheckpointPlugin(state_repo))
    bus.register(KnowledgeBasePlugin(memory))
    # ... 其他 Plugin
    return PlaybookKernel(
        executor=PtyExecutor(cfg.claude),
        evaluator=ShellEvaluator(cfg.playbook),
        brain=MinimaxBrain(cfg.minimax),
        bus=bus,
        state_repo=state_repo,
        playbook_repo=pb_repo,
    )
```

### 1.5 PostgreSQL 接入路線（前瞻，不在本次重構範圍）

| 步驟 | 動作 | 依賴 |
|------|------|------|
| P-1 | 引入 SQLAlchemy 2.0（async）+ asyncpg + Alembic | `pyproject.toml` 新增依賴 |
| P-2 | 建立 `alembic/` 目錄與初始 migration | DAL Phase 5 完成 |
| P-3 | 實作 `PgStateRepository` 通過既有 DAL 測試 | LSP 保證 |
| P-4 | 實作 `PgMemoryStore` 與 `PgPlaybookRepository` | 同上 |
| P-5 | 在 CI 加入 PG fixture（docker-compose 起 postgres:17） | infra |
| P-6 | 提供 file → pg 遷移腳本 | 一次性工具 |

> **Architect**：注意——SQLAlchemy 與 asyncpg 是 Phase 6+ 才落地的決定，**現階段重構不引入這兩個套件**。我們只負責「介面準備好」即可。

---

## 2. TDD 重構執行步驟（Strangler Fig 6 階段）

### 2.1 階段總覽（v1.1：補人日 / FTE / Gate / 簽核人）

> **PM 必要修改 #1**：v1.0 僅有粗估週次，無法換算 sprint capacity。v1.1 改為「Phase × 週次區間 × 人日(PD) × FTE × 對應 Gate × 簽核人」六欄總表。

| Phase | 週次 | 人日(PD) | FTE | 主要交付 | **對應 Gate**（01 v1.1 §3.13.2） | **簽核人** |
|-------|------|---------|-----|---------|------------------------------------|-----------|
| Phase 0：Equivalence Test 基準線 | W1 | 4 ~ 6 PD | 1.0 | 13 golden fixtures + snapshot test + CLI 相容性測試 + `check_loc_budget.py` | **G1**（前置：Phase 1 進入前） | Architect + QA + PM |
| Phase 1：Port 介面抽出 | W2 | 3 ~ 5 PD | 1.0 | 3 Port + 3 Adapter | （G1 已通過） | Architect + QA |
| Phase 2：Kernel + EventBus 骨架 | W3-W4 | 8 ~ 12 PD | 1.0 | Kernel < 250 行 + EventBus + IResolutionPolicy + 50~80 unit tests | **G2**（進入 Phase 3 前） | Architect + QA |
| Phase 3：12 Plugin + 1 Domain Service 遷移 | W5-W11 | 25 ~ 40 PD | 1.5 ~ 2.0 | 13 個獨立 PR（含 GotoCounterPlugin） | （Phase 3 末 → G3 前置） | Architect + QA（每 PR 雙簽） |
| Phase 4：Facade 切換 | W12 | 4 ~ 6 PD | 1.0 | runner < 300 行 + Frozen Surface 9 項 shim 完整 | **G3**（最高風險，**PM 強制簽核**） | Architect + QA + **PM** |
| Phase 5：DAL File backend 抽出 | W13 | 5 ~ 8 PD | 1.0 | File* + InMemory* + LSP ABC 契約測 | **G4** | Architect + QA |
| Phase 6：PostgreSQL backend（選配） | W15+ | 10 ~ 15 PD | 1.0 | PG* + Alembic + docker-compose CI | **G5** | PM + Stakeholder |

**總工時估計**：核心重構（Phase 0~5）= **49 ~ 77 PD**，FTE 1.0 → 約 **10 ~ 16 週**；FTE 2.0 並行（Phase 3 期間）→ 約 **12 ~ 14 週日曆週**。Phase 6 為選配，當業務需求觸發時再排期。

**關鍵路徑（Critical Path）**：Phase 0 → Phase 2 → Phase 3 (#7 TokenGuardPlugin → #11 EvolutionPlugin → #13 MutationApplyService) → Phase 4。任一節點 slip 直接影響後續；Phase 1 與 Phase 5 可一定程度並行於 Phase 3 之後段。

**Gate 對齊規則**：
- 每個 Gate 通過後，於 git tag `gate/G{N}-passed` 並更新 [gate_audit.md](../05_development/gate_audit.md)（首次建立交給 Phase 0）
- Gate G3 為唯一**PM 強制簽核**節點；任何試圖繞過 G3 的 PR 將被 QA 直接 revert

### 2.2 Phase 0：建立 Equivalence Test 基準線

**目標**：在動任何重構之前，建立**「給定相同輸入，產生相同輸出」**的黃金基準。

**為什麼這是 Phase 0**：

> **QA**：如果連基準都沒對齊，後面 Phase 1+ 的「保持 558 tests green」根本無法保證等價性——測試可能 green 但行為已偏離。基準線必須先打。

#### 0.1 建立 Golden Fixture（v1.1：擴充至 13 個，補 Gap-042/048/049 場景）

> **QA 必要修改 #1**：v1.0 的 10 個 fixture **未覆蓋 Gap-042（goto/inject_before/skip_to 計數器跨 TOKEN_HALT 持久化）、Gap-048（per-step 演化次數跨 ESC+F12）、Gap-049（max_goto_per_step 配置覆寫）**，無法保證 byte-level 等價。v1.1 補上 11~13 號 fixture。

```python
# tests/equivalence/fixtures.py（新增）
GOLDEN_PLAYBOOKS = [
    # v1.0 既有 10 個（覆蓋基本場景）
    "tests/equivalence/fixtures/01_simple_2_step.yaml",
    "tests/equivalence/fixtures/02_with_correction.yaml",
    "tests/equivalence/fixtures/03_with_mutation.yaml",
    "tests/equivalence/fixtures/04_token_halt_resume.yaml",
    "tests/equivalence/fixtures/05_evolution_inject.yaml",
    "tests/equivalence/fixtures/06_goal_synthesis.yaml",
    "tests/equivalence/fixtures/07_goto_step.yaml",
    "tests/equivalence/fixtures/08_skip_to.yaml",
    "tests/equivalence/fixtures/09_conditional.yaml",
    "tests/equivalence/fixtures/10_full_e2e_dry_run.yaml",
    # v1.1 新增 3 個（鎖死 Gap-042/048/049 byte-level 等價）
    "tests/equivalence/fixtures/11_goto_counter_token_halt.yaml",      # Gap-042
    "tests/equivalence/fixtures/12_evolution_counter_esc_f12.yaml",     # Gap-048
    "tests/equivalence/fixtures/13_max_goto_per_step_override.yaml",    # Gap-049
]
```

**11_goto_counter_token_halt.yaml 場景設計**：3 步 playbook，第 2 步觸發 GOTO_STEP 回跳第 1 步，連續 2 次後觸發 TOKEN_HALT；驗證 `goto_counter` 在 checkpoint 中正確持久化、resume 後計數不歸零、第 3 次跳轉受 `max_goto_per_step` 阻擋。

**12_evolution_counter_esc_f12.yaml 場景設計**：模擬演化步驟 + ESC+F12 中斷；驗證 `step_evolution_counter` 跨 Session 完整保留、resume 後不超過 `max_evolutions` 上限。

**13_max_goto_per_step_override.yaml 場景設計**：`config.yaml` 設定 `playbook.max_goto_per_step: 5`；驗證 GotoCounterPlugin 讀取覆寫值、第 6 次回跳被阻擋。

#### 0.2 撰寫 Equivalence Snapshot Test（v1.1：snapshot 擴增至 11 個欄位，byte-level 比對）

> **QA 必要修改 #2**：v1.0 snapshot 僅 4 個欄位（`step_log` / `completed_steps` / `halt_for_token` / `evolved_playbook_path`），**未涵蓋跨 Session 狀態**（`goto_counter` / `step_evolution_counter` 等），無法偵測「行為等價但內部偏移」。v1.1 擴增 7 個跨 Session 狀態欄並改為 deterministic JSON sort_keys 比對。

```python
# tests/equivalence/test_runner_snapshot.py（新增）
import json
import pytest
from autoclaude.execution.playbook_runner import PlaybookRunner

@pytest.mark.parametrize("pb_path", GOLDEN_PLAYBOOKS)
def test_runner_produces_stable_snapshot(pb_path, snapshot_dir):
    """確保現有 PlaybookRunner 在 dry_run 模式下產生穩定的執行軌跡。
    每個 playbook 輸出 (step_log, mutation_log, completed_step_ids,
    peak_token_pct) snapshot，與 fixture/{name}.snapshot.json 比對。
    """
    runner = PlaybookRunner(cfg, minimax_mock, hotkey, dry_run=True)
    result = runner.run(pb_path, fresh=True)

    # v1.1：actual 必須包含所有可觀察 + 跨 Session 狀態
    actual = {
        # v1.0 既有 4 欄
        "step_log":              result.step_log,
        "completed_steps":       result.completed_steps,
        "halt_for_token":        result.halt_for_token,
        "evolved_playbook_path": result.evolved_playbook_path,
        # v1.1 新增 7 欄（鎖死 Gap-009/012/041/042/048）
        "mutation_log":            result.mutation_log,            # Gap-009/012
        "completed_step_ids":      result.completed_step_ids,      # Gap-041
        "goto_counter":            result.checkpoint.goto_counter,           # Gap-042
        "inject_before_counter":   result.checkpoint.inject_before_counter,  # Gap-042
        "skip_to_counter":         result.checkpoint.skip_to_counter,        # Gap-042
        "step_evolution_counter":  result.checkpoint.step_evolution_counter, # Gap-048
        "failure_history":         result.checkpoint.failure_history,        # Gap-007-A
    }

    # v1.1：採 JSON sort_keys 達 byte-level deterministic 比對
    actual_json = json.dumps(actual, sort_keys=True, ensure_ascii=False, indent=2)
    expected_json = (snapshot_dir / f"{Path(pb_path).stem}.snapshot.json").read_text(encoding="utf-8")
    assert actual_json == expected_json, f"行為不一致（byte-level）: {pb_path}"
```

#### 0.3 CLI 相容性測試（v1.1 新增｜PM 必要修改 #4）

> **PM 必要修改**：01 v1.1 §3.11 承諾 CLI 100% 向後相容（9 場景），但 v1.0 未在 02 規劃對應測試。v1.1 將 `tests/cli/test_cli_compatibility.py` **併入 Phase 0 交付**。

```python
# tests/cli/test_cli_compatibility.py（Phase 0 新增）
import subprocess

CLI_GOLDEN_SCENARIOS = [
    # 9 個 CLI 場景（對齊 01 v1.1 §3.11）
    {"args": ["python", "-m", "autoclaude", "fixtures/01_simple.yaml"], "expected_exit": 0},
    {"args": ["python", "-m", "autoclaude", "fixtures/01_simple.yaml", "--config", "config.local.yaml"], "expected_exit": 0},
    {"args": ["python", "-m", "autoclaude", "fixtures/01_simple.yaml", "--fresh"], "expected_exit": 0},
    {"args": ["python", "-m", "autoclaude", "fixtures/01_simple.yaml", "--dry-run"], "expected_exit": 0},
    {"args": ["python", "-m", "autoclaude", "fixtures/04_token_halt.yaml"], "expected_exit": 3},  # halted
    {"args": ["python", "-m", "autoclaude", "fixtures/escalated.yaml"], "expected_exit": 2},      # escalated
    {"args": ["python", "-m", "autoclaude", "nonexistent.yaml"], "expected_exit": 1},             # failure
    {"args": ["autoclaude", "fixtures/01_simple.yaml"], "expected_exit": 0},                       # entrypoint
    {"args": ["python", "-m", "autoclaude", "--help"], "expected_exit": 0},                       # help
]

@pytest.mark.parametrize("scenario", CLI_GOLDEN_SCENARIOS)
def test_cli_backward_compatibility(scenario, tmp_path):
    """確保 CLI 9 個場景在 Phase 0 ~ Phase 6 期間完全相容。"""
    result = subprocess.run(scenario["args"], cwd=tmp_path, capture_output=True)
    assert result.returncode == scenario["expected_exit"]
```

#### 0.4 行數預算 CI 工具（v1.1 新增｜PM 必要修改 #4）

> **PM 必要修改**：01 v1.1 §3.13.1 設定行數預算（Kernel ≤ 250 / Plugin ≤ 250 / 總增量 ≤ +20%），但 v1.0 未規劃 CI 工具。v1.1 將 `tools/check_loc_budget.py` **併入 Phase 0 交付**並啟用 CI gate。

```python
# tools/check_loc_budget.py（Phase 0 新增）
"""行數預算檢查器：CI 整合，超預算 fail。"""
BUDGETS = {
    "autoclaude/core/kernel.py":              250,   # Kernel
    "autoclaude/core/event_bus.py":           200,   # EventBus + DefaultResolutionPolicy
    "autoclaude/plugins/*.py":                250,   # 每個 Plugin
    "autoclaude/core/services/mutation/*.py": 80,    # 每個 IMutationStrategy
}
TOTAL_INCREASE_LIMIT = 1.20  # 重構後總行數 ≤ 原始 × 1.20

def main():
    violations = []
    for pattern, limit in BUDGETS.items():
        for path in glob.glob(pattern):
            loc = count_loc(path)  # 排除空行 / 純註解行
            if loc > limit:
                violations.append(f"{path}: {loc} > {limit}")
    # 總量檢查
    total = sum(count_loc(p) for p in glob.glob("autoclaude/**/*.py", recursive=True))
    baseline = read_baseline()  # 從 .loc_baseline 讀取 Phase 0 起始基準
    if total > baseline * TOTAL_INCREASE_LIMIT:
        violations.append(f"TOTAL: {total} > {baseline}×1.20={int(baseline*1.20)}")
    if violations:
        print("\n".join(violations)); sys.exit(1)
```

CI 整合（`.github/workflows/autoclaude-ci.yml` 新增 step）：
```yaml
- name: Check LOC budget
  run: python tools/check_loc_budget.py
```

**Phase 0 驗收條件（DoD，v1.1 擴充）**：

**新增交付物**：
- [ ] `tests/equivalence/` 目錄建立完成，含 **≥ 13 個 golden playbook**（v1.1 新增 11/12/13）
- [ ] 每個 fixture 都有 `*.snapshot.json` 對齊基準（**byte-level deterministic**，JSON sort_keys）
- [ ] **`tests/cli/test_cli_compatibility.py` 含 9 個 CLI 場景**全綠（PM 必要修改 #4）
- [ ] **`tools/check_loc_budget.py` 建立並整合 CI gate**（PM 必要修改 #4）
- [ ] `.loc_baseline` 檔案建立（記錄 Phase 0 起始行數，作為 +20% 上限基準）

**snapshot 欄位完整性檢查**：
- [ ] snapshot 包含 v1.1 規定的 11 個欄位（v1.0 的 4 欄 + v1.1 新增 7 欄）
- [ ] Gap-042/048/049 三個 fixture 各自驗證對應計數器欄位 byte-level 一致

**測試門檻**：
- [ ] `pytest tests/equivalence/ -v` 全綠（13 + ≥7 場景測試）
- [ ] `pytest tests/cli/ -v` 全綠（9 場景）
- [ ] `pytest tests/ -q` 仍然 558 + 新測試全綠（總數約 580+）
- [ ] **`pytest tests/test_gap*.py -v` 全綠**（17 個 Gap 測試檔，Gap-009~049 不退化基準，01 v1.1 §3.12）

**Gate 與簽核**：
- [ ] `tools/check_loc_budget.py` 在 main 分支首次執行通過
- [ ] PR commit message 標註 `[Phase 0]` + `[Gate G1 前置]`
- [ ] **Gate G1 簽核完成**（Architect + QA + PM 三方）後，方可進入 Phase 1

### 2.3 Phase 1：抽出 Port 介面（IExecutor / IEvaluator / IBrain）

**目標**：把 PlaybookRunner 對 Pty / Evaluator / Minimax 的呼叫，改為對 Protocol 介面的呼叫。**不改變行為，只改變類型**。

#### 1.1 建立介面檔

```python
# autoclaude/core/ports/__init__.py
# autoclaude/core/ports/executor.py
class IExecutor(Protocol):
    def execute(
        self, prompt: str, *, maintain_context: bool, timeout: int, label: str,
    ) -> "StepOutput": ...

# autoclaude/core/ports/evaluator.py
class IEvaluator(Protocol):
    def evaluate(
        self, task: PlaybookTask, output: str,
    ) -> tuple[Optional[str], str, int]: ...

# autoclaude/core/ports/brain.py
class IBrain(Protocol):
    def decide_correction(self, ...) -> Optional[CorrectionDecision]: ...
    def propose_evolution(self, ...) -> Optional[EvolutionDecision]: ...
```

#### 1.2 建立 Adapter（薄包裝）

```python
# autoclaude/infra/adapters/pty_executor.py
class PtyExecutor:  # implements IExecutor
    def __init__(self, claude_cfg: ClaudeConfig): ...
    def execute(self, prompt, *, maintain_context, timeout, label) -> StepOutput:
        # 原 PlaybookRunner._execute_prompt 的邏輯整段搬過來，無業務修改
        ...
```

#### 1.3 修改 Runner 改用介面

```python
class PlaybookRunner:
    def __init__(
        self, config, minimax_client, hotkey_handler, *,
        executor: Optional[IExecutor] = None,    # 新增，預設由 config 建構
        evaluator: Optional[IEvaluator] = None,
        brain: Optional[IBrain] = None,
        dry_run: bool = False,
    ):
        self._exec = executor or PtyExecutor(config.claude)
        self._eval = evaluator or ShellEvaluator(config.playbook)
        self._brain = brain or MinimaxBrainAdapter(minimax_client)
        # 既有屬性保留（用於 backward compat 的 facade）
```

**Phase 1 驗收條件（DoD）**：

- [ ] `autoclaude/core/ports/` 三個介面檔案建立完成。
- [ ] `autoclaude/infra/adapters/` 三個 adapter 建立並通過獨立測試。
- [ ] `PlaybookRunner.__init__` 簽章新增 3 個 keyword-only optional 參數。
- [ ] 既有 249 處測試耦合**全部不需修改**（向後相容）。
- [ ] `pytest tests/ -q` 全綠。
- [ ] Equivalence test 仍然 green（snapshot 完全一致）。

### 2.4 Phase 2：建立 Kernel + EventBus 骨架

**目標**：在 `autoclaude/core/` 新建 Kernel 與 EventBus，但**不啟用**——只跑單元測試驗證骨架正確。

#### 2.1 新增模組樹

```
autoclaude/core/
├── __init__.py
├── kernel.py              # PlaybookKernel（先做基本骨架）
├── event_bus.py           # EventBus 同步分派器
├── hookspec.py            # IHook / KernelPhase / HookContext / HookResult
├── kernel_state.py        # StepOutcome / KernelResult 等 dataclass
└── ports/                 # Phase 1 已建立
```

#### 2.2 Kernel 骨架測試（純 plugin 行為）

```python
# tests/core/test_kernel_skeleton.py（新增）
def test_kernel_emits_pre_run_event():
    bus = EventBus()
    captured = []
    class Spy:
        def name(self): return "spy"
        def subscribed_phases(self): return [KernelPhase.PRE_RUN]
        def on_event(self, ctx):
            captured.append(ctx.phase)
            return None
    bus.register(Spy())

    kernel = PlaybookKernel(
        executor=FakeExecutor(),
        evaluator=FakeEvaluator(),
        brain=FakeBrain(),
        bus=bus,
        state_repo=InMemoryStateRepository(),
        playbook_repo=InMemoryPlaybookRepository({"test": _empty_playbook()}),
    )
    kernel.run("test", fresh=True)
    assert KernelPhase.PRE_RUN in captured

def test_kernel_respects_pre_run_veto():
    """PreRunValidatorPlugin 等價測試。"""
    ...

def test_kernel_advances_step_on_success():
    ...

def test_kernel_loops_on_failure_until_max_retries():
    ...

def test_kernel_emits_on_escalation_when_convergence_says_escalate():
    ...
```

> **QA**：Phase 2 的測試**不依賴**舊 Runner，是全新的 Kernel-level 測試。我預期會新增 50-80 個測試，全部用 Fake/InMemory implementation。這些測試完成後，Kernel 的契約就鎖死了。

**Phase 2 驗收條件（DoD）**：

- [ ] `autoclaude/core/` 5 個檔案建立完成，每檔 < 250 行。
- [ ] `tests/core/` 新增 ≥ 50 個 Kernel-level 測試。
- [ ] Kernel 在所有 fake plugin 下行為符合 Part 1 §3.4 的合約。
- [ ] **Kernel 與 PlaybookRunner 並存**，舊 Runner 完全不受影響。
- [ ] `pytest tests/ -q` 全綠（總數約 620+）。

### 2.5 Phase 3：逐一搬遷 Plugin（每個 PR 一個 Plugin，v1.1：13 列 + weekly cadence）

**目標**：將 PlaybookRunner 的橫切關注點，逐一抽出為 12 個 Plugin + 1 個 Domain Service。每個元件一個 PR，**禁止合併多個元件到同一 PR**。

> **Architect/QA 必要修改**（v1.1）：
> - **新增 GotoCounterPlugin（priority=85）**承接 Gap-042/048 計數器（原 v1.0 矩陣遺漏）
> - 順序由「測試耦合度」決定，並標註 priority 對齊 01 v1.1 §3.4.2 約定表
> - 第 #13 列 `MutationApplyService` 為 **Domain Service（Layer 2）**，由 Kernel 直接呼叫，非 Plugin

#### 搬遷順序（依「測試耦合度」由低到高，含 priority 標註）

| 順序 | 元件 | Priority（01 v1.1 §3.4.2） | 取代區段 | 既有測試影響 |
|------|------|------|----------|--------------|
| #1 | `NotificationPlugin` | 50 | `_notify` 7 處 | 低（無測試直接 patch） |
| #2 | `HotkeyPlugin` | 10 | `if self._hotkey.triggered:` 3 處 | 低 |
| #3 | `PreRunValidatorPlugin` | 5 | `PreRunValidator().validate_step` | 低 |
| #4 | `CrossStepValidatorPlugin` | 15 | `CrossStepStateValidator()` | 低 |
| #5 | `KnowledgeBasePlugin` | 50 | `record_success` / `record_escalation` 4 處 | 中 |
| **#6** | **`GotoCounterPlugin`（v1.1 新增）** | **85** | **Gap-042 / Gap-048 / Gap-049 跨 Session 計數器（goto/inject_before/skip_to/step_evolution）持久化與上限檢查** | **中** |
| #7 | `GlobalGoalAnchorPlugin` | 35 | `_prepend_global_goal*` + `_send_compact` 中 anchor | 中 |
| #8 | `TokenGuardPlugin` | 30 | `_should_compact_now` / `_send_compact` / `_handle_token_halt` | **高** |
| #9 | `CheckpointPlugin` | 90 | `_save_*_checkpoint` 3 處 | **高** |
| #10 | `ConvergencePlugin` | 65 | `monitor.evaluate(tracker)` + ESCALATE 判定 | **高** |
| #11 | `EvolutionPlugin` | 70 | `_evolver` + `_minimax_evolver` | **極高** |
| #12 | `GoalSynthesisPlugin` | 50 | GOAL_SYNTHESIS ESCALATION 補完（去重） | 極高 |
| #13 | `MutationApplyService`（**Domain Service, Layer 2**） | — | `_apply_single_mutation` 拆 7 個 IMutationStrategy（REVISE/INJECT_AFTER/INJECT_BEFORE/GOTO/SKIP_TO/DELETE/NO_OP） | 極高 |

**v1.1 weekly cadence（PM 必要修改 #2）**：

| 週次 | 交付 PR | 累計完成 | 風險級別 |
|------|---------|----------|---------|
| W5 | #1 NotificationPlugin、#2 HotkeyPlugin、#3 PreRunValidatorPlugin | 3/13 | 低 |
| W6 | #4 CrossStepValidatorPlugin、#5 KnowledgeBasePlugin、#6 GotoCounterPlugin | 6/13 | 低-中 |
| W7 | #7 GlobalGoalAnchorPlugin、#8 TokenGuardPlugin | 8/13 | 中-高 |
| W8 | #9 CheckpointPlugin | 9/13 | 高 |
| W9 | #10 ConvergencePlugin | 10/13 | 高 |
| W10 | #11 EvolutionPlugin | 11/13 | 極高 |
| W11 | #12 GoalSynthesisPlugin、#13 MutationApplyService | 13/13 | 極高 |

**節奏規則**：
- W5 ~ W6 為「熱身週」，每週 3 個低風險 Plugin
- W7 ~ W8 進入「精準週」，每週 1 ~ 2 個高風險元件
- W9 ~ W11 進入「肉搏週」，每週 1 個極高風險元件，需資深開發者
- 任一 PR 無法在當週收斂（連續 2 工作天無法綠燈），即觸發回滾並順延一週

#### 每個 Plugin PR 的標準工作流程（TDD Red-Green-Refactor）

```
[Red 階段]
  1. 在 tests/plugins/test_xxx_plugin.py 寫 Plugin 行為測試
  2. 跑 pytest tests/plugins/test_xxx_plugin.py → FAIL（Plugin 還不存在）

[Green 階段]
  3. 在 autoclaude/plugins/xxx.py 實作 Plugin
  4. 跑 pytest tests/plugins/test_xxx_plugin.py → PASS
  5. 跑 pytest tests/ -q → 558+ tests PASS（其他測試不變）

[Refactor 階段（關鍵）]
  6. 在 PlaybookRunner 中註冊新 Plugin（透過內部 EventBus）
  7. 把舊邏輯（如 _notify 直接呼叫）改為 emit event
  8. 舊 _notify 方法保留為「無操作 stub」（為了 backward compat）
  9. 跑 pytest tests/ -q → 558+ tests 仍然 PASS
  10. Equivalence test 仍然 green
```

#### 範例：PR #1 `NotificationPlugin`

```python
# autoclaude/plugins/notification.py
class NotificationPlugin:
    def __init__(self, enabled: bool = True):
        self._enabled = enabled

    def name(self) -> str:
        return "notification"

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.ON_ESCALATION,
            KernelPhase.ON_EVOLUTION,
            KernelPhase.POST_RUN,
        ]

    def on_event(self, ctx: HookContext) -> Optional[HookResult]:
        if ctx.phase == KernelPhase.ON_ESCALATION:
            notify_escalation(...)
        elif ctx.phase == KernelPhase.ON_EVOLUTION:
            notify("AutoClaude — Playbook 自動演化", ...)
        elif ctx.phase == KernelPhase.POST_RUN:
            notify("AutoClaude — 完成", ...)
        return None
```

```python
# 在 PlaybookRunner.__init__ 新增：
if self._internal_bus is None:
    self._internal_bus = EventBus()
self._internal_bus.register(NotificationPlugin(enabled=cfg.notification.enabled))

# 在 _save_escalation_dump 結尾改為：
self._internal_bus.emit(HookContext(
    phase=KernelPhase.ON_ESCALATION,
    playbook=playbook, task=task, payload={"dump": _dump},
))
# self._notify(...) ← 移除直接呼叫
```

**Phase 3 驗收條件（DoD，每個 Plugin PR，v1.1 擴充）**：

**檔案 / 測試（每個 PR 必過）**：
- [ ] Plugin 檔案 ≤ **250 行**（IMutationStrategy ≤ 80 行；對齊 01 v1.1 §3.13.1）
- [ ] **`tools/check_loc_budget.py` 通過**（CI gate）
- [ ] Plugin 有 ≥ 10 個獨立單元測試
- [ ] Plugin 宣告 `priority(): int` 並對齊 01 v1.1 §3.4.2 約定表
- [ ] PlaybookRunner 對應的舊邏輯已委派為 emit event

**測試門檻（每個 PR 必過）**：
- [ ] `pytest tests/ -q` 全綠（含 Equivalence + 既有 558 + Plugin 新測試）
- [ ] **`pytest tests/test_gap*.py -v` 全綠**（17 個 Gap 測試檔，01 v1.1 §3.12 不退化清單）
- [ ] **`pytest tests/equivalence/ -v` byte-level 一致**（11 欄 snapshot 對齊）
- [ ] **Frozen Surface 9 項簽章未變動**（01 v1.1 §3.10）

**Plugin 特定驗證**：
- [ ] **#6 GotoCounterPlugin PR**：必須通過 `tests/equivalence/fixtures/{11,12,13}_*.yaml` 三個 Gap-042/048/049 場景
- [ ] **#9 CheckpointPlugin PR**：必須通過 `goto_counter` / `step_evolution_counter` 跨 Session round-trip 測試
- [ ] **#11 EvolutionPlugin PR** 完成後，可解凍 `_evolver` / `_minimax_evolver` 兩個 Frozen Surface 成員（標記 `@deprecated(version="2.0")`）
- [ ] **#13 MutationApplyService PR**：7 個 IMutationStrategy 各 ≤ 80 行，每個有獨立測試

**PR 流程**：
- [ ] PR description 標註 `[Phase 3 / 元件 N / priority=X]` 與「取代了哪些原 PlaybookRunner 行數」
- [ ] Code Review 由 **Architect 與 QA 雙簽**
- [ ] **Phase 3 末（W11 結束）→ Gate G2 簽核完成**（Architect + QA），方可進入 Phase 4

### 2.6 Phase 4：Facade 切換（v1.1：Frozen Surface 9 項完整 + 解凍排程 + G3 PM 強制簽核）

> ⚠️ **v1.2 補充：Phase 4 實際完成由 SD_03 補完**
> 本節描述為原始設計規格。Phase 4 Facade 真正切換（Kernel 委派 + DAL 接通生產路徑）由 [SD_Improving_03.md](SD_Improving_03_Phase4_Real_Switch.md) **v1.1** 獨立 sprint（5 週 / 27~36 PD / G3 PM 強制簽核）實施。Gate G3 當前狀態：✅ 已完成（SD_03 v1.1 W4 末 Architect+QA+PM 三方簽核，2026-05-12），詳見 [gate_audit.md](../05_development/gate_audit.md) §1 G3。

> **🔴 v1.1 補註（Gate G3 PM 簽核時加入）**：
> Phase 4 完成 = **build_kernel() 工廠 + Kernel 路徑能跑 13 個 fixture**（並存於舊 PlaybookRunner 之側）。
> **playbook_runner.py < 300 行的目標延後至 Phase 5 末段**——原因：193 處測試耦合 `runner._private_*`，必須在 Phase 5 期間漸進解除（每 PR 解凍一個 Frozen Surface 成員 + 對應測試遷移）。任一試圖在 Phase 4 直接刪除舊邏輯都會破壞 193 處測試耦合，違反「558 + 30 必綠」承諾。
> **責任人**：Architect + QA 共同擁有
> **目標 Sprint**：Phase 5 末段（W13~W14）逐步淘汰，視測試遷移節奏調整
> **Phase 5 啟動規則**：「淨減行優先」（行數預算僅餘 15 行緩衝；任何新增即須先刪除等量舊邏輯）


**目標**：當 12 個 Plugin + 1 個 Domain Service 全部到位，把 `PlaybookRunner._run_steps` 整段替換為「呼叫 Kernel」。`PlaybookRunner` 對外簽章不變，內部完全委派。

> **QA 必要修改 #5**：v1.0 範例只示意 5 項 shim，**遺漏 4 項**（`_apply_single_mutation` / `_validate_batch_compatibility` / `_consecutive_compact_failures` / `_cfg.token_guard.enabled`）。v1.1 補齊 01 v1.1 §3.10 的 9 項 Frozen Surface 完整 shim。

> **PM 必要修改 #3**：Phase 4 是最高風險變更（Facade 切換），對應 **Gate G3 PM 強制簽核**。任何試圖跳過 PM 簽核的 PR 將被 QA 直接 revert。

```python
# autoclaude/execution/playbook_runner.py（重構後，目標 < 300 行）
class PlaybookRunner:
    """Backward-compatible facade。內部委派給 PlaybookKernel。

    保留此 class 的唯一原因：193 處測試直接耦合 runner._evaluate / runner._evolver 等
    （01 v1.1 §3.10 Frozen Private Surface 9 項）。
    Phase 5 之後逐步解凍，最終可刪除此 facade。
    """

    def __init__(self, config, minimax_client, hotkey_handler, dry_run=False):
        self._kernel = build_kernel(config, minimax_client, hotkey_handler, dry_run)
        # ── v1.1：Frozen Surface 9 項完整 shim（對齊 01 v1.1 §3.10）──
        # (1) _cfg：193 處測試含 runner._cfg.token_guard.enabled = False 等直接寫入
        self._cfg = config
        self._dry_run = dry_run
        # (2) _evaluator / _evolver / _minimax_evolver：14+9 處測試 patch
        self._evaluator = self._kernel._eval
        self._evolver = self._kernel.bus.get_plugin("evolution")._rule_evolver
        self._minimax_evolver = self._kernel.bus.get_plugin("evolution")._ai_evolver
        # (3) _consecutive_compact_failures：test_token_checkpoint.py:908 直接寫入
        # 透過 property 同步至 TokenGuardPlugin 的內部狀態
        # ...

    @property
    def _consecutive_compact_failures(self) -> int:
        """v1.1 Frozen Surface #8：對應 TokenGuardPlugin 內部計數器。"""
        return self._kernel.bus.get_plugin("token_guard")._compact_failure_count

    @_consecutive_compact_failures.setter
    def _consecutive_compact_failures(self, value: int) -> None:
        self._kernel.bus.get_plugin("token_guard")._compact_failure_count = value

    def run(self, playbook_path: str, fresh: bool = False) -> PlaybookResult:
        kernel_result = self._kernel.run(playbook_path, fresh=fresh)
        return PlaybookResult.from_kernel_result(kernel_result)

    # ── v1.1：Frozen Surface 9 項完整 shim（讓 193 處測試繼續綠）──
    # 對齊 01 v1.1 §3.10：每項標註引用次數與解凍 Phase

    def _evaluate(self, task, output):  # Frozen #1（41 處）→ Phase 4 後解凍
        return self._kernel._eval.evaluate(task, output)

    def _get_correction(self, *args, **kwargs):  # Frozen #2（28 處）→ Phase 4 後解凍
        return self._kernel._brain.decide_correction(*args, **kwargs)

    def _send_compact(self, *args, **kwargs):  # Frozen #3（17 處）→ Phase 4 後解凍
        return self._kernel.bus.get_plugin("token_guard").send_compact(*args, **kwargs)

    def _apply_single_mutation(self, mutation, **kwargs):  # Frozen #4（22 處，v1.1 補）→ Phase 4 後解凍
        return self._kernel._mutation_service.apply(mutation, **kwargs)

    def _validate_batch_compatibility(self, mutations):  # Frozen #5（8 處，v1.1 補）→ Phase 4 後解凍
        return self._kernel._mutation_service.validate_batch(mutations)

    # Frozen #6 _evolver、#7 _minimax_evolver、#8 _consecutive_compact_failures 已在
    # __init__ / property 處理；#9 _cfg.token_guard.enabled 透過 self._cfg 直通
```

**v1.1 解凍排程（Deprecation Cycle，對齊 01 v1.1 §3.10 步驟 1~4）**：

| Phase 階段 | 解凍時機 | 解凍成員 | 對應 PR |
|------------|---------|---------|---------|
| Phase 3 末（W11） | EvolutionPlugin 完成後 | #6 `_evolver`、#7 `_minimax_evolver` | 標記 `@deprecated(version="2.0")` |
| Phase 3 末（W11） | TokenGuardPlugin 完成後 | #8 `_consecutive_compact_failures` | 同上 |
| Phase 4 末（W12） | Facade 切換完成後 | #1 `_evaluate`、#2 `_get_correction`、#3 `_send_compact`、#4 `_apply_single_mutation`、#5 `_validate_batch_compatibility`、#9 `_cfg.token_guard.enabled` | 全數標記 `@deprecated` |
| Phase 5 期間 | 測試逐步遷移 | （刪除 `@deprecated` 成員） | 每改一個 PR |

**Phase 4 驗收條件（DoD，v1.1 擴充）**：

**核心 DoD**：
- [ ] `playbook_runner.py` < 300 行（從 2246 → < 300）
- [ ] 所有 193 處測試耦合**仍然綠**（透過 9 項 Frozen Surface shim）
- [ ] Equivalence test 仍然綠（**11 欄 snapshot byte-level 一致**）
- [ ] **`tools/check_loc_budget.py` 全綠**（含 +20% 總量上限）
- [ ] **`pytest tests/test_gap*.py -v` 全綠**（17 個 Gap 不退化）
- [ ] **`pytest tests/cli/ -v` 全綠**（9 個 CLI 場景）

**Frozen Surface 完整性檢查**：
- [ ] 9 項 Frozen Private Surface shim 全部存在且功能正確
- [ ] 每項 shim 為純委派（無業務邏輯，對齊 §5「禁止行為」）
- [ ] 解凍標記（`@deprecated(version="2.0")`）已加上 6 項

**Gate G3 強制簽核**：
- [ ] **PM 強制簽核完成**（Gate G3，01 v1.1 §3.13.2）
- [ ] Architect 與 QA 雙簽
- [ ] PR description 標註「god object 拆解完成 / Gate G3 PM 簽核」里程碑
- [ ] git tag `gate/G3-passed` 並更新 `docs/05_development/gate_audit.md`

### 2.7 Phase 5：DAL 介面化（File backend，v1.1：改用 Contract ABC）

**目標**：把 `CheckpointManager` / `FailureKnowledgeBase` / 直接 `yaml.dump` 都換成 IStateRepository / IMemoryStore / IPlaybookRepository。

> **QA 必要修改 #6**：v1.0 用 `@pytest.fixture(params=...)` 寫法，未強制 backend 繼承 abstract base class，無法在 Phase 6 PG 接入時自動套用同一組契約。v1.1 改採 **`IStateRepositoryContract` ABC 繼承式**（對齊 01 v1.1 §3.9）。

#### 5.1 LSP 契約測 Suite（v1.1：ABC 繼承式）

```python
# tests/contract/test_state_repository_contract.py（v1.1 採 ABC 繼承）
from abc import ABC, abstractmethod

class IStateRepositoryContract(ABC):
    """所有 IStateRepository 實作的共通行為驗證骨架。
    Phase 5 / Phase 6 任一新後端必須繼承此 class 並實作 _make_repo()，
    否則 CI 阻擋合併（對齊 01 v1.1 §3.9）。
    """

    @abstractmethod
    def _make_repo(self, tmp_path) -> "IStateRepository": ...

    def test_save_load_roundtrip(self, tmp_path):
        repo = self._make_repo(tmp_path)
        cp = make_sample_checkpoint()
        repo.save_checkpoint("pb_001", cp)
        assert repo.load_checkpoint("pb_001") == cp

    def test_concurrent_save_is_atomic(self, tmp_path):
        # 多 process 同時 save 不應產生 partial write（v1.1 必測，01 v1.1 §3.9）
        ...

    def test_load_missing_returns_none(self, tmp_path):
        repo = self._make_repo(tmp_path)
        assert repo.load_checkpoint("nonexistent") is None

    def test_clear_idempotent(self, tmp_path):
        repo = self._make_repo(tmp_path)
        repo.clear_checkpoint("pb_001")
        repo.clear_checkpoint("pb_001")  # 重複 clear 不應拋例外

    def test_counter_persistence_round_trip(self, tmp_path):
        # v1.1 必測：Gap-042 / Gap-048 計數器跨 save/load 完整保留（01 v1.1 §3.9）
        repo = self._make_repo(tmp_path)
        cp = make_sample_checkpoint(
            goto_counter={"T01": 2, "T03": 1},
            inject_before_counter={"T02": 1},
            skip_to_counter={"T04": 3},
            step_evolution_counter={"T05": 2, "T06": 1},
        )
        repo.save_checkpoint("pb_001", cp)
        loaded = repo.load_checkpoint("pb_001")
        assert loaded.goto_counter == cp.goto_counter
        assert loaded.inject_before_counter == cp.inject_before_counter
        assert loaded.skip_to_counter == cp.skip_to_counter
        assert loaded.step_evolution_counter == cp.step_evolution_counter

    def test_failure_history_round_trip(self, tmp_path):
        # Gap-007-A：FailureTracker 跨 Session 持久化
        ...

    def test_schedule_resume_sets_iso_timestamp(self, tmp_path):
        ...


class TestFileStateRepositoryContract(IStateRepositoryContract):
    """File backend 必過所有契約測。"""
    def _make_repo(self, tmp_path):
        return FileStateRepository(checkpoint_dir=str(tmp_path))


class TestInMemoryStateRepositoryContract(IStateRepositoryContract):
    """InMemory backend 必過所有契約測（測試夾具）。"""
    def _make_repo(self, tmp_path):
        return InMemoryStateRepository()


# Phase 6 接入時自動繼承同一組契約測，零額外撰寫成本：
# class TestPgStateRepositoryContract(IStateRepositoryContract):
#     def _make_repo(self, tmp_path):
#         return PgStateRepository(dsn=os.environ["TEST_PG_DSN"])
```

**LSP 雙 backend 契約測 ≥ 7 個 × 2 backend = ≥ 14 個強制測試**（File + InMemory），對齊 01 v1.1 §3.9 的 5 項必測 + Gap-042/048 + Gap-007-A。

**Phase 5 驗收條件（DoD，v1.1 擴充）**：

- [ ] `autoclaude/infra/repositories/` 建立 File* + InMemory* 6 個類別
- [ ] **`tests/contract/` 目錄建立**，含 `IStateRepositoryContract` ABC 與 2 個繼承實作（File + InMemory）
- [ ] **`pytest tests/contract/ -v` 全綠**（≥ 14 個契約測）
- [ ] `CheckpointManager` 變成 deprecated alias（內部委派給 FileStateRepository）
- [ ] `FailureKnowledgeBase` 變成 deprecated alias
- [ ] 558 + Equivalence + 新增 DAL 測試全綠
- [ ] **`pytest tests/test_gap*.py -v` 全綠**（17 個 Gap 不退化）
- [ ] **行數預算 CI 全綠**
- [ ] **Gate G4 簽核完成**（Architect + QA），方可進入 Phase 6（選配）

### 2.8 Phase 6：PostgreSQL backend（選配，v1.1：強制契約測前置）

> 此階段不在重構必修範圍，列為 future work。當業務需求觸發時（例：要在雲端部署、要做歷史分析 dashboard），LSP 測試會幫我們把 PG backend 一次接上。

> **QA 必要修改 #7**：v1.0 對 PG backend 沒有強制契約測前置條件。v1.1 增訂：**任何 `PgStateRepository` PR 必須先通過 `tests/contract/` 全綠**（含 `TestPgStateRepositoryContract(IStateRepositoryContract)` 繼承實作）才可合併。

**Phase 6 驗收條件（DoD，v1.1 新增）**：

- [ ] `autoclaude/infra/repositories/pg_*.py` 三個類別建立完成（State / Memory / Playbook）
- [ ] `tests/contract/test_state_repository_contract.py` 新增 `TestPgStateRepositoryContract(IStateRepositoryContract)` 繼承實作
- [ ] **`pytest tests/contract/ -v` 全綠**（File + InMemory + PG 三後端通過同一組 ≥ 14 個契約測）
- [ ] CI 加入 docker-compose（`postgres:17`）fixture
- [ ] Alembic migration 初始版本完成
- [ ] 一次性 `scripts/migrate_file_to_pg.py` 工具完成
- [ ] **Gate G5 簽核完成**（PM + Stakeholder，01 v1.1 §3.13.2）

---

## 3. 風險矩陣與回滾策略

### 3.1 風險識別（v1.1：每項加觸發條件量化值）

> **PM 必要修改 #5**：v1.0 緩解措施模糊（「順序錯誤」「不夠嚴密」），無法量化判定何時 escalate。v1.1 為每項風險新增「**觸發條件（量化）**」欄位，超過閾值即自動 escalate 至 PM + Architect。

| 風險 ID | 風險描述 | 機率 | 影響 | Severity | **觸發條件（量化）** | 緩解措施 |
|---------|----------|------|------|----------|----------------------|----------|
| R-1 | 重構期間 ScheduleWakeup / TOKEN_HALT 行為偏移 | 中 | 高 | 🟠 | snapshot byte-level diff > 0 處 | Equivalence test 含 token_halt fixture（fixture 04）；diff > 0 即 fail PR |
| R-2 | EventBus 同步 dispatch 順序錯誤導致 token compact 在 evaluator 後才觸發 | 中 | 高 | 🟠 | 任一 Plugin 違反 priority 約定表（01 v1.1 §3.4.2） | Plugin 訂閱順序由 priority 顯式控制；新增 `test_event_bus_priority_order.py` 順序測試 ≥ 8 case |
| R-3 | Plugin 之間互相依賴形成隱性耦合 | 高 | 中 | 🟠 | `grep "from autoclaude.plugins\."`  在 plugins/ 下匹配 ≥ 1 處 | 嚴禁 plugin 直接 import 另一 plugin；CI lint 加入 `import-linter` 檢查；只透過 HookContext.payload 傳遞 |
| R-4 | Facade shim 漏接某個私有方法導致測試突然 fail | 高 | 低 | 🟡 | 9 項 Frozen Surface 任一 fail 數 ≥ 1 | Phase 4 前先跑 `grep "runner\._" tests/` 列清單；自動產生 Frozen Surface check 腳本（`tools/check_frozen_surface.py`） |
| R-5 | 舊 Checkpoint 檔在 Phase 5 升級後無法讀取 | 低 | 高 | 🟠 | 既有 `checkpoints/*.checkpoint.json` 任一檔讀取失敗 | FileStateRepository 在 load 時嘗試舊 schema；提供一次性 migration script `scripts/migrate_checkpoint_schema.py` |
| R-6 | 演化版 Playbook 路徑邏輯漏接 | 中 | 中 | 🟡 | Equivalence fixture 05/12 任一 fail | Equivalence fixture 含 `evolution_inject`、`evolution_counter_esc_f12` case |
| R-7 | 開發週期過長導致 Evo-007 新需求進來 | 高 | 中 | 🟠 | 主分支 ≥ 5 個工作日無 Plugin PR merge | 採用 trunk-based development；weekly cadence 表（§2.5）強制 W5~W11 每週至少 1 個 Plugin PR |
| R-8 | PostgreSQL backend 改變 ID 計算方式（path → sha256）破壞 backward compat | 中 | 高 | 🟠 | Phase 6 PR 中任一既有 checkpoint 讀取 fail | 過渡期 File backend 沿用 path-based ID；切到 PG 時提供 dual-id 支援；migrate script 一次性轉換 |
| R-9 | 測試耦合（193 處）的 shim 不夠嚴密，造成行為偏移 | 高 | 高 | 🔴 | Equivalence byte-level diff > 0 處 OR `pytest tests/test_gap*.py` 任一退化 | Equivalence test 必過；Phase 4 結束前 **QA + PM 雙簽**（Gate G3）；連續 2 工作天無法綠燈即觸發回滾 |
| R-10 | 開發人員過度設計 Plugin 介面（Phase 2 over-engineering） | 中 | 中 | 🟡 | 任一 Plugin 行數 > 250 OR Kernel > 250 OR 總增量 > +20% | Architect 把關 hookspec；`tools/check_loc_budget.py` CI gate（01 v1.1 §3.13.1） |
| **R-11**（v1.1 新增） | **GotoCounterPlugin 計數器邏輯與 Kernel 不一致導致 Gap-042/048/049 退化** | 中 | 高 | 🟠 | `pytest tests/equivalence/fixtures/{11,12,13}_*.yaml` 任一 fail | 三個專屬 fixture（§2.2 §0.1）byte-level 比對；GotoCounterPlugin PR DoD 強制執行 |
| **R-12**（v1.1 新增） | **CLI 介面破壞向後相容（如 exit code 變更）** | 低 | 高 | 🟠 | `tests/cli/test_cli_compatibility.py` 9 場景任一 fail | Phase 0 即建立 CLI snapshot；任一退化即 PR fail |

**自動 escalation 規則**：任一風險的觸發條件達標時，CI 自動：
1. 阻擋 PR 合併
2. 通知 PM + Architect（Slack #autoclaude-refactor）
3. 記錄至 `docs/05_development/risk_log.md`

### 3.2 回滾策略（v1.1：擴充 KB / evolved playbook 備份）

> **PM 必要修改 #5**：v1.0 僅備份 `checkpoints/`，未涵蓋 `failure_knowledge_base.jsonl`、演化版 Playbook、`escalation_dump_*.md` 等。v1.1 擴充至完整持久化鏡像。

**每個 Phase 開始前必須執行**：

```bash
# (1) 建立 git tag 作為回滾點
git tag refactor/phase-N-start
git push origin refactor/phase-N-start

# (2) v1.1：完整持久化備份（不再只備份 checkpoints/）
BACKUP_DIR="backups/phase-N-start-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${BACKUP_DIR}"
cp -r checkpoints/                  "${BACKUP_DIR}/"   # 既有
cp -r checkpoints/*.jsonl           "${BACKUP_DIR}/"   # KB（FailureKnowledgeBase）
cp -r scripts/evolved_*.yaml        "${BACKUP_DIR}/"   # 演化版 Playbook
cp -r logs/escalation_dump_*.md     "${BACKUP_DIR}/"   # ESCALATION dump
cp .loc_baseline                    "${BACKUP_DIR}/"   # 行數基準
echo "Phase N start at $(git rev-parse HEAD)" > "${BACKUP_DIR}/HEAD.txt"

# (3) 通知 PM
notify_pm "Phase N 開始，備份位置：${BACKUP_DIR}"
```

**回滾觸發條件（v1.1：含量化值）**：

- 任一 commit 後 `pytest tests/ -q` 出現 fail
- Equivalence test snapshot 出現非預期 byte-level diff（>= 1 處）
- **`pytest tests/test_gap*.py` 任一退化**（01 v1.1 §3.12 不退化承諾）
- **`tests/cli/test_cli_compatibility.py` 9 場景任一 fail**（01 v1.1 §3.11 CLI 相容承諾）
- **`tools/check_loc_budget.py` 失敗**（行數超預算）
- **9 項 Frozen Surface 任一 shim 缺失**
- 連續 **2 個工作天**無法解決的 regression（自動 escalate）

**回滾動作（v1.1：完整還原）**：

```bash
# (1) 還原程式碼
git reset --hard refactor/phase-N-start
git push --force-with-lease origin refactor/phase-N

# (2) v1.1：還原所有持久化資料
BACKUP_DIR=$(ls -td backups/phase-N-start-* | head -1)
rm -rf checkpoints/
cp -r "${BACKUP_DIR}/checkpoints"/    .
cp    "${BACKUP_DIR}"/*.jsonl         checkpoints/
cp    "${BACKUP_DIR}"/evolved_*.yaml  scripts/
cp    "${BACKUP_DIR}/.loc_baseline"   .

# (3) 通知 PM + 回到設計階段重新檢視
notify_pm "Phase N 回滾完成，請重新評估設計"
```

> **QA**：回滾不是失敗，是**設計回饋**。我們寧可回滾 3 次也不要把破損的程式合進 main。
> **PM**：回滾觸發後，下次該 Phase 重啟必須先補完 root cause 分析（`docs/05_development/rollback_postmortem_phase-N.md`）。

---

## 4. 里程碑與驗收條件總表（v1.1：補 Gate 欄位 + Gap test gate）

> ⚠️ **v1.2 補充：Phase 4 實際完成由 SD_03 補完**
> 里程碑 M4（Facade 切換，G3 PM 強制簽核）於本表記為 W12；但依 2026-05-08 三方審查，M4 實際工程由 [SD_Improving_03.md](SD_Improving_03_Phase4_Real_Switch.md) v1.1 獨立 5 週 sprint（27~36 PD）承接。G3 當前狀態：✅ 已完成（2026-05-12），詳見 [gate_audit.md](../05_development/gate_audit.md)。

> **Architect 必要修改 #2**：v1.0 表格未對應 01 v1.1 §3.13.2 的 Gate G1~G5；v1.1 新增「對應 Gate」與「Gap test 全綠」兩欄，明文要求每 milestone 必過。

| 里程碑 | Phase | 預估完成 | 主要交付 | **對應 Gate** | DoD（含 v1.1 強制門檻） |
|--------|-------|----------|----------|---------------|--------------------------|
| **M0**：基準對齊 | 0 | W1 | **13** golden fixtures + snapshot（11 欄）+ CLI test + `check_loc_budget.py` | 前置 **G1** | 558 + 13 + 9 CLI 全綠；**Gap test 全綠**；行數預算建立 baseline |
| **M1**：Port 抽出 | 1 | W2 | 3 Port 介面 + 3 Adapter | （G1 已過） | 558 全綠；**Gap test 全綠**；Equivalence snapshot 不變 |
| **M2**：Kernel 骨架 | 2 | W3-W4 | Kernel + EventBus + IResolutionPolicy + 50~80 unit tests | **G2**（進 Phase 3 前） | 608+ 全綠；**Gap test 全綠**；行數預算 CI 全綠 |
| **M3a**：低風險 Plugin（#1~#6 含 GotoCounterPlugin） | 3 | W5-W6 | 6 Plugin 完成 | （Phase 3 進行中） | 每 PR 全綠 + **Gap test 全綠** + Equivalence byte-level 一致 + 行數預算 CI |
| **M3b**：中-高風險 Plugin（#7~#9） | 3 | W7-W8 | 3 Plugin 完成 | （Phase 3 進行中） | 同上 |
| **M3c**：極高風險（#10 ~ #13） | 3 | W9-W11 | ConvergencePlugin / EvolutionPlugin / GoalSynthesisPlugin / MutationApplyService（7 IMutationStrategy） | **G2 收口**（進 Phase 4 前） | 全綠 + **解凍 `_evolver` / `_minimax_evolver` / `_consecutive_compact_failures` 標 `@deprecated`** |
| **M4**：Facade 切換 | 4 | W12 | runner < 300 行 + 9 項 Frozen Surface shim 完整 | **G3 PM 強制簽核** | Equivalence byte-level 一致；CLI 9 場景全綠；**Gap test 全綠**；行數預算 CI 全綠 |
| **M5**：DAL 抽出 | 5 | W13 | File + InMemory backend + `IStateRepositoryContract` ABC | **G4** | LSP 契約測 ≥ 14 個全綠；**Gap test 全綠** |
| **M6**：PG backend（選配） | 6 | W15+ | Postgres backend + Alembic + docker-compose | **G5** | 三 backend 共過同一組 ≥ 14 個契約測；migrate script 完成 |

**Gate 流程**：
- 每個 Gate 通過後在 git tag `gate/G{N}-passed`，並 append 至 `docs/05_development/gate_audit.md`
- **Gate G3 為唯一 PM 強制簽核點**；任何試圖繞過 G3 的 PR 將被 QA 直接 revert

### 4.1 「重構成功」的最終驗收（M4 完成後，v1.1 擴充）

**結構達成**：
- [ ] `playbook_runner.py` 從 2246 行降至 < 300 行
- [ ] `PlaybookKernel` ≤ 250 行，`_run_step` 方法 ≤ 80 行
- [ ] **12 個 Plugin** 各自獨立檔案，每個 ≤ 250 行（含 v1.1 新增的 GotoCounterPlugin）
- [ ] **MutationApplyService 為 Layer 2 Domain Service**，含 7 個 IMutationStrategy（每個 ≤ 80 行）
- [ ] 任何新功能可透過「新增 Plugin 檔案」完成（OCP 達成，01 v1.1 §3.8）

**測試與 CI（v1.1 強制門檻）**：
- [ ] 558 既有測試全綠 + Equivalence byte-level 一致（11 欄）
- [ ] **`pytest tests/test_gap*.py -v` 全綠**（17 個 Gap 不退化，01 v1.1 §3.12）
- [ ] **`pytest tests/cli/ -v` 全綠**（9 個 CLI 場景，01 v1.1 §3.11）
- [ ] **`tools/check_loc_budget.py` 全綠**（Kernel ≤ 250、Plugin ≤ 250、總增量 ≤ +20%，01 v1.1 §3.13.1）
- [ ] **9 項 Frozen Surface shim 完整且為純委派**（01 v1.1 §3.10）

**框架與文件**：
- [ ] `pyproject.toml` 未引入 `pluggy` 等新框架（保持輕量）
- [ ] CLAUDE.md 補充「新增 Plugin 的 SOP」段落
- [ ] **Gate G3 PM 簽核完成**

### 4.2 「DAL 接入準備就緒」的驗收（M5 完成後，v1.1 擴充）

**Port 介面**：
- [ ] 3 個 Port 介面 `IStateRepository` / `IMemoryStore` / `IPlaybookRepository` 完整定義
- [ ] **`IQueryableStateRepository` 子介面**（v1.1 ISP 修正）正確實作

**契約測（v1.1：對齊 01 v1.1 §3.9 ABC 寫法）**：
- [ ] `tests/contract/test_state_repository_contract.py` 含 `IStateRepositoryContract` ABC
- [ ] **File backend 與 InMemory backend 通過 ≥ 14 個契約測**（含 `test_counter_persistence_round_trip` / `test_concurrent_save_is_atomic`）
- [ ] **`pytest tests/contract/ -v` 全綠**

**架構**：
- [ ] `main.py` 的 DI 組裝為唯一決定後端的位置
- [ ] PostgreSQL schema DDL 已在文件中審查通過（即使未實作）
- [ ] 一次性 migration 腳本 `scripts/migrate_file_to_pg.py` 設計完成

**Gate**：
- [ ] **Gate G4 簽核完成**（Architect + QA）

---

## 5. 對 Claude Code 開發循環的相容性

> 本重構必須遵守 CLAUDE.md 的「開發-編譯-測試循環強制規則」：

```
每完成一個 Plugin（或一個介面定義）→ 立即 pytest → 通過才繼續
每完成一個 Phase → tag git + 跑完整 558 + Equivalence → 通過才合併
每個 PR → 雙人簽核（Architect + QA）→ 通過才 merge
```

**禁止行為**：

- ❌ 累積 2 個以上 Plugin 在同一 PR。
- ❌ 為趕進度跳過 Equivalence test。
- ❌ 在 facade shim 偷加業務邏輯（shim 必須是純委派）。
- ❌ 在 Plugin 內部互相 import（用 HookContext.payload 通訊）。

---

## 6. Open Questions（v1.1：每題加 owner + 決策時限）

> **PM 必要修改 #6**：v1.0 僅給「建議」，無 owner 與時限，PM 無法追蹤。v1.1 為每題指定負責人並設決策截止點，超期未決即升級為 R-? 風險。

### Q1：Plugin 之間的執行順序由誰決定？（v1.1 已決議）

> **v1.1 決議**：採 01 v1.1 §3.4.2 的 **priority 約定表**（候選 B 升級版）。

**priority 約定表（取自 01 v1.1 §3.4.2）**：

| Priority 區間 | 用途 | 範例 Plugin |
|--------------|------|-------------|
| 0 ~ 9 | 系統級 veto / 中斷檢查 | HotkeyPlugin(10), PreRunValidatorPlugin(5) |
| 10 ~ 29 | 安全 / 一致性 guards | CrossStepValidatorPlugin(15) |
| 30 ~ 49 | Prompt 注入 / 資源管理 | TokenGuardPlugin(30), GlobalGoalAnchorPlugin(35) |
| 50（預設） | 一般觀察者 | KnowledgeBasePlugin, NotificationPlugin, GoalSynthesisPlugin |
| 60 ~ 79 | 演化 / 突變提議 | ConvergencePlugin(65), EvolutionPlugin(70) |
| 80 ~ 99 | 持久化（最後執行） | GotoCounterPlugin(85), CheckpointPlugin(90) |

| 欄位 | 內容 |
|------|------|
| Owner | Architect |
| 決策時限 | 已於 01 v1.1 §3.4.2 決議（**已關閉**） |

### Q2：是否引入 `pluggy` 套件？（已決議）

| 欄位 | 內容 |
|------|------|
| 決議 | **不引入**。自建 EventBus 約 150 行，pluggy 引入後維護成本（主要是學習曲線）大於節省的程式碼。AutoClaude 是工具，不是框架。 |
| Owner | Architect |
| 決策時限 | 已關閉 |

### Q3：MutationApplyService 是 Plugin 還是 Domain Service？（已決議）

| 欄位 | 內容 |
|------|------|
| 決議 | **Domain Service（Layer 2）**。被 Kernel 直接呼叫，由 ConvergencePlugin / EvolutionPlugin 透過 `MutationProposal` 提議。Mutation 不是事件回應，是命令處理。 |
| Owner | Architect |
| 決策時限 | 已於 01 v1.1 §3.5 決議（**已關閉**） |

### Q4：PostgreSQL backend 是否要支援 `pg_listen` / `pg_notify` 做即時通知？

| 欄位 | 內容 |
|------|------|
| 建議 | Phase 6+ 再評估。當前 NotificationPlugin 已負責桌面通知，PG-level 即時推送屬未來增強。 |
| Owner | **PM** |
| 決策時限 | **W14 結束前**（Phase 5 末，G5 前置） |
| 升級條件 | 若 W14 仍未決議 → 列入 R-13 風險，預設「不支援」 |

### Q5：Equivalence test 的 snapshot 怎麼維護？

| 欄位 | 內容 |
|------|------|
| 建議 | 使用 `syrupy` 或 `pytest-snapshot`；v1.1 評估後**選定 `syrupy`**（支援 JSON sort_keys 比對） |
| Owner | **QA** |
| 決策時限 | **W1 結束前**（Phase 0 啟動時即定案） |
| 升級條件 | 若 W1 仍未決議 → 預設使用 `pytest-snapshot` 並改寫至 `syrupy`（額外 1-2 PD 成本） |

### Q6（v1.1 新增）：GotoCounterPlugin 與 CheckpointPlugin 同 phase 排序衝突如何避免？

| 欄位 | 內容 |
|------|------|
| 議題 | 兩者皆訂閱 `POST_ATTEMPT` / `ON_INTERRUPT`；priority 85 vs 90，需文件化「Goto(85) 必先於 Checkpoint(90)」不變式 |
| 建議 | 由 EventBus.register 順序保序，priority 排序確保；新增 `test_event_bus_priority_order.py` 驗證 |
| Owner | **Architect** |
| 決策時限 | **W2 結束前**（Phase 1 末） |

---

## 7. 三人結語（v1.1）

**Architect**：v1.1 已併入 GotoCounterPlugin 獨立遷移、Gate G1~G5 對應、Frozen Surface 9 項完整 shim、`IQueryableStateRepository` 子介面（ISP/LSP 修正）、契約測 ABC 寫法等修正。Part 1 + Part 2 的 commitment 是「**12-14 週內把 god object 拆乾淨，每個 commit 都 green**」。如果做到這點，AutoClaude 就具備了支撐 Evo-007 ~ Evo-010 的結構容量。

**QA**：我接受 v1.1 計畫，並重申以下硬性條件：

1. 每個 Phase 開始前，必須先執行 `git tag refactor/phase-N-start` + 完整持久化備份（含 KB / evolved playbook / escalation dump，§3.2）
2. Equivalence test snapshot（**v1.1：11 欄 byte-level**）不允許因「行為改進」而修改——除非經過 PM 與 Architect 雙簽
3. Phase 3 的 13 個元件順序不可調整——已依測試耦合度排序，由低到高，這是風險控制的關鍵
4. 任何 Phase 連續 2 工作天無法綠燈，立即觸發 Phase 0 檢視（重新評估設計而非加 hack）
5. **`pytest tests/test_gap*.py -v` 全綠**為每個 Phase / 每個 PR 的硬門檻——任一退化 = 直接 revert
6. **`tests/cli/test_cli_compatibility.py` 全綠**為 CLI 100% 向後相容承諾的執行端兌現

**PM**：v1.1 已補上人日(PD) / FTE / Gate G1~G5 / weekly cadence（W5~W11）/ 觸發條件量化值 / Q1~Q6 owner 與時限。**Gate G3（Phase 4 Facade 切換）為唯一 PM 強制簽核點**——任何試圖跳 Gate 趕進度的 PR 將被直接 revert。Phase 6 PG backend 為選配，待業務需求觸發；Q4（pg_listen/pg_notify）若 W14 未決議自動降級為「不支援」。

---

## 8. 文件審查 Checklist（給 Reviewer，v1.1 擴充）

請依下列項目逐一勾選：

**架構面（Architect）**：
- [ ] DAL 三大介面是否覆蓋現有所有持久化來源？（Checkpoint / KB / Playbook 演化版）
- [ ] **`IQueryableStateRepository` 子介面是否解決 LSP 違反問題**？（v1.1，§1.2.1）
- [ ] PostgreSQL schema 是否與 Pydantic models 對齊？（含 JSONB 欄位語意）
- [ ] **Phase 3 的 13 個元件**順序是否合理？（測試耦合度由低到高，含 v1.1 新增 GotoCounterPlugin）
- [ ] 是否回應了 Part 1 §3.8 的反例？（OCP 達成條件）
- [ ] **MutationApplyService 歸屬是否一致**？（Layer 2 Domain Service）

**測試面（QA）**：
- [ ] **Phase 0 fixture 是否 ≥ 13 個**？（含 Gap-042/048/049 三場景）
- [ ] **Snapshot 是否含 11 個欄位**（4 既有 + 7 新增 byte-level 跨 Session 狀態）？
- [ ] **`tests/cli/test_cli_compatibility.py` 是否在 Phase 0 建立**？（9 場景）
- [ ] **`tests/contract/` 是否採 ABC 繼承寫法**？（v1.1 對齊 01 v1.1 §3.9）
- [ ] **9 項 Frozen Surface shim 是否完整**？（v1.1 §2.6）
- [ ] **Gap-009~049 不退化 CI gate 是否每 Phase / 每 PR 強制執行**？（17 個 test_gap*.py）
- [ ] TDD 6 階段是否每階段都有 DoD？（含 git tag 與回滾點）
- [ ] 風險矩陣是否覆蓋 ≥ 12 個風險點？（含 v1.1 新增 R-11、R-12）
- [ ] **每項風險是否有觸發條件量化值**？

**商業／落地面（PM）**：
- [ ] **每個 Phase 是否有人日(PD) / FTE 估算**？（v1.1 §2.1）
- [ ] **是否提供 weekly cadence（W5~W11）**？（v1.1 §2.5）
- [ ] **Gate G1~G5 是否與 Milestone M0~M6 對齊**？（v1.1 §4）
- [ ] **Gate G3 是否標明 PM 強制簽核**？（v1.1 §2.6 / §4）
- [ ] **`tools/check_loc_budget.py` 是否在 Phase 0 建立並 CI gate**？（v1.1 §2.2 §0.4）
- [ ] **回滾 SOP 是否涵蓋 KB / evolved playbook**？（v1.1 §3.2）
- [ ] **Q1~Q6 是否各有 owner + 決策時限**？（v1.1 §6）

**通過門檻**：以上 24 項逐一勾選；任一未勾選則 v1.1 不予批准。

---

**文件元數據**：

- 建立日期：2026-05-07
- 文件版本：**v1.1**（Draft，已併入三方必要修改 19 項）
- 預估閱讀時間：55 分鐘
- 適用團隊：核心架構組 + QA 組 + PM + DBA（Phase 5+）
- Review 截止：待專案 PM 排期
- 對應 Part 1：[SD_Improving_01.md](SD_Improving_01.md) **v1.1**

**v1.1 變更摘要**（vs v1.0）：

| 章節 | 變更 | 對應三方審查 |
|------|------|-------------|
| 元數據 | v1.0 → v1.1，加 PM 維護者 | 全部 |
| §1.2.1 | 拆出 `IQueryableStateRepository` 子介面（修 LSP 違反） | Architect #4 |
| §2.1 | 階段總覽加「人日(PD) / FTE / Gate / 簽核人」四欄 | PM #1 |
| §2.2 §0.1 | Golden fixture 由 10 → **13 個**（補 Gap-042/048/049） | QA #1 |
| §2.2 §0.2 | Snapshot dict 由 4 欄 → **11 欄**（byte-level + JSON sort_keys） | QA #2 |
| §2.2 §0.3（新增） | CLI 相容性測試 9 場景，Phase 0 交付 | PM #4 |
| §2.2 §0.4（新增） | `tools/check_loc_budget.py` CI gate，Phase 0 交付 | PM #4 |
| §2.5 | Plugin 表 12 → **13 列**（新增 GotoCounterPlugin），加 priority；新增 weekly cadence W5~W11 | Architect #1 / QA #3 / PM #2 |
| §2.5 DoD | 加入 `pytest tests/test_gap*.py` 全綠 + 行數預算 + Frozen Surface 完整性 | QA #4 |
| §2.6 | Frozen Surface shim 5 → **9 項完整**；加解凍排程；標 **G3 PM 強制簽核** | QA #5 / PM #3 |
| §2.7 | LSP 改 `IStateRepositoryContract` ABC 繼承式（對齊 01 v1.1 §3.9） | QA #6 / Architect #5 |
| §2.8 | Phase 6 加「`PgStateRepository` 必先過 `tests/contract/` 全綠」 | QA #7 |
| §3.1 | R-1~R-10 加「觸發條件量化值」欄；新增 R-11 / R-12 | PM #5 |
| §3.2 | 回滾 SOP 擴充 KB / evolved playbook / escalation dump 備份 | PM #5 |
| §4 | 里程碑表加「對應 Gate」欄；DoD 加 Gap test gate | Architect #2 / QA #4 |
| §4.1 / §4.2 | DoD 加行數預算 CI + Frozen Surface + Gap test + Gate 簽核 | Architect #3 |
| §6 | Q1 升級為 priority 約定表；Q1~Q5 加 owner + 時限；新增 Q6 | PM #6 / Architect #6 |
| §7 | 升級為三人結語 | PM 全部 |
| §8 | Reviewer Checklist 擴為 24 項 | 全部 |
