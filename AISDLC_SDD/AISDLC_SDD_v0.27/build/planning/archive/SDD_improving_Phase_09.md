# SDD 改善報告 — Phase 09 QA 審查

**審查日期**: 2026-04-16
**審查人員**: SDD-QA 專家（自動化審查）
**審查範圍**: AISDLC_v0.09 → AISDLC_SDD_v0.01 完整性比對
**審查方法**: 實際讀取所有檔案清單、關鍵索引文件、計算實際數量

---

## 執行摘要

本次審查發現以下問題：

- **文件數量聲明不一致（文件錯誤）**: 12 項
- **結構性遺漏（缺少文件/目錄）**: 6 項
- **版本未更新（版本號殘留 v0.09）**: 5 項
- **閘門定義不一致（SCG 命名衝突）**: 1 項（嚴重）
- **INIT.md 說法過時**: 3 項
- **問題總計**: 27 項

**總體評估**：AISDLC_SDD_v0.01 框架核心功能完整，但存在多個文件說明數字嚴重過時、關鍵文件版本號未更新、以及 SCG 閘門命名不一致的問題，需要優先修復。

---

## 1. Agent 審查

### 1.1 數量比對

| 項目 | v0.09 實際數量 | SDD 宣稱數量（CLAUDE.md） | SDD 實際數量 | 差異 |
|------|--------------|--------------------------|-------------|------|
| 核心 Agent (core/) | 7（含模板） | 7 | 7 | ✅ 一致 |
| 專業化 Agent (specialized/) | 14 | 14 | 14 | ✅ 一致 |
| 合計（含模板） | 21 | 21 | 21 | ✅ 一致 |

> **說明**：CLAUDE.md 宣稱「21 Agents（7 core + 14 specialized）」，實際數量吻合。其中 `01.agent-template-zh.yaml` 為模板，非實際使用 Agent，故有效 Agent 為 20 個。

### 1.2 SDD 技能新增狀況

根據 `agent/README.md` v0.01-SDD 版本記錄，所有 Agent 已完成 SDD 技能升級：

- `04.sa-analyst-zh.yaml`：新增逆向規格工程、Gap Analysis、Invariants 提取
- `05.sd-architect-zh.yaml`：新增 As-Is C4、ADR Archaeology、Before/After 比較
- `07.qa-tester-zh.yaml`：新增 As-Is 測試規格、Invariant Test Contract
- `code-analyzer-zh.yaml`：新增 Tech Debt 規格化、品質基準線
- `dev-senior-zh.yaml`：新增 Strangler Fig / Branch by Abstraction
- `technical-writer-zh.yaml`：新增 Living Documentation、ADR 維護

### 1.3 遺漏：backup_en 目錄

| 項目 | v0.09 狀態 | SDD 狀態 | 說明 |
|------|-----------|---------|------|
| `agent/core/backup_en/` | 存在（8 個檔案） | **不存在** | 刻意去除（SDD 僅維護中文版）|
| `agent/specialized/backup_en/` | 存在（15 個檔案） | **不存在** | 刻意去除（SDD 僅維護中文版）|

**評估**：刻意設計，非遺漏。但 `agent/README.md` 目前仍提及 `backup_en/` 目錄（第 37 行「14 個英文版 Agent YAML」），卻實際上不存在，造成文件與實際結構不符。

---

## 2. Skills 審查

### 2.1 數量比對

| 項目 | v0.09 實際數量 | SDD 宣稱數量 | SDD 實際數量 | 差異 |
|------|--------------|-------------|-------------|------|
| SKILL.md 檔案 | 33 | CLAUDE.md 說 33 | **39** | ❌ CLAUDE.md 過時 |
| SDD 專屬新增 Skills | 0 | - | 6（新增） | - |
| 合計 | 33 | 33（CLAUDE.md） | 39 | ❌ 差 6 個 |

### 2.2 數量聲明不一致

