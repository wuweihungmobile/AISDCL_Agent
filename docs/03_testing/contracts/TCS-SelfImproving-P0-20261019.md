# Test Contract Specification — SelfImproving P0（觀察帳本定稿、一次性遷移、`check` 與協定目錄）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（PRD 與研究方法 SOP 於 Stage-1 凍結）的單一 Feature（P0 階段）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-001 |
| **Feature 名稱** | SelfImproving P0：觀察帳本定稿（九欄加檔頭 tz）、一次性遷移與豁免、唯讀檢查器 `tools/selfimproving.py check`、協定目錄 `SelfImproving_Protocol/`、Operations SOP 骨架 |
| **User Story** | US-001～US-005 |
| **建立日期** | 2026-10-19 |
| **QA 負責人** | SelfImproving P0 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝Developer 棒加主控〔D1、D2 的帳本編修〕，三方不同） |
| **FSM 功能鍵** | `monorepo-si-p0-ledger` |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（monorepo 根層；上位文件＝`docs/01_requirements/SelfImproving_PRD.md` 與 `docs/05_development/SelfImproving_Research_Methodology_SOP.md`，已於 Stage-1 凍結）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。**凍結檔不得再改**：本檔發現 PRD 需修訂之處，一律寫在交卷單，走掌舵者 T1／SPEC_REGRESSION_CHECK。

### FRD-lite

**現況與變更（Before／After；brownfield）**

- Before：(1) `docs/06_quality/SelfImproving_Observation_Ledger.md` 是八欄暫定版（ID、時間、情境、症狀、證據座標、分類、嚴重度、處置），處置為自由文字，時區只靠表頭一句話，沒有來源、回報者、面欄位，沒有機器檢查（HEAD 7b9c6ba6 現查 47 列，數字不構成契約）；(2) 缺陷帳本家族已有 `tools/check_defect_log_crossref.py` 與 `tools/tests/test_defect_id_reference_integrity.py` 兩把鎖，OBS 帳本不在其射程；(3) 沒有 `tools/selfimproving.py`、`tools/lib/si_*.py`、`docs/06_quality/SelfImproving_Protocol/`、`docs/05_development/SelfImproving_Operations_SOP.md`。
- After：九欄帳本（第 9 欄「標記」，檔頭機器可讀 `tz=`）、處置落入枚舉且原文逐字保全；單一遷移 commit 加掌舵者確認列加 `migration_base_sha` 的一次性豁免；唯讀檢查器 `check`（21 個判定項、四種 rc、判準指紋、可貼入的 OBS 草稿列）；協定目錄（`params.json`、`metrics.md`）；SOP 骨架（五角色任務書位置，擷取者節完整）；`tools/tests/test_selfimproving_check.py`。

**AC 編號規則**（ADR-XPLAT-016 §8.1 的 AC 文法是 `AC-[\d\-]+`，PRD 的 `AC-SI-NN-Y` 不合）：本檔以 `AC-0NN-Y` 對映 PRD（`AC-001-1`＝PRD `AC-SI-01-1`，`AC-029-2`＝`AC-SI-29-2`，其餘類推，共 13 個 PRD AC）。`AC-030-x`、`AC-031-x`、`AC-032-x` 為本檔自增（PRD 的 FR 只編到 29，無編號衝突），合計 19 個 AC。**自增 AC 的來源逐條標示，並區分「PRD 明文」與「本檔類推」**：AC-030-1 ← PRD §9.3 `check` 列（PRD:786）與 NFR-SI-09-1（PRD:531）；AC-030-2 ← §9.3 `check` 列的「只讀」欄（PRD:786）與 §9.4 的「CLI 不自寫 OBS 帳本」（PRD:836）；AC-030-3 的**草稿列**＝PRD §9.4（PRD:836）與 NFR-SI-09-3（PRD:533）明文，**判準指紋＝本檔類推**（PRD 只在量測腳本列 PRD:800 與五問協定先例 `tools/probe/fivequestion_ledger.py` 定義指紋，`check` 列 PRD:786 沒有此句；任務書 D4 要求 `check` 輸出判準指紋，算法沿用 PRD:800 的「協定目錄各檔 CRLF 轉 LF 後雜湊加 `metrics_rev`」，`check_rules_rev` 為本檔類推，請掌舵者知悉）；AC-031-1 ← §9.1 C5 列（PRD:658）、§9.3 `check` 列的 params 對表句（PRD:786）、NFR-SI-02-1（PRD:491～494）、PRD:857；AC-031-2 ← C5 列的「指標定義」（PRD:658）與 §1.3（PRD:62～66、70～79）；AC-032-1 ← §9.1 C6 列（PRD:659）、NFR-SI-07-2（PRD:524）。

**P0 交付物**（D1～D6）

| 編號 | 交付物 | 路徑（相對 monorepo 根） | 製作者 | 主要驗證 |
|------|--------|--------------------------|--------|----------|
| D1 | 觀察帳本定稿與一次性遷移 | `docs/06_quality/SelfImproving_Observation_Ledger.md`（改）；`docs/05_development/SelfImproving_Observation_Ledger_notes.md`（新，附註檔；被 NFR-SI-02-1 (iv) 既有的實體 glob `docs/05_development/SelfImproving_*.md` 涵蓋，不必改 PRD） | 主控（帳本單一窗口，PRD C1） | 實跑檢核 V1～V3，與 V2 的 `check` |
| D2 | 遷移豁免 | `docs/06_quality/SelfImproving_Protocol/params.json`（改一個鍵）；帳本（追加一列） | 主控 | 實跑檢核 V4、V5；§2 的遷移鏈 AT |
| D3 | 協定目錄 | `docs/06_quality/SelfImproving_Protocol/params.json`、`docs/06_quality/SelfImproving_Protocol/metrics.md`（新） | Developer | §2 的 AC-031 系列 AT；實跑檢核 V6 |
| D4 | 檢查器 | `tools/selfimproving.py`（入口薄殼）、`tools/lib/selfimproving/*.py`（套件；2026-10-19 自 `tools/lib/si_*.py` 搬入，見末尾〈搬遷勘誤〉）（新） | Developer | §2 的 AC-001、002、004、030、031 系列 AT |
| D5 | SOP 骨架 | `docs/05_development/SelfImproving_Operations_SOP.md`（新） | Developer（文件作者） | §2 的 AC-032 與流程型 AT；實跑檢核 V8 |
| D6 | 測試 | `tools/tests/test_selfimproving_check.py`（新） | Developer | 本檔全部 AT |

**提交順序與責任**（PRD §9.6 P0 列：遷移 commit 與寫入該 sha 的 commit 是兩個 commit，commit 不能引用自己的 sha）

- **T**（Developer；D3、D4、D5、D6）→ **M**（主控；D1：單一 commit，只動帳本與附註檔）→ **N**（主控；D2：把 M 的完整 sha 寫入 `params.json` 的 `migration_base_sha`，並於帳本追加一筆掌舵者確認的 `decided` 列）。T 之前真帳本還是八欄、`check` 對真帳本必紅（預期）；M 之後、N 之前 `check` 仍紅（未豁免，預期）；N 之後 `check` 對真帳本須為綠（實跑檢核 V2）。
- 真帳本只由主控寫（PRD C1「他人只讀」）；Developer 棒不得碰真帳本與真附註檔；遷移腳本若有，放 scratchpad、不入庫。
- 確認列的引言取自掌舵者逐字稿的人工載體（`type` 為 `user` 且 `origin.kind` 為 `human`，或 `queued_command` 附件；PRD Q11），座標 `sid` 加 `line`（jsonl 的 1 起算實體行號）。P0 只記錄、不機械驗引言（引言回查屬 P2，AC-SI-12-4）；QA 在實跑檢核 V5 以逐字稿現查。
- **帳本更新慣例**（預審 F-04、二審 N-03）：M 之前（遷移基準以前）的原地改寫——例如 OBS-SI-011 的累計次數、時間欄更正——依 AC-SI-01-3 屬遷移豁免涵蓋的歷史，不比對；**M 之後帳本除處置欄 `open`→終值一次（PRD:223、AC-SI-04-3）外，一律追加列**（累計、狀態更新與更正都用追加列，更正列標 `rel=corrects:<ID>`；處置欄 `open`→終值一次是 PRD 明許的唯一原地改寫，與 R20 的放行集合一致），其餘原地改寫即 `ROW-MUTATED`；SOP 擷取者節須載明（R25 (9)，含此例外），實跑檢核 V9 於 N 之後至 SCG-4 前驗收。主控宜在 M 之前把 OBS-SI-011 這類累計欄改成追加或「現查」形態，免得 M 之後的慣性原地改寫使 V2 轉紅。

**〈P0 行為規則〉**（R1～R26；各 AT 以 R 編號引用；判定碼見其後的〈判定碼表〉）

*A. 介面與輸出*

