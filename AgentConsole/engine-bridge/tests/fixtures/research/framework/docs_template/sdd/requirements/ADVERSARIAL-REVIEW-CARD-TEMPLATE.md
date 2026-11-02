# Adversarial Review Card — 對抗式審查評分卡模板
# 使用說明：四位審查者各依第 6 節寫一份單維度 JSON；執行層（Bridge）依第 2、7 節確定性聚合為 `02_governance/review_card.json`（無執行層時由人依同一公式手算並手寫）

**文件類型**: Adversarial Review Card（審查協定＋兩份 JSON 契約＋rubric 登錄表）
**契約版本**: `schema_rev` = 1
**存放位置**: 審查者輸出 `<研究工作區>/02_governance/reviews/round-<k>/<dimension 小寫>.json`（`architecture`｜`product`｜`qa`｜`security`）；彙整卡 `<研究工作區>/02_governance/review_card.json`
**SDD Gate**: SCG-0（Requirement Spec Gate）的評估器之一：本卡**不取代** SLV 與 Ambiguity Gate，前置否決先行（第 3 節）；PASS 只代表「可交人工核准」，核准是 Gate 0 的人工動作
**作者分工**: 審查者＝`sd-architect`、`pm-po`、`qa-tester`、`security-engineer`（授權欄由 `compliance-officer` 輔）；加權、判定、彙整＝執行層程式，**審查者不給總分、不算權重**
**立案**: 掌舵者 2026-11-02 ResearchSOPtoPRD；主控裁決 D-21（另：D-14 地板與未結 P1、D-24 三輪）

---

## 1. 檔案與流向

| 檔案（相對研究工作區） | 作者 | 說明 |
|----------------------|------|------|
| `02_governance/reviews/round-<k>/architecture.json` | `sd-architect` | 第 6 節契約 |
| `02_governance/reviews/round-<k>/product.json` | `pm-po` | 同上 |
| `02_governance/reviews/round-<k>/qa.json` | `qa-tester` | 同上，另含 `qa_extra.slv_manual_check` |
| `02_governance/reviews/round-<k>/security.json` | `security-engineer`（授權項由 `compliance-officer` 輔） | 同上 |
| `02_governance/review_card.json` | 執行層（跨輪彙整，每輪重新渲染） | 第 7 節契約；歷史評分與缺陷修訂紀錄 |

---

## 2. 參數與判定

### 2.1 參數（產品常數；不提供 UI 修改；每輪記錄自帶快照）

<!-- r2p:contract=review_params -->
```json
{
  "weights": { "ARCHITECTURE": 0.30, "PRODUCT": 0.25, "QA": 0.25, "SECURITY": 0.20 },
  "threshold": 85,
  "dimension_floor": 60
}
```

權重、門檻是來源規格 §3.3 的常數；`dimension_floor`（單維度地板，初值 60，未校準）與「未結 P1 阻擋」是主控裁決 D-14 加上的兩條硬條件。調整任一數字＝修訂本模板與 Console PRD，不是設定。

### 2.2 公式（執行層與人手流程共用；整數運算，不用浮點比較）

設四維整數分為 `A`（ARCHITECTURE）、`P`（PRODUCT）、`Q`（QA）、`S`（SECURITY）：

```
W100           = 30·A + 25·P + 25·Q + 20·S          （整數）
weighted_total = W100 / 100                          （精確到小數 2 位，不四捨五入）
```

一輪通過（`passed = true`）當且僅當**四個條件全部成立**：

| 條件鍵 | 內容 |
|--------|------|
| `precheck_passed` | 第 3 節的前置否決全部通過（任一不過＝本輪不計分，`weighted_total` 為 `null`） |
| `weighted_ge_threshold` | `W100 ≥ 100 × threshold`（即 `W100 ≥ 8500`） |
| `all_dimensions_ge_floor` | `min(A, P, Q, S) ≥ dimension_floor` |
| `no_open_p1` | 本輪各維度提出、狀態為 `OPEN` 的 P1 缺陷數＝0（`WAIVED` 的不計，須人工理由） |

`verdict`：`passed` → `PASS`；否則 FSM 回報已耗盡預算（`gate FAIL` 回傳 `escalated: true`）→ `ESCALATE`；否則 → `REVISE`；任一審查者輸出重試一次後仍不合 schema → `REVIEW_INVALID`（不計輪、不呼叫 FSM、不得判 PASS；它是評估器對「無法評分」的回報，不寫審查輪列，所以彙整卡的 `rounds[].verdict` 沒有這個值，見 7.2）。

**為何用整數與 2 位小數**：權重是 0.05 的倍數，`weighted_total` 本來就最多 2 位小數。若先四捨五入到 1 位再與 85 比較，會出現假通過——例：`A=85, P=85, Q=84, S=86` 時 `W100 = 8495`，`weighted_total = 84.95`，四捨五入成 `85.0` 就「達標」，實際低於門檻。本卡一律以 `W100` 判定、以 `W100/100` 顯示，兩者永遠一致；**不四捨五入到一位再比較**（84.95 不過）。判定公式只住本節（主控裁決 D-42），Console 側的 PRD、API 契約與資料表向本節對齊，不各算各的。

