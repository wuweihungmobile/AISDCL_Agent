# RTM — Research-to-PRD 框架層（鍵 `sdd-research-to-prd`）

**專案**: AISDLC-SDD 框架（LATEST＝`AISDLC_SDD_v0.30`；外部專案模式 `sub=sdd`，BRIDGE §8）
**TCS**: `docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md`（Stage-2 凍結；SCG-4 二審時的現檔 sha256 `9602289ef45c…`；其後只有勘誤 10 的訂正，以 `spec-refreeze` 重記為 `8514830713af…`，RELEASE_READY 態）
**審查報告**: `docs/06_quality/SCG4-REVIEW-ResearchToPRD-Framework-20261102.md`（一審 FAIL 2026-11-02 14:2x → 二審 PASS 2026-11-02 19:0x；P1 0／P2 0／P3 0／P4 2）
**上位**: 根層 `docs/01_requirements/ResearchToPRD_PRD.md`（FR-R2P／AC-R2P）、`docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`（D1～D7）
**建立**: 2026-11-02（RTM_VERIFY 態；TCS §6「RTM 與報告落點」、SCG-4 一審 F-08）
**規約**: 每完成一項需求回填四格（實作檔／自動測試／E2E 驗證／狀態）；不刪列、不改號、不合併列。「自動測試」欄的 rc 皆取自 SCG-4 二審 QA 鏡（Sonnet，唯讀）的 driver 行程輸出（`RESULT <AT> PASS`，driver rc 0），AT-970-4-4 取自一審；主控收尾重跑的結果併記於各列，逐字輸出貼於 SCG-4 報告〈二審後附記〉。

## 1. AC → AT 追溯（35 列）

| 需求 | AT | 實作檔（框架側） | 自動測試 | E2E 驗證 | 狀態 |
|------|----|------------------|----------|----------|------|
| AC-970-1 九個新增檔齊備與格式 | AT-970-1-1 | `workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`、`agent/specialized/research-analyst-zh.yaml`、`agent/specialized/spec-engineer-zh.yaml`、`docs_template/sdd/requirements/{ISSUE-SCOPE,EVIDENCE-MATRIX,PRD-SPEC-ENGINEERED,ADVERSARIAL-REVIEW-CARD}-TEMPLATE.md`、`docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`、本 TCS | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-1 | AT-970-1-2 | 兩支 specialized agent YAML | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-1 | AT-970-1-3 | 九個新增檔＋十二個被改檔（UTF-8／無 BOM／LF／檔尾換行） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-1 | AT-970-1-E-1 | `workflow/sdd-research-to-prd/`（只一檔）；舊名 ADR 與框架側 PRD 不存在 | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-2 註冊與計數 | AT-970-2-1 | `AISDLC_SDD_INIT.md`（四處）、`workflow/README.md`、`agent/README.md`、`agent/specialized/README.md`、`docs_template/README.md`、`guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md`、`AISDLC_SDD/CLAUDE.md`（三處）、`releases/CHANGELOG.md`、`EVOLUTION_LOG.md`、`AISDLC_SDD/scripts/framework_status_snapshot.py`（組成字串） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-2 | AT-970-2-2 | `AISDLC_SDD/FRAMEWORK_STATUS.md`（`framework_status_snapshot.py --check`） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-2 | AT-970-2-E-1 | 同上（暫存迷你樹負控） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-3 JSON 契約自洽 | AT-970-3-1 | 四份模板內 9 個 `<!-- r2p:contract=… -->` 區塊；檢核器＝TCS 附錄 A `r2p_contract_check.py` | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-3 | AT-970-3-2 | 檢核器自證（29 個注入錯誤、1 個合法變體） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-3 | AT-970-3-E-1 | 契約模板暫存複本（缺標記負控） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-4 框架治理閘不退步 | AT-970-4-1 | 四支 agent 的 lint（既有工具 `tools/agent_template_lint.py`，零改動） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-4 | AT-970-4-2 | `arch_fitness`（既有，零改動） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-4 | AT-970-4-3 | skills 鏡像與版本戳記 `--check`（既有，零改動） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-4 | AT-970-4-4 | `AISDLC_SDD/scripts/ci-gate.ps1`（本機 CI 閘門） | 一審實跑 PASS（rc 0）；二審沿用（唯讀鏡不重跑：ci-gate 會改寫被忽略的快取檔）；主控收尾重跑 rc 0（AISDLC_SDD_v0.01:1478、AISDLC_SDD_v0.30:2250、scripts/tests:425） | ci-gate.ps1＝本鍵的 E2E；雲端 `aisdlc-sdd-ci` 於 commit 後現查 | ✅ |
| AC-970-4 | AT-970-4-E-1 | 暫存版本樹 `v0.99`（鬼影模板路徑負控） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-5 變更邊界與追溯 | AT-970-5-1 | 變更集合：24 條白名單＋`docs/06_quality/`＋D-46 根層例外 8 條（`git diff` 對起點 `01d9be6e`） | 二審實跑 PASS（rc 0；violations=0、whitelist 24、root exempt 8、changed paths 102）；主控於 RTM／報告落檔後重跑 PASS violations=0（changed paths 104） | — | ✅ |
| AC-970-5 | AT-970-5-2 | 受保護路徑（`tools/`、`.claude/`、`governance/`、`formal/`）零差異 | 二審實跑 PASS（rc 0；protected paths changed=0）；主控收尾重跑 PASS | — | ✅ |
| AC-970-5 | AT-970-5-3 | 〈增量追溯表〉U1～U5 ＝ FSM 凍結記錄聯集（`FSM-STATE-sdd-research-to-prd.yaml`，不入庫；唯讀 `show`） | 二審實跑 PASS（rc 0；table_rows=5、6 鍵 SAME、drift 0）；主控於勘誤 10 refreeze 後重跑 PASS table_rows=5 | — | ✅ |
| AC-970-5 | AT-970-5-E-1 | 邊界函式（合成越界路徑負控，含近似檔名 `….md.bak`） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-6 文件內容對齊 | AT-970-6-1 | 工作流（章節 0～14）、ADR-001（D1～D7）、SE-PRD 模板（P0-7 逐處計數）、缺陷狀態轉移矩陣 | 二審實跑 PASS（rc 0；chapters=0…14） | — | ✅ |
| AC-970-6 | AT-970-6-2 | 工作流 Gate 0 四文件、BRIDGE §9.2 動詞列與四個閘、人工退回守則三處 | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-6 | AT-970-6-3 | `PRD-SPEC-ENGINEERED-TEMPLATE.md`（14 章、六錨點、附錄 R） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-6 | AT-970-6-4 | 九個新增檔（無占位字樣／雙大括號） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-6 | AT-970-6-5 | 九個新增檔的上位編號 ↔ 根層 PRD | 二審實跑 PASS（rc 0；absent in PRD: 0） | — | ✅ |
| AC-970-6 | AT-970-6-6 | 工作流、審查卡模板（`review_params`）、ADR-001 D7、BRIDGE §9.2、證據矩陣模板、引擎 `tools/fsm_runtime/transition_rules.py`（`RETRY_LIMITS`，讀） | 二審實跑 PASS（rc 0；八項）；勘誤 10 加第九項「最多 N 輪」六處（二審 N-1）：主控於 RELEASE_READY 態實跑九行 PASS、六個 3→4 突變皆 FAIL、對照句控制組 PASS（SCG-4 報告〈二審後附記〉） | — | ✅ |
| AC-970-6 | AT-970-6-E-1 | SE-PRD 結構函式（四種變異負控） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-7 FSM 演練 | AT-970-7-1 | `tools/fsm_runtime/{fsm_runtime,state_loader,transition_rules}.py`（既有引擎，零改動）；演練在 `$tmp/AISDLC_SDD` 複本與 `$tmp/fsm` | 二審實跑 PASS（rc 0） | 🔶 真引擎演練（複本） | ✅ |
| AC-970-7 | AT-970-7-2 | 同上 | 二審實跑 PASS（rc 0） | 🔶 | ✅ |
| AC-970-7 | AT-970-7-3 | 同上 | 二審實跑 PASS（rc 0） | 🔶 | ✅ |
| AC-970-7 | AT-970-7-4 | 同上 | 二審實跑 PASS（rc 0） | 🔶 | ✅ |
| AC-970-7 | AT-970-7-5 | `fsm_runtime._is_blocked_spec_write`（讀；`-B` 不寫位元組碼） | 二審實跑 PASS（rc 0） | — | ✅ |
| AC-970-7 | AT-970-7-6 | 同 7-1 | 二審實跑 PASS（rc 0） | 🔶 | ✅ |
| AC-970-7 | AT-970-7-E-1 | 同 7-1（自動恢復預設開啟負控；複本內留 `build/reports/abort/` 產物，真 repo 零寫入） | 二審實跑 PASS（rc 0） | 🔶 | ✅ |
| AC-970-7 | AT-970-7-E-2 | 同 7-1（D-50 負控） | 二審實跑 PASS（rc 0） | 🔶 | ✅ |
| AC-970-7 | AT-970-7-E-3 | 同 7-1（D-50 負控） | 二審實跑 PASS（rc 0） | 🔶 | ✅ |

