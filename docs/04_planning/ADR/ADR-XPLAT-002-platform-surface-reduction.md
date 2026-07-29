# ADR-XPLAT-002：跨平台「需驗證平面」收斂架構與其可機械追蹤的下降判準

| 欄位 | 內容 |
|------|------|
| **狀態** | Accepted（**設計交付**）。本 ADR **不在 R60 執行任何遷移**——理由見 §7，那不是保守，是四條實測出來的阻礙 |
| **日期** | 2026-07-29（R60 收輪；量測時點見 §2 各條，HEAD `e3a5c53`、工作樹 dirty 81 筆） |
| **決策層** | 綜合者裁決（R60 三案九鏡對抗式複審之收斂）。**政策層變更**（護欄層 LOC 預算、`ci-gate.ps1` fallback 刪除）仍須使用者／PM signoff，見 §5 Phase 2 |
| **適用範圍** | 根層 `tools/`、`AutoClaude/tools/`、`AISDLC_SDD/scripts/`、`AISDLC_SDD/AISDLC_SDD_v0.<LATEST>/tools/` 四棵樹的 `.sh`／`.ps1`／Python 核心，及其登記表 `tools/check_script_parity.py`／`tools/check_wrapper_thinness.py`。**不適用**於 `.github/workflows/`（§6 邊界 6）、`AISDLC_SDD/AISDLC_SDD_v0.XX/` 凍結版（走 `ADR-XPLAT-001`） |
| **驅動來源** | R60 Architect 裁決：「所有改善都發生在『驗證這件事有沒有被做對』的那一層」 |
| **關係** | `ADR-XPLAT-001` 管「凍結版要不要回補」；本檔管「同一語意的雙平台實作要不要收斂、怎麼證明真的收斂了」。兩者互不覆蓋，體例沿用 001（含 §6「判準邊界」的誠實劃界段） |

---

## 1. 背景與觸發

使用者的原始要求是「**全面檢視多平台相容性的設計架構…進行最佳化改善設計**」。
R60 三輪修復之後，Architect 的裁決逐字如下：

> R60 三輪修復的主導模式是「一個 finding → 一支鎖」。護欄層 `tools/tests/*.py` 由 52 支/20,188 行
> 漲到 56 支/23,329 行，**已超過它所護的 AutoClaude 生產碼行數**；而 round 2 六筆新發現
> **零筆落在生產碼**。真有架構收斂的只有四項（`_ps_engine` 引擎挑選 N 份→1 份 SSOT、
> `_script_scan_surface` 遞迴列舉 4 消費者→1 份、`archive_defect_log.py` 由用完即丟腳本升為
> 可重跑程式並接兩道閘門、`ADR-XPLAT-001` §4.3 由散文升為 C1/C2 機械鎖）。
> **但跨平台相容性本身沒有出現任何抽象層**——沒有統一的 platform capability 層、沒有把
> pwsh/bash 雙實作收斂成單一契約 + 兩個 adapter，所有改善都發生在「驗證這件事有沒有被做對」
> 的那一層。裁決＝**部分達成，不足以稱最佳化**。

### 1.1 護欄層行數趨勢（我親自量測，三個時點，同一台機器同一 HEAD）

```
$ date -u +"%Y-%m-%dT%H:%M:%SZ"; cat tools/tests/*.py | wc -l; ls tools/tests/*.py | wc -l
2026-07-29T00:45（約）  24793   56
2026-07-29T00:55:08Z    25080   56      # python splitlines 法
2026-07-29T00:55:37Z    25091   56      # cat|wc -l 法（同一秒 python 法為 25092，差 1＝一支檔無尾隨換行）
```

**這三個數字是本 ADR 最重要的一項實據，而且它的意義不是「行數很大」**：
同一個 HEAD、同一台機器，**10 分鐘內成長 298 行、30 秒內成長 12 行**，檔數 56 完全不動。
兩包並行修復正在寫入 `tools/tests/`。Architect 引述的 23,329、盤點者量到的 23,786、
其他鏡量到的 23,999／24,000／24,261 與我的 25,091 **全部都是真的**——它們量的是不同秒。

⇒ 由此導出本 ADR 的第一條設計約束：**任何以「護欄層行數下降」為成果的宣稱，
必須在同一個 commit 上前後各量一次；跨時點比較在本 repo 當前狀態下是噪音，不是訊號。**
（這條同時否決了 C 案「G 淨 −51」那種跨包比較的記帳方式。）

### 1.2 `check_script_parity` 現況值（我親跑，逐字）

```
$ python tools/check_script_parity.py > /tmp/sp.txt 2>&1; echo REAL_RC=$?
REAL_RC=0
✅ run_tlc_tracks（LATEST FSM 軌錨點集合）：6 個 step 標籤一致
✅ pytest 釘選一致：三處皆 pytest==9.1.1
✅ git longpaths 旗標鎖：兩側皆含 '-c core.longpaths=true'（macos 1 處／windows 2 處）
✅ thinness 交叉鎖：5 對薄殼登記與 10 支 hash 釘選鍵集合一致
✅ 腳本註冊完整性：13 對 + 18 支單邊皆已納管（遞迴掃描 3 棵 SSOT 樹 + LATEST tools）

$ python tools/check_wrapper_thinness.py > /tmp/wt.txt 2>&1; echo REAL_RC=$?
REAL_RC=0
✅ wrapper 薄殼守門通過（10 支殼 hash 釘選 + 行數上限皆正常）
```

### 1.3 Architect 指定的刻度量不到任何一案要做的事（三案獨立同結論，我複驗成立）

Architect 給的判準是「`13 對 + 18 支單邊` 必須下降」。但那個數**數的是「檔案成對存在且已納管」**：

- 刪掉 `ci-gate.ps1` 的 36 行第二實作 → 兩支檔都還在 → 仍算 1 對。
- 把 `install_git_hooks` 從「決策豁免」改成「hash 釘選」→ 檔數不變 → 仍算 1 對。
- `.github/workflows/` 的兩支 compat-ci（另一盤點者實測合計 1,974 行、canonicalize 後 27.6% 重複、
  alert job 100% 重複）**根本不在這把尺的掃描面內**（該檔輸出逐字自述「遞迴掃描 3 棵 SSOT 樹 + LATEST tools」）。

三個提案角度**各自獨立**算出「照 Architect 的刻度，我的設計得分 0」，而三者算出「真正會動的數」時
落點是**同一個集合**：`_EXEMPT_PAIRS ∪ _TLC_TRACK_ENROLLED`。這個一致性是本 ADR 換刻度的依據
（§4），不是為了讓成績單好看。

---

## 2. 機械事實（我親自實測，非引述；每條附指令與時點）

量測時點統一為 **2026-07-29T00:55Z 前後**，HEAD `e3a5c53`，`git status --porcelain | wc -l` = **81**（工作樹髒，兩包並行修復進行中）。

### 2.1 登記表現況

```
$ python <scratchpad>/uep.py            # 只 import 既有登記表，不新增度量檔
REAL_RC=0
UEP = 8 (_EXEMPT_PAIRS=7 + _TLC_TRACK_ENROLLED=1)
THINNESS_ENROLLED = 5
PINNED_SHA256 = 10
SINGLE_SIDED_EXEMPT = 18
MIN_EXTRACT_COUNTS = 1
AC = 42
```

`_EXEMPT_PAIRS` 七個鍵（實測逐字）：`AISDLC_SDD/scripts/ci-gate`、`AISDLC_SDD/scripts/install-hooks`、
`AutoClaude/tools/install_git_hooks`、`AutoClaude/tools/run_local_nightly`、
`LATEST/tools/arch_fitness/run_self_evolution`、`LATEST/tools/init_project`、
`LATEST/tools/install_hooks/install_post_commit`。
驗算：`5 + 1 + 7 = 13` 對，與 §1.2 的「13 對」逐字相符。

### 2.2 🔴 `ci-gate` 不可能納入 `_THINNESS_ENROLLED`（我以記憶體注入實測，零寫檔）

A 案把這一步標成「0 行程式碼、純登記類別遷移、風險低」，並寫 gate_proof 要求輸出「7 對薄殼 / 14 支 hash 釘選」。
兩者都不成立：

```
$ wc -l AISDLC_SDD/scripts/ci-gate.sh AISDLC_SDD/scripts/ci-gate.ps1
  281 AISDLC_SDD/scripts/ci-gate.sh
   80 AISDLC_SDD/scripts/ci-gate.ps1
$ grep -n 'MAX_LINES' tools/check_wrapper_thinness.py
73:MAX_LINES = 100
288:        if line_count > MAX_LINES:
$ python - <<'EOF'      # 模擬 S7 的登記遷移 + 補兩支 hash
  ... T._PINNED_SHA256[rel] = T._sha256_text(T.normalized_content(Path(rel))) for ci-gate.{sh,ps1}
  ... P._THINNESS_ENROLLED.add('AISDLC_SDD/scripts/ci-gate')
EOF
✅ thinness 交叉鎖：6 對薄殼登記與 12 支 hash 釘選鍵集合一致
cross_lock_ok = True
problems = ['AISDLC_SDD/scripts/ci-gate.sh：281 行超過薄殼上限 100 行 —— 業務邏輯應收斂進 tools/dev_start.py，不應長在 wrapper 內']
```

