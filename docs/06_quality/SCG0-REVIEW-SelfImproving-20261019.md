# SCG-0 零信任獨立審查報告 — SelfImproving（自我進化機制）PRD

| 項目 | 內容 |
|---|---|
| 受審物 | `docs/01_requirements/SelfImproving_PRD.md`（954 行／175,851 bytes）、`docs/05_development/SelfImproving_Research_Methodology_SOP.md`（345 行／94,071 bytes）、`docs/06_quality/SelfImproving_Observation_Ledger.md`（43 行／14,240 bytes；34 列） |
| 輸入快照 | HEAD＝`6c23495d`（`git -C D:\CursorProject\AISDCL_Agent rev-parse --short HEAD` → `HEAD=6c23495d rc=0`）；`git status --short` → `status-lines=0`（工作樹乾淨 ⇒ 工作樹檔案＝HEAD 版本，審查以 Read 讀工作樹；審查結束前複驗 HEAD 與工作樹未變，見 §4） |
| 審查者 | QA（Sonnet 5.5；未參與 SOP／PRD／帳本撰寫；唯讀，不改受審物，不做 git 寫入，不派子代理，不跑 FSM CLI，不用 Bash） |
| 二審輸入快照 | HEAD＝`978df84c`（`git -C D:\CursorProject\AISDCL_Agent rev-parse --short HEAD` → `HEAD=978df84c rc=0`；`git status --short` → `status lines=0`，09:22 +08:00 重查）；修復批次 `31824e56`（SOP）、`a52ee13e`（SA 非 §9）、`978df84c`（SD §9＋主控同步＋帳本）、`c0716f16`（一審報告＋帳本更正）；詳 §6.0 |
| 日期 | 2026-10-19（本機 +08:00；一審約 04:33～05:15；二審 06:18 起，06:18:41 因週額度 429 中斷、09:21 續跑，完成時刻見 §6.6） |
| 判定 | **一審 FAIL → 二審 PASS**（一審 HEAD `6c23495d`：P1＝0、P2＝3、P3＝18、P4＝7；二審 HEAD `978df84c`：P1＝0、P2＝0，另新增 P3＝7、P4＝6；判定口徑＝無 P≤2 才 PASS）。§1～§5＝一審原文（不改）、§6＝二審 |

## 0. 一頁摘要

- 這份 PRD 的**引用品質很高**：我抽開 6 個外部來源頁面（S-11、S-17、S-08、S-23、S-25，加 V1 的 S-04；詳 §1.3）、對 §11／§9.0 的 40 餘個 repo 座標逐條對行號，**零筆不存在、零筆失真**（P1＝0）。SD 的 Q7 普查數字我重跑全部吻合。
- 結構性問題集中在三處（各是 P2，必須在凍結前修）：**F-01** 不可進化面的「機械邊界」只比單一 `target`、不比 patch 觸及的全部路徑；**F-02** 成功指標 M1 與 §1.1 反證條件在 PRD 自己普查出的基率（再現事件約 1／1,490 列）下沒有鑑別力，NOT-EVALUABLE 護欄量錯對象；**F-03** P0 的欄位遷移（AC-SI-01-3）與原地改寫偵測（AC-SI-04-3）互相矛盾，P0 出口 (b)「`check` 綠」依文字不可達。
- 另有 18 筆 P3（多為文字／座標／計數過期／灰區明文化）與 7 筆 P4（理論洞，登記不修）。SOP 本身結構完整（八步各有輸入／輸出／判準、S7 全為症狀驅動、有三桶誠實劃界、來源表標查證方式）。

## 1. 判準逐項結果

### 1.1 模板完整性（對照 `AISDLC_SDD/AISDLC_SDD_v0.30/docs_template/core/prd/PRD_Universal_Template.md`）— PASS（附 P3／P4）

- 章節：模板 `## 1.`～`## 14.` 與〈文檔完成檢查清單〉在 PRD 全數存在（兩檔 `^#{1,3} ` 標題清單逐一對照）；元數據 10 欄（專案名稱／類型／目標平台／目標日期／狀態／PO／Stakeholders／撰寫日期／最後更新／AISDLC 版本）與 Brownfield 專屬 5 欄（既有系統名稱／現行版本／目標版本／系統文檔位置／技術棧）齊全，其餘平台專屬區塊標「不適用」並寫理由（PRD:7、:16、:25–32）。
- 與模板的有理由差異（均不扣分）：模板 §8.2 Sprint 規劃（Sprint 情境專屬，Brownfield 不需）；§9 本為 Greenfield 專屬，PRD 由 SD 填成「元件／資料模型／介面／安全／ADR」；§11.2 影響分析在 PRD 為 §11.3（另加 §11.2 缺口表）；§12.1／§12.3 合併成 §12.2；§5.1 的 Kano／RICE／Epic 欄未採（以〈追溯〉〈憲法對照〉取代）→ P4。
- 佔位字樣掃描（`TODO|TBD|FIXME|XXX|待補|待定|佔位|placeholder|之後再看|下輪候選|待排程|[專案名稱]|[…]|YYYY-MM-DD`）：PRD 命中 7 筆（行 106、198、230、355、466、479、672）、SOP 1 筆（行 128）、帳本 1 筆（行 6），**逐筆看前後文皆是「禁止出現『之後再看』／『待排程』」的規則敘述，不是佔位**；無 `[…]`／`TODO`。
- 〈檢核表〉：PRD 品質 8 項＋流程 5 項＋本稿特有 5 項皆在；未勾項（所有 🔴 確認點、與 Stakeholders 評審、PM／BA Agent 項）都附理由且指向 QA／掌舵者（PRD:930–946），誠實。

### 1.2 ID 與可測性 — PASS（附 P3）

指令（PowerShell 腳本，逐行解析 PRD；輸出節錄，省略處以「…」標示，其餘逐字）：

```
PRD bytes=175851 lines=954 CR=0
FR defs=29 unique=29
AC defs=76 unique=76
US defs=8 NFR defs=9
FR without AC: 
FR range: 1-29
referenced AC ids=76; referenced-but-undefined: 
referenced FR ids=29; referenced-but-undefined: 
DP refs: DP-01,DP-02,DP-03,DP-04,DP-05,DP-06,DP-07,DP-08,DP-09,DP-10,DP-11,DP-12
S refs: S-01,S-02,…,S-30（30 個皆在來源表）
ADR refs: ADR-SI-01…ADR-SI-09；US refs: US-SI-01…US-SI-08
```

- 編號唯一、格式一致、無懸空引用；每條 FR 至少 1 條 Given／When／Then 的 AC（FR 1～29 皆有，AC 共 76，與 §9.7 的「72→76」相符）。
- 可測性：依 G／W／T 形態判讀（**未逐條實作驗證**，與 §9.7 自述同口徑）。多數 AC 指向可觀測事實（指令 rc、欄位值、digest、`git status`／HEAD 對照、事件帳本折疊結果）。無法單靠文字判定者：AC-SI-17-2（F-08）；AC-SI-10-2「零遞迴」與 §2.1.1 多處「不能做」未標邊界型（F-09）；AC-SI-12-4 的引言比對錨定未定義（F-07）。流程型 AC 已多數自標（AC-SI-08-1、18-1、20-1、22-3）。
- 格式：ID 前綴 `FR-SI`／`AC-SI-NN-Y`（NN＝FR 號）與 `AISDLC_ID_Naming_Convention.md`:30–36（`F-XXX`；`AC-XXX-Y` 的 XXX＝US 號）不同；PRD:177 以 repo 先例辯護，我驗得先例存在（`Agent_ConsoleUI_PRD.md` 行 95／108／1556 有 `FR-SEC-03`；PRD v2.1 行 23／2702 有 `F-SBR-001`）→ P4（F-27）。

### 1.3 追溯鏈與 URL 抽查 — PASS（P1＝0）

**FR→DP**：29 條 FR 的〈追溯〉行（PRD §5.2）所列 DP-01～12 全部存在於 SOP II-5；附錄 A（PRD:866–879）的 FR-SI 欄與各 FR 追溯行**雙向一致**（我逐 DP 比對 12 列，無缺漏）。FR-SI-03／04／29 以既有機制為主，附錄 A 已說明。

**DP→S-NN**（SOP；腳本輸出逐字）：

```
DP rows parsed=12
matrix S entries parsed=30
DP table source not in matrix S->DP: []
matrix S->DP pair not in DP-table main-source column (these are the prose-only/limiting sources): [S-01->DP-01, S-02->DP-01, S-04->DP-02, S-04->DP-08, S-11->DP-08, S-12->DP-02, S-12->DP-08, S-17->DP-12, S-22->DP-08, S-28->DP-12]
S with no DP in matrix: [S-30]
```

12 條 DP 的主要來源全在來源表且全在 S→DP 追溯矩陣內；矩陣多出的 10 對是 DP 內文的限定／旁證來源（SOP:280–291 逐條有寫；其中「S-28->DP-12」是我的解析把「S-28、S-29→地圖用（S-29 另支撐 DP-12）」併成一組的假象，實際只有 S-29 支撐 DP-12）；S-30 無去處但 SOP 明標「旁證，不支撐 DP」。

**URL 抽查**（額度守衛把 WebFetch 當扇出，每 300 秒放行 1 次；我交錯進行，合計嘗試 8 次上限；以下時間為本機 +08:00，帳本現查：`%TEMP%\autosdd_quota_dispatch.d\*.dispatch` 的 LastWriteTime）：

| # | 嘗試時間 | 來源（層級；追溯 DP 數） | URL | 結果 | 與 SOP 描述比對 |
|---|---|---|---|---|---|
| 1 | 04:34:22 | S-11（V2；DP-01／05／08／09／10） | `https://arxiv.org/abs/2608.00017` | **被守衛擋下**（hook 訊息：每 300s 最多 1 次扇出，本視窗已用 1 次；帳本 04:33:13 有一筆非我發出的 dispatch，帳號層級） | 不計入「抽到」 |
| 2 | 04:38:39 | S-11 | 同上 | 成功。標題「Memory Reward Inflation in Self-Improving LLM Agents」；作者 5 人（Mohammad Asadolahi、Amir Amini、Samira Talebi、Amirfarhad Farhadi、Azadeh Zamanifar）；「Submitted on 29 Jun 2026」只有 v1；無 comments／venue；摘要「LUCID … raises execution accuracy to 56.9%」「Memento-style self-graded agent (54.0%, a +2.9-point mean gain across seeds)」「memory-less agent of identical architecture (52.4%)」、`Echo Gap`、`Error-Independence Assumption` | **全部吻合**（SOP II-3 S-11、II-4 S-11、II-2 #18）。附註：頁面自己顯示 ID 前綴 2608 與提交日 6 月不符，SOP 只對 S-14 標了這種異常（F-20） |
| 3 | 04:46:48 | S-17（V3；DP 8 條，全 SOP 最多） | `https://arxiv.org/abs/2505.22954` | 成功。標題「Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents」；作者 5 人（Jenny Zhang、Shengran Hu、Cong Lu、Robert Lange、Jeff Clune）；v1 29 May 2025、v2 26 Sep 2025、v3 12 Mar 2026；Comments 欄只有程式碼連結、無 venue；摘要「SWE-bench from 20.0% to 50.0%」「Polyglot from 14.2% to 30.7%」「safety precautions (e.g., sandboxing, human oversight)」 | **全部吻合**（SOP S-17；F6 已記「摘要頁無 venue、PDF 頁首 ICLR 2026」） |
| 4 | 約 04:51:3x | S-08（V3；DP-02／03／04／07／09） | `https://code.claude.com/docs/en/memory` | **被守衛擋下**（距上次成功僅約 296 秒） | 不計入 |
| 5 | 04:52:04 | S-08 | 同上 | 成功（整頁 50.2KB 回傳並存檔，我對存檔 Grep／Read）。存檔行 546：「The first 200 lines of `MEMORY.md`, or the first 25KB, whichever comes first, are loaded at the start of every conversation」；行 31 表格「Every session (first 200 lines or 25KB)」；行 94「…proposed edits, and nothing in your files changes until you ask Claude to apply them」（`/doctor prompt-audit`）；行 540「Auto memory is machine-local …」；頁首「Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook」 | **全部吻合**。另發現 SOP／PRD 未記的 harness 容量機制（存檔行 548；F-05） |
| 6 | 04:57:18 | S-23（V2；DP-04／06／10＋CD-03） | `https://arxiv.org/abs/2606.08106` | 成功。標題「PACE: Anytime-Valid Acceptance Tests for Self-Evolving Agents」；單一作者 Zayx Shawn；v1「6 Jun 2026」、無後續版；無 venue；摘要「greedy acceptance commits 30-42% false and 10-33% harmful edits」「13-21 spurious self-modifications per run (72-100% false)」「most fragile agent by 4.9 points」「about 18% lower evaluation cost」「Qwen2.5 agents (0.5B-3B)」、GSM8K／SVAMP／ARC-Challenge、testing-by-betting e-process | **全部吻合**（含 SOP 標的「單一作者、小模型」信度註記） |
| 7 | 05:05:0x | S-25（V2；DP-06／09） | `https://arxiv.org/abs/2607.27687` | 成功。標題「Rehearse: Stepping Back from the Confidence Cliff in Self-Improving Autoresearch」；作者 Jiazhen Ji、Shouhong Ding；v1「30 Jul 2026」；無 venue；摘要「falls from 70% in the first two iterations to 43% by iteration 6+」（來自公開 AutoSOTA 紀錄）、「falls from 82.8% to 56.9%」（嚴格共識有裁決的成對上）、「raises late selective accuracy to 83.5%」、296 組／39 任務／79.5%、366-pair benchmark、4,000 budgeted training runs over three loops | **全部吻合** |
| 8 | 05:10:2x | S-04（**V1**；DP-02／08 旁證） | `https://arxiv.org/html/2308.10144v3` | 成功（頁面全文 100,740 字元，工具只讀前 100,000）。標題「ExpeL: LLM Agents Are Experiential Learners」；作者 6 人（Andrew Zhao、Daniel Huang、Quentin Xu、Matthieu Lin、Yong-Jin Liu、Gao Huang；Tsinghua／BNRist）；頁首 `arXiv:2308.10144v3 [cs.LG]`、日期 20 Dec 2024；無 venue；摘要「learning from agent experiences without requiring parametric updates」「extracts knowledge in natural language … recalls insights and past experiences at inference」 | **標題、年份、無梯度更新吻合**；SOP II-4 S-04 的「從成功與失敗軌跡抽取洞見」（V1 搜尋摘要轉述）在摘要頁查無（只說從訓練任務蒐集經驗並抽取自然語言知識），「作者欄未見」現可補（6 人）。僅旁證，不影響 DP（F-20） |

**合計嘗試 8 次、成功開頁 6 個（V2／V3 五個：S-11、S-17、S-08、S-23、S-25；V1 一個：S-04）**；被守衛擋下的 2 次（#1、#4）不計入「抽到」。打不開、標題不符、作者年份不符者：0 筆（⇒ 無「引用不存在／失真」P1）。SOP 交付自檢清單⑨「抽 3 個 V2 數字開原頁面核對一致」：S-11（三個百分比）、S-17（兩組百分比）、S-23（五組數字）、S-25（六組數字）共 16 個數字皆與 SOP II-4 抽取逐字一致 ⇒ ⑨ 成立。未抽的 2026 預印本（S-12、S-13、S-14、S-15、S-19、S-24、S-29）列入 §4 未涵蓋。

### 1.4 憲法對照 — FAIL（F-01）

