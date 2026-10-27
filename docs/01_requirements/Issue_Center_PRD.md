# 議題中心（Issue Center）需求規格 v1.0

**狀態**：v1.0 可凍結版（SA 補齊 v0.1 草案；SCG-0 一審意見 F-01～F-30、二審意見 N-1～N-11、三審小修 R3-01～R3-08 已於 2026-10-27 逐條處理，見 §13；待凍結）。**立案**：掌舵者 2026-10-26（sid `0a41ada1-921d-48d4-bb4b-4cc4a18190e8`）原文「這個就是一個議題列表管理…請幫我重新設計以上清楚呈現、簡單易懂的議題管理機制」「我連如何查帳本 43 列都有點難度」。**範圍裁決**：階段一（唯讀議題中心）＋階段二（優先順序＋待您決定按鈕）同批交付（範圍裁決＝掌舵者 2026-10-26 互動選項「階段一和二一起做」，sid `0a41ada1-921d-48d4-bb4b-4cc4a18190e8`）。
**定位**：在既有三類帳本（觀察帳本、缺陷帳本、提案與事件帳本）**之上**加一層「議題視角」。帳本仍是機器與稽核用的唯一真相源、一個字不動；議題中心只把它們翻成人看得懂的一張工作清單。所有狀態、結果、來源、嚴重度在顯示層一律中文；對照表只住一個檔（§4）。
**規格文件**：本檔＋一份 TCS（`docs/03_testing/contracts/TCS-IssueCenter-20261027.md`）＋一份 API 契約檔（`AgentConsole/docs/02_architecture/API_Contract_IssueCenter.md`：端點表、`console.issue_priority` 資料所有權、reason 表，見 §6.4）；兩者都在 TCS 階段產出，不另寫 ADR、SOP（使用說明見附錄 A）。

---

## 1. 目標與範圍

> 您打開「議題中心」，看到的是一張待辦清單：每一列是一個議題，寫著它從哪來、現在到哪一步、多嚴重、該誰動、下一步是什麼；做完的進「已完成」可依條件翻查。

- **本版交付**：階段一＝唯讀議題中心（聚合、中文對照、CLI、匯出、Bridge、console-api 讀取、前端四分頁與「狀態說明」）；階段二＝您的優先順序（Console 自有資料）與「待您決定」直接按鈕（沿用既有簽章對話框）。
- **後續（階段三，不在本版）**：已完成歸檔報表（時間窗篩選、CSV／Markdown 匯出、30 天摘要）、歸檔缺陷帳本納入、「本週完成」數字（需帳本加結案時間欄，見 §12）。
- **成功的樣子**（症狀型，§11）：您不看任何英文就能回答「現在有幾件待處理、最嚴重的是哪件、有什麼在等我決定」；帳本一個位元都沒被動過。
- **名詞**：「議題」＝帳本裡一個可追蹤的項目，議題編號就是原帳本 ID；「機器值」＝帳本裡寫的英文狀態（`open`、`fixed@…`、`measuring`…）；「顯示層」＝只在議題中心出現的中文。

## 2. 議題從哪裡來（來源四類）與自動判定

**哪些帳本列算議題**（一個議題＝一個帳本 ID；RUN、ATT、DEC、APP、MEA 不是議題）：

| 帳本 | 讀哪裡 | 議題 ID | 備註 |
|---|---|---|---|
| 觀察帳本 | `docs/06_quality/SelfImproving_Observation_Ledger.md`（九欄；若有 `…_archive*.md` 一併讀，同 `refs.obs_rows`） | `OBS-SI-NNN` | 每個九欄合法列一件（`ledger.Row.nine` 為真且 ID 欄合 `OBS-SI-NNN`）；其餘壞列不成議題，計入 `problems`（`ROW-ARITY`） |
| 缺陷帳本 | `docs/06_quality/AutoSDD_Defect_Log.md` 主檔（七欄，`defs.load_rows`） | `DEF-<族>-<序>` | 每個資料列一件；欄數與表頭不符者不成議題，計 `ROW-ARITY`（辨識＝`DefRow.arity_ok` 為假；`load_rows` 內部本就算出此旗標，只是尚未外露）；**不讀** `AutoSDD_Defect_Log_archive_*.md`（理由見下） |
| 姊妹軌 | `AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md` 的〈缺陷總表〉（五欄，依表頭欄名定位） | `DEF-<族>-<序>`（僅主檔找不到時才新增議題） | 表內 `DEF-ID` 在主檔有列＝該議題狀態覆蓋為「延後」；在主檔找不到（列已歸檔）＝仍成議題：來源系統缺陷、延後、標題「（主帳本列已歸檔）」、嚴重度 `null` 並列 `ne`、不進 `problems`；現況兩表皆空 |
| 提案 | `SelfImproving_Event_Ledger.jsonl` 經 `fold.fold` 折疊 | `PROP-SI-NNN` | 每個 PROP 一件（取最新修訂） |

- **不讀歸檔缺陷帳本的理由**（主控裁決 2026-10-26；實測同日，HEAD `7cb4d60d`，`defs.load_rows` 逐檔掃）：68 個歸檔檔共 1,415 列，其中 14 列欄數與表頭不符（狀態無法分類）、6 組 ID 重複、3 列被 `defs.classify_status` 的「最早關鍵字」判準歸為 `open`（例：DEF-24-001 敘述已 `fixed@`、DEF-13-002 為 `resolved@` 且寫「非 open 缺陷」）。納入會讓「待處理」出現無人認領的假待辦與常駐 `problems`；主檔 270 列則全部可分類。歸檔缺陷查詢列入階段三。
- **真帳本現況**（同日實測）：觀察 325 列（處置：decided 176、fixed@ 60、deferred 51、merged@ 24、DEF- 13、proposed@ 1；open 0）、缺陷主檔 270 列（fixed 219、closed-by-decision 51）、提案 2 件（皆 measuring）、姊妹軌 0 列。以本節與 §4 規則寫的一次性原型（不入庫）對這份現況分類：597 件全部可歸類、`problems` 為空。

**來源四類**（依順位判定，先中者定案；中文是顯示值）：

| 順位 | 來源 | 判定（讀的帳本欄位） | 一句話 |
|---|---|---|---|
| ① | 使用者提案 | 觀察列「標記」欄含 `來源=人` 或 `carrier=console`；提案：任一 `sources` 判為使用者提案 | 您自己提的（含經 Console 簽章入帳的） |
| ② | 系統缺陷 | 觀察列「分類」欄為 `bug`；缺陷帳本每一列；提案：任一 `sources` 判為系統缺陷（含所有 `DEF-` 來源） | 測試、CI、體檢或主控發現的缺陷 |
| ③ | 研究提案 | 觀察列「標記」欄含 `回報者=研究者`（`si check` 保證同列帶 `src` 與 `外部衍生=是`）；提案：任一 `sources` 判為研究提案 | 研究掃描外部來源產生；外部內容須另有內部佐證才能成提案（SelfImproving PRD AC-SI-02-1 不變） |
| ④ | 系統改善 | 其餘：觀察列分類為 `process`、`tooling`、`doc`、`decision`；提案其餘 | 流程、工具、文件的改善 |

- **順位固定**為使用者提案 > 系統缺陷 > 研究提案 > 系統改善（主控裁決 2026-10-26，掌舵者授權代決），觀察列與提案共用這一張順位表（例：您經 Console 報的 bug 顯示為使用者提案；研究者回報的 bug 顯示為系統缺陷）。提案的來源＝任一來源項目命中即取最前順位（真帳本例：PROP-SI-004 的來源項目含一列 `來源=人` 的觀察 OBS-SI-163，故顯示為使用者提案）；來源項目查不到者略過，全部查不到＝「未歸類：<來源項目 ID，以「、」相接>」並計入 `problems`；觀察帳本整本讀不到時另論：來源項目含觀察號的提案，其來源與嚴重度為 `null` 並列同一筆 `ne`（`OBS-LEDGER-UNAVAILABLE`），不走本條、不計 `UNMAPPED`（§4.6）。

## 3. 怎麼變成「正式議題」

候選只來自「處置為 `open` 的觀察列」；缺陷帳本列與提案一入帳就是正式議題，不經候選。

```
  觀察列剛入帳（處置 open）──▶ 候選（沒走下面兩條路之一，就停在候選〔可直接被關成終值〕，不會變成待辦）
        │ 路徑 A 系統判定：歸因者提出 attr，審查者 attr-confirm
        │ 路徑 B 使用者簽核：標記含 carrier=console（Console 新增觀察，簽章稽核入帳）或 來源=人
        ▼
  待解（缺陷、改善：已成立，尚無人處理）       待您決定（提案待決或復發待回滾；分類 decision 的觀察，不分路徑）
        │ 分流、修復或沙盒動工                       │ 您決定（核准、晉升、否決、退回、回滾、裁決）
        ▼                                             ▼
      進行中 ──▶ 觀察中（採納後量測窗）──▶ 已完成（結果：已修復／已採納／已否決／已退役／已裁決／已轉交／已合併／已回滾）
  任何階段都可能：延後（寫明再開症狀）或直接已完成；缺陷與提案不經候選；量測窗內復發的提案回到待您決定（等您決定是否回滾）
```

- **路徑 A**：存在 `attr`（type root 的 `obs` 含該列，或 type link 的 `from` 為該列）且其 `attr.confirm` 已入帳（以折疊後 `Att.settled` 為 `attr.confirm` 為準，與 `confirmed_root_causes` 同口徑；確認者等於提出者的違規由 `si check` 另報 `CONFIRMER-IS-PROPOSER`，不改變此判定）。只有 `attr` 未確認、或被 `attr.reject`＝仍是候選。
- **路徑 B**：標記含 `carrier=console` 或 `來源=人`＝該列本身就是您親自（簽章或口述）入帳的，入帳即成立，不需 `attr`。尚未入帳的 Console 稽核檔不是議題（議題只讀帳本；待入帳清單仍在「自我進化」頁的對帳面板）。
- **「待您決定」只收四種**（前三種為主控裁決 2026-10-26，第四種為 SCG-0 二審 N-3 裁決）：提案 `proposed`、提案 `verified`、提案 `closed` 且量測窗內復發而尚無 `dec(rollback)`（等您決定是否回滾）、分類 `decision` 的 `open` 觀察列（後者不論路徑，它本身就是一個等裁決的問題）。改善類（`process`、`tooling`、`doc`）的正式議題進「待解」，不經「待您決定」。
- **「成立」不是帳本動作而是讀出來的結果**：本功能不新增機器狀態、帳本動作或決定動詞（`events.DKINDS`）；對提案的決定（Console 簽章或打字核准）走既有 `decide`，與「成立」無關。這張圖只是把今天已存在的三套狀態機（觀察處置、缺陷狀態、提案狀態機）合成一張人看的圖。

## 4. 狀態對照表（顯示層唯一真相源，住 `tools/lib/selfimproving/issuemap.py`）

**4.1 七個議題狀態**（「待處理」不是狀態而是分頁名，也可當篩選別名＝待解＋進行中＋觀察中；「待您決定」收提案 `proposed`、`verified`、復發待回滾的 `closed` 與分類 `decision` 的 `open` 觀察列，見 §3）：

| 議題狀態 | 意思（一句話；＝「狀態說明」的白話） | 專屬分頁 | 可排優先順序 |
|---|---|---|---|
| 候選 | 剛記下來，還沒成立，不會成為待辦 | （只在「全部」） | 否 |
| 待您決定 | 等掌舵者按一下：決定提案（含復發後是否回滾），或裁決一個決定類觀察；復發待回滾的議題若您決定不回滾，目前沒有對應動詞可消去，會留在待您決定；要消去須另案新增決定動詞 | 待您決定 | 是 |
| 待解 | 已成立的缺陷或觀察，還沒人在處理 | 待處理 | 是 |
| 進行中 | 有人在做：修復、沙盒、驗證、修訂、回滾 | 待處理 | 是 |
| 觀察中 | 已採納，量測窗內看會不會復發 | 待處理 | 否 |
| 延後 | 刻意先放著，寫明「什麼情況再回來」；下一步欄是帳本原文節錄，可能含英文片段 | （只在「全部」） | 否 |
| 已完成 | 結案；「結果」欄寫明怎麼結的 | 已完成 | 否 |

**4.2 機器值 → 中文**（每個機器值在其條件的每種取值下恰一個歸類；「條件」欄由上而下先中者定案）：

| 帳本 | 機器值（帳本原值） | 條件 | 狀態 | 結果 |
|---|---|---|---|---|
| 觀察 | `open` | 分類 `decision` | 待您決定 | — |
| 觀察 | `open` | 路徑 A 或路徑 B 成立（§3） | 待解 | — |
| 觀察 | `open` | 其餘 | 候選 | — |
| 觀察 | `deferred` | — | 延後 | — |
| 觀察 | `fixed@<sha>` | — | 已完成 | 已修復 |
| 觀察 | `decided` | — | 已完成 | 已裁決 |
| 觀察 | `retired` | — | 已完成 | 已退役 |
| 觀察 | `merged@OBS-SI-NNN` | — | 已完成 | 已合併 |
| 觀察 | `DEF-<族>-<序>`、`proposed@PROP-SI-NNN` | 已轉到別處追蹤，目標議題另有自己的列 | 已完成 | 已轉交 |
| 缺陷 | `open`（`defs.classify_status` 判例：含 `partial`、`workaround`） | DEF-ID 不在姊妹軌表 | 待解 | — |
| 缺陷 | `routed` | 同上 | 進行中 | — |
| 缺陷 | `fixed` | 同上 | 已完成 | 已修復 |
| 缺陷 | `wontfix` | 同上 | 已完成 | 已否決 |
| 缺陷 | `closed-by-decision`（含 `no_action_needed`） | 同上 | 已完成 | 已裁決 |
| 缺陷 | 任一標籤 | DEF-ID 列在姊妹軌〈缺陷總表〉 | 延後 | — |
| 提案 | `proposed`、`verified` | — | 待您決定 | — |
| 提案 | `approved`、`returned`、`sandboxed` | — | 進行中 | — |
| 提案 | `promoted`、`measuring` | 已有 `dec(rollback)` 而 `app.rollback` 尚未被消耗 | 進行中 | — |
| 提案 | `promoted`、`measuring` | 其餘 | 觀察中 | — |
| 提案 | `closed` | 生效量測結果為 `recurred` 且從未有過 `dec(rollback)`（＝`meaplan.rollback_pending` 的成員，AC-IC-03-7 以差分鎖） | 待您決定 | — |
| 提案 | `closed` | 生效量測結果為 `rolled-back`，或已有被消耗的 `app.rollback`（決定 `rollback` 已配對一筆 `app.rollback` 事件） | 已完成 | 已回滾 |
| 提案 | `closed` | 生效量測結果為 `recurred` 或 `clean`，已有 `dec(rollback)` 而 `app.rollback` 尚未被消耗 | 進行中 | — |
| 提案 | `closed` | 生效量測結果量不到（僅限此情形；§4.6） | 已完成 | 未歸類：closed（計 `UNMAPPED`） |
| 提案 | `closed` | 其餘（生效量測結果為 `clean`） | 已完成 | 已採納 |
| 提案 | `rejected` | — | 已完成 | 已否決 |
| 提案 | `handed-off` | — | 已完成 | 已轉交 |

