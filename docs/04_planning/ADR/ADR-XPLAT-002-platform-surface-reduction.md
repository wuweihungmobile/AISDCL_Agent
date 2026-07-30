# ADR-XPLAT-002：跨平台「需驗證平面」收斂架構與其可機械追蹤的下降判準

| 欄位 | 內容 |
|------|------|
| **狀態** | Accepted（**設計交付**，R60）。本 ADR **不在 R60 執行任何遷移**——理由見 §7，那不是保守，是四條實測出來的阻礙。🔴 **R61 更新**：Phase 1-B 已落地（UEP 8→6）＋ Phase 1-C 最小可行切片已落地（`--print-collapse`），Phase 1-C 全量與 Phase 2 仍待後續輪次；見 §5 Phase 1 表內逐列「R61 已落地／R61 部分落地」標記與 R61 對 `DEF-101-561` 四處合併提案的裁決段。🔴 **R62 更新**：Phase 2-E 經查證已於 **R60 round 3 同一輪內**由另一個平行修復包（P10-1）落地——本 ADR 本身即**與該修復包同屬 commit `796c7a6`**（`git log --follow --diff-filter=A` 證實本 ADR 檔案首次入庫正是這個 commit；commit message 自陳「本次推送的定位是已驗證綠燈狀態的耐久性保全」，屬同輪多個並行修復包一次彙整 checkpoint，非單一線性先後），**非「Phase 2-E 先修好、ADR 後定案時漏追」這種乾淨先後順序**，而是同一輪內兩個互不知情的並行產出、彼此未同步：§5 Phase 2 表與 §8 交棒表因此原將已完成的 P10-1 誤列為「R62 待辦」，屬過期宣稱，R62 訂正為已結案；R62 本輪另補齊 R61 §5 1-B 列遺留的「未跑 `windows_smoke_local.ps1` 真實安裝」驗證缺口（PASS=12/FAIL=0，原生 PowerShell）並執行全專案 Scan-A~H 複掃（零新缺陷）；Phase 1-C 全量評估後判斷仍延後，理由見 §5 Phase 1-C 列。詳見 `docs/06_quality/CrossPlatform_R62_Architect_Evidence.md`。🔴 **R63 更新**：Phase 1-C 全量 (a)(b)(d) 已落地（(c) 於 R61 完成）——4 組異名對等品字典化 + stale 自檢、23 筆 `_EXEMPT_PAIRS`/`_SINGLE_SIDED_EXEMPT` 逐一 tier 分類（6 類合法值）、tier3/4 硬理由關鍵詞斷言，`--print-collapse` 擴充為逐對印出 tier/reason；UEP=6／AC=46 不變（純內部結構升級，不影響 §4.1/§4.2 計數公式）；棘輪化本身另立為新的未指派項（§8 item 12）。另訂正 §8 item 6「測試數基線三值不一致」——親跑複驗後確認已於 R60/R61 一般日常維護中意外解決（非本表原排定的「R61 動工第一件事」），本表原文屬過期宣稱，R63 訂正。詳見本輪 R63 commit 訊息與工作樹逐字實測（本輪未另立獨立 Evidence 檔，證據內嵌於 §5 Phase 1-C 列與 §8 item 6/12）。🔴 **R64 更新**：§8 item 12「UEP 棘輪化」已落地（見該列，`tools/check_script_parity.py::tier_ratchet_problems()` 比照 `TestShrinkOnlyRatchet` 五件套形狀，10 支新測試）；全專案掃描零新缺陷（唯一疑似案例覆核後證實是既有 `DEF-101-019` wontfix 舊案）。另在 Windows 11 機器親跑真實驗證時意外發現並修復兩筆與本項無關的既有缺陷：`DEF-101-617`（`tools/tests/test_bash_probe_spec_contract.py` 的 `_BASH` fixture 天真信任 `shutil.which("bash")`，在 Git Bash 未直接掛系統 PATH 的機器上會誤判 WSL System32 佔位版為可用 bash，致 6/8 測試確定性失敗，已修復並驗證）與 `DEF-101-618(b)`（姊妹檔 `test_windowsapps_guard_bash_parity.py` 同型缺陷同步套用相同修法）；`DEF-101-618(a)`（`Git\bin\bash.exe` 啟動器自我注入內部 PATH、使「限縮外部 PATH 模擬缺 coreutils」測試手法對其失效）判斷需人工設計決策，本輪誠實留列 `open`，未強修。詳見缺陷帳本 `DEF-101-617`／`DEF-101-618` 兩列，本輪未另立獨立 Evidence 檔 |
| **日期** | 2026-07-29（R60 收輪；量測時點見 §2 各條，HEAD `e3a5c53`、工作樹 dirty 81 筆）；**R61 執行更新 2026-07-30**（詳見 `docs/06_quality/CrossPlatform_R61_Architect_Evidence.md`）；**R62 執行更新 2026-07-30**（同日接續，詳見 `docs/06_quality/CrossPlatform_R62_Architect_Evidence.md`）；**R63 執行更新 2026-07-30**（同日接續，證據內嵌本檔 §5/§8，未另立 Evidence 檔）；**R64 執行更新 2026-07-31**（證據內嵌本檔 §8 item 12 與缺陷帳本 `DEF-101-617`／`DEF-101-618`，未另立 Evidence 檔） |
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

### 2.4 ~~🔴~~ `Find-GitBash.ps1` 的 System32 排除在斜線路徑下失效（**已於 R60 修復；本節降為史料**）

> 🔴 **狀態訂正（R60 round 3，Pkg-E）**：本節原文寫「活缺陷」，那是相對於 HEAD `e3a5c53`（R59）
> 的敘述。本 ADR 落地後、同輪 R60 的 P10-2 已修復並隨 `796c7a6` 入庫：`Find-GitBash.ps1` 的行內
> `-notmatch '\\System32\\'` 已改為 `Test-HasSystem32Segment` 逐段比對（與 Python 側
> `PureWindowsPath` 同語意），並新增 `test_find_git_bash_parity.py::TestSystem32VerdictParity`
> **行為表 parity 鎖**（真的起 PowerShell 執行、非比對原始碼字面）。
> **依 HEAD `796c7a6` 讀本節時，下列輸出全部是修前史料，不是現況。**
>
> Pkg-E 於 HEAD `796c7a6` 以原生 PS 5.1 重驗（真實 WSL bash 在位：
> `C:\Windows\System32\bash.exe` 確實存在於本機，故本次量測具鑑別力而非空跑）：
>
> ```
> PATH_FORM=[C:/Windows/System32] GetCommand_Source=[C:/Windows/System32\bash.exe] FindGitBash=[(none)]
> PATH_FORM=[C:\Windows\System32] GetCommand_Source=[C:\Windows\System32\bash.exe] FindGitBash=[(none)]
> PATH_FORM=[C:/Windows\System32] GetCommand_Source=[C:/Windows\System32\bash.exe] FindGitBash=[(none)]
> ```
>
> 三種分隔符形態（含病灶本體的全正斜線、與 `Get-Command` 實際產出的混用形態）皆正確回 `(none)`。
>
> **殘餘盲區的精確狀態（措辭刻意講清楚，避免被讀成已收斂）**：`C:\Windows\Sysnative\bash.exe`
> **兩側實作都不排除**——盲區本身存在於 PS 與 Python **兩份**實作中，不是「只剩一份」；
> 因 1-D 判定 NO-GO、生產側仍是兩份實作，這個狀態在 R61 不會改變。
> **一份的是「記載」**：兩側共用同一條判準邊界敘述，登記在 `Find-GitBash.ps1` 的 comment-based help
> 與 `test_find_git_bash_parity.py::_SEGMENT_CASES` 最後一列（`expected_excluded=False`，
> 逐字標「已知殘餘盲區、非已驗證安全」），且該列由行為表鎖強制**兩側同判**
> ⇒ 任何一側想單邊收掉它都會轉紅，不會有人靜默處理。
> **未驗事項（誠實劃界，沿用 SD round 3 的保留）**：Sysnative 在 32-bit 行程下是否真可觸達，
> 本輪仍未實測；記載僅主張「兩側一致不排除」，不主張「安全」。

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
| 🔴 **R61 實測（已達成）** | **6**（`_EXEMPT_PAIRS`=5 + `_TLC_TRACK_ENROLLED`=1） | Phase 1-B 已落地：`install_git_hooks`／`install-hooks` 兩對遷入 `_THINNESS_ENROLLED`；上列指令 2026-07-30 工作樹重跑，詳見 `docs/06_quality/CrossPlatform_R61_Architect_Evidence.md` |
| **R62+ 目標** | **≤ 4** | Phase 2-A（run_tlc）＋ Phase 2-B（ci-gate，需 signoff） |
| **地板（可辯護殘留）** | **4** | `run_local_nightly`（R11 D1 拍板兩側語意刻意不同）／`init_project`（§3.3 #6）／`install_post_commit`／`run_self_evolution` |

