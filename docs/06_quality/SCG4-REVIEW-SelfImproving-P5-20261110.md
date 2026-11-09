# SCG-4 獨立驗收報告：SelfImproving P5 頂尖專家四問檢視（2026-11-10）

受驗 tip＝`462fd94e`（P5 前＝`d864d638`）。QA＝Sonnet 獨立棒。oracle＝TCS-SelfImproving-P5-20261110（含〈勘誤〉）。共用工作樹唯讀；突變在 repo 外 worktree `D:\CursorProject\_wt_p5qa`，卡面基準在 `D:\CursorProject\_wt_p5qa_base`（d864d638）。

## 結論：有條件 PASS（無 P1；P2 兩項建議修後收口，其餘 P3／P4）

58 AT 全綠、零退化全綠、卡面逐位元組相同。但突變驗證有 4 個存活突變（2 個落在 TCS 明列的突變清單項目），安全面有 1 個路徑逃逸。主控可依下列 P2 修完後 refreeze；P2 不影響「功能是否存在」，影響「測試能否在日後擋住回歸」與「答案檔座標可讀 repo 外檔案」。

## 發現

### P2-1 座標檢查可逃出 repo 根（含 UNC）——`fourqparse._coord_ok`
- 座標：`tools/lib/selfimproving/fourqparse.py:198`（`repo / m["p"]`，`_COORD_RE=^[^\s:]+:\d+…`）。
- 實測：`../AISDCL_Agent/CLAUDE.md:1` 回 `(True,'')`（可定位）；`\\localhost\c$\Windows\win.ini:1` 回 `(True,'')`（Windows 上 `Path / UNC` 取代根，觸發 SMB 存取）。`..` 在 Q3 工具判準有擋（`".." not in tool`），座標路徑沒擋，兩處不對稱。
- 影響：答案檔由審視者（子代理）撰寫、內容視為資料——座標讓 CLI 在入帳時探測 repo 外任意檔的存在與某行是否含查詢字串（零項 Q1 的 `q in ls[n-1]` 成為內容探測 oracle），UNC 還會連網。與 TCS AT-445-4-1「`fourq.py` 無網路」的意圖衝突，也繞過「外部衍生隔離」。
- 建議：座標路徑一律拒絕 `..` 片段、絕對路徑（含 `/` 起頭、反斜線 UNC）、並以 `Path.resolve()` 驗證仍在 `repo.resolve()` 之下；補一個 AT 變體（AT-441-3-E-1）。

### P2-2 「額度帶→項數上限」的真入口映射沒有任何 AT 守住（突變存活）
- 突變：`fourq.py:87` `cap = params["fourq_items_max" if _free_band() else "fourq_degrade_items_max"]` 改為恆用 `fourq_items_max`。FM 全 26 個 AT 與 FG 全 31 個（排除範圍守衛）**全部通過**＝存活。
- 原因：AT-441-2-E-3（`test_selfimproving_fourq_model.py:127-140`）的 `with f5.free_band(band): got = fourq.review` 區塊只取函式參考、不呼叫，`items_max` 由測試自己傳給 `fourqparse.validate`；band 注入縫從未影響任何斷言。PRD AC「降載帶上限＝degrade 值」在入帳路徑上無守衛。
- 建議：AT-441-2-E-3 改成真呼叫 `fourq --answers-file`（`free_band("notice")` 下 2 項 Q3 ⇒ rc 1 `FOURQ-ITEMS-OVER`；`free_band("free")` 下同檔 ⇒ rc 0）。

### P3-1 `loop` 快照的值只有 M1 狀態被獨立對帳（突變存活 ×2）
- `fourqparse.loop_snapshot` 回傳改成 M5a/M5b 對調，或 M4 換成假值，AT-441-4-2 仍過。測試的 `direct` 是同一函式自比（`test_selfimproving_fourq_model.py` AT-441-4-2 段），只有 `m1.status` 與 `meastat.metrics` 比對；TCS 要求 M1、M4、M5a、M5b「與 meastat 同函式直接重算相等」。
- 建議：四項各自與 `meastat.metrics(...)["success"]` 的 `{status,value,n,reason}` 逐鍵比對。

