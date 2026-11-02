# SDD Research-to-PRD Workflow
# 研究到規格工作流程（Stage-0：研究 → 證據 → PRD → 四方審查 → Gate 0）

**版本**: v1.0
**建立日期**: 2026-11-02
**最後更新**: 2026-11-02
**工作流程類型**: 前置工作流（Stage-0；SCG-0 之前的外環）
**分類**: ResearchSOPtoPRD 整合的「方法層」；立案：掌舵者 2026-11-02 ResearchSOPtoPRD；主控裁決 D-21（方法層進框架、執行層在 Console／Bridge）
**配套 Agent**: `agent/specialized/research-analyst-zh.yaml`（證據端）、`agent/specialized/spec-engineer-zh.yaml`（規格端）；審查沿用 `agent/core/05.sd-architect-zh.yaml`、`agent/core/03.pm-po-agent-zh.yaml`、`agent/core/07.qa-tester-zh.yaml`、`agent/specialized/security-engineer-zh.yaml`（授權欄由 `agent/specialized/compliance-officer-zh.yaml` 輔）
**配套模板**: `docs_template/sdd/requirements/ISSUE-SCOPE-TEMPLATE.md`、`EVIDENCE-MATRIX-TEMPLATE.md`、`PRD-SPEC-ENGINEERED-TEMPLATE.md`、`ADVERSARIAL-REVIEW-CARD-TEMPLATE.md`
**配套規則**: 無新增規則；沿用 R-9.1（重試預算）、R-9.4（凍結）、R-9.5 與 Rule 8（人工閘、ESCALATION 只有人能解）。理由見 `docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`
**上位需求**: 根層 `docs/01_requirements/ResearchToPRD_PRD.md`（唯一 PRD；FR-R2P-01～23、NFR-R2P-01～13；章節對照見第 14 章）。框架側沒有自己的 PRD

---

## 0. 目的與邊界

### 0.1 目的

在 SDD 的 SCG-0（需求凍結）**之前**，提供一條可稽核的方法：把一個研究議題變成**有證據、可測、經四方對抗審查、由人核准**的 PRD。產出的 PRD 與證據矩陣在 Gate 0 凍結，之後才分流進既有的 SDD 內環（TCS → 實作 → 審查 → 交付）。

整條外環是**同一條 FSM 鍵**（`research-<slug>`）從 AGENT_LOAD 走到 SPEC_FROZEN，沒有新增任何狀態或邊（第 2 章逐邊證明）。

### 0.2 雙環漏斗

```
議題（issue_scope.json）
   │ ① 三層檢索與證據抽取（research-analyst）
   ▼
證據（evidence_items.json → 證據矩陣 evidence_matrix.md）
   │ ② 起草（spec-engineer）→ 草擬預檢 P0
   ▼
SE-PRD 草稿 ── ③ 前置否決（SLV／Ambiguity）→ 四方審查（加權、地板、無未結 P1）──┐
   ▲                                                                           │ 未過：缺陷清單 → 修訂
   └───────────────────────────────────────────────────────────────────────────┘ （最多 3 輪審查）
   │ 通過（只代表「可交人工核准」）
   ▼
④ Gate 0：人工核准（spec-frozen --stage Gate-0）＝外環終點
   │ ⑤ 分流：軌道 A 併入既有模組／軌道 B 獨立新專案 ＝ 建內環鍵＋Stage-1 基線採納
   ▼
內環：既有 SDD 全流程（Stage-2 TCS → 實作 → SCG-4 → SCG-5 → RELEASE）
```

### 0.3 方法層與執行層（D-21）

| 層 | 內容 | 住哪 |
|----|------|------|
| **方法層（本框架）** | 本工作流、兩支 agent、四份模板（含 JSON 契約）、SCG-0 評分協定、SCR 路徑；全部是 Markdown 與 YAML | `AISDLC_SDD/AISDLC_SDD_v<LATEST>/`（只准 LATEST 原地改） |
| **執行層（Console／Bridge）** | 使用者介面、資料庫、stage run 編排、第三方抓取、確定性驗證與評分聚合、FSM 驅動、SSE | `AgentConsole/`（Bridge 是 Python 服務；框架內**沒有**網路或資料庫程式） |

分工的理由：agent 人設與閘門語意的唯一真相源在框架；網路客戶端與資料庫寫入器需要 Bridge 的外呼 allowlist、SSRF 防線與連線池，不屬於 FSM 治理 runtime。**沒有執行層時，方法仍可由人手流程執行**（第 13 章），只是少了機器驗證器（第 11 章誠實劃界）。

### 0.4 不做什麼

- 不寫程式、不取代 SCG-1～SCG-6；不新增 FSM 狀態或邊，不改 `_HAPPY_PATH`、`formal/`、`governance/rules/R-*.yaml`、skills。
- 不含網路或資料庫程式；Console 專屬的 UI、資料表、API 形狀不在本文（見第 12 章指標）。
- 不替審查者定分數、不把審查分數當成果指標（反 Goodhart，第 6 章）。

### 0.5 名稱對照（避免混用）

| 名稱 | 指什麼 |
|------|--------|
| 本工作流的 **Stage-0** | 研究到規格這段外環前置（本文件） |
| FSM stage 名 **`Gate-0`**（`Gate-0-SCR<n>`） | 外環鍵的凍結階段名；`spec-frozen --stage Gate-0`。Gate 0＝SCG-0 人類確認點（SDD_SPEC_FIRST_GATE 流程步驟 4～5）在本工作流的名稱 |
| `Stage-1`、`Stage-2` | 內環鍵的 FSM stage 名：Stage-1＝已發佈 PRD 的基線採納；Stage-2＝TCS 增量規格 |
| Greenfield 流程總覽的「Stage 0: Spec Foundation」 | 一般場景內環的第 0 步（建 ADR 目錄、RTM 骨架）；與本工作流的 Stage-0 是兩件事 |
| 外環鍵／內環鍵 | `research-<slug>`／`<sub>-<slug>`（第 2.1 節） |

---

## 1. 角色與載入

| 角色 | 檔案 | 階段 | 職責 |
|------|------|------|------|
| 研究者 `research-analyst`（Rae） | `agent/specialized/research-analyst-zh.yaml` | RESEARCH；增補 | 三層檢索、七欄抽取、反證、誠實劃界，產出 `evidence_items.json` |
| 規格工程師 `spec-engineer`（SpecEng） | `agent/specialized/spec-engineer-zh.yaml` | DRAFT、REVISE | 起草與修訂 SE-PRD、`adr_draft.md`；只回應缺陷，不自審 |
| 架構審查 `sd-architect`（ARCHITECTURE，權重 30%） | `agent/core/05.sd-architect-zh.yaml` | REVIEW-k | 耦合、相依風險、效能邊界、資料與介面契約、選型與證據一致 |
| 產品審查 `pm-po`（PRODUCT，25%） | `agent/core/03.pm-po-agent-zh.yaml` | REVIEW-k | 商業價值、指標可衡量、範圍紀律、優先級、研究依據相稱 |
| 品質審查 `qa-tester`（QA，25%） | `agent/core/07.qa-tester-zh.yaml` | REVIEW-k | 模糊地帶、Given-When-Then 可自動化、邊界覆蓋、追溯、NFR 可測；必填 `slv_manual_check` |
| 資安審查 `security-engineer`（SECURITY，20%） | `agent/specialized/security-engineer-zh.yaml`（授權欄由 `agent/specialized/compliance-officer-zh.yaml` 輔） | REVIEW-k | 授權衝突、機密、注入、驗證授權、外部內容與供應鏈 |
| 人（Gate 0 核准者） | — | Gate 0 之後的一切人工閘 | 核准、要求修改、分流確認；`--approver` 必須是真人 |

載入規則：

1. 兩支新 agent 登記在 `AISDLC_SDD_INIT.md` 的 `auto_load_config.system_wide_supporting_agents`（Stage-0 載入，不新增場景鍵）；審查四角沿用其既有載入規則。
2. **起草者與審查者分離**（`SDD_AUTOCLAUDE_BRIDGE.md` 第 6.4 節 C-3 的補償控制）：`spec-engineer` 不得兼任任一審查角。
3. 每個 stage run 一個獨立 context（`maintain_context: false`），步驟之間只經檔案交接；審查者之間彼此不可見（盲審）。審查者任務書的內容限制見 `ADVERSARIAL-REVIEW-CARD-TEMPLATE.md` 第 8 節。
4. agent 人設在執行層以「by-reference」載入：編譯成工作區 `.prompts/<role>.md` 並記錄 sha256，stage 任務書只寫「先讀該檔再執行」。審查卡的 `persona_sha256`、`agent_yaml_sha256` 因此可稽核。

---

## 2. FSM 對映與指令

> 約束：**不新增任何狀態、不新增任何邊、不碰 `_HAPPY_PATH`／`formal/`**（`AISDLC_SDD/CLAUDE.md` Rule 9 絕對禁令 #8）。研究子步、審查輪次與分數住執行層資料庫，不進 FSM。指令形態與呼叫樣板同 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈FSM 寫入指令〉；行號為 2026-11-02 在 LATEST 實查的值，改檔後以符號名為準。

### 2.1 兩把鍵（為何不是單鍵）

| | 外環鍵 R（研究與 PRD） | 內環鍵 I（實作） |
|---|---|---|
| 鍵名 | `research-<slug>`（換世代：`research-<slug>-g2`） | 軌道 A：`<sub>-<slug>`（`sub` 為 autoclaude／agentconsole／sdd／monorepo）；軌道 B：新專案名 |
| 狀態目錄 | `<研究工作區>/build/reports/fsm`（目標未定時唯一可用） | 目標專案根的 `build/reports/fsm`（`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.1 節） |
| 生命週期 | INIT → … → SPEC_FROZEN（Gate 0）；之後只在 SCR 時回 SPEC_DRAFTING（`transition_rules.py:35`） | Stage-1 基線採納 → Stage-2 TCS → IMPLEMENTATION → … → RELEASE（終態，`transition_rules.py:78`） |
| 建檔者 | 執行層（Bridge 的唯一建檔點）；人手流程由人跑第一次 `show` | 分流時建（同一建檔例外） |
| 為何不合併 | 單鍵必須讓狀態目錄＝研究工作區（目標未定才不依賴目標），但 AutoClaude 引擎的 adapter 與 Bridge 以「向上找含 `build/reports/fsm` 的目錄」定位狀態檔，而軌道 A 的 TCS 必須住目標專案的 `docs/03_testing/contracts/`：兩者互斥，內環整條會斷。兩鍵各守「一個狀態目錄、一個功能週期」（`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.0 節） | |

