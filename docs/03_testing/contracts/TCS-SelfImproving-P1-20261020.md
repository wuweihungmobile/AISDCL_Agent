# Test Contract Specification — SelfImproving P1（事件帳本與寫入鎖、運轉與歸因、提案物件與卡面、研究掃描、模組體檢、`status`／`export`、根層落點鎖、「演化只提案」可重跑檢查）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（PRD 與研究方法 SOP 於 Stage-1 凍結）的單一 Feature（P1 階段）；兩個 FSM 功能鍵共用本檔（各鍵 `spec-frozen --doc` 皆指向本檔）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P1-20261020.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-002 |
| **Feature 名稱** | SelfImproving P1：事件帳本（JSONL）與寫入鎖、`check` 的事件重放追加項、運轉與歸因（`run-open`／`run-close`／`attr*`）、提案物件與前置檢查（`prop-new`／`prop-revise`）與卡面（`card`）、研究掃描（`research`）、模組體檢（`scan`）、唯讀 `status` 與 `export`、根層模組落點鎖、Operations SOP 定稿；另含鍵 B 的「演化只提案不套用」可重跑檢查（AutoClaude 契約測試） |
| **User Story** | US-101～US-109 |
| **建立日期** | 2026-10-20 |
| **QA 負責人** | SelfImproving P1 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝Developer 棒加主控〔收尾、帳本編修、`AutoClaude/CLAUDE.md` 改述〕，三方不同） |
| **FSM 功能鍵** | 鍵 A：`monorepo-si-p1-propose`（P1 核心，根層）；鍵 B：`autoclaude-evolution-propose-only`（FR-SI-28，AutoClaude 持有面；與鍵 A 互不相依、可並行） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（monorepo 根層；上位文件＝`docs/01_requirements/SelfImproving_PRD.md` 與 `docs/05_development/SelfImproving_Research_Methodology_SOP.md`，已於 Stage-1 凍結）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。**凍結檔不得再改**：本檔發現 PRD 需修訂之處，一律寫在 §7 的 ⚖ 清單與交卷單，走掌舵者 T1／SPEC_REGRESSION_CHECK；本檔不自行改 PRD，凡 PRD 未定、本檔為使其可測而補定義者，一律標「本檔類推」並列入 §7.1。

### FRD-lite

**現況與變更（Before／After；brownfield）**

- Before：(1) P0 已完成：`tools/selfimproving.py` 只有 `check` 一個動詞（21 個判定項、四種 rc），觀察帳本九欄且遷移已豁免，協定目錄 `params.json`（23 鍵）與 `metrics.md`，Operations SOP 為骨架（擷取者節完整、其餘四個角色節只有「P1 定稿」）；(2) 沒有事件帳本載體、沒有寫入鎖與配號、沒有運轉／歸因／提案物件／卡面、沒有研究掃描與體檢、沒有 `status`／`export`；(3) 根層落點規範 SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md` 自陳「沒有機械鎖」；(4) AutoClaude「演化只提案不套用」只靠「舊 `PlaybookRunner` 沒有生產建構點」的文字宣稱（`AutoClaude/CLAUDE.md` 的 ESCALATION 條以 `main.py:<行號>` 形態引註解，行號會再腐），僅有一個既有測試（`AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py`）釘住「`PlaybookRunner` 零生產建構點」。
- After：根層新增 16 支套件模組（`tools/lib/selfimproving/` 能力類別 ro／rw／net，PRD §9.1〈C4 套件檔案表〉）與 13 個動詞（`check` 既有加 12 個新動詞）；事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl` 由 CLI 在寫入鎖內配號追加；`check` 在 21 項之後追加 7 項（`events.structure`、`events.transitions`、`events.mutated`、`events.vacuity`、`events.prop_files`、`events.research`、`research.sources`），載體缺席一律 nonblocking NE，P0 基線 repo 的 rc 與 overall 不變；PROP 提案物件與 `rN.{md,patch}` 內容檔、前置檢查（類別、`touched` 自 patch 導出並全路徑比對不可進化面與合法根、規格本體路徑、內部來源、運轉預算、同型去重、SUSPENDED、研究事件、觸及比例、M 類四欄、修訂上限）、確定性卡面（≤12 行）；研究來源表 `research_sources.json` 與唯一可連網的動詞 `research --fetch`；唯讀 `scan`、`status`、`export`；落點鎖 `tools/tests/test_root_module_layout.py`；Operations SOP 四角色定稿（含研究者節與模組體檢任務書範本）；`params.json` 加 5 個新鍵；鍵 B：`AutoClaude/tests/contract/test_evolution_propose_only.py`（AC-SI-28-1 五格各帶對照組）與 `AutoClaude/CLAUDE.md` 改述。

**AC 編號規則**（本節回答「PRD 的 AC 與本檔的 AC 怎麼對應」，並記錄兩個與任務書、PRD 字面衝突之處）：

1. **編譯文法**：ADR-XPLAT-016 §8.1 規定 AC 文法為 `AC-[\d\-]+`、AT 文法為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC、§1 映射列的 AC 須等於 AT 前兩段推得者。PRD 的 `AC-SI-NN-Y` 與 PRD §5〈編號注意〉規定的階段前綴形 `AC-P1-001-1` 兩種字面都不合此文法（含字母），照寫則 §1 映射列不被 `sdd_compile` 收、AT 列入 `unmapped_at_ids`（rc 6）。**本檔採雙名**：§1、§2 等機器可讀位置一律用合文法的數字 id；人讀處（FRD-lite 表的 AC 欄、§6）一律同時寫出 PRD 全名。
2. **對映規則**：階段前綴＝百位的 `1`（即 PRD §5〈編號注意〉所稱的 `P1` 前綴）。PRD 的 AC：`AC-SI-NN-Y`＝本檔 `AC-1NN-Y`（兩位 FR 號接兩位以內的 Y；例：PRD `AC-SI-07-3`＝本檔 `AC-107-3`、`AC-SI-30-1`＝本檔 `AC-130-1`）。本檔自增 AC：FR 號位自 40 起編（PRD 的 FR 只編到 34，無衝突），名為 `AC-140-1` 起，其 PRD 階段前綴形為 `AC-P1-040-1`（前綴 `P1-0` 即百位 `1`）；FRD-lite 表逐條標示。因此本檔不使用 P0 TCS 自增的 `AC-030-x`、`AC-031-x`、`AC-032-x` 這組號碼（PRD 的 `AC-SI-30-x` 等落在 `AC-130-x`），避免 RTM 引 P0 時還要加註「TCS 自增」。
3. **與任務書的差異**：任務書寫「P1 自 AC-033 起編本檔自增 AC、PRD 的 AC-SI-NN-M 照引」；`AC-033`、`AC-034` 與 PRD 的 `AC-SI-33-x`（P2b）、`AC-SI-34-x`（本檔 FR-SI-34 的四條）同號，故以 PRD §5〈編號注意〉為準（任務書與 PRD 不一致時以 PRD 為準），並以百位 `1` 承載該前綴（§7.1 ⚖ 1）。
4. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控／邊界 `AT-<AC 數字 id>-E-<序>`；測試函式名含其底線形（`AT-107-3-1`→`AT_107_3_1`）。每個 AC 內的 AT 序號不超過 9，使 `pytest -k AT_107_3_1` 不會誤收其他 AT。
5. **AC 數**：PRD 的 AC 44 個（鍵 A 41 個、鍵 B 3 個）加本檔自增 10 個，合計 54 個。**自增 AC 的來源逐條標示**（見下方 FRD-lite 表 AC 欄）：PRD 明文者標 PRD 座標；PRD 只給機制、未給編號者標「本檔自增」；PRD 未定、本檔為使其可測而補定義者標「本檔類推」。

**P1 交付物**（D1～D14）

| 編號 | 交付物 | 路徑（相對 monorepo 根） | 製作者 | 主要驗證 |
|------|--------|--------------------------|--------|----------|
| D1 | 事件帳本讀寫、寫入鎖與配號、折疊、`check` 追加項（重放） | `tools/lib/selfimproving/{events,fold,evcheck,evwrite}.py`（新）；`tools/lib/selfimproving/{check,params,rows,history,refs}.py`（改，限 R36～R46 所需）；事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`（由 CLI 建立，Developer 不手寫） | Developer | §2 的 AC-141、AC-108-4、AC-142 系列 AT |
| D2 | 運轉動詞 `run-open`／`run-close` | `tools/lib/selfimproving/writeverbs.py`；入口 `tools/selfimproving.py` | Developer | AC-110-3、AC-103-2 的 AT |
| D3 | 歸因動詞 `attr`／`attr-confirm`／`attr-reject` 與復發候選提示 | 同上；`tools/lib/selfimproving/{defs,rows}.py` | Developer | AC-105、AC-106 系列 AT |
| D4 | 提案動詞 `prop-new`／`prop-revise`、`touched` 導出、前置檢查、digest、PROP 內容檔 | `tools/lib/selfimproving/{paths,props,propfiles}.py`、`writeverbs.py`、`git.py`（改：新增 `apply_numstat`）；內容檔 `docs/06_quality/SelfImproving_Proposals/PROP-SI-NNN/rN.{md,patch}`（由 CLI 建立） | Developer | AC-102-1、AC-107、AC-108、AC-109、AC-110-1／110-2、AC-111、AC-144 系列 AT |
| D5 | 確定性卡面 `card` | `tools/lib/selfimproving/card.py` | Developer | AC-114 系列 AT |
| D6 | 唯讀 `status` | `tools/lib/selfimproving/{status,defs}.py` | Developer | AC-103-1 的 AT |
| D7 | 研究掃描 `research --fetch`／`--skip`、來源表驗證與抓取 | `tools/lib/selfimproving/{sources,fetch,research}.py`（`fetch.py` 唯一可 import 網路模組）；`writeverbs.py`（`--skip`） | Developer | AC-130 系列 AT（本機 HTTP 夾具，不連外網） |
| D8 | 模組體檢確定性半 `scan` | `tools/lib/selfimproving/scan.py` | Developer | AC-131 系列 AT |
| D9 | 唯讀匯出 `export`（末棒交付；P1 出口 (h)） | `tools/lib/selfimproving/export.py` | Developer | AC-132-5、AC-140-2 的 AT |
| D10 | 根層落點鎖 | `tools/tests/test_root_module_layout.py` | Developer | AC-134 系列 AT（鎖自身含正負控） |
| D11 | Operations SOP 定稿（四角色節、研究者節、模組體檢任務書範本、研究事件條文） | `docs/05_development/SelfImproving_Operations_SOP.md` | Developer（文件作者） | AC-145-2 與流程型 AC 的代位 AT |
| D12 | 協定目錄：`params.json` 加 5 鍵、研究來源表初值、指紋排除 | `docs/06_quality/SelfImproving_Protocol/params.json`（改）、`docs/06_quality/SelfImproving_Protocol/research_sources.json`（新）；`metrics.md` 不變 | Developer | AC-145-1、AC-130-2、AC-130-6 的 AT |
| D13 | 鍵 B：「演化只提案不套用」契約測試與文件改述 | `AutoClaude/tests/contract/test_evolution_propose_only.py`（新）；`AutoClaude/CLAUDE.md`（改述；該檔屬不可進化面、走一般開發、主控親改）；引擎碼零改動 | Developer（測試）、主控（改述） | AC-128-1～128-3 的 AT |
| D14 | P0 測試與鎖的連動同步 | `tools/tests/test_selfimproving_check.py`（只改 R67 列出的站點） | Developer | AC-142-2 的 AT |

**提交順序與責任**

- 鍵 A 的實作分棒由主控依持有面切（鐵律七檢查表）；依賴序為 D1 → D2、D3 → D4 → D5 → D6、D7、D8 → D9（**末棒**，PRD C.2 #12）→ D10 → D11、D12、D14。每支程式完成立即跑該區 AT（根 `CLAUDE.md`〈兩專案共通的工程紀律〉第 2 條），不累積。D12 的 `params.json` 新鍵須在 D1 的 `check` 追加項之前或同一個 commit 落地，否則 `params.keys` 紅。
- 鍵 B 與鍵 A 不同持有面（`AutoClaude/` 對根層 `tools/`），可並行；D13 的測試與 `AutoClaude/CLAUDE.md` 改述須**同一輪落地**（PRD AC-SI-28-2：改述與 ⑤ 同輪）。
- 真帳本與真事件帳本只由主控寫（PRD C1「他人只讀」）：Developer 棒不得碰真 OBS 帳本、真事件帳本與真 `SelfImproving_Proposals/`；AT 一律在 tmp 目錄的合成 repo 內進行。P1 出口 (a)（真實觀察端到端走到提案卡）由主控於實作完成後用真帳本執行，列於 §6 的實跑檢核。
- 重釘儀式（護欄層行數棘輪、`tools/tests` 檔數下限與 E501 棘輪、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE` 具名一次性例外〔名冊上限的上修須可見〕）由主控單人窗口於同一個 commit 收齊，實作者不碰鎖檔（NFR-P1-8）。

**〈P1 行為規則〉**（R27～R67；各 AT 以 R 編號引用；判定碼見其後的〈判定碼表〉。P0 的 R1～R26 在 P0 範圍內不變；P1 對其的重定與擴充見 R36、R63、R64、R67）

*A. 介面、rc 與輸出（P1 動詞；PRD §9.3、§7.2；旗標細節 PRD 只給 `check`／`status`／`research`／`scan`／`export` 與 `prop-new --patch-file`，其餘旗標為本檔類推，§7.1 ⚖ 4）*

- **R27 動詞、旗標與 rc 表**：`python tools/selfimproving.py <verb> [旗標]`。`main(argv: list[str] | None = None) -> int`、檔首 `import _stdio_utf8`、argparse 的 `SystemExit` 在 `main` 內攔截——沿 P0 R1，不重述。13 個動詞：`check`（P0 既有，規則 R1～R8 不變，追加項見 R36）加下表 12 個。凡本表未列的動詞名（含 PRD 列為 P2／P3 的 `decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`capacity`，以及 `card --issue` 這個旗標）一律 rc 3、stdout 空、stderr 至少一行。`--help` 與 `<verb> --help`：rc 0、usage 走 stdout，頂層 usage 列出 13 個動詞。共通旗標：`--repo DIR`（預設 `Path(__file__).resolve().parents[1]`；不是目錄＝rc 3）與 `--json`（`export` 必帶，其餘為選用）。**rc 通則**：唯讀非閘門動詞（`status`、`scan`、`card`、`export`）＝0（已執行）／3（無法執行）；寫入動詞＝0（已寫）／1（拒收：依帳本狀態的前置檢查失敗、取鎖逾時、事件行超長；未寫）／3（用法或輸入格式錯誤、`params.json` 必要鍵缺失或無效、家目錄不可寫）；`research --fetch` 另有 2（事件已寫、至少一個來源失敗）。**格式類錯誤（旗標缺漏、枚舉值不在集合、`--sid` UUID 與 `--line` 行號形態不合、檔案讀不到或非 UTF-8）一律 rc 3；`--coord`／`--item` 的座標不可定位（不合 P0 R16 九形態）＝rc 1＋`COORD-NONE`（R47 (a)、R48 (a)，列入拒收碼表）；依帳本當下狀態才能判定者（運轉未開、確認者等於提出者、預算超界…）一律 rc 1。**

| 動詞 | 旗標（＊必備；可重複者標「複」） | 事件 kind | 規則 |
|------|----------------------------------|-----------|------|
| `status` | `--repo --json` | —（唯讀） | R60 |
| `scan` | `--repo --json --since <commit>` | —（唯讀） | R59 |
| `card` | 位置參數 `<PROP-ID>`＊ `--repo --json` | —（唯讀） | R56 |
| `export` | `--json`＊ `--kind {observations,events,proposals,runs,status}`＊ `--since N --limit N --id <ID> --repo` | —（唯讀） | R61 |
| `run-open` | `--trigger {a,b,c,d,e}`＊ `--coord <座標>`＊複（≥1） `--by <標籤>`＊ `--repo --json` | `run.open` | R47 |
| `run-close` | `--run <RUN-ID>`＊ `--by`＊ `--repo --json` | `run.close` | R47 |
| `attr` | `--type {root,link}`＊ `--by`＊；root：`--obs <OBS-ID>`＊複 `--item <種類>=<座標>`＊複 `--root-cause <鍵>`＊；link：`--from <OBS-ID>`＊ `--reopens <ID>`＊ | `attr` | R48 |
| `attr-confirm` | `--att <ATT-ID>`＊ `--by`＊ | `attr.confirm` | R48 |
| `attr-reject` | `--att`＊ `--by`＊ `--note <一句>`＊ | `attr.reject` | R48 |
| `prop-new` | `--run`＊ `--cls {M,P,R,D,evaluator-change,loop-self}`＊ `--action {add,modify,delete,retire}`＊ `--target <路徑>`＊複 `--source <ID>`＊複 `--patch-file <檔>`＊ `--body-file <檔>`＊ `--proposer <標籤>`＊ `--reviewer <標籤> --handoff {DEF,R,T1,PRD} --memory-dir <目錄>` | `prop` | R49～R55 |
| `prop-revise` | `--run`＊ `--prop <PROP-ID>`＊ `--patch-file`＊ `--body-file`＊ `--proposer`＊ `--reviewer --handoff --memory-dir`（`cls`、`action`、`target`、`source` 沿用前一版、不收旗標） | `prop` | R49～R55 |
| `research` | `--fetch`｜`--skip`（互斥、必其一）＊ `--run`＊ `--json --repo`；`--skip`：`--reason {quota-band,offline,helmsman}`＊ `--note <一行>`＊ `--band <值>`（`quota-band` 必帶）、`--sid <UUID> --line <N>`（`helmsman` 必帶） | `research.scan`／`research.skip` | R57、R58 |

- **R28 成功、拒收與草稿列的輸出文法（寫入動詞）**：(a) **成功**（rc 0；`research --fetch` 的 rc 2 同）：文字形態＝單行 `ok <kind> seq=<N>`，指派了 ID 者接 ` id=<ID>`，再接該動詞規則列出的 ` <鍵>=<值>` 附加欄（值不含空白）；`--json` 形態＝單一 JSON 物件加換行（`ensure_ascii=False`），鍵序為 `ok`（`true`）、`kind`、`seq`、`id`（無則 `null`）、其後附加欄。(b) **拒收**（rc 1；未寫）：stdout 依序為 `reject <verb> <CODE>[,<CODE>…]`（一行）、每個碼一行 `  <CODE> <detail>`、`obs-draft:`、恰一行 OBS 草稿列；`--json` 形態＝`{"ok": false, "rc": 1, "verb": …, "codes": [{"code": …, "detail": …}, …], "obs_draft": "<列>"}`。拒收時**不得**留下任何殘留：事件帳本位元組不變、`SelfImproving_Proposals/` 無新檔、家目錄除鎖檔（已釋放）外無新檔。(c) **用法錯誤**（rc 3）：stdout 空、stderr 至少一行且以 `selfimproving:` 起頭、零寫入。(d) **OBS 草稿列**（沿 P0 R6，供主控入帳，CLI 不自寫 OBS 帳本）：ID＝`--ledger` 預設帳本現有合法 ID 最大者加一（至少三位；帳本不存在則 001）、時間＝現在本機時間 `YYYY-MM-DD HH:MM ±HH:MM`、情境＝`si <verb>（自動草稿）`、症狀＝`si <verb> 拒收（rc=1）：` 接至多 5 個碼（以「、」連接，超過尾接 `…等 <k> 項`；`<k>` 為不重複碼的總數，碼依拒收輸出中的出現順序，恰好 5 個不加尾綴）、證據座標＝反引號包住 `python tools/selfimproving.py <verb>` 接 ` rc=1`、分類 `bug`、嚴重度 `P3`、處置 `open`、標記 `面=流程;來源=工具;回報者=si-<verb>`；草稿列本身須通過 P0 R9～R17 全部逐列判準、位元組數不超過 `row_max_bytes`（AT 以 `check` 對「附加該列後的帳本」零 finding 驗證）。(e) 唯讀動詞的 stdout 形態各見其規則；一律位元組直寫、UTF-8、LF。
- **R29 路徑常數、家目錄與 params 依賴**：以下路徑一律相對 `--repo`、為常數、P1 不提供旗標（`check` 的 `--ledger`／`--params` 為 P0 既有）：OBS 帳本 `docs/06_quality/SelfImproving_Observation_Ledger.md`（含 `…_archive*.md`）、事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`、提案內容檔目錄 `docs/06_quality/SelfImproving_Proposals/`、協定目錄 `docs/06_quality/SelfImproving_Protocol/`（`params.json`、`research_sources.json`）、缺陷帳本家族（P0 R18 (b) 所列各檔）。**家目錄**＝`si_dir()`：環境變數 `AUTOSDD_SI_DIR` 非空則取之，否則 `<使用者家目錄>/.autosdd/selfimproving`；寫入動詞需要其下 `locks/`、`research/`（可建立、可寫），不可寫＝rc 3（detail `HOME-UNWRITABLE`），**不退回系統暫存目錄**。**可寫性探測**：於 `locks/` 內建立再刪除一個名為 `.probe-<行程號>` 的空檔（建不出或寫不進即不可寫；與「建不出 `locks/` 或 `research/` 目錄」是兩條不同的失敗路徑；探測檔名入規格，使測試能以同名目錄跨平台地製造「目錄在、但寫不進」，§7.1 ⚖ 28）。唯讀動詞（`check`、`status`、`scan`、`card`、`export`）不建立、不寫入家目錄下任何檔，也不要求它可寫；`export` 不讀家目錄下任何檔（R61）。**`params.json` 依賴**：每個動詞只讀它需要的鍵（R29 之後各規則逐條點名）；所需鍵缺失、型別不符或超出範圍＝rc 3（stderr 點名該鍵），不以內建預設值頂替（P0 R5 同精神）。

*B. 事件帳本、寫入鎖、配號與折疊（PRD §9.2、ADR-SI-10；事件欄位名中標「本檔類推」者見 §7.1 ⚖ 15）*

- **R30 事件行規約**：事件帳本＝單一檔、一行一個 JSON 物件。**寫入側**（CLI）：UTF-8 無 BOM、行尾只有 LF、`json.dumps(obj, ensure_ascii=False, separators=(",", ":"))`（緊湊式，鍵序為共通鍵 `seq`、`t`、`kind`、`by`，其後依 R31 表序）；`t`＝`datetime.now().astimezone().isoformat(timespec="seconds")`（帶 offset，絕不輸出 naive 時間戳）；整行位元組數（不含結尾 LF）須 ≤ `event_max_bytes`，超限＝拒收（rc 1、碼 `EVENT-BYTES-OVER`）；每次追加是**單次完整行寫入**（`行文字 + "\n"` 一次 `os.write`），且僅在既有檔案末位元組為 LF（或檔案為空、不存在）時進行，否則 rc 1（碼 `LEDGER-TORN`）。**讀取側**（`check`、`status`、`export`、`fold`）：容忍開頭 BOM 與行尾單一 CR（不判紅；P0 R9 同精神）；空白行與非 JSON 物件的行由 `events.structure` 判（R37）；`status`／`export`／`card` 遇到無法解析的行時不中止，記入 `problems`（R61）或略過並計數。**只准追加**：已提交的行被改寫或刪除由 `events.mutated` 判（R39）。
- **R31 事件欄位表（P1 範圍）**：共通鍵 `seq`（整數 ≥1、非布林）、`t`（字串，符合 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$` 且可建構為 aware 時間）、`kind`（封閉詞彙，共 19 個：`run.open`、`run.close`、`research.scan`、`research.skip`、`attr`、`attr.confirm`、`attr.reject`、`prop`、`card`、`dec`、`heldout.freeze`、`app.sandbox`、`app.verify`、`app.promote`、`app.rollback`、`mea.open`、`mea.close`、`mea.amend`、`mea.report`；PRD §9.2 逐字）、`by`（角色標籤：非空、無空白、≤32 字元）。**P1 欄位表的 kind**（必備鍵；表外的鍵＝不合規）：

| kind | 必備鍵（共通鍵之外）與型別 |
|------|----------------------------|
| `run.open` | `run`（`^RUN-SI-\d{3,}$`）、`trigger`（`a`～`e`）、`coords`（字串陣列、≥1、每個非空）、`head_sha`（40 位小寫 hex） |
| `run.close` | `run`；與下列**恰一個**：`outcomes`（物件，鍵 `^PROP-SI-\d{3,}$`、值為 R34 的狀態名）、`no_event`（JSON `true`） |
| `research.scan` | `run`、`sources`（陣列 ≥1；元素恰有 `id`、`sha256`〔`sha256:` 接 64 位小寫 hex〕、`bytes`〔整數 ≥0〕、`changed`〔布林〕、`http_status`〔200～299 整數〕）、`sources_sha256`（同 `sha256:` 形態）、`fetched_at`（同 `t` 形態）；`by` 恆為 `researcher` |
| `research.skip` | `run`、`reason`（`quota-band`｜`offline`｜`helmsman`）、`note`（1～120 字元、無換行）；`quota-band` 加 `band`（非空、不等於 `free`〔不分大小寫〕）；`helmsman` 加 `sid`（UUID）、`line`（整數 ≥1）；`offline` 無其他鍵；`by` 恆為 `main` |
| `attr` | `id`（`^ATT-SI-\d{3,}$`）、`type`（`root`｜`link`）；`root`：`obs`（OBS ID 陣列 ≥1）、`items`（陣列 ≥1，元素為二元陣列 `[種類, 座標]`，種類∈`DEF`、`OBS`、`RULE`、`PLAYBOOK_STEP`、`DOC`、`MEMORY_ENTRY`、`NONE`）、`root_cause`（`^[a-z][a-z0-9-]*/[a-z][a-z0-9-]*$`）；`link`：`from`（OBS ID）、`reopens`（OBS 或 DEF 的 ID） |
| `attr.confirm` | `att`（ATT ID） |
| `attr.reject` | `att`、`note`（1～120 字元、無換行） |
| `prop` | `id`（`^PROP-SI-\d{3,}$`）、`rev`（整數 ≥1）、`run`、`base`（40 位小寫 hex）、`cls`（`M`、`P`、`R`、`D`、`evaluator-change`、`loop-self`）、`action`（`add`、`modify`、`delete`、`retire`）、`route`（`loop`｜`handoff:DEF`｜`handoff:R`｜`handoff:T1`｜`handoff:PRD`）、`target`（排序、去重的路徑陣列 ≥1）、`touched_count`（整數 ≥0）、`touched_sha256`、`patch_sha256`、`body_sha256`、`digest`（四者皆 `sha256:` 形態）、`sources`（ID 陣列 ≥1）、`proposer`（標籤）、`reviewer`（標籤或 `null`）；`cls` 為 `M` 時另必備 `preimage`（物件：鍵為邏輯路徑、值為 `sha256:` 形態），其餘類別不得有此鍵 |

  **P2 起的 kind**（`card`、`dec`、`heldout.freeze`、`app.*`、`mea.*`）在 P1 只驗共通鍵與詞彙，其餘鍵不判（各階段 TCS 擴充欄位表）；R34、R35 的折疊讀取其中的 `prop`（PROP ID）、`dkind`、`verdict`、`flags`、`result`、`window`、`from`、`to`、`cause`、`run`（本檔類推，缺鍵＝該事件對折疊無貢獻並由 `events.transitions` 判 `TRANSITION-ORPHAN`；§7.1 ⚖ 15）。
- **R32 配號**：(a) `seq`＝鎖內讀到的**末行** `seq` 加一（檔案不存在或為空＝1；末行無法解析＝rc 1 碼 `LEDGER-TORN`）。(b) `RUN-SI-NNN`、`ATT-SI-NNN`：`NNN`＝該家族已出現於 `run.open`／`attr` 事件 `id` 欄的最大數值加一，三位零補齊（超過三位則自然加寬）。(c) `PROP-SI-NNN`：`NNN`＝max（事件帳本中 `prop` 事件的 `id` 數值、**OBS 帳本內任何 `PROP-SI-<數字>` 出現處**的數值）加一，於寫入鎖內計算——**含 archive 檔在內的 OBS 帳本讀取亦在鎖內（`build` 內）進行**，不得於取鎖前讀取後帶入（取鎖前讀到的值可能被取鎖之間他人新增的引用蓋過而撞號）（P0 已有的 OBS 引用佔用了低號；AT 的合成 OBS 帳本以執行期組出的 PROP 引用驗證）。(d) 修訂號 `rN`：同一 PROP 的 `rev` 自 1 起連號（`prop-revise` 為前一版加一）。配號只在鎖內進行；一次成功寫入恰追加一行。
- **R33 寫入鎖與鎖內判定**：所有寫事件的動詞（`run-open`、`run-close`、`attr*`、`prop-new`、`prop-revise`、`research`）一律在**寫入鎖**內完成「讀事件帳本最新內容 → 依該內容做全部依帳本狀態的前置檢查 → 配號 → 寫內容檔（僅 `prop-*`）→ 單次完整行追加」。鎖＝獨佔建檔鎖（`lib.apply_lock.acquire`，不用 `msvcrt.locking`／`fcntl.flock`，不單靠 `O_APPEND`），鎖檔 `<si_dir>/locks/<事件帳本 realpath 的 sha256 前 16 位 hex>.lock`（檔名算法：`hashlib.sha256(os.path.realpath(ledger).encode("utf-8")).hexdigest()[:16]`，`ledger` 為事件帳本路徑）；`LOCK_TIMEOUT_SECONDS`＝60、`LOCK_STALE_SECONDS`＝300 為 `evwrite.py` 的**模組常數**（初值未校準，先例 `tools/archive_apply_locked.py`；測試以 `mock.patch.object` 改小）。**寫入核心與測試鉤子**（沿 PRD §9.2〈多寫入者與配號〉併發負控 ①）：`evwrite.append_event(ledger: Path, lock_path: Path | None, build)` 是全部寫事件動詞的唯一追加路徑——`lock_path` 非 `None` 時先取鎖（逾時拋 `LockBusyError`）；為 `None` 時不取鎖（**僅供測試的無鎖對照組**，`writeverbs` 一律傳鎖檔路徑）；取得後讀事件帳本最新內容、以該狀態呼叫 `build(state)`（`state` 至少有兩個屬性：`last_seq`〔末行 `seq`，空檔或不存在＝0〕與 `events`〔已解析的事件 dict 串列〕；`build` 回傳要追加的事件 dict〔含 `kind`、`by` 與該 kind 的欄位，不含 `seq`、`t`，二者由 `append_event` 補在前端〕，或拋 `Reject`〔帶碼集合〕使本次拒收）、配 `seq`、呼叫模組屬性 `evwrite.PAUSE_HOOK`（預設 `None`＝不做事；有值時以無參數呼叫，位置在「讀末行並配號之後、單次追加之前」）、單次完整行追加、釋放鎖；測試以 `mock.patch.object(evwrite, "PAUSE_HOOK", <可暫停的函式>)` 設鉤子。取鎖逾時（`LockBusyError`）＝rc 1、碼 `LOCK-BUSY`、拒收輸出的 detail 逐字帶持鎖者（pid 與取得時間）、帳本與內容檔零變動；陳舊鎖（mtime 超過 `LOCK_STALE_SECONDS`）被回收後寫入成功；`prop-*` 若在追加事件失敗後已寫出內容檔，須刪除該次寫出的檔（尚未被事件指向的孤兒檔不得留下）。`research --fetch` 的抓取在鎖**之外**進行、鎖內只重驗與追加（R58）。
- **R34 PROP 狀態折疊表（PRD §5.1.2 的唯一合法轉移，§9.2；P1 的 `fold.py` 實作，`status`、`card`、`export`、`check` 共用）**：狀態名＝`proposed`、`approved`、`rejected`、`returned`、`handed-off`、`sandboxed`、`verified`、`promoted`、`measuring`、`closed`（`retired` 的折疊屬 P3，P1 不產生）。對該 PROP 的事件依 `seq` 折疊；不合下表任一列者為非法轉移（`events.transitions` 判 `TRANSITION-ILLEGAL`，R38）：

| 事件 | 前置狀態 | 後置狀態 | 附加條件 |
|------|----------|----------|----------|
| `prop`（`rev`＝1） | （該 `id` 尚未出現） | `proposed` | — |
| `prop`（`rev`＝N+1） | `returned`，且 N＝目前 `rev` | `proposed` | `rev` 必連號 |
| `dec`（`dkind`＝`approve`） | `proposed` | `approved` | `route` 為 `loop` |
| `dec`（`dkind`＝`reject`） | `proposed` | `rejected` | — |
| `dec`（`dkind`＝`decline-promote`） | `verified` | `rejected` | — |
| `dec`（`dkind`＝`return`） | `proposed`；或 `verified` 且最近 `app.verify` 的 `verdict`＝`FAIL` | `returned` | — |
| `dec`（`dkind`＝`ack-handoff`） | `proposed` | `handed-off` | `route` 為 `handoff:*` |
| `dec`（`dkind`＝`unblock`） | `rejected` | `rejected` | 只解除冷卻（R35），不改狀態 |
| `app.sandbox` | `approved` | `sandboxed` | — |
| `app.verify` | `sandboxed` | `verified` | `verdict`∈`PASS`、`FAIL`、`NE` |
| `dec`（`dkind`＝`promote`） | `verified` | `verified` | 最近 `verdict`＝`PASS`；或＝`NE` 且 `flags` 含 `unverified_ack`；`FAIL`＝非法 |
| `app.promote` | `verified`，且其前最近一筆該 PROP 的 `dec` 為 `promote` | `promoted` | — |
| `mea.open` | `promoted` | `measuring` | — |
| `mea.close`（`result`∈`clean`、`recurred`、`rolled-back`） | `measuring` | `closed` | — |
| `mea.close`（`result`＝`pending`） | `measuring` | `measuring` | 窗結果見 R35 |

  不改 PROP 狀態但須通過存在性判斷的事件：`card`、`app.rollback`、`dec`（`dkind`∈`rollback`；前置狀態∈`promoted`、`measuring`、`closed`）、`mea.amend`、`mea.report`、`heldout.freeze`：其 `prop` 鍵須指向已存在的 PROP，否則 `TRANSITION-ORPHAN`；`dec`（`dkind`＝`resume`）以 `run`（RUN ID）取代 `prop`，其 `run` 須存在。同一 `id` 的 `prop`（`rev`＝1）出現第二次＝非法。
- **R35 運轉、SUSPENDED 與冷卻折疊**：(a) **運轉**：`run.open` 開、對應 `run.close` 關；`open_runs`＝已開未關者；可同時有多個 open 運轉（故寫入動詞一律顯式帶 `--run`）。(b) **窗的生效結果**：每個 `mea.close` 的生效結果＝以其 `seq` 為 `window` 的最後一筆 `mea.amend` 的 `to`，無則取該 `mea.close` 的 `result`；窗依 `mea.close` 的 `seq` 排序。(c) **SUSPENDED**：取生效結果≠`pending` 的窗，若最近連續 `stop_after_bad`（`params.json`）個皆為 `recurred` 或 `rolled-back`（`pending` 的窗不計入也不打斷連續），且其後（`seq` 大於其中最後一個窗的 `mea.close`）沒有 `dec`（`dkind`＝`resume`），則為 SUSPENDED；其**所在運轉**＝`seq` 小於該最後一個壞窗 `mea.close` 的最近一筆 `run.open` 的 `run`（`status` 印出，即 `恢復` 的綁定值）。(d) **冷卻**（P1 只折疊 PRD AC-SI-13-2 的 (a) 解除）：每個目前狀態為 `rejected` 的 PROP 產生一筆 `{prop, cls, target, root_cause, rejected_seq}`——`root_cause`＝所有 `attr`（`type`＝`root`）事件中 `obs` 與該 PROP `sources` 有交集者的根因鍵（排序、去重）；`rejected_seq`＝使其轉為 `rejected` 的 `dec` 的 `seq`；之後出現指名該 PROP 的 `dec`（`dkind`＝`unblock`）即移除；(b)「新證據解除」屬 P2 的 FR-SI-13，P1 不折疊。

*C. `check` 的 P1 追加項與既有項擴充（PRD §9.3 `check` 列、§9.7 #48；AC-SI-08-4、AC-SI-30-1／30-2／30-4、AC-SI-06-2）*

- **R36 追加項總則**：(a) P0 的 21 個判定項的 id、項序、語意與判定碼**一字不變**。(b) 其後依序追加 7 項：`events.structure`、`events.transitions`、`events.mutated`、`events.vacuity`、`events.prop_files`、`events.research`、`research.sources`（共 28 項；P0 R3 的項目行文法 `[a-z_]+\.[a-z_]+` 照收）；首行 `si-check rows=<N> items=28`；JSON 的 `items` 為 28 個物件、鍵序同 P0 R4。(c) **載體缺席**：事件帳本檔不存在 ⇒ 前六項（`events.*`）各為 NE nonblocking、碼 `CARRIER-NOT-ESTABLISHED`；`research_sources.json` 不存在 ⇒ `research.sources` 為 NE nonblocking、同碼。因此 P0 基線 repo（無事件帳本、無來源表）的 `overall`、rc 與前 21 項的狀態皆與 P0 相同（`overall=PASS`、rc 0；28 項中 `ref.carrier_families` 與新增 7 項為 NE nonblocking）。(d) **nonblocking NE 的碼集合**由 P0 的單一碼擴為兩個：`CARRIER-NOT-ESTABLISHED`、`SOURCES-HISTORY-NOT-ESTABLISHED`；其餘 NE 碼一律 blocking。`QUOTE-VERIFIER-NOT-ESTABLISHED` **不是 NE 碼**：它是 `PASS` 項目上的 **warn 層級 finding**（`level` 為 `warn`，沿 R45 `REOPEN-CANDIDATE` 的形態：detail 以 `[warn]` 起頭；P0 R5：warn 不改項目狀態、不影響 rc；R38、R42 (d)）。(e) 追加項所需的 `params.json` 鍵無效 ⇒ 該項 blocking NE `SOURCE-UNAVAILABLE`（P0 R5）；事件帳本存在而需要 git 的比對（`events.mutated`）遇 git 不可用 ⇒ blocking NE `GIT-UNAVAILABLE`（`events.research` 的 git 依賴見 R42）。(f) OBS 草稿列規則（P0 R6）不變：非 PASS 項（含 nonblocking NE）依項序列入。(g) **P0 R8 的純度對追加項照樣成立**：`check` 零副作用、不連網、唯一子行程是環境淨化的 `git`；且 `check` 行程**不載入** `evwrite`、`propfiles`、`writeverbs`、`fetch`、`research` 五個模組（R63 ③）。(h) `ref.carrier_families`（P0 R18 (d)）語意**不變**：任何 `(ATT|PROP|DEC|APP|MEA|RUN)-SI-<數字>` 的提及仍印 NE nonblocking（§7.1 ⚖ 2）。
- **R37 `events.structure`**：對事件帳本逐行（先剝 BOM 與行尾單一 CR）判：空白行、或非 JSON 物件的行 ⇒ `EVENT-PARSE`；共通鍵缺 ⇒ `EVENT-KEY-MISSING`；`kind` 不在詞彙 ⇒ `EVENT-KIND`；其餘型別或值域不合（`seq` 為布林或 <1、`t` naive 或不合形態、`by` 不合標籤、R31 各列的型別與值域，含 `run.close` 的 `outcomes`／`no_event` 非恰一個、`research.skip` 的 `reason` 與附帶鍵不符、`prop` 的 `preimage` 與 `cls` 不符）⇒ `EVENT-TYPE`；P1 欄位表 kind 的必備鍵缺 ⇒ `EVENT-KEY-MISSING`、表外鍵 ⇒ `EVENT-KEY-UNKNOWN`；`seq` 非嚴格遞增（重複或遞減；可跳號）⇒ `EVENT-SEQ`；整行位元組數 > `event_max_bytes` ⇒ `EVENT-BYTES-OVER`。subject＝`seq=<n>`（`seq` 可解析時）或 `L<行號>`。P2 起的 kind 只驗共通鍵與詞彙（R31）。`event_max_bytes` 無效 ⇒ blocking NE `SOURCE-UNAVAILABLE`。**讀取側防禦（折疊的入口）**：折疊（R34、R35；`status`、`export`、`card`、`check` 與全部寫入動詞的鎖內折疊共用同一份）**只納入通過上述單事件判準的事件**——未通過者對折疊沒有貢獻（不開運轉、不登記 PROP 或 ATT、不算研究事件、不計入 `skip_reasons` 與窗），其問題只由本項以 `EVENT-*` 報；對事件欄位值做集合或字典查表前，先確認其為字串（型別怪異的值＝該事件未通過，例：`reason`、`type`、`att` 為陣列，或 `obs` 的元素為陣列，一律判 `EVENT-TYPE`，不得拋 `TypeError`，§7.1 ⚖ 26）。`export --kind events` 仍原樣輸出全部可解析的事件（R61）；`check` 的其餘追加項照常產出。
- **R38 `events.transitions`**：依 R34 折疊；非法轉移 ⇒ `TRANSITION-ILLEGAL`（subject＝PROP ID，detail 含 `seq=<n>`、事件 kind 與前置狀態）；事件的 `prop`／`att` 鍵（與 `dec`〔`dkind`＝`resume`〕的 `run` 鍵）指向不存在的對象 ⇒ `TRANSITION-ORPHAN`（subject＝該事件的 `seq=<n>`）；下列三類**不走孤兒判定**、一律 `TRANSITION-ILLEGAL`（detail 含 `seq=<n>` 與事件 kind）：`attr.confirm`／`attr.reject` 對已落定（已有 confirm 或 reject）的 ATT 再落定（subject＝ATT ID）、`run.close` 的 `run` 為未開（尚無 `run.open`）或已關的運轉（subject＝RUN ID）、`prop` 事件的 `run` 在該事件的 `seq` 時並非 open 運轉（subject＝PROP ID）；`attr.confirm`／`attr.reject` 的 `by` 等於被引 `attr` 的 `by` ⇒ `CONFIRMER-IS-PROPOSER`（subject＝被引的 ATT ID；PRD AC-SI-06-1：確認者≠提出者）。**AC-SI-08-4 ⑤**：事件帳本含 ≥1 筆 `dec`（**單一 `dec` 即印**）時，本項另印**一個 warn 層級 finding**（碼 `QUOTE-VERIFIER-NOT-ESTABLISHED`、subject `-`、detail 以 `[warn]` 起頭並含 `dec` 筆數與「引言回查屬 P2」），項目狀態不變（沒有其他問題時仍為 `PASS`）、不影響 rc（§7.1 ⚖ 3）；零筆 `dec` 不印；`dec` 的 `dkind` 轉移照 R34 判。
- **R39 `events.mutated`**：帳本相對於 `--repo` 的 POSIX 路徑記為 P。基準＝`git log --first-parent --reverse --format=%H -- <P>` 的第一個 commit（事件帳本無遷移，P0 R20 的遷移豁免不適用）；沒有任何 commit 動過 P ⇒ 本項 PASS（項目層 `detail` 為 `no-history`）。版本序列＝基準版內容、其後各 commit 的內容、工作樹內容（與 HEAD 不同時）；各版先把 CRLF 換成 LF、以 `\n` 切行。**逐對比較**（相鄰版）：前版的**每一行**須與後版同位置的行逐字相等（即前版必為後版的行前綴）；後版較短 ⇒ `ROW-MUTATED`（cause＝`deleted`）、位置上內容不同 ⇒ `ROW-MUTATED`（cause＝`changed`）；後版只在尾端多出行＝追加、放行。每筆 finding 的 subject＝**前版該位置的行**之 `seq=<n>`（`cause=changed` 與 `cause=deleted` 皆然；例：前版有 `seq` 為 3、4、5 的三行，後版刪去 3 號行而變成 4、5 兩行，則位置 3 判 `changed`（subject `seq=3`）、位置 4 判 `changed`（subject `seq=4`）、位置 5 判 `deleted`（subject `seq=5`）；前版該行無法解析則 `L<行號>`），detail 含 `commit=<短 sha 或 WORKTREE>`、`cause=<deleted|changed>` 與字樣 `掌舵者`（要求過目；與 P0 R20 同）。誠實劃界：未提交工作樹內的多步改寫無歷史可比，只看工作樹與 HEAD 的淨差異。git 不可用 ⇒ blocking NE `GIT-UNAVAILABLE`。
- **R40 `events.vacuity`**：事件帳本存在且解析到的事件數（空白行與無法解析的行不計）< `min_events` ⇒ blocking NE `EVENTS-BELOW-FLOOR`（等於下限算通過；空檔＝0 筆）；檔案不存在由 R36 (c) 處理（nonblocking NE），不在此判。`min_events` 無效 ⇒ blocking NE `SOURCE-UNAVAILABLE`。
- **R41 `events.prop_files`**：對每個 `prop` 事件，內容檔 `docs/06_quality/SelfImproving_Proposals/<id>/r<rev>.patch` 與 `.md` 須存在（缺 ⇒ `PROP-FILE-MISSING`）；`patch_sha256`＝`sha256:` 接 `.patch` 檔**原位元組**的 sha256（不做 CRLF 正規化，§7.1 ⚖ 16）、`body_sha256`＝`.md` 檔 CRLF 換 LF 後的 sha256，不符 ⇒ `PROP-PATCH-SHA-MISMATCH`、`PROP-BODY-SHA-MISMATCH`；`touched_count`、`touched_sha256` 由 `.patch` 依 R51 重新導出（`touched_sha256`＝`json.dumps(排序去重後的路徑陣列, ensure_ascii=False, separators=(",", ":"))` 的 UTF-8 位元組之 sha256，加 `sha256:` 前綴），不符 ⇒ `PROP-TOUCHED-MISMATCH`（**只在 `patch_sha256` 相符時才判**：`.patch` 已被改動者，導出值不可信，只報 `PROP-PATCH-SHA-MISMATCH` 一碼）。subject＝`<PROP-ID> r<rev>`。內容檔存在但 `git` 不可用不影響本項（重導出走 R51 的自寫解析器；`git apply` 超集檢查只在 `prop-*` 的寫入路徑，不在 `check`）。
- **R42 `events.research`（PRD AC-SI-30-1、30-2）**：(a) **每運轉研究事件**：對每個運轉 R：研究事件（`research.scan`／`research.skip`，其 `run`＝R）多於 1 筆 ⇒ `RESEARCH-MULTIPLE`（subject＝R，detail 列 `seq`）；R 有 ≥1 筆 `prop` 事件而研究事件為 0 筆 ⇒ `RESEARCH-MISSING`；唯一的研究事件的 `seq` 不介於 R 的 `run.open` 與 R 的第一筆 `prop` 之間 ⇒ `RESEARCH-ORDER`。(b) **來源 id**：每筆 `research.scan` 的 `sources[].id` 須屬來源表所有 `id`（含 `retired: true` 者），否則 `SRC-UNKNOWN`（subject＝`seq=<n> <id>`）；來源表不存在或無法解析而存在 `research.scan` ⇒ blocking NE `SOURCE-UNAVAILABLE`。(c) **`sources_sha256` 對提交歷史**：對每筆 `research.scan`，取來源表檔路徑 `docs/06_quality/SelfImproving_Protocol/research_sources.json` 的 git 提交歷史中、committer 時間不晚於該事件 `t`（**等號放行**：提交時間與 `t` 為同一秒者算不晚於）的**最近一次**提交，其當時內容（CRLF 換 LF）的 sha256（加 `sha256:` 前綴）須等於事件的 `sources_sha256`；不符、或 `t` 之前沒有任何提交含該檔 ⇒ `SOURCES-SHA-MISMATCH`（subject＝`seq=<n>`）；git 不可用 ⇒ nonblocking NE `SOURCES-HISTORY-NOT-ESTABLISHED`（單一 finding、subject `-`）。誠實劃界：來源表的 git 歷史被 rebase／amend 改寫會使既有事件永遠紅（與 `ROW-MUTATED` 同型假設）；工作樹中未提交的來源表改動不被視為歷史。(d) **`helmsman` 免掃**：存在 ≥1 筆 `research.skip`（`reason`＝`helmsman`；單一筆即印）⇒ 一個 warn 層級 finding（碼 `QUOTE-VERIFIER-NOT-ESTABLISHED`、subject `-`、detail 以 `[warn]` 起頭；項目狀態不變、不影響 rc，同 R38）；`reason`、`note`、附帶鍵的形態由 R37 判。
- **R43 `research.sources` 與來源表檔格式（PRD AC-SI-30-2、§9.2）**：來源表＝`docs/06_quality/SelfImproving_Protocol/research_sources.json`，UTF-8（無 BOM）、換行 LF、結尾換行、頂層 `{"schema_rev": 1, "sources": [...]}`；`sources` 依 `id` 的位元組序遞增；每筆必備 `id`（`^[a-z0-9][a-z0-9-]{0,31}$`、唯一）、`url`、`kind`（`changelog`｜`docs`｜`release`｜`blog`）、`extract`（非空字串）、`added_by`（非空字串），選用 `retired`（值只准 JSON `true`；缺＝現役）。**驗證函式 `sources.validate_table(raw: bytes, policy) -> list[tuple[str, str, str]]`**（回傳〔碼, subject, detail〕三元組串列，無問題＝空串列；`check` 的本項與 `research --fetch` 的預檢共用同一個函式；`sources.Policy` 為 frozen dataclass，欄位 `allow_http: bool`、`allow_loopback: bool`）依序產生下列碼，任一 ⇒ 本項 FAIL：`SRC-FILE-FORMAT`（BOM、CR、結尾無換行、不是 UTF-8 JSON 物件）、`SRC-SCHEMA`（`schema_rev` 缺或不是 1、頂層缺 `sources`、`sources` 不是陣列、元素不是物件或有表外鍵）、`SRC-FIELD-MISSING`（必備鍵缺或空）、`SRC-ID-FORMAT`、`SRC-ID-DUP`、`SRC-ORDER`（未依 `id` 位元組序遞增；`id` 相同者由 `SRC-ID-DUP` 判、不另報本碼）、`SRC-KIND`、`SRC-RETIRED-TYPE`、`SRC-URL-SCHEME`（`url` 不以 `https://` 起頭；`policy.allow_http` 為真時另收 `http://`）、`SRC-URL-USERINFO`（authority 含 `@`）、`SRC-URL-HOST`（host 為 `localhost` 或 `*.localhost`，或字面 IP 落在 `127.0.0.0/8`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`、IPv6 `::1`、`fe80::/10`、`fc00::/7`〔含 IPv4 映射寫法〕；規則集沿 `AgentConsole/docs/02_architecture/Architecture.md` §8.4 的私網段清單，**只驗字串形態**，不做 DNS 解析；`policy.allow_loopback` 為真時 loopback 放行）。`sources.DEFAULT_POLICY`＝嚴格政策（`allow_http` 與 `allow_loopback` 皆為 `False`）；CLI 入口不暴露放寬旗標，測試以 `mock.patch.object(sources, "DEFAULT_POLICY", …)` 放寬（`check` 與 `research` 同取該物件）。表檔不存在 ⇒ R36 (c)。**只增不刪**的偵測由 R42 (b) 的 `SRC-UNKNOWN` 承擔，不另設碼。
- **R44 標記欄擴充（PRD §5.1.1、AC-SI-30-4）**：標記鍵詞彙加 `src`（P0 R14 的詞彙由 10 個擴為 11 個；`MARK-UNKNOWN-KEY` 的集合隨之）；`src` 的值須符合 `^[a-z0-9][a-z0-9-]{0,31}$`，否則 `MARK-VALUE`。新增三個判定碼：(a) `回報者` 為 `研究者` 的列，若標記無 `外部衍生=是` ⇒ `RESEARCHER-NOT-EXTERNAL`、若無 `src` ⇒ `RESEARCHER-NO-SRC`（兩碼屬項目 `row.provenance`，subject＝列 ID）；(b) 任何帶 `src` 的列，其值須屬來源表所有 `id`（含 `retired`），否則 `SRC-UNKNOWN`（項目 `row.markers`）；來源表不存在或無法解析而有帶 `src` 的列 ⇒ `row.markers` blocking NE `SOURCE-UNAVAILABLE`。只在標記欄語法合格、鍵值皆已解析的列上判。P0 的其餘列判準不變。（§7.1 ⚖ 17：PRD 寫「`row.provenance`／`row.markers` 加碼」，三碼各屬哪一項為本檔類推。）
- **R45 復發候選提示（PRD AC-SI-06-2；§7.1 ⚖ 17）**：`check` 對**新列**列出「同證據座標檔案路徑」的已結列供立案者確認。**新列**＝OBS 帳本工作樹內容中、不在 HEAD 版（`git show HEAD:<帳本>`）的列（以 ID 比對；帳本未被追蹤或 HEAD 無該檔＝全部列皆新列；git 不可用＝本提示不產生），且處置首詞為 `open`、標記無 `reopens` 鍵。路徑集合：**先剝除符合 P0 R16 第八形態（`cmd`：反引號包住、以 `python`、`git` 等指令名起頭的指令片段）的片段**——草稿列的證據格就是這種片段（以反引號包住 `python tools/selfimproving.py <verb>`，其後接 ` rc=N`；見 R28 (d)），不剝則每個草稿列都因片段內的 `tools/selfimproving.py` 對已結列觸發 `REOPEN-CANDIDATE`，R28 (d) 的「零 finding」不成立；只剝該形態，反引號包住的普通路徑照取——**再**取證據座標格中 P0 R16 的 `path`、`file`、`dir` 三形態命中的片段，去掉結尾 `:行號` 或 `:行號–行號`，反斜線換成 `/`，以 `casefold` 比對。**已結列**＝(i) OBS 帳本（含 `…_archive*.md`）中處置首詞∈`fixed@…`、`DEF-…`、`merged@…`、`retired`、`decided` 的列（其證據座標格的路徑集合）；(ii) 缺陷帳本主檔與 archive 中狀態欄分類為 `fixed`、`wontfix`、`closed-by-decision`、`routed` 的 DEF 列（其「現象與證據（file:line）」欄的路徑集合；DEF 列無「分類」欄、只比路徑，候選精準度未量）；**分類與解析一律走 `defs.py`**：`defs.classify_status(text: str) -> str | None`（回傳 `open`、`fixed`、`wontfix`、`closed-by-decision`、`routed` 或 `None`）與 `defs.load_ledger_status(path: Path) -> dict[str, str | None]`（{DEF 號: 分類}；以表頭定位 `ID` 與 `狀態` 欄、同號後列覆寫前列、欄數與表頭不符的列記 `None`、無表頭回空 dict），兩者須與 `tools/check_defect_log_crossref.py` 的 `_classify`、`_load_ledger_status()` 逐筆差分一致（PRD §9.1 C4 的 `defs` 列；AC-131-2 的負控）。新列與某已結列的路徑集合有交集 ⇒ 一個 **warn 等級** finding：項目 `row.markers`、碼 `REOPEN-CANDIDATE`、subject＝新列 ID、detail 以 `[warn]` 起頭並列至多 5 個已結列 ID（依 ID 字串的位元組序排序後取前 5 個，餘以 `…+<k>`）。warn 不改項目狀態（P0 R5）、不影響 rc；新列不與自己比。
- **R46 `params.json` 新鍵、指紋排除與判準版本（PRD AC-SI-30-5／30-6、§9.7 #52）**：(a) `PARAM_SPECS` 加 5 個鍵，型別皆為整數 ≥1：`research_fetch_max`、`research_bytes_max`、`research_timeout_seconds`、`min_events`、`export_limit_max`（P0 R21 的必備鍵由 23 增為 28；缺 ⇒ `PARAM-MISSING`、型別 ⇒ `PARAM-TYPE`、範圍 ⇒ `PARAM-RANGE`）；真 `params.json` 的頂層鍵依位元組序遞增（P0 R24 不變），5 個新鍵的初值（未校準）為 8、262144、20、1、500，`check` 與 AT 不斷言值（V6 於提交當下核對）。(b) **指紋排除**：判準指紋的 manifest（P0 R7）排除相對協定目錄路徑**恰為** `research_sources.json` 的檔；排除清單只涵蓋這一個檔名；改它不改指紋、改 `params.json` 或 `metrics.md` 改指紋。(c) `check_rules_rev` 由 1 改為 2（P1 擴充 `check` 判準語意；本檔類推，§7.1 ⚖ 14）。

*D. 運轉與歸因（PRD §9.2、AC-SI-10-3、AC-SI-03-2、AC-SI-05、AC-SI-06）*

- **R47 `run-open`／`run-close`**：(a) `run-open`：`--trigger`∈`a`～`e`（對映 AC-SI-03-1 的 (a)～(e)）、`--coord` 至少一個且**每個**須通過 P0 R16 的可定位形態（否則 rc 1、碼 `COORD-NONE`，subject＝該座標；本檔類推）、`--by` 為角色標籤；`head_sha`＝`git rev-parse HEAD` 的 40 位小寫 hex，git 不可用或無 commit ⇒ rc 1、碼 `GIT-UNAVAILABLE`。寫 `run.open`（`run` 依 R32 (b)；R28 (a) 的 `id` 即 RUN ID）；附加欄 `head_sha`。可同時有多個 open 運轉。(b) `run-close`：`--run` 須為已開未關的運轉，否則 rc 1、碼 `RUN-NOT-OPEN`（含查無此 ID）。事件內容**由 CLI 折疊產生、不收旗標**（§7.1 ⚖ 13）：該運轉內所有 `prop` 事件涉及的 PROP 集合為空 ⇒ `no_event: true`（PRD AC-SI-03-2：零事件或零提案記為「無事件」、不是通過）；否則 `outcomes`＝`{<PROP-ID>: <該 PROP 此刻的 R34 折疊狀態>}`（涵蓋該運轉內出現過 `prop` 事件的每個 PROP，含修訂）。附加欄 `run`，及 `no_event=true` 或 `outcomes=<筆數>`。同一運轉不可二次關閉。
- **R48 `attr`／`attr-confirm`／`attr-reject`**：(a) `attr --type root`：每個 `--obs` 須是 OBS 帳本（含 `…_archive*.md`）的列 ID，否則 rc 1、碼 `OBS-NOT-FOUND`（subject＝該 ID）；`--item <種類>=<座標>` 的種類∈`DEF`、`OBS`、`RULE`、`PLAYBOOK_STEP`、`DOC`、`MEMORY_ENTRY`、`NONE`，不在集合 ⇒ rc 3；非 `NONE` 者座標須通過 P0 R16 ⇒ 否則 rc 1、碼 `COORD-NONE`；`NONE` 的值須以「無法歸因」起頭（不得以猜測補位）⇒ 否則 rc 1、碼 `ATTR-NONE-TEXT`；`--root-cause` 須符合 `^[a-z][a-z0-9-]*/[a-z][a-z0-9-]*$`（`<面>/<機制>`，小寫連字號）⇒ 否則 rc 1、碼 `ROOT-CAUSE-FORMAT`。(b) `attr --type link`：`--from` 須是 OBS 帳本的列（`OBS-NOT-FOUND`）；`--reopens` 須是**已結列**（R45 的定義：OBS 處置首詞∈`fixed@…`、`DEF-…`、`merged@…`、`retired`、`decided`，或 DEF 帳本家族中分類為 `fixed`／`wontfix`／`closed-by-decision`／`routed` 的列），查無 ⇒ rc 1、碼 `REOPENS-NOT-FOUND`，查得但未結 ⇒ rc 1、碼 `REOPENS-NOT-CLOSED`。`root` 與 `link` 專屬旗標互相混用 ⇒ rc 3。(c) `attr-confirm`／`attr-reject`：`--att` 須存在（`ATT-NOT-FOUND`）、尚未落定（既無 confirm 也無 reject；否則 `ALREADY-SETTLED`）、`--by` 不得等於被引 `attr` 的 `by`（`CONFIRMER-IS-PROPOSER`，確認者≠提出者）；`attr-reject` 的 `--note` 必填（1～120 字元、無換行，否則 rc 3）。附加欄：`attr` 為 `type`（`id` 由 R28 (a) 帶出）；`attr-confirm`／`attr-reject` 為 `att`。(d) **無自評分數、零寫入（PRD AC-SI-05-2）**：動詞沒有任何 `--confidence`／`--score` 類旗標（出現即未知旗標＝rc 3）；`attr` 事件的鍵恰為 R31 所列（含任何多出的鍵會被 `check` 判 `EVENT-KEY-UNKNOWN`）；歸因動詞前後 `git status --porcelain` 的差異只有事件帳本一個檔（不修改被指向的任何檔）。(e) **根因鍵更改次數**（PRD AC-SI-06-1，記入資訊欄，`status` 的 `root_cause_changes`）：對每個 OBS ID，依 `seq` 取所有 `type=root` 且 `obs` 含它的 `attr` 的 `root_cause`，相鄰兩個不同值記一次更改，全部 OBS 加總。(f) **刻意不做**：PRD §9.3 `attr` 列所述「confirm／reject 落定時於同一把鎖內重折疊採納窗並追加 `mea.amend`」屬 AC-SI-23-1 的窗機制，其寫入者與欄位屬 P3，P1 CLI 不實作（§4〈刻意不做〉、§7.1 ⚖ 11）。

*E. 提案物件與前置檢查（PRD §9.4〈`si prop-new`／`si prop-revise` 前置檢查〉、AC-SI-07～11、14）*

- **R49 `prop-new`／`prop-revise` 流程**：(a) **輸入**：`--patch-file`（unified diff，以**位元組**讀入並原樣存為 `rN.patch`；不得空、不得含 `GIT binary patch`）；`--body-file`（Markdown，須為 UTF-8；CRLF 換 LF 後存為 `rN.md`）；`--target` 與 `--source` 可重複；`--target` 須為 repo 相對 POSIX 路徑（M 類為 `memory/<檔名>`），語法不合 R51 (c) 的別名形態 ⇒ rc 3；去重並排序後入 `target`。(b) **兩階段**：階段一（輸入類，鎖內、收到即回，不進階段二）：`PATCH-EMPTY`、`PATCH-BINARY`、`PATCH-PARSE`（無可辨識標頭、C-style 引號解碼失敗、非 UTF-8 路徑、`git apply --numstat -z` 自身失敗〔R51 (b)〕）、`PATCH-PATH-MISMATCH`（`git apply --numstat -z` 看到的路徑不全在自寫解析器的聯集內，R51 (b)）、`GIT-UNAVAILABLE`、`BODY-SKELETON`、`BODY-FIELD-MISSING`、`BODY-FIELD-VALUE`（R50）；階段二（政策與狀態類，**全部收集後一併回報**）：R52～R54 與卡面高寬（R56）的碼。任一碼 ⇒ 拒收（R28 (b)），否則依序：配 `PROP-SI-NNN`／`rev`（R32）→ 寫內容檔（R55）→ 追加 `prop` 事件。(c) **`prop-revise`**：`--prop` 須存在（碼 `PROP-NOT-FOUND`）、目前折疊狀態須為 `returned`（否則 `TRANSITION-ILLEGAL`，與 `check` 的 R38 同碼；PRD AC-SI-08-2：跳級被拒並印 OBS 草稿列）、新 `rev`＝目前 `rev`＋1 須 ≤ `max_revisions`＋1（否則 `REV-LIMIT`）；`cls`、`action`、`target`、`sources` 取自該 PROP 最近一筆 `prop` 事件；`DUPLICATE-TYPE` 判定排除其自身；不計入 `BUDGET-PROPOSALS`。(d) **成功附加欄**（R28 (a) 的 `id` 即 PROP ID）：`rev`、`route`、`cls`、`digest`（文字形態印前 8 碼、`--json` 印全值）、`touched_count`；`--json` 另有 `files`（兩個內容檔的 repo 相對路徑）。(e) **誠實劃界**（PRD §9.4）：以上只擋經 SI CLI 建立的 PROP；直接用 Edit／Write 改正式面不經 SI，不在本契約的射程。**修訂超限的後果（P1）**：`REV-LIMIT` 只拒收、不寫事件、PROP 維持 `returned`；PRD 所稱「超限＝rejected＋冷卻」需要人決定事件（`dec`，P2），P1 不代寫（§7.1 ⚖ 10）。
- **R50 `rN.md` 形態（沿 SPEC-PATCH 三節骨架，PRD §9.2；欄位名為本檔類推，§7.1 ⚖ 6）**：(a) **骨架**：須有 `## ` 級標題，其文字分別含 `反例證據`、`Before`、`After`、`影響面`、`欄位`（順序不拘；缺任一 ⇒ `BODY-SKELETON`，detail 列缺者）。(b) **欄位表**：標題含 `欄位` 的節下的第一個 Markdown 表（`| 欄位 | 內容 |` 表頭加分隔列）；每列第一格為鍵、第二格為單行值（strip）。可識別的鍵：`symptom`、`risk`、`rollback`、`retire_when`、`reopen_symptom`、`budget`、`verify_plan`、`result_label`、`scope`、`source_obs`。(c) **必備**：`symptom`、`risk`、`rollback`、`budget`、`result_label`、`scope` 對**所有類別**必備（缺或空 ⇒ `BODY-FIELD-MISSING`，detail 列欄名；PRD AC-SI-09-1：輸入帶結果標籤與適用範圍、每提案宣告預算〔AC-SI-10-2〕、一個動作的回滾配方）；`result_label` 的值須∈`失敗`、`成功`、`升級`（否則 `BODY-FIELD-VALUE`）。(d) **M 類四欄**（PRD AC-SI-09-3）＝`result_label`、`scope`、`source_obs`、`retire_when`：`cls` 為 `M` 時此四欄缺或空 ⇒ `M-FIELD-MISSING`（detail 列欄名；M 類的這四欄不另報 `BODY-FIELD-MISSING`）；`source_obs` 的每個以頓號或逗號分隔的記號須是 OBS ID 且屬 `--source`，否則同碼。(e) **誠實劃界**：「輸入須是抽象化摘要、不得以原始軌跡全文充當條目」（PRD AC-SI-09-1）只能由本節的形態判準（骨架、標籤、範圍、單行欄位）近似，無機械物判定語意，流程面由 SOP 條文代位（R65）。
- **R51 `touched` 導出與別名形態拒收（PRD AC-SI-07-3、§9.4、§9.2〈鐵律三自問〉）**：(a) **自寫解析器**逐行取：`diff --git <A> <B>` 的兩個路徑（去掉各自一層 `a/`、`b/` 前綴）、`--- <路徑>` 與 `+++ <路徑>`（去前綴；`/dev/null` 視為無路徑；結尾的 TAB 與其後時間戳不計）、`rename from`／`rename to`、`copy from`／`copy to`（無前綴）；**須實作 git 的 C-style 引號解碼**（以雙引號包住的路徑內，`\"`、`\\`、`\n`、`\t`、`\ooo` 八進位位元組皆解碼，位元組序列以 UTF-8 解讀）；新增、刪除、改名兩端皆算；各處路徑取**聯集**、排序、去重，檔數即 `touched_count`（寧多勿漏；`diff --git` 與 `---`／`+++` 不一致不另判，聯集已涵蓋兩者）。(b) **超集檢查**：以 `git apply --numstat -z <patch>` 列出 git 看到的路徑（經 `git.py` 的 `apply_numstat(repo: Path, patch_file: Path) -> list[str]`、環境淨化、帶 timeout；測試以 `mock.patch.object(git, "apply_numstat", …)` 模擬「git 看見而解析器漏掉」），每一條都須在 (a) 的聯集內（比較前反斜線換 `/`），否則拒收 `PATCH-PATH-MISMATCH`；它只能檢查、不能當 `touched` 的來源（改名與複製只列目的端）。**`git apply --numstat -z` 自身失敗**（rc 非 0：損毀的 hunk、context-diff 等 git 不收的格式）＝拒收 `PATCH-PARSE`（fail-closed）：不得把失敗當成「git 沒看到任何路徑」而放行超集檢查（失敗時自寫解析器的導出值不可信，例：context-diff 會被導出垃圾路徑）；git 不可用的整體處置仍為 `GIT-UNAVAILABLE`（R49 (b)；§7.1 ⚖ 27）。(c) **別名形態**（fail-closed→整張 PROP `route=handoff`，不是拒收）：先把 `\` 換成 `/`，再判——任一段為 `..`；以 `/` 起頭（含 UNC `//`）；含 `:`（磁碟機代號、NTFS 資料流）；任一段（單獨的 `.` 除外）以 `.` 或空白結尾；任一段（取第一個 `.` 之前、`casefold`）屬 Windows 保留裝置名 `con`、`prn`、`aux`、`nul`、`com1`～`com9`、`lpt1`～`lpt9`；含 NUL 或任何控制字元（<0x20、0x7f）。(d) 兩平台對同一 patch 必須導出同一個 `touched`（macOS 未驗）；digest 內存原大小寫的正規化 POSIX 路徑（R55）。
- **R52 不可進化面、合法根、規格本體路徑與 `route`／`cls` 判定（PRD AC-SI-07-1／07-3／11-1、NFR-SI-02-1、§9.4）**：(a) **比對對象＝`touched` 的每一條**（不只 `target`）：通過 R51 (c) 的路徑先以 `os.path.realpath`（解符號連結）正規化為 repo 相對 POSIX 形（結果在 repo 之外＝逃逸＝命中），再 `normcase` 加 `casefold`，與 `params.json` 的 `non_evolvable_globs`（同法正規化）比對；glob 語意＝相對 repo 根、`**` 可吃零段至多段、不帶 `**/` 前綴者只錨定 repo 根。(b) **LATEST**：`AISDLC_SDD/AISDLC_SDD_v*/**` 的語意是「去掉 LATEST」——LATEST 名取 `lib.sdd_latest.resolve_latest_name_fast(<repo>/AISDLC_SDD)`，解析失敗（`AssertionError`）＝`None`＝整個 `AISDLC_SDD_v*/**` 視為凍結（fail-closed）；LATEST 目錄內的路徑只由其他 glob 判（例：其下的 `.claude/**`、`docs_template/**`）。純函式層以參數 `latest_name` 注入（`props`／`paths` 為 `ro` 類、不起子行程；呼叫 `sdd_latest` 的組裝在 `writeverbs`）。(c) **合法根**：`cls` 為 `M` ⇒ 每條路徑須以 `memory/` 起頭；其餘類別＝repo 根；逃出者視同命中。(d) **`R-*.yaml` 內容條件式**：命中 `AISDLC_SDD/*/governance/rules/R-*.yaml` 這個 glob 者分兩種：**base 已存在者**，只在 base 快照（`git show <base>:<路徑>`）的該檔含 `maturity: active`、或讀不出 `maturity` 時才算命中（fail-closed，§7.1 ⚖ 25）；**base 不存在（`--- /dev/null` 的純新增 `R-*.yaml`）一律不算命中不可進化面，其政策判準只有 `R-NOT-PROPOSED`**：`cls` 為 `R` 而新增的 `R-*.yaml` 不含 `trust_level: proposed` ⇒ 拒收 `R-NOT-PROPOSED`，含者受理為 `loop`（PRD AC-SI-08-3；「不得阻塞 SCG」的 FSM 面無機械物，流程面由 SOP 代位）。此款只管這個 glob：同一路徑若另落在其他 glob（例：凍結版本目錄），照該 glob 另判。(e) **規格本體路徑**：`touched` 任一條落在 `spec_body_globs` ⇒ handoff，**除了**「`cls`＝`D`、`action`＝`add`、且 `touched` 恰為一條且符合 `**/docs/01_requirements/SPEC-PATCH-*.md`」。(f) **`cls` 標記**：命中的 `non_evolvable_globs` 項若屬 PRD NFR-SI-02-1 的 (iii) 群組 ⇒ `cls` 改記 `evaluator-change`；屬 (iv) 群組 ⇒ `loop-self`（兩者皆命中取 `evaluator-change`）；群組歸屬**不另存第二份清單**，取自 PRD 該「實體 glob」行的標籤位置（與 P0 R22 `required_globs` 同一抽取、追蹤最近的 `(i)`～`(v)` 標籤；對不上的 glob 不改 `cls`，§7.1 ⚖ 8）；提案者自填的 `evaluator-change`／`loop-self` 保持。(g) **`route`**：當且僅當 `cls`（標記後）∉{`M`,`P`,`R`,`D`}、或存在別名形態、或任一 `touched` 命中 (a)／(c)／(d)／(e) ⇒ `handoff:<通道>`（整張，不得只轉交命中的檔）；否則 `loop`。**提案者不得自填 `loop`**（沒有 `--route` 旗標）；導出為 handoff 時 `--handoff {DEF,R,T1,PRD}` 必備（缺 ⇒ `HANDOFF-CHANNEL-MISSING`），導出為 loop 而給了 `--handoff` ⇒ `HANDOFF-CHANNEL-UNEXPECTED`。(h) 邊界型 M（SI CLI 前置檢查）；誠實劃界：只擋經 SI CLI 建立的 PROP。
- **R53 前置檢查：來源、運轉、研究事件、預算、SUSPENDED、同型、修訂**（全部在鎖內讀最新事件帳本後判；PRD AC-SI-02-1、10-1～10-3、30-1、17-2 的 M 半）：(a) `RUN-NOT-OPEN`：`--run` 不是 open 運轉（AC-SI-10-3：無 `run.open` 的提案不受理）。(b) `RESEARCH-MISSING`：該運轉內沒有研究事件（`research.scan`／`research.skip`；`seq` 必介於其 `run.open` 與本次寫入之間，AC-SI-30-1）。(c) `SUSPENDED`：R35 (c) 的結果非空（AC-SI-17-2 的 M 半）。(d) `BUDGET-PROPOSALS`（僅 `prop-new`）：該運轉內 `rev`＝1 的不同 PROP 數已 ≥ `max_proposals_per_run`（AC-SI-10-1；退役 PROP 同計）。(e) `DUPLICATE-TYPE`（僅 `prop-new`）：已有**活躍** PROP（折疊狀態∈`proposed`、`returned`、`approved`、`sandboxed`、`verified`）與其同型：`cls` 相同、`target` 集合相等，且兩者的根因鍵集合相交或皆為空；PROP 的根因鍵集合＝所有 `attr`（`type`＝`root`）事件中 `obs` 與該 PROP `sources` 有交集者的 `root_cause`（排序、去重；§7.1 ⚖ 7）。(f) **來源**：每個 `--source` 須可解析——`OBS-SI-<n>` 為 OBS 帳本（含 archive）的列、`DEF-<a>-<b>` 為缺陷帳本家族（P0 R18 (b) 所列檔）的列，否則 `SOURCE-UNRESOLVED`；**內部來源**＝DEF 列與標記無 `外部衍生=是` 的 OBS 列，外部衍生列（含 `回報者=研究者` 的候選）不算；解析成功的來源中內部來源為 0 ⇒ `NO-INTERNAL-SOURCE`（**任何類別**，M／P／R／D 與標記後的 `evaluator-change`／`loop-self` 皆然；PRD AC-SI-02-1、30-4 ④）。(g) `REVIEWER-IS-PROPOSER`：給了 `--reviewer` 且等於 `--proposer`。(h) `EVENT-BYTES-OVER`：組出的 `prop` 事件行超過 `event_max_bytes`（要求拆分，PRD §9.7 #49）。(i) 使用的 `params.json` 鍵：`max_proposals_per_run`、`max_revisions`、`stop_after_bad`、`event_max_bytes`、`non_evolvable_globs`、`spec_body_globs`、`max_touch_ratio`、`max_new_entries`、`max_archive_entries_per_card`、`card_line_max`。
- **R54 觸及比例、新增條目、歸檔型豁免與 M 類 pre-image（PRD AC-SI-09-2、ADR-SI-06；量法為本檔類推，§7.1 ⚖ 5）**：自 patch 的各檔 hunk 計：`removed`＝以 `-` 起頭的行（不含 `---` 標頭）、`added`＝以 `+` 起頭的行（不含 `+++`）。(a) **觸及比例**＝（所有在 base 已存在的被觸及檔的 `removed` 總和）÷（這些檔在 base 的總行數）；base 內容取 `git show <base>:<路徑>`，M 類改取 `--memory-dir` 下對應檔（`memory/<名>`→`<目錄>/<名>`；不在 `memory/` 之下的路徑已依 R52 (c) 視同命中、整張轉交，不計入比例的分子與分母）；分母為 0（全為新檔）＝比例 0；`ratio > max_touch_ratio` ⇒ `TOUCH-RATIO`（恰等於放行）。(b) **新增條目數**＝新增行中非空白且符合 `^\s*([-*+]\s|\d+[.)]\s|#{1,6}\s)` 者的個數，加新檔（`--- /dev/null`）的個數；`> max_new_entries` ⇒ `NEW-ENTRIES`。(c) **歸檔型**（僅 `cls`＝`M`）：同時成立才算——被觸及檔為索引檔（檔名 `MEMORY.md`）與歸檔檔（檔名 `archive-index-*.md`）；索引檔只有刪行與（至多）新增指標行；歸檔檔只有新增行；索引檔每一條被刪行都以**逐字**（整行相同）出現在歸檔檔的新增行中（重數一致），零內容修改。歸檔型**不受** `max_touch_ratio` 約束，改受 `max_archive_entries_per_card`（被搬移行數 > 上限 ⇒ `ARCHIVE-ENTRIES`）；歸檔型的 (b) 只計索引檔新增的指標行（歸檔檔上逐字搬移而來的新增行不計入 (b)）；任一行被改寫＝非歸檔型、回到 (a)。(d) **`--memory-dir`**：`cls` 為 `M` 而未給 ⇒ 拒收 `MEMORY-DIR-MISSING`；不是目錄 ⇒ rc 3。(e) **pre-image**（`cls`＝`M` 才有，入 `preimage`）：對 `touched` 的每個邏輯路徑（含 base 不存在的新檔），鍵＝該邏輯路徑、值＝`sha256:` 接「該檔被刪除行（依序以 `\n` 連接、結尾加 `\n`）的 UTF-8 位元組」的 sha256；只新增行的檔（含新檔）的值＝空位元組的 sha256。非 M 類無 `preimage` 鍵、digest 內以 `base` 代之（R55）。
- **R55 digest 與內容檔落地（PRD §9.2〈digest〉、AC-SI-07-3）**：(a) `digest`＝`sha256:` 接 `sha256(canonical(core))` 的 64 位小寫 hex；`canonical(x)`＝`json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` 的 UTF-8 位元組；`core` 的鍵恰為：`id`、`rev`、`cls`、`action`、`target`（排序去重的路徑陣列）、`touched`（自 `.patch` 導出的全部路徑，排序去重，**保留原大小寫**、正規化後的 repo 相對 POSIX 形）、`touched_count`、`base`、`preimage`（M 類為物件，其餘為 `base` 的值）、`patch_sha256`、`body_sha256`、`rollback`、`retire_when`、`reopen_symptom`、`budget`（後四者取自欄位表，缺的選用欄為 `null`；文字先 CRLF 換 LF）。`target` 與 `touched` 都在 digest 內。重算 digest 時 `touched` 由 `.patch` 重新導出、不信任事件裡存的值。(b) **內容檔**：`docs/06_quality/SelfImproving_Proposals/<PROP-ID>/r<rev>.patch` 與 `r<rev>.md`（目錄與檔由 `propfiles` 在鎖內建立；寫入一律 `newline="\n"`／二進位模式；已存在的 `r<rev>.*` 不得覆寫，撞名＝rc 1 碼 `PROP-FILE-EXISTS`）。(c) `patch_sha256`、`body_sha256`、`touched_sha256` 的算法同 R41。(d) 卡面顯示 digest 前 8 碼；`--json` 的 `digest` 為全值。
- **R56 `card`（PRD AC-SI-14-1～14-3、§7.3；格式為本檔據線框定義）**：`card <PROP-ID> [--json]`，唯讀。(a) **文字形態**（LF、UTF-8、位元組直寫）；`route` 為 `loop` 的 PROP：第 1 行 `[<PROP-ID>] <類別名>｜<action>｜目標：<target 以「、」連接>｜digest：<前 8 碼>｜驗證：<驗證狀態>`；第 2 行 `一、症狀：<symptom>`；第 3 行 `二、改什麼：+<added>／-<removed> 行；觸及比例 <比例，小數兩位；`M` 類印 `n/a`>；觸及檔案數 <touched_count>；不在 target 內的路徑：<k>`，其後若 k>0，**逐筆各一行** `  - <路徑>`（觸及但不在 `target` 內者，排序）；第 4 行 `三、風險與回滾：<risk>｜回滾：<rollback>｜驗證：<驗證狀態>`；第 5 行 `決定：核准 ／ 否決＋一句理由 ／ 退回＋一句修改要求`；第 6 行 `--- 以下不計入核心區 ---`；第 7 行 `證據座標：<sources 以「、」連接>｜預算宣告：<budget>｜完整 diff 座標：<該 rev 的 .patch repo 相對路徑>｜冷卻狀態：<無｜冷卻中>｜轉交通道：<通道或 無>`。`route` 為 `handoff:*`：第 1 行尾加 `｜僅轉交，本迴圈不套用`，第 5 行改為 `決定：轉交 ／ 不轉交＋一句理由`。類別名：`M`→`記憶條目`、`P`→`Playbook 片段`、`R`→`SDD 規則草案`、`D`→`非治理文件`、`evaluator-change`→`評估器變更`、`loop-self`→`迴圈自身`；驗證狀態＝R34 折疊出的最近 `app.verify` 的 `verdict`（`PASS`／`FAIL`／`NE`），無則 `未驗`。**`M` 類的觸及比例**：`M` 類的 base 是 `--memory-dir` 下的記憶檔（在 repo 之外，`card`／`export` 不帶該旗標，沒有 base 快照可重算），故卡面第 3 行的觸及比例一律印 `n/a`（比例判準只在 `prop-new`／`prop-revise` 以 `--memory-dir` 計算，R54 (a)）；其餘各行與非 `M` 類相同。(b) **核心區**＝第 1～5 行加其間逐筆列出的路徑行（不含第 6 行起）：行數須 ≤ 12（k 超過 7 ⇒ `CARD-TOO-TALL`）；**第 2～5 行與每個路徑行**的**顯示寬度**須 ≤ `card_line_max`（CJK 全形算 2：以 `unicodedata.east_asian_width` 為 `W`／`F` 者算 2、其餘算 1，同根層 E501 量法；超過 ⇒ `CARD-LINE-TOO-WIDE`，恰等於放行）；**第 1 行是標題行（含 `目標：` 的路徑，轉交卡另加轉交標記），長度隨目標而定、不受寬度限制**——PRD AC-SI-14-3 的「每項單行」讀作一、二、三、決定四項與其路徑行；若把標題行也算入，`R` 類提案（目標路徑已逾 50 個字元，標題行除目標外已佔約 65 欄）與轉交卡（標題行再多 22 欄）幾乎必然超限（§7.1 ⚖ 4）。`prop-new`／`prop-revise` 以**同一個渲染函式**對候選 PROP 預判，超限即拒收（R49 階段二）。(c) **確定性**：同一事件帳本與內容檔的內容下，輸出逐字相同；`symptom`、`risk`、`rollback`、`budget` 取自 `rN.md` 欄位表，`+added／-removed`、觸及比例、觸及檔案數與路徑行取自 `rN.patch` 與 `prop` 事件，**提案者自由撰寫的摘要不取代 diff 本文**（卡尾只給 diff 的座標）。(d) **反解析一致性**（AC-SI-14-2）：輸出前把卡面反解析回（digest 前 8 碼、`added`、`removed`、觸及檔案數、不在 `target` 內的路徑清單、驗證狀態），與重算值逐欄比對（重算值：`digest` 前 8 碼取 R55 (a) 由事件欄位與兩個內容檔**現算**的 digest 的前 8 碼——卡面第 1 行印的是事件所存的 `digest`，兩者相比；`added`、`removed`、觸及檔案數與路徑清單取自 `.patch`；驗證狀態取自 R34 折疊）；任一不符（例：`.patch` 於 `prop-new` 之後被改動）⇒ rc 3、stdout 空、stderr 含 `CARD-INCONSISTENT` 與不符欄名（不一致的卡不得送達）；PROP 不存在、內容檔缺 ⇒ rc 3（stderr 含 `PROP-NOT-FOUND`／`PROP-FILE-MISSING`）。(e) `--json`：`{"schema_rev": 1, "prop": …, "rev": …, "digest": "<全值>", "core_lines": <n>, "text": "<卡面全文含結尾 LF>", "parsed": {"digest8": …, "added": …, "removed": …, "touched_count": …, "extra_paths": […], "verdict": …}}`（鍵序如列）。

*F. 研究掃描、模組體檢、`status` 與 `export`（PRD FR-SI-30、31、32 的 AC-SI-32-5、§9.2、§9.3）*

- **R57 `research` 通則與 `--skip`（PRD AC-SI-30-1）**：(a) `research --skip --run <R> --reason <r> --note <一行> [--band <值>｜--sid <UUID> --line <N>]`：格式類錯誤一律 rc 3——`--reason` 不在 `quota-band`、`offline`、`helmsman`；`--note` 為空、超過 120 字元或含換行；`quota-band` 缺 `--band`（或值為 `free`〔不分大小寫〕）；`helmsman` 缺 `--sid`（須為 UUID）或 `--line`（須為整數 ≥1）；與該 reason 不相干的附帶旗標一併出現。狀態類錯誤 rc 1：`RUN-NOT-OPEN`、`RESEARCH-ALREADY`（該運轉已有研究事件；PRD：`--run` 須已 `run.open`、未 `run.close`，且尚無研究事件）。寫 `research.skip`（`by` 恆為 `main`；`quota-band` 帶 `band`、`helmsman` 帶 `sid`＋`line`、`offline` 無附帶鍵）；附加欄 `run`、`reason`；**零網路**（R63 ⑥）。(b) `research --fetch --run <R>` 的**預檢**（全部在發出任何請求之前；任一失敗＝整次拒收 rc 1、不抓、不寫事件、印草稿列）：`RUN-NOT-OPEN`、`RESEARCH-ALREADY`；來源表不存在 ⇒ `SOURCES-ABSENT`；對**工作樹來源表位元組先把 CRLF 換成 LF 之後**呼叫 `sources.validate_table(raw, sources.DEFAULT_POLICY)`（`raw`＝換行正規化後的位元組；任何 `SRC-*` 碼＝拒收，R43；BOM 與其餘格式問題照判，只有 CRLF 由正規化吸收）；現役（未 `retired`）筆數 > `research_fetch_max` ⇒ `FETCH-MAX`（已 `retired` 者不計）；工作樹的來源表（同樣先換成 LF）與 `HEAD` 提交版（同樣先換成 LF）逐位元組比對不同、或該檔不在 `HEAD` ⇒ `SOURCES-UNCOMMITTED`（git 不可用＝略過本項，並於輸出印 NE 提示：文字形態一行 `ne sources-commit-check git-unavailable`、`--json` 的 `ne` 陣列含 `{"field": "sources-commit-check", "reason": "git-unavailable"}`）；現役來源為 0 筆 ⇒ `ZERO-SUCCESS`。**劃界（位元組口徑）**：`check` 的 `research.sources` 與預檢取用的位元組不同——`check` 對工作樹**原位元組**呼叫同一個 `validate_table`，含 CR 即 `SRC-FILE-FORMAT`（R43）；預檢先換 LF，使 Windows 工作樹因 `core.autocrlf` 而帶 CR 的來源表，只要與 `HEAD` 版在換行正規化後相同仍可抓取，而 `check` 仍把 CR 當格式問題提醒；`sources_sha256` 一律以換行正規化後的位元組計（R42 (c)、R58 (f)）。(c) **流程**：預檢 → 依來源表順序**逐一（不併發）**抓取現役來源（R58）→ 取寫入鎖 → 鎖內重驗（運轉仍 open、仍無研究事件、來源表雜湊仍等於抓取開始時，否則依序 `RUN-NOT-OPEN`、`RESEARCH-ALREADY`、`SOURCES-CHANGED`）→ 以鎖內最新事件重算 `changed` → 追加 `research.scan`（行長超 `event_max_bytes` ⇒ `EVENT-BYTES-OVER`、不寫）。抓取在鎖**之外**進行（最壞 `research_fetch_max`×`research_timeout_seconds`，遠大於取鎖逾時）。來源檔先落地、事件後追加；事件追加失敗時來源檔留作快取、不影響帳本。(d) **rc**：0＝事件已寫且每個來源皆成功；2＝事件已寫、≥1 來源失敗（逐一列出，已抓的照記）；1＝未寫（預檢失敗、零來源成功〔改記 `research.skip(offline)` 或經 T1 修表〕、取鎖逾時、鎖內重驗失敗、事件行超長）；3＝用法或輸入錯誤（含家目錄不可寫）。(e) **輸出**：依序每個現役來源一行——成功 `source <id> ok sha256=<前 12 碼> bytes=<n> changed=<true|false>`、失敗 `source <id> FAIL <原因>`；其後成功寫入者接 `ok research.scan seq=<N> run=<R>`；有失敗者接 `obs-draft:` 與每個失敗來源各一行草稿列（R28 (d)；症狀 `si research --fetch 來源 <id> 失敗（<原因>）`、座標的 `rc=` 為本次實際 rc；各列 ID 自帳本最大合法 ID 加一起連號，依來源表順序遞增）。`--json`：`{"ok": …, "kind": "research.scan", "seq": <N 或 null>, "id": null, "run": …, "rc": …, "sources": [事件的 sources 元素…], "failed": [{"id", "reason", "detail"}…], "obs_drafts": […], "ne": […]}`。失敗原因為封閉集合：`timeout`、`http-status`、`too-large`、`non-text`、`encoding`、`redirect-refused`、`network`。
- **R58 抓取行為與事件（PRD AC-SI-30-3、30-5；`fetch.py` 是整個套件唯一 import `urllib`／`http`／`socket`／`ssl` 的檔）**：(a) `fetch.fetch_source(url, *, policy, timeout, max_bytes, allowed_hosts)` 以標準庫 `urllib.request` 對**單一**來源發 GET，取**原始位元組**；CLI 入口不暴露放寬旗標，測試以政策物件（`allow_loopback`、`allow_http`）與 `mock.patch.object(sources, "DEFAULT_POLICY", …)` 容許本機夾具。(b) **請求形態**：只准 `http`／`https`；`User-Agent` 恆為 `selfimproving-research/1`；`Accept-Encoding` 恆為 `identity`；不帶 `Cookie`、`Authorization`、`Proxy-Authorization` 或任何認證標頭；回應帶 `Content-Encoding` 且不是 `identity` ⇒ 該來源失敗 `encoding`。(c) **重導向**手動處理（關掉 `urllib` 自動跟隨）：至多 5 跳（第 6 次重導向 ⇒ `redirect-refused`）；每個目標須 scheme∈`http`、`https` 且**不得改變 scheme**（`http`↔`https` 皆拒：`https` 降 `http` 是降級、`http` 升 `https` 亦是 scheme 變更，一律 fail-closed）、目標 `hostname:port`（缺連接埠取該目標 scheme 的預設）須屬允許集合（＝現役表項 `url` 的 `hostname:port`），否則 `redirect-refused`；逐跳判定住純函式 `fetch.check_redirect(from_url: str, to_url: str, allowed_hosts) -> str | None`（拒絕時回傳 `redirect-refused`、可放行回傳 `None`；測試直接以字串餵它，覆蓋 loopback 夾具起不了的 https 降 http 與 http 升 https 等情形；**scheme 判準的負控須用顯式同埠的 URL**——預設埠下 `https` 與 `http` 的 `hostname:port` 本來就不同，會被連接埠判準先拒而遮住 scheme 判準，使它無任何測試鎖住）。(d) **界限**：整個來源（含全部重導向跳）的牆鐘 ≤ `research_timeout_seconds`，超過 ⇒ 中止、失敗 `timeout`；**強制點在每一次讀取**（含狀態列、標頭與本文）：每次讀取前以剩餘時間設定該次的逾時，不得只在區塊與區塊之間檢查期限（對持續慢滴 1 位元組的回應，區塊間檢查永遠等不到下一個區塊；亦不得以 `threading.Timer` 等常駐機制實作，R64）；已讀位元組（或 `Content-Length`）> `research_bytes_max` ⇒ 中止、失敗 `too-large`（**不截斷**）；`Content-Type` 的主型別（`;` 之前）須屬 `text/*`、`application/json`、`application/xml`、`application/atom+xml`、`application/rss+xml`、`application/xhtml+xml`，缺或不符 ⇒ `non-text`；最終狀態須 2xx，否則 `http-status`（detail 帶狀態碼）；連線或名稱解析錯誤 ⇒ `network`。(e) **成功的來源**：對原始位元組算 `sha256`（不做任何正規化），以二進位原樣寫入 `<si_dir>/research/<id>/<sha256 前 12 碼>.txt`，並維護 `<si_dir>/research/<id>/latest`（內容＝該 12 碼，無副檔名、無換行）；`changed`＝該 `id` 在事件帳本上一筆含它的 `research.scan` 的 `sha256` 與本次不同（無前筆＝`true`）。**失敗的來源**不入 `sources[]`、不得以舊 digest 代填（NFR-SI-09-1）。(f) **事件**：欄位照 R31；`sources_sha256`＝來源表檔位元組 CRLF 換 LF 後的 sha256（加 `sha256:` 前綴，與 R42 (c) 的算法相同）；`fetched_at`＝抓取完成時刻（帶 offset）；**不存 `url`、不存候選數**；`by` 恆為 `researcher`。(g) **預算與純度**：現役來源筆數、單來源位元組、單來源牆鐘三界各由 `params.json` 的 `research_fetch_max`、`research_bytes_max`、`research_timeout_seconds` 供應；`research --skip` 與其餘全部動詞零網路（R63 ⑥）。(h) 誠實劃界：`sha256` 量的是來源**原始位元組**的穩定性、不是語意改版（含伺服器端產生內容的 HTML 會使 `changed` 假陽性，來源表應優先取原始檔或 feed）；不做 DNS 解析後驗 IP；研究者讀檔的牆鐘與 token 無機械物量測。
- **R59 `scan`（PRD AC-SI-31-1～31-4；候選推導為本檔類推，§7.1 ⚖ 9）**：`scan [--json] [--since <commit>] [--repo DIR]`，唯讀、離線、無狀態、不寫事件（R63 ⑥）。(a) **起算點**：給 `--since` ⇒ 該 commit（7～40 位 hex，須可解析為 commit，否則 rc 3）的 committer 時間與 `<commit>..HEAD`；否則取最近一筆 `run.close` 事件的 `t`；無則取 `migration_base_sha` 那個 commit 的 committer 時間（`git show -s --format=%ct`）；皆無 ⇒ 起算點量不到。日精度的 DEF 列以「發現日期對起算時刻的 UTC 日期」比較：早於者排除、同日者納入。(b) **五個證據來源，各印一行**（`source <id> 讀到 <N> 筆` 或 `source <id> 量不到：<原因>`）：`defects`（缺陷帳本主檔 `docs/06_quality/AutoSDD_Defect_Log.md`；以表頭欄名定位 `ID`、`發現日期`、`嚴重度`、`狀態`；列的嚴重度∈`P1`、`P2`、狀態分類為 `open`〔`defs.py`，差分對 `check_defect_log_crossref._classify`；`open` 含 `workaround`、`partial` 字樣〕、發現日期不早於起算日；原因碼 `ledger-missing`、`ledger-header`、`anchor-unavailable`）；`observations`（OBS 帳本中 `時間` 不早於起算時刻的列數，加 `<commit>..HEAD` 或起算時刻之後（committer 時間**嚴格晚於**起算時刻；恰等於者不計）的 commit 依路徑歸桶；原因碼 `git-unavailable`、`anchor-unavailable`）；`event_ledger`（事件帳本的待決 PROP、SUSPENDED、冷卻摘要，是狀態摘要、不是候選；原因碼 `carrier-not-established`）；`build_reports`（repo 內任何路徑含 `build/reports/` 片段、副檔名∈`.xml`、`.json`、`.log`、`.txt` 的檔個數；原因碼 `no-artifacts`）；`probe_outputs`（符合常數 `PROBE_OUTPUT_GLOBS`＝`**/misstep_attribution*.jsonl` 的檔個數；原因碼 `no-artifacts`）。後兩者在 P1 只計數、不產生候選。(c) **候選列**：`defects` 每個符合列一筆（症狀 `缺陷帳本新立 <P1|P2> 未結列 <DEF-ID>`、座標＝該 DEF ID）；`observations` 每個「窗內有 ≥1 個 commit 觸及」的模組桶一筆（症狀 `<桶> 窗內有 <k> 個 commit 觸及（<至多 3 個路徑，以、連接>）`、座標＝`commit <最新 commit 的前 12 位 hex>`）。每筆候選＝P0 九欄格式：ID 自 OBS 帳本現有合法 ID 最大者加一起連號、時間帶 offset、情境 `si scan（自動草稿）`、分類 `bug`、嚴重度 `P3`、處置 `open`、標記 `面=流程;來源=工具;回報者=scan`；每列 ≤ `row_max_bytes`（超長則縮短路徑清單）、自身通過 P0 R9～R17（AT：把全部候選附加到帳本副本後 `check` 對這些列零 finding）；**無座標的候選不印**；草稿不寫入帳本（主控單窗口入帳）。(d) **模組歸桶**（PRD AC-SI-31-4；判定住純函式 `scan.bucket_of(path: str) -> str`，回傳桶名或 `未分類`，測試直接以字串餵它）：依序判 `SelfImproving`（`tools/lib/selfimproving/**`、`tools/selfimproving.py`、`tools/probe/selfimproving_*`、`tools/tests/test_selfimproving_*`、`docs/**` 下檔名含 `SelfImproving` 者）→ `AutoClaude`（`AutoClaude/**`）→ `AISDLC_SDD`（`AISDLC_SDD/**`）→ `AgentConsole`（`AgentConsole/**`）→ `根層`（其餘 repo 內路徑）；絕對路徑、含 `..`、空字串等非 repo 相對形態歸 `未分類`並計數、不丟棄；觸及多桶的 commit 依其觸及的每個路徑各歸一次。(e) **零候選＝無事件**（AC-SI-31-3、NFR-SI-09-1）：零候選時整體印 `無事件`（JSON `status:"no-event"`）；任一來源量不到時改印 `無事件（<K> 個來源量不到）`；**不得**印成「通過」「達標」「綠」；量不到不併入零；候選數只印在資訊欄；`scan` 不接任何閘門 rc。(f) **輸出**：文字形態＝五行來源、（有候選時）`candidates:` 與每筆候選一行、末行（`無事件`｜`無事件（K 個來源量不到）`｜`候選 <M> 筆`）；`--json`＝`{"schema_rev": 1, "status": "no-event"｜"candidates", "unavailable_count": K, "anchor": {"kind": "since"｜"run.close"｜"migration_base_sha"｜null, "time": <ISO 或 null>}, "sources": [{"id", "status": "read"｜"unavailable", "count"｜"reason"}…], "candidates": [{"bucket", "row"}…], "buckets": {<桶>: <候選數>…}}`。rc：0＝已執行（零候選仍 0）、3＝無法執行。(g) 誠實劃界：候選是啟發式（路徑歸桶、P≤2 未結）而非缺陷判定；「量不到」只報告 `scan` 自己讀不到的來源，讀得到但內容殘缺的看不見。
- **R60 `status`（PRD AC-SI-03-1、AC-SI-06-1、AC-SI-23-1、AC-SI-30-1、NFR-SI-09-2；鍵名與元素形態為本檔類推，§7.1 ⚖ 9）**：`status [--json] [--repo DIR]`，唯讀。物件（`--json` 的輸出；亦是 `export --kind status` 的 `items[0]`，由**同一個函式**產生）鍵序固定：`events_detected`、`unavailable`、`open_runs`、`pending_props`、`suspended`、`cooldowns`、`skip_reasons`、`capacity`、`root_cause_changes`、`reopen_candidates`、`pending_windows`、`friction_reconcile`、`no_event`。(a) **啟動事件偵測**（窗＝最近一筆 `run.close` 之後的事件；無 `run.close` 則為全部）：`events_detected` 的元素 `{"trigger": "b"｜"c"｜"d", "subject": <ID>, "detail": <字串>}`——(b)＝窗內每筆對 `type=link` 的 `attr` 的 `attr.confirm`（subject＝ATT ID，「同一症狀第二次被記入、經審查者確認」）；(c)＝缺陷帳本新立 P≤2 未結列（同 R59 `defects` 的判定與起算點；subject＝DEF ID）；(d)＝窗內已確認的復發連結，其 `reopens` 落在某個折疊狀態∈`promoted`、`measuring`、`closed` 的 PROP 的 `sources`（subject＝PROP ID）。(e)（容量事件）P3 的 `capacity` 動詞建成前**印 NOT-EVALUABLE、不得印成零**：`capacity`＝`{"status": "NOT-EVALUABLE", "reason": "capacity-verb-not-established"}`。起算點量不到（(c) 需要）⇒ `unavailable` 含 `{"trigger": "c", "reason": "anchor-unavailable"}`（正常為空陣列）。`no_event`＝`events_detected` 為空；為真時文字形態印 `無事件`（`unavailable` 非空則 `無事件（<K> 個來源量不到）`），**不得**印成通過。(b) **狀態摘要**：`open_runs`＝`[{"run", "opened_seq", "research": {"kind", "seq"}｜null, "props": [PROP ID…]}]`；`pending_props`＝折疊狀態∈`proposed`、`verified` 者 `[{"id", "rev", "state", "route", "digest8"}]`；`suspended`＝`null` 或 `{"run": <RUN-ID>}`（R35 (c)，即 `恢復` 的綁定值）；`cooldowns`＝R35 (d) 的元素陣列；`skip_reasons`＝`{"quota-band": n, "offline": n, "helmsman": n}`（三鍵恆在，計所有 `research.skip`）；`root_cause_changes`＝R48 (e) 的整數；`reopen_candidates`＝`{"unsettled": <無 confirm／reject 的 type=link 的 attr 筆數>}`；`pending_windows`＝`[{"prop", "close_seq"}…]`（生效結果為 `pending` 的 `mea.close`）。(c) **交卷對帳**（NFR-SI-09-2，只量不閘；**P1 恆為 NOT-EVALUABLE**，`measured` 分支屬 P2 起、P1 不產生，§4〈刻意不做〉）：`friction_reconcile`＝`{"status": "NOT-EVALUABLE", "reason": <下列兩種之一>}`——`transcript-unavailable`（逐字稿目錄取不到，例：容器內或他機。**逐字稿目錄取法**：`lib.platform_utils.claude_home()`〔環境變數 `CLAUDE_CONFIG_DIR` 非空白則取之，否則 `Path.home() / ".claude"`〕下的 `projects/<slug>/`，`<slug>` 由 `--repo` 的解析後絕對路徑推得：`re.sub(r"[^A-Za-z0-9]", "-", <路徑字串>)`（規則同 `tools/probe/audit_session.py` 的 `project_transcript_dir`，是觀察到的編碼、非官方契約；`status` 自行實作、不 import `probe`，守 R63 的 import 範圍），例：`D:\CursorProject\AISDCL_Agent` 對應 `D--CursorProject-AISDCL-Agent`；該目錄不存在或讀不到＝取不到。tmp 目錄下的合成 repo 其 slug 目錄不會存在，再加 §5.5 (b) 的家目錄隔離，AT 中此欄在未特別佈置時必為 `transcript-unavailable`）；`transcript-parser-not-established`（逐字稿目錄存在，但「流程摩擦」節項數的解析器 P1 未建立：目錄存在不等於量得到，不得因此印成 `measured` 或任何數字計數）。量不到不得印成 0。(d) 事件帳本不存在 ⇒ 全部事件類欄位為空狀態、`unavailable` 照常，不是錯誤；rc 0（已執行）或 3。文字形態逐鍵印出（至少含 `無事件`／事件行、`capacity NOT-EVALUABLE`、`suspended`、`skip_reasons` 各字樣）。
- **R61 `export`（PRD AC-SI-32-5、§9.2〈`export --json` 輸出〉；Console 三層屬 P1b，本檔只定根層的輸出契約與穩定性）**：`export --json --kind <k> [--since N] [--limit N] [--id <ID>] [--repo DIR]`，唯讀、離線、只用標準庫。**用法錯誤＝rc 3**：缺 `--json`；`--kind` 不在 `observations`、`events`、`proposals`、`runs`、`status`；`--limit` <1 或 > `export_limit_max`；`--since` 非非負整數，或與 `status` 併用；`--id` 與 `observations`／`events`／`status` 併用，或格式不合（`proposals` 須 `^PROP-SI-\d{3,}$`、`runs` 須 `^RUN-SI-\d{3,}$`）。**輸出**：單一 JSON 文件加 LF，UTF-8 位元組直寫（`ensure_ascii=False`、無 BOM）；頂層鍵序 `schema_rev`（1）、`kind`、`generated_at`（呼叫時刻、帶 offset）、`head_sha`（`git rev-parse HEAD` 的 40 碼；git 不可用＝`null` 並於 `ne` 列 `{"field": "head_sha", "reason": "git-unavailable"}`）、`items`、`next_since`（整數或 `null`）、`truncated`（布林）、`ne`（`[{"field", "reason"}…]`：量不到的欄位逐一列出、不省略）、`problems`（`[{"subject", "code", "detail"}…]`：帳本結構層問題，例如無法解析的事件行，不是 `check` 的判級）。`items` 依 kind：`observations`＝九欄（鍵 `id`、`time`、`context`、`symptom`、`evidence`、`category`、`severity`、`disposition`、`marks`，值皆字串）加 `marks_kv`（`rows.parse_marks` 的解析：鍵→值）與 `line`（帳本 1 起算實體行號），欄數不是九的列＝`{"line", "raw", "valid": false}`（並於 `problems` 記 `ROW-ARITY`）；`events`＝事件原樣（不加鍵）；`proposals`＝`id`、`state`、`route`、`cls`、`action`、`run`、`rev`、`digest`、`target`、`touched`（自最新 rev 的 `.patch` 現導）、`touched_count`、`sources`、`created_seq`、`last_seq`、`verdict`、`flags`、`cooldown`（物件或 `null`）、`card`（`card` 動詞逐字輸出的文字；內容檔缺或反解析不一致 ⇒ `card: null` 並於 `ne` 列 `{"field": "proposals.<id>.card", "reason": <碼>}`）；`runs`＝`id`、`opened_seq`、`closed_seq`、`trigger`、`head_sha`、`research`（`{"kind", "seq"}` 或 `null`）、`prop_ids`、`outcome`（`"no_event"`、`{PROP: 狀態}` 或未關時 `null`）；`status`＝單元素陣列，元素＝R60 的物件。**游標**：`--since N`＝嚴格大於 N（`events` 取 `seq`；`observations`、`proposals`、`runs` 取 ID 的數字部分）；`--limit N` 預設與上限＝`export_limit_max`；`next_since`＝本頁最後一筆的游標、已無下一頁＝`null`；`truncated`＝是否因 `--limit` 截斷（本頁之後仍有符合游標的項目才為真：筆數恰等於 `--limit` 時為 `false`、`next_since` 為 `null`，多一筆才為 `true`）。`--id` 取單筆，找不到＝`items: []`、rc 0。**事件帳本不存在**：`events`、`proposals`、`runs`＝`items: []`、`status`＝全空狀態的單元素，四者的 `ne` 皆含 `{"field": "events", "reason": "carrier-not-established"}`（不是零筆通過）。**Console 不得見的內容**：`export` 不讀、不印 `<si_dir>/` 下任何檔（AT：把哨兵字串放進 `AUTOSDD_SI_DIR` 的檔後輸出不得含它）。**共用同一組函式**：`export` 與 `status`、`card`、`check` 共用 `fold.py`、`card.py`、`status.py`（R63 ③ 以 import 關係加差分測試驗證，不得有第二份折疊或卡面實作）。**穩定性**：同一狀態下連續兩次輸出，除 `generated_at` 外逐字相同；`PYTHONIOENCODING=cp950` 的子行程輸出仍為 UTF-8。rc：0＝已輸出（`ne`／`problems` 非空不是錯誤）、3＝用法或輸入錯誤。

*G. 落點鎖、純度、SOP、鍵 B 與既有測試同步（PRD FR-SI-34、§9.4、FR-SI-28、§9.7 #47／#48）*

- **R62 落點鎖 `tools/tests/test_root_module_layout.py`（PRD AC-SI-34-1～34-4、§9.1〈C19 判準〉）**：判準函式以 `repo_root: Path` 為參數（真樹與 AT 的合成樹用同一份碼）。(a) **登記表解析**：取 SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md` 中標題含 `## 3.` 的節內、欄數為六的資料列；取第 2～5 欄的反引號片段；含空白者（指令字串）、以 `~` 或 `$` 起頭者（repo 外）不判；含 `/`、結尾為 `.py`、`.md`、`.json`、`.jsonl`、`.yml`、`.yaml`、`.ps1`、`.sh` 之一、或含 `*` 者為**路徑候選**（`ledger`、`_hook_launcher` 這類裸詞不判）；無目錄前綴的檔名片段承繼**同欄前一個帶目錄的片段**為基底（**只承繼其前方**：同欄中位於該檔名片段之前、最近的一個帶目錄片段，其後的片段不影響它；候選基底＝該片段本身〔若為目錄〕與其上一層，任一處命中即過）；含 `*` 者 glob 展開至少命中一檔，目錄片段須存在且含檔。(b) **AC-SI-34-1**：每個路徑候選在磁碟至少命中一檔；缺一 ⇒ 紅並印列名與路徑；解析不到登記表或解析出 0 列 ⇒ 紅（不得 0 列通過）。(c) **AC-SI-34-2**：`tools/lib/` 的扁平 `.py` 檔（不含 `__init__.py`）取檔名第一個底線之前為前綴，同前綴 ≥3 支且 `tools/lib/<前綴>/` 套件目錄不存在 ⇒ 紅；存量以 **shrink-only 名冊**豁免（名冊住測試檔常數、初值＝以本規則對真樹現查的結果；名冊內前綴若已成套件須自名冊移除，否則紅；名冊另受天花板常數雙邊相等釘住：長大或縮短而不下修天花板皆紅）；新增檔使一個未入名冊的前綴達 3 支 ⇒ 紅。(d) **AC-SI-34-3**：`tools/lib/` 下每個含 `__init__.py` 的套件目錄，其名須出現在某一列「程式碼」欄的某個**反引號片段**內（片段為 `tools/lib/<套件>/`，或以它起頭的路徑；該欄片段之外的散文字串不算登記、其他欄的片段亦不算），未登記 ⇒ 紅。(e) **AC-SI-34-4**：`docs/01_requirements/*_PRD.md` 中含字樣「模組落點表」者，必含字串 `docs/02_architecture/Root_Layout_and_Module_Placement.md`，缺 ⇒ 紅。(f) 邊界型 M（形態判準）；誠實劃界：只驗路徑存在與登記，不驗路徑「該不該在那裡」；只看檔名前綴，同一模組換前綴命名的散落看不見；只判含該字樣的 PRD。新增 `tools/tests/` 檔須付重釘稅（NFR-P1-9）。
- **R63 能力登記與純度（PRD §9.4〈能力登記與純度判準〉；取代 P0 AT-030-2-1／AT-003-1-1 靜態段的「每個 `tools/lib/selfimproving/*.py`」字面）**：登記表常數 `CAPABILITY`（鍵＝`tools/lib/selfimproving/` 下的檔名，值＝類別 `ro`／`rw`／`net`）住 `tools/tests/test_selfimproving_capability.py`，共 24 個：`ro`＝`__init__`、`ledger`、`rows`、`git`、`refs`、`history`、`params`、`check`、`events`、`fold`、`evcheck`、`paths`、`props`、`defs`、`sources`、`card`、`status`、`scan`、`export`（19）；`rw`＝`evwrite`、`propfiles`、`writeverbs`（3）；`net`＝`fetch`、`research`（2）。**判準**：① 套件內每個 `*.py` 都在登記表、登記表的每個檔都存在（新檔未登記 ⇒ 紅）；② 逐檔掃描符合所登類別——`ro`：不得有 P0 的寫入形原語（正規式 `write_text|write_bytes|\.mkdir\(|os\.remove|os\.unlink|os\.rename|os\.replace|shutil\.|open\([^)]*['"][wax]b?\+?['"]`）、`os.system`／`os.popen`、網路模組 import，且 `subprocess` 字樣只准出現在 `git.py`；`rw`：不得 import 網路模組、不得有 `subprocess` 字樣；`net`：網路模組（`socket`、`urllib`、`http`、`ssl`、`ftplib`、`smtplib`、`asyncio`、`requests`）的 import 只准出現在 `fetch.py`（`research.py` 因 `import` 它而歸 `net`，自身不直接 import 網路模組）；所有類別的 import 只准標準庫、`_stdio_utf8`、`lib`（含 `lib.apply_lock`、`lib.sdd_latest`）與套件內相對 import；③ `check.py`、`status.py`、`scan.py`、`export.py`、`card.py` 的**相對 import 閉包**（經 AST 取 `from . import x`、`from .x import y`、`import lib.selfimproving.x`）⊆ `ro` 檔（唯讀動詞在結構上碰不到寫入或網路碼）；④ 常駐機制禁字樣（R64）仍掃全套件與入口；⑤ **動態**：在乾淨直譯器行程中 import `lib.selfimproving.check` 並跑一次 `check`，`sys.modules` 內不得出現 `lib.selfimproving.evwrite`、`.propfiles`、`.writeverbs`、`.fetch`、`.research`（`check` 行程不載入寫入與網路碼）；入口 `tools/selfimproving.py` 的模組層級 import 只含 `ro` 類模組，`writeverbs`、`research` 等一律在 handler 內延遲 import；⑥ **動態零網路**：對 `status`、`scan`、`card`、`export`、`check`、`run-open`、`run-close`、`attr*`、`prop-*`、`research --skip` 各跑一次，期間 `socket.socket.connect` 被替換為會拋例外者，皆不得觸發。`check` 自身的動態純度（P0 AT-030-2-1 的動態段：檔案摘要與 `git status --porcelain` 前後相同、子行程只有環境淨化的 `git`）不變，且涵蓋追加的 7 項。這不是新增守衛碼：測試檔在 `tools/tests/`、不在守衛面清單、不是 hook（PRD §9.7 #47）。
- **R64 常駐機制禁字樣（P0 R26 的 P1 重定）**：`tools/selfimproving.py` 與 `tools/lib/selfimproving/` 下**每個** `*.py`（含 `__init__.py` 與全部 `ro`／`rw`／`net` 檔；`apply_lock` 的輪詢睡眠在 `tools/lib/apply_lock.py`、不在套件內），原始碼不得出現 P0 R26 的 14 個正規式（`schtasks`、`launchctl`、`crontab`、`ScheduleWakeup`、`CronCreate`、`Register-ScheduledTask`、`apscheduler`、`threading\.Timer`、`sched\.scheduler`、`time\.sleep`、`while\s+True`、`daemon\s*=\s*True`、`os\.fork`、`signal\.alarm`；區分大小寫）；根 `.claude/settings.json` 全文不得含 `selfimproving`（不分大小寫）；P2／P3 動詞（R27）一律 rc 3。P0 R26 中「`status`、`prop-new` 等非 `check` 動詞一律 rc 3」的字面隨 P1 動詞落地而被取代（P0 測試改選仍未實作的動詞，R67）。
- **R65 Operations SOP 定稿（PRD §9.1 C6、AC-SI-30-4／31-5 的任務書範本；`docs/05_development/SelfImproving_Operations_SOP.md`）**：測試以 LF 正規化全文與「`## ` 標題切段」判定，只判關鍵片段是否存在，語意由實跑檢核 V7 對照 PRD。(a) **P0 條文不退化**：P0 R25 的全部關鍵片段（擷取者節、啟動條件節、無事件、再開、真缺陷升 DEF、外部衍生、loop-self、流程摩擦入口、M 之後只追加）仍成立——由 P0 既有測試不改地執行把關；四個角色節（`歸因者`、`提案者`、`審查者`、`凍結者`）各須**仍含字面「P1 定稿」**作為狀態標示（P0 的 AT-032-1-1 斷言它），並另有實質內容。(b) **歸因者節**須含：`attr`、`attr-confirm`、`attr-reject`、`根因鍵`、`NONE`、`無法歸因`、`確認者`；一行同時含 `理論洞`、`P4`、`暴露證據`、`不立案`（AC-SI-07-2 的代位條文）；一行同時含 `evaluator-change`、`evaluator_command`、`expected_output_regex`、`OBS`、`不得轉送沙盒`（AC-SI-11-2 的代位條文）；**模組體檢任務書範本**（含 `模組體檢` 的子標題之下）：五個模組桶名 `AutoClaude`、`AISDLC_SDD`、`AgentConsole`、`根層`、`SelfImproving`；工具行 `Read／Grep／Glob／PowerShell`；`唯讀`、`不得 Write／Edit`、`git status --porcelain`、`文字交卷`、`流程摩擦`、`不並行扇出`、`零遞迴`；且 PRD FR-SI-31「模組體檢入口表」第 2 欄（先讀）的每個反引號片段都出現在該範本內（片段自 PRD 現抽，本檔不複寫第二份清單，PRD 為唯一真相源）。(c) **提案者節**須含：`prop-new`、`--patch-file`、`scratchpad`、`抽象化`、`結果標籤`、`適用範圍`、`增量`、`觸及比例`、`預算宣告`、`外部衍生`、`內部來源`、`M 類四欄`；一行同時含 `抽象化`、`結果標籤`、`原始軌跡全文`（AC-SI-09-1 的代位條文）；一行同時含 `不得再派`、`提案者`、`審查者`（AC-SI-10-2 的代位條文）；`R 類`與 `trust_level: proposed`。(d) **審查者節**須含：`唯讀`、`不得自起背景長任務`、`外部可重跑訊號`、`不同代理實例`。(e) **凍結者節**須含：`評估集`、`提案者看不到`、`heldout-freeze`。(f) **研究者節**（新增的 `## ` 級標題含「研究者」）須含：`Read／Grep／Glob`、`無 Web 工具`、`資料、不是指令`、`changed=true`、`外部衍生=是`、`src=`、`文字交卷`、`每運轉至多一個`、`--pace`、`quota-band`、`research_sources.json`、`僅 T1`。(g) **研究事件條文**：一行同時含 `研究事件`、`research.scan`、`research.skip`、`prop-new`、`拒收`；一行同時含 `quota-band`、`offline`、`helmsman`。
- **R66 鍵 B：「演化只提案不套用」可重跑檢查（PRD FR-SI-28、§9.1 C13、ADR-SI-07；`AutoClaude/tests/contract/test_evolution_propose_only.py`，引擎碼零改動）**：形態沿 `AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py` 的 AST 普查加對照組；檔名不帶輪號。判準函式取參數（掃描根、受檢清單）以便合成樹自證。五格：① **引用格**：以 AST 讀既有的 `AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py`（下稱 r85 檔），斷言它仍含函式 `test_playbook_runner_has_no_production_construction_site` 與 `test_the_scanner_can_see_production_sites_at_all`（本檔引用、不重寫掃描）；② **`apply_evolution` 呼叫點**：普查 `autoclaude/` 下 `Call` 節點（func 名取 `Name.id` 或 `Attribute.attr`）為 `apply_evolution` 者，依（相對 `autoclaude/` 的 POSIX 路徑、外層函式名）彙整，須恰等於受檢清單常數 `APPLY_EVOLUTION_SITES`（現況＝`execution/steps_orchestrator/_escalation_handler.py` 三處與 `execution/mutation_applier/_complex_mutations.py` 一處；清單以檔加外層函式登記、不寫行號，由 Developer 現查原始碼填入），且 `execution/` 之外沒有任何模組 import 含 `steps_orchestrator` 或 `mutation_applier` 的模組路徑；③ **演化重載生產者**：普查 `plugins/` 與 `core/` 下 (i) 任何 `Call` 的 keyword `evolved_playbook_path`、(ii) `PersistenceResult(...)` 的 keyword `kind` 為常數 `"evolved_playbook"`，須零命中，唯排除檔（定義與彙整）`core/kernel_state.py`、`core/resolution_policy.py`（常數 `PRODUCER_EXCLUDED`，附 WHY）；原因：`core/services/auto_resume.py` 的演化重載分支無 signoff 閘，現靠「無生產者」不可達；④ **signoff 讀取點**：`autoclaude/` 下對屬性 `require_evolution_signoff` 的讀取（`Attribute`，Load 語境）只准出現在 `execution/playbook_runner.py`；⑤ **文件宣稱釘住**：`AutoClaude/autoclaude/main.py` 仍含字樣「舊 PlaybookRunner 直連模式已於 W6 拔除」；`AutoClaude/CLAUDE.md` 中含 `ON_ESCALATION` 的敘述行（常數 `EVOLUTION_DOC_ANCHOR`）至少一行含該字樣，且這些行皆不含 `main.py:<數字>` 形態（正規式 `main\.py:\d+`）。**每格自帶對照組**：① 以缺該函式的合成檔文字判紅；② 掃描器在 `execution/` 抓得到 `apply_evolution`（≥4 筆），合成樹多一個呼叫點或在 `execution/` 外多一個 import 即紅；③ 掃描器在 `execution/` 抓得到 `evolved_playbook_path=`（≥3 筆）、在排除檔 `core/resolution_policy.py` 抓得到至少 1 筆，合成 `plugins/x.py` 含該 keyword 即紅；④ 掃描器在 `execution/playbook_runner.py` 抓得到讀取，合成的另一處讀取即紅；⑤ 合成含 `main.py:277` 的文件文字與缺字樣的合成 `main.py` 皆判紅。**AC-SI-28-2**：`autoclaude/utils/config.py` 的 `require_evolution_signoff` 預設值仍為 `False`（AST 讀欄位預設，零退化）；`AutoClaude/CLAUDE.md` 的演化敘述含 `Kernel 路徑只提案`、`預設放行`、`無生產建構點`、`無演化重載生產者` 四個片段（各刪一則判紅）；該行長度仍 ≤ 800 codepoint（既有鎖 `AutoClaude/tests/contract/test_claude_md_no_long_lines.py`）。**AC-SI-28-3**：①～④ 任一格轉紅時，斷言訊息須含 `OBS-SI-010`、`升為缺陷列`、`FR-SI-12`（AT 以合成注入使該格失敗並檢查訊息）。誠實劃界：AST 為形態判準，`getattr`／`importlib` 動態建構看不到。
- **R67 既有 P0 測試與鎖的連動同步（PRD §9.7 #48 加本檔查得的兩處，§7.1 ⚖ 12）**：P1 只准改 `tools/tests/test_selfimproving_check.py` 的下列站點（座標為本檔撰寫時現查的快照值，重跑法＝Grep 該函式名），其餘 P0 測試一字不動：

| 站點（函式名；行號為快照） | 為何會紅 | 改法 |
|----------------------------|----------|------|
| `test_AT_001_1_1_baseline_is_green`（`ITEMS21` 全等、`items=21` 字串；約 L712、L726） | `check` 項數 21→28 | 項 id 清單改為前 21 個等於 `ITEMS21` 且總數為 28；首行改 `items=28`；其餘斷言不動（前 21 項 PASS／載體項 NE 照舊，新增 7 項在基線為 NE nonblocking） |
| `test_AT_003_1_1_no_resident_mechanism`（`("status", "prop-new")` 須 rc 3；約 L1360–1362） | 這兩個動詞已存在 | 改選仍未實作的動詞 `("decide", "promote")`；靜態禁字樣掃描 `si_sources()` 不動（R64：仍掃全套件） |
| `test_AT_030_1_E_1_usage_errors`（`calls` 內的 `["status"]`；約 L1842） | `status` 已存在、不再是用法錯誤 | 該項改 `["decide"]`（rc 3、stdout 空、stderr 非空） |
| `params_dict()`（合成 `params.json`；約 L275–315） | `PARAM_SPECS` 多 5 個必備鍵，缺鍵使基線 `params.keys` 紅 | 補 `research_fetch_max`＝8、`research_bytes_max`＝262144、`research_timeout_seconds`＝20、`min_events`＝1、`export_limit_max`＝500（`dump_params` 的鍵序排序照舊） |
| `test_AT_030_2_1_purity`（靜態段以 `si_sources()` 掃全套件的寫入形原語與網路 import；約 L1958–1971） | 套件新增 `rw`／`net` 檔（`evwrite`、`fetch` 等） | 靜態段改掃「入口＋登記為 `ro` 的檔」（自 `tools/tests/test_selfimproving_capability.py` 匯入 `CAPABILITY` 衍生）；動態段不動 |

  **不用改但受 P1 約束**：`test_AT_032_1_1_sop_skeleton`（斷言四個角色節含「P1 定稿」；R65 (a) 要求保留該字面）、`test_AT_001_1_E_6_fixed_sha`（非 git 目錄「17 項 PASS、blocking NE 恰四項」；R36 (c) 使新增 7 項為 nonblocking NE 而不影響）、`test_AT_031_1_1_real_params`（真 `params.json` 須含新 5 鍵，D12）、`test_AT_030_3_1_fingerprint`（基線無 `research_sources.json`，排除規則不影響；`check_rules_rev` 只斷言 ≥1）、`fingerprint_of()` 輔助函式（同理）。改後以 `python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=` 須仍為「42 passed」（子測試數以實跑為準），逐字貼末行。

**〈判定碼表（P1 追加；P0 的 21 項與其碼不變）〉**（項序即輸出序；「狀態」欄＝該碼命中時該項的狀態）

| 項目 ID | 碼 | 狀態 | 觸發 |
|---------|-----|------|------|
| `events.structure` | `EVENT-PARSE` | FAIL | 空白行或非 JSON 物件的行（R37） |
| `events.structure` | `EVENT-KEY-MISSING`、`EVENT-KEY-UNKNOWN` | FAIL | 共通鍵或欄位表必備鍵缺；P1 欄位表 kind 出現表外鍵（R37） |
| `events.structure` | `EVENT-KIND`、`EVENT-TYPE` | FAIL | `kind` 不在 19 個詞彙；型別或值域不合（R31、R37） |
| `events.structure` | `EVENT-SEQ` | FAIL | `seq` 重複或遞減（R37） |
| `events.structure` | `EVENT-BYTES-OVER` | FAIL | 整行位元組大於 `event_max_bytes`（R37） |
| `events.transitions` | `TRANSITION-ILLEGAL`、`TRANSITION-ORPHAN` | FAIL | 非法轉移；引用不存在的 PROP／ATT／RUN（R34、R38） |
| `events.transitions` | `CONFIRMER-IS-PROPOSER` | FAIL | `attr.confirm`／`attr.reject` 的 `by` 等於被引 `attr` 的 `by`（R38） |
| `events.transitions` | `QUOTE-VERIFIER-NOT-ESTABLISHED` | PASS（warn finding；項目狀態不變） | 事件帳本含 ≥1 筆 `dec`，引言回查屬 P2（R38） |
| `events.mutated` | `ROW-MUTATED` | FAIL | 已提交的事件行被改寫或刪除（R39） |
| `events.mutated` | `GIT-UNAVAILABLE` | NE blocking | git 不可用（R39） |
| `events.vacuity` | `EVENTS-BELOW-FLOOR` | NE blocking | 事件數小於 `min_events`（R40） |
| `events.prop_files` | `PROP-FILE-MISSING`、`PROP-PATCH-SHA-MISMATCH`、`PROP-BODY-SHA-MISMATCH`、`PROP-TOUCHED-MISMATCH` | FAIL | 內容檔缺；雜湊或 `touched` 與重算不符（R41） |
| `events.research` | `RESEARCH-MISSING`、`RESEARCH-MULTIPLE`、`RESEARCH-ORDER` | FAIL | 有 `prop` 的運轉無研究事件；同運轉多筆；`seq` 不在 `run.open` 與第一筆 `prop` 之間（R42） |
| `events.research` | `SRC-UNKNOWN` | FAIL | `research.scan` 的 `sources[].id` 不在來源表（R42） |
| `events.research` | `SOURCES-SHA-MISMATCH` | FAIL | `sources_sha256` 與該事件 `t` 之前最近一次提交的來源表雜湊不符，或之前無提交（R42） |
| `events.research` | `SOURCES-HISTORY-NOT-ESTABLISHED` | NE nonblocking | git 不可用而無法比對提交歷史（R42） |
| `events.research` | `QUOTE-VERIFIER-NOT-ESTABLISHED` | PASS（warn finding；項目狀態不變） | 存在 `helmsman` 免掃（R42） |
| `research.sources` | `SRC-FILE-FORMAT`、`SRC-SCHEMA`、`SRC-FIELD-MISSING`、`SRC-ID-FORMAT`、`SRC-ID-DUP`、`SRC-ORDER`、`SRC-KIND`、`SRC-RETIRED-TYPE`、`SRC-URL-SCHEME`、`SRC-URL-USERINFO`、`SRC-URL-HOST` | FAIL | 來源表驗證失敗（R43） |
| 六個 `events.*` 與 `research.sources` | `CARRIER-NOT-ESTABLISHED` | NE nonblocking | 事件帳本或來源表檔不存在（R36） |
| 六個 `events.*` 與 `research.sources`、`row.markers` | `SOURCE-UNAVAILABLE` | NE blocking | 該項所需 `params.json` 鍵無效，或需驗證而來源表讀不到（R36、R42、R44） |
| `row.provenance` | `RESEARCHER-NOT-EXTERNAL`、`RESEARCHER-NO-SRC` | FAIL | `回報者=研究者` 而無 `外部衍生=是`；或無 `src`（R44） |
| `row.markers` | `SRC-UNKNOWN` | FAIL | 列的 `src` 不在來源表（R44） |
| `row.markers` | `REOPEN-CANDIDATE` | PASS（warn） | 新列與已結列的證據路徑有交集（R45） |
| `params.keys` | `PARAM-MISSING`、`PARAM-TYPE`、`PARAM-RANGE` | FAIL | 必備鍵由 23 增為 28（R46） |

**〈寫入動詞拒收碼表（rc 1；R28 (b)）〉**（供 AT 以「碼集合」斷言；階段一＝輸入類、鎖內收到即回；階段二＝政策與狀態類、全部收集）

| 動詞 | 碼 |
|------|-----|
| 全部寫入動詞 | `LOCK-BUSY`、`LEDGER-TORN`、`EVENT-BYTES-OVER` |
| `run-open` | `COORD-NONE`、`GIT-UNAVAILABLE` |
| `run-close` | `RUN-NOT-OPEN` |
| `attr`、`attr-confirm`、`attr-reject` | `OBS-NOT-FOUND`、`COORD-NONE`、`ATTR-NONE-TEXT`、`ROOT-CAUSE-FORMAT`、`REOPENS-NOT-FOUND`、`REOPENS-NOT-CLOSED`、`ATT-NOT-FOUND`、`ALREADY-SETTLED`、`CONFIRMER-IS-PROPOSER` |
| `prop-new`、`prop-revise`（階段一） | `PATCH-EMPTY`、`PATCH-BINARY`、`PATCH-PARSE`、`PATCH-PATH-MISMATCH`、`GIT-UNAVAILABLE`、`BODY-SKELETON`、`BODY-FIELD-MISSING`、`BODY-FIELD-VALUE` |
| `prop-new`、`prop-revise`（階段二） | `RUN-NOT-OPEN`、`RESEARCH-MISSING`、`SUSPENDED`、`BUDGET-PROPOSALS`、`DUPLICATE-TYPE`、`SOURCE-UNRESOLVED`、`NO-INTERNAL-SOURCE`、`REVIEWER-IS-PROPOSER`、`HANDOFF-CHANNEL-MISSING`、`HANDOFF-CHANNEL-UNEXPECTED`、`TOUCH-RATIO`、`NEW-ENTRIES`、`ARCHIVE-ENTRIES`、`M-FIELD-MISSING`、`MEMORY-DIR-MISSING`、`R-NOT-PROPOSED`、`CARD-TOO-TALL`、`CARD-LINE-TOO-WIDE`、`PROP-FILE-EXISTS` |
| `prop-revise`（專屬） | `PROP-NOT-FOUND`、`TRANSITION-ILLEGAL`、`REV-LIMIT` |
| `research --skip` | `RUN-NOT-OPEN`、`RESEARCH-ALREADY` |
| `research --fetch` | `RUN-NOT-OPEN`、`RESEARCH-ALREADY`、`SOURCES-ABSENT`、`SRC-*`（R43 各碼）、`FETCH-MAX`、`SOURCES-UNCOMMITTED`、`ZERO-SUCCESS`、`SOURCES-CHANGED` |

| US ID | User Story | AC ID | AC（Given／When／Then；括號內為 PRD 全名與所指動詞或檔案） |
|-------|------------|-------|-----------------------------------------------------------|
| US-101 | 作為主控，我要在有編號的運轉內記錄歸因與復發連結，並讓零產出的運轉被記成「無事件」，以便同一症狀的再現能被結構化追蹤 | AC-110-3 | （PRD AC-SI-10-3；`run-open`／`run-close`，R47）Given 任何啟動事件 When 迴圈開始 Then 先記 `run.open`（RUN 號、trigger、證據座標、`head_sha`），結束記 `run.close`；無 `run.open` 的提案不受理 |
| US-101 | 同上 | AC-103-2 | （PRD AC-SI-03-2 的 `run-close` 半；R47）Given 某運轉內沒有任何 `prop` 事件 When `run-close` Then 記 `no_event`（「無事件」而非「通過」）；有提案者記各 PROP 的折疊狀態 |
| US-101 | 同上 | AC-105-1 | （PRD AC-SI-05-1；`attr`，R48）Given 一個觀察或觀察群 When 歸因 Then 產出（種類，座標）清單；`NONE` 必須寫明「無法歸因」、不得猜測補位 |
| US-101 | 同上 | AC-105-2 | （PRD AC-SI-05-2；R48 (d)）Given 歸因輸出 When 檢視欄位 Then 不含自評分數或信心數值；歸因不修改被指向的任何檔 |
| US-101 | 同上 | AC-106-1 | （PRD AC-SI-06-1；`attr`／`attr-confirm`，R48）Given 歸因完成 When 指派根因鍵 Then 鍵（`<面>/<機制>`）由歸因者提出、審查者（≠歸因者）以 `attr.confirm` 確認；鍵被事後更改的次數記入資訊欄 |
| US-101 | 同上 | AC-106-2 | （PRD AC-SI-06-2；`attr --type link`、`attr-confirm`、`attr-reject`，R45、R48）Given 新列疑似為已結列所防症狀的再現 When 立案當下 Then `check` 列出同證據路徑的已結列供確認；經確認才算再現、審查者可駁回（附一句理由），未確認者只印數量 |
| US-102 | 作為提案者（子代理）與主控，我要提案經 CLI 受理且前置檢查機械化，以便越界、重複、無來源或無研究事件的提案在入帳當下就被拒或轉交 | AC-102-1 | （PRD AC-SI-02-1 的 `prop-new` 機械半；R53 (f)）Given 提案的 `sources` When `prop-new` Then 任何類別都至少須有 1 個內部來源，外部衍生列（含研究者候選）不得單獨充當證據；P0 以標記詞彙與 SOP 條文代位 |
| US-102 | 同上 | AC-107-1 | （PRD AC-SI-07-1；R52）Given 歸因目標或 patch 觸及的任一路徑落在不可進化面 When 產生提案 Then `route=handoff:<通道>`、卡面標「僅轉交，本迴圈不套用」、迴圈對該目標零寫入 |
| US-102 | 同上 | AC-107-2 | （PRD AC-SI-07-2；SOP 歸因者節）Given 轉交目標屬守衛面且無暴露證據 When 轉交 Then 一律登記為理論洞（P4）、不立案修復；流程型，以 SOP 條文代位 |
| US-102 | 同上 | AC-107-3 | （PRD AC-SI-07-3；`prop-new`／`prop-revise`，R51、R52）Given 一筆 PROP 的 `rN.patch` When 受理 Then 解析全部路徑逐一以 `realpath`＋`normcase`＋`casefold` 比對不可進化面與合法根，任一命中（含別名形態、逃逸）⇒ 整張 PROP `route=handoff`；`touched` 自 patch 導出、`target` 為路徑集合、與 digest 一併綁定 |
| US-102 | 同上 | AC-108-1 | （PRD AC-SI-08-1；R49、R55）Given 任一來源的改進 When 登記 Then 一律是 `PROP-SI-NNN`、初始 `proposed`；R 類 `target`＝既有管線產出的草案座標；產生者不寫正式面（流程型約束，`git status`／HEAD 對照偵測） |
| US-102 | 同上 | AC-108-2 | （PRD AC-SI-08-2；R34、R49 (c)）Given PROP When 狀態轉移 Then 僅允許 §5.1.2 狀態機所列轉移；CLI 前置檢查拒收跳級並印 OBS 草稿列 |
| US-102 | 同上 | AC-108-3 | （PRD AC-SI-08-3；R52 (d)）Given R 類提案 When 入庫 Then `trust_level: proposed` 且不得阻塞 SCG（新增的規則候選檔須含 `trust_level: proposed`；既有 active 規則本體觸及即轉交） |
| US-102 | 同上 | AC-109-1 | （PRD AC-SI-09-1；R50）Given 提案生成 When 取輸入 Then 只能是帳本列、證據座標與抽象化摘要（帶結果標籤與適用範圍），不得以原始軌跡全文充當條目；以 `rN.md` 形態判準近似，流程面由 SOP 代位 |
| US-102 | 同上 | AC-109-2 | （PRD AC-SI-09-2；R54）Given 提案 diff When 受理檢查 Then 觸及既有內容比例 ≤ `max_touch_ratio`、新增條目 ≤ `max_new_entries`；歸檔型（逐字搬移、零內容修改）改受 `max_archive_entries_per_card` |
| US-102 | 同上 | AC-109-3 | （PRD AC-SI-09-3；R50 (d)）Given M 類條目 When 入提案 Then 必含結果標籤、適用範圍、來源 OBS、退役條件四欄，缺欄不受理 |
| US-102 | 同上 | AC-110-1 | （PRD AC-SI-10-1 加 AC-SI-17-2 的 M 半；R53）Given 一次運轉 When 產生提案 Then 提案數 ≤ `max_proposals_per_run`、同型者不重複產生、SUSPENDED 期間與無研究事件的運轉拒收 |
| US-102 | 同上 | AC-110-2 | （PRD AC-SI-10-2；R50 (c)、R65 (c)）Given 提案者或審查者 When 執行 Then 不得再派提案者／審查者（流程型，SOP 代位）；每提案宣告預算（`budget` 欄必備，缺即拒收） |
| US-102 | 同上 | AC-111-1 | （PRD AC-SI-11-1；R52 (f)）Given 提案類別 When 受理 Then 僅 M／P／R／D 四類（及其退役）進採納流程；改變評估器或迴圈自身者（`rN.patch` 路徑落在 (iii)(iv)）標 `evaluator-change`／`loop-self` 並轉交 |
| US-102 | 同上 | AC-111-2 | （PRD AC-SI-11-2；SOP 歸因者節）Given 引擎演化提案內容涉及評估器 When 歸因者讀 dump／log 判讀 Then 標 `evaluator-change` 並記一筆 OBS、不得轉送沙盒；流程型，SOP 代位 |
| US-103 | 作為掌舵者，我要提案卡由確定性轉換產出、核心區 ≤12 行、可被反解析驗證，以便三句話判讀且卡與物件不會不一致 | AC-114-1 | （PRD AC-SI-14-1；`card`，R56）Given PROP When 產卡 Then 核心三句、diff 座標、digest、證據座標、預算、觸及檔案數與不在 `target` 內的路徑皆由 PROP 欄位與 `rN.patch` 確定性轉換，自由撰寫的摘要不取代 diff 本文 |
| US-103 | 同上 | AC-114-2 | （PRD AC-SI-14-2；R56 (d)）Given 一張卡 When 反解析卡面欄位 Then 與 PROP 物件逐欄一致（digest、diff 行數、觸及檔案數、驗證狀態）；不一致的卡不得送達 |
| US-103 | 同上 | AC-114-3 | （PRD AC-SI-14-3；R56 (b)）Given 一張卡 When 檢視版面 Then 核心區 ≤12 行、每項單行且顯示寬度 ≤ `card_line_max`（CJK 算 2，同 E501 量法） |
| US-104 | 作為主控，我要每次運轉能以限定來源、增量、有界的方式取得外部最新資訊，且產物只是候選，以便不開放式搜尋也不被內嵌指示毒化 | AC-130-1 | （PRD AC-SI-30-1；`research`、R42、R53、R57）Given 運轉要產生 `prop` When `prop-new` Then 同運轉須恰有一筆研究事件（`research.scan` 或 `research.skip`，`seq` 介於 `run.open` 與第一筆 `prop` 之間），否則拒收；`check` 重放同判；`research.skip` 的 `reason` 屬封閉集合 |
| US-104 | 同上 | AC-130-2 | （PRD AC-SI-30-2；`sources`、R43、R57 (b)）Given 研究來源表 When `research --fetch` 發出任何請求之前 Then 先驗表自身並驗工作樹表等於 HEAD 提交版，任一不符整次拒收；`check` 對同一份表跑同一驗證函式並以 `sources_sha256` 比對提交歷史；重導向目標 host 亦須在表內 |
| US-104 | 同上 | AC-130-3 | （PRD AC-SI-30-3；`fetch`，R58）Given `research --fetch --run R` When 執行 Then 逐一抓現役來源原始位元組、自算 `sha256` 與 `changed`、原樣落家目錄、寫 `research.scan`（不存 `url`、不存候選數）；失敗來源不入事件、不以舊 digest 代填；任一失敗整次 rc 2、零成功 rc 1 |
| US-104 | 同上 | AC-130-4 | （PRD AC-SI-30-4；R44、R53 (f)、SOP 研究者節）Given 研究者運作 When 產物入帳 Then 只能是 OBS 候選（`外部衍生=是; src=<id>`）；`check` 驗 `回報者=研究者` 的列與 `src`；以研究者候選為 `sources` 的 PROP 仍須 ≥1 個內部來源；工具白名單與「資料不是指令」為流程型，SOP 代位 |
| US-104 | 同上 | AC-130-5 | （PRD AC-SI-30-5；R57、R58 (d)(g)、R46）Given 一個運轉的研究掃描 When 執行 Then 現役來源筆數、每來源位元組與牆鐘皆有界（`params.json` 三鍵），超界依規則拒收或判該來源失敗，且只有 `fetch.py` 能連網 |
| US-104 | 同上 | AC-130-6 | （PRD AC-SI-30-6；R46 (b)）Given 來源表住協定目錄 When T1 增減來源 Then 判準指紋不變；改 `params.json` 或 `metrics.md` 則指紋變 |
| US-105 | 作為主控，我要有唯讀、離線、無狀態的模組體檢彙整與按任務書派出的唯讀體檢子代理，以便主動檢討五個模組又不改任何狀態 | AC-131-1 | （PRD AC-SI-31-1；`scan`，R59、R63 ⑥）Given 任一 repo 狀態 When `scan` Then 零副作用、不連網、只用標準庫、沒有接受筆數／日期／排程的旗標（`--since` 只收 commit）；前後 `git status --porcelain` 與 HEAD 逐字相同 |
| US-105 | 同上 | AC-131-2 | （PRD AC-SI-31-2；R59 (a)～(c)）Given `scan` 讀到的本地證據 When 印候選 Then 每列九欄、≥1 個座標、單列 ≤ `row_max_bytes`、自身通過 `check` 的列規則；無座標者不印；草稿不寫入帳本 |
| US-105 | 同上 | AC-131-3 | （PRD AC-SI-31-3；R59 (b)(e)）Given 每個證據來源 When 輸出 Then 各印一行（讀到 N 筆／量不到）；零候選印「無事件」、不得印成通過；量不到不併入零 |
| US-105 | 同上 | AC-131-4 | （PRD AC-SI-31-4；R59 (d)）Given 候選涉及的路徑 When 歸桶 Then 依序 SelfImproving→AutoClaude→AISDLC_SDD→AgentConsole→根層；不屬任何桶者歸「未分類」並計數 |
| US-105 | 同上 | AC-131-5 | （PRD AC-SI-31-5；SOP 歸因者節的體檢任務書範本，R65 (b)）Given 模組體檢任務書 When 派出子代理 Then 單一 Sonnet 唯讀子代理、依入口表逐模組檢、工具為 Read／Grep／Glob／PowerShell、文字交卷；邊界型 P＋D（前後對照），以 SOP 條文與前後對照夾具代位 |
| US-106 | 作為掌舵者與 QA，我要唯讀的 `status` 與 `export` 輸出可機器判讀、可重放、量不到不被印成零，以便狀態一眼可見且 Console 差分有穩定的對象 | AC-103-1 | （PRD AC-SI-03-1 的 `si status` 半；R60）Given 迴圈任一階段 When 檢視啟動條件 Then `status` 唯讀按需偵測 (b)～(d)、印待決 PROP、SUSPENDED 與冷卻、研究免掃分佈；(e) 容量事件於 P3 前印 NOT-EVALUABLE、不印成零；零事件印「無事件」 |
| US-106 | 同上 | AC-132-5 | （PRD AC-SI-32-5；`export`，R61）Given `export --json --kind K` When 執行 Then 唯讀、離線、單一 JSON（`schema_rev`、`kind`、`generated_at`、`head_sha`、`items`、游標、`ne`、`problems`）；`--kind` 為封閉集合，其餘 rc 3；與 `status`／`card`／`check` 共用同一組折疊與卡面函式 |
| US-106 | 同上 | AC-140-2 | （本檔自增，PRD 階段前綴形 `AC-P1-040-2`；PRD §9.2〈`export` 輸出〉與 AC-SI-32-5 的差分前提）Given 同一狀態 When 連續執行 `status`／`scan`／`card`／`export` Then 輸出除 `generated_at` 外逐字相同、UTF-8 位元組直寫（含 cp950 管線）、JSON 鍵序固定、`schema_rev` 起於 1 |
| US-107 | 作為 AutoClaude 維護者，我要「演化只提案不套用」成為可重跑的檢查而不是文件宣稱，以便生產路徑一旦出現建構點或演化重載生產者就轉紅 | AC-128-1 | （PRD AC-SI-28-1；鍵 B，R66）Given AutoClaude 原始碼 When 靜態可達性檢查（AST 普查，pytest；引擎碼零改動） Then 可證①②③④⑤五格，每格自帶對照組 |
| US-107 | 同上 | AC-128-2 | （PRD AC-SI-28-2；R66、D13）Given `require_evolution_signoff` 預設 False 而文件宣稱「只提案不套用」 When 對照 Then 文件改述為「Kernel 路徑只提案；預設放行，但無生產建構點、無演化重載生產者」，改述引註解字樣、不引行號，並由 ⑤ 釘住 |
| US-107 | 同上 | AC-128-3 | （PRD AC-SI-28-3；R66）Given 任何路徑出現生產建構 `PlaybookRunner` 或演化重載生產者 When AC-128-1 轉紅 Then 失敗訊息指向立即升為缺陷列並走 FR-SI-12 的人工閘 |
| US-108 | 作為維護者，我要根層模組落點有機械鎖，以便新模組不再散落且登記表與磁碟一致 | AC-134-1 | （PRD AC-SI-34-1；`tools/tests/test_root_module_layout.py`，R62）Given SSOT §3 登記表 When 解析 Then 每列所列 repo 內路徑在磁碟至少命中一檔；缺一或解析出 0 列＝紅 |
| US-108 | 同上 | AC-134-2 | （PRD AC-SI-34-2；R62 (c)）Given `tools/lib/` 的扁平檔 When 同前綴 ≥3 支且無套件目錄 Then 紅；存量以 shrink-only 名冊豁免，名冊內前綴已成套件須移除 |
| US-108 | 同上 | AC-134-3 | （PRD AC-SI-34-3；R62 (d)）Given `tools/lib/` 下含 `__init__.py` 的套件目錄 When 比對登記表 Then 每個套件名都出現在某一列「程式碼」欄，未登記＝紅 |
| US-108 | 同上 | AC-134-4 | （PRD AC-SI-34-4；R62 (e)）Given 含「模組落點表」字樣的 PRD When 掃描 Then 必含 SSOT 路徑，缺＝紅 |
| US-109 | 作為主控與 QA，我要事件帳本的重放、介面與純度可被機器驗證，且 P0 的成果不退化，以便 P1 的 `check` 綠成為驗收憑證 | AC-108-4 | （PRD AC-SI-08-4 ①～④；⑤ 屬 P2；R37～R40）Given 事件帳本 When `check` 重放 Then ① 每個 PROP 的事件序列皆為合法轉移；② 已提交的既有行不得被改寫或刪除；③ ID 唯一遞增、`t` 帶 offset、`kind` 在封閉詞彙；④ 事件數低於 `min_events` 印 NE；⑤ `dec` 引言回查印 warn 層級提示（P2 承接） |
| US-109 | 同上 | AC-140-1 | （本檔自增，PRD 階段前綴形 `AC-P1-040-1`；PRD §9.3 動詞表與 rc 通則，R27、R28）Given 13 個動詞 When 呼叫 Then 旗標、rc（0／1／2／3）、成功與拒收輸出文法依表；P2／P3 動詞與未知旗標一律 rc 3 |
| US-109 | 同上 | AC-141-1 | （本檔自增，`AC-P1-041-1`；PRD §9.2〈事件帳本規約〉〈事件欄位表〉，R30～R32）Given 任一寫入動詞 When 成功 Then 追加恰一行：UTF-8 無 BOM、LF、`ensure_ascii=False`、共通鍵齊備、`t` 帶 offset、`kind` 在詞彙、行長 ≤ `event_max_bytes`；配號依規則 |
| US-109 | 同上 | AC-141-2 | （本檔自增，`AC-P1-041-2`；PRD ADR-SI-10 的併發負控 ①～④，R33）Given 多個行程寫同一事件帳本 When 同時寫入 Then 鎖內「讀末行→配號→單次追加」使 `seq` 唯一連續、行行完整；陳舊鎖被回收、新鮮鎖逾時 fail-loud |
| US-109 | 同上 | AC-142-1 | （本檔自增，`AC-P1-042-1`；PRD §9.3 `check` 列的 P1 追加項，R36～R46）Given 任一 repo When `check` Then 21 項之後追加 7 項（共 28）、載體缺席一律 nonblocking NE、各追加項依規則判紅或判未判 |
| US-109 | 同上 | AC-142-2 | （本檔自增，`AC-P1-042-2`；PRD §9.3「21 項原樣保留」與 §9.7 #48，R36 (a)、R67）Given P0 的 42 個 AT When P1 落地 Then 前 21 項的 id、順序、語意、判定碼不變、P0 基線 repo 的 rc 與 overall 不變，P0 測試只經 R67 列出的站點同步後仍為 42 個全綠 |
| US-109 | 同上 | AC-143-1 | （本檔自增，`AC-P1-043-1`；PRD §9.4〈能力登記與純度判準〉、§9.7 #47，R63、R64）Given 套件內每個 `*.py` When 靜態與動態檢查 Then 逐檔符合所登類別（ro／rw／net）、唯讀動詞的 import 閉包 ⊆ ro、`check` 行程不載入寫入與網路碼、除 `fetch.py` 外無網路 import、常駐機制禁字樣零命中 |
| US-109 | 同上 | AC-144-1 | （本檔自增，`AC-P1-044-1`；PRD §9.2〈digest〉與 AC-SI-07-3，R41、R55）Given PROP When 落地 Then `rN.md`／`rN.patch` 與 `prop` 事件互相可驗（雜湊、`touched`），digest 綁 `target` 與 `touched` 且對 CRLF 等價、對欄位異動敏感 |
| US-109 | 同上 | AC-145-1 | （本檔自增，`AC-P1-045-1`；PRD §9.1 C5／C16、§9.7 #52，R43、R46；D12）Given 協定目錄 When 交付 Then `params.json` 含 28 鍵且排序、型別範圍合規，`research_sources.json` 初始表通過來源表驗證 |
| US-109 | 同上 | AC-145-2 | （本檔自增，`AC-P1-045-2`；PRD §9.1 C6，R65；D11）Given Operations SOP When 定稿 Then 四個角色節、研究者節、模組體檢任務書範本與研究事件條文齊備，P0 條文不退化 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。本檔除 §1 外沒有任何第一欄以 AC 起頭的表格；AT ID 於 §1 與 §2 的宣告位置之外，只出現在說明性文字與表格的非第一欄（不在第一欄形如 AC 的列的第三欄）。

**INVEST 自檢**：獨立（只依賴 git、PRD 與根 `CLAUDE.md` 的現況文字、既有 `tools/_stdio_utf8.py`、`lib.apply_lock`、`lib.sdd_latest`；鍵 B 只讀 AutoClaude 原始碼）、可協商（旗標名、拒收碼、`status`／`scan`／`export` 的元素形態、`rN.md` 欄位表、觸及比例與新增條目量法由本檔定義並列入 §7.1，掌舵者可裁決）、有價值（P1 出口 (a)～(h) 除真實端到端與真實體檢外皆可由 AT 判定，且每條「不能做」都標邊界型 M／D／P）、可估計（16 支新套件模組＋入口增子命令＋6 個新測試檔＋1 個共用夾具模組＋鍵 B 1 個測試檔＋3 份文件；PRD §9.1〈C4 套件檔案表〉估新 16 檔共約 3,700 斷言行）、小（P1 範圍已由 PRD 劃定，P2 的 `decide`／沙盒／驗證與 P3 的量測退役不在本檔）、可測（AT 數見 §1 覆蓋率統計；絕大多數用 tmp 目錄的合成 repo 與合成事件帳本，研究抓取用本機 loopback HTTP 夾具，皆不碰真帳本、不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P1-1 | 純度與能力登記：R63（逐檔類別掃描、唯讀動詞閉包 ⊆ ro、`check` 行程不載入寫入與網路碼、除 `fetch.py` 外無網路 import、零網路動態驗證）與 R64（常駐機制禁字樣）；`check` 的動態純度（P0 R8）涵蓋追加項 | §2 的 AC-143-1 AT；SCG-4 程式碼審查 |
| NFR-P1-2 | 效能（皆 AT 只做不等式、不列入 AT 者另述）：合成 repo 上單次 `check`、`status`、`scan`、`export`、`card` 小於 5 秒；單次寫入動詞（不含 `research --fetch`）小於 5 秒；併發 AT（8 行程×10 筆）整體小於 60 秒；單次 `research --fetch`（loopback 夾具、≤3 來源）小於 10 秒；每個新測試檔在 CI 上小於 300 秒（超過時依持有面拆檔、不降低覆蓋；P0 的單檔 42 個 AT 約 40 秒為量級參考）；真 repo 上單次 `check`（28 項）小於 30 秒（沿 NFR-P0-2） | 合成情境以 AT 內的牆鐘上界斷言（寬鬆上界，避免 CI 抖動）；真 repo 以 SCG-4 實跑量測（3 次取最大值），不列 AT |
| NFR-P1-3 | 跨平台（根 `CLAUDE.md` 鐵律三）：路徑一律 `Path`／`os.path`、git 路徑 POSIX 斜線；不用 `sys.platform` 分支；家目錄解析用 `AUTOSDD_SI_DIR` 或 `Path.home()`；鎖只用獨佔建檔（不用 `msvcrt.locking`／`fcntl.flock`）；輸出位元組直寫、UTF-8、LF；Windows 保留裝置名、尾端點與空白、`:`、大小寫不敏感比對（R51、R52）；測試字面值不含磁碟機代號開頭的路徑；macOS 未實跑項在報告標「未驗」（NFR-SI-06-5） | 根層 `tools/tests/test_platform_neutral_paths.py` 相關鎖；SCG-4 審查；AT-107-3-E-2 等別名形態案例 |
| NFR-P1-4 | 根層護欄相容：測試與工具不新增 skip、skipTest、skipIf、xfail（git 缺席視為環境壞、直接失敗）；所有 `open`、`read_text`、`write_text` 帶 `encoding="utf-8"`（根層鎖 `TestTextIoDeclaresEncoding`）；測試以 `unittest.TestCase` 撰寫並可被 `python -m pytest` 與 `python -m unittest discover -s tools/tests` 兩種方式收集；不得另寫 stdout 重設站點；本機 HTTP 夾具只綁 loopback、測試結束必關；子行程併發夾具必回收 | 根層 unittest 閘門；SCG-4 |
| NFR-P1-5 | LOC 分級：`tools/lib/selfimproving/*.py` 每檔 `guardrail_lib` 400 斷言行（計價只算斷言行）、入口 `tools/selfimproving.py` `guardrail_cli` 750；現查 `python AutoClaude/tools/check_loc_budget.py --json`（`root_tools_tiers`）rc 0；PRD §9.1 估單檔 ≤340，逼近上限時先依職責拆檔、不調 tier | SCG-4 實跑 |
| NFR-P1-6 | 靜態檢查：`ruff check` 對新增與改動的每個 `.py` 0 錯（規則集以 repo 根的 ruff 設定現查）；鍵 B 的新測試檔同 | SCG-4 實跑 |
| NFR-P1-7 | 測試 hermetic：全部 AT 只用 tmp 目錄內的合成 repo、合成帳本與以 `AUTOSDD_SI_DIR` 指向 tmp 的家目錄；唯讀存取真 repo 的 `params.json`、PRD、SOP、SSOT、`tools/` 原始碼、`.claude/settings.json`、`AutoClaude/` 原始碼與 `CLAUDE.md`；不寫真帳本、真事件帳本、真 `SelfImproving_Proposals/`；不連外網（本機 loopback 夾具除外）；不得在測試原始碼或本檔寫出不存在於真帳本與真缺陷帳本的字面 `OBS-SI-<數字>` 或 `DEF-<數字>` 編號（合成編號於執行期組出，先例 `tools/tests/test_defect_id_reference_integrity.py` 的 `_syn()`；R18 (a) 的 `git grep` 會掃整個 repo 的非忽略檔） | 實跑檢核 V2（真帳本 `ref.obs`）與既有鎖 `test_defect_id_reference_integrity.py` |
| NFR-P1-8 | 範圍守衛：實作者只新增或修改 §5.6 允許集合內的檔案；不改 `.claude/**`、不改任何凍結檔（PRD、研究方法 SOP、P0 TCS）、不改 `autoclaude/` 引擎原始碼；重釘根層棘輪（檔案數下限、LOC、E501；現查 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `repin_growth_problems()`、`tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS` 與 `tree_floor_problems()`、`tools/tests/test_platform_neutral_paths.py` 的 `_tmpdir_scan_roots` 檔數雙邊帶）與 SSOT 登記列同步由主控收尾，實作者不碰鎖檔 | 實跑檢核 V1（`git diff --name-only`） |
| NFR-P1-9 | CI 與棘輪：P1 新增 `tools/` 估 3,700 斷言行與 6 個新測試檔，遠超護欄層單輪淨額上限，須由主控以具名一次性例外重釘（`_REPIN_APPROVED_ROUND_OVERAGE`，名冊上限的上修須可見）；compat-ci 兩支 `paths` 已含 `tools/lib/selfimproving/**` 與 `tools/selfimproving.py`，新測試檔在 `tools/tests/` 不必另加；若新測試檔唯讀消費新的根層資料檔（`research_sources.json`、SSOT），以 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 現查是否須列入 `paths`，同一個 commit 收齊；鍵 B 的新測試檔在 `AutoClaude/tests/contract/`，走 autoclaude-ci，並使 ONBOARDING §7 基線數字與 `_tmpdir_scan_roots` 的 `AutoClaude/tests` 檔數雙邊帶移動，須現查重釘 | 實跑檢核 V5；根層全套 unittest |
| NFR-P1-10 | **Developer 交卷前閘門清單（缺一即不得交卷；輸出逐字貼入交卷）**：(1) 本檔 AT 與 P0 的 42 個 AT 全綠（`python -m pytest tools/tests/test_selfimproving_check.py tools/tests/test_selfimproving_events.py tools/tests/test_selfimproving_props.py tools/tests/test_selfimproving_research_scan.py tools/tests/test_selfimproving_export_status.py tools/tests/test_selfimproving_capability.py tools/tests/test_root_module_layout.py -q -p no:xdist -o addopts=`；鍵 B 另在 `AutoClaude/` 下跑 `python -m pytest tests/contract/test_evolution_propose_only.py -q -n 0`；加 `-n 0` 的原因：本機 PG 在場時，AutoClaude 的 conftest 對全域 addopts 的 `-n auto` 回 rc=4〔PG 在場但未用 `--dist loadgroup`〕；`-p no:xdist` 不能與 `-n` 並用，實測 `unrecognized arguments`）；(2) `python tools/selfimproving.py check` 對真 repo rc 0（28 項）；(3) `ruff check` 對新增與改動的每個 `.py` 為 0 錯；(4) `python AutoClaude/tools/check_loc_budget.py --json` rc 0；(5) `python tools/sync_onboarding_baselines.py --check-snapshot` rc 0；(6) 官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）rc 0；(7) 護欄層重釘儀式做到 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` 的淨差額為 +0（由主控收尾）；(8) 文件引用子專案檔案一律寫 monorepo 根起算路徑（`TestR81GhostPathClaims` 會判相對路徑為幽靈）；(9) 大檔（>100KB）編修先備自 pristine 的冪等重建腳本、交卷即退役；(10) 交卷含「流程摩擦」節（根 `CLAUDE.md` 與 SOP 擷取者節）；(11) **新增 `tools/tests/` 檔會撞的根層鎖，逐項過**（OBS-SI-161：七支新檔一次撞 23 筆紅；本清單是規格來源，各鎖的判準以其所在檔為準，修法一律是「重釘為現查值」或「改正成因」、不得壓制）：① `tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS`（`tools/tests` 與 `AutoClaude/tests` 的檔數掃描下限）；② `tools/tests/test_platform_neutral_paths.py` 的腐化上界（`_tmpdir_scan_roots` 檔數雙邊帶，`tools/tests` 與 `tools/lib`）；③ E501 存量棘輪（`tools/tests/test_subprocess_encoding_hygiene.py` 的 `test_e501_debt_only_shrinks`；ruff 量**東亞寬度**、CJK 算 2；找新長行：`ruff check --isolated --select E501 --line-length 100 --output-format concise <檔>`）；④ 同檔的編碼衛生掃描下限；⑤ POSIX 絕對路徑字面（`tools/tests/test_platform_neutral_paths.py` 的 `TestNoPosixAbsPathLiteralInAsserts`：測試字面值不得含 `/etc/…` 之類整串 POSIX 絕對路徑，需要時於執行期拆開組出）；⑥ 死信引用（repo 內路徑形態的字面須指向存在的檔，合成路徑拆開寫，先例 `TESTS_A`；文件側 `TestR81GhostPathClaims`）；⑦ NTFS 錨站點登記（`tools/tests/test_windows_forbidden_filename_parity.py`：新增處理 NTFS 保留名、尾端點的原始碼站點須登記）；⑧ `unittest discover` 靜態守門（`tools/tests/test_schedule_capability_parity.py`：**跨檔基底鏈不解析，自夾具檔匯入的測試基底類別，其名稱須含 `TestCase`**，OBS-SI-162）；⑨ `tools/run_root_unittests.py` 的 `MIN_TESTS` 下限；(12) **測試 class 與夾具 def 的 docstring 指名受測模組**（`tools/lib/selfimproving/<x>.py`）：分桶棘輪（`tools/lib/guard_bucket_policy.py`）以頂層 class／def 為單位，chunk 文字只參照 `docs/`、`ONBOARDING.md` 這類文件 token 就整塊算 prose（shrink-only）；docstring 指名受測模組即歸 mixed（正確分類，不是繞過）；交卷前現查 `python tools/probe/guard_layer_bucket_census.py --grain chunk`，看 `prose` 桶的 `exclusive`（OBS-SI-164：未指名時 1,546 行落 prose）；僅守文件字面的 class（例：SOP 條文判準）歸 prose 是正確分類，其增量由主控於重釘儀式併記；(13) **`--print-guard-lines` 住 `tools/tests/test_adr_xplat001_c1c2_lock.py`、不是分桶探針的旗標**：取護欄層淨額與逐檔表一律 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；對 `tools/probe/guard_layer_bucket_census.py` 傳它回 rc=2（unrecognized arguments；OBS-SI-160）；該探針的 `--jsonl` 是**輸出路徑**（會覆寫該檔）、不是輸入檔 | SCG-4 實跑檢核 V2、V3、V4、V5（讀 rc 先存變數再讀，不接管線） |
| NFR-P1-11 | 失效可偵測（NFR-SI-09）：量不到＝NOT-EVALUABLE、不得印成零或綠——`status` 的 (e) 與 `friction_reconcile`、`scan` 的來源行與「無事件（K 個來源量不到）」、`export` 的 `ne`、`research` 失敗來源（不入 `sources[]`、不以舊 digest 代填、印 OBS 草稿列）、`check` 載體缺席的 NE | §2 對應各 AT |

**追溯矩陣**：F-002 ← PRD FR-SI-05～11、14、28、30、31、34（§5.2）、FR-SI-32 的 AC-SI-32-5、AC-SI-02-1／03-1／03-2 的 P1 機械半，與 §9.1 的 C3、C4、C6、C7、C13、C14、C16、C17、C18 根層半、C19、§9.2、§9.3、§9.4、§9.5 的 ADR-SI-07／10／11、§9.6 P1 列、§8.1 P1 出口 (a)～(h)；US-101～US-109 → AC-103-1～AC-145-2（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；兩個 FSM 鍵〔`monorepo-si-p1-propose`、`autoclaude-evolution-propose-only`〕共用本表）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD 全文（§8.1 P1、§9.6 P1）；Stage-1 凍結＝掌舵者預先核准、主控代為執行 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-002（本檔 FRD-lite）；FR-SI-05～11、14、28、30、31、34 與 AC-SI-32-5 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-0／NFR 已量化定義 | NFR-P1-1～11（本檔）；最近依據 PRD NFR-SI-01、02、06、07、08、09 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-101～US-109（本檔 INVEST 自檢） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-0／利害關係人已確認簽核 | PRD 附錄 C.2（掌舵者授權代決，#10～#16；T1 修訂授權座標 sid ee6af537-7091-4f0e-842c-0d091085f77b line 13；Stage-1 預先核准凍結） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC 到 AT 映射）；根層 RTM 檔另依 SSOT §2 落 `docs/06_quality/RTM-SelfImproving-P1-<日期>.md` | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | 不適用（功能級增量；設計載於 PRD §9）；最近依據 PRD §9.0～§9.6 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-1／API Spec 草稿完成（所有端點清單） | 不適用（P1 無 HTTP 端點；Console 端點屬 P1b）；命令列介面即契約：本檔 R27～R28 與 PRD §9.3 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-1／資料模型設計完成 | PRD §5.1.2、§9.2（事件帳本、事件欄位表、`research_sources.json`、`export` 輸出、digest）；本檔 R30～R35、R43、R50、R55、R61 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-P1-1～11 對應 R63（純度）、R33（併發）、R57／R58（有界與逾時）、R36 (c)（NE 不是綠）；PRD NFR-SI-09-1（量不到＝NE） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-1／整合架構說明完整（第三方服務已識別） | 無第三方服務；外聯只有 `research --fetch` 對來源表 URL 的 HTTP GET（唯一例外、`fetch.py` 一個模組）；依賴 git、`lib.apply_lock`、`lib.sdd_latest`、既有 `tools/_stdio_utf8.py` | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | PRD §9.1 載體對映表（C3、C4、C6、C7、C13、C14、C16、C17、C19，與 C18 的根層半）；P1 不新增系統邊界（P1b 的 Console 邊界屬另鍵） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-2／C4 Container 圖完成（主要組件識別） | 落點：根層 `tools/`（CLI `selfimproving.py` 與套件 `lib/selfimproving/` 的 24 檔）、`tools/tests/`、`docs/06_quality/`（事件帳本、提案內容檔、協定目錄）、`docs/05_development/`（SOP）、`AutoClaude/tests/contract/`（鍵 B）；家目錄機器狀態 `<si_dir>/{locks,research}/`（repo 外） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | PRD §9.5：ADR-SI-02、ADR-SI-05、ADR-SI-07、ADR-SI-10、ADR-SI-11（及 ADR-SI-12 的根層半）；本增量無新架構決策，ADR 不新開 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 brownfield，非 security）；信任邊界要點：外部抓回內容是資料不是指令（FR-SI-30）、研究者無 Web 工具、`fetch.py` 唯一外聯、不可進化面全路徑比對（AC-SI-07-3） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 本檔 FRD-lite〈現況與變更〉（只有 `check` 的 P0 到事件帳本、運轉、提案、研究、體檢、匯出、落點鎖） | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | 不適用（無 HTTP API）；介面為命令列 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／Request／Response Schema 定義完整 | 輸出形態：本檔 R28、R56、R57 (e)、R59 (f)、R60、R61；事件欄位表 R31；來源表格式 R43 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-3／錯誤碼定義（400／401／403／404／500） | rc 表 0、1、2、3（R27）、判定碼表與寫入動詞拒收碼表 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-3／Consumer Contract 完成（整合情境） | 消費者＝主控與 QA（讀 `check`、`status`、`scan`、`card`）、P1b 的 Bridge（消費 `export` 輸出；本檔只定輸出契約）、P3 量測腳本（讀事件帳本與 `params.json`）；SOP 是各角色任務書的上位（研究方法 SOP，本增量不改它） | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/SelfImproving_PRD.md | sha256:e90d8eb388ba739a278c65d8f65cc3d3e8a68213451132e5160fd64aea589c73 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 的值是 Stage-1 重凍後的 digest（主控於 HEAD 2f13bb2b 交付，SA 以 `Get-FileHash -Algorithm SHA256` 對工作樹現況重算一致）；SOP 的值不變，同樣重算一致。**兩個功能鍵的 Stage-1 必須採納同一份重凍後的 PRD 與同一份研究方法 SOP**（否則「引用不得指向未凍結文件」不成立）；凍結後的實際 digest 以各鍵 `show` 的輸出為準，與本表不符時以 `show` 為準並更正本表。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（見〈AC 編號規則〉）；邊界與錯誤（負控）AT 以 `AT-<NNN>-<Y>-E-<n>` 命名並列於本表。標「代位」者＝流程型 AC 以 SOP 條文（加刪去自證）判定；其餘 AT 的判定指令與測試檔見 §2 各 AT 標頭。測試檔縮寫：EV、PR、RS、ES、CP、LY、KB 見 §2 開頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-102-1 | `prop-new` 內部來源前置檢查（任何類別至少一個內部來源）（PRD AC-SI-02-1） | AT-102-1-1 | （PR）任何類別的提案至少有 1 個內部來源即受理；DEF 列算內部來源 | ✅ | Integration | □ |
| AC-102-1 | `prop-new` 內部來源前置檢查（任何類別至少一個內部來源）（PRD AC-SI-02-1） | AT-102-1-E-1 | （PR）外部衍生列（含研究者候選）不得單獨充當任何類別提案的證據；來源須可解析 | ✅ | Integration | □ |
| AC-103-1 | `status` 啟動事件偵測與狀態摘要（PRD AC-SI-03-1） | AT-103-1-1 | （ES）唯讀按需偵測啟動事件 (b)(c)(d)、印待決 PROP、運轉、冷卻、免掃分佈與根因鍵更改次數；(e) 印 NOT-EVALUABLE | ✅ | Integration | □ |
| AC-103-1 | `status` 啟動事件偵測與狀態摘要（PRD AC-SI-03-1） | AT-103-1-E-1 | （ES）零事件印無事件而不印通過；起算點量不到；SUSPENDED 折疊與恢復；冷卻解除；pending 窗；事件帳本缺席與壞行 | ✅ | Integration | □ |
| AC-103-1 | `status` 啟動事件偵測與狀態摘要（PRD AC-SI-03-1） | AT-103-1-E-2 | （ES）SUSPENDED 的連續判準：兩窗只有一壞不暫停、連續兩壞才暫停、`pending` 窗不打斷連續 | ✅ | Integration | □ |
| AC-103-1 | `status` 啟動事件偵測與狀態摘要（PRD AC-SI-03-1） | AT-103-1-E-3 | （ES）`pending_props` 含 `verified`；偵測窗以最近 `run.close` 為界、已處理者不重複偵測；`friction_reconcile` 兩種 NOT-EVALUABLE 原因 | ✅ | Integration | □ |
| AC-103-2 | `run-close` 無事件記錄（PRD AC-SI-03-2） | AT-103-2-1 | （EV）零 `prop` 的運轉記 `no_event`、有 `prop` 的運轉記 `outcomes`（各 PROP 折疊狀態） | ✅ | Integration | □ |
| AC-103-2 | `run-close` 無事件記錄（PRD AC-SI-03-2） | AT-103-2-E-1 | （EV）未開、已關、查無的運轉不得關閉；同一運轉不可二次關閉 | ✅ | Integration | □ |
| AC-105-1 | 歸因清單（種類、座標；`NONE` 須寫明無法歸因）（PRD AC-SI-05-1） | AT-105-1-1 | （EV）`attr --type root` 七種種類皆受理；事件鍵恰為欄位表；`NONE` 須以「無法歸因」起頭 | ✅ | Integration | □ |
| AC-105-1 | 歸因清單（種類、座標；`NONE` 須寫明無法歸因）（PRD AC-SI-05-1） | AT-105-1-E-1 | （EV）種類不在集合 rc 3；`NONE` 缺「無法歸因」、座標不可定位、根因鍵格式錯、OBS 不存在各 rc 1 並印對應碼；零寫入 | ✅ | Unit | □ |
| AC-105-2 | 歸因無自評分數且不改檔（PRD AC-SI-05-2） | AT-105-2-1 | （EV）歸因事件不含自評分數；歸因只動事件帳本，不改任何被指向的檔 | ✅ | Integration | □ |
| AC-105-2 | 歸因無自評分數且不改檔（PRD AC-SI-05-2） | AT-105-2-E-1 | （EV）自評旗標即未知旗標 rc 3；手寫夾帶自評鍵的 attr 事件被 `check` 判 EVENT-KEY-UNKNOWN | ✅ | Unit | □ |
| AC-106-1 | 根因鍵與確認者不得等於提出者（PRD AC-SI-06-1） | AT-106-1-1 | （EV）確認者≠提出者、確認落事件；根因鍵事後更改的次數入資訊欄 | ✅ | Integration | □ |
| AC-106-1 | 根因鍵與確認者不得等於提出者（PRD AC-SI-06-1） | AT-106-1-E-1 | （EV）自己確認、重複落定、查無歸因皆拒收；手寫的自我確認被 `check` 判 CONFIRMER-IS-PROPOSER | ✅ | Integration | □ |
| AC-106-2 | 復發連結、候選提示、確認與駁回（PRD AC-SI-06-2） | AT-106-2-1 | （EV）`attr --type link` 受理已結列；確認與駁回（附一句理由）；未確認者只計入數量 | ✅ | Integration | □ |
| AC-106-2 | 復發連結、候選提示、確認與駁回（PRD AC-SI-06-2） | AT-106-2-E-1 | （EV）連結對象須是已結列；`attr-reject` 須附合規的一句理由 | ✅ | Integration | □ |
| AC-106-2 | 復發連結、候選提示、確認與駁回（PRD AC-SI-06-2） | AT-106-2-E-2 | （EV）立案當下 `check` 對新列印復發候選提示（warn 等級：不改狀態、不影響 rc），誤報面（已提交、已有 reopens、處置非 open、路徑無交集）零提示 | ✅ | Integration | □ |
| AC-107-1 | 不可進化面的歸因出口（整張轉交）（PRD AC-SI-07-1） | AT-107-1-1 | （PR）patch 觸及不可進化面者整張轉交：`route=handoff:<通道>`、卡面標僅轉交、迴圈對目標零寫入 | ✅ | Integration | □ |
| AC-107-1 | 不可進化面的歸因出口（整張轉交）（PRD AC-SI-07-1） | AT-107-1-E-1 | （PR）提案者不得自填 loop；導出為 handoff 而缺通道、導出為 loop 而給通道皆拒收 | ✅ | Unit | □ |
| AC-107-2 | 守衛面無暴露證據登記為理論洞（流程型）（PRD AC-SI-07-2） | AT-107-2-1 | （代位）（EV）守衛面轉交且無暴露證據者一律登記為理論洞（P4）、不立案修復——SOP 歸因者節的條文 | ✅ | Unit | □ |
| AC-107-2 | 守衛面無暴露證據登記為理論洞（流程型）（PRD AC-SI-07-2） | AT-107-2-E-1 | （代位）（EV）理論洞條文判準的自證 | ✅ | Unit | □ |
| AC-107-3 | `touched` 全路徑導出與不可進化面、合法根比對（PRD AC-SI-07-3） | AT-107-3-1 | （PR）`touched` 自 patch 的全部路徑標頭導出（聯集、排序、去重）；`git apply --numstat` 超集檢查通過 | ✅ | Unit | □ |
| AC-107-3 | `touched` 全路徑導出與不可進化面、合法根比對（PRD AC-SI-07-3） | AT-107-3-E-1 | （PR）patch 的任一路徑命中不可進化面（含大小寫變體、純改名來源端）即整張 handoff | ✅ | Unit | □ |
| AC-107-3 | `touched` 全路徑導出與不可進化面、合法根比對（PRD AC-SI-07-3） | AT-107-3-E-2 | （PR）路徑別名形態（逃逸、絕對、磁碟機代號、資料流、尾端點與空白、保留裝置名、控制字元、反斜線）整張轉交；git 看見而解析器漏掉者拒收；`--target` 別名形態 rc 3 | ✅ | Unit | □ |
| AC-107-3 | `touched` 全路徑導出與不可進化面、合法根比對（PRD AC-SI-07-3） | AT-107-3-E-3 | （PR）`R-*.yaml` 內容條件式、LATEST 注入與解析失敗 fail-closed、規格本體路徑與 SPEC-PATCH 草案例外、`cls` 自動標記、M 類合法根 | ✅ | Integration | □ |
| AC-107-3 | `touched` 全路徑導出與不可進化面、合法根比對（PRD AC-SI-07-3） | AT-107-3-E-4 | （PR）`git apply --numstat` 自身失敗（損毀 hunk、context-diff）⇒ 拒收 `PATCH-PARSE`，不放行 | ✅ | Unit | □ |
| AC-108-1 | PROP 登記（只產 proposed、不寫正式面）（PRD AC-SI-08-1） | AT-108-1-1 | （PR）任何來源的改進一律登記為 `PROP-SI-NNN`、初始 `proposed`；R 類 `target` 為草案座標；產生者不寫正式面 | ✅ | Integration | □ |
| AC-108-1 | PROP 登記（只產 proposed、不寫正式面）（PRD AC-SI-08-1） | AT-108-1-E-1 | （PR）輸入類錯誤（階段一）收到即回；旗標缺漏 rc 3；審查者不得等於提案者；拒收零殘留 | ✅ | Unit | □ |
| AC-108-2 | 狀態轉移合法性（跳級被拒）（PRD AC-SI-08-2） | AT-108-2-1 | （PR）`prop-revise` 只在 returned 狀態受理；沿用前一版的類別、動作、目標與來源；不計入運轉預算 | ✅ | Integration | □ |
| AC-108-2 | 狀態轉移合法性（跳級被拒）（PRD AC-SI-08-2） | AT-108-2-E-1 | （PR）跳級被拒並印 OBS 草稿列；修訂超限、查無 PROP 的拒收碼 | ✅ | Integration | □ |
| AC-108-3 | R 類 `trust_level: proposed`（PRD AC-SI-08-3） | AT-108-3-1 | （PR）R 類新增規則候選檔含 `trust_level: proposed` 即受理，且不碰 FSM 狀態檔 | ✅ | Integration | □ |
| AC-108-3 | R 類 `trust_level: proposed`（PRD AC-SI-08-3） | AT-108-3-E-1 | （PR）R 類新增檔缺 `trust_level: proposed` 拒收；觸及既有 active 規則本體者整張轉交而非拒收 | ✅ | Integration | □ |
| AC-108-4 | `check` 事件重放（①～④；⑤ 以 warn 層級提示未建）（PRD AC-SI-08-4） | AT-108-4-1 | （EV）事件序列的合法轉移與跳級、孤兒的判定 | ✅ | Integration | □ |
| AC-108-4 | `check` 事件重放（①～④；⑤ 以 warn 層級提示未建）（PRD AC-SI-08-4） | AT-108-4-E-1 | （EV）已提交的事件行不得被改寫或刪除；追加與 CRLF 轉換放行；無歷史與 git 不可用的處置 | ✅ | Integration | □ |
| AC-108-4 | `check` 事件重放（①～④；⑤ 以 warn 層級提示未建）（PRD AC-SI-08-4） | AT-108-4-E-2 | （EV）結構判準（ID 唯一遞增、`t` 帶 offset、`kind` 在封閉詞彙）、反空轉下限、`dec` 引言回查印 warn 層級提示 | ✅ | Unit | □ |
| AC-108-4 | `check` 事件重放（①～④；⑤ 以 warn 層級提示未建）（PRD AC-SI-08-4） | AT-108-4-E-3 | （EV）型別怪異的手寫事件（欄位值為陣列）恰報 `EVENT-TYPE`，`check` 其餘項目照常產出、不拋例外 | ✅ | Unit | □ |
| AC-108-4 | `check` 事件重放（①～④；⑤ 以 warn 層級提示未建）（PRD AC-SI-08-4） | AT-108-4-E-4 | （EV）事件欄位值域的 check 層負控：`note` 120／121、`http_status` 199～300、`research.skip` 的 `by`、`sid` 正規形、事件行位元組 L 與 L－1 | ✅ | Unit | □ |
| AC-108-4 | `check` 事件重放（①～④；⑤ 以 warn 層級提示未建）（PRD AC-SI-08-4） | AT-108-4-E-5 | （EV）引言回查未建的 warn 提示邊界：單一 `dec`、單一 `helmsman` 免掃即印，零筆不印；warn 不改狀態與 rc | ✅ | Unit | □ |
| AC-109-1 | 提案輸入限定（形態判準加流程型條文）（PRD AC-SI-09-1） | AT-109-1-1 | （PR）提案本文的形態判準：五節骨架、欄位表、必備欄與結果標籤三值 | ✅ | Integration | □ |
| AC-109-1 | 提案輸入限定（形態判準加流程型條文）（PRD AC-SI-09-1） | AT-109-1-2 | （代位）（PR）輸入限於抽象化摘要、不得以原始軌跡全文充當條目——SOP 提案者節的條文（機械判準只能近似，語意由實跑檢核對照 PRD） | ✅ | Unit | □ |
| AC-109-1 | 提案輸入限定（形態判準加流程型條文）（PRD AC-SI-09-1） | AT-109-1-E-1 | （PR）骨架缺節、必備欄缺或空、結果標籤值域外各拒收；非 UTF-8 本文 rc 3 | ✅ | Unit | □ |
| AC-109-2 | 增量 delta：觸及比例、新增條目、歸檔型豁免（PRD AC-SI-09-2） | AT-109-2-1 | （PR）觸及比例與新增條目的邊界（恰等於放行、超過拒收），多檔比例加總，條目的三種樣式與新檔計數 | ✅ | Integration | □ |
| AC-109-2 | 增量 delta：觸及比例、新增條目、歸檔型豁免（PRD AC-SI-09-2） | AT-109-2-E-1 | （PR）M 類歸檔型（逐字搬移、零內容修改）豁免觸及比例、改受歸檔上限；任一行被改寫即回到比例判準 | ✅ | Integration | □ |
| AC-109-3 | M 類四欄（PRD AC-SI-09-3） | AT-109-3-1 | （PR）M 類四欄齊備即受理；`preimage` 為被刪行的逐檔 sha256；非 M 類沒有 `preimage` | ✅ | Integration | □ |
| AC-109-3 | M 類四欄（PRD AC-SI-09-3） | AT-109-3-E-1 | （PR）M 類四欄缺或空、`source_obs` 不在 `--source` 內或非 OBS 號各拒收；`result_label` 值域外走 BODY-FIELD-VALUE | ✅ | Unit | □ |
| AC-110-1 | 運轉預算、同型去重與停機前置檢查（PRD AC-SI-10-1） | AT-110-1-1 | （PR）運轉預算與同型去重：邊界、跨運轉、活躍狀態與根因鍵的相交規則 | ✅ | Integration | □ |
| AC-110-1 | 運轉預算、同型去重與停機前置檢查（PRD AC-SI-10-1） | AT-110-1-E-1 | （PR）未開運轉、無研究事件、SUSPENDED 期間拒收；多碼一併回報；恢復後放行 | ✅ | Integration | □ |
| AC-110-2 | 零遞迴（流程型）與預算宣告（PRD AC-SI-10-2） | AT-110-2-1 | （PR）每提案宣告預算，預算文字原樣進卡面第 7 行 | ✅ | Integration | □ |
| AC-110-2 | 零遞迴（流程型）與預算宣告（PRD AC-SI-10-2） | AT-110-2-2 | （代位）（PR）提案者與審查者不得再派提案者與審查者（零遞迴）——SOP 提案者節的條文 | ✅ | Unit | □ |
| AC-110-2 | 零遞迴（流程型）與預算宣告（PRD AC-SI-10-2） | AT-110-2-E-1 | （PR）`budget` 欄缺或空即拒收 | ✅ | Unit | □ |
| AC-110-3 | 運轉識別 `run-open`／`run-close`（PRD AC-SI-10-3） | AT-110-3-1 | （EV）`run-open` 五種 trigger 皆受理、配 RUN 號、記 head_sha，可多個運轉並存 | ✅ | Integration | □ |
| AC-110-3 | 運轉識別 `run-open`／`run-close`（PRD AC-SI-10-3） | AT-110-3-E-1 | （EV）`run-open` 的用法錯誤 rc 3、狀態錯誤 rc 1；無 `run.open` 的提案與研究不受理；拒收零殘留且草稿列自驗 | ✅ | Integration | □ |
| AC-111-1 | 類別白名單與評估器、迴圈自身轉交（PRD AC-SI-11-1） | AT-111-1-1 | （PR）M、P、R、D 四類受理；評估器群組與迴圈自身群組的標記取自 PRD 標籤位置 | ✅ | Integration | □ |
| AC-111-1 | 類別白名單與評估器、迴圈自身轉交（PRD AC-SI-11-1） | AT-111-1-E-1 | （PR）評估器變更與迴圈自身類別不進採納流程（整張轉交）；類別旗標值域外 rc 3；patch 觸及的群組覆寫自填類別 | ✅ | Integration | □ |
| AC-111-2 | 引擎演化提案涉及評估器（流程型）（PRD AC-SI-11-2） | AT-111-2-1 | （代位）（EV）引擎演化提案涉及評估器者標 `evaluator-change`、記一筆 OBS、不得轉送沙盒——SOP 歸因者節的條文 | ✅ | Unit | □ |
| AC-111-2 | 引擎演化提案涉及評估器（流程型）（PRD AC-SI-11-2） | AT-111-2-E-1 | （代位）（EV）evaluator-change 條文判準的自證 | ✅ | Unit | □ |
| AC-114-1 | 卡面確定性轉換（PRD AC-SI-14-1） | AT-114-1-1 | （PR）卡面由 PROP 欄位與 `rN.patch` 確定性轉換：逐行格式、轉交變體、驗證狀態與冷卻狀態的顯示、連續兩次輸出逐字相同 | ✅ | Integration | □ |
| AC-114-1 | 卡面確定性轉換（PRD AC-SI-14-1） | AT-114-1-2 | （PR）`M` 類卡面（正控）：七行、觸及比例印 `n/a`、核心區不超限；`--json` 的 `parsed` 與文字形態一致 | ✅ | Integration | □ |
| AC-114-1 | 卡面確定性轉換（PRD AC-SI-14-1） | AT-114-1-E-1 | （PR）提案者自由撰寫的摘要不取代 diff 本文；查無 PROP 與內容檔缺失 rc 3 | ✅ | Integration | □ |
| AC-114-2 | 卡面反解析一致（PRD AC-SI-14-2） | AT-114-2-1 | （PR）卡面反解析與由事件、patch、本文重算的值逐欄一致；`--json` 形態 | ✅ | Integration | □ |
| AC-114-2 | 卡面反解析一致（PRD AC-SI-14-2） | AT-114-2-E-1 | （PR）內容檔於 `prop-new` 之後被改動，卡不得送達（rc 3、stdout 空、印 CARD-INCONSISTENT 與不符欄名） | ✅ | Integration | □ |
| AC-114-3 | 卡面版面（核心區 12 行、顯示寬度）（PRD AC-SI-14-3） | AT-114-3-1 | （PR）核心區 12 行與單行顯示寬度 100（CJK 算 2）的邊界放行；`prop-new` 與 `card` 用同一渲染函式 | ✅ | Unit | □ |
| AC-114-3 | 卡面版面（核心區 12 行、顯示寬度）（PRD AC-SI-14-3） | AT-114-3-E-1 | （PR）額外路徑 8 筆、第 2 行顯示寬度 101 與 CJK 字數少但寬度超界皆拒收 | ✅ | Integration | □ |
| AC-128-1 | 演化只提案不套用的五格檢查（PRD AC-SI-28-1） | AT-128-1-1 | （KB）鍵 B：真 AutoClaude 原始碼上五格皆綠，且每格的掃描器自帶對照組證明看得見生產站點 | ✅ | Contract | □ |
| AC-128-1 | 演化只提案不套用的五格檢查（PRD AC-SI-28-1） | AT-128-1-E-1 | （KB）引用格缺函式、apply_evolution 呼叫點多或少、execution/ 外的呼叫與 import 皆判紅（合成樹） | ✅ | Contract | □ |
| AC-128-1 | 演化只提案不套用的五格檢查（PRD AC-SI-28-1） | AT-128-1-E-2 | （KB）plugins 與 core 內出現演化重載生產者即判紅；排除檔豁免；掃描器在 execution 內看得見生產者 | ✅ | Contract | □ |
| AC-128-1 | 演化只提案不套用的五格檢查（PRD AC-SI-28-1） | AT-128-1-E-3 | （KB）require_evolution_signoff 的讀取點多出一處即判紅；Store 語境不算讀取 | ✅ | Contract | □ |
| AC-128-1 | 演化只提案不套用的五格檢查（PRD AC-SI-28-1） | AT-128-1-E-4 | （KB）文件宣稱釘住：缺字樣、帶 `main.py:<行號>` 形態、main.py 缺註解字樣皆判紅 | ✅ | Contract | □ |
| AC-128-2 | 文件改述與預設值零退化（PRD AC-SI-28-2） | AT-128-2-1 | （KB）`require_evolution_signoff` 預設值仍為 False；文件演化敘述含四個改述片段且該行不超過 800 個碼位 | ✅ | Contract | □ |
| AC-128-2 | 文件改述與預設值零退化（PRD AC-SI-28-2） | AT-128-2-E-1 | （KB）預設值被改成 True、任一改述片段被刪、行長超過 800 皆判紅 | ✅ | Contract | □ |
| AC-128-2 | 文件改述與預設值零退化（PRD AC-SI-28-2） | AT-128-2-E-2 | （KB）判準常數 `REWRITE_FRAGMENTS` 的獨立釘選：與 R66 的四個片段相等，改任一元素即紅 | ✅ | Contract | □ |
| AC-128-3 | 轉紅時升為缺陷列並走人工閘（訊息）（PRD AC-SI-28-3） | AT-128-3-1 | （KB）①～④ 任一格轉紅時，失敗訊息指向立即升為缺陷列並走 FR-SI-12 的人工閘 | ✅ | Contract | □ |
| AC-128-3 | 轉紅時升為缺陷列並走人工閘（訊息）（PRD AC-SI-28-3） | AT-128-3-E-1 | （KB）訊息判準自證：缺任一片段的訊息被判不合格；格 ⑤ 的訊息不要求含該三片段 | ✅ | Contract | □ |
| AC-130-1 | 研究事件必有（PRD AC-SI-30-1） | AT-130-1-1 | （RS）同運轉產生 `prop` 前須恰有一筆研究事件，序位介於 `run.open` 與第一筆 `prop` 之間；`prop-new` 拒收與 `check` 重放同判 | ✅ | Integration | □ |
| AC-130-1 | 研究事件必有（PRD AC-SI-30-1） | AT-130-1-E-1 | （RS）`research --skip` 的 reason 封閉集合與附帶旗標；同運轉第二筆研究事件拒收；helmsman 免掃印 warn 層級的引言回查未建提示 | ✅ | Integration | □ |
| AC-130-2 | 來源白名單與預檢（PRD AC-SI-30-2） | AT-130-2-1 | （RS）已提交的合規來源表通過預檢；請求只發給表內現役來源；表內 host 的重導向放行；`check` 的表驗證與 sources_sha256 比對皆 PASS | ✅ | Integration | □ |
| AC-130-2 | 來源白名單與預檢（PRD AC-SI-30-2） | AT-130-2-E-1 | （RS）來源表驗證碼逐一命中；預檢失敗整次拒收（零請求、零事件）；表與 HEAD 提交版不同即拒收 | ✅ | Integration | □ |
| AC-130-2 | 來源白名單與預檢（PRD AC-SI-30-2） | AT-130-2-E-2 | （RS）`check` 以 sources_sha256 比對提交歷史、來源 id 須在表內（retired 仍認得）、git 不可用的處置、未提交的表不算歷史 | ✅ | Integration | □ |
| AC-130-2 | 來源白名單與預檢（PRD AC-SI-30-2） | AT-130-2-E-3 | （RS）重導向把關：表外 host 與連接埠、非 http 與 https 的 scheme、https 降 http 與 http 升 https（scheme 不得改變；函式層用顯式同埠 URL）、第 6 跳皆拒；表內重導向至多 5 跳放行 | ✅ | Integration | □ |
| AC-130-2 | 來源白名單與預檢（PRD AC-SI-30-2） | AT-130-2-E-4 | （RS）來源表提交時間與事件 `t` 同一秒放行、事件早一秒判 `SOURCES-SHA-MISMATCH`、晚一秒放行 | ✅ | Integration | □ |
| AC-130-3 | 增量 digest 與抓取（PRD AC-SI-30-3） | AT-130-3-1 | （RS）抓原始位元組、自算 sha256 與 changed 三態、原樣落家目錄、事件不存 url、請求形態固定且逐一發出 | ✅ | Integration | □ |
| AC-130-3 | 增量 digest 與抓取（PRD AC-SI-30-3） | AT-130-3-E-1 | （RS）失敗矩陣：逾時、非 2xx、超位元組（邊界）、非文字、缺 Content-Type、壓縮編碼、連線被拒；失敗來源不入事件 | ✅ | Integration | □ |
| AC-130-3 | 增量 digest 與抓取（PRD AC-SI-30-3） | AT-130-3-E-2 | （RS）零來源成功 rc 1 不寫事件；事件行超長 rc 1 但來源檔留作快取；零成功後仍可改記 offline 免掃 | ✅ | Integration | □ |
| AC-130-3 | 增量 digest 與抓取（PRD AC-SI-30-3） | AT-130-3-E-3 | （RS）抓取在寫入鎖之外進行、鎖內重驗：抓取期間他人的改動使本次拒收且不追加 | ✅ | Integration | □ |
| AC-130-3 | 增量 digest 與抓取（PRD AC-SI-30-3） | AT-130-3-E-4 | （RS）全部來源失敗與現役為 0 筆皆以 `ZERO-SUCCESS` 拒收（rc 1、不寫事件；零現役時預檢零請求） | ✅ | Integration | □ |
| AC-130-3 | 增量 digest 與抓取（PRD AC-SI-30-3） | AT-130-3-E-5 | （RS）Content-Type 白名單逐一釘住：`text/*` 與五個 `application/*` 放行，其餘判 `non-text` | ✅ | Integration | □ |
| AC-130-4 | 產物只為候選（PRD AC-SI-30-4） | AT-130-4-1 | （RS）研究者候選列帶外部衍生與 src 且 src 在表內即合規；以候選加一個內部來源為 sources 的 PROP 受理 | ✅ | Integration | □ |
| AC-130-4 | 產物只為候選（PRD AC-SI-30-4） | AT-130-4-2 | （代位）（RS）研究者的工具白名單與抓回內容是資料不是指令——SOP 研究者節的條文 | ✅ | Unit | □ |
| AC-130-4 | 產物只為候選（PRD AC-SI-30-4） | AT-130-4-E-1 | （RS）研究者候選的入帳鏈：缺外部衍生、缺 src、src 不在表內各被 check 判出；候選單獨充當 PROP 來源被拒 | ✅ | Integration | □ |
| AC-130-5 | 預算與純度（PRD AC-SI-30-5） | AT-130-5-1 | （RS）預算三界的邊界放行（現役恰 `research_fetch_max` 筆、位元組恰 `research_bytes_max`、牆鐘在上限內）；三界取自 params；網路模組 import 只在 `fetch.py` | ✅ | Integration | □ |
| AC-130-5 | 預算與純度（PRD AC-SI-30-5） | AT-130-5-E-1 | （RS）預算超界：現役多 1 筆整次拒收、位元組多 1 判失敗、牆鐘超過判失敗；retired 不計；三鍵缺失 rc 3 | ✅ | Integration | □ |
| AC-130-5 | 預算與純度（PRD AC-SI-30-5） | AT-130-5-E-2 | （RS）牆鐘上限對慢滴回應成立（每 0.5 秒 1 位元組）、送完標頭後停滯亦在逾時上限附近以 `timeout` 返回 | ✅ | Integration | □ |
| AC-130-6 | 來源表變更不改指紋（PRD AC-SI-30-6） | AT-130-6-1 | （RS）改來源表不改判準指紋 | ✅ | Unit | □ |
| AC-130-6 | 來源表變更不改指紋（PRD AC-SI-30-6） | AT-130-6-E-1 | （RS）改 `params.json` 或 `metrics.md` 指紋變；排除只涵蓋一個檔名 | ✅ | Unit | □ |
| AC-131-1 | `scan` 唯讀離線（PRD AC-SI-31-1） | AT-131-1-1 | （RS）`scan` 唯讀、離線、無狀態：前後 `git status --porcelain` 與 HEAD 相同、不連網、子行程只有環境淨化的 git、不受 GIT_DIR 污染 | ✅ | Integration | □ |
| AC-131-1 | `scan` 唯讀離線（PRD AC-SI-31-1） | AT-131-1-E-1 | （RS）筆數、日期、排程類旗標一律是未知旗標；`--since` 只收 commit，其餘寫法 rc 3 | ✅ | Unit | □ |
| AC-131-2 | 候選列有座標且自驗（PRD AC-SI-31-2） | AT-131-2-1 | （RS）候選列為九欄、至少一個座標、不超過列位元組上限，附加到帳本副本後 `check` 對這些列零 finding；草稿不寫入帳本 | ✅ | Integration | □ |
| AC-131-2 | 候選列有座標且自驗（PRD AC-SI-31-2） | AT-131-2-E-1 | （RS）過長的路徑清單被縮短以守住列上限；缺陷帳本欄位不全時該來源量不到、不產生候選 | ✅ | Integration | □ |
| AC-131-2 | 候選列有座標且自驗（PRD AC-SI-31-2） | AT-131-2-E-2 | （RS）缺陷帳本的狀態分類與表格解析對既有解析器差分一致：同一批狀態字串與同一份合成帳本，兩邊輸出逐筆相同 | ✅ | Unit | □ |
| AC-131-2 | 候選列有座標且自驗（PRD AC-SI-31-2） | AT-131-2-E-3 | （RS）`scan` 起算時刻的 commit 時間邊界：committer 時間等於起算時刻者不計入窗、晚一秒者計入 | ✅ | Integration | □ |
| AC-131-3 | 零候選＝無事件、量不到不併入（PRD AC-SI-31-3） | AT-131-3-1 | （RS）每個來源各印一行；零候選整體印無事件，不印成通過 | ✅ | Integration | □ |
| AC-131-3 | 零候選＝無事件、量不到不併入（PRD AC-SI-31-3） | AT-131-3-E-1 | （RS）量不到的來源不併入零：整體改印無事件加量不到個數；有候選時仍列出量不到者 | ✅ | Integration | □ |
| AC-131-4 | 模組歸桶（PRD AC-SI-31-4） | AT-131-4-1 | （RS）模組歸桶依序為 SelfImproving、AutoClaude、AISDLC_SDD、AgentConsole、根層 | ✅ | Unit | □ |
| AC-131-4 | 模組歸桶（PRD AC-SI-31-4） | AT-131-4-E-1 | （RS）非 repo 相對形態歸未分類並計數、不丟棄；觸及多個桶的 commit 各歸一次 | ✅ | Integration | □ |
| AC-131-5 | 體檢子代理（流程型加前後對照）（PRD AC-SI-31-5） | AT-131-5-1 | （代位）（RS）模組體檢任務書範本含五桶、工具白名單、唯讀、文字交卷等片段，且 PRD 入口表第 2 欄的每個反引號片段都在範本內 | ✅ | Unit | □ |
| AC-131-5 | 體檢子代理（流程型加前後對照）（PRD AC-SI-31-5） | AT-131-5-E-1 | （代位）（RS）範本判準自證；體檢前後對照夾具能偵測寫入，並誠實標出看不見被忽略檔的寫入 | ✅ | Integration | □ |
| AC-132-5 | `export` 動詞（PRD AC-SI-32-5） | AT-132-5-1 | （ES）`export --json` 五個 kind 的頂層鍵序與 items 形態；唯讀離線；`schema_rev` 起於 1 | ✅ | Contract | □ |
| AC-132-5 | `export` 動詞（PRD AC-SI-32-5） | AT-132-5-E-1 | （ES）用法錯誤 rc 3；游標與截斷；`--id` 找不到回空；事件帳本缺席的 ne 標示 | ✅ | Unit | □ |
| AC-132-5 | `export` 動詞（PRD AC-SI-32-5） | AT-132-5-E-2 | （ES）與 `status`、`card` 差分一致；不讀不印家目錄；壞列與壞行入 problems；被竄改的內容檔使 card 為 null 並標 ne | ✅ | Integration | □ |
| AC-132-5 | `export` 動詞（PRD AC-SI-32-5） | AT-132-5-E-3 | （ES）`truncated` 的邊界：筆數恰等於 `--limit` 不截斷、多一筆才截斷 | ✅ | Unit | □ |
| AC-134-1 | 登記表與磁碟一致（PRD AC-SI-34-1） | AT-134-1-1 | （LY）真登記表可解析出至少一列，每個 repo 內路徑在磁碟至少命中一檔；兩種檔名承繼寫法與不判的片段 | ✅ | Unit | □ |
| AC-134-1 | 登記表與磁碟一致（PRD AC-SI-34-1） | AT-134-1-E-1 | （LY）登記路徑在磁碟缺一即紅並印列名與路徑；解析出 0 列或缺登記表節即紅 | ✅ | Unit | □ |
| AC-134-2 | 前綴散落（PRD AC-SI-34-2） | AT-134-2-1 | （LY）前綴散落鎖的合規情形：真樹以現查名冊為綠；同前綴不足 3 支、已成套件、名冊豁免皆綠 | ✅ | Unit | □ |
| AC-134-2 | 前綴散落（PRD AC-SI-34-2） | AT-134-2-E-1 | （LY）前綴散落鎖的紅燈情形：同前綴 3 支無套件、名冊內前綴已成套件、新前綴達 3 支、名冊與天花板不一致 | ✅ | Unit | □ |
| AC-134-3 | 套件須登記（PRD AC-SI-34-3） | AT-134-3-1 | （LY）真樹每個含 `__init__.py` 的套件目錄都登記在某一列的程式碼欄 | ✅ | Unit | □ |
| AC-134-3 | 套件須登記（PRD AC-SI-34-3） | AT-134-3-E-1 | （LY）未登記的套件即紅 | ✅ | Unit | □ |
| AC-134-3 | 套件須登記（PRD AC-SI-34-3） | AT-134-3-E-2 | （LY）套件登記以程式碼欄的反引號片段為準：片段之外的散文字串不算登記 | ✅ | Unit | □ |
| AC-134-4 | 新模組 PRD 須引落點 SSOT（PRD AC-SI-34-4） | AT-134-4-1 | （LY）含「模組落點表」字樣的 PRD 必含 SSOT 路徑；真 PRD 為綠；不含字樣的 PRD 不判 | ✅ | Unit | □ |
| AC-134-4 | 新模組 PRD 須引落點 SSOT（PRD AC-SI-34-4） | AT-134-4-E-1 | （LY）含「模組落點表」字樣而缺 SSOT 路徑的 PRD 即紅 | ✅ | Unit | □ |
| AC-140-1 | CLI 介面、動詞集合與 rc 表（本檔自增） | AT-140-1-1 | （EV）13 個動詞皆可呼叫，求助輸出、`--repo` 檢查與 rc 0 路徑 | ✅ | Integration | □ |
| AC-140-1 | CLI 介面、動詞集合與 rc 表（本檔自增） | AT-140-1-E-1 | （EV）P2 與 P3 的動詞、`card --issue`、未知旗標與未知動詞一律 rc 3；拒收輸出文法（文字與 JSON）與 OBS 草稿列內容 | ✅ | Unit | □ |
| AC-140-1 | CLI 介面、動詞集合與 rc 表（本檔自增） | AT-140-1-E-2 | （EV）帳本含型別怪異事件時，讀取與寫入動詞不拋未捕捉例外，rc 與輸出依既有規則；怪異事件不被折疊 | ✅ | Integration | □ |
| AC-140-1 | CLI 介面、動詞集合與 rc 表（本檔自增） | AT-140-1-E-3 | （EV）OBS 草稿列的症狀至多顯示 5 個碼，超過尾接 `…等 k 項`；恰好 5 個不加尾綴 | ✅ | Unit | □ |
| AC-140-2 | 輸出 schema 穩定（本檔自增） | AT-140-2-1 | （ES）`status`、`scan`、`card`、`export` 連續兩次輸出除 generated_at 外逐字相同；UTF-8、LF、無 BOM、JSON 鍵序固定 | ✅ | Contract | □ |
| AC-140-2 | 輸出 schema 穩定（本檔自增） | AT-140-2-E-1 | （ES）輸出不得含不穩定來源：雜湊種子、cwd、時區、絕對路徑、行程號 | ✅ | Integration | □ |
| AC-140-2 | 輸出 schema 穩定（本檔自增） | AT-140-2-E-2 | （ES）含中文的 `--json` 輸出為 UTF-8 原字、沒有 u 跳脫序列（`PYTHONIOENCODING=cp950` 管線下亦然） | ✅ | Integration | □ |
| AC-141-1 | 事件帳本形態與配號（本檔自增） | AT-141-1-1 | （EV）各寫入動詞成功時恰追加一行，行形態與鍵序合規 | ✅ | Contract | □ |
| AC-141-1 | 事件帳本形態與配號（本檔自增） | AT-141-1-E-1 | （EV）`seq` 與各家族編號的配法、行長上限邊界、撕裂帳本拒寫 | ✅ | Integration | □ |
| AC-141-1 | 事件帳本形態與配號（本檔自增） | AT-141-1-E-2 | （EV）PROP 配號的 OBS 帳本部分在寫入鎖內讀取：取鎖之前才出現的 PROP 引用不被漏算 | ✅ | Integration | □ |
| AC-141-2 | 寫入鎖與併發（本檔自增） | AT-141-2-1 | （EV）鎖內重讀末行與配號：確定性交錯（無鎖對照組撞同一 seq）與多行程壓力 | ✅ | Integration | □ |
| AC-141-2 | 寫入鎖與併發（本檔自增） | AT-141-2-E-1 | （EV）陳舊鎖被回收；新鮮鎖逾時 fail-loud 並印持鎖者；家目錄不可寫拒寫 | ✅ | Integration | □ |
| AC-141-2 | 寫入鎖與併發（本檔自增） | AT-141-2-E-2 | （EV）鎖檔名為事件帳本 realpath 的 sha256 前 16 位 hex 加 `.lock`；持鎖期間存在、寫入完成後已釋放 | ✅ | Integration | □ |
| AC-141-2 | 寫入鎖與併發（本檔自增） | AT-141-2-E-3 | （EV）家目錄與其 locks、research 皆存在但寫不進（可寫性探測失敗）⇒ 寫入動詞 rc 3 `HOME-UNWRITABLE` | ✅ | Integration | □ |
| AC-142-1 | `check` 的 P1 追加項（本檔自增） | AT-142-1-1 | （EV）`check` 在 21 項之後追加 7 項（共 28），載體缺席一律 nonblocking NE，合法事件帳本使追加項轉 PASS | ✅ | Integration | □ |
| AC-142-1 | `check` 的 P1 追加項（本檔自增） | AT-142-1-E-1 | （EV）`events.prop_files` 抓出內容檔缺失與雜湊不符；`research.sources` 接上來源表驗證；CRLF 的正規化規則（`.md` 換行不計、`.patch` 位元組原樣） | ✅ | Integration | □ |
| AC-142-1 | `check` 的 P1 追加項（本檔自增） | AT-142-1-E-2 | （EV）標記鍵詞彙加 `src`；`回報者=研究者` 的列須帶外部衍生與 `src`；`src` 須在來源表內（含 retired） | ✅ | Unit | □ |
| AC-142-2 | P0 不退化與測試同步（本檔自增） | AT-142-2-1 | （EV）P0 基線 repo 在 P1 下：前 21 項的 id、順序、狀態、碼與 P0 相同，rc 與 overall 不變 | ✅ | Integration | □ |
| AC-142-2 | P0 不退化與測試同步（本檔自增） | AT-142-2-E-1 | （EV）P0 的紅燈碼在 P1 下不變；非 git 目錄的未判型態與 rc 表不變；P0 測試檔的 R67 同步有靜態證據 | ✅ | Integration | □ |
| AC-143-1 | 純度與能力登記（本檔自增） | AT-143-1-1 | （CP）真套件逐檔符合所登能力類別；唯讀動詞的 import 閉包只含 ro 檔；網路 import 只在 fetch.py；入口模組層級只 import ro | ✅ | Unit | □ |
| AC-143-1 | 純度與能力登記（本檔自增） | AT-143-1-E-1 | （CP）判準自證：合成套件樹的各種違規各被判出，合法合成樹為對照 | ✅ | Unit | □ |
| AC-143-1 | 純度與能力登記（本檔自增） | AT-143-1-E-2 | （CP）動態純度：唯讀動詞行程不載入寫入與網路模組；全部動詞零網路；常駐機制禁字樣零命中且樣本自證 | ✅ | Integration | □ |
| AC-144-1 | PROP 內容檔與 digest（本檔自增） | AT-144-1-1 | （PR）PROP 內容檔的位元組與雜湊、digest 的獨立重算、同輸入同 digest | ✅ | Integration | □ |
| AC-144-1 | PROP 內容檔與 digest（本檔自增） | AT-144-1-E-1 | （PR）digest 對 `target` 與本文欄位異動敏感；內容檔撞名拒收；追加失敗不留孤兒檔 | ✅ | Integration | □ |
| AC-145-1 | 協定目錄（params 新鍵、來源表初值）（本檔自增） | AT-145-1-1 | （EV）真 `params.json` 含五個新鍵且合規；真來源表通過來源表驗證 | ✅ | Unit | □ |
| AC-145-1 | 協定目錄（params 新鍵、來源表初值）（本檔自增） | AT-145-1-E-1 | （EV）五個新鍵逐鍵缺失、型別錯、範圍錯各被判出；取不到鍵的動詞 rc 3 | ✅ | Unit | □ |
| AC-145-2 | SOP 定稿（本檔自增） | AT-145-2-1 | （代位）（EV）Operations SOP 定稿：四個角色節仍含「P1 定稿」並有實質內容、研究者節、研究事件條文與各代位條文的必備片段齊備 | ✅ | Unit | □ |
| AC-145-2 | SOP 定稿（本檔自增） | AT-145-2-E-1 | （代位）（EV）SOP 判準的自證：每個必備片段刪去的副本須判不合格，同行條件被拆行、標題被改名也判不合格 | ✅ | Unit | □ |
| AC-145-2 | SOP 定稿（本檔自增） | AT-145-2-E-2 | （EV）SOP 判準常數的獨立釘選：`SAME_LINE_GROUPS` 與 `RESEARCH_EVENT_LINES` 和 R65 相等，改任一元素即紅 | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: 54（PRD 的 44 個加本檔自增的 10 個）
- 已映射 AT 數: 148（正控 58 個、負控〔E 類〕90 個；每個 AC 至少一個正控與一個負控）
- 各測試檔的 AT 數: EV 44；PR 38；RS 33；ES 11；CP 3；LY 9；KB 10
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_110_3_1]`；E 類為 `[AT_OK_110_3_E_1]`），本節 Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，單引號字元用文字描述。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑判定指令（cwd 為 monorepo 根；鍵 B 的 AT 例外，cwd 為 `AutoClaude/`，見各 AT），**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。兩種等價的判定指令：
> - `python -m pytest tools/tests/<檔名> -k <AT 底線形> -q`
> - `python -m unittest discover -s tools/tests -p <檔名> -k <AT 底線形>`
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-110-3-E-1` 的底線形是 `AT_110_3_E_1`）；每個 AT 的測試函式名稱須含其底線形（例 `test_AT_110_3_E_1_usage_and_state_errors`）。每個 AC 內的 AT 序號不超過 9，使 `-k` 的子字串比對不會誤收其他 AT。
>
> **判定指令的形態（勘誤一）**：§2 原有 126 個 AT 的判定指令只帶 `-k <AT 底線形> -q`（根層實測可單跑）；SCG-4 一審後新增的 22 個 AT（見〈勘誤〉節）的根層指令另加 `-p no:xdist -o addopts=`（與 NFR-P1-10 (1) 同形，排除全域 `addopts` 與 xdist 對單一 AT 的影響）；鍵 B 的 AT（cwd 為 `AutoClaude/`）一律加 `-n 0`——本機 PG 在場時，AutoClaude 的 conftest 對全域 addopts 的 `-n auto` 回 rc=4（PG 在場但未用 `--dist loadgroup`），故既有九個與新增的鍵 B 指令皆為 `… -q -n 0`（`-p no:xdist` 不能與 `-n` 並用：`unrecognized arguments`，所以鍵 B 不加它；§7.1 ⚖ 29）。每個 `-k` 仍恰收一個測試。
>
> **測試檔縮寫**（判定指令的檔名依各 AT 標頭所列；鍵 B 的檔在 `AutoClaude/tests/contract/`）：**EV**＝`test_selfimproving_events.py`、**PR**＝`test_selfimproving_props.py`、**RS**＝`test_selfimproving_research_scan.py`、**ES**＝`test_selfimproving_export_status.py`、**CP**＝`test_selfimproving_capability.py`、**LY**＝`test_root_module_layout.py`（以上六檔皆在 `tools/tests/`）、**KB**＝`test_evolution_propose_only.py`。共用夾具住 `tools/tests/_selfimproving_fixtures.py`（底線開頭、不被收集；§5）。
>
> **斷言簡寫**（本節各 AT 共用）：
> - `main`＝`selfimproving.main`（測試以 `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` 後 `import selfimproving`，比照 P0 既有風格）；`M(<動詞與旗標>)`＝以 `contextlib.redirect_stdout`／`redirect_stderr` 呼叫 `main`（自動補 `--repo <R>`，AT 另指定者除外），回傳 `(rc, stdout, stderr)`；`MJ(…)`＝同上、附 `--json` 並 `json.loads` stdout。旗標以反引號內的命令列文字書寫（例 `run-open --trigger a …`），不是 Python 字面值。
> - `R`＝`make_p1_repo(...)` 回傳的 tmp git repo（§5.1）；`HOME`＝tmp 內的家目錄，環境變數 `AUTOSDD_SI_DIR` 指向它（§5.5）；`EVL`＝事件帳本路徑 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`；`EV(R)`＝事件帳本逐行 `json.loads` 的 dict 串列（檔案不存在＝空串列）；`ev(…)`、`SC-…`＝§5.2 的事件建構器與情境表（P2 起才由 CLI 寫的 kind，例如 `dec`、`app.*`、`mea.*`，一律由 `ev(…)` 手寫進事件帳本，P1 的 CLI 寫不出它們）。
> - `snap(R)`＝`R` 內除 `.git/` 之外全部檔案的〔相對路徑→位元組 sha256〕對照加 `git status --porcelain` 輸出；「**零殘留**」＝拒收後 `snap(R)` 等於拒收前、`HOME` 內除（已釋放的）鎖檔外無新檔（R28 (b)）；`codes(out)`＝自拒收輸出的 `  <CODE> <detail>` 行取出的碼集合（R28 (b)）；`draft_ok(R, out)`＝取拒收輸出 `obs-draft:` 之下那一行附加到 `R` 的複本的 OBS 帳本、跑 `check --json`，該列 ID 的 finding 為零（R28 (d)）。
> - `S(項目)`＝該項目的 `status`；`F(項目)`＝該項目 `findings` 的 `(subject, code)` 集合；「恰為」＝集合相等、「含」＝子集——沿 P0 §2 簡寫。「OBS 列號」`003` 等一律指 `OBS-SI-003`。
>
> **變異慣例**：預設自基線複製一份（`shutil.copytree`，含 `.git`）、在工作樹改寫、不 commit；需要「歷史」的情境（`events.mutated`、`events.research` 的提交歷史比對）明文寫出 commit 順序。各 AT 只斷言自己指名的項目與集合，**除非該 AT 明文寫 overall 或 rc**。**子情境**：AT 內以「情境一」「情境 (a)」等列舉的子情境，測試一律以 `subTest` 或參數化實作（保留 AT ID 對映），任一子情境失敗時，失敗訊息須指出是哪個情境。**AT 內不引用其他 AT 的 ID**（只有 §1、§3、§4、§6 的表格引用 AT ID）。**不得 skip**：git 或 loopback 埠缺席視為環境壞、測試直接失敗（NFR-P1-4）。

```gherkin
# AT-110-3-1
# 對應 AC: AC-110-3（PRD AC-SI-10-3；R47 (a)）`run-open` 五種 trigger 皆受理、配 RUN 號、記 head_sha，可多個運轉並存
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_110_3_1 -q

Feature: run-open 開運轉

Scenario: 五種 trigger 與雙座標的運轉各自受理，RUN 號連號，head_sha 取自 HEAD
  Given 依 §5.1 建出基線 `R`（無事件帳本），`HEAD` 為 `git rev-parse HEAD` 的值，家目錄為 tmp 內的 `HOME`
  When 依序呼叫 `run-open --trigger x --coord tools/lib/selfimproving/check.py:10 --by main`，x 依序取 `a`、`b`、`c`、`d`、`e`
  And 再呼叫一次 `run-open --trigger a --by main --json`，帶兩個 `--coord`（一個 `path:行號` 形態、一個反引號包住的 `python tools/selfimproving.py check` 加 ` rc=1`）
  Then 六次 rc 皆為 `0`；前五次 stdout 各為單行，符合 `ok run.open seq=<n> id=RUN-SI-<NNN> head_sha=<40 位小寫 hex>`，`<NNN>` 依序為 `001`～`005`
  And 第六次的 JSON 鍵序為 `ok`、`kind`、`seq`、`id`、`head_sha`，其 `id` 為 `RUN-SI-006`、`seq` 為 `6`
  And 事件帳本恰 6 行、`kind` 皆為 `run.open`、`seq` 為 1～6；各行的鍵集合恰為 `seq`、`t`、`kind`、`by`、`run`、`trigger`、`coords`、`head_sha`，`by` 為 `main`、`trigger` 依序為 `a`～`e` 與 `a`、`coords` 長度依序為 1、1、1、1、1、2、`head_sha` 全等於 `HEAD`
  And `MJ(status)` 的 `open_runs` 含六個運轉（多個運轉可同時開著），`MJ(check)` 的 `events.structure` 與 `events.transitions` 皆為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_3_1]"
```

```gherkin
# AT-110-3-E-1
# 對應 AC: AC-110-3（PRD AC-SI-10-3；R47 (a)、R27、R28）`run-open` 的用法錯誤 rc 3、狀態錯誤 rc 1；無 `run.open` 的提案與研究不受理；拒收零殘留且草稿列自驗
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_110_3_E_1 -q

Feature: run-open 與運轉前置的拒收

Scenario: 用法錯誤 rc 3，座標與 git 錯誤 rc 1，不存在的運轉擋下提案與研究
  Given 基線 `R`；`snap0＝snap(R)`、`home0＝HOME` 的檔案清單；執行期組出一個不存在的運轉號 `RX`（`RUN-SI-` 接 `9` 開頭的三位數）
  When 情境一（用法）：`run-open --trigger f --coord tools/a.py:1 --by main`、`run-open --trigger a --by main`（無 `--coord`）、`run-open --trigger a --coord tools/a.py:1`（無 `--by`）、兩次 `run-open --trigger a --coord tools/a.py:1 --by <標籤>`，標籤各為「含空白的字串」與「33 字元的字串」
  And 情境二：`run-open --trigger a --coord 本檔時間欄 --by main`（座標不可定位）
  And 情境三：把 `R` 複製為不含 `.git` 的目錄 `R2`，對 `R2` 呼叫 `run-open --trigger a --coord tools/a.py:1 --by main`
  And 情境四：對 `R` 呼叫 `prop-new --run RX` 加 §5.3 `good_prop_args(R)` 的其餘旗標，與 `research --skip --run RX --reason offline --note 離線`
  Then 情境一的五次呼叫：rc 皆為 `3`、stdout 空、stderr 至少一行且以 `selfimproving:` 起頭
  And 情境二：rc `1`，`codes(out)` 恰為 `COORD-NONE`，輸出含該座標原字；情境三：rc `1`、碼 `GIT-UNAVAILABLE`；情境四：兩個呼叫 rc 皆為 `1`，`codes(out)` 皆含 `RUN-NOT-OPEN`
  And 所有 rc 為 `1` 的呼叫：stdout 依序為 `reject <verb> …` 行、各碼行、`obs-draft:`、恰一行草稿列；`snap(R)` 等於 `snap0`、`HOME` 檔案清單等於 `home0`（零殘留）；`draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_3_E_1]"
```

```gherkin
# AT-103-2-1
# 對應 AC: AC-103-2（PRD AC-SI-03-2 的 `run-close` 半；R47 (b)）零 `prop` 的運轉記 `no_event`、有 `prop` 的運轉記 `outcomes`（各 PROP 折疊狀態）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_103_2_1 -q

Feature: run-close 記錄無事件與結果

Scenario: 零提案的運轉記無事件，有提案的運轉記各 PROP 的折疊狀態
  Given 依 §5.2 情境 `SC-CLOSE` 手寫事件帳本：運轉 `RUN-SI-001`（無任何 `prop`）；運轉 `RUN-SI-002`（含研究事件、`PROP-SI-124` 經 `dec approve` 成為 `approved`、`PROP-SI-125` 經 `dec reject` 成為 `rejected`）；兩個運轉皆 open
  When 呼叫 `run-close --run RUN-SI-001 --by main`，再呼叫 `run-close --run RUN-SI-002 --by main --json`
  Then 兩次 rc 皆為 `0`；第一次 stdout 為單行 `ok run.close seq=<n> run=RUN-SI-001 no_event=true`
  And 第一個 `run.close` 事件的鍵集合恰為 `seq`、`t`、`kind`、`by`、`run`、`no_event`，`no_event` 為 JSON `true`、沒有 `outcomes` 鍵
  And 第二次的 JSON 含 `outcomes` 筆數 2；第二個 `run.close` 事件的鍵集合恰為 `seq`、`t`、`kind`、`by`、`run`、`outcomes`，`outcomes` 恰為 PROP-SI-124 對 `approved`、PROP-SI-125 對 `rejected`，沒有 `no_event` 鍵
  And 兩次 `run.close` 後 `MJ(status)` 的 `open_runs` 為空；`MJ(check)` 的 `events.structure` 與 `events.transitions` 皆為 `PASS`（`SC-CLOSE` 含 `dec`，`events.transitions` 另帶 warn 層級的引言回查提示，不改狀態）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_103_2_1]"
```

```gherkin
# AT-103-2-E-1
# 對應 AC: AC-103-2（PRD AC-SI-03-2；R47 (b)）未開、已關、查無的運轉不得關閉；同一運轉不可二次關閉
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_103_2_E_1 -q

Feature: run-close 的拒收

Scenario: 已關與查無的運轉 rc 1，格式不合 rc 3，不產生第二筆 run.close
  Given 手寫事件帳本：`RUN-SI-001` 已 `run.open` 並已 `run.close`（記 `no_event`）；`R` 已提交；`n0＝EV(R)` 的筆數；執行期組出不存在的運轉號 `RX`
  When 情境一：`run-close --run RUN-SI-001 --by main`；情境二：`run-close --run RX --by main`；情境三：`run-close --run bad-id --by main`；情境四：`run-close --by main`（缺 `--run`）
  Then 情境一與二：rc 皆為 `1`，`codes(out)` 恰為 `RUN-NOT-OPEN`；情境三與四：rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 全部情境後 `EV(R)` 的筆數仍為 `n0`（沒有第二筆 `run.close`）、`snap(R)` 不變；rc 為 `1` 的兩個情境輸出含可貼入的草稿列且 `draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_103_2_E_1]"
```

```gherkin
# AT-105-1-1
# 對應 AC: AC-105-1（PRD AC-SI-05-1；R48 (a)）`attr --type root` 七種種類皆受理；事件鍵恰為欄位表；`NONE` 須以「無法歸因」起頭
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_105_1_1 -q

Feature: attr 歸因清單

Scenario: DEF、OBS、RULE、PLAYBOOK_STEP、DOC、MEMORY_ENTRY、NONE 七種種類皆可歸因
  Given 基線 `R`（OBS 列 001～010，缺陷帳本含 §5.1 的執行期 DEF 號 `D1`）
  When 依序呼叫七次 `attr --type root --by SA --obs OBS-SI-001 --item <種類>=<座標> --root-cause tools/lock-race`：`DEF=<D1>`、`OBS=OBS-SI-002`、`RULE=AISDLC_SDD/<VNEW>/governance/rules/R-9.1.yaml`（`<VNEW>` 取 §5.1 的夾具 LATEST 目錄名）、`PLAYBOOK_STEP=tools/x.py:3`、`DOC=docs/05_development/SelfImproving_Operations_SOP.md:5`、`MEMORY_ENTRY=memory/foo.md:3`、`NONE=無法歸因：缺少逐字稿`
  And 再呼叫一次 `attr --type root --by SA --obs OBS-SI-001 --obs OBS-SI-004 --item DOC=docs/06_quality/ --item OBS=OBS-SI-002 --root-cause docs/stale-note --json`
  Then 八次 rc 皆為 `0`；文字形態 stdout 各為單行 `ok attr seq=<n> id=ATT-SI-<NNN> type=root`，`<NNN>` 依序為 `001`～`007`（第八次為 `--json`，其 `id` 為 `ATT-SI-008`，鍵序為 `ok`、`kind`、`seq`、`id`、`type`）
  And 事件帳本恰 8 行 `attr`；各行的鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`type`、`obs`、`items`、`root_cause`；`items` 的每個元素是二元陣列〔種類, 座標〕（第七行的 `items` 只有一個元素，種類為 `NONE`、座標為 `無法歸因：缺少逐字稿`）；第八行的 `obs` 依旗標順序為兩個 ID、`items` 兩個元素
  And `MJ(check)` 的 `events.structure` 為 `PASS`（欄位表合規）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_105_1_1]"
```

```gherkin
# AT-105-1-E-1
# 對應 AC: AC-105-1（PRD AC-SI-05-1；R48 (a)）種類不在集合 rc 3；`NONE` 缺「無法歸因」、座標不可定位、根因鍵格式錯、OBS 不存在各 rc 1 並印對應碼；零寫入
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_105_1_E_1 -q

Feature: attr 的拒收

Scenario: 不合規的歸因被拒，且不留任何殘留
  Given 基線 `R`；`snap0＝snap(R)`；執行期組出不存在的 OBS 號 `OX`（`OBS-SI-` 接 `9` 開頭的三位數）
  When 情境一（rc 3）：`--item FOO=tools/x.py:1`（種類不在集合）、缺 `--root-cause`、缺 `--item`、`--type bogus`、`--type link` 而夾帶 `--obs`
  And 情境二（rc 1）：`--item NONE=猜測是網路問題`、`--item DEF=本檔時間欄`、`--root-cause` 依序為 `Tools/Lock`、`tools`、`tools/Lock_race`、`--obs OX`
  Then 情境一的五次呼叫：rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 情境二依序的 `codes(out)` 恰為 `ATTR-NONE-TEXT`、`COORD-NONE`、`ROOT-CAUSE-FORMAT`、`ROOT-CAUSE-FORMAT`、`ROOT-CAUSE-FORMAT`、`OBS-NOT-FOUND`（最後一項的輸出含 `OX`）；皆 rc `1`
  And 全部呼叫後 `snap(R)` 等於 `snap0`；rc 為 `1` 的呼叫其 `draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_105_1_E_1]"
```

```gherkin
# AT-105-2-1
# 對應 AC: AC-105-2（PRD AC-SI-05-2；R48 (d)）歸因事件不含自評分數；歸因只動事件帳本，不改任何被指向的檔
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_105_2_1 -q

Feature: 歸因無自評分數、不改檔

Scenario: attr 前後只多事件帳本一個檔，事件鍵不含任何分數類欄位
  Given 基線 `R`（已提交、工作樹乾淨）；`snap0＝snap(R)`
  When 呼叫 `attr --type root --by SA --obs OBS-SI-001 --item DOC=docs/05_development/SelfImproving_Operations_SOP.md:5 --root-cause docs/stale-note`
  Then rc 為 `0`；事件的鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`type`、`obs`、`items`、`root_cause`（沒有任何名稱含 `conf`、`score`、`rating`、`prob` 的鍵）
  And `git status --porcelain` 的輸出恰多出事件帳本一個未追蹤檔（其餘行與 `snap0` 相同）；`snap(R)` 除事件帳本之外的全部檔案位元組摘要等於 `snap0`（含被歸因所指向的 SOP 檔與帳本）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_105_2_1]"
```

```gherkin
# AT-105-2-E-1
# 對應 AC: AC-105-2（PRD AC-SI-05-2；R48 (d)、R37）自評旗標即未知旗標 rc 3；手寫夾帶自評鍵的 attr 事件被 `check` 判 EVENT-KEY-UNKNOWN
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_105_2_E_1 -q

Feature: 自評分數被擋

Scenario: 沒有自評旗標，夾帶自評鍵的事件被判紅
  Given 基線 `R`；`snap0＝snap(R)`
  When 情境一：呼叫 `attr --type root --by SA --obs OBS-SI-001 --item DOC=docs/06_quality/ --root-cause docs/stale-note --confidence 0.9`，另一次改帶 `--score 3`
  And 情境二：手寫一筆合規的 `attr` 事件，多加一個鍵 `confidence`（值 `0.9`），寫入事件帳本後呼叫 `check --json`
  Then 情境一：兩次 rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭，`snap(R)` 等於 `snap0`
  And 情境二：`S(events.structure)` 為 `FAIL`，`F(events.structure)` 恰為 `seq=<該筆 seq>` 對 `EVENT-KEY-UNKNOWN`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_105_2_E_1]"
```

```gherkin
# AT-106-1-1
# 對應 AC: AC-106-1（PRD AC-SI-06-1；R48 (c)(e)）確認者≠提出者、確認落事件；根因鍵事後更改的次數入資訊欄
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_106_1_1 -q

Feature: 根因鍵與確認

Scenario: 審查者確認歸因，同一 OBS 的根因鍵被改過一次即計一次
  Given 基線 `R`；先以 CLI 兩次 `attr --type root --by SA --obs OBS-SI-001 --item DOC=docs/06_quality/ --root-cause tools/a-b`、`attr --type root --by SA --obs OBS-SI-001 --item DOC=docs/06_quality/ --root-cause tools/c-d`（得 `ATT-SI-001`、`ATT-SI-002`）
  When 呼叫 `attr-confirm --att ATT-SI-001 --by QA`，再呼叫 `status --json`
  Then `attr-confirm` rc 為 `0`、stdout 為單行 `ok attr.confirm seq=3 att=ATT-SI-001`；事件鍵集合恰為 `seq`、`t`、`kind`、`by`、`att`，`by` 為 `QA`
  And `MJ(status)` 的 `root_cause_changes` 為 `1`（同一 OBS 的兩個根因鍵相鄰不同）
  And `MJ(check)` 的 `events.transitions` 為 `PASS`（沒有 `CONFIRMER-IS-PROPOSER`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_106_1_1]"
```

```gherkin
# AT-106-1-E-1
# 對應 AC: AC-106-1（PRD AC-SI-06-1；R48 (c)、R38）自己確認、重複落定、查無歸因皆拒收；手寫的自我確認被 `check` 判 CONFIRMER-IS-PROPOSER
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_106_1_E_1 -q

Feature: attr-confirm 與 attr-reject 的拒收

Scenario: 確認者等於提出者、重複落定、查無歸因被拒；事件層的違規被 check 抓到
  Given 基線 `R`；以 CLI 建 `ATT-SI-001`（`by` 為 `SA`）與 `ATT-SI-002`（`by` 為 `SA`）；`snap0＝snap(R)`；執行期組出不存在的歸因號 `AX`
  When 情境一：`attr-confirm --att ATT-SI-001 --by SA`；情境二：先 `attr-confirm --att ATT-SI-001 --by QA`（成功）再重複一次、再對同一筆呼叫 `attr-reject --att ATT-SI-001 --by QA --note 另有看法`；情境三：`attr-confirm --att AX --by QA`
  And 情境四：另建一份帳本，手寫一筆 `attr.confirm` 其 `by` 等於被引 `attr` 的 `by`，另手寫第二筆對已落定的歸因再次 `attr.confirm`，呼叫 `check --json`
  Then 情境一：rc `1`、`codes(out)` 恰為 `CONFIRMER-IS-PROPOSER`；情境二的重複確認與反向駁回：rc 皆 `1`、碼 `ALREADY-SETTLED`；情境三：rc `1`、碼 `ATT-NOT-FOUND`
  And 情境一與三的 rc 為 `1` 之呼叫後 `snap(R)` 不變、`draft_ok` 成立；情境二只多一筆成功的 `attr.confirm`
  And 情境四：`S(events.transitions)` 為 `FAIL`，`F(events.transitions)` 含 `CONFIRMER-IS-PROPOSER`（subject 為被引的歸因號）與 `TRANSITION-ILLEGAL`（第二筆落定）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_106_1_E_1]"
```

```gherkin
# AT-106-2-1
# 對應 AC: AC-106-2（PRD AC-SI-06-2；R48 (b)(c)）`attr --type link` 受理已結列；確認與駁回（附一句理由）；未確認者只計入數量
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_106_2_1 -q

Feature: 復發連結與確認

Scenario: 連結須指向已結列；確認或駁回後未確認數遞減
  Given 基線 `R`（已結列：OBS 列 002〔`fixed@…`〕、006〔`decided`〕、缺陷帳本的 `D1`）
  When 呼叫三次 `attr --type link --by SA --from OBS-SI-009 --reopens OBS-SI-002`、`attr --type link --by SA --from OBS-SI-010 --reopens OBS-SI-006`、`attr --type link --by SA --from OBS-SI-001 --reopens <D1>`
  And 呼叫 `status --json` 得 `u0`；再呼叫 `attr-confirm --att ATT-SI-001 --by QA` 與 `attr-reject --att ATT-SI-002 --by QA --note 證據不足`；再呼叫 `status --json` 得 `u1`
  Then 三次 `attr` rc 皆為 `0`；`link` 事件的鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`type`、`from`、`reopens`；`attr-reject` 事件的鍵集合恰為 `seq`、`t`、`kind`、`by`、`att`、`note`，`note` 為 `證據不足`
  And `u0` 的 `reopen_candidates.unsettled` 為 `3`、`u1` 的為 `1`（只有 `ATT-SI-003` 未落定）
  And `MJ(check)` 的 `events.structure` 與 `events.transitions` 皆為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_106_2_1]"
```

```gherkin
# AT-106-2-E-1
# 對應 AC: AC-106-2（PRD AC-SI-06-2；R48 (b)(c)）連結對象須是已結列；`attr-reject` 須附合規的一句理由
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_106_2_E_1 -q

Feature: attr link 與 attr-reject 的拒收

Scenario: 未結列、查無的連結對象與不合規的駁回理由被拒
  Given 基線 `R`（OBS 列 001 為 `open`、004 為 `deferred`）；先建 `ATT-SI-001`（`type` 為 `root`，`by` 為 `SA`）；`snap0＝snap(R)`；執行期組出不存在的 OBS 號 `OX` 與不存在的 DEF 號 `DX`（以字串相加，不寫字面編號）
  When 情境一：`attr --type link --by SA --from OBS-SI-009 --reopens OBS-SI-001`、`--reopens OBS-SI-004`；情境二：`--reopens OX`、`--reopens DX`；情境三：`--from OX --reopens OBS-SI-002`
  And 情境四：`attr-reject --att ATT-SI-001 --by QA` 缺 `--note`、`--note` 為空字串、`--note` 為 121 個字元、`--note` 含換行
  Then 情境一：兩次 rc 皆 `1`、`codes(out)` 皆為 `REOPENS-NOT-CLOSED`；情境二：兩次 rc 皆 `1`、碼 `REOPENS-NOT-FOUND`；情境三：rc `1`、碼 `OBS-NOT-FOUND`
  And 情境四的四次呼叫：rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 全部呼叫後 `snap(R)` 等於 `snap0`；rc 為 `1` 的呼叫其 `draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_106_2_E_1]"
```

```gherkin
# AT-106-2-E-2
# 對應 AC: AC-106-2（PRD AC-SI-06-2；R45）立案當下 `check` 對新列印復發候選提示（warn 等級：不改狀態、不影響 rc），誤報面（已提交、已有 reopens、處置非 open、路徑無交集）零提示
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_106_2_E_2 -q

Feature: 復發候選提示

Scenario: 新列與已結列同證據路徑時列出候選；其餘情形不提示
  Given `make_p1_repo` 帶 `extra_obs`：已結列 OBS-SI-021（處置 `decided：…`、證據座標 `tools/lib/selfimproving/zz.py:7`）與缺陷帳本的一列（執行期 DEF 號、狀態 `fixed@abc1234`、證據 `tools/lib/selfimproving/zz.py:99`），已提交；工作樹（未提交）另加新列 OBS-SI-040（處置 `open`、證據 `tools/lib/selfimproving/zz.py:40`、標記 `面=產品;來源=代理;回報者=SA`）
  When 情境一：呼叫 `check --json`
  And 情境二（誤報面，各自複製基線再變異）：(a) 把新列連同基線一起提交；(b) 新列標記加 `reopens=OBS-SI-021`；(c) 新列處置改為 `deferred；再開症狀：同一症狀再現`；(d) 新列證據改為 `tools/lib/selfimproving/other.py:3`
  And 情境三：另一份帳本含七個已結 OBS 列（OBS-SI-021～027，同一證據路徑、缺陷帳本無匹配列）加同一新列 OBS-SI-040
  And 情境四：把情境一的工作樹複製成不含 `.git` 的目錄後呼叫 `check --json`
  Then 情境一：`S(row.markers)` 為 `PASS`；`F(row.markers)` 含 `(OBS-SI-040, REOPEN-CANDIDATE)`，該 finding 的 detail 以 `[warn]` 起頭並含 `OBS-SI-021` 與執行期 DEF 號；整體 rc 為 `0`、`overall` 為 `PASS`
  And 情境二的四個變異：`F(row.markers)` 皆不含 `REOPEN-CANDIDATE`
  And 情境三：detail 依字串位元組序列出 `OBS-SI-021`～`OBS-SI-025` 五個並以 `…+2` 結尾
  And 情境四：`F(row.markers)` 不含 `REOPEN-CANDIDATE`（git 不可用則本提示不產生）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_106_2_E_2]"
```

```gherkin
# AT-141-1-1
# 對應 AC: AC-141-1（本檔自增；PRD §9.2〈事件帳本規約〉；R30、R31、R32）各寫入動詞成功時恰追加一行，行形態與鍵序合規
# 測試類型: Contract
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_1_1 -q

Feature: 事件行形態

Scenario: 八個寫入呼叫各追加一行，行為緊湊 JSON、UTF-8 無 BOM、LF，鍵序為共通鍵加欄位表序
  Given 基線 `R`；`event_max_bytes` 為 §5.1 的初值
  When 依序呼叫：`run-open`（得 `RUN-SI-001`）、`research --skip --run RUN-SI-001 --reason offline --note 離線驗證`、`attr --type root`（`ATT-SI-001`）、`attr --type link`（`ATT-SI-002`，`--reopens` 取 OBS 列 002）、`attr-confirm --att ATT-SI-001 --by QA`、`attr-reject --att ATT-SI-002 --by QA --note 證據不足`、`prop-new`（旗標取 §5.3 `good_prop_args(R)`，`--run RUN-SI-001`）、`run-close --run RUN-SI-001`
  And 每次呼叫前後各記一次事件帳本的位元組長與行數
  Then 八次 rc 皆為 `0`，每次成功恰多一行（八次後共 8 行，`seq` 為 1～8）
  And 事件帳本位元組以嚴格 UTF-8 解碼成功、開頭沒有 BOM、不含 CR、結尾為 LF；每行等於對該行 `json.loads`（保留鍵序）後以 `ensure_ascii=False` 與緊湊分隔符重新輸出的結果（逐字相同）；`attr.reject` 那行的 `note` 以原字（非 `\u` 跳脫）出現
  And 每行前四個鍵依序為 `seq`、`t`、`kind`、`by`；`t` 符合 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$` 且 `datetime.fromisoformat(t).utcoffset()` 不是 `None`；`kind` 屬 19 個詞彙；整行位元組數（不含 LF）不超過 `event_max_bytes`
  And 各 kind 在共通鍵之後的鍵序與 R31 表一致：`run.open` 為 `run`、`trigger`、`coords`、`head_sha`；`research.skip` 為 `run`、`reason`、`note`；`attr`（root）為 `id`、`type`、`obs`、`items`、`root_cause`；`attr`（link）為 `id`、`type`、`from`、`reopens`；`attr.confirm` 為 `att`；`attr.reject` 為 `att`、`note`；`prop` 為 `id`、`rev`、`run`、`base`、`cls`、`action`、`route`、`target`、`touched_count`、`touched_sha256`、`patch_sha256`、`body_sha256`、`digest`、`sources`、`proposer`、`reviewer`；`run.close` 為 `run`、`outcomes`
  And `by` 的取值：`research.skip` 為 `main`，其餘為各呼叫的 `--by` 或 `--proposer` 值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_1_1]"
```

```gherkin
# AT-141-1-E-1
# 對應 AC: AC-141-1（本檔自增；R30、R32）`seq` 與各家族編號的配法、行長上限邊界、撕裂帳本拒寫
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_1_E_1 -q

Feature: 事件帳本的配號與寫入前置

Scenario: seq 取末行加一、編號家族取最大值加一、行長恰等於上限放行、撕裂帳本拒寫
  Given 情境一：依 §5.2 情境 `SC-SEQ` 手寫事件帳本（`seq` 依序為 5、6、9、10：第 5 筆 `run.open`〔`RUN-SI-007`〕、第 6 筆該運轉的 `research.skip`、第 9 筆 `attr`〔`ATT-SI-012`〕、第 10 筆 `prop`〔`PROP-SI-130`，類別 `D`，`target` 為 `docs/notes/demo.md`〕）
  And 情境二：事件帳本為 0 位元組空檔；情境三：事件帳本不存在
  And 情境四（自我校準的邊界）：先在一份新 `R` 以高上限呼叫一次 `run-open`（兩個 `--coord`），量得該事件行位元組數 `L`；再各建新 `R`，`event_max_bytes` 分別設為 `L` 與 `L－1`（同一指令）
  And 情境五：事件帳本的最後一個位元組不是 LF（合規行去掉結尾 LF）；情境六：末行是無法解析的字串（結尾有 LF）
  When 情境一依序呼叫 `run-open`、`attr --type root`、`prop-new --run RUN-SI-007`（其餘旗標取 §5.3 `good_prop_args(R)`，類別 `P`，與既有 PROP 不同型）；情境二與三依序呼叫 `run-open`、`research --skip`（對剛開的運轉）、`prop-new`；其餘情境各呼叫一次 `run-open`
  Then 情境一：新事件的 `seq` 皆為前一行 `seq` 加一（接在 10 之後依序為 11、12、13）；`RUN` 號為 `RUN-SI-008`、`ATT` 號為 `ATT-SI-013`、`PROP` 號為 `PROP-SI-131`（事件帳本的最大值 130 與 OBS 帳本內的 PROP 引用 123 取大者加一）
  And 情境二與三：第一個新事件的 `seq` 為 `1`、`RUN` 號為 `RUN-SI-001`；`prop-new` 的 `PROP` 號為 `PROP-SI-124`（事件帳本沒有 PROP，只有 OBS 帳本的引用 123）
  And 情境四：`event_max_bytes` 為 `L` 時 rc 為 `0` 且事件行位元組數恰為 `L`；為 `L－1` 時 rc 為 `1`、`codes(out)` 恰為 `EVENT-BYTES-OVER`、事件帳本位元組不變
  And 情境五與六：rc 皆為 `1`、`codes(out)` 恰為 `LEDGER-TORN`、事件帳本位元組不變、`HOME` 無新檔；`draft_ok` 成立
  And 另一個情境：`params.json` 刪去 `event_max_bytes` 後呼叫 `run-open`：rc 為 `3`、stderr 含鍵名 `event_max_bytes`、事件帳本不存在
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_1_E_1]"
```

```gherkin
# AT-141-1-E-2
# 對應 AC: AC-141-1（本檔自增；R32 (c)、R33）`PROP-SI-NNN` 配號的 OBS 帳本部分在寫入鎖內讀取：取鎖之前才出現的 PROP 引用不得被漏算
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_1_E_2 -q -p no:xdist -o addopts=

Feature: PROP 配號的鎖內判定

Scenario: 於取鎖之前才附加到 OBS 帳本的 PROP 引用仍被配號納入；對照組不改帳本
  Given 基線 `R`（OBS 帳本列 008 引用執行期組出的 `PROP-SI-123`、事件帳本沒有 PROP）；已開運轉 `RUN-SI-001`（夾具 `open_run`）；執行期組出 `PX`＝`PROP-SI-` 接 `140`；兩份複本各自進行
  When 情境一（對照）：呼叫 `prop-new --run RUN-SI-001`（旗標取 §5.3 `good_prop_args(R)`，類別 `P`）
  And 情境二：先以 `mock.patch.object(evwrite, "append_event", <包裝函式>)` 包住追加路徑——包裝函式在以原引數轉呼叫真實 `append_event` 之前，把一行含 `PX` 的文字附加到該複本的 OBS 帳本檔尾（模擬他人在本動詞開始執行之後、取得寫入鎖之前改動 OBS 帳本）——再呼叫同一個 `prop-new`
  Then 情境一：rc 為 `0`、新 PROP 號為 `PROP-SI-124`（OBS 帳本的引用 123 加一；事件帳本沒有 PROP）
  And 情境二：rc 為 `0`、新 PROP 號為 `PROP-SI-141`（鎖內讀到的 OBS 帳本最大 PROP 引用 140 加一）
  And 情境二的 `prop` 事件 `id` 與內容檔目錄 `docs/06_quality/SelfImproving_Proposals/PROP-SI-141/` 一致，該複本的事件帳本恰多一行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_1_E_2]"
```

```gherkin
# AT-141-2-1
# 對應 AC: AC-141-2（本檔自增；PRD ADR-SI-10 併發負控 ①②；R33）鎖內重讀末行與配號：確定性交錯（無鎖對照組撞同一 seq）與多行程壓力
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + threading 與 subprocess
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_2_1 -q

Feature: 事件帳本寫入鎖

Scenario: 無鎖路徑必撞號、有鎖路徑第二者得 seq 加一；八行程各十筆無撞號無撕行
  Given 基線 `R` 與 `HOME`；`ledger` 為 `R` 的事件帳本路徑；`lock_path` 為 `HOME` 下依 R33 規則算出的鎖檔路徑；測試函式 `build` 回傳 `run.open` 事件（`run` 取 `state.last_seq` 加一組成，`coords` 固定、`by` 固定、`trigger` 為 `a`、`head_sha` 為 40 個 `0`）
  When 情境一（無鎖對照組）：以兩個執行緒各呼叫 `evwrite.append_event(ledger, None, build)`，`evwrite.PAUSE_HOOK` 以 `mock.patch.object` 設為「到達後等待另一執行緒也到達」的柵欄函式（兩者都已讀完末行才放行）
  And 情境二（有鎖路徑）：以兩個執行緒各呼叫 `evwrite.append_event(ledger, lock_path, build)`，鉤子設為「第一個到達者等待測試放行訊號、並記下到達順序」；測試等待 1 秒，確認第二個執行緒尚未到達鉤子，再放行
  And 情境三（壓力）：啟動 8 個子行程（先全部 `Popen`、再等待），每個子行程在環境變數 `AUTOSDD_SI_DIR` 指向同一 `HOME` 之下，於行程內連續呼叫 `main` 十次 `attr --type root`（每次的 `--obs`、`--item`、`--root-cause` 合規）；全部結束後讀事件帳本
  Then 情境一：帳本有 2 行且兩行的 `seq` 相同（對照組證明讀改寫的競態確實存在）
  And 情境二：帳本有 2 行、`seq` 為相異的相鄰兩號；第二個執行緒的 `build` 收到的 `state.last_seq` 等於第一個寫入的 `seq`（鎖內重讀）；第二個執行緒在放行前未到達鉤子
  And 情境三：8 個子行程 rc 皆為 `0`；帳本恰 80 行、`seq` 為 1～80 連續無重複；每行皆為完整 JSON 且不超過 `event_max_bytes`；`ATT-SI-001`～`ATT-SI-080` 無重複；整個情境牆鐘小於 60 秒；`MJ(check)` 的 `events.structure` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_2_1]"
```

```gherkin
# AT-141-2-E-1
# 對應 AC: AC-141-2（本檔自增；PRD ADR-SI-10 併發負控 ③④；R29、R33）陳舊鎖被回收；新鮮鎖逾時 fail-loud 並印持鎖者；家目錄不可寫拒寫
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_2_E_1 -q

Feature: 鎖的失效模式

Scenario: 陳舊鎖回收後寫入成功；新鮮鎖不放時逾時 rc 1；家目錄不可寫 rc 3 且不退回暫存目錄
  Given 基線 `R` 與 `HOME`；`lock_path` 為依 R33 規則算出的鎖檔路徑（目錄 `HOME/locks` 已建）
  When 情境一（陳舊）：在 `lock_path` 預置一個鎖檔（內容為某個不存在的 pid 與時間），以 `os.utime` 把其 mtime 設為 1000 秒之前，呼叫 `run-open`
  And 情境二（新鮮）：測試以 `lib.apply_lock.acquire(lock_path, 5, 300)` 取得鎖並持有，期間把 `evwrite.LOCK_TIMEOUT_SECONDS` 以 `mock.patch.object` 改為 1 後呼叫 `run-open`；結束後釋放鎖再呼叫一次
  And 情境三（家目錄不可寫）：`AUTOSDD_SI_DIR` 指向一個其上層是普通檔案的路徑（建不出 `locks/`）；呼叫 `run-open`；另對同一環境呼叫 `check`、`status --json`、`scan`、`export --json --kind status`；呼叫前後各列一次系統暫存目錄（`tempfile.gettempdir()`）內名稱含 `selfimproving` 或 `locks` 者
  Then 情境一：rc 為 `0`、事件帳本多一行、`lock_path` 在呼叫後不存在（已釋放）
  And 情境二：第一次 rc 為 `1`、`codes(out)` 恰為 `LOCK-BUSY`、輸出含持鎖者的 pid（測試行程自己的 `os.getpid()`）、事件帳本位元組不變、`draft_ok` 成立；釋放後第二次 rc 為 `0`
  And 情境三：`run-open` rc 為 `3`、stderr 含 `HOME-UNWRITABLE`、事件帳本不存在；系統暫存目錄前後清單相同（沒有退回暫存目錄）；其餘四個唯讀動詞 rc 皆為 `0`（唯讀動詞不要求家目錄可寫）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_2_E_1]"
```

```gherkin
# AT-141-2-E-2
# 對應 AC: AC-141-2（本檔自增；R33）鎖檔名為事件帳本 realpath 的 sha256 前 16 位 hex 加 `.lock`：持鎖期間存在、寫入完成後已釋放
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_2_E_2 -q -p no:xdist -o addopts=

Feature: 鎖檔命名

Scenario: 持鎖期間 HOME 的 locks 目錄恰有一個依事件帳本 realpath 雜湊命名的鎖檔
  Given 基線 `R` 與 `HOME`（兩份不同的 `R` 複本 `R1`、`R2`，其事件帳本 realpath 不同）；測試端獨立算出各自的 `want`＝`hashlib.sha256(os.path.realpath(<事件帳本路徑>).encode("utf-8")).hexdigest()[:16]` 接 `.lock`（不呼叫 `evwrite.lock_path_for`）
  When 以 `mock.patch.object(evwrite, "PAUSE_HOOK", <鉤子>)` 設鉤子（讀末行並配號之後、單次追加之前被呼叫），鉤子記下 `HOME/locks` 內的檔名清單；對 `R1` 與 `R2` 各呼叫一次 `run-open --trigger a --coord tools/a.py:1 --by main`
  Then 兩次 rc 皆為 `0`；兩次鉤子記到的清單各恰為單一元素 `[want]`（16 位小寫 hex 加 `.lock`），且兩個 `want` 互不相同
  And 每次呼叫結束後，`HOME/locks` 內沒有任何 `.lock` 檔（已釋放）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_2_E_2]"
```

```gherkin
# AT-141-2-E-3
# 對應 AC: AC-141-2（本檔自增；R29）家目錄與其 `locks/`、`research/` 都已存在但寫不進（可寫性探測失敗）⇒ 寫入動詞 rc 3、`HOME-UNWRITABLE`；與「建不出目錄」是兩條不同的失敗路徑
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_141_2_E_3 -q -p no:xdist -o addopts=

Feature: 家目錄存在但不可寫

Scenario: 探測檔建不出時寫入動詞拒寫，唯讀動詞照常
  Given 基線 `R` 與 `HOME`；預先建好 `HOME/locks` 與 `HOME/research` 兩個目錄；於 `HOME/locks` 內預先建一個名為 `.probe-<本測試行程的行程號>` 的**目錄**（與 R29 的可寫性探測檔同名；同名目錄使建檔在 Windows 與 POSIX 皆失敗，免用平台專屬的唯讀權限）；`snap0＝snap(R)`、`home0＝HOME` 的檔案清單
  When 在同一行程內呼叫 `run-open --trigger a --coord tools/a.py:1 --by main`；另對同一環境呼叫 `check`、`status --json`、`scan`、`export --json --kind status`
  Then `run-open`：rc 為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭且含 `HOME-UNWRITABLE`；事件帳本不存在、`snap(R)` 等於 `snap0`、`HOME` 檔案清單等於 `home0`（沒有鎖檔殘留）
  And 其餘四個唯讀動詞 rc 皆為 `0`
  And 對照：移除那個同名目錄後，同一環境呼叫 `run-open` 的 rc 為 `0`、事件帳本多一行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_141_2_E_3]"
```

```gherkin
# AT-108-4-1
# 對應 AC: AC-108-4（PRD AC-SI-08-4 ①；R34、R38）事件序列的合法轉移與跳級、孤兒的判定
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_108_4_1 -q

Feature: check 的狀態轉移重放

Scenario: 合法序列通過，各種跳級與孤兒各被判出
  Given 依 §5.2 情境 `SC-LEGAL` 手寫事件帳本（`PROP-SI-124`～`PROP-SI-137` 的事件鏈與終態見該表：涵蓋全部合法轉移，含 returned 後修訂、`verdict` 為 `NE` 加 `unverified_ack` 的晉升、`decline-promote`、`mea.close` 為 `pending` 維持 measuring、`mea.amend`、`dec rollback`；運轉 `RUN-SI-001` 全程 open）
  When 情境一：對 `SC-LEGAL` 呼叫 `check --json`
  And 情境二（各自在 `SC-LEGAL` 之後加一筆違規事件，逐一呼叫 `check --json`；PROP 號取自該表的終態）：(a) 對 `proposed` 的 `PROP-SI-129` 做 `app.sandbox`；(b) 對 `handoff:T1` 的 `PROP-SI-134` 做 `dec approve`；(c) 對 `returned` 的 `PROP-SI-135`（`rev` 為 1）追加 `rev` 為 3 的 `prop`，另一案對 `proposed` 的 `PROP-SI-129` 追加 `rev` 為 2 的 `prop`；(d) 對 `verified`（`PASS`）而尚無 `dec promote` 的 `PROP-SI-131` 做 `app.promote`；(e) 對 `verdict` 為 `FAIL` 的 `PROP-SI-132`、對 `verdict` 為 `NE` 而無 `unverified_ack` 的 `PROP-SI-133` 各做 `dec promote`；(f) 對 `approved` 的 `PROP-SI-130` 做 `mea.open`；(g) 對 `PROP-SI-124` 追加第二筆 `rev` 為 1 的 `prop`
  And 情境三（孤兒；各自一筆）：對執行期組出的不存在 PROP 號做 `dec approve`、對不存在的 ATT 號 `attr.confirm`、對不存在的 PROP 號 `card`、`dec resume` 指向不存在的運轉
  And 情境四：對未開的運轉 `run.close`、對已關的運轉再 `run.close`、`prop` 事件的 `run` 在該事件當時並非 open
  Then 情境一：`S(events.transitions)` 為 `PASS`、`F(events.transitions)` 恰為單一 `(-, QUOTE-VERIFIER-NOT-ESTABLISHED)`（`SC-LEGAL` 含 `dec`，故帶 warn 層級的引言回查提示，R38）；`S(events.structure)` 為 `PASS`
  And 情境二的九個變異（(a)、(b)、(c) 的兩個子情境、(d)、(e) 的兩個子情境、(f)、(g)）：`S(events.transitions)` 皆為 `FAIL`，`F(events.transitions)` 去掉上述引言回查提示後恰含一筆 `TRANSITION-ILLEGAL`，subject 為被違規的 PROP 號、detail 含 `seq=<該事件的 seq>`、事件 kind 與前置狀態
  And 情境三：四組各（同樣去掉該提示後）恰一筆 `TRANSITION-ORPHAN`，subject 為 `seq=<該事件的 seq>`
  And 情境四：三組各（同樣去掉該提示後）恰一筆 `TRANSITION-ILLEGAL`，detail 含 `seq=<該事件的 seq>`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_4_1]"
```

```gherkin
# AT-108-4-E-1
# 對應 AC: AC-108-4（PRD AC-SI-08-4 ②；R39）已提交的事件行不得被改寫或刪除；追加與 CRLF 轉換放行；無歷史與 git 不可用的處置
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_108_4_E_1 -q

Feature: 事件帳本只准追加

Scenario: 改寫與刪除判 ROW-MUTATED，追加與格式轉換放行
  Given 基線 `R`，其事件帳本由四筆合規事件組成（`seq` 為 1～4），提交為 C1
  When 情境一（追加）：再提交 C2，附加第 5 筆；`check --json`
  And 情境二（改寫）：自 C2 另提交 C3，把 `seq` 為 2 的行的 `by` 改成別的標籤；情境三（刪末行）：自 C2 另提交 C3，刪去最後一行；情境四（刪中間行）：自 C2 另提交 C3，刪去 `seq` 為 3 的行
  And 情境五（工作樹）：自 C2 起不提交，(a) 改寫 `seq` 為 2 的行；(b) 附加一行；(c) 先改寫再改回原樣
  And 情境六：自 C2 另提交 C3，把整個事件帳本轉成 CRLF 行尾
  And 情境七：事件帳本存在但從未被提交（未追蹤）；情境八：把 `R` 複製成不含 `.git` 的目錄
  Then 情境一：`S(events.mutated)` 為 `PASS`
  And 情境二：`F(events.mutated)` 恰為 `(seq=2, ROW-MUTATED)`，detail 含 `cause=changed`、`commit=` 接 C3 的前 7 位 sha 與字樣 `掌舵者`
  And 情境三：恰為 `(seq=5, ROW-MUTATED)`，detail 含 `cause=deleted`；情境四（刪去中間的 `seq` 為 3 的行，其後各行上移）：恰為 `(seq=3, ROW-MUTATED)`、`(seq=4, ROW-MUTATED)`、`(seq=5, ROW-MUTATED)` 三筆，前兩者 detail 含 `cause=changed`、第三者含 `cause=deleted`
  And 情境五：(a) `F(events.mutated)` 恰為 `(seq=2, ROW-MUTATED)` 且 detail 含 `commit=WORKTREE`；(b) 與 (c) 的 `S(events.mutated)` 為 `PASS`（只看工作樹與 HEAD 的淨差異）
  And 情境六：`S(events.mutated)` 為 `PASS`；情境七：`S(events.mutated)` 為 `PASS` 且項目層 detail 為 `no-history`；情境八：該項為 NE、`blocking` 為 true、碼 `GIT-UNAVAILABLE`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_4_E_1]"
```

```gherkin
# AT-108-4-E-2
# 對應 AC: AC-108-4（PRD AC-SI-08-4 ③④⑤；R37、R40、R38）結構判準（ID 唯一遞增、`t` 帶 offset、`kind` 在封閉詞彙）、反空轉下限、`dec` 引言回查印 warn 層級提示
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_108_4_E_2 -q

Feature: 事件行結構、下限與回查未建

Scenario: 各結構碼逐一命中；事件數低於下限判未判；有 dec 時印 warn 層級的引言回查未建提示
  Given 基線 `R`（`min_events` 為 1）；每個情境各自在乾淨的事件帳本寫入合規事件加一個變異行
  When 情境一（EVENT-PARSE）：夾一個空白行、一行 `[1]`、一行不是 JSON 的字串
  And 情境二（EVENT-KEY-MISSING）：缺 `by`；`run.open` 缺 `head_sha`；情境三（EVENT-KIND）：`kind` 為不在 19 個詞彙內的字串
  And 情境四（EVENT-TYPE）：`seq` 為 JSON `true`、`seq` 為 `0`、`t` 為不帶 offset 的時間、`by` 含空白、`by` 為 33 字元、`run.close` 同時有 `outcomes` 與 `no_event`、`run.close` 兩者皆無、`research.skip` 的 `reason` 為 `quota-band` 而缺 `band`、`band` 為 `Free`、`prop` 的 `cls` 為 `M` 而缺 `preimage`、`cls` 為 `P` 而有 `preimage`
  And 情境五（EVENT-KEY-UNKNOWN）：`run.open` 多一個鍵；情境六（EVENT-SEQ）：`seq` 依序為 1、2、2、1，另一情境為 1、3、7（跳號合法）
  And 情境七（EVENT-BYTES-OVER）：`event_max_bytes` 設小，一行超過；情境八：整檔 CRLF 加開頭 BOM
  And 情境九（下限）：`min_events` 設為 3，事件數分別為 2、3；另一情境事件帳本為空檔
  And 情境十（回查；不套用「每個情境各自寫入合規事件」的做法）：先以 CLI 建兩個不同型的合規 PROP（夾具 `open_run` 與 `good_prop_args`，`P` 類與 `D` 類各一個，內容檔俱在），再手寫兩筆 `dec`（`dkind` 為 `approve`，各指其中一個 PROP）接在事件帳本之後
  Then 情境一至五與七：`S(events.structure)` 皆為 `FAIL`，`F(events.structure)` 各恰為對應碼（subject 為 `seq=<n>`，`seq` 不可解析時為 `L<行號>`；情境一的三個變異各自一筆 `EVENT-PARSE`、情境四的每個變異各自一筆 `EVENT-TYPE`）；P2 起的 kind（`card`、`mea.report` 等）只含共通鍵時 `S(events.structure)` 為 `PASS`
  And 情境六：`seq` 為 1、2、2、1 時 `F(events.structure)` 恰為 `(seq=2, EVENT-SEQ)` 與 `(seq=1, EVENT-SEQ)`；為 1、3、7 時 `S(events.structure)` 為 `PASS`
  And 情境八：`S(events.structure)` 為 `PASS`（容忍 BOM 與 CR）；情境九：事件數 2 時 `S(events.vacuity)` 為 NE、`blocking` 為 true、碼 `EVENTS-BELOW-FLOOR`，事件數 3 時為 `PASS`，空檔為 NE（碼同上）
  And 情境十：`S(events.transitions)` 為 `PASS`（warn 層級，不改狀態）、含單一 finding `(-, QUOTE-VERIFIER-NOT-ESTABLISHED)`，其 `level` 為 `warn`、detail 以 `[warn]` 起頭並含 `dec` 筆數 2 與字樣 `引言回查屬 P2`；`overall` 為 `PASS`、rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_4_E_2]"
```

```gherkin
# AT-108-4-E-3
# 對應 AC: AC-108-4（PRD AC-SI-08-4 ③；R37 讀取側防禦、R38）型別怪異的手寫事件（欄位值為陣列）使 `events.structure` 恰報 `EVENT-TYPE`，`check` 其餘項目照常產出、不得拋例外
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git + subprocess（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_108_4_E_3 -q -p no:xdist -o addopts=

Feature: 型別怪異的事件不使 check 崩潰

Scenario: 欄位值為陣列的四型事件各被判 EVENT-TYPE，其餘項目照常產出
  Given 依 §5.2 情境 `SC-WEIRD` 建四份事件帳本複本 `W1`～`W4`：`seq` 為 1 的合規 `run.open`（`RUN-SI-001`），其後 `seq` 為 2 的一筆怪異事件——`W1` 為 `reason` 是 JSON 陣列的 `research.skip`、`W2` 為 `type` 是 JSON 陣列的 `attr`、`W3` 為 `obs` 的元素是陣列的 `attr`、`W4` 為 `att` 是 JSON 陣列的 `attr.confirm`
  When 對四份各以子行程（§5.5 (d)）呼叫 `check --json`，擷取 rc、stdout 與 stderr
  Then 四份：rc 皆為 `1`、stderr 不含 `Traceback`；stdout 為單一 JSON 文件，`items` 為 28 項且每項都有 `status`
  And 四份：`S(events.structure)` 為 `FAIL`，`F(events.structure)` 恰為 `(seq=2, EVENT-TYPE)`
  And 四份：怪異事件對折疊沒有貢獻——`F(events.transitions)` 不含 `TRANSITION-ILLEGAL` 與 `TRANSITION-ORPHAN`，`events.research` 與 `events.vacuity` 兩項的 `status` 皆已產出
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_4_E_3]"
```

```gherkin
# AT-108-4-E-4
# 對應 AC: AC-108-4（PRD AC-SI-08-4 ③；R31、R37）事件欄位值域的 check 層負控：`note` 長度、`http_status` 範圍、`research.skip` 的 `by`、`sid` 正規形、事件行位元組上限的邊界
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_108_4_E_4 -q -p no:xdist -o addopts=

Feature: 事件欄位值域的負控

Scenario: 值域邊界內放行，越界判 EVENT-TYPE 或 EVENT-BYTES-OVER
  Given 基線 `R`（`min_events` 為 1、`event_max_bytes` 為 §5.1 初值）；除 (e) 外，每個案例各自在乾淨的事件帳本寫入 `seq` 為 1 的合規 `run.open`（`RUN-SI-001`）加 `seq` 為 2 的一筆案例事件
  When (a) `research.skip`（`offline`）的 `note` 為 120 字元、121 字元；`attr.reject` 的 `note` 同樣各一案
  And (b) `research.scan`（`by` 為 `researcher`，其餘鍵合規）的 `sources[0].http_status` 為 199、200、299、300
  And (c) `research.skip` 的 `by` 為 `main`、`researcher`、`SA`
  And (d) `research.skip`（`reason` 為 `helmsman`、`line` 為 3）的 `sid` 為小寫正規形 UUID、去掉連字號的 32 位 hex、以大括號包住的正規形、加 `urn:uuid:` 前綴的正規形
  And (e) 事件帳本只有 `seq` 為 1 的 `run.open`；測試端量得該行的位元組數 `L`（不含結尾 LF）；兩份 `R` 的 `event_max_bytes` 分別設為 `L` 與 `L－1`（行長比上限多 1）
  Then 對各案例呼叫 `check --json`：(a) 的 `note` 為 120 字元時 `S(events.structure)` 為 `PASS`、為 121 字元時 `F(events.structure)` 恰為 `(seq=2, EVENT-TYPE)`（`research.skip` 與 `attr.reject` 兩種事件各同）
  And (b) 的 199 與 300 各恰為 `(seq=2, EVENT-TYPE)`，200 與 299 為 `PASS`；(c) 的 `main` 為 `PASS`，`researcher` 與 `SA` 各恰為 `(seq=2, EVENT-TYPE)`
  And (d) 的小寫正規形 UUID 為 `PASS`，其餘三種各恰為 `(seq=2, EVENT-TYPE)`
  And (e)：`event_max_bytes` 為 `L` 時 `S(events.structure)` 為 `PASS`，為 `L－1` 時 `F(events.structure)` 恰為 `(seq=1, EVENT-BYTES-OVER)`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_4_E_4]"
```

```gherkin
# AT-108-4-E-5
# 對應 AC: AC-108-4（PRD AC-SI-08-4 ⑤；R38、R42 (d)）引言回查未建的 warn 層級提示之邊界：單一 `dec`、單一 `helmsman` 免掃即印，零筆不印；warn 不改項目狀態、不影響 rc
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_108_4_E_5 -q -p no:xdist -o addopts=

Feature: 引言回查未建提示的邊界

Scenario: 一筆即印、零筆不印，warn 不改狀態與 rc
  Given 基線 `R`；四份事件帳本複本各自手寫：(a) `run.open`、`research.skip`（`offline`）、一個 `proposed` 的 `prop`、恰一筆 `dec`（`dkind` 為 `approve`）；(b) 同 (a) 但沒有 `dec`；(c) `run.open` 加一筆 `research.skip`（`reason` 為 `helmsman`、`sid` 為正規形 UUID、`line` 為 3）；(d) `run.open` 加一筆 `research.skip`（`offline`）
  When 對四份各呼叫 `check --json`
  Then (a)：`S(events.transitions)` 為 `PASS`，`F(events.transitions)` 恰為 `(-, QUOTE-VERIFIER-NOT-ESTABLISHED)`；該 finding 的 `level` 為 `warn`，detail 以 `[warn]` 起頭、含 `dec` 筆數 1 與字樣 `引言回查屬 P2`
  And (b)：`F(events.transitions)` 為空
  And (c)：`S(events.research)` 為 `PASS`，`F(events.research)` 恰為 `(-, QUOTE-VERIFIER-NOT-ESTABLISHED)` 且其 `level` 為 `warn`；(d)：`F(events.research)` 為空
  And (a) 的 `events.transitions` 與 (c) 的 `events.research` 皆不是 NE（`blocking` 為 false）；(c) 與 (d) 的 `overall` 皆為 `PASS`、rc 皆為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_4_E_5]"
```

```gherkin
# AT-142-1-1
# 對應 AC: AC-142-1（本檔自增；PRD §9.3 `check` 列；R36、R46 (c)）`check` 在 21 項之後追加 7 項（共 28），載體缺席一律 nonblocking NE，合法事件帳本使追加項轉 PASS
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_142_1_1 -q

Feature: check 的 P1 追加項

Scenario: P0 基線 repo 的追加項皆為未判（不影響 rc）；以 CLI 走完一輪後追加項轉 PASS
  Given 情境一：`R＝make_p1_repo()`（OBS 列 001～010、無事件帳本、無來源表）
  And 情境二：在情境一的 repo 上以 CLI 走完一輪（`run-open`、`research --skip --reason offline`、`attr`（root）、`attr-confirm`、`prop-new`、`run-close`）後提交
  When 對兩個情境各呼叫 `check --json`；情境一另呼叫文字形態
  Then 情境一：rc 為 `0`、`overall` 為 `PASS`、`rows` 為 `10`；`items` 為 28 個物件，前 21 個的 `id` 依序等於夾具常數 `P0_ITEMS21`、後 7 個依序為 `events.structure`、`events.transitions`、`events.mutated`、`events.vacuity`、`events.prop_files`、`events.research`、`research.sources`
  And 情境一：後 7 項的 `status` 皆為 `NE`、`blocking` 皆為 false、各恰一個 finding 且碼為 `CARRIER-NOT-ESTABLISHED`；前 21 項中 `ref.carrier_families` 為 `NE`（nonblocking），其餘 20 項皆為 `PASS` 且 findings 為空；`fingerprint_parts.check_rules_rev` 為 `2`
  And 情境一的文字形態：首行為 `si-check rows=10 items=28`，每個項目各一行且狀態與 JSON 一致，最後一個非空行以 `overall=PASS rc=0 fingerprint=sha256:` 起頭；沒有 OBS 草稿列；每個 `items` 元素的鍵序與前 21 項的鍵序相同
  And 情境二：rc 為 `0`、`overall` 為 `PASS`；六個 `events.*` 項皆為 `PASS` 且 findings 為空；`research.sources` 仍為 `NE`（nonblocking、`CARRIER-NOT-ESTABLISHED`）；`ref.carrier_families` 仍為 `NE`（nonblocking；事件帳本與提案檔提及 `RUN-SI`、`ATT-SI`、`PROP-SI` 家族）；其餘各項與情境一相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_142_1_1]"
```

```gherkin
# AT-142-1-E-1
# 對應 AC: AC-142-1（本檔自增；R41、R43、R36）`events.prop_files` 抓出內容檔缺失與雜湊不符；`research.sources` 接上來源表驗證；CRLF 的正規化規則（`.md` 換行不計、`.patch` 位元組原樣）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_142_1_E_1 -q

Feature: 提案內容檔與來源表的 check 判定

Scenario: 內容檔與事件互驗，被竄改即紅；來源表驗證經 check 接線
  Given 基線 `R`，以 CLI 建一個合規 PROP（`PROP-SI-124`，內容檔 `r1.patch`、`r1.md` 存在），提交；每個情境各自複製再變異
  When 情境一：(a) 刪 `r1.patch`；(b) 刪 `r1.md`；(c) 在 `r1.patch` 末尾加一行；(d) 把 `r1.md` 欄位表的 `symptom` 值改字；(e) 把 `r1.md` 整檔轉為 CRLF；(f) 把 `r1.patch` 整檔轉為 CRLF；(g) 把事件帳本中該 `prop` 行的 `touched_sha256` 換成另一個合法形態的雜湊字串；(h) 把該行的 `touched_count` 加一
  And 情境二（來源表經 `check` 接線；各自提交後呼叫）：(a) 合規來源表（一筆，`id` 為 `a-src`，`url` 為 `https://example.com/x.md`）；(b) 同表但 `schema_rev` 為 2；(c) 同表但開頭加 BOM
  Then 情境一的 `F(events.prop_files)`（subject 皆為 `PROP-SI-124 r1`）：(a)(b) 恰為 `PROP-FILE-MISSING`（只有缺的那個檔）；(c) 恰為 `PROP-PATCH-SHA-MISMATCH`；(d) 恰為 `PROP-BODY-SHA-MISMATCH`；(e) 為空（`S(events.prop_files)` 為 `PASS`）；(f) 恰為 `PROP-PATCH-SHA-MISMATCH`；(g)(h) 恰為 `PROP-TOUCHED-MISMATCH`
  And 情境二：(a) `S(research.sources)` 為 `PASS`；(b) `F(research.sources)` 恰為 `(schema_rev, SRC-SCHEMA)`（subject 依實作取欄名，碼不變）；(c) 含 `SRC-FILE-FORMAT`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_142_1_E_1]"
```

```gherkin
# AT-142-1-E-2
# 對應 AC: AC-142-1（本檔自增；PRD AC-SI-30-4 ③；R44）標記鍵詞彙加 `src`；`回報者=研究者` 的列須帶外部衍生與 `src`；`src` 須在來源表內（含 retired）
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_142_1_E_2 -q

Feature: 研究者候選列的標記判準

Scenario: 研究者列、src 值與來源表三方對得上才通過
  Given 基線 `R` 加已提交的來源表（兩筆：`cc-note` 現役、`old-src` 帶 `retired: true`）；每個情境各自追加一列新 OBS 列（ID 取 011，處置 `open`，證據座標取 `tools/lib/selfimproving/fresh.py:1`（與任何已結列的路徑無交集，使復發候選提示不介入）），其標記如下
  When (a) `面=流程;來源=代理;回報者=研究者;外部衍生=是;src=cc-note`；(b) `面=流程;來源=代理;回報者=研究者;src=cc-note`；(c) `面=流程;來源=代理;回報者=研究者;外部衍生=是`
  And (d) `面=流程;來源=代理;回報者=SA;src=zz-unknown`；(e) `面=流程;來源=代理;回報者=SA;src=old-src`；(f) `面=流程;來源=代理;回報者=SA;src=Bad_Id`；(g) `面=流程;來源=代理;回報者=SA;foo=1`
  And (h) 把來源表刪除後，列帶 `src=cc-note`
  Then (a) 與 (e)：`F(row.provenance)` 與 `F(row.markers)` 皆不含該列的任何 finding（`src` 已入詞彙；retired 的 `id` 仍被認得）
  And (b)：`F(row.provenance)` 恰為 `(OBS-SI-011, RESEARCHER-NOT-EXTERNAL)`；(c)：恰為 `(OBS-SI-011, RESEARCHER-NO-SRC)`
  And (d)：`F(row.markers)` 恰為 `(OBS-SI-011, SRC-UNKNOWN)`；(f)：含 `(OBS-SI-011, MARK-VALUE)` 且不含 `SRC-UNKNOWN`；(g)：恰為 `(OBS-SI-011, MARK-UNKNOWN-KEY)`（P0 判準不變）
  And (h)：`S(row.markers)` 為 NE、`blocking` 為 true、碼 `SOURCE-UNAVAILABLE`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_142_1_E_2]"
```

```gherkin
# AT-142-2-1
# 對應 AC: AC-142-2（本檔自增；PRD §9.3「21 項原樣保留」；R36 (a)(c)）P0 基線 repo 在 P1 下：前 21 項的 id、順序、狀態、碼與 P0 相同，rc 與 overall 不變
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_142_2_1 -q

Feature: P0 判準不退化

Scenario: P0 基線的前 21 項逐項與 P0 的斷言相同
  Given 基線 `R＝make_p1_repo()`；夾具常數 `P0_ITEMS21`（21 個項目 ID，依 P0 判定碼表逐字抄入）
  When 呼叫 `check --json`；另把帳本整檔轉為 CRLF 後再呼叫一次
  Then 兩次的 rc 皆為 `0`、`overall` 皆為 `PASS`；前 21 個 `items` 的 `id` 依序等於 `P0_ITEMS21`
  And 前 21 項：`ref.carrier_families` 為 `NE`（nonblocking、碼 `CARRIER-NOT-ESTABLISHED`、detail 為 `families=PROP-SI count=1`）；其餘 20 項皆為 `PASS` 且 findings 為空，其中 `history.migration` 的項目層 detail 為 `claim=none`、`history.row_mutated` 為 `PASS`（基線兩個 commit 之間只有 open 轉終值一次，屬放行集合）
  And CRLF 轉換前後前 21 項的 `status` 序列相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_142_2_1]"
```

```gherkin
# AT-142-2-E-1
# 對應 AC: AC-142-2（本檔自增；R36 (a)(c)、R67）P0 的紅燈碼在 P1 下不變；非 git 目錄的未判型態與 rc 表不變；P0 測試檔的 R67 同步有靜態證據
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_142_2_E_1 -q

Feature: P0 負控在 P1 下仍同碼

Scenario: 代表性的 P0 變異得到與 P0 相同的碼，非 git 目錄的未判型態不變
  Given 基線 `R＝make_p1_repo()`；每個情境各自複製再變異
  When (a) 刪掉帳本檔頭的 tz 宣告；(b) 把列 003 的 `分類` 清成空白；(c) 把列 004 的 `嚴重度` 改成 `P0`；(d) 把列 004 的證據座標改成 `本檔時間欄`
  And (e) 在工作樹把已提交的列 005 的症狀改字；(f) 自 `params.json` 刪去鍵 `row_max_bytes`
  And (g) 把 `R` 複製成不含 `.git` 的目錄後呼叫 `check --json`；(h) 呼叫 `check --ledger <不存在的檔>`
  And (i) 以 `ast` 與原始碼文字唯讀讀取 P0 的 `tools/tests/test_selfimproving_check.py`，檢查 R67 列出的五處站點是否已同步
  Then (a)：`F(ledger.time_tz)` 恰為列 001～008 與列 010 各一筆 `TIME-NO-TZ`；(b)：`F(row.required)` 恰為 `(OBS-SI-003, FIELD-EMPTY)`；(c)：`F(row.enums)` 含 `(OBS-SI-004, ENUM-SEVERITY)`；(d)：`F(row.coordinates)` 恰為 `(OBS-SI-004, COORD-NONE)`
  And (e)：`F(history.row_mutated)` 恰為 `(OBS-SI-005, ROW-MUTATED)`，detail 含 `commit=WORKTREE` 與字樣 `掌舵者`；(f)：`F(params.keys)` 含 `(row_max_bytes, PARAM-MISSING)`，且依賴該鍵的項目為 NE（blocking、`SOURCE-UNAVAILABLE`）
  And (g)：rc 為 `2`；前 21 項中恰 17 項 `PASS`、恰 4 項為 blocking NE，後 7 項皆為 nonblocking NE；(h)：rc 為 `3`、stdout 空、stderr 至少一行
  And (i)：首行斷言的字串含 `items=28` 而不含 `items=21`；`test_AT_003_1_1_no_resident_mechanism` 內的字串常數含 `decide` 與 `promote`、不含 `prop-new`；`test_AT_030_1_E_1_usage_errors` 內的字串常數含 `decide`；`params_dict()` 的回傳 dict 字面值鍵集合含五個新鍵；`test_AT_030_2_1_purity` 的靜態段引用 `CAPABILITY`（自能力登記表衍生）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_142_2_E_1]"
```

```gherkin
# AT-140-1-1
# 對應 AC: AC-140-1（本檔自增；PRD §9.3 動詞表；R27）13 個動詞皆可呼叫，求助輸出、`--repo` 檢查與 rc 0 路徑
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_140_1_1 -q

Feature: 命令列介面與 rc 表

Scenario: 十三個動詞都能被呼叫；--repo 非目錄一律 rc 3；求助輸出列出全部動詞
  Given 基線 `R`；動詞集合為 `check`、`status`、`scan`、`card`、`export`、`run-open`、`run-close`、`attr`、`attr-confirm`、`attr-reject`、`prop-new`、`prop-revise`、`research`
  When 情境一：呼叫 `--help` 與每個動詞的 `<verb> --help`
  And 情境二：對 `R` 依序呼叫：`run-open`、`research --skip --run RUN-SI-001 --reason offline --note 離線驗證`、`attr --type root`、`attr-confirm --att ATT-SI-001 --by QA`、`attr --type link`、`attr-reject --att ATT-SI-002 --by QA --note 證據不足`、`prop-new`（旗標取 §5.3 `good_prop_args(R)`）；再手寫一筆 `dec`（`dkind` 為 `return`）使該 PROP 成為 `returned`；呼叫 `prop-revise --run RUN-SI-001 --prop PROP-SI-124 …`、`status`、`scan`、`card PROP-SI-124`、`export --json --kind status`、`check`、`run-close --run RUN-SI-001 --by main`
  And 情境三：對十三個動詞各以一組其餘合規的旗標，加 `--repo` 指向一個普通檔案與一個不存在的路徑（`research` 取 `--skip` 形態）
  Then 情境一：`--help` 與每個 `<verb> --help` rc 皆為 `0`、usage 走 stdout；頂層 usage 含全部 13 個動詞名；`prop-new --help` 含 `--patch-file`、`export --help` 含 `--kind`、`research --help` 含 `--fetch` 與 `--skip`
  And 情境二：除 `check` 外的十二個動詞（`research` 取 `--skip`）各至少一次 rc 為 `0`；`check` 的 rc 為 `0`；唯讀動詞（`status`、`scan`、`card`、`export`）不改變 `snap(R)`
  And 情境三：26 次呼叫 rc 皆為 `3`、stdout 空、stderr 至少一行且以 `selfimproving:` 起頭
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_1_1]"
```

```gherkin
# AT-140-1-E-1
# 對應 AC: AC-140-1（本檔自增；R27、R28）P2 與 P3 的動詞、`card --issue`、未知旗標與未知動詞一律 rc 3；拒收輸出文法（文字與 JSON）與 OBS 草稿列內容
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_140_1_E_1 -q

Feature: 未實作動詞與拒收輸出文法

Scenario: 後續階段的動詞 rc 3；拒收輸出的行文法與草稿列欄位固定
  Given 基線 `R`；`snap0＝snap(R)`
  When 情境一：依序呼叫動詞 `decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`capacity`、`frobnicate`，另呼叫 `card PROP-SI-124 --issue`、`status --bogus`、`scan --since <執行期以今日日期組出的 ISO 日期字串>`（`--since` 只收 commit）、`scan --count 5`
  And 情境二：呼叫 `run-close --run <執行期組出的不存在運轉號> --by main`（文字形態與 `--json` 形態各一次）
  Then 情境一的十二次呼叫：rc 皆為 `3`、stdout 空、stderr 至少一行且以 `selfimproving:` 起頭；`snap(R)` 等於 `snap0`
  And 情境二文字形態：rc 為 `1`；stdout 依序為 `reject run-close RUN-NOT-OPEN`、一行 `  RUN-NOT-OPEN <detail>`、`obs-draft:`、恰一行草稿列
  And 情境二 JSON 形態：單一 JSON 物件，鍵序為 `ok`、`rc`、`verb`、`codes`、`obs_draft`，值為 false、1、`run-close`、`[{code, detail}…]`、草稿列字串
  And 草稿列拆成九欄後：ID 為 `OBS-SI-011`（帳本現有最大 ID 加一）、情境為 `si run-close（自動草稿）`、症狀以 `si run-close 拒收（rc=1）：` 起頭並含碼 `RUN-NOT-OPEN`、分類 `bug`、嚴重度 `P3`、處置 `open`、標記 `面=流程;來源=工具;回報者=si-run-close`、證據座標含反引號包住的 `python tools/selfimproving.py run-close` 與 `rc=1`；兩種形態的草稿列皆 `draft_ok` 成立；零殘留
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_1_E_1]"
```

```gherkin
# AT-140-1-E-2
# 對應 AC: AC-140-1（本檔自增；R27、R37 讀取側防禦）帳本含型別怪異事件時，讀取與寫入動詞皆不得以未捕捉的例外結束，rc 與輸出依各動詞既有規則
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + subprocess（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_140_1_E_2 -q -p no:xdist -o addopts=

Feature: 怪異事件之下的動詞不崩潰

Scenario: 四型怪異事件之下，各動詞照規格回 rc、stderr 不含 Traceback
  Given 依 §5.2 情境 `SC-WEIRD` 的四份複本 `W1`～`W4`（各含 `seq` 為 1 的 `run.open` `RUN-SI-001` 與 `seq` 為 2 的怪異事件）；`HOME` 為 tmp 家目錄；每個呼叫各自在一份新複本上進行（寫入動詞互不影響）；記下複本事件帳本的原位元組 `b0`
  When 以子行程（§5.5 (d)）逐一呼叫：`status`；`status --json`；`export --json --kind events`、`runs`、`proposals`、`status` 各一次；`run-close --run RUN-SI-001 --by main`；`attr-confirm --att <A> --by QA`（`<A>` 取怪異 `attr` 事件自己的 `id`，`W1` 與 `W4` 取 `ATT-SI-001`）；`research --skip --run RUN-SI-001 --reason offline --note x`
  Then 每個呼叫：stderr 不含 `Traceback`；`status`、`status --json` 與四個 `export` 的 rc 皆為 `0`，JSON 形態的 stdout 可被 `json.loads` 解析（`status --json` 的頂層鍵序同 R60）
  And `export --json --kind events`：`items` 含該怪異事件，且與帳本該行逐行 `json.loads` 的結果相等（事件原樣輸出，R61）
  And `run-close`：rc 為 `0`、stdout 為單行 `ok run.close seq=3 run=RUN-SI-001 no_event=true`（怪異事件不是該運轉的 `prop`）；`research --skip`：rc 為 `0`（怪異事件不算研究事件，即使 `W1` 本身是 `research.skip`）
  And `attr-confirm`：rc 為 `1`、`codes(out)` 恰為 `ATT-NOT-FOUND`（怪異事件不被折疊成 ATT，`W2` 與 `W3` 自己的 `id` 亦然）
  And 兩個寫入動詞成功之後，各自複本的事件帳本前兩行位元組逐字等於 `b0` 的兩行（只增不減）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_1_E_2]"
```

```gherkin
# AT-140-1-E-3
# 對應 AC: AC-140-1（本檔自增；R28 (d)）OBS 草稿列的症狀至多顯示 5 個碼，超過尾接 `…等 <k> 項`（k 為不重複碼的總數）；恰好 5 個不加尾綴
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_140_1_E_3 -q -p no:xdist -o addopts=

Feature: 草稿列的碼數上限

Scenario: 六個不同碼的拒收截為前五個加尾綴；五個碼全列、不加尾綴
  Given 基線 `R`（已提交）；執行期組出不存在的運轉號 `RX` 與不存在的 OBS 號 `SX`；旗標取 §5.3 `good_prop_args(R)`，另把 `--source` 覆寫為 `SX`、`--proposer` 為標籤 `SA`
  When 情境一（6 個碼）：`prop-new --run RX`，`--reviewer SA`（與提案者相同）並另帶 `--handoff T1`（導出為 `loop` 而給了通道）；情境二（5 個碼）：同情境一但不帶 `--handoff`；情境三（4 個碼）：再去掉 `--reviewer`
  Then 三個情境：rc 皆為 `1`；各自取拒收輸出首行 `reject prop-new` 之後所列的碼（依出現順序）為 `names`，三者長度依序為 6、5、4 且各自不重複；情境一的 `codes(out)` 恰為 `RUN-NOT-OPEN`、`RESEARCH-MISSING`、`SOURCE-UNRESOLVED`、`NO-INTERNAL-SOURCE`、`REVIEWER-IS-PROPOSER`、`HANDOFF-CHANNEL-UNEXPECTED`
  And `obs-draft:` 之下的草稿列，其症狀欄：情境一恰為 `si prop-new 拒收（rc=1）：` 接 `names` 的前 5 個（以頓號連接）再接 `…等 6 項`；情境二為同一前綴接全部 5 個碼、不含 `…等`；情境三接全部 4 個碼、不含 `…等`
  And 三個草稿列的 `draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_1_E_3]"
```

```gherkin
# AT-145-1-1
# 對應 AC: AC-145-1（本檔自增；PRD §9.1 C5、C16；R43、R46）真 `params.json` 含五個新鍵且合規；真來源表通過來源表驗證
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 repo 檔案）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_145_1_1 -q

Feature: 協定目錄的真檔案

Scenario: 真 params.json 與真 research_sources.json 合規
  Given 真 repo 的 `docs/06_quality/SelfImproving_Protocol/params.json` 與 `research_sources.json`（唯讀，不得被測試修改）
  When 解析兩個檔，並對真 repo 呼叫 `check --json`
  Then `params.json` 為 UTF-8（無 BOM）、LF、結尾換行，頂層鍵依位元組序遞增；含 `research_fetch_max`、`research_bytes_max`、`research_timeout_seconds`、`min_events`、`export_limit_max` 五鍵，皆為整數（非布林）且不小於 1
  And `check` 的 `params.keys`、`params.globs`、`params.coupling` 三項皆為 `PASS`
  And `research_sources.json` 的原始位元組經 `sources.validate_table(raw, sources.DEFAULT_POLICY)` 回傳空串列；`id` 依位元組序遞增；每筆的 `added_by` 非空；現役（未 `retired`）筆數不大於 `params.json` 的 `research_fetch_max`；`check` 的 `research.sources` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_145_1_1]"
```

```gherkin
# AT-145-1-E-1
# 對應 AC: AC-145-1（本檔自增；R46 (a)、R29）五個新鍵逐鍵缺失、型別錯、範圍錯各被判出；取不到鍵的動詞 rc 3
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_145_1_E_1 -q

Feature: 新增的 params 鍵

Scenario: 缺鍵、型別錯、範圍錯各判對應碼；消費該鍵的動詞在鍵無效時 rc 3
  Given 基線 `R`；五個鍵為 `research_fetch_max`、`research_bytes_max`、`research_timeout_seconds`、`min_events`、`export_limit_max`
  When 對每個鍵各複製一份基線，依序把 `params.json` 的該鍵：刪除、改成字串 `x`、改成浮點 `1.5`、改成布林 `true`、改成 `0`，各呼叫 `check --json`
  And 另對三個消費者各複製一份基線並使其鍵無效：`export --json --kind status` 搭 `export_limit_max` 缺失；`research --fetch --run RUN-SI-001`（事前以 CLI 開好運轉）搭 `research_fetch_max` 缺失；以含事件帳本的基線呼叫 `check --json` 搭 `min_events` 為 `0`
  Then 五個鍵各五種變異（共 25 個）：`S(params.keys)` 皆為 `FAIL`；`F(params.keys)` 恰為 `(<鍵名>, PARAM-MISSING)`、`(<鍵名>, PARAM-TYPE)`（字串、浮點、布林三種）、`(<鍵名>, PARAM-RANGE)`（`0`）
  And `export` 與 `research --fetch` 兩個呼叫：rc 皆為 `3`、stdout 空、stderr 點名該鍵；`research --fetch` 未發出任何連線、事件帳本不變
  And `min_events` 為 `0` 的 `check`：`S(events.vacuity)` 為 NE、`blocking` 為 true、碼 `SOURCE-UNAVAILABLE`，且 `S(params.keys)` 為 `FAIL`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_145_1_E_1]"
```

```gherkin
# AT-145-2-1
# 對應 AC: AC-145-2（本檔自增；PRD §9.1 C6；R65；代位）Operations SOP 定稿：四個角色節仍含「P1 定稿」並有實質內容、研究者節、研究事件條文與各代位條文的必備片段齊備
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP；以 `## ` 標題切段的關鍵片段判準）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_145_2_1 -q

Feature: Operations SOP 定稿（代位）

Scenario: 真 SOP 滿足 R65 (a) 至 (g) 的全部關鍵片段
  Given 真 repo 的 `docs/05_development/SelfImproving_Operations_SOP.md`（唯讀）；夾具函式 `sop_problems(text)` 回傳不滿足的片段清單（每項點名節與片段）；`text` 先將 CRLF 換成 LF
  When 呼叫 `sop_problems(<真 SOP 全文>)`，並取出四個角色節（標題含 `歸因者`、`提案者`、`審查者`、`凍結者`）與研究者節（標題含 `研究者`）各自的節文字
  Then 回傳空清單
  And 四個角色節各自含字面 `P1 定稿`，且各節（去掉含 `P1 定稿` 的那一行後）的非空白字元數大於零
  And 歸因者節含 R65 (b) 的全部片段：`attr`、`attr-confirm`、`attr-reject`、`根因鍵`、`NONE`、`無法歸因`、`確認者`、模組體檢任務書範本的各片段，與 PRD 模組體檢入口表第 2 欄的每個反引號片段（片段自真 PRD 現抽）
  And 提案者節含 R65 (c)、審查者節含 R65 (d)、凍結者節含 R65 (e)、研究者節含 R65 (f)、全文含 R65 (g) 的兩行研究事件條文
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_145_2_1]"
```

```gherkin
# AT-145-2-E-1
# 對應 AC: AC-145-2（本檔自增；R65；代位）SOP 判準的自證：每個必備片段刪去的副本須判不合格，同行條件被拆行、標題被改名也判不合格
# 測試類型: Unit
# 自動化工具: pytest（以真 SOP 全文的變異副本）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_145_2_E_1 -q

Feature: SOP 判準非恆真

Scenario: 刪去任一片段、拆開同行條件或改名標題都使判準回報該處不合格
  Given 真 SOP 全文（唯讀）與 `sop_problems`；R65 (a)～(g) 的全部必備片段清單 `FRAGMENTS`（由夾具自 R65 逐字承載）
  When 對 `FRAGMENTS` 的每個片段各產生一個副本：把該片段在其所屬節的首次出現處刪去
  And 對 R65 要求「同一行」的各組片段（歸因者節的理論洞條文與 evaluator-change 條文、提案者節的抽象化條文與不得再派條文、研究事件的兩行條文）各產生一個副本：把組內最後一個片段移到下一行
  And 另產生副本：把研究者節的標題改成不含 `研究者`；把任一角色節的 `P1 定稿` 字面刪去；把模組體檢任務書範本的子標題改成不含 `模組體檢`
  Then 每個副本的 `sop_problems` 都非空，且回報內容點名被動過的節與片段（子情境失敗訊息須指出是哪個片段）
  And 對真 SOP 全文本身 `sop_problems` 為空（正控）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_145_2_E_1]"
```

```gherkin
# AT-145-2-E-2
# 對應 AC: AC-145-2（本檔自增；R65 (b)(c)(g)）判準常數的獨立釘選：夾具的「同一行」片段組與 R65 的條文相等，改常數的任一元素即紅
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取夾具常數；以常數的突變副本自證）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_145_2_E_2 -q -p no:xdist -o addopts=

Feature: SOP 判準常數的釘選

Scenario: 同一行片段組常數與 R65 逐組相等，突變副本比對不相等
  Given 夾具常數 `SAME_LINE_GROUPS`（〔節名, 片段元組〕串列）與 `RESEARCH_EVENT_LINES`（片段元組串列）；期望值於測試內以字面獨立寫出（不由常數衍生、不呼叫 `line_has_all`），取自本檔 R65：歸因者節 `理論洞`、`P4`、`暴露證據`、`不立案`；歸因者節 `evaluator-change`、`evaluator_command`、`expected_output_regex`、`OBS`、`不得轉送沙盒`；提案者節 `抽象化`、`結果標籤`、`原始軌跡全文`；提案者節 `不得再派`、`提案者`、`審查者`；全文 `研究事件`、`research.scan`、`research.skip`、`prop-new`、`拒收`；全文 `quota-band`、`offline`、`helmsman`
  When 以集合語意（組與組之間、組內片段之間的順序不拘）比對常數與期望值；另對常數各產生突變副本：刪去任一組、刪去任一組內的任一片段、把任一片段改掉一個字、把某一組的節名換成另一節——各比對一次
  Then 原常數與期望值相等：`SAME_LINE_GROUPS` 恰四組、`RESEARCH_EVENT_LINES` 恰兩組
  And 每個突變副本與期望值比對皆為不相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_145_2_E_2]"
```

```gherkin
# AT-107-2-1
# 對應 AC: AC-107-2（PRD AC-SI-07-2；R65 (b)；代位）守衛面轉交且無暴露證據者一律登記為理論洞（P4）、不立案修復——SOP 歸因者節的條文
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_107_2_1 -q

Feature: 理論洞條文（代位）

Scenario: 歸因者節有同一行同時含理論洞、P4、暴露證據、不立案的條文
  Given 真 SOP 的歸因者節（標題含 `歸因者`；LF 正規化）
  When 以夾具函式 `line_has_all(section, 理論洞, P4, 暴露證據, 不立案)` 取符合的行
  Then 至少有一行同時含四個片段
  And 該行位於歸因者節內、不在程式碼圍欄內
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_2_1]"
```

```gherkin
# AT-107-2-E-1
# 對應 AC: AC-107-2（PRD AC-SI-07-2；R65 (b)；代位）理論洞條文判準的自證
# 測試類型: Unit
# 自動化工具: pytest（以真 SOP 全文的變異副本）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_107_2_E_1 -q

Feature: 理論洞條文判準非恆真

Scenario: 刪片段、拆行、換節的副本皆判不合格
  Given 真 SOP 全文（唯讀）與 `line_has_all`
  When 產生副本：四個片段各自在該條文行中刪去（四個副本）；把條文行的後半段移到下一行；把整行移到審查者節
  Then 每個副本的 `line_has_all(<歸因者節>, …)` 皆找不到符合的行
  And 正控：真 SOP 的歸因者節找得到
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_2_E_1]"
```

```gherkin
# AT-111-2-1
# 對應 AC: AC-111-2（PRD AC-SI-11-2；R65 (b)；代位）引擎演化提案涉及評估器者標 `evaluator-change`、記一筆 OBS、不得轉送沙盒——SOP 歸因者節的條文
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_111_2_1 -q

Feature: evaluator-change 條文（代位）

Scenario: 歸因者節有同一行同時含 evaluator-change、evaluator_command、expected_output_regex、OBS、不得轉送沙盒的條文
  Given 真 SOP 的歸因者節（LF 正規化）
  When 以 `line_has_all(section, evaluator-change, evaluator_command, expected_output_regex, OBS, 不得轉送沙盒)` 取符合的行
  Then 至少有一行同時含五個片段，且位於歸因者節內、不在程式碼圍欄內
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_111_2_1]"
```

```gherkin
# AT-111-2-E-1
# 對應 AC: AC-111-2（PRD AC-SI-11-2；R65 (b)；代位）evaluator-change 條文判準的自證
# 測試類型: Unit
# 自動化工具: pytest（以真 SOP 全文的變異副本）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events.py -k AT_111_2_E_1 -q

Feature: evaluator-change 條文判準非恆真

Scenario: 刪片段、拆行、換節的副本皆判不合格
  Given 真 SOP 全文（唯讀）與 `line_has_all`
  When 產生副本：五個片段各自在該條文行中刪去（五個副本）；把條文行的後半段移到下一行；把整行移到凍結者節
  Then 每個副本的 `line_has_all(<歸因者節>, …)` 皆找不到符合的行
  And 正控：真 SOP 的歸因者節找得到
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_111_2_E_1]"
```

```gherkin
# AT-102-1-1
# 對應 AC: AC-102-1（PRD AC-SI-02-1 的 `prop-new` 機械半；R53 (f)）任何類別的提案至少有 1 個內部來源即受理；DEF 列算內部來源
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_102_1_1 -q

Feature: prop-new 的內部來源前置檢查

Scenario: 一個內部來源加一個外部衍生來源即受理，四種類別皆然
  Given 基線 `R`（OBS 列 010 的標記含 `外部衍生=是`，列 001～009 不含）；缺陷帳本含執行期 DEF 號 `D1`；為每個提案各開一個運轉並補好研究事件（夾具 `open_run(R)`，依序得 `RUN-SI-001`～`RUN-SI-005`）；`memory_dir` 為 §5.3 的記憶目錄夾具
  When 對 M、P、R、D 四類各呼叫一次 `prop-new`，旗標取 §5.3 `good_prop_args(R, cls=<類別>)` 並把來源改成 `--source OBS-SI-001 --source OBS-SI-010`（M 類另帶 `--memory-dir <memory_dir>`）
  And 再對 D 類呼叫一次，`--target docs/notes/other.md`、來源為 `--source <D1> --source OBS-SI-010`（與前一次不同型）
  Then 五次 rc 皆為 `0`；各事件的 `cls` 依序為 `M`、`P`、`R`、`D`、`D`，`sources` 依旗標順序為兩個 ID（外部衍生來源照記在內）、`route` 皆為 `loop`
  And 五個事件的 `target` 皆為排序去重的路徑陣列；M 類事件另有 `preimage` 鍵、其餘類別沒有
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_102_1_1]"
```

```gherkin
# AT-102-1-E-1
# 對應 AC: AC-102-1（PRD AC-SI-02-1；R53 (f)）外部衍生列（含研究者候選）不得單獨充當任何類別提案的證據；來源須可解析
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_102_1_E_1 -q

Feature: prop-new 的來源拒收

Scenario: 只有外部衍生來源者、來源查無者被拒，零殘留
  Given 基線 `R` 加已提交的研究者候選列 OBS-SI-011（標記 `面=流程;來源=代理;回報者=研究者;外部衍生=是;src=cc-note`）與含 `cc-note` 的來源表；已開運轉並補好研究事件；`snap0＝snap(R)`；執行期組出不存在的 OBS 號 `OX` 與 DEF 號 `DX`
  When 情境一：對 M、P、R、D、`evaluator-change`、`loop-self` 六種 `--cls` 各呼叫 `prop-new --source OBS-SI-010`（後兩者加 `--handoff T1`；其餘旗標取 `good_prop_args`）
  And 情境二：`prop-new --cls D --source OBS-SI-011`；情境三：`prop-new --cls D --source OX --source DX`；情境四：`prop-new --cls D --source OBS-SI-001 --source OX`
  Then 情境一的六次與情境二：rc 皆為 `1`，`codes(out)` 皆恰為 `NO-INTERNAL-SOURCE`
  And 情境三：`codes(out)` 恰為 `SOURCE-UNRESOLVED` 與 `NO-INTERNAL-SOURCE`；情境四：恰為 `SOURCE-UNRESOLVED`
  And 全部呼叫後 `snap(R)` 等於 `snap0`（事件帳本與 `SelfImproving_Proposals/` 皆無新檔）；`draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_102_1_E_1]"
```

```gherkin
# AT-107-1-1
# 對應 AC: AC-107-1（PRD AC-SI-07-1；R52 (g)）patch 觸及不可進化面者整張轉交：`route=handoff:<通道>`、卡面標僅轉交、迴圈對目標零寫入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_1_1 -q

Feature: 不可進化面轉交

Scenario: 觸及守衛面的提案整張轉交，四種通道各一次，正式面零寫入
  Given 基線 `R`；為每個通道各開一個運轉並補好研究事件（四個運轉）；`snap0＝snap(R)`
  When 對通道 `DEF`、`R`、`T1`、`PRD` 各呼叫一次 `prop-new --cls P --action add --target .claude/hooks/new_guard_<通道小寫>.py --handoff <通道> …`，patch 新增兩個檔：該守衛面檔與 `docs/notes/clean_<通道小寫>.md`（後者不在不可進化面）
  And 對每個 PROP 呼叫 `card <PROP>`
  Then 四次 rc 皆為 `0`，事件的 `route` 依序為 `handoff:DEF`、`handoff:R`、`handoff:T1`、`handoff:PRD`；`touched_count` 皆為 `2`（整張轉交，不只轉交命中的檔）
  And 四張卡的第 1 行皆以 `｜僅轉交，本迴圈不套用` 結尾、第 5 行皆為 `決定：轉交 ／ 不轉交＋一句理由`
  And 全部呼叫後 `snap(R)` 與 `snap0` 的差異只有事件帳本與 `docs/06_quality/SelfImproving_Proposals/` 下的新檔；`.claude/hooks/new_guard_*.py` 與 `docs/notes/clean_*.md` 皆不存在於工作樹（迴圈對目標零寫入）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_1_1]"
```

```gherkin
# AT-107-1-E-1
# 對應 AC: AC-107-1（PRD AC-SI-07-1；R52 (g)、R27）提案者不得自填 loop；導出為 handoff 而缺通道、導出為 loop 而給通道皆拒收
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_1_E_1 -q

Feature: 轉交通道的拒收

Scenario: 沒有 route 旗標；通道與導出結果必須一致
  Given 基線 `R`、已開運轉並補好研究事件；`snap0＝snap(R)`
  When 情境一：`prop-new … --route loop`（其餘旗標取 `good_prop_args`）；`prop-new … --handoff X`（通道不在集合）
  And 情境二：patch 觸及守衛面（新增 `.claude/hooks/new_guard_x.py`）而不帶 `--handoff`；`--cls evaluator-change` 搭乾淨 patch 而不帶 `--handoff`
  And 情境三：乾淨 patch（只動 `target` 內檔案）而帶 `--handoff T1`
  Then 情境一的兩次：rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 情境二的兩次：rc 皆為 `1`，`codes(out)` 皆含 `HANDOFF-CHANNEL-MISSING`；情境三：rc `1`，`codes(out)` 恰為 `HANDOFF-CHANNEL-UNEXPECTED`
  And 全部呼叫後 `snap(R)` 等於 `snap0`；rc 為 `1` 的呼叫其 `draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_1_E_1]"
```

```gherkin
# AT-107-3-1
# 對應 AC: AC-107-3（PRD AC-SI-07-3；R51 (a)(b)）`touched` 自 patch 的全部路徑標頭導出（聯集、排序、去重）；`git apply --numstat` 超集檢查通過
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_3_1 -q

Feature: touched 導出

Scenario: 各種標頭形態導出的 touched 恰為預期聯集，且只動目標內檔案者導出為 loop
  Given 基線 `R`（含 §5.3 的 `docs/notes/` 夾具檔）；每個案例各自複製一份已開運轉並補好研究事件的 `R`（夾具 `fresh(R0)`），避免同型去重與運轉預算互相干擾
  When 對 §5.3 表 `TOUCH-CASES` 的 T01～T10 各建出其 patch，呼叫 `prop-new --cls D --action modify --target <表中的 target> …`
  Then 十個案例 rc 皆為 `0`、事件的 `route` 皆為 `loop`；事件的 `touched_count` 等於表中預期集合的大小
  And 事件的 `touched_sha256` 等於 `sha256:` 接預期集合（排序去重後以緊湊 JSON 輸出：`ensure_ascii` 為假、逗號與冒號後不加空白）的 UTF-8 位元組之 sha256（測試端獨立計算，不呼叫被測碼）
  And `r1.patch` 的位元組逐字等於輸入的 patch 檔（含 T09 的 TAB 與時間戳尾段）；T04（純改名）與 T06（複製）的預期集合含新舊兩端；T10 把兩個檔案區塊的順序顛倒後，`touched_sha256` 與原順序相同
  And 全部案例都沒有 `PATCH-PATH-MISMATCH`（git 看到的路徑皆在解析器聯集之內）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_3_1]"
```

```gherkin
# AT-107-3-E-1
# 對應 AC: AC-107-3（PRD AC-SI-07-3；R52 (a)(g)）patch 的任一路徑命中不可進化面（含大小寫變體、純改名來源端）即整張 handoff
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_3_E_1 -q

Feature: 不可進化面的全路徑比對

Scenario: 夾帶任一不可進化路徑即整張轉交，乾淨 patch 對照組走 loop
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When 對 §5.3 表 `HANDOFF-CASES` 的 H01～H15 各建出 patch（每個 patch 含該表指定的命中路徑，另含乾淨檔 `docs/notes/clean_x.md`），呼叫 `prop-new --cls D --action add --handoff T1 …`
  And 對照組 C01：patch 只新增 `target` 內的乾淨檔，不帶 `--handoff`
  Then H01～H15 每案 rc 皆為 `0`，事件的 `route` 皆為 `handoff:T1`，`touched_count` 皆為 2（整張轉交）
  And C01：rc 為 `0`，事件的 `route` 為 `loop`
  And H15（純改名，命中路徑只在改名來源端）與 H14（大小寫變體）也被轉交（來源端與 `casefold` 後比對皆計入）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_3_E_1]"
```

```gherkin
# AT-107-3-E-2
# 對應 AC: AC-107-3（PRD AC-SI-07-3；R51 (b)(c)、R49 (a)）路徑別名形態（逃逸、絕對、磁碟機代號、資料流、尾端點與空白、保留裝置名、控制字元、反斜線）整張轉交；git 看見而解析器漏掉者拒收；`--target` 別名形態 rc 3
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_3_E_2 -q

Feature: 路徑別名形態

Scenario: 別名形態 fail-closed 轉交；解析器聯集漏路徑時拒收
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`；磁碟機代號形態的路徑於執行期以字串相加組出（測試原始碼不含磁碟機代號開頭的路徑字面）
  When 情境一：對 §5.3 表 `ALIAS-CASES` 的 A01～A11 各建出 patch（新增該別名路徑一個檔，另含乾淨檔 `docs/notes/clean_x.md`），呼叫 `prop-new --cls D --action add --handoff T1 …`
  And 情境二：乾淨 patch 搭 `mock.patch.object(git, apply_numstat, …)`，回傳串列含一個不在 patch 標頭內的路徑 `docs/notes/unlisted.md`；對照組：不加 mock
  And 情境三：`--target` 依序為 `../x.md`、`docs/../x.md`、以 `/` 起頭的絕對路徑、執行期組出的磁碟機代號形態
  Then 情境一：A01～A11 每案 rc 皆為 `0`、事件的 `route` 皆為 `handoff:T1`、`touched_count` 皆為 2
  And 情境二：加 mock 時 rc 為 `1`、`codes(out)` 恰為 `PATCH-PATH-MISMATCH`、零殘留；不加 mock 的對照組 rc 為 `0`
  And 情境三：四次 rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_3_E_2]"
```

```gherkin
# AT-107-3-E-3
# 對應 AC: AC-107-3（PRD AC-SI-07-3、AC-SI-11-1；R52 (b)～(f)）`R-*.yaml` 內容條件式、LATEST 注入與解析失敗 fail-closed、規格本體路徑與 SPEC-PATCH 草案例外、`cls` 自動標記、M 類合法根
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_3_E_3 -q

Feature: 不可進化面的條件式與標記

Scenario: 條件式命中、LATEST 現查、規格本體、cls 標記與合法根各依規則導出 route
  Given 基線 `R`（含 §5.1 的規則檔夾具：`<VNEW>` 下 `R-9.1.yaml` 為 `maturity: active`、`R-9.2.yaml` 為 `maturity: proposed`、`R-9.3.yaml` 無 `maturity` 鍵）；每個案例各自複製一份已開運轉並補好研究事件的 `R`；旗標取 `good_prop_args`（預設 `--cls D --action modify`，`--target` 取 patch 的第一個路徑，M 類帶 `--memory-dir`，各情境另有指明者從其指明），預期為 `handoff:*` 的案例另帶 `--handoff T1`、預期為 `loop` 的案例不帶
  When 情境一（規則檔）：各建 patch 觸及 `R-9.1.yaml`、`R-9.2.yaml`、`R-9.3.yaml`（修改既有檔），另一案新增 `R-9.9.yaml`（含 `trust_level: proposed`，`--cls R`）
  And 情境二（LATEST）：patch 觸及 `AISDLC_SDD/<VNEW>/agent/x.md` 與 `AISDLC_SDD/<VOLD>/agent/x.md`（各一案）；再把 `R` 的 `AISDLC_SDD/scripts/sdd_version.py` 刪除後重做 `<VNEW>` 路徑一案
  And 情境三（規格本體）：patch 觸及 `docs/01_requirements/Some.md`；新增 `docs/01_requirements/SPEC-PATCH-demo.md` 且 `--cls D --action add`（唯一觸及路徑）；同一 patch 但 `--cls P`；同一 patch 另加第二個檔；同一 patch 但 `--action modify`
  And 情境四（cls 標記）：`--cls P` 搭觸及 `docs/06_quality/SelfImproving_Protocol/params.json` 的 patch；搭觸及 `tools/lib/selfimproving/x.py` 的 patch；搭兩者皆觸及的 patch；`--cls loop-self` 搭乾淨 patch（皆加 `--handoff T1`）
  And 情境五（M 類合法根）：`--cls M --target memory/demo.md` 且 patch 路徑為 `memory/demo.md`；同一提案但 patch 路徑為 `docs/notes/demo.md`
  Then 情境一：`R-9.1.yaml` 與 `R-9.3.yaml`（讀不出 `maturity`）整張轉交；`R-9.2.yaml` 為 `loop`；新增的 `R-9.9.yaml` 為 `loop`
  And 情境二：`<VNEW>` 路徑為 `loop`（LATEST 不屬凍結）、`<VOLD>` 路徑為 `handoff:T1`；刪去解析腳本後 `<VNEW>` 路徑也為 `handoff:T1`（fail-closed、不當機）
  And 情境三：規格本體路徑為 `handoff:T1`；SPEC-PATCH 草案例外那一案為 `loop`；其餘三案（類別不符、多一個檔、動作不符）皆為 `handoff:T1`
  And 情境四：事件的 `cls` 依序為 `evaluator-change`、`loop-self`、`evaluator-change`（兩群皆命中取前者）、`loop-self`（自填值保持），`route` 皆為 `handoff:T1`
  And 情境五：第一案 `route` 為 `loop`；第二案（逃出合法根 `memory/`）為 `handoff:T1`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_3_E_3]"
```

```gherkin
# AT-107-3-E-4
# 對應 AC: AC-107-3（PRD AC-SI-07-3；R51 (b)、R49 (b)）`git apply --numstat -z` 自身失敗（損毀的 hunk、context-diff 等 git 不收的格式）⇒ 拒收 `PATCH-PARSE`（fail-closed），不得把失敗當成 git 沒看到路徑而放行
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_107_3_E_4 -q -p no:xdist -o addopts=

Feature: 超集檢查失敗即拒收

Scenario: git 無法解析的 patch 一律 PATCH-PARSE，合法 patch 不受影響
  Given 基線 `R`（已開運轉 `RUN-SI-001`、含研究事件；每個情境各自複製一份）；兩份 git 會以 rc 非 0 拒絕、而自寫解析器仍導出路徑的 patch（位元組以 `\n` 分行）：(a) 損毀的 hunk——`diff --git a/docs/notes/demo.md b/docs/notes/demo.md`、`--- a/docs/notes/demo.md`、`+++ b/docs/notes/demo.md`、`@@ -3,5 +3,5 @@`（宣告各 5 行）、`-line 003`、`+line 003 changed`（只給各 1 行）；(b) context-diff 格式——`*** a/docs/notes/demo.md`、`--- b/docs/notes/demo.md`、`***************`、`*** 3 ****`、`! line 003`、`--- 3 ----`、`! line 003 changed`
  When 情境一：對 (a)、(b) 各呼叫 `prop-new --run RUN-SI-001`（類別 `D`、`--target docs/notes/demo.md`，其餘旗標取 §5.3 `good_prop_args(R, "D")`，patch 檔內容換成該份位元組）
  And 情境二：在 `mock.patch.object(git, "apply_numstat", side_effect=OSError("x"))` 之下，以 §5.3 `T01` 的合規 patch 呼叫同一個 `prop-new`
  And 情境三（對照）：不 mock，以 §5.3 `T01` 的合規 patch 呼叫同一個 `prop-new`
  Then 情境一的兩案與情境二：rc 皆為 `1`、`codes(out)` 恰為 `PATCH-PARSE`、事件帳本位元組不變、`SelfImproving_Proposals/` 下沒有新檔（零殘留）、`draft_ok` 成立
  And 情境三：rc 為 `0`，事件帳本多一筆 `prop`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_107_3_E_4]"
```

```gherkin
# AT-108-1-1
# 對應 AC: AC-108-1（PRD AC-SI-08-1；R49、R55）任何來源的改進一律登記為 `PROP-SI-NNN`、初始 `proposed`；R 類 `target` 為草案座標；產生者不寫正式面
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_108_1_1 -q

Feature: PROP 登記

Scenario: prop-new 受理後折疊狀態為 proposed，只多事件帳本與提案內容檔
  Given 基線 `R`（已提交）；已開運轉並補好研究事件；`snap0＝snap(R)`
  When 呼叫 `prop-new`（R 類：新增 `AISDLC_SDD/<VNEW>/governance/rules/R-9.9.yaml`，內容含 `trust_level: proposed`；旗標取 `good_prop_args(R, cls=R)`），再對 P 類呼叫一次（不同型）
  And 呼叫 `status --json`
  Then 兩次 rc 皆為 `0`；`prop` 事件的鍵集合恰為 R31 的 `prop` 欄位表（不含 `preimage`）；`id` 依序為 `PROP-SI-124`、`PROP-SI-125`，`rev` 皆為 `1`
  And `MJ(status)` 的 `pending_props` 含兩個 PROP，`state` 皆為 `proposed`；R 類的 `target` 為草案檔座標 `AISDLC_SDD/<VNEW>/governance/rules/R-9.9.yaml`
  And `snap(R)` 與 `snap0` 的差異只有事件帳本與 `docs/06_quality/SelfImproving_Proposals/` 下的新檔；草案檔 `R-9.9.yaml` 與 P 類的 `target` 檔皆未被產生或改動（正式面零寫入）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_1_1]"
```

```gherkin
# AT-108-1-E-1
# 對應 AC: AC-108-1（PRD AC-SI-08-1；R49 (b)、R28）輸入類錯誤（階段一）收到即回；旗標缺漏 rc 3；審查者不得等於提案者；拒收零殘留
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_108_1_E_1 -q

Feature: prop-new 的輸入拒收

Scenario: 空、二進位、無法解析的 patch 與不合骨架的本文被拒；階段一不進階段二
  Given 基線 `R`；已開運轉並補好研究事件；`snap0＝snap(R)`；另備「未開的運轉號」`RX`（執行期組出）
  When 情境一（rc 3）：缺 `--patch-file`、缺 `--body-file`、缺 `--proposer`、缺 `--source`、`--cls Z`
  And 情境二（階段一，`--run RX` 與其他政策錯誤同時存在以驗證收到即回）：patch 為 0 位元組；patch 含 `GIT binary patch` 字樣；patch 為純文字 `this is not a patch`；patch 標頭含無法解碼的 C-style 跳脫（`"a/docs/\xyz"`）；patch 標頭路徑的八進位位元組不是合法 UTF-8；本文缺 `## 影響面` 標題
  And 情境三（階段二）：`--reviewer SA --proposer SA`
  Then 情境一：五次 rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 情境二：依序的 `codes(out)` 恰為 `PATCH-EMPTY`、`PATCH-BINARY`、`PATCH-PARSE`、`PATCH-PARSE`、`PATCH-PARSE`、`BODY-SKELETON`（皆不含 `RUN-NOT-OPEN`，因階段一收到即回）；情境三：`codes(out)` 含 `REVIEWER-IS-PROPOSER`
  And 全部呼叫後 `snap(R)` 等於 `snap0`；rc 為 `1` 的呼叫其 `draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_1_E_1]"
```

```gherkin
# AT-108-2-1
# 對應 AC: AC-108-2（PRD AC-SI-08-2；R34、R49 (c)）`prop-revise` 只在 returned 狀態受理；沿用前一版的類別、動作、目標與來源；不計入運轉預算
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_108_2_1 -q

Feature: PROP 修訂

Scenario: returned 的 PROP 可修訂，修訂後回到 proposed
  Given 基線 `R`；以 CLI 建立 `PROP-SI-124`（P 類、`rev` 為 1），再手寫一筆 `dec`（`dkind` 為 `return`）使其為 `returned`；同一運轉內另有兩個不同型的 PROP（共 3 個，已達 `max_proposals_per_run`）
  When 呼叫 `prop-revise --run <該運轉> --prop PROP-SI-124 --patch-file <新 patch> --body-file <新本文> --proposer SA`
  Then rc 為 `0`、stdout 為單行 `ok prop seq=<n> id=PROP-SI-124 rev=2 route=loop cls=P digest=<8 碼> touched_count=<k>`
  And 新事件的 `rev` 為 `2`，`cls`、`action`、`target`、`sources` 與 `rev` 為 1 的事件相同；內容檔 `r2.patch` 與 `r2.md` 存在、`r1.*` 位元組不變
  And `MJ(status)` 顯示 `PROP-SI-124` 的 `state` 為 `proposed`、`rev` 為 `2`；運轉預算已滿仍受理（修訂不計入預算）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_2_1]"
```

```gherkin
# AT-108-2-E-1
# 對應 AC: AC-108-2（PRD AC-SI-08-2；R49 (c)）跳級被拒並印 OBS 草稿列；修訂超限、查無 PROP 的拒收碼
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_108_2_E_1 -q

Feature: prop-revise 的拒收

Scenario: 非 returned 狀態、超過修訂上限、查無 PROP 皆拒收
  Given 依 §5.2 情境 `SC-REV` 手寫事件帳本與內容檔：`PROP-SI-124` 為 `proposed`、`PROP-SI-125` 為 `approved`、`PROP-SI-126` 為 `rejected`、`PROP-SI-127` 為 `handed-off`、`PROP-SI-128` 為 `returned` 且 `rev` 已為 3（`max_revisions` 為 2，故下一版為 4）；執行期組出不存在的 PROP 號 `PX`；`snap0＝snap(R)`
  When 對 124～127 各呼叫一次 `prop-revise`（旗標取 `good_prop_args`）、對 128 呼叫一次、對 `PX` 呼叫一次
  Then 對 124～127：rc 皆為 `1`，`codes(out)` 皆含 `TRANSITION-ILLEGAL`，輸出含 `obs-draft:` 與恰一行草稿列
  And 對 128：rc 為 `1`，`codes(out)` 含 `REV-LIMIT`，`PROP-SI-128` 的折疊狀態仍為 `returned`（拒收不寫事件、不另產生 rejected）
  And 對 `PX`：rc 為 `1`，`codes(out)` 恰為 `PROP-NOT-FOUND`
  And 全部呼叫後 `snap(R)` 等於 `snap0`；`draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_2_E_1]"
```

```gherkin
# AT-108-3-1
# 對應 AC: AC-108-3（PRD AC-SI-08-3；R52 (d)）R 類新增規則候選檔含 `trust_level: proposed` 即受理，且不碰 FSM 狀態檔
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_108_3_1 -q

Feature: R 類提案

Scenario: 新增含 trust_level: proposed 的規則檔受理為 loop
  Given 基線 `R`（`<VNEW>` 下有 `R-9.1.yaml`〔active〕）；已開運轉並補好研究事件；`snap0＝snap(R)`
  When 呼叫 `prop-new --cls R --action add --target AISDLC_SDD/<VNEW>/governance/rules/R-9.9.yaml …`，patch 新增該檔，內容含字面 `trust_level: proposed`
  Then rc 為 `0`、事件的 `cls` 為 `R`、`route` 為 `loop`
  And `snap(R)` 與 `snap0` 的差異只有事件帳本與提案內容檔；工作樹內不存在 `R-9.9.yaml`，且沒有任何 `FSM-STATE` 類檔案被建立或改動
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_3_1]"
```

```gherkin
# AT-108-3-E-1
# 對應 AC: AC-108-3（PRD AC-SI-08-3；R52 (d)）R 類新增檔缺 `trust_level: proposed` 拒收；觸及既有 active 規則本體者整張轉交而非拒收
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_108_3_E_1 -q

Feature: R 類提案的拒收與轉交

Scenario: 缺 trust_level: proposed 被拒；改既有 active 規則被轉交
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When 情境一：`--cls R --action add` 新增 `R-9.9.yaml`，內容不含 `trust_level: proposed`（含 `trust_level: active` 的變體一案）
  And 情境二：`--cls R --action modify --handoff R`，patch 修改既有的 `R-9.1.yaml`（`maturity: active`）
  Then 情境一的兩案：rc 皆為 `1`，`codes(out)` 恰為 `R-NOT-PROPOSED`；零殘留、`draft_ok` 成立
  And 情境二：rc 為 `0`，事件的 `route` 為 `handoff:R`（轉交而非拒收）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_108_3_E_1]"
```

```gherkin
# AT-109-1-1
# 對應 AC: AC-109-1（PRD AC-SI-09-1；R50 (a)(b)(c)）提案本文的形態判準：五節骨架、欄位表、必備欄與結果標籤三值
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_1_1 -q

Feature: 提案本文形態

Scenario: 合規的 rN.md 受理，標題可帶修飾字、順序不拘、結果標籤三值皆可
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`；§5.3 的 `body_md(...)` 建構器
  When 案例一至三：骨架五節（標題文字各含 `反例證據`、`Before`、`After`、`影響面`、`欄位`），欄位表含 `symptom`、`risk`、`rollback`、`budget`、`scope` 與 `result_label`，`result_label` 依序為 `失敗`、`成功`、`升級`
  And 案例四：五節順序打亂（`## 欄位` 在最前）、標題帶修飾字（例 `## 一、反例證據（帳本列）`）、另含選用欄 `retire_when`、`reopen_symptom`、`verify_plan`
  Then 四案 rc 皆為 `0`；各 `r1.md` 的位元組等於輸入本文（CRLF 換 LF 後）
  And 各案卡面第 2 行的症狀文字等於欄位表的 `symptom`、第 4 行的風險與回滾等於欄位表的 `risk` 與 `rollback`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_1_1]"
```

```gherkin
# AT-109-1-E-1
# 對應 AC: AC-109-1（PRD AC-SI-09-1；R50 (a)(b)(c)(e)）骨架缺節、必備欄缺或空、結果標籤值域外各拒收；非 UTF-8 本文 rc 3
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_1_E_1 -q

Feature: 提案本文的拒收

Scenario: 缺節、缺欄、空欄、值域外各報對應碼，且列出缺的項目
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`；`snap0＝snap(R)`
  When 情境一：本文各缺一個 `## ` 標題（`反例證據`、`Before`、`After`、`影響面`、`欄位`，共 5 案）
  And 情境二：欄位表各缺一個必備欄（`symptom`、`risk`、`rollback`、`budget`、`result_label`、`scope`，共 6 案）；另 6 案把該欄的值清成空白
  And 情境三：`result_label` 為 `maybe`；情境四：本文檔案含非 UTF-8 位元組
  Then 情境一：每案 rc 為 `1`、`codes(out)` 恰為 `BODY-SKELETON`，該碼的 detail 列出缺的那節
  And 情境二：12 案 rc 皆為 `1`、`codes(out)` 恰為 `BODY-FIELD-MISSING`，detail 列出欄名；情境三：rc `1`、碼 `BODY-FIELD-VALUE`；情境四：rc `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 全部呼叫後 `snap(R)` 等於 `snap0`；rc 為 `1` 的呼叫其 `draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_1_E_1]"
```

```gherkin
# AT-109-1-2
# 對應 AC: AC-109-1（PRD AC-SI-09-1；R65 (c)；代位）輸入限於抽象化摘要、不得以原始軌跡全文充當條目——SOP 提案者節的條文（機械判準只能近似，語意由實跑檢核對照 PRD）
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP；含刪去自證）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_1_2 -q

Feature: 抽象化條文（代位）

Scenario: 提案者節有同一行同時含抽象化、結果標籤、原始軌跡全文的條文，且判準非恆真
  Given 真 SOP 的提案者節（標題含 `提案者`；LF 正規化）與夾具函式 `line_has_all`
  When 以 `line_has_all(section, 抽象化, 結果標籤, 原始軌跡全文)` 取符合的行；另產生副本：三個片段各自在該行刪去（三個副本）、把該行後半段移到下一行、把整行移到審查者節
  Then 真 SOP 的提案者節至少有一行同時含三個片段，且不在程式碼圍欄內
  And 每個副本的 `line_has_all(<提案者節>, …)` 皆找不到符合的行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_1_2]"
```

```gherkin
# AT-109-2-1
# 對應 AC: AC-109-2（PRD AC-SI-09-2；R54 (a)(b)）觸及比例與新增條目的邊界（恰等於放行、超過拒收），多檔比例加總，條目的三種樣式與新檔計數
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_2_1 -q

Feature: 增量 delta 的受理

Scenario: 觸及比例恰 0.2 放行、新增條目恰 3 放行，以及各自的超界拒收
  Given 基線 `R`（`max_touch_ratio` 為 0.2、`max_new_entries` 為 3；§5.3 夾具檔 `docs/notes/other.md` 為 50 行、`f1.md` 為 50 行）；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When 比例組：(R1) 取代 `other.md` 的 10 行（`-` 10 行、`+` 10 行，新增行不是條目樣式）；(R2) 取代 11 行；(R3) 兩個檔各取代 6 行與 5 行（合計 11 行、分母 100）
  And 條目組：(E1) 在 `other.md` 新增 3 行 `- x` 樣式；(E2) 新增 4 行；(E3) 新增 `## h`、`1. x`、`- y` 三種樣式各一行；(E4) 新增 `## h`、`1. x`、`- y`、`* z` 四行；(E5) 新增 10 行非條目文字加 3 行條目；(E6) 新增三個新檔；(E7) 新增四個新檔；(E8) 新增兩個新檔加兩行條目
  Then 比例組：R1 rc `0`；R2 rc `1`、`codes(out)` 恰為 `TOUCH-RATIO`；R3 rc `0`（比例以全部被觸及檔的總和計）
  And 條目組：E1、E3、E5、E6 rc `0`；E2、E4、E7、E8 rc `1`、`codes(out)` 恰為 `NEW-ENTRIES`
  And 被拒案例零殘留且 `draft_ok` 成立；受理案例的卡面第 3 行顯示的觸及比例（小數兩位）等於獨立計算值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_2_1]"
```

```gherkin
# AT-109-2-E-1
# 對應 AC: AC-109-2（PRD AC-SI-09-2；R54 (c)(d)）M 類歸檔型（逐字搬移、零內容修改）豁免觸及比例、改受歸檔上限；任一行被改寫即回到比例判準
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_2_E_1 -q

Feature: 歸檔型豁免

Scenario: 搬 40 行放行、搬 50 行放行、搬 51 行拒收；改寫一行即非歸檔型；缺記憶目錄拒收
  Given 基線 `R`（`max_archive_entries_per_card` 為 50）；§5.3 記憶目錄夾具 `memory_dir`（`MEMORY.md` 120 行、`archive-index-old.md` 30 行）；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When (M1) `--cls M`，patch 把 `MEMORY.md` 的 40 行逐字搬到 `archive-index-old.md` 末尾，索引檔另增 1 個指標行；(M2) 同 M1 但搬 51 行；(M3) 搬 50 行
  And (M4) 同 M1 但歸檔檔上有一行與原文差一個字元；(M5) 同 M1 但索引檔增 4 個指標行
  And (M6) 缺 `--memory-dir`；(M7) `--memory-dir` 指向一個普通檔案
  Then M1、M3：rc `0`（觸及比例超過 `max_touch_ratio`，但歸檔型不受其約束）；M2：rc `1`、`codes(out)` 恰為 `ARCHIVE-ENTRIES`
  And M4：rc `1`、`codes(out)` 含 `TOUCH-RATIO`（任一行被改寫即回到比例判準）；M5：rc `1`、`codes(out)` 含 `NEW-ENTRIES`
  And M6：rc `1`、`codes(out)` 恰為 `MEMORY-DIR-MISSING`；M7：rc `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 被拒案例零殘留且 `draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_2_E_1]"
```

```gherkin
# AT-109-3-1
# 對應 AC: AC-109-3（PRD AC-SI-09-3；R50 (d)、R54 (e)）M 類四欄齊備即受理；`preimage` 為被刪行的逐檔 sha256；非 M 類沒有 `preimage`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_3_1 -q

Feature: M 類四欄與 pre-image

Scenario: 四欄齊備的 M 類提案受理，preimage 與被刪行的雜湊一致
  Given 基線 `R`；記憶目錄夾具 `memory_dir` 的 `demo.md` 為 20 行；已開運轉並補好研究事件
  When 呼叫 `prop-new --cls M --action modify --target memory/demo.md --memory-dir <memory_dir> --source OBS-SI-001 …`，patch 刪去 `demo.md` 的 2 行、新增 1 行、另新增新檔 `memory/new_note.md`；本文欄位表的 `result_label` 為 `失敗`、`scope` 為 `memory 索引`、`source_obs` 為 `OBS-SI-001`、`retire_when` 為 `該症狀不再出現`
  And 另呼叫兩次 `--cls P`（`target` 各為 `playbooks/demo.yaml`、`docs/notes/other.md`，互不同型）：第一次本文帶四欄、第二次本文不帶 `source_obs` 與 `retire_when`
  Then M 類 rc 為 `0`；事件有 `preimage` 鍵，其鍵集合恰為 `memory/demo.md` 與 `memory/new_note.md`
  And `preimage` 的 `memory/demo.md` 值等於 `sha256:` 接被刪兩行（依序以 LF 連接並結尾加 LF）的 UTF-8 位元組之 sha256（測試端獨立計算）；`memory/new_note.md`（只新增）的值等於空位元組的 sha256
  And P 類兩次皆 rc `0`、事件沒有 `preimage` 鍵（非 M 類不要求 `source_obs` 與 `retire_when`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_3_1]"
```

```gherkin
# AT-109-3-E-1
# 對應 AC: AC-109-3（PRD AC-SI-09-3；R50 (d)）M 類四欄缺或空、`source_obs` 不在 `--source` 內或非 OBS 號各拒收；`result_label` 值域外走 BODY-FIELD-VALUE
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_109_3_E_1 -q

Feature: M 類四欄的拒收

Scenario: 缺欄、空欄、來源對不上皆報 M-FIELD-MISSING
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`；`snap0＝snap(R)`
  When 情境一：M 類本文四欄各缺一欄（`result_label`、`scope`、`source_obs`、`retire_when`，共 4 案）；各把該欄清成空白（4 案）
  And 情境二：`source_obs` 為 `OBS-SI-003`（不在 `--source OBS-SI-001` 內）；`source_obs` 為 `foo`（不是 OBS 號）；`source_obs` 為 `OBS-SI-001、OBS-SI-003`（其一不在內）
  And 情境三：`result_label` 為 `maybe`（M 類）
  Then 情境一的八案與情境二的三案：rc 皆為 `1`，`codes(out)` 恰為 `M-FIELD-MISSING`（四欄不另報 `BODY-FIELD-MISSING`），detail 列欄名
  And 情境三：rc `1`，`codes(out)` 恰為 `BODY-FIELD-VALUE`
  And 全部呼叫後 `snap(R)` 等於 `snap0`；`draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_109_3_E_1]"
```

```gherkin
# AT-110-1-1
# 對應 AC: AC-110-1（PRD AC-SI-10-1；R53 (d)(e)）運轉預算與同型去重：邊界、跨運轉、活躍狀態與根因鍵的相交規則
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_110_1_1 -q

Feature: 提案前置的預算與去重

Scenario: 同運轉第 4 個新 PROP 被拒；同型的活躍 PROP 存在時被拒，條件改變即放行
  Given 基線 `R`（`max_proposals_per_run` 為 3）；兩個已開運轉 `RUN-SI-001`、`RUN-SI-002`（皆補好研究事件）
  When 預算組：在 `RUN-SI-001` 依序建三個不同型的 PROP（P 類 `playbooks/demo.yaml`、D 類 `docs/notes/demo.md`、D 類 `docs/notes/other.md`），再建第四個（D 類 `docs/notes/f1.md`）；同一個第四個改在 `RUN-SI-002` 建
  And 去重組（另一份基線，`max_proposals_per_run` 改為 99）：(a) 活躍 PROP A（D 類、`docs/notes/f2.md`、來源 `OBS-SI-001`，無歸因）存在時再建同型者；(b) 手寫 `dec`（`dkind` 為 `reject`）使 A 為 `rejected` 後再建同型者；(c) 同型但 `target` 不同；(d) 同型、`target` 同，但雙方的來源各自有 `attr`（root）且根因鍵不相交（A 為 `tools/a-b`、新者為 `tools/c-d`）；(e) 同型、`target` 同，A 有根因鍵而新者的來源無歸因；(f) 在 (e) 之後再建一個同型且來源無歸因者
  Then 預算組：前三個 rc `0`；第四個在 `RUN-SI-001`：rc `1`、`codes(out)` 恰為 `BUDGET-PROPOSALS`；在 `RUN-SI-002`：rc `0`
  And 去重組：(a) rc `1`、碼 `DUPLICATE-TYPE`（雙方根因鍵集合皆為空）；(b) rc `0`（`rejected` 不是活躍）；(c) rc `0`；(d) rc `0`（根因鍵不相交且不皆為空）；(e) rc `0`（一方為空、一方非空）；(f) rc `1`、碼 `DUPLICATE-TYPE`（與 (e) 建立的 PROP 雙方皆空）
  And 被拒案例零殘留且 `draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_1_1]"
```

```gherkin
# AT-110-1-E-1
# 對應 AC: AC-110-1（PRD AC-SI-10-1、AC-SI-17-2 的 M 半；R53 (a)(b)(c)、R35 (c)）未開運轉、無研究事件、SUSPENDED 期間拒收；多碼一併回報；恢復後放行
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_110_1_E_1 -q

Feature: 提案前置的狀態類拒收

Scenario: 運轉與研究事件缺失、SUSPENDED 期間的提案被拒，階段二的碼一併回報
  Given 情境一：手寫事件帳本，`RUN-SI-001` 已 `run.open` 且已 `run.close`；情境二：`RUN-SI-002` 為 open 但沒有研究事件；情境三：依 §5.2 情境 `SC-SUSP` 手寫事件帳本（連續兩個壞窗，`stop_after_bad` 為 2；其後 `RUN-SI-002` 為 open 且無研究事件、`RUN-SI-003` 為 open 且有研究事件）
  When 情境一與二各呼叫 `prop-new --run <該運轉>`；情境三呼叫 `prop-new --run RUN-SI-003`
  And 情境四：在 `SC-SUSP` 上以執行期組出的不存在運轉號呼叫一次（同時成立「運轉未開」「該運轉無研究事件」「處於 SUSPENDED」三個條件）
  And 情境五：在 `SC-SUSP` 之後手寫一筆 `dec`（`dkind` 為 `resume`，`run` 為 `SC-SUSP` 的所在運轉）後再呼叫 `prop-new --run RUN-SI-003`
  Then 情境一：rc `1`、`codes(out)` 含 `RUN-NOT-OPEN`；情境二：rc `1`、`codes(out)` 恰為 `RESEARCH-MISSING`；情境三：rc `1`、`codes(out)` 恰為 `SUSPENDED`
  And 情境四：`codes(out)` 同時含 `RUN-NOT-OPEN`、`RESEARCH-MISSING`、`SUSPENDED`（階段二一併回報）；情境五：rc `0`（恢復後不再 SUSPENDED）
  And 被拒案例零殘留且 `draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_1_E_1]"
```

```gherkin
# AT-110-2-1
# 對應 AC: AC-110-2（PRD AC-SI-10-2；R50 (c)、R56）每提案宣告預算，預算文字原樣進卡面第 7 行
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_110_2_1 -q

Feature: 預算宣告

Scenario: 帶預算宣告的提案受理，卡面第 7 行逐字顯示預算
  Given 基線 `R`；已開運轉並補好研究事件；本文欄位表的 `budget` 為 `1 次子代理、約 3000 token`
  When 呼叫 `prop-new`（旗標取 `good_prop_args`），再呼叫 `card <PROP>`
  Then `prop-new` rc 為 `0`；`card` 輸出的第 7 行含 `預算宣告：1 次子代理、約 3000 token`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_2_1]"
```

```gherkin
# AT-110-2-E-1
# 對應 AC: AC-110-2（PRD AC-SI-10-2；R50 (c)）`budget` 欄缺或空即拒收
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_110_2_E_1 -q

Feature: 缺預算宣告的拒收

Scenario: 欄位表缺 budget 或 budget 為空白，提案被拒
  Given 基線 `R`；已開運轉並補好研究事件；`snap0＝snap(R)`
  When 呼叫 `prop-new`，本文欄位表缺 `budget` 列；再呼叫一次，`budget` 值為空白
  Then 兩次 rc 皆為 `1`，`codes(out)` 恰為 `BODY-FIELD-MISSING`，detail 含欄名 `budget`
  And `snap(R)` 等於 `snap0`；`draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_2_E_1]"
```

```gherkin
# AT-110-2-2
# 對應 AC: AC-110-2（PRD AC-SI-10-2；R65 (c)；代位）提案者與審查者不得再派提案者與審查者（零遞迴）——SOP 提案者節的條文
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP；含刪去自證）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_110_2_2 -q

Feature: 零遞迴條文（代位）

Scenario: 提案者節有同一行同時含不得再派、提案者、審查者的條文，且判準非恆真
  Given 真 SOP 的提案者節（LF 正規化）與夾具函式 `line_has_all`
  When 以 `line_has_all(section, 不得再派, 提案者, 審查者)` 取符合的行；另產生副本：三個片段各自在該行刪去（三個副本）、把該行後半段移到下一行、把整行移到凍結者節
  Then 真 SOP 的提案者節至少有一行同時含三個片段，且不在程式碼圍欄內
  And 每個副本的 `line_has_all(<提案者節>, …)` 皆找不到符合的行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_110_2_2]"
```

```gherkin
# AT-111-1-1
# 對應 AC: AC-111-1（PRD AC-SI-11-1；R52 (f)(g)）M、P、R、D 四類受理；評估器群組與迴圈自身群組的標記取自 PRD 標籤位置
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_111_1_1 -q

Feature: 類別白名單

Scenario: 四個合法類別各自受理並導出為 loop；群組標記不另存第二份清單
  Given 基線 `R`（其迷你 PRD 的實體 glob 行含 (i)～(v) 五個群組標籤，見 §5.3）；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When 對 `--cls` 為 `M`、`P`、`R`、`D` 各呼叫一次（旗標取 `good_prop_args`，目標皆為乾淨路徑），另對動作 `--action retire` 呼叫一次（`--cls D`，patch 刪除 `docs/notes/tiny.md` 並修改 `docs/notes/demo.md` 的 1 行，使觸及比例仍在上限內）
  And 另把迷你 PRD 中 `docs/06_quality/SelfImproving_Protocol/**` 這個 glob 從 (iii) 群組搬到 (iv) 群組（glob 集合不變，`params.json` 照舊），對觸及 `docs/06_quality/SelfImproving_Protocol/params.json` 的 patch 呼叫 `prop-new --cls P --handoff T1`；搬動前後各呼叫一次
  Then 前五次 rc 皆為 `0`、事件的 `route` 皆為 `loop`、`cls` 依序為 `M`、`P`、`R`、`D`、`D`、`action` 最後一次為 `retire`
  And 搬動標籤前的呼叫：事件的 `cls` 為 `evaluator-change`；搬動後的呼叫：`cls` 改為 `loop-self`（兩次 `route` 皆為 `handoff:T1`），證明群組歸屬取自 PRD 現文、沒有第二份清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_111_1_1]"
```

```gherkin
# AT-111-1-E-1
# 對應 AC: AC-111-1（PRD AC-SI-11-1；R52 (f)(g)、R27）評估器變更與迴圈自身類別不進採納流程（整張轉交）；類別旗標值域外 rc 3；patch 觸及的群組覆寫自填類別
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_111_1_E_1 -q

Feature: 評估器與迴圈自身的轉交

Scenario: evaluator-change 與 loop-self 不走 loop；patch 觸及的群組覆寫自填類別
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When 情境一：`prop-new --cls evaluator-change --handoff T1`、`--cls loop-self --handoff T1`（patch 皆為乾淨路徑）
  And 情境二：`--cls P --handoff T1` 搭觸及 `docs/06_quality/SelfImproving_Protocol/params.json`、搭觸及 `tools/selfimproving.py`；`--cls D --handoff T1` 搭兩者皆觸及
  And 情境三：`--cls Z`、`--cls m`（大小寫不符）
  Then 情境一：兩次 rc 皆為 `0`、事件的 `route` 皆為 `handoff:T1`、`cls` 保持自填值
  And 情境二：三次事件的 `cls` 依序為 `evaluator-change`、`loop-self`、`evaluator-change`，`route` 皆為 `handoff:T1`（自填的 `P`、`D` 被群組覆寫）
  And 情境三：兩次 rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_111_1_E_1]"
```

```gherkin
# AT-114-1-1
# 對應 AC: AC-114-1（PRD AC-SI-14-1；R56 (a)(c)）卡面由 PROP 欄位與 `rN.patch` 確定性轉換：逐行格式、轉交變體、驗證狀態與冷卻狀態的顯示、連續兩次輸出逐字相同
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_1_1 -q

Feature: 卡面確定性轉換

Scenario: loop 卡與轉交卡的七行格式逐字等於測試端獨立組出的文字
  Given 基線 `R`；已開運轉並補好研究事件；以 `good_prop_args(R, cls=P)` 建 `PROP-SI-124`（patch 取代 `playbooks/demo.yaml` 的 2 行、該檔共 40 行；本文 `symptom` 為 `卡面症狀一句`、`risk` 為 `風險一句`、`rollback` 為 `git revert 該 patch`、`budget` 為 `1 次子代理、約 3000 token`；來源 `OBS-SI-001`、`OBS-SI-002`）；另以守衛面新增檔建一個轉交 PROP（`PROP-SI-125`，通道 `DEF`）
  When 對 `PROP-SI-124` 連續呼叫兩次 `card PROP-SI-124`；呼叫 `card PROP-SI-125`
  And 驗證狀態變體（各自複製、手寫合法事件序列）：`dec approve`、`app.sandbox`、`app.verify` 的 `verdict` 依序為 `PASS`、`FAIL`、`NE`，各呼叫 `card`；冷卻變體：手寫 `dec`（`reject`）使 PROP 為 `rejected` 後呼叫 `card`，再追加 `dec`（`unblock`）後呼叫
  Then 兩次輸出逐字相同；輸出以 LF 結尾、UTF-8，恰為七行
  And 第 1 行為 `[PROP-SI-124] Playbook 片段｜modify｜目標：playbooks/demo.yaml｜digest：<前 8 碼>｜驗證：未驗`（前 8 碼取事件 `digest` 去掉前綴後的前 8 位）；第 2 行為 `一、症狀：卡面症狀一句`；第 3 行為 `二、改什麼：+2／-2 行；觸及比例 0.05；觸及檔案數 1；不在 target 內的路徑：0`
  And 第 4 行為 `三、風險與回滾：風險一句｜回滾：git revert 該 patch｜驗證：未驗`；第 5 行為 `決定：核准 ／ 否決＋一句理由 ／ 退回＋一句修改要求`；第 6 行為 `--- 以下不計入核心區 ---`；第 7 行為 `證據座標：OBS-SI-001、OBS-SI-002｜預算宣告：1 次子代理、約 3000 token｜完整 diff 座標：docs/06_quality/SelfImproving_Proposals/PROP-SI-124/r1.patch｜冷卻狀態：無｜轉交通道：無`
  And 轉交卡：第 1 行結尾多 `｜僅轉交，本迴圈不套用`、第 5 行為 `決定：轉交 ／ 不轉交＋一句理由`、第 7 行結尾為 `轉交通道：DEF`
  And 驗證狀態變體的第 1 與第 4 行的 `驗證：` 後依序為 `PASS`、`FAIL`、`NE`；冷卻變體：`rejected` 時第 7 行為 `冷卻狀態：冷卻中`，`unblock` 後為 `冷卻狀態：無`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_1_1]"
```

```gherkin
# AT-114-1-2
# 對應 AC: AC-114-1（PRD AC-SI-14-1；R56 (a)(b)）`M` 類卡面（正控）：觸及比例印 `n/a`（無 base 快照），其餘各行形態與非 `M` 類相同，核心區不超限
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_1_2 -q -p no:xdist -o addopts=

Feature: M 類卡面

Scenario: M 類提案的卡面為七行，第三行的觸及比例為 n/a
  Given 基線 `R`（已開運轉 `RUN-SI-001`、含研究事件）；記憶目錄夾具 `memory_dir`；以 §5.3 `good_prop_args(R, "M")` 呼叫 `prop-new --run RUN-SI-001`，得 `PROP-SI-124`（`M` 類、`target` 為 `memory/demo.md`、patch 取代 `demo.md` 第 3、4 行）
  When 呼叫 `card PROP-SI-124` 與 `card PROP-SI-124 --json`
  Then 兩次 rc 皆為 `0`；文字形態恰 7 行（結尾 LF）；第 1 行為 `[PROP-SI-124] 記憶條目｜modify｜目標：memory/demo.md｜digest：<前 8 碼>｜驗證：未驗`
  And 第 3 行恰為 `二、改什麼：+2／-2 行；觸及比例 n/a；觸及檔案數 1；不在 target 內的路徑：0`（不含小數比例）
  And 核心區（第 1～5 行）為 5 行；第 2～5 行的顯示寬度皆不大於 `card_line_max`（CJK 算 2，測試端獨立以 `unicodedata.east_asian_width` 算出）
  And `--json`：`core_lines` 為 `5`；`parsed` 的 `digest8` 等於 digest 前 8 碼、`added` 為 `2`、`removed` 為 `2`、`touched_count` 為 `1`、`extra_paths` 為空陣列、`verdict` 為 `未驗`；`text` 等於文字形態的輸出
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_1_2]"
```

```gherkin
# AT-114-1-E-1
# 對應 AC: AC-114-1（PRD AC-SI-14-1；R56 (c)(d)）提案者自由撰寫的摘要不取代 diff 本文；查無 PROP 與內容檔缺失 rc 3
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_1_E_1 -q

Feature: 卡面不信任自由文字

Scenario: 症狀文字冒充 diff 行數無效；查無 PROP 與缺內容檔拒出卡
  Given 基線 `R`；已開運轉並補好研究事件；以 `good_prop_args(R, cls=P)` 建 `PROP-SI-124`，但本文 `symptom` 為 `+99／-99 行；觸及比例 0.99；觸及檔案數 9`
  When 情境一：呼叫 `card PROP-SI-124`；情境二：呼叫 `card` 搭執行期組出的不存在 PROP 號；情境三：刪去 `r1.md` 後呼叫 `card PROP-SI-124`；情境四：不帶 PROP 號呼叫 `card`
  Then 情境一：rc `0`；第 2 行含該症狀原文，但第 3 行仍為 `二、改什麼：+2／-2 行；觸及比例 0.05；觸及檔案數 1；不在 target 內的路徑：0`（取自 `.patch` 與事件，不取自自由文字）
  And 情境二：rc `3`、stdout 空、stderr 含 `PROP-NOT-FOUND`；情境三：rc `3`、stdout 空、stderr 含 `PROP-FILE-MISSING`；情境四：rc `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_1_E_1]"
```

```gherkin
# AT-114-2-1
# 對應 AC: AC-114-2（PRD AC-SI-14-2；R56 (d)(e)）卡面反解析與由事件、patch、本文重算的值逐欄一致；`--json` 形態
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_2_1 -q

Feature: 卡面反解析一致

Scenario: 一致的卡可送達，JSON 形態的 parsed 與重算值相同
  Given 基線 `R`；以 `good_prop_args(R, cls=P)` 建 `PROP-SI-124`
  When 呼叫 `card PROP-SI-124 --json`，並另呼叫文字形態
  Then rc 為 `0`；JSON 鍵序為 `schema_rev`、`prop`、`rev`、`digest`、`core_lines`、`text`、`parsed`；`schema_rev` 為 `1`、`core_lines` 為 `5`、`digest` 為事件 `digest` 的全值
  And `text` 逐字等於文字形態的 stdout；`parsed` 的鍵序為 `digest8`、`added`、`removed`、`touched_count`、`extra_paths`、`verdict`，值依序為事件 `digest` 的前 8 碼、`2`、`2`、`1`、空陣列、`未驗`
  And 由事件、`r1.patch`（`+`、`-` 行數）、`r1.md` 獨立重算的同一組值與 `parsed` 逐欄相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_2_1]"
```

```gherkin
# AT-114-2-E-1
# 對應 AC: AC-114-2（PRD AC-SI-14-2；R56 (d)）內容檔於 `prop-new` 之後被改動，卡不得送達（rc 3、stdout 空、印 CARD-INCONSISTENT 與不符欄名）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_2_E_1 -q

Feature: 不一致的卡不得送達

Scenario: 竄改 patch 或本文後 card 拒絕輸出
  Given 基線 `R`；以 `good_prop_args(R, cls=P)` 建 `PROP-SI-124`；每個情境各自複製再變異；變異前的 `card` 輸出為對照
  When 情境一：在 `r1.patch` 末尾多加一個新增行；情境二：把 `r1.md` 的 `symptom` 值改字；情境三：把事件帳本中該 `prop` 行的 `digest` 換成另一個合法形態的雜湊字串（工作樹改寫）
  Then 三個情境：`card PROP-SI-124` 與 `card PROP-SI-124 --json` 的 rc 皆為 `3`、stdout 皆為空、stderr 含 `CARD-INCONSISTENT` 與不符欄名 `digest8`
  And 變異前的 `card` 輸出（對照）rc 為 `0` 且為七行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_2_E_1]"
```

```gherkin
# AT-114-3-1
# 對應 AC: AC-114-3（PRD AC-SI-14-3；R56 (b)）核心區 12 行與單行顯示寬度 100（CJK 算 2）的邊界放行；`prop-new` 與 `card` 用同一渲染函式
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_3_1 -q

Feature: 卡面版面邊界

Scenario: 額外路徑 7 筆（核心區 12 行）與第 2 行顯示寬度恰 100 皆放行
  Given 基線 `R`（`card_line_max` 為 100）；每個案例各自複製一份已開運轉並補好研究事件的 `R`；§5.3 夾具檔 `docs/notes/f1.md`～`f8.md` 各 50 行
  When 案例一：`--target playbooks/demo.yaml`，patch 修改 `playbooks/demo.yaml` 與 `f1.md`～`f7.md` 各 1 行（不在 `target` 內的路徑 7 筆）
  And 案例二：本文 `symptom` 為 90 個 ASCII 字元（第 2 行顯示寬度為 10 加 90＝100）；案例三：`symptom` 為 45 個全形字（顯示寬度 90，第 2 行為 100）
  And 各案例成功後呼叫 `card <PROP>`
  Then 三個案例 `prop-new` 的 rc 皆為 `0`
  And 案例一：`card` 輸出的核心區（第 1～5 行加其間的路徑行）為 12 行，第 3 行與第 4 行之間逐筆列出 7 行 `  - <路徑>`（排序）；案例二與三：第 2 行以 `unicodedata.east_asian_width` 為 `W`、`F` 者算 2 的顯示寬度恰為 100
  And 全部案例的核心區第 2～5 行與各路徑行顯示寬度皆不大於 100（第 1 行為標題行、不受此限）；`card` 的輸出與 `prop-new` 預判所用的渲染結果逐字相同（以 `card` 重新渲染的核心區對照 `prop-new` 成功後的事件欄位重算值）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_3_1]"
```

```gherkin
# AT-114-3-E-1
# 對應 AC: AC-114-3（PRD AC-SI-14-3；R56 (b)、R49 (b)）額外路徑 8 筆、第 2 行顯示寬度 101 與 CJK 字數少但寬度超界皆拒收
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_114_3_E_1 -q

Feature: 卡面版面的拒收

Scenario: 超過核心區行數或單行寬度的提案在 prop-new 即被拒，零殘留
  Given 基線 `R`；每個案例各自複製一份已開運轉並補好研究事件的 `R`；`snap0＝snap(R)`
  When 案例一：patch 修改 `playbooks/demo.yaml` 與 `f1.md`～`f8.md` 各 1 行、`--target playbooks/demo.yaml`（不在 `target` 內的路徑 8 筆）
  And 案例二：`symptom` 為 91 個 ASCII 字元（第 2 行寬度 101）；案例三：`symptom` 為 46 個全形字（寬度 92，第 2 行 102）；案例四：`symptom` 為 50 個全形字（字元數少於 100、顯示寬度 100，第 2 行 110）
  Then 案例一：rc `1`、`codes(out)` 恰為 `CARD-TOO-TALL`
  And 案例二至四：rc 皆為 `1`、`codes(out)` 皆恰為 `CARD-LINE-TOO-WIDE`（以顯示寬度而非字元數判定）
  And 全部案例後 `snap(R)` 等於 `snap0`；`draft_ok` 皆成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_114_3_E_1]"
```

```gherkin
# AT-144-1-1
# 對應 AC: AC-144-1（本檔自增；PRD §9.2〈digest〉、AC-SI-07-3；R41、R55）PROP 內容檔的位元組與雜湊、digest 的獨立重算、同輸入同 digest
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_144_1_1 -q

Feature: PROP 內容檔與 digest

Scenario: 內容檔與事件的雜湊互相對得上，digest 等於測試端獨立重算
  Given 基線 `R`（兩份以相同方式建出的 repo `Ra`、`Rb`：固定的作者與提交時間環境，故 HEAD 相同）；已開運轉並補好研究事件；本文檔以 CRLF 換行寫成（`Rb` 用 LF 版本），patch 檔為 LF
  When 在 `Ra`、`Rb` 各以相同旗標呼叫 `prop-new --cls P …`
  Then 兩個 rc 皆為 `0`；內容檔路徑為 `docs/06_quality/SelfImproving_Proposals/PROP-SI-124/r1.patch` 與 `r1.md`；`r1.patch` 的位元組逐字等於輸入 patch 檔；`r1.md` 不含 CR、其位元組等於輸入本文換 LF 後
  And 事件的 `patch_sha256` 等於 `sha256:` 接 `r1.patch` 位元組的 sha256；`body_sha256` 等於 `sha256:` 接 `r1.md` 位元組的 sha256；`touched_sha256` 依 R41 的公式由測試端自 patch 路徑算出
  And 事件的 `digest` 等於 `sha256:` 接由 R55 (a) 的 15 個鍵（`id`、`rev`、`cls`、`action`、`target`、`touched`、`touched_count`、`base`、`preimage`〔P 類取 `base` 的值〕、`patch_sha256`、`body_sha256`、`rollback`、`retire_when`、`reopen_symptom`、`budget`，缺的選用欄為 null）組成的物件，依鍵排序、緊湊分隔符、`ensure_ascii` 為假輸出的 UTF-8 位元組之 sha256（測試端獨立重算，不呼叫被測碼）
  And `Ra` 與 `Rb` 的 `body_sha256` 與 `digest` 相同（CRLF 與 LF 本文等價；輸入相同則 digest 相同）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_144_1_1]"
```

```gherkin
# AT-144-1-E-1
# 對應 AC: AC-144-1（本檔自增；R55、R33）digest 對 `target` 與本文欄位異動敏感；內容檔撞名拒收；追加失敗不留孤兒檔
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_props.py -k AT_144_1_E_1 -q

Feature: digest 的敏感度與內容檔的寫入失敗

Scenario: 目標集合或欄位改動使 digest 改變；撞名拒收；追加失敗不留孤兒
  Given 基線 `R`（固定提交時間環境）；每個案例各自複製一份已開運轉並補好研究事件的 `R`
  When 案例一（敏感度）：以相同 patch 與本文，一案 `--target playbooks/demo.yaml`、另一案多加 `--target docs/notes/other.md`；案例二：本文 `retire_when` 差一個字的兩案
  And 案例三（撞名）：呼叫前先在 `docs/06_quality/SelfImproving_Proposals/PROP-SI-124/` 建 `r1.md`（任意內容）
  And 案例四（追加失敗）：把 `evwrite.PAUSE_HOOK` 以 `mock.patch.object` 設為拋出 `OSError` 的函式後呼叫 `prop-new`
  Then 案例一：兩個事件的 `patch_sha256`、`body_sha256`、`touched_sha256` 相同而 `digest` 不同；案例二：兩個事件的 `digest` 不同
  And 案例三：rc `1`、`codes(out)` 含 `PROP-FILE-EXISTS`；預先建的 `r1.md` 位元組不變、沒有新建 `r1.patch`；事件帳本位元組不變
  And 案例四：rc 不為 `0`；事件帳本位元組不變；`SelfImproving_Proposals/` 下沒有本次寫出的檔（孤兒檔已刪）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_144_1_E_1]"
```

```gherkin
# AT-130-1-1
# 對應 AC: AC-130-1（PRD AC-SI-30-1；R42 (a)、R53 (b)、R57 (a)）同運轉產生 `prop` 前須恰有一筆研究事件，序位介於 `run.open` 與第一筆 `prop` 之間；`prop-new` 拒收與 `check` 重放同判
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_1_1 -q

Feature: 研究事件必有

Scenario: 無研究事件時提案被拒，補研究事件後受理；check 重放抓出缺漏、序位錯誤與多筆
  Given 基線 `R`；已 `run-open` 得 `RUN-SI-001`，尚無研究事件
  When 情境一：呼叫 `prop-new --run RUN-SI-001 …`（旗標取 `good_prop_args`）；再呼叫 `research --skip --run RUN-SI-001 --reason offline --note 離線驗證`；再呼叫同樣的 `prop-new`
  And 情境二（各自以 §5.2 建構器手寫事件帳本後呼叫 `check --json`）：(a) 運轉有 `prop` 而無研究事件；(b) 研究事件的 `seq` 在該運轉第一筆 `prop` 之後；(c) 同運轉有兩筆 `research.skip`；(d) 運轉零 `prop` 且無研究事件；(e) 研究事件的 `seq` 介於 `run.open` 與第一筆 `prop` 之間
  Then 情境一：第一次 `prop-new` rc `1`、`codes(out)` 恰為 `RESEARCH-MISSING`；`research --skip` rc `0`；第二次 `prop-new` rc `0`
  And 情境二：(a) `F(events.research)` 恰為 `(RUN-SI-001, RESEARCH-MISSING)`；(b) 恰為 `(RUN-SI-001, RESEARCH-ORDER)`；(c) 恰為 `(RUN-SI-001, RESEARCH-MULTIPLE)`，detail 列出兩筆的 `seq`
  And 情境二：(d) 與 (e) 的 `S(events.research)` 為 `PASS`、findings 為空（零 `prop` 的運轉不受約束；序位合規）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_1_1]"
```

```gherkin
# AT-130-1-E-1
# 對應 AC: AC-130-1（PRD AC-SI-30-1；R57 (a)）`research --skip` 的 reason 封閉集合與附帶旗標；同運轉第二筆研究事件拒收；helmsman 免掃印 warn 層級的引言回查未建提示
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_1_E_1 -q

Feature: research --skip 的格式與狀態拒收

Scenario: 三種 reason 各自合規受理；格式錯誤 rc 3、狀態錯誤 rc 1、零網路零寫入
  Given 基線 `R`；三個已開運轉 `RUN-SI-001`～`RUN-SI-003`（皆無研究事件）；另有一個已關運轉 `RUN-SI-004`（以 `run-open` 加 `run-close` 造出，亦可手寫這兩行事件）；`snap0＝snap(R)` 與事件帳本的行數基準 `n0` 都取造出 `RUN-SI-004` **之後**
  When 情境一（受理）：`--run RUN-SI-001 --reason quota-band --band high --note 額度帶非 free`；`--run RUN-SI-002 --reason helmsman --sid <UUID> --line 12 --note 掌舵者明示免掃`；`--run RUN-SI-003 --reason offline --note 離線`
  And 情境二（rc 3）：`--reason bogus`；`--note` 為空、121 字元、含換行；`quota-band` 缺 `--band`、`--band free`、`--band Free`；`helmsman` 缺 `--sid`、缺 `--line`、`--sid` 不是 UUID、`--line 0`、`--line abc`；`offline` 加 `--band high`；不帶 `--fetch` 也不帶 `--skip`；同時帶兩者
  And 情境三（rc 1）：對已有研究事件的 `RUN-SI-001` 再呼叫 `--reason offline`；對已關運轉 `RUN-SI-004` 與執行期組出的不存在運轉號各呼叫一次
  And 情境四：對情境一之後的 `R` 呼叫 `check --json`
  Then 情境一：三次 rc 皆為 `0`、stdout 各為 `ok research.skip seq=<n> run=<運轉> reason=<reason>`；三個事件的 `by` 皆為 `main`；共通鍵之後的鍵序依序為（`quota-band`）`run`、`reason`、`note`、`band`，（`helmsman`）`run`、`reason`、`note`、`sid`、`line`（`line` 為整數 12），（`offline`）`run`、`reason`、`note`
  And 情境二的 15 次呼叫（逐項計）：rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 情境三：重複者 rc `1`、`codes(out)` 恰為 `RESEARCH-ALREADY`；已關與不存在的運轉 rc `1`、碼 `RUN-NOT-OPEN`；`draft_ok` 成立；情境二與三沒有改變事件帳本的行數（相對 `n0`，事件帳本只多情境一的 3 行）
  And 情境四：`F(events.research)` 恰為 `(-, QUOTE-VERIFIER-NOT-ESTABLISHED)`（warn 層級，來自 `helmsman`；項目狀態不變）；`overall` 為 `PASS`、rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_1_E_1]"
```

```gherkin
# AT-130-2-1
# 對應 AC: AC-130-2（PRD AC-SI-30-2；R43、R57 (b)、R42 (c)）已提交的合規來源表通過預檢；請求只發給表內現役來源；表內 host 的重導向放行；`check` 的表驗證與 sources_sha256 比對皆 PASS
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_2_1 -q

Feature: 來源白名單與預檢（正控）

Scenario: 合規且已提交的來源表通過預檢，請求只到表內來源與其同 host 的重導向目標
  Given 基線 `R`；§5.4 `serve` 起本機伺服器，路由 `/a`（200、`text/plain`、內容 `A`）、`/b`（302 到同一 host 與連接埠的 `/b2`）、`/b2`（200、`text/plain`、內容 `B`）、`/unlisted`（200，不在表內）；§5.4 `write_table` 寫入並提交兩個現役來源 `src-a`（`/a`）、`src-b`（`/b`）；以 `relaxed()` 暫時放寬 `sources.DEFAULT_POLICY`；已 `run-open` 得 `RUN-SI-001`
  When 呼叫 `research --fetch --run RUN-SI-001`；再呼叫 `check --json`
  Then 抓取 rc 為 `0`；伺服器收到的請求路徑依序恰為 `/a`、`/b`、`/b2`（沒有 `/unlisted`，請求逐一發出、`max_inflight` 為 1）
  And `research.scan` 事件的 `sources` 兩筆的 `id` 依序為 `src-a`、`src-b`
  And `S(research.sources)` 為 `PASS`；`S(events.research)` 為 `PASS`（事件的 `sources_sha256` 等於其 `t` 之前最近一次含該表的提交所載表內容〔CRLF 換 LF〕的 sha256）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_2_1]"
```

```gherkin
# AT-130-2-E-1
# 對應 AC: AC-130-2（PRD AC-SI-30-2；R43、R57 (b)）來源表驗證碼逐一命中；預檢失敗整次拒收（零請求、零事件）；表與 HEAD 提交版不同即拒收
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_2_E_1 -q

Feature: 來源表驗證與預檢拒收

Scenario: 表驗證的每個碼各被判出；預檢任一失敗即整次拒收且零請求
  Given 基線 `R`；§5.4 `serve` 起伺服器（記錄請求）；各案例各自複製一份已開運轉的 `R`；`validate_table` 取 `sources.validate_table(raw, sources.DEFAULT_POLICY)`（嚴格政策）
  When 函式層（各案例以一個合規單筆來源表的位元組變異後直接呼叫 `validate_table`）：BOM；含 CR；結尾無換行；不是 JSON 物件；`schema_rev` 為 2；缺 `sources` 鍵；元素多一個表外鍵；缺 `extract`；`id` 含大寫；兩筆同 `id`；兩筆未依 `id` 位元組序；`kind` 為 `news`；`retired` 為字串 `yes`；`url` 為 `http://…`；`url` 帶 userinfo；`url` 的 host 為 `localhost`、`127.0.0.1`、`10.0.0.1`、`172.16.0.1`、`192.168.0.1`、`169.254.0.1`、`[::1]`、`[fe80::1]`、`[fc00::1]`、`[::ffff:10.0.0.1]`（私網形態的字面 IP）
  And 預檢（CLI，不放寬政策；每案各自提交來源表）：來源表不存在；來源表帶 BOM；現役來源 9 筆（`research_fetch_max` 為 8）；9 筆中 2 筆 `retired`（現役 7 筆，且 url 指向會回 200 的 loopback，以 `relaxed()` 放行）；所有來源皆 `retired`；工作樹來源表與 HEAD 不同（未提交的改動）、僅行尾轉成 CRLF、該檔未追蹤；`--run` 為已關運轉、已有研究事件的運轉
  And 非 git 目錄：把已開運轉、已手寫事件的 `R` 複製成不含 `.git` 的目錄後以 `relaxed()` 呼叫 `research --fetch`
  Then 函式層：空白對照（合規表）回傳空串列；各變異回傳的碼依序為 `SRC-FILE-FORMAT`、`SRC-FILE-FORMAT`、`SRC-FILE-FORMAT`、`SRC-FILE-FORMAT`、`SRC-SCHEMA`、`SRC-SCHEMA`、`SRC-SCHEMA`、`SRC-FIELD-MISSING`、`SRC-ID-FORMAT`、`SRC-ID-DUP`、`SRC-ORDER`、`SRC-KIND`、`SRC-RETIRED-TYPE`、`SRC-URL-SCHEME`、`SRC-URL-USERINFO`、`SRC-URL-HOST`（host 的十種寫法各回 `SRC-URL-HOST`）
  And 預檢：不存在者 rc `1`、碼 `SOURCES-ABSENT`；帶 BOM 者碼 `SRC-FILE-FORMAT`；現役 9 筆者碼 `FETCH-MAX`；現役 7 筆者 rc `0`（`retired` 不計）；全部 `retired` 者碼 `ZERO-SUCCESS`；工作樹與 HEAD 不同者與未追蹤者碼 `SOURCES-UNCOMMITTED`；僅 CRLF 差異者 rc `0`（雙方先換 LF 再比）；已關運轉者碼 `RUN-NOT-OPEN`；已有研究事件者碼 `RESEARCH-ALREADY`
  And 預檢被拒的案例：伺服器收到的請求數為 0、事件帳本位元組不變、輸出含恰一行草稿列且 `draft_ok` 成立
  And 非 git 目錄：略過提交比對並於輸出印 `ne sources-commit-check git-unavailable`（`--json` 的 `ne` 含 `{field: sources-commit-check, reason: git-unavailable}`），其餘預檢照常，抓取照做、rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_2_E_1]"
```

```gherkin
# AT-130-2-E-2
# 對應 AC: AC-130-2（PRD AC-SI-30-2；R42 (b)(c)）`check` 以 sources_sha256 比對提交歷史、來源 id 須在表內（retired 仍認得）、git 不可用的處置、未提交的表不算歷史
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_2_E_2 -q

Feature: sources_sha256 對提交歷史

Scenario: 事件的來源表雜湊須等於其時間點之前最近一次提交的表
  Given 基線 `R`；以執行期組出的時間點 `B`（現在減十日）、`T1＝B`、`T2＝B 加一日`、`T3＝B 加二日`、`T4＝B 加三日`（皆帶 offset 的 ISO 字串與對應的 `GIT_COMMITTER_DATE`）；來源表 v1（兩筆：`s-live` 現役、`s-old` 帶 `retired: true`）與 v2（v1 加一筆 `s-new`）
  And 提交順序：C1 於 `T1` 提交 v1；手寫事件 E1（`t` 為 `T2`、`research.scan`、`sources_sha256` 為 v1 的雜湊、`sources` 為 `s-live`）；C2 於 `T3` 提交 v2；手寫事件 E2（`t` 為 `T4`，`sources_sha256` 仍為 v1 的雜湊）；每個研究事件各屬一個獨立運轉（先有該運轉的 `run.open`，使 `RESEARCH-MULTIPLE` 與 `RESEARCH-ORDER` 不介入）
  When 情境一：呼叫 `check --json`（上述歷史）
  And 情境二：另一份帳本，事件 E0 的 `t` 早於 `T1`（來源表尚無任何提交）；情境三：事件 E3 的 `sources` 含 `zz-unknown`、另一事件含 `s-old`（retired）
  And 情境四：把工作樹的來源表改成 v3 而不提交，再呼叫；情境五：把 `R` 複製成不含 `.git` 的目錄後呼叫；情境六：刪去來源表後呼叫（事件仍在）
  Then 情境一：`F(events.research)` 恰為 `(seq=<E2 的 seq>, SOURCES-SHA-MISMATCH)`（E1 為 PASS：`T2` 之前最近一次提交是 C1）
  And 情境二：含 `(seq=<E0 的 seq>, SOURCES-SHA-MISMATCH)`（`t` 之前沒有任何提交）；情境三：含 `(seq=<該事件的 seq> zz-unknown, SRC-UNKNOWN)`，`s-old` 不被判紅
  And 情境四：E1 仍為 PASS（未提交的表不是歷史）；情境五：`S(events.research)` 為 NE、`blocking` 為 false、含單一 finding `(-, SOURCES-HISTORY-NOT-ESTABLISHED)`
  And 情境六：`S(events.research)` 為 NE、`blocking` 為 true、碼 `SOURCE-UNAVAILABLE`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_2_E_2]"
```

```gherkin
# AT-130-2-E-3
# 對應 AC: AC-130-2（PRD AC-SI-30-2；R58 (c)）重導向把關：表外 host 與連接埠、非 http 與 https 的 scheme、https 降 http 與 http 升 https（scheme 不得改變；函式層用顯式同埠 URL）、第 6 跳皆拒；表內重導向至多 5 跳放行
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_2_E_3 -q

Feature: 重導向把關

Scenario: 重導向目標須屬允許集合；跳數有上限
  Given 基線 `R`；§5.4 `serve` 起伺服器（連接埠 `P`），路由：`/to-ok`（302 到本 host 同埠 `/ok`）、`/ok`（200 文字）、`/to-localhost`（302 到 `localhost` 同埠 `/ok`）、`/to-otherport`（302 到另一個連接埠）、`/to-ftp`（302 到 `ftp://` 目標）、`/to-file`（302 到 `file://` 目標）、`/c0`～`/c5`（`/cK` 302 到 `/c(K+1)`，`/c5` 回 200）、`/d0`～`/d6`（同型，`/d6` 回 200，故需 6 次重導向）；每個案例各自複製一份已開運轉的 `R`、以 `write_table` 提交單一來源（`url` 指向該案例的入口路由），並以 `relaxed()` 放寬政策
  When 對 `/to-ok`、`/to-localhost`、`/to-otherport`、`/to-ftp`、`/to-file`、`/c0`、`/d0` 各呼叫 `research --fetch --run RUN-SI-001`
  And 函式層：以字串直接呼叫 `fetch.check_redirect(from_url, to_url, allowed_hosts)`，`allowed_hosts` 為單一元素集合 `{example.com:8443}`，**URL 一律帶顯式連接埠 8443**（預設埠下 https 與 http 的 `hostname:port` 本來就不同，會被連接埠判準先拒、遮住 scheme 判準；原案例因此使「scheme 不得改變」沒有任何測試鎖住）：`https://example.com:8443/a` 到 `https://example.com:8443/b`；`https://example.com:8443/a` 到 `http://example.com:8443/b`（降級）；`http://example.com:8443/a` 到 `https://example.com:8443/b`（升級，反向）；`http://example.com:8443/a` 到 `http://example.com:8443/b`；`https://example.com:8443/a` 到 `https://other.example:8443/b`（另一 host）；`https://example.com:8443/a` 到 `ftp://example.com:8443/b`；`https://example.com:8443/a` 到 `file:///b`
  Then `/to-ok` 與 `/c0`（5 次重導向）：rc `0`、輸出含 `source s1 ok`
  And `/to-localhost`、`/to-otherport`、`/to-ftp`、`/to-file`、`/d0`（第 6 次重導向）：rc `1`（零來源成功）、輸出含 `source s1 FAIL redirect-refused`、事件帳本不變
  And 函式層：同 scheme 同埠的兩案（https 到 https、http 到 http）回傳 `None`；其餘五案（https 降 http、http 升 https、另一 host、`ftp://`、`file://`）皆回傳 `redirect-refused`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_2_E_3]"
```

```gherkin
# AT-130-2-E-4
# 對應 AC: AC-130-2（PRD AC-SI-30-2；R42 (c)）`sources_sha256` 對提交歷史的時間邊界：來源表的提交時間與事件 `t` 為同一秒放行（不晚於）、事件 `t` 早一秒即 `SOURCES-SHA-MISMATCH`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_2_E_4 -q -p no:xdist -o addopts=

Feature: 來源表提交時間邊界

Scenario: 提交時間等於事件時間放行；事件早一秒判不符；晚一秒放行
  Given 基線 `R`；以執行期組出的時間點 `Tc`（現在減一日，秒精度，帶 offset 的 ISO 字串與對應的 `GIT_COMMITTER_DATE`）；來源表 v1（單一現役來源 `s-live`；`write_table` 時 `commit` 為假）；每個情境各自複製一份 `R`，手寫事件帳本為 `run.open`（`RUN-SI-001`）加一筆 `research.scan`（`sources` 為 `s-live`、`sources_sha256` 為 v1 的雜湊、`fetched_at` 同該事件的 `t`）
  When 情境一：事件 `t` 為 `Tc`；情境二：事件 `t` 為 `Tc` 減 1 秒；情境三：事件 `t` 為 `Tc` 加 1 秒
  And 三個情境皆以 `commit_all(R, …, when=Tc)` 把來源表與事件帳本提交於同一個 commit（committer 時間恰為 `Tc`）後呼叫 `check --json`
  Then 情境一與情境三：`S(events.research)` 為 `PASS`、`F(events.research)` 為空（提交時間不晚於事件 `t`，等號放行）
  And 情境二：`F(events.research)` 恰為 `(seq=2, SOURCES-SHA-MISMATCH)`（事件 `t` 之前沒有任何提交含來源表）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_2_E_4]"
```

```gherkin
# AT-130-3-1
# 對應 AC: AC-130-3（PRD AC-SI-30-3；R58 (a)(b)(e)(f)）抓原始位元組、自算 sha256 與 changed 三態、原樣落家目錄、事件不存 url、請求形態固定且逐一發出
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_3_1 -q

Feature: 增量 digest 與抓取

Scenario: 成功抓取三個來源，原始位元組落地，changed 依上一筆而定
  Given 基線 `R`；§5.4 `serve` 路由：`/a`（1000 個位元組的 ASCII、`text/plain; charset=utf-8`）、`/b`（JSON、`application/json`）、`/c`（Atom、`application/atom+xml`），皆記錄請求；以 `write_table` 提交三個現役來源（`id` 依位元組序為 `s-a`、`s-b`、`s-c`）；`relaxed()`；開兩個運轉 `RUN-SI-001`、`RUN-SI-002`
  When 對 `RUN-SI-001` 呼叫 `research --fetch`；再對 `RUN-SI-002` 呼叫（三個來源內容不變）；把 `/b` 的內容改變後，另開 `RUN-SI-003` 呼叫
  Then 三次 rc 皆為 `0`；第一次 stdout 依序為三行 `source <id> ok sha256=<12 碼> bytes=<n> changed=true` 與 `ok research.scan seq=<N> run=RUN-SI-001`
  And 事件 `research.scan` 的鍵序為 `seq`、`t`、`kind`、`by`、`run`、`sources`、`sources_sha256`、`fetched_at`，`by` 為 `researcher`；`sources` 每個元素的鍵序恰為 `id`、`sha256`、`bytes`、`changed`、`http_status`；事件中沒有任何 `url` 字樣與候選數欄位；`sources_sha256` 等於提交的來源表位元組（CRLF 換 LF）的 sha256；`fetched_at` 帶 offset
  And `sha256` 等於測試端對伺服器原始位元組算出的雜湊（不做任何正規化）；`HOME/research/<id>/<sha12>.txt` 的位元組逐字等於伺服器內容；`HOME/research/<id>/latest` 的內容等於該 12 碼（無換行、無副檔名）
  And 第二次三個來源的 `changed` 皆為 `false`；第三次只有 `s-b` 的 `changed` 為 `true`
  And 請求形態：伺服器記錄的每個請求 `User-Agent` 為 `selfimproving-research/1`、`Accept-Encoding` 為 `identity`、不含 `Cookie`、`Authorization`、`Proxy-Authorization`；同一次抓取的請求依來源表順序逐一發出，伺服器量得的最大同時連線數為 1
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_3_1]"
```

```gherkin
# AT-130-3-E-1
# 對應 AC: AC-130-3（PRD AC-SI-30-3；R57 (d)(e)、R58 (b)(d)）失敗矩陣：逾時、非 2xx、超位元組（邊界）、非文字、缺 Content-Type、壓縮編碼、連線被拒；失敗來源不入事件
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_3_E_1 -q

Feature: 抓取失敗矩陣

Scenario: 各種失敗各有固定原因，成功的來源照記，rc 為 2
  Given 基線 `R`，`params.json` 的 `research_fetch_max` 為 20、`research_bytes_max` 為 1000、`research_timeout_seconds` 為 1；§5.4 `serve` 路由：`s-ok`（200 文字 100 位元組）、`s-edge`（200 文字恰 1000 位元組）、`s-big`（200 文字 1001 位元組）、`s-404`（404）、`s-500`（500）、`s-bin`（200、`image/png`）、`s-noct`（200、不帶 Content-Type）、`s-gz`（200 文字、`Content-Encoding: gzip`）、`s-slow`（延遲 3 秒才回 200）、`s-refused`（來源 url 指向一個已關閉的本機連接埠）；以 `write_table` 提交這十個現役來源（`id` 與路由同名）；`relaxed()`；已開運轉
  When 呼叫 `research --fetch --run RUN-SI-001`（文字形態），另在同一份新複本以 `--json` 呼叫
  Then rc 為 `2`；每個來源各一行：成功者 `source <id> ok …`，失敗者 `source <id> FAIL <原因>`
  And 失敗原因依來源為：`s-404` 與 `s-500` 為 `http-status`（detail 分別帶 404 與 500）、`s-big` 為 `too-large`（恰 1000 位元組的 `s-edge` 成功）、`s-bin` 與 `s-noct` 為 `non-text`、`s-gz` 為 `encoding`、`s-slow` 為 `timeout`、`s-refused` 為 `network`
  And 事件的 `sources` 恰為 `s-edge`、`s-ok` 兩筆（依來源表位元組序；失敗來源不入、不以舊 digest 代填）；輸出在 `obs-draft:` 之後每個失敗來源各一行草稿列（共 8 行，症狀含來源 id 與原因，座標的 `rc=` 為 2），每行 `draft_ok` 成立；`--json` 的 `failed` 陣列八個元素、鍵序為 `id`、`reason`、`detail`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_3_E_1]"
```

```gherkin
# AT-130-3-E-2
# 對應 AC: AC-130-3（PRD AC-SI-30-3；R57 (c)(d)(e)）零來源成功 rc 1 不寫事件；事件行超長 rc 1 但來源檔留作快取；零成功後仍可改記 offline 免掃
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_3_E_2 -q

Feature: 抓取的 rc 與事件語意

Scenario: 全失敗不寫事件；事件行超長不寫事件；JSON 形態鍵序固定
  Given 基線 `R`；§5.4 `serve`；已開運轉；`relaxed()`
  When 情境一：兩個來源皆回 404，呼叫 `research --fetch`；其後呼叫 `research --skip --reason offline --note 離線驗證`
  And 情境二：三個成功來源，另一份 `R` 的 `event_max_bytes` 設為 200，呼叫 `research --fetch`
  And 情境三：兩個成功來源，呼叫 `research --fetch --json`
  Then 情境一：抓取 rc 為 `1`、事件帳本不變、輸出含每個來源一行 `FAIL` 與草稿列；其後的 `--skip` rc 為 `0`（沒有寫過研究事件，不會 `RESEARCH-ALREADY`）
  And 情境二：rc 為 `1`、`codes(out)` 含 `EVENT-BYTES-OVER`、事件帳本不變；`HOME/research/<id>/` 下三個來源的落地檔與 `latest` 仍在（留作快取）
  And 情境三：rc 為 `0`；JSON 鍵序為 `ok`、`kind`、`seq`、`id`、`run`、`rc`、`sources`、`failed`、`obs_drafts`、`ne`，`kind` 為 `research.scan`、`id` 為 `null`、`failed` 與 `obs_drafts` 為空陣列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_3_E_2]"
```

```gherkin
# AT-130-3-E-3
# 對應 AC: AC-130-3（PRD AC-SI-30-3、ADR-SI-10；R57 (c)、R58）抓取在寫入鎖之外進行、鎖內重驗：抓取期間他人的改動使本次拒收且不追加
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 + threading
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_3_E_3 -q

Feature: 抓取在鎖外、鎖內重驗

Scenario: 抓取進行中可取得寫入鎖；抓取結束時依鎖內最新狀態重驗
  Given 基線 `R`；§5.4 `serve` 的 `/hold` 路由會等待測試放行訊號才回應，並在請求到達時通知測試；單一來源 `s-hold` 指向 `/hold`，已提交；已開運轉 `RUN-SI-001`；`relaxed()`；每個情境各自複製再執行
  When 在背景執行緒內以 `main` 呼叫 `research --fetch --run RUN-SI-001`（只有該執行緒使用輸出重導向），測試等待伺服器通知請求到達
  And 情境一：測試以 `lib.apply_lock.acquire(<鎖檔>, 2, 300)` 取得並釋放寫入鎖；情境二：測試以 `evwrite.append_event` 直接追加一筆 `research.skip`（`RUN-SI-001`）；情境三：測試直接追加 `run.close`（`RUN-SI-001`）；情境四：測試改動來源表內容並提交
  And 放行伺服器、等待背景執行緒結束
  Then 情境一：取鎖在 2 秒內成功（抓取期間不持鎖）；抓取結束 rc 為 `0`、事件帳本多一筆 `research.scan`
  And 情境二：抓取結束 rc 為 `1`、`codes(out)` 含 `RESEARCH-ALREADY`、事件帳本只多測試追加的那一筆（沒有 `research.scan`）
  And 情境三：rc 為 `1`、碼含 `RUN-NOT-OPEN`，沒有 `research.scan`；情境四：rc 為 `1`、碼含 `SOURCES-CHANGED`，沒有 `research.scan`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_3_E_3]"
```

```gherkin
# AT-130-3-E-4
# 對應 AC: AC-130-3（PRD AC-SI-30-3；R57 (b)(d)）全部來源皆失敗與現役來源為 0 筆，皆以碼 `ZERO-SUCCESS` 拒收（rc 1、不寫事件）；碼名與兩條路徑被釘住
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_3_E_4 -q -p no:xdist -o addopts=

Feature: ZERO-SUCCESS 拒收碼

Scenario: 抓取後零成功與預檢零現役各以 ZERO-SUCCESS 拒收
  Given 基線 `R` 與已提交的單純運轉：僅 `run-open` 得 `RUN-SI-001`（**未**記研究事件）；§5.4 `serve` 路由 `/a`（404）、`/b`（500）；`relaxed()`；事件帳本位元組 `before`；每個情境各自複製一份
  When 情境一：以 `write_table` 提交兩個現役來源 `s1`（`/a`）與 `s2`（`/b`），呼叫 `research --fetch --run RUN-SI-001`；另在一份新複本以 `--json` 呼叫
  And 情境二：新複本，來源表的兩個來源皆 `retired`，呼叫 `research --fetch --run RUN-SI-001`；其後呼叫 `research --skip --run RUN-SI-001 --reason offline --note 離線驗證`
  Then 情境一：rc 為 `1`、`codes(out)` 恰為 `ZERO-SUCCESS`；輸出依序含 `source s1 FAIL http-status 404`、`source s2 FAIL http-status 500`、`reject research ZERO-SUCCESS`；`obs-draft:` 之下有兩行草稿列（每個失敗來源各一，症狀含來源 id 與原因 `http-status`）；事件帳本位元組等於 `before`
  And 情境一的 `--json`：rc 為 `1`、`ok` 為 false、`codes` 恰一個元素且其 `code` 為 `ZERO-SUCCESS`、`failed` 恰兩個元素（`id` 為 `s1` 與 `s2`，`reason` 皆為 `http-status`）
  And 情境二：抓取 rc 為 `1`、`codes(out)` 恰為 `ZERO-SUCCESS`、伺服器收到的請求數為 0（預檢即拒）、事件帳本位元組等於 `before`；其後的 `--skip` rc 為 `0`（沒有留下研究事件，不會 `RESEARCH-ALREADY`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_3_E_4]"
```

```gherkin
# AT-130-3-E-5
# 對應 AC: AC-130-3（PRD AC-SI-30-3；R58 (d)）可接受的 Content-Type 集合被逐一釘住：`text/*` 與五個 `application/*` 形態放行，白名單外判 `non-text`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_3_E_5 -q -p no:xdist -o addopts=

Feature: Content-Type 白名單

Scenario: 六種可接受形態各自放行，白名單外的型別判 non-text
  Given §5.4 `serve`，每個路由回 200 與 5 位元組文字、各帶一個 `Content-Type`：可接受組七個——`text/plain`、`text/html; charset=utf-8`、`application/json`、`application/xml`、`application/atom+xml`、`application/rss+xml`、`application/xhtml+xml`；白名單外組五個——`application/octet-stream`、`image/png`、`application/pdf`、`application/x-ndjson`、`application/javascript`；放寬政策物件（`allow_loopback` 與 `allow_http` 皆為真）
  When 函式層：對每個路由各呼叫一次 `fetch.fetch_source(<url>, policy=<放寬政策>, timeout=5, max_bytes=1000, allowed_hosts={<該伺服器的 host:port>})`
  Then 可接受組的七個：皆回傳 `Fetched`（`status` 為 `200`、原始位元組為 5 個）
  And 白名單外組的五個：皆拋 `FetchError`，其 `reason` 為 `non-text`、`detail` 為該 Content-Type 的主型別
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_3_E_5]"
```

```gherkin
# AT-130-4-1
# 對應 AC: AC-130-4（PRD AC-SI-30-4 ③④；R44、R53 (f)）研究者候選列帶外部衍生與 src 且 src 在表內即合規；以候選加一個內部來源為 sources 的 PROP 受理
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_4_1 -q

Feature: 研究者候選只為候選

Scenario: 合規的研究者候選列通過 check，並可與內部來源並列充當提案的來源
  Given 基線 `R` 加已提交的來源表（含 `cc-note`）與研究者候選列 OBS-SI-011（標記 `面=流程;來源=代理;回報者=研究者;外部衍生=是;src=cc-note`）；已開運轉並補好研究事件
  When 呼叫 `check --json`；呼叫 `prop-new --cls D --source OBS-SI-011 --source OBS-SI-001 …`
  Then `F(row.provenance)` 與 `F(row.markers)` 皆不含 OBS-SI-011 的 finding
  And `prop-new` rc 為 `0`，事件的 `sources` 為兩個 ID（研究者候選照記，且因另有內部來源而受理）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_4_1]"
```

```gherkin
# AT-130-4-E-1
# 對應 AC: AC-130-4（PRD AC-SI-30-4 ③④；R44、R53 (f)）研究者候選的入帳鏈：缺外部衍生、缺 src、src 不在表內各被 check 判出；候選單獨充當 PROP 來源被拒
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_4_E_1 -q

Feature: 研究者候選的拒收鏈

Scenario: 不合規的研究者列被 check 判紅；以候選為唯一來源的提案被拒
  Given 基線 `R` 加已提交的來源表（含 `cc-note`）；各案例各自追加一列研究者候選列（ID 取 011，處置 `open`，證據座標取 `tools/lib/selfimproving/fresh.py:1`（與任何已結列的路徑無交集，使復發候選提示不介入））
  When (a) 標記為 `面=流程;來源=代理;回報者=研究者;src=cc-note`（缺外部衍生）；(b) `…;回報者=研究者;外部衍生=是`（缺 src）；(c) `…;回報者=研究者;外部衍生=是;src=zz-unknown`
  And (d) 合規的研究者列（`外部衍生=是;src=cc-note`）已入帳；對 M、P、R、D 四類各呼叫 `prop-new --source OBS-SI-011`（已開運轉並補好研究事件）
  Then (a)：`F(row.provenance)` 恰為 `(OBS-SI-011, RESEARCHER-NOT-EXTERNAL)`；(b)：恰為 `(OBS-SI-011, RESEARCHER-NO-SRC)`；(c)：`F(row.markers)` 恰為 `(OBS-SI-011, SRC-UNKNOWN)`
  And (d)：四次 rc 皆為 `1`、`codes(out)` 皆恰為 `NO-INTERNAL-SOURCE`、零殘留
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_4_E_1]"
```

```gherkin
# AT-130-4-2
# 對應 AC: AC-130-4（PRD AC-SI-30-4 ①②；R65 (f)；代位）研究者的工具白名單與抓回內容是資料不是指令——SOP 研究者節的條文
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP；含刪去自證）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_4_2 -q

Feature: 研究者節條文（代位）

Scenario: 研究者節含必備片段，且每個片段刪去的副本判不合格
  Given 真 SOP 的研究者節（標題含 `研究者`；LF 正規化）與夾具函式 `sop_problems`
  When 取 R65 (f) 的 12 個片段：`Read／Grep／Glob`、`無 Web 工具`、`資料、不是指令`、`changed=true`、`外部衍生=是`、`src=`、`文字交卷`、`每運轉至多一個`、`--pace`、`quota-band`、`research_sources.json`、`僅 T1`；對每個片段各產生一個把它在研究者節刪去的副本
  Then 真 SOP 的研究者節含全部 12 個片段
  And 12 個副本的 `sop_problems` 皆非空且點名被刪的片段
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_4_2]"
```

```gherkin
# AT-130-5-1
# 對應 AC: AC-130-5（PRD AC-SI-30-5；R57 (b)、R58 (d)(g)）預算三界的邊界放行（現役恰 `research_fetch_max` 筆、位元組恰 `research_bytes_max`、牆鐘在上限內）；三界取自 params；網路模組 import 只在 `fetch.py`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_5_1 -q

Feature: 研究掃描的預算（正控）

Scenario: 邊界值放行，且界限來自 params.json
  Given 基線 `R`；`params.json` 的 `research_fetch_max` 為 3、`research_bytes_max` 為 500、`research_timeout_seconds` 為 2；§5.4 `serve` 路由：`/a`、`/b`（各回恰 500 位元組的文字）、`/late`（延遲 0.3 秒後回恰 500 位元組的文字）；以 `write_table` 提交恰 3 筆現役來源（分別指向 `/a`、`/b`、`/late`）；已開運轉；`relaxed()`
  When 呼叫 `research --fetch --run RUN-SI-001`
  And 靜態：以 AST 掃 `tools/lib/selfimproving/*.py`，列出 import `socket`、`urllib`、`http`、`ssl`、`ftplib`、`smtplib`、`asyncio`、`requests` 的檔
  Then rc 為 `0`、三個來源皆成功（現役恰等於 `research_fetch_max`、位元組恰等於 `research_bytes_max`、延遲在逾時內都放行）
  And 靜態掃描列出的檔恰為 `fetch.py` 一個
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_5_1]"
```

```gherkin
# AT-130-5-E-1
# 對應 AC: AC-130-5（PRD AC-SI-30-5；R57 (b)(d)、R58 (d)、R29）預算超界：現役多 1 筆整次拒收、位元組多 1 判失敗、牆鐘超過判失敗；retired 不計；三鍵缺失 rc 3
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_5_E_1 -q

Feature: 研究掃描的預算（負控）

Scenario: 超界各依規則拒收或判失敗；退場來源不計入
  Given 基線 `R`；`research_fetch_max` 為 3、`research_bytes_max` 為 500、`research_timeout_seconds` 為 1；§5.4 `serve`；各案例各自複製一份已開運轉的 `R`；`relaxed()`
  When (a) 現役 4 筆；(b) 現役 3 筆加 2 筆 `retired`；(c) 單一來源回 501 位元組；(d) 單一來源延遲 3 秒才回；(e) `params.json` 依序缺 `research_fetch_max`、`research_bytes_max`、`research_timeout_seconds`（各一案，來源表合規）
  Then (a)：rc `1`、`codes(out)` 恰為 `FETCH-MAX`、請求數 0、事件帳本不變；(b)：rc `0`（退場者不計、也不被抓取，請求數為 3）
  And (c)：rc `1`（零成功）、輸出含 `source <id> FAIL too-large`、不截斷落地（家目錄無該來源檔）；(d)：rc `1`、輸出含 `source <id> FAIL timeout`
  And (e) 的三案：rc 皆為 `3`、stdout 空、stderr 點名缺的鍵、請求數 0
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_5_E_1]"
```

```gherkin
# AT-130-5-E-2
# 對應 AC: AC-130-5（PRD AC-SI-30-5；R58 (d)）牆鐘上限對慢滴回應成立：每 0.5 秒滴 1 位元組的本文在 `research_timeout_seconds` 內以 `timeout` 歸類返回；送完標頭後停滯的既有行為不變
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_5_E_2 -q -p no:xdist -o addopts=

Feature: 牆鐘上限（慢滴與停滯）

Scenario: 慢滴與停滯兩型回應皆在逾時上限附近返回並歸類 timeout
  Given §5.4 `serve` 路由：`/drip`（200、`text/plain`、`Content-Length` 為 100000，送完標頭後每 0.5 秒送出本文的 1 個位元組，選項 `drip`）、`/stall`（200、`text/plain`、`Content-Length` 為 100000，送完標頭後不送本文，選項 `stall`）；`research_timeout_seconds` 為 2、`research_bytes_max` 為 262144；測試結束必關伺服器（兩條路由的處理執行緒隨之結束）
  When 函式層：對 `/drip`、`/stall` 各呼叫一次 `fetch.fetch_source(<url>, policy=<放寬政策>, timeout=2, max_bytes=262144, allowed_hosts={<該伺服器的 host:port>})`，以 `time.monotonic()` 量呼叫前後的牆鐘
  And 指令層：`params.json` 的 `research_timeout_seconds` 為 2；以 `write_table` 提交單一來源（`/drip`）、已開運轉 `RUN-SI-001`、`relaxed()`；呼叫 `research --fetch --run RUN-SI-001`，量整個指令的牆鐘
  Then 函式層：兩次皆拋 `FetchError` 且 `reason` 為 `timeout`；兩次牆鐘皆落在 1.5 秒至 2.5 秒之間（上限 2 秒加減 0.5 秒）
  And 指令層：rc 為 `1`、輸出含 `source <id> FAIL timeout`、`codes(out)` 恰為 `ZERO-SUCCESS`、事件帳本位元組不變；整個指令的牆鐘小於 6 秒（含預檢與 git；不得等到伺服器停手）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_5_E_2]"
```

```gherkin
# AT-130-6-1
# 對應 AC: AC-130-6（PRD AC-SI-30-6；R46 (b)）改來源表不改判準指紋
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_6_1 -q

Feature: 指紋排除來源表

Scenario: 新增與修改 research_sources.json 不改指紋
  Given 基線 `R`，`MJ(check)` 的 `fingerprint` 為 `F0`
  When 把合規的 `research_sources.json` 加進協定目錄；再把其內容改成另一份合規表
  Then 兩次 `check` 的 `fingerprint` 皆等於 `F0`（`fingerprint_parts.manifest` 相同）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_6_1]"
```

```gherkin
# AT-130-6-E-1
# 對應 AC: AC-130-6（PRD AC-SI-30-6；R46 (b)）改 `params.json` 或 `metrics.md` 指紋變；排除只涵蓋一個檔名
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_130_6_E_1 -q

Feature: 指紋仍隨判準變

Scenario: 其他協定檔的任何改動都使指紋改變
  Given 基線 `R`，`fingerprint` 為 `F0`；每個案例各自複製再變異
  When (a) 把 `params.json` 的 `max_new_entries` 改成另一個合法值；(b) 把 `metrics.md` 的內容改一個字；(c) 在協定目錄新增 `extra.json`；(d) 在協定目錄新增子目錄檔 `sub/research_sources.json`；(e) 把 `metrics_rev` 改成另一個整數
  Then 五個案例的 `fingerprint` 皆不等於 `F0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_130_6_E_1]"
```

```gherkin
# AT-131-1-1
# 對應 AC: AC-131-1（PRD AC-SI-31-1；R59、R63 ⑥）`scan` 唯讀、離線、無狀態：前後 `git status --porcelain` 與 HEAD 相同、不連網、子行程只有環境淨化的 git、不受 GIT_DIR 污染
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_1_1 -q

Feature: scan 的純度

Scenario: scan 不改任何檔、不連網、不起 git 以外的子行程
  Given 依 §5.2 情境 `SC-SCAN` 建的 `R`（已提交、工作樹乾淨）；`snap0＝snap(R)`、`HEAD0＝git rev-parse HEAD`；`HOME` 內放一個哨兵檔
  When 以 `socket.socket.connect` 被替換為拋例外的狀態、並以記錄替身包住 `subprocess.run` 與 `subprocess.Popen`，呼叫 `scan` 與 `scan --json`
  And 另在環境變數 `GIT_DIR` 與 `GIT_INDEX_FILE` 指向他處的狀態下再呼叫 `scan --json`
  And 呼叫 `scan --help`
  Then 兩次呼叫 rc 皆為 `0`；`snap(R)` 等於 `snap0`、HEAD 等於 `HEAD0`；`connect` 未被呼叫；`HOME` 內檔案清單與位元組不變（`scan` 不讀不寫家目錄）
  And 記錄到的每個子行程的 argv 第一項是 `git`、其後接 `-C` 與 `R` 的解析後路徑，皆帶 `timeout`、`encoding`，子行程環境不含 `GIT_DIR` 等七個變數並設 `GIT_OPTIONAL_LOCKS` 為 `0`；`GIT_DIR` 污染情境的輸出與未污染時逐字相同
  And `scan --help` 的旗標集合恰為 `--json`、`--since`、`--repo`、`--help`（沒有筆數、日期、排程類旗標）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_1_1]"
```

```gherkin
# AT-131-1-E-1
# 對應 AC: AC-131-1（PRD AC-SI-31-1；R59 (a)）筆數、日期、排程類旗標一律是未知旗標；`--since` 只收 commit，其餘寫法 rc 3
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_1_E_1 -q

Feature: scan 的旗標限制

Scenario: 不收筆數、日期、排程與相對寫法
  Given 依 `SC-SCAN` 建的 `R`；`snap0＝snap(R)`
  When 依序呼叫 `scan --count 5`、`scan --limit 5`、`scan --date <今日 ISO 日期>`、`scan --schedule daily`、`scan --since <執行期以今日日期組出的 ISO 日期字串>`、`scan --since yesterday`、`scan --since HEAD~1`、`scan --since 3`、`scan --since <40 位 0 的字串>`（查無此 commit）、`scan --repo <普通檔案>`
  And 對照組：`scan --since <HEAD 的前 7 位 hex>`
  Then 前十次 rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 對照組 rc 為 `0`；`snap(R)` 等於 `snap0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_1_E_1]"
```

```gherkin
# AT-131-2-1
# 對應 AC: AC-131-2（PRD AC-SI-31-2；R59 (a)(b)(c)）候選列為九欄、至少一個座標、不超過列位元組上限，附加到帳本副本後 `check` 對這些列零 finding；草稿不寫入帳本
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_2_1 -q

Feature: scan 的候選列

Scenario: 缺陷帳本新立的 P≤2 未結列與窗內 commit 各產候選列，列自身通過 check
  Given 依 `SC-SCAN` 建的 `R`：起算點為最近一筆 `run.close` 的 `t`；缺陷帳本含 Q1（發現日期為起算點的 UTC 日期、P2、open）、Q2（同日、P1、`open（workaround-applied）`）、Q3（同日、P3、open）、Q4（同日、P2、`fixed@…`）、Q5（前一日、P2、open）；起算點之後有五類路徑的 commit（`AutoClaude/`、`AISDLC_SDD/`、`AgentConsole/`、`tools/lib/selfimproving/`、根層）；`snap0＝snap(R)`
  When 呼叫 `scan --json`
  Then `defects` 來源的候選恰為 Q1 與 Q2 各一筆（Q3 嚴重度不符、Q4 已結、Q5 早於起算日皆不產生）；`observations` 來源對每個窗內有 commit 觸及的模組桶各一筆候選
  And 每筆候選列拆成九欄、位元組數不超過 `row_max_bytes`、至少含一個 R16 的座標形態（缺陷候選的座標為該 DEF 號、桶候選的座標為 `commit <前 12 位 hex>`）；分類為 `bug`、嚴重度為 `P3`、處置為 `open`、標記為 `面=流程;來源=工具;回報者=scan`、情境為 `si scan（自動草稿）`
  And 候選列的 ID 自 `OBS-SI-011` 起依序連號；把全部候選列依序附加到 `R` 的帳本複本後呼叫 `check --json`，這些列的 finding 為零（`REOPEN-CANDIDATE` 提示除外）
  And `snap(R)` 等於 `snap0`（草稿不寫入帳本）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_2_1]"
```

```gherkin
# AT-131-2-E-1
# 對應 AC: AC-131-2（PRD AC-SI-31-2；R59 (b)(c)）過長的路徑清單被縮短以守住列上限；缺陷帳本欄位不全時該來源量不到、不產生候選
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_2_E_1 -q

Feature: scan 候選列的邊界

Scenario: 單一 commit 觸及大量長路徑時候選列仍不超過 700 位元組；缺陷帳本表頭不全不產候選
  Given 情境一：起算點之後的一個 commit 觸及 `AutoClaude/` 下 40 個各約 60 字元長的路徑；情境二：缺陷帳本主檔的表頭只有兩欄（P0 夾具的形態，缺 `發現日期`、`嚴重度`、`狀態`）
  When 對情境一呼叫 `scan --json`；對情境二呼叫 `scan --json`
  Then 情境一：`AutoClaude` 桶的候選列位元組數不超過 `row_max_bytes`（700），仍含 `commit <前 12 位 hex>` 座標，附加到帳本複本後 `check` 對該列零 finding
  And 情境二：`defects` 來源為 `status: unavailable`、`reason` 為 `ledger-header`，沒有缺陷候選；輸出該來源行為 `source defects 量不到：ledger-header`；整體 `unavailable_count` 至少為 1
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_2_E_1]"
```

```gherkin
# AT-131-2-E-2
# 對應 AC: AC-131-2（PRD §9.1 C4 的 `defs` 列〔ADR-SI-05〕；R45、R59 (b)）缺陷帳本的狀態分類與表格解析對既有解析器差分一致：同一批狀態字串與同一份合成帳本，兩邊輸出逐筆相同
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（差分對 `tools/check_defect_log_crossref.py` 的 `_classify` 與 `_load_ledger_status`）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_2_E_2 -q

Feature: defs 與既有缺陷帳本解析器的差分

Scenario: 狀態字串母體與合成缺陷帳本在兩個解析器下的結果逐筆相同
  Given 狀態字串母體 `STATUS-CORPUS`（§5.3）；兩組函式：`defs.classify_status(text)` 對 `check_defect_log_crossref._classify(text)`、`defs.load_ledger_status(path)` 對 `check_defect_log_crossref._load_ledger_status()`（後者以 `mock.patch.object(check_defect_log_crossref, _DEFECT_LOG, <tmp 帳本檔>)` 指向合成帳本；DEF 號於執行期以 `def_id(n)` 組出）
  When 對 `STATUS-CORPUS` 的每個字串，兩邊各呼叫一次
  And 對五份合成缺陷帳本，兩邊各呼叫一次：(a) 七欄表頭（同 §5.1 的缺陷帳本表頭）加四列，狀態依序為 `open`、`fixed@abc1234`、`wontfix`、`routed：外部`；(b) 同一 DEF 號出現兩列，前列 `open`、後列 `fixed@abc1234`；(c) 一列的證據欄多一個欄位分隔符，使該列欄數與表頭不符；(d) 一列的狀態欄為空白；(e) 沒有表頭的檔
  Then 母體內每個字串：兩邊的回傳值相等（含 `None`），且等於 §5.3 表中的預期分類
  And 五份帳本：兩邊回傳的 dict 相等（鍵為 DEF 號、值為分類或 `None`）；(a) 的四個鍵依序對應 `open`、`fixed`、`wontfix`、`routed`；(b) 只有一個鍵、值為 `fixed`（後列覆寫前列）；(c) 與 (d) 的該列值為 `None`；(e) 為空 dict
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_2_E_2]"
```

```gherkin
# AT-131-2-E-3
# 對應 AC: AC-131-2（PRD AC-SI-31-2；R59 (a)(b)）起算點的 commit 時間邊界：committer 時間恰等於起算時刻的 commit 不計入窗、晚一秒者計入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_2_E_3 -q -p no:xdist -o addopts=

Feature: scan 的窗邊界

Scenario: 起算時刻恰好的 commit 不產生候選，晚一秒的 commit 產生候選
  Given 依 §5.2 情境 `SC-SCAN-EDGE` 建 `R`：事件帳本為 `run.open`（`RUN-SI-001`）加 `run.close`（`no_event`，`t` 為錨點 `Ta`＝現在減 1 日、秒精度）；缺陷帳本只含不符合 (c) 的列；錨點之後的兩個 commit：`K1` 於 `Ta` 提交、觸及 `AutoClaude/x.py`；`K2` 於 `Ta` 加 1 秒提交、觸及 `AISDLC_SDD/z.md`；`snap0＝snap(R)`
  When 呼叫 `scan --json`（不帶 `--since`）
  Then rc 為 `0`；`anchor` 的 `kind` 為 `run.close`、`time` 等於 `Ta`
  And `buckets` 恰為 `AISDLC_SDD` 一個且計 1，沒有 `AutoClaude` 桶（`K1` 的 committer 時間等於起算時刻，不在窗內）
  And `candidates` 恰一筆，其 `bucket` 為 `AISDLC_SDD`、`row` 的證據座標為 `commit ` 接 `K2` 的前 12 位 hex
  And `snap(R)` 等於 `snap0`（唯讀）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_2_E_3]"
```

```gherkin
# AT-131-3-1
# 對應 AC: AC-131-3（PRD AC-SI-31-3；R59 (b)(e)(f)）每個來源各印一行；零候選整體印無事件，不印成通過
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_3_1 -q

Feature: scan 的零候選

Scenario: 五個來源都讀得到而沒有候選時，印無事件
  Given 依 §5.2 情境 `SC-SCAN-QUIET` 建的 `R`：起算點存在（一筆 `run.close`），缺陷帳本沒有符合列，起算點之後沒有 commit，且倉內有一個 `build/reports/` 下的 `.log` 檔與一個符合 `**/misstep_attribution*.jsonl` 的檔
  When 呼叫 `scan`（文字形態）與 `scan --json`
  Then 文字形態恰有五行來源（依序 `defects`、`observations`、`event_ledger`、`build_reports`、`probe_outputs`，各為 `source <id> 讀到 <N> 筆`），其後末行為 `無事件`；沒有 `candidates:` 行
  And `--json`：`status` 為 `no-event`、`unavailable_count` 為 `0`、`candidates` 為空陣列、`sources` 五個元素的 `status` 皆為 `read`；`anchor.kind` 為 `run.close`
  And 輸出全文不含 `通過`、`達標`、`綠` 三個字樣；rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_3_1]"
```

```gherkin
# AT-131-3-E-1
# 對應 AC: AC-131-3（PRD AC-SI-31-3；R59 (b)(e)）量不到的來源不併入零：整體改印無事件加量不到個數；有候選時仍列出量不到者
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_3_E_1 -q

Feature: scan 的量不到

Scenario: 量不到的來源逐一標出原因並計入整體
  Given 每個情境各自複製 `SC-SCAN-QUIET` 再變異
  When (a) 事件帳本不存在且 `migration_base_sha` 為 null（起算點量不到）；(b) 缺陷帳本主檔不存在；(c) 缺陷帳本表頭欄位不全；(d) 複製成不含 `.git` 的目錄；(e) 倉內沒有任何 `build/reports/` 下的符合檔；(f) 倉內沒有符合 `**/misstep_attribution*.jsonl` 的檔
  And (g) 情境 `SC-SCAN` 加上 (e)（有候選且有一個來源量不到）
  Then (a)：`defects` 與 `observations` 皆為 `量不到：anchor-unavailable`、`event_ledger` 為 `量不到：carrier-not-established`，末行為 `無事件（3 個來源量不到）`
  And (b)：`defects` 為 `量不到：ledger-missing`；(c)：`defects` 為 `量不到：ledger-header`；(d)：`observations` 為 `量不到：git-unavailable`；(e)：`build_reports` 為 `量不到：no-artifacts`；(f)：`probe_outputs` 為 `量不到：no-artifacts`；(b)～(f) 的末行各為 `無事件（<K> 個來源量不到）`，K 為該情境量不到的來源數
  And (g)：末行為 `候選 <M> 筆`（M 為候選數），輸出仍列出 `build_reports` 的 `量不到：no-artifacts` 一行；全部情境的輸出皆不含 `通過`、`達標`、`綠`；rc 皆為 `0`（`scan` 不接閘門 rc）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_3_E_1]"
```

```gherkin
# AT-131-4-1
# 對應 AC: AC-131-4（PRD AC-SI-31-4；R59 (d)）模組歸桶依序為 SelfImproving、AutoClaude、AISDLC_SDD、AgentConsole、根層
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_4_1 -q

Feature: 模組歸桶

Scenario: 路徑依判定順序歸入五個桶
  Given 純函式 `scan.bucket_of(path)`
  When 對下列路徑各呼叫一次：`tools/lib/selfimproving/check.py`、`tools/selfimproving.py`、`tools/probe/selfimproving_measure.py`、`tools/tests/test_selfimproving_check.py`、`docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/05_development/SelfImproving_Operations_SOP.md`；`AutoClaude/autoclaude/main.py`、`AutoClaude/docs/SelfImproving_note.md`；`AISDLC_SDD/FRAMEWORK_STATUS.md`；`AgentConsole/CLAUDE.md`；`tools/other.py`、`tools/tests/test_root_module_layout.py`、`docs/06_quality/AutoSDD_Defect_Log.md`、`CLAUDE.md`
  Then 前六個回傳 `SelfImproving`；`AutoClaude/autoclaude/main.py` 與 `AutoClaude/docs/SelfImproving_note.md`（非根層 `docs/**`，故不屬 SelfImproving）回傳 `AutoClaude`；`AISDLC_SDD/…` 回傳 `AISDLC_SDD`；`AgentConsole/…` 回傳 `AgentConsole`
  And `tools/other.py`、`tools/tests/test_root_module_layout.py`、`docs/06_quality/AutoSDD_Defect_Log.md`、`CLAUDE.md` 皆回傳 `根層`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_4_1]"
```

```gherkin
# AT-131-4-E-1
# 對應 AC: AC-131-4（PRD AC-SI-31-4；R59 (d)）非 repo 相對形態歸未分類並計數、不丟棄；觸及多個桶的 commit 各歸一次
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_4_E_1 -q

Feature: 歸桶的邊界

Scenario: 絕對路徑、含 .. 與空字串歸未分類；一個 commit 觸及兩桶時各歸一次
  Given 純函式 `scan.bucket_of(path)`；一份 `R`，起算點之後有一個 commit 同時觸及 `AutoClaude/a.py` 與 `tools/other.py`
  When 對 `/etc/x.md`、`../x.md`、`docs/../x.md`、空字串、執行期組出的磁碟機代號形態路徑各呼叫 `bucket_of`；對 `R` 呼叫 `scan --json`
  Then 五個非 repo 相對形態皆回傳 `未分類`
  And `scan --json` 的 `buckets` 含 `AutoClaude` 與 `根層` 各 1（該 commit 依其觸及的每個路徑各歸一次）、不含任何被丟棄的路徑
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_4_E_1]"
```

```gherkin
# AT-131-5-1
# 對應 AC: AC-131-5（PRD AC-SI-31-5；R65 (b)；代位）模組體檢任務書範本含五桶、工具白名單、唯讀、文字交卷等片段，且 PRD 入口表第 2 欄的每個反引號片段都在範本內
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SOP 與真 PRD）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_5_1 -q

Feature: 體檢任務書範本（代位）

Scenario: 範本含必備片段，且與 PRD 入口表同步
  Given 真 SOP 歸因者節內標題含 `模組體檢` 的子節文字（`tmpl`）；真 PRD 的「模組體檢入口表」（表頭列以 `| 模組桶 | 先讀（權威指引）` 起頭；取其資料列第 2 欄的全部反引號片段，不複寫第二份清單）
  When 檢查 `tmpl` 是否含：`AutoClaude`、`AISDLC_SDD`、`AgentConsole`、`根層`、`SelfImproving`、`Read／Grep／Glob／PowerShell`、`唯讀`、`不得 Write／Edit`、`git status --porcelain`、`文字交卷`、`流程摩擦`、`不並行扇出`、`零遞迴`；並檢查 PRD 入口表第 2 欄的每個片段是否都出現在 `tmpl`
  Then 全部片段都在 `tmpl` 內；PRD 入口表第 2 欄的片段數不少於 10 個（五列各至少兩個）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_5_1]"
```

```gherkin
# AT-131-5-E-1
# 對應 AC: AC-131-5（PRD AC-SI-31-5；R65 (b)；邊界型 P 加 D）範本判準自證；體檢前後對照夾具能偵測寫入，並誠實標出看不見被忽略檔的寫入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_131_5_E_1 -q

Feature: 體檢任務書判準自證與前後對照

Scenario: 刪片段的範本判不合格；前後對照偵測得到寫入但看不到被忽略的檔
  Given 真 SOP 的體檢任務書範本與 PRD 入口表片段清單；夾具函式 `tree_state(R)`（回傳 `git status --porcelain` 輸出與 HEAD）與 `states_equal`
  When 對 `tmpl` 的每個必備片段（含 PRD 入口表的每個片段）各產生一個刪去該片段的副本，呼叫判準
  And 對基線 `R` 取體檢前狀態後，各自模擬：(a) 只讀操作；(b) 新增一個未追蹤檔；(c) 修改一個已追蹤檔；(d) 提交一個新 commit；(e) 在 `.gitignore` 忽略的路徑建立一個檔
  Then 每個刪片段的副本判準皆不合格並點名該片段
  And 前後對照：(a) 與 (e) 判相同（(e) 即誠實劃界：被忽略的檔的寫入看不見）；(b)、(c)、(d) 皆判不同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_131_5_E_1]"
```

```gherkin
# AT-103-1-1
# 對應 AC: AC-103-1（PRD AC-SI-03-1 的 `si status` 半；R60）唯讀按需偵測啟動事件 (b)(c)(d)、印待決 PROP、運轉、冷卻、免掃分佈與根因鍵更改次數；(e) 印 NOT-EVALUABLE
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_103_1_1 -q

Feature: status 的狀態摘要

Scenario: 依情境 SC-STATUS 的事件與缺陷帳本，status 的每個鍵取值固定
  Given 依 §5.2 情境 `SC-STATUS` 建的 `R`（事件帳本 19 筆；缺陷帳本含 Q1、Q2、Q6 三個符合 (c) 的列及不符合者）；環境變數 `HOME` 與 `USERPROFILE` 指向空的 tmp 目錄、並移除 `CLAUDE_CONFIG_DIR`（§5.5 (b)；使逐字稿目錄取不到）；`snap0＝snap(R)`
  When 呼叫 `status --json` 與 `status`（文字形態）
  Then `status --json` 的頂層鍵序為 `events_detected`、`unavailable`、`open_runs`、`pending_props`、`suspended`、`cooldowns`、`skip_reasons`、`capacity`、`root_cause_changes`、`reopen_candidates`、`pending_windows`、`friction_reconcile`、`no_event`；rc 為 `0`
  And `events_detected` 的 `(trigger, subject)` 集合恰為 `(b, ATT-SI-001)`、`(c, <Q1 的 DEF 號>)`、`(c, <Q2>)`、`(c, <Q6>)`、`(d, PROP-SI-124)`；`unavailable` 為空陣列；`no_event` 為 false
  And `open_runs` 恰為 `RUN-SI-002` 一筆，其 `opened_seq` 為 10、`research` 為 `kind` 是 `research.skip` 且 `seq` 是 11、`props` 為 `PROP-SI-125`、`PROP-SI-126`
  And `pending_props` 恰為 `PROP-SI-125` 一筆（`rev` 為 1、`state` 為 `proposed`、`route` 為 `handoff:DEF`、`digest8` 為其事件 `digest` 的前 8 碼）；`suspended` 為 `null`；`cooldowns` 恰為一筆：`prop` 為 `PROP-SI-126`、`cls` 為 `D`、`target` 為 `docs/notes/other.md` 單一元素陣列、`root_cause` 為 `tools/a-b` 與 `tools/c-d`、`rejected_seq` 為 17
  And `skip_reasons` 為 `quota-band` 1、`offline` 1、`helmsman` 0（三鍵恆在）；`capacity` 為 `status` 是 `NOT-EVALUABLE`、`reason` 是 `capacity-verb-not-established`；`root_cause_changes` 為 `1`；`reopen_candidates` 為 `unsettled` 是 1；`pending_windows` 為空陣列；`friction_reconcile` 為 `status` 是 `NOT-EVALUABLE`、`reason` 是 `transcript-unavailable`
  And 文字形態至少含字樣 `capacity NOT-EVALUABLE`、`suspended`、`skip_reasons`，且各偵測到的事件各有一行；不含 `無事件`
  And `snap(R)` 等於 `snap0`（唯讀）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_103_1_1]"
```

```gherkin
# AT-103-1-E-1
# 對應 AC: AC-103-1（PRD AC-SI-03-1、AC-SI-17-2、AC-SI-23-1；R60、R35）零事件印無事件而不印通過；起算點量不到；SUSPENDED 折疊與恢復；冷卻解除；pending 窗；事件帳本缺席與壞行
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_103_1_E_1 -q

Feature: status 的邊界

Scenario: 無事件、量不到、SUSPENDED、冷卻解除、pending 窗各依規則呈現
  Given 每個情境各自建 `R`：(a) 無事件帳本、`migration_base_sha` 為 null；(b) 事件帳本存在（`SC-SCAN-QUIET` 的合規事件）、起算點存在、無符合 (c) 的缺陷；(c) 依 `SC-SUSP`（連續兩個壞窗，`stop_after_bad` 為 2）；(d) 在 (c) 之後手寫 `dec`（`dkind` 為 `resume`，`run` 為 `RUN-SI-001`）；(e) 依 `SC-STATUS` 再手寫 `dec`（`dkind` 為 `unblock`，指名 `PROP-SI-126`）；(f) 依 §5.2 情境 `SC-WINDOWS`（兩個 promoted 的 PROP 各有一筆 `mea.close`，其 `result` 皆為 `pending`，其中一筆之後有 `mea.amend` 把生效結果改為 `clean`）；(g) 事件帳本中夾一行無法解析的字串
  When 對各情境呼叫 `status --json` 與文字形態
  Then (a)：`events_detected` 為空、`unavailable` 恰為 `{trigger: c, reason: anchor-unavailable}`、`no_event` 為 true，文字形態含 `無事件（1 個來源量不到）`；`open_runs` 等事件類欄位為空狀態、rc `0`（事件帳本缺席不是錯誤）
  And (b)：`no_event` 為 true、`unavailable` 為空，文字形態含 `無事件` 而不含 `無事件（`；兩種情形的輸出皆不含 `通過`
  And (c)：`suspended` 為 `{run: RUN-SI-001}`（壞窗所在運轉）；(d)：`suspended` 為 `null`；(e)：`cooldowns` 為空陣列（`unblock` 解除冷卻）
  And (f)：`pending_windows` 恰含生效結果仍為 `pending` 的那一筆（`prop` 與 `close_seq`），被 `mea.amend` 改為 `clean` 者不在內；(g)：rc `0`、其餘鍵照常取值（壞行不中止）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_103_1_E_1]"
```

```gherkin
# AT-103-1-E-2
# 對應 AC: AC-103-1（PRD AC-SI-17-2、AC-SI-03-1；R35 (c)、R60）SUSPENDED 折疊的連續判準：兩個窗只有一個壞窗不暫停，連續兩個壞窗才暫停；`pending` 的窗不計入也不打斷連續
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_103_1_E_2 -q -p no:xdist -o addopts=

Feature: SUSPENDED 的連續判準

Scenario: 好壞混合的兩窗不暫停，連續兩壞窗才暫停
  Given 依 §5.2 情境 `SC-SUSP-MIX` 的建法（`stop_after_bad` 為 2）：`RUN-SI-001` 內各 PROP 走到 `promoted` 後 `mea.open`、`mea.close`，依序的 `result` 依情境取——(a) `clean`、`recurred`；(b) `recurred`、`clean`；(c) `recurred`、`rolled-back`；(d) `recurred`、`pending`、`rolled-back`；每個情境各自建一份 `R`
  When 對各情境呼叫 `status --json`
  Then (a) 與 (b)：`suspended` 為 `null`
  And (c) 與 (d)：`suspended` 為 `{run: RUN-SI-001}`（(d) 的 `pending` 窗不計入也不打斷連續）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_103_1_E_2]"
```

```gherkin
# AT-103-1-E-3
# 對應 AC: AC-103-1（PRD AC-SI-03-1、NFR-SI-09-2；R60）`pending_props` 含 `verified` 狀態；啟動事件偵測窗以最近一筆 `run.close` 為界、已處理的事件不重複偵測；`friction_reconcile` 的兩種 NOT-EVALUABLE 原因
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_103_1_E_3 -q -p no:xdist -o addopts=

Feature: status 的待決、偵測窗與對帳

Scenario: verified 也算待決；run.close 之前已處理的確認不重複偵測；逐字稿目錄存在時原因為 parser-not-established
  Given 環境變數 `HOME` 與 `USERPROFILE` 指向空的 tmp 目錄並移除 `CLAUDE_CONFIG_DIR`（§5.5 (b)；情境 (c) 另行佈置）
  When 情境 (a)：對 §5.2 `SC-LEGAL` 建的 `R` 呼叫 `status --json`
  And 情境 (b)：依 §5.2 `SC-STATUS-WIN` 的前五筆事件建 `R` 呼叫 `status --json`；再追加第 6～9 筆事件後再呼叫一次
  And 情境 (c)：事件帳本為任一合規者；把 `CLAUDE_CONFIG_DIR` 指向 tmp 內的目錄 `C`，並在 `C/projects/<slug>/` 建出空目錄（`<slug>` 依 R60 (c) 的規則，由測試端獨立以 `re.sub` 自 `R` 的解析後絕對路徑算出）；呼叫 `status --json`；再移除該 `<slug>` 目錄後呼叫一次
  Then (a)：`pending_props` 的 `(id, state)` 集合恰為 `(PROP-SI-128, proposed)`、`(PROP-SI-129, proposed)`、`(PROP-SI-131, verified)`、`(PROP-SI-132, verified)`、`(PROP-SI-133, verified)`、`(PROP-SI-134, proposed)`；`approved` 的 `PROP-SI-130` 與 `returned` 的 `PROP-SI-135` 等其餘狀態皆不在內
  And (b)：前五筆之後 `events_detected` 為空陣列、`no_event` 為 true（`ATT-SI-001` 的確認發生在該 `run.close` 之前，不重複偵測）；追加後 `events_detected` 的 `(trigger, subject)` 恰為 `(b, ATT-SI-002)`、`no_event` 為 false
  And (c)：`<slug>` 目錄存在時 `friction_reconcile` 為 `status` 是 `NOT-EVALUABLE`、`reason` 是 `transcript-parser-not-established`；移除後 `reason` 為 `transcript-unavailable`；兩者皆不是 `measured`、不含任何數字計數
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_103_1_E_3]"
```

```gherkin
# AT-132-5-1
# 對應 AC: AC-132-5（PRD AC-SI-32-5；R61）`export --json` 五個 kind 的頂層鍵序與 items 形態；唯讀離線；`schema_rev` 起於 1
# 測試類型: Contract
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_132_5_1 -q

Feature: export 的輸出契約

Scenario: 五個 kind 各自輸出固定形態的單一 JSON 文件
  Given 依 §5.2 情境 `SC-EXPORT` 以 CLI 建的 `R`（`RUN-SI-001` 開著且有研究免掃、`ATT-SI-001` 與其確認、`PROP-SI-124`〔loop〕、`PROP-SI-125`〔`handoff:T1`〕，內容檔俱在；另有 `RUN-SI-002` 以 `no_event` 關閉）；`snap0＝snap(R)`
  When 對 `observations`、`events`、`proposals`、`runs`、`status` 各呼叫 `export --json --kind <k>`
  Then 五次 rc 皆為 `0`；stdout 各為單一 JSON 文件加 LF（UTF-8 位元組直寫、無 BOM）；頂層鍵序為 `schema_rev`、`kind`、`generated_at`、`head_sha`、`items`、`next_since`、`truncated`、`ne`、`problems`；`schema_rev` 為 `1`、`head_sha` 等於 `HEAD`、`generated_at` 帶 offset
  And `observations`：`items` 為 10 個元素，鍵序為 `id`、`time`、`context`、`symptom`、`evidence`、`category`、`severity`、`disposition`、`marks`、`marks_kv`、`line`；`marks_kv` 為標記欄解析後的鍵值物件；`line` 等於該列在帳本檔的 1 起算實體行號（測試端以逐行掃描獨立算出）
  And `events`：`items` 與事件帳本逐行 `json.loads` 的結果逐一相等（不加鍵、不減鍵）；`proposals`：兩個元素，鍵序為 `id`、`state`、`route`、`cls`、`action`、`run`、`rev`、`digest`、`target`、`touched`、`touched_count`、`sources`、`created_seq`、`last_seq`、`verdict`、`flags`、`cooldown`、`card`，其 `touched` 等於由最新 rev 的 `.patch` 獨立導出的路徑陣列
  And `runs`：元素鍵序為 `id`、`opened_seq`、`closed_seq`、`trigger`、`head_sha`、`research`、`prop_ids`、`outcome`（`RUN-SI-001` 未關，`outcome` 為 `null`；`RUN-SI-002` 為字串 `no_event`）；`status`：`items` 為單元素陣列
  And `snap(R)` 等於 `snap0`（唯讀）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_132_5_1]"
```

```gherkin
# AT-132-5-E-1
# 對應 AC: AC-132-5（PRD AC-SI-32-5；R61）用法錯誤 rc 3；游標與截斷；`--id` 找不到回空；事件帳本缺席的 ne 標示
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_132_5_E_1 -q

Feature: export 的邊界

Scenario: 旗標錯誤 rc 3；分頁以 next_since 銜接；缺載體標 ne
  Given 依 `SC-EXPORT` 建的 `R`（事件帳本含 `seq` 為 1～N 的連續事件，`export_limit_max` 為 500）；另一份無事件帳本的 `R0`
  When 情境一（rc 3）：缺 `--json`；缺 `--kind`；`--kind bogus`；`--limit 0`；`--limit 501`；`--since -1`；`--since abc`；`--since 1 --kind status`；`--id X --kind events`；`--id X --kind observations`；`--id X --kind status`；`--id bad --kind proposals`；`--id bad --kind runs`
  And 情境二（分頁）：`--kind events --limit 3`；再以前一頁的 `next_since` 呼叫 `--since <next_since> --limit 3`，直到最後一頁
  And 情境三：`--kind proposals --id PROP-SI-124`；`--kind proposals --id <執行期組出的不存在 PROP 號>`
  And 情境四：對 `R0` 呼叫 `events`、`proposals`、`runs`、`status` 四個 kind
  Then 情境一的 13 次呼叫：rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭
  And 情境二：第一頁 `items` 為 3 筆、`truncated` 為 true、`next_since` 等於第 3 筆的 `seq`；依序銜接所得全部 `seq` 恰為 1～N 無重複無遺漏；最後一頁 `truncated` 為 false、`next_since` 為 `null`
  And 情境三：第一次 `items` 恰為該 PROP 一筆；第二次 `items` 為空陣列、rc 為 `0`
  And 情境四：四個 kind 的 `ne` 皆含 `{field: events, reason: carrier-not-established}`；`events`、`proposals`、`runs` 的 `items` 為空陣列，`status` 的 `items` 為全空狀態的單元素；rc 皆為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_132_5_E_1]"
```

```gherkin
# AT-132-5-E-2
# 對應 AC: AC-132-5（PRD AC-SI-32-5、AC-SI-32-1 的前提；R61）與 `status`、`card` 差分一致；不讀不印家目錄；壞列與壞行入 problems；被竄改的內容檔使 card 為 null 並標 ne
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_132_5_E_2 -q

Feature: export 的差分與隔離

Scenario: export 與 status、card 逐字一致；家目錄內容不外洩；壞資料不中止
  Given 依 `SC-EXPORT` 建的 `R`；`HOME` 內放一個含哨兵字串的檔（`research/sentinel.txt`）；`snap0＝snap(R)`；環境變數 `HOME` 與 `USERPROFILE` 指向空的 tmp 目錄、並移除 `CLAUDE_CONFIG_DIR`（§5.5 (b)；`status` 的 `friction_reconcile` 因而恆為 NOT-EVALUABLE，`export` 與 `status` 的逐字比對不受開發機真實逐字稿影響）
  When 情境一：對 `R` 呼叫 `export --json --kind status`、`status --json`、`export --json --kind proposals`、`card <每個 PROP>`
  And 情境二：在帳本複本加一個只有 8 欄的壞列、在事件帳本複本夾一行非 JSON 的壞行，呼叫 `export --json --kind observations`、`export --json --kind events`
  And 情境三：把 `PROP-SI-124` 的 `r1.patch` 末尾多加一行後呼叫 `export --json --kind proposals`
  Then 情境一：`status` 的 `items[0]` 與 `status --json` 輸出的物件相等；`proposals` 每個元素的 `card` 逐字等於對應的 `card` 輸出文字
  And 所有 `export` 輸出皆不含哨兵字串；`HOME` 內檔案與位元組不變；`snap(R)` 等於 `snap0`
  And 情境二：`observations` 的壞列元素為 `line`、`raw`、`valid`（false）三鍵，`problems` 含 `ROW-ARITY`；`events` 的 `items` 不含壞行、`problems` 含對應的結構問題；兩者 rc 皆為 `0`
  And 情境三：`PROP-SI-124` 的 `card` 為 `null`，`ne` 含 `{field: proposals.PROP-SI-124.card, reason: CARD-INCONSISTENT}`；另一個 PROP 的 `card` 不受影響；rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_132_5_E_2]"
```

```gherkin
# AT-132-5-E-3
# 對應 AC: AC-132-5（PRD AC-SI-32-5；R61）`truncated` 的邊界：筆數恰等於 `--limit` 不是截斷，多一筆才是
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_132_5_E_3 -q -p no:xdist -o addopts=

Feature: export 的截斷邊界

Scenario: 筆數恰等於 limit 時不截斷，多一筆時截斷
  Given 基線 `R`（`export_limit_max` 為 500）；兩份事件帳本複本：(a) 恰 3 筆合規事件（`seq` 為 1～3）；(b) 恰 4 筆（`seq` 為 1～4）
  When 對 (a)、(b) 各呼叫 `export --json --kind events --limit 3`；另對 (a) 呼叫 `--limit 4` 與 `--limit 2`
  Then (a) 的 `--limit 3`：`items` 為 3 筆、`truncated` 為 false、`next_since` 為 `null`
  And (b) 的 `--limit 3`：`items` 為 3 筆（`seq` 為 1～3）、`truncated` 為 true、`next_since` 為 `3`
  And (a) 的 `--limit 4`：`items` 為 3 筆、`truncated` 為 false、`next_since` 為 `null`；(a) 的 `--limit 2`：`items` 為 2 筆、`truncated` 為 true、`next_since` 為 `2`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_132_5_E_3]"
```

```gherkin
# AT-140-2-1
# 對應 AC: AC-140-2（本檔自增；PRD §9.2〈export 輸出〉；R61 穩定性）`status`、`scan`、`card`、`export` 連續兩次輸出除 generated_at 外逐字相同；UTF-8、LF、無 BOM、JSON 鍵序固定
# 測試類型: Contract
# 自動化工具: pytest + tmp 目錄 + 真 git + subprocess（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_140_2_1 -q

Feature: 輸出 schema 穩定

Scenario: 同一狀態下連續兩次輸出相同，且位元組層級不受主控台編碼影響
  Given 依 `SC-EXPORT` 建的 `R`（已提交、工作樹乾淨）；子行程環境依 §5.5 (b) 隔離逐字稿目錄（環境變數 `HOME` 與 `USERPROFILE` 指向空的 tmp 目錄、移除 `CLAUDE_CONFIG_DIR`；`status --json` 的 `friction_reconcile` 因而恆為 NOT-EVALUABLE，兩次輸出才可能逐位元組相同）
  When 以子行程（`PYTHONIOENCODING` 為 `cp950`）連續兩次執行：`status --json`、`scan --json`、`card PROP-SI-124 --json`、`export --json --kind <五個 kind 各一>`
  Then 兩次輸出逐位元組相同（`export` 去掉 `generated_at` 的值後相同）；每個輸出的位元組以嚴格 UTF-8 解碼成功、開頭不是 BOM、不含 CR
  And 各 JSON 以 `object_pairs_hook` 取得的鍵序等於其規則所列（`status` 為 R60、`scan` 為 R59 (f)、`card` 為 R56 (e)、`export` 為 R61）；`scan`、`card`、`export` 的 `schema_rev` 皆為 `1`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_2_1]"
```

```gherkin
# AT-140-2-E-1
# 對應 AC: AC-140-2（本檔自增；R61）輸出不得含不穩定來源：雜湊種子、cwd、時區、絕對路徑、行程號
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + subprocess（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_140_2_E_1 -q

Feature: 輸出的確定性

Scenario: 改變雜湊種子、工作目錄與時區，輸出不變；輸出不洩漏本機路徑
  Given 依 `SC-EXPORT` 建的 `R`；兩組子行程環境：(A) `PYTHONHASHSEED` 為 0、cwd 為 `R`、`TZ` 為 UTC；(B) `PYTHONHASHSEED` 為 12345、cwd 為另一個放有誘餌檔的 tmp 目錄（命令列以 `--repo` 指向 `R`）、`TZ` 為另一個時區；兩組環境皆依 §5.5 (b) 隔離逐字稿目錄（環境變數 `HOME` 與 `USERPROFILE` 各指向自己的空 tmp 目錄、移除 `CLAUDE_CONFIG_DIR`），使 `friction_reconcile` 恆為 NOT-EVALUABLE
  When 在兩組環境各執行 `status --json`、`scan --json`、`card PROP-SI-124`、`export --json --kind proposals`、`export --json --kind events`
  Then 兩組環境的輸出（`export` 去掉 `generated_at` 的值後）逐字相同
  And 各輸出不含 `R` 與 `HOME` 的絕對路徑字串、不含行程號；除 `generated_at` 與事件自帶的 `t` 之外沒有以呼叫當下時鐘產生的時間值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_2_E_1]"
```

```gherkin
# AT-140-2-E-2
# 對應 AC: AC-140-2（本檔自增；R28 (a)、R56 (e)、R59 (f)、R60、R61）含非 ASCII 內容的 `--json` 輸出以 UTF-8 位元組直寫、不跳脫（`ensure_ascii=False`），在 `PYTHONIOENCODING=cp950` 的管線下亦然
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + subprocess（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_export_status.py -k AT_140_2_E_2 -q -p no:xdist -o addopts=

Feature: JSON 輸出的 UTF-8 直寫

Scenario: 含中文的 JSON 輸出為 UTF-8 原字，沒有 \uXXXX 跳脫
  Given 環境變數 `PYTHONIOENCODING` 為 `cp950`；測試端為每個呼叫備一份含中文內容的狀態：(a) 事件帳本含 `by` 為 `主控` 的 `run.open`；(b) 基線 `R` 的 OBS 帳本（九欄含中文）；(c) `SC-STATUS-WIN` 的前四筆事件，使 `status` 偵測到一筆 (b) 事件（detail 含中文）；(d) `SC-SCAN-EDGE`，使 `scan` 產生候選列（含 `自動草稿`）；(e) 以 CLI 建好一個 PROP，使 `card --json` 的 `text` 含中文；(f) 對不存在的運轉號呼叫 `run-close` 得拒收（`obs_draft` 含中文）
  When 以子行程（`[sys.executable, <入口絕對路徑>, …]`，§5.5 (d)）逐一呼叫：(a) `export --json --kind events`；(b) `export --json --kind observations`；(c) `status --json`；(d) `scan --json`；(e) `card <PROP> --json`；(f) `run-close --run <不存在的運轉號> --by main --json`
  Then 六個呼叫的 stdout 位元組皆能以嚴格 UTF-8 解碼、開頭沒有 BOM、不含 CR、結尾為單一 LF，且 `json.loads` 成功
  And 各 stdout 位元組含對應的中文原字（(a) 為 `主控` 的 UTF-8 位元組；(c) 為 `同一症狀`；(d) 與 (f) 為 `自動草稿`；(e) 為 `一、症狀`；(b) 為任一 OBS 列的中文欄位內容），且不含反斜線加小寫 `u` 的跳脫序列
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_140_2_E_2]"
```

```gherkin
# AT-143-1-1
# 對應 AC: AC-143-1（本檔自增；PRD §9.4〈能力登記與純度判準〉、§9.7 #47；R63）真套件逐檔符合所登能力類別；唯讀動詞的 import 閉包只含 ro 檔；網路 import 只在 fetch.py；入口模組層級只 import ro
# 測試類型: Unit
# 自動化工具: pytest（AST 與正規式靜態掃描；唯讀存取真原始碼）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_143_1_1 -q

Feature: 純度與能力登記（真樹）

Scenario: 登記表與套件一致，逐檔、閉包、入口三層都合規
  Given 測試檔內的登記表常數 `CAPABILITY`（24 個鍵：19 個 `ro`、3 個 `rw`、2 個 `net`，見 R63）；真 repo 的 `tools/lib/selfimproving/*.py` 與 `tools/selfimproving.py`（唯讀）；判準函式 `capability_problems(pkg_dir, registry, entry_file)` 回傳問題清單
  When 呼叫 `capability_problems`（真樹與真登記表）
  Then 回傳空清單
  And 套件內 `*.py` 的檔名集合等於 `CAPABILITY` 的鍵集合；類別計數為 `ro` 19、`rw` 3、`net` 2
  And 以 AST 另行獨立驗證：import 網路模組（`socket`、`urllib`、`http`、`ssl`、`ftplib`、`smtplib`、`asyncio`、`requests`）的檔恰為 `fetch.py`；含 `subprocess` 字樣的檔恰為 `git.py`；`check.py`、`status.py`、`scan.py`、`export.py`、`card.py` 的相對 import 閉包皆只含 `ro` 檔
  And 入口 `tools/selfimproving.py` 的模組層級 import 只含 `ro` 類模組（`writeverbs` 與 `research` 只在 handler 函式內 import）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_143_1_1]"
```

```gherkin
# AT-143-1-E-1
# 對應 AC: AC-143-1（本檔自增；R63）判準自證：合成套件樹的各種違規各被判出，合法合成樹為對照
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成套件樹）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_143_1_E_1 -q

Feature: 能力登記判準非恆真

Scenario: 新檔未登記、類別越界、閉包越界、入口越界各被判紅
  Given 夾具 `make_pkg(files, registry)` 在 tmp 內建一個合成套件目錄與入口檔；合法對照樹：`ro` 檔 `a.py`、`rw` 檔 `w.py`（寫檔）、`net` 檔 `f.py`（import `urllib`）與 `r.py`（相對 import `f`）、唯讀動詞檔 `check.py`（只相對 import `a`）、入口只在函式內 import `w`
  When 對對照樹呼叫 `capability_problems`；再各自對下列單一變異的樹呼叫：(a) 多一個未登記的 `x.py`；(b) 登記表有鍵而檔不存在；(c) `ro` 檔含 `write_text(`；(d) `ro` 檔含 `subprocess` 字樣（非 `git.py`）；(e) `ro` 檔 import `socket`；(f) `rw` 檔 import `urllib`；(g) `rw` 檔含 `subprocess` 字樣
  And (h) `net` 類的 `r.py` 直接 import `http`；(i) `check.py` 相對 import `w`（`rw`）；(j) `status.py` 相對 import `fold.py`，而 `fold.py` 相對 import `w`（傳遞性）；(k) 入口模組層級 import `w`；(l) 任一檔 import 第三方套件 `yaml`；(m) 登記表的類別值為 `xx`
  Then 對照樹回傳空清單
  And 變異 (a)～(m) 每一個都回傳非空清單，且訊息點名違規的檔與規則（子情境失敗訊息須指出是哪個變異）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_143_1_E_1]"
```

```gherkin
# AT-143-1-E-2
# 對應 AC: AC-143-1（本檔自增；R63 ⑤⑥、R64、R36 (g)）動態純度：唯讀動詞行程不載入寫入與網路模組；全部動詞零網路；常駐機制禁字樣零命中且樣本自證
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_143_1_E_2 -q

Feature: 動態純度與常駐機制禁字樣

Scenario: 載入面、連線面與禁字樣三個動態與靜態面都合規
  Given 依 `SC-EXPORT` 建的 `R`（含事件帳本、提案內容檔，另提交一份來源表）；乾淨直譯器子行程夾具 `loaded_modules(argv)`（於子行程內 import `selfimproving`、呼叫 `main(argv)`，回傳 `sys.modules` 中以 `lib.selfimproving.` 起頭的名稱）
  When 對 `check`、`status`、`scan`、`export --json --kind status`、`card PROP-SI-124` 各呼叫 `loaded_modules`；另對「只 import `selfimproving` 而不呼叫 `main`」取一次
  And 以 `socket.socket.connect` 被替換為拋例外的狀態，對 `status`、`scan`、`card`、`export`、`check`、`run-open`、`run-close`、`attr`、`attr-confirm`、`attr-reject`、`prop-new`、`prop-revise`、`research --skip` 各執行一次（旗標合規、狀態依序銜接）
  And 禁字樣掃描：對 `tools/selfimproving.py` 與套件內每個 `*.py` 套用 R64 的 14 個正規式；另讀根 `.claude/settings.json` 全文
  And 對 `check` 另做 P0 的動態純度：在含事件帳本、提案內容檔與來源表的 `R` 上，呼叫前後 `snap(R)` 與 `git status --porcelain` 相同，記錄到的子行程皆為環境淨化的 git
  Then 五個唯讀動詞與只 import 入口的 `loaded_modules` 結果皆不含 `lib.selfimproving.evwrite`、`lib.selfimproving.propfiles`、`lib.selfimproving.writeverbs`、`lib.selfimproving.fetch`、`lib.selfimproving.research`
  And 十三個呼叫期間 `connect` 一次都未被觸發
  And 14 個正規式在全部檔案零命中；14 個各以含該字樣的合成文字驗證會被判出（樣本自證）；根 `.claude/settings.json` 全文不分大小寫不含 `selfimproving`
  And `check` 的動態純度成立（零副作用、子行程只有環境淨化的 git、涵蓋追加的 7 項）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_143_1_E_2]"
```

```gherkin
# AT-134-1-1
# 對應 AC: AC-134-1（PRD AC-SI-34-1；R62 (a)(b)）真登記表可解析出至少一列，每個 repo 內路徑在磁碟至少命中一檔；兩種檔名承繼寫法與不判的片段
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 SSOT；合成 SSOT 驗解析規則）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_1_1 -q

Feature: 落點登記表對磁碟

Scenario: 真登記表全綠，解析規則對各種片段寫法判對
  Given 判準函式（以 `repo_root` 為參數）；真 repo 的 `docs/02_architecture/Root_Layout_and_Module_Placement.md`
  When 對真 repo 呼叫判準的 AC-SI-34-1 部分
  And 另對合成 repo（tmp 內放合成 SSOT 與對應檔案）呼叫：一個登記列的欄內含「帶目錄的片段」後接一個「無目錄前綴的檔名片段」（承繼同欄前一個帶目錄片段為基底），另一列使用「目錄片段加檔名片段」並列的寫法；含空白的指令字串片段、以 `~` 或 `$` 起頭的片段、裸詞片段（無 `/`、無已知副檔名、無 `*`）、含 `*` 的 glob 片段
  Then 真 repo：回傳空清單，且解析出的登記列數至少為 1、解析出的路徑候選數至少為 1
  And 合成 repo：承繼寫法的檔名片段在其基底之下命中檔案即過；指令字串、repo 外片段、裸詞皆不被判；glob 片段在磁碟至少命中一檔即過
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_1_1]"
```

```gherkin
# AT-134-1-E-1
# 對應 AC: AC-134-1（PRD AC-SI-34-1；R62 (b)）登記路徑在磁碟缺一即紅並印列名與路徑；解析出 0 列或缺登記表節即紅
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成 repo）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_1_E_1 -q

Feature: 落點登記表的負控

Scenario: 路徑缺失與解析不到登記表都判紅
  Given 合成 repo 的 SSOT 含一個 `## 3.` 節與一列六欄的登記資料（路徑皆存在）作為對照
  When 情境一：刪去其中一個登記路徑對應的檔；情境二：glob 片段改成磁碟上零命中；情境三：目錄片段改成存在但不含任何檔的目錄；情境四：SSOT 沒有 `## 3.` 節；情境五：`## 3.` 節內沒有任何六欄資料列
  Then 對照組：回傳空清單
  And 情境一至三：各回傳一筆問題，訊息含該登記列名與缺失的路徑；情境四與五：各回傳問題（不得以 0 列通過）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_1_E_1]"
```

```gherkin
# AT-134-2-1
# 對應 AC: AC-134-2（PRD AC-SI-34-2；R62 (c)）前綴散落鎖的合規情形：真樹以現查名冊為綠；同前綴不足 3 支、已成套件、名冊豁免皆綠
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成 `tools/lib/`）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_2_1 -q

Feature: tools/lib 前綴散落（合規情形）

Scenario: 真樹為綠；合成樹的各合規形態為綠
  Given 判準函式 `prefix_problems(repo_root, roster, ceiling)`；測試檔內的 shrink-only 名冊常數與天花板常數（初值為對真樹現查的結果）
  When 對真 repo 呼叫；另對合成 `tools/lib/` 呼叫：(a) 同前綴 2 支且無套件；(b) 同前綴 3 支但 `tools/lib/<前綴>/` 套件目錄存在；(c) 同前綴 3 支且前綴在名冊內、名冊與天花板相等；(d) 不同前綴各 1 支
  Then 真 repo 回傳空清單；(a)～(d) 皆回傳空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_2_1]"
```

```gherkin
# AT-134-2-E-1
# 對應 AC: AC-134-2（PRD AC-SI-34-2；R62 (c)）前綴散落鎖的紅燈情形：同前綴 3 支無套件、名冊內前綴已成套件、新前綴達 3 支、名冊與天花板不一致
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成 `tools/lib/`）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_2_E_1 -q

Feature: tools/lib 前綴散落（紅燈情形）

Scenario: 散落、名冊過期、新增散落、名冊與天花板不等各判紅
  Given 判準函式 `prefix_problems(repo_root, roster, ceiling)`；合成 `tools/lib/` 與合成名冊、天花板
  When (a) 同前綴 3 支（`aa_x.py`、`aa_y.py`、`aa_z.py`）、無 `tools/lib/aa/` 套件、前綴不在名冊；(b) 名冊含前綴 `bb`，而 `tools/lib/bb/` 套件目錄已存在；(c) 名冊（含前綴 `cc`）與天花板相等，另有新前綴 `dd` 的三支檔 `dd_*.py` 不在名冊；(d) 名冊多一個項目而天花板不變；(e) 名冊少一個項目而天花板不變
  Then (a)～(e) 每個情境都回傳非空清單，訊息點名前綴與規則（(a) 為散落、(b) 為名冊內前綴已成套件須移除、(c) 為新前綴散落、(d) 與 (e) 為名冊與天花板不相等）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_2_E_1]"
```

```gherkin
# AT-134-3-1
# 對應 AC: AC-134-3（PRD AC-SI-34-3；R62 (d)）真樹每個含 `__init__.py` 的套件目錄都登記在某一列的程式碼欄
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真樹；合成樹驗合規形態）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_3_1 -q

Feature: 套件須登記（合規情形）

Scenario: 真樹的套件皆已登記；合成樹登記後為綠
  Given 判準函式 `package_problems(repo_root)`；真 repo 的 `tools/lib/` 與 SSOT
  When 對真 repo 呼叫；另對合成 repo 呼叫：`tools/lib/pkg1/__init__.py` 存在，且 SSOT 某列的程式碼欄含 `tools/lib/pkg1/`
  Then 兩者皆回傳空清單；真樹的檢查涵蓋 `selfimproving` 套件（其已登記）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_3_1]"
```

```gherkin
# AT-134-3-E-1
# 對應 AC: AC-134-3（PRD AC-SI-34-3；R62 (d)）未登記的套件即紅
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成 repo）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_3_E_1 -q

Feature: 套件須登記（負控）

Scenario: 新套件目錄未出現在任何登記列的程式碼欄即判紅
  Given 合成 repo：`tools/lib/pkg1/__init__.py` 與 `tools/lib/pkg2/__init__.py` 皆存在，SSOT 只有一列、程式碼欄只含 `tools/lib/pkg1/`；另備把 `pkg2` 寫在「測試欄」而非「程式碼欄」的變體
  When 呼叫 `package_problems`
  Then 回傳非空清單，訊息點名 `pkg2`（`pkg1` 不在內）；變體同樣點名 `pkg2`（只認程式碼欄）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_3_E_1]"
```

```gherkin
# AT-134-3-E-2
# 對應 AC: AC-134-3（PRD AC-SI-34-3；R62 (d)）套件登記以「程式碼」欄的反引號片段為準：片段之外的散文字串不算登記
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成 repo）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_3_E_2 -q -p no:xdist -o addopts=

Feature: 套件須登記（片段判準）

Scenario: 套件名只出現在程式碼欄的散文中即判紅，登記為片段才為綠
  Given 合成 repo：`tools/lib/pkg/__init__.py` 存在；SSOT 的登記表（§3 節、六欄）依情境各一份——(a) 程式碼欄只有散文 `tools/lib/pkg/ 尚待登記`（沒有反引號）；(b) 程式碼欄含片段 `tools/lib/other/`，另有散文 `（相鄰：tools/lib/pkg/ 說明）`；(c) 對照：程式碼欄含片段 `tools/lib/pkg/`
  When 對三份各呼叫 `package_problems`
  Then (a) 與 (b)：回傳非空清單，訊息點名 `pkg`
  And (c)：回傳空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_3_E_2]"
```

```gherkin
# AT-134-4-1
# 對應 AC: AC-134-4（PRD AC-SI-34-4；R62 (e)）含「模組落點表」字樣的 PRD 必含 SSOT 路徑；真 PRD 為綠；不含字樣的 PRD 不判
# 測試類型: Unit
# 自動化工具: pytest（唯讀存取真 PRD；合成 PRD 驗合規形態）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_4_1 -q

Feature: 新模組 PRD 須引落點 SSOT（合規情形）

Scenario: 含字樣且含 SSOT 路徑者綠；不含字樣者不判
  Given 判準函式 `prd_problems(repo_root)`；SSOT 路徑字串 `docs/02_architecture/Root_Layout_and_Module_Placement.md`
  When 對真 repo 呼叫；另對合成 repo 的 `docs/01_requirements/` 呼叫：(a) `X_PRD.md` 含「模組落點表」字樣與 SSOT 路徑；(b) `Y_PRD.md` 不含字樣（也不含路徑）；(c) 不以 `_PRD.md` 結尾的檔含字樣而缺路徑
  Then 真 repo 回傳空清單；(a)、(b)、(c) 皆回傳空清單（(c) 不在判定範圍）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_4_1]"
```

```gherkin
# AT-134-4-E-1
# 對應 AC: AC-134-4（PRD AC-SI-34-4；R62 (e)）含「模組落點表」字樣而缺 SSOT 路徑的 PRD 即紅
# 測試類型: Unit
# 自動化工具: pytest + tmp 目錄（合成 repo）
# 判定指令: python -m pytest tools/tests/test_root_module_layout.py -k AT_134_4_E_1 -q

Feature: 新模組 PRD 須引落點 SSOT（負控）

Scenario: 有字樣無路徑的 PRD 被判紅
  Given 合成 repo 的 `docs/01_requirements/Z_PRD.md` 含字樣「模組落點表」與一個模組落點表，但不含 SSOT 路徑字串；對照：同檔補上 SSOT 路徑
  When 對缺路徑版本與補上路徑版本各呼叫 `prd_problems`
  Then 缺路徑版本回傳非空清單、訊息點名 `Z_PRD.md`；補上路徑版本回傳空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_134_4_E_1]"
```

```gherkin
# AT-128-1-1
# 對應 AC: AC-128-1（PRD AC-SI-28-1；R66）鍵 B：真 AutoClaude 原始碼上五格皆綠，且每格的掃描器自帶對照組證明看得見生產站點
# 測試類型: Contract
# 自動化工具: pytest + AST（唯讀存取 AutoClaude 原始碼；cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_1_1 -q -n 0

Feature: 演化只提案不套用（真樹）

Scenario: 引用格、apply_evolution 呼叫點、演化重載生產者、signoff 讀取點、文件宣稱五格皆綠
  Given 真樹：`AutoClaude/autoclaude/`、`AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py`、`AutoClaude/autoclaude/main.py`、`AutoClaude/CLAUDE.md`（皆唯讀；改述與本測試同輪落地，見 D13）；測試檔常數 `APPLY_EVOLUTION_SITES`（以〔相對 `autoclaude/` 的 POSIX 路徑, 外層函式名〕登記，不寫行號）、`PRODUCER_EXCLUDED`（`core/kernel_state.py`、`core/resolution_policy.py`）、`EVOLUTION_DOC_ANCHOR`（含 `ON_ESCALATION` 的敘述行）
  When 對真樹呼叫五個格的判準函式，並呼叫各格的對照組判準
  Then ①：r85 檔仍含函式 `test_playbook_runner_has_no_production_construction_site` 與 `test_the_scanner_can_see_production_sites_at_all`
  And ②：`autoclaude/` 下名為 `apply_evolution` 的 `Call` 節點，依〔路徑, 外層函式名〕彙整的集合恰等於 `APPLY_EVOLUTION_SITES`（現況為 `execution/steps_orchestrator/_escalation_handler.py` 的三處與 `execution/mutation_applier/_complex_mutations.py` 的一處）；`execution/` 之外沒有任何模組 import 含 `steps_orchestrator` 或 `mutation_applier` 的模組路徑
  And ③：`plugins/` 與 `core/`（排除 `PRODUCER_EXCLUDED`）內沒有任何 `Call` 帶 keyword `evolved_playbook_path`，也沒有 `PersistenceResult(...)` 的 keyword `kind` 為常數 `evolved_playbook`；④：`autoclaude/` 下對屬性 `require_evolution_signoff` 的 Load 語境讀取只出現在 `execution/playbook_runner.py`
  And ⑤：`AutoClaude/autoclaude/main.py` 仍含字樣 `舊 PlaybookRunner 直連模式已於 W6 拔除`；`AutoClaude/CLAUDE.md` 中含 `ON_ESCALATION` 的敘述行至少一行含該字樣，且這些行皆不含 `main.py:<數字>` 形態
  And 對照組：② 掃描器在 `execution/` 找到不少於 4 個 `apply_evolution` 呼叫；③ 掃描器在 `execution/` 找到不少於 3 個 `evolved_playbook_path=` keyword，並在 `core/resolution_policy.py` 找到至少 1 個；④ 掃描器在 `execution/playbook_runner.py` 找到恰 1 個讀取
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_1_1]"
```

```gherkin
# AT-128-1-E-1
# 對應 AC: AC-128-1（PRD AC-SI-28-1 ①②；R66）引用格缺函式、apply_evolution 呼叫點多或少、execution/ 外的呼叫與 import 皆判紅（合成樹）
# 測試類型: Contract
# 自動化工具: pytest + AST + tmp 目錄（合成 `autoclaude/` 樹；cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_1_E_1 -q -n 0

Feature: 引用格與呼叫點的注入負控

Scenario: 注入違規的合成樹使格 ① ② 轉紅，合法合成樹為對照
  Given 夾具 `make_tree(files)` 建合成 `autoclaude/` 樹；合法對照樹：`execution/steps_orchestrator/_escalation_handler.py` 在函式 `f1` 與 `f2` 各含一個 `apply_evolution` 呼叫，合成的 `APPLY_EVOLUTION_SITES` 恰登記這兩個〔路徑, 函式〕；合成的 r85 檔文字含兩個必備函式
  When 情境一（①）：合成 r85 檔文字缺 `test_the_scanner_can_see_production_sites_at_all`；另一案缺 `test_playbook_runner_has_no_production_construction_site`
  And 情境二（②）：(a) 同檔再加函式 `f3` 內的一個呼叫；(b) 移除 `f2` 內的呼叫；(c) `plugins/x.py` 含 `apply_evolution` 呼叫；(d) `plugins/y.py` import 路徑含 `steps_orchestrator` 的模組；(e) `core/z.py` 以 `from autoclaude.execution.mutation_applier import …` 引入
  Then 對照樹：① 與 ② 皆回傳空清單
  And 情境一的兩案：① 回傳非空清單並點名缺的函式；情境二 (a)～(e)：② 皆回傳非空清單（(a) 點名多出的 `f3`、(b) 點名缺的 `f2`、(c)(d)(e) 點名違規檔）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_1_E_1]"
```

```gherkin
# AT-128-1-E-2
# 對應 AC: AC-128-1（PRD AC-SI-28-1 ③；R66）plugins 與 core 內出現演化重載生產者即判紅；排除檔豁免；掃描器在 execution 內看得見生產者
# 測試類型: Contract
# 自動化工具: pytest + AST + tmp 目錄（合成 `autoclaude/` 樹；cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_1_E_2 -q -n 0

Feature: 演化重載生產者的注入負控

Scenario: 注入生產者使格 ③ 轉紅；排除檔內的同形態不判；掃描器自證看得見
  Given 夾具 `make_tree(files)`；合法對照樹：`plugins/` 與 `core/`（排除檔之外）皆無生產者；`core/resolution_policy.py` 含一個 `Foo(evolved_playbook_path=…)` 呼叫（排除檔）；`execution/` 下合成三個含 `evolved_playbook_path=` keyword 的呼叫
  When (a) `plugins/x.py` 含 `Foo(evolved_playbook_path="p")`；(b) `core/other.py` 含 `PersistenceResult(kind="evolved_playbook")`；(c) `plugins/y.py` 含 `PersistenceResult(kind="other")`（不同常數）；(d) `core/kernel_state.py` 含 `Foo(evolved_playbook_path="p")`
  Then 對照樹：③ 回傳空清單，且掃描器在 `execution/` 找到 3 個、在排除檔 `core/resolution_policy.py` 找到 1 個
  And (a)、(b)：③ 皆回傳非空清單並點名該檔；(c)：回傳空清單（常數不是 `evolved_playbook`）；(d)：回傳空清單（排除檔）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_1_E_2]"
```

```gherkin
# AT-128-1-E-3
# 對應 AC: AC-128-1（PRD AC-SI-28-1 ④；R66）require_evolution_signoff 的讀取點多出一處即判紅；Store 語境不算讀取
# 測試類型: Contract
# 自動化工具: pytest + AST + tmp 目錄（合成 `autoclaude/` 樹；cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_1_E_3 -q -n 0

Feature: signoff 讀取點的注入負控

Scenario: 讀取點只准在 execution/playbook_runner.py
  Given 夾具 `make_tree(files)`；合法對照樹：`execution/playbook_runner.py` 含一個 `cfg.playbook.require_evolution_signoff` 的 Load 讀取；`utils/config.py` 含該欄位的宣告（`AnnAssign`）
  When (a) `execution/other.py` 多一個同樣的讀取；(b) `plugins/p.py` 含該讀取；(c) `plugins/q.py` 只有 Store 語境的賦值 `cfg.require_evolution_signoff = True`
  Then 對照樹：④ 回傳空清單，掃描器在 `execution/playbook_runner.py` 找到恰 1 個讀取
  And (a)、(b)：④ 皆回傳非空清單並點名該檔；(c)：回傳空清單（Store 語境不是讀取）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_1_E_3]"
```

```gherkin
# AT-128-1-E-4
# 對應 AC: AC-128-1（PRD AC-SI-28-1 ⑤；R66）文件宣稱釘住：缺字樣、帶 `main.py:<行號>` 形態、main.py 缺註解字樣皆判紅
# 測試類型: Contract
# 自動化工具: pytest + 合成文字（cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_1_E_4 -q -n 0

Feature: 文件宣稱的注入負控

Scenario: 引註解字樣而不引行號；缺字樣或帶行號即紅
  Given 合法對照：合成文件文字含一行含 `ON_ESCALATION` 並含字樣 `舊 PlaybookRunner 直連模式已於 W6 拔除` 而不含 `main.py:<數字>`；合成 `main.py` 文字含該字樣
  When (a) 文件文字改成含 `main.py:277` 的形態；(b) 文件文字中含 `ON_ESCALATION` 的行都不含該字樣；(c) 兩行含 `ON_ESCALATION`，其一合規、其一含 `main.py:12`；(d) 合成 `main.py` 文字缺該字樣
  Then 對照：⑤ 回傳空清單
  And (a)、(b)、(c)、(d)：⑤ 皆回傳非空清單並點名問題（(c) 點名含行號形態的那一行）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_1_E_4]"
```

```gherkin
# AT-128-2-1
# 對應 AC: AC-128-2（PRD AC-SI-28-2；R66）`require_evolution_signoff` 預設值仍為 False；文件演化敘述含四個改述片段且該行不超過 800 個碼位
# 測試類型: Contract
# 自動化工具: pytest + AST（唯讀存取 AutoClaude 原始碼與 CLAUDE.md；cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_2_1 -q -n 0

Feature: 預設值零退化與文件改述

Scenario: 預設值未變，文件已改述為只提案、預設放行、無生產建構點、無演化重載生產者
  Given 真 `AutoClaude/autoclaude/utils/config.py` 與 `AutoClaude/CLAUDE.md`（唯讀）
  When 以 AST 讀 `require_evolution_signoff` 欄位的預設值；取 `CLAUDE.md` 中含 `ON_ESCALATION` 的敘述行
  Then 預設值為 `False`
  And 該敘述行（至少一行）同時含四個片段：`Kernel 路徑只提案`、`預設放行`、`無生產建構點`、`無演化重載生產者`；每個含 `ON_ESCALATION` 的行長度（碼位數）皆不大於 800
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_2_1]"
```

```gherkin
# AT-128-2-E-1
# 對應 AC: AC-128-2（PRD AC-SI-28-2；R66）預設值被改成 True、任一改述片段被刪、行長超過 800 皆判紅
# 測試類型: Contract
# 自動化工具: pytest + 合成文字與合成 config 原始碼（cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_2_E_1 -q -n 0

Feature: 預設值與改述的注入負控

Scenario: 退化與缺片段與超長行各被判出
  Given 合法對照：合成 config 原始碼的欄位預設為 `False`；合成文件行含四個片段、含 `ON_ESCALATION` 且長度恰 800 個碼位
  When (a) 合成 config 的預設改為 `True`；(b) 四個片段各刪去一個的副本（四個）；(c) 同一行補長到 801 個碼位
  Then 對照：預設值判準與文件判準皆回傳空清單
  And (a)：預設值判準回傳非空清單；(b)：四個副本各回傳非空清單並點名被刪的片段；(c)：長度判準回傳非空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_2_E_1]"
```

```gherkin
# AT-128-2-E-2
# 對應 AC: AC-128-2（PRD AC-SI-28-2；R66）判準常數的獨立釘選：`REWRITE_FRAGMENTS` 與 R66 的四個改述片段相等，改常數的任一元素即紅
# 測試類型: Contract
# 自動化工具: pytest（常數的字面比對與突變副本自證；cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_2_E_2 -q -n 0

Feature: 改述片段常數的釘選

Scenario: 常數內容與 R66 的四個片段相等，突變副本比對不相等
  Given 測試檔常數 `REWRITE_FRAGMENTS`；期望值於測試內以字面獨立寫出（不由常數衍生），取自本檔 R66：`Kernel 路徑只提案`、`預設放行`、`無生產建構點`、`無演化重載生產者`
  When 以集合語意（順序不拘）比對常數與期望值；另對常數各產生突變副本：刪去任一元素（四個副本）、把任一元素改掉一個字（四個副本）、多加一個元素——各比對一次
  Then 常數與期望值相等（恰四個元素、無重複）
  And 九個突變副本與期望值比對皆為不相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_2_E_2]"
```

```gherkin
# AT-128-3-1
# 對應 AC: AC-128-3（PRD AC-SI-28-3；R66）①～④ 任一格轉紅時，失敗訊息指向立即升為缺陷列並走 FR-SI-12 的人工閘
# 測試類型: Contract
# 自動化工具: pytest + 合成樹（cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_3_1 -q -n 0

Feature: 轉紅訊息指向人工閘

Scenario: 四個格各以合成注入轉紅，訊息含 OBS-SI-010、升為缺陷列、FR-SI-12
  Given 合成樹與四個注入：① 缺引用函式；② 多一個 `apply_evolution` 呼叫點；③ `plugins/x.py` 含演化重載生產者；④ `execution/other.py` 多一個 `require_evolution_signoff` 讀取
  When 對每個注入呼叫對應格的斷言並擷取失敗訊息
  Then 四個斷言都失敗（`AssertionError`）
  And 四則失敗訊息各自同時含 `OBS-SI-010`、`升為缺陷列`、`FR-SI-12` 三個片段
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_3_1]"
```

```gherkin
# AT-128-3-E-1
# 對應 AC: AC-128-3（PRD AC-SI-28-3；R66）訊息判準自證：缺任一片段的訊息被判不合格；格 ⑤ 的訊息不要求含該三片段
# 測試類型: Contract
# 自動化工具: pytest + 合成訊息（cwd 為 AutoClaude/）
# 判定指令: python -m pytest tests/contract/test_evolution_propose_only.py -k AT_128_3_E_1 -q -n 0

Feature: 訊息判準非恆真

Scenario: 少一個片段的訊息不合格；格 ⑤ 只是文件宣稱，不要求人工閘字樣
  Given 訊息判準函式 `message_ok(text)`（要求同時含 `OBS-SI-010`、`升為缺陷列`、`FR-SI-12`）；一則合規訊息
  When 對三則各缺一個片段的訊息呼叫；另對格 ⑤ 以合成注入（文件含 `main.py:277`）轉紅後擷取其失敗訊息
  Then 合規訊息判為合格；三則缺片段的訊息皆判為不合格
  And 格 ⑤ 的失敗訊息只需點名問題，不要求含上述三個片段（判準只套用在 ① 至 ④）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_128_3_E_1]"
```

---

## 3. AT 完整清單

> 本節是依測試類型的閱讀索引（AT 的權威清單是 §1；P0 預審 F-15 同型：兩處清單由同一份登錄自動產生、不手工維護）。測試方法欄為測試函式名的樣式，函式名須含 AT 底線形。

### 3.1 Unit Tests

| AT ID | 對應 AC | 測試檔 | 測試方法 | 自動化工具 |
|-------|---------|--------|---------|-----------|
| AT-105-1-E-1 | AC-105-1 | tools/tests/test_selfimproving_events.py | test_AT_105_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-105-2-E-1 | AC-105-2 | tools/tests/test_selfimproving_events.py | test_AT_105_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-1-E-1 | AC-107-1 | tools/tests/test_selfimproving_props.py | test_AT_107_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-2-1 | AC-107-2 | tools/tests/test_selfimproving_events.py | test_AT_107_2_1_* | pytest（唯讀存取真 SOP） |
| AT-107-2-E-1 | AC-107-2 | tools/tests/test_selfimproving_events.py | test_AT_107_2_E_1_* | pytest（以真 SOP 全文的變異副本） |
| AT-107-3-1 | AC-107-3 | tools/tests/test_selfimproving_props.py | test_AT_107_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-3-E-1 | AC-107-3 | tools/tests/test_selfimproving_props.py | test_AT_107_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-3-E-2 | AC-107-3 | tools/tests/test_selfimproving_props.py | test_AT_107_3_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-3-E-4 | AC-107-3 | tools/tests/test_selfimproving_props.py | test_AT_107_3_E_4_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-1-E-1 | AC-108-1 | tools/tests/test_selfimproving_props.py | test_AT_108_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-4-E-2 | AC-108-4 | tools/tests/test_selfimproving_events.py | test_AT_108_4_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-4-E-3 | AC-108-4 | tools/tests/test_selfimproving_events.py | test_AT_108_4_E_3_* | pytest + tmp 目錄 + 真 git + subprocess（hermetic） |
| AT-108-4-E-4 | AC-108-4 | tools/tests/test_selfimproving_events.py | test_AT_108_4_E_4_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-4-E-5 | AC-108-4 | tools/tests/test_selfimproving_events.py | test_AT_108_4_E_5_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-109-1-2 | AC-109-1 | tools/tests/test_selfimproving_props.py | test_AT_109_1_2_* | pytest（唯讀存取真 SOP；含刪去自證） |
| AT-109-1-E-1 | AC-109-1 | tools/tests/test_selfimproving_props.py | test_AT_109_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-109-3-E-1 | AC-109-3 | tools/tests/test_selfimproving_props.py | test_AT_109_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-110-2-2 | AC-110-2 | tools/tests/test_selfimproving_props.py | test_AT_110_2_2_* | pytest（唯讀存取真 SOP；含刪去自證） |
| AT-110-2-E-1 | AC-110-2 | tools/tests/test_selfimproving_props.py | test_AT_110_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-111-2-1 | AC-111-2 | tools/tests/test_selfimproving_events.py | test_AT_111_2_1_* | pytest（唯讀存取真 SOP） |
| AT-111-2-E-1 | AC-111-2 | tools/tests/test_selfimproving_events.py | test_AT_111_2_E_1_* | pytest（以真 SOP 全文的變異副本） |
| AT-114-3-1 | AC-114-3 | tools/tests/test_selfimproving_props.py | test_AT_114_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-130-4-2 | AC-130-4 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_4_2_* | pytest（唯讀存取真 SOP；含刪去自證） |
| AT-130-6-1 | AC-130-6 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_6_1_* | pytest + tmp 目錄（hermetic） |
| AT-130-6-E-1 | AC-130-6 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_6_E_1_* | pytest + tmp 目錄（hermetic） |
| AT-131-1-E-1 | AC-131-1 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-131-2-E-2 | AC-131-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_2_E_2_* | pytest + tmp 目錄（差分對 `tools/check_defect_log_crossref.py` 的 `_classify` 與 `_load_ledger_status`） |
| AT-131-4-1 | AC-131-4 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_4_1_* | pytest（純函式） |
| AT-131-5-1 | AC-131-5 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_5_1_* | pytest（唯讀存取真 SOP 與真 PRD） |
| AT-132-5-E-1 | AC-132-5 | tools/tests/test_selfimproving_export_status.py | test_AT_132_5_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-132-5-E-3 | AC-132-5 | tools/tests/test_selfimproving_export_status.py | test_AT_132_5_E_3_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-134-1-1 | AC-134-1 | tools/tests/test_root_module_layout.py | test_AT_134_1_1_* | pytest（唯讀存取真 SSOT；合成 SSOT 驗解析規則） |
| AT-134-1-E-1 | AC-134-1 | tools/tests/test_root_module_layout.py | test_AT_134_1_E_1_* | pytest + tmp 目錄（合成 repo） |
| AT-134-2-1 | AC-134-2 | tools/tests/test_root_module_layout.py | test_AT_134_2_1_* | pytest + tmp 目錄（合成 `tools/lib/`） |
| AT-134-2-E-1 | AC-134-2 | tools/tests/test_root_module_layout.py | test_AT_134_2_E_1_* | pytest + tmp 目錄（合成 `tools/lib/`） |
| AT-134-3-1 | AC-134-3 | tools/tests/test_root_module_layout.py | test_AT_134_3_1_* | pytest（唯讀存取真樹；合成樹驗合規形態） |
| AT-134-3-E-1 | AC-134-3 | tools/tests/test_root_module_layout.py | test_AT_134_3_E_1_* | pytest + tmp 目錄（合成 repo） |
| AT-134-3-E-2 | AC-134-3 | tools/tests/test_root_module_layout.py | test_AT_134_3_E_2_* | pytest + tmp 目錄（合成 repo） |
| AT-134-4-1 | AC-134-4 | tools/tests/test_root_module_layout.py | test_AT_134_4_1_* | pytest（唯讀存取真 PRD；合成 PRD 驗合規形態） |
| AT-134-4-E-1 | AC-134-4 | tools/tests/test_root_module_layout.py | test_AT_134_4_E_1_* | pytest + tmp 目錄（合成 repo） |
| AT-140-1-E-1 | AC-140-1 | tools/tests/test_selfimproving_events.py | test_AT_140_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-140-1-E-3 | AC-140-1 | tools/tests/test_selfimproving_events.py | test_AT_140_1_E_3_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-142-1-E-2 | AC-142-1 | tools/tests/test_selfimproving_events.py | test_AT_142_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-143-1-1 | AC-143-1 | tools/tests/test_selfimproving_capability.py | test_AT_143_1_1_* | pytest（AST 與正規式靜態掃描；唯讀存取真原始碼） |
| AT-143-1-E-1 | AC-143-1 | tools/tests/test_selfimproving_capability.py | test_AT_143_1_E_1_* | pytest + tmp 目錄（合成套件樹） |
| AT-145-1-1 | AC-145-1 | tools/tests/test_selfimproving_events.py | test_AT_145_1_1_* | pytest（唯讀存取真 repo 檔案） |
| AT-145-1-E-1 | AC-145-1 | tools/tests/test_selfimproving_events.py | test_AT_145_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-145-2-1 | AC-145-2 | tools/tests/test_selfimproving_events.py | test_AT_145_2_1_* | pytest（唯讀存取真 SOP；以 `## ` 標題切段的關鍵片段判準） |
| AT-145-2-E-1 | AC-145-2 | tools/tests/test_selfimproving_events.py | test_AT_145_2_E_1_* | pytest（以真 SOP 全文的變異副本） |
| AT-145-2-E-2 | AC-145-2 | tools/tests/test_selfimproving_events.py | test_AT_145_2_E_2_* | pytest（唯讀存取夾具常數；以常數的突變副本自證） |

### 3.2 Integration Tests

| AT ID | 對應 AC | 測試檔 | 測試方法 | 自動化工具 |
|-------|---------|--------|---------|-----------|
| AT-102-1-1 | AC-102-1 | tools/tests/test_selfimproving_props.py | test_AT_102_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-102-1-E-1 | AC-102-1 | tools/tests/test_selfimproving_props.py | test_AT_102_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-103-1-1 | AC-103-1 | tools/tests/test_selfimproving_export_status.py | test_AT_103_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-103-1-E-1 | AC-103-1 | tools/tests/test_selfimproving_export_status.py | test_AT_103_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-103-1-E-2 | AC-103-1 | tools/tests/test_selfimproving_export_status.py | test_AT_103_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-103-1-E-3 | AC-103-1 | tools/tests/test_selfimproving_export_status.py | test_AT_103_1_E_3_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-103-2-1 | AC-103-2 | tools/tests/test_selfimproving_events.py | test_AT_103_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-103-2-E-1 | AC-103-2 | tools/tests/test_selfimproving_events.py | test_AT_103_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-105-1-1 | AC-105-1 | tools/tests/test_selfimproving_events.py | test_AT_105_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-105-2-1 | AC-105-2 | tools/tests/test_selfimproving_events.py | test_AT_105_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-106-1-1 | AC-106-1 | tools/tests/test_selfimproving_events.py | test_AT_106_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-106-1-E-1 | AC-106-1 | tools/tests/test_selfimproving_events.py | test_AT_106_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-106-2-1 | AC-106-2 | tools/tests/test_selfimproving_events.py | test_AT_106_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-106-2-E-1 | AC-106-2 | tools/tests/test_selfimproving_events.py | test_AT_106_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-106-2-E-2 | AC-106-2 | tools/tests/test_selfimproving_events.py | test_AT_106_2_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-1-1 | AC-107-1 | tools/tests/test_selfimproving_props.py | test_AT_107_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-107-3-E-3 | AC-107-3 | tools/tests/test_selfimproving_props.py | test_AT_107_3_E_3_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-1-1 | AC-108-1 | tools/tests/test_selfimproving_props.py | test_AT_108_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-2-1 | AC-108-2 | tools/tests/test_selfimproving_props.py | test_AT_108_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-2-E-1 | AC-108-2 | tools/tests/test_selfimproving_props.py | test_AT_108_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-3-1 | AC-108-3 | tools/tests/test_selfimproving_props.py | test_AT_108_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-3-E-1 | AC-108-3 | tools/tests/test_selfimproving_props.py | test_AT_108_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-4-1 | AC-108-4 | tools/tests/test_selfimproving_events.py | test_AT_108_4_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-108-4-E-1 | AC-108-4 | tools/tests/test_selfimproving_events.py | test_AT_108_4_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-109-1-1 | AC-109-1 | tools/tests/test_selfimproving_props.py | test_AT_109_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-109-2-1 | AC-109-2 | tools/tests/test_selfimproving_props.py | test_AT_109_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-109-2-E-1 | AC-109-2 | tools/tests/test_selfimproving_props.py | test_AT_109_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-109-3-1 | AC-109-3 | tools/tests/test_selfimproving_props.py | test_AT_109_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-110-1-1 | AC-110-1 | tools/tests/test_selfimproving_props.py | test_AT_110_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-110-1-E-1 | AC-110-1 | tools/tests/test_selfimproving_props.py | test_AT_110_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-110-2-1 | AC-110-2 | tools/tests/test_selfimproving_props.py | test_AT_110_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-110-3-1 | AC-110-3 | tools/tests/test_selfimproving_events.py | test_AT_110_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-110-3-E-1 | AC-110-3 | tools/tests/test_selfimproving_events.py | test_AT_110_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-111-1-1 | AC-111-1 | tools/tests/test_selfimproving_props.py | test_AT_111_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-111-1-E-1 | AC-111-1 | tools/tests/test_selfimproving_props.py | test_AT_111_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-114-1-1 | AC-114-1 | tools/tests/test_selfimproving_props.py | test_AT_114_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-114-1-2 | AC-114-1 | tools/tests/test_selfimproving_props.py | test_AT_114_1_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-114-1-E-1 | AC-114-1 | tools/tests/test_selfimproving_props.py | test_AT_114_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-114-2-1 | AC-114-2 | tools/tests/test_selfimproving_props.py | test_AT_114_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-114-2-E-1 | AC-114-2 | tools/tests/test_selfimproving_props.py | test_AT_114_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-114-3-E-1 | AC-114-3 | tools/tests/test_selfimproving_props.py | test_AT_114_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-130-1-1 | AC-130-1 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-130-1-E-1 | AC-130-1 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-130-2-1 | AC-130-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_2_1_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-2-E-1 | AC-130-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_2_E_1_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-2-E-2 | AC-130-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_2_E_2_* | pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間） |
| AT-130-2-E-3 | AC-130-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_2_E_3_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-2-E-4 | AC-130-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_2_E_4_* | pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間） |
| AT-130-3-1 | AC-130-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_3_1_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-3-E-1 | AC-130-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_3_E_1_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-3-E-2 | AC-130-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_3_E_2_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-3-E-3 | AC-130-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_3_E_3_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 + threading |
| AT-130-3-E-4 | AC-130-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_3_E_4_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-3-E-5 | AC-130-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_3_E_5_* | pytest + tmp 目錄 + 本機 loopback HTTP 夾具 |
| AT-130-4-1 | AC-130-4 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_4_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-130-4-E-1 | AC-130-4 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_4_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-130-5-1 | AC-130-5 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_5_1_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-5-E-1 | AC-130-5 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_5_E_1_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-130-5-E-2 | AC-130-5 | tools/tests/test_selfimproving_research_scan.py | test_AT_130_5_E_2_* | pytest + tmp 目錄 + 真 git + 本機 loopback HTTP 夾具 |
| AT-131-1-1 | AC-131-1 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-131-2-1 | AC-131-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_2_1_* | pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間） |
| AT-131-2-E-1 | AC-131-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_2_E_1_* | pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間） |
| AT-131-2-E-3 | AC-131-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_2_E_3_* | pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間） |
| AT-131-3-1 | AC-131-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-131-3-E-1 | AC-131-3 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-131-4-E-1 | AC-131-4 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_4_E_1_* | pytest + tmp 目錄 + 真 git（以環境變數固定各 commit 的提交時間） |
| AT-131-5-E-1 | AC-131-5 | tools/tests/test_selfimproving_research_scan.py | test_AT_131_5_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-132-5-E-2 | AC-132-5 | tools/tests/test_selfimproving_export_status.py | test_AT_132_5_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-140-1-1 | AC-140-1 | tools/tests/test_selfimproving_events.py | test_AT_140_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-140-1-E-2 | AC-140-1 | tools/tests/test_selfimproving_events.py | test_AT_140_1_E_2_* | pytest + tmp 目錄 + 真 git + subprocess（hermetic） |
| AT-140-2-E-1 | AC-140-2 | tools/tests/test_selfimproving_export_status.py | test_AT_140_2_E_1_* | pytest + tmp 目錄 + 真 git + subprocess（hermetic） |
| AT-140-2-E-2 | AC-140-2 | tools/tests/test_selfimproving_export_status.py | test_AT_140_2_E_2_* | pytest + tmp 目錄 + 真 git + subprocess（hermetic） |
| AT-141-1-E-1 | AC-141-1 | tools/tests/test_selfimproving_events.py | test_AT_141_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-141-1-E-2 | AC-141-1 | tools/tests/test_selfimproving_events.py | test_AT_141_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-141-2-1 | AC-141-2 | tools/tests/test_selfimproving_events.py | test_AT_141_2_1_* | pytest + tmp 目錄 + 真 git + threading 與 subprocess |
| AT-141-2-E-1 | AC-141-2 | tools/tests/test_selfimproving_events.py | test_AT_141_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-141-2-E-2 | AC-141-2 | tools/tests/test_selfimproving_events.py | test_AT_141_2_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-141-2-E-3 | AC-141-2 | tools/tests/test_selfimproving_events.py | test_AT_141_2_E_3_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-142-1-1 | AC-142-1 | tools/tests/test_selfimproving_events.py | test_AT_142_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-142-1-E-1 | AC-142-1 | tools/tests/test_selfimproving_events.py | test_AT_142_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-142-2-1 | AC-142-2 | tools/tests/test_selfimproving_events.py | test_AT_142_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-142-2-E-1 | AC-142-2 | tools/tests/test_selfimproving_events.py | test_AT_142_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-143-1-E-2 | AC-143-1 | tools/tests/test_selfimproving_capability.py | test_AT_143_1_E_2_* | pytest + tmp 目錄 + 真 git + 子行程（hermetic） |
| AT-144-1-1 | AC-144-1 | tools/tests/test_selfimproving_props.py | test_AT_144_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-144-1-E-1 | AC-144-1 | tools/tests/test_selfimproving_props.py | test_AT_144_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |

### 3.3 Contract Tests

| AT ID | 對應 AC | 測試檔 | 測試方法 | 自動化工具 |
|-------|---------|--------|---------|-----------|
| AT-128-1-1 | AC-128-1 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_1_1_* | pytest + AST（唯讀存取 AutoClaude 原始碼；cwd 為 AutoClaude/） |
| AT-128-1-E-1 | AC-128-1 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_1_E_1_* | pytest + AST + tmp 目錄（合成 `autoclaude/` 樹；cwd 為 AutoClaude/） |
| AT-128-1-E-2 | AC-128-1 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_1_E_2_* | pytest + AST + tmp 目錄（合成 `autoclaude/` 樹；cwd 為 AutoClaude/） |
| AT-128-1-E-3 | AC-128-1 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_1_E_3_* | pytest + AST + tmp 目錄（合成 `autoclaude/` 樹；cwd 為 AutoClaude/） |
| AT-128-1-E-4 | AC-128-1 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_1_E_4_* | pytest + 合成文字（cwd 為 AutoClaude/） |
| AT-128-2-1 | AC-128-2 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_2_1_* | pytest + AST（唯讀存取 AutoClaude 原始碼與 CLAUDE.md；cwd 為 AutoClaude/） |
| AT-128-2-E-1 | AC-128-2 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_2_E_1_* | pytest + 合成文字與合成 config 原始碼（cwd 為 AutoClaude/） |
| AT-128-2-E-2 | AC-128-2 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_2_E_2_* | pytest（常數的字面比對與突變副本自證；cwd 為 AutoClaude/） |
| AT-128-3-1 | AC-128-3 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_3_1_* | pytest + 合成樹（cwd 為 AutoClaude/） |
| AT-128-3-E-1 | AC-128-3 | AutoClaude/tests/contract/test_evolution_propose_only.py | test_AT_128_3_E_1_* | pytest + 合成訊息（cwd 為 AutoClaude/） |
| AT-132-5-1 | AC-132-5 | tools/tests/test_selfimproving_export_status.py | test_AT_132_5_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-140-2-1 | AC-140-2 | tools/tests/test_selfimproving_export_status.py | test_AT_140_2_1_* | pytest + tmp 目錄 + 真 git + subprocess（hermetic） |
| AT-141-1-1 | AC-141-1 | tools/tests/test_selfimproving_events.py | test_AT_141_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |

### 3.4 E2E Tests

（無；P1 出口 (a) 真實觀察端到端與 (f) 真實體檢屬實跑檢核 V8，不入 AT，因為 AT 不碰真帳本與外網。）

---

## 4. 邊界與錯誤測試規格

邊界與錯誤情境以 `AT-<NNN>-<Y>-E-<n>` 命名並已列入 §1；下表是依場景類型的索引（第一欄為場景類型、不是 AC ID）。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|----------|
| 用法錯誤（格式類） | AT-110-3-E-1、AT-105-1-E-1、AT-106-2-E-1、AT-130-1-E-1、AT-131-1-E-1、AT-132-5-E-1、AT-140-1-E-1、AT-141-1-E-1 | 旗標缺漏、枚舉值不在集合、UUID 與行號形態不合、未知旗標與未知動詞、P2 與 P3 動詞 | 見各 AT | rc 3、stdout 空、stderr 以 `selfimproving:` 起頭 |
| 狀態類拒收 | AT-103-2-E-1、AT-106-1-E-1、AT-108-2-E-1、AT-110-1-E-1、AT-130-2-E-1 | 運轉未開、確認者等於提出者、跳級、預算與研究事件、預檢失敗 | 手寫事件帳本或 CLI 序列 | rc 1、`reject <verb> <碼>`、OBS 草稿列、零殘留 |
| 邊界值（事件行位元組） | AT-141-1-E-1 | `event_max_bytes` 恰等於一行的位元組數 L 與 L－1 | 自我校準 | L 放行、L－1 `EVENT-BYTES-OVER` |
| 邊界值（觸及比例與新增條目） | AT-109-2-1、AT-109-2-E-1 | 比例恰 0.2 與 0.22；條目恰 3 與 4；歸檔搬移恰 50 與 51 行 | 取代行數、新增行數、搬移行數 | 恰等於放行、超過拒收 |
| 邊界值（卡面） | AT-114-3-1、AT-114-3-E-1 | 額外路徑 7 與 8 筆（核心區 12 行）；第 2 行顯示寬度 100 與 101；CJK 字數少而寬度超界 | `symptom` 長度與 patch 檔數 | 7 筆與寬 100 放行；8 筆與寬 101、102、110 拒收 |
| 邊界值（運轉預算） | AT-110-1-1 | 同運轉第 3 與第 4 個新 PROP；他運轉不受影響 | 連續 `prop-new` | 第 4 個 `BUDGET-PROPOSALS` |
| 邊界值（修訂上限） | AT-108-2-E-1 | `rev` 已為 3、`max_revisions` 為 2 | `prop-revise` | `REV-LIMIT`，狀態維持 returned |
| 邊界值（反空轉下限） | AT-108-4-E-2 | `min_events` 為 3，事件數 2 與 3；空檔 | 手寫事件帳本 | 2 筆與空檔 NE（blocking）、3 筆 PASS |
| 邊界值（匯出上限） | AT-132-5-E-1 | `--limit` 為 0 與 501（`export_limit_max` 為 500）；分頁銜接 | `export` 旗標 | rc 3；分頁無重複無遺漏 |
| 邊界值（抓取三界） | AT-130-5-1、AT-130-5-E-1、AT-130-3-E-1 | 現役恰等於上限與多 1；位元組恰等於上限（500、1000）與多 1；逾時 | `params.json` 的三個研究鍵 | 恰等於放行；多 1 `FETCH-MAX`、`too-large`、`timeout` |
| 邊界值（重導向跳數） | AT-130-2-E-3 | 5 次重導向放行、第 6 次 `redirect-refused` | loopback 路由鏈 | 見 AT |
| 邊界值（字元長度） | AT-130-1-E-1、AT-106-2-E-1、AT-110-3-E-1 | `--note` 為 120 字元內與 121 字元；`--by` 為含空白與 33 字元 | 旗標值 | rc 3 |
| 時間（naive 時間戳） | AT-108-4-E-2、AT-141-1-1 | 事件 `t` 不帶 offset；CLI 寫出的 `t` 一律帶 offset | 手寫事件、CLI 輸出 | `EVENT-TYPE`；寫入側零 naive |
| 併發衝突 | AT-141-2-1、AT-141-2-E-1、AT-130-3-E-3 | 無鎖對照撞號、有鎖後者得加一、8 行程×10 筆、陳舊鎖、新鮮鎖逾時、抓取在鎖外 | 執行緒與子行程 | 見 AT |
| 非 git 目錄 | AT-110-3-E-1、AT-108-4-E-1、AT-142-2-E-1、AT-130-2-E-1、AT-130-2-E-2、AT-131-3-E-1、AT-106-2-E-2 | 複製成不含 `.git` 的目錄 | 檔案複製 | `GIT-UNAVAILABLE`、blocking NE、nonblocking NE 或略過並印 NE 提示，依各動詞規則 |
| 行尾與 BOM | AT-108-4-E-1、AT-108-4-E-2、AT-142-1-E-1、AT-142-2-1、AT-130-2-E-1 | 整檔 CRLF、開頭 BOM | 位元組 | 事件帳本容忍；`.patch` 位元組原樣、`.md` 與來源表先換 LF；來源表帶 BOM 即 `SRC-FILE-FORMAT` |
| 非 UTF-8 輸入 | AT-109-1-E-1 | 本文檔含非 UTF-8 位元組 | 位元組 | rc 3 |
| 路徑別名形態 | AT-107-3-E-2、AT-107-3-E-1 | 逃逸、絕對、磁碟機代號、資料流、尾端點與空白、保留裝置名、控制字元、反斜線；大小寫變體 | 合成 patch | 整張轉交；git 看見而解析器漏掉者拒收 |
| 中文顯示寬度 | AT-114-3-1、AT-114-3-E-1 | 全形字算 2 | CJK 字串 | 以寬度而非字元數判定 |
| 網路失敗 | AT-130-3-E-1、AT-130-3-E-2、AT-130-2-E-3 | 逾時、非 2xx、超界、非文字、缺 Content-Type、壓縮編碼、連線被拒、重導向被拒 | loopback 夾具 | 固定原因字串；失敗來源不入事件 |
| 環境污染 | AT-131-1-1 | `GIT_DIR`、`GIT_INDEX_FILE` 指向他處 | 環境變數 | 輸出不變 |
| 家目錄不可寫 | AT-141-2-E-1 | `AUTOSDD_SI_DIR` 建不出 `locks/` | 其上層為普通檔案 | 寫入動詞 rc 3 `HOME-UNWRITABLE`、不退回暫存目錄；唯讀動詞照常 |
| 載體缺席 | AT-142-1-1、AT-132-5-E-1、AT-103-1-E-1、AT-131-3-E-1 | 無事件帳本、無來源表 | 檔案不存在 | nonblocking NE 或 `ne` 標示或空狀態；不是零筆通過 |
| 量不到不等於零 | AT-131-3-E-1、AT-103-1-E-1、AT-132-5-E-1、AT-130-3-E-1 | 起算點、來源檔、git、逐字稿、失敗來源 | 見 AT | 印量不到與原因；整體改印含 K 的無事件；失敗來源不以舊 digest 代填 |
| 零事件 | AT-131-3-1、AT-103-1-E-1、AT-103-2-1 | 沒有候選、沒有事件、零提案的運轉 | 見 AT | 印無事件、不印通過；`run-close` 記 `no_event` |
| 純度 | AT-143-1-1、AT-143-1-E-1、AT-143-1-E-2、AT-131-1-1 | 能力登記、閉包、載入面、零網路、常駐禁字樣 | 靜態與動態 | 見 AT |
| 差分（既有解析器） | AT-131-2-E-2 | `defs` 的狀態分類與表格解析對 `check_defect_log_crossref` 的 `_classify`、`_load_ledger_status` | `STATUS-CORPUS` 與五份合成缺陷帳本 | 兩邊輸出逐筆相同 |
| 型別怪異的事件 | AT-108-4-E-3、AT-140-1-E-2 | 欄位值為陣列的手寫事件：`reason`、`type`、`obs` 的元素、`att` | 手寫事件帳本（`SC-WEIRD`） | `check` rc 1 且恰報 `EVENT-TYPE`；各動詞不拋例外、怪異事件不被折疊 |
| 值域邊界（check 層） | AT-108-4-E-4 | `note` 120 與 121；`http_status` 199、200、299、300；`research.skip` 的 `by`；`sid` 正規形；事件行位元組 L 與 L－1 | 手寫事件帳本與 `event_max_bytes` | 邊界內放行；越界 `EVENT-TYPE`、`EVENT-BYTES-OVER` |
| 時間邊界（等號） | AT-130-2-E-4、AT-131-2-E-3 | 來源表提交時間等於事件 `t`；commit 時間等於 `scan` 起算時刻 | 以環境變數固定 commit 的提交時間 | 提交時間不晚於事件 `t` 放行、早一秒 `SOURCES-SHA-MISMATCH`；等於起算時刻的 commit 不計入窗 |
| 筆數與窗的邊界 | AT-132-5-E-3、AT-103-1-E-2 | `export` 筆數恰等於 `--limit`；兩個窗一好一壞 | `export --limit`、`mea.close` 的 `result` | 恰整頁不截斷、多一筆才截斷；一壞不暫停、連續兩壞才暫停 |
| 慢滴與停滯回應 | AT-130-5-E-2 | 每 0.5 秒送 1 位元組；送完標頭後不送本文 | loopback 夾具的 `drip`、`stall` | 在 `research_timeout_seconds` 上限（2 秒加減 0.5 秒）內以 `timeout` 返回 |
| 外部工具失敗的 fail-closed | AT-107-3-E-4、AT-130-3-E-4 | `git apply --numstat` 失敗；全部來源失敗與零現役 | 損毀的 patch、404 與 500 路由 | `PATCH-PARSE`；`ZERO-SUCCESS`（rc 1、不寫事件） |
| 輸出編碼 | AT-140-2-E-2 | 含中文的 `--json` 輸出 | `PYTHONIOENCODING=cp950` 的子行程 | UTF-8 原字、沒有 u 跳脫序列 |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| `attr-confirm`／`attr-reject` 落定時於同一把鎖內重折疊採納窗並追加 `mea.amend`（PRD §9.3 `attr` 列） | 採納窗與量測事件屬 P3（AC-SI-23-1）；P1 的 `attr*` 只寫 `attr.confirm`／`attr.reject` | P3 開工，或事件帳本出現 `mea.*` 而 `attr` 落定未連動窗結果 |
| `decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`capacity` 與 `card --issue` | 屬 P2、P3；P1 以 rc 3 釘住「未實作」（AT-140-1-E-1） | 掌舵者要求 P1 就能在 CLI 內核准提案 |
| `dec` 事件的引言回查（AC-SI-08-4 ⑤）與 `helmsman` 免掃座標回查 | 屬 P2（與 AC-SI-12-4 共用驗證函式）；P1 印 warn 層級 finding `QUOTE-VERIFIER-NOT-ESTABLISHED`（項目狀態不變） | 出現偽造的 `dec` 或 `helmsman` 座標被發現與逐字稿不符 |
| `status` 的 (e) 容量事件偵測、`retired` 狀態的折疊（R34） | 屬 P3；P1 印 NOT-EVALUABLE 或不產生 | P3 開工 |
| `REV-LIMIT` 的「rejected 加冷卻」後果（PRD AC-SI-08-2 的修訂上限說明） | 需要人決定事件 `dec`（P2）；P1 只拒收、PROP 維持 returned（§7.1 ⚖ 10） | 掌舵者要求修訂超限自動轉 rejected |
| 冷卻的 (b)「新證據解除」 | 屬 P2 的 FR-SI-13；P1 只折疊 (a) `unblock` | P2 開工 |
| `scan` 的 (iv) `build/reports/` 與 (v) 探針輸出只計數、不產生候選 | PRD 只要求逐來源印讀到筆數；候選來源為缺陷帳本與 commit | 掌舵者要求由測試報告產生候選 |
| `status` 的 `friction_reconcile` measured 分支（解析逐字稿中的流程摩擦項數） | 逐字稿格式依賴 harness、AT 不碰真逐字稿；AT 只驗 NOT-EVALUABLE 分支（兩種原因） | 掌舵者回報對帳數字與真實不符 |
| https 降 http 的實連線重導向測試 | loopback 夾具只有 http；以純函式 `fetch.check_redirect` 覆蓋（AT-130-2-E-3） | 上線後出現降級重導向被放行 |
| 研究來源 URL 的可達性與內容真偽、`sha256` 的語意改版偵測 | 字串形態判準不證明可達；`sha256` 量原始位元組穩定性（PRD AC-SI-30-2、30-3 誠實劃界） | 首跑發現來源失效或高噪音，經 T1 改表 |
| `getattr`、`importlib` 等動態建構（鍵 B 與能力登記的 AST 判準） | AST 是形態判準，看不到動態形態（PRD 誠實劃界） | 發現以動態形態繞過登記或演化只提案鎖 |
| SOP 條文的語意判定 | 機械只判關鍵片段是否存在；語意由實跑檢核 V7 對照 PRD | 條文被改成含關鍵字而語意相反 |
| 在 CI 或 hook 接 `check`、`scan`、`status` | P1 隨需執行，不新增 hook、排程或 CI 步驟（PRD AC-SI-03-1；PRD §9.7 #47 不新增守衛碼） | 事件帳本在無人 `check` 時被改壞並進入主幹 |
| 跨機器 macOS 實跑與跨機器回查 | 未驗（NFR-SI-06-5）；報告標「未驗」 | macOS 上路徑別名、保留裝置名或鎖語意與 Windows 不同 |
| P1b 的 Console 三層（Bridge、backend、frontend） | 另一份 TCS（AgentConsole 子專案流程） | P1b 開工 |

**需同步的既有測試**：`tools/tests/test_selfimproving_check.py` 的 R67 五處站點（`test_AT_001_1_1_baseline_is_green`、`test_AT_003_1_1_no_resident_mechanism`、`test_AT_030_1_E_1_usage_errors`、`params_dict()`、`test_AT_030_2_1_purity`），其餘一字不動；根層護欄的重釘由主控收尾（NFR-P1-8、NFR-P1-9）。

---

## 5. 測試資料規格

共用夾具住 `tools/tests/_selfimproving_fixtures.py`（底線開頭、不被收集；§5.6）。夾具模組**自行定義**與 P0 測試檔等價的純函式（`base_rows()`、`render_ledger()`、`common_files()`、`dump_params()` 的邏輯，不 import 依賴 `setUpModule` 全域的 P0 函式），並提供各 P1 測試檔 `setUpModule` 呼叫的建置與清理函式（tmp 根目錄與 `GIT_CONFIG_GLOBAL` 空檔，§5.5）。合成編號一律於執行期以字串相加組出（先例 P0 的 `def_id()`、`obs_id()`）；本檔與測試原始碼不寫不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>` 編號（NFR-P1-7）。

### 5.1 基線 repo（`make_p1_repo`）與 `params.json`

`make_p1_repo(dest, *, events=None, sources=None, extra_obs=(), defs=(), prm=None, rows=10, commit=True) -> Path`：回傳 tmp 內一個 git repo。**C1、C2**＝P0 §5.1 的基線（OBS 列 001～010，列 002 於 C2 由 `open` 轉 `fixed@<C1 前 12 位>`，列 008 引用執行期組出的 `PROP-SI-123`，缺陷帳本家族與 OBS 封存檔如 P0）；**C3**＝下表的 P1 新增與覆寫（一個 commit）。`commit` 為假時 C3 的內容留在工作樹（供「新列」類情境）。所有 commit 的作者與提交時間以環境變數固定（`GIT_AUTHOR_DATE`、`GIT_COMMITTER_DATE` 為同一個固定的 Unix 時間戳字串，故相同輸入建出的 repo 其 HEAD 相同）；需要特定提交時間的情境以 `commit_all(R, msg, when=<帶 offset 的 ISO 字串>)` 覆寫。

| 路徑（相對 `R`） | 內容 |
|------------------|------|
| `docs/06_quality/SelfImproving_Protocol/params.json` | 28 鍵（下表），鍵依位元組序、LF、結尾換行；`prm` 參數覆寫個別鍵 |
| `docs/01_requirements/SelfImproving_PRD.md`、`CLAUDE.md` | §5.3 的 P1 迷你版（取代 P0 迷你版） |
| `docs/06_quality/AutoSDD_Defect_Log.md` | 七欄表頭 `\| ID \| 發現日期 \| 發現情境 \| 現象與證據（file:line） \| 嚴重度 \| 分流去向 \| 狀態 \|` 與分隔列；列 `D1`＝`def_id(1)`（發現日期為今日減 30 日、情境 `夾具`、證據 `tools/lib/si_demo.py:12`、`P2`、分流去向 `-`、狀態 `fixed@abc1234`）加 `defs` 參數給的列（每個元素為〔DEF 號, 發現日期, 嚴重度, 狀態, 證據〕）；另三個家族檔如 P0 §5.1 |
| `AISDLC_SDD/scripts/sdd_version.py` | 位元組複製自真 repo 同名檔（唯讀來源；`resolve_latest_name_fast` 以 `importlib` 載入它） |
| `AISDLC_SDD/<VOLD>/README.md`、`AISDLC_SDD/<VNEW>/README.md` | 各一行文字；`<VOLD>`、`<VNEW>` 為執行期組出的兩個版本目錄名（`AISDLC_SDD_v` 接兩組數值遞增的 `主.次`，本檔其餘處以 `<VOLD>`、`<VNEW>` 稱之），且皆為已追蹤檔，故 LATEST 解析為 `<VNEW>` |
| `AISDLC_SDD/<VNEW>/governance/rules/R-9.1.yaml`、`R-9.2.yaml`、`R-9.3.yaml` | 各兩行：`id: …` 與（`R-9.1`）`maturity: active`、（`R-9.2`）`maturity: proposed`、（`R-9.3`）無 `maturity` 鍵 |
| `playbooks/demo.yaml` | 40 行，第 N 行為 `step_NN: value NN`（N 兩位零補齊） |
| `docs/notes/demo.md` | 100 行，第 N 行為 `line NNN` |
| `docs/notes/other.md`、`docs/notes/f1.md`～`f9.md` | 各 50 行，第 N 行為 `line NN` |
| `docs/notes/tiny.md` | 3 行 |
| `build/reports/pytest.log`、`docs/06_quality/misstep_attribution_demo.jsonl` | 各一行（使 `scan` 的 `build_reports` 與 `probe_outputs` 讀得到） |
| `.gitignore` | 一行 `ignored/` |
| 協定目錄的 `research_sources.json` | 僅在 `sources` 參數給了時寫入並提交（§5.4 `write_table`） |
| 事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl` | 僅在 `events` 參數給了時寫入（§5.2） |

`params.json` 的 28 鍵與夾具值（AT 的邊界值依賴這些值；它們與真檔初值巧合相同，真檔由掌舵者調參時不影響 AT）：

| 鍵 | 值 | 鍵 | 值 |
|----|----|----|----|
| `row_max_bytes` | 700 | `max_proposals_per_run` | 3 |
| `w_n`、`w_min`、`w_evt`、`w_opp` | 20、5、2、5 | `max_revisions` | 2 |
| `churn_max`、`min_heldout` | 2、5 | `max_touch_ratio` | 0.2 |
| `max_new_entries` | 3 | `stop_after_bad` | 2 |
| `cap_frac` | 0.9 | `max_archive_entries_per_card` | 50 |
| `card_line_max` | 100 | `event_max_bytes` | 2000 |
| `metrics_rev` | 1 | `min_obs_rows` | 10 |
| `ledger_warn_bytes`、`ledger_fail_bytes` | 245760、262144 | `migration_base_sha` | null |
| `spec_body_globs` | `**/docs/01_requirements/**`、`**/docs/02_architecture/**`、`**/docs/03_testing/**` | `non_evolvable_globs` | §5.3 的 18 項 |
| `research_fetch_max` | 8 | `research_bytes_max` | 262144 |
| `research_timeout_seconds` | 20 | `min_events` | 1 |
| `export_limit_max` | 500 | | |

### 5.2 事件帳本夾具（建構器與情境表）

- **建構器**：`ev(kind, by="main", **fields)` 回傳一個事件 dict（不含 `seq`、`t`，由 `write_events` 補在最前）；`write_events(R, events, *, commit=False, seqs=None)` 把事件依序寫成 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`（緊湊 JSON、UTF-8 無 BOM、LF；`seq` 預設自 1 連號，情境明列者例外）。`t` 預設為 `T0` 加 `seq` 分鐘（`T0`＝執行期的現在減 2 日，帶本機 offset，`isoformat(timespec="seconds")`）；情境另指定 `Ta`（錨點）者依該情境。`H(n)`＝`sha256:` 接 `format(n, "064x")`（確定性的假雜湊）。
- **預設欄位**：`prop` 為 `rev` 1、`base` 為 `R` 的 HEAD、`action` `modify`、`route` `loop`、`touched_count` 1、`touched_sha256` `H(1)`、`patch_sha256` `H(2)`、`body_sha256` `H(3)`、`digest` `H(4)`、`proposer` `SA`、`reviewer` 為 null；`run.open` 為 `trigger` `a`、`coords` `["tools/a.py:1"]`、`head_sha` 為 `R` 的 HEAD；`research.skip` 為 `reason` `offline`、`note` `夾具`、`by` `main`；P2 起的 kind 的欄位名為 `prop`、`dkind`、`verdict`、`flags`、`result`、`window`、`from`、`to`、`cause`、`run`（R31 與 §7.1 ⚖ 15）。
- **缺陷帳本列（`Q1`～`Q6`；`D(k)`＝錨點 `Ta` 的 UTC 日期加 k 日；DEF 號為 `def_id(11)`～`def_id(16)`）**：`Q1`＝`D(0)`、`P2`、`open`；`Q2`＝`D(0)`、`P1`、`open（workaround-applied）`；`Q3`＝`D(0)`、`P3`、`open`；`Q4`＝`D(0)`、`P2`、`fixed@abc1234`；`Q5`＝`D(-1)`、`P2`、`open`；`Q6`＝`D(1)`、`P2`、`open`；證據欄各為 `tools/a<k>.py:1`。

**情境表**（`PROP` 欄只寫 PROP 號末三位；事件鏈中的 `dec <dkind>` 指 `kind` 為 `dec`、`dkind` 為該值；`by` 依角色取任意合規標籤；除另有註明，運轉為 `RUN-SI-001` 且 `run.open` 與 `research.skip`〔`offline`〕在最前）：

- **`SC-CLOSE`**（`AT-103-2-1`）：`run.open` 為 `RUN-SI-001`、`RUN-SI-002`（兩個皆 open）；`research.skip` 屬 `RUN-SI-002`；`RUN-SI-002` 內：`PROP-124`（P、loop）`prop` 後 `dec approve`；`PROP-125`（D、loop）`prop` 後 `dec reject`。`RUN-SI-001` 沒有任何 `prop`。
- **`SC-SEQ`**（`AT-141-1-E-1`）：`seq` 為 5、6、9、10：第 5 筆 `run.open` 為 `RUN-SI-007`；第 6 筆 `research.skip` 屬 `RUN-SI-007`；第 9 筆 `attr`（root）為 `ATT-SI-012`（`obs` 為 `["OBS-SI-001"]`、`root_cause` 為 `docs/stale-note`）；第 10 筆 `prop` 為 `PROP-SI-130`（D、`target` 為 `docs/notes/demo.md`、`sources` 為 `["OBS-SI-002"]`、屬 `RUN-SI-007`）。
- **`SC-LEGAL`**（`AT-108-4-1`；運轉 `RUN-SI-001` 全程 open；事件鏈依序）：

| PROP | route | 事件鏈 | 終態 |
|------|-------|--------|------|
| 124 | loop | `prop`(rev 1)、`dec approve`、`app.sandbox`、`app.verify`(PASS)、`dec promote`、`app.promote`、`mea.open`、`mea.close`(clean) | closed |
| 125 | loop | `prop`(1)、`dec return`、`prop`(2)、`dec reject`、`dec unblock` | rejected |
| 126 | handoff:R | `prop`(1)、`dec ack-handoff` | handed-off |
| 127 | loop | `prop`(1)、`dec approve`、`app.sandbox`、`app.verify`(NE)、`dec promote`（`flags` 含 `unverified_ack`）、`app.promote` | promoted |
| 128 | loop | `prop`(1)、`dec approve`、`app.sandbox`、`app.verify`(FAIL)、`dec return`、`prop`(2) | proposed（rev 2） |
| 129 | loop | `prop`(1) | proposed |
| 130 | loop | `prop`(1)、`dec approve` | approved |
| 131 | loop | `prop`(1)、`dec approve`、`app.sandbox`、`app.verify`(PASS) | verified（PASS） |
| 132 | loop | 同 131 但 `app.verify`(FAIL) | verified（FAIL） |
| 133 | loop | 同 131 但 `app.verify`(NE) | verified（NE） |
| 134 | handoff:T1 | `prop`(1) | proposed |
| 135 | loop | `prop`(1)、`dec return` | returned |
| 136 | loop | `prop`(1)、`dec approve`、`app.sandbox`、`app.verify`(PASS)、`dec decline-promote` | rejected |
| 137 | loop | `prop`(1)、`dec approve`、`app.sandbox`、`app.verify`(PASS)、`dec promote`、`app.promote`、`mea.open`、`mea.close`(pending)、`mea.amend`（`window` 為該 `mea.close` 的 `seq`、`from` 為 pending、`to` 為 clean）、`mea.report`、`card`、`dec rollback`、`app.rollback` | measuring |

  各 PROP 的 `target` 互異（避免同型去重干擾）；`SC-LEGAL` 全部合法。`AT-108-4-1` 情境三的孤兒事件與情境四的運轉類違規事件於其後附加一筆，其對象為執行期組出、不存在或不 open 的號。
- **`SC-REV`**（`AT-108-2-E-1`）：`PROP-124` 為 proposed、`PROP-125` 為 approved（`prop`、`dec approve`）、`PROP-126` 為 rejected（`prop`、`dec reject`）、`PROP-127`（route 為 `handoff:DEF`）為 handed-off（`prop`、`dec ack-handoff`）、`PROP-128` 為 returned 且 `rev` 為 3（`prop`(1)、`dec return`、`prop`(2)、`dec return`、`prop`(3)、`dec return`）；各 `target` 互異；`RUN-SI-001` open。
- **`SC-SUSP`**（`AT-110-1-E-1`、`AT-103-1-E-1`；`stop_after_bad` 為 2）：`RUN-SI-001` 內 `PROP-124` 走到 `promoted` 後 `mea.open`、`mea.close`(recurred)；`PROP-125` 同樣走到 `promoted` 後 `mea.open`、`mea.close`(rolled-back)；再 `run.close` 為 `RUN-SI-001`（`outcomes` 兩個 PROP 皆 closed）；其後 `run.open` 為 `RUN-SI-002`（無研究事件）、`run.open` 為 `RUN-SI-003` 加其 `research.skip`。折疊結果：SUSPENDED，所在運轉為 `RUN-SI-001`。
- **`SC-WINDOWS`**（`AT-103-1-E-1` (f)）：`PROP-124`、`PROP-125` 各走到 `promoted` 後 `mea.open`、`mea.close`(pending)；`PROP-125` 的 `mea.close` 之後有 `mea.amend`（`window` 為該 `mea.close` 的 `seq`、`from` 為 pending、`to` 為 clean）。折疊結果：`pending_windows` 只有 `PROP-124` 的那一筆。
- **`SC-STATUS`**（`AT-103-1-1`；錨點 `Ta`＝現在減 1 日，第 9 筆事件的 `t`；其餘事件的 `t` 為 `Ta` 加（`seq` 減 9）分鐘）：缺陷帳本含 `Q1`～`Q6`；事件依序：(1) `run.open` `RUN-SI-001`；(2) `research.skip`；(3) `prop` `PROP-124`（P、`target` 為 `playbooks/demo.yaml`、`sources` 為 `OBS-SI-002`、`OBS-SI-003`）；(4) `dec approve`；(5) `app.sandbox`；(6) `app.verify`(PASS)；(7) `dec promote`；(8) `app.promote`；(9) `run.close` `RUN-SI-001`（`outcomes` 為 `PROP-124` 對 promoted）；(10) `run.open` `RUN-SI-002`；(11) `research.skip`（`quota-band`，`band` 為 `high`，屬 `RUN-SI-002`）；(12) `attr`（link，`from` 為 `OBS-SI-009`、`reopens` 為 `OBS-SI-002`，得 `ATT-SI-001`，`by` 為 `SA`）；(13) `attr.confirm` 為 `ATT-SI-001`（`by` 為 `QA`）；(14) `attr`（link，`from` 為 `OBS-SI-010`、`reopens` 為 `OBS-SI-006`，得 `ATT-SI-002`）；(15) `prop` `PROP-125`（D、`target` 為 `docs/notes/demo.md`、route 為 `handoff:DEF`、`sources` 為 `OBS-SI-001`、屬 `RUN-SI-002`）；(16) `prop` `PROP-126`（D、`target` 為 `docs/notes/other.md`、`sources` 為 `OBS-SI-004`、屬 `RUN-SI-002`）；(17) `dec reject` 為 `PROP-126`；(18) `attr`（root，`obs` 為 `OBS-SI-004`、`root_cause` 為 `tools/a-b`，得 `ATT-SI-003`）；(19) `attr`（root，`obs` 為 `OBS-SI-004`、`root_cause` 為 `tools/c-d`，得 `ATT-SI-004`）。
- **`SC-SCAN`**（AC-131-1～131-4 的 AT）：事件帳本只有 `run.open` 為 `RUN-SI-001` 與 `run.close`（`no_event`）；`run.close` 的 `t` 為錨點 `Ta`（現在減 1 日）；缺陷帳本含 `Q1`～`Q5`；錨點之後（提交時間為現在）有五個 commit：K1 觸及 `AutoClaude/x.py` 與 `AutoClaude/y.py`、K2 觸及 `AISDLC_SDD/z.md`、K3 觸及 `tools/lib/selfimproving/w.py`、K4 觸及 `tools/other.py` 與 `AgentConsole/c.ts`、K5 觸及 `docs/06_quality/SelfImproving_Foo.md`。預期桶：`AutoClaude`、`AISDLC_SDD`、`SelfImproving`（K3 與 K5）、`根層`、`AgentConsole` 各一個候選。
- **`SC-SCAN-QUIET`**：同 `SC-SCAN` 的事件帳本，缺陷帳本只含 `Q3`、`Q4`、`Q5`（皆不符合），錨點之後沒有 commit。
- **`SC-EXPORT`**（AC-132-5 與 AC-140-2 的 AT，及 `AT-143-1-E-2`）：以 CLI 依序：`run-open`（`RUN-SI-001`）、`research --skip`（offline）、`attr`（root，`ATT-SI-001`）、`attr-confirm`（`by` 為 `QA`）、`prop-new` 得 `PROP-SI-124`（P、loop）、`prop-new` 得 `PROP-SI-125`（新增 `.claude/hooks/new_guard_e.py` 與 `docs/notes/clean_e.md`，`--handoff T1`）、`run-open`（`RUN-SI-002`）、`run-close`（`RUN-SI-002`，得 `no_event`）；最後提交，工作樹乾淨。
- **`SC-WEIRD`**（`AT-108-4-E-3`、`AT-140-1-E-2`；SCG-4 一審 F-02）：每份複本的事件帳本恰兩行——`seq` 為 1 的合規 `run.open`（`RUN-SI-001`），與 `seq` 為 2 的一筆怪異事件（`t` 取 `T0` 加 2 分鐘）。怪異事件共四型，皆為「某個欄位值的型別怪異、其餘合規」：`W1`＝`research.skip`（`by` 為 `main`、`run` 為 `RUN-SI-001`、`reason` 為 JSON 陣列 `["a"]`、`note` 為 `x`）；`W2`＝`attr`（`by` 為 `x`、`id` 為 `ATT-SI-099`、`type` 為 JSON 陣列 `["root"]`，除共通鍵與 `id`、`type` 外無其他鍵）；`W3`＝`attr`（`by` 為 `x`、`id` 為 `ATT-SI-098`、`type` 為 `root`、`obs` 為 `[["x"]]`、`items` 為 `[["DOC", "a.md"]]`、`root_cause` 為 `a/b`）；`W4`＝`attr.confirm`（`by` 為 `QA`、`att` 為 JSON 陣列 `["ATT-SI-001"]`）。四型皆使 `events.structure` 恰報 `(seq=2, EVENT-TYPE)`（R37）。夾具以 `ev(…)` 手寫，欄位值原樣寫入、不經任何型別檢查。
- **`SC-SUSP-MIX`**（`AT-103-1-E-2`；`stop_after_bad` 為 2）：`RUN-SI-001` 與其研究事件在最前（同 `SC-SUSP`）；其後依情境逐個建 `PROP-SI-124`、`PROP-SI-125`（情境 (d) 另加 `PROP-SI-126`），每個 PROP 走 `prop`、`dec approve`、`app.sandbox`、`app.verify`（`PASS`）、`dec promote`、`app.promote`、`mea.open`、`mea.close`；各 `mea.close` 的 `result` 依 `AT-103-1-E-2` 所列的順序取值；不含 `run.close` 與 `dec resume`。
- **`SC-STATUS-WIN`**（`AT-103-1-E-3`、`AT-140-2-E-2`；事件的 `t` 取 `T0` 加（`seq` 分鐘））：(1) `run.open` `RUN-SI-001`；(2) `research.skip`（`offline`）屬 `RUN-SI-001`；(3) `attr`（link，`from` 為 OBS 列 009、`reopens` 為 OBS 列 002，得 `ATT-SI-001`，`by` 為 `SA`）；(4) `attr.confirm` 為 `ATT-SI-001`（`by` 為 `QA`）；(5) `run.close` 為 `RUN-SI-001`（`no_event`）；(6) `run.open` `RUN-SI-002`；(7) `research.skip`（`offline`）屬 `RUN-SI-002`；(8) `attr`（link，`from` 為 OBS 列 010、`reopens` 為 OBS 列 006，得 `ATT-SI-002`，`by` 為 `SA`）；(9) `attr.confirm` 為 `ATT-SI-002`（`by` 為 `QA`）。缺陷帳本只含 §5.1 的 `D1`（不符合 (c)）。
- **`SC-SCAN-EDGE`**（`AT-131-2-E-3`、`AT-140-2-E-2`）：事件帳本只有 `run.open`（`RUN-SI-001`）與 `run.close`（`no_event`），後者的 `t` 為錨點 `Ta`（現在減 1 日，秒精度、帶 offset）；缺陷帳本含 `D1`；基線與事件帳本先提交（提交時間為 §5.1 的固定時間）；其後兩個 commit：`K1` 於 `Ta` 提交（新增 `AutoClaude/x.py`）、`K2` 於 `Ta` 加 1 秒提交（新增 `AISDLC_SDD/z.md`）；以 `commit_all(R, …, when=<帶 offset 的 ISO 字串>)` 取得精確的 committer 時間。

### 5.3 迷你 PRD、patch 與本文建構器、記憶目錄、案例表

**P1 迷你 PRD**（`docs/01_requirements/SelfImproving_PRD.md`；含恰一個含字面 `**實體 glob**` 的行，內容逐字如下，沿 P0 §5.3 的抽取規則，另追蹤最近的 `(i)`～`(v)` 標籤）：

```text
- **實體 glob**：(i) `**/CLAUDE.md`；`AISDLC_SDD/*/governance/rules/R-*.yaml` 中**既有且 `maturity: active`** 者（新增的 `trust_level: proposed` 不在此列）；(ii) `**/.claude/**`、根 `CLAUDE.md`〈守衛面准入〉所列 `tools/lib/` 檔、`tools/guard.py`；(iii) `docs/06_quality/SelfImproving_Protocol/**`、`tools/probe/selfimproving_measure.py`；(iv) `docs/01_requirements/SelfImproving_PRD.md`、`docs/05_development/SelfImproving_*.md`、`docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/06_quality/SelfImproving_Event_Ledger.jsonl`、`docs/06_quality/SelfImproving_Proposals/**`、`tools/selfimproving.py`、`tools/lib/selfimproving/**`；(v) `AISDLC_SDD/AISDLC_SDD_v*/**` 去掉 LATEST（`python AISDLC_SDD/scripts/sdd_version.py` 現查）、`**/docs_template/**`。
```

**P1 迷你根 `CLAUDE.md`** 同 P0 §5.3（含 `守衛面＝` 行與 `tools/lib/{aa,bb,cc}.py` 的大括號展開）。**夾具的 `non_evolvable_globs`（18 項，依位元組序）**：`**/.claude/**`、`**/CLAUDE.md`、`**/docs_template/**`、`AISDLC_SDD/*/governance/rules/R-*.yaml`、`AISDLC_SDD/AISDLC_SDD_v*/**`、`docs/01_requirements/SelfImproving_PRD.md`、`docs/05_development/SelfImproving_*.md`、`docs/06_quality/SelfImproving_Event_Ledger.jsonl`、`docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/06_quality/SelfImproving_Proposals/**`、`docs/06_quality/SelfImproving_Protocol/**`、`tools/guard.py`、`tools/lib/aa.py`、`tools/lib/bb.py`、`tools/lib/cc.py`、`tools/lib/selfimproving/**`、`tools/probe/selfimproving_measure.py`、`tools/selfimproving.py`（即迷你 PRD 抽出的 15 項加迷你 `CLAUDE.md` 展開的 3 項；`AT-142-1-1` 的 `params.globs` 為 `PASS` 同時驗證此清單與抽取規則一致，不一致時以 P0 R22 為準、修本節清單）。群組歸屬：(iii)＝評估器群組、(iv)＝迴圈自身群組（R52 (f)）。

**建構器**（夾具模組）：
- `patch_mod(path, edits)`、`patch_add(path, lines)`、`patch_del(path)`、`patch_rename(old, new, edits=())`、`patch_copy(src, dst)`、`patch_join(*patches)`：各回傳 `bytes`（LF、UTF-8）；`patch_mod` 與 `patch_del` 依夾具檔的已知內容算出正確的 hunk 標頭計數；選項 `quote=True` 以 C-style 引號輸出標頭路徑；`tab_suffix=<字串>` 於 `---`／`+++` 行尾加 TAB 與該字串。
- `body_md(cls="P", **fields)`：回傳合規 `rN.md` 文字：五節標題 `## 反例證據`、`## Before`、`## After`、`## 影響面`、`## 欄位`；`欄位` 節含 `| 欄位 | 內容 |` 表頭、分隔列與各欄位列。預設值：`symptom` 為 `卡面症狀一句`、`risk` 為 `風險一句`、`rollback` 為 `git revert 該 patch`、`budget` 為 `1 次子代理、約 3000 token`、`result_label` 為 `失敗`、`scope` 為 `夾具範圍`；M 類另預設 `source_obs` 為 `OBS-SI-001`、`retire_when` 為 `該症狀不再出現`；`drop=[…]` 刪去指定欄位列、`skeleton_drop=[…]` 刪去指定標題。
- `good_prop_args(R, cls="P", **over)`：回傳 `prop-new` 的旗標串列並於 tmp 寫好 patch 與本文檔（`--run` 由呼叫者補）。各類預設：`P`＝`--cls P --action modify --target playbooks/demo.yaml`，patch 取代該檔第 3、4 行；`D`＝`--target docs/notes/demo.md`，patch 取代第 3、4 行；`R`＝`--action add --target AISDLC_SDD/<VNEW>/governance/rules/R-9.9.yaml`，patch 新增該檔（內容含 `trust_level: proposed`）；`M`＝`--target memory/demo.md --memory-dir <記憶目錄>`，patch 取代 `demo.md` 第 3、4 行；皆 `--source OBS-SI-001 --source OBS-SI-002 --proposer SA`。`over` 可覆寫 `target`、`sources`、`patch`、`body`、`handoff`、`reviewer`。
- `open_run(R)`：呼叫 `run-open --trigger a --coord tools/a.py:1 --by main` 與 `research --skip --reason offline --note 離線驗證`，回傳運轉號。`fresh(R0)`：自一份已 `open_run` 的樣板 repo `copytree` 出一份獨立複本（每個測試檔於 `setUpModule` 建一次樣板）。
- **記憶目錄夾具 `memory_dir(tmp)`**：`MEMORY.md` 120 行（第 N 行為 `- [條目 NNN](m_NNN.md) — 一句說明 NNN`）、`archive-index-old.md` 30 行（同樣式）、`demo.md` 20 行（第 N 行為 `note NN`）；邏輯路徑 `memory/<名>` 對映 `<記憶目錄>/<名>`。歸檔型 patch 把 `MEMORY.md` 的前 K 行逐字附加到 `archive-index-old.md` 末尾（hunk 為 `@@ -30,0 +31,K @@`）、並自 `MEMORY.md` 刪除該 K 行（可另加一個指標行）。

**案例表 `TOUCH-CASES`**（`AT-107-3-1`；皆 `--cls D --action modify`，皆預期受理且 `route` 為 `loop`；「預期集合」為排序去重的 repo 相對 POSIX 路徑）：

| 案 | patch 形態 | `--target` | 預期 touched 集合 |
|----|-----------|-----------|--------------------|
| T01 | 標準修改：`docs/notes/demo.md` 取代 2 行（`diff --git`、帶 `a/`、`b/` 前綴的 `---`／`+++`） | `docs/notes/demo.md` | `docs/notes/demo.md` |
| T02 | 新增：`docs/notes/new_a.md`（`new file mode`、`--- /dev/null`） | `docs/notes/new_a.md` | `docs/notes/new_a.md` |
| T03 | 刪除加修改：刪 `docs/notes/tiny.md`（3 行全刪、`+++ /dev/null`）並取代 `docs/notes/demo.md` 1 行 | `docs/notes/demo.md` | `docs/notes/tiny.md`、`docs/notes/demo.md` |
| T04 | 純改名（無 hunk）：`docs/notes/other.md` 到 `docs/notes/renamed.md`，`similarity index 100%`、`rename from`、`rename to` | `docs/notes/renamed.md` | `docs/notes/other.md`、`docs/notes/renamed.md` |
| T05 | 改名加修改：`docs/notes/f1.md` 到 `docs/notes/f1_moved.md`，一個 hunk 取代 1 行，`---` 指舊檔、`+++` 指新檔 | `docs/notes/f1_moved.md` | `docs/notes/f1.md`、`docs/notes/f1_moved.md` |
| T06 | 複製：`copy from docs/notes/f2.md`、`copy to docs/notes/f2_copy.md`，`similarity index 100%` | `docs/notes/f2_copy.md` | `docs/notes/f2.md`、`docs/notes/f2_copy.md` |
| T07 | 帶空白的路徑：新增 `docs/notes/dir with space/a b.md`，所有標頭路徑以雙引號包住 | 該路徑 | 該路徑 |
| T08 | 八進位跳脫的 UTF-8 路徑：新增 `docs/notes/日本.md`，標頭路徑為 `"a/docs/notes/\346\227\245\346\234\254.md"` 形 | `docs/notes/日本.md` | `docs/notes/日本.md` |
| T09 | `---`／`+++` 行尾帶 TAB 與執行期組出的時間戳：修改 `docs/notes/f3.md` 1 行 | `docs/notes/f3.md` | `docs/notes/f3.md` |
| T10 | 多檔且重複：同一個 `docs/notes/f4.md` 兩個 hunk，加 `docs/notes/f5.md` 一個區塊；另有兩個檔案區塊順序顛倒的版本 | `docs/notes/f4.md` | `docs/notes/f4.md`、`docs/notes/f5.md`（兩個版本的 `touched_sha256` 相同） |

**案例表 `HANDOFF-CASES`**（`AT-107-3-E-1`；每案的 patch 新增兩個檔：該列的命中路徑與乾淨檔 `docs/notes/clean_x.md`；`--cls D --action add --handoff T1`；預期 `route` 為 `handoff:T1`、`touched_count` 為 2。H15 為純改名，命中只在來源端）：

| 案 | 命中路徑 | 對應群組或規則 |
|----|---------|----------------|
| H01 | `CLAUDE.md` | (i) 根 |
| H02 | `AutoClaude/CLAUDE.md` | (i) 子專案 |
| H03 | `.claude/hooks/new_guard_a.py` | (ii) |
| H04 | `AutoClaude/.claude/hooks/new_guard_b.py` | (ii) 子專案 |
| H05 | `AISDLC_SDD/<VNEW>/.claude/hooks/new_guard_c.py` | (ii) 版本目錄下 |
| H06 | `tools/guard.py` | (ii) 守衛面檔 |
| H07 | `AISDLC_SDD/<VOLD>/agent/a.md` | (v) 凍結版本目錄 |
| H08 | `AISDLC_SDD/<VNEW>/docs_template/t.md` | (v) 模板 |
| H09 | `docs/06_quality/SelfImproving_Event_Ledger.jsonl` | (iv) |
| H10 | `docs/06_quality/SelfImproving_Proposals/PROP-SI-001/r1.md` | (iv) |
| H11 | `docs/06_quality/SelfImproving_Observation_Ledger.md` | (iv) |
| H12 | `docs/05_development/SelfImproving_Operations_SOP.md` | (iv) |
| H13 | `docs/01_requirements/SelfImproving_PRD.md` | (iv) 且規格本體 |
| H14 | `claude.md`（H14a）、`AutoClaude/Claude.MD`（H14b） | (i) 的大小寫變體（`casefold`） |
| H15 | 純改名：`CLAUDE.md` 到 `docs/notes/c.md` | (i)，命中在來源端 |

**案例表 `ALIAS-CASES`**（`AT-107-3-E-2`；每案的 patch 新增兩個檔：別名路徑與 `docs/notes/clean_x.md`；`--cls D --action add --handoff T1`；預期受理且 `route` 為 `handoff:T1`、`touched_count` 為 2；磁碟機代號形態於執行期以字串相加組出）：

| 案 | 別名路徑 | 規則（R51 (c)） |
|----|---------|-----------------|
| A01 | `docs/notes/../../outside.md` | 含 `..` 段 |
| A02 | `/etc/x.md`（標頭寫成 `a//etc/x.md` 形） | 以 `/` 起頭 |
| A03 | 磁碟機代號開頭的 `X:/x.md`（執行期組出） | 含 `:` |
| A04 | `docs/notes/f.md::$DATA` | 含 `:`（資料流） |
| A05 | `docs/notes/demo.md.` | 尾端點 |
| A06 | `docs/notes/demo.md `（尾端空白，標頭路徑以雙引號包住） | 尾端空白 |
| A07 | `docs/notes/nul.md` | 保留裝置名 `nul` |
| A08 | `docs/aux/x.md` | 保留裝置名 `aux`（目錄段） |
| A09 | `docs/notes/COM1.txt` | 保留裝置名 `com1`（`casefold`） |
| A10 | `"docs/n\001.md"`（八進位跳脫的控制字元） | 控制字元 |
| A11 | `docs\..\CLAUDE.md` | 反斜線換 `/` 後含 `..` |

**狀態字串母體 `STATUS-CORPUS`**（`AT-131-2-E-2`；兩個解析器對每個字串的分類須相等；下表「預期」欄是對既有 `_classify` 實測的分類，供自證，不另立判準）：

| 狀態字串 | 預期分類 |
|----------|----------|
| `open`、`open（workaround-applied）`、`partial（只修了一半）`、`workaround`、`修復後open尚待驗證`、`open；後續 fixed` | `open` |
| `fixed@abc1234`、`fixed`、`fixed；後續 open` | `fixed` |
| `wontfix` | `wontfix` |
| `closed-by-decision`、`no_action_needed`、`no action needed` | `closed-by-decision` |
| `routed：外部` | `routed` |
| `reopened`、`unfixed`、`Fixed`、空字串、`deferred；再開症狀：x`（各是一個字串） | `None` |

### 5.4 本機 HTTP 夾具、來源表與真檔案

- **`serve(routes)`**：以標準庫 `http.server.ThreadingHTTPServer` 綁 `127.0.0.1`、連接埠 0（系統配），守護執行緒；回傳物件 `srv`：`srv.url(path)`、`srv.port`、`srv.requests`（每筆含 `path` 與全小寫鍵的 `headers`）、`srv.max_inflight`（同時在途請求的最大值）、`srv.arrived(path)`（請求到達時被設定的 `threading.Event`）、`srv.close()`（測試結束必關）。`routes` 的值為〔狀態碼, 標頭 dict, 本文位元組〕，另可帶 `delay`（秒）或 `hold`（等待測試放行的 `threading.Event`），兩者都在送出狀態列**之前**等待；另可帶 `drip`（秒數：送完狀態列與標頭後，每隔該秒數送出本文的 1 個位元組，直到本文送完、連線中斷或 `srv.close()`）或 `stall`（`threading.Event`：送完狀態列與標頭後不送本文，直到該 Event 被設定、連線中斷或 `srv.close()`）——這兩個選項供 R58 (d) 的牆鐘強制點負控使用（`Content-Length` 取路由標頭或本文長度，故路由本文須長於逾時內可滴完的量）；重導向路由為狀態 302 加 `Location`。
- **`write_table(R, srv, entries, *, retired=(), commit=True)`**：把來源表寫到協定目錄並（`commit` 為真時）提交；`entries` 的每個元素為〔`id`, 路由路徑〕，`url` 取 `srv.url(路徑)`、`kind` 為 `docs`、`extract` 為 `讀標題`、`added_by` 為 `夾具`；`retired` 內的 `id` 加 `"retired": true`；`sources` 依 `id` 位元組序排序。表檔為 UTF-8 無 BOM、LF、結尾換行。
- **`relaxed()`**：context manager，以 `mock.patch.object(sources, "DEFAULT_POLICY", sources.Policy(allow_http=True, allow_loopback=True))` 暫時放寬政策（`research --fetch` 的 in-process 呼叫須在其內進行）。
- **真檔案（唯讀，測試不得修改）**：`docs/06_quality/SelfImproving_Protocol/params.json`、`metrics.md`、`research_sources.json`、`docs/05_development/SelfImproving_Operations_SOP.md`、`docs/01_requirements/SelfImproving_PRD.md`、`docs/02_architecture/Root_Layout_and_Module_Placement.md`、根 `CLAUDE.md`、`.claude/settings.json`、`tools/selfimproving.py`、`tools/lib/selfimproving/*.py`、`AISDLC_SDD/scripts/sdd_version.py`、`AutoClaude/autoclaude/**`、`AutoClaude/CLAUDE.md`、`AutoClaude/tests/core/test_kernel_unhandled_mutation_failloud_r85.py`。測試以 `Path(__file__).resolve().parents[2]` 為 repo 根（鍵 B 的檔以 `parents[2]` 為 `AutoClaude/`、其上一層為 monorepo 根）。**測試不讀真帳本、真事件帳本與真提案目錄。**
- **SOP 判準夾具**：`sop_sections(text)`（依 `## ` 標題切段，回傳〔標題, 節文字〕串列）、`line_has_all(section, *fragments)`（取節內、不在程式碼圍欄內、同時含全部片段的行）、`sop_problems(text)`（依 R65 (a)～(g) 的片段清單 `FRAGMENTS` 回傳不滿足者，每項點名節與片段）、`prd_entry_fragments(prd_text)`（取 PRD 模組體檢入口表資料列第 2 欄的全部反引號片段）。

### 5.5 hermetic 環境

沿 P0 §5.5，並增列：(a) 每個會呼叫 git 的測試在 `mock.patch.dict(os.environ, …)` 之下執行：先移除 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE`、`GIT_COMMON_DIR`、`GIT_PREFIX`、`GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES`；再設 `GIT_CONFIG_GLOBAL` 指向 tmp 內一個空檔案、`GIT_CONFIG_NOSYSTEM=1`、作者與提交者的名稱與電子郵件、`GIT_TERMINAL_PROMPT=0`、固定的 `GIT_AUTHOR_DATE` 與 `GIT_COMMITTER_DATE`（§5.1）；測試建立的 repo 以 `-c commit.gpgsign=false -c core.autocrlf=false` 提交；寫檔一律 `encoding="utf-8"`、`newline="\n"`（CRLF 情境明確以位元組寫入）。(b) `AUTOSDD_SI_DIR` 指向 tmp 內的 `HOME`（每個測試各自一個）；需要「逐字稿目錄取不到」的情境（`status`、`export --kind status` 與一切會算 `friction_reconcile` 的 AT）另把環境變數 `HOME` 與 `USERPROFILE` 指向空的 tmp 目錄並移除 `CLAUDE_CONFIG_DIR`（`claude_home()` 先認它）。(c) 不連外網：只有本機 loopback 夾具；動態零網路的 AT 以 `socket.socket.connect` 被替換為拋例外的方式驗證。(d) 子行程（`python tools/selfimproving.py …`）以 `[sys.executable, <入口絕對路徑>, …]` 啟動，環境取上列淨化後的環境加 `PYTHONIOENCODING` 等情境變數；子行程併發夾具必回收。(e) git 缺席視為環境壞、測試直接失敗（不得 skip）。(f) 事件與 PROP 號等需要避開真帳本的編號，於執行期組出。

### 5.6 允許變更的檔案集合（與 PRD §9.1〈C4 套件檔案表〉及模組落點表逐格一致）

**Developer 棒新增**：
- `tools/lib/selfimproving/{events,fold,evcheck,paths,props,defs,sources,card,status,scan,export}.py`（11 檔，能力類別 `ro`）、`{evwrite,propfiles,writeverbs}.py`（3 檔，`rw`）、`{fetch,research}.py`（2 檔，`net`；`fetch.py` 唯一 import 網路模組）——合計 16 檔，與登記表 `CAPABILITY` 的 24 個鍵（既有 8 檔加新 16 檔）逐一對應。
- `tools/tests/test_selfimproving_events.py`、`test_selfimproving_props.py`、`test_selfimproving_research_scan.py`、`test_selfimproving_export_status.py`、`test_selfimproving_capability.py`、`test_root_module_layout.py`，與共用夾具模組 `tools/tests/_selfimproving_fixtures.py`。
- `AutoClaude/tests/contract/test_evolution_propose_only.py`（鍵 B）。
- `docs/06_quality/SelfImproving_Protocol/research_sources.json`（初值 7 筆，取自 PRD FR-SI-30〈初始研究來源表〉：`id` 依位元組序遞增、`url` 與 `extract` 逐字取自該表〔未驗〕、`added_by` 為 T1 座標 `sid ee6af537-7091-4f0e-842c-0d091085f77b line 13`）。

**Developer 棒修改**：
- `tools/selfimproving.py`（只增 argparse 子命令與 handler；`writeverbs`、`research` 於 handler 內延遲 import）。
- `tools/lib/selfimproving/{check,params,rows,git,history,refs}.py`（六個既有 `ro` 檔，限 R36～R46、R51 (b) 所需；`ledger.py`、`__init__.py` 不動，若須動則於交卷說明）。
- `docs/06_quality/SelfImproving_Protocol/params.json`（加五鍵；`metrics.md` 不動）。
- `docs/05_development/SelfImproving_Operations_SOP.md`（定稿：四角色節、研究者節、模組體檢任務書範本、研究事件條文）。
- `tools/tests/test_selfimproving_check.py`（只改 R67 列出的五處站點）。

**主控收尾另動**：`AutoClaude/CLAUDE.md`（AC-SI-28-2 的改述，與鍵 B 測試同輪落地）；根層鎖檔與棘輪重釘（護欄層行數、`tools/tests` 檔數下限與 E501、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE` 具名一次性例外，NFR-P1-9）；SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md` §3 登記列同步（落點鎖會讀它）；`docs/06_quality/RTM-SelfImproving-P1-<日期>.md`；真帳本、真事件帳本與真 `SelfImproving_Proposals/` 的實跑與入帳。**其餘一律不動**：尤其不動 PRD、研究方法 SOP、P0 TCS、`.claude/**`、`AutoClaude/autoclaude/` 引擎原始碼；真帳本與真事件帳本只由主控寫（Developer 棒不得碰）。

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| PRD FR-SI-05～11、14、28、30、31、34，加 FR-SI-32 的 AC-SI-32-5，加 AC-SI-02-1／03-1／03-2 的 P1 機械半 → F-002 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-002 → US-101～US-109 | ☑ 已映射 |
| US-101～US-109 → 本檔 54 個 AC | ☑ 已映射（FRD-lite） |
| PRD 的 44 個 P1 AC（鍵 A 41 個、鍵 B 3 個）→ 本檔 `AC-102-1`～`AC-134-4` 與 `AC-128-1`～`AC-128-3` | ☑ 已映射（編號規則見 FRD-lite 與 §7.1 ⚖ 1） |
| 本檔自增的 10 個 AC（`AC-140-1`、`AC-140-2`、`AC-141-1`、`AC-141-2`、`AC-142-1`、`AC-142-2`、`AC-143-1`、`AC-144-1`、`AC-145-1`、`AC-145-2`）→ AT | ☑ 已映射 |
| 本檔 AC（54 個）→ AT（148 個：正控 58、負控 90） | ☑ 已映射（本檔 §1，覆蓋率 100%；每個 AC 至少一個正控與一個負控） |
| PRD §8.1 P1 出口 (a) 真實觀察端到端走到提案卡，且至少一筆屬 M／P／R／D 類 → AT-103-2-1、AT-106-1-1、AT-108-1-1、AT-114-1-1、AT-144-1-1 與實跑檢核 V8 | ☑ |
| PRD §8.1 P1 出口 (b) 零提案觸及正式面 → AT-107-1-1、AT-108-1-1、AT-108-3-1 與實跑檢核 V8、V9 | ☑ |
| PRD §8.1 P1 出口 (c) 卡面不清的退回為零 → AT-114-1-1、AT-114-1-2、AT-114-1-E-1、AT-114-2-1、AT-114-2-E-1、AT-114-3-1、AT-114-3-E-1 與實跑檢核 V8 | ☑ |
| PRD §8.1 P1 出口 (d) FR-SI-28 的可重跑檢查存在且綠 → AT-128-1-1、AT-128-1-E-1～E-4、AT-128-2-1、AT-128-2-E-1、AT-128-2-E-2、AT-128-3-1、AT-128-3-E-1 | ☑ |
| PRD §8.1 P1 出口 (e) 每個有 `prop` 的運轉都有研究事件 → AT-130-1-1、AT-130-1-E-1、AT-110-1-E-1 | ☑ |
| PRD §8.1 P1 出口 (f) 至少一次體檢子代理交卷入帳 ≥1 列（真實） → AT-131-5-1、AT-131-5-E-1（任務書與前後對照）與實跑檢核 V8 | ☑ |
| PRD §8.1 P1 出口 (g) 落點鎖存在且綠 → AT-134-1-1～AT-134-4-E-1（共 9 個，含 AT-134-3-E-2） | ☑ |
| PRD §8.1 P1 出口 (h) `si export` 存在且 AC-SI-32-5 綠 → AT-132-5-1、AT-132-5-E-1、AT-132-5-E-2、AT-132-5-E-3、AT-140-2-1、AT-140-2-E-1、AT-140-2-E-2 | ☑ |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由根層 unittest 閘門一併執行；鍵 B 走 autoclaude-ci；根層重釘由主控收尾） |

**R 規則覆蓋表**（R27～R67 各至少由一個 AT 引用；本表由 §2 各 AT 的標頭與本文所引用的 R 編號自動產生，不手工維護；R1～R26 屬 P0、由 P0 的 42 個 AT 覆蓋，P1 對其的重定見 R36、R63、R64、R67）：

| 規則 | 主題 | 引用該規則的 AT |
|------|------|-----------------|
| R27 | 動詞、旗標與 rc 表 | AT-110-3-E-1、AT-140-1-1、AT-140-1-E-1、AT-107-1-E-1、AT-111-1-E-1、AT-140-1-E-2 |
| R28 | 成功、拒收與草稿列的輸出文法 | AT-110-3-E-1、AT-140-1-E-1、AT-108-1-E-1、AT-140-1-E-3、AT-140-2-E-2 |
| R29 | 路徑常數、家目錄與 params 依賴 | AT-141-2-E-1、AT-145-1-E-1、AT-130-5-E-1、AT-141-2-E-3 |
| R30 | 事件行規約 | AT-141-1-1、AT-141-1-E-1 |
| R31 | 事件欄位表 | AT-141-1-1、AT-108-1-1、AT-108-4-E-4 |
| R32 | 配號 | AT-141-1-1、AT-141-1-E-1、AT-141-1-E-2 |
| R33 | 寫入鎖與鎖內判定 | AT-141-2-1、AT-141-2-E-1、AT-144-1-E-1、AT-141-1-E-2、AT-141-2-E-2 |
| R34 | PROP 狀態折疊表 | AT-108-4-1、AT-108-2-1 |
| R35 | 運轉、SUSPENDED 與冷卻折疊 | AT-110-1-E-1、AT-103-1-E-1、AT-103-1-E-2 |
| R36 | 追加項總則 | AT-142-1-1、AT-142-1-E-1、AT-142-2-1、AT-142-2-E-1、AT-143-1-E-2 |
| R37 | `events.structure` | AT-105-2-E-1、AT-108-4-E-2、AT-108-4-E-3、AT-108-4-E-4、AT-140-1-E-2 |
| R38 | `events.transitions` | AT-106-1-E-1、AT-108-4-1、AT-108-4-E-2、AT-108-4-E-3、AT-108-4-E-5 |
| R39 | `events.mutated` | AT-108-4-E-1 |
| R40 | `events.vacuity` | AT-108-4-E-2 |
| R41 | `events.prop_files` | AT-142-1-E-1、AT-144-1-1 |
| R42 | `events.research` | AT-130-1-1、AT-130-2-1、AT-130-2-E-2、AT-108-4-E-5、AT-130-2-E-4 |
| R43 | `research.sources` 與來源表檔格式 | AT-142-1-E-1、AT-145-1-1、AT-130-2-1、AT-130-2-E-1 |
| R44 | 標記欄擴充 | AT-142-1-E-2、AT-130-4-1、AT-130-4-E-1 |
| R45 | 復發候選提示 | AT-106-2-E-2、AT-131-2-E-2 |
| R46 | `params.json` 新鍵、指紋排除與判準版本 | AT-142-1-1、AT-145-1-1、AT-145-1-E-1、AT-130-6-1、AT-130-6-E-1 |
| R47 | `run-open`／`run-close` | AT-110-3-1、AT-110-3-E-1、AT-103-2-1、AT-103-2-E-1 |
| R48 | `attr`／`attr-confirm`／`attr-reject` | AT-105-1-1、AT-105-1-E-1、AT-105-2-1、AT-105-2-E-1、AT-106-1-1、AT-106-1-E-1、AT-106-2-1、AT-106-2-E-1 |
| R49 | `prop-new`／`prop-revise` 流程 | AT-107-3-E-2、AT-108-1-1、AT-108-1-E-1、AT-108-2-1、AT-108-2-E-1、AT-114-3-E-1、AT-107-3-E-4 |
| R50 | `rN.md` 形態 | AT-109-1-1、AT-109-1-E-1、AT-109-3-1、AT-109-3-E-1、AT-110-2-1、AT-110-2-E-1 |
| R51 | `touched` 導出與別名形態拒收 | AT-107-3-1、AT-107-3-E-2、AT-107-3-E-4 |
| R52 | 不可進化面、合法根、規格本體路徑與 `route`／`cls` 判定 | AT-107-1-1、AT-107-1-E-1、AT-107-3-E-1、AT-107-3-E-3、AT-108-3-1、AT-108-3-E-1、AT-111-1-1、AT-111-1-E-1 |
| R53 | 前置檢查：來源、運轉、研究事件、預算、SUSPENDED、同型、修訂 | AT-102-1-1、AT-102-1-E-1、AT-110-1-1、AT-110-1-E-1、AT-130-1-1、AT-130-4-1、AT-130-4-E-1 |
| R54 | 觸及比例、新增條目、歸檔型豁免與 M 類 pre-image | AT-109-2-1、AT-109-2-E-1、AT-109-3-1 |
| R55 | digest 與內容檔落地 | AT-108-1-1、AT-144-1-1、AT-144-1-E-1 |
| R56 | `card` | AT-110-2-1、AT-114-1-1、AT-114-1-E-1、AT-114-2-1、AT-114-2-E-1、AT-114-3-1、AT-114-3-E-1、AT-140-2-1、AT-114-1-2、AT-140-2-E-2 |
| R57 | `research` 通則與 `--skip` | AT-130-1-1、AT-130-1-E-1、AT-130-2-1、AT-130-2-E-1、AT-130-3-E-1、AT-130-3-E-2、AT-130-3-E-3、AT-130-5-1、AT-130-5-E-1、AT-130-3-E-4 |
| R58 | 抓取行為與事件 | AT-130-2-E-3、AT-130-3-1、AT-130-3-E-1、AT-130-3-E-3、AT-130-5-1、AT-130-5-E-1、AT-130-3-E-5、AT-130-5-E-2 |
| R59 | `scan` | AT-131-1-1、AT-131-1-E-1、AT-131-2-1、AT-131-2-E-1、AT-131-2-E-2、AT-131-3-1、AT-131-3-E-1、AT-131-4-1、AT-131-4-E-1、AT-140-2-1、AT-131-2-E-3、AT-140-2-E-2 |
| R60 | `status` | AT-103-1-1、AT-103-1-E-1、AT-140-2-1、AT-103-1-E-2、AT-103-1-E-3、AT-140-2-E-2 |
| R61 | `export` | AT-132-5-1、AT-132-5-E-1、AT-132-5-E-2、AT-140-2-1、AT-140-2-E-1、AT-132-5-E-3、AT-140-2-E-2 |
| R62 | 落點鎖 `tools/tests/test_root_module_layout.py` | AT-134-1-1、AT-134-1-E-1、AT-134-2-1、AT-134-2-E-1、AT-134-3-1、AT-134-3-E-1、AT-134-4-1、AT-134-4-E-1、AT-134-3-E-2 |
| R63 | 能力登記與純度 | AT-131-1-1、AT-143-1-1、AT-143-1-E-1、AT-143-1-E-2 |
| R64 | 常駐機制禁字樣 | AT-143-1-E-2 |
| R65 | Operations SOP 定稿 | AT-145-2-1、AT-145-2-E-1、AT-107-2-1、AT-107-2-E-1、AT-111-2-1、AT-111-2-E-1、AT-109-1-2、AT-110-2-2、AT-130-4-2、AT-131-5-1、AT-131-5-E-1、AT-145-2-E-2 |
| R66 | 鍵 B：「演化只提案不套用」可重跑檢查 | AT-128-1-1、AT-128-1-E-1、AT-128-1-E-2、AT-128-1-E-3、AT-128-1-E-4、AT-128-2-1、AT-128-2-E-1、AT-128-3-1、AT-128-3-E-1、AT-128-2-E-2 |
| R67 | 既有 P0 測試與鎖的連動同步 | AT-142-2-E-1 |

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（⚖ 1～⚖ 29）

| 編號 | 問題（PRD 內部矛盾或不可測處） | 本檔已採用的預設 | 替代與再開症狀 |
|------|--------------------------------|------------------|----------------|
| ⚖ 1 | AC 編號：PRD 的 `AC-SI-NN-Y` 與 PRD §5〈編號注意〉的 `AC-P1-001-1` 皆含字母，不合 ADR-XPLAT-016 §8.1 的 `AC-[\d\-]+`；任務書要求自 `AC-033` 起編自增 AC，與 PRD 的 `AC-SI-33-x`（P2b）、`AC-SI-34-x`（FR-SI-34）同號 | 百位 `1` 承載階段前綴：`AC-SI-NN-Y`＝`AC-1NN-Y`；自增 AC 自 FR 號位 40 起（`AC-140-1`…）；任務書與 PRD 不一致以 PRD 為準 | 替代：保留 PRD 全名並加編譯前置轉換（框架改動）。再開症狀：`sdd_compile` 對本檔回報 `unmapped_at_ids` 非空，或 RTM 對不上 PRD AC。建議：PRD 下次修訂把 AC 編號文法與 ADR-XPLAT-016 §8.1 對齊 |
| ⚖ 2 | `ref.carrier_families` 語意：P1 起事件帳本與提案內容檔已建立，P0 的「載體尚未建立」NE 對 `RUN-SI`、`ATT-SI`、`PROP-SI` 提及仍會印出（P0 R18 (d) 字面） | 不變：仍印 nonblocking NE（R36 (h)）；不影響 rc | 替代：P1 起依事件帳本與提案目錄現況判該家族載體已建立而 PASS。再開症狀：掌舵者或 QA 把「帳本已建立而仍印未判」讀成假訊號。建議：P1 修訂時把判準改為對三個已建立的家族查事件帳本 |
| ⚖ 3 | PRD AC-SI-08-4 ⑤（`dec` 引言回查）屬 P2、P1 要求印 NOT-EVALUABLE（未建），但未說印在哪一項、用哪個碼、什麼層級 | 印在 `events.transitions`，warn 層級 finding（項目狀態不變、不影響 rc），碼 `QUOTE-VERIFIER-NOT-ESTABLISHED`（R38），單一 finding；`helmsman` 免掃同形（R42 (d)）。原採 nonblocking NE，與 AT 要求的 `PASS` 不能並存，SCG-4 一審 §F ① 裁定採納實作 | 替代：新增第 29 個判定項。再開症狀：P2 落地時引言回查找不到掛接點 |
| ⚖ 4 | PRD §9.3 只給 `check`／`status`／`research`／`scan`／`export` 與 `prop-new --patch-file` 的旗標，未給其餘旗標、成功與拒收輸出文法、OBS 草稿列欄位細節、卡面逐行格式（只有 §7.3 線框）；AC-SI-14-3 的「每項單行且寬度 ≤ CARD_LINE_MAX」未說標題行（第 1 行，含目標路徑）算不算一項 | R27、R28、R56 的定義（本檔類推）；拒收碼表見判定碼表；標題行不受寬度限制、第 2～5 行與路徑行受限（R56 (b)）——標題行若受限，`R` 類（目標路徑逾 50 個字元，標題行除目標外已佔約 65 欄）與轉交卡（標題行再多 22 欄）幾乎必然超限 | 替代：掌舵者逐項裁決。再開症狀：SOP 角色任務書或 Console 需要不同旗標名或輸出行文法，或掌舵者要求標題行也限寬（則 `R` 類與轉交卡須改以縮寫座標顯示目標）。建議：PRD AC-SI-14-3 明寫哪幾行受寬度限制 |
| ⚖ 5 | PRD AC-SI-09-2 只給門檻與歸檔型豁免，未定義觸及比例的分子分母、新增條目的樣式，以及歸檔型下歸檔檔新增行是否計入條目 | R54：比例＝被刪行數總和÷被觸及既有檔在 base 的總行數；條目＝符合清單、編號、標題樣式的新增行加新檔個數；歸檔型只計索引檔新增的指標行 | 替代：以行數差、字元數或 token 估算。再開症狀：合法的小改被擋或大改被放行，被掌舵者回報 |
| ⚖ 6 | PRD 要求提案帶結果標籤與適用範圍、每提案宣告預算、一個動作的回滾配方、M 類四欄，但未給 `rN.md` 的欄位名與載體 | R50：`## 欄位` 節的 Markdown 表，鍵為 `symptom`、`risk`、`rollback`、`retire_when`、`reopen_symptom`、`budget`、`verify_plan`、`result_label`、`scope`、`source_obs` | 替代：改用 YAML frontmatter。再開症狀：提案者子代理反覆寫錯格式、被拒收率高 |
| ⚖ 7 | PRD AC-SI-10-1 的「同型」未定義根因鍵怎麼取 | R53 (e)：PROP 的根因鍵集合＝其 `sources` 與 `attr`（root）事件 `obs` 有交集者的根因鍵；兩集合相交或皆空即同型 | 替代：另設 `--root-cause` 旗標。再開症狀：同根因的兩個提案被判不同型，或不同根因被誤判同型 |
| ⚖ 8 | PRD AC-SI-11-1 要求 (iii)(iv) 群組命中時標 `evaluator-change`／`loop-self`，群組歸屬只在 NFR-SI-02-1 散文標籤內，無機器可讀形式 | R52 (f)：自 PRD 該行的標籤位置現抽（同 P0 R22），不另存第二份清單 | 替代：PRD 加機器可讀區塊。再開症狀：PRD 改標籤排版使抽取錯位（`AT-111-1-1` 的標籤搬移情境會先紅） |
| ⚖ 9 | PRD 只列 `status`、`scan`、`export` 的頂層欄位與意圖，未定義 `events_detected` 的元素、`scan` 候選的推導（候選只來自缺陷帳本與 commit 歸桶）、五個來源的計數口徑、探針輸出 glob、`export` 各 kind 的元素 | R59、R60、R61 | 替代：掌舵者逐項裁決。再開症狀：P1b 的 Bridge 與 backend DTO 對不上 `export` 輸出 |
| ⚖ 10 | PRD AC-SI-08-2「修訂超限＝rejected 加冷卻」，但 rejected 需要人決定事件（`dec`，P2） | P1 只拒收（`REV-LIMIT`），PROP 維持 returned（R49 (e)） | 替代：P1 讓 CLI 代寫 `dec reject`（違反決定只由人）。再開症狀：returned 的 PROP 因超限而永遠懸置 |
| ⚖ 11 | PRD §9.3 `attr` 列要求 confirm 或 reject 落定時於同一把鎖內重折疊採納窗並追加 `mea.amend`，其寫入者與欄位屬 P3（AC-SI-23-1） | P1 不實作（R48 (f)；見 §4 刻意不做） | 替代：P1 先寫 stub。再開症狀：P3 開工時發現落定事件與窗結果脫節 |
| ⚖ 12 | PRD §9.7 #48 漏列的 P0 連動：`test_AT_030_1_E_1` 的 `["status"]` 用法錯誤、SOP 四角色節須保留字面 `P1 定稿`（P0 的 `test_AT_032_1_1` 斷言它）；`check_rules_rev` 與指紋排除也牽動 P0 判準 | R67 與 R46 | 替代：另案處理。再開症狀：Developer 實作後 P0 測試仍有未同步的紅 |
| ⚖ 13 | PRD 說零事件的運轉記無事件，未說 `run-close` 的 `outcomes` 由誰填 | CLI 自折疊產生、不收旗標（R47 (b)） | 替代：由主控傳 `--outcome`。再開症狀：主控傳入的結果與折疊狀態不一致 |
| ⚖ 14 | P1 擴充 `check` 的判準語意，P0 R7 要求判準語意變動時人工 bump `check_rules_rev` | 1 改為 2（R46 (c)；`AT-142-1-1` 斷言 `fingerprint_parts.check_rules_rev` 為 2） | 替代：不 bump。再開症狀：指紋對追加項改版失明（M1～M5 數字被誤並列） |
| ⚖ 15 | PRD §9.2 列 19 個 kind 的詞彙，未列 P2 起 kind 的欄位名；`fold` 需要讀 `prop`、`dkind`、`verdict`、`flags`、`result`、`window`、`from`、`to`、`cause`、`run` | R31 末段（本檔類推；缺鍵者對折疊無貢獻並由 `events.transitions` 判 `TRANSITION-ORPHAN`） | 替代：各階段 TCS 定義。再開症狀：P2 TCS 的欄位名與本檔不同、須改 `fold` |
| ⚖ 16 | PRD 對 `rN.patch` 的雜湊口徑說法不一：digest 段寫 CRLF 正規化，AC-SI-07-3 要求 patch 以位元組導出路徑 | `.patch` 以原位元組存檔與雜湊（不做 CRLF 正規化）；`.md` 與來源表先換 LF（R41、R55）；`AT-142-1-E-1` 的 (e)(f) 釘住 | 替代：patch 也先換 LF。再開症狀：Windows 工作樹的 autocrlf 改變 `.patch` 位元組、使 `PROP-PATCH-SHA-MISMATCH` 假紅 |
| ⚖ 17 | PRD 寫「`row.provenance`／`row.markers` 加碼」，未指三個新碼各屬哪一項；AC-SI-06-2 的「新列」與已結列未定義 | R44（`RESEARCHER-*` 屬 `row.provenance`、`SRC-UNKNOWN` 屬 `row.markers`）、R45（新列＝工作樹有而 HEAD 無、處置首詞 `open`、無 `reopens` 標記；已結列的定義；候選為 warn，不影響 rc） | 替代：另設獨立判定項。再開症狀：候選提示對 DEF 列的精準度過低（DEF 列無分類欄，只比路徑；未量） |
| ⚖ 18 | 測試檔清單：任務書列 5 個測試檔；本檔另增 `test_selfimproving_capability.py`（PRD §9.4 判準的承載面）與共用夾具模組 | 7 個測試檔（含鍵 B）加夾具模組（§5.6） | 替代：併入 `events`。再開症狀：新增測試檔的重釘稅超出預期（NFR-P1-9） |
| ⚖ 19 | 任務書估 AT 60～90 條，同時要求每條 PRD AC 至少一正控一負控；PRD 有 44 條 AC、本檔自增 10 條，下限即 108 條 | 以覆蓋規則為準：原 126 條（正控 57、負控 69），SCG-4 一審後補測至 148 條（正控 58、負控 90）；每個 AC 皆有至少一個負控（流程型 AC 的負控＝SOP 片段刪去自證） | 替代：把部分 AC 的負向變體併入正控（P0 體例）。再開症狀：實作量或 CI 時間超出預期 |
| ⚖ 20 | PRD 只命名模組，未命名測試需要的函式與物件 | 本檔補定義：`evwrite.append_event`、`evwrite.PAUSE_HOOK`、`evwrite.LOCK_TIMEOUT_SECONDS`、`evwrite.LOCK_STALE_SECONDS`（R33）；`sources.validate_table`、`sources.Policy`、`sources.DEFAULT_POLICY`（R43）；`fetch.fetch_source`、`fetch.check_redirect`（R58）；`scan.bucket_of`（R59 (d)）；`git.apply_numstat`（R51 (b)）；`defs.classify_status`、`defs.load_ledger_status`（R45 (ii)） | 替代：Developer 另名並回寫本檔。再開症狀：實作與本檔的介面名不一致 |
| ⚖ 21 | PRD ADR-SI-10 併發負控 ① 寫「雙行程」加「測試鉤子」；鉤子須在同一行程內設定 | 以雙執行緒做確定性交錯（`AT-141-2-1` 情境一、二），跨行程由 8 行程×10 筆壓力承擔（情境三） | 替代：以環境變數驅動子行程內的鉤子（需在生產碼加讀環境變數的分支，與不新增守衛碼精神相左）。再開症狀：跨行程的交錯只靠壓力測試覆蓋而漏判 |
| ⚖ 22 | 流程型 AC（AC-SI-07-2、09-1 的語意半、10-2 的零遞迴、11-2、30-4 ①②、31-5、08-3 的不得阻塞 SCG）無機械物，PRD 已標邊界型 P | 以 SOP 條文片段的存在判準代位（R65），語意由實跑檢核 V7 對照 PRD；每個代位 AT 含刪去自證 | 再開症狀：SOP 措辭微調使 AT 反覆轉紅（P0 預審 F-11 同型） |
| ⚖ 23 | `status` 的 `friction_reconcile` measured 分支依賴逐字稿格式 | P1 不實作 measured 分支（§4〈刻意不做〉）；AT 驗兩種 NOT-EVALUABLE 原因（`AT-103-1-1` 驗 `transcript-unavailable`、`AT-103-1-E-3` 驗 `transcript-parser-not-established`），V8 於真逐字稿環境對照原因 | 再開症狀：掌舵者回報對帳數字與真實不符 |
| ⚖ 24 | 鍵 B 第 ⑤ 格依賴主控改寫 `AutoClaude/CLAUDE.md`：改述前 `AT-128-1-1` 為紅 | 改述與測試同輪落地（PRD AC-SI-28-2、D13；§1 的交付順序） | 替代：⑤ 先標 expected failure（違反 NFR-P1-4 不新增 xfail）。再開症狀：鍵 B 測試先於改述入庫而使 autoclaude-ci 紅 |
| ⚖ 25 | 讀不出 `maturity` 的既有 `R-*.yaml` 是否算命中不可進化面：PRD 只寫「既有且 `maturity: active` 者」 | 讀不出視同命中（fail-closed，R52 (d)；`AT-107-3-E-3` 的 `R-9.3.yaml`） | 替代：視為不命中。再開症狀：規則檔格式演進使合法提案被轉交 |
| ⚖ 26 | SCG-4 一審 F-02：R37 要求型別不合 ⇒ `EVENT-TYPE`，`fold` 檔頭要求絕不拋例外，但本檔未定義型別怪異的事件在折疊與各動詞中的處置——實作對陣列型欄位值（`reason`、`type`、`obs`、`att`）拋 `TypeError`，`check`、`status`、`export` 與多數寫入動詞整體崩潰 | R37 末段新增讀取側防禦：折疊只納入通過單事件判準的事件，未通過者對折疊沒有貢獻、其問題只由 `events.structure` 報；查表前先確認型別；怪異事件不算研究事件、不被折疊成運轉、ATT 或 PROP（`AT-108-4-E-3`、`AT-140-1-E-2`） | 替代：怪異事件仍納入折疊而各查表處各自防禦（規則會分歧）；或帳本含結構問題時寫入動詞一律拒寫（要新增拒收碼，行為面更大）。再開症狀：怪異事件被忽略使流程重複或漏做（例：某運轉的唯一研究事件是怪異事件），而 `check` 的 `EVENT-TYPE` 提醒被忽略；掌舵者要求結構問題時寫入動詞拒寫；或 Console 需要在 `export` 的 `problems` 看到型別怪異的事件（P1 只在 `check` 報） |
| ⚖ 27 | SCG-4 一審 F-12：R51 (b) 只寫 git 看到的路徑須在聯集內，未定義 `git apply --numstat` 自身失敗（損毀 hunk、context-diff）；實作把失敗吞成空集合（fail-open），且自寫解析器對 context-diff 導出垃圾路徑 | 失敗 ⇒ 拒收 `PATCH-PARSE`（R51 (b)、R49 (b)；`AT-107-3-E-4`） | 替代：失敗時改信自寫解析器（fail-open，與寧多勿漏的精神相左）。再開症狀：合法的 patch 因 git 版本差異被 `numstat` 拒收而大量 `PATCH-PARSE` |
| ⚖ 28 | SCG-4 一審 F-08 (f)：R29 要求家目錄不可寫 ⇒ rc 3，但「目錄存在而寫不進」在 Windows 與 POSIX 沒有共通的測試法（唯讀權限語意不同） | R29 規定可寫性探測檔名 `.probe-<行程號>`，AT 以同名目錄在兩平台一致地使建檔失敗（`AT-141-2-E-3`） | 替代：AT 於 POSIX 用 `chmod`、於 Windows 用 ACL（需平台分支，違反 NFR-P1-3）。再開症狀：探測檔改名而該 AT 不再能製造失敗 |
| ⚖ 29 | 判定指令形態：原 126 個 AT 只帶 `-k <底線形> -q`；鍵 B 指令在本機 PG 在場時 rc=4（SCG-4 一審 §F ⑤） | 新增 AT 的根層指令另加 `-p no:xdist -o addopts=`；鍵 B 全部（含既有九個）加 `-n 0`（`-p no:xdist` 不能與 `-n` 並用，實測 `unrecognized arguments`）；既有根層指令不改（實測可單跑） | 替代：把既有 117 個根層指令一併補旗標（機械改寫、無行為差）。再開症狀：根層出現全域 xdist 設定而使單一 AT 的 `-k` 指令行為不同 |

### 7.2 預審登記

（本檔尚未經 SCG-4 預審；預審與審查的發現登記於此，只登記、不改規格，凍結後的訂正走下方勘誤節。）

| 編號 | 預審所述 | 本檔處置 | 再開症狀 |
|------|----------|----------|----------|
| SCG-4 一審（FAIL；P1／P2／P3／P4＝0／8／6／8） | 報告 `docs/06_quality/SCG4-REVIEW-SelfImproving-P1-20261020.md` 的 F-01～F-22 與 §K 的八項勘誤建議 | 見〈勘誤一〉：條文訂正、補條文與 22 個新 AT；碼修歸 Developer 修復棒、`F-13`、`F-19`、`F-20` 歸主控 | 二審 QA 重放存活突變清單仍有未被打紅者，或新 AT 的期望值與修復後的實作不符 |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 54 個 AC 無未映射者（§1） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 有判定指令與驗收字樣；判定指令的 `-k` 字串等於 AT 底線形 | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（E 類；流程型 AC 的負向＝對 SOP 條文逐一刪去的副本須判不合格） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試（事件行位元組恰等於與少 1、觸及比例恰 0.2、新增條目恰 3、歸檔 50 與 51、核心區 12 行與寬度 100、運轉預算第 4 個、修訂上限、事件數下限、匯出上限、抓取三界、重導向 5 與 6 跳、check 層的事件行位元組 L 與 L－1、`note` 120 與 121、`http_status` 299 與 300、來源表提交時間與事件 `t` 同一秒、`scan` 起算時刻同一秒、`export` 筆數恰等於 `--limit`、慢滴回應的牆鐘） | □ |
| 併發負控 | 無鎖對照組撞號、有鎖後者得加一、8 行程×10 筆、陳舊鎖回收、新鮮鎖逾時（AT-141-2-1、AT-141-2-E-1） | □ |
| 純度與常駐機制 | 能力登記判準與其合成樹自證、動態載入面、零網路、14 個禁字樣樣本自證（AT-143-1-1、E-1、E-2） | □ |
| 測試資料規格完整 | 資料來源明確定義（§5；情境表、案例表、夾具函式） | □ |
| 實跑檢核 V1～V11 全部有逐字輸出證據 | 見下表；沒貼輸出＝未驗證 | □ |

**實跑檢核（非 AT；QA 於 SCG-4 親跑，輸出逐字貼入證據；AT 不碰真帳本與外網，真帳本與真來源的驗收全在這裡）**

| 編號 | 檢核 | 指令與證據 | 判斷標準 |
|------|------|-----------|---------|
| V1 | 範圍守衛 | `git diff --name-only <Developer 棒起點>..HEAD`；`git diff --stat -- .claude`；`git status --porcelain` | 只含 §5.6 的集合與主控收尾檔；`.claude/**`、PRD、研究方法 SOP、P0 TCS、`autoclaude/` 引擎原始碼無變動；真事件帳本與真 `SelfImproving_Proposals/` 不在 Developer 棒的 diff 內 |
| V2 | 真 repo `check` | `python tools/selfimproving.py check --json`（讀 rc 先存變數）；貼 JSON | rc 0；`items` 為 28 項；`research.sources` 為 PASS；`events.*` 六項為 PASS 或 nonblocking NE；`ref.obs` 為 PASS（字面反例 ID 一律以文字描述，不得寫成 `ref.obs` 抓得到的字面編號）；牆鐘小於 30 秒（取 3 次最大值） |
| V3 | P0 回歸與同步範圍 | `python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=`（逐字貼末行）；`git diff -U0 -- tools/tests/test_selfimproving_check.py` | 「42 passed」（子測試數以實跑為準）；diff 的 hunk 只落在 R67 列出的五處站點 |
| V4 | P1 新 AT 全套 | 對每個測試檔跑 `python -m pytest tools/tests/<檔> -q -p no:xdist -o addopts=`（六個）與鍵 B 的 `python -m pytest tests/contract/test_evolution_propose_only.py -q -n 0`（cwd＝`AutoClaude/`；`-n 0` 的原因見 NFR-P1-10 (1)）；另對 §2 的每個 AT 以 `-k <底線形>` 各跑一次 | 全綠；每個 `-k` 至少收到一個測試且不誤收其他 AT；每個 AT 的驗收字樣已在交卷逐項列出 |
| V5 | 護欄與零退化 | `ruff check` 對新增與改動的每個 `.py`；`python AutoClaude/tools/check_loc_budget.py --json`；`python tools/sync_onboarding_baselines.py --check-snapshot`；`python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）；`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（主控）；`tools/tests/test_defect_id_reference_integrity.py` | 皆 rc 0；護欄層重釘後淨差額 +0；根層全套 unittest 通過數以實跑為準；`git grep` 本檔與測試原始碼無不存在於真帳本的字面 `OBS-SI-<數字>` 或 `DEF-<數字>` |
| V6 | params 與來源表初值 | 逐鍵對照 PRD C5 與 §5.1；讀 `research_sources.json` | `params.json` 的五個新鍵初值為 8、262144、20、1、500（PRD C5），合計 28 鍵；來源表 7 筆逐字對照 PRD 初始研究來源表；`check` 對兩者皆 PASS |
| V7 | SOP 與流程型 AC | QA 逐項對照 PRD AC-SI-07-2、09-1、10-2、11-2、30-4 ①②、31-5 與 SOP 條文語意（不只關鍵字在）；Developer 與 QA 的文字交卷 | SOP 條文語意與 PRD 一致；Developer 棒與 QA 棒的交卷都含「流程摩擦」節，節內項目於 SCG-4 前已由主控入帳為 OBS 列，且 V2 仍為綠 |
| V8 | P1 出口 (a)(f) 與 `friction_reconcile` 真實檢核（主控執行；非構造） | (a) 對真實觀察走完 `run-open`、`attr`、`prop-new`、`card`，貼 `card` 輸出與 `git status --porcelain`；(f) 派一次體檢子代理，貼其交卷與入帳列（附 sid 與 OBS 座標）；另在真逐字稿環境跑 `status --json` 看 `friction_reconcile` | (a) 至少一筆屬 M／P／R／D 類（PROP-SI-001、002 屬轉交，不能充當）；(b) 正式面逐字相同；(f) 入帳 ≥1 列，零候選＝無事件而 (f) 不達、不得以構造候選充當；`friction_reconcile` 為 NOT-EVALUABLE（P1：measured 分支屬 P2；真逐字稿環境下 `reason` 為 `transcript-parser-not-established`、目錄取不到時為 `transcript-unavailable`；不得印成 0 或 measured） |
| V9 | 提案不觸及正式面 | 對 V8 的每筆 PROP：`git status --porcelain` 與 HEAD 前後對照 | 只多事件帳本與 `SelfImproving_Proposals/` 下的檔；正式面零變更 |
| V10 | 首跑研究掃描（主控；掌舵者授權外聯後） | `python tools/selfimproving.py research --fetch --run <運轉>`（讀 rc 先存變數）；貼輸出 | 有成功來源則 rc 為 0 或 2 且事件已寫；失敗來源以 OBS 候選回報，來源失效經 T1 修表；不列為 AT（外網） |
| V11 | 效能與 CI 時間 | 真 repo 上 `check` 三次取最大；新測試檔在 CI 上的單檔時間 | 真 repo `check` 小於 30 秒；每個新測試檔小於 300 秒（NFR-P1-2） |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

### 勘誤一（SCG-4 一審 FAIL 後的規格訂正；既有 AT 的 id 與判定碼名稱一字未改、一個 AT 也未刪）

- **事由**：SCG-4 一審（報告 `docs/06_quality/SCG4-REVIEW-SelfImproving-P1-20261020.md`；判定 FAIL，P1／P2／P3／P4＝0／8／6／8）的 §F 五項 TCS 內部不一致裁定、§G 的 F-01～F-22 與 §K 的八項勘誤建議。本次由 SA 棒套用；實作面的修復（F-01、F-02、F-12、F-18、F-21、F-22 的碼修）由 Developer 修復棒依本檔進行。
- **文字訂正（採納實作，條文對齊）**：
  1. **判定碼層級**（§K 1、2；F-18）：`QUOTE-VERIFIER-NOT-ESTABLISHED` 是 `PASS` 項目上的 warn 層級 finding、不是 NE 碼——R36 (d)（nonblocking NE 碼集合由三個縮為兩個）、R38 末句、R42 (d)、判定碼表（`events.transitions` 列改 `PASS（warn finding；項目狀態不變）`，`events.research` 列拆成兩列）、§4〈刻意不做〉、FRD-lite 的 AC-108-4 列、§1 的 AC-108-4 三列與兩個 AT 描述列、`AT-108-4-1` 情境一至四（`SC-LEGAL` 含 `dec`，故情境一的 `F(events.transitions)` 恰為該提示、情境二至四先去掉它再判）、`AT-108-4-E-2`、`AT-130-1-E-1` 情境四、`AT-103-2-1` 註記、§7.1 ⚖ 3。
  2. **R45**（§K 3）：先剝除符合 P0 R16 第八形態的反引號指令片段，再取 `path`／`file`／`dir` 三形態（否則每個草稿列都觸發復發候選提示）。
  3. **R58 (c)**（§K 4；F-03）：scheme 不得改變（`http`↔`https` 皆拒）；`AT-130-2-E-3` 的函式層案例改為顯式同埠 URL 並加反向與同 scheme 同埠對照（原案例因預設埠遮住 scheme 判準，使該判準沒有任何測試鎖住）。
  4. **鍵 B 指令**（§K 5）：九個鍵 B 判定指令、NFR-P1-10 (1) 與 V4 加 `-n 0`，§2 前言新增〈判定指令的形態〉。PRD 的 ADR-SI-07 漏列 `_TREE_FILE_FLOORS` 屬凍結的 PRD 文字，本檔 NFR-P1-8 已列名、不改，留 PRD 下次修訂。
  5. **`friction_reconcile`**（§K 6；F-11）：R60 (c) 補第三種原因 `transcript-parser-not-established`，P1 恆為 NOT-EVALUABLE；V8、§7.1 ⚖ 23、§4〈刻意不做〉同步。
  6. **R56 (a)**（§K 7；F-10）：`M` 類無 base 快照，觸及比例印 `n/a`，並補正控 `AT-114-1-2`。
  7. **NFR-P1-10 (11)～(13)**（F-15；OBS-SI-160、OBS-SI-161、OBS-SI-164）：新增 `tools/tests/` 檔會撞的根層鎖逐項過；測試 class 與夾具 def 的 docstring 指名受測模組；`--print-guard-lines` 的所在。
- **補條文（對應新增 AT，條文與 AT 同步）**：R37 讀取側防禦（F-02；折疊只納入通過單事件判準的事件）；R58 (d) 牆鐘強制點在每一次讀取（F-01）；R51 (b) 與 R49 (b) 的 `git apply --numstat` 失敗 ⇒ `PATCH-PARSE`（F-12）；R32 (c) 鎖內讀 OBS 帳本（F-21）；R29 可寫性探測檔名（F-08 (f)）；R62 (d) 片段判準（F-22）；R28 (d) 的 `k` 定義（F-08 (d)）；R42 (c) 等號放行（F-05）；R59 (b) 嚴格晚於（F-07）；R61 `truncated` 邊界（F-07）。
- **資料規格**：§5.2 新增情境 `SC-WEIRD`、`SC-SUSP-MIX`、`SC-STATUS-WIN`、`SC-SCAN-EDGE`；§5.4 的 `serve` 路由新增選項 `drip`、`stall`。§7.1 新增 ⚖ 26～⚖ 29；§7.2 登記一審的處置。
- **新增 22 個 AT（AC 總數仍為 54；括號內為所屬 AC、測試檔縮寫、`-k` 底線形）**：
  - `AT-103-1-E-2`（AC-103-1；ES；`-k AT_103_1_E_2`）：SUSPENDED 的連續判準：兩窗只有一壞不暫停、連續兩壞才暫停、`pending` 窗不打斷連續
  - `AT-103-1-E-3`（AC-103-1；ES；`-k AT_103_1_E_3`）：`pending_props` 含 `verified`；偵測窗以最近 `run.close` 為界、已處理者不重複偵測；`friction_reconcile` 兩種 NOT-EVALUABLE 原因
  - `AT-107-3-E-4`（AC-107-3；PR；`-k AT_107_3_E_4`）：`git apply --numstat` 自身失敗（損毀 hunk、context-diff）⇒ 拒收 `PATCH-PARSE`，不放行
  - `AT-108-4-E-3`（AC-108-4；EV；`-k AT_108_4_E_3`）：型別怪異的手寫事件（欄位值為陣列）恰報 `EVENT-TYPE`，`check` 其餘項目照常產出、不拋例外
  - `AT-108-4-E-4`（AC-108-4；EV；`-k AT_108_4_E_4`）：事件欄位值域的 check 層負控：`note` 120／121、`http_status` 199～300、`research.skip` 的 `by`、`sid` 正規形、事件行位元組 L 與 L－1
  - `AT-108-4-E-5`（AC-108-4；EV；`-k AT_108_4_E_5`）：引言回查未建的 warn 提示邊界：單一 `dec`、單一 `helmsman` 免掃即印，零筆不印；warn 不改狀態與 rc
  - `AT-114-1-2`（AC-114-1；PR；`-k AT_114_1_2`）：`M` 類卡面（正控）：七行、觸及比例印 `n/a`、核心區不超限；`--json` 的 `parsed` 與文字形態一致
  - `AT-128-2-E-2`（AC-128-2；KB；`-k AT_128_2_E_2`）：判準常數 `REWRITE_FRAGMENTS` 的獨立釘選：與 R66 的四個片段相等，改任一元素即紅
  - `AT-130-2-E-4`（AC-130-2；RS；`-k AT_130_2_E_4`）：來源表提交時間與事件 `t` 同一秒放行、事件早一秒判 `SOURCES-SHA-MISMATCH`、晚一秒放行
  - `AT-130-3-E-4`（AC-130-3；RS；`-k AT_130_3_E_4`）：全部來源失敗與現役為 0 筆皆以 `ZERO-SUCCESS` 拒收（rc 1、不寫事件；零現役時預檢零請求）
  - `AT-130-3-E-5`（AC-130-3；RS；`-k AT_130_3_E_5`）：Content-Type 白名單逐一釘住：`text/*` 與五個 `application/*` 放行，其餘判 `non-text`
  - `AT-130-5-E-2`（AC-130-5；RS；`-k AT_130_5_E_2`）：牆鐘上限對慢滴回應成立（每 0.5 秒 1 位元組）、送完標頭後停滯亦在逾時上限附近以 `timeout` 返回
  - `AT-131-2-E-3`（AC-131-2；RS；`-k AT_131_2_E_3`）：`scan` 起算時刻的 commit 時間邊界：committer 時間等於起算時刻者不計入窗、晚一秒者計入
  - `AT-132-5-E-3`（AC-132-5；ES；`-k AT_132_5_E_3`）：`truncated` 的邊界：筆數恰等於 `--limit` 不截斷、多一筆才截斷
  - `AT-134-3-E-2`（AC-134-3；LY；`-k AT_134_3_E_2`）：套件登記以程式碼欄的反引號片段為準：片段之外的散文字串不算登記
  - `AT-140-1-E-2`（AC-140-1；EV；`-k AT_140_1_E_2`）：帳本含型別怪異事件時，讀取與寫入動詞不拋未捕捉例外，rc 與輸出依既有規則；怪異事件不被折疊
  - `AT-140-1-E-3`（AC-140-1；EV；`-k AT_140_1_E_3`）：OBS 草稿列的症狀至多顯示 5 個碼，超過尾接 `…等 k 項`；恰好 5 個不加尾綴
  - `AT-140-2-E-2`（AC-140-2；ES；`-k AT_140_2_E_2`）：含中文的 `--json` 輸出為 UTF-8 原字、沒有 u 跳脫序列（`PYTHONIOENCODING=cp950` 管線下亦然）
  - `AT-141-1-E-2`（AC-141-1；EV；`-k AT_141_1_E_2`）：PROP 配號的 OBS 帳本部分在寫入鎖內讀取：取鎖之前才出現的 PROP 引用不被漏算
  - `AT-141-2-E-2`（AC-141-2；EV；`-k AT_141_2_E_2`）：鎖檔名為事件帳本 realpath 的 sha256 前 16 位 hex 加 `.lock`；持鎖期間存在、寫入完成後已釋放
  - `AT-141-2-E-3`（AC-141-2；EV；`-k AT_141_2_E_3`）：家目錄與其 locks、research 皆存在但寫不進（可寫性探測失敗）⇒ 寫入動詞 rc 3 `HOME-UNWRITABLE`
  - `AT-145-2-E-2`（AC-145-2；EV；`-k AT_145_2_E_2`）：SOP 判準常數的獨立釘選：`SAME_LINE_GROUPS` 與 `RESEARCH_EVENT_LINES` 和 R65 相等，改任一元素即紅
- **數量**：AT 由 126 條增為 148 條（正控 57→58、負控 69→90）；各測試檔：EV 35→44、PR 36→38、RS 28→33、ES 7→11、CP 3、LY 8→9、KB 9→10。
- **本檔未改的一審發現**：F-13（SSOT §3 列與第 72 行）、F-19（OBS 訂正列）、F-20（compat-ci 註解）屬主控自修項；F-16（近等價突變）與 F-17（URL 字串過濾的理論洞）為 P4 登記項（無暴露證據）。
- **凍結紀錄**：Stage-2 原凍結 digest `sha256:d7555681d94c143b71d8a35050a08b4da99eaefa8ed7f3e1f400b54e1f32c92c` 保留為歷史；本次訂正使檔案內容改變，修訂後的 digest 由主控以 `spec-refreeze` 重記（FSM `SPEC_AUDIT` 路徑），不以手改狀態檔代替。增量追溯表的 PRD 與研究方法 SOP 凍結摘要未動（兩份上位文件本次皆未改）。

