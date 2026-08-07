# CrossPlatform_R79_Debt_Audit — 缺陷帳本瘦身與續改派 backlog 逐筆定案（R79 技術債清除）

> **本檔為什麼屬於「具名治理文件」**：它承擔與缺陷帳本主檔同等的義務——複審者要重驗本輪
> 的結案與定案判定，就得讀完它；它逐筆寫出「某缺陷在今天的磁碟上是什麼狀態」的宣稱。
> 故已登記進 `tools/check_defect_log_crossref.py` 的 `_GOVERNANCE_DOCS`，同時受體積守門與
> 指針稽核管轄（登記與否不是喜好，是資格判斷，見該常數上方 WHY）。
>
> 🔴 **本檔同時是帳本瘦身的接收端**：主檔的列被政策定義成**索引**（≤700 bytes），長文
> （「當回合查證」「解鎖條件」「原狀態欄全文」）一律搬來這裡。帳本那一列只留一句話
> 與指向本檔某一節的指針，而那個指針受 `TestEvidenceFamilyPointersResolve` 機械看守
> ——指到不存在的檔或不存在的節即紅（本輪落地過程中被它抓過一次）。

## 動工前基線（當回合實測，逐字）

| 量 | 指令 | 值 |
|---|---|---|
| 未結列 | `python tools/check_defect_log_crossref.py --unresolved-count` | **86**／全 120 列，warn 86 fail 98（距 fail 12 筆），rc=0 |
| 主檔體積 | 自寫探針量 `st_size` | **256,920 bytes**，距 pre-push 硬閘 `_LEDGER_FAIL_BYTES=262,144` 僅 **5,224 bytes** |
| 逐列位元組 | 自寫探針逐列 `len(line.encode("utf-8"))` | 120 列中 **110 列 > 700 bytes**，平均 **2,089**，最大 10,445 |
| 「≤700」的機械物 | `Grep '700' tools/check_defect_log_crossref.py` / `tools/archive_defect_log.py` | 各 1 命中無關散文／0 命中 ⇒ **零機械物** |

---

## DEF-101-890

**本輪新立列**（`P1`）：帳本「單列 ≤700 bytes」政策零機械物。

### 缺陷本體

政策自 R75 訂立、R76／R77／R78 三份交棒書逐字沿用並寫進「禁止事項」，而**全 repo 沒有
任何東西在看它**。後果不是「列太長很難看」，是**帳本主檔的可用容量**：110 列違規列合計
吃掉 244,880 bytes（全檔 95%），把主檔推到距 pre-push 硬閘約 2 列的位置。本輪必然要寫
帳本列，寫到第 3 列就會讓 `check_defect_log_crossref.py` rc=1 ⇒ 整個 repo 的 push 被擋死。

同一處還有第二個缺陷：唯一在看體積的觀測者在觸發當下是 `return _bail(...)` **早退**，
會連帶關掉同一支工具其後**全部**內容判準（跨文件一致、孤兒承接、未結存量、狀態 token…），
而讀者拿到的畫面只是「輸出變短」——診斷與閘門同時消失，方向正是「看起來變乾淨」。

### 落地物（判準本體住 `tools/lib/defect_ledger_index.py`，兩支工具共用）

| 常數／函式 | 作用 |
|---|---|
| `ROW_MAX_BYTES = 700` | 政策值，**不重新談**（本輪只替它裝上量測者） |
| `row_bytes()` | 主檔逐列 UTF-8 位元組數；量位元組不量字元（CJK 一字三位元組） |
| `OVERSIZE_ROW_GRANDFATHERED` | **具名**存量豁免（105 筆）——判準因此分得開「新列／新膨脹」與「既有列」 |
| `OVERSIZE_ROW_CEILING = 105` | 豁免清單**筆數**棘輪，只准往下 |
| `OVERSIZE_ROW_EXCESS_CEILING` | 存量列**超標總量**棘輪，只准往下、零成長容忍（現值一律現查該常數，本檔不寫死——寫死就是下一個 stale 站點，且它由 `test_the_real_ledger_baselines_are_exact_not_padded` 雙邊釘住） |
| `oversize_row_problems()` | 四向判準 |

**四向為什麼缺一不可**（每一向都對應一條靠其餘三向擋不住的繞道）：

1. 超標而**不在**豁免清單 ⇒ 紅。缺它 ⇒ 新列可以隨便長。
2. 在豁免清單而**已不超標**（或該 ID 已不在主檔）⇒ 紅，要求刪除該筆。
   缺它 ⇒ 清單退化成永久額度（判例同 `stale_grandfather_problems()`）。
3. 清單筆數 > 棘輪上限 ⇒ 紅。缺它 ⇒「膨脹了就順手把 ID 補進清單」是免費的（①會轉綠）。
4. 超標總量 > 棘輪上限 ⇒ 紅。缺它 ⇒ 一列 800 bytes 的豁免列可以長到 8,000 而 ①②③ 全綠，
   **而主檔體積正是被這個量推上硬閘的**。

**為什麼不一次全紅**：105 列是歷史事實，硬擋會讓本鎖上線即永紅，而永紅的鎖會被整個關掉，
比沒有鎖更糟（`ARCH-R59-NB4` 判例）。取值紀律照抄 `_FROZEN_GUARD_LINES`：**當回合實測
直接填入、零加減推算、不留成長緩衝**，並由
`TestR79RowByteCeiling::test_the_real_ledger_baselines_are_exact_not_padded` 雙邊釘住
（基線比實況大＝留了餘裕、比實況小＝有人瘦身後忘了下修，兩個方向都要說話）。

### 注入證明（當回合實跑，`tools/tests/test_check_defect_log_crossref.py::TestR79RowByteCeiling`，9 passed／rc=0）

| 注入 | 期望 | 實測 |
|---|---|---|
| 800 bytes 的新列、不在豁免清單 | 紅並指名 ID 與位元組 | ✅ `test_a_new_oversize_row_is_red` |
| 同一列縮到 700 bytes | 綠（證明上面那個紅不是恆真） | ✅ `test_the_same_row_under_the_ceiling_is_green` |
| 豁免清單列了一個已縮小／已不存在的 ID | 兩筆紅：「豁免已過期」「查無此 ID」 | ✅ `test_a_stale_grandfather_entry_is_red` |
| 把違規 ID 補進豁免清單（繞道③） | ① 轉綠但筆數棘輪接手 ⇒ 仍紅 | ✅ `test_padding_the_grandfather_list_is_red_not_a_free_pass` |
| 豁免列由 900 長到 901 bytes（繞道④） | ①②③ 全綠、總量棘輪接手，訊息點名「被改長了 1 bytes」 | ✅ `test_growing_an_exempt_row_is_red` |
| 真實主檔 | 零問題 | ✅ `test_the_real_ledger_is_green_today` |
| 主檔超線（合成 fixture 撐過 256KB） | rc=1、訊息含「輪替上限」、且**不得**再說「尚有 N 道未執行」 | ✅ `test_the_volume_check_no_longer_masks_the_later_checks` |

最後一列就是早退遮蔽的回歸鎖：判準取「體積名目排在 `_CHECK_ORDER` **最後一位**」＋
「超線時訊息不得宣稱有未執行的檢查」，兩者合起來即「它不再遮蔽任何東西」。

**端到端注入（不經任何 mock，直接動真實主檔；還原以位元組為單位並比對 sha256）**：

```
[BEFORE]        rc=0  sha=949c716aa29ea2f2
[INJECT]        新列 988 bytes（> 700，且不在 OVERSIZE_ROW_GRANDFATHERED）
[AFTER-INJECT]  rc=1
   ❌ 帳本體積與逐列位元組上限（2 筆）：
   - DEF-99-777：該列 988 bytes > 單列上限 700 且不在存量豁免清單內。…
[RESTORED]      rc=0  sha=949c716aa29ea2f2  byte-identical=True
```

「2 筆」是兩向同時發話：① 新列不在豁免清單、④ 超標總量被推高 288 bytes。
還原後 sha256 與注入前**逐字相同** ⇒ 這次實驗在工作樹上零殘留。

**這道鎖上線後第一件事就是抓本包自己**：本輪把 `DEF-101-810` 的狀態欄改寫時多寫了
84 bytes，`OVERSIZE_ROW_EXCESS_CEILING` 當場轉紅並點名「既有豁免列被改長了 84 bytes」。
處置照它自己指定的合法出口——**把那一列縮回去**，不是調高常數。

### 本輪實際換回多少容量

| | 動工前 | 收工 |
|---|---|---|
| 主檔 bytes | 256,920 | 見〈收工實測〉節 |
| 未結列 | 86 | 見〈收工實測〉節 |
| >700 bytes 的列 | 110／120 | 105／115 |

換回容量的兩個手段（都不動政策、不調任何門檻）：
① 瘦身——把 10 列的長文搬進本檔（本輪處理的就是下面那 9 個 DEF 節 ＋ `DEF-101-377`）；
② 歸檔——`python tools/archive_defect_log.py --apply --archive-num 62 --keep DEF-101-890`
把 R78 四方複審已結的 6 列搬進 `AutoSDD_Defect_Log_archive_62.md`（實測釋出 4,927 bytes，
`--check` rc=0）。`--keep` 是刻意的：`DEF-101-890` 是本輪新立列，依帳本標頭政策留主檔。

---

## DEF-101-810（R79 結案取證）

> 🔴 **標題刻意不是裸錨 `## DEF-101-810`**：該 ID 的證據節已住
> `CrossPlatform_R75_Review_Evidence.md`（立帳詳情），而
> `TestEvidenceFamilyPointersResolve::test_no_anchor_lives_in_two_files_at_once` 明令
> 同一個 DEF-ID 的證據節不得同時出現在兩份檔（那代表拆分時複製而非搬移）。本節是**另一
> 件事**（R79 的結案取證），故用非錨標題；帳本該列指向立帳詳情的機械指針仍指 R75 那一份。

**定案：結案（`fixed@R77`）。** 連續三輪（R76／R77／R78）把一件**已經做完**的事寫進 backlog。

**當回合取證**（我親跑，非採信掃描報告）：

```
Push-Location AutoClaude; python -m pytest tests/tools/test_run_local_nightly_static.py -q -k "cli or help or unknown"
→ 19 passed, 81 deselected in 3.69s   rc=0
```

`AutoClaude/tools/run_local_nightly.ps1:109` 已是頂層 `param([switch]$Help)`，`:144-147`
`if ($Help) { …; exit 0 }`、`:148-152` 未知參數 `exit 2`；回歸鎖住
`AutoClaude/tests/tools/test_run_local_nightly_static.py:2275` 起的「組一：CLI 契約」，
內含順序鎖 `test_cli_guard_precedes_every_disk_and_cross_process_side_effect`
（斷言 guard 早於 Mutex 與 log 目錄建立）——**比「有沒有 param」嚴**。

**R76 的「當回合查證」結論已於 R77（`a7a3080`）失效**，此後三輪沒有任何一輪重驗。

**一般化的成因（本輪最值得記的一筆）**：續改派機制只驗「上一輪有沒有做」，**不驗
「有沒有別人順手做掉了」**，於是同一筆可以無限期在 backlog 裡循環而閘門全程零訊號。
建議（未落地，列入交棒）：`orphan_backlog_problems` 加一條 warn——任一列的承接輪次被
連續改派 ≥3 次時印「請先重驗它是否已被順手修掉」。

**原狀態欄全文**（逐字保全，本輪自主檔搬來）：

> open（承接輪次：**R76**）｜本列＝`DEF-101-652` 交棒殘餘的獨立載體（已結列的殘留待辦結構上進不了孤兒承接稽核） ｜🔴 承接輪次 **R79**（沿革：R76 首度改派、指定的那一輪未做完，R78 未處理故續改派，見 `DEF-101-878`）（R76 收斂包收輪時查證後改派；R76 未服務本列解鎖條件，上方原文逐字保全未動）。**當回合查證**：讀 `AutoClaude/tools/run_local_nightly.ps1` 實測 `-Help` 全檔零命中、第一個 `param(` 仍在 `:250` 且屬函式內 ⇒ 缺口原封不動；本輪七包無一持有該項（PKG-D 雖持有該檔，射程只到 drift 白名單與 GA 判準）。**解鎖條件（可直接執行）**＝在該檔頂端補 `param([switch]$Help)`＋`if ($Help) { 印用法; exit 0 }`，未知參數 rc=2，並在 `AutoClaude/tests/tools/test_run_local_nightly_static.py` 併入回歸鎖，形狀逐字比照 `.sh` 側既有的 `test_help_prints_usage_rc_zero_and_starts_no_stage`／`test_unknown_flag_fails_loud_and_starts_no_stage`（該兩支現為 POSIX-only skip，Windows 側對等鎖須以靜態文字判準寫）。

---

## DEF-101-794

**定案：結案（`fixed@R79`）。** 本列自書的解鎖條件已完全滿足。

**當回合取證，刻意走兩條互相獨立的通道**（只信偵測器等於把「調低期望值假裝達標」
這條路留著）：

① 偵測器：

```
python tools/check_scheduled_task_drift.py   → rc=0
[schedule-drift] status=ok
  - AutoClaude_Nightly: 全部 7 項設定符合期望
  - AutoClaude_WindowsSmoke: 全部 7 項設定符合期望
```

② 繞過偵測器直接問作業系統（`Get-ScheduledTask`，兩支任務逐項）：

```
TaskName : AutoClaude_Nightly       ETL : PT4H  SWA : True  WTR : True  LogonType : S4U
TaskName : AutoClaude_WindowsSmoke  ETL : PT4H  SWA : True  WTR : True  LogonType : S4U
```