鍵名規則：`research` 是新的外環前綴（`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.0 節、第 9 節）；`slug` 小寫 kebab、≤30 字（含 FSM 專案鍵淨化後不被改寫）。外環鍵**不屬於**第 8.1 節四個標準狀態目錄，三件組的 `SDD_STATE_DIR` 一律指向研究工作區的 `build/reports/fsm`（絕對路徑）。

### 2.2 狀態對映表（來源規格每個狀態與轉換）

行號：`T`＝`tools/fsm_runtime/transition_rules.py`，`R`＝`tools/fsm_runtime/fsm_runtime.py`。

#### 外環（鍵 R）

| # | 來源規格 | FSM 狀態與邊 | 動作 | 備註 |
|---|----------|--------------|------|------|
| R1 | `TOPIC_INGESTION`（必填 topic、scope、depth_level） | INIT → SCENARIO_DETECT（T:13）→ AGENT_LOAD（T:14） | 建工作區、渲染 `issue_scope.json`；`show` 建檔；兩次 `transition` | `SCENARIO_DETECT` 的場景此時未定（greenfield 或 brownfield 到分流才知）：reason 如實寫「scenario decided at route」，FSM 不驗內容 |
| R2 | `DEEP_RESEARCH` | **停在 AGENT_LOAD**（屬可寫規格態，R:328-336；AGENT_LOAD 的出邊含 SPEC_DRAFTING，T:19） | 無 FSM 呼叫；執行 RESEARCH stage run | 研究是 FSM 之外的子活動，進度住執行層 |
| R3 | `PRD_DRAFTING` | AGENT_LOAD → SPEC_DRAFTING（T:19）；修訂時 SCG_VALIDATION → SPEC_DRAFTING（T:27，由 `gate FAIL` 自動帶入） | 首次 `transition`；修訂不另呼叫 | |
| R4 | `ADVERSARIAL_REVIEW` 開始 | SPEC_DRAFTING → SCG_VALIDATION（T:26） | `transition --to SCG_VALIDATION` | 先做前置否決（第 6.1 節）；不過直接 `gate FAIL`，不計分 |
| R5a | 分數達標 → `BASELINE_APPROVAL` | `gate PASS`：SCG_VALIDATION → HUMAN_PENDING（T:305-307；R:535-544，PASS 時 `reset_retry`，R:536） | `gate --gate SCG_VALIDATION --result PASS` | 人工閘開啟 |
| R5b | 分數不足且未耗盡 → 修訂 | `gate FAIL`：計數 <3 → SPEC_DRAFTING（T:327-328；R:546-578、621-627） | `gate … --result FAIL --reason …` | 見第 2.3 節預算 |
| R5c | 分數不足且耗盡 → 升級人工 | `gate FAIL`：計數 ≥3 → ESCALATION（T:323-324；R:579-595） | 同 R5b；回傳 `escalated: true` | 🔴 環境須 `SDD_ENABLE_AUTO_RECOVERY=0`（R:596-620：預設開啟時，gate 耗盡會先嘗試自動恢復） |
| R6 | `BASELINE_APPROVAL`（Gate 0；觸發 `User_Manual_Signoff`） | HUMAN_PENDING → SPEC_FROZEN（T:28）；若人工退回修訂過（`SCG_VALIDATION.current_count > 0`），先 HUMAN_PENDING → SPEC_REGRESSION_CHECK（T:28）→ SPEC_FROZEN（T:29；規則 `SDD_FSM_ENGINE.md` 轉換表「HUMAN_PENDING／人工確認通過」兩列） | 〈有重試史才〉`transition --to SPEC_REGRESSION_CHECK`；`spec-frozen --stage Gate-0 …` | **人按核准才執行**；`--approver` 必須是人（第 8 章） |
| R7 | 人工退回修訂（規格沒有、核准畫面需要「要求修改」） | **FSM 沒有 HUMAN_PENDING → SPEC_DRAFTING**（`SDD_SPEC_FIRST_GATE.md` 對照表第 5 列）；走 `gate SCG_VALIDATION FAIL "人工審查：…"`（計數加 1；被擋的轉態記 `gate_fail_blocked`，R:628-641），狀態停在 HUMAN_PENDING | `gate … --result FAIL --reason "人工審查：<修改要求>"` | 與自動 FAIL **共用同一個 3 次預算**。修訂後的重新審查只存在於執行層（審查輪紀錄），FSM 態不變，直到人再次核准；這段期間執行層**不得**呼叫 `gate SCG_VALIDATION PASS`（第 8 章〈人工退回與核准守則〉，裁決 D-50） |
| R8 | `BRANCHING_ROUTER` | 外環鍵**不動**（停在 SPEC_FROZEN） | 無 | 路由是執行層動作（第 9 章） |

#### 內環（鍵 I）

| # | 來源規格 | FSM 狀態與邊 | 動作 | 備註 |
|---|----------|--------------|------|------|
| I1 | 專案設定（`AISDLC_FEATURE_SETUP`／`STANDALONE_SCAFFOLD_SETUP`）＋建內環鍵 | INIT → SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING → SCG_VALIDATION → HUMAN_PENDING（T:13、14、19、26、27；`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.4 節的五次 transition） | `show`＋五次 `transition`，reason 寫採納理由 | 不用 `gate PASS`：採納不是重跑 SCG |
| I2 | Stage-1 凍結 | HUMAN_PENDING → SPEC_FROZEN（T:28） | `spec-frozen --stage Stage-1 --doc <已發佈 PRD 等> --digest --root <目標根> …` | **分流確認＝這一步的人工確認**（Rule 8） |
| I3 | `SDD_TASK_DECOMPOSITION`（TCS 草擬） | SPEC_FROZEN → SPEC_DRAFTING（Stage-2，T:35）→ SCG_VALIDATION → HUMAN_PENDING → SPEC_FROZEN（Stage-2，TCS 在 `--doc`） | 同 `SDD_AUTOCLAUDE_BRIDGE.md` 第 8.5 節 | |
| I4 | 測試先行 | SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION（T:35、38） | 既有路徑（Bridge 在委派批次內自動做；人手走第 8.6 節） | R-9.20.3 獨立性在此路徑結構上不成立，不宣稱滿足（第 6.7 節） |
| I5 | 實作與自癒 | IMPLEMENTATION ⇄ AUTOCLAUDE_DELEGATED（T:151）；自癒是引擎 run 內的重試，不是 FSM 態 | 既有 | 耗盡 → 引擎升級 → ESCALATION，只有人能恢復 |
| I6 | 回歸驗收 | IMPLEMENTATION → PR_REVIEW（T:46）→ RTM_VERIFY（T:66）→ RELEASE_READY（T:68） | `gate PR_REVIEW`、`gate RTM_VERIFY` | SCG-4 審查者必須未參與規格與實作 |
| I7 | 交付 | RELEASE_READY → RELEASE（T:77-78，終態） | 合併進 main 且雲端 CI 綠後 `transition --to RELEASE` | CI 紅：`gate RELEASE_READY FAIL --reason …`（理由必填） |

### 2.3 預算語意：最多 3 輪審查（裁決 D-24）

`record_gate_result` 在 FAIL 時**先**累計重試次數、再與上限比（R:546-547、576-578；`transition_rules.py:323-324`），`RETRY_LIMITS["SCG_VALIDATION"]` 是 3（T:267-268），所以**第 3 次 FAIL 就是 ESCALATION**：

| 審查輪 | 結果 | `gate` | `SCG_VALIDATION.current_count` | 轉態 | 工作流階段 |
|--------|------|--------|-------------------------------|------|-----------|
| 1（首審） | 未過 | FAIL | 1 | SCG_VALIDATION → SPEC_DRAFTING | 自動修訂 1 |
| 2 | 未過 | FAIL | 2 | → SPEC_DRAFTING | 自動修訂 2 |
| 3 | 未過 | FAIL | 3 | → **ESCALATION** | 升級人工 |
| 任一輪 | 通過 | PASS | 歸 0 | → HUMAN_PENDING | 待人核准 |

⇒ **最多 3 輪審查（首審加 2 次自動修訂）**，與來源規格字面「≤3 次修訂＝最多 4 輪」差 1，是有意的：

- 不改 `RETRY_LIMITS`：改上限等於動 `formal/SDD_FSM.tla`（Rule 9.18）。
- 不用裸 `transition SCG_VALIDATION → SPEC_DRAFTING` 規避計數：邊雖合法（T:27），但不記次數，等於繞過 R-9.1（絕對禁令 #4）。
- 人工「要求修改」（R7）與自動 FAIL 共用這 3 次預算；前置否決不過（第 6.1 節）也是一次 `gate FAIL`。
- ESCALATION 經人工恢復後預算不歸零（第 2.5 節；主控 D-60）。

### 2.4 人工退回與 SPEC_REGRESSION_CHECK

- 人工退回用 `gate SCG_VALIDATION FAIL`（R7），不用 `SDD_AUTOCLAUDE_BRIDGE.md` 第 8.6 節第 1 點的 SPEC_REGRESSION_CHECK 退回法：後者不計預算，會讓人工退回成為不受 R-9.1 約束的迴圈；本工作流要求外環鍵的有界停機涵蓋人工退回。
- **核准前的迴歸檢查**：只有在 `SCG_VALIDATION.current_count > 0`（人工退回過，且之後沒有被 `gate PASS` 歸零）時，核准前必須先 `transition --to SPEC_REGRESSION_CHECK`（`SDD_FSM_ENGINE.md` 轉換表：HUMAN_PENDING／人工確認通過但本 Stage 有重試歷史）。reason 寫「Gate 0 regression check: <已處理缺陷數>／<人工要求數>」。Stage-0 對「是否只是表面修正」的實質檢查＝SE-PRD 第 13.4 節修訂紀錄對每個缺陷 id 逐條回應，由人在核准前核對。
- 不要用 `gate --gate SPEC_REGRESSION_CHECK --result PASS` 代替：它只轉態，不寫 `frozen_stages`／`spec_doc_digests`（`SDD_SPEC_FIRST_GATE.md` 補充說明）。

### 2.5 ESCALATION（只有人能解）

第 3 次 FAIL 後 `escalated: true`，外環鍵進 ESCALATION。**只有人能恢復**（Rule 9.5、絕對禁令 #6）：

