# ADR-SD09-007 — Hook Governance（Claude Code hooks 啟用門檻與 backlog 處置）

| 項目 | 內容 |
|------|------|
| 編號 | ADR-SD09-007 |
| 狀態 | **ACCEPTED — PM 形式核准 2026-05-21（場景 A dev 自核）** |
| 提出者 | Tech Lead（SD_09 W0 三次 zero-trust audit fix agent D-17）|
| 提出日期 | 2026-05-21 |
| 對應議題 | SD_Improving_09 W0 補修 — Hook 治理 SSOT |
| 相依 ADR | [ADR-SD08-001](ADR-SD08-001-claude-md-budget.md)（CLAUDE.md 預算）/ [ADR-SD08-004](ADR-SD08-004-observability-port.md)（IObservabilityPort）|

---

## 1. 背景

SD_09 W0 啟用 4 個 Claude Code hooks（`.claude/settings.json`）作為 CLAUDE.md prompt 層規範的**事後告警**補強。哲學：**Hook 只能控制 tool 呼叫與生命周期事件，無法直接改變 LLM 內容生成**。因此 prompt 層規範（語言 / 編譯測試循環 / ID 命名）必須保留。

W0 W1 W2 演進至今共設計 8 個 hook（4 active + 4 backlog），缺乏統一的「啟用門檻」治理文件 → 容易出現「為加而加」誤觸發 / 「為刪而刪」失去保護。本 ADR 統一治理。

### 1.1 目前 active 4 hook（已通過 W0）

| Hook | 事件 | Script | 動作 | 單元測試 |
|------|------|--------|------|---------|
| 語言檢查 | Stop | `tools/hooks/check_lang.py` | 偵測 assistant 訊息含韓/日/簡體 → stderr warn（exit 1，不阻斷）| ≥ 3 case |
| 文件路徑強制 | PreToolUse(Write) | `tools/hooks/enforce_docs_path.py` | `.md` 必須在 `docs/0[1-8]_*/` 或根層白名單；違規 exit 2 阻斷 | ≥ 3 case |
| LOC 預算檢查 | PostToolUse(Edit\|Write) | `tools/hooks/loc_budget_check.py` | `.py` 超 tier budget → warn；CLAUDE.md > 400 行 → exit 2 阻斷 | ≥ 3 case |
| Snapshot 新鮮度 | Stop | `tools/hooks/claude_md_freshness.py` | `snapshot_sync.py --check` drift → warn；CLAUDE.md > 400 行 → exit 2 | ≥ 3 case |

### 1.2 Backlog 4 hook（暫未啟用）

| Hook | 暫不啟用理由 | 啟用門檻（本 ADR §2 決議）|
|------|------------|--------------------------|
| `build_test_cycle.py` | PostToolUse 每個 .py edit 都跑測試 → 過慢（單測 80s） | opt-in via env：`AUTOCLAUDE_HOOK_BUILD_TEST=1` 才生效；W1 評估 |
| `agent_autoloader.py` | YAML header 注入誤觸發風險高 | 需 1 週實機誤觸發率 < 5%；W3 評估 |
| `check_id_naming.py` | F-XXX/US-XXX 誤判率高（含程式碼字串） | 需誤判率 < 1%（≥ 100 sample 統計）；W3 評估 |
| `nightly_guard.py` | 設計尚未成熟 | W3 起評估設計選項 |

---

## 2. 決策

### 2.1 Active 4 hook 維持

W0 已驗證 4 active hook 治理價值（語言切換 / 文件落點 / CLAUDE.md 預算 / snapshot drift）；本 ADR 不變動 active 4 hook。

### 2.2 Backlog 4 hook 啟用門檻

