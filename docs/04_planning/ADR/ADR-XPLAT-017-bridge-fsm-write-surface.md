輸入快照：HEAD＝01d9be6e；主控裁決 D-01～D-66

# ADR-XPLAT-017：Bridge 研究寫入面——雙鍵模型、FSM 動詞擴充、Gate-0 端點、框架側白名單

- **狀態**：**定稿候選 v1.0.0-rc3**（SCG-0 獨立審查後由主控依〈凍結常態規則〉凍結為 Accepted；本檔是設計文件，不含任何生產碼；§7 的白名單是框架鍵 `sdd-research-to-prd` 的施工授權範圍）。
- **日期**：2026-11-02
- **平台**：平台中立（Windows 11＋PowerShell 為主控機；Bridge 子行程環境逐項寫在 §4）
- **關聯**：PRD `docs/01_requirements/ResearchToPRD_PRD.md`（FR-R2P-08、10、11、19）；`AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md`（D13）；主控裁決 D-21～D-26、D-38、D-41、D-45～D-47、D-49、D-50、D-60、D-64；[ADR-XPLAT-016](ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md) §3.5（動詞白名單列）與 §11（最小侵入白名單）；AISDLC_SDD Rule 9（R-9.1、R-9.5、R-9.6）、`SDD_AUTOCLAUDE_BRIDGE.md` §6.8、§8
- **修訂對象**：**補充**（不取代任何決策）ADR-XPLAT-016 §3.5 的「動詞白名單」列與 §11；`AgentConsole/CLAUDE.md` 鐵律 7 的白名單句加本檔 §D7 的引用。**ADR-XPLAT-016 §11 本文不改**（已 Accepted，D-38）。
- **證據**：讀碼座標（落地時行號會漂，動手前各自重取）——`engine-bridge/app/sdd_cli.py:61-74,115-124,165-167`、`app/routers/sdd.py:300-364`（`:freeze` 的 `missing_tcs` 於 :313-316，主控親驗 :315、:342）、`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/transition_rules.py:12-35,267-275,305-326`（主控親驗）、`fsm_runtime.py:526-645`（`record_gate_result`）、`:596-620`（自動恢復）、`:703-769`（`spec-refreeze`）、`:3585-3600`（`spec-frozen`）。**本檔未跑任何 FSM 寫入動詞**；附錄 A 與 §5 的指令序列由 P0／P1 的暫存狀態目錄實跑落證（V-R6、V-R7）。

---

## 1. 脈絡

ADR-XPLAT-016 §3.5 把 Bridge 對 FSM 的寫入收斂為 5 個動詞（`spec-frozen`、`negotiate-enter`、`negotiate-exit agreed`、`delegate-enter`、`delegate-exit`）且每次帶 `--must-exist`。ResearchToPRD 的 Phase 0（研究→PRD→四方審查→Gate 0）要在 FSM 上走 SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING→SPEC_FROZEN，現況有三個缺口：(1) Bridge 沒有 `transition`／`gate`、無法建狀態檔；(2) `:freeze` 強制 `docs[]` 含 TCS（`routers/sdd.py:313-316`），Gate 0 時只有 PRD；(3) 單一 FSM 鍵無法同時滿足「研究工作區與目標無關」與「軌道 A 沿用子專案狀態目錄」（adapter 以「向上找含 `build/reports/fsm` 的目錄」定位狀態檔，BRIDGE §8.11:593-596）。本 ADR 以**最小**擴充補上，不新增任何 FSM 狀態或邊、不碰 `_HAPPY_PATH`／`formal/`（Rule 9 禁令 8）。

## 2. 決策總覽

| 編號 | 決定（摘要） | 落點 | 本檔節 |
|------|-------------|------|--------|
| D1 | 兩把 FSM 鍵：外環 `research-<slug>`（狀態目錄＝研究工作區 `build/reports/fsm`）、內環 `<sub>-<slug>`（目標專案標準狀態目錄） | Bridge `fsm_ops.py`、DB 互指 | §3 D1 |
| D2 | Bridge FSM 動詞白名單擴充：唯一建檔點（`show`）、受限 `transition`、`gate`（四個閘）、`spec-refreeze`；`resume-from-escalation` **不入** | `sdd_cli.py` 研究面 | §3 D2 |
| D3 | Gate 0 載具＝新端點 `POST /research/projects/{id}:approve-baseline`（Stage 名 `Gate-0`、不要求 TCS）；既有 `:freeze` 不動 | Bridge 研究路由模組（新增，`app.routers.research`） | §3 D3 |
| D4 | 外環鍵的 CLI 環境固定 `SDD_ENABLE_AUTO_RECOVERY=0` | Bridge 子行程環境 | §3 D4 |
| D5 | SCR 三路：MINOR（外環重走 Stage＋內環 SPEC_AUDIT／`spec-refreeze`）、MAJOR（新研究專案）、自癒耗盡（人手 `resume-from-escalation`） | Bridge `scr.py` | §3 D5、附錄 A |
| D6 | 預算語意採 FSM 預算：`SCG_VALIDATION` 3 次 FAIL＝ESCALATION＝最多 3 輪審查；不改 `RETRY_LIMITS`／`formal/`；ESCALATION 人工恢復後不歸零（至多再得一次審查），全新預算＝換世代（D-60） | FSM 既有 | §3 D6 |
| D7 | 框架側白名單：`sdd-research-to-prd` 鍵視窗可改的 LATEST 檔清單與機械核對法 | `AISDLC_SDD/<LATEST>` | §3 D7 |

## 3. 逐項決策

