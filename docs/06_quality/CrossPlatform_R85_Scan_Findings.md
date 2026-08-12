# CrossPlatform_R85_Scan_Findings — R85（macOS；P4 唯讀深掃包）

> **本檔的資格**（同 R80~R84 同名檔）：本輪 P4 掃描發現的**唯一居所**。
>
> 🔴 **本檔體例**：會漂移的量測值一律附「哪一支載具會印出它」；每一筆 finding 附
> ①現查指令 ②**我這回合真跑出來的輸出** ③現有鎖為何攔不到（指名到檔與符號）
> ④修法草案＋**持有面**（鐵律七）⑤嚴重度與承接輪次。
>
> 🔴 **本包是唯讀掃描包**：本檔與 `tools/probe/xplat_hazard_census.py` 是本包唯二的寫入；
> 一個既有檔都沒改，一次 git 寫入都沒有。**下列全部是「修復提案」，不是修復。**
>
> 🔴 **平台劃界**：本輪在 **macOS**（`darwin`）。凡結論涉及 Windows 執行期行為者，
> 一律標「**靜態推論、未在真機驗證**」——沿用 R84 §A 的紀律，不得把推論寫成事實。

---

## §0 本包這回合真跑過的指令與輸出（取證清單）

| # | 指令（絕對路徑 python、**讀 rc 不接管線**） | 結果 |
|---|---|---|
| 1 | `.venv/bin/python -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix` | `OK`；`[Xplat injection matrix] Win2mac=6/12 mac2Win=5/10`（與 R84 逐字相同＝該輪零動屬實） |
| 2 | `.venv/bin/python tools/probe/misstep_attribution.py --source all --control --json` | rc=0；`n=1243`，`{OTHER:636, CLAIM-FIRST:197, LOCKBLIND:181, BADPIPE:120, CARRIER:109}` |
| 3 | `.venv/bin/python tools/probe/xplat_hazard_census.py`（**本包新建**） | rc=0；活躍面 tracked `.py`＝**735 支**、解析失敗 0；`exe-argv=24`／`chmod-exec=17`／`shell-true=13`／`win-codec=1` |
| 4 | `.venv/bin/python tools/probe/misstep_attribution.py --help` | rc=0；旗標只有 `--source/--project-dir/--jsonl/--show/--control/--selftest/--json`（**無**輪次／日期過濾） |
| 5 | AST 對帳：`test_platform_neutral_paths.py` 檔級 `scan_*` 定義數 vs `_injection_criteria()` 接線數 | **11 定義 / 8 接線**；未接線＝`scan_git_path_enumeration`／`scan_naive_timestamp_persist`／`scan_ps_platform_sites` |
| 6 | `re.compile(r'^[\w\s\-./=:!"\']+$')` 逐句實跑（`_SAFE_COND_PATTERN` 的逐字複本） | `python -c "print(1)"` → **False**；`test -f foo` → **True**；`grep -q x file` → True；`pgrep -f x` → True；`pmset -g custom` → True；`rm -rf /` → **True** |
| 7 | `grep -nE "subprocess\.(run\|Popen\|call\|check_output)" AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/*.py` | **3 筆**，argv[0] 皆為 `"git"`（`closure_evidence_verify.py:68`／`post_commit_drift.py:54,72`） |
| 8 | `.venv/bin/python -c "…lib.sdd_latest.resolve_latest_name(Path('AISDLC_SDD'))"` | `AISDLC_SDD_v0.30`（LATEST 現查，本檔他處不再複寫版號） |

**新建探針**：`tools/probe/xplat_hazard_census.py`——`--rule`／`--detail`／`--jsonl`。
它**只量不判**（永遠 exit 0，不接任何閘門 rc）。存在理由逐字寫在檔頭：R83 為毀滅性 git
判準做的假紅普查沒有留下產物，導致 R84 必須重建（`DEF-200-046`）；本檔就是不讓 R86 重蹈。

---

## §A 目標(1) — 相容性缺陷：鐵律三大表「無機械物」兩格的深挖

### A-1 `shell=True` 格：**唯一存在的輸入面正規化與可攜性目標反相關** 🔴 blocking

**現查**：
```bash
grep -n "_SAFE_COND_PATTERN" AutoClaude/autoclaude/execution/mutation_applier/_conditional.py
grep -nE "SAFE|_PATTERN|re\.compile|os\.name|sys\.platform" AutoClaude/autoclaude/execution/evaluator.py
```

**本回合實測**（取證 #6，逐句真跑）：

| 送進 `_SAFE_COND_PATTERN` 的指令 | 判決 | 該 docstring 怎麼說 |
|---|---|---|
| `python -c "print(1)"` | **False（擋掉）** | 它是 docstring **逐字建議的可攜寫法** |
| `test -f foo` | True（放行） | 它是 docstring **逐字點名要避免的 POSIX 專屬語法** |
| `grep -q x file` | True（放行） | 同上（docstring 點名 `grep`） |
| `pgrep -f x` / `pmset -g custom` | True（放行） | POSIX-only，Windows 上必定「找不到指令」 |
| `rm -rf /` | True（放行） | — |

⇒ 這道 repo 內**唯一**與 `shell=True` 可攜性沾邊的輸入面過濾器，**擋掉它自己推薦的正解、
放行它自己點名的每一個反例**。成因不是寫錯：`_SAFE_COND_PATTERN` 是 **Gap-046 的資安過濾器**
（擋 shell metacharacter），可攜性只是它擋掉 `&&`／`||` 的**副作用**；而該檔 docstring 第 34 行
逐字把這個副作用寫成「`&&`/`||` 則已被上方 Gap-046 `_SAFE_COND_PATTERN` 擋下」，
讀起來像是可攜性有人在守。

