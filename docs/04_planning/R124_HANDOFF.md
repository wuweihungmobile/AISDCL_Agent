# R124 交棒書（帳本可寫性修復輪）

- **輪籤**：R124
- **主線**：`docs/04_planning/R124_Row_Slimming_Plan.md` 檔頭〈掌舵者裁決〉。本輪**不結任何
  一筆缺陷**，目標是解除「帳本列寫不進字」這個結構瓶頸：700 bytes 逐列上限使多筆列物理上
  寫不下結案理由，且部分列把好幾件互不相關的待辦擠在同一個 ID 底下（收集列），這正是它們
  數十輪不動的機制本身。兩手並用：A 型（史料搬證據檔）＋ B 型（一個 ID 一件事拆列）。
- **帳本**：未結列 **40 → 57**（🔴 分母上升是本輪的**設計目標**，不是退步——見下方逐筆
  說明）。commit＝`c9b92fe`（尚未 push）。

## 本輪已落地

### A 型瘦身（6 筆超標列，史料逐字搬進 `CrossPlatform_R124_Row_Slimming.md`）

| ID | 原列 bytes | 瘦身後 | 餘裕 |
|---|---|---|---|
| `DEF-101-736` | 2537 | 635 | 65 |
| `DEF-101-856` | 2238 | 631 | 69 |
| `DEF-101-675` | 1319 | 686 | 14 |
| `DEF-101-803` | 1304 | 663 | 37 |
| `DEF-101-796` | 1271 | 587 | 113 |
| `DEF-101-887` | 1024 | 658 | 42 |

六筆全數跌破 700B 後已從 `OVERSIZE_ROW_GRANDFATHERED` 移除（`archive_defect_log.py
--repin-oversize`）：`OVERSIZE_ROW_CEILING` 42→36、`OVERSIZE_ROW_EXCESS_CEILING`
25520→20027；`tools/lib/ledger_rotation.py` 的 `*_HISTORY` 與封印表（`_SEAL_TOTAL_MIN_LEN`
44→46、`_SEAL_TABLE_SHA256` 已重算）同步補上——這是 `--repin-oversize` 自己聲明**不做**
的另一半，本輪已補齊。

### B 型拆列（收集列一個 ID 一件事；原列保留、不結案；新列一律 `open（未指派）`）

| 原列 | 原項目數 | 保留哪項 | 拆出新列 |
|---|---|---|---|
| `DEF-101-856` | 7（①已由 `DEF-101-865` 同輪完成、⑦因拆列消解，實拆 5） | ⑥ pgvector staging | `DEF-200-247`~`250`（②③④⑤） |
| `DEF-200-065` | 3（③已修，實拆 1） | ② `skip_group_policy.py` 貼牆 | `DEF-200-251`（①） |
| `DEF-101-981` | 6 | ⑥ `hook_wiring.py` 職責分離 | `DEF-200-252`~`256`（①②③④⑤） |
| `DEF-200-172` | 8 | ③ 帳本體例三筆（須改根 CLAUDE.md） | `DEF-200-257`~`263`（①②④⑤⑥⑦⑧） |

共新立 17 筆（`DEF-200-247`~`263`），每筆自帶四欄（發現情境**零輪號**／現象與證據／嚴重度／
分流去向）與狀態欄（`open（未指派）`＋可執行解鎖條件＋指回
`CrossPlatform_R124_Row_Slimming.md §<原列 ID>` 讀原始判讀史料）。

### 🔴 刻意保留、本輪未拆的候選

- **`DEF-200-213`**：與 `DEF-200-207`／`241` 同屬 `check_handoff_carriers.py` 的承接憑證
  （紅線：不准動狀態欄首詞），且該列狀態欄本身是高度壓縮的簡寫（`open（交由R112）
  ④②已落@R111①③結案包`），哪幾項真正「已落地」需要逐字回讀 `CrossPlatform_R111`／
  `R112` 系列史料才能判準，本輪判斷**風險大於收益**，留給下一輪仔細判讀後再拆。現查該列
  仍是單一未拆列：`Select-String -Path docs/06_quality/AutoSDD_Defect_Log.md -Pattern "^\| DEF-200-213 \|"`。

## 已驗證（本 session 實測）

- 三支文件閘門：`check_defect_log_crossref.py` rc=0（帳本 192 筆有效狀態紀錄、具名治理
  文件 95 份皆已登記）、`check_archive_required.py` rc=0、`check_handoff_carriers.py` rc=0
  （commit 前，帶 `AUTOSDD_NET_RATCHET_OFF=1`）。
- `--print-guard-lines`：淨額 `91990→91990 (+0)`，逐檔漂移 0 支。
- `sync_onboarding_baselines.py --write`：ONBOARDING.md §7 已是最新，未變更。
- `AutoClaude/tools/check_loc_budget.py --json`：`total_violation=False`、三類 violations
  皆空清單。
- `python -m pytest tools/tests/test_check_defect_log_crossref.py tools/tests/test_archive_defect_log.py -q`：
  commit 前跑（工作樹相對 HEAD 有淨增 4~17 筆的中繼狀態）僅
  `TestMain::test_main_against_real_repo_is_clean` 與
  `TestEarlyExitAnnouncesUnrunChecks::test_the_real_gate_still_reaches_the_late_checks`
  兩支紅（兩支都是「真實 repo 現況」測試，不帶逃生口直接呼叫 `m.main()`／子行程比對淨額，
  在**未 commit**的中繼狀態下必然如此，commit 後工作樹＝HEAD、差集歸零即自然轉綠，不是
  新缺陷）；其餘 435~437 個測試與 390 個 subtest 全通過。
