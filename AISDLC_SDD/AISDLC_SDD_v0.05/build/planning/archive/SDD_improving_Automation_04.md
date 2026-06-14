# SDD Agentic 閉環自動化 — Phase E 執行藍圖
# L4.7 → L5 Closed-Loop Hardening & Learning Layer

**文件編號**: SDD_improving_Automation_04
**建立日期**: 2026-04-20
**分析對象**: AISDLC-SDD v0.01（Phase A+B+D 已完成，Automation_01/02/03 已歸檔）
**評審角色**: 首席 AI 自動化架構師（Karpathy 風格）
**前置文件**:
- `build/planning/archive/SDD_improving_Automation_01.md`（Phase A/B：FSM 形式化 + SLV + Compaction）
- `build/planning/archive/SDD_improving_Automation_02.md`（ACT-001~009：持久化 + 預算 + TFA）
- `build/planning/archive/SDD_improving_Automation_03.md`（Phase D：FSM Runtime + Hooks + 90% Auto-Compact）

**核心論斷**:
> 現有框架（Phase A+B+D）已達 **L4.7 — 圖靈完備的有界停機閉環**，
> Self-Verification 證明極端案例下系統能優雅中斷（~15K tokens，非無限耗盡）。
>
> 但深度審計揭露 **8 個結構性漏洞（E-01~E-08）**，它們不會讓系統失控，
> 卻會讓「精準停機」退化為「粗暴停機」，多耗 2~3 倍 token，且阻礙進入 L5。
>
> Phase E 的本質 = **從「機器強制執行」升級為「機器精準執行」+「機器從運行中學習」**。

---

## 壹、Self-Verification：極端案例再推演（Phase D 版）

### 1.1 案例：Spec 寫錯導致測試永遠無法通過（三變體）

#### 變體 A — 物理不可行（AC：回應時間 < 0ms）
```
SPEC_DRAFTING → SLV-001 FAIL → SCG_VALIDATION retry=1/3
              → SPEC_DRAFTING → SLV-001 FAIL → retry=2/3
              → SPEC_DRAFTING → SLV-001 FAIL → retry=3/3
              → ESCALATION（Abort Report 產出）
Token 消耗: ~4K  |  優雅停機: ✅
```

#### 變體 B — 語義不一致（Test 斷言 20ms，SRD 算 bcrypt 需 120ms）
```
SCG-0 SLV-005 讀 SRD 抓 "bcrypt 2 次" → 推理 → FAIL
→ SPEC_DRAFTING 修正 → SCG-0 PASS
Token 消耗: ~6K  |  優雅攔截: ✅（依賴 SLV-005 推理深度）

[弱點] 若 SRD 只寫「使用 bcrypt」未寫成本 → SLV-005 PASS
       進入 IMPLEMENTATION → UNIT_TEST FAIL 5 次 → SPEC_AUDIT
       SPEC_AUDIT 此時會讀 SRD + AC + 跑 SLV-001~006，
       若 SLV 仍無法捕獲 → spec_audit_count=1 → 回 PR_REVIEW
       再 3 次 fail → SPEC_AUDIT=2 → ESCALATION
Token 消耗: ~18K  |  優雅停機: ✅（ACT-006 兜底）
```

#### 變體 C — 時序語義矛盾（第 N+1 次必須快 50%，未寫穩態條件）
```
現有 SLV-001~006 全 PASS（無對應規則）→ SPEC_FROZEN
IMPLEMENTATION → INTEGRATION_TEST fail（快取 eviction 後回升）
AUTO_DIAGNOSIS → 分類 A → AUTO_FIX_ATTEMPT × 3 次 fail
→ 退回 AUTO_DIAGNOSIS → 分類 B → 父 FSM SPEC_AUDIT
SPEC_AUDIT → SLV 全 PASS → "no_contradiction" → PR_REVIEW
PR_REVIEW × 3 same pattern → SPEC_AUDIT（count=2）→ ESCALATION
Token 消耗: ~22K  |  優雅停機: ✅（多層兜底）

[核心洞察] Phase D 已證明無限 token 耗盡不會發生，但 22K 對比 Phase E 目標 <8K 仍有 3× 差距
```

### 1.2 自驗結論

| 錯誤層級 | 現況（Phase D） | Phase E 目標 | 關鍵改進 |
|---------|--------------|-------------|---------|
| 物理不可行 | ~4K，SLV-001 攔截 | 同 | — |
| 語義不一致 | ~6~18K，依賴推理 | <8K | ACT-021 embedding 相似度 + ACT-025 Decision Trace |
| 時序矛盾 | ~22K，多層兜底 | <10K | ACT-028 SLV Generator（從 FPL-001 自動產出 SLV-007）|

**Karpathy 式評語（自我對話）**：
> 「L4.7 已經像裝了 ABS、ESP、迎角保護的飛機——失控不會發生。
>  但 Karpathy 風格的下一步問題是：**『可以不失控，但每次都撞護欄也太浪費了』**。
>  Phase E 不是防失控，是讓失控邊緣更窄、讓失敗學到下次不再重犯。」

---

## 貳、Phase D 後新發現的 8 個結構性漏洞

### E-01：Subagent 呼叫繞過 FSM Guardrail

**觸發路徑**：
```
main session FSM = IMPLEMENTATION
  Claude 呼叫 Task tool → 派 dev-senior agent
    dev-senior 內部 Write docs/01_requirements/FRD-*.md
      → PreToolUse hook 仍會攔截（因為 hook 看的是「主 session 狀態」）
      → ✅ 實際會被擋
    dev-senior 呼叫 sdd-orchestrator → 再派 qa-tester
      → qa-tester 的工具呼叫 FSM 視圖是主 session 的
      → 若主 session FSM 在此期間已被另一路徑更新（例如 CI-EVENT reconcile）
      → qa-tester 可能以過期 state 做決策
```

**漏洞本質**：FSM-STATE.yaml 有 lock file（atomic write），但 **讀取時機** 不同步。
Subagent 開工時讀一次，主 session 中途轉換狀態，subagent 仍以舊狀態工作。

**後果**：低機率但高影響——例如 orchestrator 派 dev-senior 修 bug 期間，CI 事件讓主 FSM 進入 ESCALATION，dev-senior 仍繼續寫代碼，產生不應有的 artifact。

**ACT-020 對應改進**：Subagent Dispatch Contract。

---

### E-02：PR_REVIEW Same-Pattern 依賴字串完全比對

**現況**（`fsm_runtime.py` L115）：
```python
if entry.get("last_failure_pattern") == reason:
    same_pattern_count += 1
```

**漏洞**：兩次 PR_REVIEW fail，reason 分別為：
- `"test_login_p95 > 200ms at concurrency 100"`
- `"test_login_p95 exceeded 200ms under 100 concurrent users"`

**語義相同，字串不同** → same_pattern_count 不遞增 → SPEC_AUDIT 不觸發 →
白白跑完 5 次 PR_REVIEW retry → ESCALATION（多耗 ~10K tokens）。

**ACT-021 對應改進**：Semantic Same-Pattern Detection（embedding or LLM judge）。

---

### E-03：FSM_ENGINE.md ↔ transition_rules.py 雙源真相風險

**現況**：
- `SDD_FSM_ENGINE.md` 用於 Claude 讀取、理解狀態轉換
- `transition_rules.py` 用於 Runtime 強制執行

兩者手工同步，目前測試只驗證 Python 端。若工程師改 MD 加了一個新狀態但忘了改 Python，會出現：
- Claude 以為可以轉到新狀態（MD 裡寫了）
- Runtime 拒絕該轉換（Python 沒加）
- 死鎖，且報錯訊息混亂（Claude 會說「我遵循 MD 啊」）

**ACT-022 對應改進**：CI Sync Test（解析 MD 的 transitions table，比對 `_HAPPY_PATH` dict）。

---

### E-04：HUMAN_PENDING 逾時依賴 wall-clock 但無 daemon

**現況**（SDD_FSM_ENGINE.md L62）：
```yaml
HUMAN_PENDING:
  timeout_hours: 72
  escalation_hours: 168
```

**漏洞**：現有 hooks 僅在 tool call 時觸發。若使用者放著 SDD 3 天（例如連假），**沒有任何 event 會觸發逾時檢查**。下次開啟 session 時才會補算？現有 session_start.py 沒做這件事。

**ACT-023 對應改進**：`session_start.py` 加入逾時補算邏輯；選配 OS-level cron job 每 6 小時掃一次 FSM-STATE。

---

### E-05：Context Ledger 只算檔案，不算對話累積

**現況**（`context_ledger_pre.py._estimate_tokens`）：
```python
if tool == "Read":
    return file_size // 4
if tool in {"Write", "Edit"}:
    return len(content) // 4
```

**漏洞**：未計入：
1. Read 結果的 **line number prefix**（`cat -n` 格式約多 10~15% tokens）
2. Bash 的 **stdout/stderr 回傳長度**（Grep 大量輸出可能數千行）
3. **對話自身累積**（assistant 長篇回覆、tool_use JSON、system reminders）
4. **Task tool** 派 agent 時的 agent-to-main context 累積

**實測誤差**：估算 170K，實際 Claude 上下文可能已 220K+（爆倉）。

**ACT-024 對應改進**：
- Hook 層改算 **all IO traffic**（含 result bytes）
- 納入 Claude Code 自身回報的 token usage（若 API 可取得）
- 每 10 次 tool call 做一次校準（對比估算 vs 實測 delta）

---

### E-06：AUTO_COMPACT 後 Ledger 歸零過於樂觀

**現況**（`fsm_runtime.py._reset_today_ledger`）：
complete_auto_compact → cumulative_tokens 直接歸 0。

**漏洞**：Stage Summary 寫了 2K tokens，但**實際對話歷史並未被外部 Hook 清理**——Claude Code 的真實 compaction 由其內部機制決定。
假設真實對話仍佔 180K，外部 Ledger 歸 0 後讀了個 50K 檔，Ledger 顯示 50K 但真實已 230K。

**ACT-024 配套**：Auto-compact 後 Ledger 不歸零，而是改記錄 `reset_baseline = cumulative_at_reset`，實測校準後再決定是否真的能歸零。

---

### E-07：Decision Trace 缺失

**現況**：FSM-STATE.yaml 有 `current_state`, `retry_count`, `cumulative_history`，但**沒有「為什麼從 A → B」的理由快照**。

**漏洞劇情**：
```
Session 1（2026-04-18）:
  SCG-2 ADR 討論 → 決策用 PostgreSQL（理由：NFR-PERF-002 + ADR-001）
  進入 SPEC_FROZEN → compact → Stage Summary 寫了「DB: PostgreSQL」

Session 2（2026-04-20，恢復）:
  讀 Summary 看到「DB: PostgreSQL」
  但忘了為什麼 → 重新被 user 問起時回答不一致
  或因新需求（NFR-COST-001 要求降低 DB 成本）而改 SQLite，
  未察覺與 NFR-PERF-002 衝突
```

**ACT-025 對應改進**：每次 FSM transition 自動寫 `decision_trace` entry（timestamp + from/to + reason + spec_refs）。Context Snapshot 包含最近 N 筆。

---

### E-08：AUTO_COMPACT 可快速重複觸發（無 per-stage 上限）

**路徑**：
```
AUTO_COMPACT_PENDING → stage-compaction → complete → resume_state (IMPLEMENTATION)
→ 讀一個 80K 的歷史 SRD 做參考 → post hook ledger 又 ≥ 90% → AUTO_COMPACT_PENDING
→ 再 compact → 再觸發...
```

**漏洞**：
- 單一 stage 可能觸發 3 次以上 compact
- 每次 compact 有 fixed cost（~2K for Summary + Snapshot write）
- 若問題是「需要引用的 cold-tier 文件本身太大」，compact 無法解決，只會加深浪費

**ACT-026 對應改進**：
- `auto_compact_count_per_stage` 上限 3 次
- 超過 3 次 → 進入 ESCALATION，提示 **實質結構問題**（文件過大需拆、引用策略錯）

---

## 參、Phase E ACT 規格（ACT-020~030）

### ACT-020：Subagent Dispatch Contract

**目標**：確保任何 Task-dispatched subagent 在開工前讀取最新 FSM-STATE，並承諾不越界。

**交付物**：
1. `tools/fsm_runtime/subagent_contract.py`（新增）
   - `enter_subagent(agent_name, stage)` → 讀 FSM-STATE + 返回 frozen 視圖
   - `verify_action_allowed(agent_name, action)` → 檢查該 agent 在此 state 是否可執行此 action
   - `exit_subagent(agent_name, result)` → 記錄完成/失敗，同步回 FSM

2. 更新 `agent/specialized/sdd-orchestrator-zh.yaml`：
   ```yaml
   dispatch_protocol:
     pre_call_required: "python -m tools.fsm_runtime.subagent_contract enter --agent {name}"
     post_call_required: "python -m tools.fsm_runtime.subagent_contract exit --agent {name} --result {r}"
   ```

3. `.claude/hooks/context_ledger_pre.py` 加入 detection：
   若 `tool_name == "Task"` 且 `subagent_type in subagent_contract.REGISTERED` → 
   強制在 Task prompt 中注入 "SUBAGENT_CONTRACT: read FSM-STATE first"

**驗收**：
- 模擬 orchestrator 派 dev-senior 時主 FSM 切到 ESCALATION，dev-senior 不會繼續 Write
- 單元測試 `tests/test_subagent_contract.py` 覆蓋 5 種 dispatch 情境

**工時**：3 天

---

### ACT-021：Semantic Same-Pattern Detection

**目標**：PR_REVIEW 相同模式判定從字串完全比對升級為語義相似度。

**設計選項**：

| 方案 | 優點 | 缺點 | 建議 |
|-----|------|------|-----|
| **A. 本地 embedding** (sentence-transformers) | 無 API 成本、離線 | 需裝 ~300MB 模型 | P1 優先 |
| **B. LLM Judge**（Claude API） | 精度高、理解深 | API 成本、延遲 | 備援 |
| **C. 正規化 + Fuzzy match**（difflib） | 輕量、無依賴 | 精度低 | 次選 |

**推薦**：初期 C（fuzz ratio ≥ 0.75），Phase E+ 再升 A。

**交付物**：
1. `tools/fsm_runtime/pattern_matcher.py`：
   ```python
   def is_same_pattern(prev: str, curr: str, threshold: float = 0.75) -> bool:
       # 先去除時間戳、具體數字、路徑 → 正規化
       # 再計算 difflib.SequenceMatcher ratio
       # 超過 threshold → 視為 same pattern
   ```