算例（對應第 7 節範例）：第 1 輪 `A=82, P=88, Q=74, S=90` → `W100 = 2460 + 2200 + 1850 + 1800 = 8310` → 83.10，未達 85 → `REVISE`；第 2 輪 `A=88, P=90, Q=84, S=92` → `W100 = 2640 + 2250 + 2100 + 1840 = 8830` → 88.30，四條件皆成立 → `PASS`。

人手流程的手算（PowerShell）：

```powershell
$A = 88; $P = 90; $Q = 84; $S = 92
$W100 = 30*$A + 25*$P + 25*$Q + 20*$S
"W100=$W100 weighted_total=" + ($W100 / 100).ToString('0.00') + " 達門檻=" + ($W100 -ge 8500)
```

### 2.3 輪數（FSM 預算語意）

審查輪數用 FSM 的 `SCG_VALIDATION` 預算（上限 3）：第 1、2 次 `gate FAIL` 退回修訂，**第 3 次 `gate FAIL` 即 ESCALATION**，所以最多 3 輪審查（首審＋2 次自動修訂）。這與來源規格字面「≤3 次修訂＝4 輪」差 1，是有意的：不改 `RETRY_LIMITS`，也不用裸 `transition` 繞過計數。人工「要求修改」同樣算一次 `gate FAIL`，與自動 FAIL 共用 3 次預算。ESCALATION 人工恢復後預算不歸零：至多再得一次審查，FAIL 立即再 ESCALATION、PASS 歸零；全新預算＝換世代鍵（引擎的 `resume-from-escalation` 不動重試計數，只有 `gate PASS` 與 `spec-frozen` 歸零；工作流第 2.5 節）。UI 的剩餘預算＝`max(0, 3 − currentCount)`。

---

## 3. 前置否決（P1；SCG-0 的條件，在 `SCG_VALIDATION` 內、四位審查者開跑之前由程式執行）

任一不過＝本輪直接 `gate FAIL`（計入 FSM 預算）、**不計分**、不開審查者；`precheck.checks` 逐項記錄。這四項是 SCG-0 的既有條件，評分卡不得以高分覆蓋：

| 編號 | 檢查 | 依據 |
|------|------|------|
| `SLV-001` | NFR 物理可行性：回應時間、吞吐量、儲存、並發須 >0；可用性 ≤100%；錯誤率在 0～100% | `.claude/skills/spec-logical-validator/rules/SLV-001.yaml` |
| `SLV-002` | AC 可測試性：每個 AC 有明確前置條件（Given）與可觀察或可量測的期望結果（Then），不得只用模糊詞判定 | `SLV-002.yaml` |
| `SLV-003` | 業務不變量矛盾偵測：`INV-NNN` 兩兩無互斥、範圍矛盾、時序矛盾（PRD 沒有 INV 時為空集合，視為通過） | `SLV-003.yaml` |
| `AMBIGUITY` | 錨點 4（5.2 驗收標準）區段內每個 AC 的模糊度 <0.4，或已有對應 `AMBIGUITY-WAIVER`；計分器＝`tools.fsm_runtime.ambiguity_scorer`，輸入是**該區段的文字**（不是整份 PRD，避免最後一條 AC 吞進後面章節） | `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` 步驟 2a-bis |

> 誠實劃界：SLV 規則檔的 `scan_targets` 是路徑樣式（`docs/01_requirements/FRD-*.md`），研究工作區的 PRD 不在其內，所以機械半段由執行層對 PRD 內容實作同一份 `required_qualifiers` 條文；對非標準寫法可能空轉，因此 QA 角必填 `slv_manual_check` 人讀補位（第 6.3 節），不得把「機械半段沒報錯」當成通過。
>
> 另有**草擬預檢 P0**（結構性，見 `PRD-SPEC-ENGINEERED-TEMPLATE.md` 第 0.2 節）在草稿進入審查**之前**執行：它不過＝不轉 FSM 態、不耗預算；本節的 P1 才計入預算。

---

## 4. rubric 登錄表（四維各 5 項，每項 0～20 分，加總 0～100）

### 4.1 評分錨點（所有項目通用）

| 分數帶 | 意義 |
|--------|------|
| 19～20 | 無缺陷；`note` 引出至少兩個實際核對過的 PRD 錨點 |
| 15～18 | 只有 P3／P4 等級的問題 |
| 10～14 | 有 P2 問題，但不阻擋實作 |
| 5～9 | 有 P1 或多個 P2，需重大修訂 |
| 0～4 | 該項實質缺席（區塊空白、全為佔位） |

> 校準建議（QA 抽查，**不入機械判準**）：某項若被提出 P1 缺陷，該項分數宜 ≤9；被提出 P2，宜 ≤14。機械判準只有第 6.2 節的規則。

### 4.2 各維度項目

**ARCHITECTURE（權重 30%；`sd-architect`）**

