# PRD - SelfImproving（自我進化機制）模組
# Product Requirements Document - Universal Template

**文檔類型**: PRD (Product Requirements Document)
**模板版本**: v0.01 Universal（結構複製自 `AISDLC_SDD/AISDLC_SDD_v0.30/docs_template/core/prd/PRD_Universal_Template.md`；模板本體未改）
**適用情境**: Brownfield（必讀章節 1–8；可選 10、11；依任務書另填 12、13、14）
**適用平台**: 不適用（工作流與治理機制，無 UI 平台）。介面＝CLI 文字（§7）；跨平台＝Windows PowerShell 與 macOS（NFR-SI-06）
**上游需求**: 掌舵者 T1（2026-10-18）原文五點（§14）；T1 修訂（2026-10-19 20:21 +08:00，四問＋授權句，sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13；附錄 C.1、§14）；研究方法論 SOP `docs/05_development/SelfImproving_Research_Methodology_SOP.md`
**FSM 位置**: 鍵 `monorepo-selfimproving`、SPEC_DRAFTING（Stage-1；依任務書，本稿作者未跑 FSM CLI 查證）。本檔是 Stage-1 上位規格，FRD／TCS／SRD 於實作輪再產

## 📋 文檔元數據
| 項目 | 內容 |
|-----|------|
| **專案名稱** | SelfImproving（自我進化機制）模組 |
| **專案類型** | Brownfield |
| **目標平台** | 不適用（無 UI 平台；介面＝CLI 文字，見 §7）；跨平台＝Windows（PowerShell）與 macOS |
| **目標日期** | 無日曆日期（刻意；階段出口一律為症狀型判準，見 §8） |
| **文檔狀態** | Draft |
| **Product Owner** | 掌舵者 |
| **Stakeholders** | 掌舵者（唯一核准者）；主控 agent（Fable）；子代理（Sonnet／haiku）；AutoClaude 引擎；AISDLC_SDD FSM runtime；Console 操作者 |
| **撰寫日期** | 2026-10-19（掌舵者 T1 立案日仍為 2026-10-18） |
| **最後更新** | 2026-10-19（v0.9：Architect 棒技術定稿，見 §13.3） |
| **AISDLC 版本** | v0.30（LATEST；現查 `python AISDLC_SDD/scripts/sdd_version.py`） |

### 專案類型專屬欄位（Brownfield）
| 項目 | 內容 |
|-----|------|
| **既有系統名稱** | AutoSDD（AutoClaude 指揮官＋AISDLC_SDD 框架＋AgentConsole＋根整合層；monorepo 根 `AISDCL_Agent/`） |
| **現行版本** | AISDLC_SDD v0.30；其餘子專案版本一律現查各自 `CLAUDE.md`／`AISDLC_SDD/FRAMEWORK_STATUS.md`（本稿不寫死） |
| **目標版本** | 不適用（新增模組，非版本升級；框架改動走 LATEST 原地改，見根 `CLAUDE.md`〈路徑陷阱〉） |
| **系統文檔位置** | 根 `CLAUDE.md`、`AutoClaude/CLAUDE.md`、`AISDLC_SDD/CLAUDE.md`、`AgentConsole/CLAUDE.md` |
| **技術棧**（既有，非本 PRD 選型） | Python 3.11+（AutoClaude 引擎、SDD FSM runtime）；Next.js＋Spring Boot＋FastAPI（AgentConsole）；Claude Code harness（hooks／skills／auto memory） |

## 🎯 1. 專案願景與目標 (Vision & Objectives)
### 1.1 專案願景
讓 AutoSDD 對「同一類流程缺陷反覆發生」這件事，不再靠掌舵者與主控的記憶，而是由帳本驅動一條**有界、人工逐項核准、可一個動作回滾、以真實症狀驗收**的改進迴圈（觀察→歸因→提案→人工閘→沙盒套用→驗證→量測→退役）；全程不更新模型權重、不自動修改治理面。

**可被反證**：在**可評估窗**內——基線窗內確認再現事件數 ≥ `W_EVT`（初值 2，無先例、未校準；§1.3 M1）——迴圈採納若干改進後，若同一根因鍵下連續兩個可評估的採納窗都仍復發（M1：窗結果 `recurred`；「連續」的定義見 §1.3〈M1 判定細則〉(c)），或掌舵者讀 M5（含與不含 `unverified_ack` 兩值；只報值與 n、不機械判趨勢，〈M1 判定細則〉(e)）後認定採納後回滾比例隨採納數上升，本願景即被反證——不自動下線，改列為掌舵者 T1 決策項（縮減範圍或廢止）。基線窗事件數不足（含 0 事件）、或 M5 的已關閉採納窗數 < `W_MIN`＝NOT-EVALUABLE，既不算支持也不算反證，不得把基線 0 事件算成「未低於」或「已改善」；M1 的「未再現」因基線窗為事件所選（均值回歸）而不構成成效證明，只用於反證（§1.3 M1 檢定力說明）。

### 1.2 業務目標
**解決的問題**:
- **現況痛點**（座標皆寫稿時現查）:
  - 復發靠人記得：缺陷帳本以自由文字記「再開症狀」，復發連結沒有結構化欄（例：DEF-200-551 現象欄以文字寫「DEF-200-535 再開症狀於 116 命中」，`docs/06_quality/AutoSDD_Defect_Log.md` 寫稿時第 324 行）⇒ 復發率今天只能人工數。
  - 記憶面沒有結果標籤與退役機制：Claude Code 記憶索引 `MEMORY.md` 寫稿時為 22,755 bytes／113 行（記憶目錄共 125 個 .md 檔，含索引），逼近官方載入上限（S-08 稱「前 200 行或 25KB」；25KB 換算未查證）；2026-10-19 主控人工歸檔後降為 15,558 bytes／76 行（22,755→15,558 bytes、113→76 行；OBS-SI-016，PROP-SI-003 的手動先例；§9.0 Q5），歸檔是人手做的一次性動作、不是機制。另有 harness 自帶的容量機制（官方 memory 頁，S-08；SCG-0 一審 F-05 開頁複核，`docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md`）：Claude 寫入 `MEMORY.md` 後 harness 自行量測，近上限時提醒 Claude「一條一行、細節搬到主題檔、合併或丟棄過期條目」，超限時寫入仍成功但回錯誤要求重寫索引——它由不受本迴圈控制的寫入者（harness 內的 Claude）執行，不帶結果標籤、不經人工閘；SI 的容量事件（`CAP_FRAC`）與它並存而非取代，衝突處置見 AC-SI-27-1。
  - 引擎演化「只提案不套用」靠「舊 PlaybookRunner 沒有生產建構點」而非守衛（OBS-SI-010；`AutoClaude/CLAUDE.md:191`）。
  - 改進提案沒有獨立評估器：AutoClaude 演化提案與根整合層的改進迴圈皆無 held-out（SOP II-6 缺口欄）。
  - 提案沒有統一審閱介面與冷卻：被否決的同型提案可重複出現（SDD 規則面有 add↔retire 抖動防護 R-9.24，其他面無）。
- **目標用戶**: 掌舵者（主要）；主控與子代理（執行者）。
- **市場機會**: 不適用（Brownfield 內部模組；替代方案比較見 §4.2）。

**預期成果**（階段性、以症狀出口表達，無日曆；出口全文見 §8）:
- **短期＝P0＋P1**：任何視窗新增觀察時不需追問欄位；提案物件與提案卡可被掌舵者三句話判讀。
- **中期＝P2**：至少一筆真實提案走完「閘→沙盒→驗證→晉升或否決」，正式面零未經閘的變更。
- **長期＝P3**：M1～M5 可重跑量測；至少一個採納窗關閉並入帳；至少一筆退役走完人工閘。

### 1.3 成功指標 (Success Metrics)
只准症狀型結果指標。初值參數（W_N、W_MIN、W_EVT、W_OPP 等）皆標「初值（未校準）」，見 §5 開頭說明。基線未量測者一律寫 NOT-EVALUABLE，不得用估計值頂替。M2、M3 無因果連結而降為資訊欄（見表內說明），成功指標為 M1、M4、M5。

<!-- 機械消費：下表的 M1～M5 五個指標列，加上表後〈M1 判定細則〉（自該節標題行起至下一個四級標題前的全部非空行）須逐字出現在 docs/06_quality/SelfImproving_Protocol/metrics.md（tools/lib/selfimproving/params.py 的 metrics_problems；測試 tools/tests/test_selfimproving_check.py 的 test_AT_031_2_1_metrics_verbatim）；改動這些列或該節任一行須同步 metrics.md，並依指標定義變更程序處理（判準指紋、metrics_rev）。本行是註解、不在比對範圍。 -->
| 指標類型 | 具體指標 | 目標值 | 衡量時間點（事件，非日曆） | 量法與資料來源 |
|---------|---------|--------|---------------------------|----------------|
| **結果指標** | **M1 同根因缺陷復發率（per-PROP 前後對照）** | 可評估採納窗中，採納後仍復發的比例低於基線（可評估的基線窗依定義已含 ≥ `W_EVT` 次再現，即基線＝有再現）；同一根因鍵下連續兩個可評估採納窗皆仍復發＝願景被反證（§1.1；「連續」見〈M1 判定細則〉(c)）；不可評估＝NOT-EVALUABLE（不算支持、不算反證） | P2、P3 出口評估；每個採納量測窗關閉時 | M1＝可評估採納窗中「採納後仍復發」（窗結果 `recurred`）的窗數 ÷ 可評估採納窗數，並附 n。**基線窗**（前）＝同一 PROP 晉升前、同一機會列規則（AC-SI-23-1）、自再現標記上線後的最近 `W_OPP` 筆機會列（「再現標記上線」的錨與起算規則見下〈M1 判定細則〉）；**採納窗**（後）＝FR-SI-23 的窗。**可評估條件（NE 護欄量事件數、不量列數）**：基線窗內確認再現事件數 ≥ `W_EVT`（初值 2，無先例、未校準），且基線窗機會列數 ≥ `W_MIN`（初值 5，先例 `params.json` 的 `q1b_min_n`）；基線事件數＝0 一律 NE，不得算「未低於」或「已改善」。因再現而提早關閉的採納窗（`recurred`）照樣可評估——再現本身是決定性觀察，不設最小列數；`clean` 的窗必已累計 `W_OPP` 筆機會列、且關閉時窗內無未決候選（有則記 `pending`，不計 `clean`，AC-SI-23-1）；因回滾先到而關閉、窗內無確認再現者（`rolled-back`）M1 不評估（無再現觀察、窗被截短），仍計入 M5；之後若晚到的確認指向窗關閉前立案的再現列，該窗改判 `recurred`（`mea.amend`，AC-SI-23-1）。再現候選在立案當下寫入標記（`reopens`／現象欄 `reopens:DEF-xxx`），確認由審查者（≠立案者）以 `attr.confirm` 為準；量測腳本只讀已寫入的標記與確認事件，不在量測期掃描產生候選（AC-SI-06-2）。全域窗（最近 `W_N`〔初值 20，無先例〕筆首詞為 `fixed` 的 DEF／OBS 列內被確認再現者的比例）降為資訊欄，不得單獨宣稱成效。歷史基線結構性 NOT-EVALUABLE（OBS-SI-027：1,490 筆 fixed 列只有 34 列有 git 認得的 commit hex、`reopens:` 0 列；§9.0 Q6）：基線窗只計標記上線後的列、不回溯標註，並於首次 `app.promote` 前以前瞻窗記一筆基線報告（ADR-SI-05）；§1.1 反證條件自首個可評估採納窗關閉後才可評估。來源：`docs/06_quality/AutoSDD_Defect_Log.md`（含 `_archive_*`）、觀察帳本 |
| **資訊欄**（不作成功指標） | **M2 DEF 列從立案到 fixed 的中位時間** | 無目標值（只看趨勢，不設達成門檻；不得宣稱成效） | 同上 | 中位數（`fixed@<sha>` 的 commit 時間 − 該列「發現日期」），單位日（日期欄無時分）；sha 取自狀態欄、commit 時間以 git 查；sha 無法解析者排除並計數；`closed-by-decision` 另列。**降為資訊欄的理由**（SCG-0 一審 F-14）：與迴圈沒有因果連結，且可被拆列快速結案、改發現日期、批次結案影響。來源：缺陷帳本＋git |
| **資訊欄**（不作成功指標） | **M3 再開症狀命中後到修復的時間** | 無目標值（只看趨勢，不設達成門檻；不得宣稱成效） | 同上 | 中位數（修復 commit 時間 − 命中列發現日期）；命中清單同 M1 的確認結果；降為資訊欄的理由同 M2（無因果連結、可被拆列與批次結案影響）。來源：缺陷帳本＋觀察帳本＋git |
| **結果指標** | **M4 提案被否決後同型提案再出現的次數** | 0（由冷卻結構保證；>0＝冷卻被繞過） | 每次人工閘決定時 | 計數（同型＝artifact_class＋target＋〔根因鍵相同或證據座標有交集〕）在冷卻期內且無再提資格事件而再生成者。來源：PROP／DEC 紀錄 |
| **結果指標** | **M5 採納後回滾比例** | 不設機械達成門檻：只報兩個值（見量法）與 n、不機械判趨勢，是否隨採納數上升由掌舵者讀值認定（〈M1 判定細則〉(e)）；無「未經人工閘而採納」者 | 每個採納量測窗關閉時 | M5＝窗內被回滾的 promoted PROP 數 ÷ 量測窗已關閉（AC-SI-23-1）的 promoted PROP 數；窗未關閉者不計。**同時報兩個值並列**：(a) 主值＝不含 `unverified_ack` 採納（已驗證類）；(b) 含 `unverified_ack` 採納的值。M／D 類預設走 `unverified_ack`（AC-SI-19-2；§9.4 預期常態），主值的分母主要是易驗證類，有倖存者偏誤，故兩值缺一不可、不得只報其一（AC-SI-22-2）。已關閉的 promoted PROP 數 < `W_MIN`＝NOT-EVALUABLE。來源：DEC 紀錄 |

**M1 檢定力說明**（SCG-0 一審 F-02）：§9.0 Q6 快照基率為 1,490 筆 `fixed` 列中「再開症狀」4 列、「…命中」1 列、`reopens:` 標記 0 列；以此估算，全域 20 列窗的期望再現事件數約 0.01～0.05 件（20×1÷1,490≈0.013、20×4÷1,490≈0.054），全域 M1 幾乎恆為 0／20：基線為 0 時「低於基線」不可能成立，「連續兩窗未低於基線」在最可能的世界裡幾乎必然成立、與迴圈有無效果無關，所以全域窗不能當成功指標或反證依據，只作資訊欄。per-PROP 設計只在基線窗已含 ≥ `W_EVT` 次再現時才評估，但樣本仍是個位數：M1 是證據、不是顯著性檢定；基線窗因「已出現再現」而被選入，之後的窗本就會因均值回歸而較少再現，所以「採納窗未再現」不構成成效證明，只有「可評估卻連續兩窗仍復發」才構成反證。樣本不足的結論一律是 NOT-EVALUABLE（既不算支持、也不算反證）。

**M1 判定細則**（SCG-0 二審 F-29、F-31、F-32；主控裁決 2026-10-19；各參數沿用本節「無先例、未校準」口徑）：
- **「再現標記上線」的錨**（基線窗的起點）＝`params.json` 的 `migration_base_sha` 那個 commit 的 committer 時間（UTC；量測腳本以 `git show -s --format=%ct <sha>` 現查、不另存第二份）。早於該時刻的 DEF／OBS 列**不計再現候選、也不進基線窗**；日精度的 DEF 列以發現日期對錨的 UTC 日期比較，早於者排除、同日者納入（同日更早的列沒有再現標記，不會成為候選）。P1 前（`attr.confirm` 尚不存在）已寫標記的候選，可於 P1 上線後補確認；基線事件數於 `app.promote` 當下固定（`mea.report` baseline，同時記未決候選數、不計入事件數），之後晚到的確認不回補基線——只會讓基線偏低、偏向 NE，保守。
- (a) **再現歸屬**＝以 `attr.confirm` 確認的根因鍵為準：符合該鍵、機會列規則涵蓋、且晉升早於該再現列立案的 promoted PROP 中，**同一筆再現只歸最近晉升的那一個**，不雙計；尚未確認的候選以標記所指已結列的根因鍵暫判歸屬（只供 `pending` 判定），確認後定案。
- (b) **窗重疊**＝允許、各自計：各窗各自累計自己的機會列（同一機會列可同時算在兩個窗），但再現只依 (a) 歸一個 PROP，所以單一事件不會同時令兩個窗 `recurred`。
- (c) **「連續」**（§1.1 反證條件、§8.1 P3 出口）＝同一根因鍵下、依窗關閉時間排序相鄰的兩個可評估採納窗（一個 PROP 只開一個窗〔AC-SI-23-1〕，所以「連續」必然跨 PROP：第二個窗通常屬針對同一症狀的再提案，例如退役或回滾後的新 PROP）；NE 窗與 `pending` 窗不計入也不打斷。
- (d) **M 類機會列與再現重疊**＝再現優先：根因鍵相同的新立列，經 `attr.confirm` 確認為再現者只算再現（窗以 `recurred` 提早關閉）、不算機會列；經 `attr.reject` 駁回者回頭算機會列；仍未決者暫不算，窗關閉時依 AC-SI-23-1 記 `pending`；引用同條目的新立列照常算機會列。
- (e) **M5 趨勢**＝只報值與 n、不機械判趨勢；「是否隨採納數上升」由掌舵者讀值認定。
- (f) **`W_MIN`／`W_OPP` 耦合**＝要求 `W_OPP ≥ W_MIN`，由 `si check` 對 `params.json` 驗（違反＝紅）；否則基線機會列數永遠達不到下限、所有窗永遠 NE。
- **窗關閉時的未決候選與晚到確認**＝見 AC-SI-23-1（`pending`、`mea.amend`）。

#### 1.3.1 明文禁止當成功指標（Goodhart）
| 禁用指標 | 為什麼不行 | 座標 |
|---------|-----------|------|
| 提案數、採納率、駁回率 | 可被灌水（多提小案、挑好過的案）；只准當資訊欄 | DP-10；先例：五問協定家族計數降為資訊欄（`docs/06_quality/FiveQuestion_Audit_Protocol/README.md`:85–89） |
| 審查產出數（發現數）、OBS 筆數 | 對擴張中的面做對抗搜尋沒有不動點；多查漲、少查歸零 | C-13；根 `CLAUDE.md`〈守衛面准入〉 |
| 任何自評分數（LLM 信心、「這提案很好」） | 自評存入記憶會放大錯誤；自評不得充當成效 | DP-01、DP-05（S-11、S-20、S-21）；禁令 17 |
| 覆蓋度、測試數、行數等量化代理 | 對代理指標過度最佳化會損害真實表現 | DP-10；C-12（無覆蓋度門檻） |
| 「零發現」 | 零發現不是 PASS | C-13；`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`:371–375 |
| 研究掃描的來源數與變更數（`changed` 為真的來源數）、`scan` 候選數、體檢候選列數 | 多抓、多檢就多，少抓、少檢就歸零，與審查產出數同構（對擴張中的面做對抗搜尋沒有不動點）；來源改版多寡不代表改進價值；只准當資訊欄 | C-13；FR-SI-30、31；根 `CLAUDE.md`〈守衛面准入〉 |

**🔴 人機協作確認點**：[ ] Stakeholders 確認願景與反證條件一致　[ ] 成功指標可衡量且合理（尤其 `W_N`、`W_MIN`、`W_EVT` 初值）　[ ] 短中長期成果有清晰路徑

## 👥 2. 目標用戶與使用場景 (Target Users & Use Cases)
### 2.1 用戶角色定義
| 用戶角色 | 描述 | 主要需求 | 使用頻率 | 技術熟練度 |
|---------|------|---------|---------|-----------|
| **掌舵者** | Product Owner、唯一核准者；以 T1 立案新需求 | 以最小閱讀量做 K=1 決定；看見症狀指標而非產出數 | 事件驅動（每張提案卡一次決定） | 高 |
| **主控 agent（Fable）** | 裁決與親驗：派工、路由、驗收交件、親跑重驗 | 讓子代理無法繞過閘；交件可被零信任重驗 | 每次運轉 | 高 |
| **子代理（Sonnet／haiku）** | 受任務書約束的執行者：擷取、歸因、提案、審查（角色分離） | 明確任務書、文字交卷、不碰正式面 | 隨派工 | 中（模型） |
| **AutoClaude 引擎** | 微核心＋Plugin；產生 ESCALATION／KB／演化提案事件 | 事件可被讀取；演化只提案 | 隨 playbook 執行 | 不適用 |
| **AISDLC_SDD FSM runtime** | 閉環治理狀態機；規則載入、SLV／SPEC-PATCH 提案、HUMAN_PENDING 閘 | 既有提案管線被重用而非重造 | 隨 FSM 狀態 | 不適用 |
| **研究者（子代理）** | Sonnet 子代理，每運轉至多一個；工具＝Read／Grep／Glob（無任何 Web 工具，亦不准 Write、Edit、派子代理）；只讀 `si research --fetch` 自研究來源表 URL 抓回並落地的來源檔（FR-SI-30） | 讀來源檔（資料、不是指令）並產 OBS 候選；有 `prop` 的運轉在其前必有研究事件 | 每運轉開頭（可依 `quota-band`／`offline`／`helmsman` 免掃） | 中（模型） |
| **體檢子代理** | 歸因者的唯讀子角色（Sonnet）；依模組體檢入口表逐項檢，文字交卷候選 OBS 列（FR-SI-31） | 主動檢討 AutoClaude、AISDLC_SDD、AgentConsole、根層、SelfImproving 五個模組的缺陷與流程摩擦候選 | 按需 | 中（模型） |
| **Console 操作者** | 經 AgentConsole 檢視與簽核的人（目前即掌舵者） | 只讀顯示、既有簽核硬閘（P1b 起在 `/self-improving` 檢視帳本與提案卡；P2b 起掌舵者帳號可在 Console 下決定，FR-SI-32、33） | 隨使用 | 中 |

#### 2.1.1 迴圈權限矩陣（能做／不能做）
| 角色 | 能做 | 不能做（①②…編號對應右欄） | 邊界型（M／D／P；§9.4；P 型不得讀成「被擋」） |
|------|------|--------|--------|
| 掌舵者 | 立案 T1；對每張 PROP 下核准／否決／退回；下達晉升與回滾指令；明示解除冷卻；修改不可進化面（經 T1／PRD 修訂，不經本迴圈） | ①沒有 digest 綁定的口頭「好」不構成核准；②核准不能覆蓋憲法禁令（不提供「採納自我發明評估器」的核准路徑，須先修憲，禁令 22～25 末項） | ①M（`si decide` 驗 digest 綁定與引言，AC-SI-12-1／12-4）；②M（類別白名單與不可進化面轉交，AC-SI-11-1／07-3；沒有核准入口） |
| 主控 agent | 派工與角色分派；讀全部帳本；親驗（親跑指令、先存 rc 再讀）；退回不合規交件；以單一窗口寫帳本處置欄 | ①代為核准任何 PROP（MVP 不開放代決，附錄 C.2 #2）；②改不可進化面；③跳過驗證；④以自評分數當成效；⑤ESCALATION 後自動恢復 | ①M（經 `si decide` 的路徑：只認真人發言載體〔`origin.kind=="human"` 的 user 記錄，或 `queued_command` 附件內的真人文字，AC-SI-12-4 ①〕；`AUTOSDD_UNATTENDED` 下一律非零 rc）＋D（不經 `si decide`、直接追加格式合法的 `dec` 事件行：`si check` 與 `si promote` 回查引言，不符＝`check` 紅、`promote` 拒，AC-SI-12-4 ⑤；偵測型、不是被擋；他機取不到逐字稿＝NE）；②M（經 SI CLI 建立／晉升的 PROP，AC-SI-07-3）＋P（直接 Edit／Write 不經 SI，仍歸既有治理，§9.4 誠實劃界）；③M（`si promote` 驗 verdict＋DEC＋digest，AC-SI-16-1）；④P（量測腳本不讀自評，但「不得宣稱」本身無機械物）；⑤P（本迴圈不驅動 FSM，恢復只走既有人工路徑，AC-SI-17-2） |
| 子代理 | 擔任擷取者、歸因者、提案者（產 `proposed` 物件）、審查者（唯讀、獨立 context）；在沙盒副本跑驗證 | ①寫正式面；②寫 DEC 紀錄；③提案者看見 held-out 與評估指令；④同一提案兼任提案者與審查者；⑤再派子代理（遞迴）；⑥寫報告檔（文字交卷，OBS-SI-004） | ①P＋D（流程型約束；偵測＝正式面 `git status`／HEAD 對照與 AC-SI-08-4 重放，AC-SI-08-1）；②D（CLI 為唯一支援寫入者；直接改既有行由 `si check` 事後標紅〔`ROW-MUTATED`〕，直接追加格式合法的 `dec` 行由引言回查承接〔AC-SI-12-4 ⑤〕；皆為偵測、不是被擋，ADR-SI-02）；③P＋D（AC-SI-20-1；偵測見 AC-SI-20-4）；④P（角色標籤為自述，`reviewer≠proposer` 只檢標籤、不證身分，AC-SI-18-1）；⑤P（AC-SI-10-2；無專屬機械物）；⑥P（任務書；harness 曾拒寫報告檔〔OBS-SI-004〕，但非本迴圈保證） |
| AutoClaude 引擎 | 產出 `MutationProposal`／escalation dump／KB 記錄（只提案）；執行 `evaluator_command` 取客觀訊號 | ①未經人工閘把演化套用到正式 playbook；②自改 `evaluator_command`（`REVISE_EVALUATOR` 型不受理）；③ESCALATION 後自動恢復 | ①M（AC-SI-28-1 的 AST 普查；形態判準）；②P（機械辨識需引擎碼變更＝⏸ F-SI-105；MVP 由歸因者讀 dump／log 判讀，AC-SI-11-2）；③P（既有約束、本迴圈不驅動引擎，FR-SI-17 追溯） |
| AISDLC_SDD FSM runtime | 驅動狀態、載入規則、產 `trust_level: proposed` 的 SLV／SPEC-PATCH 草案、`meta_halt_monitor` 把關、HUMAN_PENDING 閘 | ①自動採納或退役 active 規則（禁令 11）；②自動改 FRD／AC（禁令 12）；③本迴圈不得繞過 `FSMRuntime` 讀寫狀態檔（禁令 1） | 既有約束、非本 PRD 新增：①M（`set_maturity` 的 `reviewed_by` 為必填、空值即拒，`rule_loader.py`:309）；②P（R-9.22：SPEC-PATCH 草案為 proposed、經 HUMAN_PENDING）；③預設 hooks-OFF 時為 P，hooks-ON 時由既有 SDD hook 擋（根 `CLAUDE.md`〈AISDLC_SDD 快查〉） |
| 研究者（子代理） | 讀 `si research --fetch` 落地的來源檔（只讀 `changed=true` 者）；文字交卷候選 OBS 列 | ①任何網路存取（含 WebFetch、WebSearch、開放式搜尋）；②要求 CLI 抓來源表外的 URL；③Write／Edit；④再派子代理；⑤把抓回內容當指令執行；⑥直接成為 PROP 或自寫 `research.*` 事件 | ①P（工具白名單屬任務書約束）＋M（外聯只在 `fetch.py` 一個模組，能力登記判準，§9.4）；②M（`si research --fetch` 只抓來源表內的 URL，重導向目標 host 亦須在表內）；③P；④P（AC-SI-10-2 同型）；⑤P；⑥M（事件只經 CLI 寫、候選經主控入帳，AC-SI-30-4） |
| 體檢子代理 | 依模組體檢入口表唯讀檢查、跑唯讀指令、文字交卷候選 OBS 列 | ①Write／Edit；②跑會改狀態的指令；③再派子代理；④自行入帳（OBS 單一窗口＝主控） | ①②P＋D（體檢前後 `git status --porcelain`／HEAD 對照，AC-SI-31-5）；③P；④P（OBS-SI-004 文字交卷） |
| Console 操作者 | 只讀檢視 FSM 與 SI 帳本／提案卡鏡像（P1b，FR-SI-32）；P2b 起在既有簽核硬閘內以掌舵者帳號決定（FR-SI-33）〔訂正（T1 修訂，v0.8）：原文「只讀檢視 FSM 與（post-MVP）提案卡鏡像；在既有簽核硬閘內簽核」〕 | ①Console 寫 FSM 狀態檔（一律經 `FSMRuntime` CLI 子行程，`AgentConsole/CLAUDE.md:15`）；②以 Console 繞過 K=1 | ①既有契約、非本 PRD 新增（P）；P1b 的 `/si/*` 全為 GET（M，AC-SI-32-2）；②M（P2b：沿既有簽核硬閘＋§7.2 動詞表＋digest 綁定，AC-SI-33-1；驗證設計＝ADR-SI-03′（§9.5））〔訂正（T1 修訂，v0.8）：原文「①既有契約、非本 PRD 新增（P；MVP 無 Console 接點）；②N/A（MVP 無 Console 接點；post-MVP 須另立 ADR，ADR-SI-03 再開）」〕 |

### 2.2 核心使用場景
| 場景 | 觸發條件 | 用戶目標 | 關鍵步驟 | 成功標準 |
|------|---------|---------|---------|---------|
| **SC-SI-1 同症狀復發→提案** | 新缺陷列的症狀與某已結列的再開症狀相符（例：DEF-200-535 的再開症狀於 116 命中而立 DEF-200-551） | 讓同根因不再第三次發生 | 觀察入帳（`reopens` 候選）→ 歸因（根因鍵）→ 產 PROP → 上卡 → K=1 決定 | 採納窗內無再現；M1、M3 可量 |
| **SC-SI-2 三句話決定** | 一張提案卡送達掌舵者 | 不讀長文即可決定 | 卡面三句（症狀／改動／風險與回滾）＋座標；回覆「核准／否決／退回 PROP-SI-NNN」 | 無歧義決定被記為 DEC，digest 綁定 |
| **SC-SI-3 否決後再提被擋** | 子代理對同一目標與根因再生成提案 | 不重複審同一件事 | 冷卻擋下；除非掌舵者解除或出現新證據 | M4＝0 |
| **SC-SI-4 記憶索引容量事件** | `MEMORY.md` 用量達上限的 `CAP_FRAC` | 條目不被默默截斷 | 產生退役／合併提案清單（M 類）→ 逐項 K=1 → 晉升前先做前置快照 | 索引回到上限內；回滾配方乾跑通過 |
| **SC-SI-5 迴圈自觀察（dogfood）** | 開發本模組時發現流程不當或 BUG（本輪 OBS-SI-001 起） | 迴圈自身的缺陷也能被消化 | 發現當下入帳；真缺陷升 DEF；對迴圈自身的改進走轉交 | 處置欄無「之後再看」且皆合枚舉 |

### 2.3 User Stories
- **US-SI-01** 身為掌舵者，我要在一張卡上用三句話決定核准／否決／退回，審閱成本才不隨提案複雜度增加（FR-SI-12、14）。
- **US-SI-02** 身為掌舵者，我要被否決的同型提案在沒有新證據前不再出現，才不必重複審同一件事（FR-SI-13）。
- **US-SI-03** 身為掌舵者，我要任何已採納的改進都能一個動作回滾，出錯時損失才有界（FR-SI-16、23）。
- **US-SI-04** 身為主控，我要子代理交卷的「流程摩擦」成為帶座標的觀察，教訓才不靠記憶累積（FR-SI-01、02、29）。
- **US-SI-05** 身為審查者（子代理），我要有獨立於提案者的外部可重跑訊號，驗證才不是自說自話（FR-SI-18、19、20）。
- **US-SI-06** 身為掌舵者，我要看到症狀型指標（復發率、修復時間、回滾比例）而不是提案數，才能判斷模組值不值得保留（FR-SI-22、24）。
- **US-SI-07** 身為掌舵者，我要記憶索引逼近上限時被提示退役或合併，而不是被默默截斷（FR-SI-25、27）。
- **US-SI-08** 身為 AutoClaude 維護者，我要「演化只提案不套用」是可重跑的檢查而不是文件宣稱（FR-SI-28）。

**🔴 人機協作確認點**：[ ] 用戶角色定義準確　[ ] 使用場景符合實際需求　[ ] 使用流程合理可行

## 🏗️ 3. 功能範圍與 MVP 定義 (Scope & MVP Definition)
### 3.1 MVP / 本次範圍（Brownfield：本次新增範圍）
**MVP 迴圈**（事件驅動，無日曆）：觀察 → 歸因 → 提案 → 人工閘（K=1）→ 套用（僅沙盒；最後一步「晉升」為人工動作）→ 驗證（審查者≠提案者）→ 量測 → 退役。觀察的入口除被動擷取（子代理「流程摩擦」文字交卷、主控發現）外，另有兩個主動入口（T1 2026-10-19 修訂）：**研究掃描**（限定來源、增量、有界，FR-SI-30；綁運轉）與**體檢**（`si scan`＋唯讀子代理，FR-SI-31）；兩者產物一律只是 OBS 候選列，經主控入帳，不直接成為 PROP。

**MVP 邊界**：四類可進化工件（M 記憶條目、P Playbook 片段、R SDD 規則草案、D 非治理文件 diff）；掌舵者本人 K=1；CLI 文字提案卡（Console 是顯示面：P1b 唯讀鏡像、P2b 決定載體，FR-SI-32、33，不改變 K=1 與 DEC 規則）；零新增守衛碼（增補僅 FR-SI-34 落點鎖，見 §3.2；§9.4 的能力登記測試是 P0 純度鎖的細化、不是新守衛，§9.7 #47）；不可進化面一律轉交（FR-SI-07）。**管轄範圍（誠實劃界）**：本迴圈只管轄經它提出的改進；掌舵者與主控依既有治理做的日常編修、以及 harness 自寫的記憶不在其管轄內，只作為觀察來源（FR-SI-29；§10 記憶污染列）。優先級 M＝Must-have、S＝Should-have（刻意不用 P0／P1，避免與階段 P0～P3 同名）。

| 群組 | 功能名稱 | FR | 階段 | 優先級 | 複雜度 | FRD 連結 | 狀態 |
|------|---------|-----|------|--------|--------|----------|------|
| FG-A | 觀察擷取 | FR-SI-01～04 | P0 | M | 低 | 實作輪產出 | P0 已 dogfood |
| FG-B | 歸因 | FR-SI-05～07 | P1 | M | 中 | 實作輪產出 | Planning |
| FG-C | 提案生成 | FR-SI-08～11 | P1 | M | 中 | 實作輪產出 | Planning |
| FG-D | 人工閘 | FR-SI-12～14 | P2（14 為 P1） | M | 中 | 實作輪產出 | Planning |
| FG-E | 套用（沙盒／晉升） | FR-SI-15～17 | P2 | M | 高 | 實作輪產出 | Planning |
| FG-F | 驗證 | FR-SI-18～21 | P2 | M | 高 | 實作輪產出 | Planning |
| FG-G | 量測 | FR-SI-22～24 | P3 | S | 中 | 實作輪產出 | Planning |
| FG-H | 退役 | FR-SI-25～27 | P3 | S | 中 | 實作輪產出 | Planning |
| FG-I | 既有缺口收斂／元層 | FR-SI-28、29、34 | P1、P0、P1 | S、M、S | 低 | 實作輪產出 | Planning |
| FG-J | 研究掃描（限定來源、增量、有界、只產候選） | FR-SI-30 | P1 | M | 中 | 不開 FRD（C.2 #15） | Planning |
| FG-K | 模組體檢（`si scan`＋唯讀子代理） | FR-SI-31 | P1 | M | 中 | 不開 FRD（C.2 #15） | Planning |
| FG-L | Console 面（唯讀鏡像；決定載體） | FR-SI-32、33 | P1b、P2b | M、S | 中 | 不開 FRD（C.2 #15） | Planning |

FRD 欄（T1 修訂，C.2 #15）：本模組自 v0.8 起不另產 FRD／SRD，追溯由 TCS 的 AC 對映與 RTM 承接；既有各列的「實作輪產出」改讀為「TCS」〔訂正：原文「實作輪產出」，保留供追溯〕。

### 3.2 範圍外 (Out of Scope)
- ❌ 更新模型權重（RL 微調、自博弈訓練；SOP S1 不在範圍）。
- ❌ 自動改各層 `CLAUDE.md`（根／`AISDLC_SDD`／`AutoClaude`／`AgentConsole`）／`**/.claude/**`（含各子專案與各版本目錄）／守衛面——無暴露證據不得碰（根 `CLAUDE.md`〈守衛面准入〉）；本 PRD 亦不新增任何守衛碼、鎖或 hook（唯一增補：FR-SI-34 的落點鎖——`tools/tests/` 下的形態判準測試，不在守衛面清單、不是 hook、不碰 `.claude/**`，由掌舵者 T1 直接指令驅動〔2026-10-19 問題 2 與落點指令；附錄 B〕，不是無暴露證據的守衛面擴張）。
- ❌ D 類（非治理文件 diff）直接改 `docs/01～03` 的規格文件本體（PRD／FRD／AC／SRD…）：規格變更一律走既有 SPEC-PATCH（`trust_level: proposed` 草案）＋HUMAN_PENDING。本迴圈的 K=1 晉升不是 FSM 的 HUMAN_PENDING 態、不得取代它（R-9.22；SOP C-02）；D 類目標落在 `docs/01～03` 者，其 PROP 只能是 SPEC-PATCH 草案檔。邊界型 **M＋P**（路徑前綴＝M：`si prop-new` 以 `spec_body_globs` 比對 `touched`，`docs/01～03` 下非 SPEC-PATCH 草案的 D 類目標一律轉交，§9.4 已機械化；語意層＝P，由人審）。
- ❌ 自我發明評估器（meta-oracle 自演化；禁令 22～25 末項、C-07）。反例（候選 CD-01：label-free 自設計評估套件作次級把關；S-24 單一來源，且須先有對抗分離不可繞過性證明，只登記不採納）。
- ❌ 以自評當唯一判官；以無驗證資料的軌跡蒸餾結果直接當採納依據（候選 CD-04，DP-01）。
- ❌ 經自動評估通過即自動採納、無人工閘（候選 CD-02，S-18／S-19；違反禁令 11、12）。
- ❌ 對每次採納做 e-process 序貫統計把關（候選 CD-03：證據單一、本系統無實證，只登記）。
- ❌ 無界遞迴與任何層級的自我擴充（維度、詞彙、算子、字母、深度、互遞迴；禁令 19～25）；迴圈不改自己的預算、閘門、停機條件與指標定義（DP-12）。
- ❌ 日曆觸發、版本號觸發、覆蓋度門檻、「每 N 輪」型觸發（C-12）；常駐行程或排程驅動（本 repo 刻意不做 Daemon：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16.1 ➖）。
- ❌ 運轉期開放式網路搜尋與文獻擴充：一律禁用 WebSearch；運轉期唯一的外聯是 `si research --fetch` 對**研究來源表**（`research_sources.json`）列出之 URL 的 HTTP GET（原始位元組、不用任何 Web 工具），且只在 FR-SI-30 範圍內（限定來源、增量、有界、只產 OBS 候選，由掌舵者 T1 2026-10-19 修訂開放；〔訂正（T1 修訂，v0.8）：原文「運轉期使用 WebSearch／WebFetch 做文獻擴充（SOP 已完成；重跑僅依 SOP S7 觸發）」〕）；研究方法論 SOP 的深度重跑（S1～S8）仍僅依 SOP S7 觸發（本 T1 為其 T-6 實例，不改 SOP 檔）。❌ 跨機器同步記憶（auto memory 本機不跨機器，S-08）。
- ❌ 開 `AutoSDD_improving_117`（附錄 C.1；本 PRD 本身是驅動器）。

### 3.3 未來規劃 (Post-MVP；皆為 ⏸，以再開症狀驅動、不排日曆)
| 功能編號 | 功能名稱 | 再開症狀（一句可觀測事件） |
|---------|---------|--------------------------|
| F-SI-101 | Console 提案卡（唯讀鏡像＋既有簽核硬閘） | **已再開**（T1 2026-10-19 20:21 +08:00，sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13，命中「掌舵者要求在 Console 內審提案」）→ 轉 FR-SI-32（P1b 唯讀鏡像）、FR-SI-33（P2b 決定載體）；原再開症狀：掌舵者要求在 Console 內審提案，或 CLI 卡的 digest 綁定在實際使用中被誤用（附 sid 與 PROP-ID） |
| F-SI-102 | 授權代決（主控在書面授權下代為核准 D 類） | 掌舵者書面明示授權，或掌舵者回報來不及審（附待決 PROP-ID 清單） |
| F-SI-103 | OBS 觀察帳本改機器可讀（jsonl 等）以取代 Markdown 表（ATT／PROP／DEC／APP／MEA／RUN 自 P1 起已是 JSONL 事件帳本，C.2 #5） | 量測腳本解析 Markdown 表連續出現誤判（附列座標），或同一運轉需處理的列數使人工核對不可行 |
| F-SI-104 | harness 整體 diff 提案（playbook 以外的 harness 元件） | 掌舵者要求以提案方式改 playbook 以外的 harness 元件，或同型 harness 缺陷第二次復發（DP-12 的凍結快照評估管線現無） |
| F-SI-105 | 演化提案結構化落地（引擎持久化演化提案的型別與內容，使其進統一審閱面；需引擎碼變更，MVP 改由歸因者讀 dump／log 後登記，AC-SI-08-1） | 歸因者漏登或誤登演化提案（附 OBS／PROP 座標與 dump／log 對照），或掌舵者要求演化提案進統一審閱面（座標：OBS-SI-024、`AutoClaude/autoclaude/core/kernel.py`:371–374） |

**🔴 人機協作確認點**：[ ] MVP／範圍定義清晰　[ ] 優先級合理　[ ] 範圍外項目已確認

## 📊 4. 商業需求分析 (Business Requirements)
> Brownfield 內部模組：不金額化，成本以額度與人審表達。

### 4.1 投資報酬分析
**成本項目（上界）**：掌舵者審閱（每次運轉 ≤ `MAX_PROPOSALS_PER_RUN` 張卡；不審＝不變，FR-SI-10、12）；子代理額度（受 `--pace` 與額度門檻節制、扇出前現查、百分比不複寫，NFR-SI-07；每個運轉另含至多 1 個研究者〔可依額度帶免掃，FR-SI-30〕與按需的體檢子代理〔FR-SI-31〕，皆用 Sonnet）；沙盒與驗證算力（每提案宣告預算、超界收 verdict，NFR-SI-01）；帳本維護（每列 ≤700 bytes、活躍帳本有上限與歸檔，NFR-SI-08）。

**預期收益**：以 §1.3 症狀指標表達，不換算金額。**ROI**：不適用——價值主張被反證時依 §1.1 退場。

### 4.2 競爭分析（替代方案）
| 替代方案 | 優勢 | 劣勢 | 我們的差異化 |
|---------|------|------|-------------|
| 現行人工流程（缺陷帳本＋記憶檔＋掌舵者記憶） | 零新增機制 | 復發靠人記得；記憶無退役；無冷卻 | 把「觀察→提案→閘」結構化，保留人工 K=1 |
| 引擎內建演化（EvolutionPlugin） | 已有提案管線與計數上限 | 只涵蓋 Playbook；無 held-out；有 `REVISE_EVALUATOR` 型 | 統一 PROP 物件；評估器隔離；評估器變更不受理 |
| 論文式全自動自我改進（S-17、S-18、S-19） | 在機器可驗證領域有進步 | 治理工件沒有機器可驗訊號；憲法禁止自動採納；有自評偏誤與目標玩弄風險（S-17 附錄 H） | 只取「文字工件＋外部訊號重跑」，採納一律人工 |

## 💡 5. 功能性需求 (Functional Requirements)
> 📋 **ID 命名規範**: `FR-SI-NN`＝Feature ID 的模組前綴形態（先例：`docs/01_requirements/Agent_ConsoleUI_PRD.md` 的 `FR-SEC-03`、PRD v2.1 的 `F-SBR-001`）；`AC-SI-NN-Y`、`US-SI-NN`、`NFR-SI-NN` 同；觀察／提案／決定 ID 見 §5.1。**編號注意（T1 修訂，v0.8）**：P0 TCS（`docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`:39）的 `AC-030-x`／`AC-031-x`／`AC-032-x` 是 TCS 自增 AC（當時「PRD 的 FR 只編到 29，無編號衝突」），與本節新增的 FR-SI-30～34（`AC-SI-30-x`～`AC-SI-34-x`）無關；P0 TCS 已隨 P0 RELEASE 凍結不改，該句「無編號衝突」的前提自 v0.8 起不再成立，P1 TCS 的 AC 編號規則須避開（Architect 棒定：P1 起各階段 TCS 的自增 AC 一律帶階段前綴，形如 `AC-P1-001-1`，TCS 內引本 PRD 的 AC 一律寫全名 `AC-SI-NN-Y`），RTM 引 P0 的 `AC-030-x` 時須寫明「TCS 自增」。

**閱讀說明**
- 每條 FR 標〔階段｜接既有／新建／既有缺口收斂〕。工件類別碼：**M**＝記憶條目（Claude Code 記憶檔的新增／修改／刪除；AutoClaude KB／偏好條目僅退役或合併提案）、**P**＝Playbook 片段、**R**＝SDD 規則草案（`trust_level: proposed`）、**D**＝非治理文件 diff。不可進化面（NFR-SI-02-1）一律走轉交（FR-SI-07）。
- 座標縮寫：「禁令 N」＝`AISDLC_SDD/CLAUDE.md` Rule 9〈絕對禁令〉第 N 條（位於該檔第 314＋N 行）；「C-NN」＝SOP Part I S1 約束表；「守衛面准入」＝根 `CLAUDE.md`〈守衛面准入（R197 裁決：量、不挖）〉；「鐵律 N」＝根 `CLAUDE.md`〈Windows 側單一載具原則〉。
- 數值參數一律標「初值（未校準）」：有既有同類上限者附座標，無先例者明標「無先例」；調整屬不可進化面（掌舵者核准）；參數 SSOT 建立後以 SSOT 為準，本文不再複寫（根 `CLAUDE.md`「數字現查」紀律）。
- **運轉**＝由啟動事件起、到該次各提案皆落入終態止的一次迴圈執行；不是日曆週期。以 `RUN-SI-NNN` 識別（事件 `run.open`／`run.close`，§9.2；AC-SI-10-3）。
- **⚖**（v0.8 起）＝SA 增補處中，需 Architect 棒或主控再決的點，裁決後改寫為已裁決並記入附錄 C.2。**v0.9 狀態**：v0.8 的 ⚖1～⚖12 已由主控裁決、Architect 棒落檔（附錄 C.2 #16），正文不再有未決的 ⚖，唯 ADR-SI-03′ 的兩點（金鑰通道、入帳模式）仍待主控確認（§9.5）；「Architect 棒定」一詞在 v0.9 已全數落實為具體檔名與參數（§9.1、§9.2、§9.3）。

### 5.1 資料模型定稿（FR-SI-01、08、12 共用）
存放形態已定（OBS＝Markdown 表；ATT／PROP／DEC／APP／MEA／RUN＝JSONL 事件帳本，§9.2；已裁決，附錄 C.2 #5）；P0 現行載體＝`docs/06_quality/SelfImproving_Observation_Ledger.md` 的 Markdown 表（8 欄）加第 9 欄「標記」，欄位語意不因載體改變。

#### 5.1.1 觀察記錄（`OBS-SI-NNN`）
| 欄位 | 口徑 | 必填 | 規則 |
|------|------|------|------|
| ID | `OBS-SI-NNN`（≥3 位流水號、遞增、不重用、不改號；歸檔不改 ID） | 必 | 帳本內唯一；跨檔引用須指向存在的列（AC-SI-04-1） |
| 時間 | 發現時點，本機時間且帶 UTC offset（例 `2026-10-19 02:30 +08:00`）；歷時型另記 `span=<起>～<迄>` | 必 | 列內明示 offset，或沿用檔頭機器可讀宣告 `tz=±HH:MM`（OBS-SI-019 裁決）；與檔頭 tz 不同的列（跨 DST／出差）必須列內明示；兩者皆無＝拒收（鐵律三 naive 時間戳同型；§9.7 #1） |
| 情境 | 視窗・代理・FSM 階段 | 必 | 一句 |
| 症狀 | 一句可觀測事實（不含推論） | 必 | 一句 |
| 證據座標 | 檔案:行／指令＋rc／sid＋seq／帳本列 ID，≥1 個 | 必 | 無座標不入帳；只存座標，不存原始輸出全文 |
| 分類 | `process`／`bug`／`tooling`／`doc`／`decision` | 必 | 單選 |
| 嚴重度 | P1～P4（口徑見下） | 必 | 兩套口徑不得混用 |
| 處置 | 枚舉見下 | 必 | 不得空白或「之後再看」；唯一可原地改寫的欄位，且只能由 `open` 轉為終值一次 |
| 標記（第 9 欄；key=value，`;` 分隔） | `面`＝守衛／產品／文件／流程；`暴露`＝a／b／c／無（`面=守衛` 時必填）；`來源`＝人／代理／工具／逐字稿／帳本（`外部衍生=是` 見 FR-SI-02）；`src`＝研究來源表的 `id`（`回報者=研究者` 的列必帶，且該列必為 `外部衍生=是`；值須存在於 `research_sources.json`，FR-SI-30；其他來源的外部衍生列不帶；P1 實作輪須同步把 `src` 加入 `check` 的標記鍵集合）；`回報者`＝角色標籤；`根因`＝立案當下已知的根因鍵（其後的歸因與確認一律以事件帳本 `attr`／`attr.confirm` 追加、不回寫本列，§9.2）；`rel`＝關聯列 ID；`reopens`＝立案當下已知的被再現已結列 ID（事後確認走 `attr`）；`orig`＝遷移前處置原文（逐字；僅處置值被改寫者記，加第 9 欄後超長者原文搬附註檔、列上留 `orig=@<附註檔>#OBS-SI-NNN`）；`orig` 只用於一次性遷移（AC-SI-01-3），遷移後的更正一律追加更正列（AC-SI-04-3） | 條件 | 加此欄後仍 ≤ `ROW_MAX_BYTES`（700 bytes，先例 `tools/lib/defect_ledger_index.py:545`）；超長內容搬附註檔並留座標 |

**嚴重度口徑（兩套，依 `面` 擇一）**：
- `面≠守衛`（產品／文件／流程）：P1＝走不通、鎖死、資料分裂或已造成不實結案宣稱；P2＝須手動繞過、文件自相矛盾、結案不成立或終點設計有結構漏洞；P3＝文字／可用性；P4＝理論洞（構造性、無暴露證據）。座標：`docs/04_planning/AutoSDD_improving_116.md` §3 標題列；範本〈審查閉環的終止〉（`AutoSDD_Iteration_Prompt_Template.md`:371–375）。
- `面=守衛`：逐字引 `docs/06_quality/FiveQuestion_Audit_Protocol/severity.md`（P2 須有暴露證據 a／b／c 三取一；無暴露證據者一律 P4，入理論洞清單、不立輪、不同輪修）。

**處置枚舉**：`open`（唯一暫態）／`fixed@<sha>`／`DEF-<id>`（升級為缺陷列，該列須存在）／`deferred`（附一句可觀測再開症狀）／`retired`（附依據座標）／`decided`（附裁決者與一句裁決）／`merged@OBS-SI-NNN`／`proposed@PROP-SI-NNN`（已轉提案，終態看該 PROP）。三分類對映範本〈休眠判準〉#3：立案＝`DEF-`、延後＝`deferred`、退役＝`retired`（`AutoSDD_Iteration_Prompt_Template.md`:344–350）。

#### 5.1.2 提案（`PROP-SI-NNN`；先例：觀察帳本處置欄已出現 PROP-SI-001／002）
| 欄位 | 內容 |
|------|------|
| id／state／run／base | `PROP-SI-NNN`（修訂號 `rN`）／見下方狀態機／所屬運轉 `RUN-SI-NNN`／輸入快照（git sha；M 類另記被觸及行 pre-image 摘要） |
| sources | 來源 OBS／DEF ID（≥1）；`sources` 若含外部衍生 OBS（`外部衍生=是`，含研究者候選），仍須 ≥1 內部來源（AC-SI-02-1） |
| attribution | (種類, 座標) 清單；不含任何自評分數 |
| cls／action | M／P／R／D × add／modify／delete／retire；另有 `evaluator-change`、`loop-self` 兩類標記（不受理，只轉交） |
| target／touched／diff／digest／touch | `target`＝目標路徑**集合**（排序、去重；POSIX 邏輯路徑，M 類為 `memory/<檔名>`）；`touched`＝自 `rN.patch` 導出的實際觸及路徑集合與檔數（含新增、刪除、改名兩端，AC-SI-07-3）；增量 delta；內容摘要（演算法見 §9.2，核准綁定此值；`target` 與 `touched` 皆在 digest 內）；新增／刪除行數與觸及比例 |
| budget／verify_plan | 回合・牆鐘・token（零扇出）；提案者建議的可重跑探針、基線症狀預期、突變規格（僅供審查者參考；判定用的評估指令與 held-out 由提案者以外角色凍結，FR-SI-20） |
| rollback／retire_when／reopen_symptom | 一個動作的回滾配方；各一句可觀測條件 |
| proposer／reviewer／route | 角色標籤（reviewer≠proposer）；`loop`／`handoff:<通道>`（由 `si prop-new` 依 AC-SI-07-3 判定，提案者不得自填 `loop`） |

**不可進化面比對**（唯一真相源＝NFR-SI-02-1：錨定語意與實體 glob 皆在該處）：前置檢查對 `touched` 的**每一條**路徑逐一比對 `non_evolvable_globs`，不只比 `target`（glob 相對 repo 根，不帶 `**/` 前綴者只錨定 repo 根，故守衛面寫 `**/.claude/**`）；任一命中＝整張 PROP `route=handoff`（AC-SI-07-3）。

**狀態機（唯一合法轉移）**：`proposed → approved｜rejected｜returned｜handed-off`；`returned → proposed`（修訂 ≤ `MAX_REVISIONS`，超限＝rejected）；`approved → sandboxed → verified`（verdict＝PASS／FAIL／NE）；`verified[PASS] → promoted｜rejected`（人決定不晉升，入冷卻）；`verified[NE] → promoted｜rejected`（promoted 須 `unverified_ack`）；`verified[FAIL] → returned｜rejected`；`promoted → measuring → closed`（clean／recurred／rolled-back）；`closed → retired`（退役提案經閘）。

#### 5.1.3 決定（`DEC-SI-NNN`）
`prop`（PROP ID；`resume` 無對應 PROP，改記 `run`＝`RUN-SI-NNN`）；`kind`＝approve／reject／return／promote／decline-promote／rollback／unblock／resume／ack-handoff（與回覆動詞的對映以 §7.2 動詞表為準；`decline-promote` 由「否決」在 PROP 處 `verified` 態時對映，不另設動詞）；`decider`（掌舵者；MVP 不開放代決）；`quote`（掌舵者原句與逐字稿座標：`sid` 完整 UUID＋`line` 逐字稿 jsonl 的 1 起算實體行號；由 `si decide` 自逐字稿抽取、非主控輸入；`seq` 一詞在本 repo 指工具呼叫序〔`audit_session.py`〕，本欄不沿用，§9.7 #12）；`time`（帶 offset）；`digest`（綁定的卡面摘要）；`reason_class`（證據不足／風險過高／工件類別錯／已被涵蓋／範圍外／卡面不清／未說明）＋一句 `reason`；`flags`（例 `unverified_ack`）；`carrier`（預留；`transcript`＝預設，欄缺席亦視為 `transcript`，舊事件不改；`console`＝FR-SI-33，P2b，以 `audit_ref`／`audit_sha256`／`key_id` 取代 `quote`／`sid`／`line`，ADR-SI-03′；P1 不寫此欄）。

### 5.2 核心功能詳述
#### FG-A 觀察擷取（P0）
##### FR-SI-01 觀察記錄資料模型（欄位定稿）〔P0｜接既有＋定稿〕
**追溯**：DP-08；既有：`docs/06_quality/SelfImproving_Observation_Ledger.md`（欄位暫定版）、`AutoSDD_Defect_Log.md` 列體例。｜**憲法對照**：守衛面准入（`暴露` 欄）；鐵律三（時間欄帶 offset）。
- **AC-SI-01-1** Given 一筆新觀察 When 寫入帳本 Then 必填欄（ID／時間／情境／症狀／證據座標／分類／嚴重度／處置）皆有值、證據座標 ≥1 個可定位、時間帶 UTC offset（列內明示，或沿用檔頭 `tz=` 宣告）；缺任一欄者被檢查器（`si check`，§9.3）判不合規並拒收。
- **AC-SI-01-2** Given `面=守衛` 的列 When 嚴重度標 P1／P2 Then `暴露` 必為 a／b／c 之一且附座標，否則降為 P4 並入理論洞清單；`面≠守衛` 者依非守衛口徑判級。
- **AC-SI-01-3** Given 既有各列（列數與範圍以遷移當下的帳本現查為準，不寫死） When 遷移到定稿欄位 Then 遷移作為**一次性、單一 commit**（遷移 commit）：ID 不變、處置值被改寫者原文逐字留 `orig=`（加第 9 欄後超 `ROW_MAX_BYTES` 者原文搬附註檔、列上留座標）、處置值落入枚舉、遷移後無「之後再看」類字樣（訂正協議：禁止靜默覆寫）。此一次性原地改寫**不計** `ROW-MUTATED`，豁免須同時具備：(a) 遷移 commit 的 sha 寫入 `params.json` 的 `migration_base_sha`（`si check` 的 `ROW-MUTATED` 比對自該 commit 起，AC-SI-04-3）；(b) 一筆掌舵者確認紀錄——處置為 `decided` 的觀察列，附掌舵者原句與逐字稿座標（`sid`＋`line`，體例同 FR-SI-12；P0 階段只記錄、不機械驗引言，驗引言屬 P2 的 AC-SI-12-4）並引用該 sha；二者缺一，遷移視為未豁免（`si check` 自第一個提交起比對，遷移改動的列標 `ROW-MUTATED`）。`orig=` 只用於本次遷移，遷移後的更正走 AC-SI-04-3 的追加更正列。
##### FR-SI-02 觀察來源標記與外部衍生內容隔離〔P0｜新建〕
**追溯**：DP-09、DP-08；既有：無（記憶「依寫入來源過濾」本輪未見，SOP II-6）。｜**憲法對照**：禁令 26（外聯須 OPEN-X.x）；守衛面准入。
- **AC-SI-02-1** Given 觀察內容源自網頁、第三方檔案或工具輸出中的內嵌指示 When 入帳 Then `外部衍生=是`，且該列不得單獨充當**任何類別（M／P／R／D）**提案的證據；須另有 ≥1 個內部來源（本 repo 檔案、指令 rc、掌舵者回報）佐證。P 類（Playbook 片段＝可執行步驟）與 D 類不排除：外部內嵌指示是與 S-13（MemoryGraft）、S-09 的內嵌指示風險同型的入口，P 類被毒化的後果比 M 類更直接。
- **AC-SI-02-2** Given 任一觀察 When 入帳 Then `來源` 與 `回報者` 皆有值；觀察本身不自動啟動任何行為（觀察≠記憶，不得直接寫入記憶或規則）。
##### FR-SI-03 迴圈只由事件啟動〔P0｜接既有〕
**追溯**：既有 C-12（範本〈🏁〉T1～T4：`AutoSDD_Iteration_Prompt_Template.md`:352–358；五問協定 S1～S6：`FiveQuestion_Audit_Protocol/README.md`:67–76）；DP-06。｜**憲法對照**：C-12、C-13。
- **AC-SI-03-1** Given 迴圈任一階段 When 檢視啟動條件 Then 僅有：(a) 掌舵者指令；(b) 同一症狀第二次被記入觀察（經審查者確認相同）；(c) 缺陷帳本新立 P≤2 未結列；(d) 已採納工件的再開症狀命中；(e) 容量事件（FR-SI-27）。不存在日曆、版本號、覆蓋度門檻、「每 N 輪」型觸發。事件偵測＝`si status`（唯讀、按需執行，主控於視窗開場與收尾各跑一次，列入 SOP）；不新增常駐行程、排程或 hook。
- **AC-SI-03-2** Given 某次運轉觀察零筆或零提案 When 判定狀態 Then 記為「無事件」而非「通過」；任何成效宣稱仍須指向症狀指標（§1.3）。
- **AC-SI-03-3** Given 本迴圈產出數量 When 評估是否再開 `AutoSDD_improving_NN` Then 產出數量不構成理由（再開僅依範本〈🏁〉T1～T4）。
##### FR-SI-04 觀察與缺陷帳本分工、引用完整性與原地改寫偵測〔P0｜接既有＋新建（檢查）〕
**追溯**：DP-08；既有：`AutoSDD_Defect_Log.md` 治理、`tools/check_defect_log_crossref.py`、`tools/tests/test_defect_id_reference_integrity.py`（`_REF_RE` 現含 DEF-101／200 兩族）。｜**憲法對照**：鐵律四。
- **AC-SI-04-1** Given 處置為 `DEF-<id>` 或任何 `OBS-SI-`／`PROP-SI-`／`DEC-SI-` 跨檔引用 When 檢查 Then 被引列存在（含 archive）；引用不存在的 ID＝不合規。`DEF-` 引用由既有 `tools/tests/test_defect_id_reference_integrity.py`（`git grep --untracked`，含帳本家族與 archive）涵蓋；`OBS-SI-`／`ATT-SI-`／`PROP-SI-`／`DEC-SI-`／`APP-SI-`／`MEA-SI-`／`RUN-SI-` 由 `si check` 涵蓋；載體尚未建立的 ID 家族（P1 前的 `PROP-SI-`／`DEC-SI-`）印「未判：載體未建立」（NOT-EVALUABLE），不得判通過、亦不得判不合規。
- **AC-SI-04-2** Given 符合缺陷帳本收錄定義的真缺陷 When 觀察入帳 Then 處置須為 `DEF-<id>`（OBS 只留觀察與座標，不取代 DEF 帳本）。
- **AC-SI-04-3** Given 已存在的列 When `si check`（唯讀）自**遷移基準 commit**（`params.json` 的 `migration_base_sha`，AC-SI-01-3）起，對 HEAD 與歷次提交逐對比較同 ID 列 Then 除「處置欄 open→終值一次」外的原地改寫被標 `ROW-MUTATED` 並要求掌舵者過目；基準以前的歷史不比對（一次性遷移豁免，AC-SI-01-3）。更正一律追加「更正列」（`rel=corrects:OBS-SI-NNN`），這是遷移以外**唯一**的更正機制，`orig=` 只在遷移內使用。誠實劃界：未提交工作樹內的多次改寫無歷史可比、不可偵測；事件帳本無遷移、自首個提交起比對（AC-SI-08-4）。

#### FG-B 歸因（P1）
##### FR-SI-05 歸因映射〔P1｜接既有（唯讀量測器）＋新建（映射格式）〕
**追溯**：DP-08；既有：`tools/probe/misstep_attribution.py`（關鍵詞分群、只量不閘）、SDD `test-failure-analyzer` skill（失敗 TC→AC／US／F 映射）、`spec_localizer.py`。｜**憲法對照**：禁令 13（localizer 不得自動改 spec）。
- **AC-SI-05-1** Given 一個觀察或觀察群 When 歸因 Then 產出 `attribution` 清單，每項為（種類∈DEF／OBS／RULE／PLAYBOOK_STEP／DOC／MEMORY_ENTRY／NONE，座標）；NONE 必須寫明「無法歸因」，不得以猜測補位。
- **AC-SI-05-2** Given 歸因輸出 When 檢視欄位 Then 不含自評分數或信心數值；歸因不修改被指向的任何檔案。
##### FR-SI-06 根因鍵與復發連結（人審確認）〔P1｜新建〕
**追溯**：DP-10；既有：缺陷帳本「再開症狀」文字（寫在分流去向／狀態欄，非獨立欄）。｜**憲法對照**：C-13；守衛面准入。
- **AC-SI-06-1** Given 歸因完成 When 指派根因鍵（`<面>/<機制>`，小寫連字號） Then 鍵由歸因者提出、審查者（≠歸因者）確認；鍵被事後更改的次數記入資訊欄。提出與確認各以事件帳本 `attr`／`attr.confirm` 追加（OBS 列不回寫；同一 OBS 後出的不同鍵＝更改一次）。
- **AC-SI-06-2** Given 新列疑似為已結列所防症狀的再現 When 立案當下（`si check` 對新列列出「同證據座標檔案路徑」的已結列供立案者確認；DEF 列無「分類」欄，僅比路徑，候選精準度未量） Then 立案者寫入 `reopens` 標記（OBS）或現象欄 `reopens:DEF-xxx`（DEF，附錄 C.2 #3），其後經審查者（≠立案者）以 `attr.confirm` 確認才計入 M1（審查者也可 `attr.reject` 駁回、附一句理由，駁回者不計再現）；量測腳本只讀已寫入的標記與確認事件，不在量測期掃描產生候選；未確認者標「候選」，只印數量、不計數。
##### FR-SI-07 不可進化面的歸因出口（轉交，不套用）〔P1｜新建（流程）；零新增守衛碼〕
**追溯**：DP-11、DP-12；既有：守衛面准入；治理檔唯讀守衛（`.claude/hooks/block_destructive_git.py`:1423–1472，僅 `AUTOSDD_UNATTENDED` 下阻斷）。｜**憲法對照**：守衛面准入；禁令 22～25 末項；PRD v2.1 §15.5 紅線 10。
- **AC-SI-07-1** Given 歸因目標，或 `rN.patch` 觸及的任一路徑（AC-SI-07-3），落在不可進化面（NFR-SI-02-1 清單） When 產生提案 Then `route=handoff:<既有通道>`（DEF／R 系列／T1／PRD 修訂擇一），卡面標「僅轉交，本迴圈不套用」，迴圈對該目標零寫入（例：OBS-SI-005 的候選 PROP-SI-001 屬守衛面、OBS-SI-012 的候選 PROP-SI-002 屬根 `CLAUDE.md`，皆走轉交）。
- **AC-SI-07-2** Given 轉交目標屬守衛面且無暴露證據（`severity.md`〈暴露度〉三取一） When 轉交 Then 一律登記為理論洞（P4）、不立案修復；本 PRD 不新增任何守衛碼、鎖或 hook。
- **AC-SI-07-3**（SCG-0 一審 F-01 新增；追溯 DP-11、DP-12；憲法對照：禁令 11、12、守衛面准入） Given 一筆 PROP 的 `rN.patch`（unified diff，可含多檔） When `si prop-new`／`si prop-revise` 受理，且 `si promote` 於晉升前以當下的 `params.json` 重驗 Then 解析 patch 內**全部**路徑——`---`／`+++` 行、`diff --git` 標頭、`rename from／to`、`copy from／to`（`/dev/null` 視為無路徑；新增、刪除、改名兩端皆算）——逐一以 `realpath`＋`normcase`＋`casefold` 正規化後比對 NFR-SI-02-1 的實體 glob（`posixpath.normcase` 不改大小寫，macOS APFS 預設大小寫不敏感，故另加 `casefold`；§9.4）；任一路徑命中不可進化面（含凍結版本目錄與模板），或逃出該類別的合法根（M 類＝邏輯根 `memory/`；其餘類別＝repo 根；含 `..`、絕對路徑、磁碟機代號）⇒ **整張** PROP `route=handoff`（不得只轉交命中的檔、其餘照走）。`target` 為排序、去重的路徑集合（不是單一路徑），與 `touched` 一併進 digest（§9.2）；卡核心區顯示「觸及檔案數」與「不在 `target` 內的路徑」（為 0 時顯示 0；非 0 時逐筆列出且計入核心區行數上限，超限者 `prop-new` 拒收並要求拆分或補齊 `target`，AC-SI-14-3）。以合成 patch 自證：正控（只動 `target` 內檔案⇒`route=loop`）；負控（夾帶根 `CLAUDE.md`、`.claude/hooks/*.py`（含子專案與各版本目錄下的 `.claude/`）、凍結版本目錄下的檔、`docs_template/` 下的檔、SI 帳本與 `SelfImproving_Proposals/` 下的檔、路徑逃逸、純改名標頭 ⇒ 皆被轉交）。邊界型 M（SI CLI 前置檢查與晉升前重驗）；誠實劃界：只擋經 SI CLI 建立與晉升的 PROP，直接用 Edit／Write 改檔不經 SI（§9.4）。

#### FG-C 提案生成（P1）
##### FR-SI-08 提案物件（只產 proposed）與狀態機〔P1｜接既有＋新建（統一物件）〕
**追溯**：DP-04、DP-02、DP-07；既有：`EvolutionPlugin` 回傳 `MutationProposal`（`AutoClaude/autoclaude/plugins/evolution_plugin.py`:113–132）、`translation_learner_plugin.py`（只產 proposed）、SDD `slv_generator.py`（`trust_level: proposed`、`reviewed_by: null`）、`spec_patch_proposer.py`。｜**憲法對照**：禁令 10、11、12。
- **AC-SI-08-1** Given 任一來源（歸因者；SLV／SPEC-PATCH 管線草案；EvolutionPlugin——Kernel 路徑只寫 log 一行、無結構化落地，MVP 由歸因者讀 dump／log 後登記，結構化落地需引擎碼變更而不在 MVP，已列 §3.3 F-SI-105） When 產生改進 Then 一律登記為 `PROP-SI-NNN`（§5.1.2 欄位齊備）、初始狀態 `proposed`；R 類 PROP 的 target＝既有管線產出的草案座標（不複製、不改管線）；產生者不得寫正式面（流程型約束，偵測見 AC-SI-08-4；§9.4 邊界三型）。
- **AC-SI-08-2** Given PROP When 狀態轉移 Then 僅允許 §5.1.2 狀態機所列轉移；任何跳級（例：`proposed`→`promoted`）被拒並記 OBS。
- **AC-SI-08-3** Given R 類提案 When 入庫 Then `trust_level: proposed` 且不得阻塞 SCG（禁令 10）。
- **AC-SI-08-4**（SD 新增；追溯 DP-04、DP-10；憲法對照：鐵律四） Given 事件帳本（§9.2） When `si check` 重放 Then ① 每個 PROP 的事件序列皆為 §5.1.2 的合法轉移（任何跳級＝不合規並印違規座標）；② 已提交的既有行不得被改寫或刪除（對 HEAD 與歷次提交逐對比＝`ROW-MUTATED`）；③ ID 唯一遞增、`t` 帶 offset、`kind` 在封閉詞彙內；④ 解析到的事件數低於反空轉下限時印 NOT-EVALUABLE（不得靜默零違規）；⑤ 每筆 `dec` 的引言回查（座標可定位、出處與錨定合法；他機取不到逐字稿＝NOT-EVALUABLE），見 AC-SI-12-4 ⑤。CLI 前置檢查拒收跳級（AC-SI-08-2）；直接改檔的跳級由本條事後標紅。
##### FR-SI-09 提案輸入限定、抽象化與增量 delta〔P1｜新建〕
**追溯**：DP-03、DP-08、DP-09；既有：preference 10 鍵上限（`preference_memory_plugin.py`:19）、KB 結果標籤（`knowledge_base_plugin.py`:7–10）、SDD `NoBigBangValueRewrite`（`AISDLC_SDD/CLAUDE.md`:332）。｜**憲法對照**：禁令 18。
- **AC-SI-09-1** Given 提案生成 When 取輸入 Then 輸入只能是帳本列、歸因證據座標與真實失敗軌跡的**抽象化摘要**（帶結果標籤＝失敗／成功／升級，與適用範圍），不得以原始軌跡全文充當條目。
- **AC-SI-09-2** Given 提案 diff When 受理檢查 Then 為增量 delta：觸及既有內容比例 ≤ `MAX_TOUCH_RATIO`（初值 0.2，無先例）、新增條目 ≤ `MAX_NEW_ENTRIES`（初值 3，無先例）；超界者退回拆分，整份重寫一律不受理。**歸檔型豁免（附錄 C.2 #8）**：逐字搬移（來源行原文＝歸檔行原文）、零內容修改、且單一反向 patch 即可回滾的「歸檔型」提案（M 類記憶索引，FR-SI-27）不受 `MAX_TOUCH_RATIO` 約束，改受 `MAX_ARCHIVE_ENTRIES_PER_CARD`（每卡搬移條目數上限，初值 50，無先例、未校準）；索引新增的歸檔指標行仍計入 `MAX_NEW_ENTRIES`；是否「歸檔型」由 `si prop-new` 以逐字比對判定，任一行被改寫＝非歸檔型、回到 `MAX_TOUCH_RATIO`。
- **AC-SI-09-3** Given M 類條目 When 入提案 Then 必含結果標籤、適用範圍、來源 OBS、退役條件（FR-SI-25）四欄，缺欄不受理。
##### FR-SI-10 提案數量、預算與不遞迴〔P1｜接既有＋新建〕
**追溯**：DP-06；既有：`translation_max_proposals_per_run=3`（`AutoClaude/autoclaude/utils/config.py`:226）、`max_evolutions=3`（:192）、Gap-042／048 計數器（`AutoClaude/CLAUDE.md`:200–201）、`select_proposals` 的 dedup（`core/ports/translation_learning.py`:94）。｜**憲法對照**：禁令 4、16。
- **AC-SI-10-1** Given 一次運轉（以 `RUN-SI-NNN` 識別，AC-SI-10-3） When 產生提案 Then 提案數 ≤ `MAX_PROPOSALS_PER_RUN`（初值 3，先例同上）；與待決或已核准提案同型者（artifact_class＋target＋根因鍵）不重複產生。
- **AC-SI-10-2** Given 提案者或審查者 When 執行 Then 不得再派提案者／審查者（零遞迴；邊界型 **P**：任務書約束，無專屬機械物，偵測面＝無，審查者可人工讀提案者逐字稿〔含 `subagents/`〕但不構成機制，不得讀成「被擋」）；每提案宣告預算（回合、牆鐘、token），超界即停並升級人工（禁令 4）：沙盒與驗證階段的牆鐘／回合上限＝**M**（CLI 收 verdict，AC-SI-17-1），提案者與審查者自身的 token 預算＝**P**（任務書宣告、超出必揭露，NFR-SI-07-3）。
- **AC-SI-10-3**（SD 新增；追溯 DP-06；憲法對照：C-12） Given 任何啟動事件（AC-SI-03-1 的 (a)～(e)） When 迴圈開始 Then 先記一筆 `run.open`（`RUN-SI-NNN`、trigger 與證據座標、輸入快照 `head_sha`）；本運轉內的提案數、修訂數、驗證重跑數皆以該 `RUN-SI-NNN` 計；運轉結束記 `run.close`（各提案落入的終態清單；零事件或零提案＝`no-event`，AC-SI-03-2）；無 `run.open` 的提案不受理。
##### FR-SI-11 提案類別白名單與評估器變更提案不受理〔P1｜新建；接既有型別標記〕
**追溯**：DP-05、DP-12、DP-11；既有：`playbook_evolver.py`:14–16、:37（含 `REVISE_EVALUATOR`）、`evolution_plugin.py`:284–289。｜**憲法對照**：禁令 22～25 末項（meta-oracle 自演化紅線）；C-07。
- **AC-SI-11-1** Given 提案類別 When 受理 Then 僅 M／P／R／D 四類（及其退役）受理；任何改變評估器、held-out、評分權重、本迴圈預算／閘門／停機條件者，或 `rN.patch` 的任一路徑落在不可進化面 (iii)(iv)（AC-SI-07-3，機械判定）者，標 `evaluator-change` 或 `loop-self`，走 FR-SI-07 轉交，不進採納流程；僅憑內容語意才能判定者（無路徑命中）仍由歸因者讀判（AC-SI-11-2）。
- **AC-SI-11-2** Given 引擎演化提案內容涉及評估器（`evaluator_command`、`expected_output_regex`、`[evolved evaluator suggested]` 字樣；舊路徑 `REVISE_EVALUATOR` 型，Kernel 路徑已將其轉成 `REVISE_CURRENT`，log 只留 `type=REVISE_CURRENT` 與理由前 200 字，無法機械辨識型別） When 歸因者讀 dump／log 判讀 Then 標 `evaluator-change` 並記一筆 OBS；不得轉送沙盒或晉升。機械辨識需引擎碼變更（持久化提案型別），同 F-SI-105（AC-SI-08-1），不在 MVP。

#### FG-D 人工閘（P2；FR-SI-14 為 P1）
##### FR-SI-12 K=1 人工閘〔P2｜接既有（SDD HUMAN_PENDING／Console）＋新建（通用閘）〕
**追溯**：DP-04；既有：SDD HUMAN_PENDING 與 `rule_loader.set_maturity(reviewed_by=)`（`rule_loader.py`:309）、`PlaybookRunner._evolution_signoff_granted`（`AutoClaude/autoclaude/execution/playbook_runner.py`:299–322）、AgentConsole 簽核硬閘（`AgentConsole/CLAUDE.md`:15）。｜**憲法對照**：禁令 11、12、13；C-15。
- **AC-SI-12-1** Given 一張 PROP 卡（或迴圈處 SUSPENDED） When 掌舵者回覆 Then 僅 §7.2 動詞表所列語法之一（核准／否決／退回／晉升／轉交／不轉交／回滾／解除／恢復，各帶該列規定的 ID）構成決定；綁 PROP 的動詞同時綁定該 PROP 最近一次送達之卡面 digest（卡面與 digest 一併留存），`恢復` 綁 `RUN-SI-NNN`；DEC 須附掌舵者原句與其逐字稿座標（`sid`＋`line`，見 §5.1.3；引言由 `si decide` 自逐字稿抽取，驗證規則見 AC-SI-12-4），使「主控偽造核准」可被事後稽核（承接動作＝AC-SI-12-4 ⑤ 的回查）；無決定或無法解析的回覆＝預設拒絕、狀態不變。
- **AC-SI-12-2** Given 核准後 PROP 內容改變（digest 不同），或決定對應的卡面 digest ≠ 現行 digest（過期卡） When 嘗試進入沙盒 Then 核准失效、決定被拒並重新上卡。
- **AC-SI-12-3** Given 多張 PROP When 呈現 Then 逐張決定（K=1），不提供「全部核准」；核准者必須是掌舵者本人（MVP 不開放代決，附錄 C.2 #2），DEC 記 `decider`。
- **AC-SI-12-4**（SD 新增；SCG-0 一審 F-07 補錨定、二審 F-30／F-33／F-34 補動詞表、載體與回查；追溯 DP-04、DP-10；憲法對照：禁令 11、12、鐵律四） Given 一筆待記的 DEC（或帳本中已存的 `dec`） When `si decide` 驗證（⑤ 由 `si check`／`si promote` 重跑） Then ① 引言逐字出現在「真人發言」；真人發言有**兩種逐字稿載體**：(i) `type:"user"` 記錄且頂層 `origin.kind=="human"`；(ii) `type:"attachment"`、`attachment.type=="queued_command"` 且 `attachment.origin.kind=="human"` 的附件記錄（掌舵者在主控跑工具中途送出的訊息，文字在 `attachment.prompt`、沒有任何 `user` 記錄帶該文字；§9.0 Q11 普查：本機真人發言有 24.7% 走此載體）；`sdk`〔`claude -p` 的 prompt，主控可自製〕、`isMeta`、harness 代筆、`tool_result`（含 `AskUserQuestion` 的答覆）皆不算；出處欄位缺席＝判 NOT-EVALUABLE、不得記為已核准；逐字稿一律解析 JSON 後以結構欄位判定，不做整行子字串比對（工具內容可含 `"origin":…` 字樣）；② 引言須**錨定**於 §7.2 動詞表的某一列：「整則訊息」＝該記錄的全部 text（user 記錄＝content 的 text 區塊串接；附件＝`attachment.prompt`）；決定語法位於整則訊息的開頭（去除前後空白後），或獨立成一行且整則訊息只含一個決定行；**尾隨規則依該列的「尾隨規則」欄**（無尾隨文字者之後不得有任何文字；要求一句理由或修改要求者之後只准接一句）；子字串命中不算（動詞前有任何前綴字，例如否定詞，亦不受理）；一則訊息含多個 PROP 的決定，或夾帶卡面引用者，整則不受理（回報「無法解析」，預設拒絕，AC-SI-12-1）；動詞、ID 與 `--kind` 須同列一致（ID 欄綁定依該列：`恢復` 綁 `RUN-SI-NNN`，其餘綁 PROP ID）；③ 同一逐字稿中，該發言之前最近一則**含 text 區塊**的 assistant 訊息的 text 逐字含該 PROP 現行卡面核心區（工具輸出不算送達；只含 `tool_use` 的 assistant 訊息略過）；「之前」的時序基準：user 記錄用物理行序，附件用附件自帶的 `timestamp`（入列＝打字時刻）對 assistant 訊息的頂層 `timestamp`——附件記錄物理上落在被注入之處、時間戳早於相鄰記錄（§9.0 Q11），不能用行序；附件缺 `timestamp`＝NOT-EVALUABLE；`恢復` 沒有卡面、不驗 ③（其 RUN 號即綁定：須等於事件帳本折疊出的 SUSPENDED 所在運轉，不符＝拒絕）；④ 逐字稿取不到（他機）＝NOT-EVALUABLE、不記 DEC；⑤ **已存 DEC 的回查**（偽造追加的偵測承接，SCG-0 二審 F-34）：`si check` 對事件帳本中每筆 `dec`、`si promote` 於晉升前對該 PROP 的 `approve` 與 `promote` 兩筆 DEC，各以同一個驗證函式重跑 ①～③——以 `quote` 的 `sid`＋`line` 回查本機逐字稿（座標可定位、該記錄屬 ① 的兩種載體之一、引言逐字相符、② 的錨定成立、③ 的卡面送達與 digest 相符）；不符＝`check` 紅（附該 `dec` 的 `seq`）、`promote` 拒；逐字稿取不到（他機）＝`check` 印 NOT-EVALUABLE、不判紅，`promote` 因無法回查而拒（fail-closed）。直接追加格式合法的 `dec` 事件行（不經 `si decide`）因此是**偵測型（D）**：事後由 `check` 標紅、晉升時被 `promote` 擋下，不是被擋住的寫入。以合成逐字稿的正控（真人核准→受理；附件載體的真人核准在卡面送達之後打出→受理）與負控（`sdk` 發言、他 PROP、過期 digest、被改寫的卡面、**否定句**〔「不核准 PROP-SI-007」〕、**疑問句**〔「核准 PROP-SI-007？先等一下」〕、**引用卡面**〔貼回含「決定：核准 ／ 否決…」的卡面〕、**多 PROP 同則訊息**、`tool_result` 內容含 `"origin":…` 字樣者、動詞表各列的反例（尾隨文字、ID 綁定、前提不符，例：`恢復` 缺 RUN 號、`回滾` 對未晉升者；清單見 §9.1 C8）、附件打出時刻早於卡面送達但物理上注入在其後者→皆拒絕；追加格式合法但引言對不上逐字稿的 `dec` 行→`check` 紅、`promote` 拒）自證；座標＝`sid`＋`line`（該記錄的 1 起算實體行號，附件載體取附件記錄本身的行號；不沿用 `seq`）。本 repo 的同型先例：Stop hook 否定句誤報（DEF-200-501）。
##### FR-SI-13 拒絕紀錄與同型冷卻〔P2｜新建；接既有（dedup、抖動防護）〕
**追溯**：DP-04、DP-10；既有：SDD 抖動防護 R-9.24.1／9.24.2（`AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/R-9.24-meta-halting-offline-experiment-phase-l.yaml`）、`select_proposals` 的 dedup。｜**憲法對照**：禁令 14。
- **AC-SI-13-1** Given 否決或退回 When 記 DEC Then 必含 `reason_class` 與一句理由；「未說明」亦可，但採最嚴冷卻。
- **AC-SI-13-2** Given 某型（artifact_class＋target＋〔根因鍵相同或證據座標集合有交集〕）剛被否決 When 同型提案再生成 Then 被擋（冷卻中），直到再提資格事件：(a) 掌舵者明示解除（DEC kind=unblock；語法 `解除 PROP-SI-NNN`，§7.2）；(b) 否決後新立、同根因鍵、且證據座標與原提案證據集不相交的觀察或缺陷列 ≥1 筆；再提案須附「逐項回應否決理由」。
- **AC-SI-13-3** Given 冷卻被繞過 When 量測 M4 Then 計數 >0 並記 OBS（分類 `bug`）。
##### FR-SI-14 提案卡由確定性轉換產出〔P1｜新建；類比既有 R-9.37〕
**追溯**：DP-04、DP-10；既有類比：`recursion_topology_view` 的 `verify_topology_consistency`（`AISDLC_SDD/CLAUDE.md`:341 禁令 27，渲染須與來源物件同構）。｜**憲法對照**：禁令 27（可審批性不得靠簡化呈現繞過）。
- **AC-SI-14-1** Given PROP When 產卡 Then 卡面核心三句（症狀／改動／風險與回滾）、diff、digest、證據座標、預算、觸及檔案數與不在 `target` 內的路徑（AC-SI-07-3）皆由 PROP 欄位與 `rN.patch` 確定性轉換而來；提案者自由撰寫的摘要不得取代 diff 本文。
- **AC-SI-14-2** Given 一張卡 When 反解析卡面欄位 Then 與 PROP 物件逐欄一致（digest、diff 行數、觸及檔案數、驗證狀態）；不一致的卡不得送達掌舵者。
- **AC-SI-14-3** Given 一張卡 When 檢視版面 Then 核心區 ≤ 12 行、每項單行且寬度 ≤ `CARD_LINE_MAX`（初值 100，無先例；CJK 算 2，同根層 E501 量法）；完整 diff 與證據以座標附於卡尾（§7.3）。

#### FG-E 套用（P2；僅沙盒，最後一步晉升為人工動作）
##### FR-SI-15 沙盒套用（正式面零變更）〔P2｜接既有＋新建〕
**追溯**：DP-04、DP-07、DP-11；既有：`PlaybookEvolver.apply_evolution` 寫 `evolved_<原檔名>.yaml` 而非原地改（`AutoClaude/autoclaude/evolution/playbook_evolver.py`:302）、SDD `sandbox_runner.py`／R-9.20.1。｜**憲法對照**：鐵律五；根 `CLAUDE.md`〈權限姿態〉。
- **AC-SI-15-1** Given 已核准 PROP When 套用 Then 只作用於隔離副本（沙盒；形態由 ADR-SI-04 定，預設 `git archive` 匯出到樹外）；沙盒位置不得改變正式面的掃描與棘輪量測結果——沙盒根必須在 repo 樹外、且不得在 `.claude/worktrees/`（R178 實測：樹內 worktree 被全庫掃描鎖算成第二份複本而假紅）；套用前後正式面 `git status --porcelain`、HEAD、`git worktree list` 逐字相同（任何沙盒形態都不得在正式面新增 worktree 登記；此項同時偵測誤建樹內 worktree）。
- **AC-SI-15-2** Given 沙盒建立與清理 When 執行 Then 不使用鐵律五擋下的毀滅性 git 形態（`stash`、`reset --hard`、`checkout --`、`clean` 等）；清理＝丟棄副本即回原狀。
- **AC-SI-15-3** Given 遇 R-9.6 擋寫（路徑子字串含 `docs/01～03` 且視窗綁定 IMPLEMENTATION 中功能鍵）或 harness 分類器拒絕（`.claude/**`） When 套用 Then 不得以改派子代理或換路徑繞過；改由符合條件的視窗處理，或走轉交（FR-SI-07）。
##### FR-SI-16 晉升為人工動作與回滾配方〔P2｜新建；接既有（git、set_maturity）〕
**追溯**：DP-04、DP-07、DP-02；既有：git、`rule_loader.set_maturity(reviewed_by=)`、`EvolutionMetadata`（`playbook_evolver.py`:274–298 的 generation／mutation_log）。｜**憲法對照**：禁令 11、12。
- **AC-SI-16-1** Given 驗證 verdict＝PASS 且 digest 與核准時相同 When 掌舵者下達晉升指令（DEC 附其原句與 `sid`＋`line`，驗證同 AC-SI-12-4） Then 才合入正式面；verdict 為 FAIL、或 NE 而無 `unverified_ack`（FR-SI-19；NE 的晉升須用 §7.2 的 `晉升 PROP-SI-NNN 未驗採納` 式）、或 digest 不同者，晉升被拒。`si promote` 另對該 PROP 的 `approve` 與 `promote` 兩筆 DEC 重跑 AC-SI-12-4 的回查（⑤）：不符，或逐字稿取不到（他機）而無法回查，晉升被拒（fail-closed；晉升須在持有該逐字稿的機器上進行）。
- **AC-SI-16-2** Given 每筆 PROP When 受理 Then 必附一個動作的回滾配方（git revert、逐行反向 patch、刪檔、`set_maturity` 退回之一）；回滾配方在驗證階段乾跑通過才可晉升——乾跑＝沙盒內「正向 patch→反向 patch」後與 base 匯出逐位元相同（M 類的記憶目錄不在版本控制內，不得假設 git revert 可用；harness 可能於期間併發自寫索引，故 M 類以逐行反向 patch 回滾、不整檔還原，前置快照僅作稽核副本）。
- **AC-SI-16-3** Given 晉升完成 When 記 DEC Then 含晉升者、時間（帶 offset）、合入 sha 或快照座標。
##### FR-SI-17 套用預算、停機與不自動恢復〔P2｜接既有〕
**追溯**：DP-06；既有：R-9.5／R-9.14（ESCALATION 後不自動恢復）、`step_timeout_seconds`（`AutoClaude/autoclaude/utils/config.py`:188）。｜**憲法對照**：禁令 4、6、7、26。
- **AC-SI-17-1** Given 沙盒套用或驗證超出宣告預算 When 超界 Then 立即停止並收一個 verdict（FAIL 或 NE），不等沙箱（禁令 26：沙箱 hang 收 verdict），並升級人工。
- **AC-SI-17-2** Given 迴圈進入 SUSPENDED（AC-SI-24-1），或驗證超界而升級人工（AC-SI-17-1） When 要繼續 Then 僅能由掌舵者以 DEC 恢復或決定下一步（SUSPENDED＝`dec(resume)`；超界升級後＝依 §5.1.2 狀態機的人工決定），迴圈與子代理不得自動恢復、自行重試或繞過（禁令 6、7 同精神；重跑上限見 NFR-SI-01）；SUSPENDED 期間 `si prop-new` 拒收（邊界型 M，由事件帳本折疊判定，§9.4）。FSM 自身的 ESCALATION 恢復不在本迴圈內：本迴圈不讀寫 FSM-STATE、不恢復任何 FSM 鍵，該恢復只走既有人工路徑（禁令 1、6、7；邊界型 P，不由本迴圈機械擋）。

#### FG-F 驗證（P2）
##### FR-SI-18 審查者≠提案者；外部訊號為主依據〔P2｜接既有＋新建〕
**追溯**：DP-01、DP-05；既有：R-9.20.3（Generator／Evaluator 獨立 context；`governance/rules/R-9.20-phase-h-gae.yaml`）、`evaluator_command` 二次驗證（`AutoClaude/CLAUDE.md`:175、239）、鐵律七檢查表第 3 點（複審唯讀）。｜**憲法對照**：禁令 17；鐵律七。
- **AC-SI-18-1** Given 一張 PROP When 驗證 Then 審查者與提案者為不同代理實例與不同 context，審查者全程唯讀、不得自起背景長任務（流程型約束；機械化選項見 ADR-SI-09）。
- **AC-SI-18-2** Given 判定 When 記 PASS Then 主依據必為外部可重跑訊號（指令 rc、測試、重放結果）；LLM 審查意見只作次級，且不得單獨把 FAIL 改成 PASS（同家族模型的審查獨立性有限，見 §10 自評偏誤列）。
##### FR-SI-19 對照／突變與三態判定〔P2｜新建〕
**追溯**：DP-01、DP-10；既有：五問協定三態 PASS／FAIL／NOT-EVALUABLE（`FiveQuestion_Audit_Protocol/README.md`:48–62）、SDD `counterfactual_replay.py`（命中率僅為證據）、整合輪 116 QA 以 `git archive` 匯出 commit 量突變（`docs/04_planning/AutoSDD_improving_116.md` §9.1）。｜**憲法對照**：禁令 14、26；C-13。
- **AC-SI-19-1** Given 驗證計畫 When 執行 Then 先對照：基線（未套用）須重現症狀（RED），套用後症狀消失（GREEN），再突變（弱化或移除提案內容）後症狀須回來（RED）；三者缺一＝驗證無鑑別力＝NE。另需載具自證：沙盒內被測模組的 `__file__` 落在沙盒內（可編輯安裝可能指向主樹，須以 `PYTHONPATH` 遮蔽並自證），否則 NE（「驗證載具要能觸發 bug」判例）。
- **AC-SI-19-2** Given 結果 When 判定 Then 僅三態 PASS／FAIL／NE（NOT-EVALUABLE）；NE 不得視為 PASS，晉升須掌舵者 `unverified_ack`，且該 PROP 在指標中另列「未驗採納」；M／D 類無可執行症狀探針者預設 NE（容量事件觸發的 M 類退役以容量量測〔位元組／行數：基線≥`CAP_FRAC`×上限＝RED、套用後低於該值＝GREEN、半數還原後回到該值以上＝RED〕為症狀探針，可得 PASS，不在此列）。
- **AC-SI-19-3** Given R 類重放 When 命中率高 Then 僅為證據，不得據此自動核准（禁令 14）。
##### FR-SI-20 評估器隔離與 held-out 分割〔P2｜新建（通用化既有 SDD 機制）〕
**追溯**：DP-05；既有：R-9.20.3、R-9.27～R-9.29 held-out 對抗分離（`AISDLC_SDD/CLAUDE.md`:331～333）、`AISDLC_SDD/AISDLC_SDD_v0.30/knowledge/held-out-corpus/`。｜**憲法對照**：禁令 17、18、19；C-05、C-07。
- **AC-SI-20-1** Given 一個驗證計畫 When 於歸因完成、提案生成之前 Then 評估集（held-out 觀察／缺陷列分割與評估指令）由提案者以外的角色先行凍結（內容存家目錄 `~/.autosdd/selfimproving/heldout/`、不入 git；摘要 digest 入事件帳本 `heldout.freeze`）；提案者任務書不含其內容與路徑（流程型隔離，偵測見 AC-SI-20-4）。
- **AC-SI-20-2** Given 評估集 When 規模 < `MIN_HELDOUT`（初值 5；先例：`SDD_REPLAY_MAX_CASES` clamp 下限 5、`params.json` 的 `q1b_min_n`＝5） Then 判 NE，不得以小樣本宣稱有效。
- **AC-SI-20-3** Given 任一角色 When 嘗試修改評估指令、評分權重、held-out 或量測腳本 Then 視為 `evaluator-change`（FR-SI-11）；僅掌舵者經 T1 可改。
- **AC-SI-20-4**（SD 新增；追溯 DP-05、DP-10；憲法對照：禁令 17、18） Given 一筆 PROP 進入驗證 When 預檢 Then ① 以 `heldout.freeze` 的 digest 重算 held-out 檔，不符＝NE（疑遭改寫）；② 掃提案者逐字稿（含 `subagents/`），工具呼叫的路徑或 pattern 命中 held-out 目錄、`params.json` 或量測腳本者標 `exposed`＝驗證判 NE；本檢查只量不阻擋，逐字稿取不到＝NE（偵測型邊界，§9.4）。
##### FR-SI-21 驗證證據逐字入帳〔P2｜接既有（鐵律四）〕
**追溯**：DP-10；既有：`.claude/hooks/check_claim_provenance.py`（Stop 事件，只出聲不阻斷）。｜**憲法對照**：鐵律四；C-14。
- **AC-SI-21-1** Given 驗證記錄 When 入帳 Then 含執行者、時間（帶 offset）、指令、rc（先存變數再讀）、輸出摘錄座標（＝`out_sha256`＋`out_bytes`＋經遮蔽〔先例 `AutoClaude/autoclaude/utils/redaction.py`〕的末段摘錄 ≤300 bytes；原始輸出全文不入 git〔NFR-SI-02-4〕，稽核靠「同指令於同 base 沙盒重跑」）、母體／樣本數；轉述他包者標 `[他包回報]`，主控親跑後才升格為「已驗證」。
- **AC-SI-21-2** Given 「已驗證／已達標」宣稱 When 檢視 Then 附當回合真跑輸出；貼不出者改寫為「未驗證」。

#### FG-G 量測（P3）
##### FR-SI-22 症狀型指標量測（確定性）〔P3｜新建；類比既有量測器〕
**追溯**：DP-10；既有：`tools/probe/audit_session.py`（只量不閘，檔頭:8–14；印判準指紋，檔頭:31–32）、`tools/probe/misstep_attribution.py`。｜**憲法對照**：C-13；根 `CLAUDE.md` 12-Rule Rule 5（確定性轉換不用模型）。
- **AC-SI-22-1** Given 帳本與 git 歷史 When 跑量測腳本 Then 輸出 M1～M5 的值、樣本數、窗定義與「判準指紋」；腳本不呼叫模型。NE 判準：M1 為 per-PROP 前後對照（§1.3），NE 護欄量**基線窗內確認再現事件數**（< `W_EVT`＝NOT-EVALUABLE，基線事件數 0 一律 NE），並同時印基線窗事件數與機會列數（機會列數 < `W_MIN` 亦 NE）；因再現而提早關閉的採納窗（`recurred`）照樣可評估，無再現的 `rolled-back` 窗 M1 不評估（仍計 M5）；窗結果取生效結果（`mea.close` 加最後一筆 `mea.amend`，AC-SI-23-1），`pending` 的窗不評估、不計入分母；全域 `W_N` 窗的值只印在資訊欄；M5 同印含與不含 `unverified_ack` 兩值；其餘 n < `W_MIN`（初值 5，先例 `q1b_min_n`／`q2_min_n`＝5）者印 NOT-EVALUABLE。
- **AC-SI-22-2** Given 輸出 When 呈現 Then 資訊欄（提案數、決定分佈、OBS 筆數、`closed-by-decision` 數、未驗採納數，以及 M2、M3 與全域窗 M1）與成功指標（M1 per-PROP、M4、M5）分區；M5 的兩個值並列於成功指標區，不得只報「不含 `unverified_ack`」者；指標定義變更必改指紋，不同指紋的數字不得並列；量測腳本不接任何閘門。
- **AC-SI-22-3** Given 提案者 When 運作 Then 任務書不含指標目標值、計算細節與 `params.json` 路徑（迴圈層指標只對掌舵者與量測者呈現；流程型隔離，偵測同 AC-SI-20-4 ②）。
##### FR-SI-23 採納後量測窗與回滾偵測〔P3｜新建〕
**追溯**：DP-04、DP-10；既有：缺陷帳本「再開症狀」體例。｜**憲法對照**：C-12。
- **AC-SI-23-1** Given 一筆 promoted PROP When 開量測窗 Then 窗以事件界定：自晉升起，到「機會列」累計 `W_OPP`（初值 5，無先例）筆，或「出現再現／回滾」先到者關閉；窗關閉結果記 `clean`／`recurred`／`rolled-back`／`pending`（見下）。**機會列規則**（採納窗與 M1 的基線窗共用）：非 M 類＝OBS／DEF 新立列，其證據路徑落在該 PROP `target` 路徑集合的最近公共目錄之下（DEF 表頭無「面」欄，不能比「面」；無路徑的列不計）；**M 類**（`target`＝repo 外的邏輯路徑 `memory/<檔名>`，證據路徑幾乎不會落在其前綴下）＝新立列中，其根因鍵（經 `attr.confirm` 確認）與該 PROP 歸因的根因鍵相同，或其證據座標／現象欄引用該記憶條目（檔名或條目標題）者。M1 的基線窗＝同一 PROP 晉升前、同一機會列規則、自再現標記上線後的最近 `W_OPP` 筆機會列（§1.3）。窗未關閉的 PROP 不計入 M5 分母，也不以暫值宣稱 M1（維持 NOT-EVALUABLE）。**未決候選與晚到確認**（SCG-0 二審 F-31）：本條的「再現」＝經審查者 `attr.confirm` 確認者；窗內（自晉升起至關閉時點）已寫再現標記、但 `attr.confirm`／`attr.reject` 都還沒到的候選稱「未決候選」（歸屬暫判依 §1.3〈M1 判定細則〉(a)）。窗因機會列累計達 `W_OPP` 而要關閉時，若仍有未決候選⇒`mea.close` 記 `pending`：不算 `clean`，不計入 M1 與 M5 的分母，也不計入 `STOP_AFTER_BAD` 的任何一側，PROP 維持 `measuring`；該窗的候選全數落定（`attr.confirm` 或 `attr.reject`）時，CLI 於同一把寫入鎖內追加 `mea.amend`（`window`＝該 `mea.close` 的 `seq`、`from`＝`pending`、`to`＝任一候選確認則 `recurred`、全數駁回則 `clean`、`cause`＝觸發落定的事件 `seq`）。**晚到確認**——確認事件晚於 `mea.close`，而其再現列的立案時間早於窗的關閉時點（關閉時點＝累計達 `W_OPP` 的那一筆機會列的立案時間，或回滾 DEC 的時間；「先到」一律比再現列的立案時間、不比確認時間）——同樣追加 `mea.amend`（`from`＝`clean` 或 `rolled-back`、`to`＝`recurred`），不得靜默維持 `clean`。窗的生效結果＝最後一筆 `mea.amend` 的 `to`、無則取 `mea.close` 的值；`mea.close` 本身不改寫（帳本只准追加）；M5 的分子取 `dec(rollback)` 的事實，不隨窗結果標籤的改判而變。
- **AC-SI-23-2** Given 窗內偵測到再現（「偵測」＝經審查者 `attr.confirm` 確認的再現；僅有未決候選時只在 `si status` 印候選數與 `pending` 的窗，不產生回滾卡） When 出聲 Then 產生回滾提案卡（不自動回滾）；回滾動作由掌舵者執行，記 DEC（回覆語法 `回滾 PROP-SI-NNN <一句理由>`，§7.2）。
##### FR-SI-24 劣化暫停（邊際報酬遞減）〔P3｜新建〕
**追溯**：DP-06；既有：SDD `SDD_META_CHURN_MAX`（R-9.24.1）、ESCALATION 不自動恢復（R-9.5）。｜**憲法對照**：禁令 6、7、14。
- **AC-SI-24-1** Given 連續 `STOP_AFTER_BAD`（初值 2，無先例）筆採納於其量測窗內 recurred 或 rolled-back When 判定 Then 迴圈進入 SUSPENDED：不再受理新提案，僅掌舵者可恢復（DEC kind=resume；語法 `恢復 RUN-SI-NNN <一句理由>`，§7.2）。SUSPENDED 由事件帳本重放導出（最近連續 `STOP_AFTER_BAD` 筆窗的生效結果為 recurred／rolled-back〔含 `mea.amend` 的更正；`pending` 的窗不計入也不打斷連續〕且其後無 `dec(resume)`），不另存狀態。
- **AC-SI-24-2** Given SUSPENDED When 觀察 Then 觀察擷取（FR-SI-01）照常，僅提案以後各階段暫停。

#### FG-H 退役（P3）
##### FR-SI-25 退役條件與退役提案（人工）〔P3｜接既有（scaffold_gc、set_maturity）＋新建（通用）〕
**追溯**：DP-02、DP-03；既有：`scaffold_gc.py`（GC 只提議、永不自動退役，檔頭:10–11）、`scaffold_ceiling_detector.py`（advisory）、`rule_loader.set_maturity(reviewed_by=)`。｜**憲法對照**：禁令 11。
- **AC-SI-25-1** Given 任一已採納工件 When 受理 Then 帶 `retire_when`（一句可觀測條件）與 `reopen_symptom`（一句可觀測再開症狀，不得含輪號、日期、「待排程」字樣）。
- **AC-SI-25-2** Given 退役 When 執行 Then 退役本身是 `action=retire` 的 PROP、走同一 K=1 閘；SDD 規則退役必經 `set_maturity(reviewed_by=)`；系統只提議、不自動退役。
##### FR-SI-26 抖動防護（add↔retire）〔P3｜接既有（SDD）＋新建（其他面）〕
**追溯**：DP-04；既有：`tools/fsm_runtime/meta_halt/meta_halt_monitor.py`、R-9.24.1／9.24.2（`CHURN_MAX` 預設 2；退役棘輪）。｜**憲法對照**：禁令 14。
- **AC-SI-26-1** Given 同一（target, 根因鍵）的 add→retire→re-add 循環 When 次數 > `CHURN_MAX`（初值 2，先例 `SDD_META_CHURN_MAX`） Then 不再受理並升級人工。
- **AC-SI-26-2** Given 已退役工件被再提 When 受理 Then 須附 capability-delta 證據＝退役後新出現、與原證據集不相交的症狀證據；SDD 規則面沿用 `meta_halt_monitor` 把關，其他面由本迴圈檢查。
##### FR-SI-27 容量事件觸發退役／合併提案〔P3｜新建；接既有上限〕
**追溯**：DP-03、DP-09；既有：S-08（`MEMORY.md` 前 200 行或 25KB；官方頁另述 harness 自帶的近上限提醒與超限錯誤回報）、`_MAX_ENTRIES=1000`（`AutoClaude/autoclaude/utils/knowledge_base.py`:31）、preference 10 鍵（`preference_memory_plugin.py`:19）。｜**憲法對照**：C-12（事件驅動、無日曆）。
- **AC-SI-27-1** Given 有上限的儲存或載入面（記憶索引、KB、偏好注入） When 用量達其上限的 `CAP_FRAC`（初值 0.9，無先例；`MEMORY.md` 寫稿時約為上限的 89%～91%，25KB 換算未查證；人工歸檔後已下降，數值一律以 `si capacity` 現查為準） Then 記憶索引：產生退役／合併提案清單（M 類，逐字歸檔，只提議、不自動刪除）；KB（`_MAX_ENTRIES` 自動汰除，現有 `kb_cache_eviction_count` 指標）與偏好（`IPreferenceStore` 無 delete，唯一 production 寫入點為 `wiring.py:187` 的 config seed）：MVP 只印容量報告並記 OBS，不產退役提案（需引擎碼變更，§9.7 #23）。**與 harness 自帶容量機制的先後與衝突**（S-08；SCG-0 一審 F-05）：harness 在 Claude 寫入索引後自行量測並提醒或報錯，其改寫者（harness 內的 Claude）是不受本迴圈控制的寫入者；兩個機制各自觸發、先後不預設（harness 提醒的觸發門檻本 PRD 未查證），故衝突處置不依賴先後，一律以機械的 pre-image 比對為準——M 類 PROP 的 digest 綁被觸及行的 pre-image，晉升前重驗，不符＝拒絕並重新上卡、不嘗試自動合併，且 CLI 印可貼入的 OBS 草稿列（§9.4，ADR-SI-06）；harness 自行改寫索引的結果（含其因提醒而合併或丟棄條目）不在本迴圈管轄內，只作觀察來源。
- **AC-SI-27-2** Given 索引檔實際大小超過載入上限（位元組或行數）而仍有條目排在上限之後 When 檢查 Then 視為「截斷風險」缺陷入帳（面＝流程），因為「被截斷」與「已退役」的表徵不同；官方頁另述超限時 harness 的寫入仍成功但回錯誤要求重寫索引（S-08），該錯誤出現過同樣入帳，不得當成「harness 已處理」而略過。

#### FG-I 既有缺口收斂／元層
##### FR-SI-28 「演化只提案不套用」由宣稱升為可重跑檢查〔P1｜既有缺口收斂；零新增守衛碼〕
**追溯**：DP-04、DP-12；既有：`AutoClaude/CLAUDE.md`:191、`evolution_plugin.py`:9–19（`ON_EVOLUTION_APPLY` 為 NO-OP）、DEF-13-004 `evolution_approver`（`playbook_runner.py`:299–322）。｜**憲法對照**：禁令 12；守衛面准入（無暴露證據⇒取最小形態）。
- **AC-SI-28-1** Given AutoClaude 原始碼 When 靜態可達性檢查（AST 普查，pytest；`AutoClaude/tests/contract/` 新增 1 檔、引擎碼零改動，§9.4） Then 可證：① `PlaybookRunner` 無生產建構點（既有 `AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py`:97–112 已釘且含對照組，本檔引用、不重寫）；② `apply_evolution` 呼叫點恰為受檢清單（`execution/steps_orchestrator/_escalation_handler.py`:111／208／263、`execution/mutation_applier/_complex_mutations.py`:114），且 `execution/` 之外無模組 import `steps_orchestrator`／`mutation_applier`；③ 演化重載的**生產者**普查：`evolved_playbook_path=` 與 `PersistenceResult(kind="evolved_playbook")` 在 `plugins/` 與 `core/`（定義與彙整除外）零命中——因 `core/services/auto_resume.py`:255–272 的重載分支無 signoff 閘，現靠「無生產者」不可達；④ `require_evolution_signoff` 的讀取點只在 `execution/playbook_runner.py`；⑤ 文件宣稱釘住：`AutoClaude/autoclaude/main.py` 仍含註解字樣「舊 PlaybookRunner 直連模式已於 W6 拔除」，且 `AutoClaude/CLAUDE.md` 的演化提案敘述引的是該字樣、不含 `main.py:<行號>` 形態（AC-SI-28-2；與該文改述同一輪落地）。每格自帶對照組（掃描器在 `execution/` 抓得到對照名；⑤ 以合成的含行號引用文字驗證其會被判紅）；誠實劃界：形態判準，`getattr`／`importlib` 動態建構看不到。這把 `AutoClaude/CLAUDE.md`:191 的文字宣稱變成可重跑檢查，取代僅靠「沒有建構點」。
- **AC-SI-28-2** Given `require_evolution_signoff` 預設 False（`utils/config.py`:194，演化版自動重載放行）而文件宣稱「只提案不套用」 When 對照 Then 二者須一致：文件改述為「Kernel 路徑只提案；預設放行，但無生產建構點、無演化重載生產者」（附錄 C.2 #4 已裁維持 False＋文件改述，零退化）。🔴 「改預設為 True」**對生產路徑無效**：該旗標只被不可達的舊路徑讀取（`execution/playbook_runner.py`:306），`AutoResumeService` 不讀；在生產路徑加閘屬引擎碼變更，已裁不做（附錄 C.2 #7，ADR-SI-07）。**文件座標現況**：`AutoClaude/CLAUDE.md`:191 原引 `main.py:239`（過期；該行為 `model = os.environ…`），已於 commit 69a644e6 改引 `main.py:277`（OBS-SI-023 fixed；該行註解為「舊 PlaybookRunner 直連模式已於 W6 拔除」）。行號引用本身會再腐，故收斂為**一種**修法：改述一律引該註解字樣、不引行號，並由 AC-SI-28-1 ⑤ 釘住（改述與 ⑤ 同一輪落地）；該檔屬不可進化面，改述走一般開發流程（DEF／AutoClaude 改進），不經 PROP。
- **AC-SI-28-3** Given 任何路徑出現生產建構 `PlaybookRunner` 或演化重載生產者（OBS-SI-010 再開症狀；AC-SI-28-1 轉紅） When 發生 Then 立即升為缺陷列，並走 FR-SI-12 的人工閘（此時暴露證據成立）。
##### FR-SI-29 迴圈自我觀察（dogfood；T1 原文第 3、4 點）〔P0｜新建（流程）〕
**追溯**：DP-08、DP-12；既有：T1 原文第 3、4 點、`SelfImproving_Observation_Ledger.md`。｜**憲法對照**：C-12。
- **AC-SI-29-1** Given 開發或運轉本迴圈時發現流程不當或 BUG When 發現當下 Then 一律入觀察帳本（一句症狀＋一個座標），真缺陷升 DEF；子代理以文字交卷的「流程摩擦」節為入口（OBS-SI-004）。
- **AC-SI-29-2** Given 對迴圈本身預算／閘門／停機條件／指標定義的改進 When 提出 Then 一律標 `loop-self` 並轉交（FR-SI-07），僅經掌舵者 T1／PRD 修訂；本迴圈不得提案修改自己（DP-12；禁令 20～25）。

##### FR-SI-34 根層模組落點鎖〔P1｜既有缺口收斂（OBS-SI-105）；新建（形態判準測試）〕
**追溯**：T1 2026-10-19 問題 2（原文「請規劃日後有新模組產生時, 可以有系統, 有組織的規劃整體專案系統目錄, 不要到處散落, 請寫在CLAUDE.md及專案規格相關文件中落實! 記住此點」；附錄 C.1、§14）與掌舵者 2026-10-19 落點指令（SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md` 立案欄，sid `f3ead132-29b1-418c-97d9-35868ab11c70`）；OBS-SI-105（SSOT §5 自陳「沒有機械鎖」，再開待辦）。｜**憲法對照**：守衛面准入（本鎖是 `tools/tests/` 下的形態判準測試，不在守衛面清單、不是 hook，由掌舵者直接指令驅動；見 §3.2、附錄 B）；鐵律三；根 `CLAUDE.md`〈根層模組落點〉。落點規則本文只住 SSOT，本 FR 只規定它的機械鎖、不複寫規則；新增 `tools/tests/` 檔須付重釘稅（護欄層行數棘輪、compat-ci `paths`、CI paths 覆蓋鎖，同一個 commit 收齊；SSOT §4 第 3 點）。
- **AC-SI-34-1**（登記表↔磁碟）Given SSOT §3 登記表 When `tools/tests/test_root_module_layout.py` 解析 Then 每列「程式碼／入口／測試／資料」欄所列的 repo 內路徑（含萬用字元者以 glob 展開）在磁碟都至少命中一個檔；缺一＝紅並印列名與路徑；標明 repo 外（例：`~/autosdd_quota.json`）或「—」者不判；解析不到登記表或解析出 0 列＝紅（fail-loud，不得 0 列通過）。路徑片段的抽取規則（含無目錄前綴的檔名片段承繼同欄前一個帶目錄的片段）屬形態判準，已由 Architect 棒定（§9.1〈C19 判準〉），以現行 §3 全部列為正控（SSOT 須先依該判準修正一處，同節）、合成登記表刪一個路徑為負控。邊界型 **M**（形態判準）；誠實劃界：只驗路徑存在，不驗該路徑「該不該在那裡」。
- **AC-SI-34-2**（前綴散落）Given `tools/lib/` 的扁平 `.py` 檔 When 取檔名第一個底線之前為前綴，同前綴 ≥3 支（初值 3，先例＝SSOT §5 既有表述）且 `tools/lib/<prefix>/` 套件目錄不存在 Then 紅；存量以 shrink-only 名冊豁免（名冊住測試檔常數、初值＝〈C19 判準〉的現查值（`quota`、`skip`、`ledger`；實作輪重查）；只准縮、不准長；名冊內前綴若已成套件須自名冊移除，否則紅，防名冊腐爛）；新增檔使一個未入名冊的前綴達 3 支＝紅。邊界型 **M**（形態判準）；誠實劃界：只看檔名前綴，同一模組換前綴命名的散落看不見。
- **AC-SI-34-3**（套件須登記）Given `tools/lib/` 下每個含 `__init__.py` 的套件目錄 When 比對 SSOT §3 登記表 Then 每個套件名都出現在某一列的「程式碼」欄；未登記＝紅（先改 SSOT §3 再落檔，SSOT §4 第 5 點）。邊界型 **M**（形態判準）；誠實劃界：只驗「套件有登記」，不驗登記列內容正確（路徑存在由 AC-SI-34-1 驗）。
- **AC-SI-34-4**（新模組 PRD 須引 SSOT）Given `docs/01_requirements/*_PRD.md` 中含「模組落點表」字樣者 When 掃描 Then 該檔必含 SSOT 路徑 `docs/02_architecture/Root_Layout_and_Module_Placement.md`；缺＝紅。邊界型 **M**（形態判準）；誠實劃界：只判含該字樣的 PRD，不含字樣的新 PRD 看不見——其是否需要落點表由 SCG-0 檢查表第 1 點把關（SSOT §4）。

#### FG-J 研究掃描（P1）
##### FR-SI-30 研究掃描：限定來源、增量、有界、只產候選〔P1｜新建；接既有（FR-SI-02、研究方法論 SOP）〕
**追溯**：DP-09、DP-06；T1 2026-10-19 問題 1b1（原文「如每次研究外部網路(OPENAI/Claude Code等)前沿技術SOP(每次啟動驗進SOP,取得外部最新資訊)」；附錄 C.1、§14）；既有：研究方法論 SOP（深度重跑 S1～S8 仍只依 S7 症狀驅動，本 FR 不改該檔）、FR-SI-02（外部衍生隔離）。｜**憲法對照**：禁令 26（外聯，見附錄 B）；C-12、C-13；守衛面准入；鐵律四。
**定位（先讀）**：研究掃描是**運轉（RUN）內的擷取動作，不是啟動事件**——AC-SI-03-1 的 (a)～(e) 不變，它只綁 `RUN-SI-NNN`，不綁日曆、版本號或輪次（C-12）。研究者是 Sonnet 子代理，**只產 OBS 候選列**（`外部衍生=是; src=<id>`，主控單窗口入帳），不直接成為 PROP。**網路外聯只有 `si research --fetch`**（CLI 自抓來源表 URL 的原始位元組，D-1′，附錄 C.2 #16）；研究者沒有 Web 工具，只讀 CLI 落地的來源檔。名詞：「研究來源表」（運轉期、`research_sources.json`、僅 T1 增減）≠ SOP II-3 的 S-NN 文獻表（立案期、已完成）。
- **AC-SI-30-1**（研究事件必有）Given 一個運轉（`run.open` 之後） When 該運轉要產生任何 `prop` Then 同一運轉內須恰有一筆研究事件——`research.scan`（`si research --fetch`）或 `research.skip`（`si research --skip --reason <r>`），且其 `seq` 介於該 `run.open` 與該運轉第一筆 `prop` 之間：`si prop-new` 前置檢查在同運轉無研究事件時拒收（rc 1、印可貼入的 OBS 草稿列）；`si check`（P1 起）重放，有 `prop` 而無研究事件、或同運轉研究事件多於一筆者＝紅（附運轉號與 `seq`）。`research.skip` 的 `reason` 屬封閉集合：`quota-band`（`python tools/session_resume_planner.py --pace` 的 band 非 free，附當時 band 值）、`offline`（附一句現象）、`helmsman`（掌舵者明示免掃，附 `sid`＋`line` 座標；P1 只驗座標格式〔`sid` 為 UUID、`line` 為正整數〕，`si check` 印 NOT-EVALUABLE〔碼 `QUOTE-VERIFIER-NOT-ESTABLISHED`，nonblocking〕；引言回查於 P2 與 AC-SI-12-4 ⑤ 共用同一驗證函式，附錄 C.2 #16）；集合外的值或缺附註＝CLI 拒收。零 `prop` 的運轉（`no-event`，AC-SI-03-2）不受此檢查約束。邊界型 **M**（`prop-new` 前置檢查與 `check` 重放；`helmsman` 座標 P1 為 NOT-EVALUABLE、P2 起可回查，逐字稿取不到＝NOT-EVALUABLE）＋**P**（誠實劃界：`quota-band`／`offline` 是自述、無機械物可證，不得讀成「被擋」；偵測 **D**：`si status` 印本運轉與歷來免掃的原因分佈，資訊欄、不接閘門）。
- **AC-SI-30-2**（來源白名單）Given 研究來源表 `docs/06_quality/SelfImproving_Protocol/research_sources.json`（協定目錄；NFR-SI-02-1 (iii) 既有 glob `docs/06_quality/SelfImproving_Protocol/**` 已涵蓋、不另加 glob；僅經 T1 或 PRD 修訂增減；每筆 `id`〔`^[a-z0-9][a-z0-9-]{0,31}$`、唯一〕、`url`、`kind`〔`changelog`／`docs`／`release`／`blog`〕、`extract`〔一句：給研究者的閱讀指示，即讀該來源檔時要看什麼〕、`added_by`〔T1 座標〕；檔案格式見 §9.2） When `si research --fetch` 發出任何請求之前 Then 先驗來源表自身——欄位齊備、`id` 唯一、`kind` 在封閉集合、`added_by` 非空、`url` 以 `https://` 開頭且不含 userinfo、host 非私網／loopback／link-local（規則集沿 `AgentConsole/docs/02_architecture/Architecture.md` §8.4 的私網段清單，只驗字串形態），`si check`（P1 起）對同一份表跑同一個驗證函式；任一不符＝整次拒收（rc 1、不抓、不寫事件、印違規項）。請求只發給表內 `url`；重導向的目標 host 也須在表內（scheme 限 http／https、https 不得降為 http、至多 5 跳），否則該來源判失敗（`redirect-refused`）；研究者無 Web 工具、不經手網路。邊界型 **M**（`fetch.py` 的來源限定與 `check` 的表驗證；外聯面＝能力登記判準，§9.4）；誠實劃界：字串形態判準不證明 URL 可達或內容可信（可達性由首跑驗，內容真偽見 AC-SI-30-4）；不做 DNS 解析後驗 IP（沿 Architecture §8.4 的誠實劃界；來源表僅 T1 增減、host 為廠商網域）；來源表本身可被有寫入權者改動，只留 git 可見性（`added_by` 非空由 `check` 驗，不證明 T1 真有其事，**P**）。
- **AC-SI-30-3**（增量 digest；D-1′，附錄 C.2 #16）Given `si research --fetch --run RUN-SI-NNN` When 執行 Then CLI 依序（不併發）對來源表每個來源，以標準庫 `urllib.request` 取得其 `url` 的**原始位元組**：只准 http／https；不帶 cookie、token 或任何認證標頭；`User-Agent` 為固定字串；`Accept-Encoding: identity`（回應帶其他 `Content-Encoding`＝該來源失敗）；整個來源的牆鐘 ≤ `RESEARCH_TIMEOUT_SECONDS`、位元組 ≤ `RESEARCH_BYTES_MAX`（超界即中止、不截斷）；`Content-Type` 須是文字類（`text/*`、`application/json`、`application/xml`、`application/atom+xml`、`application/rss+xml`、`application/xhtml+xml`），缺或不符＝失敗；只收最終狀態 2xx。成功的來源以原始位元組算 `sha256`（不做任何正規化），原樣寫入家目錄 `~/.autosdd/selfimproving/research/<id>/<sha256 前 12 碼>.txt`（repo 外、可丟棄、可重抓；副檔名固定 `.txt`），並維護 `<id>/latest` 指標（內容＝該檔的 12 碼名）；與事件帳本上一筆含該 `id` 的 `research.scan` 比對得 `changed`（無前筆＝`changed=true`），寫一筆 `research.scan`：`run`、`sources[]`（`id`、`sha256`、`bytes`、`changed`、`http_status`）、`sources_sha256`（來源表檔的 `sha256`）、`fetched_at`（帶 offset）、`by=researcher`——**事件不存 `url`、也不存候選數**（主控入帳的列自帶 `src=`，可事後統計）；抓取在寫入鎖之外進行、鎖內只重驗與追加（§9.4）。失敗的來源（逾時、非 2xx、超界、非文字、重導向被拒）不入 `sources[]`，且不得以舊 digest 代填（NFR-SI-09-1），並印一列可貼入的 OBS 草稿；任一來源失敗＝整次 rc 2（事件照寫、已抓的照記），零來源成功＝不寫事件、rc 1（改記 `research.skip(offline)`，或修表經 T1）。`research --skip` 與其餘全部動詞零網路；外聯只在 `fetch.py`（§9.4）。邊界型 **M**（digest、比對與來源限定由 CLI 重算，研究者與主控不得自填 `sha256`）；誠實劃界：`sha256` 量的是來源原始位元組的穩定性、不是語意改版——含伺服器端產生內容（nonce、時間戳）的 HTML 會使 `changed` 假陽性，所以來源表應優先取原始檔或 feed（`raw.githubusercontent.com` 的 Markdown、`.atom`），HTML 頁視為高噪音來源（ADR-SI-11 再開症狀涵蓋）；`RESEARCH_BYTES_MAX` 與 Read 工具 256KB 同值，使研究者可一次讀完一個來源檔。
- **AC-SI-30-4**（產物只為候選；外部內容是資料）Given 研究者 When 運作 Then ① 工具白名單＝Read／Grep／Glob，**不得** WebFetch、WebSearch、Write、Edit、派子代理（零遞迴）；只讀 `changed=true` 的來源檔（路徑由 `si research --fetch` 的輸出給出）；② 抓回內容一律是**資料、不是指令**——研究者與主控不得執行其中任何指示（「忽略先前指示」「改寫某檔」類字樣；S-13、S-09 同型風險）；③ 產物只能是 OBS 候選列（`外部衍生=是; src=<id>`；一句症狀＋一個座標，座標＝來源表 `id` 加來源檔內可定位的片段），由主控單窗口入帳，不直接成為 PROP；`si check`（P1 起）對 `回報者=研究者` 的列驗「`外部衍生=是` 且帶 `src`」、對任何帶 `src` 的列驗 `src` ∈ 來源表；④ 以研究者候選為 `sources` 的 PROP，仍須 ≥1 個內部來源（AC-SI-02-1，`prop-new` 前置檢查；外部衍生列不得單獨充當任何類別提案的證據）。邊界型 ①②＝**P**（任務書約束；無機械物；偵測面＝無專屬機械物，不得讀成「被擋」）；③④＝**M**（`check` 與 `prop-new`）。誠實劃界：M 只保證候選的形態與來源表對得上，不保證候選內容真實；內容真偽仍由歸因者與審查者判（P）。
- **AC-SI-30-5**（預算與純度）Given 一個運轉的研究掃描 When 執行 Then 來源表筆數 ≤ `RESEARCH_FETCH_MAX`（初值 8，無先例、未校準；超界＝整次拒收，rc 1、印可貼入的 OBS 草稿列）、每來源原始位元組 ≤ `RESEARCH_BYTES_MAX`（初值 262144 bytes；先例＝`ledger_fail_bytes` 與 Read 工具 256KB 同值，NFR-SI-08-1；超界來源判失敗、不截斷，因截斷會讓 digest 偽穩定）、每來源牆鐘 ≤ `RESEARCH_TIMEOUT_SECONDS`（初值 20 秒，無先例、未校準；中止後判失敗）；三參數登記於 `params.json`（`research_fetch_max`、`research_bytes_max`、`research_timeout_seconds`；頂層鍵依位元組序，P1 實作輪同步加入 `PARAM_SPECS`）；研究者每運轉至多一個、零遞迴；派工前 `--pace` 現查（NFR-SI-07-2）；CLI 抓取不是 harness 的 Web 工具呼叫，額度守衛對 Web 工具的節流不牽制它（OBS-SI-005 的節流成本隨之消失），牆鐘上界＝來源數×`RESEARCH_TIMEOUT_SECONDS`＋研究者讀檔時間。邊界型 **M**（預算由 CLI 拒收或判失敗）＋**P**（研究者讀檔的 token 預算＝任務書宣告、超出必揭露，NFR-SI-07-3）；誠實劃界：研究者讀檔的牆鐘無機械物量測。
- **AC-SI-30-6**（來源表變更不改指標指紋）Given 研究來源表住協定目錄，而 `check` 的判準指紋 manifest 現行對協定目錄全部檔雜湊（`tools/lib/selfimproving/params.py` 的 `fingerprint`） When T1 增減來源 Then M1～M5 的判準指紋不變（來源表不是指標定義；否則每次增減來源都使既有指標數字不得並列，AC-SI-22-2）：指紋 manifest 須排除 `research_sources.json`，P1 實作輪改碼並以測試釘住（正控＝改來源表→指紋不變；負控＝改 `params.json` 或 `metrics.md`→指紋變）。邊界型 **M**；誠實劃界：排除清單只涵蓋 `research_sources.json` 一個檔名，協定目錄再增非指標資料檔時須同步擴充；採用此案（附錄 C.2 #16；已否決的替代方案＝接受「來源表變更＝指紋換代」並把 AC-SI-22-2 的並列限制寫進 T1 增減來源的流程）。

**初始研究來源表（提案值）**：本稿作者未上網、未開頁，每筆 `url` 皆「未驗，研究者首跑驗」，不宣稱任何頁面存在；`added_by` 值＝T1 座標 sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13；首跑結果以 OBS 候選列回報，來源表的修正經 T1。D-1′ 後 CLI 取的是原始位元組：HTML 頁含伺服器端產生內容時 `changed` 恆為真，故兩個 GitHub 來源改取原始檔與 feed 網址（仍未驗）；首跑若見其餘 HTML 來源同型，經 T1 改網址。

| `id` | `kind` | `url`（未驗） | `extract`（給研究者的閱讀指示） |
|---|---|---|---|
| `cc-changelog` | changelog | `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`（未驗；原始 Markdown） | 最新 5 個版本的編號與各版首行（逐字，不改寫） |
| `cc-docs-memory` | docs | `https://code.claude.com/docs/en/memory`（未驗；SOP II-3 S-08 的 URL） | 頁面標題清單＋含數字上限的句子（逐字） |
| `cc-docs-hooks` | docs | `https://code.claude.com/docs/en/hooks-guide`（未驗；SOP II-3 S-10 的 URL） | 標題清單＋事件名清單（逐字） |
| `cc-docs-skills` | docs | `https://code.claude.com/docs/en/skills`（未驗；SOP II-3 S-09 的 URL） | 標題清單＋frontmatter 欄位名清單（逐字） |
| `anthropic-engineering` | blog | `https://www.anthropic.com/engineering`（未驗） | 最新 5 篇文章的標題與日期（逐字） |
| `openai-api-changelog` | changelog | `https://platform.openai.com/docs/changelog`（未驗） | 最新 5 筆變更的日期與標題（逐字） |
| `openai-agents-releases` | release | `https://github.com/openai/openai-agents-python/releases.atom`（未驗；Atom feed） | 最新 5 個 release 的編號與日期（逐字） |

#### FG-K 模組體檢（P1）
##### FR-SI-31 模組體檢：`si scan`＋唯讀體檢子代理〔P1｜新建；唯讀量測器接既有〕
**追溯**：DP-08；T1 2026-10-19 問題 1a（原文「可以自行檢討AutoClaude, AISDLC_SDD, AgentConsole,SelfImproving等現有模組是否還有需要改進的地方與BUG!」；附錄 C.1、§14）；既有：`tools/probe/misstep_attribution.py`、`tools/probe/audit_session.py`（只量不閘）、缺陷帳本家族、`si status`（C14）。｜**憲法對照**：12-Rule Rule 5（確定性部分進 CLI、需判斷的部分交子代理）；C-13（零發現不是 PASS）；鐵律四；守衛面准入。
**定位（先讀）**：確定性彙整＝`si scan`（無狀態、不寫事件）；需判斷＝唯讀 Sonnet 子代理依下表逐模組檢；兩者產物都只是 OBS 候選，由主控入帳。體檢按需執行、不綁運轉，也不是啟動事件（AC-SI-03-1 不變）。**模組體檢入口表**（Operations SOP 歸因者節的體檢任務書範本於 P1 定稿時照抄本表；只列「先讀什麼」，不列判準）：

| 模組桶 | 先讀（權威指引） | 缺陷與未結座標（唯讀） | 品質基線與量測（只讀既有輸出；不重跑全套、不加 `--fix`、不重跑探針） |
|---|---|---|---|
| AutoClaude | `AutoClaude/CLAUDE.md`（含 `[Architecture Snapshot]`） | 缺陷帳本 `docs/06_quality/AutoSDD_Defect_Log.md` 中路徑含 `AutoClaude/` 的未結列；`AutoClaude/docs/06_quality/` | 測試基線數字唯一出處＝根 `ONBOARDING.md` §7；`python AutoClaude/tools/check_loc_budget.py --json`；`ruff check --no-cache <入口檔>`（整棵樹存量債另案，根 `CLAUDE.md`〈測試／Lint〉） |
| AISDLC_SDD | `AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD/FRAMEWORK_STATUS.md`（版本與資產計數唯一出處） | 缺陷帳本路徑含 `AISDLC_SDD/` 的未結列；軌道②帳本 `SDD_improving_Automation_NN.md`（路徑見根 `CLAUDE.md`〈三條改進軌道〉）；LATEST 現查 `python AISDLC_SDD/scripts/sdd_version.py` | `build/reports/` 下已存在的 pytest／ci-gate 輸出（沒有就記「量不到」，不重跑） |
| AgentConsole | `AgentConsole/CLAUDE.md`、`AgentConsole/docs/02_architecture/Architecture.md` §12（已知限制與待驗證項） | `AgentConsole/docs/06_quality/RTM.md` 的未結列、`AgentConsole/docs/04_planning/Implementation_Plan.md` 進度帳；缺陷帳本路徑含 `AgentConsole/` 者 | 各服務既有測試輸出（若在；Gradle／vitest／pytest 不重跑） |
| 根層 | 根 `CLAUDE.md`、`docs/02_architecture/Root_Layout_and_Module_Placement.md` | 缺陷帳本主列、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md`（皆在 `docs/06_quality/`） | 既有探針輸出檔（例：`misstep_attribution` 的 jsonl；若在） |
| SelfImproving | `docs/01_requirements/SelfImproving_PRD.md`、`docs/05_development/SelfImproving_Operations_SOP.md` | `docs/06_quality/SelfImproving_Observation_Ledger.md` 中處置為 `open`／`deferred` 的列（再開症狀是否成立）；`si status` 的待決 PROP／SUSPENDED／冷卻 | `python tools/selfimproving.py check`、`python tools/selfimproving.py scan`（皆唯讀） |

- **AC-SI-31-1**（唯讀離線）Given 任一 repo 狀態 When 執行 `python tools/selfimproving.py scan` Then 零副作用（不寫任何檔、不寫事件帳本、不呼叫寫入型 git 形態）、不連網、只用標準庫（沿 P0 TCS `AC-030-2` 的純度；唯一子行程是環境被淨化的 `git`）、沒有任何接受筆數、日期或排程的旗標（唯一的窗口旗標 `--since <commit>` 只收 commit，不收日期、筆數或相對寫法，§9.3）；執行前後正式面 `git status --porcelain` 與 HEAD 逐字相同。邊界型 **M**（以前後對照與斷網夾具自證）；誠實劃界：「零副作用」以正式面 `git status --porcelain`／HEAD 與斷網夾具驗，不涵蓋 `.git` 內部檔（例：git 對 index 的機會式刷新）的位元組不變。
- **AC-SI-31-2**（候選有座標）Given `scan` 讀到的本地證據（只讀已存在於磁碟者、不重跑任何量測器）：(i) 缺陷帳本新立（自最近一筆 `run.close` 的 `t` 起；無 `run.close` 者自 `migration_base_sha` 的 committer 時間起；帶 offset 的時刻比較，日精度的 DEF 列以發現日期對該時刻的 UTC 日期比較、早於者排除、同日者納入，沿 §1.3〈M1 判定細則〉的錨規則）P≤2 未結列（即啟動事件 (c)）；(ii) 同窗新增的 OBS 列與 commit（依路徑歸五模組桶，AC-SI-31-4）；(iii) 事件帳本折疊出的待決 PROP／SUSPENDED／冷卻（狀態摘要區，不是候選）；(iv) `build/reports/` 下已存在的測試與 CI 產物；(v) 既有探針輸出檔（例：`misstep_attribution` 的 jsonl） When 印 OBS 候選草稿列 Then 每列＝九欄格式（ID 取帳本現查的下一個可用號、時間帶 offset、一句症狀、**≥1 個座標**〔TCS P0 R16 九形態之一〕、分類、嚴重度、處置 `open`、標記含 `面`、`來源=工具`、`回報者=scan`），單列 ≤ `ROW_MAX_BYTES`、自身通過 `check` 的列規則（零 finding，同 P0 TCS `AC-030-3` 草稿列判準）；無座標的候選不印；草稿不寫入帳本（主控單窗口入帳）。邊界型 **M**（草稿列自驗）；誠實劃界：候選是啟發式（路徑歸桶、P≤2 未結）而非缺陷判定，是否為真缺陷由歸因與人審決定；DEF 解析器與 C11 共用同一實作（ADR-SI-05）。
- **AC-SI-31-3**（零候選＝無事件；量不到不併入）Given `scan` 的每個證據來源 When 輸出 Then 每個來源各印一行（`讀到 N 筆`／`量不到：<原因>`）；零候選時整體印「無事件」（JSON `status:"no-event"`），**不得**印成通過、達標或綠；任一來源量不到時整體改印「無事件（K 個來源量不到）」，不得把量不到併入零（NFR-SI-09-1）；候選數只印在資訊欄（§1.3.1）；`scan` 不接任何閘門 rc（執行成功＝rc 0、無法執行＝rc 3，沿 `check` 的 rc 3 語意）。邊界型 **M**；誠實劃界：「量不到」只報告 `scan` 自己讀不到的來源，讀得到但內容殘缺（例：被截斷的輸出檔）看不見。
- **AC-SI-31-4**（模組歸桶）Given 候選涉及的路徑 When 歸桶 Then 依序判定：SelfImproving（`tools/lib/selfimproving/**`、`tools/selfimproving.py`、`tools/probe/selfimproving_*`、`tools/tests/test_selfimproving_*`、檔名含 `SelfImproving` 的 `docs/**`）→ AutoClaude（`AutoClaude/**`）→ AISDLC_SDD（`AISDLC_SDD/**`）→ AgentConsole（`AgentConsole/**`）→ 根層（其餘 repo 內路徑）；不屬任何桶者歸「未分類」並計數、不丟棄；先判 SelfImproving 是因其檔案落在根層路徑下（SSOT §3）。邊界型 **M**（形態判準：路徑前綴）；誠實劃界：觸及多個桶的 commit 依其觸及的每個路徑各歸一次。
- **AC-SI-31-5**（體檢子代理）Given 模組體檢任務書（Operations SOP 歸因者節新增的範本，內容＝上表） When 派出體檢子代理 Then 單一 Sonnet 子代理、依入口表逐模組檢（不並行扇出、零遞迴）、工具＝Read／Grep／Glob／PowerShell（只准唯讀指令；不得 Write／Edit，不得跑會改狀態的指令，含全套測試、`--fix`、寫入型 git 形態、重跑探針）；交卷＝文字：候選 OBS 列（一句症狀＋一個座標，無座標不入帳）＋〈流程摩擦〉節；主控入帳（單窗口）；候選列數不設門檻（§1.3.1），超出任務書宣告的 token 預算必揭露（NFR-SI-07-3）；體檢前後主控對照正式面 `git status --porcelain`／HEAD。邊界型 **P**（任務書約束，無機械物）＋**D**（前後對照偵測）；不得讀成「被擋」；誠實劃界：前後對照看不見被 `.gitignore` 忽略的檔案（例：快取、`build/`）的寫入。

#### FG-L Console 面（P1b／P2b）
##### FR-SI-32 Console 唯讀鏡像：`si export`＋Bridge `/si/*`＋backend 代理＋frontend 頁〔P1b｜新建；接既有（AgentConsole Architecture 體例）〕
**追溯**：DP-04；T1 2026-10-19 問題 1c（原文「自我精進帳本系統化統一管理, 可以由AgentConsole UI介面管理」；附錄 C.1、§14）；§3.3 F-SI-101 再開（其再開症狀「掌舵者要求在 Console 內審提案」已實際發生）；既有：`AgentConsole/docs/02_architecture/Architecture.md` §3（目錄地圖）、§5.1（路由樹）、§5.2（四區塊）、§8（安全與角色）、§10／§10.1／§10.2（Bridge 契約：唯一消費者是 console-api；SDD 寫入面不變量）、§11（後端 API：`/api/v1/**`、camelCase、狀態碼語意）。｜**憲法對照**：禁令 1（本 FR 不碰 FSM）；C-15（Console 簽核硬閘、FSM 只讀）；守衛面准入；鐵律四。
**定位（先讀）**：Console 是**顯示面、不是資料來源**——頁面資料＝`si export` 的輸出（單一真相＝git 內帳本）；P1b **零寫入端點**。端點命名沿 Architecture §10 體例：Bridge `GET /si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/{id}`、`/si/runs`（對應 `export --kind status`／`observations`／`events`／`proposals`／`runs`）；backend `GET /api/v1/si/**` 逐一代理；frontend 新頁 `/self-improving`（狀態橫幅取 `status` 的事件與待決、觀察／提案／事件三分頁、待決 PROP 的卡面**逐字**顯示 `si card` 輸出；導航入口只改 `ToolsRegion.tsx`，Architecture §5.2 硬規則 2）。端點、DTO 欄位、分頁與 `since` 參數、`SI_ROOT` 設定項（沿 `SDD_ROOT` 體例）與檔名已由 Architect 棒定（§9.1 C18、§9.3、§9.7 FC-a～FC-d）。**落點與持有面**：`export` 動詞住根層 `tools/`，而 `AgentConsole/CLAUDE.md` 鐵律 7 禁其開發 agent 動 `tools/`，故 AC-SI-32-5 由根層鍵交付、AC-SI-32-1～32-4 在 AgentConsole 鍵（附錄 C.2 #12，⚖6 已採用）；本 FR 的追溯另落根層 RTM（`docs/06_quality/RTM-SelfImproving-<Phase>-<日期>.md`，SSOT §2），不往 `AgentConsole/docs/06_quality/RTM.md` 的計數列加列（該檔有「US 58」與 PRD 對帳；Architect 棒查證：該對帳是 RTM.md §3.4 的人讀現查指令、無程式碼讀它，可容納 AgentConsole 側的本地編號子表〔先例 RTM.md:469，ID 加反引號故不計入總列數〕；根層 RTM 仍是 FR-SI 追溯主載體，§9.7 FC-c）。
- **AC-SI-32-1**（差分）Given 任一時刻的帳本與事件帳本 When 開 `/self-improving` 或呼叫 `GET /si/*`、`GET /api/v1/si/**` Then 頁面與回應的每個資料欄，與同一時刻 `python tools/selfimproving.py export --json --kind <k>` 輸出的對應欄逐欄相同（欄名只經 snake_case↔camelCase 對映；`generated_at` 是呼叫時刻、不參與比對）；待決 PROP 的卡面**逐字**＝`si card` 的輸出（`export --kind proposals` 的卡面欄由同一函式產生，Bridge、backend、frontend 皆不另渲染、不重排行；AC-SI-14-2 同構）；Bridge、backend、frontend 不重算判準（不重折疊事件、不重算 digest、不重判 NE）。差分測試＝正控（一致）＋負控（追加一筆帳本列後頁面隨之改變且仍與 CLI 一致）。邊界型 **M**；誠實劃界：差分只證明頁面＝`export` 輸出，不證明 `export` 的折疊邏輯正確（後者由 P1 核心的 `status`／`card`／`check` 測試承擔）。
- **AC-SI-32-2**（唯讀）Given 任意 Console 操作序列（含全部分頁、篩選、重新整理與直接呼叫端點） When 結束 Then 正式面 `git status --porcelain` 與 HEAD 前後逐字相同、`~/.autosdd/selfimproving/` 無新增檔；P1b 的 `/si/**`、`/api/v1/si/**` 沒有任何非 GET 方法（POST／PUT／PATCH／DELETE 回 404 或 405）；Bridge 原始碼不含以寫入模式開啟 SI 帳本路徑、不 import 根層 `tools/lib`（AST 鎖，先例：Bridge 不得開寫 `FSM-STATE-*.yaml` 的 AST 測試，Architecture §10.2「寫入只經 CLI」列）。邊界型 **M**；誠實劃界：AST 鎖是形態判準（`getattr` 與動態開檔看不到），唯讀斷言只涵蓋測試所用的操作序列。
- **AC-SI-32-3**（fail-loud）Given SI 不可用（`tools/selfimproving.py` 不存在、子行程逾時或 rc 非 0、輸出非合法 JSON、`SI_ROOT` 未設、未掛載或不含 `tools/selfimproving.py`、輸出的 `schema_rev` 不是 Bridge 釘住的值） When 請求任一 `/si/*` Then Bridge 回 503 `si_unavailable`（`detail` 逐字帶 rc 與 stderr 末段；先例：`engine-bridge/app/routers/sdd.py` 的 503 `sdd_unavailable`），backend 把原因逐字轉出（Bridge 不可達或逾時沿 Architecture §11.1 的 502／504），frontend 顯示錯誤態與原因；**不得渲染空表、零筆或過期快取當作正常**；子行程環境缺件（容器內無 `.git`、無逐字稿、無家目錄；NFR-SI-06-6）使某欄量不到時，該欄回 NOT-EVALUABLE 並顯示，不省略欄位。邊界型 **M**（Bridge／backend 測試與 frontend 元件測試，各以注入失敗為負控）；誠實劃界：只涵蓋所列失敗形態，子行程輸出「合法 JSON 但已過期」（例：帳本被另一視窗改動後的短暫不一致）不在偵測範圍，回應帶 `head_sha` 供人對照。
- **AC-SI-32-4**（需登入）Given 未帶有效 JWT When `GET /api/v1/si/**` Then 401；Viewer 以上角色可讀（沿 Architecture §8.2 的「讀取」列）；Bridge 的 `/si/*` 不對任何使用者開放、唯一消費者是 console-api，瀏覽器不直連 Bridge（Architecture §10.1「消費者」列）；`/self-improving` 頁在未登入時導向登入（沿 `login/page.tsx`，Architecture §5.1）。邊界型 **M**（backend 安全測試）＋**P**（誠實劃界：Bridge 無認證、只准 backend-net，Architecture §12.1 L-6：對 host 發布 8081 視為缺陷，無機械物；本 AC 的 M 只涵蓋 backend 的 JWT 與角色）。
- **AC-SI-32-5**（`export` 動詞；根層半）Given `python tools/selfimproving.py export --json --kind {observations|events|proposals|runs|status}` When 執行 Then 唯讀、離線、只用標準庫（沿 P0 TCS `AC-030-2` 的純度；唯一子行程是環境被淨化的 `git`）；輸出單一 JSON 文件（頂層 `schema_rev`、`kind`、`generated_at`、`head_sha`、`items[]`，其餘見 §9.2）；`--kind` 為封閉集合，其餘值 rc 3；與 `status`／`card`／`check` 共用同一組折疊與卡面函式（不得有第二份實作）；分頁參數 `--since`／`--limit` 形狀見 §9.3。自證：前後 `git status --porcelain` 相同；斷網夾具下輸出不變。邊界型 **M**；誠實劃界：「共用同一組函式」只由匯入關係與差分測試（AC-SI-32-1）間接驗證（形態判準）；階段：根層半隨 P1 核心鍵交付、於 P1 出口 (h) 驗收（附錄 C.2 #12，⚖6 已採用）。

##### FR-SI-33 Console 決定載體（DEC 的第二種載體）〔P2b｜新建；接既有（Console 簽核硬閘、FR-SI-12）〕
**追溯**：DP-04；T1 2026-10-19 問題 1c；ADR-SI-03（再開）；既有：Architecture §8.2（RBAC）、§8.6（審計）、§10.2（寫入面不變量：`X-Bridge-Token`、子行程 CLI、動詞白名單）、`AgentConsole/CLAUDE.md`:15（寫入一律經 CLI 子行程）。｜**憲法對照**：禁令 11、12（人工 K=1，不得自動採納）；C-15；鐵律四。本 FR 寫需求與 AC 的形狀，機制細節見 ADR-SI-03′；**驗證設計（Console 路徑沒有逐字稿，AC-SI-12-4 的引言回查在此如何對應）已由 Architect 棒於 ADR-SI-03′ 裁決（§9.5；附錄 C.2 #16）**：稽核 JSON＋HMAC＋主機端 CLI 入帳；其中兩點待主控確認，確認前 P2b 不開工。
- **AC-SI-33-1**（載體）Given Console 為 DEC 的第二種載體（第一種＝逐字稿） When 掌舵者在 Console 對一張待決 PROP 下決定 Then 仍須符合 §7.2 動詞表（動詞、ID 綁定、前提不變；「必填理由」以必填欄位表達）、綁該卡面 digest、預設拒絕、無「全部核准」（AC-SI-12-1、12-3）；決定資格＝Architecture §8.2 的 Admin 角色**且**帳號名在 `console.si.deciders`（環境變數 `CONSOLE_SI_DECIDERS`，逗號清單，預設空＝無人可決；K=1，不開放代決）；console-api 產稽核 JSON 並以專用金鑰簽 HMAC-SHA256，Bridge 驗 `X-Bridge-Token` 後只把它原樣寫入稽核目錄、自身不開寫帳本檔且不呼叫任何寫入型 CLI 動詞（未設權杖＝503 `si_write_disabled`，沿 Architecture §10.2 權杖列）；成立的決定由主機端 `si decide --carrier console --audit-ref <id>` 驗證後於寫入鎖內寫入 `dec` 事件，帶 `carrier=console`、`audit_ref`、`audit_sha256`、`key_id`（取代 `quote`／`sid`／`line`；缺 `carrier` 欄者視為 `transcript`，舊事件不改）；`AUTOSDD_UNATTENDED` 有設時一律非零 rc。`si decide`、`si check`、`si promote` 對 `carrier=console` 的 `dec` 以同一個驗證函式回查稽核檔（ADR-SI-03′）：`audit_sha256`、PROP、digest、動詞、決定者、時間逐欄相符，金鑰在場再驗 HMAC；稽核檔不存在（他機）或缺金鑰＝NOT-EVALUABLE，`promote` 因無法回查而拒（fail-closed）；同一 `audit_ref` 不得二次入帳。邊界型 **M**（backend RBAC 與白名單、Bridge 權杖、CLI 驗證函式）；誠實劃界：HMAC 金鑰在主機環境，持有它的行程（含主控）可鑄造合法稽核檔，所以偽造偵測弱於逐字稿載體；獨立證據是 Console DB 稽核列（AC-SI-33-2）。
- **AC-SI-33-2**（稽核列與對帳）Given 一次 Console 決定 When 記錄 Then console-api 於伺服器端同時寫（a）稽核 JSON（使用者、角色、時間〔帶 offset〕、PROP、digest、`dkind`、理由、`audit_ref`；沿 Architecture §8.6「審計」結構化 JSON 日誌體例，簽名對象＝`body` 字串的位元組、不重新序列化）與（b）Console DB 新表 `si_decisions` 的同型列（Flyway 新版本；`audit_ref` 為主鍵）；稽核檔與 `dec` 的 PROP、digest、動詞逐欄相符由 CLI 驗證函式與 Console 側測試對帳；Console 頁對每筆 `carrier=console` 的 `dec` 比對 `si_decisions`：有 `dec` 而無對應列＝紅色警示，已送出而尚無 `dec`＝「待入帳」。邊界型 **D**（事後對帳）；誠實劃界：`si_decisions` 在 PG 容器內，repo 內的 `si check` 看不到它，對帳只在 Console 側與持有該伺服器的機器上成立。

**🔴 人機協作確認點**（§5 整體）：[ ] FR／AC 與 T1 原文五點及 2026-10-19 修訂四問一致（§14、附錄 C.1）　[ ] 每條 FR 皆有 DP 或既有機制追溯（附錄 A）　[ ] 每條 FR 皆有憲法對照且無違反（附錄 B）

## 🔧 6. 非功能性需求 (Non-Functional Requirements)
> 📋 **ID 命名規範**: `NFR-SI-NN`，子項 `NFR-SI-NN-M`。數值皆為「初值（未校準）」，先例座標附於欄內，調整屬不可進化面。

### NFR-SI-01: 有界停機（每階段預算與停機條件）
| 階段 | 上界（初值） | 停機條件 | 超界動作 |
|------|-------------|---------|---------|
| 觀察擷取 | 純文字寫入、零扇出；單列 ≤ `ROW_MAX_BYTES`（先例 700） | 單列超長 | 拒收並要求縮寫，長內容搬附註檔留座標 |
| 研究掃描 | 每運轉至多 1 個研究者、零遞迴；來源表筆數 ≤ `RESEARCH_FETCH_MAX`、每來源原始位元組 ≤ `RESEARCH_BYTES_MAX`、每來源牆鐘 ≤ `RESEARCH_TIMEOUT_SECONDS`；研究者無 Web 工具 | 超界或逾時 | 來源表筆數超界＝整次拒收（rc 1）；來源超界或逾時＝該來源判失敗（不截斷、不入 `sources[]`，整次 rc 2），已抓的照記；整次免掃須記 `research.skip` 並附原因（AC-SI-30-1） |
| 體檢 | 1 個唯讀子代理＋`si scan`；零扇出、零遞迴；讀取面限體檢入口表 | 超出任務書宣告預算 | 交已完成部分並揭露，不猜（FR-SI-31） |
| 歸因 | 單一歸因者；讀取面限帳本＋證據座標；不上網 | 超出任務書宣告預算 | 記 `NONE`（無法歸因），不猜 |
| 提案生成 | ≤ `MAX_PROPOSALS_PER_RUN`（3）；每提案修訂 ≤ `MAX_REVISIONS`（2；先例 `MAX_PATCH_PER_AC=2`、範本「至多二審」）；零遞迴 | 任一超界 | 停止並升級人工；修訂超限＝否決並入冷卻 |
| 人工閘 | 無逾時自動核准（預設拒絕）；待決不計時 | — | 待決提案不阻塞觀察擷取 |
| 沙盒套用 | 牆鐘與回合依提案宣告（先例 `step_timeout_seconds` 600）；零扇出 | 超界或沙箱 hang | 收 verdict（FAIL／NE），不等待（禁令 26） |
| 驗證 | 一審＋一次複驗（至多二審）；每次重跑 ≤ 2 | 超界 | 判 NE 並升級人工 |
| 量測／退役 | 量測腳本零 token；窗以事件關閉（FR-SI-23）；退役與提案共用 `MAX_PROPOSALS_PER_RUN` | — | — |
| 整體 | 劣化暫停 `STOP_AFTER_BAD`（2）；抖動 `CHURN_MAX`（2） | 觸發 | SUSPENDED／升級；僅掌舵者恢復 |

context 三段水位與額度四道門檻一律現查（`python tools/session_resume_planner.py --check`、`python tools/lib/quota_policy.py --print-env-example`），本文不複寫百分比。

### NFR-SI-02: 安全（守衛面與受保護路徑）
- **NFR-SI-02-1 不可進化面（唯一真相源）**：(i) agent 指令與憲法檔：根／`AISDLC_SDD`／`AutoClaude`／`AgentConsole` 的 `CLAUDE.md`、`maturity: active` 的 `governance/rules/R-*.yaml` 規則本體；(ii) 守衛面：各層 `.claude/**`（含 hooks、`settings*.json`〔含 permissions.allow〕、skills）、根 `CLAUDE.md`〈守衛面准入〉所列 `tools/lib/` 檔與 `tools/session_resume_planner.py`；(iii) 評估與協定：`evaluator_command`、`knowledge/held-out-corpus/`、評分權重常數、`docs/06_quality/FiveQuestion_Audit_Protocol/`、範本〈🏁〉、量測腳本與指標定義；(iv) 迴圈自身：本 PRD 與 SI 全部文件、帳本與提案目錄、預算／閘門／停機參數、狀態機、角色任務書範本、SI 腳本；(v) 凍結版本與模板：`AISDLC_SDD` 的非 LATEST 版本目錄（只有 LATEST 可原地改，根 `CLAUDE.md`〈路徑陷阱〉；**所有提案類別適用，不只 R 類**）與 `docs_template/` 模板（模板不可直接改，`AISDLC_SDD/CLAUDE.md` Rule 3）。「不可進化」＝不得成為任何 PROP 的 `target` 或 patch 觸及路徑；SI CLI 自己對事件帳本與 `SelfImproving_Proposals/` 的追加／新建寫入是運轉紀錄、不是提案套用，不受此限（只准追加／新建，改寫由 AC-SI-08-4 偵測）。機器可讀 SSOT＝`docs/06_quality/SelfImproving_Protocol/params.json` 的 `non_evolvable_globs`；`si prop-new`、`si promote` 讀它，散文與 JSON 不一致＝`si check` 紅。
  - **錨定語意**（SCG-0 一審 F-01）：glob 相對 repo 根（`git rev-parse --show-toplevel` 的 realpath），分隔符先正規化為 `/`；`**` 可吃零段至多段；**不帶 `**/` 前綴者只錨定 repo 根**（例：根錨定的 `.claude/**` 管不到 `AutoClaude/.claude/` 與 `AISDLC_SDD/AISDLC_SDD_v*/.claude/`——修復當下現查 `git ls-files`：tracked 的 `.claude/` 目錄共 33 處＝根、`AutoClaude/`、`AISDLC_SDD/` 與 `AISDLC_SDD/AISDLC_SDD_v*/` 各版，根錨定只涵蓋其中 1 處，故守衛面一律寫 `**/.claude/**`）；比對對象是 patch 內**每一條**路徑（AC-SI-07-3），先 `realpath`（解符號連結）再 `normcase`＋`casefold`（NTFS 與 macOS APFS 預設皆大小寫不敏感，而 `posixpath.normcase` 不改大小寫；repo 已以 `tools/check_ntfs_paths.py` 禁止僅大小寫相異的 tracked 路徑，故不致誤殺）；路徑逃出該類別的合法根（M 類＝邏輯根 `memory/`；其餘＝repo 根）視同命中。
    <!-- 機械消費：下一行（NFR-SI-02-1 的 glob 清單段，粗體標籤為「實體」空格「glob」）由 tools/lib/selfimproving/params.py 的 required_globs 讀取：取本檔首個含該粗體標籤的行，其中前綴為「、」「；」或 (i)～(v) 標籤的反引號片段，連同根 CLAUDE.md「守衛面＝」行的大括號展開，必須等於 params.json 的 non_evolvable_globs；改動下一行須同步 params.json 並重跑 python tools/selfimproving.py check（項目 params.globs）。本行是註解、不得含該粗體標籤。 -->
  - **實體 glob**：(i) `**/CLAUDE.md`；`AISDLC_SDD/*/governance/rules/R-*.yaml` 中**既有且 `maturity: active`** 者（新增的 `trust_level: proposed` 候選檔不在此列，由 `si prop-new` 讀檔判定）；(ii) `**/.claude/**`、根 `CLAUDE.md`〈守衛面准入〉所列 `tools/lib/` 檔、`tools/session_resume_planner.py`；(iii) `docs/06_quality/FiveQuestion_Audit_Protocol/**`、`AISDLC_SDD/*/knowledge/held-out-corpus/**`、`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`、`tools/probe/selfimproving_measure.py`、`docs/06_quality/SelfImproving_Protocol/**`；(iv) `docs/01_requirements/SelfImproving_PRD.md`、`docs/05_development/SelfImproving_*.md`、`docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/06_quality/SelfImproving_Event_Ledger.jsonl`、`docs/06_quality/SelfImproving_Proposals/**`、`tools/selfimproving.py`、`tools/lib/selfimproving/**`；(v) `AISDLC_SDD/AISDLC_SDD_v*/**` 去掉 LATEST（`python AISDLC_SDD/scripts/sdd_version.py` 現查、不寫死版號；查不到＝整個 `AISDLC_SDD_v*/**` 一律視為凍結，fail-closed）、`**/docs_template/**`。
- **NFR-SI-02-2 受保護路徑**：`.claude/**` 屬 harness 受保護路徑（auto 模式一律交分類器，根 `CLAUDE.md`〈權限姿態〉）；子代理成品一律 staged 到 scratchpad 交主控；被拒一次走人工核准重試，不改派子代理或換路徑繞過。
- **NFR-SI-02-3 無人值守**：`AUTOSDD_UNATTENDED` 下治理檔唯讀；迴圈在無人值守下僅可執行到「提案」止；人工閘、套用、晉升必須有人；人的逃生口（`AUTOSDD_GOVWRITE_GUARD_OFF`、`AUTOSDD_GIT_GUARD_OFF`）模型碰不到，迴圈不得要求關閉任何守衛。
- **NFR-SI-02-4 無外聯與最小留存**：運轉期不開網路外聯（**唯一例外**：FR-SI-30 的 `si research --fetch` 對來源表 URL 的 HTTP GET，外聯面見 §9.4 與附錄 B；禁令 26：外聯須 OPEN-X.x；邊界型 **M**——外聯只在 `fetch.py` 一個模組、對象限來源表（能力登記判準，§9.4）；誠實劃界：不做 DNS 解析後驗 IP；研究者無 Web 工具，額度守衛對 Web 工具的限流與此外聯無關、不是外聯禁令，不得讀成「被擋」）；證據只存座標、不存原始輸出全文（邊界型 **M**——CLI 只寫 `out_sha256`／`out_bytes`／遮蔽末段，AC-SI-21-1；降低密鑰／PII 外洩面；日誌遮蔽先例 `AutoClaude/autoclaude/utils/redaction.py`）。
- **NFR-SI-02-5 守衛面准入的誠實劃界**：現有 `_GOV_EXACT` 僅在 `AUTOSDD_UNATTENDED` 下阻斷、僅涵蓋 Write／Edit／NotebookEdit，且不含三份 `CLAUDE.md`、`governance/rules/*.yaml`（`.claude/hooks/block_destructive_git.py`:1423–1472）；本 PRD 不為此新增守衛碼（無暴露證據⇒理論洞 P4），MVP 以流程性邊界達成：提案產物只落沙盒、晉升為人工動作、不可進化面轉交。

### NFR-SI-03: 可稽核
- **NFR-SI-03-1** 每個 PROP 可追到 OBS→歸因→PROP→DEC→套用→驗證→量測→退役；斷鏈者不得晉升。
- **NFR-SI-03-2** ID 不重用、不改號；更正以追加列（遷移以外唯一的更正機制，AC-SI-04-3）；已存在列的原地改寫（自遷移基準 `migration_base_sha` 起算）被標 `ROW-MUTATED`（AC-SI-04-3）。
- **NFR-SI-03-3** 每筆紀錄含執行者角色與帶 offset 的時間；驗證證據含指令、rc、母體數（FR-SI-21）；追溯完整性由確定性檢查產出（不用模型）。

### NFR-SI-04: 可逆
- **NFR-SI-04-1** M：逐行反向 patch（前置快照僅作稽核副本，不整檔還原；§9.7 #16）；P：撤銷採納 commit 或刪 evolved 副本；R：`set_maturity` 退回或撤銷 commit；D：git revert。
- **NFR-SI-04-2** 每筆 PROP 的回滾為一個動作並於驗證階段乾跑（AC-SI-16-2）；回滾本身是人工動作（掌舵者），系統只提示（AC-SI-23-2）。

### NFR-SI-05: 反 Goodhart
- **NFR-SI-05-1** 評估器對生成器不可見：held-out 與評估指令由提案者以外角色凍結（FR-SI-20）。
- **NFR-SI-05-2** 迴圈層指標由確定性腳本產出、只對掌舵者與量測者呈現；提案者看不到目標值（AC-SI-22-3）。
- **NFR-SI-05-3** 資訊欄與成功指標分區，不用提案數、採納率、自評分數（§1.3.1）；指標定義帶判準指紋、定義變更屬不可進化面（FR-SI-22）；重放命中率只作證據、不得自動核准（禁令 14）。

### NFR-SI-06: 跨平台（Windows PowerShell／macOS）
- **NFR-SI-06-1** Windows 只用 PowerShell 工具（禁 Bash 工具）；一律絕對路徑、不裸 `cd`；讀 rc 先存變數（鐵律一、二）。
- **NFR-SI-06-2** 凡新增腳本或欄位先自問「這在另一個平台是什麼值？」（鐵律三觸發清單：時間戳 offset、路徑分隔符、console 編碼、行尾、大小寫）。
- **NFR-SI-06-3** 帳本與腳本的檔案 I/O 一律明示 UTF-8 編碼；`.md` 帳本不依賴特定行尾。
- **NFR-SI-06-4** 沙盒與背景任務不使用被擋的毀滅性 git 形態與壞等待形態（鐵律五、六）。
- **NFR-SI-06-5** macOS 未實跑的項目在驗收報告標「未驗」，不得以 Windows 結果代表。
- **NFR-SI-06-6** Console 在 Docker（Linux 容器）內以子行程呼叫 `tools/selfimproving.py export`（P1b，FR-SI-32）的平台自問：容器是 Linux、不是 Windows／macOS 主機——(i) repo 須以**唯讀**掛載到 `SI_ROOT`（沿 `SDD_ROOT` 體例；掛載範圍＝`tools/`、`docs/06_quality/`、`.git/` 三段、不掛 repo 根，§9.7 FC-b；compose 屬 AgentConsole 子專案），而 Bridge 映像現不含 `.git`（Architecture §12.2 V-11；映像只安裝 `git` 執行檔，Architecture §10.1 深度探針列），且映像使用者 uid 10001 與主機擁有者不同，`git` 的擁有者檢查須以環境變數式 `safe.directory` 放行（§9.2 鐵律三自問表）；(ii) `claude_home()` 逐字稿與 `~/.autosdd/` 家目錄在容器內不存在 ⇒ 依賴它們的欄位＝NOT-EVALUABLE 並顯示（AC-SI-32-3），不得省略欄位或印空；(iii) 路徑比對先 `realpath` 再 `normcase`、不寫死磁碟絕對路徑（`AgentConsole/CLAUDE.md` 跨平台鐵律 5）；(iv) 子行程 spawn 沿 Bridge `procutil` 的平台旗標（同檔跨平台鐵律 2：Windows 帶 `CREATE_NEW_PROCESS_GROUP`，結束子行程用 `terminate()`／`kill()`）；(v) 輸出一律 UTF-8（容器 locale 可能是 POSIX，`PYTHONUTF8=1`）；(vi) 事件 `t` 帶的 offset 是產生該事件那台機器的（容器多為 UTC），顯示層依 offset 顯示、不當本機時間；(vii) 換行與編碼風險同 §9.2 鐵律三表。macOS 未驗（NFR-SI-06-5）。

### NFR-SI-07: Token／額度預算
- **NFR-SI-07-1** 主控 Fable 只做裁決與親驗（派工、驗收、親跑重驗）；擷取、歸因、提案、審查用子代理 Sonnet（T1 2026-10-19 重申：Fable 當用則用、派子代理一律 Sonnet 5；研究者與體檢子代理同）；機械性轉換與格式檢查用 haiku 或確定性腳本；子代理以文字交卷、不寫報告檔（OBS-SI-004）。
- **NFR-SI-07-2** 每次扇出前現查 `python tools/session_resume_planner.py --pace`，不得記住上次值（根 `CLAUDE.md`〈工具選型〉）。
- **NFR-SI-07-3** 預算語意＝「任務書宣告、超出必揭露」；它與根 `CLAUDE.md` 12-Rule Rule 6 字面（每任務 4,000／每 session 30,000 tokens）的關係見 OBS-SI-012（候選 PROP-SI-002，待人工閘）；裁決前本迴圈不得默默超支。
- **NFR-SI-07-4** 研究者預算（FR-SI-30）：每運轉至多一個研究者（Sonnet，零遞迴）；來源表筆數 ≤ `RESEARCH_FETCH_MAX`（初值 8，無先例、未校準）、每來源原始位元組 ≤ `RESEARCH_BYTES_MAX`（初值 262144 bytes；先例＝`ledger_fail_bytes` 與 Read 工具 256KB 同值）、每來源牆鐘 ≤ `RESEARCH_TIMEOUT_SECONDS`（初值 20 秒，無先例、未校準）；CLI 抓取不是 Web 工具呼叫，不受守衛節流牽制（研究者無 Web 工具；OBS-SI-005）；派工前 `--pace` 現查，band 非 free 時改記 `research.skip(reason=quota-band)`（AC-SI-30-1）；體檢子代理同受 `--pace` 節制（FR-SI-31）。三個研究參數住 `params.json`，調整屬不可進化面。
### NFR-SI-08: 容量與可讀性
- **NFR-SI-08-1** OBS 單列 ≤ `ROW_MAX_BYTES`；事件帳本每行 ≤ `event_max_bytes`（初值 2,000，無先例；長內容搬 `rN.md`）；活躍帳本有位元組警戒線（warn／fail 取 Read 工具 256KB 實測事實，值住 `params.json`；`SelfImproving_*` 不在 `governance_docs.py` 的體積守門面，故自備），超限依「歸檔不改 ID」搬遷（先例：`docs/06_quality/AutoSDD_Defect_Log_archive_*.md`；搬遷工具不在 MVP，再開症狀：任一 SI 帳本逼近 warn 線）；PROP 卡核心區 ≤ 12 行（AC-SI-14-3）。

### NFR-SI-09: 失效可偵測（fail loud）
- **NFR-SI-09-1** 量不到＝NOT-EVALUABLE，不得 false-green（禁令 26；根 `CLAUDE.md` 12-Rule Rule 12）。
- **NFR-SI-09-2** 擷取通路失效可偵測：子代理交卷的「流程摩擦」項目數與入帳 OBS 數對帳（只量、不接閘門；先例 `tools/probe/audit_session.py`）。
- **NFR-SI-09-3** 迴圈任一階段失敗都留一筆 OBS（分類 `bug`），不得靜默吞掉。
- **NFR-SI-09-4** Console 面 fail loud（FR-SI-32）：SI 資料面取不到（`tools/selfimproving.py` 不存在、子行程逾時或 rc 非 0、輸出非合法 JSON、`SI_ROOT` 未設、未掛載或不含 `tools/selfimproving.py`、`schema_rev` 不符）一律回 503 `si_unavailable` 並顯示原因，不得顯示空表或過期快取當正常（AC-SI-32-3；禁令 26、12-Rule Rule 12）。`si research --fetch` 抓取失敗（逾時、非 2xx、超界、非文字、重導向被拒）＝該來源不入 `sources[]` 並印一筆 OBS 草稿列（NFR-SI-09-3），不得以舊 digest 充當本次結果。

**追蹤鏈**：`NFR-SI-01 → AC-SI-10-2／17-1／24-1`；`NFR-SI-02 → AC-SI-07-1／07-3／15-3`；`NFR-SI-05 → AC-SI-20-1／22-3`；`NFR-SI-09 → AC-SI-19-2／20-2／32-3`；`NFR-SI-06 → AC-SI-32-3`；`NFR-SI-07 → AC-SI-30-5`。

**🔴 人機協作確認點**：[ ] 所有 NFR 已定義 ID　[ ] 預算初值與先例座標可接受　[ ] 安全要求符合守衛面准入與受保護路徑姿態

## 🎨 7. 使用者體驗需求 (UX Requirements)
### 7.1 設計原則
- **易用性**：一卡一決定；三句話可決定核准／否決／退回；預設拒絕（不回覆＝不變）。
- **一致性**：卡面欄位順序固定；用語沿用 §13.1 詞彙表。
- **回饋機制**：每個決定回一行確認（PROP ID〔`恢復` 為 RUN ID〕、決定、digest 前 8 碼）；被拒的決定說明原因（過期卡／無法解析／冷卻中）。

### 7.2 介面規範（二擇一：採「CLI 文字提案卡」）
- **MVP 介面＝CLI 文字提案卡**：純文字／Markdown 區塊，由主控在掌舵者視窗貼出（或終端機印出）。**回覆語法只有下表這一張**（SCG-0 二審 F-30；AC-SI-12-1、AC-SI-12-4 ②、§9.1 C8 只引用本表、不複寫）；不合下表任一列者依 AC-SI-12-1 預設拒絕、狀態不變。轉交卡（`route=handoff`）同樣逐張、帶 PROP ID（K=1），不提供不帶 ID 的「轉交／不轉交」。

| 動詞 | 語法樣板 | 尾隨規則 | ID 綁定 | `--kind` | 前提（PROP 或迴圈狀態） |
|---|---|---|---|---|---|
| 核准 | `核准 PROP-SI-NNN` | 無尾隨文字 | PROP＋該 PROP 最近一次送達的卡面 digest | approve | PROP＝`proposed` 且 `route=loop`（`route=handoff` 的 PROP 不收，AC-SI-07-1） |
| 否決 | `否決 PROP-SI-NNN <一句理由>` | 只准接一句理由（必填；寫不出時填「未說明」，AC-SI-13-1） | PROP＋digest | reject；PROP 處 `verified` 態時＝decline-promote（人決定不晉升） | PROP＝`proposed` 且 `route=loop`，或 `verified`（`route=handoff` 的 PROP 用「不轉交」） |
| 退回 | `退回 PROP-SI-NNN <一句修改要求>` | 只准接一句修改要求（必填） | PROP＋digest | return | PROP＝`proposed`，或 `verified` 且 verdict＝FAIL |
| 晉升 | `晉升 PROP-SI-NNN`（verdict＝PASS）／`晉升 PROP-SI-NNN 未驗採納`（verdict＝NE；`flags` 記 `unverified_ack`） | 前式無尾隨文字；後式只准接「未驗採納」四字；式與 verdict 不符＝拒絕 | PROP＋digest | promote | PROP＝`verified` 且 digest 與核准時相同（AC-SI-16-1）；`route=handoff` 的 PROP 不收 |
| 轉交 | `轉交 PROP-SI-NNN` | 無尾隨文字 | PROP＋digest | ack-handoff | PROP＝`proposed` 且 `route=handoff`（轉交卡） |
| 不轉交 | `不轉交 PROP-SI-NNN <一句理由>` | 只准接一句理由（必填） | PROP＋digest | reject | PROP＝`proposed` 且 `route=handoff`（轉交卡） |
| 回滾 | `回滾 PROP-SI-NNN <一句理由>` | 只准接一句理由（必填） | PROP | rollback | PROP 已晉升（`promoted`／`measuring`／`closed`，且未退役）；回滾動作由掌舵者執行（AC-SI-23-2） |
| 解除 | `解除 PROP-SI-NNN` | 無尾隨文字 | PROP（被否決而啟動冷卻的那一個） | unblock | PROP＝`rejected` 且其同型仍在冷卻（AC-SI-13-2） |
| 恢復 | `恢復 RUN-SI-NNN <一句理由>` | 只准接一句理由（必填） | **RUN**（不是 PROP）：須等於事件帳本折疊出的「SUSPENDED 所在運轉」（觸發 SUSPENDED 的最後一筆壞窗關閉當下最近一筆 `run.open` 的 `RUN-SI-NNN`，`si status` 印出）；不符＝拒絕，防止舊回覆重播 | resume | 迴圈處 SUSPENDED（AC-SI-24-1） |

「一句」＝不含換行的單句；標「必填」的理由或要求缺席＝拒絕；動詞、ID 與 `--kind` 須同列一致（AC-SI-12-4 ②）。

- **取捨（明文）**：本設計的 DEC 只認「真人文字訊息」（逐字稿的兩種真人發言載體：`type:"user"` 且 `origin.kind=="human"`，或 `queued_command` 附件內的真人文字，AC-SI-12-4 ①；§9.0 Q11）；`AskUserQuestion` 類互動選項工具的答覆在逐字稿中是 `tool_result`、無 `origin` 欄，**不作 DEC**。附錄 C.2 的授權原句含「互動選項決策」，此處為刻意劃界，理由＝只有 `human` 出處可稽核；互動選項的答覆可作討論依據，但對 PROP 的決定仍須另以符合上列語法的文字訊息送出（PRD 凍結核准時 C.2 各項的逐項確認屬凍結閘、不是 SI 的 DEC，不受此限）。
- **Console 段（T1 修訂，v0.8）**：P1b＝唯讀鏡像（FR-SI-32；頁面的待決卡面逐字＝`si card` 輸出，不另渲染）；P2b＝決定載體（FR-SI-33；DEC 的第二種載體，上表動詞、ID 綁定、尾隨規則與前提在 Console 載體下不變，理由與要求以必填欄位表達）。兩者皆不寫入 FSM 狀態檔、不繞過既有簽核硬閘；Console 是顯示面與第二載體，不是第二種介面規範的替代（本節仍以 CLI 文字卡為準）。〔訂正（T1 修訂，v0.8）：原文「Console 卡片＝範圍外（⏸ F-SI-101，見 §3.3）：不寫入 FSM 狀態檔、不繞過既有簽核硬閘。」〕
- 設計系統：不適用（純文字）；響應式：不適用；無障礙：不依賴色彩，可在 Windows Terminal 與 macOS Terminal 顯示；語言：繁體中文，專有名詞保留原文。

### 7.3 原型／線框（提案卡；核心區 ≤ 12 行）
```text
[PROP-SI-007] 記憶條目｜retire｜目標：<座標>｜digest：a1b2c3d4｜驗證：PASS／FAIL／NE／未驗
一、症狀：<一句；含 OBS／DEF 座標與再現次數>
二、改什麼：<一句；+x／-y 行；觸及比例；觸及檔案數 n；不在 target 內的路徑〔無則 0〕>
三、風險與回滾：<一句；影響面＋一個動作的回滾配方＋驗證狀態>
決定：核准 ／ 否決＋一句理由 ／ 退回＋一句修改要求
--- 以下不計入核心區 ---
證據座標｜預算宣告｜完整 diff 座標｜冷卻狀態｜轉交通道（route=handoff 時）
```

## 📅 8. 時程與里程碑 (Timeline & Milestones)
### 8.1 專案里程碑（階段出口一律為症狀型判準；沒有日期、沒有版本號）
| 階段 | 里程碑 | 交付物 | 出口判準（症狀型；條件全部成立） | 負責人 |
|------|--------|--------|--------------------------------|--------|
| **P0** | 觀察帳本＋資料模型（本輪已 dogfood） | §5.1.1 欄位定稿、遷移後的觀察帳本；FR-SI-01～04、29 | (a) 任何視窗新增一筆觀察時不需向掌舵者追問任何必填欄（反症狀：出現「某欄無法填」的觀察即未達）；(b) 自遷移基準 `migration_base_sha` 起，全帳本通過欄位、引用與 `ROW-MUTATED` 檢查（`check` 綠；遷移 commit 本身依 AC-SI-01-3 豁免）；(c) 既有各列處置皆合枚舉且 `orig` 保全；(d) 零筆無座標列、零筆「之後再看」 | 主控（帳本單一窗口）、SD、QA（SCG-0 審查） |
| **P1** | 歸因＋提案（只提案） | FR-SI-05～11、14、28、30、31、34（另含 FR-SI-32 的根層半＝AC-SI-32-5 `export`）；PROP 物件與提案卡、研究掃描、體檢、落點鎖 | (a) 至少一筆真實（非構造）觀察端到端走到提案卡，且至少一筆屬 M／P／R／D 類（PROP-SI-001、002 屬不可進化面，走轉交，不能充當本條）；(b) 零提案觸及正式面（`git status`／HEAD 逐字對照）；(c) 掌舵者回饋中無 `reason_class=卡面不清` 的退回；(d) FR-SI-28 的可重跑檢查存在且綠；(e) 每個有 `prop` 的運轉都有研究事件（機械：`si check` 重放綠、`prop-new` 負控拒收，AC-SI-30-1）；(f) 至少一次體檢子代理交卷入帳 ≥1 列（真實、非構造，附 sid 與 OBS 座標；這是通路存在證明、不是成效，零候選＝「無事件」且 (f) 不達、不得以構造候選充當，AC-SI-31-5、§1.3.1）；(g) 落點鎖存在且綠（AC-SI-34-1～34-4）；(h) `si export` 存在且 AC-SI-32-5 綠（附錄 C.2 #12；⚖6 已採用） | 子代理（提案者）、主控 |
| **P1b** | Console 唯讀鏡像 | FR-SI-32 的 AgentConsole 半（AC-SI-32-1～32-4：Bridge `/si/*`、backend `/api/v1/si/**`、frontend `/self-improving`；前置＝Bridge 容器唯讀掛載與 `SI_ROOT`，§9.7 FC-b；檔名見 §9.1〈C18 檔名表〉） | (a) 差分（AC-SI-32-1）、(b) 唯讀（AC-SI-32-2）、(c) fail-loud（AC-SI-32-3）三 AC 綠，且 (d) 需登入（AC-SI-32-4）綠；(e) 至少一次真實瀏覽：掌舵者在真機開 `/self-improving` 並回報（附 sid＋line；構造情境或自動化截圖不能充當） | AgentConsole 開發 agent（鍵 `agentconsole-si-mirror`）、掌舵者（瀏覽）、主控 |
| **P2** | 人工閘＋沙盒套用＋驗證 | FR-SI-12、13、15～21 | (a) 至少一筆 M／P／R／D 類真實提案走完「閘→沙盒→驗證→晉升或否決」，DEC 紀錄齊全；(b) 該筆驗證含對照與突變，且突變確實使驗證轉紅（證明驗證有鑑別力）；(c) 至少一次同型再提被冷卻擋下（M4 結構性為 0 的證據）；(d) 正式面零「未經人工閘的變更」（git 歷史與 DEC 對帳）；(e) 回滾配方乾跑通過 | 掌舵者（閘）、審查者（子代理）、主控 |
| **P2b** | Console 決定載體（P2 之後） | FR-SI-33 | (a) ADR-SI-03′ 已裁決且其兩個待確認點經主控確認（§9.5；附錄 C.2 #16），兩端專用金鑰已配置（缺金鑰＝`promote` 拒）；(b) AC-SI-33-1、33-2 綠；(c) 至少一次真實 Console 決定走完（`dec` 事件帶 `carrier=console` 與稽核列座標；掌舵者真機操作，附 sid）；(d) 正式面零「未經人工閘的變更」（git 歷史與 DEC 對帳，含 Console 載體的決定） | AgentConsole 開發 agent（鍵 `agentconsole-si-decide`）、掌舵者（閘）、主控 |
| **P3** | 量測＋退役 | FR-SI-22～27；量測腳本 | (a) 量測腳本在真實帳本上跑通，輸出 M1～M5 值、樣本數、窗與判準指紋（樣本不足者印 NOT-EVALUABLE）；(b) 至少一個採納量測窗關閉並入帳（clean／recurred／rolled-back）；(c) 至少一筆退役提案走完人工閘；(d) §1.1 反證條件已檢查並留紀錄（同一根因鍵下連續兩個可評估採納窗皆仍復發者〔§1.3〈M1 判定細則〉(c)〕列為 T1 決策項，不自動下線；無可評估窗＝NOT-EVALUABLE，記錄缺什麼） | 主控、掌舵者 |

**🔴 人機協作確認點**：[ ] 出口判準為症狀型且無日期　[ ] 負責人已確認　[ ] 里程碑定義清晰

### 8.2 出口判定規則
- 出口須有**正向證據**：零發現不是 PASS（C-13）；量不到＝NOT-EVALUABLE，不算達標也不算失敗，沿用上值並說明缺什麼。
- 已達標階段的出口症狀再現（附 sid 或 OBS 座標）＝該階段重評；時間流逝、版本升級、覆蓋度數字不構成重評理由。
- 每階段出口時，該階段 FR 與 AC 各列必須落在且只落在 §8.3 四格之一，沒有「未分類」列。

### 8.3 結案帳體例（沿用 PRD v2.1 §16.1）與立案時已宣告的 ➖／⏸
四格：✅ 已落地（規範性機制在、且有測試或鎖）／➖ 依設計退役（附依據座標）／⏸ 延後至症狀驅動（附**一句**可觀測再開症狀；禁止寫輪號、日期、「待排程」）／📎 驗收資料殘留（附殘留是什麼）。座標：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16.1。立案時（本稿）尚無任何 ✅；以下是立案時已宣告的 ➖／⏸：

| 項目 | 格 | 依據／再開症狀 |
|------|-----|---------------|
| 更新模型權重 | ➖ | SOP S1 不在範圍；§3.2 |
| 自我發明評估器（meta-oracle 自演化） | ➖ | 禁令 22～25 末項；C-07 |
| 日曆／版本號觸發與常駐排程 | ➖ | C-12；PRD v2.1 §16.1 ➖（本 repo 刻意不做 Daemon） |
| 無人工閘的自動採納 | ➖ | 禁令 11、12；§3.2 |
| F-SI-102～105（授權代決／機器可讀 OBS 帳本／harness 整體 diff 提案／演化提案結構化落地） | ⏸ | 各自的一句再開症狀見 §3.3 |
| F-SI-101（Console 提案卡） | 已再開（轉為 FR，不再是 ⏸） | T1 2026-10-19（sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13）命中其再開症狀「掌舵者要求在 Console 內審提案」→ FR-SI-32（P1b）、FR-SI-33（P2b）；各階段出口時依 §8.2 歸入四格〔訂正（T1 修訂，v0.8）：原文「F-SI-101～105 … ⏸」中的 F-SI-101〕 |

### 8.4 再開與退場（事件驅動）
- 修訂本 PRD 只依：T1（掌舵者立案，附原文）、SOP S7 觸發 T-1～T-7 的症狀、§3.3 某 ⏸ 列的再開症狀實際發生（附 sid／座標）。
- 本 PRD 本身是驅動器：不開 `AutoSDD_improving_117`、不產四件套（附錄 C.1）；範本〈🏁〉T1～T4 仍管軌道①。
- 退場：§1.1 反證條件成立時列為 T1 決策項；退場方式（縮減或廢止）由掌舵者決定，不自動下線。

## 🔧 9. 技術選型與架構 (Technical Stack & Architecture)
> **SD／Architect 棒填寫（Sonnet 5.5；2026-10-19；輸入快照 HEAD＝`0bf83bad`，開工時工作樹乾淨）。** 本節只定**架構方向**：不引入新技術棧（沿既有 Python 3.11+ stdlib／git／Markdown／JSON Lines），不新增守衛碼、鎖、hook、Plugin、KernelPhase、FSM 狀態、PG 表。座標與數字皆 SD 寫稿時現查的**快照值**（重跑法＝座標本身），不是 SSOT；SD 一次性普查腳本在 session scratchpad、未入庫；QA 須獨立重跑，不得採信本節。§9.5 原待裁決項（ADR-SI-02／03／06／07）已於附錄 C.2 裁決（#5～#9）；殘留清理續棒基於 HEAD `69a644e6`；SCG-0 一審修復續棒（SD）基於 HEAD `a52ee13e`（開工時工作樹乾淨），一審報告＝`docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md`；二審後收尾棒（SD）基於 HEAD `978df84c`（二審報告＝同檔 §6；本棒起可改任何章節）。本節新增的實測（Q11、Q12，Q5、Q6 的刷新）同樣是快照值，探針在 session scratchpad、未入庫。

> **T1 修訂（v0.8，SA 棒；輸入快照 HEAD＝`d4b7868f`）**：本節中 C16～C19、§9.2 事件詞彙與 `carrier`、§9.3 動詞與 Console 端點、§9.4 研究者與 Console 面、§9.5 ADR-SI-11／12、§9.6 的 P1／P1b／P2b 列，是 SA 依掌舵者 T1 與附錄 C.2 #10～#15 增補的**需求面骨架**；檔名、DTO、分頁參數與 ⚖ 項標「Architect 棒定」，SD／Architect 棒續審並將審閱紀錄追加於 §9.7（#41 起）。座標與數字仍是快照值，QA 須獨立重跑。

> **T1 修訂（v0.9，SD／Architect 棒；輸入快照＝PRD 修訂 commit `c2aee850`；動工與交卷時 `git diff c2aee850 HEAD -- docs/01_requirements/SelfImproving_PRD.md` 皆無輸出；工作樹其餘改動屬他棒、本棒未碰）**：上一段 SA 骨架中的「Architect 棒定」與 ⚖ 已落定——檔名與路由（§9.1〈C4 套件檔案表〉〈C18 檔名表〉）、資料模型（§9.2）、動詞旗標與 rc（§9.3）、純度與外聯判準（§9.4）、ADR-SI-03′／11／12（§9.5）、鍵與依賴（§9.6）；可行性核對 FC-a～FC-f 與審閱紀錄（#41 起）在 §9.7。§9.7 原 #1～#40 與 §9.0 Q1～Q12 的全文逐字搬到 `docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` 附錄 SD（PRD 超過 Read 工具 256KB 上限，NFR-SI-08-1 同型）。座標與數字仍是快照值，探針在 session scratchpad、未入庫，QA 須獨立重跑。§9 引言的「不新增守衛碼、鎖、hook、Plugin、KernelPhase、FSM 狀態、PG 表」仍指 SI 根層核心；例外三處各有明文——FR-SI-34 落點鎖（§3.2、附錄 B）與 §9.4 能力登記測試（皆 `tools/tests/` 形態判準、不在守衛面清單、非 hook，§9.7 #47）、P2b 的 Console DB 稽核表 `si_decisions`（AgentConsole 子專案，ADR-SI-03′）。

### 9.0 約束落點與 SD 查證
**約束 → 落點**（任一落點與約束衝突＝本節自身有缺陷）
| 約束（座標） | 本設計的落點 |
|---|---|
| AutoClaude 微核心：`core/` 只依賴 `ports/`、plugins 互不 import（`AutoClaude/.importlinter` Rule 1／2）；**套件不得 import monorepo `tools/`**（Rule 9：只鎖 autoclaude→tools，tools→autoclaude 屬合法消費） | SI 的判準與資料全部住根層 `tools/`＋`docs/`（P1b 起另有 AgentConsole 側的顯示面，見下列 AgentConsole 列），**`autoclaude/` 原始碼零改動**；引擎產物一律以檔案契約唯讀消費；AutoClaude 側的 SI 交付僅 `AutoClaude/tests/` 新增 1 檔（C13）；`AutoClaude/CLAUDE.md`:191 的改述走一般開發流程（AC-SI-28-2） |
| 新增 Plugin 六步、LOC 分級（`AutoClaude/CLAUDE.md`；`python AutoClaude/tools/check_loc_budget.py --json`：根層 `guardrail_lib`≤400／`guardrail_cli`≤750） | MVP 不新增 Plugin／KernelPhase／EventBus 事件（§9.3）；根層新檔各守所屬 tier（`tools/lib/` 每檔 ≤400、入口 ≤750，計價只算斷言行；P1 新增 16 檔的估算見 §9.1〈C4 套件檔案表〉、§9.7 FC-e） |
| DAL 三後端（`core/wiring.py`、`infra/repositories/factory.py`） | SI 資料不進 DAL／PG（§9.2）；偏好／KB 只讀 |
| SDD Rule 9：禁令 1（不繞 `FSMRuntime`）、8／9（不動 `_HAPPY_PATH`／Terminals）、11／12（退役／spec patch 必人工）、26（沙箱 hang 收 verdict、外聯須 OPEN-X.x） | SI 不讀寫 FSM-STATE（只經 `show`）；PROP 狀態機只在事件帳本；R 類沿用 SLV／SPEC-PATCH 管線產物（座標引用）；逾時收 verdict、不外聯（唯一例外＝FR-SI-30 的 `si research --fetch` 對來源表 URL 的 HTTP GET，§9.4；其餘動詞一律不連網） |
| AgentConsole：SDD 寫入一律經 `FSMRuntime` CLI 子行程、Console 對 FSM 只讀（`AgentConsole/CLAUDE.md`:15）；資料所有權（Architecture §7）、Bridge 契約（§10、§10.2）；ADR-XPLAT-016 §11 引擎可改檔白名單 | P1b 起 Console 唯讀鏡像（FR-SI-32）：`/si/*` 全 GET、Bridge 以子行程呼叫根層 `export`、自身不開帳本檔；AgentConsole 鐵律 7 禁其開發 agent 動根層 `tools/`，故 `export` 住根層（附錄 C.2 #12，⚖6 已採用）；P2b 決定載體（FR-SI-33，ADR-SI-03′）；端點與檔名見 §9.1 C18、§9.3；SI 自持引擎白名單（ADR-SI-07；已裁決，附錄 C.2 #6、#7）〔訂正（T1 修訂，v0.8）：原文「MVP 不碰 Console／Bridge；post-MVP 端點骨架見 §9.3」〕 |
| 根層：守衛面准入（量、不挖）、〈權限姿態〉、鐵律一～七 | 零新增守衛碼（SI 新檔不在守衛面清單）；每條「不能做」標邊界三型（§9.4）；鐵律三自問見 §9.2 末表 |
| 護欄層行數棘輪、`tools/tests` 檔數下限、CI `paths`（根 `CLAUDE.md` 鐵律七；記憶 `guard-ratchet-repin-ritual`） | P1 新增 `tools/` 估 3,700 行（斷言行，§9.1〈C4 套件檔案表〉）與數支 `tools/tests/test_selfimproving_*.py`、`test_root_module_layout.py`，遠超單輪淨額上限（`_REPIN_ROUND_NET_CAP`＝516，`tools/tests/test_adr_xplat001_c1c2_lock.py`:2709–2725）⇒ **實作輪重釘**（屬收尾、不是設計缺口）：`_FROZEN_GUARD_LINES` 逐檔值、`_REPIN_APPROVED_ROUND_OVERAGE` 具名一次性例外（名冊上限 `_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES`＝5，:2794；P0 已用 R213 列，上修須可見）、兩站點 guard-total、`tools/tests` 的 E501 棘輪與 `_TREE_FILE_FLOORS`，由主控單人窗口於同一個 commit 收齊（鐵律七檢查表 4）；compat-ci 兩支 `paths` 已含 `tools/lib/selfimproving/**`、`tools/selfimproving.py`（`windows-compat-ci.yml`:233–234、:705–706；`macos-compat-ci.yml`:97–98、:577–578），P1 另加新測試檔所消費者；`agentconsole-ci.yml` 的 `paths`（:21–38）P1b 加 `tools/selfimproving.py`、`tools/lib/selfimproving/**`、`docs/06_quality/SelfImproving_*`（Bridge 差分測試呼叫真 CLI，根層改動須觸發它） |

**SD 查證**（回答 PRD 的「未查證」處；快照值，QA 重跑＝照座標 Grep／量測；每題只留結論與座標，逐字全文＝`docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` 附錄 SD-2）
| # | 查什麼 | 結論與座標 |
|---|---|---|
| Q1 | `translation_learner` 的 proposed 由誰、在哪審（§11.1 列 4、G-SI-14） | 現況無固定審閱者與介面：落地＝`<checkpoint_dir>/translation_learning/PROPOSALS-<project>.jsonl`（`core/wiring.py`:331–341），讀取者只有 plugin 自己的 dedup（`plugins/translation_learner_plugin.py`:99），`autoclaude/`、`AgentConsole/`、根 `tools/` 的 Grep 無其他讀者 |
| Q2 | `IPreferenceStore.set` 的呼叫端（§11.1 列 3） | Port 無 delete（`core/ports/preference_store.py`:20–31）、唯一 production `set`＝`core/wiring.py`:187（啟動 seed）、Brain 回寫為 ADR-AGT-003 §2 所禁 ⇒ 偏好「退役」在 Port 層做不到 |
| Q3 | 「演化只提案不套用」在生產路徑的真實依據（OBS-SI-010、G-SI-01／02） | `PlaybookRunner` 零生產建構點已有測試（`AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py`:97–112）；`AutoResumeService` 演化重載分支（`core/services/auto_resume.py`:255–272）無 signoff 閘、現靠無生產者不可達，`require_evolution_signoff` 只在 `execution/playbook_runner.py`:306 被讀 ⇒ 改預設為 True 對生產路徑無效；文件座標改引註解字樣（OBS-SI-023；AC-SI-28-2、28-1 ⑤） |
| Q4 | EvolutionPlugin 提案在 Kernel 路徑落到哪 | 只剩一行 log（`core/kernel.py`:371–374）；`REVISE_EVALUATOR` 已被轉成 `REVISE_CURRENT`（`plugins/evolution_plugin.py`:284–289）⇒ log 無法辨識型別；`MutationProposal` 無結構化落地（dump 是否另含提案：未查證） |
| Q5 | `MEMORY.md` 現況（§1.2／§11.1 列 13／AC-SI-27-1；OBS-SI-016、030） | 快照 2026-10-19 06:00 +08:00：16,391 bytes、79 行；OBS-SI-030 重排後被截斷時先被吃掉的是尾端輪次列表、常青教訓節不受影響（SCG-0 一審 F-06，原結論已反轉）；此檔會被重排或自寫，數字一律現查 |
| Q6 | DEF 帳本的歷史基線與再現基率（AC-SI-06-2、FR-SI-22） | 歷史基線結構性 NOT-EVALUABLE，下列數字只供 §1.3 M1 檢定力估算、不作基線：家族 70 檔、1,667 列（去重 1,661）；首詞 `fixed` 1,490、可解析 commit hex 僅 34 列、「再開症狀」字樣 4 列、「…命中」1 列、`reopens:` 0 列 ⇒ 全域 20 列窗期望再現事件約 0.01～0.05 件，故 M1 改 per-PROP 前後對照（ADR-SI-05）；舊口徑 1,508 列的差額對帳見附錄 SD-2 |
| Q7 | 沙盒量級與路徑（ADR-SI-04） | tracked 29,249 檔、最長相對路徑 142 字元；session scratchpad 根 118 字元（全樹匯出最長可達 261＞260 MAX_PATH）、`~/.autosdd/selfimproving/sandbox/PROP-SI-007` 根 57 字元（最長 200）；`core.longpaths` 不隨 repo；`.gitattributes` 無 `export-ignore` |
| Q8 | 守衛對 worktree／沙盒清理的態度 | `git worktree remove --force` 對樹外既存目錄放行、對樹內擋（`.claude/hooks/block_destructive_git.py`:824–867；`tools/lib/worktree_paths.py`）；R178：樹內 `.claude/worktrees/` 使全庫掃描鎖 4 個假紅 |
| Q9 | SI 帳本的體積守門 | `SelfImproving_*` 不在 `_GOVERNANCE_DOC_GLOBS`（`tools/lib/governance_docs.py`:710–718）⇒ 無體積守門；Read 工具 256KB 上限是實測工具事實（`tools/check_defect_log_crossref.py`:1152–1153）⇒ SI 自備警戒線 |
| Q10 | 觀察帳本現值 vs 700 bytes | 快照 2026-10-19 10:28 +08:00：41 列 215～583 bytes、全 8 欄、現無超線列（`ROW_MAX_BYTES`＝700，`tools/lib/defect_ledger_index.py`:545）；最長五列加第 9 欄後預估超線（估，未實測）；數字一律現查 |
| Q11 | 逐字稿真人發言與互動選項答覆的形態（AC-SI-12-4 ①③；SCG-0 二審 F-33） | 真人發言兩種載體：(i) `type:"user"`＋頂層 `origin.kind=="human"`；(ii) `queued_command` 附件（文字在 `attachment.prompt`、時序用附件自帶 `timestamp`）；`AskUserQuestion` 答覆是無 `origin` 的 `tool_result`、不能作 DEC；本機 138 份普查 (ii) 占 24／97＝24.7%；一律 JSON 結構判定；只驗本機（他機、他版本的欄位形態未驗）；欄位為觀察所得、非官方契約（ADR-SI-03） |
| Q12 | `git apply --numstat -z` 對 patch 標頭導出哪些路徑（AC-SI-07-3） | 只能當超集檢查、不能當 `touched` 來源（git 2.51.0.windows.1；macOS 未驗）：改名與複製只列目的端、八進位引號被解開、不拒絕 `..`／絕對路徑／磁碟機代號／尾端點／`:` 資料流、`diff --git` 標頭與 `---`／`+++` 不一致時以後者為準 |

### 9.1 元件與落點
八階段（觀察→歸因→提案→人工閘→套用→驗證→量測→退役）全部落在**根整合層**（P1b 起 Console 顯示面落在 AgentConsole 子專案，只消費根層的 `export`；P2b 的決定經稽核 JSON 交主機端 `decide` 入帳，C18）；兩引擎只作唯讀資料來源。元件數＝**19**（新建 16；接既有 3，其中 C2、C15 零改動、C1 為 SI 自有帳本的定稿；C16～C19 為 T1 修訂 v0.8 新增）。下文 `si <動詞>`＝`python tools/selfimproving.py <動詞>`（Windows 用 repo `.venv` 的 python）。**模組落點表**（掌舵者 2026-10-19 指令：新模組不得散落；SSOT＝`docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）：函式庫 `tools/lib/selfimproving/`（套件）、指令入口 `tools/selfimproving.py`、探針 `tools/probe/selfimproving_measure.py`（P3，C11；SSOT §3 該列誤寫「P1 探針」，§9.7 #53）、測試 `tools/tests/test_selfimproving_*.py`（另有全 repo 落點鎖 `tools/tests/test_root_module_layout.py`〔FR-SI-34、C19〕，不屬 SI 套件）、協定資料 `docs/06_quality/SelfImproving_Protocol/`（`params.json`、`metrics.md`、研究來源表 `research_sources.json`〔C16〕）、帳本 `docs/06_quality/SelfImproving_*_Ledger.md`（附註檔 `docs/05_development/`）、提案內容檔 `docs/06_quality/SelfImproving_Proposals/`、事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`、規格與 SOP 依編號制（本檔、`docs/03_testing/contracts/TCS-SelfImproving-*.md`、`docs/05_development/SelfImproving_*_SOP.md`）、審查與 RTM `docs/06_quality/`；家目錄機器狀態 `~/.autosdd/selfimproving/{sandbox,heldout,locks,research,console_audit}/`（repo 外，§9.2）；Console 顯示面（P1b／P2b）依 `AgentConsole/docs/02_architecture/Architecture.md` §3／§4.1／§5.1 落在該子專案（SSOT §2 末段：子專案內的模組不往根層放），檔名見〈C18 檔名表〉；`tools/lib/selfimproving/` 的檔案表與能力類別見〈C4 套件檔案表〉。
| # | 階段 | 元件 | 落點 | 接既有／新建 | 職責；輸入→輸出 | 閘門 |
|---|---|---|---|---|---|---|
| C1 | 觀察 | OBS 帳本 | `docs/06_quality/SelfImproving_Observation_Ledger.md`（Markdown 表） | 接既有（P0 定稿第 9 欄＋檔頭 `tz=`；**一次性遷移＝單一 commit，其 sha 於另一個 commit 寫入 `params.json` 的 `migration_base_sha`，並附一筆掌舵者確認的 `decided` 列**，AC-SI-01-3） | 記觀察、只存座標；子代理「流程摩擦」文字交卷＋主控發現→一句症狀列；`ROW-MUTATED` 自 `migration_base_sha` 起比對（AC-SI-04-3），遷移後更正只准追加更正列（`rel=corrects:`） | 主控單一窗口寫；他人只讀 |
| C2 | 觀察 | 既有量測器與引擎產物（唯讀） | `tools/probe/audit_session.py`、`misstep_attribution.py`；DEF 帳本家族；`<checkpoint_dir>` 下 escalation dump、`failure_knowledge_base.jsonl`、`translation_learning/PROPOSALS-*.jsonl`、RTM history | 接既有（零改動） | 供擷取者讀的證據源→OBS 候選列 | 只讀 |
| C3 | 歸因 | ATT 事件＋歸因者任務書 | 事件帳本 `attr`／`attr.confirm`；任務書範本在 C6 | 新建（P1） | OBS 群→（種類,座標）清單＋根因鍵；確認者≠提出者 | 提案 |
| C4 | 提案 | PROP 物件與 SI CLI | `tools/selfimproving.py`（入口薄殼）＋`tools/lib/selfimproving/`（套件，檔案表與能力類別見下〈C4 套件檔案表〉；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）；內容檔 `docs/06_quality/SelfImproving_Proposals/PROP-SI-NNN/rN.{md,patch}`；事件 `prop` | 新建（P1）；R 類接 SDD `slv_generator`／`spec_patch_proposer`（座標引用、不複製） | 抽象化輸入→PROP（proposed）；前置檢查（AC-SI-07-3，§9.4）：類別白名單、`touched`（自 patch 導出）**全部路徑**逐一比對不可進化面與合法根（凍結版本目錄與模板適用所有類別）、`spec_body_globs`、所有類別都要有內部來源（AC-SI-02-1）、運轉預算、同運轉有研究事件（AC-SI-30-1）、同型去重、SUSPENDED；寫事件於鎖內配號（ADR-SI-10） | 提案 |
| C5 | 全程 | 協定目錄 | `docs/06_quality/SelfImproving_Protocol/{params.json,metrics.md}`（T1 修訂 v0.8 另有 `research_sources.json`，由 C16 持有） | 新建（P0；先例 `FiveQuestion_Audit_Protocol/params.json`） | 全部「初值（未校準）」參數（PRD 的 `UPPER_SNAKE` 與 JSON 的 `lower_snake` 一對一，含 `w_evt`〔初值 2，無先例、未校準；M1 的 NE 護欄量基線窗確認再現事件數〕、`max_archive_entries_per_card`〔C.2 #8，初值 50〕、`card_line_max`、`event_max_bytes`、`research_fetch_max`〔初值 8，無先例〕、`research_bytes_max`〔初值 262144，每來源；先例 `ledger_fail_bytes`〕）；另有非「初值」類的欄位：`migration_base_sha`（一次性事實值＝P0 遷移 commit 的 sha；commit 不能引用自己的 sha，故於遷移之後另一個 commit 寫入）、`spec_body_globs`（§9.4）；`non_evolvable_globs`（**實體 glob 對齊 NFR-SI-02-1「實體 glob」段、該段為唯一真相源，本節不複寫第二份清單**；錨定語意照 NFR-SI-02-1：`**` 可吃零段至多段、不帶 `**/` 前綴者只錨定 repo 根，故守衛面寫 `**/.claude/**`，根錨定的 `.claude/**` 管不到子專案與各版本目錄下的 `.claude/`；LATEST 沿 `tools/lib/sdd_latest.py` 的 `resolve_latest_name` 現查〔內部呼叫 `sdd_version.py`〕、不寫死版號，解析失敗〔該函式拋 `AssertionError`〕＝整個 `AISDLC_SDD_v*/**` 視為凍結＝fail-closed；JSON 與 NFR-SI-02-1 散文不一致＝`si check` 紅）、體積警戒線（warn／fail）、反空轉下限、`metrics_rev`、指標定義 | 不可進化面（僅 T1 改） |
| C6 | 全程 | SOP 與角色任務書 | `docs/05_development/SelfImproving_Operations_SOP.md` | 新建（P0 草稿／P1 定稿） | 擷取者／歸因者／提案者／審查者／凍結者任務書範本（P1 定稿另新增：研究者任務書範本〔C16〕與模組體檢任務書範本〔歸因者節，內容＝FR-SI-31 的入口表〕）；輸入快照 `HEAD=<sha>`、文字交卷、`--pace` 現查 | 不可進化面 |
| C7 | 人工閘 | 卡面轉換器 `si card` | C4 CLI 的動詞 | 新建（P1） | PROP→核心區 ≤12 行＋反解析一致性檢查（digest、diff 行數、**觸及檔案數**、驗證狀態，AC-SI-14-2）；核心區顯示 `touched` 的檔案數與「不在 `target` 內的路徑」（為 0 顯示 0；非 0 逐筆列出且計入 ≤12 行，超限＝`prop-new` 拒收並要求拆分或補齊 `target`，AC-SI-07-3／14-3）；`--issue` 記 `card` 事件 | 只讀（`--issue` 寫事件） |
| C8 | 人工閘 | DEC 驗證器 `si decide` | C4 CLI；讀 `claude_home()/projects/<slug>/<sid>.jsonl` | 新建（P2；user 記錄的判準沿 `.claude/hooks/check_claim_provenance.py` 的 `_is_genuine_user_turn`——該函式只看 user 記錄的 `origin`／`turnOrigin`／`isMeta`；`queued_command` 附件載體是本元件新增的判準） | 自逐字稿抽取掌舵者引言（工具抽取、非主控輸入）→DEC 事件。**真人發言有兩種載體**（SCG-0 二審 F-33；§9.0 Q11）：(i) `type:"user"` 且頂層 `origin.kind=="human"`；(ii) `type:"attachment"`、`attachment.type=="queued_command"` 且 `attachment.origin.kind=="human"`（文字取 `attachment.prompt`）；`sdk`、`isMeta`、harness 代筆、`tool_result`（含 `AskUserQuestion` 的答覆）皆不算；**逐字稿一律解析 JSON 後以結構欄位判定，不做整行子字串比對**（工具內容可含 `"origin":…` 字樣）。座標＝`sid`＋`line`（該記錄的 1 起算物理行號；附件載體取附件記錄本身的行號）。**動詞、尾隨規則、ID 綁定與 `--kind` 一律以 §7.2 動詞表為唯一真相源，本節不複寫**（SCG-0 二審 F-30）。**錨定（AC-SI-12-4 ②）**：「整則訊息」＝該記錄的全部 text（user 記錄＝content 的 text 區塊串接；附件＝`attachment.prompt`）；決定語法須位於整則開頭（去前後空白後），或獨立成一行且整則只含一個決定行；子字串命中不算（動詞前有任何前綴字，例如否定詞，亦不受理）；一則訊息含多個 PROP 的決定、或夾帶卡面引用者，整則拒絕（預設拒絕，AC-SI-12-1）。**③ 的時序基準**：user 記錄用物理行序；附件用附件自帶的 `timestamp` 對 assistant 訊息的頂層 `timestamp`（不用行序），附件缺 `timestamp`＝NOT-EVALUABLE；「最近一則 assistant 訊息」指最近一則含 text 區塊者（只含 `tool_use` 的訊息略過）；`恢復` 無卡面、不驗 ③。**回查（AC-SI-12-4 ⑤）**：`si decide` 寫入前、`si check` 對每筆已存 `dec`、`si promote` 對 `approve` 與 `promote` 兩筆 DEC，都呼叫同一個驗證函式（函式依 `dec` 的 `carrier` 分派：缺欄＝`transcript`，走本列規則；`console`＝ADR-SI-03′ 的稽核檔回查）。**負控自證**（合成逐字稿，實作輪）：`sdk` 發言、他 PROP、過期 digest、被改寫的卡面，加上否定句（「不核准 PROP-SI-007」）、疑問句（「核准 PROP-SI-007？先等一下」）、引用卡面（貼回含「決定：核准 ／ 否決…」的卡面）、多 PROP 同則訊息，皆拒絕；`tool_result` 內容含 `"origin":…` 字樣者不得被當成 human（結構判定）；動詞表負控——`解除 PROP-SI-NNN` 後有尾隨文字、`恢復` 缺 RUN 號或 RUN 號過期、`回滾` 對未晉升的 PROP、`晉升` 的式與 verdict 不符（PASS 卻用「未驗採納」式、NE 卻用前式）、對 `route=handoff` 的 PROP 說「核准」或「晉升」，皆拒絕；附件載體——正控＝卡面送達之後打出的核准受理，負控＝打出時刻（附件 `timestamp`）早於卡面送達、但物理上注入在其後者拒絕；回查負控——追加格式合法但引言對不上逐字稿的 `dec` 行→`check` 紅、`promote` 拒；正控＝真人核准受理。同型先例 DEF-200-501（Stop hook 否定句誤報） | 需人工 |
| C9 | 套用 | 沙盒 | `~/.autosdd/selfimproving/sandbox/`（ADR-SI-04） | 新建（P2） | `git archive` 匯出 base 快照（M 類＝檔案複製）→套 patch（套用器實際寫入的路徑集合須 ⊆ `touched`，多出者＝拒絕驗證，§9.4）→丟棄 | 提案（副本）；`si promote`＝需人工 |
| C10 | 驗證 | 驗證執行器＋held-out 凍結／暴露偵測 | C4 CLI（`heldout-freeze`、`verify`）；內容 `~/.autosdd/selfimproving/heldout/` | 新建（P2）；通用化 SDD R-9.20.3／R-9.27 概念 | 凍結評估集→沙盒內 RED／GREEN／突變三步＋載具自證＋逾時收 verdict→`app.verify` | 提案；審查者唯讀 |
| C11 | 量測 | 量測腳本 | `tools/probe/selfimproving_measure.py` | 新建（P3；形態同 `tools/probe/fivequestion_ledger.py`） | 帳本＋git→M1～M5＋資訊欄＋判準指紋；零 token | 只讀、不接閘門 |
| C12 | 退役 | 容量偵測與退役流程 | C4 CLI（`capacity`）；退役走 C4 同一條 PROP 鏈 | 新建（P3） | 記憶索引／KB 驅逐指標／偏好鍵數→容量事件→索引行逐字歸檔提案 | 偵測只讀；退役＝提案＋需人工 |
| C13 | 既有缺口 | 「演化只提案不套用」檢查 | `AutoClaude/tests/contract/test_evolution_propose_only.py`（新檔） | 新建（P1）；形態沿 `tests/core/test_kernel_unhandled_mutation_failloud_r85.py` | AC-SI-28-1 的五格：①～④ AST 普查、⑤ 文件宣稱釘住 | pytest |
| C14 | 觀察 | 事件偵測 `si status` | C4 CLI | 新建（P1） | AC-SI-03-1 (b)～(e)：新 P≤2 未結 DEF、已採納工件再開症狀、容量事件、待決 PROP、SUSPENDED／冷卻；交卷對帳（NFR-SI-09-2）：主控逐字稿中 Agent 回傳的「流程摩擦」節項數 vs 同窗新增 OBS 列數（只量不閘）；無常駐行程 | 只讀 |
| C15 | 提案／退役 | SDD R 類管線與抖動把關 | LATEST 的 `tools/fsm_runtime/{slv_generator,spec_patch_proposer,scaffold_gc}.py`、`rule_loader.set_maturity`、`meta_halt/meta_halt_monitor.py` | 接既有（零改動） | R 類草案來源；退役與 add↔retire 抖動把關（SDD 面） | 提案＋需人工（HUMAN_PENDING／`reviewed_by`） |
| C16 | 觀察 | 研究來源表與 `si research` | 協定目錄 `docs/06_quality/SelfImproving_Protocol/research_sources.json`（NFR-SI-02-1 (iii) 既有 glob 涵蓋）；CLI 動詞 `research`（C4 套件：`sources.py`〔ro〕、`research.py`＋`fetch.py`〔net〕、`writeverbs.py`〔`--skip`〕）；家目錄來源檔 `~/.autosdd/selfimproving/research/<id>/<sha12>.txt`；事件 `research.scan`／`research.skip`；研究者任務書範本在 C6 | 新建（P1；形態沿五問協定的協定目錄＋CLI） | `si research --fetch` 依來源表 URL 抓**原始位元組**→落地家目錄來源檔→自算 `sha256`、比對上一筆同 `id` 得 `changed`→寫事件（D-1′，附錄 C.2 #16）；研究者（Sonnet；Read／Grep／Glob）讀 `changed=true` 的來源檔→文字交卷 OBS 候選（`外部衍生=是; src=<id>`，主控入帳）；`--skip` 寫免掃事件；`prop-new` 前置檢查與 `check` 重放守「有 `prop` 的運轉必有研究事件」（AC-SI-30-1～30-6） | 提案（寫事件；外聯只在 `fetch.py`）；候選入帳＝主控單窗口 |
| C17 | 觀察 | 模組體檢 `si scan`＋體檢任務書範本 | C4 套件 `scan.py`（ro）；任務書範本在 C6 歸因者節（入口表＝FR-SI-31） | 新建（P1；唯讀量測器 C2 接既有） | `scan`：唯讀、離線、無狀態、不寫事件，彙整本地證據印 OBS 候選草稿列（五模組桶＋未分類；每個證據來源各印一行）；體檢子代理依入口表逐模組檢→文字交卷候選 OBS 列＋流程摩擦；DEF 解析器與 C11 共用（ADR-SI-05）（AC-SI-31-1～31-5） | 只讀；候選入帳＝主控單窗口 |
| C18 | 人工閘（顯示面） | Console 唯讀鏡像：`si export`＋Bridge `/si/*`＋backend 代理＋frontend 頁（P2b 另含決定載體） | 根層半＝C4 套件 `export.py`（ro）＋入口 `tools/selfimproving.py export`；AgentConsole 半見下〈C18 檔名表〉 | 新建（根層半隨 P1 核心鍵；AgentConsole 半 P1b；決定載體 P2b；附錄 C.2 #12） | `export` 唯讀序列化帳本→Bridge 子行程呼叫→backend `GET /api/v1/si/**` 代理→頁面（狀態橫幅、觀察／提案／事件三分頁、待決卡面逐字＝`si card`）；SI 不可用＝503 `si_unavailable`、不得印空表；P2b：console-api 簽稽核 JSON→Bridge 落檔→主機端 `si decide --carrier console --audit-ref` 入帳（AC-SI-32-1～32-5、33-1～33-2；ADR-SI-03′） | P1b 只讀；P2b 需人工 |
| C19 | 元層 | 根層模組落點鎖 | `tools/tests/test_root_module_layout.py`（新檔；不屬 SI 套件、也不在守衛面清單） | 新建（P1；形態沿 `tools/tests/test_platform_neutral_paths.py` 的形態判準體例） | SSOT §3 登記表↔磁碟、同前綴 ≥3 支未成套件即紅（shrink-only 名冊）、套件須登記、新模組 PRD 須引 SSOT（AC-SI-34-1～34-4）；判準見下〈C19 判準〉 | 根層全套 unittest（不接 SI 閘門） |

**C4 套件檔案表（P1；`tools/lib/selfimproving/`；每檔限 `guardrail_lib` 400 斷言行；能力類別是 §9.4〈能力登記與純度判準〉的登記面——同類內拆檔不改類別、新增檔須先登記）**
| 檔 | 類 | 職責（P1） | 估算（斷言行） |
|---|---|---|---|
| `ledger`、`rows`、`git`、`refs`、`history`、`params`、`check` | ro | P0 既有；`git.py` 是唯一子行程出口（環境淨化、`-C`、timeout） | 現值 61～199 |
| `events` | ro | 事件帳本讀取與形態：JSONL 解析（容忍 CRLF）、`KINDS` 封閉詞彙、欄位表、家目錄解析 `si_dir()`（沿 `endurance_env._durable_dir_status` 形態；不可寫＝拒、不退回暫存） | 130 |
| `fold` | ro | 事件→PROP／RUN／SUSPENDED／冷卻的純函式折疊（含 §5.1.2 轉移表）；`status`、`card`、`export`、`check` 共用 | 260 |
| `evcheck` | ro | `check` 的 P1 追加項（`events.*`、`research.sources`） | 300 |
| `paths` | ro | patch 標頭路徑導出（C-style 引號解碼、聯集）、別名形態拒收、glob 比對（`**` 語意、`normcase`＋`casefold`）、`git apply --numstat -z` 超集檢查（經 `git.py`） | 280 |
| `props` | ro | `prop-new`／`prop-revise` 前置檢查（純函式）與 digest | 330 |
| `defs` | ro | DEF 帳本解析（`status`、`scan`、P3 量測腳本共用；差分測試對 `check_defect_log_crossref._load_ledger_status()`，ADR-SI-05） | 150 |
| `sources` | ro | 研究來源表載入、驗證、URL 正規化（`fetch` 與 `check` 共用） | 130 |
| `card` | ro | 卡面渲染與反解析、CJK 寬度（`card_line_max`） | 280 |
| `status` | ro | AC-SI-03-1 事件偵測 (b)～(e)、待決清單、研究事件分佈 | 280 |
| `scan` | ro | 模組體檢確定性半：五桶歸類、候選草稿列 | 340 |
| `export` | ro | `export` 序列化、游標分頁、`schema_rev` | 260 |
| `evwrite` | rw | 寫入鎖內「讀末行→配號→單次完整行追加」（`lib.apply_lock`，ADR-SI-10）、行長上限 | 140 |
| `propfiles` | rw | `SelfImproving_Proposals/PROP-SI-NNN/rN.{md,patch}` 落地 | 90 |
| `writeverbs` | rw | `run-open`／`run-close`／`attr*`／`prop-new`／`prop-revise`／`research --skip` 的組裝（判準呼叫 ro 模組、寫入呼叫 `evwrite`／`propfiles`） | 330 |
| `fetch` | net | **唯一** import `urllib`／`http`／`socket`／`ssl` 的檔：抓取、重導向把關、大小與逾時、家目錄來源檔落地；測試以政策物件允許 loopback 夾具（CLI 入口不暴露） | 230 |
| `research` | net | `research --fetch` 的組裝：鎖外抓取→鎖內重驗、算 `changed`、追加；網路層以參數注入（測試替身） | 200 |

新 16 檔合計估 3,700 行（SD 估算，未實作、未量測），單檔估 ≤ 340 ⇒ 與 tier 相容（§9.7 FC-e）；入口 `tools/selfimproving.py` 只增 argparse 子命令與 handler（估 +300，≤ 750），`research`／`writeverbs` 於 handler 內延遲 import，使 `check` 行程不載入寫入與網路碼。

**C18 檔名表（AgentConsole 半；依既有體例現查，座標見 §9.7 FC-a、FC-c、FC-d；路由與端點名實作輪不得改，檔名可依 ArchUnit／ruff 微調並回寫本表）**
| 層 | 檔／路由 | 先例座標（現查） |
|---|---|---|
| Bridge 路由 | `AgentConsole/engine-bridge/app/routers/si.py`：`router = APIRouter(prefix="/si")`；`GET /si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/{id}`、`/si/runs`（P2b 另有 `POST /si/proposals/{id}:decide`）；`main.py` 加 `include_router(si.router)` | `routers/sdd.py`:52；`main.py`:102–103 |
| Bridge 子行程 | `app/si_cli.py`：`run_export(kind, since, limit, id)`、白名單環境、`SI_CLI_TIMEOUT_SECONDS = 15.0`、`SI_EXPORT_SCHEMA_REV = 1`；整個 `app/` 只有此檔出現字面 `selfimproving.py` | `app/sdd_cli.py`:46–48、:249–310 |
| Bridge 設定與測試 | `app/settings.py` 加 `si_root`（`SI_ROOT`）；P2b 加 `si_write_token`（`BRIDGE_SI_WRITE_TOKEN`，規則同 `_parse_sdd_write_token`）；測試 `tests/test_si_cli.py`、`test_si_routes.py`、`test_si_export_differential.py`（真 CLI 對拍）、`test_si_readonly_lock.py`（AST 鎖）、`fake_si.py`（假 CLI 夾具） | `settings.py`:110–123、:154–161；`tests/test_sdd_integration_parity.py`、`tests/fake_sdd.py` |
| backend | `adapter/in/web/SiController.java`（`@RequestMapping("/api/v1/si")`；GET `/status`、`/observations`、`/events`、`/proposals`、`/proposals/{id}`、`/runs`；P2b 加 `POST /proposals/{id}/decide`）、`adapter/in/web/dto/SiExportResponse.java`（＋`SiObservationDto`、`SiProposalDto`、`SiRunDto`、`SiStatusDto`；`events` 為 `Map<String,Object>`，多型事件鍵依 `kind`、原樣轉 camelCase）、`application/port/in/SiMirrorUseCase.java`、`application/service/SiMirrorQueryService.java`（＋套件私有 `SiBridgeErrors.java`）、`application/port/out/AgentBridge.java` 加 `siExport(...)`、`domain/model/si/SiExport.java`、`adapter/out/bridge/BridgeHttpAdapter.java` 加 `siExport` 並讓 `handle()` 把 503 `si_unavailable`、404 `si_not_found` 轉 `BridgeRejectedException`（連線 2 秒、讀取 20 秒、不重試）、`BridgeEndpoints.siBase()`、`ErrorReasons` 加 `SI_UNAVAILABLE`／`SI_NOT_FOUND` | `EnginesController.java`、`SddEngineQueryService.java`、`SddBridgeErrors.java`、`BridgeHttpAdapter.java`:195–229、:793–816 |
| frontend | `app/self-improving/page.tsx`、`components/domain/si/SiView.tsx`（＋狀態橫幅、觀察／提案／事件三分頁、卡面逐字區的子元件）、`lib/api/endpoints.ts`／`queries.ts`／`types.ts` 加 SI 條目（`schema.d.ts` 重產入庫）、`lib/domain/si.ts`（游標合併等純函式）、`components/layout/ToolsRegion.tsx` 的 `NAV` 加第七項「自我進化」 | `app/settings/page.tsx`＋`components/domain/settings/SettingsView.tsx`；`ToolsRegion.tsx`:23–29 |
| P2b 另增 | Flyway 新版本 `si_decisions`；`SecurityConfig.java` 於 :82 之前加 `POST /api/v1/si/**`→`ADMIN`；`console.si.deciders`、`console.si.audit-key`、`console.bridge.si-write-token`；`components/domain/si/SiDecideDialog.tsx`（待入帳指令用 `CopyCommand`） | FC-c；`components/domain/sdd/CopyCommand.tsx` |
| 文件與 CI 連動 | `AgentConsole/docs/02_architecture/Architecture.md` §3 目錄地圖、§5.1 路由樹、§5.2 導覽六項→七項、§10 Bridge 契約、§11.1 狀態碼、§12.1 續號加一列（現查最大為 L-13；SI 鏡像的唯讀掛載前提）；契約新版（`API_Contract_P3-6.md` 後繼）；`docs/06_quality/RTM.md` 本地編號子表（先例 :469）；`docker-compose.yml`（掛載、`SI_ROOT`）；`.github/workflows/agentconsole-ci.yml` 的 `paths`；`layout.test.tsx` 的導覽斷言 | 同一 commit 收齊（根 `CLAUDE.md` 第 5 條） |

**C19 判準（Architect 棒定；AC-SI-34-1～34-4）**：解析 SSOT §3 登記表（標題含 `## 3.` 的節內、六欄資料列）；取第 2～5 欄（程式碼、入口／探針、測試、資料／文件）的反引號片段，含空白者（指令字串）、以 `~` 或 `$` 起頭者（repo 外）不判；含 `/`、結尾為已知副檔名（`.py .md .json .jsonl .yml .yaml .ps1 .sh`）或含 `*` 者為路徑候選（`ledger`、`_hook_launcher` 這類裸詞不判）；無目錄前綴的檔名片段以同欄前一個帶目錄的片段為基底，候選基底＝該片段本身（若為目錄）與其上一層，任一處命中即過（現行表兩種寫法並存：「目錄（括號內列檔名）」與「同層兄弟檔」）；含 `*` 者 glob 展開至少一檔，目錄片段須存在且含檔。**本棒探針**（scratchpad `arch_layout_probe.py`、未入庫；現行 SSOT §3 七列）：6 列正控綠、1 處紅——SelfImproving 列的 `tools/probe/selfimproving_measure.py` 尚未建檔（本 PRD C11 屬 P3，SSOT 該列卻寫「P1 探針」）⇒ 實作輪須先改 SSOT §3（該檔改為不加反引號的文字敘述，P3 建檔後再列；SSOT §4 第 1 點，不是放寬規則）、再落鎖。AC-SI-34-2 名冊初值（`tools/lib/` 現查：扁平 79 檔，≥3 支同前綴者 3 組＝`quota`〔16〕、`skip`〔6〕、`ledger`〔3〕，皆無套件目錄；shrink-only）；AC-SI-34-3 現查：含 `__init__.py` 的套件僅 `selfimproving`（已登記於 SSOT §3）；AC-SI-34-4 母體＝`docs/01_requirements/*_PRD.md` 內含字樣「模組落點表」者。

階段→元件：觀察 C1／C2／C14／C16／C17；歸因 C3；提案 C4／C5／C6／C15；人工閘 C7／C8（顯示面 C18）；套用 C9；驗證 C10／C13；量測 C11；退役 C12／C15；元層 C19。

### 9.2 資料模型
**儲存原則**
- **入 git（`docs/06_quality/`；跨機器可稽核、可 diff；單一真相＝git）**：OBS 帳本、事件帳本、PROP 內容檔、協定目錄。
- **家目錄 `~/.autosdd/selfimproving/`（機器狀態、不入 git）**：`sandbox/`（可丟棄，可由 `base`＋patch 重建）、`heldout/`（評估集內容；digest 在事件帳本）、`locks/`（事件帳本寫入鎖的鎖檔，ADR-SI-10；可丟棄，陳舊鎖會被回收）、`research/<id>/`（P1；`si research --fetch` 落地的來源原始位元組，`<sha256 前 12 碼>.txt` 與 `latest` 指標；可丟棄、可重抓）、`console_audit/`（P2b；Console 決定的稽核 JSON，**不可丟棄**——它是 `carrier=console` 之 `dec` 的回查憑證，丟失＝他機狀態、`promote` 拒；ADR-SI-03′）。解析形態沿 `tools/lib/endurance_env.py` 的 `_durable_dir_status`（ENV 逃生口 `AUTOSDD_SI_DIR`→家目錄居所）；**不可寫時不退回系統暫存**（暫存會被清、路徑長度不可控）＝fail-loud，驗證判 NE。
- **不用 `build/`**（`build/reports/` 被 `.gitignore` 忽略且屬 FSM 工具產物，BRIDGE §8.1）；**不用 PG**（AutoClaude DAL 是引擎狀態，SI 是治理紀錄；PG 若作 Console 唯讀讀模型（ADR-SI-12；P1b 不用 PG、資料每次現取自 `si export`），可由帳本重建、不得成為來源〔訂正（T1 修訂，v0.8）：原文「PG 僅在 ⏸ F-SI-101 作 Console 唯讀讀模型，可由帳本重建，不得成為來源」；F-SI-101 已再開為 FR-SI-32、33〕）；**原始輸出不入庫**（NFR-SI-02-4）：只存 `out_sha256`、`out_bytes`、遮蔽後末段摘錄。

**物件**（6 種＋運轉；事件帳本＝`docs/06_quality/SelfImproving_Event_Ledger.jsonl`）
| 物件 | ID 規則 | 核心欄位 | 載體 | 寫入者 |
|---|---|---|---|---|
| Observation | `OBS-SI-NNN`（≥3 位、遞增、不重用、不改號） | §5.1.1 九欄；檔頭 `<!-- si-ledger: tz=±HH:MM -->` | C1 Markdown 表 | 主控單一窗口 |
| Attribution | `ATT-SI-NNN` | `type=root`（`obs[]`、`items[(種類,座標)]`、根因鍵 `<面>/<機制>`）或 `type=link`（`from` 新列、`reopens` 已結列）；`by`；確認＝`attr.confirm`（確認者≠提出者）；駁回＝`attr.reject`（審查者≠立案者，附一句理由；SCG-0 二審 F-31） | 事件 `attr`／`attr.confirm`／`attr.reject` | CLI |
| Proposal | `PROP-SI-NNN`＋修訂 `rN`（配號＝max(事件帳本, OBS 帳本內既有 `PROP-SI-` 引用)＋1，於寫入鎖內計算〔ADR-SI-10〕；001～003 已被 OBS 處置文字佔用） | §5.1.2 欄位＋`run`、`base`；**`target`＝排序、去重的路徑集合（M 類邏輯根＝`memory/`）；`touched` 與檔數由 CLI 自 `rN.patch` 導出、提案者不得自填**（AC-SI-07-3）；內容檔 `rN.md`（沿 SPEC-PATCH 三節骨架：反例證據／Before／After＋影響面＋欄位表）＋`rN.patch`（unified diff，LF、原位元組） | 事件 `prop`＋`SelfImproving_Proposals/PROP-SI-NNN/` | CLI |
| Decision | `DEC-SI-NNN` | §5.1.3（`resume` 記 `run`＝`RUN-SI-NNN`、不記 `prop`）；`quote`／`sid`／`line` 由 `si decide` 抽取（座標＝該記錄的物理行號，附件載體取附件記錄本身）；`card_seq`；`digest`；`carrier`（`transcript`｜`console`，見 §5.1.3；`console` 時改帶 `audit_ref`／`audit_sha256`／`key_id`）；事件鍵 `dkind` 承載 DEC 的 `kind`（見〈事件欄位表〉） | 事件 `dec` | CLI（驗證後） |
| ApplicationRecord | `APP-SI-NNN` | `kind`＝sandbox／verify／promote／rollback；`prop`、`rev`、`base`；verify 帶 verdict、`baseline_red`／`patched_green`／`mutated_red`、`carrier_proof`、探針清單 `[(cmd, rc, out_sha256, out_bytes, n_pop, tail)]`；promote／rollback 帶 `commit_sha` 或 `reverse_patch_digest` | 事件 `app.*` | CLI |
| Measurement | `MEA-SI-NNN` | `mea.open`（prop、窗規則）／`mea.close`（clean／recurred／rolled-back／pending、`n_opp`；`pending`＝關閉時窗內仍有未決候選）／`mea.amend`（窗結果更正：`window`＝該 `mea.close` 的 `seq`、`from`、`to`、`cause`＝落定事件的 `seq`；`mea.close` 不改寫，AC-SI-23-1）／`mea.report`（`kind`＝baseline 或 check；baseline＝該 PROP 晉升前**基線窗**的機會列 ID 與窗內確認再現事件數；check＝M1～M5 值、n、窗、判準指紋）。**窗規則**（AC-SI-23-1；採納窗與基線窗共用「機會列」定義）：非 M 類＝OBS／DEF 新立列中證據路徑落在 `target` 路徑集合最近公共目錄之下者；**M 類＝新立列中根因鍵（經 `attr.confirm` 確認）與該 PROP 歸因的根因鍵相同，或證據座標／現象欄引用該記憶條目（檔名或條目標題）者**（M 類 `target` 在 repo 外，證據路徑不會落在其前綴下，SCG-0 一審 F-12）；窗以累計 `W_OPP` 筆機會列或再現／回滾先到者關閉 | 事件 `mea.*` | CLI（`--record`；量測腳本本身只讀） |
| Run | `RUN-SI-NNN` | `run.open`（trigger a～e、證據座標、`head_sha`）／`run.close`（終態清單；`no-event`） | 事件 `run.*` | CLI |
另有不建 ID 的事件：`card`（卡面送達，記 digest）、`heldout.freeze`（評估集 digest）、`research.scan`／`research.skip`（研究事件，以 `run`＋`seq` 識別；欄位見下〈事件欄位表〉；AC-SI-30-1、30-3）。

**事件帳本規約**
- UTF-8 無 BOM、LF、一行一事件、`ensure_ascii=False`；**只准追加**（既有行改寫／刪除＝`ROW-MUTATED`，AC-SI-08-4）；每行必有 `seq`（遞增不重用）、`t`（`datetime.now().astimezone().isoformat(timespec="seconds")`，帶 offset）、`kind`（封閉詞彙：`run.open`／`run.close`／`research.scan`／`research.skip`／`attr`／`attr.confirm`／`attr.reject`／`prop`／`card`／`dec`／`heldout.freeze`／`app.sandbox`／`app.verify`／`app.promote`／`app.rollback`／`mea.open`／`mea.close`／`mea.amend`／`mea.report`）、`by`（角色標籤）。
- **PROP 狀態＝對該 PROP 事件依 `seq` 折疊**，合法轉移以 §5.1.2 為唯一真相：`prop(r1)`→proposed；`dec(approve／reject／return／ack-handoff)`→approved／rejected／returned／handed-off；`prop(rN+1)`（僅 returned 後）→proposed；`app.sandbox`→sandboxed；`app.verify`→verified(verdict)；`dec(promote)`＋`app.promote`→promoted；`dec(decline-promote)`→rejected；`mea.open`→measuring；`mea.close`（clean／recurred／rolled-back）→closed(結果)，`mea.close(pending)` 維持 measuring；`mea.amend` 更正生效結果（pending→clean／recurred，clean／rolled-back→recurred；`mea.close` 不改寫）；退役＝另一筆 `action=retire` 的 PROP 走同一條鏈。冷卻、SUSPENDED、M4／M5、「同型」判定皆為事件的純函式折疊，不另存狀態。
- `si check` 反空轉：解析到的 OBS 列數／事件數低於下限（`params.json`）＝NOT-EVALUABLE。
- **多寫入者與配號（SCG-0 一審 F-11；ADR-SI-10）**：所有寫事件的 `si` 動詞（`run-open`／`research`／`attr`／`prop-new`／`card --issue`／`decide`／`sandbox`／`verify`／`promote` 等）一律在**寫入鎖**內完成「讀末行→配號（`seq`、`PROP-SI-NNN`＝max＋1）→單次完整行追加」；鎖＝獨佔建檔（`O_CREAT` 且 `O_EXCL`）的鎖檔，沿 `tools/lib/apply_lock.py` 的 `acquire`（逾時拋 `LockBusyError`＝CLI 非零 rc 並印持鎖者，fail-loud；陳舊鎖依 mtime 回收），鎖檔放 `~/.autosdd/selfimproving/locks/`（不入 git）。**不靠 `O_APPEND` 單獨保證原子性，也不用 `msvcrt.locking`／`fcntl.flock`**：R81 在本 repo 實測（`tools/lib/quota_ledger.py` 檔頭）Windows 上 `O_APPEND` 單次寫仍掉 12.2%（8 行程×40 筆）、`msvcrt.locking` 在 N=20 時行程直接死亡——一審建議的「檔案鎖＋`O_APPEND`」裡只有「鎖」承重。主控單窗口寫仍是預設做法（鐵律七檢查表 1 的精神），鎖是兜底。**併發負控**（實作輪，合成帳本）：① 確定性交錯——在「讀末行」與「追加」之間以測試鉤子暫停，雙行程各配一號：無鎖路徑（對照組）必現同一 `seq`，有鎖路徑第二者等待後得 `seq`＋1；② 多行程壓力（N≥8 行程×M 筆，量法同 R81）：行數＝N×M、`seq` 連續無重複、每行皆為完整 JSON 且 ≤ `event_max_bytes`、`PROP-SI-NNN` 無重複；③ 預置陳舊鎖檔（mtime 過期）→被回收後寫入成功；④ 預置新鮮鎖檔且不釋放→逾時非零 rc 並印持鎖者、帳本不增行。誠實劃界：鎖只管同機行程；跨機器各自追加同一帳本是 git 合併問題，由 `si check`（`seq` 唯一遞增，AC-SI-08-4 ③）事後偵測、不嘗試自動合併。

**事件欄位表（P1 範圍；`si check` 的 `events.structure` 以此驗必備鍵與型別，表外的鍵＝不合規）**：共通鍵 `seq`（正整數；鎖內末行 `seq`＋1）、`t`（帶 offset 的 ISO 8601，秒精度）、`kind`（封閉詞彙）、`by`（角色標籤）。
| `kind` | 必備鍵（共通鍵之外） | 備註 |
|---|---|---|
| `run.open` | `run`、`trigger`（`a`～`e`）、`coords[]`（≥1）、`head_sha`（40 碼；CLI 自 git 取） | AC-SI-10-3；可同時有多個 open 運轉，故 `research`／`prop-new` 一律顯式帶 `--run` |
| `run.close` | `run`、`outcomes{<PROP-ID>:<state>}`｜`no_event:true` | 零事件或零提案＝`no_event`（AC-SI-03-2） |
| `research.scan` | `run`、`sources[]{id,sha256,bytes,changed,http_status}`、`sources_sha256`、`fetched_at` | `by=researcher`；不存 `url`、不存候選數；`sha256`、`sources_sha256` 皆 `sha256:`＋64 碼；8 筆、`id` 滿 32 字元的最壞行＝1,642 bytes（每多一筆約 +174；`event_max_bytes` 2,000 約容 10 筆），寫入前以實際行長把關（超限＝rc 1） |
| `research.skip` | `run`、`reason`、`note`（一行，≤120 字元）＋（`quota-band`：`band`｜`helmsman`：`sid`、`line`） | `by=main`；`reason` 為封閉集合（AC-SI-30-1） |
| `attr`／`attr.confirm`／`attr.reject` | `attr`：`id`（`ATT-SI-NNN`）、`type`（`root`｜`link`）、`obs[]`、`items[[種類,座標]]`、`root_cause`（`root`）｜`from`＋`reopens`（`link`）；`attr.confirm`／`attr.reject`：`att`（`reject` 另必帶 `note`） | 確認者與審查者≠提出者（`by` 角色標籤，AC-SI-06-1） |
| `prop` | `id`、`rev`、`run`、`base`、`cls`、`action`、`route`、`target[]`、`touched_count`、`touched_sha256`、`patch_sha256`、`body_sha256`、`digest`、`sources[]`、`preimage{}`（M 類）、`proposer`、`reviewer` | 只存結構欄；自由文字欄（`rollback`／`retire_when`／`reopen_symptom`／`budget`／`verify_plan`）住 `rN.md`（`body_sha256` 綁定）；完整 `touched` 自 `rN.patch` 重新導出，`touched_sha256`＝排序去重後路徑集合的 sha256；行超 `event_max_bytes`＝`prop-new` 拒收並要求拆分（§9.7 #49） |

P2 起的 `kind`（`card`、`dec`、`heldout.freeze`、`app.*`、`mea.*`）欄位見各 FR。凡物件欄位與事件共通鍵 `kind` 同名者，事件鍵改名：`dec` 以 `dkind` 存 DEC 的 `kind`（§5.1.3；CLI 旗標仍是 `--kind`）、`mea.report` 以 `report`（`baseline`｜`check`）存其 `kind`，`app.*` 的種類由事件 `kind` 後綴承載（`app.verify`＝verify）。

**研究來源表 `research_sources.json`（AC-SI-30-2）**：UTF-8（無 BOM）、LF、結尾換行；頂層 `{"schema_rev":1,"sources":[…]}`；`sources` 依 `id` 位元組序遞增、每筆恰五鍵 `id`／`url`／`kind`／`extract`／`added_by`（型別與規則見 AC-SI-30-2）；`schema_rev` 起於 1，改鍵名或語意須升版（`check` 對不認得的版本＝紅）。

**`export --json` 輸出（FR-SI-32；`schema_rev` 起於 1）**：單一 JSON 文件，UTF-8 位元組直寫（`ensure_ascii=False`、LF、無 BOM）；頂層鍵固定順序 `schema_rev`、`kind`、`generated_at`（呼叫時刻、帶 offset，不參與差分）、`head_sha`（`git rev-parse HEAD`；git 不可用＝`null` 並列入 `ne`）、`items`（陣列）、`next_since`（整數或 `null`）、`truncated`（布林）、`ne`（`[{field,reason}]`：量不到的欄位逐一列出、不省略，NFR-SI-09-1、NFR-SI-06-6）、`problems`（`[{subject,code,detail}]`：帳本結構層問題，例如無法解析的行；不是 `check` 的判級）。`items` 依 `kind`：`observations`＝九欄（鍵 `id`、`time`、`context`、`symptom`、`evidence`、`category`、`severity`、`disposition`、`marks`，皆字串）加 `marks_kv`（`rows.parse_marks` 的解析）與 `line`（帳本 1 起算實體行號），欄數不是九的列＝`{line,raw,valid:false}`；`events`＝事件原樣（不加鍵）；`proposals`＝`id`、`state`、`route`、`cls`、`action`、`run`、`rev`、`digest`、`target[]`、`touched[]`（自 `rN.patch` 現導）、`touched_count`、`sources[]`、`created_seq`、`last_seq`、`verdict`、`flags[]`、`cooldown`（物件或 `null`）、`card`（`si card` 逐字輸出，LF）；`runs`＝`id`、`opened_seq`、`closed_seq`、`trigger`、`head_sha`、`research`（`{kind,seq}` 或 `null`）、`prop_ids[]`、`outcome`；`status`＝`items` 為單元素陣列，元素＝`si status --json` 的物件（至少含 `events_detected[]`、`open_runs[]`、`pending_props[]`、`suspended`、`cooldowns[]`、`skip_reasons{}`、`capacity`）。游標：`--since N`＝嚴格大於 N（`events` 取 `seq`；`observations`、`proposals`、`runs` 取 ID 的數字部分；`status` 不收）；`--limit N` 預設與上限＝`export_limit_max`（初值 500，無先例、未校準；超過＝rc 3）；`next_since`＝本頁最後一筆的游標、已無下一頁＝`null`，`truncated`＝是否因 `--limit` 截斷。`--id <PROP-SI-NNN｜RUN-SI-NNN>`（只收 `proposals`／`runs`）取單筆，找不到＝`items:[]`、rc 0（HTTP 語意由 Bridge 判）。事件帳本檔不存在＝`items:[]` 並於 `ne` 列 `events: carrier-not-established`（不是零筆通過）。**Console 不得見的內容**：`export` 不讀、不印 `~/.autosdd/` 下任何檔（含 `console_audit/`、`research/`），以測試釘住（把哨兵字串放進 `AUTOSDD_SI_DIR` 後輸出不得含它）。差分（AC-SI-32-1）以 `schema_rev` 與逐欄比對為準。

**digest**：`"sha256:" + sha256(canonical(core))`；`core`＝{`id`, `rev`, `cls`, `action`, `target`（**排序、去重的路徑集合**；POSIX 邏輯路徑，M 類邏輯根＝`memory/`、形如 `memory/<檔名>`）, `touched`（**自 `rN.patch` 導出的全部觸及路徑**，排序、去重：`diff --git` 標頭、`---`／`+++`、`rename from／to`、`copy from／to`，新增、刪除、改名兩端皆算；導出法見 §9.4、Q12）, `touched_count`（檔數）, `base`, `preimage`（原名 `touched_preimage`，改名以免與 `touched` 混淆：M 類＝被觸及行的逐檔 sha256，非整檔——harness 併發自寫其他行不致使核准失效；其餘＝`base`）, `patch_sha256`, `body_sha256`, `rollback`, `retire_when`, `reopen_symptom`, `budget`}；`canonical`＝`json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` 的 UTF-8；文字先 CRLF→LF 再雜湊（先例 `tools/probe/fivequestion_ledger.py` 的 `manifest_sha`）；`target` 與 `touched` 皆在 digest 內（AC-SI-07-3），核准綁定的是「這組路徑」；digest 內的路徑一律存正規化後的 repo 相對 POSIX 形、**保留原大小寫**，`normcase`／`casefold` 只用於 glob 比對（Windows 與 POSIX 的 `normcase` 不同，若入 digest 則同一 PROP 在兩平台算出不同值，鐵律三）；重算 digest 時 `touched` 由 CLI 重新導出、不信任事件裡存的值；卡面顯示前 8 碼，DEC 存全值。

**與既有物件的對映**
| 既有物件（座標） | 與 SI 的關係 |
|---|---|
| DEF 列（`docs/06_quality/AutoSDD_Defect_Log*.md`） | 真缺陷以 OBS 處置 `DEF-<id>` 升級；M1～M3 讀其狀態／現象欄；DEF 側復發標記＝現象欄 `reopens:DEF-xxx` 文字慣例（C.2 #3，不改表頭） |
| SPEC-PATCH（`docs_template/sdd/requirements/SPEC-PATCH-TEMPLATE.md`；`spec_patch_proposer.propose()` 寫 `docs/01_requirements/SPEC-PATCH-{AC}-{date}.md`） | **複用三節骨架**為 PROP 內容檔；不複用其檔案位置與產生器（該位置在 R-9.6 擋寫區、語意只涵蓋 AC 補丁）；R／D 類 `target` 可指向真實 SPEC-PATCH 座標 |
| SLV 候選（`slv_generator.write_rule_candidate`；`trust_level: proposed`、`reviewed_by: null`） | R 類 `target`＝候選 yaml 座標；本迴圈的晉升＝合入 proposed 候選（不阻塞 SCG，AC-SI-08-3）；轉 `verified`／退役仍走 `set_maturity(reviewed_by=)`（SDD 既有人工動作，非本迴圈，禁令 11） |
| FSM `decision_trace`／FSM-STATE（`build/reports/fsm/`，不入庫） | 不複製；PROP 只引用「專案鍵＋trace 序號」；SI 只經 `show` 讀 |
| AutoClaude `PROPOSALS-<project>.jsonl` | 觀察來源（唯讀）；**不轉成 PROP**——其目標是 adapter 轉譯程式碼，不在 M／P／R／D 內，歸因後走 DEF（handoff） |
| EvolutionPlugin `MutationProposal` | Kernel 路徑僅 log 一行（Q4）；MVP 由歸因者讀 dump／log 後登記 P 類 PROP；結構化落地＝已列 §3.3 F-SI-105 |
| AutoClaude checkpoint／escalation dump／KB jsonl | 觀察來源（唯讀）；KB 的 `outcome` 欄＝既有結果標籤先例 |
| Claude Code 記憶（`claude_home()/projects/<slug>/memory/`） | M 類目標（repo 外）；ADR-SI-06 |

**鐵律三自問**（「這在另一個平台是什麼值」；macOS 全部未驗，NFR-SI-06-5）
| 落點 | 另一平台的值／風險 | 處置 |
|---|---|---|
| 帳本／PROP 檔（Markdown、JSONL、patch） | `.gitattributes` 的 `* text=auto eol=lf` 使兩平台工作樹皆 LF，編輯器仍可能造 CRLF | 寫入一律 UTF-8＋`newline="\n"`；讀取容忍 CRLF；digest 先 CRLF→LF |
| 時間戳 | 本機時區在他處可能有 DST（naive 相減靜默錯） | 一律 aware（`astimezone()`）；OBS 時間欄列內 offset 或檔頭 `tz=`；既有鎖 `tools/tests/test_platform_neutral_paths.py::TestNaiveLocalTimestampsAreNotPersisted` |
| 家目錄路徑 | Windows `C:\Users\<名>\.autosdd\…`、POSIX `$HOME/.autosdd/…` | 經 `endurance_env` 形態解析；比對用 `realpath`＋`normcase`（NTFS 大小寫不敏感）；不寫死 |
| patch 路徑與 `touched` | Windows 路徑大小寫不敏感、反斜線與正斜線皆為分隔符、片段尾端的點與空白會被收掉、冒號是磁碟機代號或 NTFS 資料流；POSIX 上這些是合法檔名字元或不同語意 | 解析時先拒絕別名形態（fail-closed→handoff，§9.4）；glob 比對一律 `normcase`＋`casefold`（POSIX 的 `normcase` 是恆等函式，macOS 預設卻大小寫不敏感）；digest 存原大小寫路徑；兩平台對同一 patch 必須導出同一個 `touched`（macOS 未驗） |
| 寫入鎖（事件帳本） | Windows 與 POSIX 的位元組層級鎖語意不同（`msvcrt.locking` 對 `fcntl.flock`）；R81 實測 Windows 上前者在 N=20 時行程死亡、`O_APPEND` 跨行程不原子 | 只用獨佔建檔（`O_CREAT` 且 `O_EXCL`），兩平台語意一致（`tools/lib/apply_lock.py`）；鎖檔在家目錄（ADR-SI-10） |
| 逐字稿路徑與欄位 | slug 規則與 `origin`／`isMeta`／`turnOrigin` 皆觀察所得、非官方契約（`tools/probe/audit_session.py`:250–257；欄位見 `.claude/hooks/check_claim_provenance.py`:854–866） | `claude_home()` SSOT（尊重 `CLAUDE_CONFIG_DIR`）；缺欄位＝NE |
| git 呼叫 | `core.quotepath`／`core.longpaths` 是本機設定、不隨 repo | `-c core.quotepath=false`＋`-z`、`encoding="utf-8", errors="replace"`、不用 `shell=True` |
| 行程樹終止（驗證逾時） | Windows 無 `killpg` | Windows `taskkill /T`／POSIX `os.killpg` 各自平台守衛（鐵律三「外部執行檔 argv[0]」觸發項；`ConsoleFreeSpawnTest` 判 console 視窗），實作輪逐項自問 |
| 主控台編碼 | cp950 主控台印 `🔴` 即 `UnicodeEncodeError`（SD 普查腳本實踩）；`python -I` 會忽略 `PYTHONIOENCODING` | CLI 入口 import `tools/_stdio_utf8.py`；不靠環境變數 |
| Console 容器（Linux）內以子行程呼叫根層 CLI（P1b） | 容器內路徑是 `<SI_ROOT>/…`（≠主機路徑）；直譯器是 Bridge 自己的 `sys.executable`（不是根 `.venv`）；locale 可能是 POSIX；`git` 對 bind mount 的擁有者檢查（映像使用者 uid 10001≠主機擁有者＝`dubious ownership`）；唯讀掛載下 `.pyc` 寫不進去 | 路徑一律相對 `SI_ROOT` 並 `realpath`、不寫死磁碟路徑；子行程環境白名單加固定 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`；**不帶 `-I`／`-P`**（3.11 起 `-I` 蘊含 `-P`，腳本目錄不進 `sys.path`，`import _stdio_utf8` 與 `from lib…` 失敗；本棒以 3.11.9 實測 `python -I` 的 `sys.flags.safe_path` 為真）；`git` 以 `GIT_CONFIG_COUNT=1`、`GIT_CONFIG_KEY_0=safe.directory`、`GIT_CONFIG_VALUE_0=<SI_ROOT>` 只對該路徑放行（CLI 的 `git.py` 只剝定位用 `GIT_*`、不剝 `GIT_CONFIG_*`；映像 `git` 須 ≥2.31；**未實測**，P1b 實作輪以真容器驗）；輸出 UTF-8 無 BOM |
| 研究來源檔 `<sha12>.txt`（P1） | 原始位元組可含 CRLF、BOM、非 UTF-8 的 charset；Windows 檔名不分大小寫（`<id>` 為小寫連字號、`<sha12>` 為小寫 hex，無碰撞）；Windows 路徑長度 | 位元組原樣寫入（二進位模式、不轉行尾、不剝 BOM）；`sha256` 對原始位元組算、**不經**本表第一列的 CRLF→LF 正規化（來源檔不是 repo 文字，原樣才可用 `sha256sum`／`Get-FileHash` 複驗）；非 UTF-8 回應照存、不轉碼（`Content-Type` 檢查只擋非文字類）；研究者以 Read 讀（工具自行處理編碼）；家目錄根經 `si_dir()`、長度現查 |
| `export` 的 JSON 輸出（P1） | Windows 文字模式 stdout 把 `\n` 變 `\r\n`；cp950 主控台印非 ASCII 會 `UnicodeEncodeError`；`ensure_ascii=True` 把中文轉成 `\uXXXX`（差分與肉眼皆不利）；`generated_at` 帶容器時區（多為 UTC） | `ensure_ascii=False`、UTF-8 位元組直寫 `sys.stdout.buffer`（沿 `tools/selfimproving.py` 的 `_emit`）、LF、無 BOM；入口 import `_stdio_utf8`；Bridge 以位元組讀 stdout 後 UTF-8 解碼；顯示層依 offset 顯示、不當本機時間（NFR-SI-06-6 (vi)） |

### 9.3 介面
**CLI**（**不走 FSMRuntime CLI**：禁令 8／9 與 BRIDGE §8.0「不新增 CLI 動詞」同精神；PROP 生命週期橫跨多個功能週期，與 FSM「一功能一鍵」不同單位）
| 動詞（階段） | 做什麼 | 讀寫 | 標示 |
|---|---|---|---|
| `check`（P0；P1 起重放事件帳本） | OBS 欄位／tz／枚舉／`fixed@<sha>` 可解析／≤700B／欄內控制字元（含 TAB）＝拒收（SCG-0 二審 F-35）／`ROW-MUTATED`（**自 `params.json` 的 `migration_base_sha` 起**對 HEAD 與歷次提交逐對比較同 ID 列；該 sha 須存在且為 HEAD 祖先〔`git merge-base --is-ancestor`〕，否則 `check` 紅、不靜默放行；缺值，或缺掌舵者確認列〔處置 `decided`、文字含該 sha 與 `sid`＋`line` 座標；P0 只驗存在與格式、不驗引言〕＝遷移未豁免，自第一個提交起比對、遷移改動的列標 `ROW-MUTATED`，AC-SI-01-3／04-3；事件帳本無遷移、自首個提交起比對，AC-SI-08-4）／引用完整性／`params.json` 對表（PRD 引用的參數名須存在〔含 `migration_base_sha`、`w_evt`〕、`non_evolvable_globs` 與 NFR-SI-02-1 一致、`w_opp ≥ w_min`，違反＝紅）；（P1 起）`prop` 事件的 `touched`／`patch_sha256` 與內容檔 `rN.patch` 重算一致，不符＝標紅；（P1 起）每個有 `prop` 的運轉恰有一筆研究事件（`research.scan`／`research.skip`，其 `seq` 介於該運轉的 `run.open` 與第一筆 `prop` 之間；`reason` 在封閉集合內、`helmsman` 帶可定位的座標；AC-SI-30-1）、研究來源表自身合規、`回報者=研究者` 的列必為 `外部衍生=是` 且帶 `src`、任何帶 `src` 的列其 `src` ∈ 來源表（AC-SI-30-2、30-4），不符＝標紅；（P2 起）每筆 `dec` 回查引言（`sid`＋`line` 可定位且逐字相符、出處與錨定合法，AC-SI-12-4 ⑤），不符＝標紅（附該 `dec` 的 `seq`）、逐字稿取不到（他機）＝NE；新列的復發候選提示；**P1 追加項**（21 項原樣保留，id、順序、語意、判定碼不變；追加項接在其後，載體缺席一律 nonblocking NE〔`CARRIER-NOT-ESTABLISHED`〕，故 P0 基線 repo 的 rc 與 overall 不變）：`events.structure`（JSONL 形態、`seq` 唯一遞增、`t` 帶 offset、`kind` 封閉詞彙、行長 ≤ `event_max_bytes`）、`events.transitions`（§5.1.2 合法轉移）、`events.mutated`（自首個提交起比對，AC-SI-08-4 ②）、`events.vacuity`（事件數低於 `min_events`＝NE）、`events.prop_files`（`touched_count`／`touched_sha256`／`patch_sha256`／`body_sha256` 與 `rN.*` 重算一致）、`events.research`（AC-SI-30-1 重放）、`research.sources`（AC-SI-30-2 表驗證）；P2 另加 `events.dec_quote`、P2b 另加 `events.dec_console`；`src` 加入標記鍵集合，`row.provenance`／`row.markers` 加判定碼 `RESEARCHER-NOT-EXTERNAL`、`RESEARCHER-NO-SRC`、`SRC-UNKNOWN`（AC-SI-30-4）；`params.json` 對表加 `research_fetch_max`、`research_bytes_max`、`research_timeout_seconds`、`min_events`、`export_limit_max`（`PARAM_SPECS`）；P0 測試中依賴總項數 21 的斷言改為前綴比對（P1 TCS；§9.7 #48） | 只讀 | 只讀 |
| `status`（P1） | AC-SI-03-1 事件偵測＋待決清單＋SUSPENDED／冷卻（SUSPENDED 時印出其所在運轉 `RUN-SI-NNN`，即 `恢復` 的綁定值，§7.2）；(d)＝已確認的復發連結指向某 promoted PROP 的 `sources`（觸發判定用；M1 的再現歸屬另依根因鍵，§1.3〈M1 判定細則〉(a)；`reopen_symptom` 為自由文字，只供人判讀、不機械比對）；印未決再現候選數與 `pending` 的採納窗（AC-SI-23-1）；交卷對帳（NFR-SI-09-2，只量不閘）；另印本運轉的研究事件有無與歷來免掃的原因分佈（資訊欄，AC-SI-30-1）；旗標 `--json`（輸出＝`export --kind status` 的 `items[0]`，同一函式）、`--repo`；容量事件（AC-SI-03-1 (e)）於 P3 `capacity` 動詞建成前印 NOT-EVALUABLE（不得印成零）；交卷對帳需逐字稿，容器內＝NOT-EVALUABLE（NFR-SI-06-6） | 只讀 | 只讀 |
| `research`（P1） | 研究掃描的唯一寫入口（AC-SI-30-1～30-6）：`--fetch --run RUN-SI-NNN [--sources <路徑>] [--json]`＝依 AC-SI-30-3 抓來源表 URL 的原始位元組、落地家目錄來源檔、寫 `research.scan`（**唯一可連網的動詞**；`User-Agent` 固定為 `selfimproving-research/1`）；`--skip --run RUN-SI-NNN --reason {quota-band｜offline｜helmsman} --note <一行> [--band <值>｜--sid <UUID> --line <N>]`＝寫 `research.skip`（零網路；`quota-band` 必帶 `--band`、`helmsman` 必帶 `--sid`＋`--line`，P1 只驗格式）。`--run` 須是已 `run.open`、未 `run.close` 的運轉，且該運轉尚無研究事件（有＝rc 1）。rc：0＝事件已寫、每個來源皆成功；2＝事件已寫、≥1 來源失敗（逐一列出，已抓的照記）；1＝未寫（來源表驗證失敗、筆數超界、零來源成功、運轉不合、取鎖逾時〔印持鎖者〕、事件行超 `event_max_bytes`；一律印可貼入的 OBS 草稿列）；3＝用法或輸入錯誤（含家目錄不可寫，不退回暫存）。網路只在 `fetch.py`；抓取在寫入鎖之外、鎖內只重驗（運轉仍開、尚無研究事件）與追加 | 寫事件＋家目錄來源檔 | 提案（候選；寫事件） |
| `scan`（P1） | `scan [--json] [--since <commit>] [--repo DIR]`：模組體檢的確定性半（AC-SI-31-1～31-4）：唯讀、離線、無狀態、不寫事件，彙整本地證據印 OBS 候選草稿列（五模組桶＋未分類；每個證據來源各印一行：讀到 N 筆／量不到）；零候選印「無事件」；`--since` 只收 commit（7～40 位 hex，解析不到＝rc 3），覆寫候選彙整的起算點、不收日期、筆數或相對寫法；rc：0＝已執行（零候選仍 rc 0）、3＝無法執行；不接任何閘門 rc | 只讀 | 只讀 |
| `run-open`／`run-close`（P1） | 運轉識別與輸入快照 | 寫事件 | 提案 |
| `attr`／`attr-confirm`／`attr-reject`（P1） | 歸因與復發連結（確認者≠提出者）；審查者可駁回再現候選（附一句理由）；confirm／reject 落定時，於同一把寫入鎖內重折疊受影響的採納窗，必要時追加 `mea.amend`（AC-SI-23-1） | 寫事件 | 提案 |
| `prop-new`／`prop-revise`（P1） | 建 PROP（§9.4 前置檢查）、修訂（≤`MAX_REVISIONS`） | 寫事件＋內容檔 | 提案 |
| `card`（P1）／`card --issue`（P2） | `card PROP-SI-NNN [--json]`：確定性卡面＋反解析檢查（rc 0／3）；`--issue` 記 `card` 事件（寫入類 rc） | 只讀／寫事件 | 只讀／提案 |
| `decide`（P2） | 自逐字稿抽取並驗證掌舵者引言→DEC（approve／reject／return／promote／decline-promote／unblock／resume／ack-handoff／rollback；動詞對映見 §7.2 動詞表，錨定規則與負控見 C8；P2b 起另有 `--carrier console --audit-ref <id>`＝FR-SI-33，驗證與入帳見 ADR-SI-03′） | 寫事件 | **需人工** |
| `heldout-freeze`（P2） | 凍結評估集（內容在家目錄、digest 入帳） | 寫家目錄＋事件 | 提案（凍結者角色） |
| `sandbox`／`verify`（P2） | 匯出沙盒、套 patch、三步驗證、載具自證、預算逾時收 verdict | 寫家目錄＋事件 | 提案（副本） |
| `promote`／`rollback`（P2） | 對主工作樹套用／反套用（先驗 DEC〔對 `approve` 與 `promote` 兩筆重跑 AC-SI-12-4 回查，不符或逐字稿取不到＝拒絕〕＋digest＋pre-image；不 commit） | 寫主工作樹＋事件 | **需人工** |
| `capacity`（P3） | 容量偵測（記憶索引位元組／行數、KB `kb_cache_eviction_count`、偏好鍵數） | 只讀 | 只讀 |
| `export`（P1b；根層半隨 P1 核心鍵交付，附錄 C.2 #12） | `export --json --kind {observations｜events｜proposals｜runs｜status} [--since N] [--limit N] [--id <PROP-SI-NNN｜RUN-SI-NNN>] [--repo DIR]`（AC-SI-32-5）：唯讀序列化，供 Bridge 以子行程呼叫；輸出 schema 與游標語意＝§9.2；`--json` 必帶（缺＝rc 3）；`--kind` 為封閉集合；與 `status`／`card`／`check` 共用同一組折疊與卡面函式（`fold.py`、`card.py`）；rc：0＝已輸出（`ne`／`problems` 非空不是錯誤）、3＝用法或輸入錯誤（`--kind` 不在集合、`--limit` 超 `export_limit_max`、repo 不可讀） | 只讀 | 只讀 |
| `tools/probe/selfimproving_measure.py`（P3） | M1～M5＋資訊欄＋判準指紋（＝`SelfImproving_Protocol/` 各檔 CRLF→LF 後雜湊〔先例 `manifest_sha`〕＋`params.json` 的 `metrics_rev`；量測碼語意變動時人工 bump，先例：量測碼不入 manifest）。**M1 為 per-PROP 前後對照**（AC-SI-22-1）：NE 護欄量**事件數**而非列數——該 PROP 基線窗（`mea.report` baseline 所記）內確認再現事件數 ≥ `W_EVT` 且機會列數 ≥ `W_MIN` 才可評估，基線事件數 0 一律 NE（不得算「未低於」）；採納窗結果 `recurred`（因再現提早關閉，照樣可評估）／`clean`（已累計 `W_OPP` 筆機會列）／`rolled-back`（窗內無確認再現者 M1 不評估、仍計 M5）；**全域 `W_N`（初值 20）列窗的 M1，以及 M2、M3，一律印在資訊欄**，不得單獨宣稱成效；**M5 兩值並列於成功指標區**——主值不含 `unverified_ack` 採納、另一值含之（AC-SI-22-2）；再現候選只讀已寫入的標記（`reopens`／現象欄 `reopens:DEF-xxx`）與 `attr.confirm`／`attr.reject`，不在量測期掃描產生（AC-SI-06-2）。**基線與再現候選的起點**＝`migration_base_sha` 那個 commit 的 committer 時間（UTC，`git show -s --format=%ct` 現查；主控裁決，SCG-0 二審 F-29）：更早的 DEF／OBS 列不計再現候選、也不進基線窗（日精度的 DEF 列以日期比對錨的 UTC 日期，早於者排除、同日者納入）；窗結果取生效結果（`mea.close` 加最後一筆 `mea.amend`），`pending` 的窗不計入分母；再現歸屬、窗重疊、「連續」、M 類機會列與再現重疊、M5 趨勢、`W_OPP ≥ W_MIN` 依 §1.3〈M1 判定細則〉(a)～(f) 實作。窗序＝（發現日期, ID 數字鍵）合併 DEF 與 OBS（日精度，同日以 ID 鍵決勝）；DEF 解析器自寫，並以**差分測試**對真帳本釘住「與 `check_defect_log_crossref._load_ledger_status()` 對同批列給同組（ID, 結案類）」 | 只讀 | 只讀、不接閘門 |

**rc 通則與共通旗標**：`check`＝0（綠）／1（不合規）／2（未判）／3（無法執行）；唯讀非閘門動詞（`status`、`scan`、`card`、`export`）＝0（已執行）／3（無法執行）；寫入動詞＝0（已寫）／1（拒收：前置檢查失敗或取鎖逾時；未寫、印可貼入的 OBS 草稿列）／3（用法或輸入錯誤，含家目錄不可寫），`research --fetch` 另有 2（部分成功）。共通旗標 `--repo DIR`（預設＝本檔所在 repo；容器內＝`SI_ROOT`）、`--json`。入口一律先 import `_stdio_utf8`、輸出以位元組直寫（沿 `tools/selfimproving.py` 的 `_emit`）。`AUTOSDD_UNATTENDED` 有設時 `decide`／`promote`／`rollback` 一律非零 rc（P2；既有）；P1 寫入動詞照常（迴圈在無人值守下可執行到提案止，NFR-SI-02-3）。

**Bridge／Console（P1b 唯讀鏡像；P2b 決定載體）**：沿 `AgentConsole/docs/02_architecture/Architecture.md` §10／§10.1／§10.2 體例（Bridge 契約的唯一消費者是 console-api；Bridge 回 snake_case、backend 轉 camelCase；錯誤封包含 `code`／`reason`）。**P1b（FR-SI-32；全為 GET）**：Bridge `GET /si/status`、`GET /si/observations`、`GET /si/events`、`GET /si/proposals`、`GET /si/proposals/{id}`、`GET /si/runs`（查詢參數只有 `since`〔整數游標，對映 `export --since`〕與 `limit`〔對映 `--limit`〕，其餘一律不收；`{id}` 須符 `^PROP-SI-\d{3,}$`，不符＝422 `invalid_request`，找不到＝404 `si_not_found`）——Bridge 以子行程呼叫 `python <SI_ROOT>/tools/selfimproving.py export --json --kind <k> …`（沿 `sdd_cli.run_verb` 體例：`Popen`＋`communicate(timeout)`、逾時 `_reap`、`procutil.popen_platform_kwargs()`；逾時 15 秒〔`si_cli.py` 常數 `SI_CLI_TIMEOUT_SECONDS`；須小於 backend 讀取逾時 20 秒，初值、未校準〕；子行程環境**白名單**：`PATH`、`SYSTEMROOT`、`TEMP`、`TMP`、`HOME`、`USERPROFILE`、`LANG`、`LC_ALL`，加固定 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1` 與 `safe.directory` 三鍵〔不繼承 `BRIDGE_*`、`MINIMAX_API_KEY` 等任何機密——`sdd_cli.build_cli_env` 只剝 `BRIDGE_*`／`SDD_*`／`PYTHONPATH`、其餘環境原樣繼承，export 子行程不需要任何機密〕；stdout 上限 8MB（初值，無先例、未校準），須恰為單一 JSON 文件且 `schema_rev` 等於 Bridge 釘住的常數 `SI_EXPORT_SCHEMA_REV`），自身不開帳本檔、不 import 根層 `tools/lib`；**`SI_ROOT`**＝伺服器端設定（環境變數，沿 `SDD_ROOT` 體例；本機直跑且 `_looks_like_monorepo` 時預設為 monorepo 根，Docker 為掛載點），請求不帶任何路徑參數，所以沒有路徑 allowlist 可言（不併入 `BRIDGE_ALLOWED_PATH_ROOTS`：那是引擎 `execution_path` 的閘〔NFR-SEC-03〕，把 SI 根放進去會讓引擎可被指向掛載的 repo；啟動時拒檔案系統根〔`settings._anchor_guard`〕）；SI 不可用＝503 `si_unavailable`（`SI_ROOT` 未設或不含 `tools/selfimproving.py`、子行程逾時、rc 非 0、stdout 非單一合法 JSON、`schema_rev` 不符；`detail`＝`rc=<n>; stderr=<末 1,000 字元>`；先例：`routers/sdd.py` 的 503 `sdd_unavailable`）；backend `GET /api/v1/si/**` 逐一代理（JWT；Viewer 以上可讀）、連線 2 秒／讀取 20 秒、不重試，`BridgeHttpAdapter.handle` 把 503 `si_unavailable` 與 404 `si_not_found` 視為明確拒絕（沿 `sdd_write_disabled` 的處理）原因逐字轉出，Bridge 不可達或逾時沿 502／504；frontend 新頁 `/self-improving`（狀態橫幅、觀察／提案／事件三分頁、待決 PROP 的卡面逐字＝`si card` 輸出；SI 查詢 `retry:false`、`staleTime:0`、`gcTime:0`，`isError` 時只顯示錯誤態與原因、不渲染 `data`）。**P2b（FR-SI-33；需人工）**：Bridge `POST /si/proposals/{id}:decide`（`X-Bridge-Token`＝`BRIDGE_SI_WRITE_TOKEN`，未設即 503 `si_write_disabled`、錯＝403 `si_write_forbidden`）只把 console-api 簽好的稽核 JSON 原樣寫入稽核目錄 `<AUTOSDD_SI_DIR>/console_audit/<audit_ref>.json`（Bridge 不驗簽、不開帳本檔、不呼叫任何寫入型 CLI 動詞）；`dec` 由主機端 `si decide --carrier console --audit-ref <id>` 驗證後入帳（ADR-SI-03′）。Console 對 FSM 與帳本，P1b 全程只讀，P2b 的寫入只有稽核 JSON 落檔一條。〔訂正（T1 修訂，v0.8）：原文「Bridge／Console（⏸ F-SI-101 的命名骨架；MVP 無）」；F-SI-101 已再開，原骨架的 `GET /si/proposals`、`GET /si/proposals/{id}`、`POST /si/proposals/{id}:decide` 三條保留並擴充。〕
**EventBus／Plugin**：MVP 不新增 KernelPhase／Plugin／事件；若日後要由引擎主動發 SI 事件，須走 Plugin SOP 六步＋`.importlinter` Rule 1 清單同步＋`wiring._REGISTER_ORDER`＋LOC 分級。引擎側一律讀已落地檔案（檔案契約，同 Rule 9 精神）。

### 9.4 安全與停機
**邊界三型**（本 PRD 任何「不能做／被拒」宣稱必須註記屬哪型；**P 型不得寫成「被擋」**）：**M**＝機械可擋且可測（SI CLI 前置檢查、`si check`、pytest AST 普查）；**D**＝偵測型（事後量測、只出聲不阻擋：對 HEAD 比對、逐字稿掃描）；**P**＝流程型（任務書／SOP 約束，無機械物）。

**對抗分離落點（評估器 vs 生成器）**
| 角色 | 看得到 | 看不到 | 可寫 | 隔離型 |
|---|---|---|---|---|
| 擷取者（Sonnet） | 逐字稿、dump、量測器輸出 | held-out、`params.json` | 無（文字交卷，OBS-SI-004） | P |
| 研究者（Sonnet） | 研究來源表、`si research --fetch` 落地的來源檔（資料）、本運轉的 `run.open` | held-out、`params.json`、指標目標值 | 無（文字交卷；來源檔由 CLI 落地到家目錄，研究者無 Write 權） | P（工具白名單 Read／Grep／Glob，無 Web 工具）＋M（`research --fetch` 只抓表內 URL、digest 由 CLI 對原始位元組重算） |
| 體檢子代理（Sonnet；歸因者的唯讀子角色） | 體檢入口表所列文件、既有輸出檔、唯讀指令輸出 | held-out、`params.json`、指標目標值 | 無（文字交卷） | P＋D（體檢前後 `git status --porcelain`／HEAD 對照，AC-SI-31-5） |
| 歸因者（Sonnet） | OBS 群＋證據座標 | held-out、指標目標值與計算 | `attr` 事件（經 CLI） | P＋M（欄位檢查） |
| 凍結者（≠提案者） | 全帳本 | — | `heldout/`（家目錄）、`heldout.freeze` | M（digest） |
| 提案者（Sonnet） | 抽象化摘要（帶結果標籤與適用範圍，AC-SI-09-1） | held-out、`params.json`、指標目標值 | scratchpad 成品＋`prop-new`；不得寫正式面／DEC／APP | P＋D（AC-SI-20-4 暴露掃描） |
| 審查者（Sonnet，≠提案者） | PROP＋驗證證據 | 同提案者 | 無（唯讀） | P（ADR-SI-09） |
| 驗證執行 | 確定性 CLI（主控呼叫）；LLM 意見次級（AC-SI-18-2） | — | `app.*` 事件 | M |
| 主控 | 全部 | — | 帳本（單窗口）、`decide`／`promote`／`rollback`（驗證後）；不得代核准 | M（`decide` 驗引言） |

**每階段預算與停機**（數值皆「初值（未校準）」，住 `params.json`；計數來源＝事件帳本折疊，非記憶）
| 階段 | 次數／牆鐘／token | 停機條件→動作 |
|---|---|---|
| 觀察擷取 | 零扇出；OBS 單列 ≤ `ROW_MAX_BYTES` | 超長→拒收、長內容搬附註檔 |
| 研究掃描 | 每運轉至多 1 個研究者；來源表筆數 ≤ `RESEARCH_FETCH_MAX`、每來源原始位元組 ≤ `RESEARCH_BYTES_MAX`、每來源牆鐘 ≤ `RESEARCH_TIMEOUT_SECONDS`（CLI 強制；守衛對 Web 工具的節流不牽制 CLI）；零遞迴 | 來源表筆數超界→整次拒收（rc 1）；來源超界或逾時→該來源判失敗（不入 `sources[]`、不截斷、不以舊 digest 代填；整次 rc 2）；一律印可貼入的 OBS 草稿列 |
| 體檢 | 1 個唯讀子代理＋`si scan`；零扇出、零遞迴；任務書宣告 token 上限（未校準，超出必揭露） | 超界→交已完成部分並揭露、不猜 |
| 歸因 | 1 歸因者＋1 確認者；任務書宣告 token 上限（未校準，首輪實測後定；超出必揭露，OBS-SI-012） | 超界→記 `NONE`，不猜 |
| 提案 | ≤ `MAX_PROPOSALS_PER_RUN`／運轉；修訂 ≤ `MAX_REVISIONS`；零遞迴 | 任一超界→拒收＋升級人工；修訂超限＝rejected＋冷卻 |
| 提案（歸檔型，C.2 #8） | 每卡搬移條目 ≤ `MAX_ARCHIVE_ENTRIES_PER_CARD`（初值 50，無先例、未校準）；不受 `MAX_TOUCH_RATIO`；仍受 `MAX_PROPOSALS_PER_RUN`／`MAX_REVISIONS` | 超界→退回拆分；任一行被改寫＝非歸檔型、回到 `MAX_TOUCH_RATIO` |
| 人工閘 | 無逾時、預設拒絕、待決不計時 | — |
| 沙盒套用／驗證 | 每探針牆鐘先例 `step_timeout_seconds`＝600（初值）；重跑 ≤2；零扇出 | 逾時殺行程樹→收 verdict（FAIL／NE），不等沙箱（禁令 26） |
| 量測／退役 | 零 token；窗以事件關閉 | — |
| 整體 | `STOP_AFTER_BAD`／`CHURN_MAX`；扇出前 `python tools/session_resume_planner.py --pace` 現查；額度帶在準備帶以上不得新增扇出 | SUSPENDED／升級人工；僅掌舵者恢復 |
任何階段失敗（含取寫入鎖逾時，ADR-SI-10）：CLI 非零 rc 並印**可貼入的 OBS 草稿列**（CLI 不自寫 OBS 帳本——單一窗口，鐵律七檢查表 1；NFR-SI-09-3）。

**回滾路徑**
| 類 | 回滾配方（一個動作） | 乾跑（驗證階段，AC-SI-16-2） |
|---|---|---|
| M | 逐行反向 patch（不整檔還原：harness 可能併發自寫索引） | 沙盒檔案複本：正向→反向→逐位元＝base |
| P | `git revert <promote sha>` 或刪 `evolved_*.yaml` 副本 | `git archive` 匯出 base＋patch→反向 patch→逐位元＝base |
| R | 撤銷合入 commit；`verified` 後的 `set_maturity` 退回由人 | 同 P；`set_maturity` 只在沙盒乾跑 |
| D | `git revert` | 同 P |

**受保護路徑與守衛面**
- `si prop-new`／`si prop-revise` 前置檢查（邊界型 **M**；SCG-0 一審 F-01，AC-SI-07-3）：
  - **類別**：`cls` 非 M／P／R／D（含 `evaluator-change`／`loop-self`）→handoff。
  - **比對對象＝`touched` 的全部路徑，不只 `target`**：先對每條路徑做語法拒收（fail-closed→整張 handoff）——含 `..` 片段、絕對路徑（`/` 或 `\` 開頭、UNC）、磁碟機代號或任何 `:`（NTFS 資料流）、片段（除單獨的 `.`）尾端為點或空白、Windows 保留裝置名、NUL 或控制字元（這些在 Windows 會別名成另一個檔，字串 glob 看不出；鐵律三自問）；通過後以 `realpath`（解符號連結）＋`normcase`＋`casefold` 正規化（POSIX 的 `normcase` 是恆等函式〔本回合以 `posixpath.normcase('docs/Claude.MD')` 實測原樣回傳〕，而 macOS 預設的 APFS 大小寫不敏感，只靠 `normcase` 會讓 `claude.md` 在 macOS 漏過 `**/CLAUDE.md`；repo 已由 `tools/check_ntfs_paths.py` 禁止僅大小寫相異的 tracked 路徑，兩平台一律大小寫不敏感比對不致誤殺；macOS 未實跑），比對 (a) `non_evolvable_globs`——含**凍結版本目錄與 `docs_template/`，適用所有類別、不只 R 類**（AISDLC_SDD 非 LATEST 的版本目錄，根 `CLAUDE.md`〈路徑陷阱〉：只有 LATEST 可原地改；LATEST 現查，解析失敗＝全部視為凍結，C5）、(b) 該類合法根（M＝邏輯根 `memory/`；其餘＝repo 根；逃出者視同命中）；任一命中＝**整張** `route=handoff`，不得只轉交命中的檔。NFR-SI-02-1 (i) 的 `R-*.yaml` 為內容條件式：觸及既有且 `maturity: active` 者命中，僅新增 `trust_level: proposed` 候選檔者不命中（讀 base 快照的檔與 patch 判定；讀不出 `maturity`＝視同 active，fail-closed）。
  - **`touched` 雙法導出**：(a) 自寫解析器逐行取 `diff --git` 標頭、`---`／`+++`、`rename from／to`、`copy from／to`，**須實作 git 的 C-style 引號解碼**（八進位 `\ooo`、`\n`／`\t`／`\"`／`\\`），`/dev/null` 視為無路徑，各處路徑取聯集（寧多勿漏）；(b) `git apply --numstat -z` 當**超集檢查**：git 看到的每條路徑都必須 ∈ (a) 的集合，否則拒收。Q12 實測：該指令解得開八進位引號，但改名與複製只列目的端，所以只能檢查、不能當來源；改名來源端只靠 (a)，由下列負控釘住。P2 起沙盒套 patch 時，套用器實際寫入的路徑集合須 ⊆ `touched`，多出者＝拒絕驗證（C9）。
  - **內部來源**：**任何類別（M／P／R／D）**的 `sources` 至少 1 個內部來源（AC-SI-02-1；外部衍生列不得單獨充當證據，P／D 類不豁免）。
  - SUSPENDED／無 `run.open`／同運轉無研究事件（AC-SI-30-1）／超預算→拒收。
  - **負控自證**（合成 patch，實作輪；正控＝只動 `target` 內檔案⇒`route=loop`）：夾帶根 `CLAUDE.md`、`.claude/hooks/*.py`（含子專案與各版本目錄下的 `.claude/`）、凍結版本目錄下的檔、`docs_template/` 下的檔、SI 帳本／`SelfImproving_Proposals/`／協定目錄下的檔、既有 `maturity: active` 的 `R-*.yaml`、路徑逃逸（`..`／絕對路徑／磁碟機代號／尾端點／`:` 資料流）、純改名（只有 `rename from／to` 標頭、來源端為受護檔）、八進位引號偽裝（`CLAUD\105.md`）、大小寫變體（`claude.MD`）、`diff --git` 標頭與 `---`／`+++` 不一致 ⇒ 皆整張 handoff。
- **誠實劃界**：以上只擋「經 SI CLI 建立的 PROP」；直接用 Edit／Write 改正式面不經 SI，仍由既有治理（Rule 9、harness 分類器、審查）管轄——本設計不新增也不聲稱新增該層防護（守衛面准入：量、不挖）。**直接寫事件帳本**（用檔案寫入工具追加一行格式合法的 `dec`／`resume`／`unblock` 事件，不經 `si decide`）同屬此類：不是被擋，而是**偵測型（D）**——`si check` 與 `si promote` 回查每筆 `dec` 的引言（AC-SI-12-4 ⑤），不符＝`check` 紅、`promote` 拒，他機取不到逐字稿時只是 NE。折疊出來的 SUSPENDED／冷卻在被回查標紅之前已經生效，這段空窗由事後偵測承接、不另加守衛碼（守衛面准入：量、不挖；偽造被抓到的暴露證據即 ADR-SI-02 的再開症狀）。
- 成品 staged：子代理成品一律放 scratchpad，由主控 `prop-new --patch-file` 收；各層 `.claude/**`（`**/.claude/**`）一律 handoff、不改派子代理繞過（NFR-SI-02-2）；套用只在沙盒，`si promote` 是唯一對主工作樹寫入的動詞，僅在 verdict＝PASS（或 NE＋`unverified_ack`）且 DEC＋digest＋被觸及行 pre-image 皆符時執行、**不 commit**（commit 由主控走一般流程，訊息引 DEC-ID）。**晉升前以當下 `params.json`（含當下 LATEST）重新解析 `rN.patch` 並重驗全部路徑**——核准之後 `non_evolvable_globs` 或 LATEST 都可能已變，不沿用 `prop-new` 當時的結果；任一命中不可進化面或逃出合法根＝拒絕晉升並改轉交（AC-SI-07-3）。M 類 pre-image 不符＝拒絕並重新上卡、不嘗試自動合併，並印可貼入的 OBS 草稿列（AC-SI-27-1；ADR-SI-06）。
- 無人值守：`AUTOSDD_UNATTENDED` 有設時 `decide`／`promote`／`rollback` 一律非零 rc（讀自己行程環境、非 hook；人的逃生口模型碰不到，NFR-SI-02-3）。
- **規格本體路徑（SCG-0 一審 F-21；§3.2；評估結論＝機械化）**：任何類別的 `touched` 只要落在 `spec_body_globs`（`params.json`；初值 `**/docs/01_requirements/**`、`**/docs/02_architecture/**`、`**/docs/03_testing/**`——即 R-9.6 擋寫的三個規格目錄；不帶 `**/` 前綴只錨定 repo 根，而 AutoClaude、AgentConsole、AISDLC_SDD 各有自己的 `docs/01～03`，與 R-9.6 的路徑字串比對同範圍，BRIDGE §8.3 第 3 點），除「`action=add` 且唯一觸及路徑為 `**/docs/01_requirements/SPEC-PATCH-*.md` 的 D 類草案」外，一律 `route=handoff`（走既有 SPEC-PATCH＋HUMAN_PENDING／PRD 修訂）。只比路徑前綴、不判內容語意：邊界型 **M**，`prop-new` 與 `promote` 兩處都查；「改動算不算規格變更」的語意判斷仍是 **P**。這把 §3.2 原標的 P 型縮到只剩語意那一半（§3.2 已同步標為 M＋P）。**R-9.6 本身不是 SI 的防線**：BRIDGE §8.3 第 3 點寫明它擋的是 hooks-ON 視窗在非草擬態的 Write／Edit 工具呼叫（路徑字串含上列三目錄）；`si promote` 以 CLI 子行程寫檔、不經該 hook（本機未實測），所以 SI 需要自己的路徑前綴檢查。更正首輪：首輪寫的「`promote` 會被 router 擋」是過度宣稱。若改以 Edit／Write 落地而遇 R-9.6 擋寫，不得改派子代理或換路徑繞過，改由符合條件的視窗（hooks-OFF）處理或 handoff（AC-SI-15-3）。

**T1 修訂增補（v0.8 骨架、v0.9 定稿；純度、研究者與 Console 面）**
- **能力登記與純度判準**（邊界型 **M**；P0 TCS `AC-030-2`／`AT-030-2-1`、`AT-003-1-1` 靜態段的承接）：`tools/lib/selfimproving/` 每個 `*.py` 在測試檔常數登記表（`tools/tests/test_selfimproving_capability.py`，P1 新檔）登記一個能力類別——`ro`（零寫入原語、零網路、零子行程；`git.py` 是唯一子行程出口，環境淨化、`-C`、timeout，沿 P0）、`rw`（可寫 repo 內 `docs/` 與家目錄 `AUTOSDD_SI_DIR`、零網路）、`net`（唯一可 import 網路模組的類別，僅 `fetch.py`；`research.py` 因 import 它而歸 `net`）。判準：① 套件內每個 `*.py` 都在登記表（新檔未登記＝紅）；② 逐檔 AST／正規式掃描符合所登類別（`ro` 檔不得有 P0 的寫入形原語、`os.system`／`os.popen`、`subprocess`〔`git.py` 除外〕與網路 import；`rw` 檔不得有網路 import；網路 import 只許出現在 `net` 檔）；③ `check.py`、`status.py`、`scan.py`、`export.py`、`card.py` 的相對 import 閉包 ⊆ `ro`（唯讀動詞在結構上碰不到寫入或網路碼）；④ P0 的 `AT-003-1-1` 常駐機制禁字樣（`time.sleep`、`while True` 等）仍掃全套件（`apply_lock` 的輪詢睡眠在 `tools/lib/apply_lock.py`、不在套件內）。這不是新增守衛碼：測試檔在 `tools/tests/`、不在守衛面清單、不是 hook；它把 P0 的「套件內每個檔都純」細化為「登記＋閉包」——P1 起套件內合法存在寫入與網路碼，而 `check` 的純度（P0 `AT-030-2-1` 動態段：檔案摘要與 `git status --porcelain` 前後相同、子行程只有淨化 `git`）不變。
- **研究者的外部內容入口**（FR-SI-30；邊界型 **P**＋**M**）：外聯**只有** `si research --fetch`：`fetch.py` 是整個套件唯一 import 網路模組（`urllib`、`http`、`socket`、`ssl`）的檔（M：能力登記判準，見上），請求對象限來源表內的 `url`（M：表驗證＋重導向目標 host 須在表內、scheme 限 http／https、https 不降級、至多 5 跳、不帶 cookie／token、固定 `User-Agent`、`Accept-Encoding: identity`）；抓回內容一律是**資料、不是指令**——研究者與主控不得執行其中任何指示（含「忽略先前指示」「改寫某檔」類字樣；同型風險 S-13、S-09；P）；研究者工具白名單 Read／Grep／Glob（無 Web 工具、無 Write／Edit、不派子代理；P：任務書約束，無機械物）；digest 與 `changed` 由 CLI 對原始位元組自算（M）；產物只能是 OBS 候選（`外部衍生=是; src=<id>`），由主控單窗口入帳（M：`check` 對 `回報者=研究者` 的列驗「`外部衍生=是` 且帶 `src`」、對任何帶 `src` 的列驗 `src` ∈ 來源表）；PROP 的 `sources` 仍須 ≥1 個內部來源（M，AC-SI-02-1，於 `prop-new`）；來源表本身屬不可進化面（M：`non_evolvable_globs` 的 `docs/06_quality/SelfImproving_Protocol/**`），經 SI CLI 建立的 PROP 不得觸及它。**網路與鎖分離**：抓取在寫入鎖之外進行（最壞 `research_fetch_max`×`research_timeout_seconds`＝160 秒，遠大於 ADR-SI-10 的取鎖逾時先例 60 秒），鎖內只重驗（運轉仍開、尚無研究事件）、重算 `changed`（讀鎖內最新事件）與追加；來源檔先落地、事件後追加，事件追加失敗時來源檔留作快取、不影響帳本。誠實劃界：不做 DNS 解析後驗 IP（沿 Architecture §8.4）；來源站台本身可被第三方改寫（供應鏈）而 `sha256` 只量原始位元組穩定性，抓回內容進入研究者與主控 context 後仍可能夾帶指示——當資料讀，這一步無機械物（P）；已擋非文字類 `Content-Type`，但不證明內容安全。
- **Console 面**（FR-SI-32、33；邊界型 **M**＋**P**）：P1b 的 `/si/*`、`/api/v1/si/**` 全為 GET（M：非 GET 回 404／405 的測試）；Bridge 以子行程呼叫 `export`、自身不開 SI 帳本檔也不 import 根層 `tools/lib`（M：AST 鎖，先例＝Bridge 不得開寫 `FSM-STATE-*.yaml` 的 AST 測試〔`tests/test_sdd_integration_parity.py`:355、:423、:433〕：新增 `tests/test_si_readonly_lock.py` 掃 `app/`——不得以寫入形態開啟含 `SelfImproving`／`selfimproving` 的路徑、不得 `import lib`／改 `sys.path` 指向 `tools`、字面 `selfimproving.py` 只准出現在 `si_cli.py`）；`SI_ROOT` 是伺服器設定、請求不帶路徑（§9.3；不併入 `BRIDGE_ALLOWED_PATH_ROOTS`）；子行程環境為白名單、不繼承 `BRIDGE_*` 與其他機密（M；§9.3）；`--kind` 為封閉集合、`id` 以 `^PROP-SI-\d{3,}$` 驗（M）；`export` 不讀不印 `~/.autosdd/` 下任何檔（M：哨兵測試，§9.2）；Bridge 無認證、只准 backend-net（P，Architecture §12.1 L-6）；P2b 起 Bridge 的寫入只有一條——稽核 JSON 落檔，需 `X-Bridge-Token`（M，沿 Architecture §10.2 權杖列）；決定資格＝Admin 角色且在 `console.si.deciders`（M：backend RBAC＋白名單）；`dec` 的入帳在主機端 `si decide`（`AUTOSDD_UNATTENDED` 有設時非零 rc，M，既有）。誠實劃界：Console 路徑沒有逐字稿，偽造決定的偵測弱於逐字稿載體——HMAC 金鑰在主機環境、防不了主控，獨立證據是 Console DB 稽核列（對帳為偵測型），見 ADR-SI-03′。

**驗證載具要點**：① RED／GREEN／突變三步（AC-SI-19-1）；② 載具自證：沙盒內被測模組 `__file__` 須在沙盒內（可編輯安裝指向主樹，須 `PYTHONPATH` 遮蔽）；③ 容量事件觸發的 M 類退役以容量量測當探針，可得 PASS；M 類新增／修改（教訓條目）與多數 D 類無確定性探針⇒NE＋`unverified_ack` 為**預期常態，不是缺陷**；④ 判定用的評估指令取自凍結評估集，提案者的 `verify_plan` 只供審查者參考；⑤ C13 的檔名不帶輪號（程式碼內輪號字面撞鎖）、形態沿 R85 測試的 `construction_sites()` AST 普查＋對照組，屬測試檔、不在守衛面清單。

### 9.5 ADR 候選（`docs/04_planning/ADR/ADR-SI-NN-*.md`；實作輪前由 SD 轉正式 ADR；「再開症狀」皆為可觀測事件）
| ADR | 背景 | 選項 | 建議 | 代價 | 再開症狀 |
|---|---|---|---|---|---|
| ADR-SI-01 觀察儲存位置 | P0 已 dogfood 於 Markdown 表；SI 帳本不在體積守門面（Q9） | A git 內 Markdown 表（現況）；B JSONL；C `~/.autosdd/`（機器本地）；D PG／Console | **A**（九欄、標記＝`key=value`、檔頭 `tz=`）。C 否：機器本地＝跨機不可稽核；D 否（§9.2） | Markdown 表欄位切分與管線字元轉義曾是 DEF 帳本反覆缺陷源（欄數與轉義類缺陷，見 `tools/check_defect_log_crossref.py` 的 `row_arity_problems`）⇒`si check` 自帶欄數檢查與反空轉下限；體積警戒自備 | `si check` 對 OBS 列連續誤判（附列座標，同 F-SI-103）；或單檔逼近 256KB |
| ADR-SI-02 已裁決（C.2 #5） 提案物件格式與機器可讀載體（C.2 #5 的 SD 評估） | SPEC-PATCH 只涵蓋 AC 補丁且寫入 R-9.6 擋寫區；PROP 需 class／digest／rollback／budget／狀態；C.2 #5 要求 P2 前評估機器可讀 | A 直接複用 SPEC-PATCH；B 新 PROP 內容檔（SPEC-PATCH 三節骨架）＋JSONL 事件帳本；C 全 Markdown 表（C.2 #5 字面）；D 純 JSONL（diff 內嵌） | **B，自 P1 起**（OBS 仍 Markdown，F-SI-103 ⏸ 不變）：狀態折疊、digest、冷卻、M1～M5 都要結構化解析；事件由 CLI 寫（LLM 不手寫 JSON）；先例 `docs/06_quality/FiveQuestion_Round_Ledger.jsonl`＋`tools/probe/fivequestion_ledger.py` | 兩種載體並存、CLI 為唯一支援寫入者（直接改檔由 `si check` 事後偵測，含追加格式合法的 `dec` 行——由引言回查承接，AC-SI-12-4 ⑤；多寫入者併發的取鎖與配號見 ADR-SI-10）；`tools/` 新檔付重釘稅（LOC tier、`tools/tests` 鎖、compat-ci `paths`）。退路＝C（同欄位、同 CLI，換成追加表） | 手改事件帳本致格式錯連續（附列座標）；或 `check`／`promote` 的引言回查抓到一筆偽造的 `dec`（附 sid＋line，符合〈暴露度〉(b)）→升機械擋寫；或掌舵者要求純 Markdown |
| ADR-SI-03 已裁決（C.2 #9） 人工閘載體與決定驗證 | C.2 #5＝MVP CLI 卡；Console 簽核硬閘只覆蓋 SDD 凍結，`review_requests` 由 console-api 唯一寫入（Architecture §7.2） | A CLI 卡＋自逐字稿抽取並驗證引言；B Console 卡（`POST /si/proposals/{id}:decide`）；C 並行 | **A**（MVP）；B ⏸ F-SI-101。驗證只認 `origin.kind=="human"`（不含 `sdk`）、缺出處欄位判 NE、卡面須逐字出現在先前 assistant text | 逐字稿在本機⇒他機重驗＝NE；`origin`／`isMeta`／`turnOrigin` 是觀察所得、非官方契約（`.claude/hooks/check_claim_provenance.py`:824–866） | 出處欄位缺席／改名使驗證連續 NE（附 sid＋line）；或掌舵者要求 Console 內審〔T1 修訂（v0.8）：此再開症狀已實際發生——T1 2026-10-19 line 13 要求帳本可由 Console 管理；本 ADR 因而再開，為 FR-SI-33 的 Console 載體重審驗證設計（選項 B 由 ⏸ 轉 P2b），裁決見下列 ADR-SI-03′〕 |
| ADR-SI-03′ 再開：Console 決定載體的驗證設計（FR-SI-33；P2b；Architect 棒裁決，附錄 C.2 #16） | Console 路徑沒有逐字稿，AC-SI-12-4 ①～⑤ 無從套用，需要等價物＝**由主控以外的一方**記下、可事後回查的證據。現查（§9.7 FC-b）：Bridge 容器的 repo 掛載是唯讀（P1b），ADR-SI-10 的寫入鎖在**主機**家目錄、容器內的行程與主機寫入者互斥不了；`CONSOLE_ENCRYPTION_KEY` 只在 backend 環境（`AgentConsole/docker-compose.yml`:136），Bridge 與主機 CLI 都沒有，且它能解密全部敏感設定 | A Bridge 子行程呼叫 `si decide --carrier console` 直接寫帳本（SA 預設）；B（建議）稽核 JSON＋HMAC＋主機端 CLI 入帳；C 非對稱簽章；D 只落稽核 JSON、不簽；E Console DB 當來源、CLI 讀 PG | **B**。(i) 資格＝Architecture §8.2 的 Admin 角色**且**帳號名在 `console.si.deciders`（`CONSOLE_SI_DECIDERS`，逗號清單，預設空＝無人可決；K=1）；(ii) console-api 產稽核檔：`body`（字串，JSON 物件文字：`schema_rev`、`audit_ref`〔UUID〕、`user`、`role`、`time`〔伺服器時間帶 offset〕、`prop`、`digest`、`dkind`〔§7.2 動詞對映的 `--kind`〕、`reason_class`、`reason`、`flags`、`run`〔`resume` 才有〕）＋`key_id`（金鑰 sha256 前 8 碼）＋`mac`（HMAC-SHA256，**簽 `body` 字串的 UTF-8 位元組、不重新序列化**，避開 Java 與 Python 的 canonical JSON 差異）；同型列另存 Console DB 新表 `si_decisions`；(iii) Bridge 驗 `X-Bridge-Token`（`BRIDGE_SI_WRITE_TOKEN`，規則同 SDD 權杖）後把該檔原樣寫入 `<AUTOSDD_SI_DIR>/console_audit/<audit_ref>.json`（需該子目錄的可寫 bind mount；Bridge 不驗簽、不碰帳本）；(iv) 主機端 `si decide --carrier console --audit-ref <id>`（主控單窗口；`AUTOSDD_UNATTENDED` 有設＝非零 rc）以金鑰環 `AUTOSDD_SI_AUDIT_KEY`（逗號分隔，依 `key_id` 選）驗簽，再驗 PROP 狀態、現行卡面 digest、§7.2 前提，通過才於寫入鎖內追加 `dec`：`carrier=console`、`audit_ref`、`audit_sha256`（稽核檔位元組的 sha256）、`key_id`、`decider`、`time`、`digest`、`dkind`…（取代 `quote`／`sid`／`line`）；同一 `audit_ref` 不得二次入帳；(v) `check`／`promote` 回查＝同一個驗證函式：稽核檔存在→`audit_sha256`、PROP、digest、動詞、決定者、時間逐欄相符，金鑰在場再驗 HMAC；檔不存在（他機）或缺金鑰＝NOT-EVALUABLE，`promote` fail-closed；(vi) Console 頁在對應 `dec` 出現前顯示「待入帳」與可複製的入帳指令（先例：`components/domain/sdd/CopyCommand.tsx`），並對 `carrier=console` 的 `dec` 比對 `si_decisions`（無列＝紅色警示，偵測型）。**⚖ 待主控確認兩點**：①金鑰通道——建議專用 `CONSOLE_SI_AUDIT_KEY`（backend）／`AUTOSDD_SI_AUDIT_KEY`（主機）；主控建議派生自 `CONSOLE_ENCRYPTION_KEY`（暴露面較寬：Bridge 與主機都得持有可解密全部敏感設定的金鑰）；②入帳模式——建議 pull（B）；SA 與主控預設為 Bridge 子行程直寫（A）。確認前 P2b 不開工 | 主控須入帳（多一步，但帳本維持單窗口寫入，鐵律七）；HMAC 金鑰在主機環境，持有它的行程（含主控）可鑄造合法稽核檔，**偽造偵測弱於逐字稿載體**（只擋沒有金鑰者；獨立證據是 Console DB 列，在 PG 容器內、與帳本不同信任域，對帳為偵測型）；多一把專用金鑰要管理與輪替（舊簽章保留 `key_id`，金鑰環缺舊金鑰＝該筆 NE、`audit_sha256` 仍可驗）；稽核目錄需可寫 bind mount；跨語言 HMAC（Java 簽、Python 驗）以測試向量釘住。已否決：A（容器內寫帳本，與唯讀掛載及主機鎖域衝突）；C（stdlib 無非對稱驗簽，破 NFR-SI-02-4 純度）；D（稽核檔可被手寫）；E（PG 成為第二個真相源、CLI 需第三方驅動） | 主控入帳成為瓶頸（附待入帳筆數與 sid）→評估 Bridge 本機模式直寫（驗證函式不變）；稽核檔與 `si_decisions` 對帳出現不符（附 `audit_ref`）→查簽章與序列化；金鑰洩漏或輪替致 ≥1 筆既存 `dec` 回查 NE（附 `key_id`）→重議簽章方案 |
| ADR-SI-04 套用沙盒 | AC-SI-15-1 要正式面零變更、沙盒位置不改掃描與棘輪結果；鐵律五禁毀滅性 git；Q7、Q8 | A `git worktree add --detach`（樹外＋sparse）；B `git archive` 匯出到樹外短根（M 類＝檔案複製）；C 分支＋主工作樹切換；D Agent `isolation: "worktree"` | **B**：零 repo 元資料變更（無 `.git/worktrees` 登記）；只含已提交快照（對齊「輸入快照」）；清理＝刪目錄（不碰鐵律五）；匯出經 Python `subprocess`＋`tarfile`（避開 PowerShell 原生指令管線對二進位串流的編碼風險；本機未實測）；先例＝整合輪 116 QA 以 `git archive` 匯出量突變（`AutoSDD_improving_116.md` §9.1）。C 否（切 HEAD，違 AC-SI-15-1）；D 否（建在 `.claude/worktrees/` 樹內，R178） | 沙盒無 `.git`（需 git 歷史的探針不適用；備案＝沙盒內 `git init`＋baseline commit，`git apply` 在無 `.git` 目錄的行為未查證）；`tarfile` 抽取須防路徑穿越（`filter="data"` 為 3.12 起，本機 venv 版本未查證）；被測碼 import 可能解析到主樹⇒載具自證 | 探針需要 git 歷史／`git grep`（→改 A，仍在樹外）；或匯出耗時逼近 `step_timeout_seconds` |
| ADR-SI-05 量測資料源與腳本落點 | M1～M5 需 DEF／OBS／PROP／DEC＋git；`tools/check_defect_log_crossref.py` 是 SPECIAL_FILES 棘輪下的大檔、滿載 DEF 專屬判準 | A 帳本＋git（確定性、零 token）；B 逐字稿；C CI 結果（`gh`）；D 擴充 crossref | **A 為唯一指標資料源**；獨立 `tools/probe/selfimproving_measure.py`，DEF 解析器自寫＋差分測試釘一致；B 僅用於 DEC 驗證與暴露偵測（非指標）；C 否（T3 前例：CI 紅本身不是觸發）；D 否（耦合 DEF 棘輪） | Q6：M2／M3 結構性低 n；M1 無歷史標記，且全域 20 列窗的基率過低（期望再現事件約 0.01～0.05 件）而無鑑別力 ⇒ **基線機制改 per-PROP 基線窗**（SCG-0 一審 F-02；§1.3）：每個 PROP 於其 `app.promote` 時由 CLI 記一筆 `mea.report`（`kind`＝baseline）——該 PROP 基線窗（同機會列規則、自再現標記上線後的最近 `W_OPP` 筆機會列）的機會列 ID、窗內確認再現事件數、`W_OPP`／`W_EVT`／`W_MIN` 取值；基線事件數 < `W_EVT`（含 0）⇒ 該 PROP 的 M1＝NE，不得算「未低於」；基線窗只計標記上線後的列、不做歷史回溯標註（「標記上線」錨＝`migration_base_sha` 那個 commit 的 committer 時間〔UTC；主控裁決，SCG-0 二審 F-29〕：更早的 DEF／OBS 列不計再現候選、也不進基線窗；P0 完成前不會有任何基線）；首次 `app.promote` 前另記一筆全域前瞻基線（§1.3）；全域 `W_N` 窗只作資訊欄。代價：M1 可能長期 NE（事件太稀）——這是誠實結果、不是缺陷；n 為個位數，M1 是證據、不是顯著性檢定 | 差分測試出現歧異；或 DEF 側表頭改動（需掌舵者）；或每個已關閉採納窗的 PROP 其 M1 都因基線事件數 < `W_EVT` 而 NE（附 PROP-ID 清單）→重議 §1.3 的指標選擇（PRD 修訂，經掌舵者 T1） |
| ADR-SI-06 已裁決（C.2 #8） 與 Claude Code 記憶的關係 | 記憶目錄在 repo 外、harness 會自寫、由主控維護；Q5；2026-10-19 人工歸檔（41 條移到歸檔索引、不刪記憶檔）是現成先例 | A 全納管；B 只納管「經本迴圈寫入者」＋索引層退役／合併；C 不納管（只觀察） | **B**：M 類 PROP 以邏輯路徑（`memory/<檔名>`）表達、晉升由主控解析實際目錄；退役＝索引行逐字搬到 `archive-index-*.md`（索引留一行指標）、不刪記憶檔；harness 自寫不受控、只觀察；digest 綁被觸及行 pre-image | 兩個寫入者並存⇒晉升前必驗 pre-image，不符＝拒絕並重新上卡；結果標籤欄位（`outcome`／`scope`／`source_obs`／`retire_when`）放記憶檔 frontmatter `metadata:` 下是否被 harness 容忍＝未查證；AC-SI-09-2 的觸及比例（`MAX_TOUCH_RATIO`）使單次索引歸檔須拆成 ≤`MAX_PROPOSALS_PER_RUN` 張卡⇒已裁決（C.2 #8）：對「逐字搬移、零內容修改、一個反向 patch 可回滾」的歸檔豁免比例，改以每卡條目數上限（`MAX_ARCHIVE_ENTRIES_PER_CARD`）約束，上限初值 50（無先例、未校準） | 晉升時 pre-image 比對連續失敗（附 PROP-ID）；或索引再度逼近 `CAP_FRAC` |
| ADR-SI-07 已裁決（C.2 #6、#7） FR-SI-28 落點與 SI 最小侵入白名單 | Q3；`AgentConsole/CLAUDE.md`:15 把 ADR-XPLAT-016 §11 寫成「兩引擎只准改的檔」，而其 §11.3 核對以 115 輪 `<起點>` 為準 | A AutoClaude contract 測試（AST 普查，零引擎碼）；B importlinter contract；C 物理拔除舊路徑；D 於 `AutoResumeService` 加 signoff 閘（引擎碼） | **A**；SI 自持白名單＝「引擎源碼零改動；僅 `AutoClaude/tests/contract/` 新增 1 檔；`AutoClaude/CLAUDE.md`:191 改述走一般開發流程」。B 否（importlinter 管 import、不管「誰建構／誰產出」）；C 不可逆（R85 明言不主張）；D 動引擎碼且超白名單 | AST 普查是**形態判準**（`getattr`／`importlib` 動態建構看不到）；新增測試檔移動 AutoClaude 基線數字（ONBOARDING §7）與 `tools/tests/test_platform_neutral_paths.py` 的 `_tmpdir_scan_roots` 檔數雙邊帶（`AutoClaude/tests` 註解快照：實測 282／下限 268），實作輪現查重釘 | 任一生產路徑出現 `PlaybookRunner` 建構或演化重載生產者（OBS-SI-010 再開症狀）→ 改採 D 並走 FR-SI-12 |
| ADR-SI-08 held-out 存放與凍結 | AC-SI-20-1 要評估集由提案者以外角色凍結且提案者看不到；子代理可讀整個 repo、無檔案層隔離 | A 放 repo（可稽核、提案者可讀）；B 家目錄＋digest 入帳＋暴露偵測；C 完全由人保管 | **B**（`~/.autosdd/selfimproving/heldout/<PROP>/`，不退回暫存）；驗證預檢重算 digest、掃提案者逐字稿有無讀取該路徑；隔離是**流程型＋偵測型**，不寫成「被擋」 | 他機無 held-out 內容⇒重驗判 NE；偵測靠逐字稿欄位（觀察所得） | 暴露偵測命中（附 sid＋line）→升機械隔離 |
| ADR-SI-09 審查者機械唯讀 | 鐵律七檢查表 3「複審唯讀」只靠任務書；`.claude/agents/` 不存在、`.claude/**` 屬受保護路徑 | A 任務書約束＋逐字稿偵測（現行）；B `.claude/agents/si-reviewer.md` 以 `tools` 白名單（Read／Grep／Glob） | **A**；B 僅在暴露證據成立後（守衛面准入）。探針由確定性 CLI 執行、審查者只讀證據，故無需 shell（`tools` 白名單依 Agent 工具說明，repo 無先例，未實測） | 唯讀靠自律＋事後偵測 | 審查者逐字稿出現 Write／Edit 或背景任務（附 sid＋seq，符合〈暴露度〉(b)） |
| ADR-SI-10 事件帳本多寫入者與配號（SCG-0 一審 F-11） | 歸因者、提案者、凍結者、驗證執行等經 CLI 寫同一個 git 追蹤的 JSONL；`seq` 與 `PROP-SI-NNN`＝max＋1 是「讀末行→算號→追加」的讀改寫，NFR-SI-07-2 允許扇出，鐵律七檢查表 1 的單窗口只對 OBS 明文；AC-SI-08-4 ③「ID 唯一遞增」只事後偵測。repo 實測先例（R81，`tools/lib/quota_ledger.py` 檔頭）：Windows 上 `O_APPEND` 單次 `os.write` 跨行程不原子（8 行程×40 筆掉 12.2%）、`msvcrt.locking` 在 N=20 時行程直接死在 `Resource deadlock avoided`；獨佔建檔（`O_CREAT` 且 `O_EXCL`）才是兩平台語意一致的原語（`tools/lib/apply_lock.py`） | A 沿 `tools/lib/apply_lock.py` 的 `acquire`（獨佔建檔鎖＋逾時 fail-loud＋陳舊鎖回收）包住「讀末行→配號→追加」整段；B 只准單一寫入視窗（子代理成品與歸因一律由主控代錄）；C `msvcrt.locking`／`fcntl.flock`（R81 實測否決）；D 只靠 `O_APPEND`（R81 實測否決）；E 每事件一檔（目錄項原子，但事件帳本不再是單一可 diff 檔，折疊重放與 `ROW-MUTATED` 比對都要改） | **A 為機制、B 為預設流程**：鎖內配號（`seq`＝鎖內讀到的末行 `seq`＋1；`PROP-SI-NNN`＝max(事件帳本, OBS 帳本引用)＋1，同一把鎖內算），追加為單次完整行寫入；取鎖逾時＝`LockBusyError`→CLI 非零 rc 並印持鎖者（pid、取得時間），**fail-loud、不 fail-open**——與 hook 關鍵路徑上 fail-open 的 `quota_ledger.with_lock` 相反，因為治理帳本漏一筆或撞一號都比等待糟；主控單窗口寫仍是預設做法，鎖只是兜底。併發負控見 §9.2 事件帳本規約 | 每次寫事件多一次鎖檔建立與刪除；鎖檔放家目錄 `~/.autosdd/selfimproving/locks/<帳本路徑雜湊>.lock`（機器狀態、不入 git；放在 `docs/06_quality/` 會讓持鎖期間的 `git status --porcelain` 多出未追蹤檔，與 AC-SI-15-1「正式面 `git status` 逐字相同」衝突；雜湊讓同機多個 clone 不互鎖），家目錄不可寫＝拒寫（同 §9.2 儲存原則，不退回暫存）；`stale_after`／`timeout` 初值未校準（先例 `tools/archive_apply_locked.py`：逾時 60 秒、陳舊 300 秒）；鎖只管同機行程，**跨機器**各自追加同一帳本是 git 合併問題（相同 `seq` 的合併衝突），由 `si check`（`seq` 唯一遞增，AC-SI-08-4 ③）事後偵測、不嘗試自動合併 | `si check` 在真實帳本偵測到 `seq` 重複或撕行（附列座標）；或非構造性運轉中出現 `LockBusyError`（附 sid＋line）；或陳舊鎖回收後仍撞號 |
| ADR-SI-11 研究來源表與增量掃描（T1 2026-10-19 問題 1b1；C.2 #10、#16） | T1 要求每次啟動取得外部最新資訊；§3.2 原禁運轉期 Web；全開放搜尋每棒燒數小時（守衛把 Web 工具當扇出、節流約一次數分鐘）且是毒化入口（S-13、FR-SI-02）；C-12 禁日曆觸發；研究方法論 SOP 已完成、深度重跑只依 S7；WebFetch 回的是 harness 模型處理後的文字，digest 無意義、主控逐字落檔是人工搬運（⚖2 裁決） | A 開放式 WebSearch；B（SA 原案）研究者 WebFetch 抽取文字＋主控落檔＋CLI 對檔案算 digest；C（採，D-1′）CLI 以標準庫抓來源表 URL 的原始位元組＋增量 digest＋只產 OBS 候選；D 維持不外聯 | **C**：綁運轉而非日曆（有 `prop` 的運轉必有研究事件，`prop-new` 拒收＋`check` 重放）；來源表住協定目錄、不可進化面、僅 T1 增減；外聯只在 `fetch.py`（能力登記判準，§9.4）；研究者只剩 Read／Grep／Glob（無 Web 工具、無 Write）；digest 對原始位元組算，可重放、可用本機 HTTP 伺服器夾具做正負控。A 否（毒化入口、節流成本）；B 否（模型改寫文本、digest 無意義、人工搬運不可重放）；D 否（與 T1 衝突） | NFR-SI-02-4 的外聯唯一例外落在 CLI（純度改由能力登記判準承接，不再是「`check` 以外的動詞也零網路」的套件級宣稱）；原始位元組含伺服器端產生內容的 HTML 使 `changed` 假陽性，來源表應優先取原始檔／feed；`research_bytes_max` 262144 使大頁判失敗（不截斷）；不做 DNS 解析後驗 IP；來源 URL 皆未驗、修正經 T1；`research.scan` 事件 8 筆最壞 1,642 bytes（＜`event_max_bytes` 2,000，上限約 10 筆）；來源表放協定目錄使指紋 manifest 須排除它（AC-SI-30-6） | 首跑發現 ≥1 個來源 URL 不可抓、超界、非文字或已改址（附 sid＋line）→經 T1 修來源表；或同一來源連續兩個運轉 `changed=true` 而內容語意相同（附 digest 對照）→改取原始檔／feed 或重議 B；或抓回內容夾帶疑似注入指示而被入帳為候選（附 OBS 座標）→重審 AC-SI-30-4 |
| ADR-SI-12 Console 唯讀讀模型（T1 2026-10-19 問題 1c；C.2 #12） | T1 要求帳本可由 AgentConsole UI 管理；F-SI-101 再開；Console 資料所有權（Architecture §7）：console-api 寫 console 表、Bridge 寫 execution 表；SI 帳本在 git，單一真相；PG 讀模型雖快、可分頁，卻會形成第二個真相源 | A Bridge 每請求以子行程呼叫 `si export`（無狀態、現取）；B backend 匯入 PG 讀模型並增量同步（或 Bridge 內 ≤N 秒快取）；C frontend 直讀 git raw；D Bridge import 根層 `tools/lib` | **A**（P1b；無快取——AC-SI-32-3 禁止過期快取當正常）；B 不採：若日後引入＝由帳本重建、可丟棄、不得成為來源、每次回應帶 `head_sha`；C 否（瀏覽器不直連、無逐欄一致性）；D 否（Bridge 自身不開帳本檔、不 import `tools/lib`，映像無根層套件佈局保證，AST 鎖） | 每請求一個子行程（冷啟動時間未量測；子行程逾時 15 秒、backend 讀取逾時 20 秒，實作輪於 P1b 量 `export --kind status` 冷啟動三次中位數寫入 TCS）；Docker 需唯讀掛載 `tools/`、`docs/06_quality/`、`.git/` 三段（§9.7 FC-b；映像使用者 uid 10001 與主機擁有者不同，`git` 需環境變數式 `safe.directory`，未實測）；大帳本全量序列化（OBS 帳本 warn 線＝`params.json` 的 `ledger_warn_bytes` 245,760 bytes；事件帳本隨增→`--since`／`--limit`，§9.2） | 單次 `export` 耗時逼近 Bridge 子行程逾時（附量測）或帳本逼近 `ledger_warn_bytes` 致 UI 取數退化→評估 B（PG 讀模型，仍由帳本重建）；或差分測試（AC-SI-32-1）出現歧異→查序列化層 |

### 9.6 分階段落地對 §8 的對映
| 階段 | 交付元件 | FR | §8.1 出口的落地 | FSM 鍵（BRIDGE §8.0 一功能一鍵） |
|---|---|---|---|---|
| P0 | C1（定稿＋遷移）、C5、C4 的 `check`、C6 草稿 | 01～04、29 | (a) 必填欄免追問＝`check` 欄位／枚舉／tz 檢查；(b) 自 `migration_base_sha` 起全帳本過檢＝`check` 綠（遷移 commit 本身依 AC-SI-01-3 豁免；遷移 commit、寫入該 sha 與掌舵者確認列的 commit 是兩個 commit——commit 不能引用自己的 sha；加第 9 欄後預估超線的列須先搬附註檔，Q10）；(c) 處置合枚舉、`orig` 保全；(d) 零無座標列／零「之後再看」 | `monorepo-si-p0-ledger` |
| P1 | C2 接點、C3、C4（`run-open／close`、`attr`、`prop-new／revise`、`card`、`status`、`research`、`scan`、`export`）、C6 定稿、C7、C13、C14、C16、C17、C19、C18 的根層半（`export`） | 05～11、14、28、30、31、34；32 的 AC-SI-32-5 | (a) 真實觀察端到端走到卡＝事件帳本＋卡面；(b) 零提案觸及正式面＝`git status`／HEAD 對照；(c) 無 `卡面不清` 退回；(d) FR-SI-28 檢查存在且綠＝C13；(e) 每個有 `prop` 的運轉都有研究事件＝`check` 重放綠＋`prop-new` 負控拒收（C16）；(f) 體檢交卷入帳 ≥1 列（真實；C17）；(g) 落點鎖綠＝C19；(h) `export` 綠＝AC-SI-32-5（C18 根層半） | `monorepo-si-p1-propose`（含 FR-SI-32 的 `export` 半，併於末棒；附錄 C.2 #12）；FR-SI-28 另鍵 `autoclaude-evolution-propose-only` |
| P1b | C18 的 AgentConsole 半（Bridge 路由、backend 代理、frontend 頁）；ADR-SI-12 | 32（AC-SI-32-1～32-4） | (a) 差分、(b) 唯讀、(c) fail-loud 三 AC 綠，(d) 需登入綠＝差分測試、非 GET 404／405、注入失敗負控、401 測試；(e) 至少一次真實瀏覽（掌舵者回報，附 sid＋line） | `agentconsole-si-mirror`（AgentConsole 子專案 SDD 流程，在 P1 核心之後；依賴 `export`；啟動 `python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-mirror`，一律從 monorepo 根開 session，根 `CLAUDE.md`〈AISDLC_SDD 快查〉；前置＝Bridge 容器唯讀掛載與 `SI_ROOT`，§9.7 FC-b；開發 agent 不得動根層 `tools/`，`AgentConsole/CLAUDE.md` 鐵律 7） |
| P2 | C8、C9、C10、`decide`／`promote`／`rollback`、冷卻折疊；P2b：C18 的決定載體 | 12、13、15～21；33（P2b，P2 之後） | (a)(b) 驗證含對照＋突變＝`app.verify` 三步；(c) 同型再提被擋＝冷卻折疊；(d) 正式面零未經閘變更＝git 歷史對 DEC 對帳；(e) 回滾乾跑通過；P2b：ADR-SI-03′ 已裁決＋AC-SI-33-1／33-2 綠＋至少一次真實 Console 決定（`dec` 帶 `carrier=console` 與 `audit_ref`，附 sid） | `monorepo-si-p2-gate-apply`；FR-SI-33（P2b）另鍵 `agentconsole-si-decide`（在 P2 之後；ADR-SI-03′ 已裁決、其兩個待確認點經主控確認後開工；啟動 `python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-decide`） |
| P3 | C11、C12、SUSPENDED 折疊 | 22～27 | (a) 量測腳本真帳本跑通；(b) ≥1 量測窗關閉；(c) ≥1 退役走完閘；(d) 反證條件檢查留紀錄＝`mea.report`（無可評估窗＝NE 也留紀錄並寫缺什麼；§8.1 P3 (d)） | `monorepo-si-p3-measure-retire` |
依賴：P0→P1（事件帳本載體）；FR-SI-28 與 P1 並行、互不相依；P2 需 P1 的卡面與 digest；P3 需 P2 的 `app.promote`／`mea.open`；P1b 需 P1 核心的 `export` 與 `status`／`card`；P2b 需 P2 的 `decide`、P1b 的顯示面、ADR-SI-03′ 兩個待確認點經主控確認，並需兩端專用金鑰配置（`CONSOLE_SI_AUDIT_KEY`／`AUTOSDD_SI_AUDIT_KEY`）。每個鍵開工先做 BRIDGE §8.4 基線採納（引本 PRD 為 Stage-1 上位文件）；現行鍵 `monorepo-selfimproving` 只管本 PRD 的 Stage-1 凍結。macOS 全部未驗（NFR-SI-06-5）。

### 9.7 SD 審閱紀錄（可行性審閱；逐條改到可行，改動最小）
審 §5 全部 FR／AC 與 §6 全部 NFR 的歷輪紀錄（首輪 SD、SCG-0 一審後 SD 修復、二審後收尾，**#1～#40**）已逐字搬到 `docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` 檔尾〈附錄 SD　PRD §9.7 審閱紀錄與 §9.0 SD 查證（自 PRD 搬出，逐字）〉SD-1（搬遷原因＝PRD 超過 Read 工具 256KB 上限，NFR-SI-08-1 同型；**編號不變**，本 PRD 內既有的「§9.7 #N」引用一律指該附錄同號列）。**本棒（SD／Architect，T1 修訂 v0.9；輸入快照＝PRD 修訂 commit `c2aee850`）審 FR-SI-30～34 的 22 條 AC 與 NFR-SI-01／02-4／06-6／07-4／09-4**；有改動者列於下表（#41 起）；其餘各條未改（可測性僅依 Given／When／Then 形態判斷、未逐條實作驗證；AC-SI-31-2～31-4、34-3、34-4 可由合成夾具判定，AC-SI-31-5 為 P＋D、不得讀成被擋）。

**可行性核對 FC-a～FC-f**（本棒現查；座標與數字是快照值，重跑＝照座標 Grep／量測）
| # | 核對項 | 座標與結論 |
|---|---|---|
| FC-a | Bridge 子行程先例的檔案與函式 | `AgentConsole/engine-bridge/app/sdd_cli.py`：`run_verb`（:249–310；`subprocess.Popen` :284–286、`communicate(timeout)` :292、逾時 `_reap` :213→504）、`DEFAULT_TIMEOUT_SECONDS = 20.0`（:48）、`build_cli_env`（:150–162：剝除 `BRIDGE_*`／`SDD_*`／`PYTHONPATH`，其餘環境原樣繼承，`MINIMAX_API_KEY` 不在剝除之列）、`procutil.popen_platform_kwargs()`（`procutil.py`:25）、`AuditLog.record`（`security.py`:83–105）；路由先例 `routers/sdd.py`（`APIRouter(prefix="/sdd")` :52、`_sdd_root` 的 503 `sdd_unavailable` :63–68）；設定先例 `settings.py`（`SDD_ROOT` :154–161、`_looks_like_monorepo` :76、`BRIDGE_SDD_WRITE_TOKEN` :110–123）；AST 鎖先例 `tests/test_sdd_integration_parity.py`（`write_shaped_calls` :355、:423、`test_only_sdd_cli_names_the_cli_module` :433）。**結論**：SI 沿同形新增 `app/si_cli.py`＋`app/routers/si.py`＋`SI_ROOT`；差異只有三處——環境改白名單（export 不需任何機密）、不帶 `-I`／`-P`（本棒以 3.11.9 實測 `python -I` 使 `sys.flags.safe_path` 為真，腳本目錄不進 `sys.path`，`import _stdio_utf8` 會失敗）、逾時 15 秒 |
| FC-b | Bridge 容器看得到 `tools/selfimproving.py` 嗎 | **看不到**：`AgentConsole/docker-compose.yml` 的 engine-bridge 服務（:190–231）只掛 `../AISDLC_SDD:/sdd:ro`、`engine_workspace:/workspace`、`app_logs:/app/logs`（:216–219），`BRIDGE_ALLOWED_PATH_ROOTS: /workspace`（:210）；映像（`engine-bridge/Dockerfile`:33–34）只 COPY `AutoClaude/` 與 `AgentConsole/engine-bridge/`、無 `.git`（`USER bridge`，uid 10001，:46）；`CONSOLE_ENCRYPTION_KEY` 只在 backend 環境（:136），Bridge 沒有。**結論＝P1b 前置條件**：Bridge 容器須唯讀掛載 repo——建議三段 `../tools:<SI_ROOT>/tools:ro`、`../docs/06_quality:<SI_ROOT>/docs/06_quality:ro`、`../.git:<SI_ROOT>/.git:ro`（`SI_ROOT=/repo`），**不掛 repo 根**：Bridge 容器內跑的是引擎執行的使用者指令（evaluator），根下被 `.gitignore` 排除的 `AgentConsole/.env`（部署機上存在時含 `JWT_SECRET`、`CONSOLE_ENCRYPTION_KEY`）會變成其可讀檔；整包唯讀掛載較簡單、代價即此（建議三段；三段不足時 `export` 的 `ne` 會逐欄列出量不到的欄位，不靜默）。寫入面的另一個事實：ADR-SI-10 的寫入鎖在**主機**家目錄，容器內寫帳本無法與主機寫入者互斥，故 P2b 的 `dec` 不在容器內寫（ADR-SI-03′）。`git` 對 bind mount 的擁有者檢查（uid 10001≠主機擁有者）需環境變數式 `safe.directory`（未實測，P1b 實作輪以真容器驗：映像 `git --version` 須 ≥2.31） |
| FC-c | backend 代理的 JWT 角色與 RTM 容納 | `infrastructure/config/SecurityConfig.java`:80（`GET /api/v1/**`→`VIEWER`／`OPERATOR`／`ADMIN`）、:81（`/api/v1/settings/**`→`ADMIN`）、:82（其餘 `/api/v1/**`→`OPERATOR`／`ADMIN`）；使用者清單 `application.yml`:83–92（`admin`／`operator`／`viewer`，`role` 欄 `ADMIN`／`OPERATOR`／`VIEWER`）；Architecture §8.2 表。**結論**：P1b `GET /api/v1/si/**` 任何登入者可讀，由 :80 既有規則涵蓋、`SecurityConfig` 零改動；P2b 於 :82 之前加 `POST /api/v1/si/**`→`hasRole("ADMIN")`，並要求帳號名在 `console.si.deciders`（`CONSOLE_SI_DECIDERS`）。RTM：`AgentConsole/docs/06_quality/RTM.md` 沒有程式碼閘讀它（`tools/` 與 AgentConsole 程式碼 Grep `RTM.md` 無相關命中；`agentconsole-ci.yml` 無 RTM 步驟），「US 58」對帳是其 §3.4 的人讀現查指令（只數行首為前綴編號的列）；先例 RTM.md:469（FsmTrail 本地編號子表，ID 加反引號故不計入總列數）可容納 SI 的 AgentConsole 側追溯 |
| FC-d | frontend 現有資料抓取方式 | TanStack Query（`@tanstack/react-query`；SWR 未用）：`frontend/lib/api/queries.ts`（`qk` :117、`useAllProjects` :189–196、`usePendingSignoffs` :255–262）；端點函式 `lib/api/endpoints.ts`（`getSddEngineStatus` :277–278 以 `apiRequest` 包裝）；fetch 封裝 `lib/api/client.ts`（`ApiError` :24、`apiRequest` :261）；預設重試政策 `components/providers/Providers.tsx`:14–28（4xx 不重試、其餘重試 1 次）；導覽 `components/layout/ToolsRegion.tsx`:23–29 的 `NAV`（六項，`layout.test.tsx`:132–136 斷言）；頁面慣例 `app/<route>/page.tsx` 薄頁＋`components/domain/<feature>/<Feature>View.tsx`。**結論**：沿此體例（〈C18 檔名表〉）；SI 查詢覆寫為 `retry:false`、`staleTime:0`、`gcTime:0`（不留過期快取，AC-SI-32-3）；導覽加第七項、`layout.test.tsx` 同步 |
| FC-e | `tools/lib/selfimproving/` 新檔數與 LOC tier | `AutoClaude/tools/check_loc_budget.py`:270–283（`guardrail_lib`≤400〔`tools/lib/`〕、`guardrail_cli`≤750〔`tools/`〕）；計價只算斷言行（:318–340）。現值（`--json` 的 `guard_taxonomy`）：`rows` 199、`check` 171、`params` 149、`ledger` 119、`refs` 114、`history` 92、`git` 61、入口 `tools/selfimproving.py` 56。P1 新增 16 檔（§9.1〈C4 套件檔案表〉）估 3,700 行（SD 估算，未實作、未量測），單檔估 ≤ 340、全部 ≤ 400；入口增至約 350（≤ 750）。**相容**；實作輪逼近 400 時先依職責拆檔、不調 tier |
| FC-f | `tools/tests/` 新檔撞護欄層棘輪 | 見 §9.0 末列：重釘為**實作輪收尾**（記憶 `guard-ratchet-repin-ritual` 13 道；`_REPIN_NET_CAP_SCHEDULE` :2709、`_REPIN_APPROVED_ROUND_OVERAGE` :2737、名冊上限 :2794），不是設計缺口；P0 測試的 P1 連動點見 #48 |

**審閱紀錄（#41 起；#1～#40 見上列指標）**
| # | FR／AC（原文摘要） | 改法 | 理由（座標） |
|---|---|---|---|
| 41 | AC-SI-30-1～30-5、NFR-SI-01／02-4／07-4／09-4、§2.1／§2.1.1／§3.2／§9.0／§9.1 C16／§9.4／§10.1／§12.1／§13.1／附錄 B／C.1／C.2 #10：研究抓取經 harness 的 WebFetch | 依主控 ⚖1／⚖2（附錄 C.2 #16）改為 **D-1′**：`si research --fetch` 由 CLI 自抓來源表 URL 的**原始位元組**（`fetch.py` 是唯一外聯處）；研究者只剩 Read／Grep／Glob；SA 的 `--record --dir` 取消；AC-SI-30-3／30-4／30-5 依任務書改寫，AC-SI-30-1／30-2 因字面含 `--record` 與「CLI 不經手網路」同步最小改寫（連動面）；`extract` 改義為「給研究者的閱讀指示」；初始來源表兩個 GitHub 來源改原始檔與 feed 網址（仍未驗）；C.2 #10 以〔訂正〕保留原文 | WebFetch 回的是 harness 模型處理後的文字，digest 無意義，主控逐字落檔是不可重放的人工搬運；CLI 自抓可重放、可用本機 HTTP 伺服器夾具做正負控（`fetch` 層以政策物件允許 loopback，CLI 入口不暴露；CLI 層以參數注入網路替身） |
| 42 | AC-SI-30-3、§9.2：`research.scan` 欄位與事件行長 | 依 ⚖3：`sources[]{id,sha256,bytes,changed,http_status}`＋`sources_sha256`＋`fetched_at`、`by=researcher`，不存 `url`、不存候選數；SA 的 `first` 欄取消（無前筆＝`changed=true`）；寫入前以實際行長把關（超 `event_max_bytes`＝rc 1＋OBS 草稿列） | SD 探針（scratchpad `arch_size_probe.py`、未入庫）：8 筆、`id` 滿 32 字元、`sha256:` 前綴、6 位數 bytes 的最壞行＝**1,642 bytes**＜2,000（每多一筆約 +174，上限約 10 筆）；7 筆 1,468 |
| 43 | AC-SI-30-1（`helmsman`）、AC-SI-30-6 | ⚖5：P1 只記 `sid`＋`line`（驗格式）、`check` 印 nonblocking NE（`QUOTE-VERIFIER-NOT-ESTABLISHED`，沿 `CARRIER-NOT-ESTABLISHED` 先例使 P0 基線 rc 不變），P2 與 AC-SI-12-4 ⑤ 共用驗證函式；⚖4：指紋 manifest 排除 `research_sources.json`，刪原 ⚖ 替代方案敘述（已否決案留註） | `params.py`:123–135 的 `fingerprint` 現對協定目錄全部檔雜湊；不排除則每次增減來源換代指紋、AC-SI-22-2 的並列限制失效 |
| 44 | AC-SI-32-1／32-3／32-5、§9.2、§9.3：匯出命名與分頁 | 頂層鍵統一 `schema_rev`、`kind`、`generated_at`、`head_sha`、`items[]`（SA 文字的 `schema`／`repo_head` 改名）；`generated_at` 不參與差分；游標統一 `--since`（嚴格大於；`events` 取 `seq`、其餘取 ID 數字部分）與 `--limit`（上限 `export_limit_max`），HTTP 同名 `since`／`limit`（任務書的 `since_seq` 推廣：observations、runs 沒有 `seq`）；新增 `--id` 取單筆（`GET /si/proposals/{id}`）；`ne`／`problems` 兩個頂層欄使量不到與帳本結構問題不被省略；Bridge 釘 `SI_EXPORT_SCHEMA_REV`，不符＝503 `si_unavailable` | AC-SI-32-1 要逐欄差分、AC-SI-32-3 要 fail-loud 並帶可對照的 `head_sha`；`generated_at` 每次不同；NFR-SI-09-1、06-6 要求量不到不得省略欄位 |
| 45 | AC-SI-32-3、NFR-SI-09-4、§9.3、§9.4：路徑 allowlist | SA 稿「repo 根與路徑參數過 `BRIDGE_ALLOWED_PATH_ROOTS`」改為：`SI_ROOT` 是伺服器端設定、請求不帶任何路徑參數、**不併入**該 allowlist（那是引擎 `execution_path` 的閘，NFR-SEC-03；併入會讓引擎可被指向掛載的 repo）；啟動拒檔案系統根（`settings._anchor_guard`）；`si_unavailable` 觸發條件改列「`SI_ROOT` 未設、未掛載或不含 `tools/selfimproving.py`」。**更正任務書前提**：Bridge 既有路徑違規回應是 **422** `violations[]`（`routers/sdd.py`:76–80 的 `unprocessable`），沒有 403；P1b 無請求層路徑，該情形不存在 | FC-a、FC-b；SDD 先例同形（`SDD_ROOT` 是伺服器設定，只有選填的 `root` 參數過 allowlist） |
| 46 | §9.3 Bridge 子行程環境 | 白名單環境（§9.3），不沿 `sdd_cli.build_cli_env` 的剝除清單 | FC-a：現行清單只剝 `BRIDGE_*`／`SDD_*`／`PYTHONPATH`，`MINIMAX_API_KEY` 會流進子行程；export 不需任何機密 |
| 47 | §9.4、NFR-SI-02-4：純度判準 | P0 `AT-030-2-1`（`tools/tests/test_selfimproving_check.py`:1866–1971）與 `AT-003-1-1`（:1318–1374）的靜態段以 `si_sources()`（:702–704，`glob("*.py")`）掃**整個套件**、禁網路 import 與寫入原語——P1 新增 `evwrite`、`fetch` 等檔會使它們轉紅；改為**能力登記＋import 閉包**（§9.4〈能力登記與純度判準〉）；`check` 的動態純度（檔案摘要與 `git status --porcelain` 前後相同、子行程只有淨化 `git`）不變 | 不削弱 `check` 純度，改以結構鎖住「唯讀動詞碰不到寫入或網路碼」；不是新增守衛碼（`tools/tests/` 形態判準、不在守衛面清單、不是 hook）；P0 TCS 凍結不改，AT 取代走 P1 TCS（是否在 P0 TCS 勘誤三另記一筆，待主控決定；本棒建議記，因 AT 字面「每個 `*.py`」被取代） |
| 48 | §9.3 `check`：21 項 | 21 項原樣保留（id、順序、語意、判定碼不變），P1 追加項接在其後、載體缺席一律 nonblocking NE；P0 測試的 P1 連動點（P1 TCS 一併改）：`items=21`／`ITEMS21` 全等斷言（`test_selfimproving_check.py`:712、726）、`status`／`prop-new` 須為 rc 3 的斷言（:1360–1362，改選仍未實作的動詞）、`baseline()` 合成 `params.json` 須補新鍵（否則 `PARAM_SPECS` 缺鍵而 `params.keys` 紅）、`si_sources()` 掃描面（#47） | 「`check` 的 21 項未被破壞」＝語意與順序不變；斷言字面隨追加項更新是 P1 的義務、不是回歸 |
| 49 | §9.2 `prop` 事件與 `event_max_bytes` | `prop` 事件只存結構欄（§9.2〈事件欄位表〉）；自由文字欄住 `rN.md`（`body_sha256` 綁定）；完整 `touched` 自 `rN.patch` 重新導出（digest 規則本就如此），事件存 `touched_count`＋`touched_sha256`；`prop-new` 於行長超限時拒收並要求拆分（AC-SI-14-3 同型） | SD 探針（`arch_size_probe2.py`）：`target`＋`touched` 兩個路徑集合都存時，1 路徑 1,009、3 路徑 1,297、6 路徑 1,729、10 路徑 2,306 bytes（＞2,000）；`touched` 只存 count＋hash 時 10 路徑 1,574、13 路徑 1,790（約容 16 個 `target` 路徑） |
| 50 | §5.1.3、§9.2：事件鍵衝突 | 事件共通鍵 `kind`（事件種類）與物件欄位同名者改名：`dec` 的 DEC `kind`→`dkind`（CLI 旗標仍 `--kind`）、`mea.report` 的 `kind`→`report`；`app.*` 的種類由事件 `kind` 後綴承載 | §5.1.3 與 §9.2 都用 `kind`（approve／reject… 與事件 `kind="dec"`）會在同一 JSON 物件內撞鍵 |
| 51 | §9.3 `research`、ADR-SI-10：網路與鎖 | 抓取在寫入鎖之外、鎖內只重驗與追加；`--run` 顯式（不靠「唯一 open 運轉」隱含）；部分失敗（≥1 來源）寫事件並 rc 2、零成功 rc 1 不寫（改記 `research.skip(offline)`） | 最壞 8×20＝160 秒＞ADR-SI-10 的取鎖逾時先例 60 秒（`tools/archive_apply_locked.py`）；一運轉恰一筆研究事件，單一失效來源不得讓該運轉永遠無法 `prop-new` |
| 52 | §9.2／`params.json`：新參數 | 新增 `research_timeout_seconds`（20）、`min_events`（1；AC-SI-08-4 ④ 的事件下限，先例 `min_obs_rows`）、`export_limit_max`（500），連同已列的 `research_fetch_max`（8）、`research_bytes_max`（262144）共五鍵，皆「初值（未校準）」入 `PARAM_SPECS`（頂層鍵依位元組序） | 有界停機參數一律住 `params.json`（C5）；`git.py` 的 `_TIMEOUT` 是 git 子行程常數、非研究網路預算 |
| 53 | AC-SI-34-1～34-4、C19 | 抽取規則定案（§9.1〈C19 判準〉）；探針現查：現行 SSOT §3 七列、6 列綠、SelfImproving 列的 `tools/probe/selfimproving_measure.py` 未建檔（C11 屬 P3、SSOT 卻寫「P1 探針」）⇒ 實作輪先改 SSOT 再落鎖；同時更正 §9.1 引言的「探針（P1）」→（P3）；AC-SI-34-2 名冊初值現查＝`quota`（16）、`skip`（6）、`ledger`（3）；AC-SI-34-3 現查僅 `selfimproving` 一個套件、已登記 | 否則落鎖當天正控即紅（SSOT §4 第 1 點：先改 SSOT 再落檔，不放寬規則）；SD 探針 `arch_layout_probe.py`、`arch_prefix_probe.py`（scratchpad、未入庫） |
| 54 | AC-SI-33-1／33-2、ADR-SI-03′、§8.1 P2b、§10.1 | ⚖8 定案（§9.5）；AC-SI-33-1／33-2 改寫為可測；原「Bridge 子行程呼叫 `si decide --carrier console`」改為「Bridge 只落稽核 JSON、主機端 CLI 入帳」 | FC-b：容器內寫帳本與唯讀掛載、主機寫入鎖域衝突（ADR-SI-10 的鎖在主機家目錄） |
| 55 | ADR-SI-11／12、§9.6、§8.1、§10.1、§12.1、附錄 A／C；§5 編號注意 | ADR-SI-11 改寫為 D-1′；ADR-SI-12 定案 A（無快取）、補三段掛載與 `safe.directory`；§9.6 鍵與依賴句更新（P1b 啟動指令 `python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-mirror`，腳本住 `AISDLC_SDD/scripts/`）；v0.8 的 ⚖ 逐處改為已裁決（附錄 C.2 #16）；§5 編號注意定案（P1 TCS 的自增 AC 帶階段前綴，如 `AC-P1-001-1`） | 連動面同一棒收齊（根 `CLAUDE.md` 第 5 條）；`--sub`／`--slug` 現查 `AISDLC_SDD/scripts/sdd_env.py`:72–73 |
| 56 | §9.1 C4／C16～C19、§9.2、§9.3：落點與檔名 | 新增〈C4 套件檔案表〉（16 新檔、能力類別）、〈C18 檔名表〉、〈C19 判準〉；§9.2 增〈事件欄位表〉、`research_sources.json` 格式、`export` 輸出 schema、鐵律三三列；§9.3 增 rc 通則與旗標，`research`／`scan`／`export`／`status`／`check` 列改寫，Bridge／Console 段改寫（端點、`since`／`limit`、`si_unavailable`／`si_not_found`、子行程形態、逾時 15／20 秒） | 任務書 §2 第 1～3、7 項；座標＝FC-a～FC-d |
| 57 | 檔案大小（NFR-SI-08-1 同型：Read 工具 256KB）、機械消費行警語 | **額外 A**：§9.7 原 #1～#40（含引言與表頭）與 §9.0 Q1～Q12 全文逐行搬至 `docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` 附錄 SD（SD-1、SD-2；只追加；搬遷以腳本逐行搬、不經人工轉錄），PRD 留指標與結論句；PRD 339,687 → 378,366 bytes（目標 ≤ 262,144：**未達**，差 116,222 bytes；§9 的技術定稿多於搬出量，再縮須搬遷 §10～§14、附錄或 FR-SI-30～34 的 AC 全文（結構性決定，待主控裁決））。**額外 B**：NFR-SI-02-1 的 glob 清單行與 §1.3 M1～M5 表之上各加一行 HTML 註解；`params.py`:75–95（`required_globs` 取首個含該粗體標籤的行）與 :159–180（`metrics_problems` 取 `startswith` 標題字樣的行與 M1～M5 列）的比對規則不受註解行影響（註解不含該粗體標籤、不以標題字樣起頭） | PRD 單行極長、Read 工具有 256KB 上限，大檔要分段讀；機械消費行警語避免日後改文時無意破壞 `check` 與 `metrics.md` 的逐字比對 |

## ⚠️ 10. 風險與依賴 (Risks & Dependencies)
### 10.1 風險評估
| 風險（來源） | 機率 | 影響 | 現有防線（座標） | 本 PRD 緩解 | 剩餘風險 | 負責人 |
|-------------|------|------|-----------------|------------|----------|--------|
| **Goodhart／指標被優化**（S-20、S-21） | 中 | 高 | 五問協定家族計數降為資訊欄（`FiveQuestion_Audit_Protocol/README.md`:85–89）；R-9.27／9.28 held-out（`AISDLC_SDD/CLAUDE.md`:331～332） | §1.3.1、FR-SI-20、22、NFR-SI-05 | 帳本與腳本是可寫純文字；偵測靠 git 歷史（AC-SI-04-3）而非機械擋寫 | 掌舵者、量測者 |
| **Reward hacking／目標玩弄**（S-17 附錄 H：代理移除偵測所需記錄而得滿分） | 中 | 高 | R-9.20.3 Generator／Evaluator 獨立；鐵律四 | FR-SI-11、18、20；AC-SI-04-3 | 提案者可能改「被評估對象」而非評估器；靠審查者唯讀與突變鑑別（FR-SI-19） | 審查者 |
| **自評偏誤**（S-03、S-11、S-24、S-25） | 高 | 中 | `evaluator_command` 二次驗證（`AutoClaude/CLAUDE.md`:175、239）；K=1 人工閘 | FR-SI-18（外部訊號為主）、19；AC-SI-06-1 | 提案者與審查者同為 Claude 家族，錯誤可能相關（S-11：錯誤獨立是矯正的必要條件）⇒ 只能降低、不能消除 | 主控 |
| **無界遞迴／無界增長／成本**（S-17、S-25、S-26） | 中 | 高 | `SDD_*_BUDGET`；Gap-042／048（`AutoClaude/CLAUDE.md`:200–201）；額度守衛 | NFR-SI-01；FR-SI-10、17、24 | 初值未校準；邊際報酬遞減只靠落後指標（回滾／再現），沒有領先指標 | 主控 |
| **Context collapse／brevity bias／記憶膨脹**（S-06、S-07、S-12） | 中 | 中 | `MEMORY.md` 載入上限（S-08）；preference 10 鍵；context 水位守衛 | FR-SI-09（增量 delta、禁整份重寫）、27 | delta 累積仍會膨脹；Playbook 與規則層沒有通用策展（SOP II-6） | 提案者 |
| **守衛面自我修改**（S-09、S-10、S-22） | 低～中 | 高 | 治理檔唯讀守衛（`.claude/hooks/block_destructive_git.py`:1445，僅 `AUTOSDD_UNATTENDED` 阻斷）；守衛面准入；harness 分類器（`.claude/**`） | FR-SI-07（轉交）、NFR-SI-02；零新增守衛碼 | 有人值守時 `_GOV_EXACT` 只出聲不阻斷；三份 `CLAUDE.md`、`governance/rules/*.yaml` 不在清單（理論洞 P4）；靠流程與審查者唯讀 | 主控 |
| **記憶污染／記憶獎勵膨脹**（S-13、S-11、S-22） | 中 | 高 | `knowledge_base` 存結果標籤；`MEMORY.md` 可人審 | FR-SI-02、09、27；K=1 閘 | Claude Code auto memory 由 harness 自寫、不在本迴圈控制內（誠實劃界）；只能事後稽核（只讀） | 掌舵者 |
| **Misevolution／工具與技能供應鏈**（S-22、S-09、S-10） | 低 | 高 | Rule 9；hooks deny 連 `bypassPermissions` 都擋（S-10）；治理檔唯讀守衛 | NFR-SI-02；FR-SI-07（skill／hook 一律轉交） | 新 skill／hook 啟用前的掃描流程本輪未確認存在（SOP II-6） | 掌舵者 |
| **信心懸崖**（S-25：裁判可靠度隨迴圈衰退） | 中 | 中 | K=1 人工閘；`meta_halt_monitor` | FR-SI-24（劣化暫停）、19（對照／突變，不靠裁判預測） | 後期提案的裁判可靠度仍可能衰退；以回滾／再現作落後訊號 | 掌舵者 |
| **提案疲勞（審閱瓶頸）** | 中 | 中 | — | FR-SI-10（≤3）、§7 三句話卡、預設拒絕（不審＝不變） | 長期不審則迴圈靜止（安全但無價值）；無採納窗可評估＝M1 NOT-EVALUABLE（不是「顯示無改善」），價值主張長期未證，見下列「樣本過小」列與 §1.1 | 掌舵者 |
| **樣本過小致指標常態 NOT-EVALUABLE** | 高 | 中 | NOT-EVALUABLE 體例（五問協定） | FR-SI-22（印樣本數與基線窗事件數；不以小樣本宣稱；M1 的 NE 護欄量事件數，§1.3） | 基率≈0（§1.3 檢定力說明）⇒ 多數採納窗的 M1 為 NOT-EVALUABLE；P3 出口 (b)(d) 可能長期達不到 ⇒ 價值主張長期「未證」；是否維持由掌舵者決定 | 量測者 |
| **額度耗盡**（C-16） | 高 | 中 | 額度守衛、`--pace` | NFR-SI-07 | 研究型 Web 工具節流已被實測成瓶頸（OBS-SI-005）；運轉期除 FR-SI-30 的限定來源增量掃描外不使用 Web（§3.2），且該掃描受 `RESEARCH_FETCH_MAX`、`quota-band` 免掃牽制（v0.9：CLI 抓取不是 Web 工具呼叫，不受守衛節流牽制）〔訂正（T1 修訂，v0.8）：原文「運轉期不使用 Web（§3.2）」〕 | 主控 |
| **外部內容毒化（研究者）**（S-13、S-09、S-22；與 FR-SI-02 同源） | 中 | 高 | FR-SI-02（外部衍生不得單獨充當證據）；研究者無 Web 工具（外聯只在 CLI `fetch.py`）；守衛面准入 | FR-SI-30（來源白名單僅 T1 增減、工具白名單、抓回內容是資料不是指令、產物只入帳為 OBS 候選、PROP 仍須內部來源）；§9.4 | 研究者工具白名單是 P 型（無機械物）、「只抓表內 URL」由 CLI 機械限定（M）；來源站台本身可被第三方改寫；來源檔內容進入研究者與主控 context 後仍可能夾帶指示（須當資料讀）；`外部衍生=是` 標記由入帳的主控填寫 | 主控 |
| **Console 權限面**（Console 成為 DEC 第二載體；Bridge 無認證） | 低 | 高 | Console RBAC 與簽核硬閘（Architecture §8.2）；Bridge 只准 backend-net（Architecture §12.1 L-6）；`X-Bridge-Token`（Architecture §10.2） | P1b 零寫入端點（AC-SI-32-2）、需登入（AC-SI-32-4）；P2b 僅掌舵者帳號＋稽核列（AC-SI-33-1、33-2），驗證設計＝ADR-SI-03′（稽核 JSON＋HMAC＋主機端 CLI 入帳；⚖ 兩點待主控確認） | Console 路徑沒有逐字稿，偽造決定的偵測弱於逐字稿載體（HMAC 金鑰在主機環境、防不了主控；以 Console DB 稽核列對帳補強，ADR-SI-03′）；「掌舵者帳號」＝Admin 角色且在 `CONSOLE_SI_DECIDERS`（JWT 使用者清單在 `application.yml`，Architecture §8.1） | 掌舵者、主控 |

### 10.2 依賴項目
**技術依賴**：AutoClaude EventBus／EvolutionPlugin（`AutoClaude/autoclaude/core/`、`plugins/`）；SDD FSM runtime CLI（`FSMRuntime`）與 R-9.2x 提案管線；缺陷帳本與其工具（`tools/check_defect_log_crossref.py`）；Claude Code harness 的記憶／hooks／skills 行為（以 S-08／S-09／S-10 為準，現行頁面描述，不以版本號當觸發）；git；額度守衛。
**團隊依賴**：掌舵者審閱（唯一核准者）；QA 獨立審查（SCG-0）；SD 補架構方向（§9）。
**再查證觸發**：本 PRD 引用的 DP／S-NN 失效時依 SOP II-7（T-1 追溯斷裂、T-2 dogfood 失效、T-4 反證浮現、T-7 來源失效等症狀）重跑相關步驟，不整份重跑。

**🔴 人機協作確認點**：[ ] 所有風險已識別　[ ] 緩解措施可行　[ ] 依賴項目已確認

## 🔍 11. 既有系統分析 (Existing System Analysis)
### 11.1 現況分析
**系統概況**：AutoSDD 已有分散的自我改進面（引擎內演化／知識庫、SDD 規則提案管線、根層缺陷帳本與審計協定、Claude Code 記憶／hooks／skills）。共同特徵：多數已守「只提案、人工閘」，但各面各自為政——沒有統一的提案物件、冷卻、獨立評估器、症狀指標與退役。**盤點基準**：寫稿期間 HEAD 由 `a50bc04c` 前進到 `b78effb4`（主控並行提交），下表以 `b78effb4` 時的檔案為準，座標一律現查。

| # | 面 | 位置 | 學什麼 | 怎麼套用 | 閘門 | 缺口 → 對應 FR |
|---|----|------|--------|---------|------|----------------|
| 1 | AutoClaude 演化 | `autoclaude/evolution/`（`playbook_evolver.py`、`minimax_evolver.py`）＋`plugins/evolution_plugin.py` | ESCALATION 失敗鏈→INJECT_STEP／SPLIT_STEP／REVISE_EVALUATOR 提案（AI 優先、規則 fallback） | Kernel 路徑回傳 `MutationProposal`、只寫 log（`AutoClaude/CLAUDE.md`:191）；舊路徑 `apply_evolution` 寫 `evolved_<檔名>.yaml` | `max_evolutions=3`、per-step 上限 2、`require_evolution_signoff`（預設 False） | 只提案靠「無生產建構點」；`REVISE_EVALUATOR` 動到評估器；無 held-out → FR-SI-11、20、28 |
| 2 | AutoClaude 知識庫 | `utils/knowledge_base.py`＋`plugins/knowledge_base_plugin.py` | 成功／升級結果→error_signature→策略映射（JSONL） | 查詢命中直接跳到歷史有效策略 | `_MAX_ENTRIES=1000`；帶結果標籤 | 容量汰除無人審、無退役條件 → FR-SI-09、27 |
| 3 | AutoClaude 偏好記憶 | `plugins/preference_memory_plugin.py` | 使用者偏好（人寫入） | PRE_CORRECTION 唯讀注入 correction prompt | ≤10 鍵；Brain 輸出不得回寫（ADR-AGT-003 §2） | 寫入通道已查證（§9.0 Q2）：Port 只有 get／set／list、無 delete，唯一 production `set` 呼叫點為 `core/wiring.py`:187（啟動時以 config seed）→ 只讀接點 |
| 4 | AutoClaude 轉譯策略學習 | `plugins/translation_learner_plugin.py`＋`core/ports/translation_learning.py` | RTM 覆蓋度歷史的失敗頻次→轉譯策略改進候選 | 只產 `proposed`、dedup、`record_proposal` | `translation_max_proposals_per_run=3`；apply＝人工 signoff 守界 | 提議的審閱者與介面已查證（§9.0 Q1）：落地＝`<checkpoint_dir>/translation_learning/PROPOSALS-<project>.jsonl`，讀取者只有 plugin 自己的 dedup，現況無固定審閱者與介面 → FR-SI-08、12、14 |
| 5 | AutoClaude 收斂／目標驗證 | `plugins/convergence_plugin.py`、`plugins/goal_synthesis_plugin.py` | 即時 trend 判定；DONE 前 Brain 驗證 global_goal，未達成→`MutationProposal(INJECT_AFTER)` | run 內動態步驟突變（不落盤） | `goal_synthesis_fail_closed=False`（預設 fail-open，`utils/config.py`:211） | Brain 判定屬自評點，是否有外部校驗未逐一盤點（SOP II-6）→ FR-SI-18（僅涵蓋進迴圈者） |
| 6 | AutoClaude 回寫與進度 | `plugins/rtm_writeback_plugin.py`、`plugins/goal_progress_plugin.py` | RTM 覆蓋度報告、跨 run 進度快照 | 諮詢用報告／帳本，不覆寫人工 RTM | — | 資料來源（只讀） |
| 7 | SDD 規則提案管線 | `tools/fsm_runtime/{production_to_fpl,slv_generator,spec_patch_proposer,scaffold_gc}.py`；`governance/rules/R-9.20～R-9.37` | 生產偏差→FPL→SLV 草案；spec_defect 重複→SPEC-PATCH 草案；規則 ROI→退役提議 | 一律 `proposed`；LEARNING_COMMIT／HUMAN_PENDING 人工 review（`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`:395–396） | `set_maturity(reviewed_by=)`、`MAX_PATCH_PER_AC=2`、`meta_halt_monitor` | AutoClaude 與根層無對等管線；僅 SDD 面完整 → FR-SI-08（R 類）、25、26 |
| 8 | SDD 元停機與 held-out | `tools/fsm_runtime/meta_halt/`、`objective_tuner.py`、`dimension_necessity_oracle.py`、`joint_calibration_oracle.py`、`counterfactual_replay.py`；R-9.24／9.27～9.29 | 元迴圈採納／退役抖動；tuner 與 held-out 對抗分離 | advisory＋有界 | `SDD_META_CHURN_MAX`、`SDD_REPLAY_MAX_CASES`、`SDD_OBJ_TUNE_BUDGET` | 機制只服務 SDD 自身評分器（依檔名與規則文判斷，未逐檔讀碼），未通用化到記憶／Playbook／文件 → FR-SI-20、26 |
| 9 | SDD 測試失敗映射 | `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/skills/test-failure-analyzer/SKILL.md` | 失敗 TC→RTM→AC／US／F，判修程式或修 Spec | advisory skill（allowed-tools: Read） | — | 歸因的既有映射來源 → FR-SI-05 |
| 10 | 根層改進軌道與缺陷帳本 | `docs/04_planning/AutoSDD_improving_NN.md`（軌道①）、`docs/06_quality/AutoSDD_Defect_Log.md` | 缺陷／摩擦→DEF 列，附「再開症狀」文字 | 人工單一窗口入帳；休眠範本〈🏁〉T1～T4 | 每列 ≤700 bytes；crossref 閘 | 復發連結無結構化欄；發現日期無時分 → FR-SI-01、04、06 |
| 11 | 根層五問審計協定 | `docs/06_quality/FiveQuestion_Audit_Protocol/`、`docs/06_quality/FiveQuestion_Round_Ledger.jsonl` | hook 行為症狀量測 | 症狀閘＋三態；家族計數降為資訊欄 | `params.json` | （參考體例）→ FR-SI-19、22 |
| 12 | 根層事後量測器 | `tools/probe/audit_session.py`、`tools/probe/misstep_attribution.py` | 逐字稿／帳本的違規與失誤歸因（關鍵詞啟發式，量級可信） | 只量不閘（`audit_session.py` 檔頭:8–14） | — | 歸因／量測的既有載體 → FR-SI-05、22 |
| 13 | Claude Code 記憶檔 | `~/.claude/projects/<slug>/memory/`（`MEMORY.md`＋記憶檔；不在 repo 內） | Claude 依修正與偏好自寫筆記（S-08）；人可編輯／刪除 | 每次對話載入索引（有上限）；視為 context 非強制設定 | 寫稿時 `MEMORY.md` 22,755 bytes／113 行（目錄共 125 個 .md 檔含索引；本稿量測）；2026-10-19 主控人工歸檔後 22,755→15,558 bytes／113→76 行（OBS-SI-016，PROP-SI-003 的手動先例；§9.0 Q5） | 無結果標籤、無退役機制（歸檔靠人工）；harness 自帶近上限提醒與超限錯誤回報（S-08；寫入者不受控）；依寫入來源過濾未見；auto memory 不在迴圈控制內 → FR-SI-02、09、27 |
| 14 | Claude Code hooks／skills | 根 `.claude/hooks/`、`.claude/settings*.json`；各子專案 `.claude/skills/` | hooks＝確定性控制（deny 連 bypassPermissions 都擋，S-10）；skills 由 Claude 自建／改寫（S-09） | 守衛面准入；治理檔唯讀守衛 | `allowed-tools`、`` !`cmd` `` 風險（S-09） | 新 skill／hook 啟用前掃描流程未確認存在 → FR-SI-07（轉交） |
| 15 | AgentConsole | `AgentConsole/CLAUDE.md`:15；`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md` | BRD／PRD 匯入、人工 signoff 硬閘、FSM 唯讀顯示 | SDD FSM 寫入一律經 `FSMRuntime` CLI 子行程 | — | P1b 起整合唯讀鏡像、P2b 起整合決定載體（§3.3 F-SI-101 已再開）→ FR-SI-32、33（以 FR-SI-12 的既有人工閘為依據）〔訂正（T1 修訂，v0.8）：原文「MVP 不整合提案卡（⏸，§8.3）」〕 |
| 16 | 休眠重評與延後體例 | `docs/04_planning/AutoSDD_improving_116.md` §9、`AutoSDD_improving_115.md` §5.2、PRD v2.1 §16 | 每輪末歸格＋延後清單附可觀測再開症狀 | 只准三分類；四格結案帳 | — | §8 階段出口沿用此體例 |

### 11.2 缺口表（接既有／新建）
| 缺口 | 證據座標 | 對應 FR | 類型 |
|------|---------|---------|------|
| G-SI-01 演化「只提案不套用」靠無生產建構點；`apply_evolution` 呼叫點仍在 | `AutoClaude/CLAUDE.md`:191；`_escalation_handler.py`:111／208／263；`_complex_mutations.py`:114；OBS-SI-010 | FR-SI-28 | 既有缺口收斂 |
| G-SI-02 `require_evolution_signoff` 預設 False 與文件宣稱並存 | `AutoClaude/autoclaude/utils/config.py`:194；`execution/playbook_runner.py`:299–322 | FR-SI-28（AC-2） | 既有缺口收斂 |
| G-SI-03 `REVISE_EVALUATOR` 與評估器隔離衝突；兩條路徑語意不一（Kernel 路徑轉成 `REVISE_CURRENT` 的 prompt 包裝，舊路徑直接覆寫 `evaluator_command`）；`AutoClaude/CLAUDE.md`:109 原只列兩型，已於 `738f4f60` 補列（OBS-SI-009） | `evolution_plugin.py`:259、284；`playbook_evolver.py`:255–259 | FR-SI-11 | 新建（不受理） |
| G-SI-04 AutoClaude 演化提案與根層改進迴圈皆無 held-out／獨立評估器 | SOP II-6 | FR-SI-20 | 新建（通用化 SDD 機制） |
| G-SI-05 Playbook 與規則層無通用 delta 策展 | SOP II-6 | FR-SI-09 | 新建 |
| G-SI-06 無邊際報酬遞減停機規則 | SOP II-6 | FR-SI-24 | 新建 |
| G-SI-07 記憶面無結果標籤／退役機制；索引曾逼近載入上限（2026-10-19 主控人工歸檔後 22,755→15,558 bytes／113→76 行，PROP-SI-003 的手動先例）；harness 另有自帶的近上限提醒與超限錯誤回報（S-08；SCG-0 一審 F-05），其寫入者不受控，與 SI 容量事件並存（AC-SI-27-1） | `MEMORY.md`（本機，不在 repo）；S-08；OBS-SI-016；§9.0 Q5 | FR-SI-02、09、27 | 新建 |
| G-SI-08 新 skill／hook 啟用前掃描流程未確認存在 | SOP II-6 | FR-SI-07（轉交；不新增守衛碼） | 登記（理論洞） |
| G-SI-09 可進化／不可進化面缺機械分界（`_GOV_EXACT` 僅無人值守阻斷、僅涵蓋 Write／Edit／NotebookEdit，不含三份 `CLAUDE.md`、`governance/rules/*.yaml`） | `.claude/hooks/block_destructive_git.py`:1423–1472 | FR-SI-07、15（流程性邊界） | 登記（理論洞；守衛面准入） |
| G-SI-10 復發連結無結構化欄；DEF 發現日期無時分 | `AutoSDD_Defect_Log.md`:70（欄位列）、DEF-200-551 列 | FR-SI-01、06、22 | 新建（OBS 側）；DEF 側欄位變更須掌舵者裁決（附錄 C.2 #3） |
| G-SI-11 `PROP-SI-NNN` 沒有定義的載體：目前只出現在觀察帳本處置欄文字 | OBS-SI-005、OBS-SI-012 | FR-SI-08（物件定義）；載體形態＝JSONL 事件帳本＋PROP 內容檔（§9.2；附錄 C.2 #5） | 新建 |
| G-SI-12 驗證三態與突變鑑別在產品面未成文：只見於整合輪 116 QA 實務 | `AutoSDD_improving_116.md` §9.1 | FR-SI-19 | 新建（成文化既有實務） |
| G-SI-13 提案無冷卻（SDD 規則面有抖動防護，其他面無） | R-9.24.1／9.24.2 | FR-SI-13、26 | 新建（通用化） |
| G-SI-14 `translation_learner` 的 proposed 提議未見固定審閱介面 | `translation_learner_plugin.py`:10–19；`AutoSDD_improving_115.md` §5.2（Console 路徑活化列為延後） | FR-SI-14（提案卡）、§8.3 ⏸ | 新建（現況審閱者已查證＝無，§9.0 Q1；該提議不轉 PROP、歸因後走 DEF，§9.2） |
| G-SI-15 運轉期沒有取得外部最新資訊的機制：§3.2 原禁運轉期 Web，SOP 已完成、深度重跑只依 S7；T1 要求每次啟動驗進 | T1 2026-10-19 問題 1b1；§3.2（v0.8 前原文） | FR-SI-30 | 新建（限定來源、增量、有界；接 FR-SI-02） |
| G-SI-16 無主動體檢入口：現行只有被動擷取（子代理「流程摩擦」交卷＋主控發現），沒有動詞或角色主動檢討四個模組 | T1 問題 1a；§9.1 C2（既有量測器皆為唯讀來源，無人呼叫它們彙整） | FR-SI-31 | 新建 |
| G-SI-17 Console 無 SI 端點與頁面（F-SI-101 再開） | T1 問題 1c；`AgentConsole/docs/02_architecture/Architecture.md` §5.1 路由樹與 §10 契約皆無 `/self-improving`、`/si/*` | FR-SI-32、33 | 新建 |
| G-SI-18 根層模組落點無機械鎖 | OBS-SI-105；`docs/02_architecture/Root_Layout_and_Module_Placement.md` §5 自陳「沒有機械鎖」 | FR-SI-34 | 新建（形態判準測試） |

### 11.3 影響分析
| 模組／功能 | 影響程度 | 需要修改 | 風險 |
|-----------|---------|---------|------|
| AutoClaude 演化面 | 低 | 加可重跑檢查（FR-SI-28）；不改既有行為 | 零退化；須過 AutoClaude 全套與 lint |
| AISDLC_SDD runtime／規則 | 低 | 重用既有 proposed 管線；不改 `_HAPPY_PATH`、不改規則本體 | 不得引入新 FSM 狀態（禁令 8、9） |
| 根帳本與文件 | 中 | 新增欄位與提案／決定載體；DEF 側欄位變更須掌舵者裁決 | 每列 ≤700 bytes；crossref 閘需同步 |
| 記憶面 | 中 | 新增條目規範與容量事件 | 條目規範只約束經本迴圈寫入者；harness 自寫條目不受控 |
| Hooks／settings／守衛面 | 無 | 零修改（守衛面准入） | — |
| AgentConsole | 低（P1b 起；原「無」） | P1b：Bridge 新增 `/si/*` 路由、backend 新增唯讀代理、frontend 新增頁與導航項；P2b：一條決定端點（Bridge、backend 各一）與一張新表 `si_decisions`（Flyway 新版本，ADR-SI-03′）；不改既有端點與既有資料表〔訂正（T1 修訂，v0.8）：原文「無／MVP 不改（⏸）」〕 | 不得動根層 `tools/`（`AgentConsole/CLAUDE.md` 鐵律 7）；其 RTM 有「US 58」對帳（SI 追溯落根層 RTM，AgentConsole 側可補本地編號子表〔先例 RTM.md:469〕）；Bridge 映像無 `.git`（Architecture §12.2 V-11）→Docker 需唯讀掛載 `tools/`、`docs/06_quality/`、`.git/`（NFR-SI-06-6；§9.7 FC-b） |

**向後相容性**:
- [x] 需要保持向後相容（既有演化行為、DEF 帳本體例、既有 OBS ID 不變）
- [ ] 允許 Breaking Changes

**🔴 人機協作確認點**：[ ] 影響範圍已完整評估　[ ] 相容性策略已確認

## 🔗 12. 整合規格 (Integration Specifications)
### 12.1 接點表
| # | 接點 | 對象與座標 | 資料流向／內容 | 權限 | 備註 |
|---|------|-----------|---------------|------|------|
| 1 | AutoClaude Plugin／EventBus | `autoclaude/core/event_bus.py`、`plugins/*` | 讀 ON_ESCALATION／ON_SUCCESS 產物（KB jsonl、escalation dump、checkpoint） | **只讀** | MVP 不新增 Plugin；新增須走 Plugin SOP（`AutoClaude/CLAUDE.md`） |
| 2 | AutoClaude 演化提案 | `EvolutionPlugin` 的 `MutationProposal` | 流入 PROP（FR-SI-08） | **提案**；套用**需人工**（FR-SI-12／16） | `apply_evolution` 現有呼叫點受 FR-SI-28 檢查 |
| 3 | SDD R-9.2x 提案管線 | `slv_generator`／`spec_patch_proposer`／`scaffold_gc`／`rule_loader.set_maturity` | R 類沿用；本迴圈只加歸因、冷卻、量測 | **提案**＋**需人工**（HUMAN_PENDING／`reviewed_by`） | 不新增管線 |
| 4 | SDD FSM runtime | `FSMRuntime` CLI（`python -m tools.fsm_runtime.fsm_runtime`） | 讀 `show` | **只讀** | 寫入一律經 CLI（禁令 1）；本迴圈不新增 FSM 狀態 |
| 5 | AgentConsole 簽核與顯示 | `AgentConsole/CLAUDE.md`:15；ADR-XPLAT-016 | P1b 唯讀鏡像（帳本與提案卡）；P2b 決定載體（見 #12） | P1b：**只讀**；P2b：既有簽核硬閘內（**需人工**） | F-SI-101 已再開為 FR-SI-32、33〔訂正（T1 修訂，v0.8）：原文「MVP 不整合；post-MVP 唯讀鏡像提案卡／MVP：無；post-MVP：只讀＋既有簽核硬閘／⏸ F-SI-101」〕 |
| 6 | Claude Code 記憶檔 | `~/.claude/projects/<slug>/memory/` | 讀：稽核報告；寫：M 類提案經核准後由人晉升 | 讀＝**只讀**；寫＝**提案**＋**需人工**；harness 自寫＝不受控 | 回滾＝逐行反向 patch；前置快照僅作稽核副本（AC-SI-16-2） |
| 7 | Claude Code hooks | `.claude/hooks/`、`.claude/settings*.json` | 讀 hooks 痕跡與量測器輸出；不新增、不修改 | **只讀**；任何變更＝守衛面准入（需暴露證據＋**需人工**） | 活性現查見根 `CLAUDE.md`〈hook 載具〉 |
| 8 | Claude Code skills | 各子專案 `.claude/skills/` | D 類提案 diff；啟用前掃描 `allowed-tools`／`` !`cmd` ``／夾帶 hook（S-09） | **提案**＋**需人工**；掃描＝**只讀** | `.claude/**` 屬受保護路徑 ⇒ 轉交（FR-SI-07） |
| 9 | 缺陷帳本／五問協定／休眠範本 | `AutoSDD_Defect_Log.md`、`FiveQuestion_Audit_Protocol/`、`AutoSDD_Iteration_Prompt_Template.md` | 讀；OBS→DEF 升級依帳本既有單一窗口治理 | **只讀**；升級＝**需人工**（單一窗口） | 不改既有協定一字（改協定＝`window_reset`） |
| 10 | 額度守衛 | `python tools/session_resume_planner.py --pace`、`tools/lib/quota_gate.py` | 派工前查詢 | **只讀** | 每次現查，不得記住上次值 |
| 11 | git | 根 repo | 沙盒副本／晉升 commit／回滾 revert | 晉升與回滾＝**需人工**；沙盒＝自動可丟棄 | 鐵律五擋毀滅性形態 |
| 12 | Bridge `/si/*`、backend `/api/v1/si/**`、frontend `/self-improving` | `AgentConsole/docs/02_architecture/Architecture.md` §5.1／§10／§11；根層 `tools/selfimproving.py export`（Bridge 以子行程呼叫） | 讀：`export` 的 JSON→Bridge→backend→頁面；P2b 寫：稽核 JSON（Bridge）→主機端 `decide --carrier console` | P1b：**只讀**；P2b：**需人工**（掌舵者帳號＋`X-Bridge-Token`） | 差分、唯讀、fail-loud（AC-SI-32-1～32-3）；Docker 需唯讀掛載 `tools/`、`docs/06_quality/`、`.git/` 三段（NFR-SI-06-6；§9.7 FC-b） |
| 13 | 外部網站（研究來源表列出的 URL） | `docs/06_quality/SelfImproving_Protocol/research_sources.json`；`si research --fetch`（CLI，`fetch.py`） | 讀：原始位元組→家目錄 `research/<id>/<sha12>.txt`→研究者讀檔→OBS 候選（主控入帳） | **只讀**；外聯唯一例外（NFR-SI-02-4）；產物只入帳為 OBS 候選 | 不跟隨表外連結、不用 WebSearch、研究者無 Web 工具；URL 皆未驗，首跑驗 |

### 12.2 資料流向、同步策略與錯誤處理
- **資料流向與同步**：事件驅動、單向（來源 → 觀察 → 歸因 → PROP → DEC → 套用／驗證 → 量測 → 退役）；無常駐行程、無排程（PRD v2.1 §16.1 ➖ 不做 Daemon）；同步頻率不適用，啟動只依 AC-SI-03-1 的五類事件；研究掃描（FR-SI-30）與體檢（FR-SI-31）是運轉內或按需的擷取動作、不是啟動事件；Console 的 Bridge／backend 是 AgentConsole 既有服務，按需以子行程呼叫 `export`，SI 自身仍無常駐行程。
- **錯誤處理**：修訂 ≤ `MAX_REVISIONS`、驗證重跑 ≤ 2，超界即停、不退避重試（禁令 4）；階段失敗留一筆 OBS（分類 `bug`）並於提案卡標示；ESCALATION 後僅人工恢復（禁令 6、7）；資料補償＝回滾配方（NFR-SI-04），人工執行。

**🔴 人機協作確認點**：[ ] 各接點的權限標示（只讀／提案／需人工）已確認　[ ] 同步策略符合需求　[ ] 錯誤處理機制完善

## 📎 13. 附錄 (Appendix)
### 13.1 詞彙表 (Glossary)
| 術語 | 定義 |
|------|------|
| 觀察（OBS）／提案（PROP）／決定（DEC） | OBS＝帶座標的一句症狀記錄，不取代 DEF 缺陷帳本；PROP＝起始狀態必為 `proposed` 的改進物件，產生者無正式面寫入權；DEC＝掌舵者對 PROP 的人工決定紀錄，綁 digest |
| 運轉／再開症狀／容量事件 | 運轉＝由啟動事件起、到該次各提案皆落入終態止的一次迴圈執行（非日曆週期）；再開症狀＝一句可觀測事件，成立時重新啟動某延後項，不得含輪號、日期；容量事件＝有上限的儲存用量達 `CAP_FRAC`，觸發退役／合併提案 |
| 歸因／根因鍵／復發 | 歸因＝把觀察映射到 DEF／OBS／規則／Playbook 步驟／文件／記憶條目的座標清單（不含自評分數）；根因鍵＝`<面>/<機制>` 短字串，由歸因者提出、審查者確認；復發（再現）＝已結列所防症狀再次發生且經審查者確認 |
| 機會列／採納窗／基線窗 | 機會列＝同目標前綴（M 類：同根因鍵或引用同條目）的新立 OBS／DEF 列；採納窗＝晉升後累計 `W_OPP` 筆機會列或再現／回滾先到者；基線窗＝同一 PROP 晉升前、同規則的最近 `W_OPP` 筆機會列（AC-SI-23-1；M1 以兩窗前後對照，§1.3） |
| 暴露度／守衛面 | 暴露度＝P2 的必要條件：a 掌舵者真機回報／b 非構造性逐字稿／c 真實語料重放命中（`severity.md`〈暴露度〉）；守衛面＝根 `CLAUDE.md`〈守衛面准入〉所列 `.claude/hooks/**`、`.claude/settings*.json`、指定 `tools/lib/` 檔與 `tools/session_resume_planner.py` |
| 不可進化面／可進化面／轉交 | 不可進化面＝NFR-SI-02-1 清單（含凍結版本目錄與模板；以 PROP 的 `rN.patch` 全部路徑逐一比對），本迴圈不得以 PROP 對其寫入（SI CLI 自己的運轉紀錄除外）；可進化面＝M 記憶條目／P Playbook 片段／R SDD 規則草案／D 非治理文件 diff；轉交（handoff）＝目標或 patch 任一路徑在不可進化面時，把整張提案交給既有人工通道（DEF／R 系列／T1／PRD 修訂） |
| K=1／digest | K=1＝逐項人工核准，一個決定對應一個 PROP、不批次；digest＝PROP 內容摘要（演算法見 §9.2），核准綁定此值、內容變動即失效 |
| 沙盒／晉升／回滾配方 | 沙盒＝與正式面隔離的副本，丟棄即回原狀；晉升＝把已驗證的沙盒變更合入正式面，必為人工動作；回滾配方＝一個動作即可回到採納前的指示（git revert、逐行反向 patch、刪檔、`set_maturity` 退回；前置快照僅稽核副本，AC-SI-16-2） |
| 對照／突變／held-out | 對照／突變＝基線重現症狀、套用後消失、弱化後再現，缺一則驗證無鑑別力；held-out＝提案者看不到的評估資料與指令，由提案者以外角色凍結 |
| 三態（NE） | PASS／FAIL／NOT-EVALUABLE（簡寫 NE）；NE 不算 PASS |
| 冷卻／劣化暫停 | 冷卻＝被否決的同型提案暫禁再提，直到掌舵者解除或出現與原證據不相交的新證據（再提資格事件）；劣化暫停（SUSPENDED）＝連續採納劣化時迴圈停止受理提案，僅掌舵者可恢復 |
| Goodhart／context collapse／misevolution | 對代理指標過度最佳化損害真實目標（S-20、S-21、S-17 附錄 H）；整份重寫逐漸侵蝕細節（S-06）；自我演化經 model／memory／tool／workflow 路徑無意走偏（S-22） |
| 判準指紋／訂正協議 | 指標定義的摘要，指紋不同的數字不得並列（先例 `audit_session.py` 輸出）；修正舊文時原文逐字保留、不靜默覆寫（先例 `AISDLC_SDD/CLAUDE.md` 各〈訂正〉段） |
| 研究掃描／研究來源表／增量／體檢／Console 載體 | 研究掃描＝運轉內由 `si research --fetch` 依研究來源表抓取外部來源的原始位元組、研究者（Sonnet 子代理，只讀檔）只產 OBS 候選的擷取動作（FR-SI-30；不是啟動事件）；研究來源表＝`research_sources.json`，運轉期、僅 T1 增減，≠ SOP II-3 的 S-NN 文獻表；增量＝CLI 對來源原始位元組自算 `sha256` 與上一筆同 `id` 比對得 `changed`；體檢＝`si scan`（確定性、唯讀）加唯讀子代理依模組體檢入口表逐項檢，產物只是 OBS 候選（FR-SI-31）；Console 載體＝DEC 的第二種載體（第一種＝逐字稿），P2b 起，`dec` 事件帶 `carrier=console`（FR-SI-33） |

### 13.2 參考資料
- **上游與帳本**：SOP `docs/05_development/SelfImproving_Research_Methodology_SOP.md`；觀察帳本 `docs/06_quality/SelfImproving_Observation_Ledger.md`。
- **研究來源（只引 SOP 來源表 S-NN；層級 V1／V2／V3 與 URL 見 SOP II-3；本 PRD 不引用任何來源的量化結果——V2 數字是小模型轉述，引用前須開原頁面核對）**：S-01 Reflexion；S-02 Self-Refine；S-03 Large Language Models Cannot Self-Correct Reasoning Yet；S-05 Voyager；S-06 Agentic Context Engineering；S-07 Effective context engineering for AI agents；S-08 Claude Code 記憶官方文件；S-09 skills 官方文件；S-10 hooks 官方文件；S-11 Memory Reward Inflation；S-12 When Continual Learning Moves to Memory；S-13 MemoryGraft；S-14 Coding Agents are Strong Prompt Optimizers；S-15 MAS-PromptBench；S-16 ADAS；S-17 Darwin Gödel Machine；S-18 AlphaEvolve；S-19 Ouroboros；S-20 Scaling Laws for Reward Model Overoptimization；S-21 Categorizing Variants of Goodhart's Law；S-22 Your Agent May Misevolve；S-23 PACE；S-24 Self-Designed Evaluators and Warm Memory；S-25 Rehearse；S-26 Building effective agents；S-27 Practices for Governing Agentic AI Systems；S-28、S-29 綜述（地圖用）。S-04 已升 V2（QA 一審開頁）、作者 6 人，支撐 DP-02／DP-08 旁證；S-30 為旁證、無 DP 去處；二者皆不入 FR 追溯，本 PRD 不以其立論。
- **憲法**：`AISDLC_SDD/CLAUDE.md` Rule 9〈絕對禁令〉1～27 與〈核心機制速查〉R-9.20～9.37；根 `CLAUDE.md`〈守衛面准入〉〈鐵律一～七〉〈權限姿態〉〈三條改進軌道〉；`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`〈🏁〉；`docs/06_quality/FiveQuestion_Audit_Protocol/`（`README.md`、`severity.md`、`params.json`）。
- **既有機制與體例**：§11.1 各列座標；`docs/06_quality/AutoSDD_Defect_Log.md`；`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16；`docs/04_planning/AutoSDD_improving_115.md` §5.2、`AutoSDD_improving_116.md` §9。

### 13.3 變更記錄
| 日期 | 版本 | 變更內容 | 變更人 |
|------|------|---------|--------|
| 2026-10-19 | v0.1（Draft） | 初版：依掌舵者 T1 與 SOP 起草 Stage-1 上位規格（Brownfield） | SA 棒（Sonnet 5.5） |
| 2026-10-19 | v0.2（Draft） | SD／Architect 棒：填寫 §9（元件 C1～C15、ADR-SI-01～09、§9.0 查證 Q1～Q10、§9.7 審閱紀錄 28 處〔初版 27 處，#28 於 6c23495d 補入〕）；審閱並改動 §5／§6（AC 72→76：新增 AC-SI-08-4、10-3、12-4、20-4）；§5.1 補 JSONL 事件帳本載體與 RUN／ATT 記述 | SD 棒（Sonnet 5.5） |
| 2026-10-19 | v0.3（Draft） | 主控裁決（授權依據見附錄 C.2 表頭）：C.2 #5 修訂（OBS 維持 Markdown；ATT／PROP／DEC／APP／MEA／RUN 自 P1 起用 JSONL 事件帳本）、新增 #6～#9（SI 白名單自持、不加引擎閘、歸檔型提案豁免觸及比例、DEC 只認 `human` 出處） | 主控（代掌舵者決策） |
| 2026-10-19 | v0.4（Draft） | SA 連動修改（只動連動處）：§1.2／§11.1／§11.2 的 MEMORY.md 數字與「未查證→已查證」（§9.0 Q1、Q2、Q5）；§1.3 M1 補歷史基線 NOT-EVALUABLE 與前瞻窗（OBS-SI-027）；§3.3／§8.3 新增 ⏸ F-SI-105（OBS-SI-024）並補註 F-SI-103 的載體現況；§12.1 #6 回滾備註對齊 AC-SI-16-2；附錄 C.1 補帳本後續裁決至 OBS-SI-030；C.2 改寫為已裁決表（附錄 C 標題同步去掉「待裁決」）；§9.5 ADR-SI-02／03／06／07 的待裁決標記改為已裁決 | SA 棒（Sonnet 5.5） |
| 2026-10-19 | v0.4.1（Draft） | SD 殘留清理（commit 6c23495d）：待裁決標記與「建議補入」等現在式改寫清零、§13.1 回滾配方、AC-SI-28-2 改引註解字樣、AC-SI-09-2 歸檔型豁免與 §9.7 #28、檢核表現況 | SD 棒（續棒；主控提交） |
| 2026-10-19 | v0.5（Draft） | SA 修復棒（SCG-0 一審 FAIL，報告 `docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md`：P2＝3、P3＝18、P4＝7；非 §9 部分，§9 由 SD 修；AC 76→77）：F-01 patch 全路徑比對（新增 AC-SI-07-3；NFR-SI-02-1 錨定語意與 glob 補齊；AC-SI-07-1、11-1、14-1／14-2、§5.1.2、§3.2、詞彙表、附錄 B 同步）；F-02 M1 改 per-PROP 前後對照、NE 護欄量事件數（`W_EVT`）、補檢定力說明（§1.1、§1.3、AC-SI-22-1／22-2、23-1、§8.1 P3、§10.1）；F-03 遷移與原地改寫偵測以 `migration_base_sha` 對齊、更正機制統一為追加更正列（AC-SI-01-3／04-3、§8.1 P0、NFR-SI-03-2）；F-04 C.2 授權引句與範圍、C.1 補座標；F-05 harness 容量機制（§1.2、§11.1 列 13、G-SI-07、AC-SI-27-1／27-2）；F-07 AC-SI-12-4 錨定；F-08 AC-SI-17-2；F-09 邊界型（§2.1.1、NFR-SI-02-4、AC-SI-10-2）；F-10 AC-SI-02-1 擴及各類；F-12 AC-SI-23-1 M 類窗；F-13 M1 量法；F-14 M2／M3 降為資訊欄、M5 兩值並列；F-18 計數與變更記錄；F-19 附錄 A 強度欄同步 SOP II-5 一審後重判；F-20 §13.2 S-04；F-21 §3.2 與附錄 B（R-9.22）；順手 F-23（AC-SI-15-1）；P4 其餘（F-22、24～28）登記不改 | SA 棒（Sonnet 5.5） |
| 2026-10-19 | v0.6（Draft） | SD 修復棒（§9 同步 SA 修法 8 點：§9.2 Proposal／digest 改路徑集合＋`touched`＋`preimage`、§9.4 前置檢查比對全路徑＋逃逸判定＋負控清單＋`spec_body_globs` 機械化、§9.1 C1／C4／C5／C7／C8／C9、§9.3 `check` 自 `migration_base_sha` 起＋量測腳本 per-PROP、ADR-SI-05 基線窗、Q6 口徑對帳、§9.6 P0 (b)、§9.7 #29～#34；F-06 Q5 重排後反轉；F-11 新增 ADR-SI-10 事件帳本寫入鎖（獨佔建檔沿 `apply_lock`，不採 O_APPEND——R81 實測）；§7.2 轉交卡帶 PROP ID、`AskUserQuestion` 答覆不作 DEC；新增 §9.0 Q11／Q12）＋主控同步（§3.2 邊界型改 M＋P；AC-SI-07-3／NFR-SI-02-1 補 `casefold`；§7.2 補 rollback／unblock／resume 語法） | SD 棒（續棒）＋主控 |
| 2026-10-19 | v0.7（Draft） | SD 收尾棒（QA 二審 PASS 後的 P3 當輪改字＋P4 一筆；二審報告＝`docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` §6.3；SA 不再續棒、本棒可改任何章節；AC 數不變＝77）：F-29 過期待辦句改為現況（§9 引言、C8、§9.4、§9.7、§11.2 G-SI-11、§13.1、§5.1 引言、檢核表、頁尾）、「再現標記上線」錨＝`migration_base_sha` 那個 commit 的 committer 時間（UTC；主控裁決；§1.3〈M1 判定細則〉、ADR-SI-05、§9.3 量測腳本）；F-30 DEC 回覆語法統一為 §7.2 動詞表（AC-SI-12-1、12-4 ②、C8 只引用；`恢復` 綁 `RUN-SI-NNN`；補 `晉升 … 未驗採納`）；F-31 M1 窗 `pending`、晚到確認 `mea.amend`、駁回候選 `attr.reject`（AC-SI-23-1、23-2、24-1、06-2；§9.2、§9.3）；F-32 M1 六灰區裁決（§1.3、§1.1、§8.1；M5 只報值不判趨勢）；F-33 真人發言兩種載體（`queued_command` 附件；AC-SI-12-4 ①③、C8、Q11 普查 24.7%）；F-34 `dec` 回查（AC-SI-12-4 ⑤、16-1、08-4；§9.3 `check`／`promote`；§2.1.1 矩陣；§9.4 誠實劃界）；F-35 的 SD 部分（`check` 拒欄內控制字元）；F-36 C.1 不複寫累計次數；§9.7 新增 #35～#40；P4 F-37～F-41 登記不改 | SD 棒（收尾） |
| 2026-10-19 | v0.8（Draft） | SA 棒 T1 修訂（掌舵者 2026-10-19 20:21 +08:00 四問＋授權句，sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13；輸入快照 HEAD＝`d4b7868f`；主控判讀與 D-1～D-6 裁決＝附錄 C.1、C.2 #10～#15；本列於 21:04 +08:00 現查時刻寫入）：**新增 5 條 FR 與 22 條 AC（77→99）**——FR-SI-30 研究掃描（限定來源、增量、有界、只產候選；P1）、31 模組體檢（P1）、32 Console 唯讀鏡像（P1b）、33 Console 決定載體（P2b；驗證設計 ⚖ 交 Architect 棒）、34 根層模組落點鎖（P1）；§3.2 運轉期 Web 條改寫（開放式搜尋仍範圍外）、§3.3／§8.3 F-SI-101 再開；同步 §1.3.1、§2.1／§2.1.1、§3.1、§4.1、§5（編號注意、⚖ 圖例、§5.1.1～5.1.3）、§6（NFR-SI-01／02-4／06-6／07-1／07-4／09-4）、§7.2、§8.1（P1 出口加 (e)～(h)、新增 P1b／P2b 列）、§9（C16～C19、事件詞彙與 `carrier`、動詞表、Console 端點、研究者與 Console 面、ADR-SI-11／12、§9.6）、§10（加 2 列風險）、§11、§12、§13.1、§14、附錄 A／B／C；凡改動既有敘述處皆以〔訂正〕保留原文；M1～M5 指標列與〈M1 判定細則〉未動（`metrics.md` 逐字副本仍相符）、NFR-SI-02-1 實體 glob 行未動。**行號座標偏移聲明**：P0 TCS、RTM、SCG 審查報告與觀察帳本以 PRD 行號為座標（例 `PRD:208`、`PRD:413～415`、`PRD:635`、`PRD:646`），本修訂在這些座標之前插入多行，座標全數偏移；P0 已 RELEASE、各文件凍結不改，重驗請以「節＋引文」定位，不以行號 | SA 棒（Sonnet 5.5） |
| 2026-10-19 | v0.9（Draft） | SD／Architect 棒技術定稿（輸入快照＝PRD 修訂 commit `c2aee850`；主控對 v0.8 各 ⚖ 的裁決＝附錄 C.2 #16）：**§9 全節定稿**——〈C4 套件檔案表〉（16 新檔、能力類別 `ro`／`rw`／`net`）、C16～C19 落點與判準（含〈C18 檔名表〉AgentConsole 三層）、§9.2〈事件欄位表〉／`research_sources.json` 格式／`export` 輸出 schema／鐵律三三列、§9.3 動詞旗標與 rc 通則／Bridge 子行程形態、§9.4〈能力登記與純度判準〉與研究者、Console 面改寫、ADR-SI-03′（Console 決定載體裁決；兩點待主控確認）／11（D-1′）／12、§9.6 鍵與依賴、§9.7 可行性核對 FC-a～FC-f 與審閱紀錄 #41 起；D-1′ 連動改動 AC-SI-30-1～30-5、NFR-SI-01／02-4／07-4／09-4 與 §2.1／§2.1.1／§3.2／§10.1／§12.1／§13.1／附錄 B／C；AC-SI-31-1、32-1／32-3／32-5、33-1／33-2、34 的最小改寫；AC 數不變＝99；§9.7 #1～#40 與 §9.0 Q1～Q12 逐字搬至 `docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` 附錄 SD；M1～M5 指標列與〈M1 判定細則〉、NFR-SI-02-1 的 glob 清單行未動（兩處之上各加一行機械消費警語註解） | SD／Architect 棒（Sonnet 5.5） |

## 🔗 14. 文檔追蹤鏈 (Traceability)
### 上游文檔
- **需求來源（掌舵者 T1，2026-10-18，逐字；本 PRD 立案的上游需求，T1 修訂見下一條）**〔訂正（T1 修訂，v0.8）：原文「本 PRD 的唯一上游需求」〕：
  > 請協助設計自我進化機制 ==> SelfImproving.prd:
  > 1.請參考OPENAI/Claude Code等網路前言論文==> 有關自我進化機制論文, 收集有關的有用且重要資料進行分析研究, 來進行設計! 並統整一個研究方法論SOP
  > 2.依照第一項方法論SOP, 進行規劃，分析，設計，實作，與獨立審查, 完成此模組的PRD!
  > 3.在進行任何開發過程, 若有發現相關流程不適當或BUG, 請隨時記錄情境與相關資訊, 記錄成帳本, 以便日後進行自我精進!
  > 4.有必要則會隨時自我精進演化與除Bugs
  > 5.將SelfImproving.prd寫入docs\01_requirements
- **T1 修訂（掌舵者，2026-10-19 20:21 +08:00，逐字；sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13，JSON 解析 `type=user`、`origin.kind=human`；座標由主控親驗，SA 棒重驗該行的類型、出處與時間戳 `2026-10-19T12:21:32.705Z`；同則訊息另含與本 PRD 無關的 IDE 錯誤清單，不入此處）**：前言
  > 以AISDLC的程序(請Architect/SA/SD/Developer考慮如何規劃設計實作獨立審查?省去非必要文件，只留一定需要文件)，幫我解決以下問題：
  > 因為Fable Token實在花太兇(Fable當用則用)，請派Subagent時, 使用Sonnet 5！你當主控Agent還是使用Fable 5.1

  四個問題：
  > 1.請驗證自我精進演化機制是否完備==> SelfImproving.prd:
  >   a.可以自行檢討AutoClaude, AISDLC_SDD, AgentConsole,SelfImproving等現有模組是否還有需要改進的地方與BUG!
  >   b.如何適當啟動自行精進演化機制? b1.如每次研究外部網路(OPENAI/Claude Code等)前沿技術SOP(每次啟動驗進SOP,取得外部最新資訊),b2.如何融入現有系統分析, b3.如何實作? b4.如何驗證, b5.如何上線等==> 請Architect/SA/SD/Developer考慮如何規劃設計實作獨立審查
  >   c.自我精進帳本系統化統一管理, 可以由AgentConsole UI介面管理
  > 2.請規劃日後有新模組產生時, 可以有系統, 有組織的規劃整體專案系統目錄, 不要到處散落, 請寫在CLAUDE.md及專案規格相關文件中落實! 記住此點
  > 3.若SelfImproving.prd各方驗證都沒問題, 即可凍結實作!
  > 4.收輪最後, 請一併將暫存檔或測試相關檔案刪除!

  授權句：
  > 以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策
  > 若需要請派出Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作，與獨立審查,請確認以上功能都已經完備！
- **逐點對映**：第 1 點→SOP，附錄 A 以 DP-01～12 承接；第 2 點→本 PRD（SA）→SD 補 §9→QA 做 SCG-0 獨立審查→實作輪依 §8；第 3 點→FR-SI-01、02、29 與觀察帳本；第 4 點→全迴圈（§3.1）、事件驅動啟動（FR-SI-03）、Bug 升 DEF（FR-SI-04）；第 5 點→本檔（檔名依 OBS-SI-001 裁決）。T1 修訂四問的逐點對映見附錄 C.1。
- **研究方法論**：SOP（DP-01～12、風險登記表、再查證觸發）。

### 下游文檔
- **FRD／TCS／SRD**：於實作輪再產（非缺漏）；FRD 以 FR-SI-NN 為追溯鍵。**T1 修訂後的文件集（C.2 #15，T1 前言「省去非必要文件，只留一定需要文件」）**：自 v0.8 起不另產 FRD／SRD、不開獨立 ADR 檔（ADR-SI-11、12 只在 §9.5 加列）；每個實作鍵留 TCS、審查報告、RTM 各一份（主控派）〔訂正（T1 修訂，v0.8）：原文「FRD／TCS／SRD：於實作輪再產（非缺漏）；FRD 以 FR-SI-NN 為追溯鍵」中的 FRD、SRD 部分〕。
- **觀察帳本**：`docs/06_quality/SelfImproving_Observation_Ledger.md`（P0 載體，欄位依 §5.1.1 同步）。
- **RTM**：FR-SI-NN → AC-SI-NN-Y → TC，於實作輪產出。
- **追蹤鏈範例**：`DP-04 → FR-SI-12 → AC-SI-12-1 → （FRD BR）→ TCS → TC`；`T1 第 3 點 → FR-SI-29 → AC-SI-29-1 → OBS-SI-NNN → DEF-<id>`。

## 附錄 A　追溯矩陣（DP → FR-SI → 既有機制／新建）
每條 FR 的 DP／既有機制追溯見 §5.2 各條「追溯」行；FR-SI-03、04、29 以既有機制為主（C-12、缺陷帳本治理、T1 原文第 3、4 點）。強度與來源取自 SOP II-5：強度欄為**一審後重判值**（強→中：DP-01、04、05、06、09、10，標「一審後重判；原強」；其餘維持），組別與理由見 SOP II-5〈強度重判表〉，本表不複寫、不引行號；SOP 該表「PR」欄由本表「FR-SI」欄填寫（PR＝FR-SI-NN）。

| DP | 原則（摘自 SOP） | 主要來源 | 強度 | FR-SI | 既有機制／新建 |
|----|-----------------|---------|------|-------|---------------|
| DP-01 | 外部可驗證訊號優先於自評，自評只作輔助 | S-03、S-26、S-24、S-11、S-06、S-17 | 中（一審後重判；原強） | 18、19 | 有（`evaluator_command`、R-9.27、鐵律四）；通用化到 M／D 類＝新建 |
| DP-02 | 改進落成人類可讀、可版本化、可刪除的工件，不碰權重 | S-05、S-06、S-08、S-09、S-16、S-18 | 強 | 08、16、25 | 有（KB、偏好、`MEMORY.md`、skills、git）→ 接既有 |
| DP-03 | 增量 delta 與逐條策展，禁整份重寫，容量有界 | S-06、S-07、S-08、S-12 | 中 | 09、25、27 | 部分（preference 10 鍵、`_MAX_ENTRIES`、`NoBigBangValueRewrite`）；Playbook／規則層策展＝新建 |
| DP-04 | 提案—驗證—採納三段分離；採納只經人工 K=1、可回滾 | S-17、S-19、S-27、S-26、S-23、S-08 | 中（一審後重判；原強） | 08、12～16、23、26、28 | 有（`evolution_plugin` NO-OP、`translation_learner`、R-9.22、Console 簽核）→ 接既有；統一閘＝新建 |
| DP-05 | 評估器對生成器隔離；評估器不得由被評估者自行發明或修改 | S-17、S-20、S-11、S-21、S-24 | 中（一審後重判；原強） | 11、18、20 | 部分（SDD R-9.27～9.32 有；AutoClaude／根層無）→ 新建（通用化） |
| DP-06 | 迴圈有界，且有邊際報酬遞減的停止規則 | S-25、S-17、S-26、S-10、S-23 | 中（一審後重判；原強） | 03、10、17、24 | 有（`SDD_*_BUDGET`、Gap-042／048、ESCALATION、額度守衛）；停止規則（劣化暫停）＝新建 |
| DP-07 | 保留譜系與回滾；探索型改進保留多分支 | S-17、S-18、S-19、S-08（S-16 同組） | 中 | 08、15、16 | 有（git、Copy-on-Evolve、`EvolutionMetadata`）；「探索型多分支」不在 MVP |
| DP-08 | 提案以真實失敗軌跡與帳本列為輸入（抽象化、帶結果標籤） | S-01、S-14、S-06、S-05 | 強 | 01、02、04、05、09、29 | 有（`translation_learner`、KB、缺陷帳本、觀察帳本）→ 接既有 |
| DP-09 | 記憶只存帶真實結果標籤的條目，可審計並防毒化 | S-11、S-08、S-13、S-22、S-25 | 中（一審後重判；原強） | 02、09、27 | 部分（KB 結果標籤、`MEMORY.md` 可人審）；來源過濾＝新建 |
| DP-10 | 成效以真實症狀驗收，不以自評分數、審查產出數、貪婪接受當成功 | S-20、S-21、S-17、S-11（機制 S-23） | 中（一審後重判；原強） | 06、13、14、19、21、22、23 | 部分（症狀閘、再開症狀）；指標量測腳本＝新建 |
| DP-11 | 自我進化本身要做安全評估；新 skill／hook／工具啟用前掃描並人審；治理檔不在可進化面 | S-22、S-09、S-10、S-13、S-17、S-27 | 強 | 07、11、15；NFR-SI-02 | 有（Rule 9、hooks deny、治理檔唯讀守衛、守衛面准入）→ 接既有；掃描流程＝轉交（登記） |
| DP-12 | harness 可成為優化對象，但一律 diff 提案＋凍結快照評估後才活化；探索／評估流程本身不可改 | S-16、S-19、S-14、S-29、S-15 | 中 | 07、11、28、29 | 部分（INJECT_STEP／SPLIT_STEP／REVISE_EVALUATOR 提案；無 harness 整體 diff 管線）→ MVP 只落地「評估與迴圈自身不可改」半條；harness 整體 diff 提案＝⏸ F-SI-104 |

**T1 修訂新增 FR（FR-SI-30～34）的追溯**（v0.8；上表 DP 列的 FR-SI 欄為立案時定稿、不回改，新 FR 的 DP 對映以本表為準；每條新 FR 另有 §5.2 的「追溯」行）

| FR-SI | 追溯（DP／T1／帳本） | 既有機制／新建 | 階段與鍵 |
|-------|---------------------|---------------|---------|
| 30 研究掃描 | DP-09（記憶與外部內容只存帶結果標籤、可審計並防毒化）、DP-06（迴圈有界）＋T1 2026-10-19 問題 1b1 | 有（研究方法論 SOP；FR-SI-02 外部衍生隔離）→接既有；來源表、增量 digest、研究事件＝新建 | P1；`monorepo-si-p1-propose` |
| 31 模組體檢 | DP-08（提案以真實失敗軌跡與帳本列為輸入）＋T1 問題 1a | 有（`misstep_attribution`、`audit_session`、缺陷帳本；皆唯讀）→接既有；`scan` 與體檢任務書＝新建 | P1；`monorepo-si-p1-propose` |
| 32 Console 唯讀鏡像 | DP-04（採納只經人工 K=1；顯示面不繞過）＋T1 問題 1c | 有（Console 既有簽核硬閘、Bridge 契約）→接既有；`export`、端點、頁＝新建 | P1b；`agentconsole-si-mirror`（`export` 半＝`monorepo-si-p1-propose` 末棒，附錄 C.2 #12） |
| 33 Console 決定載體 | DP-04＋T1 問題 1c；ADR-SI-03 再開 | 同上 | P2b；`agentconsole-si-decide` |
| 34 根層模組落點鎖 | T1 2026-10-19 問題 2 與落點指令（SSOT 立案欄，sid `f3ead132-29b1-418c-97d9-35868ab11c70`）＋OBS-SI-105 | 有（落點規範 SSOT）→接既有；機械鎖＝新建 | P1；`monorepo-si-p1-propose` |

## 附錄 B　憲法對照表（被觸及的 Rule 9 禁令與守衛面規則 → 本 PRD 如何遵守）
| 規則（座標） | 被觸及原因 | 本 PRD 如何遵守 |
|-------------|-----------|----------------|
| 禁令 1、3（繞過 `FSMRuntime` 讀寫 FSM-STATE；IMPLEMENTATION 期間寫 `docs/01~03`；R-9.6） | 迴圈讀 FSM 狀態；D／R 類目標可能落在 `docs/01～03` | 只讀 `show`、寫入一律經 CLI、不新增 FSM 狀態（§12 #4）；不繞過 R-9.6 擋寫，改由符合條件的視窗處理或轉交（AC-SI-15-3） |
| 禁令 4、5、6、7（retry 超限；Token ≥95% 仍工作；ESCALATION 後自動恢復；structural 強行 auto-recovery） | 提案修訂、驗證重跑、扇出耗額度、停機 | `MAX_REVISIONS`、重跑 ≤ 2、超界升級人工（NFR-SI-01；AC-SI-10-2、10-3、17-1）；扇出前 `--pace`（NFR-SI-07）；ESCALATION／SUSPENDED 後僅人工恢復（AC-SI-17-2、24-1） |
| 禁令 8、9、10（`_HAPPY_PATH`／TLA+；觀測態入 Terminals；proposed／external 規則阻塞 SCG） | 是否新增狀態；R 類草案 | 不新增 FSM 狀態、PROP 狀態機只在帳本欄位（不觸 `_HAPPY_PATH`，N/A）；AC-SI-08-3：`proposed` 不阻塞 SCG |
| 禁令 11、12、13（自動退役 active 規則；自動套用 spec patch；planner 自動選目標、localizer 自動改 spec） | 退役提案；R／D 類 diff；歸因會指向 spec | FR-SI-25（系統只提議、SDD 規則退役必經 `set_maturity`）；FR-SI-12、16（K=1、晉升為人工動作；AC-SI-12-4 引言驗證）；FR-SI-05（歸因只指向座標、不改檔）；AC-SI-07-3（patch 全部路徑逐一比對不可進化面）。**R-9.22**（SPEC-PATCH 草案為 proposed、絕不自動套用、經 HUMAN_PENDING）：本迴圈的 K=1 晉升是人工動作而非自動套用，故不違反；但 K=1 不是 FSM 的 HUMAN_PENDING 態，所以 D 類不得以 K=1 直接改 `docs/01～03` 規格文件本體，規格變更仍走 SPEC-PATCH＋HUMAN_PENDING（§3.2；SOP C-02） |
| 禁令 14、15、16（繞過 `meta_halt_monitor`／無 capability-delta 重學／重放命中率自動 approve；組合排程與最佳化搜尋無界） | 退役與再採納、重放驗證、候選生成 | FR-SI-26；AC-SI-19-3；不做組合最佳化搜尋、候選數上限 FR-SI-10（15、16 其餘 N/A） |
| 禁令 17～25（自評放水、tuner 讀寫 held-out；維度／詞彙／算子／字母／深度／互遞迴自我發明；末項：未獲對抗分離證明即採納自我發明評估器） | 評估、指標與提案類別邊界 | FR-SI-18、20（含 AC-SI-20-4 暴露偵測）；NFR-SI-05；§3.2 範圍外；FR-SI-11（評估器變更不受理）；AC-SI-29-2（`loop-self` 轉交） |
| 禁令 26、27（接地 fail-closed、沙箱 hang 收 verdict、外聯須 OPEN-X.x；視覺化自動 signoff／簡化呈現繞過） | 沙盒驗證、量不到、提案卡呈現 | AC-SI-19-2、17-1；NFR-SI-02-4、09-1；FR-SI-14（卡面確定性轉換、反解析比對） |
| 守衛面准入（R197：量、不挖）、〈權限姿態〉（`.claude/**` 受保護路徑；不改派子代理繞過）、PRD v2.1 §15.5 紅線 10、`severity.md`〈暴露度〉 | 不可進化面、轉交與沙盒目標、無人值守、守衛面觀察的嚴重度 | FR-SI-01（`暴露` 欄）、07（含 AC-SI-07-3）；NFR-SI-02-1～02-5；AC-SI-15-3；本 PRD 零新增守衛碼（增補僅見下列 FR-SI-34 落點鎖列；§9.4 能力登記測試是 P0 純度鎖的細化，§9.7 #47），無暴露證據一律理論洞 P4 |
| 鐵律四（宣稱附當回合輸出） | 驗證與指標宣稱 | FR-SI-21；AC-SI-08-4、12-4 |
| 鐵律一～三、五、六（Windows 載具、絕對路徑、跨平台自問、毀滅性 git、壞等待形態） | 新腳本與欄位、沙盒建立／清理、背景任務 | NFR-SI-06；AC-SI-15-2 |
| 鐵律七（並行派工前切鎖持有面；四點檢查表） | 角色分離與帳本寫入 | FR-SI-18（複審唯讀）；角色矩陣（帳本單一窗口）；附錄 C.1 串行裁決 |
| 三條改進軌道／範本〈🏁〉T1～T4 | 迴圈啟動與是否開輪 | FR-SI-03；附錄 C.1（不開 117） |
| 根 `CLAUDE.md` 12-Rule Rule 5／6／12 | 確定性轉換、預算、fail loud | FR-SI-22；NFR-SI-07-3；NFR-SI-09-1 |
| AgentConsole 人工 signoff 硬閘、FSM 只讀（C-15） | Console 接點（P1b 唯讀鏡像、P2b 決定載體；原標 post-MVP） | FR-SI-12、32、33；§12 #5、#12 |
| 禁令 26（外聯須 OPEN-X.x；R-9.36 字面針對具身接地活體 canary 的 HTTP 外聯，OPEN-10.6）、NFR-SI-02-4 | `si research --fetch` 以 HTTP GET 外聯（FR-SI-30；本 PRD 唯一的外聯例外） | 事前登記載體＝研究來源表 `research_sources.json`（僅 T1 增減，NFR-SI-02-1 (iii) 既有 glob）；研究者無任何 Web 工具；外聯只在 `fetch.py`、對象限來源表；產物只入帳為 OBS 候選（AC-SI-02-1、30-4）。誠實劃界：禁令 26 字面是 SDD 元迴圈的 OPEN-X.x 登記機制，本迴圈取其精神（外聯事前登記、可稽核）；是否另須在 SDD 側登記 OPEN-X.x，本稿未查證，交 SCG-0（QA）審（主控 ⚖10 裁決：來源表＝事前登記載體，附錄 C.2 #16） |
| 守衛面准入（R197：量、不挖）— FR-SI-34 落點鎖 | 新增 `tools/tests/test_root_module_layout.py` | 該測試不在守衛面清單（守衛面＝`.claude/hooks/**`、`.claude/settings*.json`、根 `CLAUDE.md`〈守衛面准入〉指定的 `tools/lib/` 檔、`tools/session_resume_planner.py`），不是 hook、不碰 `.claude/**`；驅動來源是掌舵者 T1 直接指令（2026-10-19 問題 2 與落點指令）與 OBS-SI-105，不是審查者對守衛面的對抗搜尋；新增付重釘稅（護欄層行數棘輪、CI paths，同一個 commit）。誠實劃界：形態判準（AC-SI-34-1～34-4 各自標明看不見什麼） |
| AgentConsole 鐵律 7（不准動根層 `tools/`、`.claude/`、`CLAUDE.md`）；根 `CLAUDE.md`〈根層模組落點〉 | `export` 住根層、Console 只消費 | `export` 由根層鍵交付；AgentConsole 側只經子行程呼叫、不 import `tools/lib`（AC-SI-32-2）；AgentConsole 子專案內的模組落點依其 Architecture §3，不往根層放（SSOT §2 末段） |

## 附錄 C　主控裁決
### C.1 主控裁決（流程類；授權範圍與限制見 C.2 表頭；掌舵者可隨時以 T1 推翻）
| 編號 | 裁決 | 座標 |
|------|------|------|
| OBS-SI-001 | 檔名用 repo 慣例 `docs/01_requirements/SelfImproving_PRD.md`（T1 原文 `SelfImproving.prd` 不合 `*_PRD.md` 慣例，文件工具鏈與 docs 守門只認 `.md`）；回報掌舵者 | 觀察帳本 OBS-SI-001 |
| OBS-SI-002 | 額度守衛 `--pace` 回 cap=1，四方專家串行：研究員→SA→SD／Architect→QA；每棒交卷後主控親驗再派下一棒 | 觀察帳本 OBS-SI-002 |
| OBS-SI-003 | 延後；再開症狀：第二次有人為探針手改三件組而寫錯真狀態目錄 | 觀察帳本 OBS-SI-003 |
| OBS-SI-004 | 任務書一律改「文字交卷」，不再要求子代理寫報告檔 | 觀察帳本 OBS-SI-004 |
| 不開 `AutoSDD_improving_117` | 掌舵者要求省去非必要文件（原句「省去非必要文件，只留一定需要文件」，sid f3ead132-29b1-418c-97d9-35868ab11c70 line 13）；本 PRD 本身是驅動器（不複製範本、不產四件套；軌道① 仍依範本〈🏁〉T1～T4 休眠） | 根 `CLAUDE.md`〈三條改進軌道〉；`AutoSDD_Iteration_Prompt_Template.md`〈🏁〉 |
| T1 修訂（2026-10-19，四問＋授權句；原文見 §14） | 主控判讀（掌舵者可反駁）：①(a) 自行檢討四模組→原只有被動擷取，缺口→FR-SI-31；①(b1) 每次啟動取外部最新資訊→與原 §3.2 的 ❌ 衝突，T1 為掌舵者立案（研究方法論 SOP S7 的 T-6 實例）→FR-SI-30，§3.2 該條改寫、開放式搜尋仍範圍外；①(b2～b5) 融入分析／實作／驗證／上線→已由 FG-B～FG-H（P1～P3）涵蓋，本輪只補每一步的機械入口（下表）、不新增需求；①(c) 帳本由 Console 管理→F-SI-101 再開症狀命中→FR-SI-32（P1b）、FR-SI-33（P2b）；②新模組目錄規範→已落地（SSOT、根 `CLAUDE.md`〈根層模組落點〉、§9.1 模組落點表），缺機械鎖（OBS-SI-105）→FR-SI-34；③各方驗證沒問題即可凍結→掌舵者已預先核准，由主控依該座標執行 Stage-1 重凍，不屬本 PRD 內容；④收輪清理暫存檔→主控收尾。不開 `AutoSDD_improving_117`（沿上列）；文件最小化＝C.2 #15；前言「Fable 當用則用、派 Subagent 用 Sonnet 5」→NFR-SI-07-1 | sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13（JSON 解析 `type=user`、`origin.kind=human`，主控親驗） |

帳本後續裁決（快照至 OBS-SI-030；只列編號與一句，細節以帳本為準）：OBS-SI-006（任務書一次一題）、OBS-SI-007（Glob 任務書寫法改「path 指到目錄＋純檔名 pattern」，再開症狀已命中、升 P3）、OBS-SI-008（PDF 走本機 `python -I` 粗抽、大頁改抓摘要頁）、OBS-SI-011（鐵律一優先於系統提示的 Bash 偏好；各棒復發；累計次數見帳本現查，本檔不複寫計數）、OBS-SI-013（時間欄寫實際日期、任務書改寫「起算日」）、OBS-SI-015（自 SD 棒起任務書標明輸入快照的 HEAD，棒內主控不動受審檔）、OBS-SI-016（記憶索引人工歸檔 22,755→15,558 bytes，PROP-SI-003 的手動先例、不經閘）、OBS-SI-018（＝C.2 #4）、OBS-SI-019（表頭宣告「本機 +08:00」即視為帶 offset、區間允許）、OBS-SI-021（＝C.2 #3）、OBS-SI-022（＝C.2 #7）、OBS-SI-029（scratch 腳本自行 `reconfigure` UTF-8；repo 內工具走 `init_utf8_streams`）、OBS-SI-030（記憶索引常青兩節移前、輪次列表殿後，主控已重排）。

**T1 修訂（2026-10-19）四問→FR 對映與 b2～b5 的機械入口**（每一步的動詞、事件、閘一次列清；動詞與事件的定義以 §9.2／§9.3 為準）

| T1 問 | 結論 | 對映 FR（階段） | 機械入口（動詞／事件／閘） |
|---|---|---|---|
| 1a 自行檢討四模組 | 原只有被動擷取，缺口 | FR-SI-31（P1） | `si scan`（唯讀）＋唯讀體檢子代理→OBS 候選；閘＝主控單窗口入帳、`si check` |
| 1b1 每次啟動取外部最新資訊 | 與原 §3.2 ❌ 衝突；改寫為限定來源增量掃描 | FR-SI-30（P1） | `si research --fetch`／`--skip`→事件 `research.scan`／`research.skip`；閘＝`prop-new` 前置檢查＋`check` 重放（AC-SI-30-1） |
| 1b2 融入現有系統分析 | 已涵蓋 | FR-SI-05、06、07（P1） | `attr`／`attr-confirm`→事件 `attr`／`attr.confirm`；閘＝確認者≠提出者、不可進化面轉交 |
| 1b3 如何實作 | 已涵蓋 | FR-SI-08～11、15（P1／P2） | `prop-new`／`prop-revise`→事件 `prop`；`sandbox`→`app.sandbox`；閘＝前置檢查（AC-SI-07-3）、K=1 |
| 1b4 如何驗證 | 已涵蓋 | FR-SI-18～21（P2） | `heldout-freeze`／`verify`→事件 `heldout.freeze`／`app.verify`；閘＝審查者≠提案者、RED／GREEN／突變、三態 |
| 1b5 如何上線 | 已涵蓋 | FR-SI-12、16、22～24（P2／P3） | `decide`／`promote`→事件 `dec`／`app.promote`；閘＝DEC 引言回查＋digest；上線後 `mea.*` 量測窗 |
| 1c 帳本由 Console 管理 | F-SI-101 再開 | FR-SI-32（P1b）、FR-SI-33（P2b） | `export`→Bridge `/si/*`；P2b `decide --carrier console`；閘＝差分／唯讀／fail-loud、簽核硬閘 |
| 2 新模組目錄規範 | 已落地；缺機械鎖 | FR-SI-34（P1） | `tools/tests/test_root_module_layout.py`；閘＝根層全套 unittest |
| 3 驗證沒問題即可凍結 | 掌舵者已預先核准 | —（不屬本 PRD 內容） | FSM 重凍（主控）；approver 依預先核准座標 |
| 4 收輪清理暫存檔 | 主控收尾 | — | — |

### C.2 已裁決（主控代決 2026-10-19；授權範圍與限制見下）
主控代決（2026-10-19）；授權依據＝掌舵者於本 session 第一則訊息（2026-10-18 21:03 +08:00，sid f3ead132-29b1-418c-97d9-35868ab11c70 line 13）原文：『以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策』。該句的『以上』指該則訊息的四個問題；SelfImproving T1（同 sid line 901，22:40）未重述此句，故本表 #1～#9 是主控對該授權的延伸解釋，凍結核准時由掌舵者以互動選項逐項確認、可推翻；凍結核准本身不代決。**補記（2026-10-19，QA 一審 F-04 之後）**：掌舵者於本輪重述授權（同 sid line 2476，10:21 +08:00；初稿誤引 assistant 空記錄 line 2493，SA 起草 P0 TCS 時發現、主控以 JSON 解析親驗 `origin.kind=="human"` 後訂正，更正列 OBS-SI-043）原文：『以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案(不用考量成本)，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策』，並預先核准凍結（同 sid line 2525，10:24 +08:00；初稿誤引 line 2536）原文：『真正需要你本人的只剩凍結核准 ==> 現在先授權核准! (避免不在機器旁)』⇒ #1～#9 的授權出處補為本輪原文；Stage-1 凍結以此預先核准執行、`--approver` 引該座標，不再互動確認（首次凍結 commit 8d2d5ef0 的 approver 字串引的是誤座標 line 2536，訂正後經 SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING 重凍）；掌舵者開 P0 的指示在同 sid line 2581（「了解，凍結後接著開 P0 實作」）；掌舵者仍可隨時以 T1 推翻任一項。**補記（T1 修訂，2026-10-19 20:21 +08:00）**：本表 #10～#15 的授權依據＝掌舵者同則訊息（sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13；JSON 解析 `type=user`、`origin.kind=human`；原文見 §14）的授權句『以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策』與『若需要請派出Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作，與獨立審查,請確認以上功能都已經完備！』；其「以上」指該則訊息的四個問題。#10～#15 仍是主控對該授權的代決，掌舵者可隨時以 T1 推翻；標 ⚖ 者另待 Architect 棒或主控再決〔v0.9：均已由 #16 裁決，唯 ADR-SI-03′ 兩點待主控確認〕。問題 3 的凍結已由掌舵者在同則訊息預先核准（『若SelfImproving.prd各方驗證都沒問題, 即可凍結實作!』），凍結的執行不屬本表、不代決。

| # | 事項（原為待裁決） | 裁決（#1～#4＝SA 建議預設值；#5 起見各列） | 影響 |
|---|-----------|-----------|------|
| 1 | 晉升形態：核准（綁 digest）後，驗證 PASS 仍須掌舵者再執行一次「晉升」動作（兩次人工接觸，第二次只確認）是否可接受？ | 接受（核准一次、晉升確認一次；晉升前顯示驗證摘要） | FR-SI-12、16 |
| 2 | 是否開放主控在掌舵者書面授權下代為核准？ | MVP 不開放；日後若開放，僅限 D 類且逐次書面授權，M／P／R 與轉交一律掌舵者本人（⏸ F-SI-102） | FR-SI-12 |
| 3 | DEF 帳本是否加復發標記（現象欄 `reopens:DEF-xxx` 文字慣例，或新增欄位／時分精度）以使 M1～M3 可機械量測？ | 只在 OBS 側新增；DEF 側用現象欄文字慣例由量測腳本解析、不改表頭；改表頭須另經掌舵者核准 | FR-SI-01、06、22 |
| 4 | `require_evolution_signoff` 預設方向：維持 False＋文件改述，或改 True（fail-closed）？ | 維持 False＋補可重跑靜態檢查＋文件改述（零退化）；改 True 會改變舊路徑行為，僅在掌舵者要求引擎層預設拒絕時採 | FR-SI-28 |
| 5 | MVP 介面採 CLI 文字提案卡（Console 卡 ⏸），PROP／DEC 載體 P1 先用 Markdown 表（與觀察帳本同型），P2 前由 SD 評估機器可讀？ | **修訂**（原裁決「同意」；採 SD 棒 ADR-SI-02 建議，其中「P1 先用 Markdown 表」字面退役）：MVP 介面維持 CLI 文字提案卡（Console 卡 ⏸）；OBS 觀察帳本維持 Markdown 表；ATT／PROP／DEC／APP／MEA／RUN 自 P1 起用 JSONL 事件帳本，一律由 CLI 寫入、LLM 不手寫 JSON。理由：狀態折疊、digest、冷卻、M1～M5 都要結構化解析 | §7、§5.1、§9.2、ADR-SI-02 |
| 6 | FR-SI-28 落點（ADR-SI-07 前半）：SI 對引擎碼的侵入白名單由誰定、是否需修訂 ADR-XPLAT-016 §11？ | SI 白名單自持：引擎源碼零改動；僅 `AutoClaude/tests/contract/` 新增 1 檔；`AutoClaude/CLAUDE.md`:191 改述走一般開發流程；不修訂 ADR-XPLAT-016 §11 | FR-SI-28、§9.4、ADR-SI-07 |
| 7 | FR-SI-28 引擎層（ADR-SI-07 後半）：是否在 `AutoResumeService` 加演化重載的 signoff 閘？ | 不在引擎加閘；以契約測試釘「演化重載分支無生產者」（座標：`AutoClaude/autoclaude/core/services/auto_resume.py`:255–272）。再開症狀：出現演化重載的生產者（OBS-SI-010；AC-SI-28-3） | AC-SI-28-1 ③、28-3 |
| 8 | AC-SI-09-2 的觸及比例上限（`MAX_TOUCH_RATIO`）是否適用「歸檔型」提案（ADR-SI-06）？ | 豁免：逐字搬移、零內容修改、一個反向 patch 可回滾的「歸檔型」提案不受 `MAX_TOUCH_RATIO` 約束，改以每卡條目數上限約束；上限初值 50（無先例、未校準） | AC-SI-09-2、FR-SI-27、ADR-SI-06 |
| 9 | DEC（人工決定）的出處驗證（ADR-SI-03）：逐字稿 `origin.kind` 哪些算「人工」？出處欄位缺席怎麼處置？ | DEC 只認逐字稿的真人文字，排除 `sdk`：載體 (i) `type:"user"` 且 `origin.kind=="human"`、(ii) `queued_command` 附件且 `attachment.origin.kind=="human"`（二審 F-33 補，本機 24.7% 真人發言走附件載體）；出處欄位缺席＝判 NE、不記 DEC。代價：他機重驗＝NE；欄位為觀察所得、非官方契約，照寫 | AC-SI-12-4、FR-SI-16、ADR-SI-03 |
| 10 | 研究者與限定來源增量掃描：每次啟動取得外部最新資訊（T1 1b1；D-1），與 §3.2 原禁運轉期 Web 衝突 | 採「限定來源＋增量＋只產候選」：新角色研究者（Sonnet；工具 Read／Grep／Glob／WebFetch；不准 WebSearch／Write／Edit／派子代理）；每個運轉，`run.open` 之後、任何 `prop` 之前恰有一筆 `research.scan` 或 `research.skip`（`prop-new` 拒收、`check` 重放紅）；來源只准來自 `docs/06_quality/SelfImproving_Protocol/research_sources.json`（不可進化面、僅 T1 增減；初始 7 筆提案、URL 皆未驗）；`si research --record --dir` 由 CLI 對檔案自算 sha256、與上一筆同 `id` 比對得 `changed`，**CLI 不連網**（P0 TCS `AC-030-2` 純度不變）；`research.skip` 的 `reason`∈{`quota-band`、`offline`、`helmsman`}；產物只能是 OBS 候選（`外部衍生=是; src=<id>`，主控入帳）、不得直接成為 PROP，FR-SI-02 照舊；預算 `research_fetch_max`＝8（無先例）、`research_bytes_max`＝262144（每來源）登記 `params.json`；研究方法論 SOP 的深度重跑（S1～S8）維持 S7 症狀驅動，本 T1＝其 T-6 實例（不改 SOP 檔）。WHY：掌舵者要「每次啟動取得外部最新資訊」；全開放搜尋每棒燒數小時（守衛把 Web 工具當扇出、約 300 秒一次，主控任務書引述、本稿未重驗）且是毒化入口，限定來源＋增量＋只產候選是同時滿足 T1、C-12、FR-SI-02、NFR-SI-07 的最小形態。**SA 補記（⚖，各附預設）**：①研究者無 Write 權卻要「存成 `<id>.txt`」→預設＝研究者文字交卷、主控逐字落檔；若主控寧給研究者「只准寫指定暫存目錄」的 Write 權，AC-SI-30-4 ① 的工具白名單須改；②WebFetch 回模型處理後的文字而非頁面原文→`sha256` 量抽取穩定性（AC-SI-30-3 誠實劃界）；③`research.scan` 事件行含 8 筆來源可能逼近 `event_max_bytes`→預設＝實作輪實測、超限時不存 `url`；④來源表放協定目錄使指紋 manifest 受影響→預設＝AC-SI-30-6 要求排除；⑤`helmsman` 免掃加掌舵者座標（SA 加碼，預設採用，防主控自填繞過）；⑥禁令 26 的 OPEN-X.x 是否適用本迴圈外聯＝未查證，交 SCG-0（附錄 B）。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13　〔訂正（Architect 棒 v0.9；主控 ⚖1／⚖2 裁決，#16）：本列「`si research --record --dir` 由 CLI 對檔案自算 `sha256`、**CLI 不連網**」「工具 Read／Grep／Glob／WebFetch」「研究者文字交卷、主控逐字落檔」三處被 D-1′ 取代——CLI 以 `research --fetch` 自抓來源表 URL 的原始位元組（唯一可連網的動詞），研究者工具剩 Read／Grep／Glob；SA 補記①②由 D-1′ 消解，③④⑤⑥依 #16 裁決〕 | FR-SI-30；§3.2；NFR-SI-02-4、07-4；ADR-SI-11；附錄 B |
| 11 | 模組體檢（T1 1a；D-2） | 新動詞 `si scan`（唯讀、離線、無狀態、不寫事件）：彙整缺陷帳本新立 P≤2 未結列（啟動事件 (c)）、自上一筆 `run.close` 起新增的 OBS 列與 commit（依路徑歸 AutoClaude／AISDLC_SDD／AgentConsole／根層／SelfImproving 五桶）、事件帳本折疊出的待決 PROP／SUSPENDED／冷卻、`build/reports/` 下已存在的測試與 CI 產物、既有探針輸出檔，印 OBS 候選草稿列；零候選＝「無事件」、不得印成通過，候選數只進資訊欄。歸因者節新增模組體檢任務書範本（唯讀 Sonnet 子代理依 FR-SI-31 的入口表逐項檢，交卷＝候選 OBS 列＋流程摩擦，主控入帳；不得 Write／Edit、不得跑會改狀態的指令）。WHY：T1 1a 要「自行檢討」，沒有主動入口就只剩被動擷取；確定性部分進 CLI、需判斷的部分交唯讀子代理（12-Rule Rule 5）。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13 | FR-SI-31；§1.3.1 |
| 12 | Console：F-SI-101 再開（T1 1c；D-3） | **P1b（鍵 `agentconsole-si-mirror`，AgentConsole 子專案 SDD 流程）**：新唯讀動詞 `si export --json --kind {observations｜events｜proposals｜runs｜status}`；Bridge 以子行程呼叫它（自身不開帳本檔、不 import 根層 `tools/lib`，路徑過 `BRIDGE_ALLOWED_PATH_ROOTS`），提供 `GET /si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/{id}`、`/si/runs`；backend `GET /api/v1/si/**` 代理（JWT）；frontend 新頁 `/self-improving`（狀態橫幅、三分頁、待決卡面逐字＝`si card`）；P1b 零寫入端點；AC＝差分、唯讀、fail-loud（503 `si_unavailable`）、需登入。**P2b（鍵 `agentconsole-si-decide`）**：Console 成為 DEC 的第二種載體（`dec` 加 `carrier`），沿簽核硬閘（只准掌舵者帳號）、伺服器端稽核列（使用者、時間、PROP、digest、動詞、理由）、Bridge 子行程呼叫 `si decide --carrier console`；**驗證設計（逐字稿回查在 Console 路徑如何對應）＝⚖ 交 Architect 棒（ADR-SI-03 再開）**。WHY：T1 1c；F-SI-101 再開症狀逐字命中；Console 的定位是唯讀鏡像加既有簽核硬閘（§7.2、§9.3）。**SA 補記（⚖，各附預設）**：①`export` 動詞住根層 `tools/`，而 `AgentConsole/CLAUDE.md` 鐵律 7 禁其開發 agent 動 `tools/`，D-5 又寫 P1b 依賴 `export`→預設＝`export`（AC-SI-32-5）併入根層鍵 `monorepo-si-p1-propose` 的末棒、P1 出口加 (h)，`agentconsole-si-mirror` 只含 AgentConsole 半；②本 FR 的追溯落根層 RTM，不往 AgentConsole 的 RTM 加列（其「US 58」對帳閘），除非 Architect 棒查證可容納；③「掌舵者帳號」與 Architecture §8.2 的 Viewer／Operator／Admin 角色如何對映＝Architect 棒定。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13　〔訂正（Architect 棒 v0.9；#16）：SA 補記①②③已裁決——`export` 併根層鍵末棒（⚖6）、RTM 可容納本地編號子表（⚖11；§9.7 FC-c）、「掌舵者帳號」＝Admin 角色且在 `CONSOLE_SI_DECIDERS`（⚖12）；P2b 驗證設計＝ADR-SI-03′（⚖8）〕 | FR-SI-32、33；§9.3；ADR-SI-12 |
| 13 | 落點鎖（T1 2026-10-19 問題 2 與落點指令；D-4） | `tools/tests/test_root_module_layout.py`：(a) 解析 SSOT §3 登記表，每列的程式碼／入口／測試／資料路徑在磁碟存在；(b) `tools/lib/` 扁平檔同前綴 ≥3 支且未成套件＝紅，存量以 shrink-only 名冊豁免（名冊初值由實作輪現查）；(c) `tools/lib/<pkg>/` 每個套件都在 §3 登記表出現；(d) 新模組 PRD 的模組落點表必引用 SSOT 路徑（對 `docs/01_requirements/*_PRD.md` 掃含「模組落點表」字樣者判）。誠實劃界：形態判準。對應 OBS-SI-105 的再開待辦。**SA 補記**：此鎖是本 PRD 唯一新增的「鎖」，與「零新增守衛碼」的字面衝突已以明文例外化解（§3.2、附錄 B：`tools/tests/` 形態判準測試、不在守衛面清單、由 T1 直接指令驅動）。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13 | FR-SI-34；OBS-SI-105 |
| 14 | 階段與鍵（D-5） | P1 核心鍵 `monorepo-si-p1-propose`：FR-SI-05～11、14、30、31、34＋C6 定稿；FR-SI-28 另鍵 `autoclaude-evolution-propose-only`（不同持有面，可並行）；P1b 鍵 `agentconsole-si-mirror` 在 P1 核心之後（依賴 `export`，見 #12；⚖6 已採用）；P2b 併入 P2 之後（鍵 `agentconsole-si-decide`）；§8.1 P1 出口加 (e)(f)(g)（SA 另加 (h)＝`export` 綠，見 #12）、新增 P1b 列（出口：差分、唯讀、fail-loud 三 AC 綠＋至少一次真實瀏覽〔附 sid〕；SA 把需登入 AC 一併列入）；SA 另增 P2b 列（FR-SI-33 才有出口可歸）。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13 | §8.1；§9.6 |
| 15 | 文件最小化（T1 前言「省去非必要文件，只留一定需要文件」；D-6） | 不開新 ADR 檔：ADR-SI-11（研究來源表與增量掃描）、ADR-SI-12（Console 唯讀讀模型＝由帳本重建、不得成為來源）只在 §9.5 加列；不開 FRD／SRD；TCS、審查報告、RTM 各一份（主控派）。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13 | §3.1 FRD 欄；§9.5；§14 |
| 16 | Architect 棒（v0.9）落地 v0.8 的 12 個 ⚖ 與技術定案（⚖ 編號＝主控裁決節的編號；主控對 ⚖11、⚖12 只寫「採用」未展開，本棒依 #12 的 SA 補記②③推定為下列 ⚖11、⚖12，主控可更正；主控裁決 2026-10-19，掌舵者可隨時以 T1 推翻） | ⚖1／⚖2＝**D-1′**：研究抓取改由 CLI 以標準庫抓來源表 URL 的原始位元組（動詞 `si research --fetch`；只准 http／https、主機與重導向目標須在表內、逾時與位元組上限、不帶 cookie／token、固定 UA；來源檔存家目錄 `research/<id>/<sha12>.txt`；sha256 對原始位元組算）；研究者工具剩 Read／Grep／Glob（無 Web 工具）；`research --fetch` 是唯一可連網的動詞；SA 的 `--record --dir` 取消。⚖3＝`research.scan` 不存 `url`、不存候選數，存 `sources_sha256`。⚖4＝指紋 manifest 排除 `research_sources.json`。⚖5＝`helmsman` 免掃 P1 只記座標、`check` 印 NOT-EVALUABLE，引言回查於 P2 與 AC-SI-12-4 ⑤ 共用同一驗證函式。⚖6＝`export` 屬 P1 核心鍵出口 (h)，`agentconsole-si-mirror` 只含 AgentConsole 三層。⚖7＝P2b 列採用，需登入 AC 併 P1b 出口。⚖8＝FR-SI-33 驗證機制交 Architect 棒定案（ADR-SI-03′，§9.5）：Console 決定＝Admin 角色且在 `CONSOLE_SI_DECIDERS`（主控稱 `SI_DECIDERS`，依 console-api 設定體例加 `CONSOLE_` 前綴；K=1）、稽核 JSON＋HMAC、主機端 CLI 入帳；兩點待主控確認（金鑰通道、入帳模式）。⚖9＝FR-SI-34 是 `tools/tests/` 形態判準、不在守衛面清單、由 T1 直接指令驅動，接受其為「零新增守衛碼」的明文例外。⚖10＝來源表為事前登記載體；禁令 26（OPEN-X.x）適用性交 QA（SCG-0）判。⚖11＝SI 追溯落根層 RTM、AgentConsole 側可補本地編號子表（§9.7 FC-c）。⚖12＝「掌舵者帳號」對映 Admin 角色＋`CONSOLE_SI_DECIDERS`。授權座標：sid `ee6af537-7091-4f0e-842c-0d091085f77b` line 13 | FR-SI-30～34；§9；附錄 B |

## ✅ 文檔完成檢查清單
### PRD 品質檢查
- [x] 所有必填欄位已完成（元數據與 Brownfield 欄位已填；「目標日期」刻意無日曆，見 §8）
- [x] 根據專案類型填寫對應的情境專屬章節（Brownfield：§11 已填；Web／Mobile／Greenfield／Sprint／Integration 專屬欄位不適用：無 UI 平台、非新專案、非衝刺、非第三方整合）
- [x] 成功指標明確可衡量（§1.3 M1～M5 附量法與來源；基線未量測者標 NOT-EVALUABLE）
- [x] 範圍定義清晰（§3.1 In-Scope／§3.2 Out-of-Scope）
- [ ] 所有 🔴 確認點已通過（掌舵者尚未確認；QA SCG-0 二審已 PASS；本稿作者不得自證）
- [x] 時程與資源合理（不適用日曆：改以症狀出口 §8 與額度／人審成本 §4.1 表達）
- [x] 風險已識別並有緩解措施（§10：14 項〔v0.8 加 2 列〕，含現有防線座標與剩餘風險）
- [ ] 與 Stakeholders 完成評審（QA SCG-0 一審 FAIL、二審 PASS〔P1＝0、P2＝0；`docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` §6〕；二審新增的 P3 已於 v0.7 收尾；v0.8 的 T1 修訂與 v0.9 的技術定稿尚待 QA 審查；掌舵者尚未評審）

### AISDLC 流程檢查
- [ ] 已由 PM/PO Agent (Victoria) 主導撰寫——不適用：本稿由 SA 棒（Sonnet 5.5）依掌舵者 T1 與 SOP 起草（四方專家流程）
- [ ] 已由 BA Agent (Beatrice) 協助驗證——不適用：由 QA 做 SCG-0 獨立審查（一審 FAIL、二審 PASS）
- [ ] 所有人機協作確認點已完成（待掌舵者）
- [x] 文檔追蹤鏈完整（§14、附錄 A；FRD／TCS／SRD 為實作輪下游，非缺漏）
- [x] 版本控制正確（Draft；落在 git 追蹤的 `docs/01_requirements/`；本稿作者未做 git 寫入，由主控提交）

### 本稿特有檢查（SA 自檢；QA 須獨立重驗，不得採信本欄）
- [x] 無日曆／版本號／覆蓋度門檻型觸發；延後項皆為 ⏸＋可觀測再開症狀
- [x] 只引 DP-01～12 與 S-01～30、repo 座標；候選 CD 只出現在 §3.2 作反例
- [x] 不引用任何外部來源的實驗量化結果（S-08 的載入上限屬文件陳述，已標 25KB 換算未查證）；初值參數皆標「初值（未校準）」並註明先例或「無先例」
- [x] 每條 FR 有「追溯」與「憲法對照」；每個 DP 至少落在一條 FR（附錄 A）
- [x] 未新增任何守衛碼、鎖、hook；本稿新增本檔；本輪另改 `AutoClaude/CLAUDE.md` 兩處（738f4f60、69a644e6）、SOP II-7 T-1、觀察帳本——皆主控 commit（v0.8 增補 FR-SI-34 落點鎖：`tools/tests/` 形態判準測試，非守衛面、非 hook，見 §3.2；本欄為立案時 SA 自檢，v0.8 的自檢另見交卷、QA 須獨立重驗）

---

**文檔所有者**: 掌舵者
**最後審查日期**: 2026-10-19（QA SCG-0 一審：FAIL；二審：PASS；P3 收尾見 §13.3 v0.7；v0.8 的 T1 修訂與 v0.9 的技術定稿待 QA 獨立審查，主控派）
**下一次審查日期**: 事件驅動（掌舵者的凍結核准；或 §3.3 某 ⏸ 列的再開症狀成立；不排日曆）