### D1　兩把鍵（為何不是單鍵）
| | 外環鍵 R（研究／PRD） | 內環鍵 I（實作） |
|--|---------------------|-----------------|
| 鍵名 | `research-<slug>`（換世代：`research-<slug>-g2`） | 軌道 A：`<sub>-<slug>`（`sub`∈autoclaude／agentconsole／sdd／monorepo，BRIDGE §8.0:341）；軌道 B：`<project-name>` |
| 狀態目錄 | `<BRIDGE_RESEARCH_ROOT>/<slug>/build/reports/fsm`（工作區內；目標未定時唯一可用） | 目標專案根的 `build/reports/fsm`（BRIDGE §8.1:353-358；Bridge 固定讀 `<execution_path>/build/reports/fsm`，ADR-XPLAT-016 §3.5:172） |
| 生命週期 | INIT→…→SPEC_FROZEN（Gate 0）；之後只在 SCR 時回 SPEC_DRAFTING（`transition_rules.py:35`） | Stage-1 基線採納→Stage-2 TCS→IMPLEMENTATION→…→RELEASE（終態，`:78`） |
| 建檔者 | Bridge `POST /research/projects`（**唯一建檔點**；換世代時由 `:reinit` 的 `generation:"next"` 模式建新世代鍵，同屬建檔例外，D-60） | Bridge `:route`（同一建檔例外） |
| 連結 | DB：`research_projects.fsm_project`／`fsm_state_dir`；`research_route_decisions.impl_fsm_project`／`impl_state_dir`；內環 Stage-1 的 `--reason` 引外環 `gate_decisions.id` 與 PRD sha256 | 同左 |
- **決策**：各守「一個狀態目錄、一個功能週期」（BRIDGE §8.0:340）。
- **替代案**：單鍵（狀態目錄在工作區或在目標）。
- **WHY**：單鍵必須讓狀態目錄＝工作區（才不依賴目標），但引擎 adapter 以「向上找含 `build/reports/fsm` 的目錄」定位狀態檔（BRIDGE §8.11:596；`routers/sdd.py:382-387` 同走法），而軌道 A 的 TCS 必須住目標 `docs/03_testing/contracts/`（`AgentConsole/CLAUDE.md` 文件索引、BRIDGE §8.5:525）——spec_dir 的祖先裡找不到工作區的狀態目錄 ⇒ 內環整條斷。
- **再開症狀**：兩鍵的 DB 互指出現一次不一致（`:reconcile` 報 drift）；或 BRIDGE §8.11 的 adapter 定位法改變。

### D2　FSM 動詞白名單擴充（研究面）
現況允許：`spec-frozen`、`negotiate-enter`、`negotiate-exit`（`--outcome agreed`）、`delegate-enter`、`delegate-exit`；`build_cli_argv` 恆附 `--must-exist`（`sdd_cli.py:165-167`）；越界一律 500 `sdd_cli_usage`（`:115-124`）。**實作形態（D-49）**：以下動詞放在 `sdd_cli.py` **新增的獨立表** `RESEARCH_VERBS`（動詞規格，含是否附 `--must-exist`）與 `sdd_cli._RESEARCH_VERB_FLAGS`（動詞→旗標白名單），由專用組裝路徑（只查這兩張表）建構 argv；既有 `ALLOWED_VERBS`（`:61`）、`sdd_cli._VERB_FLAGS`（`:67`）、`build_cli_argv` 與 `AgentConsole/engine-bridge/tests/test_sdd_cli.py` **零改動**，既有 AT 不退步。新增（**全部以研究寫入面限定：獨立權杖 `BRIDGE_RESEARCH_WRITE_TOKEN`、獨立端點，不開放給 `:freeze` 或 `/autoclaude/runs` 的 `sdd` 區塊**）：

| 動詞 | 旗標白名單 | 值域限制 | 契約形態 | Bridge 包裝要點 |
|------|-----------|---------|---------|----------------|
| `show`（**建檔專用**） | `--project` | 唯一不帶 `--must-exist` 的呼叫；僅三個呼叫點：①`POST /research/projects`（鍵須符合 `^research-[a-z0-9][a-z0-9-]{0,29}(-g[0-9]+)?$`）②`:reinit` 的換世代模式（D-60；鍵＝`research-<slug>-g<N+1>`，N＝DB 的 `fsm_generation`，同一鍵名文法）③`:route`（鍵須等於 DB 已記錄的 `impl_fsm_project`、目錄＝`impl_state_dir`）；目錄須在 allowed roots 且為 `…/build/reports/fsm` | 舊（多行 JSON） | 事後以 `read_state` 直接讀驗 `INIT`；建檔前檔已存在⇒409 |
| `transition` | `--to`、`--reason`、`--trigger` | `--to`∈{SCENARIO_DETECT, AGENT_LOAD, SPEC_DRAFTING, SCG_VALIDATION, SPEC_REGRESSION_CHECK, SPEC_AUDIT, PR_REVIEW, RELEASE, HUMAN_PENDING〔僅內環鍵採納路徑：現態須為 SCG_VALIDATION 且 `--reason` 以 `baseline adoption` 起頭〕}；外環鍵只准前五值；`--trigger` 固定 `research_bridge` | **舊**：成功 stdout `OK transitioned to X`；非法＝traceback rc 1（`SDD_SPEC_FIRST_GATE.md:208-209`；`fsm_runtime.py:3684-3692`） | 先 `read_state` 預檢「現態→目標」在 `is_transition_allowed` 內（Bridge 內鏡像邊表＋對拍測試），再呼叫；事後再讀驗；不解析 stderr 文字 |
| `gate` | `--gate`、`--result`、`--reason` | `--gate`∈{SCG_VALIDATION, PR_REVIEW, RTM_VERIFY, RELEASE_READY}（D-23）；`--result`∈{PASS, FAIL}；`--reason` 必填；`SCG_VALIDATION` 只用於外環鍵，其餘三閘只用於內環鍵。**使用面（D-45）**：外環鍵 `SCG_VALIDATION` 由審查 evaluator（自動 FAIL／PASS）與 ADMIN 人工退回（FAIL）呼叫；內環鍵 `PR_REVIEW`／`RTM_VERIFY`／`RELEASE_READY` 由 Console `POST …/gates`（ADMIN，P2）登錄 SCG-4／SCG-5／CI 結果時呼叫，P0／P1 不呼叫。**守則（D-50）**：外環鍵現態為 HUMAN_PENDING 時不呼叫 `gate SCG_VALIDATION PASS`（見 D6） | 舊但 stdout 為單行 JSON（`fsm_runtime.py:3693-3700`） | 取回傳 `next_state`／`retry_count`／`escalated`，**以回傳為準、不自建計數** |
| `spec-refreeze` | `--doc`（多）、`--root`、`--reason`、`--approver` | 同 `spec-frozen`；`--project` 必填；僅 SCR 用 | 新（結構化 JSON，`fsm_runtime.py:3431`） | `--approver` 取 JWT subject |
| `spec-frozen`（既有） | 既有 | `--stage` 研究面限 `Gate-0`、`Gate-0-SCR<n>`、`Stage-1` | 既有 | `:approve-baseline` 與 `:route` 呼叫；**放寬 `missing_tcs` 只在這兩個端點內**，不改 `:freeze` |

