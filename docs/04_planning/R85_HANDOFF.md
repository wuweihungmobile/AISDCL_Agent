# R85 → R86 交棒書（R85＝**macOS 第三輪、十二包並行 ＋ 四方複審 ＋ 三包收斂**）

> 前一份＝[`R84_HANDOFF.md`](R84_HANDOFF.md)。本輪計畫書＝[`AutoSDD_improving_109.md`](AutoSDD_improving_109.md)；
> 掃描發現＝[`CrossPlatform_R85_Scan_Findings.md`](../06_quality/CrossPlatform_R85_Scan_Findings.md)；
> 四方複審＝[`Architect`](../06_quality/CrossPlatform_R85_Review_Architect.md)／[`SA`](../06_quality/CrossPlatform_R85_Review_SA.md)／[`SD`](../06_quality/CrossPlatform_R85_Review_SD.md)／[`QA`](../06_quality/CrossPlatform_R85_Review_QA.md)。
>
> 🔴 **本檔體例**：會漂移的量測值一律不寫死，只寫「哪一支載具會印出它」。
> 凡本檔寫出的 rc，都是**收尾單人窗口當回合真的跑過**的；沒跑的一律標明。

---

## §0 開場必讀（跑完再往下讀）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
git log -1 --format='%H %s'
git status --porcelain | wc -l
.venv/bin/python -c "import sys;sys.path.insert(0,'tools');import check_defect_log_crossref as C;from pathlib import Path;print(C.current_round(Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8')))"
```

1. **不採信本檔任何「已通過」宣稱。** 重啟後第一件事是重驗（§5.1）。zero-trust 對自己上一段也適用——
   本輪四方複審**逐字駁回了 R85 自己的多筆宣稱**，包括收尾窗口寫下的那幾筆。
2. **先讀根 `CLAUDE.md`。** 鐵律三～鐵律七四條**平台無關**，本輪抓到的東西幾乎全落在那四條上。
3. 🔴 **本輪 Windows 側零真機量測。** 凡本檔提到 Windows 的地方一律是靜態推論。
   SA 的判詞逐字：**訴求 1「無任何相容性 Bug」今天結構上不可查證**——Windows 零真機
   ＋ GitHub CI **6/6 全紅（job `steps=0`、各 3 秒＝帳務停擺不是程式錯）**。

---

## §1 一句話總結

**R85 是第一次「十二包並行 ＋ 四方獨立複審 ＋ 三包收斂」的一輪。**
它最大的產出不是修好的東西，而是**一批被實測推翻的自我宣稱**：
四方複審合計 **21 blocking**，其中有 **9 筆是駁回本輪自己的交付宣稱**。
本輪 agent 實測駁回上級／同儕判讀共 **10 次以上，無一次是錯的**。

---

## §2 掌舵者訴求逐條結算

> 🔴 判定用四級：**達成／部分／未達成／做不到（附結構性理由）**。
> 「做不到」與「未達成」刻意分開——前者是今天沒有任何人能做到的事，後者是沒做。

| 訴求 | 判定 | 依據 |
|---|---|---|
| **1** 兩平台零相容性問題 | **做不到（今天不可查證）** | Windows 零真機 ＋ CI 6/6 帳務停擺。mac 半邊：`AutoClaude pytest` rc=0、`AISDLC_SDD ci-gate` rc=0 |
| **2** 架構簡潔／拿掉不合理機制 | **部分** | Architect 實測**減法佔比 7.0%→27.6%（約 3.9×）**；但**整支移除機制數＝0**，護欄層淨額仍為正（詳見 §3） |
| **3** 兩邊不落差 | **未達成** | M5 注入矩陣 `Win2mac=6/12 mac2Win=5/10`，**與 R84 逐字相同**；且 AST 接線率一度由 8/11 惡化為 8/12（F1 處置中） |
| **4** Windows 低級錯誤根因 | **部分** | 歸因重跑 n=**1243**（含 R84 逐字稿），最大非-OTHER 桶＝**「宣稱先於查證」197**，`--control` lift 亦排第一（+11.1pp）⇒ **連兩輪居首且今天零機械物** |
| **5** 挖深清債 | **達成** | 帳本 bytes 餘裕 883 B → **33 KB**；殘留待辦 40→13（**修判準不是關小燈**）；幽靈依賴 302→0；4 支 fail-open lint 治本 |
| **6a** 隨時監控 | **達成** | 伺服器端算好的 %，分母不在本機 ⇒ 換帳號不可能算錯 |
| **6b** cap＝f(水位,距 reset) | **達成，且本輪真的擋了我三次** | 見 §4 |
| **6C/6c** 85 準備／95 停止 | **達成** | 四門檻 50/70/85/95 皆 env 可調；`halt` 帶 `cap=0` 且不吃任何覆寫 |
| **6d** 同 session 續跑 | **部分** | 哨兵活著、續跑 argv 實查為 `claude -p -r <sid>`（同 session 正確），但**痕跡只有 patrol 分支**，`arm_reset`／`probe` 從未走過＝**端到端零驗證** |
| **6e** 撐過 0~5h | **部分，但找到新出路** | 🔴 **實測否決掌舵者問的「每 50 分鐘喚醒一次」**：以 1,063 支逐字稿／15 episode 重量，改 50 分會讓 **3/15 完全沒醒**。mac 不休眠的**可行解是 `caffeinate`**（不需 sudo、不改任何持久設定 ⇒ 不在已否決的 `pmset repeat` 射程內） |
| **6f** `.env` 實測調優 | **部分** | 根 `.env` **本輪首次建立**（此前從不存在 ⇒ 14 政策鍵全走出廠預設）；生效已證（`CONVERGE_PCT` 70→60 使 `cap` 4→2、band `notice`→`converge`，水位三次相同排除混淆）；但**逐鍵仍是出廠值**，「調成最佳值」未做——`PACE_*`／`CAP_*` **零實測依據，刻意不動** |
| **6z** 前沿調研 | **達成** | 官方原文三筆。最重要：**查不到任何官方通道能回答「個人訂閱帳號當前水位＋reset」**（Usage & Cost Admin API 逐字 "unavailable for individual accounts"）⇒ `api/oauth/usage` 是唯一存在的路 |
| **7** Windows 彈窗 | **未達成（且不得計入）** | QA 獨立裁決：AC-(c)＝**部分交付，且交付的不是所報症狀那一半**。詳見 §2.1 |
| **8** Container 整理 | **達成（工作量很小）** | 5 image 全部有消費者、零刪除；`docker builder prune` 回收 **407.8 MB**。🔴 本項一度**被靜默漏掉**（做了但不落磁碟），由 SA 抓出後補記於計畫書 §3.1 |
| **AC-(a)** 舵手喚醒 | **部分** | `unattended_refusal()` 能力閘落地並接上兩個 `shell=True` 面 ＋ 58 支回歸鎖；**mac 側 `AUTOSDD_UNATTENDED` 原本等於沒有牙**已由 P12 補（F1 正在修其射程缺口） |
| **AC-(b)** example_playbook | **達成（首次）** | 連續三輪零交付後首次真交付：**無 `MINIMAX_API_KEY`、走 production `main()` 原路、rc=0、4/4 步驟全跑完**，T03 的 `evaluator_command` 是真 `pytest`（`評估通過 [exit=0]`），PG `both` 模式 `pg_real` 1 passed |
| **AC-(c)** 彈窗 | **部分（見 §2.1）** | — |
| **SDD Agents** | **達成** | 28 支全盤點；**19 支實改**；幽靈依賴 302→0 並在**源頭模板**堵住再生 |
| **S1** skipped | **做不到（結構性）** | 見 §2.2 |
| **S2** 帳本警告線 | **未達成** | 未結 88 → **89**（越過 warn 86）。🔴 但理由經**三方獨立驗證**：P9 查 21 列、P1 查 8 列、複驗 agent 掃 55 列，**合計 84 列次只找到 3 列真的已修** ⇒ **不是沒人去結，是它們真的還沒修** |
| **注③** Archive | **部分** | 盤點完成（母體 116 支／4.29 MB；**可回收 40 支／1.71 MiB，只需改 2 個具名常數**），**零搬檔**（`git mv`／`git rm` 只有收尾窗口能做，且跨檔參照稅高） |
| **注⑥** 先本機驗證 | **達成** | 全程零 `push` 試探；CI 帳務停擺使這是**唯一可行路徑**，不是偏好 |

<!-- absent-if: measured-at=2026-08-12 host=Windows -->
<!-- absent-if: R83 / AC-(b) -->
<!-- absent-if: R84 / AC-(b) -->

> **本節三筆「某物不存在」宣稱的證偽標的（皆為真標的，未動用逃生口）**：
> · **「Windows 零真機」**（訴求 1／7／S1 三列共用的前提）——錨＝`ONBOARDING.md` 的
>   `snapshot-fingerprints-win32`，repo 內**唯一**機械記下「某平台上一次真機量測是什麼時候」
>   的地方。本輪期間只要有人在真 Windows 上跑過 `--write --with-slow`，該欄就會變成本輪日期
>   而讓那三列一起轉紅。
> · **AC-(b)「連續三輪零交付」**——沿用 R84 §3 立下的命名慣例判例：本 repo 的 AC 交付會在
>   回歸鎖檔頭第一行逐字寫下「輪號 ＋ AC 標籤」。上面兩個 pattern 一旦在任何 tracked 檔裡
>   搜得到（標記行自己不算），就代表 R83／R84 其中一輪其實交付過 ⇒ 這句話當場為假。
>   🔴 **誠實劃界**：它是**命名慣例依賴**——抓得到「照本 repo 慣例交付了」，
>   抓不到「用別的形狀交付了」（同 R84 §3 對這個判例自己下的註）。
> ⚠️ 標記是**區塊級**的，本節數列共用這三個 pattern；任一命中時需人工分辨是哪一列被打臉。

### 2.1 🔴 AC-(c)／訴求 7 的最終裁決（掌舵者指定 QA 驗，QA 複驗後**修正** P3）

三條判準：
1. **有會紅的鎖** → **是**。QA 自己重做合成注入：基線 16 passed rc=0；三種注入各 rc=1 且**各只打中一支、零串音**；還原後 sha256 逐字相同。
   補一筆：該鎖 docstring **對自己的鑑別力多報一層**（其中一項其實是別支鎖抓到的）。
2. **生產碼落在「所報症狀」的因果鏈上** → **未成立**。掌舵者看到的黑框已定位在**額度哨兵 tick**
   （15 分鐘節律，SSOT＝`session_resume_planner.py` 的 `SENTINEL_INTERVAL_SECONDS=900`）；
   而 AutoClaude 發的是 toast 泡泡、不是黑框、無 15 分鐘節律。
3. **殘留風險有登記** → 🔴 **QA 推翻 P3 的「否」＝有登記**（`DEF-200-063`，`open（承接輪次 R85）`）。

**⇒ 部分交付，且交付的不是所報症狀那一半。不得記為「已交付」，也不得記為「整項未交付」。**

### 2.2 🔴 S1「徹底解決 skipped」為何是**做不到**而不是沒做

- 根層 44 支**全部**是 `[WINDOWS-NATIVE-ONLY]`（`debt=0`／`untagged=0`，QA 抽樣複驗分類正確）⇒ mac 上結構性不可執行。
- AutoClaude 側 73 支：`untagged` 已歸零。
- 🔴 **QA 的關鍵發現**：那 44 支今天在 Windows 上**沒有憑證**（win32 剖面落款是 **R82**，三輪未量），
  而且——**即使明天真的上 Windows 重量也答不了 M6**：`skip_group_policy.py` 自己的〈誠實劃界〉逐字承認
  「判準粒度是**剖面**不是**測試**」⇒ 比的是計數不是 test-id 集合。
  **這是結構性缺口，不是量測缺口。** 交棒給 R86 的是「改判準粒度」而不是「去 Windows 跑一次」。

---

## §3 訴求 2 的量化（Architect 設計、可重跑）

R84 的 2.6% 是上一輪 Architect 量出來的（−71 / 2655）。本輪改用三個**單邊量**：

| 量 | R84 | R85 | 判定 |
|---|---|---|---|
| **M-A 減法佔比** | 7.0% | **27.6%** | ✅ 約 3.9× |
| **M-B 整支移除機制** | 0 | **0** | ❌ |
| **M-C 護欄層淨額** | +3755 | **82838 → 83475（+637）**（R85 三列稽核痕跡的逐輪加總；收尾單人窗口在所有包停工後實測，憑證＝`--print-guard-lines` 印 `(+0)` 且逐檔漂移 0 支） | ❌ **未達成**——F1 已窮盡去重面並留下可重跑載具 `tools/probe/guard_layer_dedup_census.py`，差額與交棒對象見 `docs/06_quality/CrossPlatform_R85_Guard_Repin_Evidence.md` §4 |

🔴 **Architect 的架構級結論（本輪最有價值的單一洞見，R86 應據此行動）**：
護欄層 : 生產碼 ＝ **113,084 : 26,125（4.33:1）**；分桶普查
**守散文 34.2%／守 SDD 23.0%／守自己 14.0%／守生產碼僅 ≤12.5%**（first-match 啟發式，末值是**上界**）。
> **問題不是「太多」，是單一總量棘輪讓最便宜的那一桶（守散文）永遠贏。**

它**明確反對拆掉棘輪機制**（本輪它真的攔下了最重要的一句假話，成本約 16 行/輪），
建議 R86 做兩件事：**S1 先做分桶 probe 讓比例可見；S2 把 `_FROZEN_GUARD_LINES` 按桶拆**
（守生產碼可長、守散文／守自己 shrink-only）。

---

## §4 訴求 6b 在本輪的三次真實作用（不是設計文件，是實帳）

| 時刻 | 機制說的話 | 我的動作 |
|---|---|---|
| 派第 9 包時 | `每 300s 最多 4 次扇出，本視窗已用 4 次 ⇒ Agent 本次不執行` | 排隊，改做收斂工作 |
| 派第 11 包時 | 同上 | 排隊 |
| 派 F3 時 | `seven_day 70% band=converge cap=2`（**cap 由 4 掉到 2**） | 停止開新工作面，只收不展 |

🔴 **P10 的副產品發現解釋了為何我一直被擋**：派發帳是**機器全域**
（`$TMPDIR/autosdd_quota_dispatch.d`，**路徑不含 session id**）⇒ `cap` 由全部並行包共用；
本輪 N=6／cap=4 時**人均 0.67**，**調研型包在並行波中會被結構性餓死，而表徵看起來像「額度很緊」**。

🔴 **政策 P-1（本輪明文化）**：`--pace` 的 session 軸可算出 `cap=16`，卻被 `seven_day` 的 far×0.5 夾住
⇒ **任何週級軸 ≥50% 時，5 小時軸的加速結構上表現不出來**，且畫面看不出原因。
懸崖恰在 `notice_pct`：**49.9%→rec=16／50.0%→rec=4**。
P10 判定**這不是 bug**（週軸 binding 時未用額度不會蒸發，取 `min` 是正確的），但**必須寫下來**。

---

## §5 R86 首日要做的事

### 5.1 開工前先確認基線（照順序，全部讀 rc 不接管線）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
docker compose -f docker-compose.ci.yml up -d; echo rc=$?
.venv/bin/python -m alembic upgrade head          # 🔴 容器 healthy ≠ 已 migrate
.venv/bin/python tools/run_root_unittests.py > /tmp/a.log 2>&1; echo rc=$?
cd tools/tests && ../../.venv/bin/python -m unittest discover > /tmp/b.log 2>&1; echo rc=$?
cd "$r" && .venv/bin/python tools/check_defect_log_crossref.py > /tmp/c.log 2>&1; echo rc=$?
.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines   # 護欄層淨額現查
cd AutoClaude && ../.venv/bin/python -m pytest tests -q; echo rc=$?
cd ../AISDLC_SDD && bash scripts/ci-gate.sh; echo rc=$?
```