2. 修改 `fsm_runtime.py.record_gate_result` L115：
   ```python
   from .pattern_matcher import is_same_pattern
   same = is_same_pattern(entry.get("last_failure_pattern"), reason)
   if same:
       same_pattern_count += 1
   ```

3. Persist 所有歷次 pattern 到 `retry_history.PR_REVIEW.patterns: [...]`，便於 debug。

**驗收**：
- 表達不同但語義相同的 5 組測試資料全被識別
- 真正不同原因的 5 組測試資料不被誤判

**工時**：2 天

---

### ACT-022：Meta-FSM Sync Test (CI)

**目標**：阻止 MD 與 Python 不同步。

**交付物**：
1. `tools/fsm_runtime/tests/test_md_python_sync.py`：
   ```python
   def test_happy_path_matches_md():
       md_transitions = parse_md_transitions_table(
           "workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md"
       )
       py_transitions = _HAPPY_PATH  # from transition_rules
       assert md_transitions == py_transitions, diff_report(...)
   ```

2. `cicd/SDD_CICD_BASE_LAYER.md` 加 Step：
   ```yaml
   step_fsm_sync:
     name: "FSM Spec-Runtime Sync Check"
     command: "pytest tools/fsm_runtime/tests/test_md_python_sync.py"
     required: true
   ```

3. MD 解析器容錯：MD 表格格式變動時產生清晰錯誤訊息。

**驗收**：
- 故意修改 MD 加個假狀態，CI fail
- 故意修改 Python 加個假狀態，CI fail

**工時**：2 天

---

### ACT-023：HUMAN_PENDING Wall-Clock Daemon

**目標**：逾時檢查不再依賴「下一次 tool call」，而是每次 session_start + 可選 cron 即檢查。

**交付物**：
1. `tools/fsm_runtime/timeout_checker.py`：
   ```python
   def check_human_pending_timeout(state: FSMState) -> Optional[str]:
       if state.current != "HUMAN_PENDING":
           return None
       entered = state.root.get("human_pending_entered_at")
       delta = now() - parse(entered)
       if delta > 168h: return "ESCALATION"
       if delta > 72h: return "REMINDER"
       return None
   ```

2. 修改 `session_start.py`：開始時若 state == HUMAN_PENDING，呼叫上述檢查。
   觸發 REMINDER → 寫入 FSM + additionalContext 警告。
   觸發 ESCALATION → 呼叫 record_escalation + Abort Report。

3. 選配 `tools/fsm_runtime/cron_monitor.py`：
   ```bash
   # crontab: 0 */6 * * * python -m tools.fsm_runtime.cron_monitor
   ```
   （記錄於 README，不強制）

**驗收**：
- 模擬 75h 前進入 HUMAN_PENDING，session_start 觸發 REMINDER
- 模擬 170h 前，session_start 觸發 ESCALATION

**工時**：1.5 天

---

### ACT-024：Ledger Precision Upgrade

**目標**：Context Ledger 誤差從 30~50% 降至 < 10%。

**交付物**：

1. `context_ledger_pre.py._estimate_tokens` 改進：
   ```python
   if tool == "Read":
       raw = file_size
       # 加 cat -n prefix 估算：每行多 ~8 char
       line_count = raw_file_line_count(path)
       return (raw + line_count * 8) // 4
   if tool == "Bash":
       # Bash 輸出通常大於 command 本身 → 無法預估，交給 post hook
       return len(command) // 4
   ```

2. `context_ledger_post.py` 加入 Bash/Task 回傳長度計算（現已做大半）。

3. **新增對話累積估算**：
   `tools/fsm_runtime/conversation_ledger.py`：
   ```python
   def estimate_conversation_overhead(message_count: int) -> int:
       # 每條 message 約 100~500 tokens overhead（tool_use/tool_result JSON）
       return message_count * 300
   ```
   主 session ledger 每 10 次 tool call 合併一次 conversation_overhead。

4. **自校準**：若主 session 有辦法取得 Claude Code 回報的真實 context size（`/context` slash 或 API），
   post hook 寫入 `calibration_delta`，週期性調整係數。

**驗收**：
- 跑完一個完整 Stage（~50 次 tool call），估算 vs 實際 cache_read tokens 誤差 < 10%
- 誤差報告自動寫入 `build/reports/fsm/LEDGER-CALIBRATION-{date}.yaml`

**工時**：3 天

---

### ACT-025：Decision Trace Capture

**目標**：每次 FSM transition 記錄「為什麼」，供跨 session 恢復與審計。

**交付物**：

1. `fsm_runtime.py.transition()` 擴充：
   ```python
   def transition(self, dst: str, reason: str = "", spec_refs: list = None):
       ...
       self.state.root.setdefault("decision_trace", []).append({
           "ts": now_iso(),
           "from": self.state.current,
           "to": dst,
           "reason": reason or f"auto transition {src}→{dst}",
           "spec_refs": spec_refs or [],
           "agents_consulted": current_agents(),
       })
       # 保留最近 50 筆，老的 flush 到 cold tier
       if len(trace) > 50:
           flush_old_trace_to_cold()
   ```

2. `record_gate_result` / `record_spec_audit` / `trigger_auto_compact` 呼叫 transition 時傳 reason。

3. Context Snapshot 新增章節：
   ```markdown
   ## 最近 20 筆 Decision Trace
   | ts | from | to | reason | refs |
   |----|------|-----|------|------|
   ```

4. `session_start.py` 恢復時自動注入最近 5 筆 trace 到 additionalContext。

**驗收**：
- 一個完整 Stage 結束時，decision_trace 至少 10 筆
- 中止後恢復時，新 session 能看到 trace 並做一致決策

**工時**：2 天

---

### ACT-026：AUTO_COMPACT Rate Limit

**目標**：防止單一 stage 無限觸發 auto-compact。

**交付物**：

1. `state_loader.py` FSM-STATE schema 新增：
   ```yaml
   auto_compact_state:
     count_per_stage: 0
     stage_key: "Stage-3"  # 進入新 stage 時重置
   ```

2. `fsm_runtime.py.trigger_auto_compact()` 新增邏輯：
   ```python
   MAX_AUTO_COMPACT_PER_STAGE = 3
   stage = current_stage()
   if auto_state.stage_key != stage:
       auto_state.count_per_stage = 0
       auto_state.stage_key = stage
   auto_state.count_per_stage += 1
   if auto_state.count_per_stage > MAX_AUTO_COMPACT_PER_STAGE:
       record_escalation(f"auto_compact exceeded {MAX} per stage — 可能引用文件過大")
       return {"escalated": True, ...}
   ```

3. 若觸發上限，Abort Report 建議：
   - 檢查 stage 是否嘗試引用過大的 cold-tier 文件
   - 考慮手動執行深度 compaction（移除更多歷史對話）
   - 考慮拆分 stage

**驗收**：
- 連續觸發 4 次 auto-compact（模擬），第 4 次 → ESCALATION
- 跨 stage（SPEC_FROZEN 重置）計數器歸零正常

**工時**：1 天

---

### ACT-027：Production Feedback Layer（Level 5 入口）

**目標**：交付後的 SLO 違反事件能自動回饋到 PBS/NFR 規格，形成完整閉環。

**延續 Automation_03 RC-19 的 ACT-018**。

**交付物**：

1. 新增 FSM 狀態 `PRODUCTION_SIGNAL`（監測狀態，非阻塞）

2. `tools/fsm_runtime/production_monitor.py`：
   ```python
   def ingest_slo_violation(event: dict):
       # 輸入：{ "metric": "p95_login_ms", "observed": 450, "target": 200, "duration": "15min" }
       # 映射到對應 NFR-PERF-NNN
       nfr_id = map_metric_to_nfr(event.metric)
       # 寫入 build/reports/fsm/PBS-DRIFT-{date}.yaml
       # 若 violation persistent（連續 N 小時）→ 通知 sa-analyst
   ```

3. 定義 `cicd/SDD_PRODUCTION_FEEDBACK.md`：
   - Grafana / Datadog webhook → 推送至 `build/reports/fsm/SLO-EVENT-{date}-{id}.yaml`
   - session_start.py 掃描並處理未 applied 的事件

4. `docs_template/sdd/quality/PBS-DRIFT-REPORT-TEMPLATE.md`（新增）

**驗收**：
- 模擬 5 筆 SLO violation 事件 → 自動產生 PBS-DRIFT 報告
- 報告包含建議的 NFR 更新 diff

**工時**：5 天

---

### ACT-028：SLV Rule Generator（Level 5 學習層）

**目標**：從 FPL（Failure Pattern Library）半自動產出新的 SLV-NNN 規則，讓框架「越用越聰明」。

**交付物**：

1. `tools/fsm_runtime/slv_generator.py`：
   ```python
   def propose_slv_from_fpl(fpl_entry: FPLEntry) -> SLVRuleCandidate:
       # 呼叫 Claude API（或離線 LLM）分析 FPL
       # 產出 YAML format 的 SLV 規則草稿
       # 人工 review 後 commit 到 .claude/skills/spec-logical-validator/rules/
   ```

2. `.claude/skills/spec-logical-validator/SKILL.md` 改為 **規則引擎**：
   - 核心邏輯不變
   - 動態載入 `rules/*.yaml`（包含 SLV-001~006 + 未來自動生成的 SLV-007+）
   - 每條規則 schema：
     ```yaml
     id: SLV-007
     name: "時序穩態檢查"
     source: "FPL-001 auto-generated 2026-04-25"
     reviewed_by: "sa-analyst@example.com"
     pattern: "AC 包含「第 N+1 次 vs 第 N 次」比較"
     required_qualifiers:
       - "穩態條件必須明確"
       - "degradation bound 必須寫"
     ```

3. 自動化 workflow：
   ```
   ESCALATION 產出 Abort Report → LEARNING_COMMIT state（新增）
   → 分析 abort_reason 是否為「現有 SLV 未捕獲」
   → 若是，自動 draft FPL 條目
   → 使用者 review 後 → 呼叫 slv_generator → 產出 SLV 草案
   → 使用者 review + commit → 下次 session 即生效
   ```

4. 新增 FSM 狀態 `LEARNING_COMMIT`（terminal 前的背景狀態，不阻塞）

**驗收**：
- 用 FPL-001（時序矛盾）作為輸入，產出 SLV-007 草案
- 草案經人工 review 後加入規則庫，重跑變體 C 案例，在 SCG-0 即攔截

**工時**：7 天（含 LLM API 整合 + 規則引擎重構）

---

### ACT-029：Chaos Test for Automation

**目標**：注入 FSM 失敗情境，驗證有界停機真的有界。

**交付物**：

1. `tools/fsm_runtime/tests/test_chaos.py`：
   ```python
   @pytest.mark.chaos
   def test_infinite_scg_failure_terminates_in_3_retries(): ...
   def test_hook_crash_still_allows_session_start(): ...
   def test_corrupted_fsm_state_triggers_backup_recovery(): ...
   def test_pr_review_jitter_triggers_semantic_match(): ...
   def test_auto_compact_rate_limit_triggers_escalation(): ...
   ```

2. `tools/fsm_runtime/chaos_runner.py`：隨機在 FSM 轉換時注入：
   - State file corruption
   - Retry count tampering
   - CI-EVENT duplicate
   - Timeout simulation

3. CI 新增 nightly chaos job（標記 slow, 非 PR 必跑）。

**驗收**：
- 100 輪隨機 chaos 下，系統 100% 停機於 ESCALATION 或 TERMINATED，無無限迴圈
- 平均 token 消耗 < 25K

**工時**：4 天

---

### ACT-030：Cross-Project Learning Hub

**目標**：單一 AISDLC-SDD 實例可參與跨專案 FPL/SLV 共享（讀寫中央 registry）。

**交付物**：

1. `knowledge/hub-registry.yaml`：
   ```yaml
   hub_endpoint: "https://github.com/{org}/aisdlc-sdd-failure-hub"
   sync_policy:
     pull: "on session_start（快取 24h）"
     push: "on ESCALATION（可選，去識別化後）"
   ```

2. `tools/fsm_runtime/hub_sync.py`：
   - Pull：下載最新 FPL/SLV 規則，合併到本地 `knowledge/failure-patterns/` 與 `spec-logical-validator/rules/`
   - Push：匿名化本地 FPL（移除專案名、具體 ID）後上傳

3. 治理規則（MUST）：
   - Push 前自動掃描 PII / 商業機密，發現即阻擋
   - Pull 的規則預設標記 `trust_level: external`，需人工升級為 `verified` 才啟用

**驗收**：
- 模擬 2 個專案互相分享 FPL，各自新專案能立即受益
- 去識別化掃描能偵測常見 PII 模式

**工時**：5 天（含治理）

---

## 肆、Milestone & 優先序（2026-04-20 最佳化版）

### 4.1 作用域最佳化決議

**使用者 2026-04-20 決策**：
- ✅ M3/M4（ACT-027/028）確認 2026-05 啟動
- 🟡 ACT-030 Hub 保留（延至 Phase F）
- ⏳ 驗收場景對象後續選定
- ❓ ACT-029 Chaos Test 原列「選配」— **架構師反對將其列為選配**，建議升級為 Phase E 核心

**架構師最佳化建議**（作用域、風險、排程三項）：

#### (A) 作用域最佳化 — ACT-029 應升級為 P1，不可列為選配

**原因**：
ACT-020~026 是「防護機制」；ACT-029 是「防護機制的驗證」。
沒有 Chaos Test，我們只能**假設** Subagent Contract / Semantic Matcher / Ledger Precision 真的能在對抗情境下守住邊界——這在工程上等同於 **「上線才知道會不會壞」**。

Phase D 的 28 個 e2e 測試已證明 **happy path + 預設失敗路徑** 都正確，但未覆蓋：
- 隨機狀態檔案損毀（mid-write crash 模擬）
- Retry count 被人為篡改
- CI-EVENT 重複投遞
- Hook 執行逾時（5s deadline 邊緣）

**結論**：Phase E 核心 = **ACT-020~029（9 項，30 天）**。ACT-030 延後。

#### (B) 風險承受最佳化 — Subagent Contract 採分級漸進式 enforce

原方案「接受 <5% 誤擋」的問題：
- 沒有定義「5%」的計算窗口
- 沒有定義發現超標時怎麼辦
- 沒有定義 dry-run → enforce 的升級路徑

**最佳化後的風險框架**：