| item | 名稱 | 檢核重點 |
|------|------|----------|
| `coupling` | 模組耦合度 | 模組邊界、相依方向、介面可否獨立替換 |
| `dependency_risk` | 第三方依賴維護風險 | 每個外部相依都有維護狀態、授權與替代方案的證據 |
| `performance_bounds` | 效能邊界 | 延遲、吞吐、資源預算有量化且與架構相稱 |
| `data_interface` | 資料模型與介面契約 | JSON Schema、資料表、API 規格完整到可據以實作 |
| `evidence_fit` | 選型與證據一致 | 技術選型的結論由 T1／T2 證據支撐（`[E-NNN]`），不憑空 |

**PRODUCT（權重 25%；`pm-po`）**

| item | 名稱 | 檢核重點 |
|------|------|----------|
| `business_value` | 痛點的商業價值 | 痛點量化、目標用戶明確、值得做 |
| `metric_measurability` | 驗收指標可衡量 | 成功指標與 AC 有數值與量測法 |
| `scope_discipline` | 範圍與 MVP 邊界 | In／Out of scope 清楚、`topic` 四要素在 PRD 中被兌現、無需求蔓延 |
| `prioritization` | 優先級與取捨 | P0／P1／P2、依賴與風險已排序 |
| `evidence_grounding` | 研究依據相稱 | 問題陳述與結論和證據矩陣一致、不誇大、不引用 V1 或 `UNANCHORED` 的列 |

**QA（權重 25%；`qa-tester`）**

| item | 名稱 | 檢核重點 |
|------|------|----------|
| `us_ambiguity` | User Story 模糊地帶 | 每個 US 與 AC 無模糊詞、無未定義名詞 |
| `gwt_automatable` | Given-When-Then 可自動化 | 每個 AC 的 Then 能直接寫成自動化斷言 |
| `edge_case_coverage` | 邊界案例覆蓋 | 邊界條件小節與負向 AC 覆蓋空值、上限、並發與失敗 |
| `traceability` | 追溯完整 | EPIC→F→US→AC 無斷鏈，ID 格式與唯一性合規 |
| `nfr_testability` | NFR 可測 | 每條 NFR 有可量測門檻與量測法（SLV-001 精神） |

**SECURITY（權重 20%；`security-engineer`，授權項由 `compliance-officer` 輔）**

| item | 名稱 | 檢核重點 |
|------|------|----------|
| `license_conflict` | 授權衝突 | 外部相依與目標授權相容；矩陣的「授權待查」列逐項處置 |
| `secret_handling` | 機密安全 | 機密不入檔、不入日誌、不入版控；脫敏規則明確 |
| `injection_risk` | 注入風險 | 輸入驗證與外部內容視為資料不是指令 |
| `authn_authz` | 驗證與授權設計 | 角色與權限、核准人身分如何驗證 |
| `external_content_safety` | 外部內容與供應鏈 | 抓取白名單、SSRF、第三方內容再散布與授權風險 |

### 4.3 機器可讀登錄表（Bridge 對拍用；`agent_file` 必須指向存在的檔）

<!-- r2p:contract=rubric_registry -->
```json
{
  "ARCHITECTURE": {"agent_id": "sd-architect", "agent_file": "agent/core/05.sd-architect-zh.yaml", "assist_agent_id": null, "assist_agent_file": null, "weight": 0.30, "defect_prefix": "ARCH", "items": ["coupling", "dependency_risk", "performance_bounds", "data_interface", "evidence_fit"]},
  "PRODUCT": {"agent_id": "pm-po", "agent_file": "agent/core/03.pm-po-agent-zh.yaml", "assist_agent_id": null, "assist_agent_file": null, "weight": 0.25, "defect_prefix": "PROD", "items": ["business_value", "metric_measurability", "scope_discipline", "prioritization", "evidence_grounding"]},
  "QA": {"agent_id": "qa-tester", "agent_file": "agent/core/07.qa-tester-zh.yaml", "assist_agent_id": null, "assist_agent_file": null, "weight": 0.25, "defect_prefix": "QA", "items": ["us_ambiguity", "gwt_automatable", "edge_case_coverage", "traceability", "nfr_testability"]},
  "SECURITY": {"agent_id": "security-engineer", "agent_file": "agent/specialized/security-engineer-zh.yaml", "assist_agent_id": "compliance-officer", "assist_agent_file": "agent/specialized/compliance-officer-zh.yaml", "weight": 0.20, "defect_prefix": "SEC", "items": ["license_conflict", "secret_handling", "injection_risk", "authn_authz", "external_content_safety"]}
}
```

---

## 5. 缺陷

### 5.1 嚴重度

| 級 | 定義 | 範例 |
|----|------|------|
| P1 | 阻斷：核准後會導致無法實作或違規 | AC 不可測（無可觀察斷言）、授權衝突、憑空引用（`[E-NNN]` 不存在、引 V1／`UNANCHORED`／`CANDIDATE`）、機密入檔、NFR 物理不可行 |
| P2 | 重大：需人工繞過，或使 AC 無法自動化 | 缺邊界條件、相依無維護證據、追溯斷鏈 |
| P3 | 改善：文字、命名、可讀性 | 標題不一致、術語未定義 |
| P4 | 建議：理論性或偏好 | 圖表風格 |