- **R1 介面與 rc**：`python tools/selfimproving.py check [--repo <dir>] [--ledger <file>] [--params <file>] [--json]`。`main(argv: list[str] | None = None) -> int` 回傳 rc、不呼叫 `sys.exit`（argparse 的 `SystemExit` 在 `main` 內攔截並轉成回傳值）；檔尾 `if __name__ == "__main__": sys.exit(main())`；檔首 `import _stdio_utf8  # noqa: F401`（`tools/_stdio_utf8.py` 是 stdout／stderr 強制 UTF-8 的唯一實作，本工具不得另寫 `.reconfigure(` 站點，根層去重鎖 `tools/tests/test_platform_utils_dedup.py` 會紅）。P0 只有 `check` 一個動詞；其他動詞名（含 PRD §9.3 列為後續階段的 `status`、`prop-new` 等）一律視為未知動詞。**rc 表**：`0`＝無 FAIL 且無 blocking NE；`1`＝至少一項 FAIL；`2`＝無 FAIL、至少一項 blocking NE；`3`＝檢查器無法執行（用法錯誤、未知動詞、`--repo` 不是目錄、`--ledger` 或 `--params` 不存在、不是檔案、不可讀、非 UTF-8、`params.json` 不是 JSON 物件），此時 stdout 為空、stderr 至少一行理由。`--help` 與 `check --help`：rc 0，usage 走 stdout 並列出 `check`（`check --help` 另列四個旗標）。rc 3 刻意與 argparse 預設的用法錯誤碼 2 分開：本工具的 2 專指「未判」。
- **R2 路徑**：`--repo` 預設 `Path(__file__).resolve().parents[1]`；`--ledger` 預設 `<repo>/docs/06_quality/SelfImproving_Observation_Ledger.md`；`--params` 預設 `<repo>/docs/06_quality/SelfImproving_Protocol/params.json`；`--ledger`／`--params` 給相對路徑時相對於 `--repo`（不是 cwd）。其餘固定相對 `--repo` 的路徑為常數、P0 不提供旗標：PRD `docs/01_requirements/SelfImproving_PRD.md`、根 `CLAUDE.md`、缺陷帳本家族與 OBS 附註檔／封存檔（R18）、協定目錄 `docs/06_quality/SelfImproving_Protocol/`（R7）。
- **R3 文字形態**：stdout（UTF-8、LF）依序為：(1) 首行 `si-check rows=<N> items=21`（N＝R9 解析到的資料列數）；(2) 每個判定項一行 `<PASS|FAIL|NE> <item_id>`，NE 行在項目 ID 之後加一個空白與 `blocking` 或 `nonblocking`，該項的項目層 `detail` 非空時在行尾接 ` # <detail>`（行文法 `^(PASS|FAIL|NE) ([a-z_]+\.[a-z_]+)(?: (blocking|nonblocking))?(?: # (.*))?$`），項序固定（見碼表）；(3) 該項的 finding 逐行縮排兩個空白：`  <subject> <CODE> <detail>`（subject 是列 ID、`L<行號>`、參數名或 `-`；level 為 warn 者 detail 以 `[warn]` 起頭；列層級 finding 的 detail 須含所涉欄的中文欄名，例如 `分類`、`處置`、`證據座標`、`時間`；`ROW-MUTATED` 的 detail 須含 `掌舵者` 字樣，提示要求掌舵者過目）；PASS 項除 warn 外不印 finding；(4) `overall=<PASS|FAIL|NE> rc=<n> fingerprint=sha256:<64 位小寫 hex>`；(5) rc 不為 0 時其後接一行 `obs-draft:` 與一行 OBS 草稿列（R6）。
- **R4 JSON 形態**：`--json` 時 stdout 只有一個 JSON 物件加換行（`json.dumps(..., ensure_ascii=False)`），鍵序為 `overall`、`rc`、`fingerprint`、`fingerprint_parts`（鍵 `manifest`、`metrics_rev`、`check_rules_rev`）、`rows`、`items`、`obs_draft`；`fingerprint_parts`、`items` 的元素、`findings` 的元素的鍵序亦依下列所列順序。`items` 是 21 個物件，依碼表順序，各含 `id`、`status`、`blocking`、`detail`（項目層的說明字串，多數項為空字串；只有 `history.migration` 與 `history.row_mutated` 另有指定，見 R19、R20）、`findings`；`findings` 的元素含 `subject`、`code`、`level`（`fail`、`warn`、`info` 之一；NE 項的 finding 為 `info`）、`detail`。`blocking` 只有 NE 項可為 true，其餘恆為 false；`obs_draft` 是草稿列字串，rc 為 0 時是 null。文字形態與 JSON 形態的 rc、項狀態、finding 集合必須一致。
- **R5 狀態語意**：每項狀態恆為 PASS、FAIL、NE 三者之一：有任一 `fail` 等級的 finding ⇒ FAIL；否則命中碼表的任一 NE 碼 ⇒ NE；否則 PASS。NE 分兩類：**nonblocking**（只有 `ref.carrier_families` 的 `CARRIER-NOT-ESTABLISHED`：PRD AC-SI-04-1 規定載體尚未建立的 ID 家族要印「未判」、不得判通過也不得判不合規，而 P0 退出條件 (b) 要求 `check` 綠，所以這類 NE 不影響 rc）與 **blocking**（其餘 NE 碼）。overall：任一 FAIL ⇒ FAIL、rc 1；否則任一 blocking NE ⇒ NE、rc 2；否則 PASS、rc 0（nonblocking NE 照印）。**取不到判準輸入＝NE，不以內建預設值頂替**：某項所需的 `params.json` 鍵缺失或型別不符時，該項為 blocking NE（碼 `SOURCE-UNAVAILABLE`），並由 `params.keys` 另報 FAIL。
- **R6 OBS 草稿列**（PRD §9.4：任何階段失敗，CLI 非零 rc 並印可貼入的 OBS 草稿列；CLI 不自寫 OBS 帳本）：rc 不為 0 時印恰一行九欄 Markdown 列——ID＝`OBS-SI-` 接（帳本現有合法 ID 數值最大者加一，至少三位、零補齊；帳本沒有列則 001）；時間＝現在的本機時間，格式 `YYYY-MM-DD HH:MM ±HH:MM`（`datetime.now().astimezone()`，不得持久化或輸出無 offset 的時間）；情境＝`si check（自動草稿）`；症狀＝`si check 判 <overall>（rc=<n>）：` 接至多 5 個非 PASS 項的 item_id（依碼表順序、以「、」連接），超過 5 項尾接 `…等 <k> 項`（k 為非 PASS 項總數）；證據座標＝反引號包住 `python tools/selfimproving.py check` 之後接 ` rc=<n>；判準指紋 sha256:<前 12 位 hex>`；分類＝`bug`（PRD NFR-SI-09-3：迴圈任一階段失敗都留一筆分類 `bug` 的 OBS，見 PRD:533、PRD:1040、PRD:321；§9.4 的草稿列規則綁在其上，PRD:836）；嚴重度＝`P3`；處置＝`open`；標記＝`面=流程;來源=工具;回報者=si-check`。草稿列本身必須通過 R9～R17 的全部逐列判準，且位元組數不超過 `row_max_bytes`。
- **R7 判準指紋**（本檔類推：PRD 只在量測腳本列〔PRD:800〕與五問協定先例定義指紋，`check` 列〔PRD:786〕沒有此句；任務書 D4 要求 `check` 輸出判準指紋，見〈AC 編號規則〉）：`manifest`＝先例 `tools/probe/fivequestion_ledger.py` 的 `manifest_sha` 算法逐字沿用於協定目錄：該目錄下（遞迴）每個檔名不以 `.` 開頭的檔，取（相對協定目錄的 POSIX 路徑, sha256 十六進位字串〔內容先把 CRLF 換成 LF〕）、依路徑排序成清單，對 `json.dumps(清單, ensure_ascii=False)` 的 UTF-8 位元組取 sha256 的 64 位小寫 hex；`metrics_rev`＝`params.json` 的同名鍵值（缺失或型別不符＝null）；`check_rules_rev`＝工具內的整數常數（初值 1；`check` 判準語意變動時人工 bump，先例：量測碼不入 manifest）。`fingerprint`＝`sha256:` 接 `json.dumps({"check_rules_rev":…, "manifest":…, "metrics_rev":…}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` 的 UTF-8 位元組之 sha256 hex。指紋只隨「判準」變（協定目錄任一檔內容、`metrics_rev`、`check_rules_rev`），不隨帳本資料、工作樹其他檔或 git 狀態變。
- **R8 純度與零副作用**：(a) 只讀：不建立、修改、刪除任何檔案或目錄（含暫存檔、`.lock`），不寫 OBS 帳本；(b) 只用標準庫與 repo 內本地模組（`_stdio_utf8`、`lib.*`），不連網；(c) 唯一的子行程是 `git`，一律經 `subprocess.run`（不直接用 `Popen`、`check_output`、`os.system`），每個呼叫：`shell` 不為真；argv 以 `git`、`-C`、`<--repo 的解析後路徑>` 起頭；帶 `encoding="utf-8"` 與 `errors="replace"`；帶正數的 `timeout`（建議 60 秒）；子行程環境（以 `env` 引數明給）移除 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE`、`GIT_COMMON_DIR`、`GIT_PREFIX`、`GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES` 並設 `GIT_OPTIONAL_LOCKS=0`；列舉路徑的 git 呼叫一律帶 `-c core.quotepath=false`（根層鎖 `TestGitPathEnumerationIsQuotepathSafe`）；git 不可用（找不到執行檔、`--repo` 不是 git 工作樹、逾時）⇒ 需要 git 的項目為 blocking NE（碼 `GIT-UNAVAILABLE`）；(d) 所有文字檔讀寫帶 `encoding="utf-8"`；(e) 不持久化或輸出 naive 時間戳。

*B. 帳本解析與逐列判準*

- **R9 列識別與切分**：檔案以 UTF-8 讀（開頭 BOM 容許），以 `\n` 切行，每行尾端單一 `\r` 剝除（CRLF 容許）。**檔頭 tz 宣告**：整檔中符合 `^<!--\s*si-ledger:\s*(.*?)\s*-->\s*$` 的行；有效宣告的內容須含 `tz=<offset>`（offset 文法見 R10）；宣告行有兩個以上，或唯一的宣告內容不合法 ⇒ `TZ-HEADER-MALFORMED`，且這兩種情形都視同沒有宣告（宣告行為零個是合法的，此時每列時間都須自帶 offset）。**表頭列**＝第一個符合 `^\|\s*ID\s*\|` 的行，其欄名序列（strip 後）須恰為 `ID`、`時間`、`情境`、`症狀`、`證據座標`、`分類`、`嚴重度`、`處置`、`標記`，找不到或不符 ⇒ `HEADER-COLS`（subject 為 `-`）。**資料列**＝(1) 檔內所有符合 `^\|\s*OBS-SI-` 的行；加上 (2) 表頭列之後連續（直到空行或不以 `|` 起頭的行為止）、以 `|` 起頭、非表頭列、非分隔列的其餘行（subject 記為 `L<1 起算的行號>`，其 ID 欄視為不合法 ⇒ `ROW-ID-FORMAT`）。(1) 類資料列的 subject 取其 ID 儲存格原字串；ID 不合法的資料列，其餘逐列判準照常評估。分隔列＝各格皆符合 `:?-{3,}:?`。**欄切分**：行須以 `|` 起頭並以 `|` 結尾（否則 `ROW-ARITY`），去掉首尾的 `|` 後以「未被反斜線跳脫的 `|`」切開；`\|` 在格內還原為字面 `|` 且不切；各格 strip；未跳脫的 `|` 即使包在反引號內也照切（先例：`tools/check_defect_log_crossref.py` 的 `row_arity_problems`）。欄數須為 9，否則 `ROW-ARITY`；欄數不是 9 的列只報 `ROW-ARITY` 與以整行文字判定的 `ROW-BYTES-OVER`、`CTRL-CHAR`，不做其餘依欄位的判準（無法對齊欄位）。**ID**：須符合 `^OBS-SI-\d{3,}$`，否則 `ROW-ID-FORMAT`，且該列（含 (2) 類資料列的空或不合法 ID 欄）**不參與**下列 `ROW-ID-DUP`、`ROW-ID-ORDER` 的追蹤——不加入已見集合、不更新最大值、不做整數轉換；格式合法的列依檔內出現順序逐列判定：ID 已出現過 ⇒ `ROW-ID-DUP`（第二次起每次一筆）；否則數值（`int`）不大於此前出現過的最大數值 ⇒ `ROW-ID-ORDER`；否則更新最大值（可跳號、嚴格遞增）。
- **R10 時間文法**：時間格（strip 後）須整串符合下列正規式，且起點能以 `datetime(年, 月, 日, 時, 分, 秒或0)` 建構（排除 2026-02-30、24:00 這類假日期），否則 `TIME-FORMAT`；起點帶 offset 者列內明示優先於檔頭；起點不帶 offset 且檔頭沒有有效 tz ⇒ `TIME-NO-TZ`；格式不合者不再判 `TIME-NO-TZ`。區間的迄點不帶 offset 時沿用起點。

```text
START = (\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?(?: ?([+-](?:0\d|1[0-4]):[0-5]\d))?
END   = (?:(?:\d{4}-)?\d{2}-\d{2} )?\d{2}:\d{2}(?::\d{2})?(?: ?[+-](?:0\d|1[0-4]):[0-5]\d)?
CELL  = ^START(?:[～~]END)?$
```

- **R11 位元組與控制字元**：列位元組＝去掉行尾 `\n` 與單一行尾 `\r` 之後 `len(line.encode("utf-8"))`；大於 `row_max_bytes` ⇒ `ROW-BYTES-OVER`（恰等於不算超）。資料列內任何碼位小於 0x20 的字元（含 TAB、NUL、ESC、行中的單獨 CR）或等於 0x7f ⇒ `CTRL-CHAR`（行尾的單一 `\r` 不算）。
- **R12 必填欄**：時間、情境、症狀、證據座標、分類、嚴重度、處置共 7 欄（ID 另依 R9）；strip 後為空，或為佔位值 `-`、`—`、`TBD`、`N/A`（不分大小寫）⇒ `FIELD-EMPTY`（detail 含欄名）。某欄已報 `FIELD-EMPTY` 者，不再就該欄報其他碼。
- **R13 分類、嚴重度、處置**：分類須為 `process`、`bug`、`tooling`、`doc`、`decision` 之一，嚴重度須為 `P1`～`P4` 之一（區分大小寫），否則各報 `ENUM-CATEGORY`、`ENUM-SEVERITY`。處置文法如下：首詞須命中 `DISP_TOKEN`，且 `fixed@…`、`DEF-…`、`merged@…`、`proposed@…` 四種首詞字串還須整串符合其後對應的正規式，任一不符 ⇒ `DISP-ENUM`；`deferred`、`retired`、`decided` 的附加文字（首詞之後去掉前導分隔字元〔`：`、`:`、`（`、`(`、`；`、`;`、`，`、`,`、空白〕所餘）為空，或 `retired` 的附加文字不含任何 R16 座標形態 ⇒ `DISP-TEXT-MISSING`；處置格內出現字面「之後再看」（任何位置、任何首詞）⇒ `DISP-DEFER-LATER`（與其他碼並存，同一格只報一次）。

```text
DISP_TOKEN = ^(open|deferred|retired|decided|fixed@\S+?|DEF-\S+?|merged@\S+?|proposed@\S+?)(?=$|[：:（(；;，,\s])
FIXED_SHA  = ^fixed@[0-9a-f]{7,40}$
DEF_ID     = ^DEF-\d+-\d+$
MERGED     = ^merged@OBS-SI-\d{3,}$
PROPOSED   = ^proposed@PROP-SI-\d{3,}$
```

- **R14 標記欄**：格內以「引號外的 `;`」切成片段；空片段（含結尾 `;`）略過；每個片段須為 `鍵=值`（以第一個 `=` 分鍵與值，各自 strip），值為空、片段無 `=`、同鍵重複、引號值未以對應的結尾引號收尾 ⇒ `MARK-SYNTAX`；值可為引號字串（`"…"`，內含 `"` 寫 `\"`、`\` 寫 `\\`）或不含 `"` 與 `;` 的裸值；引號字串須逐字元掃描解析（遇 `\` 連同下一字元視為一個跳脫對，以第一個未跳脫的 `"` 為結尾，且它必須是該值的最後一個字元；以跳脫反斜線結尾的字串如 `"…\\"` 是合法的，切分片段時引號內的 `;` 不切）。鍵須屬封閉詞彙 `面`、`暴露`、`來源`、`外部衍生`、`回報者`、`根因`、`rel`、`reopens`、`orig`、`span`，否則 `MARK-UNKNOWN-KEY`。值域：`面`∈{守衛, 產品, 文件, 流程}；`暴露`∈{a, b, c, 無}；`外部衍生` 只能是 `是`；違反 ⇒ `MARK-VALUE`。`orig` 的值須為引號字串，或 `@<路徑>#OBS-SI-<數字>`（路徑不含空白與 `#`），否則 `MARK-ORIG-FORMAT`。`根因`、`rel`、`reopens`、`span`、`回報者` 的值只要求非空。**值空的鍵視為缺鍵**（下游判準同缺鍵）。`面` 為每列必備，缺 ⇒ `MARK-FACE-MISSING`。
- **R15 面、暴露、來源、回報者**：`面` 為 `守衛` 時 `暴露` 必備，缺 ⇒ `GUARD-NO-EXPOSURE`；`面` 為 `守衛` 且嚴重度為 `P1` 或 `P2` 時 `暴露` 須為 a、b、c 之一，為 `無` ⇒ `GUARD-P12-NO-EXPOSURE`（PRD AC-SI-01-2：這類列應降為 P4 並入理論洞清單；「附座標」由該列證據座標通過 R16 承擔）；`面` 不是守衛者不受暴露規則約束。`來源` 必備且須為 `人`、`代理`、`工具`、`逐字稿`、`帳本` 之一，缺 ⇒ `SOURCE-MISSING`、值不在詞彙 ⇒ `SOURCE-VALUE`；`回報者` 必備，缺 ⇒ `REPORTER-MISSING`。
- **R16 證據座標可定位形態**（規範性；只驗「形態」，不驗該檔或該行是否真的存在，見 §4 刻意不做）：證據座標格須命中下列九種之一，否則 `COORD-NONE`。PRD:220 只列四形態（檔案:行、指令＋rc、sid＋seq、帳本列 ID）；本檔放寬為九形態的理由、真帳本實測與替代見 §7 Q6；其中 `sid` 形態比照 PRD 要求帶 `line=N` 或 `seq=N`（範圍以下列正規式為準：UUID 之後 40 字元內、不跨 `；`、`;`、`、`；`line`、`seq` 之後可接 `=`、`:` 或空白，與 R19 (d) 的 `line` 語法一致；裸 sid 不算）；`sha` 形態的前後邊界都排除連字號，故 UUID 的任一段（含第一段）不會被當成 sha 放行（二審 N-01）；短 sid 前綴與縮寫 sha 同形，`check` 無從區分，照 `sha` 形態過關。

```text
path   = (?<![\w.])(?:[A-Za-z0-9_.%\-]+[/\\])+[A-Za-z0-9_.%\-<>*{}\[\]]+\.[A-Za-z0-9]{1,8}(?::\d+(?:[–-]\d+)?)?
file   = (?<![\w./\\-])[A-Za-z0-9_.\-]+\.(?:md|py|json|jsonl|yaml|yml|ps1|sh|bash|toml|ts|tsx|js|mjs|java|xml|txt|log|html|css|cfg|ini|lock|patch|csv|tla)(?![A-Za-z0-9])(?::\d+(?:[–-]\d+)?)?
dir    = (?<![\w./\\-])(?:docs|tools|AutoClaude|AISDLC_SDD|AgentConsole|\.claude|\.github)/[^\s、，；）)`]*
sha    = (?<![0-9A-Za-z-])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![0-9A-Za-z-])
sha_kw = (?i:commit|sha)\s*[:=]?\s*[0-9a-f]{7,40}(?![0-9A-Za-z])
sid    = [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[^；;、\n]{0,40}?(?i:line|seq)\s*[:=]?\s*\d+
id     = (?<![A-Za-z0-9-])(?:(?:OBS|ATT|PROP|DEC|APP|MEA|RUN)-SI-\d{3,}|DEF-\d+-\d+)(?![0-9A-Za-z])
cmd    = `(?:python3?|py|git|powershell|pwsh|bash|sh|pytest|ruff|lint-imports|node|npm|npx|docker|gh|claude|uv)\b[^`]*`
docref = §\s?\d|(?:SOP|PRD|TCS|FRD|SRD|BRIDGE|ADR-[A-Z]+-\d+)\b[ \t]*[§\w.\-]*\d
```

- **R17 `fixed@<sha>`**：處置首詞符合 `FIXED_SHA` 者，以 `git rev-parse --verify --quiet <sha>^{commit}` 解析，rc 非 0 ⇒ `FIXED-SHA-UNRESOLVED`（物件存在但不是 commit 亦同）；格式不符者已由 R13 報 `DISP-ENUM`，不進解析。有 `fixed@` 列而 git 不可用 ⇒ blocking NE `GIT-UNAVAILABLE`；沒有 `fixed@` 列則本項不需要 git。

*C. 引用完整性*

- **R18 引用完整性**：(a) **OBS 引用**：主鍵集合＝`--ledger` 與 `docs/06_quality/SelfImproving_Observation_Ledger_archive*.md`（若存在）各檔中符合 `^\|\s*(OBS-SI-\d+)\s*\|` 的列首格；提及＝`git -c core.quotepath=false grep -I -n --untracked -E` 在整個 repo（含未追蹤但未被忽略的檔）找到的 `OBS-SI-[0-9]+`，但帳本與封存檔中「列首格」那一處是定義、不算提及；每個不在主鍵集合內的 ID 報一筆 `OBS-REF-DANGLING`（subject 為該 ID；同 ID 多處提及只報一筆，detail 列至多 5 處 `<相對路徑>:<行號>`，其餘以 `…+<k>` 表示）。(b) **DEF 引用**：處置首詞符合 `DEF_ID` 者，其 ID 須是下列檔案的列首格主鍵之一（`^\s*\|\s*(DEF-\d+-\d+)\s*\|`，先例 `tools/tests/test_defect_id_reference_integrity.py`）：`docs/06_quality/AutoSDD_Defect_Log*.md`（含 `_archive_*`）、`docs/06_quality/AutoSDD_External_Blocked_Log.md`、`docs/06_quality/AutoSDD_Structural_Debt_Log.md`；不在內 ⇒ `DEF-REF-DANGLING`（subject 為列 ID）；有 DEF 引用而上述檔案一個都不存在 ⇒ blocking NE `SOURCE-UNAVAILABLE`。(c) **orig 附註檔**：標記含 `orig=@<路徑>#<ID>`（語法合格）的列，路徑解析在 `--repo` 之下（絕對路徑或含 `..` 逃出 repo 視同不存在）；檔不存在 ⇒ `ORIG-NOTES-MISSING`；檔存在但沒有符合 `^#{2,6}\s+<ID>\b` 的標題，或 `<ID>` 不等於該列自己的 ID ⇒ `ORIG-NOTES-ANCHOR`。(d) **載體尚未建立的家族**：`git grep` 找到 `(ATT|PROP|DEC|APP|MEA|RUN)-SI-[0-9]+` 提及者，本項為 NE（nonblocking，碼 `CARRIER-NOT-ESTABLISHED`，detail 為 `families=<以字母序、逗號分隔的家族前綴> count=<提及總數，以符合的出現次數計、非行數>`）；沒有任何提及則 PASS。P0 不重放事件帳本，載體是否存在一律不判。(e) `ref.obs`、`ref.carrier_families` 需要 git，git 不可用時為 blocking NE `GIT-UNAVAILABLE`。

*D. 歷史比對（遷移豁免與 ROW-MUTATED）*

- **R19 遷移豁免**：讀 `params.json` 的 `migration_base_sha`（缺鍵或 null＝沒有宣稱，本項 PASS、項目層 `detail` 為 `claim=none`）。有宣稱時下列 (a)～(d) 須依序成立，否則 `history.migration` 為 FAIL 並視為未豁免（只報依序第一個不成立者；`MIG-SHA-*` 的 subject 為 `migration_base_sha`，`MIG-CONFIRM-MISSING` 的 subject 為 `-`）：(a) 值符合 `^[0-9a-f]{40}$`，否則 `MIG-SHA-FORMAT`（縮寫、大寫皆不合）；(b) `git rev-parse --verify --quiet <sha>^{commit}` rc 為 0，否則 `MIG-SHA-UNRESOLVED`（物件不存在或不是 commit）；(c) `git merge-base --is-ancestor <sha> HEAD` rc 為 0，否則 `MIG-SHA-NOT-ANCESTOR`；(d) 帳本中存在一列**掌舵者確認列**，否則 `MIG-CONFIRM-MISSING`：處置首詞為 `decided`、整列文字含該 sha 的前 7 位（不分大小寫）、並且含 `sid` 與一個 UUID（`sid\s*[:=]?\s*[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}`，不分大小寫）與 `line` 加一個整數（`line\s*[:=]?\s*\d+`，不分大小寫）——P0 只驗存在與格式、不驗引言。四條皆成立 ⇒ 該項 PASS、項目層 `detail` 為 `claim=valid`，並稱此遷移**已豁免**。已豁免時另有：(e) `orig` 鍵只准出現在「遷移當下已存在的列」（以 `git show <sha>:<帳本相對路徑>` 的 ID 集合為準）；之後才新增的列帶 `orig` ⇒ `ORIG-OUTSIDE-MIGRATION`（subject 為該列 ID；未豁免時不評 (e)）。git 不可用而有宣稱 ⇒ blocking NE `GIT-UNAVAILABLE`。
- **R20 ROW-MUTATED**：帳本相對於 `--repo` 的 POSIX 路徑記為 P（帳本不在 repo 內 ⇒ blocking NE `SOURCE-UNAVAILABLE`）。**基準 B**：已豁免（R19）則 B＝`migration_base_sha`；否則（沒有宣稱、宣稱無效、或缺確認列）B＝`git log --first-parent --reverse --format=%H -- <P>` 的第一個 commit；沒有任何 commit 動過 P ⇒ 只有工作樹一個版本、無歷史可比，本項 PASS（項目層 `detail` 為 `no-history`）。**版本序列**：B 當時的帳本內容；加上 `git log --first-parent --reverse --format=%H <B>..HEAD -- <P>` 的各 commit 當時的內容（`git show <commit>:<P>`）；加上工作樹內容（若與 HEAD 的內容不同，或 P 在 HEAD 不存在）。各版本內容先把 CRLF 換成 LF，以 R9 的列識別取出各列、依 ID 對照（版本內重複的 ID 取第一次出現者）。**逐對比較**（相鄰兩版本）：前版有、後版沒有的 ID ⇒ `ROW-MUTATED`（cause=`deleted`）；兩版都有但格內容（各格 strip、`\|` 還原後逐格相等，格數須相同）有差異者，**只有**同時滿足下列三條才放行：前版處置首詞為 `open`、後版處置首詞不是 `open`、其餘各格逐格相等（含第 9 欄）；否則 ⇒ `ROW-MUTATED`（cause=`changed`）。後版新出現的 ID 是追加，放行。每筆 finding 的 subject 為該 ID，detail 含 `commit=<引發差異的 commit 短 sha，或工作樹的 WORKTREE>`、`cause=<deleted 或 changed>` 與 R3 要求的 `掌舵者` 字樣。更正一律走追加更正列（標記 `rel=corrects:<ID>`），這是遷移以外唯一的更正機制。**誠實劃界**（PRD AC-SI-04-3）：工作樹內未提交的多步改寫無歷史可比，只看工作樹與 HEAD 的淨差異（淨差異為 open 轉終值一次者放行）；事件帳本的比對屬 P1。

*E. 協定參數、體積與反空轉*

- **R21 `params.json` 對表**：頂層須為 JSON 物件，必備鍵＝下表 23 鍵（與 PRD 的 `UPPER_SNAKE` 參數一對一，另含 PRD 在 C5 列點名但未取名的三項〔`min_obs_rows`、`ledger_warn_bytes`、`ledger_fail_bytes`〕與 `metrics_rev`、`migration_base_sha`、兩個 glob 清單）。缺鍵 ⇒ `PARAM-MISSING`、型別不符 ⇒ `PARAM-TYPE`（布林不算整數與數值）、超出範圍 ⇒ `PARAM-RANGE`（subject 皆為鍵名）。**多出的鍵不判紅**：PRD:786 只要求「PRD 引用的參數名須存在」，多鍵檢查沒有 PRD 依據、且會擋住 P1、P2 加鍵（須先改本檔），故不設未登記鍵的判定碼；D3 交付當下恰為這 23 鍵，由實跑檢核 V6 核對。「初值」欄是 D3 提交當下的值（`check` 與 AT 不斷言值，避免掌舵者調參後測試過期；V6 在提交當下一次性核對）；P1、P2 才用到的參數（沙盒逾時、寫入鎖逾時、事件數下限等）由各階段的 TCS 擴充登記表。

| 鍵 | 型別 | 範圍 | 初值 | PRD 座標與備註 |
|----|------|------|------|----------------|
| `row_max_bytes` | 整數 | ≥ 1 | 700 | PRD:224、646 |
| `w_n` | 整數 | ≥ 1 | 20 | PRD:62 |
| `w_min` | 整數 | ≥ 1 | 5 | PRD:62、368 |
| `w_evt` | 整數 | ≥ 1 | 2 | PRD:38、62、658 |
| `w_opp` | 整數 | ≥ 1 | 5 | PRD:373；R22 耦合 |
| `max_proposals_per_run` | 整數 | ≥ 1 | 3 | PRD:302、481 |
| `max_revisions` | 整數 | ≥ 1 | 2 | PRD:246、481 |
| `churn_max` | 整數 | ≥ 1 | 2 | PRD:387、486 |
| `min_heldout` | 整數 | ≥ 1 | 5 | PRD:357 |
| `max_touch_ratio` | 數值 | 大於 0 且 ≤ 1 | 0.2 | PRD:298 |
| `max_new_entries` | 整數 | ≥ 1 | 3 | PRD:298 |
| `stop_after_bad` | 整數 | ≥ 1 | 2 | PRD:377、486 |
| `cap_frac` | 數值 | 大於 0 且 ≤ 1 | 0.9 | PRD:391 |
| `max_archive_entries_per_card` | 整數 | ≥ 1 | 50 | PRD:298、658、831 |
| `card_line_max` | 整數 | ≥ 1 | 100 | PRD:326 |
| `event_max_bytes` | 整數 | ≥ 1 | 2000 | PRD:528、658 |
| `metrics_rev` | 整數 | ≥ 1 | 1 | PRD:658、800；PRD 未給值，SA 決定 1 |
| `min_obs_rows` | 整數 | ≥ 1 | 10 | 反空轉下限，PRD:658、733；名稱與初值由本檔定（開放問題） |
| `ledger_warn_bytes` | 整數 | ≥ 1 | 245760 | 體積警戒線 warn，PRD:528、658；名稱由本檔定；先例 `tools/check_defect_log_crossref.py` 的 240 KiB |
| `ledger_fail_bytes` | 整數 | ≥ 1 | 262144 | 體積警戒線 fail（256 KiB，PRD:528）；名稱由本檔定 |
| `migration_base_sha` | 字串或 null | 字串時須為 40 位小寫 hex（由 R19 判，非本項） | null（D2 前） | PRD:257、658 |
| `spec_body_globs` | 字串陣列 | 非空 | `**/docs/01_requirements/**`、`**/docs/02_architecture/**`、`**/docs/03_testing/**` | PRD:857 |
| `non_evolvable_globs` | 字串陣列 | 非空（重複項由 R22 判） | 由 R22 的規則自 PRD 與根 `CLAUDE.md` 現算 | NFR-SI-02-1（PRD:491–494） |

- **R22 耦合與 glob 一致性**：(a) `w_opp` 與 `w_min` 皆為有效整數時，`w_opp` 小於 `w_min` ⇒ `COUPLING-W-OPP-LT-W-MIN`（subject 為 `w_opp`；相等或大於放行；PRD §1.3〈M1 判定細則〉(f)）；`ledger_warn_bytes` 不小於 `ledger_fail_bytes` ⇒ `COUPLING-WARN-GE-FAIL`（subject 為 `ledger_warn_bytes`）；任一參與的鍵無效 ⇒ 該耦合項 blocking NE `SOURCE-UNAVAILABLE`。(b) **`non_evolvable_globs` 與 PRD 一致**（PRD 的散文是唯一真相源，不得在檢查器內複寫第二份清單）：必備集合＝兩個來源的聯集。來源一：PRD（`docs/01_requirements/SelfImproving_PRD.md`）中**第一個**含字面 `**實體 glob**` 的行，取該行內所有反引號片段，且片段開頭反引號的緊鄰前文須以 `、` 或 `；` 結尾，或以標籤 `(i) `、`(ii) `、`(iii) `、`(iv) `、`(v) `（小寫羅馬數字加括號加一個空白）結尾；散文片段（如前接「根 」的 `CLAUDE.md`、前接「所列 」的 `tools/lib/`、前接「且 」的 `maturity: active`、前接「（」的指令）因緊鄰前文不符而不納入。來源二：根 `CLAUDE.md` 中**第一個**含字面 `守衛面＝` 的行，取該行內符合 `^(?P<dir>[^{}\s]+/)\{(?P<names>[^{}\s]+)\}(?P<ext>\.[A-Za-z0-9]+)$` 的反引號片段，以逗號展開成 `<dir><name><ext>`（大括號展開）。`params.json` 的 `non_evolvable_globs` 與必備集合比對：集合不等（缺少、多出）或清單內有重複項 ⇒ `GLOBS-SET-MISMATCH`（subject 為 `non_evolvable_globs`，detail 列缺少與多出的項；順序不拘）；PRD 或根 `CLAUDE.md` 讀不到、或找不到其標記行 ⇒ blocking NE `SOURCE-UNAVAILABLE`。（SA 預演現查：真 PRD 取得 18 項、真 `CLAUDE.md` 展開 7 項，合計 25 項；Developer 以規則現算為準，不得抄此數字。）
- **R23 反空轉與體積**：`ledger.vacuity`：R9 解析到的資料列數小於 `min_obs_rows`（含零列）⇒ blocking NE `LEDGER-BELOW-FLOOR`（subject 為 `-`；等於下限算通過；PRD:733「低於下限＝NOT-EVALUABLE」）。`ledger.volume`：`--ledger` 檔案的位元組數大於等於 `ledger_fail_bytes` ⇒ `VOLUME-FAIL`（fail）；否則大於等於 `ledger_warn_bytes` ⇒ `VOLUME-WARN`（warn 等級，狀態仍 PASS）。兩項所需的參數無效 ⇒ blocking NE `SOURCE-UNAVAILABLE`。

*F. 協定目錄、SOP 與範圍守衛*

- **R24 協定目錄**：`params.json` 為 UTF-8（無 BOM）、換行 LF、結尾有換行、頂層鍵依位元組序遞增（先例 `docs/06_quality/FiveQuestion_Audit_Protocol/params.json` 的扁平排序形態）。`metrics.md`：(a) PRD §1.3 表格中五個指標列（以 `^\| \*\*(?:結果指標|資訊欄)\*\*[^|]* \| \*\*M([1-5]) ` 辨識，M1～M5 各恰一列；SA 預演現查：真 PRD 取得 5 列，判定細則區段有 9 個非空行）逐字出現在 `metrics.md`（CRLF 換成 LF 後以整行比對），且順序為 M1 至 M5；(b) 該表之後自標題行 `**M1 判定細則**` 起、至下一個以 `#### ` 起頭的標題行之前，所有非空行也逐字出現在 `metrics.md`。PRD 凍結，此兩段即指標定義的來源；PRD 經 T1 修訂時 `metrics.md` 須同步，不同步即由 AC-031-2 的 AT 轉紅。
- **R25 SOP 骨架**（`docs/05_development/SelfImproving_Operations_SOP.md`；測試以 LF 正規化全文與「`## ` 標題切段」判定，只判關鍵片段是否存在，語意由實跑檢核 V8 對照 PRD 檢核）：(1) **角色節**：有 `## ` 級標題分別含「擷取者」「歸因者」「提案者」「審查者」「凍結者」；擷取者節（自其標題至下一個 `## ` 之前）須含 `HEAD=<sha>`、`文字交卷`、`流程摩擦`、`python tools/session_resume_planner.py --pace`、`Omitted`、`OBS-SI-033`、`OBS-SI-038`、`python tools/selfimproving.py check`、`來源`、`回報者`；其餘四個角色節須存在，P0 可只有標題與一行「P1 定稿」。(2) **啟動條件節**（`## ` 級標題含「啟動條件」，節內以下一個 `## ` 為界）：含 `(a)` 至 `(e)` 五個標籤；標籤 `(a)` 之後到標籤 `(b)` 之前的文字含 `掌舵者指令`，`(b)` 段含 `第二次`，`(c)` 段含 `P≤2`，`(d)` 段含 `再開症狀`，`(e)` 之後的同一行含 `容量事件`；含一行同時有 `日曆`、`版本號`、`覆蓋度`、`每 N 輪`（否定句）；含 `si status`，且同節含 `視窗開場` 與 `收尾`。(3) **無事件條文**：含一行同時有 `無事件` 與 `通過`。(4) **再開條文**：含一行同時有 `產出數量` 與 `T1`。(5) **真缺陷升 DEF**：含一行同時有 `DEF-<id>` 與 `真缺陷`。(6) **外部衍生**：擷取者節含一行同時有 `外部衍生=是` 與 `不得單獨`。(7) **loop-self**：含一行同時有 `loop-self`、`轉交`、`T1`。(8) **流程摩擦入口**：擷取者節含一行同時有 `流程摩擦` 與 `OBS-SI-004`。(9) **M 之後只追加（處置欄 `open`→終值一次除外）**：擷取者節含一行同時有 `追加`、`rel=corrects:`、`ROW-MUTATED`、`open`、`終值`（M 之後帳本的更新——累計次數、狀態、更正——除處置欄 `open`→終值一次〔PRD:223、AC-SI-04-3〕外一律追加列，其餘原地改寫即 `ROW-MUTATED`；M 之前的原地改寫依 AC-SI-01-3 豁免，不在此限）。
- **R26 範圍守衛（P0 不新增常駐行程、排程或 hook）**：`tools/selfimproving.py` 與 P0 驗收時存在的每個 `tools/lib/selfimproving/*.py`（含 `__init__.py`），原始碼不得出現下列字樣（正規式，區分大小寫）：`schtasks`、`launchctl`、`crontab`、`ScheduleWakeup`、`CronCreate`、`Register-ScheduledTask`、`apscheduler`、`threading\.Timer`、`sched\.scheduler`、`time\.sleep`、`while\s+True`、`daemon\s*=\s*True`、`os\.fork`、`signal\.alarm`；根 `.claude/settings.json` 全文不得含 `selfimproving`（不分大小寫）；`main` 對 `status`、`prop-new` 等非 `check` 的動詞一律 rc 3。（P1 起新增動詞與事件帳本寫入，範圍守衛與 R8(a) 的靜態掃描由 P1 的 TCS 重定。）

**〈判定碼表〉**（項序即輸出序；「狀態」欄＝該碼命中時該項的狀態；NE 的 nonblocking 只有一個）

| 項目 ID | 碼 | 狀態 | 觸發 |
|---------|-----|------|------|
| `ledger.structure` | `HEADER-COLS` | FAIL | 表頭缺或欄名序列不符（R9） |
| `ledger.structure` | `ROW-ARITY` | FAIL | 資料列欄數不是 9，或行不以 `\|` 結尾（R9） |
| `ledger.structure` | `ROW-ID-FORMAT` | FAIL | ID 欄不符 `OBS-SI-\d{3,}`（含空 ID 欄的表內行，subject 為 `L<行號>`） |
| `ledger.structure` | `ROW-ID-DUP` | FAIL | ID 重複 |
| `ledger.structure` | `ROW-ID-ORDER` | FAIL | ID 數值未嚴格遞增 |
| `ledger.time_tz` | `TZ-HEADER-MALFORMED` | FAIL | 檔頭 tz 宣告不合法或超過一個（R9、R10） |
| `ledger.time_tz` | `TIME-FORMAT` | FAIL | 時間格不合文法或日期不存在（R10） |
| `ledger.time_tz` | `TIME-NO-TZ` | FAIL | 起點無 offset 且檔頭無有效 tz（R10） |
| `row.required` | `FIELD-EMPTY` | FAIL | 七個必填欄為空或佔位值（R12） |
| `row.enums` | `ENUM-CATEGORY`、`ENUM-SEVERITY` | FAIL | 分類或嚴重度不在枚舉（R13） |
| `row.enums` | `DISP-ENUM` | FAIL | 處置首詞或其參照文法不符（R13） |
| `row.enums` | `DISP-TEXT-MISSING` | FAIL | `deferred`、`retired`、`decided` 缺附加文字，或 `retired` 缺座標（R13） |
| `row.enums` | `DISP-DEFER-LATER` | FAIL | 處置格含「之後再看」（R13） |
| `row.markers` | `MARK-SYNTAX`、`MARK-UNKNOWN-KEY`、`MARK-VALUE`、`MARK-ORIG-FORMAT`、`MARK-FACE-MISSING` | FAIL | 標記欄語法、詞彙、值域、`orig` 形態、缺 `面`（R14） |
| `row.markers` | `GUARD-NO-EXPOSURE`、`GUARD-P12-NO-EXPOSURE` | FAIL | 守衛面缺暴露、或守衛面 P1／P2 的暴露為「無」（R15） |
| `row.provenance` | `SOURCE-MISSING`、`SOURCE-VALUE`、`REPORTER-MISSING` | FAIL | 來源、回報者缺漏或來源值域外（R15） |
| `row.coordinates` | `COORD-NONE` | FAIL | 證據座標不命中 R16 九種形態 |
| `row.bytes` | `ROW-BYTES-OVER` | FAIL | 列位元組大於 `row_max_bytes`（R11） |
| `row.control_chars` | `CTRL-CHAR` | FAIL | 列內有控制字元（R11） |
| `row.fixed_sha` | `FIXED-SHA-UNRESOLVED` | FAIL | `fixed@` 的 sha 解析不成 commit（R17） |
| `row.fixed_sha` | `GIT-UNAVAILABLE` | NE blocking | 有 `fixed@` 列而 git 不可用（R8、R17） |
| `ref.def` | `DEF-REF-DANGLING` | FAIL | DEF 引用不在缺陷帳本家族主鍵內（R18） |
| `ref.def` | `SOURCE-UNAVAILABLE` | NE blocking | 有 DEF 引用而缺陷帳本家族檔案全無（R18） |
| `ref.obs` | `OBS-REF-DANGLING` | FAIL | 提及的 OBS ID 不在主鍵集合（R18） |
| `ref.obs` | `GIT-UNAVAILABLE` | NE blocking | git 不可用（R18） |
| `ref.orig_notes` | `ORIG-NOTES-MISSING`、`ORIG-NOTES-ANCHOR` | FAIL | 附註檔不存在，或錨點與標題不符（R18） |
| `ref.carrier_families` | `CARRIER-NOT-ESTABLISHED` | NE nonblocking | 有載體尚未建立之家族的提及（R18） |
| `ref.carrier_families` | `GIT-UNAVAILABLE` | NE blocking | git 不可用（R18） |
| `history.migration` | `MIG-SHA-FORMAT`、`MIG-SHA-UNRESOLVED`、`MIG-SHA-NOT-ANCESTOR`、`MIG-CONFIRM-MISSING`、`ORIG-OUTSIDE-MIGRATION` | FAIL | 遷移宣稱無效、缺確認列、orig 出現在遷移之外（R19） |
| `history.migration` | `GIT-UNAVAILABLE` | NE blocking | 有宣稱而 git 不可用（R19） |
| `history.row_mutated` | `ROW-MUTATED` | FAIL | 已存在列被原地改寫或刪除（R20） |
| `history.row_mutated` | `GIT-UNAVAILABLE`、`SOURCE-UNAVAILABLE` | NE blocking | git 不可用，或帳本不在 repo 內（R20） |
| `params.keys` | `PARAM-MISSING`、`PARAM-TYPE`、`PARAM-RANGE` | FAIL | 必備鍵缺少、型別、範圍不符（R21） |
| `params.globs` | `GLOBS-SET-MISMATCH` | FAIL | `non_evolvable_globs` 與 PRD 加根 `CLAUDE.md` 的必備集合不一致（R22） |
| `params.globs` | `SOURCE-UNAVAILABLE` | NE blocking | PRD 或根 `CLAUDE.md` 讀不到或找不到標記行（R22） |
| `params.coupling` | `COUPLING-W-OPP-LT-W-MIN`、`COUPLING-WARN-GE-FAIL` | FAIL | 參數耦合被違反（R22） |
| `params.coupling` | `SOURCE-UNAVAILABLE` | NE blocking | 參與耦合的鍵無效（R22） |
| `ledger.volume` | `VOLUME-FAIL` | FAIL | 帳本位元組大於等於 `ledger_fail_bytes`（R23） |
| `ledger.volume` | `VOLUME-WARN` | PASS（warn） | 帳本位元組大於等於 `ledger_warn_bytes` 而未達 fail（R23） |
| `ledger.volume` | `SOURCE-UNAVAILABLE` | NE blocking | 體積參數無效（R5、R23） |
| `ledger.vacuity` | `LEDGER-BELOW-FLOOR` | NE blocking | 資料列數小於 `min_obs_rows`（R23） |
| `ledger.vacuity` | `SOURCE-UNAVAILABLE` | NE blocking | `min_obs_rows` 無效（R5、R23） |

> 需要某參數的其餘項目（`row.bytes` 需 `row_max_bytes`）參數無效時，同樣為 blocking NE `SOURCE-UNAVAILABLE`（R5）；表中不逐項重列。

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-001 | 作為在任何視窗新增一筆觀察的人，我要欄位、時間、座標與標記的規則定稿且能被機器檢查，以便新增時不必向掌舵者追問任何必填欄（P0 退出條件 (a)） | AC-001-1 | （PRD AC-SI-01-1）Given 一筆新觀察 When 寫入帳本並執行 `check` Then 必填欄皆有值、證據座標至少一個可定位、時間帶 UTC offset（列內明示或沿用檔頭 `tz=`）；缺任一者 `check` 判不合規（rc 1）而不是放行 |
| US-001 | 同上 | AC-001-2 | （PRD AC-SI-01-2）Given 面為守衛的列 When 嚴重度標 P1 或 P2 Then 暴露必為 a、b、c 之一，否則 `check` 判不合規（應降 P4）；面不是守衛者依非守衛口徑，不受暴露規則約束 |
| US-001 | 同上 | AC-002-1 | （PRD AC-SI-02-1）Given 觀察內容源自外部內嵌指示 When 入帳 Then 標記 `外部衍生=是`（詞彙與語法由 `check` 守）；「該列不得單獨充當任何類別提案的證據」屬 P1 的 `prop-new` 前置檢查，P0 以標記詞彙加 SOP 條文代位 |
| US-001 | 同上 | AC-002-2 | （PRD AC-SI-02-2）Given 任一觀察 When 入帳 Then 來源與回報者皆有值（`check` 守）；觀察本身不自動啟動任何行為（`check` 唯讀、零副作用） |
| US-002 | 作為掌舵者，我要既有各列一次性遷移到定稿欄位且原文不被靜默覆寫，遷移後任何原地改寫都被偵測，以便帳本可稽核 | AC-001-3 | （PRD AC-SI-01-3）Given 既有各列 When 遷移 Then 單一 commit、ID 不變、處置落入枚舉、原文逐字留 `orig`（超長者搬附註檔）、無「之後再看」；豁免須同時有 `migration_base_sha`（遷移 commit 的 sha，另一個 commit 寫入）與掌舵者確認的 `decided` 列（含 sha、`sid`、`line`）；缺一則遷移視為未豁免、自第一個提交起比對；`orig` 只用於遷移 |
| US-002 | 同上 | AC-004-3 | （PRD AC-SI-04-3）Given 已存在的列 When `check` 自遷移基準起對 HEAD 與歷次提交逐對比較 Then 除處置欄 open 轉終值一次外的原地改寫標 `ROW-MUTATED` 並要求掌舵者過目；基準以前不比；更正走追加更正列；工作樹內多步改寫不可偵測（誠實劃界） |
| US-003 | 作為維護帳本的主控，我要引用完整性與缺陷／觀察分工有機器檢查，以便懸空引用與真缺陷漏升 DEF 不會靜默存在 | AC-004-1 | （PRD AC-SI-04-1）Given 處置為 `DEF-<id>` 或任何跨檔的 `OBS-SI-` 引用 When `check` Then 被引列存在（含封存檔）；引用不存在的 ID 判不合規；載體尚未建立的家族（`PROP-SI-` 等）印「未判」（NE，nonblocking），不判通過也不判不合規 |
| US-003 | 同上 | AC-004-2 | （PRD AC-SI-04-2）Given 符合缺陷帳本收錄定義的真缺陷 When 觀察入帳 Then 處置須為 `DEF-<id>`（OBS 不取代 DEF 帳本）；P0 以 DEF 引用的機器檢查（AC-004-1）加 SOP 條文代位，「是否符合收錄定義」屬判斷、不機械化 |
| US-004 | 作為掌舵者，我要迴圈只由事件啟動、零事件記為「無事件」、產出數量不構成再開理由，且發現的流程問題一律當下入帳，以便不出現靜默空轉與日曆式觸發 | AC-003-1 | （PRD AC-SI-03-1）Given 迴圈任一階段 When 檢視啟動條件 Then 僅有 (a)～(e) 五類事件，沒有日曆、版本號、覆蓋度、每 N 輪觸發；事件偵測 `si status` 唯讀按需、不新增常駐行程、排程或 hook；P0 以靜態掃描（無常駐機制、`status` 動詞不存在）加 SOP 條文代位 |
| US-004 | 同上 | AC-003-2 | （PRD AC-SI-03-2）Given 觀察零筆或低於下限 When 判定狀態 Then 記為未判（`check` 的 NE，rc 2）或「無事件」而非通過 |
| US-004 | 同上 | AC-003-3 | （PRD AC-SI-03-3）Given 迴圈產出數量 When 評估是否再開 `AutoSDD_improving_NN` Then 產出數量不構成理由；流程型，P0 以 SOP 條文加「`check` 沒有任何以筆數或排程為參數的旗標」代位 |
| US-004 | 同上 | AC-029-1 | （PRD AC-SI-29-1）Given 開發或運轉本迴圈時發現流程不當或 BUG When 發現當下 Then 一律入觀察帳本（一句症狀加一個座標），真缺陷升 DEF；子代理以文字交卷的「流程摩擦」節為入口；流程型，P0 以 SOP 條文代位並由實跑檢核 V8 對照 |
| US-004 | 同上 | AC-029-2 | （PRD AC-SI-29-2）Given 對迴圈本身預算、閘門、停機條件、指標定義的改進 When 提出 Then 一律標 `loop-self` 並轉交，僅經掌舵者 T1 或 PRD 修訂，本迴圈不得提案修改自己；P0 以 SOP 條文加 `non_evolvable_globs` 涵蓋迴圈自身檔案代位 |
| US-005 | 作為主控與 QA，我要一支唯讀檢查器與協定目錄，輸出可機器判讀、可重放、失敗時給出可貼入帳本的草稿列，以便 `check` 綠成為 P0 的驗收憑證 | AC-030-1 | （本檔自增；PRD §9.3 `check` 列、NFR-SI-09-1）Given 任一 repo 與帳本 When 執行 `check` Then 21 個判定項依固定順序輸出 PASS、FAIL、NE，rc 依 0、1、2 表達；用法錯誤與讀不到輸入為 rc 3；文字與 JSON 形態一致；中文輸出在非 UTF-8 管線下不降解 |
| US-005 | 同上 | AC-030-2 | （本檔自增；PRD §9.3 唯讀、§9.4 CLI 不自寫帳本）Given 任意輸入 When 執行 `check` Then 零副作用、不連網、只用標準庫、唯一子行程是環境被淨化的 `git` |
| US-005 | 同上 | AC-030-3 | （本檔自增；草稿列＝PRD §9.4 與 NFR-SI-09-3 明文，判準指紋＝本檔類推，見〈AC 編號規則〉）Given 判準不變 When 重跑 Then 指紋相同且只隨判準變；rc 不為 0 時印一行可貼入且自身零 finding 的 OBS 草稿列 |
| US-005 | 同上 | AC-031-1 | （本檔自增；PRD §9.1 C5 列、§9.3 `check` 的 params 對表、NFR-SI-02-1）Given 協定目錄的 `params.json` When `check` 對表 Then 鍵集合、型別、範圍、`w_opp` 與 `w_min` 的耦合、`non_evolvable_globs` 與 PRD 及根 `CLAUDE.md` 的一致性任一違反皆判紅；取不到判準輸入判未判 |
| US-005 | 同上 | AC-031-2 | （本檔自增；PRD §9.1 C5 列「指標定義」）Given PRD §1.3 的 M1～M5 When 建立 `metrics.md` Then 五個指標列與 M1 判定細則逐字存在於 `metrics.md` |
| US-005 | 同上 | AC-032-1 | （本檔自增；PRD §9.1 C6 列、NFR-SI-07-2）Given P0 的 SOP 骨架 When 檢視 Then 五個角色節的位置齊備，擷取者節完整（輸入快照、文字交卷、`--pace` 現查、Grep 命中 Omitted 必 Read、外部衍生、來源與回報者、`check` 指令） |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。本檔除 §1 外沒有任何第一欄以 AC 起頭的表格；AT ID 只出現在 §1、§2、§3、§4、§6。

**INVEST 自檢**：獨立（只依賴 git、PRD 與根 `CLAUDE.md` 的現況文字、既有 `tools/_stdio_utf8.py`）、可協商（判定碼、輸出文法、`min_obs_rows` 等未命名參數由本檔定義，掌舵者可於開放問題裁決）、有價值（P0 退出條件 (a)～(d) 全部可由 `check` 與實跑檢核判定，且遷移與豁免有機械憑證）、可估計（套件 `tools/lib/selfimproving/` 加 1 支 CLI 加 1 個測試檔加 3 份文件；立案時估「約 3 個 `si_*.py` 模組」，實作為 7 支套件模組，勘誤二）、小（P0 只有 `check` 一個動詞）、可測（42 個 AT；其中 17 個用真 git、其餘為解析層與文件層，皆 tmp 目錄隔離、不碰真帳本）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P0-1 | 純度與零副作用：R8 全部（唯讀、只用標準庫與本地模組、不連網、git 子行程環境淨化、timeout、UTF-8、無 naive 時間戳） | §2 的 AC-030-2 AT；SCG-4 程式碼審查 |
| NFR-P0-2 | 效能：真帳本、真 repo 上單次 `check` 牆鐘小於 30 秒（`git grep` 占大宗）；合成 repo 上單次小於 5 秒；整個測試檔在 CI 上小於 180 秒 | SCG-4 實跑量測（3 次取最大值）；不列 AT |
| NFR-P0-3 | 跨平台（根 `CLAUDE.md` 鐵律三）：路徑一律 `Path` 或 `os.path`，git 的路徑一律 POSIX 斜線；不用單平台 API、不用 `sys.platform` 分支；主控台編碼走 `_stdio_utf8`；換行 LF；測試字面值不含磁碟機代號開頭的路徑 | 根層 `tools/tests/test_platform_neutral_paths.py` 相關鎖；SCG-4 審查；macOS 未實跑項在報告標「未驗」（NFR-SI-06-5） |
| NFR-P0-4 | 根層護欄相容：測試與工具不新增 skip、skipTest、skipIf、xfail（git 缺席視為環境壞、直接失敗；根層 skip 登記義務見 `tools/lib/skip_tag_policy.py`）；所有 `open`、`read_text`、`write_text` 帶 `encoding="utf-8"`（根層鎖 `TestTextIoDeclaresEncoding`）；測試以 `unittest.TestCase` 撰寫並可被 `python -m pytest` 與根層 `python -m unittest discover -s tools/tests` 兩種方式收集；不得另寫 stdout 重設站點（R1） | 根層 unittest 閘門；SCG-4 |
| NFR-P0-5 | LOC 分級：`tools/selfimproving.py` 與 `tools/lib/selfimproving/*.py` 落在根層護欄層分級內，分級與紅線唯一真相源＝`AutoClaude/tools/check_loc_budget.py`（`python AutoClaude/tools/check_loc_budget.py --json` rc 0；數字現查、本檔不複寫）；單檔逼近分級就在套件內依職責拆新模組 | SCG-4 實跑 |
| NFR-P0-6 | 靜態檢查：`ruff check` 對新增的每個 `.py` 0 錯（規則集以 repo 根的 ruff 設定現查） | SCG-4 實跑 |
| NFR-P0-7 | 測試 hermetic：全部 AT 只用 tmp 目錄內的合成 repo 與合成帳本，唯讀存取真 repo 的 `params.json`、`metrics.md`、SOP、PRD、根 `CLAUDE.md`、`tools/` 原始碼與 `.claude/settings.json`；不寫真帳本、不連網、git 子行程環境依 §5.5 淨化；不得在測試原始碼或本檔寫出不存在於真帳本與真缺陷帳本的字面 `OBS-SI-` 或 `DEF-` 編號（合成編號於執行期組出，先例 `tools/tests/test_defect_id_reference_integrity.py` 的 `_syn()`） | 實跑檢核 V2（真帳本 `ref.obs`）與既有鎖 `test_defect_id_reference_integrity.py` |
| NFR-P0-8 | 範圍守衛：T 提交只新增或修改 §5.6 允許集合內的檔案；不改 `.claude/**`（含 `settings*.json`）、不改任何凍結檔（PRD、研究方法 SOP）、不動根層鎖檔；重釘根層棘輪的儀式（檔案數下限、LOC、E501 等；現查 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `repin_growth_problems()`、`tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS` 與 `tree_floor_problems()`，以及根層全套 unittest 現跑所指出的其餘棘輪）由主控收尾，實作者不碰鎖檔 | 實跑檢核 V7（`git diff --name-only`） |

**追溯矩陣**：F-001 ← PRD FR-SI-01、02、03、04、29（§5.2）與 §9.1 的 C1、C4（`check`）、C5、C6 列、§9.3 `check` 列、§9.4 草稿列規則、§9.6 P0 列、§8.1 P0 退出條件 (a)～(d)；US-001～US-005 → AC-001-1～AC-032-1（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD 全文（§8.1 P0、§9.6 P0）；Stage-1 凍結＝掌舵者預先核准、主控代為執行 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-001（本檔 FRD-lite）；FR-SI-01～04、29 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-0／NFR 已量化定義 | NFR-P0-1～8（本檔）；最近依據 PRD NFR-SI-02-1、NFR-SI-06、NFR-SI-08、NFR-SI-09 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-0／User Story 已完成 INVEST 檢查 | US-001～US-005（本檔 INVEST 自檢） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-0／利害關係人已確認簽核 | PRD 附錄 C.2（掌舵者授權代決與預先核准凍結；引言座標已於重凍訂正為 line 2476／2525／2581，見實跑檢核 V5） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC 到 AT 映射） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | 不適用（功能級增量；設計載於 PRD §9）；最近依據 PRD §9.0～§9.6 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-1／API Spec 草稿完成（所有端點清單） | 不適用（無 HTTP 端點）；命令列介面即契約：本檔 R1～R8 與 PRD §9.3 `check` 列 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-1／資料模型設計完成 | PRD §5.1.1（九欄）、§9.2（OBS 載體與檔頭 tz）；本檔 R9～R21 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-P0-1～8 對應 R8（純度）、R1（編碼）；PRD NFR-SI-09-1（量不到＝NE） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-1／整合架構說明完整（第三方服務已識別） | 無第三方服務；僅依賴 git 與既有 `tools/_stdio_utf8.py`、`tools/probe/fivequestion_ledger.py` 的 manifest 算法（先例，不 import） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | PRD §9.1 載體對映表（C1、C4、C5、C6、C14）；P0 不新增系統邊界 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-2／C4 Container 圖完成（主要組件識別） | 落點：根層 `tools/`（CLI `selfimproving.py` 與套件 `lib/selfimproving/`）、`docs/06_quality/`（帳本與協定目錄）、`docs/05_development/`（SOP） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | PRD §9.5：ADR-SI-01（觀察儲存位置）、ADR-SI-05（基線窗）；本增量無新架構決策，ADR 不新開 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 brownfield，非 security）；`check` 無網路、只讀、子行程限 git；不可進化面見 PRD NFR-SI-02-1 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 本檔 FRD-lite〈現況與變更〉（八欄暫定版到九欄定稿加檢查器） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | 不適用（無 HTTP API）；介面為命令列 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／Request／Response Schema 定義完整 | 輸出形態文字與 JSON（本檔 R3、R4）；`params.json` 登記表（R21） | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-3／錯誤碼定義（400／401／403／404／500） | rc 表 0、1、2、3（R1）與判定碼表 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-3／Consumer Contract 完成（整合情境） | 消費者＝主控與 QA（讀 `check`）；P3 的量測腳本讀 `params.json` 與 `metrics.md`（PRD §9.3 量測腳本列）；SOP 是各角色任務書的上位（研究方法 SOP，本增量不改它） | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/SelfImproving_PRD.md | sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 的值是**重凍後**的新 digest（PRD 因附錄 C.2 的逐字稿座標訂正〔line 2493／2536 改為 2476／2525／2581〕走 SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING 重凍，主控於 HEAD 7b9c6ba6 交付，SA 以 `Get-FileHash -Algorithm SHA256` 對工作樹現況重算一致）；SOP 的值不變，取自功能鍵 `monorepo-selfimproving` 的 Stage-1 `spec-frozen` 逐字輸出（`docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md` §7），同樣重算一致。**功能鍵 `monorepo-si-p0-ledger` 的 Stage-1 必須採納重凍後的 PRD 與同一份 SOP**（否則「引用不得指向未凍結文件」不成立）；凍結後的實際 digest 以該鍵 `show` 的輸出為準，與本表不符時以 `show` 為準並更正本表。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；邊界與錯誤 AT 以 `AT-<NNN>-<Y>-E-<n>` 命名並列於本表。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-1 | 基線有效 repo 全綠：八種處置形態、九種座標形態、21 項齊全、rc 0 | ✅ | Integration | □ |
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-E-1 | 時間與 tz：缺宣告、宣告毀損、格式與日期不合；列內 offset 與區間通過 | ✅ | Unit | □ |
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-E-2 | 七個必填欄為空、佔位值、座標不可定位（含真實形裸 sid）與九種形態、sid 的 line=N／seq: N 寫法 | ✅ | Unit | □ |
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-E-3 | 分類、嚴重度、處置的枚舉、附加文字規則與「之後再看」 | ✅ | Unit | □ |
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-E-4 | 結構：欄數、表頭、ID 格式、重複、遞增、跳脫管線 | ✅ | Unit | □ |
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-E-5 | 列位元組 700 邊界、CJK、控制字元、CRLF、體積警戒線 | ✅ | Unit | □ |
| AC-001-1 | 必填欄、時間 offset、座標可定位；不合規者 `check` 判紅 | AT-001-1-E-6 | `fixed@` 的 sha 解析、格式不符、非 git 目錄時未判 | ✅ | Integration | □ |
| AC-001-2 | 守衛面 P1、P2 須有暴露證據 | AT-001-2-1 | 守衛面缺暴露、P1／P2 暴露為無、面與暴露的詞彙；非守衛面不受約束 | ✅ | Unit | □ |
| AC-001-3 | 一次性遷移與豁免（`migration_base_sha` 加確認列） | AT-001-3-1 | 遷移鏈 C0、M、N：已豁免，遷移改動的列不計 ROW-MUTATED | ✅ | Integration | □ |
| AC-001-3 | 一次性遷移與豁免（`migration_base_sha` 加確認列） | AT-001-3-E-1 | 沒有 `migration_base_sha`：未豁免，舊列全標 ROW-MUTATED | ✅ | Integration | □ |
| AC-001-3 | 一次性遷移與豁免（`migration_base_sha` 加確認列） | AT-001-3-E-2 | 有 sha 但確認列缺漏或不合格（六種變體加對照組） | ✅ | Integration | □ |
| AC-001-3 | 一次性遷移與豁免（`migration_base_sha` 加確認列） | AT-001-3-E-3 | sha 格式不符、查無此物件、不是 commit、不是 HEAD 的祖先 | ✅ | Integration | □ |
| AC-001-3 | 一次性遷移與豁免（`migration_base_sha` 加確認列） | AT-001-3-E-4 | `orig` 的附註檔錨點、遷移之外使用、語法 | ✅ | Integration | □ |
| AC-002-1 | 外部衍生標記與標記欄詞彙 | AT-002-1-1 | 標記欄語法與封閉詞彙；外部衍生只接受「是」 | ✅ | Unit | □ |
| AC-002-2 | 來源與回報者必備 | AT-002-2-1 | 來源與回報者缺漏、值空、來源值域外 | ✅ | Unit | □ |
| AC-003-1 | 迴圈只由事件啟動（P0 無常駐機制） | AT-003-1-1 | 無常駐、排程、hook 的靜態掃描；動詞範圍；SOP 啟動條件條文 | ✅ | Unit | □ |
| AC-003-2 | 零筆記為未判或無事件，而非通過 | AT-003-2-1 | 低於反空轉下限判 NE（rc 2）；SOP 無事件條文 | ✅ | Unit | □ |
| AC-003-3 | 產出數量不構成再開理由 | AT-003-3-1 | SOP 產出數量條文；`check` 旗標清單不含筆數或排程 | ✅ | Unit | □ |
| AC-004-1 | 引用完整性（OBS、DEF、載體未建立） | AT-004-1-1 | 各種存在的引用都解析得到：主帳本、封存檔、姊妹帳本、OBS 封存檔 | ✅ | Integration | □ |
| AC-004-1 | 引用完整性（OBS、DEF、載體未建立） | AT-004-1-E-1 | 引用不存在的 OBS：處置、症狀、其他檔、附註檔標題、rel | ✅ | Integration | □ |
| AC-004-1 | 引用完整性（OBS、DEF、載體未建立） | AT-004-1-E-2 | 引用不存在的 DEF；缺陷帳本家族全缺時未判 | ✅ | Integration | □ |
| AC-004-1 | 引用完整性（OBS、DEF、載體未建立） | AT-004-1-E-3 | 載體尚未建立的家族印未判，不判通過也不影響 rc | ✅ | Integration | □ |
| AC-004-2 | 真缺陷處置須為 DEF | AT-004-2-1 | SOP「真缺陷處置須為 DEF」條文 | ✅ | Unit | □ |
| AC-004-3 | 原地改寫偵測（ROW-MUTATED） | AT-004-3-1 | open 轉終值一次、追加新列、追加更正列、格式整理皆放行 | ✅ | Integration | □ |
| AC-004-3 | 原地改寫偵測（ROW-MUTATED） | AT-004-3-E-1 | 遷移之後的原地改寫：改格、二次改處置、刪列、改號、混改 | ✅ | Integration | □ |
| AC-004-3 | 原地改寫偵測（ROW-MUTATED） | AT-004-3-E-2 | 工作樹未提交的改寫；誠實劃界 | ✅ | Integration | □ |
| AC-004-3 | 原地改寫偵測（ROW-MUTATED） | AT-004-3-E-3 | 無歷史可比（`no-history`）與帳本在 repo 外（`SOURCE-UNAVAILABLE`） | ✅ | Integration | □ |
| AC-029-1 | 流程摩擦當下入帳 | AT-029-1-1 | SOP「流程摩擦」入口與當下入帳條文 | ✅ | Unit | □ |
| AC-029-2 | `loop-self` 轉交 | AT-029-2-1 | SOP `loop-self` 條文；迴圈自身檔案列入 `non_evolvable_globs` | ✅ | Unit | □ |
| AC-030-1 | `check` 介面、輸出與 rc 表 | AT-030-1-1 | 輸出形態、rc 0 與 1、文字與 JSON 一致、非 UTF-8 管線下中文不降解 | ✅ | Integration | □ |
| AC-030-1 | `check` 介面、輸出與 rc 表 | AT-030-1-E-1 | 用法錯誤與讀不到輸入一律 rc 3；`--help` | ✅ | Unit | □ |
| AC-030-2 | 唯讀與純度 | AT-030-2-1 | 零副作用、純標準庫、git 子行程環境淨化 | ✅ | Integration | □ |
| AC-030-3 | 判準指紋與 OBS 草稿列 | AT-030-3-1 | 判準指紋：可重放、只隨判準變 | ✅ | Unit | □ |
| AC-030-3 | 判準指紋與 OBS 草稿列 | AT-030-3-2 | OBS 草稿列：可貼入、自身零 finding、位元組上限 | ✅ | Unit | □ |
| AC-031-1 | `params.json` 對表 | AT-031-1-1 | 真 `params.json`：格式、鍵集合、型別範圍、與 PRD 及根 `CLAUDE.md` 一致 | ✅ | Unit | □ |
| AC-031-1 | `params.json` 對表 | AT-031-1-E-1 | 缺鍵（逐鍵）；取不到參數的項目判未判 | ✅ | Unit | □ |
| AC-031-1 | `params.json` 對表 | AT-031-1-E-2 | `non_evolvable_globs` 與 PRD 不一致：缺少、多出、重複、來源變動、來源讀不到 | ✅ | Unit | □ |
| AC-031-1 | `params.json` 對表 | AT-031-1-E-3 | 耦合：`w_opp` 小於 `w_min`、warn 不小於 fail | ✅ | Unit | □ |
| AC-031-1 | `params.json` 對表 | AT-031-1-E-4 | 型別錯誤（字串、浮點、布林、整數、陣列元素）；多出的鍵不判紅 | ✅ | Unit | □ |
| AC-031-1 | `params.json` 對表 | AT-031-1-E-5 | 範圍錯誤（比例鍵、下限鍵、非空陣列） | ✅ | Unit | □ |
| AC-031-2 | `metrics.md` 指標定義 | AT-031-2-1 | `metrics.md` 的 M1～M5 與判定細則逐字存在 | ✅ | Unit | □ |
| AC-032-1 | SOP 骨架 | AT-032-1-1 | SOP 骨架：五角色節、擷取者節完整、外部衍生條文 | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: 19（PRD 的 13 個加本檔自增的 6 個）
- 已映射 AT 數: 42（其中 E 類 22 個）
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_001_1_1]`；E 類為 `[AT_OK_001_1_E_1]`），本節 Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，單引號字元用文字描述。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑判定指令（cwd 為 monorepo 根），**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。兩種等價的判定指令：
> - `python -m pytest tools/tests/test_selfimproving_check.py -k <AT 底線形> -q`
> - `python -m unittest discover -s tools/tests -p test_selfimproving_check.py -k <AT 底線形>`
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-001-1-E-1` 的底線形是 `AT_001_1_E_1`）；每個 AT 的測試函式名稱須含其底線形（例 `test_AT_001_1_E_1_time_and_tz`）。
>
> **斷言簡寫**（本節各 AT 共用）：`main`＝`selfimproving.main`（測試以 `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` 後 `import selfimproving`，比照 `tools/tests` 既有風格）；`run_json(repo)`＝以 `contextlib.redirect_stdout` 呼叫 `main(["check", "--repo", str(repo), "--json"])` 並 `json.loads` stdout；`S(項目)`＝該項的 `status`；`F(項目)`＝該項 `findings` 的 `(subject, code)` 集合；「恰為」＝集合相等（不多不少）、「含」＝子集；列號 `003` 等一律指 `OBS-SI-003`。基線有效 repo、遷移鏈 repo、迷你 PRD 與迷你 `CLAUDE.md`、hermetic 環境見 §5。
>
> **變異慣例**：預設自基線複製一份（`shutil.copytree`，含 `.git`）、在工作樹改寫、不 commit。因此在變異情境下 `history.row_mutated` 可能為 FAIL（工作樹相對 HEAD 有改寫）；各 AT 只斷言自己指名的項目與集合，**除非該 AT 明文寫 overall 或 rc**——那樣的 AT 一律改用「烘入第一個 commit」的建法（基線的 `mutate` 參數：先改再提交，使歷史比對項為 PASS）。
>
> **子情境**：AT 內以「情境一」「情境 (a)」等列舉的子情境，測試一律以 `subTest` 或參數化實作（保留 AT ID 對映），任一子情境失敗時，失敗訊息須指出是哪個情境，不得讓一個紅燈無法定位。
>
> **AT 內不引用其他 AT 的 ID**（只有 §1、§3、§4、§6 的表格引用 AT ID），避免編譯器把引用當成宣告。

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1 必填欄、時間 offset、座標可定位——全部合規時 `check` 綠（正向基線）
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_1 -q