### P3-2 查詢寬度下界邊界（寬度 3）未測（突變存活）
- `fourqparse.py:225` `w < 4` 改 `w < 3`，AT-441-3-E-2 仍過（測試只用寬度 2 的「漸」）。TCS 明列「寬度 3（`-TOO-SHORT`）」。建議補寬度 3 變體。

### P3-3 Goodhart 否定形態的「單字『非』不構成豁免」未測（突變存活）
- `_NEG` 加入單字 `"非"`，AT-441-4-E-1 仍過。TCS：「單字『非常』或『非』不構成豁免」。補 `非常觀察筆數…` 變體。

### P3-4 「skip 運轉不判 IS-PROPOSER」無對照（突變存活）
- `evspec.gate_codes` 把條件放寬到 skip 事件也判，AT-443-1-E-2 仍過（skip 事件 `by` 固定 `main`，測試沒用 `--proposer main`）。補 `skip` 運轉＋`--proposer main` 放行的對照。

### P3-5 範圍守衛在 tip 以預設基準是「未觸發」的空綠，與 TCS 提交程序③④互相打架
- `test_AT_440_8_1`、AT-445-5-1 在預設基準（`HEAD~1`＝`f06cbbe7`…實為 462fd94e 的前一個）通過，因為 462fd94e 只動 P5 TCS，未觸及允許集合＝「範圍守衛未觸發」。以 TCS ⑥指定的規格 commit 為基準（`SI_P4_BASE_SHA=d9fa84c9`）重跑則 **紅**：差異含 `docs/03_testing/contracts/TCS-SelfImproving-P5-20261110.md`（勘誤 commit）。以 P5 前 `d864d638` 為基準亦紅（含規格 commit 的 PRD／SOP／SCG0 報告）。
- 我另以 `git diff --name-only d864d638 462fd94e` 獨立驗證：實作範圍乾淨（無 `.claude`、`AgentConsole`、`.github`、`fold.py`、`writeverbs.py`、`resume_route.py`、`schedule_backend.py`、`unattended_authz.py`、`model_roles.py`、`research_sources.json`、P0～P4 TCS、研究方法 SOP 的差異；實作 commit f06cbbe7、1c3d26f9 不含 PRD／SOP／TCS）。
- 結論：「範圍守衛綠」成立（獨立驗證為實），但該綠不是由守衛證明的。建議勘誤記一筆：P5 TCS 自身應由守衛豁免（現僅豁免 `-P4-`），否則 P5 TCS 一有勘誤、用規格 commit 當基準就必紅。

### P4-1 傳遞性子行程
- `fourqparse.loop_snapshot` 經 `mea`／`meastat`／`Git` 會間接呼叫 `git` 子行程（既有 P3 唯讀碼）。`fourqparse` 登記 `ro` 是指不寫入；AT-444-6-1 只掃直接 import。屬已知可接受，登記於此供日後 capability 判準參考。

### P4-2 勘誤編號
- 任務書寫「勘誤一～七」，檔內實為一～八（八＝AT-445-5-1 無跳過字樣判準），且排序為六、八、七。不影響內容。

## 驗收重點 1：AT 全跑
- 指令：`.venv\Scripts\python.exe -m pytest tools/tests/test_selfimproving_fourq_model.py tools/tests/test_selfimproving_fourq_gate.py -q -p no:xdist -o addopts=`（預設基準，tip）→ **58 passed in 83.50s，rc=0**。含 AT-445-5-1。
- `test_AT_440_8_1`＋AT-445-5-1 單跑預設基準：2 passed rc=0（見 P3-5：空綠）。
- 抽查 8 個 AT 對 TCS：AT-441-2-E-2（管線／控制字元／位元組）、AT-441-2-E-3、AT-441-3-E-2、AT-441-4-2、AT-442-2-E-1、AT-443-2-E-1、AT-444-4-1／E-1、AT-443-4-1／E-1。多數貼合；AT-441-2-E-3（P2-2）、AT-441-4-2（P3-1）、AT-441-3-E-2（P3-2）有缺口，AT-443-1-E-2（P3-4）缺對照。