**問題**：CLAUDE.md 第一層說「33 Claude Code Skills」，但實際 SDD v0.01 已有 39 個 SKILL.md。

根據 `.claude/skills/README.md`（v0.02-SDD）的正確說明：
- 繼承自 v0.09：33 個（已 SDD 強化改寫）
- SDD 專屬新增：6 個（adr-generate, spec-compliance-check, rtm-generate, contract-generate, sdd-gate, sdd-review）
- **正確總計：39 個**

**CLAUDE.md 需要更新「33 Claude Code Skills」→「39 Claude Code Skills（33 繼承強化 + 6 SDD 新增）」**

### 2.3 v0.09 vs SDD Skills 對應

| v0.09 Skills | SDD 對應 | 狀態 |
|-------------|---------|------|
| 33 個 SKILL.md | 33 個已強化改寫 | ✅ 全部移植並升級 |
| （無 SDD 專屬） | 6 個新增（adr-generate, spec-compliance-check, rtm-generate, contract-generate, sdd-gate, sdd-review） | ✅ 新增 |

---

## 3. Scenarios 審查

### 3.1 數量比對

| 項目 | v0.09 狀態 | SDD 狀態 | 差異 |
|------|-----------|---------|------|
| 場景總數 | 10 個（greenfield/brownfield/refactoring/documentation/devops/integration/migration/performance/security/testing） | 10 個 | ✅ 一致 |
| SDD Enhancement 文件 | 4 個（greenfield/brownfield/refactoring/documentation） | **10 個** | ✅ SDD 新增 6 個 |

### 3.2 各場景完整性逐一驗證

| 場景 | v0.09 SOP.md | v0.09 SOP_DeepDive | v0.09 SOP_QuickRef | v0.09 SDD_ENHANCEMENT | SDD SOP.md | SDD SOP_DeepDive | SDD SOP_QuickRef | SDD SDD_ENHANCEMENT |
|------|-------------|-------------------|-------------------|----------------------|-----------|-----------------|-----------------|---------------------|
| greenfield | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| brownfield | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| refactoring | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| documentation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| devops | ✅ | ✅ | ✅ | **❌（v0.09 無）** | ✅ | ✅ | ✅ | ✅（SDD 新增）|
| integration | ✅ | ✅ | ✅ | **❌（v0.09 無）** | ✅ | ✅ | ✅ | ✅（SDD 新增）|
| migration | ✅ | **❌（v0.09 無）** | ✅ | **❌（v0.09 無）** | ✅ | ✅（SDD 新增）| ✅ | ✅（SDD 新增）|
| performance | ✅ | ✅ | ✅ | **❌（v0.09 無）** | ✅ | ✅ | ✅ | ✅（SDD 新增）|
| security | ✅ | ✅ | ✅ | **❌（v0.09 無）** | ✅ | ✅ | ✅ | ✅（SDD 新增）|
| testing | ✅ | ✅ | ✅ | **❌（v0.09 無）** | ✅ | ✅ | ✅ | ✅（SDD 新增）|

**結論**：所有 10 個場景均完整，SDD v0.01 較 v0.09 在 6 個場景新增了 SDD Enhancement 文件，migration 場景額外新增了 SOP_DeepDive。

---

## 4. Workflow 審查

### 4.1 數量比對

| 項目 | v0.09 數量 | SDD 宣稱數量（CLAUDE.md） | SDD 實際數量 | 差異 |
|------|-----------|--------------------------|-------------|------|
| 核心 Workflow (core/) | 8 | - | 8 | ✅ 一致 |
| 場景 Workflow (scenario-specific/) | 13 | - | 13 | ✅ 一致 |
| SDD 專屬 (sdd-spec-first-gate/) | 0 | - | 1 | ✅ SDD 新增 |
| ADR 生成 (adr-generation/) | 1 | - | 1 | ✅ 一致 |
| **合計** | **22（含 adr-generation）** | **23** | **23** | ✅ 一致 |