對照物：`AISDLC_SDD/CLAUDE.md` Rule 9 禁令 1～27（行號＝314＋N，我讀 300–342 行逐條核對，與 PRD:181 的座標規則相符）、根 `CLAUDE.md`〈守衛面准入〉〈權限姿態〉〈鐵律四〉、範本〈🏁〉（`AutoSDD_Iteration_Prompt_Template.md`:352–358 再開觸發、:344–350 休眠判準、:371–375 審查閉環）、五問協定 README:67–76（S1～S6）、:85–89。

| 檢查項 | 結果 | 證據 |
|---|---|---|
| 自動套用規格補丁（禁令 12） | 無（晉升須 `dec(promote)` 且 `si promote` 驗引言；不自動） | AC-SI-16-1（PRD:308）、AC-SI-12-4（:288）；R-9.22 原文「proposed，絕不自動套用，經 HUMAN_PENDING」（R-9.22 yaml:14）。灰區見 F-21 |
| 自改守衛面／憲法面 | **設計上有繞過路徑** | F-01：機械邊界只比 `target` |
| 以自評為唯一判官（禁令 17） | 無 | AC-SI-18-2（:320）「主依據必為外部可重跑訊號…LLM 審查意見不得單獨把 FAIL 改成 PASS」；NE 不得視為 PASS（:324） |
| 無界遞迴／自我擴充（禁令 4、14～25） | 無 | FR-SI-10（≤3、零遞迴）、MAX_REVISIONS、STOP_AFTER_BAD、CHURN_MAX、SUSPENDED 由事件折疊（NFR-SI-01 表，PRD:383–392）；§3.2 :145 明禁迴圈改自己的預算／閘門／停機條件／指標定義 |
| 日曆／版本號／覆蓋度觸發（C-12） | 無 | 我對 PRD 全文 Grep 兩組字樣——(一)「每 N 輪」「定期」「每週」「每日」「每月」「cron」「schtasks」「排程」「常駐」「Daemon」「週期」22 筆命中；(二)「覆蓋度」「coverage」8 筆命中（行 73、146、237、475、744、746、943）——**逐筆看前後文全是否定句或既有機制引述**（行 146、183、237、475、485、809、819…）；`si status` 為「唯讀、按需」不是排程（AC-SI-03-1，:237） |
| 零發現不是 PASS | 有 | AC-SI-03-2（:238）、§8.2（:474）、§1.3.1 末列（:74） |
| 守衛面准入（量、不挖） | 字面合規，精神有張力 | PRD 零新增 hook／`.claude/**`／守衛面 `tools/lib/` 檔；C13 契約測試與 `tools/` 新檔屬「鎖」類但不在守衛面清單（:654 ⑤）→ P4（F-22） |
| 附錄 B 漏列被觸及的禁令 | 無 | 附錄 B（:881–897）涵蓋禁令 1～27（2 號 Phase D·E hooks 未被觸及，無需列）、守衛面准入、權限姿態、PRD v2.1 §15.5 紅線 10、鐵律一～七、〈🏁〉、Rule 5／6／12 |

### 1.5 Goodhart 檢查 — FAIL（F-02）

- §1.3 的 M1～M5 沒有一個是提案數／採納率／審查產出數／覆蓋度百分比；§1.3.1（:67–74）明文禁用表（提案數、採納率、駁回率、審查產出數、OBS 筆數、自評分數、覆蓋度／測試數／行數、零發現）並附座標。每個指標都有量法與資料源座標（:61–65 末欄）。
- **但 M1 的鑑別力不足**（F-02，P2）。M2／M3 可被灌水且與迴圈因果連結未述（F-14，P3）；M5 排除 `unverified_ack` 而 M／D 類預設走 `unverified_ack`（:324、:654），分母剩易驗證類，有倖存者偏誤（F-14）。M4＝0 屬結構不變式（由冷卻保證），可證偽（>0＝冷卻被繞過），不扣分。

### 1.6 既有系統盤點真偽（§11、§9.0）— PASS（P1＝0）

要求抽查 ≥6 筆；我實際以 PowerShell `Test-Path` 對 PRD 引用的 **82 條**路徑逐條現查（輸出逐行 `True/False`），**77 條存在；5 條不存在＝PRD 明標「新建」的路徑**（`tools\selfimproving.py`、`tools\probe\selfimproving_measure.py`、`docs\06_quality\SelfImproving_Protocol`、`docs\06_quality\SelfImproving_Event_Ledger.jsonl`、`docs\05_development\SelfImproving_Operations_SOP.md`）；`docs/04_planning/ADR/` 無任何 `ADR-SI-*`（PRD 稱「候選」，相符）。再對行號逐條比對（Grep／Read 逐字）：

| PRD 宣稱（座標） | 現場（逐字重點） | 結論 |
|---|---|---|
| `utils/config.py`:188／192／194／211／226 | 188 `step_timeout_seconds: int = 600`；192 `max_evolutions: int = Field(default=3…)`；194 `require_evolution_signoff: bool = False`；211 `goal_synthesis_fail_closed: bool = False`；226 `translation_max_proposals_per_run … default=3` | 五處行號全中 |
| `evolution/playbook_evolver.py`:14–16、:37、:302、:274–298 | 14 `INJECT_STEP`、15 `SPLIT_STEP`、16 `REVISE_EVALUATOR`；302 `evolved_path = … f"evolved_{…}"`；274 起 `evolution_metadata`／`mutation_log` | 吻合（SOP:291 稱 14～15 列兩型為小誤，F-20） |
| `plugins/evolution_plugin.py`:9–19、:113–132、:284–289 | 13 `ON_EVOLUTION_APPLY → **NO-OP**`；113 `_handle_propose`、124 `MutationProposal(`；284–287 `REVISE_EVALUATOR` → `REVISE_CURRENT`＋`[evolved evaluator suggested]` | 吻合 |
| `core/kernel.py`:371–374 | `logger.info("=== EVOLUTION PROPOSAL \| [%s] type=%s \| %s ===", … reasoning[:200])` | 吻合 |
| `core/services/auto_resume.py`:255–272 | `if result.evolved_playbook_path and _evolution_count < _max_evolutions:` 重載分支，無 signoff 閘 | 吻合 |
| `execution/playbook_runner.py`:299–322、:306 | `_evolution_signoff_granted`；306 `if not self._cfg.playbook.require_evolution_signoff: return True` | 吻合 |
| `apply_evolution` 呼叫點（AC-SI-28-1 ②） | 全 `autoclaude/` Grep：定義 `playbook_evolver.py:229`＋呼叫點恰為 `_escalation_handler.py:111／208／263`、`_complex_mutations.py:114`；`execution/` 之外對 `steps_orchestrator`／`mutation_applier` 只有註解、無 import | 吻合 |
| 演化重載生產者（AC-SI-28-1 ③）、旗標讀取點（④） | `evolved_playbook_path=` 只在 `resolution_policy.py`（彙整）與 `execution/`；`kind="evolved_playbook"` 零命中；`require_evolution_signoff` 讀取只在 `playbook_runner.py:306` | 吻合 |
| `main.py`:277 註解；`AutoClaude/CLAUDE.md`:191 | 277 `# 舊 PlaybookRunner 直連模式已於 W6 拔除（…）`；CLAUDE.md:191 現仍含 `（main.py:277）` 行號形態（AC-SI-28-1 ⑤ 將於改述落地後轉綠，PRD 已載明同輪落地） | 吻合 |
| `tests/core/test_kernel_unhandled_mutation_failloud_r85.py`:97–112 | 97 `class TestTheUnreachableImplementationsAreReallyUnreachable`、103–112 含對照組（`PlaybookTask` ≥10 筆） | 吻合 |
| `.claude/hooks/block_destructive_git.py`:1445、:1423–1472、:824–867 | 1437 `GOV_TOOLS = frozenset({"Write","Edit","NotebookEdit"})`；1445 `_GOV_EXACT`（不含三份 CLAUDE.md、governance/rules）；1424–1425「只在 AUTOSDD_UNATTENDED 有設時阻斷」；824–867 worktree remove 判準 | 吻合 |
| `.claude/hooks/check_claim_provenance.py`:824–826、:854–866 | 826 `_OPERATOR_TURN_ORIGINS = ("human", "sdk")`；836–866 docstring 載明欄位「觀察所得、非官方契約」 | 吻合 |
| `tools/probe/audit_session.py`:8–14、:31–32、:250–257、:844 | 8 起「🔴 邊界：只能當量測器，不得接成閘門」；31–32「報表印判準指紋」；251–257 slug 規則；844 `"seq": i` | 吻合 |
| `tools/lib/defect_ledger_index.py`:545；`governance_docs.py`:710；`check_defect_log_crossref.py`:1152–1153 | 545 `ROW_MAX_BYTES = 700`；710 `_GOVERNANCE_DOC_GLOBS = (`；1152–1153 `_LEDGER_WARN_BYTES = 240 * 1024`／`_LEDGER_FAIL_BYTES = 256 * 1024`（另 212 `row_arity_problems`、1013 `_load_ledger_status` 存在） | 吻合 |
| `tools/tests/test_defect_id_reference_integrity.py`:73、:76–79、:126–141 | 73 `_REF_RE = re.compile(r"DEF-(?:101\|200)-\d+…")`；78–79 `_MIN_LEDGER_IDS = 500`／`_MIN_REF_LINES = 800`；126 `_git_grep` | 吻合 |
| SDD：`rule_loader.py`:309、`scaffold_gc.py`:10–11、`meta_halt_monitor.py`、`spec_patch_proposer.py`:25、`counterfactual_replay.py`:19、`SDD_FSM_ENGINE.md`:395–396 | 309 `def set_maturity(rule_id, new_maturity, *, reviewed_by…)`；10–11「GC 只『提議』，永不自動退役」；`SDD_META_CHURN_MAX` clamp[1,5] 預設 2；`MAX_PATCH_PER_AC = 2`；`SDD_REPLAY_MAX_CASES` clamp[5,200]；395–396 LEARNING_COMMIT 人工 review | 吻合 |
| `AgentConsole/CLAUDE.md`:15；`FiveQuestion_Audit_Protocol/README.md`:67–76、:85–89；範本:352–358、:371–375；`params.json` | 15 SDD FSM 寫入一律經 `FSMRuntime` CLI；README S1～S6 與家族計數降為資訊欄；`q1b_min_n: 5`、`q2_min_n: 5` | 吻合 |
| `AutoSDD_Defect_Log.md`:70、:324 | 70 表頭 `\| ID \| 發現日期 \| …`；324 DEF-200-551 現象欄含「DEF-200-535 再開症狀於 116 命中」 | 吻合 |
| `commit 738f4f60`、`69a644e6` | 皆存在；各只改 `AutoClaude/CLAUDE.md` 1 行 | 吻合 |

**§9.0 SD 普查重跑**：Q7（`git ls-files -z`）：`tracked files=29249`、`AISDLC_SDD/ files=26207`、`max relative path length=142`、四棵子樹 `files=2132 maxlen=118`、scratchpad 根 118、`export-ignore: unspecified`——**與 PRD:517 全部一致**。Q6：`defect ledger family files=70`；DEF 列（我的正則 `^\| DEF-(101\|200)-\d+ \|`）1,508（SD 稱 1,667／去重 1,661，口徑不同、未對帳）；`rows containing '再開症狀'=4`、`… and '命中'=1`、`rows containing 'reopens:'=0`——**三個關鍵基率與 PRD:516 一致**（F-02 的前提）。Q5：`archive-index-2026-07-to-09-rounds.md` 8,192 bytes、41 條 `- [` 行，相符；`MEMORY.md` 現為 16,391 bytes／75 行／記憶目錄 127 個 `.md`（快照值，PRD 已聲明；節序已變，見 F-06）。

### 1.7 邏輯一致性（SLV 精神）— FAIL（F-03）

- §3.1 ↔ §8.1 ↔ §9.6：29 條 FR 在三處的階段歸屬**逐條一致且各只出現一次**（P0：01～04、29；P1：05～11、14、28；P2：12、13、15～21；P3：22～27）；FR-SI-14 屬 P1 而 FG-D 屬 P2 已在 §3.1 註明。
- §3.2 範圍外 ↔ §5 需求：無衝突（候選 CD-01～04 只作反例出現，T-1 字面已訂正）。
- §12 接點 ↔ §9：一致（MVP 不碰 Console／Bridge、引擎只讀、`FSMRuntime` 只經 `show`）。
- §9 架構 ↔ §5：ATT／PROP／DEC 載體、`si check`／`status`／`decide` 的階段、digest 演算法與 §5.1.2／AC-SI-12 對得上；§9.7 的 28 筆審閱紀錄各指向 §5／§6／附錄 B 中確實存在的條目。
- 矛盾／灰區：**F-03（P2）**、F-08（ESCALATION 未定義）、F-13（M1 量法與 AC-SI-06-2）、F-12（M 類窗可能不關）、F-21（D 類與規格文件）、F-23（AC-SI-15-1 的 `git worktree list` 與 ADR-SI-04 選 B 不對齊，P4）。
- 物理可行性：`si decide` 依賴的逐字稿欄位在本機**實際存在**——我對 `f3ead132-…jsonl` Grep：`"origin":{"kind":"human"}` 於 line 13／761／901，`"origin":{"kind":"task-notification",…}` 多筆，`"turnOrigin":"human"／"peer"`，`"isMeta":true` 共 7 筆；`sid`＝檔名 UUID、`line`＝1 起算實體行號皆可取。欄位為觀察所得非官方契約，PRD 已自承（ADR-SI-03、:587）。ADR-SI-04 選 B（`git archive` 匯出）量級經 Q7 重跑可行。

### 1.8 SOP 本身 — PASS（附 P3／P4）

- Part I 八步：SOP:15–24 總表每步皆有輸入／輸出／通過判準，S1～S8 各節展開；S3 七欄固定、缺欄寫「未見」；S4 有證據門檻與強度規則；S5 結論只准四種；S6 四條件缺一＝只登記。
- S7（SOP:112–122、II-7:316–326）：T-1～T-7 全為可觀測症狀（追溯斷裂、dogfood 失效、harness 行為與假設矛盾、反證浮現、守衛面變動附暴露證據、新需求、來源失效），明文「不是觸發：日期經過、版本號改變、論文數量增加、覆蓋度」；無日曆與版本號。
- 誠實劃界：Part II-8 三桶齊全（沒查到／只讀摘要或搜尋結果／沒讀全文＋其他界線）；來源表第 8 欄標「查證方式（呼叫 #）」，層級欄非空（V1：S-04、S-30；V3：S-08、S-10、S-17、S-27）。
- 交付自檢清單 10 條：① 來源表每列有 URL 且層級非空 ✓；② 每個 URL 有出處呼叫（對應 #）✓（V1 兩筆的 URL 只在工具輸出、不在 SOP 紀錄表內逐字出現，見 §4）；③ 每條 DP 組數 ≥2（或 1＋實證）✓（組數欄 3～6）；④ 每條 DP 有反證／限定欄、DP-07 誠實寫「未做專門反證搜尋」✓；⑤ 四格有理由（唯 SOP:278 自承四格全 ✓ 是選出來的，F-26）；⑥ 數字可追 S-NN ✓；⑦ S7 不含日期／版本號 ✓；⑧ 三桶齊全 ✓；⑨ 見 §1.3，16 個 V2 數字核對一致 ✓；⑩ 無「之後再看」✓。
- 問題：DP 強度欄與 S4 自己的規則（SOP:69、:92）無法對照（F-19）；S-14／S-11 的 arXiv ID 與提交日不符只標一處（F-20）。

### 1.9 觀察帳本 — PASS（附 P3；P0 遷移待做）

