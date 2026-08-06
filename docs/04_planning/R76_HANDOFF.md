# R76 交棒任務書（跨平台相容性輪）

> **產出**：`5993f09`（單一 commit，67 檔／+6299 −762；前身 `a262369`，因回填 ONBOARDING 基線而 amend）。
> **平台**：Windows 11 Pro build 26200 真機。
> 🔴 **本輪 F-07 附註（不改寫史料，只標明不可採信的部分）**：本行原逐字宣告載具為「PowerShell 5.1」。
> 當回合實測：Claude Code 的 **PowerShell 工具是 pwsh 7.6.4（Core）**，`powershell.exe -NoProfile` 才是
> 5.1.26100.8875（Desktop）。R76 是否曾顯式外呼 `powershell.exe` **未留痕、無法複驗**，
> 因此本檔（與 §9 取證表「原生 PowerShell 5.1」那一列）凡涉及**引擎相依行為**的結論
> ——預設檔案編碼（utf-8 vs big5）、`.ps1` 語法解析結果、`$IsWindows` 之類 PS 6+ 專屬變數
> ——一律視為**未以 5.1 複驗**。與引擎無關的量測（rc、檔案內容、git、gh）不受影響。
> **本檔用途**：讓 R77 不必採信任何宣稱就能接手。凡「已通過」一律附當回合可重跑的指令。
> **體例沿用** `R75_HANDOFF.md`。

---

## 1. 收輪時的實測狀態

> 🔴 **R77 開場請自己重跑，不要採信本表。** 下表每一格都是我在 2026-08-05 深夜／08-06 凌晨於
> 主樹當回合真跑的輸出，**只對取得它的那個時點有效**。本 repo 已有判例：同一條指令、同一台
> 機器、相隔十幾分鐘，rc 由 0 翻 1（`CrossPlatform_R76_Scan_Findings.md` 附錄 A 第 1／1b 項）。

共用前綴（每個閘門都用這一段）：

```powershell
$r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
```

| 閘門 | 指令 | R76 收輪實測 |
|------|------|--------------|
| 根層 unittest | `& $p "$r\tools\run_root_unittests.py"` | `Ran 1979 tests in 282.300s`／`OK (skipped=43)`／**rc=0** |
| LOC budget | `& $p "$r\AutoClaude\tools\check_loc_budget.py"` | **rc=0**，另印 `[SPECIAL-WARN]` 2 支餘裕 ≤5 行（本輪新增的預警帶，見 §3） |
| 缺陷帳本一致性 | `& $p "$r\tools\check_defect_log_crossref.py"` | **rc=0**，兩則 warning（帳本體積逼近上限、19 筆已結列殘留待辦） |
| 未結列數 | `& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count` | **83／全部 134 列**（warn 86／fail 98，餘裕 15 筆）／rc=0 |
| 帳本保全稽核 | `& $p "$r\tools\archive_defect_log.py" --check` | **rc=0**（61 檔／977 個 ID／59 條歸檔索引 bullet 對 59 支 archive） |
| ONBOARDING 基線 | `& $p "$r\tools\sync_onboarding_baselines.py" --check` | **rc=0** |
| ONBOARDING 指紋 | `& $p "$r\tools\sync_onboarding_baselines.py" --check-snapshot` | **rc=0**（Windows 欄相符） |
| 腳本對等 | `& $p "$r\tools\check_script_parity.py"` | **rc=0** |
| 排程漂移 | `& $p "$r\tools\check_scheduled_task_drift.py"` | `status=ok`／兩支任務各「全部 7 項設定符合期望」／**rc=0** |
| NTFS 路徑 | `& $p "$r\tools\check_ntfs_paths.py"` | **rc=0**（27526 個 tracked 路徑／最長 142 字元） |

> 🔴 **上表量的是 `5993f09`；本輪還有第二個 commit（收尾包，見 §9）**，其中三格必然不同：
> 未結列數（＋3 列）、帳本 bytes、以及**根層 unittest 的下限**（`MIN_TESTS` 已由收尾包重釘，
> §9.1）。收尾包對同一批閘門重跑過一次，rc 逐項在該節。**兩組數字都只對各自的 commit 有效。**
> ⚠️ 另外：上表那個 `rc=0` 是在**交棒書尚未存在**時量的——交棒書自己後來讓兩道根層鎖轉紅
> （`DEF-101-868`），這正是「.md 也在閘門掃描面內」的實證。

工作樹與帳本體積（現查指令附後，勿採信數字本身）：

- `git rev-parse HEAD` ＝ `git rev-parse origin/main` ＝ `5993f09…`；`git status --porcelain` 零行。
- 帳本主檔 `docs/06_quality/AutoSDD_Defect_Log.md` **252,113 bytes**（warn 245,760／fail 262,144，
  餘裕約 9.8KB）。現查：`(Get-Item "$r\docs\06_quality\AutoSDD_Defect_Log.md").Length`。
  🔴 **歸檔不會降低未結列數**（那 83 筆在結構上不可搬），bytes 與列數是兩條各自獨立的線。

### 1.1 🔴 AutoClaude pytest：本機數字與出廠基線**不是同一件事**（R77 先讀這段再下判斷）

**我沒有跑 AutoClaude pytest**（約 100 秒，且跑了也不能直接與基線比對）。原因是一個**環境事實**：

| 面 | 值 | 我當回合的取證 |
|---|---|---|
| 主 `.venv` 現在的 PG extras 狀態 | **present** | `& $p -c "import sys; sys.path.insert(0,'tools'); import sync_onboarding_baselines as s; print(s.pg_extras_state())"` → `present`；逐套件實查 `psycopg2-binary 2.9.12`／`pgvector 0.5.0`／`sqlalchemy 2.0.51`／`alembic 1.19.0`／`asyncpg 0.31.0` 皆已安裝 |
| 本機因此量到的 pytest | `4017 passed／160 skipped`（**引用本輪其他包的量測，我未當回合重跑**） | 重跑指令見下 |
| ONBOARDING §7 表② 的**出廠基線** | `3919 passed／224 skipped` | `--check-snapshot` 當回合印出 `[autoclaude-pytest-snapshot:] {'passed': 3919, 'skipped': 224}`／rc=0 |

**兩個數字都對，量的不是同一個環境。** 表② 的定義（ONBOARDING §7 逐字）是「只裝
`.[dev,notifications]` 的乾淨 venv」，provenance 錨明載 `pgextras=absent`。裝了 PG extras 之後，
一批原本 skip 的測試會轉成 pass ⇒ `passed` 上升、`skipped` 下降，**這是預期行為，不是基線壞掉**。

```powershell
Push-Location "$r\AutoClaude"; & $p -m pytest tests\ -q; Pop-Location   # 本機現況數字
```

🔴 **R77 必須知道的連鎖後果（我當回合實測，本輪未處理）**：`sync_onboarding_baselines.py`
的回填腳（`--write --with-slow`）在**可 import psycopg2／sqlalchemy 的直譯器上會 rc=2 拒跑**
（判準＝`pg_extras_state()`，實測現在回 `present`）。也就是說：**下一次要回填表② 的人，
用這支主 `.venv` 會被擋**。正解是另建只裝 `.[dev,notifications]` 的乾淨 venv；
❌ **不准用 `--allow-pg-extras` 繞過**——`useMacWin.md` 明文寫著那等於悄悄改掉「出廠環境」
的定義，而且沒有任何機械物會察覺這個語意變更。

### 1.2 🔴 雲端狀態：**兩件事，不要合併成一句**

> **這兩件事發生在同一天、同一個 sha 上，結論卻相反。把它們寫成一句話，任何一邊都會失真。**

**(甲) push 軌五支全部 completed／success。** 我當回合逐 workflow 現查
（`gh run list --workflow <wf> --event push --limit 1 --json headSha,conclusion,status,createdAt`）：

