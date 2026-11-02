# SCG-4 審查報告（二審）— ResearchToPRD 框架側方法層（鍵 `sdd-research-to-prd`）

**審查輪次**：**二審**（一審 FAIL 的複驗；一審報告全文留存於 `S\qa\fw\SCG4-REVIEW-ResearchToPRD-Framework-20261102.R1-first-review.md`，一審發現表原文與差異見〈附錄 R1〉）。
**Oracle**：`AISDLC_SDD/AISDLC_SDD_v0.30/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md` 現檔（174,924 bytes、sha256 `9602289ef45c…`；35 AT＝正控 26／負控 9；勘誤 1～9；`spec-refreeze` 已重記，現值與記錄逐值相同，F.1）。
**審查對象**：工作樹＝HEAD `b1f308f6`＋未提交修改（框架 TCS、根層 PRD、ADR-XPLAT-017、計畫書）；一審 commit `25c66981`，起點 `$base`＝`01d9be6e`。`AISDLC_SDD/docs/.github/tools/.claude` 自 `25c66981` 起沒有任何已提交差異（F.2），工作樹相對 HEAD 在 `AISDLC_SDD` 範圍只有 TCS 一檔。
**審查者**：SCG-4 QA 鏡（Sonnet 5.5；全程唯讀、零信任）；規格作者＝SD-B、落檔／refreeze＝主控、審查＝本鏡。獨立性的已知邊界同一審（TCS ⚖6），見 G。
**證據落點**：本檔每段輸出皆為本回合真跑；腳本、原始 log、突變結果 JSON 在 `S\qa\fw2\`（一審的在 `S\qa\fw\`）。

## A. 範圍與快照

| 項目 | 值（本回合現查） |
|------|------------------|
| repo／HEAD | `D:\CursorProject\AISDCL_Agent`；`git rev-parse HEAD`＝`b1f308f6`（一審時為 `25c66981`；其後兩個 commit 只動 `AgentConsole/`，`git diff --name-only 25c66981 HEAD -- AISDLC_SDD docs .github tools .claude` 輸出為空，F.2） |
| 工作樹未提交修改（框架側） | TCS（相對 `25c66981`：`git diff --numstat` 見 F.2）、根層 PRD（+3／−3）、ADR-XPLAT-017（+1／−1）、計畫書（+1／−1）；`git status --porcelain -- AISDLC_SDD tools .claude .github` 條數＝1（只有 TCS） |
| 框架鍵 FSM 現態（唯讀 `show --must-exist`；三件組 `SDD_ACTIVE_VERSION=0.30`／`SDD_PROJECT=sdd-research-to-prd`／`SDD_STATE_DIR`＝版本目錄 `build/reports/sdd-dogfood`） | `current_state=PR_REVIEW`；四閘 retry current_count 皆 0；`total_spec_frozen_count=2`、`escalation_count=0`；`decision_trace` 末三筆＝`PR_REVIEW → SPEC_AUDIT`（cli_manual）→ `SPEC_AUDIT → SPEC_AUDIT`（`spec_refreeze`）→ `SPEC_AUDIT → PR_REVIEW`（「SCG-4 二審開始」）；`frozen_stages` 三條：Stage-1（五檔）、Stage-2（TCS 原值）、重記條目 `[2]`（stage＝Stage-2、`kind=refreeze`、`supersedes=2026-11-02T04:04:48+00:00`、六檔：`AISDLC_SDD/CLAUDE.md`、INIT、SPEC_FIRST_GATE、PRD `179e839f…`、ADR-001、TCS `9602289e…`）。逐字見 F.1 |
| 凍結摘要複驗 | 取三條 `frozen_stages` 的聯集（同鍵後者勝出＝`state_loader.py:325-332` 與 AutoClaude `_sdd_frozen_gate.py:182-197` 的消費語意，F.6）得 6 鍵；以框架自己的 `digest_doc` 對現檔重算，**6 鍵逐值 SAME、`drift_count=0`**；TCS〈增量追溯表〉U1～U5 五鍵逐值與聯集相同（F.1） |
| 二審範圍 | (1) 指定 8 項實跑：AT-970-5-1／5-2／5-3／5-E-1／6-1／6-6／7-0／7-E-1（`7-0`＝§2.7 共用區塊，沒有 RESULT 行，判準為預期輸出與無錯誤）；(2) 一審 F-03～F-07 以 TCS 現檔條文逐條對照（行號見 C、F.3）；(3) 其餘沿用一審——**但本鏡加跑了 27 個 AT**（唯讀、約 20 秒、不改指定項判定），理由：TCS 檔本身是 1-1／1-3／3-1／6-4／6-5 的輸入、且 7-0 把 `Invoke-Sdd` 改為從複本執行而影響所有 🔶 演練 AT；(4) **沿用一審的只有 4-4（ci-gate）**：`AISDLC_SDD` 樹自 `25c66981` 起只有 TCS 一檔差異（ci-gate 所測程式／agent／模板／工作流皆未動），且 ci-gate 會改寫被忽略的快取檔，違「全程唯讀」，故不重跑 |
| 執行環境 | 同一審：Windows 11、pwsh 7.6.9、Python 3.11.9（根 `.venv`）；AT 區塊由 `gen_driver2.py` 自**更新後的 TCS** 逐字抽出（39 個 powershell 區塊＝35 AT 的 34 個＋共用前置＋5-3 摘要重算＋7-0＋7-Z；4-4 不含），在單一 pwsh 行程內依 TCS 順序執行；每段前後做「`AISDLC_SDD` 檔案清單＋mtime＋`git status --ignored` 雜湊」唯讀快照（結果見 F.4） |

## B. 判定與計數

**判定：二審 PASS**（P1 0／P2 0／P3 0／P4 2；規則：P1 0 且 P2 0 ⇒ PASS）。

| 計數 | 值 |
|------|----|
| P1／P2／P3／P4 | **0／0／0／2**（一審為 0／2／2／4；一審 F-01～F-07 皆已修；剩 F-08 流程性未結，另有二審新增 N-1，見 C） |
| 一審發現處置 | F-01 已修、F-02 已修、F-03 已修、F-04 已修、F-05 已修、F-06 已修、F-07 已修、F-08 未結（P4，流程性） |
| AT（35 個） | **二審實跑 34 個全 PASS、沿用一審 1 個（4-4 PASS）、FAIL 0、NOT-EVALUABLE 0**；指定 8 項：7 個 AT PASS＋7-0 共用區塊無錯誤；加跑 27 個全 PASS |
| 突變（F-04 複驗） | 一審的 9 個存活突變（M27、S01～S08）在更新後的 AT 下**全數被殺**（M27／M27b 被 6-1、S01～S08 各被 6-6）；另探 3 個（S09～S11）：S09、S10 存活（N-1），S11 被殺（E） |
| 對真 repo 的寫入 | **零**：B2／C2／S1／S2 四段前後快照逐字相同、狀態檔雜湊不變、真 repo `build/reports/abort/` 今日檔案 0 個（F.4）——一審 F-03 的隔離修法經實證有效 |

**指定 8 項的結果（每個 AT 的 rc）**

| # | AT | 判定 | RESULT 行（逐字；含 AT 自帶 rc） | driver 行程 rc |
|---|----|------|----------------------------------|----------------|
| 1 | `AT-970-5-1` | **PASS** | `RESULT AT-970-5-1 PASS violations=0` | 0（B 段 1 秒） |
| 2 | `AT-970-5-2` | **PASS** | `RESULT AT-970-5-2 PASS protected paths changed=0` | 0（B 段 1 秒） |
| 3 | `AT-970-5-3` | **PASS** | `RESULT AT-970-5-3 PASS rc=0 table_rows=5` | 0（B 段 1 秒） |
| 4 | `AT-970-5-E-1` | **PASS** | `RESULT AT-970-5-E-1 PASS` | 0（B 段 1 秒） |
| 5 | `AT-970-6-1` | **PASS** | `RESULT AT-970-6-1 PASS chapters=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14` | 0（B 段 1 秒） |
| 6 | `AT-970-6-6` | **PASS** | `RESULT AT-970-6-6 PASS` | 0（B 段 1 秒） |
| 7 | `AT-970-7-0`（共用區塊） | **OK**（無錯誤） | 無 RESULT 行；輸出 `state dir = <暫存>\fsm`、`version dir copy = <暫存>\AISDLC_SDD\AISDLC_SDD_v0.30`（逐字見 D.7） | 0（C 段 12 秒） |
| 8 | `AT-970-7-E-1` | **PASS** | `RESULT AT-970-7-E-1 PASS` | 0（C 段 12 秒） |

## C. 發現表（二審）

| 編號 | 一審 | 二審處置 | TCS 現檔座標（行號；`S\qa\fw2\tcs_lines.py` 現查，F.3） | 本回合查證 |
|------|------|----------|-------------------------------------------------------|------------|
| F-01 | P2 | **已修** | 5-1 `$rootExempt` 第 8 條 `ResearchSOPtoPRD_Source_Spec.md` L573、判定 `-eq 8` L602、預期輸出 L605、描述（逐字 8 條＋勘誤 1 句）L561；5-E-1 `$okPaths` L668、`$c6` 加 `….md.bak` 且 `-eq 4` L674；W-F6 L75、§5 L1219、⚖4 L1263；勘誤 1 L1866 | **5-1 `PASS violations=0`（`root exempt entries: 8`）、5-2 PASS、5-E-1 PASS**（D.1～D.4）。同批同步已核：PRD C.7 D-46 列、§9.0 兩列（根層連動列、來源規格逐字檔列）、ADR-XPLAT-017 §D7（`:112`）皆含 8 個標記，TCS `$rootExempt`＋目錄前綴恰 8 條；舊句「先於各鍵 Stage-1 採納的基準 commit，故不在…」在 PRD:1165 與計畫書:31 已刪並改為「首次入庫於 W0 落檔 commit `25c66981`，在基準 commit `01d9be6e` 之後，故列入」（F.2 §3 全 True） |
| F-02 | P2 | **已修** | 輸入快照 L23、增量條款段 L32（落檔時序）、追溯表說明 L103、U1～U5 L107～L111、改動前基準 L113、5-3 描述（聯集）L619、`$eff` 聯集 L629、逐鍵比對 L634、判定 `-eq 5` L636、§6 收尾段 L1254、⚖1 L1260；勘誤 2 L1867 | **5-3 `PASS rc=0 table_rows=5`**（D.3）。refreeze 後真狀態：聯集 6 鍵逐值 SAME、`drift_count=0`、U1～U5 逐值與聯集相同（F.1）；聯集語意＝`state_loader.py:325-332`、AutoClaude `_sdd_frozen_gate.py:182-197`（F.6）；AT 讀全部條目而非只讀 `Stage-1` 那一筆，所以重記後不會失明 |
| F-03 | P3 | **已修** | §2.7 引言（`$tmp` 之下＋版本目錄複本、據實說明 `SNAPSHOT_DIR` 不隨 `SDD_STATE_DIR`）L905；7-0：`$fsmSdd` L946、`$fsmVd` L948、複製版本目錄 L949、複製 `scripts/` L950、`Invoke-Sdd` 改 `Push-Location $fsmVd` L954、印出 `version dir copy` L978、預期輸出 L981；7-Z（含複本）L1177；⚖8 L1267；勘誤 3 L1868 | **7-E-1 `PASS`；隔離探針**（7-E-1 之後、7-Z 之前）：真 repo abort 目錄今日（2026-11-02）檔案**空**；複本內有 `ABORT-2026-11-02-auto-recovery-refused.md`、`ABORT-RAW-2026-11-02.yaml`，內文 `project: research-at970c`（D.8）。C 段前後快照逐字相同；現查真 repo abort 目錄今日檔案＝`無`（F.4） |
| F-04 | P3 | **已修** | 6-1 描述（逐處計數）L684、`$codeCnt` L701、`$p07Ok` 逐處計數迴圈 L703、判定列 L712；§1 映射 6-6 L170；6-6 描述 L843、區塊 L846、判定 L879；勘誤 4 L1869 | **6-1 PASS（P0-7 列：四個預檢代碼逐處計數且各有定義子句）、6-6 PASS（八項散文對拍）**。突變複驗（新沙箱，基線 22 個 AT 全 PASS）：M27、M27b 被 6-1 殺；S01～S08 **各被 6-6 殺**（E.1）。6-6 條 (3) 以相同正則實測覆蓋 6 處「第 N 次…ESCALATION」（工作流 L141／L184／L473／L682、卡 L74／L178；F.5），與 TCS 描述的六處一致 |
| F-05 | P4 | **已修** | 7-1 預期輸出（`adr_draft` 在 `PRD-v1.0.0` 之前，附 `Sort-Object` 說明）L1002；勘誤 5 L1870 | 加跑的 7-1 PASS，實際輸出行 `digest keys: 00_research/evidence_matrix.md,00_research/issue_scope.json,01_specs/adr_draft.md,01_specs/PRD-v1.0.0.md` 與訂正後預期逐字相同（D.10） |
| F-06 | P4 | **已修** | D5 列（落檔 commit `25c66981`）L59；AT-970-1-1 Given L235；§2 引言 L191；⚖1 重現指令 L1260；⚖7 L1266；⚖8 L1267；勘誤 6 L1871。`FRAMEWORK_EDITS`／`FRAMEWORK_VERIFY` 除勘誤 6 列（引用被訂正的原文）外在 TCS 已無殘留（F.3） | 本鏡逐字重跑 ⚖1 的三個 numstat：**13 檔 +176／−22、24 檔 +4632／−29、15 檔 +184／−29，與 TCS 宣稱逐值一致**（F.2 §1）；1-1、1-3 重跑 PASS（D.10） |
| F-07 | P4 | **已修** | 〈上位需求對照〉AC-970-5 列 L85（NFR-R2P-08「文件最小集與回填」；直接依據 PRD §9.0 與 ADR-XPLAT-017 §D7；AC-R2P-11-7、AC-R2P-12-6）；勘誤 7 L1872 | PRD 定義核對：AC-R2P-11-7＝Stage-1 採納 `spec-frozen --stage Stage-1 … --digest --root`；AC-R2P-12-6＝`git diff --name-only` 核對 `CLAUDE.md`／`.claude/`／`tools/` 零變更（F.2 §2）。6-5 重跑 `cited ids: 44 (FR 11, AC 27); absent in PRD: 0`（與 TCS 預期逐值相同）。備註：AC-R2P-12-6 的主體是軌道 A 目標分支，與框架鍵變更集合是同型核對而非同一對象，連結可接受 |
| F-08 | P4 | **未結（流程性）** | `v0.30/docs/06_quality/` 仍只有既有 `HUB-GOVERNANCE-SPEC.md`；TCS §6 要求的 `RTM-ResearchToPRD-Framework-20261102.md` 與 SCG-4 證據檔尚未落檔 | 不影響 AT；隨 RTM_VERIFY 與本報告落檔結案（RTM 與證據檔須列在 AT-970-5-1 的 `docs/06_quality/` 例外內，已在白名單規則中） |
| N-1 | P4（**二審新增**） | 開立 | AT-970-6-6 條 (3)（L843 描述、區塊 `$nEsc`） | 條 (3) 的範圍是「第 N 次…ESCALATION」六處；工作流另有 4 處以「最多 3 輪」復述同一預算（L35、L139 §2.3 標題、L150〔含刻意的「最多 4 輪」對照句〕、L406 §6.3 末段）不在守衛內：突變 **S09**（§2.3 標題 3→4）、**S10**（§6.3 末段 3→4）**存活**；範圍內的 **S11 被 6-6 殺死**（偵測器在位）。這是 AT 描述範圍之外的已知邊界，不阻擋 | 可選：6-6 條 (3) 再加 `最多 (\d+) 輪` 抽取（排除 L150 的來源規格對照句），或在 TCS 註明「最多 N 輪」不在守衛內 |

## D. AT 逐項實跑（指定 8 項＋加跑 27 項＋沿用 1 項）

**35 個 AT 的二審狀態總表**

| # | AT | 類型 | 二審狀態 | 判定 | RESULT 行（逐字） |
|---|----|------|----------|------|-------------------|
| 1 | `AT-970-1-1` | Unit | 加跑 | **PASS** | `RESULT AT-970-1-1 PASS` |
| 2 | `AT-970-1-2` | Unit | 加跑 | **PASS** | `RESULT AT-970-1-2 PASS rc=0` |
| 3 | `AT-970-1-3` | Unit | 加跑 | **PASS** | `RESULT AT-970-1-3 PASS files checked: 22` |
| 4 | `AT-970-1-E-1` | Unit | 加跑 | **PASS** | `RESULT AT-970-1-E-1 PASS` |
| 5 | `AT-970-2-1` | Integration | 加跑 | **PASS** | `RESULT AT-970-2-1 PASS specialized=23 templates=63 workflows=24` |
| 6 | `AT-970-2-2` | Integration | 加跑 | **PASS** | `RESULT AT-970-2-2 PASS rc=0` |
| 7 | `AT-970-2-E-1` | Integration | 加跑 | **PASS** | `RESULT AT-970-2-E-1 PASS` |
| 8 | `AT-970-3-1` | Contract | 加跑 | **PASS** | `RESULT AT-970-3-1 PASS rc=0` |
| 9 | `AT-970-3-2` | Contract | 加跑 | **PASS** | `RESULT AT-970-3-2 PASS rc=0` |
| 10 | `AT-970-3-E-1` | Contract | 加跑 | **PASS** | `RESULT AT-970-3-E-1 PASS rc=1` |
| 11 | `AT-970-4-1` | Integration | 加跑 | **PASS** | `RESULT AT-970-4-1 PASS` |
| 12 | `AT-970-4-2` | Integration | 加跑 | **PASS** | `RESULT AT-970-4-2 PASS rc=1 n_fail=0 n_warn=3` |
| 13 | `AT-970-4-3` | Integration | 加跑 | **PASS** | `RESULT AT-970-4-3 PASS` |
| 14 | `AT-970-4-4` | E2E | **沿用一審**（不重跑；理由見 A） | PASS | `RESULT AT-970-4-4 PASS rc=0`（一審；ci-gate 逐軌計數 `v0.01:1478 v0.30:2250 scripts/tests:425`） |
| 15 | `AT-970-4-E-1` | Integration | 加跑 | **PASS** | `RESULT AT-970-4-E-1 PASS` |
| 16 | `AT-970-5-1` | Integration | **指定重跑** | **PASS** | `RESULT AT-970-5-1 PASS violations=0` |
| 17 | `AT-970-5-2` | Integration | **指定重跑** | **PASS** | `RESULT AT-970-5-2 PASS protected paths changed=0` |
| 18 | `AT-970-5-3` | Integration | **指定重跑** | **PASS** | `RESULT AT-970-5-3 PASS rc=0 table_rows=5` |
| 19 | `AT-970-5-E-1` | Unit | **指定重跑** | **PASS** | `RESULT AT-970-5-E-1 PASS` |
| 20 | `AT-970-6-1` | Unit | **指定重跑** | **PASS** | `RESULT AT-970-6-1 PASS chapters=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14` |
| 21 | `AT-970-6-2` | Unit | 加跑 | **PASS** | `RESULT AT-970-6-2 PASS verbs=show,transition,gate,spec-refreeze,spec-frozen` |
| 22 | `AT-970-6-3` | Unit | 加跑 | **PASS** | `RESULT AT-970-6-3 PASS problems=0` |
| 23 | `AT-970-6-4` | Unit | 加跑 | **PASS** | `RESULT AT-970-6-4 PASS placeholder-words=0 brace-placeholders=0` |
| 24 | `AT-970-6-5` | Unit | 加跑 | **PASS** | `RESULT AT-970-6-5 PASS` |
| 25 | `AT-970-6-6` | Unit | **指定重跑** | **PASS** | `RESULT AT-970-6-6 PASS` |
| 26 | `AT-970-6-E-1` | Unit | 加跑 | **PASS** | `RESULT AT-970-6-E-1 PASS` |
| 27 | `AT-970-7-1` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-1 PASS` |
| 28 | `AT-970-7-2` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-2 PASS` |
| 29 | `AT-970-7-3` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-3 PASS` |
| 30 | `AT-970-7-4` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-4 PASS` |
| 31 | `AT-970-7-5` | Unit | 加跑 | **PASS** | `RESULT AT-970-7-5 PASS rc=0` |
| 32 | `AT-970-7-6` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-6 PASS` |
| 33 | `AT-970-7-E-1` | Integration | **指定重跑** | **PASS** | `RESULT AT-970-7-E-1 PASS` |
| 34 | `AT-970-7-E-2` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-E-2 PASS` |
| 35 | `AT-970-7-E-3` | Integration | 加跑 | **PASS** | `RESULT AT-970-7-E-3 PASS` |

### D.1　AT-970-5-1（Integration）— 指定重跑 — PASS

Given／When／Then：變更集合落在 24 條白名單路徑、`docs/06_quality/` 與 D-46 根層連動逐字清單內；`tools/`、`.claude/` 零差異

來源 log：`run2_B.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-5-1.ps1`（自更新後的 TCS 逐字抽出）

```text
whitelist size: 24
root exempt entries: 8
changed paths: 102
RESULT AT-970-5-1 PASS violations=0
```

> 一審為 `FAIL violations=1`（違規 `docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`）；現 `root exempt entries: 8`、`violations=0`。`changed paths: 102` 含 AgentConsole 開發棒的併行修改（以 `AgentConsole/` 前綴豁免）與兩個新 commit。`$base`＝`git -C $root rev-parse 01d9be6e`（依 TCS 現檔 5-1 前置段）。

### D.2　AT-970-5-2（Integration）— 指定重跑 — PASS

Given／When／Then：受保護路徑零差異

來源 log：`run2_B.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-5-2.ps1`（自更新後的 TCS 逐字抽出）

```text
RESULT AT-970-5-2 PASS protected paths changed=0
```

### D.3　AT-970-5-3（Integration）— 指定重跑 — PASS

Given／When／Then：〈增量追溯表〉五個摘要＝Stage-1 凍結記錄與 `spec-refreeze` 重記條目的聯集（唯讀 `show`）

來源 log：`run2_B.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-5-3.ps1`（自更新後的 TCS 逐字抽出）

```text
RESULT AT-970-5-3 PASS rc=0 table_rows=5
--- 緊接的 AT-970-5-3-digest 區塊（TCS 提供的重算指令，現含五檔、`-B`）---
AISDLC_SDD/CLAUDE.md	sha256:09d88638cd8e3d441c3f1bd94cbf289beff767cd9455063263125c06b9142908
AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md	sha256:c0732753d2a2e7b19678ec48d169845e3280a3b06422325a966a9fd4b07dde28
AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md	sha256:ca913bb1f62f97ef4b06fd698c2c5c3b0327f464fa90b1760d8a07a8b4ec98fa
docs/01_requirements/ResearchToPRD_PRD.md	sha256:179e839fe318388ad3522de3d7b6f8bda222f6b808dff23455e32a3ae3007ed8
AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md	sha256:c2935ae10317a9db4992057db14a0e58983005711f9072f0b74cd39829260180
```

> 一審為 `FAIL rc=0 table_rows=3`。本回合在 driver 內暫設三件組（`SDD_ACTIVE_VERSION=0.30`、`SDD_STATE_DIR`＝真狀態目錄、`SDD_PROJECT=sdd-research-to-prd`）後做唯讀 `show --must-exist`，跑完清除；狀態檔雜湊前後相同。

### D.4　AT-970-5-E-1（Unit）— 指定重跑 — PASS

Given／When／Then：負控：邊界函式對合成的越界路徑（含清單外的根層文件、清單外的 `scripts/` 檔、根層 `.claude/`）回報違規

來源 log：`run2_B.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-5-E-1.ps1`（自更新後的 TCS 逐字抽出）

```text
transition_rules flagged=True; frozen baseline flagged=True; root tools flagged=True; root .claude flagged=True; allowed and exempt not flagged=True; other workflow flagged=True; off-list root docs flagged=True; other script flagged=True
RESULT AT-970-5-E-1 PASS
```

> 含新增的近似檔名負控 `ResearchSOPtoPRD_Source_Spec.md.bak`（清單是逐字比對、不是前綴；`off-list root docs flagged=True` 即含該筆）。

### D.5　AT-970-6-1（Unit）— 指定重跑 — PASS

Given／When／Then：工作流章節 0～14 連號；ADR 決策恰 D1～D7 且各含其關鍵語；恢復後預算句（D-60）、P0-7 預檢代碼逐處計數、缺陷狀態轉移矩陣各在其位

來源 log：`run2_B.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-6-1.ps1`（自更新後的 TCS 逐字抽出）

```text
PASS 工作流章節 0..14 連號
PASS ADR 決策恰 D1..D7
PASS D1..D7 各含 PRD §9.5 關鍵語
PASS 工作流表頭引用根層 PRD
PASS ADR 引用 FR-R2P 與 AC-R2P
PASS 工作流第 2.5 節含恢復後預算句（D-60）
PASS 審查卡模板第 2.3 節含恢復後預算句（D-60）
PASS SE-PRD 模板 P0-7 列：四個預檢代碼逐處計數且各有定義子句
PASS 審查卡模板第 5.3 節含缺陷狀態轉移矩陣
RESULT AT-970-6-1 PASS chapters=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
```

> 第 8 項已改為「P0-7 列：四個預檢代碼逐處計數且各有定義子句」（一審為只判整列 `Contains`，M27 因此存活）。

### D.6　AT-970-6-6（Unit，新增）— 指定重跑 — PASS

Given／When／Then：散文條文與契約 JSON／引擎常數對拍：W100 公式與 8500 門檻、第 N 次 FAIL＝ESCALATION、ADR D7 後半、四維權重百分比、BRIDGE 外環鍵前五值、Gate 0 永遠要求真人核准、V0 不得列入

來源 log：`run2_B.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-6-6.ps1`（自更新後的 TCS 逐字抽出）

```text
PASS 卡 2.2 與工作流 6.3 的 W100 公式係數＝review_params.weights×100
PASS 卡與工作流的 W100 門檻 N＝100×review_params.threshold
PASS 工作流與卡所有「第 N 次…ESCALATION」復述的 N＝引擎 RETRY_LIMITS[SCG_VALIDATION]
PASS ADR-001 D7 行含「審查預算採 FSM 預算」
PASS 工作流兩處權重百分比表列＝review_params.weights
PASS BRIDGE 9.2 外環鍵只准前五值，且前五值為外環集合
PASS 工作流第 8 章：產品內的 Gate 0 永遠要求真人核准
PASS 證據矩陣模板：V0（只憑記憶）不得列入
RESULT AT-970-6-6 PASS
```

> 新增 AT：八項散文條文與 `review_params` JSON、引擎 `RETRY_LIMITS` 對拍（回應一審 F-04）。突變複驗見 E.1。

### D.7　AT-970-7-0（共用區塊：FSM 暫存狀態目錄與版本目錄複本）— 指定重跑 — OK

來源 log：`run2_C.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-7-0.ps1`（自更新後的 TCS 逐字抽出）

```text
state dir = C:\Users\wuwei\AppData\Local\Temp\at970_a2a61472\fsm
version dir copy = C:\Users\wuwei\AppData\Local\Temp\at970_a2a61472\AISDLC_SDD\AISDLC_SDD_v0.30
```

> 預期輸出（TCS L981）：`state dir = <暫存目錄>/fsm`、`version dir copy = <暫存目錄>/AISDLC_SDD/AISDLC_SDD_v<LATEST>`，無錯誤——實際輸出相符，區塊 10 秒（複製版本目錄與 `scripts/`）。

### D.8　AT-970-7-E-1（Integration，負控，🔶）— 指定重跑 — PASS

Given／When／Then：🔶 負控：自動恢復預設開啟時第 3 次 FAIL 的回傳含 `auto_recovery`

來源 log：`run2_C.log`；指令區塊：`S\qa\fw2\at2\*_AT-970-7-E-1.ps1`（自更新後的 TCS 逐字抽出）

```text
round 3 (auto recovery default ON): retry_count=3 auto_recovery_key=True next_state=ESCALATION_FINAL
RESULT AT-970-7-E-1 PASS
--- 隔離探針（本鏡在 7-E-1 之後、7-Z 之前插入的唯讀指令）---
real repo abort dir, files dated 2026-11-02: 
copy abort dir, files dated 2026-11-02: ABORT-2026-11-02-auto-recovery-refused.md, ABORT-RAW-2026-11-02.yaml
copy abort report project line: **project**: research-at970c
```

> **一審 F-03 的核心證據**：7-E-1（自動恢復預設開啟，第 3 次 FAIL 觸發 `auto_recovery`）仍會寫 abort 報告，但現在寫在 `$tmp` 內的複本；真 repo 的 `build/reports/abort/` 今日檔案為空，C 段前後快照逐字相同（F.4）。7-Z 之後 `temp dir removed: True`（見 run2_C.log）。

### D.9　加跑（超出指定範圍）：其餘 27 個 AT 的 RESULT 行（逐字）

來源 log：`run2_S1.log`（20 個，含 6-1 的依賴重跑）、`run2_S2.log`（7 個 FSM 演練，皆從複本執行）。本節不改變上方判定表，只用來證明「沿用一審」在 TCS 檔與 `Invoke-Sdd` 改動後仍成立。

```text
RESULT AT-970-1-1 PASS
RESULT AT-970-1-2 PASS rc=0
RESULT AT-970-1-3 PASS files checked: 22
RESULT AT-970-1-E-1 PASS
RESULT AT-970-2-1 PASS specialized=23 templates=63 workflows=24
RESULT AT-970-2-2 PASS rc=0
RESULT AT-970-2-E-1 PASS
RESULT AT-970-3-1 PASS rc=0
RESULT AT-970-3-2 PASS rc=0
RESULT AT-970-3-E-1 PASS rc=1
RESULT AT-970-4-1 PASS
RESULT AT-970-4-2 PASS rc=1 n_fail=0 n_warn=3
RESULT AT-970-4-3 PASS
RESULT AT-970-4-E-1 PASS
RESULT AT-970-6-2 PASS verbs=show,transition,gate,spec-refreeze,spec-frozen
RESULT AT-970-6-3 PASS problems=0
RESULT AT-970-6-4 PASS placeholder-words=0 brace-placeholders=0
RESULT AT-970-6-5 PASS
RESULT AT-970-6-E-1 PASS
RESULT AT-970-7-1 PASS
RESULT AT-970-7-2 PASS
RESULT AT-970-7-3 PASS
RESULT AT-970-7-4 PASS
RESULT AT-970-7-5 PASS rc=0
RESULT AT-970-7-6 PASS
RESULT AT-970-7-E-2 PASS
RESULT AT-970-7-E-3 PASS
```

### D.10　其中與一審發現直接相關者的完整輸出

**AT-970-7-1**（F-05：`digest keys` 行與訂正後的預期逐字相同）

```text
gate PASS -> next_state=HUMAN_PENDING
spec-frozen rc=0 current_state=SPEC_FROZEN stage=Gate-0
digest keys: 00_research/evidence_matrix.md,00_research/issue_scope.json,01_specs/adr_draft.md,01_specs/PRD-v1.0.0.md
RESULT AT-970-7-1 PASS
```

**AT-970-6-5**（F-07：引用的上位編號 44 個（FR 11、AC 27）皆存在於 PRD）

```text
stale old names: 0
cited ids: 44 (FR 11, AC 27); absent in PRD: 0
RESULT AT-970-6-5 PASS
```

**AT-970-1-3**（F-06／TCS 檔形態：UTF-8、無 BOM、純 LF、檔尾換行（含已修改的 TCS））

```text
RESULT AT-970-1-3 PASS files checked: 22
```

## E. 突變複驗（F-04）

方法同一審：`git archive HEAD -- AISDLC_SDD docs/01_requirements/ResearchToPRD_PRD.md` 匯出沙箱（`%TEMP%\qa_mut\box`，26,219 檔），再把**工作樹的 TCS 與 PRD 覆蓋進沙箱**（雜湊與 repo 相同，已驗）——因 TCS 與 PRD 尚未提交；AT 區塊自更新後的 TCS 抽出。沙箱基線：22 個 AT（1～4 不含 4-4、6、7-5）全 PASS。每個突變＝單點變更→跑全部→還原位元組並驗雜湊（全部 `restored=True`）。

### E.1　一審存活的 9 個突變：二審全數被殺

| 編號 | 變更（單點） | 一審 | 二審實際紅的 AT | 二審結果 |
|------|--------------|------|-----------------|----------|
| M27 | SE-PRD 模板 P0-7 列第一處 `CITES_CANDIDATE` 改 `CITES_CAND`（該代碼在列內出現兩次） | 存活 | 6-1 | **殺死** |
| M27b | 同 M27，但列內兩處皆改 | 被 6-1 殺（對照） | 6-1 | **殺死** |
| S01 | 審查卡 §2.2 散文公式 `W100 = 30·A+25·P+25·Q+20·S` 改成 40/20/20/20 | 存活 | 6-6 | **殺死** |
| S02 | 工作流 §6.3 `W100 ≥ 8500（≥85）` 改 `≥ 8000（≥80）` | 存活 | 6-6 | **殺死** |
| S03 | 工作流 §2.3『第 3 次 FAIL 就是 ESCALATION』改『第 4 次』 | 存活 | 6-6 | **殺死** |
| S04 | ADR-001 D7 後半句『審查預算採 FSM 預算』改『採固定五輪』 | 存活 | 6-6 | **殺死** |
| S05 | 工作流 §6.2 表 ARCHITECTURE 30% 改 35% | 存活 | 6-6 | **殺死** |
| S06 | BRIDGE §9.2『外環鍵只准前五值』改『前六值』 | 存活 | 6-6 | **殺死** |
| S07 | 工作流 §8『Gate 0 永遠要求真人核准』改『可由 agent 代為核准』 | 存活 | 6-6 | **殺死** |
| S08 | 證據矩陣模板『V0（只憑記憶）不得列入』改『可列入』 | 存活 | 6-6 | **殺死** |

### E.2　二審追加探測（N-1）

| 編號 | 變更（單點） | 實際紅的 AT | 結果 |
|------|--------------|-------------|------|
| S09 | 工作流 §2.3 標題『最多 3 輪審查』改『最多 4 輪審查』 | — | **存活** |
| S10 | 工作流 §6.3 末段『最多 3 輪＋ESCALATION』改『最多 4 輪＋ESCALATION』 | — | **存活** |
| S11 | 工作流 §2.3『第 3 次 FAIL 就是 ESCALATION』改『第 4 次』（對照：6-6 條 (3) 範圍內，應被殺死） | 6-6 | **殺死** |

一審 M01～M33 與 G 組（邊界）針對的 AT（1～4、6-2～6-5、6-E-1、7-x）在 TCS 現檔**區塊未變**（TCS diff 只動 5-1／5-3／5-E-1／6-1／7-0 與新增 6-6，F.2），故該部分一審結論沿用（殺 33／34＋邊界 7／7；唯一存活 M27 已於上表殺死）。5-1／5-E-1 的變更邊界判準因 `$rootExempt` 改為 8 條，由 5-1／5-2／5-E-1 在真 repo 重跑 PASS 驗證；未重做 G 組小型 git 沙箱（一審 G 組是在「Source_Spec 已在 base」的假設下建的，與現行清單等價）。

## F. 機械檢核逐字

### F.1　FSM 現態、凍結記錄聯集與摘要複驗（`show --must-exist` 唯讀；`digest_check2.py`；框架自己的 `spec_digest.digest_doc`）

```text
current_state=PR_REVIEW  total_spec_frozen_count=2  escalation_count=0
retry current_count: SCG_VALIDATION=0, PR_REVIEW=0, RTM_VERIFY=0, RELEASE_READY=0
== decision_trace 末 6 筆（from -> to ; trigger ; reason 前 70 字）
  2026-11-02T04:04:48+00:00  SPEC_FROZEN -> TEST_CONTRACT_NEGOTIATED ; test_contract_enter ; Dev／QA 以 TCS 為 oracle；AT 文法 ADR-XPLAT-016 §8.1
  2026-11-02T04:04:48+00:00  TEST_CONTRACT_NEGOTIATED -> IMPLEMENTATION ; test_contract_exit ; TCS 的 AT 即 oracle；QA 三審 PASS；r9.20.3=not-satisfied（增量專案機械半段由 QA 人讀補位，B
  2026-11-02T06:16:13+00:00  IMPLEMENTATION -> PR_REVIEW ; cli_manual ; SCG-4 PR 審查開始：框架側方法層已於 commit 25c66981 落檔（九個新檔＋13 檔編修；FRAMEWORK_STATUS
  2026-11-02T07:52:51+00:00  PR_REVIEW -> SPEC_AUDIT ; cli_manual ; SCG-4 一審 F-01／F-02：rootExempt 補來源規格逐字檔、追溯表改真 Stage-1 記錄；PRD／ADR-017 同步
  2026-11-02T07:52:51+00:00  SPEC_AUDIT -> SPEC_AUDIT ; spec_refreeze ; SCG-4 一審 F-01／F-02 勘誤：PRD（D-46 列、§9.0）與框架 TCS（rootExempt 8、追溯表＝真記錄、7-0
  2026-11-02T07:52:51+00:00  SPEC_AUDIT -> PR_REVIEW ; cli_manual ; SCG-4 二審開始（一審 F-01～F-07 已修）
