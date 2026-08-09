# R82 → R83 交棒書（🔴 R83 在 **macOS 真機** 上開跑）

> **給誰看**：一個剛坐到 Mac 前面、對 R82 一無所知的人。
> **本檔體例**：凡述及狀態（做了沒／過了沒／推了沒），一律**附現查指令**，不寫快照結論。
> 本檔裡的每一個數字都是**量測值不是常數**——照著指令重跑一次，以你跑出來的為準。
>
> 兩個路徑簡寫（本檔全篇沿用）：
> - Windows：`$r = 'D:\CursorProject\AISDCL_Agent'`、`$p = "$r\.venv\Scripts\python.exe"`
> - macOS：`r=$(git rev-parse --show-toplevel)`；直譯器見 §2.1（**這正是第一天要驗的東西**）

---

## §0 開場必讀（三分鐘，先做這四件事）

先確認你站在哪裡。下面四條在 mac 上逐條跑完，再往下讀。

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
git log -1 --format='%H %s'
git status --porcelain
git fetch origin && git rev-parse HEAD origin/main
```

- **本輪收在哪一個 commit**：`git log -1 --format='%H %s'` 應看到 `85363bf`
  開頭、訊息以 `feat(cross-platform): R82` 起。⚠️ 我寫這份交棒書的當下，**舵手正在推送**，
  所以「推上去了沒」你必須自己看：`git fetch origin; git rev-parse HEAD origin/main`
  兩個 sha 相同才算推成功。**我沒有推、也沒有 commit 任何東西**，本檔在你手上時可能仍未進版控。
- **本輪規模**：`git show --stat --format='' 85363bf` 末行為 `95 files changed, 13429 insertions(+), 1342 deletions(-)`（我當回合實測）。
- **輪號基準**：`python -c "import sys;sys.path.insert(0,'tools');import check_defect_log_crossref as C;from pathlib import Path;print(C.current_round(Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8')))"` → 我實測 `82`。R83 的第一個帳本列會把它推成 83。
- **先讀根 `CLAUDE.md`**，尤其〈Windows 側單一載具原則〉。🔴 **那一節在 mac 上不適用**，見 §6。

---

## §1 R82 做了什麼（一頁）

主題三條：**跨平台**（mac 就緒度）、**額度水位分軸**、**機密外洩守衛**。

| 面向 | 落地物 | 現查 |
|---|---|---|
| 額度水位分軸 | `tools/lib/quota_policy.py`（純判讀層）＋`tools/lib/quota_gate.py`（接線）＋meter schema `/2` 吐 `axes[]`，每軸自帶 `resets_at` | `& $p "$r\tools\tests\test_quota_policy.py"`；於 `tools/tests/` 跑 `& $p -m unittest test_quota_policy` |
| AutoClaude 側新軸 | `AutoClaude/autoclaude/core/ports/quota_meter.py`（port）＋`infra/adapters/file_quota_meter.py`（讀 `%TEMP%/autosdd_quota.json` 的檔案契約） | `Get-Content "$r\AutoClaude\autoclaude\core\ports\quota_meter.py" -TotalCount 40` |
| 機密守衛 | `tools/lib/secret_scan.py`（唯一判準層）＋`tools/git-hooks/pre-commit`（路徑形態那一層刻意零 python 依賴） | `& $p "$r\tools\lib\secret_scan.py" --tracked`（rc 0＝乾淨／1＝命中／2＝取數壞掉） |
| mac 就緒度 | 裸 `mktemp` 三站點補模板、`install_mac_nightly.sh` 補 `pmset`、`date +%N` 補判準與棘輪、hook 載具告警訊息改寫、`quota_policy.py` 刻意維持 3.9 可載入 | 見 §2 逐條 |

**四方複審**：Architect 判 **REJECT**，SA／SD／QA 三方判 **APPROVE_WITH_CONDITIONS**；
去重後 **14 筆 blocking，收斂 13**（commit 訊息逐字如此）。
🔴 **複審結論沒有落成一份文件**——計畫書點名的那份 CrossPlatform_R82_Review.md（於 `docs/06_quality/`）在磁碟上找不到
（現查：`Get-ChildItem "$r\docs\06_quality" -Filter '*R82*'` 只列得到 `Ledger_Closure` 與 `Scan_Findings` 兩份；
🔴 此處刻意**不以反引號寫出**那個路徑——本 repo 有機械物禁止以 code span 指名不存在的檔）。
複審發現只有兩筆進了帳本（`Select-String -Path "$r\docs\06_quality\AutoSDD_Defect_Log.md" -Pattern 'R82 複審'` → 我實測 2 命中，即 `DEF-101-996`／`997`，兩筆皆已 `fixed@R82`）。
⇒ **另外 11 筆收斂的內容今天只活在 commit 訊息裡**，這件事本身值得 R83 補記。

**三個治理數字**（都附現查，別引用本表的字面）：

| 量 | 我當回合實測 | 現查指令 |
|---|---|---|
| LOC total／cap | `total=20430 cap=20438`（餘裕 **8**，開場是 1） | `& $p "$r\AutoClaude\tools\check_loc_budget.py" --json` |
| 護欄層累積淨額 | `73823`（開場 68423，**+5400**）⇒ 本輪是加法，**Q2 判未達成** | `& $p "$r\tools\tests\test_adr_xplat001_c1c2_lock.py" --print-guard-lines` |
| 成熟度 M1~M6 | **六條裡 0 條達標** | `Select-String -Path "$r\docs\06_quality\CrossPlatform_Maturity_Criteria.md" -Pattern '現況總判'` |

---

## §2 mac 第一天的待辦（**本檔最重要的一節，可以直接照做**）

這一節來自 R82 那位 mac 就緒度掃描者交出的清單（原稿見 §2.9），我逐條複驗過**檔案路徑真的存在**，
但 🔴 **BSD 工具的實際行為在 R82 還沒有被觀測過任何一次**——下面每一格都是推論，你要做的就是把它們變成實測。

先確認這一節指名的東西在你的 checkout 上都在（一行，缺件當場看得到）：

```bash
git ls-files --error-unmatch .claude/hooks/_hook_launcher.py tools/lib/quota_policy.py \
    tools/lib/quota_meter.py tools/lib/skip_group_policy.py tools/check_hooks_liveness.py \
    tools/run_root_unittests.py tools/install_mac_nightly.sh tools/macos_smoke_local.sh
