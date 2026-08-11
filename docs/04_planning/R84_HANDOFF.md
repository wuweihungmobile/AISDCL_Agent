# R84 → R85 交棒書（R84＝**macOS 第二輪、九包並行**）

> 前一份＝[`R83_HANDOFF.md`](R83_HANDOFF.md)。本輪計畫書＝[`AutoSDD_improving_108.md`](AutoSDD_improving_108.md)；
> 掃描發現＝[`docs/06_quality/CrossPlatform_R84_Scan_Findings.md`](../06_quality/CrossPlatform_R84_Scan_Findings.md)。
>
> 🔴 **本檔體例**：會漂移的量測值一律不寫死，只寫「哪一支載具會印出它」。
> 凡本檔寫出的 rc，都是**我（收尾單人窗口）當回合真的跑過**的；我沒跑的一律標明。

---

## §0 開場必讀（跑完再往下讀）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
git log -1 --format='%H %s'                      # 本輪收在哪個 commit
git status --porcelain | wc -l                    # 工作樹是否乾淨
.venv/bin/python -c "import sys;sys.path.insert(0,'tools');import check_defect_log_crossref as C;from pathlib import Path;print(C.current_round(Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8')))"
```

1. **我沒有 commit、沒有 push。** 我離開時工作樹**仍未**全部進版控——現查
   `git status --porcelain | wc -l`。保全點是 tag（`git tag -l 'R84-wip*'`），
   全部由 `git stash create` 產生（**不動工作樹**的唯一保全手法）。
2. **不採信本檔任何「已通過」宣稱。** §② 那些 rc 是我當回合跑的，你接手時樹已經不同了。
   **重啟後第一件事是重驗**——`.venv/bin/python tools/run_root_unittests.py; echo rc=$?`。
   zero-trust 對自己上一段也適用。
3. **先讀根 `CLAUDE.md`。**〈Windows 側單一載具原則〉在 mac 上不適用（鐵律一的 hook 非 Windows 一律 exit 0），
   但**鐵律三**（跨平台自問）、**鐵律四**（宣稱先於查證）、**鐵律五**（毀滅性 git）、
   **鐵律六**（等待機制自己靜默壞掉）四條**兩個平台都適用**，本輪抓到的東西幾乎全落在那四條上。
4. 🔴 **本輪 Windows 側零真機量測。** 凡本檔提到 Windows 的地方，一律是靜態推論；
   **它們全部尚未驗證**，逐筆清單在 §5.2（每一項都附可直接貼的現查指令）。
   本輪跑過哪些東西、在哪個平台上跑的，現查
   `.venv/bin/python tools/run_root_unittests.py`（末段會印 `[skip census] tools/tests@darwin`）。

---

## §1 一句話總結

**R84 是第一次「九隻手同時在同一棵樹上」的一輪。** 它產出兩類東西：
① 額度／續航鏈的治本（訴求 6b／6C）與彈窗的**定位**（訴求 7）；
② 兩次真實事故，共同結構是「**哪一棵樹現在有人在寫，沒有任何一層看得到**」。

---

## §2 我這一回合真的跑過的（附 rc）

| # | 指令（皆從 repo 根、絕對路徑 python、**讀 rc 不接管線**） | rc |
|---|---|---|
| 1 | `.venv/bin/python tools/run_root_unittests.py` | **0**（`OK (skipped=44)`）。🔴 收尾窗口**動工時實測 rc=1**，五筆紅逐筆收在 §2.2，沒有一筆是靠放寬門檻收掉的 |
| 2 | `.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` | **0**（第二次重釘後：淨額 `82838→82838 (+0)`、逐檔漂移 **0 支**＝凍結表逐字等於工作樹） |
| 3 | `.venv/bin/python tools/check_defect_log_crossref.py` | **0** |
| 4 | `.venv/bin/python tools/check_pytest_baseline_sites.py` | **0** |
| 5 | `.venv/bin/python tools/check_ntfs_paths.py` | **0** |
| 6 | `.venv/bin/python tools/check_hooks_liveness.py` | **0** |
| 7 | `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json` | **0** |
| 8 | `.venv/bin/python tools/sync_onboarding_baselines.py --check-snapshot` | **0**（動工時 rc=1＝表② macOS 欄四格 presumed stale；已用**乾淨 venv**（只裝 `.[dev,notifications]`）跑 `--write --with-slow` 回填，**未用** `--allow-pg-extras`。🔴 收尾窗口為了 `MIN_TESTS` 重釘**又跑了一次 `--write`**（不帶 `--with-slow`⇒ 只動表① 的 `loc-baseline-live:`／`rootunit-baseline-live:` 兩格，表② 的慢格原封不動；同樣**未用** `--allow-pg-extras`） |
| 9 | `cd AutoClaude && ../.venv/bin/python -m pytest tests -q` | **0**（`4344 passed, 73 skipped`） |
| 10 | `cd AISDLC_SDD && bash scripts/ci-gate.sh` | **0**（逐軌計數 v0.01:1478／v0.30:1747／scripts:333） |

> 🔴 **上表那些 rc 是我當回合跑的，不是承諾**：我跑完之後這棵樹沒有被凍結（tag 是保全點不是凍結）
> ⇒ 你讀到它的時候不保證還成立，照 §0 第 2 條重驗。
> 本檔唯一寫死的**累積**量測值是 §2.1 的護欄層三元組（那三個數字受 `doc_guard_total_problems()` 對帳，寫錯即紅）。

### 2.1 護欄層重釘（本輪**兩次**，皆在收尾單人窗口）

- 起點 → 總量（淨額）：**79083 → 82838（+3755）**。逐檔表在 findings §B-1／§B-1b（**直接取工具輸出，非手抄**）。
  🔴 這是**逐輪加總**（款(10) 判的就是加總）：第一次 79083→81738（+2655），第二次 81738→82838（+1100）。
- 🔴 **為何有第二次**：第一次重釘時該列自陳「全輪唯一一次」，其後仍有四包尾段交付落地
  ⇒ 那句話已成過期事實。`_GUARD_LINES_REPIN_LOG` 是 append-only，**不回頭改既有列**
  （就地把過期宣稱改成真話正是款(7) 指紋要防的形狀）⇒ 更正寫在新追加的第二列，兩列並存即稽核痕跡。
- `_GUARD_LINES_REPIN_LOG` 現有 R84 **兩列**（各含 `[非淨減法輪]` ＋ 指名 findings 當逐檔清單的家）；
  `_REPIN_LOG_FROZEN_PREFIX_LEN` 由 20 → **21**（第一次）→ **22**（第二次，把新列一併納入
  append-only 指紋；`_REPIN_LOG_MAX_UNFROZEN_TAIL=1` 本可留在 21，推到 22 是**更嚴**的方向）、
  `_REPIN_LOG_HISTORY_SHA256` 同步重釘為 `51db3d36…`。
- 🔴 **未動任何門檻**：`_REPIN_ROUND_NET_CAP` 仍是 5400（本輪加總 3755 ≤ 5400，不需要放寬）；
  款(12) 的到期義務（R85 前下修到 ≤3200）**原封不動留給下一輪**。
- 🔴 **自我指涉**：重釘會改變該檔自己的行數 ⇒ 我是**迭代到不動點**才收的
  （現查憑證＝`--print-guard-lines` 印出 `(+0)` 且「逐檔漂移 0 支」）。

### 2.2 收尾窗口動工時的五筆紅，與各自的收法（**零放寬**）

> 這五筆全部是「前四包停工後才第一次被一起量到」的東西。逐筆列出收法，
> 因為其中兩筆的正解**看起來像放寬**（加豁免標記、把下限往上釘），必須寫清楚為什麼不是。

| # | 紅 | 根因 | 收法 |
|---|---|---|---|
| 1 | `test_check_defect_log_crossref` 輪號鎖 | `test_adr_xplat001_c1c2_lock.py` 內 **4 處** `R87`／`R99` 合成語料（`git show HEAD:` 實查該檔 HEAD 版命中 0 ⇒ 本輪新增） | 4 行**行尾**加具名豁免 `round-label-ok`。**不是放寬**：那正是該掃描器 docstring 指定的兩條正解之一（合成語料），且豁免是具名的、逐行的 |
| 2 | `test_doc_loc_baseline_freshness_r60` 2 筆（幽靈符號 ＋ 平台模擬） | **同一根因**：`test_context_budget_guard.py` 以反引號指名一個只是方法名**前綴**的字串（全 repo 無此定義） | 改寫成真實存在的完整符號名 `test_after_the_nested_runner_the_pin_is_still_up`。平台模擬那一筆是同一鎖在三個模擬平台各紅一次，根因收掉即全綠 |
| 3 | `test_platform_neutral_paths` POSIX 絕對路徑字面值 | F3 新落地的 ZT-04 斷言用 `"/ADR/"` 比對 | 行尾 `# posix-abs-ok:`。**先查證再豁免**：該比對對象由 `guard_total_docs_in_worktree()` 的 **`as_posix()`** 產生 ⇒ Windows 上不會渲染成反斜線，是真的假陽性 |
| 4 | `test_subprocess_encoding_hygiene` E501 存量棘輪（139 → 141） | **我自己造成的**：第 1 筆的 4 個行尾豁免，其中 2 行因此超過 100 寬 | **重新折行**（把 `R<n>` 那一段搬到較短的行、豁免跟著走），不是調高棘輪。收完 `tools/tests/` 過長行回到 139 |
| 5 | `ZeroDepEnvironmentDiscriminationTest` ——`環境問題` not found in `❌ discovery 佔位測試 4 筆…` | `MIN_TESTS` 舊值 **3095 已低於零相依沙箱的收集數** ⇒ 探針走「下限通過」那一支、把整棵樹再跑一次，而不是走 `report_floor_failure` 印環境歸因 | **把 `MIN_TESTS` 往上釘到 3279**（取 runner 當場印出的計數直接填入、零加減推算）。🔴 **方向是收緊不是放寬**：它是**下限**，往上釘＝讓「靜默蒸發若干支測試仍全綠」的窗口變小。這是該常數註記自己逐字載明的處置（R82／R83 各發生過一次，本輪是第三次）。同步站點 `ONBOARDING.md` §7 表① 已在同一次變更內以 `--write` 回填 |