== frozen_stages 全部條目
  [0] stage=Stage-1 frozen_at=2026-11-02T04:04:47+00:00 docs=5 approved_by=掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d
        AISDLC_SDD/CLAUDE.md  sha256:09d88638cd8e3d44…
        AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md  sha256:c0732753d2a2e7b1…
        AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md  sha256:ca913bb1f62f97ef…
        docs/01_requirements/ResearchToPRD_PRD.md  sha256:2237bfeb80d72d90…
        AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md  sha256:c2935ae10317a9db…
  [1] stage=Stage-2 frozen_at=2026-11-02T04:04:48+00:00 docs=1 approved_by=掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d
        AISDLC_SDD/AISDLC_SDD_v0.30/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md  sha256:e2773302e38b82b1…
  [2] stage=Stage-2 frozen_at=2026-11-02T07:52:51+00:00 docs=6 approved_by=掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d
        AISDLC_SDD/CLAUDE.md  sha256:09d88638cd8e3d44…
        AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md  sha256:c0732753d2a2e7b1…
        AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md  sha256:ca913bb1f62f97ef…
        docs/01_requirements/ResearchToPRD_PRD.md  sha256:179e839fe318388a…
        AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md  sha256:c2935ae10317a9db…
        AISDLC_SDD/AISDLC_SDD_v0.30/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md  sha256:9602289ef45c3de5…
  最後一筆的其他欄位鍵：['kind', 'reason', 'supersedes']
    supersedes=2026-11-02T04:04:48+00:00
    reason=SCG-4 一審 F-01／F-02 勘誤：PRD（D-46 列、§9.0）與框架 TCS（rootExempt 8、追溯表＝真記錄、7-0 隔離、6-6 散文核對）修訂；發生在 PR_REVIEW→SPEC_AUDIT