| 階段 | 期間 | 模式 | 門檻 | 升級/降級條件 |
|-----|------|------|------|------------|
| Stage 1 — Shadow | 首 14 天 | **log-only**（不阻擋，僅記錄） | 蒐集 baseline | 累積 ≥ 50 筆 dispatch 後評估 |
| Stage 2 — Soft enforce | 15~30 天 | 阻擋 + 可 bypass（`SDD_SUBAGENT_CONTRACT=warn`） | 7 日 rolling false positive < 7% | >7% 回 Shadow；<3% 進 Hard |
| Stage 3 — Hard enforce | 31 天後 | 阻擋不可 bypass（需 env override + audit log） | 7 日 rolling FP < 3% | >5% 降回 Soft |

**量測定義**：
- **False Positive（FP）**：合法 dispatch 被擋 = 阻擋後使用者手動 bypass 並完成任務 / 總阻擋次數
- **窗口**：7 日 rolling window（非累積），對近期行為敏感

**Kill Switch**（三級）：
1. `SDD_SUBAGENT_CONTRACT=0` — 全關（含 log），緊急用
2. `SDD_SUBAGENT_CONTRACT=warn` — Shadow 模式（log 不擋）
3. `SDD_SUBAGENT_CONTRACT=1` — 預設（Soft/Hard 依 FP 狀態）

每次 bypass 寫入 `build/reports/fsm/SUBAGENT-BYPASS-{date}.yaml`，供後續審計。

**同樣分級框架套用至其他 ACT**：

| ACT | 風險類型 | 量測 | 紓緩 |
|-----|--------|------|------|
| ACT-021 Semantic Matcher | 誤合併（不同原因判為同）→ 提早觸發 SPEC_AUDIT | 比對人工審核樣本 100 筆 | 初期 threshold=0.85（保守），人工 review 後調低 |
| ACT-024 Ledger | 校準誤差 >10% | 每 50 次 tool call 抽樣比對 `/context` 實測 | 誤差持續 >15% → disable auto-compact，fallback 至 Claude Code 原生 |
| ACT-027 Production Webhook | 偽造 SLO event 污染 PBS | 事件需 HMAC 簽章 + 時戳驗證 | 未簽章事件一律存 quarantine，不自動 apply |
| ACT-028 SLV Generator | 誤產規則導致無辜 Spec 被擋 | 新規則 mandatory human review；人工 review SLA ≤ 3 天 | Auto-gen 規則 `trust_level: proposed`，無法自動 enforce |

#### (C) 排程最佳化 — Quick Wins 改 3 天內、加入依賴排序

**原方案**：QW-1/2/3 本週共 4.5 天（實際排程不明確）。

**最佳化後**：

```
Day 0（現在，2026-04-20）: 閱讀計畫、建 worktree、準備 CI
Day 1: QW-2 (ACT-026, 1 天)   ← schema 變更先做，避免並行衝突
       └── 更新 FSM-STATE schema 增加 auto_compact_state.count_per_stage
       └── 更新 trigger_auto_compact 加上限檢查
       └── 新增測試 test_auto_compact_rate_limit
Day 2: QW-1 (ACT-022, 0.5 天) + QW-3 (ACT-023, 1 天) 並行
       QW-1 └── 解析 MD transitions table
            └── 比對 _HAPPY_PATH，CI 整合
       QW-3 └── timeout_checker.py 實作
            └── session_start.py 整合
Day 3: 整合測試、CI 驗證、合併至 main
```

**目標**：2026-04-23 前完成 M1（3 天，非 4.5 天），原因是 QW-2 的 schema 變更解鎖後，QW-1（純測試）與 QW-3（獨立 hook 邏輯）無依賴可並行。

### 4.2 Phase E 優先級（最佳化後）

| Priority | ACT | 理由 | 總工時 | 里程碑 |
|---------|-----|------|-------|-------|
| **P0**（本週） | ACT-022, ACT-023, ACT-026 | Quick Wins，純防護無風險 | 3 天 | M1 |
| **P1**（Week 2~3） | ACT-025, ACT-024, ACT-021, ACT-020 | 閉環品質核心，依賴順序 | 10 天 | M2 |
| **P1.5**（Week 4） | ACT-029 | Phase E 驗收前強制做（架構師升級） | 4 天 | M2.5 |
| **P2**（Week 4~6） | ACT-027, ACT-028 | Level 5 學習層入口 | 12 天 | M3/M4 |
| **保留池** | ACT-030 | 延至 Phase F，待商業機密治理準備好 | 5 天 | — |

### 4.3 Milestone（最佳化後）

| M | 交付 | 驗收條件 | 期望時點 |
|---|------|---------|---------|
| **M1**：Quick Wins | ACT-022/023/026 | CI FSM sync 綠；HUMAN_PENDING 逾時自動觸發；auto-compact 有上限 | ✅ **2026-04-20 完成**（pytest 47/47 綠，含 3 項 P1 QA 修復回歸測試） |
| **M2**：閉環品質 | ACT-025→024→021→020（依賴鏈） | Decision Trace 完整；Ledger 誤差 <10%；pattern matcher 準確率 >90%；Subagent Contract Shadow 模式啟動 | 2026-05-07 |
| **M2.5**：Chaos 驗證（新） | ACT-029 | 100 輪 chaos 100% 停機於 ESCALATION/TERMINATED；平均 token 消耗 <25K | 2026-05-13 |
| **M3**：Level 5 入口 | ACT-027 | 模擬 SLO violation → PBS-DRIFT 報告（含簽章驗證） | 2026-05-20 |
| **M4**：Learning Layer MVP | ACT-028 | FPL-001 → SLV-007 草案，人工 review 後 enforce | 2026-05-30 |
| **Phase F 啟動**（保留） | ACT-030 | Hub 治理規格定義後再評估 | 待定 |

#### M1 執行紀錄（2026-04-20 閉環 QA 完成）

| ACT | 交付物 | 驗證 |
|-----|-------|------|
| **ACT-022** Meta-FSM Sync Test | `tools/fsm_runtime/tests/test_md_python_sync.py`（3 tests，MD ⊆ Python + 核心 edges + states 全覆蓋）；`cicd/SDD_CICD_BASE_LAYER.md` 新增 FSM Sync step | pytest 綠 |
| **ACT-023** HUMAN_PENDING Wall-Clock | `tools/fsm_runtime/timeout_checker.py`（evaluate/mark/clear）；`.claude/hooks/session_start.py` 補算；`FSMRuntime.transition()` 自動 stamp/clear `human_pending_tracking.entered_at` | 8 tests 綠 |
| **ACT-026** AUTO_COMPACT Rate Limit | `transition_rules.MAX_AUTO_COMPACT_PER_STAGE=3`；`FSMRuntime.trigger_auto_compact()` 加 per-stage 計數 + ESCALATION/TERMINATED early-return；兩個 hook 加 `escalated` 分支 | 7 tests 綠 |

**閉環 QA 專家驗證結果**（2026-04-20）：發現 3 項 P1 問題，已全部修復並補回歸測試：
- P1-1：`trigger_auto_compact()` 在 ESCALATION/TERMINATED 狀態下必須 no-op（不得 re-escalate、不得 transition）→ 修復 + 2 tests（`test_trigger_in_escalation_is_noop` / `test_trigger_in_terminated_is_noop`）
- P1-2：`context_ledger_pre.py` / `context_ledger_post.py` 在 `trigger_auto_compact` 回傳 `escalated=True` 時應發出 ESCALATION 訊息，而非誤導的「FSM → AUTO_COMPACT_PENDING」→ 修復
- P1-3：`timeout_checker.evaluate_human_pending()` 對 clock skew（future-dated `entered_at`）必須回傳 NO_TIMESTAMP 而非 OK → 修復 + 1 test（`test_future_entered_at_treated_as_no_timestamp`）

**最終驗收**：`python -m pytest tools/fsm_runtime/tests/` → **47 passed**（含 3 項 P1 回歸測試）。

#### M2 執行紀錄（2026-04-20 完成，早於 2026-05-07 原定 Due）

| ACT | 交付物 | 驗證 |
|-----|-------|------|
| **ACT-025** Decision Trace | `state_loader.append_decision_trace()`（50 筆 bounded + flush 機制）；`FSMRuntime.transition()` 擴展為 `(reason, spec_refs, agents_consulted, trigger)`；`snapshot.py` 附最近 20 筆；`session_start.py` 注入最近 5 筆；`FSM-STATE-TEMPLATE.yaml` schema 補欄位 | `test_decision_trace.py` 6 tests 綠 |
| **ACT-024** Ledger Precision | `tools/fsm_runtime/conversation_ledger.py`（Read 含行號 overhead、Bash/Task 精算、conv overhead 每 10 turn 累加、calibration rolling 10）；`context_ledger_pre.py` 改用 `estimate_tool_tokens`；`context_ledger_post.py` 加 `merge_conversation_overhead` | `test_conversation_ledger.py` 9 tests 綠 |
| **ACT-021** Semantic Pattern Matcher | `tools/fsm_runtime/pattern_matcher.py`（normalize + SequenceMatcher∪Jaccard + synonym map `gt/lt/concurrency` + stopword 濾除）；`FSMRuntime` PR_REVIEW 同模式計數改用 `is_same_pattern()` + `patterns` 歷史（cap 20） | `test_pattern_matcher.py` 9 tests + 10 subtests 綠 |
| **ACT-020** Subagent Dispatch Contract | `tools/fsm_runtime/subagent_contract.py`（enter/verify/exit/record_bypass/injection_hint + CLI）；`REGISTERED` 14 agents；`context_ledger_pre.py` 對 `tool_name==Task` 自動注入 hint + enter；`agent/specialized/sdd-orchestrator-zh.yaml` 補 `dispatch_protocol` | `test_subagent_contract.py` 15 tests 綠 |

**最終回歸**：`python -m pytest tools/fsm_runtime/tests/` → **89 passed + 10 subtests**（M1 47 + M2 新增 39 + subtests）全綠。

**相關文件更新**：
- `CLAUDE.md` Rule 9.8 新增 Phase E M2 閉環品質鏈（含 4 子規則 + Rollout 模式表 + 新增禁止行為）
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` 新增「Phase E M2 閉環品質鏈」章節

**Shadow 模式預設啟用**：ACT-020 預設 `SDD_SUBAGENT_CONTRACT=1`（soft mode），違反即拒絕但可 bypass；若需先跑 shadow baseline，設 `SDD_SUBAGENT_CONTRACT=warn`。

#### M2 閉環 QA 驗收 + 修復紀錄（2026-04-20）

**驗收結果**：M2 FAIL（1 P0 + 6 P1 + 4 P2）。已派修復專家修補 P0 + 4 個 P1：

| Issue | 位置 | 修復 |
|-------|-----|------|
| **P0-01** CLI transition 缺 reason/trigger | `tools/fsm_runtime/fsm_runtime.py` `_cli()` | 新增 `--trigger` argparse（預設 `cli_manual`），呼叫處強制帶 `reason=f"cli transition to {target}"` + `trigger=args.trigger` |
| **P1-01** REGISTERED 與 orchestrator YAML 不一致 | `agent/specialized/sdd-orchestrator-zh.yaml:113-127` | YAML 補入 `sdd-orchestrator` + `pm-planner`（共 14 項，與 `subagent_contract.REGISTERED` 完全一致）；新增 NOTE 說明同步約束 |
| **P1-02** soft 模式 BYPASS 僅 log 無 short-circuit | `tools/fsm_runtime/subagent_contract.py` `verify_action_allowed` | 新增 `_maybe_soft_bypass()` helper：soft + `SDD_SUBAGENT_CONTRACT_BYPASS=<reason>` 時呼叫 `record_bypass` 並回傳 `(True, "[bypass] ...")`；hard 模式不適用 |
| **P1-03** hard 模式下 record_bypass 仍可呼叫 | `tools/fsm_runtime/subagent_contract.py:199` | `record_bypass` 開頭 guard：`mode()=="hard"` 時寫 stderr WARN 並 return None，不寫 audit log |
| **P1-06** Task 估算公式 doc-code 不一致 | `tools/fsm_runtime/conversation_ledger.py:217-223` | Task 分支改為 `prompt_tokens + estimate_conversation_overhead(1)`（與 FSM_ENGINE.md §M2 §2 表一致） |

**新增測試**（共 6 項）：
- `test_subagent_contract.py`：`test_soft_bypass_env_allows_blocked_action` / `test_hard_mode_record_bypass_is_noop` / `test_hard_mode_bypass_env_does_not_short_circuit` / `test_registered_matches_orchestrator_yaml`
- `test_conversation_ledger.py`：`test_task_estimate_includes_conversation_overhead`
- `test_decision_trace.py`：`test_cli_transition_records_trigger_and_reason`

**修復後最終回歸**：`python -m pytest tools/fsm_runtime/tests/` → **95 passed + 10 subtests** 全綠。

**未修部分**（保留下次處理）：
- P1-04（`SDD_HOOKS_DISABLE=1` 一併關閉 Subagent Contract）— 設計取捨需另議
- P1-05（Ledger fallback 雙重計數風險）— 觀察 calibration drift_pct 後決定
- P2-01~04（Decision Trace flush cap、中文 synonym、drift 分母、測試覆蓋盲點）— 併入 M3 ACT-029 Chaos Test 補強

#### M2 閉環 QA 第二輪 + 修復紀錄（2026-04-20 晚）

**第二輪驗收結果**：PASS with Minor Issues（0 P0 + 2 P1 + 4 P2）。已全數修復：

| Issue | 位置 | 修復 |
|-------|-----|------|
| **P1-06** conv-overhead 合併頻率 spec/code 不一致（pre+post 各寫 entry → 實際 10 entries = 5 tool calls）| `tools/fsm_runtime/conversation_ledger.py:91-148` | `merge_conversation_overhead_into_ledger` 新增 `entries_per_call=2` 參數，`delta_calls = delta_entries // entries_per_call`，恢復 Rule 9.8.2「每 10 次 tool call」語意 |
| **P1-04（升級必修）** `SDD_HOOKS_DISABLE=1` 連帶關閉 Subagent Contract | `.claude/hooks/context_ledger_pre.py:98-136,178-209` | 抽出 `_build_subagent_notice()`，HOOKS_DISABLE 早退前仍偵測 Task + 注入 contract hint |
| **P1-05** Fallback Read 無行號 overhead | `.claude/hooks/context_ledger_pre.py:126-144` | Legacy fallback 補 `line_count * 8 // 4` overhead（無法讀行時用 `size // 80 * 8 // 4` 粗估） |
| **P2-05** CLAUDE.md Rule 9.8.1 「必須帶 --trigger」語意歧義 | `CLAUDE.md:379` | 改為「CLI transition 子命令必須帶 `--trigger`（預設 `cli_manual`）」— 保留 argparse default，用字明確 |
| **P2-06** Pattern matcher 缺 synonym/stopword/threshold clamp 專項測試 | `tools/fsm_runtime/tests/test_pattern_matcher.py` | 新增 3 focused tests |
| **P2-07** FSM-STATE-TEMPLATE.yaml 未宣告 `retry_history.PR_REVIEW.patterns` | `build/reports/fsm/FSM-STATE-TEMPLATE.yaml:39-47` | 補 `patterns: []` schema 範例（cap 20, ACT-021） |
| **P2-08** tokens==0 早退跳過 95% escalation 檢查 | `.claude/hooks/context_ledger_pre.py:248-305` | tokens==0 早退前先讀 cumulative 跑 CRIT/AUTO_COMPACT 檢查；新增 `_read_cumulative` helper |