這正是本列點名的 5 筆漂移（Nightly 2 筆：`ExecutionTimeLimit` `<missing>`→PT4H、
`MultipleInstancesPolicy`；WindowsSmoke 3 筆：同上兩筆 ＋ `LogonType` InteractiveToken→S4U）
修復後的狀態 ⇒ **機器真的改了**，不只是偵測器說 ok。

**副作用**：`DEF-101-795` 的解鎖條件 (a)「先服務 DEF-101-794 使 rc=0（E3 成立）」
今天已成立，它被凍在一個假前提上——這是「一筆待辦的前置已滿足而沒有任何人知道」的實例。

**誠實劃界**：偵測器輸出同時報了兩支任務「上次執行 rc=1」。那是**該工作自己**判定失敗
（要看 nightly log），不是排程設定漂移，依該檔自己的設計不影響 rc；本節不拿它當本列的證據，
也不拿它當「已全綠」的證據。

---

## DEF-101-790

**定案：結案（`fixed@R77`）。**

**本列自書的解鎖條件逐字**＝「存在一道本機閘門，在不改任何原始碼的前提下能重現
DEF-101-787 的紅」。而 DEF-101-787 的缺陷本體逐字是：`sys.stderr` 預設
`errors='backslashreplace'`，locale 編碼表達不了 CJK 時整段 hook 指引降解為 `\uXXXX` 字面。

**當回合取證**：

```
Push-Location tools\tests
python -m unittest test_check_hooks_liveness.TestBlockBashHookGuidanceSurvivesNonUtf8Locale -v
→ test_guidance_is_readable_under_non_cjk_locale_encoding ... ok
  test_guidance_is_readable_without_inherited_pythonutf8 ... ok
  Ran 2 tests in 0.074s  OK   rc=0
```

該類住 `tools/tests/test_check_hooks_liveness.py:481`，子行程環境**顯式剝除**
`PYTHONUTF8`／`PYTHONIOENCODING` 再疊 `PYTHONIOENCODING=cp1252`（＝GitHub
windows-latest en-US 的條件，逐字重現雲端那筆失敗），斷言 rc=2 且指引無逃脫字面。
它在 `tools/tests/` 樹內 ⇒ 隨 `run_root_unittests.py` 進 pre-push。**解鎖條件成立。**

**R76 為什麼判它「未落地」**：用的 grep 樣式是 `pop\(.PYTHONUTF8.`，而實作是 dict
comprehension（`{k: v for k, v in os.environ.items() if k not in (…)}`）——**查證器自己
失明**，不是工作沒做。這是本輪主軸「鎖／查證器沒有鑑別力」長在 triage 環節上的標本。

**誠實劃界（不因結案而消失）**：本列**現象欄**描述的更大結構——「九支本機閘門全部硬設
`PYTHONUTF8=1`，把區分本機與雲端的變數正規化掉」——**仍然成立**。已落地的那道閘門只
覆蓋「單一 hook 的 stderr 編碼」這一條路徑。這一段不是解鎖條件（解鎖條件是上面那句），
故不阻擋結案；它會以「已結列殘留待辦」warning 的形式每輪被印出來，要立獨立載體請另開列。

---

## DEF-101-795

**定案：`partial`，剩餘只有 (b)，分流到「需掌舵者拍板」。**

| 解鎖條件 | R79 狀態 |
|---|---|
| (a) 先服務 `DEF-101-794`，使 `check_scheduled_task_drift.py` rc=0（E3 成立） | ✅ **已達成**（見上節，本輪結案） |
| (b) 由 PM 在帳本或 ADR 明文二擇一（退場／降頻） | ❌ **需掌舵者拍板，agent 不得代決** |
| (c) 若裁定退場，照 `Scheduled_Jobs_Lifecycle_Review_R75.md` §5 D-4 逐項執行四處改動 | 只在 (b) 裁定退場時觸發 |

E1（雲端 windows-compat-ci 連續 N 次綠）與 E2 在 R75 已取證達標，記錄在
`docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md` §2.2.3。⚠️ 但 `DEF-101-866`
（Actions 帳務停擺復發）尚未關閉，**E1 的持續性不得視為已保證**——這一點請掌舵者在
拍板時一併考慮，本節不代為判斷。

---

## DEF-101-796

**定案：真承接。載體已落地，實跑未做（原因是硬性的，不是順延）。**

### 載體

`tools/probe/xplat_injection_matrix.py` —— 六類「只在 mac/Linux 會炸」的注入 × 三關
攔阻矩陣，逐類自帶還原與**還原後雜湊比對**（還原不完全即 fail-loud），預設 `--dry-run`
只列不改樹，`--apply` 才真的動檔案。用法與六類定義寫在該檔檔頭。

### 六類的可考性（誠實劃界，不得誤讀為「逐字還原了 R74 的六類」）

帳本該列寫「R74 記載的六類」，而**那六類的逐字內容今天在磁碟上查不到**：`Grep 六類`
全 repo 只命中該列自身與 `ADR-XPLAT-002:396`（後者講的是別的東西）。所以本輪的六類是
**依 R74 該列的敘述與根 `CLAUDE.md` 鐵律三的觸發清單重新定義**的，並在載體檔頭逐條寫明
判準與「為什麼它只在 mac/Linux 會炸」。⇒ **與 R74 的 2/6 基線只能做量級比較，不得逐格對照**。

### 為什麼本輪不實跑

注入會就地改動共用工作樹。依 `DEF-101-886`，本輪有 6 個修復包同時在改樹，此時量到的
任何 rc 都是「別人鍵盤的函數」，而我的注入也會污染別人。這不是把工作往後推——載體已經
在磁碟上、可重跑；缺的是一個**全包停工的窗口**，那是輪次層級的排程，不是本包能製造的條件。

### 解鎖條件（可直接執行）

在全包停工窗口內跑 `python tools/probe/xplat_injection_matrix.py --apply`，把它印出的
矩陣貼進本節下方，並與 R74 的 2/6 基線並列。

### 攔阻矩陣（R79 收尾單人窗口實跑，`--apply`）

當回合實跑 `python tools/probe/xplat_injection_matrix.py --apply`，rc=0，
末行逐字 `✅ 還原完全：注入前後 `git status --porcelain` 逐字相同`。原始輸出：

| 注入類別 | posttooluse-hooks | pre-commit | root-unittest |
|---|---|---|---|
| sh-crlf | PASS-THROUGH | PASS-THROUGH | PASS-THROUGH |
| posix-sep | PASS-THROUGH | PASS-THROUGH | PASS-THROUGH |
| case-mismatch | PASS-THROUGH | PASS-THROUGH | PASS-THROUGH |
| win-only-api | PASS-THROUGH | PASS-THROUGH | PASS-THROUGH |
| env-pathext | PASS-THROUGH | PASS-THROUGH | PASS-THROUGH |
| win-only-skip | PASS-THROUGH | PASS-THROUGH | PASS-THROUGH |

工具自印合計＝`0/6 類至少被一關攔下（R74 基線＝2/6）`。雲端 CI 那一格本檔不量，`N/A`。

### 🔴 這個 0/6 **不是**攔阻率量測值，本列因此**不結案**

收尾者在把上表寫進本節前先問了一句「0/6 比 R74 的 2/6 還差，是護欄退步了嗎」，
逐項回查之後答案是**兩者都不是**——**載體自己有缺陷，這一輪量的東西沒有意義**。
逐字記錄，因為「拿到一張看起來像數據的表就照抄」正是本 repo 反覆在治的形態：

1. **注入位置落在所有掃描面之外（六格全中，這一項單獨就足以否定整張表）。**
   沙箱是 `_REPO/_xplat_injection_sandbox/`＝一個**新開的頂層目錄**。而主要消費者
   `tools/tests/test_platform_neutral_paths.py` 的掃描面是 `_scan_roots()` **逐項列舉的目錄清單**
   （`tools/tests`、`tools`、`tools/lib`、`.claude/hooks`、`AutoClaude/{autoclaude,tools,tests,scripts,alembic}`、
   `AISDLC_SDD/scripts`、LATEST `fsm_runtime` 等）＋ `_scan_single_files()` 兩支具名檔。
   新頂層目錄**不在任何一個掃描根底下** ⇒ 六類注入對這些鎖**結構上不可見**，
   PASS-THROUGH 量到的是「檔案放在沒人看的地方」，不是「鎖沒有鑑別力」。
2. **`sh-crlf` 那一類根本沒有注入 CRLF（payload bug）。**
   payload 寫的是 `_BS + "r" + _BS + "n"`，而 `_BS = chr(92)`＝**反斜線**
   ⇒ 落到磁碟的是**字面兩字元** `\` `r`，不是 CR。實測該檔 **34 bytes**＝
   `#!/usr/bin/env bash`(19) ＋ `\r`(2) ＋ `\n`(2) ＋ `echo hi`(7) ＋ `\r`(2) ＋ `\n`(2)，
   全檔一個 CR 位元組都沒有。⇒ 該格 PASS-THROUGH 是**正確行為**（沒有東西該被攔）。
   同一格還疊了第二層失明：`TestWorktreeEolMatchesPolicy` 讀 `git ls-files --eol`，
   而那條管道**只涵蓋 tracked 檔**，未追蹤的沙箱檔就算真的是 CRLF 也照樣看不到。

⇒ **本輪的處置**：解鎖條件字面上（「停工窗口跑 `--apply` 並把矩陣貼進本節」）已執行完畢，
但把它判成 `fixed` 等於把一張**已知失實**的 0/6 表釘成本 repo 的攔阻率基線，
那是「有鎖在守假話」的原形。**狀態維持不變，改派 R80**，並把上面兩筆載體缺陷寫成
可直接照做的修法。這一趟不是白跑：R74 以來四輪「六類注入」零可重跑產物，
本輪第一次真的跑起來，而**第一次跑就把載體自己的兩個缺陷曝出來**——這正是實跑的價值。

### 帳本該列原狀態欄全文（逐字保全，一字未改）

