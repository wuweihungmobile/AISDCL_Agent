# ADR-001: Research-to-PRD 框架層——方法層納入 AISDLC_SDD，執行層留在 Console／Bridge

**日期**: 2026-11-02
**狀態**: Accepted
**決策者**: 主控（Fable 5.1；掌舵者授權代決，裁決 D-21、D-38）＋ 掌舵者（立案；可隨時以明示指令推翻）
**立案**: 掌舵者 2026-11-02 ResearchSOPtoPRD；主控裁決 D-21
**FSM 功能鍵**: `sdd-research-to-prd`（`sub=sdd`；狀態目錄 `AISDLC_SDD/AISDLC_SDD_v<LATEST>/build/reports/sdd-dogfood`，`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.1 節）
**上位需求（唯一 PRD）**: 根層 `docs/01_requirements/ResearchToPRD_PRD.md`（FR-R2P-01～23、NFR-R2P-01～13；本 ADR 即其 §9.5 列「框架 ADR-001」，兩側並列見其 §11.2）。**框架側沒有自己的 PRD**：本框架鍵的 FRD-lite 併入測試契約檔頭（`docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md`），避免兩份 PRD 各說各話。

---

## 情境（Context）

掌舵者貼入的 ResearchSOPtoPRD 規格要求一條「研究 → 證據矩陣 → PRD → 四方對抗審查 → 人工核准（Gate 0）→ 分流 → 實作」的流程，並問是否納入 AISDLC_SDD 流程。事實：

- 流程的前半（研究、證據、PRD、審查、核准）與 SDD 的 SCG-0 重疊：SCG-0 本來就要求 PRD 與 FRD 完成、US 有 Given/When/Then、追溯鏈完整、SLV 前置驗證與 Ambiguity Gate（`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈閘門通過標準〉）。
- agent 人設與閘門語意的唯一真相源在框架（`AutoClaude/CLAUDE.md` 的人設單一來源規定）；若在 Console 內另寫一份，就是第二個家。
- 但抓取第三方內容需要 Bridge 的外呼 allowlist 與 SSRF 防線（PRD NFR-R2P-03），入庫需要 Bridge 的連線池與 fail-loud 寫入器（PRD FR-R2P-02）；框架的 Python 是 FSM 治理 runtime（`tools/fsm_runtime/`），不是網路客戶端或資料庫寫入器。
- FSM 已能表達整條外環，**不需要新增狀態或邊**（`workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md` 第 2.7 節逐邊證明）；但外環鍵與內環鍵的狀態目錄不同，必須是兩把鍵（Bridge 側的寫入面與動詞白名單另見 `docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`，本 ADR 只決定框架層）。
- 架構分析、FSM 對映與 JSON 契約草稿由 Architect 交卷，主控親驗 `transition_rules.py:12-35,267-275,305-326` 後裁決。

## 決策（Decision）

本 ADR 共七項決策，編號 D1～D7 固定（上位 PRD §9.5 逐字引用同一組編號）；每項附上位需求座標，使「為什麼這樣設計」可回溯到 PRD 的 FR／AC。

**D1　新增一個 workflow，不新增 scenario。** `workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md` 是方法的單一真相源；Stage-0 是**任何**場景的可選前置，不是第 11 種專案類型。Greenfield 與 Brownfield 的 enhancement 文件各加一段指標。
上位需求：FR-R2P-01（單一流程脊；AC-R2P-01-1）、PRD §11.2 整合點 #23（框架演進路徑）、裁決 D-21。

**D2　新增兩支 agent，審查沿用既有四支。** `research-analyst`（證據端）與 `spec-engineer`（規格端）住 `agent/specialized/`；審查＝`05.sd-architect`（架構）、`03.pm-po`（產品；檔名 `03.pm-po-agent-zh.yaml`，`agent.id` 為 `pm-po`）、`07.qa-tester`（QA）、`security-engineer`（資安；授權欄由 `compliance-officer` 輔）。起草者與審查者分離（`SDD_AUTOCLAUDE_BRIDGE.md` 第 6.4 節 C-3 補償控制）。兩支新 agent 的 YAML 以 `evidence_discipline.inherits_from` 指向 `agent/EVIDENCE_DISCIPLINE.md`。
上位需求：FR-R2P-07（`spec-engineer` 起草；AC-R2P-07-1）、FR-R2P-08（審查者與起草者分離；AC-R2P-08-4）、FR-R2P-04（每角色 persona 以 by-reference 載入並記雜湊；AC-R2P-04-9）、裁決 D-05。