**不新增**：`resume-from-escalation`、`reconcile`、`spec-audit`、`check-impl`、`complete-auto-compact`、`reset-ledger`、`negotiate-exit underspecified`。
- **決策**：以上為白名單的全部；單一寫入面（CLI 子行程）、表驅動測試釘住。
- **替代案**：(1) 在 `:freeze` 內放寬 TCS 規則（改一個已凍結契約＋二個既有 AT）；(2) 只在 Gate 0 時事後補寫 FSM（失去有界停機與即時軌跡）；(3) 給 `transition`／`gate` 加框架 CLI `--json`（動 LATEST 的 CLI，更乾淨但要改 CLI 與測試，**本案不採**，列再開症狀）；(4) 單鍵（見 D1）。
- **WHY**：每個替代案的具體失敗座標見 D1 與 `routers/sdd.py:313-316`；`transition`／`gate` 是舊 CLI 契約（非單行 JSON），故 Bridge 採「預檢＋事後驗證」而不解析 stderr。
- **再開症狀**：Bridge 對 `transition` 的錯誤判讀出現一次誤判（→ 採替代案 3）；掌舵者要求 Console 內恢復 ESCALATION（→ 需修憲：Rule 9 禁令 6）。

### D3　Gate 0 載具：`POST /research/projects/{id}:approve-baseline`
- **決策**：新端點（Stage 名 `Gate-0`；`docs[]`（相對 `--root`＝研究工作區）＝`<工作區>/01_specs/PRD-v1.0.0.md`＋`<工作區>/00_research/evidence_matrix.md`＋`<工作區>/00_research/issue_scope.json`＋`<工作區>/01_specs/adr_draft.md`，**不要求 TCS**；`--digest --root <工作區>`）。檢查序（先中者定案）：①權杖 ②`prd_version` 為 head 且有 `passed=true` 的審查輪（否則 409 `review_not_passed`；Bridge 以版號為憑——最後一輪審查通過、其 `prd_version_no` 等於最新 DRAFT 版號、且 `prd_version` 等於該版號；前端另以 prd sha256 判「審查是否過期」只作提示，兩判準並存、以 Bridge 為權威；D-83）③`expected_digests` **只比對送來的鍵**（至少一鍵，零鍵 422 `missing_digests`；不符 422 `digest_mismatch`，`details.files[{key,expected,current}]`；缺鍵不算錯——四份文件的摘要一律由 `spec-frozen --digest --root` 於凍結當下自工作區計算並記入凍結記錄；D-72）④FSM 現態＝HUMAN_PENDING（否則 409 `fsm_state_conflict`，帶 `expected_state`；ESCALATION 時 409 `escalated`）⑤〈外環鍵有重試史 `retry_history.SCG_VALIDATION.current_count>0`〉先 `transition --to SPEC_REGRESSION_CHECK`（規則＝`SDD_FSM_ENGINE.md:374-378`、`SDD_SPEC_FIRST_GATE.md:210-213`；D-25）⑥`spec-frozen --stage Gate-0 … --approver <JWT subject> --json`。`approver`＝JWT subject，由 console-api 轉傳，Bridge 驗非空、非保留字（`bridge`／`agent`／`system`）、長度 1 至 100 且符合 `^[A-Za-z0-9._@-]+$`；**任何 agent、Bridge 排程或 CLI 不得呼叫本端點**（D-19；AST 鎖）。核准後 `PRD-v1.0.0.md` 為核准當下 head 版本的位元組相同複本；非冪等（第二次 409 `fsm_state_conflict`）；既有 `:freeze` 契約（`routers/sdd.py:336-364`）不改、留給 Stage-2 TCS 凍結。
- **替代案**：在 `:freeze` 放寬 `missing_tcs`；Gate 0 改走 headless SDD session。
- **WHY**：D-06 要的語意（`spec-frozen`）不變，只換載具；放寬限定在新端點內可使既有 AT 不退步。
- **再開症狀**：Gate 0 的 `frozen_stages[-1].spec_doc_digests` 與 `research_gate_decisions.frozen_digests` 出現一次不一致。

### D4　外環鍵關閉自動恢復
- **決策**：外環鍵的每一次 CLI 呼叫環境固定 `SDD_ENABLE_AUTO_RECOVERY=0`（`fsm_runtime.py:596-620`：預設 ON 時 gate 耗盡會先 `enter_auto_recovery`）；內環鍵沿既有行為。測試釘住：第 3 次 `gate SCG_VALIDATION FAIL` 後現態＝ESCALATION，**不是** AUTO_RECOVERY_ATTEMPT／ESCALATION_FINAL。
- **WHY**：審查分數不足不得被自動恢復（R-9.5／禁令 6、7）。
- **再開症狀**：外環鍵出現 AUTO_RECOVERY_ATTEMPT 一次（環境被洩漏或被覆寫）。