**對偶判準（必須同時上升，否則 UEP 下降只是把列刪掉）**：

| 指標 | 基線（實測） | R61 目標 | 🔴 R61 實測（已達成） |
|------|------------|---------|----------------------|
| `len(_THINNESS_ENROLLED)` | 5 | ≥ 7 | **7** |
| `len(_PINNED_SHA256)` | 10 | ≥ 14 | **14** |

兩者今天就在 `check_script_parity` 的「thinness 交叉鎖」那一行同時 print（實測逐字
「✅ thinness 交叉鎖：5 對薄殼登記與 10 支 hash 釘選鍵集合一致」），零新增度量檔即可逐輪追蹤。
R61 落地後同一行印「✅ thinness 交叉鎖：**7 對**薄殼登記與 **14 支** hash 釘選鍵集合一致」
（`python tools/check_script_parity.py` 逐字輸出，2026-07-30 工作樹實測，rc=0）。

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

基線：**見上列指令的現查值，本節刻意不寫死行數**。

🔴 **原基線「56 支／25,092 行（2026-07-29T00:55:37Z）」已作廢，且是依本節自己的規則作廢的**
（R60 round 3 Architect `ARCH-R60R3-03` 命中，Pkg-E 複驗成立）：

- 該數取自 §1.1 在 HEAD `e3a5c53`、`git status --porcelain | wc -l` = **81**（兩包並行修復進行中）
  的量測。依本節下方「唯一規則」，**跨時點量測無效** ⇒ 它從寫下的那一刻起就不是合格基線。
- 同一個「56 支」在三處被寫成三個不同行數：`DEF-101-565` 寫 23,329、本節原寫 25,092、
  Architect 與 Pkg-E 各自在 HEAD `796c7a6` 實測 **26,286**。**集合相同而行數不同**，正是
  §1.1 已經診斷過的那個現象——而它發生在宣告該病的文件自己身上。
- Pkg-E 實測（HEAD `796c7a6`，上列兩道逐字指令，同一秒連量兩次皆同值）：

  ```
  $ git status --porcelain -- tools/tests/          # 量測面乾淨性取證：空輸出
  $ ls tools/tests/*.py | wc -l
  56
  $ python -c "import pathlib;t=list(pathlib.Path('tools/tests').glob('*.py'));print(sum(len(p.read_text(encoding='utf-8',errors='replace').splitlines()) for p in t))"
  26286        # REAL_RC=0；緊接著重跑一次仍為 26286
  ```

- 🔴 **同一個 session 內，本規則又被實地驗證了一次**：Pkg-E 完成上列量測後繼續作業約數十分鐘，
  期間並行包寫入 `tools/tests/`（`test_adr_xplat001_c1c2_lock.py`／`test_doc_loc_baseline_freshness_r60.py`／
  `test_platform_neutral_paths.py` 轉為未提交變更）。**同一個 HEAD `796c7a6`、同一台機器**重量：

  ```
  $ git status --porcelain -- tools/tests/          # 3 支檔已髒 ⇒ 依本節規則，此次量測不得作為基線
  $ python -c "…同一道指令…"
  56 files 27369 lines                              # 檔數仍 56，行數 26,286 → 27,369（+1,083）
  ```

  **檔數 56 三次量測完全不動、行數三度不同。** 這正是 §1.1 的現象在 round 3 的重演，
  也是「GLC 只能同 commit 前後配對比較、且量測面必須乾淨」這條規則的最新實據。

**⇒ 本節此後不再登載任何行數常數。** 要引用 GLC 一律跑上列指令現查；要比較就照下方唯一規則
在同一個 commit 上前後各量一次。任何文件（含帳本）若要寫下 GLC 數字，必須同時寫下
「HEAD sha ＋ 量測時點 ＋ 當時 `tools/tests/` 是否乾淨」三者，否則該數字不可被引用為基線。

**本 ADR 刻意不對 GLC 設任何上限**，並明文否決兩種上限：
- A 案的 `TOTAL_INCREASE_LIMIT=1.20` ⇒ §2.6/§3.0 實測 6,541 行免費額度＝好幾輪內收不到代價；
- C 案的零餘裕棘輪 ⇒ repo 現實鏡實測 34/40 個相關 commit 淨增行，會優先咬住它宣稱要保護的
  那類跨平台加固，而「只准往下調」封死了唯一出路。

**唯一規則**：GLC 必須在**同一個 commit** 上前後各量一次，跨時點／跨並行包比較無效（§1.1 實測依據）。

> **R60 round 3 訂正（Pkg-E）——「乾淨」指的是量測面，不是整棵樹**：原規則搭配 §2 的
> `git status --porcelain | wc -l` 記法，實務上被讀成「整個工作樹必須乾淨」。那個門檻在本 repo
> 幾乎永遠達不到（並行包、`.perf_baseline.toml` 這類自動寫回的檔），結果是規則被繞過而非被遵守。
> **正確判準：量測面 `tools/tests/*.py` 內零未提交變更即可**——GLC 只讀這 56 支檔，樹上其他檔
> 髒不髒對這個數字沒有因果影響。Pkg-E 本次即在 `git status --porcelain` = 4 但
> `git status --porcelain -- tools/tests/` = **0** 的條件下取得 26,286，並連量兩次同值。
> 取證指令：`git status --porcelain -- tools/tests/`（**空輸出**＝該次 GLC 可作為基線）。
真正的預算設計列 Phase 2-E，並在該處寫明具名要求（含 `AutoClaude/tests` 57,351 行為何不納管的劃界）。

### 4.4 若要把 UEP 閘門化：照哪一支抄

R61 Phase 1-C 若要把 UEP 釘成上限，**必須照 `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet`
的形狀**（`git show HEAD:<鎖檔>` 取上一版常數機械比對，調升即紅），**不要照 `check_loc_budget.py`**（§2.6：那不是棘輪）。
且該棘輪自己已記載一個既知空轉窗口（鎖檔首個 commit 上 HEAD 還沒有它可比 ⇒ `skipTest` 並印理由），照抄時一併照抄。

### 4.5 SDS（語意分歧面）—— 補 UEP 量不到的那一類（R60 round 3 新增）