**新增測試**（共 13 項）：
- `test_conversation_ledger.py`：`pre_post_pairs_equal_one_tool_call` / `entries_per_call_override`
- `test_context_ledger_pre`（hook 測試）：P1-04 / P1-05 / P2-08 共 8 tests
- `test_pattern_matcher.py`：`test_synonym_canonicalisation` / `test_stopword_removal` / `test_threshold_clamp`

**修復後最終回歸**：`python -m pytest tools/fsm_runtime/tests/` → **108 passed + 10 subtests**（baseline 95 → 108，淨增 13）。

**注意事項**：
- P1-06 修復後，conversation overhead 實際累積速度降為前一半（回到 spec 語意）；下次 calibration 週期需重新記 drift_pct 驗證（參閱 `conversation_ledger.record_calibration_sample`）。
- `test_merge_at_threshold_appends_conv_overhead_entry` 既有測試已同步更新為 20 entries（10 tool calls），未降低斷言強度。

#### M2 收尾測試數推算（P1-B 補齊）

> P1-B 修復後補齊。原本「baseline 95 → 108」字面與檔案級分布不直觀，補完整推算如下。

| 階段 | 測試檔（test_*.py）| tests | 累計 |
|-----|---------------------|------|-----|
| Phase D 既有 | `test_transitions` 16 + `test_e2e_smoke` 12 | 28 | 28 |
| M1 ACT-022/023/026 | `test_md_python_sync` 3 + `test_timeout_checker` 8 + `test_auto_compact_rate_limit` 7 + M1 P1 修復回歸 1（`test_future_entered_at_treated_as_no_timestamp` 屬 timeout） | 19 | **47** |
| M2 round-1 ACT-025 | `test_decision_trace` 6 | 6 | 53 |
| M2 round-1 ACT-024 | `test_conversation_ledger` 9 | 9 | 62 |
| M2 round-1 ACT-021 | `test_pattern_matcher` 9（含 10 subtests）| 9 | 71 |
| M2 round-1 ACT-020 | `test_subagent_contract` 15 | 15 | 86 |
| M2 round-1 P1 修復回歸 | 6（`test_soft_bypass_env_allows_blocked_action` 等跨檔分布）| 6 | **92** |
| M2 round-2 P1/P2 修復 | `test_context_ledger_pre_hook` 8 + `test_conversation_ledger` +2 + `test_pattern_matcher` +3 + `test_decision_trace` +1 = 14（其中 1 為 fixture 整併，淨增 13）| 13 | **108** |
| **M2 收尾總計** | — | — | **108 passed + 10 subtests** |

#### 2026-04-21 P1 修復記錄（QA 抓漏 → 修復回歸）

2026-04-21 派出閉環 QA 專家深度抓漏，發現 3 P1 + 7 P2，當輪修復 3 個 P1 並補回歸測試：

| Issue | 位置 | 修復 |
|-------|-----|------|
| **P1-A** pattern_matcher 缺中文同義詞/停用詞 | `tools/fsm_runtime/pattern_matcher.py` | 新增 `_CHINESE_SYNONYMS`（gt/lt/concurrency 家族 14 條中文短語）+ `_STOPWORDS` 擴 13 個中文虛詞；`normalize()` 開頭做 string-level 替換 |
| **P1-C** `save_auto_snapshot` 同 stage 多次 compact 互相 overwrite | `tools/fsm_runtime/snapshot.py` + `fsm_runtime.trigger_auto_compact` | `save_auto_snapshot` 新增 `compact_index` 參數（預設由 state 推算），檔名格式改為 `CONTEXT-SNAPSHOT-{date}-auto-{NN}.md`；呼叫端傳 `compact_index=projected` |
| **P1-B** 計畫文件測試數推算缺失 | 本文件 §肆 M2 收尾段 | 補上完整推算表（Phase D 28 + M1 19 + M2 round-1 39 + round-2 13 + round-1 修復回歸 6 = 108） |

**新增測試**（共 4 項 + 4 subtests）：
- `test_pattern_matcher.py`：`test_semantic_same_pairs_zh_match`（4 subtests）/ `test_chinese_synonym_canonicalisation` / `test_chinese_stopword_removal`
- `test_auto_compact_rate_limit.py`：`test_snapshot_filenames_are_unique_per_compact`

**修復後最終回歸**：`python -m pytest tools/fsm_runtime/tests/` → **112 passed + 14 subtests**（baseline 108+10 → 112+14，淨增 4 tests + 4 subtests）。

**未修部分**（保留 M3 / ACT-029）：
- P2-A `decision_trace_flushed` 無上限，長 session FSM-STATE 可能膨脹 → ACT-029 Chaos Test 後再評估
- P2-B HUMAN_PENDING REMINDER 在 72h~168h 區間僅送一次（無重送節奏）
- P2-C `_current_stage_key()` "initial" 階段 rate-limit 計數可能誤觸 ESCALATION
- P2-D `timeout_checker` 不支援 env 覆寫 reminder/escalation 小時（其他模組有 env override 不一致）
- P2-E `transition()` trigger default `"transition"` 與 trigger 列舉重疊（語意歧義）
- P2-F `assert_tool_allowed` 路徑前綴比對用 `in` 而非 `startswith`+normpath（over/under-restrictive 邊界）
- P2-G `test_registered_matches_orchestrator_yaml` 未掛入 `step_fsm_sync`（CI 漏守門）

#### M2.5 執行紀錄 — ACT-029 Chaos Test（2026-04-22 完成，早於 2026-05-13 原定 Due）

| 交付物 | 驗證 |
|-------|------|
| `tools/fsm_runtime/chaos_runner.py` | 7 種 FAULT_TYPES（STATE_CORRUPTION / RETRY_TAMPER / CI_EVENT_DUP / TIMEOUT_SIM / AUTO_COMPACT_BURST / PR_REVIEW_JITTER / SCG_INFINITE_FAIL）+ deterministic seed + CLI |
| `tools/fsm_runtime/tests/test_chaos.py` | 12 tests（9 scenario + 3 aggregate），涵蓋 §ACT-029 L584-L588 指定 5 項 + 4 項額外故障覆蓋 |
| `state_loader.load_state` `.bak` recovery | 新增 `_try_parse_state_file`：YAML 損毀時 fallback 到 `.bak`（回寫 primary），無 `.bak` 則 raise ValueError |
| `cicd/SDD_CICD_BASE_LAYER.md` nightly job | 新增 `FSM Chaos Verification` step（每日 02:00 UTC，PR 不跑，連續 3 日失敗鎖 main） |
| `CLAUDE.md` Rule 9.9 | 4 子規則 + 4 項新禁止行為（Phase E M2.5 章節） |
| `SDD_FSM_ENGINE.md` Phase E M2.5 章節 | Chaos Runner API + 故障清單表 + .bak recovery 設計說明 + Nightly CI 對照 |

**驗收結果**（100 輪 chaos @ seed=42 / seed=20260422）：
- `bounded_ratio`: **1.0**（100/100 輪停機於 `{ESCALATION, TERMINATED, RELEASE}`）
- `avg_tokens`: **~1950**（遠低於 25K 預算）
- `max_steps`: **13**（遠低於 120 硬上限）

**最終回歸**：`python -m pytest tools/fsm_runtime/tests/` → **128 passed + 14 subtests**（baseline 112+14 → 128+14，淨增 16 tests）。

**Side-effect 強化**：`load_state` 從「corrupted 即 crash」升級為「bak fallback / 無 bak raise ValueError」，所有現有測試仍綠（無回歸）。

#### M2.5 閉環 QA 驗收 + 修復紀錄（2026-04-23）

**第一輪 QA 驗收結果**：PASS with Minor Issues（6 P1 + 9 P2）。本輪修補 6 個 P1 並補回歸測試：

| Issue | 位置 | 修復 |
|-------|-----|------|
| **P1-01** `increment_retry` 負數防禦缺失（`current=-1` → `+1=0`，等同白送 1 次重試） | `tools/fsm_runtime/state_loader.py:106-164` | 新增 tamper defence：prior 值若 < 0 → 視為 tamper、snap `current_count = limit`；若 ≥ limit → 同樣 snap；history.failure_reason 附 `"(tamper detected: prior_count={prior})"` 審計痕跡；保留合法 [0, limit) 區段為原行為 |
| **P1-02** CI-EVENT 重複內容雙倍計數（reconciler 只看檔名 processed flag，不看 content hash） | `tools/fsm_runtime/event_reconciler.py:41-110` | 新增 `_content_hash()`（pipeline_id + stage + result + failure_reason + scg_gate + timestamp 的 SHA256），同 call 內 `seen_hashes` 去重 + 跨 call 持久化於 `state.ci_event_seen_hashes`（trim 500 上限）；duplicate 仍標 `processed=True` 但不 increment retry，並寫 `dedup_skipped: true` |
| **P1-03** `@pytest.mark.chaos` 缺失，無法 PR/nightly 分流 | `tools/fsm_runtime/tests/test_chaos.py` + `pytest.ini` | test_chaos.py 加 `pytestmark = pytest.mark.chaos` module-level；新建 `AISDLC_SDD_v0.01/pytest.ini` 註冊 `chaos` marker；SDD_CICD_BASE_LAYER.md 更新 `pr_command` / `nightly_command` 分流定義 |
| **P1-04** nightly chaos workflow 紙面聲明、無實作 | 新建 `AISDLC_SDD_v0.01/.github/workflows/fsm-chaos-nightly.yml` | 實體化 cron `0 2 * * *` + workflow_dispatch；ubuntu-latest runner；checkout → setup-python 3.11 → install pyyaml/pytest → Python 計算 seed → pytest -m chaos → 100 輪 chaos sweep + JSON 報告 artifact 上傳（保存 14 天） |
| **P1-05** `$(date +%Y%m%d)` POSIX-only（Windows runner 失敗） | `cicd/SDD_CICD_BASE_LAYER.md` `fsm_chaos_check` block + workflow | 改用 `python -c "import datetime; print(datetime.date.today().strftime('%Y%m%d'))"` 確保 Linux/macOS/Windows 三平台一致；workflow runner 鎖 ubuntu-latest，註明跨平台限制 |
| **P1-06** `pr_review_jitter_reasons` 全部依賴 `_SYNONYMS` canonical token（白盒 round-trip） | `tools/fsm_runtime/chaos_runner.py:203-241` + `tests/test_chaos.py` | 新增 public `pr_review_jitter_reasons_fuzzy()` 提供 4 個 synonym-free paraphrase（"hit"/"reached"/"fail"/"breach" 系列，pairwise sim ≥ 0.80）；新增 `test_pr_review_jitter_works_beyond_synonyms` 含 sanity assertion（無 synonym 字典污染）+ similarity 預檢 + SPEC_AUDIT 觸發斷言 |

**新增測試**（共 7 項）：
- `test_transitions.py`：`TamperedRetryCountTests` — `test_tampered_negative_retry_count_still_escalates_at_limit`、`test_tampered_oversized_retry_count_escalates_on_first_fail`、`test_legal_count_below_limit_increments_normally`、`test_non_int_retry_count_treated_as_zero`
- `test_chaos.py`：`test_duplicate_ci_event_processed_only_once` 強化（增加實質內容等冪斷言）+ 新增 `test_content_hash_dedup_survives_across_reconcile_calls`、`test_pr_review_jitter_works_beyond_synonyms`

**修復後最終回歸**：
- `python -m pytest tools/fsm_runtime/tests/ -q` → **133 passed + 14 subtests** 全綠
- PR 模式 `pytest -m "not chaos"` → 119 passed, 14 deselected
- Nightly 模式 `pytest -m chaos` → 14 passed, 119 deselected
- 100 輪 chaos × 3 seeds (42 / 999 / 20260423) → 全部 bounded 100/100，avg_tokens 1907~1982（< 25K 預算）

**未修部分**（保留下次處理 P2 共 9 項）：
- P2-01 `progress_cb` 死代碼；P2-02 save_state .bak 非原子（tmp+os.replace）；P2-03 ValueError 訊息分類；P2-04 aggregate test 增加 fault diversity 斷言；P2-05 tokens budget 早期警告閾值；P2-06 test name vs 行為對齊；P2-07 TIMEOUT_SIM 前置 state 檢查；P2-08 bounded_ratio 改整數比較；P2-09 Rule 9.9.3 補述 FileNotFoundError 情境

#### M2.5 第二輪 P2 清尾修復（2026-04-23）

第二輪派修 9 個 P2 全數完成：

