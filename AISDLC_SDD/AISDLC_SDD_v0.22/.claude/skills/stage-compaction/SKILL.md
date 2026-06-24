---
name: stage-compaction
description: 在 SDD Stage 凍結里程碑後，強制壓縮上下文視窗，產出 Stage Summary，移除已凍結文件的詳細內容，保持後續 Stage 有足夠的 Token 預算
user-invocable: true
disable-model-invocation: false
argument-hint: "<stage: 0|1|2|3|4|5|6|auto>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
---

# Stage Compaction Skill（SDD 原生）

**SPEC_FROZEN milestone 觸發**：每次規格凍結後強制執行，確保上下文視窗不因累積而耗盡。

---

## 觸發方式

```bash
/stage-compaction auto    # 自動偵測當前 Stage 並執行
/stage-compaction 2       # 指定壓縮 Stage 2 的上下文
/stage-compaction         # 同 auto
```

**自動觸發**：FSM 進入 SPEC_FROZEN milestone 時由系統呼叫，無需手動執行。

---

## 前置條件

- 當前 Stage 所有文件已寫入 docs/ 目錄
- 🔴 Human Checkpoint 已通過（SPEC_FROZEN 狀態）
- 當前 FSM 狀態 = SPEC_FROZEN

---

## 執行步驟

### Step 1：文件持久化驗證

```
讀取 docs/ 目錄，確認當前 Stage 所有文件存在：

Stage 0: docs/02_architecture/adr/ADR-INDEX.md, docs/03_testing/RTM-*.md（骨架）
Stage 1: docs/01_requirements/PRD-*.md
Stage 2: docs/01_requirements/FRD-*.md, docs/03_testing/RTM-*-v1.md
Stage 3: docs/02_architecture/SRD-*.md, docs/02_architecture/C4-*.md, docs/02_architecture/adr/ADR-*.md
Stage 4: docs/02_architecture/api/CONTRACT-*.yaml
Stage 5: docs/03_testing/contracts/TCS-*.md, docs/03_testing/RTM-*-final.md
Stage 6: docs/06_quality/security/SAD-*.md, docs/06_quality/security/STRIDE-*.md
```

若有文件缺失：**停止 Compaction，提示補完文件後再執行**

---

### Step 2：產出 Stage Summary

在上下文中產出以下格式的摘要（目標 ~2000 tokens）：

```markdown
# Stage {N} Summary — {Stage Name}
**凍結日期**: {YYYY-MM-DD}
**凍結狀態**: ✅ FROZEN（Human Approved）

## 完成文件清單
| 文件 | 路徑 | 狀態 |
|------|------|------|
| PRD | docs/01_requirements/PRD-{system}.md | ✅ Approved |
| FRD | docs/01_requirements/FRD-{system}.md | ✅ Approved |

## 關鍵決策摘要
| ADR | 決策摘要 | 狀態 |
|-----|---------|------|
| ADR-001 | 使用 PostgreSQL 作為主資料庫 | Accepted |
| ADR-002 | 採用 REST API 架構 | Accepted |

## RTM 覆蓋率快照
- EPIC: {N}個 | Feature: {N}個 | US: {N}個 | AC: {N}個
- AT 覆蓋率: {XX}%
- 未覆蓋 AC: {列出 ID，或「無」}

## API Contract 狀態（Stage 4後）
- 凍結端點: {N}個（模組清單）
- 未凍結: {N}個（預計 Stage N 完成）

## NFR 量化目標
| NFR 類型 | 目標值 | 文件位置 |
|---------|-------|---------|
| 回應時間 P95 | < 200ms | FRD L.XX |
| 可用性 | 99.9% | SRD L.XX |

## SCG 通過記錄
- SCG-{N}: ✅ 通過（日期 + 執行者）

## 下一 Stage 前置條件
- {列出必須已完成的項目}

## 已知風險與待確認項目
- {如有，列出}
```

---

### Step 3：宣告上下文清除

