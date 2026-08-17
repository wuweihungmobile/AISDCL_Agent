# CrossPlatform R95 — 護欄層行數棘輪重釘證據檔（收尾單人窗口）

> 本檔兩個角色：① R95 重釘（`_GUARD_LINES_REPIN_LOG` R95 列）的量測與處置帳；
> ② R89 體例的**史料搬遷目的地**——`tools/tests/test_adr_xplat001_c1c2_lock.py` 等
> 鎖檔為壓低護欄層淨額而外移的立案敘事原文，逐字收在 §B（各搬出點留有指回本節的
> 座標；判準與判準的理由一行都沒搬）。
> 先例體例＝CrossPlatform_R86_Guard_Repin_Evidence.md／CrossPlatform_R90_Guard_Repin_Evidence.md。
> 章節依批次追加、序號非單調（各批落款時間序，不重排——重排會改寫既有搬遷點指回的座標）。

## §A R95 重釘帳（收尾窗口實測）

- 動因：R95 三個並行包（Pkg-B／C／D）合計 +454（`test_quota_policy.py` +154、
  `test_context_budget_guard.py` +164、`test_block_destructive_git_r83.py` +136；
  任務書寫 +468 係以 +168 高估 quota 檔，實測 `--print-guard-lines` 為 +154）。
- 硬約束：R93（+225）／R94（+39）已連升 2/2 ⇒ 款(11) 要求 **R95 淨額 ≤ 0**。
- 處置：照棘輪自列的出口「把史料搬進帳本」執行——只搬「哪一輪發生過什麼／實測數字
  多少」的史料段，判準與判準理由零搬動；每檔搬遷後立即重跑該測試模組（逐字 rc 見
  收尾交件回報）。
- 最終淨額與逐檔清單：見 `_GUARD_LINES_REPIN_LOG` R95 列與本檔 §C（收尾窗口完工時回填）。

## §B 史料搬遷（自 `test_adr_xplat001_c1c2_lock.py` 逐字外移；原文一字不動）

### B-1 `_GUARD_LINES_REPIN_LOG` 檔頭：R78 ARCH-01 缺陷本體

> 🔴 R78 ARCH-01 的落地物。缺陷本體：舊的檔數棘輪重釘是**一個**數字，一望即知方向；
> 換成逐檔行數表之後，重釘變成「整張表同時變」，而**淨額不出現在任何地方**——
> 實測 `a7a3080` 這一個 commit 內量測面 54188 → 57693（+3505），閘門全程 rc=0。
> 也就是說「重釘」在機械上與「順手更新一下」無法區分，棘輪的張力全靠人自律。

### B-2 `_FROZEN_GUARD_LINES` 檔頭：為何檔數棘輪退場、行數表接手

> 🔴 為何檔數棘輪要退場、而這張表是它的接手者：檔數被釘住之後，護欄層的成長並沒有停，
> 只是全部灌進既有巨檔——同期行數翻倍而唯一的通過判準（檔數相等＋glob 非空）全程綠。
> 「只准變少」預設了「變多是安全的」，而那個預設在這一層被實測推翻。行數面把成長本身
> 變成會轉紅的事件，方向仍是收緊（成長側零容忍，見 `glc_growth_problem`）。

### B-3 R84 ARCH-01：重釘的「代價」立案量測

> 🔴 **R84 ARCH-01：重釘的「代價」**（本表歷來只有「補一列紀錄＋寫理由」這道成本≈零的
> 手續）。立案量測：`_GUARD_LINES_REPIN_LOG` **每一列都是上升、零列下降**，R77→R83 共
> +24,895（+46%）；逐輪淨額現查 `repin_round_nets()`，不寫死列數。檔頭與
> `AutoClaude/tools/check_loc_budget.py` 的註解都逐字寫著
> 「淨行數只准往下」，而那句話對這張表從未成立過。⇒ 它名義上是棘輪，實際是一本成長帳，
> 成熟度 M1（「總量連續三輪不上升」）**照現行機制永遠做不到**。

### B-4 R84 F3／B-1：`_REPIN_ROUND_CAP_SINCE` 原本無鎖的立案量測

> 🔴 **R84 F3／B-1：起算錨也是門檻，而它原本是本組唯一沒有後設鎖的那一個**。
> 立案量測（當回合注入實測）：把 `_REPIN_ROUND_CAP_SINCE` 由 84 改成 99、其餘一字不動，
> `-k "cost_envelope or rising or net_cap or tightened"` 回 **rc=0／4 passed**；同一份合成
> 「R84~R87 四輪連升」語料
> 在 `since=88` 下 `repin_growth_problems()` 回 `[]`（現行 84 回
> `[只升不降]`）⇒ **一行 diff 就能把款(10)(11) 整段關掉，而且沒有任何東西會轉紅**。
> 兩個門檻常數守得再嚴都沒有意義——把生效點推到未來，等於把判準的分母清空。

### B-5 R85／款(12) 兌現時發現的結構性死結

> 🔴 **R85／款(12) 兌現時發現的結構性死結，以及它的解**（本段取代前一輪把上限寫成
> 單一純量的那個形狀）。R84 訂下的到期目標 3200 依據的是它自己寫下的逐輪淨額表，其中
> R84＝2655；但**同一輪稍後的第二次重釘**（+1100）已讓 R84 的真實合計變成 3755
> ⇒ 到期目標訂完就過期了。照字面把純量上限下修到 3200 的當回合實測：款(10) 會回頭把
> **R84 判紅**（3755 > 3200），而那一列受款(7) 的 append-only 指紋保護、沒有任何人補得
> 回來 ⇒ 款(10)（要求 ≥3755）與款(12)（要求 ≤3200）互相排斥，唯一出路變成放寬其中一個。

### B-6 `repin_log_problems` 款(6)(7) 的 R79 立案

> 🔴 **(6)(7) 是 R79 收斂包補的，它們治的是這張表自己的假話**：檔頭逐字寫著
> 「**append-only**」，而 R79 掃描實測 append-only **零機械強制**——把 R77＋R78 兩列
> 壓成一列、把起點的舊總量從 54188 改成任意數字（實測 90000），(1)~(5) 全部沉默、
> `rc=0`。而本表存在的唯一理由是「讓淨額在結構上不可能缺席」，壓平歷史比不補一列
> 更難看見（表上永遠都有一列）。**合併歷史與追加新列在機械上原本無法區分**——那正是
> R78 ARCH-01 對「重釘 vs 順手更新一下」下過的同一句判詞，只是這次長在防它的機制上。

### B-7 `repin_cost_ratchet_problems` 的 F3／B-1 與 A-03 立案

