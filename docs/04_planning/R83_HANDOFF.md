# R83 → R84 交棒書（R83＝**macOS 真機首輪**）

> **給誰看**：一個要接手 R84、對 R83 一無所知的人（不論他坐在 Mac 還是 Windows 前面）。
>
> **本檔體例（與 R82 交棒書相同，且本輪實證過它的必要性）**：凡述及狀態（做了沒／過了沒／
> 推了沒），一律**附現查指令**，不寫快照結論。本檔裡幾乎每一個數字都是**量測值不是常數**，
> 照著指令重跑一次，以**你跑出來的為準**。
>
> 🔴 **唯一刻意寫死的量測值是護欄層淨額三元組**（§2.3）——那是
> `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `repin_log_problems()` 款(9) **強制要求**的
> 「承認」，不寫等於把本輪最不利的那個事實藏起來。其餘一律指向載具。
>
> 🔴 **本檔刻意不寫任何 pytest／unittest 的支數 token**（`Ran <N> tests`／`<N> passed`／
> `skipped=<N>`）。理由不是體例潔癖，是**機械的**：`tools/check_pytest_baseline_sites.py` 對
> 「同一行同時出現 `passed`／`skipped` 字樣與四位數」判為「又多開了一個基線數字的家」，
> 而該閘門**現在就是紅的**（見 §5.2）。把支數寫進交棒書會讓它更紅。
>
> 兩個路徑簡寫（本檔全篇沿用）：
> - macOS：`r=$(git rev-parse --show-toplevel)`；直譯器＝`$r/.venv/bin/python`（3.11.15）
> - Windows：`$r = '<你的 checkout 路徑>'`、`$p = "$r\.venv\Scripts\python.exe"`
>   （🔴 **不要**照抄任何一台機器的絕對路徑——R73 的 `Find-GitBash` 判例就是這樣來的）

---

## §0 開場必讀（五條，跑完再往下讀）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
git log -1 --format='%H %s'                     # 本輪收在哪個 commit
git status --porcelain | wc -l                   # 工作樹是否乾淨
git fetch origin && git rev-parse HEAD origin/main   # 兩個 sha 相同才算推成功
.venv/bin/python -c "import sys;sys.path.insert(0,'tools');import check_defect_log_crossref as C;from pathlib import Path;print(C.current_round(Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8')))"
```

- **輪號基準**：上面最後一條印出的就是帳本現查的當前輪。我寫本檔時它是 **83**。
  R84 的第一個帳本列會把它推成 84——**那一步會觸發連鎖，先讀 §5.4 再落列**。
- **我沒有 commit、沒有 push、沒有動任何一支我未被授權的檔**——現查
  `git log -1 --format='%H %s'`（本檔進不進得了那個 commit，由收輪窗口決定）＋
  `git status --porcelain`（我離開時工作樹**仍未**全部進版控，數十個檔）。本檔在你手上時，
  **至少三道閘門是紅的**（§5.2 逐筆附現查指令與修法）。
- **先讀根 `CLAUDE.md`**。🔴 其中〈Windows 側單一載具原則〉那一整節在 mac 上不適用
  （鐵律一的 hook `.claude/hooks/block_bash_on_windows.py` 在非 Windows 一律 exit 0）；
  但〈鐵律三〉（跨平台自問）與〈鐵律四〉（宣稱先於查證）兩節**兩個平台都適用**，
  而本輪抓到的東西幾乎全部落在那兩條上。

---

## §1 本輪的性質與一句話總結

**R83 是第一次在 macOS 真機上完整跑完一輪。** 之前每一輪都在 Windows 上（R67~R70 有 mac 真機期，
但不是「完整跑完一輪」）。這件事決定了本輪全部發現的形態：

> **判準把「某一台 Windows 機器上量到的值」寫成了常數，於是同一棵樹在 mac 上必紅。**

動工時根層 `tools/run_root_unittests.py` 有 10 支紅，歸因後恰好落在 5 個根因上，
逐一都是這個形態的實例。逐支的家＝帳本 `docs/06_quality/AutoSDD_Defect_Log.md` 的
`DEF-200-030`~`DEF-200-039` 十列；重現配方、根因分群與「治本 vs 拔判準」的判準＝
`docs/06_quality/CrossPlatform_R83_Scan_Findings.md` §A-1。

**修法一律不是「把常數改成 mac 的值」**——那只是把紅從 mac 搬到 Windows。本輪兩種正解都用到：
① 換量測面讓它平台中立（EOL 改讀 `git ls-files --eol` 的 `i/` 欄＝content-addressed；
路徑比較改用 `os.path.samefile`；幽靈路徑判準改問 repo 自己的宣告）；
② 顯式雙欄，兩欄在任何主機上都跑（額度計憑證來源登記 `("win32", "darwin")`）。

🔴 **一句話總結**：這一輪的價值**不在**「把 mac 弄綠了」，而在**量到了一批只有換平台才看得見的
假綠**——包括「fixture 比被測世界簡單」「鎖在守假話」「移除用得動、列舉壞掉且回報成功」這三類，
逐條見 §6。代價是護欄層長了本表歷來最大的一筆（§2.3），M1 因此**比動工前更遠**。

---

## §2 收輪狀態（數字一律現查，指令可直接貼）

### 2.1 我（本交棒書作者）這一回合真的跑過的，附 rc

| 項目 | 指令 | 我實測 rc |
|---|---|---|
| 帳本跨文件一致性 | `.venv/bin/python tools/check_defect_log_crossref.py` | **0**（另吐 3 類 warning，見 2.4） |
| 帳本未結存量 | `.venv/bin/python tools/check_defect_log_crossref.py --unresolved-count` | **0** |
| 帳本歸檔保全 | `.venv/bin/python tools/archive_defect_log.py --check` | **0** |
| 雙平台腳本對等 | `.venv/bin/python tools/check_script_parity.py` | **0** |
| NTFS／大小寫碰撞 | `.venv/bin/python tools/check_ntfs_paths.py` | **0** |
| wrapper 厚度 | `.venv/bin/python tools/check_wrapper_thinness.py` | **0** |
| GHA action 版本 | `.venv/bin/python tools/check_gha_action_versions.py` | **0** |
| `.ps1` 掃描面 SSOT | `.venv/bin/python tools/_script_scan_surface.py --list --suffix .ps1 --with-latest --check-floors` | **0** |
| hook 活性（開發機層） | `.venv/bin/python tools/check_hooks_liveness.py` | **0** |
| 幽靈路徑／符號鎖 | `.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_doc_loc_baseline_freshness_r60.py'` | **0** |
| 否定存在宣稱鎖 | `.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_negative_existence_claims_r82.py'` | **0** |
| **基線數字站點** | `.venv/bin/python tools/check_pytest_baseline_sites.py` | 🔴 **1** — 見 §5.2 ① |
| **帳本 crossref 單元測試** | `.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_check_defect_log_crossref.py'` | 🔴 **1** — 見 §5.2 ② |
| **ONBOARDING 表② 新鮮度** | `.venv/bin/python tools/sync_onboarding_baselines.py --check-snapshot` | 🔴 **1** — 見 §5.2 ③ |
| **護欄層棘輪** | `.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_adr_xplat001_c1c2_lock.py'` | 🔴 **1** — 見 §5.2 ④ |

> 🔴 **後四筆紅不是「本輪失敗」，是「收輪還沒做完」**：我寫本檔的同時另有一個包在改三支 `.md`、
> 舵手在跑全樹。四筆各自的成因與修法都在 §5.2，逐筆都是分鐘級的動作。**但它們現在會擋住 push**。