**旁證（不是我推的，是量出來的）**：第 5 筆修好後，同一支全樹閘門的牆鐘由 **700.755s 降到 360.518s**
——正是該註記預告的「下限太舊 ⇒ 探針不再提前判紅而是實跑整棵樹」那條放大路徑被關掉。
收尾實測 `下限釘選通過：發現 3279 個測試（下限 3279）`，兩數相等。

---

## §3 訴求逐條結算

| 訴求 | 結算 |
|---|---|
| **1** 兩平台零相容性問題 | **只成立 mac 半**。Windows 側零真機量測 ⇒ 本輪不得宣稱「兩平台」 |
| **2** 架構簡潔／不重複模組 | 生產碼側**有減法**（三支超標檔回到 tier 內、抽出三個共用層）；**護欄層是加法**（+3755，兩次重釘加總）。合起來不是淨減法輪 |
| **3** 兩邊不落差 | 補的是 compat-CI 的**觸發面**（`paths:` 三支新檔），判準面在 Windows 上本輪一次都沒跑 |
| **4** Windows 低級錯誤歸因 | **本輪未跑**（在 mac）。載具＝`.venv/bin/python tools/probe/misstep_attribution.py` |
| **5** 挖深清債 | 帳本本輪新落一批 `DEF-200-*`（**列數／區間不寫死，現查＝`grep -cE '^\| DEF-[0-9]+-[0-9]+ \| [0-9-]+ \| R84' docs/06_quality/AutoSDD_Defect_Log.md`**；R84 收尾訂正 `DEF-200-085`：原文寫的「38 列」被自附配方當場證偽〔訂正當回合＝39〕）；LOC tier 治本；`DEF-101-947` 結案。🔴 **帳本 bytes 死結（`DEF-200-053`）未治本、未結任何列**——兩格餘裕皆 0（`83/83`、`121758/121758`）。**「三條治法都是放寬」為假**：另有兩條非放寬出路（超長列長文搬進具名證據檔／天花板改為現查值 ≤ 史料末元素），**未做**的理由是工作量與持有面，不是無解 |
| **6** Token 監控＋排程喚醒 | **6b／6C 治本落地**（`_pace_of()` 的 null 軸否決權、`--pace` 出口、hub tier 解封）。🔴 **6e 只做到「失效可偵測」**；**6d 仍零端到端驗證** |
| **7** Windows 彈窗 | 🔴 **已定位（哨兵 tick，每 15 分鐘一次，掌舵者當面確認）、未驗證**。兩層防護失效時**皆零痕跡** ⇒「不閃窗了」不算驗收通過 |
| **S1** skipped | PG skip 真因定位、剖面登記面補兩個缺口；天花板零餘裕與 5/5 假紅的問題**存量未清** |
| **S2** 帳本警告線 | `check_defect_log_crossref.py` rc=0，三類 warning 仍在往線上靠（數字現查 `--unresolved-count`） |
| **AC**（三個 AutoClaude 問題） | 🔴 **R84 收尾訂正（本列原文「本輪零交付」被本輪自己的工作樹證偽）**：AC-(c) 本輪**有**交付——回歸鎖 `AutoClaude/tests/plugins/test_notification_quiet_after_session_r84.py` 檔頭第一行逐字寫著它服務的是哪一個 AC 標籤，`notifier.py`／`notification_plugin.py` 同 commit 一起改，帳本座標 `DEF-200-060`（狀態＝已定位、真機未驗，即上面訴求 7 那一列）。⇒ **真正零交付的是 AC-(a)／AC-(b)**（連續第三輪順延）。不得再以「已交棒」代替結算 |