```

（rc=0 才代表八支都在。我在 Windows 側以 `Test-Path` 逐支確認過，上面這一行是同一件事在 mac 上的說法。）

### 2.1 直譯器版本（🔴 **最高優先，其他事情都掛在它上面**）

POSIX 側的 hook 載具是 `.claude/hooks/_hook_launcher.py`，它的 shebang 是 `#!/usr/bin/env python3`
（現查 `head -1 .claude/hooks/_hook_launcher.py`），而 macOS 原廠 `python3` 常年是 3.9，
repo 的 bootstrap 下限是 3.11（現查 `grep -n 'POSIX_MIN_PY' tools/lib/hook_wiring.py` → 我實測 `:397 POSIX_MIN_PY = (3, 11)`）。

```bash
/usr/bin/env python3 -c 'import sys; print("env python3 =", sys.version)'
/usr/bin/python3     -c 'import sys; print("system python3 =", sys.version)'
python3 -c 'import sys; sys.path.insert(0,"tools/lib"); import quota_policy; print("quota_policy 載入成功")'
```

- 第三行是本格真正的驗收：R82 刻意把 `tools/lib/quota_policy.py` 的 3.10+ 構造全部拿掉，
  讓它在 3.9 上載得起來（理由逐字在該檔 `:112-123`，現查 `sed -n '108,124p' tools/lib/quota_policy.py`）。
  **為什麼這件事要緊**：`quota_gate.py` 對它是 hard import，一炸就被 hook 端的 `try/except`
  收成 `None`，整條額度軸短路且**零訊息零痕跡**——`note_degraded()` 自己就住在 `quota_gate` 裡，結構上叫不到。
- 這個修復**在真機上還沒被驗過一次**。它今天只有 Windows 上的 AST 判準在守
  （`python -m unittest -v tools.tests.test_mac_readiness_r82` 的 `test_r82_the_quota_policy_module_is_loadable_on_39`）。

### 2.2 hook 到底活著沒有（🔴 fail-open，表徵與「修好了」一模一樣）

hook 載具解析不到時 Claude Code 只記一行 ERROR 就放行 ⇒ **六支守衛一起靜默消失，而螢幕上什麼都不會發生**。
唯一權威通道是 `--debug hooks`，行程表看不到那麼快的東西。