> 🔴 **R84 F3／B-1：`_REPIN_ROUND_CAP_SINCE` 是本組原本唯一沒被守的常數，而它的
> 威力最大**——另外兩個調的是門檻高低，它調的是**分母**：把生效輪次推到未來，款(10)(11)
> 就沒有任何一列可判。注入實測（當回合）：副本的 `SINCE` 由 84 改成 99 之後
> `-k "cost_envelope or rising or net_cap or tightened"` 仍 **rc=0／4 passed**；
> `repin_growth_problems(<R84~R87 四輪連升>, since=88)` 回 `[]`。
> ⇒ 「一行 diff 關掉整段判準且無一物轉紅」正是 ARCH-01 在治的那個病，只是這次長在
> 防它的機制上（同款(6)(7) 對稽核痕跡自己的假話所下的判詞）。
>
> 🔴 **R84 F3／A-03：款(12) `[到期未下修]` 也住這裡**——它判的是「`net_cap` 這把尺自己
> 該不該被下修了」，而不是某一張表的內容，所以家在後設鎖而不是 `repin_growth_problems()`
> （放在那邊會讓每一份輪號較大的合成語料一起鳴叫＝串音；R99 追加對照組實測轉紅）。

### B-8 `doc_guard_total_problems` 的 R80 二審立案與 ZT-04 訂正

> 🔴 **立案（R80 二審 NEW-SA2-01＝QA2-N2，實測三處全錯）**：款(4) 只守稽核痕跡那一條
> 線，而讀者實際會引用的數字住在計畫書與掃描發現文件裡。二審實查：兩處只記了第一次
> 重釘、漏掉第二次；第三處把兩次相加寫成一個既不等於總量、也不等於兩者之和的數。
> 三個站點沒有一個會轉紅，因為在此之前**沒有任何判準看得到 `.md`**。
>
> 🔴 **R84 F3／B-2：ZT-04 那次「擴面」對它自己立案的缺陷零效果，而擴完之後
> 看起來像修好了**（本 repo 判過：有鎖在守假話，比沒有鎖更難看見）。實測兩件事——
>   ① 帶標記的站點**無一例外**都落在舊的兩個 glob 內，新掃描面一處都沒有 ⇒
>      Architect 注入「把 `R84_HANDOFF.md` 的護欄層三元組改成全錯值」，
>      `doc_guard_total_problems()` 回 `[]`。擴面擴到的是「檔案被讀進來了」，
>      不是「有東西被判到」。
>   ② `docs/04_planning/ADR/*.md` 這一面**結構上永遠咬不到**：`ADR-XPLAT-006` 已裁定
>      不得給 ADR 補標記（原話：那會是「誘餌標記」），而該檔內僅有的三組三元組
>      （ln 521／543／673，實查）是它**刻意寫壞、用來示範注入**的合成語料 ⇒ 任何
>      不靠標記的三元組判準一掃到它就是永久假紅。

### B-9 `handoff_guard_total_problems` 的立案與假紅存量實測

> 🔴 **立案（R84 F3／B-2，Architect 當回合注入實測）**：ZT-04 把掃描面擴到交棒書與
> ADR，但**帶標記的站點全數落在舊的兩個 glob 內** ⇒ 新面一處都沒判到；把
> `R84_HANDOFF.md` 的三元組改成全錯值，`doc_guard_total_problems()` 回 `[]`。
> 而該檔逐字寫著 `79083 → 81738（+2655）`、**零標記**——它是呈給掌舵者的那個數字，
> 卻是全庫唯一一個「寫在活文件上、沒有任何東西看得到」的護欄層宣稱。
>
> 假紅存量（落地當回合對 `R*_HANDOFF.md` **逐份**實測）：R74/R75/R76 無稽核列⇒跳過；
> R77~R82 的三元組數**皆為零**（生效點 `since=83` 之外，且本來就沒寫過這個數字）；
> R83 命中 `(73823, 79083, 5260)`＝該輪合計 ✅；R84 命中 `(79083, 81738, 2655)` ✅。
> ⇒ **假紅存量為空**，同輪不需要修任何一份文件。

### B-10 `--print-guard-lines` 旗標的 R78 ARCH-02 立案

> 🔴 R78 ARCH-02：這個旗標在 R77 只存在於紅燈訊息裡，實跑 rc=2 `unrecognized arguments`；
> 本輪補上 `__main__` 分派，並由 `TestRepinCommandIsReal` 雙向釘住「訊息教的指令必須真的
> 跑得動」——否則棘輪一紅，唯一出路是逐列手改整張凍結表，而那樣改的人不會順手算淨額。

### B-11 SA-R67-08 凍結基準的病灶實證

> 病灶（SA 沙箱實證，非推論）：舊實作以 `git show HEAD:<本檔>` 取上一版。未 commit 時它確實
> 有牙（改大即紅），但**每一個真正消費本鎖 rc 的閘門都跑在 commit 之後**——`tools/git-hooks/
> pre-push` 的 root-infra leg 走 `run_root_unittests.py`，而 push 必然發生在 commit 之後；CI
> 更是乾淨 checkout。commit 一落地，HEAD 就等於工作樹 ⇒ previous == current ⇒ 恆真。SA 實測
> 把 `_MAX_BASELINE_ENTRIES` 放大十餘倍後 commit，本類全綠、鎖檔內容與門檻的對照零訊號。

### B-12 R85 收尾訂正與「為何達不到」的兩份量測

> 🔴 R85 收尾單人窗口訂正：本斷言此前把「**R85 是第一個非上升輪**」寫死成契約，
> 而那是 P2 在本輪**動工中**寫下的**預測**——同一輪其後的必付成長（款(12) 到期義務
> ＋四方複審點名的那批 blocking 修復）把它推翻，於是這條斷言在**它自己那一輪**就變成
> 一句假話。該輪逐輪加總實測為正，現查 `repin_round_nets()`。
>
> 🔴 **R85 為何達不到（是算術不是判斷，兩份互相獨立的量測）**：需要淨刪 588 行，而
>   · 機械普查 `tools/probe/guard_layer_dedup_census.py`（F1 落地，可重跑）＋人工複核
>     ⇒ 可用去重面合計 ≈ 90〜128 行；`assertX(a, a)` 型 tautology **一筆都沒有**；
>   · 棘輪自陳的第三條出口（把 WHY／史料搬出護欄層）最集中處＝本表自己，
>     全數搬走上限 ≈ 314 行。
>   ⇒ **全部出口用盡 ≈ 442 < 588**。硬湊只能開始砍射程確有差異的對子＝真的挖洞。
>   逐筆量測與交棒見 `docs/06_quality/CrossPlatform_R85_Guard_Repin_Evidence.md` §4。

## §D 史料搬遷（自 `tools/tests/test_dev_start.py` 逐字外移；原文一字不動）

### D-1 R71（DEF-101-760）：PowerShell pipe 編碼缺陷形狀與訂正