| workflow | 對 `5993f09` 的 push run | 結論 |
|---|---|---|
| `root-infra-ci.yml` | 2026-08-05T15:44:00Z | success |
| `windows-compat-ci.yml` | 同上（run id `31021778224`） | success |
| `macos-compat-ci.yml` | 同上 | success |
| `autoclaude-ci.yml` | 同上 | success |
| `aisdlc-sdd-ci.yml` | 同上 | success |
| `autoclaude-mutation-on-change.yml` | 未為 HEAD 觸發（源碼變動軌，`paths:` 過濾） | 不適用 |

**(乙) 21 分鐘後的一次手動 dispatch，三個 job 全部因 GitHub Actions 帳務／消費上限而未啟動。**
掌舵者於 16:05:50Z 跑 `gh workflow run windows-compat-ci.yml --ref main`（run id `31023606162`，
同一個 `headSha=5993f09`），三個 job 全 `conclusion=failure`、**`steps` 長度為 0**、2~4 秒結束。
我當回合取 annotation 逐字，三個 job **同一則訊息**：

```
gh api repos/:owner/:repo/actions/runs/31023606162/jobs \
  --jq '.jobs[] | "\(.id) | \(.name) | conclusion=\(.conclusion) | steps=\(.steps|length)"'
# 92366299034 / 92366299162 / 92366311414 皆 conclusion=failure、steps=0

gh api repos/:owner/:repo/check-runs/92366299034/annotations
# failure | The job was not started because recent account payments have failed
#           or your spending limit needs to be increased. Please check the
#           'Billing & plans' section in your settings
```

⇒ **Actions 帳務在 15:44Z 與 16:05Z 之間被卡住。這是 `DEF-101-081` 同型復發。**

#### 🔴 R77 的辨識方法（不要把它誤判成自己弄壞的）

帳務未解前，**任何 push 都會看到雲端紅，而那個紅與程式碼無關**。兩個特徵同時出現即可斷定：

1. job 的 **`steps` 是空陣列**（工作根本沒開始，不是跑到一半失敗）；
2. annotation 訊息含 `payments have failed` 或 `spending limit`。

```powershell
gh run list --workflow <wf> --limit 1 --json databaseId,conclusion
gh api repos/:owner/:repo/actions/runs/<runId>/jobs --jq '.jobs[] | "\(.id) steps=\(.steps|length)"'
gh api repos/:owner/:repo/check-runs/<jobId>/annotations
```

**在確認是這個形態之前，不要動任何程式碼去「修」它**——本 repo 已有判例（R58 整輪作廢的根因
之一就是拿假前提撐出規模）。

---

## 2. 掌舵者三個系統問題的當前答案

### Q1｜`AutoClaude_Nightly` 是什麼、還要跑多久？

**性質是混合的**，兩半的終點完全不同：

| 半 | 內容 | 有沒有終點 |
|---|---|---|
| 觀察期採集 | mutation／AC4／observability GA／drift GA 四軌進帳 | **有**（四軌全綠後由 PM 拍板降頻） |
| 常態回歸 | `local_ci_gate`／`perf`／`chaos`／`pg-e2e` 等 stage | **沒有**（這是常態回歸，不是階段性測試） |

**四軌現況**（`AutoClaude/.g0_readiness.json` 的 `generated_at` ＝ `2026-08-05T14:32:54Z`；
下表三支 `--json` 是我當回合在 `cwd=AutoClaude` 重跑的，rc 皆**未經管線**取得）：

| 軌 | 現況 | rc |
|---|---|---|
| mutation | `pass=true`（`should_lock=True`；`.g0_readiness.json` 引用，我未重跑該軌工具） | 未量 |
| AC4 | `status=ready`／`green_streak=45`（門檻 14）／`staleness_days=0` | **0** |
| observability GA | `status=sparse`／`green_streak=45`（門檻 30）／**`window_span_days=58`（上限 40）**／`max_gap=12 天` | **1** |
| drift GA | `status=sparse`／`green_streak=29`（門檻 30）／**`window_span_days=65`（上限 40）**／`max_gap=12 天` | **1** |

```powershell
Push-Location "$r\AutoClaude"
& $p "tools\observability_ga_check.py" --json ; "obs RC=$LASTEXITCODE"
& $p "tools\drift_log_ga_check.py"      --json ; "drift RC=$LASTEXITCODE"
& $p "tools\ac4_progress_check.py"      --json ; "ac4 RC=$LASTEXITCODE"
Pop-Location
```

#### 🔴 舊的「差 2 筆」已經不成立——不是進度倒退，是**判準改了、量的東西換了**

R75 交棒書寫的是「drift GA 差 2 筆，最快 2026-08-06 夜」。本輪 PKG-D（依 R76-13）**收緊了
兩支 GA 判準**：除原有的「連續綠筆數 ≥ window」外，新增 ①證據新鮮度（`staleness_days ≤ 30`）
與 ②**窗內連續性**（last-30 筆的日曆跨度 ≤ `window × 4/3` ＝ 40 天）。

**舊判準量錯了東西**：它只數筆數，於是 observability 用「30 筆橫跨 58 個日曆天、窗內最大有
12 天全黑」宣告「30 天零事件 GA 取證通過」。**30 筆不等於 30 天**——一段連續 12 天沒有任何
採集的空窗，正是觀察期本來要排除的情形。收緊之後兩軌由「已達標」翻回 `sparse`，
**這是判準第一次真的在說話，不得為了讓數字好看而放寬**。

#### 新的可判定終點（我當回合以判準公式對現有帳本逐日試算）

綁住兩軌的已不再是 `green_streak` 而是 **span**，所以「再等兩天」這個心智模型整個作廢：

| 軌 | 還需連續進帳幾晚 | 最早達標日 |
|---|---|---|
| observability | **16 晚** | **2026-08-21**（屆時 last-30 span＝39） |
| drift | **17 晚** | **2026-08-22**（屆時 last-30 span＝40，恰好卡在上限） |

試算配方（R77 請自己重算，不要抄上表）：

```powershell
Push-Location "$r\AutoClaude"
& $p -c "
import sys, json, datetime as dt
sys.path.insert(0,'tools'); import ga_window as g
for name,path in (('obs','.observability_history.jsonl'),('drift','.drift_log_history.jsonl')):
    days=sorted(g.parse_ts(x).date() for x in map(json.loads, open(path,encoding='utf-8')) if g.parse_ts(x))
    sim=list(days); d=days[-1]
    for n in range(1,90):
        d+=dt.timedelta(days=1); sim.append(d); w=sim[-30:]
        if (w[-1]-w[0]).days+1<=40: print(name,d,'after',n,'nights'); break
"
Pop-Location
```

**前提是每晚 22:30 排程不漏跑——中間漏一晚就往後推**，因為連續性本身現在就是判準。
⚠️ **在兩軌轉綠之前不得降頻**：每週採集結構上永遠滿足不了「last-30 落在 ≤40 個日曆天內」。
拍板時點因此順延；詳見 `docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md` §0 的 R76 全域訂正塊。

### Q2｜`AutoClaude_WindowsSmoke` 是什麼、能不能結束？

**目的**：Windows 側 88 秒的 tripwire（12 個 PASS 點），讓「push 前／離線時有沒有壞」在
一分半內有答案。要分清兩個東西——這件事此前被混為一談，正是它一直問不出答案的原因：

| 標的 | 性質 | 有退出判準嗎 |
|---|---|---|
| **腳本** `tools/windows_smoke_local.ps1` | 本地鏡像，價值與雲端 CI 活不活著無關 | **沒有，永久保留（設計如此）** |
| **排程任務** `AutoClaude_WindowsSmoke` | R60 為「雲端 CI 帳務停擺期間零執行級訊號」而建的**補償控制** | **有**（三條 E1／E2／E3，寫在該腳本的退出判準段） |