**D3　不新增 `governance/rules/R-*.yaml`、不新增 skills，不碰 FSM runtime、CLI、`_HAPPY_PATH`、`formal/`。** 重試上限＝R-9.1、人工閘＝R-9.5 與 Rule 8、凍結＝R-9.4、審查獨立性＝`SDD_AUTOCLAUDE_BRIDGE.md` 第 6.4 節補償控制；本功能沒有新的「違反即停機」絕對禁令，也不新增 hook 或守衛碼。
上位需求：FR-R2P-08（憲法對照：絕對禁令 4、6）、NFR-R2P-05-4（不新增 hook、守衛碼或根層守衛面）、PRD §9.0 約束 D-01（不動 `_HAPPY_PATH` 與 `formal/`）。

**D4　新增四份模板，不改 `PRD_Universal_Template.md`。** `ISSUE-SCOPE`（議題與檢索邊界契約）、`EVIDENCE-MATRIX`（證據項契約與矩陣版式）、`PRD-SPEC-ENGINEERED`（SE-PRD）、`ADVERSARIAL-REVIEW-CARD`（評分卡）。SE-PRD 的骨架＝**家規 `PRD_Universal_Template` 的 14 章章號與標題在頂層**，來源規格的六個區塊以 `<!-- r2p:section=N -->` 錨點嵌入對應章節，**章尾附「來源六節 ↔ 家規章節」對映表**（裁決 D-20 SA-01；PRD C.6 SD-13），使「來源六節不得省略」與「家規必讀章非空」兩套檢查（雙重預檢）能對同一份文件機械驗證。SE-PRD 的 US 與 AC 使用 Rule 7 數字制 ID，兼具 FRD-lite，使 SCG-0 的「PRD 加 FRD」成立而不重複造檔。欄位值域一律與 PRD §5.1 一致：`topic` 1～500 字；`slug` 為 `^[a-z0-9][a-z0-9-]{0,29}$`；`depth_level` 為 `QUICK／STANDARD／DEEP`；`layers` 為 `academic／industry／oss／community` 四個布林。
上位需求：FR-R2P-03（議題輸入；AC-R2P-03-1、03-2）、FR-R2P-05（證據矩陣格式；AC-R2P-05-1、05-7）、FR-R2P-07（PRD 草擬與雙重預檢；AC-R2P-07-2）、FR-R2P-08（評分卡；AC-R2P-08-1）、PRD §5.1.2～§5.1.4、裁決 D-20。

**D5　Stage 與鍵命名；Gate 0 永遠要求真人核准，凍結文件集不含 TCS。**
- **兩把鍵**：外環鍵 `research-<slug>`（換世代為 `research-<slug>-g<N>`；狀態目錄＝研究工作區的 `build/reports/fsm`，`SDD_AUTOCLAUDE_BRIDGE.md` 第 8.0 節加 `research` 前綴）；內環鍵 `<sub>-<slug>`（分流後建於目標專案標準狀態目錄，Stage-1 採納已發佈的 PRD，理由寫「SCG 已在外環鍵通過」）。
- **Stage 名**：`Gate-0`、`Gate-0-SCR<n>`（外環）；`Stage-1`、`Stage-2`（內環）；`--stage` 值域 `^[A-Za-z0-9._-]{1,64}$`。
- **Gate 0**：`spec-frozen --stage Gate-0` 的 `--doc` 恰為四份——`01_specs/PRD-v1.0.0.md`、`00_research/evidence_matrix.md`、`00_research/issue_scope.json`、`01_specs/adr_draft.md`，**不含 TCS**（TCS 是分流後內環 Stage-2 的文件）；`--approver` 必須是真人。根 `CLAUDE.md` 的「凍結常態規則」只適用於開發本 repo 自身，不適用於產品執行期（裁決 D-19）。TCS 要求在 Bridge 的 `:freeze` 端點，不在 FSM CLI，所以 Gate 0 由專用端點承載、`:freeze` 契約不改（裁決 D-23）。
- **SCR 三路**（不改 `_HAPPY_PATH`；ADR-XPLAT-017 §D5）：小型（MINOR）＝外環鍵 SPEC_FROZEN→SPEC_DRAFTING 重走 Stage `Gate-0-SCR<n>`，再由內環鍵 SPEC_AUDIT 加 `spec-refreeze`；大型（MAJOR）＝新研究專案；自癒耗盡＝人手 `resume-from-escalation`。
- **Bridge 可用的 FSM 動詞**：`show`（唯一建檔點）、`transition`（受限邊集合）、`gate`（四個閘：`SCG_VALIDATION`、`PR_REVIEW`、`RTM_VERIFY`、`RELEASE_READY`）、`spec-refreeze`、`spec-frozen`；**不含** `resume-from-escalation`（只有人，R-9.5、絕對禁令 6）。
上位需求：FR-R2P-10（Gate 0；AC-R2P-10-1、10-8、10-9）、FR-R2P-19（SCR；AC-R2P-19-1～8）、FR-R2P-03（外環鍵於初始化時建立；AC-R2P-03-1）、PRD §5.1.1、裁決 D-19、D-22、D-23。