- 現行欄位 8 欄（ID／時間／情境／症狀／證據座標／分類／嚴重度／處置），PRD §5.1.1 定稿為 8 欄＋第 9 欄「標記」，PRD §8.1 P0 把遷移列為交付（AC-SI-01-3），目前尚未做 ⇒ 尚不一致但屬已排程，不扣分。處置值現皆為自由文字（「登記」「裁決：…」「入 PRD §11 缺口表…」等），非 PRD:205 枚舉；PRD 以 AC-SI-01-3 規劃遷移——但該遷移與 AC-SI-04-3 矛盾（F-03）。
- 指令與輸出（逐字）：`file bytes=14240`、`lines=43`、`data rows=34`、`min=215 max=558`、`OBS-SI-016=558, OBS-SI-010=538, OBS-SI-005=510, OBS-SI-022=501`、`unique ids=34 first=OBS-SI-001 last=OBS-SI-034`、`CR bytes in file: 0`；34 列皆 ≤700 bytes（Q10 重跑吻合）。
- 「之後再看」：無（唯一命中是行 6 的規則句）。「沒有座標」：無空座標，但 **3 列座標不可定位**（F-15）。
- 另發現：OBS-SI-028 列被切成 9 欄（F-16）；OBS-SI-001／002 時間欄早於 T1 實際到達（F-17）。

### 1.10 語言與格式 — PASS

繁體中文（專有名詞保留原文）；檔名 `SelfImproving_PRD.md` 合 `*_PRD.md` 慣例（OBS-SI-001 裁決）；三檔 CR 位元組 0（PRD／帳本實測 `CR=0`、`CR bytes in file: 0`）；機密值掃描（`sk-…`、`AKIA…`、`ghp_…`、`xox…`、`-----BEGIN`、`api_key=`、`password=`、`Bearer …`、60+ 字元 base64 樣式）對三檔 `No matches found`；全文無日曆承諾（§1.4 的 Grep）。

## 2. 發現清單

嚴重度口徑：P1＝引用不存在／失真、宣稱無證據、違反 Rule 9 絕對禁令；P2＝終點設計結構漏洞；P3＝文字／可用性；P4＝理論洞（登記不修）。誰修：SA＝§1～§8、§10～§14；SD＝§9；主控＝帳本／裁決；研究員＝SOP。

### 2.1 P1（0 筆）與 P2（3 筆）

| 編號 | 嚴重度 | 位置 | 症狀（一句） | 修法建議 | 誰修 |
|---|---|---|---|---|---|
| F-01 | **P2** | PRD:214、:567、:648（§9.4）、:650、:397（NFR-SI-02-1）、:664（ADR-SI-06）、:298／:452–460 | 不可進化面的「機械可擋（M 型）」前置檢查只把**單一 `target`** 比對 `non_evolvable_globs`；`rN.patch` 是 unified diff 可含多檔（PRD 自己的歸檔型 M 類就要同時動 `MEMORY.md` 與新檔 `archive-index-*.md`，:664），沒有任何 AC 要求「diff 內每個路徑」都過 glob，`si promote` 也只驗 DEC＋digest＋pre-image（:650），提案卡核心區 ≤12 行且 diff 只以座標附尾（:298），人審看不到觸及的檔案集合。glob 也有缺口：`.claude/**` 根錨定（子專案 `.claude/` 是否涵蓋未定義；我現查：`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/` 有 5 支 hook——`closure_evidence_verify.py`、`context_ledger_post.py`、`context_ledger_pre.py`、`post_commit_drift.py`、`session_start.py`，即禁令 2 的 Phase D·E hooks，另 `AISDLC_SDD/.claude`、`AutoClaude/.claude` 亦存在）；「非 LATEST 版本目錄→handoff」只對 R 類（:648），D／P／M 類可指向凍結版本目錄（根 CLAUDE.md〈路徑陷阱〉：只有 LATEST 可原地改）與 `docs_template/**`；OBS／事件帳本與 `SelfImproving_Proposals/` 不在 (iv)。結果：標成 M 型的閘給出超過實際的保證，憲法面（守衛面、`CLAUDE.md`、凍結版）有繞過路徑，違反 PRD 自己宣稱的「不可進化面…本迴圈對其零寫入」（詞彙表 :822、AC-SI-07-1 :257）與附錄 B 對禁令 11／12、守衛面准入的對照 | 新增 AC（例 AC-SI-07-3）：`prop-new` 與 `promote` 解析 `rN.patch` **全部** `---`／`+++` 路徑並逐一比對（realpath＋normcase）；任一命中不可進化面或凍結版本目錄 ⇒ 整張 `route=handoff`；`target` 改為路徑集合並進 digest core；卡核心區顯示「觸及檔案數＋非 target 路徑」；明定 glob 錨定語意（`**/.claude/**` 或逐子專案列出）、補子專案 `.claude/`、凍結版本目錄（所有類別）、`docs_template/**`、SI 帳本與 Proposals 目錄；負控：patch 夾帶 `CLAUDE.md`／`.claude/hooks/*.py`／凍結版本檔 ⇒ 被拒 | SA（§5.1.2、FR-SI-07／11 AC、NFR-SI-02-1）＋SD（§9.2 digest core、§9.4 前置檢查） |
| F-02 | **P2** | PRD:38（§1.1 反證條件）、:61（M1）、:516（Q6）、:725、:345、:469 | M1＝窗內確認再現數 ÷ 窗內已結列數，窗＝最近 `W_N`＝20 筆 `fixed` 列；NE 護欄 `n < W_MIN`（5）作用在列數，窗定義使 n 恆為 20，**護欄永不觸發**。PRD 自己的 Q6 普查（「再開症狀」4 列、「命中」1 列、`reopens:` 0 列為我重跑吻合；「1,490 筆 fixed」是 PRD:516 的 SD 數字、我未重算）顯示再現事件基率約千分之一，20 列窗的期望事件數約 0.01～0.05（＝20×1/1,490～20×4/1,490）⇒ M1 幾乎恆為 0/20。後果：(a) 基線為 0 時「低於基線」不可能成立；(b) §1.1「連續兩窗未低於基線＝願景被反證」在最可能的世界裡**必然成立，與迴圈有沒有效無關**，反過來也無從「支持」願景；(c) 全域 20 列窗稀釋單一 PROP 的效果，且與 FR-SI-23 的「同目標路徑前綴」窗不同基準；(d) §10.1 自承「樣本過小致指標常態 NOT-EVALUABLE」，但護欄量錯對象 | NE 護欄改量「基線窗內確認再現事件數」（`W_EVT` 下限，初值未校準）；基線事件數＝0 時明文判 NE（不得算「未低於」）；M1 改採 per-PROP 前後對照（沿 FR-SI-23 的採納窗與目標前綴）或另設基率較高的症狀指標；§1.1 反證條件改寫為「在可評估窗（事件數 ≥ 下限）內…」；補一段檢定力說明（預期事件數） | SA（§1.1、§1.3、FR-SI-22／23） |
| F-03 | **P2** | PRD:230（AC-SI-01-3）、:244（AC-SI-04-3）、:466（§8.1 P0 (b)）、:596（§9.3 `check` 含 `ROW-MUTATED`）、:672（§9.6 P0 (b)「`check` 綠」） | AC-SI-01-3 要求把既有各列遷移到定稿欄位（加第 9 欄、非枚舉處置改寫為枚舉並以 `orig=` 留原文＝**原地改寫**）；AC-SI-04-3 規定除「處置欄 open→終值一次」外的原地改寫一律標 `ROW-MUTATED`、「更正一律追加更正列」，且 `si check` 對 HEAD 與**歷次提交**逐對比較——遷移 commit 永遠留在歷史 ⇒ 34 列永久 `ROW-MUTATED`；P0 出口 (b)／§9.6 要求「`check` 綠」。現行 34 列處置皆為自由文字（非 `open`），所以都是「終值→終值」的改寫。全文沒有遷移基準 commit、豁免或確認清除機制；兩種更正機制（`orig=` 原地 vs 追加更正列）也互相衝突。依文字 P0 出口不可達 | 在 `params.json` 定義 `migration_base_sha`（`ROW-MUTATED` 比對起點＝遷移 commit）或「遷移一次性豁免＋掌舵者確認事件」，並在 AC-SI-04-3 明文；統一「更正」機制（擇一）；§8.1／§9.6 P0 (b) 改述為「自遷移基準起 `check` 綠」 | SA（AC-SI-01-3／04-3、§8.1）＋SD（§9.3 `check` 比對起點、§9.6） |

### 2.2 P3（18 筆）

| 編號 | 位置 | 症狀（一句） | 修法建議 | 誰修 |
|---|---|---|---|---|
| F-04 | PRD:911（C.2 表頭）、:907、:909；逐字稿 `C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\f3ead132-29b1-418c-97d9-35868ab11c70.jsonl` line 13／761／901 | C.2 寫「授權依據＝掌舵者**本輪**原文」；該句實為本 session **第一則** human 訊息（line 13，2026-10-18T13:03:23Z，整合輪 116 的問題 1～4，「以上」指該訊息內容）；SelfImproving T1（line 901，14:40:46Z）不含此句；整個 session 在查驗時只有 3 則 `origin.kind=="human"`（13、761、901），T1 之後掌舵者再無發言；PRD 引文還截掉後半「若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策」。#5 修訂與 #6～#9 是主控代決。PRD 已寫「凍結核准時掌舵者可逐項推翻」，故不升級 | C.2 改述為「延伸解釋，凍結時逐項確認」，完整引句並附 sid＋line（同 FR-SI-12 的引言體例）；主控向掌舵者報告時如實說明授權範圍 | 主控（附錄 C） |
| F-05 | PRD:44（§1.2）、:363–364（AC-SI-27-1／2）、:767（G-SI-07）；SOP:235（II-4 S-08）；官方頁（本審查存檔行 546–548） | 官方 memory 頁寫明 harness 在 Claude 寫入 `MEMORY.md` 後**自己量測**：近上限時提醒 Claude「keep one line per entry, move detail into topic files, and merge or drop stale entries」，超限時寫入仍成功但回錯誤要求重寫索引；SOP 對 S-08 只 Grep 關鍵行（V3 自述未通讀），PRD 因此把「無退役機制／被截斷」當缺口，未提這條既有機制，也未處理它與 `CAP_FRAC` 容量事件、M 類 PROP pre-image 比對的競爭（harness 的 Claude 是不受控寫入者） | 補一行既有機制（S-08 行 546–548）；G-SI-07／AC-SI-27 說明 harness 提醒與 SI 容量事件的先後與 pre-image 衝突處置；SOP II-4 S-08 補列（觸發 T-3／T-4） | SA（§1.2、§11.2）＋研究員（SOP II-4） |
| F-06 | PRD:515（Q5）；帳本:39（OBS-SI-030）；PRD:909（C.1） | Q5 結論「若被截斷，先被吃掉的是尾端常青教訓節」已被 OBS-SI-030 的重排推翻（現行 `MEMORY.md` 節序：工作方式教訓行 5→機制與環境事實行 30→近期輪次行 51；現值 16,391 bytes／75 行／127 檔），PRD 同檔 C.1 已記重排卻未回填 Q5 | Q5 加「重排後已反轉」並標快照時刻 | SD（§9.0 Q5） |
| F-07 | PRD:288（AC-SI-12-4）、:447（§7.2） | ① 只說「引言逐字出現在真人發言」＋② 「符合 §7.2 回覆語法」，沒規定整則訊息（或整行）必須等於語法（子字串即可？）；「不核准 PROP-SI-007」「核准 PROP-SI-007？先等一下」「貼回卡面（含『決定：核准 ／ 否決…』）」可能被子字串命中。負控清單（sdk、他 PROP、過期 digest、被改寫卡面）無否定句／引用句；本 repo 已有同型先例（Stop hook 否定句誤報，DEF-200-501） | 規定錨定（整則 human 訊息去空白後＝語法，或獨立一行）；負控加否定句、疑問句、引用卡面、多 PROP 同則訊息 | SA（AC）＋SD（C8） |
| F-08 | PRD:314（AC-SI-17-2）；:504 | 「Given 進入 ESCALATION When 恢復」：本迴圈不讀寫 FSM-STATE、無 FSM 狀態，自身停機態是 SUSPENDED（AC-SI-24-1）；`si status` 不讀 `show`——AC 無可觀測判定 | 改用 SUSPENDED／「升級人工」語彙，或明定 `run-open` 先讀 `show` 並在 ESCALATION 時拒絕 | SA |
| F-09 | PRD:89–97（§2.1.1 矩陣）、:613；:275；:400 | §9.4 自訂規則「任何不能做／被拒宣稱必須註記邊界型（M／D／P）；P 型不得寫成被擋」，但 §2.1.1 權限矩陣整表「不能做」欄（寫正式面、再派子代理、看見 held-out、寫報告檔…）、NFR-SI-02-4「運轉期不開網路外聯」、AC-SI-10-2「零遞迴」皆無型別標註 | 矩陣加一欄「邊界型」；NFR-SI-02-4 與 AC-SI-10-2 標 P 型並指偵測面（若有） | SA |
| F-10 | PRD:233（AC-SI-02-1）、:648（`cls∈{M,R}`） | 「外部衍生內容不得單獨充當證據」只限 M／R 類；P 類（Playbook 片段＝可執行步驟）與 D 類不受限，與 SOP 風險 S-13（MemoryGraft）／S-09 頁尾內嵌指示同型入口，且無理由說明 | 擴及 P／D，或明寫為何排除 | SA |
| F-11 | PRD:563、:555、:619–621（事件帳本多寫入者） | 歸因者／確認者／提案者／凍結者／審查者皆經 CLI 寫同一個 git 追蹤 JSONL，`seq` 與 `PROP-SI-NNN`＝max＋1 在並行（NFR-SI-07-2 允許扇出）下會撞號；鐵律七檢查表 1（帳本單窗口）只對 OBS 明文；AC-SI-08-4 的「ID 唯一遞增」只事後偵測 | `si` 寫事件取檔案鎖並以 O_APPEND 原子追加，或明定單一寫入視窗；補併發負控 | SD（§9.2） |
| F-12 | PRD:345（AC-SI-23-1）、:469、:725 | 採納窗以「OBS／DEF 證據路徑落在 target 最近公共目錄之下」計 `W_OPP`；M 類 target＝`memory/<檔名>`（repo 外），OBS／DEF 證據路徑幾乎不會落在該前綴 ⇒ M 類窗只能靠再現／回滾關閉；P3 出口 (b) 與 M5 分母可能長期空；沒有「久未關閉」的事件型處置 | M 類窗改以「同條目被引用／同根因鍵新列」計；或明定 M 類窗關閉規則 | SA |
| F-13 | PRD:61（M1 量法）、:254（AC-SI-06-2）、:688（§9.7 #7） | M1 說「再現候選由量測腳本自帳本抓（`reopens:` 標記、現象欄『再開症狀…命中』字樣）」；AC-SI-06-2／SD #7 改為「量測腳本只讀已寫入的標記與確認事件，不在量測期掃描產生候選」，M1 文字未連動 | M1 量法改述同 AC-SI-06-2 | SA |
| F-14 | PRD:62–63（M2／M3）、:65（M5）、:324、:654 | M2／M3 與迴圈因果連結未述，中位數可被拆列快速結案、改發現日期、批次結案影響（只排除 `closed-by-decision` 一種）；M5 排除 `unverified_ack` 而 M／D 類預設走 `unverified_ack`（「預期常態」）⇒ 分母主要剩易驗證類，倖存者偏誤；資訊欄「另列」但未要求與指標並列呈現 | 補因果說明或降為資訊欄；M5 同時報「含 `unverified_ack`」值；AC-SI-22-2 要求並列 | SA |
| F-15 | 帳本:13（OBS-SI-004「操作員回報原文」）、:22（OBS-SI-013「研究員回報」）、:42（OBS-SI-033「SA 回報」）、:41（OBS-SI-032「PRD 約 186／495／…行」）、:36（OBS-SI-027 座標＝scratchpad 腳本） | 依 PRD §5.1.1「證據座標 ≥1 個可定位（檔案:行／指令＋rc／sid＋seq／帳本列 ID）」不合規；scratchpad 座標會隨收輪清理消失；P0 出口 (d)「零筆無座標列」（:466）未達 | 補 sid＋line 或可重跑指令；不可補者處置改 `retired` 並寫依據 | 主控 |
| F-16 | 帳本:37（OBS-SI-028） | 症狀欄 `` `(?:101\|200)` `` 內的 `\|` 未轉義，該列被切成 9 欄（腳本輸出 `rows with !=8 columns: OBS-SI-028:cols=9`；其餘 33 列皆 8 欄）＝PRD ADR-SI-01（:659）自述的「管線字元轉義」反覆缺陷源已在本帳本現形 | 轉義或改寫；`si check` 欄數檢查須能抓到此型 | 主控 |
| F-17 | 帳本:10–11（OBS-SI-001／002）；逐字稿 line 893／901 | 時間欄寫 22:05（OBS-SI-002 另寫「量測於 21:34」），但 T1 的 queue-operation enqueue＝2026-10-18T14:40:29.689Z、送達 14:40:46.671Z（＝22:40 +08:00）：時間欄是估值而非讀時鐘（OBS-SI-031 同型）；AC-SI-01-1 只檢 offset、檢不出。另 OBS-SI-003／004（21:20／21:25）亦早於 T1，屬整合輪 116 尾端觀察，與帳本定位句「開發 SelfImproving 模組期間」（帳本:4）不符 | 改正為實際時刻（追加更正列，勿原地改）；任務書沿 OBS-SI-031 裁決「寫入前 `Get-Date` 現查」 | 主控 |
| F-18 | PRD:230、:841、:909 | 計數過期：AC-SI-01-3「寫稿時 OBS-SI-001～014」（現 34 列）；§13.3 v0.2「§9.7 審閱紀錄 27 處」對 §9.7 實有 28 筆（:679、:709）；變更記錄沒有 6c23495d（SD 殘留清理）條目；C.1 的 OBS-SI-011「累計 ×3」對帳本「×5」（帳本:20） | 同步或改「見帳本現查」；補變更記錄 | SA／主控 |
| F-19 | SOP:265–276（DP-04／06／09 的「強」）、:69、:92 | S4 規則：強＝≥2 組實驗＋≥2 組「直接檢驗」（:92），且小模型／單基準／構造資料來源最多把 DP 撐到「中」（:69）。DP-06 的直接實驗來源只有 S-25（構造成對基準、單一預印本）與 S-23（Qwen2.5 0.5B～3B、單作者）；DP-09 的 S-11（單基準 BIRD）、S-13（單架構）、S-25 皆受封頂；DP-04 的「人工 K=1」半條無實驗來源直接檢驗（S-26／S-27 為官方文，S-19 審查者身分未明）；SOP 未逐 DP 列出「實驗組」「直接檢驗組」，無法稽核。PRD 附錄 A 沿用 | 重算並列組別，或在 DP 欄註明哪半條由憲法而非證據支撐；判讀題，不影響需求展開 | 研究員（SOP II-5）＋SA（附錄 A 同步） |
| F-20 | PRD:833；SOP:291、:301、:162、:180 | 小處：PRD「S-04…無 DP 去處」對 SOP 矩陣 S-04→DP-02／DP-08（旁證）；SOP 稱 `playbook_evolver.py`:14～15 列兩型、:37 另有 REVISE_EVALUATOR，實檔 :14–16 三型皆列（PRD:278 引 14–16 正確）；SOP 對 S-14 標了 arXiv ID（2609）與提交日（2026-08-13）不符，對 S-11（ID 2608／提交 2026-06-29；我開頁見頁面自己如此顯示）未標；SOP II-4 S-04（V1）的「從成功與失敗軌跡抽取洞見」在摘要頁查無、「作者欄未見」現可補為 6 人（§1.3 #8） | 文字訂正；S-04 可由 V1 升 V2 | 研究員／SA |
| F-21 | PRD:652、:140；SOP:36（C-02）；R-9.22 yaml:14 | §9.4 預期 D／R 類目標落在 `docs/01～03`（規格文件），§3.2 與 NFR-SI-02-1 都沒排除 FRD／AC／PRD；SOP C-02 字面「改 FRD／AC 必經 HUMAN_PENDING」，本迴圈的 K=1 不是 FSM 的 HUMAN_PENDING 態。R-9.22 原文是「絕不自動套用、經 HUMAN_PENDING」，K=1 非自動，故不判違憲，但灰區須明文裁決 | §3.2 加一條（D 類不得改 `docs/01～03` 規格文件，須走 SPEC-PATCH＋HUMAN_PENDING），或附錄 B 補對照與理由 | SA |