🔴 **QA 對「兩種載具」的裁決（訂正 P11 的疑慮，我採納）**：`run_root_unittests.py` 的三條早退
**全部 `return 1`**（`grep "return 0"` 全檔只有 2 處且都在跑完後的 census 內）⇒
**結構上做不出假綠，被騙成綠的次數＝0**——只要**讀 rc**。風險只在讀畫面。
建議 R86 讓早退時多印一行「本次一支測試都沒有執行」。

### 5.2 R86 的三件最該先做

1. 🔴 **護欄層分桶**（Architect S1+S2）——這是唯一能讓 M1 真的動起來的結構性改動。
2. 🔴 **M6 判準粒度**（QA §2.2）——把剖面比對改成 test-id 集合比對，否則「上 Windows 跑一次」也答不了。
3. 🔴 **「宣稱先於查證」的機械物**（訴求 4 最大桶，連兩輪居首、今天零攔截器）。
   誠實劃界：它發生的平面（宣稱本身）**永不變成 repo 裡的檔案**，靜態掃描結構上看不到
   ⇒ 需要的是**輸出面**判準（例：回報格式強制「rc 與指令必須成對出現」），不是又一支掃描器。

### 5.3 Windows 真機清單（沿用 R84 §5.2，本輪仍一項未驗）