**為什麼現有鎖攔不到**：`AutoClaude/tests/test_evaluator_kill_tree.py` 守的是逾時 kill 行程樹
（根 `CLAUDE.md` 該格已誠實記載「同一個關鍵字、不同的主題」）。可攜性這一軸**零判準**，
而失效表徵是 `logger.warning(...)` 後 `return`／`cond_exit=1` ⇒ **靜默走 false 分支**，rc=0。

**修法草案（R85-D）**：
1. **先把兩個站點對齊**——`Evaluator.run`（`evaluator.py:51`）今天**連 `_SAFE_COND_PATTERN`
   都沒有**（取證 #6 的 grep 全檔零命中）。兩個站點跑同一類輸入、docstring 講同一段話、
   只有一個有過濾器。
2. **可攜性契約與資安過濾器分開**（不要把可攜性再掛成副作用）：新增一支
   `portability_verdict(command) -> list[str]`，判「argv[0] 是不是單平台專屬外部執行檔」
   （詞彙表複用 A-3 的 `_WIN_ONLY_EXE`／`_POSIX_ONLY_EXE`），命中時**不擋、只在
   `EvalResult.output` 與 log 出聲**（playbook 是使用者輸入，擋掉會讓引擎不能用——
   repo 已判過「擋到讓人無法工作的守衛會被整個關掉」）。
3. **靜態面只守分母**：新增判準「`shell=True` 站點只准出現在登記清單內」（今天 13 筆、
   production 只有 2 筆，見 A-2），新站點必須回來登記。

**持有面（鐵律七）**：
- 常數／詞彙表：`AutoClaude/autoclaude/execution/` 新檔（或 `tools/lib/` 若要與 A-3 共用）
- 消費端：`AutoClaude/autoclaude/execution/evaluator.py`＋`.../mutation_applier/_conditional.py`（**兩支**）
- 史料／鎖：`AutoClaude/tests/` 新測 ＋ 根 `CLAUDE.md` 該列機械物欄
⇒ **三者跨 AutoClaude 生產碼與根層護欄兩個面**，不可切給不同並行包。建議整包一人做。

**嚴重度**：blocking（它讓一句「已有輸入面正規化」的印象在帳面上成立，而實際方向相反）。
**承接**：R85 收尾或 R86 單包。

---

### A-2 `shell=True` 的執行期契約**有明確落點**（該格自陳「量不到真實危害面」需訂正）

**現查**：`.venv/bin/python tools/probe/xplat_hazard_census.py --rule shell-true --detail`

**本回合實測**：13 筆，分流 `{'non-literal': 13}`、`literal: 0`。逐筆座標：

| 面 | 站點 |
|---|---|
| **production（2 筆）** | `AutoClaude/autoclaude/execution/evaluator.py:51`；`AutoClaude/autoclaude/execution/mutation_applier/_conditional.py:49` |
| 測試（10 筆） | `AutoClaude/tests/test_gap021_028.py`×6、`AutoClaude/tests/test_playbook_runner.py`×3、`AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py`×1 |
| SDD scripts（1 筆） | `AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py:100` |

**這對該格的宣稱意味著什麼**：該格寫「存量掃描**結構上量不到**真實危害面，真正被送進殼的
指令來自 playbook＝使用者輸入，根本不在 repo 裡」。**前半為真、後半推出的結論過寬**——
指令內容確實不在 repo 裡，但**入口**在，而且**只有 2 個**。執行期契約要掛在哪裡這個問題，
今天有一個精確答案，不是開放式的。建議把該格的機械物欄由「無機械物」改成
「無機械物；入口面已可列舉（現查 `xplat_hazard_census.py --rule shell-true`）」——
**分母不動、分子不動**（不觸發棘輪），但下一輪不必再從零找落點。

**嚴重度**：major。**承接**：R85（改一句話）／R86（實作契約）。

---

### A-3 新危害類：**單平台專屬「外部執行檔」的 argv[0] 字面** 🔴 major（本輪新登記）

**現查**：`.venv/bin/python tools/probe/xplat_hazard_census.py --rule exe-argv --detail`

**本回合實測**：**24 筆**（`win-only` 22／`posix-only` 2），活躍面 735 支 `.py`。
production 面 5 筆：`AutoClaude/autoclaude/utils/platform_caps.py:80`（`taskkill`）／
`AutoClaude/autoclaude/utils/notifier.py:143`（`osascript`）／`tools/check_scheduled_task_drift.py:146`
（`powershell.exe`）／`tools/dev_start.py:1600`（`launchctl`）／`tools/session_resume_planner.py:408`
（`powershell.exe`）。逐筆查守衛（本回合實跑，取前 18 行找守衛關鍵字）：**5 筆全部有守衛**
——4 筆是站點級（`if is_windows():`／`if os.name != "nt":`／darwin docstring），
1 筆（`check_scheduled_task_drift.py`）是**檔級**（檔頭逐字「非 Windows → SKIP，rc=0」）。

**為什麼現有鎖攔不到**：`tools/tests/test_platform_neutral_paths.py::TestForeignPlatformApiIsGuarded`
的 `_FOREIGN_ATTR_TABLE` 收的是 **Python 符號**（`os.*`／`signal.*`／`ctypes.*`／`subprocess.CREATE_*`）。
「送給 OS 的外部程式名」**不是 Python 符號**——AST 看到的只是一個 `ast.Constant` 字串 ⇒
那一族從來不在分母裡。這與 R81 訂正的 `ctypes.*` 失明**逐字同型**（owner 判準寫死字串 ⇒ 整片失明）。

**修法草案（R85-A）**：把 `TestForeignPlatformApiIsGuarded` 的 owner 概念由「模組屬性」擴成
「**模組屬性 ∪ subprocess argv[0] 字面**」，**沿用它既有的五種罩法**（不新增豁免語法）。
檔級守衛那一種必須被認得，否則 `check_scheduled_task_drift.py` 會是假紅。

