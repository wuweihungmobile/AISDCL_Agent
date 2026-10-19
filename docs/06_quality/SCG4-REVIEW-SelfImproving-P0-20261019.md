# SCG-4 PR Review 報告 — SelfImproving P0（觀察帳本定稿、一次性遷移、`check` 與協定目錄）

**審查日期**: 2026-10-19（本機 15:49 +08:00 起算）　**審查者**: SCG-4 獨立 QA 棒（Sonnet 5.5；未參與 TCS 撰寫與 P0 實作；規格作者＝SA 棒，實作者＝Developer 棒〔D3～D6〕加主控〔D1、D2 帳本編修與護欄層重釘〕，三方不同）
**FSM 功能鍵**: `monorepo-si-p0-ledger`（PR_REVIEW／SCG-4）
**基準規格**: `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`（Stage-2 凍結 digest `sha256:6c4e28ed30ab3e05ea1acbbf4b8d1a5a5004f5a2aed3fb535abb59cfb420de56`，當回合重算相符）；上游 `docs/01_requirements/SelfImproving_PRD.md`（`sha256:9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e`，重算相符）
**姊妹檔**: `docs/06_quality/RTM-SelfImproving-P0-20261019.md`（FR／AC → AT → 測試方法 → 本次結果 → 證據座標）
**判定**: **FAIL**（P1＝0、P2＝2、P3＝3、P4＝9）。V1、V2、V4、V5、V6、V7、V9 通過；**V3 的 (9)「座標可重查」未通過（F-02）、V8「SOP 條文語意對照 PRD」未通過（F-01）**。兩個 P2 的補救成本都低（改一段 SOP 文字、追加一列更正列），補救後須由 QA 複驗 V3 (9) 與 V8。

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