### 2.2 我**沒有**複驗、採信他人實測的（逐筆標明來源）

| 項目 | 來源 | 為什麼我沒重跑 | 現查指令 |
|---|---|---|---|
| 根層全樹 unittest 全綠 | 舵手收尾實測，**Architect／QA／SD／SA 四方各自獨立重跑，四份逐字相符** | 單跑約 6~7 分鐘，且本檔寫作期間另有並行寫檔者 ⇒ 依 `DEF-101-886`（多 agent 共用一棵樹時 runner 的 rc 是別人鍵盤的函數），我此刻量到的值不具代表性 | `.venv/bin/python tools/run_root_unittests.py` |
| `macos_smoke_local.sh` 全綠 | 舵手實測 | 它會在工作樹寫檔（同 SA 複審者拒跑的理由） | `bash tools/macos_smoke_local.sh` |
| `AISDLC_SDD` ci-gate 全綠 | 舵手實測 | 同上（會寫 `arch-fitness.json` 等產物） | `bash AISDLC_SDD/scripts/ci-gate.sh` |
| AutoClaude 側 pytest 無 fail | 舵手＋SA 實測 | 同上；🔴 **必須在 `AutoClaude/` 目錄下跑**（SA-14 實測：從 monorepo 根跑會拿到 6 支 cwd 相依的假紅，逐字 `can't open file '<repo根>/tools/mutmut_exit_code.py'`） | 於 `AutoClaude/` 下 `python -m pytest tests -q` |
| shellcheck 與基線一致 | SD 實測 | 需 docker 載具 | `.venv/bin/python tools/run_shellcheck.py` |

### 2.3 護欄層淨額（**本檔唯一刻意寫死的量測值**）

**本輪護欄層累積淨額＝ 73823 → 79083（+5260）**

- 權威載具（零手抄）：`.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`
  （末段會印出 `_GUARD_LINES_REPIN_LOG` 該補的那一列草稿，照貼即可）。
- 我當回合另跑 `-m unittest ... test_adr_xplat001_c1c2_lock.py`，末行印
  `[Scan-H triplet] UEP=5 AC=47 GLC_FILES=63 GLC_LINES=79083` ⇒ 凍結表側與工作樹側的總量
  現在**是一致的 79083**；紅的是**文件側**兩行還停在中途值（§5.2 ④）。
- 🔴 **這是 `_GUARD_LINES_REPIN_LOG` 歷來最大的一筆淨額。照實記，不粉飾。**

🔴 **一筆對「歷來最大」的必要限定（我逐列重算過，這一條我親手抓到自己的任務書錯了）**：
以 **per-entry**（一列）論，R83 的 +5260 是**歷來最大的一筆**；但以 **per-round**（一輪合計）論，
**R82 是 +5400，比 R83 大**（R82 那一輪有三列：+3675／+1668／+57）。
上一輪的 Architect 複審者（F-5）也抓過同一個轉述誤差。⇒ 語氣上不得寫成「史上最糟的一輪」，
因為**上一輪在同一條軸上長得更多**。重算指令：對 `_GUARD_LINES_REPIN_LOG` 逐列按輪號分組加總。

**兩點對本輪不利的事實**：
1. M1 的達標條件是**總量連續三輪不上升**。本輪是明確的反方向。
2. **本輪淨減法為 0**。`schedule_backend` 的 `list_jobs()` 原本被記為「本輪刻意做的減法」（約 15 行），
   而它在**同一輪後段**因為 mac 回收臂的修復被整組回補——現查
   `grep -n "def list_jobs" tools/lib/schedule_backend.py` ＝ **3 處**（三個後端都有）。
   `docs/04_planning/AutoSDD_improving_107.md` §2 已就地訂正並保留原文為史料。

### 2.4 帳本現況（三個數字一律現查，本節不寫死）

唯一量測入口：`.venv/bin/python tools/check_defect_log_crossref.py --unresolved-count`

我當回合看到三類 warning，方向**都在往線上靠**，逐類都要 R84 正面處理：

1. **未結存量距 fail 線的餘裕**——我實測時距 warn 線只剩個位數筆。
   🔴 **歸檔不會降低這個數**（未結列在結構上不可搬），唯一出路是把列真的結掉，或改派給具名承接者。
2. **主檔 bytes 已逼近輪替上限**（`DEF-99-001` 政策；同一支檢查器逐字警告）。
3. **已結列殘留待辦數十筆**——「已結」這個分類使它們結構上進不了承接稽核
   ⇒ 它們是**零承接**的待辦。`DEF-200-042` 已為其中最貴的一格（LOC total）立列。

### 2.5 ONBOARDING §7 表② macOS 欄

🔴 **訂正一個我在任務書裡收到的說法**：那不是「macOS 欄**首次**回填」——`git show HEAD:ONBOARDING.md`
裡 `snapshot-fingerprints-darwin` 錨**早就存在**（`measured-at=2026-08-02`）。本輪真正的第一次是
**provenance 首次完整**：該錨的 `interpreter=` 與 `sdk-extra=` 兩欄在 HEAD 上都是
`tools/lib/baseline_origin.py::PRE_FIELD`（「本錨早於那一欄」），本輪換成了真值
（出廠乾淨 venv、無 PG extras、無 sdk extra）。差異現查：
`git diff ONBOARDING.md | grep snapshot-fingerprints-darwin`。

🔴 **而它此刻又 stale 了**（§5.2 ③）：AutoClaude 測試樹指紋在回填之後又被動過。
這一格的結構性弱點值得記住——`--check-snapshot` 只管**指紋**，
表① 那一格的散文（量測時點、跳過支數）**不在任何鎖內**（QA F-4），會靜默腐爛。

### 2.6 `MIN_TESTS` 是本輪最後一個仍在動的受鎖值

現查：`grep -n "^MIN_TESTS" tools/run_root_unittests.py`。

🔴 **它在我寫本檔的這段時間內又被重釘過一次**（我開場看到的值與收尾看到的值不同）。
該常數的註記**自己**訂了一條規則：重釘要綁在四方複審全數 APPROVE 之後，否則屬**中途值**。
本輪的複審已執行、收斂包也已落地，但收斂包本身沒有第三方看過（§7.2）⇒ 依它自己的判準，
**收輪窗口必須在所有包停工後再確認一次它是最終值**，並同輪回填
`ONBOARDING.md` §7 表① 那一格（兩者由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，
一鍵回填＝`.venv/bin/python tools/sync_onboarding_baselines.py --write`）。

---

## §3 🔴 訴求逐條結算（**本節是本檔的核心，請直接讀這一節**）

> 🔴 **先解一個編號衝突，否則這張表會被讀錯**（SA-13 立案）：`AutoSDD_improving_107.md` §1 宣告
> 它的 `1`~`6`＋`S1`／`S2`／`AC` 是**訴求編號的 SSOT**；而帳本與口語討論裡另有一組
> 「訴求 1／2／3」指的是**三個 AutoClaude 問題**（舵手被喚醒回來／example 跑不動／關不掉的通知）。
> **同一個標籤指兩件事**，交叉引用者必然對錯。本檔一律採 `improving_107` 的體系，
> 三個 AutoClaude 問題以 **AC-(a)／AC-(b)／AC-(c)** 標示，並在該列註明它在口語裡的別名。