**假紅普查（草案的必經步驟，母體與載具已具名）**：母體＝`xplat_hazard_census.py --rule exe-argv`
的 24 筆（活躍面 tracked `.py`，凍結面已排除）；判準上線前逐筆比對「是否落在五種罩法內」，
今天的期望是 **24/24 全部落在罩法內 ⇒ 假紅 0、存量 0**，也就是**純寫入面判準**
（與 `Get-Command` 解析那一格同形：存量 0 時缺的一直是「下一個人寫出來時當場紅」的門）。
🔴 我**只實測了 production 那 5 筆的守衛**；另外 19 筆（測試面）本包未逐筆查 ⇒ **未驗證**。

**持有面**：常數（詞彙表）＋消費端（判準）＋史料（棘輪）**三者同住**
`tools/tests/test_platform_neutral_paths.py`；根 `CLAUDE.md` 該列一行。⇒ **可派給單一並行包**。
🔴 唯一跨檔處：若要與 A-1 共用詞彙表，就得抽到 `tools/lib/` ⇒ 那一刻它就跨面了。
**建議先在測試檔內落地，A-1 用時再抽**（避免一開始就跨面）。

**嚴重度**：major。**承接**：R85（P2 持有面）。

---

### A-4 新危害類：**顯式指名 Windows 專屬 codepage** 🔴 minor（存量 0 ⇒ 零遷移成本）

**現查**：`.venv/bin/python tools/probe/xplat_hazard_census.py --rule win-codec --detail`
**本回合實測**：**1 筆**——`AutoClaude/tests/tools/test_ab_compare_backends.py:704`，
原行逐字 `fake = io.TextIOWrapper(io.BytesIO(), encoding="cp950")  # 模擬 Windows console`
⇒ **刻意的模擬，真陽性 0、假陽性 1/1**。

**為什麼現有鎖攔不到**：`TestTextIoDeclaresEncoding`／`scan_missing_encoding` 判的是
「**有沒有寫** `encoding=`」。`encoding="cp950"` 完全滿足它。兩者是**相反方向**的失效，
同一道判準結構上接不住。且 POSIX 的 Python **認得** `cp950` 這個 codec ⇒ 不拋例外、
只是讀出亂碼 ⇒ 失效表徵比崩潰更難看見。

**修法草案（R85-B）**：在 `scan_missing_encoding` 旁加一條同掃描面的判準，
命中 `_WIN_ONLY_CODEC`（`cp950/cp1252/cp936/cp932/mbcs/big5/gbk/cp437`）即紅，
行尾豁免 `# codec-ok: <WHY>`；那 1 筆模擬即以豁免收（理由是「刻意模擬 Windows console」）。
**持有面**：全部同住 `tools/tests/test_platform_neutral_paths.py`。⇒ 可派單包，成本極低。
**嚴重度**：minor。**承接**：R85。

---

### A-5 `os.chmod` 執行位元：**建議不建靜態掃描**（誠實劃界，避免下一輪蓋一支必被關掉的鎖）

**現查**：`.venv/bin/python tools/probe/xplat_hazard_census.py --rule chmod-exec --detail`
**本回合實測**：**17 筆，全部在測試 scaffolding**（`tools/tests/test_pre_commit_dispatcher_sigpipe.py`×5、
`tools/tests/test_pre_push_dispatcher.py`×5、`tools/tests/test_dev_start.py`×4、
`tools/tests/test_ntfs_trailing_space_device_name.py`×1、`AISDLC_SDD/scripts/tests/…`×1、
另 1 筆 `0o700`）。全部是「在 tmpdir 造一支假 hook／假執行檔」。

**判讀**：Windows 的 `os.chmod` 只認 read-only 旗標、其餘 bit 靜默丟棄（rc=0）——但這 17 筆的
**消費者是同一支測試自己**，Windows 上這些測試另有 skip 或不依賴 exec bit。
⇒ 一支天真的 `chmod-exec` 靜態掃描今天會產出 **17 筆要逐一辯護的假紅**，而 repo 已判過
「那種鎖活不過一輪」（同 `sorted()` 那格 148 筆假紅的判例）。

**⇒ 本格的正解仍是根 `CLAUDE.md` 「exec bit／git 索引檔案模式」列自己已寫的那半句**：
「**安裝產物**那一半仍無人守」。本包**不提議**建 `chmod-exec` 掃描，只把「為什麼不建」
連同 17 筆座標登記下來，避免 R86 重新發明並被假紅打回。
**嚴重度**：minor（登記，不動分子分母）。**承接**：不指定。

---

### A-6 「副檔名判斷」格的**寫入面判準形狀**（M5 的 `b4-exe-suffix`）

該格自陳「production 存量已近乎清空 ⇒ 缺的是**寫入面**判準，不是存量掃描——今天蓋一支存量
掃描會回 0 命中而給出假的安心」。本包同意該診斷，並補上它缺的那一半：**寫入面判準長什麼樣**。

M5 語料 `b4-exe-suffix` 逐字是 `def f(name):\n    return name + ".exe"\n`，今天 `hits=[]`。
問題在於「字串加 `.exe`」在 Windows 語境是**正確寫法**，判它就是判正解。
⇒ 寫入面判準的正確形狀**不是判字面**，而是判「**這個副檔名有沒有被平台守衛罩住**」——
與 A-3 完全同一個判準骨架（五種罩法 × 單平台專屬詞彙），只是詞彙由「執行檔名」換成
「單平台專屬副檔名」（`.exe`／`.bat`／`.cmd`／`.ps1`／`.msi` vs POSIX 側的無副檔名 shebang 檔）。

⇒ **建議與 A-3 合併為同一包**（同骨架、同持有面、同一次假紅普查）；分開做會得到兩份
幾乎相同的罩法實作，那正是 R73 `Find-GitBash` 同型的「同一份知識住兩個家」。
**嚴重度**：major。**承接**：R85（與 A-3 同包）。

---

## §B 目標(2) — M5 注入矩陣：11 題逐題分析