### D5　SCR 三路（不改 `_HAPPY_PATH`）
事實：IMPLEMENTATION／PR_REVIEW／RTM_VERIFY 沒有回 SPEC_DRAFTING 的邊（`transition_rules.py:46,66,68`）；SPEC_AUDIT 唯一出邊是 PR_REVIEW（:67）；SPEC_FROZEN→SPEC_DRAFTING 是合法邊（:35）。
- **MINOR**（規格文字／AC 缺陷，證據與前提不變）：外環鍵 SPEC_FROZEN→SPEC_DRAFTING（Stage `Gate-0-SCR<n>`）重走起草／審查／gate 迴圈（預算重新計：`spec-frozen` 對四個閘一併歸零，`state_loader.py:305-308`）→ ADMIN 核准 `spec-frozen --stage Gate-0-SCR<n>` → 內環鍵 `transition →SPEC_AUDIT`（允許寫規格檔的態，BRIDGE §8.3 第 3 點）→ 發佈新 PRD 到目標 `docs/` → `spec-refreeze` → `transition →PR_REVIEW` → `gate PR_REVIEW FAIL`（回 IMPLEMENTATION）；內環現態矩陣見附錄 A。裸 `transition →SPEC_AUDIT` 不累加 `spec_audit_count`（只有 `record_spec_audit` 累加，`fsm_runtime.py:647-673`；上限 `SPEC_AUDIT_MAX_PER_STAGE=2`，`transition_rules.py:282`），故 **Console 層自設同值：同 Stage 內 MINOR ≤2，第 3 次強制改 MAJOR**。`gate PR_REVIEW FAIL` 的「同模式」判準若把相鄰 SCR 的 reason 判為同模式 ≥3 次會改走 SPEC_AUDIT（:325-326）：Bridge 讀 `next_state`，≠IMPLEMENTATION 即回報 `BLOCKED` 交人處置、不重試。
- **MAJOR**（研究前提被推翻）：新 `research_projects` 列（`parent_research_id`、slug `<slug>-scr<N>`、新外環鍵）重走 Phase 0；舊內環鍵**不動**（Console 標「已被取代」，不自動 `TERMINATED`——它是毀滅性終態且 hooks-ON 窗下是阻塞態，BRIDGE §8.8:557）。
- **來源是 SCG-4／自癒耗盡**（HUMAN_ESCALATION #2）：內環 ESCALATION 由人恢復（`resume-from-escalation --to IMPLEMENTATION`，BRIDGE §6.8）；若人判斷需改規格，恢復目標可選 `SPEC_DRAFTING`（`RESUME_TARGETS`，`fsm_runtime.py:41`、`transition_rules.py:160`）——**唯一**能從內環回到 SPEC_DRAFTING 的合法路，且必須人手（R-9.5）。Console 的 SCR 鈕在此情境只產生指令與記錄，不代跑。
- **替代案**：改 `_HAPPY_PATH` 加 IMPLEMENTATION→SPEC_DRAFTING（需同步 TLA+，R-9.18，不建議）；SCR 一律新研究專案（小修成本過高）。
- **再開症狀**：MINOR 序列在 `gate PR_REVIEW FAIL` 一律被判同模式；或 SCR 後舊內環鍵的殘留造成混淆。

### D6　預算語意：採 FSM 預算
- **決策**：`record_gate_result` 對 FAIL **先** `increment_retry` 得 `new_count`（`fsm_runtime.py:546-547`），再 `next_state_on_gate_fail(gate, new_count)`：`new_count >= limit`→ESCALATION，否則 SCG_VALIDATION→SPEC_DRAFTING（`transition_rules.py:305-326`；`RETRY_LIMITS["SCG_VALIDATION"]=3`，:267-275）。PASS 時 `reset_retry`。故**最多 3 輪審查（首審＋2 次自動修訂）**；人工「退回修改」＝`gate SCG_VALIDATION FAIL --reason "人工審查：…"`，與自動 FAIL 共用此預算（FSM 沒有 HUMAN_PENDING→SPEC_DRAFTING 的邊，`SDD_SPEC_FIRST_GATE.md:194`；被擋的轉態記 `gate_fail_blocked`，`fsm_runtime.py:628-641`）。不用裸 `transition SCG_VALIDATION→SPEC_DRAFTING` 規避（邊雖合法，:27，但不記次數＝繞過 R-9.1、絕對禁令 4）。

  | 審查輪 | 結果 | `gate` | `current_count` | 轉態 | Console 相態 |
  |--------|------|--------|-----------------|------|-------------|
  | 1（首審） | 未過 | FAIL | 1 | SCG_VALIDATION→SPEC_DRAFTING | `REVISING`（自動修訂 1） |
  | 2 | 未過 | FAIL | 2 | →SPEC_DRAFTING | `REVISING`（自動修訂 2） |
  | 3 | 未過 | FAIL | 3（≥3） | →**ESCALATION** | `ESCALATED` |
  | 任一 | 通過 | PASS | 歸 0 | →HUMAN_PENDING | `GATE0_PENDING` |
  | 人工退回（現態 HUMAN_PENDING） | 人工要求修改 | FAIL | ＋1 | **態不動**（仍 HUMAN_PENDING；被擋的轉態記 `gate_fail_blocked`；累計第 3 次→ESCALATION） | `GATE0_PENDING`（PRD 回可編輯；第 3 次→`ESCALATED`） |