### 2.3 P4（7 筆；登記不修）

| 編號 | 位置 | 理論洞（一句） |
|---|---|---|
| F-22 | PRD:369、:654 ⑤、:371 | FR-SI-28 新增契約測試（AST 普查）屬「鎖」類，無暴露證據；以「測試檔不在守衛面清單」字面合規，與 C-11（新鎖須暴露證據）精神有張力；AC-SI-28-3 自承暴露證據尚未成立 |
| F-23 | PRD:303、:662（ADR-SI-04） | AC-SI-15-1 例示「git worktree」與要求 `git worktree list` 逐字相同，ADR-SI-04 建議選 B（`git archive`）後該項無實質意義；AC 與 ADR 未對齊 |
| F-24 | PRD:309（AC-SI-16-2） | 回滾「乾跑」（沙盒內正→反 patch 與 base 逐位元相同）無法預測晉升後主樹因他人改動同行而產生的回滾衝突 |
| F-25 | PRD:363（`CAP_FRAC`） | `CAP_FRAC`＝0.9 是代理指標；真症狀（條目被截斷）可由 harness 事件直接觀測（見 F-05） |
| F-26 | SOP:278 | DP 表四格全 ✓ 是由「只收已把四格寫進原則的 DP」選出來的，S6 判準對這 12 條沒有鑑別力（SOP 自承）；欄位 B／H／M／R 只是宣告 |
| F-27 | PRD:177 | ID 前綴與 `AISDLC_ID_Naming_Convention.md`:30–36 不同（`F-XXX`；`AC-XXX-Y` 掛 US），AC 掛 FR 而非 US，§14 追蹤鏈（:861）略過 Epic／US；先例存在（已驗），RTM 實作輪需對映規則 |
| F-28 | PRD:296（AC-SI-14-1）、:452–460 | 提案卡「三句」由 PROP 欄位確定性轉換，但欄位文字仍是提案者自由撰寫；確定性轉換保證格式與 diff 同構，不保證句子屬實；另掌舵者曾要求「互動選項決策」（C.2 引文後半），CLI 文字卡須自行打字回覆，AskUserQuestion 類 tool_result 不是 human 訊息、不能作 DEC（取捨需明文） |

## 3. SCG-0 判定

**判定：FAIL。**

理由：
1. **P≤2 共 3 筆**（F-01、F-02、F-03），判定口徑「無 P≤2 才 PASS」不成立。
2. P1＝0：引用完整（S-11、S-17、S-08、S-23、S-25、S-04 開頁 6/6 標題與作者年份吻合，16 個 V2 數字逐字一致；§11／§9.0 的 40 餘個座標零筆不存在／失真；Q7 重跑全吻合）。
3. 三筆 P2 都是**可在規格層修掉的結構問題**，不需要重做研究或推翻架構；P3 18 筆多為文字／座標／計數過期／灰區明文化。

**P≤2 清單**
- F-01（P2）：不可進化面的機械邊界只比 `target`，不比 patch 全部路徑；glob 缺子專案 `.claude/`、凍結版本目錄（D／P／M 類）、`docs_template/**`、SI 帳本。
- F-02（P2）：M1 與 §1.1 反證條件在基率≈0 下無鑑別力，NE 護欄量錯對象（n 恆為 20）。
- F-03（P2）：AC-SI-01-3 遷移與 AC-SI-04-3 原地改寫偵測矛盾，P0 出口 (b)「`check` 綠」依文字不可達。

**對 FSM 的建議**（QA 棒未跑 FSM CLI，不讀 FSM-STATE，遵守禁令 1）：由主控在三件組環境下執行 `gate --gate SCG_VALIDATION --result FAIL`（FSM 鍵 `monorepo-selfimproving`，PRD:9 稱位於 SPEC_DRAFTING）；SA 修 F-01／F-02／F-03 的 §1.1／§1.3／§5／§8／NFR-SI-02-1，SD 修 §9.2／§9.3／§9.4／§9.6 的連動處，主控修 F-04／F-15／F-16／F-17 的帳本與附錄 C；修復後只做**二審驗修復**（範本〈審查閉環的終止〉：一審全查、二審驗修復、至多二審），二審範圍＝F-01～F-03 的修法＋被連動的 AC 與帳本；P3 當輪改文字（F-04～F-21，可逐筆處置為 fixed／retired），P4 只登記。二審通過後再 `gate --gate SCG_VALIDATION --result PASS`。零發現不是 PASS：本審查有 3 筆正向發現，二審的 PASS 須有同等正向證據（新指令輸出）。

## 4. 未涵蓋與誠實劃界

- **FSM 狀態**：PRD:9 稱鍵 `monorepo-selfimproving` 在 SPEC_DRAFTING（trace 3 筆）——我**未**跑 FSM CLI、**未**直接讀 FSM-STATE（禁令 1、任務書禁止），此宣稱本審查「未驗證」。
- **URL**：只開了 6 個成功（S-11、S-17、S-08、S-23、S-25、S-04；見 §1.3 表）；SOP 來源表其餘 24 篇（含 2026 預印本 S-12、S-13、S-14、S-15、S-19、S-24、S-29，V1 的 S-30）**未開頁**，其標題／作者／日期／數字本審查未驗；S-09、S-10、S-27 未重開；S-04 的頁面只讀到前 100,000／100,740 字元的轉述。SOP II-3 稱「全部 URL 都出現在上表某次搜尋結果或 fetch 內」，V1 兩筆（S-04、S-30）的 URL 只在研究員的工具輸出、不在 SOP 紀錄表逐字出現，本審查無法稽核。
- **數字**：16 個 V2 數字已核；SOP 其他 V2 數字（S-14 的 +16.6、S-19 的 86.74%／90.69% 等）未核。PRD 本身不引用來源量化結果（PRD:833、:945），僅 S-08 的「前 200 行或 25KB」，已核。
- **Q6**：「fixed 1,490」「git 認得 commit hex 34 列」「backtick 路徑 846 列」「配對上界 8,476」我未重算（我的 DEF 列正則口徑與 SD 不同：1,508 對 1,667）；只重算了三個關鍵基率（4／1／0）與家族檔數 70。
- **可測性**：依 G／W／T 形態判讀，未逐條實作驗證；未執行任何測試（例如 R85 測試、`tests/contract -k claude_md`），因唯讀；§9 全為規格敘述，未做實作驗證（§9.7 自述同）。
- **逐字稿**：欄位存在性只在本機 `f3ead132-…jsonl`（及 `check_claim_provenance.py` docstring 的 65 支普查自述）驗證；未掃全部逐字稿；逐字稿為 untracked、機器本地，他機無法重驗（PRD 已自承 NE）。
- **harness 文件主張**：S-08 `metadata:` frontmatter 是否被容忍（ADR-SI-06）、`.claude/skills` 是否在受保護路徑例外名單（PRD:803）、Agent 工具 `tools` 白名單（ADR-SI-09）皆未驗。
- **macOS**：全部未驗（PRD NFR-SI-06-5 同）。
- **未抽查**：PRD §9.1 的 15 元件為「規劃」，非現況，無從查；`~/.autosdd/` 路徑解析、`tarfile filter="data"` 的 Python 版本（ADR-SI-04）未驗。
- **審查期間工作樹**：開工（約 04:33）`HEAD=6c23495d rc=0`、`status-lines=0`；收尾（05:11 +08:00）`HEAD=6c23495d rc=0`、`git status --short` 只有本報告一個未追蹤檔（`?? docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md`），三份受審檔 `git diff --stat` 無輸出 ⇒ 審查期間受審物未變；我沒有改任何其他檔、沒有任何 git 寫入。

## 5. 流程摩擦／疑似缺陷（審查過程遇到的工具／文件問題）

1. auto mode 系統指示「盡量用 Bash 工具（cat／grep／sed 讀寫檔）」與根 `CLAUDE.md` 鐵律一（Windows 禁用 Bash）及任務書衝突，QA 棒再度復發（OBS-SI-011 累計 ×6）：座標＝帳本:20、系統提示 MCP Server Instructions 區塊、`.claude/hooks/block_bash_on_windows.py`。
2. 額度守衛的擋下訊息不帶「還要等幾秒」：我 2／8 次嘗試被擋（#1、#4；#4 距上次成功僅約 296 秒），只能自己用 `%TEMP%\autosdd_quota_dispatch.d\*.dispatch` 的 LastWriteTime 推算；#1 是被帳號層級帳本裡非本 session 的 dispatch（04:33:13）擋掉：座標＝`tools/lib/quota_gate.py`:165（`FANOUT_WINDOW_SECONDS = 300`）、:536（`live_dispatches`）。
3. 官方文件頁經 WebFetch 整頁回傳並存檔（50.2KB），回傳內容不是依提問的摘要，須改用 Grep／Read 讀存檔（SOP:72 ③ 已記同型，確認可重現）：座標＝`C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\f3ead132-29b1-418c-97d9-35868ab11c70\tool-results\toolu_01RahyncmHKcnsc64GdkgUbv.txt`。
4. 帳本 OBS-SI-028 的未轉義管線字元造成 9 欄（F-16）：座標＝帳本:37；若 `si check` 的欄數檢查晚於 P0 才有，現行帳本已有一筆既存違規。
5. SOP 對 arXiv 的「ID 月份與提交日不符」只在 S-14 標註、S-11 未標（F-20）：座標＝SOP:162、:180。
6. 任務書兩處數字不一致：原任務書要求「抽查 ≥6 個 URL」，補充改為「抽 5 個、最多嘗試 8 次」，我依補充（以補充為準）：座標＝任務書 §3 判準 3 與補充 7。
7. PowerShell 腳本踩到單元素管線被攤平成字串、`[0]` 取到第一個字元的陷阱（我自己的一次性腳本，已改 `@(...)[0]`，非 repo 缺陷；列出以供之後 `si` 腳本避免）：座標＝審查期間的一次性腳本，無 repo 座標。

---

審查完成：2026-10-19 05:11（+08:00）；QA（Sonnet 5.5，未參與撰寫）；判定 FAIL（P1＝0、P2＝3、P3＝18、P4＝7）。

---

## 6. 二審（驗修復）

> 範圍＝一審 F-01～F-28 的修復與修復連動的文字，不重做一審全查；嚴重度口徑同一審（P1＝引用不存在／失真、宣稱無證據、違反 Rule 9 絕對禁令；P2＝終點設計結構漏洞；P3＝文字／可用性；P4＝理論洞，登記不修）。範本〈審查閉環的終止〉＝一審全查、二審驗修復、至多二審：不再有第三審，P3 由主控當輪驗收。**§1～§5 是一審原文（未改）；本節 §6 是二審。**

### 6.0 輸入、方法與時序