```bash
python3 tools/check_hooks_liveness.py
claude -p --model haiku --debug hooks --debug-file h.log "ok"
grep -E 'Hook SessionStart.*success' h.log
```

- 最後一行**有輸出**才算 hook 活著。沒有輸出而畫面一切正常＝最壞的那種情況。
- `check_hooks_liveness.py` 在 mac 上會對「PATH 上的 `python3` 版本低於下限」出聲；
  R82 已把那段訊息裡一句沒被驗證過的因果（宣稱 hook 一 import 就炸）改寫成風險宣稱
  （現查 `sed -n '460,490p' tools/lib/hook_wiring.py`）。**它在 mac day 1 必定會響，響了不等於壞了**，
  要靠上面第二、三行去分辨。

### 2.3 Keychain 憑證取得（R82 寫了 mac 分支，**在真機上沒有跑過一次**）

```bash
security find-generic-password -s 'Claude Code-credentials' -w
```

- 站點：`tools/lib/quota_meter.py:79` 的 `KEYCHAIN_SERVICE = "Claude Code-credentials"`
  與 `:149-157` 的取值分支（現查 `grep -n 'KEYCHAIN_SERVICE\|find-generic-password' tools/lib/quota_meter.py`，我實測 4 命中）。
- 🔴 **那個字串字面沒有權威來源可查證**，是照 Claude Code 的慣例推的。三種失敗都要分辨：
  ① 服務名不對 → `The specified item could not be found`；
  ② Keychain ACL 跳 **GUI 授權對話框**（第一次幾乎必跳，要按「總是允許」）；
  ③ 非互動情境（schtasks 對等物／`claude -p`）下回 `errSecInteractionNotAllowed`。
  ②③ 兩種在自動化路徑上是致命的，而 Windows 側**結構上重現不了**。

### 2.4 兩組互斥宣稱，一行指令各裁掉一組

repo 內對這兩件事各留了兩句互相矛盾的話，真值只有一個，而它只能在 mac 上量。

```bash
date +%s%N
mktemp; echo "mktemp rc=$?"
```

- `date +%s%N` **尾巴若是字母 `N`** ⇒ BSD 不支援奈秒 ⇒ `AutoClaude/tools/sd06_w3_staging_dryrun.sh`
  的 `$(( END - START ))` 會拿到非數字而算術崩。該檔今天仍有 17 行命中
  （現查 `grep -c 'date +%s%N' AutoClaude/tools/sd06_w3_staging_dryrun.sh`）。
  R82 已補判準與存量棘輪（`grep -n '_GNU_DATE_NANOS_RE' tools/tests/test_bash32_compat.py`），
  **但站點一個都沒改**——因為在裁決真值之前改是猜。
- 裸 `mktemp` 那一組 R82 已經動手了：三個 git hook 站點全部補了模板
  （現查 `grep -n 'mktemp' tools/git-hooks/pre-commit tools/git-hooks/pre-push`），
  `AISDLC_SDD/scripts/ci-gate.sh:170-176` 那句矛盾散文也訂正了。
  **仍要跑這一行**：它是那句「BSD mktemp 必須帶模板」的唯一直接證據，今天 repo 裡沒有人跑過。

### 2.5 排程對等物（睡著的 Mac 會不會醒）

```bash
pmset -g sched
launchctl print gui/$(id -u) | grep -i autosdd
```

- R82 已把 `pmset` 接進安裝器（現查 `grep -c pmset tools/install_mac_nightly.sh` → 我實測 29 命中；
  R82 動工前是 0）。`WakeToRun` 在 launchd 沒有直接對應，真正的對等物是 `pmset repeat wakeorpoweron`
  ——launchd 只在機器醒著時補跑，不會把睡著的 Mac 叫醒。
- 憑證紀律與 Windows 同構：**憑證是那個「下次執行時間」的值，不是指令的 rc**。
  `pmset -g sched` 印不出下一次喚醒時刻就等於沒排到。

### 2.6 skip census：把 `tools/tests@darwin` 那一格填掉（`DEF-101-960`）

```bash
python3 tools/run_root_unittests.py 2>&1 | tee /tmp/rootunit.log
grep 'skip census' /tmp/rootunit.log
```

- 抄 `[skip census] tools/tests@darwin 共 N 支：…` 那一行，**逐格**填進
  `tools/lib/skip_group_policy.py` 的 `_RUNTIME_SKIP_CEILING` 與 `_RUNTIME_SKIP_CEILING_MAX`，
  然後把 `_UNMEASURED_RUNNER_PROFILES` 裡那一列移除（現查 `grep -n 'tools/tests@darwin' tools/lib/skip_group_policy.py` → 我實測 4 命中）。