**D6　框架不含網路或資料庫程式；機器 schema 住 Bridge。** 框架文件放契約欄位定義與有效範例（每個 JSON 區塊前有 `<!-- r2p:contract=<名稱> -->` 定位標記），Bridge 以契約對拍測試鎖欄位名與範例（`tests/test_research_schema_parity.py`）；先例＝Bridge 自帶 `DENY_CHARS` 並以 parity 測試鎖。第三方抓取、allowlist、SSRF 防線、入庫與評分聚合全在 Bridge。
上位需求：NFR-R2P-03（外呼安全與內容隔離）、FR-R2P-04（抓取走 Bridge 獨立 allowlist；AC-R2P-04-2、04-8）、FR-R2P-02（寫入者唯一為 Bridge；AC-R2P-02-10）、PRD §9.1 元件 C14～C17。

**D7　評分卡是 SCG-0 的評估器，不取代 SLV 與 Ambiguity Gate；審查預算採 FSM 預算。**
- **評估器定位**：前置否決（SLV-001～003、Ambiguity <0.4 或有豁免、SE-PRD 結構、`E-NNN` 引用）任一不過＝本輪 `gate FAIL`、不計分；通過後四角加權（ARCHITECTURE 30／PRODUCT 25／QA 25／SECURITY 20）≥85，**且**每維度不低於地板 60，**且**無未結 P1 缺陷（裁決 D-14）。QA 角必填 `slv_manual_check`，補增量或非標準寫法下機械半段空轉的洞。權重、門檻、地板是產品常數。嚴重度 P1～P4 與缺陷 id `D-<輪>-<序>` 的定義以評分卡模板為單一真相源（PRD §5.1.4 引用之）。
- **預算語意**：審查最多 3 輪（首審加 2 次自動修訂；第 3 次 `gate SCG_VALIDATION FAIL` 即 ESCALATION，裁決 D-24），不改 `RETRY_LIMITS`、不用裸 `transition` 繞計數；人工「要求修改」走 `gate SCG_VALIDATION FAIL`（共用同一預算，裁決 D-25；現態 HUMAN_PENDING 時 Bridge 不呼叫 `gate PASS`、再審通過只記資料庫，因為 HUMAN_PENDING → HUMAN_PENDING 不是合法邊，裁決 D-50）；外環鍵的 CLI 環境固定 `SDD_ENABLE_AUTO_RECOVERY=0`（裁決 D-26）；ESCALATION 的恢復只有人（Rule 9.5），且人工恢復後預算不歸零：至多再得一次審查，FAIL 立即再 ESCALATION、PASS 歸零，全新預算＝換世代鍵（裁決 D-60；工作流第 2.5 節）。
上位需求：FR-R2P-08（四方審查與迭代；AC-R2P-08-1、08-2、08-3、08-5、08-7、08-8、08-9、08-10）、FR-R2P-09（核准鈕的解鎖條件；AC-R2P-09-5）、NFR-R2P-02（有界停機與研究預算）、PRD §5.1.4、裁決 D-14、D-24～D-26。

## 理由（Rationale）