只有 P1 會阻擋通過；P2～P4 透過 rubric 分數反映。

**本表是缺陷嚴重度 P1～P4 的單一真相源**：根層 PRD（`docs/01_requirements/ResearchToPRD_PRD.md` §5.1.4）與資料庫的 `severity` 欄引用本表，不另立定義。缺陷 id 一律 `D-<輪>-<序>`（`<輪>` 為審查輪序號、`<序>` 為該輪的三位流水號，例：`D-1-001`）；審查輪預算＝FSM `SCG_VALIDATION` 的 3 次（首審加 2 次自動修訂，第 3 次 `gate FAIL` 即 ESCALATION，第 2.3 節）。

### 5.2 `code` 與 `prd_anchor` 文法

- `code`：`^(ARCH|PROD|QA|SEC)-[A-Z][A-Z0-9_]{1,23}-[0-9]{2}$`，前綴對應維度、中間段＝該維度某 rubric 項目 id 的大寫（例：`ARCH-DEPENDENCY_RISK-01`、`QA-GWT_AUTOMATABLE-01`），末兩位為同一項目下的流水號。
- `prd_anchor`：`§<章>[.<節>][/<ID>]`，章為家規 14 章之一，`<ID>` 為 `F-`／`US-`／`AC-`／`NFR-`／`INV-`／`EPIC-` 開頭的 PRD 內 ID（例：`§5.2/AC-003-2`、`§9.4`、`§6/NFR-001`）。找不到對應 ID 時只寫到章或節。

### 5.3 狀態（彙整卡 `defects[].status`；審查者不改舊缺陷的狀態）

| 狀態 | 意義 |
|------|------|
| `OPEN` | 本輪提出、尚未解決 |
| `FIXED` | 之後某輪未再提出同 `code`＋同 `prd_anchor`（解決於該輪審查的 PRD 版本，記 `resolved_in`） |
| `REGRESSED` | 曾為 `FIXED`、後來又被提出；合法出口只有 `FIXED`（之後某輪再度不被提出）——不得直接轉為 `OPEN`、`WAIVED` 或 `SUPERSEDED` |
| `WAIVED` | 人工豁免；必須有 `waiver.by`、`waiver.reason`、`waiver.at` |
| `SUPERSEDED` | 其 `prd_anchor` 所指的內容已被移除或重寫，缺陷已無對象 |

狀態轉移由執行層依後續輪次的缺陷清單**確定性**判定；`WAIVED` 只能由人工動作產生。合法轉移只有下列（資料庫以觸發器守住，其餘一律拒）：`OPEN`→`FIXED`／`WAIVED`／`SUPERSEDED`；`FIXED`→`REGRESSED`；`REGRESSED`→`FIXED`。`WAIVED` 與 `SUPERSEDED` 是終態。

---

## 6. 單維度審查輸出契約（`reviews/round-<k>/<dimension>.json`）

### 6.1 範例一：ARCHITECTURE（虛構內容）

<!-- r2p:contract=review_dimension -->
```json
{
  "schema_rev": 1,
  "round": 1,
  "dimension": "ARCHITECTURE",
  "agent_id": "sd-architect",
  "prd_sha256": "0000000000000000000000000000000000000000000000000000000000000002",
  "rubric": [
    {"item": "coupling", "score": 17, "max": 20, "note": "模組邊界清楚，§9.1 與 §9.3 的相依方向一致"},
    {"item": "dependency_risk", "score": 15, "max": 20, "note": "§9.4 的兩個相依缺維護者數量證據"},
    {"item": "performance_bounds", "score": 16, "max": 20, "note": "NFR-001 有 P99 與資源預算，但未說明量測條件"},
    {"item": "data_interface", "score": 18, "max": 20, "note": "§9.2 與 §9.3 完整，§9.3/API-002 的錯誤碼已列"},
    {"item": "evidence_fit", "score": 16, "max": 20, "note": "§1.2 的選型結論引用 E-001、E-002，E-003 的自述數字未加註"}
  ],
  "score": 82,
  "summary": "整體結構清楚；主要缺口是相依的維護狀態與效能量測條件",
  "defects": [
    {"code": "ARCH-DEPENDENCY_RISK-01", "severity": "P2", "prd_anchor": "§9.4", "description": "外部相依表未載每個相依的維護者人數與最近提交，無法評估停更風險", "suggestion": "於 §9.4 補維護狀態欄，並引用對應證據列", "evidence_refs": ["E-002"]}
  ]
}
```

### 6.2 欄位與驗證規則（執行層以確定性程式檢查；不合＝該審查者重試一次，仍不合＝本次評審 `REVIEW_INVALID`，不寫審查輪列，見 7.2）

