# Test Contract Specification — SelfImproving P5（頂尖專家四問檢視：四問審視者、答案檔判準、`fourq` 動詞與事件、閘門、`method`／`proof`、`status.fourq`、範本九步）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層單半，Console 零程式改動）

**文件類型**: Test Contract Specification (TCS)　**SDD Gate**: SCG-4　**spec-format-version**: 1.0　**scenario**: brownfield
**使用時機**: 已凍結系統（PRD v0.14 於 Stage-1 重凍）的單一 Feature（P5）；FSM 功能鍵建議 `monorepo-si-p5-expert-review`；`spec-frozen --doc` 指向本檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P5-20261110.md`　**輸入快照**: HEAD `d864d638`（寫稿時現查，工作樹乾淨）
**建立日期**: 2026-11-10　**QA**: SCG-4 獨立 QA 棒（規格作者＝本 SD 棒，實作者＝Developer 棒＋主控〔收尾、真機、重釘〕，三方不同）　**SCG Gate**: SCG-4 □ 待審

---

## 增量變更：FRD-lite 與追溯

> 沿 P4 TCS 體例（AT 格式、驗收字樣 `[AT_OK_<底線形>]`、hermetic、零殘留、`-k` 錨定）：本檔不複寫。**凍結檔不改**；PRD 需修訂處寫在 §5。**裁決（D-EFQ／D-EQA）全文只住 PRD 附錄 C.2 #24，本檔只引編號。** 本檔刻意精簡（D-EQA-12）。

**Before／After（寫稿時現查）**：Before——`_HELP` 26、`KINDS` 23、`ITEM_IDS` 35、`PARAM_SPECS`／`params.json` 41、`CHECK_RULES_REV` 5、`status` 16 鍵、`CAPABILITY` 59、`EVENT_LABELS` 23；`events.py` 400／400；範本八步；無 `fourq`、`_fourq/`、`method`／`proof`。After——`_HELP` 27、`KINDS` 25、`ITEM_IDS` 35（判準併入 `events.research`）、44 鍵、`CHECK_RULES_REV` 6、`status` 17 鍵、`CAPABILITY` 62（`fourqparse` `ro`、`fourq` `rw`、`evspec` `ro`）、`EVENT_LABELS` 25、範本九步。**不含**：Console 程式（零改動，V37 實跑）、真機（V36～V39，不入 AT）、審視者內容品質（P）、macOS。

**編號**：FR 自 41（`AT-440-*` 已是 P4 自增 AC，D-EFQ-18）；自增 AC `AC-P5-045-1`～`-5`→`AT-445-*`；PRD AC 18＋自增 5＝23，皆有 AT；**AT 共 58（正控 27、負控 31）**；FM＝`tools/tests/test_selfimproving_fourq_model.py`（26）、FG＝`tools/tests/test_selfimproving_fourq_gate.py`（32）。

**交付物與順序**：①夾具與既有測試同步站點（§2）先行 → ②`events.py` 拆 `evspec.py`（零行為變更，既有 AT 全綠才往下）→ ③`PARAM_SPECS`＋`params.json`＋基線三列同 commit → ④兩種事件 → ⑤`fourqparse` → ⑥`fourq`＋`propfiles.write_new`＋入口 → ⑦九處接線（PRD §9.8.5）→ ⑧能力登記。每支程式完成立即跑該區 AT。
**提交程序（D-EQA-5、D-EQA-9；`test_AT_440_8_1` 現查：基準＝`SI_P4_BASE_SHA`，缺省 `HEAD~1`；差分觸及 P4 允許集合〔`tools/lib/selfimproving/*.py`、`tools/selfimproving.py`、`tools/tests/(_)selfimproving_*`、`params.json`、基線文件〕時強制差分 ⊆ 允許集合，且 PRD、SOP、`TCS-SelfImproving-P*` 差異為空）**：①規格 commit（PRD、SOP、本 TCS）不含允許集合路徑，**本身不觸發**；②只在工作樹已有實作改動時才 commit 規格，規格與實作 commit 連續、同一次 push（有改動時 (f)／(a) 被 `dirty-tree` 擋，主控在場時被 `other-driver` 擋）；③實作 commit 不得含 PRD、SOP、TCS；**本機跑 `test_AT_440_8_1` 與 AT-445-5-1 時才需設 `SI_P4_BASE_SHA=<規格 commit>`（WHY：pre-commit 不跑 unittest）；開發期規格檔尚未 commit，這兩個範圍守衛在本機必紅，開發期一律以 `-k "not test_AT_440_8_1 and not AT_445_5_1_"` 排除，commit 後在 tip 以預設基準重跑驗綠（D-EQA-20，列入 SCG-4 標準）**；④本檔日後勘誤**單獨 commit**（`FROZEN` 以 `TCS-SelfImproving-P` 為前綴、僅豁免 `-P4-`）；⑤重釘儀式另一 commit（主控收尾）；⑥新 `template_problems` 對舊範本 fail-closed（AC-SI-44-1）是第二道防線。**以上兩條防線取代 `sched disarm`**，並列為 V36 前置。

---

## 1. AC → AT 映射（唯一一張表；判定指令一律 `python -m pytest <檔> -k <AT 底線形>_ -q -p no:xdist -o addopts=`）

**舊碼紅法**欄：`MNF`＝舊碼 `lib.selfimproving.{fourqparse,fourq,evspec}` ModuleNotFoundError 或 `fourq` 子命令不存在即紅；其餘寫斷言差異。`fx`＝夾具建構器（§3）。

### AC-SI-41-1 角色與隔離（R168）、AC-SI-41-2 答案檔格式（R169）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-441-1-1 | FM | 真 SOP 的〈四問審視者〉節（圍欄外）含 `Read／Grep／Glob`、無 Web、不得 Write／Edit、零遞迴、不同實例、`--pace`、「任務書不含任何迴圈層量測值」、四問標準句四句逐字；`sop_p5_problems` 回空 | 無該節 ⇒ `SOP-P5-REQ-MISSING` |
| AT-441-1-E-1 | FM | 變體：刪上列任一片段／四問第 3 句改一字／整節搬入圍欄／節改名 ⇒ 各回對應 `SOP-P5-*`；原檔回空 | 判準不存在 |
| AT-441-2-1 | FM | `fx.answers()` 合法檔（Q1 一項、Q2 F＋G、Q3、Q4）`parse`＋`validate` 無問題；各問項數 (1,2,1,1)，`gaps`＝1 | MNF |
| AT-441-2-E-1 | FM | 變體：缺首行；缺／換序／多／改字標題；項目編號不連號；`Q2-F0` 與 `Q2-F1` 並存；Q1 項缺 `領域`／領域 >20 字；Q4 項多一個標籤 ⇒ 各一個 `FOURQ-FORMAT` | MNF |
| AT-441-2-E-2 | FM | Q1 項與 Q2-G 行含 ASCII `|` ⇒ `FOURQ-PIPE`；**Q4 的反引號內含 `|` 與 Q3 行不判**（D-EQA-13，對照）；控制字元 `\x07`、`\x85`；單行 `row_max_bytes`＋1；整檔 24,577 bytes；非 UTF-8 ⇒ `-LINE`／`-FILE-BYTES`／`-FORMAT` | MNF |
| AT-441-2-E-3 | FM | 額度帶經注入縫：`free` 上限 `fourq_items_max`、`notice`／`converge`／量不到上限 `fourq_degrade_items_max`；每問超限各一個 `FOURQ-ITEMS-OVER`；`Q1-X` 另計；恰達上限通過 | MNF |

### AC-SI-41-3 座標、查詢、引用（R170）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-441-3-1 | FM | 夾具 repo（OBS 帳本、archive、缺陷帳本、迷你 PRD／SOP 含已知字串）＋合法檔，座標五式各一、每 Q1 項 ≥2 條綁定查詢且狀態與重算相符 ⇒ 無問題 | MNF |
| AT-441-3-E-1 | FM | 座標空／行號超出／`DEF` 不存在／`src=<id>` 不在表（retired 者照收，對照）；Q3 工具為不存在路徑或 `外部：` 無 `src`；Q2-G 的 URL 為 `http://`／含 userinfo／分級 `T3` ⇒ `FOURQ-COORD-MISSING`／`-SRC-UNKNOWN`／`-TOOL-UNKNOWN`／`-FORMAT` | MNF |
| AT-441-3-2 | FM | `CORPUS` 固定清單：語料多放一個 archive 或備份檔不影響結果；宣稱 `零命中`／`命中不涵蓋` 只在零／非零與重算一致時通過（行數不必相等）；CRLF 語料同結果；行數記入 `qhits`；`fourq --corpus` 印出與 `CORPUS` 相同的清單 | MNF |
| AT-441-3-E-2 | FM | 變體：Q1 項只有 1 條查詢／兩條相同（`FOURQ-QUERY-DUP`）；查詢顯示寬度 3（`-TOO-SHORT`）或 17（`FOURQ-QUERY-TOO-LONG`，另測 5 個中文字＝寬度 10 合格、9 個中文字＝寬度 18 過長）；查詢不是該項做法或機制的子字串（`-UNBOUND`）；宣稱零命中而實際 ≥1（`-MISMATCH`）；零項 Q1 只有 1 筆 `Q1-X` 或其查詢宣稱命中而實際 0，或其涵蓋座標所指的那一行不含該查詢字串（`FOURQ-Q1-EMPTY-UNJUSTIFIED`）；語料缺（`FOURQ-CORPUS-UNAVAILABLE`，fail-closed） | MNF |
| AT-441-3-3 | FM | 答案檔全文（含 `差異`、`發現`、`反證` 等自由欄）出現的 OBS／ATT／PROP／DEC／APP／RUN 編號皆存在於對應帳本 ⇒ 通過；以 `fx.obs_id()` 組出存在的號 | MNF |
| AT-441-3-E-3 | FM | 自由欄含不存在的 OBS 號、不存在的 PROP／RUN 號、任一 `MEA` 號 ⇒ `FOURQ-REF-DANGLING`（點名 token）；**對照**：把該答案檔真提交進夾具 repo 的 git 後 `check` 的 `ref.obs` 為紅（證明本碼擋的是真失敗） | MNF |

### AC-SI-41-4 Q4 與迴圈層快照（R171）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-441-4-1 | FM | Q4 項四子欄合法（指標類別 M1／M4／M5／`症狀：…`；症狀定義為反引號指令含數字與 `|` 或座標）⇒ 無問題 | MNF |
| AT-441-4-E-1 | FM | 變體：反引號外的 `n=5`／`30%`、「基線」「門檻」「閾值」、`PARAM_SPECS` 任一鍵名、`params.json`、`W_MIN` ⇒ `FOURQ-Q4-LEAK`；「觀察筆數上升」「提案筆數」「採納率」「自評」「信心」⇒ `FOURQ-GOODHART`；「不以觀察筆數為成效」「不得以…」「並非以…」不判；單字「非常」或「非」不構成豁免 | MNF |
| AT-441-4-2 | FM | 夾具 repo 入帳 ⇒ 事件 `loop` 含 M1、M4、M5a、M5b 的值、n 或 NE 理由，且與 `meastat` 同函式直接重算相等；輸出印出同樣各行；**入帳前後事件帳本無任何 `mea.*` 新事件**；`meastat` 載體缺席 ⇒ `loop` 逐項 NE（不是 0、不是達標）；無人值守環境（`AUTOSDD_UNATTENDED`＋`PATROL_RUN`）下同樣得到快照，不需任何輸入；**`params-invalid` 例**：`params` 缺 `valid_keys` 所需鍵 ⇒ `loop` 逐項 NE、理由 `params-invalid`；事件帳本不在場 ⇒ 理由 `carrier-not-established`（D-EQA-25、26） | MNF |
| AT-441-4-E-2 | FM | 答案檔含 `Q4-L` 節或任何迴圈層數值字樣（`M1：read`）⇒ `FOURQ-FORMAT`／`-Q4-LEAK`；不存在 `FOURQ-LOOP-MISMATCH` 碼（掃原始碼） | MNF |

### AC-SI-42-1～42-4 動詞、免審、落地、事件（R172～R175）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-442-1-1 | FM | 已開運轉有 `research.skip`＋合法檔 ⇒ `fourq` rc 0；事件帳本恰多一行 `fourq.review`（`path`、`sha256`＝落地檔 LF 雜湊、`q1`～`q4`、`gaps`、`qhits`、`loop`）；落地檔位元組等於答案檔；`seq` 連續 | 子命令不存在 |
| AT-442-1-E-1 | FM | 運轉已關／無研究事件／已有 fourq／`--by main`／`--by researcher`／標籤含空白／答案檔不存在或非 UTF-8 ⇒ rc 1（`RUN-NOT-OPEN`／`FOURQ-BEFORE-RESEARCH`／`-ALREADY`／`-BY-RESERVED`）或 rc 3；事件帳本與 `_fourq/` 零變化、輸出含 `obs-draft:` | MNF |
| AT-442-1-E-2 | FM | 事件追加失敗（`event_max_bytes` 注入極小／`LOCK-BUSY`）⇒ rc 1、`_fourq/<RUN>.md` 不存在、帳本不變；落地檔已存在 ⇒ `FOURQ-FILE-EXISTS`、既有檔不變 | MNF |
| AT-442-1-2 | FM | `--dry-run`：合法檔 rc 0、不合法檔 rc 1 且碼與正式入帳一致；兩者事件帳本、`_fourq/`、OBS 帳本位元組零變化 | MNF |
| AT-442-2-1 | FM | 互動（無 `AUTOSDD_UNATTENDED`）、注入額度帶為非 free：`--reason quota-band --band notice` ⇒ 一行 `fourq.skip`；`helmsman --sid <UUID> --line 3` ⇒ 一行；其後 `fourq --answers-file` ⇒ `FOURQ-ALREADY` | MNF |
| AT-442-2-E-1 | FM | 無人環境任何 `--skip` ⇒ `FOURQ-SKIP-REFUSED`；互動但額度帶 free 的 `quota-band` ⇒ `FOURQ-SKIP-BAND-FREE`；`--reason offline`／缺 `--band`／`--band free`／`--sid` 非 UUID／`--line 0`／`--note` 空或 121 字元 ⇒ rc 3；零寫入 | MNF |
| AT-442-3-1 | FM | 提案目錄含已落地 `_fourq/<RUN>.md` 與一合法 PROP：`check` 無 `PROP-DIR-ORPHAN`、`events.prop_files` 無新碼、`export --kind proposals` 不含 `_fourq`、`dirty-tree` 判乾淨、`sandbox`／`verify`／`promote` 前置讀取與無 `_fourq/` 時位元組相同 | 夾具建構失敗 |
| AT-442-3-E-1 | FM | 另有名稱符合 `PROP_RE` 而無 `prop` 事件的目錄 ⇒ 仍只有它被報 `PROP-DIR-ORPHAN`；`_fourq/<RUN>.md` 改一字 ⇒ `FOURQ-SHA-MISMATCH` | MNF |
| AT-442-4-1 | FM | `len(KINDS)`＝25；`validate` 對合法兩事件回空；`events` 既有對外名稱（`validate`、`sound`、`read_lines`、`KINDS`、`SKIP_REASONS`、各 `*_RE`、`LEDGER_REL`、`PROPOSALS_REL`…）在 `evspec` 拆分後仍可自 `events` 取得；`fourq_events` 回 `{run:(kind,seq,ev)}` | `KINDS`＝23 |
| AT-442-4-E-1 | FM | 缺 `path`／`path` 不等於 `…/_fourq/<run>.md`／`sha256` 無前綴／`q1` 負或布林／`gaps`＞`q2`／`loop` 或 `qhits` 非字串、含非 ASCII、`loop`＞256 bytes、`qhits`＞128 bytes（超界變體各一）／`by` 為 `main`／skip 的 `by` 非 `main`／`reason` 為 `offline`／表外鍵 ⇒ 各 `EVENT-KEY-*`／`EVENT-TYPE`；`sound()` 濾掉 | MNF |

### AC-SI-43-1～43-4 閘門與欄位（R176～R179）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-443-1-1 | FG | `fourq_from_run`＝1、運轉有 review（或 skip）⇒ `prop-new --proposer <另一標籤>`（本文含 `method`／`proof`）rc 0 | 夾具呼叫 `fourq` 不存在 |
| AT-443-1-E-1 | FG | 適用運轉無 fourq ⇒ rc 1、`FOURQ-MISSING`、`obs-draft:`、零變化；與 `NO-INTERNAL-SOURCE` 並存時兩碼同回 | 舊碼放行 rc 0 |
| AT-443-1-E-2 | FG | `review.by`＝X 且 `--proposer X`（含 `prop-revise`）⇒ `FOURQ-IS-PROPOSER`；`--proposer Y` 通過；skip 運轉不判 | 舊碼放行 |
| AT-443-2-1 | FG | 合法流程 `check` rc 0、`events.research` PASS、`len(items)`＝35、`check_rules_rev`＝6 | rev＝5 |
| AT-443-2-E-1 | FG | 變體：有 prop 無 fourq；兩筆 fourq；fourq 在研究事件前／第一筆 prop 後；`by`＝同運轉 `proposer`；檔缺；檔被改；檔格式不合；事件 `q2` 與解析不符 ⇒ 依序 `FOURQ-MISSING`／`-MULTIPLE`／`-ORDER`×2／`-IS-PROPOSER`／`-FILE-MISSING`／`-SHA-MISMATCH`／`-FORMAT`／`-COUNT-MISMATCH` | 無此碼 |
| AT-443-2-E-2 | FG | 適用運轉已關閉且無 fourq（含 `no_event`）⇒ info `FOURQ-NOT-RUN`、`check` rc 不變；`fourq_from_run` 之前的運轉無任何 fourq 碼 | 無此 info |
| AT-443-3-1 | FG | 適用運轉提案本文含 `method`＋四子欄 `proof` ⇒ `card` tail 多一行「方法與工具：…｜成效與收斂：…」；核心區行數、`CORE_MAX`、`parse()` 與同提案無兩欄時相同；同 patch 與五欄、不同 `method`／`proof` 文字的 `digest` 差異只來自 `body_sha256`（15 鍵公式不變） | 卡面無該行 |
| AT-443-3-E-1 | FG | 缺／空白 `method`／`proof` ⇒ `BODY-FIELD-MISSING`；`proof` 含基線數字／門檻／參數鍵名／`params.json` ⇒ `PROOF-LEAK`（同一禁字函式，AT-441-4-E-1 的詞表）；豁免運轉缺兩欄照收；`proof` 少一個子欄 ⇒ 拒收 | 舊碼放行 |
| AT-443-3-E-2 | FG | 真 repo 既有 PROP 的 `card` 輸出與 HEAD 版逐位元組相同；本文只有一欄時 tail 不渲染 | 對照組：舊碼亦過，紅在突變（SCG-4 清單） |
| AT-443-4-1 | FG | `fourq_from_run`＝F（含 F＝999）：`rid(F-1)` 豁免、`rid(F)`、`rid(F+1)` 與 `rid(1000)` 適用，依**整數**比較（`"1000"<"999"` 陷阱） | 無此鍵；整數比較紅在突變 |
| AT-443-4-E-1 | FG | 三鍵缺／`fourq_from_run`＝0、負、字串、布林／`fourq_items_max`＝0／degrade＞items ⇒ `PARAM-MISSING`／`-TYPE`／`-RANGE`／`COUPLING-FOURQ-DEGRADE-GT-MAX`；(3,1,N) 綠 | `PARAM_SPECS` 無三鍵 |

### AC-SI-44-1～44-6 範本、巡邏、可見面（R180～R185）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-444-1-1 | FG | 真 SOP：`template_problems`＝[]；`render`（五個大寫占位符代入）含四問四句逐字、`^[1-9]\. ` 恰 9 行、`## 禁止事項`、handback 四節；步 2 的靜態項數上限數字（1、3）**等於** `params.json` 的 `fourq_degrade_items_max`、`fourq_items_max` | 八步；無四問 |
| AT-444-1-E-1 | FG | 範本變體：刪四問任一句×4／刪步 2／刪第 9 步／步 2 與 3 對調／刪 `fourq` 指令句 ⇒ `FOURQ-TEXT-MISSING`／`ROLE-STEP-MISSING:2`／`:9`／順序碼；**舊範本（八步、無四問，取 HEAD 版 SOP 範本）⇒ 非空（fail-closed）**；`sched.spawn_problem` 對各變體回 `sop-template:` 起頭、不 spawn | 舊判準放行八步範本 |
| AT-444-2-1 | FG | `DEGRADE_TEXT.format(band=…)` 呼叫簽章與輸出不變（`free` 無降載聲明、`notice`／`converge` 有）；`UPPER_FIELDS` 不變 | **紅在突變**（舊碼亦過；已列入 SCG-4 突變清單，D-EQA-24） |
| AT-444-3-1 | FG | `spawn.json` 子行程已結束、運轉適用、無 fourq 事件 ⇒ 日誌恰一行 `FOURQ-NOT-RUN`、`run-close(no_event)` 照常、spawn 次數與 `sched.skip` 數不增、`SKIP_REASONS` 仍 7 值 | 無此日誌 |
| AT-444-3-E-1 | FG | 同情境但有 review／skip，或運轉不適用 ⇒ 無此日誌 | 紅在突變（適用判斷，SCG-4 清單） |
| AT-444-4-1 | FG | 夾具（一 review 運轉、一適用而無 fourq 的已關閉運轉、OBS 兩列「來源缺口候選：」一 open 一終值）`status --json` 與 `export --kind status` 的 `fourq` 逐值相同；`state`／`last_run`／`loop`（最近快照）／`gaps_open.count`＝1／`missing_runs`＝1；文字含 `fourq:` 行；`status` 17 鍵、末鍵 `fourq` | 16 鍵 |
| AT-444-4-E-1 | FG | 無事件帳本／OBS 帳本讀不到／無運轉 ⇒ `fourq` NE（`carrier-not-established`）／`gaps_open` NE（不是 0）／`state`＝`none`；`EVENT_LABELS` 25、含兩新標籤、`closure_problems()` 空；刪一標籤時點名 | 標籤 23 |
| AT-444-5-1 | FG | `AUTOSDD_UNATTENDED`＋`PATROL_RUN`＝A：`gate("fourq","A",env)` 空、`A_CLASS` 含 `fourq`；`fourq-corpus` 在 `READONLY`；真入口入帳成功；**`fourq --dry-run` 走同一道 A 類閘**（`--run`＝`PATROL_RUN` 放行）| 舊 `gate` 回 `UNATTENDED-REFUSED` |
| AT-444-5-E-1 | FG | `--run` 為 B／`PATROL_RUN` 未設、空字串、字面 `0` ⇒ rc 1、`UNATTENDED-REFUSED`、零寫入零落地檔；`--dry-run` 的 `--run` 為 B 亦 rc 1、`UNATTENDED-REFUSED`（D-EQA-21）；未設 `AUTOSDD_UNATTENDED` 行為不變 | 子命令不存在 |
| AT-444-6-1 | FG | 三支新／拆檔以 `ast` 掃 import（含延遲 import）只含標準庫、套件內相對 import、`si_repo_support.CLI_CLOSURE` 既有 `lib` 頂層檔（`sched.quota_check` 的 `quota_gate` 為 `sched.py` 既有延遲載入）；`git diff --name-only <基準> -- AgentConsole .github` 為空（觸及 P5 允許集合時才強制） | 檔不存在 |
| AT-444-6-E-1 | FG | 注入副本：新模組多 `from lib import quota_ledger`／`import subprocess` ⇒ 掃描點名；`CLI_CLOSURE` 第四項仍是目錄 `tools/lib/selfimproving/`（讀文字斷言） | 同上 |

### 自增 AC-P5-045-1～5（R179、R186～R189）
| AT | 檔 | Given／When／Then | 舊碼紅法 |
|---|---|---|---|
| AT-445-1-1 | FG | 真 `params.json` 44 鍵、鍵序合規、三鍵位於 `export_limit_max` 與 `ledger_fail_bytes` 之間、鍵集等於 `PARAM_SPECS`、`fourq_from_run` 整數且大於事件帳本現有最大運轉號 | 41 鍵 |
| AT-445-1-E-1 | FG | 基線文件 `params.json` 雜湊／位元組、指紋、`CHECK_RULES_REV` 列等於活值（沿 `AT-LD-02-6-1`／`-E-1`）；`CHECK_RULES_REV`＝6 | 列為 5 |
| AT-445-2-1 | FG | P4 基線夾具（`fourq_from_run` 大於夾具內所有運轉號）重放 `sc_close`、`sc_legal`、`sc_rev`、`sc_susp`、`sc_p2_legal`、`sc_seq`：`events.structure` PASS、既有 PROP 卡面位元組不變、`make_p1_repo`／`make_p2_repo` 簽章不變 | `p5_base` 不存在 |
| AT-445-2-E-1 | FG | §2 站點表逐項持新值：`_HELP`＝27、`KINDS`＝25、`ITEM_IDS`＝35、`PARAM_SPECS`＝44、`CHECK_RULES_REV`＝6、`CAPABILITY`＝62、`status` 17 鍵、`EVENT_LABELS`＝25 | 仍為舊值 |
| AT-445-3-1 | FG | SOP：〈rc 契約表〉有 `fourq` 列（rc 0／1／3 非空）；〈最小序列〉PowerShell 與 bash 圍欄各含 `fourq` 且位於 `scan` 之後、`attr` 之前；〈提案檔〉含 `method`、`proof`；〈四問審視者〉節在〈研究者〉與〈運轉配方〉之間；〈研究者〉節與研究方法論 SOP 全檔 sha256 等於測試常數（主控於規格 commit 以 `d864d638` 版計算填入；WHY：以 HEAD 對照在規格 commit 落地後恆為空差異） | 舊 SOP 無 |
| AT-445-3-E-1 | FG | 變體：刪 rc 列／`fourq` 移到 `attr` 之後／刪 `proof`／改〈研究者〉一字 ⇒ `SOP-P5-*`（含 `SOP-P5-RESEARCHER-CHANGED`） | 判準不存在 |
| AT-445-4-1 | FG | `CAPABILITY` 62 鍵、`fourqparse`＝`ro`、`fourq`＝`rw`、`evspec`＝`ro`；`fourq.py` 不 import `runner`／`fetch`、無網路與子行程字樣；`check_loc_budget.py --json` 無違規（`events.py` 拆後餘量為正） | 未登記 |
| AT-445-4-E-1 | FG | 注入：`fourq.py` 含 `import subprocess`／`urllib`／`time.sleep`；`fourqparse.py` 含 `open(…,"w")`；`evspec` 登記為 `rw` ⇒ 各回登記碼（沿 P4 `AT-440-3-E-1`） | 同上 |
| AT-445-5-1 | FG | 差分觸及 §3 允許集合時：⊆ 允許集合；`.claude/**`、`AgentConsole/**`、`.github/**`、研究方法論 SOP、P0～P4 TCS、`schedule_backend.py`、`resume_route.py`、`unattended_authz.py`、`model_roles.py` 差異為空；未觸及＝「範圍守衛未觸發」；兩測試檔與夾具無跳過類字樣 | 測試檔不存在 |
| AT-445-5-E-1 | FG | 本表每個 AT 有名為 `test_<底線形>_…` 的函式、`-k` 錨定不誤中兄弟（`AT_441_2_1_` 不命中 `AT_441_2_E_1_`）、AT 總數 58（FM 26、FG 32）；缺函式的副本回缺 | 同上 |

（AT 數：FM 26＝AT-441×16＋AT-442×10；FG 32＝AT-443×11＋AT-444×11＋AT-445×10。）

---

## 2. 既有測試的同步站點（行號僅供參考，須現查；`check` 項數 35 不變，故十餘處 `len(items)==35` 不改）

| 站點 | 既有檔與函式 | 變更 |
|---|---|---|
| `_HELP` 26→27 | `test_selfimproving_issues.py`、`console_obs::test_AT_235_3_1`、`p3_meta`（`len(selfimproving._HELP)`）、`schedule_gate::test_AT_440_5_E_1`（含其對上列檔的字面需要檢查 `"len(selfimproving._HELP), 26"`、`"len(verbs), 26"`） | 改 27；P4 該 AT 之改動屬 P4 勘誤，由主控追認 |
| `KINDS` 23→25、`EVENT_LABELS` 23→25 | `events_p2`（約 143）、`issuemap`（約 157）、`schedule_gate::test_AT_440_5_E_1`、`events.py` 內「不在 N 個詞彙內」斷言 | 改 25 |
| `CHECK_RULES_REV` 5→6 | `p3_meta:292`、`schedule_gate`（約 85、1046）、`measure_verb:163`、`events_p2:883`、`events:1196`、基線文件列（`ledgerdb_p0::test_AT_LD_02_6_1`） | 改 6；基線同 commit |
| `params` 41→44 | `schedule_gate` 的 `len(...)==41`（兩處）、`_selfimproving_fixtures.params_dict`、`check` 本地 `params_dict`、`p2`／`p4` 夾具 `params.json`、`p2_meta` 鍵集斷言、基線文件雜湊／位元組／指紋 | 加三鍵；夾具 `fourq_from_run` 大於夾具內所有運轉號 |
| `status` 16→17 | `export_status::STATUS_KEYS`、`events.py` 的 `WEIRD_STATUS_KEYS`、`console_obs::test_AT_240_12_1`、`schedule_gate` 的 `len(self.status(...)),16` | 末鍵 `fourq` |
| `CAPABILITY` 59→62 | `capability`：`CAPABILITY`、`test_AT_143_1_1`、`_240_5_1`、`_340_4_2`、`_143_1_E_2` | 加三鍵與計數；`exec` 集合不變 |
| 範本 | `schedule_patrol::test_AT_438_2_1`（`[1-8]`→`[1-9]`、8→9）、`::_E_1`（變體數）；`unattended` 真值表 A 類 8→9 | 同左 |
| SOP 切段 | `events::TestSopArticles`、`p3_meta::sop_p3_problems`、`p2_meta::sop_p2_problems`（`p3m.section` 以同級標題切，答案檔範本圍欄內含 `# `／`## `，故 `sop_p5_problems` 須圍欄感知） | 預期零改；紅則 ⚖ 回報 |
| 範圍守衛 | `schedule_gate::TestScope::test_AT_440_8_1` | 不改；依 §0 提交程序 |
| 護欄層與棘輪 | 檔數下限、E501、guard-total、`_REPIN_APPROVED_ROUND_OVERAGE`、compat-ci `paths`；`test_root_module_layout.py`；`test_platform_neutral_paths.py`（`encoding="utf-8"`、`sys.platform`、時間帶 offset） | 主控收尾重釘（獨立 commit）；新檔遵守鐵律三 |

## 3. 測試資料、seam 與允許集合

夾具 `tools/tests/_selfimproving_p5_fixtures.py`：`p5_base()`（自 `fx4.p4_base()`，加三鍵、迷你語料）、`answers(**mods)`（合法答案檔建構器，可逐項抽換／注入變體）、`rid()`／`pid()`／`obs_id()`（執行期字串相加；本檔與測試不寫不存在於真帳本的字面編號）、額度帶注入縫（`sched.quota_check` 的 `read`）。函式名皆建議，改名須勘誤登記。
seam（建議）：`fourqparse.parse／validate／CORPUS`；`fourq.review／skip／loop_snapshot／gate_codes／check_findings／status_value／fourq_events`；`loop_snapshot(repo, params, events)`：先照 `status.measure_value` 判 `valid_keys(params)` 與事件帳本在場，缺則逐項 NE（理由 `params-invalid`／`carrier-not-established`）；在場時呼叫 `mea.build_ctx(repo, Git(repo), params, events)` 與 `meastat.metrics(repo, git, ctx, carrier=True)`，取 `success.m1`、`m4`、`m5.main`（M5a）、`m5.all`（M5b）各自的 `{status, value, n, reason}`（D-EQA-26）；`patrolbrief.template_problems`；`unattended.gate`；`propfiles.write_new`。
**允許集合**：程式 `tools/lib/selfimproving/{fourqparse,fourq,evspec}.py`（新）與 `{events,props,evcheck,card,status,patrolbrief,patrolrun,unattended,issuemap,params,propfiles}.py`（各限 PRD §9.8.5 所列一處）、`tools/selfimproving.py`；`params.json`；基線文件；測試兩檔＋夾具＋§2 站點。**不得改**：`fold.py`、`writeverbs.py`、`resume_route.py`、`schedule_backend.py`、`unattended_authz.py`、`.claude/**`、PRD、SOP、研究方法 SOP、P0～P4 TCS、`AgentConsole/**`、`.github/**`、`research_sources.json`。

## 4. 實跑檢核 V36～V39（不是 AT；真機做，結果寫進 SCG-4 報告；未驗如實標「未驗」）

| 編號 | 項 | 通過判準 |
|---|---|---|
| V36 | 首個帶四問的真實運轉（PRD §8.1 P5 (a)(b)(d)）；**前置：落地窗口內無到期的 (f)，且已依 §0 提交程序兩道防線** | 互動與無人運轉各一次：真審視者交卷、`fourq` 入帳；貼 `fourq.review` 事件行、`_fourq/<RUN>.md` 雜湊對帳、`si check` rc、迴圈層快照；無人那次見 CLI 在 `AUTOSDD_UNATTENDED=1` 下落地成功（驗治理檔禁寫守衛不攔 CLI 寫檔）；Q1／Q2 候選入 OBS 並在議題中心目視（附 sid）；零候選＝「無事件」，不得構造 |
| V37 | Console 零改動（(f)） | `AgentConsole/engine-bridge` 跑 `test_si_export_differential.py`（A、B 全綠）與 `test_si_deploy_config.py`；`tsc --noEmit`；`git diff --name-only <基準> -- AgentConsole .github` 為空；橫幅「其他欄位」目視 `fourq` |
| V38 | Q2-G 候選經掌舵者決定（(c)） | 加入者：經 T1、`added_by` 引掌舵者打字訊息 sid＋line、`research --fetch` 首跑、`research.sources` 綠；不加者：OBS 列處置終值並寫理由；零候選＝「未達成（前置未成立）」 |
| V39 | `FOURQ-NOT-RUN` 與 `missing_runs` 一致（(e)） | 真帳本 `si check` 輸出條數與 `si status` 的 `missing_runs` 逐一對上，貼兩份輸出 |

## 5. 本檔決策與待主控（⚖；裁決全文見 PRD 附錄 C.2 #24）

| 編號 | 問題 | 預設 |
|---|---|---|
| ⚖2 | 範本步 2 的項數上限（1、3）為靜態文字，與 `params.json` 可能漂移 | AT-444-1-1 釘兩者相等（D-EQA-10） |
| ⚖3 | `fourq_from_run` 初值 | D-EQA-15；AT-445-1-1 斷言「大於現有最大運轉號」 |
| ⚖4 | `CHECK_RULES_REV` 5→6、判準併入 `events.research` | 見 D-EFQ-18；再開：掌舵者要求四問單獨出項 |
| ⚖5 | 查詢重放以固定語料＋零／非零比對 | D-EQA-3；再開：掌舵者連續兩次指出「已涵蓋卻被列為沒想到」 |

**SCG-4 通過標準**：☐ 58 個 AT 全綠（開發期排除兩個範圍守衛；**commit 後在 tip 以預設基準重跑 `test_AT_440_8_1` 與 AT-445-5-1 驗綠**）且 P0～P4、議題中心既有 AT 全綠 ☐ `si check` rc 0（35 項、`CHECK_RULES_REV` 6、44 鍵、`status` 17 鍵、動詞 27、`KINDS` 25、`CAPABILITY` 62）☐ LOC 與 ruff、onboarding 基線、根層全套多 CPU 輸出貼入 ☐ **突變驗證（repo 外 worktree，不與主控並行動共用樹）**：`fourqparse` 標題逐字、`｜`／ASCII 管線判準與 Q4 反引號例外、項數上限、查詢綁定與零／非零比對、全文引用檢查、`gate_codes` 適用判斷與 `FOURQ-IS-PROPOSER`、`check` 順序判準、卡面 tail「兩欄皆有才渲染」、`loop` 快照不寫 `mea.*`、`unattended` 真值表 `fourq` 列、`patrolbrief` 四問逐字與舊範本 fail-closed、**步 0′ `FOURQ-NOT-RUN` 適用判斷**、`DEGRADE_TEXT` 呼叫形態（AT-444-2-1）、**`fourq_from_run` 整數比較（1000 對 999）**、無人環境 `--skip` 拒收（D-EQA-8）各至少一個並確認對應 AT 轉紅 ☐ 範圍守衛綠 ☐ V36～V39 如實標記 ☐ 重釘儀式於獨立 commit 收齊。

## 勘誤（本檔凍結之後的訂正；凍結前留空；日後勘誤單獨 commit）

- **勘誤一（2026-11-10，實作棒回報、主控裁決）AT-443-2-E-2 的級別**：原文要求 info 級 `FOURQ-NOT-RUN`、`check` rc 不變。改為 **warn** 級：`events.research` 項仍 PASS，rc 不變。WHY：`check.py` 的 info 若不在 `_NONBLOCKING`，該項會轉成 blocking NE（rc 2），而 `check.py` 不在 §3 允許集合。warn 達成同一意圖（不阻斷、看得見）。PRD AC-SI-43-2 的「資訊項」以本勘誤為準。
- **勘誤二（§2 站點補列）**：
  - `test_selfimproving_check.py` 的本地 `params_dict` 加三鍵。
  - `test_selfimproving_schedule_patrol.py::test_AT_438_2_1` 的斷言由「降載聲明」改為 `DEGRADE_TEXT` 前綴「降載聲明：額度帶」。WHY：新範本步 2 的靜態文字本身含「降載聲明」，free 帶也會命中。
  - `::test_AT_438_2_E_1` 的 `step6` 變體改為刪步 7，變體名改為 `step7`。WHY：新步 6 含 `<MAX_PROPOSALS>`，刪掉後與 `run` 變體同碼。
  - `p2_meta`、`schedule_model`、`console_obs` 等鍵數與動詞數的機械同步，屬 P5 同步，P4 各 AT 語意不變。
- **勘誤三（AT-441-3-2 與 PRD「固定語料」）**：`fourqparse.CORPUS` 是固定的檔名與 glob 樣式清單，因為缺陷帳本的 archive 無法逐檔列舉。「語料多放一個 archive 或備份檔不影響結果」改讀為「多放**不符清單樣式**的檔（例 `*.bak`、其他筆記檔）不影響結果」。審視者與 CLI 在入帳當下看到的是同一組檔（`fourq --corpus` 印出解析後的清單），所以兩者計數一致。
- **勘誤四（`loop` 格式；把 PRD §9.8.2 的「…」具體化）**：格式為 `M1=<status>(<值，.4g>,n=<N>);M4=<status>(<值>);M5a=NE(<理由 ≤24 字元>);M5b=…`。
  - status 取 `meastat` 的原值。
  - M4 沒有 n 時不帶 `n=`。
  - 整串為 ASCII，≤256 bytes。
- **勘誤五（AT-443-4-E-1，fail-closed）**：`fourq_from_run` 缺失或無效（非整數、布林、<1）時，`prop-new` 回 rc 1、碼 `FOURQ-PARAM-INVALID`。做法是 `gate_codes` 先判參數；`applicable()` 給 `check`／`status` 用，行為不變，無效參數由 `params.keys` 另判。WHY：`prop-new` 的 `PROP_KEYS` 不含 `fourq_from_run`（`writeverbs.py` 不在允許集合），否則參數一壞，閘門就靜默失效。AT 數不變，此變體併入 AT-443-4-E-1。
- **勘誤六**：`Q2-F0`（免掃）不計入 q2 項數。WHY：降載帶上限為 1 時，才容得下「免掃＋1 個來源缺口候選」。
- **勘誤七（細部）**：
  - `fourq --skip` 同樣要求同運轉已有研究事件。
  - 答案檔不存在或非 UTF-8 時 rc 3。
  - Q1 項的「做法」「機制」含 ASCII 管線字元時回 `FOURQ-PIPE`。
- **勘誤八（AT-445-5-1 的「無跳過類字樣」判準）**：限定為真正會跳過或預期失敗的寫法，即 `skipTest`／`skipIf`／`skipUnless`（需字界）、`unittest.skip`、`pytest.skip`、`mark.skip`、`SkipTest`、`xfail`。WHY：實作初版用 `skip[A-Z(]`，把 AT-443-1-1 函式名 `…_review_or_skip(self)` 裡的免審動詞誤判成跳過測試；開發期排除了這個 AT，到 tip 才紅。修法是收斂判準，函式名不改；正反各樣本已驗。
- **勘誤九（SCG-4 一審 P2-1，安全）AT-441-3-E-1：座標與工具路徑的逃逸判定**：
  - 範圍：座標（`<repo 檔>:<行>`）與 Q3 工具路徑共用同一個判定。
  - 判定時機：在任何檔案系統存取**之前**先做字面判定。下列情形一律拒收，回 `FOURQ-COORD-ESCAPE`：
    - 含 `..` 片段（以 `/` 或 `\` 切分）；
    - 以 `/` 或 `\` 開頭，含 UNC 的 `\\`、`//`；
    - 以磁碟代號開頭；
    - 含 NUL 或控制字元。
  - 字面判定通過後，再以 `resolve()` 確認路徑仍在 repo 根之下。
  - WHY：答案檔內容來自讀過外部來源的模型，可能被注入。UNC 路徑在 Windows 上會觸發 SMB 存取，可能外洩憑證；「座標所指那一行含查詢字串」判準也會變成探測 repo 外內容的手段。
  - AT 數不變，變體併入 AT-441-3-E-1。