**E3 本輪被重寫**，因為舊版**結構上不可滿足**：舊 E3 逐字要求「移除 smoke 後
`check_scheduled_task_drift.py` 回 rc=0」，而該工具的期望值 SSOT 同時列著兩支任務
⇒ 一旦執行 E3 自己授權的動作，判準必然轉紅。新版改為只量「執行完該動作之後還存在的東西」：
`AutoClaude_Nightly` 存在，且**逐任務**欄位 `present=true`／`drifts` 為空（刻意不讀整支工具的 rc）。

#### 🔴「唯一卡點是一條需要提權的指令」＝哪一條：**已結案**

那條指令是 **`tools/install_windows_nightly.ps1`**（住在 **monorepo 根層** `tools/`，不是 `AutoClaude/`）。
它需要系統管理員權限才能改排程設定。**掌舵者已於本輪執行完畢**，漂移已清、smoke 已移到 21:30。
當回合取證：

```powershell
& $p "$r\tools\check_scheduled_task_drift.py"   # → status=ok，兩支任務各「全部 7 項設定符合期望」，rc=0
Get-ScheduledTask | Where-Object TaskName -like 'AutoClaude*' | Select-Object TaskName,State
```

連帶處置：`AutoClaude/tools/run_local_nightly.ps1` 內對 `status=drift` 的具名豁免已於本輪移除
（白名單只剩 `ok`／`skip`）——**豁免的解除條件已達成、豁免卻仍在生效**，這是本輪抓到的同族三例之一。

#### 🔴 **處置：撤回退場建議。smoke 排程維持每日，不得退場。**（2026-08-05 16:05Z 之後）

本輪一度得出「三條全滿、可以開始談退場」的結論。**那個結論在寫下時成立，現在不成立**——
**E1 當場失效**，原因是外部事件（見 §1.2 (乙)）：

E1 逐字要求「雲端主通道活著：`windows-compat-ci` 近 30 天內有 ≥ 20 個 run，
且其中**零筆** conclusion 屬 billing／startup_failure 類」。
現在**確定有一筆**：run `31023606162` 的三個 job，annotation 逐字指名
`payments have failed`／`spending limit`。⇒ **E1 的「零筆」條件已破，三條不再全滿。**

> **誠實劃界**：我當回合量到近 30 天內共 60 個 run（failure 49／success 11），
> 但**沒有**逐 run 去驗那 49 筆各自屬不屬於 billing 類——多數是前幾輪的程式碼紅。
> 我能斷定的只有「**至少一筆**是 billing 類」，而 E1 要的是零筆，一筆就夠推翻它。
> R77 若要精確分類，配方＝對每個 failure run 取 jobs 看 `steps` 是否為空陣列。

#### 🔴 這反而是補償控制**設計正確的正向實證**

`AutoClaude_WindowsSmoke` 的立案理由（R60，`DEF-101-081`）就是「雲端 CI 帳務停擺期間，
Windows 側零執行級訊號」。**那個情境此刻正在重現**——而排程還在跑，所以 Windows 側仍有每日
真機訊號。這一次意外驗證了一個設計選擇：

> **E1 綁在「主通道活性」，而不是綁在「smoke 發現數」。**

如果當初把退出判準寫成「smoke 連續 N 天零發現就可以撤」，這支排程早就被撤掉了——
而它被撤掉的時點，恰好會是它最有價值的時點（主通道剛好死掉的那一天）。
**「零發現」只代表這一層看不到那一類缺陷，不代表沒有東西可發現。**
該腳本的退出判準段自己已經寫過這個論證，本輪把它從論證變成了實證。

#### R77 若要重新評估，逐條現查（三條的顏色是會漂移的量測值，本檔刻意不快照）

```powershell
gh run list --workflow windows-compat-ci.yml --limit 60 --json createdAt,conclusion,event,status  # E1
& $p -m unittest discover -s "$r\tools\tests" -p test_smoke_ci_sync.py                            # E2
& $p "$r\tools\check_scheduled_task_drift.py" --json                                              # E3（讀逐任務欄位）
```

三條全成立才可移除該排程任務；**任一條未取證就不算成立**（「沒去查」不等於「已通過」）。
移除本身是掌舵者的決定，且退場是一輪 code 工作（見該生命週期報告 §5 D-4），不是刪個工作了事。

⚠️ **`docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md` 的 R76 註記寫著「3 條全數達標」，
該句自 2026-08-05 16:05Z 起已失實。** ✅ **已由 R76 收尾包就地處置**（2026-08-06）：該檔 §0
新增第二個訂正塊（事件取證＋三處結論的影響表＋量測配方補一步），並在一頁結論表、§2.2.3、
§2.2.6 段 ② 三處各加一行指路；**歷史原文一字未改**。同一份處置也寫進了
`tools/windows_smoke_local.ps1` 判準段之後的「E1 現況欄」（記事件不記顏色）。

### Q3｜224 支 skipped 是什麼？

**一句話**：224 支裡約七成是「該補的洞」（兩平台與全部 workflow 都沒有任何通道跑到），
本輪用兩行 CI recipe 修改把絕大多數補回；剩下的少數是真正健康的條件式跳過、可辯護地永久
不覆蓋（付費 `claude` CLI ＋巢狀 session 必死結）、以及誠實補不了的少數幾支。
**逐類支數與每一格的實測憑證見 `docs/06_quality/Skipped_Test_Inventory_R76.md` §6／§7，本檔不重複**
（那份文件自己記載了初稿估算與實測的三處差異）。

#### 🔴 本輪最重要的訂正：**「需要 PG」不等於「沒有 PG」**

我（舵手）一度誤稱「本機沒有 PostgreSQL service」，並用這個假前提解釋「那批只能等雲端」。
**該前提為假，掌舵者當場糾正**。實查：本機一直有一個長駐健康的容器。

```powershell
docker ps --format "{{.Names}} | {{.Image}} | {{.Status}}"
# → autoclaude_pg | pgvector/pgvector:pg18 | Up 3 days (healthy)
```

**完整配方逐字寫在這裡，R77 不必重新發現**（`Skipped_Test_Inventory_R76.md` §4.7.1 同源）：

```powershell
# 一次性：cwd=AutoClaude
uv pip install -e '.[postgres,pgvector]'      # 缺 sqlalchemy 時症狀是 error 而非 skip
# 四個環境變數
$env:AUTOCLAUDE_DB_DSN      = 'postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/<DB>'
$env:AUTOCLAUDE_TEST_PG_DSN = $env:AUTOCLAUDE_DB_DSN
$env:AUTOCLAUDE_ALLOW_INSECURE_DB = '1'
$env:SD07_REAL_PG_E2E_ENABLED     = 'true'
python -m pytest tests/ -q -p no:randomly
```

🔴 **四步缺一即仍 skip**，且 `alembic upgrade head` **不可用 `alembic stamp` 代替**：
長壽開發 DB 的 `alembic_version` 停在 head 卻沒真跑過 0010，會讓三支 `backfill_legacy_fk` 紅
（那三支紅是**正確訊號**，不是本輪弄壞的——是從未被執行過所以從未被看見的）。
`pg_real` 那幾支另需 `seed_kb.py --mock-pg-seed`，且**語料與 ground truth 必須同一次 seed**
（ground truth 記的是列 UUID，每次 seed 重新隨機產生）。

**版本差揭露（不得互相外推）**：本機容器是 **pg18**（`show server_version;` → 18.4），
雲端 `pg-contract`／`pg-e2e-nightly` 與 `docker-compose.ci.yml` 都是 **pg17**。
本輪複驗者曾以 pg17 起容器重跑同一射程，得到逐位相同的結果 ⇒ **目前沒有已知行為差，
但那是量測不是推論**，新增任何 PG 相關斷言時仍須各量一次。

---

## 3. 本輪做了什麼（詳情一律見具名證據檔，本檔不重複）