**4.3 八個結果**（只在狀態＝已完成時有值）：

| 結果 | 意思 |
|---|---|
| 已修復 | 問題已改好（觀察 `fixed@`、缺陷 `fixed`） |
| 已採納 | 提案已晉升並走完量測窗、窗內未復發 |
| 已否決 | 決定不做（提案被否決、缺陷 `wontfix`） |
| 已退役 | 觀察列不再相關（附依據座標） |
| 已裁決 | 由掌舵者或主控裁決結案、不改程式（觀察 `decided`、缺陷 `closed-by-decision`） |
| 已轉交 | 已轉到別處追蹤：觀察轉成缺陷或提案、提案轉交其他通道；「下一步」寫明去向 |
| 已合併 | 併入另一筆觀察 |
| 已回滾 | 提案採納後被回滾（量測結果為回滾，或已執行 `app.rollback`） |

**4.4 嚴重度**（四個中文；值由各帳本依既有口徑判，您不用改）：`P0`、`P1`→緊急（rank 1）；`P2`→高（2）；`P3`→中（3）；`P4`→低（4）。缺陷帳本頭部仍寫 P0～P3 舊口徑，實況含 P4（以實況為準）。
- 讀法：觀察列取「嚴重度」欄；缺陷列取該欄開頭的 `P`＋數字（開頭的空白與 markdown 強調記號略過，後綴說明不看）；提案本身沒有此欄，取其 `sources` 中最嚴重者，查不到＝`null`（顯示「—」並列 `ne`，不補成低）。
- **兩組鍵、各有各的鎖**：觀察組＝`rows.SEVERITIES`（`P1`～`P4`，與上游雙向相等）；缺陷組＝`issuemap` 自持常數 `DEF_SEVERITIES`（`P0`～`P4`；缺陷帳本沒有集合型的上游常數，鎖＝真主檔嚴重度欄首碼的集合 ⊆ 該常數）。缺陷嚴重度欄不以 `P0`～`P4` 起頭（含 `P5` 之類不在常數內者）＝表外值，依 4.6 處理。
- 為何 P0、P1 併為緊急：兩組都是「各自最高級」，併成一級才能共用一個排序；原值仍在詳情的原列區。

**4.5 其他封閉詞**（時間線、下一步與提示條用；同樣由 `issuemap.py` 持有、同樣受 4.6 雙向鎖）：
- 事件動作（`events.KINDS` 全部）：run.open＝開運轉、run.close＝關運轉、research.scan＝研究掃描、research.skip＝免掃、attr＝歸因、attr.confirm＝確認歸因、attr.reject＝駁回歸因、prop＝提案、card＝出卡、dec＝決定、heldout.freeze＝凍結評估集、app.sandbox＝沙盒套用、app.verify＝驗證、app.promote＝晉升、app.rollback＝回滾、mea.open＝開量測窗、mea.close＝關量測窗、mea.amend＝更正量測、mea.report＝量測報告、obs.add＝新增觀察、obs.close＝關閉觀察。
- 決定動詞（`events.DKINDS` 全部；時間線的 `dec` 顯示為「決定：<動詞>」）：approve＝核准、reject＝否決、return＝退回、promote＝晉升、decline-promote＝不晉升、rollback＝回滾、unblock＝解除冷卻、resume＝恢復運轉、ack-handoff＝確認轉交。帳本標籤：觀察帳本、缺陷帳本、事件帳本。
- 通道（`events.ROUTES` 的 `handoff:` 後綴）：DEF＝缺陷帳本、R＝跨平台輪、T1＝掌舵者指令、PRD＝規格修訂。`problems` 碼：ROW-ARITY＝帳本列欄數不符（觀察列另含 ID 格式不合），該列不成議題；缺陷列的壞 ID 由 `defs.load_rows` 略過，是已知限制（§12）；ID-DUP＝同編號多列、只收第一列；UNMAPPED＝帳本值不在對照表；EVENT-PARSE＝事件帳本有讀不懂的行；EVENT-UNSOUND＝事件帳本有不合格事件、已略過。
- `ne` 理由：OBS-LEDGER-UNAVAILABLE＝觀察帳本讀不到、DEFECT-LEDGER-UNAVAILABLE＝缺陷帳本讀不到、SIBLING-LEDGER-UNAVAILABLE＝姊妹軌檔讀不到、EVENT-LEDGER-UNAVAILABLE＝事件帳本讀不到、SEVERITY-UNAVAILABLE＝嚴重度量不到、TIME-UNPARSEABLE＝時間欄解不出、CARD-UNAVAILABLE＝提案卡面建不出、MEASURE-UNAVAILABLE＝量測窗進度量不到、git-unavailable＝git 取不到版本（沿 `export` 既有理由）。

**4.6 封閉與 fail-loud 規則**：
- **雙向封閉鎖**：對照表的鍵集合必須與上游單一真相雙向相等——`events.PROP_STATES`、`events.KINDS`、`events.DKINDS`、`events.ROUTES`（通道）、`rows.CATEGORIES`、觀察嚴重度 `rows.SEVERITIES`、處置首詞（八個；`DISP_TOKEN_RE` 是正規式、`rows.py` 不改，改以八個探針字串加「`DISP_TOKEN_RE.pattern` 第一個捕捉群組內的分支數＝8」的斷言鎖，上游新增第九個分支即紅，見 AC-IC-01-1）、`defs` 的狀態標籤（五個）；上游新增值而本表沒登記＝測試紅，不是悄悄漏掉。
- **子集鎖與產出鎖**：缺陷嚴重度只做子集鎖（見 4.4）；`problems` 碼與 `ne` 理由是 `issues.py` 自己產出的封閉集合，鎖＝產出與表互為子集（AC-IC-01-7）。（`SelfImproving_PRD` §5.1.2 所述 `closed → retired` 不是 `PROP_STATES` 的值，不在表內；日後若入列，鎖會紅、須同步。）
- **表外機器值＝fail-loud**：該欄一律顯示「未歸類：<原值>」（狀態、結果、來源、嚴重度皆同；原值＝帳本裡那個對不上的值逐字，來源查不到時為來源項目 ID），不得靜默歸入任何一類、也不得丟棄該筆；顯示時原值超過 80 字以「…」截（「…」不計入），完整原值逐字放在該筆 `problems` 的 `detail`。
- **`problems` 一筆一值**：每個表外值各佔一筆（碼 `UNMAPPED`、subject＝議題 ID、detail＝「<維度>：<原值>」），不合併同值、不彙總計數。狀態為未歸類的議題只出現在「全部」分頁，不計入前三個分頁的數字（`summary.unmapped` 另計）。
- **量不到≠表外值**：欄位根本沒有值（例：提案無可查來源項目、時間欄解不出）＝該欄 `null`、列入 `ne`（顯示「—」），不顯示成零、低或空白字串。整本帳讀不到（檔缺或不可讀）＝該類議題整批缺席，由 `ne` 的 `*-LEDGER-UNAVAILABLE` 與畫面提示條明說，依賴它的 `summary.byTab` 格為 `null`（顯示「—」，不顯示成「0 件」）。
- **帳本讀不到的連帶規則**：觀察帳本讀不到時，來源項目含觀察號的提案，其來源與嚴重度為 `null` 並列同一筆 `ne`（不走 `UNMAPPED`）；事件帳本讀不到時，靠 `attr` 判定的路徑 A 無法判定，該類觀察列暫列候選並由同一筆 `ne` 明說。

## 5. 資料模型

**5.1 議題物件**（`export` 的 `items[]`；鍵序固定；鍵英文、值中文。本文欄位名一律寫 console-api 與畫面所見的 camelCase；`export`、CLI `--json`、Bridge 的同一鍵為 snake_case，如 `severity_rank`、`updated_at`、`next_step`、`next_since`、`by_status`、`by_tab`，轉換沿 `SiKeyNames`，值不動）：

| 欄位 | 型別 | 內容（來源） |
|---|---|---|
| `id` | string | 原帳本 ID（`OBS-SI-NNN`、`DEF-<族>-<序>`、`PROP-SI-NNN`） |
| `source` | string | 四來源之一（§2）或「未歸類：<原值>」；來源項目所在帳本讀不到而無從判定＝`null`（顯示「—」，並列 `ne`） |
| `title` | string | 觀察＝「症狀」欄；缺陷＝「現象與證據」欄；提案＝提案卡〈一、症狀〉（`card.build` 的 `fields.symptom`）；姊妹軌孤列固定為「（主帳本列已歸檔）」；去 markdown 記號、空白折疊；超過 80 個 code point 者取前 80 個再加「…」（「…」不計入；本檔所有「N 字」皆以 code point 計，全形與表情符號各算 1），原文在 `raw` |
| `severity`、`severityRank` | string、int | 四個中文（§4.4）與 1～4；量不到為 `null`；表外值為「未歸類：<原值>」且 `severityRank` 為 `null` |
| `status` | string | 七狀態之一（§4.1）或「未歸類：<原值>」 |
| `result` | string | 八結果之一（量測結果對不上時為「未歸類：<原值>」）；僅 `status`＝已完成時有值，否則 `null` |
| `updatedAt` | string | `YYYY-MM-DD`（規則見下）；解不出為 `null` 並列 `ne` |
| `nextStep` | string | §5.2 |
| `origin` | object | 觀察、缺陷：`{ledger, file, line}`（`ledger` 為「觀察帳本」「缺陷帳本」；姊妹軌孤列的 `file` 為姊妹軌檔）；提案：`{ledger:"事件帳本", file, seq}`（取 `prop` 事件的 `created_seq`） |
| `links` | string[] | 直接關聯的議題 ID（去重、依 ID 排序），**方向逐類固定**：提案的 `sources`＝雙向；觀察處置指向的 `DEF-`、`merged@`、`proposed@`＝雙向（目標議題也列回該觀察）；標記 `rel`（取 `corrects:`／`recurs:` 冒號後的 ID）與 `reopens`＝單向（本列→被指者）；`attr` link 的 `from`→`reopens`＝單向 |
| `rankable` | bool | 狀態可排優先順序（§4.1 最右欄） |
| `action` | string | `decide-proposal`（待您決定的提案）、`close-observation`（待您決定的觀察），其餘 `null`；畫面依它決定按鈕 |
| `raw`、`timeline` | array | **只在單筆（`--id`）出現**。`raw`＝`[{label, value}]`：觀察九欄與缺陷七欄（含姊妹軌欄）以帳本表頭為中文標籤、值逐字；提案為「提案卡」全文加原值（狀態、路由…）。`timeline`＝`[{seq, t, by, action}]` 依 `seq` 升冪，`action` 用 §4.5 的中文 |
| `priority`、`priorityNote` | int、string | **只由 console-api 加上**（Console 自有資料，§6.4）：僅 `rankable` 為真且有列時＝順位（優先順序的號碼，1 最先）與備註（可為空字串）；其餘（`rankable` 為假，或無列）＝兩者 `null`，不顯示、不參與排序；`export` 與 CLI 沒有這兩欄；遺留列見 AC-IC-09-10 |

- `updatedAt`：觀察＝時間欄的起日（區間「起～迄」取起），若有 `obs.close` 事件則取兩者較晚的日期；缺陷＝發現日期；姊妹軌孤列＝其「最近複查日」；提案＝最後一筆事件（`last_seq`）的日期；日期一律取時間字串的日期部分、不換算時區。**帳本沒有記結案時間**，故已完成議題的日期是「最後已知動靜」而非結案日（詳情與狀態說明須如實寫出）。
- 時間線的引用鍵：觀察與缺陷＝`attr`（`obs`、`items` 的 `[DEF|OBS, ID]`、`from`、`reopens`）及其 `attr.confirm`／`attr.reject`、`prop`（`sources`）、`obs.add`／`obs.close`（`obs`）；提案＝`prop`（`id`）、`card`／`dec`／`heldout.freeze`／`app.*`／`mea.*`（`prop`）、該提案 `run` 的 `run.open`／`run.close`。

**範例**（`export` 的清單項目，取真帳本 2026-10-26 的 PROP-SI-005；來源項目 OBS-SI-201 為 P4、來源代理；單筆另有 `raw`、`timeline`，console-api 另有 `priority`、`priorityNote`）：

```json
{"id": "PROP-SI-005", "source": "系統改善", "title": "進度帳 §5.2 最後一列仍是 374，RTM 現為 392，兩者不一致",
 "severity": "低", "severity_rank": 4, "status": "觀察中", "result": null, "updated_at": "2026-10-26",
 "next_step": "量測窗 0／5", "origin": {"ledger": "事件帳本", "file": "docs/06_quality/SelfImproving_Event_Ledger.jsonl", "seq": 9},
 "links": ["OBS-SI-201"], "rankable": false, "action": null}
```

**5.2 「下一步」推導**（每個情境恰一句；`[ ]` 內為代入值；全句 ≤ 80 字、不含 §4.2 機器值欄的英文詞〔整詞比對，議題 ID 形態除外；通道已中文化；延後列方括號內的帳本原文節錄除外，它可能含英文片段，只驗截斷長度〕）：