| 欄位 | 型別 | 規則 |
|------|------|------|
| `schema_rev` | integer | 固定 `1` |
| `round` | integer ≥1 | 等於任務書指定的輪次 |
| `dimension` | enum | `ARCHITECTURE`｜`PRODUCT`｜`QA`｜`SECURITY`；檔名小寫須對應 |
| `agent_id` | string | 必須等於 4.3 登錄表該維度的 `agent_id` |
| `prd_sha256` | string | 64 位小寫 hex；**由任務書提供，原樣抄寫**（審查者沒有雜湊工具）；演算法＝換行正規化後 UTF-8 的 SHA-256（與 `spec-frozen --digest` 同，不含 `sha256:` 前綴） |
| `rubric` | object[5] | `item` 集合恰等於 4.3 該維度的 `items`；每項 `max=20`、`score` 為 0～20 整數、`note` 非空且 ≤300 字元；`score`≥18 的項目，`note` 必須含至少一個 PRD 錨點（含 `§`） |
| `score` | integer 0～100 | **必須等於 `rubric` 五項 `score` 之和**；不等＝無效 |
| `summary` | string | 非空、≤600 字元 |
| `defects[]` | object[] | `code`（5.2 文法，前綴與項目屬該維度）、`severity`（P1～P4）、`prd_anchor`（5.2 文法）、`description`（非空）、`suggestion`（非空）、`evidence_refs`（`E-NNN` 陣列，可空，每個必須存在於證據矩陣） |
| `qa_extra` | object | **只有** `QA` 維度必含且只含 `slv_manual_check`；其他維度不得出現 |

另：所有文字欄位不得含換行；JSON 為 UTF-8、LF、無 BOM；整份檔案只含一個 JSON 物件，不得有前後說明文字。

### 6.3 範例二：QA 與 `slv_manual_check`

增量專案與非標準寫法下，SLV 與模糊度計分的機械半段可能空轉，所以 QA 角必須人讀補位：逐條讀 AC，回報 AC 總數與其中「真的能寫成自動化斷言」的條數。

<!-- r2p:contract=review_dimension_qa -->
```json
{
  "schema_rev": 1,
  "round": 1,
  "dimension": "QA",
  "agent_id": "qa-tester",
  "prd_sha256": "0000000000000000000000000000000000000000000000000000000000000002",
  "rubric": [
    {"item": "us_ambiguity", "score": 15, "max": 20, "note": "US-002 的『適量』未定義，其餘 US 明確"},
    {"item": "gwt_automatable", "score": 14, "max": 20, "note": "AC-003-2 的 Then 沒有可觀察狀態"},
    {"item": "edge_case_coverage", "score": 14, "max": 20, "note": "F-001 的邊界條件缺空值與並發"},
    {"item": "traceability", "score": 16, "max": 20, "note": "EPIC→F→US→AC 完整，ID 格式合規"},
    {"item": "nfr_testability", "score": 15, "max": 20, "note": "NFR-002 缺量測法"}
  ],
  "score": 74,
  "summary": "AC 多數可自動化；缺口在 AC-003-2 的可觀察斷言與邊界覆蓋",
  "defects": [
    {"code": "QA-GWT_AUTOMATABLE-01", "severity": "P2", "prd_anchor": "§5.2/AC-003-2", "description": "Then 子句沒有可量測的狀態變更，無法寫成自動化斷言", "suggestion": "補上預期的狀態碼與欄位值", "evidence_refs": []}
  ],
  "qa_extra": {
    "slv_manual_check": {"ac_total": 18, "ac_testable": 16, "notes": "逐條人讀；AC-003-2 與 AC-005-1 的 Then 不可觀察"}
  }
}
```

`slv_manual_check` 規則：`ac_total` 必須等於執行層對 PRD 5.2 節 `#### AC-` 標題的機械計數（人讀不得與機械計數矛盾）；`0 ≤ ac_testable ≤ ac_total`；`notes` 非空。`ac_testable < ac_total` 而 `defects` 沒有對應的 P1 或 P2 缺陷，視為內部矛盾（QA 角須補缺陷或修正條數）。

---

## 7. 彙整卡 `review_card.json` 契約（執行層寫；跨輪累積）

### 7.1 範例（兩輪：第 1 輪 REVISE，第 2 輪 PASS；虛構內容）