== 有效摘要（聯集）6 鍵 vs 現檔重算（digest_doc）
  SAME  AISDLC_SDD/CLAUDE.md
        frozen=sha256:09d88638cd8e3d441c3f1bd94cbf289beff767cd9455063263125c06b9142908
        now   =sha256:09d88638cd8e3d441c3f1bd94cbf289beff767cd9455063263125c06b9142908
  SAME  AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md
        frozen=sha256:c0732753d2a2e7b19678ec48d169845e3280a3b06422325a966a9fd4b07dde28
        now   =sha256:c0732753d2a2e7b19678ec48d169845e3280a3b06422325a966a9fd4b07dde28
  SAME  AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md
        frozen=sha256:ca913bb1f62f97ef4b06fd698c2c5c3b0327f464fa90b1760d8a07a8b4ec98fa
        now   =sha256:ca913bb1f62f97ef4b06fd698c2c5c3b0327f464fa90b1760d8a07a8b4ec98fa
  SAME  docs/01_requirements/ResearchToPRD_PRD.md
        frozen=sha256:179e839fe318388ad3522de3d7b6f8bda222f6b808dff23455e32a3ae3007ed8
        now   =sha256:179e839fe318388ad3522de3d7b6f8bda222f6b808dff23455e32a3ae3007ed8
  SAME  AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md
        frozen=sha256:c2935ae10317a9db4992057db14a0e58983005711f9072f0b74cd39829260180
        now   =sha256:c2935ae10317a9db4992057db14a0e58983005711f9072f0b74cd39829260180
  SAME  AISDLC_SDD/AISDLC_SDD_v0.30/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md
        frozen=sha256:9602289ef45c3de5634e8e42a04f0eea352e06d1b09e3ec3b49e1c03255f3594
        now   =sha256:9602289ef45c3de5634e8e42a04f0eea352e06d1b09e3ec3b49e1c03255f3594
