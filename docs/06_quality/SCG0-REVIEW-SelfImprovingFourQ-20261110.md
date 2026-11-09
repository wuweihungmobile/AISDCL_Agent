# SCG-0～3 一審：SelfImproving P5「頂尖專家四問」規格獨立審查

審查者：獨立 QA（Sonnet）；日期 2026-11-10；基準 HEAD `d864d638`；審查標的＝mirror 三檔（PRD v0.14、Operations SOP、TCS-SelfImproving-P5-20261110）。repo 全程唯讀。

## 結論：FAIL（一審；1 個 P1、4 個 P2，皆可在規格內修，無需推翻 D-EFQ-1～10）

## 發現

### P1-1　無人運轉取不到 Q4-L 的 M1／M4／M5 值，`FOURQ-LOOP-MISMATCH` 在無人運轉必然發生
- 座標：PRD AC-SI-41-4 ③、D-EFQ-14；SOP 範本步 3「Q4 末行的迴圈層量測值由你貼在輸入節」；`tools/lib/selfimproving/status.py:84-101`（`measure_value` 只有 `status／due／windows／candidates_unsettled／rollback_pending`，沒有 M1／M4／M5）；`tools/lib/selfimproving/meastat.py:188`（`metrics()`，唯一算 M1／M4／M5 之處）；`tools/lib/selfimproving/meawrite.py:115`（`measure` 在 `AUTOSDD_UNATTENDED` 下 `gate("measure")` 一律拒收）；`tools/lib/selfimproving/unattended.py:23`（`measure` 屬 C_CLASS）；READONLY 清單只有 `check／status／scan／card／export／capacity／issues／sched-show`。
- 問題：`si status` 文字與 JSON 只給 `due／measuring／candidates_unsettled`，M1／M4／M5 的值要經 `meastat.metrics`，而唯一把它印出來的 CLI 動詞 `measure` 既寫 `mea.*` 事件、又在無人運轉整個被拒。巡邏器生成任務書的占位符（`UPPER_FIELDS`）也沒有 Q4-L 欄位。無人主控沒有任何被授權的方式拿到值；若寫 NE，入帳時 CLI 以 `meastat` 重算得 `read（…）` ⇒ 逐欄比對不符 ⇒ rc 1。結果：無人運轉要嘛永遠 `fourq` 失敗，要嘛只能走 `--skip`（SOP 又禁），AC-SI-44-5 與 V36 的無人那一半不可達。互動運轉也要求主控手抄長串數字，⚖5 自己承認會因量測漂移被誤拒。
- 建議修法（擇一，推薦 A）：A. 讓 CLI 自己產生並驗證 Q4-L：新增唯讀動詞形態 `fourq --q4l`（歸 READONLY；與入帳比對共用同一取數函式）印出標準 Q4-L 一行，主控原樣貼入答案檔，審視者不再抄值（審視者也就不必知道量測值，同時解 P2-1）；B. Q4-L 不進答案檔，改由 CLI 在入帳時算出並寫進 `fourq.review` 事件的欄位（`m1／m4／m5／due`），答案檔只留 Q4-1…；比對消失、漂移誤拒消失。兩案都要補 AT：無人環境下取得 Q4-L 的路徑、NE 載體缺席的對照。

### P2-1　Q4 與 `proof` 把迴圈層指標交給提案者，與 AC-SI-22-3／SOP〈提案者隔離〉字面衝突，答案檔又落在提案者讀得到的目錄
- 座標：PRD AC-SI-22-3（L376：「任務書不含指標目標值、計算細節…迴圈層指標只對掌舵者與量測者呈現」）；SOP〈P3 動詞〉L310（「量測腳本與指標只對掌舵者與量測者（主控、QA）呈現」）；PRD AC-SI-43-3（交給提案者「Q4 的逐擬提案項（指標的根因鍵、基線值與 n、反證、收斂判準）」）；PRD AC-SI-20-4 ②（偵測只掃 held-out 目錄、`params.json`、量測腳本）；落點 `docs/06_quality/SelfImproving_Proposals/_fourq/<RUN>.md`（repo 內，提案者有 Read／Grep／Glob）。
- 問題：（a）審視者不在原清單的「掌舵者與量測者」內，卻被餵 M1／M4／M5 值；（b）提案者必填 `proof`、內容須錨定 M1／M4／M5 並引基線值與 n，等於合法看見並直接對著迴圈層指標寫提案——這正是隔離要防的 Goodhart 路徑；PRD 只在 AC-SI-43-3 寫「提案者隔離不變」，沒有修訂 AC-SI-22-3 也沒有說明為何仍相容；（c）答案檔含 Q4-L 值，整檔在 repo 內，隔離只靠任務書約束（P），AC-SI-20-4 ② 的偵測不覆蓋 `_fourq/`，用過的人看不出提案者是否讀過它。
- 建議修法：先在 PRD 明文裁決「提案者可見的指標範圍」：允許看見指標的**類別**（M1／M4／M5 的名稱與根因鍵）、不允許看見迴圈層**值與門檻**；Q4-L 與基線值不交給提案者（`proof` 的基線欄由審視者提供的症狀計數基線填，而非迴圈層 M 值）。實作上採 P1-1 的 B 案（Q4-L 不進答案檔、進事件欄位），並把 `_fourq/` 路徑加進 AC-SI-20-4 ② 的偵測 pattern（掃提案者逐字稿命中 `_fourq/` 者標 `exposed` 或至少列為資訊項）。同時改 AC-SI-22-3 條文或在其後加註（T1 修訂紀錄）。

