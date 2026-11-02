# Issue Scope — 研究議題與檢索邊界模板
# 使用說明：複製第 1 節的 JSON 到 `<研究工作區>/00_research/issue_scope.json` 後填寫（Console 路徑由 Bridge 依使用者輸入確定性渲染，人手流程由人依本模板手寫）

**文件類型**: Issue Scope（`issue_scope.json`；機器可讀 JSON，不是 Markdown 文件）
**契約版本**: `schema_rev` = 1
**存放位置**: `<研究工作區>/00_research/issue_scope.json`（研究工作區不是 `docs/`；位置與目錄結構見 `workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md` 第 10 章）
**作者**: 執行層（Bridge）由使用者輸入渲染；沒有執行層時由人手寫。研究者與規格工程師只讀、不改
**下游**: `research-analyst`（檢索邊界與四個層開關）、`spec-engineer`（`target_scope_hint` 建議值）、審查四角（產品角依第 3 節核對 `topic` 四要素）
**立案**: 掌舵者 2026-11-02 ResearchSOPtoPRD；主控裁決 D-21

> 本檔是 Stage-0 研究到規格的第一份契約：`evidence_items.json` 以 `issue_scope_sha256` 綁定它的版本，
> 所以範圍一變（`scope_rev` 遞增）就是新的一輪檢索，不是改舊檔後假裝沒變。

---

## 1. 契約（JSON）

> 範例的人名、機構與數值皆為虛構，只示範形狀。機器對拍以本節 JSON 區塊為準（區塊前一行的 `r2p:contract` 註解是對拍工具的定位標記，勿刪）。

<!-- r2p:contract=issue_scope -->
```json
{
  "schema_rev": 1,
  "research_id": "6f1d3c2e-8a4b-4c5d-9e7f-0a1b2c3d4e5f",
  "rp_no": "RP-0007",
  "slug": "pdf-export-engine",
  "scope_rev": 1,
  "title": "PDF 匯出渲染方案選型",
  "topic": "在不新增常駐服務、授權限 Apache-2.0 或 MIT 的約束下，替 Console 維護者回答「PDF 匯出該採哪一種渲染方案」；以「候選方案在授權、維護風險、效能邊界三軸皆有 T1 或 T2 證據」驗收；任一候選授權不相容或缺乏可重現的量化結果即否決。",
  "scope": {
    "in_scope": ["可由 Python 3.11 呼叫的 PDF 渲染方案", "近三年仍有維護紀錄的開源專案"],
    "out_of_scope": ["需要付費授權的商用 SDK", "只能在瀏覽器端執行的方案"],
    "tech_stack": "Python 3.11；FastAPI",
    "target_scope_hint": "AISDLC_MODULE"
  },
  "depth_level": "STANDARD",
  "layers": { "academic": true, "industry": true, "oss": true, "community": true },
  "recency_years": 3,
  "applicability_axes": ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"],
  "created_by": "alice",
  "created_at": "2026-11-02T10:00:00+08:00"
}
```

### 1.1 欄位定義