- **ESCALATION 人工恢復後（D-60）**：引擎事實——`resume-from-escalation` 只轉 `ESCALATION→RESUME_VERIFICATION→<to>` 並回填 `escalation_history`，**不動 retry 計數**；只有 `gate PASS`（`reset_retry`）與 `spec-frozen` 歸零（`fsm_runtime.py:526-645`、`state_loader.py:271-308`）；`increment_retry` 見 `prior ≥ limit` 時把 `current_count` 夾在上限並在歷史列標「(tamper detected …)」（`state_loader.py:211-269`）。故人工恢復後 `current_count` 仍為 3：

  | 事件 | `gate` | `current_count` | 轉態 | Console 相態 |
  |------|--------|-----------------|------|-------------|
  | 人工 `resume-from-escalation --to SPEC_DRAFTING` | （無） | 3（不變） | ESCALATION→RESUME_VERIFICATION→SPEC_DRAFTING | `REVISING`；剩餘預算 `max(0, 3 − 3)`＝0，標「恢復後僅一次機會」 |
  | 恢復後的審查輪：通過 | PASS | 歸 0 | →HUMAN_PENDING | `GATE0_PENDING` |
  | 恢復後的審查輪：未過 | FAIL | 3（夾在上限） | →**ESCALATION**（立即；歷史列帶引擎的 tamper 字樣＝已知邊界，Architecture §12.1 L-R12） | `ESCALATED` |

  即每次人工恢復至多再得**一次**審查（PASS 歸零、FAIL 立即再 ESCALATION），不是再得三輪；`iterate` 在恢復後只跑一輪（迴圈續停取每輪 `gate` 回傳的 `next_state`／`escalated`，Bridge 不以 `3 − current_count` 自算）。**全新預算**＝換世代鍵 `research-<slug>-g<N+1>`（框架工作流第 2.5 節既有路徑；舊鍵永遠停在 ESCALATION、不被恢復——這是放棄，不是恢復，R-9.5 不受影響）：Console 的 ESCALATION 區塊提供「換世代」鈕（**僅 ADMIN**，D-64：`SecurityConfig` 的 matcher 無法依請求本文分流，所以角色檢查分兩段：VIEWER 由既有授權鏈擋下〔403 `ACCESS_DENIED`〕，OPERATOR 通過授權鏈後由 console-api 的 `ResearchCommandService` 在服務層擋下〔403 `research_write_forbidden`〕，兩者 Bridge 請求數 0），經 `POST …/reinit` 的 `generation:"next"` 模式，Bridge 先於單一交易寫 `research_gate_decisions(gate=ABANDON_KEY, decision=ABANDONED)`、`fsm_generation`＋1 並改指 `fsm_project`，再以 §D2 的 `show` 建檔例外（第三個呼叫點）建新鍵並走到 AGENT_LOAD；`resume-from-escalation` 仍不入白名單。
- **輪列與 `gate` 呼叫一一對應（D-57）**：審查輪列只在輪有結果、`gate` 已回傳之後才寫入（取消、中斷、輸出無效一律不寫、不佔 `round_no`、不耗預算），故 `round_no`＝已完成評估的序號，與上表每一次審查輪的 `gate` 呼叫一一對應；人工退回列是 `gate FAIL` 但不是審查輪，POST_HUMAN 通過輪不呼叫 `gate`。
- **HUMAN_PENDING 守則（D-50；主控親驗 `fsm_runtime.py:526-645`、`SDD_SPEC_FIRST_GATE.md:194,210-213`）**：外環鍵現態為 HUMAN_PENDING 時，Bridge **不呼叫 `gate SCG_VALIDATION PASS`**——PASS 路徑直接 `transition(HUMAN_PENDING)`（無 try／except），而 HUMAN_PENDING→HUMAN_PENDING 不是合法邊，會以 traceback 結束（rc 1）。因此：人工退回後的再審「通過」只記 DB（`trigger_kind=POST_HUMAN`）並等 ADMIN 核准、不呼叫 `gate`；再審「未通過」仍呼叫 `gate SCG_VALIDATION FAIL`（態不動、計數＋1），使預算有界；核准時若有重試史，先 `transition --to SPEC_REGRESSION_CHECK` 再 `spec-frozen`（框架 SOP 補充條）。測試鎖見 §5（暫存狀態目錄實跑的兩個負控）。
- **替代案**：保留來源「3 次修訂＝4 輪」→ 須改 `RETRY_LIMITS` 與 `formal/`（動 TLA+，不建議）。
- **WHY**：來源 §5 的 `score_lt_85_retry_le_3`／`retry_gt_3` 字面可讀成 4 輪；D-24 採 FSM 既有預算，PRD 字面據此改寫。
- **再開症狀**：掌舵者要求第 4 輪審查（須先改 `RETRY_LIMITS` 與 TLA+）。

### D7　框架側白名單（`sdd-research-to-prd` 鍵視窗）
> 供 `AgentConsole/CLAUDE.md` 鐵律 7 引用的**擴充句**：「`AISDLC_SDD/<LATEST>` 內，只有鍵 `sdd-research-to-prd` 的 hooks-ON 視窗可依 ADR-XPLAT-017 §D7 清單原地修改；AgentConsole 三鍵（`agentconsole-research-to-prd-p0|p1|p2`）的開發 agent 一律不得動框架樹；ADR-XPLAT-016 §11 不改。」