```powershell
Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR '.venv\Scripts\pythonw.exe')   # 必須 True
$hookLog = Join-Path $env:TEMP 'autosdd_r86_hooks.log'
claude -p --model haiku --debug hooks --debug-file $hookLog "ok"
Select-String -Path $hookLog -Pattern 'Hook SessionStart.*success'          # 有 success 才算活著
Get-ScheduledTask | Where-Object TaskName -like 'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime
```
🔴 **驗收條件是正負兩面一起看**：「不閃窗」單獨成立**不算**通過（那正是 fail-open 的表徵）。

---

## §5.4 🔴 收尾單人窗口在本輪做的一筆「訂正」，攤開讓 R86 覆核

**它與「為了讓紅變綠而改成不比較」只有一線之隔，所以逐條寫下判準。**

**事實**：P2 在本輪動工中，於 `test_the_real_repin_log_stays_inside_the_cost_envelope`
裡把「**R85 是第一個非上升輪**」寫成斷言。那是一個**對本輪的預測**，被同一輪其後的必付成長
（款(12) 到期義務 ＋ 四方複審點名的 blocking 修復）推翻 ⇒ 該斷言在**它自己那一輪**變成假話。

**它與真正的義務居所不一致**：ADR-XPLAT-002 §8.1 item 15 逐字寫的是「**R86 前**必須出現一次
淨額 ≤ 0」——是**到期日**形狀，不是「R85 當場」。P2 的斷言比義務嚴，且嚴在一個被證偽的前提上。