> 🔴 R71（DEF-101-760）：PowerShell 寫進 pipe 的位元組編碼＝**console output code
> page**，不是 UTF-8。Windows 繁中預設 CP=950（Big5），而本檔對 PowerShell 輸出的
> 斷言含 `❌`（U+274C）——CP950 表示不了它，Windows PowerShell 5.1 會靜默換成 `?`，
> Python 端再以 `encoding="utf-8"` 解碼整段中文即成亂碼 ⇒ `assertIn("❌", …)` 必紅。
>
> 為什麼以前沒紅（這才是本缺陷真正的形狀）：`chcp` 是**整個 console 共用**的行程外
> 狀態，全套跑時只要有任何一支較早的測試把它換成 65001，後面所有 PowerShell 呼叫
> 就跟著沾光。於是這支斷言「全套跑綠、單獨跑紅」——綠燈不是它自己掙來的，是別的
> 測試檔的副作用借給它的。這種綠沒有鑑別力，也會隨測試順序漂移。
>
> 修法＝每次呼叫都自帶 UTF-8 前置，把 `[Console]::OutputEncoding`（引擎寫進 pipe 的
> 編碼）釘成 UTF-8。前置字串本身住在 `_platform_helpers.PS_UTF8_PRELUDE`。
>
> 🔴 R71 訂正（原本這裡是第 4 份、且寫法與其他三處不同）：本檔首版自寫
> `$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
> $false`，理由寫「`[System.Text.Encoding]::UTF8` 帶 preamble 會吐 BOM」。該理由經
> Windows 11 真機 / PS 5.1 單變因實測**證偽**（三種寫法輸出逐位元組相同、BOM 全程
> 未出現；`$OutputEncoding` 只管餵原生子行程 stdin，本檔無此用法）——完整量測貼在
> `PS_UTF8_PRELUDE` 上方註解。故本檔改用既有多數寫法的共用常數，不留第 4 種。

### D-2 R69 P1：版本閘之前的 prelude 缺陷本體與舊測試盲區

> R69 P1：「版本閘之前的 prelude 必須在 _MIN_PY 下限**以下**的直譯器可載入」
>
> 缺陷本體（macOS 真機重現）：`tools/dev_start.py` 第 53 行被加上
> `from datetime import UTC`（`datetime.UTC` 是 **3.11** 才有的別名），而該行位在
> 版本閘（`_MIN_PY` / `SystemExit(2)`）**之前** ⇒ 用 macOS 系統 python3（3.9.6）跑
> 本檔會在 import 期就吐 `ImportError` traceback，DEF-101-628 修好的友善最低版本
> 訊息整個被打回原形。
>
> 🔴 為何舊測試抓不到、非重寫不可：既有的 `_FAKE_39_SHIM` 是「真 3.11 直譯器 +
> 開跑後改寫 `sys.version_info`」。改寫發生在 `runpy.run_path()` **之前**沒錯，但
> 底下跑的仍是真 3.11 直譯器——`from datetime import UTC` 在它身上永遠成功。也就是
> 說那支 shim **結構上不可能**觀測到 import-time 的版本相依失敗，它只能驗「版本
> 判斷分支」，驗不了「prelude 本身載不載得動」。本節因此改用**真的**次版直譯器
> subprocess 實跑（第一道），並補一道不依賴外部直譯器的靜態掃描（第二道），
> 兩道互為備援：真跑有鑑別力但依賴環境，靜態掃描恆跑但只看得到語法/名字。

### D-3 DEF-101-243③／R19／DEF-101-247③：win32 專屬案例與三重 mock 視野缺口

> DEF-101-243③：既有三態測試只覆蓋 darwin/linux，缺 win32 專屬案例
> （launchd 為純 macOS 機制，win32 上 platform_utils.is_macos() 應同樣判 False
> 並提早 return，不嘗試呼叫 launchctl）。
>
> R19 四方一審 QA 對抗式 bug-injection 標的：只 mock `subprocess.run` 對
> `Popen`/`os.system` 這類其他子行程 API 完全無視野——同時 mock 這三個入口，
> 確保「提早 return、不 spawn 任何子行程」的意圖真的被完整鎖住，而不只鎖住
> 目前實作剛好用到的那一個 API。
>
> DEF-101-247③（R19 複審，記入 backlog；R20 補齊）：三重 mock 仍未涵蓋
> `os.spawnv`/`os.posix_spawn` 等不經 `Popen` 的行程建立 API——本專案風格
> 全走 subprocess，發生機率低，但既然要鎖「不 spawn 任何子行程」的意圖，
> 補齊視野比留下已知縫隙划算。`os.posix_spawn` 為 POSIX-only（Windows
> `os` 模組無此屬性），`create=True` 讓 mock 在任何平台上都能安全掛上去，
> 不因屬性不存在而先於斷言就 AttributeError。

### D-4 QA 複審：`_cache_restore_trust()` restored 分支覆蓋缺口

> QA 複審：_cache_restore_trust() / _venv_healthy() 的『restored』分支是 round 2
> （b2a9cf2）修復的核心防線、也是本工具『秒級換回』賣點的實作核心，先前只測到
> TestVenvCacheHandoffBackup 這個旁支（碰撞備份），本體完全沒有直接測試機械把關。

### D-5 R3 QA 發現：shebang 腳本在 Windows 上的健康判定假死

> R3 QA 發現：shebang 腳本（#!/bin/sh）只在 POSIX 上可執行，Windows
> 上 _venv_healthy() 實際 subprocess.run([py, "--version"]) 會撞
> WinError 193（非合法 PE 格式），使「健康」情境在 Windows 上永遠
> 走到「不健康」分支——改複製當前真正在跑的直譯器本體（含 pyvenv.cfg，
> 見 _copy_functional_interpreter），三平台皆為合法可執行檔，能真實
> 驗證 _venv_healthy() 的 subprocess 呼叫成功。

### D-6 R3／R59：Windows Popen handle 殘留與有界等待改法

> R3 QA 發現（Windows-only）：Popen 物件本身持有子行程 handle，即使
> 子行程已真正結束，只要此 handle 未關閉，Windows 仍視該行程物件為
> 存活（OpenProcess 可成功開啟），造成 _pid_alive() 誤判仍存活——這
> 與正式場景（另一個全新 dev_start 行程檢查陌生 PID、從未持有其
> handle）不同，顯式釋放本行程自己持有的 handle 才能正確模擬「已
> 終止且無人持有」的情境。POSIX 上 del 對測試結果無影響。
>
> R59 DEF-101-523：`del proc` 只是丟掉 Python 端參照，實際 handle 由 CPython
> 的 refcount 立即釋放，但**Windows 核心釋放行程物件仍有極短延遲**，期間
> `OpenProcess` 仍可能成功 → `_pid_alive()` 回 True → 本斷言偶發翻紅。
> R59 主控實測：連續多次執行中出現過一次 `AssertionError: 1976 is not None`，
> 隨後連續 3 次重跑皆綠＝非決定性。改為**有界等待**（≤2s、20 次輪詢）後才斷言：
> 語意仍是「子行程結束後必須回 None」，但不再把「核心尚未釋放」誤判為缺陷。
> 假紅與漏測同等有害——它會讓人去追一個不存在的缺陷，或反過來養成忽略紅燈的習慣。