- **鍵與視窗**：`sub=sdd`，狀態目錄 `AISDLC_SDD/AISDLC_SDD_v<LATEST>/build/reports/sdd-dogfood`（BRIDGE §8.1:358）；hooks-ON 視窗一次只綁一個功能（BRIDGE §8.3:467-470）；專案層文件寫版本目錄 `docs/`（不是根層 `docs/`）。
- **可改檔（相對 `<SDD>`＝`AISDLC_SDD/AISDLC_SDD_v<LATEST>`）**：`<SDD>/workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`（新）；`agent/specialized/{research-analyst,spec-engineer}-zh.yaml`（新）；`docs_template/sdd/requirements/{ISSUE-SCOPE,EVIDENCE-MATRIX,PRD-SPEC-ENGINEERED,ADVERSARIAL-REVIEW-CARD}-TEMPLATE.md`（新）；`<SDD>/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`（新）；`<SDD>/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-<日期>.md`（新；框架鍵**沒有自己的 PRD**，唯一 PRD＝根層 `docs/01_requirements/ResearchToPRD_PRD.md`，框架 TCS 直接引 FR-R2P／AC-R2P 追溯；D-41）；`AISDLC_SDD_INIT.md`（`auto_load_config` 兩支 agent、Agent 清單 21→23、Workflow 清單、模板索引）、`workflow/README.md`、`agent/specialized/README.md`、`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`（Stage-0 命名 `Gate-0` 與 SCR 條文、SCG-0 評分卡為其評估器）、`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`（§8.0 鍵前綴表加 `research`、新 §9）、`scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`、`scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`（各一段指標）、`EVOLUTION_LOG.md`、`releases/CHANGELOG.md`（只增條目，含頂部「最後更新」行）；**D-47 增列**：`docs_template/README.md`（計數、需求類清單、更新歷史）、`agent/README.md`（計數句訂正——保留原文逐字、補列 `sdd-zero-trust-auditor` 與本鍵兩支 agent）、`guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md`（Workflow 23→24）；版本目錄**之外**（白名單內）：`AISDLC_SDD/CLAUDE.md`（三處：Rule 2 目錄樹一句、〈框架核心文件快速參考〉一列、Rule 6 Agent 表補兩列）、`AISDLC_SDD/FRAMEWORK_STATUS.md`（`framework_status_snapshot.py --write` 重生，**同 commit 最後一步**）；另 `AISDLC_SDD/scripts/framework_status_snapshot.py` 的 curated 組成字串加 `+1 Research-to-PRD`（**主控做**；`scripts/**` 本在機械核對例外）。
- **不動**：`governance/rules/R-*.yaml`、`tools/fsm_runtime/**`（含 `transition_rules.py`、`formal/`）、`.claude/skills/**`、`.claude/settings.json`、`PRD_Universal_Template.md`；不新增 skill、不新增 scenario、不新增 `R-*.yaml`、不在框架內放網路或 DB 程式。
- **機械核對法**（`<起點>`＝框架鍵開工前的 commit，由主控記錄）：`git diff --name-only <起點> HEAD -- AISDLC_SDD` 的輸出，除 `AISDLC_SDD/scripts/**`、`AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD/FRAMEWORK_STATUS.md`、`AISDLC_SDD/.claude/**` 與 LATEST 目錄外必須為空（同 ADR-XPLAT-016 §11.3:598）；`git diff <起點> HEAD -- 'AISDLC_SDD/*/tools/fsm_runtime/transition_rules.py' 'AISDLC_SDD/*/tools/fsm_runtime/formal'` 必須為空（`_HAPPY_PATH` 不變 ⇒ 免跑 TLC）；根層 diff 只准含主控收尾單窗的 W0 連動檔：`.gitignore`、`.github/workflows/agentconsole-ci.yml`（只有 `paths`）、`docs/01_requirements/ResearchToPRD_PRD.md`、`docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`、`docs/01_requirements/Agent_ConsoleUI_PRD.md`、`docs/04_planning/ADR/ADR-XPLAT-016-…`／`ADR-XPLAT-017-…`、`AgentConsole/**` 文件；`tools/`、`.claude/` 必須為空（D-46；框架 TCS 的 `$rootExempt` 與此清單逐字同步）。
- **替代案**：把新檔逐一補進 ADR-XPLAT-016 §11 白名單（改已 Accepted 的 ADR，耦合大）。
- **再開症狀**：框架鍵視窗被發現改了清單外的檔（`git diff --name-only` 非空）。

## 4. Bridge 子行程環境（沿 ADR-XPLAT-016 §3.5:166-178，加研究面差異）

| 變數 | 值 | 備註 |
|------|----|------|
| `SDD_STATE_DIR` | 外環＝`<工作區>/build/reports/fsm`；內環＝`<目標根>/build/reports/fsm`（絕對路徑） | 相對路徑 rc 4（ADR-XPLAT-016 §3.2） |
| `SDD_PROJECT` | 鍵 | |
| `SDD_ENABLE_RULE_FIRE_TELEMETRY`／`…CATCH…` | `0` | 沿用 |
| **`SDD_ENABLE_AUTO_RECOVERY`** | **`0`（僅外環鍵的呼叫）** | D4 |
| `PYTHONPATH`／`PYTHONUTF8`／`PYTHONDONTWRITEBYTECODE` | `<SDD>`／`1`／`1` | 沿用 |
| 其餘 | 移除所有 `BRIDGE_*`、`SDD_*`、`PYTHONPATH` 後再設 | 權杖不進子行程 |
| 研究 stage run 的引擎子行程（非 FSM CLI；`ResearchRunHandle._child_env`） | 剝除 `BRIDGE_*`、`SDD_*`、`MINIMAX_*` 三個前綴與 `PYTHONPATH`、`GITHUB_TOKEN`、`GH_TOKEN`、`GH_ENTERPRISE_TOKEN`；請求 `config_overrides` 釘 `minimax.enable_kernel_brain=false` | D-79：研究 run 的判定全由 gate_cli evaluator 承擔，引擎 Brain 外呼既是資料出口也是無意義延遲；兩道各自獨立釘（環境剝除與設定釘關）；失敗路徑走規則引擎、零外呼 |
| cwd／逾時／序列化 | `<SDD>`／20 s／以 `(狀態目錄, 鍵)` 為鍵的互斥鎖 | 沿用；子行程一律經 `procutil.popen_platform_kwargs()` |