- 環境固定 `SDD_ENABLE_AUTO_RECOVERY=0`（外環鍵的每一次 CLI 呼叫）：審查分數不足不得被自動恢復進 AUTO_RECOVERY_ATTEMPT。
- 恢復指令由人在終端執行（樣板見 `SDD_AUTOCLAUDE_BRIDGE.md` 第 8.2(b)）：`resume-from-escalation --project "research-<slug>" --to SPEC_DRAFTING --must-exist --reason "<人工原因>"`（`--to` 只能是 SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW；外環鍵選 SPEC_DRAFTING）。
- 執行層不代跑、不開第二條恢復路徑；Console 只顯示可複製的恢復指令與「我已恢復，繼續」鈕（執行層唯讀驗證 FSM 已離開 ESCALATION 才續跑）。
- 預算耗盡後仍要繼續的合法做法：人恢復後繼續修訂（預算不歸零，見下一條）；或放棄這一鍵，另開新世代鍵 `research-<slug>-g2`（不是恢復，是放棄，仍由人決定並留稽核紀錄）。
- **ESCALATION 人工恢復後預算不歸零：至多再得一次審查，FAIL 立即再 ESCALATION、PASS 歸零；全新預算＝換世代鍵**（主控 D-60）。引擎事實：`resume-from-escalation` 不動重試計數（`fsm_runtime.py` 的 `resume_from_escalation` 只轉 ESCALATION → RESUME_VERIFICATION → 目標態並回填 `escalation_history`），只有 `gate … PASS` 與 `spec-frozen` 會把計數歸零；`state_loader.py` 的 `increment_retry` 見計數已達上限時把計數夾在上限、並在歷史列標「tamper detected」。所以人工恢復後的第一次 `gate SCG_VALIDATION FAIL` 就再進 ESCALATION、回傳的 `retry_count` 仍是 3（歷史列帶引擎的 tamper 字樣，是這個行為的已知邊界，不是真的遭竄改）；恢復後的第一次 `gate PASS` 才把計數歸 0 並進 HUMAN_PENDING。要全新的 3 次預算只有上一條的換世代鍵。執行層：UI 的剩餘預算＝`max(0, 3 − currentCount)`，恢復後的 `iterate` 只跑一輪。演練見 TCS AT-970-7-6。

### 2.6 〈FSM 寫入指令〉外環鍵（填入 `SDD_SPEC_FIRST_GATE.md` 的呼叫樣板；`--project "research-<slug>"` 已在樣板內）

環境：外環鍵的三件組為 `SDD_ACTIVE_VERSION`（LATEST 版號）、`SDD_PROJECT`＝`research-<slug>`、`SDD_STATE_DIR`＝`<研究工作區>\build\reports\fsm`（絕對路徑）；另設 `SDD_ENABLE_AUTO_RECOVERY=0`。

| # | 時機 | FSM 轉態 | 指令（`<動詞> <旗標>`） |
|---|------|----------|--------------------------|
| 1 | 研究專案建立（整個週期唯一允許缺檔自動建立的一次） | 建立 INIT | `show`（其後一律帶 `--must-exist`） |
| 2 | 議題攝取 | INIT → SCENARIO_DETECT → AGENT_LOAD | `transition --must-exist --to SCENARIO_DETECT --reason "research topic ingested: <slug>; scenario decided at route"`；`transition --must-exist --to AGENT_LOAD --reason "load research-analyst, spec-engineer, 4 reviewers"` |
| 3 | 研究完成、開始起草 | AGENT_LOAD → SPEC_DRAFTING | `transition --must-exist --to SPEC_DRAFTING --reason "Stage Gate-0: PRD drafting v<n>"` |
| 4 | 草稿過 P0 預檢，審查第 k 輪開始 | SPEC_DRAFTING → SCG_VALIDATION | `transition --must-exist --to SCG_VALIDATION --reason "SCG-0 對抗審查 round <k> 開始"` |
| 5 | 第 k 輪通過（四條件皆成立） | SCG_VALIDATION → HUMAN_PENDING | `gate --must-exist --gate SCG_VALIDATION --result PASS --reason "round <k> score=<s>; open P1=0"` |
| 6 | 第 k 輪未通過（含前置否決不過） | SCG_VALIDATION → SPEC_DRAFTING；第 3 次 → ESCALATION | `gate --must-exist --gate SCG_VALIDATION --result FAIL --reason "round <k> score=<s>: <前 3 個缺陷碼>"`（輸出單行 JSON，取 `next_state`、`retry_count`、`escalated`） |
| 7 | 人要求修改 | 維持 HUMAN_PENDING（計數加 1） | `gate --must-exist --gate SCG_VALIDATION --result FAIL --reason "人工審查：<修改要求>"` |
| 8 | 核准前的迴歸檢查（僅有重試史時） | HUMAN_PENDING → SPEC_REGRESSION_CHECK | `transition --must-exist --to SPEC_REGRESSION_CHECK --reason "Gate 0 regression check: <已處理缺陷數>/<人工要求數>"` |
| 9 | 人核准 Gate 0 | HUMAN_PENDING（或 SPEC_REGRESSION_CHECK）→ SPEC_FROZEN | `spec-frozen --must-exist --stage Gate-0 --doc "01_specs/PRD-v1.0.0.md" --doc "00_research/evidence_matrix.md" --doc "00_research/issue_scope.json" --doc "01_specs/adr_draft.md" --digest --root "<研究工作區>" --reason "<人類確認依據>" --approver "<人類確認者>" --json` |
| 10 | SCR 重新起草（第 9 章） | SPEC_FROZEN → SPEC_DRAFTING | `transition --must-exist --to SPEC_DRAFTING --reason "進入 Stage Gate-0-SCR<k>: <摘要>"` |

`transition` 與 `gate` 是舊 CLI 契約（成功輸出 `OK transitioned to <狀態>` 或單行 JSON；非法轉態是 traceback 與 rc 1）：執行層在呼叫前以 `show --must-exist` 預檢「現態 → 目標」、呼叫後再讀驗，不解析 stderr 文字（第 11 章）。讀 rc 不接管線。

### 2.7 邊集合審計（證明沒有新增邊）

| 邊 | `transition_rules.py` | 用在 |
|----|----------------------|------|
| INIT → SCENARIO_DETECT → AGENT_LOAD | :13、:14 | R1、I1 |
| AGENT_LOAD → SPEC_DRAFTING | :19 | R3、I1 |
| SPEC_DRAFTING → SCG_VALIDATION | :26 | R4、I1、I3 |
| SCG_VALIDATION → HUMAN_PENDING／SPEC_DRAFTING | :27 | R5a、R5b |
| HUMAN_PENDING → SPEC_FROZEN／SPEC_REGRESSION_CHECK | :28 | R6、I2 |
| SPEC_REGRESSION_CHECK → SPEC_FROZEN | :29 | R6 |
| SPEC_FROZEN → SPEC_DRAFTING | :35 | SCR 外環、I3 |
| SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION | :35、:38 | I4 |
| IMPLEMENTATION → SPEC_AUDIT／PR_REVIEW | :46 | SCR-minor、I6 |
| PR_REVIEW → IMPLEMENTATION／RTM_VERIFY；SPEC_AUDIT → PR_REVIEW；RTM_VERIFY → RELEASE_READY | :66、:67、:68 | SCR-minor、I6 |
| RELEASE_READY → RELEASE／IMPLEMENTATION | :77 | I7 |
| 任何態 → ESCALATION | :220-226、:291-292（`_EMERGENCY_TARGETS`） | R5c |
| ESCALATION → RESUME_VERIFICATION → SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW | :156、:160 | 人工恢復 |

**刻意不用或不存在的邊**：HUMAN_PENDING → SPEC_DRAFTING（不存在）；IMPLEMENTATION／PR_REVIEW／RTM_VERIFY → SPEC_DRAFTING（不存在，所以內環不能直接回規格階段，SCR 才需要第 9 章的機制）；裸 `transition SCG_VALIDATION → SPEC_DRAFTING`（合法但繞過計數，禁用）；TERMINATED（毀滅性終態，不用於 SCR）。

---

## 3. 研究方法

本章自足，不依賴任何 monorepo 根層的 SOP 檔；方法源自 monorepo 的 `docs/05_development/SelfImproving_Research_Methodology_SOP.md` Part I（S1～S8），第 3.7 節列出有意的差異。

### 3.0 方法對照（S1～S8 在 Stage-0 的取用）

| SOP 步驟 | Stage-0 對應 | 負責 |
|----------|--------------|------|
| S1 問題定義 | `issue_scope.json` 的 `topic` 四要素 | 執行層渲染（使用者輸入）；產品審查角核對內容 |
| S2 來源策略 | 三層檢索、來源分級、查證層級、搜尋紀錄 | `research-analyst` |
| S3 抽取 | 七欄抽取（F1～F7）與六軸適用性 | `research-analyst` |
| S4 綜合 | 起草 SE-PRD（問題定義、技術方案對比、功能規格） | `spec-engineer` |
| S5 反證 | 每個證據項恰一筆反證結論 | `research-analyst` |
| S6 落地判準 | 四方審查的 rubric 與通過條件（第 6 章）；SOP 的 B／H／M／R 四格不直接沿用 | 審查四角 |
| S7 再查證觸發 | 研究範圍修訂（`scope_rev` 加 1）、審查或人工指出證據缺口 → 增補研究；SCR | 人與執行層（症狀驅動，沒有日曆或次數門檻） |
| S8 誠實劃界 | `honest_bounds` 三桶與矩陣末節 | `research-analyst`；執行層渲染 |

### 3.1 S1 問題定義與 `issue_scope.json`

契約見 `docs_template/sdd/requirements/ISSUE-SCOPE-TEMPLATE.md`。`topic` 一句話必須同時含四要素，缺一回頭補，不得開始檢索：

| 要素 | 問自己 |
|------|--------|
| 約束 | 在哪些邊界內決定？ |
| 決策者與問題 | 替誰回答什麼問題？ |
| 成功判準 | 怎樣算答案夠用？ |
| 否決條件 | 什麼情況下放棄或改選？ |

四要素檢查屬於**審查**的 rubric 項目（產品角的 `scope_discipline`），不是 schema 驗證：schema 只擋形狀，不擋內容貧乏。`issue_scope.json` 由執行層（使用者輸入）渲染，研究者與規格工程師唯讀；範圍變更＝`scope_rev` 加 1，舊證據不刪、標示其所屬 `scope_rev`，修訂後必須重跑檢索（新的 `issue_scope_sha256`）。

### 3.2 三層檢索（四個來源層）

來源規格的三層是學術、產業、開源與社群；「開源與社群」在 `layer` 值與議題檔開關上拆為 OSS 與 COMMUNITY 兩個，所以實際有四個來源層：

| 層（`layer`） | `issue_scope.layers` 開關 | 取得方式 | 來源網域（allowlist 初值） | 查證層級上限 |
|---------------|--------------------------|----------|---------------------------|--------------|
| ACADEMIC 學術與文獻 | `academic` | 預取（執行層以官方 API 抓回原檔位元組並記雜湊）＋研究者抽取 | arXiv、Semantic Scholar（含 DOI 解析） | V3 |
| INDUSTRY 產業前沿 | `industry` | Web 層（headless WebSearch 與 WebFetch）；**預設關閉** | 產業部落格網域須由管理員逐一加入 | V2（WebFetch 是小模型轉述） |
| OSS 開源專案 | `oss` | 預取 GitHub API（repo、授權、提交、issue 與 PR 熱度） | GitHub API | V3（`git_commit`、`license_spdx` 取自 API） |
| COMMUNITY 社群討論 | `community` | 預取 Stack Exchange API；Reddit 預設關閉（須管理員自建應用並接受條款後才可加入，且僅經 Web 層） | Stack Exchange API | 只當線索（T3） |

