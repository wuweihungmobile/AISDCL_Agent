# SCG-4 PR Review 報告 — SelfImproving P0（觀察帳本定稿、一次性遷移、`check` 與協定目錄）

**審查日期**: 2026-10-19（本機 15:49 +08:00 起算）　**審查者**: SCG-4 獨立 QA 棒（Sonnet 5.5；未參與 TCS 撰寫與 P0 實作；規格作者＝SA 棒，實作者＝Developer 棒〔D3～D6〕加主控〔D1、D2 帳本編修與護欄層重釘〕，三方不同）
**FSM 功能鍵**: `monorepo-si-p0-ledger`（PR_REVIEW／SCG-4）
**基準規格**: `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`（Stage-2 凍結 digest `sha256:6c4e28ed30ab3e05ea1acbbf4b8d1a5a5004f5a2aed3fb535abb59cfb420de56`，當回合重算相符）；上游 `docs/01_requirements/SelfImproving_PRD.md`（`sha256:9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e`，重算相符）
**姊妹檔**: `docs/06_quality/RTM-SelfImproving-P0-20261019.md`（FR／AC → AT → 測試方法 → 本次結果 → 證據座標）
**判定**: **FAIL**（P1＝0、P2＝2、P3＝3、P4＝9）。V1、V2、V4、V5、V6、V7、V9 通過；**V3 的 (9)「座標可重查」未通過（F-02）、V8「SOP 條文語意對照 PRD」未通過（F-01）**。兩個 P2 的補救成本都低（改一段 SOP 文字、追加一列更正列），補救後須由 QA 複驗 V3 (9) 與 V8。
**現行判定（主控 2026-10-19 補註）**: 上列為一審原文、保留為歷史；修復（Y2 `9fd15796`～Y5 `622c83d2`）後二審複驗 **PASS**（P1／P2／P3＝0，P4 殘餘不阻斷），逐字證據與各 F 結案表見 §8。FSM：`gate --gate PR_REVIEW --result PASS` 於二審後由主控執行。其後掌舵者裁決程式碼搬成套件 `tools/lib/selfimproving/`（commit `e83ebb14`），三審（搬遷複驗）**PASS**，見 §9；F-16～F-21 的處置入帳 OBS-SI-106 起。

> 方法聲明：本報告凡寫「通過」者，皆附當回合真跑的指令與輸出；做不到的寫「未驗」（見 §7）。稽核腳本全部放在 scratchpad `C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\f3ead132-29b1-418c-97d9-35868ab11c70\scratchpad\qa_scg4\`，不入庫；repo 內除本檔與姊妹檔外零改動（見 V7）。Windows 上只用 PowerShell／Read／Grep／Glob／Edit／Write（Bash 被 hook 擋，也不用），Python 一律 `D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe`。工具輸出若帶表情符號，下文逐字引用時略去行首符號。

---

## §1 輸入快照與 digest 核對

| 項目 | 值 | 核對 |
|------|----|------|
| HEAD | `56ef5393ccd41e868b8bf9fd4d8fbd946527b0a0`（＝X） | `git rev-parse HEAD` 相符；`git status --short` 為空（工作樹乾淨） |
| T | `13e87b749721cae25a6782005df73587c73baf21`（Developer D3～D6 加主控收尾） | 在 `git log --first-parent` 上 |
| M | `ab4638c439ad1cc4b8408efcd454c29ef7966d0b`（帳本一次性遷移） | 同上 |
| N | `f1d7660f16ac8afb15ccdaa582a8ef4a7f6caf04`（`migration_base_sha`＋確認列） | 同上 |
| X | `56ef5393ccd41e868b8bf9fd4d8fbd946527b0a0`（流程摩擦入帳列） | 同上 |
| 環境 | Windows 11 專業版 10.0.26300；pwsh 7；Python 3.11.9（`.venv`）；pytest 9.1.1；ruff 0.15.21；git 2.51.0.windows.1 | 當回合現查 |

```text
> Get-FileHash -Algorithm SHA256 <TCS>      Hash : 6C4E28ED30AB3E05EA1ACBBF4B8D1A5A5004F5A2AED3FB535ABB59CFB420DE56
> Get-FileHash -Algorithm SHA256 <PRD>      Hash : 9C5718274EB511CC071DEB1193AE7EADAAFFC3B636826ACF8E7935A50754460E
> HEAD=56ef5393ccd41e868b8bf9fd4d8fbd946527b0a0   （git status --short 的行數＝0）
```

研究方法 SOP 的 digest（V7 現算）：`deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2`，與 TCS 增量追溯表所列相符。

提交順序（`git log --first-parent --format='%h parent=%p' -n 8`）：

```text
56ef5393 parent=f1d7660f      <- X
f1d7660f parent=ab4638c4      <- N
ab4638c4 parent=13e87b74      <- M
13e87b74 parent=eaed744b      <- T
eaed744b parent=96bbd73a
96bbd73a parent=407c945b
407c945b parent=7b9c6ba6
7b9c6ba6 parent=64f2fc0f
```

---

## §2 實跑檢核 V1～V9

### V1 提交鏈 — 通過

```text
> git log --format="%H %s" -- docs/06_quality/SelfImproving_Observation_Ledger.md        （subject 很長，下列只取前段；rc=0）
56ef5393ccd41e868b8bf9fd4d8fbd946527b0a0 docs(selfimproving): P0 流程摩擦入帳（SCG-4 前，V8 要求）——帳本追加 …   <- X
f1d7660f16ac8afb15ccdaa582a8ef4a7f6caf04 docs(selfimproving): P0 D2 遷移豁免（N；只動 params.json 與帳本追加一列）——…   <- N
ab4638c439ad1cc4b8408efcd454c29ef7966d0b docs(selfimproving): P0 D1 觀察帳本一次性遷移（M；單一 commit，只動帳本與附註檔）——…   <- M
96bbd73a8531b871dad7d3c4b2b6a7a1edaf8ebd docs(selfimproving): P0 TCS 二審 PASS（QA：…
407c945b07aceeddcd85d4d073a2d59a87c79175 docs(selfimproving): P0 TCS 修訂（SA：…
7b9c6ba66ab6e622bc4b0c7054998e77be1e7950 … 64f2fc0f… ad677719… 978df84c… 31824e56… c0716f16… 6c23495d… 0bf83bad… b78effb4…（遷移前的 9 個歷史 commit）

> git show --name-only --format= ab4638c4…   （M）    rc=0
docs/05_development/SelfImproving_Observation_Ledger_notes.md
docs/06_quality/SelfImproving_Observation_Ledger.md

> git show --name-only --format= f1d7660f…   （N）    rc=0
docs/06_quality/SelfImproving_Observation_Ledger.md
docs/06_quality/SelfImproving_Protocol/params.json

> git show --name-only --format= 56ef5393…   （X）    rc=0
docs/06_quality/SelfImproving_Observation_Ledger.md

> git diff --stat M N        rc=0
 docs/06_quality/SelfImproving_Observation_Ledger.md | 1 +
 docs/06_quality/SelfImproving_Protocol/params.json  | 2 +-
 2 files changed, 2 insertions(+), 1 deletion(-)
> git diff --unified=0 M N -- params.json   ->  -  "migration_base_sha": null,
                                                +  "migration_base_sha": "ab4638c439ad1cc4b8408efcd454c29ef7966d0b",