三個機械事實：
1. 交叉鎖（`check_script_parity.py` 的 `expected = {stem+ext for stem in _THINNESS_ENROLLED for ext in ('.sh','.ps1')}`）
   **強制**把同名另一側一併拖進 `_PINNED_SHA256`——登記 `ci-gate` 就等於把 281 行的 `ci-gate.sh` 送進薄殼檢查。
2. `MAX_LINES` 判的是 **raw** 行數（281），不是正規化後的 115。
3. 交叉鎖印的是「**6 對／12 支**」（單納編 ci-gate 一對），A 案 gate_proof 寫的「7 對／14 支」在該步永不可能出現
   ——驗收字串本身錯，複審者只能二選一：判假紅，或放行不看。

⇒ **`ci-gate.sh` 不是薄殼，它就是閘門本體**（三軌 pytest + arch_fitness + 十道 lint 硬閘由它產生）。
把它納編的真實 scope 是「把整個 SDD CI gate 移植進 Python」。本 ADR 據此把
「**納編前必須先驗兩側 raw 行數皆 ≤ MAX_LINES**」寫成 Tier-1 的硬前置條件（§3.1）。

### 2.3 `install_git_hooks` / `install-hooks` 四支殼可納編（S8 可行性，我實測）

```
$ python - (T.normalized_content + raw splitlines)
AutoClaude/tools/install_git_hooks.sh:  raw=50 normalized=25 MAX_LINES=100 over=False
AutoClaude/tools/install_git_hooks.ps1: raw=65 normalized=33 MAX_LINES=100 over=False
AISDLC_SDD/scripts/install-hooks.sh:    raw=40 normalized=21 MAX_LINES=100 over=False
AISDLC_SDD/scripts/install-hooks.ps1:   raw=42 normalized=24 MAX_LINES=100 over=False
```

四支 raw 皆 ≤ 100 ⇒ 與 2.2 的 `ci-gate` 相反，這兩對**可以**遷移。
語意上它們早已是「Python 契約（`tools/git_hooks_install_common.py` 四子指令）+ 2 語言 adapter + 4 產品文案殼」，
只是治理類別掛在 `_EXEMPT_PAIRS`（決策豁免）＝**沒有任何機制阻止它們日後長回業務邏輯**。

### 2.4 🔴 `Find-GitBash.ps1` 的 System32 排除在斜線路徑下失效（活缺陷，我雙語言實測）

PowerShell 側（原生 5.1，以檔案載具執行避免 quoting 失真）：

```
$ powershell -NoProfile -ExecutionPolicy Bypass -File <scratchpad>/probe_fgb.ps1
C:\Windows\System32\bash.exe      current_accepts=False  fixed_accepts=False
C:/Windows/System32/bash.exe      current_accepts=True   fixed_accepts=False   ← 現行判定失效
C:/Windows/System32\bash.exe      current_accepts=True   fixed_accepts=False   ← 混合分隔符亦失效
C:\MySystem32Tools\bash.exe       current_accepts=True   fixed_accepts=True    （子字串偽陽性，兩者皆正確放行）
C:\Windows\Sysnative\bash.exe     current_accepts=True   fixed_accepts=True    ← 見 §6 邊界 3
PSVersion=5.1.26100.8875
GetCommand_bash_Source=C:\Program Files\Git\usr\bin\bash.exe
```
（`current` ＝ 現行 `$c -notmatch '\\System32\\'`；`fixed` ＝ 分隔符不敏感形態 `[\\/]System32[\\/]`）

Python 側同五筆（`integration_gate_core._has_system32_segment`，逐段小寫比對）：

```
$ python <scratchpad>/probe_py.py
'C:\\Windows\\System32\\bash.exe' -> has_system32_segment = True
'C:/Windows/System32/bash.exe'    -> has_system32_segment = True     ← 與 PS 側裁決相反
'C:/Windows/System32\\bash.exe'   -> has_system32_segment = True     ← 與 PS 側裁決相反
'C:\\MySystem32Tools\\bash.exe'   -> has_system32_segment = False
'C:\\Windows\\Sysnative\\bash.exe'-> has_system32_segment = False
```

**兩語言在正斜線與混合分隔符兩筆上裁決相反，而 `test_find_git_bash_parity.py` 全綠**——
它從 PS1 regex 抽字面詞與 `bash_probe_spec.SYSTEM32_SEGMENT` 比對相等，兩側字面都是 `system32`、
完全一致；分歧藏在「怎麼比對」而非「比對什麼」。這是本 ADR 的核心診斷（§3.2）。

**可觸達性（誠實劃界）**：我這一次量測時 `Get-Command bash` 解析到 `C:\Program Files\Git\usr\bin\bash.exe`
（Git Bash，非 WSL）⇒ 本機當下**不觸發**。另一鏡在自己的 shell 內量到 `C:\WINDOWS\system32\bash.exe`
並以改 `$env:PATH` 為正斜線形態實測觸發。故本 ADR 的宣稱嚴格限定為：
**判定語意分歧已實測成立；「若 PATH 中存在正斜線寫法的 System32 項且 WSL bash 先被解析到則必觸發」為條件式結論；
真實使用者機器上該前置條件的普遍性未證實。**

### 2.5 🔴 `_normalize` 對帶 BOM 的 `.ps1` 首行註解剝不掉（量尺本身的缺陷，我實測）

```
$ python - (sample tools/*.ps1 + AISDLC_SDD/scripts/ci-gate.ps1)
ps1 sampled: 6 with BOM: 6
normalize utf-8   lines = 14      # tools/integration_gate.ps1
normalize utf-8sig lines = 13
first line utf-8 repr = '\ufeff'
```

`check_wrapper_thinness.py:249` 讀 `encoding="utf-8"`（非 `utf-8-sig`），而本 repo 的 `.ps1`
一律帶 UTF-8 BOM（`root-infra-ci` 第 2 道強制）⇒ BOM 使首行變成 `'\ufeff# …'`，
`line.lstrip().startswith("#")` 判定失敗 ⇒ **每支 `.ps1` 白算一行**，且正規化後首行是純 `\ufeff`。

三個後果，全部載入本 ADR：
1. C 案的 `D = 3526` 用它自己指名的 SSOT 算出 **3543**（兩鏡各自實測，差值恰等於受測 `.ps1` 支數）
   ⇒ 零餘裕棘輪落地當天即紅。**這是 C 案主判準被否決的直接原因。**
2. B 案 Step 3 用 `_PINNED_SHA256`（＝同一份正規化）當「等價性證明」的 oracle，
   而該 oracle 對 EOL／BOM／整行註解／`<#…#>` 說明區塊全盲 ⇒ 它證不到它宣稱的事。
3. 任何未來以 `_normalize` 為量尺的指標，對 `.ps1` 恆偏高 1 行/檔。**修法一行**（改 `utf-8-sig`
   ＋同步重釘 10 支 hash ＋加一支「BOM 不影響正規化」回歸），列 §8 交棒。

### 2.6 兩個「先例」的實測訂正

| 提案宣稱 | 實測 |
|---------|------|
| C 案：「形狀抄 `tools/check_loc_budget.py` 的『只能下調的預算』，本 repo 已有此慣例」 | 根層**沒有**該檔（`wc -l` → `No such file or directory`）；實體在 `AutoClaude/tools/check_loc_budget.py`，形狀是 `cap = baseline × TOTAL_INCREASE_LIMIT(1.20)`（實測 `total=20361 baseline=17032 cap=20438 violations=0`），baseline 可被 `--update` 覆寫 ⇒ **不是棘輪** |
| 本 repo 真正存在的棘輪先例 | `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet`（實查 :1013，以 `git show HEAD:<鎖檔>` 取上一版常數機械比對，docstring 逐字記載「round 2 的『shrink-only』只是檔頭的一句宣稱…SD 實測把上限往上改**不會紅**」）⇒ **R61 若要棘輪，照這支抄，不要照 check_loc_budget** |

### 2.7 A 案 `GFC` 的定義與其宣稱值不一致（我實測）

```
$ ls tools/tests/test_*.py | wc -l        →  53      # GFC as defined
$ ls tools/tests/*.py | wc -l             →  56      # 提案宣稱的「56」是這個集合
$ ls tools/tests/*.py | grep -v '/test_'
tools/tests/_ci_scan_anchors.py
tools/tests/_platform_helpers.py
tools/tests/_ps_engine.py
$ git ls-files 'tools/tests/test_*.py' | wc -l   →  43   # HEAD 追蹤數（工作樹 53 = 43 + 10 支未 commit）
```

差額的三支正是 `_` 前綴的護欄層共用模組，`GFC = len(glob('test_*.py'))` 對它們**結構性全盲**——
而 `_ps_engine.py` 恰是 Architect 唯一認可的四項真收斂之一（R60 本輪新增）。
一個「硬不變量」同時基線錯 3、且對它要擋的行為留了合法逃生門（把新鎖命名成 `_foo.py`）。

### 2.8 `run_tlc.ps1` 在 PS 5.1 拒跑；Java 21 可用（R62 等價證明的前置條件已滿足）