Feature: check 對合規帳本判綠

Scenario: 基線有效 repo 的 21 個判定項符合預期，rc 為 0
  Given 依 §5.1 建出基線有效 repo（10 列、涵蓋八種處置形態與九種證據座標形態；`min_obs_rows` 為 10；`migration_base_sha` 為 null；兩個 commit；工作樹乾淨），測試以 §5.5 的 hermetic 環境執行
  When 呼叫 `main(["check", "--repo", <repo>, "--json"])` 並解析 stdout；再呼叫 `main(["check", "--repo", <repo>])` 取文字形態
  Then 兩次的 rc 都是 `0`，JSON 的 `overall` 為 `PASS`，`rows` 為 `10`，`items` 的 `id` 依序恰為判定碼表所列的 21 項
  And 除 `ref.carrier_families` 外的 20 項 `status` 皆為 `PASS` 且 `findings` 為空（其中 `history.migration` 的 `detail` 為 `claim=none`）；`ref.carrier_families` 為 `NE`、`blocking` 為 false，其 finding 的 `code` 為 `CARRIER-NOT-ESTABLISHED`
  And 文字形態首行符合 `si-check rows=10 items=21`，每個判定項各一行且狀態與 JSON 一致，最後一個非空行以 `overall=PASS rc=0 fingerprint=sha256:` 起頭並接 64 位小寫 hex；兩種形態都沒有 OBS 草稿列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_1]"