**處置**：改成本 repo 既有的到期日形狀，具名常數 `_NET_SUBTRACTION_DUE_ROUND`。

| | 放寬（禁止） | 本輪做的訂正 |
|---|---|---|
| 「必須有一輪 ≤ 0」這個要求 | 拿掉 | **一個字都沒拿掉** |
| 到期時點 | 無限延後 | **釘死在具名常數，且刻意不留延期參數** |
| 今天的斷言內容 | 「已經達成」 | 「**尚未到期**」（今天為真；前者為假） |
| 方向鎖 | 無 | 只准往**前**挪（更早到期＝更嚴），往後挪需掌舵者裁決 |

**R86 覆核者請直接查兩件事**：① 那個常數的值有沒有被往後挪；② 到期輪一到，
`repin_round_nets()` 裡有沒有出現 ≤ 0 的一輪。**兩者任一失守，這筆訂正就退化成放寬。**

**同輪另一筆同型訂正**：`test_appending_one_row_keeps_the_history_digest_stable` 的**合成列**
淨額由正改為 0。理由不是讓它變綠，而是**下一輪真正合法的重釘本來就必須非上升**
（款(11) 現況如此）⇒ 0 才是「正常的下一輪」該有的形狀。款(11) 自己的主牙住
`test_a_third_consecutive_rising_round_is_red`（三格一組），本測試從來不是它的載具。