### P2-2　Q1「已查涵蓋」重放可被無意義查詢繞過，且 N 的取得方式不確定、易大量假紅
- 座標：PRD AC-SI-41-3 ②、D-EFQ-12；TCS AT-441-3-*；SOP〈答案檔格式〉「對各檔各下一次 `Grep -c` 後加總」。
- 問題：（a）重放只驗「宣稱的 N＝重算 N」，查詢字串與該項的做法／機制無任何關聯；`「zzzz」＝0` 永遠過、`N=0` 不觸發 `HIT-NO-DIFF`，零成本繞過；零項 Q1 只要一行任意查詢就合格。（b）空字串或單字元查詢的 N＝全帳本行數或極大值，沒有最小長度與正規化規則；（c）審視者無 shell，只能對 Grep／Glob 手算「語料各檔」的行數加總，語料檔集合（`archive*`、`Defect_Log*`、PRD、SOP）由 glob 決定，審視者與 CLI 只要差一個檔（例：多一個 archive、`Defect_Log_*` 備份）就 `FOURQ-QUERY-MISMATCH`，每次被拒＝重派一個 Sonnet 審視者（燒額度，P4 實跑的無人窗口預算受限）。
- 建議修法：①查詢字串須是該項 `做法／機制` 文字的子字串且長度 ≥4 個字元（把查詢綁在聲明上），Q1 每項至少 2 條互異查詢；零項 Q1 至少 3 條互異查詢（長度同）；②`FOURQ-QUERY-EMPTY`／`TOO-SHORT` 碼；③唯讀動詞形態 `fourq --count "<字串>"`（READONLY）由 CLI 印出 N 與逐檔分佈，主控代審視者核算後填入，或 CLI 入帳時以「CLI 重算值」覆寫答案檔副本的 N 並標註（二擇一，須定位 AT-442-1-1 的「位元組相等」是否保留）；④AT：空查詢、1 字元、與項目文字無關的查詢、多一個 archive 檔。

### P2-3　`_fourq/` 內的自由文字會讓 `si check` 的 `ref.obs` 轉紅（規格漏查掃描點）
- 座標：`tools/lib/selfimproving/refs.py:17,91-109`（`git grep -E "(OBS|ATT|PROP|DEC|APP|MEA|RUN)-SI-[0-9]+"` 掃全 repo，未在帳本內的 `OBS-SI-<n>` ⇒ `OBS-REF-DANGLING` fail）；PRD §9.8.4 掃描面表（未列 `ref.obs`／`git.grep_only`）；教訓記憶 `windows-20261109-console-ux-sort-help-round.md`（同型已擋過三次 push）。
- 問題：座標欄會被驗證，但 `差異`、`發現`、`為何前沿`、`反證`、`收斂`、查詢字串等自由文字內出現的 `OBS-SI-<n>`（含舉例、不存在的號）不驗。答案檔提交進 git 後 `ref.obs` 判紅，`check` rc≠0，影響後續 `prop-new`／推送。
- 建議修法：入帳驗證加碼：整檔任何 `OBS-SI-\d+` 字面都必須存在於帳本（否則 `FOURQ-COORD-MISSING` 點名該 token）；補 AT（自由欄位含不存在的 OBS 號 ⇒ rc 1；含存在者通過），並把 `refs.py::obs_findings` 列入 PRD §9.8.4 掃描面表。

### P2-4　規格先落地、實作後落地的窗口對真實排程是活的（SOP 範本在工作樹即生效）
- 座標：`tools/lib/selfimproving/patrolrun.py:88-91`（`compose` 讀工作樹的 SOP 範本，`template_problems` 舊碼只檢 1～8 步，九步範本照過）；PRD §9.8.8、TCS ⚖9（「不得只推規格 commit」）。
- 問題：舊 `template_problems` 對九步範本回空，所以規格檔一落到工作樹（甚至未 commit），下一次心跳（每 15 分鐘）若遇到 (f) 到期，就會生成一份叫無人主控跑不存在的 `fourq` 動詞的任務書（argparse rc 2 或 UNATTENDED-REFUSED），空耗額度並留下半套運轉。⚖9 只防「推送」，沒防「工作樹內的排程」。
- 建議修法：落地程序寫成硬步驟：規格與實作在同一工作窗口內連續完成，且落地規格前先 `sched disarm`（或確認下次 due 之後），實作 commit 完成且 `si check`／ P4 範圍守衛綠之後再 `sched arm`；寫進 TCS §0 提交順序與 SOP 的收尾，並把「落地窗口內不得有到期的 (f)」列入 V36 前置。