> **為何新增**：round 3 Architect 的批評成立且必須入帳——本 ADR 把跨平台面上**唯一一個已被實證
> 「兩份生產實作可對同一輸入給出相反裁決」**的站點（`Find-GitBash`）歸類為 Phase 1-A「修缺陷、
> 不得計入收斂成果」，然後把收斂額度全押在 `_EXEMPT_PAIRS` 的登記表搬移（1-B）。
> 那個批評的實質是：**UEP 這把尺量的是「有沒有守門」，量不到「有幾份實作可以分歧」。**
> 一個站點可以 UEP 記 0（有鎖看著）卻仍持有兩份會分歧的生產碼；R60 的 P10-2 就是活證據
> ——舊鎖全綠、兩側裁決相反。故補本判準，**不動 §4.1～§4.4 任何定義**。

**定義**：SDS ＝「同一語意、有 ≥2 份**生產**實作（非測試），且分歧時的後果是**使用者拿到錯誤行為
而不是紅燈**」的站點數。測試側的獨立重寫**不計入**——那是刻意保留的鑑別力
（`bash_probe_spec.py` docstring 的主張在「測試 vs 生產」這一層成立，本 ADR 採納）。

| 站點 | 兩份實作 | 現況 | 計分 |
|---|---|---|---|
| Git Bash 偵測的 System32 排除判定 | `tools/lib/Find-GitBash.ps1::Test-HasSystem32Segment`（PS）／`tools/integration_gate_core.py::_has_system32_segment`（Py） | R60 後兩側同語意，由行為表 parity 鎖逐筆守住；**實作仍是兩份** | SDS **記 1**（未歸零） |

**當前 SDS ＝ 1**（本 ADR 盤點面內；R61 開輪時應重新盤點，不得沿用本數字）。

**計分規則（與 §4.2 三條並存，不取代）**：

1. 一個標的使 **ΔSDS < 0**（某站點的生產實作由 N 份真正變 1 份）即**可計入收斂成果**，
   即使 ΔUEP = 0。這正是 Architect 要的「不要用 UEP 這把量不到它的尺去否定它」。
2. 但 **ΔSDS < 0 不是免費通行證**：仍須通過 §4.2 rule 2 的反位移檢查——
   若消掉一份 in-process 實作卻引入一個**行程邊界**（subprocess／新 CLI 進入點／新失敗模式），
   須逐條列出新增的失敗模式並論證淨值為正。**1-D 正是卡在這一條而非只卡在 python 可用性**。
3. SDS 歸零**不是無條件目標**。Tier-3（OS 原語）與 Tier-4（明文禁止收斂）底下的多份實作
   依 §3.3／§3.4 本來就不該收斂，**不列入 SDS 盤點面**。

**與 GLC 的搭配**：ΔSDS < 0 的標的允許以「GLC 下降 ＋ SDS 下降」雙記分；
若 GLC 上升而 SDS 下降，須在同一 commit 內具名說明上升的行數買到了什麼
（照 §4.2 rule 2 的同型舉證責任）。

---

## 5. 分階段遷移計畫

### Phase 0 —— R60（本輪）：**只交付本 ADR，零程式碼變更**

等價性證明：`git status --porcelain` 中本輪新增的唯一檔案是本 ADR（`docs/04_planning/ADR/`）；
不觸及任何 `.sh`／`.ps1`／`tools/*.py`／登記表 ⇒ §1.2 的六個基線值結構上不可能變。
落地後實跑 `python tools/check_ntfs_paths.py`（rc 見 §9）。

### Phase 1 —— R61（**三步必須在同一輪落地；前置＝兩包並行修復全部 commit、工作樹乾淨、基線重取**）

| 步 | 動作 | 本輪可安全執行 | 等價性證明（跑哪個閘門、看什麼數字） |
|---|------|--------------|--------------------------------|
| ~~**1-A**~~ | ~~修 `tools/lib/Find-GitBash.ps1`：`-notmatch '\\System32\\'` → 分隔符不敏感形態~~ 🔴 **已於 R60 落地，本步從 Phase 1 移除**（見 §2.4 狀態訂正）。R60 實作**不同於本步原本開的藥方**且更強：不是換一個分隔符不敏感的 regex（`'[\\/]System32[\\/]'` 對「System32 為結尾段、無尾隨分隔符」仍會漏），而是 `Test-HasSystem32Segment` 以 `-split '[\\/]+'` **逐段比對**，與 Python 側 `PureWindowsPath(path).parts` 同語意。`bash_probe_spec.py` 未增列判定規則常數——改以行為表 parity 鎖直接鎖「兩側對同一輸入同判」，比鎖常數更貼近真正會分歧的東西 | **已完成（R60）** | R60 已交付：① 行為表 7 筆逐筆兩側同判（`TestSystem32VerdictParity`，真起 PowerShell）；② 端到端沙箱假檔 + Pkg-E 於 HEAD `796c7a6` 以**真實在位的 WSL bash** 重驗三種分隔符形態皆 `(none)`；③ UEP／AC 不變（確為修缺陷，未計入收斂成果） |
| **1-D**（R60 round 3 新增，取代原 1-A 的位置） | 🔴 **`Find-GitBash` 的「判定」單源化——本輪評估後判定 NO-GO，不排入 R61 執行，改列為「已具名封存的設計選項」**。標的：PS 側只枚舉候選路徑，accept/reject 決策委派 Python（`python tools/lib/bash_probe.py --accept <path>`），一次消掉整個 PS↔Python 判定分歧平面 | 🔴 **阻塞中（見下方阻塞條件）** | 見下方〈1-D 決策紀錄〉 |

#### 1-D 決策紀錄（R60 round 3，Pkg-E 實測後裁決：**NO-GO**）

**提案來源**：R60 round 3 Architect 架構評估段。其論證的前提是
「`ci-gate.ps1` 第 34-38 行已經在跑 `python -m ...` ⇒ Python 在該時點必然可用」。

**🔴 該前提經實查為偽（兩重）**：

1. `ci-gate.ps1` 第 34-38 行**全部是註解行**（逐行首字元為 `#`），它們只是在散文裡*提到*
   `python -m pytest`。真正的 `python` 呼叫在第 **50／55／62** 行。
2. 那三行全都在 `Find-GitBash`（第 **22** 行）**之後**，且全在「找不到 Git Bash」才會走的
   fallback 分支內。該分支起頭第 40-43 行還有一道 `Test-IsRealPython` 前置守門，
   python 不存在時逐字印「❌ 找不到 python…」並 `exit 1`——**該腳本的設計本身就明文預期
   python 可能不存在**（第 36-37 行註解逐字：「全新 Windows 11 機器未裝真 Python…」）。

**三個呼叫端的 python 可用性實查（Pkg-E，原生 PS 5.1，HEAD `796c7a6`）**：

| 呼叫端 | Find-GitBash 呼叫行 | 該行之前是否保證 python | 證據 |
|---|---|---|---|
| `AISDLC_SDD/scripts/install-hooks.ps1` | 35 | ✅ **保證** | 第 13 行 dot-source `GitHooksInstallCommon.ps1`，該檔**頂層**（非函式內）第 52-58 行 `Test-IsRealPython` 失敗即 `[Environment]::Exit(1)` |
| `AutoClaude/tools/install_git_hooks.ps1` | 58 | ✅ **保證** | 同上，dot-source 在第 27 行 |
| `AISDLC_SDD/scripts/ci-gate.ps1` | 22 | ❌ **不保證** | 第 22 行前只有 4 行功能碼（`$ErrorActionPreference` / `$env:PYTHONUTF8` / `$repo` / dot-source `Find-GitBash.ps1`），**無任何 python 守門**；`WindowsAppsGuard` 遲至第 39 行才載入 |