| 訴求 | 本輪狀態 | 實測依據（現查指令／座標） | R84 要做什麼（**可執行**） |
|---|---|---|---|
| **1** 全面掃描、兩平台零相容性問題 | **mac 側成立；Windows 側沒有任何本輪量測值** | 10 支紅逐支落 `DEF-200-030`~`DEF-200-039`，重現配方見發現文件 §A-1（含「HEAD 乾淨拷貝樹」與「HEAD 版判準 × 主工作樹」**兩個載體**——少任一個就重現不出 10 支）；三棵樹在 mac 驗綠見 §2.2 | 在一台真 Windows 11 上重跑同一批閘門；成功的憑證＝`snapshot-fingerprints-win32` 錨的 `measured-at` 前進 |
| **2** 架構簡潔／分工清楚／不重複模組 | **未達成**（護欄層 +5260、淨減法 0） | §2.3；`AutoClaude/tools/check_loc_budget.py --json` 現查 10 個額度／續航模組中有數個貼著 tier 天花板 | 先做 A-07 那個結構決定（見 §5.3 第 2 項），**再**做 6C。否則下一支模組就是第 11 個 |
| **3** 一邊開發不讓另一邊產生落差 | **量測面已平台中立；指引面只上了一道掃描器，且它擋不住自己立案那個缺陷的最小變形** | 掃描器＝`tools/tests/test_skip_discoverability_r83.py`；SD F-07 實測：只加「兩個平台字樣」即可通過，而它判的不是「兩個形態都在」 | 把判準改成「同一判定單位內 `_WINDOWS_ONLY` 命中時必須另有一筆 `_POSIX_ONLY` 命中」；🔴 **上線前先量假紅存量**（SD 自己劃界說他沒量） |
| **4** Windows 上常犯低級錯誤的根因 | **本輪未重跑那次歸因**（本輪在 mac） | 該歸因是**量測值不是常數**，載具＝`tools/probe/misstep_attribution.py`（來源清單、桶的關鍵詞表、每筆歸屬理由都在檔內，輸出可 diff 的 `.jsonl`） | 回到 Windows 的那一輪**開輪就跑一次**，並把桶的分佈與上一次對照（只可量級對照，百分比不得寫進任何文件當常數） |
| **5** 每輪挖深、清技術債 | **有真交付、也有真退步** | 真交付：AutoClaude 的 AC_MATRIX 欠債 3 → 0（`_AC_TARGET_PENDING` → `frozenset()`、天花板同步壓到 0，並新建三支真斷言整合測試）。真退步：帳本未結存量與 bytes 兩條線都在往上（§2.4） | ① 清未結列（不是歸檔）；② `AutoClaude/tests/integration/test_concurrent_runs.py` 的品質保留必須關掉（見 §5.3 第 3 項） |
| **6a** 隨時監控額度 | **成立** | 現查（**符號錨，不用行號**——行號會漂，本輪實證過 6 處行號錨失準）：`grep -n "measuring and quota_gate" .claude/hooks/context_budget_guard.py` ⇒ 呼叫點的條件是 `measuring`，**不再**被 `blocking` 罩住（`DEF-200-018` 的「三層同義過濾器」修法）⇒ 每一次工具呼叫都量；TTL 過期時真打端點 | 無（維持）。回歸鎖＝`test_context_budget_guard.py::QuotaGateIsWiredToTheBurnPathTest`（含「呼叫點不得再被 `blocking` 罩住」的 AST 判準） |
| **6b** cap＝f(水位%, 距 reset) | **未做（結構性，不是參數沒調對）** | `tools/lib/quota_policy.py` 的 `_pace_of()` 在 production **恆夾 1.0**：live 快取現查有數軸 `resets_at` 恆為 `null` ⇒ horizon 恆有 `none` 軸，而 `_MULTIPLIER` 的 `near=2.0` 結構上到不了。另：`tools/session_resume_planner.py --help` 的旗標裡沒有任何「我現在能派幾個」的出口 | ① 讓 `resets_at=null` 的軸**不參與** `min()`（或明文降級為 advisory）；② 加一個 CLI 出口印出「當前 band／cap」——**這是舵手每次派工前唯一需要的那個數字** |
| **6C** 85% 準備動作 | **未做**（`prepare` 帶只有一個沒人印的 cap 值） | 沙箱實測 `PostToolUse×Read@86%` → rc=0／stderr 0 位元組／任務書 0 份（`DEF-200-022`）。落點 `tools/lib/quota_gate.py` LOC **400/400、餘裕 0**（`AutoClaude/tools/check_loc_budget.py --json` 現查） | 🔴 **必須先騰位**。合法出口只有：刪死碼／把 docstring 改成 `#` 註解（`#` 不計 LOC）／拆職責。**不得調高 LOC 預算**——那條禁令的方向就是禁放寬 |
| **6c** 95% 停止並記錄 | **成立** | rc=2 阻斷 ＋ 任務書落磁碟 ＋ 武裝哨兵，且**一個 reset 視窗只做一次**（避免每次工具呼叫都重寫一份） | 無（維持） |
| **6d** 同 session 續跑 | **機制本輪修好且有決定性痕跡；端到端只在合成 job 上走過** | `tools/lib/schedule_backend.py` 的 `_defer()` 改成**等父行程真的退場**才動手（`while kill -0 $p …`，上界 `DEFER_WAIT_CAP_SECONDS`）。決定性痕跡：`$TMPDIR/autosdd_sentinel_bootout_*.log` 內有一支逐字寫 `parent-gone waited=20s`，其後才 `bootout rc=0`；修法前的同族痕跡檔只有 `bootout rc=0` 一行。哨兵事件分佈現查 `cat "$TMPDIR"/autosdd_resume_log_*.jsonl`：我當回合看到 `probed` 已經 **不再是 0**，而 `resumed`／`arm_reset` **仍是 0** | 在**真實撞線**上再驗一次（不為取證燒額度；等它自然發生）。真撞線那一次跑的是舊碼 ⇒ 那次的失敗不算證據 |
| **6e** 撐過 0~5h reset | 🔴 **不得宣稱達成**（`DEF-200-020`，P1） | `pmset -g sched` 我當回合實測輸出 **0 位元組**（零排程喚醒）；`pmset -g custom` 的 AC Power 段逐字 `sleep 0`。⇒ 今天成立的唯一原因是 `pmset sleep 0` 這個**不在 repo 裡、不隨 clone 走**的機器設定（同 R73 把一台機器的安裝路徑寫成常數的判例） | 二擇一：① 把 `pmset repeat` 排進 `tools/install_mac_nightly.sh` 並誠實記「需 sudo」；② 明文宣告「睡著的 Mac 不會醒」是本專案的**已知邊界**，並讓武裝路徑在偵測到 `sleep != 0` 時**出聲**（現在是靜默的） |
| **6f** 前沿調研（有沒有更好的取數管道） | **完成，結論＝不換** | 調研結論落在本輪文件；憑證面的結論是本輪最重要的跨平台結論：Windows `Get-ScheduledTask` 對不存在的工作回 **rc=0**（假綠）⇒ 憑證必須是 `NextRunTime` 的**值**；macOS `launchctl print` 對不存在的 label 回 **rc=113**（rc 有鑑別力）但**沒有** next-run 欄位 ⇒ 憑證＝rc ＋ descriptor 回讀 ＋ plist 路徑，且**刻意不含任何時刻** | 無。但**別讓它變成散文**：同一條「反事後諸葛」紀律在兩平台需要相反的實作，這件事的家是 `tools/lib/schedule_backend.py` |
| **S1** 徹底解決 skipped | **量到一個結構事實 ＋ 關掉一個假綠 ＋ 留下兩個量測缺口** | ①「單機零 skip 結構上不可能」成立（mac 側剩餘的最大單一類在 mac 上**沒有標的**）；② `tools/tests@darwin` 剖面已由 advisory **升為阻斷式天花板**（現查 `profile_registered('tools/tests@darwin')` → `True`、`_MEASURED_RUNNERS_MIN` → `4`、已自 `_UNMEASURED_RUNNER_PROFILES` 移除）；③ 互補剖面宣告已訂正為 `('tools/tests@win32',)`（現查 `_COMPLEMENTARY_PROFILE`） | ① **一行 docker 指令**先做掉最便宜那一塊（見 §5.1）；② 把 `AutoClaude/tests@darwin+pg+nested` 入表（現查 `profile_registered(...)` → `False`，連「已知缺口」都沒入）；③ 「那些測試在**今天的** win32 上真的跑到」要 Windows 真機才量得到 |
| **S1 訂正** 🔴 「聯集才是零」 | **本輪一個錯誤結論已被訂正，而訂正後仍不是「已達標」** | 交件時 darwin 的互補剖面宣告成 `tools/tests@linux`，而 mac 上被 skip 的那一批**全部**是 `[WINDOWS-NATIVE-ONLY]`、skip 條件是 `os.name != "nt"` ⇒ **linux 一樣 skip、承接不了**，`skip_target_report()` 因此回空＝假的「已達標」（SA-02）。宣告面已修；但該函式兩道判準**都是宣告面／登記面** ⇒ 回空仍不等於有證據 | 量測面唯一的路是 Windows 真機。**不要**因為 `skip_target_report()` 回空就把這一格記成綠 |
| **S2** 消除技術債（帳本警告線） | **未越線，但三條線都在靠近** | 見 §2.4 三類 warning（一律現查，本檔不寫死） | 把「清列」排進 R84 首日：優先結掉 `DEF-200-*` 裡本輪已完成卻仍 open 的列；並為 `DEF-101-726` 的 LOC total 那一格指派真的承接者（`DEF-200-042` 已立列） |
| **AC-(a)** 舵手被喚醒回來（口語「訴求 1」） | 🔴 **架構天花板，登記而非修**（`DEF-200-028`） | launchd／schtasks 叫起來的那一跑**沒有 TTY** ⇒ 回來的必然是受限 headless 代理（`tools/session_resume_planner.py` 走 `claude -p -r <sid>`，spawn 時注入 `AUTOSDD_UNATTENDED=1`，該旗標會讓破壞性 git 的行內豁免失效）。真舵手只能由**人**跑 `claude -r <sessionId>` | 不要再嘗試「自動變回真舵手」。**該做的是把 headless 代理的能力面寫清楚**：它能做什麼（收斂、寫任務書、跑閘門）、不能做什麼（commit／push／改配置） |
| **AC-(b)** example playbook 跑不動（口語「訴求 2」） | **本輪未動**（被追蹤兩輪） | 🔴 **順手訂正一個路徑**：該 playbook 在 `AutoClaude/scripts/example_playbook.yaml`（**不是** AutoClaude 根目錄）；我現查該檔確有 `global_goal:` 與 `tasks:` 兩個鍵 | 端到端實跑一次（PG 已可用，見 §5.1）。W7 判定它與額度軸「判準互為雜訊」⇒ **另輪單獨跑**，不要與額度軸包並行 |
| **AC-(c)** session 結束仍有彈跳視窗（口語「訴求 3」） | 🔴 **無法處理——不是不想做，是看不到標的** | 掌舵者提到的截圖 `沒有啟動的提示視窗.png` 未提供到工作樹裡，任何 agent 都看不到它 | **請掌舵者給那張圖，或給彈窗的逐字文字**（標題列＋內文）。在那之前這一列不得被寫成「已修」或「已交棒」——它只是**缺料** |

