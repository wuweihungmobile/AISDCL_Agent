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

### Step 0：凍結寫入（FSM 尚未在 SPEC_FROZEN 時；🔴 人類明確確認之後才可執行）

本 Skill 的前置條件是「當前 FSM 狀態 = SPEC_FROZEN」。若狀態檔還停在 HUMAN_PENDING（凍結只發生在文件層、FSM 沒寫），
先以 CLI 寫入凍結——這是整條橋接（AutoClaude 凍結閘／Bridge／Console）唯一看得到的凍結憑證；不得手改
`FSM-STATE-*.yaml`（Rule 9 絕對禁令 #1）。完整旗標與 rc 契約見
`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈FSM 寫入指令〉。`--approver` 填**人類**確認者，不得填 agent；
`--doc` 須含要交給 AutoClaude 的 TCS；一律帶 `--digest`（不帶＝舊行為，凍結後改檔偵測不到）。
`<SDD 版本目錄>`＝`AISDLC_SDD/<LATEST>`（現查：`python AISDLC_SDD/scripts/sdd_version.py`）；`<鍵>`＝FSM 專案鍵。

PowerShell（不裸 `cd`；`Push-Location`／`Pop-Location` 同一次呼叫成對）：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; python -m tools.fsm_runtime.fsm_runtime spec-frozen --project "<鍵>" --stage "Stage-<n>" --doc "<凍結文件相對路徑>" --digest --root "<專案根>" --reason "<人類確認依據>" --approver "<人類確認者>" --json; Pop-Location
```

bash／zsh（mac／Linux）：

```bash
cd "<SDD 版本目錄>" && python -m tools.fsm_runtime.fsm_runtime spec-frozen --project "<鍵>" --stage "Stage-<n>" --doc "<凍結文件相對路徑>" --digest --root "<專案根>" --reason "<人類確認依據>" --approver "<人類確認者>" --json
```

外部專案模式（`SDD_STATE_DIR` 有設時改指該目錄，必須是絕對路徑）請套用 `SDD_SPEC_FIRST_GATE.md`〈FSM 寫入指令〉的
第二組樣板（多設 `SDD_STATE_DIR` 與 `SDD_PROJECT`）。

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

若本次 Compaction 是由 90% 閾值的 AUTO_COMPACT_PENDING 觸發（檢查 `build/reports/fsm/FSM-STATE-{project}.yaml` 的 `current_state == "AUTO_COMPACT_PENDING"`；`SDD_STATE_DIR` 有設時改指該目錄），**必須執行**以下指令（PowerShell 或 bash，擇當前平台一種）完成閉環，否則 FSM 會永遠卡在 AUTO_COMPACT_PENDING、Ledger cumulative 也不會歸零，下次 PreToolUse 仍 ≥ 90% 觸發無限迴圈。
cwd 必須是「本 skill 所在的框架版本目錄」`AISDLC_SDD/<LATEST>`（現查：`python AISDLC_SDD/scripts/sdd_version.py`）——
`tools.fsm_runtime` 是以該版本目錄為根的 namespace package，須以其為 cwd 才能解析；勿寫死特定版本號（避免每輪
Copy-on-Evolve 漂移，DEF-CLDREV-008 紀律）。指令把 FSM 從 AUTO_COMPACT_PENDING 轉回原 resume_state，並重置今日 Ledger
cumulative_tokens：

PowerShell（Windows；不裸 `cd`，`Push-Location`／`Pop-Location` 同一次呼叫成對）：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; python -m tools.fsm_runtime.fsm_runtime complete-auto-compact --project "<鍵>"; Pop-Location
```

bash／zsh（mac／Linux）：

```bash
cd "<SDD 版本目錄>" && python -m tools.fsm_runtime.fsm_runtime complete-auto-compact --project "<鍵>"
```

```
# 預期輸出（範例）：
# {"resumed_to": "SPEC_DRAFTING", "ledger": {"reset": true, "path": "...", "previous_cumulative": 184000}}
```

> 🔴 **訂正（整合輪 115／S-19②）**：**被訂正的原文逐字保留（訂正協議：禁止靜默覆寫）**：
> 「`cd AISDLC_SDD_v0.0X && python -m tools.fsm_runtime.fsm_runtime complete-auto-compact`」與句中的「以下兩條 Bash 指令」。
> 為何改：`v0.0X` 佔位對 v0.30 這類兩位次版號易被代成錯版本；原指令是 bash＋裸 `cd`，Windows 鐵律一／二下不可照抄；
> 該區塊實際只有一條指令（不是兩條）。現改為 `<LATEST>` 雙形態（與 `SDD_CONTEXT_GOVERNOR.md` 的 `<LATEST>` 寫法一致）。
> 全文搜尋同一寫法（`cd AISDLC_SDD_v0.0X && …complete-auto-compact`）：全樹僅此一處（`SDD_CONTEXT_GOVERNOR.md` 已用
> `AISDLC_SDD_v<LATEST>`；其餘 `v0.0X` 字樣是 skills README／開發計畫裡的泛稱佔位，不是指令）。

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

**基於**: AISDLC-SDD v0.30（SDD 原生新增 Skill）
**對應藍圖**: SDD_improving_Automation_01.md Phase B — stage-compaction