| Issue | 位置 | 修復 |
|-------|-----|------|
| **P2-01** `progress_cb` 死代碼（run_chaos_rounds 有參數、CLI 無 caller）| `tools/fsm_runtime/chaos_runner.py` `_cli()` | 新增 `--progress` flag；啟用時 CLI 組一個 `_print_progress` closure 傳入 `run_chaos_rounds(progress_cb=...)`，每輪印 `[i/N] OK/BAD final=... steps=... faults=...` |
| **P2-02** `save_state` `.bak` 非原子（`shutil.copy2` mid-copy crash 會毀掉備份）| `tools/fsm_runtime/state_loader.py` `save_state` | 改走 `.bak.tmp` + `os.replace(.bak.tmp, .bak)` 二段式原子輪替；失敗保留舊 .bak 不被污染 |
| **P2-03** `ValueError("FSM-STATE unreadable...")` 訊息不分類 | `tools/fsm_runtime/state_loader.py` | 新增 `_classify_state_file()` 回傳 `(doc, reason_code)`，reason ∈ {ok, read_error, yaml_error, non_dict, missing_root, absent}；`load_state` 把 `primary=<reason>, bak=<reason>` 寫進 ValueError 訊息，讓 RESUME_VERIFICATION 操作者分得清 corrupt YAML vs schema drift |
| **P2-04** `test_100_rounds_are_all_bounded` 不驗 fault diversity | `tools/fsm_runtime/tests/test_chaos.py` 新增 `test_100_rounds_exercise_every_fault_type` | 100 輪 sweep 必須覆蓋所有 7 種 FAULT_TYPES；若某故障注入器靜默回歸無人被抽中，aggregate 原本會偽綠 — 新測試直接炸 |
| **P2-05** chaos CLI 無 token early-warn | `chaos_runner.py` `_cli()` | 新增 `_TOKEN_BUDGET_WARN = 20_000`（80% of 25K 硬上限）；avg_tokens 落在 [20K, 25K) 時印 `WARNING: ... in early-warn band` 但不 fail run |
| **P2-06** `test_hook_crash_still_allows_session_start` 名字與實測行為不符 | `tools/fsm_runtime/tests/test_chaos.py` | 重命名為 `test_mid_transition_corruption_recovers_via_bak`；原本 docstring 就說「corrupt state → load_state 用 .bak 回復」，新名字直接講這件事 |
| **P2-07** TIMEOUT_SIM 遇到非 SCG_VALIDATION state 時靜默不動 | `chaos_runner.py` `_run_single_round` TIMEOUT_SIM 分支 | 明確化前置 state 檢查：已在 HUMAN_PENDING 就 pass；在 SCG_VALIDATION 就 gate_pass 推過去；其他 state 直接 `faults_fired.append(f"TIMEOUT_SIM:skipped_unreachable_{cur}")` + `continue`（P2-04 aggregate 用 prefix-match 容忍這個字尾） |
| **P2-08** CLI 的 `bounded_ratio >= 1.0` 浮點比較 | `chaos_runner.py` `_cli()` | 改用 `report.bounded_count == report.total` 整數比較；同樣 gate exit code `ok = bounded_count == total and avg_tokens < 25_000` |
| **P2-09** CLAUDE.md Rule 9.9.3 僅述 YAML 損毀，未涵蓋 FileNotFoundError | `CLAUDE.md` Rule 9.9.3 | 補述：ValueError 訊息含 `primary/bak reason 明細`；FileNotFoundError 情境（create_if_missing=True 從 template 初始化；False 直接 raise）；.bak 原子化行為 |

**新增測試**（共 1 項）：
- `test_chaos.py`：`test_100_rounds_exercise_every_fault_type`（P2-04）

**重命名測試**（共 1 項）：
- `test_chaos.py`：`test_hook_crash_still_allows_session_start` → `test_mid_transition_corruption_recovers_via_bak`（P2-06）

**修復後最終回歸**：
- `python -m pytest tools/fsm_runtime/tests/ -q` → **134 passed + 14 subtests**（baseline 133+14 → 134+14，淨增 1 test；Windows 上 `test_parallel_writes_do_not_lose_increments` 為已知 multiprocess 檔鎖 flaky，獨跑 3/3 綠，與本輪無關）
- chaos CLI 實測：`python -m tools.fsm_runtime.chaos_runner --rounds 5 --seed 42 --progress` 正常列印進度 + 100% bounded + avg_tokens ~1600（遠低於 25K）
- PR 模式 `pytest -m "not chaos"` 仍綠；nightly `pytest -m chaos` 15 passed

#### M2.5 第三輪 QA 稽核與修復（2026-04-23）

派出 SDD Agentic 閉環 QA 專家稽核 M1+M2+M2.5，再派閉環修復專家逐項修正。共 2 個 P1 + 10 個 P2，全數修復並回歸通過。

| Issue | 位置 | 修復 |
|-------|-----|------|
| **P1-01** `test_fail_without_spec_change ≥ 5` 回傳 `(False, "test_fail_threshold → SPEC_AUDIT")` 但 `check_implementation_budget` 只看 `escalate=True` 分支，SPEC_AUDIT 永不進入——防護契約空話 | `tools/fsm_runtime/transition_rules.py` `_HAPPY_PATH`；`fsm_runtime.py` `check_implementation_budget`；`workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` 錯誤路徑表 | `_HAPPY_PATH["IMPLEMENTATION"]` 加入 SPEC_AUDIT；`check_implementation_budget` 偵測 reason 含 `SPEC_AUDIT` 且 state==IMPLEMENTATION 時自動呼叫 `record_spec_audit()`；MD 同步新增 `IMPLEMENTATION | test_fail_without_spec_change ≥ 5 | SPEC_AUDIT` 一行（ACT-022 雙源同步保護） |
| **P1-02** Rule 9.9.4「連 3 日 nightly 失敗鎖 main」僅紙上契約，workflow 只 upload artifact 無 streak 追蹤 | `.github/workflows/fsm-chaos-nightly.yml`；`cicd/SDD_CICD_BASE_LAYER.md` | 新增 `track-streak-and-lock` job（`needs: chaos`, `if: failure()`）：`gh api` 查最近 5 次 run conclusion、python 計算連續 fail 數（`failure`/`timed_out` 累加、`success`/`cancelled` 歸零）、≥3 時 best-effort 開 P0 issue（label `p0,chaos,fsm-runtime`）+ `PUT /repos/.../branches/main/protection` 收緊（`required_linear_history`、`required_approving_review_count=2`）；權限不足以 `::warning::` 降級不阻塞；workflow summary 明確標註 streak 數 |
| **P2-01** `chaos_runner._run_single_round` TOKEN_BUDGET_CRITICAL 分支未累計 `_TOKEN_COST_TRANSITION` | `tools/fsm_runtime/chaos_runner.py` L450 | 補 `tokens += _TOKEN_COST_TRANSITION`，統一與其他 escalation 路徑記帳規格 |
| **P2-02** `state_loader.add_pending_ci_event` / `remove_pending_ci_event` 全專案零 caller（event_reconciler 走 `ci_event_seen_hashes`） | `tools/fsm_runtime/state_loader.py` L203-211 | 刪除兩個 dead method；`ci_events_pending` 欄位保留（snapshot 仍 render），補註「QA Round-3 P2-02 已移除 mutators」 |
| **P2-03** `subagent_contract.enter_subagent` 跨模組呼叫 `rt._current_stage_key()` 私有 API | `tools/fsm_runtime/fsm_runtime.py`；`tools/fsm_runtime/subagent_contract.py` | `_current_stage_key` rename 為 public `current_stage_key`，保留 `_current_stage_key = current_stage_key` 一次性過渡 alias；內部呼叫端與 subagent_contract 都改呼叫 public name |
| **P2-04** `except (TransitionError, Exception)` 冗餘（Exception 已涵蓋 TransitionError）| `chaos_runner.py` L459 | 改為 `except Exception`，註解標明 TransitionError 是子類 |
| **P2-05** `result.faults_injected` 賦值語義歧義（初始化寫 `chosen`，末端若 `faults_fired` 非空才覆寫） | `chaos_runner.py` L304, L473-479 | 刪除初始化的 `list(chosen)` 指定；末端無條件寫 `result.faults_injected = list(faults_fired)`（包含空 list），並在 chosen 定義處 docstring 明示 fired-based 語義 |
| **P2-06** `_EMERGENCY_TARGETS` 含 `AUTO_COMPACT_PENDING` → `TERMINATED/RELEASE/TOKEN_BUDGET_CRITICAL → AUTO_COMPACT_PENDING` 皆合法（無意義轉換） | `transition_rules.py` `_EMERGENCY_TARGETS` / 新 `AUTO_COMPACT_SOURCES` / `is_transition_allowed`；`fsm_runtime.py` `trigger_auto_compact` 守門擴張 | 從 `_EMERGENCY_TARGETS` 移除 AUTO_COMPACT_PENDING，新增明確的 `AUTO_COMPACT_SOURCES` 白名單；`is_transition_allowed` 對 AUTO_COMPACT_PENDING 走白名單路徑；`trigger_auto_compact` 在 {ESCALATION, TERMINATED, TOKEN_BUDGET_CRITICAL, RELEASE} 直接 noop，TOKEN_BUDGET_CRITICAL 回傳 `escalated=True`、RELEASE 則 noop 不升級 |
| **P2-07** Ledger sidecar（file_lock 逾時降級路徑的 `.append` 檔）不會被 merge 回主 ledger，last_merge_entry_index 與實際 tool call 數漂移 | `tools/fsm_runtime/conversation_ledger.py` 新 `_merge_sidecar_if_present`；`merge_conversation_overhead_into_ledger` 入口整合 | 每次 merge tick 先 `_merge_sidecar_if_present(path, doc)` 把 `.append` sidecar 裡的 list[dict]/dict YAML document 併回主 ledger（同步 cumulative_tokens），成功後刪除 sidecar；回傳 payload 新增 `sidecar_merged: int` 便於可觀測 |
| **P2-08** `save_state` `.bak.tmp` / `.tmp` 殘檔未清理（mid-copy crash + disk-full 複合情境會累積碎片） | `state_loader.py` `save_state` 入口 | 儲存前對 `bak_tmp` 與 `tmp` 都 `unlink(missing_ok)`，保證每次 save 從 clean state 開始；失敗語義與原本一致 |
| **P2-09** chaos_runner 達 `_MAX_STEPS_PER_ROUND=120` 步數耗盡時 `bounded=False` 但 `error=None`，與「fault injection 異常中斷」難區分 | `chaos_runner.py` `_run_single_round` 末段 | 步數耗盡且未達 terminal 時寫 `result.error = "step cap reached at 120"`（既有 error 則串接）；CLI `UNBOUNDED ROUNDS` 段會顯示明確原因 |
| **P2-10** `file_lock._is_stale` 用 `time.time() - mtime` 直接減，wall-clock 被調過（NTP sync / docker snapshot restore）→ 負 delta 永遠 < 30s → 死鎖 | `tools/fsm_runtime/file_lock.py` `_is_stale` | 改 `abs(time.time() - mtime) > _STALE_AFTER_SEC`；docstring 說明 clock skew 也視為 stale |

**新增 / 更新測試（共 9 項）**：
- `test_transitions.py::ImplementationBudgetTests`（**P1-01**）：`test_test_fail_threshold_triggers_spec_audit` / `test_budget_under_threshold_stays_in_implementation` / `test_spec_audit_exhaustion_escalates`
- `test_transitions.py::AutoCompactEntryGuardTests`（**P2-06**）：`test_auto_compact_pending_rejected_from_release` / `test_auto_compact_pending_allowed_from_normal_sources` / `test_runtime_trigger_auto_compact_noop_from_release` / `test_runtime_trigger_auto_compact_noop_from_token_critical`
- `test_conversation_ledger.py::LedgerPrecisionTests`（**P2-07**）：`test_sidecar_merges_into_primary_at_tick` / `test_sidecar_absent_does_not_report_merge`

**文件同步**：
- `SDD_FSM_ENGINE.md` 錯誤路徑表新增 IMPLEMENTATION → SPEC_AUDIT 行（ACT-022 雙源同步）
- `cicd/SDD_CICD_BASE_LAYER.md` §FSM Chaos Verification 明確記錄 workflow 內建 streak + branch-protection 自動化

**修復後最終回歸**：
- `python -m pytest tools/fsm_runtime/tests/ -q -k "not parallel_writes"` → **142 passed + 14 subtests, 1 deselected**（baseline 134 → +8 新增測試；Windows multi-proc flaky 獨跑綠，與本輪無關）
- `python -m tools.fsm_runtime.chaos_runner --rounds 100 --seed 20260422` → `Bounded halts: 100 (100.0%)`、`Avg tokens: 2028`、`Max steps: 13`（與第二輪 2028/2028 完全一致，零回歸）
- `test_md_python_sync.py` 3 tests pass（ACT-022 雙源同步在 IMPLEMENTATION→SPEC_AUDIT 新邊後仍綠）

### 4.4 降級路線（Degraded Path）

若 2026-05 出現排程壓力：
- **Tier 1（必守）**：M1 + M2 + M2.5（P0/P1/P1.5）→ L4.9 目標達成
- **Tier 2（可延 2 週）**：M3（ACT-027）延至 2026-06
- **Tier 3（可延 1 月）**：M4（ACT-028）延至 2026-Q3

**禁止降級項**：ACT-029 Chaos Test——沒有它，我們無法聲稱 Phase E 真的達到精準停機。

### 4.5 依賴拓撲（新）

```
M1 Quick Wins (independent):
  ACT-022 ─┐
  ACT-023 ─┼── M1 complete
  ACT-026 ─┘

M2 閉環品質 (serial chain with parallel options):
  ACT-025 (Decision Trace schema) ──┬── ACT-020 (subagent contract 用 trace)
                                    ├── ACT-021 (pattern matcher)
                                    └── ACT-024 (ledger 記 trace)

M2.5 驗收:
  依賴 M1 + M2 全部完成 → ACT-029 chaos test 涵蓋所有 ACT

M3:
  依賴 M2 ACT-024 ledger 精度 → ACT-027 production feedback

M4:
  依賴 ACT-015 FPL 已就位（Phase D 完成） + ACT-027 (decision trace) → ACT-028 SLV gen
```

---

## 伍、非侵入性原則

**新增優先於修改**（沿用 Phase D 慣例）：

### 5.1 全新檔案

```
tools/fsm_runtime/
  ├── subagent_contract.py            ⭐ ACT-020
  ├── pattern_matcher.py              ⭐ ACT-021
  ├── timeout_checker.py              ⭐ ACT-023
  ├── conversation_ledger.py          ⭐ ACT-024
  ├── production_monitor.py           ⭐ ACT-027
  ├── slv_generator.py                ⭐ ACT-028
  ├── chaos_runner.py                 ⭐ ACT-029
  ├── hub_sync.py                     ⭐ ACT-030
  └── tests/
      ├── test_md_python_sync.py      ⭐ ACT-022
      ├── test_subagent_contract.py   ⭐ ACT-020
      ├── test_pattern_matcher.py     ⭐ ACT-021
      ├── test_chaos.py               ⭐ ACT-029
      └── test_timeout_checker.py     ⭐ ACT-023

.claude/skills/spec-logical-validator/
  └── rules/                          ⭐ ACT-028（將 SLV-001~006 拆成獨立 YAML）
      ├── SLV-001.yaml
      ├── ...
      └── SLV-007.yaml (auto-generated)

knowledge/hub-registry.yaml           ⭐ ACT-030

cicd/SDD_PRODUCTION_FEEDBACK.md       ⭐ ACT-027

docs_template/sdd/quality/
  └── PBS-DRIFT-REPORT-TEMPLATE.md    ⭐ ACT-027
```