**流程**：十二路深掃（Scan-A~T 十一維 ＋ Q3-Skipped 專項）→ 去重分級 →
解死結包 ＋ 七個修復包 ＋ 收斂包 → **四方獨立複審**（Architect／SA／SD／QA **全部
`APPROVE-WITH-CONDITIONS`**）提 13 筆 blocking → 對抗式複驗**證偽 1 筆** → **12 筆全部修畢**
→ 技術債收尾包 → lint 修復包 → 回填基線包。

| 項目 | 落點 |
|---|---|
| 掃描發現、去重帳、假陽性剔除、修復序、成熟度 M1~M6 表 | `docs/06_quality/CrossPlatform_R76_Scan_Findings.md` |
| 224 支 skipped 逐類盤點、本機 PG 補測、pg18／pg17 揭露 | `docs/06_quality/Skipped_Test_Inventory_R76.md` |
| 排程 Job 生命週期裁決（含本輪 §0 全域訂正塊） | `docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md` |
| 缺陷列 | `docs/06_quality/AutoSDD_Defect_Log.md`，本輪新列自 `DEF-101-832` 至 `DEF-101-867`（🔴 **現查配方刻意不寫 ID 正則**：任何「不完整的 ID 字面」都會被 `tools/tests/test_defect_id_reference_integrity.py` 判成指向空號的斷鏈引用，而改寫成「ID 前綴＋英文字母占位」那種形態則會擠爆同一支測試的占位站點上限（後門規模鎖）——本表原先兩種都踩過，收尾包實測各紅一支。**要示範這兩種寫法就會再紅一次，所以此處只描述、不逐字寫出**。改以輪號查：`Select-String -Path <帳本> -Pattern 'R76' -Encoding utf8`） |
| 平台面積縮減 ADR | `docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md` |

**技術債清除**：刪掉孤兒腳本 `AutoClaude/tools/reschedule_g0_gatecheck.ps1` 並同步清理它散落的
登記站點（含兩處 `paths:`、三檔散文註記與四個實測型下限）。教訓寫在
`CrossPlatform_R76_Scan_Findings.md` §5.7：**「刪一支孤兒」的真成本不在檔案本身，在它被登記過幾次；
沒現查就估成本，會系統性低估**——實際耦合面比原估的多一倍。

**新增的機械物**（本輪最有價值的兩條，由 R76-00 直接推導，見 §4）：
Scan-H 必跑項 **⑥「新鎖要求的補救動作，是否會違反另一道既有硬閘？」**
與 **⑦「同一支工具內多道檢查的早退順序，是否會遮蔽後面檢查的訊號？」**，
兩條的立案理由與落地形態逐字寫在 `CrossPlatform_R76_Scan_Findings.md` §7。

---

## 4. 本輪最重要的一般化規則（升為機械物的那幾條）

### 4-1 🔴 **兩道各自正確的鎖，可以在交界處產生不可滿足的狀態**（新的死結形態）

> **A 鎖要求你加一行，B 鎖禁止你加那一行。這不是「鎖壞了」，是它們的射程在交界處相撞。**

**立案實證（R76-00，肇事者是掃描報告自己）**：`CrossPlatform_R76_Scan_Findings.md` 一落地，
就因為符合 `CrossPlatform_*.md` 治理文件命名慣例而未登記，讓 `check_defect_log_crossref.py`
**當場 rc=1**（該 rc 有兩個硬消費者：pre-push 的快層守門迴圈與 `root-infra-ci.yml`）。
而工具自己教的第一條修法是「在 `_GOVERNANCE_DOCS` 補一筆」＝**+1 行**，
該檔當時是 **1474/1474（餘裕 0）**，加一行當場觸發 LOC violation。

- **機械物住哪**：Scan-H 必跑項 ⑥，規格寫在
  `docs/06_quality/CrossPlatform_Scan_Dimensions.md`（Scan-H 段）；
  落地形態＝凡「錯誤訊息教人往某支檔加內容」的鎖，其測試須斷言該檔在 `check_loc_budget` 下
  有 ≥N 行餘裕（N＝該修法的行數成本），否則訊息必須同時給出零成本出口。
  預警面由 `AutoClaude/tools/check_loc_budget.py` 的 `[SPECIAL-WARN]` 帶承接
  （本輪新增，rc 不變，只把「第一個訊號就是紅」變成「先有一段黃」）。
- **🔴 它抓不到什麼（誠實劃界）**：⑥ 只覆蓋「錯誤訊息明文教人加內容」這一種形態。
  兩道鎖以**別的方式**相撞（例如 A 要求某檔存在、B 要求該目錄檔數不增）**不在射程內**；
  而且它是一條**維度必跑項**（人執行的檢查清單），不是每次 push 會跑的 unittest ⇒
  **漏做零訊號**。把它上成自動判準是 R77 可做的事。

### 4-2 🔴 **同一支工具內多道檢查的早退，會遮蔽後面的訊號，而遮蔽方向是「看起來變乾淨」**

`check_defect_log_crossref.py` 在具名治理文件那一關就 `return 1` 早退，於是 R76-04 那
**8 筆「承接者是已結束輪次」的孤兒列警告整批消失**（實測輸出總共只剩 2 行）。
缺陷沒有消失，只是沒有人看得到它——**這比 rc 直接是紅更危險**，因為紅有人修、消失沒人查。

- **機械物住哪**：Scan-H 必跑項 ⑦（同一份維度定義檔）。落地形態＝該類工具改為
  「全部檢查跑完再彙總 rc」，或在早退處印一行「尚有 N 道檢查未執行」；
  測試以**雙缺陷注入**驗證兩者都被列出（單缺陷注入抓不到這個形態）。
- **🔴 它抓不到什麼**：同上，是必跑項不是自動判準。且它只問「早退有沒有遮蔽」，
  不問「被遮蔽的那一項本身有沒有鑑別力」——兩件事要分開查。

### 4-3 🔴 **先問清楚「這個判準量的是筆數還是天數」**（GA 那一族的教訓）

observability GA 用「30 筆」宣告「30 天零事件取證通過」，而那 30 筆實際橫跨 58 個日曆天、
中間有 12 天全黑。**筆數是天數的 proxy，而 proxy 在採集不連續時會系統性高估**，
且高估方向正好是「看起來已達標」。

- **機械物住哪**：`AutoClaude/tools/ga_window.py`（本輪由兩支 GA 工具的 112 行複本抽出的共用層，
  兩支各以 `assertIs` 鎖住同一個物件），常數 `WINDOW_SPAN_MAX_FACTOR = Fraction(4, 3)` 與
  `STALENESS_MAX_DAYS = 30` 各自帶 WHY；判準函式 `window_calendar_span()`／`evaluate()`。
- **🔴 它抓不到什麼**：`ga_window.py` 只服務 observability／drift 兩軌。
  **其他任何以「筆數」代言「時間跨度」的判準都不在射程內**，本 repo 沒有普查過還有幾處。
  另外 span 判準本身也擋不住「每晚都跑但每晚量的是同一份 stale 資料」——
  新鮮度那一半由 `staleness_days` 管，兩者要一起看。

---

## 5. 交給 R77 的事（依優先序，每筆附可直接執行的解鎖條件）

### 5-1 🔴 首選架構標的：**M6 — 讓量測配方只有一個可執行的家**

四方在成熟度上唯一完全一致的一句是：**「閘門全綠」與「成熟」無關**
（R75 的 12 筆 blocking 有 8 筆是閘門自己沒鑑別力；R76 存活的 12 筆**沒有一筆**會被任何現有
閘門攔下）。六條判準 M1~M6 的定義、量測配方、本輪實測基線與門檻見
`CrossPlatform_R76_Scan_Findings.md` §R76-MATURITY —— **六條現況全部未達標**。