<!-- absent-if: measured-at=2026-08-11 host=Windows -->
<!-- absent-if: measured-at=2026-08-12 host=Windows -->
<!-- absent-if: R84 / AC-(a) -->
<!-- absent-if: R84 / AC-(b) -->

> **上面四個標記是本節兩筆「某物不存在」宣稱的證偽標的。** 語意＝該字面一旦在任何 tracked
> 檔裡搜得到（`git grep -F`，標記行自己不算），對應那句話即為假 ⇒ 本節當場轉紅。
>
> · **前兩個**對訴求 3 那一列（判準面在 Windows 上的執行狀態）。錨＝`ONBOARDING.md` 的
>   `snapshot-fingerprints-win32`，它是 repo 內**唯一**會機械記下「這個平台上一次真機量測是
>   什麼時候」的地方（現查該欄＝`measured-at=2026-08-09`）。只要 R84 期間有人在真 Windows 上
>   跑過 `python tools/sync_onboarding_baselines.py --write --with-slow`，那一欄就會被改寫成本輪
>   日期，兩個 pattern 任一即命中。**錨與宣稱同軸，才打得臉**——這是沿用 R83 §7.3 的判例。
>   列兩個日期是因為本輪跨兩天（帳本列標 08-11、收尾 commit 在 08-12 04:15）。
>
> · **後兩個**對 AC 那一列。**正對照就在本輪內**：AC-(c) 的交付在磁碟上留下的字面，就是上列
>   點名的那支回歸鎖 `AutoClaude/tests/plugins/test_notification_quiet_after_session_r84.py` 的
>   **檔頭第一行**（開頭逐字帶著輪號＋AC 標籤）；而 (a)／(b) 兩個標籤在全庫的唯一出現處是上面
>   那兩行 `absent-if:` 宣告本身（判準會過濾宣告行，見該鎖的 `falsified()`）⇒ 真實命中 0。
>   ⇒ 這個形狀**不是假想的慣例**，它在同一輪裡已被證明會亮，且亮與不亮在同一族內分得開。
>   （本段刻意**不逐字寫出**那個字面：寫出來它自己就會變成一筆命中，讓上面這句話當場失真。）
>   🔴 **誠實劃界**：它是**命名慣例依賴**——若下一輪的 AC 交付不採用該檔頭字面，這一格接不住；
>   它抓得到「照本 repo 慣例交付了」，抓不到「用別的形狀交付了」。
>
> ⚠️ 標記是**區塊級**的（判準以「標題→下一個標題」為單位收集），所以本節兩筆宣稱共用這四個
> pattern；任一命中時，訊息會把本節兩列一起點名，需人工分辨是哪一列被打臉。方向是**過報**
> 而不是漏報，故不另拆小節（拆了會把上面那張表切斷）。