### D-7 MUST FIX A：舊版『事後 ppid 回溯』測試方式的 Architect 複審否證

> MUST FIX A 迴歸測試（取代舊版 TestGrandchildOrphanSurvivesDirectChildKill /
> TestMultiGrandchildLockNotPrematurelyStale 對『事後 ppid 回溯』的測試方式）：
> Architect 第三輪複審已用真實驗證證明那個修法在因果上必然無效（見上方
> TestStreamNewProcessGroupSurvivesDirectChildDeath 與 dev_start.py 內
> `_stream`/`_lock_target_alive`/`_DescendantWatcher` docstring 的完整推導），
> 舊測試的 `root_pid` 用的是測試行程自己（全程沒有死亡），跟真正的 bug
> （直接子行程本身已經死亡、孫行程被過繼）完全是兩回事。

### D-8 MUST FIX #3：`_DescendantWatcher` 舊版測試命中已移除的 POSIX 分支

> MUST FIX #3 迴歸測試（Windows 版）：`_DescendantWatcher` 自 MUST FIX A
> 起僅供 Windows 使用（POSIX 已改用 pgid + os.killpg，見上方兩個新測試類別）；
> 舊版 `TestDescendantWatcherFinalSyncSample` 是在這台 macOS 開發機上直接
> 呼叫 `_DescendantWatcher`，實際命中的是已被移除的 POSIX 分支
> （`_list_pid_ppid_pairs_posix`）——該分支代表的機制在生產環境已不再被任何
> 平台呼叫（POSIX 不用，且該分支本身已刪除），繼續測它沒有意義。

### D-9 R50／R67-E21／R67-M40：心跳跨站行為等價鎖立案沿革

> R50 四方複審發現：dev_start.py `_check_nightly_heartbeat()` 與
> install_mac_nightly.sh `report_heartbeat()` 是各自獨立實作的心跳判斷。既有
> `TestCrossSiteLiteralLocks` 只用 regex 從兩側原始碼抽『字面常數』（門檻天數、
> label）斷言相等，從未拿同一組心跳檔輸入實際執行兩側邏輯、比對『判定結果』是否
> 一致——若任一側未來改變比較運算子或取整方式，字面值鎖完全不會有訊號。
>
> 🔴 R67-E21：比對「哪些維度」不再由本檔自行決定——`_classify()` 回傳的 dict
> 鍵集合就是實際比對面，而 `test_lock_covers_every_dimension_claimed_by_installer`
> 強制它等於安裝器檔頭 `DIMENSIONS:` 機讀清單。WHY：R15 於 dev_start 新增第 4 個
> 維度（FAIL 計數）時安裝器沒跟上，而本鎖被寫死在 R12 的「三態」語意上，於是
> 「--status 對 nightly 全紅假綠」這件事在兩層守門下都零訊號。散文契約若沒有
> 機械出口，就只是一句沒人會發現它過期的話。
>
> 🔴 R67-M40：`now` 由測試凍結後**同時**餵給兩側（bash 走 IMN_NOW 測試縫、python
> 走 time.time patch），年齡以整數秒指定。舊版讓兩側各自呼叫 date/time.time，在
> 8.0 天整秒邊界上必然分歧且無法穩定斷言，只好刻意取 7.9／8.1 天避開——避開的
> 那一點正是唯一會出事的點。
>
> R67-M38：門檻取自 `dev_start._HEARTBEAT_MAX_AGE_DAYS`，**不得硬編**。舊版
> 寫死 `HEARTBEAT_MAX_AGE_DAYS=8`，是全 repo 第 4 份門檻字面值且不受任何跨檔
> 鎖保護——兩生產站點合法同步演進（8→10）時字面鎖 `test_heartbeat_threshold_
> matches_installer` 仍綠，只有本鎖假紅，且失敗訊息指控生產程式碼「兩份實作
> 分歧」，把維護者導向一個不存在的問題。

### D-10 R67-M37／R67-F29：`--status` 修前「三行全綠」的兩筆盲區立案

> 背景：`--status` 過去是「三行全綠」——launchctl 有沒有列出 label、plist 檔案存
> 不存在、心跳 mtime 幾天前。三個判準沒有一個會去看**已安裝產物的內容**，也沒有
> 一個看得見**中間漏跑**：
>
>   R67-M37  一份指向 `/nonexistent/OLD_PATH` 載體、且缺 `RunAtLoad` 的死排程
>            （R15 之前安裝過的機器至今就是這個樣子）回報全綠 rc=0。護欄側
>            `tools/macos_smoke_local.sh:474` 鎖的是**安裝器 heredoc 原始碼**含
>            RunAtLoad，不是**機器上實際安裝的產物**——來源正確不蘊含產物正確。
>            Windows 側 Show-TaskDetail 逐項印 4 個補跑保護設定的 `(expected X)`
>            供人比對，mac 側零對等物。
>   R67-F29  本機 07-28/29/30 三天零 nightly（整段關機），`--status` 仍印「✅ 心跳：
>            新鮮（距今 0 天）」——因為 07-31 開機後 RunAtLoad 補跑一輪把計數歸零。
>            心跳語意是「最後一次何時跑」，結構上看不見連續性缺口，而任何一次補跑
>            都會把先前整段空窗永久蓋掉。CI 停擺（DEF-101-081）期間本地 nightly 是
>            唯一每日兜底層，這正是判斷該兜底層死活的工具。

### D-11 DEF-101-766：非 Windows 平台短路缺陷本體與被否決的第三種做法

> 缺陷本體：`WindowsAppsGuard.ps1::Resolve-NativeExecutable`（DEF-101-759 為擋 pyenv-win
> 無副檔名 shim 而生）原本無條件照 `$env:PATHEXT` 過濾候選。PATHEXT 是 **Windows-only**
> 概念——PS Core 跑在 macOS/Linux 時該變數不存在，且 POSIX 執行檔本來就不帶副檔名
> ⇒ 每個候選都被淘汰 ⇒ `Get-PythonGeMin` 恆回 $null ⇒ macos-compat-ci 與
> root-infra-ci(ubuntu) 必紅。與 DEF-101-759 是同一個病，只是換平台發作。
>
> 🔴 被否決的第三種做法（誠實記錄，免下一個人再走一遍）：「在 PS 5.1 下清空
> `$env:PATHEXT` 跑生產函式、斷言它不回 $null」**零鑑別力**。本包實測（原生 5.1、
> 子行程內 `$env:PATHEXT = ''`）：修好之後的生產函式對無副檔名候選回 `FAKEPY_NULL=True`、
> 對真 `.exe` 候選 `git` 也回 `GIT_NULL=True`——因為 Major=5 一律短路進 Windows 分支，
> 清 PATHEXT 只是讓 Windows 分支把全部候選濾光，永遠碰不到本次修的那條路。修好修壞都綠。