### P3 級發現
- P3-1　憲法相容表缺 K=1 列（brief 審查重點 4）：PRD 附錄 B 的 P5 相容表有 C-01～C-16、禁令 26、外部衍生隔離、loop-self，沒有「K=1 只認掌舵者」。建議加一列（相容：`fourq` 不寫 `dec`、`fourq --skip --reason helmsman` 的 sid／line 只驗格式、不構成 K=1 決定）。
- P3-2　`fourq --skip` 在無人環境屬 A 類可用（PRD AC-SI-44-5「含 `--skip`」），SOP 範本只用文字禁止；`--reason helmsman` 的 sid／line 只驗格式（與 `research --skip` 同型，已誠實劃界），但無人主控可自填 `helmsman` 而零成本繞過四問。建議：`AUTOSDD_UNATTENDED` 有設時 `--skip` 只准 `quota-band` 且 `--band` 須與任務書 BAND 一致（若 CLI 讀得到），或在 PRD 明寫為已知劃界並由 `status`／巡邏日誌偵測（`fourq.skip` 在無人運轉出現即記一行）。
- P3-3　C-07 列結論「相容」的理由偏薄：審視者替提案擬收斂判準（反證、收斂）即「提案者之外的角色提出評估標準」，其合法性來自 M1／M4／M5 錨定與 K=1 人工閘；應在列內寫明 `proof` 僅供掌舵者閱讀、不被 `measure`／`verify` 讀取（已核 `meawrite.py:73` 只讀既有欄位，`proof` 不入量測）。
- P3-4　SCG-4 突變清單缺：`FOURQ-NOT-RUN` 步 0′ 的適用判斷（AT-444-3-E-1 自承舊碼不紅、只靠突變）、`fourq_from_run` 的整數比較（AT-443-4-1 的「1000 vs 999」字串序陷阱）、AT-443-3-E-2（已列入）以外的「紅在突變」型 AT 都應逐一入清單。
- P3-5　TCS 勘誤與 P4 守衛：`test_selfimproving_schedule_gate.py:349-356` 的 `FROZEN` 以 `docs/03_testing/contracts/TCS-SelfImproving-P` 為前綴，僅豁免 `-P4-`；TCS-P5 在實作 commit 內被主控追加勘誤時，`TestScope::test_AT_440_8_1` 會判紅。§5.7 只寫「本檔勘誤追加不計」是 AT-445-5-1 的語意，對 P4 守衛無效。建議：勘誤批次獨立 commit（不含 ALLOWED 面檔案），或同 commit 修 `FROZEN_EXEMPT`（P4 TCS 勘誤，列入 §2.5）。
- P3-6　`DEGRADE_TEXT.format(band=…)`（`patrolbrief.py:30`、`patrolrun.py:97`）要加每問項數值：TCS AT-444-1-E-2 寫「既有呼叫形態不變」，與加入 `fourq_degrade_items_max` 數值互相矛盾（要嘛加 format 引數、要嘛由呼叫端串接）。建議在 §5.6 明寫採「呼叫端串接」或「`format(band=…, n=…)` 並更新兩呼叫點」。
- P3-7　降載聲明現文「只做最小必要工作（研究者與歸因者各一輪、至多一張提案）」與新增「四問照做」在同一段並列，字面互不衝突但角色清單漏列審視者；建議 `DEGRADE_TEXT` 同步改寫。
- P3-8　Q4-L 的 `measure：due=… measuring=… candidates_unsettled=…` 與 `status` 文字行相符（`status.py:196-197`），但 JSON 的 `status.measure` 沒有 `measuring` 鍵（需由 `windows` 計數）；PRD AC-SI-41-4 寫「取自 si status 的 measure」，應寫明 `measuring＝windows 中 state 為 measuring 的個數`。
- P4-1　文件最小集仍偏重：D-EFQ 決策在 PRD 同時出現四次（FG-N 敘述、附錄 C.2 #24 單格約 5 KB、§9.8.9 審閱表、TCS §7.1）；TCS §6.1／§6.2 兩張追溯表與 §1 重複，可刪；SOP〈答案檔格式〉與 PRD AC-SI-41-2 重複列一次格式，可留 SOP 範本＋指向 PRD。建議 C.2 #24 只留編號與一句話＋座標。
- P4-2　D-EFQ-11 的「整檔不得含 ASCII `|`」與 Q4「症狀計數：含可重跑的指令」衝突：PowerShell／grep 指令常含管線。SOP 應示範全形化或建議改寫（例：用 `Select-String` 單指令、或改記檔案座標）。