---

## §4 成熟度 M1~M6（判準 SSOT＝[`CrossPlatform_Maturity_Criteria.md`](../06_quality/CrossPlatform_Maturity_Criteria.md)，本節**不重抄判準表**）

| # | 本輪判定 | 理由（依 SSOT 的門檻欄逐字比對） |
|---|---|---|
| **M1** | ❌ | 合取的兩半都沒到。UEP 半：ADR-XPLAT-002 §8.1 至今無回執。**護欄行數半**：本輪總量**上升**（+3755）⇒ 「連續三輪不上升」歸零重算。🔴 本輪的交付是給這條棘輪**裝上第一個代價**（款(10)(11)＋只准下修的後設鎖），不是達標 |
| **M2** | **N/A** | 依門檻①：本輪**未執行四方複審**（九包並行後直接進收尾窗口）⇒ 一律判 N/A，**禁記 0** |
| **M3** | ❌ | 本輪新增判準絕大多數是**作者自證**；既有鎖庫隨機 20 支的抽樣面至今一次都沒做過 |
| **M4** | ❌ | 本輪自己就修了數筆「散文宣稱 ≠ 實作射程」（例：`SHELL_FORM_CENSUS` 的分母、`_EOL_LF_SCOPE` 把 `.py` 釘成必須放行） |
| **M5** | ❌ | 兩個方向的**未攔到題數**現跑 `.venv/bin/python -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix`（`setUpClass` 末行印）。程式碼語意層仍是 0 |
| **M6** | ❌ | 兩棵樹的 skip 現跑：`.venv/bin/python tools/run_root_unittests.py`（印 skip 明細）＋ AutoClaude 側 `--census-only`。本輪未達「零未執行」 |