**計算說明**：v0.09 = 8 core + 13 scenario + 1 adr-generation = 22；SDD 加上 SDD_SPEC_FIRST_GATE = 23。

### 4.2 嚴重問題：Workflow README 版本號未更新

**問題**：`AISDLC_SDD_v0.01/workflow/README.md` 第 4 行仍顯示「**版本**: v0.09」，第 11 行仍說「AISDLC v0.09 提供...」，第 130 行引用 `AISDLC_INIT.md`（應為 `AISDLC_SDD_INIT.md`）。

**路徑**：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/workflow/README.md`

---

## 5. Guide 審查

### 5.1 數量比對

| 項目 | v0.09 數量 | SDD 宣稱數量（CLAUDE.md） | SDD 實際數量 | 差異 |
|------|-----------|--------------------------|-------------|------|
| system/ md 檔案 | 20 | - | 21（含 sdd/SDD_GUIDE.md）| ✅ SDD 新增 1 個 |
| user/ md 檔案（含 sample，含 README） | 36 | - | 35 | 略減 |
| 合計（含 README，不含 backup） | 56 | 55+ | **57** | ✅ 符合 55+ |

### 5.2 遺漏：guides/backup 目錄

| 項目 | v0.09 狀態 | SDD 狀態 | 說明 |
|------|-----------|---------|------|
| `guides/backup/HOW_TO_RESUME.md` | 存在 | **不存在** | SDD 未移植 |
| `guides/backup/INDEX.md` | 存在 | **不存在** | SDD 未移植 |
| `guides/backup/REVIEW_INDEX.md` | 存在 | **不存在** | SDD 未移植 |
| `guides/backup/REVIEW_QUICK_REFERENCE.md` | 存在 | **不存在** | SDD 未移植 |
| `guides/backup/README.md` | 存在 | **不存在** | SDD 未移植 |

**評估**：guides/backup/ 目錄整個未移植至 SDD。根據 v0.09 的 `guides/README.md` 說明，backup 是歷史文件備份，屬低優先遺漏，但 guides/README.md 在 SDD 版本中仍有提及 backup 目錄（第 178 行），造成說明不符。

### 5.3 新增 Guide

SDD v0.01 新增了 `guides/system/sdd/SDD_GUIDE.md`（SDD 核心指引），這是 v0.09 沒有的。

---

## 6. Prompt 審查

### 6.1 數量比對

| 項目 | v0.09 數量 | SDD 數量 | 差異 |
|------|-----------|---------|------|
| quick-start/ | 4 | 4 | ✅ 一致 |
| complete-flow/ | 2（含 README） | 2（含 README） | ✅ 一致 |
| scenario-prompts/ | 10（無 README） | 11（含 README） | ✅ SDD 新增 README |
| README.md | 1 | 1 | ✅ 一致 |

### 6.2 新增項目

SDD v0.01 在 `prompts/scenario-prompts/` 目錄新增了 `README.md`，這是 v0.09 沒有的。

### 6.3 內容更新狀態

Prompt 文件是否已更新為 SDD 版本（含 SCG 閘門說明）需要進一步內容審查，本次僅驗證結構完整性。

---

## 7. Template 審查

### 7.1 數量比對（嚴重不一致）

| 文件聲明位置 | 聲明數量 | 實際計算 | 差異 |
|------------|---------|---------|------|
| `AISDLC_SDD_INIT.md`（第 19 行） | 「18 個」SDD 專屬模板 | **48 個 .md + 3 個 .yaml = 51 個** | ❌ 嚴重過時 |
| `FILE_DIRECTORY_RULES.md`（Layer 2 說明） | 「18 SDD + 50+ AISDLC」 | 實際 51 個（含 yaml）| ❌ 嚴重過時 |
| `CLAUDE.md` | 「19 個 SDD 專屬模板」 | **51 個** | ❌ 嚴重過時 |
| `docs_template/README.md`（版本 v0.09） | 無 sdd/ 目錄說明 | - | ❌ 未更新 |

### 7.2 docs_template/sdd/ 實際子目錄統計

| 子目錄 | 實際檔案數 | 說明 |
|--------|----------|------|
| requirements/ | 2 | INVARIANT-SPEC + THIRD-PARTY-API-RESEARCH |
| architecture/ | 11 | 含 AD-INTEGRATION-ACL、AFTER/BEFORE-ARCH、AS-IS/TO-BE-SRD、INFRA-REQUIREMENTS-SPEC、MIGRATION-ADR/CONTRACT-MAP、SAD、SDD-COMPLIANCE-AUDIT、TRUST-BOUNDARY-MAP |
| adr/ | 4 | ADR-INDEX、ADR-TEMPLATE、AUTOMATION-FRAMEWORK-ADR、PERFORMANCE-OPTIMIZATION-ADR |
| api/ | 4（含 3 yaml） | API-COMPAT + CONTRACT-TEMPLATE.yaml + CONSUMER-CONTRACT-TEMPLATE.yaml + PROVIDER-API-SPEC-TEMPLATE.yaml |
| testing/ | 18 | 含 ASSET-INVENTORY、BASELINE-PERFORMANCE-REPORT、CHAOS-CONTRACT、COMPLIANCE-MATRIX、CONTRACT-TEST-SPEC-INTEGRATION/MIGRATION、DATA-INTEGRITY-TEST-SPEC、DEFECT-CLASSIFICATION-SPEC、ENV-CONTRACT-SPEC、INVARIANT-TEST-CONTRACT、LIVING-TEST-REPORT、PERFORMANCE-BASELINE-SPEC、RTM、RTM-EXISTING-SYSTEM、SECURITY-TEST-SPEC、STRIDE-THREAT-MODEL、TEST-CONTRACT-SPEC、TEST-STRATEGY-SPEC |
| planning/ | 2 | GAP-ANALYSIS + REFACTOR-PLAN |
| quality/ | 2 | CODE-QUALITY-BASELINE + TECH-DEBT-SPEC |
| development/ | 1 | LIVING-DOC-STRATEGY |
| deployment/ | 7 | CANARY-SPEC、CUTOVER-SPEC、INCIDENT-RESPONSE-SPEC、MONITORING-ALERT-SPEC、PIPELINE-SPEC、ROLLBACK-SPEC、SECURITY-MONITORING-SPEC |
| **總計** | **51** | **（48 md + 3 yaml）** |

### 7.3 docs_template/README.md 未更新

**問題**：`docs_template/README.md` 版本仍為 v0.09（最後更新 2025-11-11），目錄結構說明中**完全沒有提及 `sdd/` 目錄**，也沒有更新以反映 51 個 SDD 模板的存在。

**路徑**：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/docs_template/README.md`