## 逐項查證（brief 十項）

1. 需求覆蓋：四問原句逐字出現在 SOP〈四問審視者〉節與範本步 2（mirror SOP L12-17、L549-560）；誰（審視者／主控）、何時（研究事件後、歸因前）、產出（答案檔）、去哪（`_fourq/`、OBS、卡面 tail）、機械保證（`fourq` 動詞、`prop-new`／`check` 閘）齊備。口號級條文：Q2(a)「前沿發現」「為何前沿」只有存在性判準，屬 P，已誠實標示。
2. 流於形式：見 P2-2；專家設定單一視角可行，建議每項加選填欄 `領域：{自我改進代理｜測試與品質工程｜SDLC 流程｜可靠性營運｜安全}`（封閉集合、只作分類、不計數不當成效；若加，不得有「各領域至少一項」之類配額）。
3. Goodhart：Q4 欄與禁用詞、錨定檢查對（M1／M4／M5／症狀計數＋§1.1）；禁用詞表為形態判準、可被同義詞繞過（PRD 已誠實劃界）；未發現把項數當成效的條文（`status.fourq` 只印狀態與缺漏數、`gaps_open` 為資訊）；提案者隔離見 P2-1。
4. 憲法相容表：逐條核對成立，缺 K=1（P3-1）、C-07 說理薄（P3-3）；禁令 26（審視者無外聯、來源只列不加、研究方法 SOP 凍結不改）成立；外部衍生隔離：D-EFQ-16 的 OBS 列＋`rows.py:260-263` 只對 `回報者=研究者` 強制 `src`，已核成立；loop-self：`params.json` 的 `non_evolvable_globs` 含 `tools/lib/selfimproving/**`、`tools/selfimproving.py`、`docs/06_quality/SelfImproving_Proposals/**`、`docs/05_development/SelfImproving_*.md`、PRD（已核 L21-36）。
5. 可測性：抽查並實證舊碼紅（`.venv\Scripts\python.exe -B -X utf8 -I` 載入）：`_HELP`＝26、`KINDS`＝23、`ITEM_IDS`＝35、`PARAM_SPECS`＝41、`CHECK_RULES_REV`＝5、`EVENT_LABELS`＝23、`CAPABILITY`＝59、`STATUS_KEYS`＝16（末鍵 `schedule`）、`params.json` 41 鍵、`fourq`／`fourqparse`／`evspec` 皆 ImportError、`unattended.gate("fourq", …)` 回 `UNATTENDED-REFUSED`、`propfiles.write_new` 不存在、`patrolbrief` 只檢步 1～8 ⇒ AT-441-*、442-4-1、443-2-1、444-1-1、444-4-1、444-5-1、445-1-1、445-2-E-1、445-3-1、445-4-1 十條以上舊碼確實紅。AT 計數驗算：FM 22（441×13、442×9）、FG 33（443×11、444×12、445×10）、合計 55、正控 24、負控 31，與規格自述相符；AC 18＋5＝23 皆有 AT。無 AT 碰真帳本或外網（夾具 hermetic）。「紅在突變」型 AT 見 P3-4。
6. 一致性：三檔 FR／AC／AT 編號、動詞名、旗標、碼名、`Q4-L` 欄位標籤一致；自行重跑（`.venv\Scripts\python.exe -B -X utf8 -I` 載入 repo 的測試判準函式、對 mirror SOP／PRD 文字）：`sop_p2_problems`＝[]、`sop_p3_problems`＝[]、`sop_p4_problems`＝[]、`patrolbrief.template_problems`＝[]、`params.metrics_problems(mirror PRD)`＝[]（對照 repo 原檔亦皆 []）。範本節 `1.～5.`（引言前一段）與 `1.～9.` 順序存在，`_STEP_RE` 以集合判斷不受影響。`DEGRADE_TEXT` 問題見 P3-6／7。
7. 連動面：§2.5 已涵蓋 `_HELP`（26→27）、`KINDS`（23→25）、`PARAM_SPECS`（41→44）、`CHECK_RULES_REV`（5→6）、`status`（16→17）、`CAPABILITY`（59→62）、`EVENT_LABELS`（23→25）、`A_CLASS`、範本 `[1-8]` 判準、P4 範圍守衛；已核這些舊值屬實。漏列：`ref.obs` 掃描（P2-3）、P4 守衛對 TCS-P5 勘誤（P3-5）、`DEGRADE_TEXT` 呼叫點（P3-6）、`test_selfimproving_schedule_patrol.py` 內 `len(set(codes.values())) == 5` 的變體數（已列）、巡邏器 (f) 任務書占位符若採 P1-1 的 A 案需新增欄位（`UPPER_FIELDS` 與 `template_problems` 的 `PLACEHOLDER-MISSING`）。
8. 無人運轉可行性：寫入面——`block_destructive_git.py:1437-1536` 的治理檔禁寫只判 Write／Edit／NotebookEdit 工具呼叫，保護面清單（`_GOV_EXACT`、`.claude/hooks/*.py`、`.autoclaude/`、`.git/`、`~/.ssh`）不含 `docs/06_quality/SelfImproving_Proposals/_fourq/`；`fourq` 由 CLI 子行程寫檔，不經工具，不被擋；`.claude/settings.unattended.json` 允許 `PowerShell` 與 `Bash(python …)`，`~/.autosdd/handback` 在 `additionalDirectories`，任務目錄先例（handback.md）已能寫，故答案草稿檔存入任務目錄可行；`docs/…/Proposals` 不在 deny 清單。**阻礙不在寫入面而在 Q4-L 取值（P1-1）**。另 `fourq`／`fourq --skip` 授權路徑：`unattended.check` 對 A 類走 `owner_runs`，`--run` 必須等於 `AUTOSDD_SI_PATROL_RUN`，行為與其他 A 類一致。
9. Console 零改動：核對 `AgentConsole/engine-bridge/app/si_cli.py:175`（只驗 `kind` 與 `items` 為 list）、`routers/si.py`（僅轉傳，無逐鍵白名單）、`frontend/components/domain/si/SiStatusBanner.tsx:19,130-132`（`SI_STATUS_KNOWN_KEYS` 外的鍵列在 `si-status-extra`）、`frontend/lib/api/types.ts:341-342`（型別註記「其餘鍵原樣保留」）、後端 `SiReconcileService.java:128-130` 只處理 Console 自寫 kind（`sched.set`／`run.open`／`sched.skip`），不枚舉事件詞彙；`SiExportResponse` 以 Map 持整棵樹——零改動宣稱成立，「未驗」兩處已讀碼補驗。`CLI_CLOSURE` 為目錄項已由 PRD 查證；仍須 V37 實跑（`test_si_export_differential.py`、`tsc`）。
10. 文件最小集：見 P4-1；缺了的必要項：P1-1／P2-1 修後需要的 `fourq --q4l`（或事件欄位）條文與 AT、AC-SI-22-3 修訂註記。