兩側皆以**注入實測**取證，非讀碼推論：

```
# (a) 兩支安裝腳本：PATH 抽掉 python 後 dot-source 共用檔 —— 硬中止，走不到 Find-GitBash
python_resolves_to=
BEFORE_DOTSOURCE
❌ 找不到 python — 請先啟用 venv：…
INNER_RC=1                      # REACHED_AFTER_DOTSOURCE 未印出
# 控制組（PATH 正常）：python_resolves_to=…\.venv\Scripts\python.exe → REACHED_AFTER_DOTSOURCE 印出

# (b) ci-gate.ps1 前導段逐行複刻，PATH 抽掉 python —— Find-GitBash 照跑且成功
python_resolves_to=[]
FindGitBash_RAN_WITHOUT_PYTHON=[C:\Program Files\Git\bin\bash.exe]
```

**⇒ 三個呼叫端中有一個（`ci-gate.ps1`）在 Find-GitBash 執行時點不保證 python 可用，
且該路徑今天在 python 完全缺席下運作正常。** 依「任一呼叫端不保證即不出此變更」的決策規則，
判定 **NO-GO**。

**除了阻塞條件之外，Pkg-E 另有三條獨立的架構理由反對此案**（即使阻塞條件被解除亦成立，
R61+ 若要重啟必須逐條回應）：

1. **失敗模式反轉**。`Find-GitBash` 在兩支安裝腳本裡的職責是「**偵測前置條件缺失並警告**」。
   讓這個偵測器自己依賴另一個前置條件，等於在最需要它的那類機器（配置最不完整者）上，
   偵測器本身成為第一個壞掉的東西。在 `ci-gate.ps1` 上更糟：python 缺席時 Find-GitBash 若回 null，
   使用者看到的是「找不到 Git Bash」→ 落入 fallback → 才被告知「找不到 python」，
   **兩段式誤導**（第一段訊息與真因無關）。
2. **淨平面是增加而非減少**。今天 PS 側的「判定」總共是 `Test-HasSystem32Segment` 的
   **6 行函式本體**（純字串切段，無 I/O、無外部行程）。單源化要把這 6 行換成：跨行程呼叫 ＋
   python 可用性守門 ＋ 退出碼判讀 ＋ 輸出解析 ＋ 編碼處理 ＋ 一支新的 Python CLI 進入點，
   而契約測試**仍然必須起 PowerShell**（否則就退化成比字串，正是本輪在修的病）。
   以一個 6 行的純函式分歧面，換一個多模式的行程邊界失敗面（python 找不到／找到錯的
   python／WindowsApps 空殼／編碼／逾時），**GLC 與 UEP 兩把尺上都不會下降**。
3. **殘餘風險已接近零**。這 6 行現由 7 筆行為表逐筆兩側同判 ＋ 端到端真 WSL bash 三形態
   實測守著。Architect 批評「逐案補不是消除平面」在通則上正確，但套到這個站點時，
   被消除的平面小於被引入的平面——**這是本 ADR §4.2 rule 2「換個地方複雜」要擋的形狀**，
   只是這次換的地方是行程邊界而不是登記表。

**阻塞條件（具名，解除後才可重議）**：
`AISDLC_SDD/scripts/ci-gate.ps1` 第 22 行的 Find-GitBash 呼叫必須落在一道 python 可用性守門**之後**。
唯一乾淨的解除路徑是 **Phase 2-B**（刪除 fallback 3-stage，改「找不到 Git Bash → fail-loud exit 1」）
——它需要 🔴 使用者／PM signoff，且 2-B 自己的低風險依據目前仍是讀碼推論（需一台無 Git Bash 的
乾淨 Windows 機器）。**2-B 落地前，1-D 不具備可行性前提。**