| 狀態／情境 | 下一步 |
|---|---|
| 候選 | 等歸因確認（歸因者提出、審查者確認），或由掌舵者簽核成立 |
| 待您決定・提案 `proposed`（`route=loop`） | 等掌舵者決定：核准、否決或退回 |
| 待您決定・提案 `proposed`（`route=handoff:[通道]`） | 等掌舵者決定：轉交、不轉交或退回（通道：[通道中文]） |
| 待您決定・提案 `verified` | 驗證已有結果，等掌舵者決定（可選的決定依驗證結果而定，見「決定」對話框） |
| 待您決定・提案 `closed`（復發待回滾） | 量測窗內復發，等您決定是否回滾（目前只有「回滾」動詞） |
| 待您決定・觀察（分類 decision） | 等掌舵者決定：在此關閉並寫下裁決 |
| 待解・缺陷 | 尚未分流，等待修復 |
| 待解・觀察 | 已成立，尚無人接手 |
| 進行中・缺陷 `routed` | 已分流待修 |
| 進行中・提案 `approved` | 已核准，等沙盒套用 |
| 進行中・提案 `returned` | 已退回，等提案者修訂（第 [rev] 版） |
| 進行中・提案 `sandboxed` | 沙盒已套用，等驗證 |
| 進行中・提案已決定回滾（`promoted`／`measuring`／`closed` 且 `dec(rollback)` 已記、尚未執行） | 已決定回滾，等執行回滾 |
| 觀察中・提案 `promoted` | 已晉升，等量測窗開啟 |
| 觀察中・提案 `measuring` | 量測窗 [n_opp]／[w_opp]（`n_opp` 取 `status.measure_value` 的 `windows[].n_opp`〔與 `si status` 的 `measure.windows` 同源〕，`w_opp` 取該提案 `mea.open` 事件的 `w_opp`；`issues.py` 不直呼 `meaplan.window_rows`；NOT-EVALUABLE 或查無該窗＝「量測窗進度量不到」並列 `ne`） |
| 延後・觀察 | 等再開症狀出現：[處置欄附加文字，去前導分隔符與「再開症狀：」，截 40 字] |
| 延後・缺陷（姊妹軌） | 等解鎖條件：[姊妹軌「解鎖條件」欄，截 40 字]（最近複查 [日期]） |
| 已完成 | 已結案（[結果]）；觀察的已轉交加「，見 [目標 ID]」、提案的已轉交加「，通道：[通道中文]」；提案已否決者加「；同型冷卻中」或「；冷卻已解除」 |
| 未歸類 | 帳本值不在對照表內，請查原列 |

**5.3 排序**：`export`／API 的輸出順序＝游標序（便於分頁）；顯示序由消費者套用，規則只有兩條（`updatedAt` 為 `null` 者兩條都排最後；順位只對 `rankable` 的列存在，其餘視為無順位）：
- **待處理、待您決定**：優先順序升冪（無順位排最後）→ `severityRank` 升冪（`null` 最後）→ `updatedAt` 升冪（最久沒動的在前，`null` 最後）→ `id` 字串升冪。
- **已完成、全部**：`updatedAt` 降冪（`null` 最後）→ `id` 升冪；全部分頁另把狀態為待您決定的列置頂（見 §7）。
- 實作各一份：`issues.py` 的頁內顯示序供 CLI（無順位），`lib/domain/issues.ts` 供畫面（含順位）；AC-IC-05-1 以同一張範例表兩端各驗一次。

**5.4 游標、圖例與摘要**：
- **游標**：整數；同一帳本內隨附加單調遞增、跨來源不撞號、附加新列不改變既有項的游標（觀察＝OBS 號數字、提案＝PROP 號數字、缺陷＝主檔資料列行號〔`DefRow.lineno`；DEF 號的族與序不單調，不能當游標〕、姊妹軌孤列＝其所在檔的行號，各加不重疊的基數，細則由 TCS 定）；`since` 取游標嚴格大於它者，`next_since`（console-api 為 `nextSince`）＝本頁最後一項的游標、末頁為 `null`；篩選在分頁**之前**套用；帳本輪替歸檔會重排行號，所以前端每次進頁從頭載入、不跨載入保存游標。
- **`legend`**（清單回應每次都帶，單筆不帶）：`statuses[{name, meaning, tab, rankable}]`（`tab`＝專屬分頁名，候選與延後為 `null`）、`results[{name, meaning}]`、`sources[{name, meaning}]`（依 §2 順位排列）、`severities[{name, rank, meaning}]`、`problemCodes[{code, meaning}]`、`neReasons[{reason, meaning}]`、`unmappedLabel`（「未歸類」前綴字串）、`updatedAtNote`（§5.1 的「最後已知動靜」註記）；`meaning`＝§4 的一句話（問題碼與 `ne` 理由取 §4.5）。「狀態說明」、提示條與狀態 pill 的文字都來自它，前端不持有第二份。
- **`summary`**（清單回應每次都帶，單筆不帶）：`{total, byStatus{七狀態→件數}, byTab{待處理, 待您決定, 已完成}, unmapped}`，**整本帳**的計數，不受篩選、`since`、`limit` 影響；`problems`、`ne` 同樣是整本帳一份，每頁相同。`byTab` 某格所依賴的帳本讀不到時為 `null`（觀察或事件帳本讀不到＝三格；缺陷或姊妹軌讀不到＝待處理與已完成），畫面顯示「—」；`total`、`byStatus` 只計讀得到的帳本（`ne` 已聲明不完整）。

## 6. 介面契約

**6.1 CLI**（`tools/selfimproving.py` 加一個唯讀動詞，薄殼不含判準）：`python tools/selfimproving.py issues [--status <中文[,中文…]>] [--source <中文[,中文…]>] [--since N] [--limit N] [--json] [--repo <路徑>]`
- 預設輸出純文字中文表：每議題一行「編號、來源、嚴重度、狀態、最後更新、標題→下一步」，欄以兩個空白分隔並依顯示寬度（全形算 2，沿 `card.width` 同一量法）對齊；末行「共 N 件；問題 M 筆」，被截斷時加「尚有更多，--since <next_since>」。`--json`＝與 `export --kind issues` 同一份物件（一行 JSON）。
- `--status` 值＝七個狀態名或分頁名「待處理」；`--source` 值＝四個來源名；逗號分隔取聯集，兩旗標並用取交集；未知值 → rc 3，stderr 列出合法值。`--since` ≥ 0、`--limit` 介於 1 與 `export_limit_max`（`params.json`），否則 rc 3。rc：0＝已執行、3＝用法或輸入錯誤（沿 `selfimproving.py` 檔頭）。唯讀：不寫任何檔、不讀家目錄。

**6.2 匯出**：`python tools/selfimproving.py export --json --kind issues [--since N] [--limit N] [--id <ID>] [--status …] [--source …]`
- `export.KINDS` 加 `issues`；`--id` 接受三種議題 ID 格式且不與 `--status`／`--source` 併用；`--status`／`--source` 只配 `--kind issues`（其餘 kind 帶它們＝rc 3）。
- 回傳沿既有形狀：`schema_rev`（維持 1，新增鍵為加法）、`kind`、`generated_at`、`head_sha`、`items`、`next_since`、`truncated`、`ne`、`problems`，另有 `legend`、`summary`（單筆無）。`problems` 的碼（封閉，§4.5）：`ROW-ARITY`、`ID-DUP`（同 ID 後列不收）、`UNMAPPED`、`EVENT-PARSE`（事件帳本中非 JSON 物件的行，沿 `export` 既有碼）、`EVENT-UNSOUND`（JSON 物件但未過 `events.validate`、不進折疊的事件，一筆一事件）；`ne` 的理由見 §4.5。

**6.3 Engine Bridge**（唯讀；每請求恰啟動一次 `si export` 子行程；無快取）：
- `GET /si/issues?since=&limit=&status=&source=`、`GET /si/issues/{id}`；200 本文＝子行程輸出解析後的物件逐值透傳；其他方法 405。
- 輸入驗證在子行程之前：清單類只收 `since`、`limit`、`status`、`source`（其餘 422 `invalid_request`，`rule=unknown_parameter`），單筆不收任何查詢參數；`status`／`source` 值 ≤ 64 字元、不得以 `-` 起頭、不得含控制字元（U+0000～U+001F、U+007F；例：NUL 會使啟動子行程拋例外而回 500），不合＝422，以 `--status=<值>` 單一 argv 傳入；`{id}` 須符 `OBS-SI-<三位以上數字>`、`PROP-SI-<三位以上數字>` 或 `DEF-<數字>-<數字>`，不符 422；合法而查無 404 `si_not_found`。
- CLI 失敗（含未知篩選值 rc 3）＝503 `si_unavailable`（`cause`、`detail` 逐字；沿既有 `limit` 越界同型）。`si_cli.SI_KINDS` 加 `issues`，`build_argv` 補 `--status`、`--source`。

**6.4 console-api**（`/api/v1`；回應包既有 `{code,message,data,…}`）：

| 端點 | 角色 | 說明 |
|---|---|---|
| `GET /issues?status=&source=&since=&limit=` | VIEWER 以上 | 轉遞 Bridge 物件（鍵 snake→camel、值不動）並在每筆加 `priority`、`priorityNote`；`since`<0 或 `limit`<1＝400（不觸及 Bridge）；其餘錯誤同 SI 唯讀端點（503 `si_unavailable`、422、502、504） |
| `GET /issues/{id}` | VIEWER 以上 | 單筆：含 `raw`、`timeline`、`links` 與 priority；格式不合 422、查無 404 `si_not_found`（訊息「查無此議題」，不沿用「查無此提案」） |
| `PUT /issues/{id}/priority` | **僅 ADMIN** | 設定或更新順位：body `{rank: 整數 1～9999, note: 字串 ≤ 200 個 code point（口徑同 §5.1）、不含控制字元}`，`rank` 必填（null 或缺＝422，**不**當清除），`note` 選填（缺＝空字串）；成功 200 `{id, rank, note, setBy, setAt}` |
| `DELETE /issues/{id}/priority` | **僅 ADMIN** | 清除順位＝刪列（與 `rank` NOT NULL 一致）：無 body；成功 204（沿既有 DELETE 慣例），該列不存在也 204（冪等）；不呼叫 Bridge |

- **PUT 的驗證序**（先中者定案）：401 → 403 `ACCESS_DENIED`（非 ADMIN）→ 422 `invalid_request`（`details.violations[{field,message}]` 一次全列；`id` 格式與 DB 的 CHECK 同式）→ 呼叫 Bridge 取該議題：失敗沿 SI 唯讀端點同表（503 `si_unavailable`、502、504）、查無 404 `si_not_found`、`rankable` 為 false 409 `issue_not_rankable` → UPSERT。
- **DELETE 的驗證序**：401 → 403 → 422（`id` 格式）→ DELETE；不呼叫 Bridge、冪等，所以議題已完成或已不存在時仍清得掉遺留順位。兩者都不要求 `console.si.deciders` 名單（優先順序不是帳本決定）。
- **安全層**：`SecurityConfig` 在通用 `/api/v1/**` 規則**之前**加 `PUT`、`DELETE` 的 `/api/v1/issues/**`＝ADMIN（各一條，否則 OPERATOR 會通過）；沿既有 `AuditLoggingFilter`（位於授權之前），兩者成功與被拒（401／403）都在 `console.audit_log` 留一列。
- **傳遞**：`AgentBridge.siExport` 簽章由 `(kind, since, limit, id)` 增為 `(kind, since, limit, id, status, source)`（既有呼叫端 `SiMirrorQueryService`、`SiReconcileService` 補 `null`），`si` 起頭方法仍恰五個。讀優先順序表失敗＝整個請求失敗、沒有 `data`（不回缺 priority 的清單，以免把「量不到」顯示成「未排」）。
- **查詢值編碼**：`BridgeHttpAdapter.siExport` 沿既有作法以 `URI.create(完整網址)` 發請求（不經範本引擎，否則已編碼的 `%` 會被再編一次），所以 `status`／`source` 須先嚴格 percent-encode（UTF-8，僅非保留字元原樣，同 `pathSegment` 規則）；漏編時含空白、豎線等字元的值會使 `URI.create` 拋例外而回 500。
- 新增 reason `issue_not_rankable`（409；後端 `ErrorReasons` 加常數）：**不入 `reasons.ts`**（它與 `API_Contract_P3-6.md` 附錄 B 雙向鎖，動它會連動該契約）；中文訊息由 `lib/domain/issues.ts` 的 `ISSUE_REASONS` 持有，並與新契約檔 `API_Contract_IssueCenter.md` 的 reason 表雙向鎖（比照 `reasons.test.ts`，AC-IC-07-9）。分層守既有 A1～A6；新增 `IssueController`（名稱不符 `Si*Controller`，不受那組計數鎖；議題中心唯一帶 PUT、DELETE 映射的類別，各恰一個）。

**6.5 資料庫**（Flyway `V14__issue_priority.sql`，沿 V13 風格：`console` schema、JDBC 配接器、無 JPA 實體）：

```sql
CREATE TABLE console.issue_priority (
    issue_id VARCHAR(64) PRIMARY KEY CHECK (issue_id ~ '^(OBS-SI-[0-9]{3,}|PROP-SI-[0-9]{3,}|DEF-[0-9]+-[0-9]+)$'),
    rank     INTEGER      NOT NULL CHECK (rank BETWEEN 1 AND 9999),
    note     VARCHAR(200) NOT NULL DEFAULT '',
    set_by   VARCHAR(64)  NOT NULL,
    set_at   TIMESTAMP WITH TIME ZONE NOT NULL
);
```

- 與草案 DDL 的差異：`rank`、`note` 為 NOT NULL——清除走 `DELETE /issues/{id}/priority`（刪列，不用 `rank`＝null 當清除），表內不會有沒有順位的列，約束放結構層。`note` 長度以 code point 計（PG 的 `VARCHAR(200)` 同口徑）。不存歷史（變更軌跡在 `console.audit_log`）；順位可重複（同順位依 §5.3 後續鍵排）。