**現查**：`.venv/bin/python -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix`
**本回合實測**：`OK`，`[Xplat injection matrix] Win2mac=6/12 mac2Win=5/10`
（與 R84 逐字相同 ⇒ 交棒書「該輪零動」屬實，本包複驗通過）。

### B-0 🔴 先講一個比 11 題更重要的：**M5 的判準集自己漏了三分之一** — blocking

**現查**（AST 對帳，取證 #5）：
```bash
.venv/bin/python -c "
import ast,pathlib,sys; sys.path.insert(0,'tools/tests')
import test_platform_neutral_paths as T
t=ast.parse(pathlib.Path('tools/tests/test_platform_neutral_paths.py').read_text(encoding='utf-8'))
d=sorted(n.name for n in t.body if isinstance(n,ast.FunctionDef) and n.name.startswith('scan_'))
w=sorted(f.__name__ for f in T._injection_criteria().values())
print(len(d),len(w)); print('NOT wired:',sorted(set(d)-set(w)))"
```
**本回合輸出**：`11 8` ／ `NOT wired: ['scan_git_path_enumeration', 'scan_naive_timestamp_persist', 'scan_ps_platform_sites']`

`_injection_criteria()` 的 docstring 逐字寫「**本檔全部判準的統一入口**——語料逐題過**每一道**，
不是只過一道」，而同檔第 259~260 行另一段更逐字寫「注入語料矩陣需要對**每一道**判準問同一個
問題，**缺一個入口就等於那一格永遠量不到**」。**兩處宣稱同時為假**：實際是 8/11。
三支缺席者全部是 **R80／R81 之後才落地的判準** ⇒ M5 的分母被**凍結在 R79 那一代的判準集**，
**此後每補一道判準，M5 就更失真一分，而不會有任何東西轉紅**。

**現有鎖為何攔不到**：`TestR75IronLawMechanismSubstance` 比的是「大表指名的檔存不存在／
關鍵詞有沒有出現」；`TestXplatInjectionMatrix` 的三支測試比的是「每題判決有沒有漂」與
「攔截數等不等於 floors」。**沒有任何一支比「判準集完不完整」**——那是一個
`len(defined) == len(wired)` 的問題，全 repo 零判準（`grep -rn "_injection_criteria"` 本回合
實測**只有 2 筆命中**：定義與唯一消費端，各一）。

🔴 **今天的數字沒有錯**（我實測把三支補進去，**11 題的判決一筆都沒變**：`changed=[]`）
——所以這是「假綠」而不是「假數字」：**它今天是對的，而讓它明天出錯的機制已經裝好了。**

**修法草案（R85-M5-0）**：在 `TestXplatInjectionMatrix` 加一條
`test_the_criteria_entry_point_really_holds_every_scanner_in_this_file`：
以 AST 取本檔所有 `scan_*` 頂層函式，與 `_injection_criteria()` 的值集合**取相等**；
刻意排除的必須進一張具名 `_CRITERIA_OUT_OF_SCOPE = {name: WHY}`（例如 `scan_ps_platform_sites`
的輸入是 `.ps1` 而語料是 `.py` ⇒ 合法排除，但**必須具名寫下來**）。
**持有面**：常數（`_CRITERIA_OUT_OF_SCOPE`）／消費端（`_injection_criteria`）／史料（floors、
`_XPLAT_INJECTION_CORPUS` 的 expected 欄）**三者同住** `tools/tests/test_platform_neutral_paths.py`
⇒ **可派給單一並行包**。
**嚴重度**：**blocking**。**承接**：R85（P2 持有面）。

### B-1 11 題未攔到，逐題

> 現查逐題：`.venv/bin/python -c "import sys;sys.path.insert(0,'tools/tests');import test_platform_neutral_paths as T;[print(c,T.injection_hits(s)) for c,d,s,e in T._XPLAT_INJECTION_CORPUS if not T.injection_hits(s)]"`
> 本回合輸出＝下表第 1 欄那 11 題，`hits=[]` 全部。