- 具體網域清單與逾時、單檔大小、單專案抓取次數上限屬**執行層設定**，不寫進本框架文件（數字會調整）；外呼 allowlist 與模型端點清單是**兩個獨立實例**。
- **不抓取 PDF**：取不到文字的來源改取摘要頁（例如 arXiv 的 abs 頁）並標 V2，全文未讀列入誠實劃界；再開症狀＝掌舵者要求納入必須讀 PDF 全文的來源。
- 四個層開關（`academic`、`industry`、`oss`、`community`；來源規格把 OSS 與 COMMUNITY 併為「開源與社群層」，議題檔拆成兩個勾選）至少一個為 true；開關為 true 但該層不可用（例如 `industry` 開啟而 Web 層未啟用）時，執行層回報「該層不可用」，不靜默略過。
- headless 的 WebSearch 與 WebFetch 逐筆呼叫執行層**觀測不到**，只認研究者在 `search_log` 的宣告，因此這類來源的查證層級最高 V2，且 URL 必須出現在某筆 `result_urls`（第 4 章）。

### 3.3 S2 來源策略

- **分級**：T1 一手（arXiv 或會議頁、官方文件與官方工程部落格、官方 repo）；T2 二手（survey、基準報告；畫地圖用，不單獨支撐論點）；T3 線索（個人貼文、論壇、社群討論；**收進來源表但強制 `clue_only`，不得當證據**）。
- **時間窗**：依 `recency_years`；超出時間窗的來源只在奠基性（定義、標準、授權條款）時納入，並在 `f6` 註明年份與理由。
- **納入**（三條皆成立）：說清楚技術或做法的對象與適用條件；有實驗證據、可驗證事實（授權條款、維護紀錄）或明確的負面結果；與 `in_scope` 或 `tech_stack` 至少一項相關。**排除**：與命題無關；無技術細節的行銷稿；只轉述他人結論的二手貼文（可降為 T3 線索）；頁面取不到。
- **查證層級**（來源表必填，不准憑記憶列入）：V1 只見搜尋結果的標題與 URL；V2 已開啟頁面（WebFetch 轉述最高 V2；或執行層抓回原文但尚未針對章節專項抽取）；V3 原文位元組已落地，且針對方法、限制、安全章節做過專項抽取；V0（只憑記憶）**不得列入**。
- **建議查詢族**（每個啟用的層至少兩條，實際用的字串寫進 `search_log`）：方案綜述與比較（`<主題> survey`、`<主題> benchmark`）；官方文件與工程實務（`<技術> documentation`、`<技術> engineering blog`、`<技術> postmortem`）；開源專案健康度（`<技術> github license maintenance`）；授權與合規（`<技術> license compatibility`）；失敗與批評（`<機制> limitations`、`<機制> fails`、`<機制> negative result`）；帶年份的最新字串（`<主題> 2026`）。一題一次，不以分號串接多題。
- **深度預算**：`depth_level`（`QUICK` 快速、`STANDARD` 標準、`DEEP` 深入）對應的來源數、抓取次數與牆鐘預算由執行層在任務書宣告；到了預算就停並把未完成面寫進誠實劃界。研究者**邊查邊寫**（每新增約三個來源就覆寫一次 `evidence_items.json`），不等查完才一次落檔。
- **URL 規則**：每個 URL 必須出自本輪某次搜尋結果或抓取；憑記憶猜出的網址先以 WebFetch 開啟並把頁面標題核對一致才算驗證，核對不上就移除，不保留猜的 URL。

### 3.4 S3 七欄抽取

契約與驗證規則見 `docs_template/sdd/requirements/EVIDENCE-MATRIX-TEMPLATE.md` 第 2 節。每個證據項固定七欄，缺資訊寫「未見」，不留空白：

| 欄 | 內容 |
|----|------|
| F1 機制 | 一句話：做了什麼、由誰觸發、由誰驗證 |
| F2 證據 | 基準名、數字、對照組；數字原樣抄 |
| F3 失敗與批評 | 來源自述限制；後續文獻的反證 |
| F4 風險標籤 | 取自通用登錄表（LOCK、IMM、SELF、SCOPE、DEP、LIC、SEC、COMP），不自創；表外風險寫進 F3 或 F6 |
| F5 適用性 | **對本專案**的六軸：技術可行｜授權相容｜維護風險｜效能邊界｜資安｜成本，各填 A 直接適用、M 需改造、N 不適用並附一句理由 |
| F6 限制 | 模型、資料集、成本、單次實驗、是否重現；預印本、單一作者、自述成果、只讀摘要都寫在這裡 |
| F7 查證層級 | V1、V2 或 V3，不得高於來源的查證層級 |

- **F5 是研究者的判斷，必須與 F2（來源說了什麼）分開寫，不得把判斷寫成來源所說。**
- **數字登錄規則**：數字原樣抄（含單位、基準、對照組），不四捨五入、不換算；兩個數字要比較時必須出自同一來源同一基準；搜尋工具轉述的數字只能放 V1 並標「須核對」。執行層對 V2、V3 的數字做字面或數值比對，比對不到標 `UNANCHORED`（由執行層計算，研究者不寫）。
- 只為 T1、T2 來源建立證據項；每個證據項的 `claim` 是一句話，供 PRD 以 `[E-NNN]` 引用。

### 3.5 S5 反證

每個證據項**恰一筆**反證結論，只准五種：

| 結論 | 意義 |
|------|------|
| `WEAKEN` 削弱 | 證據項降級 |
| `LIMIT` 限定 | 補適用範圍條件，並已寫進 F3 或 F6 |
| `IRRELEVANT` 無關 | 寫理由 |
| `NOT_FOUND` 未找到 | 附搜尋字串與日期，同一字串也列入誠實劃界的「沒查到」；「沒找到」不是「已證無反例」，強度上限 MEDIUM |
| `NOT_SEARCHED` 未搜 | 如實寫「未做專門反證搜尋」，不得寫成「未找到」；強度上限 MEDIUM |

字串範本：`<機制> limitations`、`<機制> fails`、`<機制> negative result`、`<機制> does not generalize`；記憶或經驗類加 `stale`、`poisoned`；評估器類加 `judge bias`、`overoptimization`；迴圈類加 `diminishing returns`。

### 3.6 S8 誠實劃界（收尾必寫；三桶分開，不得合併）

1. **沒查到**：搜尋字串、日期、結果。
2. **只讀摘要或搜尋結果**（V1、V2）：逐篇列出。
3. **沒讀全文**：除 V3 外一律視為未讀全文。

固定三句寫在證據矩陣末節：「WebFetch 是小模型依提問轉述，所有 V2 的數字與陳述都是轉述，PRD 引用前須核對原頁面。」「來源表以外的文獻一律視為『未納入』，不是『不存在』。」「搜尋引擎找得到的不等於全集，本矩陣不聲稱窮盡。」

### 3.7 與 SelfImproving 研究方法 SOP 的差異清單（規範性；若兩份並存，各自為其領域的真相源）

| # | 差異 | 本工作流 | SOP |
|---|------|----------|-----|
| 1 | F5 適用性六格 | 改為「對本專案」的六軸：技術可行｜授權相容｜維護風險｜效能邊界｜資安｜成本 | 專屬於自我進化主題的六格（CLI agent｜不更新權重｜harness｜Playbook｜SDD FSM｜人工閘） |
| 2 | T3 線索 | 收進來源表但強制 `clue_only`，不得出現在任何證據項 | 把 T3 排除在來源表之外 |
| 3 | F4 風險標籤 | 通用登錄表（LOCK、IMM、SELF、SCOPE、DEP、LIC、SEC、COMP） | 自我進化主題專屬的標籤集合 |
| 4 | V3 的取得 | 要求原文位元組已落地（執行層預取）且針對章節專項抽取；WebFetch 轉述最高 V2 | 允許以 WebFetch 追問章節升到 V3 |

---

## 4. 證據錨定與防幻覺

本章沿用 [EVIDENCE_DISCIPLINE.md](../../agent/EVIDENCE_DISCIPLINE.md)（單一真相源；本章不複寫其條文，只寫本工作流特有的錨定規則）。

1. **錨定鏈**：PRD 的每個研究依據宣稱 → `[E-NNN]`（證據項）→ `S-NNN`（來源）→ URL、DOI 或 git commit（三者至少一個；開源 repo 另須 `license_spdx`）。鏈上任一環缺失＝該宣稱無效。
2. **PRD 引用規則**：只能引用 `查證層級` ≥V2、未標 `UNANCHORED`、`strength` 非 `CANDIDATE` 的列；不得引用不存在的編號；PRD 的「研究依據」表至少一列，且每列至少一個 `[E-NNN]`；`1.2` 的研究依據至少含一筆 T1 或 T2 來源（T3 只當線索，資料層與驗證器皆禁止當證據）。
3. **強度由函式決定**，研究者與規格工程師都不得自行升降（函式見證據模板第 3.3 節：基準由來源分級與查證層級決定，反證與風險標籤再調整）。`CANDIDATE` 只當候選線索。
4. **URL 出處**：每個來源的 URL 必須出現在某筆 `search_log` 的結果或該來源的抓取紀錄中；搜尋工具轉述的數字不得當 V2 或 V3。
5. **證據矩陣的確定性渲染**：`evidence_matrix.md` 由 `evidence_items.json` 與抓取紀錄渲染，**同輸入必得同輸出**（不含當下時間或隨機值），Gate 0 才有可凍結的穩定摘要；矩陣版本只增不改（`<!-- r2p:evidence_matrix schema_rev=1 version=N -->`）。
6. **增補只增不改**：已有前一版 `evidence_items.json` 時，新版必須逐位元保留其全部來源、證據項與搜尋紀錄，編號延續，只准新增（見研究者設定的增補模式）。
7. **授權欄**：矩陣首段統計「授權待查」筆數（授權為 GPL／AGPL 系或「未見」的證據列），是資安審查角的輸入；PRD 第 9.4 節外部相依表每列授權非空。
8. **第三方原文不入版控**：原文只存研究工作區（`00_research/raw/`，不入版控與備份）；PRD 與矩陣對第三方內容以摘要與短引文為限；證據靠 URL、DOI、commit 與雜湊錨定，不靠保存原文。

---

## 5. SE-PRD 撰寫規範

模板：`docs_template/sdd/requirements/PRD-SPEC-ENGINEERED-TEMPLATE.md`（家規 14 章為骨架，來源六節以 `<!-- r2p:section=N -->` 錨點標記；**不改** `docs_template/core/prd/PRD_Universal_Template.md`）。

### 5.1 來源六節與家規 14 章

**骨架原則（裁決 D-20 SA-01；PRD C.6 SD-13）**：SE-PRD 的頂層是家規 `PRD_Universal_Template` 的 14 章（章號與標題逐字一致），來源規格 §3.2 的六個區塊以 `<!-- r2p:section=N -->` 錨點嵌入對應章節，**章尾（第 14 章之後的附錄 R）附「來源六節 ↔ 家規章節」對映表，並保留在交付檔內**。同一份文件因此同時接受兩套檢查——**雙重預檢**：(a) 六節錨點齊全；(b) 家規必讀章非空，缺一不可。「六章為頂層」的骨架（把來源六節直接當章）已被否決：家規必讀章（目標用戶、商業需求、UX、時程、風險）會沒有位置，雙重預檢之一落空。