**總判：0／6**，與 R80~R83 相同。M1 因本輪上升而**更遠**。

---

## §5 R85 首日可貼的指令與**尚未做完**的事

### 5.1 開工前先確認基線（照順序，全部讀 rc 不接管線）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
# ① 先把 PG 起來——否則 AutoClaude 側會回來一批「其實只是 docker 沒開」的 skip
docker compose -f docker-compose.ci.yml up -d; echo rc=$?
# ② 快層守門（秒~分鐘級）
.venv/bin/python tools/check_defect_log_crossref.py > /tmp/a.log 2>&1; echo rc=$?
.venv/bin/python tools/check_hooks_liveness.py      > /tmp/b.log 2>&1; echo rc=$?
.venv/bin/python tools/check_ntfs_paths.py          > /tmp/c.log 2>&1; echo rc=$?
.venv/bin/python AutoClaude/tools/check_loc_budget.py --json > /tmp/d.log 2>&1; echo rc=$?
# ③ 全樹（數分鐘）。🔴 等它的時候不要用裸 pgrep（見 §6 第 2 條）
.venv/bin/python tools/run_root_unittests.py > /tmp/root.log 2>&1; echo rc=$?
```

### 5.2 🔴 Windows 真機重驗清單（**本輪全部 Windows 宣稱都是靜態推論，一項都沒驗**）

> 這一節是 R85 的**最高優先項**。理由不是「還沒做」而是結構性的：
> 訴求 7 的兩層防護**失效時皆零痕跡**，而其中一層的失效表徵（不閃窗）**與修好完全相同**
> ⇒ 只看畫面必被騙，只有下面第 2 行拿得到正面憑證。

```powershell
# ① 載具還在不在（守的是 settings.json 宣告的 Windows hook 載具是否真的存在）
Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR '.venv\Scripts\pythonw.exe')   # 必須是 True