<!-- r2p:contract=review_card -->
```json
{
  "schema_rev": 1,
  "research_id": "6f1d3c2e-8a4b-4c5d-9e7f-0a1b2c3d4e5f",
  "rounds": [
    {
      "round": 1,
      "prd_version": "v0.1.0-draft",
      "prd_version_no": 1,
      "prd_sha256": "0000000000000000000000000000000000000000000000000000000000000002",
      "params": { "weights": { "ARCHITECTURE": 0.30, "PRODUCT": 0.25, "QA": 0.25, "SECURITY": 0.20 }, "threshold": 85, "dimension_floor": 60 },
      "precheck": { "passed": true, "checks": [
        {"id": "SLV-001", "passed": true, "detail": ""},
        {"id": "SLV-002", "passed": true, "detail": ""},
        {"id": "SLV-003", "passed": true, "detail": ""},
        {"id": "AMBIGUITY", "passed": true, "detail": "最大 AC 模糊度 0.31，低於 0.4"}
      ]},
      "reviewers": [
        {"dimension": "ARCHITECTURE", "weight": 0.30, "agent": "05.sd-architect-zh", "agent_id": "sd-architect", "agent_yaml_sha256": "1111111111111111111111111111111111111111111111111111111111111111", "assist_agent_id": null, "assist_agent_yaml_sha256": null, "persona_sha256": "2222222222222222222222222222222222222222222222222222222222222222", "score": 82, "raw_file": "02_governance/reviews/round-1/architecture.json", "raw_sha256": "3333333333333333333333333333333333333333333333333333333333333333"},
        {"dimension": "PRODUCT", "weight": 0.25, "agent": "03.pm-po-agent-zh", "agent_id": "pm-po", "agent_yaml_sha256": "4444444444444444444444444444444444444444444444444444444444444444", "assist_agent_id": null, "assist_agent_yaml_sha256": null, "persona_sha256": "5555555555555555555555555555555555555555555555555555555555555555", "score": 88, "raw_file": "02_governance/reviews/round-1/product.json", "raw_sha256": "6666666666666666666666666666666666666666666666666666666666666666"},
        {"dimension": "QA", "weight": 0.25, "agent": "07.qa-tester-zh", "agent_id": "qa-tester", "agent_yaml_sha256": "7777777777777777777777777777777777777777777777777777777777777777", "assist_agent_id": null, "assist_agent_yaml_sha256": null, "persona_sha256": "8888888888888888888888888888888888888888888888888888888888888888", "score": 74, "raw_file": "02_governance/reviews/round-1/qa.json", "raw_sha256": "9999999999999999999999999999999999999999999999999999999999999999"},
        {"dimension": "SECURITY", "weight": 0.20, "agent": "security-engineer-zh", "agent_id": "security-engineer", "agent_yaml_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "assist_agent_id": "compliance-officer", "assist_agent_yaml_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "persona_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "score": 90, "raw_file": "02_governance/reviews/round-1/security.json", "raw_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"}
      ],
      "weighted_total": 83.10,
      "min_dimension_score": 74,
      "conditions": { "precheck_passed": true, "weighted_ge_threshold": false, "all_dimensions_ge_floor": true, "no_open_p1": true },
      "open_p1_count": 0,
      "passed": false,
      "verdict": "REVISE",
      "defects": [
        {"id": "D-1-001", "dimension": "QA", "severity": "P2", "code": "QA-GWT_AUTOMATABLE-01", "anchor": "§5.2/AC-003-2", "finding": "Then 子句沒有可量測的狀態變更，無法寫成自動化斷言", "suggestion": "補上預期的狀態碼與欄位值", "evidence_refs": [], "status": "FIXED", "resolved_in": "v0.2.0-draft", "waiver": null},
        {"id": "D-1-002", "dimension": "ARCHITECTURE", "severity": "P2", "code": "ARCH-DEPENDENCY_RISK-01", "anchor": "§9.4", "finding": "外部相依表未載每個相依的維護者人數與最近提交，無法評估停更風險", "suggestion": "於 §9.4 補維護狀態欄，並引用對應證據列", "evidence_refs": ["E-002"], "status": "FIXED", "resolved_in": "v0.2.0-draft", "waiver": null}
      ],
      "fsm": { "gate_result": "FAIL", "retry_count": 1 },
      "started_at": "2026-11-02T10:30:00+08:00",
      "ended_at": "2026-11-02T10:41:00+08:00"
    },
    {
      "round": 2,
      "prd_version": "v0.2.0-draft",
      "prd_version_no": 2,
      "prd_sha256": "0000000000000000000000000000000000000000000000000000000000000003",
      "params": { "weights": { "ARCHITECTURE": 0.30, "PRODUCT": 0.25, "QA": 0.25, "SECURITY": 0.20 }, "threshold": 85, "dimension_floor": 60 },
      "precheck": { "passed": true, "checks": [
        {"id": "SLV-001", "passed": true, "detail": ""},
        {"id": "SLV-002", "passed": true, "detail": ""},
        {"id": "SLV-003", "passed": true, "detail": ""},
        {"id": "AMBIGUITY", "passed": true, "detail": "最大 AC 模糊度 0.22，低於 0.4"}
      ]},
      "reviewers": [
        {"dimension": "ARCHITECTURE", "weight": 0.30, "agent": "05.sd-architect-zh", "agent_id": "sd-architect", "agent_yaml_sha256": "1111111111111111111111111111111111111111111111111111111111111111", "assist_agent_id": null, "assist_agent_yaml_sha256": null, "persona_sha256": "2222222222222222222222222222222222222222222222222222222222222222", "score": 88, "raw_file": "02_governance/reviews/round-2/architecture.json", "raw_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"},
        {"dimension": "PRODUCT", "weight": 0.25, "agent": "03.pm-po-agent-zh", "agent_id": "pm-po", "agent_yaml_sha256": "4444444444444444444444444444444444444444444444444444444444444444", "assist_agent_id": null, "assist_agent_yaml_sha256": null, "persona_sha256": "5555555555555555555555555555555555555555555555555555555555555555", "score": 90, "raw_file": "02_governance/reviews/round-2/product.json", "raw_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"},
        {"dimension": "QA", "weight": 0.25, "agent": "07.qa-tester-zh", "agent_id": "qa-tester", "agent_yaml_sha256": "7777777777777777777777777777777777777777777777777777777777777777", "assist_agent_id": null, "assist_agent_yaml_sha256": null, "persona_sha256": "8888888888888888888888888888888888888888888888888888888888888888", "score": 84, "raw_file": "02_governance/reviews/round-2/qa.json", "raw_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"},
        {"dimension": "SECURITY", "weight": 0.20, "agent": "security-engineer-zh", "agent_id": "security-engineer", "agent_yaml_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "assist_agent_id": "compliance-officer", "assist_agent_yaml_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "persona_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "score": 92, "raw_file": "02_governance/reviews/round-2/security.json", "raw_sha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"}
      ],
      "weighted_total": 88.30,
      "min_dimension_score": 84,
      "conditions": { "precheck_passed": true, "weighted_ge_threshold": true, "all_dimensions_ge_floor": true, "no_open_p1": true },
      "open_p1_count": 0,
      "passed": true,
      "verdict": "PASS",
      "defects": [
        {"id": "D-2-001", "dimension": "PRODUCT", "severity": "P3", "code": "PROD-PRIORITIZATION-01", "anchor": "§3.1", "finding": "MVP 清單的優先級欄混用 P0 與 Must", "suggestion": "統一為 P0／P1／P2", "evidence_refs": [], "status": "OPEN", "resolved_in": null, "waiver": null}
      ],
      "fsm": { "gate_result": "PASS", "retry_count": 0 },
      "started_at": "2026-11-02T11:05:00+08:00",
      "ended_at": "2026-11-02T11:15:00+08:00"
    }
  ],
  "retry_count": 0,
  "final_verdict": "PASS"
}
```