**明文否決的折衷設計（避免 R61 重新發明）**：「安裝腳本走內嵌 PS fallback ＋ 契約鎖，
`ci-gate` 走 Python 單源」的混合案 **更差**——它會造出**兩條** PS 判定路徑（內嵌一條、委派一條），
語意分歧面從 1 變 2，與本案初衷相反。反向的混合（只在保證 python 的兩支安裝腳本單源化）同樣
留下兩份實作，一樣不得分。**1-D 要嘛三個呼叫端一起做，要嘛不做。**
| **1-B** | `AutoClaude/tools/install_git_hooks` 與 `AISDLC_SDD/scripts/install-hooks` 由 `_EXEMPT_PAIRS` 移入 `_THINNESS_ENROLLED` ＋ `_PINNED_SHA256` 補 4 支 hash。**零程式邏輯變更** | ✅ **R61 已落地** | ① 納編前先跑 `wc -l` 四支確認 raw ≤ 100（§2.3 已實測 50/65/40/42，仍須在乾淨樹重量）——**R61 複驗仍為 50/65/40/42**；② `python tools/check_wrapper_thinness.py` rc=0——**R61 實測 rc=0**；③ `python tools/check_script_parity.py` 的交叉鎖行由「5 對／10 支」變「**7 對／14 支**」——**R61 實測逐字相符**；④ **UEP 8 → 6**——**R61 實測 UEP=6**；⑤ bug-injection：在 `install-hooks.ps1` 加一行實質判定邏輯，thinness hash 須紅——**R61 實測：注入 `foreach (...)` 後 hash 釘選＋並聯關鍵字兩訊號皆轉紅（rc=1），revert 後 `git diff` 確認四支腳本零位元變動、rc 復綠**；⑥ 兩平台 smoke 的 install/uninstall 往返 + linked-worktree 拒絕三情境須全綠（Windows 側須以**原生 PowerShell** 啟動，DEF-101-511）——**未跑（本輪只驗證登記層／hash 層，未起 windows_smoke_local.ps1 真實安裝；但四支 .sh/.ps1 檔案本體零位元變動，該情境的既有覆蓋率邏輯上不受影響，非同義於「已驗證」，留待有機會跑 compat-ci 或 smoke 腳本時覆核）**。詳見 `docs/06_quality/CrossPlatform_R61_Architect_Evidence.md` |
| **1-C** | `tools/check_script_parity.py` 內（a）4 組「異名對等品」由 reason 散文升為 4 筆字典 + stale 自檢；（b）`_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的值由純理由字串升為 `(tier, reason)`，`tier ∈ {tier1_contract, tier1_adapter, tier2_spec, tier3_os_primitive, tier4_forbidden, unpinned}`；（c）新增 `--print-collapse` 印 UEP／AC／各對 tier 與 reason；（d）斷言「tier3/tier4 的 reason 必須非空且含硬理由關鍵詞」。**擴充既有檔、零新檔**；測試加進**既有的** `tools/tests/test_check_script_parity.py` | 🟡 **R61 僅落地 (c) 的最小可行切片，(a)(b)(d) R62 評估後仍判斷延後**（非重複拖延——R62 可用產能優先投入訂正 Phase 2-E 過期宣稱、補齊 windows_smoke_local.ps1 真實驗證缺口、全專案 Scan-A~H 複掃三項；(a)(b)(d) 本身的風險評估未變：23 個條目〔`_EXEMPT_PAIRS` 5 ＋ `_SINGLE_SIDED_EXEMPT` 18〕須逐一指定 tier，且至少 3 支既有測試檔對字串型別的依賴須同步改寫，屬多檔連動重構，詳見 `docs/06_quality/CrossPlatform_R62_Architect_Evidence.md`；**留給 R63**）。🟢 **R63：(a)(b)(d) 全數落地，1-C 全量完成**——`_EQUIVALENCE_GROUPS`（4 組字典）+ `_check_equivalence_groups_fresh()`（三種 stale 情境：磁碟消失／未登記／stem 相同）；23 筆 `_EXEMPT_PAIRS`（5）/`_SINGLE_SIDED_EXEMPT`（18）逐一指派 tier（`_check_tier_classification()` 機械驗證二元組型別＋合法 tier＋非空 reason＋tier3/4 硬理由關鍵詞）；`_print_collapse()` 擴充為逐對印出 tier/reason 與異名對等品清單。**未改動任何 `.sh`/`.ps1` 生產碼**，僅擴充 `tools/check_script_parity.py` 本體與既有 2 支測試檔（`test_check_script_parity.py` 新增 12 支 bug-injection 測試、`test_onboarding_parity_interlock.py` 的 2 處 `why`→`why[1]`）；R62 §2.7 grep 複驗延伸再核一次，除原 3 處外未發現其他消費者 | ① `python tools/check_script_parity.py --print-collapse` rc=0 且印出 `UEP=6` / `AC=46`——**R61 實測逐字相符**（未實作完整 `--print-collapse` 的 tier/reason 逐對印出，只印六張登記表長度＋UEP/AC 兩個總量）；② `python tools/run_root_unittests.py` 發現數——**R61 現查：`✅ unittest 數量下限釘選通過：發現 1075 個測試（下限 1069）`，rc=0，非本輪改動所致（本輪新增 6 個 tools/tests 內測試已含在 1075 內）**；③ GLC 檔數不變（零新檔）——**R61 確認：`tools/tests/` 仍 56 支，git status 顯示零新檔；行數 28,118→28,194（+76，來自擴充既有 `test_check_script_parity.py`／`test_check_wrapper_thinness.py`，round 1 Architect 複審訂正原「行數不變」誤寫）**；④ 🔴 **(a)(b)(d) 為何延後**：grep 複驗至少 3 處既有測試直接依賴 `_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的值是**字串**型別（`test_check_script_parity.py:248` 的 `.strip()`、`test_onboarding_parity_interlock.py:105/114` 的 `for key, why in ...items()` 字串比對），把值改成 `(tier, reason)` tuple 屬**多檔連動重構**，其驗證負擔（逐一走過 25 個 `_EXEMPT_PAIRS`/`_SINGLE_SIDED_EXEMPT` 條目 + 至少 3 支既有測試檔同步）超出本輪已排定範圍；(c) 因**不改動既有字串型別**（純附加印出邏輯），無此依賴，故可安全落地。**本切片不違反「1-C 不得單獨落地」**——它與 1-B 同一輪、同一批修改落地；⑤ **R62 新增評估**（(a) 子切片可分割性，advisory、未落地）：(a) 是「4 組異名對等品的 reason 散文升為字典 + stale 自檢」，作用對象是獨立於 `_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的另一份資料結構，同樣**不改動**該兩份表既有的字串型別，故初步評估與 (c) 同型——理論上可比照 R61 對 (c) 的做法單獨安全切出落地，不必等 (b)(d) 完成；但本輪未實測（未 grep 複驗 (a) 是否也有 ≥1 支既有測試對其字串型別的依賴），**留待 R63 動工前先驗證再定**，本輪僅記錄評估結論，不承諾已核實安全。⑥ 🟢 **R63 實測**：`python tools/check_script_parity.py --print-collapse` rc=0，逐對印出 23 筆 `(tier, reason)`（`EXEMPT_PAIRS=5`／`SINGLE_SIDED_EXEMPT=18`）與 `EQUIVALENCE_GROUPS=4`；`UEP=6`／`AC=46` 不變（tier 分類是既有登記表的內部結構升級，不影響 §4.1/§4.2 定義的計數公式，本就不該變動）；`python tools/check_script_parity.py`（完整檢查模式）新增兩道皆綠：「✅ tier 分類完整性：23 筆（_EXEMPT_PAIRS 5 + _SINGLE_SIDED_EXEMPT 18）tier 合法、reason 非空、tier3/4 硬理由關鍵詞齊備」「✅ 異名對等品 stale 自檢：4 組皆新鮮（磁碟存在 + 仍登記於 _SINGLE_SIDED_EXEMPT + stem 確實不同）」；⑦ **bug-injection 紅綠對照**（`TestR63TierClassification`／`TestR63EquivalenceGroupsFreshness`，12 個新測試）：逐一構造「舊字串值格式」「非法 tier」「空 reason」「tier3/4 缺硬關鍵詞」四種紅案例皆轉紅，並證明 tier1/tier2/unpinned 不受硬關鍵詞約束（綠）；異名對等品逐一構造「檔案消失」「未登記單邊豁免」「stem 相同」三種 stale 情境皆轉紅，並證明真 repo 現況是綠的；⑧ `python tools/run_root_unittests.py` 實測 **1087** 個測試（下限 1069，+12 為本輪新增 bug-injection 測試，1075+12=1087，可解釋的增長）、`OK (skipped=10)`、rc=0；GLC 檔數不變（`tools/tests/` 仍 **56** 支，僅擴充既有 2 支檔 `test_check_script_parity.py`／`test_onboarding_parity_interlock.py`，零新檔；`git diff --numstat` 顯示 3 檔變動：`tools/check_script_parity.py` +269/-29、`tools/tests/test_check_script_parity.py` +155/-2、`tools/tests/test_onboarding_parity_interlock.py` +6/-3，合計 430 insertions/34 deletions）；⑨ `windows_smoke_local.ps1` 原生 PowerShell 5.1 重跑：`PASS=12 FAIL=0`（含 `[8/9] check_script_parity.py` 項），rc=0 |

#### R61 對 `DEF-101-561` 四處剝除層合併提案的裁決（**評估後 NO-GO，非 1-D 那種阻塞式 NO-GO，而是「風險/效益不划算」式 NO-GO**）

**提案來源**：`DEF-101-561`（R60 round 1 ARCH-R60-09）routed 給 R61 的三項必評之一（②）：
「同缺面四處合併」——R46 `_has_ssot_guard`（`tools/tests/test_windowsapps_guard_bash_parity.py:334`）、
DEF-101-482 `_ps1_code_lines()`（`AISDLC_SDD/scripts/tests/test_ci_gate_version_resolution.py:241`）、
ARCH-R60-06 `_ps_engine` 相關掃描器、`check_wrapper_thinness._normalize`
（`tools/check_wrapper_thinness.py:269`）——聲稱四處各自重造「剝除註解／docstring」邏輯，
建議抽成 `tools/tests/_source_strip.py` 共享層。

**親讀四份原始碼後的實測發現（本輪 Architect 逐一開啟四個檔案核實，非轉述帳本描述）**：

1. **「ARCH-R60-06 `_ps_engine`」實際指向 Python AST 掃描，不是文字剝除**。
   `tools/tests/_ps_engine.py` 本體只有 PowerShell 引擎選擇述詞（`production_engine()` 等），
   完全不含任何註解剝除邏輯；真正的「剝除」發生在其守門測試
   `tools/tests/test_ps_engine_ssot.py` 的 `_engine_selection_linenos()`（:174），
   走 `ast.parse()` 判斷 `shutil.which(...)` 是否為**真正的 Call 節點**（排除 docstring／
   註解／字串常數內的字面提及）。這與另外三處的「.sh/.ps1 **文字**行剝除」是完全不同的
   機制（AST vs regex），語言也不同（Python vs bash/PowerShell）——DEF-101-561 把兩種
   不同機制都稱為「剝除」，但實際上是**不同問題**（本 ADR §4.5 SDS 判準的精神在此適用：
   不能只因為兩者都叫「剝除」就假設可以共用一份實作）。
2. **其餘三處（`_has_ssot_guard`／`_ps1_code_lines`／`_normalize`）語意互不相同**，
   合併會遺失各自刻意保留的行為：
   - `_has_ssot_guard` 是逐行文字掃描 + 位置錨定正則（非真正 bash 語法解析），
     其 docstring 明文記載對 heredoc、死函式兩種偽裝手法無鑑別力，且逐字寫著
     「複雜度遠超本檔工具定位，留待出現真實呼叫點再評估」——這是 R46 三審
     （一審／QA 二審 bug-injection／Architect 三審）逐輪加固出來的判斷，非本輪可單方推翻。
   - `_ps1_code_lines()` 刻意**只剝整行 `#`**、不剝行尾註解（另有專治該案的
     `_cut_ps_inline_comment()` 處理特定呼叫點），這是有意的窄範圍設計。
   - `check_wrapper_thinness._normalize()` 除整行剝除外還處理 `<#…#>` 區塊註解、
     rstrip 行尾空白、去空行；其 BOM 前提由呼叫端 `_read_source()`（`utf-8-sig`）
     先行處理，`_normalize()` 刻意不重複剝 BOM。
   三者在「是否剝區塊註解」「是否剝行尾註解」「是否剝空行」「BOM 由誰負責」四個維度上
   各不相同，若強行合一，依 §4.2 rule 3 dominance test 必須為每一支既有斷言逐一構造
   突變證明新機制同樣抓得到——尤其 `_has_ssot_guard` 是三輪 bug-injection 調校過的
   位置錨定正則，貿然重寫的回歸風險遠高於它能省下的行數。