== TCS〈增量追溯表〉U1～U5 vs 有效摘要
  U1 SAME  AISDLC_SDD/CLAUDE.md
  U2 SAME  AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md
  U3 SAME  AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md
  U4 SAME  docs/01_requirements/ResearchToPRD_PRD.md
  U5 SAME  AISDLC_SDD/AISDLC_SDD_v0.30/docs/02_architecture/adr/ADR-001-research-to-prd-framework-layer.md
table_rows=5  drift_count=0
```

### F.2　TCS 宣稱的對帳（`extra_checks2.py`）與相對一審 commit 的差異

```text
== 1. 勘誤 6 的 numstat 數字（01d9be6e → 25c66981）
  篩選＋排除（TCS 指令）：13 檔 +176／−22   （TCS 宣稱 13 檔 +176／−22）→ 一致
  不加篩選（-- AISDLC_SDD）：24 檔 +4632／−29   （TCS 宣稱 24 檔 +4632／−29）→ 一致
  只加 --diff-filter=M：15 檔 +184／−29   （TCS 宣稱 15 檔 +184／−29）→ 一致
== 2. 勘誤 7 引用的上位 AC 在 PRD 的定義（前 170 字）
  AC-R2P-11-7: - **AC-R2P-11-7**（M＋E）〔新增；D-22〕Given ADMIN 確認分流 When 執行 Then Bridge 於目標根建內環鍵 `<sub>-<slug>`（軌道 B 為 `<project-name>`）並採納基線：`show`（唯一建檔點）＋5 次 `transition`（`--reason` 註明「bas
  AC-R2P-12-6: - **AC-R2P-12-6**（M）〔新增〕Given 軌道 A 完成 When 檢查目標分支變更 Then 僅含發佈的規格檔與「落點 stub」（`docs/` 內，提示人去改 SSOT）；根 `CLAUDE.md`、`.claude/`、落點 SSOT、`tools/` 零變更（`git diff --name-only` 核對；
  AC-R2P-10-9: - **AC-R2P-10-9**（M）〔新增；D-23〕Given 既有 `POST /sdd/fsm/{project}:freeze` When 以研究工作區外環鍵、`docs[]` 不含 TCS 呼叫 Then 仍回 422 `missing_tcs`（契約不變、既有 AT 不退步）；Gate 0 只走 `:approve-bas
== 3. D-46 根層例外清單（8 條）：各文件是否同為 8 條、且含來源規格逐字檔
  TCS $rootExempt＋$rootExemptDirs 條數：8（8 ✓）
  PRD C.7 D-46 列         8 個標記皆在：True
  PRD §9.0 根層連動列         8 個標記皆在：True
  ADR-017 §D7 機械核對法      8 個標記皆在：True
  PRD §9.0 來源規格逐字檔列：含『列入』且含『首次入庫於 W0 落檔 commit』：True；舊句『先於各鍵 Stage-1 採納的基準 commit，故不在』已刪：True
  計畫書 :31 含『列入』：True；舊句已刪：True
== 4. TCS §1 映射表計數
  映射表列數=35（宣稱 35）；類型分佈={'Unit': 13, 'Integration': 18, 'Contract': 3, 'E2E': 1}（§3 宣稱 Unit 13、Integration 18、Contract 3、E2E 1）；正控 26／負控 9（宣稱 26／9）；✅ 27／🔶 8（宣稱 27／8）
  檔頭計數句      含『AT 35 個（正控 26、負控 9』：True
  §1 覆蓋率句    含『已映射 AT 數: 35（✅ 27、🔶 8）』：True
  §3 類型分佈    含『Unit 13、Integration 18、Contract 3、E2E 1』：True
  §6 追溯項     含『35 個 AT』：True
  SCG-4 通過標準 含『7 個 AC、35 個 AT』：True
```