---

## §4 成熟度評估（依 `docs/06_quality/CrossPlatform_Maturity_Criteria.md` 這份 SSOT）

**現況總判：六條裡 0 條達標（0／6），與 R80／R81／R82 相同。**

> 🔴 這一節**不重抄判準表**（那份 SSOT 的體例明文禁止第二個家，`TestR78MaturityCriteriaSsot` 在守）。
> 每一格只寫「達標？／距離／量測配方指向哪支載具」。

| 判準 | 達標？ | 距離與依據（量測配方一律指向載具） |
|---|---|---|
| **M1** 護欄層停止自我增殖（**兩半合取**） | ❌ **比動工前更遠** | **①UEP 半**：`[Scan-H triplet]` 印 `UEP=5`；達標需要一次 ADR 級拍板（回執容器＝`docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md` §8.1，現查該表是否仍為空）。**②護欄行數半**：門檻是**總量連續三輪不上升**，而本輪是 **+5260**（§2.3）⇒ 這一半在本輪明確倒退。🔴 **這件事不因為「成長有正當理由」而改變**——判準量的是總量，不是理由。且本輪**淨減法為 0**（§2.3 第 2 點），連「有加也有減」都說不上。載具：`--print-guard-lines` |
| **M2** 假宣稱密度單調下降 | ❌（**本輪有分子，不得再記 N/A、也不得記 0**） | 判準①「該輪未執行複審一律判 N/A」的前提**在本輪消失**——四方複審已執行，Architect／QA／SD／SA **全數 `APPROVE_WITH_CONDITIONS`，無人 REJECT**。判準②「分母為 0 不適用」也不適用：本輪新帳本列是 `DEF-200-001`~`DEF-200-043`（現查帳本「發現情境」欄提及 R83 的列）。判準③「門檻是**絕對值**不是比率」⇒ 拿分子直接比：四方 `falsified_claims` 段逐條相加＝**32 筆**（Architect 6／QA 9／SD 5／SA 12，**跨方重複未去重**），門檻是「連續三輪 ≤1 筆且無任何一筆 P1」，而本輪光是一輪就遠超，且本輪確有 P1（例：`DEF-200-020` 逐字「不得宣稱達成」）⇒ **M2 判 ❌**。結算依據的居所＝發現文件 §G（此前它只活在複審者的逐字稿裡，會被 compact 掉） |
| **M3** 新增判準的**第三方**注入通過率＝100%（作者自證不計分） | ❌（兩個獨立理由，任一都足以判否） | ① **通過率本身不是 100%**：SD 對本輪新判準抽 5 支做注入，自陳 **4 支真的有牙**——沒有牙的那一支是寫死分母的武裝臂清單（注入第五支 `arm_next_thing` 後兩支鎖仍全綠，改用 AST 量測分母才當場紅）。② **複審後的收斂包沒有再被第三方看過**：四方審的是**送審那一批**；其後為收斂條件而落地的三個包（含護欄層重釘、帳本 15 列、三支 `.md` 的逐格訂正）依 M3 仍屬**作者自證**。門檻另要求「抽樣面含既有鎖庫隨機 20 支」——那件事至今一次都沒做過 |
| **M4** 「宣稱射程 ≡ 實作射程」零落差 | ❌ | 門檻是**一輪內 0 筆**。本輪光是四方點名的射程落差就有數筆，其中兩筆是「**有鎖在守假話**」的教科書案例：`tools/lib/schedule_backend.py` 檔頭第 1 行的「唯一提問點」（守它的鎖只讀 hook 一支檔，回收臂在射程外）與 `tools/tests/test_mac_endurance_r83.py` 的武裝臂寫死分母。機械化的第一個實例仍是 `TestR75IronLawMechanismSubstance` |
| **M5** 雙向注入語料裡「還攔不到的題數」各 ≤1 | ❌（差得很遠） | 我當回合真跑 `.venv/bin/python -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix` → `Ran 3 tests / OK`，`setUpClass` 末行印 `[Xplat injection matrix] Win2mac=6/12 mac2Win=5/10` ⇒ **未攔到題數＝ total − hit ＝ 6 與 5**，門檻是各 ≤1。且 SSOT 記載的質性缺口（Win→mac 命中全在檔名／路徑／編碼層，**程式碼語意層仍是 0**）本輪一格都沒動 |
| **M6** 從未被執行過的測試歸零 | ❌（**但本輪是這一條唯一真的前進了的**） | 門檻兩條同時成立：①支數為 0 ②有**當輪**實跑 rc 佐證。本輪把 `tools/tests@darwin` 那一軌從「剖面未登記（advisory）」變成**阻斷式天花板**（`_RUNTIME_SKIP_CEILING` 與其 MAX 兩張表皆入、`_MEASURED_RUNNERS_MIN` 3→4），這是 R82 交棒書登記的證偽標的被真的兌現。**仍不為 0 的兩塊**：`AutoClaude/tests@darwin+pg+nested` 兩張表都沒登記（現查 `profile_registered(...)` → `False`）；`tools/tests@win32` 的天花板值來自**先前輪次**的 Windows 量測，不是當輪 ⇒ 門檻②在 Windows 那一半不成立。載具：根層 runner 的 `[skip census]` 行 ＋ 於 `AutoClaude/` 下 `pytest tests -q -rs` 餵給 `AutoClaude/tools/local_ci_gate.py --census-only <log>` |