### 7.4 AISDLC_SDD_INIT.md 模板索引與實際不符

`AISDLC_SDD_INIT.md` 的「SDD 模板索引」表格（第 284~330 行）列出 30+ 個模板，但第 19 行說「18 個」，且表格本身列出超過 18 個，前後矛盾。

---

## 8. Tools 審查

### 8.1 數量比對

| 工具 | v0.09 狀態 | SDD 狀態 | 差異 |
|------|-----------|---------|------|
| `init_project.sh` | ✅ 存在 | ✅ 存在（v3.3-SDD，支援 --sdd 模式）| ✅ 已更新 |
| `init_project.ps1` | ✅ 存在 | ✅ 存在 | 需確認版本 |
| `verify_traceability.sh` | ✅ 存在 | ✅ 存在（v1.0，建立日期 2026-02-11）| ⚠️ 未更新 SDD 路徑 |
| `AISDLC_CLAUDE_RULES.md` | ✅ 存在 | ✅ 存在（v1.1，適用 v0.09+）| ⚠️ 版本說明未更新 |
| `PROJECT_CLAUDE_Template.md` | ✅ 存在 | ✅ 存在 | 需確認 |
| `README.md` | ✅ 存在 | ✅ 存在 | 需確認 |

### 8.2 工具更新問題