```
$ powershell -NoProfile -ExecutionPolicy Bypass -File tools/fsm_runtime/formal/run_tlc.ps1 -InstallOnly
REAL_RC=2      （訊息：本腳本需 pwsh 7+…替代：bash …run_tlc.sh，或五軌權威路徑 python -m tools.fsm_runtime.tlc_runner）
$ java -version
REAL_RC=0      openjdk version "21.0.10" 2026-01-20
```

意義：`run_tlc` 這一對的收斂，其「Windows 使用者仍有可用路徑」的等價證明**本機取得得到**
（另一鏡已實跑 `python -m tools.fsm_runtime.tlc_runner --module SDD_FSM` 得 rc=0／TLC_DISTINCT=855；
**該次實跑我未複驗**，僅複驗了 Java 存在與 `.ps1` 拒跑）。三案原本都因「取不到 Java」把它標未證實。

---

## 3. 決策

### 3.0 選定：**綜合案**——以 C 的「先量再收斂」為骨架，標的與分類採 A 的 Tier 模型與其三個具體標的，反位移面採 B 的 M2 洞見；**三案各自的旗艦機制全部不採用**

一句話：**本 repo 缺的不是第 N+1 個抽象層，是「未受檢的等價宣稱」從來沒有被量過**；
量了之後才知道大半的雙實作有可驗證的硬理由，而真正該收的是「治理類別掛錯」與「鎖的種類選錯」。

#### 為何骨架取 C

三案唯一的共同實證結論是 §1.3：Architect 的刻度量不到任何一案要做的事，而三者算出的「真正會動的數」
落在同一個集合。C 案最早、最完整地把這件事寫成「先立量尺 + 棘輪，再一對一對搬」，
且它的量測面（既有登記表）不需要任何新概念。骨架採它。

#### 為何不選 A（作為整案）

| A 案元件 | 處置 | 依據 |
|---------|------|------|
| Tier-1/2/3 分類、「不得放進 `autoclaude/core/ports/`」的判斷 | **採用**（§3.1~3.3） | 三鏡皆攻不倒；LOC 餘裕 77 行、`.importlinter` 只管 `autoclaude` 套件、`.sh`/`.ps1` 對 Python 無 import 邊，三項我皆複驗 |
| S3（修 Find-GitBash）+ S4（字面 parity → 行為表 parity） | **採用，S4 換載具** | §2.4 我雙語言實測缺陷成立；載具依 Windows 執行期鏡改 `native_ps51()`／`windows_with_native_ps51()`（PATH 分隔符／反斜線正規化只在原生 5.1 成立，用 `production_engine()` 會 fallback 到 pwsh 而失去鑑別力；先例 `test_nightly_interpreter_determinism.py:205/238`） |
| S8（install hooks 登記遷移） | **採用** | §2.3 四支 raw 行數實測皆 ≤100 |
| S7（ci-gate 登記遷移） | ❌ **已由 repo 現實鏡攻破，我親自複驗證偽，故不採用** | §2.2：交叉鎖強制拖進 281 行的 `.sh`，`MAX_LINES` 判 raw ⇒ 必紅；驗收字串「7 對／14 支」在該步永不可能出現 |
| 主判準 `GFC` | ❌ **已由三鏡一致攻破（定義錯 + 對 `_*.py` 全盲），不採用** | §2.7 |
| S2（`TOTAL_INCREASE_LIMIT=1.20` 的 tools/ LOC 預算） | ⚠️ **方向採用、參數與範圍全部否決**，降為 R61 設計項（§5 Phase 2-E） | 我實測 `tools/**/*.py` = 74 檔／**32,708** 行 ⇒ cap = 39,249 ⇒ **免費餘裕 6,541 行**；對照 §1.1 十分鐘 298 行的成長速率，這道「讓多寫一支鎖有代價」的閘門要好幾輪才第一次咬到人。治理契合鏡另實測 `AutoClaude/tests` = 279 檔／57,351 行同樣零預算 ⇒ 「tools/tests 是唯一沒有 LOC 預算的層」為假 |
| S5／S6（LATEST 解析樣板 10 份 → 1、frozen 正則 5 份 → 1） | **採用方向，排到 Phase 2**（§5 Phase 2-C/2-D） | 三鏡皆複驗重複為真（`grep -rln '"sdd_version.py"' tools/tests/*.py` → 10）；但必須等並行包停工（改 12 支 `tools/tests/*.py`，共用 `__pycache__` 已知互踩三次） |
| S1 的 894 測試數基線 | ❌ 錯值，不採用 | `tools/run_root_unittests.py:48` 實查 `MIN_TESTS = 845`；兩鏡各自實跑 discover 得 **916** 與 **901**（一鏡另遇 rc=1／14 errors，根因是並行包 `archive_defect_log` 缺 `_CELL_SPLIT_RE` 的半套接線）。三個數字互不相同 ⇒ 見 §6 邊界 8 與 §8 交棒 |

#### 為何不選 B

| B 案元件 | 處置 | 依據 |
|---------|------|------|
| M1/M2/M3 量尺批評（「檔數是錯的量尺」、M2＝換地方複雜的偵測器） | **採用**，M2 改寫為 `AC`（§4.2） | 三鏡皆認可；且 M2 定了提出者自己的罪（spec 寫死 `AISDLC_SDD_v0.30` 本身就是一枚 M2 常數） |
| 規則 3（兩平台 smoke 與 pre-push 直跑 pytest 不得被吸收） | **採用並升格為 Tier-4**（§3.4） | 形態論證正確且三鏡一致；靜態渲染能證明「殼長對了」，永遠不能證明「殼跑起來對」 |
| `init_project` 硬理由訂正 | **採用**（§3.3） | 兩鏡各自實測 `git ls-files \| grep -c '^AISDLC_v'` → 0、in-repo 零程式消費者 ⇒ 真正的硬理由是「與上游 repo 分歧 + Copy-on-Evolve 只覆蓋 1/30」，不是「遠端 one-liner 自足性」 |
| `gen_shells.py --check` 取代 `check_wrapper_thinness` | ❌ **已由 repo 現實鏡攻破（dominance 實測 0/1，`gen --check` 是恆真式），故不採用** | 突變＝把迴圈寫進 spec ⇒ 兩邊同時含迴圈 ⇒ 比對恆等、`--check` 全綠；舊鎖 `_FORBIDDEN` 命中 `['foreach (']` 即紅。依 B 案自訂的 rule 2（M/N 須 100%），Step 5 的「−1109 行」歸零 |
| Step 3 的 oracle（`--print-sha256` 對 `_PINNED_SHA256` 全中） | ❌ **已由 Windows 執行期鏡攻破，我獨立複驗成因，故不採用** | §2.5：該 pin 是正規化 hash，對 EOL／BOM／`<#…#>`／文案全盲。Windows 鏡另實測 banner 插入後「pin 仍綠、逐位元不同」⇒ Step 2（逐位元）與 Step 3（pin 對帳）對同一件事給相反答案 |
| 生成物入庫 + banner（Step 7/8 動 `AISDLC_SDD_v0.30/`） | ❌ **已由治理契合鏡攻破，不採用** | banner「勿手改，改 spec 後 `--write`」會被 Copy-on-Evolve 逐版**複製並凍結**，而在凍結版執行 `--write` 正是鐵律禁止的動作 ⇒ 每升一版固化一份「叫人做被禁止的事」的檔案；另 spec 寫死 `AISDLC_SDD_v0.30` 違反 `tools/_script_scan_surface.py:48-51` 與 `sdd_version.py` 明文的「呼叫端不得再自行實作 LATEST 解析」 |
| 「殼形狀可由少量參數推導」這個能力本身 | **保留為 R62+ 候選，但角色改為偵測器不是獨裁者** | 若 renderer 能證明「10 支殼全部位元可由 5 個受鎖參數 + 固定模板推導」，則 `--check` 紅燈的語意是「有人在殼裡放了模板容納不下的形狀」——那是形狀鎖，比位元鎖強。**前提：`MAX_LINES` 與 `_FORBIDDEN` 不得退場**（兩者與「位元相同」正交，生成不覆蓋） |

#### 為何不選 C（作為整案）

| C 案元件 | 處置 | 依據 |
|---------|------|------|
| 「先量再改」框架、`--print-collapse` 逐對報表、形狀 A/B/C 分類、「形狀 C 的 reason 必須非空且含硬理由關鍵詞」斷言 | **採用**（§4.3、§5 Phase 1-C） | 正面命中 Scan-H 判準 #3「不得寫死可由程式現查的數字」 |
| 步驟 1(a)：4 組「異名對等品」由 reason 散文升為字典 + stale 自檢 | **採用**（§5 Phase 1-C） | ΔD=0、風險低、把既有事實資料化 |
| 步驟 2：刪 `run_tlc.ps1` | **採用方向，排 Phase 2**（§5 Phase 2-A） | §2.8 前置條件已滿足；但治理鏡實測 `ONBOARDING.md:383` §9 有一列以「改用 **v0.30 對應檔**」為 29 支凍結版無 BOM 缺口的緩解方案 ⇒ **刪檔會斷那條救生索，且 C1/C2 機械鎖抓不到**（它只驗 DEF-ID 出現在 §9，不驗語意）。故 touch 清單必須含 ONBOARDING.md §9，且該檔正被並行包修改 |
| 主判準 `D`（雙實作邏輯質量）＋ `_DUAL_IMPL_LINE_CEILING = 3526` 零餘裕棘輪 | ❌ **已由兩鏡攻破（D 用它自己的 SSOT 算出 3543），且我獨立複驗成因，故不採用** | §2.5 BOM；另：零餘裕 × 已接 pre-push ⇒ repo 現實鏡實測近 40 個碰到這些腳本的 commit 有 **34 個淨增行**，而「只准往下調」自己封死了唯一出路 |
| 「形狀抄 check_loc_budget 的只能下調預算」 | ❌ 先例不存在，不採用 | §2.6 |
| bug-injection 選 `tools/integration_gate.ps1` 當注入標的 | ❌ 載具選錯 | 該檔本身就在 `_PINNED_SHA256` 十支釘選內 ⇒ 插行會同時打翻 hash，無法歸因是新閘門抓到的。有鑑別力的標的必須落在**未被 hash 釘選**的那 8 對 |