```

```gherkin
# AT-001-1-E-1
# 對應 AC: AC-001-1 時間必帶 UTC offset（檔頭 tz 宣告或列內明示）；格式與日期
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_E_1 -q

Feature: check 的時間與時區判準

Scenario: 缺 tz、tz 宣告毀損、時間格式不合各被標出，列內 offset 與區間仍通過
  Given 基線有效 repo（§5.1：列 009 的時間列內明示 `+09:00`，列 010 的時間是不帶 offset 的區間，其餘列沿用檔頭 `tz=+08:00`）；每個情境各自複製一份基線、只做一處變異
  When 情境一：刪掉檔頭 tz 宣告那一行
  And 情境二：把宣告改成 `tz=+8:00`；情境三：在檔頭再加一行內容相同的第二個宣告
  And 情境四：把列 003 的時間改成 `2026/10/19 02:30`、列 004 改成 `2026-02-30 10:00`、列 005 改成 `2026-10-19 24:00`、列 006 改成 `2026-10-19 02:30 +25:00`、列 007 改成 `2026-10-18 22:47～`（區間缺迄點）
  Then 情境一：`S(ledger.time_tz)` 為 `FAIL`，`F(ledger.time_tz)` 恰為列 001～008 與列 010 各一筆 `TIME-NO-TZ`（列 009 因列內明示 offset 不在內）
  And 情境二與情境三：`F(ledger.time_tz)` 含 `(-, TZ-HEADER-MALFORMED)`，且其中 `TIME-NO-TZ` 的 subject 集合與情境一相同（無效或重複的宣告視同沒有宣告）
  And 情境四：`F(ledger.time_tz)` 恰為列 003、004、005、006、007 各一筆 `TIME-FORMAT`（格式已不合者不再報 `TIME-NO-TZ`）
  And 基線本身 `S(ledger.time_tz)` 為 `PASS`（列內 offset 優先於檔頭、不帶 offset 的區間通過）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_E_1]"
```

```gherkin
# AT-001-1-E-2
# 對應 AC: AC-001-1 七個必填欄為空與佔位值被標出；證據座標不可定位（含真實形裸 sid）被標出，九種可定位形態與 sid 的 line=N／seq: N 寫法被接受
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_E_2 -q

Feature: check 的必填欄與證據座標判準

Scenario: 空欄與佔位值判 FIELD-EMPTY，不可定位的座標判 COORD-NONE
  Given 基線有效 repo（§5.1：10 列的證據座標依序覆蓋 R16 的九種形態）；每個情境各自複製一份基線、只做一處變異
  When 七個情境各自把列 003 的 時間、情境、症狀、證據座標、分類、嚴重度、處置 其中一欄清成空白
  And 另一個情境把列 004 的症狀改成 `-`、列 005 的情境改成 `—`、列 006 的症狀改成 `TBD`、列 007 的情境改成 `n/a`
  And 再一個情境把列 004、005、006 的證據座標分別改成 `本檔時間欄`、`SD 第一支普查腳本實踩`、`PRD 行數`，把列 007 的證據座標改成 `Claude Code 2.1.283；e.g. 見前述`，並把列 008 的證據座標改成只有 UUID 的裸 sid（真實形 `0a1b2c3d-4e5f-4a6b-8c7d-9e8f0a1b2c3d`，第一段含 a～f，不帶 `line` 或 `seq`；不得改用全數字 UUID，那種本來就不被 `sha` 形態收，測不出二審 N-01）
  And 又一個情境把列 009 的證據座標改成 `sid 0a1b2c3d-4e5f-4a6b-8c7d-9e8f0a1b2c3d line=12`、列 010 改成 `sid 0a1b2c3d-4e5f-4a6b-8c7d-9e8f0a1b2c3d seq: 3`（`line`、`seq` 之後接 `=` 或 `:`，與 R19 (d) 的 `line` 語法一致）
  Then 七個清空情境各自：`S(row.required)` 為 `FAIL`，`F(row.required)` 恰為 `(OBS-SI-003, FIELD-EMPTY)`，該 finding 的 detail 含被清空的欄名；該列在 `ledger.time_tz`、`row.enums`、`row.coordinates` 不因該欄為空而另生 finding
  And 佔位值情境：`F(row.required)` 恰為列 004、005、006、007 各一筆 `FIELD-EMPTY`
  And 座標情境：`S(row.coordinates)` 為 `FAIL`，`F(row.coordinates)` 恰為列 004、005、006、007、008 各一筆 `COORD-NONE`（列 008 是第一段含字母的真實形裸 sid）
  And `sid` 寫法情境：`S(row.coordinates)` 為 `PASS` 且 `F(row.coordinates)` 為空（列 009、010 只靠 `sid` 形態過關，其 UUID 的各段都因連字號邊界不被 `sha` 形態收）
  And 基線的 10 列 `S(row.coordinates)` 為 `PASS`（路徑加行號、反引號指令、帳本或缺陷 ID、檔名加行號、repo 根目錄路徑、sid 加 `line` 或 `seq`、七位以上含字母的 hex、`commit` 關鍵字加 hex、`§` 或文件別名加章節，九種形態皆被接受）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_E_2]"
```

```gherkin
# AT-001-1-E-3
# 對應 AC: AC-001-1 分類、嚴重度、處置的枚舉；處置的附加文字規則；「之後再看」
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_E_3 -q

Feature: check 的枚舉判準

Scenario: 非法的分類、嚴重度、處置各被標出；八種合法處置形態通過
  Given 基線有效 repo（§5.1：列 001～010 的處置涵蓋 `open`、`fixed@`、`DEF-`、`deferred`、`retired`、`decided`、`merged@`、`proposed@` 八種）；每個情境各自複製一份基線、只做一處變異
  When 情境一：列 003 的分類改成 `Process`、列 004 改成 `other`
  And 情境二：列 005 的嚴重度改成 `P0`、列 006 改成 `p1`、列 007 改成 `P5`、列 008 改成 `高`
  And 情境三：列 004～010 的處置依序改成 `TODO`、`fixed`、`fixed@`、`fixed@xyz1234`、`DEF-`、`merged@OBS-SI` 與 `Open`（七個非法首詞）
  And 情境四：列 004 的處置改成不帶附加文字的 `deferred`、列 005 改成 `retired；沒有座標的依據`、列 006 改成不帶附加文字的 `decided`
  And 情境五：列 003 的處置改成 `deferred；之後再看`、列 004 的處置改成 `open；之後再看`
  Then 情境一：`F(row.enums)` 恰為列 003、004 各一筆 `ENUM-CATEGORY`
  And 情境二：`F(row.enums)` 恰為列 005、006、007、008 各一筆 `ENUM-SEVERITY`
  And 情境三：`F(row.enums)` 恰為列 004～010 各一筆 `DISP-ENUM`
  And 情境四：`F(row.enums)` 恰為列 004、005、006 各一筆 `DISP-TEXT-MISSING`
  And 情境五：`F(row.enums)` 恰為列 003、004 各一筆 `DISP-DEFER-LATER`（首詞合法、附加文字非空，不另報其他碼）
  And 基線 `S(row.enums)` 為 `PASS`（八種合法處置形態皆被接受，含 `open`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_E_3]"
```

```gherkin
# AT-001-1-E-4
# 對應 AC: AC-001-1 帳本結構：欄數、表頭、ID 格式、重複、遞增；跳脫管線字元
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_E_4 -q

Feature: check 的帳本結構判準

Scenario: 欄數、表頭、ID 的錯誤各被標出；跳脫的管線字元不影響欄數
  Given 基線有效 repo；每個情境各自複製一份基線、只做一處變異；測試以執行期字串相加組出非法 ID，使測試原始碼不含不存在的字面 OBS 編號（NFR-P0-7）
  When 情境一：列 003 刪掉最後一欄（8 欄），列 004 多加一欄（10 欄）
  And 情境二：表頭改成舊版八欄（沒有「標記」）
  And 情境三：列 005 的 ID 改成只有兩位數字的形態（`OBS-SI-` 接 `12`）、列 007 的 ID 改成第三位是英文字母 O 的形態、並在列 006 之後插入一行 ID 欄為空的九欄資料列（記下該行的行號 n）
  And 情境四：列 008 的 ID 改成與列 002 相同，並把列 009 與列 010 的位置對調
  And 情境五：列 004 的症狀加入一個以反斜線跳脫的管線字元；列 005 的症狀加入一個內含未跳脫管線字元的反引號片段
  And 情境六：把帳本檔改成以 UTF-8 BOM 開頭、第一行就是表頭列的版本（前言與檔頭 tz 宣告都移到最後一個資料列之後）
  Then 情境一：`F(ledger.structure)` 恰為列 003、004 各一筆 `ROW-ARITY`
  And 情境二：`F(ledger.structure)` 恰為 `(-, HEADER-COLS)`（各資料列欄數仍以固定的九判定，不隨表頭）
  And 情境三：`F(ledger.structure)` 恰為三筆 `ROW-ID-FORMAT`，subject 分別是兩位數字的 ID、第三位為字母的 ID、`L<n>`（格式不合的列不參與重複與遞增的追蹤，不另生 `ROW-ID-DUP`、`ROW-ID-ORDER`，R9）
  And 情境四：`F(ledger.structure)` 恰為 `(OBS-SI-002, ROW-ID-DUP)` 與 `(OBS-SI-009, ROW-ID-ORDER)`
  And 情境五：`F(ledger.structure)` 恰為 `(OBS-SI-005, ROW-ARITY)`（跳脫的管線不切欄，反引號內未跳脫的管線照切）
  And 情境六：`S(ledger.structure)` 與 `S(ledger.time_tz)` 皆為 `PASS`，`rows` 仍為 `10`（BOM 容許，表頭在第 1 行也認得，宣告在表後也有效）
  And 基線 `S(ledger.structure)` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_E_4]"
```

```gherkin
# AT-001-1-E-5
# 對應 AC: AC-001-1 列位元組 700 邊界；控制字元；CRLF；帳本體積警戒線
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_E_5 -q

Feature: check 的位元組、控制字元與體積判準

Scenario: 列位元組以 UTF-8 位元組計且 700 為邊界；控制字元被標出；CRLF 檔不誤判；體積警戒線
  Given 基線有效 repo（`row_max_bytes` 為 700、`ledger_warn_bytes` 為 245760、`ledger_fail_bytes` 為 262144）；每個情境各自複製一份基線、只做一處變異
  When 情境一：把列 003 的症狀以 ASCII 字元補到整列（不含換行）恰 700 位元組；情境二：補到恰 701 位元組
  And 情境三：把列 004 的症狀換成 300 個 CJK 字元（約 900 位元組、字元數遠小於 700）
  And 情境四：列 003 維持 701 位元組，但把 `params.json` 的 `row_max_bytes` 改成 800
  And 情境五：分別在列 005 插入一個 TAB、列 006 插入 NUL（0x00）、列 007 插入 ESC（0x1b）、列 008 插入 DEL（0x7f），並在列 009 的行中間（不在行尾）插入單獨一個 CR
  And 情境六：把整個帳本檔的換行改成 CRLF（git 設定不做換行轉換）
  And 情境七：把 `params.json` 設成 `ledger_warn_bytes` 等於帳本檔位元組數、`ledger_fail_bytes` 為其加一；情境八：設成 `ledger_fail_bytes` 等於帳本檔位元組數、`ledger_warn_bytes` 為其減一
  Then 情境一：`S(row.bytes)` 為 `PASS`；情境二：`F(row.bytes)` 恰為 `(OBS-SI-003, ROW-BYTES-OVER)`；情境三：`F(row.bytes)` 恰為 `(OBS-SI-004, ROW-BYTES-OVER)`；情境四：`S(row.bytes)` 為 `PASS`
  And 情境五：`S(row.control_chars)` 為 `FAIL`，`F(row.control_chars)` 恰為列 005、006、007、008、009 各一筆 `CTRL-CHAR`
  And 情境六：21 個判定項的 `status` 與基線逐項相同（尤其 `row.control_chars`、`row.bytes`、`history.row_mutated` 為 `PASS`；行尾 CR 不算控制字元、不計入位元組，歷史比對先把 CRLF 換成 LF）
  And 情境七：`S(ledger.volume)` 為 `PASS` 且 `F(ledger.volume)` 恰為 `(-, VOLUME-WARN)`，該 finding 的 `level` 為 `warn`；情境八：`S(ledger.volume)` 為 `FAIL` 且 `F(ledger.volume)` 恰為 `(-, VOLUME-FAIL)`；基線 `S(ledger.volume)` 為 `PASS` 且 `findings` 為空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_E_5]"
```

```gherkin
# AT-001-1-E-6
# 對應 AC: AC-001-1 `fixed@` 的 sha 必須解析成存在的 commit；格式不符歸處置枚舉；非 git 目錄時未判
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_1_E_6 -q

Feature: check 的 fixed@ 解析判準

Scenario: 解析不到的 sha 判紅；格式不符者由枚舉判準攔下；沒有 git 時判未判
  Given 基線有效 repo（列 002 的處置是 `fixed@` 接第一個 commit 的前 12 位，該 commit 存在）；每個情境各自複製一份基線、只做一處變異
  When 情境一：列 004 的處置改成 `fixed@deadbee`（七位小寫 hex、無此物件）
  And 情境二：在 repo 內以 `git hash-object -w` 寫入一個 blob，列 005 的處置改成 `fixed@` 接該 blob 的 40 位 sha（物件存在但不是 commit）
  And 情境三：列 006 的處置改成 `fixed@ABCDEF1`（大寫）、列 007 改成 `fixed@abc`（過短）
  And 情境四：把基線的檔案（不含 `.git`）複製到另一個沒有 git 的目錄後執行
  Then 情境一：`S(row.fixed_sha)` 為 `FAIL`，`F(row.fixed_sha)` 恰為 `(OBS-SI-004, FIXED-SHA-UNRESOLVED)`
  And 情境二：`F(row.fixed_sha)` 恰為 `(OBS-SI-005, FIXED-SHA-UNRESOLVED)`
  And 情境三：`F(row.enums)` 恰為列 006、007 各一筆 `DISP-ENUM`，`S(row.fixed_sha)` 為 `PASS`（格式不符者不進 sha 解析）
  And 情境四：`status` 為 `NE` 且 `blocking` 為 true 的項目恰為 `row.fixed_sha`、`ref.obs`、`ref.carrier_families`、`history.row_mutated` 四項，每項的 finding 碼皆為 `GIT-UNAVAILABLE`；其餘 17 項皆 `PASS`；`overall` 為 `NE`、rc 為 `2`
  And 基線 `S(row.fixed_sha)` 為 `PASS`（列 002 解析得到）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_E_6]"
```

```gherkin
# AT-001-2-1
# 對應 AC: AC-001-2 守衛面 P1、P2 須有暴露證據；面與暴露的詞彙；非守衛面不受約束
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_2_1 -q

Feature: check 的守衛面暴露規則

Scenario: 守衛面 P1／P2 缺暴露證據被標出，非守衛面與守衛面 P3／P4 不受約束
  Given 基線有效 repo（§5.1：列 009 為守衛面、P2、暴露 a；列 010 為守衛面、P4、暴露為無）；每個情境各自複製一份基線、只做一處變異
  When 情境一：列 003 改成 面 為守衛、嚴重度 P1、暴露為無；列 004 改成 面 為守衛、嚴重度 P2、標記欄完全沒有暴露鍵；列 005 改成 面 為守衛、嚴重度 P3、暴露為無；列 006 改成 面 為產品、嚴重度 P1、沒有暴露鍵
  And 情境二：列 007 的標記欄移除 面 鍵；列 008 的 面 改成 `其他`；列 003 的暴露改成 `d`
  Then 情境一：`F(row.markers)` 恰為 `(OBS-SI-003, GUARD-P12-NO-EXPOSURE)` 與 `(OBS-SI-004, GUARD-NO-EXPOSURE)`（列 005、006、009、010 通過）
  And 情境二：`F(row.markers)` 恰為 `(OBS-SI-007, MARK-FACE-MISSING)`、`(OBS-SI-008, MARK-VALUE)`、`(OBS-SI-003, MARK-VALUE)`
  And 基線 `S(row.markers)` 為 `PASS`；守衛面 P1／P2 列的暴露證據座標由該列證據座標通過 `row.coordinates` 承擔（情境一的守衛面列座標仍為 `PASS`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_2_1]"
```

```gherkin
# AT-001-3-1
# 對應 AC: AC-001-3 遷移鏈 C0、M、N：已豁免，遷移改動的列不計 ROW-MUTATED
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_3_1 -q

Feature: 一次性遷移的豁免

Scenario: M 與 N 兩個 commit 之後，C0 到 M 的改動不計 ROW-MUTATED，check 綠
  Given 依 §5.2 建出遷移鏈 repo：C0（舊版八欄帳本、4 列、無 tz 宣告）、M（單一 commit：九欄、檔頭 tz、處置落入枚舉、`orig`、附註檔，只動帳本與附註檔）、N（`params.json` 的 `migration_base_sha` 寫入 M 的完整 sha，並追加一筆合格的 `decided` 確認列）
  When 呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then rc 為 `0`，`overall` 為 `PASS`
  And `S(history.migration)` 為 `PASS` 且該項的 `detail` 為 `claim=valid`；`S(history.row_mutated)` 為 `PASS`；`S(ref.orig_notes)` 為 `PASS`；`row.enums`、`row.markers`、`row.provenance`、`row.coordinates`、`row.bytes` 皆為 `PASS`
  And 列 004 的 `orig` 是 `@` 指向附註檔錨點的形態，附註檔中該錨點段落的內容與 C0 的列 004 處置原文逐字相同（測試以 `git show` 取 C0 的原文比對）
  And 夾具自證：M 這個 commit 只動兩個檔（`git show --name-only --format=` 的輸出恰為帳本與附註檔）；N 只動 `params.json` 與帳本；M 與 N 是兩個不同的 commit，且 N 的帳本內容含 M 的 sha 前 7 位
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_1]"
```

```gherkin
# AT-001-3-E-1
# 對應 AC: AC-001-3 沒有 migration_base_sha 時遷移不豁免，不靜默放行
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_3_E_1 -q

Feature: 缺 migration_base_sha 即未豁免

Scenario: migration_base_sha 為 null 時，遷移改動的列全部標 ROW-MUTATED
  Given 遷移鏈 repo（§5.2，N 之後）再加一個 commit：把 `params.json` 的 `migration_base_sha` 改回 null（確認列仍在）；另有一個對照：從不寫 `migration_base_sha` 鍵的 params 變體
  When 對兩份各呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then 兩份的 `S(history.migration)` 都是 `PASS` 且該項的 `detail` 為 `claim=none`（沒有宣稱就沒有可驗的宣稱）
  And `S(history.row_mutated)` 為 `FAIL`，`F(history.row_mutated)` 恰為 C0 的四個舊列 `OBS-SI-001`～`OBS-SI-004` 各一筆 `ROW-MUTATED`（列 001 處置雖仍為 open，但加了第九欄，整列內容變了；追加的確認列不在內）
  And 每筆 finding 的 detail 含 `掌舵者`（要求掌舵者過目）、`cause=changed`，以及 `commit=` 後接 M 的短 sha
  And `overall` 為 `FAIL`、rc 為 `1`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_E_1]"
```

```gherkin
# AT-001-3-E-2
# 對應 AC: AC-001-3 有 sha 卻缺合格的掌舵者確認列時，遷移視為未豁免
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_3_E_2 -q

Feature: 掌舵者確認列的存在與格式

Scenario: 確認列缺漏或不合格的六種變體判紅，合格的對照組判綠
  Given 遷移鏈 repo 的七個變體（各自獨立建立，N 的確認列依下列改法；§5.2 的 `confirm` 參數）：(a) 沒有任何 `decided` 列；(b) 有 `decided` 列但文字不含 M 的 sha；(c) 文字含 M 的 sha 但沒有 `sid` 與 UUID；(d) 有 `sid` 與 UUID 但沒有 `line` 與整數；(e) 文字引用的是 C0 的 sha 而不是 M 的；(f) 該列處置是 `deferred；…` 而非 `decided`，其餘條件皆具；(g) 完整合格（對照組）
  When 對七個變體各呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then (a)～(f)：`S(history.migration)` 為 `FAIL`，`F(history.migration)` 恰為 `(-, MIG-CONFIRM-MISSING)`；同時 `S(history.row_mutated)` 為 `FAIL` 且 `F(history.row_mutated)` 含 C0 的四個舊列（未豁免）
  And (g)：`S(history.migration)` 為 `PASS` 且該項的 `detail` 為 `claim=valid`，`S(history.row_mutated)` 為 `PASS`
  And 確認列的驗證只看存在與格式：(g) 的引言文字內容不被比對（P0 不驗引言，引言回查屬 P2）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_E_2]"
```

```gherkin
# AT-001-3-E-3
# 對應 AC: AC-001-3 migration_base_sha 格式不符、查無此物件、不是 commit、不是 HEAD 的祖先
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_3_E_3 -q

Feature: migration_base_sha 的有效性

Scenario: 六種無效的 sha 一律判紅，遷移不豁免，不靜默放行
  Given 遷移鏈 repo（§5.2，N 之後）；六個變體各自改 `params.json` 的 `migration_base_sha`：(a) `zzzz`；(b) M 的前 12 位（縮寫）；(c) 40 位小寫 hex 但無此物件；(d) 某個 blob 的 40 位 sha；(e) 另一條無父 commit（例如以 `git commit-tree` 建立）的 40 位 sha，物件存在、是 commit、但不是 HEAD 的祖先；(f) M 的完整 sha 轉成大寫
  When 對六個變體各呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then (a)、(b)、(f)：`S(history.migration)` 為 `FAIL`，`F(history.migration)` 恰為 `(migration_base_sha, MIG-SHA-FORMAT)`
  And (c)、(d)：`F(history.migration)` 恰為 `(migration_base_sha, MIG-SHA-UNRESOLVED)`
  And (e)：`F(history.migration)` 恰為 `(migration_base_sha, MIG-SHA-NOT-ANCESTOR)`
  And 六個變體的 `S(history.row_mutated)` 都是 `FAIL` 且 `F(history.row_mutated)` 含 C0 的四個舊列（無效的宣稱不豁免）；`overall` 為 `FAIL`、rc 為 `1`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_E_3]"
```

```gherkin
# AT-001-3-E-4
# 對應 AC: AC-001-3 orig 的附註檔錨點、只在遷移內使用、語法
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_001_3_E_4 -q

Feature: orig 的使用規則

Scenario: 附註檔錨點、遷移之外使用、語法錯誤各被標出
  Given 遷移鏈 repo（§5.2，N 之後；M 之中列 004 的 `orig` 是 `@docs/05_development/SelfImproving_Observation_Ledger_notes.md#OBS-SI-004`，附註檔有對應標題段落）；每個變體各自複製一份、只做一處變異
  When 變體 (a)：刪掉附註檔；(b)：把附註檔中列 004 的標題改成另一個 ID；(c)：把列 004 的錨點改成 `#OBS-SI-003`（附註檔沒有該 ID 的標題）
  And 變體 (d)：新增一個 commit，追加新列 `OBS-SI-006`（M 之後才出現的 ID），其標記含 `orig="…"`
  And 變體 (e)：把列 002 的 `orig` 值改成沒有引號的自由文字
  And 變體 (f)（正向對照）：列 003 的 `orig` 引號內含以反斜線跳脫的雙引號與反斜線，字串閉合正確
  Then (a)：`S(ref.orig_notes)` 為 `FAIL`，`F(ref.orig_notes)` 恰為 `(OBS-SI-004, ORIG-NOTES-MISSING)`
  And (b)、(c)：`F(ref.orig_notes)` 恰為 `(OBS-SI-004, ORIG-NOTES-ANCHOR)`
  And (d)：`S(history.migration)` 為 `FAIL`，`F(history.migration)` 恰為 `(OBS-SI-006, ORIG-OUTSIDE-MIGRATION)`
  And (e)：`S(row.markers)` 為 `FAIL`，`F(row.markers)` 恰為 `(OBS-SI-002, MARK-ORIG-FORMAT)`
  And (f)：`S(row.markers)` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_E_4]"
```

```gherkin
# AT-002-1-1
# 對應 AC: AC-002-1 標記欄語法與封閉詞彙；外部衍生只接受「是」
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_002_1_1 -q

Feature: check 的標記欄判準

Scenario: 標記欄採 key=value 語法與封閉詞彙，違規各被標出，合法的外部衍生通過
  Given 基線有效 repo（§5.1：列 010 的標記含 `外部衍生=是`）；每個情境各自複製一份基線、只做一處變異
  When 情境 (a)：列 003 的標記加上 `外部衍生=否`；(b)：列 004 的標記加上 `外部衍生=`（值空）；(c)：列 005 的標記加上未知鍵 `foo=1`；(d)：列 006 的標記重複一次 `面` 鍵
  And 情境 (e)：列 007 的標記尾端追加一個不含等號的片段 `守衛`；(f)：列 008 的 `回報者` 值改成 `SA;SD`（未加引號的分號，切成兩段，第二段沒有等號）
  And 情境 (g)：列 009 的標記欄整格清空
  And 情境 (h)：列 003 加上 `orig=自由文字`（無引號）、列 004 加上內含以反斜線跳脫的雙引號與反斜線且閉合正確的 `orig` 引號字串、列 005 加上 `orig=@docs/x.md#OBS-SI-001`（只驗語法）
  Then 情境 (a)～(f)：`F(row.markers)` 依序恰為 `(OBS-SI-003, MARK-VALUE)`、`(OBS-SI-004, MARK-SYNTAX)`、`(OBS-SI-005, MARK-UNKNOWN-KEY)`、`(OBS-SI-006, MARK-SYNTAX)`、`(OBS-SI-007, MARK-SYNTAX)`、`(OBS-SI-008, MARK-SYNTAX)`
  And 情境 (g)：`F(row.markers)` 恰為 `(OBS-SI-009, MARK-FACE-MISSING)`；`F(row.provenance)` 恰為 `(OBS-SI-009, SOURCE-MISSING)` 與 `(OBS-SI-009, REPORTER-MISSING)`
  And 情境 (h)：`F(row.markers)` 恰為 `(OBS-SI-003, MARK-ORIG-FORMAT)`（列 004 的合法跳脫字串與列 005 的 `@` 形態語法通過）
  And 基線 `S(row.markers)` 為 `PASS`（列 010 的 `外部衍生=是` 通過）；AC 後半的外部衍生列不得單獨充當提案證據，屬 P1 的 `prop-new` 前置檢查，P0 的 SOP 條文由 SOP 骨架的 AT 檢核
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_002_1_1]"
```

```gherkin
# AT-002-2-1
# 對應 AC: AC-002-2 來源與回報者必備；來源值域
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_002_2_1 -q