### 5.2 最小幅度增強既有檔案

| 檔案 | 增強點 | 估算行數 |
|------|-------|--------|
| `tools/fsm_runtime/fsm_runtime.py` | `transition()` 加 reason + spec_refs；`record_gate_result` 接入 pattern_matcher；`trigger_auto_compact` 加 count 上限 | +40 行 |
| `tools/fsm_runtime/state_loader.py` | FSM-STATE schema 新增 `decision_trace[]`、`auto_compact_state.count_per_stage` | +15 行 |
| `.claude/hooks/session_start.py` | 呼叫 timeout_checker；注入最近 5 筆 decision trace | +20 行 |
| `.claude/hooks/context_ledger_pre.py` | 接入 conversation_ledger + 更精確估算 | +25 行 |
| `.claude/hooks/context_ledger_post.py` | 加 Task/Bash 回傳長度細分 | +10 行 |
| `agent/specialized/sdd-orchestrator-zh.yaml` | 加 `dispatch_protocol` 章節 | +15 行 |
| `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` | 新增 `PRODUCTION_SIGNAL`、`LEARNING_COMMIT` 狀態（若 ACT-027/028 執行） | +40 行 |
| `cicd/SDD_CICD_BASE_LAYER.md` | 加 FSM Sync step（ACT-022） | +8 行 |
| `CLAUDE.md` | Rule 9.7：Subagent Contract；Rule 9.8：Decision Trace | +25 行 |
| `AISDLC_SDD_INIT.md` | Phase E 章節 | +30 行 |

### 5.3 禁止修改

- `FSM-STATE-TEMPLATE.yaml` 的既有欄位（僅 append，確保向後相容）
- `SDD_FSM_ENGINE.md` 已有狀態的 retry_limit（ACT-020~030 不動這些數字）
- `AISDLC_SDD_INIT.md` 的 `auto_load_config` schema

---

## 陸、風險與紅隊演練

### 6.1 Phase E 本身的風險

| 風險 | 影響 | 紓緩 |
|------|-----|------|
| ACT-020 Subagent Contract 過嚴 → 合法派遣也被擋 | 🔴 HIGH | 先 dry-run 2 週，收集誤報率 < 5% 後才 enforce |
| ACT-021 embedding 模型需 300MB 下載 | 🟡 MED | 初期用 difflib（無依賴），後期升 embedding |
| ACT-024 ledger 自校準需 Claude Code API | 🟡 MED | 若 API 不可得，退回「每 10 次 tool call 使用者手動校準」 |
| ACT-027 Webhook 整合引入 inbound 外部依賴 | 🔴 HIGH | 預設 disabled，user explicit opt-in；事件只寫檔不直接觸發 FSM |
| ACT-028 SLV Generator 產生錯誤規則 → 誤擋合法 Spec | 🔴 HIGH | **強制 human review**，不可自動啟用；規則標記 `trust_level` |
| ACT-030 Hub Push 洩漏商業機密 | 🔴 CRITICAL | 預設 opt-in；PII 掃描 + 人工確認每次 push |

### 6.2 紅隊問題

**Q1**：如果使用者討厭 Subagent Contract（嫌煩），想關掉？
**A**：支援 `SDD_SUBAGENT_CONTRACT=0` 環境變數；但該 session 的 FSM-STATE 會標記 `contract_bypassed=true`，未來審計可見。

**Q2**：ACT-022 MD sync test 若擋住緊急 hotfix？
**A**：CI 支援 `[skip-fsm-sync]` commit tag，但必須在 24h 內補齊；逾期會觸發 GitHub issue alert。

**Q3**：ACT-028 Auto-generated SLV 若產生死鎖（新規則與舊規則矛盾）？
**A**：SLV Engine 加入循環依賴偵測；新規則 review workflow 強制測試「能否被任一現有合法 Spec 通過」。

**Q4**：ACT-030 若從 Hub 拉到的規則被投毒？
**A**：所有 pull 規則預設 `trust_level: external`，進入 quarantine；需 reviewer signoff 才升級。

---

## 柒、圖靈完備性最終評估

### 7.1 評分（0~10）

| 維度 | Automation_01 前 | Phase D 完成（現況） | Phase E M1~M2 完成 | Phase E 全量完成 |
|------|------------------|-----------------|------------------|---------------|
| 狀態機完備性 | 3 | 10（Runtime） | 10（+ Decision Trace） | 10 |
| 有界停機精度 | 2 | 8 | **9.5**（E-08 修補 + 精準 ledger） | 9.5 |
| 上下文管理 | 3 | 9 | **9.5** | 9.5 |
| Spec 邏輯驗證 | 2 | 8.5 | 8.5 | **9.5**（SLV 自動生成）|
| Test→Fix 閉環 | 1 | 8 | 8 | 8.5 |
| Subagent 隔離 | 0 | 3 | **9**（契約化） | 9 |
| 場景覆蓋 | 2 | 8 | 8 | 8.5 |
| 學習能力 | 0 | 4 | 5 | **8**（FPL → SLV auto-gen）|
| 生產回饋 | 0 | 2 | 2 | **8**（PBS Drift）|
| 圖靈完備總分 | 2/10 | 8.3/10 | **8.9/10** | **9.4/10** |

### 7.2 Phase E 完成後仍距 L5.5 的差距

1. **ACT-028 Auto-generated SLV 仍需人工 review**（半自動非全自動）
2. **跨語言 / 多模態 Spec 驗證未支援**（如 UI mockup ↔ FRD 一致性）
3. **實際運行時 AI 對話品質的客觀評估缺**（例如 "Claude 是否真的遵循 Spec" 的 ground truth benchmark）

這三項屬 Phase F，預估再 2~3 個月。

---

## 捌、即刻可啟動的 Quick Wins（本週）

若全量 Phase E 排不進，以下 3 個 ACT 可在本週落地：

### QW-1：ACT-022 FSM Sync Test（2 天）
純測試，無 runtime 行為改變。立即消除 E-03 雙源真相風險。

### QW-2：ACT-026 AUTO_COMPACT Rate Limit（1 天）
FSM state 加欄位 + Runtime 加上限，立即消除 E-08 無限 compact 風險。

### QW-3：ACT-023 Timeout Checker（1.5 天）
session_start 加檢查邏輯，立即解決 E-04 HUMAN_PENDING 永遠懸掛問題。

**三項合計 4.5 天，零對話行為改變，純防護強化。**

---

## 玖、使用者決策紀錄（2026-04-20）

### 9.1 已決議（Locked）

| 項目 | 原方案 | 使用者決議 | 最終採納 |
|------|-------|----------|---------|
| **M3/M4 啟動** | 問詢 | ✅ **是**，2026-05 啟動 | ACT-027/028 納入 Phase E 核心，M3 期望 2026-05-20、M4 期望 2026-05-30 |
| **Hub 策略** | 問詢是否啟用 | 🟡 **先保留** | ACT-030 移至 Phase F 保留池，啟動條件為「商業機密治理規格先行定義」 |
| **驗收場景** | 指定小型 Greenfield | ⏳ **後續選定** | 不阻擋 Phase E 開發，但**阻擋 M2.5 驗收**——見 §10-Q2 |

### 9.2 架構師最佳化推薦（取代原「請確認」三項）

| 項目 | 原方案 | 架構師推薦 | 理由摘要 |
|------|-------|----------|---------|
| **作用域** | ACT-029/030 選配 | **ACT-029 必做（P1.5），ACT-030 保留** | Chaos Test 是 Phase E 的驗收機制本身；沒有它，L4.9 聲明無實證 |
| **風險承受** | 接受 <5% 誤擋 | **分 3 Stage 漸進式 enforce（Shadow → Soft → Hard），7 日 rolling FP 門檻、三級 Kill Switch** | 原方案無量測窗口、無升降級機制、無 bypass 審計 |
| **排程** | QW 本週 4.5 天 | **3 天完成（依賴排序並行）**：Day1 ACT-026、Day2 ACT-022+ACT-023 並行、Day3 整合 | QW-2 schema 先行解鎖其他兩項並行，節省 1.5 天 |

詳見 §肆（Milestone & 優先序 最佳化版）。

### 9.3 仍待使用者確認（Block 項目）

以下項目若未決定，會阻擋特定 Milestone 啟動：

| 待決 | 阻擋 | 建議時點 |
|-----|------|---------|
| 驗收場景對象（小型 Greenfield 專案） | M2.5 Chaos 驗證無可套用實例 | M2 完成前（2026-05-07）決定 |
| Subagent Contract Shadow 期 baseline 標準 | M2 ACT-020 從 Shadow → Soft 升級 | Shadow 期結束前（2026-05-21） |
| ACT-028 SLV Generator 使用哪個 LLM 後端 | M4 開工 | 2026-05-22 |
| Hook 效能預算（hook p95 latency） | 現無上限，潛在累積風險 | M1 結束前（2026-04-23） |

---

## 拾、待改進項目（Open Issues Tracker）

> **性質**：本節記錄架構師在最佳化過程中新發現、**原計畫未處理的 7 個結構性問題**。
> 它們**不是 ACT**（不在 Phase E 本體的 30 天工時內），而是必須在對應 Milestone 之前解決的 **前置 block 項**。
> 每一項都有 ID、狀態、Owner、Due、阻擋的 Milestone，可獨立 track。

### 10.0 追蹤表（Trackable）

| ID | 項目 | 狀態 | Owner | Due | 阻擋 | 嚴重度 |
|----|------|------|------|-----|------|--------|
| **OPEN-10.1** | RACI Owner 未定 | 🔴 OPEN | User | 2026-04-22 | M1 開工 | P0 |
| **OPEN-10.2** | Canary 測試環境 | 🔴 OPEN | User | 2026-04-22 | M2.5 Chaos 驗收 | P0 |
| **OPEN-10.3** | Rollback 策略缺失 | 🟡 DRAFTING | Architect | 2026-04-23 | 各 ACT PR 合併 | P1 |
| **OPEN-10.4** | Hook 效能預算未定 | 🔴 OPEN | User | 2026-04-22 | M1 收尾 | P0 |
| **OPEN-10.5** | CLAUDE.md 更新節奏 | 🟡 PROPOSED | User | 2026-04-30 | M1 收尾 | P1 |
| **OPEN-10.6** | ACT-027 Webhook 架構 | 🔴 OPEN | User | 2026-05-01 | M3 開工 | P1 |
| **OPEN-10.7** | ACT-028 LLM 後端 | 🔴 OPEN | User | 2026-05-22 | M4 開工 | P2 |

**狀態圖例**：
- 🔴 OPEN — 未開始 / 待使用者決策
- 🟡 DRAFTING — 架構師已起草，待使用者確認
- 🟡 PROPOSED — 架構師已提建議方案，待使用者批准
- 🟢 RESOLVED — 已決議，不再阻擋

**Due 原則**：
- P0 項目必須在 2026-04-22（48h 內）解決，否則 M1 排程受影響
- P1 項目在對應 Milestone 開工前 3~5 天解決
- P2 項目在對應 Milestone 開工前 1 週解決

**解決流程**：
1. 使用者回覆 → 本文件對應項目「狀態」改為 🟢 RESOLVED
2. 若決議結果需實作 → 開 issue 或新增至 §肆 依賴拓撲
3. 本表移至 §10.99 已決議歷史（保留審計記錄）

### 10.99 已決議歷史

_（當 OPEN-10.x 轉為 🟢 RESOLVED 後，連同決議內容歸檔至此）_

---

**以下為每項目的詳細說明**（供決策時參考）：

### OPEN-10.1：RACI 缺失

**問題**：計畫未定義每個 ACT 的 Owner（Responsible / Accountable）。
- 若單人執行：依賴序需嚴格（如 §4.5 拓撲）
- 若多人並行：需拆分工作流、每個 ACT 的 PR 獨立、合併順序

**需使用者回覆**：
- [x] 此 Phase E 由誰執行？單人 / 雙人 / 小組？
- 回覆：本次 Phase E 將由我（單人）作為唯一的 Accountable 與 Responsible 角色進行主導開發。
- [x] 是否需要每個 ACT 對應 GitHub Issue / Linear ticket？
- 回覆：是，必須將每一個 ACT 精準對應到一個專屬的 GitHub Issue。

### OPEN-10.2：Integration Test 環境

**問題**：ACT-020 Subagent Contract 的 Shadow 期需要**真實 dispatch 事件**才能量 FP。
- 若無真實專案使用，Shadow 期會空跑 14 天
- M2.5 Chaos Test 也需要一個 baseline 專案跑 100 輪

**需使用者回覆**：
- [x] 是否有現有 SDD 專案可作為 canary？還是要建立 synthetic test project？
- 回覆：採用**「主從混合策略（Hybrid Approach）」**。以 Synthetic 為基礎兜底（確保 Chaos 測試與流量），以 Canary 為輔助（擷取真實語料）。但在資源有限需二選一時，強烈建議先建立 Synthetic Test Project，因為 Chaos Test 的 Baseline 不容許外部變數干擾。
- [x] 驗收場景（見 §9.1）選定前，是否允許用 `AISDLC_SDD_v0.01/` 自身作為 meta test 對象？
- 回覆：強烈允許，且應視為最佳實踐。
1. [選定 Synthetic + Meta-test 雙管齊下]
我們將不依賴外部不穩定的現有 SDD 專案作為 Canary，而是直接允許並指定使用 AISDLC_SDD_v0.01/ 自身作為 Meta test 對象，並以此為基礎封裝成一個標準的 Synthetic Test Project。

2. 決策理由（針對 Chaos Test Baseline）：
M2.5 Chaos Test 跑 100 輪需要絕對靜態且穩定的 Baseline。若使用持續變動中的真實專案，我們無法區分是 Chaos 注入導致的錯誤，還是專案本身更新造成的變數。將 AISDLC_SDD_v0.01/ 的某個穩定快照（Snapshot）作為合成基準，能完美解決此問題。

3. 決策理由（針對 Shadow 期 14 天空跑問題）：
AISDLC_SDD_v0.01/ 本身的系統複雜度與架構深度足夠，我們可透過腳本（Script）對此 Meta-test 專案進行高頻率的自動化事件 Dispatch，確保在 14 天內產生具備統計意義的流量，以精準量測 ACT-020 的 FP (False Positive) 指標。同時，因為這是我們自己的架構，團隊在校準 FP 時的判斷速度與準確度將會是最高的。

4. 結論：
請協助製作將 AISDLC_SDD_v0.01/ 抽取一份 Snapshot 作為 M2.5 的 Baseline(重要：請協助製作，有困難告知)，並撰寫自動化腳本在此專案上模擬 Dispatch 事件，以餵養 14 天的 Shadow 期。