```

判斷：T 早於 M 早於 N（`T..HEAD` 順序為 13e87b74、ab4638c4、f1d7660f、56ef5393）；M 是單一 commit 且只動帳本與附註檔；N 只動 `params.json`（恰一個鍵）與帳本（追加一列）；M 與 N 是兩個 commit。T 本身不動帳本（不在上列帳本歷史內），符合「Developer 棒不得碰真帳本」。

### V2 真帳本 `check` — 通過

```text
> python tools/selfimproving.py check --json      （真 repo，HEAD＝X；rc=0；wall=1.05s；stdout 2358 位元組；stderr 0 位元組）
{"overall": "PASS", "rc": 0, "fingerprint": "sha256:87b349b706f38fce6e99255c2a50ddc4f49ea7ba3c283f52451fff18e3bab394", "fingerprint_parts": {"manifest": "48fe99e7a1c9c890ba1618dc6c1a38d2c917063bdb535e94474493a190df69a2", "metrics_rev": 1, "check_rules_rev": 1}, "rows": 62, "items": [{"id": "ledger.structure", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ledger.time_tz", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.required", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.enums", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.markers", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.provenance", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.coordinates", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.bytes", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.control_chars", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "row.fixed_sha", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ref.def", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ref.obs", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ref.orig_notes", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ref.carrier_families", "status": "NE", "blocking": false, "detail": "", "findings": [{"subject": "-", "code": "CARRIER-NOT-ESTABLISHED", "level": "info", "detail": "families=PROP-SI count=24"}]}, {"id": "history.migration", "status": "PASS", "blocking": false, "detail": "claim=valid", "findings": []}, {"id": "history.row_mutated", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "params.keys", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "params.globs", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "params.coupling", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ledger.volume", "status": "PASS", "blocking": false, "detail": "", "findings": []}, {"id": "ledger.vacuity", "status": "PASS", "blocking": false, "detail": "", "findings": []}], "obs_draft": null}
```

文字形態（`check`，rc=0，611 位元組）：

```text
si-check rows=62 items=21
PASS ledger.structure
PASS ledger.time_tz
PASS row.required
PASS row.enums
PASS row.markers
PASS row.provenance
PASS row.coordinates
PASS row.bytes
PASS row.control_chars
PASS row.fixed_sha
PASS ref.def
PASS ref.obs
PASS ref.orig_notes
NE ref.carrier_families nonblocking
  - CARRIER-NOT-ESTABLISHED families=PROP-SI count=24
PASS history.migration # claim=valid
PASS history.row_mutated
PASS params.keys
PASS params.globs
PASS params.coupling
PASS ledger.volume
PASS ledger.vacuity
overall=PASS rc=0 fingerprint=sha256:87b349b706f38fce6e99255c2a50ddc4f49ea7ba3c283f52451fff18e3bab394
```

判斷：rc 0；21 項依碼表順序齊備；除 `ref.carrier_families`（nonblocking NE，TCS Q1 已預告）外皆 PASS；`row.coordinates`、`row.enums` PASS（零無座標列、零「之後再看」於處置欄）；`ref.obs` PASS。

**獨立重判（不信任 `check` 的 PASS）**：`qa_scg4\v2_independent.py` 依 TCS R9～R16 自行實作逐列判準（不 import `tools/lib/si_*.py`），對 HEAD 帳本 62 列、27 個判定碼的結果全為 0 命中（`HEADER-COLS`、`ROW-ARITY`、`ROW-ID-FORMAT`、`ROW-ID-DUP`、`ROW-ID-ORDER`、`TZ-HEADER-MALFORMED`、`TIME-FORMAT`、`TIME-NO-TZ`、`FIELD-EMPTY`、`ENUM-CATEGORY`、`ENUM-SEVERITY`、`DISP-ENUM`、`DISP-TEXT-MISSING`、`DISP-DEFER-LATER`、`MARK-SYNTAX`、`MARK-UNKNOWN-KEY`、`MARK-VALUE`、`MARK-ORIG-FORMAT`、`MARK-FACE-MISSING`、`GUARD-NO-EXPOSURE`、`GUARD-P12-NO-EXPOSURE`、`SOURCE-MISSING`、`SOURCE-VALUE`、`REPORTER-MISSING`、`COORD-NONE`、`ROW-BYTES-OVER`、`CTRL-CHAR`）；列位元組最大 689（第 049 列）、無列超過 700；檔案 35838 位元組、無 BOM、無 CR。兩套實作結論一致。

### V3 M 稽核（唯讀；`M^` 對 `M`）— **未通過（僅 (9)）**

稽核腳本：`qa_scg4\v3_audit.py`（逐列比對 (1)～(7)、輸出 (8)(9) 的審視材料）、`v3_fixed_sha.py`（回填的 sha 語意核對）、`v3_coord_exist.py`（路徑型座標存在性與行號界限）、`v3_sid_lines.py`／`v3_queue_ops.py`／`v3_queue_kw.py`（`sid`＋`line` 座標回查）。下列 V3、V5 的輸出為腳本輸出的節錄（合併同節相鄰的短行、省略空行與頂層鍵清單；完整原文見 `v3_audit.txt`、`v5_transcript.txt`）。

```text
## (1) ID 集合與順序不變、無增減列
old rows=50 new rows=50    ID 序列相等=True    added=[] removed=[]    連號 001..050 且無重複=True
## (2) 時間、情境、症狀、分類、嚴重度逐格相同
差異格數=0
## (3) 證據座標：逐格相同，或僅為前綴保留的追加
逐格相同=47 前綴保留追加=3 其他(違反)=0
  PREFIX-APPEND OBS-SI-019: 追加尾段='；docs/06_quality/SelfImproving_Observation_Ledger.md'
  PREFIX-APPEND OBS-SI-029: 追加尾段='；sid f3ead132-29b1-418c-97d9-35868ab11c70 line 1386（SD 交卷原文）'
  PREFIX-APPEND OBS-SI-034: 追加尾段='；docs/01_requirements/SelfImproving_PRD.md'
## (4) 處置被改寫的列都有 orig 且與 M^ 處置原文逐字相同；未改寫者無 orig
處置被改寫列數=50 其中 inline orig=47 anchor orig=3；處置未改寫列數=0 -> []
違反數=0    含 orig 的列數=50
## (5) 九欄與檔頭 tz 宣告齊備
arity histogram new={9: 50}    表頭行數=1; 欄名=['ID','時間','情境','症狀','證據座標','分類','嚴重度','處置','標記']; 與九欄定稿相符=True
檔頭 tz 宣告行數=1 -> [(7, '<!-- si-ledger: tz=+08:00 -->')]    宣告內容='tz=+08:00' 含 tz=<offset> 合法=True
## (6) 每個 @ 錨點在附註檔有同 ID 的段落
  OBS-SI-027 / OBS-SI-043 / OBS-SI-050: 段落存在=True 路徑即附註檔=True
## (7) 沒有「之後再看」
  M^: 命中行數=1（第 6 行，檔頭〈規則〉的禁令敘述「處置欄不得留「之後再看」」）   M: 命中行數=1（同一行）   M notes: 0
  M 的處置欄命中列=[]
```

判斷：

- (1)～(7) 全數成立。(4) 的「處置未改寫的列沒有 orig」在本次遷移中為空真（50 列處置全部被改寫為枚舉首詞，故 50 列皆帶 `orig`）；附註檔 3 段（027、043、050）與 `M^` 處置原文逐字相同。
- (8) 回填語意（**全 50 列逐列審視，非抽樣**）：
  - 處置分佈 decided 34／fixed@ 8／deferred 5／open 3，與 M 的 commit message 一致。
  - `fixed@` 8 列的 sha 以 `git log -S`（舊處置原文首次出現的 commit）加 `git show -s --format=%s` 核對：009→738f4f60（CLAUDE.md 目錄樹補 `REVISE_EVALUATOR`）、014→4e626a4d（nightly perf baseline 重鎖 chore）、020→0bf83bad、023→69a644e6（CLAUDE.md 第 191 行座標 239→277）、031→6c23495d、035→c0716f16、041→ad677719、043→7b9c6ba6；其中 020、031、035、041 四列（原寫「fixed（本 commit…）」）與 043（原寫「fixed：…」）共五列，舊處置原文首次出現的 commit 恰等於回填的 sha，且該 commit 對帳本的 diff 含該列。全數吻合，無編造 sha。
  - 面／來源／暴露：面＝文件 22／流程 14／產品 9／守衛 5；來源＝代理 49／逐字稿 1（043）；守衛 5 列（002、005、017、036、050）的暴露＝002 無、005 b、017 無、036 b、050 b，與開放問題 Q3 的規則一致（座標有檔加行者填 b，017 的原處置明寫「無暴露證據不立案」故維持無）；全帳本無 P1／P2 列，故無守衛面 P1／P2 的暴露規則違反風險。
  - 備註（P4，F-14）：010、022、024、042、049 五列原處置同時含裁決與再開症狀子句，改寫為 `decided：…` 後再開症狀只存在 `orig`；`decided` 不要求再開症狀（PRD:218），資訊未遺失，但現行處置欄不再自帶；34 列 `decided` 皆未寫裁決者（PRD:218「附裁決者與一句裁決」；TCS §7.2 的預審登記項 F-12 已登記為 P4）。
- (9) 座標可重查抽查：**實查範圍＝只靠放寬形態過關的全部 21 列**（TCS 所列 12 列：docref 7、無行號 file 3、無行號 path 2，我的獨立分類結果與其逐列相符；另加路徑加目錄形態的 9 列），遠多於「≥5 列」的下限，並對 50 列的路徑型座標做存在性與行號界限檢查、對 13 組 `sid`＋`line` 座標回查逐字稿。

```text
> 路徑型座標存在性（qa_scg4\v3_coord_exist.py）：所有 path:line 皆在檔案行數界限內；找不到者 3 筆
   OBS-SI-030  MEMORY.md                                  -> MISSING（使用者本機記憶檔，不在 repo）
   OBS-SI-037  qa_brief.md                                 -> MISSING（scratchpad，列內自述「收輪即刪」）
   OBS-SI-047  AutoClaude/autoclaude/execution/sdd_to_playbook_adapter.py -> MISSING
> git log --oneline --all -- AutoClaude/autoclaude/execution/sdd_to_playbook_adapter.py   ->  (no history: path never existed)
> 實檔位置（Glob）：AutoClaude\autoclaude\infra\adapters\sdd_to_playbook_adapter.py
> sid＋line 回查（13 組）：004／013／027／032／033／038／039 指向 type=queue-operation 且 operation=enqueue 的記錄，其頂層 content 為子代理交卷
  （關鍵字回查全數命中，例：013 命中 10-19／跨午夜／今天；038 命中 Omitted／548；039 命中 補丁／patch／Omitted）；
  029 指向 type=user、origin=peer 的 SD 交卷；037 指向 assistant 的 Agent 派工 tool_use；040 指向 assistant 的 SendMessage tool_use；
  042 指向 assistant 的 PowerShell tool_use（即已被更正列 043 訂正的舊座標 2536）；051 的兩行見 V5。
```

21 列逐列結果：

| 列 | 弱形態 | 座標（縮） | 重查結果 | 判定 |
|----|--------|-----------|----------|------|
| 001 | path＋dir | `docs/01_requirements/Agent_ConsoleUI_PRD.md`、`AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` | 兩檔皆在 `docs/01_requirements/` | 通過 |
| 003 | path＋dir | `AISDLC_SDD/scripts/sdd_env.py` 參數面 | 檔在；argparse 只有 `--sub`／`--slug`／`--shell`／`--root`／`--check`，無狀態目錄覆寫，與症狀一致 | 通過 |
| 006 | docref | `SOP II-2 呼叫 #3～#5` | 研究方法 SOP II-2 表 #3～#5（`:149–151`）存在，內容為分號串接多題的 WebSearch | 通過 |
| 007 | path 無行號 | `autoclaude/evolution/*.py`、`autoclaude/plugins/translation_learner*` | 兩 glob 在 `AutoClaude/` 下有實檔；**當場複現症狀**：帶目錄前綴的 pattern 回 No files found，path 指到目錄後 `translation_learner*` 列得出 `translation_learner_plugin.py` | 通過 |
| 008 | docref | `SOP II-2 #7～#9、#20、#22、#31、#34` | 各 # 皆存在（`:153–155、:166、:168、:177、:180`）且內容對應（arXiv 分段、官方頁整頁、PDF FlateDecode） | 通過 |
| 011 | file 無行號 | 系統提示 MCP Server Instructions vs 根 `CLAUDE.md`〈鐵律一〉 | 根 `CLAUDE.md`〈鐵律一〉在；本次 QA 的 context 即再現該衝突（見 §6） | 通過 |
| 012 | file 無行號 | 根 `CLAUDE.md`〈12-Rule Template〉Rule 6 | 在 | 通過 |
| 016 | path 無行號 | `~/.claude/projects/<slug>/memory/MEMORY.md`（本機，不在 repo） | 檔在本機記憶目錄（`<slug>` 可由專案路徑推得）；repo 外 | 通過（弱） |
| 019 | path＋dir | 本檔時間欄；`docs/06_quality/SelfImproving_Observation_Ledger.md` | 在 | 通過 |
| 020 | docref | `SOP II-7 T-1（:319）` | II-7 T-1 在（SOP `:340`），但 `:319` 現為候選 CD 表的 CD-03 列——行號隨 SOP 一審後修訂而過期 | 通過（P4：行號過期，F-02 軟項） |
| 030 | file 無行號 | `MEMORY.md` 三節起點 10／10,299／12,776 | 檔在 repo 外；該檔已依處置欄所述重排，現為 265／3048／5525，**原量測值不可重現** | 弱（P4，F-02 軟項） |
| 034 | path＋dir | `PRD 行數；docs/01_requirements/SelfImproving_PRD.md` | 在（現 1020 行；列所述 952 為當時量測） | 通過 |
| 035 | path＋dir | `docs/06_quality/SCG0-REVIEW-SelfImproving-20261019.md F-15～F-17` | 檔在；F-15、F-16、F-17 皆在（`:149–150`、`:183–185`） | 通過 |
| 041 | docref | `QA 報告 §6.3 F-35；本檔 036～039 列` | SCG0 報告 §6.3（`:310`）內有 F-35（`:322`）；036～039 列在 | 通過 |
| 043 | docref | `主控 JSON 解析親驗（type／origin.kind）；SA P0 交卷 §5` | 無 repo 內載體；SA 交卷在主控逐字稿（`type=user` 的 agent-message，約 line 2959、3272），未標 `sid`＋`line`；列所述 2493／2536 為 assistant 空記錄、2476／2525／2581 為 human，已由 V5 重現 | 弱（P4，F-02 軟項） |
| 044 | path＋dir＋docref | ADR-XPLAT-016 §8.1；TCS FRD-lite 對映表；SA 回報 | ADR 檔在、§8.1 在 `:386`；TCS 有 FRD-lite 對映表 | 通過 |
| 045 | path＋dir | `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md` | 在 | 通過 |
| 046 | path＋dir | QA 第三棒回報；`TCS-PREREVIEW-…md` 流程摩擦 #3 | 預審報告 §5（`:85`）的 (3) 即 Glob 大括號假陰性 | 通過 |
| **047** | path＋dir | QA 第三棒回報 #4；`AutoClaude/autoclaude/execution/sdd_to_playbook_adapter.py` | **路徑不存在，git 歷史上也從未存在**；實檔在 `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py`；列內「QA 第三棒回報 #4」對應預審報告 §5 的 (4)，但該列沒有引用該報告檔 | **不通過** |
| 048 | docref | `TCS §7 Q3（修訂版）；QA 預審報告；SA 回報 §六` | TCS §7.1 Q3 在且內容吻合（草稿估算把舊處置重複計入，已更正） | 通過 |
| 049 | docref | `TCS §7 Q6；PRD:208；SA 回報 §五` | Q6 在；PRD `:208` 為證據座標欄 | 通過 |

判斷：TCS V3 (9) 明文「任一列點不到 ⇒ V3 不通過，退回主控補救」。第 047 列的檔案路徑點不到（F-02，P2），故 **V3 不通過**；補救＝追加一列更正列（`rel=corrects:OBS-SI-047`，座標改為真路徑），帳本於 M 之後只准追加，不可原地改。第 020、030、043 為軟性問題（行號過期、量測值失效、無持久載體），建議同批以更正列補強但不單獨構成不通過。

### V4 `migration_base_sha` — 通過

```text
> git rev-parse ab4638c439ad1cc4b8408efcd454c29ef7966d0b      ab4638c439ad1cc4b8408efcd454c29ef7966d0b   rc=0
> git rev-parse ab4638c4                                       ab4638c439ad1cc4b8408efcd454c29ef7966d0b   rc=0
> git merge-base --is-ancestor <M> HEAD                        rc=0      （rc 先存變數再印，未接管線）
> params.json 的 migration_base_sha 行                          "migration_base_sha": "ab4638c439ad1cc4b8408efcd454c29ef7966d0b",
```

判斷：值等於 M 的完整 40 位 sha；M 是 HEAD 的祖先（rc 0）。

### V5 確認列引言座標 — 通過

確認列為 OBS-SI-051（處置 `decided：掌舵者預先授權，主控代為確認遷移豁免`），整列文字所引的 `line` 恰兩個：2476、2581（`qa_scg4\v5_transcript.py`，以位元組 `split(b"\n")` 取第 N-1 段再 `json.loads`）。

```text
transcript bytes=21142485 (stat size=21142485) LF-split segments=4886 last_segment_empty=True
--- 實體行 2476 ---
  type='user' message.role='user' origin={'kind': 'human'} turnOrigin='human' userType='external'
  content 型別=str 文字長度=75
  文字='以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案(不用考量成本)，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策'
  引言與文字逐字相等=True；引言為子字串=True；引言長度=75 文字長度=75
--- 實體行 2581 ---
  type='user' message.role='user' origin={'kind': 'human'} turnOrigin='human' userType='external'
  content 型別=str 文字長度=15
  文字='了解，凍結後接著開 P0 實作'
  引言與文字逐字相等=True；引言為子字串=True；引言長度=15 文字長度=15
--- 參考行 2525（PRD 附錄 C.2 的預先核准句；非確認列所引）---
  type='user' message.role='user' origin={'kind': 'human'} 文字='真正需要你本人的只剩凍結核准 ==> 現在先授權核准! (避免不在機器旁)'
對照 line 2493: type='assistant' role='assistant' origin=None 文字='<tool_use:PowerShell>'
對照 line 2536: type='assistant' role='assistant' origin=None 文字='<tool_use:PowerShell>'
```

判斷：兩行皆 `type=user`＋`origin.kind=human`，文字與列內引言逐字相符；舊座標 2493／2536 確為 assistant 的空文字 tool_use 記錄，與更正列及 PRD 附錄 C.2 的訂正一致。觀察（P4，F-08）：兩句引言是一般性授權與「開 P0 實作」指令，不是針對遷移豁免的逐項確認；列的處置欄已誠實標示「預先授權、主控代為確認」，符合 TCS R19 (d)「只驗存在與格式」，但語意強度弱於 PRD AC-SI-01-3 (b) 字面的「掌舵者確認紀錄」。

### V6 `params.json` 初值 — 通過

```text
params.json bytes=1681 BOM=False CR=False 結尾換行=True    鍵數=23 依位元組序遞增=True
R21 初值逐鍵：20 個數值鍵（row_max_bytes=700、w_n=20、w_min=5、w_evt=2、w_opp=5、max_proposals_per_run=3、max_revisions=2、churn_max=2、
  min_heldout=5、max_touch_ratio=0.2、max_new_entries=3、stop_after_bad=2、cap_frac=0.9、max_archive_entries_per_card=50、card_line_max=100、
  event_max_bytes=2000、metrics_rev=1、min_obs_rows=10、ledger_warn_bytes=245760、ledger_fail_bytes=262144）全部 OK（值與型別皆與 TCS 表相同）
migration_base_sha: 'ab4638c439ad1cc4b8408efcd454c29ef7966d0b'（D2 前 null；N 之後＝M 的完整 sha）
spec_body_globs 相符=True    鍵集合恰為 R21 的 23 鍵：True（多出=[] 缺少=[]）    全部 20 個數值初值相符=True
## R22 non_evolvable_globs 現算
PRD 第一個含 **實體 glob** 的行 = PRD:415；來源一取得 18 項、重複=0；根 CLAUDE.md 第一個含 守衛面＝ 的行 = CLAUDE.md:81；來源二展開 7 項
必備集合合計 25 項；params 清單 25 項；重複項=0；集合相等=True；缺少=[]；多出=[]
AT-029-2 四個迴圈自身 glob 皆在清單內=True
```

PRD 座標逐項核對（`qa_scg4\v6_params.py`、`v6_prd_peek.py`）：W_N 20（PRD:61）、W_MIN 5（:61）、W_EVT 2（:38、:61）、W_OPP 5（:361）、MAX_PROPOSALS_PER_RUN 3（:290、:403）、MAX_REVISIONS 2（:403）、CHURN_MAX 2（:375）、MIN_HELDOUT 5（:345）、MAX_TOUCH_RATIO 0.2 與 MAX_NEW_ENTRIES 3（:286）、STOP_AFTER_BAD 2（:365）、CAP_FRAC 0.9（:379）、MAX_ARCHIVE_ENTRIES_PER_CARD 50（:286、:671）、CARD_LINE_MAX 100（:314）、`event_max_bytes` 2,000（:447）、ROW_MAX_BYTES 700（:212）、`spec_body_globs` 三個 glob（:697）、`ledger_fail_bytes` 對 Read 工具 256KB 實測（:447）與 `ledger_warn_bytes` 245760／`min_obs_rows` 10／`metrics_rev` 1 為 TCS Q4 自定值（PRD 未給值，PRD:566、:601 只點名）。25 項 glob 由規則現算與 `params.json` 逐項相等。

### V7 護欄與零退化 — 通過

```text
> $env:AUTOSDD_PARALLEL_TESTS='1'; python tools/run_root_unittests.py     rc=0   wall=138.02s   stdout 22475 位元組   stderr 344 位元組（wexpect 的 pkg_resources 警告，既有）
  unittest 數量下限釘選通過：發現 5426 個測試（下限 5326）
  收集面盤存：92 支 test_*.py 檔／指紋 ee42006abfd0
  [cpu_budget] root-unittest workers=18 source=cpu_budget
  模組耗時排行（前 5，共 405 模組，平行模式，worker=18）：…… test_selfimproving_check: 81.0s
  派工摘要：worker=18｜S=2035.9s｜ideal=max(S/W, 最長單位)=113.1s（S/W-bound）｜loss=1.00x｜slot 利用率=99.7%
  本次 skip 明細（共 46 支；全列，略）
  [skip census] tools/tests@win32 共 46 支：platform=42／tool-absence=0／env-disabled=4／structural-pair=0／debt=0／untagged=0／欠債型 4 支（目標 0）
  [M6 id 集合] tools/tests@win32：集合關係成立（本次 skip 46 支）
  真實 TEMP 圍籬：全套期間真實契約目錄下 autosdd_pace*.json 零變動（前 4／後 4 份）
  孤兒 console 普查：零增長（前 1／後 1）
> ruff check（9 個新 .py：tools/selfimproving.py、tools/lib/si_{check,git,history,ledger,params,refs,rows}.py、tools/tests/test_selfimproving_check.py）
  All checks passed!      ruff_rc=0
> python AutoClaude/tools/check_loc_budget.py --json      rc=0（wall 3.97s）
  total: 18625  baseline: 17079  cap: 20438  total_violation: False  absolute_violations=[]  tier_violations=[]  special_violations=[]  root_tools_violations=[]
  guard_taxonomy 內含 tools/selfimproving.py 與 7 個 tools/lib/si_*.py 共 8 筆
> python -m pytest tools/tests/test_defect_id_reference_integrity.py -q -p no:xdist -o addopts=       rc=0
  11 passed in 2.08s
> git diff --name-only          (empty)   rc=0
> git diff --stat -- .claude    (empty)   rc=0
> git diff --cached --name-only (empty)   rc=0
> git status --short            (clean)   rc=0
> Get-FileHash 凍結三檔：PRD 9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e／TCS 6c4e28ed30ab3e05ea1acbbf4b8d1a5a5004f5a2aed3fb535abb59cfb420de56／研究方法 SOP deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2
> git log eaed744b..HEAD -- <PRD、TCS、研究方法 SOP、.claude>      (none)
> Measure-Command { check --json } 三次（NFR-P0-2）：1.077s／1.044s／1.033s（rc 皆 0；最大 1.077s，門檻 < 30s）
```

判斷：全綠。通過數說明：根層 runner 不印「通過數」，只印「發現 5426 個測試（下限 5326）」「skip 46 支（皆已標籤）」與 rc＝0；本報告不自行推算通過數。`test_selfimproving_check` 單檔實跑 `42 passed, 86 subtests passed in 38.41s`（§3）。

T 提交（`git show --name-status --format= 13e87b74`）含 §5.6 以外的 8 個檔：`.github/workflows/{macos,windows}-compat-ci.yml`（各 +4 行 `paths:` 兩個條目）、`docs/04_planning/AutoSDD_improving_112.md` 與 `docs/06_quality/CrossPlatform_R145_Scan_Findings.md`（各 1 行 guard-total 數字同步）、`tools/lib/skip_tag_policy.py`（樹下限 72→73）、`tools/tests/test_platform_neutral_paths.py`（下限 75→89）、`tools/tests/test_adr_xplat001_c1c2_lock.py`（重釘）。逐一檢視 diff，皆為重釘與 CI paths 覆蓋鎖的連動、由主控收尾，符合 V7「只含 §5.6 的集合與主控收尾的重釘檔」的精神；記為 F-13（P4，TCS §5.6 文字未預留這兩類連動檔）與 F-10（重釘走一次性例外，屬治理裁決）。

**本報告與姊妹檔寫入後的複驗**（兩檔皆為未追蹤檔，`git status --short` 只多這兩行 `??`）：

```text
> python tools/selfimproving.py check      rc=0   wall=1.08s
  si-check rows=62 items=21 … PASS ref.obs … NE ref.carrier_families nonblocking … overall=PASS rc=0 fingerprint=sha256:87b349b706f38fce6e99255c2a50ddc4f49ea7ba3c283f52451fff18e3bab394
> $env:AUTOSDD_PARALLEL_TESTS='1'; python tools/run_root_unittests.py     rc=0   wall=137.69s
  unittest 數量下限釘選通過：發現 5426 個測試（下限 5326）；[skip census] tools/tests@win32 共 46 支（untagged=0）；真實 TEMP 圍籬、孤兒 console 普查皆通過
```

兩份報告內提到的觀察列編號全是帳本已存在的編號（grep 驗證：只有 001～062 範圍內的 ID），沒有可被 R18 (a) 抓成懸空的字面編號；`check` 的指紋不變（指紋只隨協定目錄內容變）。

### V8 SOP 與流程型 AC 的文件檢核 — **未通過**

逐項對照 PRD 與 SOP（`docs/05_development/SelfImproving_Operations_SOP.md`）：

| PRD AC | PRD 原意（座標） | SOP 條文（座標） | 語意判定 |
|--------|------------------|------------------|----------|
| AC-SI-02-1 | 內嵌指示來源標 `外部衍生=是`，不得單獨充當任何類別提案的證據，須另有 ≥1 個內部來源佐證（PRD:248） | 標 `外部衍生=是`；此類列不得單獨充當任何提案的證據（P1 的 `prop-new` 前置檢查，P0 以本條文代位）（SOP:50） | 一致；缺「須另有 ≥1 個內部來源」（F-11） |
| AC-SI-03-1 | 啟動事件僅五類：(a) 掌舵者指令；(b) 同一症狀第二次被記入觀察（經審查者確認相同）；(c) 缺陷帳本新立 P≤2 未結列；(d) 已採納工件的再開症狀命中；(e) 容量事件（FR-SI-27）。無日曆、版本號、覆蓋度、每 N 輪觸發；事件偵測 `si status` 唯讀按需（PRD:252） | (a) 掌舵者明示要求啟動或再開（T1）；(b) 同一症狀第二次出現：觀察帳本內同一症狀再現（再開症狀命中）；(c) **嚴重度 P≤2 的觀察入帳：一筆 P1 或 P2 的觀察被記下**；(d) **先前延後或退役的列，其再開症狀發生：處置欄寫明的再開症狀被觀察到**；(e) **額度或 context 的容量事件：守衛面回報額度或 context 水位事件**（SOP:11–15） | **不一致**（見 F-01） |
| AC-SI-03-2 | 零筆或零提案記為「無事件」而非「通過」（PRD:253） | 零事件記為「無事件」，不得寫成通過；觀察筆數低於 `min_obs_rows` 時 `check` 回 rc 2（SOP:21） | 一致 |
| AC-SI-03-3 | 產出數量不構成再開理由，再開僅依範本〈終止條件・休眠・再開〉的 T1～T4（PRD:254；該節標題前綴一個旗標符號，本報告一律略去） | 產出數量不構成再開理由；再開僅依範本該節的 T1～T4，由掌舵者裁決（SOP:23） | 一致；「由掌舵者裁決」把事件驅動的 T2～T4 一併說成裁決（F-11） |
| AC-SI-04-2 | 真缺陷處置須為 `DEF-<id>`（PRD:258） | 符合缺陷帳本收錄定義的真缺陷，處置須為 `DEF-<id>`（SOP:41） | 一致 |
| AC-SI-29-1 | 流程不當或 BUG 當下入帳，一句症狀加一個座標，真缺陷升 DEF，子代理以文字交卷的「流程摩擦」節為入口（PRD:390） | 子代理文字交卷、交卷必含該節；流程摩擦項目由主控當下入帳；真缺陷處置須為 `DEF-<id>`（SOP:37–41） | 一致 |
| AC-SI-29-2 | 對迴圈本身預算／閘門／停機條件／指標定義的改進標 `loop-self` 並轉交，僅經掌舵者 T1／PRD 修訂（PRD:391） | 同（SOP:25），並指出迴圈自身檔案列在 `non_evolvable_globs`（V6 已驗清單含四檔） | 一致 |

**不一致的根據**（F-01）：
- (c)：範本〈終止條件・休眠・再開〉的 T2 與 PRD C14 列都寫「缺陷帳本新立 P≤2 未結列」（`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md:354`、`PRD:575`「新 P≤2 未結 DEF」），事件源是缺陷帳本（DEF），不是觀察帳本的嚴重度。
- (d)：PRD:252 與 PRD:575「已採納工件再開症狀」、PRD:636 `status` 列「已確認的復發連結指向某 promoted PROP 的 `sources`」，對象是已採納（promoted）的工件，不是觀察帳本中處置為 deferred／retired 的列。
- (e)：FR-SI-27（PRD:377–379）的容量事件是「有上限的儲存或載入面（記憶索引、KB、偏好注入）用量達其上限的 `CAP_FRAC`」，與額度（quota）或 context 水位無關；根 `CLAUDE.md` 還特別強調額度與 context 水位是兩把不同的尺。
- (b)：缺「經審查者確認相同」。

TCS R25 (2) 與 AT-003-1-1／AT-032-1-1 只以關鍵字（`P≤2`、`再開症狀`、`容量事件`…）判準，所以 42 個 AT 全綠仍抓不到這個偏離——這正是 TCS 把語意留給 V8 的設計。SOP 是各角色任務書的上位文件，啟動條件寫錯會讓後續任務書沿用錯的觸發定義。

**Developer 交卷「流程摩擦」節對帳（對照 X＝56ef5393）**：Developer 交卷共 5 項，皆已入帳——#1（ruff format 膨脹吃光護欄層單輪上限）→ OBS-SI-052；#2（任務書 AT 39 對 TCS 42）→ OBS-SI-053；#3（任務書重釘句與 NFR-P0-8 矛盾）→ OBS-SI-054；#4（根層全套途中撞 5 小時窗）→ OBS-SI-055；#5（誤用 Bash 被 hook 擋）→ OBS-SI-056（`merged@OBS-SI-011`）。SD 重釘棒與主控的 057～062 共 6 列，依 X 的 commit message 對應「SD 四項＋主控兩項」；057 處置稱「記憶檔第 5 點改寫」，已核對 `guard-ratchet-repin-ritual.md:20` 現文含「`--jsonl` 是輸出路徑」。SD 交卷原文我沒有拿到，057～060 與 SD 交卷項目的逐項對帳未驗（§7）。V2 於入帳後仍為綠（`rows=62`）。結構性備註（F-11）：V8 要求「QA 棒的交卷於 SCG-4 前已入帳」，對本棒（SCG-4 QA）本身在時序上不可能成立，本報告 §6 的項目須由主控於收尾前入帳。

### V9 P0 退出條件 (a)，與 M 之後只追加 — 通過

```text
> git log --format="%h" f1d7660f..HEAD -- <ledger>        56ef5393                         rc=0
> git log -p --format="COMMIT %h" --unified=0 f1d7660f..HEAD -- <ledger>      rc=0
  hunks = 1        @@ -61,0 +62,11 @@
  removed lines ('-') = 0        added lines ('+') = 11     （OBS-SI-052～062，皆 2026-10-19 15:11）
```

判斷：N 之後只有 X 一個 commit、單一 hunk、純追加 11 列、0 行刪改；N 之後既有的列（001～051）零原地改寫；`history.row_mutated` 為 PASS（機械憑證，V2）。11 個新增列皆通過 `check`（V2 與 V2 的獨立重判）；新增列沒有「某欄無法填」的反症狀（12 列：051～062 的 9 欄皆有值）。觀察（P4，F-09）：052～062 的時間欄皆為批次入帳時刻 15:11，不是各事件的發現時點（PRD §5.1.1「發現時點」；Developer 事件約在 12:00～14:30）。

---

## §3 AT 抽查（對照 TCS 的 Given／When／Then）

**全檔實跑**：

```text
> python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=     rc=0   wall=38.73s
........................... [ 64%]
...............                 [100%]
42 passed, 86 subtests passed in 38.41s
> --collect-only：42 tests collected（每個 AT 恰一個測試函式，名稱含其底線形）
```

**逐 AT 單跑**（TCS §2 的判定指令 `-k <底線形>`，42 次）：全數 `1 passed`（含子測試）、rc＝0、每個 `-k` 恰選到 1 個測試；逐項結果與座標見姊妹檔 RTM §2。

**TCS 結構自檢**（`qa_scg4\rtm_data.py` 機械抽取）：FRD-lite 的 AC＝19、§1 映射的 AT＝42、AC 集合與 FRD-lite 相等；§2 gherkin 區塊 42 個，皆含判定指令與驗收字樣；§1 與 §2 的 AT 集合相等；測試函式 42 個；E 類 22、Integration 17、Unit 25，與 TCS 自述（E 類 22、用真 git 17）相符。AC→AT 100% 映射成立。

**抽查（本棒讀完 42 個測試本體並逐一對照 TCS；下表為深度對照的 12 個）**：

| AT | TCS 的 Then 要點（TCS 行） | 測試實際斷言（測試檔行） | 結論 |
|----|---------------------------|--------------------------|------|
| AT-001-1-E-2 | 七欄各自清空恰一筆 `FIELD-EMPTY`、detail 含欄名、不連帶其他項；四種佔位值；五種不可定位座標含第一段含 a～f 的真實形裸 sid；`sid … line=12`／`seq: 3` 通過（`:394–413`） | `:755–800`：七欄 subTest 斷言集合恰為一筆、`assertIn(col, detail)`、三項不含該列；佔位值恰四列；座標恰 004～008 的 `COORD-NONE`，UUID 為 `0a1b2c3d-…`（含 a～f）；兩種 sid 寫法斷言 PASS 且 findings 為空 | 一致 |
| AT-001-1-E-5 | 700／701 位元組邊界、CJK 300 字、`row_max_bytes`＝800、五種控制字元含行中單獨 CR、整檔 CRLF 與基線逐項同狀態、warn／fail 恰等於檔案大小（`:469–489`） | `:905–959` 全部斷言，包含 CRLF 時 21 項狀態與基線相同、`VOLUME-WARN` 的 level 為 warn | 一致；文字形態 `[warn]` 前綴無 AT（F-05） |
| AT-001-2-1 | 守衛面 P1＋暴露無→`GUARD-P12-NO-EXPOSURE`；P2 缺暴露鍵→`GUARD-NO-EXPOSURE`；P3 與非守衛面放行；缺面、面值域外、暴露值域外（`:516–531`） | `:996–1025` 斷言兩集合恰為所列 | 一致；**P2＋暴露＝無的組合沒有 AT**（突變存活，F-05） |
| AT-001-3-E-2 | 七種確認列變體，(a)～(f)→`MIG-CONFIRM-MISSING` 加 `ROW-MUTATED`，(g) 通過；且「引言文字內容不被比對」（`:573–587`） | `:1089–1114` 七個變體 subTest 全斷言 | 一致；「引言不被比對」未被直接斷言（F-07） |
| AT-001-3-E-3 | 六種無效 sha（`zzzz`、縮寫 12 位、無此物件、blob、無父 commit、大寫）各得對應碼，且 row_mutated 含四個舊列、rc 1（`:591–606`） | `:1116–1149` 六個 subTest，孤兒 commit 以 `mktree`＋`commit-tree` 建 | 一致 |
| AT-004-3-E-1 | N 之後五個 commit（改症狀、二次改處置、刪列、改號、混改）→五筆 `ROW-MUTATED`，順序為 002、003、004、005、001，cause 與 commit 短 sha 正確、含「掌舵者」（`:846–862`） | `:1544–1584` 斷言順序、cause 列表、`commit=` 短 sha、新 ID 009 不被標、`history.migration` 維持 PASS、rc 1 | 一致；突變 M-C 被殺 |
| AT-004-1-E-1 | 五種位置的懸空 OBS 各一筆、同編號多處只報一筆、七處提及截斷為 5 處加 `…+2`（`:749–767`） | `:1424–1466` 五個單點情境、雙點情境、七處情境；斷言 detail 的位置數與 `…+2` | 一致；突變 M-M 被殺 |
| AT-030-1-1 | in-process 與子行程（`PYTHONIOENCODING=cp950`、cwd 放誘餌檔）；文字與 JSON 的 rc、各項 status、**各項 finding 的 (subject, code) 集合逐項一致**；**文字形態逐行符合 R3 的行文法（含縮排的 finding 行）**；JSON 鍵序（`:942–961`） | `:1661–1742`：rc、`obs-draft:` 與恰一行草稿列、項目行以正規式比對並與 JSON 的 status 對映、無 ANSI、子行程 UTF-8 解碼、相對路徑語意、四層鍵序皆斷言；**縮排的 finding 行只斷言非空，沒有解析 `<subject> <CODE> <detail>`，也沒有與 JSON 的 finding 集合比對**（`:1678–1679`） | **弱於 TCS 文字**（F-04）；突變 M-H（文字形態完全不印 finding 行）存活 |
| AT-030-2-1 | `GIT_DIR`、`GIT_INDEX_FILE` 污染不改結果；檔案摘要與 `git status --porcelain` 前後相同；`subprocess.run` 記錄器驗 argv／`shell`／`timeout`／`encoding`／`errors`／淨化後的 env；`Popen` 次數等於 `run` 次數；AST 驗 import；寫入原語正規式加自證（`:986–1003`） | `:1780–1878` 全部斷言；突變 M-K（拿掉 timeout）被殺 | 一致；記錄器看不到 `os.system`（F-07，靜態面我另以 grep 驗為零命中） |
| AT-031-1-E-2 | 缺少、多出、重複、來源變動判紅；順序不拘；PRD 行或 CLAUDE.md 讀不到判 NE（`:1088–1105`） | `:2041–2090` 五個判紅情境、順序顛倒 PASS、兩個 NE 情境 | 一致 |
| AT-003-1-1 | R26 的 14 個禁用字樣各以合成字串自證且乾淨字串不命中；`status`／`prop-new` rc 3 且 stdout 空；settings 不含 `selfimproving`；SOP 判準與逐一刪除自證（`:675–690`） | `:1264–1320` 全部斷言；其中 `:1314` 的 `sop_roles_problems(sop)[:0]` 恆為空串，是恆真斷言 | 一致；恆真斷言（F-07）；語意由 V8（F-01） |
| AT-001-3-E-4 | 附註檔缺、錨點不符、遷移之外使用 `orig`、語法錯、跳脫字串正向（`:610–629`） | `:1151–1187` 六個情境全斷言；**R18 (c) 的「絕對路徑或含 `..` 逃出 repo 視同不存在」沒有任何 AT** | 與 TCS 一致；規則面缺口（F-03） |

**突變試驗（量 AT 的鑑別力；只動 scratchpad 複本，repo 零改動）**：`qa_scg4\mut_run.py` 把測試檔、`tools/selfimproving.py`、`tools/lib/si_*.py` 與測試唯讀存取的真檔複製到 `qa_scg4\mutroot_<時間戳>\`，複本基線 `42 passed, 86 subtests passed in 39.38s`；再逐一對生產碼做單點突變並以對應 `-k` 重跑。22 個突變中 16 個被殺、6 個存活：

| 突變 | 結果 | 含義 |
|------|------|------|
| M-A 體積 fail 邊界 `>=` 改 `>`；M-B 列位元組邊界 `>` 改 `>=` | 被殺 | AT-001-1-E-5 咬得住兩個邊界 |
| M-C open 轉終值放行條件拿掉「其餘格相等」 | 被殺 | AT-004-3-E-1 的混改情境有效 |
| M-D 確認列不再要求 decided；M-E 不再要求含 M 的 sha 前 7 位 | 被殺 | AT-001-3-E-2 有效 |
| M-I 拿掉 `ROW-ID-DUP`；M-J 比例鍵上界含 1 改不含；M-K 拿掉 git 的 timeout；M-L 指紋不做 CRLF 正規化；M-M 位置截斷 5 改 6；M-O 忽略工作樹版本；M-P 遷移豁免不改用基準；M-Q retired 缺座標不再判；M-R 草稿 ID 不加一；M-S fixed@ 不解析；M-T 載體 NE 改 blocking | 全數被殺 | 對應 AT 有鑑別力 |
| M-F 拿掉 R18 (c) 的「含 `..`」判斷；M-F2 拿掉 `is_absolute` 判斷 | **存活** | R18 (c) 路徑逃逸沒有 AT（F-03） |
| M-G 體積 warn 去掉 `[warn]` 前綴 | **存活** | R3 的 `[warn]` 前綴沒有 AT（F-05） |
| M-H 文字形態不印任何 finding 行 | **存活** | AT-030-1-1 弱於 TCS（F-04） |
| M-H2 NE 行不印 `blocking`／`nonblocking` | **存活** | R3 的 NE 字樣沒有 AT（F-05） |
| M-N 守衛面 P1／P2 規則只認 P1 | **存活** | P2＋暴露＝無沒有 AT（F-05） |

**黑箱探測**（`qa_scg4\bb_probe.py`，合成 repo 全建在 scratchpad）：(1) 體積 warn 時文字形態印 `PASS ledger.volume` 與縮排的 `- VOLUME-WARN [warn] 帳本 2024 位元組已達 warn 線`；紅變體的 finding 行（`OBS-SI-003 ENUM-CATEGORY …`、`ROW-MUTATED commit=WORKTREE cause=changed 列被原地改寫，請掌舵者過目`）與項目行全部符合 R3 文法，不合文法行數＝0；草稿列九欄、ID 為最大值加一、時間 `2026-10-19 15:36 +08:00`。(2) R18 (c)：`orig=@../…` 與 `orig=@C:/…`（含磁碟機代號的絕對路徑）皆 `ORIG-NOTES-MISSING`；**`orig=@/Users/…`（rooted、無磁碟機代號）在 Windows 上被當相對路徑解析為 `C:\Users\…`（repo 外）而 PASS**——POSIX 上同一輸入是絕對路徑、應判 MISSING（F-03）。(3) CLI：`main([])`、`status` 皆 rc 3、stdout 空、stderr 有「用法錯誤」；`check --help` rc 0 並列四個旗標。

---

## §4 發現

嚴重度口徑同 `docs/06_quality/FiveQuestion_Audit_Protocol/severity.md`（非守衛面：P2＝文件自相矛盾／結案不成立；P3＝文字與可用性；P4＝理論洞與建議）；依任務書，V1～V9 任一不通過即 P2。

| 編號 | 嚴重度 | 發現 | 座標 | 建議處置 |
|------|--------|------|------|----------|
| F-01 | **P2** | SOP〈啟動條件〉(b)(c)(d)(e) 與 PRD AC-SI-03-1 語意不符：(c) 把「缺陷帳本新立 P≤2 未結列」寫成觀察帳本的 P1／P2 觀察入帳；(d) 把「已採納工件的再開症狀命中」寫成帳本中 deferred／retired 列的再開症狀；(e) 把 FR-SI-27 的「儲存／載入面容量達 `CAP_FRAC`」寫成額度或 context 水位事件；(b) 漏「經審查者確認相同」。V8 不通過 | `docs/05_development/SelfImproving_Operations_SOP.md:12–15`；對照 `docs/01_requirements/SelfImproving_PRD.md:252、:575、:636、:377–379`、`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md:354` | 主控或文件作者改寫 SOP:11–15（SOP 不在凍結集合內，不需動 PRD／TCS）。建議文字——(a) 掌舵者指令：掌舵者明示要求啟動或再開（T1）。(b) 同一症狀第二次被記入觀察，且經審查者確認相同（P0 以人工比對）。(c) 缺陷帳本新立 P≤2 未結列（即範本〈終止條件・休眠・再開〉的 T2）。(d) 已採納工件的再開症狀命中（P1 起才有已採納工件，P0 無此事件源）。(e) 容量事件（FR-SI-27）：記憶索引、知識庫或偏好注入等有上限的面，用量達其上限的 `CAP_FRAC`。此寫法保留 R25 (2) 的全部關鍵字，改後重跑 `-k "AT_003_1_1 or AT_032_1_1"` 與 `check`（須仍為 rc 0），再由 QA 複驗 V8 |
| F-02 | **P2** | V3 (9)「座標可重查」未通過：OBS-SI-047 的檔案路徑不存在（git 歷史上也從未存在）；實檔在 `AutoClaude/autoclaude/infra/adapters/`。軟性同型問題：020 的 `:319` 行號過期（T-1 現在 SOP `:340`）；030 的量測值因 MEMORY.md 重排失效且檔在 repo 外；043／048／049 的「SA 回報／交卷 §N」沒有 `sid`＋`line`，只能搜逐字稿；新列 058 的座標同屬易失（唯一的檔是待刪的 repo 外殘留檔、另一個座標是對話內的 SD 交卷；057 另有 repo 內檔 `tools/probe/guard_layer_bucket_census.py` 可查） | 帳本 OBS-SI-047 的「證據座標」欄；`git log --oneline --all -- AutoClaude/autoclaude/execution/sdd_to_playbook_adapter.py` 無輸出 | 主控追加更正列（`rel=corrects:OBS-SI-047`，座標改為 `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py`；M 之後不可原地改）。020、030、043 建議同批以更正列補 repo 內座標或 `sid`＋`line`。往後引用子代理交卷的座標一律帶 `sid`＋`line`（見 §6）。補救後 QA 複驗 V3 (9) |
| F-03 | P3 | R18 (c)「絕對路徑視同不存在」在 Windows 上對 rooted 路徑（開頭 `/`、無磁碟機代號）不成立：`Path("/x").is_absolute()` 在 Windows 為 False，程式把它接到 repo 之下解析成同磁碟機根的 repo 外檔案而放行；POSIX 上同輸入判 MISSING，違反鐵律三的跨平台自問。唯讀、`orig` 僅遷移使用，風險低；沒有任何 AT 涵蓋 `..` 或絕對路徑（突變 M-F、M-F2 存活） | `tools/lib/si_refs.py:125`（`target = None if p.is_absolute() or ".." in p.parts else repo / p`）；黑箱探測 `qa_scg4\bb_probe.txt` 第 35–37 行 | 判斷改為 `rel.startswith(("/", "\\")) or PureWindowsPath(rel).drive or p.is_absolute() or ".." in p.parts`；補一個 AT（`..`、含磁碟機代號、rooted 三種）。TCS 已凍結，補測試屬測試檔增列、不動規格 |
| F-04 | P3 | AT-030-1-1 的斷言弱於 TCS 文字：TCS 要求文字與 JSON 的 finding (subject, code) 集合逐項一致、文字形態逐行符合 R3 文法（含縮排 finding 行），測試只斷言縮排行非空；突變 M-H（文字形態完全不印 finding 行）全綠 | `tools/tests/test_selfimproving_check.py:1676–1684`；TCS `:956–957` | 解析縮排行 `^  (\S+) ([A-Z][A-Z0-9-]+)( .*)?$`，與 JSON 的 (subject, code) 集合相等，並加對 `overall=` 行的正規式 |
| F-05 | P4 | 三處規則無 AT 鑑別（突變存活）：R3 的 `[warn]` 前綴（M-G）、R3 的 NE 行 `blocking`／`nonblocking` 字樣（M-H2）、R15 守衛面 P2＋暴露＝無（M-N）。TCS 本身未要求這些斷言，屬規格面缺口 | `tools/lib/si_check.py:130`、`:187`；`tools/lib/si_rows.py:225`；TCS R3、R15 | 補三個斷言（同 F-04）；P1 的 TCS 登記為必測項 |
| F-06 | P3 | Developer 交卷沒有逐 AT 列出驗收字樣 `[AT_OK_…]`，只報 `42 passed`；TCS §2 要求「逐 AT 列出驗收字樣」且「沒貼＝未驗證」。（Developer 的終端輸出 `out_dev_p0*.txt` 與交卷檔皆零命中 `AT_OK`） | TCS `:340`；`…\scratchpad\selfimproving\dev_p0_handoff.md` | 本棒的逐 AT 單跑（RTM §2）已補足機器證據；建議流程上要求 Developer 交卷附 42 行驗收字樣，或將此規則改為由 QA 補跑 |
| F-07 | P4 | 測試衛生四點：(i) `:1314` 恆真斷言；(ii) AT-001-3-E-2 未直接證明「引言文字內容不被比對」；(iii) 模組層級 `tempfile.mkdtemp()` 於 import 即建暫存目錄，單獨 import 測試模組（如黑箱探測）須自行呼叫 `tearDownModule()`；(iv) AT-030-2-1 的記錄器看不到 `os.system`／`os.popen`（本棒以 grep 驗證 `tools/selfimproving.py` 與 `tools/lib/si_*.py` 零命中 `os.system`、`os.popen`、`check_output`） | `tools/tests/test_selfimproving_check.py:1314`、`:1089–1114`、`:43`、`:1780–1878` | 刪恆真斷言；為 (ii) 加「引言改成任意文字仍 PASS」的對照變體；(iii)(iv) 視需要 |
| F-08 | P4 | 確認列 OBS-SI-051 為授權代決型：引言是一般授權（line 2476）與「開 P0 實作」（line 2581），不是針對遷移豁免的逐項確認；處置欄已誠實標示。符合 TCS R19 (d)（只驗存在與格式），語意強度弱於 PRD AC-SI-01-3 (b) | 帳本 OBS-SI-051；V5 | 建議掌舵者下次互動時明示追認（可選，P0 退出不依賴） |
| F-09 | P4 | 052～062 的時間欄皆為批次入帳時刻 15:11，非各事件發現時點；與 PRD §5.1.1「發現時點」口徑及 OBS-SI-031 的先例不符；`check` 只驗格式 | 帳本 OBS-SI-052～062；PRD:205 | 以後批次入帳時依各事件的實際時刻填；既有列不可原地改，視需要以更正列處理 |
| F-10 | P4 | 護欄層重釘走一次性例外：例外名冊上限 4→5（可見上修）、接鏈列借用既有缺陷列的編號。已誠實入帳為 OBS-SI-052 與 OBS-SI-060；屬主控與掌舵者的治理裁決，QA 僅標示 | `tools/tests/test_adr_xplat001_c1c2_lock.py:2770`（名冊列）、`:2786`（`_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES = 5`）、`:3555`（接鏈列） | 請掌舵者過目；OBS-SI-052 已寫再開症狀（第 6 筆名冊需求即改機制） |
| F-11 | P4 | SOP 其他微偏與 V8 的時序倒置：(i)「由掌舵者裁決」把 T2～T4 一併說成裁決；(ii) 未寫 AC-SI-02-1 的「須另有 ≥1 個內部來源佐證」；(iii) 未寫 AC-SI-03-2 的「成效宣稱須指向症狀指標（§1.3）」；(iv) V8 要求 QA 棒交卷於 SCG-4 前入帳，對 SCG-4 QA 本身不可能成立 | SOP:23、:50、:21；TCS V8 | 併入 F-01 的 SOP 修訂；(iv) 於下一份 TCS 範本改為「SCG-4 收尾前入帳」 |
| F-12 | P4 | OBS 草稿列的「前 5 個非 PASS 項」名額會被 nonblocking NE 的 `ref.carrier_families` 占用（R6 字面如此），真正失敗的項目多時會被擠出草稿 | `tools/lib/si_check.py:158`；黑箱探測第 25 行 | 草稿排除 nonblocking NE（需改 R6 字面，P1 的 TCS 再議） |
| F-13 | P4 | T 提交含 §5.6 以外的檔案：兩支 compat-ci workflow 的 `paths`、兩個 guard-total 站點文件；為重釘與 CI paths 覆蓋鎖的必要連動、由主控收尾 | `git show --name-status --format= 13e87b74` | 下一份 TCS 的 §5.6 預留「CI paths 與 guard-total 站點」兩類連動檔 |
| F-14 | P4 | V3 (8) 備註：五列把再開症狀子句移出現行處置（只存 `orig`）；34 列 `decided` 未寫裁決者（TCS §7.2 預審登記項 F-12 已登記） | 帳本 OBS-SI-010、022、024、042、049；PRD:218 | 不需處理；日後以追加列補更新 |

**統計**：P1＝0；P2＝2（F-01、F-02）；P3＝3（F-03、F-04、F-06）；P4＝9（F-05、F-07～F-14）。

---

## §5 判定

**FAIL**——理由：V8 不通過（F-01，SOP 啟動條件的 (b)(c)(d)(e) 與 PRD AC-SI-03-1 語意不符）與 V3 的 (9) 不通過（F-02，第 047 列座標點不到），依任務書「V1～V9 任一不通過＝P2、任一 P1／P2＝FAIL」。

TCS 末段〈SCG-4 通過標準〉逐項：

| 驗證項目 | 本棒結果 |
|---------|----------|
| AC → AT 100% 映射 | 通過：19/19，機械抽取驗證（§3「TCS 結構自檢」） |
| AT 格式可自動化 | 通過：42 個 gherkin 區塊皆含判定指令與驗收字樣；42 個測試函式名含其底線形，逐 AT 單跑皆 `1 passed` |
| 負向測試覆蓋 | 通過：每個 AC 至少一個負向（E 類，或內含負向變體，或 SOP 條文逐一刪去的副本須判不合格）；突變試驗 16/22 被殺 |
| 邊界值測試 | 通過：列位元組 700／701、反空轉下限 9／10、`w_opp` 等於 `w_min`、體積 warn 與 fail 恰等於檔案大小皆有斷言（突變 M-A、M-B 被殺） |
| 測試資料規格完整 | 通過：`base_rows`（`:202–263`）與 TCS §5.1 基線 10 列逐列相符（分類、嚴重度、處置、座標形態、標記）；遷移鏈 fixture（`:429–509`）與 §5.2 相符（C0 四列、處置原文超過 450 位元組、M 單一 commit、N 的確認列時間與 sid／line）；`hermetic()` 與 `_STRIP`（`:34–42`、`:124–133`）與 §5.5 相符 |
| 實跑檢核 V1～V9 全部有逐字輸出證據 | **未通過**：V3 (9)、V8 不通過（其餘 V1、V2、V4～V7、V9 通過並附輸出） |

可通過的部分（皆有當回合輸出）：提交鏈（V1）、`check` 對真帳本 rc 0（V2，含獨立重判）、`migration_base_sha` 與祖先關係（V4）、確認列引言座標（V5）、23 鍵初值與 25 項 glob（V6）、根層全套 rc 0／ruff／LOC／缺陷編號引用鎖／凍結三檔不變／工作樹零改動（V7）、N 之後只追加（V9）；42 個 AT 全數單跑與整檔皆通過。

轉 PASS 的最小條件：(1) 改寫 SOP 啟動條件 (b)～(e)（F-01）；(2) 追加 OBS-SI-047 的更正列（F-02），建議同批補 020、030、043。完成後我只需複驗 V3 (9)、V8，並重跑 `-k "AT_003_1_1 or AT_032_1_1"`、`check`（須為 rc 0 且 `ref.obs` 仍 PASS）與根層全套；其餘 P3、P4 不阻斷 SCG-4，可併入下一輪。

---

## §6 流程摩擦（本棒；每項一句症狀加一個座標，請主控於 SCG-4 收尾前入帳）

1. 系統提示（MCP Server Instructions，auto mode）再度要求優先用 Bash，與根 `CLAUDE.md`〈鐵律一〉衝突，本棒全程改用 PowerShell／Read／Grep／Glob／Edit／Write（OBS-SI-011 再復發）；座標：根 `CLAUDE.md`〈鐵律一〉。
2. `Grep` 的 `glob` 參數帶含目錄分隔符的大括號展開（`{selfimproving.py,lib/si_*.py,…}`）回「No files found」假陰性，改拆成多次單一 glob 才找到；座標：`docs/06_quality/TCS-PREREVIEW-SelfImproving-P0-20261019.md` 的流程摩擦 #3（OBS-SI-046 同族）。
3. `Grep` 對極長行回「[Omitted long matching line]」（SOP、記憶檔），改用 `-o` 搭 `.{0,80}…` 視窗取片段；座標：`C:\Users\wuwei\.claude\projects\D--CursorProject-AISDCL-Agent\memory\guard-ratchet-repin-ritual.md:20`（OBS-SI-033、OBS-SI-038 再復發）。
4. `python -I` 忽略 `PYTHONIOENCODING`，PowerShell 主控台以 cp950 解碼原生 python 的中文輸出成亂碼（本棒遇 3 次），一律改寫檔再用 Read 讀；座標：OBS-SI-029 同型（`python -I` 與主控台編碼）。
5. 根層 `run_root_unittests.py` 不印「通過數」（只印發現數、skip 明細與 rc），任務書的「通過數以實跑為準」無法逐字滿足；座標：`tools/run_root_unittests.py` 的 stdout（本報告 V7 逐字摘錄）。
6. 帳本座標型態「SA 回報 §N」「主控 JSON 解析親驗」沒有持久載體，V3 (9) 只能搜逐字稿才能重查；座標：帳本 OBS-SI-043、OBS-SI-048、OBS-SI-049 的證據座標欄。
7. 測試檔在模組層級建 `tempfile.mkdtemp()`，為做黑箱探測而 import 它會在 `%TEMP%` 留 `si_check_*` 目錄；座標：`tools/tests/test_selfimproving_check.py:43`。
8. Developer 交卷沒有逐 AT 的驗收字樣，QA 須自跑 42 個判定指令補證；座標：TCS `:340`。

---

## §7 未查證／未做

- **macOS／POSIX 未實跑**（NFR-P0-3、NFR-SI-06-5 標「未驗」）；F-03 的 POSIX 行為是依 `pathlib` 語意推斷，未在 POSIX 實跑。
- **GitHub Actions／CI 端未跑**：包含 T 對兩支 compat-ci workflow 的 `paths` 變動，以及 NFR-P0-2 的「CI 上整個測試檔小於 180 秒」（本機單檔 38.41 秒；根層平行 worker 內 81.0 秒）。
- **SD 重釘棒交卷原文未取得**：057～060 與 SD 交卷項目的逐項對帳未驗（只驗了 057 的記憶檔改寫與入帳列本身通過 `check`）；SD 若有未入帳項目我看不到。
- **「SA／QA 回報 §N」類座標**只做存在性搜尋（確認 SA 交卷在逐字稿 line 約 2959、3272），未逐段比對內容。
- **V3 (8) 為語意判斷**：50 列逐列審視，`fixed@` 8 列以 `git log -S` 與 commit subject 驗證；其餘 `decided` 34 列未回溯各自「所述事實是否已執行」。
- **TCS 提交順序段預期的紅燈狀態未重現**：T 之前與「M 之後、N 之前」`check` 對真帳本應為紅，我只驗了 HEAD（N 之後）為綠。
- **突變試驗為手選 22 個，非窮盡**；複本以 HEAD 檔案為基礎，不涵蓋 `tools/_stdio_utf8.py` 與其他根層鎖。
- **未跑** `lint-imports`、AutoClaude 的 pytest、AISDLC_SDD 的 `ci-gate`（本變更未觸及這些面）。
- **`check` 的邊界未探**：`--repo` 為較大 repo 的子目錄、tmp 位於另一個 git 工作樹內（TCS §7.2 預審登記項 F-14 已登記）、非 ASCII 檔名的 `git grep` 輸出。
- **PRD 行座標**只核對本報告引用到的 AC、NFR 與 FR 行；TCS 所引其餘 PRD 行（例如 PRD:635、:676 的 `check` 列細節）未逐一比對。
- repo 內執行 Python 與 pytest 會在工作樹內產生被 git 忽略的 `__pycache__` 與 `.pytest_cache`；`git status --short` 在執行前後皆為乾淨（V7）。

### 證據檔（scratchpad，不入庫）

`qa_scg4\` 下：`run_cmd.py`、`qa_lib.py`、`v2_check_json.txt`、`v2_independent.py/.txt`、`v3_audit.py/.txt`、`v3_fixed_sha.py/.txt`、`v3_coord_exist.py/.txt`、`v3_sid_lines.py/.txt`、`v3_queue_ops.py/.txt`、`v3_queue_kw.py/.txt`、`v3_find_sa_handoff.py/.txt`、`v5_transcript.py/.txt`、`v6_params.py/.txt`、`v6_prd_peek.py/.txt`、`v7_root_suite.txt`（根層全套完整輸出）、`v7_loc.json`、`at_full.txt`、`each_at.json/.txt`、`rtm_data.py/.json/.txt`、`bb_probe.py/.txt`、`mut_run.py`、`mut_results.txt`。

---

## §8 二審（複驗）

**二審日期**: 2026-10-19（本節寫入時刻 17:09 +08:00）　**審查者**: 同一位 SCG-4 獨立 QA 棒（Sonnet 5.5；仍未參與 TCS 撰寫、P0 實作與一審發現的修復）
**複驗基準**: HEAD `622c83d22675d41c8e85172e95c8af92a6c399f3`（＝Y5；FSM 已回 PR_REVIEW）
**二審判定**: **PASS**（P1＝0、P2＝0、P3＝0；P4 殘餘 6 項皆不阻斷，見 §8.7、§8.8）。一審兩個阻斷項——V3 (9)（F-02）與 V8（F-01）——複驗通過；一審六個存活突變（M-F、M-F2、M-G、M-H、M-H2、M-N）對新碼重放全數被殺。**§5 的「FAIL」與檔頭的「判定」列是一審歷史原文（依任務書未改動），現行判定以本節為準。**

> 方法聲明同一審：凡寫「通過」者皆附本回合真跑的指令與輸出，做不到的寫「未驗」（§8.11）。稽核與突變腳本放在 scratchpad `qa_scg4\`（`r2_` 前綴，不入庫）；repo 內除本檔與姊妹檔外零改動（§8.5 寫入前現查）。Windows 上只用 PowerShell／Read／Grep／Glob／Edit／Write，Python 一律 `.venv`。工具輸出若帶表情符號，下文逐字引用時略去行首符號。

### 8.1 輸入快照與提交鏈

| 代號 | sha | 本機時間 | 內容 |
|------|-----|----------|------|
| Y1 | `6c4a753d` | 16:05:42 | 一審報告與 RTM（本棒；2 檔新增） |
| Y2 | `9fd15796` | 16:09:22 | SOP〈啟動條件〉(b)～(e)、無事件、再開、外部衍生四處改寫（1 檔，7 增 7 刪） |
| Y3 | `4eb912d0` | 16:09:53 | 帳本 063～081（19 列純追加） |
| Y4 | `968e827b` | 16:36:07 | SD 棒修復：`tools/lib/si_refs.py`、測試檔、護欄層重釘（鎖檔與兩個 guard-total 站點；5 檔，146 增 32 刪） |
| Y5 | `622c83d2` | 16:36:48 | 帳本 082～092（11 列純追加） |

```text
> git rev-parse HEAD                      622c83d22675d41c8e85172e95c8af92a6c399f3   rc=0
> git status --short                      （空；行數 0）   rc=0
> git diff --name-only                    （空）   rc=0
> git diff --cached --name-only           （空）   rc=0
> git diff --stat -- .claude              （空）   rc=0
> git log --oneline 56ef5393..HEAD -- <PRD> <TCS> <研究方法 SOP>        （0 筆）   rc=0
> git diff --stat 56ef5393..HEAD -- .claude .github                     （空）   rc=0
> git diff --name-status 56ef5393..HEAD   （9 檔：M 7、A 2〔A＝本棒兩份報告〕）
  M docs/04_planning/AutoSDD_improving_112.md
  M docs/05_development/SelfImproving_Operations_SOP.md
  M docs/06_quality/CrossPlatform_R145_Scan_Findings.md
  A docs/06_quality/RTM-SelfImproving-P0-20261019.md
  A docs/06_quality/SCG4-REVIEW-SelfImproving-P0-20261019.md
  M docs/06_quality/SelfImproving_Observation_Ledger.md
  M tools/lib/si_refs.py
  M tools/tests/test_adr_xplat001_c1c2_lock.py
  M tools/tests/test_selfimproving_check.py
> Get-FileHash -Algorithm SHA256 <PRD>        9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e   （與一審相同）
> Get-FileHash -Algorithm SHA256 <TCS>        6c4e28ed30ab3e05ea1acbbf4b8d1a5a5004f5a2aed3fb535abb59cfb420de56   （與一審相同）
> Get-FileHash -Algorithm SHA256 <研究方法 SOP>  deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2   （與一審相同）
> git log --first-parent --format='%h parent=%p' -n 9
  622c83d2 parent=968e827b / 968e827b parent=4eb912d0 / 4eb912d0 parent=9fd15796 / 9fd15796 parent=6c4a753d
  6c4a753d parent=56ef5393 / 56ef5393 parent=f1d7660f / f1d7660f parent=ab4638c4 / ab4638c4 parent=13e87b74 / 13e87b74 parent=eaed744b
> git merge-base --is-ancestor <T|M|N|X> HEAD      四個皆 rc=0
> git diff --stat 56ef5393..HEAD -- docs/06_quality/SelfImproving_Protocol   （空；協定目錄零改動）
> params.json 的 migration_base_sha = ab4638c439ad1cc4b8408efcd454c29ef7966d0b（＝M 的完整 sha；V4 輸入不變）
```

範圍判斷：Y2～Y5 只動 SOP 四處、帳本（只追加）、`si_refs.py`、測試檔、護欄層重釘與兩個 guard-total 站點；沒有碰 `.claude/**`、`.github/**`、凍結三檔、協定目錄或 `params.json`。V1（提交鏈）、V4（`migration_base_sha`）、V6（`params.json` 初值）的輸入未變，且 V2 的 `history.migration`（`claim=valid`）、`params.*` 皆 PASS（§8.5），故不重做一審的逐項細查。

### 8.2 V3 (9) 複驗——通過（F-02 結案）

帳本 063～068 是六列更正列（`rel=corrects:<原列>`；M 之後不可原地改，故以追加列更正）。逐一重查新座標：

| 更正列 | 更正對象 | 新座標 | 重查結果 |
|--------|----------|--------|----------|
| 063 | 047 | `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py` | 存在（32034 位元組）且有 git 追蹤；舊路徑 `execution/…` 在 `git log --all` 仍 0 筆 |
| 064 | 020 | 研究方法 SOP `:340` | 檔共 370 行；第 340 行是 T-1 列（`T-1`、`SA 寫 PRD 時…`） |
| 065 | 030 | `MEMORY.md:3`（repo 外：`~/.claude/projects/<slug>/memory/`） | 唯讀 Read：第 3 行是檔頭「排序原則」註（見下） |
| 066 | 043 | sid `f3ead132-…` line 2959 | 實體行 2959：`type=user`、`origin.kind=peer`，寄件者是 SA 代理，內容為 SA 起草 TCS 的交卷；其第 5 節寫明 line 2536、2493 是 assistant 空文字記錄，2525、2476、2581 是人工句——與 043 的主張一致 |
| 067 | 048 | sid `f3ead132-…` line 3272 | 實體行 3272：同一寄件者的 peer 交卷（TCS 修訂棒）；含「更正聲明」段，內有 Q3「8 列…舊處置重複計入一次」 |
| 068 | 049 | sid `f3ead132-…` line 3272 | 同一行含「開放問題現況」段，內有 Q6、九形態、`PRD:208` |

```text
> Test-Path AutoClaude\autoclaude\infra\adapters\sdd_to_playbook_adapter.py      True ; bytes=32034
> git ls-files -- AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py   AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py   rc=0
> git log --oneline --all -- AutoClaude/autoclaude/execution/sdd_to_playbook_adapter.py   （0 筆）   rc=0
> SOP:340（第 340 行前 80 字）     | T-1 | SA 寫 PRD 時，某需求在追溯矩陣找不到 DP 或 S-NN；或 PRD 把候選 CD-NN 當需求採納（§3.2 範圍外把 CD 當反例引
> MEMORY.md:3（Read；repo 外檔）   > 排序原則（2026-10-19，OBS-SI-030）：索引若被截斷是從尾端吃起，所以常青的〈工作方式教訓〉〈機制與環境事實〉放前面、會一直長的〈近期輪次〉殿後；舊輪次指標歸檔…

> python -I r2_transcript.py     （逐字稿 jsonl：23225777 位元組；以 b"\n" 切為 5488 段，實體行 N＝索引 N-1；唯讀 json.loads）
--- 實體行 2959 ---
  type='user' message.role='user' origin.kind='peer' origin.from='a11b56747dc350251' origin.name='general-purpose' handback=True 文字長度=8360
  前 120 字：'Another Claude session sent a message:\n<agent-message from="a11b56747dc350251">\n[Subagent hand-back] The text below is t'
  標題：'## 交卷：SA 新棒（P0 功能鍵 monorepo-si-p0-ledger，Stage-2）— 已完成'、'### 5. 給掌舵者與 PRD 的發現（PRD 凍結，未改，建議走 T1 或帳本更正列）' …
  '2536'／'2493'：命中；上下文＝'… line 2536 與 2493 都是 assistant 的空文字記錄（緊接在 assistant 收到訊息後的工具呼叫），不是人工句 …'
--- 實體行 3272 ---
  type='user' message.role='user' origin.kind='peer' origin.from='a11b56747dc350251' origin.name='general-purpose' handback=True 文字長度=8902
  前 120 字：（同上）
> python -I r2_transcript2.py
  【五】區段長度=654；含 Q6=True；含 九形態=True；含 PRD:208=True
  【六】區段長度=233；含 Q3=True；含 重複計入=True；含 8 列=True
```

延伸檢查（`r2_coord_exist.py`）：對 063～092 共 30 列的所有檔案座標逐一檢查，檔案皆存在、行號皆未超出檔長；唯一不在 repo 內的 `MEMORY.md` 以上列 Read 驗證；sid 型座標（066～068）以上列逐字稿驗證。節錄：

```text
OBS-SI-063: AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py -> EXISTS
OBS-SI-064: docs/05_development/SelfImproving_Research_Methodology_SOP.md:340 -> EXISTS 檔共 370 行；引用 340 OK
OBS-SI-065: MEMORY.md:3 -> MISSING（repo 外檔；改以 Read 驗，見上）
OBS-SI-081: docs/05_development/SelfImproving_Operations_SOP.md:11–15 -> EXISTS 檔共 72 行；引用 11–15 OK
OBS-SI-082: tools/lib/si_refs.py:125 -> EXISTS 檔共 145 行；引用 125 OK        （行號語意見 F-15）
OBS-SI-084: tools/lib/si_check.py:130 -> OK ; tools/lib/si_rows.py:225 -> OK
其餘 069～092：皆 EXISTS 且行號在界內
```

判斷：硬傷（047 的路徑）與一審列出的軟性項（020、030、043、048、049）都已由更正列補上可重查的座標；原列文字依 append-only 保持原樣（`history.row_mutated` 為 PASS，§8.5），讀者須經更正列才見新座標，這是設計取捨，不是缺陷。一審另點名的「新列 058 座標易失」本輪沒有更正，已併入 F-15（P4）。

### 8.3 V8 複驗——通過（F-01 結案；F-11 (i)(ii)(iii) 結案）

Y2 只動 SOP 四處（`git show --stat --format= 9fd15796`：1 檔，7 增 7 刪；hunk＝`@@ -12,4 +12,4 @@`、`@@ -21 +21 @@`、`@@ -23 +23 @@`、`@@ -50 +50 @@`），即 (b)～(e)、無事件條文、再開條文、外部衍生條文；(a) 與其他條文未動。逐句語意對照（PRD 原文：`PRD:252`、`:253`、`:254`、`:248`；範本 T1～T4：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md:353–356`）：

| PRD AC | PRD 原意 | SOP 現文（座標） | 語意判定 |
|--------|----------|------------------|----------|
| AC-SI-03-1 (a) | 掌舵者指令 | 掌舵者明示要求啟動或再開（T1）（SOP:11） | 一致；T1＝範本「掌舵者直接立案新需求」 |
| AC-SI-03-1 (b) | 同一症狀第二次被記入觀察（經審查者確認相同） | 同一症狀第二次被記入觀察，且經審查者確認相同；P0 尚無 `attr.confirm`，以人工比對；確認者不得是立案者（SOP:12） | 一致；「確認者不得是立案者」有據於 PRD:268–269 的「審查者（≠歸因者／≠立案者）」；`attr.confirm` 為 PRD 內既有動詞 |
| AC-SI-03-1 (c) | 缺陷帳本新立 P≤2 未結列 | 缺陷帳本（`AutoSDD_Defect_Log.md`）新立 P≤2 未結列，即範本 T2；觀察帳本的 P1／P2 入帳不是本事件源，真缺陷依 AC-SI-04-2 升 DEF 後才成為 (c)（SOP:13） | 一致；事件源是缺陷帳本（範本 :354 的 T2、PRD:575），一審指出的「誤指觀察帳本」已消除，且補上與 AC-SI-04-2 的銜接 |
| AC-SI-03-1 (d) | 已採納工件的再開症狀命中 | 已採納工件的再開症狀命中；P1 起才有已採納工件，P0 無此事件源；觀察帳本 deferred／retired 列的再開症狀再被觀察到時走 (b)（SOP:14） | 一致；對象是已採納（promoted）工件，與 PRD:636 的 `status` 列（P1 動詞）一致，且把一審誤寫的情形改走 (b) |
| AC-SI-03-1 (e) | 容量事件（FR-SI-27） | 記憶索引、知識庫或偏好注入等有上限的儲存／載入面，用量達其上限的 `CAP_FRAC`（以 `si capacity` 現查為準，P0 尚無該動詞）；額度與 context 水位是守衛面的事，不是本事件源（SOP:15） | 一致；用語取自 PRD:379（AC-SI-27-1：`CAP_FRAC`、`si capacity`），明確排除額度與 context 水位 |
| AC-SI-03-1 後半 | 無日曆、版本號、覆蓋度、每 N 輪；`si status` 唯讀按需、視窗開場與收尾各跑一次 | SOP:17、:19（未動） | 一致 |
| AC-SI-03-2 | 零筆或零提案＝「無事件」；成效宣稱須指向症狀指標（§1.3） | 零事件記為「無事件」，不得寫成通過；…任何成效宣稱仍須指向症狀指標（PRD §1.3 的 M1～M5），觀察筆數、提案筆數不是成效（SOP:21） | 一致；F-11 (iii) 結案 |
| AC-SI-03-3 | 產出數量不構成再開理由；再開僅依範本 T1～T4 | 產出數量不構成再開理由；再開僅依範本該節 T1～T4，其中 T1 是掌舵者指令、T2～T4 是症狀條件，成立與否各自現查，不是裁決（SOP:23） | 一致；F-11 (i) 結案 |
| AC-SI-02-1 | 外部衍生不得單獨充當任何類別（M／P／R／D）提案的證據；須另有 ≥1 個內部來源（本 repo 檔案、指令 rc、掌舵者回報） | 此類列不得單獨充當任何類別（M／P／R／D）提案的證據，提案須另有 ≥1 個內部來源（本 repo 檔案、指令 rc、掌舵者回報）佐證（SOP:50） | 一致；F-11 (ii) 結案 |

```text
> python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts= -k "AT_003_1_1 or AT_032_1_1 or sop"      rc=0
.......                                                                  [100%]
7 passed, 35 deselected in 1.55s
```

註：`-k` 的 `sop` 子字串同時選中類別 `TestScopeAndSop` 的全部 7 個測試（含 AT-003-1-1 與 AT-032-1-1）。R25 的關鍵字判準仍抓不到語意偏離，這是 TCS 把語意留給 V8 的設計，本節即是該逐句對照；F-11 (iv)（V8 的時序倒置）仍為延後（帳本 078）。

### 8.4 F-03～F-05、F-07 複驗——通過

**生產碼（F-03）**：`git show 968e827b -- tools/lib/si_refs.py`（+15／−3）是一個 import 加上 `PureWindowsPath`、新增一個函式、替換 `orig_findings` 內的兩行判斷。新增 `_escapes_repo(rel)`：`win = PureWindowsPath(rel)`，回傳 `rel.startswith(("/", "\\")) or bool(win.drive) or ".." in win.parts`；`orig_findings` 改為 `target = None if _escapes_repo(rel) else repo / rel`，其餘判定（`target.is_file()`、錨點比對）原樣。審查結論：(1) 以 Windows 語法一律判（`/`、`\` 皆分隔符），同一份帳本在 Windows 與 POSIX 得同一判決，鐵律三的自問答案寫在 docstring；(2) `PureWindowsPath` 是不碰檔案系統的純路徑類別，沒有新增外部依賴；(3) 不誤殺正常路徑——`inside` 對照（repo 內的 `orig_inside.md`）仍 PASS。

**測試碼（F-04、F-05、F-07；現行座標，`tools/tests/test_selfimproving_check.py`）**：

- AT-001-3-E-4（`:1171–1236`）：誘餌檔放在逃出後真會解析到的位置（repo 外 `orig_outside.md`；repo 內 `orig_inside.md` 為正向對照）；六個形態子測試 `dotdot`、`absolute`、`rooted`、`rooted-backslash`、`drive-letter`、`inside`；磁碟機形態以 `PureWindowsPath("C:/…").as_posix()` 顯式建構（避開平台中立鎖對磁碟機字面的擋）；POSIX 分支另在 repo 內放 `C:/orig_outside.md` 誘餌，使同一輸入在兩個平台判決相同。
- AT-030-1-1（`:1750–1824`）：`assert_text_matches_json`（`:1716–1748`）以 `ITEM_RE`、`FINDING_RE` 逐行解析文字形態，與 `--json` 逐項比對首行、`overall=` 行、rc、各項 status、NE 項的 `blocking`／`nonblocking`、各項 finding 的 (subject, code) 集合；對 green、red、no-git 三種 repo 各一個子測試（F-04，並含 F-05 的 NE 字樣）。
- AT-001-1-E-5（`:915–972`）：JSON 的 `detail` 須以 `[warn]` 開頭，文字形態須含 `"\n  - VOLUME-WARN [warn] "`（F-05）。
- AT-001-2-1（`:1009–1044`）：子測試 `P2＋暴露=無`（第 9 列→`GUARD-P12-NO-EXPOSURE`）（F-05）。
- AT-003-1-1（`:1313–1370`）：恆真斷言換成對真 SOP 逐一刪去五個關鍵字（`掌舵者指令`、`第二次`、`P≤2`、`再開症狀`、`容量事件`）與 (a)～(e) 五個標記，`sop_startup_problems` 都必須非空（F-07 i）。
- AT-001-3-E-2（`:1108–1134`）：新增 `wrong-quote` 模式（引言故意寫錯）仍 PASS 且 `claim=valid`，直接證明引言不被比對（F-07 ii）。
- 模組暫存目錄（`:114–125`）：`setUpModule` 建、`tearDownModule` 清，並清空 `_BASE`、`_CHAIN`、歸零 `_COUNTER`；單獨 import 本模組不再於 `%TEMP%` 留 `si_check_*` 目錄（F-07 iii）。
- AT-030-2-1（`:1862–1971`）：以 `mock.patch.object` 攔截 `os.system`、`os.popen`（命中即拋 `OSError`，並斷言 `shells == []`），再加靜態正規式 `os\.(?:system|popen)` 掃描 `selfimproving.py` 與 `si_*.py`，含正反自證（F-07 iv）。

```text
> python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts= -k "AT_001_3_E_4 or AT_030_1_1 or AT_001_1_E_5 or AT_001_2_1 or AT_003_1_1 or AT_001_3_E_2 or AT_030_2_1"      rc=0
.......                                                [100%]
7 passed, 35 deselected, 18 subtests passed in 12.55s
> python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=      rc=0
..........................................      [100%]
42 passed, 97 subtests passed in 41.54s
> --collect-only：42 tests collected
```

**突變重放**（`qa_scg4\r2_mut_run.py`；把測試檔、`tools/selfimproving.py`、`tools/_stdio_utf8.py`、`tools/lib/si_*.py` 與測試唯讀存取的真檔複製到 `qa_scg4\mutroot2_<組別>_<時間戳>\`，只在複本上對 HEAD 碼做單點突變；repo 零改動）。複本基線：`42 passed, 97 subtests passed in 42.18s`（F 組）、`41.72s`（G 組）、`41.36s`（F 組補跑）。下表「七 AT」＝上列 `-k` 七個 AT 的 failed 數，「整檔」＝整個測試檔；failed 數含子測試失敗（pytest 9 以 `SUBFAILED(...)` 列出）。

| 突變 | 七 AT 的 failed | 整檔的 failed | 殺掉它的測試 | 結果 |
|------|-----------------|---------------|--------------|------|
| M-F 拿掉 R18 (c) 的「含 `..`」判斷（一審存活） | 1 failed（7 passed、17 subtests passed） | 1 failed（42 passed、96 subtests passed） | AT-001-3-E-4 的 `dotdot` | 殺 |
| M-F2 拿掉 rooted 與磁碟機代號判斷、只剩 `..`（對應一審「拿掉 is_absolute」；一審存活） | 3 failed（7 passed、15 subtests passed） | 3 failed（42 passed、94 subtests passed） | AT-001-3-E-4 的 `absolute`、`rooted`、`rooted-backslash` | 殺 |
| M-G 體積 warn 去掉 `[warn]` 前綴（一審存活） | 1 failed（6 passed、18 subtests passed） | 1 failed（41 passed、97 subtests passed） | AT-001-1-E-5 | 殺 |
| M-H 文字形態不印任何 finding 行（一審存活） | 4 failed（6 passed、15 subtests passed） | 4 failed（41 passed、94 subtests passed） | AT-001-1-E-5；AT-030-1-1 的 `text_form` green／red／no-git | 殺 |
| M-H2 NE 行不印 `blocking`／`nonblocking`（一審存活） | 3 failed（7 passed、15 subtests passed） | 3 failed（42 passed、94 subtests passed） | AT-030-1-1 的 `text_form` green／red／no-git | 殺 |
| M-N 守衛面 P1／P2 規則只認 P1（一審存活） | 1 failed（7 passed、17 subtests passed） | 1 failed（42 passed、96 subtests passed） | AT-001-2-1 的 `P2＋暴露=無` | 殺 |
| M-F2a 只拿掉磁碟機代號判斷（自訂） | 1 failed | 未跑 | AT-001-3-E-4 的 `absolute` | 殺 |
| M-F2b 只拿掉 rooted（開頭 `/` 或 `\`）判斷（自訂） | 2 failed | 未跑 | `rooted`、`rooted-backslash` | 殺 |
| M-F3 只拿掉開頭反斜線的 rooted 判斷（自訂） | 1 failed | 未跑 | `rooted-backslash` | 殺 |
| M-F0 整段還原成修復前的 `Path.is_absolute()`＋`..`（自訂） | 2 failed | 2 failed（42 passed、95 subtests passed） | `rooted`、`rooted-backslash`（即一審的 Windows 洞） | 殺 |
| M-H3 finding 行的 subject 與 code 對調（自訂） | 4 failed | 未跑 | AT-001-1-E-5；AT-030-1-1 三個 `text_form` | 殺 |
| M-W `check` 經 `os.system` 起行程（F-07 iv 對照；自訂） | 1 failed（6 passed、18 subtests passed） | 未跑 | AT-030-2-1 | 殺 |
| M-Q2 確認列改成要求引言含特定文字（F-07 ii 對照；自訂；編號加 2 以免與一審 §3 的 M-Q「retired 缺座標不再判」混淆） | 1 failed（7 passed、17 subtests passed） | 未跑 | AT-001-3-E-2 的 `wrong-quote` | 殺 |

共 13 個突變（一審六個存活突變加七個自訂）全數被殺，無存活（證據檔 `r2_mut_results_G.txt` 內，M-Q2 仍記為 M-Q）。誠實劃界：(1) M-F2a 在 Windows 由 `absolute` 殺，`drive-letter` 子測試對它沒有獨立鑑別力（它的誘餌檔得放在磁碟機根目錄，測試不寫磁碟機根）；POSIX 分支則以 repo 內的 `C:/orig_outside.md` 誘餌鑑別——POSIX 行為依測試設計與 `PureWindowsPath` 語意推斷，未在 POSIX 實跑（§8.11）。(2) 13 個突變是手選、非窮盡。

### 8.5 V2／V7／V9 重跑與寫入前的工作樹現查

```text
> python tools/selfimproving.py check --json     rc=0   wall=1.42s
{"overall": "PASS", "rc": 0, "fingerprint": "sha256:87b349b706f38fce6e99255c2a50ddc4f49ea7ba3c283f52451fff18e3bab394", …, "rows": 92, "items": [21 項], …}
  ref.obs PASS ; ref.def PASS ; ref.orig_notes PASS ; row.fixed_sha PASS ; row.coordinates PASS ; history.migration PASS（detail=claim=valid） ; history.row_mutated PASS ; params.keys／params.globs／params.coupling PASS ; ledger.volume PASS ; ledger.vacuity PASS
  ref.carrier_families NE（nonblocking；CARRIER-NOT-ESTABLISHED families=PROP-SI count=24）
> python tools/selfimproving.py check     rc=0   wall=1.17s
si-check rows=92 items=21 … overall=PASS rc=0 fingerprint=sha256:87b349b706f38fce6e99255c2a50ddc4f49ea7ba3c283f52451fff18e3bab394
> python -I r2_v2_independent.py（獨立於 tools/lib/si_*.py，依 TCS R9～R16 逐列重判）
file bytes=48315 lines=103 data_rows=92 CRLF=False BOM=False ; 27 個判定碼全部 0 筆 ; 列位元組 max=689、超過 700 的列數＝0
> Grep 「之後再看」於帳本：只命中檔頭〈規則〉的第 6 行（禁令敘述）
```

判準指紋與一審相同（`sha256:87b349b7…b394`），符合協定目錄零改動。`check` 牆鐘 1.42s、1.17s（含直譯器啟動），門檻 < 30s。

```text
> $env:AUTOSDD_PARALLEL_TESTS='1'; python tools/run_root_unittests.py      rc=0   wall=143.61s
unittest 數量下限釘選通過：發現 5426 個測試（下限 5326）
收集面盤存：92 支 test_*.py 檔／指紋 e550e12db2f5
[cpu_budget] root-unittest workers=18 source=cpu_budget
模組耗時排行（前 5，共 405 模組，平行模式，worker=18）：… test_selfimproving_check: 88.8s（第 2）…
派工摘要：worker=18｜S=2055.1s｜ideal=max(S/W, 最長單位)=114.2s（S/W-bound）｜loss=1.00x｜slot 利用率=99.9%
[skip census] tools/tests@win32 共 46 支：platform=42／tool-absence=0／env-disabled=4／structural-pair=0／debt=0／untagged=0／欠債型 4 支（目標 0）
真實 TEMP 圍籬：全套期間真實契約目錄（與 autosdd_quota.json 同目錄）下 autosdd_pace*.json 零變動（前 4／後 4 份；目錄 C:\Users\wuwei）；隔離根已建立並清除。
孤兒 console 普查：零增長（前 1／後 1）。
（輸出中以 FAIL／ERROR 開頭的行：0 行）
> python -m ruff check tools/selfimproving.py tools/lib/si_*.py（7 檔） tools/tests/test_selfimproving_check.py      rc=0
All checks passed!
> python AutoClaude/tools/check_loc_budget.py --json      rc=0
total=18625 baseline=17079 cap=20438 total_violation=False ; absolute_violations／tier_violations／special_violations／root_tools_violations 皆 len=0
> python -m pytest tools/tests/test_defect_id_reference_integrity.py -q -p no:xdist -p no:cacheprovider -o addopts=      rc=0
11 passed in 2.09s
> python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines      rc=0
# 淨額 119056→119056 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
# _REPIN_LOG_HISTORY_SHA256 = "94b2abd8d962b936ea56e404fcd42cceb92f381a9d23a4199c6c1418e4571c4d"   （與 Y4 的釘值相同）
> git status --short（根層全套、ruff、LOC、本節各項測試跑完之後）      （空）
```

V9（M 之後只追加）：

```text
> git log --numstat --format='COMMIT %h' f1d7660f..HEAD -- <ledger>      rc=0
COMMIT 622c83d2   11  0
COMMIT 4eb912d0   19  0
COMMIT 56ef5393   11  0
> git log -p --format='COMMIT %h' --unified=0 4eb912d0^..HEAD -- <ledger>      rc=0
  hunk：@@ -91,0 +92,11 @@（622c83d2）、@@ -72,0 +73,19 @@（4eb912d0）；刪除行數 0
```

判斷：自 N 起帳本只有三個 commit 動過，皆為單一 hunk 的純追加（11＋19＋11＝41 列，等於 92 減 N 時的 51 列），0 行刪改；`history.row_mutated` 為 PASS（機械憑證）；既有的 001～062 列零原地改寫。V7 其餘：凍結三檔 digest 與一審相同、`.claude` 與 `.github` 零改動、工作樹乾淨（§8.1）。護欄層重釘（Y4）以「根層全套 rc 0」與 `--print-guard-lines` 的 +0／漂移 0 驗證，未獨立重算 sha（§8.11）。NFR-P0-2：整檔 41.54s（本機）；根層平行 worker 內 `test_selfimproving_check` 為 88.8s（一審 81.0s；多了 11 個子測試與較多誘餌檔），門檻 180s，CI 端未驗。

### 8.6 逐 AT 單跑（姊妹檔 RTM §2 已更新）

重跑 TCS §2 的 42 個判定指令（`-k <底線形>`，各加 `-p no:xdist -o addopts=`）：42/42 皆為 `1 passed`、rc＝0、每個 `-k` 恰選到 1 個測試（腳本的非預期清單為空）。與一審相比只有四個 AT 的子測試數改變：AT-001-2-1（0→1）、AT-001-3-E-2（7→8）、AT-001-3-E-4（0→6）、AT-030-1-1（0→3）；子測試合計 86→97，與整檔 `97 subtests passed` 吻合。測試函式的行區間因 Y4 增加 93 行而位移，RTM §2 已全部重抽（座標以 HEAD `622c83d2` 為準）。

### 8.7 各 F 結案表

| 編號 | 一審 | 二審狀態 | 依據 |
|------|------|----------|------|
| F-01 | P2 | 已結案 | SOP:12–15 與 :21、:23、:50 逐句語意對照 PRD AC-SI-03-1／-03-2／-03-3 與 AC-SI-02-1 一致（§8.3）；`-k "AT_003_1_1 or AT_032_1_1 or sop"` 7 passed；帳本 081 `fixed@9fd15796` |
| F-02 | P2 | 已結案 | 063～068 六列更正列座標逐一可定位（§8.2）；`check` 仍綠；原列依 append-only 不動 |
| F-03 | P3 | 已結案 | `_escapes_repo` 平台中立；AT-001-3-E-4 增六個子測試；M-F、M-F2、M-F2a、M-F2b、M-F3、M-F0 全殺（§8.4）；帳本 082 `fixed@968e827b` |
| F-04 | P3 | 已結案 | AT-030-1-1 逐行解析並與 `--json` 的 (subject, code) 集合相等；M-H、M-H3 殺；帳本 083 |
| F-05 | P4 | 已結案 | `[warn]` 前綴、NE 的 `blocking`／`nonblocking`、守衛面 P2＋暴露＝無三處補斷言；M-G、M-H2、M-N 殺；帳本 084 |
| F-06 | P3 | 依裁決結案（流程） | 帳本 075 decided：Developer 任務書加「逐 AT 驗收字樣」；本輪仍由 QA 逐 AT 單跑補證（42/42）；無程式變更 |
| F-07 | P4 | 已結案 | (i) 恆真斷言換成關鍵字刪除鑑別；(ii) `wrong-quote` 對照（M-Q2 殺）；(iii) `setUpModule`／`tearDownModule`；(iv) 攔截 `os.system`／`os.popen`（M-W 殺）；帳本 085 |
| F-08 | P4 | 延後（接受） | 帳本 076 deferred，附可觀測再開症狀；P0 退出不依賴 |
| F-09 | P4 | 依裁決結案（附殘餘） | 帳本 077 decided：自本批起時間欄填事件實際時刻（可追溯者）。事件即入帳之列（063～068、081～085）的時刻與提交時刻相符；回補列（069～080、086～092）仍是批次入帳時刻，因事件時刻不可追溯，符合「可追溯者」條件；建議流程摩擦的交卷格式附事件時刻 |
| F-10 | P4 | 不動作（治理，請掌舵者過目） | Y4 的護欄層重釘再度走一次性例外名冊：R213 列精確淨額 2216→2318（名冊上限仍 5）、`_REPIN_LOG_FROZEN_PREFIX_LEN` 341→342、歷史 sha 重釘、接鏈列再度借用既有缺陷列的編號。機制本意即每次增列都得改精確值，但同標籤已連續第四列；屬主控與掌舵者裁決，QA 僅標示 |
| F-11 | P4 | (i)(ii)(iii) 已結案；(iv) 延後 | (i)(ii)(iii) 見 §8.3（SOP:21、:23、:50）；(iv) 帳本 078 deferred，附再開症狀 |
| F-12 | P4 | 延後（接受） | 帳本 079 deferred，附再開症狀 |
| F-13 | P4 | 依裁決結案 | 帳本 080 decided：下一份 TCS 的 §5.6 預留「CI paths 與 guard-total 站點」兩類連動檔；Y4 再度動到兩個 guard-total 站點，印證預留的必要 |
| F-14 | P4 | 不動作 | 同一審 |
| F-15（新） | P4 | 新發現，不阻斷 | 見 §8.8 |

統計：P1＝0、P2＝0、P3＝0；P4 殘餘 6 項（F-08、F-10、F-11 (iv)、F-12、F-14、F-15）。

### 8.8 二審新發現

| 編號 | 嚴重度 | 發現 | 座標 | 建議處置 |
|------|--------|------|------|----------|
| F-15 | P4 | 新列座標的可重查性殘餘兩處：(i) 帳本 082 的 `tools/lib/si_refs.py:125` 是修復前的行號，修復後該行成了 `_escapes_repo` docstring 的結尾引號（083、085 已標「（修復前）」，082 漏標；以 `fixed@968e827b` 的父提交可還原到原句）；(ii) 帳本 058 的座標含省略號（`D:\Users\wuwei\AppData\...\e501_count.py`），指向待刪的 repo 外殘留檔——一審 F-02 已列為易失，本輪現查該檔仍在 `D:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\f3ead132-29b1-418c-97d9-35868ab11c70\scratchpad\selfimproving\e501_count.py` | 帳本 082、058 的「證據座標」欄；`tools/lib/si_refs.py:125`（現為 docstring 結尾） | 不阻斷。若要補，追加更正列（`rel=corrects:`），把 082 的座標改成以符號命名的形式（`tools/lib/si_refs.py` 的 `_escapes_repo`、`orig_findings`），058 待殘留檔刪除後以更正列註記；往後帶行號的座標一律標「（修復前）」或改用符號名 |

本輪沒有發現 P1～P3；也沒有為找新缺陷而對修復範圍之外的面構造變體（只做一審存活突變的重放，加七個與修復直接對應的對照突變）。

### 8.9 二審判定

**PASS**——理由：一審的兩個阻斷項 V3 (9)（F-02）與 V8（F-01）複驗通過；V2、V7、V9 重跑全綠，V1、V4、V6 的輸入未變且機械憑證仍綠（`history.migration`＝`claim=valid`、`params.*` PASS、判準指紋不變）；一審六個存活突變全數被殺，P3 以上發現全數結案。

TCS 末段〈SCG-4 通過標準〉逐項（二審）：

| 驗證項目 | 二審結果 |
|---------|----------|
| AC → AT 100% 映射 | 通過：19/19（TCS 凍結，AT 仍 42 個；`rtm_data.py` 重抽驗證） |
| AT 格式可自動化 | 通過：42 個測試函式名含其底線形，逐 AT 單跑皆 `1 passed` |
| 負向測試覆蓋 | 通過：每個 AC 至少一個負向；突變重放 13/13 被殺，一審 22 個手選突變的六個存活者現已全殺 |
| 邊界值測試 | 通過：一審已驗的邊界不變；新增 R18 (c) 六形態與 R15 的 P2＋暴露＝無 |
| 測試資料規格完整 | 通過：誘餌檔放在逃出後真會解析到的位置（F-03），測試資料不再只驗「不存在的路徑報不存在」 |
| 實跑檢核 V1～V9 全部有逐字輸出證據 | 通過：V3 (9)、V8 見 §8.2、§8.3；V2、V7、V9 見 §8.5；V1、V4、V6 見 §8.1、§8.5（輸入不變、憑證仍綠） |

給主控的收尾建議（非阻斷）：
1. 本檔檔頭「判定: FAIL」與 §5 是一審原文（本棒依任務書不改一審內文）；建議收尾 commit 時於檔頭補一行指向本節。
2. SOP 檔頭「狀態」列仍寫「P0 草稿（Developer 棒起草，待 SCG-4 QA 逐項對照 PRD 檢核）」；SCG-4 通過後建議改為已通過並附本報告座標（SOP 不在凍結集合內）。
3. 本節 §8.10 的流程摩擦與 F-15 請於 SCG-4 收尾前入帳（本棒不寫帳本）；FSM 閘門動作（`gate --gate PR_REVIEW --result PASS`）由主控執行，本棒未碰 FSM。
4. 帳本 058 所指的 repo 外殘留檔 `e501_count.py` 仍待掌舵者刪除。

### 8.10 流程摩擦（本棒二審；每項一句症狀加一個座標，請主控於 SCG-4 收尾前入帳）

1. 系統提示（auto mode）本棒中途再度要求優先用 Bash，與根 `CLAUDE.md`〈鐵律一〉衝突；全程仍用 PowerShell／Read／Grep／Glob／Edit／Write（OBS-SI-011 再復發）；座標：根 `CLAUDE.md`〈鐵律一〉。
2. `python -I` 腳本的中文 `print`（逐 AT 單跑腳本的結尾訊息）在 PowerShell 主控台以 cp950 顯示成亂碼，需改寫檔再用 Read 讀（OBS-SI-072、OBS-SI-029 再復發）；座標：`qa_scg4\run_each_at.py` 末行。
3. pytest 9.1.1 內建 subtests：失敗的子測試在 `-rf` 摘要以 `SUBFAILED(...)` 列出而非 `FAILED`，且計入「N failed」；突變重放腳本一開始只收 `FAILED` 前綴而漏列子測試失敗名，補收 `SUBFAIL` 才完整；座標：`qa_scg4\r2_mut_run.py` 的 `pytest()`。
4. 測試檔每增減行數，RTM §2 的「行區間」就全數過期（Y4 增 93 行使 AT-001-1-1 以下的區間全部位移）；座標：RTM §2；建議 RTM 座標附 commit sha（本棒已註明以 HEAD `622c83d2` 為準）。
5. `.venv` 是 Python 3.11.9，QA 腳本多次撞「f-string 運算式不得含反斜線」，每次改成先算值再格式化；座標：`qa_scg4\r2_rows.py`。
6. `Grep` 對含長理由的 skip 明細行回「[Omitted long matching line]」，改用 `-o` 視窗或 Read 取片段（OBS-SI-071、OBS-SI-033 再復發）；座標：`qa_scg4\r2_root_suite.txt` 第 81 行。
7. `Grep` 的 `glob` 參數帶含目錄分隔符的大括號展開，回無結果的假陰性，改拆成多次單一 glob（OBS-SI-070、OBS-SI-046 再復發）；座標：`docs/06_quality/TCS-PREREVIEW-SelfImproving-P0-20261019.md` 的流程摩擦 #3。

### 8.11 未查證／未做（二審）

- **macOS／POSIX 與 GitHub Actions 仍未實跑**：F-03 的 POSIX 行為依測試的 `os.name` 分支設計與 `PureWindowsPath` 語意推斷，未在 POSIX 實跑；NFR-P0-2 的 CI「整個測試檔小於 180 秒」未驗（本機整檔 41.54s；根層平行 worker 內 88.8s）。
- **SD 修復棒交卷原文未取得**：086～092 與 SD 交卷七項只驗了列本身通過 `check` 且座標可定位，逐項對帳未驗。
- **護欄層重釘（Y4）未獨立重算**：`test_adr_xplat001_c1c2_lock.py` 的名冊、前綴長度、歷史 sha 與兩個 guard-total 站點，只以根層全套 rc 0 與 `--print-guard-lines` 的 +0／漂移 0 驗證，未手算 sha。
- **突變重放為 13 個手選突變，非窮盡**；`drive-letter` 子測試在 Windows 上對 M-F2a 沒有獨立鑑別力（見 §8.4 劃界）。
- **repo 內符號連結逃逸未探**：本機無建立符號連結的權限（根層全套的 skip 明細有 `[WinError 1314]`），且 R18 (c) 只規範路徑字面。
- **063～092 的語意只驗到座標可定位與 `check` 綠**，未逐列回溯各列所述事實。
- 一審 §7 的其餘項目（`lint-imports`、AutoClaude pytest、`ci-gate`、`check` 的邊界探測、T 之前與 M 之後的紅燈狀態重現）本輪仍未做。

### 8.12 勘誤（對一審內文）

本輪沒有發現一審的事實性錯誤。僅座標需註記：一審 §3 抽查表與 §4（F-04、F-05、F-07）所引測試檔行號是一審當時 X 版的座標，Y4 後已位移，現行座標見 RTM §2（`git show 56ef5393:tools/tests/test_selfimproving_check.py` 可還原一審所指的行）；一審 §2 的 `rows=62` 等數字是 X 版的量測，現行為 92 列（§8.5）。

### 8.13 證據檔（scratchpad，不入庫）

`qa_scg4\` 下：`run_cmd.py`、`r2_rows.py/.txt`、`r2_coord_exist.py/.txt`、`r2_transcript.py/.txt`、`r2_transcript2.py/.txt`、`r2_y4_refs.diff`、`r2_y4_tests.diff`、`r2_y4_lock.diff`、`r2_y4_stat.txt`、`r2_sop_run.txt`、`r2_k7_run.txt`、`r2_full_at.txt`、`r2_mut_run.py`、`r2_mut_results_F.txt`、`r2_mut_results_F_names.txt`、`r2_mut_results_G.txt`、`r2_check_json.txt`、`r2_check_text.txt`、`r2_v2_independent.py/.txt`、`r2_root_suite.txt`、`r2_ruff.txt`、`r2_loc.txt`、`r2_defid.txt`、`r2_print_guard.txt`、`r2_v9_logp.txt`、`r2_v9_numstat.txt`、`r2_v9_numstat_fromN.txt`、`each_at.json/.txt`（二審重跑）、`each_at_r1.json`（一審備份）、`rtm_data.json`、`rtm_at_table2.md`、`r2_subtest_diff.txt`。

---

## §9 三審（搬遷複驗）

**三審日期**: 2026-10-19（本節寫入時刻 18:12 +08:00）　**審查者**: 同一位 SCG-4 獨立 QA 棒（Sonnet 5.5；未參與搬遷的實作、規格修訂與落點規範起草）
**複驗基準**: HEAD `3c94b53381a420ee70cba4dec01598342b124c0c`（＝Z2）；搬遷 commit Z＝`e83ebb14ddb2158df43aab514afa17dccf749861`（17:43:32），入帳 commit Z2（17:45:15）；二審報告 commit `faebb596`（17:25:00）為本輪的追加基準。FSM：P0 鍵 `PR_REVIEW`、PRD 鍵 `SPEC_FROZEN`
**事由**: 二審 PASS 後，掌舵者裁決「現在就搬」並指令新模組不得散落、規範寫進 CLAUDE.md 與規格。主控與 SD 棒把程式碼自 `tools/lib/si_*.py` 搬成套件 `tools/lib/selfimproving/`（入口 `tools/selfimproving.py` 與指令字面不變），同步修訂 PRD、TCS、`params.json`、兩支 compat-ci 的 `paths`，新增落點規範 SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md` 與根 `CLAUDE.md`〈根層模組落點〉節，帳本追加 101～105。
**三審判定**: **PASS**（P1＝0、P2＝0；新發現 1 個 P3〔F-16〕與 5 個 P4〔F-17～F-21〕，皆不阻斷，見 §9.7）。規格修訂只動路徑字面、落點表、勘誤與 18 處 PRD digest，AT 數、R 規則語意、判定碼不變（§9.2 機械證明）；程式搬遷不改行為（§9.4：整檔 42 passed、根層全套 rc 0、鏡像突變全殺）；落點規範與現況、根 `CLAUDE.md`、PRD §9 大體一致（§9.3，不一致處入 F-19）。**一審、二審的結論與內文未改動；§5、§8 的判定是各自當時的歷史判定。**

> 方法聲明同前：凡寫「通過」者皆附本回合真跑的指令與輸出，做不到的寫「未驗」（§9.10）。稽核與突變腳本放在 scratchpad `qa_scg4\`（`r3_` 前綴，不入庫）；repo 內除本檔與姊妹檔外零改動（§9.5 寫入前現查）。Windows 上只用 PowerShell／Read／Grep／Glob／Edit／Write，Python 一律 `.venv`。FSM 只經 `FSMRuntime` 的 `show --must-exist` 唯讀取用（兩個遙測旗標顯式設 0），不直接讀寫 `FSM-STATE-*.yaml`。工具輸出若帶表情符號，下文逐字引用時略去行首符號。已知事項（主控已知、不 amend）：Z2 的 commit 訊息把 OBS-SI-101 稱為「更正列 rel=corrects:OBS-SI-001」，實際該列沒有 `rel=` 標記（是一筆 `decision` 列），以帳本內容為準，`check` 為綠。

### 9.1 輸入快照

```text
> git rev-parse HEAD                              3c94b53381a420ee70cba4dec01598342b124c0c   rc=0
> git status --short                              （空；行數 0）   rc=0
> git diff --name-only ; git diff --cached --name-only        （皆空）
> git diff --stat faebb596..HEAD -- .claude       （空）；`.github` 只動兩支 compat-ci（見下）
> git diff --name-status faebb596..HEAD           （20 檔：Z 19 檔＋Z2 帳本 1 檔）
  M .github/workflows/macos-compat-ci.yml          M docs/01_requirements/SelfImproving_PRD.md
  M .github/workflows/windows-compat-ci.yml        A docs/02_architecture/Root_Layout_and_Module_Placement.md
  M CLAUDE.md                                      M docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md
  M docs/04_planning/AutoSDD_improving_112.md      M docs/06_quality/CrossPlatform_R145_Scan_Findings.md
  M docs/06_quality/SelfImproving_Observation_Ledger.md   M docs/06_quality/SelfImproving_Protocol/params.json
  A tools/lib/selfimproving/__init__.py            R097 si_check.py→selfimproving/check.py    R100 si_git.py→git.py
  R096 si_history.py→history.py                    R098 si_ledger.py→ledger.py                R099 si_params.py→params.py
  R097 si_refs.py→refs.py                          R098 si_rows.py→rows.py
  M tools/selfimproving.py                         M tools/tests/test_selfimproving_check.py
> git diff --shortstat faebb596..HEAD             20 files changed, 176 insertions(+), 80 deletions(-)
> Get-FileHash -Algorithm SHA256（現檔）
  PRD  fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de   （1019 行）
  TCS  6f7e24e73dd29b729933be1a6edb58b11f5d7eb06fc047a02c7bb89acb05996f   （1484 行）
  SOP  deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2   （研究方法 SOP；與一、二審相同）
```

範圍判斷：沒有碰 `.claude/**`、研究方法 SOP；`.github` 只動兩支 compat-ci 的 `paths`（四處 `tools/lib/si_*.py`→`tools/lib/selfimproving/**`）；PRD 與 TCS 的修訂走 FSM（§9.2）；`tools/tests/` 只動 `test_selfimproving_check.py`（鎖檔未動）。

### 9.2 規格一致性（任務 1）——通過

**機械證明**（`git show e83ebb14^:<檔>` 對 `e83ebb14:<檔>`，`r3_tcs_invariants.py`）：

```text
TCS lines before=1475 after=1484 HEAD=1484 (after==HEAD: True)
AT ids before=42 after=42 same_list=True unique=42
R bullets before=26 after=26 same_keys=True changed=['R26']
判定碼表 lines before=49 after=49 identical=True
判定碼 token 集合 before=50 after=50 same=True
AT gherkin 區塊 before=42 after=42 changed blocks=['AT-003-1-1', 'AT-029-2-1', 'AT-030-2-1', 'AT-032-1-1']
TCS hunks=13 ; added=35 removed=26
old PRD digest occurrences before=18 after=0 ; new digest occurrences after=18
PRD lines before=1019 after=1019 ; hunks=3 added=3 removed=3
PRD **AC/FR/NFR-SI** 條目 token 數 before=97 after=97 same=True
```

「changed blocks」的 AT-032-1-1 是假訊號：該腳本把最後一個 AT 區塊延伸到檔尾，§5.6 的兩行與新增的勘誤節都落在它之後（gherkin 自身未變）；hunk 座標逐一對帳如下，沒有任何 hunk 落在 R1～R25 條文、判定碼表（:161–207）、其餘 39 個 AT 區塊內（真正改到的 gherkin 區塊只有 AT-003-1-1、AT-029-2-1、AT-030-2-1 三個）。

| TCS hunk（舊行號） | 內容 | 性質 |
|--------------------|------|------|
| :48 | D4 列：`tools/lib/si_*.py`→`tools/selfimproving.py`（入口薄殼）、`tools/lib/selfimproving/*.py`（套件，見勘誤） | 路徑字面 |
| :159 | R26：掃描對象改為 `tools/lib/selfimproving/*.py`（含 `__init__.py`）；禁用字樣、rc 3 規則不變 | 路徑字面 |
| :244 | NFR-P0-5：路徑改套件；「拆 `si_*.py` 模組」改「在套件內依職責拆新模組」 | 路徑字面 |
| :255～275（5＋10＋2＋1 列） | 增量追溯表的 PRD digest `9c571827…`→`fbca6bc9…`，共 18 處（舊 digest 剩 0 處） | digest 回填 |
| :684、:936、:1001 | AT-003-1-1 Given、AT-029-2-1 的四項 glob、AT-030-2-1 的 AST 子句（本地模組認 `lib`／`lib.selfimproving.*`、套件內相對 import 視為本地） | 路徑字面（AST 子句是實作 R8 (b) 的判準措辭，R8 條文本身未動） |
| :1392、:1400 | §5.6 唯讀存取清單與新增清單的路徑 | 路徑字面 |
| +1476～1484 | 〈搬遷勘誤〉節（事由、改了什麼、凍結紀錄、:1353 合成座標不改） | 勘誤 |

PRD 三個 hunk（`+3／−3`）：NFR-SI-02-1 實體 glob (iv) 的 `tools/lib/si_*.py`→`tools/lib/selfimproving/**`（:415）；§9.1 開頭加「模組落點表」一段（:559）；C4 列的落點改成「入口薄殼＋套件（`ledger`、`rows`、`git`、`refs`、`history`、`params`、`check`）」並引 SSOT §2（:565）。FR／AC／NFR 條目 id 97 個全未動，元件數 15、各階段與閘門欄未動。

**FSM**（只經 `FSMRuntime` 唯讀；`python scripts/sdd_version.py` → `AISDLC_SDD_v0.30`）：

```text
> $env:SDD_STATE_DIR='<根>\build\reports\fsm'; $env:SDD_ENABLE_RULE_FIRE_TELEMETRY='0'; $env:SDD_ENABLE_RULE_CATCH_TELEMETRY='0'
> Push-Location AISDLC_SDD\AISDLC_SDD_v0.30
> python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project monorepo-si-p0-ledger --must-exist     rc=0   （單一 JSON）
> python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project monorepo-selfimproving --must-exist    rc=0
  monorepo-si-p0-ledger  : current_state=PR_REVIEW  updated_at=2026-10-19T09:45:21+00:00  decision_trace=21 筆  frozen_stages=2（Stage-1、Stage-2）
  monorepo-selfimproving : current_state=SPEC_FROZEN updated_at=2026-10-19T09:30:36+00:00  decision_trace=16 筆  frozen_stages=3（皆 Stage-1）
```

P0 鍵（`monorepo-si-p0-ledger`）decision_trace 末六筆（UTC）：

| # | 時間 | 轉換（trigger） | reason 摘要 |
|---|------|-----------------|-------------|
| 15 | 08:04:05 | PR_REVIEW→IMPLEMENTATION（gate_fail） | SCG-4 一審 FAIL（P2 F-01、F-02…），修復分工 |
| 16 | 08:36:54 | IMPLEMENTATION→PR_REVIEW（cli_manual） | 一審修復完成，Y1～Y5 |
| 17 | 09:23:22 | PR_REVIEW→RTM_VERIFY（gate_pass） | `PR_REVIEW PASS` |
| 18 | 09:25:07 | RTM_VERIFY→IMPLEMENTATION（cli_manual） | 掌舵者 2026-10-19 裁決「現在就搬」：程式碼自 `tools/lib/si_*.py` 搬成 `tools/lib/selfimproving/`（入口不變）；SD 棒改 import／測試／重釘，主控改 params、compat-ci paths、落點規範與根 CLAUDE.md；TCS 路徑字面搬遷後進 SPEC_AUDIT 修訂，再回 PR_REVIEW 三審 |
| 19 | 09:42:13 | IMPLEMENTATION→SPEC_AUDIT（cli_manual） | 規格修訂（非缺陷）：TCS 的路徑字面（D4／R26／NFR-P0-5／AT-003-1-1 Given／AT-029-2-1 四項 glob／R8 (a) 本地模組規則／§5.6）與 18 處 PRD digest 須同步並補搬遷勘誤；AT id、數量、判定碼不變 |
| 20 | 09:45:21 | SPEC_AUDIT→PR_REVIEW（cli_manual） | 修訂完成回三審：commit Z `e83ebb14`、Z2 `3c94b533`；**修訂後 TCS digest `sha256:6f7e24e73dd29b729933be1a6edb58b11f5d7eb06fc047a02c7bb89acb05996f`（1484 行；Stage-2 原 `6c4e28ed…` 保留為歷史）**、PRD 重凍 `fbca6bc9…`；主控親跑 42 AT、`check` rc 0、+0、全套 rc 0 5426、CI paths 49 passed；QA 三審聚焦搬遷 |

PRD 鍵（`monorepo-selfimproving`）decision_trace 末四筆（UTC）：#12 09:23:22 `SPEC_FROZEN→SPEC_DRAFTING`（掌舵者裁決，sid 與 line 5507 提問、互動選項「現在就搬」、後續指令；PRD §9.1 C4 與 NFR-SI-02-1 實體 glob 改套件路徑並引落點規範；改完 SCG_VALIDATION 單項複核後重凍）；#13 09:30:36 `SPEC_DRAFTING→SCG_VALIDATION`（路徑字面與落點表，語意不變；「QA 三審複核 PRD diff」）；#14 同秒 `SCG_VALIDATION→HUMAN_PENDING`（gate_pass）；#15 同秒 `HUMAN_PENDING→SPEC_FROZEN`（`Stage-1 重凍（第三次）`）。`frozen_stages` 末筆（第 3 筆，`frozen_at` 09:30:36）：

```text
PRD  sha256:fbca6bc905fe85b6555d40b804c2e8adcc373a93f25bf8f06acdf9a0a06f11de   ＝ Get-FileHash 現檔（逐字相同）
SOP  sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2   ＝ Get-FileHash 現檔
approved_by：掌舵者（本人互動裁決，sid f3ead132-… line 5507／5524／5565；主控執行）
```

判斷：兩鍵的 decision_trace 都有對應理由，且與 Z 的 commit 訊息、TCS 勘誤的流程描述（`PR_REVIEW→RTM_VERIFY→IMPLEMENTATION→SPEC_AUDIT→PR_REVIEW`）逐段吻合；P0 鍵 #20 記載的 TCS digest 等於現檔；PRD 鍵末筆 digest 等於現檔。PRD 鍵的 `SCG_VALIDATION PASS`（#14）與進入該態（#13）、重凍（#15）在同一秒記錄，獨立複核落在凍結之後；#13 的 reason 已明載「QA 三審複核 PRD diff」，本節即該複核——PRD diff 只有上列 3 行、語意不變，複核通過。兩項殘餘入 F-16（授權座標）與 F-17（P0 鍵凍結紀錄與現檔不符）。

### 9.3 落點規範（任務 2）——大體通過（不精確處入 F-19）

SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md`（71 行）§2「根層模組落點表」12 格逐格對 SelfImproving 現況與磁碟（`r3_layout_exist.py`、`Get-ChildItem`、`git ls-files`、`git grep`）：

| §2 格 | SelfImproving 的填寫 | 磁碟核對 |
|-------|----------------------|----------|
| 函式庫（成套件、`__init__.py` 一句用途、依職責分檔、套件內相對 import、不互 import 他套件） | `tools/lib/selfimproving/`：`__init__.py`（73 位元組，一句用途的 docstring）＋7 個職責檔（`ledger`、`rows`、`git`、`refs`、`history`、`params`、`check`），皆 `git ls-files` 有追蹤 | 通過：套件內 `from . import`／`from .x import` 全為相對 import；對 `tools/lib/selfimproving` 用 `git grep -E` 搜尋以 `from lib` 或 `import lib` 起頭的行（正規式以 `\b` 收尾）零命中，套件不 import 任何其他 `tools/lib` 模組；`tools/lib/__init__.py` 不存在（與 SSOT §1 敘述相符）；`tools/lib/si_*` 殘留 0 檔 |
| 指令入口（薄殼、不含判準、指令字面不變） | `tools/selfimproving.py`（80 行：argparse、`_stdio_utf8`、`from lib.selfimproving import check`，呼叫 `check.*`）；`python tools/selfimproving.py check` 照跑，AT-030-1-1 的子行程案（cwd 為誘餌目錄）綠 | 通過 |
| 量測探針 `tools/probe/<module>_*.py` | P0 無；PRD 與 SSOT §3 皆標 P1 的 `tools/probe/selfimproving_measure.py` | 不存在（已明標 P1，非缺漏） |
| 測試 `tools/tests/test_<module>_*.py` | `tools/tests/test_selfimproving_check.py` | 通過 |
| 執行期協定資料 `docs/06_quality/<Module>_Protocol/` | `docs/06_quality/SelfImproving_Protocol/{params.json,metrics.md}` | 通過 |
| 帳本與附註檔 | `docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/05_development/SelfImproving_Observation_Ledger_notes.md` | 通過 |
| 需求／設計（PRD §9 必附落點表） | `docs/01_requirements/SelfImproving_PRD.md`，§9.1 已附（散文形態） | 通過（形態與兩格額外項見 F-19） |
| 測試契約 `TCS-<Module>-<Phase>-<YYYYMMDD>.md` | `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`；§5.6 檔案集合與本表一致 | 通過 |
| 運作 SOP | `docs/05_development/SelfImproving_Operations_SOP.md`、`SelfImproving_Research_Methodology_SOP.md` | 通過 |
| 審查／RTM | `docs/06_quality/SCG4-REVIEW-SelfImproving-P0-20261019.md`、`RTM-SelfImproving-P0-20261019.md`、`TCS-PREREVIEW-SelfImproving-P0-20261019.md`、`SCG0-REVIEW-SelfImproving-20261019.md` | 存在；但 SSOT 的審查報告樣式 `SCG<n>-REVIEW-<Module>-<YYYYMMDD>.md` 漏 `<Phase>`，`SCG4-REVIEW-…-P0-…` 對不上（F-19） |
| CI 接線（compat-ci 兩支 `paths`） | 兩支 workflow 的 push 與 pull_request 共四處皆含 `tools/lib/selfimproving/**` 與 `tools/selfimproving.py`，無殘留 `tools/lib/si_*` | 通過（§9.4 獨立解析 YAML） |
| 不可進化面 | `params.json` 的 `non_evolvable_globs` 含 `tools/lib/selfimproving/**`，PRD NFR-SI-02-1 (iv) 同步 | 通過（`params.globs` PASS；V6 重算 25＝25；鏡像突變 D1～D3 殺） |

§3「既有模組登記表」6 列、§1「目錄地圖」的路徑逐一檢查：§3 全部存在，唯一缺的是已標 P1 的 `tools/probe/selfimproving_measure.py`；§1 有一處路徑錯誤——`tools/git-hooks/`、`tools/act/` 列的權威指引寫 `tools/install_git_hooks.*`，該檔不存在於根層 `tools/`，實檔在 `AutoClaude/tools/install_git_hooks.ps1` 與 `.sh`（F-19）；`build/`、`logs/`、`checkpoints/`、`.act-runs/` 在本機皆存在。

**根 `CLAUDE.md`〈根層模組落點〉（:27–33）對 SSOT**：只導航不複寫——SSOT 路徑連結、新模組落點（函式庫成套件、入口薄殼、探針、測試、協定資料、帳本、規格依編號制）、「PRD §9 必附模組落點表、對不上先改 SSOT」「compat-ci `paths`、`non_evolvable_globs`、棘輪重釘、CI paths 覆蓋鎖同一 commit 收齊」「子專案內的模組不往根層放」「首例＝SelfImproving」逐點對 SSOT §2、§4 第 1 與 3 條、§2 末段，無矛盾；略寫了「架構決策 ADR 放 `docs/02_architecture/`」一項（導航節的省略，不是矛盾）。

**PRD §9.1 落點表對 SSOT §2**：函式庫、入口、探針、測試、協定資料、帳本（附註檔）、規格與 SOP 依編號制、審查與 RTM 皆一致；多出兩格——事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl`（機器寫的 JSONL，§2 的帳本列是人寫的 `<Module>_<Kind>_Ledger.md`）與提案內容檔 `docs/06_quality/SelfImproving_Proposals/`——在 SSOT §2 沒有對應列，而 SSOT §4 第 1 條要求「PRD 元件表每一列的路徑都能對上 §2 的某一格；對不上＝先改本檔」（F-19）。

### 9.4 程式面（任務 3）——通過

```text
> python tools/selfimproving.py check --json      rc=0   wall=1.25s
  overall=PASS rc=0 rows=105 items=21 fingerprint=sha256:751d4c3df047d35ce6164679bbea4884705d3e1f63d95572a5622d734a7503ca
  fingerprint_parts: manifest=daf2826f…c45b metrics_rev=1 check_rules_rev=1
  params.globs PASS ; params.keys PASS ; params.coupling PASS ; ref.obs PASS ; ref.def PASS ; ref.orig_notes PASS ; row.fixed_sha PASS
  history.migration PASS（claim=valid）; history.row_mutated PASS ; ledger.volume PASS ; ledger.vacuity PASS
  ref.carrier_families NE（nonblocking；CARRIER-NOT-ESTABLISHED families=PROP-SI count=24）
> python tools/selfimproving.py check             rc=0   wall=1.27s   si-check rows=105 items=21 … overall=PASS rc=0
> python -m pytest tools/tests/test_selfimproving_check.py -q -p no:xdist -o addopts=      rc=0
  42 passed, 97 subtests passed in 40.79s          （--collect-only：42 tests collected）
> … -k "AT_003_1_1 or AT_031 or AT_030_2_1"        rc=0   9 passed, 33 deselected, 30 subtests passed in 10.23s
> … -k "AT_003_1_1 or AT_029_2_1 or AT_030_2_1"    rc=0   3 passed, 39 deselected in 1.85s
> python -m ruff check tools/selfimproving.py tools/lib/selfimproving/*.py（8 檔）tools/tests/test_selfimproving_check.py    rc=0   All checks passed!
> python AutoClaude/tools/check_loc_budget.py --json    rc=0
  total=18625 baseline=17079 cap=20438 total_violation=False ; absolute／tier／special／root_tools_violations 皆 len=0
  guard_taxonomy 194 項（二審 193＋新增 `__init__.py`）；selfimproving 相關 9 項（入口＋套件 8 檔）；`tools/lib/` 前綴歸 guardrail_lib ≤ 400
> Push-Location AISDLC_SDD ; python -m pytest scripts/tests/test_ci_paths_cover_root_consumers.py -q -p no:xdist      rc=0   49 passed in 15.90s
> python tools/check_ntfs_paths.py                rc=0   NTFS 檔名檢查通過（29269 個 tracked 路徑，0 違規；最長 142 字元）
> git status --short ; git diff --name-only ; git diff --stat -- .claude     （皆空；每項測試跑完之後再查一次仍為空）
```

判準指紋由二審的 `87b349b7…` 變為 `751d4c3d…`：協定目錄的 `params.json` 改了一個 glob 鍵，`manifest` 隨之變；`metrics_rev`、`check_rules_rev` 不變，符合「指紋只隨判準變」。

**CI paths 覆蓋鎖不只看綠燈**：(1) 獨立解析兩支 compat-ci 的 YAML（`yaml.safe_load`；`on.push.paths` 與 `on.pull_request.paths`，190／191 條）——四處皆含 `tools/lib/selfimproving/**` 與 `tools/selfimproving.py`，殘留 `tools/lib/si_*` 為 0，入口、套件 8 檔、測試檔皆被某條 pattern 匹配；(2) 匯入該鎖的 `_consumed_root_paths(tools/tests)`：它掃出的 281 個消費檔包含入口與套件全部 8 檔（BFS 能解 dotted from-import 與相對 import），把 `tools/lib/selfimproving/**` 自 paths 拿掉（記憶體內重算，`r3_lock_red.py`）後，兩支 workflow 各列出套件 8 檔未覆蓋（拿掉 `tools/selfimproving.py` 則列出入口），即該鎖的「消費檔 ⊆ paths」斷言會紅——SSOT §2「漏列即紅」對程式碼路徑成立；(3) 但它**看不到**測試以 `ROOT / "docs/…"` 消費的四個資料／文件檔（`params.json`、`metrics.md`、SOP、PRD），兩支 compat-ci 的 `paths` 也沒列它們（先例：`FiveQuestion_Audit_Protocol/params.json` 有列）；`root-infra-ci.yml` 無 `paths` 過濾、恆跑，Linux 側仍覆蓋（F-21 (iii)）。

**鏡像突變**（`r3_mut_run.py`：把測試檔、入口、`_stdio_utf8.py`、套件 8 檔、SOP、`params.json`、`metrics.md`、PRD、根 `CLAUDE.md`、`.claude/settings.json` 複製到 `qa_scg4\mutroot3_<時間戳>_<代號>\`，只在複本上突變；repo 零改動）。複本基線：整檔 `42 passed, 97 subtests passed in 40.75s`；`-k "AT_003_1_1 or AT_029_2_1 or AT_030_2_1 or AT_031"` 為 `10 passed, 32 deselected, 30 subtests passed in 10.21s`。下表 failed 數取後者：

| 突變 | failed | 殺掉它的測試 | 結果 |
|------|--------|--------------|------|
| S1 `refs.py` 加 `import socket` | 1 | AT-030-2-1 | 殺 |
| S2 `check.py` 加 `time.sleep` 引用 | 1 | AT-003-1-1 | 殺 |
| S3 `git.py` 加 `os.system` 呼叫 | 1 | AT-030-2-1 | 殺 |
| S4 `rows.py` 加 `write_text` | 1 | AT-030-2-1 | 殺 |
| S5 `ledger.py` 加 `import yaml`（非標準庫） | 1 | AT-030-2-1 | 殺 |
| S6 對照：`history.py` 加 stdlib import 與套件內相對 import | 0 | — | 綠（合法寫法不誤殺） |
| S7 套件新增檔 `extra.py` 含 `import socket` | 1 | AT-030-2-1 | 殺（glob 涵蓋新檔） |
| S8 子套件 `sub/inner.py` 含 `import socket` | 0 | — | **未偵測**（`*.py` 非遞迴；邊界，見 F-21 (ii)） |
| D1 `params.json` 拿掉 `tools/lib/selfimproving/**` | 2 | AT-029-2-1、AT-031-1-1 | 殺 |
| D2 `params.json` 改回舊字面 `tools/lib/si_*.py` | 2 | AT-029-2-1、AT-031-1-1 | 殺 |
| D3 PRD 的 NFR-SI-02-1 (iv) 改回舊字面（JSON 與 PRD 不一致） | 1 | AT-031-1-1 | 殺 |

與 Z 的 commit 訊息自陳一致（socket、write_text、time.sleep、yaml、os.system 五個皆紅、合法 import 對照綠），另補了新檔涵蓋、JSON↔PRD 耦合與子套件邊界三項。V6 獨立重算（`r3_v6_params.py`，不經 `tools/lib/selfimproving/params.py`）：`params.json` 23 鍵恰為 R21 的 23 鍵、20 個數值初值逐鍵相符、`non_evolvable_globs` 必備集合＝PRD 來源一 18 項加根 `CLAUDE.md` 展開 7 項＝25 項，與 params 清單 25 項集合相等、無重複，AT-029-2 四個迴圈自身 glob 皆在清單內。

**搬遷的程式碼差異**（`git show e83ebb14 -M --unified=2 -- tools/lib tools/selfimproving.py`）：七支檔的相似度 96%～100%，變更只有 import 改寫（`from lib import si_x`→`from . import x as si_x`／`from .x import …`，`check.py` 保留 `si_*` 別名以免遮蔽名為 `params` 的參數）、docstring 內的舊檔名，以及入口的 `from lib.selfimproving import check` 與 `si_check.*`→`check.*`；沒有邏輯變動。測試檔差異（40 行）：`import` 改新路徑、八處 docstring 與一個合成座標字串、靜態掃描檔案集合收成 `si_sources()`（入口＋`tools/lib/selfimproving/*.py`，用於 AT-003-1-1 與 AT-030-2-1）、AT-029-2-1 的 glob 斷言、AST 本地模組規則改成只認 `_stdio_utf8` 與 `lib`（相對 import 視為套件內部）；鎖檔與兩個 guard-total 站點只加搬遷說明。

### 9.5 護欄與寫入前現查（任務 4）——通過

```text
> $env:AUTOSDD_PARALLEL_TESTS='1'; python tools/run_root_unittests.py      rc=0   wall=138.03s
unittest 數量下限釘選通過：發現 5426 個測試（下限 5326）
收集面盤存：92 支 test_*.py 檔／指紋 ec7498398005
[cpu_budget] root-unittest workers=18 source=cpu_budget
模組耗時排行（前 5，共 405 模組，平行模式，worker=18）：test_selfimproving_check: 88.8s（第 1）…
派工摘要：worker=18｜S=2031.2s｜ideal=max(S/W, 最長單位)=112.8s（S/W-bound）｜loss=1.00x｜slot 利用率=99.8%
[skip census] tools/tests@win32 共 46 支：platform=42／tool-absence=0／env-disabled=4／structural-pair=0／debt=0／untagged=0／欠債型 4 支（目標 0）
真實 TEMP 圍籬：全套期間真實契約目錄（與 autosdd_quota.json 同目錄）下 autosdd_pace*.json 零變動（前 4／後 4 份；目錄 C:\Users\wuwei）；隔離根已建立並清除。
孤兒 console 普查：零增長（前 1／後 1）。
（輸出中以 FAIL／ERROR 開頭的行：0 行）
> python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines      rc=0
# 淨額 119056→119056 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
# _REPIN_LOG_HISTORY_SHA256 = "94b2abd8d962b936ea56e404fcd42cceb92f381a9d23a4199c6c1418e4571c4d"   （與二審相同，鎖檔未動）
> git log --numstat --format='COMMIT %h' faebb596..HEAD -- <ledger>      rc=0
COMMIT 3c94b533   5  0
> git diff -U0 faebb596 HEAD -- <ledger>        單一 hunk  @@ -110,0 +111,5 @@（OBS-SI-101～105 五列純追加）；刪除行數 0
```

V9：自 `faebb596` 起帳本只有 Z2 一個 commit、單一 hunk、純追加 5 列、0 行刪改；自 N 起合計 54 列（052～105）純追加（X＋11、Y3＋19、Y5＋11、`faebb596`＋8、Z2＋5），`history.row_mutated` 為 PASS。護欄層淨額 +0、逐檔漂移 0，與 Z 的自陳相符；搬遷沒有開新的重釘列，也未再動一次性例外名冊。

### 9.6 逐 AT 單跑（姊妹檔 RTM §2 已更新）

重跑 TCS §2 的 42 個判定指令（`-k <底線形>`）：42/42 皆 `1 passed`、rc＝0、每個 `-k` 恰選到 1 個測試；子測試數與節點名與二審完全相同（整檔仍是 97 個子測試）。測試檔因 `si_sources()` 與 docstring 異動而位移：33/42 個 AT 的行區間改變（AT-001-1-1 到 AT-003-1-1 的起點 +5，其後到 AT-030-2-1 的起點 +4；AT-030-2-1 的結尾行與 AT-030-3-1 之後 0，所以尾端 9 個 AT 不變），TCS 區塊行號 0 個改變（勘誤只加在檔尾）。RTM §2 已全部重抽，座標以 HEAD `3c94b533` 為準。

### 9.7 三審新發現

| 編號 | 嚴重度 | 發現 | 座標 | 建議處置 |
|------|--------|------|------|----------|
| F-16 | **P3** | 授權座標偏到衍生記錄，且時間欄是入帳批次時刻：帳本 101 的證據座標、PRD 鍵 `frozen_stages` 末筆的 `approved_by`、TCS 搬遷勘誤、Z 的 commit 訊息都引「逐字稿 line 5507／5524／5565」。實測（`r3_transcript.py`，唯讀 `json.loads` 該實體行，LF 切 6280 段）：5507＝`type=user`、`origin.kind=human`（「所以這個模組不用規劃獨立的目錄? 放實作的目錄或程式是嗎?」）正確；5524＝`type=user` 的 `tool_result`，內容是 AskUserQuestion 的回答「現在就搬」，`origin.kind` 為空——是互動選項的記錄，可接受但不是 human 文字；**5565＝`type=api-request-blob`（請求傾印），不是人工記錄**。第三句指令（「請注意, 請規劃日後有新模組產生時, 可以有系統, 有組織的規劃整體專案系統目錄, 不要到處散落, 請寫在CLAUDE.md及專案規格相關文件中落實! 記住此點」）的原始記錄是 line 5534（`queue-operation enqueue`，09:15:52Z）與 line 5563（`attachment`、`queued_command`、`origin.kind=human`、`humanTurn=true`，09:15:52Z）。同型錯誤（假座標落在 assistant 空記錄）在 PRD 附錄 C.2 已訂正過一次（TCS 預審任務 A）；授權事實本身不受影響（同一句在 5534／5563 逐字可查）。另，帳本 101 的時間欄 17:45 是入帳時刻，事件可由逐字稿追溯到 17:12～17:15（5507：09:12:08Z；5524：09:13:43Z；5534：09:15:52Z），與帳本 077「可追溯者填事件時刻」的決議不符 | 帳本 OBS-SI-101 的證據座標與時間欄；`FSM-STATE-monorepo-selfimproving` 末筆 `approved_by`（經 `show`）；TCS `:1481`（搬遷勘誤〈事由〉）；Z 的 commit 訊息；逐字稿 `f3ead132-….jsonl` line 5507／5524／5534／5563／5565 | 不阻斷。追加更正列（`rel=corrects:OBS-SI-101`），座標改為 line 5507（human）、5524（AskUserQuestion 回答）、5563（queued_command，`origin.kind=human`；入列於 5534），時間改事件時刻；FSM 與 TCS 為凍結紀錄不改，以更正列為準。往後引用人類指令的座標一律取 `origin.kind=human` 的原始記錄（`type=user`、`queued_command` 附件或 `queue-operation`），不取 `api-request-blob` |
| F-17 | P4 | P0 鍵的凍結紀錄與現檔不符：`frozen_stages`（Stage-1、Stage-2）記的 TCS 摘要是 `6c4e28ed…`、PRD 摘要是 `9c571827…`，現檔已是 `6f7e24e7…` 與 `fbca6bc9…`；修訂後的 TCS digest 只在 decision_trace #20 的自由文字裡。這是已揭露的取捨（TCS 勘誤與 #19、#20 都明載；`transition_rules.py` 的 `SPEC_AUDIT` 只能出邊到 `PR_REVIEW`，IMPLEMENTATION 之後沒有重凍的邊）。實證後果（`r3_check_digest.py`：把 `show` 取得的 `frozen_stages` 餵給 AutoClaude adapter 的凍結閘 `_sdd_frozen_gate.check_digest`，記憶體內、唯讀）：P0 鍵對 TCS 與 PRD 都拋 `SpecDigestMismatchError`（「凍結後改檔須重新核准凍結」），對研究方法 SOP 為 `verified`；PRD 鍵對 PRD、SOP 為 `verified`、對 TCS 拋 `SpecNotFrozenError`（TCS 不在該鍵的凍結清單，預期）。即：日後若以 P0 鍵跑 SDD→Playbook 編譯（A 軌），該閘會 fail-closed。本棒查到的消費者中沒有受影響者（P0 已實作並驗收；AISDLC_SDD v0.30 的 `fsm_runtime`、`state_loader` 只寫入摘要、hooks 不引用它；AgentConsole／Bridge 的消費未查，見 §9.10） | `FSM-STATE-monorepo-si-p0-ledger` 的 `frozen_stages`（經 `show`）；`AutoClaude/autoclaude/infra/adapters/_sdd_frozen_gate.py:179`（`check_digest`）；TCS 搬遷勘誤 | 不動作；請掌舵者知悉。P0 鍵收尾（RELEASE）前若要避免日後誤判，可在證據檔記一句「P0 鍵 frozen_stages 為歷史、現行 digest 以 decision_trace #20 與現檔為準」；P1 另開新鍵時凍結新 TCS 即綁新 digest |
| F-18 | P4 | TCS 殘留舊路徑字面，且勘誤的標籤不夠精確：(i) 仍有三處 `si_*.py` 字面——現況列 `:36`（「沒有 `tools/lib/si_*.py`…」，描述 P0 前的狀態，尚可讀作歷史）、INVEST 自檢 `:234`（「約 3 個 `si_*.py` 模組」，估算本來就與實況〔7 個模組〕不符）、增量追溯表 SCG-2 Container 列 `:267`（「落點：根層 `tools/`（CLI 與 `lib/si_*.py`）…」，是落點陳述，與同檔 D4 列的新路徑自相矛盾）；`:1353` 的合成座標已於勘誤聲明不改。(ii) 勘誤與 decision_trace #19 寫「R8 (a) 本地模組規則」，實際被改的是 AT-030-2-1 的 AST 子句（`:1001`），R8 條文自身未動，且「本地模組」屬 R8 (b)；(iii) 勘誤的改動清單沒列 `:267` | TCS `:36`、`:234`、`:267`、`:1001`、勘誤節（`:1479` 起） | 不阻斷。下次動 TCS（P1 另開新檔）時一併改；或在勘誤追加一行「`:267` 同改套件路徑」。TCS 已凍結，現階段不為此再走一次 FSM |
| F-19 | P4 | 落點規範文件三處不精確：(i) §1 `tools/git-hooks/`、`tools/act/` 列的權威指引寫 `tools/install_git_hooks.*`，根層 `tools/` 沒有此檔，實檔是 `AutoClaude/tools/install_git_hooks.ps1`、`.sh`（根 `CLAUDE.md` 的 AutoClaude 快查在 `AutoClaude/` 下執行，SSOT 沿用該相對路徑而漏了前綴）；(ii) §2「審查／RTM」列的審查報告樣式 `SCG<n>-REVIEW-<Module>-<YYYYMMDD>.md` 漏 `<Phase>`，現有 `SCG4-REVIEW-SelfImproving-P0-20261019.md` 對不上，而同列 RTM 與預審樣式都有 `<Phase>`；(iii) PRD §9.1 的落點表是散文、不是表，且含兩格（事件帳本 `.jsonl`、提案內容檔目錄）在 §2 沒有對應列，違反 SSOT §4 第 1 條「PRD 元件表每一列的路徑都能對上 §2 的某一格；對不上＝先改本檔」 | `docs/02_architecture/Root_Layout_and_Module_Placement.md:18`、`:38`、§4 第 1 條；PRD `:559` | 不阻斷。SSOT 不在凍結集合內，可由主控直接改：(i) 路徑補 `AutoClaude/tools/`；(ii) 樣式補 `[-<Phase>]`；(iii) §2 補「機器寫的事件帳本」與「提案內容檔」兩列（P1 才落檔，標 P1），PRD 落點段落可維持散文但註明「填寫版」 |
| F-20 | P4 | 搬遷對映列不全：帳本 102～104 只為 079、084、090 補了舊→新路徑對映；082（F-03 修復列，座標 `tools/lib/si_refs.py:125`）搬遷後的路徑也已不存在，且其更正列 100 的處置寫「修復後位置以本列與後續搬遷列為準」，後續搬遷列卻沒有 082。101 的處置有通則（「搬遷前的列一律依該列 commit 當時的路徑解讀」），所以資訊不致遺失，只是對映不一致 | 帳本 OBS-SI-082、100、102～104 | 不阻斷。下一批入帳時追加一列 `rel=corrects:OBS-SI-082`（`tools/lib/selfimproving/refs.py` 的 `_escapes_repo`、`orig_findings`），或在 105 之後的列註明「通則涵蓋、不逐列對映」 |
| F-21 | P4（理論洞，無暴露證據） | 三個邊界，皆為實測、現況無受害者：(i) **同名遮蔽**：SSOT §2 要求入口 `tools/<module>.py` 與套件 `tools/lib/<module>/` 同名；實測 `sys.path` 為 `[tools/lib, tools]` 時 `import selfimproving` 解析到套件 `__init__.py`（`has main=False`），為 `[tools, tools/lib]` 時才是入口（`has main=True`）。唯一 `import selfimproving` 的消費者是測試檔，且先插入 `tools/`，現況安全；(ii) **非遞迴掃描**：AT-003-1-1／AT-030-2-1 與 R26 的掃描集合是 `tools/lib/selfimproving/*.py`，子套件內的檔不在內（S8 實測 0 failed）；SSOT §2 沒禁止子套件；(iii) **CI 覆蓋看不到資料／文件消費**：見 §9.4，測試以變數名 `ROOT`（非 `REPO_ROOT`）消費的 `params.json`、`metrics.md`、SOP、PRD 不在 compat-ci `paths`，覆蓋鎖也掃不到 | `tools/tests/test_selfimproving_check.py:27–28`（`ROOT`）、`si_sources()`；`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`；SSOT §2 | 依根 `CLAUDE.md`〈守衛面准入〉的精神：無暴露證據就登記理論洞、不立輪、不同輪修。(i) 可在 SSOT §2 加一句「入口與套件同名；消費入口者須先把 `tools/` 排在 `tools/lib` 之前」；(ii) P1 若加子套件，同批把掃描集合改遞迴；(iii) 想補時，把測試的 `ROOT` 改名 `REPO_ROOT` 或在兩支 compat-ci 加四條 `paths`，覆蓋鎖就會自動要求 |

統計：二審殘餘 P4 六項（F-08、F-10、F-11 (iv)、F-12、F-14、F-15）不變；三審新增 P3 一項（F-16）、P4 五項（F-17～F-21）；P1、P2 為 0。

### 9.8 三審判定

**PASS**——理由：(1) 規格修訂經機械證明只動路徑字面、落點表、勘誤與 18 處 digest，AT 42、R 26、判定碼 50 個 token、PRD 條目 97 個全未變，兩個 FSM 鍵的 decision_trace 有對應理由、PRD 鍵末筆 digest 與現檔相符；(2) 落點規範對 SelfImproving 現況、根 `CLAUDE.md` 與 PRD §9 大體一致，不一致處是文件精確度問題（F-19）；(3) 程式搬遷不改行為：`check` rc 0（`params.globs`、`ref.obs` PASS、105 列）、整檔 42 passed、`-k` 兩組綠、ruff 綠、LOC 綠（入口與套件共 9 檔皆在管轄內）、CI paths 覆蓋鎖 49 passed 且獨立解析證明兩支 compat-ci 涵蓋新套件、鏡像突變 9 個全殺且合法對照不誤殺；(4) 根層全套 rc 0（5426）、護欄淨額 +0、V9 自 `faebb596` 起純追加。

給主控的收尾建議（非阻斷）：
1. 本檔檔頭的「現行判定」補註目前只提到 §8；建議再補一句「三審（搬遷複驗）見 §9，PASS」。
2. F-16 的更正列與 F-20 的對映列，連同 §9.9 的流程摩擦，請於 SCG-4 收尾前入帳（本棒不寫帳本）；FSM `gate --gate PR_REVIEW --result PASS` 由主控執行，本棒未碰 FSM。
3. F-19 的三處是 SSOT 文件的修字，主控可直接改（SSOT 不在凍結集合內）；F-18、F-17 屬已凍結檔與 FSM 紀錄，不建議為此重走 FSM。
4. 帳本 058 所指的 repo 外殘留檔 `e501_count.py` 仍待掌舵者刪除（二審 §8.9 已提）。

### 9.9 流程摩擦（本棒三審；每項一句症狀加一個座標，請主控於 SCG-4 收尾前入帳）

1. 系統提示（auto mode）本輪開頭再度要求優先用 Bash，與根 `CLAUDE.md`〈鐵律一〉衝突，全程仍用 PowerShell／Read／Grep／Glob／Edit／Write（OBS-SI-011 再復發）；座標：根 `CLAUDE.md`〈鐵律一〉。
2. PowerShell 工具的安全掃描把 Python 腳本（here-string）裡的 `del sys.modules[k]` 當成 PowerShell 別名 `del`（Remove-Item），回「Remove-Item on system path … is blocked」而整個呼叫被擋；改寫成 `sys.modules.pop(k, None)` 才放行；座標：`qa_scg4\r3_shadow.py`。
3. `Grep` 對 PRD 的超長行（單行含整段落點表）即使加 `-o` 與 `.{0,900}` 視窗仍回「[Omitted long matching line]」，改讀 `git show` 輸出檔才取得原文（OBS-SI-033 再復發）；座標：PRD `:559`。
4. 測試檔動了 5 行，RTM §2 有 33/42 列的行區間又全數過期，得重跑 42 個單跑與重抽（OBS-SI-096 再復發）；座標：RTM §2。
5. 任務書與任務訊息對同一個 `-k` 選測寫了兩種運算式（訊息為 `AT_003_1_1 or AT_029_2_1 or AT_030_2_1`，任務書為 `AT_003_1_1 or AT_031 or AT_030_2_1`），兩種都跑了才無歧義；座標：`qa_scg4_r3_brief.md` 第 3 項。
6. 取用 FSM 狀態只能經 `FSMRuntime` 的 `show --must-exist`，需手設 `SDD_STATE_DIR`、遙測旗標與版本目錄為 cwd，且 `show` 的輸出是單行 17 KB 的 JSON，要另寫腳本才讀得出 decision_trace 與 `frozen_stages`；座標：`SDD_AUTOCLAUDE_BRIDGE.md` §8.2 (a) 的 `show` 配方。

### 9.10 未查證／未做（三審）

- **macOS／POSIX 與 GitHub Actions 仍未實跑**：compat-ci 的 `paths` 只做了靜態 YAML 解析與覆蓋鎖，沒有在真 CI 上驗證路徑過濾行為；F-21 (i) 的同名遮蔽只在 Windows 實測。
- **SD 搬遷棒交卷原文未取得**：Z 的 commit 訊息所述 SD 做法（相對 import、`si_*` 別名、鏡像突變五項）只以本棒自己的 diff 讀取與鏡像重放驗證，沒有與 SD 交卷逐項對帳。
- **`ci-gate.sh`、AISDLC_SDD 全套、`lint-imports`、AutoClaude pytest、AgentConsole／Bridge 對 FSM 摘要的消費** 皆未跑或未查（本輪只跑 CI paths 覆蓋鎖）；F-17 只驗了 AutoClaude adapter 的凍結閘。
- **`git log --follow` 的改名歷史** 只看了 Z 的相似度（96%～100%），沒有逐檔追蹤。
- **FSM 路徑的合規性不裁決**：`IMPLEMENTATION→SPEC_AUDIT→PR_REVIEW` 是否為框架對「凍結後規格修訂」的預期用法，我只核對了轉換合法（`transition_rules.py`）與 reason 齊備，沒有評論其設計。
- **P1 才會有的件不在本輪範圍**：`tools/probe/selfimproving_measure.py` 與候選鎖 `test_root_module_layout.py` 皆未落檔（SSOT §5 與帳本 105 已誠實標示）。
- **PRD 其他段落的路徑字面**：以全 repo 的字面 grep 確認 PRD 已無 `si_*.py` 殘留，但沒有逐段重讀 PRD 其餘 1000 多行。
- 一審 §7、二審 §8.11 的其餘未查證項目（`check` 邊界探測、T 之前與 M 之後的紅燈狀態重現等）本輪仍未做。

### 9.11 勘誤（對一、二審內文）

本輪沒有發現一、二審的事實性錯誤。座標需註記：一審 §3、§4 與二審 §8.4 所引測試檔與 `tools/lib/si_*.py` 的行號與路徑是當時版本的座標；搬遷（Z）後 `si_*.py` 已成 `tools/lib/selfimproving/*.py`（`git mv`，相似度 96%～100%），測試檔行號再位移，現行座標見 RTM §2（以 HEAD `3c94b533` 為準）；二審 §8.5 的 `rows=92`、判準指紋 `87b349b7…` 是當時的量測，現行為 105 列與 `751d4c3d…`。

### 9.12 證據檔（scratchpad，不入庫）

`qa_scg4\` 下：`r3_show_faebb596.txt`、`r3_show_Z.txt`、`r3_show_Z2.txt`、`r3_Z_tcs_prd.diff`、`r3_Z_code.diff`、`r3_Z_tests.diff`、`r3_Z_misc.diff`、`r3_tcs_invariants.py/.txt`、`r3_fsm_show_monorepo-si-p0-ledger.txt`、`r3_fsm_show_monorepo-selfimproving.txt`、`r3_fsm_overview.py/.txt`、`r3_fsm_detail.py/.txt`、`r3_check_digest.py/.txt`、`r3_layout_exist.py/.txt`、`r3_check_json.txt`、`r3_check_text.txt`、`r3_k_run.txt`、`r3_k_run2.txt`、`r3_full_file.txt`、`r3_collect.txt`、`r3_ruff.txt`、`r3_loc.txt`、`r3_loc_view.py/.txt`、`r3_ci_paths.txt`、`r3_ci_cover.py/.txt`、`r3_ci_data_cover.py/.txt`、`r3_lock_view.py/.txt`、`r3_mut_run.py`、`r3_mut_results.txt`、`r3_shadow.py/.txt`、`r3_v6_params.py/.txt`、`r3_ntfs.txt`、`r3_print_guard.txt`、`r3_root_suite.txt`、`r3_v9_numstat.txt`、`r3_v9_hunks.txt`、`r3_transcript.py/.txt`、`r3_transcript_find.py/.txt`、`r3_transcript_find2.py/.txt`、`r3_transcript_5534.py/.txt`、`each_at.json/.txt`（三審重跑）、`each_at_r2.json`（二審備份）、`rtm_data.json`、`rtm_data_r2.json`、`rtm_at_table3.md`、`r3_rtm_diff.py/.txt`。