---

## §5.5 成熟度 M1~M6（判準 SSOT＝[`CrossPlatform_Maturity_Criteria.md`](../06_quality/CrossPlatform_Maturity_Criteria.md)）

> 🔴 **本節不重抄判準表**。SA 複審獨立做過一次判定，本節與它一致；分歧處已標明。

| # | 判定 | 理由（依門檻欄逐字比對） |
|---|---|---|
| **M1** | ❌ | 合取兩半都沒到。UEP 半：ADR-XPLAT-002 §8.1 逐行實查**回執列數＝0**。護欄行數半：本輪總量**上升**（§3 現查）⇒「連續三輪不上升」歸零重算。🔴 本輪的交付是把 Architect 的**分桶診斷**做出來（守散文 34.2%／守自己 14.0%／守生產碼 ≤12.5%），那是 R86 唯一能讓這條真的往下走的槓桿 |
| **M2** | ❌ | 門檻＝連續三輪假宣稱 ≤1。本輪四方複審 falsified **合計 9 筆**（QA 獨立列 5 筆、SA 7 筆、SD 7 筆、Architect 4 筆，去重後 9）。🔴 **與 R84 不同的是本輪 N/A 不成立**——四方複審真的執行了，分母非空 |
| **M3** | ❌ | 門檻＝第三方注入 100%。本輪**大幅前進但未達標**：F2 對四桶、F3 對 schema、QA 對通知鎖、SD 對 15 個判準各做了獨立注入；但**既有鎖庫隨機 20 支的抽樣面至今一次都沒做過**（SA 與 Architect 同時點名） |
| **M4** | ❌ | 門檻＝一輪 0 筆。本輪自己就修了多筆「散文宣稱 ≠ 實作射程」：計畫書「未派」已過期、AGT-11 立案數字住三個家且三份都錯、`shell=True` 白名單常數改名後根 `CLAUDE.md` 仍指舊名，成為幽靈符號、訴求 8 做了但不落磁碟 |
| **M5** | ❌ | 門檻＝未攔到 ≤1。本輪 `Win2mac` **6/12 → 8/12**（F1 接線後首次改善），`mac2Win` **5/10 未動**。程式碼語意層仍是 0 |
| **M6** | ❌ | 🔴 **本輪的發現讓這條的性質改變了**：QA 查出「即使明天上 Windows 真機也答不了 M6」——`skip_group_policy.py` 自陳判準粒度是**剖面**不是**測試**，比的是計數不是 test-id 集合。⇒ R86 要改的是**判準**，不是去補一次量測 |