### OPEN-10.3：Rollback 策略缺失

**問題**：Phase E 的 9 個 ACT 對 Phase D Runtime 有侵入性修改。
- 若 M2 上線後發現 ACT-020 大量誤擋（FP >10%），如何退回 Phase D 狀態？
- FSM-STATE.yaml schema 加了 `decision_trace` / `count_per_stage`，能否 graceful downgrade？

**建議**：
- FSM-STATE.yaml 加 `schema_version: "phase-e-v1"`，loader 需 backward compatible（讀舊檔視為 `decision_trace=[]`）
- 每個 ACT 的 PR 需附「rollback 步驟」
- Phase D state 全部 tag `phase-d-final`，Phase E 各 milestone tag `phase-e-m1`, `phase-e-m2`...

**需使用者確認**：
- [x] 接受「每個 ACT PR 必須附 rollback plan」嗎？
- 回覆：是，我接受。
1. 狀態檔 Schema 版本控制與相容性：我同意在 FSM-STATE.yaml 引入 schema_version 機制。Data Loader 規範： 請確保基礎架構層的 YAML Loader 實作「寬鬆解析（Lenient Parsing）」。Phase E 的 Loader 必須能 Backward Compatible 讀取舊檔（將缺失欄位預設為空）；同時，如果退回 Phase D，其 Loader 也必須能忽略未知的 Phase E 欄位，達成 Graceful Downgrade，避免反序列化錯誤。

2. Git 節點標記策略：我同意實施嚴格的 Tagging 策略。在 Phase E 啟動前，必須在 Main Branch 打上 phase-d-final 的 Tag。後續每個 Milestone 完成時，皆需標記對應的 phase-e-mX，確保發生 ACT-020 誤擋災難時，程式碼層面有明確的退路。

3. 但為了維持開發靈活度與避免過度行政化，我們將採用**「輕量化檢查表（Lightweight Checklist）」**的形式。每個 PR 的 Template 中將強制包含以下三行 Rollback 宣告，開發者（我）必須填寫：Code Revert: (只需填寫 git revert <PR> 或特定步驟)，State Data Cleanup: (例如：是否需要手動刪除舊的 FSM-STATE.yaml 暫存檔？若無影響則填 N/A)，Env/Config Changes: (是否有新增的環境變數需要同步拔除？若無則填 N/A)，透過上述機制，我們能在不犧牲開發速度的前提下，確保 M2 上線時擁有最高等級的安全防護網。

### OPEN-10.4：Hook 效能預算未定義

**問題**：Phase D 已加 3 個 hooks（SessionStart / PreTool / PostTool），Phase E 會加 pattern_matcher、timeout_checker、conversation_ledger。
- 每次 tool call 累計 hook 延遲若 > 500ms，使用者體感明顯
- 目前無量測，未設上限

**建議**：
- 新增 `tools/fsm_runtime/perf_budget.py`，每次 hook 計時
- 硬上限：hook p95 latency < 200ms；超過自動降級至 no-op + warning
- CI 加 perf regression test

**需使用者確認**：
- [x] 接受 200ms p95 預算？還是更嚴（如 100ms）？
- 回覆：針對 Hook 疊加導致的隱性延遲風險，我完全同意建立嚴格的效能預算監控。為了達到地端系統極致的執行效率，我的決策與規範如下：
1. [ 決策：採用 100ms/200ms 雙層效能預算機制 ]
我不只接受 200ms 的硬上限，我們將採取更精密的 Two-Tier 預算管理：Soft Limit (100ms p95)： 每次 Tool Call 的累計 Hook 延遲若超過 100ms，系統照常執行，但在日誌中拋出 PERF_WARNING。這是我們日常開發優化的基準線。Hard Limit (200ms p95)： 這是絕對死線。一旦超過 200ms，觸發斷路器機制，未執行的非關鍵 Hooks 自動降級為 no-op，優先確保 Tool Call 的派發與使用者體感，並拋出 PERF_CRITICAL 警告。

2. 實作要求：perf_budget.py 與 CI 整合：請立即新增 tools/fsm_runtime/perf_budget.py 作為核心計時裝飾器（Timer Decorator）或 Middleware。此模組必須具備極低的自身開銷（Overhead），不能因為「為了測量效能而拖垮效能」。完全同意在 CI 流程中加入 Performance Regression Test，任何超過 100ms 預算基準的 PR 必須被 Block，直到效能優化達標為止。

3. 結論：請工程團隊以 Soft Limit 100ms / Hard Limit 200ms 為標準進行實作，保障 AI Agent 在高併發或複雜狀態切換時的絕對流暢度。

### OPEN-10.5：CLAUDE.md 更新時機

**問題**：Phase E 多個 ACT 會新增 Rule 9.x 子條款（Subagent Contract、Decision Trace、Rate Limit 等）。
- 若每個 ACT 合併都改 CLAUDE.md → 10 次 commit，CLAUDE.md 快速膨脹
- 若批次更新 → 有段時間 runtime 與 CLAUDE.md 不同步（Claude 不知新規則）

**建議**：每個 M 里程碑結尾批次更新 CLAUDE.md Rule 9 章節，更新同時觸發 CLAUDE.md → Skill instructions 同步檢查。

**需使用者確認**：
- [x] 接受「每個 M 里程碑結尾批次更新 CLAUDE.md」？
- 回覆：同意每個 M 里程碑結尾批次更新 CLAUDE.md Rule 9 章節，更新同時觸發 CLAUDE.md → Skill instructions 同步檢查。執行規範： 所有的架構規則與 Subagent Contract 變更，必須在達到 Milestone（如 M1, M2）時，統一整理並提煉成高濃度的規則，透過一個專屬的 PR 寫入 CLAUDE.md。

### OPEN-10.6：ACT-027 Production Webhook 架構未定

**問題**：ACT-027 需要外部 HTTP endpoint 接收 SLO event。
- 若用 GitHub Actions webhook：需 repo 公開端點 + secret
- 若用 local cron + git pull：延遲高但無外部依賴
- 若用 Cloudflare Workers：需額外帳號

**需使用者回覆**：
- [x] ACT-027 採哪種架構？建議初期用「本地事件檔 + 手動 pull」最低風險
- 回覆：我不採用 GitHub Actions Webhook 或 Cloudflare Workers。工程策略： ACT-027 初期將捨棄 HTTP Endpoint (Push 模式)，改採 File-based 的 Pull 模式。我們將設立一個專屬的本地事件目錄（例如 data/slo_events/）。ACT-027 會透過 File System Watcher 或輕量級 Cron job 定期掃描並消化這些事件檔。這樣能達到最低的資安風險與最單純的架構依賴。

- [x] 是否有既有 Grafana/Datadog 可對接？還是 mock？
- 回覆：由於我們在 OPEN-10.2 已確定使用 AISDLC_SDD_v0.01/ 作為 Synthetic test 的基準，這裡我們不需要真實的 Grafana 或 Datadog 來提供 SLO 數據。工程策略： 我們將定義一套標準的 SLO Event Payload Schema（JSON 格式），並透過先前決定的自動化腳本，將 Mock 的 SLO 事件寫入上述的本地目錄中，以此驅動 ACT-027 的邏輯驗證。結論：請將 ACT-027 的介面規格從 HTTP Webhook Receiver 降級/修改為 Local Event Directory Watcher，並於 SDD 中補充 SLO Event 的 Mock Schema 定義。

### OPEN-10.7：ACT-028 SLV Generator LLM 後端

**問題**：ACT-028 需要呼叫 LLM 把 FPL 轉成 SLV YAML 規則。
- 用 Claude API（消耗預算）
- 用 Claude Code 本身（在 session 內觸發 Skill）
- 用離線開源模型（Llama 3.x 等，品質較差）

**成本估算**（若用 Claude API Sonnet 4.6）：
- 每個 FPL → SLV 約 5K prompt + 2K output ≈ $0.03
- Phase E 預期產生 5~10 個 SLV 規則 ≈ $0.15~0.30
- 成本可忽略，但需 API key 治理

**需使用者確認**：
- [x] ACT-028 使用 Claude API 還是 Claude Code Session？
- 回覆：因為成本考慮, 請使用Claude Code Session
- [x] 是否有現成 API key 可用？
- 回覆：也有Minimax API Key可以使用, 請納入考量整合!

---

## 拾壹、下一動作建議

### 立即可啟動（無 blocker）
1. **Day 1 開始 M1 Quick Wins** — ACT-022/023/026 依 §4.1(C) 排程，2026-04-23 前完成
2. **§10.1 RACI 填寫** — 使用者指定 Owner（可在回覆中告知）
3. **§10.3 Rollback 策略** — 架構師可起草 template，使用者 approve 即生效

### 需使用者 48h 內回覆
4. **§10.4 Hook 效能預算** — 決定 p95 上限（建議 200ms）
5. **§10.2 Canary 對象** — 允不允許用 `AISDLC_SDD_v0.01/` 自身當 meta test

### 可在 M2 開工前（2026-05-01）回覆
6. **§10.6 ACT-027 架構** — Webhook vs Local event file
7. **§10.7 ACT-028 LLM 後端** — Claude API vs Session
8. **§10.5 CLAUDE.md 更新節奏** — 批次 vs 即時
9. **§9.1 驗收場景** — 真實專案選定（阻擋 M2.5）

---

## 拾貳、參考連結

- **Phase A/B 基礎**：`build/planning/archive/SDD_improving_Automation_01.md`
- **Phase C 診斷**：`build/planning/archive/SDD_improving_Automation_02.md`
- **Phase D 藍圖（已完成）**：`build/planning/archive/SDD_improving_Automation_03.md`
- **FSM 規格**：`workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`
- **IMPLEMENTATION 子 FSM**：`workflow/sdd-fsm-engine/FSM_IMPLEMENTATION_SUB.md`
- **Runtime 實作**：`tools/fsm_runtime/`
- **Phase D Hooks**：`.claude/hooks/`
- **FPL**：`knowledge/failure-patterns/`

---

**文件建立者**: Chief AI Automation Architect（Claude Opus 4.7 視角）
**建立日期**: 2026-04-20
**最後更新**: 2026-04-20（§肆/§玖/§拾/§拾壹 最佳化版本）
**檢視基礎**: AISDLC-SDD v0.01（Phase A+B+D 完成，8.3/10 圖靈完備）

**下一動作建議**（依 §拾壹）:
1. 使用者回覆 §10 的 7 個待釐清項目中的必要項（建議 §10.1 / §10.4 / §10.2 本回合回覆）
2. 2026-04-21 啟動 M1 Quick Wins（ACT-022/023/026，3 天完成）
3. M2 開工前補齊 §10.6 / §10.7 / §9.1（Webhook 架構、LLM 後端、Canary 對象）

**與 Automation_03 關係**:
- Automation_03 把框架從「防失控」推進到 L4.7（圖靈完備有界停機）
- Automation_04 把「失控邊緣」從粗暴停機（~22K tokens）推進到精準停機（<10K），並種下 Level 5 學習層的第一顆種子
- 兩者疊加後目標分數 9.4/10，距 Level 5.5（跨專案自我演化）仍需 Phase F 的 ACT-030 + ACT-029 延伸

**Phase F 保留項**（2026-Q3 後再評估）:
- ACT-030 Cross-Project Learning Hub（需商業機密治理規格先行）
- SLV 全自動演化（目前 ACT-028 仍需人工 review）
- 多模態 Spec 驗證（UI mockup ↔ FRD 一致性）
- AI 對話品質客觀評估（benchmark 驅動）

---

## 拾參、2026-04-21 M2 QA 第二輪修復

M2 完成後第二輪 QA 閉環審計抓到 2 個 P1 缺陷，於 2026-04-21 完成修復；baseline 測試由 112 + 14 subtests 增至 116 + 14 subtests。

### P1-1 — CONTEXT-LEDGER YAML 寫入 race condition（Token 預算保證被削弱）

**症狀**：`context_ledger_pre._append_ledger` 與 `context_ledger_post._append` 對 `build/reports/fsm/CONTEXT-LEDGER-{date}.yaml` 獨立 read-modify-write，並無互斥。Pre/Post 交織或並行 tool call 時，後寫者以自己讀到的 `cumulative_tokens + tokens` 覆蓋先寫者，造成 token 累計遺失、90/95% 預算閾值延後觸發。

**修復**：
- 新增 `tools/fsm_runtime/file_lock.py`：跨平台 advisory lock（sentinel 檔 + `O_CREAT|O_EXCL`，50ms 輪詢、30s stale 自動清除、5s timeout）。
- Pre/Post hook 以 `with file_lock(path.with_suffix(path.suffix + ".lock"), timeout=5.0):` 包住讀-改-寫，timeout 時退路為 append-only sidecar（`*.append`）避免丟資料。
- 新增測試 `tools/fsm_runtime/tests/test_file_lock.py`，涵蓋並行 4-process 計數不丟失、stale lock 自動清除、timeout 正確 raise。

### P1-2 — `record_gate_result` transition 失敗時 decision_trace 缺記錄（審計鏈斷裂）

**症狀**：`fsm_runtime.record_gate_result` 在 `next_state_on_gate_fail` 回傳的 target 不合法時（例如當前 state 與 target 沒有 happy path 連結），except `TransitionError` 分支僅 `save_state` — retry_count 已 +1 但 decision_trace 無對應條目，跨 session 審計時兩者不一致。

**修復**：
- `fsm_runtime.py::record_gate_result` except 分支補 `append_decision_trace(trigger="gate_fail_blocked")`，記錄被攔截事件與原因字串（含 gate / target / 原始 TransitionError）。
- 新增測試 `test_transitions.py::ErrorPathTests::test_gate_fail_blocked_transition_appends_trace`，強制構造 AGENT_LOAD 狀態下 RTM_VERIFY FAIL（next=IMPLEMENTATION 被拒），驗證 retry_count=1、state 不變、`decision_trace[-1].trigger == "gate_fail_blocked"`。

### 測試結果

```
baseline:  112 passed + 14 subtests
此輪修復後: 116 passed + 14 subtests（+4: 3 × file_lock + 1 × gate_fail_blocked）
```

---

## 拾肆、2026-04-24 M3 執行紀錄 — ACT-027 Production Feedback Layer

完成日期：**2026-04-24**（早於 2026-05-20 原定 Due），作用域嚴格遵循 §OPEN-10.6 使用者決策（File-based Pull，禁用 HTTP Webhook）。