- 過程中另修復並複驗兩筆真回歸（見下方〈本輪順手修的兩個小坑〉）。
- **`python tools/run_root_unittests.py`（commit 後、工作樹乾淨狀態下的全套）**：本檔
  落筆時該次背景執行尚未回報，**不得**把本行當「已通過」宣稱使用；下一位接手者或本
  session 續行時請先現查該次執行的 log（本輪存於
  `C:\Users\wuwei\AppData\Local\Temp\claude\d--CursorProject-AISDCL-Agent\e6952875-a902-4df9-8fd4-0c59010a98a0\scratchpad\run_root_unittests_post_commit.log`，
  該路徑屬本機 session 暫存、不隨 repo 走，下一個 session 請自行重跑一次取得真實 rc）
  取得真實 rc，不得沿用本檔任何字面。

## 本輪順手修的兩個小坑（非本輪主線，跑測試時揪出）

1. `tools/lib/ledger_rotation.py` 新增的封印註解一度自稱 `# R121 純結案輪` 卻沒帶
   `round-label-ok` 標籤，被 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 當場
   擋下（程式碼註解的輪號不得超前帳本時鐘，除非顯式標記）；已補標籤修復。
2. `docs/06_quality/CrossPlatform_R124_Row_Slimming.md` 的 `## DEF-101-796`／`## DEF-101-803`
   兩個小節標題與 `CrossPlatform_R79_Debt_Audit.md` 既有標題撞號，被
   `TestEvidenceFamilyPointersResolve::test_no_anchor_lives_in_two_files_at_once` 擋下
   （同一 DEF-ID 的證據節不得出現在兩份治理文件）；已各自加註「（R124 帳本列瘦身）」
   後綴消歧義。

## 還沒做（不塗綠）

1. **`DEF-200-213` 尚未拆列**（見上方〈刻意保留〉）——下一輪動工前務必先逐字回讀
   `CrossPlatform_R111`／`R112` 系列史料，判清哪幾項真的已落地才能安全拆。現查該列仍是
   單一未拆列：`Select-String -Path docs/06_quality/AutoSDD_Defect_Log.md -Pattern "^\| DEF-200-213 \|"`。
2. **9 筆餘裕 ≤5B 的列（`213` 除外）尚未處理**：`DEF-200-133`／`206`／`137`／`118`／
   `167`／`183`／`197`／`124`／`234`，非本輪六筆超標清單成員、本輪未觸及。現查最新清單：
   `python -c "import re,pathlib; t=pathlib.Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8'); [print(m.group(1), len(l.encode('utf-8'))) for l in t.splitlines() if (m:=re.match(r'^\\|\\s*(DEF-\\d+-\\d+)\\s*\\|', l)) and len(l.encode('utf-8'))>=690]"`。
3. **本輪四方複審尚未執行**
   <!-- absent-if: CrossPlatform_R124_Review -->——證偽錨＝四方複審結論轉錄檔名（同
   R79~R81 既有體例）：那個字面一旦在任何 tracked 檔裡搜得到，本條宣稱即為假並當場轉紅。
   依 M3「作者自證不計分」，本輪全部改動屬自證。現查本輪落地了哪幾個 commit：
   `git log --oneline -3`。
4. **尚未 push**：commit `c9b92fe` 仍只在本機，push 前請先確認上方〈全套〉那行的真實 rc。
   現查本機領先 origin/main 幾個 commit：`git log origin/main..HEAD --oneline`。

## 下一步（下一個窗口）

- 若〈全套〉log 顯示乾淨全綠：直接 `git push`（**不帶** `AUTOSDD_NET_RATCHET_OFF`，
  commit 後工作樹已與 HEAD 一致，淨額棘輪不會再攔）；push 後等雲端四／五支全部
  `completed`，逐支查看結論（不得只看是否觸發）。
- 若〈全套〉log 顯示有紅：先讀 log 判斷是否為本輪改動所致，修復後才 push。
- 完成 push 且雲端全綠後，可考慮續拆 `DEF-200-213` 或處理清單②列出的 9 筆貼線列
  （兩者皆為候選，非強制）。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`；**push 不帶 `AUTOSDD_NET_RATCHET_OFF`**
  （commit 後working tree=HEAD，淨額棘輪比較的差集已歸零，不需要也不應該帶）。
- 不准把六筆已瘦身的 ID（`DEF-101-736`／`856`／`675`／`803`／`796`／`887`）補回
  `OVERSIZE_ROW_GRANDFATHERED`——本輪的方向是從名單移除，回補即是無聲漲回去。
- 不准動 `DEF-200-207`／`213`／`241` 的狀態欄首詞（可瘦身史料，不准結案）。
- 不准在任何帳本列的「發現情境」欄補當前輪號（帳本時鐘刻意零輪號按住在 R100）；程式碼
  檔（如 `tools/lib/*.py`）內的輪號提及需帶 `round-label-ok` 標籤，見上方〈順手修的兩個
  小坑〉第 1 條。
- 交棒書「還沒做」節每一筆都要帶詞表詞＋現查指令 code span，否定宣稱要帶 `absent-if` 錨
  ——附指令不算數（R81 §3.2 判例；R123 交棒書曾在此被 pre-push 擋下一次）。