> **partial@R74**（承接輪次：**R75**）｜🔴 承接輪次 **R79**（改派沿革見 `DEF-101-878`）。R79 真承接：**載體已落地**＝`tools/probe/xplat_injection_matrix.py`（六類「只在 mac/Linux 會炸」注入 × 三關攔阻矩陣，逐類自帶還原與還原後雜湊比對；預設 `--dry-run` 只列不改樹）。**未做＝實跑**：注入會就地改共用工作樹，依 `DEF-101-886` 只能在其他 agent 停工的窗口內跑。解鎖條件＝停工窗口跑 `--apply` 並把矩陣貼進 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-796` 節（六類定義與 2/6 基線的可考性亦記於該節）

### 給 R80 的載體修法（可直接執行，缺一不可）

1. **沙箱移進掃描面**：`_SANDBOX` 由 `_REPO/_xplat_injection_sandbox` 改為
   **既有掃描根底下**的目錄（例如 `tools/probe/_injection_sandbox/`——`tools` 是遞迴掃描根）。
   ⚠️ **不要選 `tools/tests/`**：該樹的 `.py` 檔數受 shrink-only 棘輪管，新增檔會讓根層
   unittest 因**別的理由**轉紅，量到的仍是 `RED-BUT-UNRELATED` 而非 `BLOCK`。
2. **`sh-crlf` payload 改注入真正的 CR**：`chr(13) + chr(10)`（不是 `_BS + "r"`）。
   `_BS` 那個寫法本來是為了避開靜態掃描器誤判，但它對 CR 這一類是**語意錯誤**不是規避。
3. **該類另需一條 tracked 通道**：`git ls-files --eol` 看不到未追蹤檔 ⇒ 要嘛在 gate 前
   `git add` 該檔（`needs_stage` 已有此機制，把它擴到 `root-unittest` 那一關），
   要嘛在矩陣上把該格標成 `N/A（判準只涵蓋 tracked）` 而不是 `PASS-THROUGH`。
4. **改完後重跑一次全六類**，並在本節下方以 before/after 兩張表並列——
   舊表（本節上方那張）**保留不刪**，它是「載體缺陷會長成什麼樣」的樣本。

---

## DEF-101-797

**定案：真承接，但**當輪內轉包**——不再順延輪次。**

**R79 復驗兩處違規原封不動**（我親讀，非採信）：

- `tools/tests/test_ps_engine_ssot.py:719` 逐字 `_SCAN_ROOT = Path(__file__).resolve().parents[1]`
  （＝`tools/`），`:735` 另硬斷言樹根名必須是 `tools` ⇒ `AISDLC_SDD/scripts/tests/`
  仍不在反增生鎖射程內。
- `AISDLC_SDD/scripts/tests/test_install_post_commit_windowsapps_guard.py:67-68` 的
  `_pwsh_exe()` 仍是 `shutil.which("pwsh") or shutil.which("powershell")`（pwsh 優先，
  與 `DEF-101-509` 拍板的「生產引擎 5.1 優先」方向相反）。

**為什麼不是本包做**：兩支檔都不在本包持有面內，而本輪 6 包並行改樹，越界編輯會互相覆蓋。

**可直接照做的修法**：

1. 把 `_SCAN_ROOT` 的單一樹根改成一組樹根（`tools/` ＋ `AISDLC_SDD/scripts/`），
   並把 `:735` 的「樹根名必須是 tools」自檢改成「每個樹根都必須存在且非空」——
   那道自檢的意圖是「本檔被搬走時要 fail-loud」，換成多樹根後意圖不變。
2. 修 `_pwsh_exe()` 為 `shutil.which("powershell") or shutil.which("pwsh")`，並在該處
   寫明 WHY 指向 `DEF-101-509`（生產引擎是 schtasks Action 跑的 5.1）。
3. **驗收（缺一不可）**：先只做 1 不做 2 ⇒ 該鎖必須**當場轉紅**並具名點出
   `test_install_post_commit_windowsapps_guard.py`；再做 2 ⇒ 轉綠。兩個方向的 rc 都要貼。

---

## DEF-101-798

**定案：分流到「需掌舵者拍板」，不再列入一般 backlog。**

**R79 復驗**：`Grep 'enforce_docs_path|loc_budget_check|check_lang|claude_md_freshness'
.claude/settings.json` → **0 命中**，那 4 支仍未橋接到根層。

**為什麼這不是實作待辦**：把它們橋進根層＝改變**每一個**根 session 的行為，而其中
`enforce_docs_path.py` 是 **PreToolUse deny** 形態——該檔自己記載過「hook 誤觸 deny 會把
所有工具硬鎖死」的 P0。這是政策決定（要不要讓根 session 也受 AutoClaude 的文件路徑／LOC
預算／語言／CLAUDE.md 新鮮度四項管轄），不是誰有空就能做的工。

**逐支風險**（供拍板參考，未實測其行為，**不得引用為已驗證**）：

| hook | 形態 | 主要風險 |
|---|---|---|
| `enforce_docs_path.py` | PreToolUse deny | 🔴 最高：deny 面誤觸即全工具鎖死；且根層 `docs/` 的編號規則與 AutoClaude 的未必同義 |
| `loc_budget_check.py` | PostToolUse | 中：會對根層 `tools/` 的檔套 AutoClaude 的 tier 語意，兩層度量面已知不同 |
| `check_lang.py` | Stop（warn-only） | 低：只 warn |
| `claude_md_freshness.py` | — | 中：它守的是 `AutoClaude/CLAUDE.md` 的 snapshot，在根 session 下標的可能落空 |

**若拍板要做，執行順序**（每一步都要有可回退點）：
① 先只橋 `check_lang.py`（warn-only，零阻斷風險），跑一輪確認根 session 正常；
② 再橋 `loc_budget_check.py`，並先確認它對根層 `tools/` 的判準不會與 `SPECIAL_FILES`
   raw-line 棘輪雙重審判同一支檔；
③ `enforce_docs_path.py` 最後，且橋接前必須在一個可丟棄的 session 裡實測「觸發時的
   exit code 與訊息」；④ 同一次變更同步根 `CLAUDE.md` 那兩條列的射程措辭——該處有
`TestR74RootClaudeMdHookClaimsMatchRegistration` 的**雙向**判準在守，寫錯方向同樣會紅。

---

## DEF-101-802

三項各自定案，不再整列順延。

### ① 護欄層規模三元組（UEP／AC／GLC）R70~R73 四輪未回填 —— **明文關閉**

本列自書的解鎖條件給了二擇一：「以 `git worktree` 逐 commit 前後各量一次並回填，**或**
明文放棄回填並在本列記錄放棄理由（禁止推算硬填）」。取後者，理由是**回填的對象已經不存在**：

- `ADR-XPLAT-002:637` 逐字：「🔴 **R75 裁決：逐輪「手抄登記」廢除，改由機械物承接。
  本節此後不再要求任何人抄任何數字。**」
- 同節 `:672` 逐字：「本節此後不再新增表列」——而 ① 要做的正是**往該表新增表列**。
- `:650-652` 另載明：抄進去的內容「本節自己判為不合格資料」。
- `CrossPlatform_Scan_Dimensions.md:126-127` 亦逐字記載該登記已由 ADR §4.3.1 明文廢除。

⇒ 回填是「對一個已廢除的機制補資料」。**放棄回填不是偷懶，是不製造已被判為不合格的資料。**

**這一筆的形態值得記**：一筆待辦被上游決策取消時，帳本這一側**沒有任何機制會知道**
（ADR 與帳本之間沒有雙向綁定），於是取消只發生在 ADR 裡、帳本繼續派工三輪。

### ② UEP 階梯末階需 PM signoff，而回執容器是空表 —— **需掌舵者拍板**

`ADR-XPLAT-002:468` 逐字「UEP 自 R65 起停在 **5**，連續 8 輪 ΔUEP＝0」；§8.1 signoff
記錄至今**零回執**（空表本身即證據）。結構上不可能由修復包單方完成，故分流到需拍板清單。

### ③ 逐列檢視 `ADR-XPLAT-002` §8 交棒表尚開著的列 —— **已做完**

當回合逐列讀 §8（`:1236-1251`），未刪除線的列共 7 筆，逐列處置如下：

| # | 標的 | 承接者欄現況 | R79 處置 |
|---|---|---|---|
| 7 | 護欄層 LOC 預算未設計 | 未指派（前置＝PM signoff） | **維持**；合法形態（「未指派」）。降維選項（只量不判的報表）零 signoff 需求，是唯一可繞開阻塞的路，建議下輪認領 |
| 8 | `ci-gate.ps1` fallback 刪除政策未拍板 | 未指派（前置＝PM signoff） | **維持**；另需一台無 Git Bash 的 Windows，本機造不出鑑別力 |
| 9 | CI workflow 層在 ADR 射程外 | 未指派（需新機制） | **維持**；殘餘缺口已收斂為單一方向（mac 側單邊新增 job 零訊號），可承接 |
| 10 | Copy-on-Evolve 對跨語言對子無解 | 未指派（政策層） | **維持**；掛 `DEF-101-392`／`401`，本 ADR 不取代那筆決策 |
| 11 | `Find-GitBash` 單源化 NO-GO | 封存中，解除前置＝Phase 2-B | **維持**；解除判準三條全在文件內、可機械查 |
| 13 | `report_heartbeat()` 收斂 | 未指派（具名角色＝下一個 macOS 真機輪） | **維持**；R67 表頭規則 1(1a) 明文允許「可機械查的具名角色」 |
| 14 | §8 與 §5 各 Phase 表無機械對應 | (c)(d) 未指派 | **維持**；純掃描器、成本低，可承接 |

**結論**：7 列**沒有一列**違反 R67 表頭三規則（承接者欄全是「具名輪次／未指派／可機械查
的具名角色」、signoff 一律指向 §8.1 這個真實容器、完成判準欄無寫死量測常數）⇒ ③ 要求的
「各標註處置」由本表完成，**ADR 本身不需要改動**（它不在本包持有面內，本輪亦未代改）。

---

## DEF-101-803

**定案：真承接，但**當輪內轉包**——不再順延輪次。**

**R79 復驗結構性修法仍未落地**（我親讀 `tools/tests/test_run_root_unittests.py`）：

- `:1280` 逐字「結構性修法（探針不應在套件內重跑整套）已登記 DEF-101-803，承接輪次見該列。」
- `:1283` 逐字「執行整棵 `tools/tests/`，其中就包含本類別 ⇒ 孫探針、曾孫探針…只被逾時值截斷。」
- `:1396` 逐字「就會遞迴生出孫探針、曾孫探針，只被逾時值截斷（DEF-101-803 實測：整套牆鐘 823s→3813s …」

⇒ R74 的止血（放寬逾時＋同參數快取）仍是現況。

**為什麼不是本包做**：`tools/tests/test_run_root_unittests.py` 不在本包持有面內，而它是
本輪並行度最高的一棵樹裡最容易撞編輯衝突的檔之一。

**可直接照做的改法**：

1. `_run_zero_dep_probe("floor", …)` 改為對一棵**受控 fixture 樹**（tmp 目錄、N 支合成
   測試）叩 `run_with_floor()` 的下限層——那才是它要證明的東西（下限層會不會說話）。
2. 「真實樹的收集塌縮」改以**收集面數字**驗證（`unittest.defaultTestLoader.discover()`
   的 `countTestCases()`），不實跑。
3. 逾時值改為與 fixture 樹規模掛鉤的常數，**與每輪測試成長脫鉤**。
4. **驗收**：貼改前／改後的牆鐘秒數與 rc 對照；並注入一次「fixture 樹少一支測試」證明
   下限層仍會轉紅（否則 1 的改法會讓探針失去鑑別力）。

---

## DEF-101-377

**定案：補登 `.py` 半邊的現況與處置方向；實作轉包（`.gitattributes` 不在本包持有面內）。**

**當回合實測**（`git ls-files --eol`，不經任何行為推論）：

| glob | 總數 | `w/lf` | `w/crlf` | `w/mixed` | `w/none` |
|---|---|---|---|---|---|
| `*.py` | 5478 | 1251 | **4175** | 1 | 49 |
| `*.sh` | 168 | 168 | 0 | 0 | 0 |
| `*.ps1` | 136 | 0 | 136 | 0 | 0 |

`.gitattributes` 宣告 `*.py text eol=lf`、`*.sh text eol=lf`、`*.ps1 text eol=crlf`
⇒ `.sh` 與 `.ps1` 兩向皆與政策一致（R78 修復仍有效），**唯獨 `.py` 從本列立帳起一行未動**
（立帳原文就點名過「~4225 支 .py」）。

**為什麼它今天仍不是 P1**：blob 側全為 LF（`git status --porcelain` 乾淨、任何全新 clone
皆正確），本機沒有任何已知功能失效。真正咬人的路徑與 `.sh` 同構——任何以**位元組**為單位
讀寫 `.py` 的工具（雜湊釘選、raw-line 棘輪、外部 parser、act 容器內跑工作樹）在本機量到的
數字會與 fresh clone 不同，而 `git status` 全程乾淨 ⇒ 差異只會在別處以「無法解釋的數字
漂移」現形。

**處置方向（兩步，且不得合併）**：

1. **止血**——併入既有 `tools/tests/` 檔（該樹逐檔行數為棘輪，不得新增 `.py`），以
   `git ls-files --eol` 對 `attr eol=lf` 的路徑斷言 `w/` 非 crlf、對 `attr eol=crlf` 的
   路徑斷言 `w/` 非 lf。🔴 **現況 4175 支違反，直接硬擋會讓本機 pre-push 永紅**
   （`ARCH-R59-NB4`）⇒ 照本 repo 既有形狀：釘現況為具名／計數基線，只對**新增與改動的檔**
   硬擋，基線只准往下。
2. **歸一**——在**所有包停工的窗口**內對 `.py` 做一次 renormalize，前後各記一次
   `git ls-files --eol` 計數與 `git status --porcelain` 是否為空。

**本包不做的部分（轉包，見交件回報 `needs_from_other_packages`）**：`.gitattributes`
由 XPLAT 包持有；根 `CLAUDE.md` 鐵律三那張機械物盤點表要補一列「`.py` 行尾：無機械物」
（新增一列＝分母升、分子不動 ⇒ 覆蓋率棘輪判綠，**誠實登記沒有代價**）由收斂包處理。

---

## 其他 5 包的帳本列登記區（收斂包填入）

> 🔴 **本區塊是刻意預留的**：本輪 6 包並行，其餘 5 包的 `defect_log_entries` 在本包收工時
> **還收不到**（他們與我同時在跑）。收斂包請把各包回報的列**直接寫進主檔的缺陷總表**
> （不是寫進本節——本節只是把「誰負責合流」講清楚，避免又出現一筆沒有載體的死信）。
>
> **寫入時必須遵守的三條**（前兩條是本輪新上線的機械物，違反即 `check_defect_log_crossref.py` rc=1）：
>
> 1. **新列 ≤700 bytes**（UTF-8），且**不得**把新列的 ID 加進 `OVERSIZE_ROW_GRANDFATHERED`
>    ——那條路已被 `OVERSIZE_ROW_CEILING` 堵死。長文請開一節寫進 `CrossPlatform_R79_*.md`
>    具名證據檔，列上只留一句話與節指針（節指針受 `TestEvidenceFamilyPointersResolve` 看守）。
> 2. **不得把既有豁免列改長**——`OVERSIZE_ROW_EXCESS_CEILING` 零成長容忍。要在既有列
>    追記 R79 回執，請追記**一句話＋節指針**，或在同一次變更內把別的列縮回等量以上。
> 3. 列內**禁半形直線符號**（欄位切分器只認未被反斜線前導的 `|`；字面豎線寫成 `\|`）。
>
> **另外兩件收斂包必做的事**（本包無權處理）：見交件回報的 `needs_from_other_packages`。

---

## 收工實測

> 本節的數字由收斂包在所有包停工後的單人窗口重取一次；本包收工當下的自量值見交件回報
> 的 `verification` 欄。**刻意不在本檔寫死一組會過期的數字**——量測值一律現查：
>
> ```
> python tools/check_defect_log_crossref.py --unresolved-count
> python tools/check_defect_log_crossref.py
> python tools/archive_defect_log.py --check
> python -m unittest test_check_defect_log_crossref.TestR79RowByteCeiling   # 於 tools/tests/
> ```

---

## R79 各修復包交件回報原文（DEF-101-896 ～ DEF-101-929 的來源）

> 本節由 R79 收尾補列作業寫入。主檔那 34 列是**索引**（每列 ≤700 bytes），各包交件回報的**原文逐字**保全於此，一個字未改寫。原文內的自編號（OBS-1、R79-XPLAT-3、ARCH-5 之類）是各包內部編號，與主檔 DEF-ID 的對應即本節小節標題。


## DEF-101-896

**來源包**：OBS｜觀測者（攔截器 hook ＋ 量測器 probe ＋ 守它們的鎖）

```text
DEF-101-NNN（ID 由 DEBT 指派）；2026-08-07；R79 OBS 掃描＋pwsh 7.6.4 真機注入；攔截器 _RC_RESET_RE 把「提到」當成「執行」：2>&1 的 & 與任意位置的 .exe 皆被判為 rc 已重設，實測三種語句一個都沒重設，端到端重現真 rc=7 讀成 0；P1；fixed@R79（左邊界加 >、副檔名收到語句開頭、抽 _statement_resets_rc）；證據 tools/tests/test_check_hooks_liveness.py::RC_RESET_PAIRS，注入 7 failures，913 條真實指令對照 149→150
```

## DEF-101-897

**來源包**：OBS｜觀測者（攔截器 hook ＋ 量測器 probe ＋ 守它們的鎖）

```text
DEF-101-NNN（ID 由 DEBT 指派）；2026-08-07；R79 OBS；naked-cd 尾巴硬性要求一個參數，不帶參數的 cd／sl／chdir／Set-Location 整條放行，而它切到 $HOME 破壞性更大；P2；fixed@R79（尾巴改可選，hook 與 probe 兩份逐字同步）；注入還原舊 pattern 兩側各紅（failures=3 與 2），MUST_BLOCK 新增 4 列、_PARITY_HITS 新增 1 列
```

## DEF-101-898

**來源包**：OBS｜觀測者（攔截器 hook ＋ 量測器 probe ＋ 守它們的鎖）

```text
DEF-101-NNN（ID 由 DEBT 指派）；2026-08-07；R79 OBS；行內豁免比對原文，任何在字串裡引述 ps-lint-ok 標記的指令會一次關掉三條檢查且無痕跡；P3；fixed@R79（mask_regions 加 keep_comments，只認住在真註解裡的標記；舊版防撇號誤擋的理由已保住，遮蔽器先看到井號就跳到行尾）；注入還原比對原文 rc=1 failures=1
```

## DEF-101-899

**來源包**：OBS｜觀測者（攔截器 hook ＋ 量測器 probe ＋ 守它們的鎖）

```text
DEF-101-NNN（ID 由 DEBT 指派）；2026-08-07；R79 OBS；量測器自寫扁平正則，兩個相反方向同時失準：視窗只跨一個換行使多行指令整類隱形（低報），不切語句不比位置使 CLAUDE.md 教的正解被算成違規（高報、符號相反）；P1；fixed@R79（改借攔截端 _rc_after_pipe）；913 條真實指令實測 probe 162→150、兩端分歧 15→0；注入還原扁平正則 failures=8
```

## DEF-101-900

**來源包**：OBS｜觀測者（攔截器 hook ＋ 量測器 probe ＋ 守它們的鎖）

```text
DEF-101-NNN（ID 由 DEBT 指派）；2026-08-07；R79 OBS；三筆觀測者失真合記：--latest 窗被同期 agent 逐字稿汙染（同指令一小時三組數字）、鐵律四觀測者佐證條件近乎恆真（本輪窗 0/72）、inline-loop 混入慣用管線；P2；fixed@R79（必印量測窗清單＋--exclude／--exclude-self、EVIDENCE_RE 去除裝飾字元且窗 12→3 附敏感度表、迴圈欄拆兩欄並標明無攔截端）；四道注入各自轉紅
```

## DEF-101-901

**來源包**：OBS｜觀測者（攔截器 hook ＋ 量測器 probe ＋ 守它們的鎖）

```text
DEF-101-NNN（ID 由 DEBT 指派）；2026-08-07；R79 OBS；R77 的失誤歸因百分比無任何可重跑產物，使 CLAUDE.md 的 Windows 失誤根因成為不可稽核常數（同 R71 n=8 模型被沿用五輪的形態）；P2；fixed@R79（新建 tools/probe/misstep_attribution.py，來源清單為檔內 SSOT、桶具名附判準、平手一律 OTHER、逐筆附歸屬理由、語料塌了 rc=1、判準性質由腳本自印）；重跑結果見 needs_from_other_packages，四道注入全紅
```


## DEF-101-902

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-01 P1 FIXED pg-contract 硬閘吞掉 pytest rc。GHA 未宣告 shell 時走 bash -e（無 pipefail），`tee` 讓管線 rc 恆 0；census 只數 passed 與 skipped 不看 failed。實測重放 tail「3 failed, 1238 passed, 40 skipped」判定零問題、rc=0。修法：run 首行 set -o pipefail、真 rc 以 OR list 顯式接出，census 由 2 道增為 4 道。注入證明 scratchpad/proof_pgcontract.py（修前 rc=0、修後 rc=1）。檔 .github/workflows/autoclaude-ci.yml
```