3. **就算合併成功，也不會移動任何本 ADR 已閘門化的指標**：GLC（護欄層行數）在 §4.3
   已被本 ADR 自己定性為「報表，不設上限」，UEP／AC／SDS 三個真正閘門化的判準
   皆與這四處測試側 helper 的內部實作方式無關（它們都是**測試側**對不同**生產**檔案
   的獨立驗證邏輯，不是同一份生產程式碼的重複實作——§3.2 Tier-2 已載明「測試側的
   獨立重寫刻意保留、不計入收斂」的原則，本案適用同一邏輯）。

**裁決：本輪不執行**。理由是風險/效益不成比例（高驗證負擔、對已閘門指標零貢獻），
不是像 1-D 那樣被某個具體阻塞條件卡死。**與 1-D 的差異**：1-D 有明確的、可解除的
阻塞條件（Phase 2-B 落地）；本案沒有「阻塞條件解除後就該做」的性質——即使 Phase 2-B
落地或任何其他前置條件被滿足，①的 AST 掃描與②的三處文字剝除仍然是為不同目的、
不同輸入語言服務的獨立邏輯，合併的理由不會因為時間推移而變得更充分。

**若未來仍要重啟**：真正有共同點、且合併風險較低的，是 `_ps1_code_lines()` 與
`_normalize()` 之中「剝整行 `#`」這一個共同子步驟（兩者都在 PowerShell 文字上做
`[ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]`）——若有人重啟此案，
應把範圍縮小到這一個子步驟，而不是四處全收，且仍須先確認 `_ps1_code_lines()` 刻意
不剝行尾註解、`_normalize()` 會多剝空行這兩個行為差異在抽出共用 helper 後不會被抹掉。
`_has_ssot_guard`（bash，位置錨定正則）與 `_ps_engine` 相關的 AST 掃描器**不應**併入
同一個合併範圍。

**DEF-101-561 狀態**：①②本輪評估後轉記獨立可追溯項 `DEF-101-614`（fixed，另案——
`DEF-101-614` 記錄的是本輪實際交付的 Phase 1-B/1-C 最小切片，而非四處合併本身）；
四處合併提案本身維持不執行，本節即為其正式裁決記錄。③邊際效益量測：本輪新增鎖檔數
＝**0**，完全符合 R60 round 3 訂正的「R61 開輪即禁止新增鎖檔、只准合併／刪除」模式。

---

### Phase 2 —— R62+（每項各自獨立，順序可調）