| 來源 §3.2 區塊 | 錨點 | 家規 PRD 章 | 在內環的去向 |
|----------------|------|-------------|--------------|
| 1 元數據 | `section=1` | 文檔元數據、第 14 章追蹤鏈 | Stage-2 TCS 的文件資訊 |
| 2 問題定義與背景（含研究依據表） | `section=2` | 1.2、1.3、第 11 章、13.2 | FRD-lite 前言的背景段 |
| 3 功能性規格（Epic→Feature→US；邊界條件） | `section=3` | 第 3、5 章 | FRD-lite 的 US 欄 |
| 4 驗收標準（Gherkin） | `section=4` | 第 5 章各功能的 AC | FRD-lite 的 AC 欄；TCS 的 AC→AT 映射 |
| 5 技術與資料架構 | `section=5` | 第 9、12 章 | TCS 的整合與契約測試被測介面 |
| 6 非功能性需求 | `section=6` | 第 6 章 | TCS 的效能與資安 AT |

### 5.2 撰寫規則

1. **ID 沿 Rule 7 數字制**：`EPIC-NNN`、`F-NNN`、`US-NNN`、`AC-NNN-Y`、`NFR-NNN`，選填 `INV-NNN`；NNN 三位數字，同類不重複；`AC` 的 NNN 慣例取其所屬 US 的編號，使 Stage-2 TCS 的 AT 文法 `AT-\d{3}-\d+` 可直接對映。
2. **AC 是標題加 Gherkin**：每個 AC 一個 `#### AC-NNN-Y <標題>`，其下用 `Scenario`／`Given`／`When`／`Then`。標題形態是為了讓既有模糊度計分器（`tools.fsm_runtime.ambiguity_scorer`，以標題抽取 AC）抽得到每一條 AC；寫成條列或表格會抽到 0 條，Ambiguity Gate 空轉。`Then` 必須是可觀察或可量測的狀態變更，不得只靠「快速」「適當」「合理」這類模糊詞。
3. **每個 Feature 有邊界條件**（輸入範圍、上限、空值、並發、失敗時行為，每條可被測試）與一行 `**對應 US**:`；每個 US 一行 `**對應 AC**:`；EPIC→F→US→AC 無斷鏈，每個 AC 被某個 US 引用、每個 US 被某個 Feature 引用。
4. **NFR 數值物理可達**：回應時間與吞吐量大於 0、可用性不超過 100%、錯誤率在 0～100%（SLV-001），並寫量測法。
5. **第 9 章四個子區塊皆非空**：9.2 資料模型、9.3 API 與 Mermaid 序列圖、9.4 外部相依與授權（每列授權條款非空；查不到寫「未見」並標授權待查）、9.5 架構決策（指向 `01_specs/adr_draft.md`，每個決策依 `docs_template/sdd/adr/ADR-TEMPLATE.md` 章節）。
6. **`Target Scope`**（`AISDLC_MODULE` 或 `STANDALONE_PROJECT`）只是**路由建議值**，人在分流時可改；`AISDLC_MODULE` 或專案類型為 Brownfield 時，第 11 章既有系統分析必填。
7. **版本號**：草稿 `v0.<rev>.0-draft`，每個新版本 `rev` 加 1；Gate 0 核准後基線檔名為 `PRD-v1.0.0.md`，內容與被核准草稿**位元組相同**（檔內 Version 欄仍是草稿版號）；SCR 後再核准為 `v1.<n>.0`（小修）或 `v2.0.0`（結構性變更）。
8. **FRD-lite**：SE-PRD 第 5.1 節的 US 與第 5.2 節的 AC 兼具 FRD-lite 功能，使 SCG-0 的「PRD 加 FRD」成立而不重複造檔。
9. **修訂紀錄**：修訂輪在第 13.4 節對上一輪缺陷清單的每個 `id` 逐條回應（已改／不改附理由／人工豁免），不得順手改動無關章節。

### 5.3 草擬預檢 P0（草稿進入審查**之前**由執行層以確定性程式檢查）

P0-1 至 P0-9 的條文見模板第 0.2 節（錨點、章節非空、無佔位、ID 格式、追溯完整、`[E-NNN]` 有效、第 9 章完整、Mermaid）；其中 `[E-NNN]` 有效（P0-7）的違規以 `CITES_MISSING`、`CITES_V1`、`CITES_UNANCHORED`、`CITES_CANDIDATE` 四個代碼逐引用回報（代碼的定義與判準以模板第 0.2 節 P0-7 列為單一真相源，與根層 PRD §5.1.3 同名）。**雙重預檢**（第 5.1 節）＝P0-1 與 P0-2（六節錨點齊全且各節非空）加上 P0-3（家規必讀章非空：文檔元數據表與第 1～8 章、第 10 章），兩者都過才算結構預檢通過。**P0 不過＝草稿不進審查、不轉 FSM 態、不耗審查預算，只列出缺漏**；這與第 6.1 節的前置否決（`gate FAIL` 計入預算）是兩道不同的檢查。

---

## 6. 對抗式審查（SCG-0 的評估器）

契約、rubric 登錄表、JSON 範例、算例與任務書規則見 `docs_template/sdd/requirements/ADVERSARIAL-REVIEW-CARD-TEMPLATE.md`；本章是流程與語意。

### 6.1 前置否決（先於審查者；任一不過＝本輪 `gate FAIL`、不計分）

| 檢查 | 內容 |
|------|------|
| `SLV-001` | NFR 物理可行性 |
| `SLV-002` | AC 可測試性（每個 AC 有明確前置條件與可觀察或可量測的期望結果） |
| `SLV-003` | 業務不變量無矛盾（沒有 `INV` 時為空集合，視為通過） |
| `AMBIGUITY` | 錨點 4 區段內每個 AC 的模糊度 <0.4，或已有對應 `AMBIGUITY-WAIVER` |

**評分卡是 SCG-0 的評估器，不取代 SLV 與 Ambiguity Gate；前置否決不可被分數覆蓋。** 誠實劃界：SLV 規則檔的掃描目標是路徑樣式（`docs/01_requirements/FRD-*.md`），研究工作區的 PRD 不在其內，機械半段由執行層對 PRD 內容實作同一份條文，對非標準寫法可能空轉，所以 QA 角必填 `slv_manual_check` 人讀補位（逐條讀 AC，回報 AC 總數與可自動化條數）；不得把「機械半段沒報錯」當成通過。

### 6.2 四維 rubric（每維 5 項，每項 0～20 分，加總 0～100）

| 維度 | 權重 | 審查者 | 五個項目 |
|------|------|--------|----------|
| ARCHITECTURE | 30% | `sd-architect` | `coupling`、`dependency_risk`、`performance_bounds`、`data_interface`、`evidence_fit` |
| PRODUCT | 25% | `pm-po` | `business_value`、`metric_measurability`、`scope_discipline`、`prioritization`、`evidence_grounding` |
| QA | 25% | `qa-tester` | `us_ambiguity`、`gwt_automatable`、`edge_case_coverage`、`traceability`、`nfr_testability` |
| SECURITY | 20% | `security-engineer`（`compliance-officer` 輔） | `license_conflict`、`secret_handling`、`injection_risk`、`authn_authz`、`external_content_safety` |

評分錨點（19～20 無缺陷且須有核對過的 PRD 錨點；0～4 該項實質缺席）、缺陷嚴重度 P1～P4、缺陷 `code` 與 `prd_anchor` 文法、缺陷狀態生命週期（`OPEN`、`FIXED`、`REGRESSED`、`WAIVED`、`SUPERSEDED`）皆在審查卡模板。

### 6.3 通過條件（整數運算；公式與算例見審查卡模板第 2 節）

`W100 = 30·A + 25·P + 25·Q + 20·S`；一輪通過當且僅當**四個條件全部成立**：

1. 前置否決全過；
2. `W100 ≥ 8500`（加權總分 ≥85）；
3. 四維每一維 ≥ 地板 60（`dimension_floor`，初值、未校準）；
4. 本輪沒有未結（`OPEN`）的 P1 缺陷。

地板與未結 P1 阻擋是裁決 D-14：加權平均會掩蓋單維度的致命缺陷（例：資安 40 分仍可過），代價是更常進修訂輪，由「最多 3 輪＋ESCALATION」承擔。權重、門檻、地板是產品常數，不提供介面修改；調整任一數字＝修訂審查卡模板與 Console PRD，不是設定。

`verdict`（寫入審查輪與彙整卡的值）：`PASS`｜`REVISE`｜`ESCALATE`。另有評估器的回報 `REVIEW_INVALID`——任一審查者輸出重試一次後仍不合 schema：不計輪、不呼叫 FSM、不得判 PASS，**不寫審查輪列**（執行層只記 stage run〔exit_reason=review_invalid〕與事件），所以它不在彙整卡 `rounds[].verdict` 的值域（審查卡模板第 7.2 節；主控 D-55）。彙整卡每輪另含 `prd_version_no`（整數，對映資料庫 `version_no`），與 `prd_version`、`prd_sha256` 描述同一份 PRD（審查卡模板第 7.1～7.3 節；主控 D-54）。

### 6.4 盲審與任務書規則

- 每位審查者一個**獨立 run**（`maintain_context: false`），不讀他角輸出；只准寫自己維度的 `02_governance/reviews/round-<k>/<dimension>.json`，整份檔案只含一個 JSON 物件。
- 審查者任務書**不得含**權重、門檻、地板、其他維度的分數或缺陷、前幾輪分數、FSM 狀態、「通過條件」說明；修訂者（`spec-engineer`）任務書**不得含**任何分數、加權總分、權重與門檻，只含缺陷清單。
- 加權、判定、彙整＝執行層**程式**（確定性），審查者不給總分、不算權重；單維度 `score` 必須等於五項 `score` 之和，不等＝該維度 JSON 無效。
- 審查結果只對被審 PRD 的雜湊有效：人儲存新版本後舊結果過期（第 7 章）。

### 6.5 反 Goodhart

- PRD 的成功指標不得是審查產出數或審查分數；修訂者看不到分數，審查者看不到權重與門檻。
- 零發現不是滿分：給 ≥18 分的項目 `note` 必須含實際核對過的 PRD 錨點。
- 參數快照隨每輪記錄（`params`），分數綁 PRD 版本與雜湊，歷史評分不被事後改寫。

### 6.6 缺陷處置

缺陷只有五種狀態且由執行層依後續輪次的缺陷清單確定性判定；`WAIVED` 只能由人工動作產生（含 `waiver.by`、`waiver.reason`、`waiver.at`）。P1 缺陷要通過只能「改」，或由人工豁免。

### 6.7 已知邊界（獨立性）