1. **人設與閘門語意只有一個家**：兩支新 agent 與四份模板住框架，Console 以 by-reference 載入並記雜湊；審查卡的 `agent_yaml_sha256` 與 `persona_sha256` 使「這輪審查用的是哪一版人設」可稽核。
2. **沿用既有閘門而不是另造評分語意**：把評分卡定位成 SCG-0 的評估器，避免出現「分數高但 AC 不可測」被放行的洞；前置否決先行、分數不能覆蓋它。
3. **零新邊零新狀態**：全部轉態都是 `transition_rules.py` 既有邊（逐邊證明見工作流第 2.7 節），因此免跑 TLA+/TLC（`_HAPPY_PATH` 不變，與 ADR-XPLAT-016 §11.3 同前提）。
4. **有界停機涵蓋人工退回**：人工退回走 `gate FAIL` 而不是第 8.6 節的 SPEC_REGRESSION_CHECK 退回法（後者不計預算），使整條外環受 R-9.1 約束。
5. **骨架以家規為頂層**：兩套檢查（來源六節、家規必讀章）共用同一份文件，不必維護兩份骨架；對映表放章尾，交付後仍留在 PRD 內，後續 Stage-2 TCS 草擬者可直接取用。
6. **最小侵入**：框架側改動全是 Markdown 與 YAML 加幾張註冊表與一次 `FRAMEWORK_STATUS.md` 重生；沒有 Python、沒有規則、沒有 hook。
7. **排除替代方案的理由**：見下表。

## 後果（Consequences）

- **正面影響**：研究到規格的方法可脫離 Console 用人手流程執行（工作流第 13 章）；方法與執行分離，各自可演進；SCG-0 的人工確認點有了明確的外環載體與 stage 名。
- **負面影響**：兩個視窗要協調（框架窗先、Console 窗後；框架鍵與 Console 鍵各自一個 hooks-ON 視窗）；Bridge 必須擴充 FSM 動詞白名單（`show` 建檔專用、`transition`、`gate`、`spec-refreeze`），並新增 Gate 0 專用端點（ADR-XPLAT-017）；`transition` 與 `gate` 是舊 CLI 契約（非單行 JSON），需預檢加事後驗證。
- **技術債務（誠實記載）**：審查獨立性不滿足 R-9.20.3 型要求（同一 AI、同工作區可互讀），以分 run、`maintain_context:false`、聚合由程式、Gate 0 由人補償；無執行層的人手流程沒有機器驗證器；`sdd_env.py` 不認研究鍵（三件組手設）；框架內沒有 HUMAN_PENDING 逾時守門的產品路徑實作（逾時只由 hooks 的 SessionStart 執行，Console 路徑沒有 hooks；裁決 D-48(3)：Console 路徑以 UI 顯示等待時長＋72h 橫幅、不轉 REMINDER，不新增 hook 或守衛）；軌道 B（全新專案）的內環走完整 SCG-1～3、不適用增量條款（裁決 D-48(2)）。
- **後續行動**：框架側 `FRAMEWORK_STATUS.md` 重生（Agents +2、`docs_template/sdd` 模板 +4、Workflows +1；絕對數字以重生結果為準，本檔不複寫）；`SDD_AUTOCLAUDE_BRIDGE.md` 新增第 9 節；`AISDLC_SDD/CLAUDE.md` 補 Rule 2 目錄樹一句、〈框架核心文件快速參考〉一列與 Rule 6 兩列；`docs_template/README.md`、`agent/README.md`、`PROJECT_DOCUMENTATION_STANDARDS.md` 的計數與清單同步，`scripts/framework_status_snapshot.py` 的組成字串補 `+1 Research-to-PRD`（裁決 D-47）；Console 側見 `AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md` 與 `docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`。
- **再開症狀**（症狀驅動，沒有日曆或次數門檻）：

| 決策 | 再開症狀 |
|------|----------|
| D1 | 出現兩個以上場景需要互不相容的研究流程 |
| D2 | 審查評分在盲測對照中顯著偏離人類審查（處置是校準，不是加 agent） |
| D3 | QA 或 SCG-4 發現某種「研究造假」缺陷在既有規則下沒有任何機械攔截且反覆出現 |
| D4 | SCG-0 的 SLV 機械半段對 SE-PRD 的表格形 AC 空轉，放行過有缺陷的 AC 一次；或家規 `PRD_Universal_Template` 的章號改動使章尾對映表失真 |
| D5 | 人手流程被使用兩次以上且三件組設錯一次（處置：擴 `sdd_env.py` 的 `SUBS`）；掌舵者要求產品內 Gate 0 可由規則自動核准（需修憲：Rule 8 與 R-9.5） |
| D6 | 框架使用者要求「不經 Console 也能機驗評分卡」（處置：抽出純標準庫的 `tools/research_gate/`，不改本 ADR 其他決定） |
| D7 | 委員會通過的 PRD 在 SCG-1～3 或 SCG-4 被判 FAIL 的比例顯著偏高（處置：校準門檻與地板，不改前置否決）；Bridge 對 `transition` 的錯誤判讀出現一次誤判（處置：給 FSM CLI 加 `--json`）；掌舵者要求在 Console 內恢復 ESCALATION（需修憲：Rule 9 絕對禁令 #6）或要求第 4 輪審查（須先改 `RETRY_LIMITS` 與 TLA+） |