## 驗收重點 2：突變結果表（worktree 改一處→跑 AT→改回；`git status` 於收場前確認乾淨）
| # | 突變 | 對應 AT | 結果 |
|---|------|---------|------|
| M1 | 二級標題逐字判準關閉 | AT-441-2-E-1 | 轉紅 |
| M2 | ASCII 管線判準整段關閉 | AT-441-2-E-2 | 轉紅 |
| M3b | 管線判準擴及 Q3／Q4 且不剝反引號（破壞 Q4 反引號例外） | AT-441-2-E-2 | 轉紅 |
| M4b | 項數上限 `>` 改 `>=` | AT-441-2-E-3 | 轉紅 |
| **M4** | **額度帶→cap 恆用 `fourq_items_max`（真入口）** | AT-441-2-E-3／AT-442-*／FG 全檔 | **存活（P2-2）** |
| M4' | cap 恆用 degrade 值 | AT-441-4-2 | 轉紅 |
| M5a | 查詢綁定（UNBOUND）關閉 | AT-441-3-E-2 | 轉紅 |
| M5b | 零／非零比對整段關閉 | AT-441-3-2 | 轉紅 |
| M5c | 只留「宣稱零命中而實際 >0」一半 | AT-441-3-2 | 轉紅 |
| M6 | 全文引用檢查關閉 | AT-441-3-E-3 | 轉紅 |
| M6b | MEA 號放行 | AT-441-3-E-3 | 轉紅 |
| M7 | 寬度上限 16→20 | AT-441-3-E-2 | 轉紅 |
| **M7b** | **寬度下界 4→3** | AT-441-3-E-2 | **存活（P3-2）** |
| M8 | `gate_codes` 適用判斷移除 | AT-443-3-E-1 等 | 轉紅 |
| M8b | `FOURQ-IS-PROPOSER` 判準移除 | AT-443-1-E-2 | 轉紅 |
| **M8c** | **IS-PROPOSER 擴及 skip 運轉** | AT-443-1-E-2 | **存活（P3-4）** |
| M9／M9b／M9c | `check` 順序判準：全關／只判研究前／只判 prop 後 | AT-443-2-E-1 | 皆轉紅 |
| M10／M10b | 卡面 tail：「任一欄」／「恆渲染」 | AT-443-3-1 | 皆轉紅 |
| M11 | `loop` 快照寫入 `mea.*` 事件（真實追加一行） | AT-441-4-2 | 轉紅 |
| **M11b／M11d** | **M5a／M5b 對調；M4 換假值** | AT-441-4-2 | **存活（P3-1）** |
| M11c | 載體缺席時不回 NE | AT-441-4-2 | 轉紅 |
| M12／M12b | `unattended` A 類移除 `fourq`／READONLY 移除 `fourq-corpus` | AT-444-5-1 | 皆轉紅 |
| M13／M13b／M13c | `patrolbrief` 四問逐字關閉／舊範本步數範圍 1..8（失去 fail-closed）／指令句檢查關閉 | AT-444-1-E-1 | 皆轉紅 |
| M14／M14b | 步 0′ 適用判斷移除／有 fourq 仍記日誌 | AT-444-3-E-1 | 皆轉紅 |
| M15 | `DEGRADE_TEXT` 呼叫形態改變 | AT-444-2-1 | 轉紅 |
| M16 | `fourq_from_run` 改字串比較（1000 對 999） | AT-443-4-1 | 轉紅 |
| M17 | 無人環境 `--skip` 拒收關閉 | AT-442-2-E-1 | 轉紅 |
| M18 | `gate_codes` fail-closed（勘誤五）關閉 | AT-443-4-E-1 | 轉紅 |
| M19／M19c／M19d／M19e | Goodhart 否定豁免全關／Q4 反引號例外移除／`%` 禁字移除／參數鍵名禁字移除 | AT-441-4-E-1 | 皆轉紅 |
| **M19b** | **否定詞表加入單字「非」** | AT-441-4-E-1 | **存活（P3-3）** |
| M20 | `FOURQ-NOT-RUN` 移除 | AT-443-2-E-2 | 轉紅 |
| M21 | `PROOF-LEAK` 移除 | AT-443-3-E-1 | 轉紅 |
| M22 | LF 雜湊比對移除 | AT-443-2-E-1 | 轉紅 |
| M23 | `FOURQ-BEFORE-RESEARCH` 碼改名 | AT-442-1-E-1 | 轉紅 |
說明：FG 突變運行時排除 AT-445-5-1／AT-440_8_1（worktree 內改檔必觸發範圍守衛＝非訊號）；M4 在含範圍守衛的 FG 全檔「轉紅」是範圍守衛的假訊號，排除後 31 passed＝存活。M3（只改成 `"|" in line` 且仍限 Q1／Q2G）與 M3c 為等價／越界變體，不計。