`git diff --numstat 25c66981 --`（工作樹相對一審 commit；框架側四檔）：

```text
142	75	AISDLC_SDD/AISDLC_SDD_v0.30/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md
1	1	AgentConsole/docs/04_planning/ResearchToPRD_Plan.md
3	3	docs/01_requirements/ResearchToPRD_PRD.md
1	1	docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md
```

`git diff --name-only 25c66981 HEAD -- AISDLC_SDD docs .github tools .claude` 輸出：（空）

### F.3　TCS 現檔的行號座標（`tcs_lines.py`）

```text
total lines: 1892
F01 rootExempt 新增一行                          -> 573
F01 5-1 判定 -eq 8                             -> 602
F01 5-1 預期輸出 root exempt entries: 8          -> 605
F01 5-1 描述（逐字 8 條＋勘誤 1 句）                    -> 561
F01 5-E-1 $okPaths 加該檔                       -> 573,668
F01 5-E-1 $c6 含 .md.bak 且 -eq 4              -> 674
F01 W-F6 共 8 條                               -> 75,1263
F01 ⚖4 逐字清單共 8 條                             -> 1263
F01 §5 資料表 8 條                               -> 1219
F02 輸入快照列                                    -> 23
F02 增量追溯表說明（真實採納集合）                          -> 103
F02 U1                                       -> 107
F02 U5                                       -> 111
F02 改動前基準                                    -> 113
F02 5-3 描述（聯集）                               -> 619
F02 5-3 $eff 聯集                              -> 629
F02 5-3 逐鍵比對                                 -> 634
F02 5-3 判定 -eq 5                             -> 636
F02 §6 收尾段                                   -> 1254
F03 §2.7 引言（隔離）                              -> 905
F03 7-0 區塊標題                                 -> 941
F03 7-0 $fsmSdd                              -> 946
F03 7-0 $fsmVd                               -> 948
F03 7-0 複製版本目錄                               -> 949
F03 7-0 複製 scripts                           -> 950
F03 Invoke-Sdd 從複本執行                         -> 954
F03 7-0 印出 version dir copy                  -> 978
F03 7-0 預期輸出                                 -> 981
F03 7-Z 說明（含複本）                              -> 1177
F03 ⚖8（repo 零寫入）                             -> 1267
F04 6-1 描述（逐處計數）                             -> 684,1869
F04 6-1 $codeCnt                             -> 701
F04 6-1 $p07Ok 逐處計數迴圈                        -> 703
F04 6-1 判定列                                  -> 712
F04 §1 映射表 6-6                               -> 170
F04 6-6 描述                                   -> 843
F04 6-6 區塊首行                                 -> 846
F04 6-6 判定                                   -> 879
F05 7-1 預期輸出（排序已訂正）                          -> 1002
F06 D5 列（落檔 commit 25c66981）                 -> 59
F06 AT-970-1-1 Given                         -> 235
F06 §2 引言（預期輸出對落檔後 repo）                     -> 191
F06 ⚖1 重現指令                                  -> 1260
F06 ⚖7（落檔 commit）                            -> 1266
F07 上位對照 AC-970-5 列                          -> 85
勘誤表標題                                        -> 1860
勘誤 1                                         -> 1866
勘誤 2                                         -> 1867
勘誤 3                                         -> 1868
勘誤 4                                         -> 1869
勘誤 5                                         -> 1870
勘誤 6                                         -> 1871
勘誤 7                                         -> 1872
勘誤 8                                         -> 1873
勘誤 9                                         -> 1874
--- 殘留的「FRAMEWORK_EDITS／FRAMEWORK_VERIFY」行： [1871]
--- 殘留的「34 個 AT／AT 34／34 個」行： [(1873, '| 8 | 2026-11-02 | 檔頭計數、§1 表與覆蓋率、§3、§6、SCG-4 通過標準 | 「AT 34 個')]
```