| Hook | 啟用門檻 | 評估時程 |
|------|---------|---------|
| `build_test_cycle.py` | **opt-in via env**（預設 disabled；`AUTOCLAUDE_HOOK_BUILD_TEST=1` 才生效）；CI 用 fast mode（只跑被改檔對應 module test）| W1 評估 |
| `agent_autoloader.py` | **誤觸發率 < 5%**（1 週 ≥ 50 次 PreToolUse Edit 採樣）+ YAML header parser 單元測試 ≥ 10 case | W3 評估 |
| `check_id_naming.py` | **誤判率 < 1%**（≥ 100 個含 F-XXX/US-XXX 字串 sample 統計）+ AST-based 過濾程式碼字串 | W3 評估 |
| `nightly_guard.py` | **設計選項 ADR 草案**（待 W3 提出，含告警通道 / 觸發條件 / fail-open vs fail-closed 取捨）| W3 起評估 |

### 2.3 紀律：驗證鏡子自身要被驗證（紀律 #4）

任何 hook 必須有 ≥ 3 case 單元測試，**測試「假 PASS 場景能被拒絕」而非只測通過路徑**。對應 `tests/tools/hooks/` 既有 hook 測試紀律。

### 2.4 SSOT 一致性檢查

`CLAUDE.md §Hook 治理` 表 ↔ `.claude/settings.json hooks` ↔ `tools/hooks/*.py` 三方必須一致；CI nightly W3 起加 `tests/tools/test_hook_governance_consistency.py`（D-18 cross-check 升級為 hook governance contract）。

---

## 3. W1+ 排程

| Wave | 動作 |
|------|------|
| **W1** | 評估 `build_test_cycle.py` opt-in 模式可行性；若可開 → 文件化 env override + fast mode（只跑 module test）|
| **W2** | 落地 `tests/tools/test_hook_governance_consistency.py`（active vs backlog 表 vs settings.json）|
| **W3** | 評估 `agent_autoloader.py` 誤觸發率（需先 1 週採樣）+ `check_id_naming.py` 誤判率 + `nightly_guard.py` 設計選項 |
| **W4+** | 依評估結果啟用 / 維持 backlog / 轉 SD_10 |

---

## 4. 風險與緩解

| 風險 | 嚴重 | 緩解 |
|------|------|------|
| Hook 過多 → Claude Code 啟動延遲 | 🟠 | 採 stage 化啟用（先 4 → 8 漸進）；單 hook 執行時間 < 200ms |
| Hook fail-closed 誤阻塞使用者 | 🔴 | 預設 fail-open（warn 不 exit 2）；只有「真正破壞性」才 fail-closed（如 CLAUDE.md > 400 / docs 落錯目錄）|
| Hook 與 prompt 規範職責重疊 → 雙重執行 | 🟡 | 本 ADR §1 哲學明訂分工：Hook 只做事後告警，prompt 規範主導 LLM 行為 |
| Hook 自身有 bug 阻塞所有 tool 呼叫 | 🔴 | 每 hook ≥ 3 case 單元測試（紀律 #4）；script 異常時 stderr 警告但不退出非 0 |

---

## 5. 簽核

| 角色 | 狀態 | 日期 | 摘要 |
|------|------|------|------|
| Tech Lead / Architect / SA / SD / QA / PM | ✅ ACCEPTED | 2026-05-21 | 場景 A dev 自核（個人開發）；W1 評估 build_test_cycle opt-in |

---

## 6. 相關文件

- [CLAUDE.md §Hook 治理](../../CLAUDE.md) — SSOT 列表
- [.claude/settings.json](../../.claude/settings.json) — Hook 配置檔
- [tools/hooks/](../../tools/hooks/) — Hook 實作
- [tests/tools/hooks/](../../tests/tools/hooks/) — Hook 單元測試
- [ADR-SD08-001](ADR-SD08-001-claude-md-budget.md) — CLAUDE.md 預算治理

---

**文檔元數據**：v1.0 ACCEPTED | 建立 2026-05-21（SD_09 W0 三次 zero-trust audit fix agent D-17 補建）| PM 形式核准 2026-05-21（場景 A dev 自核）| W3 backlog 評估後升 production-ready
