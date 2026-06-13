# SRD 增補 — Improving_012 Phase 2 閉環強化（B 能力）

**版本**: v1.0 | **建立日期**: 2026-06-13 | **建立者**: sd-architect
**對應計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 已凍結）
**閘門**: SCG-1（SRD 增補 + 介面規格）🔴 人工確認後凍結
**涵蓋**: F-B1（AlertLadder 漸進式告警階梯）/ F-B2（Correction 效果事後驗證 + KB 失效回寫）

---

## 0. 凍結計畫精化聲明（Rule 7 + 流程改善 #1「擴充點實證」）

| 項目 | 凍結計畫原文 | 本 SRD 精化（附源碼實證） |
|------|-------------|--------------------------|
| checkpoint 持久化 | §2「`checkpoints` 新增欄位 alert_ladder（JSON 欄）」；Phase1 NextAction 寫「alembic 0017」 | **不需 alembic 0017**。PG `checkpoints` 表既有 `counters` JSONB 欄（`_pg_models.py:95`，server_default `'{}'`），Gap-042 四計數器即落此欄（`pg_state_repository.py:276-281` save / `:463` load）；alert_ladder 以 `counters["alert_ladder"]` 子鍵落地 = 零 schema migration、舊列向下相容。File backend 以 `PlaybookCheckpoint` additive 欄位（`sdd_governance` 前例：`checkpoint_manager.py:57-63`） |
| 新 port / plugin | §2 受影響模組表未列 ports/plugins 變更（F-B 系列） | 確認**無新 port、無新 plugin**：F-B 全在 execution 層（2 新 strategy 模組），wiring / `_REGISTER_ORDER` / importlinter 8 contracts 不動 |

> 以上為實作層精化，非範圍變更（F-B1/F-B2 功能語意與凍結計畫 §1 完全一致）。

### 擴充點實證表（所有宣稱之注入點附 `檔案:行號`，且已驗證確實被觸發）

| 擴充點 | 實證 | 觸發驗證 |
|--------|------|---------|
| 收斂升級唯一攔截點 | `_impl.py:278` `if report.recommendation == "escalate"` → `handle_convergence_escalation`（grep 全 codebase 唯一 call site） | 既有 escalation 測試覆蓋此路徑 |
| HINT 注入通道 | `_impl.py:326-331` `strategy_hint` 變數 → `_impl.py:416` `runner._get_correction(strategy_hint=...)` 既有參數 | change_strategy 路徑既有行為 |
| 重試耗盡保底 | `_impl.py:338` `if attempt >= max_retries` → `handle_max_retries_escalation`（不受 flag 影響，階梯有界性保證） | 既有測試 |
| checkpoint 計數恢復點 | `_loop_state.py:53-61` `initialize_loop_state` counters restore | Gap-042 既有測試 |
| KB skip_strategies merge 前例 | `knowledge_base.py:219-236` `record_escalation` | 既有測試 |
| AttemptRecord 效果比對欄位 | `failure_tracker.py:61-65`（`error_signature` / `exit_code` / `correction_prompt_sent` / `mutation_applied`）+ `_extract_fail_count_from_output:263` | Gap-007/008 既有測試 |

## 1. F-B1 — AlertLadder（漸進式告警階梯）

### 1.1 模組

`autoclaude/execution/alert_ladder.py`（strategy tier ≤300）：

```python
@dataclass
class LadderDecision:
    action: str           # "warning" | "hint" | "escalate"
    hint_text: str = ""   # action=="hint" 時注入 strategy_hint 的本地提示文字
    reasoning: str = ""

class AlertLadder:
    def __init__(self, threshold_no_improve: int = 2): ...
    def intercept(self, step_id: str, report: ConvergenceReport,
                  no_improve_streak: int) -> LadderDecision: ...
    def snapshot(self) -> dict: ...                # {step_id: {"warning": n, "hint": n}}
    def restore(self, state: dict) -> None: ...
```

### 1.2 行為（flag on 時，攔截 `_impl.py:278`）