- R82 已經把分母補好了：`_FULL_SUITE_RUNNERS` 收了 darwin 那一列、`_FULL_SUITE_RUNNERS_MIN` 由 5 改 **7**。
  ⇒ 你要做的只剩「填實測值」這一步，那是把 mac 的 skip 從「無上限可無聲長大」轉成有牙的**唯一**動作。
- ⚠️ 上面那一行 `tee` 只用在收集 log，**不要拿它的 rc 當閘門結論**（管線會吃掉 rc；本 repo 為此付過學費）。
  要 rc 就單獨跑一次不接管線的 `python3 tools/run_root_unittests.py; echo "rc=$?"`。

### 2.7 `TMPDIR` 在三種情境是不是同一個目錄

```bash
echo "gui : $TMPDIR"
ssh localhost 'echo "ssh : $TMPDIR"'
sudo -n printenv TMPDIR || echo "sudo : (被清掉或需要密碼)"
```

- 為什麼要問：額度快取是一份**檔案契約**，兩端各自算路徑——
  harness 側 `tools/lib/quota_meter.py:137` 與套件側 `AutoClaude/autoclaude/infra/adapters/file_quota_meter.py:35`
  都走 `Path(tempfile.gettempdir()) / "autosdd_quota.json"`（現查
  `grep -n 'gettempdir' tools/lib/quota_meter.py AutoClaude/autoclaude/infra/adapters/file_quota_meter.py`）。
- macOS 的 `TMPDIR` 是**每使用者每 session** 的 `/var/folders/...`，不是 `/tmp`。
  gui／ssh／sudo 三者不同時，寫的人與讀的人會各自看著一個空目錄，而**兩邊都不會報錯**。
  Windows 上 `%TEMP%` 幾乎恆等，所以這個失效模式在 Windows 上結構上量不到。

### 2.8 這一節裡「已經修掉」與「還要驗」的分界（免得白花時間）

R82 動了不少 mac 相關的**程式碼**，但**沒有一行是在 mac 上跑出來的**。分界如下，逐格附現查：

| 代號 | R82 動了什麼 | R83 還要做什麼 |
|---|---|---|
| MAC-01 裸 `mktemp` | 三站點補模板＋散文訂正（`grep -n mktemp tools/git-hooks/pre-commit`） | 跑 §2.4 那一行留下實證 |
| MAC-02 darwin skip 天花板 | 補進分母、立 `DEF-101-960`（`grep -n 'DEF-101-960' tools/lib/skip_group_policy.py`） | §2.6 填實測值 |
| MAC-03 hook 載具告警 | 訊息改寫＋`test_mac_readiness_r82.py` 補 3.9 判準（`ls tools/tests/test_mac_readiness_r82.py`） | §2.1／§2.2 真機交叉驗 |
| MAC-04 `pmset` | 接進安裝器（`grep -c pmset tools/install_mac_nightly.sh`） | §2.5 驗它真的排得進去 |
| MAC-05 `date +%N` | 補判準＋棘輪，**站點未動**（`grep -n '_GNU_DATE_NANOS_RE' tools/tests/test_bash32_compat.py`） | §2.4 裁決後再決定怎麼改 |

### 2.9 原稿在哪裡

那位掃描者的完整原稿（含每一筆的 evidence 與 proposed_fix）落在 scratchpad，**不在版控裡、會被清掉**：
`C:\Users\wuwei\AppData\Local\Temp\claude\d--CursorProject-AISDCL-Agent\67a47258-fcad-4980-9d4d-a190fb187290\scratchpad\R82_scan_mac.md`。
進了版控的濃縮版是 `docs/06_quality/CrossPlatform_R82_Scan_Findings.md` §E
（現查 `Select-String -Path "$r\docs\06_quality\CrossPlatform_R82_Scan_Findings.md" -Pattern 'MAC-0'`）。
⚠️ 你在 mac 上讀不到那個 Windows scratchpad 路徑 ⇒ **要用就趁還在 Windows 上時先搬進 repo**。

---

## §3 mac 真機的覆蓋規模：待辦第一天就會撞到的東西