| 題 | 方向 | 「本來應該」是誰 | 它為什麼失明 | 草案 |
|---|---|---|---|---|
| `b2-backslash-join` | Win→mac | 大表第一列「路徑分隔符」→`test_platform_neutral_paths.py` | 該列**沒有指名符號**，實際在守的是 `scan_drive_literal`＝**磁碟機代號字面**（`D:/…`），對「裸反斜線串接」零判準。POSIX 上反斜線是合法檔名字元 ⇒ 不拋例外、只是 `FileNotFoundError` | 見 **B-2**（大表該列的訂正）＋新判準：`BinOp` 串接中出現 `"\\"` 字面且結果餵給路徑 API |
| `a1-posix-sep-concat` | mac→Win | 同上 | 同上 | 🔴 **建議不建**：`"/"` 在 Windows 的 Win32 API 上可用 ⇒ 真陽性率低，判它會是大量假紅。**建議把此題從語料移到「已知不判」註記**（但語料題數只准上升 ⇒ 需同時改 `assertGreaterEqual(…, 22)` 的持有面，見下方持有面欄） |
| `b4-exe-suffix` | Win→mac | 大表「副檔名判斷」（自陳無機械物） | 判字面＝判正解 | **A-6**（與 A-3 同骨架） |
| `b8-schtasks` | Win→mac | `TestForeignPlatformApiIsGuarded` | owner 是 **Python 符號**，外部程式名不是符號 | **A-3** |
| `b11-powershell-shell` | Win→mac | 同上 | 同上 | **A-3** |
| `b5-cp950-encoding` | Win→mac | `TestTextIoDeclaresEncoding`／`scan_missing_encoding` | 它判「**有沒有寫** `encoding=`」，寫了就過 ⇒ 相反方向的失效 | **A-4** |
| `a5-chmod-exec` | mac→Win | `TestForeignPlatformApiIsGuarded` | `os.chmod` **兩平台都有** ⇒ 不在「對面平台會 AttributeError」那張表裡；危害是**靜默 no-op** 不是崩潰 | 🔴 **A-5：建議不建**（17 筆假紅） |
| `b10-case-insensitive` | Win→mac | 大表「大小寫敏感度」→`tools/check_ntfs_paths.py` | 該判準守的是 **tracked 路徑的大小寫碰撞**，對「程式邏輯用 `.lower()` 比對」零關係 | 🔴 **建議不建**：`a.lower()==b.lower()` 在絕大多數情境是正解，假紅率極高。同 A-5 的理由登記為「刻意不判」 |
| `a8-shebang-exec` | mac→Win | 大表「`#!` shebang ＋ 非 LF 行尾」→`TestShebangImpliesLfLineEndings` | 那一列判的是**被執行檔自己的行尾**；本題是**呼叫端**直接把 `./x.sh` 當 argv[0]（Windows 無 shebang 機制 ⇒ `[WinError 193]`） | 併入 **A-3** 的骨架：argv[0] 字面以 `.sh` 結尾＝POSIX-only 執行形態 |
| `a2-tmp-hardcode` | mac→Win | `scan_intree_tmpdir`／`scan_posix_abs_asserts` | 本回合實測兩者對該語料皆回 `([], [])`。`scan_intree_tmpdir` 守的是「**樹內**造暫存目錄」；`scan_posix_abs_asserts` 守的是**斷言**裡的 POSIX 絕對路徑 ⇒ 「模組級常數硬編 `/tmp/…`」兩邊都不在射程 | 擴 `scan_posix_abs_asserts` 的射程：由「assert 的比較對象」擴到「模組級字串常數」，行尾豁免沿用既有 `# posix-abs-ok:` |
| `a9-lf-only-write` | mac→Win | 大表「行尾」三列 | 那三列全部判**磁碟上的檔**（工作樹／blob／`.gitattributes`）；本題是**寫入 API 沒指定 `newline=`** ⇒ 在 Windows 上 `write_text` 會把 `\n` 轉成 `\r\n`（與意圖相反的方向） | 與 `TestTextIoDeclaresEncoding` 同骨架：判 `write_text`／`open(..., "w")` 是否宣告 `newline=`。**存量待普查**（本包未量，見 §E） |

**共同持有面（鐵律七）**：上表**全部**草案的常數／判準／史料都住
`tools/tests/test_platform_neutral_paths.py` **一支檔**，加根 `CLAUDE.md` 大表一行。
⇒ **可以整批派給同一個並行包**；但**不得**與「動大表列數」的包分開（棘輪讀的是那張表本身）。
🔴 例外：`a1`／`b10` 那兩題若要「移出語料」，會同時動 `_XPLAT_INJECTION_CORPUS`、
`assertGreaterEqual(…, 22)` 與 `floors` 三處 ⇒ 三者雖同檔，但**與 B-0 的新判準相互干涉**
（改語料會改 `live_interception()`）⇒ **B-0 與 B-1 必須同一包、同一次收斂**。

### B-2 🔴 大表第一列「路徑分隔符」宣稱有機械物，而同一支檔內的 M5 證明它接不住 — major

**這是本輪最典型的「假綠」形態**：
- 大表第 1 列：`路徑分隔符 | tools/tests/test_platform_neutral_paths.py | 根層 unittest 閘門`（**只指名檔、不指名符號**）。
- 同一支檔內的 `TestXplatInjectionMatrix`：`b2-backslash-join`（裸反斜線串接）與
  `a1-posix-sep-concat`（裸 `/` 串接）**都釘著 `expected=False`＝攔不到**。

⇒ 兩道鎖住在同一支檔、對同一件事給出相反的答案，而**沒有任何東西轉紅**。
**為什麼 `TestR75IronLawMechanismSubstance` 接不住**：它的實質判準是**關鍵詞佐證**
（該檔內要出現該列主題的關鍵詞），而該檔當然滿滿都是「分隔符」——該測試的 docstring
自己已誠實劃界：「關鍵詞佐證是**必要條件不是充分條件**——它抓得到『完全沒碰那個主題』，
抓不到『碰了但判準很弱』」。本例正是被那句話點名的情形，只是此前沒有人把它量出來。

**修法草案（R85-M5-2）**：讓大表與 M5 語料**互相對帳**——新增判準：
大表任一列若宣稱有機械物，而 M5 語料中**同主題**的題目 `expected=False`，即紅，
除非該列的機械物欄明寫射程限縮（照 `行尾（.sh／.bash 方向）` 那一列已有的體例）。
最小可行版：先把第 1 列的機械物欄由整支檔改成 **`::scan_drive_literal`（射程＝磁碟機代號字面；
裸分隔符串接見 M5 `b2`／`a1`，未覆蓋）** ——這是**低報分子的相反面**：
過報分子，而根 `CLAUDE.md` 已判過「低報與過報一樣貴」。
**持有面**：根 `CLAUDE.md` 一行 ＋ `tools/tests/test_doc_loc_baseline_freshness_r60.py`
（棘輪與實質判準）＋ `tools/tests/test_platform_neutral_paths.py`（語料）⇒ **跨三檔**。
🔴 依鐵律七：**不得派給並行包**，須由收尾單人窗口做，或只做「改一行大表欄位」那半。
**嚴重度**：major。**承接**：R85 收尾（改欄位）／R86（對帳判準）。

---

## §C 目標(3) — Windows 低級錯誤歸因重跑（含 R84 逐字稿）

**現查**：`.venv/bin/python tools/probe/misstep_attribution.py --source all --control --json`
**本回合實測**（rc=0）：

| 桶 | 全母體 n=1243 | 帳本 1207 | 逐字稿 36 | control lift（只算逐字稿面） |
|---|---|---|---|---|
| OTHER | 636 | 613 | 23 | **−27.8 pp** |
| **CLAIM-FIRST**（宣稱先於查證） | **197** | 191 | **6** | **+11.1 pp（最大）** |
| LOCKBLIND（鎖失明／恆綠） | 181 | 178 | 3 | +5.6 pp |
| BADPIPE（取數管道給假數字） | 120 | 117 | 3 | +8.3 pp |
| CARRIER（選錯載具） | 109 | 108 | 1 | +2.8 pp |