## 驗收重點 3：規格符合（逐項）
- 四問原句逐字：`fourqparse.QS`／`TITLES`、`patrolbrief.template_problems`、SOP 判準（AT-441-1-1／E-1、AT-444-1-E-1）有守，M1、M13 轉紅。
- 答案檔判準：標題、項數（但見 P2-2）、查詢綁定與寬度（但見 P3-2）、零項舉證（`Q1-X` 涵蓋座標指向的行含查詢字串）、全文 ID 引用、Q4 禁字與 Goodhart（但見 P3-3）＝實作與 PRD 一致。
- 迴圈層快照不寫 `mea.*`：M11 轉紅；值對帳弱（P3-1）。
- `prop-new`：`FOURQ-MISSING`／`FOURQ-IS-PROPOSER`／`FOURQ-PARAM-INVALID`（M8、M8b、M18）、`method`／`proof`（M21、AT-443-3-E-1）＝一致。
- 卡面 tail 兩欄皆有才渲染、核心區不變（M10 轉紅、卡面逐位元組比對見下）。
- `status.fourq` 第 17 鍵、與 export 同值（AT-444-4-1 綠）；真帳本現查 `status --json` 的 `fourq`：`state=exempt`、`gaps_open.count=0`、`missing_runs=0`（`fourq_from_run` 大於現有運轉，適用起點尚未到）。
- 無人：A 類、`--skip` 拒收、`--dry-run` 同閘（M12、M17 轉紅）。`patrolbrief` 舊範本 fail-closed（M13b 轉紅）。步 0′ 日誌（M14 轉紅）。
- 真帳本 `fourq --corpus` rc=0，印出固定清單（唯讀）。

## 驗收重點 4：零退化
- SI 全部測試檔（27 檔，`tools/tests/test_selfimproving*.py`）：見文末「SI 全套」結果。
- `python tools/selfimproving.py check` → **overall=PASS rc=0**，fingerprint `sha256:519d800f…0f310b4f`（nonblocking NE 為既有 console 金鑰環項目）。
- `AgentConsole/engine-bridge`：`tests/test_si_export_differential.py`＋`tests/test_si_deploy_config.py` → **19 passed rc=0**。
- `python AutoClaude/tools/check_loc_budget.py --json` → rc=0，`absolute_violations`／`tier_violations`／`special_violations` 皆空（total 18647／cap 20438）。
- `ruff check`（`d864d638..462fd94e` 之 33 個改動 .py）→ **All checks passed, rc=0**。
- 卡面：`PROP-SI-004～007` 各以 `card`＋`card --json` 在 d864d638 worktree 與 462fd94e worktree 各跑一次、stdout 位元組比對：**8 組全部 identical**（rc 皆 0）。