### D-12 DEF-101-762：原生 stdout 解碼鎖為何併檔、缺陷為何出貨兩天以上

> 🔴 為何這組鎖住在本檔、而不是自己一支檔（R71／DEF-101-561③）：架構級裁決「R61 開輪
> 即禁止新增鎖檔、只准合併／刪除」——理由是護欄層已經比它所護的生產碼還大。R71 落地
> 時新開了 `test_native_stdout_utf8_decoding.py`，使 tools/tests 鎖檔數 53→54，三支機械
> 棘輪當場翻紅而四路收尾無一提到。四方指定的落點就是本檔：本檔已持有 `PS_UTF8_PRELUDE`
> 一族判準，同源的判準放同一處；併進來也順帶逼出了「兩道鎖互斥」這個真設計衝突的解
> （見 `_narrative_node_ids()`）。**併檔不等於降低鑑別力**：五個 case 逐一注入退化複驗。
>
> WHY（這條缺陷為什麼能活著出貨兩天以上）：
> Windows PowerShell 解碼**原生指令 stdout** 用的是 `[Console]::OutputEncoding`，而本
> repo 兩個上游都固定吐 UTF-8——`tools/git_hooks_install_common.py` 於載入
> `tools/_stdio_utf8.py` 時把 stdout reconfigure 成 UTF-8（不看 locale），`git` 本身也
> 一律以 UTF-8 輸出路徑。兩者只在 **UTF-8 主控台**下剛好對得上；在 **cp950**（繁中
> Windows 的 OEM 預設）下，含非 ASCII 的路徑會被解成 mojibake（真機實測：`煙霧測試`
> U+7159 U+9727 U+6E2C U+8A66 → U+003F U+EA57 U+EBEC U+769C U+7948 U+5CAB）。
>
> 致命的是**顯形條件與驗證條件互斥**：
>   · schtasks 起的排程環境 codepage＝950 ⇒ 每日必現；
>   · 人手動跑（Claude Code 的 PowerShell 工具／Windows Terminal）codepage＝65001
>     ⇒ 永遠不現；
>   · GitHub 的 windows runner 既非繁中系統、也不跑中文路徑情境 ⇒ 雲端 CI 抓不到。
> 也就是說**所有既有的人工與 CI 驗證載具，系統性地繞開了缺陷所在的那個條件**。
> `tools/windows_smoke_local.ps1` [6/9] 其實正確抓到了它，卻因為該腳本當時沒有任何 log
> 落點（DEF-101-761）而讓紅燈原因連續兩天不可考。這組鎖的存在，就是把那個條件從
> 「只有每日排程碰得到」搬進**平常就會跑的測試**。

### D-13 R81 包 F（S3-06）：pyenv-win shim 在 Windows 上結構性找不到候選

> 🔴 R81 包 F（S3-06）：原本只有一串 PATH 名稱，而那串在 Windows 上**結構上**
> 找不到任何可用的東西——pyenv-win 放進 PATH 的是 shim（`python3.10.BAT`），該
> shim 只有在 pyenv 把該版設成 global/local 時才轉得過去，否則它自己 rc=1
> （本機實測 stderr 逐字：`'python3.10' is not recognized as an internal or
> external command`）。真的直譯器住在 `<PYENV_ROOT>/versions/<ver>/python.exe`，
> PATH 上沒有它 ⇒ 只掃 PATH 等於在一台**裝了** 3.10 的機器上宣稱「找不到」。

### D-14 R81 包 F（S3-06）：TOOL-ABSENCE 與載具壞掉的兩種失效必須分得開

> 🔴 R81 包 F（S3-06）：**兩種失效必須分得開**。原訊息只說得出「找不到」，
> 而本機的實況是「找到了 pyenv 的 3.10.11、跑它、它自己 rc=1」——把後者
> 印成前者，等於在帳面上宣稱一件與磁碟相反的事（而且是一個永遠不會有人
> 去修的理由：「這台機器缺件」）。

### D-15 DEF-101-769／R74：真 pwsh 7 補驗為何非補不可、解鎖條件於 R73 成立

> WHY 這一支非補不可（帳本逐字指派 R74）：`DEF-101-766` 的修法此前**只有 harness 鎖**
> ——把生產函式原始碼搬進 harness、把唯讀的 `$PSVersionTable.PSVersion.Major` 換成可
> 設定的替身。那份鎖量的是**一份副本**，它證明不了「真的用 PS 7 跑起來時，這個分支
> 真的走得到、且行為與副本一致」。帳本把解鎖條件寫成三個可辨認的觸發時刻，其中
> 「要改雙引擎判準」已於 R73 發生、pwsh 7.6.4 也已在機器上 ⇒ 條件成立，補驗即到期。

### D-16 R71（DEF-101-755 結案）：skip 遮蔽鑑別力、DEF-101-760 躲在後面出貨

> 🔴 R71（DEF-101-755 結案）：`test_skips_sub_311_candidate` 原掛
> `@unittest.skipIf(os.name == "nt", "shim 為 POSIX sh 腳本")`——也就是說，
> 這支 `.ps1` **唯一真正出貨的平台**上，本類的行為鑑別力等於零，而類別 docstring
> 讀起來像它有。代價不是理論的：DEF-101-760（`else ""` 被 PS 5.1 吃掉一個雙引號，
> `Get-PythonGeMin` 在真 Windows 上恆回 $null）就是躲在這個 skip 後面出貨的，
> macOS/pwsh 上跑本類**全綠**。

### D-17 複審實測訂正：一次性 wake 事件鎖的鑑別力宣稱曾是假的

> 🔴 本鎖的鑑別力射程（**複審實測訂正**，不是推論）：本測試此前自陳「合成注入
> 『退回全文子字串比對』→ 轉紅（有鑑別力）」——**那句話是假的**。忠實還原該形態
> （`pmset -g sched | grep -iE "(${PMSET_WAKE_EVENTTYPES})"`）實測 24 tests **OK、
> rc=0**。原因：本 stub 的 eventtype 是 `wake`，而它不是詞彙表
> `wakepoweron|wakeorpoweron|poweron` 裡任何一項的子字串 ⇒ 全文比對在這份輸入上
> **本來就不會命中**，綠是白撿的，不是判準擋下來的。真正吃得下那個假綠的輸入是
> 一次性的 **wakeorpoweron**，已補成獨立一支
> （`test_a_one_shot_wakeorpoweron_is_not_mistaken_for_the_daily_repeat`）。
> ⇒ 本支保留的價值是「macOS 出廠常態（user-invisible wake）不得被誤判」這個
> **情境**覆蓋，不是形態鑑別力；別再把它讀成全文比對的守門人。

### D-18 R82：pmset 字面值鎖為何獨立成平台中立類別、真機實測數字