該步驟第 1 次 escalate 信號 → **WARNING**（log + 計數，修正迴圈繼續）；第 2 次 → **HINT**（本地生成提示文字——含 trend/reasoning 與「已連續無法收斂，請徹底改變修法」——經既有 `strategy_hint` 參數注入 correction prompt；**不呼叫 Brain**，遵守「code 能答就 code 答」與 `.importlinter` Rule 4/5）；第 3 次 → **ESCALATE**（走既有 `handle_convergence_escalation`，行為與 flag off 完全相同）。

**Bypass（不入梯、直接 ESCALATE）**：
1. `report.trend == "environment_error"`（AutoClaude 無法修復，緩階無意義；`convergence_monitor.py:52-57`）；
2. F-B2 `no_improve_streak >= threshold`（見 §2.3，穿透剩餘階梯提前升級）。

**有界性**：階梯不增加 attempt 預算——WARNING/HINT 後 continue 既有 `for attempt` 迴圈，`max_retries` 上限與 `handle_max_retries_escalation`（`_impl.py:338`）、ErrorBudget 語意預算（`_impl.py:299-324`）均不受 flag 影響；每步驟最多 2 次緩階。

### 1.3 Feature flag

`AppConfig` 新增 `alert_ladder: AlertLadderConfig`（`utils/config.py`）：

```python
class AlertLadderConfig(BaseModel):
    enabled: bool = False                                   # 預設 off（凍結計畫 §4 緩解措施）
    no_improve_escalate_threshold: int = Field(default=2, ge=1, le=5)  # F-B2 N
```

flag off = escalation 控制流 byte-level 不變（零回歸保證）。轉正路徑依 SCG-6：nightly 觀察 7 天綠 → 預設 on。

### 1.4 持久化（凍結計畫「各階計數持久化於 checkpoint」）

- `PlaybookCheckpoint` 新增 `alert_ladder: dict = field(default_factory=dict)`（additive，舊 checkpoint 反序列化補空 dict，比照 `sdd_governance` 前例）。
- PG：`pg_state_repository._save` 之 `counters` dict 增 `"alert_ladder"` 鍵；`_load` 對應恢復。零 migration。
- 存檔路徑（三條，均 additive 預設空 dict）：interrupt 顯式 kwarg（`_step_init.check_hotkey_and_save` → `save_interrupt_checkpoint`）/ evolution kwarg（`save_evolution_resume_checkpoint`）/ token-halt payload 鍵（`checkpoint/_builder.py:53-70` 組裝處）。
- resume：`initialize_loop_state`（`_loop_state.py:53-61`）自 `resume_checkpoint.alert_ladder` 恢復至 runner 持有之 `AlertLadder` 實例。

## 2. F-B2 — Correction 效果事後驗證 + KB 失效回寫

### 2.1 模組

`autoclaude/execution/correction_verifier.py`（strategy tier ≤300）：`CorrectionVerifier.assess(tracker) -> EffectReport`（`improved: bool` / `reason: str`）+ per-step `no_improve_streak` 計數（隨 alert_ladder dict 一同持久化於 checkpoint：`{step_id: {"no_improve_streak": n}}`）。

### 2.2 改善判準（純本地比對，不呼叫 Brain）

比較 tracker 最後兩筆 `AttemptRecord`，且前筆確曾施加修正（`correction_prompt_sent` 非空或 `mutation_applied=True`）：

`improved = (error_signature 改變) OR (fail_count 下降) OR (exit_code 下降)`

（fail_count 取 `FailureTracker._extract_fail_count_from_output`；任一筆取不到 fail_count 時該分量視為無資訊，不計改善。）無改善 → `no_improve_streak += 1` 且觸發 KB 失效回寫；有改善 → streak 歸零。

> **exit_code 分量適用範圍（Architect P2-2）**：`exit_code 下降` 僅對「回傳**遞減**錯誤碼以反映修正進度」之 evaluator 有效（例如 fail 數隨 exit code 同向遞減的自訂評估器）。對「成功 0 / 失敗固定非零（如恆為 1 或 2）」的常見 evaluator（pytest 等），相鄰兩筆失敗的 exit_code 通常相等 → 此分量恆不觸發、退化為無資訊，改善判定僅由 signature / fail_count 兩分量承擔，不影響正確性（不會誤判改善）。