### 7.2 欄位定義

**頂層**：`schema_rev`（固定 1）、`research_id`、`rounds[]`（只增不改；缺陷 `status` 例外，依 5.3 隨後續輪次更新並重新渲染）、`retry_count`（FSM `SCG_VALIDATION` 現計數，取自 `gate`／`show` 的回傳，**不自建第二套計數**）、`final_verdict`（`IN_PROGRESS`｜`PASS`｜`ESCALATED`）。

**輪（`rounds[]`）**：

| 欄位 | 說明 |
|------|------|
| `round` | 審查輪序號（資料庫審查輪表為準，從 1 起；`REVIEW_INVALID` 不佔序號：執行層只記 stage run（exit_reason=review_invalid）與事件，不寫審查輪列） |
| `prd_version`、`prd_version_no`、`prd_sha256` | 被審的 PRD 版本與雜湊：`prd_version`＝semver 字串（例 `v0.2.0-draft`）、`prd_version_no`＝整數（從 1 起，對映資料庫 `version_no`，是正式鍵）、`prd_sha256`＝內容雜湊；三者描述同一份 PRD（見 7.3 不變量 4）。審查結果只對這個雜湊有效；人工儲存新版本後舊結果過期 |
| `params` | 本輪參數快照（2.1 的三個鍵） |
| `precheck` | `{passed, checks[{id, passed, detail}]}`；`checks` 的 `id` 取自第 3 節 |
| `reviewers[]` | 四個維度各一筆：`dimension`、`weight`、`agent`（agent YAML 檔名去 `.yaml`）、`agent_id`、`agent_yaml_sha256`（審查者 agent 檔案雜湊）、`assist_agent_id`／`assist_agent_yaml_sha256`（只有 SECURITY 為 `compliance-officer`，其餘 `null`）、`persona_sha256`（編譯後任務書人設檔雜湊）、`score`、`raw_file`、`raw_sha256` |
| `weighted_total` | 2.2 的 `W100/100`；前置否決不過時為 `null`（`reviewers` 可為空陣列） |
| `min_dimension_score` | 四維整數分的最小值（地板判定的輸入）；前置否決不過時為 `null` |
| `conditions` | 2.2 的四個條件鍵 |
| `open_p1_count` | 本輪 `OPEN` 的 P1 缺陷數 |
| `passed`、`verdict` | `passed` 為四條件之且；`verdict`＝`PASS`｜`REVISE`｜`ESCALATE`（`REVIEW_INVALID` 不寫審查輪列，不在此值域，見 `round` 列與 2.2） |
| `defects[]` | `id`（`D-<輪>-<NNN>`）、`dimension`、`severity`、`code`、`anchor`（＝審查者的 `prd_anchor`）、`finding`（＝審查者的 `description`）、`suggestion`、`evidence_refs`、`status`、`resolved_in`（`FIXED` 時為被審 PRD 版本，否則 `null`）、`waiver`（`WAIVED` 時 `{by, reason, at}`，否則 `null`） |
| `fsm` | `{gate_result, retry_count}`：本輪呼叫 `gate` 的結果與回傳的重試計數（`gate_result` 為 `PASS` 或 `FAIL`）；未呼叫 `gate` 的輪——POST_HUMAN 再審通過（定義見 7.3）——兩者皆為 `null` |
| `started_at`、`ended_at` | ISO-8601 帶 offset |