> 這件事在本輪特別要緊：被撤回的那個字面值**就是在 Windows 上寫下的**（R82 全輪
> 在 Windows 完成，mac 側整組被 skip 掉所以零回饋）。把守它的鎖也做成 mac 才跑，
> 等於把守衛擺在錯的那一岸——下一個在 Windows 上動這支安裝器的人照樣看不到紅。
>
> 真 mac 實測：`strings /usr/bin/pmset | grep -c "wake or poweron"` ＝ 0。
> pmset 印的是 com.apple.AutoWake.plist 的 `eventtype` **原值**
> （輸出樣板 `  %s at %s %s`），值域＝sleep/wake/poweron/shutdown/
> wakepoweron/wakeorpoweron。押那句散文的後果不是報錯而是**恆不命中**：
> 使用者照著跑完 sudo 指令，這兩列照樣印 ⚠️，於是他會再排一次、再一次。

## §E 史料搬遷（自 `tools/tests/test_mac_endurance_r83.py`／`tools/tests/test_archive_defect_log.py` 逐字外移；原文一字不動）

### E-1 `tools/tests/test_mac_endurance_r83.py`：`arming_arms` 分母硬編 vs 現查（R83 複審 F-05／FC-5）

> 🔴 R83 複審 F-05／FC-5 訂正：此處原本是**寫死的四元組**，而它上方的註解自稱那是
> 「全部入口」。複審者注入第五支 `arm_next_thing`（body 內含 `os.name != "nt"`，正是本包
> 立案要防的那個寫法）實測：現行寫死分母之下**兩支鎖皆綠**；換成量測分母後當場紅
> （`arm_next_thing:1083` / `arm_next_thing:UNWIRED`）。⇒ 那句話是「今天成立的量測值被
> 寫成常數」，本 repo 反覆判過這個形態（R79 為 hook 註冊面補的「第三向以量測集合當分母」
> 是同一件事）。

### E-2 `tools/tests/test_mac_endurance_r83.py`：R83 複審 A-02／F-6 立案實測（`sentinel_lifecycle` 回收臂在射程外）

> 上面那一組判準讀的是 `_GUARD_SRC`，而 `_GUARD_SRC` 只有 `.claude/hooks/
> context_budget_guard.py` 一支檔 ⇒ `tools/lib/sentinel_lifecycle.py` 的回收臂（零 import、
> 硬寫 `powershell.exe`）完全在射程外。複審實測後果：mac 上 `sentinel_task_names()` 回 `[]`、
> `_remove_task()` 回 127，而同一刻 `launchctl list` 列著活著的哨兵 ⇒ GC 回報「沒有任何工作」。
> **這是「有鎖在守假話」**（檔案在、判準在、測試全綠），本 repo 判過它比沒鎖更貴。

### E-3 `tools/tests/test_mac_endurance_r83.py`：`BackendInterfaceIsSymmetricTest` 立案與 A-01／A-06 訂正

> 立案（實測，非預防性）：修前 `list_jobs()` 只住在 `LaunchdBackend` 與
> `NoCarrierBackend`，`SchtasksBackend` **沒有**。一旦有人寫 `select().list_jobs(...)`，
> 同一行程式在 mac 上會工作、在 Windows 上 `AttributeError`——那正是「單平台判準不可
> 無條件外推」（DEF-101-766）的形狀，只是這次外推的是**介面**。
>
> F2-⑤ 當時的處置是**刪掉那兩支**而不是補第三支（依據：實查零呼叫端零測試＝死碼；
> 補一支給不存在的呼叫端＝推測性程式碼，Rule 2）。原註記自己寫了那個判斷的失效條件：
> 「哪天真的有消費者，補的時候三支一起補」。
> 🔴 R83 複審 A-01／A-06 訂正：**消費者當時就存在**，只是住在還沒重構的另一側——
> `sentinel_lifecycle.sentinel_task_names()` 是這支方法的 Windows 孿生，且有活消費者
> （`gc()`）。「零呼叫端」在字面上為真、在語意上為假，而那筆減法把 mac 回收臂的修法從
> 「叫一個現成方法」變成「先補回原語」。本輪三支一起回補，這道鎖的射程不變：

### E-4 `tools/tests/test_mac_endurance_r83.py`：`RecyclingArmIsWiredTest` 立案實測（A-01）

> 落地當時的實測（複審者，我複驗）：`sentinel_lifecycle` 對 `schedule_backend` 的 import 數
> ＝**0**，GC 走 `powershell.exe` ⇒ mac 上 `sentinel_task_names()` 回 `[]`、`_remove_task()`
> 回 127，而同一刻 `launchctl list` 列著活著的哨兵。**最貴的一半是回報**：GC 逐字印
> 「（沒有任何 AutoSDD_Sentinel_* 工作…）」＝假陰性——專門用來發現增生的那支工具說一切正常。
> 而「移除」那一半其實是通的（舵手手動 `--remove-schtasks` rc=0 收掉孤兒走的正是那條路）
> ⇒ 只壞列舉比整支壞掉更危險：移除得動、卻永遠找不到要移除的東西。

### E-5 `tools/tests/test_mac_endurance_r83.py`：`CredentialKeyHasOneHomeTest` 立案實查（F2-④）

> 立案（實查）：`schedule_backend.CRED_KEY_LAUNCHD = "schedule_credential"` 是宣告的家，
> 但 `session_resume_planner.py` 有 **3 處**把它當 kwarg 名字直接寫出來
> （`state.update(next_run_time="", schedule_credential="")`，三支終態路徑各一處）。
> 改鍵名的後果：後端把憑證寫進新鍵、終態清的是舊鍵 ⇒ 舊鍵殘留一個過期憑證，而
> `relay_problems()` 的判準是「兩鍵任一非空」⇒ 一個**已經放棄**的續航會被判成
> armed／waiting 而繼續被信任。這與 R59 事故同形（「我下了指令」≠「它真的排進去了」），
> 且全套測試照綠——因為兩個家今天恰好相符，而判準從不問「這兩個字面是同一個東西嗎」。

### E-6 `tools/tests/test_mac_endurance_r83.py`：`_print_output` fixture 扁平改巢狀（R83／QA 訂正）

> 🔴 R83／QA 訂正：本 fixture 原本是**扁平**的，而真機輸出是巢狀的——`state = ` 在裡面
> 出現三次（job 自己那一個在最外層，另外兩個在 `resource coalition`／`jetsam coalition`
> 子區塊裡，且那兩個恆為 `active`）。fixture 少了巢狀結構，等於讓整組 launchd 測試都在
> 一個比真實世界簡單的世界裡跑：解析器的「掃到就覆蓋」缺陷在這裡結構上顯現不出來，於是
> 30 條綠全數成立，而真機上的憑證同一刻在說假話。**fixture 與被測世界的形狀不符，是最
> 貴的一種假綠**——所以這裡照真機補上巢狀塊，讓每一條既有的綠都改在真的形狀上成立。

### E-7 `tools/tests/test_mac_endurance_r83.py`：`CalendarMomentReachesThePlistTest` 修前逐位元組實測