**問題 1**：`verify_traceability.sh` 版本 v1.0，建立日期 2026-02-11，說明中仍使用舊路徑 `AISDLC/framework/tools/`，未反映 SDD 的新目錄結構（docs/ 子目錄結構）。

**問題 2**：`AISDLC_CLAUDE_RULES.md` 標示「**適用範圍**: AISDLC v0.09+ 所有專案」，版本 v1.1，但未明確提及 AISDLC-SDD v0.01 的特定規則（如 SCG 閘門）。

---

## 9. 版本控管審查

### 9.1 版本追蹤機制

SDD v0.01 新增了以下版本管理文件（v0.09 沒有）：

| 文件 | 路徑 | 狀態 |
|------|------|------|
| `AISDLC_SDD_UPGRADE_SOP.md` | 根目錄 | ✅ 存在 |
| `AISDLC_SDD_UPGRADE_CHECKLIST.md` | 根目錄 | ✅ 存在 |
| `SDD_VERSION_HISTORY.md` | 根目錄 | ✅ 存在 |
| `RELEASE_NOTES_v0.01.md` | `releases/v0.01/` | ✅ 存在 |

### 9.2 releases 目錄差異

| 項目 | v0.09 | SDD v0.01 | 說明 |
|------|-------|---------|------|
| 實際打包文件（.tar.gz） | ✅ 有（1.7MB 實際文件）| **❌ 無** | SDD 尚未產出實際打包文件 |
| SHA256 驗證文件 | ✅ 有 | **❌ 無** | 同上 |
| RELEASE_NOTES | ✅ 有 | ✅ 有 | ✅ 完整 |
| backups/ | 有 package/ 目錄 | 有 backups/.gitkeep | 結構不同 |

**評估**：SDD v0.01 的 releases/ 缺少實際打包文件（.tar.gz）和 SHA256。這表示 v0.01 尚未完成正式打包發布。

---

## 10. 目錄結構審查

### 10.1 FILE_DIRECTORY_RULES.md 完整性

`FILE_DIRECTORY_RULES.md` 版本 v0.04，建立日期 2026-04-12，已更新至 2026-04-15，整體結構完整，但存在以下問題：

| 問題 | 位置 | 說明 |
|------|------|------|
| Layer 2 說「18 SDD 模板」 | 第 284 行 | 實際 51 個，已嚴重過時 |
| Layer 2 說「60+ guides」 | 第 286 行 | 實際 57 個，略有差異 |
| Layer 2 說「33+ Skills」 | 第 287 行 | 實際 39 個，未更新 |

### 10.2 DEVELOPMENT_DIRECTORY_STRUCTURE.md 遺漏

| 項目 | v0.09 狀態 | SDD 狀態 | 說明 |
|------|-----------|---------|------|
| `DEVELOPMENT_DIRECTORY_STRUCTURE.md` | ✅ 存在（根目錄） | **❌ 不存在** | SDD 未移植此文件 |

**評估**：v0.09 根目錄有 `DEVELOPMENT_DIRECTORY_STRUCTURE.md`，說明開發期間的完整目錄結構。SDD v0.01 此文件由 `FILE_DIRECTORY_RULES.md` 取代，屬設計選擇，非遺漏。

### 10.3 build/logs 目錄差異

| 項目 | v0.09 狀態 | SDD 狀態 | 說明 |
|------|-----------|---------|------|
| build/logs/ | 有 stage_3.checkpoint, stage_5.checkpoint | **空目錄** | SDD 無工作日誌 |

---

## 11. 其他遺漏與問題

### 11.1 SCG 閘門命名嚴重不一致（最重要問題）

**問題**：框架中存在兩套不同的 SCG 閘門命名體系，且兩者均有官方文件支持：

**體系 A（AISDLC_SDD_INIT.md、CLAUDE.md 採用）**：

