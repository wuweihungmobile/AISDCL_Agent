# AutoSDD_improving_102 — B/C 軌：Mac × Windows 11 相容性 R68（掃描完成、修復波中斷、**本輪未收輪**）

> **本輪柱別**：**B 軌（手腳框架）＋ C 軌（指揮官 AutoClaude）雙柱**——跨平台相容性同時觸及兩子專案與根層整合層。下一份：`AutoSDD_improving_103.md`。
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（整合迭代軌道①）。
> **日期**：2026-08-02　**平台**：本輪執行平台＝macOS 26.5.2 arm64 真機（Darwin 25.5.0）；**Windows 側本輪未取得真機**（⚠️ 不等於「Windows 從未驗過」——R20~R66 為 Windows 真機期，且 Windows nightly 每日 02:00 仍在跑；逐輪覆蓋見 `ADR-XPLAT-002` §6，DEF-101-756）。
> **版本演化**：**無**——只動 LATEST（`AISDLC_SDD_v0.30`）與根層／AutoClaude，零碰凍結版本體，故不觸發 Copy-on-Evolve、不觸發五軌 TLC。
> 🔴 **本輪狀態：未達收輪標準**。理由見 §4，**不得讀成「R68 已完成」**。
> 📝 檔名說明：`improving_100`／`101` 已由 C 軌 SD_09 佔用（2026-06-30），本輪續號 `102`。

---

## §1　本輪輸入（自 R68 前一輪 commit `24c5f34` 繼承）

上一跨平台輪（R67）收於 `24c5f34`，四支 CI 首次全綠。遺留三項：
1. **帳本容量死結**（`DEF-101-676`）：主檔 260747／硬線 262144，餘裕 **1367 bytes**、`--plan` 可搬 **0 筆** ⇒ 本輪加任何一列缺陷都會撞 rc=1 硬閘。**這是 blocking 前置**。
2. `DEF-101-652` 殘餘：`run_local_nightly.ps1` 無頂層 `param()`／`-Help`（本輪**未動**）。
3. `AutoClaude/tests/` 整棵樹從未在 Windows 執行過（`windows-nightly-full` 零執行）——本輪查明真相**比原認知更糟**，見 §2.2。

## §2　本輪已完成（附取證）

### 2.1 帳本容量政策解（blocking 解除）

專責 agent 逐條評估 `DEF-101-676` 所列三方向，**駁回兩條、採納一條、另立第四條**：

| 方向 | 裁決 | 依據（實測） |
|------|------|-------------|
| ③ 調高硬線 262144 | **駁回** | 對 Read 工具實跑探針：2MB 與 300KB 檔皆回 `exceeds maximum allowed size (256KB)` ⇒ 硬線綁的是**仍生效的工具事實**，非政策自由度。已加 `_READ_TOOL_MAX_BYTES` ＋ `TestHardLineIsToolFact` 綁死兩者相等 |
| ② open-backlog archive | **駁回** | 會讓兩條硬規則同時瞎掉：`orphan_backlog_problems()` 的輸入是主檔全文，未結列一旦搬出，孤兒偵測對「唯一需要偵測的那一群」變成零檢查。駁回鎖 `TestOpenBacklogArchiveIsRejected` |
| ① 判準③ 改寫 | **採納，並改成根因解** | 根因是 `_load_ledger_status()` 只讀主檔 ⇒ 補 `_load_archive_status()`，帳本 SSOT 至此才真的是它一直宣稱的「主檔 ∪ archive 家族」。釋放 11 筆／16217 bytes |
| ④ 判準② 誤報收窄（**本輪新立**） | 採納 | 判準② 是對整個狀態欄的裸子字串掃描，16 筆已結列因程式碼片段裡的 `open`、或**引述自己被推翻的舊狀態**而誤命中（語意剛好相反）。收窄後釋放 6 筆／18637 bytes |

**真正的成果不是釋放的 bytes，而是輪替吞吐被恢復**：動工前 31 筆已結列可搬 **0 筆**（全被誤報型判準釘住）＝結構性死結；落地後已無任何已結列被誤報擋住。本輪隨後在輪中跑了兩次 `--apply`（`archive_45`／`46`）即為實證。