🔴 **一句誠實的總結**：本輪把 M2 從「判不出來（N/A）」變成「判得出來且是 ❌」，把 M6 的一軌從
「沒有覆蓋」變成「有覆蓋且有天花板」。**這兩件都不算進度**——它們只是把量尺修好，
而量出來的數字一格都沒動；同時 M1 明確倒退。

---

## §5 🔴 R84 首日要做什麼（可直接貼的指令）

### 5.1 開工前先確認基線（照順序）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"

# ① 先把 PG 起來——否則 AutoClaude 側會回來一大批「其實只是 docker 沒開」的 skip。
#    零程式改動、零環境變數（conftest 有 PG autodetect），這是本輪量到的最便宜的一塊。
docker compose -f AutoClaude/docker-compose.ci.yml up -d
#    （根 CLAUDE.md 記載的等價形態是在 AutoClaude/ 下跑 `docker compose -f docker-compose.ci.yml up -d`；
#      我實查該 compose 檔內沒有任何相對路徑掛載 ⇒ 從 repo 根帶 -f 跑也成立）
docker ps            # 應看到 pg 容器 healthy

# ② 快層守門（秒~分鐘級，先跑這些，別急著跑全樹）
.venv/bin/python tools/check_defect_log_crossref.py
.venv/bin/python tools/check_pytest_baseline_sites.py          # ← 我實測 rc=1，見 5.2 ①
.venv/bin/python tools/sync_onboarding_baselines.py --check-snapshot   # ← rc=1，見 5.2 ③
.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_check_defect_log_crossref.py'   # ← rc=1，見 5.2 ②
.venv/bin/python -m unittest discover -s tools/tests -t tools/tests -p 'test_adr_xplat001_c1c2_lock.py'      # ← rc=1，見 5.2 ④