四位審查者同為 AI、同工作區可互讀檔案，**不滿足** R-9.20.3 型的獨立性（oracle 對生產者不可見；`SDD_AUTOCLAUDE_BRIDGE.md` 第 6.4 節誠實條款）。補償控制：每位審查者獨立 run、聚合與判定由程式、Gate 0 由人。**不宣稱已滿足。**

---

## 7. 迭代與升級

```
DRAFT（spec-engineer）→ P0 預檢（不過：回 DRAFT，不耗預算）
  → transition SCG_VALIDATION（審查第 k 輪）→ 前置否決 → 四方審查 → 聚合
      ├─ 四條件皆成立 ─→ gate PASS ─→ HUMAN_PENDING（待核准）
      ├─ 未過且計數 <3 ─→ gate FAIL ─→ SPEC_DRAFTING ─→ REVISE-k（帶缺陷清單）─→ P0 預檢 → 第 k+1 輪
      └─ 未過且計數 =3 ─→ gate FAIL ─→ ESCALATION（只有人能恢復）
```

- **修訂**：`spec-engineer` 帶上一輪缺陷清單修訂，13.4 修訂紀錄逐條回應；只改缺陷錨點與其必要連動。
- **證據缺口型缺陷**：不憑空補證據；在 PRD 第 10 章新增「證據缺口」一列，由執行層或人啟動增補研究（`scope_rev` 不變）；範圍變更才升 `scope_rev`。
- **人工編輯**：人可在工作室直接編輯 PRD（產生人工版本，版本號 `rev` 照計）；儲存新版本後舊審查結果對新雜湊失效，需重新審查。人工要求修改走第 2.2 節 R7。
- **人工退回後的再審（POST_HUMAN）**：人工退回（第 2.2 節 R7）之後現態仍是 HUMAN_PENDING。再審**通過**只寫資料庫（彙整卡該輪 `fsm.gate_result` 與 `fsm.retry_count` 皆為 `null`；不呼叫 `gate PASS`，見第 8 章 Bridge 守則）；再審**未通過**仍呼叫 `gate SCG_VALIDATION FAIL`（態不動、計數加 1，共用 3 次預算）。契約見審查卡模板第 7.3 節不變量 1（主控 D-54）。
- **REVIEW_INVALID**：審查者輸出不合 schema 且重試一次仍不合 → 不佔輪序號、不呼叫 FSM；執行層只記 stage run（exit_reason=review_invalid）與事件，不寫審查輪列（主控 D-55）；執行層回報，由人決定重跑或改人工審查。
- **升級**：ESCALATION 的恢復、解除與放棄見第 2.5 節；恢復只有人（Rule 9.5），本工作流不增加任何自動恢復路徑。

---

## 8. Gate 0（人工核准）

Gate 0 是**人**的動作（Rule 8、R-9.5）。**產品內的 Gate 0 永遠要求真人核准**：`--approver` 是真人（Console 為登入者；人手流程為人名或帳號），任何 agent、排程或腳本都不得替人核准；只有管理員可核准、建立 Release Tag 與 PR（裁決 D-12）。本 repo 根 `CLAUDE.md` 的「凍結常態規則」只適用於**開發本 repo 自身**時由主控代執行的 `spec-frozen`，**不適用**於產品執行期的 Gate 0。

**前置條件（全部成立才可核准）**：

1. 外環鍵現態為 HUMAN_PENDING（或已依第 2.4 節進入 SPEC_REGRESSION_CHECK）。
2. 最新一輪審查 `passed = true`，且被核准的 PRD 雜湊等於該輪 `prd_sha256`（人在核准後不得再改內容；核准之後審查結果對新版本不再有效）。
3. `01_specs/PRD-v1.0.0.md` 已由執行層複製為被核准版（位元組相同）；人手流程由人複製。

**凍結文件集**（`--doc`，相對 `--root`＝研究工作區；**不含 TCS**）：

| 文件 | 說明 |
|------|------|
| `01_specs/PRD-v1.0.0.md` | 被核准版 PRD（基線檔） |
| `00_research/evidence_matrix.md` | 證據矩陣（確定性渲染） |
| `00_research/issue_scope.json` | 研究議題與檢索邊界 |
| `01_specs/adr_draft.md` | 架構決策草稿 |

指令見第 2.6 節第 9 列；FSM stage 名固定 `Gate-0`。`spec-frozen` 對 TCS 沒有要求（TCS 要求在 Bridge 的 `:freeze` 端點與 AutoClaude adapter 的凍結閘，不在 FSM CLI），所以 Gate 0 以專用端點 `:approve-baseline` 承載、`:freeze` 契約不改（執行層，第 12 章）。核准後 `/stage-compaction`（SPEC_FROZEN 的進入動作）。

**人工退回與核准守則（裁決 D-50；與 `SDD_SPEC_FIRST_GATE.md` 對照表第 5 列同一做法）**：人在 Gate 0 要求修改＝`gate SCG_VALIDATION FAIL --reason "人工審查：<修改要求>"`（第 2.6 節第 7 列），因為 FSM 沒有 HUMAN_PENDING → SPEC_DRAFTING 的邊，所以狀態維持 HUMAN_PENDING、重試計數加 1、被擋的轉態記成 `gate_fail_blocked`，第 3 次 FAIL 進 ESCALATION（共用第 2.3 節的預算）。**Bridge 守則：現態 HUMAN_PENDING 時不呼叫 gate PASS；再審通過只記 DB**。原因：`record_gate_result` 的 PASS 路徑直接 `transition` 到 HUMAN_PENDING 且沒有 try／except，HUMAN_PENDING → HUMAN_PENDING 不是合法邊（`transition_rules.py` 的 `assert_transition`），結果是 traceback 與 rc 1，狀態檔不動；所以人工退回、修訂後的再審通過只寫資料庫（審查輪 `passed = true`；彙整卡該輪 `fsm.gate_result=null`，審查卡模板第 7.3 節不變量 1），FSM 態維持 HUMAN_PENDING，等管理員核准；核准時有重試史就先走 SPEC_REGRESSION_CHECK（第 2.4 節）再 `spec-frozen`。

**核准後唯讀**：Gate 0 凍結的四份文件不得再改；要改規格只能走 SCR（第 9.3 節），並以新的 stage `Gate-0-SCR<n>` 重新核准。

---

## 9. 分流與內環交接

### 9.1 軌道

| 軌道 | 目標 | 對應場景風格 | 規格掛載 |
|------|------|--------------|----------|
| A 併入既有模組 | `Target Scope = AISDLC_MODULE`（或人於分流時選定） | Brownfield | Gate 0 後把 PRD、證據矩陣、ADR 發佈到目標子專案 `docs/` 編號目錄（複製加雜湊驗證，不搬動） |
| B 獨立新專案 | `Target Scope = STANDALONE_PROJECT` | Greenfield（外加 DevOps 的 CI 骨架） | 整個研究工作區複製進新專案根（原工作區保留）；`build/reports/` 狀態目錄仍被版控忽略 |

分流是**執行層動作**，且**路由確認是人工動作**＝內環 Stage-1 基線採納的人類確認（Rule 8）。預演與副作用順序、worktree、scaffold、GitHub 初始化屬執行層（見第 12 章指標）；本框架只規定下列方法層條件。

### 9.2 內環鍵建立與 Stage-1 基線採納

1. 內環鍵 `<sub>-<slug>`（軌道 A）或新專案名（軌道 B）在**目標專案的標準狀態目錄**建檔（`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.1 節）。
2. 採納鏈沿第 8.4 節：`show`（建檔）＋五次 `transition`（INIT → SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING → SCG_VALIDATION → HUMAN_PENDING），reason 寫「baseline adoption；SCG 未重跑；SCG 已在外環鍵 research-<slug> 通過」並引外環 Gate 0 的審查輪識別與 PRD 雜湊；**不用** `gate PASS`（採納不是重跑 SCG）。
3. `spec-frozen --stage Stage-1 --doc <已發佈到目標 docs/ 的 PRD（必含）、證據矩陣、ADR 草稿> --digest --root <目標根> --reason "baseline adoption from research <id>; PRD sha256=<…>" --approver <路由確認人> --json`。已發佈副本與 Gate 0 基線**位元組相同**，所以摘要不漂移。
4. **Stage-2（TCS 增量規格）**：沿第 8.5 節；TCS 檔頭〈增量追溯表〉追溯到上一步採納的已凍結文件。Stage-2 TCS 草擬屬 P1。
5. **軌道 B 的規格深度**（主控 D-48(2) 裁決：軌道 B 內環走完整 SCG-1～3）：全新專案**不適用**增量條款（`SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉的適用範圍排除全新系統），內環除 Stage-1 採納 PRD 外，SCG-1～3（SRD、C4、ADR、OpenAPI）仍須走完整清單；Gate 0 只交付 SCG-0 與其前置。軌道 A 以既有模組的已凍結上位文件為追溯對象，適用增量條款。

### 9.3 SCR（Spec Change Request：規格變更退回 Stage-0）

事實：IMPLEMENTATION／PR_REVIEW／RTM_VERIFY 沒有回 SPEC_DRAFTING 的邊（T:46、66、68）；SPEC_AUDIT 唯一出邊是 PR_REVIEW（T:67）。合法機制有三條，各管一種 SCR：

**SCR-minor（規格文字或 AC 缺陷，證據與前提不變）**——內環走 SPEC_AUDIT 加 `spec-refreeze`，外環重走一個 Stage：

```
1) 外環鍵 R：transition --must-exist --to SPEC_DRAFTING --reason "進入 Stage Gate-0-SCR<k>: <摘要>"      # SPEC_FROZEN → SPEC_DRAFTING（T:35）
   → 與 Stage-0 相同的 DRAFT／審查／gate 迴圈（預算重新計：spec-frozen 會把 SCG_VALIDATION／PR_REVIEW／RTM_VERIFY／RELEASE_READY 一併歸零）
   → 人核准：spec-frozen --must-exist --stage Gate-0-SCR<k> --doc … --digest --root "<研究工作區>" --approver "<人>" --reason "SCR-<k> approved" --json
2) 發佈新 PRD 到目標 docs/（複製加雜湊），然後內環鍵 I：
   transition --must-exist --to SPEC_AUDIT --reason "SCR-<k> minor: <摘要>; research=<id>"                # IMPLEMENTATION → SPEC_AUDIT（T:46）
   spec-refreeze --doc "<目標 docs/ 相對路徑>" --root "<目標根>" --reason "SCR-<k>: PRD <a>→<b>" --approver "<人>"   # SPEC_AUDIT 屬 spec-refreeze 的合法狀態（R:707）；不轉態
   transition --must-exist --to PR_REVIEW --reason "SCR-<k> spec refrozen"                                # SPEC_AUDIT 唯一出邊（T:67）
   gate --must-exist --gate PR_REVIEW --result FAIL --reason "SCR-<k>: spec changed; re-implement"        # PR_REVIEW → IMPLEMENTATION（T:66）
```

