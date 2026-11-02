# Test Contract Specification — Research-to-PRD 框架層（鍵 `sdd-research-to-prd`）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AISDLC_SDD 框架：`AISDLC_SDD/CLAUDE.md`、框架入口 `AISDLC_SDD_INIT.md`、閘門工作流 `SDD_SPEC_FIRST_GATE.md`）的單一 Feature；FRD-lite 與 TCS 同檔。框架側**沒有自己的 PRD**：上位需求是根層唯一 PRD（`docs/01_requirements/ResearchToPRD_PRD.md`，兩側並列見其 §11.2）
**存放位置**: `AISDLC_SDD/AISDLC_SDD_v<LATEST>/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md`（相對 monorepo 根；`spec-frozen --root` 取 `AISDLC_SDD/`，因凍結文件含 `AISDLC_SDD/CLAUDE.md`，BRIDGE §8.1）
**spec-format-version**: 1.0
**scenario**: documentation
**立案**: 掌舵者 2026-11-02 ResearchSOPtoPRD；主控裁決 D-21
**走法**: 徑②（SDD session-only；`SDD_AUTOCLAUDE_BRIDGE.md` §7、§8.6 第 4 點）——本檔**不經 AutoClaude 評估器編譯**（evaluator 只收 pytest）；每個 AT 的指令是 PowerShell，由獨立 QA 在 SDD session 內逐一自跑，**輸出逐字貼進證據檔與 RTM 的「自動測試」欄，沒貼＝未驗證**

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-970（EPIC-970 之下的單一 Feature） |
| **Feature 名稱** | Research-to-PRD 框架層——Stage-0 研究到規格的方法層（1 個工作流、2 支 agent、4 份模板、ADR-001）與其註冊／條文增補，不動 FSM runtime、規則、skills |
| **User Story** | US-970（已對全 repo 的 md／yaml／json／py／ts／java 以 Grep 確認 F-970、US-970、AC-970、AT-970、EPIC-970 皆未被使用；Console 側既有最大號 F-905、US-919、AC-953，`R2P` 前綴的上位需求另有命名空間，不撞號） |
| **建立日期** | 2026-11-02 |
| **輸入快照** | 起點 commit（`$base`）＝`01d9be6e`（框架鍵開工前，本鍵 Stage-1 的基準）；框架側落檔 commit＝`25c66981`；LATEST＝`AISDLC_SDD_v0.30`（現查 `python AISDLC_SDD/scripts/sdd_version.py`）；五份 Stage-1 採納文件的摘要見〈增量追溯表〉（以框架自己的 `spec_digest.digest_doc` 對 repo 工作樹現檔重算；SCG-4 一審 F-02 訂正，見勘誤） |
| **QA 負責人** | 本鍵 SCG-4 的獨立審查者（規格作者＝SD-B，落地者＝框架鍵視窗的開發 agent，三方不同；審查者獨立性的已知邊界見 §7 ⚖6） |
| **FSM 功能鍵** | `sdd-research-to-prd`（`sub=sdd`；一律從 monorepo 根啟動：`python AISDLC_SDD/scripts/sdd_env.py --sub sdd --slug research-to-prd`；狀態目錄 `AISDLC_SDD/AISDLC_SDD_v<LATEST>/build/reports/sdd-dogfood`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature。**適用性的誠實聲明**：條款的適用範圍排除「要改動已凍結上位文件本身者」，而本鍵改動了三份框架上位文件（INIT、SPEC_FIRST_GATE、`AISDLC_SDD/CLAUDE.md`）——改動性質是**只增不減的註冊與條文增補**（新增清單列、新增條目、新增一節、既有計數句依磁碟現值更新），不改任何既有條款的語意。**這個判斷已由主控 D-48(1) 裁決：適用增量條款，以 `spec-refreeze` 重記摘要**（§7 ⚖1；屬流程解釋，在凍結常態規則射程內由主控代決，掌舵者可隨時以 T1 推翻，推翻時改走完整 SCG-1～3 清單）。**落檔時序（SCG-4 一審 F-02 查證）**：本鍵的 Stage-1 於框架側改動落入工作樹**之後**才採納，所以五份採納文件（三份框架上位文件、根層 PRD、ADR-001）的凍結摘要記的是**改動後**的內容；其後任何再改（SCG-4 審查所致的 PRD 訂正、本檔勘誤）都須以 `spec-refreeze` 重記（§6）。

### FRD-lite

**背景**：掌舵者 2026-11-02 貼入 ResearchSOPtoPRD 規格並問是否納入 AISDLC_SDD 流程；主控裁決 D-21（方法層進框架、執行層在 Console／Bridge）。框架側只放 Markdown 與 YAML，抓取、資料庫、UI、FSM 驅動屬 Console／Bridge（根層 PRD、ADR-XPLAT-017、AgentConsole 的 ADR-003）。

**現況與變更（Before／After；增量）**

- Before：框架沒有研究到規格的方法文件；PRD 的起草與審查沒有證據錨定與對抗審查協定；FSM 外環（SPEC_DRAFTING → SCG_VALIDATION → HUMAN_PENDING → SPEC_FROZEN）沒有以「研究專案」為單位的鍵命名與 stage 名。
- After：(1) 新增工作流 `workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`（第 0～14 章）。(2) 新增兩支 agent `research-analyst`、`spec-engineer`（審查沿用既有四支）。(3) 新增四份模板（議題、證據、SE-PRD、評分卡；含 9 個機器可讀 JSON 契約區塊）。(4) 新增 `ADR-001-research-to-prd-framework-layer.md`（D1～D7）。(5) 既有檔只增不減（被取代的只有就地延伸的計數句、日期行與註記句，被訂正的原文逐字保留）：INIT 四處註冊與計數、`workflow/README.md`、`agent/README.md`、`agent/specialized/README.md`、`docs_template/README.md` 與 `PROJECT_DOCUMENTATION_STANDARDS.md` 的計數與清單、`SDD_SPEC_FIRST_GATE.md`（Gate-0 命名、SCR stage 名、SCG-0 評估器條款）、`SDD_AUTOCLAUDE_BRIDGE.md`（§8.0 一列、新 §9）、greenfield 與 brownfield enhancement（各一段指標）、`AISDLC_SDD/CLAUDE.md`（Rule 2 目錄樹一句、快速參考一列、Rule 6 兩列）、`EVOLUTION_LOG.md`、`CHANGELOG.md`（新增條目與頂部日期行）。(6) 主控補 `framework_status_snapshot.py` 的 curated 組成字串（`+1 Research-to-PRD`；D-47），再以 `--write` 重生 `FRAMEWORK_STATUS.md`。
- **非目標**：不新增 FSM 狀態或邊、不改 `_HAPPY_PATH`／`formal/`／`R-*.yaml`／skills／`.claude/`／`PRD_Universal_Template.md`；框架不含網路或資料庫程式；不寫框架側 PRD；不改根層 `tools/`、`.claude/`（零例外）；根層其餘變動只准 D-46 逐字清單內的 W0 連動檔（AT-970-5-1）；導覽項的落後已由 D-47 納入白名單處理（§7 ⚖7）。

**AC 編號規則**

1. **編譯文法**（備查；本檔走徑②，不編譯）：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：本檔 AC 自 `AC-970-1` 起，共 7 個：970-1 新增檔齊備與格式、970-2 註冊與計數、970-3 JSON 契約自洽、970-4 框架治理閘不退步、970-5 變更邊界與追溯、970-6 文件內容對齊、970-7 FSM 演練。
3. **AT 命名**：`AT-970-<AC 序>-<序>`；負控與邊界 `AT-970-<AC 序>-E-<序>`（掛在其所屬 AC 之下，符合文法）。
4. **計數**：AC 7 個、AT 35 個（正控 26、負控 9；見 §1）。

**本增量交付物**（D1～D6；路徑相對版本目錄 `AISDLC_SDD/AISDLC_SDD_v<LATEST>/`，除非另註）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | 工作流 | `workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md` | 框架鍵開發 agent | AC-970-1、6、7 |
| D2 | 兩支 agent | `agent/specialized/research-analyst-zh.yaml`、`spec-engineer-zh.yaml` | 同上 | AC-970-1、4 |
| D3 | 四份模板 | `docs_template/sdd/requirements/{ISSUE-SCOPE,EVIDENCE-MATRIX,PRD-SPEC-ENGINEERED,ADVERSARIAL-REVIEW-CARD}-TEMPLATE.md` | 同上 | AC-970-3、6 |
| D4 | ADR | `docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md` | 同上 | AC-970-6 |
| D5 | 註冊與條文增補（既有檔，只增不減） | 版本目錄內 12 檔（`AISDLC_SDD_INIT.md`、`workflow/README.md`、`agent/README.md`、`agent/specialized/README.md`、`SDD_SPEC_FIRST_GATE.md`、`SDD_AUTOCLAUDE_BRIDGE.md`、greenfield 與 brownfield enhancement、`docs_template/README.md`、`guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md`、`EVOLUTION_LOG.md`、`releases/CHANGELOG.md`）＋版本目錄外 `AISDLC_SDD/CLAUDE.md`（Rule 2 目錄樹一句、快速參考一列、Rule 6 兩列） | 同上（落檔 commit `25c66981`；只增不減的重現指令見 §7 ⚖1） | AC-970-2、5 |
| D6 | 本檔、組成字串補丁與 `FRAMEWORK_STATUS.md` 重生 | 本檔；`AISDLC_SDD/scripts/framework_status_snapshot.py`（curated 組成字串加 `+1 Research-to-PRD`，D-47）；`AISDLC_SDD/FRAMEWORK_STATUS.md`（`framework_status_snapshot.py --write`，同 commit 最後一步） | SD-B（本檔）／主控（補丁與重生） | AC-970-2 |

**提交順序與責任**

- D1～D4（新增檔）→ AT-970-3-x（契約自洽）→ D5（既有檔編修）→ D6 重生 → AT-970-1～6 全跑 → `spec-refreeze`（§6）。以上步驟已於落檔 commit `25c66981` 完成，本行保留為重做時的順序。
- 框架鍵視窗是 hooks-ON 視窗：寫 `docs/02_architecture/`、`docs/03_testing/` 須在 INIT、SCENARIO_DETECT、AGENT_LOAD、SPEC_DRAFTING、SPEC_AUDIT、SPEC_REGRESSION_CHECK 或 RESUME_VERIFICATION 態（BRIDGE §8.3 第 3 點）。
- 開發 agent **不 commit／push**（主控驗證後 commit）；不動 §5 白名單（AT-970-5-1）以外的檔；凍結版與中間歷史版一律不碰；不跑 FSM CLI 寫入動詞（AT-970-7 的演練只寫 `$tmp` 之下的暫存狀態目錄與版本目錄複本，由獨立 QA 於 SCG-4 時執行）。

**〈增量行為規則〉**（W-F1～W-F6；各 AT 以 W-F 編號引用。實查依據：`transition_rules.py`、`fsm_runtime.py`、`framework_status_snapshot.py`、`agent_template_lint.py`、`arch_fitness.py`、`SDD_AUTOCLAUDE_BRIDGE.md` §8）

- **W-F1 工作流與 ADR**：工作流章節 0～14 連號；ADR 決策編號固定 D1～D7（D1 新增 workflow 不新增 scenario／D2 兩支新 agent、審查沿用既有四支／D3 不新增 `R-*.yaml`／D4 四份新模板／D5 Stage 與鍵命名／D6 框架不含網路與資料庫程式／D7 評分卡是 SCG-0 的評估器）；ADR 與工作流表頭引用根層 PRD 的 FR-R2P／AC-R2P 編號，且每個被引用的編號都存在於該 PRD。
- **W-F2 註冊**：INIT 的 `auto_load_config`（兩支 agent 各一條）、Agent 清單表（兩列）、Workflow 清單（一列）、模板索引（四列）；INIT、`workflow/README.md`、`agent/specialized/README.md`、`agent/README.md`、`docs_template/README.md`、`PROJECT_DOCUMENTATION_STANDARDS.md` 的計數句以 `REPLACE_NUM`（磁碟現值＋偏移）更新並等於磁碟；`agent/README.md` 的訂正依訂正協議保留原文逐字（D-47）；`AISDLC_SDD/CLAUDE.md` Rule 2 目錄樹一句、〈框架核心文件快速參考〉一列與 Rule 6 場景專屬表兩列；`framework_status_snapshot.py` 的組成字串含 `+1 Research-to-PRD`。
- **W-F3 契約**：四份模板共 9 個 `<!-- r2p:contract=<名稱> -->` JSON 區塊，各恰 1 個，自洽於檢核器（附錄 A）；值域與根層 PRD §5.1 一致——`topic` 1～500 字、`slug` `^[a-z0-9][a-z0-9-]{0,29}$`、`depth_level` `QUICK／STANDARD／DEEP`、`layers` 四個布林 `academic／industry／oss／community`；評分以整數 `W100 = 30A+25P+25Q+20S` 判定，通過＝前置全過且 `W100 ≥ 8500` 且每維度 ≥ 60 且無未結 P1（D-14）；彙整卡 `review_card`（審查卡模板第 7 節）另有三條契約（主控 D-54、D-55）：每輪含 `prd_version`（semver 字串）與 `prd_version_no`（整數，對映資料庫 `version_no`，是正式鍵），兩者連同 `prd_sha256` 描述同一份 PRD、輪與輪之間 `prd_version_no` 不遞減；凡有呼叫 `gate` 的輪 `fsm.gate_result=PASS` ⇔ `passed=true`，POST_HUMAN 再審通過的輪 `fsm.gate_result=null`；`REVIEW_INVALID` 不寫審查輪列、不在 `rounds[].verdict` 的值域（只記 stage run 與事件）。
- **W-F4 SE-PRD**：頂層是家規 `PRD_Universal_Template` 的 14 章（章號與標題逐字一致）；來源六節以 `<!-- r2p:section=N -->` 錨點嵌入、各恰 1 個；章尾附錄 R 附「來源六節 ↔ 家規章節」對映表（7 列、無錨點語法）；**雙重預檢**＝六節錨點齊全 且 家規必讀章非空（D-20 SA-01；PRD AC-R2P-07-2）。
- **W-F5 FSM 對映**：外環鍵 `research-<slug>`（換世代 `-g<N>`）、內環鍵 `<sub>-<slug>`；stage 名 `Gate-0`、`Gate-0-SCR<n>`、`Stage-1`、`Stage-2`；Gate 0 的 `--doc` 恰為 `01_specs/PRD-v1.0.0.md`、`00_research/evidence_matrix.md`、`00_research/issue_scope.json`、`01_specs/adr_draft.md` 四份、不含 TCS，`--approver` 必須是真人；審查最多 3 輪（`RETRY_LIMITS["SCG_VALIDATION"]=3`，第 3 次 `gate FAIL` 即 ESCALATION；人工退回走 `gate SCG_VALIDATION FAIL` 共用預算；現態 HUMAN_PENDING 時 Bridge 不呼叫 gate PASS、再審通過只記 DB，D-50；ESCALATION 經人工恢復後預算不歸零：至多再得一次審查，FAIL 立即再 ESCALATION、PASS 歸零，全新預算＝換世代鍵，D-60）；外環鍵環境 `SDD_ENABLE_AUTO_RECOVERY=0`；SCR 三路（MINOR＝外環重走 `Gate-0-SCR<n>` 加內環 SPEC_AUDIT／`spec-refreeze`；MAJOR＝新研究專案；自癒耗盡＝人手 `resume-from-escalation`）；Bridge 可用動詞＝`show`（建檔）、`transition`（受限）、`gate`（`SCG_VALIDATION`／`PR_REVIEW`／`RTM_VERIFY`／`RELEASE_READY`）、`spec-refreeze`、`spec-frozen`，**不含** `resume-from-escalation`。
- **W-F6 變更邊界**：本鍵的變更集合只准落在 24 條白名單路徑（9 個新增檔、版本目錄內 12 個被改檔、`AISDLC_SDD/CLAUDE.md`、主控補丁 `AISDLC_SDD/scripts/framework_status_snapshot.py`、重生的 `FRAMEWORK_STATUS.md`）與版本目錄 `docs/06_quality/`（報告與 RTM 落點）；`_HAPPY_PATH`、`formal/`、`governance/rules/R-*.yaml`、`.claude/`、skills、`PRD_Universal_Template.md`、根層 `tools/`、`.claude/` 零差異；根層其餘變動只准主控收尾單窗的 W0 連動檔（D-46 逐字清單，共 8 條：`.gitignore`、`.github/workflows/agentconsole-ci.yml`、根層 PRD 兩份與來源規格逐字檔 `ResearchSOPtoPRD_Source_Spec.md`、ADR-XPLAT-016／017、`AgentConsole/**`）。

**上位需求對照**（根層 `docs/01_requirements/ResearchToPRD_PRD.md`；AT-970-6-5 機械核對每個編號都存在於該 PRD）

| 本檔 AC | 上位 FR／NFR | 上位 AC |
|---------|-------------|---------|
| AC-970-1 | FR-R2P-03、FR-R2P-07 | AC-R2P-03-1、AC-R2P-03-2、AC-R2P-07-1 |
| AC-970-2 | PRD §9.1 元件 C21、C22 | AC-R2P-07-2 |
| AC-970-3 | FR-R2P-03、FR-R2P-05、FR-R2P-08 | AC-R2P-03-2、AC-R2P-05-1、AC-R2P-05-7、AC-R2P-08-1、AC-R2P-08-5 |
| AC-970-4 | NFR-R2P-05、NFR-R2P-08 | AC-R2P-04-9 |
| AC-970-5 | NFR-R2P-08（文件最小集與回填）；變更邊界的直接依據是 PRD §9.0 落點表與 ADR-XPLAT-017 §D7（非 AC） | AC-R2P-11-7、AC-R2P-12-6 |
| AC-970-6 | FR-R2P-07、FR-R2P-08、FR-R2P-10、FR-R2P-19 | AC-R2P-07-2、AC-R2P-08-2、AC-R2P-08-3、AC-R2P-10-1、AC-R2P-19-1 |
| AC-970-7 | FR-R2P-08、FR-R2P-10、FR-R2P-19 | AC-R2P-08-3、AC-R2P-08-9、AC-R2P-08-10、AC-R2P-10-5、AC-R2P-10-8、AC-R2P-19-8 |

**FRD-lite 表**（第一欄用 US ID；不把 AC ID 放第一欄，避免被編譯器當 AC→AT 映射列掃描）

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-970 | 身為框架維護者，我想把研究到規格的方法層以 Markdown 與 YAML 納入 AISDLC_SDD LATEST 而不動 FSM runtime、規則與 skills，以便 Console 與人手流程共用同一個方法真相源 | AC-970-1 | Given 框架側九個新增檔已落地 When 檢查九個新增檔 Then 九檔存在於指定路徑；兩支 agent YAML 可解析且含值域（`required_input`）與雙重預檢（`dual_precheck`）欄位；全部為 UTF-8、無 BOM、純 LF；舊名 ADR 與已取消的框架側 PRD 不存在 |
| US-970 | 同上 | AC-970-2 | Given 既有註冊清單 When 逐塊套用編修並重生 `FRAMEWORK_STATUS.md` Then INIT 四處、五份 README 與標準文件（`workflow/README.md`、`agent/specialized/README.md`、`agent/README.md`、`docs_template/README.md`、`PROJECT_DOCUMENTATION_STANDARDS.md`）、`AISDLC_SDD/CLAUDE.md`（Rule 2、快速參考、Rule 6）、CHANGELOG 日期皆登記新增項、計數宣稱等於磁碟（`agent/README.md` 的訂正保留原文）、`framework_status_snapshot.py --check` rc 0；對一份「磁碟多了一支 agent 卻未重生」的狀態檔 `--check` 必須 rc 1 |
| US-970 | 同上 | AC-970-3 | Given 四份模板的九個 JSON 契約區塊 When 以契約檢核器檢核 Then 9 個區塊 0 項問題、29 個注入錯誤全被抓到且 1 個合法變體（POST_HUMAN 再審通過的輪 `fsm.gate_result=null`）不被誤判；缺任一標記即 rc 1 |
| US-970 | 同上 | AC-970-4 | Given 新增兩支 agent 與四份模板 When 跑四支 agent lint、`arch_fitness`、skills 鏡像檢查與 `ci-gate` Then 四 lint rc 0、FF-6／7／13／15 皆為 info 且 `n_fail` 0、鏡像 rc 0、`ci-gate` rc 0；鬼影模板路徑會被 lint 抓到 |
| US-970 | 同上 | AC-970-5 | Given 本鍵的變更集合 When 與白名單核對 Then 全部落在 24 條白名單路徑、版本目錄 `docs/06_quality/` 與 D-46 的根層連動逐字清單內，`tools/`、`.claude/` 與其他受保護路徑零差異；〈增量追溯表〉的五個摘要等於 Stage-1 凍結記錄（含 `spec-refreeze` 重記） |
| US-970 | 同上 | AC-970-6 | Given 工作流、ADR、模板、BRIDGE §9 與 SPEC_FIRST_GATE 條文 When 逐項比對 Then 章節與決策編號齊全、Gate 0 恰四份文件不含 TCS、`gate` 為四個閘且不含 `resume-from-escalation`（BRIDGE §9.2 含實際使用面句，D-45）、人工退回守則住在工作流第 8 章與 BRIDGE §9.3 且與 `SDD_SPEC_FIRST_GATE.md` 對照表第 5 列一致（D-50）、SE-PRD 為家規 14 章頂層加六錨點加章尾對映表、無占位字樣、被引用的上位需求編號皆存在於根層 PRD、恢復後預算句（D-60）同在工作流第 2.5 節與審查卡模板第 2.3 節、SE-PRD 模板 P0-7 列的四個預檢代碼逐處計數、審查卡模板第 5.3 節含缺陷狀態轉移矩陣、散文條文的關鍵數字與句子（W100 公式與 8500 門檻、第 N 次 FAIL＝ESCALATION、四維權重百分比、ADR D7 後半句、BRIDGE 外環鍵前五值、Gate 0 永遠要求真人核准、V0 不得列入）與契約 JSON 或引擎常數對拍 |
| US-970 | 同上 | AC-970-7 | Given 暫存 FSM 狀態目錄 When 依工作流第 2.6、9.3 節的指令序列演練 Then PASS 後 Gate 0 以四文件凍結；3 次 FAIL 為 ESCALATION（自動恢復關閉時回傳無 `auto_recovery`，預設開啟時有）；人工退回走 `gate FAIL` 且 HUMAN_PENDING→SPEC_DRAFTING 被拒、SPEC_REGRESSION_CHECK 後可凍結；現態 HUMAN_PENDING 時 `gate FAIL` 態不動且計數加 1、`gate PASS` rc≠0 且態與計數不變（D-50 負控）；ESCALATION 人工恢復後計數仍為上限、恢復後第一次 `gate FAIL` 立即再 ESCALATION、`gate PASS` 歸零並進 HUMAN_PENDING（D-60）；SCR-minor 序列落到 IMPLEMENTATION；研究工作區路徑不被 Rule 9.6 規格寫入阻擋 |

### 〈增量追溯表〉（SCG-0～3 每個清單項一列；清單見 `SDD_SPEC_FIRST_GATE.md`〈閘門通過標準〉）