根層 `tools/tests` 那一棵今天在 Windows 上 skip **38 支**（`platform=37`／`env-disabled=1`），
數字與逐格分群逐字登記在 `tools/lib/skip_group_policy.py:301-315`
（現查 `Select-String -Path "$r\tools\lib\skip_group_policy.py" -Pattern 'skip census. tools/tests@win32'`）。
其中只有 darwin 跑得到的那一群，repo 自己記著 **26 支**（`:627-628` 的 `_COMPLEMENTARY_PROFILE` 註解），
而 `docs/04_planning/AutoSDD_improving_106.md` 的 S3 那一列寫的是 **27 支**
（現查 `Select-String -Path "$r\docs\04_planning\AutoSDD_improving_106.md" -Pattern '只有 macOS 跑得到'`）。
🔴 **兩個數字互斥，而且哪一個都不能靠讀檔裁決**——它是執行期的量，只有 §2.6 那一跑能定案。

加上另一件事：macOS CI 自 2026-08-05 起連續多跑都是 `steps=0`（帳務停擺，不是測試失敗），
所以那一群測試**在世界上任何一處都沒被執行過**，mac 真機這一側是零覆蓋。
現查（需 `gh` 已登入）：`gh run list --workflow macos-compat-ci.yml --limit 10 --json createdAt,conclusion,name`
——看 conclusion 與實際執行步數，全 `failure` 且原因是帳務就是本段描述的狀態。