## 5. 測試鎖

- `AgentConsole/engine-bridge/tests/test_sdd_cli.py`：既有動詞表照舊釘住、**零改動**（D-49）；新增測試模組 `tests.test_research_sdd_verbs`（Bridge `tests/` 目錄）：`RESEARCH_VERBS`／`sdd_cli._RESEARCH_VERB_FLAGS` 的 verb／旗標／值域表驅動測試（含 `transition --to` 依鍵的矩陣、`gate --gate` 依鍵的矩陣）。
- 鏡像邊表對 `transition_rules._HAPPY_PATH` 的對拍測試（`SDD_ROOT` 存在才跑，否則 skip 並標 TOOL-ABSENCE）。
- AST 鎖：Bridge 原始碼不直接寫 `FSM-STATE-*.yaml`；沒有任何程式路徑呼叫 `:approve-baseline`／`spec-frozen --stage Gate-0`（唯一入口＝帶權杖的 HTTP 請求）；子行程只經 `procutil` helper。
- 環境測試：外環鍵呼叫的子行程環境含 `SDD_ENABLE_AUTO_RECOVERY=0`、不含任何 `BRIDGE_*`。
- 暫存狀態目錄實跑（V-R6／V-R7，腳本見計畫書）：第 3 次 FAIL 後現態＝ESCALATION；`spec-frozen --stage Gate-0 --digest --root <暫存根>` 的 `frozen_stages[-1].spec_doc_digests`。
- HUMAN_PENDING 守則負控（D-50）：暫存狀態目錄的外環鍵在 HUMAN_PENDING 時，`gate SCG_VALIDATION FAIL` 態不動且 `retry_count` 恰＋1（trace 記 `gate_fail_blocked`）、連續第 3 次＝ESCALATION；`gate SCG_VALIDATION PASS` rc≠0（證明守則必要）；AST 鎖：研究面對 `gate … PASS` 的呼叫點在 HUMAN_PENDING 下不可達（PRD AC-R2P-10-10）。
- ESCALATION 恢復後預算負控（D-60）：暫存狀態目錄的外環鍵 3 次 `gate SCG_VALIDATION FAIL`→ESCALATION→人工 `resume-from-escalation --to SPEC_DRAFTING`（測試腳本直接呼叫框架 CLI；Bridge 不呼叫）→`show` 的 `current_count` 仍為 3；再一次 `gate … FAIL` 立即再 ESCALATION，改為 `gate … PASS` 則 `current_count` 歸 0 並轉 HUMAN_PENDING；`fake_sdd` 夾具對齊此行為（歸 P0 TCS）。
- DB 觸發器斷言（`ResearchSchemaMigrationIT`〔新類別，既有 `SchemaMigrationIT` 只改版本清單〕；D-49、D-61）：缺陷 `status` 單向轉移、來源 `verification` 只升不降、受控可更新表的通用守衛（清單外欄位 UPDATE 與任何 DELETE 被拒）；`research_review_rounds` 為 append-only（任何 UPDATE／DELETE 被拒；D-57）、其 `passed`／`fsm_gate_result`／`trigger_kind` 一致性 `CHECK`（含「未通過 ⇒ `fsm_gate_result='FAIL'`」；PRD AC-R2P-02-7、02-11、05-9、08-11）；D-61 補鎖：輪表 `verdict`／`passed`、`escalated`／`ESCALATE`、`fsm_retry_count`／`fsm_gate_result` 的充要 `CHECK` 與 `threshold` 範圍、`research_stage_runs` 同研究專案至多一筆 QUEUED／RUNNING 的部分唯一索引、`research_fetches.host` 非空字串。

## 6. 後果

- Bridge 的 FSM 寫入面從 5 個動詞增為 9 個（含建檔例外），全部集中在新增的 `app.research.fsm_ops` 模組與 `sdd_cli.py` 內獨立的 `RESEARCH_VERBS` 表（既有 `ALLOWED_VERBS` 零改動）；`resume-from-escalation` 維持不入，R-9.5 的人工恢復路徑不變。
- 框架側改動限於 Markdown／YAML，不影響 TLA+／TLC。
- 外環鍵的狀態檔住研究工作區（repo 外，ADR-003 D8），不被 git 追蹤；每次 Gate／SCR 把 `show` 輸出引進證據檔以保可稽核。

---

## 附錄 A　SCR MINOR 的指令序列（PowerShell 形態；於暫存狀態目錄實跑後落證）