### F.4　對真 repo 的唯讀證明

四段 AT 執行（`run_real2.ps1`）各自前後的快照比對（每段輸出皆為 `SNAPSHOT-DIFF: none`；pre／post 快照 sha256 皆 `EF45753E554A236E3A175870ADEE8BCA0B3FE08B92CDD9453F550E4F687A3F69`、4143 行）：B2（5-x／6-x，driver rc=0，1 秒）、C2（7-0／7-E-1，driver rc=0，12 秒）、S1（20 個，driver rc=0，4 秒）、S2（7 個，driver rc=0，11 秒）。報告組裝當下再現查：

```text
git status --porcelain -- AISDLC_SDD tools .claude .github：條數=1（M AISDLC_SDD/AISDLC_SDD_v0.30/docs/03_testing/contracts/TCS-ResearchToPRD-Framework-20261102.md）
5CDC3ACD38B17281F2F20D7E4B8E423E99B884FEBA1303BDEDC6E8AD32DCC9DB  11175  FSM-STATE-sdd-research-to-prd.yaml
E1554E56C634864CAD5260FD260473D76FF6FA8190C6C7033F3ED06DED4697EF  10965  FSM-STATE-sdd-research-to-prd.yaml.bak
（二審起始：5CDC3ACD38B17281F2F20D7E4B8E423E99B884FEBA1303BDEDC6E8AD32DCC9DB  FSM-STATE-sdd-research-to-prd.yaml／E1554E56C634864CAD5260FD260473D76FF6FA8190C6C7033F3ED06DED4697EF  .yaml.bak）
真 repo `build/reports/abort/` 今日（2026-11-02）檔案：無
SNAPSHOT vs B2-pre.txt: identical (lines=4143)
```

### F.5　AT-970-6-6 條 (3) 的實際覆蓋站點（`nesc_count.py`；與 TCS 區塊相同的正則）

```text
workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md：命中 4 處
   L141  N=3  「第 3 次 FAIL 就是 ESCALATION」
   L184  N=3  「第 3 次 → ESCALATION」
   L473  N=3  「第 3 次 FAIL 進 ESCALATION」
   L682  N=3  「第 3 次即 ESCALATION」
docs_template/sdd/requirements/ADVERSARIAL-REVIEW-CARD-TEMPLATE.md：命中 2 處
   L74  N=3  「第 3 次 `gate FAIL` 即 ESCALATION」
   L178  N=3  「第 3 次 `gate FAIL` 即 ESCALATION」
SDD_RESEARCH_TO_PRD.md：以『第 N 次 FAIL／最多 N 輪／上限 N』寫法復述預算、但不在 6-6 正則涵蓋行內的有 6 處：[(35, '最多 3 輪'), (139, '最多 3 輪'), (150, '最多 3 輪'), (150, '最多 4 輪'), (165, '第 3 次 FAIL'), (406, '最多 3 輪')]
ADVERSARIAL-REVIEW-CARD-TEMPLATE.md：以『第 N 次 FAIL／最多 N 輪／上限 N』寫法復述預算、但不在 6-6 正則涵蓋行內的有 0 處：[]
```

### F.6　聯集語意的程式依據（唯讀引用）

```text
AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/state_loader.py:325-332
        """OBS-SI-108（F-17）：為「已凍結、後來被合法修訂」的規格**追加**一筆重記條目，回該條目。

        只追加、不改寫舊條目（舊條目留作歷史）：`stage` 取最近一筆的 stage（所以 `current_stage_key()` 不變、
        每階段 auto-compact 上限不會被重記洗掉）、`supersedes` 記被取代那筆的 `frozen_at`、`kind` 標
        `refreeze`、`reason` 寫修訂內容。**不碰**任何 retry 計數與 `total_spec_frozen_count`——重記不是新的
        SPEC_FROZEN 里程碑，否則它會變成洗掉 R-9.1 重試預算的後門。條目只含這次被重新背書的文件；消費端
        （AutoClaude `check_digest`、Bridge）取全部條目的摘要聯集、同鍵後者勝出，所以沒被點名的文件仍沿用
        先前條目的摘要（誠實地：它們這次沒被重新檢視）。
AutoClaude/autoclaude/infra/adapters/_sdd_frozen_gate.py:182-197
    取全部 `frozen_stages[*].spec_doc_digests` 的聯集（同鍵多階段出現時後一階段勝出＝以最近一次
    凍結為準）：
      - 聯集為空（舊狀態檔，或凍結時沒帶 --digest）→ "absent"，維持放行（呼叫端須出聲）；
      - 有摘要但規格檔不在任何階段的清單內 → SpecNotFrozenError；
      - 吻合 → "verified"；不吻合 → SpecDigestMismatchError（SpecNotFrozenError 的子類）。
    """
    union: dict[str, str] = {}
    for stage in frozen_stages:
        digests = stage.get("spec_doc_digests")
        if digests is None:
            continue
        if not isinstance(digests, dict):
            raise SpecNotFrozenError(
                f"frozen_stages 的 spec_doc_digests 不是映射（{type(digests).__name__}）"
                "——凍結摘要格式不合，無法比對，fail-closed")
        union.update({str(k): str(v) for k, v in digests.items()})
```

## G. 誠實劃界