Architect 的判斷是 **M6 槓桿最大，且有現成樣板可照抄**：本輪已經證明「量測配方寫成散文」
與「量測配方寫成可執行物」的差別有多大——`Skipped_Test_Inventory_R76.md` §4.7.1 那個
三行配方，把「這批只能等雲端」直接翻成「本機當場多跑 157 支並曝出 4 支從未執行過的紅」。
**解鎖條件**：把本檔 §2 三個 Q 裡每一條現查指令收斂成單一可執行載具（一支腳本／一支測試），
使「這個數字怎麼來的」不再有第二個家；驗收＝盤點文件內「零覆蓋」欄為 0，且每一格都有當輪實跑 rc。

### 5-2 SA 指出「一輪內做得完」的兩條（做完會讓失實宣稱密度自己掉下來）

| 條 | 內容 | 解鎖條件 |
|---|---|---|
| **B** | **散文型宣稱歸零**：凡會漂移的量（筆數、行號、顏色、日期）不得寫成散文常數，只留現查配方 | 對根 `CLAUDE.md`／`ONBOARDING.md`／本檔以外的活治理文件逐份掃一遍，把每一個裸數字換成「指令＋『一律現查』」；驗收＝隨機抽 10 個數字，每個都能在文件裡找到它的量測指令 |
| **D** | **改了尺就要同步改讀數**：判準門檻一動，所有引用該門檻結論的文件必須在**同一個 commit** 內更新 | 本輪 GA 判準收緊即為實例（`Scheduled_Jobs_Lifecycle_Review_R75.md` 有三處要同步）；驗收＝加一支鎖，斷言「凡引用 `ga_window` 常數的 .md，其結論句必須帶當輪重算指令」 |

M2 的量測配方是「每輪複審抓到的失實宣稱筆數 ÷ 該輪新帳本列數 × 100」，本輪基線落在
24〜48/100，門檻是 3/100 —— **差一個數量級**。B/D 兩條直接打在分子上。

### 5-3 帳本裡明文承接 R77 的列（現查，勿抄本節）

```powershell
& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count
Select-String -Path "$r\docs\06_quality\AutoSDD_Defect_Log.md" -Pattern 'R77' -Encoding utf8
```

當回合查到的三筆主要承接列：

- **`DEF-101-810`**（R75 交棒殘餘，R76 改派 R77）：`run_local_nightly.ps1` 無頂層
  `param()`／`-Help`，`--help` 會直接開跑 7 stage nightly（`.sh` 側同型缺口早已修好＝雙平台不對稱）。
  **解鎖條件**（帳本內逐字寫著，可直接照做）：該檔頂端補 `param([switch]$Help)` ＋
  `if ($Help) { 印用法; exit 0 }`，未知參數 rc=2，並在
  `AutoClaude/tests/tools/test_run_local_nightly_static.py` 併入回歸鎖，形狀比照 `.sh` 側既有兩支。
- **`DEF-101-856`**（R76 收斂包彙整的六項 `not_done`）：⚠️ **該列的第 ① 項已經過期** ——
  它寫「`reschedule_g0_gatecheck.ps1` 只標 DEPRECATED 未刪」，而本輪後續的技術債收尾包
  **真的把它刪了**（實測 `Test-Path` → `False`）。
  ✅ **已由 R76 收尾包就地訂正**（2026-08-06，狀態欄追加訂正、原文一字未改）：**R77 只要做剩下五項**，
  其中「死碼候選 `AutoClaude/tools/verify_token_guard_e2e.py`」實測**檔案仍在**。
  🔴 順帶：這是「**同一輪的兩列互相矛盾而零訊號**」的實例，可行性評估與 R77 的收斂設計
  見 `DEF-101-867` ／ `CrossPlatform_R76_Scan_Findings.md` §R76-FIX-6（結論＝**本輪刻意不落地**，
  唯一可機械化的代理判準實測訊噪比只有約 25%）。
- **`DEF-101-863`**：skip 理由的可操作性（把「未啟用」與「缺件」在**輸出面**分開）。
  本輪只落到踩到的那一支檔。**解鎖條件**＝全樹 224 支 reason 逐支套用同一形態，
  並加一支鎖斷言「(c)(d) 類 reason 必須含可執行指令或明示旗標名」。

### 5-4 已知的 provenance 盲維度（我當回合實測，本輪未修）

`tools/sync_onboarding_baselines.py` 的 provenance 記 `measured-at`／`host`／`docker`／`pgextras`
四項，但**不記 `SD07_REAL_PG_E2E_ENABLED`**，而該變數同樣會左右 pytest 計數
（本輪實測有 3 支因此在 pass 與 skip 之間移動）。
⇒ 兩個環境的 provenance 可以四項全同，pytest 數字卻不同，而**沒有任何東西會說話**。
**解鎖條件**：在 `env_provenance()` 那一組欄位加第五格（值域 set／unset），
並讓 `--check-snapshot` 在該格變動時判 presumed stale；驗收＝設與不設各量一次，指紋必須不同。

### 5-5 🔴 **帳務恢復後的第一件事**（具名項目，附可直接執行的指令）

**現況**：push 軌五支對 `5993f09` 全 success（§1.2 (甲)），但 Actions 帳務自 2026-08-05 16:05Z
起卡住（§1.2 (乙)）⇒ **任何手動 dispatch 目前都會在 2~4 秒內以 billing 失敗告終，跑不了任何驗證。**

**本輪對 `windows-nightly-full` 的修復＝已入庫、但零次成功執行可以證明它修好了。**
背景：`shell: powershell` 的 run 本體被 runner 寫成無 BOM 暫存 `.ps1`，PS 5.1 以 ANSI codepage
誤讀繁中 ⇒ 該 step 自 R48 起**從未執行過一次**（雲端逐字 `ParserError`）。本輪把 run 本體改成
全 ASCII（中文 WHY 移到 step 上方註解）並加了鎖。**這是「已修、未經執行驗證」，
不得寫成「已修復」**——修的東西正好只有真跑一次才看得出來。

**解鎖條件（帳務恢復後照順序做，可直接執行）**：

```powershell
# ① 手動觸發一次，取得 windows-nightly-full 的真實執行證據
gh workflow run windows-compat-ci.yml --ref main
gh run list --workflow windows-compat-ci.yml --limit 1 --json databaseId,conclusion,status

# ② 確認不是又一次 billing 空轉（steps 必須非 0）
gh api repos/:owner/:repo/actions/runs/<runId>/jobs \
  --jq '.jobs[] | "\(.name) conclusion=\(.conclusion) steps=\(.steps|length)"'

# ③ 確認 nightly-full 那個 job 的 PS 步驟真的跑過且沒有 ParserError
gh run view <runId> --log-failed

# ④ 全綠後回頭關掉 issue #10
gh issue list --state open --search '深度回歸失敗 in:title'
gh issue close 10 --comment "<附 ③ 的 run URL 與逐字證據>"
```

### 5-6 本輪不得宣稱「雲端全綠」（誠實揭露，非遺漏）

本輪 R76-03 新增了一條收輪判準，我當回合跑了，**它是紅的**：

```powershell
gh issue list --state open --search '深度回歸失敗 in:title'
# → 10  OPEN  [P1] windows-nightly-full 深度回歸失敗   2026-08-03
```

背景：`continue-on-error` 讓 run 層 conclusion 顯示 success，job 層的紅只透過 GitHub issue 顯形，
而那個通道**零讀者** ⇒ 一筆真實 P1 橫跨數輪「雲端全綠」宣稱都沒被看見。
issue #10 **仍為 OPEN**（最後更新 2026-08-03），而關掉它的前提是 §5-5 的四步，
**而那四步現在被帳務擋住**。⇒ 在 §5-5 走完之前，**不得宣稱雲端全綠**。

R74 已為「沒等雲端結論就收輪」付過學費。本輪的 push 軌五支都等到 completed 才寫這份交棒書
（§1.2 (甲) 逐支附 run id 與時間戳），這一條紀律有守住。

### 5-7 近期會咬人的（不修會卡住下一個動這支檔的人）

