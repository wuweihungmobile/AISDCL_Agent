# Agent broken `template_path` 處置裁決書

> **狀態**：✅ **已決並套用**（2026-06-22 掌舵者 signoff：方案一「重新接線」+ 配套）。詳見文末「§5 套用結果」。
> **產生於**：2026-06-22 agent/* 符規審查（v0.17→v0.18）
> **關聯**：`EVOLUTION_LOG.md` v0.17→v0.18、`Agent_Conformance_Audit_v0.18.md`、`AutoSDD_Defect_Log.md` DEF-AGTREV-002
> **範圍界定**：本輪（v0.18）**已修** 3 處 WRONGDIR（檔案存在、僅路徑指錯目錄）；本書處理**另一批指向「完全不存在目錄／裸檔名」的 ~40 條 broken path**，因涉框架語意（要不要補建模板、要不要刪欄位），**刻意不自主硬改**。

---

## 1. 問題本質

SD 專家 zero-trust 審查實測（`find`/`test -f` 逐條驗證）發現：框架存在**兩套互相矛盾的模板路徑撰寫慣例**——

- ✅ **SDD 時代新增的 `sdd_skills`/`sdd_phase*` 區塊**：一律用框架根相對 `docs_template/sdd/...`，**21 條全部解析成功**。實際 SDD 文件產出走此路徑，runtime 衝擊低。
- ❌ **更早的 `document_responsibilities.*.template_path` 與舊 `dependencies.templates`（pre-SDD 基底配置）**：指向 **SDD 轉型時從未建立的目錄**或裸檔名，**幾乎全斷裂**。

**根因**：SDD 轉型只「往前加」新 `sdd_skills` 接線，**未隨 `docs_template/` 重構回填**舊欄位 → 典型「轉型只前加、未清理舊接線」的技術債。

---

## 2. broken 清單（依類別，~40 條跨 16 agent；證據＝SD 審查 find/test -f 實測）

| 類別 | 樣態 | 代表（檔:line→引用） | 約數 |
|------|------|---------------------|------|
| **A：指向不存在目錄** | `docs_template/<category>/` 整個目錄從未建立（實際只有 core/ scenario_specific/ sdd/ support/） | compliance/security `../docs_template/security/*`（各 7）；devops `../docs_template/devops/*`；technical-writer `../docs_template/documentation/*`；performance `../docs_template/performance/*`；03.pm `../docs_template/prd/*`；sd-mobile/web `../docs_template/srd/*` 變體 | ~50 引用 |
| **B：裸檔名** | 無路徑、全庫不存在同名檔 | 02.ba `stakeholder-validation` 等 3；04.sa `user-story`/`traceability-matrix`；05.sd `technical-architecture`/`api-spec`；06.dev/07.qa 各 2 | ~20 引用 |
| **C：scenario_specific 子類缺檔** | 目錄存在但指定檔名不存在或子目錄缺 | code-analyzer `scenario_specific/analysis/*`（4 檔名不存在）；dev-senior `scenario_specific/refactoring/*`（無此子目錄）；integration `scenario_specific/integration/*`（僅 README）；qa-automation/qa-lead `scenario_specific/testing/*`（僅 README，作者已自註 `# planned`） | ~15 引用 |
| **D：路徑前綴慣例衝突** | `document_responsibilities` 用 `../docs_template/`（一層），同檔 `sdd_skills` 用根相對（零層），同檔兩基準並存 | 全 core/specialized persona agent | 系統性 |

> 註：類別 C 的 `# planned` 自註是**誠實標記**（作者已承認模板未做），但仍為懸空引用。

---

## 3. 三方案（請擇一，或分類別混用）

### 方案一：改指向既有對應模板（重新接線）— **推薦**
- 把 broken path 逐條改指到 `docs_template/sdd/` 或 `docs_template/core/` 下**已存在**的最接近模板（如 PRD→`docs_template/core/prd/...`、SRD→`docs_template/core/srd/...`、ADR→`docs_template/sdd/adr/...`）。
- **優點**：零新增檔、立即消除斷裂、與 `sdd_skills` 既有正確路徑收斂為單一慣例。**成本最低、風險最低**。
- **缺點**：少數確無對應模板者仍需降級為方案三。
- **配套**：同步執行類別 D 修正——全 agent template 路徑統一為**框架根相對**（移除 `../`），並加一條 lint（掃 `template_path`/`templates` 存在性）納入 `scripts/ci-gate.sh`，杜絕再生。

### 方案二：補建缺漏模板
- 為類別 A/B/C 真正缺的模板，在 `docs_template/` 對應位置補建實體模板檔。
- **優點**：agent 宣稱的文檔責任真正可履行、dogfooding 完整。
- **缺點**：**工程量大**（~40+ 模板）、需逐一定義模板內容與 SCG 對應，且部分可能與既有 sdd/ 模板重複。**建議僅對「高頻且確無替代」者採用**。

### 方案三：刪除無效欄位
- 直接刪掉指向不存在目標的 `template_path`/`dependencies.templates` 條目（保留 `sdd_skills` 正確路徑為唯一 SSOT）。
- **優點**：最徹底消除「定義存在但連結斷裂」、檔案最精簡。
- **缺點**：失去「該角色該產哪些文檔」的宣告性資訊（雖多為展示性）。

---

## 4. 建議

**主採方案一（重新接線）+ 類別 D 統一慣例 + ci-gate lint 兜底**；對方案一確無對應模板的殘餘條目，逐條由掌舵者決定走方案二（補建）或方案三（刪除）。此組合成本/風險最低且根除再生。

**待你 signoff 後**，於 v0.18（或下一 Copy-on-Evolve 版）執行，並回填本書狀態為 `decided→fixed@v0.0X`。

---

## 5. 套用結果（fixed@v0.18，2026-06-22）

掌舵者拍板**方案一 + 配套**，已於 v0.18 以確定性腳本套用：

| 動作 | 數量 | 說明 |
|------|------|------|
| **重新接線**（rewire） | 67 | broken path → docs_template/ 下最接近既有模板（如 PRD→core/prd/PRD_Universal、SRD→core/srd/SRD_Module、ADR→sdd/adr/ADR-TEMPLATE、Threat_Model→sdd/testing/STRIDE-THREAT-MODEL、Third_Party_API→sdd/requirements/THIRD-PARTY-API-RESEARCH、CI_CD→scenario_specific/devops/CICD_Pipeline 等） |
| **正規化**（Category D） | 26 | 既有正確路徑移除 `../` 前綴，統一「框架根相對」單一慣例 |
| **刪除**（方案三 fallback） | 9 | 確無對應模板者刪該引用：Operations_Guide、Container_Configuration(×2)、security 之 Privacy_Policy/Data_Processing_Record/DSAR_Process_Guide/Remediation_Plan、refactoring 之 Development_Standards、integration 之 Webhook_Handler_Design |

**配套已落地**：
- 全 agent template 路徑統一**框架根相對**（無 `../`）。
- 新增 `AISDLC_SDD/scripts/agent_template_lint.py`（硬閘，掃最新版 agent template 引用存在性 + 根相對），已接入 `scripts/ci-gate.sh`。

**驗證**：功能性 broken = **0**（3 個註解內示例已忽略）；`ci-gate.sh` 全綠（v0.01:1478 / v0.18:1611 / scripts/tests:56、arch_fitness fail=0、agent_template_lint ✅）。狀態：`decided → fixed@v0.18`。