## D-EFQ-11～18 逐條意見
- D-EFQ-11（答案檔格式）：同意；加一條——指令示例遇 `|` 的處理（P4-2）。
- D-EFQ-12（查詢重放）：修改（P2-2）：查詢綁定項目文字、最小長度、至少 2 條、零項 3 條、`--count` 輔助。
- D-EFQ-13（`propfiles.write_new` O_EXCL）：同意；已核 `propfiles.write_new` 目前不存在、需新增，且 `fold.py`／`writeverbs.py` 不碰的約束成立。
- D-EFQ-14（Q4-L 主控貼值＋CLI 重算比對）：否決現案（P1-1）；改 A 或 B 案。
- D-EFQ-15（Goodhart 形態判準只判指標與收斂欄）：同意；補一句「`非`」緊鄰判準要排除「非常」類詞頭（以詞表式否定語 `不以／不得以／並非以` 取代單字 `非`）。
- D-EFQ-16（Q2-G 為 OBS 列、前綴「來源缺口候選：」、不帶 `src`）：同意；已核 `rows.py:260-263` 僅對 `回報者=研究者` 強制 `src`，`回報者` 為自由字串。
- D-EFQ-17（`added_by` 只認掌舵者打字訊息）：同意，與 AC-SI-30-2 一致。
- D-EFQ-18（`CHECK_RULES_REV` 5→6、判準併入 `events.research`、FR 編號自 41、`events.py` 先拆 `evspec`）：同意；`AT-440-*` 撞名論證成立。

## TCS §7.1 ⚖1～10 逐條意見
- ⚖1 同意；⚖2 同意；⚖3 同意（另注意實作當下若有未關的運轉其號≥`fourq_from_run`，須先關閉或把值設為再下一號）；⚖4 同意；⚖5 否決（隨 P1-1）；⚖6 同意（前綴約定可接受，AT 已含負控）；⚖7 同意；⚖8 同意（拆分先行、零行為變更、`events` 對外名稱不變由 AT-442-4-1 釘住）；⚖9 修改（P2-4：補排程停用與連續落地程序）；⚖10 同意，加綁定查詢文字的緩解（P2-2）。