---

### 3.1 Tier-1｜CLI port（bootstrap 之後的 capability）

- **契約**：一支 Python 模組 + argparse 子指令。**契約面是 argv 進、exit code + 結構化 stdout 出，不是 import。**
- **adapter**：每語言一支薄殼，只做 argv 搬運與 rc 原樣傳遞。
- **活體先例（照抄，不另創風格）**：`tools/git_hooks_install_common.py`（4 子指令：`assert-not-linked-worktree`／
  `get-hooks-dir`／`assert-hooks-present`／`check-installed`）＋ `tools/lib/git_hooks_install_common.sh`／
  `GitHooksInstallCommon.ps1` 兩個 adapter ＋ 4 個產品文案殼。
- **強制機制**：`check_wrapper_thinness._PINNED_SHA256` 正規化 hash 釘選（第一訊號）＋ `MAX_LINES=100`
  （第二訊號）＋ `_FORBIDDEN` 關鍵字並聯（第三訊號，R60 起刻意不縮排進 hash 的 `if` 內）
  ＋ `check_script_parity._THINNESS_ENROLLED` 鍵集合交叉鎖。
- 🔴 **納編硬前置條件（本 ADR 由 §2.2 實測新增）**：`_THINNESS_ENROLLED` 的鍵是 **stem**，交叉鎖會把
  同名 `.sh` 與 `.ps1` **兩側**一併要求進 `_PINNED_SHA256`，而 `MAX_LINES` 判 **raw** 行數。
  ⇒ **納編前必須先跑 `wc -l` 確認兩側 raw 皆 ≤ 100**。這條就是 S7 死在哪裡，寫下來避免下一輪重犯。
- 現況成員：5 對（`dev_start`／`bootstrap`／`integration_gate`／`local_ci_gate`／`run_act`），10 支殼全數釘選。

### 3.2 Tier-2｜spec port（bootstrap 之前的 capability，**實作數不可減**）

- **契約**：一份 Python 規格模組，**必須同時收「資料」與「判定規則」**——現況只收資料，這就是缺口（§2.4）。
- **adapter**：每語言恰一份實作，各自讀同一份規格。
- **先例**：`tools/lib/bash_probe_spec.py`（該檔 docstring 自述執行邏輯刻意保三份，
  「以維持三份回歸鎖彼此獨立的鑑別力」）。
- **成員（第三份由治理鏡指出、我獨立複驗：`grep -n '_has_system32_segment' AISDLC_SDD/scripts/bash_probe.py` → `:41 def _has_system32_segment`，且該檔 `:38` 已 `import bash_probe_spec as _spec`；A 案原只算 2 份）**：
  - `real_python_candidate`（WindowsApps 空殼判定）— **4 份**：`tools/lib/windowsapps_guard.sh`、
    `tools/lib/WindowsAppsGuard.ps1`、`tools/bootstrap_core.py`、
    `AutoClaude/autoclaude/execution/pre_run_validator.py`。bootstrap 悖論已由
    `CrossPlatform_Scan_Dimensions.md` §「WindowsApps guard 三語言等價實作為何不可收斂」定案，
    **不得重辯**；第 4 份的成因是 `autoclaude` 可獨立 pip 安裝、不得依賴 monorepo 根層 `tools/*.py`。
  - `git_bash_locator` — **3 份**：`tools/lib/Find-GitBash.ps1`、`tools/integration_gate_core.py::find_git_bash`、
    `AISDLC_SDD/scripts/bash_probe.py`（含 `_has_system32_segment`，且已有自己的偽陽性測試）。
- 🔴 **強制機制改為行為表 parity（餵同一組輸入給各語言實作、比對裁決），取代現行的字面 parity。**
  理由是 §2.4 實測：字面完全一致、鎖全綠，而底下藏著兩語言裁決相反的活缺陷。
  **字面比對型 parity 鎖自本 ADR 起不計為機械釘選。**
- 這條同時是對 `CrossPlatform_Scan_Dimensions.md` §93 那節定案折衷（「資料抽 SSOT + 機械 parity 鎖」）的
  **補訂**：它只收斂了資料，沒收斂**判定語意**；而同一盲區在兩個獨立 capability 上同時出現
  （`-notmatch '\\System32\\'`、`-notlike '*\WindowsApps\*'`，bash 側兩者皆有 `tr` 正規化、PowerShell 側皆無）
  ——不是巧合，是缺契約的系統性後果。

### 3.3 Tier-3｜OS 原語（不可收斂，**明文封頂，禁止未來輪重辯**）

比照 `CrossPlatform_Scan_Dimensions.md` 對 WindowsApps guard 的做法（該節開頭逐字寫「每一輪的
Architect 都會把它重新列為候選發現、再逐一論證掉」），本節把下列六類**一次性封頂**：

| # | 原語 | 為何不可收斂 |
|---|------|-------------|
| 1 | launchd plist／`plutil -lint`／`launchctl` ↔ `New-ScheduledTaskSettingsSet`／`Register-ScheduledTask` | 無共同 API；且 cmdlet 參數名與物件屬性名極性相反（`-AllowStartIfOnBatteries` ↔ `DisallowStartIfOnBatteries=False`，DEF-101-249 真機才炸出來） |
| 2 | 在**呼叫端 shell 內**啟用 venv | 子行程改不了父 shell 環境（盤點者實測 `export DEMO_VAR=parent` → python 內改 → 退出後父 shell 不變） |
| 3 | Python 接手前的輸出改道（`exec > >(tee -a …)`） | 必須在 Python 起來之前完成 |
| 4 | PowerShell 原生 `-WhatIf`（`SupportsShouldProcess`） | Python 契約只能決定「要不要真的執行」，給不出 PowerShell 的 `-WhatIf` 語意 |
| 5 | container 內執行（`AutoClaude/tools/run_mutmut_in_docker.sh`） | 由 `docker run python:3.11-slim bash …` 送進 Linux container；container 內不會有 PowerShell |
| 6 | 遠端 one-liner 自足性（`init_project`） | ⚠️ **理由訂正**：兩鏡實查 `git ls-files \| grep -c '^AISDLC_v'` → **0**、in-repo 零程式消費者、廣告網址指向另一個 GitHub repo ⇒ **真正的硬理由是「與上游分歧 + Copy-on-Evolve 只覆蓋 1/30」，不是自足性**。處置不變（不收斂），但**下一輪若要重審，第一件事是驗那個遠端入口是否還活著，別再引用錯理由** |

契約只能覆蓋它們的**周邊**（路徑解析、四能力表、exit code 語意、文案）；OS 呼叫序列原樣留在殼裡。

### 3.4 Tier-4｜**明文禁止收斂**（B 案 rule 3 升格；本 ADR 新增類別）

| 成員 | 為何禁止 |
|------|---------|
| `tools/macos_smoke_local.sh`／`tools/windows_smoke_local.ps1` | 它們**就是**驗證載具。判定合流到單一 Python 核心 ⇒ 核心壞掉時兩平台同時假綠，與 R12 QA-2「兩訊號合流即單點化」直接衝突。另 `windows_smoke_local.ps1` 自 DEF-101-511 起偵測 `$env:MSYSTEM` 即拒跑（經 Git Bash 呼叫會在非 ASCII 路徑產生假紅：實測 PASS=11 FAIL=2 vs 原生 PASS=12 FAIL=0）⇒ 連「由 Python 統一啟動」都不行 |
| dispatcher pre-push AutoClaude leg 直跑 pytest | `ONBOARDING.md:150` 逐字「刻意不經 local_ci_gate，勿改為經其呼叫——兩訊號合流即單點化，R12 QA-2 紀律」 |
| `AutoClaude/tools/run_local_nightly.{sh,ps1}` 的心跳檔前 2 行 | `run_local_nightly.sh:187-190` 逐字「🔴 前 2 行格式為三站點契約（`dev_start.py` mtime 讀取／`install_mac_nightly.sh --status`／本函式寫入），絕不可變」 |

**上限只能是**「共用清單與掃描面、各自保留獨立執行與判定」。

### 3.5 誰依賴誰 / SSOT 是誰