Feature: check 的來源與回報者判準

Scenario: 來源或回報者缺漏、值空、來源值域外各被標出，五個合法來源值通過
  Given 基線有效 repo；每個情境各自複製一份基線、只做一處變異
  When 情境 (a)：列 003 的標記移除 `來源` 鍵；(b)：列 004 的標記移除 `回報者` 鍵；(c)：列 005 的 `來源` 值清空；(d)：列 006 的 `回報者` 值清空；(e)：列 007 的 `來源` 改成 `網路`
  And 情境 (f)：列 008 的 `來源` 依序改成 `人`、`代理`、`工具`、`逐字稿`、`帳本`（五個合法值，各一個情境）
  Then (a)：`F(row.provenance)` 恰為 `(OBS-SI-003, SOURCE-MISSING)`；(b)：恰為 `(OBS-SI-004, REPORTER-MISSING)`
  And (c)：`F(row.provenance)` 恰為 `(OBS-SI-005, SOURCE-MISSING)` 且 `F(row.markers)` 含 `(OBS-SI-005, MARK-SYNTAX)`（值空的鍵視為缺鍵）；(d)：`F(row.provenance)` 恰為 `(OBS-SI-006, REPORTER-MISSING)` 且 `F(row.markers)` 含 `(OBS-SI-006, MARK-SYNTAX)`
  And (e)：`F(row.provenance)` 恰為 `(OBS-SI-007, SOURCE-VALUE)`；(f)：五個情境的 `S(row.provenance)` 皆為 `PASS`
  And 基線 `S(row.provenance)` 為 `PASS`；觀察本身不自動啟動任何行為，由 `check` 的零副作用判準承擔（見 AC-030-2 的 AT）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_002_2_1]"
```

```gherkin
# AT-003-1-1
# 對應 AC: AC-003-1 P0 不新增常駐行程、排程或 hook；動詞範圍；SOP 的啟動條件條文
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_003_1_1 -q

Feature: 迴圈只由事件啟動，P0 無常駐機制

Scenario: 原始碼無常駐或排程字樣、動詞只有 check、未註冊 hook、SOP 載明五類啟動事件
  Given 真 repo 的 `tools/selfimproving.py` 與 P0 驗收時存在的每個 `tools/lib/selfimproving/*.py`、根 `.claude/settings.json`、`docs/05_development/SelfImproving_Operations_SOP.md`
  When 以 R26 的禁用字樣正規式逐檔掃描上述原始碼；呼叫 `main(["status"])` 與 `main(["prop-new"])`；讀 `.claude/settings.json` 全文；以 R25 (2) 的判準檢查 SOP
  And 自證：把 R26 的每個禁用字樣各造一個合成字串送進掃描函式，再送一個乾淨字串；對 SOP 文字逐一刪去 R25 (2) 的各片段（`(a)`～`(e)` 標籤之一、否定句那一行、含 `si status` 的行、`視窗開場`、`收尾`）造出副本，各送進 SOP 判準
  Then 原始碼掃描零命中；以動詞 `status` 與動詞 `prop-new` 呼叫 `main` 的 rc 都是 `3`、stdout 為空；`.claude/settings.json` 全文不含 `selfimproving`（不分大小寫）
  And SOP 判準對真 SOP 為合格：含 `(a)`～`(e)` 五個標籤並依序接 `掌舵者指令`、`第二次`、`P≤2`、`再開症狀`、`容量事件`；含同時有 `日曆`、`版本號`、`覆蓋度`、`每 N 輪` 的否定句；含 `si status` 且同節含 `視窗開場` 與 `收尾`
  And 自證結果：每個禁用字樣的合成字串都判命中、乾淨字串判不命中；SOP 的每個刪去副本都判不合格（判準函式不是恆真）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_003_1_1]"
```

```gherkin
# AT-003-2-1
# 對應 AC: AC-003-2 零筆或低於反空轉下限記為未判，而不是通過
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_003_2_1 -q

Feature: 零筆不等於通過

Scenario: 資料列數低於 min_obs_rows 判未判（NE，rc 2）；等於下限通過；SOP 載明無事件
  Given 以「烘入第一個 commit」的建法（§2 變異慣例）建出四個變體，使歷史比對項為 PASS：(A) 9 列（列 001～009）而 `min_obs_rows` 為 10；(B) 只有表頭、0 列；(C) 9 列而 `min_obs_rows` 為 9；(D) 基線（10 列、下限 10）
  When 對四個變體各呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then (A)：`S(ledger.vacuity)` 為 `NE`、`blocking` 為 true，`F(ledger.vacuity)` 恰為 `(-, LEDGER-BELOW-FLOOR)`；`overall` 為 `NE`、rc 為 `2`
  And (B)：`rows` 為 `0`，`F(ledger.vacuity)` 恰為 `(-, LEDGER-BELOW-FLOOR)`，`overall` 為 `NE`、rc 為 `2`，不是 `PASS`
  And (C) 與 (D)：`S(ledger.vacuity)` 為 `PASS`（列數等於下限算通過）；(D) 的 rc 為 `0`
  And SOP 判準 R25 (3) 對真 SOP 為合格（含同時有 `無事件` 與 `通過` 的一行）；刪去該行的副本判不合格
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_003_2_1]"
```

```gherkin
# AT-003-3-1
# 對應 AC: AC-003-3 產出數量不構成再開理由（流程型，SCG-4 以文件檢核）
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_003_3_1 -q

Feature: 產出數量不觸發再開

Scenario: SOP 載明產出數量不構成再開理由，且 check 沒有以筆數或排程為參數的旗標
  Given 真 SOP 與真 `tools/selfimproving.py`
  When 以 R25 (4) 判準檢查 SOP；對刪去該行的副本再檢一次；呼叫 `main(["check", "--help"])` 取旗標清單
  Then SOP 判準對真 SOP 為合格（含同時有 `產出數量` 與 `T1` 的一行）、對刪去副本為不合格
  And `check --help` 的 stdout 以正規式 `--[a-z][a-z-]*` 取出的旗標集合恰為 `--repo`、`--ledger`、`--params`、`--json`、`--help`，沒有任何以筆數、覆蓋度、日曆或排程為參數的旗標
  And 本 AT 為流程型：語意（再開僅依範本〈🏁〉T1～T4，產出數量不構成理由）由實跑檢核 V8 對照 PRD AC-SI-03-3 以文件檢核；機器面只鎖上述兩個可觀察代位
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_003_3_1]"
```

```gherkin
# AT-004-1-1
# 對應 AC: AC-004-1 引用完整性——各種存在的引用都解析得到
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_1_1 -q

Feature: 存在的引用判通過

Scenario: 主缺陷帳本、封存檔、兩個姊妹帳本、OBS 封存檔、其他文件內的引用都解析得到
  Given 基線有效 repo（§5.1：缺陷帳本家族含主帳本、`AutoSDD_Defect_Log_archive_01.md`、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md` 各一個以執行期組出的 DEF 編號為主鍵的列；另有 `SelfImproving_Observation_Ledger_archive_01.md` 內一個以執行期組出的 OBS 編號為主鍵的列）
  When 在工作樹把列 004、005、006 的處置分別改成引用封存檔、外部阻塞帳本、結構性長債帳本內的 DEF（列 003 維持引用主帳本內的 DEF）；把列 008 的標記加上 `rel=` 接 OBS 封存檔內那個編號；新增未追蹤檔 `docs/notes/refs.md`，內容提及 `OBS-SI-001` 與 `OBS-SI-005`
  And 呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then `S(ref.def)` 為 `PASS`、`S(ref.obs)` 為 `PASS`、`S(ref.orig_notes)` 為 `PASS`，三者的 `findings` 皆為空
  And 帳本與封存檔中列首格的定義處不被當成引用；未追蹤但未被忽略的檔案內的提及會被納入掃描且解析得到
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_1_1]"
```

```gherkin
# AT-004-1-E-1
# 對應 AC: AC-004-1 引用不存在的 OBS 判不合規
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_1_E_1 -q

Feature: 懸空的 OBS 引用

Scenario: 五種位置的不存在 OBS 編號都被標出，同編號多處只報一筆
  Given 基線有效 repo；測試以執行期字串相加組出一個不存在的 OBS 編號（記為 X；同樣組出另一個 Y），使測試原始碼不含字面的不存在編號；每個情境各自複製一份基線、只做一處變異
  When 情境一：列 003 的處置改成 `merged@` 接 X；情境二：列 004 的症狀文字提及 X；情境三：新增未追蹤檔 `docs/notes/readme.md`，提及 X 與存在的 `OBS-SI-001`
  And 情境四：新增附註檔 `docs/05_development/SelfImproving_Observation_Ledger_notes.md`，其中有標題為 X 的 `## ` 段落；情境五：列 005 的標記加上 `rel=` 接 X
  And 情境六：列 004 的症狀與 `docs/notes/readme.md` 兩處都提及 X，另有一處提及 Y
  And 情境七：X 在七處被提及（列 004 的症狀，加另外六個未追蹤檔 `docs/notes/m1.md`～`docs/notes/m6.md` 各一處）
  Then 情境一到五各自：`S(ref.obs)` 為 `FAIL`，`F(ref.obs)` 恰為 `(X, OBS-REF-DANGLING)`，該 finding 的 detail 含引用處的 `<相對路徑>:<行號>`
  And 情境六：`F(ref.obs)` 恰為 `(X, OBS-REF-DANGLING)` 與 `(Y, OBS-REF-DANGLING)` 兩筆（同編號多處只報一筆），X 那筆的 detail 列出兩處引用位置
  And 情境七：`F(ref.obs)` 恰為一筆 `(X, OBS-REF-DANGLING)`，其 detail 恰列 5 處 `<相對路徑>:<行號>`，其餘兩處以 `…+2` 表示（R18 (a) 的截斷）
  And 存在的 `OBS-SI-001` 與帳本列首格的定義處都不被報
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_1_E_1]"
```

```gherkin
# AT-004-1-E-2
# 對應 AC: AC-004-1 引用不存在的 DEF 判不合規；缺陷帳本家族全缺時判未判
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_1_E_2 -q

Feature: 懸空的 DEF 引用

Scenario: 處置引用不存在的 DEF 判紅；存在於四個帳本檔任一者皆通過；帳本家族全缺時未判
  Given 基線有效 repo（§5.1：缺陷帳本家族四個檔各有一個以執行期組出的 DEF 編號為主鍵的列）；每個情境各自複製一份基線、只做一處變異
  When 情境一：列 004 的處置改成 `DEF-200-` 接一個執行期組出、不存在於任何帳本檔的編號；列 005、006、007、008 的處置分別改成主帳本、封存檔、外部阻塞帳本、結構性長債帳本內存在的 DEF（對照列）
  And 情境二：刪掉 `docs/06_quality/` 下全部缺陷帳本家族檔案
  Then 情境一：`S(ref.def)` 為 `FAIL`，`F(ref.def)` 恰為 `(OBS-SI-004, DEF-REF-DANGLING)`（四個對照列不被報）
  And 情境二：`S(ref.def)` 為 `NE`、`blocking` 為 true，其 finding 碼為 `SOURCE-UNAVAILABLE`
  And 基線 `S(ref.def)` 為 `PASS`（列 003 引用主帳本內的 DEF）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_1_E_2]"
```

```gherkin
# AT-004-1-E-3
# 對應 AC: AC-004-1 載體尚未建立的 ID 家族印未判，不判通過也不判不合規
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_1_E_3 -q

Feature: 載體未建立的家族

Scenario: PROP、ATT、DEC、APP、MEA、RUN 家族的提及印 NE（nonblocking），不影響 rc
  Given 基線有效 repo（列 008 的處置是 `proposed@PROP-SI-` 接一個執行期組出的三位數編號）；每個情境各自複製一份基線、只做一處變異
  When 情境一：不變異；情境二：新增未追蹤檔 `docs/notes/x.md`，內含 `ATT-SI-`、`DEC-SI-`、`APP-SI-`、`MEA-SI-`、`RUN-SI-` 各接一個執行期組出的三位數編號
  And 情境三：把列 008 的處置改成 `open`（移除所有此類提及）
  Then 情境一與情境二：`S(ref.carrier_families)` 為 `NE`、`blocking` 為 false，finding 的 `code` 為 `CARRIER-NOT-ESTABLISHED`；情境一的 detail 含 `families=PROP-SI` 與 `count=1`，情境二的 detail 含 `families=APP-SI,ATT-SI,DEC-SI,MEA-SI,PROP-SI,RUN-SI` 與 `count=6`
  And 兩個情境的 `overall` 不因該項變紅：除該項外全為 `PASS` 時 rc 為 `0`；沒有任何 `level` 為 `fail` 的 finding 來自該項
  And 情境三：`S(ref.carrier_families)` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_1_E_3]"
```

```gherkin
# AT-004-2-1
# 對應 AC: AC-004-2 真缺陷處置須為 DEF（SOP 條文代位；流程型）
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_2_1 -q

Feature: 真缺陷升 DEF

Scenario: SOP 載明符合缺陷帳本收錄定義的真缺陷其處置須為 DEF
  Given 真 SOP
  When 以 R25 (5) 判準檢查 SOP；對刪去該行的副本再檢一次
  Then 判準對真 SOP 為合格（含同時有 `DEF-<id>` 與 `真缺陷` 的一行）、對刪去副本為不合格
  And 機器面的代位已在 DEF 引用的懸空判準承擔（`ref.def`，見 AC-004-1 的 AT）；某筆觀察是否符合缺陷帳本收錄定義屬判斷，P0 不機械化，由實跑檢核 V8 以文件檢核
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_2_1]"
```

```gherkin
# AT-004-3-1
# 對應 AC: AC-004-3 處置 open 轉終值一次、追加新列、追加更正列、格式整理皆放行
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_3_1 -q

Feature: 合法的帳本演進不被標 ROW-MUTATED

Scenario: open 轉終值一次、追加列、追加更正列、空白與換行整理都放行
  Given 遷移鏈 repo（§5.2，N 之後，已豁免；列 001 處置仍為 `open`）
  When 在 N 之後依序加三個 commit：K1＝列 001 的處置由 `open` 改成 `deferred；再開症狀：同一症狀第二次出現`（只動處置格）；K2＝追加新列 `OBS-SI-006`；K3＝追加更正列 `OBS-SI-007`，標記含 `rel=corrects:OBS-SI-002`
  And 另在工作樹（不 commit）整理格式：各欄之間的空白數改變、整個檔換行改成 CRLF
  And 呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then `S(history.row_mutated)` 為 `PASS` 且 `findings` 為空；`overall` 為 `PASS`、rc 為 `0`
  And K1、K2、K3 各自只動帳本一個檔（`git show --name-only --format=` 驗證）；K1 只改列 001 的處置格
  And SOP 條文：以 R25 (9) 判準檢查真 SOP（擷取者節含同時有 `追加`、`rel=corrects:`、`ROW-MUTATED`、`open`、`終值` 的一行）為合格；對刪去該行的副本、與只把該行的 `終值` 一詞刪去（例外句不見）的副本再檢，皆須判不合格（M 之後帳本只追加、處置欄 `open`→終值一次除外的人為慣例以條文代位，機器面由本 AT 的 `history.row_mutated` 判準承擔，K1 即該例外的放行實例）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_3_1]"
```

```gherkin
# AT-004-3-E-1
# 對應 AC: AC-004-3 遷移之後的原地改寫被標 ROW-MUTATED
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_3_E_1 -q

Feature: 遷移之後的原地改寫

Scenario: 改症狀、二次改處置、刪列、改號、混改各被標出，並要求掌舵者過目
  Given 遷移鏈 repo（§5.2，N 之後，已豁免；列 001 為 open、列 002 與 003 的處置為終值、列 005 為確認列）
  When 在 N 之後依序加五個 commit：D1＝改列 002 的症狀格；D2＝列 003 的處置由 `deferred；…` 改成 `retired；依據` 接一個座標（已是終值，第二次改）；D3＝刪除列 004
  And D4＝把列 005（確認列）的 ID 改成另一個未用過的更大編號（舊 ID 消失）；D5＝同一個 commit 內把列 001 的處置由 `open` 改成終值（合法的一半）並同時改它的情境格（不合法的一半）
  And 呼叫 `main(["check", "--repo", <repo>, "--json"])`
  Then `S(history.row_mutated)` 為 `FAIL`，`F(history.row_mutated)` 恰為列 002、003、004、005、001 各一筆 `ROW-MUTATED`
  And 各筆 detail 的 `cause` 依序為 `changed`、`changed`、`deleted`、`deleted`、`changed`，`commit=` 後依序為 D1、D2、D3、D4、D5 的短 sha，且都含 `掌舵者`
  And D4 的新 ID 作為新列不被標；確認列改號後仍符合 R19 (d)，`S(history.migration)` 維持 `PASS`；`overall` 為 `FAIL`、rc 為 `1`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_3_E_1]"
```

```gherkin
# AT-004-3-E-2
# 對應 AC: AC-004-3 工作樹未提交的改寫也被比對；誠實劃界
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_3_E_2 -q

Feature: 工作樹改寫與誠實劃界

Scenario: 未提交的改寫與 HEAD 比對；工作樹內的多步改寫只看淨差異
  Given 遷移鏈 repo（§5.2，N 之後，已豁免，工作樹乾淨；列 001 為 open）；每個情境各自複製一份、只做一處變異
  When 情境一：只在工作樹改列 002 的症狀（不 commit）
  And 情境二：只在工作樹把列 001 的處置由 `open` 改成 `deferred；再開症狀：甲`
  And 情境三：只在工作樹把列 001 的處置先改成 `deferred；再開症狀：甲`、再改成 `retired；依據` 接一個座標（同一工作樹內兩步）
  And 情境四：只在工作樹刪掉列 003
  Then 情境一：`F(history.row_mutated)` 恰為 `(OBS-SI-002, ROW-MUTATED)`，detail 含 `commit=WORKTREE`
  And 情境二：`S(history.row_mutated)` 為 `PASS`
  And 情境三：`S(history.row_mutated)` 為 `PASS`（誠實劃界，PRD AC-SI-04-3：未提交的多次改寫無歷史可比、不可偵測；工具對淨差異為 open 轉終值者不得報紅，也不得假裝偵測中間步驟）
  And 情境四：`F(history.row_mutated)` 恰為 `(OBS-SI-003, ROW-MUTATED)`，detail 含 `cause=deleted`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_3_E_2]"
```

```gherkin
# AT-004-3-E-3
# 對應 AC: AC-004-3 無歷史可比與帳本在 repo 外
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_004_3_E_3 -q

Feature: 歷史比對的兩個邊界

Scenario: 帳本從未被提交時無歷史可比；帳本在 repo 外時判未判
  Given 基線有效 repo 的兩個變體：(A) 帳本檔只存在於工作樹、從未被 `git add` 或提交（`make_valid_repo` 在兩個 commit 之後才寫入帳本；列 002 的 `fixed@` 仍指向第一個 commit）；(B) 基線原樣，另在 tmp 內、repo 目錄之外放一份內容相同的合規帳本
  When 對變體 (A) 呼叫 `main(["check", "--repo", <repo>, "--json"])`
  And 對變體 (B) 呼叫 `main(["check", "--repo", <repo>, "--ledger", <repo 之外那份帳本的絕對路徑>, "--json"])`
  Then (A)：`S(history.row_mutated)` 為 `PASS`，該項 `detail` 為 `no-history`，`findings` 為空；`S(history.migration)` 為 `PASS` 且 `detail` 為 `claim=none`；rc 為 `0`
  And (B)：`S(history.row_mutated)` 為 `NE`、`blocking` 為 true，`F(history.row_mutated)` 恰為 `(-, SOURCE-UNAVAILABLE)`；不依賴 git 歷史的逐列項目照常評估（`rows` 為 `10`、`S(row.enums)` 為 `PASS`）
  And (B) 的 `overall` 為 `NE`、rc 為 `2`（無 FAIL 時）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_004_3_E_3]"
```

```gherkin
# AT-029-1-1
# 對應 AC: AC-029-1 流程不當或 BUG 當下入帳，子代理以「流程摩擦」節為入口（流程型，SOP 條文代位）
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_029_1_1 -q

Feature: 流程摩擦當下入帳

Scenario: SOP 的擷取者節載明文字交卷的流程摩擦入口
  Given 真 SOP
  When 以 R25 (1) 的擷取者節判準與 R25 (8) 判準檢查 SOP；對刪去相關片段的副本（逐一刪去 `文字交卷`、`流程摩擦`、含 `流程摩擦` 與 `OBS-SI-004` 的那一行）再檢
  Then 判準對真 SOP 為合格（擷取者節含 `文字交卷` 與 `流程摩擦`，且含同時有 `流程摩擦` 與 `OBS-SI-004` 的一行）；每個刪去副本皆判不合格
  And 流程型：本 P0 開發期間 Developer 棒與 QA 棒的文字交卷必含流程摩擦節，節內項目於 SCG-4 前已由主控入帳為 OBS 列（實跑檢核 V8）；機器可驗的部分只有入帳後的列通過 `check`（實跑檢核 V2）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_029_1_1]"
```

```gherkin
# AT-029-2-1
# 對應 AC: AC-029-2 對迴圈自身的改進標 loop-self 轉交，本迴圈不得提案修改自己（SOP 條文加受保護面代位）
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_029_2_1 -q

Feature: loop-self 轉交

Scenario: SOP 載明 loop-self 轉交規則，且迴圈自身檔案列在不可進化面內
  Given 真 SOP 與真 `docs/06_quality/SelfImproving_Protocol/params.json`
  When 以 R25 (7) 判準檢查 SOP；對刪去該行的副本再檢；讀 `params.json` 的 `non_evolvable_globs`
  Then SOP 判準對真 SOP 為合格（含同時有 `loop-self`、`轉交`、`T1` 的一行）、對刪去副本為不合格
  And `non_evolvable_globs` 含 `docs/06_quality/SelfImproving_Protocol/**`、`docs/01_requirements/SelfImproving_PRD.md`、`tools/selfimproving.py`、`tools/lib/selfimproving/**` 四項（預算、閘門、停機條件、指標定義與迴圈腳本都在不可進化面內，PRD NFR-SI-02-1 的 iii、iv 兩類）
  And 流程型：語意（提出時標 `loop-self`、僅經掌舵者 T1 或 PRD 修訂）由實跑檢核 V8 對照 PRD AC-SI-29-2 以文件檢核
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_029_2_1]"
```

```gherkin
# AT-030-1-1
# 對應 AC: AC-030-1 輸出形態、rc 0 與 1、文字與 JSON 一致、鍵序、相對路徑語意、非 UTF-8 管線下中文不降解
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git + 子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_030_1_1 -q

Feature: check 的輸出契約

Scenario: in-process 與子行程兩條路徑的輸出一致，且在非 UTF-8 管線下中文不降解
  Given 基線有效 repo（綠），以及一份紅的變體（列 003 的分類改成 `Process`，其餘不變，仍可解析）
  When in-process：對兩份各呼叫 `main(["check", "--repo", <repo>])` 與 `main(["check", "--repo", <repo>, "--json"])`
  And 子行程：以 `[sys.executable, <repo 根>/tools/selfimproving.py, "check", "--repo", <紅 repo>, "--json"]` 執行，cwd 設為另一個暫存目錄，環境變數 `PYTHONIOENCODING` 設為 `cp950`（其餘沿用 §5.5 的 hermetic 環境），以位元組擷取 stdout 與 stderr
  And 相對路徑語意（R2）：在另一個暫存目錄（當作 cwd）放兩份誘餌檔，路徑與預設帳本、預設 `params.json` 的 repo 相對路徑相同但內容是壞的（帳本只有表頭、`params.json` 內容為 `{}`），再以 repo 相對路徑 `docs/06_quality/SelfImproving_Observation_Ledger.md` 與 `docs/06_quality/SelfImproving_Protocol/params.json` 當作 `--ledger` 與 `--params`，以該 cwd 子行程呼叫綠 repo 的 `check --json`
  Then 綠：rc 為 `0`；紅：rc 為 `1`，`overall` 為 `FAIL`，文字形態在 `overall=` 行之後有一行 `obs-draft:` 與恰一行以 `| OBS-SI-` 起頭的草稿列
  And 文字形態與 JSON 形態的 rc、各項 `status`、各項 finding 的 `(subject, code)` 集合逐項一致；紅變體的 `F(row.enums)` 恰為 `(OBS-SI-003, ENUM-CATEGORY)`，該 finding 的 detail 含 `分類`
  And 文字形態逐行符合 R3 的行文法（首行、項目行、縮排的 finding 行、`overall=` 行）；沒有任何一行含 ANSI 跳脫序列
  And 子行程的 rc 為 `1`；stdout 位元組可嚴格以 UTF-8 解碼並可 `json.loads`，其中 `ENUM-CATEGORY` 的 detail 解碼後含完整的 `分類` 二字；stderr 沒有 `Traceback`
  And 相對路徑那一次的 rc 為 `0`、`rows` 為 `10`（相對路徑相對於 `--repo` 而不是 cwd；若誤以 cwd 解析，會讀到誘餌檔而 rc 不為 `0`）
  And JSON 鍵序（R4）：以 `json.loads` 的 `object_pairs_hook=list` 取得的頂層鍵序恰為 `overall`、`rc`、`fingerprint`、`fingerprint_parts`、`rows`、`items`、`obs_draft`；`fingerprint_parts` 的鍵序為 `manifest`、`metrics_rev`、`check_rules_rev`；`items` 元素的鍵序為 `id`、`status`、`blocking`、`detail`、`findings`；`findings` 元素的鍵序為 `subject`、`code`、`level`、`detail`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_030_1_1]"
```

```gherkin
# AT-030-1-E-1
# 對應 AC: AC-030-1 用法錯誤與讀不到輸入一律 rc 3；--help
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_030_1_E_1 -q

Feature: check 的 rc 3 與求助

Scenario: 用法錯誤與讀不到輸入一律 rc 3 且 stdout 為空；--help rc 0
  Given 一個 tmp 目錄與基線有效 repo
  When 依序呼叫（每次只有指名的這一項不合法）：`main([])`、`main(["status"])`、`main(["check", "--bogus"])`、`main(["check", "--repo", <不存在的路徑>])`、`main(["check", "--repo", <一個檔案>])`、`main(["check", "--repo", <repo>, "--ledger", "no/such.md"])`、`main(["check", "--repo", <repo>, "--params", "no/such.json"])`
  And 另造四份：帳本含非 UTF-8 位元組 0xff 0xfe；`params.json` 內容為 `not json`；`params.json` 內容為 JSON 陣列 `[]`；`--ledger` 指向一個目錄
  And 再呼叫 `main(["--help"])` 與 `main(["check", "--help"])`
  Then 前述十一次的 rc 都是 `3`，stdout 為空字串，stderr 非空
  And 兩次 `--help` 的 rc 都是 `0`，stdout 含 `check`，且 `check --help` 的 stdout 含 `--repo`、`--ledger`、`--params`、`--json`
  And 沒有任何一次拋出例外，`SystemExit` 亦不外洩到呼叫端
  And rc 2 專屬於無 FAIL 但有 blocking NE 的情形，用法錯誤不得得到 2（argparse 的預設用法錯誤碼在 `main` 內被改成 3）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_030_1_E_1]"