```powershell
# 前置：函式 sdd 包 `& $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime @args`，cwd＝<SDD>（Push-Location 同呼叫成對），環境依 §4
# 0) Console：POST /api/v1/research/projects/{id}/scr {kind:MINOR, reason, affectedSections}  → research_scr(OPEN)；Bridge 先 :stop 進行中的 run
# 1) 外環鍵 R：
sdd transition --project research-<slug> --must-exist --to SPEC_DRAFTING --reason "進入 Stage Gate-0-SCR<k>: <摘要>" --trigger research_bridge
#    →（起草／審查／gate 迴圈，預算重新計）→ ADMIN 按「核准 SCR」
sdd spec-frozen --project research-<slug> --must-exist --stage Gate-0-SCR<k> --doc <相對路徑>… --digest --root <工作區> --approver <JWT subject> --reason "SCR-<k> approved" --json
# 2) 內環鍵 I。現態矩陣：IMPLEMENTATION／EXECUTION_EVALUATION／ADVERSARIAL_EVALUATION／PR_REVIEW 有 →SPEC_AUDIT 邊，直接起跑（現態已是 SPEC_AUDIT 者略過下一行）；
#    RTM_VERIFY／RELEASE_READY 沒有該邊，須先 gate RTM_VERIFY FAIL／gate RELEASE_READY FAIL（後者 --reason 必填）退回 IMPLEMENTATION，回傳 next_state 不是 IMPLEMENTATION（含 ESCALATION）即回報 BLOCKED、不重試；其餘現態（含 ESCALATION*）回 409、不起跑
sdd transition --project <I> --must-exist --to SPEC_AUDIT --reason "SCR-<k> minor: <摘要>; research=<id>" --trigger research_bridge
# 3) 發佈新 PRD 到目標 docs/（複製＋sha256）：SPEC_AUDIT 是允許寫規格檔的態（BRIDGE §8.3 第 3 點）；先發佈會在 IMPLEMENTATION 態被 hooks-ON 視窗擋下，人工等價序列才走得通
sdd spec-refreeze --project <I> --doc <目標 docs/ 相對路徑>… --root <目標根> --reason "SCR-<k>: PRD <a>→<b>; gate_decision <id>" --approver <JWT subject>
sdd transition --project <I> --must-exist --to PR_REVIEW --reason "SCR-<k> spec refrozen"
sdd gate --project <I> --must-exist --gate PR_REVIEW --result FAIL --reason "SCR-<k>: spec changed; re-implement"
```
人工等價：同一序列在 hooks-ON 的 SDD session 手跑（鍵 `<I>`，三件組同 BRIDGE §8.1）；兩者必須產生相同的 `decision_trace`。

## 附錄 B　對 ADR-XPLAT-016 的回寫註記文字（由主控於收尾單人窗口貼入；本檔不改該 ADR 本文）

1. **§3.5 動詞白名單列（`:178`）列尾加註**：「〔2026-11-02 註記：研究面（鍵 `research-<slug>` 與 `agentconsole-research-to-prd-*`／`sdd-research-to-prd` 功能鍵）的動詞白名單另見 ADR-XPLAT-017 §D2；本列對 `:freeze` 與 `/autoclaude/runs` 的 `sdd` 區塊仍有效，`resume-from-escalation` 仍不入。〕」
2. **新增附錄 F（標題與內文）**：「附錄 F　後續 ADR 指標——ADR-XPLAT-017（Bridge 研究寫入面：雙鍵模型、FSM 動詞擴充、Gate-0 端點、框架側白名單）補充本 ADR §3.5 與 §11，不取代任何決策；§11 白名單本文不改，框架鍵 `sdd-research-to-prd` 的可改檔以 ADR-XPLAT-017 §D7 為準。」
3. **`SDD_AUTOCLAUDE_BRIDGE.md`**（框架鍵視窗做）：§8.0 鍵前綴表加 `research`（註明「外環鍵，狀態目錄在研究工作區，不屬四個子專案標準目錄」）、新增 §9「Research-to-PRD 路徑（Console／Bridge）」。
4. **`AgentConsole/CLAUDE.md` 鐵律 7**（主控）：白名單句尾加「ADR-XPLAT-017 §D7（僅 `sdd-research-to-prd` 鍵視窗）」。

---

## 勘誤記錄（凍結後的訂正；條文已原地訂正，被訂正的原文逐字保留於本表；只涵蓋 ResearchToPRD 研究面相關段；走 `spec-refreeze`）

> 日期一律 2026-11-03（表內日期欄只寫月-日）；來源＝P0 實作期的勘誤候選（鍵 `agentconsole-research-to-prd-p0`）與主控裁決 D-72、D-79、D-83。

<!-- 日期欄只寫月-日、不寫四位數年份：本表的列常同時引用含 passed／skipped 字樣的 reason 識別字，完整年份會讓 tools/check_pytest_baseline_sites.py 把該列誤判成測試基線數字，而它的站點棘輪不吃行內豁免標記；改寫識別字則失去可 grep 性，故改日期格式（年份見上方首句）。 -->

| 號 | 日期 | 條文 | 原文 → 改文 | 來源包／裁決號 |
|---|---|---|---|---|
| 1 | 11-03 | §D3 Gate 0 檢查序 ③（與 ② 加註、④ 加 `escalated`） | 原文：「③`expected_digests` 與現檔逐一比對（不符 409 原 spec_digest_changed，`details.pair=expected_vs_file`）④FSM 現態＝HUMAN_PENDING（否則 409 `fsm_state_conflict`，帶 `expected_state`）」 → 改文：③只比對送來的鍵（至少一鍵；零鍵 422 `missing_digests`；不符 422 `digest_mismatch`，`details.files[{key,expected,current}]`；缺鍵不算錯，四份文件摘要由 `spec-frozen --digest --root` 於凍結當下計算並記入凍結記錄）；④ESCALATION 時 409 `escalated`；② 加註 Bridge 以版號為憑、前端 sha256 判過期只作提示（兩判準並存、Bridge 為權威） | FE-C E3／P1、BR-C、FIX-API、FIX-BR 勘誤 10；D-72、D-83 |
| 2 | 11-03 | §4 Bridge 子行程環境（新增研究 stage run 引擎子行程列） | 原文：表只列 FSM CLI 子行程（「其餘＝移除所有 `BRIDGE_*`、`SDD_*`、`PYTHONPATH` 後再設」），沒有研究 stage run 的引擎子行程環境與引擎 Brain 設定 → 改文：新增一列：引擎子行程剝除 `BRIDGE_*`、`SDD_*`、`MINIMAX_*` 前綴與 `PYTHONPATH`、`GITHUB_TOKEN`、`GH_TOKEN`、`GH_ENTERPRISE_TOKEN`；`config_overrides` 釘 `minimax.enable_kernel_brain=false` | D-79（INT-07）；FIX-BR；`orchestrator.py` `_STRIPPED_PREFIXES`／`_STRIPPED_NAMES` |