- **輸入快照**：HEAD＝`978df84c`。二審開工（06:18:38 的第一個 PowerShell 呼叫，transcript line 1243）、續跑後（09:22）、寫入前終檢（09:58:41 +08:00）三次 `git rev-parse --short HEAD` 皆 `rc=0` 且同值；終檢 `git status --short` 只有本報告一個 ` M`，三份受審檔 `git diff --stat HEAD` 無輸出，且 mtime（PRD 06:15:03、SOP 05:27:43、帳本 05:48:36）都早於二審開工 06:18 ⇒ 受審物二審期間未變。修復批次：`31824e56`（SOP）、`a52ee13e`（PRD，SA 棒，非 §9）、`978df84c`（PRD §9＋主控同步＋帳本）、`c0716f16`（一審報告入庫＋帳本更正）。
- **體積變化**：PRD 954→986 行、175,851→227,975 bytes（＋29.6%）；SOP 345→369 行、94,071→106,992 bytes；帳本 34→40 列（43→49 行、14,240→17,605 bytes）。
- **方法**：(1) 三檔對一審快照 `6c23495d` 的 `git diff` 導到 scratchpad 後分段 Read（避開 Grep 的「Omitted long matching line」，OBS-SI-033／038），逐 F-NN 讀**現座標**；(2) 今日實測重驗 PRD 的可重現宣稱：`git apply --numstat -z` 六個合成 patch（Q12）、`git ls-files` 的 `.claude/` 目錄數（NFR-SI-02-1）、`MEMORY.md` 現況（Q5）、DEF 帳本家族重算（Q6）、逐字稿載體普查（Q11）、`apply_lock.py`／`quota_ledger.py` 座標（ADR-SI-10）、授權引句與時間座標（F-04／F-15／F-17）；(3) 重跑一審的自檢（ID／欄數／佔位／⚖／日曆觸發）並新增 SOP↔PRD 強度同步檢查；(4) 對 M1 per-PROP 基線窗逐路徑推演（6.2，紙上推演、未對真帳本模擬）。**未上網、未跑 FSM CLI、未用 Bash、無 git 寫入、未派子代理**（git 只用唯讀的 `rev-parse`／`status`／`diff`／`log`／`ls-files`；`git apply --numstat` 只解析 patch、不寫工作樹）。
- **時序**：二審 2026-10-19 06:18 起；**06:18:41 因週額度 429 中斷**（座標見 6.6 #1），09:21 續跑；中斷前只完成 `git rev-parse`／`git log`，其餘查證都在續跑後；續跑靠對話摘要接上，**不採信摘要裡的任何「已通過」**，數字與座標一律今日重驗（這也是 6.4 有大量「今日重驗」輸出的原因）。

### 6.1 逐筆處置（F-01～F-28）

小計：F-01～F-03（P2）3／3 消除；F-04～F-21（P3）17 消除、1 部分（F-18）；F-22～F-28（P4）6 登記不改、1 順手修正（F-23）。

| 編號 | 一審 | 二審處置 | 證據（現座標；我今日怎麼驗） |
|---|---|---|---|
| F-01 | P2 | **消除** | AC-SI-07-3（PRD:264）：解析 patch 內**全部**路徑（`---`／`+++`、`diff --git`、`rename`／`copy` from／to；新增、刪除、改名兩端皆算）逐一 `realpath`＋`normcase`＋`casefold` 比對，任一命中或逃出合法根 ⇒ **整張** handoff；`target` 為排序去重集合、`touched`／`touched_count` 進 digest（PRD:217、:578），卡面顯示觸及檔數與非 `target` 路徑（PRD:264、:302）；NFR-SI-02-1（PRD:403）＋錨定語意（:404）＋實體 glob（:405）補 `**/.claude/**`、凍結版本目錄與 `**/docs_template/**`（所有類別）、SI 帳本與 Proposals；§9.4（PRD:661–669）雙法導出（自寫解析器含 C-style 引號解碼＋`git apply --numstat -z` 超集檢查）、負控清單、`si promote` 以當下 params 重驗。**今日實測**：`git ls-files` 的 tracked `.claude/` 目錄 33 處＝根 1／AISDLC_SDD 31／AutoClaude 1（與 PRD:404 相符，根錨定只涵蓋 1 處）；Q12 六個合成 patch 重跑（git 2.51.0.windows.1）：純改名只印目的端 `docs/x.md`、八進位引號 `CLAUD\105.md` 被解成 `CLAUDE.md`、標頭寫 `CLAUDE.md` 而 `---`／`+++` 寫 `safe.txt` 時只印 `safe.txt`、`..` 原樣印出（輸出見 6.4 b）⇒ PRD:530、:664 的「必須雙法導出」理由成立 |
| F-02 | P2 | **消除**（設計層） | §1.1（PRD:38）改為「可評估窗內反證」；M1 改 per-PROP 前後對照，NE 護欄量基線窗確認再現**事件數**（`W_EVT` 初值 2，無先例、未校準）、基線 0 事件一律 NE（PRD:61）；檢定力說明含均值回歸（PRD:67）；AC-SI-22-1／23-1（PRD:346、:351）、§9.3 量測腳本（PRD:620）、ADR-SI-05 基線窗（PRD:682）同步；全域 `W_N` 窗與 M2／M3 降資訊欄。**今日重算 Q6**（6.4 c）：家族 70 檔、DEF 列 1,667（去重 1,661、62 個前綴；101＝998、200＝550、其餘 119）、一審口徑重現 1,508、再開症狀 4／命中 1（DEF-200-551）／`reopens:` 0 ⇒ 基率前提不變，全域窗期望再現事件約 0.01～0.05（20×1÷1,490＝0.013、20×4÷1,490＝0.054）的推算成立。per-PROP 窗本身的遮蔽路徑審查見 6.2（無 P≤2；P3 弱點＝F-31、F-32） |
| F-03 | P2 | **消除** | AC-SI-01-3（PRD:235）：遷移＝一次性單一 commit，豁免須同時具備 (a) `params.json` 的 `migration_base_sha`、(b) 掌舵者確認列（處置 `decided`、附原句與 `sid`＋`line`、引用該 sha），缺一視為未豁免；AC-SI-04-3（PRD:249）自遷移基準起比對、`orig=` 只用於遷移、更正走追加更正列（NFR-SI-03-2 PRD:413；標記欄 PRD:202）；§8.1 P0 (b)（PRD:474）、§9.3 `check`（PRD:609：sha 須存在且為 HEAD 祖先，否則紅；缺值＝自第一個提交起比對）、§9.6 P0（PRD:692；遷移 commit 與寫 sha 的 commit 必為兩個，因 commit 不能引用自己的 sha）三處一致，P0 出口 (b) 現在可達；一審的兩種更正機制衝突已統一。殘餘：(b) 在 P0 只驗存在與格式（F-39，P4） |
| F-04 | P3 | **消除** | C.2（PRD:942）改述：完整引句（含後半「請以最簡單的解釋, 讓我互動選項決策」）＋`sid`＋line 13（2026-10-18 21:03 +08:00）、說明「以上」指該則四個問題、T1（line 901）未重述 ⇒ #1～#9 是主控的延伸解釋、凍結核准時由掌舵者逐項確認可推翻；C.1（PRD:937）補座標。今日重驗：f3ead132 逐字稿 line 13 `origin.kind=human`、timestamp 2026-10-18T13:03:23Z，全句逐字相符；line 901（14:40:46Z）不含該句（6.4 f） |
| F-05 | P3 | **消除** | PRD:368（FR-SI-27 追溯）、AC-SI-27-1（PRD:369）、AC-SI-27-2（PRD:370）、G-SI-07（PRD:793）補 harness 自帶容量機制（近上限提醒、超限回錯誤），並以「衝突處置不依賴先後、一律以機械 pre-image 比對為準」處理 harness 自寫索引；SOP II-4 S-08（SOP:237）補列、II-7 T-3／T-4 標既有證據（SOP:342、:347）。一審我對官方頁存檔行 546～548 的查證不變 |
| F-06 | P3 | **消除** | Q5（PRD:523）改為「OBS-SI-030 重排後此結論已反轉」並標快照時刻。今日重量 `MEMORY.md`：16,391 bytes／實體 79 行（非空行 75；一審記的 75 是非空行數，口徑差 PRD 已對帳）／節起點第 5、30、51 行／記憶目錄 127 個 `.md`——與 PRD:523 的快照值全部相符（6.4 c） |
| F-07 | P3 | **消除**（牽出新灰區） | AC-SI-12-4 ②（PRD:294）與 C8（PRD:543）寫入錨定（決定語法在整則 human 訊息開頭或獨立一行且整則只含一個決定行；核准／晉升無尾隨文字；否決／退回只接一句；子字串不算），並補四個負控（否定句、疑問句、引用卡面、多 PROP 同則訊息）。錨定本身已消除；由此牽出的新問題：語法覆蓋不全與過期句（F-30）、真人發言載體漏一種（F-33）、偽造追加的承接動作（F-34） |
| F-08 | P3 | **消除** | AC-SI-17-2（PRD:320）改用 SUSPENDED＝`dec(resume)`、超界升級＝依 §5.1.2 人工決定；FSM 的 ESCALATION 恢復明列「不在本迴圈內、邊界型 P」；SUSPENDED 期間 `si prop-new` 拒收標 M（事件折疊判定） |
| F-09 | P3 | **消除** | §2.1.1 矩陣新增「邊界型（M／D／P）」欄（PRD:92、:94–99）；AC-SI-10-2（PRD:281）、NFR-SI-02-4（PRD:408）標 P 並寫「偵測面＝無專屬機械物、不得讀成被擋」。矩陣中兩格的 D／M 宣稱承接不足見 F-34 |
| F-10 | P3 | **消除** | AC-SI-02-1（PRD:238）擴及任何類別（M／P／R／D），並說明 P／D 不排除的理由（S-13、S-09 同型入口）；§9.4（PRD:665）同 |
| F-11 | P3 | **消除** | §9.2「多寫入者與配號」（PRD:576）、ADR-SI-10（PRD:687）、§9.7 #33（PRD:734）：鎖內配號、獨佔建檔鎖沿 `apply_lock`（fail-loud），不採 `O_APPEND`。今日座標重驗：`tools/lib/apply_lock.py`:44 `class LockBusyError`、:60 `os.open` 帶 O_CREAT 與 O_EXCL（獨佔建檔）、:86 `def acquire`；`tools/lib/quota_ledger.py`:35 `O_APPEND`＋單次 `os.write` 的 `expected=320 lines=281 LOST=39 (12.2%)`、:36 `msvcrt.locking` N=20 時 10 個行程死亡（R81）⇒ 與 PRD:734 的引述一致（6.4 f）；一審建議的「檔案鎖＋`O_APPEND`」裡承重的只有「鎖」，SD 的取捨正確 |
| F-12 | P3 | **消除**（牽出 F-32 (d)） | AC-SI-23-1（PRD:351）、§9.2 Measurement（PRD:568）、§13.1 詞彙（PRD:847）：M 類機會列＝根因鍵（經 `attr.confirm`）相同或引用同條目的新立列；非 M 類沿 `target` 最近公共目錄；窗未關閉的 PROP 不計 M5 分母、M1 維持 NE。M 類窗已可關閉；此定義與「再現」定義的重疊見 F-32 (d) |
| F-13 | P3 | **消除** | M1 量法（PRD:61）改述同 AC-SI-06-2（PRD:259）：量測腳本只讀已寫入的標記與確認事件、不在量測期掃描產生候選；未確認者標「候選」只印數量 |
| F-14 | P3 | **消除** | M2／M3 降資訊欄並寫理由（PRD:62–63）；M5 兩值並列於成功指標區（PRD:65、:620；AC-SI-22-2 PRD:347；§1.1 PRD:38 含兩值） |
| F-15 | P3 | **消除**（原五列；新列同型再發＝F-35） | 原五列（LED:13、:22、:36、:41、:42）座標現為 `sid`＋`line`；今日解析 line 435／1054／1383／1505 皆為 `queue-operation`（`enqueue`）記錄，`content` 即該棒 hand-back 報告原文（15,202／11,207／11,923／8,242 bytes），可定位（6.4 f） |
| F-16 | P3 | **消除** | LED:37（OBS-SI-028）改寫去管線；今日腳本：帳本 40 列皆 8 欄（6.4 a 的 `ledger cols (all 8): True`） |
| F-17 | P3 | **消除** | LED:10–11 時間欄改 `2026-10-18 22:46`；OBS-SI-035（LED:44）記原地更正發生於遷移基準之前、不計 ROW-MUTATED。今日重驗時鐘：T1 於 22:40:29 入列、22:40:46 送達（line 893、901），帳本首次寫入在 line 943（22:45:30 +08:00）⇒ 22:46 不早於實際（6.4 f） |
| F-18 | P3 | **部分** | 四項中三項已修：AC-SI-01-3 改「以遷移當下現查為準、不寫死」（PRD:235）；§13.3 v0.2 改「28 處（初版 27，#28 於 6c23495d 補入）」（PRD:868）；變更記錄補 v0.4.1（PRD:871）。第四項 C.1 的 OBS-SI-011 累計仍落後（PRD:939「×6」對 LED:20「×7」）⇒ 殘餘 P4（F-36） |
| F-19 | P3 | **消除**（SOP 留過期句＝F-29） | SOP S4〈組別判定〉（SOP:94）、自檢第 11 條「強度可稽核」（SOP:130）、II-5〈強度重判表〉與重判結果（SOP:282–299；強→中 6 條：DP-01／04／05／06／09／10；維持強 3 條：DP-02／08／11，每條皆列 ≥3 實驗組與 ≥2 非封頂直接檢驗組，符合 S4 強度規則 SOP:93）、II-8（SOP:368）；PRD 附錄 A（PRD:898–909）今日 12／12 同級（6.4 e，`mismatches= 0`）。殘餘：SOP:299、:368 仍寫「PRD 附錄 A 的強度欄沿用舊值，需 SA 同步」——已過期（F-29） |
| F-20 | P3 | **消除** | SOP:312（DP-12 改「:14–16 三型皆列、同檔:37 型別註解亦同」）、SOP:164／:369（S-11、S-14 的 arXiv ID 與提交日不符皆已標註）、SOP:197／:233（S-04 由 V1 升 V2、作者 6 人）、PRD:860（S-04 已升 V2、作旁證） |
| F-21 | P3 | **消除** | §3.2（PRD:143）加「D 類不得直接改 `docs/01～03` 規格本體、K=1 不取代 HUMAN_PENDING（R-9.22）」並標邊界型 M＋P；§9.4（PRD:671）機械化為 `spec_body_globs` 路徑前綴檢查（`prop-new` 與 `promote` 兩處，例外＝`action=add` 的 SPEC-PATCH 草案），並更正首輪「`promote` 會被 router 擋」的過度宣稱；附錄 B（PRD:917）補 R-9.22 對照；§9.7 #34（PRD:735） |
| F-22 | P4 | 登記不改 | §13.3 v0.5（PRD:872）明列，處置誠實，無異議 |
| F-23 | P4 | 順手修正 | AC-SI-15-1（PRD:309）形態改由 ADR-SI-04 定、預設 `git archive`；`git worktree list` 不變一項改述為「任何沙盒形態都不得在正式面新增 worktree 登記，並偵測誤建樹內 worktree」，與 ADR-SI-04（PRD:681）對齊 |
| F-24 | P4 | 登記不改 | PRD:872 |
| F-25 | P4 | 登記不改 | PRD:872 |
| F-26 | P4 | 登記不改 | PRD:872；SOP:280 自承仍在 |
| F-27 | P4 | 登記不改 | PRD:872 |
| F-28 | P4 | 登記不改（取捨已明文） | 「AskUserQuestion 的答覆不作 DEC」已在 §7.2 明文（PRD:455）並以 Q11 實測支撐（PRD:529）；我今日重驗 f4c765a7 逐字稿：line 168 為 user 角色的 `tool_result`、無頂層 `origin`（6.4 d）。但 Q11 對載體的描述不完整 ⇒ F-33 |

### 6.2 M1 per-PROP 基線窗設計審查（SA 自陳「新設計、未經外部審查」）