## 指令與 rc
- `git diff --no-index --stat`（PRD、SOP 各對照 repo 原檔）：rc 1（有差異，預期）
- `.venv\Scripts\python.exe -B -X utf8 -I …\qa_probe.py`：rc 0（計數、ImportError、gate 實證）
- `.venv\Scripts\python.exe -B -X utf8 -I …\qa_sop.py`：rc 0（sop_p2／p3／p4、template、metrics 對 mirror 皆 []）
- `.venv\Scripts\python.exe -B -X utf8 -I …\qa_probe2.py`：rc 0（`CAPABILITY`＝59、`STATUS_KEYS`＝16、`CORE_MAX`＝12、`_PARSED_KEYS`＝6、`_OWN_PREFIXES`、`REQUIRED` 六欄）
- `AutoClaude\tools\check_loc_budget.py --json`：rc 0（輸出未逐項解讀；`events.py` 實體行數 506，PRD 稱 400／400 屬預算口徑，未獨立驗證）
- 其餘為 Read／Grep／`git grep` 唯讀查證。


---

# 二審（規格第二版；D-EQA-1～18）

審查者：同一審 QA（Sonnet）；範圍＝一審項目是否已結、D-EQA 是否如實落地、機械核對、規格棒自標待確認點。repo 唯讀。

## 結論：PASS（P1／P2 為 0；留 5 個 P3、2 個 P4，建議主控當場編修）

## (a) 一審項目逐項

| 一審項 | 狀態 | 座標與判斷 |
|---|---|---|
| P1-1 Q4-L 無人取不到 | 已結 | PRD AC-SI-41-4（L565）：答案檔不含迴圈層值，CLI 入帳時唯讀算快照寫進 `fourq.review.loop` 並印出；`FOURQ-LOOP-MISMATCH` 在 PRD、SOP 為 0（TCS 僅 1 處「不存在此碼」的反向斷言，AT-441-4-E-2）；`fourq` 為 A 類、無人環境下 AT-441-4-2 驗「不需任何輸入、`mea.*` 零新增」。取數可實作，見 (d)-4。 |
| P2-1 提案者隔離 | 已結 | AC-SI-22-3 與 AC-SI-20-4 增補（L366、L377）；AC-SI-43-3（L576）`proof` 只准四個定性子欄＋`PROOF-LEAK`／`FOURQ-Q4-LEAK` 禁字（`PARAM_SPECS` 鍵名）。補充：`loop` 值進事件帳本不構成新暴露面，因既有 `mea.report` 的 `check_report`（`meastat.py:216-228`）早已把 m1／m4／m5 寫進同一帳本。偵測面 `FOURQ-READ` 見 (d)-1（P3）。 |
| P2-2 查詢重放繞過 | 實質已結，殘留 P3-N1 | AC-SI-41-3 ②③（L564）：≥2 條互異、綁定做法或機制子串、≥4 字元、零／非零比對、零項 Q1 ≥2 筆 `Q1-X` 且宣稱命中；固定語料 `CORPUS`、`--corpus`、`--dry-run` 皆落地，N 的手算問題消失。殘留見 P3-N1。 |
| P2-3 `ref.obs` | 已結 | AC-SI-41-3 ④＋PRD §9.8.3（L1244）；已逐項對 `refs.py:14-17,96-109`：OBS 懸空紅、ATT／PROP／RUN 在事件帳本在場略過、DEC／APP／MEA 資訊項；規格「`MEA` 一律不收、其餘須存在」較 `refs.py` 更嚴，合理。AT-441-3-3、AT-441-3-E-3（含「真提交進 git 後 `ref.obs` 為紅」的對照）。 |
| P2-4 落地窗口 | 已結（程序性，見 P3-N2） | TCS §0 提交程序①～⑥；AT-444-1-E-1 加「舊範本（HEAD 版）⇒ 非空」fail-closed；改用 `dirty-tree`／`other-driver` 防線，不 disarm。 |
| P3-1 K=1 列 | 已結 | PRD L1550。 |
| P3-2 `--skip` 無人 | 已結 | `FOURQ-SKIP-REFUSED`、`FOURQ-SKIP-BAND-FREE`（AT-442-2-E-1）；`--degraded` 已刪（PRD 僅留否定敘述）；額度帶現讀已核 `sched.py:230-231`：只有 free／notice／converge 帶會 spawn，故「無人不需 skip」成立。 |
| P3-3 C-07 | 已結 | PRD L1542。 |
| P3-4 突變清單 | 已結 | TCS §5 末「SCG-4 通過標準」含步 0′ 適用判斷、`fourq_from_run` 整數比較、無人 `--skip` 拒收。 |
| P3-5 TCS 勘誤與 P4 守衛 | 已結 | TCS §0 ④。 |
| P3-6／7 `DEGRADE_TEXT` | 已結 | D-EQA-10：呼叫形態與文字不變、步 2 靜態項數、AT-444-1-1 釘其等於 `params.json`、AT-444-2-1。（`DEGRADE_TEXT` 的「研究者與歸因者各一輪」字面未提審視者，D-EQA-10 已明定不改，可接受。） |
| P3-8 `measuring` | 已結 | PRD L565。 |
| P4-1 文件瘦身 | 已結 | TCS 27,911 bytes（≤35 KB；162 行，原 397 行）；PRD 對 repo 原檔 `+89/−6`（一審版 `+152/−4`，淨額 83 對 148，少 44%）；SOP `+97/−10`。D-EFQ／D-EQA 全文只住附錄 C.2 #24（L1625）。 |
| P4-2 `|` | 已結 | AC-SI-41-4 ①、AT-441-2-E-2（反引號內 `|` 不判、Q1／Q2-G 含 `|` 判 `FOURQ-PIPE`）。 |