## 替代方案評估（Alternatives Considered）

| 方案 | 優點 | 缺點 | 排除原因 |
|------|------|------|----------|
| A 純 Console 功能（方法全在 Bridge 內） | 框架零改動 | Bridge 內另寫 prompt 與評分語意＝第二個家；方法被 Console 私有化，無法在 SDD session 人手跑 | 違反人設單一真相源；之後想抽出得重寫 |
| B 框架承載全部（含抓取與編排 Python） | 方法與執行同處 | 框架 Python 是 FSM 治理 runtime，不是網路客戶端；抓取需要 Bridge 的 allowlist、SSRF 防線與連線池；框架沒有資料庫與 UI | 抓取與入庫屬 Bridge；放進框架會動 runtime 與擴大 TLC 風險面（D6） |
| C 方法層進框架、執行層留 Console（採用） | 見理由 1～6 | 兩個視窗協調；Bridge 白名單擴充 | — |
| 新 scenario `research-to-prd` | 與場景機制一致 | 影響 `SCENARIO_DETECT`、TCS 場景宣告、`auto_load_config` 與 FRAMEWORK_STATUS 的場景數；研究到規格是任何場景的前置而不是第 11 種專案 | D1 |
| 新增四支專屬審查 agent | 審查者專屬 | 與既有 sd-architect、pm-po、qa-tester、security-engineer 重疊，人設多家 | D2 |
| 單一 agent 兼起草與審查 | agent 數少 | 破壞起草者與審查者分離（C-3 補償控制） | D2 |
| 新增 `R-*.yaml` 規則 | 機械強制 | 要動 `RULES_INDEX`、maturity 與 CLAUDE.md 禁令表，且沒有暴露證據 | D3 |
| 六章為頂層的 SE-PRD（Architect 草稿原案） | 與來源六節一一對應 | 家規必讀章（目標用戶、商業需求、UX、時程、風險）沒有位置，雙重預檢之一落空；與家規模板不同構 | D4（裁決 D-20 SA-01） |
| 把 JSON Schema 與聚合器放框架 `tools/` | 不經 Console 也能驗 | 框架 Python 不是網路或資料庫客戶端；先例是 Bridge 自帶並以 parity 測試鎖 | D6（列為再開選項） |
| 在 `:freeze` 內放寬 TCS 規則 | 不增端點 | 改一個已凍結契約與既有兩個 AT | D5 |
| 給 `transition` 與 `gate` 加 FSM CLI 的 `--json` | 契約更乾淨 | 要改 LATEST 的 CLI 與測試 | D7（最小侵入，列為再開選項） |
| 單鍵（外環內環同一把鍵） | 少一把鍵 | 單鍵必須讓狀態目錄＝研究工作區，但軌道 A 的 TCS 與 adapter 向上找狀態目錄的規則要求沿用目標專案目錄，兩者互斥 | D5 |

## 相關文件

- 上位需求：`docs/01_requirements/ResearchToPRD_PRD.md`（根層，唯一 PRD；FR-R2P-01～23、NFR-R2P-01～13；§9.5、§11.2）
- 工作流：`workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`；Bridge 路徑：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` 第 9 節
- 模板：`docs_template/sdd/requirements/ISSUE-SCOPE-TEMPLATE.md`、`EVIDENCE-MATRIX-TEMPLATE.md`、`PRD-SPEC-ENGINEERED-TEMPLATE.md`、`ADVERSARIAL-REVIEW-CARD-TEMPLATE.md`
- Agent：`agent/specialized/research-analyst-zh.yaml`、`agent/specialized/spec-engineer-zh.yaml`
- 測試契約：`docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md`
- 關聯 ADR：`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`（Bridge 寫入面、動詞白名單、框架側白名單 §D7）、`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`（§3.5 動詞白名單、§11 框架側白名單）、`AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md`（Console 側載體與持久化）
- 關聯 US／F／EPIC：根層 PRD 的 FR-R2P／US-R2P 全系列；本框架鍵的 F-970／US-970（TCS 檔頭 FRD-lite）

---

**觸發 Skill**: `generate_adr`
**存放位置**: `docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md`（相對 SDD 版本目錄；專案層文件）