## DEF-101-903

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-02 P1 FIXED 全 repo 對 runtime skipped 數零管轄（唯一天花板 PG_CONTRACT_MAX_SKIPPED 只覆蓋一個 job、local_ci_gate 對 skipped 零字樣、根層 runner 只印不判）。新建 tools/lib/skip_group_policy.py：7 標籤 6 群、逐群天花板加 shrink-only 守護（雙單邊：上限只准降、群數只准增），消費者 local_ci_gate.check_skip_census 併進 rc。六向注入全部轉紅、誠實登記新群不轉紅。證明 scratchpad/proof_census.py
```

## DEF-101-904

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-03 P1 FIXED 標籤詞彙鎖看不到唯一已知違規：輸入面只吃字面 reason，[TOOL-MISSING] 住在函式體 f-string 裡故隱形三輪。windows_skip_tags 新增 nonliteral_skip_reason_prefixes（取 JoinedStr 開頭常數片段），接進已消費 rc 的靜態閘門。加寬後當場多看見 3 個未登記標籤，以獨立帳 _NONLITERAL_TAG_DEBT 登記。注入 [BOGUS-TAG]：修前 0 筆、修後 1 筆、還原 0 筆。證明 proof_vocab.py
```

## DEF-101-905

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-04 P2 FIXED tests/perf/test_pgvector_recall_perf.py 自 2026-06-12 起零通道零執行且壞掉。全 repo 無處設 PG_REAL_ENABLED；首次真跑 TypeError（建構子與 search 兩處簽章皆錯）；修好簽章後再揭一層單位錯誤（每樣本 100 次查詢對上每次查詢 50ms 的 SLA，差 100 倍，實測 p95=4403.8ms）。改 from_dsn 與具名參數、每樣本 1 次查詢 runs=100、加語料前置檢查；通道補進 pg-e2e-nightly。修後本機 1 passed in 4.87s
```

## DEF-101-906

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-05 P2 FIXED alembic 鏈完整性偵測器只跑在它不可能失敗的環境（雲端每次全新 container）。判準加寬為四支 revision 六個 pg_proc 產物的 oracle（TestMigrationChainIntegrity），通道改由本機 PG 自動偵測對長壽 DB 跑。注入：對 scratch DB 把 0012 的 try_acquire_import_lock 改名 → 1 failed；還原 → 1 passed。誠實劃界：抓得到 alembic stamp，抓不到 pg_dump 建起的 DB。檔 AutoClaude/tests/contract/test_alembic_0010_fk_three_step.py
```

## DEF-101-907

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-06 P3 FIXED runner 把 6 筆結構性 POSIX-only 印成未標籤，與 5 筆真環境性 skip 同桶，害 S3 分流把可救回的工作量高估一倍。test_dev_start_ps1_lastexitcode.py 的類別層 skipIf reason 補 [POSIX-NATIVE-ONLY] 前綴，_POSIX_TAG_RATCHET 與其 CEILING 的 tools/tests 一起由 1 下修為 0。注入：拿掉標籤即 1 筆紅；把基線改回 1 而天花板留 0 亦 1 筆紅。runtime 實跑 6 支全部認成已標籤
```

## DEF-101-908

**來源包**：SKIP｜pytest skipped 徹底解決（掌舵者系統問題 S3）

```text
DEF-R79-SKIP-07 P1 FIXED 甲類 skip 靠人記得設環境變數。本機一件缺件都沒有（PG 容器 healthy、相依全裝、DB 已在 head 0018），缺的只有三個環境變數。local_ci_gate 新增 pg_autodetect（四條剎車：顯式已設、CI、本行程是 pytest、DB 未 migrate），本機預設路徑自動注入 DSN。實測 4069 passed 135 skipped → 4160 passed 44 skipped，耗時零增加、零新增 failed，91 支由 skip 轉 passed。證明 proof_autodetect.py 與 e2e_gate.py
```


## DEF-101-909

**來源包**：CTX｜context 水位／token 排程機制（掌舵者第 2、3 點）＋ 成熟度判準（Q6）

```text
| DEF-101-909 | 2026-08-07 | R79 CTX 包（掌舵者第 2 點實測） | **context 水位守衛在 1M 模型上結構性保證在真 90% 靜默**：window 判定僅三階（env 到 peak>200K 到 200K 下界），而本機 settings 的 model 欄是 opus[1m] ⇒ 真 15%／18% 各誤喊一次燒掉兩個閂鎖，之後到 99.9% 全靜默 | P1 | 本輪修復：window 改五階＋model 標記交叉否決；閂鎖鍵改含 window | fixed@R79：注入紅綠見 `tools/tests/test_context_budget_guard.py::WindowSourceOrderTest` 與 `::LatchRearmTest`；真機 --check 由 96.4% 修正為 19.3% |
```

## DEF-101-910

**來源包**：CTX｜context 水位／token 排程機制（掌舵者第 2、3 點）＋ 成熟度判準（Q6）

```text
| DEF-101-910 | 2026-08-07 | R79 CTX 包（掌舵者第 2 點） | context guard 的立案 docstring 逐字寫「實查三處」而**獨漏 harness 自己**：`claude --help` 有 `--autocompact <auto 或 tokens>`，二進位內開關預設 true ⇒ 花一輪做偵測器卻沒查內建解 | P2 | 本輪修復：docstring 補第四處並收斂角色；planner 新增 `--check-autocompact`（關閉時 rc=1）；另補 PreToolUse 阻斷模式讓 90% 真的擋得下來 | fixed@R79：本機實測 autocompact 開啟、window=auto；阻斷注入見 `::PreToolUseBlockTest` |
```

## DEF-101-911

**來源包**：CTX｜context 水位／token 排程機制（掌舵者第 2、3 點）＋ 成熟度判準（Q6）

```text
| DEF-101-911 | 2026-08-07 | R79 CTX 包 | **M5 可用「加十幾題現行判準已經攔得到的語料」刷過門檻而三支現行鎖全綠**：門檻是比率、棘輪釘的卻是絕對攔截數，分母不受任何約束 ⇒ 專門防刷分的成熟度 SSOT 自己有一條可以刷 | P2 | 本輪修復：門檻由比率改成「未攔到題數」，並鎖住「已知攔不到的題不得被刪掉」 | fixed@R79：注入紅綠見 `tools/tests/test_maturity_criteria_r79.py` |
```

## DEF-101-912

**來源包**：CTX｜context 水位／token 排程機制（掌舵者第 2、3 點）＋ 成熟度判準（Q6）

```text
| DEF-101-912 | 2026-08-07 | R79 CTX 包 | **M6 的達標判定綁在帶輪次號的凍結盤點檔上**——R78 ARCH-05 搬了判準表卻沒搬證據面 ⇒ M6 既無法宣告達標也無法被證偽 | P3 | 本輪部分修復：M6 量測配方改為指向現查載具＋當輪 rc，並上鎖禁止再指向帶輪次號檔名 | partial@R79：盤點檔本身改輪次中立檔名屬 SKIP 包射程，未做 |
```

## DEF-101-913

**來源包**：CTX｜context 水位／token 排程機制（掌舵者第 2、3 點）＋ 成熟度判準（Q6）
**收窄包**：R79 複審後 D089 包（SD blocking B05 ＋ SA nonblocking「假話原封留在三處」）

```text
| DEF-101-913 | 2026-08-07 | R79 CTX 包（context 水位與排程機制） | archive_16 的 DEF-101-089 原結論**只在 `claude -p` subprocess 這條路被推翻**（rc=0／4.0s、3.6s），連帶「排程重啟路徑無法從 session 內部驗證」亦不再成立；11 支 skip 實走的 wexpect pty 路不在該反證射程內 | P3 | planner 新增三支 schtasks 旗標並真跑取證；收斂輪補測 pty 路、把結論收窄到 subprocess 並同步 CLAUDE.md 與兩支測試檔 reason | fixed@R79：喚醒四項實測全對＋probe 已移除；pty 路 `start()` 三次皆未回返（180/180/45s）故 skip 續留，證據見 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-913` 節 |
```

原列（收窄前）的 schtasks 側實測數字在此保全，不因收窄而遺失：
`NextRunTime=2026/8/7 下午 03:09:22`、四項喚醒設定實測全對、probe 工作已移除並驗證不存在。

### 為什麼非收窄不可：反證與 skip 判準量的不是同一條路

CTX 包的反證外呼 `claude -p`，走 `subprocess.Popen` ＋ pipe。被 `requires_claude_cli`
擋住的那 11 支走的是**另一條**：`PtyWrapper.start()` 在「解析結果不是 `.cmd`/`.bat` shim
**且** wexpect 可用」時進 `_start_wexpect()`，也就是 `wexpect.spawn()`。當回合探針逐字：

```text
shutil.which('claude') = 'C:\Users\wuwei\.local\bin\claude.EXE'
  lower endswith .cmd/.bat = False
wexpect AVAILABLE, version = 4.0.0
=> start() will take: _start_wexpect
```

`.EXE` ⇒ 不是 shim ⇒ 不走 `_start_subprocess()`。**這 11 支的實際情境從來就不在
`claude -p` 那條反證的射程內**，兩件事被當成同一件事講。

### 補測結果（wexpect pty 路，同一個巢狀 session）

載具＝直接驅動 `PtyWrapper`，內建 watchdog 到點 `os._exit(99)`（避免把工具卡死）。

| # | 條件 | 硬上限 | rc | 牆鐘 | 進度 |
|---|------|--------|----|------|------|
| 1 | 繼承 `CLAUDECODE=1` | 180s | **99**（watchdog） | **180.16s** | 停在 `[0.23s] start() 呼叫前`，`start()` 未回返 |
| 2 | **剝除** `CLAUDECODE` 的對照組 | 180s | **99**（watchdog） | **180.05s**（外層 180.18s） | 停在 `[0.22s] start() 呼叫前`，同上 |
| 3 | 繼承，並於 t+22s 快照行程樹 | 45s | **99**（watchdog） | — | 同上 |