**總判：0 / 6**，與 R80~R84 相同。

🔴 **但本輪與前四輪有一個實質差異，值得記在成熟度旁邊**：
M2 的分母**首次非空**（四方複審真的跑了），M3／M5 首次出現可量測的前進，
M6 由「沒量」變成「**知道為什麼量了也沒用**」。
成熟度數字沒動，但**每一格的無知程度都下降了**——這是本輪真正的產出。

---

## §6 方法論收穫（每條附「為什麼它會再犯」）

1. **訂正文自己會變成假事實。** 收尾窗口訂正鐵律三大表時**逐字引用了舊措辭**，
   而那個字面正是棘輪用來判斷該列有沒有機械物的依據 ⇒ 該列同時被算進分子又被讀成未覆蓋列。
   **為什麼會再犯**：引用原文在寫作上是好習慣，而「這個字面同時是判準的輸入」不會寫在任何地方。
2. **自動化重釘腳本的冪等判準會失效。** 以「新列是否已存在」當冪等判準，該判準在列的數字被修正後失效
   ⇒ 重複追加了一列；又以「舊總量」正則定位本輪那一列，而同輪有兩列共用相同舊總量
   ⇒ **改到了 append-only 保護的前一列**。兩者都被鎖當場抓到（`[斷鏈]`／`[未對帳]`）。
   **為什麼會再犯**：自我指涉的重釘只能靠迭代，而迭代腳本本身沒有人在守。
3. **收斂重複時會把牙一起收掉。** P12 把兩支 hook 的判準收斂到共用層——收斂是對的，
   但**新 SSOT 弱於它取代的實作**（鐵律二明訂的絕對路徑外呼形態在 PS 側不擋）。
   **為什麼會再犯**：「同一份知識住兩個家」是明確的壞味道，於是收斂看起來一定是進步；
   而「收斂後鑑別力有沒有守住」需要**逐形態對拍**，那一步很容易被省掉。
4. **判準要治的病會搬到判準自己身上。** F2 發現 P6 的逐桶測試**迴圈跑被測模組自己的常數**
   ⇒ 把常數縮成單桶後測試仍 passed——**「分母被常數窄化」原封不動搬到測試裡**。
   **為什麼會再犯**：從被測模組 import 期望值在寫測試時最自然、也最省事。
5. **做了但不落磁碟＝沒發生。** 訴求 8 被 SA 判定為未見於任何交付面，而它其實做了——只存在於對話裡，磁碟上搜不到。
   **為什麼會再犯**：對話裡剛講完的事，主觀上與「已記錄」完全一樣。
