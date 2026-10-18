# SCG-0 零信任獨立審查報告 — SelfImproving（自我進化機制）PRD

| 項目 | 內容 |
|---|---|
| 受審物 | `docs/01_requirements/SelfImproving_PRD.md`（954 行／175,851 bytes）、`docs/05_development/SelfImproving_Research_Methodology_SOP.md`（345 行／94,071 bytes）、`docs/06_quality/SelfImproving_Observation_Ledger.md`（43 行／14,240 bytes；34 列） |
| 輸入快照 | HEAD＝`6c23495d`（`git -C D:\CursorProject\AISDCL_Agent rev-parse --short HEAD` → `HEAD=6c23495d rc=0`）；`git status --short` → `status-lines=0`（工作樹乾淨 ⇒ 工作樹檔案＝HEAD 版本，審查以 Read 讀工作樹；審查結束前複驗 HEAD 與工作樹未變，見 §4） |
| 審查者 | QA（Sonnet 5.5；未參與 SOP／PRD／帳本撰寫；唯讀，不改受審物，不做 git 寫入，不派子代理，不跑 FSM CLI，不用 Bash） |
| 日期 | 2026-10-19（本機 +08:00；審查區間約 04:33～05:15） |
| 判定 | **SCG-0：FAIL**（P1＝0、P2＝3、P3＝18、P4＝7；判定口徑＝無 P≤2 才 PASS） |

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