三次都掛在 `start()`，**連讀取迴圈都沒進到**。第 3 次的行程樹快照說明掛在哪：

```text
37856 python.exe   (探針)
 24864 python.exe  (wexpect 對本檔的再 exec)
  7964 python.exe  -m wexpect --console_reader_class=ConsoleReaderPipe --host_pid=...
   37108 conhost.exe
   7652 python.exe -m wexpect ...
```

同一刻 `Get-CimInstance Win32_Process -Filter "Name='claude.exe'"` 只有 3 支既存的
Claude Code session（01:18:50／02:23:58／07:52:20，parent 皆 9440）——**`claude.EXE`
從頭到尾沒有被啟動**。掛的是 wexpect 自己的 host↔console-reader 交握，與 `claude` 無關。

### 對照組的意義：`CLAUDECODE` 是**標記**不是**成因**

第 2 列（剝除 env var）行為與第 1 列完全一樣 ⇒ 掛起不是那個變數造成的，它只是「人正處在
Claude Code session 這個執行環境」的可靠標記，而該環境才是 wexpect 交握不成立的地方。
這與判準的**效果**不衝突（在該環境內 skip 是對的），但它讓「因為 `CLAUDECODE=1` 所以會
死結」這句因果敘述不成立，reason 文字因此改寫。

### 反方向證據：非巢狀環境這條路是通的

`AutoClaude/logs/nightly_2026-08-06_223002.log:272` 逐字
`4 failed, 4080 passed, 120 skipped in 107.28s (0:01:47)`，其 `-rs` 清單對
`test_gap014_020` 與 `test_gap039_049` **零命中** ⇒ 那 11 支在 nightly（非巢狀、schtasks
以 `powershell.exe` 起）確實跑了，而且整棵樹 107 秒跑完、沒有掛住。所以正確結論不是
「wexpect 路永遠不通」，而是「**在巢狀 Claude Code session 這個環境裡不通**」。

### 為何不走「拿掉 `or CLAUDECODE == "1"` 讓 11 支轉真跑」

該分支已由量測直接否決：拿掉之後判準只剩 `shutil.which("claude") is None`，本機
`claude` 存在 ⇒ 條件 False ⇒ 11 支會真的跑 ⇒ 依上表每一支都會掛在 `start()`，把整棵
pytest 掛死。注入實證見下方〈判準鑑別力注入〉。**因此 untagged 天花板不下修**——
skip 支數一支都沒變。

### 同一次變更內對齊的三處文字

| 站點 | 改動 |
|---|---|
| 帳本 `AutoSDD_Defect_Log.md` DEF-101-913 | 結論收窄到 `claude -p` subprocess；不逐字複述原句 |
| 根 `CLAUDE.md`〈Token 將耗盡〉節 | 原本那句「此路無法從 session 內部驗證」的斷言改為指向本節的收窄結論（不逐字複述被推翻的因果） |
| `test_gap014_020.py`／`test_gap039_049.py` 的 `requires_claude_cli` reason | 不再引用已被部分推翻的原句，改述當回合量到的事實 |

未在本包射程內、需別包處理者：`tools/session_resume_planner.py:25-26`（HANDOFF 包）、
`docs/06_quality/Skipped_Test_Inventory_R76.md:730,773`（SKIP 包）、
`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md:135`（CTX 包）。


## DEF-101-914

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-1｜P1｜fixed｜單平台專屬 API 掃描器的守衛特赦是檔案級＋純文字比對：同一組 5 筆注入只抓到 1 筆，守衛字樣寫在字串常數即可特赦全檔。改為站點級 AST 判定（祖先 if／同 block 早退守衛／def-class 平台守衛 decorator 含同檔基底類別／try 捕 ImportError 類），守衛述詞由文字比對改結構化符號比對。存量 4 筆登記於 _FOREIGN_API_SCOPE_DEBT（tools/dev_start.py，非本包所有權）。注入實測 A 1→5、C 0→1、D 0→1。機械物 tools/tests/test_platform_neutral_paths.py::TestForeignPlatformApiIsGuarded
```

## DEF-101-915

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-2｜P2｜fixed｜.ps1 行尾寫入端零強制，寫入者已溯源為 Claude Code 的 Write 工具（新建與覆寫既有 CRLF 檔都吐 LF），同一支 PostToolUse hook 只補 BOM 不碰行尾。check_ps1_encoding.py 擴為位元組正規化器（BOM＋CRLF、非合法 UTF-8 完全不動、冪等、射程不含 .sh）。LF→CRLF 對 .ps1 blob-neutral 已親驗（sha 逐字相同）。端到端實測：修前 crlf=0 lonely_lf=3、修後 crlf=3 lonely_lf=0。機械物 AutoClaude/tools/hooks/check_ps1_encoding.py 與其 6 題回歸鎖
```

## DEF-101-916

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-3｜P2｜fixed｜工作樹 .ps1 行尾漂移在本機結構上不可見（gitattributes eol=crlf 讓 index 恆為 LF、status 兩側套同一規則），hook 也繞得過。新增事後閘讀 git ls-files --eol 的 w 欄，.ps1 必 CRLF、.sh 必 LF 雙向對稱，掃描面下限 240。注入實測：把一支 tracked .ps1 轉 LF 即轉紅、原樣還原後 sha256 相同且轉綠。機械物 tools/tests/test_platform_neutral_paths.py::TestWorktreeEolMatchesPolicy
```

## DEF-101-917

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-4｜P2｜partial｜git 索引檔案模式在 Windows 結構上不可觀測（core.filemode=false，27544 支 tracked 只有 7 支 100755），而 30 個版本樹的 tools README 教 mac 使用者裸跑 ./init_project.sh（索引 100644，rc=126）。新增只讀 git ls-files -s 的判準：文件教裸跑者標的須 100755、100755 檔檔首須是 shebang 且無 BOM。LATEST 那支已改 bash 形態；凍結版 87 筆依 Copy-on-Evolve 登記為可見欠債。機械物 TestExecBitIsGovernedViaTheGitIndex
```

## DEF-101-918

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-5｜P3｜open-registered｜Windows 的 Git Bash 上 [ -x ] 是對檔首是不是 shebang 的內容猜測而非權限位元，親測加 BOM 由 EXECUTABLE 翻成 NOT-EXEC、且 chmod +x 之後仍 NOT-EXEC ⇒ post-commit dispatcher 那道守衛在 Windows 側是內容猜測，檔首多任何位元組就靜默 exit 0。已寫入 ONBOARDING 執行權限政策段並由上列判準②覆蓋一半；dispatcher 反向失效仍無判準，承接下輪
```

## DEF-101-919

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-6｜P3｜open-registered｜os.replace 覆寫被其他行程開著的目的檔在 Windows 拋 PermissionError WinError 5，POSIX 恆成功；既有知識只涵蓋 unlink 的 WinError 32（親測兩碼皆重現）。新增原語清冊與 live 樹站點普查（未處置 PermissionError／OSError 者精確 41 筆），並以不用 skip 的雙平台行為測試釘住可重量測性。凍結版 1131 筆已量到但刻意不進帳（禁改＋耗時 133 秒）。站點修復不在本包所有權內
```

## DEF-101-920

**來源包**：XPLAT｜新落差面 ＋ .ps1 行尾止血（掌舵者 Q1／Q3）

```text
R79-XPLAT-7｜P2｜fixed｜一支鎖因別包的合法動作而靜默失去鑑別力：test_ratchet_flags_both_directions_of_drift 用第一格基線減一施測「已補標未下修」那一向，而 D-skipped 包把 _POSIX_TAG_RATCHET 的 tools/tests 由 1 正確下修為 0 之後，扣完等於沒扣、該半題恆綠（當回合實測轉紅）。改為挑基線大於 0 的樹施測，並在全格為 0 時 fail-loud。判準不得依賴「哪一格排第一」這種偶然事實
```


## DEF-101-921

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-1 P2 同一份 .ps1 掃描面有 3 份獨立實作（Python SSOT ／ root-infra-ci.yml 第 2 道 ／ windows_smoke_local.ps1 [1/9]），為偵測三份不同步養了 866 行對抗式正則錨，而該錨 docstring 自承 3 種已實測抓不到的逃逸（GetFiles ／ Get-Item ／ Resolve-Path），軍備競賽已翻車兩次（R56 的 -Path 具名參數假設、R57 的大小寫敏感假設）。修法＝兩個非 Python 站點改呼叫 tools/_script_scan_surface.py --list SSOT，複本消失即結構上不可能不同步。刪 866 行（_ci_scan_anchors.py 154 ＋ test_ci_scan_anchors.py 712），殘餘鎖＝test_script_scan_surface_ssot.py::TestNonPythonSitesCallTheSsot 2 支。注入 4 形態（含舊錨抓不到的 GetFiles）全紅還原全綠；smoke rc=0、parity rc=0。狀態 fixed R79
```

## DEF-101-922

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-2 P3 check_wrapper_thinness 的並聯第三訊號 _FORBIDDEN 只有 14 鍵而 _PINNED_SHA256 有 16 鍵，兩支 LATEST run_tlc 薄殼靠 .get(rel, ()) 靜默回空集合＝零訊號，只剩 hash 一道，而更新 pin 正是它的合法維護動作（R60 Scan-E E-A-02 串聯失效原型的殘餘）。同檔 _CORE_TARGET 早有對等完整性鎖，_FORBIDDEN 沒有。修法＝補登記 JSON 與內嵌直譯器碼那一族（迴圈家族刻意排除，實測這兩支確實要迭代，照抄會假紅），並加 TestForbiddenKeywordsCoverEveryPin 鍵集合相等鎖（缺鍵與孤兒鍵雙向紅）＋非空自錨＋真跑鑑別力。注入 4 形態全紅，含真檔加 jq 後工具 rc=1。狀態 fixed R79
```

## DEF-101-923

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-3 P3 check_script_parity.py 用來支撐「這段不可刪」的事實宣稱失實：原文寫 macos 與 windows compat-CI 與兩支 smoke 只跑本檔，實測兩支 compat-CI 皆有 run_root_unittests step，而 test_check_wrapper_thinness.test_real_wrappers_pass_today 對真樹跑全部 16 鍵；smoke 那一半為真。下一輪依它做架構決定就是拿失實前提推理。修法＝就地訂正，補寫原文沒寫的真缺口（smoke 路徑只守 LATEST 2 鍵，其餘 14 支殼無 hash 守門），並新增 test_check_script_parity.py::TestLatestThinnessRationaleIsFactual 把 4 個世界事實機械釘住。注入 4 形態全紅。狀態 fixed R79
```

## DEF-101-924

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-4 P3 check_pytest_baseline_sites 是 8 檔人工白名單、無前瞻發現鎖：擋得住刪清單一行，擋不住在新文件裡多開一個家。實測掃描面外 1430 支 tracked .md 與 .py、4495 行命中同一判準，命中最多兩支是活文件 AutoClaude/docs/05_development/sprint_history.md 與 gate_audit.md。修法＝發現面改全庫 tracked 扣具名日期性文物樹（3 條附 WHY），未納管檔數 shrink-only 雙向棘輪＝114，加發現面下限 900 與活文件錨。端到端注入：新增 tracked 文件寫下基線數字 rc 由 0 轉 1，移除後回 0。劃界：發現面是 git ls-files，未進 index 的新檔掃不到。狀態 fixed R79
```

## DEF-101-925

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-5 P2 護欄層行數棘輪 TestGuardLayerRatchet 自述「淨增一行即紅」，但其 append-only 稽核列逐字記著 R77 由 54188 增為 57693（加 3505）、R78 增為 59936（加 2243），連兩輪向上重釘且閘門全程綠。精確結論：它對靜默成長有牙，對「重釘加補一列理由」零方向約束，補列門檻只是有寫、不含方向。另 AutoClaude/tools/check_loc_budget.py 的 ROOT_TOOLS_EXCLUDED_DIRS 明文排除 tests 且 iter_root_tools_files 直接 continue，故那 59936 行沒有第二個消費者。本輪以真減法往下壓 915 行（該射程內淨額），判準形狀未改。狀態 open，承接＝加跨輪累積淨額判準
```

## DEF-101-926

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-6 P3 兩支自身契約已宣告 monorepo 級的 hook 住在 AutoClaude 子專案樹：check_sh_eol.py 檔頭逐字處理非 LATEST 的 AISDLC_SDD 凍結版樹與根 gitattributes，check_ps1_encoding.py 逐字引用根 gitattributes 的 ps1 eol=crlf、editorconfig 與 CI 第 4 道 EOL 閘，兩者都在管跨子專案的事卻住 AutoClaude/tools/hooks/，只因根 settings.json 明文橋接才在根 session 生效。搬到根 .claude/hooks/ 會同時動到根與子專案兩份 settings.json 註冊面（該檔記載過 hook 誤觸 deny 會把工具硬鎖死的 P0）、根 CLAUDE.md 逐行判準、以及 AutoClaude 側測試路徑。本輪只做定位分析。狀態 open
```

## DEF-101-927

**來源包**：ARCH｜架構減法（掌舵者 Q2：架構簡潔、分工清楚、不重複模組）

```text
ARCH-7 P3 幽靈符號鎖的定義面 _SYMBOL_DEF_GLOBS 只含 tools 與 AutoClaude 兩棵樹，不含 .claude/hooks/，於是整個 hooks 層的符號在該鎖眼中都不存在。本輪實測：tools/tests/test_check_hooks_liveness.py 以反引號指名 _RC_RESET_RE 被判為幽靈，但該符號真的存在於 .claude/hooks/lint_powershell_command.py＝偽陽性。偽陽性會讓整道鎖被關掉，比縮面更糟（該鎖自己的 docstring 就這樣寫）。修法＝把 .claude/hooks/**/*.py 補進定義面。同批另有 tools/tests/test_maturity_criteria_r79.py 的 _R123 是示意字面、屬真幽靈，改寫即可。狀態 open，兩筆分屬別包
```