- `gate PR_REVIEW FAIL` 會消耗 PR_REVIEW 預算，且相鄰 SCR 的 reason 若被判為同模式達 3 次，會改走 SPEC_AUDIT：讀回傳的 `next_state`，不是 IMPLEMENTATION 即回報 `BLOCKED` 交人處置，不重試。
- 以裸 `transition` 進入 SPEC_AUDIT 不累加 `spec_audit_count`（只有 `record_spec_audit` 累加，上限 `SPEC_AUDIT_MAX_PER_STAGE=2`，T:282）⇒ **執行層自設同一上限**：同一 Stage 內 SCR-minor ≤2，第 3 次強制改走 SCR-major。
- 進行中的 run 先停止（執行層既有的 `:stop` 路徑，終態同步後內環鍵回到 IMPLEMENTATION）。

**SCR-major（研究前提被推翻：證據錯、需求錯）**——新研究專案：建新研究工作區與新外環鍵（slug `<slug>-scr<N>`，記 `parent_research_id`），重走 Stage-0；舊內環鍵**不動**（留在其當前態；Console 標 superseded，不自動 TERMINATED——TERMINATED 是毀滅性終態，且 hooks-ON 視窗下是阻塞態）。新 PRD 通過 Gate 0 後，分流時選「併入既有專案」會建新內環鍵並重做 Stage-1 採納。理由：一鍵只走得完一個功能（`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.0 節）。

**來源是 SCG-4 或自癒耗盡（內環 ESCALATION）**：由人恢復（`resume-from-escalation`，`SDD_AUTOCLAUDE_BRIDGE.md` 第 6.8 節）；若人判斷需要改規格，恢復目標可選 SPEC_DRAFTING，隨後走標準 Stage 流程——這是**唯一**能從內環回到 SPEC_DRAFTING 的合法路，且必須人手（R-9.5）；SCR 按鈕在此情境只產生指令與記錄，不代跑。

---

## 10. 產物與目錄

### 10.1 研究工作區

預設位置在 **repo 外**（裁決 D-28：工作區若在 monorepo 內，每個 headless 步驟都會載入根 `CLAUDE.md` 鏈與根 hooks，既耗 token 又干擾研究）：Windows `%USERPROFILE%\.autosdd\my-project\<slug>\`、POSIX `~/.autosdd/my-project/<slug>/`、容器 `/workspace/my-project/<slug>/`；執行層以設定覆寫並限制在其路徑 allowlist 之下。**工作區路徑不得含 `docs/01_requirements/`、`docs/02_architecture/`、`docs/03_testing/` 子字串**（規格檔 deny 看路徑子字串，`fsm_runtime.py:43-47`、`:339-352`）；工作區內的目錄 `00_research`、`01_specs`、`02_governance`、`03_execution` 本身不含這些子字串，所以外環鍵在任何狀態寫它們都不被 Rule 9.6 擋。

```
<研究工作區>/
├── .prompts/<role>.md                    執行層編譯的 agent 任務書（by-reference；記 sha256）
├── 00_research/
│   ├── issue_scope.json                  議題與檢索邊界
│   ├── raw/<sha256>.<ext>                第三方原文（內容定址；不入版控與備份）
│   ├── notes/E-NNN.md                    超長欄位附註（選用；無證據效力）
│   ├── evidence_items.json               證據項（研究者寫）
│   └── evidence_matrix.md                證據矩陣（執行層渲染；Gate 0 凍結）
├── 01_specs/
│   ├── PRD_draft.md                      PRD 工作稿（永遠是最新草稿）
│   ├── PRD-v1.0.0.md                     Gate 0 核准版基線
│   └── adr_draft.md                      架構決策草稿（Gate 0 凍結）
├── 02_governance/
│   ├── reviews/round-<k>/<dimension>.json   審查者單維度輸出
│   ├── review_card.json                  跨輪彙整（執行層寫）
│   ├── route_decision.json               分流決定（執行層寫；P1）
│   └── state.json                        匯出視圖（非權威）
├── 03_execution/                         TCS 草稿與拆解（P1）
└── build/reports/fsm/FSM-STATE-research-<slug>.yaml   外環鍵狀態（只經 FSM CLI 寫；被版控忽略）
```

### 10.2 每檔作者與流向

| 檔案 | 作者 | 說明 |
|------|------|------|
| `00_research/issue_scope.json` | 執行層（人手流程為人） | 契約見議題模板；研究者唯讀 |
| `00_research/evidence_items.json` | `research-analyst` | 驗證不過即該步失敗重試 |
| `00_research/evidence_matrix.md` | 執行層確定性渲染（人手流程由研究者依模板版式手寫） | 供人讀與 Gate 0 凍結 |
| `01_specs/PRD_draft.md`、`adr_draft.md` | `spec-engineer`（人可編輯，產生人工版本） | 草稿通過 P0 才進審查 |
| `01_specs/PRD-v1.0.0.md` | 執行層（核准時複製核准版） | **FSM `spec-frozen` 的 `--doc`** |
| `02_governance/reviews/round-<k>/<dimension>.json` | 各審查者 | 只寫自己維度 |
| `02_governance/review_card.json` | 執行層（跨輪彙整，每輪重新渲染） | 歷史評分與缺陷修訂紀錄 |
| `02_governance/state.json` | 執行層匯出 | 🔴 **非權威**：FSM 真相＝`FSM-STATE-*.yaml`（只經 `FSMRuntime`），游標真相＝執行層資料庫；不得被任何程式讀回當輸入 |
| `build/reports/fsm/FSM-STATE-research-<slug>.yaml` | FSM CLI | 不得手改（絕對禁令 #1） |

### 10.3 JSON 契約索引

契約的欄位定義與有效範例住四份模板；每個 JSON 區塊前一行有定位標記 `<!-- r2p:contract=<名稱> -->`，供執行層的契約對拍測試讀取：

| 標記 | 模板 |
|------|------|
| `issue_scope` | `ISSUE-SCOPE-TEMPLATE.md` |
| `evidence_items`、`axis_registry`、`risk_tag_registry` | `EVIDENCE-MATRIX-TEMPLATE.md` |
| `review_params`、`rubric_registry`、`review_dimension`、`review_dimension_qa`、`review_card` | `ADVERSARIAL-REVIEW-CARD-TEMPLATE.md` |

機器 schema 住 Bridge；框架只放契約與範例，以對拍測試鎖（ADR 決策 D6）。

---

## 11. 已知邊界與再開症狀

| 邊界 | 事實 | 處置與再開症狀 |
|------|------|----------------|
| Web 層呼叫不可觀測 | headless WebSearch 與 WebFetch 逐筆呼叫執行層看不到，只認研究者在 `search_log` 的宣告（`AGENT_DECLARED`），查證層級 ≤V2 | 症狀：審查發現宣告的 URL 打不開或內容不符 → 降級該來源並記缺陷 |
| 審查獨立性 | 同一 AI、同工作區可互讀，不滿足 R-9.20.3 型獨立性（第 6.7 節） | 補償控制見第 6.7 節；不宣稱滿足 |
| 機械半段可能空轉 | SLV 規則檔掃描路徑樣式、模糊度計分器依標題抽 AC；非標準寫法會放行 | QA 必填 `slv_manual_check`；症狀：機械半段放行過有缺陷的 AC 一次 → 修碼 |
| 舊 CLI 契約 | `transition` 與 `gate` 不是單行結構化 JSON（成功文字或 traceback） | 執行層預檢加事後驗證；症狀：對 `transition` 錯誤判讀出現一次誤判 → 採 FSM CLI 加 `--json` 的替代案（改 LATEST 的 CLI 與測試） |
| 狀態檔無跨行程鎖 | load-modify-save 沒有鎖（`SDD_AUTOCLAUDE_BRIDGE.md` 第 6.10 節）；外環鍵由執行層單行程寫 | 人在 hooks-ON 視窗與執行層同時寫同一鍵＝已知競態；一鍵一寫者 |
| HUMAN_PENDING 逾時守門 | 72 小時提醒、168 小時升級 ESCALATION 由 hooks 的 SessionStart 檢查執行（`.claude/hooks/session_start.py` 呼叫 `timeout_checker`）；產品（Console）路徑沒有 hooks，不會自動提醒或升級；Gate 0 等待超過 168 小時後在 hooks-ON 視窗開啟，該檢查會把外環鍵升為 ESCALATION | 裁決 D-48(3)：Console 路徑以 UI 顯示等待時長＋72h 橫幅、不轉 REMINDER，不新增 hook 或守衛（記入 Console 架構文件 §12.1 已知限制 L-R）；人手 hooks 路徑由人以第 2.5 節恢復；症狀：產品路徑要求逾時自動處置 → 另案設計，不在 hooks 內補丁 |
| 人手流程沒有驗證器 | 無執行層時 P0 預檢、schema 驗證、模糊度、UNANCHORED 都靠人逐條自檢 | 模板的自檢清單逐條勾；誠實標示「未經機器驗證」 |
| `sdd_env.py` 不認研究鍵 | `AISDLC_SDD/scripts/sdd_env.py` 的 `--sub` 只收四個子專案 | 研究鍵的三件組手動設定（第 13 章）；症狀：人手研究流程被使用兩次以上且三件組設錯一次 → 擴 `SUBS` |
| 軌道 B 的規格深度 | 裁決 D-48(2)：軌道 B 內環走完整 SCG-1～3，軌道 A 走增量條款；全新專案不適用增量條款，SCG-1～3 仍須完整清單（第 9.2 節第 5 點） | 症狀：Stage-2 TCS 以增量條款通過了一個沒有任何已凍結 SRD、ADR、OpenAPI 可追溯的全新專案 |
| 非 Python 標的 | evaluator 只收 `pytest`（`SDD_AUTOCLAUDE_BRIDGE.md` 第 7 節） | 軌道 B 範本只提供 Python；其餘技術棧警告「無凍結綁內容」；症狀：掌舵者要求其他技術棧 |
| 不抓 PDF | 見第 3.2 節 | 症狀：掌舵者要求納入必須讀 PDF 全文的來源 |

框架側整體的再開症狀（決策層面）見 `docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`。

---

## 12. Console／Bridge 對映（方法層與執行層的分工）

本章只寫分工與指標；**不複寫** Console 側的資料表與 API 形狀。

| 方法層概念 | 執行層（Console／Bridge）承擔 |
|------------|-------------------------------|
| stage 序列 `RESEARCH`、`DRAFT`、`REVIEW-k`（四角各一步）、`REVISE-k`；P1 另有 `TCS_DRAFT` | 以 AutoClaude run 當執行載體：一串短 stage run 加 Bridge 內的**確定性 orchestrator**；每步 `maintain_context: false`，步驟間只經檔案 |
| 契約驗證、P0 預檢、前置否決、聚合評分與判定、寫庫、呼叫 FSM | 全在 Bridge 的碼（不由 LLM 判斷）；審查者輸出不合 schema 時重試一次 |
| 外環鍵建檔與 FSM 寫入 | Bridge 的 FSM 動詞白名單擴充（`show` 建檔專用、受限 `transition`、`gate`〔四個閘：`SCG_VALIDATION`、`PR_REVIEW`、`RTM_VERIFY`、`RELEASE_READY`；`SCG_VALIDATION` 只用於外環鍵，其餘三閘只用於內環鍵；實際使用面見 `SDD_AUTOCLAUDE_BRIDGE.md` 第 9.2 節〕、`spec-refreeze`，既有 `spec-frozen`；**不含** `resume-from-escalation`），獨立寫入權杖；外環鍵的 CLI 環境固定 `SDD_ENABLE_AUTO_RECOVERY=0` |
| Gate 0 | 專用端點 `:approve-baseline`（stage 名 `Gate-0`，凍結文件集如第 8 章，不要求 TCS，前置 HUMAN_PENDING；`approver`＝登入者）；既有 `:freeze` 契約不改 |
| 人工退回、迴歸檢查、核准 | 核准畫面的「要求修改」落成 `gate SCG_VALIDATION FAIL`；有重試史時核准前自動先走 SPEC_REGRESSION_CHECK |
| 檔案與資料庫的關係 | 檔案是工作成品，資料庫是研發全程的入庫記錄與游標真相；`state.json` 非權威 |
| 抓取 | 預取層（學術、開源、社群 API）由 Bridge 以獨立 allowlist 抓取並記雜湊；Web 層預設關閉 |

權威文件（同輪落檔）：`AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md`、`AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md`、`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`；框架側的 Bridge 路徑條文見 [SDD_AUTOCLAUDE_BRIDGE.md](../sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md) 第 9 節。

---

## 13. 人手流程（沒有 Console 時；hooks-ON 視窗）

最小步驟（人是執行層）。三件組缺一不可、一個視窗一個功能、一律從 monorepo 根啟動、阻塞態逃生口＝第二終端跑恢復指令（`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.1～8.3、8.8 節）。PowerShell 形態（不裸 `cd`；`Push-Location`／`Pop-Location` 同呼叫成對；讀 rc 不接管線）；`$vd`、`$py`、`$ws`、`$slug` 在同一個視窗內沿用。