**單維度 JSON 到彙整卡的對映**：`score`→`reviewers[].score`；`defects[].description`→`finding`、`prd_anchor`→`anchor`；`defects[].code`、`severity`、`suggestion`、`evidence_refs` 原樣；`id` 與 `status` 由執行層賦予（初始 `OPEN`）。

### 7.3 不變量

1. `weighted_total` 與 `reviewers[].score` 必須滿足 2.2 公式；`min_dimension_score` 等於四維最低分；`passed` 必須等於 `conditions` 四值之且；`verdict=PASS` ⇔ `passed=true`；凡有呼叫 `gate` 的輪：`fsm.gate_result=PASS` ⇔ `passed=true`；POST_HUMAN 再審通過的輪 `fsm.gate_result=null`。POST_HUMAN＝人工退回（`gate SCG_VALIDATION FAIL`，態維持 HUMAN_PENDING）之後的重新審查：現態已是 HUMAN_PENDING，不呼叫 `gate PASS`（工作流第 8 章 Bridge 守則），所以只有「通過」的輪沒有 `gate` 回傳——該輪 `passed=true`、`fsm.retry_count` 亦為 `null`；再審**未通過**的輪仍呼叫 `gate SCG_VALIDATION FAIL`，照前一個子句。
2. `PASS` 的輪才允許進入核准；核准時的 PRD 雜湊必須等於該輪 `prd_sha256`（Gate 0 前置條件）。
3. 檔案與資料庫審查輪表逐欄相等；漂移只顯示、不自動修正。
4. `prd_version_no`、`prd_version`、`prd_sha256` 描述同一份 PRD：同一個 `prd_version_no` 只對應一組 `prd_version` 與 `prd_sha256`；輪與輪之間 `prd_version_no` 不遞減（再審沿用同一版時相等，人工儲存新版本後變大）。

---

## 8. 任務書契約（執行層組裝審查者與修訂者的任務書時遵守）

**審查者任務書必含**：PRD 檔路徑、`prd_sha256`（供原樣抄寫）、輪次、證據矩陣與 `issue_scope.json` 路徑、輸出檔路徑（只准寫該維度檔）、本模板第 4、5、6 節、`depth` 與預算宣告。
**審查者任務書不得含**：權重、門檻、地板、其他維度的分數或缺陷、前幾輪的分數、FSM 狀態、「通過條件」說明。審查者看到這些就會對著分數寫作（反 Goodhart）。
**修訂者（`spec-engineer`）任務書必含**：最新 PRD、上一輪缺陷清單（`id`、`severity`、`anchor`、`finding`、`suggestion`）、輸出檔路徑、`PRD-SPEC-ENGINEERED-TEMPLATE.md` 第 13.4 節規則。**不得含**任何分數、加權總分、權重與門檻。

審查者行為準則：

1. 只審、不改：不得修改 PRD、證據矩陣或其他審查者的檔案。
2. 每個 rubric 項目都要寫 `note`；**零發現不是滿分**：給 ≥18 分必須指出實際核對過的錨點。
3. 不自評、不替別的維度打分、不猜測權重。
4. 引用證據只認矩陣內存在、V2 以上、非 `UNANCHORED`、非 `CANDIDATE` 的列。
5. 輸出整份檔案只含一個 JSON 物件。

> 已知邊界：四位審查者同為 AI、同工作區可互讀檔案，**不滿足** R-9.20.3 型的獨立性。補償控制＝每位審查者一個獨立 run（`maintain_context:false`）、聚合與判定由程式、Gate 0 由人。不宣稱已滿足。

---

## 9. 自檢清單（審查者交卷前；QA 驗收本卡時逐條勾）

- [ ] `rubric` 恰五項、`item` 與登錄表一致、每項 `max=20`、`score` 為整數
- [ ] `score` 等於五項加總
- [ ] 每個 ≥18 分的 `note` 含 `§` 錨點
- [ ] 每個缺陷的 `code` 前綴、項目段與 `severity`、`prd_anchor` 合文法
- [ ] `evidence_refs` 的每個 `E-NNN` 都在矩陣內
- [ ] （QA）`slv_manual_check.ac_total` 等於 PRD 5.2 節 AC 標題數
- [ ] 檔案只含單一 JSON 物件，UTF-8、LF、無 BOM
- [ ] 沒有出現權重、門檻、總分或任何通過與否的判斷

**相關文件**:
- 研究到規格工作流：`workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`（第 6、7 章）
- SE-PRD 模板：`docs_template/sdd/requirements/PRD-SPEC-ENGINEERED-TEMPLATE.md`
- 證據契約：`docs_template/sdd/requirements/EVIDENCE-MATRIX-TEMPLATE.md`
- 閘門條文：`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`（SCG-0）
- 憑證紀律：`agent/EVIDENCE_DISCIPLINE.md`

**最後更新**: 2026-11-02