## DEF-101-928

**來源包**：CONV｜收斂包（R79 最後一個修復 agent）

```text
【建議新增，由有 ID 指派權的人寫入】兩支 compat-CI 的 `paths:` 未涵蓋新增判準所消費的根層檔（`.editorconfig`／成熟度 SSOT）——只改被讀的檔時讀它們的鎖不會被觸發。同形態自 R78 起第三次復發，唯一偵測者是 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`，而它**不在根層 unittest 閘門內**（要跑 SDD scripts 樹才會說話）⇒ 本輪是在回填 ONBOARDING 快照時才顯形的。處置：兩支 workflow push／PR 兩段各補兩條 path。
```

## DEF-101-929

**來源包**：CONV｜收斂包（R79 最後一個修復 agent）

```text
【建議新增】目錄項原語普查（`TestDirEntryPrimitivesAreAccountedFor`）的掃描面是檔案系統 rglob，排除清單只列 `.venv`／`venv` 兩個名字 ⇒ 該普查的雙向精確比對基準是「這台機器上剛好有哪幾個 venv」的函數。實測：建一個叫 `cleanvenv` 的環境（gitignored、政策上就是該建的）使實測值由 41 跳到 58、閘門轉紅。處置：改以 PEP 405 的 `pyvenv.cfg` 標記偵測 venv 根，與命名無關。狀態 fixed@R79。
```

---

## DEF-101-888

R79 收尾當回合逐項實查（讀檔，不經 shell），用以支撐本列由 `open@R79` 訂正為 `fixed@R79`：

1. **寫入者已溯源**：XPLAT 包交件回報逐字記載寫入者為 Claude Code 的 Write 工具（新建與覆寫既有 CRLF 檔都吐 LF），對應主檔新列 `DEF-101-915`。
2. **補守門（解鎖條件前半）**：`AutoClaude/tools/hooks/check_ps1_encoding.py` 檔頭已載 R79 行尾擴充段，函式體內以三步收斂成 CRLF（先把 CRLF 與單獨 CR 全收成 LF，再一次展開成 CRLF，故混合行尾亦收斂），並在動作清單追加「行尾正規化為 CRLF」。
3. **本機自檢（解鎖條件後半）**：`tools/tests/test_platform_neutral_paths.py` 內 `TestWorktreeEolMatchesPolicy` 讀 `git ls-files --eol` 的 **w 欄**（工作樹行尾），對 `.ps1` 要求 CRLF、對 `.sh` 要求 LF，雙向對稱。該檔同段註解逐字寫明「blob 判準對 `.ps1` 結構上恆綠」，正是本列原文指出的那個盲區。

誠實劃界：本節取證是**讀樹確認機械物存在且主題正確**，不含當回合對這兩支機械物的紅綠注入（注入紅綠由 XPLAT 包在其交件回報內提供，見 `DEF-101-915`／`DEF-101-916` 兩節）。本列原文所附的另一件事（C 包登記的 32 筆 grandfathered 幽靈符號名）不是本列的解鎖條件，其後續由收斂包的幽靈符號天花板承接。

---

## R79 收尾：未結列回收（逐筆實查後由 open 改 fixed）

> **回收判準（三項缺一不可，與「把數字弄好看」明確切開）**：① 該列**自書**的解鎖條件逐項對照；
> ② 滿足它的落地物必須在**當回合實查**得到（讀樹／跑測試），不採信任何交件回報的宣稱；
> ③ 原狀態欄全文逐字保全於本檔，主檔只留索引。
> 🔴 **本輪明文拒絕的兩條捷徑**：不合併列（合併＝用「少記一筆發現」換數字）、
> 不調高 warn/fail 線。回收的三列全部是 `DEF-101-810` 那個形態——
> **續改派只驗「上一輪做了沒」、不驗「有沒有別人順手做掉」**，於是已經被別人修好的事一直掛在未結。

## DEF-101-680

**帳本原狀態欄全文（逐字保全，一字未改）**：

> open：ADR 側已把 §9.1 改寫為可逐字照抄的規格三件套（SC-1~SC-7）、末段以最重措辭揭露缺口、§8 item 14 完成判準改為「接上機械消費者」；但**鎖本身至 round 2 收尾仍未落地**（不在 ADRDOC 與 EVIDENCE 任一包的授權面）。本列只把它從「無主」變成「具名待指派」，承接輪次＝未指派

**缺陷本體**：R67 round 2 複審實測 `grep -rlnE 'SC-[1-7]' --include='*.py' …` **rc=1、零輸出**
⇒ 三項頭號架構異動的唯一防回流機制 SC-1~SC-4 全 repo **零可執行消費者**，
依 Scan-H 判準⑤「可重跑但沒有閘門看 rc ＝ 不可重跑」，它們不是活體守門。

**當回合實查（讀樹，不經 shell）**：

| 本列自書的要求 | 實查結果 |
|---|---|
| 具名承接容器＝`tools/tests/test_adr_xplat001_c1c2_lock.py` | ✅ 該檔存在，`SC-[1-7]` 在檔內 **114 處**命中 |
| SC 條目要成為**可執行**判準 | ✅ `_SECTION_91_CHECKS` 是 `Check(sc, spec, fn)` 十元組：`SC-1`~`SC-10` **全部**掛上實作函式（`sc1_no_unquoted_include_glob`…`sc10_coverage_table_has_a_row_for_the_current_round`） |
| 要有**閘門在看 rc** | ✅ `tools/run_root_unittests.py:53` 的 `_TESTS_DIR = tools/tests`，`discover_suite()` 對該目錄 discover ⇒ 本檔隨根層 unittest 全套執行 |
| 注入違規形態要能轉紅 | ✅ 逐條備有**單點注入**樣本（`_SC1_INJECT`…`_SC7_INJECT_CODE`），且 `_sc6_inject()` 刻意以**現查條數合成**而非寫死，避免樣本凍在歷史值上；另有「同一段字放進交棒表本體必須全紅、放進 §8.3 必須全綠」的位置對照組 |

**修前／修後的可辨識差異（本列的原始量測面）**：原文的 `grep SC-[1-7] --include=*.py` 由
**零命中** 變成 **3 支檔命中**（`test_adr_xplat001_c1c2_lock.py`／`test_doc_loc_baseline_freshness_r60.py`／
`test_platform_neutral_paths.py`）⇒ 本列「零可執行消費者」這個事實宣稱已失實。

**誠實劃界**：本節取證是「讀樹確認判準存在、掛得上、且有閘門會跑」，
**不含**當回合對十條 SC 逐條做紅綠注入——那是該檔自帶的測試在每次全套執行時做的事。
另：SC 條數今天是 10 條而非原文寫的 7 條（`SC-8`／`SC-9`／`SC-10` 為後續輪追加），
本列的解鎖條件是「鎖要落地」而不是「恰好七條」，故不因條數增加而改判。

## DEF-101-714

**帳本原狀態欄全文（逐字保全，一字未改）**：

> open watch（登帳，非修復）。憑證＝`count_loc` 雙側量測（指令見 `ADR-XPLAT-002` §4.3.1 R69 段）。解鎖條件＝護欄成長取得**機械訊號**（例：「護欄／生產碼比例」納入 `check_loc_budget` warn band）。承接輪次：**未指派**

**缺陷本體**：R69 量到該輪 root `tools/` +1795、`AutoClaude/tests` +333、`AutoClaude/tools` +19、
`AISDLC_SDD/scripts` +167 而**生產碼 Δ=0** ⇒ 成長 100% 落在護欄層，
而「護欄層長多大」這件事當時**沒有任何機械訊號**——本列刻意不把成長率常數登進 ADR
（否則即 `DEF-101-713` 家族復發），只登量測指令，並把「取得機械訊號」訂為解鎖條件。

**當回合實查（讀樹）**：解鎖條件所要的機械訊號**已經存在**，落點在
`tools/tests/test_adr_xplat001_c1c2_lock.py`：

| 落地物 | 內容 |
|---|---|
| `_FROZEN_GUARD_LINES` | 護欄層**逐檔行數**凍結基準表（`_GUARD_LINE_PATTERN = "*.py"`，與 ADR §4.3 GLC 現查指令走同一個 glob） |
| `glc_growth_problem()` ／ `guard_line_problems()` | 護欄層行數第一次有判準在讀；**成長側零容忍** |
| `TestGuardLayerRatchet` | 消費上述判準的測試類別，隨根層 unittest 全套執行 |
| `_GUARD_LINE_STALE_SLACK = 0.02` | **雙邊帶**：縮小後不重釘也會紅（單邊棘輪只會腐化，餘裕就是日後無聲加回去的破口） |
| `_GUARD_LINES_REPIN_LOG` | 重釘必須補一列稽核痕跡，**不補即紅** ⇒ 淨額在結構上不可能缺席 |

該檔逐字寫明方向：「改版前『一輪加三萬行全綠』，改版後**淨增一行即紅**」——
比本列原文舉例的「納入 `check_loc_budget` warn band」**更緊**（硬紅 vs 只印不擋），
故以「更強的等價物已落地」判定解鎖條件成立。

**🔴 為何殘留缺口不阻擋本列結案（不是把問題掃掉）**：該棘輪確有一項已知弱點——
`DEF-101-925` 實測它「對靜默成長有牙，對**重釘加補一列理由**零方向約束」
（R77 +3505 行、R78 +2243 行，兩輪向上重釘而閘門全程綠）。
但那是**另一個缺陷**，且**已經有自己的未結列在承接**（`DEF-101-925`，`open`，承接 R80）。
本列問的是「護欄成長有沒有機械訊號」，答案是**有**；
問「那個訊號擋不擋得住有理由的向上重釘」的是 925。
兩列各自成立，關掉本列**不會讓任何一筆發現消失**——這是本輪拒絕合併列的同一條紀律的另一面。

## R79 帳本瘦身：三列存量長列的原文保全

> 主檔在本輪要進帳 34 列，而動工當下距 256KB 硬閘只剩約 10.9KB。依 `DEF-101-890` 訂立的「帳本列是索引不是報告」政策，下列三列（皆**已結案**、皆屬 `OVERSIZE_ROW_GRANDFATHERED` 存量）的欄內長文逐字搬到此處，主檔只留索引。**判定、狀態分類、嚴重度一個字沒改**，搬的只有敘述。

## DEF-101-263

瘦身前主檔原列逐字（9333 bytes）：

```text
| DEF-101-263 | 2026-07-22 | R23 四方一審/二審（QA 一審記錄 4 項＋SD 二審記錄 2 項，共 6 項非阻斷發現，本輪補記存證避免審查產出隨裁決收斂憑空消失） | **六項非阻斷 backlog，逐項記錄供下輪追蹤**：①`tools/check_ntfs_paths.py:88`（DEF-101-260 修復後）——tracked 路徑若真含非法 UTF-8，違規清單印出的檔名會混入 U+FFFD 替代字元亂碼，人類辨識度打折，建議在該檔既有「已知侷限」段落補充說明（QA 一審）；②`tools/dev_start.py::_windows_heartbeat_fail_note()`（DEF-101-200 rider ARCH-R15-1）——偵測邏輯靠字面正則對齊 `AutoClaude/tools/run_local_nightly.ps1:978,980` 的 `Log(...)` 字面量，兩邊無跨檔一致性機械鎖，任一方未來改版摘要行格式會讓哨兵靜默永久回 `None`（QA 一審）；③`.github/workflows/windows-compat-ci.yml`／`macos-compat-ci.yml`（DEF-101-200 rider SCAN-C-11 修復後）——job 層 concurrency 的 `group:`/`cancel-in-progress:` 字面值目前無機械回歸鎖（`test_workflow_permission_concurrency_lock.py` 只鎖 `aisdlc-sdd-arch-fitness.yml`/`autoclaude-ci.yml`），macos 側此缺口早於 R13 即存在、非本輪新增（QA 一審）；④dot-source 陷阱防護（DEF-101-261）——`pwsh -Command ". ./realscript.ps1"`（`-Command` 包裝一支真正生產腳本檔的 dot-source）呼叫寫法下，`(Get-PSCallStack)[-1].ScriptName` 仍判為互動情境（誤判 False），若此類 CI/自動化呼叫寫法未來被採用會退回「失敗時 return 而非 exit」；全庫 grep 目前零命中，純理論性（QA 一審）；⑤`tools/dev_start.py::_WINDOWS_EXIT_DECISION_RE`（DEF-101-261 追加修復，R23 一審後把正則改寬容後）——新正則 `end\s+exit\s+decision:\s*exit=(\d+)...`（`re.IGNORECASE`）的 `end` 前無 `\b` 單字邊界，任何以 end 結尾單字（append/recommend/weekend/backend…）緊接 `exit decision: exit=N` 皆會誤觸發，假陽性面比修復前（僅比對大寫字面 `END`）顯著擴大；風險評估為低（人工撰寫的專屬收尾語，真實雜訊輸出中巧合出現機率極低），是既有設計弱點被放大而非新類別風險，只影響 advisory 警告文字（SD 二審 bug-injection 實測）；⑥`tools/lib/GitHooksInstallCommon.ps1` 模組頂層分支的 `[Environment]::Exit(1)`（DEF-101-261 追加修復）——經 SD 二審探針腳本證實會跳過外層 `try/finally`（.NET Environment.Exit 語意即立即終止行程、不做受控堆疊展開），`throw` 可在同樣正確終止＋正確 exit code 前提下不犧牲 `finally` 語意，理論上更穩健；已查證兩支生產呼叫端（`AutoClaude/tools/install_git_hooks.ps1`、`AISDLC_SDD/scripts/install-hooks.ps1`）dot-source 位置在任何 `try`/資源配置之前，此分支在現有呼叫路徑下無 `finally` 可跳過，唯一有 `try/finally` 包住巢狀呼叫處（`tools/windows_smoke_local.ps1` 的 `Test-InstallRoundtrip`）在 python 缺失情境下會更早失敗、不可能活著跑到此分支，現況無害（SD 二審探針驗證） | P3/P4（六項皆 advisory 或需額外測試基礎建設，不影響本輪功能正確性；四方二審 Architect/SA/SD/QA 對本輪修復本身皆已 APPROVE，此六項純屬「記錄以供下輪追蹤」而非本輪必修） | 排入下一輪跨平台複審視情況處理（①③可能為文件/測試補強、②⑤可考慮加 `\b` 邊界或跨檔字面鎖測試、④⑥為觀察性記事非必修） | fixed@R27｜🔴 R75 訂正首詞（原文逐字接於後）：open watch（六項發現分別於 R23 四方一審 QA〔①②③④〕與二審 SD〔⑤⑥〕實測記錄，皆非阻斷、不影響本輪四方 APPROVE 結論；本列存在目的是避免審查產出隨裁決收斂而遺失，供下一輪 Windows/跨平台複審排查）。**R25 全面掃描逐項覆核並收斂 4/6 項（不再無謂延後）**：**①fixed@R25**——`tools/check_ntfs_paths.py` 已知侷限段補一句說明 U+FFFD 替代字元僅影響訊息可讀性、不影響偵測本身。**②fixed@R25**——`tools/tests/test_dev_start.py::TestWindowsHeartbeatFailSentinel::test_ps1_literal_end_exit_decision_lines_present_and_matched` 新增跨檔字面鎖（鏡子自證模式，先斷言 `.ps1` 字面量存在再驗證正則命中）。**③fixed@R25**——`tools/tests/test_workflow_permission_concurrency_lock.py` 新增 `TestCompatCiConcurrencyLock`（6 tests，windows/macos compat CI 各 3 個 job 層 concurrency 區塊皆納管；經手動 bug-injection〔修復後暫時改壞字面值重跑再還原〕確認皆有真實鑑別力，測試檔本身未內建自動化負向案例——四方一審 SA 指出原措辭易誤讀為「檔內含自動化 bug-injection 案例」，此處訂正用詞）。**⑤fixed@R25**——`_WINDOWS_EXIT_DECISION_RE` 加 `\b` 單字邊界（`tools/dev_start.py`），新增 `test_word_boundary_prevents_false_positive_on_end_suffixed_word` 回歸鎖；四方一審 SA 指出 `\b` 對「連字號結尾單字」（`high-end`/`front-end`，連字號非單字字元）仍會誤判，四方二審 SA 進一步指出此修法成本低（改用負向後顧 `(?<![\w-])` 即可一併關閉，不影響既有兩處真實命中）、依「不要無謂延後」紀律應當場補——**已於二審後追加修復**：`_WINDOWS_EXIT_DECISION_RE` 由 `\b` 改為 `(?<![\w-])`，新增 `test_hyphenated_end_word_prevents_false_positive` 回歸鎖，bug-injection（還原為 `\b`）確認新測試會變紅。**過程記事（誠實揭露）**：本次 bug-injection 驗證後誤用 `git checkout -- tools/dev_start.py` 還原，把該檔尚未 commit 的 R25 全部修改（含 `\b`／負向後顧兩版修復與所有註解）一併抹回 R24 committed 狀態（[[git-checkout-mutation-revert-hazard]] 已記錄過的已知陷阱再次發生）；已用 Edit 逐段重建修復內容並重跑全套（根層 unittest 359 tests OK, skipped=10）確認與意圖一致，無殘留遺漏。**④維持 backlog（R25 Scan-A 複核，非無謂延後）**：修法需新設計判斷（如改看 `CommandOrigin`/呼叫棧深度）並驗證無新假陽性/假陰性，屬需要人工決策的變更，全庫仍零實例、純理論性，維持觀察。**⑥reclassify（R25 Scan-A 複核，非未修缺陷）**：親讀兩支生產呼叫端（`AutoClaude/tools/install_git_hooks.ps1:27`、`AISDLC_SDD/scripts/install-hooks.ps1:13`）確認 dot-source 位置前皆無 `try` 包裹，現況已查證無害，非「backlog 待修」，狀態訂正為「已查證無害、觀察性記事」，不再列為待修項目。**四方一審訂正**：Architect 指出 `test_ps1_literal_end_exit_decision_lines_present_and_matched` 讀 `run_local_nightly.ps1` 原用 `encoding="utf-8"`，與同檔既有讀取同檔的 `test_windows_reader_filename_matches_ps1_writer` 慣例（`utf-8-sig`，因該檔含 BOM）不一致，已訂正為 `utf-8-sig`（Rule 11 比照既有慣例；功能上無影響，純風格一致性）。**四方一審 SA/SD/QA 三方各自獨立回報 `run_root_unittests.py`/`test_dev_start.py` 偶發假紅（`_WINDOWS_EXIT_DECISION_RE` 誤判「backend」）**：主控親自調查——反組譯確認 `tools/__pycache__/dev_start.cpython-311.pyc` 已正確內含 `\b` 修復字面量、靜態驗證 `\bend` 對 "backend" 不匹配、連續 52 次獨立 concurrent repro（cold-cache + warm-cache 混合，最高 8-way 並行 × 多輪）皆 0 失敗，排除 pyc 寫入競態與正則邏輯本身的持續性缺陷。**根因判定**：本輪一審四位審查員（Architect/SA/SD/QA）以單一訊息並行派出，SD／QA 在審查過程中各自對 `tools/dev_start.py`／`windows-compat-ci.yml` 做暫時性 bug-injection（改壞後驗證再還原），與同時段其他審查員的全套回歸執行產生時間窗重疊——符合既有已知模式 [[parallel-mutation-audit-collision]]（並行對同一主樹做突變會與其他並行讀取者互踩，產生「像 flaky 但其實是真實暫時狀態」的假紅），而非 `\b` 修復本身或新測試邏輯的缺陷。**方法論記事**：四方審查若涉及 bug-injection 需暫時改動共用主樹檔案，日後應序列化執行或改用 worktree 隔離，避免審查階段本身重演此已知陷阱。**R27 訂正④（見 DEF-101-272）**：原判定「全庫零命中、純理論性」被本輪主控手動重跑 `windows_smoke_local.ps1`（非 `-File` 頂層呼叫方式）實測推翻——`& $installer` 同行程巢狀呼叫一樣會觸發同款誤判，不需要真的用 `pwsh -Command ". ./realscript.ps1"` 逐字寫法；已修復並補回歸測試，狀態由 open watch 改為 fixed@R27，詳見 DEF-101-272。｜🔴 **R75 複驗（類別 A）**：六項現查全收斂：① `check_ntfs_paths.py:64` 侷限句在；② `test_ps1_literal_end_exit_decision_lines_present_and_matched` 在；③ `test_workflow_permission_concurrency_lock.py:190 TestCompatCiConcurrencyLock` 在；⑤ `dev_start.py:1659` 已是收斂後的負向後顧形態、兩支回歸鎖（:3223／:3245）在；④ 本欄自載「改為 fixed@R27」（載體 DEF-101-272）；⑥ 已查證無害。首詞是唯一沒跟的。`pytest ...::TestWindowsHeartbeatFailSentinel` → **10 passed，rc=0**。 |
```

## DEF-101-358

瘦身前主檔原列逐字（4857 bytes）：

```text
| DEF-101-358 | 2026-07-25 | DEF-101-357 例外回補時同步核實的殘留落差（FrozenPatch 五批次一致觀察），R44 QA 一審獨立複驗確認記載屬實（未見對方原始比對細節、獨立重新逐版比對源碼） | **v0.01～v0.29 的 `_sanitize_component()` 本身仍是較弱版本**：只把 `/` 與 `\` 剝除／替換為 `_`，未比照 v0.30 做 Windows 保留裝置名（CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]）、控制字元、長度上限等強化。DEF-101-357 的例外修復只是「接上既有的（較弱）淨化函式」，足以阻斷本輪驗證的 `../` 相對路徑逃逸攻擊面，但不具備 v0.30 現有的完整防護縱深。與過去同類「凍結版某處較弱／不完整防護」判例（DEF-101-019／020／040 等皆判 P3 wontfix）性質不同的關鍵點：**這裡的較弱淨化函式現在是真的在擋一個已證實可利用的路徑穿越攻擊面，而非單純內部狀態路徑衛生**，過去慣用的 P3 判斷基準可能不再適用，需重新評估 | P3（暫沿用既有凍結版慣例分級，但本列明文記載需重新評估，非直接沿用不查） | 下一輪視情況評估是否需要 backport v0.30 強化版（Windows 保留裝置名／控制字元／長度上限）至 v0.01～v0.29，或維持現狀；本項不在本輪使用者核准的例外範圍內，僅記事存證＋標記需重新評估優先度 | fixed@R45｜🔴 R75 訂正首詞（原文逐字接於後）：open（watch）｜🔴 R60 round 2 補《格式定義》合法首詞（原首詞非合法值，原文完整接於後）：**RESOLVED@R45（與下方 open 段落內文中的「fixed@R45」小節為同一事件，非另一次判定）** open（watch；緩解＝現行較弱版已能擋下本輪驗證之路徑穿越／任意檔案讀取攻擊面，僅缺 Windows 保留裝置名等進階防護縱深；優先度重新評估留待下一輪）；QA 一審獨立複驗：直接讀取 v0.01 `tools/fsm_runtime/state_loader.py::_sanitize_component()` 原始碼確認僅 `str(name).replace("/", "_").replace("\\", "_").strip()` 一行，並讀取 v0.30 同名函式確認確有 `_WIN_FORBIDDEN_CHARS`／`_WIN_RESERVED_NAME_RE`／`_MAX_COMPONENT_LEN` 三項強化且 v0.01 完全缺席；另抽樣核對 v0.02～v0.18／v0.25／v0.29 共 20 版 `_sanitize_component()` 之 `return` 陳述式，逐版與 v0.01 逐字相同，證實本列所稱「v0.01～v0.29」涵蓋範圍無誇大。判定本列描述準確、無需修正，亦非新缺陷，未追加修復或另立 DEF 條目，僅在本欄與標題欄註記獨立複驗以維持誠實記載。**fixed@R45**（架構最佳化，經使用者本輪明確核准「抽共享層」方案）：`_sanitize_component()` 由 30 個版本（v0.01～v0.29 + LATEST v0.30）各自一份複本，改為全數委派新建的 `AISDLC_SDD/scripts/component_sanitizer.py`（跨版本共用 SSOT，比照既有 `copy_on_evolve.sh`／`sdd_version.py` 等「共享 CI infra，免 Copy-on-Evolve」先例 EVOLUTION_LOG.md::DEF-15-001；各版 `state_loader.py` 用 `importlib.util.spec_from_file_location` 依絕對路徑載入，不污染 sys.path）。30 個版本的 `_sanitize_component` 行為即刻統一為 v0.30 強化版（Windows 保留裝置名／禁用字元／控制字元／長度上限全數涵蓋），一次性觸碰 29 個凍結版本（屬使用者本輪核准的例外範圍延伸，非新的例外決策）。新增 `tools/tests/test_component_sanitizer_shared_layer_lock.py`（behavioral 驗證 30 版皆委派同一份共用原始碼實作（同一支 `component_sanitizer.py` 檔案；因刻意不寫入 `sys.modules` 以避免跨版本快取汙染，每版各自 `exec_module()` 一次，故實際上是 30 個各自獨立的函式物件執行同一份程式碼，而非跨版本共用同一顆記憶體物件）且擋下已知危險輸入，subprocess 隔離避免同名模組跨版本快取汙染誤判）；既有 R44 回歸鎖 `test_sanitize_component_frozen_sdd_versions_lock.py`（6 case）與 v0.30 `test_state_component_sanitizer_parity.py`/`test_sanitize_component_call_site_lock.py` 皆重跑確認零回歸。驗證：AISDLC_SDD_v0.30 1721 passed／ci-gate.sh 全綠（含 v0.01 凍結基線 1478 passed）／AutoClaude 3668 passed／根層 tools/tests 467 passed（1 個既有已知失敗 DEF-101-351，非本輪回歸）。往後同類淨化強化只需改共用模組一處，不必再逐版走「打破凍結基線例外」流程｜🔴 **R75 複驗（類別 A）**：本欄自載 `RESOLVED@R45`／`fixed@R45`（30 版 `_sanitize_component()` 全數委派共用層、行為統一為 v0.30 強化版＝現象欄抱怨的「v0.01～v0.29 仍較弱」已不成立），首詞未同步。現查 `AISDLC_SDD/scripts/component_sanitizer.py` 在；`pytest tools/tests/test_component_sanitizer_shared_layer_lock.py` → **rc=0**。 |
```