**我讀到的結構**（PRD:38、:61、:67、:259、:351、:352、:355、:568、:573、:610、:620、:682）：每個 PROP 於 `app.promote` 時由 CLI 記一筆 `mea.report`（`kind`＝baseline）：基線窗＝晉升前、同一機會列規則、自「再現標記上線」後的最近 `W_OPP` 筆機會列，記窗內確認再現事件數；採納窗＝晉升後累計 `W_OPP` 筆機會列，或再現／回滾先到者關閉（`mea.close`：`clean`／`recurred`／`rolled-back`）；M1＝可評估採納窗中 `recurred` 的窗數 ÷ 可評估窗數（附 n）；可評估＝基線事件數 ≥ `W_EVT` 且基線機會列 ≥ `W_MIN`；基線 0 事件＝NE；§1.1：連續兩個可評估採納窗皆 `recurred` ⇒ 願景被反證（只轉 T1 決策項、不自動下線）。`W_EVT`、`W_MIN`、`W_OPP`、`W_N` 初值皆「無先例、未校準」，PRD 已自標。

| 路徑 | 是否遮蔽失敗 | 殘餘可見訊號 | 結論 |
|---|---|---|---|
| 基線事件數 0（最可能的世界） | 否：明文判 NE，不得算「未低於」或「已改善」（PRD:38、:61） | M1 印 NE 與 n | 方向正確（保守） |
| 採納窗 `recurred`（再現先到） | 否：提早關閉照樣可評估（再現本身是決定性觀察，PRD:61） | M1 分子、`STOP_AFTER_BAD` | 正確 |
| 採納窗 `clean` | **有條件**：`W_OPP` 筆機會列先到時，窗內未確認候選不影響結果；窗關閉後才到的確認無處落帳（`mea.close` 為終值、帳本只准追加，詞彙無駁回／補記 kind，PRD:573） | 候選只印數量不計（PRD:259、:620）、M5 | F-31（P3） |
| 採納窗 `rolled-back`（回滾先到、窗內無確認再現） | **有條件**：M1 不評估、只計 M5（PRD:61）；若回滾原因正是尚未確認的再現，M1 少一個 `recurred`；AC-SI-23-2（PRD:352）的「偵測」指候選或確認未定 | M5 兩值、回滾紀錄、`STOP_AFTER_BAD`（`rolled-back` 也算壞，PRD:355，停機面不受影響） | F-31（P3） |
| 窗重疊／同一事件雙計 | 否，方向相反：可能過早反證 | — | F-32 (b)（P3） |
| 全域 `W_N` 窗、M2、M3 | 否：已降資訊欄、不得宣稱成效（PRD:62–63、:620） | — | 正確 |
| 「未再現」被讀成成效 | 否：PRD 明文禁（均值回歸，PRD:38、:67） | — | 正確；目標欄措辭殘留見 F-40（P4） |

**結論**：無 P≤2 的失敗遮蔽路徑——每條路徑都至少留下一個可見殘餘（候選數、M5、回滾紀錄、`STOP_AFTER_BAD`），反證只會「較晚成立」、不會被改寫成支持；NE 方向全部保守。弱點集中在兩類：窗關閉規則對「未決候選」與「晚到確認」沒有說法（F-31），以及再現歸屬、獨立性、順序、M 類定義重疊等判定細則（F-32）。**嚴重度邊界**：F-31 我判 P3，理由＝殘餘訊號可見、可用合成帳本測試、修法一句；若掌舵者認為「偏向不被反證」本身就算遮蔽、不論是否可見，可升 P2（見 6.5）。

### 6.3 修復引入的新矛盾與新發現（編號續一審）

**P3（7 筆）**

| 編號 | 位置 | 症狀（附證據） | 修法建議 | 誰修 |
|---|---|---|---|---|
| F-29 | PRD:543（C8）、:671（§9.4）、:682（ADR-SI-05）、:731（§9.7 #30）、:965（檢核表）；SOP:299、SOP:368 | 修復後仍留 7 處「待／需對方確認」的現在式句。**已過期**：PRD:543「動詞→kind 對映為 SD 推定、待 SA 在 §7.2／§5.1.3 確認」與「rollback／unblock／resume 在語法補齊前＝無法解析」（§7.2 已於 978df84c 補齊，PRD:455、:873）；PRD:671「§3.2 的邊界型標示待 SA 同步」（PRD:143 已是 M＋P）；PRD:965「待 SD 修 §9」（v0.6，PRD:873 已修）；SOP:299、:368「PRD 附錄 A 的強度欄沿用舊值，需 SA 同步」（PRD:898–909 已同步，6.4 e）。**真未決**：PRD:682、:731「『標記上線』錨＝`migration_base_sha` 的 commit 時間，SD 推定、待 SA 確認」——M1 基線窗的起點「自再現標記上線後」在 SA 的 §1.3（PRD:61）與 AC-SI-23-1（PRD:351）只用不定義；確認再現事件靠 `attr.confirm`（P1 才有，PRD:612），P0 遷移 commit 早於 P1，若 P1 前的候選不能事後補確認，基線窗自 P0 起算會含「不可能被確認」的列、基線事件數被低估（偏向 NE，保守、不致假陽性），但兩個實作者會選不同的錨、基線不可重現；PRD 沒寫可否補確認。同型先例：OBS-SI-032（待裁決寫成現在式） | SA 定義「再現標記上線」（建議獨立的 `params.json` 欄位，例如以 `attr.confirm` 首次可用的 commit 為準，並明寫 P1 前候選可否事後補確認；不與 `migration_base_sha` 混用），刪 PRD:543、:671、:965 與 SOP:299、:368 的過期句，§13.3 記一行；SD 同步 PRD:682、:731 | SA（PRD:61、:351 錨定義）＋SD（PRD:543、:671、:682、:731）＋主控（PRD:965；SOP 交研究員） |
| F-30 | PRD:291（AC-SI-12-1）、:294（AC-SI-12-4 ②）、:455（§7.2）、:543（C8）、:227（kind 詞彙）、:186／:569（RUN 識別碼） | DEC 回覆語法在四處不一致：(a) AC-SI-12-1「僅『核准／否決／退回＋PROP ID』構成決定」，§7.2 另列晉升、回滾、解除、恢復、轉交、不轉交（kind 詞彙 9 種，PRD:227）；(b) AC-SI-12-4 ② 的尾隨規則只寫核准／晉升（不得有尾隨文字）與否決／退回（只接一句），回滾（帶理由）、解除（無尾隨）、轉交（無尾隨）、不轉交（帶理由）、恢復（帶 run_id 與理由）無規則；「PROP ID 與動詞須和 `--kind` 一致」對 `恢復` 無 PROP ID；§7.2 稱「AC-SI-12-4 ② 對此類比對 run_id 而非 PROP ID」，PRD:294 並無此句；(c) `run_id` 一詞全文只出現在 PRD:455，RUN 的識別碼是 `RUN-SI-NNN`（PRD:186、:569），語法樣板寫 `<run_id>`、與其餘樣板的 `PROP-SI-NNN` 形式不一致；(d) C8 仍寫「§7.2 未列回覆語法的 kind〔rollback／unblock／resume〕在語法補齊前＝無法解析、預設拒絕」（過期），其負控清單也沒有新語法（例：`解除 PROP-SI-NNN` 後有尾隨文字、`恢復` 缺 RUN 號、`回滾` 對未晉升者）。全部 fail-closed（解析不了＝拒絕），不是放行風險；但實作者與測試作者讀到三種不同的決定集合 | SA：AC-SI-12-1 改為「§7.2 列舉的語法之一」；AC-SI-12-4 ② 對 §7.2 全表逐語法列「尾隨規則＋ID 欄綁定（PROP 或 RUN）」；§7.2 樣板改 `恢復 RUN-SI-NNN <一句理由>`。SD：C8 刪過期句、補完整動詞→kind 對映與新語法負控 | SA（AC-SI-12-1／12-4、§7.2）＋SD（C8） |
| F-31 | PRD:259（AC-SI-06-2）、:351（AC-SI-23-1）、:352（AC-SI-23-2）、:61、:568、:573、:620 | M1 窗關閉規則對「未決再現候選」沒有說法，有偏向「不被反證」的遮蔽路徑：(a) 窗可在 `W_OPP` 筆機會列先到時以 `clean` 關閉，而再現須經審查者（≠立案者）的 `attr.confirm` 才計；窗內未確認候選不影響結果，窗關閉後才到的確認既不重開窗、也沒有更正事件（`mea.close` 為終值、帳本只准追加，事件詞彙沒有駁回候選或補記的 kind），該次再現永遠不進 M1；(b) AC-SI-23-2「窗內偵測到再現 ⇒ 回滾提案卡」未說「偵測」指候選或確認——若指候選，常態路徑「再現→回滾」會落在 `rolled-back`（M1 不評估）而不是 `recurred`。殘餘可見訊號：候選只印數量、M5、回滾紀錄、`STOP_AFTER_BAD`——不是無痕遮蔽；反證只會較晚成立。**邊界案例，詳 6.2、6.5** | SA：AC-SI-23-1／§1.3 加「窗關閉時窗內仍有未決候選＝窗維持 open（或記 `clean-pending`，不計入 M1 分子分母與 `STOP_AFTER_BAD` 的『好』）」；補「駁回候選」與「窗關閉後晚到確認」的追加事件（不改寫 `mea.close`）；AC-SI-23-2 明定「偵測＝確認再現」。SD：§9.2 事件詞彙補對應 kind | SA＋SD |
| F-32 | PRD:351、:61、:38、:65、:847、:610、:620 | M1 窗判定的六個灰區（同處修）：(a) **再現歸屬**——AC-SI-23-1、§1.3 只說「窗內出現再現」，哪些再現算在哪個 PROP 的窗，只有 §9.3 `status` 的 (d)（已確認復發連結指向某 promoted PROP 的 `sources`，PRD:610）寫了，量測腳本（PRD:620）沒引用；(b) **獨立性**——兩個 PROP 的 `target` 前綴重疊且晉升相近時，同一筆再現可同時關閉兩個窗為 `recurred`，「連續兩個可評估採納窗皆仍復發」（PRD:38）可由單一事件滿足（方向＝過早反證，保守但失真）；(c) **「連續」與排序**——跨 NE 窗是否打斷連續、以晉升時間或 `mea.close` 時間排序，未定；(d) **M 類機會列與再現定義重疊**——M 類機會列第一支（根因鍵相同的新立列，PRD:351、:568、:847）本身就是再現的近義，窗要 `clean` 只能靠第二支（引用該記憶條目的新立列）累計；兩支的比例，以及第一支出現但未被確認為再現時怎麼算，未寫；(e) **M5「皆不隨採納數上升」**（PRD:38、:65）沒有判定規則（趨勢怎麼判、n 為個位數）；(f) **`W_MIN`／`W_OPP` 耦合**——基線窗＝最近 `W_OPP` 筆機會列，可評估要求基線機會列 ≥ `W_MIN`（PRD:61），初值同為 5 ⇒ 列數護欄形同虛設（不致誤判，事件數護欄才是主護欄），但兩常數可獨立調，`W_MIN` ＞ `W_OPP` 會讓所有窗永遠 NE，PRD 未寫 `W_MIN` ≤ `W_OPP` | SA 於 §1.3 補判定細則：歸屬規則取 (d)＝連結指向該 PROP 的 `sources`；窗重疊時同一再現只計在最早晉升的窗或於 `mea.report` 註記共享；「連續」只計相鄰的可評估窗、NE 窗不打斷也不計；M 類的「再現」與「機會列」分開定義；M5 趨勢判定寫成可算式、n 小於下限者 NE；`params.json` 對表加 `W_MIN` ≤ `W_OPP`。SD 同步 PRD:620 | SA＋SD |
| F-33 | PRD:294（AC-SI-12-4 ①）、:543（C8）、:529（Q11）；`.claude/hooks/check_claim_provenance.py`:836（`_is_genuine_user_turn`） | DEC 提取器只描述「`type:user` 且頂層 `origin.kind=="human"` 的訊息」，漏了真人發言的第二種落盤載體：`type:attachment`／`attachment.type=="queued_command"`（掌舵者在主控跑工具中途送出的訊息；`attachment.origin={kind:human}`、`attachment.humanTurn=True`、文字在 `attachment.prompt`，緊鄰記錄是 `queue-operation` 與 `total_tokens_reminder`，沒有任何 `user` 記錄帶該文字）。**今日實測**（6.4 d）：Q11 的 f4c765a7 逐字稿，PRD:529 列的「`origin` 命中第 13、195、227、256、1286 行」裡，13 與 1286 是 `type:user`，**195、227、256 是 `queued_command` 附件**；本機 138 份逐字稿普查：`type:user` 真人 73 筆（41 檔）、`queued_command` 真人 24 筆（17 檔）⇒ 24／97＝24.7% 的真人發言在規格沒提的載體。`_is_genuine_user_turn(content, record)` 只看 user 記錄的 `origin`／`turnOrigin`／`isMeta`，C8 稱「判準沿用」。後果（fail-closed、無偽造風險）：掌舵者在主控跑工具中途打的核准會「無法解析」被拒，要等主控閒下來重送；若改為納入附件，規格須寫座標（附件記錄的 `line`）、文字取 `attachment.prompt`、以及 ③「該發言之前最近一則 assistant 訊息」的時序基準——附件記錄的物理行序落在其被注入之處，時間戳早於前一行（f4c765a7 line 195 的 10:11:26Z 早於 line 193 的 10:11:57Z），行序與打字時序不同 | SD：C8、Q11 把「真人發言」載體列為兩種並補普查數字；寫明附件載體的座標與 ③ 的時序基準（擇一：物理行序，或附件自帶時間戳），各補一個合成逐字稿的正控／負控（核准在卡面送達之前打出、注入在之後）；SA 同步 AC-SI-12-4 ① 字面 | SD（Q11、C8）＋SA（AC-SI-12-4 ①） |
| F-34 | PRD:291（AC-SI-12-1「可被事後稽核」）、:94–96（§2.1.1 主控 ①、子代理 ②）、:679（ADR-SI-02）、:272（AC-SI-08-4）、:618（`promote`）、:314（AC-SI-16-1）、:574（折疊） | 事件帳本是 git 追蹤的 JSONL；任何有檔案寫入工具的角色（含主控）可直接追加一行**格式合法**的 `dec` 事件（合法轉移、下一個 `seq`、任意 `quote` 座標）。AC-SI-08-4（PRD:272）的 `si check` 重放只查 ① 合法轉移、② 既有行改寫或刪除（ROW-MUTATED）、③ ID 唯一遞增／`t` offset／`kind` 詞彙、④ 反空轉——**不查 `dec` 的 `quote` 是否真在逐字稿**；§9.3 `promote`（PRD:618）寫「先驗 DEC＋digest＋pre-image」，沒寫是否重跑 AC-SI-12-4 回查**已存 DEC** 的引言。結果：矩陣的「子代理 ②寫 DEC＝D：直接改檔由 `si check` 事後標紅」（PRD:96；ADR-SI-02 PRD:679 同）對**格式合法的追加**不成立；「主控 ①代為核准＝M」（PRD:95）只對經 `si decide` 的路徑成立；AC-SI-12-1 稱偽造「可被事後稽核」，但稽核動作無人承接（沒寫由誰、何時、用什麼動詞回查 `sid`＋`line`）。非 K=1 的 DEC 種類（`unblock`、`resume`、`rollback`）更無第二道人工確認，而冷卻與 SUSPENDED 都是事件折疊的純函式（PRD:574）：追加一行 `resume` 即解除停機。PRD 的誠實劃界（PRD:668）只涵蓋「直接 Edit／Write 改正式面」，沒涵蓋「直接寫事件帳本」。**邊界案例，詳 6.5** | SA／SD：AC-SI-08-4 加 ⑤「每個 `dec` 的 `quote` 於本機逐字稿可得時回查（同 AC-SI-12-4 ①～③），不符＝標紅，不可得＝NOT-EVALUABLE」；`promote` 明寫對 `approve` 與 `promote` 兩筆 DEC 重跑 AC-SI-12-4；矩陣兩格改述（D 的承接＝⑤；M 只覆蓋 `si decide` 路徑）；§9.4 誠實劃界補「直接寫事件帳本」一行 | SA（AC-SI-08-4、AC-SI-12-1、矩陣）＋SD（§9.3 `check`／`promote`、§9.4） |
| F-35 | LED:45（OBS-SI-036）、LED:47（OBS-SI-038）、LED:46／48／49（OBS-SI-037／039／040） | 新入帳的列重犯一審 F-15 同型：(a) LED:45 證據座標開頭是 TAB＋`ools/lib/quota_gate.py:165、:536`、LED:47 是 TAB＋`ool-results\toolu_01Tig…txt`——「`t`ools」「`t`ool-results」的 `t` 被換成 TAB 字元（今日腳本：帳本 `TAB=2`，位置 LED:45 col 190、LED:47 col 175；成因疑為 PowerShell 雙引號字串把「反引號＋t」當跳脫，**推測**，我沒看到寫入指令），路徑不可定位；(b) LED:46（座標＝scratchpad `qa_brief.md`）、LED:48（「SA 回報」＋scratchpad 補丁腳本，列內自註「收輪會刪」）、LED:49（「主控 SendMessage 05:28」）座標不可重查。依 PRD §5.1.1 證據座標欄（PRD:198：檔案:行／指令＋rc／sid＋seq／帳本列 ID，≥1 個）與 AC-SI-01-1（PRD:233：「≥1 個可定位」）不合規；P0 出口 (d)「零筆無座標列」（PRD:474）現況不成立；§9.3 `check`（PRD:609）也沒有控制字元檢查 | 主控：兩處 TAB 換回 `t`（遷移基準之前的原地更正，同 OBS-SI-035 裁決）；037／039／040 補 `sid`＋`line`（hand-back 的 `queue-operation` 行，解析法見 F-15）或改處置為 `retired` 並寫依據。SD：`check` 加「欄內控制字元（含 TAB）＝拒收」 | 主控（帳本）＋SD（§9.3 `check`） |