### 2.2 十二維掃描（Scan-A~H/M ＋ 本輪新設 N／T）

25 agent、74 筆判決 → **CONFIRMED 41／DOWNGRADED 28／REFUTED 5**，存活 **69 筆**（P1×3、P2×24、P3×42）。
逐筆清單：[`CrossPlatform_R68_Scan_Findings.md`](../06_quality/CrossPlatform_R68_Scan_Findings.md)（已登記為具名治理文件，受體積守門＋指針稽核）。

**新設兩維**（已補進 `CrossPlatform_Scan_Dimensions.md` 維度表＋立案理由節，並由 SC-7 機械守：帳本用過的代號未定義即 rc=1，本輪當場命中兩筆）：
- **Scan-N（雙向落差）**：對應掌舵者第 3 點「Mac 開發時 Windows 不落差、反之亦然」。既有九維沒有一條問「單平台開發者的錯誤會不會溜過去」——差別當場顯形：九維全綠、四支 CI 全綠，Scan-N 一問就問出 `DEF-101-703`。
- **Scan-T（技術債）**：對應掌舵者第 4 點。既有維度會**發現**債但不負責**量化並排序**，於是債逐輪被重新發現、不被清掉。實證：`DEF-101-018` 的 ruff 存量數字被引用數十輪，本輪一量才發現它既 stale 又不可重現（未載明量測指令與根目錄，實測從 `AutoClaude/` 下 942、從 repo 根 3829）。

**三筆 P1**（前兩筆同一根因，由 Scan-C 與 Scan-N 各自獨立命中）：
1. **`DEF-101-703`**：兩支 `*-nightly-full` 自 2026-07-14 起 **18 天零成功、連續 5 次排程全紅**，橫跨 R48~R67（含 R67 一輪 40 筆修復）無人察覺。它們是**唯一**會在真 Windows／真 macOS 上跑完整 AutoClaude 測試樹的通道 ⇒ 「四支 CI 全綠」只涵蓋 **push 事件**。三道既有哨兵結構上都偵測不到：(a) `*-nightly-alert` 與被監控者同屬 GitHub Actions 計費平面；(b) `dev_start` 的 CI 活性哨兵只取 `--limit 1`、不分事件類型；(c) 心跳哨兵只讀本機 log mtime。
   → 比 §1 第 3 項的原認知更糟：不是「沒跑」，是**跑了、紅了、而且告警器會主動抹掉紅燈**（見下）。
2. **`DEF-101-704`**：`tools/dev_start.py:51` 頂層 `import tomllib`（3.11+），薄殼 `dev_start.sh:42-52` 無版本閘、無 `.venv` 時退回系統 `python3`——macOS 系統 python3 為 3.9 ⇒ `ONBOARDING.md` §2.1 明文承諾的「全新機器一鍵開工」在 mac 上必炸。

### 2.3 落地的修復（以 git diff 為準，**不以 agent 自報為準**）