> 凍結摘要＝該文件在本鍵 `frozen_stages[*].spec_doc_digests` 的值；`spec-refreeze` 追加的重記條目與原條目取聯集、同鍵後者勝出（與 AutoClaude `check_digest`、Bridge 的消費語意相同；`state_loader.py` 的 `record_spec_refreeze`）。以下五份是本鍵 **Stage-1 的真實採納集合**（SCG-4 一審 F-02 訂正）：`spec-frozen --root` 是 **monorepo 根**（因含根層 PRD），鍵是相對根的正斜線路徑；摘要是**改動後**內容的摘要（Stage-1 於框架側改動落入工作樹之後才採納，時序見檔頭〈增量條款〉段）。摘要以框架自己的 `spec_digest.digest_doc` 對 repo 工作樹現檔重算（重算指令見 AT-970-5-3），**CLI 的值為準**，主控以 AT-970-5-3 比對、不符則先更新本表（文件於凍結後被改而未重記，也會讓兩者不等）。標「本增量」者由本檔 FRD-lite 與 TCS 自身滿足（增量文件集本身仍照常走 SCG_VALIDATION → 人類確認 → `spec-frozen`，TCS 在 `--doc` 內）；標「不適用」者附理由並交人在 HUMAN_PENDING 確認（Rule 8）。
>
> | 代號 | 上位文件 | 路徑（相對 monorepo 根） | 凍結摘要 |
> |------|----------|--------------------------|----------|
> | U1 | 框架規則總綱 | `AISDLC_SDD/CLAUDE.md` | `sha256:09d88638cd8e3d441c3f1bd94cbf289beff767cd9455063263125c06b9142908` |
> | U2 | 框架入口 | `AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md` | `sha256:c0732753d2a2e7b19678ec48d169845e3280a3b06422325a966a9fd4b07dde28` |
> | U3 | 閘門工作流 | `AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` | `sha256:ca913bb1f62f97ef4b06fd698c2c5c3b0327f464fa90b1760d8a07a8b4ec98fa` |
> | U4 | 研究到規格 PRD（唯一 PRD） | `docs/01_requirements/ResearchToPRD_PRD.md` | `sha256:179e839fe318388ad3522de3d7b6f8bda222f6b808dff23455e32a3ae3007ed8` |
> | U5 | 框架 ADR-001 | `AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md` | `sha256:c2935ae10317a9db4992057db14a0e58983005711f9072f0b74cd39829260180` |
>
> 改動前基準（資訊用，不是 AT-970-5-3 的比對對象）：起點 commit `01d9be6e` 的三份框架上位文件摘要為 U1 `sha256:e1a2801843b9072bdafa599070a7b53cd91c1687e6cefc00cb4c9754ce47cd68`、U2 `sha256:7c6d5620e70f08a75587bfa8adde6ef3d3af32b0c95f084a47bec8b020ee0eac`、U3 `sha256:c44b47a825c88aa296818db2004a0267ccc1d1e49a692c2ff062b084bdd39c00`（`git show 01d9be6e:<路徑>` 經 `digest_doc` 可重算；U4 與 U5 在該 commit 尚不存在，是本鍵新增）。

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 已完成（業務目標、範疇、假設） | ADOPTED U4〈根層 PRD：業務目標、範疇、假設；FR-R2P-01～23〉 | `docs/01_requirements/ResearchToPRD_PRD.md` | `sha256:179e839fe318388ad3522de3d7b6f8bda222f6b808dff23455e32a3ae3007ed8` |
| SCG-0／FRD 所有欄位完整 | 本增量：F-970、US-970（FRD-lite 表） | —（本檔，Stage-2 凍結時由 CLI 記錄） | — |
| SCG-0／每個 US 有可測 AC（Given／When／Then） | 本增量：AC-970-1～7（§1 皆有 AT） | —（本檔） | — |
| SCG-0／追溯鏈 EPIC → F → US → AC 完整 | 本增量：EPIC-970 → F-970 → US-970 → AC-970-1～7 → AT（§1） | —（本檔） | — |
| SCG-0／使用標準 ID 格式 | ADOPTED U1〈Rule 7〉 | `AISDLC_SDD/CLAUDE.md` | `sha256:09d88638cd8e3d441c3f1bd94cbf289beff767cd9455063263125c06b9142908` |
| SCG-0／SLV 前置驗證（SLV-001～003） | ADOPTED U3〈SCG-0 通過標準〉；機械半段對表格形 AC 空轉，QA 人讀補位（BRIDGE §8.5；§7 ⚖2） | `AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` | `sha256:ca913bb1f62f97ef4b06fd698c2c5c3b0327f464fa90b1760d8a07a8b4ec98fa` |
| SCG-0／Ambiguity Gate（AC 模糊度 < 0.4 或有 WAIVER） | ADOPTED U3〈SCG-0 通過標準〉；本檔 AC 以 `AC-970-n` 編號、AT 以 Given／When／Then 描述 | 同上 | `sha256:ca913bb1f62f97ef4b06fd698c2c5c3b0327f464fa90b1760d8a07a8b4ec98fa` |
| SCG-1／SRD 完整定義系統設計 | ADOPTED U2〈框架結構與入口〉；本增量的設計＝工作流第 2 章（FSM 對映）與 ADR-001（U5） | `AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md` | `sha256:c0732753d2a2e7b19678ec48d169845e3280a3b06422325a966a9fd4b07dde28` |
| SCG-1／API Spec 草稿（端點清單） | 不適用：框架無 HTTP API；機器契約住四份模板的 9 個 JSON 區塊（AT-970-3-x 驗） | — | — |
| SCG-1／NFR 規格化（量化目標） | 不適用：Markdown 與 YAML 資產沒有執行期 NFR；非功能面＝AC-970-4（既有治理閘零退步）、AC-970-5（變更邊界） | — | — |
| SCG-1／技術選型有合理依據 | ADOPTED U5〈ADR-001 D1～D7，含替代方案評估〉 | `AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md` | `sha256:c2935ae10317a9db4992057db14a0e58983005711f9072f0b74cd39829260180` |
| SCG-2／SRD 完整定義系統架構 | ADOPTED U2；本增量的架構＝雙環漏斗與兩把鍵（工作流第 0.2、2.1 節） | `AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md` | `sha256:c0732753d2a2e7b19678ec48d169845e3280a3b06422325a966a9fd4b07dde28` |
| SCG-2／C4 Context 與 Container 圖 | 不適用：框架資產無執行期容器；Console／Bridge 的容器圖在 AgentConsole Architecture（根層 PRD §9.2） | — | — |
| SCG-2／所有重大架構決策有對應 ADR | ADOPTED U5〈ADR-001 D1～D7〉；Bridge 側＝根層 ADR-XPLAT-017 | `AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md` | `sha256:c2935ae10317a9db4992057db14a0e58983005711f9072f0b74cd39829260180` |
| SCG-2／Trust Boundary Map（安全場景必備） | 不適用：本鍵非安全場景；外呼邊界在 Bridge（根層 PRD NFR-R2P-03） | — | — |
| SCG-3／使用 OpenAPI 3.1 | 不適用：框架無 HTTP API，沒有可追溯的已凍結 OpenAPI | — | — |
| SCG-3／所有端點已定義 Request／Response Schema | 不適用：同上 | — | — |
| SCG-3／安全機制已定義（securitySchemes） | 不適用：同上 | — | — |
| SCG-3／追溯至 US／AC（`x-aisdlc.related_us`） | 不適用：同上；追溯由本檔 §1 與 §6 承擔 | — | — |
| SCG-3／SLV 前置驗證（SLV-004～006） | 不適用：SLV-004～006 針對 OpenAPI 契約 | — | — |

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（`AT-970-1-2` 屬 `AC-970-1`；`AT-970-1-E-1` 屬 `AC-970-1`）。**自動化**欄的「✅」＝可由 PowerShell 指令自動判定；「🔶」＝FSM 演練 AT（寫 `$tmp` 之下的暫存狀態目錄與版本目錄複本；§2.7 預期值原依讀碼推得，首次執行的差異以實跑為準並走勘誤）。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-970-1 | 九個新增檔齊備與格式 | AT-970-1-1 | 九檔存在、舊名 ADR 不存在 | ✅ | Unit | □ |
| AC-970-1 | 同上 | AT-970-1-2 | 兩支 agent YAML 語意（id、版本欄、值域、雙重預檢欄位） | ✅ | Unit | □ |
| AC-970-1 | 同上 | AT-970-1-3 | 新增檔與被改檔：UTF-8、無 BOM、純 LF、檔尾換行 | ✅ | Unit | □ |
| AC-970-1 | 同上 | AT-970-1-E-1 | 工作流目錄只有一檔；舊名 ADR 與已取消的框架側 PRD 不存在 | ✅ | Unit | □ |
| AC-970-2 | 註冊與計數 | AT-970-2-1 | INIT 四處、五份 README 與標準文件、`AISDLC_SDD/CLAUDE.md` 三處、CHANGELOG 日期、組成字串補丁皆登記；計數＝磁碟；訂正保留原文 | ✅ | Integration | □ |
| AC-970-2 | 同上 | AT-970-2-2 | `framework_status_snapshot.py --check` rc 0 | ✅ | Integration | □ |
| AC-970-2 | 同上 | AT-970-2-E-1 | 負控：磁碟多一支 agent 而未重生時 `--check` rc 1（暫存迷你樹） | ✅ | Integration | □ |
| AC-970-3 | JSON 契約自洽 | AT-970-3-1 | 檢核器對真模板：9 區塊 0 問題 | ✅ | Contract | □ |
| AC-970-3 | 同上 | AT-970-3-2 | 檢核器自證：29 個注入錯誤全被抓到、1 個合法變體不誤判 | ✅ | Contract | □ |
| AC-970-3 | 同上 | AT-970-3-E-1 | 負控：缺一個契約標記 → rc 1 並指名該標記 | ✅ | Contract | □ |
| AC-970-4 | 框架治理閘不退步 | AT-970-4-1 | 四支 agent lint 皆 rc 0 | ✅ | Integration | □ |
| AC-970-4 | 同上 | AT-970-4-2 | `arch_fitness`：`n_fail` 0，FF-6／7／13／15 皆 info | ✅ | Integration | □ |
| AC-970-4 | 同上 | AT-970-4-3 | skills 鏡像與版本戳記 `--check` rc 0（未新增 skill） | ✅ | Integration | □ |
| AC-970-4 | 同上 | AT-970-4-4 | 本機 CI 閘門 `ci-gate.ps1` rc 0（長時間，背景跑） | ✅ | E2E | □ |
| AC-970-4 | 同上 | AT-970-4-E-1 | 負控：鬼影模板路徑被 `agent_template_lint` 抓到（rc 1），修正後 rc 0 | ✅ | Integration | □ |
| AC-970-5 | 變更邊界與追溯 | AT-970-5-1 | 變更集合落在 24 條白名單路徑、`docs/06_quality/` 與 D-46 根層連動逐字清單內；`tools/`、`.claude/` 零差異 | ✅ | Integration | □ |
| AC-970-5 | 同上 | AT-970-5-2 | 受保護路徑零差異 | ✅ | Integration | □ |
| AC-970-5 | 同上 | AT-970-5-3 | 〈增量追溯表〉五個摘要＝Stage-1 凍結記錄與 `spec-refreeze` 重記條目的聯集（唯讀 `show`） | ✅ | Integration | □ |
| AC-970-5 | 同上 | AT-970-5-E-1 | 負控：邊界函式對合成的越界路徑（含清單外的根層文件、清單外的 `scripts/` 檔、根層 `.claude/`）回報違規 | ✅ | Unit | □ |
| AC-970-6 | 文件內容對齊 | AT-970-6-1 | 工作流章節 0～14 連號；ADR 決策恰 D1～D7 且各含其關鍵語；恢復後預算句（D-60）、P0-7 預檢代碼逐處計數、缺陷狀態轉移矩陣各在其位 | ✅ | Unit | □ |
| AC-970-6 | 同上 | AT-970-6-2 | Gate 0 四文件不含 TCS；BRIDGE §9.2 動詞列、四個閘與使用面句（D-45）；不含 `resume-from-escalation`；人工退回守則三處一致（D-50） | ✅ | Unit | □ |
| AC-970-6 | 同上 | AT-970-6-3 | SE-PRD 結構：14 章標題逐字同家規、六錨點各一、章尾附錄 R | ✅ | Unit | □ |
| AC-970-6 | 同上 | AT-970-6-4 | 無占位字樣；除 SE-PRD 模板外無雙大括號佔位 | ✅ | Unit | □ |
| AC-970-6 | 同上 | AT-970-6-5 | 上位需求編號存在於根層 PRD；舊名與已取消的框架側 PRD 零殘留 | ✅ | Unit | □ |
| AC-970-6 | 同上 | AT-970-6-6 | 散文條文與契約 JSON／引擎常數對拍：W100 公式與 8500 門檻、第 N 次 FAIL＝ESCALATION、ADR D7 後半、四維權重百分比、BRIDGE 外環鍵前五值、Gate 0 永遠要求真人核准、V0 不得列入、「最多 N 輪」六處復述（二審 N-1） | ✅ | Unit | □ |
| AC-970-6 | 同上 | AT-970-6-E-1 | 負控：SE-PRD 結構函式對四種變異各回報問題 | ✅ | Unit | □ |
| AC-970-7 | FSM 演練 | AT-970-7-1 | 🔶 PASS → Gate 0 以四文件凍結（`SPEC_FROZEN`） | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-2 | 🔶 FAIL×3 → ESCALATION；自動恢復關閉時無 `auto_recovery` | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-3 | 🔶 人工退回走 `gate FAIL`；非法邊被拒；SPEC_REGRESSION_CHECK 後凍結 | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-4 | 🔶 SCR-minor 序列（內環鍵）落到 IMPLEMENTATION | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-5 | `_is_blocked_spec_write` 對研究工作區路徑不攔、對規格目錄會攔 | ✅ | Unit | □ |
| AC-970-7 | 同上 | AT-970-7-6 | 🔶 ESCALATION 人工恢復後預算不歸零（D-60）：恢復後計數仍 3、下一次 `gate FAIL` 立即再 ESCALATION（`retry_count=3`）、`gate PASS` 歸零並進 HUMAN_PENDING | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-E-1 | 🔶 負控：自動恢復預設開啟時第 3 次 FAIL 的回傳含 `auto_recovery` | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-E-2 | 🔶 負控（D-50）：現態 HUMAN_PENDING 時人工退回 `gate FAIL` 態不動、計數加 1、記 `gate_fail_blocked` | 🔶 | Integration | □ |
| AC-970-7 | 同上 | AT-970-7-E-3 | 🔶 負控（D-50）：現態 HUMAN_PENDING 時 `gate PASS` rc≠0、態與計數不變 | 🔶 | Integration | □ |

**覆蓋率統計**:
- 總 AC 數: 7
- 已映射 AT 數: 35（✅ 27、🔶 8）
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 規格

> 每個 AT＝Given／When／Then 一句＋可直接貼進 PowerShell 的指令＋預期輸出。**PowerShell 規約**：不用裸 `cd`／`Set-Location`；讀 rc 先存變數、不接管線；讀檔一律指名 UTF-8（`Read-Utf8`）；暫存檔只放 `$tmp`；每個 AT 以一行 `RESULT <AT-ID> PASS|FAIL …` 收尾，**逐字貼進證據檔**。AT 區塊在同一個 PowerShell 視窗內依序貼（後面的 AT 沿用前面定義的變數與函式）。預期輸出是對落檔後的 repo 實跑所得；標 🔶 的 FSM 演練區塊，預期值原依讀碼推得（座標列在各 AT），以實跑為準、不符走勘誤。

### 2.0 共用前置（每個 AT 區塊假設已執行）

```powershell
# AT-970-0 共用前置
$root = (git rev-parse --show-toplevel)
$py   = if (Test-Path (Join-Path $root '.venv/Scripts/python.exe')) { Join-Path $root '.venv/Scripts/python.exe' } else { Join-Path $root '.venv/bin/python' }
$env:PYTHONUTF8 = '1'
$utf8 = [System.Text.UTF8Encoding]::new($false)
try { [Console]::OutputEncoding = $utf8 } catch { }
$sdd  = Join-Path $root 'AISDLC_SDD'
$ver  = ((& $py (Join-Path $sdd 'scripts/sdd_version.py')) | Out-String).Trim()     # 例：AISDLC_SDD_v0.30
$vd   = Join-Path $sdd $ver
$tmp  = Join-Path ([System.IO.Path]::GetTempPath()) ('at970_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null                          # 本檔所有暫存檔都放這裡；全部做完後見 AT-970-7-Z 收尾
function Read-Utf8([string]$Path) { [System.IO.File]::ReadAllText($Path, $utf8) }
function Write-Utf8([string]$Path, [string]$Text) { [System.IO.File]::WriteAllText($Path, $Text, $utf8) }
function Show-Result([string]$Id, [bool]$Ok, [string]$Detail = '') { ('RESULT {0} {1} {2}' -f $Id, $(if ($Ok) { 'PASS' } else { 'FAIL' }), $Detail).TrimEnd() }
$new9 = @(
    'workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md',
    'agent/specialized/research-analyst-zh.yaml',
    'agent/specialized/spec-engineer-zh.yaml',
    'docs_template/sdd/requirements/ISSUE-SCOPE-TEMPLATE.md',
    'docs_template/sdd/requirements/EVIDENCE-MATRIX-TEMPLATE.md',
    'docs_template/sdd/requirements/PRD-SPEC-ENGINEERED-TEMPLATE.md',
    'docs_template/sdd/requirements/ADVERSARIAL-REVIEW-CARD-TEMPLATE.md',
    'docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md',
    'docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md')
$edited12 = @(
    'AISDLC_SDD_INIT.md', 'workflow/README.md', 'agent/README.md', 'agent/specialized/README.md',
    'workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md',
    'workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md',
    'scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md',
    'scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md',
    'docs_template/README.md', 'guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md',
    'EVOLUTION_LOG.md', 'releases/CHANGELOG.md')
"vd = $vd"
```

預期輸出：一行 `vd = <monorepo 根>/AISDLC_SDD/AISDLC_SDD_v<LATEST>`，無錯誤。

### 2.1 AC-970-1：九個新增檔齊備與格式

**AT-970-1-1**（Unit）Given 框架側新增檔已落地 When 檢查九個新增檔路徑 Then 九檔皆存在，舊名 ADR 不存在。

```powershell
# AT-970-1-1
$missing = @($new9 | Where-Object { -not (Test-Path -LiteralPath (Join-Path $vd $_)) })
$oldAdr  = Test-Path -LiteralPath (Join-Path $vd ('docs/02_architecture/adr/ADR-001-research-to-prd-' + 'method' + '-layer.md'))
'new files present: {0}/{1}' -f ($new9.Count - $missing.Count), $new9.Count
$missing
Show-Result 'AT-970-1-1' ($missing.Count -eq 0 -and -not $oldAdr)
```

預期輸出：`new files present: 9/9`、`RESULT AT-970-1-1 PASS`。

**AT-970-1-2**（Unit）Given 兩支新 agent YAML When 以 PyYAML 解析並檢查語意欄位 Then `agent.id` 正確、`agent.version` 含 `see FRAMEWORK_STATUS.md`、`evidence_discipline` 指向 `agent/EVIDENCE_DISCIPLINE.md`、`collaboration_rules` 非空、`research-analyst` 的 `required_input` 值域四項與 `spec-engineer` 的 `dual_precheck` 欄位齊全（上位：AC-R2P-03-2、AC-R2P-07-2）。

```powershell
# AT-970-1-2
$code = @'
import sys, yaml
vd = sys.argv[1]
def load(rel):
    with open(vd + '/' + rel, encoding='utf-8') as fh:
        return yaml.safe_load(fh)
ra = load('agent/specialized/research-analyst-zh.yaml')
se = load('agent/specialized/spec-engineer-zh.yaml')
f = ra['required_input']['fields']
dp = se['draft_procedure']['dual_precheck']
checks = [
    ('research-analyst agent.id', ra['agent']['id'] == 'research-analyst'),
    ('spec-engineer agent.id', se['agent']['id'] == 'spec-engineer'),
    ('兩支 agent.version 含 see FRAMEWORK_STATUS.md', all('see FRAMEWORK_STATUS.md' in d['agent']['version'] for d in (ra, se))),
    ('兩支皆 inherits_from EVIDENCE_DISCIPLINE', all(d['evidence_discipline']['inherits_from'] == 'agent/EVIDENCE_DISCIPLINE.md' for d in (ra, se))),
    ('兩支 collaboration_rules 非空', all(bool(d.get('collaboration_rules')) for d in (ra, se))),
    ('required_input.fields 恰五鍵', set(f) == {'topic', 'slug', 'depth_level', 'layers', 'scope'}),
    ('topic 值域 1～500', '1～500' in f['topic']),
    ('slug 值域', '^[a-z0-9][a-z0-9-]{0,29}$' in f['slug']),
    ('depth_level 值域', all(x in f['depth_level'] for x in ('QUICK', 'STANDARD', 'DEEP'))),
    ('layers 四布林', all(x in f['layers'] for x in ('academic', 'industry', 'oss', 'community'))),
    ('雙重預檢兩項與規則', {'check_a_six_anchors', 'check_b_must_read_chapters', 'rule', 'mapping_table'} <= set(dp)),
]
for name, ok in checks:
    print(('PASS ' if ok else 'FAIL ') + name)
sys.exit(0 if all(ok for _, ok in checks) else 1)
'@
$script = Join-Path $tmp 'at970_1_2.py'
Write-Utf8 $script $code
$o = & $py -I -X utf8 $script $vd
$rc = $LASTEXITCODE
$o
Show-Result 'AT-970-1-2' ($rc -eq 0) "rc=$rc"
```

預期輸出：十一行 `PASS …`、`RESULT AT-970-1-2 PASS rc=0`。

**AT-970-1-3**（Unit）Given 九個新增檔、十二個被改檔（版本目錄內）與 `AISDLC_SDD/CLAUDE.md` When 逐檔讀位元組 Then 皆為合法 UTF-8、無 BOM、檔尾有換行、行尾不混用；九個新增檔必須純 LF（`.gitattributes` 對 md／yaml 宣告 LF）。被改檔只要求「不混用」：索引內一律是 LF（`git ls-files --eol` 的 `i/lf`），但 Windows 工作樹可能把個別既有檔檢出成 CRLF（例：`workflow/README.md`、`scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`、`agent/README.md`、`docs_template/README.md`、`PROJECT_DOCUMENTATION_STANDARDS.md` 為 `w/crlf`），套用編修時原樣保留該檔的行尾，git 於 `add` 時正規化。

```powershell
# AT-970-1-3
function Test-FileShape([string]$Path, [string]$Label, [bool]$PureLf) {
    $strict = [System.Text.UTF8Encoding]::new($false, $true)
    $b = [System.IO.File]::ReadAllBytes($Path)
    $cr = 0; $lf = 0
    foreach ($x in $b) { if ($x -eq 13) { $cr++ } elseif ($x -eq 10) { $lf++ } }
    $p = @()
    if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { $p += "$Label : BOM" }
    if ($PureLf -and $cr -gt 0) { $p += "$Label : 含 CR（新增檔要求純 LF）" }
    if ($cr -gt 0 -and $cr -ne $lf) { $p += "$Label : 行尾混用（CR=$cr LF=$lf）" }
    if ($b.Length -eq 0 -or $b[$b.Length - 1] -ne 10) { $p += "$Label : 檔尾缺換行" }
    try { [void]$strict.GetString($b) } catch { $p += "$Label : 非合法 UTF-8" }
    return $p
}
$problems = @()
foreach ($rel in $new9)    { $problems += Test-FileShape (Join-Path $vd $rel) $rel $true }
foreach ($rel in $edited12) { $problems += Test-FileShape (Join-Path $vd $rel) $rel $false }
$problems += Test-FileShape (Join-Path $sdd 'CLAUDE.md') 'AISDLC_SDD/CLAUDE.md' $false
$problems
Show-Result 'AT-970-1-3' ($problems.Count -eq 0) ('files checked: ' + ($new9.Count + $edited12.Count + 1))
```

預期輸出：`RESULT AT-970-1-3 PASS files checked: 22`。

**AT-970-1-E-1**（Unit，負控）Given 落地後的版本目錄 When 列工作流目錄與檢查被取消的路徑 Then 工作流目錄恰一檔 `SDD_RESEARCH_TO_PRD.md`；舊名 ADR 與已取消的框架側 PRD 不存在（防改名或取消後的殘留）。

```powershell
# AT-970-1-E-1
$wfFiles = @(Get-ChildItem -LiteralPath (Join-Path $vd 'workflow/sdd-research-to-prd') -Recurse -File | ForEach-Object { $_.Name })
$cancelled = @(
    ('docs/02_architecture/adr/ADR-001-research-to-prd-' + 'method' + '-layer.md'),
    ('docs/01_requirements/PRD-ResearchTo' + 'PRD-Framework.md')) | Where-Object { Test-Path -LiteralPath (Join-Path $vd $_) }
'workflow dir files: ' + ($wfFiles -join ', ')
'cancelled paths present: ' + @($cancelled).Count
Show-Result 'AT-970-1-E-1' ($wfFiles.Count -eq 1 -and $wfFiles[0] -eq 'SDD_RESEARCH_TO_PRD.md' -and @($cancelled).Count -eq 0)
```

預期輸出：`workflow dir files: SDD_RESEARCH_TO_PRD.md`、`cancelled paths present: 0`、`RESULT AT-970-1-E-1 PASS`。

### 2.2 AC-970-2：註冊與計數

**AT-970-2-1**（Integration）Given 套用編修後的 INIT、五份 README 與標準文件、`AISDLC_SDD/CLAUDE.md`、CHANGELOG 與 `framework_status_snapshot.py` When 以規則表達式核對 Then 兩支 agent 於 `auto_load_config` 與 Agent 清單表各登記一次、Workflow 清單與模板索引（四列）齊全、INIT 的 Specialized 與模板索引計數等於磁碟實數；`workflow/README.md`、`agent/specialized/README.md`、`agent/README.md`、`docs_template/README.md`、`PROJECT_DOCUMENTATION_STANDARDS.md` 的計數與清單等於磁碟，`agent/README.md` 的訂正依訂正協議保留原文逐字（訂正引言內的原計數與現值不同）；`AISDLC_SDD/CLAUDE.md` 的 Rule 2、快速參考、Rule 6 皆有新增項；CHANGELOG 日期與條目齊；組成字串補丁在位（主控 D-47）。