**6.6 前端與導覽**：
- 路由 `/issues`（`app/issues/page.tsx` 只殼，`metadata.title`＝「議題中心」）；元件目錄 `components/domain/issues/`；`lib/api`（`endpoints`、`queries`、`types`）加條目——四個新函式 `getIssues`、`getIssue`、`putIssuePriority`、`deleteIssuePriority`，**不動 `reasons.ts`**；`schema.d.ts` 由 `openapi-typescript` 重產入庫；純函式 `lib/domain/issues.ts`（顯示序、計件、優先順序表單驗證、`ISSUE_REASONS`）加同名測試。
- 導覽登記表加一列 `{id:"issues", label:"議題中心", icon:ListChecks, href:"/issues", match:/issues 與其子路徑, order:55, enabled:true, mobile:false, roles 缺}`，加在陣列**末尾**（顯示序由 `order` 決定，原七列的陣列位置與索引不變）；order 介於監控中心 50 與系統設定 60；`mobile:false`＝底部 Tab 已滿 6 項，先例同 `self-improving`。**既有「自我進化」一列（label、order 70、mobile）完全不變**，只是排在議題中心之後；不改 `ToolsRegion.tsx`。
- 導覽相關既有鎖（`registry.test.ts` 的 `AT_932_6_1`、`AT_950_10_E_1`；`ToolsRegion.test.tsx` 的連結數與預期序）須同步，逐檔逐行見 §9；`AT_950_10_E_1`「P2b 沒動導覽」的原意改述為「原七列各欄不變，另加議題中心一列」，`NAV_REGISTRY[6]` 仍是 `self-improving`。

## 7. 畫面（左列 TOOLS 新增「議題中心」；所有角色可看，寫入只給 ADMIN）

- **版面（上到下）**：標題列（右上「狀態說明」鈕）→ 摘要列（待處理 N、待您決定 M、已完成 K〔現存帳本內〕，取 `summary.byTab`，`null` 格顯示「—」，可點切換分頁）→ 四個 pill 分頁（預設「待處理」，沿用 `PillTabs`）→ 篩選列（來源下拉；關鍵字＝編號與標題，只篩已載入的頁）→ 提示條（`ne`、`problems` 非空時顯示件數與 `legend` 的中文說明，帳本讀不到時明說哪一本，不阻擋清單）→ 清單。

| 分頁 | 內容（向 API 傳的 `status`） | 排序（§5.3） | 可做的事 |
|---|---|---|---|
| 待處理 | `待處理`（＝待解、進行中、觀察中）；上方計件條「緊急 a・高 b・中 c・低 d・— e・未歸類 f」（嚴重度量不到者計 e，表外值者計 f） | 第一條 | 看詳情；ADMIN 對可排的列設優先順序 |
| 待您決定 | `待您決定`，每列帶置頂標記元素（`data-testid="issue-top-pinned"`、`aria-label="置頂"`） | 第一條 | ADMIN：提案列「決定」、觀察列「關閉並裁決」 |
| 已完成 | `已完成` | 第二條 | 依來源、結果（`legend.results`）、關鍵字篩；看詳情 |
| 全部 | 不帶 `status`（含候選、延後、未歸類）；待您決定的列置頂（先於其他列、帶同一標記元素，其內依第一條） | 第二條 | 七顆狀態 pill 快篩（文字取自 `legend`）加「未歸類」 |

- **清單**固定八欄：編號（原帳本 ID，點開詳情）、來源、標題、嚴重度、狀態（已完成者併列結果）、優先順序（只對 `rankable` 的列顯示）、最後更新、下一步（待您決定列的按鈕放在此欄尾）。
- **詳情**（同頁側面板，不換路由）：頭部（編號、來源、狀態與結果、嚴重度、順位）→ 下一步 → 原列（`raw`，中文標籤；這是唯一可見英文原值的地方）→ 事件時間線（`timeline`）→ 關聯（`links`，可點）。已完成議題的日期旁註明「最後已知動靜」。
- **優先順序**：ADMIN 對 `rankable` 的列有「排序」鈕，開對話框（順位 1 最先、備註 ≤ 200 個 code point；「儲存」走 PUT、「清除」走 DELETE）；非 ADMIN 看得到、改不到。您排了順位的排在前面，其餘依 §5.3 後續鍵；非 `rankable` 的遺留順位不顯示、不參與排序。
- **按鈕**（只有 ADMIN 看得到）：提案列＝「決定」，先 `getSiProposal(id)` 取點擊當下快照，再開 `SiDecideDialog`（`target={{ kind: "prop", proposal }}`；沿用其綁 digest、預設不選動詞、無批次核准；動詞依既有 `decideVerbOptions`，`closed` 提案只有「回滾」，`lib/domain/si.ts:512`）；觀察列＝「關閉並裁決」開 `SiObsCloseDialog`（`target={{ obsId }}`）。簽章成功只代表稽核檔已落地、待主機入帳；列不樂觀移動，入帳後重新載入才換狀態。非 ADMIN 該欄顯示「需要 ADMIN 角色才能操作」。
- **載入**：向 API 逐頁取；沿用自我進化頁的自動載完與頁數上限（`SI_AUTO_LOAD_MAX_PAGES`），到上限仍有未載入者明說「結果不完整」。**空與錯**：分頁真的沒有議題＝「這個分頁目前沒有議題」；量不到（Bridge 失敗、逾時）＝整片顯示原因（`cause`、`detail` 逐字），摘要列數字顯示「—」，絕不顯示成「0 件」；某本帳讀不到＝依賴它的摘要格（`byTab` 為 `null`）顯示「—」、提示條明說，其餘格與清單照常。
- **安全**：帳本與備註文字一律純文字（不經 HTML、不渲染 markdown）。

## 8. 驗收準則（AC；Given／When／Then，每條可由一支測試判定）