## 驗收重點 5：勘誤合理性
- 勘誤一（info→warn）：PRD 的「資訊項」改 warn，理由（`check.py` 不在允許集合、info 會轉 blocking NE）屬實；`check` rc 不變（真帳本 rc=0），意圖達成。非降標。
- 勘誤二（站點補列；P4 AT 的兩處斷言調整）：`test_AT_438_2_1` 改以 `DEGRADE_TEXT` 前綴「降載聲明：額度帶」判斷、`step6`→`step7` 變體，仍具鑑別力（M15 轉紅）。非降標。
- 勘誤三（CORPUS 固定清單、多放檔改讀為「不符樣式的檔」）：把「多放一個 archive」排除出不變性。屬必要澄清，但留一個語意代價：新增符合樣式的 archive 檔會改變重放結果。審視者與 CLI 同讀 `fourq --corpus` 清單，一致性不受影響。接受（P4 級備註）。
- 勘誤四（`loop` 格式）：具體化，非降標。
- 勘誤五（`FOURQ-PARAM-INVALID` fail-closed）：**提高**標準。
- 勘誤六（`Q2-F0` 不計 q2 項數）：放寬計數，但理由（降載帶上限 1 仍容得下免掃＋1 缺口候選）成立；`FOURQ-ITEMS-OVER` 以 q2 計數，免掃不佔額度屬一致設計。接受。
- 勘誤七（細部）：補規格，非降標。
- 勘誤八（無跳過字樣判準收斂到 `skipTest|skipIf|skipUnless|unittest.skip|pytest.skip|mark.skip|SkipTest|xfail`）：原判準誤殺函式名 `…_review_or_skip`；新判準涵蓋實際跳過寫法。接受。
- 無降低驗收標準者；但勘誤把 P3-5 的結構問題（P5 TCS 自身未被守衛豁免）留著。

## 驗收重點 6：安全面
- `fourq.py`／`fourqparse.py`／`evspec.py`：grep `eval(|exec(|subprocess|socket|urllib|requests|os.system|sleep|__import__|compile(` 零命中；答案檔只被正規式與字串比較處理，不依內容執行指令（唯一寫入＝`propfiles.write_new` `O_EXCL` 加 `evwrite` 追加，`fourq` 登記 `rw`）。
- 能力登記：AT-445-4-1／E-1 全綠。
- 例外：P2-1（座標路徑逃逸）。
- 外部衍生隔離：Q2-G 候選 URL 只判格式（`https`、無 userinfo、分級 T1／T2），不連網；`research.sources` 加入仍須經 T1。

## SI 全套
`pytest tools/tests/test_selfimproving*.py`（27 檔，`-p no:xdist -o addopts=`）→ **721 passed, 1611 subtests passed in 2240.54s，rc=0**。

## 收場
兩個 worktree 皆以 `git worktree remove`（不帶 --force）移除，rc=0；未建任何 junction／符號連結；共用工作樹 `git status` 乾淨、`worktree list` 只剩主樹。

## 指令與 rc
58 AT＝rc0；SI 全套 rc0；`selfimproving.py check` rc0；bridge 兩檔 rc0（19 passed）；`check_loc_budget.py --json` rc0；`ruff check` 33 檔 rc0；卡面 4×2 逐位元組 identical；範圍守衛預設基準 rc0、基準 d9fa84c9／d864d638 皆 rc1（P3-5）；23 組突變腳本見上表。

---

# 二審（tip 5fffb8e1；修正 commit 90e88e11；2026-11-10）

## 結論：PASS（P1／P2＝0）
一審 P2-1、P2-2、P3-1～P3-4 全部已結；P3-5 依主控裁決不改（範圍守衛逐 commit 判）；P4-2 已在 5fffb8e1 修排序；P4-1 為資訊。