1. **審查者獨立性（TCS ⚖6）**：同一審——本鏡與作者、落檔者皆為 AI，補償＝獨立 session、逐字貼輸出、主控另行親驗；不宣稱滿足 R-9.20.3 型獨立性。
2. **落檔狀態是工作樹、尚未提交**：TCS、根層 PRD、ADR-XPLAT-017、計畫書的二審修法目前是未提交修改（HEAD `b1f308f6` 的 TCS 仍是一審版）。本鏡判定針對工作樹；5-1 是「起點 commit 對工作樹」的比對，提交前後結果等價，5-3 讀的是狀態檔，不受提交影響。**建議提交後再跑一次 5-1 與 5-3 作收尾確認**（本鏡不碰 git，未做）。
3. **refreeze 與凍結常態規則**：重記條目的 `approved_by` 引「凍結常態規則（根 CLAUDE.md）」，其前提是「審查 PASS＋主控親驗」；這次重記發生在一審 FAIL 之後、二審之前，性質是勘誤重記（`state_loader.py:329-330`：重記不是新的 SPEC_FROZEN 里程碑，不動重試計數與 `total_spec_frozen_count`，現仍 2），不是新的凍結。該規則是否涵蓋「FAIL 後的勘誤重記」是主控／掌舵者的判斷，本鏡僅陳述事實，不裁決。
4. **加跑超出指定範圍**：指定範圍是 8 項；本鏡另加跑 27 個 AT（理由見 A）。這些結果只作「沿用一審成立」的佐證，未改變指定項判定；若主控認定不需要，可忽略 D.9／D.10。
5. **4-4（ci-gate）沿用一審**：一審 `rc=0`（77 秒；逐軌計數 `v0.01:1478 v0.30:2250 scripts/tests:425`）。二審未重跑——`AISDLC_SDD` 樹自 `25c66981` 起只有 TCS 一檔差異（F.2），ci-gate 測的程式、agent、模板、工作流皆未動；且它會改寫被忽略的快取檔（一審已揭露），違「全程唯讀」。
6. **5-3 的視窗前提**：該 AT 要求在「本鍵視窗」執行；本鏡非該視窗，在 driver 內暫設三件組（含 `SDD_ACTIVE_VERSION=0.30`，其在 `fsm_runtime.py` 只出現於註解、無功能影響）做唯讀 `show`，跑完清除；狀態檔雜湊前後相同。
7. **突變沙箱**：同一審——`git archive` 匯出（LF 行尾、無 `.git`、無 `.venv`），因 TCS 與 PRD 未提交而以工作樹檔案覆蓋；ci-gate 不在突變副本上跑。E 的複驗只針對一審存活者與 N-1 探測，沒有重做全部 M／G 組（理由見 E）。
8. **抽樣邊界**：一審的 31 項規格一致性抽樣未重做；二審的對帳聚焦在 TCS 勘誤逐條（numstat、上位 AC、D-46 清單、計數）。TCS 修法以外的框架資產（工作流、模板、agent、ADR）自一審 commit 起位元組未變（F.2），其一審結論沿用。
9. **併行修改**：工作樹同時有 AgentConsole 開發棒在動（5-1 的 `changed paths` 本回合為 102），皆在 `AgentConsole/` 豁免前綴內，不屬本鏡審查範圍。
10. **本檔所有數字**（AT 結果、突變殺／存、numstat、摘要值、行號）皆來自本回合真跑的輸出；`RESULT` 行是 TCS 區塊自己的判定，本鏡另以預期輸出文字逐一對照。
11. **暫存殘留（擁有者未確定，推定非本鏡）**：收尾時 `$env:TEMP` 下只剩一個空目錄 `at970_017853a1`（建立 2026-11-02T15:39:22+08:00，內容為空）。它不在本鏡任何一輪 log 的暫存目錄名單內（一審四個：`c4c1787a`／`961a504d`／`bf90f88b`／`1b9924f0`，log 時間 14:25～14:30；二審四個：`beec6b82`／`a2a61472`／`56fc10c7`／`ab2f4b32`，log 時間 19:03～19:04），建立時刻落在兩輪之間，且本鏡這八個目錄已全數清掉（現查 `$env:TEMP` 只列得到它一個）。研判是他人在兩輪之間跑 TCS 區塊的殘留；本鏡不動非自己建立的物件，故未刪，也不影響任何判定。

## 附錄 R1　一審發現表（原文）與一審→二審差異

一審判定行（原文）：**判定：一審 FAIL**（P1 0／**P2 2**／P3 2／P4 4；規則：P1 0 且 P2 0 ⇒ PASS）。

一審發現表（原文，未改動）。**提示：本表內的「D.x／E.x／F.x／G.x」等章節引用，指的是一審報告（`SCG4-REVIEW-ResearchToPRD-Framework-20261102.R1-first-review.md`）內的章節，不是本二審報告的章節。**

### R1-C　一審發現表