# ② hook 真的還在跑（唯一權威通道；行程表看不到那麼快的東西）
#    🔴 R84 訂正：原文用相對路徑 `h.log`，與〈鐵律二：一律絕對路徑〉直接抵觸——
#    PowerShell 工具的 cwd 跨呼叫持續，兩行落在不同 cwd 時第二行會讀到別的檔或讀不到。
$hookLog = Join-Path $env:TEMP 'autosdd_r85_hooks.log'
claude -p --model haiku --debug hooks --debug-file $hookLog "ok"
Select-String -Path $hookLog -Pattern 'Hook SessionStart.*success'   # 有 success 才算活著

# ③ 哨兵這一層：黑框的來源（掌舵者當面確認「一閃即消、約每 15 分鐘一次」）
Get-ScheduledTask | Where-Object TaskName -like 'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime
```

**逐項要回答的問句**（三項本輪皆**尚未**有憑證，現查指令即上面三行）：
彈窗是否真的停止／`pythonw.exe` 載具是否解析得到／`-WindowStyle Hidden` 與 `-Principal` S4U 是否真的生效。
帳本座標 `DEF-200-063`（承接輪次 R85）。

### 5.3 掌舵者要跑的三行彈窗定位指令

即 §5.2 的 ①②③ 三行。🔴 **驗收條件是正負兩面一起看**：
「不閃窗」單獨成立**不算**通過（那正是 fail-open 的表徵）；必須同時拿到 ② 的 `success` 行。

### 5.4 其餘尚未關的缺口（逐筆附現查指令）

- **訴求 6e 本體仍未達成**（喚醒睡著的 Mac 需 `pmset repeat`＋sudo＝機器設定不在 repo 裡）。
  本輪只做到「失效可偵測」。現查：`.venv/bin/python -m unittest tools.tests.test_mac_endurance_r83`；
  帳本 `DEF-200-059`。
- **護欄層淨減法義務**：**R86 之前**必須出現一次淨額 ≤ 0 的重釘，否則款(11) 轉紅。
  現查：`.venv/bin/python -m unittest tools.tests.test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet`；
  義務居所＝ADR-XPLAT-002 §8.1 item 15。**本輪是加法輪，義務順延而非兌現。**
- **帳本 bytes 死結（`DEF-200-053`）仍未治本**：超標列豁免清單與 excess 天花板兩格餘裕皆 0。
  現查：`.venv/bin/python tools/check_defect_log_crossref.py`；可行出路＝把超長列的長文搬進具名證據檔，屬獨立一包。
- **跨 session 的工作樹保護仍缺**：PreToolUse 守衛結構上看不到別的 session（§6 第 1 條）。
  現查守衛射程：`.venv/bin/python -m unittest tools.tests.test_block_destructive_git_r83`；帳本 `DEF-200-084`。
- **四方複審本輪未執行** ⇒ M2 判 N/A、M3 的第三方注入面為空。
  現查本輪新增判準有哪些：`git diff --stat HEAD -- tools/tests`。

---

## §6 方法論收穫（每條附「為什麼它會再犯」）

1. **劃界不是防護。** `block_destructive_git.py` 的檔頭 R83 就寫著「別的路徑我擋不到」，
   R84 就被那條路徑打中（另一個 session 的 `git stash` 清空 91 檔）。
   **為什麼會再犯**：寫下劃界那一刻的感受與「修好了」幾乎一樣，而劃界不會讓任何東西轉紅
   ⇒ 它在帳面上是零成本的結案。對策：凡「已知缺口」必須有一個**會到期的時點**（如 ADR §8.1 item 15），
   不能只有一段散文。
2. **等待／確認的機制自己會靜默壞掉**（鐵律六）。
   **為什麼會再犯**：壞掉的表徵與「還在正常進行」完全相同，而它發生在**沒有任何觀測者**的平面上
   （指令字串、rc 讀數、「我掛了 Monitor 沒有」都不會變成 repo 裡的檔案）。
   對策是派工前就決定「誰來叫醒我」，掛不上就換形態派工。
3. **判準在、數字也印得出來，但那條路永遠走不到**（6b 的 `min(1.0, …)` 恆夾住）。
   **為什麼會再犯**：這種缺陷在 rc 上與「沒有缺陷」完全相同，只有把**否決權的持有者**逐一問一次才看得見。
4. **低報與過報一樣貴。** 本輪又抓到數筆「其實早就有鎖在守，卻被記成沒人守」——
   它會讓下一輪有人去補一支已經存在的鎖，也讓治理數字是假的。
   **為什麼會再犯**：棘輪只讀那張表自己說什麼，從不問「這句話是真的嗎」。
5. **重釘會改變被重釘的那份檔自己**（自我指涉）。
   **為什麼會再犯**：第一次量到的數字看起來就是答案，而它在寫回去的那一刻就過期了。
   對策＝迭代到 `--print-guard-lines` 印出 `(+0)` 且「逐檔漂移 0 支」為止。

---

## §7 誠實劃界

- **Windows 側零覆蓋**：本輪一次都沒上 Windows 真機。
- **四方複審未執行**：依 M3「作者自證不計分」，本輪絕大多數新判準沒有第三雙眼睛。
- **本輪是加法輪**：護欄層 +3755（兩次重釘加總），方向與 M1 相反。
- **§4 的 M2 是 N/A 不是 0**：分子為零只是因為沒人來查。
- **§D 的事故沒有偵測到資料遺失，但那是運氣不是設計**：當時若有 agent 正在寫檔，
  `git stash apply` 會衝突或直接覆蓋（座標見 findings §D）。

<!-- absent-if: measured-at=2026-08-11 host=Windows -->
<!-- absent-if: measured-at=2026-08-12 host=Windows -->

> **第一項（Windows 側）的證偽標的即上面兩個標記**，錨與同軸理由同 §3 表末那段說明：
> `ONBOARDING.md` 的 `snapshot-fingerprints-win32` 現查是 `measured-at=2026-08-09`，本輪期間
> 只要有人在真 Windows 上跑過 `--write --with-slow`，該欄就會變成本輪日期而讓這一句轉紅。
>
> 其餘四項刻意**不掛** `absent-if:`：它們講的是「程度／狀態」（複審沒人來查、本輪方向是加法、
> M2 該判 N/A、事故沒造成損失是運氣），**沒有一個可以被 grep 打臉的標的**——硬掛一個搜不到的
> 字面只會製造一條永遠不會亮的假證據，那正是 R81 §3.2 的失效形態。

---

## §8 禁止事項

1. 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
2. 🔴 **不准任何毀滅性 git**：`git stash`（push／pop／apply／drop／clear）／`git checkout -- <path>`／
   `git checkout -f`／`git restore <path>`／`git reset --hard|--merge|--keep`／`git clean`／`git switch -f`。
   **`git stash create` 是唯一例外且是指定手法**（它不動工作樹）。
   🔴 **本輪的真實事故是跨 session 的**：`.claude/hooks/block_destructive_git.py` 只讀**本 session**
   的指令字串 ⇒ 它擋不住別的 session。**多開一個 session 在同一棵樹上工作，等於把這道守衛關掉。**
3. 不准為了讓紅變綠而刪測試／改成不比較／加 `skip`／放寬棘輪。
   本輪的具體形態：不得調高 `_REPIN_ROUND_NET_CAP`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`
   （兩者只准下修）；不得調高 LOC 預算來塞新功能；不得為了讓帳本 bytes 死結變綠而拆掉牙。
4. 🔴 等長跑指令時不准用裸 `pgrep -f <字面>`（兄弟互匹會讓 `until ! …` 永不退出），
   也不准 `nohup <cmd> &`（脫離 harness 的完成追蹤）。
5. 🔴 **開工第一件事與收工最後一件事，都要重建保全點**：
   `S=$(git stash create); git tag -f R85-wip-$(date +%H%M) "$S"; echo "preserved=$S"`。