## R79 複審後修復包（CONV 收斂）：四筆逐筆實測

> 本節四筆全部是「四方複審 → 收斂包在單人窗口落地」的產物。每一筆的注入都用 **bytes 級備份**
> 還原並比對 sha256，全程未用 `git checkout --`。

## DEF-101-930

**缺陷**：`tools/session_resume_planner.py` 的五個內插點把外部字串直接塞進 PowerShell 單引號字串。
`O'Brien` 這種**合法**使用者名就足以讓整段註冊腳本語法錯，而失效發生在 `powershell.exe` 那一端，
呼叫端只看得到一個 rc。

**修法**：`_ps_single_quote(s) = s.replace("'", "''")`，五處各套一次。`at_expr` 刻意不跳脫——
它按設計就是一段 PowerShell 運算式（預設 `(Get-Date).AddHours(5)`），跳脫會讓它失效；來源是 `--at`
或本檔自己 `strftime` 產的字面時間，不是路徑那種外部字串。**這個例外就地劃界在原始碼註解裡。**

**回歸鎖**：併進既有 `tools/tests/test_context_budget_guard.py::EnduranceWiringTest`（**未新增鎖檔**，
`_FROZEN_GUARD_FILE_COUNT` 那條禁令未觸發）。判準刻意**看產出不看呼叫**（「有沒有呼叫某個函式」那種鎖
改個名字就瞎）：以 `_outside_single_quoted()` 剝掉所有單引號字串，斷言 ①全部閉合 ②路徑／payload 的
任何一段都不得落在字串之外。🔴 **兩維必須分兩題**——放同一份腳本時路徑那個撇號會開一個永不閉合的
字串把 payload 整段吞掉，注入那一維會量到 0（前一包第一版實測 A_TOKENS 由 70 崩到 22）。