```

```gherkin
# AT-030-2-1
# 對應 AC: AC-030-2 唯讀零副作用、純標準庫、git 子行程環境淨化
# 測試類型: Integration
# 自動化工具: unittest／pytest + tmp 目錄 + 真 git + 子行程記錄替身
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_030_2_1 -q

Feature: check 的純度

Scenario: check 不寫任何檔、不連網、子行程只有環境被淨化的 git
  Given 基線有效 repo（綠）與一份紅的變體（含懸空的 OBS 引用與缺 tz）；記下兩份工作樹的檔案摘要（每個檔的相對路徑與 sha256，不含 `.git/`）與 `git status --porcelain` 的輸出
  When 設定環境變數 `GIT_DIR` 指向另一個無關的 repo、`GIT_INDEX_FILE` 指向一個不存在的路徑，並以記錄型替身包住 `subprocess.run`（記下每次呼叫的 argv、`env`、`shell`、`timeout`、`encoding`、`errors`）與 `subprocess.Popen`（只記建構次數）
  And 對兩份各呼叫 `check` 的文字形態與 `--json` 形態各一次；另在未設定 `GIT_DIR` 與 `GIT_INDEX_FILE` 時各呼叫一次作對照
  Then 呼叫前後兩份的檔案摘要與 `git status --porcelain` 完全相同（沒有新檔、沒有被改的檔、沒有 `.lock`、沒有被寫的 OBS 帳本）
  And 兩份的結果與未設定 `GIT_DIR` 時完全相同（工具自行把定位用的 `GIT_*` 變數自子行程環境移除）
  And 記錄到至少一次 `subprocess.run` 呼叫，且 `Popen` 的建構次數等於 `run` 的呼叫次數（沒有繞過 `run` 的直接 `Popen`、`check_output` 或 `os.system`）；每次呼叫：argv 的第一個元素去掉目錄與副檔名後是 `git`，第二個元素是 `-C`，第三個元素解析後等於 `--repo` 的路徑，`shell` 不為真，`timeout` 是正數，`encoding` 為 `utf-8`、`errors` 為 `replace`，`env` 是一個字典且不含 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE`、`GIT_COMMON_DIR`、`GIT_PREFIX`、`GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES`，且 `GIT_OPTIONAL_LOCKS` 為 `0`
  And 以 AST 檢視 `tools/selfimproving.py` 與每個 `tools/lib/selfimproving/*.py`：每個絕對 import 的頂層模組名屬 `sys.stdlib_module_names`，或是 `_stdio_utf8`、`lib`（含 `lib.selfimproving.*`；`tools/lib/` 沒有 `__init__.py`，`from lib import …` 靠 `tools/` 在 `sys.path` 上；套件內相對 import 視為本地模組）；沒有 `socket`、`urllib`、`http`、`requests`、`ftplib`、`smtplib`、`asyncio` 的 import
  And 以正規式掃描上述原始碼：沒有寫入形原語（`write_text`、`write_bytes`、`.mkdir(`、`os.remove`、`os.unlink`、`os.rename`、`os.replace`、`shutil.`、以 `w`、`a`、`x` 模式呼叫的 `open(`）；判準函式自證：對含這些原語的合成字串判命中、對乾淨字串判不命中
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_030_2_1]"
```

```gherkin
# AT-030-3-1
# 對應 AC: AC-030-3 判準指紋：可重放、只隨判準變
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_030_3_1 -q

Feature: 判準指紋

Scenario: 指紋逐字可重放，只隨協定目錄內容與兩個 rev 變
  Given 基線有效 repo（協定目錄含 `params.json` 與 `metrics.md`）；每個情境各自複製一份基線、只做一處變異
  When 情境一：不變異，連續呼叫兩次 `main(["check", "--repo", <repo>, "--json"])`
  And 情境二：把 `params.json` 與 `metrics.md` 的換行改成 CRLF；情境三：把 `w_evt` 由 2 改成 3；情境四：把 `metrics_rev` 由 1 改成 2；情境五：在協定目錄新增一個檔 `extra.md`；情境六：只改帳本列 003 的症狀文字
  Then 情境一：兩次的 `fingerprint` 與整個 stdout 逐字相同；`fingerprint` 以 `sha256:` 起頭接 64 位小寫 hex；`fingerprint_parts` 含 `manifest`、`metrics_rev`、`check_rules_rev` 三個鍵，`check_rules_rev` 為不小於 1 的整數
  And 測試以 R7 的算法在測試內獨立重算 `manifest` 與 `fingerprint`，與輸出逐字相同
  And 情境二：`fingerprint` 與基線相同（CRLF 與 LF 等價）；情境三、四、五：`fingerprint` 都與基線不同，且三者彼此不同（`metrics_rev` 變時 `fingerprint_parts.metrics_rev` 為 2）
  And 情境六：`fingerprint` 與基線相同（指紋是判準的指紋，不隨帳本資料變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_030_3_1]"
```

```gherkin
# AT-030-3-2
# 對應 AC: AC-030-3 OBS 草稿列：可貼入、自身零 finding、位元組上限
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_030_3_2 -q

Feature: 可貼入的 OBS 草稿列

Scenario: 紅的 check 印出一行草稿列，貼入帳本後該列自身零 finding
  Given 基線有效 repo 的紅變體：列 003 的分類改成 `Process`、列 004 的處置改成 `TODO`（仍可解析）；另一份「至少六個判定項為紅」的變體（時間、處置枚舉、座標、位元組、控制字元、引用各有一處）
  When 對第一份呼叫 `main(["check", "--repo", <repo>, "--json"])` 取 `obs_draft`，再以文字形態呼叫一次取草稿列
  And 把草稿列追加到該 repo 帳本檔的末尾（測試自己寫、不 commit），再呼叫 `check --json`
  And 對第二份變體呼叫 `check --json` 取 `obs_draft`
  Then rc 為 `1`；`obs_draft` 恰為一行；依 R9 切欄得 9 欄；ID 為基線最大 ID 加一（`OBS-SI-011`，三位零補齊）；時間符合 `YYYY-MM-DD HH:MM ±HH:MM`；情境、分類（`bug`，PRD NFR-SI-09-3）、嚴重度、處置、標記依 R6 的固定值
  And 症狀含 `rc=1` 與紅項目的 item_id（`row.enums`）；證據座標含反引號包住的 `python tools/selfimproving.py check` 與 `判準指紋 sha256:`
  And 文字形態的草稿列與 JSON 的 `obs_draft` 在時間以外逐字相同
  And 貼入草稿列後再跑的 `check --json`：所有 finding 的 subject 集合不含 `OBS-SI-011`（草稿列在全部逐列判準下零 finding）；列 003、004 的原 finding 仍在
  And 第二份變體的草稿列位元組數不超過 `row_max_bytes`，症狀只列前 5 個非 PASS 項並尾接 `…等 <k> 項`（k 為非 PASS 項總數）
  And 綠的 `check`（rc 為 0）沒有 `obs_draft`（JSON 為 null、文字形態沒有 `obs-draft:` 行）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_030_3_2]"
```

```gherkin
# AT-031-1-1
# 對應 AC: AC-031-1 真 params.json 的格式、鍵集合、型別範圍，與 PRD 及根 CLAUDE.md 一致
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案 + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_1_1 -q

Feature: 協定目錄的 params.json

Scenario: 真 params.json 的格式與內容通過 check 的對表
  Given 真 repo 的 `docs/06_quality/SelfImproving_Protocol/params.json`（P0 交付物 D3）
  When 以 UTF-8 位元組讀入並 `json.loads`
  And 另建一個合成 repo（基線檔案配置，帳本與缺陷帳本仍是合成的），但把真 `params.json`、真 PRD、真根 `CLAUDE.md` 的複本放到對應位置，呼叫 `main(["check", "--repo", <該 repo>, "--json"])`；測試不讀真帳本、不跑真 repo 的 `check`
  Then 檔案開頭沒有 BOM、不含 CR、結尾有換行、頂層是物件、鍵依位元組序遞增
  And 鍵集合含 R21 登記表的 23 個鍵（`check` 不因多出的鍵而紅；D3 交付當下恰為這 23 鍵，由實跑檢核 V6 核對）；每個登記鍵的型別與範圍符合表（整數不是布林；兩個比例鍵大於 0 且不大於 1；`migration_base_sha` 是 null 或 40 位小寫 hex；兩個 glob 清單是非空字串陣列）
  And 合成 repo 的 `S(params.keys)`、`S(params.globs)`、`S(params.coupling)` 皆為 `PASS`（`non_evolvable_globs` 與真 PRD 加真根 `CLAUDE.md` 現算的必備集合相等，`w_opp` 不小於 `w_min`）
  And 初值對 PRD 座標的逐項核對只在 D3 提交當下做一次（實跑檢核 V6），本 AT 不斷言值，避免掌舵者日後調參使測試過期
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_1_1]"
```

```gherkin
# AT-031-1-E-1
# 對應 AC: AC-031-1 缺鍵判紅；取不到所需參數的項目判未判
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_1_E_1 -q

Feature: params.json 的必備鍵

Scenario: 登記表的每個鍵缺少時各被標出；取不到所需參數的項目判未判，而不是以預設值頂替
  Given 基線有效 repo；每個子情境各自複製一份基線、只刪 `params.json` 的一個鍵
  When 對登記表的 23 個鍵各刪除一個（23 個子情境，以 `subTest` 逐鍵）
  Then 每個子情境：`S(params.keys)` 為 `FAIL`，`F(params.keys)` 恰為 `(<被刪的鍵>, PARAM-MISSING)`
  And 取不到所需參數的項目為 `NE`（blocking，碼 `SOURCE-UNAVAILABLE`）：刪除 `row_max_bytes` 時 `S(row.bytes)` 為 `NE`；刪除 `min_obs_rows` 時 `S(ledger.vacuity)` 為 `NE`；刪除 `ledger_warn_bytes` 或 `ledger_fail_bytes` 時 `S(ledger.volume)` 與 `S(params.coupling)` 皆為 `NE`；刪除 `w_opp` 或 `w_min` 時 `S(params.coupling)` 為 `NE`；刪除 `non_evolvable_globs` 時 `S(params.globs)` 為 `NE`
  And 刪除 `migration_base_sha` 時 `S(history.migration)` 為 `PASS` 且該項 `detail` 為 `claim=none`（缺鍵視為沒有宣稱）；其餘每個子情境的 21 個判定項狀態，除上述被點名的 NE 與 `params.keys` 外，與基線相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_1_E_1]"
```

```gherkin
# AT-031-1-E-2
# 對應 AC: AC-031-1 non_evolvable_globs 與 PRD 及根 CLAUDE.md 不一致判紅
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_1_E_2 -q

Feature: 不可進化面的散文與 JSON 一致

Scenario: 缺少、多出、重複、來源變動各判紅；順序不拘；來源讀不到判未判
  Given 基線有效 repo（§5.3：迷你 PRD 的 `**實體 glob**` 行含標籤式、頓號式、分號式三種前接的片段，並含緊鄰前文不符的誘餌片段；迷你根 `CLAUDE.md` 的 `守衛面＝` 行含一個大括號展開片段與一個普通片段；必備集合因此為 9 項）；每個情境各自複製一份基線、只做一處變異
  When 情境一：自 `non_evolvable_globs` 移除一項；情境二：新增一項不在必備集合內的 glob；情境三：把某一項重複寫兩次；情境四：把清單順序顛倒
  And 情境五：把迷你根 `CLAUDE.md` 的大括號展開少寫一個名字（必備集合少一項，`params.json` 變成多出一項）；情境六：把迷你 PRD 的某個頓號式片段改寫成另一個 glob（必備集合換了一項）
  And 情境七：刪掉迷你 PRD 中含 `**實體 glob**` 的那一行；情境八：刪掉迷你根 `CLAUDE.md`
  Then 情境一、二、三、五、六：`S(params.globs)` 為 `FAIL`，`F(params.globs)` 恰為 `(non_evolvable_globs, GLOBS-SET-MISMATCH)`，detail 列出缺少與多出的項
  And 情境四：`S(params.globs)` 為 `PASS`（順序不拘）
  And 情境七與八：`S(params.globs)` 為 `NE`、`blocking` 為 true，finding 碼為 `SOURCE-UNAVAILABLE`
  And 誘餌片段（緊鄰前文為 `根` 加空白的 `CLAUDE.md`、為 `所列` 加空白的 `tools/lib/`、為 `且` 加空白的 `maturity: active`、為全形左括號的指令）與迷你 `CLAUDE.md` 中不是大括號展開的普通片段都不進必備集合：基線 `S(params.globs)` 為 `PASS` 即證明
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_1_E_2]"
```

```gherkin
# AT-031-1-E-3
# 對應 AC: AC-031-1 耦合：w_opp 不小於 w_min、warn 小於 fail
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_1_E_3 -q

Feature: 參數耦合

Scenario: w_opp 小於 w_min、warn 不小於 fail 判紅；等號放行；耦合鍵無效判未判
  Given 基線有效 repo；每個情境各自複製一份基線、只改 `params.json`
  When 情境一：`w_opp` 為 4、`w_min` 為 5；情境二：兩者皆為 5；情境三：`w_opp` 為 6、`w_min` 為 5
  And 情境四：`ledger_warn_bytes` 與 `ledger_fail_bytes` 都為 262144；情境五：`ledger_warn_bytes` 大於 `ledger_fail_bytes`；情境六：warn 為 100、fail 為 101
  And 情境七：`w_opp` 改成字串 `5`
  Then 情境一：`S(params.coupling)` 為 `FAIL`，`F(params.coupling)` 恰為 `(w_opp, COUPLING-W-OPP-LT-W-MIN)`
  And 情境二與三：`F(params.coupling)` 不含 `COUPLING-W-OPP-LT-W-MIN`（相等與大於放行）
  And 情境四與五：`F(params.coupling)` 恰為 `(ledger_warn_bytes, COUPLING-WARN-GE-FAIL)`；情境六：`F(params.coupling)` 不含 `COUPLING-WARN-GE-FAIL`
  And 情境七：`S(params.keys)` 為 `FAIL`（`w_opp` 型別錯），`S(params.coupling)` 為 `NE`、`blocking` 為 true、碼為 `SOURCE-UNAVAILABLE`
  And 基線 `S(params.coupling)` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_1_E_3]"
```

```gherkin
# AT-031-1-E-4
# 對應 AC: AC-031-1 型別錯誤判紅；多出的鍵不判紅
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_1_E_4 -q

Feature: params.json 的型別

Scenario: 型別錯誤各被標出；多出的鍵不判紅
  Given 基線有效 repo；每個情境各自複製一份基線、只改 `params.json`（情境一在同一份內同時改指名的六個鍵）
  When 情境一：`w_evt` 改成字串 `2`、`w_n` 改成 `20.5`、`w_min` 改成布林 `true`、`migration_base_sha` 改成整數 `123`、`non_evolvable_globs` 改成字串、`spec_body_globs` 改成含一個整數元素的陣列
  And 情境二：新增未登記的鍵 `foo`（值為任意字串）
  Then 情境一：`S(params.keys)` 為 `FAIL`，`F(params.keys)` 恰為六筆 `PARAM-TYPE`，subject 集合為 `w_evt`、`w_n`、`w_min`、`migration_base_sha`、`non_evolvable_globs`、`spec_body_globs`（集合比對，不論順序）
  And 情境二：`S(params.keys)` 為 `PASS` 且 `findings` 為空（多出的鍵不判紅，R21）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_1_E_4]"
```

```gherkin
# AT-031-1-E-5
# 對應 AC: AC-031-1 範圍錯誤判紅；邊界值放行
# 測試類型: Unit
# 自動化工具: unittest／pytest + tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_1_E_5 -q

Feature: params.json 的範圍

Scenario: 範圍錯誤各被標出；邊界值放行
  Given 基線有效 repo；每個情境各自複製一份基線、只改 `params.json`（各情境在同一份內同時改指名的多個鍵）
  When 情境一：`max_touch_ratio` 改成 `2`、`cap_frac` 改成 `0`、`row_max_bytes` 改成 `0`、`metrics_rev` 改成 `0`、`spec_body_globs` 改成空陣列、`non_evolvable_globs` 改成空陣列
  And 情境二（邊界對照）：`max_touch_ratio` 改成 `1`、`cap_frac` 改成 `0.01`、`row_max_bytes` 改成 `1`、`metrics_rev` 改成 `1`
  Then 情境一：`S(params.keys)` 為 `FAIL`，`F(params.keys)` 恰為六筆 `PARAM-RANGE`，subject 集合為 `max_touch_ratio`、`cap_frac`、`row_max_bytes`、`metrics_rev`、`spec_body_globs`、`non_evolvable_globs`（集合比對，不論順序）
  And 情境二：`S(params.keys)` 為 `PASS`（比例鍵上界 1 含、下界須大於 0；整數鍵下限 1 含）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_1_E_5]"
```

```gherkin
# AT-031-2-1
# 對應 AC: AC-031-2 metrics.md 的 M1～M5 與判定細則逐字存在
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_031_2_1 -q

Feature: 指標定義的協定副本

Scenario: metrics.md 逐字含 PRD 的五個指標列與 M1 判定細則
  Given 真 PRD 與真 `docs/06_quality/SelfImproving_Protocol/metrics.md`（P0 交付物 D3）；兩者的 CRLF 先換成 LF
  When 依 R24 以正規式自 PRD 取出五個指標列（M1～M5 各恰一列），以及自 `**M1 判定細則**` 標題行起、至下一個以 `#### ` 起頭的標題行之前的全部非空行
  Then 取得的指標列恰為五列，順序為 M1 至 M5；每一列都逐字出現在 `metrics.md`，且在 `metrics.md` 內的先後順序為 M1 至 M5
  And 判定細則區段的每個非空行都逐字出現在 `metrics.md`
  And 判準自證：對 `metrics.md` 的副本改掉 M3 那一列的一個字元，判準函式判不合格；把 M2 與 M4 兩列對調，判準函式判不合格；刪掉判定細則中任一行，判準函式判不合格
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_031_2_1]"
```

```gherkin
# AT-032-1-1
# 對應 AC: AC-032-1 SOP 骨架：五角色節、擷取者節完整、外部衍生條文
# 測試類型: Unit
# 自動化工具: unittest／pytest + 真 repo 的唯讀檔案
# 判定指令: python -m pytest tools/tests/test_selfimproving_check.py -k AT_032_1_1 -q

Feature: Operations SOP 骨架

Scenario: SOP 有五個角色節，擷取者節含全部必備片段
  Given 真 `docs/05_development/SelfImproving_Operations_SOP.md`（P0 交付物 D5；CRLF 先換成 LF，以 `## ` 標題切段）
  When 以 R25 (1) 與 R25 (6) 的判準檢查；並對真 SOP 逐一刪去擷取者節的每個必備片段（`HEAD=<sha>`、`文字交卷`、`流程摩擦`、`python tools/session_resume_planner.py --pace`、`Omitted`、`OBS-SI-033`、`OBS-SI-038`、`python tools/selfimproving.py check`、`來源`、`回報者`）以及含 `外部衍生=是` 與 `不得單獨` 的那一行，造出副本，各送進判準；另造一份缺少某個角色標題的副本
  Then 真 SOP 判準合格：有 `## ` 級標題分別含 `擷取者`、`歸因者`、`提案者`、`審查者`、`凍結者`；擷取者節含上列全部片段；擷取者節含同時有 `外部衍生=是` 與 `不得單獨` 的一行
  And 其餘四個角色節存在（P0 可只有標題與一行 `P1 定稿`）
  And 自證：每個刪去副本與缺角色標題的副本都判不合格（判準函式不是恆真）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_032_1_1]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-001-1-E-1 | AC-001-1 | 時間與 tz | tools/tests/test_selfimproving_check.py::test_AT_001_1_E_1_* | 缺宣告、毀損、格式與日期不合各被標出；列內 offset 與區間通過 |
| AT-001-1-E-2 | AC-001-1 | 必填欄與座標 | test_AT_001_1_E_2_* | 七欄為空與佔位值 `FIELD-EMPTY`；座標不可定位（含第一段含字母的真實形裸 sid）`COORD-NONE`；九種形態通過；`sid` 的 `line=N`、`seq: N` 寫法通過 |
| AT-001-1-E-3 | AC-001-1 | 枚舉 | test_AT_001_1_E_3_* | 分類、嚴重度、處置各碼；八種合法處置通過 |
| AT-001-1-E-4 | AC-001-1 | 結構 | test_AT_001_1_E_4_* | 欄數、表頭、ID 格式、重複、遞增；格式不合的列不參與重複與遞增追蹤；跳脫管線不切欄；BOM 與表頭在第 1 行 |
| AT-001-1-E-5 | AC-001-1 | 位元組、控制字元、CRLF、體積 | test_AT_001_1_E_5_* | 700 邊界、CJK 以位元組計、五種控制字元、CRLF 不誤判、warn 與 fail |
| AT-001-2-1 | AC-001-2 | 守衛面暴露規則 | test_AT_001_2_1_* | `GUARD-*` 與 `MARK-*` 各碼；非守衛面不受約束 |
| AT-002-1-1 | AC-002-1 | 標記欄語法與詞彙 | test_AT_002_1_1_* | 語法、未知鍵、值域、`orig` 形態各碼；外部衍生只接受「是」 |
| AT-002-2-1 | AC-002-2 | 來源與回報者 | test_AT_002_2_1_* | `SOURCE-*`、`REPORTER-MISSING`；五個合法來源通過 |
| AT-003-1-1 | AC-003-1 | 無常駐機制與啟動條件條文 | test_AT_003_1_1_* | 禁用字樣零命中、`status` 與 `prop-new` rc 3、未註冊 hook、SOP 條文合格且自證 |
| AT-003-2-1 | AC-003-2 | 低於下限判 NE | test_AT_003_2_1_* | `LEDGER-BELOW-FLOOR`、rc 2；等於下限通過；SOP 無事件條文 |
| AT-003-3-1 | AC-003-3 | 產出數量條文與旗標清單 | test_AT_003_3_1_* | SOP 條文合格；`check --help` 的旗標集合恰為四個功能旗標加 `--help` |
| AT-004-2-1 | AC-004-2 | 真缺陷升 DEF 條文 | test_AT_004_2_1_* | SOP 條文合格且自證 |
| AT-029-1-1 | AC-029-1 | 流程摩擦入口條文 | test_AT_029_1_1_* | 擷取者節條文合格且自證 |
| AT-029-2-1 | AC-029-2 | loop-self 條文與受保護面 | test_AT_029_2_1_* | SOP 條文合格；四個迴圈自身 glob 在 `non_evolvable_globs` 內 |
| AT-030-1-E-1 | AC-030-1 | rc 3 與求助 | test_AT_030_1_E_1_* | 十一種輸入錯誤 rc 3、stdout 空；`--help` rc 0 |
| AT-030-3-1 | AC-030-3 | 判準指紋 | test_AT_030_3_1_* | 可重放、CRLF 等價、只隨協定目錄與兩個 rev 變 |
| AT-030-3-2 | AC-030-3 | OBS 草稿列 | test_AT_030_3_2_* | 可貼入、自身零 finding、位元組上限、綠時無草稿 |
| AT-031-1-1 | AC-031-1 | 真 `params.json` | test_AT_031_1_1_* | 格式、含 23 鍵、型別範圍、三個 params 項皆 PASS |
| AT-031-1-E-1 | AC-031-1 | 缺鍵（逐鍵） | test_AT_031_1_E_1_* | `PARAM-MISSING`；取不到參數的項目 NE |
| AT-031-1-E-2 | AC-031-1 | glob 一致性 | test_AT_031_1_E_2_* | 缺少、多出、重複、來源變動判紅；順序不拘；來源讀不到 NE |
| AT-031-1-E-3 | AC-031-1 | 參數耦合 | test_AT_031_1_E_3_* | 兩個 `COUPLING-*` 碼；相等放行；耦合鍵無效 NE |
| AT-031-1-E-4 | AC-031-1 | 型別錯誤；多鍵 | test_AT_031_1_E_4_* | 六筆 `PARAM-TYPE`；多出的鍵不判紅 |
| AT-031-1-E-5 | AC-031-1 | 範圍錯誤 | test_AT_031_1_E_5_* | 六筆 `PARAM-RANGE`；邊界值放行 |
| AT-031-2-1 | AC-031-2 | `metrics.md` 逐字 | test_AT_031_2_1_* | 五個指標列與判定細則逐字存在；判準自證 |
| AT-032-1-1 | AC-032-1 | SOP 骨架 | test_AT_032_1_1_* | 五角色節、擷取者節必備片段、外部衍生條文；判準自證 |

### 3.2 Integration Tests

| AT ID | 對應 AC | 描述 | 介面（git 子行程或 CLI） | 預期結果 |
|-------|---------|------|--------------------------|---------|
| AT-001-1-1 | AC-001-1 | 基線有效 repo 全綠 | 真 git 的合成 repo；in-process `main` | rc 0；21 項齊全；唯一 NE 為 nonblocking 的載體項 |
| AT-001-1-E-6 | AC-001-1 | `fixed@` 解析 | `git rev-parse --verify <sha>^{commit}`；無 git 目錄 | `FIXED-SHA-UNRESOLVED`、`DISP-ENUM`；無 git 時四項 NE、rc 2 |
| AT-001-3-1 | AC-001-3 | 遷移鏈已豁免 | `git log`、`git show`、`git merge-base` | rc 0；`claim=valid`；遷移改動不計 |
| AT-001-3-E-1 | AC-001-3 | 缺 sha 即未豁免 | 同上 | 四個舊列 `ROW-MUTATED`；rc 1 |
| AT-001-3-E-2 | AC-001-3 | 確認列缺漏或不合格 | 同上 | `MIG-CONFIRM-MISSING`；對照組通過 |
| AT-001-3-E-3 | AC-001-3 | sha 無效 | 同上 | 三種 `MIG-SHA-*`；不豁免 |
| AT-001-3-E-4 | AC-001-3 | `orig` 使用規則 | 同上 | `ORIG-NOTES-*`、`ORIG-OUTSIDE-MIGRATION`、`MARK-ORIG-FORMAT` |
| AT-004-1-1 | AC-004-1 | 存在的引用 | `git grep --untracked` | 三個 ref 項 PASS 且 findings 空 |
| AT-004-1-E-1 | AC-004-1 | 懸空的 OBS 引用 | 同上 | `OBS-REF-DANGLING`，同編號多處只報一筆；七處提及截斷為 5 處加 `…+2` |
| AT-004-1-E-2 | AC-004-1 | 懸空的 DEF 引用 | 檔案系統（缺陷帳本家族） | `DEF-REF-DANGLING`；家族全缺 NE |
| AT-004-1-E-3 | AC-004-1 | 載體未建立的家族 | `git grep --untracked` | NE nonblocking；不影響 rc |
| AT-004-3-1 | AC-004-3 | 合法的帳本演進 | `git log`、`git show` | `history.row_mutated` PASS；rc 0；SOP「M 之後只追加」條文合格且自證 |
| AT-004-3-E-1 | AC-004-3 | 遷移之後的原地改寫 | 同上 | 五個列各一筆 `ROW-MUTATED`，cause 與 commit 正確 |
| AT-004-3-E-2 | AC-004-3 | 工作樹改寫與劃界 | 同上 | `commit=WORKTREE`；淨差異 open 轉終值者放行 |
| AT-004-3-E-3 | AC-004-3 | 無歷史可比與帳本在 repo 外 | 未追蹤的帳本檔；repo 外的絕對路徑 | `no-history` PASS；`SOURCE-UNAVAILABLE` NE、rc 2 |
| AT-030-1-1 | AC-030-1 | 輸出契約與子行程 | `subprocess` 執行 CLI（`PYTHONIOENCODING=cp950`；cwd 放誘餌檔） | 文字與 JSON 一致；UTF-8 位元組；rc 1 附草稿列；相對路徑相對於 `--repo`；JSON 鍵序 |
| AT-030-2-1 | AC-030-2 | 純度與零副作用 | `subprocess.run` 與 `Popen` 記錄替身；`GIT_DIR` 污染 | 零副作用；git 呼叫帶 `-C`、`timeout`、`encoding`；環境淨化；純標準庫 |

### 3.3 Contract Tests

（無；`check` 是命令列工具，輸出契約由 §2 的 AC-030-1 與 AC-030-3 的 AT 以 in-process 與子行程兩種路徑鎖住。）

### 3.4 E2E Tests

（無；真帳本的遷移與 `check` 綠屬 SCG-4 實跑檢核 V1～V5，不入 AT，因為 AT 不碰真帳本。）

---

## 4. 邊界與錯誤測試規格

邊界與錯誤情境以 `AT-<NNN>-<Y>-E-<n>` 命名並已列入 §1；下表是依場景類型的索引。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|----------|
| 缺 tz | AT-001-1-E-1 | 無檔頭宣告、宣告毀損、宣告重複 | 刪或改宣告行 | `TIME-NO-TZ`、`TZ-HEADER-MALFORMED` |
| 非法枚舉 | AT-001-1-E-3 | 分類、嚴重度、處置首詞 | `Process`、`P0`、`TODO`、`Open` 等 | `ENUM-*`、`DISP-ENUM` |
| 空值處理 | AT-001-1-E-2 | 七個必填欄各自為空；佔位值 | 空白、`-`、`TBD`、`n/a` | `FIELD-EMPTY` |
| 邊界值（列位元組） | AT-001-1-E-5 | 恰 700 與恰 701 位元組；CJK 300 字 | 補長的症狀 | 700 通過、701 與 CJK 超線 |
| 控制字元 | AT-001-1-E-5 | TAB、NUL、ESC、DEL、行中 CR | 插入字元 | `CTRL-CHAR` |
| 邊界值（體積） | AT-001-1-E-5 | warn 與 fail 恰等於檔案大小 | 調 params | `VOLUME-WARN`、`VOLUME-FAIL` |
| 邊界值（下限） | AT-003-2-1 | 列數為下限減一與等於下限 | 9 列與 10 列 | 前者 NE、後者 PASS |
| `fixed@` 壞 sha | AT-001-1-E-6 | 不存在、非 commit、大寫、過短 | 見 AT | `FIXED-SHA-UNRESOLVED`、`DISP-ENUM` |
| 引用不存在的 OBS | AT-004-1-E-1 | 五種位置加多處同編號 | 執行期組出的編號 | `OBS-REF-DANGLING` |
| 引用不存在的 DEF | AT-004-1-E-2 | 不存在的 DEF；家族全缺 | 執行期組出的編號 | `DEF-REF-DANGLING`；NE |
| `migration_base_sha` 非祖先 | AT-001-3-E-3 | 另一條無父 commit 的 sha | `git commit-tree` | `MIG-SHA-NOT-ANCESTOR` |
| `migration_base_sha` 其他無效 | AT-001-3-E-3 | 格式、查無、非 commit | 見 AT | `MIG-SHA-FORMAT`、`MIG-SHA-UNRESOLVED` |
| params 缺鍵 | AT-031-1-E-1 | 23 個鍵各刪一次 | 刪鍵 | `PARAM-MISSING` |
| `non_evolvable_globs` 與 PRD 不一致 | AT-031-1-E-2 | 缺少、多出、重複、來源變動 | 見 AT | `GLOBS-SET-MISMATCH` |
| `w_opp` 小於 `w_min` | AT-031-1-E-3 | 4 對 5；相等放行 | 調 params | `COUPLING-W-OPP-LT-W-MIN` |
| 遷移後原地改寫 | AT-004-3-E-1 | 改格、二次改處置、刪列、改號、混改 | 五個 commit | `ROW-MUTATED` |
| `open` 轉終值一次放行 | AT-004-3-1 | 單格改處置；追加新列與更正列 | 三個 commit | 放行 |
| 工作樹未提交改寫 | AT-004-3-E-2 | 改格、open 轉終值、兩步改、刪列 | 只改工作樹 | 依淨差異判 |
| 用法錯誤與讀不到輸入 | AT-030-1-E-1 | 十一種輸入 | 見 AT | rc 3、stdout 空 |
| 非 git 目錄 | AT-001-1-E-6 | 無 `.git` 的複本 | 複製檔案 | 四項 NE、rc 2 |
| CRLF | AT-001-1-E-5、AT-004-3-1 | 整檔 CRLF | 換行轉換 | 狀態與 LF 相同 |
| 非 UTF-8 輸入 | AT-030-1-E-1 | 帳本含 0xff 0xfe | 位元組 | rc 3 |
| 非 UTF-8 輸出管線 | AT-030-1-1 | `PYTHONIOENCODING=cp950` 的子行程 | 環境變數 | stdout 仍為 UTF-8 |
| 載體未建立 | AT-004-1-E-3 | 六個家族的提及 | 執行期組出的編號 | NE nonblocking |
| 環境污染 | AT-030-2-1 | `GIT_DIR`、`GIT_INDEX_FILE` 指向別處 | 環境變數 | 結果不變 |
| BOM 與表頭在第 1 行 | AT-001-1-E-4 | UTF-8 BOM 開頭、表頭列為第 1 行、tz 宣告在表後 | 位元組 | 結構與 tz 判準通過 |
| 格式不合的 ID | AT-001-1-E-4 | 兩位數字、第三位為字母、空 ID 欄 | 改 ID | 只報 `ROW-ID-FORMAT`，不參與重複與遞增追蹤 |
| 裸 sid | AT-001-1-E-2 | 只有 UUID（真實形，第一段含 a～f）、不帶 `line` 或 `seq` | 改座標 | `COORD-NONE`（不得被 `sha` 形態放行；二審 N-01） |
| sid 的 `=`、`:` 寫法 | AT-001-1-E-2 | `sid <UUID> line=12`、`sid <UUID> seq: 3` | 改座標 | `row.coordinates` 為 PASS（與 R19 (d) 的 `line` 語法一致） |
| 相對路徑語意 | AT-030-1-1 | cwd 放誘餌檔；`--ledger`、`--params` 給 repo 相對路徑 | 子行程 | 以 `--repo` 為準（rc 0） |
| JSON 鍵序 | AT-030-1-1 | 頂層與三層巢狀的鍵序 | `object_pairs_hook=list` | 依 R4 |
| git 呼叫形態 | AT-030-2-1 | `-C`、`timeout`、`encoding`、`errors`、不繞過 `run` | `subprocess.run` 記錄替身 | 符合 R8 (c) |
| 提及位置截斷 | AT-004-1-E-1 | 同一不存在編號七處提及 | 七處 | 列 5 處加 `…+2` |
| 無歷史可比 | AT-004-3-E-3 | 帳本從未被提交 | 工作樹檔 | `no-history`、PASS |
| 帳本在 repo 外 | AT-004-3-E-3 | `--ledger` 為 repo 外的絕對路徑 | 絕對路徑 | `SOURCE-UNAVAILABLE`、rc 2 |
| 多出的鍵 | AT-031-1-E-4 | 未登記的鍵 | 加鍵 | 不判紅 |
| 型別錯誤 | AT-031-1-E-4 | 字串、浮點、布林、整數、陣列元素 | 改值 | `PARAM-TYPE` |
| 範圍錯誤 | AT-031-1-E-5 | 比例鍵 2 與 0、下限鍵 0、空陣列 | 改值 | `PARAM-RANGE` |
| 並發衝突 | 不適用 | `check` 唯讀、無共享可變狀態；帳本寫入鎖屬 P1（PRD ADR-SI-10） | — | — |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| 事件帳本重放、`dec` 引言回查、`prop` 事件對表 | 屬 P1、P2（PRD §9.3 `check` 列） | 事件帳本檔出現在 repo 而 `check` 仍只印 NE；或發現偽造的 `dec` |
| `status`、`prop-new` 等動詞 | 屬 P1；P0 只有 `check`（AC-003-1 的靜態掃描鎖住） | 掌舵者要求 P0 就偵測啟動事件 |
| 確認列引言的逐字驗證 | P0 只記錄（PRD AC-SI-01-3）；引言回查屬 P2 的 AC-SI-12-4 | 確認列引言被發現與逐字稿不符（SA 已於本輪現查到 PRD 附錄 C.2 的座標與逐字稿不符，見實跑檢核 V5） |
| 以 `check` 機械驗證 `orig` 保全（遷移 commit 與其親 commit 逐列比對） | PRD §9.3 的 `check` 項目清單不含它；一次性遷移，由 SCG-4 的 V3 以唯讀稽核腳本代位 | 第二次遷移被提出，或 `orig` 保全爭議發生 |
| 證據座標指向的檔案或行是否真的存在 | P0 只驗形態（R16），存在性驗證會讓 `check` 依賴工作樹其他檔 | 掌舵者回報座標點不到 |
| 附註檔內容不可變的歷史比對 | PRD 的 `check` 項目清單未列；附註檔放在 `docs/05_development/` 已被 NFR-SI-02-1 (iv) 的既有 glob 涵蓋（不可成為提案目標），但 P0 的 `check` 不比對其內容不變（開放問題 Q2） | 附註檔原文被改動 |
| 外部衍生列不得單獨充當提案證據的語意判定 | 屬 P1 `prop-new` 前置檢查（PRD AC-SI-02-1） | 出現以外部衍生列為唯一來源的提案 |
| 「是否符合缺陷帳本收錄定義」的語意判定 | 判斷題，P0 以 DEF 引用檢查與 SOP 條文代位（AC-SI-04-2） | 真缺陷被登成非 DEF 處置而被掌舵者發現 |
| 在 CI 或 hook 接 `check` | P0 隨需執行；不新增 hook、排程或 CI 步驟（AC-SI-03-1） | 帳本在無人 `check` 時被改壞並進入主幹 |
| 遷移腳本入庫 | 一次性、放 scratchpad | 需要第二次遷移 |
| `--fix`、`--write` 旗標 | `check` 唯讀；CLI 不自寫帳本（PRD §9.4） | 掌舵者要求自動補欄 |

**需同步的既有測試**：無（只新增檔案，不改任何既有檔；根層護欄的重釘由主控收尾，見 NFR-P0-8）。

---

## 5. 測試資料規格

### 5.1 基線有效 repo（`make_valid_repo`）

測試輔助函式（寫在測試檔內）；回傳 tmp 目錄內一個 git repo 的路徑。參數：`rows`（列數，預設 10）、`mutate`（可選回呼，在第一個 commit 之前改帳本文字或 `params.json`，用於「烘入第一個 commit」的建法）。檔案全為 UTF-8、LF；git 以 §5.5 的 hermetic 環境建立；兩個 commit：**C1**＝全部檔案（列 002 的處置為 `open`）、**C2**＝把列 002 的處置改成 `fixed@` 接 C1 的前 12 位（符合 open 轉終值一次）；HEAD 為 C2、工作樹乾淨。`rows` 小於 10 時只建前 `rows` 列（0 列時只有表頭）；列 002 不存在時 C2 改為只改 `metrics.md` 的內容（仍是兩個 commit）。

| 路徑 | 內容 |
|------|------|
| `docs/06_quality/SelfImproving_Observation_Ledger.md` | 兩行前言；一行 `<!-- si-ledger: tz=+08:00 -->`；九欄表頭與分隔列；列 001～010（下表） |
| `docs/06_quality/SelfImproving_Protocol/params.json` | R21 的 23 個鍵，值取初值；例外：`migration_base_sha` 為 null、`min_obs_rows` 為 10、`non_evolvable_globs` 為 §5.3 的必備集合（9 項）；鍵依位元組序、LF、結尾換行 |
| `docs/06_quality/SelfImproving_Protocol/metrics.md` | 任意一行文字 |
| `docs/01_requirements/SelfImproving_PRD.md`、`CLAUDE.md` | 迷你版（§5.3） |
| `docs/06_quality/AutoSDD_Defect_Log.md`、`AutoSDD_Defect_Log_archive_01.md`、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md` | 各一個表格，列首格為一個執行期組出的 DEF 編號（四個互異；以字串相加組出，使測試原始碼不含字面編號） |
| `docs/06_quality/SelfImproving_Observation_Ledger_archive_01.md` | 一個表格，列首格為一個執行期組出的 OBS 編號（不與 001～010 衝突） |

基線 10 列（每列的情境與症狀為「基線列 NNN」「基線症狀 NNN（一句可觀測事實）」；時間除註明者外為 `2026-10-19 01:00`，沿用檔頭 tz；每列位元組數遠小於 700）：

| 列 | 分類與嚴重度 | 處置 | 證據座標形態（R16） | 標記 |
|----|--------------|------|---------------------|------|
| 001 | process、P3 | `open` | path：`tools/lib/si_demo.py:12–15` | `面=產品;來源=代理;回報者=SA` |
| 002 | tooling、P3 | `fixed@<C1 前 12 位>`（C1 時為 `open`） | cmd：反引號包住的 `python tools/selfimproving.py check` 加 ` rc=1` | `面=流程;來源=人;回報者=掌舵者` |
| 003 | doc、P2 | `DEF-200-` 接主缺陷帳本內那個執行期編號 | id：同一個 DEF 編號 | `面=文件;來源=工具;回報者=QA` |
| 004 | bug、P3 | `deferred；再開症狀：同一症狀第二次出現` | file：`CLAUDE.md:12` | `面=產品;來源=逐字稿;回報者=主控` |
| 005 | decision、P4 | `retired；依據 docs/06_quality/notes.md:3` | dir：`docs/06_quality/` | `面=流程;來源=帳本;回報者=主控` |
| 006 | decision、P3 | `decided：掌舵者裁決採方案甲` | sid 加 line：`sid 00000000-0000-4000-8000-000000000006 line 7` | `面=流程;來源=人;回報者=掌舵者` |
| 007 | doc、P4 | `merged@OBS-SI-001` | sha：`abcdef0123` | `面=文件;來源=代理;回報者=SD` |
| 008 | process、P3 | `proposed@PROP-SI-` 接一個執行期組出的三位數編號 | docref：`PRD §9.3` | `面=產品;來源=代理;回報者=SA` |
| 009 | tooling、P2 | `open` | sha_kw：`commit 1234567`（七位全數字，只有 `commit` 關鍵字形態接受）；時間列內明示 `2026-10-19 01:00 +09:00` | `面=守衛;暴露=a;來源=代理;回報者=QA` |
| 010 | tooling、P4 | `open` | cmd 與 path 並列；時間為區間 `2026-10-19 01:00～10-19 02:00`（不帶 offset） | `面=守衛;暴露=無;外部衍生=是;來源=工具;回報者=si-check` |

### 5.2 遷移鏈 repo（`make_migration_chain`）

參數 `confirm`（確認列變體：`valid`、`no-decided`、`no-sha`、`no-sid`、`no-line`、`wrong-sha`、`not-decided`）。檔案配置同 §5.1（協定目錄、迷你 PRD 與根 `CLAUDE.md`、缺陷帳本家族皆自 C0 起存在；`min_obs_rows` 為 3；`migration_base_sha` 自 C0 起為 null），帳本與附註檔依下列三個 commit 演進：

- **C0**：舊版八欄帳本（無 tz 宣告），4 列：`OBS-SI-001`（處置 `open`）、`OBS-SI-002`（處置 `裁決：採方案甲，已回報掌舵者`）、`OBS-SI-003`（處置 `延後；再開症狀：同一症狀第二次出現`）、`OBS-SI-004`（處置為一段超過 450 位元組的自由文字，使加第九欄再複製原文會超過 700）；各列證據座標皆合 R16，時間不帶 offset。
- **M**（單一 commit，只動帳本與 `docs/05_development/SelfImproving_Observation_Ledger_notes.md`）：加檔頭 `<!-- si-ledger: tz=+08:00 -->`、第 9 欄「標記」；列 001 處置維持 `open`（標記不含 `orig`）；列 002、003 的處置改成 `decided：…`、`deferred；再開症狀：…`，標記帶內嵌 `orig="<C0 的處置原文>"`；列 004 的處置改成短的 `decided：…`，標記帶 `orig=@docs/05_development/SelfImproving_Observation_Ledger_notes.md#OBS-SI-004`，附註檔含標題 `## OBS-SI-004` 與其下 C0 處置原文逐字；各列另補 `面`、`來源`、`回報者`。
- **N**：`params.json` 的 `migration_base_sha` 寫入 M 的完整 40 位 sha；帳本追加 `OBS-SI-005`＝確認列：時間 `2026-10-19 12:00 +08:00`、症狀為掌舵者原句的引述、證據座標含 `commit <M 的前 12 位>`、`sid 00000000-0000-4000-8000-000000000001`、`line 2581`，處置 `decided：掌舵者預先授權`，標記 `面=流程;來源=人;回報者=主控`。`confirm` 各變體依名稱改這一列：`no-decided` 不追加此列；`no-sha` 去掉 sha；`no-sid` 去掉 `sid` 與 UUID；`no-line` 去掉 `line` 與整數；`wrong-sha` 改引 C0 的 sha；`not-decided` 把處置改成 `deferred；…`。

### 5.3 迷你 PRD 與迷你根 `CLAUDE.md`（`params.globs` 的合成來源）

迷你 PRD 含恰一個含字面 `**實體 glob**` 的行，內容如下（逐字）：

```text
- **實體 glob**：(i) `**/CLAUDE.md`；`A/*/b.yaml` 中**既有且 `maturity: active`** 者（新增的 `trust_level: proposed` 不在此列）；(ii) `**/.claude/**`、根 `CLAUDE.md`〈守衛面准入〉所列 `tools/lib/` 檔、`tools/x.py`；(iii) `docs/q/**`、`docs/r.md`（以 `python tools/y.py` 現查）。
```

進必備集合的 6 項：`**/CLAUDE.md`（標籤式）、`A/*/b.yaml`（分號式）、`**/.claude/**`（標籤式）、`tools/x.py`（頓號式）、`docs/q/**`（標籤式）、`docs/r.md`（頓號式）。誘餌（緊鄰前文不符，不得進）：`maturity: active`（前接「且 」）、`trust_level: proposed`（前接「的 」）、前接「根 」的 `CLAUDE.md`、前接「所列 」的 `tools/lib/`、前接「（以 」的 `python tools/y.py`。

迷你根 `CLAUDE.md` 含恰一個含字面 `守衛面＝` 的行（其前不得有另一個含該字面的行），內容如下（逐字）：

```text
- 守衛面＝`.claude/hooks/**`、`tools/lib/{aa,bb,cc}.py`、`tools/x.py`。其餘文字
```

只有大括號展開片段進必備集合：`tools/lib/aa.py`、`tools/lib/bb.py`、`tools/lib/cc.py`；`.claude/hooks/**` 與 `tools/x.py` 是普通片段，不展開。必備集合＝PRD 的 6 項加展開的 3 項，共 9 項。

### 5.4 真檔案（唯讀，不得被測試修改）

`docs/06_quality/SelfImproving_Protocol/params.json`、`docs/06_quality/SelfImproving_Protocol/metrics.md`、`docs/05_development/SelfImproving_Operations_SOP.md`、`docs/01_requirements/SelfImproving_PRD.md`、根 `CLAUDE.md`、`.claude/settings.json`、`tools/selfimproving.py`、`tools/lib/selfimproving/*.py`。測試以 `Path(__file__).resolve().parents[2]` 為 repo 根。**測試不讀真帳本與真附註檔**。

### 5.5 hermetic 環境

每個會呼叫 git 的測試（含被測的 `main` 與測試自己建 repo 的 git 指令）在 `mock.patch.dict(os.environ, …)` 之下執行：先移除 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE`、`GIT_COMMON_DIR`、`GIT_PREFIX`、`GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES`（測試可能在 git hook 內執行，這些變數會把 tmp 內的 git 指令導向真 repo）；再設 `GIT_CONFIG_GLOBAL` 指向 tmp 內一個空檔案（不用 `os.devnull`，Windows 上行為不一）、`GIT_CONFIG_NOSYSTEM=1`、`GIT_AUTHOR_NAME`、`GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_NAME`、`GIT_COMMITTER_EMAIL`、`GIT_TERMINAL_PROMPT=0`；測試建立的 repo 以 `-c commit.gpgsign=false -c core.autocrlf=false` 提交；寫檔一律 `encoding="utf-8"`、`newline="\n"`（CRLF 情境明確以位元組寫入）。git 缺席視為環境壞、測試直接失敗（不得 skip）。

### 5.6 允許變更的檔案集合（T 提交）

新增：`tools/selfimproving.py`、`tools/lib/selfimproving/*.py`（套件，模組數自定；2026-10-19 自 `tools/lib/si_*.py` 搬入）、`tools/tests/test_selfimproving_check.py`、`docs/06_quality/SelfImproving_Protocol/params.json`、`docs/06_quality/SelfImproving_Protocol/metrics.md`、`docs/05_development/SelfImproving_Operations_SOP.md`。M 與 N 另動：`docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/05_development/SelfImproving_Observation_Ledger_notes.md`（M 新增）、`docs/06_quality/SelfImproving_Protocol/params.json`（N 改一個鍵）。主控收尾另動根層鎖檔（NFR-P0-8）。其餘一律不動；尤其不動 PRD、研究方法 SOP、`.claude/**`、本 TCS。

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| PRD FR-SI-01～04、29 → F-001 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-001 → US-001～US-005 | ☑ 已映射 |
| US-001～US-005 → 本檔 19 個 AC | ☑ 已映射（FRD-lite） |
| PRD AC-SI-01-1～01-3、02-1～02-2、03-1～03-3、04-1～04-3、29-1～29-2（13 個）→ 本檔 AC-001-1～AC-029-2 | ☑ 已映射（編號規則見 FRD-lite） |
| 本檔 AC（19 個）→ AT（42 個） | ☑ 已映射（本檔 §1，覆蓋率 100%） |
| PRD §8.1 P0 退出條件 (a) 免追問必填欄 → AT-001-1-1、AT-001-1-E-1～E-5、AT-001-2-1、AT-002-2-1 與實跑檢核 V9 | ☑ |
| PRD §8.1 P0 退出條件 (b) 自遷移基準起 `check` 綠 → AT-001-3-1、AT-004-3-1 與實跑檢核 V1、V2、V4 | ☑ |
| PRD §8.1 P0 退出條件 (c) 處置合枚舉且 `orig` 保全 → AT-001-1-E-3、AT-001-3-E-4 與實跑檢核 V3 | ☑ |
| PRD §8.1 P0 退出條件 (d) 零無座標列、零「之後再看」→ AT-001-1-E-2、AT-001-1-E-3 與實跑檢核 V2 | ☑ |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由根層 unittest 閘門一併執行；根層重釘由主控收尾） |

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（Q1～Q6）

| 編號 | 問題 | 本檔已採用的預設 | 替代與再開症狀 |
|------|------|------------------|----------------|
| Q1 | `check` 的 rc 語意：PRD 只說「`check` 綠」，未定義 NE 與工具錯誤的 rc | rc 0、1、2、3（R1、R5）；nonblocking NE 只有 `CARRIER-NOT-ESTABLISHED`（PRD AC-SI-04-1 要求未判不得判通過、也不得判不合規，而真帳本引用 `PROP-SI-` 家族的列使它必然出現） | 替代：任何 NE 都非綠；代價是 P0 退出條件 (b) 因真帳本的 `PROP-SI-` 引用而不可達，須經 T1 修 PRD。再開症狀：QA 或掌舵者把「綠但帶 NE」讀成未達標 |
| Q2 | OBS 附註檔的名稱與保護面：PRD 只說「搬附註檔、列上留座標」 | `docs/05_development/SelfImproving_Observation_Ledger_notes.md`（預審 F-06 的現成解）：被 NFR-SI-02-1 (iv) 既有的實體 glob `docs/05_development/SelfImproving_*.md` 涵蓋，不必改 PRD，也不會成為 P1 `prop-new` 的可進化目標；剩餘缺口：P0 `check` 不比對附註檔內容不變（`orig` 保全只靠 V3 的一次性稽核） | 替代：放 `docs/06_quality/`（不被任何既有 glob 涵蓋，須經 T1 補 PRD）或放協定目錄（受保護，但進判準指紋的 manifest）。再開症狀：附註檔原文被改動而 `check` 沒有紅燈 |
| Q3 | D1 對既有各列補 `來源`、`回報者`、`面`、`暴露` 的回填規則，與三個座標不合格列的補件 | 回報者＝情境欄的角色詞；來源＝`代理`（掌舵者回報者用 `人`、工具輸出用 `工具`、逐字稿引述用 `逐字稿`、帳本衍生用 `帳本`）；面＝依症狀所涉檔案（`.claude/`、hook、根 `CLAUDE.md` 守衛面清單內的 `tools/lib` 與 `tools/session_resume_planner.py` 為 `守衛`；產品程式為 `產品`；文件為 `文件`；其餘為 `流程`）；守衛面列的暴露＝其座標已有 sid 加行、檔加行或指令加 rc 之一者填 a、b、c 之一，否則填 `無`；座標不合 R16 的列（HEAD 7b9c6ba6 的 47 列現查為三列：OBS-SI-019、029、034；`sid` 形態改要求帶 `line` 或 `seq` 後仍是這三列，沒有列只靠裸 sid）只准**追加**座標（不改原字，且列位元組仍不得超線）；處置對映原則：裁決、接受、已執行 ⇒ `decided：…`；延後 ⇒ `deferred；再開症狀：…`；`fixed（…）` ⇒ `fixed@<修復 commit 的 sha>`（查不到 sha 則改 `decided` 並保留 `orig`，不得編造 sha）；待議或候選提案 ⇒ `open`；原文一律逐字留 `orig`；超線估算（SA 以 HEAD 7b9c6ba6 的 47 列現查重估：新處置約 40 位元組取代舊處置、標記約 60 位元組、`orig` 內嵌舊處置；草稿版曾寫「8 列超線」，那次估算把舊處置重複計入一次，已更正，與預審另估一致）：只有 OBS-SI-043（649 位元組，估計加欄後約 757）會超過 700，須把原文搬附註檔，其餘列可內嵌；以 M 提交前現查為準 | 替代：由掌舵者逐列裁決。再開症狀：QA 在 V3 抽查發現回填與症狀語意不符 |
| Q4 | PRD C5 列點名但未取名、未給值的參數 | `min_obs_rows`＝10、`ledger_warn_bytes`＝245760、`ledger_fail_bytes`＝262144（先例 `tools/check_defect_log_crossref.py` 的 240 與 256 KiB）、`metrics_rev`＝1；P1 才用的事件數下限等由 P1 的 TCS 擴充登記表 | 替代：反空轉下限拆成 OBS 與事件兩個鍵。再開症狀：下限擋住了合法的小帳本，或掌舵者要求他名 |
| Q5 | `non_evolvable_globs` 與 NFR-SI-02-1 一致性的機器判準 | R22 的位置式抽取（片段前接頓號、分號或標籤）加根 `CLAUDE.md` 守衛面行的大括號展開；SA 預演為 18 加 7 共 25 項（現算為準） | 替代：PRD 經 T1 加機器可讀區塊；或只比對該行的雜湊（無法指出差異項）。再開症狀：PRD 或根 `CLAUDE.md` 改版使抽取規則假紅或漏判 |
| Q6 | R16 的證據座標「可定位」形態比 PRD:220 寬（預審 F-05；PRD:220 只列檔案:行、指令加 rc、sid 加 seq、帳本列 ID 四形態） | 九形態（R16）。理由：SA 以真帳本實測（HEAD 7b9c6ba6 的 47 列；二審後以 407c945b 的 49 列與 HEAD 96bbd73a 的 50 列重算，結果相同）——九形態下只有 OBS-SI-019、029、034 三列不合；若收斂到四形態（以 `路徑:行號`、反引號指令且同格有 `rc`、sid 加 `line` 或 `seq`、帳本列 ID 粗判），SA 粗判有 24 列不合，D1 又只准追加座標，等於逼 D1 對近半數列補件，風險高於收益。已收斂兩處：(1) `sid` 形態須同格帶 `line=N` 或 `seq=N`（真帳本零列只靠裸 sid，無代價）；(2) `sha` 形態前後邊界排除連字號，UUID 片段不再被當成 sha（二審 N-01；舊新規則對上述 49 列與 50 列的帳本重算，`COORD-NONE` 仍只有 019、029、034，沒有列因此轉紅）。`check` 只驗形態、不驗存在（§4 刻意不做），與一審「座標須可重查」的張力由 V3 (9) 的座標重查抽查承擔（二審 N-02）：只靠單一放寬形態過關的列——`docref` 7、無行號 `file` 3、無行號 `path` 2，共 12 列——在 HEAD 96bbd73a 的 50 列帳本與 407c945b 的 49 列帳本都是同樣這 12 列（SA 以 R16 規則重算，與 QA 二審的 12 列相符；列數隨帳本追加而變，以 V3 現查為準） | 替代：收斂到 PRD 四形態並由 D1 補件。再開症狀：掌舵者或 QA 回報座標點不到，或某筆座標只靠目錄、章節別名過關而無法重查 |

### 7.2 預審登記（TCS-PREREVIEW 的 F-11～F-15 為一審 P4，只登記、不改規格；N-01～N-04 為二審 P3，本棒已修）

| 編號 | 預審所述 | 本檔處置 | 再開症狀 |
|------|----------|----------|----------|
| F-11 | SOP 骨架以大量字面中文片段與真 ID 做存在判準，措辭一改即紅 | 登記；已以「刪去副本須判不合格」自證判準非恆真 | SOP 因措辭微調使 AT 反覆轉紅 |
| F-12 | `deferred`、`decided` 只驗附加文字非空，PRD:230 要求一句可觀測再開症狀、裁決者與一句裁決；新列的復發候選提示（PRD:786、AC-SI-06-2，屬 P1）未列入 §4 | 登記；語意判定屬人審（與 AC-004-2 同型），復發候選提示屬 P1 | 處置文字空洞（只有一個詞）而 `check` 綠，被掌舵者發現 |
| F-13 | 草稿列 ID＝帳本現有最大 ID 加一、不看封存檔，封存若搬走高號列且暫無新列可能撞號（現無封存檔） | 登記；P0 無封存工具 | 出現 OBS 封存檔且草稿撞號 |
| F-14 | hermetic 環境未設 `GIT_CEILING_DIRECTORIES`，tmp 若落在某 repo 之下，非 git 目錄情境會找到祖先 repo | 登記；一般機器與 CI 不成立 | 開發機的 tmp 位於某 repo 之內而 AT 假綠或假紅 |
| F-15 | §3 與 §1 重複維護兩份 AT 清單；TCS 體量大（已登記 OBS-SI-045） | 登記；編譯相容檢查以 §1 為準，§3 為閱讀索引 | AT 增減時兩處不同步 |
| N-01 | R16 的 `sha` 形態把 UUID 第一段當 sha 吃掉，裸 sid 靠 `sha` 形態過關；AT-001-1-E-2 的列 008 只在 UUID 全數字時才判 `COORD-NONE`；R16 的 `sid` 形態與 R19 (d) 的 `line=` 語法不一 | 已修（本棒）：`sha` 前後邊界都排除連字號；`sid` 形態改為 `line`、`seq` 之後可接 `=`、`:`（捨去 R19 (d) 沒有的「行」關鍵字）；AT-001-1-E-2 的列 008 改用第一段含 a～f 的真實形 UUID，另加列 009（`line=12`）、010（`seq: 3`）正向對照；SA 以舊新規則對真帳本重算，`COORD-NONE` 仍只有 019、029、034 | 某種真實形 sid 寫法被誤放行或誤擋；或真帳本出現「舊規則過、新規則不過」的列 |
| N-02 | Q6 把「座標可重查」交給 V3，但 V3 八項沒有抽座標；真帳本有 12 列只靠單一放寬形態過關 | 已修（本棒）：V3 新增 (9)「座標可重查抽查」（≥5 列，優先取只靠 `docref`、無行號 `file`、無行號 `path` 過關者）；Q6 註明該類列數（`docref` 7、無行號 `file` 3、無行號 `path` 2，共 12） | V3 (9) 抽到點不開的座標；或該類列數在 M 之後明顯增加 |
| N-03 | 慣例、R25 (9)、V9 寫「M 之後一律追加、既有列零原地改寫」，比 R20、AT-004-3-1 的 K1、PRD:223、AC-SI-04-3 窄（後者明許處置欄 `open`→終值一次） | 已修（本棒）：三處改為「除處置欄 `open`→終值一次外，一律追加列」；R25 (9) 的必含片段增 `open`、`終值`，AT-004-3-1 的自證同步；V9 註明 `history.row_mutated` 的放行集合與此句等價 | SOP 條文被讀成連 `open`→終值也禁；或 V9 的字面與機械憑證再度不等價 |
| N-04 | V2 括註只提本檔與測試原始碼，而 R18 (a) 掃整個 repo（QA 一審報告內的字面反例 ID 曾使 `ref.obs` 轉紅） | 已修（本棒）：V2 括註改為整個 repo 的非忽略檔（含 `docs/06_quality` 的審查報告），字面反例 ID 一律以文字描述或加零寬標記；N 之前先跑一次 `check`、把 `OBS-REF-DANGLING` 清零 | N 之後 V2 因某份文件內字面不存在的 OBS 編號而轉紅 |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 19 個 AC 無未映射者（§1） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 有判定指令與驗收字樣 | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（E 類，或內含負向變體或刪除自證的 AT；流程型 AC 的負向＝對 SOP 條文逐一刪去的副本須判不合格） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試（列位元組 700、反空轉下限、`w_opp` 等於 `w_min`、體積 warn 與 fail） | □ |
| 測試資料規格完整 | 資料來源明確定義（§5） | □ |
| 實跑檢核 V1～V9 全部有逐字輸出證據 | 見下表；沒貼輸出＝未驗證 | □ |

**實跑檢核（非 AT；QA 於 SCG-4 親跑，輸出逐字貼入證據；AT 不碰真帳本，真帳本的驗收全在這裡）**

| 編號 | 檢核 | 指令與證據 | 判斷標準 |
|------|------|-----------|---------|
| V1 | 提交鏈 | `git log --format="%H %s" -- docs/06_quality/SelfImproving_Observation_Ledger.md`；`git show --name-only --format= <M>`、`git show --name-only --format= <N>` | T 早於 M 早於 N；M 是單一 commit 且只動帳本與附註檔；N 只動 `params.json` 與帳本（追加一列）；M 與 N 是兩個 commit |
| V2 | 真帳本 `check` | `python tools/selfimproving.py check --json`（真 repo，N 之後的 HEAD）；貼 JSON | rc 0；`items` 中除 `ref.carrier_families`（可為 nonblocking NE）外皆 PASS；`row.coordinates`、`row.enums` 為 PASS（零無座標列、零「之後再看」）；`ref.obs` 為 PASS（R18 (a) 掃整個 repo 的非忽略檔——含 `docs/06_quality` 的審查報告、本檔與測試原始碼：字面反例 ID 一律以文字描述、`OBS-SI-NN` 這類不含數字的佔位或加零寬標記，不得寫成可被 R18 (a) 抓到的 ID 字面；N 之前先跑一次 `check`，把 `OBS-REF-DANGLING` 清零） |
| V3 | M 稽核（唯讀；稽核腳本放 scratchpad、不入庫） | 對 `M^` 與 `M` 的帳本逐列比對 | (1) ID 集合與順序不變、無增減列；(2) 時間、情境、症狀、分類、嚴重度逐格相同；(3) 證據座標逐格相同，或僅為「前綴保留的追加」；(4) 處置被改寫的列都有 `orig`，其值（內嵌，或 `@` 附註檔段落）與 `M^` 的處置原文逐字相同，處置未改寫的列沒有 `orig`；(5) 九欄與檔頭 tz 宣告齊備；(6) 每個 `@` 錨點在附註檔有同 ID 的段落；(7) 沒有「之後再看」；(8) 回填語意抽查（開放問題 Q3）合理；(9) 座標可重查抽查（二審 N-02，Q6 的承擔）：取 M 的帳本的「證據座標」欄，優先挑只靠單一放寬形態（`docref`、無行號 `file`、無行號 `path`）過關的列，抽 ≥5 列（不足 5 列則全查），逐一重查該座標確實可定位（檔案與其行存在、`§` 或文件別名所指章節存在）；任一列點不到 ⇒ V3 不通過，退回主控補救 |
| V4 | `migration_base_sha` | `git rev-parse <M>`；讀 `params.json`；`git merge-base --is-ancestor <M> HEAD`（讀 rc 時不接管線） | 值等於 M 的完整 40 位 sha；rc 為 0 |
| V5 | 確認列引言座標 | 對確認列所引的每個 `line`，唯讀讀取逐字稿 `<sid>.jsonl` 該實體行（`type`、`origin.kind`、文字） | 該行是 `type` 為 `user`、`origin.kind` 為 `human`（或 `queued_command` 附件）的記錄，文字與列內引言逐字相符。SA 預演現查（sid `f3ead132-29b1-418c-97d9-35868ab11c70`）：預先核准句「真正需要你本人的只剩凍結核准 ==> 現在先授權核准! (避免不在機器旁)」在 line 2525、授權句「…我授權幫我決策…」在 line 2476、「了解，凍結後接著開 P0 實作」在 line 2581；舊座標 line 2536 與 2493 是 assistant 的空文字記錄（緊接在回覆之後的工具呼叫），曾被任務書、PRD 附錄 C.2 初稿、QA 報告 §7、觀察帳本 OBS-SI-042 引用——PRD 附錄 C.2 已於重凍訂正為 2476／2525／2581，QA 報告 §7 已補註，OBS-SI-042 以更正列 OBS-SI-043 處理（凍結檔不改，帳本只追加）。確認列須用現查的行號；本檢核只驗確認列自己所引的行號 |
| V6 | `params.json` 初值 | 逐鍵對照 §2 R21 表的「初值」欄與其 PRD 座標 | D3 提交當下每個初值與 PRD 一致（`min_obs_rows` 等本檔自定者與開放問題 Q4 一致）；`non_evolvable_globs` 由 R22 規則現算；`params.json` 的鍵恰為 R21 的 23 鍵（`check` 不因多鍵而紅，故由本項核對無多出的鍵） |
| V7 | 護欄與零退化 | 根層全套 unittest（`python -m unittest discover -s tools/tests`，通過數以實跑為準）；`ruff check` 對新增的每個 `.py`；`python AutoClaude/tools/check_loc_budget.py --json`；`tools/tests/test_defect_id_reference_integrity.py`；`git diff --name-only`；`git diff --stat -- .claude` | 全綠；`git diff --name-only` 只含 §5.6 的集合與主控收尾的重釘檔；`.claude/**` 無變動；凍結檔（PRD、研究方法 SOP）無變動；`check` 真 repo 牆鐘小於 30 秒（NFR-P0-2） |
| V8 | SOP 與流程型 AC 的文件檢核 | QA 逐項對照 PRD AC-SI-02-1、03-1～03-3、04-2、29-1、29-2 與 SOP 條文；Developer 與 QA 的文字交卷 | SOP 條文語意與 PRD 一致（不只關鍵字在）；Developer 棒與 QA 棒的交卷都含「流程摩擦」節，節內項目於 SCG-4 前已由主控入帳為 OBS 列，且 V2 仍為綠 |
| V9 | P0 退出條件 (a)，與 M 之後只追加（預審 F-04、二審 N-03） | 檢視 N 之後新增與變動的 OBS 列與它們的來源；`git log -p -- docs/06_quality/SelfImproving_Observation_Ledger.md` 自 N 起至 SCG-4 前 | 沒有任何「某欄無法填」的觀察（反症狀）；新增列皆通過 `check`；**N 之後至 SCG-4 前，既有列除處置欄 `open`→終值一次外零原地改寫**（`history.row_mutated` 為 PASS 即機械憑證，其放行集合恰為追加列、處置欄 `open`→終值一次、不改格內容的格式整理三種（R20、AT-004-3-1），與此句等價；累計次數、狀態更新與更正一律追加列，R25 (9)）；M 之前的原地改寫（例如 OBS-SI-011 的累計次數）依 AC-SI-01-3 屬遷移基準以前、不在此限 |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 搬遷勘誤（2026-10-19，FSM SPEC_AUDIT；掌舵者裁決，非缺陷）

- **事由**：SCG-4 二審 PASS 後，掌舵者問「這個模組不用規劃獨立的目錄?」並選「現在就搬」，再指令「日後新模組須有系統、有組織地規劃整體專案目錄，不得散落，寫進 CLAUDE.md 與專案規格」（sid f3ead132-29b1-418c-97d9-35868ab11c70 line 5507／5524／5565）。
- **改了什麼**：程式碼自 `tools/lib/si_*.py` 搬成套件 `tools/lib/selfimproving/{__init__,ledger,rows,git,refs,history,params,check}.py`（`git mv`，套件內相對 import）；指令入口 `tools/selfimproving.py` 與指令字面 `python tools/selfimproving.py check` **不變**；本檔只改路徑字面（D4、R26、NFR-P0-5、AT-003-1-1 Given、AT-029-2-1 四項 glob、R8 (b) 本地模組規則〔AT-030-2-1 的 AST 子句；原誤寫 R8 (a)，勘誤二訂正〕、§5.6）與 18 處 PRD digest（PRD 同日重凍：`sha256:fbca6bc9…`，改 §9 C4 路徑、加模組落點表、NFR-SI-02-1 (iv) glob）；AT id、AT 數（42）、R1～R26 語意、21 項判定碼**一字未動**。落點規範 SSOT＝`docs/02_architecture/Root_Layout_and_Module_Placement.md`。
- **凍結紀錄**：Stage-2 原凍結 digest `sha256:6c4e28ed…`（2026-10-19T05:43:56Z）保留為歷史；本次修訂走 FSM `PR_REVIEW→（gate PASS）RTM_VERIFY→IMPLEMENTATION→SPEC_AUDIT→PR_REVIEW`，修訂後的本檔 digest 記在 FSM decision_trace（回 PR_REVIEW 的 reason）與 SCG-4 報告 §9 三審。
- **§5.1 測試資料列 001 的合成座標 `tools/lib/si_demo.py:12–15` 不改**：它是虛構的證據座標（只驗形態），不指向真檔。

## 搬遷勘誤二（2026-10-19 晚；OBS-SI-109；文字訂正，非缺陷）

- **事由**：SCG-4 三審 F-18 指出搬遷後本檔仍殘留舊路徑字面；掌舵者同日指令「任何修復 BUG 或架構修改都要以不留後遺症的方式修復」（根 `CLAUDE.md`〈兩專案共通的工程紀律〉第 5 條），故不等下次 TCS 修訂、即時訂正。
- **改了什麼**（只改文字，AT id、AT 數、R1～R26 語意、判定碼一字未動）：INVEST 自檢「可估計」句的「約 3 個 `si_*.py` 模組」改為套件現況（保留立案時估值字樣）；SCG-2 Container 列的落點「`lib/si_*.py`」改為「CLI `selfimproving.py` 與套件 `lib/selfimproving/`」；〈搬遷勘誤〉所寫「R8 (a) 本地模組規則」訂正為 R8 (b)（R8 (a) 是只讀，(b) 才是標準庫與本地模組規則，實際改的是 AT-030-2-1 的 AST 子句）。§1 FRD-lite「Before」段刻意保留搬遷前敘述（勘誤一已載明）。
- **凍結紀錄**：本檔的 Stage-2 凍結 digest 自勘誤一起即與現檔不符（FSM `SPEC_AUDIT` 後無重記 digest 的動詞，OBS-SI-108／SCG-4 三審 F-17）；本次訂正後 digest 再變，待框架補「重記凍結 digest」動詞後由主控重記，不以手改狀態檔代替。


## 搬遷勘誤三（PRD v0.9.1 修訂後的行號重對；文字訂正、非缺陷；AT id／R／判定碼一字未動）

- **事由**：PRD 於 v0.8（commit c2aee850，T1 修訂需求面）在 §5.2 等處插入約 165 行，v0.9（460d3135）與 v0.9.1（66ad0edd、2b994518）再增，本檔內以 `PRD:NNN` 形態寫的 PRD 行號座標全數偏移（原座標寫於 PRD 重凍前後：重凍版 `sha256:fbca6bc9…`＝commit e83ebb14 與 7b9c6ba6 版，兩版對下表 39 個行號指向同一列，個別列文字於兩版間有小幅差異、不影響指向）。掌舵者指令「修法不留後遺症」：一次改完、不只改一半、不留「之後再看」。主控 PRD §9.7 #47 裁決：P0 TCS 勘誤三由 P1 TCS 棒一併記。
- **改了什麼**（只改文字，AT id、AT 數〔42〕、R1～R26 語意、21 項判定碼、各 FRD-lite 表一字未動）：本檔含 `PRD:` 前綴行號座標的行共 34 行（「34」是行數、不是座標數）、56 組座標，一律改為凍結版 PRD（`sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73`，HEAD 2f13bb2b；PRD v0.9.1）的現行行號。**範圍與連串寫法一併處理**：座標寫法是 `PRD:` 接行號；範圍（例：61～65、413～415、413–415）與「第一個數字帶前綴、其後以頓號接的裸行號」（例：61～65、69～78 的後半，或 212、554）皆逐數改；夾在句中的座標（例：「PRD 只在量測腳本列」之後接的那個）亦同。**不屬 PRD 行號、刻意不動（已逐類查證）**：`line 2476／2525／2581／2493／2536／5507`（逐字稿 jsonl 的實體行號，不是 PRD 行）；`§…` 章節座標與 `PRD §…` 節名（以章節號為座標、不受插行影響）；全檔 `file:行號` 形態的座標只有 §5.1 測試資料的三個合成座標（`tools/lib/si_demo.py:12–15`、`CLAUDE.md:12`、`docs/06_quality/notes.md:3`；只驗形態、不指向真檔，勘誤一已載明），無須重對；全檔另無「PRD 第 N 行」「`SelfImproving_PRD.md:N`」之類其他指向 PRD 行號的寫法（Grep 查過）。
- **核對方法**（逐處，不憑記憶）：舊行取 `git show e83ebb14:docs/01_requirements/SelfImproving_PRD.md` 的第 N 行（另以 `git show 7b9c6ba6:…` 交叉，兩版對下表行號指向同一列）；新行取工作樹 PRD（digest 與凍結版相同）的第 M 行；兩行逐字相等者標 EXACT（34 個行號），v0.8～v0.9.1 改寫過、但列首欄位相同（表格列取前兩格）且人工讀兩邊內容確認仍是同一列者標 FUZZY（5 個：212、554、566、567、635）。範圍座標的末端另以首尾兩行各核一次。改後以腳本重列本檔全部 `PRD:` 組，確認舊號零殘留、新號與下表逐組相符。
- **「舊→新」逐數對照**（每個被引用的舊行號一列；範圍與連串座標內的每個數字各自查此表）：

| 舊行號 | 新行號 | 核對 | 所指內容 |
|--------|--------|------|----------|
| 38 | 38 | EXACT | §1.1「可被反證」段（`W_EVT` 初值） |
| 61 | 62 | EXACT | §1.3 指標表 M1 列（含 `W_N`、`W_MIN` 先例） |
| 65 | 66 | EXACT | §1.3 指標表 M5 列 |
| 69 | 70 | EXACT | §1.3「M1 判定細則」標題行 |
| 78 | 79 | EXACT | M1 判定細則區段末（其後空行；下一行為 `#### 1.3.1`） |
| 208 | 220 | EXACT | §5.1.1 欄位表「證據座標」列 |
| 211 | 223 | EXACT | §5.1.1 欄位表「處置」列 |
| 212 | 224 | FUZZY | §5.1.1 欄位表「標記」列 |
| 218 | 230 | EXACT | §5.1.1「處置枚舉」段 |
| 234 | 246 | EXACT | §5.1.2「狀態機（唯一合法轉移）」段 |
| 245 | 257 | EXACT | AC-SI-01-3 |
| 286 | 298 | EXACT | AC-SI-09-2 |
| 290 | 302 | EXACT | AC-SI-10-1 |
| 309 | 321 | EXACT | AC-SI-13-3 |
| 314 | 326 | EXACT | AC-SI-14-3 |
| 345 | 357 | EXACT | AC-SI-20-2 |
| 356 | 368 | EXACT | AC-SI-22-1 |
| 361 | 373 | EXACT | AC-SI-23-1 |
| 365 | 377 | EXACT | AC-SI-24-1 |
| 375 | 387 | EXACT | AC-SI-26-1 |
| 379 | 391 | EXACT | AC-SI-27-1 |
| 403 | 481 | EXACT | NFR-SI-01 表「提案生成」列 |
| 408 | 486 | EXACT | NFR-SI-01 表「整體」列 |
| 413 | 491 | EXACT | NFR-SI-02-1 主條 |
| 415 | 494 | EXACT | NFR-SI-02-1「實體 glob」行（區塊末行） |
| 444 | 524 | EXACT | NFR-SI-07-2 |
| 447 | 528 | EXACT | NFR-SI-08-1 |
| 450 | 531 | EXACT | NFR-SI-09-1 |
| 452 | 533 | EXACT | NFR-SI-09-3 |
| 554 | 646 | FUZZY | §9.0 查證表 Q10（觀察帳本現值 vs 700 bytes） |
| 566 | 658 | FUZZY | §9.1 元件表 C5 列 |
| 567 | 659 | FUZZY | §9.1 元件表 C6 列 |
| 601 | 733 | EXACT | §9.2 事件帳本規約「`si check` 反空轉」條 |
| 635 | 786 | FUZZY | §9.3 CLI 表 `check` 列 |
| 646 | 800 | EXACT | §9.3 CLI 表 `selfimproving_measure.py` 列（判準指紋） |
| 671 | 831 | EXACT | §9.4 預算表「提案（歸檔型）」列 |
| 676 | 836 | EXACT | §9.4 預算表之後「任何階段失敗…OBS 草稿列」句 |
| 697 | 857 | EXACT | §9.4「規格本體路徑」條 |
| 868 | 1040 | EXACT | §12.2「錯誤處理」條（階段失敗留一筆 OBS） |

  註：NFR-SI-02-1 區塊（舊 413～415）的末端 415 對應新 494 而非 493——493 是 v0.9 起新增的「機械消費」HTML 註解行（位於區塊內），新區塊範圍為 491～494；M1 判定細則的末端 78（空行）對應新 79（新 80 起為 `#### 1.3.1`），故舊 69～78 改為 70～79；§1.1 的 38 行號未動（38→38），仍逐處核對過。

- **「舊→新」逐處對照**（本檔行號＝本檔內含該座標的那一行；括號為該行座標組數；本檔行數不變，故行號與勘誤前相同）：

| 本檔行 | 組數 | 舊→新（每組） |
|--------|------|----------------|
| L39 | 17 | `635`→`786`；`450`→`531`；`635`→`786`；`676`→`836`；`676`→`836`；`452`→`533`；`646`→`800`；`635`→`786`；`646`→`800`；`566`→`658`；`635`→`786`；`413～415`→`491～494`；`697`→`857`；`566`→`658`；`61～65、69～78`→`62～66、70～79`；`567`→`659`；`444`→`524` |
| L57 | 1 | `211`→`223` |
| L68 | 4 | `452`→`533`；`868`→`1040`；`309`→`321`；`676`→`836` |
| L69 | 2 | `646`→`800`；`635`→`786` |
| L97 | 1 | `208`→`220` |
| L124 | 1 | `635`→`786` |
| L128 | 1 | `212、554`→`224、646` |
| L129 | 1 | `61`→`62` |
| L130 | 1 | `61、356`→`62、368` |
| L131 | 1 | `38、61、566`→`38、62、658` |
| L132 | 1 | `361`→`373` |
| L133 | 1 | `290、403`→`302、481` |
| L134 | 1 | `234、403`→`246、481` |
| L135 | 1 | `375、408`→`387、486` |
| L136 | 1 | `345`→`357` |
| L137 | 1 | `286`→`298` |
| L138 | 1 | `286`→`298` |
| L139 | 1 | `365、408`→`377、486` |
| L140 | 1 | `379`→`391` |
| L141 | 1 | `286、566、671`→`298、658、831` |
| L142 | 1 | `314`→`326` |
| L143 | 1 | `447、566`→`528、658` |
| L144 | 1 | `566、646`→`658、800` |
| L145 | 1 | `566、601`→`658、733` |
| L146 | 1 | `447、566`→`528、658` |
| L147 | 1 | `447`→`528` |
| L148 | 1 | `245、566`→`257、658` |
| L149 | 1 | `697`→`857` |
| L150 | 1 | `413–415`→`491–494` |
| L153 | 1 | `601`→`733` |
| L158 | 1 | `211`→`223` |
| L1432 | 2 | `208`→`220`；`208`→`220` |
| L1439 | 2 | `218`→`230`；`635`→`786` |
| L1445 | 1 | `211`→`223` |

- **一併記**（PRD §9.7 #47 主控裁決）：AT-030-2-1／AT-003-1-1 靜態段的字面「每個 `tools/lib/selfimproving/*.py`」自 P1 起由 PRD §9.4〈能力登記與純度判準〉取代，P0 判準本身不改（P0 R8（唯讀、標準庫與本地模組）與 R26（常駐機制禁字樣）仍是 P0 驗收當時的判準；P1 起套件新增 `evwrite`、`fetch` 等檔，靜態掃描改依「能力登記＋import 閉包」，見 `docs/03_testing/contracts/TCS-SelfImproving-P1-20261020.md` 的 R63（能力登記與純度）、R64（常駐機制禁字樣）與 AT-143-1-1／AT-143-1-E-1／AT-143-1-E-2；`check` 的動態純度〔AT-030-2-1 動態段〕不變）。
- **凍結紀錄**：本檔的 Stage-2 凍結 digest 自勘誤一起即與現檔不符（見勘誤二）；本次訂正後 digest 再變，仍待框架補「重記凍結 digest」動詞後由主控重記，不以手改狀態檔代替。