**覆蓋**: 7 AC → 35 AT，100% 映射；35／35 PASS（34 二審實跑＋4-4 一審）；FAIL 0、NOT-EVALUABLE 0。

## 2. V 系列（自動測試之外；不在 SCG-4 通過標準內）

| 編號 | 驗證者 | 本輪狀態 | 說明 |
|------|--------|----------|------|
| V1 | 主控或 QA | 未執行 | 需在框架鍵的 hooks-ON 視窗做 BRIDGE §8.2 (a)(c) 開場三步；本輪主控視窗 hooks-OFF（`SDD_ACTIVE_VERSION` 未設，須於 claude 啟動前設定），改列為本鍵 RELEASE 後第一個 hooks-ON dogfood 視窗的開場動作（BRIDGE §8.2 本來就要求每個 hooks-ON 視窗做這三步，不另立項） |
| V2 | 人 | 未執行 | 人手流程（工作流第 13 章步驟 1～2 建玩具研究工作區）；Console P0 的 Bridge 端 `research` 套件以同一流程為 oracle（PKG-BR-A／BR-B 的 FSM 動詞測試），機械面由那裡覆蓋 |
| V3 | 人 | 未執行 | 以 SE-PRD 模板填玩具 PRD、逐條核對 P0-1～P0-9；AT-970-6-1／6-3 已機械核對模板結構與預檢代碼，條文無歧義的人讀判斷留給第一次真實使用 |
| V4 | Console 側 | P0 實作期 | `AgentConsole/engine-bridge/tests/test_research_schema_parity.py`（PKG-BR 系列）以 `<!-- r2p:contract=… -->` 標記對拍 Bridge schema；以 Console 側 SCG-4 報告為準 |

## 3. 上位需求對照

| 上位 | 本鍵 AC | 備註 |
|------|---------|------|
| FR-R2P-01～10、18、21；AC-R2P-07～12 | AC-970-1～7 | 逐條對照見 TCS〈上位需求對照〉；AT-970-6-5 機械核對編號存在於根層 PRD（`absent in PRD: 0`） |
| NFR-R2P-08（文件最小集與回填） | AC-970-5 | 變更邊界直接依據＝PRD §9.0 落點表與 ADR-XPLAT-017 §D7（勘誤 7） |