| 欄位 | 型別 | 必填 | 規則 |
|------|------|------|------|
| `schema_rev` | integer | 是 | 固定 `1`；契約發生不相容演進時才加 1 |
| `research_id` | string | 是 | 研究專案的唯一識別：Console 為資料庫的 UUID；沒有 Console 的人手流程填任意唯一字串（例如新產生的 GUID） |
| `rp_no` | string | 是 | 顯示編號：`RP-NNNN`（≥4 位數字，Console 資料庫序列配號）；人手流程寫 `RP-LOCAL` |
| `slug` | string | 是 | `^[a-z0-9][a-z0-9-]{0,29}$`（1～30 字；外環 FSM 鍵 `research-<slug>` 的長度上界，`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.0 節），且須通過 FSM 專案鍵淨化（`sanitize_component`）而不被改寫；建立後不可改 |
| `scope_rev` | integer ≥1 | 是 | 範圍修訂號。遞增＝新的研究範圍修訂：既有證據不刪，標示其所屬 `scope_rev` |
| `title` | string 1～200 字 | 是 | 研究專案名稱 |
| `topic` | string 1～500 字 | 是 | 研究命題，須含第 3 節的四要素 |
| `scope.in_scope` | string[]，≥1 項 | 是 | 檢索邊界內的項目 |
| `scope.out_of_scope` | string[] | 是 | 明確排除的項目（可為空陣列，但寫出來能擋掉最常見的離題檢索） |
| `scope.tech_stack` | string ≤200 字 | 是 | 目標技術棧提示，自由文字且**不入任何指令**；沒有就寫空字串 |
| `scope.target_scope_hint` | enum | 是 | `AISDLC_MODULE`｜`STANDALONE_PROJECT`｜`UNDECIDED`。PRD 草擬時只是「建議值」，分流（Stage-1 之前的路由確認）才是決定 |
| `depth_level` | enum | 是 | `QUICK` 快速｜`STANDARD` 標準｜`DEEP` 深入；來源數、抓取次數與牆鐘預算由執行層依此宣告，不寫進本檔 |
| `layers.academic` | boolean | 是 | 學術與文獻層（`layer` 值 ACADEMIC） |
| `layers.industry` | boolean | 是 | 產業前沿層（INDUSTRY）；Web 工具是否開放由執行層的網域 allowlist 決定，本檔只表達「要不要查」 |
| `layers.oss` | boolean | 是 | 開源層（OSS）：GitHub 等開源專案的健康度、授權與 issue／PR 熱度 |
| `layers.community` | boolean | 是 | 社群層（COMMUNITY）：開發者社群討論；來源只當線索（T3）；四個 `layers.*` 至少一個為 `true` |
| `recency_years` | 1｜2｜3 | 是 | 來源時間窗（來源規格 §3.1「近 1–3 年」）；超出時間窗的來源只在「奠基性」（定義、標準、授權條款）時納入，並於 `f6` 註明年份與理由 |
| `applicability_axes` | string[]，1～6 項 | 是 | 適用性軸，取自 `EVIDENCE-MATRIX-TEMPLATE.md` 第 3 節〈適用性軸登錄表〉的中文標籤；不得自創軸；預設全六軸 |
| `created_by` | string | 是 | 建立者（Console 為 JWT subject；人手為人名或帳號） |
| `created_at` | string | 是 | ISO-8601，**必須帶時區 offset**（例 `+08:00`；naive 時間字串不合法） |

### 1.2 驗證規則（執行層以確定性程式檢查；人手流程由作者逐條自檢）

1. 必填欄位皆在、型別正確、無多餘頂層欄位。
2. `slug` 符合正規式，且 `sanitize_component(slug) == slug`；`rp_no` 為 `RP-NNNN` 或 `RP-LOCAL`；`title` 長度 1～200。
3. `layers` 四個布林至少一個為 `true`；`depth_level`、`recency_years`、`scope.target_scope_hint` 在列舉值內；`scope.tech_stack` 為字串（可為空）。
4. `applicability_axes` 的每一項都在軸登錄表的標籤集合內、不重複、數量 1～6。
5. `created_at` 帶 offset；`topic` 長度 1～500；`scope.in_scope` 至少一項。
6. 檔案編碼 UTF-8、行尾 LF、無 BOM。

---

## 2. 範圍修訂（`scope_rev`）

- 第一次研究 run 完成後，範圍只能「追加修訂」：`scope_rev` 加 1、其餘欄位照新範圍重寫，**舊證據不刪**，在矩陣內以其所屬 `scope_rev` 區分。
- 修訂後必須重跑研究（新的 `issue_scope_sha256`）；PRD 引用的證據若屬舊範圍，須由規格工程師在修訂輪逐條確認仍成立，否則改引新證據。
- `slug`、`research_id`、`rp_no` 不隨修訂改變。

---

## 3. `topic` 的寫法（對應研究方法 S1：問題定義的四要素）

一句話必須同時交代四件事，缺一回頭補，不得開始檢索：

| 要素 | 問自己 | 範例片段（取自上方 JSON） |
|------|--------|--------------------------|
| 約束 | 在哪些邊界內決定？ | 「不新增常駐服務、授權限 Apache-2.0 或 MIT」 |
| 決策者與問題 | 替誰回答什麼問題？ | 「替 Console 維護者回答『PDF 匯出該採哪一種渲染方案』」 |
| 成功判準 | 怎樣算答案夠用？ | 「候選方案在授權、維護風險、效能邊界三軸皆有 T1 或 T2 證據」 |
| 否決條件 | 什麼情況下放棄或改選？ | 「任一候選授權不相容或缺乏可重現的量化結果即否決」 |

句型：「在〈約束〉下，替〈決策者〉回答〈研究問題〉；以〈成功判準〉驗收；〈否決條件〉成立即否決。」

反例（四要素全缺）：「研究 PDF 匯出」。這類命題會讓三層檢索沒有停止條件，審查的產品角會以 `scope_discipline` 項扣分並提 P2 缺陷。

> 四要素檢查屬於審查的 rubric 項目（產品角），不是 schema 驗證：schema 只擋形狀，不擋內容貧乏。

---

## 4. 自檢清單（建立或修訂 `issue_scope.json` 時）

- [ ] `topic` 含四要素，且 1～500 字
- [ ] `scope.in_scope` 與 `scope.out_of_scope` 各自寫出至少一個具體項目（或明確空陣列）
- [ ] 四個層開關與 `depth_level`、`recency_years` 與命題相稱（只問授權條款的題目不需要學術層）
- [ ] `applicability_axes` 只含登錄表內的標籤
- [ ] `created_at` 帶時區
- [ ] 範例中的虛構資料已全部替換

**相關文件**:
- 研究到規格工作流：`workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`
- 證據契約：`docs_template/sdd/requirements/EVIDENCE-MATRIX-TEMPLATE.md`
- 方法論來源（S1）：monorepo `docs/05_development/SelfImproving_Research_Methodology_SOP.md` Part I（本框架不依賴該檔；方法以工作流第 3 章為準）

**最後更新**: 2026-11-02