| Gate | 名稱 | 觸發時機 |
|------|------|---------|
| SCG-0 | Requirement Spec Gate | 需求凍結前 |
| SCG-1 | Design Spec Gate | 設計凍結前 |
| SCG-2 | Architecture Review Gate | 架構凍結前 |
| SCG-3 | Contract Freeze Gate | 開發啟動前 |
| SCG-4 | Implementation Compliance Gate | PR Review |
| SCG-5 | RTM Completeness Gate | 交付前 |
| SCG-6 | Release Readiness Gate | 發布前 |

**體系 B（guides/system/sdd/SDD_GUIDE.md 採用）**：

| Gate | 名稱 | 觸發時機 |
|------|------|---------|
| SCG-1 | Requirement Spec Gate | 需求凍結前 |
| SCG-2 | Architecture Spec Gate | 設計凍結前 |
| SCG-3 | API Contract Gate | 開發啟動前 |
| SCG-4 | Test Strategy Gate | 測試開始前 |
| SCG-5 | Security Spec Gate | 安全設計凍結前 |
| SCG-6 | Performance Baseline Gate | 效能測試前 |
| SCG-Doc | Documentation Audit Gate | 文件交付前 |
| SCG-Pipeline | Pipeline Spec Gate | CI/CD 設計前 |

**嚴重性**：SCG-4 在體系 A 是「PR Review」，在體系 B 是「測試策略」，語義完全不同。SCG-5 在體系 A 是「RTM 100% 覆蓋」，在體系 B 是「安全設計閘門」，同樣衝突。

**路徑**：
- 體系 A：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md`
- 體系 B：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/guides/system/sdd/SDD_GUIDE.md`

### 11.2 AISDLC_SDD_INIT.md 多個過時說法

| 問題 | 位置 | 現況說明 |
|------|------|---------|
| 說「新增 SDD 專屬模板（18 個）」 | 第 19 行 | 實際 51 個（.md 48 + .yaml 3） |
| 說「CI/CD 規格（4 個）」 | 第 19 行 | 實際 9 個 |
| 說「支援三大場景：Greenfield、Brownfield、Refactoring」 | 第 21 行 | 實際支援 10 個場景，均有 SDD Enhancement |

### 11.3 workflow/README.md 版本號未更新

**問題**：`AISDLC_SDD_v0.01/workflow/README.md` 版本標示仍為 v0.09，且內文引用 `AISDLC_INIT.md`（應為 `AISDLC_SDD_INIT.md`）。

**路徑**：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/workflow/README.md`

### 11.4 docs_template/README.md 完全未更新

**問題**：版本 v0.09，最後更新 2025-11-11，目錄結構說明完全缺少 `sdd/` 目錄（51 個 SDD 專屬模板）的說明。

**路徑**：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/docs_template/README.md`

### 11.5 agent/README.md 引用不存在的 backup_en 目錄

**問題**：`agent/README.md` 第 37~38 行說明 specialized/ 目錄下有 `backup_en/`（含 14 個英文版 Agent YAML），但 SDD v0.01 實際上已刻意去除 backup_en 目錄。