| 編號 | 嚴重度 | 座標 | 事實（證據指標） | 處置建議 |
|------|--------|------|------------------|----------|
| F-01 | **P2** | TCS AT-970-5-1 的 `$rootExempt`（TCS §2.5）、§7 ⚖4、§5；PRD `ResearchToPRD_PRD.md` C.7 D-46 與 §9.0 落點表（`:1165`）；計畫書 `ResearchToPRD_Plan.md:31`；ADR-XPLAT-017 §D7（`:112`） | **AT-970-5-1 `RESULT … FAIL violations=1`**（D.2）；違規路徑＝`docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`。該檔在 `01d9be6e` 不存在（`git cat-file -e 01d9be6e:<path>` rc=128），首次入庫於 HEAD 的 `25c66981`（`git log --follow`：`A`）。PRD:1165 與 Plan:31 的理由句「先於各鍵 Stage-1 採納的基準 commit，故不在 D-46 的根層例外清單內」與 git 事實不符；ADR-XPLAT-017 §D7 機械核對法 (c) 逐字重跑亦只剩這一條（F.7）。TCS／PRD D-46／ADR §D7 三份清單彼此一致（SC-21），故是**前提錯誤**不是抄漏；SCG-0 一審 F-10 曾登記此檔（P3「落實」），落實句即為該錯誤前提。**驗證**：把該檔放進沙箱 base commit → 5-1 `PASS violations=0`（G00，E.2）；對真 repo 把第 8 條加入 `$rootExempt` 並把字面 7 改 8 → 5-1／5-2／5-E-1 全 PASS（F.9a） | 同一 commit 收齊：TCS 勘誤（5-1 的 `$rootExempt` 加第 8 條、`root exempt entries: 8`、`-eq 8`；5-E-1 的 `$okPaths` 加該路徑；§5 資料表與 §7 ⚖4「逐字 7 條」、FRD-lite 非目標句）；PRD D-46 清單與 §9.0 該列的理由句；ADR-XPLAT-017 §D7 機械核對法清單；Plan:31；再 `spec-refreeze` TCS 與 PRD |
| F-02 | **P2** | TCS〈增量追溯表〉U1～U3（TCS 第 103～109 行）、AT-970-5-3、§6 收尾段、§7 ⚖1；狀態檔 `…/build/reports/sdd-dogfood/FSM-STATE-sdd-research-to-prd.yaml` 的 `frozen_stages[Stage-1]` | **AT-970-5-3 `RESULT … FAIL rc=0 table_rows=3`**，三個鍵「凍結＝」皆空（D.3）。真 Stage-1 記錄：鍵為專案根相對路徑（`AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md`、…；`--root`＝monorepo 根，因含根層 PRD）、**五份**（另有 `docs/01_requirements/ResearchToPRD_PRD.md`、ADR-001），值＝改動**後**內容摘要（`09d88638…`／`c0732753…`／`ca913bb1…`＝HEAD 現值）。TCS 表：鍵相對 `AISDLC_SDD/`、三份、值＝`01d9be6e` 版內容摘要（`e1a28018…`／`7c6d5620…`／`c44b47a8…`；F.8 以框架自己的 `digest_doc` 對 `git show 01d9be6e:` 重算證實）。Stage-1 在改動落檔之後才採納，所以 TCS 的前提「Stage-1 採納當下（本鍵改動之前）」不成立；§6 收尾段與 ⚖1 的「收尾 `spec-refreeze` 三份上位文件」也因此失去前提（三份已記 post-edit 摘要）。六份凍結文件現值與記錄零漂移（F.8）。**驗證**：沙箱 TCS 表改成真記錄（鍵＋值）→ 5-3 `PASS rc=0 table_rows=3`，真狀態目錄雜湊前後相同（F.9b） | TCS 勘誤：表的鍵形態、份數與 `--root` 句（五份、monorepo 根）、值＝post-edit；另保留 `01d9be6e` 版摘要作「改動前基準」欄（可由 `git show 01d9be6e:<path>` 重算）；§6 收尾段與 ⚖1 改為「三份已記 post-edit 摘要，其後再改才需 `spec-refreeze`（PRD 同）」；再 `spec-refreeze` TCS |
| F-03 | P3 | TCS §2.7 引言「演練只寫 `$tmp` 之下的暫存狀態目錄」；AT-970-7-E-1；AT-970-7-Z；`tools/fsm_runtime/snapshot.py:17`（`SNAPSHOT_DIR = REPO_ROOT / "build" / "reports" / "abort"`） | 對真 repo 跑 C 段後，C 段前後快照差異恰為兩個新檔：`v0.30/build/reports/abort/ABORT-2026-11-02-auto-recovery-refused.md`（內文 `project: research-at970c`，即 7-E-1 的暫存鍵）與 `ABORT-RAW-2026-11-02.yaml`（304 位元組，只有該一筆事件）。成因：`SNAPSHOT_DIR` 是模組常數、不隨 `SDD_STATE_DIR`；框架自己的測試會 monkeypatch 它以「避免污染真實 build/reports/abort/」（例：`tools/fsm_runtime/tests/test_auto_compact_rate_limit.py:216`、`test_phase_h.py:626`）。兩檔被 `AISDLC_SDD/.gitignore:313` 忽略，不進 git，但 TCS 的隔離宣稱與 7-Z 的收尾都沒涵蓋。**本鏡已把兩檔複本存入 `S\qa\fw\evidence\` 後自行刪除，快照回到與 C 段前相同**（G.5） | 7-E-1／7-Z 收尾補「刪除該暫存鍵產生的 abort 報告」，或改在拋棄式版本目錄複本上跑 7-E-1；§2.7 引言改為「除 7-E-1 會在 `build/reports/abort/` 留下被 git 忽略的報告外，只寫 `$tmp`」 |
| F-04 | P3 | AT-970-6-1（P0-7 列判準）；TCS 對散文條文的覆蓋 | 測試鑑別力缺口，共 9 個存活突變（E.1、E.3）：**M27**＝SE-PRD 模板 P0-7 列內 `CITES_CANDIDATE` 出現兩次，改一處仍 PASS（6-1 以 `Contains` 判整列；兩處皆改的 M27b 則被殺）。**S01～S08**＝散文復述的關鍵數字／句子無任何 AT 比對：卡模板 §2.2 的 `W100 = 30·A + 25·P + 25·Q + 20·S`（S01 改成 40/20/20/20 仍全 PASS）、工作流 §6.3「`W100 ≥ 8500`」（S02）、§2.3「第 3 次 FAIL 就是 ESCALATION」（S03）、§6.2 表的 ARCHITECTURE 30%（S05）、ADR D7 後半句（S04）、BRIDGE §9.2「外環鍵只准前五值」（S06）、工作流 §8「Gate 0 永遠要求真人核准」（S07）、EVIDENCE 模板「V0 不得列入」（S08）。JSON 契約有檢核器守，散文復述沒有；D-42 又明訂「判定公式只住審查卡模板 §2.2」，復述處漂移即與 PRD 脫鉤 | 加三個便宜判準即可封口：(a) 6-1 對 P0-7 列改判「四個代碼各自出現在其定義子句（『否則 代碼』）內」；(b) 新 AT 以正則自卡模板／工作流／PRD 抽 `W100` 公式與 `≥ 8500`、§6.2 百分比，與 `review_params` JSON 對拍；(c) 6-2 補工作流 §8「永遠要求真人核准」一句 |
| F-05 | P4 | TCS AT-970-7-1 的「預期輸出」第三行 | 預期寫 `digest keys: …/issue_scope.json,01_specs/PRD-v1.0.0.md,01_specs/adr_draft.md`；實跑為 `…/issue_scope.json,01_specs/adr_draft.md,01_specs/PRD-v1.0.0.md`（`Sort-Object` 不分大小寫，`adr_draft` 在 `PRD-v1.0.0` 之前）。`RESULT PASS` 不受影響（AT 兩側用同一排序） | 勘誤該行排序（TCS 的 🔶 規則：預期值讀錯走勘誤） |
| F-06 | P4 | TCS D5 列、§7 ⚖1、⚖7 | 引用 `FRAMEWORK_EDITS.md`（E01～E36）與 `FRAMEWORK_VERIFY.md`（步驟 9b）作重現依據，兩檔是 SD-B 的過程文件、不在 repo；他機無法照 TCS 重現。本鏡改以 `git diff --numstat 01d9be6e 25c66981` 重算：+176／−22 與 ⚖1 宣稱逐值相同、22 行被移除行皆為計數／日期／註記的就地延伸（F.10） | 勘誤時把重現指令改成 `git diff --numstat <起點> HEAD -- <13 檔>`，並刪去不可達的檔名引用 |
| F-07 | P4 | TCS〈上位需求對照〉AC-970-5 列 | AC-970-5（變更邊界與追溯）對映 `AC-R2P-10-9`，但該 AC 是 `:freeze` 的 422 `missing_tcs` 契約；變更邊界的真正上位是 ADR-XPLAT-017 §D7 與 PRD §9.0 落點表（NFR-R2P-08-1 只談文件最小集） | 勘誤該列的上位引用 |
| F-08 | P4 | `v0.30/docs/06_quality/` | 現只有既有的 `HUB-GOVERNANCE-SPEC.md`；TCS §6 要求的 `RTM-ResearchToPRD-Framework-20261102.md` 與 SCG-4 證據檔尚未落檔（符合 PR_REVIEW 階段：RTM_VERIFY 在其後）。本報告即證據檔，請主控落檔於該目錄 | RTM_VERIFY 前補 RTM；本報告改名落檔 |

**未列入發現、但已查證的主張**（皆來自本回合重跑）：變更集合恰為 24 條白名單路徑（F.7 (a)：24 路徑、扣掉豁免後 0）；`_HAPPY_PATH`／`formal/`／`governance/rules/`／根層 `tools/`／`.claude/` 零差異（5-2 PASS、F.7 (b)(d)）；`agentconsole-ci.yml` 的差異只有兩段 `paths`（F.7 (e)，符合 ADR §D7「只有 paths」）；D-62(4) 的既有債（`FILE_DIRECTORY_RULES.md` 未登記四個新模板）已記於 EVOLUTION_LOG 已知邊界（SC-30）；⚖1 的「只增不減」numstat 宣稱逐值成立（F.10）；工作流／TCS 內引用的引擎行號座標：本鏡抽查的（`transition_rules.py` 的 T:13、14、19、26～29、35、38、46、66、68、77-78、267-268、300-302、305-307、323-328；`fsm_runtime.py` 的 R:328-336、339-352、526-547、576-578）皆與現碼相符，其餘（如 R:596-641、R:1194-1218、`state_loader.py`）本鏡未逐一核對。

**差異表（一審→二審）**

| 編號 | 一審嚴重度 | 二審 | 關閉證據 |
|------|------------|------|----------|
| F-01 | P2 | 已修 | 5-1 PASS（`violations=0`、`root exempt entries: 8`）、5-2 PASS、5-E-1 PASS；PRD／ADR-017／計畫書同批訂正（F.2 §3） |
| F-02 | P2 | 已修 | 5-3 PASS（`rc=0 table_rows=5`）；refreeze 後聯集 6 鍵 SAME（F.1） |
| F-03 | P3 | 已修 | 7-0 隔離＋7-E-1 PASS；真 repo 零寫入、abort 報告落在複本（D.8、F.4） |
| F-04 | P3 | 已修 | 6-1／6-6 PASS；一審 9 個存活突變全被殺（E.1） |
| F-05 | P4 | 已修 | 7-1 預期輸出排序訂正（L1002），實跑逐字相同（D.10） |
| F-06 | P4 | 已修 | TCS 已無不可達的過程文件引用；numstat 三個數字逐值一致（F.2） |
| F-07 | P4 | 已修 | 上位引用改為 PRD §9.0／ADR-017 §D7＋AC-R2P-11-7／12-6，定義核對一致（F.2） |
| F-08 | P4 | 未結 | RTM／證據檔尚未落檔（流程性） |
| N-1 | P4 | 二審新增 | 6-6 條 (3) 範圍外的「最多 N 輪」復述未受守衛（S09／S10 存活） |

---

## 二審後附記（主控，2026-11-02 晚間，RELEASE_READY 態；所有數字取自主控本回合真跑的工具輸出）

- **FSM**：`gate PR_REVIEW PASS` rc 0（`next_state` RTM_VERIFY）→ RTM 落檔 `docs/06_quality/RTM-ResearchToPRD-Framework-20261102.md`（一審 F-08 結案）→ `gate RTM_VERIFY PASS` rc 0（`next_state` RELEASE_READY）。
- **N-1 修法（勘誤 10）**：AT-970-6-6 加第九檢核 `(?<!＝)最多 (\d+) 輪`（工作流 §1 流程圖、§2.3 標題、§2.3 結論句、§6.3 末段，審查卡 §2.3，ADR-001 預算語意列，共六處；§2.3 對照句「＝最多 4 輪」以前置「＝」排除；`-ge 6`），描述八改九、預期輸出八行改九行、§1 列補述；訂正後 TCS sha256 `8514830713af…`；`spec-refreeze --doc <TCS>` rc 0（Stage-2，supersedes 2026-11-02T07:52:51Z）。
- **主控實跑 AT-970-6-6**（自 TCS 現檔抽出的區塊，36 行；驅動器 `drv66.ps1`）：真 repo 九行 `PASS …`、`RESULT AT-970-6-6 PASS`。突變重放（六檔最小複本、逐一替換字串）：S09 工作流 §2.3 標題 3→4、S10 §6.3 末段 3→4、S14 §1 流程圖 3→4、S15 §2.3 結論句 3→4、S16 審查卡 §2.3 3→4、S17 ADR-001 預算語意 3→4 ⇒ 六個皆第九行 `FAIL`、`RESULT AT-970-6-6 FAIL`；控制組 C01（對照句「＝最多 4 輪」改 5）九行仍 `PASS`、`RESULT AT-970-6-6 PASS`（排除規則有效、不誤殺）。
- **AT-970-4-4**：`AISDLC_SDD/scripts/ci-gate.ps1` rc 0——「✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）／逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:2250 scripts/tests:425」。
- **二審第三點建議的收尾重跑**（RTM／報告落檔、勘誤 10 之後；驅動器 `drv5.ps1`，`$base=01d9be6e`）：`RESULT AT-970-5-1 PASS violations=0`（whitelist size 24、root exempt entries 8、changed paths 104）、`RESULT AT-970-5-2 PASS protected paths changed=0`、`RESULT AT-970-5-3 PASS rc=0 table_rows=5`。
- **二審第四點（refreeze 時序）**：第一次 refreeze（一審 FAIL 後、二審前，supersedes 04:04:48Z）的 WHY＝AT-970-5-3 以凍結記錄為 oracle，記錄不先重記該 AT 結構上無法 PASS；二審 PASS 後，常態規則的前提（審查 PASS＋主控親驗無 P1／P2）成立；勘誤 10 的第二次 refreeze 則在二審 PASS 與主控親驗之後執行，與常態規則順序一致。
- **二審第六點（暫存殘留）**：`$env:TEMP\at970_017853a1`（SD-B 15:39 實跑所留，空目錄）已由主控刪除；主控自己的驅動器暫存目錄亦已清除。
- **其餘零額度閘**（同回合真跑）：根層 `tools/tests/test_doc_loc_baseline_freshness_r60.py` 整模組 rc 0（F-01 訂正後的 ADR-XPLAT-017／PRD）；`framework_status_snapshot.py --check` rc 0。
- **RELEASE**：本鍵六檔 commit 後 push，雲端 `aisdlc-sdd-ci` 綠再 `gate RELEASE_READY PASS`（同整合輪 116 慣例）；push 時點受 Console 側 PKG-BR-A 收卷節制（pre-push 的根層 ruff 掃整個工作樹）。