```
tools/lib/*（無相依，只靠 stdlib）
  ← 根層 tools/*_core.py、AutoClaude/tools/*、AISDLC_SDD/scripts/*
    ← 各語言薄殼（.sh / .ps1）
```
單向，零反向依賴。`autoclaude/` 套件**不**依賴 `tools/lib/`（維持 pip 邊界），其重複實作
（`pre_run_validator._is_windows_apps_alias_stub`）以 Tier-2 行為 parity 鎖納管，**不做 import 收斂**。

| 層 | SSOT |
|----|------|
| Tier-1 業務邏輯 | 各 `*_core.py`／`*_common.py`（5 支 + `git_hooks_install_common.py`） |
| Tier-2 資料＋判定規則 | `tools/lib/bash_probe_spec.py`（**須擴充為含判定規則**） |
| 掃描面 | `tools/_script_scan_surface.py`（LATEST 路徑刻意不列常數，動態解析） |
| LATEST 版本解析 | `AISDLC_SDD/scripts/sdd_version.py`（明文「呼叫端不得再自行實作」；現有 10 份 `tools/tests` 樣板違反此條，Phase 2-C） |
| PowerShell 引擎挑選 | `tools/tests/_ps_engine.py`（5 種語意各一支具名述詞） |
| 登記表 | `tools/check_script_parity.py` 四張表 + `tools/check_wrapper_thinness.py::_PINNED_SHA256` |

---

## 4. 可機械追蹤的下降判準（本 ADR 的核心）

### 4.1 主判準 UEP（未受檢等價平面）—— 閘門可跑

```bash
python - <<'PY'
import sys; sys.path.insert(0, "tools")
import check_script_parity as P
print("UEP =", len(P._EXEMPT_PAIRS) + len(P._TLC_TRACK_ENROLLED))
PY
```

**語意**：有成對檔（或已知有第二實作）、但**沒有任何機械守門阻止它長回／漂移**的語意項目數。
`_EXEMPT_PAIRS` 是「決策豁免」＝零守門；`_TLC_TRACK_ENROLLED` 是「已知曾漂移，靠客製鎖看著」。

| | 值 | 取得 |
|---|---|---|
| **當前基線** | **8**（`_EXEMPT_PAIRS`=7 + `_TLC_TRACK_ENROLLED`=1） | 上列指令，2026-07-29T00:55:08Z，HEAD `e3a5c53` |
| **R61 目標** | **≤ 6** | Phase 1-B（S8 兩對移出）|
| **R62+ 目標** | **≤ 4** | Phase 2-A（run_tlc）＋ Phase 2-B（ci-gate，需 signoff） |
| **地板（可辯護殘留）** | **4** | `run_local_nightly`（R11 D1 拍板兩側語意刻意不同）／`init_project`（§3.3 #6）／`install_post_commit`／`run_self_evolution` |

**對偶判準（必須同時上升，否則 UEP 下降只是把列刪掉）**：

| 指標 | 基線（實測） | R61 目標 |
|------|------------|---------|
| `len(_THINNESS_ENROLLED)` | 5 | ≥ 7 |
| `len(_PINNED_SHA256)` | 10 | ≥ 14 |

兩者今天就在 `check_script_parity` 的「thinness 交叉鎖」那一行同時 print（實測逐字
「✅ thinness 交叉鎖：5 對薄殼登記與 10 支 hash 釘選鍵集合一致」），零新增度量檔即可逐輪追蹤。

🔴 **為什麼不用 Architect 原本指定的「13 對 + 18 支單邊」**：§1.3——那個數數的是檔案成對存在，
本 ADR 全部十餘個標的做完之後它仍是 `13 + 18`（唯一能減的 `run_tlc` 因文件追溯鏈選擇薄殼化不刪檔；
`verify_traceability.sh` 經兩鏡實查有使用者面 SOP 指令 `bash …/verify_traceability.sh docs` 與四處
README 列名，**不是死碼、不可歸檔**）。UEP 是同一件事的可觀測投影。

### 4.2 反位移判準 AC（描述性常數登記筆數）—— 擋「換個地方複雜」

```
AC = |_PINNED_SHA256| + |_THINNESS_ENROLLED| + |_EXEMPT_PAIRS|
   + |_SINGLE_SIDED_EXEMPT| + |_TLC_TRACK_ENROLLED| + |_MIN_EXTRACT_COUNTS|
```

**基線＝42**（10 + 5 + 7 + 18 + 1 + 1，實測，同一支指令印出）。

「描述性常數」＝存在的唯一目的是「描述另一個檔案現在長什麼樣」的登記項。
B 案的 M2 只挑了會歸零的子集（11）；本 ADR 用**誠實的全集**。

**判定規則（三條，缺一即駁回該步）**：
1. **ΔUEP < 0**。新增一支 `tools/tests/*.py` 不會讓任何 `.sh`/`.ps1` 少一份未受檢宣稱 ⇒ ΔUEP ≡ 0
   ⇒ 「一個 finding → 一支鎖」在這把尺上**得分恆為 0**。這就是把 Architect 的評語變成算式。
2. **AC 允許因「零守門 → hash 釘選」的類別升級而上升**（S8 預期 42 → 46：`_EXEMPT_PAIRS` −2、
   `_THINNESS_ENROLLED` +2、`_PINNED_SHA256` +4），但**每一筆上升必須在同一 commit 內具名對應一筆
   UEP 下降**。UEP 不降而 AC 上升 ⇒ 判定「換個地方複雜」，該步作廢、不計為收斂成果。
3. **鎖的退場必須過注入矩陣（dominance test）**：要刪的每一支既有鎖的每一條斷言，逐一構造它原本
   能抓到的突變，證明新機制在**同一個突變**上也紅。M/N < 100% 者，那 N−M 條斷言保留，
   **不准以「新機制更根本」為由籠統刪掉**。
   ⚠️ 並補一條**反向** dominance（Windows 執行期鏡的貢獻）：**舊鎖刻意綠 → 新機制不得紅**。
   否則像 `test_comment_only_change_does_not_trip_hash` 這種**設計上的自由度**
   （該檔 docstring 逐字承諾「註解／說明文字調整不觸發（正規化吸收）」）會被靜默沒收而量尺全看不到。

### 4.3 GLC（護欄層行數）—— **報表，不設上限**

```bash
ls tools/tests/*.py | wc -l                                    # 檔數（含 _ 前綴共用模組）
python -c "import pathlib;t=list(pathlib.Path('tools/tests').glob('*.py'));print(sum(len(p.read_text(encoding='utf-8',errors='replace').splitlines()) for p in t))"
```

基線：**56 支／25,092 行**（2026-07-29T00:55:37Z）。

**本 ADR 刻意不對 GLC 設任何上限**，並明文否決兩種上限：
- A 案的 `TOTAL_INCREASE_LIMIT=1.20` ⇒ §2.6/§3.0 實測 6,541 行免費額度＝好幾輪內收不到代價；
- C 案的零餘裕棘輪 ⇒ repo 現實鏡實測 34/40 個相關 commit 淨增行，會優先咬住它宣稱要保護的
  那類跨平台加固，而「只准往下調」封死了唯一出路。

**唯一規則**：GLC 必須在**同一個 commit** 上前後各量一次，跨時點／跨並行包比較無效（§1.1 實測依據）。
真正的預算設計列 Phase 2-E，並在該處寫明具名要求（含 `AutoClaude/tests` 57,351 行為何不納管的劃界）。

### 4.4 若要把 UEP 閘門化：照哪一支抄

R61 Phase 1-C 若要把 UEP 釘成上限，**必須照 `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet`
的形狀**（`git show HEAD:<鎖檔>` 取上一版常數機械比對，調升即紅），**不要照 `check_loc_budget.py`**（§2.6：那不是棘輪）。
且該棘輪自己已記載一個既知空轉窗口（鎖檔首個 commit 上 HEAD 還沒有它可比 ⇒ `skipTest` 並印理由），照抄時一併照抄。

---

## 5. 分階段遷移計畫

### Phase 0 —— R60（本輪）：**只交付本 ADR，零程式碼變更**

等價性證明：`git status --porcelain` 中本輪新增的唯一檔案是本 ADR（`docs/04_planning/ADR/`）；
不觸及任何 `.sh`／`.ps1`／`tools/*.py`／登記表 ⇒ §1.2 的六個基線值結構上不可能變。
落地後實跑 `python tools/check_ntfs_paths.py`（rc 見 §9）。

### Phase 1 —— R61（**三步必須在同一輪落地；前置＝兩包並行修復全部 commit、工作樹乾淨、基線重取**）