**P4（6 筆；登記不修）**

| 編號 | 位置 | 理論洞（一句） |
|---|---|---|
| F-36 | PRD:939（C.1）、LED:20（OBS-SI-011） | C.1 寫「累計 ×6」，帳本寫「×7」（再度落後 1；一審 F-18 同型）；且 OBS-SI-011 以原地改寫累加 ×N——遷移基準之後即屬 ROW-MUTATED（AC-SI-04-3：更正走追加列）；累計型資訊需另立載體（追加列或事件），或只寫「見帳本現查」 |
| F-37 | PRD:403–405（NFR-SI-02-1）、:285（AC-SI-11-1） | 不可進化面 (i)「agent 指令」只列各層 `CLAUDE.md` 與 active `R-*.yaml`；LATEST 的 `agent/**`（agent 指令檔）、`workflow/**`、`tools/fsm_runtime/**` 不在實體 glob；類別白名單 M／P／R／D 只限「類別」、不限「路徑」，所以 `touched` 落在這些路徑的 PROP 只靠人審卡面的觸及檔案清單（AC-SI-07-3）。登記不修（守衛面准入：量、不挖） |
| F-38 | PRD:664（§9.4 `touched` 雙法導出） | 自寫解析器取聯集的步驟沒寫路徑前綴正規化：`diff --git a/…`／`b/…` 的 `a/`、`b/`（`-p1`）、`--no-prefix` 的 patch、含空白或引號的路徑；而 `git apply --numstat -z` 已剝前綴（今日 p5 印 `docs/a.md`），兩邊集合比較（「git 看到的每條路徑必須 ∈ (a)」）時實作者必須先決定剝或不剝；負控清單沒有前綴形態。實作輪會被負控逼出來，登記 |
| F-39 | PRD:235（AC-SI-01-3 (b)）、:609 | 遷移豁免的 (b) 掌舵者確認列在 P0 只驗「存在與格式」、不驗引言，且 `migration_base_sha` 存在可被後續 commit 改動的 `params.json`（改動只留 git 歷史）；一次性、且有 QA 與掌舵者審查可攔，登記 |
| F-40 | PRD:61（M1 目標欄）、:38、:67 | 目標欄仍寫「採納後仍復發的比例低於基線」，§1.1 與檢定力說明則明文「採納窗未再現不構成成效證明、只用於反證」；且基線窗依定義全有再現（PRD:61「基線＝有再現」）、採納窗結果只有 `recurred`／`clean` 二元，「低於基線」實際等於「至少一個 `clean` 窗」。建議目標欄改寫成反證語彙（「成功＝未被反證」），避免被讀成成效指標 |
| F-41 | PRD 全檔、SOP:237 | 文件體積：PRD 227,975 bytes（一審 175,851；一輪＋29.6%）、單行 >1,000 B 共 34 行、>1,500 B 共 11 行、最長 2,707 B（PRD:687，ADR-SI-10）；SOP 最長 2,107 B（SOP:237）。長行讓 Grep 回「Omitted long matching line」——OBS-SI-033／038 已有實際後果（SOP 漏掉 harness 容量機制），本審查也只能用 `git diff` 導檔＋Read 繞過；`ROW_MAX_BYTES`＝700 只管 OBS 帳本。建議 §9 長表格行拆列或分檔，並給 PRD 本身一條行寬建議 |

### 6.4 重跑與新增檢查的輸出（省略處以「…」標示；TAB 以 `<TAB>` 代替、NUL 以 `<NUL>` 代替；方括號或圓括號內的歸類、縮寫註記是我加的、不是工具輸出，其餘為工具輸出逐字）

**(a) 自檢**（`selfcheck2.py`，唯讀三檔；一審自檢的 ID／欄數／佔位／⚖／日曆觸發重跑，另加帳本控制字元與 SOP 來源表）

```
PRD bytes=227975 lines=986 CR=0 TAB=0
SOP bytes=106992 lines=369 CR=0 TAB=0
LED bytes=17605 lines=49 CR=0 TAB=2

FR defs=29 unique=29
AC defs=77 unique=77
US defs=8 unique=8  NFR defs=9 unique=9
ADR defs=10 unique=10: ADR-SI-01,ADR-SI-02,ADR-SI-03,ADR-SI-04,ADR-SI-05,ADR-SI-06,ADR-SI-07,ADR-SI-08,ADR-SI-09,ADR-SI-10
duplicate definitions: (none)
FR range: 1-29 contiguous=True
FR without AC: (none)
referenced AC ids=77; referenced-but-undefined: (none)
referenced FR ids=29; referenced-but-undefined: (none)
referenced NFR ids=9; referenced-but-undefined: (none)
referenced ADR ids=10; referenced-but-undefined: (none)
referenced US ids=8; referenced-but-undefined: (none)
PRD DP refs: DP-01,DP-02,DP-03,DP-04,DP-05,DP-06,DP-07,DP-08,DP-09,DP-10,DP-11,DP-12
PRD S refs=30 (max S-30)
PRD Q refs: 1,2,3,4,5,6,7,8,9,10,11,12

[PRD] TODO=0 TBD=0 FIXME=0 XXX=0 待補=0 待定=0 佔位=0 placeholder=0 YYYY-MM-DD=0 [專案名稱]=0 […]=0 ⚖=0 待裁決=5 建議補入=1 之後再看=5 待排程=2 下輪候選=0 待 SA=4 待 SD=1 待SA=0 待SD=0
[SOP] TODO=0 TBD=0 FIXME=0 XXX=0 待補=0 待定=0 佔位=0 placeholder=0 YYYY-MM-DD=0 [專案名稱]=0 […]=0 ⚖=0 待裁決=0 建議補入=0 之後再看=1 待排程=0 下輪候選=0 待 SA=0 待 SD=0 待SA=0 待SD=0
[LED] TODO=0 TBD=0 FIXME=0 XXX=0 待補=0 待定=0 佔位=0 placeholder=0 YYYY-MM-DD=0 [專案名稱]=0 […]=0 ⚖=0 待裁決=2 建議補入=1 之後再看=1 待排程=0 下輪候選=0 待 SA=0 待 SD=0 待SA=0 待SD=0

marker line hits（前 5 行逐字；其後 3 行是我對省略命中行的歸類註記，非腳本輸出）：
  PRD:543 [待 SA] … ID 與動詞須和 `--kind` 一致（動詞→kind 對映為 SD 推定、待 SA 在 §7.2／§5.1.3 確認：核准→approve、否決→reject〔P…
  PRD:671 [待 SA] …P**。這把 §3.2 原標的 P 型縮到只剩語意那一半（§3.2 的邊界型標示待 SA 同步）。**R-9.6 本身不是 SI 的防線**：BRIDGE §8.3 第…
  PRD:682 [待 SA] …migration_base_sha` 的 commit 時間，**SD 推定、待 SA 確認**；P0 完成前不會有任何基線）；首次 `app.promot…
  PRD:731 [待 SA] …綴下；「標記上線」錨＝`migration_base_sha` 為 SD 推定，待 SA 確認 |…
  PRD:965 [待 SD] …elfImproving-20261019.md`〕；SA 已修非 §9 部分，待 SD 修 §9、QA 二審驗修復、掌舵者）…
  PRD:503／:870／:871／:944 [待裁決／建議補入] …（皆為變更記錄或「原為待裁決」的歷史敘述）
  PRD:108、:201、:235、:474、:692、SOP:130、LED:6 [之後再看] …（皆為「處置欄無／不得留『之後再看』」的規則句）
  PRD:361、:487 [待排程] …（皆為「不得含…『待排程』字樣」的規則句）

[PRD] table blocks=39 rows=426 column-mismatch rows=0
[SOP] table blocks=13 rows=188 column-mismatch rows=0
[LED] table blocks=1 rows=42 column-mismatch rows=0

ledger rows=40 unique ids=40 first=OBS-SI-001 last=OBS-SI-040 min=215B max=565B over700=0
ledger cols (all 8): True
ledger ids contiguous 1..N: True
  ledger TAB at LED:45 col=190: …帳本裡非本 session 的 dispatch 擋下 | <TAB>ools/lib/quota_gate.py:165、:5…
  ledger TAB at LED:47 col=175: …OBS-SI-033 同型，這次有實際後果 | 研究員回報：<TAB>ool-results\toolu_01TigUpwkn7…

SOP source rows (行首 S-NN) = 30 unique=30
SOP levels: V1=1 V2=25 V3=4
SOP calendar-ish hits (含否定句；行號＋前後文)：
PRD calendar-ish hits (含否定句；行號＋前後文)：
  PRD:149 …- ❌ 日曆觸發、版本號觸發、覆蓋度門檻、「每 N 輪」型觸發（C-12）；常駐行程或排程驅動（本 repo…
  PRD:493 …| 日曆／版本號觸發與常駐排程 | ➖ | C-12；PRD v2.1 §16.1 ➖（本 repo…
```

一審的兩組日曆／覆蓋度字樣（「每 N 輪」「定期」「每週」「每日」「每月」「cron」「schtasks」「排程」「常駐」「Daemon」「週期」；「覆蓋度」「coverage」）二審對 PRD 重跑（Grep，不分大小寫）：第一組 14 筆命中（行 149、186、242×2、361、487、493×2、549、606、704、835、845、918）、第二組 8 筆命中（行 75×2、149、242、483、770、772、975）；**逐筆看前後文：皆為否定句（「不存在日曆…觸發」「不構成重評理由」）、「非日曆週期」的定義句、規則句，或既有機制描述（RTM 覆蓋度報告、生命週期），零筆肯定句觸發**。SOP 的 T-1～T-7 觸發表無日曆、版本號、覆蓋度字樣。

**(b) Q12：`git apply --numstat -z` 對六個合成 patch（scratchpad `qa2\q12\p1～p6*.patch`；`git --version`＝`git version 2.51.0.windows.1`）**

```
p1_rename.patch    diff --git a/CLAUDE.md b/docs/x.md  ＋ rename from CLAUDE.md ／ rename to docs/x.md
  --numstat -z → 0<TAB>0<TAB>docs/x.md<NUL>                 rc=0   （來源端 CLAUDE.md 不印）
p2_octal.patch     標頭與 ---／+++ 皆為 "a/CLAUD\105.md"
  --numstat -z → 1<TAB>1<TAB>CLAUDE.md<NUL>                 rc=0   （八進位引號被解開）
p3_mismatch.patch  diff --git a/CLAUDE.md b/CLAUDE.md ；--- a/safe.txt ／ +++ b/safe.txt
  --numstat -z → 1<TAB>1<TAB>safe.txt<NUL>                  rc=0   （以 ---／+++ 為準）
p4_dotdot.patch    diff --git a/../x.md b/../x.md
  --numstat -z → 1<TAB>1<TAB>../x.md<NUL>                   rc=0   （不拒絕 ..）
p5_normal.patch    docs/a.md 修改
  --numstat -z → 1<TAB>1<TAB>docs/a.md<NUL>                 rc=0   （前綴 a/ b/ 已剝）
p6_newfile.patch   new file mode 100644 ；--- /dev/null ／ +++ b/docs/new.md
  --numstat -z → 1<TAB>0<TAB>docs/new.md<NUL>               rc=0
```

**(c) Q5、Q6、`.claude/` 目錄數**

```
MEMORY.md bytes=16391 lastwrite=10-19 04:34:26
physical lines=79  non-blank=75
section header lines: 5,30,51
memory dir .md files=127

family files=70 rows(any DEF-<n>-<n> family)=1667 unique=1661 prefixes=62
prefix 101=998 200=550 others=119 (others prefixes=60)
strict(101/200 + exactly one space each side)=1508
rows containing 再開症狀=4: DEF-200-528,DEF-200-531,DEF-200-535,DEF-200-551
  of which also containing 命中=1: DEF-200-551
rows containing reopens:=0
rows=1667; status (after stripping leading */~/_/space) startswith fixed = 1489