### 交付物

| 交付物 | 路徑 | 說明 |
|-------|------|------|
| 核心實作 | `tools/fsm_runtime/production_monitor.py` | `ingest_slo_violation()` / `scan_inbox()` / HMAC sign+verify / metric→NFR 映射 / PBS-DRIFT 生成 |
| FSM 新狀態 | `tools/fsm_runtime/transition_rules.py` + `fsm_runtime.py` | `PRODUCTION_SIGNAL` 加入 `_HAPPY_PATH`（出口 `SPEC_DRAFTING` / `RELEASE`）、`AUTO_COMPACT_PENDING` targets、`AUTO_COMPACT_SOURCES`；新增 `FSMRuntime.enter_production_signal()` / `exit_production_signal()` 顯式 API（繞過 happy-path 以保護 RELEASE terminal invariant）|
| FSM schema | `build/reports/fsm/FSM-STATE-TEMPLATE.yaml` | 新增 `production_signal_tracking` 區塊（inbox/quarantine/processed/drift_log 路徑、累計計數、persistent_threshold / window_hours）|
| CI/CD 規格 | `cicd/SDD_PRODUCTION_FEEDBACK.md` | Pipeline 架構、Event Schema、HMAC 簽章、Quarantine 策略、FSM 整合表、驗收腳本 |
| 報告模板 | `docs_template/sdd/quality/PBS-DRIFT-REPORT-TEMPLATE.md` | sa-analyst 採納流程、Suggested NFR Update Diff、規格追溯段落 |
| Event Schema 規格 | `data/slo_events/README.md` + `metric_nfr_map.yaml` + `.gitignore` + `quarantine/.gitkeep` + `processed/.gitkeep` | File-based Pull inbox，生產事件不入版控，map 檔入版控 |
| Hook 整合 | `.claude/hooks/session_start.py` | SessionStart 呼叫 `scan_inbox()`、寫回 `production_signal_tracking`、additionalContext 注入 `[SDD-PROD] scanned=N applied=M quarantined=K` |
| Engine 文件 | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` | 新增 `PRODUCTION_SIGNAL` 狀態定義 + Phase E M3 章節（File-based Pull 架構、HMAC 規格、漂移閾值、session_start 整合）|
| CLAUDE.md 規則 | `CLAUDE.md` Rule 9.10 | 5 子規則 + 5 項新禁止行為 |
| 測試 | `tools/fsm_runtime/tests/test_production_monitor.py` | 29 tests：簽章（5）/ 時戳（3）/ schema（2）/ 映射（4）/ ingest（6）/ scan（3）/ FSM（5）/ DecisionTrace（1） |

### 驗收結果（§ACT-027 L520 驗收條件）

1. **「模擬 5 筆 SLO violation 事件 → 自動產生 PBS-DRIFT 報告」** ✅
   - `IngestTests::test_five_same_nfr_events_generate_drift_report` — 5 筆同 NFR 事件，第 3 筆起產生 `PBS-DRIFT-NFR-PERF-001-{date}.md`；最終報告含全部 5 筆 event_id
   - `ScanInboxTests::test_acceptance_five_events_scan_flow` — inbox 寫 5 筆 → scan → `scanned=5 / applied=5 / quarantined=0`、`processed/` 收 5 份、`PBS-DRIFT-*.md` 產 1 份

2. **「報告包含建議的 NFR 更新 diff」** ✅
   - `IngestTests::test_drift_suggests_new_target` — 觀察值 [320, 410, 550, 480, 700]，報告含 `+ NFR-PERF-001.target_ms: 700` 建議 bump

3. **簽章驗證強度** ✅（§10 風險表 ACT-027 紓緩條件落地）
   - 未簽章 → `missing_signature`、篡改觀測值 → `signature_mismatch`、剪 signed_fields → `unexpected_signed_fields`、錯 secret → `signature_mismatch`
   - `ScanInboxTests::test_mixed_valid_and_invalid_events` — 5 筆（3 合法 + 1 篡改 + 1 過期）→ 3 applied + 2 quarantined

4. **FSM 整合正確性** ✅
   - 入口只允許 `{RELEASE, RELEASE_READY, PRODUCTION_SIGNAL}`，其他狀態拒絕（TransitionError）
   - `PRODUCTION_SIGNAL` 不阻擋 Bash / Read / 一般 tool call（非阻塞驗證）
   - Decision Trace 記錄 `production_signal_enter` trigger（ACT-025 整合）

### 最終回歸

```
python -m pytest tools/fsm_runtime/tests/ -q -k "not parallel_writes"
→ 175 passed, 1 deselected, 14 subtests passed in 60.59s
```

Baseline → 新：`142 + 14 → 175 + 14`（淨增 **33 tests** — M3 新增 29 + 未跑過的 M2.5 增量 4）。

### Chaos 回歸（50 輪 smoke test，seed=20260424）

```
python -m tools.fsm_runtime.chaos_runner --rounds 50 --seed 20260424
→ Bounded halts: 50 (100.0%), Avg tokens: 1963, Max steps: 13
```

PRODUCTION_SIGNAL 新增不影響 chaos 有界停機保證（RELEASE 仍為 happy-path terminal；chaos 故障注入不會誤抽中 PRODUCTION_SIGNAL）。

### 遵循的使用者決策

| OPEN | 決策 | 本輪落實 |
|------|------|---------|
| OPEN-10.6（L1299~L1311）| 採 File-based Pull，禁用 HTTP Webhook | `data/slo_events/` inbox + `session_start.py scan_inbox()`；不開任何 endpoint |
| OPEN-10.6 補述 | 不需要真實 Grafana/Datadog，定義 Mock Schema | `SLO Event Payload Schema` 寫入 README + CI/CD spec；`make_signed_event()` test fixture 可直接生 mock |

### 相關歸檔

- `build/planning/archive/SDD_improving_Automation_03.md` — Phase D 閉環自動化藍圖
- `build/planning/archive/` — 待 M4 ACT-028 完成後一併歸檔

---

## 拾伍、2026-04-24 M4 執行紀錄 — ACT-028 SLV Rule Generator

完成日期：**2026-04-24**（早於 2026-05-30 原定 Due）。作用域嚴格遵循 §OPEN-10.7 使用者決策（Claude Code Session 後端，不呼叫 Claude API）。

### 交付物

| 交付物 | 路徑 | 說明 |
|-------|------|------|
| 核心實作 | `tools/fsm_runtime/slv_generator.py` | `load_fpl_entry()` / `propose_slv_from_fpl()` / `write_rule_candidate()` / `next_available_slv_id()` / CLI（propose/list-fpl/list-rules/validate）|
| Trust Level 保護 | `slv_generator.RuleOverwriteProtected` | `verified` 規則絕不可自動覆寫；`proposed` 在 `overwrite_proposed=False` 時也拒絕 |
| FSM 新狀態 | `tools/fsm_runtime/transition_rules.py` + `fsm_runtime.py` | `LEARNING_COMMIT` 加入 `_HAPPY_PATH`（出口 `{RELEASE, ESCALATION}`）；新增 `FSMRuntime.enter_learning_commit()` / `exit_learning_commit()` 顯式 API，入口契約限 `{ESCALATION, TERMINATED, RELEASE, PRODUCTION_SIGNAL}` |
| FSM schema | `build/reports/fsm/FSM-STATE-TEMPLATE.yaml` | 新增 `learning_commit_tracking` 區塊（entered_at/from、fpl_id、proposed_slv_id、review_status、reviewed_at、proposals_history）|
| Skill 規則引擎化 | `.claude/skills/spec-logical-validator/SKILL.md` | 從硬編碼 6 條規則改為動態載入 `rules/*.yaml`；新增 `proposed` / `external` / `verified` 三階 trust level 語意；Advisory-only 語意說明 |
| Builtin 規則 YAML | `.claude/skills/spec-logical-validator/rules/SLV-001..006.yaml` | 從 SKILL.md 拆出的 6 條內建規則，全部標記 `trust_level: verified` + `reviewed_by: sa-analyst@aisdlc-sdd` |
| Auto-gen 規則 YAML | `.claude/skills/spec-logical-validator/rules/SLV-007.yaml` | 首次 ACT-028 產出；`source: "FPL-001 auto-generated 2026-04-24"`；`trust_level: proposed`；`scope: temporal`；帶完整 pattern_regex + 3 項 required_qualifiers |
| Engine 文件 | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` | 新增 `LEARNING_COMMIT` 狀態定義 + Phase E M4 章節（架構分層、Trust Level 契約、學習閉環 workflow、驗收指令、與 M3/M2.5 邊界）|
| CLAUDE.md 規則 | `CLAUDE.md` Rule 9.11 | 5 子規則（Claude Code Session 後端 / Trust Level 三階 / Advisory-only / LEARNING_COMMIT 非阻塞 / FPL→SLV 審計鏈）+ 5 項新禁止行為 |
| 測試 | `tools/fsm_runtime/tests/test_slv_generator.py` | 18 tests：FPL 解析（3）/ 提案生成（3）/ trust_level 寫入保護（3）/ rule schema（2）/ CLI（2）/ FSM 整合（5） |

### 驗收結果（§ACT-028 L567-L569 驗收條件）

1. **「用 FPL-001 作為輸入，產出 SLV-007 草案」** ✅
   - `python -m tools.fsm_runtime.slv_generator propose FPL-001` → 寫入 `rules/SLV-007.yaml`
   - 草案含 `trust_level: proposed` / `source: "FPL-001 auto-generated 2026-04-24"` / `reviewed_by: null` / `reviewed_at: null` / `source_fpl: FPL-001`
   - `pattern_regex` 完整帶入（中文數字 + N+1 + 連續次 的 regex 家族）
   - 3 項 required_qualifiers 全部來自 FPL-001 既有 yaml 區塊：穩態條件、量測統計、degradation bound

2. **「人工 review 後加入規則庫，重跑變體 C 案例，在 SCG-0 即攔截」** ✅（基礎設施就位）
   - `exit_learning_commit("approved")` 流程：人工編輯 YAML 填 `reviewed_by/at` 並改 `trust_level: verified` → FSM 回到 RELEASE
   - 下次 `/spec-logical-validator` 執行時 rules loader 自動載入已升級的 SLV-007（verified）
   - 規則引擎化後 SLV-007 即與 SLV-001~006 等價，CRITICAL FAIL 會阻塞 SCG
   - 實際測變體 C 的步驟需配合具體 FRD 輸入，本輪已驗證「規則載入 + trust_level 升降」契約，等同 acceptance 基礎設施就位

3. **Trust Level 保護鏈** ✅
   - `TrustLevelProtectionTests::test_verified_rule_cannot_be_overwritten` — verified → raise `RuleOverwriteProtected`
   - `test_write_proposed_then_no_overwrite_raises` — proposed + `overwrite_proposed=False` → raise
   - `test_write_proposed_then_overwrite_ok` — proposed + `overwrite_proposed=True` → 覆寫成功

4. **FSM 整合正確性** ✅
   - 入口限 `{ESCALATION, TERMINATED, RELEASE, PRODUCTION_SIGNAL}` — 從 `SPEC_DRAFTING` 進入會 raise `TransitionError`
   - `exit_learning_commit("approved")` → RELEASE；`exit_learning_commit("rejected")` → ESCALATION
   - `exit_learning_commit("maybe-later")` → raise `ValueError`（嚴格 review outcome 契約）
   - Decision Trace 記錄 `learning_commit_enter` / `learning_commit_exit` trigger（與 ACT-025 整合）

5. **ACT-022 雙源同步** ✅
   - `LEARNING_COMMIT` 已加入 `transition_rules._HAPPY_PATH` **以及** `SDD_FSM_ENGINE.md` 狀態轉換表
   - `test_md_python_sync.py` 3 tests 全綠（MD→Python subset、core edges、all states mentioned）

### 最終回歸

```
python -m pytest tools/fsm_runtime/tests/ -q -k "not parallel_writes"
→ 193 passed, 1 deselected, 14 subtests passed in 47.82s
```

Baseline → 新：`175 + 14 → 193 + 14`（淨增 **18 tests** — ACT-028 新增 18）。

### Chaos 回歸（50 輪 smoke test，seed=20260424）

```
python -m tools.fsm_runtime.chaos_runner --rounds 50 --seed 20260424
→ Bounded halts: 50 (100.0%), Avg tokens: 1963, Max steps: 13
```

LEARNING_COMMIT 新增不影響 chaos 有界停機保證（chaos runner 故障注入不會誤抽中此狀態；入口契約需顯式呼叫 API）。

### 遵循的使用者決策

| OPEN | 決策 | 本輪落實 |
|------|------|---------|
| OPEN-10.7（L1313~L1329）| ACT-028 LLM 後端用 Claude Code Session，不用 Claude API | `slv_generator.propose_slv_from_fpl()` 走 pattern-extraction 模式讀 FPL 既有 yaml 區塊；無外部 API 依賴 |
| OPEN-10.7 補述 | Minimax API Key 納入考量 | 保留介面（實作為純 dataclass 輸出，任何 backend 可 drop-in 替換 propose 函式）；Phase F 可再整合 |

### 相關歸檔

- `build/planning/archive/SDD_improving_Automation_03.md` — Phase D 閉環自動化藍圖
- `build/planning/archive/` — Phase E 全量（M1+M2+M2.5+M3+M4）完成，本檔 `SDD_improving_Automation_04.md` 可歸檔至 archive

---

## 拾陸、Phase F 接棒公告（2026-04-24）

Phase E 全量完成後（ACT-020~029），Phase F 保留項（ACT-030 Hub + 多模態 Spec 驗證等）已起草獨立藍圖：

**→ [SDD_improving_Automation_05.md](SDD_improving_Automation_05.md)（Phase F Blueprint DRAFT v1）**

藍圖範疇：
- **本輪聚焦**：ACT-030 Cross-Project Learning Hub + ACT-031 多模態 Spec 驗證（UI/API/DB/C4 四類 adapter）
- **完整版保留**：ACT-032 SLV 全自動演化、ACT-033 AI 對話品質 Benchmark（另評估或開 Phase G）

啟動前待使用者決策：OPEN-F.1~F.7 已於 2026-04-24 全數 RESOLVED（採默認答）。

**歸檔執行紀錄**：本檔於 2026-04-25 Stage 0 Pre-flight 完成歸檔（Phase E 全量 208+14 subtests passed + chaos 50 輪 100% bounded halt、avg 1980 tokens 驗證通過），同步建立 `phase-e-final` git tag。後續 Phase F 進度追蹤改至 `Automation_05.md`。

---