### 2.3 提前升級

`no_improve_streak >= no_improve_escalate_threshold`（預設 2）→ 直接 ESCALATE（§1.2 bypass 2，穿透 ladder 剩餘階梯），reasoning 標注 `F-B2: 同 error signature 連續 N 次修正無改善`。

**零回歸論證**：flag off 時 `is_stuck(2)`（`convergence_monitor.py:77-86`，2 次同 signature 且無數量改善即 escalate）在相同條件下**先行**觸發既有升級，故 F-B2 提前升級語意僅於 ladder 緩階期間實際生效；既有 escalation 測試零回歸。

### 2.4 KB 失效回寫（無論 flag、常開、additive）

`FailureKnowledgeBase` 新方法 `record_strategy_failure(error_signature_key, failed_strategy, step_id)`：
- 將 `failed_strategy` 併入該 entry `skip_strategies`（merge 模式比照 `record_escalation`）；
- 若 entry 既有 `successful_strategy == failed_strategy` → 清為 `None`（**策略失效標記**：歷史成功策略此次無效，後續 `query` 命中不再直接採用）；
- `outcome="strategy_failure"`。寫入僅在「無改善」判定時發生，不影響控制流（零回歸）。

## 3. 受影響檔案與 LOC

| 檔案 | 變更 | tier |
|------|------|------|
| `execution/alert_ladder.py` 🆕 / `execution/correction_verifier.py` 🆕 | 新模組 | strategy ≤300 |
| `execution/steps_orchestrator/_impl.py` | :278 攔截區塊（~15 行，邏輯下沉至新模組） | service ≤500 |
| `utils/config.py` | +`AlertLadderConfig` | service ≤500 |
| `utils/checkpoint_manager.py` | +`alert_ladder` 欄位 | service ≤500 |
| `utils/knowledge_base.py` | +`record_strategy_failure` | service ≤500 |
| `infra/repositories/pg_state_repository.py` | counters 子鍵 save/load 映射 | adapter ≤400 |
| `plugins/checkpoint/_builder.py` + `_interrupt.py` + `_evolution.py` + `_step_init.py` | additive 傳遞 alert_ladder | 既有 tier |
| `execution/steps_orchestrator/_loop_state.py` | resume 恢復 | strategy ≤300 |

## 4. 測試與驗收對應（凍結計畫 Phase 2 驗收）

| 凍結驗收 | TC 群 |
|---------|-------|
| 階梯轉換有測試 | `tests/test_alert_ladder.py`（單元）+ `tests/test_alert_ladder_integration.py`（orchestrator 整合）：warning→hint→escalate 轉換、bypass（environment_error / streak）、flag off 直通、checkpoint 持久化往返（File：`tests/test_alert_ladder.py::TestCheckpointFieldRoundtrip` + PG mock：`tests/contract/test_checkpoint_sdd_roundtrip.py` counters JSONB 子鍵）、有界性（`TestBoundedness` 不超 max_retries）、flag-off KB 不變式（`TestFlagOffKbInvariant`） |
| 同 error signature 無改善 N=2 次提前升級 | `tests/test_correction_verifier.py`：改善判準三分量、streak 累計/歸零、threshold 觸發、KB 失效回寫（skip merge + successful_strategy 清除） |
| 既有 escalation 測試零回歸 | full pytest 全綠（flag 預設 off）；`_impl.py` 攔截區塊 flag off 路徑 diff-level 等價 |

Coverage ≥90%（新模組）；SCG-4：full pytest + lint-imports 8 kept + LOC=0 + snapshot OK。

## 5. 回滾

F-B1：`alert_ladder.enabled=false`（預設）即回滾全部行為變更。F-B2：提前升級依附 flag 同步回滾；KB `strategy_failure` 紀錄為 additive JSONL，舊版讀取相容（未知 outcome 不影響 query 語意）。

---

**SCG-1 🔴 人工確認**：koalawu 2026-06-13 核准凍結（AskUserQuestion 互動確認；含「不需 alembic 0017、alert_ladder 走 PG counters JSONB 子鍵」精化）