ls-files rc=0 count=29250
distinct tracked .claude/ directories (first .claude segment) = 33
root=1  AISDLC_SDD/*=31  AutoClaude/*=1  other=
```

（Q6 的 `fixed` 首詞數：我 1,489，PRD 1,490，差 1＝首詞切法口徑，不影響基率量級。PRD:524 的「backtick 路徑 846 列」我的口徑得 851，差 5，同屬口徑差，未影響結論。）

**(d) Q11：逐字稿載體**（`C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\f4c765a7-2a26-4453-8d20-34b3c511b6ef.jsonl`；普查範圍＝同目錄 138 份頂層逐字稿）

```
line 167: type=assistant role=assistant content0.type=tool_use name=AskUserQuestion top-level-keys-with-origin=[] msg-keys-with-origin=[] origin=None has_toolUseResult=False isMeta=None
line 168: type=user role=user content0.type=tool_result name=None top-level-keys-with-origin=[] msg-keys-with-origin=[] origin=None has_toolUseResult=True isMeta=None
line 13: type=user role=user content0.type=str name=None top-level-keys-with-origin=['origin', 'turnOrigin'] msg-keys-with-origin=[] origin={"kind": "human"} has_toolUseResult=False isMeta=None
line 1286: type=user role=user content0.type=str name=None top-level-keys-with-origin=['origin', 'turnOrigin'] msg-keys-with-origin=[] origin={"kind": "human"} has_toolUseResult=False isMeta=None
line 195: top-keys=['attachment', 'cwd', …] attachment.type=queued_command attachment-keys=['commandMode', 'humanTurn', 'origin', 'prompt', 'source_uuid', 'timestamp', 'type']
   origin paths: [('attachment.origin', {'kind': 'human'})]
line 227: （同形；attachment.type=queued_command，attachment.origin={'kind': 'human'}）
line 256: （同形；attachment.type=queued_command，attachment.origin={'kind': 'human'}）
  L193 user 10:11:57 'tool_result:'  ／ L194 queue-operation 10:11:57 ／ L195 attachment 10:11:26 att.type=queued_command humanTurn=True origin={'kind': 'human'} ／ L196 attachment 10:11:57 att.type=total_tokens_reminder ／ L197 assistant 10:12:46

files scanned=138 unparsable-lines=0
human-origin via type=user top-level origin: 73 records in 41 files
human-origin via attachment.queued_command : 24 records in 17 files
share of human-origin records that are queued_command attachments = 24/97 = 24.7%
```

**(e) SOP II-5 與 PRD 附錄 A 的強度同步**（`strength_sync.py`）

```
SOP II-5 rows: 12  PRD Appendix A rows: 12
DP-01  SOP:267 [中（一審後重判；原強）]  PRD:898 [中（一審後重判；原強）]  same-level=True
DP-02  SOP:268 [強（維持；…）]  PRD:899 [強]  same-level=True
DP-03  SOP:269 [中]  PRD:900 [中]  same-level=True
DP-04  SOP:270 [中（一審後重判；原強；…）]  PRD:901 [中（一審後重判；原強）]  same-level=True
DP-05  SOP:271 [中（一審後重判；原強）]  PRD:902 [中（一審後重判；原強）]  same-level=True
DP-06  SOP:272 [中（一審後重判；原強）]  PRD:903 [中（一審後重判；原強）]  same-level=True
DP-07  SOP:273 [中（維持；…）]  PRD:904 [中]  same-level=True
DP-08  SOP:274 [強]  PRD:905 [強]  same-level=True
DP-09  SOP:275 [中（一審後重判；原強）]  PRD:906 [中（一審後重判；原強）]  same-level=True
DP-10  SOP:276 [中（一審後重判；原強）]  PRD:907 [中（一審後重判；原強）]  same-level=True
DP-11  SOP:277 [強（維持；…）]  PRD:908 [強]  same-level=True
DP-12  SOP:278 [中（維持；…）]  PRD:909 [中]  same-level=True
mismatches= 0
```

**(f) 座標與時鐘重驗**（F-04、F-11、F-15、F-17）

```
line 13: type=user role=user origin={'kind': 'human'} timestamp=2026-10-18T13:03:23.052Z text-bytes=4248 contains-C2-quote=True
line 901: type=user role=user origin={'kind': 'human'} timestamp=2026-10-18T14:40:46.671Z text-bytes=833 contains-C2-quote=False
line 893: type=queue-operation role=None ts_local=22:40:29 +0800 operation=enqueue
line 901: type=user role=user ts_local=22:40:46 +0800
line 943: type=assistant role=assistant ts_local=22:45:30 +0800 tool='Write …\docs\06_quality\SelfImproving_Observation_Ledger.md'
line 435: keys=['content', 'operation', 'sessionId', 'timestamp', 'type'] operation=enqueue content-bytes=15202
line 1054: …operation=enqueue content-bytes=11207
line 1383: …operation=enqueue content-bytes=11923
line 1505: …operation=enqueue content-bytes=8242   （content 開頭皆為「<agent-message from="…"> [Subagent hand-back] The text below is the final report of a subagent…」）
tools/lib/apply_lock.py:44:class LockBusyError(RuntimeError):
tools/lib/apply_lock.py:60:        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
tools/lib/apply_lock.py:86:def acquire(
tools/lib/quota_ledger.py:35:      `os.open(O_APPEND)` ＋單次 os.write expected=320 lines=281 LOST=39 (12.2%)
tools/lib/quota_ledger.py:36:      `msvcrt.locking(LK_LOCK)`          N=8 時 LOST=0，**N=20 時 10 個行程直接死在
```

**(g) 寫入前終檢**（2026-10-19 09:58:41 +08:00）

```
HEAD=978df84c rc=0
status lines=1
 M docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md
diff --stat HEAD of the three reviewed files: lines=0
docs/01_requirements/SelfImproving_PRD.md  227975 bytes  mtime 10-19 06:15:03
docs/05_development/SelfImproving_Research_Methodology_SOP.md  106992 bytes  mtime 10-19 05:27:43
docs/06_quality/SelfImproving_Observation_Ledger.md  17605 bytes  mtime 10-19 05:48:36
```

### 6.5 二審判定與對 FSM 的建議

**二審判定：PASS**（P1＝0、P2＝0；新增 P3＝7、P4＝6）。口徑＝無 P≤2 才 PASS，且零發現不是 PASS——本審查的正向證據（今日新指令輸出）：

1. F-01／F-02／F-03 三筆 P2 逐條在現座標找到修法並以今日實測支撐：Q12 六個合成 patch（6.4 b）、`.claude/` 目錄數 33（6.4 c）、Q6 重算 1,667／1,661／62 前綴與三個關鍵基率（6.4 c）、`migration_base_sha` 在 AC-SI-01-3／04-3／§8.1／§9.3／§9.6 的一致鏈；
2. F-04～F-21 十八筆 P3：17 消除、1 部分（F-18，第四項計數再度落後 1，列 F-36）；F-15 原五列消除、新列再犯列 F-35；
3. 自檢：ID 唯一、無懸空引用；53 個表格區塊欄數零不符；佔位字樣與 ⚖ 零命中；日曆與覆蓋度字樣零肯定句觸發（6.4 a）；SOP↔PRD 強度 12／12 同級（6.4 e）；
4. 修復引入的新問題 13 筆（P3×7＋P4×6），皆為灰區明文化或承接動作的缺口，無一使一審 P2 回潮；M1 per-PROP 窗無 P≤2 遮蔽路徑（6.2）。

**邊界案例（請主控、掌舵者知悉）**：F-31（M1 窗關閉對未決候選無說法）與 F-34（直接追加格式合法的 `dec` 行無偵測承接）我判 P3——各自留有可見殘餘訊號，或 PRD 已自承偽造只可事後稽核（AC-SI-12-1 原文），且修法各只是一兩句規格；但兩者分別碰到成功指標的偏向與 K=1 人工閘的完整性，若掌舵者判為 P2，則二審判定改 FAIL。此時修法仍只在 SA／SD 的規格文字，建議當輪修畢由主控親驗，不需第三輪 QA（範本〈審查閉環的終止〉：至多二審）。

**對 FSM 的建議**（QA 未跑 FSM CLI、未讀 FSM-STATE，遵守禁令 1）：由主控在三件組環境下執行 `gate --gate SCG_VALIDATION --result PASS`（FSM 鍵 `monorepo-selfimproving`）。建議同輪處理的 P3：SA＝F-29（錨定義與過期句）、F-30、F-31、F-32、F-34（AC 與矩陣面）；SD＝F-33、F-34（§9.3／§9.4）、F-29（PRD:543、:671、:682、:731）；主控＝F-35、F-36、PRD:965、SOP:299／:368（交研究員）；P4（F-36～F-41）只登記。🔴 仍待掌舵者的項目不因本判定改變：附錄 C.2 #1～#9 的凍結時逐項確認；`W_N`、`W_MIN`、`W_EVT`、`W_OPP` 等「無先例、未校準」初值；F-29 的「再現標記上線」錨。

### 6.6 未涵蓋與流程摩擦

**未涵蓋**

- **URL**：二審未上網、未重開任何外部頁面（任務書：不需上網）；一審抽開的 6 個與未抽的 24 個狀態不變（§4）。
- **實作面**：全為規格敘述；未執行任何測試；`si` CLI 尚不存在、C1～C15 為規劃；§9.4 的負控未實作驗證（只驗了 `git apply --numstat -z` 的行為前提）。
- **Q12**：只在 Windows、git 2.51.0.windows.1 驗六個合成 patch；macOS 未驗（PRD 同）；`docs//CLAUDE.md` 路徑收斂、`copy` 標頭、含空白路徑未重測。
- **Q11／F-33**：逐字稿欄位只在本機驗；普查只計 `origin.kind=human` 的兩種載體，未驗他機或他版本的欄位形態；`queue-operation` 的 `content` 是否也含人類原文未逐一確認。
- **M1 窗**：紙上推演，未對真帳本模擬；`W_EVT`、`W_MIN`、`W_OPP` 數值合理性未驗（PRD 自標未校準）。
- **文字覆蓋**：PRD 單檔 227,975 bytes，我以「`git diff`＋分段 Read」覆蓋全部修改處，**未逐字重讀未被修復觸及的段落**（一審已讀、diff 外的行未變）；SOP 新增文字中 S-04 升 V2 的轉述只讀、未重開頁。
- **AC 可測性**：仍依 G／W／T 形態判讀、未逐條實作驗證。
- **DEF 帳本**：只重算列數與關鍵字樣，未讀各 DEF 列內容。

**流程摩擦／疑似缺陷**

1. **週額度 429 中斷（座標）**：我的 subagent 逐字稿 `C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\f3ead132-29b1-418c-97d9-35868ab11c70\subagents\agent-a8b9d4251ce6bb6d9.jsonl` line 1250（2026-10-19 06:18:41 +08:00；`apiError:"usage_limit_reached"`、`apiErrorStatus:429`、`rateLimitType:"seven_day"`、`resetsAt` 1792792800＝2026-10-24 06:00 +08:00、文字「You've hit your weekly limit · resets Oct 24, 6am (Asia/Taipei)」）；line 1251 是續跑訊息（09:21:45，間隔約 3 小時）。二審指示 line 1240（06:18:01）、第一個工具呼叫 line 1243（06:18:38，`git rev-parse`／`git log`）、429 line 1250、續跑訊息 line 1251——第一個工具呼叫之後即中斷，**實質查證全在續跑後**；續跑靠對話摘要接上而非磁碟任務書（CLAUDE.md〈可重啟點〉第 2 條的缺口：子代理被 429 打斷時，沒有「已完成／未完成」清單可供自我接續）。
2. auto mode 系統提示再度要求「優先用 Bash 讀寫檔」，與根 `CLAUDE.md` 鐵律一（Windows 禁用 Bash）及任務書「不用 Bash」衝突；依後者全程 PowerShell／Read／Grep／Edit（OBS-SI-011 在二審再次復發）：座標＝LED:20、系統提示 auto mode 區塊、`.claude/hooks/block_bash_on_windows.py`。
3. PRD 單行過長，Grep 命中「Omitted long matching line」（例：PRD:679），改用 `git diff --output` 導檔＋Read 分段、或 Grep `-o` 加 `.{0,N}` 窗口；與 OBS-SI-033／038 同型（F-41）。
4. 我自己的兩個腳本失誤（非 repo 缺陷）：(a) `.claude/` 目錄計數的第一版用鬆散正則得 45／13，改精準前綴正則得 33（與 PRD:404 相符），未採第一版數字；(b) 二審續跑後我曾用 `"origin":` 子字串判斷，被 `AskUserQuestion` 答覆行裡工具內容的 `"origin":{"host":"github.com"…}` 騙成「有 origin」，改看結構化欄位才對——這也是 `si decide` 實作輪的提醒：逐字稿欄位一律解析 JSON 後判結構、不用子字串。
5. 分棒串行修復的殘留（F-29、F-35）：下游棒完成後沒有回頭清上游棒留下的待辦句，帳本新列又重犯座標問題——與 OBS-SI-032、OBS-SI-040 同型；建議修復棒交卷前跑一次 Grep `待 (SA|SD)` 與「需 … 同步」作為出口檢查。

---

二審完成時刻：2026-10-19 10:07（+08:00）（報告寫入後終檢：`HEAD=978df84c rc=0`、`git status --short` 只有本報告一個 ` M`、三份受審檔 `git diff --stat HEAD` 無輸出）；QA（Sonnet 5.5，未參與撰寫）；**二審判定 PASS**（P1＝0、P2＝0；新增 P3＝7、P4＝6）。一審判定 FAIL（P1＝0、P2＝3、P3＝18、P4＝7）。

## 7. 凍結紀錄（主控補註，2026-10-19；本節非 QA 所寫）

- 收尾 commit `8d2d5ef0`（SD 收尾棒 P3 F-29～F-34、F-36＋主控 C.2 補記兩則授權座標與 #9 附件載體）後，主控執行：
  - `gate --gate SCG_VALIDATION --result PASS` → 逐字輸出 `{"gate": "SCG_VALIDATION", "result": "PASS", "next_state": "HUMAN_PENDING"}`（rc=0）；`show` 的 `current_state` 為 `HUMAN_PENDING`。
  - `spec-frozen --stage Stage-1 --doc docs/01_requirements/SelfImproving_PRD.md --doc docs/05_development/SelfImproving_Research_Methodology_SOP.md --digest --root <repo 根> --approver "掌舵者（預先核准，sid f3ead132-29b1-418c-97d9-35868ab11c70 line 2536；主控代為執行）"` → 逐字輸出：`{"ok":true,"verb":"spec-frozen","project":"monorepo-selfimproving","from_state":"HUMAN_PENDING","current_state":"SPEC_FROZEN","stage":"Stage-1","spec_doc_digests":{"docs/01_requirements/SelfImproving_PRD.md":"sha256:a27bba619c493b2edac12cdd260e889f2b023fc9344c547487d4c4337be3b513","docs/05_development/SelfImproving_Research_Methodology_SOP.md":"sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2"}}`（rc=0）。
- 人工閘依據：掌舵者本輪原文（同 sid）line 2493「…(不用考量成本)，我授權幫我決策…」與 line 2536「真正需要你本人的只剩凍結核准 ==> 現在先授權核准! (避免不在機器旁)」；凍結核准由掌舵者預先給出，主控代為執行，不再互動確認。PRD 附錄 C.2 #1～#9 仍可由掌舵者以 T1 推翻（推翻走 HUMAN_PENDING→SPEC_REGRESSION_CHECK→重新凍結）。
- 狀態檔住根 `build/reports/fsm`（不入庫）；凍結後本 PRD 與 SOP 不得再原地改，修訂走 SPEC_REGRESSION_CHECK 迴路。
- 掌舵者後續指示（line 見記憶檔）：凍結後接著開 P0 實作（新功能鍵）。
- **訂正（2026-10-19，主控）**：本節與 PRD C.2 初稿、OBS-SI-042 所引 line 2493／2536 為 assistant 空記錄；真人句＝line 2476（授權，「…(不用考量成本)…」）／2525（預先核准）／2581（「了解，凍結後接著開 P0 實作」），主控以 JSON 解析 `type`／`origin.kind` 親驗（SA 起草 P0 TCS 時發現）。PRD C.2 經 SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING 訂正重凍（新 digest 見下列補記）；更正列 OBS-SI-043。
- **重凍補記（2026-10-19，主控）**：C.2 座標訂正經 QA 複核成立（§A：三行皆 `type=user`／`origin.kind=human`、引文逐字相符、`git diff` 只動 PRD 一個物理行）後，`monorepo-selfimproving` 記 `gate SCG_VALIDATION PASS`（只覆蓋此單一項，SCG-0 二審 PASS 維持）→ HUMAN_PENDING → `spec-frozen --stage Stage-1` 重凍：PRD digest `sha256:9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e`、SOP digest `sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2`（SOP 未變）；approver＝掌舵者預先核准（line 2525），主控代為執行。P0 鍵 `monorepo-si-p0-ledger` 的 Stage-1 採納記錄仍引舊 PRD digest（內容差異只有 C.2 一行座標），TCS 追溯表回填新 digest（預審 F-07）。