# ③ 全樹（約 6~7 分鐘）。🔴 等它的時候**不要**用裸 pgrep（見 §6 第 6 條）：
.venv/bin/python tools/run_root_unittests.py
```

### 5.2 🔴 已知會擋住 push 的四筆紅（我當回合逐筆現查，附修法）

| # | 紅在哪 | 逐字成因（我的實測） | 修法 |
|---|---|---|---|
| ① | `tools/check_pytest_baseline_sites.py` rc=1 | 「未納管的基線數字站點由 **114** 增為 **116** 支（棘輪只准下修）」。我用該檔自己的 `_line_is_claim()` 對 HEAD 版與工作樹版逐檔對帳，**兩個新開的家已定位**：`AutoClaude/tests/tools/test_local_ci_gate.py`（HEAD 0 → 現 1）與 `tools/lib/skip_group_policy.py`（HEAD 0 → 現 1）。兩處是**同一份**被引用的 skip 普查證據（一行裡同時有 `passed`／`skipped` 字樣與四位數） | 二擇一（總共 2 行）：在那兩行加行內 `<!-- baseline-ok: <WHY> -->`（**WHY 必填**，空 WHY 不具豁免力），或把數字改成指向 `ONBOARDING.md` §7。**不要**去調 `_UNMANAGED_HIT_FILES_RATCHET`——那是放寬 |
| ② | `test_check_defect_log_crossref.py` 1 筆 fail | `test_no_code_file_claims_a_round_beyond_the_ledger` 紅，該測試自己印出的座標指向 `tools/lib/sentinel_lifecycle.py`（**錨是那句「交 R84」，不是行號**——現查 `grep -n "交 R84" tools/lib/sentinel_lifecycle.py`）。那句話在 A-07 的誠實劃界段裡，而帳本現查當前輪＝83 ⇒ **程式碼自稱輪號超前帳本**（`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`） | 兩條路：① 把那句改成不帶輪號的寫法（「交下一輪」＋在帳本列上寫輪號）；② R84 首列一落地，帳本時鐘進 84，這一筆**自動變綠**。🔴 **但別因此拖著**：push 前它是紅的，而 push 前通常還沒落 R84 首列 |
| ③ | `sync_onboarding_baselines.py --check-snapshot` rc=1 | §7 表② **macOS 欄 presumed stale**：`autoclaude` 測試樹指紋在本輪回填之後又漂了（工具會逐字印出「舊 → 新」兩個值） | 在**所有包停工後**於出廠乾淨 venv 重跑 `--write --with-slow`。🔴 **不可**用 `--allow-pg-extras` 繞過——那會悄悄換掉表② 宣告的「出廠環境」語意（記憶裡已有這條教訓） |
| ④ | `test_adr_xplat001_c1c2_lock.py` 11 筆 fail | 全部同源：**文件側兩行還停在中途值**。該測試自己會印出座標與逐字理由（我實測時是「`AutoSDD_improving_107.md` 引用的護欄層總量不等於 `_FROZEN_GUARD_LINES` 實際總量——重釘之後文件沒跟上」＋「`CrossPlatform_R83_Scan_Findings.md` 帶著 `guard-total:R83` 標記，卻讀不出『起點 → 總量（+淨額）』三元組」）。**行號一律以當回合輸出為準**，本輪已實證行號錨會被並行改樹弄失準 | 把那兩行改成 §2.3 那個三元組（並保持標記行的形態可被判準讀出）。同輪必須**一起重生**發現文件 §B-1／§B-2 的逐檔表（逐檔值直接取 `--print-guard-lines` 的輸出，**不要手抄**——本輪交件版就是手抄漂了 195 行而無一物轉紅） |

> 🔴 **一個結構性觀察，值得寫進 R84 的計畫書**：④ 這一筆之所以會發生，是因為
> `_GUARD_TOTAL_DOC_GLOBS` 只有兩個**不遞迴**的 glob（`docs/04_planning/AutoSDD_improving_*.md`
> 與 `docs/06_quality/CrossPlatform_R*_Scan_Findings.md`）⇒ **`docs/04_planning/ADR/` 一個都不匹配**，
> 本輪 ADR 呈給掌舵者拍板的三個數字全錯而無一物轉紅（Architect A-04）。
> **本交棒書也不在那個掃描面內**——所以 §2.3 那個三元組是我手抄的，它**沒有機械物在守**。
> 這件事我照實寫在這裡，而不是等它靜默過期。

### 5.3 最高優先項（我依證據排序，理由逐條寫出）

1. **收輪對帳（§5.2 四筆）＋ push。**
   理由：這四筆全是分鐘級動作，但**不做就上不去**；而工作樹現在有數十個檔未進版控，
   `DEF-200-007` 那次事故（共用工作樹上的 `git stash` 瞬間清空 20 個檔）證明「未 commit 的工作樹」
   本身就是最大的單點風險。**這一項優先於任何新戰場。**

2. **A-07 的結構決定：額度／續航那一族的模組數是 LOC 棘輪的函數，不是領域的函數。**
   理由（Architect 逐檔實量）：那一族 10 個模組裡有數個貼著 tier 天花板，而其中**三支的立案理由
   逐字就是「消費端塞不下」**。後果已經發生——6C（85% 準備動作）做不了，不是被設計擋住，
   是被 tier 擋住（`tools/lib/quota_gate.py` 現查 400/400、餘裕 0）。
   ⇒ **先做這件事，再做 6C**，否則下一支模組就是第 11 個。
   三個選項（`AutoClaude/tools/check_loc_budget.py` 已有 `override_reason` 機制）：
   (i) 為 `tools/lib/` 這一族開一個具名 tier 並在帳本寫明理由；
   (ii) 合併 `tools/lib/quota_ledger.py` ＋ `tools/lib/quota_escalation.py`（兩者都小、都只被 planner import）；
   (iii) 把兩個 GC 面收成一處（`quota_escalation` 按齡刪、`tools/lib/sentinel_lifecycle.py` 按 session 刪
   ——「什麼時候可以刪任務書」現在有兩個家，改了一邊不會有任何東西轉紅）。

3. **`AutoClaude/tests/integration/test_concurrent_runs.py` 的 WHY 與夾具對齊（SD F-01，本輪第三筆「夾具比被測世界簡單」）。**
   理由：這一筆比另外兩筆嚴重，因為被測面是**預設持久化後端**。該檔 WHY 點名三個危害作為它
   非存在不可的理由，而夾具給的 id 恰好是那三個危害一個都碰不到的那一種。SD 在生產預設路徑上
   **重現成功**（同一個 playbook_id 併發多個 writer → 多筆 `StateRepositoryError`；撞名 id →
   一個 run 的 checkpoint 被靜默讀成別人的、另一個遺失），而 production 的 `playbook_id` 預設就是
   `Path.stem` ⇒ 「多個 run 並存」的真形態正是同一個 id。`DEF-200-043` 已立列。
   最低處置：把那三條 WHY 改寫成「已知未覆蓋」（留著就是「有鎖在守假話」）。

4. **6b 的兩個小出口（見 §3 那一列）。**
   理由：它是掌舵者訴求 6 裡**唯一每天都會用到**的一格——「我現在能派幾個 agent」。
   而現在連讀都讀不到，舵手只能靠手搭 `QuotaState` 餵進去。

5. **S1 的兩塊（docker 一行 ＋ AC darwin 剖面入表）。**
   理由：前者零程式改動，後者是「有量測值卻沒入表」而不是「量不到」——兩者都是低成本、
   直接讓 M6 的分子下降。

### 5.4 🔴 R84 首列落地會發生什麼（**我實測的答案與交接資訊不同，以本節為準**）

任務書轉給我的說法是「11 列既有未結列的承接輪次是 R83，R84 首列一落地，其中 3 列會變孤兒、
另 8 列永遠不轉紅」。**我用帳本自己的判準逐輪模擬過（帳本文字未動），今天的答案是：**

```bash
# 把 current_round 換掉逐輪模擬 orphan_backlog_problems()（不寫檔、不動帳本）
# 我實測：round=83 → 0 筆；round=84 → 0 筆；round=90 → 10 筆；round=200 → 10 筆
```

- **R84 首列落地當下：0 筆轉紅。** 那 11 列全部走硬規則② 的合法出口 (b)：其中 8 列靠自己狀態欄的
  「R82 改派」字樣，另 3 列（`DEF-101-992`／`DEF-101-995`／`DEF-101-998`）靠 **`DEF-200-040` 這一列
  跨列回執**——該列是本輪收斂時落的，狀態欄帶「改派」且點名了那三個 ID，並在散文裡把它們改派到 R84。
  ⇒ 交接資訊裡的「3 列會變孤兒」在 W10 量測的**那一刻**為真，`DEF-200-040` 落地後就不再為真。
- **但這不是好消息，是 `DEF-200-041` 的本體**：出口 (b) 只問狀態欄有沒有「改派」字樣，
  **不解析改派到第幾輪** ⇒ 寫過一次，那一列的承接輪號此後**不再被任何東西比較**。
  我模擬到 round=200 仍是同一批 10 筆、一筆不增，⇒ 那 11 列在任何未來輪都不會轉紅。
- **round=90 那 10 筆是誰**：本輪新落的、承接 R84 的 `DEF-200-*` 列（`010`／`015`／`020`／`021`／
  `022`／`023`／`026`／`041`／`042`／`043`）＋ 一列 `DEF-101-*`。⇒ **R84 真正的期限不是「首列落地」，
  是「R84 結束前這批有沒有交付」**。
- **建議的收緊**（`DEF-200-041` 已立列）：`_reassign_hit()` 命中時一併解析「改派到哪一輪」，
  並要求那個輪號 ≥ 當前輪。今天全部相關列都寫得出輪號 ⇒ 這個收緊**不會製造假紅**。

### 5.5 兩件殘留的機器動作（不是程式問題，但沒人做就一直在）

1. **孤兒哨兵還活著。** 我當回合 `launchctl list | grep AutoSDD_Sentinel_` 看到兩支：本 session 那一支
   ＋ 一支叫 `AutoSDD_Sentinel_s` 的探針孤兒（每 900 秒巡邏一次，永不自我解除）。
   `tools/lib/sentinel_lifecycle.py` 的 `sentinel_task_names()` 現在**與它一致**（回收臂本輪已接通、
   `gc_reaped` 事件已出現在痕跡檔），所以這不再是假陰性——**它只是需要有人跑一次**：
   `.venv/bin/python tools/session_resume_planner.py --remove-schtasks --task-name AutoSDD_Sentinel_s`
   （mac 上這條路走 `LaunchdBackend.disarm`；`DEF-200-029` 記為殘留機器動作）。
2. **`--remove-schtasks` 這個旗標名在 mac 上驅動 launchd**（A-10）。檔內拒絕改名的理由我認同
   （會動到既有取證指令與交棒書字串），但 mac 使用者被教去跑一個叫 `schtasks` 的旗標。
   零風險修法：加 `--remove-schedule`／`--verify-schedule` 為 alias，舊名保留。

---

## §6 本輪的方法論收穫（比個別缺陷值錢，請完整保留）

> 每一條都附「**為什麼它會再犯**」。沒有那一句的話，這一節就只是一份感想。

1. **fixture 比被測世界簡單＝最貴的一種假綠。**
   真機 `launchctl print` 的輸出是**巢狀**的，而 `tools/tests/test_mac_endurance_r83.py` 的 fixture 原本是
   **扁平**的 ⇒ 該檔 30 條綠**全部**成立在一個比真實世界簡單的世界裡，而那個缺陷（憑證的 `state`
   取到 `resource/jetsam coalition` 子區塊的值＝恆 `active`，而 depth-1 是 `not running`）
   **結構上不可能**被它抓到。處置不是多加一條鎖，是把 fixture 改成真機形狀，讓每一條既有的綠
   都改在真的形狀上成立。
   **為什麼會再犯**：寫 fixture 的人是為了讓測試「能跑」，而不是為了讓它「像真的」；
   而簡化後的 fixture **看起來更乾淨**，複審時反而更容易被誇。本輪同一個形態犯了**三次**
   （launchd 巢狀 vs 扁平／`pgrep` 實驗把 pattern 藏在腳本檔內 vs 真實事故是 inline `zsh -c`／
   `test_concurrent_runs.py` 的 5 個不同 id vs production 預設同一個 id）。

2. **鎖的假陽性要修鎖，不要改被測物。**
   `tools/tests/test_schedule_capability_parity.py` 把三個繼承本地共用夾具（而非直接繼承 `TestCase`）
   的類別判為「unittest 不收」——實測**其實收得到**（那三類貢獻了十幾支真的在跑的測試）。
   修法是給判準補「同一份檔案內基底鏈的不動點解析」。
   **為什麼會再犯**：照假紅去改被測物**更快**，而且改完是綠的。這次若照假紅把類別階層攤平，
   換來的是三份手抄夾具——**新的缺陷源，而且沒有人會發現它是這樣來的**。

3. **用重構繞過掃描器，比留著誤報更糟。**
   有一次把 assert 的期望值抽成區域變數，於是那幾個字面值不再出現在 assert 引數裡
   ⇒ 掃描器**整組失明**，而行內豁免標記同時變成 stale（它豁免的那一行已經不存在了）。
   兩件事都是靜默的。
   **為什麼會再犯**：重構在 code review 裡是**加分項**，而「這次重構讓某支掃描器看不見這一段」
   這件事**不會出現在 diff 裡**。判準：改完之後去問一次「本來會掃到這裡的東西，現在還掃到嗎」。

4. **「移除／判定用得動，列舉／建立壞掉，而且回報成功」——最難看見的一種缺席。**
   mac 續航鏈本輪先接通了**武裝臂**，回收臂沒接：`tools/lib/sentinel_lifecycle.py` 的 GC 硬走
   `powershell.exe`（mac 上 rc=127）⇒ `sentinel_task_names()` 回空清單，而 GC 逐字回報
   「沒有任何 AutoSDD_Sentinel_* 工作」＝**假陰性**，而同一刻 `launchctl list` 列著好幾支活著的哨兵。
   **GC 是專門用來發現增生的那支工具，它在 mac 上回報「一切正常」。**
   **為什麼會再犯**：「查不到」與「沒有」在版面上長得一模一樣，而**沒有東西**會告訴你
   取數管道回的是 rc=127。判準：任何「我查過了，沒有」的結論，都要先證明**取數管道本身**是活的
   （本輪的做法是讓 `list_jobs()` 在「量不到」時回 `None`、在「真的沒有」時回 `[]`——
   兩者刻意用不同的值表示）。

5. **載具層明文放棄某個語意，而決策層以為它成立。**
   `LaunchdBackend.arm()` 對 `at_expr`（要在哪個時刻跑）**刻意忽略**——launchd 這條路只吃間隔、
   不吃時刻。但 log 仍印「已重排到那個時刻」。⇒ 決策層（哨兵的四分支判定）以為「精確重排」成立，
   而載具層從來沒有實作它。
   **為什麼會再犯**：載具層寫「本參數不使用」是**負責任的**寫法，它的問題不在自己身上，
   而在**沒有人回頭去改呼叫端的訊息**。判準：介面上任何「本後端忽略此參數」的宣告，
   都必須在呼叫端有一個對應的降級訊息，而且那件事要有一條斷言。

6. **等待迴圈的 `pgrep` 兄弟互匹（本輪三支殼靜默卡死，是掌舵者看到「token 不再增加」才被發現）。**
   `until ! pgrep -f <字面>; do sleep N; done`：機制**不是**「匹配到自己」——`man pgrep` 的 `-a` 條目
   逐字寫著預設排除自己**與祖先**。真正的機制是**兄弟互匹**：pattern 字面寫在每一支兄弟行程的
   指令列裡，而 pgrep 不排除兄弟 ⇒ **≥2 支並行等待才會死鎖**（正好對上本輪三支殼）。
   命中集有**兩類**：對方的那支 `pgrep`，**以及對方的殼本身**（只要 pattern 出現在該殼 argv 裡）。
   🔴 **第一版給出的「正解」`pgrep -f "python.*<名稱>"` 同樣死鎖**——正則 `python.*X` 對自己的字面
   `python.*X` 成立（`.*` 會匹配到字面上的 `.*`）。
   **可用的正解（實測有效）＝字元類自我否定**：

   ```bash
   until ! pgrep -f "run_root[_]unittests" >/dev/null 2>&1; do sleep 5; done
   ```

   實測一次起三支並行等待全部立刻退出；同時對照組（真的有一支 argv 含該名稱的行程在跑時）
   同一條指令 rc=0 並印出 pid ⇒ **鑑別力沒有被犧牲**。其餘各自成立的路：`pgrep <名稱>`（不加 `-f`）／
   前景等待／`wait <pid>`。
   **為什麼會再犯**：這個缺陷的**表徵是完全靜默的**（沒有錯誤、沒有 log、沒有逾時），
   而且它**只在並行時發生** ⇒ 單支測試一定通過。目前這個配方只住在散文裡
   （發現文件 §F-4），**沒有任何東西**會在有人寫回裸字面時轉紅。

7. **訂正一句假話的時候，寫下另一句假話。**
   本輪至少三個獨立實例：① 發現文件 §E 新增一列「mac 上續航鏈只有武裝臂沒有回收臂」，
   而那件事在該列被寫下**之前 12 分鐘**就已經修好（時序由 `sentinel_lifecycle.py` 的 mtime 對上
   該列的寫入時刻）；② 同一列緊接著的半句說「兩支探針孤兒已被收掉」，而孤兒從頭到尾沒被收掉
   （同輪帳本 `DEF-200-029` 自己記著「需人跑 `--remove-schtasks`」，兩處直接互斥）；
   ③ §B-3 訂正了「複審未執行」這句話**在 §E 與計畫書兩處**，唯獨漏掉自己那一格 ⇒ 同一份文件
   在 §G 說「已執行」、在 §B-3 說「未執行」。有一位獨立驗證者一次抓到 7 筆這種形態。
   **為什麼會再犯**：訂正的人正在**專心看那句錯話**，而不是看磁碟；而且訂正文
   在版面上帶著 🔴 與「訂正」字樣，**讀起來比周圍的句子更可信**。
   判準：訂正的最後一個動作是**重新現查一次那個標的**，而不是重讀那句話。

8. **查詢載具自己也會騙人（本輪造成兩筆假陰性判讀）。**
   `grep` 的大小寫敏感度與鍵名拼法各造成一次「命中 0 ⇒ 結論：沒有這件事」，而東西其實在。
   這與 repo 內既有的兩個判例同型：Windows 上 `schtasks /query | grep` 回空而 `Get-ScheduledTask`
   查得到；Git Bash 的 `grep` 讀 CP950 編碼的 PowerShell 輸出時命中 0 而誤判「沒有失敗行」。
   **為什麼會再犯**：命中 0 是一個**看起來像答案的東西**。判準（本 repo 既有紀律
   「驗證載具本身要被驗證」）：任何「命中 0」的結論，都要先用一個**已知一定會命中**的
   對照 pattern 證明這條管道是活的。

---

## §7 誠實劃界（不粉飾）

### 7.1 本輪沒做到的

- **6b／6C／6e** 三格未做，`AC-(a)` 是架構天花板、`AC-(b)` 未動、`AC-(c)` 缺料（§3 逐列）。
- **訴求 4**（Windows 低級錯誤的根因歸因）本輪未重跑——本輪在 mac。
- **架構減法未達成**，且本輪淨減法為 0（§2.3）。
- **收輪未完成**：我寫本檔時四道閘門是紅的（§5.2），工作樹未 commit。
- **`_GUARD_TOTAL_DOC_GLOBS` 的掃描面沒補**（ADR 目錄與交棒書都不在內）；
  §B-1／§B-2 的**逐檔攤分**仍然沒有機械物（總量對、攤分錯就恆綠——本輪就這樣漂了 195 行）。
- **`pgrep` 那個配方沒有機械物**（§6 第 6 條）；它的長期居所應該是 `ONBOARDING.md` 的
  等待長跑指令那一段 ＋ 任務書「禁止事項」模板。
- **CLAUDE.md 鐵律五那段「假陽性 0 筆」的量測是空的**（QA F-3 實測：命中次數吻合，但唯一字面
  相差一倍以上，且母體絕大多數是散文——markdown 表格格、ASCII art、甚至 CLAUDE.md 自己那三行）。
  它住在每個 session 開場都會載入的那份檔裡。本輪未落探針。

### 7.2 只有作者自證的（依 M3「作者自證不計分」）

- **複審後的三個收斂包**（護欄層重釘、帳本 15 列、三支 `.md` 的逐格訂正）**沒有再被第三方看過**。
  這一段包含本輪最不利的那個數字的重釘（§2.3），依 `MIN_TESTS` 註記自己訂的規則，
  它與護欄層那一列都屬**中途值**、收斂完成後要再釘一次。
- 複審者各自點名的零獨立覆蓋組：mac launchd 續航後端那一族（`DEF-200-001`~`DEF-200-006`，
  列上標的「QA 複驗」是**同輪同包內的驗證者**）、skip 可發現性掃描器、
  `windows_skip_tags` 報表明細化、以及 `ADR-XPLAT-006` 的設計取捨。
- **本交棒書本身**：§2.1 那些 rc 是我自己跑的，§2.2 那些是採信別人的，§4 的成熟度評定是我的
  人工判斷——**沒有第三方看過這一份**。

### 7.3 Windows 側

- **Windows 側零覆蓋**：本輪全程在 macOS，所有「Windows 上會怎樣」的宣稱都是替身模擬或靜態推論，
  **不是量測值**。它同時是兩件事的解鎖前提：「聯集才是零」的量測面，以及
  `tools/tests@win32` 天花板值的當輪化。

<!-- absent-if: measured-at=2026-08-11 host=Windows -->
<!-- absent-if: measured-at=2026-08-10 host=Windows -->

> 上面那兩個標記就是這句話的證偽標的：`ONBOARDING.md` 的 `snapshot-fingerprints-win32` 錨
> 現查是 `measured-at=2026-08-09`；只要 R83 期間有人在真 Windows 上跑過
> `--write --with-slow`，那一欄就會變成本輪的日期，兩個 pattern 任一被搜到即證明本節這句話為假。
> （選這個錨而不是別的理由：它是 repo 內**唯一**會機械記下「這個平台上一次真機量測是什麼時候」
> 的地方——錨與宣稱同軸，才打得臉。）

### 7.4 🔴 舵手自己的三筆錯誤判讀（都被 agent 駁回並訂正，照實記）

這一小節刻意單獨列出來，因為「主控的根因判讀只是待驗假設」這件事在本 repo 已有記憶條目，
而本輪又是三筆實證：

1. **`pgrep` 死鎖的機制講錯**：原判讀是「匹配到自己」，實為**兄弟互匹**（`man pgrep` 的 `-a` 條目
   逐字說預設只排除自己與祖先）；而且第一版給出的「正解」`python.*<名稱>` **同樣死鎖**。
   兩筆都由 agent 實測駁回。
2. **「喚醒完全不 WORK」不成立**：稽核痕跡顯示 detect → observe → wait → probe **四步都對**，
   壞掉的是 probe **之後**那一段。把「最後一哩沒走過」讀成「整條鏈沒接通」，會導向去重修
   已經好的那四步。
3. **「哨兵消失」的根因判錯**：原判讀是 register 失敗，實為 `_defer` 那條路上的
   `sleep 3` 太短——它在父行程還活著的時候就 `bootout`，於是把自己剛啟動的續跑殺掉。
   修法是**等父行程真的退場**（`while kill -0 $p …`），痕跡見 §3 的 6d 那一列。
   ⇒ 「哨兵不在了」與「哨兵把自己拆了」表徵相同，而修法完全相反。

---

## §8 禁止事項（沿用既有紀律，本輪加兩條）

1. 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
2. 🔴 不准 `git stash`／`git checkout -- `／`git restore`／`git reset --hard`／`git clean`。
   **本輪的真實事故**：一個 subagent 在六包並行共用的工作樹上跑 `git stash -q -u --keep-index`，
   瞬間清空 16 個修改檔 ＋ 4 個未追蹤檔。靠 `git stash pop` 還原、未偵測到資料遺失——
   **但那是運氣不是設計**。已上線 `.claude/hooks/block_destructive_git.py`（PreToolUse，
   matcher `Bash|PowerShell`，動詞感知），它的誠實劃界寫在該檔 docstring 裡（不經殼的
   `subprocess`／MCP、Write/Edit 直接覆寫、腳本檔內的指令、別名／函式，它都擋不到）。
3. 不准為了讓紅變綠而刪測試／改成不比較／加 `skip`／放寬棘輪。
   **本輪的具體形態**：不得調高 LOC 預算來塞 6C（§5.3 第 2 項）；
   不得調 `_UNMANAGED_HIT_FILES_RATCHET` 來讓 §5.2 ① 變綠。
4. 🔴 **等長跑指令時不准用裸 `pgrep -f <字面>`**（§6 第 6 條，含正確寫法）。
5. 🔴 **不採信本檔任何「已通過」宣稱**。§2.1 那些 rc 是我當回合跑的，但你接手時樹已經不同了；
   §2.2 那些我根本沒跑。**重啟後第一件事是重驗**（zero-trust 對自己上一段也適用）。

---

## §9 本檔自己的體例自檢（我做了什麼、抓到自己幾筆錯）

寫完之後，我把本檔新增的每一個路徑／符號／數字宣稱拿回去對磁碟跑了一次，逐項見我的交件回報。
**我抓到自己三筆錯**，都是從任務書轉述進來的：

1. **「+5260 是歷來最大」缺一個限定**：per-entry 為真，per-round **R82 的 +5400 更大**（§2.3）。
2. **「macOS 欄首次回填」不成立**：該錨在 HEAD 上就存在，本輪的第一次是
   **provenance 首次完整**（兩個 `PRE_FIELD` 欄位換成真值）（§2.5）。
3. **「R84 首列落地會有 3 列變孤兒」已過期**：我逐輪模擬實測 **0 筆**——`DEF-200-040` 這列
   跨列回執在 W10 量測之後落地，把那 3 列一起接走了（§5.4）。

另有一筆我無法對帳、照實說：任務書轉述四方複審是「55 筆 findings、blocking 約 19 筆」，
而我逐條數四方原文得到 **findings 43 筆**（Architect 10／QA 10／SD 9／SA 14）、
**blocking 16 筆**（4／3／2／7）、**falsified_claims 32 筆**（6／9／5／12，與發現文件 §G 相符）。
三個數字沒有一組是 55／19。**以四方原文與 §G 為準**；本檔 §4 的 M2 結算用的是 32 這個分子。