**路徑**：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/agent/README.md`

### 11.6 guides/README.md 引用不存在的 backup 目錄

**問題**：`guides/README.md` 第 179 行描述 `backup/` 目錄（含 5 個文件），但 SDD v0.01 沒有移植 `guides/backup/` 目錄。

**路徑**：`d:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01/guides/README.md`

---

## 問題彙整表

| 編號 | 類別 | 問題描述 | 嚴重度 | 建議行動 |
|------|------|---------|-------|---------|
| P01 | SCG 閘門 | SDD_GUIDE.md 與 AISDLC_SDD_INIT.md 的 SCG 閘門編號和語義完全不同，SCG-4/SCG-5 語義衝突 | 🔴 高 | 統一 SCG 閘門定義，選定一套體系後全面更新 |
| P02 | Template 數量 | CLAUDE.md 說「19 個 SDD 專屬模板」，實際 51 個（.md 48 + .yaml 3） | 🔴 高 | 更新 CLAUDE.md 數字 |
| P03 | Template 數量 | AISDLC_SDD_INIT.md 說「18 個」SDD 模板，實際 51 個 | 🔴 高 | 更新 INIT.md 數字 |
| P04 | CI/CD 數量 | CLAUDE.md 和 INIT.md 說「4 個」CI/CD 規格，實際 9 個 | 🔴 高 | 更新兩處的數字（4→9） |
| P05 | Skills 數量 | CLAUDE.md 說「33 Claude Code Skills」，實際 39 個 | 🔴 高 | 更新 CLAUDE.md（33→39） |
| P06 | Template README | docs_template/README.md 版本 v0.09，完全未提及 sdd/ 目錄 51 個模板 | 🔴 高 | 大幅更新 docs_template/README.md |
| P07 | Workflow README | workflow/README.md 版本 v0.09，仍引用 AISDLC_INIT.md | 🟡 中 | 更新版本號和引用路徑 |
| P08 | INIT 說法過時 | AISDLC_SDD_INIT.md 說「支援三大場景」，實際支援 10 個場景，均有 SDD Enhancement | 🟡 中 | 更新 INIT.md 第 21 行說法 |
| P09 | Agent README | agent/README.md 第 37~38 行引用不存在的 backup_en/ 目錄（14 個英文版 Agent） | 🟡 中 | 更新 agent/README.md 刪除 backup_en 引用 |
| P10 | Guides 遺漏 | guides/backup/ 目錄整個未移植（5 個歷史文件），但 guides/README.md 第 179 行仍引用 | 🟡 中 | 選擇：移植 backup/ 目錄，或從 guides/README.md 移除引用 |
| P11 | FILE_DIRECTORY 數字 | FILE_DIRECTORY_RULES.md Layer 2 說「18 SDD 模板」、「33+ Skills」，均過時 | 🟡 中 | 更新 FILE_DIRECTORY_RULES.md 數字 |
| P12 | Releases 不完整 | releases/v0.01/ 只有 RELEASE_NOTES，缺少實際打包 .tar.gz 和 SHA256 | 🟡 中 | 製作實際打包文件 |
| P13 | Tools 路徑過時 | verify_traceability.sh 說明中使用舊路徑 AISDLC/framework/tools/ | 🟢 低 | 更新腳本說明 |
| P14 | Tools 版本說明 | AISDLC_CLAUDE_RULES.md 說「v0.09+ 所有專案」，未明確納入 SDD v0.01 | 🟢 低 | 更新版本範圍說明 |
| P15 | Build logs | build/logs/ 目錄為空，v0.09 有 checkpoint 文件 | 🟢 低 | 評估是否需要初始 checkpoint |

---

## 改善優先順序

### 🔴 高優先（阻礙使用或造成混亂）

1. **P01 — SCG 閘門命名不一致**（最優先）
   - `SDD_GUIDE.md` 與 `AISDLC_SDD_INIT.md`、`CLAUDE.md` 的 SCG 閘門體系完全不同
   - 使用者無法確定「SCG-4」到底是 PR Review 還是測試策略閘門
   - **建議**：以 `AISDLC_SDD_INIT.md`（SCG-0~6 體系）為準，更新 `SDD_GUIDE.md`，或反之統一採用 SDD_GUIDE.md 的體系（需全面審查）

2. **P02/P03/P04/P05 — 多處數字嚴重過時**
   - CLAUDE.md：「33 Skills」→「39 Skills」、「19 個 SDD 模板」→「51 個 SDD 模板」、「4 個 CI/CD」→「9 個 CI/CD」
   - INIT.md：「18 個模板」→「51 個」、「CI/CD 規格（4 個）」→「9 個」、「三大場景」→「10 個場景」
   - **建議**：立即更新 CLAUDE.md 和 AISDLC_SDD_INIT.md 的統計數字

3. **P06 — docs_template/README.md 完全未更新**
   - 版本 v0.09，最後更新 2025-11-11，完全沒有 sdd/ 目錄的說明
   - 使用者查看模板目錄無法找到 SDD 專屬模板
   - **建議**：全面改寫 docs_template/README.md 以反映 SDD 結構

### 🟡 中優先（功能不完整）

4. **P07 — workflow/README.md 版本號和引用未更新**
   - 版本 v0.09，引用 AISDLC_INIT.md（不存在的路徑）
   - **建議**：更新版本號和文件引用路徑

5. **P08 — INIT.md「三大場景」說法過時**
   - 現在有 10 個場景均有 SDD Enhancement，說「三大場景」嚴重誤導
   - **建議**：更新第 21 行說法，改為「10 個場景均有 SDD Enhancement」

6. **P09 — agent/README.md 引用不存在目錄**
   - 引用已不存在的 backup_en/ 目錄
   - **建議**：更新 agent/README.md 移除 backup_en 相關說明或改為說明此設計決策

7. **P10 — guides/README.md 引用不存在的 backup 目錄**
   - guides/backup/ 整個未移植，但 README 仍引用
   - **建議**：從 guides/README.md 移除 backup/ 目錄引用，或補齊 backup/ 內容

8. **P11 — FILE_DIRECTORY_RULES.md 數字未更新**
   - Layer 2 說「18 SDD 模板」、「33+ Skills」，均嚴重過時
   - **建議**：更新 FILE_DIRECTORY_RULES.md 的統計數字

9. **P12 — releases/v0.01/ 缺少打包文件**
   - 尚未製作 .tar.gz 發布包
   - **建議**：執行打包流程，產出 AISDLC-SDD_v0.01_release_YYYY-MM-DD.tar.gz

### 🟢 低優先（最佳化）

10. **P13 — verify_traceability.sh 路徑說明過時**
11. **P14 — AISDLC_CLAUDE_RULES.md 版本範圍說明未納入 SDD v0.01**
12. **P15 — build/logs 目錄為空**

---

## Next Actions

### 立即執行（本次 Phase 09）

1. **[P01] 統一 SCG 閘門定義**
   - 確認採用哪一套體系（建議以 INIT.md 的 SCG-0~6 為準）
   - 更新 `guides/system/sdd/SDD_GUIDE.md` 的 SCG 閘門表格

2. **[P02~P05] 更新數字聲明**
   - 修改 `CLAUDE.md`：Skills 數量（33→39）、SDD 模板數量（19→51）、CI/CD 數量（4→9）
   - 修改 `AISDLC_SDD_INIT.md`：SDD 模板數量（18→51）、CI/CD 數量（4→9）、場景說明（三大→10個）

3. **[P06] 改寫 docs_template/README.md**
   - 更新版本號（v0.09→v0.01-SDD）
   - 新增 sdd/ 目錄完整說明（51 個模板）

4. **[P07] 更新 workflow/README.md**
   - 版本號（v0.09→v0.01-SDD）
   - 更新引用（AISDLC_INIT.md→AISDLC_SDD_INIT.md）

5. **[P09] 更新 agent/README.md**
   - 移除或更新 backup_en/ 相關說明

6. **[P10] 處理 guides/backup 問題**
   - 建議：從 guides/README.md 移除 backup/ 目錄引用（低歷史價值）

### 後續執行（Phase 10）

7. **[P11] 更新 FILE_DIRECTORY_RULES.md 數字**
8. **[P12] 製作 v0.01 實際打包文件**
9. **[P13/P14] 更新工具說明文件**

---

**報告產出時間**: 2026-04-16
**資料來源**: 實際執行 find 指令取得所有檔案清單，並讀取關鍵索引文件進行比對
**下次審查建議**: 完成 P01~P06 修復後，執行 Phase 10 驗證審查