<!-- absent-if: "tools/tests@darwin": { -->

> 上面那個標記是本段宣稱的**證偽標的**：`_RUNTIME_SKIP_CEILING` 一旦真的收了 darwin 那一格
> （§2.6 做完就會），這個字面就會在磁碟上找得到，本段當場轉紅並要求改寫。
> 這不是形式：它逼「零覆蓋」這句話有一個到期日。

🔴 **心理準備**：R83 第一次在 mac 上跑 `python3 tools/run_root_unittests.py`，就是那 26（或 27）支測試
**在世界上的第一次執行**。要有心理準備會冒出**從未被執行過的真紅**——R79 有先例：
一設 DSN 就暴露 4 個從未執行過的 failed。那些紅**不是你弄壞的**，是本來就在那裡、只是沒有人看過。
發現時請逐支立帳，不要為了讓當天的閘門好看而把它們 skip 掉。

---

## §4 額度軸的待辦：R82 量到了、但沒有做完的兩件事

### 4.1 `horizon` 乘數未參數化（🔴 掌舵者訴求 6b 的核心，**R83 首要**）

`tools/lib/quota_policy.py:282` 的 `_MULTIPLIER = {near: 2.0, mid: 1.0, far: 0.5, none: 0.5}`
是**模組層寫死的常數**，不像其他每一個門檻那樣有對應的環境變數
（現查 `Select-String -Path "$r\tools\lib\quota_policy.py" -Pattern '_MULTIPLIER|EnvVar\('`
——我實測 `_MULTIPLIER` 5 個站點、`EnvVar(` 13 列，而那 13 列裡**沒有任何一列**指向這三個乘數）。
該檔自己的註解逐字寫「這三個數字是**挑的**，機械物守的是方向與單調性，不是數值」。
⇒ 訴求 6b 驗收的「(二) 最佳化」那一半，今天連可調的旋鈕都沒有。

🔴 **修它是規格層變更**（要動合議決策表 `decide()` 的 `cap`／`rec` 兩個角色），
不是加一個環境變數就結束——請先讀 `sed -n '36,70p' tools/lib/quota_policy.py` 那三段設計理由再動手。

**現查它今天實際上長什麼樣**（這一段我當回合真的跑過，數字是量出來的）：

```powershell
# 於 tools/tests/ 直接叫 decide()，固定 weekly 57%@8233min（far），把 session 的 reset 掃過去
& $p -m unittest test_quota_policy
```

我用一支臨時探針直接呼叫 `quota_policy.decide()` 掃過去，得到的是：

| session reset | 雙軸（weekly 57%@8233m ＋ session 0%） | 單軸對照組（只有 session 0%） |
|---|---|---|
| 1／15／30 分 | `band=notice cap=4 rec=4` | `band=free cap=None rec=16` |
| 60／120／359 分 | `band=notice cap=4 rec=4` | `band=free cap=None rec=8` |
| 361／1440／8640 分 | `band=notice cap=4 rec=**2**` | `band=free cap=None rec=4` |

**怎麼讀這張表**（🔴 這裡與交棒給我的說法不同，見 §7-③）：
- **煞車那一半是活的**：far 軸把 `rec` 由 4 壓到 2。
- **加速那一半仍然量不出來**：near（×2）與 mid（×1）在雙軸下**同樣是 4**，
  因為 `rec ≤ cap` 而 `cap = min(逐軸 cap) = 4` 把兩者夾平了。
  ⇒ 使用者原句「Token 剩 30 分鐘就 Reset、還有 100% 沒用，就應該可以加速」在真實的雙軸情境下
  **仍然表達不出來**。這就是 R83 要治的那一格。

### 4.2 AutoClaude 側沒有東西刷新額度快取（**唯一未收斂的那一筆 blocking**）

明文降級並機械化登記了，劃界逐字寫在 `AutoClaude/autoclaude/core/ports/quota_meter.py` 檔頭
（現查 `Get-Content "$r\AutoClaude\autoclaude\core\ports\quota_meter.py" -TotalCount 35`）。

- **病**：全 repo 唯一會寫那份快取的是 harness 的 `tools/lib/quota_gate.py::refresh_quota_blocking()`，
  而它唯一的到達路徑是 Claude Code 的 PreToolUse ＋ 扇出型工具。
  ⇒ AutoClaude **獨立跑**時（沒有 Claude Code session、或整場沒人派 agent），
  快取過了 TTL 就恆回 `None`＝量不到，而引擎側對「量不到」的既有行為是**不擋**。
  也就是說：**額度軸會在無人看管那一跑上安靜地不存在**，遲到時間無上界。
- **為什麼 R82 不補**：三條硬邊界的交集（取數要 OAuth＋網路＋端點知識，那整包住在 harness；
  `.importlinter` 的 `no-harness-import` contract 禁止反向依賴；走 subprocess 或在套件內重寫都只是換載體）。
  **正解是第三方寫入者**（排程／哨兵定期刷快取），那是 harness 那一側的工作項。
- **機械物**：`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py::TestTheQuotaAxisHasNoEngineSideRefresher`
  ——哪天有人補了寫入者，那一條會紅並要求回來改掉那段檔頭。⇒ 你補完之後**必然**會撞到它，那是設計。

---

## §5 其他待辦（逐筆我都到磁碟上確認過，沒驗過的我會說）

### 5.1 帳本：兩筆承接 R83

現查：`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`
（我當回合實測 `未結列數＝71／全部 147 列｜warn=86 fail=98`，rc=0）。

- `DEF-101-995`（P2，open→R83）：`ratchet_history_problems()` 分不出「追加」與「改寫」——
  把史料末元素改寫成更大的值、或把整段史料截成單一高值，兩種都是綠的。
  探針輸出在 `docs/06_quality/CrossPlatform_R82_Scan_Findings.md` §F。
  修法方向：已釘過的**前綴必須不可變**（只准延長）。⚠️ 別做成「與當回合實測相等」，那是另一個已知的幫兇形態。
- `DEF-101-998`（P2，open→R83）：見 §5.3。
- `DEF-101-960`：見 §2.6。
- `DEF-101-992`：帳本 85 筆裡有 **62 筆結構上結不掉**，它們與 `tools/lib` 三條逐字相等基線硬耦合，
  追加一句改派就會讓基線失準、閘門當場紅。⇒ 只持有帳本的包做不到，要連基線重釘權一起給。

### 5.2 使用者指南寫著與 mac 覆蓋現況矛盾的話

`docs/AISDLC_Agent_UserGuide.md:29` 逐字寫「雙平台開發完全相容」
（現查 `Select-String -Path "$r\docs\AISDLC_Agent_UserGuide.md" -Pattern '雙平台開發完全相容'`）。
對照 §3：mac 真機那一側今天沒有任何執行證據。⇒ 這句話在 R83 跑完 §2.6 之前**不成立**，
跑完之後才有資格重寫成一句有憑證的話。**別直接刪**——它是一個要被實測換掉的宣稱，不是錯字。

### 5.3 同一份文件住兩個家、同一段 PG 設定住四個家（`DEF-101-998`）

`AutoClaude_Guide.md` 兩個副本已經漂移：`docs/` 版標 0.3.0／2026-05-14，`docs/04_planning/` 版標 1.1.0／2026-06-13。
而**同一段 PG 設定**其實住四個家（另加 `README.md` 與 `DB_Only_Switch_Runbook.md`）。
現查：`Get-ChildItem "$r\AutoClaude" -Recurse -Filter 'AutoClaude_Guide.md' | Select-Object FullName,Length`。
⇒ 同一把密碼要在四處各清一次，**漏一處就等於沒清**。修法是定一份為 SSOT、其餘改成指針。

### 5.4 playbook ＋ PG 端到端實跑（訴求 7(b)，R82 只排除了開箱阻塞）

R82 把「開箱第一秒就死」那幾道拿掉了（`config.yaml` 的非法旗標、T01 要讀的規格檔、產出路徑改道），
**但一次端到端真跑都沒有做**（真跑會呼叫 Claude Code 寫檔並燒額度）。

```powershell
docker ps --filter name=autoclaude_pg --format '{{.Names}} {{.Status}}'
Get-Content "$r\AutoClaude\.gitignore" -TotalCount 105 | Select-Object -Last 12
```

- 🔴 **訂正一筆交給我的過期資訊**：`AutoClaude/scripts/example_workspace/` 的 ignore 規則
  **R82 已經加好了**（`AutoClaude/.gitignore:95-102`，只放行輸入 fixture
  `AutoClaude/scripts/example_workspace/docs/sdd_auth_spec.md`）。
  ⇒ 你不必再補，但**真跑前請先看一眼**確認它還在——這正是這種規則最容易被誰順手刪掉的時機。
- 真跑後 `git status --porcelain` 必須乾淨。不乾淨就是 ignore 面有縫，先修縫再繼續。

### 5.5 機密守衛的兩個已知缺口（都沒關）

- **`--no-verify` 可以完全繞過**：三層守衛全部掛在 git hook 上，`tools/git-hooks/pre-commit:12` 逐字
  記著緊急跳過的方式，`:35-36` 逐字承認「`--no-verify` 的缺口另由 pre-push 與回歸鎖兜」。
  現查 CI 那一側有沒有人守：`Select-String -Path "$r\.github\workflows\*.yml" -Pattern 'secret_scan'`
  ——我實測**零命中**，也就是雲端沒有第二道。
- **git 歷史仍可讀到已遮蔽的 PG 密碼**：本輪裁定只遮當前樹。
  🔴 **真正的收尾動作是在 DB 端輪換那把密碼**，那不在本 repo 射程內，也不是 R83 動 code 能解決的。
  這件事請直接向掌舵者確認要不要做，不要自己決定「先放著」。
- `tools/lib/secret_scan.py` 有已登記的失明面（非 DSN 形態／非 `.env` 檔／DSN 被拆行，
  R82 十處命中裡有六處它結構上看不到）。補判準會撞上該檔檔頭的取捨（寧可漏報也不要假報），
  ⇒ R82 只登記診斷、**不動判準**。要動之前先讀 `Get-Content "$r\tools\lib\secret_scan.py" -TotalCount 30`。

---

## §6 禁止事項（沿用既有紀律，加本輪兩條）

- ❌ 不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`／跳過或註解掉失敗測試。
- ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限。棘輪只准往收斂的方向動，
  而且動它的那一次要說得出「什麼事實變了」。
- ❌ **不准把任何 `.env` 加進 index**（掌舵者安全紅線）。`git add -f` 也不行。
- ❌ 不准以「act／Docker 全綠」代替 mac 真機結論。容器只外推 bash 語言層，
  coreutils 與 exec bit 的執行期行為外推不過去。
- ❌ 不准把本檔任何數字當常數引用。每一個都附了現查指令，請重跑。
- 🔴 ❌ **不准在 mac 上沿用 Windows 的〈鐵律一〉**。根 `CLAUDE.md` 那一節禁用 Bash 工具、
  一律走 PowerShell——那是**Windows 專屬**的結論，理由是雙載具的決策負荷。
  **在 mac 上 bash 才是正確載具**；守衛本身也是這樣寫的（`block_bash_on_windows.py` 在非 Windows 一律 exit 0）。
  單平台判準不可無條件外推，這是 repo 自己付過學費的教訓（`DEF-101-766` 同型）。
- 🔴 ❌ **「不閃窗了／沒有紅字」永遠不算驗收通過**。hook 載具失效是 fail-open，
  螢幕表徵與「修好了」完全相同 ⇒ 正負兩面要一起看（§2.2 那三行）。

---

## §7 我複驗到、與交接資訊不符的地方（請以本節為準）

我逐項重跑了交給我的每一個數字，有五處對不上。**列在這裡不是挑錯，是因為採信它們會讓 R83 走錯方向。**

1. **未結列數**：交接說「85 → 70」。我當回合現查是 **71／147 列**
   （`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`）。
   `docs/06_quality/CrossPlatform_R82_Ledger_Closure.md:681` 記的是 `70／144`——
   那是收尾量測當下的讀數，此後同一個 commit 內帳本又長了 3 列。**方向（大幅下降）不變，數字要現查。**
2. **`[MAC-NATIVE-ONLY]` 支數**：交接說 29。磁碟上有兩個互斥的數字：`tools/lib/skip_group_policy.py:627-628` 寫 **26**、
   `docs/04_planning/AutoSDD_improving_106.md` S3 那一列寫 **27**，沒有任何一處寫 29。
   ⇒ 見 §3，這一格只能靠 §2.6 那一跑定案。
3. **`horizon` 加速器**：交接說「實測加速器在真實情境下是死的，`rec` 全部是 4」。
   我當回合直接呼叫 `quota_policy.decide()` 重量，**那已經不成立**——R82 已把聚合改成兩個角色
   （`cap` 逐軸取 min、`rec` 用最短期程那一軸的乘數），雙軸下 far 會把 `rec` 壓到 **2**。
   **仍然成立的是**：near 與 mid 在雙軸下被 `cap` 夾成同一個值（4）⇒ 加速那一半仍表達不出來。
   ⇒ §4.1 已按實測改寫。**`_MULTIPLIER` 未參數化這一半是真的**，我逐行確認過沒有對應的 `EnvVar`。
4. **`example_workspace` 的 ignore 規則**：交接說「真跑前要先給它 ignore 規則」。
   R82 已經給了（`AutoClaude/.gitignore:95-102`）。⇒ §5.4 改成「先確認它還在」。
5. **`DEF-101-996`／`997`**：交接說四筆（995~998）都承接 R83。
   帳本上 996 與 997 的狀態欄逐字是 `fixed@R82`，只有 995 與 998 是 open→R83
   （現查 `Select-String -Path "$r\docs\06_quality\AutoSDD_Defect_Log.md" -Pattern 'DEF-101-995|DEF-101-996|DEF-101-997|DEF-101-998'`。
   🔴 這裡刻意用四個**完整**編號的 alternation，而不是把共同前綴加上尾碼字元類（中括號區間）：
   `tools/tests/test_defect_id_reference_integrity.py` 的引用正則是「前綴 ＋ 一段數字 ＋ 後面不接
   英數」，而中括號**不**在那個 lookahead 的排除集合內 ⇒ 字元類寫法會被讀成一筆指向**空號**
   （截到共同前綴為止的那個短編號）的引用，讓根層 unittest 閘門轉紅、擋下 push。
   本註記自己因此也不寫出任何會被截短的編號字面，同該鎖檔自身 `_syn()` 的慣例）。

另外兩處是 **repo 自己的文件在本輪之內就過期了**，我沒有改它們（不是我的持有面），登記在這裡：

- `docs/04_planning/AutoSDD_improving_106.md:177` 那一列把本檔記成還沒建立——你讀到這句話時它已經在了。
- 同檔 `:178` 那一列說本輪沒有跑四方複審，而複審實際上跑了（commit 訊息記 14 筆收斂 13，
  帳本另有兩列標著 R82 複審）。現查兩者：
  `Select-String -Path "$r\docs\04_planning\AutoSDD_improving_106.md" -Pattern 'CrossPlatform_R82_Review|R82_HANDOFF'`。
  ⇒ **R83 開場請順手把 §6 那兩列改成實況**，並補一份複審結論文件（見 §1 末段）。

---

## §8 我沒有做的事（誠實劃界）

- **我沒有 commit、沒有 push、沒有 `git add` 任何東西**。本檔寫進工作樹就結束。
- **我沒有跑根層 unittest 全套**（>10 分鐘，且舵手同時在 push、並行跑會互踩成假紅）。
  我只跑了兩支與本檔體例直接相關的鎖（見交件回報）。⇒ 本檔對「閘門今天是不是全綠」**不做任何宣稱**。
- **我沒有碰任何 mac**。§2 每一格都是靜態站點加上 repo 內互相矛盾的自陳所推出來的，
  BSD 工具的實際行為在本輪一次都沒有被觀測過。這正是 R83 存在的理由。