6. **複審對象是移動標的。** 同一工作樹三次量測得三種結果（SA 實測）。
   **對策**：R86 複審前**宣告凍結點**，或讓複審在 worktree 快照上跑。

---

## §7 誠實劃界

- **Windows 側零覆蓋**：本輪一次都沒上 Windows 真機。
<!-- absent-if: measured-at=2026-08-12 host=Windows -->
- **GitHub CI 全紅**：`gh run list` 最新 push **6/6 failure，job `steps=0`、各 3 秒**＝帳務停擺
  ⇒ 有一整類未結缺陷（解鎖條件寫「要 Windows CI」）**結構上結不掉**。
- **本輪仍是加法輪**：護欄層總量上升（現查 §5.1），方向與 M1 相反。
- **四方複審的 rc 是時刻快照不是收輪憑證**（QA 自陳）：工作樹在複審期間持續被收尾窗口修改。
- **M3 的第三方注入面仍近乎為空**：既有鎖庫隨機 20 支的抽樣至今一次都沒做過。

---

## §8 禁止事項

1. 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准 `--allow-pg-extras`。
2. 🔴 不准任何毀滅性 git；並行包**連 `git stash create` 都不准**。
3. 不准為了讓紅變綠而刪測試／改成不比較／加 `skip`／放寬棘輪。
   本輪具體形態：`_REPIN_NET_CAP_SCHEDULE` 只准往下、只准追加；`MIN_TESTS` 是**下限**只准往上釘。
4. 🔴 等長跑時不准裸 `pgrep -f <字面>`、不准 `nohup <cmd> &`；
   **`echo "$(cmd) rc=$?"` 的命令替換會洗掉 `$?`** ⇒ rc 先存變數再印。
5. 🔴 **突變／注入實驗一律在拋棄式副本上做**，不要就地改 tracked 檔再還原
   （同輪 F2 這樣做過並自陳「共用工作樹下這是我不該冒的風險」）。
6. 🔴 **開工第一件事與收工最後一件事，都要重建保全點**：
   `S=$(git stash create); git tag -f R86-wip-$(date +%H%M) "$S"; echo "preserved=$S"`。

---

## §9 交給 R86 的待辦（R85／F1 四方複審收斂包）

1. 🔴 **訴求 2「護欄層單輪淨額 ≤ 0」在 R85 仍未達成，且不是沒去做。**
   F1 已窮盡去重面：兩份互相獨立的量測（機械普查與人工複核）都指出可用的重複判準在
   **量級上**就吃不掉本輪淨額，硬湊只能砍出真的洞。棘輪自己列的第三條出口
   （把 WHY 與史料搬出護欄層，最集中處＝`_GUARD_LINES_REPIN_LOG` 的理由欄）**尚未動用**，
   因為它必須改既有列 ⇒ 依 append-only 指紋與「淨減法只能由收尾單人窗口做」，
   只有單人窗口做得了。差額與逐項辯護見
   `docs/06_quality/CrossPlatform_R85_Guard_Repin_Evidence.md` §4。
   現查（讀 rc 不接管線）：
   `python tools/probe/guard_layer_dedup_census.py --details`
   ／`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`
2. 🔴 **`TestGuardLayerRatchet` 有兩支測試會紅，那是本輪的誠實狀態、不是壞掉。**
   `test_the_real_repin_log_stays_inside_the_cost_envelope` 與
   `test_appending_one_row_keeps_the_history_digest_stable` 兩支要求「R85 逐輪加總 ≤ 0」，
   而本輪加總為正 ⇒ 它們紅得正確。**不准靠改判準／加 skip 讓它們變綠**（那正是 ARCH-01
   立案時要防的形狀）；唯一出路是第 1 點那條。現查：
   `python -m unittest test_adr_xplat001_c1c2_lock`（於 `tools/tests/`）
3. 🔴 **`MIN_TESTS` 本輪由 F1 重釘，依 M3 仍是中途值**——F1 是複審後的收斂波，
   其修復本身**未執行**第三方複審 ⇒ 作者自證不計分，下一輪複審收斂後必須再釘一次。
   現查：`python tools/run_root_unittests.py`