| AC | 內容 |
|---|---|
| **FR-IC-01** | **對照表封閉、唯一歸類、fail-loud（§4）** |
| `AC-IC-01-1` | Given 對照表與 §4.6 所列上游集合 When 雙向比對 Then 每個機器值（含條件欄的每種取值）恰有一個中文歸類，表內沒有可鎖集合以外的鍵（缺陷嚴重度見 AC-IC-01-4）；處置首詞以八個探針字串（`open`、`deferred`、`retired`、`decided`、`fixed@abc1234`、`DEF-1-1`、`merged@OBS-SI-001`、`proposed@PROP-SI-001`）逐一餵 `rows.disp_token`，各被辨識為對應鍵（`fixed@`、`merged@`、`proposed@`、`DEF-` 以前綴為鍵），未列探針（`later`、`closed`）回 `None`；另斷言 `DISP_TOKEN_RE.pattern` 第一個捕捉群組內的分支數＝8；上游新增值而表未登記＝紅 |
| `AC-IC-01-2` | Given 夾具含表外值（提案 `state` 為 `zombie`——事件帳本產不出此值，夾具以程序內注入縫構造：測試 patch `fold.fold` 回傳含該狀態的 `Folded`，縫的寫法由 TCS 寫入；觀察處置為 `later`；缺陷狀態欄無可辨識關鍵字）When 建議題 Then 該議題 `status` 為「未歸類：<原值>」、`problems` 一值一筆 `UNMAPPED`（subject＝議題 ID、detail＝「<維度>：<原值>」）、`summary.unmapped` 加一、只出現在「全部」、匯出 rc 0；反例：同夾具中合法值的議題照常歸類，不受牽連 |
| `AC-IC-01-3` | Given 每種終態夾具（觀察六終值、缺陷三終類、提案 `rejected`／`handed-off`／`closed` 的各生效結果，含 `closed` 且已有被消耗的 `app.rollback`）When 建議題 Then `result` 依 §4.2 為八結果之一（`closed`：量測結果 `rolled-back` 或已消耗 `app.rollback`＝已回滾，`clean`＝已採納，`recurred` 另依 AC-IC-03-7）；非已完成者 `result`＝`null`；僅 `closed` 且生效量測結果量不到（同注入縫構造）者：`result` 顯示「未歸類：closed」並計 `UNMAPPED`，`status` 一律為已完成（無從判定是否復發，不進待您決定或進行中） |
| `AC-IC-01-4` | Given 觀察嚴重度 P1～P4 與缺陷嚴重度 P0～P4 When 對照 Then 依序為緊急（P0、P1）、高、中、低（rank 1、1、2、3、4）；缺陷嚴重度欄不以 `P0`～`P4` 起頭（例「—（流程紀錄）」「P5」）＝「未歸類：<原值>」並計 `problems`；`DEF_SEVERITIES` 子集鎖對真主檔綠（真帳本首碼集合 ⊆ 常數）；提案取來源最嚴重者，全查不到＝`null` 並列 `ne`（`SEVERITY-UNAVAILABLE`） |
| `AC-IC-01-5` | Given 任一清單回應 When 讀 `legend` Then 恰七狀態、八結果、四來源、四嚴重度、五個 `problemCodes`、九個 `neReasons`，每項 `meaning` 非空，`statuses[].tab` 與 §4.1 相同，`sources` 依 §2 順位排列，另帶 `unmappedLabel`、`updatedAtNote`（內容含「最後已知動靜」） |
| `AC-IC-01-6` | Given 三個議題各有一個表外值（其中兩個是同一個值）When 建議題 Then `problems` 恰三筆 `UNMAPPED`（一值一筆，subject 各為其議題 ID，同值不合併、不彙總計數），三者對應的欄位皆顯示「未歸類：<原值>」 |
| `AC-IC-01-7` | Given `issues.py` 的全部出口（`problems` 碼、`ne` 理由）與 `issuemap` 的對應表 When 以探針夾具逐一觸發（含無 git 的夾具觸發 `git-unavailable`）Then 實際產出的碼與理由都在表內且有非空中文（產出 ⊆ 表），表內每項至少被一個夾具觸發（表 ⊆ 產出）；通道鍵恰為 `events.ROUTES` 的 `handoff:` 後綴，時間線動作與決定動詞各恰為 `events.KINDS`、`events.DKINDS` |
| `AC-IC-01-8` | Given 觀察、缺陷、姊妹軌（兩檔之一）、事件四種帳本各自缺檔或不可讀的夾具（各一）When 建議題 Then 該帳本的議題整批缺席、`ne` 恰多一筆 `OBS-LEDGER-UNAVAILABLE`、`DEFECT-LEDGER-UNAVAILABLE`、`SIBLING-LEDGER-UNAVAILABLE`、`EVENT-LEDGER-UNAVAILABLE`（事件帳本缺檔不再另報 `carrier-not-established`）、其餘帳本的議題照常、匯出 rc 0；`summary.byTab` 依賴該帳本的格為 `null`（觀察或事件＝三格；缺陷或姊妹軌＝待處理與已完成） |
| `AC-IC-01-9` | Given 事件帳本含一行非 JSON 物件的文字、一筆 JSON 物件但未過 `events.validate` 的事件（例缺 `seq`）、其餘合法事件 When 建議題 Then 前者計一筆 `EVENT-PARSE`（subject＝`L<行號>`）、後者計一筆 `EVENT-UNSOUND`（subject＝`L<行號>`，一筆一事件、不進折疊）、其餘提案照常、匯出 rc 0 |
| `AC-IC-01-10` | Given 表外原值為 100 個 code point（含全形字與表情符號）的議題與恰 80 個 code point 的議題各一（同注入縫或表外處置值構造）When 建議題 Then 前者該欄顯示「未歸類：」加原值前 80 個 code point 再加「…」（「…」不計入），其 `problems[].detail` 的原值逐字完整、不截；後者不加「…」；兩者各計一筆 `UNMAPPED` |
| `AC-IC-01-11` | Given 觀察帳本缺檔而事件帳本在（提案的來源項目含觀察號）的夾具，與事件帳本缺檔而觀察列 `open`、需 `attr` 判定的夾具 When 建議題 Then 前者提案的 `source`、`severity` 為 `null` 並列同一筆 `OBS-LEDGER-UNAVAILABLE`、不計 `UNMAPPED`；後者該觀察列暫列候選，由 `EVENT-LEDGER-UNAVAILABLE` 明說；對照例：來源項目只有 `DEF-` 號的提案在觀察帳本缺檔時仍照常判定來源；事件帳本缺檔時 `decision` 類或路徑 B 的 `open` 觀察列仍照常（待您決定／待解） |
| **FR-IC-02** | **來源判定（§2）** |
| `AC-IC-02-1` | Given 觀察列標記含 `carrier=console`（或 `來源=人`）且分類 `bug` When 建議題 Then `source`＝使用者提案（優先於系統缺陷）；反例：標記只有 `來源=代理` 的 `bug` 列＝系統缺陷 |
| `AC-IC-02-2` | Given 觀察列標記含 `回報者=研究者`、分類 `tooling`（來源非人）When 建議題 Then `source`＝研究提案；反例：同為研究者但分類 `bug`＝系統缺陷（順位在研究提案之前）；`回報者=研究員`（PRD 階段的研究代理，非研究掃描）且分類 `doc`＝系統改善 |
| `AC-IC-02-3` | Given 缺陷帳本任一列，或觀察列分類 `bug`（來源非人；含研究者回報的）When 建議題 Then 系統缺陷；反例：分類 `tooling` 的觀察列不是系統缺陷 |
| `AC-IC-02-4` | Given 觀察列分類 `process`、`tooling`、`doc` 或 `decision`（來源非人、非研究者）When 建議題 Then 系統改善；反例：分類 `bug` 不是系統改善 |
| `AC-IC-02-5` | Given 提案 `sources` 含使用者提案觀察與缺陷 When 建議題 Then 依順位（使用者提案 > 系統缺陷 > 研究提案 > 系統改善）取最前者＝使用者提案；`sources` 含研究提案觀察與 `DEF-` 來源＝系統缺陷；來源觀察查不到者略過，全查不到＝「未歸類：<來源項目 ID>」並計 `problems`（一值一筆） |
| **FR-IC-03** | **成為正式議題（§3）** |
| `AC-IC-03-1` | Given 觀察列 `open`、分類 `bug`、來源代理、無任何 `attr` When 建議題 Then 狀態＝候選、不在待處理與待您決定、`rankable`＝false |
| `AC-IC-03-2` | Given 同列另有 `attr`（type root 的 `obs` 含該列，或 type link 的 `from`）且其 `attr.confirm` 已入帳 When 建議題 Then 狀態＝待解；反例：`attr` 未確認、或被 `attr.reject`＝仍是候選 |
| `AC-IC-03-3` | Given 觀察列 `open` 且標記含 `carrier=console`（或 `來源=人`）、分類 `process` When 建議題 Then 待解（不需 `attr`）；分類 `decision` 的 `open` 列不論路徑＝待您決定，且 `action`＝`close-observation` |
| `AC-IC-03-4` | Given 處置為終值或 `deferred` 的觀察列 When 建議題 Then 永不為候選；缺陷 `open`＝待解、提案 `proposed`＝待您決定（不經候選） |
| `AC-IC-03-5` | Given 尚未入帳的 Console 稽核檔（家目錄 `console_audit/<uuid>.json`）When 建議題 Then 它不是議題（議題只讀帳本；`export` 不讀家目錄） |
| `AC-IC-03-6` | Given 已成立（路徑 A 或 B）、分類 `process`、`tooling` 或 `doc` 的 `open` 觀察列 When 建議題 Then 狀態＝待解、`action`＝`null`、不在待您決定；全帳本中狀態為待您決定的議題成員恰為提案 `proposed`、`verified`、復發待回滾的 `closed`（AC-IC-03-7）與分類 `decision` 的 `open` 觀察列 |
| `AC-IC-03-7` | Given 五個提案夾具：①`closed`、`recurred`、從未有 `dec(rollback)`；②`closed`（`recurred` 或 `clean`）、有 `dec(rollback)` 而 `app.rollback` 未消耗；③`closed`、`recurred`、`app.rollback` 已消耗；④`closed`、`clean`；⑤`promoted`／`measuring`、有 `dec(rollback)` 未消耗 When 建議題 Then ①待您決定（`rankable`＝true、下一步「量測窗內復發，等您決定是否回滾（目前只有「回滾」動詞）」）、②⑤進行中、③已完成・已回滾、④已完成・已採納；①與 `meaplan.rollback_pending` 逐值相同（差分） |
| **FR-IC-04** | **下一步與欄位（§5）** |
| `AC-IC-04-1` | Given §5.2 每一列情境各一夾具 When 建議題 Then `nextStep` 恰為該列句型（含代入值）、非空、≤ 80 字（code point）、不含 §4.2 機器值欄的英文詞（整詞比對：前後字元不屬英數與 `-`；先剔除議題 ID 形態 `OBS-SI-NNN`、`PROP-SI-NNN`、`DEF-<族>-<序>`；通道已中文化；延後列方括號內的帳本原文節錄除外，只驗截 40 字）；`verified` 句型不預設驗證結果 |
| `AC-IC-04-2` | Given `measuring` 的提案，`status.measure_value` 回該窗 `n_opp`＝0、該提案 `mea.open` 事件的 `w_opp`＝5 When 建議題 Then 下一步含「量測窗 0／5」；`measure_value` 為 NOT-EVALUABLE 或查無該窗＝「量測窗進度量不到」並列 `ne`（`MEASURE-UNAVAILABLE`），不顯示 0／5；`issues.py` 原始碼不直呼 `meaplan.window_rows` |
| `AC-IC-04-3` | Given 症狀含 markdown 記號或超過 80 個 code point（含全形與表情符號）的觀察列，並有兩個 `updatedAt` 夾具：A＝時間欄為區間「2026-10-18 22:47～10-19 02:20」且無 `obs.close`；B＝起日 `2026-10-18`、另有日期 `2026-10-20` 的 `obs.close`；另有缺陷列與提案 When 建議題 Then `title` 取前 80 個 code point 再加「…」（「…」不計入）、無 `**` 與反引號；`updatedAt` A＝`2026-10-18`、B＝`2026-10-20`、缺陷＝發現日期、提案＝最後事件日期；時間欄解不出＝`null` 並列 `ne`（`TIME-UNPARSEABLE`） |
| `AC-IC-04-4` | Given 提案 `sources` 含某觀察；觀察處置為 `DEF-…`（該 DEF 是議題）、`merged@…`、`proposed@…`；觀察標記 `rel=corrects:<ID>`、`rel=recurs:<ID>`；`attr` link 的 `from`→`reopens` When 建議題 Then 提案與來源、處置指向者雙向互含（去重、依 ID 排序）；`rel`（取冒號後的 ID）與 `attr` 的 `from`→`reopens` 單向（只有起點含目標、目標不回列）；指向主檔以外 DEF 的處置仍列入 `links` |
| `AC-IC-04-5` | Given 觀察 `deferred；再開症狀：X`，或缺陷 ID 列在姊妹軌表（合成夾具，現況兩表皆空）When 建議題 Then 狀態＝延後、下一步含 X 或「解鎖條件」原文；姊妹軌 DEF-ID 在主檔找不到＝仍成議題：來源系統缺陷、狀態延後、標題「（主帳本列已歸檔）」、嚴重度 `null` 並列 `ne`（`SEVERITY-UNAVAILABLE`）、不進 `problems` |
| `AC-IC-04-6` | Given 一筆存在的議題 When 執行 `export --id <ID>` Then `items` 恰一筆且含 `raw`（標籤為帳本表頭或 §5.1 所列中文）與 `timeline`（`seq` 升冪、`action` 為 §4.5 中文）；清單項目不含這兩鍵，也不含 `priority` 欄；單筆回應沒有 `legend`、`summary` |
| `AC-IC-04-7` | Given 一筆提案的卡面可建、另一筆不可建（`card.build` 拋 `CardError`）When 建議題 Then 前者 `title`＝卡面〈一、症狀〉；後者 `title`＝「（提案 <ID>：卡面量不到）」並列 `ne`（`CARD-UNAVAILABLE`），其他議題照常 |
| `AC-IC-04-8` | Given 觀察帳本與缺陷主檔各一列、一筆提案 When 建議題 Then `origin.line` 為該列在檔內的 1 起算行號、提案的 `origin.seq`＝`prop` 事件的 `created_seq`，`origin.file` 為 repo 相對路徑（POSIX 分隔） |
| `AC-IC-04-9` | Given 夾具含欄數不符的觀察列（`ledger.Row.nine` 為假）、ID 欄不合 `OBS-SI-NNN` 的觀察列、欄數不符的缺陷列（`DefRow.arity_ok` 為假）、重複 ID 的觀察列與缺陷列 When 建議題 Then 前三者不成議題並各計一筆 `ROW-ARITY`，重複 ID 的後列不收並計 `ID-DUP`，其餘議題照常、匯出 rc 0；`problems` 與 `ne` 是整本帳一份，每頁相同、不受 `since`、`limit`、篩選影響 |
| `AC-IC-04-10` | Given 七狀態各一議題，另含提案 `proposed`、`verified`、復發待回滾的 `closed` 與分類 `decision` 的 `open` 觀察列 When 建議題 Then `rankable` 只有待您決定、待解、進行中為真；`action` 為待您決定的提案（含復發待回滾者）＝`decide-proposal`、待您決定的觀察＝`close-observation`、其餘 `null`；未歸類議題 `rankable`＝false、`action`＝`null` |
| `AC-IC-04-11` | Given 夾具使 §5.1 引用鍵所列各動作（`attr*`、`prop`、`obs.*`、`card`、`dec`、`heldout.freeze`、`app.*`、`mea.*`、`run.open`／`run.close`）與 `dec` 的各決定動詞（`resume` 除外）各見於某議題時間線 When 取 `export --id` Then 這些 `action` 全為 §4.5 中文、`dec` 顯示為「決定：<動詞中文>」、`seq` 升冪；`research.*`、`resume` 不掛在任何議題上，只受 AC-IC-01-7 字典鎖；表外動作或動詞（以 AC-IC-01-2 的注入縫構造，不要求單一議題涵蓋全部 `events.KINDS`／`events.DKINDS`）顯示「未歸類：<原值>」並計 `UNMAPPED` |
| **FR-IC-05** | **排序、分頁、篩選、摘要（§5.3、§5.4）** |
| `AC-IC-05-1` | Given 同一張範例表（含相同與不同順位、嚴重度、日期、無順位者、`null` 嚴重度、`null` 日期、非 `rankable` 卻有遺留順位者）When 在 `issues.py` 顯示序（無順位）與 `lib/domain/issues.ts`（含順位）各排一次 Then 待處理依 §5.3 第一條、已完成依第二條（`null` 日期排最後；非 `rankable` 的順位不參與排序），兩端對無順位的子集結果相同 |
| `AC-IC-05-2` | Given 議題數大於 `limit` When 以 `next_since` 迴圈取頁（console-api 為 `nextSince`）Then 全部取回、無重複無遺漏、最後一頁 `truncated`＝false 且 `next_since`＝`null`；`--limit` 為 0 或超過 `export_limit_max`、`--since` 為負＝rc 3 |
| `AC-IC-05-3` | Given 取第一頁後帳本新增一列觀察、一列缺陷（其 DEF 號的族數小於已見項）與一列提案 When 以舊 `next_since` 續取 Then 已見項不重現、未見項不遺漏、游標較大的新項出現 |
| `AC-IC-05-4` | Given 夾具含各狀態議題 When 以 `--status 待處理` 查 Then 等於待解、進行中、觀察中的聯集；`--status 待您決定,延後` 為聯集；`--source 研究提案`；兩旗標並用取交集；未知值（stderr 列出合法值）、`--id` 併 `--status`／`--source`、`--status`／`--source` 配非 `issues` 的 kind 皆 rc 3；篩選先於分頁 |
| `AC-IC-05-5` | Given 任何篩選、`since`、`limit` When 讀 `summary` Then `byStatus`、`byTab` 恆為整本帳計數；`total`＝七狀態件數加 `unmapped` |
| `AC-IC-05-6` | Given 含全形字元的夾具 When 以文字表渲染（無 `--json`）Then 狀態、結果、來源、嚴重度、下一步皆為中文（標題與 ID 除外）、欄依顯示寬度對齊（全形算 2）、末行件數與問題數正確；被截斷時末行加「尚有更多，--since <next_since>」 |
| `AC-IC-05-7` | Given 全部分頁含待您決定與其他狀態的列 When 顯示 Then 待您決定的列全部置頂（先於其他列、帶置頂標記元素 `data-testid="issue-top-pinned"`＋`aria-label="置頂"`，其內依 §5.3 第一條），其餘依第二條且沒有該元素；待您決定分頁內每列同樣帶該元素；置頂只改顯示序，不改 `summary` |
| **FR-IC-06** | **零寫入與單一真相** |
| `AC-IC-06-1` | Given 乾淨工作樹 When 各跑一次 `issues`、`export --kind issues`（含 `--id` 與篩選）、Bridge GET、console-api GET Then 前後 `git status --porcelain` 相同、四類帳本與提案目錄位元組不變、不讀不寫家目錄 |
| `AC-IC-06-2` | Given 同一帳本快照 When 比對 `issues --json` 與 `export --kind issues` Then `items`、`legend`、`summary` 逐值相同；靜態鎖只掃新檔（`tools/lib/selfimproving/issues.py`、`components/domain/issues/**`、`lib/domain/issues.ts`、`Issue*.java`；`issuemap.py` 與既有檔除外）：任一檔不得含 ≥ 4 個不同的 `issuemap` 狀態鍵（詞表現讀其鍵集合、測試不另抄；判準＝新檔不得自持狀態詞清單，只能取 `legend`／`issuemap`），掃描器自帶負控樣本 |
| `AC-IC-06-3` | Given 功能完成 When 比對 `selfimproving.py --help` 與 `CAPABILITY` Then 動詞只比功能前多 `issues`，`issues.py`、`issuemap.py` 登記為 `ro` 且通過能力判準（無寫檔、無網路、無子行程） |
| `AC-IC-06-4` | Given 功能完成 When 跑 `si check` Then rc 與功能前相同、`params.json` 位元組不變 |
| `AC-IC-06-5` | Given 缺陷帳本歸檔檔含欄數不符與重複 ID 的列（夾具）When 建議題 Then 只讀缺陷主檔與兩條姊妹軌，歸檔檔的列不成議題、不進 `problems`（以檔案讀取紀錄判定未被開啟）；觀察帳本的 `…_archive*.md`（夾具）則照常讀，其已結列成議題 |
| **FR-IC-07** | **Bridge 與 console-api 傳遞（§6.3、§6.4）** |
| `AC-IC-07-1` | Given Bridge 在線 When 呼叫 `GET /si/issues` 與 `GET /si/issues/{id}` Then 每請求恰一次子行程（無快取）、200 本文與同參數的根層 `export --kind issues` 輸出逐值相同（差分測試，`generated_at` 除外）；其他方法 405；清單類未知查詢參數與單筆任何查詢參數＝422 `invalid_request`；`{id}` 格式不符 422；合法而查無 404 `si_not_found` |
| `AC-IC-07-2` | Given `status` 或 `source` 值以 `-` 起頭、超過 64 字元或含控制字元（例 `%00`、`%0A`）When 呼叫 Bridge Then 422 且不啟動子行程（不是 500）；Given 中文 `status`、含空白的 `source` When 由 console-api 經 Bridge 以 `--status=<值>` 單一 argv 到 CLI 端到端呼叫 Then 不亂碼、不回 500（Windows 與 Linux 皆測） |
| `AC-IC-07-3` | Given 根層 CLI 回 rc 非 0（例：未知 `status` 值）When 經 Bridge 呼叫 Then Bridge 503 `si_unavailable`（`cause`＝`nonzero_rc`、`detail` 逐字），console-api 同樣 503 且沒有 `data` |
| `AC-IC-07-4` | Given VIEWER 的 JWT When `GET /api/v1/issues` Then 200、鍵為 camelCase、值不動、每筆帶 `priority`、`priorityNote`（`rankable` 為真且有列才有值，其餘 `null`）；無 JWT＝401；`since`<0 或 `limit`<1＝400 且不觸及 Bridge |
| `AC-IC-07-5` | Given 一筆存在的議題 When `GET /api/v1/issues/{id}` Then 含 `raw`、`timeline`、`links` 與 priority；查無＝404 `si_not_found`（訊息「查無此議題」）；格式不合＝422 |
| `AC-IC-07-6` | Given 結構鎖 When 檢查 `AgentBridge` Then `si` 起頭方法仍恰五個、`siExport` 參數型別為六個（既有四個加兩個 String），`SiController` 的 GET 與 POST 數不變，`SiReadOnlyArchTest` 同步修改並保留原意 |
| `AC-IC-07-7` | Given Bridge 不可用、逾時，或優先順序表讀取失敗 When `GET /api/v1/issues` Then 非 2xx 且本文沒有 `data`（不回空表、不回缺 priority 的清單） |
| `AC-IC-07-8` | （審查核對項，不列單元測試）Given 本功能的完整變更清單 When 主控或 QA 以 `git diff --name-only` 核對 Then 不含 `reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md`（`issue_not_rankable` 等 issue 類 reason 只落在 `ISSUE_REASONS`、`ErrorReasons` 與新契約檔，鎖見 AC-IC-07-9） |
| `AC-IC-07-9` | Given 前端 `ISSUE_REASONS`（`lib/domain/issues.ts`）、後端 `ErrorReasons` 的 issue 類常數（例 `ISSUE_NOT_RANKABLE`＝`issue_not_rankable`）與 `API_Contract_IssueCenter.md` 的 reason 表（只列 issue 類的新 reason，既有 reason 仍歸 `API_Contract_P3-6.md` 附錄 B）When 比對（前端比照 `reasons.test.ts`；後端為 `IssueReasonsContractTest`，讀契約檔）Then 兩端各自與該表雙向相等（契約有而程式沒有＝紅、程式有而契約沒有＝紅），訊息逐字相同 |
| **FR-IC-08** | **畫面與中文（§7）** |
| `AC-IC-08-1` | Given 夾具涵蓋七狀態、八結果、四來源、四嚴重度 When 渲染 `/issues` 的清單、詳情、狀態說明 Then 可見文字（排除議題標題、ID、原列展開區、優先順序備註、延後列的原文節錄）不含 §4.2 機器值欄的英文詞（整詞比對，判準同 AC-IC-04-1）；原列展開區顯示原值且標籤為中文 |
| `AC-IC-08-2` | Given 清單頁 When 按「狀態說明」Then 彈出的表由 `legend` 渲染（七狀態、八結果、四來源、四嚴重度各一行），前端沒有第二份說明文字；日期為「最後已知動靜」的註記同在其中 |
| `AC-IC-08-3` | Given 夾具 When 開頁 Then 預設分頁＝待處理；四分頁各以 §7 的 `status` 值向 API 取資料（前端不持有狀態成員清單）；摘要列三個數字＝`summary.byTab`（待處理、待您決定、已完成〔現存帳本內〕，沒有「本週完成」）；待處理分頁上方有嚴重度計件條（細節見 AC-IC-08-9） |
| `AC-IC-08-4` | Given 清單 When 檢視 Then 固定八欄（編號、來源、標題、嚴重度、狀態、優先順序、最後更新、下一步）；點編號開詳情（原列、時間線、關聯）；關聯 ID 可點，查無時顯示「不在議題中心（可能已歸檔）」 |
| `AC-IC-08-5` | Given Bridge 503 或 504 When 開頁 Then 整片顯示原因（`cause`、`detail` 逐字）、摘要列三個數字顯示「—」，不顯示「0 件」或空表；Given 某帳本讀不到（`ne` 含 `*-LEDGER-UNAVAILABLE`，`summary.byTab` 對應格為 `null`）When 開頁 Then 該格顯示「—」（不顯示 0）、其餘格與清單照常，提示條（說明取自 `legend`）明說哪一本讀不到；`ne` 或 `problems` 非空時一律顯示提示條但清單照常 |
| `AC-IC-08-6` | Given `truncated` 為 true When 開分頁 Then 自動載完（沿 `SI_AUTO_LOAD_MAX_PAGES`）；到上限仍有未載入者＝明說「結果不完整」並顯示已載入件數 |
| `AC-IC-08-7` | Given 帳本文字或優先順序備註含 `<script>`、`**`、反引號 When 渲染 Then 一律以純文字顯示（不執行、不成元素、不渲染 markdown）；`components/domain/issues/**` 的靜態掃描無 `dangerouslySetInnerHTML` 與 Markdown 渲染器（同 SI 頁的守衛） |
| `AC-IC-08-8` | Given 全部分頁 When 開啟 Then 七顆狀態 pill 快篩（文字取自 `legend`）加「未歸類」、來源下拉、關鍵字（編號與標題）；待您決定的列置頂（AC-IC-05-7）；分頁真的沒有議題時顯示「這個分頁目前沒有議題」（與「量不到」不同） |
| `AC-IC-08-9` | Given 待處理分頁有各嚴重度、嚴重度 `null`、嚴重度表外值的議題 When 檢視摘要列與計件條 Then 計件條六格（緊急、高、中、低、—、未歸類）加總＝待處理件數；點摘要列三個數字之一即切到對應分頁（待處理、待您決定、已完成） |
| `AC-IC-08-10` | Given 已完成分頁含各來源與八種結果的議題 When 依來源下拉、結果快篩（文字取自 `legend.results`）、關鍵字篩 Then 只顯示符合者且三者取交集；結果快篩的選項與 `legend.results` 一致；清掉篩選回到全部已完成議題 |
| `AC-IC-08-11` | Given 已完成與非已完成的議題各一 When 開詳情 Then 已完成者的日期旁註明「最後已知動靜」（文字取自 `legend.updatedAtNote`、不寫死），非已完成者不帶此註記；詳情頭部的日期＝該議題的 `updatedAt` |
| **FR-IC-09** | **優先順序（階段二，§6.4、§6.5）** |
| `AC-IC-09-1` | Given ADMIN（不在 `console.si.deciders` 名單：優先順序不是帳本決定，不要求該名單）、議題 `rankable`＝true When `PUT …/priority {"rank":2,"note":"先做"}` Then 200 回 `{id, rank:2, note:"先做", setBy:<帳號>, setAt}`、`console.issue_priority` 恰一列、之後 GET 帶 `priority`＝2、`priorityNote`＝"先做" |
| `AC-IC-09-2` | Given OPERATOR 或 VIEWER 的 JWT When PUT 或 DELETE Then 403 `ACCESS_DENIED`、表零寫入、Bridge 零呼叫、`console.audit_log` 留一列拒絕紀錄（`SecurityConfig` 的 ADMIN 規則置於通用規則之前，PUT 與 DELETE 各一條） |
| `AC-IC-09-3` | Given ADMIN When PUT 且 `rank` 為 `null`、缺鍵、0、-1、1.5、"a"、10000，或 `note` 超過 200 個 code point（含全形與表情符號各算 1，不是 UTF-16 單元）或含控制字元 Then 422 `invalid_request`、`violations` 一次全列、表零寫入、Bridge 零呼叫（`rank`＝null 不是清除）；邊界接受：`rank`＝1 與 9999、`note` 缺省（存成空字串）、恰 200 個 code point 的 `note`（含表情符號）皆 200 |
| `AC-IC-09-4` | Given 已有順位 When `DELETE …/priority` Then 204、該列被刪、GET 回 `priority`＝`null`；再送一次仍 204（冪等）；全程不呼叫 Bridge；對已完成或已不存在的議題同樣清得掉遺留順位 |
| `AC-IC-09-5` | Given 議題狀態為已完成、延後、候選或觀察中 When PUT `rank`＝1 Then 409 `issue_not_rankable` 零寫入；查無議題 404 `si_not_found`；Bridge 失敗（503 `si_unavailable`、502、504，同 SI 唯讀端點）且零寫入 |
| `AC-IC-09-6` | Given 已設定順位 When 重啟 backend 與資料庫容器 Then GET 仍回同值；Flyway V14 在既有資料庫升級成功、`ddl-auto=validate` 通過；`issue_id` 格式不合、`rank` 為 0 或 10000 或 NULL、`note` 為 NULL 的 INSERT 皆被 CHECK 或 NOT NULL 拒絕 |
| `AC-IC-09-7` | Given 兩個 ADMIN When 先後 PUT 同一議題 Then 後者生效、`setBy` 與 `setAt` 為後者 |
| `AC-IC-09-8` | Given 任一 PUT 或 DELETE When 比對前後 Then 四類帳本與提案目錄位元組不變、Bridge 只被呼叫 GET；順位表的寫入敘述恰兩條（UPSERT 與 DELETE，另有唯讀 SELECT），只有一個 persistence adapter 觸及該表，`IssueController` 恰一個 `@PutMapping` 與一個 `@DeleteMapping`（ArchUnit，比照 `SiReadOnlyArchTest` 的 AT-950-8-2） |
| `AC-IC-09-9` | Given 非 ADMIN 或 ADMIN When 開頁 Then 非 ADMIN 看得到順位與備註但沒有編輯控制項、網路層無 PUT 與 DELETE；ADMIN 只對 `rankable` 的列有「排序」鈕（對話框：順位、備註、儲存＝PUT、清除＝DELETE）；儲存後以回應為準重排，不做樂觀更新；順位欄只對 `rankable` 的列顯示 |
| `AC-IC-09-10` | Given 議題曾有順位、後來狀態變成已完成（遺留列仍在表中）When `GET /api/v1/issues` Then 該議題 `priority`、`priorityNote`＝`null` 且不參與排序；PUT 它＝409 `issue_not_rankable`；ADMIN `DELETE …/priority` 204 後表中該列消失 |
| `AC-IC-09-11` | Given ADMIN 成功 PUT、DELETE 各一次 When 查 `console.audit_log` Then 各多一列（subject＝操作者、method、path 含議題 ID、status 200／204）；被拒的 PUT、DELETE 見 AC-IC-09-2 |
| **FR-IC-10** | **待您決定按鈕（階段二，§7）** |
| `AC-IC-10-1` | Given ADMIN 在待您決定分頁看到提案列（`action`＝`decide-proposal`）When 按「決定」Then 先以 `getSiProposal(id)` 取點擊當下快照、開 `SiDecideDialog`（`target={{ kind: "prop", proposal }}`，綁該快照 digest；`closed` 提案的動詞只有「回滾」），送出走既有 `POST /api/v1/si/proposals/{id}/decide` |
| `AC-IC-10-2` | Given 待您決定的觀察列（`action`＝`close-observation`）When 按「關閉並裁決」Then 開 `SiObsCloseDialog`（`target={{ obsId }}`），送出走既有關閉端點 |
| `AC-IC-10-3` | Given 原始碼 When 靜態掃描 `components/domain/issues/`、`lib/domain/issues.ts` 與後端 `Issue*` 類別 Then 沒有對 `/si/` 寫入端點的直接呼叫，也沒有 `si decide`、`obs-close` 字樣；議題中心唯一的寫入是 PUT 優先順序與上述兩個既有對話框 |
| `AC-IC-10-4` | Given 簽章成功但尚未入帳 When 重新整理 Then 該列仍在待您決定（狀態只跟帳本走，不做樂觀更新）；入帳後下次載入才移到新狀態 |
| `AC-IC-10-5` | Given 非 ADMIN 登入 When 開待您決定分頁 Then 待您決定列顯示「需要 ADMIN 角色才能操作」且沒有按鈕；網路層零寫入請求 |
| **FR-IC-11** | **導覽接入（§6.6）** |
| `AC-IC-11-1` | Given `NAV_REGISTRY` When 讀取登記表 Then 恰八項，id 依陣列序 `dashboard`、`projects`、`import`、`execute`、`monitor`、`settings`、`self-improving`、`issues`；`issues`＝label「議題中心」、order 55、href `/issues`、mobile false、roles 缺、enabled true；原七列（含 `self-improving` 的 label「自我進化」、order 70）各欄與陣列位置全不變；`visibleNavEntries` 的顯示序為 `monitor`、`issues`、`settings`、`self-improving`；mobile 為 true 的項數仍為 6 |
| `AC-IC-11-2` | Given `registry.test.ts` 與 `ToolsRegion.test.tsx` When 本功能落地 Then 只改 §9 所列釘值（`AT_932_6_1`、`AT_950_10_E_1` 兩處改八列並各保留原意；`ToolsRegion.test.tsx` 的連結數與預期序改八項、示範項不再與議題中心同為 order 55），不刪斷言；其餘導覽測試原樣通過 |
| `AC-IC-11-3` | Given 登記表 When 檢查 Then `issues` 的 href 對應存在的 `app/issues/page.tsx`；`match` 對 `/issues`、`/issues/x` 只命中本項（`registry.test.ts` 的 `PATHS` 補這兩列）、對 `/self-improving` 不命中；`ToolsRegion.tsx` 原始碼未改 |
| **FR-IC-12** | **非功能（§10）** |
| `AC-IC-12-1` | Given 真帳本現況（觀察約 300 列、缺陷主檔約 300 列、事件約 30 行）When 連跑 5 次 `export --kind issues` Then 每次 ≤ 2 秒（含 Python 啟動）、單頁輸出 ≤ 1 MB；另以合成夾具（觀察 5,000 列、缺陷主檔 2,000 列、事件 500 行）同樣 ≤ 2 秒 |
| `AC-IC-12-2` | Given Windows 與 macOS（或 Linux）When 跑 `issues --status 待處理 --json` Then stdout 為 UTF-8 位元組（無 BOM、LF 行尾）、rc 0；中文 argv 兩平台一致 |
| `AC-IC-12-3` | Given 兩次 GET 之間帳本變動 When 第二次請求 Then 反映新內容（Bridge 與 backend 不快取；前端進頁與按重新整理都重取） |
| `AC-IC-12-4` | Given 本功能完成 When 跑既有的 SelfImproving 根層測試、Bridge `test_si_*`、backend `Si*` 測試與前端 `si` 目錄測試 Then 除 §9「需同步改的既有鎖」所列釘值外全部原樣通過；既有測試檔的 `git diff` 只含 §9 所列檔、只動釘值與預期清單、不刪斷言 |
| `AC-IC-12-5` | Given `/issues` When 只用鍵盤操作 Then 分頁（`PillTabs`）可切換、清單列可開詳情、ADMIN 可開排序對話框與決定對話框並以 Esc 關閉、焦點回到觸發鈕；分頁、對話框與按鈕帶 aria 標籤（沿用既有元件，不自刻；e2e 以鍵盤走完一輪） |