## 各項已結證據
- P2-1：`evspec.safe_path` 字面判定（`..` 片段、`/`／`\` 起頭含 UNC、磁碟代號、控制字元／NUL）先於任何檔案系統存取，通過才 `resolve().relative_to(repo.resolve())`。AT-441-3-E-1 以 mock 守衛 `Path.exists/is_file/is_dir/read_*/open/resolve…`，座標與工具路徑逃逸須回 `FOURQ-COORD-ESCAPE` 且不碰 FS（測試檔約 187～199 行）。突變「字面判定關閉」→ AT-441-3-E-1 轉紅。
- P2-2：AT-441-2-E-3 改真入口；突變 cap 恆用 items_max、恆用 degrade 皆轉紅。
- P3-1：M5a／M5b 對調、M4 換假值，AT-441-4-2 轉紅。P3-2：`w<4`→`w<3`，AT-441-3-E-2 轉紅。P3-3：`_NEG` 加「非」（現住 `evspec.py:441`），AT-441-4-E-1 轉紅。P3-4：IS-PROPOSER 擴及 skip，AT-443-1-E-2 轉紅。

## 突變表（worktree checkout 5fffb8e1）
| 突變 | 對應 AT | 結果 |
|---|---|---|
| cap 恆用 `fourq_items_max` | AT-441-2-E-3 | 轉紅 |
| cap 恆用 `fourq_degrade_items_max` | AT-441-2-E-3 | 轉紅 |
| 查詢寬度下界 4→3 | AT-441-3-E-2 | 轉紅 |
| `_NEG` 加單字「非」 | AT-441-4-E-1 | 轉紅 |
| `loop_snapshot` M5a／M5b 對調 | AT-441-4-2 | 轉紅 |
| `loop_snapshot` M4 換假值 | AT-441-4-2 | 轉紅 |
| IS-PROPOSER 擴及 skip | AT-443-1-E-2 | 轉紅 |
| `safe_path` 字面判定關閉 | AT-441-3-E-1 | 轉紅 |

## safe_path 繞法探針（實跑 `safe_path`、`_coord_ok`）
- ESCAPE：`../x`、`..\x`、`a/../../x`、`a\..\..\x`、UNC `\\localhost\c$\x`、`\\?\C:\Windows\win.ini`、`//localhost/c$/x`、`/etc/passwd`、`C:win.ini`、`c:\x`、`.. /x`、`../ x`、`... /x`、`a/.. /../x`、NUL、前置空白、`tools/..`、`../`。`_coord_ok` 對 `../AISDCL_Agent/CLAUDE.md:1`、UNC、`..\x:1` 皆 `(False,'ESCAPE')`（一審原為 `(True,'')`）。
- ok（非繞法）：全形斜線、`∕`、全形點、`‥`、`..%2f`、`...`——皆為一般檔名字元，`_coord_ok` 回 `(False,'')`（不存在）。`_COORD_RE` 仍排除冒號，ADS 無從進入。

## 範圍守衛（worktree checkout 90e88e11，預設基準 HEAD~1＝462fd94e）
`test_AT_440_8_1`、AT-445-5-1：**2 passed rc=0**。該 commit 只動 `tools/`，觸及允許集合＝守衛觸發且綠。

## 零退化（tip 5fffb8e1）
- 兩 fourq 檔 58 AT：58 passed in 80.33s，rc=0。
- events／check／capability／issuemap／export_status 五檔：122 passed、349 subtests passed in 421.66s，rc=0。
- `selfimproving.py check`：overall=PASS rc=0，fingerprint 與一審相同（`sha256:519d800f…`）。
- `ruff check`（462fd94e..5fffb8e1 改動的 .py）：rc=0。`check_loc_budget.py --json`：rc=0，total 18647／cap 20438，三類違規 0。

## 新發現
- P4-3（資訊）：`safe_path` 以字串判定、不把全形斜線視為分隔，現行平台正確；日後若引入會折疊 Unicode 斜線的檔案系統再檢視。無 P1／P2／P3。

## 收場
`_wt_p5qa2`、`_wt_p5qa3` 以 `git worktree remove`（不帶 --force）移除，rc=0；無 junction；共用工作樹未動。
