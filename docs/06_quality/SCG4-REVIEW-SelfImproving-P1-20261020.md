# SCG-4 實作審查報告：SelfImproving P1（鍵 A `monorepo-si-p1-propose`＋鍵 B `autoclaude-evolution-propose-only`）

| 項目 | 值 |
|------|----|
| 審查對象 | HEAD `001d3e5e72268462fca1c11c0b993a13bb5c4adb`（`68aa01ae` P1 核心實作＋鍵 B 契約測試 → `10039d54` 收尾單人窗口重釘 → `001d3e5e` OBS-SI-160～167） |
| 凍結基準 | P1 TCS `docs/03_testing/contracts/TCS-SelfImproving-P1-20261020.md`（Stage-2 digest `d7555681d94c143b71d8a35050a08b4da99eaefa8ed7f3e1f400b54e1f32c92c`）；PRD v0.9.1（`e90d8eb3…`）；研究方法論 SOP（`deb9716b…`）——三者 QA 以 CRLF→LF 位元組重算，全部相符 |
| 審查者 | QA（Sonnet 子代理，唯讀審查；寫入動詞、突變、損壞帳本實驗全在 scratchpad 複本上做；真實樹審查前後 `git status --short` 皆空、HEAD 不變） |
| 一審判定 | **FAIL**——P1／P2／P3／P4 ＝ 0／8／6／8 |
| 落檔說明 | 本檔由主控逐字謄寫 QA 的文字交卷（harness 規則：子代理不得寫報告檔，Write 被擋），§B／§C 兩張表為 QA 機器產生後由主控併入；QA 的稽核腳本、複本與原始輸出住 scratchpad（`selfimproving_p1\qa_work\scg4_qa\`，收輪即刪），本檔是唯一留存的證據 |
| 主控處置 | 見〈§L 主控處置〉（gate 走向、勘誤與修復棒派工、二審） |

> 數字口徑：§A～§K 所有量化數字皆為 QA 子代理當回合真跑的輸出（主控未逐一重跑，標 `[他包回報]`）；主控親驗的數字只寫在 §L。

## §A 摘要與判定

- **AT 覆蓋**：TCS 126 條（正控 57／負控 69）各恰 1 個測試函式，無缺對應、無錯對應、無 `-k` 誤收；168 個測試（P1 117＋P0 42＋鍵 B 9）全 PASSED（events 35／props 36／research_scan 28／export_status 7／capability＋layout 11／P0 42／鍵 B 9）。`[他包回報]`
- **判定指令純度**：126 條全部照字面實跑，117 條 rc=0「1 passed」；鍵 B 九條 rc=4（本機 PG 在場、AutoClaude 的 PG＋xdist 守門），加 `-n 0` 後各「1 passed」（見 §F ⑤）。`[他包回報]`
- **突變（鑑別力）**：194 個手工突變，偵測 168、存活 26（其中 A18b 為等價突變，真存活 25）；六個必審模組各 11～18 個（`events.py` 11／`evcheck.py` 13／`fold.py` 13／`fetch.py` 12／`props.py` 16／`writeverbs.py` 18）；126 個 AT 都被至少一個突變打紅（4 個落點 AT 由真實樹破壞探針打紅）。`[他包回報]`
- **判定依據**：P2 ×8（兩筆真實缺陷 F-01／F-02、一筆 fail-open F-12 列 P3、其餘為鑑別力缺口＝突變存活）⇒ 依任務書 §5 為 **FAIL**；無 P1。
- **V8（真實觀察端到端）與 V10（外網首跑）未驗**：V8 需主控於真實樹執行、V10 禁外網；兩者的機制半已在複本以等價鏈驗過（run-open → research --skip → scan → attr → confirm → prop-new → card → run-close → check／status／export，全 rc 符合規格，鏈後 `git status --porcelain` 只多事件帳本與 `SelfImproving_Proposals/`；loopback `--fetch` 鏈 rc=2、`SOURCES-UNCOMMITTED` 預檢拒收、`changed` 旗標、事件鍵序、`check` PASS 皆符合）。

## §D NFR-P1-1～11

| NFR | 結果 | 證據（QA 當回合） |
|-----|------|------------------|
| 1～7、9～11 | 通過 | ruff 對 38 個改動 .py rc=0；`python AutoClaude/tools/check_loc_budget.py --json` rc=0（違規 0）；能力登記 24＝ro 19＋rw 3＋net 2 與磁碟逐一對應；唯讀動詞行程不載入 evwrite／propfiles／writeverbs／fetch／research、零 `socket.connect`；`subprocess` 只在 `tools/lib/selfimproving/git.py`；R64 十四個禁字樣零命中 |
| 8（範圍守衛） | 過程偏差（F-15，P4） | Developer 提交改了 §5.6 以外 6 個鎖檔（`tools/lib/skip_tag_policy.py`、`tools/run_root_unittests.py`、`tools/tests/test_platform_neutral_paths.py`、`tools/tests/test_subprocess_encoding_hygiene.py`、`tools/tests/test_windows_forbidden_filename_parity.py`、`ONBOARDING.md`），已由 OBS-SI-161 追認、數字經根層全套複驗正確 |

## §E 實跑檢核 V1～V11

| V | 結果 | 證據（QA 當回合，`[他包回報]`） |
|---|------|------|
| V1 範圍 | 通過（附 P4 F-15） | `git diff --name-only`／`git diff --stat -- .claude`／`git status --porcelain`：`.claude/**`、PRD、研究方法 SOP、P0 TCS、`AutoClaude/autoclaude` 引擎碼無變動；真事件帳本與真 `SelfImproving_Proposals/` 不在 diff 內 |
| V2 真 repo check | 通過 | `check --json` ×3 rc=0（2.02／1.79／1.78 s，28 項，`research.sources` PASS，`ref.obs` PASS） |
| V3 P0 回歸 | 通過 | P0 42 passed；`git diff -U0 -- tools/tests/test_selfimproving_check.py` 只有 R67 五站點的 6 個 hunk |
| V4 P1 新 AT | 通過 | 見 §A；每個 `-k` 恰收 1 個測試 |
| V5 護欄與零退化 | 通過 | 根層全套 rc=0、183 s、「發現 5543 個測試（下限 5542）」；`--check-snapshot` rc=0；`--print-guard-lines` +0、漂移 0；`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 49 passed |
| V6 params 與來源表 | 通過 | 五鍵初值 8、262144、20、1、500 與來源表 7 筆逐字相符 PRD |
| V7 SOP 語意 | 通過 | SOP 條文語意與 PRD AC-SI-07-2／09-1／10-2／11-2／30-4 ①②／31-5 一致 |
| V8 真實端到端 | **未驗（主控執行）** | 機制半已在複本驗過（§A） |
| V9 不觸及正式面 | 通過 | 複本鏈後只多事件帳本與 Proposals 目錄 |
| V10 外網首跑 | **未驗（主控執行）** | QA 禁外網；loopback 鏈已驗 |
| V11 效能 | 通過 | 真 repo `check` 三次最大 2.02 s；新測試檔本機最長 72 s |

## §F TCS 內部不一致五項裁定（任務書 §3-6）

1. **① QUOTE-VERIFIER S=PASS vs NE nonblocking**：採納實作（warn、項目狀態不變）——AT-103-2-1／AT-108-4-E-2 要 `S(events.transitions)=PASS`，`tools/lib/selfimproving/check.py:91-98` 的規則下只有 warn 層級能同時成立；TCS 勘誤判定碼表、R36 (d)、R38、R42 (d)。座標：`tools/lib/selfimproving/evcheck.py:61-63` 以 warn 發出（細節「[warn] 帳本含 N 筆 dec；引言回查屬 P2」）；`check.py:213-214` 對 PASS 項仍印 warn finding；PRD AC-SI-08-4 ⑤ 的「不得靜默」由碼名與細節滿足。
2. **② AT-108-4-1 的 SC-LEGAL 含 dec**：採納實作（取 R38）——AT 句「F 為空」是筆誤，測試 `tools/tests/test_selfimproving_events.py:898-902` 已斷言「恰為那一則提示」，沒有放寬。
3. **③ R45 先剝反引號指令片段**：採納實作——否則每個草稿列（證據格＝`python tools/selfimproving.py <verb>` 指令片段）都對已結列觸發 REOPEN-CANDIDATE，R28 (d) 的零 finding 不成立；只剝 R16 第八形態（`tools/lib/selfimproving/rows.py:79-86`），反引號包住的普通路徑照取；突變 R1、R3 被打紅。
4. **④ http→https 同 host 亦拒**：採納（任何 scheme 變更皆拒＝fail-closed），**但 Developer 的前提不成立**——AT 的函式層案例用預設埠，已因 `host:port` 不在允許集合被拒，與 scheme 判準無關；該判準目前沒有任何測試鎖住（突變 X2 全套全綠，F-03），TCS 案例須改顯式同埠。QA 實證：`check_redirect("https://h.example:8443/a","http://h.example:8443/b",{"h.example:8443"})`＝`redirect-refused`、同 scheme 同埠＝`None`（`tools/lib/selfimproving/fetch.py:54-60`）。
5. **⑤ 鍵 B 需 `-n 0`／ADR-SI-07 漏列 `_TREE_FILE_FLOORS`**：採納——本機（PG 在場）九條字面指令 rc=4，既有 r85 測試字面同樣 rc=4，加 `-n 0` 九條各「1 passed」；`_TREE_FILE_FLOORS` 已在 NFR-P1-8 列名且實作已重釘（`tools/tests` 73→78、`AutoClaude/tests` 242→243），漏的是 PRD 凍結文字，留 PRD 下次修訂。
- 另發現兩項同型不一致（F-14 ⑥⑦）：V8 要 `friction_reconcile=measured` 但 §4〈刻意不做〉與實作皆不產生 measured；R56 (a) 要觸及比例小數兩位，M 類卡面實作印 `n/a`（`tools/lib/selfimproving/card.py:138`，TCS／AT 無 M 類卡面案例）。

## §G 缺陷清單

### P2（8）——皆需補測或修碼後由 QA 複驗

| 編號 | 症狀與座標 | 重現 | 建議修法 |
|------|-----------|------|---------|
| F-01 | **`fetch.py` 牆鐘上限對慢滴回應不成立（連網面越界，真實缺陷）**：`tools/lib/selfimproving/fetch.py:71-82`（`resp.read(_CHUNK)` 會阻塞到湊滿 8192 位元組或 EOF，期限檢查 `:77` 只在 chunk 之間）。loopback、`timeout=2`：送完標頭後完全停滯→2.0 s 正確 `timeout`；每 0.5 s 滴 1 byte→14.0 s 才返回（server 停手後），server 不停手則不返回。突變 X11（刪 `:77` 檢查）全套全綠；AT-130-5-E-1 (d) 只測整個回應延遲 | QA 腳本 slowdrip.py（scratch） | 自管 `http.client.HTTPConnection`，每次讀取前 `conn.sock.settimeout(max(0.001, deadline-now))`＋`read1`（不可用 `threading.Timer`，R64 禁字樣）；補慢滴 AT |
| F-02 | **型別怪異的手寫事件讓 `events.validate`／`fold` 拋 `TypeError`，`check`／`status`／`export` 與多數寫入動詞整體崩潰（真實缺陷）**：`tools/lib/selfimproving/events.py:186`、`events.py:236`、`fold.py:236`、`fold.py:317`、`status.py:43`、`evcheck.py:154/163`；與 `fold.py` 檔頭「絕不拋例外」及 R37（型別不合⇒`EVENT-TYPE`）不符。複本 E2E：帳本追加一行 `research.skip` 且 `reason:["a"]`（或 `attr` 的 `obs:[["x"]]`、`type:["root"]`）→ `check`、`status`、`export`、`run-close`、`attr-confirm`、`research --skip` 皆 rc=1＋Traceback（`unhashable type: 'list'`）；fuzz 20,000 輪＝1,328 次崩潰（6 個程式行）；patch／本文／來源表解析器 30,000 輪零例外 | QA 腳本 fuzz2.py、corrupt_e2e.py（scratch） | 結構正解：`fold()` 只吃通過 `events.validate` 的事件，未通過者由 `events.structure` 報 `EVENT-*`；查表鍵先 `isinstance(x, str)`；補參數化 AT |
| F-03 | 重導向「scheme 不得改變」無任何測試鎖住（突變 X2 存活）：`tools/lib/selfimproving/fetch.py:58`；測試 `tools/tests/test_selfimproving_research_scan.py:511-521` 的案例被預設埠差異遮住（實作正確，只是沒人釘它） | 同埠 https→http＝`redirect-refused` | TCS 案例改顯式同埠並補反向／同 scheme 同埠對照 |
| F-04 | 事件結構值域缺 check 層負控（突變 E3、E6、E7、E9、C9 存活）：`events.py:114-115`（note≤120）、`:138`（http_status 200～299）、`:233-235`（research.skip 的 by 恆為 main）、`:118-122`（sid UUID 正規形）、`evcheck.py:48`（EVENT-BYTES-OVER 恰等於上限放行）；AT-108-4-E-2 案例表漏列 | 突變表 | 補負控 AT |
| F-05 | `evcheck` 邊界缺測（C7、C12）：`evcheck.py:61`（單一 dec 即須印提示）、`:202`（提交時間「不晚於」含等號；C12 非理論：來源表提交與 `research --fetch` 同一秒時含等號才通過，改成 `<` 全套全綠） | 突變表 | 補邊界 AT |
| F-06 | SUSPENDED 折疊缺負控（F2：all→any 存活）：`fold.py:300-307`；AT-103-1-E-1 只有「連續兩壞窗」 | 突變表 | 補負控 AT |
| F-07 | status／export／scan 缺測（S5、S6、Q2、N4）：`status.py:77`（verified 進 pending_props）、`status.py:62`（偵測窗以最近 run.close 為界——S6 使已處理事件每次 run.close 後重複偵測而全套不紅）、`export.py:131`（恰好整頁 truncated=false）、`scan.py:98` | 突變表 | 補 AT |
| F-08 | 其餘未釘住規則：(a) `--json` 的 `ensure_ascii=False`／UTF-8 直寫（A33；`export.py:143` 等；AT-140-2-E-1 在 cp950 下對純 ASCII 跳脫輸出也綠）(b) `ZERO-SUCCESS` 碼（A24；`research.py:114`）(c) 三個合法 content-type（X10；`fetch.py:23`）(d) 草稿列碼數>5 的「…等 k 項」（W11；`writeverbs.py:36`）(e) 鎖檔名 `[:16]` 算法（V4；`evwrite.py:61`）(f) 家目錄「存在但不可寫」（V5；`evwrite.py:52-54`） | 突變表 | 補 AT |

### P3（6）

| 編號 | 內容 |
|------|------|
| F-09 | 判準常數被自己的負控迴圈引用（鍵 B 的 `REWRITE_FRAGMENTS`；`tools/tests/_selfimproving_fixtures.py` 的 `SAME_LINE_GROUPS`；改 `line_has_all` 則皆紅，缺的是常數獨立釘選） |
| F-10 | M 類卡面觸及比例印 `n/a`（`tools/lib/selfimproving/card.py:138`；無 AT） |
| F-11 | `status.friction_reconcile` 第三種 reason `transcript-parser-not-established`（`tools/lib/selfimproving/status.py:31-35`）與 V8 判準矛盾 |
| F-12 | `git apply --numstat` 失敗被吞成空集合（`tools/lib/selfimproving/writeverbs.py:299-302` fail-open）：損毀 hunk 與 context-diff 格式 patch（git rc=128）皆通過超集檢查，後者經自寫解析器得 `touched=['1 ----','b/FROZEN.md']`（帶前綴、不命中不可進化面）；P1 無套用者故暴露為零，但違反 fail-closed，建議 numstat 失敗即 `PATCH-PARSE` 拒收 |
| F-13 | SSOT 連動面未收齊：`docs/02_architecture/Root_Layout_and_Module_Placement.md:52`（§3 SelfImproving 列只列 P0）與 `:72`（「沒有機械鎖…列為 P1 待辦」過期）；TCS §5.6 列為主控收尾項；落點鎖只驗路徑存在故不會紅 |
| F-14 | TCS 勘誤彙整（§F 五項＋F-10、F-11），建議文字見 §K |

### P4（8）

| 編號 | 內容 |
|------|------|
| F-15 | V1 範圍偏差（見 §D NFR-8），已由 OBS-SI-161 追認 |
| F-16 | 近等價突變 B3（`tools/lib/selfimproving/paths.py:133`）、B5（`paths.py:224`） |
| F-17 | 理論洞：來源表 URL 字串過濾放行 `localhost.`、`127.1`、`2130706433`、`0x7f000001`、`0177.0.0.1`、`0.0.0.0`（`tools/lib/selfimproving/sources.py:61-74`；R43 劃界、T1 才能改表、無暴露證據→登記理論洞） |
| F-18 | `tools/lib/selfimproving/check.py:31-32` `_NONBLOCKING` 仍含 QUOTE-VERIFIER 碼（死項） |
| F-19 | OBS-SI-162 末句「TCS 判定指令仍寫 SiCase」查無（TCS 全文零命中）——主控依 Developer 交卷轉述入帳的錯誤，須以訂正列結案 |
| F-20 | 兩支 compat-ci 的 `paths` 註解（`.github/workflows/windows-compat-ci.yml:233`、`.github/workflows/macos-compat-ci.yml:97`／`:577`）仍寫「P0」 |
| F-21 | `PROP-SI-NNN` 配號的 OBS 部分在鎖外計算（`tools/lib/selfimproving/writeverbs.py:334-338`，R32 (c) 字面要求鎖內） |
| F-22 | 落點鎖的套件登記以整欄子字串比對（`tools/tests/test_root_module_layout.py:129-133`，R62 (d) 要求片段內） |

## §H 誠實劃界（QA 沒跑到／跑不了）

V8 真實觀察端到端與 `friction_reconcile` measured（需主控；P1 也未實作 measured）；V10 對真實來源的首跑（外網）；macOS 實跑；GitHub CI 實際執行與 CI 單檔時間（本機最長 72 s）；突變非窮舉（194 個手工突變，存活清單是下限）；fuzz 只涵蓋事件列純函式面與 patch／本文／來源表解析器；只審 P1 增量，P0 未改動邏輯未重審；Developer 整檔 `ruff format` 取捨（OBS-SI-165）只複驗數字、不評政策。

## §I QA 指令與 rc 摘要

QA 的逐條指令與原始輸出住 scratchpad `selfimproving_p1\qa_work\scg4_qa\`（run_*.txt、v2_check_*.json、root_suite.txt、mut_results*.jsonl、fuzz*_out.txt、vchain*_out.txt、numstat_out.txt、x2_out.txt 等），收輪即刪；關鍵 rc 已逐項寫在 §A／§D／§E。複本以 `subst Q:` 縮短路徑（Windows MAX_PATH，`LongPathsEnabled=0`），要重現須重新 `subst` 並在複本 `git config core.longpaths true`。

## §J QA 流程摩擦（主控入帳）

1. Windows MAX_PATH：scratchpad 路徑 151 字元＋repo 最長相對路徑 142，`LongPathsEnabled=0`，複本展開與 `git add` 失敗；任務書 §0 未提。繞法 `subst Q:`＋複本 `git config core.longpaths true`。
2. `tar.exe`（bsdtar）解 `git archive` 輸出遇非 ASCII 路徑失敗且只解一半；任務書的 `git archive | tar -x` 在 PowerShell 管線也不可行（不傳二進位）；改 `git archive --output=` 加 Python `tarfile`。
3. PowerShell 工具把 `Remove-Item Env:\<變數>` 誤判成刪系統路徑而擋；改 `$env:X = $null`。
4. lint hook 擋「原生指令接 `Select-Object -First` 再讀 `$LASTEXITCODE`」——正確，但寫稽核腳本時易踩，一律導檔再讀 rc。
5. `python -I` 會忽略 `PYTHONUTF8`，輸出在工具中呈亂碼；改 `-X utf8` 並導檔再以 `Get-Content -Encoding utf8` 讀。
6. 任務書指定的報告檔寫不出（harness：子代理不得寫報告檔）；任務書與 harness 規則衝突，日後由主控落檔或明講交付形態。
7. 全套件突變即使「偵測即終止」也要約 65～90 s／個；改「AT 靶向 `-k`」才快（69 個突變 56 秒）；日後先建「AT→受測碼」對照再靶向。

## §K QA 建議的 TCS 勘誤（供主控套用並 `spec-refreeze`；本審查不改 TCS）

1. 判定碼表 `events.transitions｜QUOTE-VERIFIER-NOT-ESTABLISHED` 改「PASS（warn finding；項目狀態不變）」；R36 (d) 的 nonblocking NE 碼集合縮為兩個；R38 末句、R42 (d)、§4〈刻意不做〉改稱 warn 層級 finding。
2. AT-108-4-1 情境一：「`F(events.transitions)` 恰為單一 `(-, QUOTE-VERIFIER-NOT-ESTABLISHED)`（SC-LEGAL 含 dec）」。
3. R45：「先剝除符合 P0 R16 第八形態的反引號指令片段，再取 path／file／dir 三形態」。
4. R58 (c)：「scheme 不得改變（http↔https 皆拒）」；AT-130-2-E-3 函式層改顯式同埠案例（`https://example.com:8443/a`→`http://example.com:8443/b`，allowed＝`{example.com:8443}`）並加反向與同 scheme 同埠＝`None` 對照。
5. 鍵 B 九條判定指令與 NFR-P1-10 (1) 加 `-n 0`（本機 PG 在場時須加，或 `--dist loadgroup`）。
6. V8：`friction_reconcile` 為 NOT-EVALUABLE（P1）；R60 (c) 補第三種 reason。
7. R56 (a)：M 類無 base 快照，觸及比例印 `n/a`，並補一個 M 類卡面 AT。
8. 凍結後走勘誤補 AT：F-01 慢滴、F-02 型別怪異事件、F-03 同埠 scheme、F-04～F-08 所列案例。

## §L 主控處置（逐段追加）

- 一審收件（2026-10-20，HEAD `001d3e5e`）：判定 FAIL 成立。處置順序＝(1) 本報告落檔 commit；(2) P1 鍵 `transition --to SPEC_AUDIT` → 主控套用 §K 勘誤（含 F-01～F-08 新 AT）→ `spec-refreeze` → `transition --to PR_REVIEW` → `gate --gate PR_REVIEW --result FAIL`（一審 FAIL，修復棒未派）→ IMPLEMENTATION；(3) 派 Developer 修復棒（碼修 F-01／F-02／F-12／F-18／F-21／F-22；補測 F-03～F-09；鍵 B 判定指令加 `-n 0`）；(4) 主控自修 F-13（SSOT §3 與第 72 行）、F-19（OBS 訂正列）、F-20（compat-ci 註解）；(5) QA 二審（同一 QA 代理續審，重放存活突變清單）。

## §B AT 對照表（126 列；QA 機器產生，主控併入）

| AT id | 類型 | 測試方法（檔::類別::函式） | 結果 | 字面判定指令 | 咬住它的突變 |
|---|---|---|---|---|---|
| AT-110-3-1 | 正控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_110_3_1_run_open_five_triggers` | PASSED | rc=0；1 passed | A01 |
| AT-110-3-E-1 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_110_3_E_1_usage_and_state_errors` | PASSED | rc=0；1 passed | E2、W7 |
| AT-103-2-1 | 正控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_103_2_1_run_close_records_no_event_or_outcomes` | PASSED | rc=0；1 passed | W2 |
| AT-103-2-E-1 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_103_2_E_1_run_close_rejections` | PASSED | rc=0；1 passed | A02 |
| AT-105-1-1 | 正控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_105_1_1_attr_seven_kinds` | PASSED | rc=0；1 passed | A03 |
| AT-105-1-E-1 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_105_1_E_1_attr_rejections` | PASSED | rc=0；1 passed | A04 |
| AT-105-2-1 | 正控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_105_2_1_attr_only_touches_event_ledger` | PASSED | rc=0；1 passed | A05 |
| AT-105-2-E-1 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_105_2_E_1_no_self_assessment` | PASSED | rc=0；1 passed | A06 |
| AT-106-1-1 | 正控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_106_1_1_confirm_and_root_cause_changes` | PASSED | rc=0；1 passed | F5 |
| AT-106-1-E-1 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_106_1_E_1_confirm_rejections` | PASSED | rc=0；1 passed | F3、W1 |
| AT-106-2-1 | 正控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_106_2_1_link_and_settle` | PASSED | rc=0；1 passed | R3 |
| AT-106-2-E-1 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_106_2_E_1_link_rejections` | PASSED | rc=0；1 passed | W9 |
| AT-106-2-E-2 | 負控 | `test_selfimproving_events.py::TestRunsAndAttribution::test_AT_106_2_E_2_reopen_candidate_hint` | PASSED | rc=0；1 passed | R1、R3 |
| AT-141-1-1 | 正控 | `test_selfimproving_events.py::TestEventLedger::test_AT_141_1_1_event_line_shape` | PASSED | rc=0；1 passed | W2 |
| AT-141-1-E-1 | 負控 | `test_selfimproving_events.py::TestEventLedger::test_AT_141_1_E_1_numbering_and_boundaries` | PASSED | rc=0；1 passed | V1、V3 |
| AT-141-2-1 | 正控 | `test_selfimproving_events.py::TestEventLedger::test_AT_141_2_1_lock_serialises_writers` | PASSED | rc=0；1 passed | V2、W6 |
| AT-141-2-E-1 | 負控 | `test_selfimproving_events.py::TestEventLedger::test_AT_141_2_E_1_lock_failure_modes` | PASSED | rc=0；1 passed | W10、W6 |
| AT-108-4-1 | 正控 | `test_selfimproving_events.py::TestCheckReplay::test_AT_108_4_1_transitions_replay` | PASSED | rc=0；1 passed | F1、F10、F12、F4、F6、F7 |
| AT-108-4-E-1 | 負控 | `test_selfimproving_events.py::TestCheckReplay::test_AT_108_4_E_1_append_only` | PASSED | rc=0；1 passed | C1、C10 |
| AT-108-4-E-2 | 負控 | `test_selfimproving_events.py::TestCheckReplay::test_AT_108_4_E_2_structure_floor_and_dec_note` | PASSED | rc=0；1 passed | C2、C3、E1、E2、E4、E5、E8 |
| AT-142-1-1 | 正控 | `test_selfimproving_events.py::TestCheckAdditions::test_AT_142_1_1_p1_items_on_p0_baseline_and_after_a_round` | PASSED | rc=0；1 passed | PM2 |
| AT-142-1-E-1 | 負控 | `test_selfimproving_events.py::TestCheckAdditions::test_AT_142_1_E_1_prop_files_and_sources_table` | PASSED | rc=0；1 passed | C6 |
| AT-142-1-E-2 | 負控 | `test_selfimproving_events.py::TestCheckAdditions::test_AT_142_1_E_2_researcher_rows` | PASSED | rc=0；1 passed | RW1、RW2 |
| AT-142-2-1 | 正控 | `test_selfimproving_events.py::TestCheckAdditions::test_AT_142_2_1_p0_items_unchanged` | PASSED | rc=0；1 passed | A37 |
| AT-142-2-E-1 | 負控 | `test_selfimproving_events.py::TestCheckAdditions::test_AT_142_2_E_1_p0_negatives_unchanged` | PASSED | rc=0；1 passed | A62 |
| AT-140-1-1 | 正控 | `test_selfimproving_events.py::TestInterface::test_AT_140_1_1_thirteen_verbs` | PASSED | rc=0；1 passed | A66 |
| AT-140-1-E-1 | 負控 | `test_selfimproving_events.py::TestInterface::test_AT_140_1_E_1_unimplemented_verbs_and_reject_grammar` | PASSED | rc=0；1 passed | A36 |
| AT-145-1-1 | 正控 | `test_selfimproving_events.py::TestInterface::test_AT_145_1_1_real_protocol_files` | PASSED | rc=0；1 passed | A39 |
| AT-145-1-E-1 | 負控 | `test_selfimproving_events.py::TestInterface::test_AT_145_1_E_1_new_param_keys` | PASSED | rc=0；1 passed | A38 |
| AT-145-2-1 | 正控 | `test_selfimproving_events.py::TestSopArticles::test_AT_145_2_1_sop_is_final` | PASSED | rc=0；1 passed | A46 |
| AT-145-2-E-1 | 負控 | `test_selfimproving_events.py::TestSopArticles::test_AT_145_2_E_1_criteria_are_not_vacuous` | PASSED | rc=0；1 passed | A65 |
| AT-107-2-1 | 正控 | `test_selfimproving_events.py::TestSopArticles::test_AT_107_2_1_theory_hole_clause` | PASSED | rc=0；1 passed | A40 |
| AT-107-2-E-1 | 負控 | `test_selfimproving_events.py::TestSopArticles::test_AT_107_2_E_1_theory_hole_criteria` | PASSED | rc=0；1 passed | A70 |
| AT-111-2-1 | 正控 | `test_selfimproving_events.py::TestSopArticles::test_AT_111_2_1_evaluator_change_clause` | PASSED | rc=0；1 passed | A41 |
| AT-111-2-E-1 | 負控 | `test_selfimproving_events.py::TestSopArticles::test_AT_111_2_E_1_evaluator_change_criteria` | PASSED | rc=0；1 passed | A70 |
| AT-102-1-1 | 正控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_102_1_1_internal_source_suffices` | PASSED | rc=0；1 passed | A08 |
| AT-102-1-E-1 | 負控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_102_1_E_1_external_only_and_unresolved` | PASSED | rc=0；1 passed | A07 |
| AT-107-1-1 | 正控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_107_1_1_guard_surface_is_handed_off_whole` | PASSED | rc=0；1 passed | A4 |
| AT-107-1-E-1 | 負控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_107_1_E_1_route_and_channel_rules` | PASSED | rc=0；1 passed | A09 |
| AT-107-3-1 | 正控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_107_3_1_touched_derivation` | PASSED | rc=0；1 passed | A10 |
| AT-107-3-E-1 | 負控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_107_3_E_1_non_evolvable_paths_hand_off` | PASSED | rc=0；1 passed | B2 |
| AT-107-3-E-2 | 負控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_107_3_E_2_alias_forms_and_numstat_superset` | PASSED | rc=0；1 passed | B1、B4 |
| AT-107-3-E-3 | 負控 | `test_selfimproving_props.py::TestSourcesAndRoute::test_AT_107_3_E_3_conditions_and_markers` | PASSED | rc=0；1 passed | B2、P4 |
| AT-108-1-1 | 正控 | `test_selfimproving_props.py::TestProposalLifecycle::test_AT_108_1_1_prop_new_registers_proposed` | PASSED | rc=0；1 passed | A11 |
| AT-108-1-E-1 | 負控 | `test_selfimproving_props.py::TestProposalLifecycle::test_AT_108_1_E_1_stage_one_inputs` | PASSED | rc=0；1 passed | P11 |
| AT-108-2-1 | 正控 | `test_selfimproving_props.py::TestProposalLifecycle::test_AT_108_2_1_revise_returned` | PASSED | rc=0；1 passed | A12 |
| AT-108-2-E-1 | 負控 | `test_selfimproving_props.py::TestProposalLifecycle::test_AT_108_2_E_1_revise_rejections` | PASSED | rc=0；1 passed | W3 |
| AT-108-3-1 | 正控 | `test_selfimproving_props.py::TestProposalLifecycle::test_AT_108_3_1_rule_candidate_accepted` | PASSED | rc=0；1 passed | A13 |
| AT-108-3-E-1 | 負控 | `test_selfimproving_props.py::TestProposalLifecycle::test_AT_108_3_E_1_rule_candidate_rejected_or_handed_off` | PASSED | rc=0；1 passed | B2 |
| AT-109-1-1 | 正控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_109_1_1_body_shapes_accepted` | PASSED | rc=0；1 passed | A4 |
| AT-109-1-E-1 | 負控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_109_1_E_1_body_rejections` | PASSED | rc=0；1 passed | P10 |
| AT-109-1-2 | 正控 | `test_selfimproving_props.py::TestProposerArticles::test_AT_109_1_2_abstraction_clause` | PASSED | rc=0；1 passed | A42 |
| AT-109-2-1 | 正控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_109_2_1_ratio_and_new_entries` | PASSED | rc=0；1 passed | A4、P1、P5 |
| AT-109-2-E-1 | 負控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_109_2_E_1_archive_exemption` | PASSED | rc=0；1 passed | P6 |
| AT-109-3-1 | 正控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_109_3_1_m_fields_and_preimage` | PASSED | rc=0；1 passed | A14 |
| AT-109-3-E-1 | 負控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_109_3_E_1_m_field_rejections` | PASSED | rc=0；1 passed | P10、P7 |
| AT-110-1-1 | 正控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_110_1_1_budget_and_duplicates` | PASSED | rc=0；1 passed | P2、P8 |
| AT-110-1-E-1 | 負控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_110_1_E_1_state_rejections` | PASSED | rc=0；1 passed | P9 |
| AT-110-2-1 | 正控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_110_2_1_budget_declared_on_card` | PASSED | rc=0；1 passed | A15 |
| AT-110-2-E-1 | 負控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_110_2_E_1_budget_required` | PASSED | rc=0；1 passed | A16 |
| AT-110-2-2 | 正控 | `test_selfimproving_props.py::TestProposerArticles::test_AT_110_2_2_zero_recursion_clause` | PASSED | rc=0；1 passed | A43 |
| AT-111-1-1 | 正控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_111_1_1_classes_and_group_marks` | PASSED | rc=0；1 passed | P4 |
| AT-111-1-E-1 | 負控 | `test_selfimproving_props.py::TestBodyAndDelta::test_AT_111_1_E_1_evaluator_and_loop_self` | PASSED | rc=0；1 passed | P4 |
| AT-114-1-1 | 正控 | `test_selfimproving_props.py::TestCard::test_AT_114_1_1_card_format` | PASSED | rc=0；1 passed | A17 |
| AT-114-1-E-1 | 負控 | `test_selfimproving_props.py::TestCard::test_AT_114_1_E_1_card_ignores_free_text` | PASSED | rc=0；1 passed | A18c |
| AT-114-2-1 | 正控 | `test_selfimproving_props.py::TestCard::test_AT_114_2_1_parsed_matches_recomputed` | PASSED | rc=0；1 passed | A19 |
| AT-114-2-E-1 | 負控 | `test_selfimproving_props.py::TestCard::test_AT_114_2_E_1_tampered_card_refused` | PASSED | rc=0；1 passed | A20 |
| AT-114-3-1 | 正控 | `test_selfimproving_props.py::TestCard::test_AT_114_3_1_layout_boundaries_accepted` | PASSED | rc=0；1 passed | A18、A21 |
| AT-114-3-E-1 | 負控 | `test_selfimproving_props.py::TestCard::test_AT_114_3_E_1_layout_rejections` | PASSED | rc=0；1 passed | A1、A18、A2 |
| AT-144-1-1 | 正控 | `test_selfimproving_props.py::TestDigestAndFiles::test_AT_144_1_1_files_and_digest` | PASSED | rc=0；1 passed | A22 |
| AT-144-1-E-1 | 負控 | `test_selfimproving_props.py::TestDigestAndFiles::test_AT_144_1_E_1_digest_sensitivity_and_failures` | PASSED | rc=0；1 passed | W4 |
| AT-130-1-1 | 正控 | `test_selfimproving_research_scan.py::TestResearchEvents::test_AT_130_1_1_research_event_required` | PASSED | rc=0；1 passed | C5、C8 |
| AT-130-1-E-1 | 負控 | `test_selfimproving_research_scan.py::TestResearchEvents::test_AT_130_1_E_1_skip_reasons_and_rejections` | PASSED | rc=0；1 passed | W5、W8 |
| AT-130-2-1 | 正控 | `test_selfimproving_research_scan.py::TestFetching::test_AT_130_2_1_compliant_committed_table_passes_preflight` | PASSED | rc=0；1 passed | A60 |
| AT-130-2-E-1 | 負控 | `test_selfimproving_research_scan.py::TestSourceTable::test_AT_130_2_E_1_table_codes_and_preflight` | PASSED | rc=0；1 passed | A23、S1、S2、S7、S8 |
| AT-130-2-E-2 | 負控 | `test_selfimproving_research_scan.py::TestSourcesHistory::test_AT_130_2_E_2_sources_sha_against_history` | PASSED | rc=0；1 passed | C11、C4、K9 |
| AT-130-2-E-3 | 負控 | `test_selfimproving_research_scan.py::TestSourcesHistory::test_AT_130_2_E_3_redirect_guard` | PASSED | rc=0；1 passed | X1、X8 |
| AT-130-3-1 | 正控 | `test_selfimproving_research_scan.py::TestFetching::test_AT_130_3_1_fetch_raw_bytes_and_changed` | PASSED | rc=0；1 passed | X4、X9 |
| AT-130-3-E-1 | 負控 | `test_selfimproving_research_scan.py::TestFetching::test_AT_130_3_E_1_failure_matrix` | PASSED | rc=0；1 passed | X3、X5、X6、X7 |
| AT-130-3-E-2 | 負控 | `test_selfimproving_research_scan.py::TestFetching::test_AT_130_3_E_2_zero_success_and_json_shape` | PASSED | rc=0；1 passed | A68 |
| AT-130-3-E-3 | 負控 | `test_selfimproving_research_scan.py::TestFetching::test_AT_130_3_E_3_fetch_outside_lock` | PASSED | rc=0；1 passed | A25 |
| AT-130-4-1 | 正控 | `test_selfimproving_research_scan.py::TestResearcherRows::test_AT_130_4_1_researcher_candidate_accepted` | PASSED | rc=0；1 passed | A26 |
| AT-130-4-E-1 | 負控 | `test_selfimproving_research_scan.py::TestResearcherRows::test_AT_130_4_E_1_researcher_chain_rejections` | PASSED | rc=0；1 passed | P3、RW1 |
| AT-130-4-2 | 正控 | `test_selfimproving_research_scan.py::TestResearcherAndTemplateArticles::test_AT_130_4_2_researcher_section` | PASSED | rc=0；1 passed | A44 |
| AT-130-5-1 | 正控 | `test_selfimproving_research_scan.py::TestBudgetsAndFingerprint::test_AT_130_5_1_budget_boundaries_pass` | PASSED | rc=0；1 passed | X3 |
| AT-130-5-E-1 | 負控 | `test_selfimproving_research_scan.py::TestBudgetsAndFingerprint::test_AT_130_5_E_1_budget_overruns` | PASSED | rc=0；1 passed | X7 |
| AT-130-6-1 | 正控 | `test_selfimproving_research_scan.py::TestBudgetsAndFingerprint::test_AT_130_6_1_sources_excluded_from_fingerprint` | PASSED | rc=0；1 passed | PM1 |
| AT-130-6-E-1 | 負控 | `test_selfimproving_research_scan.py::TestBudgetsAndFingerprint::test_AT_130_6_E_1_other_protocol_files_change_fingerprint` | PASSED | rc=0；1 passed | A27 |
| AT-131-1-1 | 正控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_1_1_scan_is_pure` | PASSED | rc=0；1 passed | A28 |
| AT-131-1-E-1 | 負控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_1_E_1_scan_flags` | PASSED | rc=0；1 passed | A28 |
| AT-131-2-1 | 正控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_2_1_candidate_rows` | PASSED | rc=0；1 passed | A29、N2、N3 |
| AT-131-2-E-1 | 負控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_2_E_1_row_cap_and_header` | PASSED | rc=0；1 passed | A61 |
| AT-131-2-E-2 | 負控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_2_E_2_defs_differential` | PASSED | rc=0；1 passed | D2 |
| AT-131-3-1 | 正控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_3_1_zero_candidates` | PASSED | rc=0；1 passed | A29、A30 |
| AT-131-3-E-1 | 負控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_3_E_1_unavailable_sources` | PASSED | rc=0；1 passed | A29、A31 |
| AT-131-4-1 | 正控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_4_1_bucket_order` | PASSED | rc=0；1 passed | N1 |
| AT-131-4-E-1 | 負控 | `test_selfimproving_research_scan.py::TestScan::test_AT_131_4_E_1_bucket_edges` | PASSED | rc=0；1 passed | A32 |
| AT-131-5-1 | 正控 | `test_selfimproving_research_scan.py::TestResearcherAndTemplateArticles::test_AT_131_5_1_template_matches_prd` | PASSED | rc=0；1 passed | A45 |
| AT-131-5-E-1 | 負控 | `test_selfimproving_research_scan.py::TestResearcherAndTemplateArticles::test_AT_131_5_E_1_template_criteria_and_tree_state` | PASSED | rc=0；1 passed | A47 |
| AT-103-1-1 | 正控 | `test_selfimproving_export_status.py::TestStatus::test_AT_103_1_1_status_summary` | PASSED | rc=0；1 passed | N2、N3、S3、S4 |
| AT-103-1-E-1 | 負控 | `test_selfimproving_export_status.py::TestStatus::test_AT_103_1_E_1_status_edges` | PASSED | rc=0；1 passed | F11、F8、F9 |
| AT-132-5-1 | 正控 | `test_selfimproving_export_status.py::TestExport::test_AT_132_5_1_five_kinds` | PASSED | rc=0；1 passed | A34 |
| AT-132-5-E-1 | 負控 | `test_selfimproving_export_status.py::TestExport::test_AT_132_5_E_1_usage_pages_and_carriers` | PASSED | rc=0；1 passed | Q1、Q3 |
| AT-132-5-E-2 | 負控 | `test_selfimproving_export_status.py::TestExport::test_AT_132_5_E_2_differential_and_isolation` | PASSED | rc=0；1 passed | A3 |
| AT-140-2-1 | 正控 | `test_selfimproving_export_status.py::TestStability::test_AT_140_2_1_outputs_are_stable` | PASSED | rc=0；1 passed | A67 |
| AT-140-2-E-1 | 負控 | `test_selfimproving_export_status.py::TestStability::test_AT_140_2_E_1_no_unstable_sources` | PASSED | rc=0；1 passed | A35 |
| AT-143-1-1 | 正控 | `test_selfimproving_capability.py::TestCapabilityRegistry::test_AT_143_1_1_real_tree_matches_registry` | PASSED | rc=0；1 passed | A52、A53、A54、A55 |
| AT-143-1-E-1 | 負控 | `test_selfimproving_capability.py::TestCapabilityRegistry::test_AT_143_1_E_1_synthetic_violations_are_flagged` | PASSED | rc=0；1 passed | A48、A49、A50、A54 |
| AT-143-1-E-2 | 負控 | `test_selfimproving_capability.py::TestDynamicPurity::test_AT_143_1_E_2_dynamic_purity_and_forbidden_words` | PASSED | rc=0；1 passed | A51、A55 |
| AT-134-1-1 | 正控 | `test_root_module_layout.py::TestRegistryMatchesDisk::test_AT_134_1_1_real_registry_is_green` | PASSED | rc=0；1 passed | 真實樹探針 |
| AT-134-1-E-1 | 負控 | `test_root_module_layout.py::TestRegistryMatchesDisk::test_AT_134_1_E_1_missing_paths_are_red` | PASSED | rc=0；1 passed | A56 |
| AT-134-2-1 | 正控 | `test_root_module_layout.py::TestPrefixScatter::test_AT_134_2_1_compliant_shapes` | PASSED | rc=0；1 passed | 真實樹探針 |
| AT-134-2-E-1 | 負控 | `test_root_module_layout.py::TestPrefixScatter::test_AT_134_2_E_1_red_shapes` | PASSED | rc=0；1 passed | A57 |
| AT-134-3-1 | 正控 | `test_root_module_layout.py::TestPackagesAndPrds::test_AT_134_3_1_real_packages_registered` | PASSED | rc=0；1 passed | 真實樹探針 |
| AT-134-3-E-1 | 負控 | `test_root_module_layout.py::TestPackagesAndPrds::test_AT_134_3_E_1_unregistered_package_red` | PASSED | rc=0；1 passed | A58 |
| AT-134-4-1 | 正控 | `test_root_module_layout.py::TestPackagesAndPrds::test_AT_134_4_1_prd_must_cite_ssot` | PASSED | rc=0；1 passed | 真實樹探針 |
| AT-134-4-E-1 | 負控 | `test_root_module_layout.py::TestPackagesAndPrds::test_AT_134_4_E_1_missing_citation_red` | PASSED | rc=0；1 passed | A59 |
| AT-128-1-1 | 正控 | `test_evolution_propose_only.py::TestRealTree::test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | K1、K2、K4、K5、K7、K8 |
| AT-128-1-E-1 | 負控 | `test_evolution_propose_only.py::TestInjectedViolations::test_AT_128_1_E_1_missing_lock_and_stray_apply_sites_turn_cells_1_and_2_red` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | B01、B02 |
| AT-128-1-E-2 | 負控 | `test_evolution_propose_only.py::TestInjectedViolations::test_AT_128_1_E_2_injected_producers_turn_cell_3_red_excluded_files_do_not` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | B03 |
| AT-128-1-E-3 | 負控 | `test_evolution_propose_only.py::TestInjectedViolations::test_AT_128_1_E_3_extra_signoff_read_turns_cell_4_red_store_context_does_not` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | B04、B05 |
| AT-128-1-E-4 | 負控 | `test_evolution_propose_only.py::TestInjectedViolations::test_AT_128_1_E_4_doc_pin_rejects_missing_phrase_line_numbers_and_stale_main` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | B06、B07 |
| AT-128-2-1 | 正控 | `test_evolution_propose_only.py::TestDefaultAndRewrite::test_AT_128_2_1_default_still_false_and_doc_rewritten_within_line_budget` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | K3、K6 |
| AT-128-2-E-1 | 負控 | `test_evolution_propose_only.py::TestDefaultAndRewrite::test_AT_128_2_E_1_flipped_default_deleted_fragment_and_overlong_line_are_caught` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | A69 |
| AT-128-3-1 | 正控 | `test_evolution_propose_only.py::TestHumanGate::test_AT_128_3_1_cells_1_to_4_failure_messages_point_to_the_human_gate` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | B02、B08、B09 |
| AT-128-3-E-1 | 負控 | `test_evolution_propose_only.py::TestHumanGate::test_AT_128_3_E_1_message_check_is_not_vacuous_and_cell_5_is_exempt` | PASSED | rc=4（PG 守門）；加 `-n 0` 後 1 passed | B08 |

## §C 突變紀錄（194 個手工突變；QA 機器產生，主控併入；「存活」＝鑑別力缺口）

| ID | 目標 | 突變（在複本上改碼；真實樹零改動） | 結果 | 範圍 | 變紅的測試 |
|---|---|---|---|---|---|
| E1 | events | 事件 t 不再要求帶 offset（naive 放行） | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note |
| E2 | events | by 長度上限 32→33 | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note、test_AT_110_3_E_1_usage_and_state_errors |
| E3 | events | note 長度上限 120→121 | 存活（全綠） | 全套件 | — |
| E4 | events | prop 的 preimage／cls 對應判準移除 | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note |
| E5 | events | seq 接受布林（not bool 判準移除） | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note |
| C1 | evcheck | events.mutated 刪行（deleted）不再判 | 偵測（紅） | 全套件 | test_AT_108_4_E_1_append_only |
| C2 | evcheck | EVENT-SEQ 容許重複（<= 改 <） | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note |
| C3 | evcheck | 反空轉下限邊界（< 改 <=） | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note |
| C4 | evcheck | sources_sha256 對提交歷史的比對移除 | 偵測（紅） | 全套件 | test_AT_130_2_E_2_sources_sha_against_history |
| C5 | evcheck | RESEARCH-ORDER 判準移除 | 偵測（紅） | 全套件 | test_AT_130_1_1_research_event_required |
| C6 | evcheck | .md 雜湊比對移除 | 偵測（紅） | 全套件 | test_AT_142_1_E_1_prop_files_and_sources_table |
| F1 | fold | approve 不再要求 route=loop | 偵測（紅） | 全套件 | test_AT_108_4_1_transitions_replay |
| F2 | fold | SUSPENDED 的 all→any | 存活（全綠） | 全套件 | — |
| F3 | fold | CONFIRMER-IS-PROPOSER 判準移除 | 偵測（紅） | 全套件 | test_AT_106_1_E_1_confirm_rejections |
| F4 | fold | rev 連號判準放寬（== 改 >=） | 偵測（紅） | 全套件 | test_AT_108_4_1_transitions_replay |
| F5 | fold | 根因鍵更改次數方向反轉 | 偵測（紅） | 全套件 | test_AT_106_1_1_confirm_and_root_cause_changes |
| F6 | fold | run.close 重複關閉不再判非法 | 偵測（紅） | 全套件 | test_AT_108_4_1_transitions_replay |
| X1 | fetch | 重導向上限 5→6 | 偵測（紅） | 全套件 | test_AT_130_2_E_3_redirect_guard |
| X2 | fetch | check_redirect 不再拒 scheme 變更 | 存活（全綠） | 全套件 | — |
| X3 | fetch | Content-Length 邊界（> 改 >=） | 偵測（紅） | 全套件 | test_AT_130_3_E_1_failure_matrix、test_AT_130_5_1_budget_boundaries_pass |
| X4 | fetch | Accept-Encoding 不再是 identity | 偵測（紅） | 全套件 | test_AT_130_3_1_fetch_raw_bytes_and_changed |
| X5 | fetch | non-text 判準移除 | 偵測（紅） | 全套件 | test_AT_130_3_E_1_failure_matrix |
| X6 | fetch | Content-Encoding 判準移除 | 偵測（紅） | 全套件 | test_AT_130_3_E_1_failure_matrix |
| P1 | props | 觸及比例邊界（> 改 >=） | 偵測（紅） | 全套件 | test_AT_109_2_1_ratio_and_new_entries |
| P2 | props | 運轉預算邊界（>= 改 >） | 偵測（紅） | 全套件 | test_AT_110_1_1_budget_and_duplicates |
| P3 | props | NO-INTERNAL-SOURCE 判準移除 | 偵測（紅） | 全套件 | test_AT_130_4_E_1_researcher_chain_rejections |
| P4 | props | cls 自動標記（evaluator-change／loop-self）移除 | 偵測（紅） | 全套件 | test_AT_107_3_E_3_conditions_and_markers、test_AT_111_1_1_classes_and_group_marks、test_AT_111_1_E_1_evaluator_and_loop_self |
| P5 | props | 新增條目邊界（> 改 >=） | 偵測（紅） | 全套件 | test_AT_109_2_1_ratio_and_new_entries |
| P6 | props | 歸檔型上限邊界（> 改 >=） | 偵測（紅） | 全套件 | test_AT_109_2_E_1_archive_exemption |
| W1 | writeverbs | attr-confirm 確認者≠提出者判準移除 | 偵測（紅） | 全套件 | test_AT_106_1_E_1_confirm_rejections |
| W2 | writeverbs | run-close 一律記 no_event | 偵測（紅） | 全套件 | test_AT_103_2_1_run_close_records_no_event_or_outcomes、test_AT_141_1_1_event_line_shape |
| W3 | writeverbs | 修訂上限放寬一次 | 偵測（紅） | 全套件 | test_AT_108_2_E_1_revise_rejections |
| W4 | writeverbs | 追加失敗時不清孤兒內容檔 | 偵測（紅） | 全套件 | test_AT_144_1_E_1_digest_sensitivity_and_failures |
| W5 | writeverbs | RESEARCH-ALREADY 判準移除 | 偵測（紅） | 全套件 | test_AT_130_1_E_1_skip_reasons_and_rejections |
| W6 | writeverbs | 寫入動詞不取鎖（lock_path=None） | 偵測（紅） | 全套件 | test_AT_141_2_1_lock_serialises_writers、test_AT_141_2_E_1_lock_failure_modes |
| V1 | evwrite | LEDGER-TORN（末位元組非 LF）判準移除 | 偵測（紅） | 全套件 | test_AT_141_1_E_1_numbering_and_boundaries |
| V2 | evwrite | PAUSE_HOOK 不再被呼叫 | 偵測（紅） | 全套件 | test_AT_141_2_1_lock_serialises_writers |
| A1 | card | CJK 全形寬度改算 1 | 偵測（紅） | 全套件 | test_AT_114_3_E_1_layout_rejections |
| A2 | card | 核心區上限 12→13 | 偵測（紅） | 全套件 | test_AT_114_3_E_1_layout_rejections |
| A3 | card | 反解析比對移除（check 恆通過） | 偵測（紅） | 全套件 | test_AT_132_5_E_2_differential_and_isolation |
| B1 | paths | 保留裝置名判準移除 | 偵測（紅） | 全套件 | test_AT_107_3_E_2_alias_forms_and_numstat_superset |
| B2 | paths | glob 比對不再 casefold | 偵測（紅） | 全套件 | test_AT_107_3_E_1_non_evolvable_paths_hand_off、test_AT_107_3_E_3_conditions_and_markers、test_AT_108_3_E_1_rule_candidate_rejected_or_handed_off |
| B3 | paths | touched 不含改名來源端 | 存活（全綠） | 全套件 | — |
| S1 | sources | 私網 172.16/12 段移除 | 偵測（紅） | 全套件 | test_AT_130_2_E_1_table_codes_and_preflight |
| S2 | sources | userinfo 判準移除 | 偵測（紅） | 全套件 | test_AT_130_2_E_1_table_codes_and_preflight |
| K1 | keyB | plugins/ 內新增 apply_evolution 呼叫點 | 偵測（紅） | 全套件 | test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites |
| K2 | keyB | plugins/ 內新增 evolved_playbook_path= keyword（演化重載生產者） | 偵測（紅） | 全套件 | test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites |
| K3 | keyB | require_evolution_signoff 預設 False→True | 偵測（紅） | 全套件 | test_AT_128_2_1_default_still_false_and_doc_rewritten_within_line_budget |
| K4 | keyB | plugins/ 內新增 require_evolution_signoff 讀取點 | 偵測（紅） | 全套件 | test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites |
| K5 | keyB | main.py 的 W6 拔除字樣被改掉 | 偵測（紅） | 全套件 | test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites |
| K6 | keyB | CLAUDE.md 演化敘述的『無演化重載生產者』被刪 | 偵測（紅） | 全套件 | test_AT_128_2_1_default_still_false_and_doc_rewritten_within_line_budget |
| K7 | keyB | CLAUDE.md 重新引用 main.py:277 行號 | 偵測（紅） | 全套件 | test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites |
| K8 | keyB | execution/ 內多一個 apply_evolution 呼叫（清單外外層函式） | 偵測（紅） | 全套件 | test_AT_128_1_1_real_tree_five_cells_green_and_scanners_see_production_sites |
| E6 | events | research.scan 的 http_status 上限 299→399 | 存活（全綠） | 全套件 | — |
| E7 | events | research.skip 的 by 恆為 main 判準移除 | 存活（全綠） | 全套件 | — |
| E8 | events | 讀取側不再剝 BOM | 偵測（紅） | 全套件 | test_AT_108_4_E_2_structure_floor_and_dec_note |
| E9 | events | sid 不再要求 UUID 正規形 | 存活（全綠） | 全套件 | — |
| C7 | evcheck | dec 引言回查提示改為『多於 1 筆 dec 才印』 | 存活（全綠） | 全套件 | — |
| C8 | evcheck | RESEARCH-MULTIPLE 門檻 >1 改 >2 | 偵測（紅） | 全套件 | test_AT_130_1_1_research_event_required |
| C9 | evcheck | 事件行位元組邊界（> 改 >=） | 存活（全綠） | 全套件 | — |
| C10 | evcheck | 不再比對工作樹相對 HEAD 的未提交改寫（WORKTREE 版） | 偵測（紅） | 全套件 | test_AT_108_4_E_1_append_only |
| C11 | evcheck | SRC-UNKNOWN（事件的來源 id 不在表）判準移除 | 偵測（紅） | 全套件 | test_AT_130_2_E_2_sources_sha_against_history |
| C12 | evcheck | git 歷史比對邊界（<= 改 <） | 存活（全綠） | 全套件 | — |
| F7 | fold | NE verdict 不需 unverified_ack 即可 promote | 偵測（紅） | 全套件 | test_AT_108_4_1_transitions_replay |
| F8 | fold | unblock 不再解除冷卻 | 偵測（紅） | 全套件 | test_AT_103_1_E_1_status_edges |
| F9 | fold | mea.amend 不再覆寫窗結果 | 偵測（紅） | 全套件 | test_AT_103_1_E_1_status_edges |
| F10 | fold | prop 事件不再檢查運轉是否 open | 偵測（紅） | 全套件 | test_AT_108_4_1_transitions_replay |
| F11 | fold | resume 事件不再解除 SUSPENDED | 偵測（紅） | 全套件 | test_AT_103_1_E_1_status_edges |
| F12 | fold | PROP 目前 rev 的 returned 前置條件移除（任何狀態皆可修訂） | 偵測（紅） | 全套件 | test_AT_108_4_1_transitions_replay |
| X7 | fetch | 逾時一律歸類為 network | 偵測（紅） | 全套件 | test_AT_130_3_E_1_failure_matrix、test_AT_130_5_E_1_budget_overruns |
| X8 | fetch | 每跳不再呼叫 check_redirect（只留跳數上限） | 偵測（紅） | 全套件 | test_AT_130_2_E_3_redirect_guard |
| X9 | fetch | User-Agent 改值 | 偵測（紅） | 全套件 | test_AT_130_3_1_fetch_raw_bytes_and_changed |
| X10 | fetch | 移除 application/xml 為合法文字型別 | 存活（全綠） | 全套件 | — |
| X11 | fetch | 逾時判斷取消（deadline 不再於讀本文時檢查） | 存活（全綠） | 全套件 | — |
| P7 | props | M 類 source_obs 不再須屬 --source | 偵測（紅） | 全套件 | test_AT_109_3_E_1_m_field_rejections |
| P8 | props | 同型判定不再把『根因鍵皆空』算同型 | 偵測（紅） | 全套件 | test_AT_110_1_1_budget_and_duplicates |
| P9 | props | SUSPENDED 前置檢查移除 | 偵測（紅） | 全套件 | test_AT_110_1_E_1_state_rejections |
| P10 | props | result_label 值域判準移除 | 偵測（紅） | 全套件 | test_AT_109_1_E_1_body_rejections、test_AT_109_3_E_1_m_field_rejections |
| P11 | props | REVIEWER-IS-PROPOSER 判準移除 | 偵測（紅） | 全套件 | test_AT_108_1_E_1_stage_one_inputs |
| W7 | writeverbs | run-open 不再驗 --by 標籤 | 偵測（紅） | 全套件 | test_AT_110_3_E_1_usage_and_state_errors |
| W8 | writeverbs | research --skip 的 band 允許 free | 偵測（紅） | 全套件 | test_AT_130_1_E_1_skip_reasons_and_rejections |
| W9 | writeverbs | attr link 不再驗 reopens 為已結列 | 偵測（紅） | 全套件 | test_AT_106_2_E_1_link_rejections |
| W10 | writeverbs | 取鎖逾時不再轉為拒收 | 偵測（紅） | 全套件 | test_AT_141_2_E_1_lock_failure_modes |
| W11 | writeverbs | 草稿列最多顯示碼數 5→6 | 存活（全綠） | 全套件 | — |
| S3 | status | (d) 事件偵測（已採納提案的復發）移除 | 偵測（紅） | 全套件 | test_AT_103_1_1_status_summary |
| S4 | status | no_event 恆為 true | 偵測（紅） | 全套件 | test_AT_103_1_1_status_summary |
| S5 | status | pending_props 不含 verified | 存活（全綠） | 全套件 | — |
| S6 | status | 事件偵測窗不再以最近 run.close 為界 | 存活（全綠） | 全套件 | — |
| N1 | scan | bucket_of 不再認 tools/selfimproving.py | 偵測（紅） | 全套件 | test_AT_131_4_1_bucket_order |
| N2 | scan | 缺陷候選只收 P1（漏 P2） | 偵測（紅） | 全套件 | test_AT_103_1_1_status_summary、test_AT_131_2_1_candidate_rows |
| N3 | scan | 缺陷發現日期邊界（同日者不納入） | 偵測（紅） | 全套件 | test_AT_103_1_1_status_summary、test_AT_131_2_1_candidate_rows |
| N4 | scan | commit 時間邊界（> 改 >=） | 存活（全綠） | 全套件 | — |
| Q1 | export | 游標嚴格大於改為大於等於 | 偵測（紅） | 全套件 | test_AT_132_5_E_1_usage_pages_and_carriers |
| Q2 | export | truncated 邊界（> 改 >=） | 存活（全綠） | 全套件 | — |
| Q3 | export | next_since 恆為 null | 偵測（紅） | 全套件 | test_AT_132_5_E_1_usage_pages_and_carriers |
| R1 | refs | 復發候選不再排除已有 reopens 標記的新列 | 偵測（紅） | 全套件 | test_AT_106_2_E_2_reopen_candidate_hint |
| R3 | refs | OBS 已結處置不再含 decided | 偵測（紅） | 全套件 | test_AT_106_2_1_link_and_settle、test_AT_106_2_E_2_reopen_candidate_hint |
| K9 | check | SOURCES-HISTORY-NOT-ESTABLISHED 不再屬 nonblocking | 偵測（紅） | 全套件 | test_AT_130_2_E_2_sources_sha_against_history |
| B4 | paths | 別名形態『含冒號』判準移除 | 偵測（紅） | 全套件 | test_AT_107_3_E_2_alias_forms_and_numstat_superset |
| B5 | paths | normalize 不再 casefold | 存活（全綠） | 全套件 | — |
| S7 | sources | IPv4 映射位址（::ffff:127.0.0.1）不再被視為私網 | 偵測（紅） | 全套件 | test_AT_130_2_E_1_table_codes_and_preflight |
| S8 | sources | SRC-ORDER 判準移除 | 偵測（紅） | 全套件 | test_AT_130_2_E_1_table_codes_and_preflight |
| D2 | defs | DEF 狀態關鍵字：wontfix 從分類移除 | 偵測（紅） | 全套件 | test_AT_131_2_E_2_defs_differential |
| RW1 | rows | R44(a)：研究者列不再要求 外部衍生／src | 偵測（紅） | 全套件 | test_AT_130_4_E_1_researcher_chain_rejections、test_AT_142_1_E_2_researcher_rows |
| RW2 | rows | R44(b)：列的 src 不在來源表不再判 SRC-UNKNOWN | 偵測（紅） | 全套件 | test_AT_142_1_E_2_researcher_rows |
| PM1 | params | 指紋不再排除 research_sources.json | 偵測（紅） | 全套件 | test_AT_130_6_1_sources_excluded_from_fingerprint |
| PM2 | params | CHECK_RULES_REV 2→1 | 偵測（紅） | 全套件 | test_AT_142_1_1_p1_items_on_p0_baseline_and_after_a_round |
| PM3 | params | PARAM_SPECS：min_events 型別規則改成 sha（接受 null／字串） | 偵測（紅） | 全套件 | test_AT_001_1_1_baseline_is_green、test_AT_001_1_E_6_fixed_sha、test_AT_001_3_1_chain_is_exempt |
| V3 | evwrite | 寫入側位元組邊界（> 改 >=） | 偵測（紅） | 全套件 | test_AT_141_1_E_1_numbering_and_boundaries |
| V4 | evwrite | 鎖檔名雜湊取 16→12 位 | 存活（全綠） | 全套件 | — |
| V5 | evwrite | 家目錄可寫性探測移除 | 存活（全綠） | 全套件 | — |
| A4 | card | 卡面 digest 顯示 8→7 碼 | 偵測（紅） | 全套件 | test_AT_107_1_1_guard_surface_is_handed_off_whole、test_AT_109_1_1_body_shapes_accepted、test_AT_109_2_1_ratio_and_new_entries |
| A01 | writeverbs.py | ok JSON 鍵序 seq／id 對調 | 偵測（紅） | AT 靶向 | test_AT_110_3_1_run_open_five_triggers |
| A02 | writeverbs.py | run-close 不再拒絕已關運轉 | 偵測（紅） | AT 靶向 | test_AT_103_2_E_1_run_close_rejections |
| A03 | events.py | 歸因種類集合缺 MEMORY_ENTRY | 偵測（紅） | AT 靶向 | test_AT_105_1_1_attr_seven_kinds |
| A04 | writeverbs.py | NONE 不再要求『無法歸因』起頭 | 偵測（紅） | AT 靶向 | test_AT_105_1_E_1_attr_rejections |
| A05 | writeverbs.py | attr 事件夾帶 confidence 鍵 | 偵測（紅） | AT 靶向 | test_AT_105_2_1_attr_only_touches_event_ledger |
| A06 | events.py | attr 欄位表接受 confidence 表外鍵 | 偵測（紅） | AT 靶向 | test_AT_105_2_E_1_no_self_assessment |
| A07 | writeverbs.py | 外部衍生列也算內部來源 | 偵測（紅） | AT 靶向 | test_AT_102_1_E_1_external_only_and_unresolved |
| A08 | writeverbs.py | DEF 來源不再可解析 | 偵測（紅） | AT 靶向 | test_AT_102_1_1_internal_source_suffices |
| A09 | props.py | 導出為 loop 而給 --handoff 不再拒收 | 偵測（紅） | AT 靶向 | test_AT_107_1_E_1_route_and_channel_rules |
| A10 | paths.py | patch 路徑不再剝 a/ b/ 前綴 | 偵測（紅） | AT 靶向 | test_AT_107_3_1_touched_derivation |
| A11 | fold.py | 新 PROP 初始狀態不是 proposed | 偵測（紅） | AT 靶向 | test_AT_108_1_1_prop_new_registers_proposed |
| A12 | writeverbs.py | prop-revise 的新 rev 加 2 | 偵測（紅） | AT 靶向 | test_AT_108_2_1_revise_returned |
| A13 | props.py | trust_level: proposed 判準改錯 | 偵測（紅） | AT 靶向 | test_AT_108_3_1_rule_candidate_accepted |
| A14 | props.py | M 類四欄多一個必備欄 | 偵測（紅） | AT 靶向 | test_AT_109_3_1_m_fields_and_preimage |
| A15 | card.py | 卡面預算宣告被截斷 | 偵測（紅） | AT 靶向 | test_AT_110_2_1_budget_declared_on_card |
| A16 | props.py | budget 不再是必備欄 | 偵測（紅） | AT 靶向 | test_AT_110_2_E_1_budget_required |
| A17 | card.py | 卡面 +added／-removed 對調 | 偵測（紅） | AT 靶向 | test_AT_114_1_1_card_format |
| A18 | card.py | 卡面不再列出 target 外的路徑 | 偵測（紅） | 全套件 | test_AT_114_3_1_layout_boundaries_accepted、test_AT_114_3_E_1_layout_rejections |
| A19 | card.py | 反解析 digest 前 8 碼改 7 碼 | 偵測（紅） | AT 靶向 | test_AT_114_2_1_parsed_matches_recomputed |
| A20 | card.py | 反解析一致性比對移除（check 恆通過） | 偵測（紅） | AT 靶向 | test_AT_114_2_E_1_tampered_card_refused |
| A21 | card.py | 核心區上限 12→11 | 偵測（紅） | AT 靶向 | test_AT_114_3_1_layout_boundaries_accepted |
| A22 | props.py | digest 核心不含 base | 偵測（紅） | AT 靶向 | test_AT_144_1_1_files_and_digest |
| A23 | sources.py | sources_sha256 不再先換 LF | 偵測（紅） | 全套件 | test_AT_130_2_E_1_table_codes_and_preflight |
| A24 | research.py | 零成功的拒收碼被改名 | 存活（全綠） | 全套件 | — |
| A25 | research.py | 鎖內重驗不再查 RESEARCH-ALREADY | 偵測（紅） | AT 靶向 | test_AT_130_3_E_3_fetch_outside_lock |
| A26 | rows.py | 研究者列一律判 NO-SRC | 偵測（紅） | AT 靶向 | test_AT_130_4_1_researcher_candidate_accepted |
| A27 | params.py | 指紋額外排除 metrics.md | 偵測（紅） | AT 靶向 | test_AT_130_6_E_1_other_protocol_files_change_fingerprint |
| A28 | selfimproving.py | scan 多出 --limit 旗標 | 偵測（紅） | AT 靶向 | test_AT_131_1_1_scan_is_pure、test_AT_131_1_E_1_scan_flags |
| A29 | scan.py | 缺陷候選把 fixed 也算 open | 偵測（紅） | 全套件 | test_AT_131_2_1_candidate_rows、test_AT_131_3_1_zero_candidates、test_AT_131_3_E_1_unavailable_sources |
| A30 | scan.py | 零候選印成『通過』 | 偵測（紅） | AT 靶向 | test_AT_131_3_1_zero_candidates |
| A31 | scan.py | 量不到的來源不再併入無事件字樣 | 偵測（紅） | AT 靶向 | test_AT_131_3_E_1_unavailable_sources |
| A32 | scan.py | bucket_of 不再把含 .. 的路徑歸未分類 | 偵測（紅） | AT 靶向 | test_AT_131_4_E_1_bucket_edges |
| A33 | export.py | export 輸出 ensure_ascii=True | 存活（全綠） | 全套件 | — |
| A34 | export.py | runs 匯出不含 outcome | 偵測（紅） | 全套件 | test_AT_132_5_1_five_kinds |
| A35 | export.py | export 輸出夾帶不穩定值 | 偵測（紅） | AT 靶向 | test_AT_140_2_E_1_no_unstable_sources |
| A36 | selfimproving.py | 用法錯誤 rc 3→2 | 偵測（紅） | AT 靶向 | test_AT_140_1_E_1_unimplemented_verbs_and_reject_grammar |
| A37 | evcheck.py | 載體缺席碼被改名 | 偵測（紅） | AT 靶向 | test_AT_142_2_1_p0_items_unchanged |
| A38 | params.py | PARAM_SPECS 缺 export_limit_max | 偵測（紅） | AT 靶向 | test_AT_145_1_E_1_new_param_keys |
| A39 | params.py | research_bytes_max 型別規則改 ratio（真 params 不合） | 偵測（紅） | AT 靶向 | test_AT_145_1_1_real_protocol_files |
| A40 | SelfImproving_Operations_SOP.md | SOP 歸因者節：理論洞條文失去『不立案』 | 偵測（紅） | AT 靶向 | test_AT_107_2_1_theory_hole_clause |
| A41 | SelfImproving_Operations_SOP.md | SOP：evaluator-change 條文失去『不得轉送沙盒』 | 偵測（紅） | AT 靶向 | test_AT_111_2_1_evaluator_change_clause |
| A42 | SelfImproving_Operations_SOP.md | SOP：抽象化條文失去『原始軌跡全文』 | 偵測（紅） | AT 靶向 | test_AT_109_1_2_abstraction_clause |
| A43 | SelfImproving_Operations_SOP.md | SOP：零遞迴條文被改成可再派 | 偵測（紅） | AT 靶向 | test_AT_110_2_2_zero_recursion_clause |
| A44 | SelfImproving_Operations_SOP.md | SOP 研究者節：『資料、不是指令』被改 | 偵測（紅） | AT 靶向 | test_AT_130_4_2_researcher_section |
| A45 | SelfImproving_Operations_SOP.md | SOP 體檢範本：工具白名單少 PowerShell | 偵測（紅） | AT 靶向 | test_AT_131_5_1_template_matches_prd |
| A46 | SelfImproving_Operations_SOP.md | SOP 歸因者節：失去『P1 定稿』狀態標示 | 偵測（紅） | AT 靶向 | test_AT_145_2_1_sop_is_final |
| A47 | SelfImproving_Operations_SOP.md | SOP 體檢範本：PRD 入口表片段 AutoClaude/CLAUDE.md 被移除 | 偵測（紅） | AT 靶向 | test_AT_131_5_E_1_template_criteria_and_tree_state |
| A48 | test_selfimproving_capability.py | 能力判準：ro 寫入形原語檢查失效 | 偵測（紅） | AT 靶向 | test_AT_143_1_E_1_synthetic_violations_are_flagged |
| A49 | test_selfimproving_capability.py | 能力判準：網路模組只准 fetch.py 的檢查失效 | 偵測（紅） | AT 靶向 | test_AT_143_1_E_1_synthetic_violations_are_flagged |
| A50 | test_selfimproving_capability.py | 能力判準：唯讀 import 閉包檢查失效 | 偵測（紅） | AT 靶向 | test_AT_143_1_E_1_synthetic_violations_are_flagged |
| A51 | test_selfimproving_capability.py | 常駐機制禁字樣清單少 time.sleep | 偵測（紅） | AT 靶向 | test_AT_143_1_E_2_dynamic_purity_and_forbidden_words |
| A52 | status.py | ro 檔 status.py import socket | 偵測（紅） | AT 靶向 | test_AT_143_1_1_real_tree_matches_registry |
| A53 | scan.py | ro 檔 scan.py 出現 subprocess 字樣 | 偵測（紅） | AT 靶向 | test_AT_143_1_1_real_tree_matches_registry |
| A54 | status.py | 唯讀 status.py 經 import 閉包牽入 evwrite（rw） | 偵測（紅） | AT 靶向 | test_AT_143_1_1_real_tree_matches_registry |
| A55 | status.py | 套件內出現 time.sleep 字樣 | 偵測（紅） | AT 靶向 | test_AT_143_1_E_2_dynamic_purity_and_forbidden_words |
| A56 | test_root_module_layout.py | 落點鎖：缺路徑不再被報 | 偵測（紅） | AT 靶向 | test_AT_134_1_E_1_missing_paths_are_red |
| A57 | test_root_module_layout.py | 落點鎖：同前綴門檻 3→4 | 偵測（紅） | AT 靶向 | test_AT_134_2_E_1_red_shapes |
| A58 | test_root_module_layout.py | 落點鎖：套件未登記不再被報 | 偵測（紅） | AT 靶向 | test_AT_134_3_E_1_unregistered_package_red |
| A59 | test_root_module_layout.py | 落點鎖：PRD 未引 SSOT 不再被報 | 偵測（紅） | AT 靶向 | test_AT_134_4_E_1_missing_citation_red |
| B01 | test_evolution_propose_only.py | 鍵 B 格①：缺鎖函式不再被報 | 偵測（紅） | AT 靶向 | test_AT_128_1_E_1_missing_lock_and_stray_apply_sites_turn_cells_1_and_2_red |
| B02 | test_evolution_propose_only.py | 鍵 B 格②：清單外呼叫點不再被報 | 偵測（紅） | 全套件 | test_AT_128_1_E_1_missing_lock_and_stray_apply_sites_turn_cells_1_and_2_red、test_AT_128_3_1_cells_1_to_4_failure_messages_point_to_the_human_gate |
| B03 | test_evolution_propose_only.py | 鍵 B 格③：生產者判準失效 | 偵測（紅） | AT 靶向 | test_AT_128_1_E_2_injected_producers_turn_cell_3_red_excluded_files_do_not |
| B04 | test_evolution_propose_only.py | 鍵 B 格④：signoff 讀取點判準失效 | 偵測（紅） | AT 靶向 | test_AT_128_1_E_3_extra_signoff_read_turns_cell_4_red_store_context_does_not |
| B05 | test_evolution_propose_only.py | 鍵 B 格④：Store 語境也被算讀取 | 偵測（紅） | AT 靶向 | test_AT_128_1_E_3_extra_signoff_read_turns_cell_4_red_store_context_does_not |
| B06 | test_evolution_propose_only.py | 鍵 B 格⑤：main.py 字樣檢查失效 | 偵測（紅） | AT 靶向 | test_AT_128_1_E_4_doc_pin_rejects_missing_phrase_line_numbers_and_stale_main |
| B07 | test_evolution_propose_only.py | 鍵 B 格⑤：行號形態只擋半形冒號 | 偵測（紅） | AT 靶向 | test_AT_128_1_E_4_doc_pin_rejects_missing_phrase_line_numbers_and_stale_main |
| B08 | test_evolution_propose_only.py | 鍵 B AC-SI-28-3：升級訊息不再含 FR-SI-12 | 偵測（紅） | AT 靶向 | test_AT_128_3_1_cells_1_to_4_failure_messages_point_to_the_human_gate |
| B09 | test_evolution_propose_only.py | 鍵 B AC-SI-28-3：升級訊息不再含 OBS-SI-010 | 偵測（紅） | AT 靶向 | test_AT_128_3_1_cells_1_to_4_failure_messages_point_to_the_human_gate |
| B10 | test_evolution_propose_only.py | 鍵 B AC-SI-28-2：改述片段清單少一個 | 存活（全綠） | 全套件 | — |
| A18b | card.py | 卡面查無 PROP 碼被改名（AT-114-1-E-1 的另一面） | 存活（全綠） | 全套件 | — |
| A18c | card.py | 卡面查無 PROP 的碼被改名為 PROP-MISSING | 偵測（紅） | 全套件 | test_AT_114_1_E_1_card_ignores_free_text |
| A60 | fetch.py | check_redirect 一律拒絕（表內 host 的重導向也被擋） | 偵測（紅） | AT 靶向 | test_AT_130_2_1_compliant_committed_table_passes_preflight |
| A61 | scan.py | 缺陷帳本表頭不全不再判量不到 | 偵測（紅） | AT 靶向 | test_AT_131_2_E_1_row_cap_and_header |
| A62 | rows.py | P0 嚴重度集合多收 P0 | 偵測（紅） | AT 靶向 | test_AT_142_2_E_1_p0_negatives_unchanged |
| A63 | _selfimproving_fixtures.py | SOP 判準：理論洞同行群組不再要求『不立案』 | 存活（全綠） | AT 靶向 | — |
| A64 | _selfimproving_fixtures.py | SOP 判準：evaluator-change 同行群組不再要求『不得轉送沙盒』 | 存活（全綠） | AT 靶向 | — |
| A65 | _selfimproving_fixtures.py | SOP 判準：不再要求節內『P1 定稿』 | 偵測（紅） | AT 靶向 | test_AT_145_2_E_1_criteria_are_not_vacuous |
| A66 | selfimproving.py | status 動詞的處理器被拿掉 | 偵測（紅） | AT 靶向 | test_AT_140_1_1_thirteen_verbs |
| A67 | status.py | status 鍵序 suspended／cooldowns 對調 | 偵測（紅） | AT 靶向 | test_AT_140_2_1_outputs_are_stable |
| A68 | research.py | research --json 鍵序 run／rc 對調 | 偵測（紅） | AT 靶向 | test_AT_130_3_E_2_zero_success_and_json_shape |
| A69 | test_evolution_propose_only.py | 鍵 B：預設值零退化判準失效 | 偵測（紅） | AT 靶向 | test_AT_128_2_E_1_flipped_default_deleted_fragment_and_overlong_line_are_caught |
| A70 | _selfimproving_fixtures.py | SOP 判準：line_has_all 不再比對片段 | 偵測（紅） | AT 靶向 | test_AT_107_2_E_1_theory_hole_criteria、test_AT_111_2_E_1_evaluator_change_criteria |
