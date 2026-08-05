# AutoSDD Defect Log — Archive 59

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **2 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串；程式碼片段、角引號引述、與「訂正首詞（原文…接於後）：」之後到下一個 `｜` 為止的舊狀態引文內的字樣皆不算，R68 收窄／R76 補第三種）／③被 crossref 掃描目標宣稱過狀態者可搬，但搬後該宣稱必須仍解析得到（帳本家族＝主檔 ∪ archive；由 --check 判準(8) 實跑驗證，R68 改寫）／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 8 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免、(8)跨檔宣稱可解析：掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致（判準③ 改寫後的事後條件，R68）
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-19-001`、`DEF-17-001`
>
> **判準全過但以 `--only`／`--keep` 具名排除、刻意留在主檔者**（DEF-101-811；排除留痕，非無聲少搬）：`DEF-101-811`、`DEF-101-840`、`DEF-101-846`、`DEF-101-837`、`DEF-101-843`、`DEF-101-852`、`DEF-101-844`、`DEF-101-842`、`DEF-101-838`、`DEF-101-839`、`DEF-101-841`、`DEF-101-853`、`DEF-101-854`、`DEF-101-836`、`DEF-101-849`、`DEF-101-855`、`DEF-101-850`、`DEF-101-832`、`DEF-101-847`、`DEF-101-833`、`DEF-101-835`、`DEF-101-834`、`DEF-101-851`
>
> **本次操作備註**：R76 收斂包：以新落地的 --only 只搬兩筆舊已結列（DEF-17-001／DEF-19-001）；本輪 R76 新列一律不搬（沿用「本輪列留主檔供舵手複審」政策，正是 DEF-101-811 建置 --only 的理由）。此次操作同時是 DEF-101-811 fixed 宣稱的端到端取證。
>
> 🔴 **R76 複審 SA-03 二次訂正（原文的兩句宣稱已於上方刪除，不逐字重述被推翻的話）**：
> ① 原備註對主檔餘裕做了定性宣稱，而**下一段就是禁止這麼做的條文**（R59 SA-R59-P2-1）；
>    複審當回合實測主檔仍在 warn 線之上，該宣稱在寫下的當回合即為假。餘裕一律現查。
> ② 原備註把「本輪 R76 新列」寫成一個定值，實數與之不符（判準＝「發現情境」欄首詞為
>    R76 者現查；`--only` 排除清單另含 R75 的 `DEF-101-811`，兩者本來就不是同一個數）。
>    本輪起本備註**不寫死筆數**，現查配方：
>    `python tools/check_defect_log_crossref.py --unresolved-count` 看未結存量；
>    `python tools/archive_defect_log.py --plan` 看可搬／不可搬與逐筆理由。
> ③ **`DEF-101-845` 在本次操作時既不在搬遷清單、也不在上面的排除清單**——它被判準②
>    誤判（該列證據欄的兩個裸 Python 識別字被當成活躍狀態字），而「被判準擋下」這條
>    路徑當時在標頭與索引都**無處可記**，於是它整個消失在帳務外。這正是 `DEF-101-811`
>    「排除留痕」只在 `--only` 那條路徑成立的射程缺口。該列已補反引號（零語意變更，
>    同 archive_55 對 7 筆歷史 token 的既有體例），複審後 `--plan` 實測已可搬，仍依同一
>    政策留在主檔。**下一次歸檔操作的標頭必須有「被判準擋下」這一欄**（見下）。
>
> **被搬遷判準擋下、非以 `--only`／`--keep` 排除者**（本次：`DEF-101-856`＝判準① `cls=open`；
> `DEF-101-845`＝判準② 假陽性，已訂正）。
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-19-001 | 2026-06-16 | improving_19 W-19 B 軌 dogfooding（閉合 catch 側契約時，揭露覆蓋面缺口） | catch 歸因覆蓋面不足（DEF-18-001 閉合後之殘留面）：W-19 定義 catch 三要件契約並接入兩確定可歸因路徑（R-9.1 gate retry 耗盡 / R-9.21 monitor 破壞），但目前僅 **2/39** active 規則補了 `failure_mode` 並接線；其餘 37 規則 `failure_mode` 未定義 → 其守望的失敗模式即使觸發 escalation 也不參與 catch 歸因（`catch_count` 恆 0、fail-closed 不記）。後果：這 37 規則的 ROI 仍為單側信號，`propose_graduation` 對它們仍可能偏頗提議退役。本輪**刻意只接 2 條無歧義路徑**（Rule 2 簡單優先、寧缺勿濫不污染 ROI）；覆蓋率以 `rule_fire_telemetry_stats().safety_certificate.catch_attribution_coverage` 程式內誠實揭露。非阻擋（catch 機制正確、紅線守界、flag 預設 OFF＝生產零影響） | P3（成熟度閉環覆蓋面缺口，非阻擋；與 B 軌「機制齊備但覆蓋漸進」家族同根） | routed 未來輪 B 軌：逐步為其餘規則補 `failure_mode` 自描述 + 對應 escalation 呼叫點歸因（每條須有「無歧義映射」證據，不可為衝覆蓋率而臆測歸因——延續 DEF-18-001 紀律）；**生產全面啟用退役前須提升覆蓋率至可接受門檻**。屬漸進補強 W 項，非單輪可竟 | closed-by-decision｜🔴 R75 訂正首詞（原文逐字接於後）：routed（漸進補強進行中：**improving_20 W-20-1 將 catch 歸因從 2/39 推進至 4/39**——新增 R-9.2〔auto_compact per-stage 超限→ESCALATION〕、R-9.22〔spec_patch per-AC 上限耗盡→ESCALATION〕兩條無歧義路徑，各補 `failure_mode` + 接對應 `record_escalation` 呼叫點顯式歸因〔fixed@v0.11，6 case 測試 test_w20_catch_wiring.py〕；`catch_attribution_coverage` 程式內誠實揭露。剩餘 35 規則續漸進補強，生產全面啟用退役前須提升覆蓋率至可接受門檻）。**improving_22 階段一複驗仍 4/39**；🔴 人工本輪 scope 選「DEF-12-002 + DEF-15-001 深層」未含 catch 補強，維持 routed 漸進，未推進。**improving_37 W-37-1 推進 4/39 → 5/39**（新增 R-9.7·9.7.2 HUMAN_PENDING 逾時 ≥168h ESCALATION 無歧義路徑，fixed@v0.15；明文僅 9.7.2 排除 9.7.3〔歸 R-9.2〕防雙重歸因，非重疊守門測試鎖定；R-9.9 親驗無唯一生產落點降級不接）。**improving_38 W-38-1/W-38-2 推進 5/39 → 7/39（+2）**（新增 **R-SELF-STRIDE**〔SANDBOX_HARDENING_GATE policy_violation → ESCALATION，唯一生產落點、與既有 5 條零交集〕、**R-9.3**〔record_spec_audit 的 SPEC_AUDIT 耗盡 → ESCALATION；failure_mode 明文排除 implementation-budget-exceeded 直接 escalate〔正交無規則〕與 R-9.1 gate-retry 落點，防雙重歸因〕兩條無歧義路徑，fixed@v0.16；`test_w38_catch_wiring.py` 8 case 含兩條非重疊守門〔R-SELF-STRIDE verdict=pass 不歸因 / R-9.3 implementation-budget 落點不歸因〕；runtime `catch_attribution_coverage` 實測 7/39）。**improving_39 揭露結構天花板**：grep `record_escalation(` v0.16 fsm_runtime.py＝9 生產 escalation 落點＝7 已接線 + 2 正交無規則（515 implementation-budget、2401 spec_patch-unable-to-draft），「1:1 無歧義落點接線」乾淨候選**已枯竭**；W-39-1 機械分類 39 條＝(A)FSM escalation 7 / (B)hook 3 / (C)lint·TLC 3 / (D)meta-loop guard 14 / (E)manual·advisory·憲法 12，證實 escalation-scoped 真實覆蓋＝**7/7=100%**（DEF-39-001 透明化）。**→ closed@improving_40（milestone，🔴 掌舵者 AskUserQuestion 拍板正式收尾）**：FSM-escalation catch 機制覆蓋已達結構天花板（7/7=100%）；其餘 32 條由 hook/lint/TLC/meta-loop/人工守門＝本質非 FSM-escalation catch-可歸因（`catch_count` 恆 0 為設計使然非缺口）。「其他守門機制覆蓋度量」另立新標的（B 軌未來輪，非本缺陷 scope）｜🔴 **R75 複驗（類別 A）**：本欄末段自載 `closed@improving_40`（掌舵者拍板收尾），首詞未同步而已。裁決的事實基礎現查仍成立：`fsm_runtime.py:1855 catch_side_wired: True`、`rule_loader.py:208 record_state_catches`；同批 `pytest` → **27 passed，rc=0**。 | 
| DEF-17-001 | 2026-06-16 | improving_17 W-17-1 B 軌 dogfooding（接入鷹架代謝 GC、驗 flag ON 端到端時揭露） | 代謝閉環「半接」結構摩擦：W-17-1 把 `scaffold_gc.run_gc()` 接入 `enter_scaffold_gc` 主迴圈後，flag ON 確實自動產 SCAFFOLD-ROI 報告，**但 `compute_proposals()` 依 `rule_loader.propose_graduation()` 需 `fire_count ≥ GRADUATION_MIN_FIRES ∧ catch_count==0` 才提議**（`scaffold_gc.py:72-73`/`rule_loader.py:150-159`）。FF-9 實測 39 條 active 規則 aggregate `fire_count=0`（`record_fire` 在 FSM 主迴圈零自動呼叫——僅測試觸發），故**即使 flag ON，生產端 GC 恆產零提議**＝GAP-X2「代謝肌肉從未收縮」**未真正閉合**：接 `run_gc` 是必要但不充分，尚需把 `record_fire(rule_id, caught=…)` 遙測接入「規則實際 fire/catch」的 FSM 執行點，ROI 帳本才有非零資料驅動退役提議。非阻擋（W-17-1 機制正確、報告真實落盤、紅線守界皆達成；零資料零提議是誠實的下游依賴而非 bug） | P3（成熟度閉環一致性/遙測接線缺口，非阻擋；與 B 軌「機制齊備但遙測未接」家族同根） | routed 未來輪 B 軌：把 `record_fire` 規則命中記帳接入 FSM 規則執行/守門點（`rule_loader.load_for_state` 命中後記帳），使 scaffold_roi 累積真實 runtime 資料；屬獨立 W 項（遙測接線），非本輪 scope（本輪聚焦「GC 提議產出鏈」接入＝代謝收縮的決策側） | fixed@improving_62｜🔴 R75 訂正首詞（原文逐字接於後）：**routed（fire 側 fixed@improving_18 / catch 側 routed → DEF-18-001）**（即記即分流；本輪 W-17-1 收縮「決策側」已閉合並測試覆蓋。**2026-06-16 improving_18 W-18-1/W-18-2 閉合「遙測 fire 側」**：`record_state_fires` 接入 `transition()` 主迴圈，flag ON 時 `fire_count` 真實累積〔`test_rule_fire_telemetry_wiring.py::test_flag_on_fire_count_accumulates_persisted` 驗 3 次轉態累積至 3〕，GC 已有非零資料可驅動提議＝DEF-17-001 點名的「`fire_count=0` 根因」已閉合。**殘留 catch 側**〔`record_fire(caught=True)` 何時觸發之語意框架未定義〕轉記為獨立 **DEF-18-001**。**2026-06-25 improving_62（v0.24）：fire 側遙測翻預設 ON 活體化**——`_rule_fire_telemetry_enabled()` unset→True（鏡像 AUTO_RECOVERY/SLV 翻環），fire_count 由 opt-in 升為生產常態累積，DEF-17-001 點名根因「生產端 fire_count 恆 0」**實質閉合**（掌舵者 signoff「B 軸 telemetry 翻 ON」；保留顯式 opt-out=0；conftest autouse 隔離護凍結 governance））｜🔴 **R75 複驗（類別 A）**：本列根因「生產端 fire_count 恆 0」已除：v0.30 現查 `rule_loader.py:182 record_state_fires`、`fsm_runtime.py:116` docstring 逐字「unset → ON（v0.24 活體化）」。catch 側早轉獨立列且該列狀態為 `fixed@v0.10`，見 DEF-18-001（現居 archive_03）；覆蓋面再轉 `DEF-19-001`（同輪結案）⇒ 名下零待辦。`pytest` 三支遙測接線測試 → **27 passed，rc=0**。 |