- **`AutoClaude/CLAUDE.md` 卡在 400/400（餘裕 0 行）**、`tools/dev_start.py` 1999/2000（餘裕 1 行）
  —— 我當回合由 `check_loc_budget.py` 的 `[SPECIAL-WARN]` 段實測。
  正解順序寫在該工具的輸出裡：①刪死碼／抽共用模組 ②確認為不可壓縮的真實功能後，
  才在缺陷帳本具名理由調高。**不得為了讓修改通過而調高門檻。**
- **未結列 83／fail 線 98**，餘裕 15 筆；**帳本 252,113 bytes／fail 262,144**，餘裕約 9.8KB。
  兩條線互相獨立：歸檔只降 bytes，不降列數。
  🔴 **R76 收尾包又加了 2 列**（`DEF-101-866`／`DEF-101-867`）⇒ 上面兩個數字都已變動，
  一律現查：`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`、
  `(Get-Item "$r\docs\06_quality\AutoSDD_Defect_Log.md").Length`。
- 🔴 **主 `.venv` 現在 `pgextras=present` ⇒ 下一次回填表② 會被工具擋下**（`--write --with-slow`
  判 `pg_extras_state()` 為 `present` 即 **rc=2 拒跑**，見 §1.1）。**乾淨 venv 還在，直接用**：
  ```powershell
  $cv='C:\Users\wuwei\AppData\Local\Temp\claude\d--CursorProject-AISDCL-Agent\8ebee27b-8136-4523-8aa3-d57342bf3b0b\scratchpad\cleanvenv'
  & "$cv\Scripts\python.exe" -c "import psycopg2"   # 應 ModuleNotFoundError＝乾淨
  & "$cv\Scripts\python.exe" "$r\tools\sync_onboarding_baselines.py" --write --with-slow
  ```
  R76 收尾包當回合實測該 venv 為 Python 3.11.9、`psycopg2` 與 `sqlalchemy` 皆 absent。
  ⚠️ 它住在 scratchpad（session 專屬、會被清），**不在時就照 `.[dev,notifications]` 重建一個**，
  ❌ **不准改用 `--allow-pg-extras` 繞過**（§6 第 8 條）。
  ⚠️ 另注意：**只有 `--write --with-slow` 會被擋**；純 `--write`（回填 live 基線格，含
  `MIN_TESTS` 那一格）不受此限，主 `.venv` 可直接跑。
- ~~**`run_root_unittests.py` 的 `MIN_TESTS` 仍是 R74 自陳的「中途值」1819**~~
  ✅ **已由 R76 收尾包重釘**（判定理由、方向說明與 bug-injection 見 §9.1）。
  R77 收輪時**照樣要再釘一次**——這是每輪收尾的常規動作，不是一次性任務；
  判準與沿革逐字寫在 `tools/run_root_unittests.py` 的 `MIN_TESTS` 那一行的註記裡。

### 5-8 未修清單與「不該修」清單（現查來源，本檔不重複內容）

- **未修／必跑項未完成**：`CrossPlatform_R76_Scan_Findings.md` §6.2 逐維度列出十一維各自
  哪些必跑項沒做完，其中 **Scan-H 是本輪最大的方法論缺口**（31 個新增鎖類別只做了 4 支紅綠實測，
  其餘依該維度自己的判準一律 `NOT-PROVEN`）。
- **判定「不該修」／需授權的 10 類**：同檔 §5。🔴 **R77 動工前先讀這一節**，
  其中三類需要 PM signoff（UEP 5→4、改判 DEF-101-561③、護欄層 GLC 硬上限），
  **不得由執行者自行改判**；另有一類（把未橋接的 4 支 hook 橋進根層）會改動 PreToolUse deny 面，
  該檔自己記載過「hook 誤觸 deny 會把所有工具硬鎖死」的 P0。
- **🔴 下一輪應該是 macOS 真機輪**：同檔 §6.1 逐條列出 11 條「本輪全靠推論、零 mac 真機」的結論，
  並建議 macOS 輪開場第一件事就是把那 11 條逐條驗掉。
  🔴 **本輪（N-03）訂正本列的 M5 敘述——兩個方向寫反了，而且診斷也錯**：
  以逐題可重跑的注入矩陣在 Windows 真機重量，**mac→Win 是 0/10（0%）**、
  **Win→mac 是 5/12（41%；扣掉一筆「因為缺 encoding 而順帶命中」後為 4/12＝33%）**。
  也就是說**攔截率為零的是 mac→Win 那個方向**，不是本列原先寫的 80%。
  🔴 **「這一格只有 mac 真機補得了」也是錯的**：mac→Win 的 0/10 全部是**靜態掃描面**缺口
  （`os.getlogin`／`import pwd`／`os.fork`／`os.killpg`＋`SIGKILL`／`os.symlink`／`/tmp` 硬編／
  `os.chmod(0o755)`／POSIX 路徑串接 這一整類「對面平台專屬 API」零判準），
  **在 Windows 上就補得起來**，補完在 Windows 上就驗得到紅綠。
  真正需要 mac 真機的是**執行期**那一半（§6.1 那 11 條），與本格不是同一件事。
  把兩者綁在一起寫，等於把一件當下可做的事凍到「等 mac」——這與 §5-5 那筆
  「可拆成兩半卻被寫成單一解鎖條件」是同一個形態。

---

## 6. 禁止事項（R77 動工前先讀）

1. ❌ 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准跳過或註解掉失敗測試。
2. ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限（砸溫度計）。棘輪一律只准變少。
   **本輪特別點名：GA 的 `WINDOW_SPAN_MAX_FACTOR` 與 `STALENESS_MAX_DAYS` 不得放寬**
   ——它們剛剛第一次真的在說話，放寬等於把唯一有鑑別力的那一格關掉。
3. ❌ 不准把「尚未查核」寫成「已查核」。雲端結論、觀察期達標、平台覆蓋皆同。
   **本輪具體：issue #10 仍 OPEN、`windows-nightly-full` 的修復零次成功執行可佐證
   ⇒ 不得宣稱雲端全綠、不得把該筆寫成「已修復」（見 §5-5／§5-6）。**
   ⚠️ 同時**不准把帳務造成的紅算成程式碼問題**——辨識法見 §1.2（job `steps` 為空陣列
   ＋ annotation 帶 `payments have failed`／`spending limit`）。查清形態之前不要動任何程式碼。
4. ❌ **Windows 上禁用 Bash 工具**（根 `.claude/settings.json` 已註冊 PreToolUse 阻斷）；
   禁裸 `cd`（用 `Push-Location` … `Pop-Location` 同一次呼叫內成對）；
   算行數／搜尋一律用 Read／Grep 不經 shell。
5. ❌ **讀 rc 不准接管線**。本輪實例：`& $p tool.py --json | Select-Object -First 30` 之後讀
   `$LASTEXITCODE` 得到 **1**，去掉管線重跑同一支工具得到 **0** ——
   `Select-Object -First N` 提前結束管線會污染退出碼。**貼 rc 之前先確認那條命令沒接管線。**
6. ❌ 不准在訂正註記裡逐字抄錄被訂正的假話（樹裡不留假句子，有鎖在抓）。
   **同理：不要在文件裡快照「判準現在是什麼顏色」**——顏色是量測值，會過期，
   而過期的顏色不會有任何東西替它說話。只留不會過期的處置規則 ＋ 現查指令。
7. ❌ 不准在缺陷帳本列或表格 cell 內寫半形 `|`（會把欄位切壞、兩道閘門轉紅）。
   帳本列是索引不是報告（≤700 bytes），詳情進具名證據檔。
8. ❌ **不准用 `--allow-pg-extras` 繞過 `sync_onboarding_baselines.py --write` 的拒跑**
   （見 §1.1）。工具拒跑是設計，不是障礙。
9. ⚠️ 多 agent 同樹作業時，看到與自己改動無關的紅先 `git status` 核對歸屬，
   不要算成自己的、也不要去修別人的檔。**任何「全套 rc=0」只對取得它的那個時點有效**，
   收輪者必須在所有包停工後於主樹重跑一次。