```powershell
# AT-970-2-1
$init   = Read-Utf8 (Join-Path $vd 'AISDLC_SDD_INIT.md')
$wfr    = Read-Utf8 (Join-Path $vd 'workflow/README.md')
$spr    = Read-Utf8 (Join-Path $vd 'agent/specialized/README.md')
$agr    = Read-Utf8 (Join-Path $vd 'agent/README.md')
$dtr    = Read-Utf8 (Join-Path $vd 'docs_template/README.md')
$pds    = Read-Utf8 (Join-Path $vd 'guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md')
$chl    = Read-Utf8 (Join-Path $vd 'releases/CHANGELOG.md')
$claude = Read-Utf8 (Join-Path $sdd 'CLAUDE.md')
$snapPy = Read-Utf8 (Join-Path $sdd 'scripts/framework_status_snapshot.py')
$specN  = @(Get-ChildItem -LiteralPath (Join-Path $vd 'agent/specialized') -Filter '*.yaml' -File).Count
$tmplF  = @(Get-ChildItem -LiteralPath (Join-Path $vd 'docs_template/sdd') -Recurse -File | Where-Object { $_.Extension -in '.md', '.yaml' })
$tmplN  = $tmplF.Count
$tmplMd = @($tmplF | Where-Object { $_.Extension -eq '.md' }).Count
$reqN   = @(Get-ChildItem -LiteralPath (Join-Path $vd 'docs_template/sdd/requirements') -File).Count
$wfN    = [int]([regex]::Match($wfr, '共\s*(\d+)\s*個工作流').Groups[1].Value)
function Get-Int([string]$Text, [string]$Rx) { $m = [regex]::Match($Text, $Rx); if ($m.Success) { [int]$m.Groups[1].Value } else { -1 } }
$q = [regex]::Match($agr, '被訂正的原文逐字保留——「共 \*\*(\d+) 個 Specialized（(\d+) persona/specialized \+ (\d+) 系統級 runtime \+ (\d+) 橋接 agent）\*\*：」')
$ck = [ordered]@{}
$ck['INIT auto_load_config：兩支 agent 各一條'] = ([regex]::Matches($init, 'path: "agent/specialized/(research-analyst|spec-engineer)-zh\.yaml"').Count -eq 2)
$ck['INIT Agent 清單表：兩列'] = ([regex]::Matches($init, '(?m)^\| `agent/specialized/(research-analyst|spec-engineer)-zh\.yaml` \|').Count -eq 2)
$ck['INIT Workflow 清單：SDD_RESEARCH_TO_PRD.md'] = $init.Contains('| `SDD_RESEARCH_TO_PRD.md` |')
foreach ($t in 'ISSUE-SCOPE', 'EVIDENCE-MATRIX', 'PRD-SPEC-ENGINEERED', 'ADVERSARIAL-REVIEW-CARD') {
    $ck["INIT 模板索引：$t"] = ([regex]::Matches($init, ('(?m)^\| \*\*requirements\*\* \| `' + $t + '-TEMPLATE\.md` \|')).Count -eq 1)
}
$ck['INIT 計數：Specialized＝磁碟'] = ((Get-Int $init 'Specialized Agents（(\d+) 個）') -eq $specN)
$ck['INIT 計數：模板索引＝磁碟'] = ((Get-Int $init '## SDD 模板索引（(\d+) 個）') -eq $tmplN)
$ck['workflow/README：小節與總數句'] = ($wfr.Contains('sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md') -and $wfr.Contains('1 個 Research-to-PRD Workflow'))
$ck['agent/specialized/README：兩列、職責小節、場景表'] = ([regex]::Matches($spr, '(?m)^\| `(research-analyst|spec-engineer)-zh\.yaml` \|').Count -eq 2 -and $spr.Contains('### Research Analyst／Spec Engineer — Stage-0 研究到規格') -and $spr.Contains('| Stage-0（任何場景的前置：研究到規格） |'))
$ck['AISDLC_SDD/CLAUDE.md Rule 6：兩列'] = ([regex]::Matches($claude, '(?m)^\| `(research-analyst|spec-engineer)-zh\.yaml` \|').Count -eq 2)
$ck['docs_template/README：狀態行、目錄樹（總數與 md 數）、需求類計數＝磁碟'] = ((Get-Int $dtr '含 (\d+) 個 SDD 專屬模板') -eq $tmplN -and (Get-Int $dtr 'SDD 專屬模板（(\d+) 個：\d+ md \+ \d+ yaml）') -eq $tmplN -and (Get-Int $dtr 'SDD 專屬模板（\d+ 個：(\d+) md \+ \d+ yaml）') -eq $tmplMd -and (Get-Int $dtr '需求類（(\d+) 個）') -eq $reqN)
$ck['docs_template/README：需求類清單、路徑表一句、更新歷史、日期'] = ($dtr.Contains('、ISSUE-SCOPE、EVIDENCE-MATRIX、PRD-SPEC-ENGINEERED、ADVERSARIAL-REVIEW-CARD') -and $dtr.Contains('研究到規格（Stage-0）的四份模板') -and $dtr.Contains('### ResearchSOPtoPRD Stage-0 模板 (2026-11-02)') -and ([regex]::Match($dtr, '\*\*最後更新\*\*: (\d{4}-\d{2}-\d{2})').Groups[1].Value -ge '2026-11-02'))
$ck['agent/README：計數句＝磁碟，訂正引言保留原文且數字不同'] = ((Get-Int $agr '共 \*\*(\d+) 個 Specialized（') -eq $specN -and $q.Success -and ([int]$q.Groups[1].Value) -lt $specN)
$ck['agent/README：目錄樹三項、Stage-0 小節、稽核者清單項'] = ($agr.Contains('├── research-analyst-zh.yaml') -and $agr.Contains('├── spec-engineer-zh.yaml') -and $agr.Contains('├── sdd-zero-trust-auditor-zh.yaml') -and $agr.Contains('### Stage-0 研究到規格（任何場景的可選前置；ResearchSOPtoPRD）') -and $agr.Contains('- `sdd-zero-trust-auditor-zh.yaml` - '))
$ck['agent/README：FAQ 合計＝磁碟，原文逐字保留於訂正引言'] = ((Get-Int $agr '合計 (\d+) 個 Specialized（計數見上方與 FRAMEWORK_STATUS\.md）。') -eq $specN -and $agr.Contains('被訂正的原文逐字保留——「A: 是的！v0.09 起所有 '))
$ck['PROJECT_DOCUMENTATION_STANDARDS：Workflow 定義數＝workflow/README 總數'] = ($wfN -gt 0 -and (Get-Int $pds 'Workflow 定義（(\d+) 個）') -eq $wfN)
$ck['AISDLC_SDD/CLAUDE.md：Rule 2 目錄樹與快速參考表'] = ($claude.Contains('← 工作流（1 SDD Gate + core + scenario + ADR + Research-to-PRD）') -and $claude.Contains('workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md` |') -and (Test-Path -LiteralPath (Join-Path $vd 'workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md')))
$ck['CHANGELOG：頂部日期與新條目'] = (([regex]::Match($chl, '\*\*最後更新\*\*: (\d{4}-\d{2}-\d{2})').Groups[1].Value -ge '2026-11-02') -and $chl.Contains('（ResearchSOPtoPRD 框架層：Stage-0 研究到規格；'))
$ck['framework_status_snapshot.py：組成字串含 +1 Research-to-PRD（主控 D-47 補丁）'] = $snapPy.Contains('1 Gate+8 core+13 scenario+1 ADR+1 Research-to-PRD')
$ck.GetEnumerator() | ForEach-Object { '{0} {1}' -f $(if ($_.Value) { 'PASS' } else { 'FAIL' }), $_.Key }
Show-Result 'AT-970-2-1' (@($ck.Values | Where-Object { -not $_ }).Count -eq 0) "specialized=$specN templates=$tmplN workflows=$wfN"
```

預期輸出：二十一行 `PASS …`、`RESULT AT-970-2-1 PASS specialized=<磁碟實數> templates=<磁碟實數> workflows=<磁碟實數>`（對 repo 現檔實跑：specialized=23、templates=63、workflows=24；以磁碟為準）。

**AT-970-2-2**（Integration）Given 重生後的 `FRAMEWORK_STATUS.md` When 跑 `framework_status_snapshot.py --check` Then rc 0。

```powershell
# AT-970-2-2
$o = & $py (Join-Path $sdd 'scripts/framework_status_snapshot.py') --check --repo-root $sdd
$rc = $LASTEXITCODE
$o
Show-Result 'AT-970-2-2' ($rc -eq 0) "rc=$rc"
```

預期輸出：`✅ FRAMEWORK_STATUS.md 新鮮（與磁碟/權威源一致）`、`RESULT AT-970-2-2 PASS rc=0`。

**AT-970-2-E-1**（Integration，負控）Given 暫存迷你樹（兩個版本目錄各一支 agent，已 `--write`）When 注入「多一支 specialized agent 而不重生」 Then `--check` 由 rc 0 變 rc 1（證明新鮮度檢查有鑑別力；這也是「重生必須是最後一步」的理由）。

```powershell
# AT-970-2-E-1
$t = Join-Path $tmp 'snap'
foreach ($v in 'AISDLC_SDD_v0.01', 'AISDLC_SDD_v0.02') {
    foreach ($d in 'agent/core', 'agent/specialized', 'workflow') { New-Item -ItemType Directory -Force -Path (Join-Path (Join-Path $t $v) $d) | Out-Null }
    Write-Utf8 (Join-Path $t "$v/agent/core/a.yaml") "agent:`n  id: a`n"
    Write-Utf8 (Join-Path $t "$v/workflow/README.md") "共 1 個工作流`n"
}
$snap = Join-Path $sdd 'scripts/framework_status_snapshot.py'
$null = & $py $snap --write --repo-root $t
$rcW = $LASTEXITCODE
$null = & $py $snap --check --repo-root $t
$rcFresh = $LASTEXITCODE
Write-Utf8 (Join-Path $t 'AISDLC_SDD_v0.02/agent/specialized/b.yaml') "agent:`n  id: b`n"
$null = & $py $snap --check --repo-root $t 2>$null
$rcStale = $LASTEXITCODE
"write rc=$rcW; fresh rc=$rcFresh; stale rc=$rcStale"
Show-Result 'AT-970-2-E-1' ($rcW -eq 0 -and $rcFresh -eq 0 -and $rcStale -eq 1)
```

預期輸出：`write rc=0; fresh rc=0; stale rc=1`、`RESULT AT-970-2-E-1 PASS`。

### 2.3 AC-970-3：JSON 契約自洽

**AT-970-3-1**（Contract）Given 本檔附錄 A 的契約檢核器 When 對版本目錄跑 Then 9 個契約區塊 0 項問題、rc 0（抽出方式：以標記 `<!-- r2p:verifier=contract_check -->` 後第一個 python 圍欄；抽取本身也在驗證附錄 A 逐字可用；上位：AC-R2P-05-7、AC-R2P-08-1）。

```powershell
# AT-970-3-1
$fence = '`' * 3
$tcsText = Read-Utf8 (Join-Path $vd 'docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md')
$rx = '(?s)<!-- r2p:verifier=contract_check -->\r?\n' + [regex]::Escape($fence) + 'python\r?\n(.*?)\r?\n' + [regex]::Escape($fence)
$m = [regex]::Match($tcsText, $rx)
$chk = Join-Path $tmp 'r2p_contract_check.py'
if ($m.Success) { Write-Utf8 $chk ($m.Groups[1].Value + "`n") }
$o = & $py -I -X utf8 $chk $vd
$rc = $LASTEXITCODE
$o
Show-Result 'AT-970-3-1' ($m.Success -and $rc -eq 0 -and (($o -join "`n") -match '9 個契約區塊、0 項問題')) "rc=$rc"
```

預期輸出：七行 `OK   <契約群組>`（issue_scope、evidence_items、review_params、rubric_registry、review_dimension、review_dimension_qa、review_card）、`r2p_contract_check: 9 個契約區塊、0 項問題`、`RESULT AT-970-3-1 PASS rc=0`。

**AT-970-3-2**（Contract）Given 同一檢核器 When 跑 `--selftest` Then 對記憶體內範例逐一注入 29 種錯誤（含彙整卡的 `prd_version_no` 缺漏、型別、對應衝突、遞減，`fsm.gate_result` 為 null 的誤用，以及已移除的 `REVIEW_INVALID` verdict），全部被抓到（漏網 0）；另對 1 個合法變體（POST_HUMAN 再審通過的輪 `fsm.gate_result` 與 `retry_count` 皆 null）不誤判（誤判 0）；rc 0（證明判準有鑑別力、也沒有過嚴；主控 D-54、D-55）。

```powershell
# AT-970-3-2
$o = & $py -I -X utf8 $chk $vd --selftest
$rc = $LASTEXITCODE
$o
Show-Result 'AT-970-3-2' ($rc -eq 0 -and (($o -join "`n") -match '29 個注入錯誤，漏網 0；1 個合法變體，誤判 0')) "rc=$rc"
```

預期輸出：`r2p_contract_check selftest: 29 個注入錯誤，漏網 0；1 個合法變體，誤判 0`、`RESULT AT-970-3-2 PASS rc=0`。

**AT-970-3-E-1**（Contract，負控）Given 四份模板的暫存複本 When 移除 `review_params` 的契約標記 Then 檢核器 rc 1 並指名該標記（缺一個標記＝Bridge 契約對拍測試抽不到該區塊）。

```powershell
# AT-970-3-E-1
$tv  = Join-Path $tmp 'ver'
$req = Join-Path $tv 'docs_template/sdd/requirements'
New-Item -ItemType Directory -Force -Path $req | Out-Null
foreach ($f in Get-ChildItem -LiteralPath (Join-Path $vd 'docs_template/sdd/requirements') -Filter '*-TEMPLATE.md' -File) { Copy-Item -LiteralPath $f.FullName -Destination $req }
$card = Join-Path $req 'ADVERSARIAL-REVIEW-CARD-TEMPLATE.md'
$orig = Read-Utf8 $card
$mut  = $orig.Replace('<!-- r2p:contract=review_params -->', '')
Write-Utf8 $card $mut
$o = & $py -I -X utf8 $chk $tv
$rc = $LASTEXITCODE
$o
Show-Result 'AT-970-3-E-1' ($orig -ne $mut -and $rc -eq 1 -and (($o -join "`n") -match 'FAIL marker review_params')) "rc=$rc"
```

預期輸出：`FAIL marker review_params: 找到 0 個（必須恰 1 個）`、`RESULT AT-970-3-E-1 PASS rc=1`。

### 2.4 AC-970-4：框架治理閘不退步

**AT-970-4-1**（Integration）Given 新增兩支 agent When 跑四支 agent lint（版本無關 shared infra，與 `ci-gate.sh` 同一組呼叫） Then 皆 rc 0（上位：AC-R2P-04-9 的 persona 載入前提——`agent.version` 不寫死、template 引用可解析）。

```powershell
# AT-970-4-1
$res = foreach ($l in 'agent_template_lint', 'collaboration_symmetry_lint', 'scenario_frequency_lint', 'agent_scg_anchor_lint') {
    $o = & $py (Join-Path $sdd "scripts/$l.py") $sdd
    '{0}: rc={1}' -f $l, $LASTEXITCODE
}
$res
Show-Result 'AT-970-4-1' (@($res | Where-Object { $_ -notmatch 'rc=0$' }).Count -eq 0)
```

預期輸出：四行 `<lint 名>: rc=0`、`RESULT AT-970-4-1 PASS`。

**AT-970-4-2**（Integration）Given 版本目錄 When 跑 `arch_fitness --strict`（從版本目錄、不帶 `-I`：`-I` 會丟掉 cwd 而 import 失敗） Then `n_fail` 為 0，FF-6、FF-7、FF-13、FF-15 皆為 info；rc 為 0 或 1（1＝既有的 advisory 警告，如 FF-5、FF-16，與本鍵無關）。

```powershell
# AT-970-4-2
$afJson = Join-Path $tmp 'af.json'
Push-Location $vd -ErrorAction Stop
$null = & $py -m tools.arch_fitness.arch_fitness --strict --json $afJson
$rc = $LASTEXITCODE
Pop-Location
$af  = (Read-Utf8 $afJson) | ConvertFrom-Json
$sel = @($af.findings | Where-Object { $_.ff -in 'FF-6', 'FF-7', 'FF-13', 'FF-15' })
$sel | ForEach-Object { '{0} {1} {2}' -f $_.ff, $_.severity, $_.title }
$okSel = ($sel.Count -ge 4 -and @($sel | Where-Object { $_.severity -ne 'info' }).Count -eq 0)
Show-Result 'AT-970-4-2' (($rc -in 0, 1) -and $af.n_fail -eq 0 -and $okSel) "rc=$rc n_fail=$($af.n_fail) n_warn=$($af.n_warn)"
```

預期輸出（對 repo 現檔實跑）：`FF-6 info 文件相對連結完整`、`FF-7 info Agent↔Workflow↔Skill 引用健康`、`FF-13 info 全部 30 個 agent YAML 嚴格合法且具 agent 定義鍵`、`FF-15 info SDD 模板索引與磁碟一致（63 個模板全索引、全可解析）`、`RESULT AT-970-4-2 PASS rc=1 n_fail=0 n_warn=3`。`n_warn=3` 是改動前就存在的 FF-5、FF-16（兩筆）advisory，在改動前的起點 commit `01d9be6e` 上跑同值（可用 `git archive 01d9be6e AISDLC_SDD` 解出複本對照），所以 rc=1 屬預期；數字 30、63 與 `n_warn` 以磁碟現值為準。

**AT-970-4-3**（Integration）Given 本鍵未新增 skill When 跑 skills 鏡像與版本戳記檢查 Then 皆 rc 0。

```powershell
# AT-970-4-3
$o1 = & $py (Join-Path $sdd 'scripts/skill_header_sync.py') --check --repo-root $sdd
$r1 = $LASTEXITCODE
$o2 = & $py (Join-Path $sdd 'scripts/sync_exposed_skills.py') --check --repo-root $sdd
$r2 = $LASTEXITCODE
"skill_header_sync rc=$r1; sync_exposed_skills rc=$r2"
Show-Result 'AT-970-4-3' ($r1 -eq 0 -and $r2 -eq 0)
```

預期輸出：`skill_header_sync rc=0; sync_exposed_skills rc=0`、`RESULT AT-970-4-3 PASS`。

**AT-970-4-4**（E2E，長時間）Given 全部編修與重生完成 When 跑本機 CI 閘門 `ci-gate.ps1` Then rc 0。**以 `run_in_background` 掛，不在前景等**；harness 不跑此項，結果由 QA 貼進證據檔。

```powershell
# AT-970-4-4（長時間；背景執行）
$log = Join-Path $tmp 'ci-gate.log'
if ([System.Environment]::OSVersion.Platform -eq 'Win32NT') {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $sdd 'scripts/ci-gate.ps1') *> $log      # Windows：PS 5.1 語意的對等腳本
} else {
    & bash (Join-Path $sdd 'scripts/ci-gate.sh') *> $log                                                           # mac／Linux：bash 原版
}
$rc = $LASTEXITCODE
Show-Result 'AT-970-4-4' ($rc -eq 0) "rc=$rc log=$log"
```

預期輸出：`RESULT AT-970-4-4 PASS rc=0 log=<暫存路徑>`；`$log` 末段須含 `[3/3]` 之後的通過摘要（逐字貼證據）。

**AT-970-4-E-1**（Integration，負控）Given 暫存版本樹（`AISDLC_SDD_v0.99`，含一份真模板與一支引用它的 agent）When 把 agent 的模板引用改成不存在的檔 Then `agent_template_lint` rc 1 並印 `BROKEN`；改回真檔後 rc 0（證明 AT-970-4-1 的綠燈不是 lint 失明）。

```powershell
# AT-970-4-E-1
$g  = Join-Path $tmp 'lint'
$gv = Join-Path $g 'AISDLC_SDD_v0.99'
foreach ($d in 'agent/specialized', 'docs_template/sdd/requirements') { New-Item -ItemType Directory -Force -Path (Join-Path $gv $d) | Out-Null }
Write-Utf8 (Join-Path $gv 'docs_template/sdd/requirements/REAL-TEMPLATE.md') "# real`n"
$y    = Join-Path $gv 'agent/specialized/x-zh.yaml'
$lint = Join-Path $sdd 'scripts/agent_template_lint.py'
$q    = '"'
Write-Utf8 $y ("agent:`n  id: x`ndependencies:`n  templates:`n    - " + $q + "docs_template/sdd/requirements/GHOST-TEMPLATE.md" + $q + "`n")
$o = & $py $lint $g
$rcBad = $LASTEXITCODE
Write-Utf8 $y ("agent:`n  id: x`ndependencies:`n  templates:`n    - " + $q + "docs_template/sdd/requirements/REAL-TEMPLATE.md" + $q + "`n")
$null = & $py $lint $g
$rcGood = $LASTEXITCODE
$o
"ghost rc=$rcBad; real rc=$rcGood"
Show-Result 'AT-970-4-E-1' ($rcBad -eq 1 -and $rcGood -eq 0 -and (($o -join "`n") -match 'BROKEN'))
```

預期輸出：`::error:: agent template lint 失敗（AISDLC_SDD_v0.99）`、`BROKEN  agent/specialized/x-zh.yaml:5 docs_template/sdd/requirements/GHOST-TEMPLATE.md` 與 `BROKEN  agent/specialized/x-zh.yaml dependencies.templates: docs_template/sdd/requirements/GHOST-TEMPLATE.md`、`ghost rc=1; real rc=0`、`RESULT AT-970-4-E-1 PASS`。

### 2.5 AC-970-5：變更邊界與追溯

> 前置：`$base` 必須先設為**起點 commit**＝框架鍵開工前的 `git rev-parse HEAD`，本鍵為 **`01d9be6e`**（本鍵 Stage-1 的基準 commit；落檔 commit 是 `25c66981`）：`$base = (git -C $root rev-parse 01d9be6e)`。`$base` 若設成 `HEAD` 而變更已 commit，比對結果會是空集合而假綠——所以 AT-970-5-1 起手就擋掉未設值。

**AT-970-5-1**（Integration）Given 起點 commit 與目前工作樹 When 列出整個 repo 相對起點的追蹤檔變更，加上 `AISDLC_SDD`、`tools`、`.claude`、`.github` 範圍內的未追蹤檔 Then 每個路徑都在 24 條白名單（9 個新增檔、版本目錄內 12 個被改檔、`AISDLC_SDD/CLAUDE.md`、主控補丁 `AISDLC_SDD/scripts/framework_status_snapshot.py`、重生的 `AISDLC_SDD/FRAMEWORK_STATUS.md`）、版本目錄 `docs/06_quality/`（報告與 RTM 落點，BRIDGE §8.5），或主控收尾單窗的根層連動例外清單（主控 D-46，逐字 8 條：`.gitignore`、`.github/workflows/agentconsole-ci.yml`、`docs/01_requirements/ResearchToPRD_PRD.md`、`docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`、`docs/01_requirements/Agent_ConsoleUI_PRD.md`、`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`、`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`、`AgentConsole/**`）之內；根層 `tools/`、`.claude/` 必須為空，不接受任何例外。追蹤檔變更掃整個 repo，是因為 D-46 的例外清單住在 `AISDLC_SDD` 範圍之外；未追蹤檔仍只掃四個範圍（根層其他未追蹤的文件由主控收尾單窗處置，不歸本鍵判）。來源規格逐字檔 `ResearchSOPtoPRD_Source_Spec.md` 在起點 commit 之後的 W0 落檔 commit 才首次入庫，所以列入清單（勘誤 1）。

```powershell
# AT-970-5-1
if (-not $base) { throw '先設 $base：起點 commit（框架鍵開工前的 git rev-parse HEAD；本鍵為 01d9be6e）' }
$allowed = @($new9 + $edited12 | ForEach-Object { "AISDLC_SDD/$ver/$_" }) + @('AISDLC_SDD/CLAUDE.md', 'AISDLC_SDD/scripts/framework_status_snapshot.py', 'AISDLC_SDD/FRAMEWORK_STATUS.md')
# 根層連動的已知例外（主控 D-46；與 ADR-XPLAT-017 §D7 機械核對法的清單逐字同步）：主控收尾單人窗口的 W0 連動檔，不是框架鍵視窗的變更。
# 清單是逐字比對、不是萬用字元（只有 AgentConsole/ 是目錄前綴）；其餘任何根層路徑一律違規，tools／.claude 零例外
$rootExempt = @(
    '.gitignore',
    '.github/workflows/agentconsole-ci.yml',
    'docs/01_requirements/ResearchToPRD_PRD.md',
    'docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md',
    'docs/01_requirements/Agent_ConsoleUI_PRD.md',
    'docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md',
    'docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md')
$rootExemptDirs = @('AgentConsole/')
function Test-RootExempt([string]$P) {
    if ($rootExempt -contains $P) { return $true }
    foreach ($d in $rootExemptDirs) { if ($P.StartsWith($d, [StringComparison]::Ordinal)) { return $true } }
    return $false
}
function Get-BoundaryViolations([string[]]$Paths) {
    foreach ($p in $Paths) {
        if (-not $p) { continue }
        if ($p -eq 'tools' -or $p.StartsWith('tools/', [StringComparison]::Ordinal) -or $p -eq '.claude' -or $p.StartsWith('.claude/', [StringComparison]::Ordinal)) { $p; continue }
        if ($allowed -contains $p) { continue }
        if (Test-RootExempt $p) { continue }
        if ($p -like "AISDLC_SDD/$ver/docs/06_quality/*") { continue }
        $p
    }
}
$untrackedScope = 'AISDLC_SDD', 'tools', '.claude', '.github'
$tracked   = @(git -c core.quotepath=false -C $root diff --name-only $base)
$untracked = @(git -c core.quotepath=false -C $root ls-files --others --exclude-standard -- @untrackedScope)
$changed = @($tracked) + @($untracked)
$viol    = @(Get-BoundaryViolations $changed)
'whitelist size: ' + $allowed.Count
'root exempt entries: ' + ($rootExempt.Count + $rootExemptDirs.Count)
'changed paths: ' + $changed.Count
$viol
Show-Result 'AT-970-5-1' ($viol.Count -eq 0 -and $allowed.Count -eq 24 -and ($rootExempt.Count + $rootExemptDirs.Count) -eq 8) "violations=$($viol.Count)"
```

預期輸出：`whitelist size: 24`、`root exempt entries: 8`、`changed paths: <N>`（N 以實際變動為準：新增與被改檔、`docs/06_quality/` 報告，加上收尾單窗的根層連動檔）、`RESULT AT-970-5-1 PASS violations=0`。

**AT-970-5-2**（Integration）Given 同一起點 When 檢查受保護路徑 Then `_HAPPY_PATH` 所在的 `transition_rules.py`、`formal/`、`governance/rules/`、兩處 `.claude/`、`PRD_Universal_Template.md`、根層 `tools/`、`.claude/`、`.github/` 皆零差異（`_HAPPY_PATH` 不變 ⇒ 免跑 TLC；唯一例外是 AT-970-5-1 的 `$rootExempt` 清單內的 `.github/workflows/agentconsole-ci.yml`）。

```powershell
# AT-970-5-2
$prot = "AISDLC_SDD/$ver/tools/fsm_runtime/transition_rules.py", "AISDLC_SDD/$ver/tools/fsm_runtime/formal", "AISDLC_SDD/$ver/governance/rules", "AISDLC_SDD/$ver/.claude", 'AISDLC_SDD/.claude', "AISDLC_SDD/$ver/docs_template/core/prd/PRD_Universal_Template.md", 'tools', '.claude', '.github'
$d = @(@(git -c core.quotepath=false -C $root diff --name-only $base -- @prot) + @(git -c core.quotepath=false -C $root ls-files --others --exclude-standard -- @prot) | Where-Object { $_ -and -not (Test-RootExempt $_) })
$d
Show-Result 'AT-970-5-2' ($d.Count -eq 0) "protected paths changed=$($d.Count)"
```

預期輸出：`RESULT AT-970-5-2 PASS protected paths changed=0`。（`$rootExempt`、`Test-RootExempt` 沿用 AT-970-5-1。）

**AT-970-5-3**（Integration）Given 本鍵 Stage-1 已採納、其後的 `spec-refreeze` 已重記（在本鍵視窗，三件組已設） When 以唯讀 `show` 取 `frozen_stages` **全部條目**的 `spec_doc_digests`，依序取聯集（同鍵後者勝出；含 `spec-refreeze` 追加的重記條目——其 `stage` 取最近一筆〔`state_loader.py` 的 `record_spec_refreeze`〕，所以不能只讀 `Stage-1` 那一筆），與本檔〈增量追溯表〉的五個摘要逐鍵比對 Then 逐值相等；不等＝表過期（文件於凍結後被改而未重記，或表未更新），須先 `spec-refreeze` 或更新本表再送審（`show` 不是寫入動詞；上位：AC-R2P-11-7、AC-R2P-19-8）。

```powershell
# AT-970-5-3（需在本鍵視窗執行：SDD_STATE_DIR 與 SDD_PROJECT 已是 sdd-research-to-prd 的三件組）
if (-not $env:SDD_STATE_DIR -or -not $env:SDD_PROJECT) { throw '需在本鍵視窗（三件組已設）執行' }
Push-Location $vd -ErrorAction Stop
$out = & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project $env:SDD_PROJECT --must-exist
$rc = $LASTEXITCODE
Pop-Location
$j = ($out -join "`n") | ConvertFrom-Json
$eff = @{}                                    # 有效凍結摘要：frozen_stages 全部條目依序取聯集、同鍵後者勝出（含 spec-refreeze 追加的重記條目；與 AutoClaude check_digest、Bridge 的消費語意相同）
foreach ($e in @($j.fsm_state.frozen_stages)) { if ($e.spec_doc_digests) { foreach ($p in $e.spec_doc_digests.PSObject.Properties) { $eff[$p.Name] = $p.Value } } }
$tcsText = Read-Utf8 (Join-Path $vd 'docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md')
$want = [ordered]@{}
foreach ($m in [regex]::Matches($tcsText, '(?m)^> \| U\d \| [^|]+ \| `([^`]+)` \| `(sha256:[0-9a-f]{64})` \|$')) { $want[$m.Groups[1].Value] = $m.Groups[2].Value }
$bad = @(foreach ($k in $want.Keys) { if ($eff[$k] -ne $want[$k]) { "$k : 表=$($want[$k]) 凍結=$($eff[$k])" } })
$bad
Show-Result 'AT-970-5-3' ($rc -eq 0 -and $want.Count -eq 5 -and $bad.Count -eq 0) "rc=$rc table_rows=$($want.Count)"
```

預期輸出：`RESULT AT-970-5-3 PASS rc=0 table_rows=5`。重算指令（唯讀；主控在 `spec-refreeze` 前先算好填表，CLI 重記的值為準；`-B` 使重算不在 repo 內寫 `__pycache__`）：

```powershell
# 摘要重算（唯讀；框架自己的 spec_digest 演算法：換行正規化後 UTF-8 的 SHA-256；鍵＝相對 monorepo 根的正斜線路徑，與 spec-frozen --root＝monorepo 根 時的鍵逐字相同）
$dg = @'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tools.fsm_runtime.spec_digest import digest_doc
for doc in sys.argv[3:]:
    print(doc + '\t' + digest_doc(Path(sys.argv[2]), doc)[1])
'@
$dgFile = Join-Path $tmp 'digest_docs.py'
Write-Utf8 $dgFile $dg
& $py -B -I -X utf8 $dgFile $vd $root 'AISDLC_SDD/CLAUDE.md' "AISDLC_SDD/$ver/AISDLC_SDD_INIT.md" "AISDLC_SDD/$ver/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md" 'docs/01_requirements/ResearchToPRD_PRD.md' "AISDLC_SDD/$ver/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md"
```

**AT-970-5-E-1**（Unit，負控）Given 邊界函式（沿用 AT-970-5-1 的 `$allowed`、`$rootExempt` 與 `Get-BoundaryViolations`） When 餵入合成路徑 Then 越界者被回報（含清單外的根層文件、清單外的 `scripts/` 檔、根層 `.claude/`，以及與清單內檔名近似的 `ResearchSOPtoPRD_Source_Spec.md.bak`——清單是逐字比對、不是前綴）；白名單、D-46 清單（含 `ResearchSOPtoPRD_Source_Spec.md`）與 `docs/06_quality/` 內者不被回報。

```powershell
# AT-970-5-E-1
$c1  = @(Get-BoundaryViolations @("AISDLC_SDD/$ver/tools/fsm_runtime/transition_rules.py")).Count -eq 1
$c2  = @(Get-BoundaryViolations @('AISDLC_SDD/AISDLC_SDD_v0.01/workflow/README.md')).Count -eq 1
$c3  = @(Get-BoundaryViolations @('tools/lib/selfimproving/x.py')).Count -eq 1
$c3b = @(Get-BoundaryViolations @('.claude/hooks/x.py')).Count -eq 1
$okPaths = @(
    "AISDLC_SDD/$ver/docs/06_quality/RTM-x.md", "AISDLC_SDD/$ver/AISDLC_SDD_INIT.md", "AISDLC_SDD/$ver/docs_template/README.md",
    "AISDLC_SDD/$ver/agent/README.md", "AISDLC_SDD/$ver/guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md",
    'AISDLC_SDD/CLAUDE.md', 'AISDLC_SDD/scripts/framework_status_snapshot.py', 'AISDLC_SDD/FRAMEWORK_STATUS.md',
    '.gitignore', '.github/workflows/agentconsole-ci.yml', 'docs/01_requirements/ResearchToPRD_PRD.md', 'docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md',
    'docs/01_requirements/Agent_ConsoleUI_PRD.md',
    'docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md', 'docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md',
    'AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md')
$c4  = @(Get-BoundaryViolations $okPaths).Count -eq 0
$c5  = @(Get-BoundaryViolations @('.github/workflows/other.yml')).Count -eq 1
$c6  = @(Get-BoundaryViolations @('docs/01_requirements/Other_PRD.md', 'ONBOARDING.md', 'docs/04_planning/ADR/ADR-XPLAT-099-other.md', 'docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md.bak')).Count -eq 4
$c7  = @(Get-BoundaryViolations @('AISDLC_SDD/scripts/other.py')).Count -eq 1
"transition_rules flagged=$c1; frozen baseline flagged=$c2; root tools flagged=$c3; root .claude flagged=$c3b; allowed and exempt not flagged=$c4; other workflow flagged=$c5; off-list root docs flagged=$c6; other script flagged=$c7"
Show-Result 'AT-970-5-E-1' ($c1 -and $c2 -and $c3 -and $c3b -and $c4 -and $c5 -and $c6 -and $c7)
```

預期輸出：`transition_rules flagged=True; frozen baseline flagged=True; root tools flagged=True; root .claude flagged=True; allowed and exempt not flagged=True; other workflow flagged=True; off-list root docs flagged=True; other script flagged=True`、`RESULT AT-970-5-E-1 PASS`。

### 2.6 AC-970-6：文件內容對齊

**AT-970-6-1**（Unit）Given 工作流、ADR 與兩份模板 When 抽出章節、決策編號與指定條文 Then 工作流章節 0～14 連號；ADR 決策恰 D1～D7，且各決策行含 PRD §9.5 的關鍵語；工作流表頭引用根層 PRD；ADR 引用 FR-R2P 與 AC-R2P；恢復後預算句（主控 D-60）同時住在工作流第 2.5 節與審查卡模板第 2.3 節；SE-PRD 模板 P0-7 列的四個預檢代碼逐處計數（`CITES_MISSING` 1、`CITES_V1` 2、`CITES_UNANCHORED` 1、`CITES_CANDIDATE` 2，且每個都有「否則 `代碼`」定義子句；與根層 PRD §5.1.3 同名）；審查卡模板第 5.3 節寫明缺陷狀態的合法轉移（`REGRESSED`→`FIXED` 是 `REGRESSED` 的唯一出口、其餘一律拒；與 Console 資料庫的轉移矩陣一致）（上位：PRD §9.5「框架 ADR-001」列；AC-R2P-02-11）。

```powershell
# AT-970-6-1
$wf  = Read-Utf8 (Join-Path $vd 'workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md')
$adr = Read-Utf8 (Join-Path $vd 'docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md')
$card = Read-Utf8 (Join-Path $vd 'docs_template/sdd/requirements/ADVERSARIAL-REVIEW-CARD-TEMPLATE.md')
$sepr = Read-Utf8 (Join-Path $vd 'docs_template/sdd/requirements/PRD-SPEC-ENGINEERED-TEMPLATE.md')
$chap = @([regex]::Matches($wf, '(?m)^## (\d+)\. ') | ForEach-Object { [int]$_.Groups[1].Value })
$dec  = @([regex]::Matches($adr, '(?m)^\*\*D(\d+)\u3000') | ForEach-Object { [int]$_.Groups[1].Value })
$kw = @('不新增 scenario', '審查沿用既有四支', '不新增 `governance/rules/R-*.yaml`', '四份模板', 'Stage 與鍵命名', '框架不含網路或資料庫程式', '評分卡是 SCG-0 的評估器')
$kwOk = @(foreach ($n in 1..7) { $line = [regex]::Match($adr, ('(?m)^\*\*D' + $n + '\u3000.*$')).Value; $line.Contains($kw[$n - 1]) })
$d60    = 'ESCALATION 人工恢復後預算不歸零：至多再得一次審查，FAIL 立即再 ESCALATION、PASS 歸零；全新預算＝換世代鍵'      # 主控 D-60
$wf25   = [regex]::Match($wf,   '(?s)\n### 2\.5 .*?(?=\n### 2\.6 )').Value
$card23 = [regex]::Match($card, '(?s)\n### 2\.3 .*?(?=\n## 3\. )').Value
$card53 = [regex]::Match($card, '(?s)\n### 5\.3 .*?(?=\n## 6\. )').Value
$p07    = [regex]::Match($sepr, '(?m)^\| P0-7 \|.*$').Value
$codeCnt = [ordered]@{ 'CITES_MISSING' = 1; 'CITES_V1' = 2; 'CITES_UNANCHORED' = 1; 'CITES_CANDIDATE' = 2 }   # 與根層 PRD §5.1.3 同名；P0-7 列內各代碼的出現次數＝1 次定義子句（「否則 `代碼`」）加 V1、CANDIDATE 各 1 次說明子句；逐處計數，改動任一處即紅
$p07Ok = ($p07 -ne '')
foreach ($c in $codeCnt.Keys) { if (([regex]::Matches($p07, [regex]::Escape($c))).Count -ne $codeCnt[$c] -or -not $p07.Contains('否則 `' + $c + '`')) { $p07Ok = $false } }
$ck = [ordered]@{
    '工作流章節 0..14 連號'          = (($chap -join ',') -eq ((0..14) -join ','))
    'ADR 決策恰 D1..D7'              = (($dec -join ',') -eq '1,2,3,4,5,6,7')
    'D1..D7 各含 PRD §9.5 關鍵語'     = (@($kwOk | Where-Object { -not $_ }).Count -eq 0 -and $kwOk.Count -eq 7)
    '工作流表頭引用根層 PRD'          = $wf.Contains('docs/01_requirements/ResearchToPRD_PRD.md')
    'ADR 引用 FR-R2P 與 AC-R2P'      = ($adr -match 'FR-R2P-\d\d' -and $adr -match 'AC-R2P-\d\d-\d')
    '工作流第 2.5 節含恢復後預算句（D-60）'   = $wf25.Contains($d60)
    '審查卡模板第 2.3 節含恢復後預算句（D-60）' = $card23.Contains($d60)
    'SE-PRD 模板 P0-7 列：四個預檢代碼逐處計數且各有定義子句' = $p07Ok
    '審查卡模板第 5.3 節含缺陷狀態轉移矩陣'    = ($card53.Contains('`REGRESSED`→`FIXED`') -and $card53.Contains('其餘一律拒'))
}
$ck.GetEnumerator() | ForEach-Object { '{0} {1}' -f $(if ($_.Value) { 'PASS' } else { 'FAIL' }), $_.Key }
Show-Result 'AT-970-6-1' (@($ck.Values | Where-Object { -not $_ }).Count -eq 0) ('chapters=' + ($chap -join ','))
```

預期輸出：九行 `PASS …`、`RESULT AT-970-6-1 PASS chapters=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14`。

**AT-970-6-2**（Unit）Given 工作流第 2.6 節、第 8 章、BRIDGE §9.2、§9.3 與 SPEC_FIRST_GATE When 抽出動詞列、閘名、Gate 0 的 `--doc` 與人工退回做法 Then BRIDGE §9.2 動詞列恰為 `show、transition、gate、spec-refreeze、spec-frozen`；`gate` 列含四個閘；`resume-from-escalation` 不在動詞列、只在「仍不呼叫」句；§9.2 含 `gate` 實際使用面句（主控 D-45）；Gate 0 指令恰四個 `--doc` 且不含 TCS；SPEC_FIRST_GATE 列出同四份；工作流名稱對照含四個 stage 名；Bridge 守則「現態 HUMAN_PENDING 時不呼叫 gate PASS；再審通過只記 DB」同時住在 BRIDGE §9.3 與工作流第 8 章，且人工退回的做法（`gate SCG_VALIDATION FAIL "人工審查：…"`、狀態維持 HUMAN_PENDING）在 SPEC_FIRST_GATE 對照表第 5 列、工作流第 8 章、BRIDGE §9.3 三處一致（指令與「維持 HUMAN_PENDING」須在同一句或同一表列內並存，單處改文會被抓到；主控 D-50；上位：AC-R2P-10-1、AC-R2P-10-9、AC-R2P-19-8）。

```powershell
# AT-970-6-2
$br   = Read-Utf8 (Join-Path $vd 'workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md')
$gt   = Read-Utf8 (Join-Path $vd 'workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md')
$s92  = [regex]::Match($br, '(?s)### 9\.2 .*?(?=### 9\.3 )').Value
$s93  = [regex]::Match($br, '(?s)### 9\.3 .*?(?=### 9\.4 )').Value
$s8   = [regex]::Match($wf, '(?s)\n## 8\. .*?(?=\n## 9\. )').Value
$verbRows = @([regex]::Matches($s92, '(?m)^\| `([a-z-]+)`') | ForEach-Object { $_.Groups[1].Value })
$gateRow  = [regex]::Match($s92, '(?m)^\| `gate` \|.*$').Value
$notCall  = [regex]::Match($s92, '(?m)^仍\*\*不\*\*呼叫.*$').Value
$g0 = '01_specs/PRD-v1.0.0.md', '00_research/evidence_matrix.md', '00_research/issue_scope.json', '01_specs/adr_draft.md'
$row9   = [regex]::Match($wf, '(?m)^\| 9 \| 人核准 Gate 0 .*$').Value
$gtRow5 = [regex]::Match($gt, '(?m)^\| 5 \| .*$').Value
$d45 = '實際使用面見 ADR-XPLAT-017 §D2：外環鍵 SCG_VALIDATION 由 evaluator 與 ADMIN 退回呼叫；內環三閘由 Console 登錄 SCG-4／SCG-5／CI 結果時呼叫'
$d50 = '現態 HUMAN_PENDING 時不呼叫 gate PASS；再審通過只記 DB'
$rxHold = '(維持 HUMAN_PENDING[^。\n]{0,400}?SCG_VALIDATION[^。\n]{0,60}?FAIL)|(SCG_VALIDATION[^。\n]{0,60}?FAIL[^。\n]{0,400}?維持 HUMAN_PENDING)'      # 同一句（或同一表列）內：人工退回指令與「維持 HUMAN_PENDING」並存
$ck = [ordered]@{
    'BRIDGE 9.2 動詞列恰五個'                 = (($verbRows -join ',') -eq 'show,transition,gate,spec-refreeze,spec-frozen')
    'gate 列含四個閘'                         = (@('SCG_VALIDATION', 'PR_REVIEW', 'RTM_VERIFY', 'RELEASE_READY' | Where-Object { -not $gateRow.Contains($_) }).Count -eq 0)
    'resume-from-escalation 只在「仍不呼叫」句' = (($verbRows -notcontains 'resume-from-escalation') -and $notCall.Contains('resume-from-escalation'))
    'Gate 0 指令恰四個 --doc 且不含 TCS'       = (([regex]::Matches($row9, '--doc').Count -eq 4) -and -not $row9.Contains('TCS') -and (@($g0 | Where-Object { -not $row9.Contains($_) }).Count -eq 0))
    '工作流第 8 章列出同四份'                  = (@($g0 | Where-Object { -not $wf.Contains('| `' + $_ + '` |') }).Count -eq 0)
    'SPEC_FIRST_GATE 列出同四份'               = (@($g0 | Where-Object { -not $gt.Contains($_) }).Count -eq 0)
    '工作流名稱對照含四個 stage 名'             = (@('`Gate-0`', 'Gate-0-SCR<n>', '`Stage-1`', '`Stage-2`' | Where-Object { -not $wf.Contains($_) }).Count -eq 0)
    'BRIDGE 9.2 含 gate 實際使用面句（D-45）'   = $s92.Contains($d45)
    'BRIDGE 9.3 含 Bridge 守則句（D-50）'       = $s93.Contains($d50)
    '工作流第 8 章含同一守則句（D-50）'          = $s8.Contains($d50)
    '人工退回做法三處一致（第 5 列、第 8 章、9.3）' = (@($gtRow5, $s8, $s93 | Where-Object { $_.Contains('人工審查') -and [regex]::IsMatch($_, $rxHold) }).Count -eq 3)
}
$ck.GetEnumerator() | ForEach-Object { '{0} {1}' -f $(if ($_.Value) { 'PASS' } else { 'FAIL' }), $_.Key }
Show-Result 'AT-970-6-2' (@($ck.Values | Where-Object { -not $_ }).Count -eq 0) ('verbs=' + ($verbRows -join ','))
```

預期輸出：十一行 `PASS …`、`RESULT AT-970-6-2 PASS verbs=show,transition,gate,spec-refreeze,spec-frozen`。

**AT-970-6-3**（Unit）Given SE-PRD 模板與家規 `PRD_Universal_Template` When 以結構函式檢查 Then 回報 0 個問題：導讀 begin／end 標記各一、六節錨點各一、錨點後第一個非空行是標題、14 章標題逐字同家規、章尾附錄 R 對映表在第 14 章之後、7 個資料列、無錨點語法（上位：AC-R2P-07-2 的雙重預檢骨架）。

```powershell
# AT-970-6-3
$se       = Read-Utf8 (Join-Path $vd 'docs_template/sdd/requirements/PRD-SPEC-ENGINEERED-TEMPLATE.md')
$homeTmpl = Read-Utf8 (Join-Path $vd 'docs_template/core/prd/PRD_Universal_Template.md')
function Test-SePrdStructure([string]$T, [string]$HomeText) {
    $p = @()
    if ([regex]::Matches($T, '<!-- r2p:template-guide:begin -->').Count -ne 1) { $p += '導讀 begin 標記不是恰 1 個' }
    if ([regex]::Matches($T, '<!-- r2p:template-guide:end -->').Count -ne 1) { $p += '導讀 end 標記不是恰 1 個' }
    $iEnd = $T.IndexOf('<!-- r2p:template-guide:end -->', [StringComparison]::Ordinal)
    $body = if ($iEnd -ge 0) { $T.Substring($iEnd) } else { $T }
    $nums = @([regex]::Matches($body, '<!--\s*r2p:section=(\d)\s*-->') | ForEach-Object { [int]$_.Groups[1].Value } | Sort-Object)
    if (($nums -join ',') -ne '1,2,3,4,5,6') { $p += ('六節錨點不是各恰 1 個：' + ($nums -join ',')) }
    foreach ($m in [regex]::Matches($body, '<!--\s*r2p:section=\d\s*-->\s*(\S[^\n]*)')) {
        if ($m.Groups[1].Value -notmatch '^#{1,6} ') { $p += ('錨點之後第一個非空行不是標題：' + $m.Groups[1].Value) }
    }
    $rx = '(?m)^## (\S+) (\d+)\. (.+?)\s*$'
    $h1 = @([regex]::Matches($HomeText, $rx) | ForEach-Object { $_.Value.TrimEnd() })
    $h2 = @([regex]::Matches($body, $rx) | ForEach-Object { $_.Value.TrimEnd() })
    if ($h1.Count -ne 14 -or (($h1 -join "`n") -ne ($h2 -join "`n"))) { $p += '14 章標題與家規 PRD_Universal_Template 不逐字一致' }
    $hm = [regex]::Match($body, '(?ms)^## [^\n]*附錄 R：來源六節 ↔ 家規章節對映表[^\n]*\n(.*?)(?=^## )')
    if (-not $hm.Success) { $p += '缺章尾附錄 R 對映表' }
    else {
        if ($hm.Groups[1].Value -match 'r2p:section') { $p += '附錄 R 內不得出現錨點語法' }
        $rows = [regex]::Matches($hm.Groups[1].Value, '(?m)^\| (?:[1-6] |（來源六節未列)').Count
        if ($rows -ne 7) { $p += "附錄 R 資料列應為 7，實為 $rows" }
        $i14 = $body.IndexOf('文檔追蹤鏈 (Traceability)', [StringComparison]::Ordinal)
        if ($i14 -lt 0 -or $body.IndexOf($hm.Value, [StringComparison]::Ordinal) -lt $i14) { $p += '附錄 R 不在第 14 章之後（章尾）' }
    }
    return $p
}
$pr = @(Test-SePrdStructure $se $homeTmpl)
$pr
Show-Result 'AT-970-6-3' ($pr.Count -eq 0) ('problems=' + $pr.Count)
```

預期輸出：`RESULT AT-970-6-3 PASS problems=0`。

**AT-970-6-4**（Unit）Given 九個新增檔 When 掃占位字樣與雙大括號佔位 Then 九檔皆無占位字樣；除 SE-PRD 模板（它本來就是帶佔位的模板）外，其餘八檔無雙大括號佔位（判準是「同一行內成對的雙大括號」，所以 JSON 範例裡巢狀物件連著收尾的兩個右大括號不算；占位字樣以字串相接組出，避免本檔自己命中）。

```powershell
# AT-970-6-4
$pats = @(('T' + 'BD'), ('TO' + 'DO'), ('FIX' + 'ME'), ('待' + '補'), ('之後' + '再看'))
$hits = @(foreach ($rel in $new9) {
    $t = Read-Utf8 (Join-Path $vd $rel)
    foreach ($pt in $pats) { $c = [regex]::Matches($t, [regex]::Escape($pt)).Count; if ($c -gt 0) { $rel + ' : ' + $pt + ' x' + $c } }
})
$ph = @(foreach ($rel in ($new9 | Where-Object { $_ -ne 'docs_template/sdd/requirements/PRD-SPEC-ENGINEERED-TEMPLATE.md' })) {
    $t = Read-Utf8 (Join-Path $vd $rel)
    $c = [regex]::Matches($t, '\{\{[^{}\n]*\}\}').Count
    if ($c -gt 0) { $rel + ' : 範本佔位 x' + $c }
})
$hits
$ph
Show-Result 'AT-970-6-4' ($hits.Count -eq 0 -and $ph.Count -eq 0) ('placeholder-words=' + $hits.Count + ' brace-placeholders=' + $ph.Count)
```

預期輸出：`RESULT AT-970-6-4 PASS placeholder-words=0 brace-placeholders=0`。

**AT-970-6-5**（Unit）Given 九個新增檔與十二個被改檔 When 掃舊名殘留並核對上位編號 Then 舊名 ADR 與已取消的框架側 PRD 零殘留；ADR、工作流、本檔引用的每個 `FR-R2P-NN`、`NFR-R2P-NN`、`US-R2P-NN`、`AC-R2P-NN-Y` 都存在於根層 PRD；本檔至少引用八個 FR（AC-R2P 至少十個）。

```powershell
# AT-970-6-5
if (-not $prdPath) { $prdPath = Join-Path $root 'docs/01_requirements/ResearchToPRD_PRD.md' }
$old1 = 'method' + '-layer'
$old2 = 'PRD-ResearchTo' + 'PRD-Framework'
$stale = @(foreach ($rel in ($new9 + $edited12)) {
    $t = Read-Utf8 (Join-Path $vd $rel)
    if ($t.Contains($old1) -or $t.Contains($old2)) { $rel }
})
$prd = Read-Utf8 $prdPath
$tcsText = Read-Utf8 (Join-Path $vd 'docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md')
$cited = @([regex]::Matches(($adr + $wf + $tcsText), '(?:FR|NFR|US)-R2P-\d{2}|AC-R2P-\d{2}-\d+') | ForEach-Object { $_.Value } | Sort-Object -Unique)
$absent = @($cited | Where-Object { -not $prd.Contains($_) })
$frN = @($cited | Where-Object { $_ -like 'FR-R2P-*' }).Count
$acN = @($cited | Where-Object { $_ -like 'AC-R2P-*' }).Count
'stale old names: ' + $stale.Count
'cited ids: ' + $cited.Count + ' (FR ' + $frN + ', AC ' + $acN + '); absent in PRD: ' + $absent.Count
$absent
Show-Result 'AT-970-6-5' ($stale.Count -eq 0 -and $absent.Count -eq 0 -and $frN -ge 8 -and $acN -ge 10)
```

預期輸出：`stale old names: 0`、`cited ids: <N> (FR <≥8>, AC <≥10>); absent in PRD: 0`（對 repo 現檔與根層 PRD 實跑：`cited ids: 44 (FR 11, AC 27); absent in PRD: 0`；PRD 與引用會隨修訂而變，判準是 `absent in PRD: 0`）、`RESULT AT-970-6-5 PASS`。（`$adr`、`$wf` 沿用 AT-970-6-1。）

**AT-970-6-6**（Unit）Given 審查卡模板的 `review_params`、工作流、ADR-001、BRIDGE §9.2、證據矩陣模板與引擎常數 `RETRY_LIMITS` When 對散文條文逐項對拍 Then 九項皆成立：(1) 審查卡 §2.2 與工作流 §6.3 的 `W100` 公式係數＝`review_params.weights` 各乘 100；(2) 兩處的 `W100 ≥ N`／`-ge N` 之 N＝100×`review_params.threshold`（8500）；(3) 工作流與審查卡裡所有「第 N 次…ESCALATION」的復述（工作流 §2.3、§2.6 表列、第 7 章、第 14 章步驟 6，審查卡 §2.3、§5.1 末句），逐處抽出的 N＝引擎 `RETRY_LIMITS["SCG_VALIDATION"]`；(4) ADR-001 的 D7 行含「審查預算採 FSM 預算」；(5) 工作流兩處權重百分比表列（§2 角色表、§6.2 維度表）＝`review_params.weights`；(6) BRIDGE §9.2 `transition` 列含「外環鍵只准前五值」，且該列 `--to` 集合的前五值恰為 `SCENARIO_DETECT`、`AGENT_LOAD`、`SPEC_DRAFTING`、`SCG_VALIDATION`、`SPEC_REGRESSION_CHECK`；(7) 工作流第 8 章含「產品內的 Gate 0 永遠要求真人核准」；(8) 證據矩陣模板含「`V0`（只憑記憶）**不得列入**」；(9) 工作流、審查卡與 ADR-001 裡所有「最多 N 輪」復述（工作流 §1 流程圖、§2.3 標題、§2.3 結論句、§6.3 末段，審查卡 §2.3，ADR-001 預算語意列，共六處；§2.3 的來源規格對照句「＝最多 4 輪」以前置「＝」排除）逐處抽出的 N＝引擎 `RETRY_LIMITS["SCG_VALIDATION"]`（SCG-4 二審 N-1，勘誤 10）（上位：PRD §5.1.3、§5.1.4；AC-R2P-08-1、AC-R2P-10-1；D-14、D-42）。這些是 JSON 契約檢核器（AT-970-3-x）管不到的散文復述——判定公式只住審查卡模板 §2.2（D-42），復述處漂移就與 PRD 脫鉤（SCG-4 一審 F-04）。

```powershell
# AT-970-6-6
$wf   = Read-Utf8 (Join-Path $vd 'workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md')
$adr  = Read-Utf8 (Join-Path $vd 'docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md')
$brg  = Read-Utf8 (Join-Path $vd 'workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md')
$card = Read-Utf8 (Join-Path $vd 'docs_template/sdd/requirements/ADVERSARIAL-REVIEW-CARD-TEMPLATE.md')
$evid = Read-Utf8 (Join-Path $vd 'docs_template/sdd/requirements/EVIDENCE-MATRIX-TEMPLATE.md')
$trl  = Read-Utf8 (Join-Path $vd 'tools/fsm_runtime/transition_rules.py')
$f3   = '`' * 3                                              # 三個反引號：不直接寫進本區塊（會截斷 Markdown 圍欄）
$rp   = [regex]::Match($card, ('(?s)<!-- r2p:contract=review_params -->\s*' + $f3 + 'json\s*(.*?)\s*' + $f3)).Groups[1].Value | ConvertFrom-Json
$pct  = [ordered]@{}                                         # 權重百分比（整數）＝review_params.weights 各乘 100
foreach ($d in 'ARCHITECTURE', 'PRODUCT', 'QA', 'SECURITY') { $pct[$d] = [int][Math]::Round($rp.weights.$d * 100) }
$thr100 = [int]$rp.threshold * 100
$limit  = [regex]::Match($trl, '"SCG_VALIDATION":\s*(\d+)').Groups[1].Value
$fx     = "$($pct['ARCHITECTURE'])·A \+ $($pct['PRODUCT'])·P \+ $($pct['QA'])·Q \+ $($pct['SECURITY'])·S"
$badN   = @(foreach ($t in @($card, $wf)) { foreach ($m in [regex]::Matches($t, '(?:W100 ≥ |-ge )(\d{4})\b')) { if ([int]$m.Groups[1].Value -ne $thr100) { $m.Value } } })
$nEsc   = @(foreach ($t in @($wf, $card)) { foreach ($m in [regex]::Matches($t, '第 (\d+) 次[^。；\n]{0,24}?ESCALATION')) { $m.Groups[1].Value } })
$nMax   = @(foreach ($t in @($wf, $card, $adr)) { foreach ($m in [regex]::Matches($t, '(?<!＝)最多 (\d+) 輪')) { $m.Groups[1].Value } })   # 六處：工作流 §1 圖、§2.3 標題、§2.3 結論句、§6.3 末段，卡 §2.3，ADR-001 預算語意列；§2.3 對照句「＝最多 4 輪」以前置「＝」排除（SCG-4 二審 N-1）
$want   = @(foreach ($d in $pct.Keys) { $d + '=' + $pct[$d] }) | Sort-Object
$pA     = @([regex]::Matches($wf, '（(ARCHITECTURE|PRODUCT|QA|SECURITY)，(?:權重 )?(\d+)%）') | ForEach-Object { $_.Groups[1].Value + '=' + $_.Groups[2].Value }) | Sort-Object
$pB     = @([regex]::Matches($wf, '(?m)^\| (ARCHITECTURE|PRODUCT|QA|SECURITY) \| (\d+)% \|') | ForEach-Object { $_.Groups[1].Value + '=' + $_.Groups[2].Value }) | Sort-Object
$d7     = [regex]::Match($adr, '(?m)^\*\*D7\u3000.*$').Value
$to     = [regex]::Match($brg, '`--to` 限 \{([^}]+)\}；外環鍵只准前五值')
$first5 = if ($to.Success) { (@($to.Groups[1].Value -split ',\s*') | Select-Object -First 5) -join ',' } else { '' }
$ck = [ordered]@{
    '卡 2.2 與工作流 6.3 的 W100 公式係數＝review_params.weights×100'          = ($null -ne $rp -and [regex]::IsMatch($card, ('W100\s*=\s*' + $fx)) -and [regex]::IsMatch($wf, ('W100\s*=\s*' + $fx)))
    '卡與工作流的 W100 門檻 N＝100×review_params.threshold'                    = ($badN.Count -eq 0 -and [regex]::IsMatch($card, 'W100 ≥ \d{4}') -and [regex]::IsMatch($wf, 'W100 ≥ \d{4}'))
    '工作流與卡所有「第 N 次…ESCALATION」復述的 N＝引擎 RETRY_LIMITS[SCG_VALIDATION]' = ($limit -ne '' -and $nEsc.Count -ge 2 -and @($nEsc | Where-Object { $_ -ne $limit }).Count -eq 0 -and $wf.Contains('第 ' + $limit + ' 次 FAIL 就是 ESCALATION') -and $card.Contains('第 ' + $limit + ' 次 `gate FAIL` 即 ESCALATION'))
    'ADR-001 D7 行含「審查預算採 FSM 預算」'                                     = ($d7.Contains('評分卡是 SCG-0 的評估器') -and $d7.Contains('審查預算採 FSM 預算'))
    '工作流兩處權重百分比表列＝review_params.weights'                           = ($want.Count -eq 4 -and ($pA -join ',') -eq ($want -join ',') -and ($pB -join ',') -eq ($want -join ','))
    'BRIDGE 9.2 外環鍵只准前五值，且前五值為外環集合'                            = ($first5 -eq 'SCENARIO_DETECT,AGENT_LOAD,SPEC_DRAFTING,SCG_VALIDATION,SPEC_REGRESSION_CHECK')
    '工作流第 8 章：產品內的 Gate 0 永遠要求真人核准'                            = $wf.Contains('產品內的 Gate 0 永遠要求真人核准')
    '證據矩陣模板：V0（只憑記憶）不得列入'                                       = $evid.Contains('`V0`（只憑記憶）**不得列入**')
    '工作流／卡／ADR-001 所有「最多 N 輪」復述的 N＝引擎 RETRY_LIMITS[SCG_VALIDATION]（六處）' = ($limit -ne '' -and $nMax.Count -ge 6 -and @($nMax | Where-Object { $_ -ne $limit }).Count -eq 0)
}
$ck.GetEnumerator() | ForEach-Object { '{0} {1}' -f $(if ($_.Value) { 'PASS' } else { 'FAIL' }), $_.Key }
Show-Result 'AT-970-6-6' (@($ck.Values | Where-Object { -not $_ }).Count -eq 0)
```

預期輸出：九行 `PASS …`、`RESULT AT-970-6-6 PASS`。

**AT-970-6-E-1**（Unit，負控）Given AT-970-6-3 的結構函式 When 餵入四種變異的 SE-PRD（重複錨點、附錄 R 改名、第 1 章標題被改寫、附錄 R 內混入錨點） Then 每種變異都回報至少一個問題（證明 AT-970-6-3 的 0 問題不是函式失明）。

```powershell
# AT-970-6-E-1
$mut = [ordered]@{
    '重複的第 3 節錨點'  = $se.Replace('<!-- r2p:section=3 -->', ('<!-- r2p:section=3 -->' + "`n" + '<!-- r2p:section=3 -->'))
    '章尾附錄 R 被改名'  = $se.Replace('附錄 R：來源六節 ↔ 家規章節對映表', '附錄 Z')
    '第 1 章標題被改寫'  = $se.Replace('專案願景與目標 (Vision & Objectives)', '專案願景')
    '附錄 R 內混入錨點'  = $se.Replace('| 6 非功能性需求 | 6 |', '| 6 非功能性需求 <!-- r2p:section=6 --> | 6 |')
}
$rows = foreach ($k in $mut.Keys) { [pscustomobject]@{ Case = $k; Mutated = ($mut[$k] -ne $se); Problems = @(Test-SePrdStructure $mut[$k] $homeTmpl).Count } }
$rows | ForEach-Object { '{0}: mutated={1} problems={2}' -f $_.Case, $_.Mutated, $_.Problems }
Show-Result 'AT-970-6-E-1' (@($rows | Where-Object { -not ($_.Mutated -and $_.Problems -ge 1) }).Count -eq 0)
```

預期輸出：四行 `<變異>: mutated=True problems=<≥1>`（對 repo 現檔實跑依序為 2、1、1、3）、`RESULT AT-970-6-E-1 PASS`。

### 2.7 AC-970-7：FSM 演練（暫存狀態目錄）

> **預期值與實跑**：標 🔶 的 AT 的預期值原依讀碼推得，座標：`tools/fsm_runtime/fsm_runtime.py`（`record_gate_result` :526-645、`_cli`／`_cli_structured` :3603-3740、`_is_blocked_spec_write` :339-352）、`state_loader.py`（`record_spec_frozen` :290-308、`record_spec_refreeze` :317-352）、`transition_rules.py`（`_HAPPY_PATH`〔HUMAN_PENDING 的出邊在 :28〕、`assert_transition` :300-302、`RETRY_LIMITS` :267-275、`next_state_on_gate_fail` :318-337）；D-50 兩個負控另依 `fsm_runtime.py:535-544`（`gate PASS` 路徑，沒有 try／except）與 `state_loader.py:271-274`（`reset_retry` 只改記憶體）；D-60 的恢復後預算（AT-970-7-6）另依 `fsm_runtime.py:1194-1218`（`resume_from_escalation` 不動重試計數）與 `state_loader.py:237-248`（`increment_retry` 見計數已達上限時夾在上限並標 tamper）。SCG-4 一審（2026-11-02）已於 repo 實跑八個 🔶 AT，全數 PASS，唯 AT-970-7-1 預期輸出的鍵排序敘述有誤（勘誤 5）。**之後再跑與預期不符時，先查預期值是否讀錯（走勘誤），再查實作。**
>
> 演練只寫 `$tmp` 之下：暫存狀態目錄（`SDD_STATE_DIR`）與 **AISDLC_SDD 的最小複本**（`$fsmVd`＝`$tmp/AISDLC_SDD/<版本目錄>`；runtime 以模組檔位置推得 `REPO_ROOT` 與共用腳本 `../scripts/component_sanitizer.py`，所以 `scripts/` 一併複製並保持相對位置）。FSM runtime 的報告目錄（例：`snapshot.py` 的 `SNAPSHOT_DIR`＝`build/reports/abort/`）由模組檔位置推得、不隨 `SDD_STATE_DIR`，而 `ABORT-RAW-<日期>.yaml` 是讀改寫的累加檔——直接從 repo 跑，自動恢復被拒時會在 repo 留下報告、且同日已有真實事件時無法精準清除（SCG-4 一審 F-03），所以演練的 CLI 一律從複本跑，repo 的 `build/reports/` 零寫入。兩個遙測旗標顯式 0（BRIDGE §8.3 第 5 點）；每次都帶 `--project` 顯式鍵。**會暫時改動目前視窗的 `SDD_STATE_DIR` 等環境變數**，AT-970-7-0 先存、AT-970-7-Z 還原——若是在 hooks-ON 的本鍵視窗跑，務必做到 AT-970-7-Z，否則後續指令會指到暫存目錄。

**AT-970-7-5**（Unit）Given `fsm_runtime._is_blocked_spec_write`（Rule 9.6 絕對禁令 3 的純函式；唯讀、不寫任何狀態） When 餵入研究工作區路徑與規格目錄路徑 Then 研究工作區路徑（`00_research`、`01_specs`、`02_governance`、`03_execution` 目錄名不含 `docs/01～03` 子字串）在任何狀態都不被擋；規格目錄在非草擬態被擋、草擬態放行（上位：PRD §9.0 D-28 的工作區位置推論；工作流第 10.1 節）。

```powershell
# AT-970-7-5
$code = @'
import sys
sys.path.insert(0, sys.argv[1])
from tools.fsm_runtime.fsm_runtime import _is_blocked_spec_write as blocked
ws = 'C:/Users/u/.autosdd/my-project/demo/'
cases = [
    ('研究工作區 PRD 草稿 @HUMAN_PENDING', blocked('HUMAN_PENDING', 'Write', ws + '01_specs/PRD_draft.md'), False),
    ('研究工作區 PRD 草稿 @SPEC_FROZEN', blocked('SPEC_FROZEN', 'Edit', ws + '01_specs/PRD_draft.md'), False),
    ('研究工作區 證據項 @SPEC_FROZEN', blocked('SPEC_FROZEN', 'Write', ws + '00_research/evidence_items.json'), False),
    ('研究工作區 審查輸出 @IMPLEMENTATION', blocked('IMPLEMENTATION', 'Write', ws + '02_governance/reviews/round-1/qa.json'), False),
    ('對照：規格目錄 @SPEC_FROZEN', blocked('SPEC_FROZEN', 'Write', 'docs/01_requirements/x.md'), True),
    ('對照：規格目錄 @SPEC_DRAFTING', blocked('SPEC_DRAFTING', 'Write', 'docs/01_requirements/x.md'), False),
]
for name, got, want in cases:
    print(('PASS ' if got == want else 'FAIL ') + name + ' -> blocked=' + str(got))
sys.exit(0 if all(g == w for _, g, w in cases) else 1)
'@
$script = Join-Path $tmp 'at970_7_5.py'
Write-Utf8 $script $code
$o = & $py -B -I -X utf8 $script $vd
$rc = $LASTEXITCODE
$o
Show-Result 'AT-970-7-5' ($rc -eq 0) "rc=$rc"
```

預期輸出：六行 `PASS …`（前四行 `blocked=False`、第五行 `blocked=True`、第六行 `blocked=False`）、`RESULT AT-970-7-5 PASS rc=0`。

**AT-970-7-0（共用，🔶 各 AT 之前先貼）**

```powershell
# AT-970-7-0 共用（FSM 暫存狀態目錄與版本目錄複本）
$saved = @{}
foreach ($n in 'SDD_STATE_DIR', 'SDD_ENABLE_AUTO_RECOVERY', 'SDD_ENABLE_RULE_FIRE_TELEMETRY', 'SDD_ENABLE_RULE_CATCH_TELEMETRY') { $saved[$n] = [Environment]::GetEnvironmentVariable($n) }
$fsmDir = Join-Path $tmp 'fsm'
New-Item -ItemType Directory -Force -Path $fsmDir | Out-Null
$fsmSdd = Join-Path $tmp 'AISDLC_SDD'                          # AISDLC_SDD 的最小複本：runtime 以模組檔位置推得 REPO_ROOT（版本目錄）與共用腳本 ../scripts/component_sanitizer.py，兩者必須保持相對位置
New-Item -ItemType Directory -Force -Path $fsmSdd | Out-Null
$fsmVd = Join-Path $fsmSdd $ver                                # FSM 的報告目錄（build/reports/abort/ 等）不隨 SDD_STATE_DIR；演練一律從複本跑，repo 零寫入（SCG-4 一審 F-03）
Copy-Item -LiteralPath $vd -Destination $fsmVd -Recurse
Copy-Item -LiteralPath (Join-Path $sdd 'scripts') -Destination (Join-Path $fsmSdd 'scripts') -Recurse
$env:SDD_STATE_DIR = $fsmDir
$env:SDD_ENABLE_RULE_FIRE_TELEMETRY = '0'; $env:SDD_ENABLE_RULE_CATCH_TELEMETRY = '0'
function Invoke-Sdd([string[]]$A) {
    Push-Location $fsmVd -ErrorAction Stop
    try { $out = & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime @A; $rc = $LASTEXITCODE } finally { Pop-Location }
    [pscustomobject]@{ Out = $out; Rc = $rc }
}
function Get-Json($R) { ($R.Out -join "`n") | ConvertFrom-Json }
function New-GateArgs([string]$Key, [string]$Gate, [string]$Result, [string]$Reason) { @('gate', '--project', $Key, '--must-exist', '--gate', $Gate, '--result', $Result, '--reason', $Reason) }
function Move-ToScgValidation([string]$Key) {
    $null = Invoke-Sdd @('show', '--project', $Key)                       # 建檔：整個週期唯一不帶 --must-exist 的一次
    foreach ($to in 'SCENARIO_DETECT', 'AGENT_LOAD', 'SPEC_DRAFTING', 'SCG_VALIDATION') {
        $r = Invoke-Sdd @('transition', '--project', $Key, '--must-exist', '--to', $to, '--reason', 'AT-970 drill')
        if ($r.Rc -ne 0) { throw "transition to $to failed rc=$($r.Rc)" }
    }
}
function New-DrillWorkspace([string]$Name) {
    $ws = Join-Path $tmp $Name
    foreach ($d in '01_specs/PRD-v1.0.0.md', '00_research/evidence_matrix.md', '00_research/issue_scope.json', '01_specs/adr_draft.md') {
        $f = Join-Path $ws $d
        New-Item -ItemType Directory -Force -Path (Split-Path $f) | Out-Null
        Write-Utf8 $f ("drill " + $d + "`n")
    }
    $ws
}
$gate0Docs = '01_specs/PRD-v1.0.0.md', '00_research/evidence_matrix.md', '00_research/issue_scope.json', '01_specs/adr_draft.md'
"state dir = $fsmDir"
"version dir copy = $fsmVd"
```

預期輸出：`state dir = <暫存目錄>/fsm`、`version dir copy = <暫存目錄>/AISDLC_SDD/AISDLC_SDD_v<LATEST>`，無錯誤。

**AT-970-7-1**（Integration，🔶）Given 外環鍵走到 SCG_VALIDATION When `gate PASS`、再以四份文件跑 `spec-frozen --stage Gate-0 --digest` Then `gate` 回傳 `next_state=HUMAN_PENDING`；`spec-frozen` rc 0、`current_state=SPEC_FROZEN`、`stage=Gate-0`、`spec_doc_digests` 的鍵恰為那四份（無 TCS）（上位：AC-R2P-10-1）。

```powershell
# AT-970-7-1
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
$k  = 'research-at970a'
$ws = New-DrillWorkspace 'ws-a'
Move-ToScgValidation $k
$g = Get-Json (Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'PASS' 'round 1 score=88.30; open P1=0'))
$docArgs = @($gate0Docs | ForEach-Object { '--doc'; $_ })
$z  = Invoke-Sdd (@('spec-frozen', '--project', $k, '--must-exist', '--stage', 'Gate-0') + $docArgs + @('--digest', '--root', $ws, '--reason', 'AT-970 drill: human approval', '--approver', 'at970-human', '--json'))
$zj = Get-Json $z
$keys = (@($zj.spec_doc_digests.PSObject.Properties.Name | Sort-Object) -join ',')
'gate PASS -> next_state=' + $g.next_state
'spec-frozen rc=' + $z.Rc + ' current_state=' + $zj.current_state + ' stage=' + $zj.stage
'digest keys: ' + $keys
Show-Result 'AT-970-7-1' ($g.next_state -eq 'HUMAN_PENDING' -and $z.Rc -eq 0 -and $zj.ok -eq $true -and $zj.current_state -eq 'SPEC_FROZEN' -and $zj.stage -eq 'Gate-0' -and $keys -eq ((@($gate0Docs | Sort-Object)) -join ','))
```

預期輸出：`gate PASS -> next_state=HUMAN_PENDING`、`spec-frozen rc=0 current_state=SPEC_FROZEN stage=Gate-0`、`digest keys: 00_research/evidence_matrix.md,00_research/issue_scope.json,01_specs/adr_draft.md,01_specs/PRD-v1.0.0.md`（`Sort-Object` 不分大小寫，`adr_draft` 排在 `PRD-v1.0.0` 之前；勘誤 5）、`RESULT AT-970-7-1 PASS`。

**AT-970-7-2**（Integration，🔶）Given 外環鍵環境 `SDD_ENABLE_AUTO_RECOVERY=0` When 連續 3 次 `gate SCG_VALIDATION FAIL`（每輪之間 `transition → SCG_VALIDATION`） Then 第 1、2 次 `next_state=SPEC_DRAFTING`；第 3 次 `retry_count=3`、`next_state=ESCALATION`、`escalated=True`、回傳**沒有** `auto_recovery`；磁碟狀態為 ESCALATION——即「最多 3 輪審查，第 3 次 FAIL 即 ESCALATION」（上位：AC-R2P-08-3、AC-R2P-08-10；D-24、D-26）。

```powershell
# AT-970-7-2
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
$k = 'research-at970b'
Move-ToScgValidation $k
$lines = @()
foreach ($i in 1, 2, 3) {
    $last = Get-Json (Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' "round $i score=70"))
    $lines += ('round {0}: retry_count={1} next_state={2} escalated={3} auto_recovery_key={4}' -f $i, $last.retry_count, $last.next_state, [bool]$last.escalated, ($last.PSObject.Properties.Name -contains 'auto_recovery'))
    if ($i -lt 3) { $null = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SCG_VALIDATION', '--reason', ('round ' + ($i + 1) + ' review start')) }
}
$disk = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state.current_state
$lines
'disk state after round 3: ' + $disk
Show-Result 'AT-970-7-2' (($lines[0] -match 'retry_count=1 next_state=SPEC_DRAFTING escalated=False') -and ($lines[1] -match 'retry_count=2 next_state=SPEC_DRAFTING escalated=False') -and ($lines[2] -match 'retry_count=3 next_state=ESCALATION escalated=True auto_recovery_key=False') -and $disk -eq 'ESCALATION')
```

預期輸出：`round 1: retry_count=1 next_state=SPEC_DRAFTING escalated=False auto_recovery_key=False`、`round 2: retry_count=2 next_state=SPEC_DRAFTING escalated=False auto_recovery_key=False`、`round 3: retry_count=3 next_state=ESCALATION escalated=True auto_recovery_key=False`、`disk state after round 3: ESCALATION`、`RESULT AT-970-7-2 PASS`。

**AT-970-7-E-1**（Integration，負控，🔶）Given 同一序列但**未設** `SDD_ENABLE_AUTO_RECOVERY`（預設開啟） When 第 3 次 FAIL Then 回傳**含** `auto_recovery`（耗盡的 SCG_VALIDATION 會先嘗試自動恢復）——證明 AT-970-7-2 的「無 `auto_recovery`」確實來自環境旗標而不是巧合（外環鍵環境被洩漏或覆寫的症狀＝ADR-XPLAT-017 §D4 的再開症狀）。

```powershell
# AT-970-7-E-1
Remove-Item Env:SDD_ENABLE_AUTO_RECOVERY -ErrorAction SilentlyContinue
$k = 'research-at970c'
Move-ToScgValidation $k
foreach ($i in 1, 2, 3) {
    $last = Get-Json (Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' "round $i score=70"))
    if ($i -lt 3) { $null = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SCG_VALIDATION', '--reason', ('round ' + ($i + 1) + ' review start')) }
}
$has = ($last.PSObject.Properties.Name -contains 'auto_recovery')
'round 3 (auto recovery default ON): retry_count=' + $last.retry_count + ' auto_recovery_key=' + $has + ' next_state=' + $last.next_state
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
Show-Result 'AT-970-7-E-1' ($has -and $last.retry_count -eq 3)
```

預期輸出：`round 3 (auto recovery default ON): retry_count=3 auto_recovery_key=True next_state=<AUTO_RECOVERY_ATTEMPT 或 ESCALATION_FINAL 或 ESCALATION>`、`RESULT AT-970-7-E-1 PASS`。

**AT-970-7-6**（Integration，🔶）Given 外環鍵（`SDD_ENABLE_AUTO_RECOVERY=0`）已用盡 3 次審查預算而在 ESCALATION When 人工 `resume-from-escalation --to SPEC_DRAFTING`、走回 SCG_VALIDATION 後再 `gate SCG_VALIDATION FAIL`；隨後第二次人工恢復、走回 SCG_VALIDATION 後 `gate SCG_VALIDATION PASS` Then 恢復 rc 0、回傳 `from=ESCALATION`、`to=SPEC_DRAFTING`，磁碟現態 SPEC_DRAFTING 且 `SCG_VALIDATION.current_count` 仍是 3（恢復不歸零）；恢復後的第一次 FAIL 回傳 `retry_count=3`（不是 1，也不是 4）、`next_state=ESCALATION`、`escalated=True`，歷史末列的 `failure_reason` 帶 `tamper detected: prior_count=3`；第二次恢復後的 `gate PASS` 回傳 `next_state=HUMAN_PENDING` 且計數歸 0——即「人工恢復後至多再得一次審查，FAIL 立即再 ESCALATION、PASS 歸零；全新預算＝換世代鍵」（上位：AC-R2P-08-3；主控 D-60；工作流第 2.5 節、審查卡模板第 2.3 節；讀碼座標：`fsm_runtime.py:1194-1218`〔恢復不動計數〕、`state_loader.py:237-248`〔`increment_retry` 見計數已達上限時夾在上限並標 tamper〕、`state_loader.py:271-274` 與 `fsm_runtime.py:536`〔`gate PASS` 才歸零〕）。每次恢復會在 stderr 印一行 `Reminder: remove SDD_HOOKS_DRY_RUN=1 …`，屬預期。

```powershell
# AT-970-7-6
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
$k = 'research-at970h'
Move-ToScgValidation $k
foreach ($i in 1, 2, 3) {                                    # 先用盡預算：第 3 次 FAIL 進 ESCALATION（同 AT-970-7-2）
    $null = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' "round $i score=70")
    if ($i -lt 3) { $null = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SCG_VALIDATION', '--reason', ('round ' + ($i + 1) + ' review start')) }
}
$esc  = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$r1   = Invoke-Sdd @('resume-from-escalation', '--project', $k, '--must-exist', '--to', 'SPEC_DRAFTING', '--reason', 'AT-970 drill: human resume 1')
$r1j  = Get-Json $r1
$s1   = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$null = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SCG_VALIDATION', '--reason', 'review start after human resume 1')
$f4   = Get-Json (Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' 'round 4 score=72'))
$s2   = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$note = @($s2.retry_history.SCG_VALIDATION.history)[-1].failure_reason
$r2   = Invoke-Sdd @('resume-from-escalation', '--project', $k, '--must-exist', '--to', 'SPEC_DRAFTING', '--reason', 'AT-970 drill: human resume 2')
$null = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SCG_VALIDATION', '--reason', 'review start after human resume 2')
$p    = Get-Json (Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'PASS' 'round 5 score=88.30; open P1=0'))
$s3   = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$c0 = $esc.retry_history.SCG_VALIDATION.current_count
$c1 = $s1.retry_history.SCG_VALIDATION.current_count
$c3 = $s3.retry_history.SCG_VALIDATION.current_count
$tamper = ($note -match 'tamper detected: prior_count=3')
'before resume: state=' + $esc.current_state + ' count=' + $c0
'resume 1: rc=' + $r1.Rc + ' from=' + $r1j.from + ' to=' + $r1j.to + '; after resume: state=' + $s1.current_state + ' count=' + $c1
'first FAIL after resume: retry_count=' + $f4.retry_count + ' next_state=' + $f4.next_state + ' escalated=' + [bool]$f4.escalated + ' tamper_note=' + $tamper
'resume 2: rc=' + $r2.Rc + '; gate PASS: next_state=' + $p.next_state + ' count after PASS=' + $c3
Show-Result 'AT-970-7-6' ($esc.current_state -eq 'ESCALATION' -and $c0 -eq 3 -and $r1.Rc -eq 0 -and $r1j.from -eq 'ESCALATION' -and $r1j.to -eq 'SPEC_DRAFTING' -and $s1.current_state -eq 'SPEC_DRAFTING' -and $c1 -eq 3 -and $f4.retry_count -eq 3 -and $f4.next_state -eq 'ESCALATION' -and [bool]$f4.escalated -and $s2.current_state -eq 'ESCALATION' -and $tamper -and $r2.Rc -eq 0 -and $p.next_state -eq 'HUMAN_PENDING' -and $c3 -eq 0)
```

預期輸出：`before resume: state=ESCALATION count=3`、`resume 1: rc=0 from=ESCALATION to=SPEC_DRAFTING; after resume: state=SPEC_DRAFTING count=3`、`first FAIL after resume: retry_count=3 next_state=ESCALATION escalated=True tamper_note=True`、`resume 2: rc=0; gate PASS: next_state=HUMAN_PENDING count after PASS=0`、`RESULT AT-970-7-6 PASS`。

**AT-970-7-3**（Integration，🔶）Given 外環鍵在 HUMAN_PENDING When 人工退回（`gate SCG_VALIDATION FAIL --reason "人工審查：…"`）、探測非法邊 `transition → SPEC_DRAFTING`、再走 `transition → SPEC_REGRESSION_CHECK` 與 `spec-frozen` Then 人工退回回傳 `retry_count=1`、`next_state=HUMAN_PENDING`（FSM 沒有 HUMAN_PENDING→SPEC_DRAFTING 的邊，被擋的轉態記 `gate_fail_blocked`）；非法邊 rc≠0 且狀態不變；`SPEC_REGRESSION_CHECK` 之後 `spec-frozen` rc 0 到 `SPEC_FROZEN`（上位：AC-R2P-08-9、AC-R2P-10-5、AC-R2P-10-8）。非法邊探測會在 stderr 印 `TransitionError` traceback，屬預期。

```powershell
# AT-970-7-3
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
$k  = 'research-at970d'
$ws = New-DrillWorkspace 'ws-d'
Move-ToScgValidation $k
$null = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'PASS' 'round 1 pass')
$r1    = Get-Json (Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' '人工審查：AC-003-2 的 Then 不可量測'))
$bad   = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SPEC_DRAFTING', '--reason', 'illegal edge probe')
$still = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state.current_state
$chk   = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SPEC_REGRESSION_CHECK', '--reason', 'Gate 0 regression check: 1/1')
$docArgs = @($gate0Docs | ForEach-Object { '--doc'; $_ })
$z  = Invoke-Sdd (@('spec-frozen', '--project', $k, '--must-exist', '--stage', 'Gate-0') + $docArgs + @('--digest', '--root', $ws, '--reason', 'AT-970 drill: approved after revision', '--approver', 'at970-human', '--json'))
$zj = Get-Json $z
'human retreat: retry_count=' + $r1.retry_count + ' next_state=' + $r1.next_state
'illegal edge: rc=' + $bad.Rc + ' state after=' + $still
'regression check rc=' + $chk.Rc + '; spec-frozen rc=' + $z.Rc + ' current_state=' + $zj.current_state
Show-Result 'AT-970-7-3' ($r1.retry_count -eq 1 -and $r1.next_state -eq 'HUMAN_PENDING' -and $bad.Rc -ne 0 -and $still -eq 'HUMAN_PENDING' -and $chk.Rc -eq 0 -and $z.Rc -eq 0 -and $zj.current_state -eq 'SPEC_FROZEN')
```

預期輸出：`human retreat: retry_count=1 next_state=HUMAN_PENDING`、`illegal edge: rc=1 state after=HUMAN_PENDING`、`regression check rc=0; spec-frozen rc=0 current_state=SPEC_FROZEN`、`RESULT AT-970-7-3 PASS`。

**AT-970-7-E-2**（Integration，負控，🔶）Given 外環鍵在 HUMAN_PENDING（計數 0） When 連續兩次人工退回 `gate SCG_VALIDATION FAIL --reason "人工審查：…"` Then 兩次皆 rc 0 且回傳 `next_state=HUMAN_PENDING`，`retry_count` 依序為 1、2；磁碟現態一直是 HUMAN_PENDING，`SCG_VALIDATION.current_count` 與回傳一致；`decision_trace` 末筆的 `trigger` 是 `gate_fail_blocked`（被擋的 HUMAN_PENDING → SPEC_DRAFTING 轉態有留痕）——即主控 D-50 的「人工退回＝態不動、計數加 1」，與 `SDD_SPEC_FIRST_GATE.md` 對照表第 5 列同一做法（上位：AC-R2P-08-9；讀碼座標：`fsm_runtime.py:546-547、621-641`）。

```powershell
# AT-970-7-E-2
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
$k = 'research-at970f'
Move-ToScgValidation $k
$null = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'PASS' 'round 1 pass')
$h1 = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' '人工審查：AC-003-2 的 Then 不可量測')
$s1 = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$h2 = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' '人工審查：第二次要求修改')
$s2 = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$j1 = Get-Json $h1
$j2 = Get-Json $h2
$trig = @($s2.decision_trace)[-1].trigger
'human FAIL #1: rc=' + $h1.Rc + ' retry_count=' + $j1.retry_count + ' next_state=' + $j1.next_state + ' disk=' + $s1.current_state + ' count=' + $s1.retry_history.SCG_VALIDATION.current_count
'human FAIL #2: rc=' + $h2.Rc + ' retry_count=' + $j2.retry_count + ' next_state=' + $j2.next_state + ' disk=' + $s2.current_state + ' count=' + $s2.retry_history.SCG_VALIDATION.current_count + ' last trace trigger=' + $trig
Show-Result 'AT-970-7-E-2' ($h1.Rc -eq 0 -and $h2.Rc -eq 0 -and $j1.retry_count -eq 1 -and $j1.next_state -eq 'HUMAN_PENDING' -and $s1.current_state -eq 'HUMAN_PENDING' -and $s1.retry_history.SCG_VALIDATION.current_count -eq 1 -and $j2.retry_count -eq 2 -and $j2.next_state -eq 'HUMAN_PENDING' -and $s2.current_state -eq 'HUMAN_PENDING' -and $s2.retry_history.SCG_VALIDATION.current_count -eq 2 -and $trig -eq 'gate_fail_blocked')
```

預期輸出：`human FAIL #1: rc=0 retry_count=1 next_state=HUMAN_PENDING disk=HUMAN_PENDING count=1`、`human FAIL #2: rc=0 retry_count=2 next_state=HUMAN_PENDING disk=HUMAN_PENDING count=2 last trace trigger=gate_fail_blocked`、`RESULT AT-970-7-E-2 PASS`。

**AT-970-7-E-3**（Integration，負控，🔶）Given 外環鍵在 HUMAN_PENDING 且人工退回過一次（計數 1） When 呼叫 Bridge 守則禁止的 `gate SCG_VALIDATION PASS` Then rc≠0（`record_gate_result` 的 PASS 路徑直接 `transition` 到 HUMAN_PENDING 且沒有 try／except，HUMAN_PENDING → HUMAN_PENDING 不是合法邊，`TransitionError` 的 traceback 印在 stderr，屬預期）；磁碟現態仍是 HUMAN_PENDING、`SCG_VALIDATION.current_count` 仍是 1（例外發生在存檔之前，`reset_retry` 只改了記憶體）——證明「現態 HUMAN_PENDING 時不呼叫 gate PASS；再審通過只記 DB」這條守則是必要的、不是潔癖（主控 D-50；讀碼座標：`fsm_runtime.py:535-544`、`transition_rules.py:28、300-302`、`state_loader.py:271-274`）。

```powershell
# AT-970-7-E-3
$env:SDD_ENABLE_AUTO_RECOVERY = '0'
$k = 'research-at970g'
Move-ToScgValidation $k
$null = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'PASS' 'round 1 pass')
$null = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'FAIL' '人工審查：要求修改')
$before = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
$bad    = Invoke-Sdd (New-GateArgs $k 'SCG_VALIDATION' 'PASS' 'round 2 pass while the human hold is open')
$after  = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state
'gate PASS under HUMAN_PENDING: rc=' + $bad.Rc
'state before/after: ' + $before.current_state + '/' + $after.current_state + '; count before/after: ' + $before.retry_history.SCG_VALIDATION.current_count + '/' + $after.retry_history.SCG_VALIDATION.current_count
Show-Result 'AT-970-7-E-3' ($bad.Rc -ne 0 -and $before.current_state -eq 'HUMAN_PENDING' -and $after.current_state -eq 'HUMAN_PENDING' -and $before.retry_history.SCG_VALIDATION.current_count -eq 1 -and $after.retry_history.SCG_VALIDATION.current_count -eq 1)
```

預期輸出：`gate PASS under HUMAN_PENDING: rc=1`（stderr 另有 `TransitionError: transition not allowed: HUMAN_PENDING -> HUMAN_PENDING` 的 traceback）、`state before/after: HUMAN_PENDING/HUMAN_PENDING; count before/after: 1/1`、`RESULT AT-970-7-E-3 PASS`。

**AT-970-7-4**（Integration，🔶）Given 內環鍵已做 Stage-1 基線採納並經談判進入 IMPLEMENTATION When 依工作流第 9.3 節與 ADR-XPLAT-017 附錄 A 走 SCR-minor 序列（`transition → SPEC_AUDIT`、`spec-refreeze`、`transition → PR_REVIEW`、`gate PR_REVIEW FAIL`） Then 每步 rc 0，`spec-refreeze` 回傳 `ok=true`，最後 `gate` 回傳 `next_state=IMPLEMENTATION`（上位：AC-R2P-19-8；證明不改 `_HAPPY_PATH` 也能由內環回到「重新實作」）。

```powershell
# AT-970-7-4
Remove-Item Env:SDD_ENABLE_AUTO_RECOVERY -ErrorAction SilentlyContinue
$k   = 'sdd-at970e'
$ws  = Join-Path $tmp 'ws-e'
$doc = 'docs/01_requirements/Demo_PRD.md'
New-Item -ItemType Directory -Force -Path (Join-Path $ws 'docs/01_requirements') | Out-Null
Write-Utf8 (Join-Path $ws $doc) "v1`n"
$null = Invoke-Sdd @('show', '--project', $k)
foreach ($to in 'SCENARIO_DETECT', 'AGENT_LOAD', 'SPEC_DRAFTING', 'SCG_VALIDATION', 'HUMAN_PENDING') {
    $r = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', $to, '--reason', 'baseline adoption；SCG 未重跑')
    if ($r.Rc -ne 0) { throw "adoption transition to $to failed rc=$($r.Rc)" }
}
$s1 = Invoke-Sdd @('spec-frozen', '--project', $k, '--must-exist', '--stage', 'Stage-1', '--doc', $doc, '--digest', '--root', $ws, '--reason', 'baseline adoption；AT-970 drill', '--approver', 'at970-human', '--json')
$ne = Invoke-Sdd @('negotiate-enter', '--project', $k, '--reason', 'AT-970 drill', '--contract-ref', 'docs/03_testing/contracts/TCS-Demo.md')
$nx = Invoke-Sdd @('negotiate-exit', '--project', $k, '--outcome', 'agreed', '--reason', 'AT-970 drill agreed')
$atImpl = (Get-Json (Invoke-Sdd @('show', '--project', $k, '--must-exist'))).fsm_state.current_state
Write-Utf8 (Join-Path $ws $doc) "v2 revised`n"
$a  = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'SPEC_AUDIT', '--reason', 'SCR-1 minor: AT-970 drill')
$rf = Invoke-Sdd @('spec-refreeze', '--project', $k, '--doc', $doc, '--root', $ws, '--reason', 'SCR-1: PRD v1 to v2', '--approver', 'at970-human')
$p  = Invoke-Sdd @('transition', '--project', $k, '--must-exist', '--to', 'PR_REVIEW', '--reason', 'SCR-1 spec refrozen')
$gf = Invoke-Sdd (New-GateArgs $k 'PR_REVIEW' 'FAIL' 'SCR-1: spec changed; re-implement')
$gj = Get-Json $gf
'stage-1 rc=' + $s1.Rc + '; negotiate rc=' + $ne.Rc + '/' + $nx.Rc + '; state before SCR=' + $atImpl
'SPEC_AUDIT rc=' + $a.Rc + '; spec-refreeze rc=' + $rf.Rc + '; PR_REVIEW rc=' + $p.Rc + '; gate FAIL next_state=' + $gj.next_state
Show-Result 'AT-970-7-4' ($s1.Rc -eq 0 -and $ne.Rc -eq 0 -and $nx.Rc -eq 0 -and $atImpl -eq 'IMPLEMENTATION' -and $a.Rc -eq 0 -and $rf.Rc -eq 0 -and $p.Rc -eq 0 -and $gj.next_state -eq 'IMPLEMENTATION')
```

預期輸出：`stage-1 rc=0; negotiate rc=0/0; state before SCR=IMPLEMENTATION`、`SPEC_AUDIT rc=0; spec-refreeze rc=0; PR_REVIEW rc=0; gate FAIL next_state=IMPLEMENTATION`、`RESULT AT-970-7-4 PASS`。

**AT-970-7-Z（收尾）**還原環境並刪暫存目錄（含版本目錄複本；跑過任何 🔶 AT 或 AT-970-0 後必做）：

```powershell
# AT-970-7-Z 收尾
foreach ($n in $saved.Keys) { [Environment]::SetEnvironmentVariable($n, $saved[$n]) }    # 原值為空時等於清除
Remove-Item -LiteralPath $tmp -Recurse -Force
'restored env; temp dir removed: ' + (-not (Test-Path -LiteralPath $tmp))
```

預期輸出：`restored env; temp dir removed: True`。

---

## 3. AT 完整清單

AT 的類型、描述與狀態只在 §1 映射表維護一份（單一真相源，避免兩處漂移）；各 AT 的指令與預期輸出在 §2。測試類型分佈：Unit 13、Integration 18、Contract 3、E2E 1（`AT-970-4-4`）。

---

## 4. 邊界與錯誤測試規格

> 負控與邊界 AT 採 `AT-970-<AC 序>-E-<序>` 命名（掛在所屬 AC 之下），並已列入 §1 映射表。每一個正控 AC 都至少配一個負控——證明綠燈不是檢查失明。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 殘留（改名、取消） | AT-970-1-E-1 | 舊名 ADR、已取消的框架側 PRD 不存在；工作流目錄只有一檔 | 落地後的版本目錄 | 0 個殘留 |
| 新鮮度失明 | AT-970-2-E-1 | 磁碟多一支 agent 而未重生，`--check` 必須紅 | 暫存迷你樹＋注入一支 agent | `stale rc=1` |
| 缺標記 | AT-970-3-E-1 | 移除 `review_params` 契約標記 | 暫存複本 | 檢核器 rc 1 並指名該標記 |
| 鬼影引用 | AT-970-4-E-1 | agent 引用不存在的模板 | 暫存版本樹 `v0.99` | lint rc 1＋`BROKEN`；改回真檔 rc 0 |
| 越界 | AT-970-5-E-1 | 邊界函式對合成越界路徑回報違規 | 合成路徑八組（含近似檔名 `….md.bak`） | 越界者被回報（含清單外的根層文件與 `scripts/` 檔、根層 `.claude/`），白名單、D-46 清單與 `06_quality` 不被回報 |
| 結構變異 | AT-970-6-E-1 | SE-PRD 四種變異（重複錨點、附錄改名、標題改寫、附錄混入錨點） | 變異後文字 | 每種 ≥1 個問題 |
| 環境旗標 | AT-970-7-E-1 | 自動恢復預設開啟時第 3 次 FAIL 的回傳含 `auto_recovery` | 同序列、未設旗標 | `auto_recovery_key=True` |
| 人工退回守則 | AT-970-7-E-2 | 現態 HUMAN_PENDING 時人工退回（`gate FAIL`）態不動、計數加 1、記 `gate_fail_blocked`（D-50） | 同一暫存鍵連續兩次人工 `gate FAIL` | 兩次皆 `next_state=HUMAN_PENDING`，計數 1 與 2 |
| 人工退回守則 | AT-970-7-E-3 | 現態 HUMAN_PENDING 時 `gate PASS` 被拒、態與計數不變（D-50） | 同一暫存鍵在計數為 1 時呼叫 `gate PASS` | rc≠0；現態與計數不變 |
| 恢復後預算邊界 | AT-970-7-6 | ESCALATION 人工恢復後預算不歸零：恢復後第一次 `gate FAIL` 立即再 ESCALATION、`gate PASS` 歸零（D-60；🔶） | 同一暫存鍵用盡 3 次預算後兩次人工 `resume-from-escalation` | 恢復後計數仍 3；第 4 次 FAIL `retry_count=3`、`next_state=ESCALATION`；PASS 後計數 0 |

---

## 5. 測試資料規格

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| 新增檔清單 `$new9`、被改檔清單 `$edited12` | 靜態清單 | 9＋12 個，路徑相對版本目錄；白名單另含 `AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD/scripts/framework_status_snapshot.py`、`AISDLC_SDD/FRAMEWORK_STATUS.md` 共 24 條；根層連動例外清單 `$rootExempt`（D-46，8 條）見 AT-970-5-1 | §2.0 前置、AT-970-5-1 |
| 契約區塊與有效範例 | 靜態 Fixture | 四份模板內 9 個 `<!-- r2p:contract=… -->` JSON 區塊（`issue_scope`、`evidence_items`、`axis_registry`、`risk_tag_registry`、`review_params`、`rubric_registry`、`review_dimension`、`review_dimension_qa`、`review_card`） | `docs_template/sdd/requirements/*-TEMPLATE.md` |
| 暫存迷你樹（新鮮度負控） | 動態生成 | 兩個版本目錄各一支 core agent 與一份 README | AT-970-2-E-1 |
| 暫存版本樹 `v0.99`（鬼影引用負控） | 動態生成 | 一份真模板、一支引用它（或引用不存在檔）的 agent | AT-970-4-E-1 |
| 契約模板暫存複本（缺標記負控） | 動態生成 | 複製 `docs_template/sdd/requirements/*-TEMPLATE.md` 後移除一個標記 | AT-970-3-E-1 |
| SE-PRD 變異文字 | 動態生成 | 對真模板做四種字串替換 | AT-970-6-E-1 |
| FSM 暫存狀態目錄與研究工作區 | 動態生成 | `$tmp/fsm`（`SDD_STATE_DIR`）、`$tmp/AISDLC_SDD`（版本目錄與 `scripts/` 的複本）、`$tmp/ws-a`／`ws-d`（Gate 0 四份文件）、`$tmp/ws-e`（內環 PRD 副本） | AT-970-7-0～7-4、7-6、7-E-1～7-E-3 |
| 上位檔摘要 | 靜態值＋現算 | 五個摘要見〈增量追溯表〉；重算指令見 AT-970-5-3 | repo 工作樹現檔（`digest_doc`）／`spec-refreeze` 重記 |
| 根層 PRD | 外部文件 | AT-970-6-5 讀 `docs/01_requirements/ResearchToPRD_PRD.md` 核對上位編號 | 根層（SD-A 交付；主控落檔） |
| 機密 | — | 本鍵不涉任何機密；演練的 approver 是固定字串 `at970-human` | — |

---

## 6. RTM 連結確認與 V 系列

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| EPIC-970 → F-970 | □ 已映射（FRD-lite 檔頭） |
| F-970 → US-970 | □ 已映射 |
| US-970 → AC-970-1～7 | □ 已映射（FRD-lite 表） |
| AC-970-1～7 → AT-970-… | □ 已映射（§1，本文件；35 個 AT） |
| AT → 本機 CI 閘門 | □ 已整合（AT-970-4-4 `ci-gate.ps1`） |
| AC → 上位 FR-R2P／AC-R2P | □ 已映射（〈上位需求對照〉；AT-970-6-5 機械核對編號存在） |

**RTM 與報告落點**：RTM 寫 `docs/06_quality/RTM-ResearchToPRD-Framework-20261102.md`（版本目錄的專案層文件；SCG_VALIDATION 起 `docs/03_testing/` 被 Rule 9.6 擋寫，所以報告與 RTM 一律放 `06_quality`，BRIDGE §8.5、D-116-09）；SCG-4 審查報告同目錄。RTM 每完成一項需求就回填四格（實作檔／自動測試／E2E 驗證／狀態），不刪列、不改號、不合併列。

**V 系列（真機或人工；自動測試之外）**

| 編號 | 驗證者 | 內容 | 判定 |
|------|--------|------|------|
| V1 | 主控或 QA | 在框架鍵的 hooks-ON 視窗做 BRIDGE §8.2 (a)(c) 的開場三步（同址、活性正負兩面），證明本鍵的三件組有效、規格寫入閘在 SPEC_DRAFTING 以外態確實擋 `docs/01～03` | 輸出逐字貼證據檔 |
| V2 | 人（掌舵者或指派者） | 依工作流第 13 章步驟 1～2 在 hooks-ON 視窗建一個玩具研究工作區（外環鍵 INIT → AGENT_LOAD），`Test-Path` 狀態檔為 True | 人手流程文件可照著跑通 |
| V3 | 人 | 以 SE-PRD 模板填一份玩具 PRD，逐條核對模板第 0.2 節 P0-1～P0-9（含雙重預檢兩項） | 模板可填、預檢條文無歧義 |
| V4 | Console 側（P0 實作期） | `AgentConsole/engine-bridge/tests/test_research_schema_parity.py` 以 `<!-- r2p:contract=… -->` 標記抽取本檔所屬四份模板的範例並對拍 Bridge 側 schema（`SDD_ROOT` 在才跑，否則標 TOOL-ABSENCE） | 框架側不阻擋、不替代；以 Console 側報告為準 |

**收尾（SPEC_AUDIT 或 RELEASE_READY 態）**：Stage-1 於框架側改動落入工作樹**之後**才採納，五份採納文件（`AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD_INIT.md`、`SDD_SPEC_FIRST_GATE.md`、根層 PRD、ADR-001；〈增量追溯表〉U1～U5）記的是改動後的摘要，所以本鍵自己的改動沒有待重記項；其後的再改（SCG-4 審查所致的 PRD 訂正、本檔勘誤）以 `spec-refreeze` 重記：一次 `--doc` 列出被改的文件（含本檔；`--root`＝monorepo 根、路徑為相對根的正斜線路徑，與 Stage-1 同形），`--approver` 填人（或依凍結常態規則由主控代執行並引審查報告座標），`--reason` 寫訂正內容；重記只追加條目、不洗掉任何重試預算，消費端取全部條目的聯集、同鍵後者勝出（`state_loader.py` 的 `record_spec_refreeze`）。其後 `FRAMEWORK_STATUS.md` 重生仍是最後一步。

---

## 7. ⚖ 預設值與已知邊界（交人在 Stage-2 HUMAN_PENDING 確認；SCG-4 審查者亦須獨立檢視）

1. **⚖1 增量條款的適用性**：**主控 D-48(1) 裁決：適用增量條款，以 `spec-refreeze` 重記摘要**（屬流程解釋，在凍結常態規則射程內由主控代決；掌舵者可隨時以 T1 推翻，推翻時改走完整 SCG-1～3 清單）。理由：改動限於註冊清單、條文增補與依磁碟現值更新的計數句，**只增不減**，不改既有條款的語意；〈閘門通過標準〉的「改動已凍結上位文件本身者不適用」字面上對本鍵有爭議，所以裁決附機械依據。**重現指令**（在 repo 內可跑；起點 `01d9be6e`、落檔 `25c66981`）：`git -c core.quotepath=false diff --numstat --diff-filter=M 01d9be6e 25c66981 -- AISDLC_SDD ':(exclude)AISDLC_SDD/FRAMEWORK_STATUS.md' ':(exclude)AISDLC_SDD/scripts'`（13 個被改檔；等價於逐一列出路徑：`$edited12` 各加 `AISDLC_SDD/<版本目錄>/` 前綴，再加 `AISDLC_SDD/CLAUDE.md`）；逐檔新增／移除行：`AISDLC_SDD_INIT.md` +24／−4、`workflow/README.md` +10／−2、`agent/README.md` +15／−2、`agent/specialized/README.md` +9／−1、`SDD_SPEC_FIRST_GATE.md` +6／−4、`SDD_AUTOCLAUDE_BRIDGE.md` +50／−1、greenfield +2／−0、brownfield +2／−0、`docs_template/README.md` +15／−5、`PROJECT_DOCUMENTATION_STANDARDS.md` +1／−1、`EVOLUTION_LOG.md` +15／−0、`CHANGELOG.md` +23／−1、`AISDLC_SDD/CLAUDE.md` +4／−1（合計 +176／−22；篩選與排除不可省——不加的 `-- AISDLC_SDD` 會連 9 個新增檔、`FRAMEWORK_STATUS.md` 與 `framework_status_snapshot.py` 一併計入，得 24 檔 +4632／−29；只加 `--diff-filter=M` 而不排除那兩檔，得 15 檔 +184／−29）；被移除的 22 行全是就地延伸的計數句、日期行、註記句，或表格列內多寫一個儲存格；`agent/README.md` 被取代的兩個計數句原文逐字保留於同檔的訂正引言（訂正協議；AT-970-2-1 驗）。**Stage-1 採納集合與重記**：真實的 Stage-1 於改動落入工作樹之後才採納，五份文件（`AISDLC_SDD/CLAUDE.md`、INIT、SPEC_FIRST_GATE、根層 PRD、ADR-001；〈增量追溯表〉U1～U5）記的是改動後摘要，所以本鍵自己的改動沒有待重記項；其後的再改（PRD 的 W0 訂正、本檔勘誤）才以 `spec-refreeze` 重記（`--doc` 列出被改的文件，`--root` 同 Stage-1）。`SDD_AUTOCLAUDE_BRIDGE.md` 不在 `sub=sdd` 的採納集合（BRIDGE §8.4），其改動同樣只增不減。反向症狀：SCG-0～3 審查發現增補改動了既有條文的語意 ⇒ 改走完整 SCG-1～3 清單（本鍵的 ADR-001 已能滿足 SCG-2 的 ADR 項，SRD、C4、OpenAPI 無對應物，需另行說明）。
2. **⚖2 機械半段空轉**：SLV 規則檔掃描路徑樣式、模糊度計分器以標題抽 AC，對本檔表格形 AC 不產生判斷（BRIDGE §8.5、G-116-15）；預設由 QA 逐條讀 AC 與追溯表補位，不得把「機械半段沒報錯」當成通過。
3. **⚖3 `agent.version` 欄**：兩支新 agent 的版本欄寫 `see FRAMEWORK_STATUS.md`（不寫死版號；`agent_scg_anchor_lint` AGT-05 要求），預設不另列版號。
4. **⚖4 白名單邊界**：預設＝24 條白名單路徑（9 個新增檔、版本目錄內 12 個被改檔、`AISDLC_SDD/CLAUDE.md`、主控補丁 `AISDLC_SDD/scripts/framework_status_snapshot.py`、重生的 `FRAMEWORK_STATUS.md`；主控 D-47 擴充）加版本目錄 `docs/06_quality/` 報告；`scripts/**` 其餘檔不在內（AT-970-5-1 比 ADR-XPLAT-017 §D7 的機械核對法更嚴：只放行 `framework_status_snapshot.py` 一檔）。**根層連動的已知例外（主控 D-46）**：主控收尾單窗的 W0 連動檔，逐字清單共 8 條＝`.gitignore`、`.github/workflows/agentconsole-ci.yml`、`docs/01_requirements/ResearchToPRD_PRD.md`、`docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`、`docs/01_requirements/Agent_ConsoleUI_PRD.md`、`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`、`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`、`AgentConsole/**`；`tools/`、`.claude/` 必須為空。`ResearchSOPtoPRD_Source_Spec.md` 在起點 commit 之後的 W0 落檔 commit 才首次入庫，所以列入（SCG-4 一審 F-01；原清單 7 條漏了它）。ADR-XPLAT-017 §D7 機械核對法的末句由主控依 D-46 改為同一清單（原句「根層 `.github/` 的 diff 必須為空」與 PRD §9.0〈根層連動〉字面衝突，測試會對合法 commit 判紅）。
5. **⚖5 Gate 0 不含 TCS**：與 SPEC_FIRST_GATE「增量文件集（FRD-lite＋TCS）本身走 SCG_VALIDATION → 人類確認 → `spec-frozen`（TCS 必須在 `--doc` 內）」不衝突——後者是**內環** Stage-2；外環 Gate 0 凍結的是 PRD、證據矩陣、議題檔、ADR 草稿（D-23）。
6. **⚖6 審查獨立性**：本鍵的 QA 審查者與起草者同為 AI、同工作區可互讀，不滿足 R-9.20.3 型獨立性；補償＝獨立 session、由 QA 重跑全部 AT 並貼輸出、主控親驗 rc。**不宣稱滿足。**
7. **⚖7 白名單外的落後項**：**已由 D-47 納入白名單**——`docs_template/README.md`、`agent/README.md`、`guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md`、`AISDLC_SDD/CLAUDE.md` 的 Rule 2 目錄樹與〈框架核心文件快速參考〉、`releases/CHANGELOG.md` 頂部日期行（落檔 commit `25c66981`），以及主控補丁 `scripts/framework_status_snapshot.py` 的工作流組成字串（`+1 Research-to-PRD`）；AT-970-2-1 逐項驗。本項不再有落後的導覽項；`agent/README.md` 的 Specialized 計數句原本就落後一支（漏列 `sdd-zero-trust-auditor`），訂正時依訂正協議保留原文逐字（AT-970-2-1 驗）。
8. **⚖8 FSM 演練預期值**：AT-970-7-1～7-4、7-6、7-E-1～7-E-3 的預期值原依讀碼推得；SCG-4 一審（2026-11-02）已於 repo 實跑八個演練 AT，全數 PASS，唯 AT-970-7-1 預期輸出的鍵排序敘述有誤（勘誤 5）。之後再跑與預期不符時，先查預期值是否讀錯並走勘誤，再查實作。演練一律從 `$tmp` 內的版本目錄複本執行，repo 零寫入（勘誤 3）。
9. **⚖9 `HUMAN_PENDING` 逾時**：72 小時提醒、168 小時升級由 hooks 的 SessionStart 檢查執行；Console 路徑沒有 hooks，不會自動提醒或升級。**D-48(3)：Console 路徑以 UI 顯示等待時長＋72h 橫幅、不轉 REMINDER**，不新增 hook 或守衛（記入 Console 架構文件 §12.1 已知限制 L-R；工作流第 11 章）。本鍵不測、不補丁。
10. **⚖10 Track B 增量條款**：**D-48(2)：軌道 B 內環走完整 SCG-1～3**；軌道 A 走增量條款。全新專案不適用增量條款，Gate 0 之後走軌道 B 的內環仍須完整 SCG-1～3（工作流第 9.2 節第 5 點）；本 TCS 只管框架層，不涵蓋軌道 B 的專案。
11. **⚖11 ESCALATION 人工恢復後的審查預算（主控 D-60）**：預設＝不歸零。`resume-from-escalation` 不動重試計數，只有 `gate PASS` 與 `spec-frozen` 歸零，所以人工恢復後至多再得一次審查（FAIL 立即再 ESCALATION、PASS 歸零）；要全新的 3 次預算只能換世代鍵 `research-<slug>-g2`（工作流第 2.5 節；審查卡模板第 2.3 節；演練見 AT-970-7-6）。**已知邊界**：引擎的 `increment_retry` 見計數已達上限時標「tamper detected」並夾在上限，合法的人工恢復後第一次 FAIL 也走這條路，所以歷史列會出現看似遭竄改的字樣而實為預期；不改引擎（Rule 9 絕對禁令 8 與守衛面准入）。AT-970-7-6 為 🔶（預期值依讀碼推得，同 ⚖8）。

---

## 附錄 A：契約自洽檢核器（`r2p_contract_check.py`；隨本檔凍結，AT-970-3-1／3-2／3-E-1 逐字抽出執行）

> 只讀、不寫任何檔、不連網、只用標準函式庫。用法：`python -I -X utf8 <此檔> <SDD 版本目錄> [--selftest]`。為使本附錄可被 AT 以標記抽出，檢核器原始碼不含任何 Markdown 圍欄字樣（反引號圍欄以乘法組出）。

<!-- r2p:verifier=contract_check -->
```python
#!/usr/bin/env python3
"""r2p_contract_check：Research-to-PRD 四份模板的 JSON 契約自洽檢核（一次性驗證腳本）。

用法：python -I -X utf8 r2p_contract_check.py <SDD 版本目錄> [--selftest]
  - 預設：抽出 docs_template/sdd/requirements 四份模板內帶 `<!-- r2p:contract=名稱 -->` 標記的 JSON 區塊，
    逐組檢核契約規則（欄位、編號、錨定、強度函式、公式、條件、跨範例一致）；rc 0 全過、rc 1 有問題。
  - --selftest：對記憶體內的範例逐一注入錯誤，每個錯誤都必須被檢核抓到（證明判準有鑑別力）；另跑「合法變體」，每個都必須不被誤判（證明判準沒有過嚴）；rc 0 全抓到且零誤判、rc 1 有漏網或誤判。
只讀、不寫任何檔、不連網、只用標準函式庫。
"""
import copy
import json
import os
import re
import sys

FENCE = "`" * 3  # 三個反引號；用乘法組出，使本檔嵌進 Markdown 圍欄時不含任何圍欄字樣（TCS 附錄 A 逐字內嵌）
MARK = re.compile(r"<!--\s*r2p:contract=([a-z_]+)\s*-->\r?\n" + FENCE + r"json\r?\n(.*?)\r?\n" + FENCE, re.S)
EXPECTED = ["issue_scope", "evidence_items", "axis_registry", "risk_tag_registry", "review_params",
            "rubric_registry", "review_dimension", "review_dimension_qa", "review_card"]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DIMS = ["ARCHITECTURE", "PRODUCT", "QA", "SECURITY"]
PREFIX = {"ARCHITECTURE": "ARCH", "PRODUCT": "PROD", "QA": "QA", "SECURITY": "SEC"}
ORDER = ["CANDIDATE", "WEAK", "MEDIUM", "STRONG"]
SEVERITIES = {"P1", "P2", "P3", "P4"}
STATUSES = {"OPEN", "FIXED", "REGRESSED", "WAIVED", "SUPERSEDED"}
# 彙整卡每輪的鍵集合（審查卡模板 7.2；D-54 起 prd_version_no 是正式鍵）。VERDICTS 不含 REVIEW_INVALID：它不寫審查輪列（D-55）
ROUND_KEYS = {"round", "prd_version", "prd_version_no", "prd_sha256", "params", "precheck", "reviewers", "weighted_total",
              "min_dimension_score", "conditions", "open_p1_count", "passed", "verdict", "defects", "fsm", "started_at",
              "ended_at"}
VERDICTS = ("PASS", "REVISE", "ESCALATE")
ANCHOR_RE = re.compile(r"^§\d{1,2}(\.\d{1,2})?(/(F|US|AC|NFR|INV|EPIC)-[0-9A-Z-]+)?$")


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def load(vd):
    base = os.path.join(vd, "docs_template", "sdd", "requirements")
    found = {}
    for fn in sorted(os.listdir(base)):
        if not fn.endswith("-TEMPLATE.md"):
            continue
        with open(os.path.join(base, fn), encoding="utf-8") as fh:
            text = fh.read()
        for name, body in MARK.findall(text):
            found.setdefault(name, []).append((fn, json.loads(body)))
    return found


def text_ok(label, s, problems):
    if not isinstance(s, str) or not s.strip():
        problems.append(f"{label} 必須是非空字串")
    elif "|" in s or "\n" in s or len(s) > 600:
        problems.append(f"{label} 含管線字元、換行或超過 600 字元")


def check_issue_scope(d, axes_reg):
    p = []
    req = {"schema_rev", "research_id", "rp_no", "slug", "scope_rev", "title", "topic", "scope", "depth_level",
           "layers", "recency_years", "applicability_axes", "created_by", "created_at"}
    if set(d) != req:
        p.append(f"欄位集合不符：多 {sorted(set(d) - req)} 少 {sorted(req - set(d))}")
        return p
    if d["schema_rev"] != 1:
        p.append("schema_rev 必須為 1")
    if not (isinstance(d["research_id"], str) and d["research_id"].strip()):
        p.append("research_id 必須是非空字串")
    if not (re.fullmatch(r"RP-\d{4,}", str(d["rp_no"])) or d["rp_no"] == "RP-LOCAL"):
        p.append("rp_no 格式不合")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,29}", str(d["slug"])):
        p.append("slug 格式不合（1～30 字）")
    if not (is_int(d["scope_rev"]) and d["scope_rev"] >= 1):
        p.append("scope_rev 必須是 ≥1 的整數")
    if not (isinstance(d["title"], str) and 1 <= len(d["title"]) <= 200):
        p.append("title 長度須 1～200")
    if not (isinstance(d["topic"], str) and 1 <= len(d["topic"]) <= 500):
        p.append("topic 長度須 1～500")
    sc = d["scope"]
    if not (isinstance(sc, dict) and set(sc) == {"in_scope", "out_of_scope", "tech_stack", "target_scope_hint"}):
        p.append("scope 欄位集合不符")
    else:
        if not (isinstance(sc["in_scope"], list) and len(sc["in_scope"]) >= 1):
            p.append("scope.in_scope 至少一項")
        if not isinstance(sc["out_of_scope"], list):
            p.append("scope.out_of_scope 必須是陣列")
        if not (isinstance(sc["tech_stack"], str) and len(sc["tech_stack"]) <= 200):
            p.append("scope.tech_stack 必須是 ≤200 字的字串")
        if sc["target_scope_hint"] not in ("AISDLC_MODULE", "STANDALONE_PROJECT", "UNDECIDED"):
            p.append("scope.target_scope_hint 不在列舉內")
    if d["depth_level"] not in ("QUICK", "STANDARD", "DEEP"):
        p.append("depth_level 不在 QUICK／STANDARD／DEEP")
    if d["recency_years"] not in (1, 2, 3):
        p.append("recency_years 不在 1～3")
    ly = d["layers"]
    if not (isinstance(ly, dict) and set(ly) == {"academic", "industry", "oss", "community"}
            and all(isinstance(v, bool) for v in ly.values()) and any(ly.values())):
        p.append("layers 須為四個布林且至少一個 true")
    ax = d["applicability_axes"]
    if not (isinstance(ax, list) and 1 <= len(ax) <= 6 and len(set(ax)) == len(ax)
            and all(a in axes_reg.values() for a in ax)):
        p.append("applicability_axes 須 1～6 項、不重複、取自軸登錄表標籤")
    if not re.search(r"(Z|[+-]\d{2}:\d{2})$", str(d["created_at"])):
        p.append("created_at 必須帶時區 offset")
    return p


def strength(tier, f7, f4, concl):
    if f7 == "V1":
        s = "CANDIDATE"
    elif tier == "T1" and f7 == "V3":
        s = "STRONG"
    elif (tier == "T1" and f7 == "V2") or (tier == "T2" and f7 == "V3"):
        s = "MEDIUM"
    elif tier == "T2" and f7 == "V2":
        s = "WEAK"
    else:
        return None
    i = ORDER.index(s)
    if concl == "WEAKEN":
        i = max(0, i - 1)
    if concl in ("NOT_FOUND", "NOT_SEARCHED"):
        i = min(i, ORDER.index("MEDIUM"))
    if set(f4) & {"IMM", "SELF", "SCOPE"}:
        i = min(i, ORDER.index("MEDIUM"))
    return ORDER[i]


def check_evidence(d, scope, axes_reg, tags_reg):
    p = []
    top = {"schema_rev", "issue_scope_sha256", "scope_rev", "search_log", "sources", "items",
           "counter_evidence", "honest_bounds"}
    if set(d) != top:
        return [f"頂層欄位集合不符：多 {sorted(set(d) - top)} 少 {sorted(top - set(d))}"]
    if d["schema_rev"] != 1:
        p.append("schema_rev 必須為 1")
    if not HEX64.match(str(d["issue_scope_sha256"])):
        p.append("issue_scope_sha256 必須是 64 位小寫 hex")
    if d["scope_rev"] != scope["scope_rev"]:
        p.append("scope_rev 與議題範例不一致")
    qs = {q["id"]: q for q in d["search_log"]}
    ss = {s["source_no"]: s for s in d["sources"]}
    es = {e["evidence_no"]: e for e in d["items"]}
    for kind, ids, pat in (("Q", [q["id"] for q in d["search_log"]], r"Q-\d{3,4}"),
                           ("S", [s["source_no"] for s in d["sources"]], r"S-\d{3,4}"),
                           ("E", [e["evidence_no"] for e in d["items"]], r"E-\d{3,4}")):
        if len(set(ids)) != len(ids):
            p.append(f"{kind} 編號重複")
        for i in ids:
            if not re.fullmatch(pat, i):
                p.append(f"{kind} 編號格式不合：{i}")
    layers = {"ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY"}
    for q in d["search_log"]:
        if q["layer"] not in layers or q["tool"] not in ("WebSearch", "WebFetch"):
            p.append(f"{q['id']} layer／tool 不在列舉內")
        if not re.search(r"(Z|[+-]\d{2}:\d{2})$", q["at"]):
            p.append(f"{q['id']} at 必須帶 offset")
        if not all(isinstance(u, str) and u.startswith("https://") for u in q["result_urls"]):
            p.append(f"{q['id']} result_urls 必須是 https")
    all_result_urls = {u for q in d["search_log"] for u in q["result_urls"]}
    refd = set()
    for e in d["items"]:
        refd.add(e["source_no"])
    for c in d["counter_evidence"]:
        if c.get("source_no"):
            refd.add(c["source_no"])
    for s in d["sources"]:
        n = s["source_no"]
        if not s["url"].startswith("https://"):
            p.append(f"{n} url 必須是 https")
        if s["anchor_kind"] == "DOI" and not s.get("doi"):
            p.append(f"{n} anchor_kind=DOI 必須有 doi")
        if s["anchor_kind"] == "COMMIT" and not re.fullmatch(r"[0-9a-f]{40}", str(s.get("git_commit"))):
            p.append(f"{n} anchor_kind=COMMIT 必須有 40 位 git_commit")
        if s["url"] not in all_result_urls and not s["fetch_refs"]:
            p.append(f"{n} 的 URL 沒有出處（不在任何 result_urls，也沒有 fetch_refs）")
        if s["tier"] == "T3" and not s["clue_only"]:
            p.append(f"{n} T3 必須 clue_only")
        if s["tier"] in ("T1", "T2") and s["clue_only"]:
            p.append(f"{n} T1／T2 不得 clue_only")
        if s["verification"] not in ("V1", "V2", "V3"):
            p.append(f"{n} verification 不在 V1～V3")
        if s["verification"] == "V3" and not s["fetch_refs"]:
            p.append(f"{n} V3 必須有 fetch_refs")
        if s["source_type"] == "REPO" and not s.get("license_spdx"):
            p.append(f"{n} 開源 repo 必須有 license_spdx")
        if not s["clue_only"] and n not in refd:
            p.append(f"{n} 是孤兒來源（沒有證據項或反證引用）")
        for k in ("title", "authors_org", "license_note"):
            text_ok(f"{n}.{k}", s[k], p)
    lab2id = {v: k for k, v in axes_reg.items()}
    want_axes = {lab2id[a] for a in scope["applicability_axes"]}
    ce = {}
    for c in d["counter_evidence"]:
        if c["evidence_no"] in ce:
            p.append(f"{c['evidence_no']} 有多筆反證")
        ce[c["evidence_no"]] = c
    for eno, e in es.items():
        src = ss.get(e["source_no"])
        if src is None:
            p.append(f"{eno} 的 source_no 不存在")
            continue
        if src["clue_only"] or src["tier"] == "T3":
            p.append(f"{eno} 引用了 T3 線索來源")
        if e["scope_rev"] != d["scope_rev"]:
            p.append(f"{eno} scope_rev 不一致")
        rank = {"V1": 1, "V2": 2, "V3": 3}
        if rank.get(e["f7"], 9) > rank[src["verification"]]:
            p.append(f"{eno} f7 高於來源 verification")
        for k in ("claim", "f1", "f2", "f3", "f6"):
            text_ok(f"{eno}.{k}", e[k], p)
        if not all(t in tags_reg for t in e["f4"]):
            p.append(f"{eno} f4 含登錄表外的標籤")
        if set(e["f5"]) != want_axes:
            p.append(f"{eno} f5 的鍵集合與議題的 applicability_axes 不符")
        for ax, v in e["f5"].items():
            if v.get("grade") not in ("A", "M", "N"):
                p.append(f"{eno}.f5.{ax} grade 不在 A／M／N")
            text_ok(f"{eno}.f5.{ax}.reason", v.get("reason"), p)
        c = ce.get(eno)
        if c is None:
            p.append(f"{eno} 缺反證結論")
            continue
        if c["conclusion"] not in ("WEAKEN", "LIMIT", "IRRELEVANT", "NOT_FOUND", "NOT_SEARCHED"):
            p.append(f"{eno} 反證 conclusion 不在列舉內")
        if c["conclusion"] == "NOT_FOUND":
            if c["search_id"] not in qs:
                p.append(f"{eno} NOT_FOUND 必須附存在的 search_id")
            elif qs[c["search_id"]]["query"] not in [x["query"] for x in d["honest_bounds"]["not_found"]]:
                p.append(f"{eno} NOT_FOUND 的搜尋字串必須同時列入 honest_bounds.not_found")
        if c["conclusion"] == "NOT_SEARCHED" and c["search_id"] is not None:
            p.append(f"{eno} NOT_SEARCHED 不得附 search_id")
        if c["conclusion"] in ("WEAKEN", "LIMIT", "IRRELEVANT") and c.get("source_no") not in ss:
            p.append(f"{eno} {c['conclusion']} 必須附存在的反證 source_no")
        want = strength(src["tier"], e["f7"], e["f4"], c["conclusion"])
        if e["strength"] != want:
            p.append(f"{eno} strength={e['strength']} 但函式值為 {want}")
    if set(ce) - set(es):
        p.append("反證指向不存在的證據項")
    hb = d["honest_bounds"]
    v12 = {n for n, s in ss.items() if s["verification"] in ("V1", "V2")}
    non3 = {n for n, s in ss.items() if s["verification"] != "V3"}
    if not v12 <= set(hb["summary_only"]):
        p.append("summary_only 未涵蓋全部 V1／V2 來源")
    if not non3 <= set(hb["not_read_fully"]):
        p.append("not_read_fully 未涵蓋全部非 V3 來源")
    return p


def check_params(d):
    p = []
    if set(d) != {"weights", "threshold", "dimension_floor"}:
        return ["review_params 欄位集合不符"]
    w = d["weights"]
    if set(w) != set(DIMS) or sum(round(v * 100) for v in w.values()) != 100:
        p.append("weights 須含四個維度且加總為 1")
    if d["threshold"] != 85 or d["dimension_floor"] != 60:
        p.append("threshold 須為 85、dimension_floor 須為 60")
    return p


def check_registry(reg, vd, params):
    p = []
    if set(reg) != set(DIMS):
        return ["rubric_registry 維度集合不符"]
    for dim, r in reg.items():
        if r["defect_prefix"] != PREFIX[dim]:
            p.append(f"{dim} defect_prefix 不符")
        if round(r["weight"] * 100) != round(params["weights"][dim] * 100):
            p.append(f"{dim} weight 與 review_params 不一致")
        items = r["items"]
        if len(items) != 5 or len(set(items)) != 5:
            p.append(f"{dim} 必須恰五個不重複項目")
        for key in ("agent_file", "assist_agent_file"):
            f = r.get(key)
            if f is not None and not os.path.isfile(os.path.join(vd, f)):
                p.append(f"{dim}.{key} 指向不存在的檔：{f}")
        if r["agent_file"] is None:
            p.append(f"{dim} 缺 agent_file")
    return p


def check_dimension(d, reg, evidence_ids, qa):
    p = []
    base = {"schema_rev", "round", "dimension", "agent_id", "prd_sha256", "rubric", "score", "summary", "defects"}
    want = base | ({"qa_extra"} if qa else set())
    if set(d) != want:
        return [f"欄位集合不符：多 {sorted(set(d) - want)} 少 {sorted(want - set(d))}"]
    dim = d["dimension"]
    if dim not in reg:
        return ["dimension 不在四維內"]
    r = reg[dim]
    if (dim == "QA") != qa:
        p.append("qa_extra 只能出現在 QA 維度")
    if d["schema_rev"] != 1 or not (is_int(d["round"]) and d["round"] >= 1):
        p.append("schema_rev／round 不合")
    if d["agent_id"] != r["agent_id"]:
        p.append("agent_id 與登錄表不符")
    if not HEX64.match(d["prd_sha256"]):
        p.append("prd_sha256 必須是 64 位小寫 hex")
    rub = d["rubric"]
    if sorted(x["item"] for x in rub) != sorted(r["items"]):
        p.append("rubric 項目集合與登錄表不符")
    for x in rub:
        if x["max"] != 20 or not (is_int(x["score"]) and 0 <= x["score"] <= 20):
            p.append(f"{x['item']} 分數須為 0～20 整數且 max=20")
        text_ok(f"{x['item']}.note", x["note"], p)
        if is_int(x["score"]) and x["score"] >= 18 and "§" not in x["note"]:
            p.append(f"{x['item']} ≥18 分的 note 必須含 § 錨點")
    if d["score"] != sum(x["score"] for x in rub):
        p.append("score 必須等於五項之和")
    text_ok("summary", d["summary"], p)
    code_re = re.compile(r"^%s-([A-Z][A-Z0-9_]{1,23})-[0-9]{2}$" % PREFIX[dim])
    for df in d["defects"]:
        m = code_re.match(df["code"])
        if not m or m.group(1).lower() not in r["items"]:
            p.append(f"缺陷 code 不合文法或項目不屬本維度：{df['code']}")
        if df["severity"] not in SEVERITIES:
            p.append(f"{df['code']} severity 不在 P1～P4")
        if not ANCHOR_RE.match(df["prd_anchor"]):
            p.append(f"{df['code']} prd_anchor 不合文法")
        for k in ("description", "suggestion"):
            text_ok(f"{df['code']}.{k}", df[k], p)
        for ref in df["evidence_refs"]:
            if ref not in evidence_ids:
                p.append(f"{df['code']} evidence_refs 指向不存在的 {ref}")
    if qa:
        s = d["qa_extra"].get("slv_manual_check", {})
        if not (is_int(s.get("ac_total")) and is_int(s.get("ac_testable")) and 0 <= s["ac_testable"] <= s["ac_total"]
                and isinstance(s.get("notes"), str) and s["notes"].strip()):
            p.append("qa_extra.slv_manual_check 不合")
    return p


def check_card(card, reg, params, dim_examples, scope):
    p = []
    if set(card) != {"schema_rev", "research_id", "rounds", "retry_count", "final_verdict"}:
        return ["review_card 頂層欄位集合不符"]
    if card["research_id"] != scope["research_id"]:
        p.append("review_card.research_id 與議題範例不一致")
    rounds = card["rounds"]
    for idx, rd in enumerate(rounds, 1):
        t = f"round {idx}"
        if not isinstance(rd, dict) or set(rd) != ROUND_KEYS:
            got = set(rd) if isinstance(rd, dict) else set()
            p.append(f"{t} 欄位集合不符：多 {sorted(got - ROUND_KEYS)} 少 {sorted(ROUND_KEYS - got)}")
            continue
        if rd["round"] != idx:
            p.append(f"{t} 序號不連續")
        if not (is_int(rd["prd_version_no"]) and rd["prd_version_no"] >= 1):
            p.append(f"{t} prd_version_no 必須是 ≥1 的整數（對映資料庫 version_no）")
        if not (isinstance(rd["prd_version"], str) and rd["prd_version"].strip()):
            p.append(f"{t} prd_version 必須是非空字串（semver）")
        if not HEX64.match(rd["prd_sha256"]):
            p.append(f"{t} prd_sha256 必須是 64 位小寫 hex")
        if rd["params"] != params:
            p.append(f"{t} params 快照與 review_params 不一致")
        pc = rd["precheck"]
        if {c["id"] for c in pc["checks"]} != {"SLV-001", "SLV-002", "SLV-003", "AMBIGUITY"}:
            p.append(f"{t} precheck.checks 的 id 集合不符")
        if pc["passed"] != all(c["passed"] for c in pc["checks"]):
            p.append(f"{t} precheck.passed 與 checks 不一致")
        rv = {x["dimension"]: x for x in rd["reviewers"]}
        if set(rv) != set(DIMS) or len(rd["reviewers"]) != 4:
            p.append(f"{t} reviewers 必須恰四個維度")
            continue
        w100 = 0
        for dim, x in rv.items():
            r = reg[dim]
            if round(x["weight"] * 100) != round(r["weight"] * 100):
                p.append(f"{t} {dim} weight 不一致")
            if x["agent_id"] != r["agent_id"]:
                p.append(f"{t} {dim} agent_id 不一致")
            if x["agent"] != os.path.basename(r["agent_file"])[:-5]:
                p.append(f"{t} {dim} agent 檔名與登錄表不一致")
            for k in ("agent_yaml_sha256", "persona_sha256", "raw_sha256"):
                if not HEX64.match(str(x[k])):
                    p.append(f"{t} {dim}.{k} 必須是 64 位小寫 hex")
            if (x["assist_agent_id"] is None) != (x["assist_agent_yaml_sha256"] is None):
                p.append(f"{t} {dim} assist 欄位須同為 null 或同有值")
            if x["assist_agent_id"] != r["assist_agent_id"]:
                p.append(f"{t} {dim} assist_agent_id 與登錄表不一致")
            if x["raw_file"] != f"02_governance/reviews/round-{idx}/{dim.lower()}.json":
                p.append(f"{t} {dim} raw_file 路徑不合")
            if not (is_int(x["score"]) and 0 <= x["score"] <= 100):
                p.append(f"{t} {dim} score 必須是 0～100 整數")
            w100 += round(x["weight"] * 100) * x["score"]
        if round(rd["weighted_total"] * 100) != w100:
            p.append(f"{t} weighted_total={rd['weighted_total']} 但 W100={w100}")
        cond = rd["conditions"]
        scores = [x["score"] for x in rv.values()]
        if rd["min_dimension_score"] != min(scores):
            p.append(f"{t} min_dimension_score={rd['min_dimension_score']} 但最低分為 {min(scores)}")
        want = {
            "precheck_passed": pc["passed"],
            "weighted_ge_threshold": w100 >= params["threshold"] * 100,
            "all_dimensions_ge_floor": min(scores) >= params["dimension_floor"],
            "no_open_p1": rd["open_p1_count"] == 0,
        }
        if cond != want:
            p.append(f"{t} conditions={cond} 但依資料應為 {want}")
        if rd["passed"] != all(want.values()):
            p.append(f"{t} passed 與四條件之且不一致")
        if (rd["verdict"] == "PASS") != rd["passed"]:
            p.append(f"{t} verdict 與 passed 不一致")
        fs = rd["fsm"]
        if not (isinstance(fs, dict) and set(fs) == {"gate_result", "retry_count"}):
            p.append(f"{t} fsm 欄位集合不符")
        else:
            gr, rcn = fs["gate_result"], fs["retry_count"]
            if gr is None:
                # 未呼叫 gate 的輪＝POST_HUMAN 再審通過（D-54）：現態已是 HUMAN_PENDING，不呼叫 gate PASS，所以只可能是通過的輪；
                # 沒有 gate 回傳就沒有 retry_count。未通過的輪一律呼叫 gate FAIL
                if rd["passed"] is not True:
                    p.append(f"{t} fsm.gate_result 為 null 只准用於 POST_HUMAN 再審通過的輪（passed 必須為 true）")
                if rcn is not None:
                    p.append(f"{t} 未呼叫 gate 的輪 fsm.retry_count 也必須是 null")
            elif gr not in ("PASS", "FAIL"):
                p.append(f"{t} fsm.gate_result 必須是 PASS、FAIL 或 null")
            else:
                if gr != ("PASS" if rd["passed"] else "FAIL"):
                    p.append(f"{t} fsm.gate_result 與 passed 不一致")
                if not (is_int(rcn) and rcn >= 0):
                    p.append(f"{t} 有呼叫 gate 的輪 fsm.retry_count 必須是 ≥0 的整數")
        if rd["verdict"] not in VERDICTS:
            p.append(f"{t} verdict 不在 PASS／REVISE／ESCALATE 內（REVIEW_INVALID 不寫審查輪列）")
        for df in rd["defects"]:
            if not re.fullmatch(r"D-%d-\d{3}" % idx, df["id"]):
                p.append(f"{t} 缺陷 id 格式不合：{df['id']}")
            if df["severity"] not in SEVERITIES or df["status"] not in STATUSES:
                p.append(f"{t} {df['id']} severity／status 不在列舉內")
            if (df["status"] == "FIXED") != (df["resolved_in"] is not None):
                p.append(f"{t} {df['id']} resolved_in 與 status 不一致")
            if (df["status"] == "WAIVED") != (df["waiver"] is not None):
                p.append(f"{t} {df['id']} waiver 與 status 不一致")
        if idx == 1:
            for ex in dim_examples:
                if ex["score"] != rv[ex["dimension"]]["score"]:
                    p.append(f"單維度範例 {ex['dimension']} 的 score 與彙整卡第 1 輪不一致")
                if ex["prd_sha256"] != rd["prd_sha256"]:
                    p.append(f"單維度範例 {ex['dimension']} 的 prd_sha256 與彙整卡第 1 輪不一致")
    # prd_version_no／prd_version／prd_sha256 描述同一份 PRD（審查卡模板 7.3 不變量 4）
    seen, prev = {}, 0
    for idx, rd in enumerate(rounds, 1):
        if not (isinstance(rd, dict) and set(rd) == ROUND_KEYS and is_int(rd["prd_version_no"])):
            continue
        vno = rd["prd_version_no"]
        if vno < prev:
            p.append(f"round {idx} prd_version_no={vno} 小於前一輪的 {prev}（輪與輪之間不遞減）")
        prev = max(prev, vno)
        if seen.setdefault(vno, (rd["prd_version"], rd["prd_sha256"])) != (rd["prd_version"], rd["prd_sha256"]):
            p.append(f"round {idx} 同一 prd_version_no={vno} 對應到不同的 prd_version 或 prd_sha256")
    last = rounds[-1]["verdict"] if rounds and isinstance(rounds[-1], dict) and "verdict" in rounds[-1] else None
    if (card["final_verdict"] == "PASS") != (last == "PASS"):
        p.append("final_verdict 與最後一輪 verdict 不一致")
    if not (is_int(card["retry_count"]) and card["retry_count"] >= 0):
        p.append("retry_count 必須是 ≥0 的整數")
    return p


def run_all(blocks, vd):
    one = {k: blocks[k][0][1] for k in EXPECTED}
    axes, tags, params = one["axis_registry"], one["risk_tag_registry"], one["review_params"]
    reg = one["rubric_registry"]
    ev_ids = {e["evidence_no"] for e in one["evidence_items"]["items"]}
    dims = [one["review_dimension"], one["review_dimension_qa"]]
    out = []
    out.append(("issue_scope", check_issue_scope(one["issue_scope"], axes)))
    out.append(("evidence_items", check_evidence(one["evidence_items"], one["issue_scope"], axes, tags)))
    out.append(("review_params", check_params(params)))
    out.append(("rubric_registry", check_registry(reg, vd, params)))
    out.append(("review_dimension", check_dimension(dims[0], reg, ev_ids, False)))
    out.append(("review_dimension_qa", check_dimension(dims[1], reg, ev_ids, True)))
    out.append(("review_card", check_card(one["review_card"], reg, params, dims, one["issue_scope"])))
    return out


def selftest(blocks, vd):
    base = {k: blocks[k][0][1] for k in EXPECTED}
    cases = []

    def mut(name, group, fn):
        cases.append((name, group, fn))

    def ev(fn):
        def go(b):
            fn(b["evidence_items"])
        return go

    mut("E-001 strength 改 WEAK", "evidence_items", ev(lambda d: d["items"][0].__setitem__("strength", "WEAK")))
    mut("證據項引用 T3 線索來源", "evidence_items", ev(lambda d: d["items"][0].__setitem__("source_no", "S-004")))
    mut("刪除 E-004 的反證", "evidence_items", ev(lambda d: d["counter_evidence"].pop()))
    mut("來源 verification 降 V1 但 f7 仍 V3", "evidence_items", ev(lambda d: d["sources"][0].__setitem__("verification", "V1")))
    mut("儲存格含管線字元", "evidence_items", ev(lambda d: d["items"][1].__setitem__("f2", "a|b")))
    mut("NOT_FOUND 的字串不在 not_found", "evidence_items", ev(lambda d: d["honest_bounds"].__setitem__("not_found", [])))
    mut("summary_only 少列 V2 來源", "evidence_items", ev(lambda d: d["honest_bounds"]["summary_only"].pop()))
    mut("issue_scope_sha256 少一碼", "evidence_items", ev(lambda d: d.__setitem__("issue_scope_sha256", d["issue_scope_sha256"][:-1])))
    mut("depth_level 用整數", "issue_scope", lambda b: b["issue_scope"].__setitem__("depth_level", 2))
    mut("layers 少一個鍵", "issue_scope", lambda b: b["issue_scope"]["layers"].pop("community"))
    mut("slug 超過 30 字", "issue_scope", lambda b: b["issue_scope"].__setitem__("slug", "a" * 31))
    mut("created_at 不帶 offset", "issue_scope", lambda b: b["issue_scope"].__setitem__("created_at", "2026-11-02T10:00:00"))
    mut("單維度 score 不等於加總", "review_dimension", lambda b: b["review_dimension"].__setitem__("score", 99))
    mut("非 QA 維度帶 qa_extra", "review_dimension", lambda b: b["review_dimension"].__setitem__("qa_extra", {}))
    mut("彙整卡第 1 輪 weighted_total 改 85.0", "review_card", lambda b: b["review_card"]["rounds"][0].__setitem__("weighted_total", 85.0))
    mut("彙整卡 no_open_p1 與 open_p1_count 矛盾", "review_card", lambda b: b["review_card"]["rounds"][1]["conditions"].__setitem__("no_open_p1", False))
    mut("彙整卡 verdict 與 passed 矛盾", "review_card", lambda b: b["review_card"]["rounds"][0].__setitem__("verdict", "PASS"))
    mut("彙整卡 min_dimension_score 與最低分不符", "review_card", lambda b: b["review_card"]["rounds"][0].__setitem__("min_dimension_score", 80))
    mut("彙整卡 fsm.gate_result 與 passed 矛盾", "review_card", lambda b: b["review_card"]["rounds"][1]["fsm"].__setitem__("gate_result", "FAIL"))
    mut("彙整卡 research_id 與議題不一致", "review_card", lambda b: b["review_card"].__setitem__("research_id", "other-id"))
    mut("登錄表 agent_file 指向不存在的檔", "rubric_registry", lambda b: b["rubric_registry"]["QA"].__setitem__("agent_file", "agent/core/nope.yaml"))
    mut("review_params 門檻改 80", "review_params", lambda b: b["review_params"].__setitem__("threshold", 80))
    mut("彙整卡第 1 輪缺 prd_version_no", "review_card", lambda b: b["review_card"]["rounds"][0].pop("prd_version_no"))
    mut("彙整卡 prd_version_no 用字串", "review_card", lambda b: b["review_card"]["rounds"][0].__setitem__("prd_version_no", "1"))
    mut("彙整卡同一 prd_version_no 對到不同雜湊", "review_card", lambda b: b["review_card"]["rounds"][1].__setitem__("prd_version_no", 1))
    mut("彙整卡 prd_version_no 遞減", "review_card", lambda b: b["review_card"]["rounds"][0].__setitem__("prd_version_no", 3))
    mut("彙整卡未通過的輪 fsm.gate_result 為 null", "review_card", lambda b: b["review_card"]["rounds"][0]["fsm"].update({"gate_result": None, "retry_count": None}))
    mut("彙整卡未呼叫 gate 的通過輪 retry_count 非 null", "review_card", lambda b: b["review_card"]["rounds"][1]["fsm"].update({"gate_result": None}))
    mut("彙整卡 verdict 用已移除的 REVIEW_INVALID", "review_card", lambda b: b["review_card"]["rounds"][0].__setitem__("verdict", "REVIEW_INVALID"))
    # 合法變體：判準不得過嚴（D-54：POST_HUMAN 再審通過的輪沒有 gate 回傳）
    oks = [("POST_HUMAN 再審通過的輪（fsm.gate_result 與 retry_count 皆 null）合法", "review_card",
            lambda b: b["review_card"]["rounds"][1]["fsm"].update({"gate_result": None, "retry_count": None}))]
    missed = []
    for name, group, fn in cases:
        b = copy.deepcopy(base)
        blocks2 = {k: [("(mut)", b[k])] for k in EXPECTED}
        fn(b)
        res = dict(run_all(blocks2, vd))
        if not res.get(group):
            missed.append(f"{name}（預期 {group} 報錯，實際無）")
    false_alarms = []
    for name, group, fn in oks:
        b = copy.deepcopy(base)
        blocks2 = {k: [("(ok)", b[k])] for k in EXPECTED}
        fn(b)
        res = dict(run_all(blocks2, vd))
        if res.get(group):
            false_alarms.append(f"{name}（預期 {group} 無誤，實際報錯：{res[group][0]}）")
    return len(cases), missed, len(oks), false_alarms


def main(argv):
    if not argv or argv[0].startswith("--"):
        print("用法：python -I -X utf8 r2p_contract_check.py <SDD 版本目錄> [--selftest]", file=sys.stderr)
        return 2
    vd = os.path.abspath(argv[0])
    blocks = load(vd)
    bad = 0
    for name in EXPECTED:
        n = len(blocks.get(name, []))
        if n != 1:
            print(f"FAIL marker {name}: 找到 {n} 個（必須恰 1 個）")
            bad += 1
    if bad:
        return 1
    if "--selftest" in argv:
        total, missed, n_ok, false_alarms = selftest(blocks, vd)
        for m in missed:
            print("FAIL selftest 漏網：" + m)
        for m in false_alarms:
            print("FAIL selftest 誤判：" + m)
        print(f"r2p_contract_check selftest: {total} 個注入錯誤，漏網 {len(missed)}；{n_ok} 個合法變體，誤判 {len(false_alarms)}")
        return 1 if (missed or false_alarms) else 0
    problems = 0
    for group, probs in run_all({k: blocks[k] for k in EXPECTED}, vd):
        if probs:
            problems += len(probs)
            for pr in probs:
                print(f"FAIL {group}: {pr}")
        else:
            print(f"OK   {group}")
    print(f"r2p_contract_check: {len(EXPECTED)} 個契約區塊、{problems} 項問題")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

---

## 勘誤（凍結後的訂正；內文已就地訂正、被訂正的原文逐字保留於下表；走 `spec-refreeze`）

> 日期一律 2026-11-02；來源＝SCG-4 一審（鍵 `sdd-research-to-prd`，commit `25c66981`）的發現 F-01～F-07 與其計數連動；勘誤 10 來源＝SCG-4 二審（同鍵，TCS 現檔 `9602289ef45c…`）的邊界發現 N-1。

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| 1 | 2026-11-02 | `AT-970-5-1` 的 `$rootExempt`、`-eq 7`、預期輸出；`AT-970-5-E-1` 的 `$okPaths` 與 `$c6`；§5 資料表；§7 ⚖4；W-F6；AT-970-5-1 描述 | 「逐字 7 條：`.gitignore`、`.github/workflows/agentconsole-ci.yml`、`docs/01_requirements/ResearchToPRD_PRD.md`、`docs/01_requirements/Agent_ConsoleUI_PRD.md`、ADR-XPLAT-016、ADR-XPLAT-017、`AgentConsole/**`」；`-eq 7`；`root exempt entries: 7` | 加第 8 條 `docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`（排在 `ResearchToPRD_PRD.md` 之後，與 ADR-XPLAT-017 §D7 同序），字面 7 改 8；5-E-1 的合法路徑加該檔，並以近似檔名 `….md.bak` 證明清單是逐字比對 | 該檔在起點 commit `01d9be6e` 不存在（`git cat-file -e 01d9be6e:<路徑>` rc 128），首次入庫於 `25c66981`；一審 AT-970-5-1 `FAIL violations=1`；對真 repo 加第 8 條後 5-1／5-2／5-E-1 全 PASS（QA 一審 F-01）；PRD §9.0 與附錄 C.7 D-46、ADR-XPLAT-017 §D7、計畫書同批由主控訂正 |
| 2 | 2026-11-02 | 檔頭〈增量條款〉段與輸入快照列；〈增量追溯表〉說明、U 表與 SCG 各列；`AT-970-5-3`；§5 資料表；§6 收尾段；§7 ⚖1 | 「以下三個是 **Stage-1 採納當下（本鍵改動之前）** 的基準」「路徑相對 `spec-frozen --root`＝`AISDLC_SDD/`」；U1 `CLAUDE.md` `sha256:e1a2801843b9…`、U2 `AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md` `sha256:7c6d5620e70f…`、U3 `AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` `sha256:c44b47a825c8…`；AT-970-5-3「取 `frozen_stages` 中 `Stage-1` 的 `spec_doc_digests`，與本檔〈增量追溯表〉的三個摘要比對」；「收尾重凍的 `--doc`＝Stage-1 採納的三份上位文件」 | 表改為真 Stage-1 記錄：五份（U1～U3 加根層 PRD、ADR-001）、`--root`＝monorepo 根、鍵＝相對根的正斜線路徑、值＝改動後內容摘要（U1 `09d88638…`、U2 `c0732753…`、U3 `ca913bb1…`、U4 `179e839f…`、U5 `c2935ae1…`；U4 是 PRD 於 2026-11-02 07:08:57Z 修改後的現檔）；保留改動前三份摘要作資訊基準；AT-970-5-3 改讀 `frozen_stages` 全部條目的聯集並比對五鍵；§6 收尾段與 ⚖1 改述 | 一審 AT-970-5-3 `FAIL rc=0 table_rows=3`（三個凍結值皆空）；Stage-1 於 2026-11-02T04:04:47Z 才採納、記五份改動後摘要（QA 一審 F-02）；`spec-refreeze` 追加的重記條目其 `stage` 取最近一筆（Stage-2）且只含被點名的文件，消費端取聯集（`state_loader.py` 的 `record_spec_refreeze`），所以只讀 `Stage-1` 那一筆會在重記後失明 |
| 3 | 2026-11-02 | §2.7 引言、`AT-970-7-0`、`AT-970-7-Z`（`AT-970-7-E-1` 受影響）；`AT-970-7-5` 的 python 呼叫 | 「演練只寫 `$tmp` 之下的暫存狀態目錄（`SDD_STATE_DIR`）」；`Invoke-Sdd` 以 `Push-Location $vd` 從 repo 的版本目錄執行；7-5 的 `& $py -I -X utf8 $script $vd` | AT-970-7-0 建立 `$tmp/AISDLC_SDD`（版本目錄與 `scripts/` 的複本）；`Invoke-Sdd` 改從 `$fsmVd` 執行；7-Z 一併刪除；§2.7 引言據實改寫；7-5 加 `-B`（不在 repo 寫位元組碼） | `snapshot.py:17` 的 `SNAPSHOT_DIR`（`REPO_ROOT/build/reports/abort`，`REPO_ROOT` 由模組檔位置推得）不隨 `SDD_STATE_DIR`；一審 7-E-1 在真 repo 留下 `ABORT-<日期>-auto-recovery-refused.md` 與 `ABORT-RAW-<日期>.yaml`（QA 一審 F-03）；後者是讀改寫的累加檔（`_append_raw_abort_event`），同日已有真實事件時無法精準清除，所以以隔離取代清理；複本須含 `AISDLC_SDD/scripts/`（`state_loader.py` 以 `parents[3]/scripts/component_sanitizer.py` 載入共用淨化模組，只複製版本目錄會 `FileNotFoundError`；作者以暫存複本實測） |
| 4 | 2026-11-02 | `AT-970-6-1` 的 P0-7 檢查；新增 `AT-970-6-6`；§1、§3、§6、SCG-4 通過標準的計數 | `'SE-PRD 模板 P0-7 列含四個預檢代碼' = ($p07 -ne '' -and @($codes | Where-Object { -not $p07.Contains($_) }).Count -eq 0)`（以 `Contains` 判整列）；沒有 AT 比對散文條文 | 改逐處計數（`CITES_MISSING` 1、`CITES_V1` 2、`CITES_UNANCHORED` 1、`CITES_CANDIDATE` 2）並要求四個「否則 `代碼`」定義子句；新增 AT-970-6-6，對八個散文條文與 `review_params` JSON、引擎 `RETRY_LIMITS` 對拍 | 一審突變 M27（P0-7 列內 `CITES_CANDIDATE` 出現兩次，改一處仍 PASS）與 S01～S08（八個散文條文改動全數存活；QA 一審 F-04）；訂正後 M27 與 S01～S08 皆被殺死（作者以突變自證腳本實跑） |
| 5 | 2026-11-02 | `AT-970-7-1` 預期輸出第三行 | `digest keys: 00_research/evidence_matrix.md,00_research/issue_scope.json,01_specs/PRD-v1.0.0.md,01_specs/adr_draft.md` | `digest keys: 00_research/evidence_matrix.md,00_research/issue_scope.json,01_specs/adr_draft.md,01_specs/PRD-v1.0.0.md` | `Sort-Object` 不分大小寫，`adr_draft` 排在 `PRD-v1.0.0` 之前；一審實跑如此（`RESULT` 行不受影響，AT 兩側用同一排序；QA 一審 F-05） |
| 6 | 2026-11-02 | 檔頭 D5 列；`AT-970-1-1` 與 FRD-lite AC-970-1 的 Given；§2 引言；§7 ⚖1、⚖7、⚖8 | 「依 SD-B 的 `FRAMEWORK_EDITS.md` E01～E36 逐塊套用」「重現指令見 `FRAMEWORK_VERIFY.md` 步驟 9b」「（`FRAMEWORK_EDITS.md` E32～E36）」「（E33a、E33g）」「Given 框架鍵視窗依 `FRAMEWORK_EDITS.md` 落地」 | 改為 repo 內可重現的依據：落檔 commit `25c66981`；只增不減以 `git diff --numstat --diff-filter=M 01d9be6e 25c66981 -- AISDLC_SDD ':(exclude)AISDLC_SDD/FRAMEWORK_STATUS.md' ':(exclude)AISDLC_SDD/scripts'` 重現（13 個被改檔，合計 +176／−22） | 兩檔是作者的過程文件、不在 repo，他機無法照 TCS 重現（QA 一審 F-06）；一審以同一 numstat 重算，與 ⚖1 宣稱逐值相同。不加篩選的 `-- AISDLC_SDD` 得 24 檔 +4632／−29（連 9 個新增檔、`FRAMEWORK_STATUS.md` 與 `framework_status_snapshot.py` 一併計入），不是 +176／−22；加 `--diff-filter=M` 並排除那兩檔才是 13 個被改檔的合計（作者對 repo 實跑：13 檔 +176／−22） |
| 7 | 2026-11-02 | 〈上位需求對照〉AC-970-5 列 | `NFR-R2P-08（變更集合與回填）`／`AC-R2P-10-9` | `NFR-R2P-08（文件最小集與回填）；變更邊界的直接依據是 PRD §9.0 落點表與 ADR-XPLAT-017 §D7（非 AC）`／`AC-R2P-11-7、AC-R2P-12-6` | AC-R2P-10-9 是 `:freeze` 的 422 `missing_tcs` 契約，與變更邊界無關；AC-R2P-11-7 是 Stage-1 採納以 `--digest --root` 記摘要、AC-R2P-12-6 是治理檔與 `tools/`、`.claude/` 零變更（`git diff --name-only` 核對）（QA 一審 F-07；作者讀 PRD 選定） |
| 8 | 2026-11-02 | 檔頭計數、§1 表與覆蓋率、§3、§6、SCG-4 通過標準 | 「AT 34 個（正控 25、負控 9）」「已映射 AT 數: 34（✅ 26、🔶 8）」「Unit 12、Integration 18、Contract 3、E2E 1」「7 個 AC、34 個 AT」 | 「AT 35 個（正控 26、負控 9）」「已映射 AT 數: 35（✅ 27、🔶 8）」「Unit 13、Integration 18、Contract 3、E2E 1」「7 個 AC、35 個 AT」 | 新增 AT-970-6-6（勘誤 4） |
| 9 | 2026-11-02 | 本節標題與說明 | 「勘誤（凍結後的訂正只寫在這裡，走 `spec-refreeze`；不改上方原文）」 | 「勘誤（凍結後的訂正；內文已就地訂正、被訂正的原文逐字保留於下表；走 `spec-refreeze`）」 | AT 區塊是可由 QA 逐字抽出執行的指令；只在勘誤表另寫更正，會讓抽出者執行到已知錯誤的舊區塊（一審 QA 即須在 driver 複本手動套用修法）。被訂正的原文仍逐字保留於本表（訂正協議：禁止靜默覆寫） |
| 10 | 2026-11-02 | `AT-970-6-6` 描述、區塊（新增 `$nMax` 與第九檢核）、預期輸出；§1 表 AT-970-6-6 列 | 「Then 八項皆成立」「預期輸出：八行 `PASS …`」；區塊只抽「第 N 次…ESCALATION」（`$nEsc`），無「最多 N 輪」抽取 | 加第 (9) 項：工作流四處（§1 流程圖、§2.3 標題、§2.3 結論句、§6.3 末段）、審查卡 §2.3、ADR-001 預算語意列的「最多 N 輪」復述逐處抽出 N，與引擎 `RETRY_LIMITS["SCG_VALIDATION"]` 對拍（`(?<!＝)最多 (\d+) 輪`：以前置「＝」排除 §2.3 的來源規格對照句「＝最多 4 輪」；`-ge 6`）；八改九 | SCG-4 二審 N-1（P4）：6-6 (3) 只守六處「第 N 次…ESCALATION」，QA 鏡突變 S09（工作流 §2.3 標題 3→4）與 S10（§6.3 末段 3→4）存活、範圍內 S11 被殺；訂正後由主控在 RELEASE_READY 態實跑 6-6 並重放 S09／S10，輸出貼於 SCG-4 報告落檔版〈二審後附記〉，再以 `spec-refreeze` 重記本檔 |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 7 個 AC、35 個 AT，無未映射 AC | □ |
| AT 格式可自動化 | 每個 AT 為 PowerShell 指令＋`RESULT … PASS／FAIL` 判定行（🔶 者已標預期值依據） | □ |
| 負向測試覆蓋 | 每個 AC 至少一個負控（AT-970-1～7 的 `E-1`） | □ |
| 邊界值測試 | 白名單邊界、檔案形態（BOM／CR／檔尾）、值域（`topic`／`slug`／`depth_level`／`layers`）、人工恢復後的預算邊界皆有 AT | □ |
| 測試資料規格完整 | §5 資料來源明確 | □ |
| 輸出逐字貼證據 | 每個 AT 的 `RESULT` 行與重要輸出貼進 `docs/06_quality/` 的證據檔（沒貼＝未驗證） | □ |
| 🔶 項實跑 | AT-970-7-1～7-4、7-6、7-E-1～7-E-3 由獨立 QA 實跑；與預期不符走勘誤 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

**最後更新**: 2026-11-02