| 步 | 動作 | 本輪可安全執行 | 等價性證明（跑哪個閘門、看什麼數字） |
|---|------|--------------|--------------------------------|
| **1-A** | 修 `tools/lib/Find-GitBash.ps1`：`-notmatch '\\System32\\'` → 分隔符不敏感形態（如 `'[\\/]System32[\\/]'`）；`tools/lib/bash_probe_spec.py` 增列判定規則常數（分隔符集合 `('\\','/')` ＋「完整路徑段、不分大小寫、分隔符不敏感」的規範敘述）；同步檢視 `WindowsAppsGuard.ps1` 的 `-notlike '*\WindowsApps\*'` | **需 R61** | ① §2.4 的五筆路徑表，修前／修後兩次逐字輸出（修前 `C:/Windows/System32/bash.exe` accepts=True、修後 False，`MySystem32Tools` 兩次皆 True 不誤殺）；② 同五筆餵 Python 側，兩側裁決逐筆相同；③ 回歸：`powershell -ExecutionPolicy Bypass -File AISDLC_SDD/scripts/ci-gate.ps1` 須仍走**完整委派**路徑（印「偵測到 Git Bash」）而非 fallback，rc 與 `bash AISDLC_SDD/scripts/ci-gate.sh` 一致；④ UEP／AC 不變（這是修缺陷，不是收斂——**不得計入收斂成果**） |
| **1-B** | `AutoClaude/tools/install_git_hooks` 與 `AISDLC_SDD/scripts/install-hooks` 由 `_EXEMPT_PAIRS` 移入 `_THINNESS_ENROLLED` ＋ `_PINNED_SHA256` 補 4 支 hash。**零程式邏輯變更** | **需 R61** | ① 納編前先跑 `wc -l` 四支確認 raw ≤ 100（§2.3 已實測 50/65/40/42，仍須在乾淨樹重量）；② `python tools/check_wrapper_thinness.py` rc=0；③ `python tools/check_script_parity.py` 的交叉鎖行由「5 對／10 支」變「**7 對／14 支**」；④ **UEP 8 → 6**；⑤ bug-injection：在 `install-hooks.ps1` 加一行實質判定邏輯，thinness hash 須紅（證明遷移後真的有守門，不是換個字典）；⑥ 兩平台 smoke 的 install/uninstall 往返 + linked-worktree 拒絕三情境須全綠（Windows 側須以**原生 PowerShell** 啟動，DEF-101-511） |
| **1-C** | `tools/check_script_parity.py` 內（a）4 組「異名對等品」由 reason 散文升為 4 筆字典 + stale 自檢；（b）`_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的值由純理由字串升為 `(tier, reason)`，`tier ∈ {tier1_contract, tier1_adapter, tier2_spec, tier3_os_primitive, tier4_forbidden, unpinned}`；（c）新增 `--print-collapse` 印 UEP／AC／各對 tier 與 reason；（d）斷言「tier3/tier4 的 reason 必須非空且含硬理由關鍵詞」。**擴充既有檔、零新檔**；測試加進**既有的** `tools/tests/test_check_script_parity.py` | **需 R61**，且 🔴 **必須與 1-B 同一 commit** | ① `python tools/check_script_parity.py` rc=0 且新增行印出 `UEP=6 / AC=46`；② `python tools/run_root_unittests.py` 發現數 = 乾淨樹重取的基線 + 新增斷言數（**逐筆列名，不得只報總數**）；③ GLC 檔數不變（零新檔）；④ 🔴 **1-C 不得單獨落地**——沒有 1-B 的話它就是孤兒儀表，正是 Architect 批評的那個病 |

### Phase 2 —— R62+（每項各自獨立，順序可調）

| 代號 | 動作 | 前置／signoff | 等價性證明 |
|-----|------|-------------|-----------|
| **2-A** | `run_tlc.{sh,ps1}` 降為委派 `python -m tools.fsm_runtime.tlc_runner` 的薄殼（**刻意不刪檔**：`AISDLC_SDD_INIT.md:899` ACT-042 追溯列、`cicd/SDD_CICD_BASE_LAYER.md` 多處引用），`_TLC_TRACK_ENROLLED` + `_check_run_tlc_tracks` + `_TLC_TRACK_RE` + `_MIN_EXTRACT_COUNTS['run_tlc_tracks']` 整套客製鎖退場。**若改為刪 `.ps1`**：另需同步 `windows_smoke_local.ps1` 的 `Floor=4` 與 `test_ps51_compat.py` 的 `_TREE_FLOORS[LATEST]` 兩處下限、`formal/README.md`／`SDD_CICD_BASE_LAYER.md`／`AISDLC_SDD_INIT.md` 共 7 處引用，**以及 `ONBOARDING.md:383` §9 那列「改用 v0.30 對應檔」的緩解方案**（C1/C2 機械鎖抓不到，見 §6 邊界 5） | Java 21 已實測可用（§2.8） | ① `python tools/check_script_parity.py` rc=0 且「run_tlc_tracks…6 個 step 標籤一致」那行**消失**，其餘各行逐字不變；② `python -m tools.fsm_runtime.tlc_runner --module SDD_FSM` 修前／修後 rc 與摘要行相同；③ `bash AISDLC_SDD/scripts/ci-gate.sh` 三軌計數逐字不變（它走 `tlc_runner`，`grep -n 'tlc_runner' …ci-gate.sh` → :171）；④ UEP −1；⑤ 依 §4.2 rule 3 逐條證明退場的客製鎖斷言在新形態下有接手者，**沒有接手者的斷言保留** |
| **2-B** | 刪 `AISDLC_SDD/scripts/ci-gate.ps1` 的 fallback 3-stage，改「找不到 Git Bash → fail-loud exit 1 並指路安裝 Git for Windows」。**該對留在 `_EXEMPT_PAIRS`，reason 由「決策豁免」升為「單側實作 + 另側 fail-loud 委派」**（❌ 不得移入 `_THINNESS_ENROLLED`，§2.2） | 🔴 **使用者／PM signoff**（政策：Windows 無 Git Bash 即拒跑） | 低風險依據（實測）：`tools/git-hooks/` 三支 hook 共 531 行純 bash、零 `.ps1` 對等 ⇒ 「Windows 沒有 Git Bash」時本 repo 早已無法 commit/push，fallback 保護的是一個不存在的可用狀態。⚠️ **但「刪它低風險」目前仍是讀碼推論**——需一台無 Git Bash 的乾淨 Windows 機器證明「那台機器連 commit 都已失敗」，本機有 Git Bash（實測 `Get-Command bash` → `C:\Program Files\Git\usr\bin\bash.exe`）無法製造鑑別力。連帶退場 DEF-101-512 那條「防 fallback 收尾字串冒充完整閘門」的補丁，且 `ONBOARDING.md` §6 那格「無 Git Bash 才退回 3-stage fallback」的散文必須同步刪除（否則變 Scan-H 型 stale 散文） |
| **2-C** | LATEST 解析 subprocess 樣板 10 份 → 1（新增 `tools/lib/sdd_latest.py`，內部仍以 subprocess 呼叫 `sdd_version.py --sdd-root`，維持不跨子專案 import）；10 個消費者各改一行 import；**呼叫端鎖擴充既有的 `tools/tests/test_platform_utils_dedup.py`**（已內建 `_scan_repo_py_for(pattern)` 與 repo-wide「共用 helper 不得有第二份定義」機制，加模式即可）⇒ **鎖的數量從 O(helper 數) 變 O(1)** | 並行包全部停工 | ① 基線 `grep -rln '"sdd_version.py"' tools/tests/*.py \| wc -l` → 10（實測），收斂後同指令 → 0；② `python tools/run_root_unittests.py` 發現數不變（純 helper 抽取；若變動即為非等價，須逐筆解釋）；③ bug-injection：任一消費者改回自帶 `_latest_root` ⇒ dedup 鎖須紅；④ GLC 檔數 +0（新檔落在 `tools/lib/`）；⑤ ΔUEP = 0 ⇒ **依 §4.2 rule 1 本步不計入收斂成果，只計入護欄縮減** |
| **2-D** | 5 份 `_FROZEN_SDD_VERSION_RE`／`_FROZEN_VERSION_DIR_RE` + 2 份 `_exclude_frozen_sdd_versions()` 併入 `tools/lib/sdd_latest.py`（只持一份目錄名 pattern，路徑投影機械推導）；7 個呼叫端的 `.match()` 對齊權威源的 `.fullmatch()` | 同 2-C | ① `git grep -n 'AISDLC_SDD_v.d'` 由 5 處生產字面值 → 1 處；② `.match`→`.fullmatch` 須以具鑑別力載具證明**這是修正不是等價**（`re.match(r'^AISDLC_SDD_v\d+\.\d+$', 'AISDLC_SDD_v0.30\n')` 命中 vs `fullmatch` 不命中，兩鏡皆已實測，R62 須自行重跑）；③ 起點可取 `git show 9593d55:tools/tests/_sdd_versions.py`（97 行，該 stash 存在但**從未在當前工作樹執行過**，其 docstring 的實測宣稱一律當「該檔作者的宣稱」處理） |
| **2-E** | 修 §2.5 的 `_normalize` BOM 缺陷：`encoding="utf-8"` → `utf-8-sig`（對齊同檔 `_extract_tlc_tracks` 既有慣例）＋同步重釘 10 支 hash ＋加一支「BOM 不影響正規化」回歸 | 無 | ① 修前 `tools/integration_gate.ps1` 正規化 14 行、修後 13 行（§2.5 實測）；② `python tools/check_wrapper_thinness.py --print-hash` 取新值釘選後 rc=0；③ 這一步必須**單獨一個 commit**，因為它會讓全部 10 支 hash 改變，混在其他改動裡就無法歸因 |
| **2-F** | 護欄層 LOC 預算設計（A 案 S2 的正確版本）。**具名要求**：(i) baseline 由程式當場量測寫入、不手抄常數（我實測 32,708 而非 A 案寫的 31,133）；(ii) 量測面用 `tools/tests/*.py` 全集含 `_` 前綴（否則 `_ps_engine.py` 這類永遠免費）；(iii) 明文劃界 `AutoClaude/tests` 57,351 行為何不納管；(iv) 寫檔一律 `newline=""`（`.gitattributes` `* text=auto eol=lf`，ADR-XPLAT-001 §4.2 已記載同型教訓）；(v) 補「未知旗標仍執行檢查」相容性斷言（`check_loc_budget.py` 現為手搓 `sys.argv`，實測 `--help` 被靜默忽略仍照跑；加 argparse 會改掉這個隱性契約）；(vi) 同步 `tools/sync_onboarding_baselines.py::_SPECS` 與 `tools/tests/test_doc_loc_baseline_freshness_r60.py` 兩支消費者 | 🔴 **PM signoff**（成長係數與 WARN 帶是政策判斷） | 落地當下必為 PASS（`total == baseline`）；AutoClaude 側原有無參數呼叫行為逐字不變（仍印 `total=20361 cap=20438`、rc=0） |

### Phase 3 —— **不排期（需 macOS 真機，本機零覆蓋）**

| 動作 | 為何不排期 |
|------|-----------|
| `install_mac_nightly.sh:57` 的 `HEARTBEAT_MAX_AGE_DAYS=8` ＋ `report_heartbeat()`（含 BSD `stat -f %m` 與 SD-R13-1 的「以秒比較避免整數除法截斷」修復）收斂為 `python tools/dev_start.py --heartbeat-only`，連帶刪 `test_dev_start.py` 內 3 處跨檔字面鎖。這是全盤點**唯一「收斂後護欄行數會下降」**的標的 | `install_mac_nightly.sh:37-40` 對非 Darwin fail-loud（`if [ "$(uname)" != "Darwin" ]`），本機沒有 macOS，連 `--status` 都跑不起來——而要收斂的正是 `--status` 這條路。前置＝真 macOS 機器上先取得修前／修後 `--status` 逐字輸出對照（含 (8,9) 天窗口的邊界案例） |
| 兩支 nightly 排程安裝器的周邊契約（exit code 語意、四能力表、路徑解析、文案）收斂 | 同上；且 Windows 側 install/uninstall 需 elevation，一般 session 內只能跑 `-Status`／`-WhatIf`，鑑別力弱於真安裝 |

---

## 6. § 判準邊界（❌ 抓不到）

沿用 `ADR-XPLAT-001` 的體例：明文列出本 ADR 的判準**抓不到**什麼，避免「鎖是綠的就以為被保證了」。

1. ❌ **macOS 零真機。** 本機是 Windows 11 / PowerShell 5.1（無 pwsh 7）/ Git Bash。凡涉及
   launchd／`plutil`／`launchctl`／BSD `stat -f`／bash 3.2／zsh／`macos_smoke_local.sh` 與
   `run_local_nightly.sh` 的**實際執行行為**，本 ADR 一律未實測，全部標為**推論**。
   Phase 3 因此明確標「不排期」而非「低優先」。
2. ❌ **UEP 只數登記筆數，不看實作行數。** 一對可以「留在 `_EXEMPT_PAIRS` 且悄悄長 500 行」而 UEP 完全不動
   （`run_local_nightly` 792 邏輯行、`init_project` 672 行就在裡面）。UEP 量的是「有幾份未受檢的等價宣稱」，
   **不是**「重複了幾行」。若要量行數，須先修 §2.5 的 BOM 缺陷（Phase 2-E），否則量尺對 `.ps1` 恆偏高。
3. ❌ **行為表 parity 只鎖「兩側一致」，不鎖「兩側對」。** §2.4 實測：`C:\Windows\Sysnative\bash.exe`
   兩側裁決一致（皆不排除）⇒ 行為表全綠 ⇒ WSL bash 照樣可能被交出去。
   Windows 執行期鏡另實測本機 64-bit PS 下 `Test-Path C:\Windows\Sysnative\bash.exe` = False
   （Sysnative 只對 32-bit 行程可見）⇒ **可觸達性未證實**，但「parity 鎖住的是 agreement 不是 correctness」
   這個結構點與可觸達性無關。Phase 1-A 必須把 Sysnative 明文記入「已實測不涵蓋」常駐表
   （照 `CrossPlatform_Scan_Dimensions.md` §143 的三段式：已實測涵蓋／已實測不涵蓋／明文不窮舉）。
4. ❌ **AC 只數登記筆數，不判斷理由寫得好不好。** 「形狀 C 的 reason 須含硬理由關鍵詞」是關鍵字比對，
   分不出「真硬理由」與「抄一句硬理由關鍵詞」。同 `ADR-XPLAT-001` §4.3.4 對 C1／C2 已劃的同型邊界。
5. ❌ **文件端的語意對應是人審責任。** `ONBOARDING.md:383` §9 有一列以「改用 **v0.30 對應檔**（已補 BOM）」為
   47 支凍結版無 BOM 缺口（`v0.01~v0.29` 的 `run_tlc.ps1` 29 支 + `v0.12~v0.29` 的 `install_post_commit.ps1` 18 支）
   的緩解方案（**我實查該列逐字如此**）；Phase 2-A 若刪 `run_tlc.ps1` 會斷那條救生索，而
   `tools/tests/test_adr_xplat001_c1c2_lock.py` **不會紅**（它只保證 DEF-ID 出現在 §9 區段內，
   不保證那一列描述的是同一個缺口）。這是零機械訊號的靜默治理漂移面。
6. ❌ **`.github/workflows/` 完全在射程外。** `check_script_parity` 只遞迴掃三棵 SSOT 樹 + LATEST tools
   （輸出逐字如此）。兩支 compat-ci（另一盤點者實測合計 1,974 行、canonicalize 後 27.6% 重複、
   alert job **100% 重複**、4 份 paths block 共 400 行、其中 48 個 entry 共用、有效觸發集合只差 1 支檔）
   收斂了 UEP 與 AC 也**不會動一個數字**。若要納管需新機制（pyyaml 讀 workflow、per-job step 對稱斷言、
   paths glob 正規化），本 ADR 明文不納入。
7. ❌ **`AutoClaude/tests` 57,351 行（治理鏡實測 279 檔）不受任何 LOC 預算，本 ADR 亦未納管。**
   因此「多寫一支鎖有代價」這件事，就算 Phase 2-F 落地也只涵蓋根層 `tools/`；
   把新鎖寫進 `AutoClaude/tests/` 仍然完全免費。這是**已知的、刻意留下的**缺口。
8. ❌ **GLC 在並行寫入下無法跨時點比較**（§1.1 三個時點實測）。同理，`tools/run_root_unittests.py`
   的測試數基線目前有 **三個互不相同的值**：源碼常數 `MIN_TESTS = 845`（我實查 :48）、
   一鏡實跑 discover **916**、另一鏡實跑 **901**（且該鏡遇 rc=1／2 failures / 31 errors，
   根因是並行包 `archive_defect_log` 缺 `_CELL_SPLIT_RE` 的半套接線）。
   **我刻意未重跑全套**（與並行包共用 `tools/tests/` 與 `__pycache__`，已重演三次互踩假紅）。
   ⇒ 任何以測試數為「等價證明」的 gate_proof，**必須在並行包停工後於乾淨樹重取基線**
   （`run_root_unittests.py:48` 的註解本身就明文規定了這個取值程序）。
9. ❌ **Copy-on-Evolve 1/30。** `run_tlc`／`init_project`／`run_self_evolution`／`install_post_commit`
   都在版本目錄下，收斂只覆蓋 LATEST；v0.01~v0.29 各留一份不回改（除非走 `ADR-XPLAT-001` §4 的破例流程）。
   R45 的 `component_sanitizer.py` 手法只適用**同語言同 runtime**，對跨語言的 `.sh`/`.ps1` 對子不適用。
10. ❌ **缺陷帳本容量。** 帳本硬閘 `_LEDGER_FAIL_BYTES = 256 * 1024`（我實查 `tools/check_defect_log_crossref.py:403`，
    未開啟帳本本體）；治理鏡實測主檔 248,251 bytes
    ⇒ 餘裕約 13.9KB、DEF 列平均約 1.9KB ⇒ 約 8 列空間，且該檔正被並行包寫入（實測兩次量測值不同）。
    本 ADR 本身**不新增任何帳本列**（禁區三檔全程未碰）；Phase 1/2 各步若逐項登記 DEF 會重新逼近，
    須先歸檔。
11. ❌ **「語言數不會少」。** 收斂後 bash／PowerShell／Python 三側各自仍有實作；
    `real_python_candidate` 仍是 4 份、`git_bash_locator` 仍是 3 份。本 ADR 主張的是
    「**需要人工維護的等價宣稱平面**下降」，不是「實作數下降」。若有人以「實作數／檔案數變少了嗎」
    評分，本 ADR 得零分——而我認為交不出那個數字是對的（bootstrap 悖論已定案，§3.2）。

---

## 7. 本輪（R60）立即可執行的子集

### 🔴 **空集合。本 ADR 為設計交付，R60 不執行任何遷移。**

這不是保守，是四條**實測**出來的阻礙，逐條有取證：

1. **工作樹是移動靶。** `git status --porcelain | wc -l` = **81**（HEAD `e3a5c53`），
   且護欄層在我量測的 10 分鐘內成長 298 行（§1.1）。三案共 25 個步驟裡，
   凡宣稱「零位元變動故基線不變」者，其驗證程序（例如「`git status --porcelain` 只出現 1 個 `??` 新檔」）
   在本輪**字面上不可能綠**。
2. **閘門底座狀態不明且很可能是紅的。** §6 邊界 8：一鏡實跑 `run_root_unittests.py` 得
   rc=1／2 failures / 31 errors，根因在並行包未提交的半套接線。在這個狀態下沒有任何一步交得出
   「等價」證明——**而「等價證明」正是每一步的驗收條件本身**。
3. **唯一「當場可修的真缺陷」（§2.4 Find-GitBash）在本輪落地會撞治理互鎖。**
   照 repo 慣例修復要在註解標 `DEF-101-NNN`，而 `tools/tests/test_defect_id_reference_integrity.py`
   要求該號必須在帳本家族某列第一欄存在——而帳本（`docs/06_quality/AutoSDD_Defect_Log.md`）
   是本輪硬規則明訂的**禁碰檔**。不標號則缺陷與修復在兩個權威站點都無紀錄，違反取證慣例。
   ⇒ 這一步的正確落點是 R61，不是「趕在收輪前塞進去」。
4. **本輪三案的安全子集，逐案檢查後都不成立**：A 案的 S1/S2 依賴錯的基線（894）與被攻破的判準（GFC）；
   B 案的 Step 1~3 交出的成果是「一份對重點盲目的收據」（§2.5）；C 案的步驟 0 若不與步驟 1/2 同輪
   落地就是孤兒儀表（該案自己也這麼寫）。

**本輪唯一產出＝本 ADR。** 它的價值不是任何數字下降，而是：
把「什麼算收斂、怎麼證明、哪些明文不准收斂、哪些判準已被實測攻破」寫成下一輪可以照著做的規格，
並且**把三案九鏡花掉的實測結論全部保存下來，讓 R61 不必重跑一遍**。

---

## 8. 未解決與交棒（具名承接，非「下一輪某人」）

| # | 未解決項 | 依據 | 承接者（具名） | 完成判準（可機械查） |
|---|---------|------|--------------|--------------------|
| 1 | **`Find-GitBash.ps1` 分隔符不敏感缺陷未修**（活缺陷，判定語意分歧已實測、可觸達性為條件式） | §2.4 | **R61**（Phase 1-A） | §2.4 五筆路徑表兩語言裁決逐筆相同；bug-injection 改回舊 regex 須紅 |
| 2 | **字面 parity 鎖仍被當成機械釘選**（`test_find_git_bash_parity.py` 全綠而底下有活分歧） | §2.4／§3.2 | **R61**（Phase 1-A） | 該鎖的 System32 段改為行為表驅動；Sysnative 進「已實測不涵蓋」常駐表 |
| 3 | **`install_git_hooks`／`install-hooks` 兩對零守門**（掛在決策豁免，無機制阻止長回業務邏輯） | §2.3 | **R61**（Phase 1-B） | UEP 8 → 6；交叉鎖行變「7 對／14 支」 |
| 4 | **UEP／AC 尚未印出、未閘門化**（本 ADR 的判準目前只能手跑一支 scratchpad 腳本） | §4 | **R61**（Phase 1-C，須與 1-B 同 commit） | `python tools/check_script_parity.py` 輸出含 `UEP=` 與 `AC=`；棘輪照 `TestShrinkOnlyRatchet` 形狀 |
| 5 | **`check_wrapper_thinness._normalize` 的 BOM 缺陷**（宣稱剝整行註解，對每支 `.ps1` 的第 1 行失效；而該文字就是 hash 釘選的輸入） | §2.5 | **R62**（Phase 2-E，單獨 commit） | `utf-8-sig` ＋ 10 支 hash 重釘 ＋「BOM 不影響正規化」回歸；`integration_gate.ps1` 正規化由 14 行變 13 行 |
| 6 | **測試數基線三值不一致**（源碼 845／一鏡 916／另一鏡 901），所有以測試數為等價證明的 gate_proof 都算在不確定的基準上 | §6 邊界 8 | **R61**（動工第一件事） | 並行包全部 commit 後於乾淨樹實跑 `python tools/run_root_unittests.py`，把印出的「發現 N 個測試」直接填 `MIN_TESTS`（不做加減推算，該檔 :48 註解明文），再跑 `python tools/sync_onboarding_baselines.py --write` 同步 §7 live 格、`--check` rc=0 |
| 7 | **護欄層 LOC 預算未設計**（根層 `tools/**/*.py` 74 檔／32,708 行零預算；`AutoClaude/tests` 279 檔／57,351 行亦零預算）——這是 Architect 批評的「速率」問題的唯一結構性解，本 ADR 只給了具名要求，沒有落地 | §4.3／Phase 2-F | **R62+**，且需 **PM signoff**（成長係數與 WARN 帶是政策判斷） | `tools/.loc_baseline` 由程式當場量測寫入；量測面含 `_` 前綴；`AutoClaude/tests` 的劃界寫成明文；六項具名要求逐條可查 |
| 8 | **`ci-gate.ps1` fallback 刪除的政策未拍板**，且「刪它低風險」目前仍是讀碼推論（本機有 Git Bash，造不出鑑別力） | Phase 2-B | **R62+**，需**使用者／PM signoff** | signoff 記錄 ＋ `ONBOARDING.md` §6 那格 fallback 散文同步刪除 ＋ DEF-101-512 補丁退場 |
| 9 | **CI workflow 層 1,974 行、27.6% 重複、alert job 100% 重複，完全在本 ADR 射程外** | §6 邊界 6 | **未指派**（需新機制：pyyaml workflow parity；且 DEF-101-081 帳單停擺期間無 CI 回饋通道，改完無法實跑驗證） | 若要納管：新增 workflow parity 斷言並讓 UEP／AC 涵蓋 workflow 對 |
| 10 | **Copy-on-Evolve 1/30 對跨語言對子無解**（R45 的共享層手法只適用同語言同 runtime） | §6 邊界 9 | **未指派**（政策層，掛 `DEF-101-392`／`DEF-101-401`，本 ADR 不取代那筆決策） | 依 `ADR-XPLAT-001` §5 的核准層級處理 |

---

## 9. 落地自檢（本 ADR 自己的取證）

```
$ python tools/check_ntfs_paths.py > /tmp/ntfs.txt 2>&1; echo REAL_RC=$?
（結果見本 ADR 落地時的 commit 訊息／複審回報；本節不寫死該值以免成為第二個 stale 站點）
$ python - (bytes 層檢查本檔)
CRLF count = 0        # 必為 0：.gitattributes 宣告 * text=auto eol=lf
BOM = False
```

檔案以 **bytes 層寫入並強制 LF**（`Path.write_bytes`），不用 `Path.write_text()`——後者在 Windows 會
寫成 CRLF，這是 `ADR-XPLAT-001` §4.2 第 2 條已記載的常設紀律（R44 曾把數十支檔行尾靜默改成 CRLF）。

---

## 10. 相關

- **ADR**：`ADR-XPLAT-001`（凍結版回補判例；本檔的姊妹，互不覆蓋）、`ADR-SD09-011`
  （「把判準從日曆解綁成單調量」的先例，本檔 UEP 沿用同型思路）
- **判例檔**：`docs/06_quality/CrossPlatform_Scan_Dimensions.md`
  — §76「WindowsApps guard 三語言等價實作為何不可收斂」（Tier-2 的定案依據）、
  §93「靜態掃描錨為何從三份複本收斂為 SSOT」（兩層分診問句；本檔 §3.2 對它**補訂**：
  它只收斂了資料，沒收斂判定語意）、§143 三段式邊界宣稱寫法（本檔 §6 沿用）
- **登記表／守門工具**：`tools/check_script_parity.py`、`tools/check_wrapper_thinness.py`、
  `tools/_script_scan_surface.py`、`tools/tests/_ps_engine.py`、`tools/tests/test_platform_utils_dedup.py`
  （repo-wide dedup 掃描器，Phase 2-C 的呼叫端鎖擴充點）、
  `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet`（唯一真棘輪先例，§4.4）
- **契約先例**：`tools/git_hooks_install_common.py`（Tier-1 活體樣板）、
  `tools/lib/bash_probe_spec.py`（Tier-2 活體樣板，須擴充判定規則）
- **雙平台對照與基線**：`ONBOARDING.md` §6／§6.1／§7（§7 為全 repo pytest 基線唯一站點，
  由 `tools/check_pytest_baseline_sites.py` 機械守門；live 格由 `tools/sync_onboarding_baselines.py` 回填）
- **紀律**：R12 QA-2「兩訊號合流即單點化」（Tier-4 的依據）、DEF-101-511（`windows_smoke_local.ps1`
  偵測 `$env:MSYSTEM` 即拒跑）、DEF-101-249（`New-ScheduledTaskSettingsSet` 參數名與屬性名極性相反）