---

## 7. R76 自身的失誤紀錄（不隱藏，這一節是本檔的誠信擔保）

### 7-1 🔴 舵手（我）誤稱「本機沒有 PostgreSQL service」，並用它解釋 224 支 skipped 為何不變

被掌舵者當場糾正。**後果不是說錯一句話而已**：那個假前提會把「152 支只能雲端驗」寫進收輪敘述，
而實際情況是——本機一設 DSN ＋ 裝 extras 就當場多跑 **157 支**，並曝出 **4 支從未被執行過的真紅**
（3 支＝開發 DB 沒真的 migrate 過、1 支＝ground truth 與語料不是同一次 seed）。
也就是說：**假前提會讓一批真缺陷繼續隱形，而且沒有任何閘門會發現它們隱形著。**

**形態＝根 `CLAUDE.md` 鐵律四「宣稱先於查證」**，只是這次的標的從權威源換成**執行環境**。
對策不變：任何「已驗證／已達標／只能在 X 驗」的宣稱，都要附當回合真跑的輸出
（`docker ps` 就能推翻它，成本一秒）。

### 7-2 🔴 舵手自寫的 PowerShell 驗證迴圈用了 `$a[1..0]`

PowerShell 對反向範圍會**反向展開**（`1..0` 得到 `1,0`），等於把腳本路徑當參數又傳了一次
⇒ 三道其實是綠的閘門回報 **rc=2**。

**教訓**：〈Windows 側單一載具原則〉治的是「選錯 shell」，**治不了「在對的 shell 裡現寫一段沒驗過的碼」**。
這正是 Architect 提 M6 的立案實證——**量測配方只要還住在「當場現寫」裡，它就會用它自己的 bug
去污染被量的東西**，而且污染方向不可預測（這次是假紅，下次可能是假綠）。

### 7-3 🔴 收斂包自陳「11 道閘門全綠」，實際有兩道是紅的

由後續的修復包（第三方）重跑抓出：

| 閘門 | 實測 | 誰造的 | 為何沒被發現 |
|---|---|---|---|
| `python tools/run_root_unittests.py` | **rc=1**（標記 stale） | 本輪 | 該包只跑了自己那支測試檔，沒跑整棵根層閘門 |
| `ruff check tools/` | **rc=1**（3 筆 E501） | 本輪 | **整輪無人跑過這一道**，也不在舵手親驗的那 7 道快閘門裡 |

兩筆都不會被 pytest 或缺陷帳本工具看見。**教訓：自述的閘門結論要由第三方重跑**
——這正是成熟度 M3「作者自證不計分」那一條的直接證據。立帳 `DEF-101-858`／`DEF-101-864`。

### 7-4 🔴 技術債收尾包把已刪檔名用**反引號**寫在錨定行上

抽取器讀的正是該行的反引號 `.ps1` token ⇒ 等於**把剛刪掉的檔又登記回去**，
根層 unittest 當場紅。它自己抓到並修了。

記在這裡是因為這是「**訂正註記自己製造新問題**」的又一實例，
而且與本輪另一筆同形態（ARCH-01 的修法在 `#` 註解裡逐字寫出姊妹檔的標記字串，
而兩支掃描器的取標記函式只認 COMMENT token ⇒ 「提到」與「登記」在機器眼中完全同形）。
**通則：要引述一個會被機器解析的字串，就寫進 docstring 或字串字面值，不要寫在註解或錨定行上。**

### 7-5 ⚪ 一筆**當時成立、現已失效**的結論（刻意不算成失誤，理由如下）

本輪一度判定 smoke 排程的退出判準 **E1／E2／E3 三條全滿**，並據此提出「可以開始談退場」。
該結論在寫下的時點**取證完整、判斷正確**；它之所以現在不成立，是因為 2026-08-05 16:05Z
GitHub Actions 帳務被卡住，使 E1 的「近 30 天零筆 billing 類 conclusion」當場破掉（見 §2 Q2）。

**這一筆不列進失誤紀錄**：失效原因是**外部事件**，不是量錯、不是宣稱先於查證、也不是判準寫壞。
記在這裡的理由有三個，每一個都對 R77 有用：

1. **避免 R77 讀到兩份互相矛盾的結論卻不知道哪份新**——`Scheduled_Jobs_Lifecycle_Review_R75.md`
   裡那句「3 條全數達標」現在是假的，而沒有任何機械物會替它說話。
2. **示範「結論有有效期」這件事本身**：本 repo 反覆吃虧的形態是把**量測值**寫成**常數**。
   一個綁在外部世界狀態上的判準，它的顏色天生就是量測值，任何快照都只對取得它的時點有效。
3. **它同時是設計正確的正向實證**（§2 Q2）：正因為 E1 綁在「主通道活性」而不是「發現數」，
   這支補償控制才會在主通道真的死掉的那一刻**還活著**。

---

## 8. 本檔取證邊界（誠實揭露）

| 內容 | 強度 |
|---|---|
| §1 十道閘門的 rc 與關鍵數字 | **當回合真跑**（2026-08-05 深夜 ~ 08-06 凌晨，Windows 11 原生 PowerShell 5.1，主樹） |
| §1 git HEAD／origin/main／porcelain 零行／帳本 bytes | **當回合真跑** |
| §1.1 主 `.venv` 的 `pg_extras_state()` ＝ `present`、五個 PG 套件版本 | **當回合真跑** |
| §1.1 本機 pytest `4017 passed／160 skipped` | 🔴 **引用**（本輪其他包的量測，我**未**當回合重跑；重跑指令已附。任務書明令不跑，理由＝約 100 秒且與出廠基線不同環境） |
| §1.1 出廠基線 `3919／224` | **當回合真跑**（`--check-snapshot` 印出） |
| §2 Q1 三支 GA 工具的 `--json` 與 rc | **當回合真跑**，且 rc **未經管線**取得（第一次量測因接了 `Select-Object` 而得到污染值，見 §6 第 5 條） |
| §2 Q1 mutation 軌 `pass=true` | **引用** `AutoClaude/.g0_readiness.json`（`generated_at=2026-08-05T14:32:54Z`，我**未**重跑該軌工具） |
| §2 Q1 obs 08-21／drift 08-22 的終點日 | **當回合真跑**（我以 `ga_window.py` 自己的 `parse_ts` 對兩本帳本逐日模擬，配方已附）。⚠️ 前提是每晚各進帳一筆且皆綠，**漏一晚即往後推** |
| §2 Q2 `check_scheduled_task_drift.py` → `status=ok` rc=0 | **當回合真跑** |
| §2 Q2 E1 已破（至少一筆 billing 類 conclusion） | **當回合真跑**（run `31023606162` 三個 job 的 `steps=0` ＋ 三則 annotation 逐字，指令已附）。⚠️ 近 30 天另 48 筆 failure **我未逐 run 分類**，只斷定「至少一筆」——E1 要零筆，一筆即足以推翻 |
| §2 Q2 E2 的顏色 | **未驗證**（刻意不快照，現查指令已附） |
| §2 Q3 `docker ps` → `autoclaude_pg` pgvector pg18 healthy | **當回合真跑** |
| §2 Q3 PG 配方的三個基線數字（157 支、4 支紅、乾淨 DB 全綠） | **引用** `Skipped_Test_Inventory_R76.md` §4.7，我未重跑 |
| §2 Q3 pg17／pg18 逐位相同 | **引用**（本輪複驗者的量測），我未重跑 |
| §3 四方複審結論、13→12 blocking、缺陷列區間 | **引用**（列區間我以 Grep 計數核對過，本輪新列共 34 個命中；🔴 此處原先以占位形逐字寫出 ID 區間，該寫法本身會擠爆占位站點上限鎖，已由收尾包改述） |
| §5-3 `reschedule_g0_gatecheck.ps1` 已刪、`verify_token_guard_e2e.py` 仍在 | **當回合真跑**（`Test-Path`） |
| §1.2 (甲) 六支 workflow 對 `5993f09` 的 push 軌結論與 run id | **當回合真跑**（`gh run list --workflow <wf> --event push`） |
| §1.2 (乙) dispatch run `31023606162` 三個 job 全 failure／`steps=0`／三則 billing annotation | **當回合真跑**（`gh api .../jobs` ＋ `gh api .../check-runs/<id>/annotations`，逐字複製） |
| §1.2 (乙)「帳務在 15:44Z 與 16:05Z 之間卡住」 | **部分推論**：兩個時點的結果是量測值，中間的**因果與確切時刻**是推論。實際觸發原因（付款失敗 vs 消費上限）我無從得知，annotation 自己也是二選一的措辭 |
| §5-6 issue #10 仍 OPEN | **當回合真跑**（`gh issue list --state open --search '深度回歸失敗 in:title'`） |
| §5-5「windows-nightly-full 的修復已入庫但零次成功執行」 | **當回合真跑**（該 workflow 對 HEAD 唯一的 dispatch run 即 (乙)，未啟動任何 step）；「修復內容是把 run 本體改全 ASCII」為**引用** `CrossPlatform_R76_Scan_Findings.md` R76-02 |
| §5-6 `MIN_TESTS=1819` vs 實測 1979 | **當回合真跑**（前者由 `--check` 印出，後者由 unittest 印出） |
| §4 三條規則的機械物落點 | **部分推論**：檔案與符號我已確認存在（`ga_window.py` 的常數與函式名逐行讀過），但**必跑項 ⑥⑦ 是人執行的檢查清單、不是自動判準**，我**未**驗證有任何東西會在漏做時說話——這正是它們最大的弱點，已寫在該節的「抓不到什麼」欄 |
| §7 四筆失誤 | 7-1／7-2 是我親身經歷；7-3／7-4 為**引用** `CrossPlatform_R76_Scan_Findings.md` §R76-FIX-0b／§R76-FIX-2 的逐字記載 |