> 修前的實況（本輪逐位元組實測，不是推論）：四個相異 `at_expr`
> （`'2026-08-10 23:02:00'`／`'2027-01-01 00:00:00'`／`(Get-Date).AddHours(5)`／空字串）
> 產出的 plist **sha256 完全相同**，相異指紋數 = 1 ⇒ 那個引數結構上到不了 plist；
> 而同一刻決策層逐字印「⇒ **重排到那個時刻**（本次零 token）」。
> 代價已經發生：本輪真實撞線語料裡同一個判定連印四次（22:06／22:21／22:36／22:51，
> `fire_at` 每次都是 23:02:00），掌舵者據此判「喚醒完全不 WORK」並開了一個 P0
> ——**假話造成假診斷**。

### E-8 `tools/tests/test_mac_endurance_r83.py`：`DeferredActionWaitsForTheParentTest` — R83-B P0 真根因逐字重現

> 掌舵者的判讀是「移除成功、建立失敗，而且回報成功」。**那個判讀被駁回**——真根因是
> `_defer_bootout` 裡寫死的 `sleep 3`：
>   · `_sentinel_tick` 的 disarm／escalate 分支在 disarm 之後只再寫一行 log（3 秒夠用，
>     所以這個缺陷躲過了當初那次對照實驗）；
>   · 而 `_resume_tick` 的 **resume** 分支在 disarm 之後才跑 `_run_resume`
>     （`subprocess.run(..., timeout=3600)`）⇒ 3 秒後 bootout 把整個 job 連同那一跑
>     一起殺掉，`append_log(resumed)` 那一行**永遠寫不出來**。
>
> 真機合成實驗（R83-B 當回合，本機 macOS 25.5.0，label `AutoSDD_R83B_E4`）逐字：
>     23:24:18 START pid=77099 XPC_SERVICE_NAME='AutoSDD_R83B_E4'
>     23:24:18 disarm rc=0（延後 bootout 已 spawn）
>     23:24:19 長工作進行中 t+1s
>     23:24:21 長工作進行中 t+2s          ← 到此為止，沒有下一行
>     bootout rc=0 at 2026-08-10T15:24:22Z
> 對照本輪**真實撞線**語料（同一個形狀，這是它在 production 的證據）：
>     23:06:33 sentinel_decided action=probe    ← reset 23:00 已過，正確地去探測
>     23:06:37 probed                            ← 探針真的跑了
>     23:06:41 bootout rc=0                      ← 4 秒後自我 bootout
>     （此後沒有任何 `resumed` 事件，哨兵也從 launchctl 消失）
> ⇒ 修法不是「把 3 改大一點」（那只是換一個會過期的猜測），而是讓那句原本就寫在
>   `disarm` 上方的話變成真的：「主行程把該寫的都寫完、正常退場，然後才 bootout」。

### E-9 `tools/tests/test_mac_endurance_r83.py`：R84／SA-05 立案實測（`pmset` 姿態靜默）

> 病（複審當回合實測）：`pmset -g sched` rc=0／**0 位元組**（零排程喚醒）、`pmset -g custom`
> 的 AC 段逐字 `sleep 0`，而武裝路徑對 `sleep != 0` **完全靜默**——憑證會照樣印出一份看起來
> 完全正常的三件式。⇒ 6e 今天在這台機器上成立的唯一原因是一個**不在 repo、不隨 clone 走**
> 的機器設定（同 R73 把一台機器的安裝路徑寫成常數的判例）。

### E-10 `tools/tests/test_mac_endurance_r83.py`：R84／ZT-03＋ZT-07 立案實測（痕跡住 `$TMPDIR` 蒸發）

> 病（複審當回合實測，逐字）：R83 那個 P0（等父行程退場才 bootout）的唯一決定性憑證
> `parent-gone waited=20s` 住在 `$TMPDIR` ⇒ `ls "$TMPDIR"/autosdd_sentinel_bootout_*.log`
> 回 `no matches found`、`grep -rl "parent-gone" "$TMPDIR"` rc=1 ⇒ **修好與沒修好在事後外觀
> 相同**；同一份實測還顯示交棒書引用的 `probed`／`gc_reaped` 在現存痕跡檔裡皆為 0。

### E-11 `tools/tests/test_archive_defect_log.py`：`TestHandoffProseDetectionCoversAlternatePhrasing` 正樣本史料（SA-R63-01）

> 正樣本取自 `archive_35` 的 `DEF-101-614`（「…留待 R62」）與 `DEF-101-615`
> （「…承接者改派 R63」）——這兩列在 R63 動工前用**舊版** `HANDOFF_PROSE_RE`
> （只認「下一輪／下輪」「R\\d+候選」「解鎖條件」「deferred」「backlog」）跑
> `--apply` 時實際被放行歸檔（見 `archive_35.md` 標頭「判準④ 攔下、刻意未加
> `--ack-handoff` 而留在主檔者：（無）」——若舊正則曾攔下這兩列之一，該欄不會是空）。
> SA 複審人工覆核確認兩列本身標的皆已完成、不算誤歸檔，但正則本身確有此盲區。

### E-12 `tools/tests/test_archive_defect_log.py`：`TestPlanRejectsRowsWithExternalResidencePointers` 立案（DEF-101-612）

> 🔴 這是 DEF-101-612 的直接修復：R60 收尾包執行 `--apply` 搬走 `DEF-101-529`／
> `555`／`558` 後，家族與治理文件內共 **11 處**居所指針同時失實——判準①②③④⑤只看
> 該列自身狀態，完全不看「有沒有別的檔指著這一列」，`--apply` 當時毫無鑑別力，
> 要等下一次 `--check`（事後稽核）才抓得到。

### E-13 `tools/tests/test_archive_defect_log.py`：`test_apply_writes_lf_only_and_conserves_bytes_on_a_faithful_copy` 三筆修訂史料

> 🔴 **不依賴 live 帳本當下是否還有可搬列**：本測試初版直接對忠實複本跑 `apply()`，
> 於是主控在同輪執行 `--apply --archive-num 31` 把全部 22 筆可搬列搬走之後，
> 沙箱裡的可搬列變成 0、`apply()` 正確回 1「無任何可搬列，拒絕產生空 archive」，
> 這兩支測試就紅了——**紅的是測試的前提，不是被測行為**。歸檔後可搬列歸零是
> 帳本的正常狀態（甚至是健康狀態），測試不該把它當失敗。故改為在沙箱主檔尾端
> 自行追加一列**保證四判準全過**的合成列（狀態 `fixed@R60`、無活躍字樣、
> 無交棒字樣、ID 於執行期組出以避開 `test_defect_id_reference_integrity` 的
> 全庫 ID 追溯鏈掃描），讓控制組在任何帳本狀態下都有可搬列。
>
> 🔴 **必須是「多列」（round 2 SD-R60-R2-07）**：初版只合成 1 列，於是「逐列加總 vs
> 只算第一列」在數學上等價——SD 溫拷突變把 `released` 改成 `len(move_lines[0])` 後
> 32 支全綠、零訊號。故本控制組固定合成**兩列**並硬斷言 `len(movable) >= 2`：
> 多列時「只算第一列」必然讓位元組守恆不成立。
>
> 🔴 **守恆算式含 `added`（round 3）**：`apply()` 自判準⑤ 起會把該次歸檔的索引
> bullet 主動寫進主檔，故恆等式是「新主檔 + 釋出 == 舊主檔 + 新增」。本測試**不重算
> bullet 內容**（那會變成第二份實作），而是從落地後的索引段反查「新出現的那一條
> bullet」量它的位元組——於是本斷言同時證明**除了那一條 bullet 之外主檔沒被偷改**。