- **P1 偵測面**：`root-infra-ci.yml` 第 15 道「nightly-full 排程陳舊度哨兵」（**阻斷式**，非 advisory——非阻斷正是 nightly-full 自己被忽略 18 天的機制）＋新模組 `tools/lib/ci_liveness.py`（本機平面外偵測、純唯讀 gh API、零 Actions 額度）。
- **告警極性**：`*-nightly-alert` 由黑名單 fail-open 改為白名單 fail-closed。原形態下 `cancelled`／`timed_out`／`skipped`／`conclusion` 為 null／job 改名五種情境都判成綠，於是走「綠燈時自動關閉既有失敗 issue」分支、對一張仍然有效的 P1 單留言「已恢復綠燈」並關掉它——**告警器主動抹除紅燈證據**，比單純漏報更糟。
- **P1 hooks 面**：`dev_start` 第⑤步在 macOS 預設情境 100% 失敗（子行程 PATH 無 `.venv/bin`、mac 又無裸 `python`）已修並真機驗證；同處裸 `.is_file()` 改走既有 `_safe_is_file()` 兜底慣例。
- **bash 3.2**：LATEST `run_tlc.sh` 在 macOS 系統 bash 3.2 下**每一條執行路徑**都必死於 `set -u` 空陣列展開，且該死法回 rc=1，恰好撞上該檔自訂的「1＝TLC 偵測到 invariant violation」語意 ⇒ 把環境問題誤報成形式化驗證失敗。薄殼 hash 已重釘（`check_script_parity._LATEST_PINNED_SHA256`）。
- **行程樹回收**：`Evaluator.run()` 與 CONDITIONAL evaluator 逾時只殺直接子行程、孫行程變孤兒續跑並寫檔，改走共用 `kill_process_tree()`（Windows `taskkill /T /F`；POSIX `killpg` SIGTERM→SIGKILL）。
- **退出碼契約**：`run_self_evolution.{sh,ps1}` 對同一失敗條件回不同 rc，已統一並寫入 `.NOTES` 契約表。其中「guard 缺席即降級」被 SSOT 鎖正確攔下並判為真陽性——**降級恰好在唯一有 WindowsApps 空殼陷阱的平台上關掉唯一防線**，故 `.ps1` 側維持 fail-loud（新 rc=8），與 bash 側刻意不對等，理由就地記於該檔。
- **Unicode／保留字**：淨化家族的 NFC/NFD 與 Windows 保留裝置名上標變體處置（`component_sanitizer.py`／`logger.py`／`check_ntfs_paths.py`）。

### 2.4 護欄層補強（Scan-H 同型復發自查，`DEF-101-707`）

本輪新落地的三處程式碼**在被接進閘門路徑時零測試**（`grep` 全 `tools/tests/` 零命中）：`tools/lib/ci_liveness.py`（100 行）、`unpinned_handover_problems()`、`stale_grandfather_problems()`——「用來偵測哨兵已死的哨兵」自己沒有任何東西保證它還活著，**正是它要消滅的形狀**。已補 **16 支雙向注入鎖**。

另把 `TestUnlockConditionIsMechanicallyChecked` 由「餘裕恆 ≥ 門檻」改寫為**對帳型**斷言（形狀取自 `DEF-101-689`）：原形態在本輪當場失效，而它給的唯一轉綠路徑是「再具名承認幾列去湊過線」——那正是 `DEF-101-676` 立這條判準要防的事。**一個只能靠做壞事才能轉綠的鎖，不是護欄**。改後兩個方向都留牙：宣稱已結卻沒解決 → 紅；改成未結卻不寫承接 → 紅。

### 2.5 閘門實測（收尾後，全部 macOS 真機）

| 閘門 | 結果 |
|------|------|
| `python tools/run_root_unittests.py` | **Ran 1438, OK (skipped=15)**（動工前 1400，+38） |
| `python -m pytest tests/ -q`（AutoClaude） | **3912 passed, 146 skipped** |
| `bash AISDLC_SDD/scripts/ci-gate.sh` | rc=0 |
| `bash tools/integration_gate.sh` | rc=0（4 PASS / 1 SKIP：cc-switch CLI 未安裝，DEF-01-007） |
| `check_defect_log_crossref.py` ／ `check_script_parity.py` | rc=0 ／ rc=0 |
| `check_loc_budget.py` | violations=0（**餘裕僅 2 行**，見 `DEF-101-706`） |

## §3　本輪的事故：修復波撞週配額（`DEF-101-705`）

11 個並行修復包**在執行中全數撞週配額上限**（11/11 agent error，`weekly limit`），留下 34 檔已改＋4 檔新增、約 3170 行的**半套工作樹**，且**無任何一包交回結構化回報**。