執行後，**明確聲明**以下內容已從活躍上下文移除（轉為 docs/ 引用）：

```
✅ 已壓縮（可從 docs/ 按需讀取）：
  - 完整 PRD 文字
  - 完整 FRD 文字（含所有 AC 詳細描述）
  - C4 圖詳細描述
  - 完整 OpenAPI Schema（含所有 Request/Response 欄位）
  - ADR 詳細分析內容
  - 過往 SCG 失敗記錄

✅ 保留在活躍上下文：
  - 此 Stage Summary（~2K tokens）
  - RTM ID 清單（AC ID + 覆蓋狀態，無詳細描述）
  - API 端點名稱清單（無 Schema）
  - ADR 編號 + 狀態清單（無詳細內容）
  - 當前活躍 Agent 配置

📁 下次需要詳細內容時，使用 Read 工具讀取對應 docs/ 文件。
```

---

### Step 4：輸出壓縮報告

```
✅ Stage Compaction 完成

Stage {N}（{Stage Name}）已凍結並壓縮。

Token 節省估算：
  壓縮前：~{X}K tokens
  壓縮後：~{Y}K tokens（-{Z}%）

Stage Summary 已建立，包含所有關鍵決策摘要。
後續需要詳細規格時，使用 Read 工具讀取 docs/ 對應文件。

下一 Stage：{Stage N+1} — {Stage Name}
```

---

### Step 5：FSM 閉環收尾（90% Auto-Compact 觸發時必執行）

若本次 Compaction 是由 90% 閾值的 AUTO_COMPACT_PENDING 觸發（檢查 `build/reports/fsm/FSM-STATE-{project}.yaml` 的 `current_state == "AUTO_COMPACT_PENDING"`），**必須執行**以下兩條 Bash 指令完成閉環，否則 FSM 會永遠卡在 AUTO_COMPACT_PENDING、Ledger cumulative 也不會歸零，下次 PreToolUse 仍 ≥ 90% 觸發無限迴圈：

```bash
# 1) 將 FSM 從 AUTO_COMPACT_PENDING 轉回原 resume_state，並重置今日 Ledger cumulative_tokens
#    cd 至「本 skill 所在的框架版本目錄根」（AISDLC_SDD_v0.0X/，X=當前版本）——tools.fsm_runtime
#    是以該版本目錄為根的 namespace package，須以其為 cwd 才能解析；勿寫死特定版本號（避免
#    每輪 Copy-on-Evolve 漂移，DEF-CLDREV-008 紀律）。
cd AISDLC_SDD_v0.0X && python -m tools.fsm_runtime.fsm_runtime complete-auto-compact

# 預期輸出（範例）：
# {"resumed_to": "SPEC_DRAFTING", "ledger": {"reset": true, "path": "...", "previous_cumulative": 184000}}
```

若 `complete-auto-compact` 回傳 `{"noop": true, ...}`，表示 FSM 不在 AUTO_COMPACT_PENDING，本次屬一般 SPEC_FROZEN compaction，不需執行 Step 5。

執行成功後，直接繼續原工作（`resumed_to` 即下一個應進入的狀態）。

---

## 強制產出

| 產出物 | 位置 | 說明 |
|--------|------|------|
| Stage Summary | 上下文中（~2K tokens） | 取代詳細文件內容 |
| Compaction 記錄 | `build/reports/compaction/COMPACT-Stage{N}-{date}.md` | 選配，記錄壓縮前後狀態 |

---

## 相關文件

- [SDD_CONTEXT_GOVERNOR.md](../../../workflow/sdd-context-governor/SDD_CONTEXT_GOVERNOR.md) — 完整預算管理策略
- [SDD_FSM_ENGINE.md](../../../workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) — SPEC_FROZEN 觸發點
- [SDD_ESCALATION_PROTOCOL.md](../../../workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md) — 95% 緊急處理

---

**基於**: AISDLC-SDD v0.21（SDD 原生新增 Skill）
**對應藍圖**: SDD_improving_Automation_01.md Phase B — stage-compaction