## (b) D-EQA-1～18 落地與新矛盾
- D-EQA-1～16 皆有對應條文與 AT；D-EQA-17（T1 座標）已親核：逐字稿第 14 行 `type=user`、`origin={"kind":"human"}`、`timestamp` 為 `2026-11-09T16:46:57Z`，等於 +08:00 的 `2026-11-10 00:46:57`，PRD L1467 一致；`[他包回報]` 已移除（PRD 剩 4 處為既有 AC-SI-21-1 等條文，與 repo 原檔同為 4）。
- AT 計數驗算：FM 26（441×16、442×10）、FG 34（443×11、444×11、445×12）、合計 60、PRD AC 18＋自增 6＝24；與 TCS 自述相符。
- 未發現 D-EQA 與 D-EFQ 條文互相矛盾（被取代者在附錄標 〔被…取代〕）。

## (c) 機械核對（對 mirror 文字重跑；皆以 `.venv\Scripts\python.exe -B -X utf8 -I`）
- `patrolbrief.template_problems`＝[]（對照 repo 原檔亦 []）；範本步號 `1`～`9`。
- `sop_p2_problems`、`sop_p3_problems`、`sop_p4_problems`（測試檔函式）皆 []。
- `_selfimproving_fixtures.sop_problems(sop, prd)`＝[]（單給 SOP 亦 []；對照原檔 []）。
- `params.metrics_problems(mirror PRD, metrics.md)`＝[]。
- `git diff --no-index --stat`：PRD `95 +++--`（89 增 6 刪）、SOP `107`（97 增 10 刪），rc 1（有差異，預期）。

## (d) 規格棒自標待確認點
1. **TCS ⚖1（`_fourq/` 只記資訊項 `FOURQ-READ`）**：語意同意（提案者本就須讀 Q3／Q4，標 `exposed` 會使正當提案全判 NE；答案檔已無迴圈層值）。但**不可實作性風險**：`transcript.exposure` 回 `str | None`（`transcript.py:207-229`）、首次命中即 return，唯一呼叫者是 `verify.py:214`（不在允許集合）。要回「資訊項」就得改回傳形態、讓 `verify.py` 接收並輸出，而 AT-445-6-1 還要求同一逐字稿「`_fourq/` 命中後仍能回報 held-out 的 `HELDOUT-EXPOSED`」，意味掃描不得首中即返。建議二擇一：（A，推薦）刪除 `FOURQ-READ`、AT-445-6-*、`transcript.py` 的允許與 AC-SI-20-4 增補——答案檔沒有任何需隱藏的值，這條偵測沒有保護對象，且少一個檔與兩個 AT；（B）保留，則把 `verify.py` 納入允許集合與 §9.8.5 接線表，並寫明新回傳形態與 `exposure` 不首中即返。
2. **允許集合新增 `transcript.py`**：該檔本身落在 P4 守衛 `ALLOWED` 的 regex（`^tools/lib/selfimproving/[a-z_]+\.py$`）內，守衛不受影響；但依 (d)-1，建議不加（採 A），否則必須同時加 `verify.py`。
3. **`SI_P4_BASE_SHA`**：已讀 `test_selfimproving_schedule_gate.py:372-388`。判準＝`git diff --name-only <基準>`（基準到**工作樹**，非到 HEAD）＋未追蹤檔；只要差分命中 `ALLOWED` 就強制「差分 ⊆ ALLOWED 且不含 `FROZEN`（PRD、SOP、`TCS-SelfImproving-P*`）」。核實結果：（i）`tools/git-hooks/pre-commit` 不跑 unittest（`git grep` 只在 `pre-push` 命中 `run_root_unittests`），TCS「pre-commit 須設」應改為「本機跑該 AT 時」；（ii）pre-push／CI 以 tip 為準、不設環境變數：實作 commit 緊接規格 commit ⇒ `HEAD~1`＝規格 commit，差分只有實作檔 ⇒ 綠；實作拆多個 commit 時各 tip 的 `HEAD~1` 亦只含實作 ⇒ 綠；CI 淺層 clone 取不到 `HEAD~1` ⇒ 只看未追蹤檔 ⇒ 綠；其後的重釘 commit 不碰 `ALLOWED` ⇒ 未觸發 ⇒ 綠。結論：**pre-push／CI 不會因此紅**。（iii）**開發期會紅（見 P3-N2）**：D-EQA-5 規定規格檔最後才與實作連續 commit，開發期間規格檔在工作樹未提交，差分含 PRD／SOP／TCS-P5（`FROZEN`）與未追蹤的新檔，此 AT 必紅，且設 `SI_P4_BASE_SHA=HEAD` 也救不了（規格仍未提交）。
4. **`loop` 快照取數入口**：已讀 `meastat.py:188-213` 與 `tools/probe/selfimproving_measure.py:45-55`。可實作，建議 TCS §3 把 seam 寫實：`ctx = mea.build_ctx(repo, Git(repo), params, events or [])`；`rep = meastat.metrics(repo, git, ctx, carrier=(events is not None))`；`loop` 取 `rep["success"]["m1"]`、`["m4"]`、`["m5"]["main"]`（M5a）、`["m5"]["all"]`（M5b），每項為 `{status, value, n, reason}`（NE 時 `status!="read"` 並帶 `reason`；`ctx.bad` 時 `metrics` 已全 NE）；僅 `meastat.metrics`／`build_ctx` 讀不寫，探針已示範；另須照 `status.measure_value`（`status.py:84-96`）先判 `valid_keys(params)` 與事件帳本缺席，缺＝逐項 NE（理由 `params-invalid`／`carrier-not-established`），因為 `build_ctx` 在 params 鍵缺時會拋例外。