**母體含 R84 逐字稿＝是**：36 筆逐字稿命中的來源分佈本回合實測，
`83021fb3-…jsonl` **13 筆**、`1d6ba528-…jsonl` **3 筆**（兩支即 R84 的 session，mtime 08-12 00:50／04:58）
⇒ **R84 貢獻 16/36**，是單輪最大貢獻者。

**與 R77／R79 的量級對照**（🔴 **百分比是量測值不是常數，三次的母體與單位都不同，只可量級對照、
不可逐點比較**）：

| 輪 | 母體 | 最大非-OTHER 桶 | 第二 |
|---|---|---|---|
| R77 | R71~R76 自陳失誤列（數十筆，**無可重跑產物**） | 鎖無鑑別力／射程失明（約四成） | 選錯載具（約五分之一） |
| R79 | 帳本＋逐字稿（首次有腳本） | **宣稱先於查證** | 鎖失明 |
| **R85（本包）** | **n=1243**（帳本 1207＋逐字稿 36） | **宣稱先於查證（197）** | 鎖失明（181） |

⇒ **R79 的排序在 R85 重跑後成立**，而且這次多一個獨立佐證：`--control` 的 lift 也把
CLAIM-FIRST 排第一（+11.1 pp），亦即「這個 repo 平常就常講這件事」不足以解釋它的規模。
**CARRIER 連兩次都是最小桶**——鐵律一＋PreToolUse 阻斷的效果在兩種取數下都成立。

### C-1 🔴 最大桶 CLAIM-FIRST **零機械物**（連兩次量測居首）— blocking

**現查**（現查註冊面，**不寫死支數**）：
```bash
.venv/bin/python -c "
import json;d=json.load(open('.claude/settings.json',encoding='utf-8'))
[print(ev, repr(e.get('matcher','')), h) for ev,es in d.get('hooks',{}).items() for e in es for h in e.get('hooks',[])]"
```
**本回合實測**（依腳本名去重後的事件×matcher）：

| hook 腳本 | 註冊的 (事件, matcher) | 它守的桶 |
|---|---|---|
| `block_bash_on_windows` | `(PreToolUse, Bash)` | CARRIER |
| `lint_powershell_command` | `(PreToolUse, PowerShell)` | CARRIER＋BADPIPE（**僅 PowerShell 側**） |
| `block_destructive_git` | `(PreToolUse, Bash\|PowerShell)` | 毀滅性 git＋waitform |
| `context_budget_guard` | `(PostToolUse, Read\|Task\|Grep\|Glob\|WebFetch\|WebSearch\|Bash\|PowerShell)`、`(PreToolUse, Task\|WebFetch\|WebSearch\|Agent\|Workflow)`、`(SessionStart, '')` | 額度／context |
| `sdd_hook_router` | `(PostToolUse, Write\|Edit\|Read\|Bash\|NotebookEdit)`、`(PreToolUse, …\|Task)`、`(SessionStart, '')` | SDD |
| `check_ps1_encoding`／`check_sh_eol` | `(PostToolUse, Write\|Edit)` | 行尾／編碼 |

🔴 **關鍵觀察（機械對帳，不是判讀）**：**每一個 matcher 都是工具名**，
而且根層**一個 `Stop` 事件都沒有註冊**。「宣稱」不是工具呼叫、不帶 `tool_input`
⇒ **沒有任何一支的射程碰得到它**。根 `CLAUDE.md` 鐵律四對這一桶的處置逐字是「對策不是『更小心』，
而是套用既有紀律 `[[no-fabricated-tool-output]]`」——**那是散文，對當下的模型零攔阻力**，
而這正是鐵律一自己記載過的失效（「寫完本節的同一個回合仍用了 Bash 工具」）。

**為什麼它結構上難有機械物**（誠實劃界，不假裝有解）：宣稱住在**助理輸出文字**裡，
既不匹配任何 PreToolUse matcher，也永不變成 repo 內的檔案——正是根 `CLAUDE.md`
R77／R79 那段歸因的**第 ② 層**。⇒ 唯一結構上成立的觀測點是 **Stop hook 或事後逐字稿稽核**
（`tools/probe/audit_session.py` 已是後者的載體，但它**不接任何閘門 rc**）。

**修法草案（R85-C1，刻意保守）**：不提議「攔下宣稱」（做不到、且會誤傷）。提議
**把事後量測接上一個會到期的時點**——照 R84 §6 第 1 條的判例（「凡『已知缺口』必須有一個
**會到期的時點**，不能只有一段散文」）：把 CLAIM-FIRST 的**逐輪逐字稿命中數**登記成棘輪
（`misstep_attribution --source transcript` 的桶計數），連續上升即紅。
**持有面**：探針（`tools/probe/misstep_attribution.py`）／史料（新棘輪常數）／消費端（新測試）
⇒ **跨兩檔**（probe ＋ tests），可派單包，但**不得**與改分群關鍵詞表的包分開
（改關鍵詞表＝重新定義量測，會讓歷史數字全部失效）。
**嚴重度**：blocking（最大桶、連兩輪、零機械物）。**承接**：R85 決策／R86 落地。

### C-2 歸因探針對「本輪」幾乎零靈敏度 — major

**本回合實測**：母體 1243 筆中 **1207 筆（97.1%）是缺陷帳本列**。帳本是**跨約百輪的累積檔且
只增不減** ⇒ 頭條百分比幾乎完全由歷史決定，**本輪做了什麼對它的影響小於一個百分點**。
per-round 的訊號只活在 36 筆逐字稿裡，而 `--help` 實測（取證 #4）**沒有任何輪次／日期過濾旗標**。