> 🔴 **上表寫於「只改本檔」的那個時點；R76 收尾包（2026-08-06）之後不再成立**——
> 原「本檔零改動聲明」逐字是「除本檔外，我未寫入或修改任何檔案，未 commit、未 push、
> 未動缺陷帳本」，該句對**寫下它的那個包**為真，對**本輪最終產出**為假。留著它會讓
> R77 以為交棒書所述狀態就是 `5993f09` 的狀態。收尾包實際改了哪些檔見下方 §9，
> 該包自己的取證邊界也在那裡。

---

## 9. R76 收尾包（`5993f09` 之後的第二個 commit）做了什麼

> 本節由收尾包自己寫，與 §1〜§8 是**不同時點、不同作者**。§1 的十道閘門數字取自
> `5993f09`；收尾包又動了樹，故**收尾包重跑了同一批閘門**，rc 逐項附在 commit 訊息與回報中。

| # | 事項 | 落點 |
|---|---|---|
| 1 | 記錄 GitHub Actions 帳務事件、撤回 smoke 排程的退場結論 | `DEF-101-866`；`tools/windows_smoke_local.ps1`「E1 現況欄」；`Scheduled_Jobs_Lifecycle_Review_R75.md` §0 第二訂正塊＋三處指路 |
| 2 | 修同輪兩列互相矛盾（`DEF-101-856` ① vs `DEF-101-865`） | `DEF-101-856` 狀態欄追加訂正（原文未改）；機械物可行性評估 `DEF-101-867` ＋ `CrossPlatform_R76_Scan_Findings.md` §R76-FIX-6 |
| 3 | `Skipped_Test_Inventory_R76.md` §4.7.1 的過期基線數字 → 改為指向 SSOT 的現查配方 | 該檔 §4.7.1；同檔另一處引用同一組數字者一併改為「出廠基線」 |
| 4 | `MIN_TESTS` 重釘（判定＝**該釘**，理由見下） | `tools/run_root_unittests.py`；`ONBOARDING.md` §7 由 `sync_onboarding_baselines.py --write` 同步 |
| 5 | 交棒書補帳務事件、cleanvenv 路徑、§5-3／§3 的訂正回執 | 本檔 §2 Q2／§3／§5-3／§5-5／§5-7／本節 |
| 6 | 🔴 **修掉交棒書自己造成的兩道根層紅** | `DEF-101-868`；本檔 §3 缺陷列那格與 §8 各一處改述 |

### 9.2 🔴 第 6 項值得單獨說：**交棒書把根層閘門弄紅了，而寫它的包不知道**

收尾包第一次對「含交棒書」的樹跑 `run_root_unittests.py` 就吃到 **rc=1／2 failures**，兩支都指向
本檔：① §3 的現查配方裡寫了一段 ID 正則字面，被 `test_defect_id_reference_integrity` 判成
「指向空號的斷鏈引用」；② §8 有一格用「ID 前綴＋字母」的占位形描述列區間，把該鎖的
**占位站點上限**（後門規模鎖）從 4 撐到 5。

**三個對 R77 有用的推論**：

1. **`.md` 也在閘門掃描面內**，而且掃的是 `git grep --untracked` ⇒ **未 commit 的檔一樣算**。
2. **危險的正是「只改文件」這種自我認知**——§8 原本那句「本檔零改動聲明」是誠實的，但它同時
   讓作者覺得沒必要跑閘門。**改文件不等於不會弄紅樹。**
3. 🔴 **訂正文第一版自己又踩了一次**：為了解釋②而在訂正句裡逐字示範那個占位形，同一支
   測試立刻再紅。這與 §7-4 是同一個形態（`DEF-101-858` 的通則）：**要引述一個會被機器解析的
   字串，就不要把它寫在會被解析的位置**——只描述、不示範。

### 9.1 為何判定 `MIN_TESTS` **該現在重釘**（這不是「調高門檻」）

- **方向**：`MIN_TESTS` 是**下限**（`countTestCases() >= MIN_TESTS` 才往下跑）。把它由陳舊的低值
  往上釘＝**收緊**，讓「靜默蒸發 N 支測試仍然全綠」的窗口變小。§6 第 2 條禁的是**放寬**
  （砸溫度計讓紅變綠）；重釘的方向相反，**不在該禁令射程內**。真正屬於「只准變小」的是
  shrink-only 棘輪（`SPECIAL_FILES` 那批），兩者不是同一種東西。
- **不釘的代價不只是鑑別力衰減**：該常數同時是零相依探針的**鑑別門檻**，下限一旦低於零相依
  環境的收集數，探針就不再提前判紅而是**實跑整棵樹** ⇒ 撞逾時（`DEF-101-803` 的實測事故）。
  「維持現狀」在這裡不是中立選項。
- **重釘判準已滿足**：該行自訂的解除條件是「所有並行修復包與**四方複審** agent 全部停工後，
  由收尾者於最終工作樹實跑並填實測值」。R74 那次自陳是**中途值**（理由＝四方複審未執行）；
  R76 四方複審已全跑並收斂，收尾包是本輪最後一個工作者 ⇒ 條件成立，且**已連兩輪沒人重釘**。
- **取值紀律**：取 runner 當場印出的計數**直接填入、零加減推算**；量測窗口前後各取一次
  **含內容**的工作樹指紋並確認相同（`git status --porcelain` ＋ `git diff HEAD` ＋ untracked 內容雜湊）。
  🔴 指紋比對只能證明「量測期間沒人在動樹」，證明不了「之後不會再有一波」——後者由
  「四方複審已收斂 ＋ 本包是最後一個工作者」承擔，這一半**沒有機械物**，照實揭露。
- **鑑別力實證（bug-injection）**：重釘後把下限往上撥一格再跑，`run_with_floor` 必須在**不執行
  任何測試**的情況下判紅；撥回實測值即綠。逐字輸出見回報。