**步驟 1：建工作區與議題**

```powershell
$slug = 'pdf-export-engine'                                   # 小寫 kebab、≤30 字；外環鍵＝research-<slug>
$ws   = Join-Path $env:USERPROFILE ".autosdd\my-project\$slug"  # repo 外；路徑不得含 docs/01_requirements 等子字串
foreach ($d in '00_research\raw', '00_research\notes', '01_specs', '02_governance\reviews', '03_execution', 'build\reports\fsm', '.prompts') {
    New-Item -ItemType Directory -Force -Path (Join-Path $ws $d) | Out-Null
}
# 把 ISSUE-SCOPE-TEMPLATE.md 第 1 節的 JSON 區塊存成 $ws\00_research\issue_scope.json（UTF-8、LF）並填寫；research_id 填新產生的 GUID、rp_no 寫 RP-LOCAL
```

**步驟 2：三件組、建檔與議題攝取**（在 monorepo 根的 PowerShell 視窗；`claude` 之前完成）

```powershell
$root = (Get-Location).Path
$ver  = ((python AISDLC_SDD/scripts/sdd_version.py) -replace '^AISDLC_SDD_v', '').Trim()
$vd   = Join-Path $root "AISDLC_SDD\AISDLC_SDD_v$ver"; $py = Join-Path $root '.venv\Scripts\python.exe'
$env:SDD_ACTIVE_VERSION = $ver
$env:SDD_PROJECT        = "research-$slug"
$env:SDD_STATE_DIR      = Join-Path $ws 'build\reports\fsm'   # 絕對路徑；外環鍵的狀態目錄在研究工作區
$env:SDD_ENABLE_RULE_FIRE_TELEMETRY = '0'; $env:SDD_ENABLE_RULE_CATCH_TELEMETRY = '0'
$env:SDD_ENABLE_AUTO_RECOVERY = '0'                           # 外環鍵：審查分數不足不得被自動恢復
function sdd { & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime @args }
Push-Location $vd -ErrorAction Stop
$null = sdd show --project $env:SDD_PROJECT                   # 建檔：整個週期唯一不帶 --must-exist 的一次
sdd transition --project $env:SDD_PROJECT --must-exist --to SCENARIO_DETECT --reason "research topic ingested: $slug; scenario decided at route"
sdd transition --project $env:SDD_PROJECT --must-exist --to AGENT_LOAD --reason 'load research-analyst, spec-engineer, 4 reviewers'
Pop-Location
Test-Path (Join-Path $env:SDD_STATE_DIR "FSM-STATE-$($env:SDD_PROJECT).yaml")   # 必須 True
claude --add-dir $ws                                          # 讓 session 可讀寫工作區（工作區在 repo 外）
```

**步驟 3：研究**。在 session 內請 Claude 依 `agent/specialized/research-analyst-zh.yaml` 的角色與 `ISSUE-SCOPE-TEMPLATE.md`、`EVIDENCE-MATRIX-TEMPLATE.md` 執行：寫 `00_research/evidence_items.json`，並依模板第 4 節版式手寫 `evidence_matrix.md`；逐條自檢第 2.3 節 16 條規則（沒有驗證器，誠實標示「未經機器驗證」）。`issue_scope_sha256` 以步驟 5 的函式算出後交給研究者。

**步驟 4：起草與預檢**。依 `agent/specialized/spec-engineer-zh.yaml` 寫 `01_specs/PRD_draft.md`、`adr_draft.md`；人逐條核對模板第 0.2 節 P0-1～P0-9；通過後：

```powershell
Push-Location $vd -ErrorAction Stop
sdd transition --project $env:SDD_PROJECT --must-exist --to SPEC_DRAFTING --reason 'Stage Gate-0: PRD drafting v0.1.0-draft'
sdd transition --project $env:SDD_PROJECT --must-exist --to SCG_VALIDATION --reason 'SCG-0 對抗審查 round 1 開始'
Pop-Location
```

**步驟 5：四方審查與判定**。每位審查者各開**獨立** session（或 `claude -p`），任務書依審查卡模板第 8 節組裝（含 PRD 路徑與雜湊、輸出路徑，不含權重與門檻），輸出寫 `02_governance/reviews/round-1/<dimension>.json`。雜湊與加權由人以下列方式算（雜湊演算法與 `spec-frozen --digest` 相同：換行正規化後 UTF-8 的 SHA-256）：

```powershell
function Get-SpecSha256([string]$Root, [string]$Doc) {
    Push-Location $vd -ErrorAction Stop
    try {
        $out = & $py -W ignore::RuntimeWarning -c "import sys; from pathlib import Path; from tools.fsm_runtime.spec_digest import digest_doc; print(digest_doc(Path(sys.argv[1]), sys.argv[2])[1])" $Root $Doc
        return (($out | Out-String).Trim() -replace '^sha256:', '')
    } finally { Pop-Location }
}
$prdSha = Get-SpecSha256 $ws '01_specs/PRD_draft.md'                 # 審查者任務書的 prd_sha256；不含 sha256: 前綴
$A = 88; $P = 90; $Q = 84; $S = 92                                   # 四個維度的整數分（取自四份審查者 JSON）
$W100 = 30*$A + 25*$P + 25*$Q + 20*$S
"W100=$W100 weighted_total=" + ($W100 / 100).ToString('0.00') + " 達門檻=" + ($W100 -ge 8500)   # 另須四維皆 ≥60 且無未結 P1
```

**步驟 6：寫 gate**（第 2.6 節第 5～7 列）：通過 `gate … --result PASS`；未通過 `gate … --result FAIL --reason …`（第 3 次即 ESCALATION，進阻塞態：第二終端跑恢復指令）。FAIL 後回步驟 4 的修訂（`spec-engineer` 帶缺陷清單，不帶分數）。

**步驟 7：Gate 0**（人）。人讀 PRD、證據矩陣、審查卡後決定：要求修改＝第 2.6 節第 7 列；核准＝複製被核准草稿為 `01_specs/PRD-v1.0.0.md`（位元組相同），有重試史則先第 8 列，再第 9 列的 `spec-frozen`（`--root` 取 `$ws`、`--approver` 填人名）；然後在 session 內 `/stage-compaction`。

**步驟 8：分流**（第 9 章）：選軌道、建內環鍵、做 Stage-1 基線採納與 Stage-2 TCS，沿 `SDD_AUTOCLAUDE_BRIDGE.md` 第 8 節。收工關視窗（環境隨視窗清空）。

---

## 14. 相關文件

- 閘門與 FSM 寫入指令：[SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)；FSM 規格：[SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md)；退場：[SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md)
- Console／Bridge 與子專案 SDD session：[SDD_AUTOCLAUDE_BRIDGE.md](../sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md)（第 9 節為本工作流的 Bridge 路徑）
- 模板：`docs_template/sdd/requirements/ISSUE-SCOPE-TEMPLATE.md`、`EVIDENCE-MATRIX-TEMPLATE.md`、`PRD-SPEC-ENGINEERED-TEMPLATE.md`、`ADVERSARIAL-REVIEW-CARD-TEMPLATE.md`
- Agent：`agent/specialized/research-analyst-zh.yaml`、`agent/specialized/spec-engineer-zh.yaml`
- 憑證紀律：[EVIDENCE_DISCIPLINE.md](../../agent/EVIDENCE_DISCIPLINE.md)
- 決策記錄：`docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`（D1～D7）；測試契約：`docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md`
- Bridge 寫入面與框架側白名單：`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`（根層，同輪落檔）

**上位需求對照**（根層唯一 PRD：`docs/01_requirements/ResearchToPRD_PRD.md`；兩側並列見其 §11.2）：

| 本工作流 | 對應的 PRD 需求 |
|----------|----------------|
| 第 2 章 FSM 對映與預算 | PRD §5.1.1；FR-R2P-08（AC-R2P-08-2、08-3、08-9、08-10）；FR-R2P-10（AC-R2P-10-8） |
| 第 3、4 章 研究方法與證據錨定 | FR-R2P-03、FR-R2P-04、FR-R2P-05（AC-R2P-05-1～05-8） |
| 第 5 章 SE-PRD | FR-R2P-07（AC-R2P-07-1～07-4） |
| 第 6、7 章 審查與迭代 | FR-R2P-08（AC-R2P-08-1～08-10）；FR-R2P-09（AC-R2P-09-5） |
| 第 8 章 Gate 0 | FR-R2P-10（AC-R2P-10-1、10-7、10-9） |
| 第 9 章 分流與 SCR | FR-R2P-11～14；FR-R2P-19（AC-R2P-19-1～19-8） |
| 第 10 章 產物與目錄 | FR-R2P-02、FR-R2P-03（AC-R2P-03-1、03-6） |
| 第 11、12 章 邊界與對映 | NFR-R2P-03、NFR-R2P-11；PRD §11.2 |