⇒ 「每輪重跑一次分群」這條要求今天在**字面上做得到、在語意上做不到**：重跑會得到一個
幾乎不動的數字，而那個不動**不代表沒有變化**。這與 R79 對 R77 下過的判決同型
（「結構上做不到」），只是這次卡在**取樣**而不是產物。

**修法草案**：加 `--since <ISO日期>`／`--round <R84>`（逐字稿以 mtime 或內容輪號切、
帳本以列的日期欄切），並讓 `--json` 同時印「全母體」與「本輪」兩組。
**持有面**：單檔 `tools/probe/misstep_attribution.py`。⇒ 可派單包，成本低。
**嚴重度**：major。**承接**：R85。

---

## §D 目標(5) — 挖深清債：「看起來像修好了、其實沒有」

> 本節三筆，各自對應一種形態。B-0（判準集 8/11）與 B-2（大表第一列）也屬本類，不重複。

### D-1 🔴 SDD LATEST 的 hook 有 3 支 `git` spawn，而**沒有任何 console-spawn 判準看得到它** — major（Windows 靜態推論）

**現查**：
```bash
.venv/bin/python -c "import sys;sys.path.insert(0,'tools');from lib.sdd_latest import resolve_latest_name;from pathlib import Path;print(resolve_latest_name(Path('AISDLC_SDD')))"
grep -nE "subprocess\.(run|Popen|call|check_output)" AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/*.py
```
**本回合實測**：LATEST＝`AISDLC_SDD_v0.30`；該目錄下 **3 筆** spawn，argv[0] **皆為 `"git"`**：
`closure_evidence_verify.py:68`、`post_commit_drift.py:54`、`post_commit_drift.py:72`。

**為什麼現有鎖攔不到（指名到符號）**：這一族的兩支判準的掃描面是**寫死的兩個目錄**——
`tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest`（實測第 2202 行
`for hook in sorted((_REPO_ROOT / ".claude" / "hooks").glob("*.py")):`）與
`tools/tests/test_check_hooks_liveness.py::TestAutoClaudeHookSpawnsAreConsoleFree`
（實測第 2949 行 `_AC_HOOK_DIR = _REPO_ROOT / "AutoClaude" / "tools" / "hooks"`）。
**`AISDLC_SDD/<LATEST>/.claude/hooks/` 是第三個掃描面，兩支都看不到。**

**為什麼這一筆特別貴**：R84 才剛把 SDD LATEST 的 `settings.json` **轉成 exec form**
（載具＝`pythonw.exe`，GUI 子系統、無 console）。根 `CLAUDE.md` 該列逐字寫著：
「載具（`pythonw.exe`）去 spawn `git.exe` 時 **OS 會替 child 另配一個新 console**
⇒ **形態修好之後彈窗仍在**」。⇒ R84 的轉換把 SDD LATEST session 的彈窗從
「bash.exe 那一類」換成「git.exe 那一類」，**而接手的那一類在該目錄上零判準**。
🔴 **靜態推論、未在真機驗證**（本輪在 macOS；macOS 沒有 console 視窗這個概念）。

**修法草案**：把掃描面由「兩個寫死目錄」改成「**現查**：根 `.claude/hooks/` ∪
`AutoClaude/tools/hooks/` ∪ `AISDLC_SDD/<LATEST>/.claude/hooks/`（LATEST 走 SSOT
`tools/lib/sdd_latest.py`，**鍵不寫版號**，體例照 R84 的 `SHELL_FORM_CENSUS`）」；
三筆 offender 的正解已有唯一的家＝`tools/lib/win_spawn.py` 的 `NO_WINDOW`／`quiet_python`
（本回合實測根層 hook 正是這樣做的：`.claude/hooks/sdd_hook_router.py:237` 帶
`creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)`；`context_budget_guard.py:305`
`from win_spawn import NO_WINDOW, quiet_python`）。
**持有面**：判準常數＋消費端同住 `tools/tests/test_context_budget_guard.py`；
**offender 修復落在 `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/`（LATEST＝可原地改）**
⇒ **兩個面**：擴掃描面（護欄層）與修 3 支檔（框架層）。可同包，但任務書要同時列出兩面，
否則「擴了掃描面」那一包會當場留下 3 筆紅給別人。
**嚴重度**：major。**承接**：R85。

### D-2 同一份知識三個家、零機械綁定：`shell=True` 的 `cmd.exe` vs `/bin/sh` 分歧 — major

**現查**：
```bash
sed -n '36,44p' AutoClaude/autoclaude/execution/evaluator.py
sed -n '30,35p' AutoClaude/autoclaude/execution/mutation_applier/_conditional.py
grep -n 'shell=True.*原生殼\|cmd.exe' CLAUDE.md
```
**本回合實測**：兩支生產碼的 docstring **各自複寫了一段幾乎逐字相同的說明**
（「Windows 為 cmd.exe，POSIX 為 /bin/sh，而非固定的 bash…避免 POSIX 專屬語法
（test -f、grep 等 shell builtin/GNU 工具）」），根 `CLAUDE.md` 鐵律三大表另有第三份。
**三處零機械綁定** ⇒ 改任一處另兩處不會轉紅。而 A-1 已實測：兩份 docstring 給的建議
（`python -c "…"`）**被同檔的過濾器擋掉**——三個家裡至少有一個已經在講假話，
而**沒有任何東西看得見**。這與 R73 `Find-GitBash`、R84 `waitform_hits`（三個家三種內容）
**逐字同型**，是本 repo 第三次踩同一個坑。

**修法草案**：收斂成一個家（依 repo 既有體例：實作與說明同住一支檔），
兩支生產碼 docstring 改成指向該家＋一行「現查」；根 `CLAUDE.md` 該列同樣只指路。
**持有面**：`AutoClaude/autoclaude/execution/` 兩支 ＋ 根 `CLAUDE.md` ＋ 新鎖
⇒ **跨子專案生產碼與根層護欄** ⇒ 依鐵律七**不得派給並行包**。
**嚴重度**：major。**承接**：R86 單人窗口（與 A-1 同包）。