處置（依 CLAUDE.md〈可重啟點四條件〉）：
1. 當場 `git add -A && git stash create` ＋ tag **`R68-wip-preserved`** 保全，零工作量損失。
2. 主控逐一收斂：根層 unittest 由 **23 筆紅**收到 0 紅。23 筆分 12 組根因——
   - **9 組是「新程式碼未走既有測試注入點／未沿用既有慣例」**：新查詢繞過 mock 而去讀真機 plist；新規則對合成 fixture 兩向假紅；新呼叫點用裸 `.is_file()`；註解逐字引述被自家鎖命中（兩筆，本 repo 經典模式，依 ONBOARDING §9「文件散文不該長出第二個受抽取站點」既定慣例處置）。
   - **3 組是既有鎖正確攔下半套修復**：LOC 破線、SSOT 繞過、CI `paths` 未涵蓋新跨樹消費者（`tools/lib/ci_liveness.py` 與 `AutoClaude/autoclaude/utils/logger.py`，雙邊 push/PR 區塊皆已補列）。
3. 半套修復缺的回歸鎖由主控補上（§2.4）。

**教訓**：並行修復包的規模須先對配額餘裕做預算——保全與收斂的成本高於它節省的時間。

## §4　為何本輪**未達收輪標準**（誠實揭露）

掌舵者訂的收輪標準是「收斂 75% 以上**或**四方專家沒有發現問題」。**兩條皆不成立**：

1. **修復收斂率無法宣稱 75%**：69 筆存活缺陷中，git diff 可見的落地修復約 20 餘筆，且**沒有任何一筆經過逐筆複核與取證**（修復包全數未交回報告）。依 zero-trust 紀律，未經複核的「已修」宣稱一律不得寫入帳本——故 `CrossPlatform_R68_Scan_Findings.md` 檔頭明寫「修復狀態不在本表」，本文件亦不宣稱任何一筆已修。
2. **四方複審（Architect／SA／SD／QA）完全未執行**（0/4）：週配額耗盡，無法派出任何 agent。

本次 commit 的性質是**保全與收斂**（把 3170 行半套工作收成閘門全綠的可用狀態），**不是收輪**。

## §5　R69 承接（具名待辦）

| 項目 | 對應 DEF | 解鎖條件（可機械查） |
|------|---------|---------|
| 69 筆逐筆修復狀態建立 | `DEF-101-702` | ① 每筆有 fixed／wontfix／open 判定且附實跑取證；② fixed 者各有能轉紅的回歸鎖；③ 具名承接者寫在動工當輪的帳本列 |
| **四方複審**（本輪 0/4） | — | Architect／SA／SD／QA 各自獨立審查本輪變更集 → 全修 → 複審至零 REJECT |
| nightly-full 失敗根因 | `DEF-101-703` | ① 查明並修復根因；② 至少一次 `*-nightly-full` 排程成功；③ 第 15 道哨兵在該次之後仍 rc=0 |
| `dev_start` tomllib 版本閘 | `DEF-101-704` | 以 `/usr/bin/python3`（3.9）直呼 `tools/dev_start.sh` 實跑重現 → 修復 → 同法複驗，兩次 rc 皆記錄於當輪帳本列 |
| `autoclaude/` LOC 餘裕僅 2 行 | `DEF-101-706` | 收斂 `kill_process_tree()` 與 `pty_wrapper.close()` 兩份行程樹回收實作至 `utils/` 使餘裕 ≥ 100 行，或走 ADR-SD07-001 §6.3 正式程序（Architect + SD 雙簽）。**禁止**直接上調 `.loc_baseline` |
| 帳本健康餘裕（現約 8000 < 10240） | `DEF-101-676`（已下修為 partial@R68） | 下一槓桿＝44 條歸檔索引 bullet 佔約 37400 bytes、每次 `--apply` 再加約 1300；與 archive 標頭去重估可回收約 26KB |
| `DEF-101-432` 狀態首詞訂正 | `DEF-101-710` | 回讀全欄確認訂正即現況後依 `DEF-101-433` 體例改首詞，使該 warning 對該列消失 |
| `run_local_nightly.ps1` 對等缺口 | `DEF-101-652` | 本輪未動（承自 R67）。需 Windows 真機實跑驗證 |
| Windows 真機驗證 | — | 本輪所有 Windows 結論皆為靜態分析／沙箱模擬／CI 對帳，**本輪未取得真機**——讀任何本輪「已驗證」宣稱前請先問「在哪個平台驗的」（此為**本輪**屬性，非 repo 常數：DEF-101-756） |