## 新發現（P3／P4）
- **P3-N1　查詢綁定把「整句自己的聲明」當查詢會永遠零命中**：AC-SI-41-3 ② 只要求子串、≥4 字元、無上限；審視者拿整句 `做法` 當查詢必然零命中，零成本通過。零項 Q1 的 `Q1-X` 查詢宣稱「命中」也可用 `OBS-SI` 之類高頻字串過關。修法（確定性）：①查詢長度 4～12 字元（`FOURQ-QUERY-TOO-LONG`）；②`Q1-X`（與 `命中不涵蓋`）所附的涵蓋座標，CLI 驗其指向的那一行**含該查詢字串**；補 AT 兩條。
- **P3-N2　開發期 AT-440-8-1 必紅，TCS 未說明**：TCS §0 ③ 只談實作 commit 的環境變數。建議寫明：開發期間以 `-k 'not test_AT_440_8_1'` 排除、不得為此改守衛，規格 commit＋實作 commit 完成後在 tip 以預設基準重跑驗綠；並把 (d)-3 的 pre-commit 字樣改成「本機跑該 AT 時」。
- **P3-N3　`fourq --dry-run`／`--corpus` 的授權分類**：TCS AT-444-5-1 只釘 `fourq-corpus` 在 `READONLY`；`--dry-run` 在無人環境屬哪一類未寫（建議同 `fourq` 入帳：A 類、須 `--run` 等於 `AUTOSDD_SI_PATROL_RUN`，或明列為唯讀）。補 AT 一條。
- **P3-N4　`FOURQ-READ`**：見 (d)-1，二擇一。
- **P3-N5　`loop` 欄位大小**：AT-442-4-E-1 已測超長；仍應在 PRD §9.8（事件欄位表）寫明 `loop` 的位元組上界與編碼（M1／M4／M5a／M5b 各含 status、value、n、reason），以對 `event_max_bytes` 4,096 做最壞行計算（沿 P2 事件欄位表慣例）。
- **P4-N6**　`AT-444-2-1` 標題與內容為「`DEGRADE_TEXT` 不變」的對照，紅只在突變；已在突變清單外，建議加入或刪除（刪較省）。
- **P4-N7**　AT-441-4-2 的測試夾具須涵蓋 `params-invalid` 一例（見 (d)-4）。

## 二審指令與 rc
- `git diff --no-index --stat`（PRD、SOP 對 repo 原檔）：rc 1（有差異，預期）
- `.venv\Scripts\python.exe -B -X utf8 -I …\qa_sop.py`（`sop_p2/p3/p4_problems`、`template_problems`、`metrics_problems`）：rc 0，皆 []
- `.venv\Scripts\python.exe -B -X utf8 -I …\qa_sop2.py`（`fx.sop_problems`）：rc 0，[]
- 其餘為 Read／Grep／`git grep`／PowerShell 唯讀（含逐字稿第 14 行 `timestamp` 與 `origin` 讀取）。