## 9. 模組落點表（依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

議題中心是 SelfImproving 三類帳本之上的**唯讀投影**，共用 `fold`、`rows`、`defs`，故新檔放進既有套件、不另開套件；新檔皆能力類別 `ro`。「需同步改的既有鎖」欄逐檔逐行列出會因本功能而紅的既有釘值（2026-10-27 於 HEAD `de3f548d` 工作樹以釘值普查，測試檔內容與 `7cb4d60d` 相同：`toHaveLength(`、`hasSize(`、`isEqualTo(`、`len(_HELP)`、`CAPABILITY`、路徑與操作計數、Flyway 版本清單、ArchUnit 簽章鎖）；行號為該次現況，TCS 階段重核；每處都是同 commit 的可見上修，不刪斷言。

| 件 | 落點 | 職責（一句） | 測試（新增） | 需同步改的既有鎖（逐檔逐行） |
|---|---|---|---|---|
| 對照表（唯一真相源） | `tools/lib/selfimproving/issuemap.py` | 七狀態、八結果、四來源、四嚴重度、事件動作、決定動詞、通道、`problems` 碼、`ne` 理由的封閉詞彙與機器值→中文歸類；未知值回 `None`，由呼叫端 fail-loud | `tools/tests/test_selfimproving_issuemap.py`（AC-IC-01） | — |
| 聚合 | `tools/lib/selfimproving/issues.py` | 讀三類帳本→議題物件：來源判定、候選規則、下一步、links、時間線、游標、legend／summary、篩選、頁內顯示序、文字表 | `tools/tests/test_selfimproving_issues.py`（AC-IC-02～06、12） | — |
| 既有檔小改（根層） | `tools/lib/selfimproving/export.py`、`defs.py`、`tools/selfimproving.py` | `KINDS` 加 `issues`、`build` 加篩選參數；`DefRow` 增 `lineno`、`arity_ok`（有預設值，既有呼叫端不變）；入口加 `issues` 動詞與兩旗標（薄殼不含判準） | 既有 `test_selfimproving_export_status.py` 擴充 | `tools/selfimproving.py:6`（檔頭「共 23 個」→24），`_HELP`、`_HANDLERS` 同步 |
| 根層既有鎖 | `tools/tests/test_selfimproving_p3_meta.py`、`test_selfimproving_capability.py`、`test_selfimproving_console_obs.py` | `CAPABILITY` 登記兩支新模組為 `ro`；動詞數與登記數上修 | — | `p3_meta:293`（`len(_HELP)` 23→24）、`:294-298`（`CAPABILITY` 47／48→49／50，分項 `(35／36,8,2,2)`→`(37／38,8,2,2)`）；`capability:4`（檔頭「48 個鍵：36 `ro`」）、`:410`（48→50）、`:647-648`（同兩組分項）；`console_obs:921`（動詞集合 23→24） |
| Engine Bridge | `AgentConsole/engine-bridge/app/routers/si.py`、`app/si_cli.py` | 兩個 GET 路由、`SI_KINDS` 加 `issues`、argv 組裝（`--status=<值>`、`--source=<值>`）、`status`／`source` 輸入驗證 | 擴充 `tests/test_si_routes.py`、`test_si_cli.py`、`test_si_export_differential.py`（差分＝Bridge 回應對根層 CLI 輸出） | 見下兩列 |
| Bridge 既有鎖 | `AgentConsole/engine-bridge/tests/` | 釘值與組合表納入 `issues` | — | `test_si_cli.py:367`（`SI_KINDS` 釘值加 `"issues"`）、`:329-336`（argv 組合加 `issues` 與兩旗標）；`test_si_readonly_lock.py:66-68`（`KINDS`、`FLAG_COMBOS`）、`:475`（組合總數隨之驗）；`test_si_routes.py:24、41、58`（路徑表與 405 矩陣只增不改，補兩條新路徑案） |
| Bridge 測試輔助與黃金檔 | `tests/si_repo_support.py`、`tests/fake_si.py`、`tests/si_golden_regen.py` | `KINDS` 取自 `si_cli.SI_KINDS`（自動含 `issues`）；假 CLI 的旗標解析要認得 `--status=`、`--source=`；黃金檔鏈納入 `issues`（A、B 兩態，三份副本同步重產） | — | `si_repo_support.py:78、365`、`fake_si.py:46-51`；`test_si_export_differential.py:165`（子集比對）、`:189`（黃金檔數 4＋4＋2 不變） |
| console-api（新增） | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下：`adapter/in/web/IssueController.java`、`application/service/IssueQueryService.java`、`IssuePriorityService.java`、`application/port/{in,out}/Issue*`、`domain/model/issue/` | 轉遞 Bridge 物件並合併 priority；順位寫入與驗證序 | `IssueApiIT`（含假 Bridge `minibridge.MiniBridge` 加兩個 `/si/issues` 路由）、`IssueReasonsContractTest`（AC-IC-07-9） | — |
| 資料庫 | `adapter/out/persistence/IssuePriorityAdapter.java`（JDBC）；`src/main/resources/db/migration/V14__issue_priority.sql` | 順位表的 UPSERT／DELETE／讀取；V14 建表 | `IssuePriorityArchTest`（AC-IC-09-8） | `backend/src/test/java/com/aisdlc/console/infrastructure/persistence/`：`SchemaMigrationIT.java:68`、`SiConsoleWritesMigrationIT.java:129`、`V5UpgradeMigrationIT.java:135`（版本清單「1」～「13」補「14」） |
| console-api（既有檔小改） | 同目錄下：`AgentBridge.java`、`BridgeHttpAdapter.java`、`SiMirrorQueryService.java:69`、`SiReconcileService.java:158`、`SecurityConfig.java`、`ErrorReasons.java` | `siExport` 簽章增 `status`、`source`（兩個呼叫端補 `null`）、查詢值 percent-encode、ADMIN 專屬 PUT／DELETE 規則、新 reason | `SiMirrorApiIT` 照跑 | 見下列 |
| console-api 既有鎖 | `backend/src/test/java/com/aisdlc/console/` 下 | 簽章與計數釘值上修 | — | `architecture/SiReadOnlyArchTest.java:100-101`（`siExport` 參數型別 4→6）；`adapter/out/bridge/BridgeHttpAdapterSiTest.java:116、117、144、152、184、265`（四參數呼叫補兩個 `null`）；`infrastructure/config/OpenApiIT.java:130、154`（路徑 71→74，`EXPECTED` 加三路徑）、`:138`（操作 81→85）、`:32` 註解 |
| frontend | `AgentConsole/frontend/`：`app/issues/page.tsx`；`components/domain/issues/`（`IssuesView`、`IssueTable`、`IssueDetail`、`IssueLegend`、`IssuePriorityDialog`）；`lib/domain/issues.ts`；`lib/api/{endpoints,queries,types}.ts` | 畫面與純函式；按鈕只開既有 `SiDecideDialog`、`SiObsCloseDialog` | 同目錄 `*.test.tsx`、`lib/domain/issues.test.ts`、新靜態鎖（AC-IC-08-7、10-3，比照 `si.static.test.ts`） | 見下三列 |
| frontend 既有鎖（導覽登記表） | `lib/nav/registry.ts`、`lib/nav/registry.test.ts` | 登記表七項增為八項（`issues` 在陣列末尾，`self-improving` 的 label、order、索引不變） | — | `registry.test.ts:16-37`（`PATHS` 補 `/issues`、`/issues/x`）、`:100-106`（`AT_932_6_1` 長度與四張清單補第八項）、`:120`（icon 互異 7→8）、`:136`（字串 href 清單補 `/issues`）、`:350-361`（`AT_950_10_E_1`） |
| frontend 既有鎖（導覽列元件） | `components/layout/ToolsRegion.test.tsx` | 連結數與預期序改八項 | — | `:77、80、82、85-93`（示範項與議題中心同為 order 55：預期序與 `links[5]` 索引改）、`:114`（`original` 補議題中心）、`:146`、`:155`（7→8）、`:160`（`max-md:hidden` 判準加議題中心） |
| frontend 既有鎖（API） | `lib/api/endpoints.test.ts`、`lib/api/si.endpoints.test.ts` | `endpoints.ts` 增四個函式；不動 `reasons.ts` | — | `endpoints.test.ts:187、190`（總數 79→83，`EXPECTED` 加四列）；元鎖 `si.endpoints.test.ts:43-46`（釘值字串 79→83、標題同步）；`:34-41` 的 `Si` 前綴鎖不受影響（新函式不以 `Si` 起頭） |
| 文件（規格） | 本檔（01）；`docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（03，階段一＋二合訂一份，兩把 SDD 鍵共用）；`AgentConsole/docs/02_architecture/API_Contract_IssueCenter.md`（02，TCS 階段產出） | 契約檔承載 Bridge 兩路由、console-api 四端點、`console.issue_priority` 資料所有權與 reason 表（`ISSUE_REASONS` 與它雙向鎖）；不改 `Architecture.md` 與 `reasons.ts` | — | `reasons.test.ts` 對 `API_Contract_P3-6.md` 附錄 B 的雙向鎖不受影響（那兩檔不動） |
| 文件（過程） | RTM 回填 `AgentConsole/docs/06_quality/RTM.md` 本地子表一列；`AgentConsole/engine-bridge/README.md` | 審查報告與 RTM 屬 SDD 流程過程紀錄（06），不是規格 | — | — |

- **已複核不需改**：`si-login-gate.test.tsx:66`（「自我進化」label 不改名）、`ToolsRegion.test.tsx:139、165-167`（只取登記表前七項或只斷言既有項）、`layout.test.tsx:135-137`（逐登記表項斷言、不釘數字）、E2E 的導覽斷言（`shells-and-layout.spec.ts:26-41`、`p9-w7-ui.spec.ts:180-206` 逐名點選、不計項數；TCS 階段以真跑複核）；新增前端檔須遵守 `tests/design-rules.test.ts` 的靜態規則。
- **連動面（同一個 commit 收齊，根 `CLAUDE.md` 第 5 條）**：`test_selfimproving_capability.py` 的 `CAPABILITY` 登記兩支新模組為 `ro`；`Root_Layout_and_Module_Placement.md` §3 的 SelfImproving 列加兩支檔名與測試檔（建檔後加反引號納入落點鎖 `test_root_module_layout.py`）；`selfimproving.py` 的 `_HELP`、`_HANDLERS` 與檔頭動詞計數同步；上表第五欄的既有鎖同 commit 上修。
- **不需新增**：compat-ci `paths`（已涵蓋 `tools/lib/selfimproving/**` 與 `tools/selfimproving.py`）、`non_evolvable_globs`（同樣已涵蓋二者）、`params.json` 新鍵（常數住程式碼）。**需補**：compat-ci `paths`（`windows-compat-ci.yml`、`macos-compat-ci.yml`）加本 PRD、TCS、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md`（缺陷主檔 `AutoSDD_Defect_Log.md` 已在；精確清單以 `test_ci_paths_cover_root_consumers.py` 為準）。
- 根層新增測試檔以 2 支為上限（每支新增都付護欄層棘輪重釘稅，見落點規範 §2 測試列）；重釘由收尾單人窗口做（鐵律七）。本功能不動 `.claude/hooks/**`、`settings*.json` 與守衛面清單檔，不新增守衛碼。
- **待 TCS 階段核對**：游標編碼、`DefRow.lineno`／`arity_ok`、`closed` 提案「從未有過 `dec(rollback)`」與「已被消耗的 `app.rollback`」的取得方式（`fold` 目前只留 `pending_rollbacks` 計數；可由事件重數 `dec(rollback)` 筆數並對照 `Prop.pending_rollbacks` 推得，不改 `fold.py`）、姊妹軌表頭解析與行號、compat-ci `paths` 的精確清單、`ListChecks` 圖示存在且與其他七項互異、上表既有鎖的行號與值重核。

## 10. 非功能需求

- **唯讀與零帳本寫入**：根層與 Bridge 不寫任何檔；Console 唯一的寫入是優先順序表（§6.5），不碰帳本。**不快取**：Bridge 與 backend 每請求重算，帳本是唯一真相源。
- **效能**：`export --kind issues` 對真帳本現況單次 ≤ 2 秒（本機實測既有 `export` 同量級為 0.14～0.32 秒）；單頁 ≤ `export_limit_max`（500）項，清單項目不含 `raw`、`timeline`。
- **fail-loud**：表外值顯示「未歸類」並計 `problems`；量不到顯示「—」並列 `ne`；某本帳讀不到時，缺的那類議題由 `ne` 與提示條明說、其餘照常；Bridge、子行程等失敗不回空表或部分資料。
- **跨平台與語言**：Windows、macOS、Linux 皆可跑；中文 argv 與 stdout 以 UTF-8 位元組傳遞（沿 `_stdio_utf8`）；介面文字一律繁體中文。
- **相容**：`schema_rev` 維持 1；既有「自我進化」頁、`/si/*` 六個 GET、`/api/v1/si/*` 的七個 GET 與四個 POST 行為不變，既有測試除 §9 列出的鎖外不改。
- **安全**：寫入只限 ADMIN；查詢參數衛生（§6.3）；帳本文字純文字渲染。
- **可及性**：分頁、對話框與按鈕沿用既有元件（`PillTabs`、`Dialog`、`Button`）的鍵盤與 aria 行為，不自刻（AC-IC-12-5）。

## 11. 分階段與出口判準（症狀型）

| 階段 | 交付 | 出口 |
|---|---|---|
| 階段一（唯讀） | `issuemap.py`、`issues.py`、CLI `issues`、`export --kind issues`、Bridge 兩個 GET、console-api 兩個 GET、前端四分頁與狀態說明、導覽一列 | (a) 掌舵者在真機打開議題中心，不看任何英文就能答出「現在有幾件待處理、最嚴重的是哪件、有什麼等我決定」；(b) 對真帳本，`summary.byStatus` 與獨立算法（只用文字處理計各處置首詞與缺陷狀態首詞，不 import 本模組）逐項相等，且 `problems` 為空（非空則每筆都對得到帳本裡真實存在的異常列）（2026-10-26 參考值：總數 597＝待處理 2、待您決定 0、延後 51、已完成 544、其餘 0；凍結日重算，不以此為準）；(c) 帳本零寫入（git 對帳）；(d) AC-IC-01-1 雙向封閉鎖綠 |
| 階段二（優先順序與按鈕） | V14、PUT 優先順序、順位編輯、「待您決定」按鈕 | (a) 真機走完一次「排序→處理→完成」：排一件順位、對一件待您決定按鈕簽章、主機入帳、重新載入後該列移到新狀態；(b) 該次決定在稽核檔與事件帳本都查得到、沒有旁路；(c) 非 ADMIN 登入實測看得到、按不到、網路層零寫入；(d) 重啟 backend 後順位仍在 |
| 階段三（後續，不在本版） | 已完成歸檔報表：時間窗篩選、CSV／Markdown 匯出、30 天摘要、歸檔缺陷帳本納入（須先決定歷史異常列的處理） | 掌舵者用它回答「上個月完成了什麼」不需翻帳本 |

- **派工切分（鐵律七）**：根層一包（`tools/**`、根層測試與連動面鎖）、Bridge 加 console-api 一包（契約、V14、安全層）、前端一包；根層先、Console 後（Console 消費 §5、§6 的匯出形狀）。SDD 鍵（BRIDGE §8，一功能一鍵）：`monorepo-issue-center`（根層）、`agentconsole-issue-center`（Console）；兩把鍵的 `spec-frozen` 都凍結同一份 PRD（本檔）與同一份 TCS（根層 `docs/03_testing/contracts/TCS-IssueCenter-20261027.md`），Console 側不另起 TCS。

## 12. 不做

- 不改帳本任何一個位元；不改英文機器狀態；不新增機器狀態、帳本動作或決定動詞（`events.DKINDS`；沒有「成立」按鈕，`closed` 提案的「回滾」沿用既有動詞）；不新增守衛碼。
- **已知限制**：缺陷列的 ID 欄不合 `DEF-<族>-<序>` 者，`defs.load_rows`（與 `tools/check_defect_log_crossref.py` 同一列辨識判準）不認它為資料列而略過——不成議題、也不計 `problems`；本版不改 `load_rows`，日後要抓這類壞列須連同該腳本一併改（階段三再議）。
- **歸檔帳本不納入**（主控裁決 2026-10-26）：缺陷帳本只讀主帳本、外部阻塞軌與結構性長債軌，不讀 `AutoSDD_Defect_Log_archive_*.md`；理由＝歷史列格式不齊與重複 ID 會造成假待辦與常駐 `problems`；階段三再議。觀察帳本的 `…_archive*.md` 不在此列：主檔有體積上限（`ledger_fail_bytes`），歸檔是它的正常生命週期，不讀會讓已結觀察從議題中心消失；該類歸檔檔現況尚不存在，出現時依 §2 一併讀。
- 不做「本週完成」數字（頂端第三個數字為「已完成（現存帳本內）」）、時間窗篩選、CSV／Markdown 匯出：都需要帳本加結案時間欄，列入階段三。
- 不把運轉暫停（`suspended` 的 RUN）納入議題，仍由「自我進化」頁橫幅恢復；不改既有「自我進化」頁與其導覽列（label、order、mobile 皆不變），其內的狀態快篩 `obsStatusClass` 維持原樣、不與本表合併（合併留待另案）。
- 不做批次操作、拖曳排序、樂觀更新、通知推播；不存優先順序的歷史版本（只存目前值，變更軌跡在 `console.audit_log`）。

## 13. 變更記錄

- **v0.1**（2026-10-26，主控）：草案。
- **v1.0**（2026-10-26，SA）：補齊為可凍結版，對照表以真帳本逐值核對。與 v0.1 的實質差異：
  1. 補 v0.1 漏掉的觀察處置 `DEF-`、`proposed@`（真帳本共 14 列），並解掉「缺陷 `closed-by-decision` 同時掛延後與已完成」的衝突，改為唯一歸類；刪去無機器依據的「缺陷待 PM 裁決」；結果由七增為八（加已回滾）；嚴重度補 P0（併入緊急）。
  2. 改善類正式議題不再先到待您決定（既有 Console 對觀察列只有「關閉」、沒有「核准」），改為待解；刪「成立」按鈕（那是新帳本動作）。
  3. 歸檔缺陷帳本不納入（理由見 §2）；摘要列第三個數字由「本週完成」改為「已完成」（帳本沒有結案時間；其後稱「累計」，SCG-0 一審 F-09 再改為「現存帳本內」）。
  4. 清單與單筆分離（`raw`、`timeline` 只在單筆），新增 `legend`、`summary`、游標、`rankable`、`action`、伺服端 `status` 篩選與別名「待處理」，使前端不持有任何詞彙副本。
  5. 資料表 `rank`、`note` 改 NOT NULL；補 AC、模組落點的連動面與派工切分。
- **主控裁決 2026-10-26**（掌舵者授權代決）：
  1. 歸檔缺陷帳本本版不讀，只讀缺陷主帳本＋外部阻塞軌＋結構性長債軌（§2、§12）；觀察帳本的歸檔檔不在此列，理由見 §12。
  2. 改善類正式議題進待解、不新增「成立」動作；待您決定只收提案 `proposed`、`verified` 與分類 `decision` 的 `open` 觀察列（§3、§4.1）。（二審 N-3 增第四種，見 §3）
  3. 頂端第三個數字＝已完成；「本週完成」列階段三，需帳本加結案時間欄（§1、§7、§12）。（原稱「累計」，SCG-0 一審 F-09 改為「現存帳本內」。）
  4. 來源順位固定為使用者提案 > 系統缺陷 > 研究提案 > 系統改善，提案取任一來源項目命中的最前順位（§2；原表順位②③對調）。
  5. `mobile:false`、運轉暫停不納入議題、`rank`／`note` NOT NULL（§6.5、§6.6、§12）。
  6. 清除順位＝`DELETE /api/v1/issues/{id}/priority`（刪列，204）；`PUT` 的 `rank` 必填、null 為 422（§6.4）。
  7. fail-loud 顯示字樣統一為「未歸類：<原值>」，`problems` 一筆一值（§4.6）。
- **SCG-0 一審修訂 2026-10-27**（SA；主控裁決 F-01～F-30）：
  1. 對照與封閉鎖：嚴重度拆兩組鍵（觀察雙向鎖、缺陷子集鎖）、處置首詞改探針鎖、通道／`problems` 碼／`ne` 理由納入對照與雙向鎖並有中文、`closed` 且已消耗 `app.rollback`＝已回滾（§4.2～§4.6、§5.4）。
  2. fail-loud 補洞：帳本缺檔進 `ne`、事件不合格計 `EVENT-UNSOUND`／`EVENT-PARSE`、姊妹軌孤列仍成延後議題、`ROW-ARITY` 辨識法（§2、§4.6、§6.2）。
  3. 欄位與顯示：`links` 方向、`priority` 只對 `rankable`、置頂定義、計件條「未歸類」、80 個 code point 計法、nextStep 措辭與量測窗取法、游標改用行號、「已完成（現存帳本內）」（§5、§7）。
  4. 介面與鎖：`status`／`source` 控制字元 422、查詢值編碼理由、`ISSUE_REASONS` 與新契約檔、導覽不改名、§9 新增「需同步改的既有鎖（逐檔逐行）」欄並補姊妹軌與 Bridge 測試輔助檔（§6.3、§6.4、§6.6、§9）。
  5. AC：新增 12 條（01-7～01-9、04-10、04-11、05-7、07-8、08-9、08-10、09-10、09-11、12-5），共 85 條；其餘相關 AC 隨上列改寫。
- **SCG-0 二審修訂 2026-10-27**（SA；主控裁決 N-1～N-11、F-14／F-25／F-27／F-28 殘項、SA 取捨風險 2 與 5）：
  1. 對照與狀態：提案 `closed` 復發待回滾＝第四種待您決定成員，並補進行中的「已決定回滾」列（§3、§4.1、§4.2、§5.2）；`ROW-ARITY` 字樣與缺陷壞 ID 已知限制（§4.5、§12）；處置首詞加第一個捕捉群組內分支數斷言（§4.6）；新增 `SIBLING-LEDGER-UNAVAILABLE`、觀察帳本缺檔時提案來源與嚴重度為 `null`、`byTab` 為 `null` 顯示「—」（§4.5、§4.6、§5.4、§7）。
  2. AC：時間線 AC 不再宣稱單一議題涵蓋全部動作（04-11）、`updatedAt` 拆兩夾具（04-3）、`note` 以 code point 計與邊界接受（09-3）、置頂標記元素（05-7）、reason 鎖拆為審查核對項與雙向鎖（07-8、07-9）；新增 5 條（01-10、01-11、03-7、07-9、08-11），共 90 條。
  3. 其他：TCS 具名且兩把鍵共用（§9、§11）、§3 候選與「決定動詞」措辭、缺陷嚴重度舊口徑註記（§4.4）、延後列原文節錄可含英文（§4.1、§5.2）。
- **SCG-0 三審小修 2026-10-27**（SA；QA 三審 R3-01～R3-08，AC 總數不變）：交叉參照改 AC-IC-07-9（§6.4）；復發待回滾不回滾時無動詞可消去的限制寫入狀態說明與下一步（§4.1、§5.2）；分支數斷言改以第一個捕捉群組計（§4.6、AC-IC-01-1）；AC-IC-04-11 補表外 Then、AC-IC-01-9 定 subject；契約 reason 表只列 issue 類、後端讀契約檔測試 `IssueReasonsContractTest`（AC-IC-07-9、§9）；AC-IC-01-11 補對照例、AC-IC-01-5 釘註記字樣；§4.2 補「已決定回滾」進行中列與「量不到」列（AC-IC-01-3、03-7）。

## 附錄 A　給掌舵者的 30 秒操作說明（階段一與二完成後）

1. 左列點「議題中心」。頂端三個數字：待處理 N、待您決定 M、已完成 K（現存帳本內：缺陷帳本的歸檔檔不納入，日後帳本輪替歸檔時這個數字會變少，不是資料被改了）。
2. 要看「還有什麼沒做」：留在「待處理」；您排了順位的在最前面，其次依緊急程度，再依擺了多久。
3. 要做決定：點「待您決定」，每列有按鈕（需要 ADMIN 角色）；按下去會簽章並顯示「待入帳」，主機入帳後重新整理，該列會移到新的狀態。
4. 要排優先順序：在「待處理」或「待您決定」的列按「排序」，填 1（最先）與備註後儲存；按「清除」就回到未排。
5. 要查以前：點「已完成」，用來源、結果或關鍵字篩。「全部」可看到候選與延後的議題（待您決定的排在最前）。
6. 看不懂某個狀態或結果：按右上「狀態說明」。

---

## 勘誤（本檔 Stage-1 凍結之後的訂正；依 TCS〈凍結後修訂路由〉第 4 點，由 `monorepo-issue-center` 先 refreeze、`agentconsole-issue-center` 隨後；正文保留、讀者以本表覆蓋對應行）

### 勘誤一（2026-10-27；SCG-4 獨立審查一審 Q-09／⚖(a) 後）

| 條 | 位置 | 原文 | 訂正 | 理由（WHY） |
|---|---|---|---|---|
| P-1 | §9 模組落點表（「聚合」列之後） | 只有 `issuemap.py`、`issues.py` 兩支新檔 | 加一列：件＝「議題物件建構」；落點＝`tools/lib/selfimproving/issues_items.py`；職責＝`Ctx` 與議題物件建構函式（標題、下一步、links、時間線、游標等純函式；不讀檔、不呼叫 git／fold／card／status，注入縫仍全住 `issues.py`）；測試＝同 `tools/tests/test_selfimproving_issues.py`；同步鎖＝`CAPABILITY` 登記第三支 `ro` | 「聚合」一支實作後 641 行，超過 `tools/lib` guardrail_lib 分級 400 行上限，依 `AutoClaude/tools/check_loc_budget.py` 的分級處置（`:161`、`:263`「先拆職責／抽共用模組」）拆出；零寫入判準、AC、匯出形狀不變 |
| P-2 | §9「根層既有鎖」列（`p3_meta:294-298`、`capability:4`、`:410`、`:647-648`） | `CAPABILITY` 47／48→49／50，分項 `(37／38,8,2,2)`；檔頭「48 個鍵：36 `ro`」；`:410` 48→50；`:647-648` 同兩組分項 | 47／48→50／51，分項 `(38／39,8,2,2)`；檔頭改「51 個鍵：39 `ro`」；`:410` 48→51；`:647-648` 同兩組分項 →`(38／39,8,2,2)` | 同 P-1：多一個 `ro` 鍵。對應 TCS 勘誤一 1-1 |
| P-3 | AC-IC-07-8（§6 AC 表）；§9「文件（規格）」列（:404） | Then 不含 `reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md`；:404「不改 `Architecture.md` 與 `reasons.ts`」 | Then 不含 `reasons.ts`、`API_Contract_P3-6.md`，且 `Architecture.md` 的 §10 Bridge 契約節與 §11.1 reason 表一字不改；§7.2 資料所有權表由主控於發布階段加 `issue_priority` 一列（純文件連動，不由開發棒做）；:404 改「不改 `reasons.ts`；`Architecture.md` 只准主控在 §7.2 資料所有權表加 `issue_priority` 一列」 | 本 AC 的目的（括號）是 issue 類 reason 不進既有雙向鎖檔；Architecture §7 是資料所有權唯一真相源，新表 `console.issue_priority` 不登記＝架構文件失真。對應 TCS 勘誤一 1-6 |