**注入（收輪當回合實跑）**：把 `_ps_single_quote` 改成恆等 ⇒

```text
BACKUP_SHA256=a8b670f50b06ed9040f522e115331c9bd79ca7201c832e6b32b5fb30606db61c  bytes=54305
健康版   Ran 10 tests / OK          HEALTHY_LOCK_RC=0
注入版   FAILED (failures=4)        INJECTED_LOCK_RC=1
  · test_a_task_name_cannot_escape_the_string_and_become_a_command
  · test_an_apostrophe_in_the_plan_path_stays_inside_the_string
  · test_the_escaper_doubles_every_apostrophe
  · test_the_evidence_template_escapes_its_task_name_too
RESTORED_SHA256=a8b670f5…（同上）  MATCH=True
```

**掃描器 vs 真 tokenizer 兩地對照**：`_outside_single_quoted()` 是自寫的（刻意不外呼 `powershell.exe`
——根層 unittest 在 mac／Linux 也要跑，多一支平台 skip 就是多一個沒人在跑的判準）。它與**真** tokenizer
的一致性以 `powershell.exe -NoProfile`（**PS 5.1**，＝生產引擎）的 `[Parser]::ParseFile` 證過：

```text
gen_healthy_path.ps1   parse_errors=0  WriteOutput_tokens=0
gen_healthy_task.ps1   parse_errors=0  WriteOutput_tokens=0
gen_injected_path.ps1  parse_errors=4  WriteOutput_tokens=0
gen_injected_task.ps1  parse_errors=7  WriteOutput_tokens=3   ← payload 成為 3 個獨立 token
```

**誠實劃界**：射程只有**單引號**。雙引號不必處理（Windows 檔名不允許 `"`，且五個內插點都落在單引號
字串裡）；掃描器對 PowerShell 的其餘文法（雙引號內插、here-string、註解）**沒有**判準——它只證明
「單引號字串沒有被提前終止」，不證明整段腳本語意正確。

## DEF-101-931

**缺陷**：交棒書 §4 叫 R80 去補 34 列缺陷帳本列，而那 34 列（`DEF-101-896`〜`929`）在寫下該指示時
已經全部在磁碟上。照做＝再寫一次約 19KB，主檔當時餘裕約 6.5KB ⇒ 超線約 12KB，並產生 34 筆重複 ID
（撞帳本自己「同一 ID 在同一份檔內不得出現兩列」那道判準）。

**成因**：交棒書由**收斂包時點**寫成，其後 ledger 與 build 兩包才落地，沒有人回填。同一個根因也造成
§2-Q5 把 ledger 包自陳的「收尾 88／超出任務書 ≤86 兩筆、**未達標**」寫成了「未結列由 86 降到 83」的
**進展**——誤差方向是**把餘裕講得比實況寬**（讀者以為距 warn 線還有 3 筆，實際只剩 1 筆）。

**修法**：§4.1 改寫成「已在磁碟上、不要再補寫，只需覆核並先換回體積餘裕」；§2-Q5 改成純指針＋誠實結論
（本檔不再記那個數字，現值一律跑 `--unresolved-count`）；§0 加一段**成書時點聲明**，明說 §1〜§3 是
收斂包那一刻的快照、其後另有兩包改樹，凡數字一律現查。

**一般化**：多包並行的一輪裡，**交棒書必須是最後一個被寫的東西**，否則它記的是某一包的窗口而不是收輪值。
本輪的處置是加時點聲明＋把可現查的都換成指令；真正的修法是把交棒書的產出時機排在所有包停工之後。

## DEF-101-932

**缺陷**：`.ps1` 掃描面三份收一份（866 行對抗式正則錨退場）的正當理由是「掃描面靜默縮小必須 rc=1、
複本不同步結構上不可能發生」。旗標遺失同時打掉這兩半——新鎖的必要字串只有
`("_script_scan_surface.py", "--list", "--check-floors")`，`--with-latest` 不在內；而 LATEST 樹是
Copy-on-Evolve 每升一版就換路徑的那一棵，恰恰是最容易被人順手拿掉旗標的一格。

**修法兩側**：①測試側把 `--with-latest` 補進必要字串（LOCK 包）；②CLI 側 `_main` 對
「`--check-floors` 且未給 `--with-latest`」直接 **rc=2 拒跑**（收斂包）。用 rc=2（用法錯誤）而非
rc=1（掃描面異常），讓兩種紅在呼叫端可分辨。「要檢查下限卻不含 LATEST」在本 repo 沒有任何合法用途
——現查三個消費站點（`root-infra-ci.yml`、`tools/git-hooks/pre-push`、`tools/windows_smoke_local.ps1`）
全部同時帶兩個旗標。

**實測（收輪當回合，rc 不接管線）**：

```text
--list --suffix .ps1 --with-latest --check-floors   WITH_LATEST_RC=0    stdout 25 行
--list --suffix .ps1 --check-floors                 WITHOUT_LATEST_RC=2 並印出理由
--list --suffix .ps1                                NO_FLOORS_RC=0      ← 射程未擴大
```

**誠實劃界**：這道 CLI 守衛擋的是「要檢查下限卻漏 LATEST」。它**擋不到**「連 `--check-floors` 都不寫」
——那一向由測試側的必要字串鎖守（兩側缺一不可，這正是本筆要兩側都改的理由）。

## DEF-101-933

**缺陷**：守交棒書的 `TestR78HandoffClaimsCarryLiveCommands`，其 `_handoff_claim_blocks()` 在**任何**
`##` 以上的標題都重設 `in_section`——包括 `###`。後果：一個住在受管大節底下、但小標題本身不含觸發字的
`###` 區塊，**整區條目靜默退出射程**。前一包發現它的方式是注入時當場量到（加了四個小標題之後，拿掉某一項
的現查指令，鎖照樣印綠），處置是「把觸發字寫進每一個小標題」＝**繞過不是修好**：下一個人在該節底下新增
一個不含該字的小標題就會再踩一次，而且沒有任何東西會轉紅。

**修法**：巢狀標題**繼承**父節的 `in_section`，只有**同級或更高級**（`#` 數不多於開啟該節的那一個）
的標題才重設。⇒ 觸發字只需寫在大節標題上一次。

**掃描器自檢補三向**（避免修過頭）：①受管大節底下的 `###` 小標題不含觸發字時，父節條目**仍在射程內**；
②射程外大節底下的 `###` **不得**被吸進來；③同級標題**仍必須**關掉射程（否則一路吃到檔尾）。

**注入（收輪當回合實跑）**：bytes 級把該段還原成舊行為 ⇒

```text
BACKUP_SHA256=ddfbf90f44b58cd9badc21c0ae4c3713a618730aa0367c6612061f9cceef730b  bytes=351536
現行實作  Ran 1 test / OK                                  HEALTHY_RC=0
注入版    FAILED (failures=1)                              INJECTED_RC=1
          AssertionError: 0 != 1 : 「待辦」大節底下的 `###` 小標題把整區條目踢出射程了
RESTORED_SHA256=ddfbf90f…（同上）  MATCH=True
```

**殘留**：`_HANDOFF_SECTION_WORDS` 仍是寫死的觸發字清單——改掉大節標題的用字仍會讓整節退出射程，
這一向今天**沒有**判準在守（同「分母必須是量測值」那條一般化規則，本筆只修了巢狀那一半）。

## DEF-101-628

瘦身前主檔原列逐字（4711 bytes）：

```text
| DEF-101-628 | 2026-07-31 | R66 修復 `DEF-101-627` 時依任務指示雙載具（Bash＋PowerShell）覆跑驗證，副作用發現 | **`tools/tests/test_bash_probe_spec_contract.py::_probe_a_real_usable_bash_for_fixture()`（R64 為修 `DEF-101-617` 新增）挑選 `_BASH` fixture 時，驗活探測不帶任何 `env=` 覆寫、直接沿用呼叫端（pytest 行程）當下繼承的環境變數**——若該環境的 PATH 本身不含 `Git\usr\bin`（原生 `powershell.exe` 常見；本機系統 PATH 只含 `Git\cmd`，不含 `Git\usr\bin`），則候選清單第一個成員 `Git\usr\bin\bash.exe`（**不會**自我注入 PATH 的「誠實」版本）連探測階段的『能否正常執行 `PROBE_CMD`』都失敗（`dirname: command not found`），於是探測邏輯落到候選清單第二個成員 `Git\bin\bash.exe`（`DEF-101-618(a)` 已記載的「啟動器自我注入內部 PATH」版本）並誤選為 `_BASH`；而 `TestProbeCmdRealSubprocessBehavior::test_fails_when_path_lacks_dirname`／`TestUsableBashEndToEndWithRestrictedPath::test_usable_bash_rejects_candidate_when_path_lacks_dirname` 兩支測試正是要驗證「PATH 缺 dirname 時 `_BASH` 應該失敗」，用在一個「本身就會自我注入 PATH、無視限縮」的候選上必然恆為 rc=0，斷言確定性落空。**現查根因對照**（同一台機器，兩個 shell 分別啟動 `python`，皆不傳 `env=` 覆寫、僅探測 `PROBE_CMD`）：Bash 工具（Git Bash 子行程）下 `Git\usr\bin\bash.exe` 驗活 rc=0（因為 Git Bash 自身繼承環境的 PATH 已含 `/usr/bin`），`_BASH` 正確解析為 `Git\usr\bin\bash.exe`；PowerShell 工具（原生 `powershell.exe` 子行程）下同一支 `Git\usr\bin\bash.exe` 驗活 rc=127（`bash: line 1: dirname: command not found`，因為原生 PowerShell 的系統 PATH 不含 `Git\usr\bin`），落到 `Git\bin\bash.exe` 驗活 rc=0 而誤選。此為 `DEF-101-617`／`DEF-101-618(a)`「`_BASH` fixture 選錯候選」家族的第三個變種（前兩者分別是「PATH 上 `bash` 解析到 WSL 佔位版」與「`Git\bin\bash.exe` 啟動器本身自我注入 PATH 使限縮手法失效」；本次是「探測階段本身未固定/隔離環境，隨呼叫端繼承環境漂移選中兩者中的『自我注入』那個」），三者根因不同但表徵同構——皆是「候選驗活條件不足以保證挑到『不自我注入 PATH』的那個」 | P2（測試鑑別力隨執行環境的 PATH 組成而不確定性翻轉，非本輪 `DEF-101-627` 修復引入；在原生 PowerShell 且系統 PATH 未含 `Git\usr\bin` 的機器上會讓 `python tools/run_root_unittests.py` 確定性回報 2 筆失敗，其餘 1136 筆不受影響） | 根層 `tools/tests/test_bash_probe_spec_contract.py`（`_probe_a_real_usable_bash_for_fixture()` 探測邏輯，或改為驗活時額外要求候選在「不自我注入」語意上與 `usr/bin/bash.exe` 一致，需 Architect 設計裁決，非本列 fix-applier 自行決定範圍） | fixed@R71｜🔴 R75 訂正首詞（原文逐字接於後）：open（**現查覆現，可重現**：Bash 工具 `python -m pytest tools/tests/test_bash_probe_spec_contract.py -v` → `12 passed`；PowerShell 工具同指令 → `2 failed, 10 passed`，逐一列出上述兩個測試名稱與 `AssertionError: 0 == 0`；`python -c "..."` 診斷腳本〔见上方現查根因對照〕於兩載具分別列印候選清單與逐候選 rc，佐證根因判定非猜測。**本列刻意未強修**：修法涉及重新設計「候選驗活」判準（例如額外驗一次限縮 PATH 情境、或直接把 `usr/bin/bash.exe` designated 為唯一合法候選不再 fallback 到 `bin/bash.exe`），影響本檔既有 `TestBinBashLauncherSelfInjectsPathContract`／`_REAL_BIN_BASH` 等既有手法的分工介面，需要下一輪 Architect 評估設計後再動手，不宜在修復 `DEF-101-627`（純帳本回填）這個不相關任務裡順手夾帶）。**分流**：候選方向——①探測階段對每個候選額外跑一次「PATH 只含候選自身目錄」的限縮探測，只有兩種探測都成功才接受；②或直接砍掉 `bin/bash.exe` fallback，`_BASH` 只認 `usr/bin/bash.exe`（`shutil.which("bash")` 那條 fallback 保留）。**R71 採①變體 fixed**：`_platform_helpers.py::honours_external_path`｜🔴 **R75 複驗（類別 A）**：本欄末段自載「R71 採①變體 fixed」。R75 用**原始復現載具**（PowerShell 工具；本列原症狀正是 Bash 12 passed／PowerShell 2 failed）實跑 `pytest tools/tests/test_bash_probe_spec_contract.py` → **19 passed／2 subtests，rc=0**，兩支原失敗測試皆綠；`_platform_helpers.py:97 honours_external_path` 在位。 |
```