### D-3 探針的假紅普查產物：本輪已止血，但**只止住 R85 這一輪**

R84 訂正 `DEF-200-046` 時把「數字視為量測值、現跑 `shell_command_corpus.py`」寫進根
`CLAUDE.md`，**那是針對 git 判準的母體**。本包的四條草案判準（A-1/A-3/A-4/A-6）需要的是
**活躍面 `.py` 的 AST 母體**，repo 內先前**沒有這個載具** ⇒ 本包新建
`tools/probe/xplat_hazard_census.py` 補上。
🔴 **誠實劃界**：它今天**不接任何鎖**——沒有任何東西會因為它的輸出改變而轉紅。
它是「讓下一輪不必重建基線」的產物，不是護欄。**若 R85 收尾決定採納 A-3／A-4，
應同時把該探針的四條規則搬進判準檔並讓探針只保留 `--detail` 取證用途**，
否則它就會變成本 repo 判過的「同一份知識住兩個家」的下一個實例。
**嚴重度**：minor（自陳）。**承接**：R85 收尾決定。

---

## §E 誠實劃界（本包沒能做到的）

1. **Windows 側零真機量測**（同 R84）。D-1、A-3 的 `win-only` 那 22 筆、A-6 全部，
   一律**靜態推論**。本輪在 `darwin`。
2. **A-3 的假紅普查只做了 5/24**：我逐筆查了 production 那 5 筆的守衛，
   **19 筆測試面未逐筆查** ⇒ 「假紅 0」這句話**本包不敢說**，只敢說 production 面 5/5 有守衛。
3. **`a9-lf-only-write` 的存量未普查**：`write_text`／`open(...,"w")` 未宣告 `newline=` 的
   站點數本包沒量（那需要第五條規則，時間不足）。⇒ 該草案的假紅率**未知**，
   不得直接上線。
4. **既有鎖的隨機抽樣注入（M3 的那一面）本包未做**：我只對 M5 那 22 題與大表第一列做了
   證偽，**沒有**對「既有鎖庫隨機 20 支」逐支合成注入。R84 §4 M3 那一格記的
   「抽樣面至今一次都沒做過」，本輪**仍然成立**。
5. **`.claude/settings.json` 的 hook 全表本包未逐條列**（C-1 的第一行現查指令我沒跑），
   C-1 的「五支 hook 射程」是**讀檔判讀**不是機械對帳 ⇒ 標未驗證。
6. **未跑全樹閘門**：本包是唯讀掃描包，`tools/run_root_unittests.py` 一次都沒跑
   （並行波共用工作樹，跑它量到的 rc 是別人鍵盤的函數——`DEF-101-886`）。
   ⇒ 本檔**沒有任何「全樹綠」宣稱**。

---

## §F 給 R85 收尾的 blocking 清單（三筆，附持有面）

| # | 項 | 持有面 | 可否派並行包 |
|---|---|---|---|
| 1 | **B-0**：`_injection_criteria()` 8/11，docstring 兩處宣稱為假；M5 分母凍結在 R79 判準集 | 常數／消費端／史料**全部同住** `tools/tests/test_platform_neutral_paths.py` | ✅ 可（單包） |
| 2 | **A-1**：`shell=True` 唯一的輸入面正規化擋掉自己推薦的正解、放行自己點名的每一個反例，且只覆蓋 2 個 production 站點中的 1 個 | `AutoClaude/autoclaude/execution/` ×2 ＋ `AutoClaude/tests/` ＋ 根 `CLAUDE.md` | ❌ **不可**（跨子專案生產碼與根層護欄） |
| 3 | **C-1**：最大失誤桶「宣稱先於查證」連兩次量測居首（control lift 亦第一），**零機械物**，現行處置只有鐵律四那段散文 | `tools/probe/misstep_attribution.py` ＋ 新棘輪／新測試 | ⚠️ 可派，但**不得**與「改分群關鍵詞表」的包分開 |

**次高（major，建議同輪處理）**：D-1（SDD LATEST hook 的 3 支 `git` spawn 無掃描面）、
B-2（大表第一列過報分子）、A-3＋A-6（單平台外部執行檔／副檔名，同骨架同包）、
C-2（歸因探針無輪次過濾）。

<!-- guard-total:R85 --> **本輪護欄層累積淨額＝ 82838 → 83475（+637）** —— 🔴 **本輪有三列稽核痕跡，款(10) 判的是逐輪加總**：① P2 收工時 `82838→82838（+0）`；② 收尾單人窗口在十二包停工後 `82838→83320（+482）`；③ 四方複審收斂包 F1 停工後 `83320→83475（+155）`，來源全是複審點名的 blocking 修復（SD-B3 授權邊界安全回歸／ARCH-02 exe-argv 接線／樣本數鎖／QA-06 探針污染）。前兩列**不追溯修改**——每一列在寫下的那一刻都為真，就地改成後見之明正是款(7) append-only 指紋要防的形狀，三列並存即稽核痕跡。⇒ **R85 是加法輪，訴求 2「單輪淨額 ≤ 0」未達成**。🔴 **這是算術不是判斷**：需淨刪的量遠大於可用的去重面——兩份互相獨立的量測（機械 AST 普查 `tools/probe/guard_layer_dedup_census.py` ＋ 人工複核）與棘輪自陳的第三條出口（把 WHY／史料搬出護欄層，最集中處＝`_GUARD_LINES_REPIN_LOG` 自己）**全部用盡仍不足**。硬湊只能開始砍射程確有差異的對子＝真的挖洞。義務未消失：已具名為 `_NET_SUBTRACTION_DUE_ROUND`（**刻意不留延期參數**），到期未兌現即當場紅。逐筆量測與交棒＝`docs/06_quality/CrossPlatform_R85_Guard_Repin_Evidence.md` §4。`[收尾單人窗口當回合實測；憑證＝tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines 印 (+0) 且逐檔漂移 0 支]`