| 代號 | 動作 | 前置／signoff | 等價性證明 |
|-----|------|-------------|-----------|
| **2-A** | `run_tlc.{sh,ps1}` 降為委派 `python -m tools.fsm_runtime.tlc_runner` 的薄殼（**刻意不刪檔**：`AISDLC_SDD_INIT.md:899` ACT-042 追溯列、`cicd/SDD_CICD_BASE_LAYER.md` 多處引用），`_TLC_TRACK_ENROLLED` + `_check_run_tlc_tracks` + `_TLC_TRACK_RE` + `_MIN_EXTRACT_COUNTS['run_tlc_tracks']` 整套客製鎖退場。**若改為刪 `.ps1`**：另需同步 `windows_smoke_local.ps1` 的 `Floor=4` 與 `test_ps51_compat.py` 的 `_TREE_FLOORS[LATEST]` 兩處下限、`formal/README.md`／`SDD_CICD_BASE_LAYER.md`／`AISDLC_SDD_INIT.md` 共 7 處引用，**以及 `ONBOARDING.md:383` §9 那列「改用 v0.30 對應檔」的緩解方案**（C1/C2 機械鎖抓不到，見 §6 邊界 5） | Java 21 已實測可用（§2.8） | ① `python tools/check_script_parity.py` rc=0 且「run_tlc_tracks…6 個 step 標籤一致」那行**消失**，其餘各行逐字不變；② `python -m tools.fsm_runtime.tlc_runner --module SDD_FSM` 修前／修後 rc 與摘要行相同；③ `bash AISDLC_SDD/scripts/ci-gate.sh` 三軌計數逐字不變（它走 `tlc_runner`，`grep -n 'tlc_runner' …ci-gate.sh` → :171）；④ UEP −1；⑤ 依 §4.2 rule 3 逐條證明退場的客製鎖斷言在新形態下有接手者，**沒有接手者的斷言保留** |
| **2-B** | 刪 `AISDLC_SDD/scripts/ci-gate.ps1` 的 fallback 3-stage，改「找不到 Git Bash → fail-loud exit 1 並指路安裝 Git for Windows」。**該對留在 `_EXEMPT_PAIRS`，reason 由「決策豁免」升為「單側實作 + 另側 fail-loud 委派」**（❌ 不得移入 `_THINNESS_ENROLLED`，§2.2） | 🔴 **使用者／PM signoff**（政策：Windows 無 Git Bash 即拒跑） | 低風險依據（實測）：`tools/git-hooks/` 三支 hook 共 531 行純 bash、零 `.ps1` 對等 ⇒ 「Windows 沒有 Git Bash」時本 repo 早已無法 commit/push，fallback 保護的是一個不存在的可用狀態。⚠️ **但「刪它低風險」目前仍是讀碼推論**——需一台無 Git Bash 的乾淨 Windows 機器證明「那台機器連 commit 都已失敗」，本機有 Git Bash（實測 `Get-Command bash` → `C:\Program Files\Git\usr\bin\bash.exe`）無法製造鑑別力。連帶退場 DEF-101-512 那條「防 fallback 收尾字串冒充完整閘門」的補丁，且 `ONBOARDING.md` §6 那格「無 Git Bash 才退回 3-stage fallback」的散文必須同步刪除（否則變 Scan-H 型 stale 散文） |
| **2-C** | LATEST 解析 subprocess 樣板 10 份 → 1（新增 `tools/lib/sdd_latest.py`，內部仍以 subprocess 呼叫 `sdd_version.py --sdd-root`，維持不跨子專案 import）；10 個消費者各改一行 import；**呼叫端鎖擴充既有的 `tools/tests/test_platform_utils_dedup.py`**（已內建 `_scan_repo_py_for(pattern)` 與 repo-wide「共用 helper 不得有第二份定義」機制，加模式即可）⇒ **鎖的數量從 O(helper 數) 變 O(1)** | 並行包全部停工 | ① 基線 `grep -rln '"sdd_version.py"' tools/tests/*.py \| wc -l` → 10（實測），收斂後同指令 → 0；② `python tools/run_root_unittests.py` 發現數不變（純 helper 抽取；若變動即為非等價，須逐筆解釋）；③ bug-injection：任一消費者改回自帶 `_latest_root` ⇒ dedup 鎖須紅；④ GLC 檔數 +0（新檔落在 `tools/lib/`）；⑤ ΔUEP = 0 ⇒ **依 §4.2 rule 1 本步不計入收斂成果，只計入護欄縮減** |
| **2-D** | 5 份 `_FROZEN_SDD_VERSION_RE`／`_FROZEN_VERSION_DIR_RE` + 2 份 `_exclude_frozen_sdd_versions()` 併入 `tools/lib/sdd_latest.py`（只持一份目錄名 pattern，路徑投影機械推導）；7 個呼叫端的 `.match()` 對齊權威源的 `.fullmatch()` | 同 2-C | ① `git grep -n 'AISDLC_SDD_v.d'` 由 5 處生產字面值 → 1 處；② `.match`→`.fullmatch` 須以具鑑別力載具證明**這是修正不是等價**（`re.match(r'^AISDLC_SDD_v\d+\.\d+$', 'AISDLC_SDD_v0.30\n')` 命中 vs `fullmatch` 不命中，兩鏡皆已實測，R62 須自行重跑）；③ 起點可取 `git show 9593d55:tools/tests/_sdd_versions.py`（97 行，該 stash 存在但**從未在當前工作樹執行過**，其 docstring 的實測宣稱一律當「該檔作者的宣稱」處理） |
| **2-E** | 修 §2.5 的 `_normalize` BOM 缺陷：`encoding="utf-8"` → `utf-8-sig`（對齊同檔 `_extract_tlc_tracks` 既有慣例）＋同步重釘 10 支 hash ＋加一支「BOM 不影響正規化」回歸 | 🔴 **已於 R60 round 3 完成（commit `796c7a6`，平行修復包 P10-1）——本 ADR 亦首次入庫於同一 commit（同輪 checkpoint 一次彙整多包，非本表所述工作先落地、ADR 後定案這種乾淨先後順序），屬同輪內兩個互不知情的並行產出彼此未同步，本表原文未追蹤到該平行包產出而誤留為「R62 待辦」，R62 訂正**（見本列右欄 R62 複驗） | ①`_read_source()` 已改 `utf-8-sig`（`tools/check_wrapper_thinness.py:320`，非本表原描述的 `:249`——該行號隨檔案演進已漂移）；②5 支 `.ps1` 側 hash 已於同 commit 重釘（`.sh` 側無 BOM、hash 不變，符合「僅 .ps1 側五支」的原始預期）；③既有回歸鎖 `TestBomIsNotContent`（`tools/tests/test_check_wrapper_thinness.py:382-504`）涵蓋「BOM 不得成為正規化首行」「BOM 有無不得改變 hash」「讀檔口不得依副檔名分歧」「釘選表內 `.ps1` 確實帶 BOM（反恆真）」「原始碼內 `read_text(encoding=…)` 僅一處且值為 utf-8-sig（AST 鎖）」五項斷言，較本列原驗收條件（②③）更完整；**R62 複驗**：`python tools/check_wrapper_thinness.py` → `✅ wrapper 薄殼守門通過（14 支殼 hash 釘選 + 行數上限皆正常）` rc=0；`python -m pytest tools/tests/test_check_wrapper_thinness.py -q -k "Bom or bom"` → `5 passed, 27 deselected, 2 subtests passed`；逐字輸出見 `docs/06_quality/CrossPlatform_R62_Architect_Evidence.md` |
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
   > 🔴 **本條已被事件推翻（R60 round 3 訂正，Pkg-E）**：R60 另一個修復包（P10-2）已在**本輪**
   > 完成此修並隨 `796c7a6` 入庫（`git log -- tools/lib/Find-GitBash.ps1` → `796c7a6`；
   > `git show HEAD:tools/lib/Find-GitBash.ps1` 含 `Test-HasSystem32Segment`、行內 `-notmatch`
   > 僅殘留於 comment-based help 的史料敘述）。上述治理互鎖**實際上並未成為阻礙**。
   > 本條逐字保留不改寫——它是本 ADR 撰寫當下的判斷快照，改寫會抹掉「同輪內其他包的進度
   > 使本 ADR 的前提失效」這個教訓本身；訂正以本標記就地指路。
   > **連帶**：§5 Phase 1-A 已標記為「已於 R60 落地、從 Phase 1 移除」，§2.4 已由「活缺陷」降為史料。
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
| ~~1~~ | ~~**`Find-GitBash.ps1` 分隔符不敏感缺陷未修**~~ ✅ **已於 R60 結案**（`796c7a6`，P10-2）。改為逐段比對 `Test-HasSystem32Segment`，非本表原開的 regex 藥方 | §2.4（已降為史料） | ~~R61~~ **R60 已交付** | 已達成：Pkg-E 於 HEAD `796c7a6` 原生 PS 5.1 重驗，三種分隔符形態 ＋ 真實在位的 WSL bash 皆回 `(none)`；SD round 3 另以「把舊行內 regex 注回沙箱複本」證明該鎖會精準轉紅 |
| ~~2~~ | ~~**字面 parity 鎖仍被當成機械釘選**~~ ✅ **已於 R60 結案**。`TestSystem32VerdictParity` 行為表 parity 鎖已落地（真起 PowerShell 執行，非比對原始碼字面） | §2.4／§3.2 | ~~R61~~ **R60 已交付** | 已達成：System32 段改為行為表驅動（7 筆逐筆兩側同判）；Sysnative 已進 `_SEGMENT_CASES` 常駐表並明文標「已知殘餘盲區、非已驗證安全」 |
| ~~3~~ | ~~**`install_git_hooks`／`install-hooks` 兩對零守門**（掛在決策豁免，無機制阻止長回業務邏輯）~~ ✅ **已於 R61 結案**：兩對遷入 `_THINNESS_ENROLLED`＋hash 釘選，`DEF-101-614` fixed | §2.3 | ~~R61~~ **R61 已交付** | 已達成：UEP 8 → **6**；交叉鎖行變「**7 對／14 支**」（`python tools/check_script_parity.py` 2026-07-30 工作樹實測，rc=0） |
| ~~4~~ | ~~**UEP／AC 尚未印出、未閘門化**（本 ADR 的判準目前只能手跑一支 scratchpad 腳本）~~ —— 🟡 **R61 部分結案**：新增 `--print-collapse` 印出 UEP/AC/六張登記表長度，**尚未棘輪化**（棘輪本身需先完成 1-C 全量 tier 分類才有 tier/reason 可棘輪）；🔴 **R62 複評後維持延後**（理由見 §5 Phase 1-C 列，非重新論證、是產能排序判斷——本輪優先投入訂正 Phase 2-E 過期宣稱＋補齊 windows_smoke_local.ps1 驗證缺口＋全專案複掃）。✅ **R63：tier/reason 逐對印出已完成**（1-C 全量 (a)(b)(d) 落地，見 §5 Phase 1-C 列 R63 段）；**棘輪化本身仍未落地**（tier/reason 資料現已齊備，但「不得調降」的棘輪判準需另立測試，比照 `TestShrinkOnlyRatchet` 形狀——本輪判斷這是獨立的下一步，非本項「印出」的必要條件，故本項就「印出」語意判定已完成，棘輪化改列新的未指派項，見下方新增列） | §4 | ~~R63~~ **R63 已交付（印出部分）** | `python tools/check_script_parity.py --print-collapse` 輸出含 `UEP=` 與 `AC=`（**R61 已達成**）；tier/reason 逐對印出（**R63 已達成**：見 §5 Phase 1-C 列 R63 實測⑥）；棘輪化（照 `TestShrinkOnlyRatchet` 形狀）**仍未落地**，改列 §8 新增項（未指派，R64+） |
| ~~5~~ | ~~**`check_wrapper_thinness._normalize` 的 BOM 缺陷**（宣稱剝整行註解，對每支 `.ps1` 的第 1 行失效；而該文字就是 hash 釘選的輸入）~~ ✅ **已於 R60 round 3 結案**（`796c7a6`，P10-1；非 R61／R62——本表原誤留為 R62 待辦，R62 訂正） | §2.5 | ~~R62~~ **R60 已交付** | 已達成：`utf-8-sig` ＋ 5 支 `.ps1` hash 已重釘 ＋ `TestBomIsNotContent` 五項回歸鎖已存在（`tools/tests/test_check_wrapper_thinness.py:382-504`）；R62 複驗 `python tools/check_wrapper_thinness.py` rc=0、BOM 相關測試 5 passed，見 `docs/06_quality/CrossPlatform_R62_Architect_Evidence.md` |
| ~~6~~ | ~~**測試數基線三值不一致**（源碼 845／一鏡 916／另一鏡 901），所有以測試數為等價證明的 gate_proof 都算在不確定的基準上~~ ✅ **已於 R60/R61 一般日常維護中意外解決**（非本表原排定的「R61 動工第一件事」專項處理——`tools/run_root_unittests.py:48` 的 `MIN_TESTS` 已重釘為 **1069**，`ONBOARDING.md` §7 表①同步為「**1069 tests OK**」；R63 親跑複驗：`python tools/run_root_unittests.py` 實測 **1087** 個測試〔本輪新增 12 支 tier 分類 bug-injection 測試，1075+12=1087〕≥ 1069，`OK (skipped=10)`，rc=0；`python tools/sync_onboarding_baselines.py --check` 亦 rc=0（`{'tests': 1069}`）——三值不一致的病灶本身已不存在，現況只剩單一權威值，本表原「R61 待辦」是過期宣稱，R63 訂正） | §6 邊界 8 | ~~R61~~ **R60/R61 日常維護（R63 訂正紀錄）** | 已達成：`MIN_TESTS`／`ONBOARDING.md` §7／實測值三者一致，`tools/sync_onboarding_baselines.py --check` rc=0（R63 複驗逐字如上） |
| 7 | **護欄層 LOC 預算未設計**（根層 `tools/**/*.py` 74 檔／32,708 行零預算；`AutoClaude/tests` 279 檔／57,351 行亦零預算）——這是 Architect 批評的「速率」問題的唯一結構性解，本 ADR 只給了具名要求，沒有落地 | §4.3／Phase 2-F | **R62+**，且需 **PM signoff**（成長係數與 WARN 帶是政策判斷） | `tools/.loc_baseline` 由程式當場量測寫入；量測面含 `_` 前綴；`AutoClaude/tests` 的劃界寫成明文；六項具名要求逐條可查 |
| 8 | **`ci-gate.ps1` fallback 刪除的政策未拍板**，且「刪它低風險」目前仍是讀碼推論（本機有 Git Bash，造不出鑑別力） | Phase 2-B | **R62+**，需**使用者／PM signoff** | signoff 記錄 ＋ `ONBOARDING.md` §6 那格 fallback 散文同步刪除 ＋ DEF-101-512 補丁退場 |
| 9 | **CI workflow 層 1,974 行、27.6% 重複、alert job 100% 重複，完全在本 ADR 射程外** | §6 邊界 6 | **未指派**（需新機制：pyyaml workflow parity；且 DEF-101-081 帳單停擺期間無 CI 回饋通道，改完無法實跑驗證） | 若要納管：新增 workflow parity 斷言並讓 UEP／AC 涵蓋 workflow 對 |
| 10 | **Copy-on-Evolve 1/30 對跨語言對子無解**（R45 的共享層手法只適用同語言同 runtime） | §6 邊界 9 | **未指派**（政策層，掛 `DEF-101-392`／`DEF-101-401`，本 ADR 不取代那筆決策） | 依 `ADR-XPLAT-001` §5 的核准層級處理 |
| 11 | **`Find-GitBash` 判定單源化（SDS 1 → 0）評估後 NO-GO，阻塞於 `ci-gate.ps1` 的 python 可用性** —— 生產側仍是兩份實作（PS 一份、Python 一份），現由行為表 parity 鎖看著而非物理消滅 | Phase 1-D／§4.5 | **封存中**；解除前置＝ **Phase 2-B**（🔴 使用者／PM signoff） | 解除判準（三者全成立才可重議）：① `ci-gate.ps1` 第 22 行的 Find-GitBash 呼叫落在 python 守門之後（即 2-B 已落地）；② 逐條回應 Phase 1-D 決策紀錄列的三條架構反對理由；③ 依 §4.5 rule 2 列出新增的行程邊界失敗模式並論證淨值為正 |
| ~~12~~ | ~~**UEP 棘輪化尚未落地**（R63 新增項，從舊項 4 拆分）：tier/reason 資料已齊備（R63），但無機械鎖阻止未來把某筆 tier3/4 悄悄改回 unpinned 或刪減硬理由關鍵詞——目前只有「當下合法」的驗證，沒有「不得退步」的棘輪~~ ✅ **已於 R64 結案**：`tools/check_script_parity.py` 新增 `_extract_tier_map_from_source()`（AST 解析上一版 `_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的 tier 值，含 `ast.AnnAssign` 形態）＋ `tier_ratchet_problems()`＋ `_check_tier_ratchet()`（已隨 `main()` 執行，非孤兒函式）；照抄 `TestShrinkOnlyRatchet` 五件套形狀，落地為 `tools/tests/test_check_script_parity.py::TestR64TierShrinkOnlyRatchet`（8 支測試，未新開檔案——比照 `TestGuardFileCountShrinkOnlyRatchet` 的既有慣例擴進本檔，避免觸發 `DEF-101-561③` 的護欄層檔數棘輪） | §4.4 | ~~R64+~~ **R64 已交付** | 已達成：`python tools/check_script_parity.py` 工作樹實測 rc=0（含新增的「✅ tier 棘輪：與 HEAD 版本比對，零降級」一行）；`python -m unittest tools.tests.test_check_script_parity -v` 58 個測試全數 `ok`（含新 10 支：正控自比自零違規、tier3/4→其他 tier 降級偵測、tier1/2→unpinned 降級偵測、升級/不變放行、整筆移出登記表視為收斂放行、字典改名不得靜默放行、對 HEAD 真棘輪、production 呼叫路徑已接線）；`python -m unittest tools.tests.test_adr_xplat001_c1c2_lock.TestGuardFileCountShrinkOnlyRatchet -v` 6 個測試全數 `ok`（確認未觸發檔數棘輪） |

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