### E-14 `tools/tests/test_archive_defect_log.py`：`TestNoAssertionSamplesALiveDocumentWholesale` 本輪實際付過的代價

> **本輪實際付過的代價**（不是假想風險）：
>   - 主鎖 `TestCriteriaListIsASingleSsot` 曾以 `dest.read_text(...)[:4000]` 取樣，切片
>     溢進逐字搬入的表格區，撞到 `DEF-101-584` 那一列的現象散文——那一列之所以寫著
>     「共七項」，正是因為它在敘述「標頭殘留共七項」這個缺陷。**被測行為是對的，紅的是
>     取樣範圍。**
>   - 後果不只是一次假紅：Pkg-P11 撞到同一支紅時的處置是**在資料側繞道**——把該列的
>     現象散文從逐字引用改寫成描述性寫法（實測：活體主檔現在對「共七項」零命中）。
>     載具的 bug 讓**帳本扭曲了自己的缺陷描述**，與「原文逐字保全、零刪除」的史料紀律
>     直接衝突。**假紅的真正代價是資料被改去討好載具，而不是紅燈本身。**

## §C 完工回填（收尾窗口實測終值，`--print-guard-lines` 重釘當回合輸出）

<!-- guard-total:R95 亦登記於 CrossPlatform_R91_Scan_Findings.md §K（doc_guard_total 兩站點在彼） -->

- 最終淨額：**84406 → 84362（−44）**；連升 streak（R93 +225／R94 +39 第 2／2 輪）歸零。
- 逐檔淨額（凍結表重釘值＝當回合實測，零加減推算）：

| 檔 | 前 | 後 | 淨額 | 搬遷目的地 |
|---|---|---|---|---|
| test_adr_xplat001_c1c2_lock.py | 5463 | 5411 | −52（含 R95 稽核列＋上限表列 +7） | 本檔 §B |
| test_archive_defect_log.py | 3877 | 3846 | −31 | 本檔 §E |
| test_block_destructive_git_r83.py | 1989 | 2098 | +109（Pkg-B +136 − 搬遷 27） | GovWrite 證據檔 §6 |
| test_context_budget_guard.py | 6900 | 6897 | −3（Pkg-D +164 − 搬遷 167） | Resume 證據檔 §L-3 |
| test_dev_start.py | 7056 | 6910 | −146 | 本檔 §D |
| test_mac_endurance_r83.py | 1787 | 1721 | −66 | 本檔 §E |
| test_quota_policy.py | 2068 | 2213 | +145（Pkg-C +154 − 搬遷 9） | Pace 證據檔 §7.4/§7.5 |

- 款(12) 兌現：`_REPIN_NET_CAP_SCHEDULE` 追加 `(95, 1100)`（步伐 200 < 300）；重武裝
  下一段 `_REPIN_NET_CAP_DUE_ROUND=97`／`_REPIN_NET_CAP_DUE_TARGET=950`（步伐 150 < 200）。
- 前綴指紋：`_REPIN_LOG_FROZEN_PREFIX_LEN` 24→25、`_REPIN_LOG_HISTORY_SHA256` 重釘為
  `0da44a4b…`（R95 列一併納入凍結前綴，未凍結尾端 0 列）。
- 分桶棘輪（搬遷後現查）：prose 4089／guard_self 3505，皆在基準與 stale 帶內，零違規、免重釘。
- 逐模組驗證：每一支被搬遷的測試模組於搬遷後當回合重跑，通過數與搬遷前逐字相同
  （lock 模組重釘後 138 passed／133 subtests，原 3 筆棘輪紅歸零）。

## §F 複審修復包批殘額重釘（收尾窗口第二列，`--print-guard-lines` 當回合輸出）

- 立案：複審唯一封鎖項——修復包批（M2/m5→`test_context_budget_guard.py`、
  M3/m4→`test_block_destructive_git_r83.py`）在 §C 凍結 84362 之後落地，實測 +31：
  `test_context_budget_guard.py` 6897→6925（+28）、`test_block_destructive_git_r83.py`
  2098→2101（+3）。複審報告另歸因 `_ps_engine.py` +7，經 `git diff HEAD`（空）與
  `--print-guard-lines`（凍結 115＝現值 115、漂移清單無此檔）雙向實查為**誤植**——
  +28 與 +3 已對足 +31 總額。
- 搬遷（R89 體例，判準與斷言零動）：M2 修前敘事→Resume 證據檔 §L-4.29、
  m5 修前段→Resume 證據檔 §L-4.30、M3 QA 實證括注→GovWrite 證據檔 §6.10；
  m4 括號句（「建立那天才發現沒人守＝靜默失效」）是判準理由，R89 裁定不搬。
  🔴 行數實抵 2 行（M2、M3 各 −1）：三段 lore 皆已外移，但 E501 顯示寬度棘輪
  （`test_e501_debt_only_shrinks`，East Asian Width 計寬、上限 100、存量 139 只准降）
  否決了 m5 併成單行的寫法——首次合併版全套實跑 `FAILED (failures=1)`（139→142），
  m5 遂回兩行形（lore 照搬、行數 ±0），M2/M3 縮短指稱後單行實測寬 98／100 過線。
- 搬遷後逐檔終值：`test_context_budget_guard.py` 6924（+27）、
  `test_block_destructive_git_r83.py` 2100（+2）、本表自身編修（新列 8 行）
  `test_adr_xplat001_c1c2_lock.py` 5411→5419（+8）⇒ 殘額合計 +37，補列
  `("R95", 84362, 84399, 37, …)` 重釘；`--print-guard-lines` 收斂輸出逐字＝
  `# 淨額 84399→84399 (+0)`／`# 逐檔漂移 0 支`。
- 前綴指紋：`_REPIN_LOG_FROZEN_PREFIX_LEN` 25→26、`_REPIN_LOG_HISTORY_SHA256` 重釘為
  `cf386020…`（新列一併納入凍結前綴，未凍結尾端 0 列）。
- R95 整輪合計（同輪多列合併）＝84406→84399（−7），仍為淨減；連升 streak 不進位。
