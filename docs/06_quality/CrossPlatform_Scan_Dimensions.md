# 跨平台複審 Scan-A/B/C/D/E 五維掃描慣例（正式規格）

> **緣起**：Mac/Windows-11 相容性複審輪（R1 起持續累積；最新輪次見 `docs/06_quality/AutoSDD_Defect_Log.md`
> 最末列——本檔刻意不寫死輪號，R56 發現原寫「累積至今 R47」時實況已是 R55，且與同檔下方
> 內容自相矛盾）自 ~10+ 輪前開始，習慣把每輪掃描
> 拆成「Scan-A/B/C/D」四個維度分工，但此慣例此前只活在各輪缺陷帳本列的引用文字裡
> （如 `docs/06_quality/AutoSDD_Defect_Log.md` 的 DEF-101-265／269／289／352／353），從未有
> 一份獨立文件把字母對應的維度定義寫下來——新加入的審查員/agent 只能逐一翻歷史帳本引用逆向
> 推敲字母含義。本檔（DEF-101-387 落地）補上這道缺口，**只做正式定義，不重複教學**。

## 五維定義

| 維度 | 範圍 | 典型產出/信號 | 歷史帳本佐證 |
|------|------|--------------|-------------|
| **Scan-A** | 廣泛／背景 agent 通用掃描，**無固定子範圍**——不預設鎖定某類檔案或機制，讓 agent 自由發現跨平台問題 | 任意類型缺陷（路徑穿越、編碼、guard 覆蓋…皆可能命中） | DEF-101-352（R43 Scan-A：`pty_executor.py`／`prompt_dispatcher.py` 路徑穿越，背景 agent 全面掃描發現） |
| **Scan-B** | 檔名淨化／防增生鎖覆蓋率——`component_sanitizer` 家族（`_sanitize_component`／`_sanitize_log_filename`）與 WindowsApps guard 家族（`windowsapps_guard.sh`／`WindowsAppsGuard.ps1`／`is_real_python_candidate`）的覆蓋面是否有語言/檔案類型/呼叫點遺漏 | 未淨化呼叫點、guard 覆蓋不對稱（如某語言/某檔案缺席） | DEF-101-353（R43 Scan-B：WindowsApps guard 只收斂 `.ps1`／`.py`，9 支 bash 呼叫端從未排除） |
| **Scan-C** | CI/CD 與排程基礎設施維度——workflow（`.github/workflows/*-compat-ci.yml`）的 `runs-on`／步驟覆蓋是否對稱、nightly 佈線（`run_local_nightly.*`）是否對等、runner 環境（如 `windows-latest`＝Server SKU 而非用戶端 Windows 11）是否誠實揭露 | workflow 步驟缺席、平台落差未揭露、排程機制不對稱 | DEF-101-265（R24 Scan-C：Windows runner 實為 Server 2022，未如 macOS 側揭露）；DEF-101-269（R26 Scan-C：`windows-compat-ci.yml` 從未實跑 `install_windows_nightly.ps1 -WhatIf`） |
| **Scan-D** | 缺陷帳本／文件維度——基線數字新鮮度（如 pytest passed/skipped 是否隨新測試增長而回填）、帳本歸檔輪替（是否逼近 256KB 上限）、跨文件引用一致性（帳本 vs `ONBOARDING.md` 等 crossref 目標是否各說各話） | 基線數字落後、帳本超限未歸檔、跨文件狀態矛盾 | DEF-101-289（R32 Scan-D：`ONBOARDING.md` §7 pytest 基線落後實測 +11） |
| **Scan-E**（＝ Architect-Design） | Architect 架構最佳化評估——針對跨平台相容性既有架構慣例（dispatcher 模式／薄殼收斂／SSOT 收斂／Copy-on-Evolve 凍結政策／CI paths 白名單／帳本基線唯一站點等）逐項複核設計合理性，非缺陷掃描 | 架構判準記錄、SSOT/收斂建議、既有慣例是否仍成立的複核結論 | DEF-101-412（R52 Architect 記錄 evaluator_command 同進程/跨進程判準，見下節）；DEF-101-413（R53 Scan-B＋Architect-Design 交叉發現） |

自 R50 起連續多輪「五維掃描」已是實務穩定用詞（見缺陷帳本 DEF-101-394/396/403/412/413/414 等），本節同步將正式定義從四維補齊至五維，消除「新審查員需翻歷史帳本逆推 Scan-E／Architect-Design 字母含義」的落差。

## 架構判準：evaluator_command 分診問題（DEF-101-412）

R52 Architect 複核 `evaluator_command` 相關修復慣例時記錄一項前瞻性判準，供未來輪處理 evaluator_command 相關跨平台缺陷時作為**第一道分診問題**：

> 此 `evaluator_command` 是**同進程生成即消費**（可安全用 `sys.executable` 絕對路徑），還是**編譯期產出、執行期可能跨行程/環境/機器消費**（`sys.executable` 不安全，應假設目標 PATH 含對應 console script，不可用 `sys.executable`）？

- **同進程生成即消費案例**：`evolution/playbook_evolver.py`／`minimax_evolver.py` 的 `_derive_part_a_evaluator()`——同一 Python 行程內生成並立即由同行程消費，故 `sys.executable` 安全（見 DEF-101-394 修法）。
- **編譯期產出、執行期跨行程消費案例**：`infra/adapters/sdd_to_playbook_adapter.py` 的 `_EVALUATOR_TEMPLATE`（R53 DEF-101-413 後已由雙模板 tuple 收斂為單一字串常數，非複數）——本檔在編譯期產出 YAML 字串，執行期可能於完全不同的行程/環境/機器上被讀取執行，編譯時解析的 `sys.executable` 路徑在執行時未必存在；正確修法是去除裸 `python -m` 前綴、假設目標 PATH 含對應 console script（如 `pytest`），而非改用 `sys.executable`（見 DEF-101-403／DEF-101-413 修法與其「刻意未採用 sys.executable」的理由記載）。

動工前先問「這行指令是誰在何時執行」，誤用會把原本明顯的 `rc=127` 換成更難診斷的路徑不存在 `FileNotFoundError`。

## 架構判準：WindowsApps guard 三語言等價實作為何不可收斂（R56 Scan-E）

WindowsApps guard（排除 Windows Store App Execution Alias 空殼 `python.exe`）目前有**三份語言別的等價實作**：`tools/lib/windowsapps_guard.sh`（bash）、`tools/lib/WindowsAppsGuard.ps1`（PowerShell）、`tools/bootstrap_core.py`（Python）。每一輪的 Architect 都會把「三份實作＝SSOT 未收斂」重新列為候選發現、再逐一論證掉（R56 Scan-E 又花掉一次）。本節把該論證定案，供未來輪直接引用，不需重辯。

**(1) bootstrap 悖論——不可能以 Python 為單一 SSOT。** guard 的職責正是「在還沒有可用 Python 之前，判斷 Python 是否可用」。`tools/git-hooks/pre-push` 內的順序即為證據：先 `. "$TOPLEVEL/tools/lib/windowsapps_guard.sh"`（純函式定義、無副作用），再以 `if ! is_real_python_candidate python` 把關，**之後**才出現該檔第一個實際的 `python` 呼叫（`python -m py_compile`）——即 guard 必須在任何 Python 執行之前就能運作。（刻意以符號而非行號錨定：該檔為高頻改動檔，行號必漂移；覆核方式＝`grep -n 'windowsapps_guard\|is_real_python_candidate\|python' tools/git-hooks/pre-push` 確認三者的出現順序。R56 實測為 L46／L191／L204。）若把判斷邏輯收斂進 Python，判斷本身就需要先有可用 Python，邏輯上自我指涉。同理 `.ps1` 呼叫端（`bootstrap.ps1` 等）也必須在取得 Python 前完成判斷。故三份實作是**語言邊界造成的必要重複**，不是可收斂的實作重複。

**(2) 既有折衷——資料抽 SSOT、執行邏輯刻意保留多份。** 同類問題本 repo 已有定案先例：`tools/lib/bash_probe_spec.py` 把「探測規則的**資料**」（`PROBE_CMD`、期望輸出、System32 排除段）抽成單一真相源，但驗活的**執行邏輯**刻意保留三份獨立實作，理由明文寫在該檔 docstring——「以維持三份回歸鎖彼此獨立的鑑別力（不會因為共用函式本身壞掉而三份同時失效）」。WindowsApps guard 沿用同一折衷：三份實作之間的等價性不靠「收斂成一份」，而靠機械 parity 鎖保證——`tools/tests/test_windowsapps_guard_bash_parity.py` 與 `tools/tests/test_windowsapps_guard_cross_consistency.py`（含 repo-wide 前瞻掃描 + 附理由豁免白名單 + stale 自檢）。

**(3) 分診問句（動工前先問）。** 遇到「同一邏輯出現 N 份」的候選發現時，先回答：

> 這個重複是**實作重複**（同一語言、同一執行時機，該收斂成一份），還是 **bootstrap／語言邊界造成的必要重複**（跨語言、或需在該語言 runtime 尚不可用時執行，不可收斂）？

- 若為前者 → 收斂為 SSOT（如 R55 `BASE_DENY_CHARS`、DEF-101-238/429）。
- 若為後者 → **不收斂**，改為「資料抽 SSOT + 機械 parity 鎖」，並確認 parity 鎖確實有前瞻性（能抓到「新增第 N+1 份」而非只驗白名單內既有幾份——R43 曾因此翻修過一次）。

附帶邊界（R56 實測揭露，避免未來高估防護力）：parity 鎖屬正則/靜態掃描類防護，對「同時改名又改寫法」的再發明形狀存在既知盲區，見 `tools/tests/test_windowsapps_guard_cross_consistency.py` 內 `_STUB_NAME_RE`／`_STUB_PREDICATE_RE` 上方的變體對照表與方法論邊界說明（同 DEF-101-333 對本測試家族殘留繞過向量的四方一致裁定：三方各自構造出**不同類型**的繞過手法＝已觸及逐行正則相對於 AST 解析的結構性天花板，此時判準應從「是否可能被繞過」〔永遠是 yes〕切換為「當前投入 vs. 已知具體威脅模式是否相稱」。**R56 訂正**：本處原引 DEF-101-433，但該則前提〔`check_wrapper_thinness.py` 缺前瞻機制〕已於 R56 經 bug-injection 證偽——反向驗證實存於 `tools/check_script_parity.py` 的納管完整性掃描，故其「比例原則裁定」建立在不成立的前提上，不宜續作判例）。

## 架構判準：靜態掃描錨為何從三份複本收斂為 SSOT（R57 Scan-E，**改判 R56 裁定**）

> **為何必須寫在這裡**：上一節（WindowsApps guard）定案的是「**不可**收斂」，本節定案的是同一輪
> repo 內另一組重複「**應該**收斂」。兩者結論相反卻都成立——若不把判準寫清楚，未來輪的
> Architect 讀到上一節會誤以為「本 repo 對重複一律採不收斂」，而 R57 正是踩過這個坑：R56 曾
> 明文裁定「三份 `_CI_TREE_RE` 逐字複本刻意不收斂」，R57 把它推翻了。

**背景**：CI 的「pwsh 語法解析 + UTF-8 BOM 守門」step 掃描 N 棵樹，本機三處鎖
（`tools/tests/test_ps1_bom.py`／`test_smoke_ci_sync.py`／`test_ps51_compat.py`）各自從該 step
抽出樹清單比對，防「CI 與本機掃描面分歧」。R56 發現三份抽取正則是逐字複本，論證後裁定
「三份各有 `len==3` 斷言擋著、收斂屬跨檔重構逾越當輪界線」，列為 backlog 不收斂。

**R57 的改判與其實證**：三份讀的是**同一個檔案的同一個 step**，彼此**不構成獨立觀測**。實證即
DEF-101-481——三份的抽取式全部硬綁 `-Path` 具名參數，而 PowerShell 的 `-Path` 可省略；插入一棵
位置參數寫法的新樹後，三份共 20 支測試**同時**全綠。複製三遍只是把同一個盲點抄了三遍。

**(1) 分診問句（承接上一節，補上「同語言」側的細分）。** 上一節問的是
「實作重複 vs bootstrap/語言邊界造成的必要重複」。當答案落在「同語言、同執行時機」時，再問第二層：

> 這 N 份複本是否**觀測同一個對象**？

- **觀測同一對象**（如三份都解析同一個 workflow step、同一個常數檔）→ 複本數不產生鑑別力，
  N 份只是同一個盲點的 N 個副本，**應收斂為 SSOT**。鑑別力的真正來源是「錨本身有沒有被鎖」。
- **觀測不同對象**（如 `tools/lib/bash_probe_spec.py` 的三份驗活邏輯各自跑在 bash/PowerShell/Python
  三個 runtime 上）→ 複本彼此是獨立訊號，**保留多份**，靠 parity 鎖維持等價。
  （R57 round 3 Architect 註記：此例其實在**第一層**問句〔跨語言〕即已完成路由，本處僅借其
  「獨立訊號」語意作說明——本 repo 目前**沒有**「同語言、同執行時機、但觀測不同對象」的實例。
  故第二層問句是第一層的細分而非覆蓋；未來若出現真正的同語言實例，應回填取代本例。）

**(2) 收斂的必要配套：SSOT 必配呼叫端鎖。** R57 收斂後，round 1 Architect 實測「把任一呼叫端改回
自寫舊正則 → 全套測試仍 rc=0 全綠」——SSOT 沒有強制力就只是慣例。本 repo 既有先例
（`test_platform_utils_dedup.py`、`test_sanitize_component_callsite_frozen_versions.py`）都配了呼叫端鎖。
**收斂與呼叫端鎖必須同一次落地**，否則是把 N 個弱鎖換成 1 個沒有強制力的弱鎖，嚴格更差。
呼叫端鎖建議走 `ast` 而非文字比對：`ast.parse` 建樹時即丟棄註解、字串字面值也不會變成
`ImportFrom`/`Call` 節點，故「把接線留在註解或字串裡」的繞過在結構上無法成立（R57 實測驗證）。

**(3) 靜態錨「何時算夠好」——比例原則的適用時機。** R57 的錨改了三輪仍被找到逃逸形態：
初版硬綁 `-Path`（位置參數逃逸）→ 加 `.ps1` 尾巴錨（引號 filter／`-Include`／`Join-Path` 逃逸）
→ 加 cmdlet 出現次數錨（`get-childitem` 全小寫／`GCI`／`Dir` 逃逸）→ 加 `re.IGNORECASE`。
這是逐行正則相對於真 PowerShell AST 解析的**結構性天花板**，與 DEF-101-333 對 WindowsApps
parity 鎖家族的裁定同型。判準應在下述時點切換：

> 當連續多輪的新發現都是「**同一結構性成因**的不同表面形態」（此處＝正則不解析 PowerShell 語法），
> 而非新的成因類別時，判準即應從「是否可能被繞過」（永遠是 yes）切換為
> 「**當前投入 vs 已知具體威脅模式是否相稱**」。

R57 的收斂點：三條錨（樹抽取式／`.ps1` 尾巴計數／cmdlet 出現次數）＋ `re.IGNORECASE` ＋
一張**已實測的「不涵蓋」常駐表**（`_KNOWN_UNCOVERED`，未來被涵蓋時翻紅強迫改文件）。
真正的護欄不是「錨抓得到每一種寫法」，而是**誠實揭露抓不到哪些**——故本判例的最後一條是：

**(4) 邊界宣稱必須實測，且不得使用未窮舉的絕對詞。** R57 有兩輪的修復本身就栽在這裡：
round 1 寫「與引號界定全部無關」被 round 2 推翻；round 2 改寫成「唯一殘餘風險是非 cmdlet 途徑」，
又被 `get-childitem`（它就是走 Get-ChildItem）當場推翻。定案寫法為三段式：

> **已實測涵蓋**：（逐項列出，每項都跑過）
> **已實測不涵蓋**：（逐項列出，每項都跑過，並釘成常駐斷言）
> **未窮舉**：明文聲明本清單非窮舉，不做「唯一殘餘風險是 X」這類宣稱。

**本判準的套用範圍（R57 round 3 Architect ARCH-R57R3-04）**：R57 僅將其套用於 `_CI_TREE_RE`
一組。repo 內同族的同語言重複（如 `_FROZEN_SDD_VERSION_RE` + `_exclude_frozen_sdd_versions()`
於 `test_windowsapps_guard_bash_parity.py`／`test_windowsapps_guard_cross_consistency.py` 逐字
相同，另有 `_FROZEN_VERSION_DIR_RE` 兩份變體）**尚未逐一檢視**，列 R58 backlog——寫明此點是為了
避免下一輪讀到本節後誤判「R57 對同語言重複採了兩套標準」。

（本節論證原僅存於 `tools/tests/_ci_scan_anchors.py` docstring，經 R57 round 3 SA 指出
「Scan-E 級論證未回寫判例檔，未來輪 Architect 會讀到 R56 的舊語境而不知已被改判」後搬入正文。
對應帳本 DEF-101-481／494。）

## 架構判準：跨平台守門的「可用性條件」必須以目標平台的出廠組態為準（R58 Scan-E）

> **為何必須寫在這裡**：R58 是 R1~R57 之後**首次在原生 Windows 11 上開工**的一輪（此前 57 輪
> 全程於 macOS 模擬 Windows，DEF-101-348 為既有 known-gap）。開工首跑就以 skip 清單揪出一個
> 此前 57 輪都看不見的缺陷類別——**它不在被守的程式碼裡，而在「守門要不要跑」那個條件式裡**。

**病灶實例（DEF-101-507）**：`tools/tests/test_install_windows_nightly.py` 的
`@unittest.skipUnless(shutil.which("pwsh"), …)`。`install_windows_nightly.ps1` 是 Windows 專屬
安裝器，唯一需要語法守門的平台就是 Windows；而 **Windows 11 出廠只有 Windows PowerShell 5.1、
不含 pwsh 7**（R58 於真 Windows 11 Pro 實測 `pwsh` NOT FOUND），於是這道守門**在它唯一要保護的
平台上恆 skip**，卻在裝了 pwsh 的 macOS 開發機上會跑——守門在不需要它的平台生效、在需要它的
平台失效。且「能力不可得」是假的：5.1 內建同一個 `[System.Management.Automation.Language.Parser]`
API，實測對該檔 parse 出 0 errors。

**判準**：

> 跨平台守門的**可用性條件**（skip 條件、能力偵測、`which`／`command -v` 探測）必須以**目標
> 平台的出廠組態**為參照系，不得以**開發機組態**為參照系。

**為何這是判準而非一次性修一行**：病灶成因可複製，且證據就寫在那支測試自己的 skip 理由旁邊
——它的敘述是「跨平台安全（macOS/Linux pwsh 皆可跑）」，**作者當時的參照系就是自己的開發機**。
這是 DEF-101-348（Windows 專屬測試連續多輪全 APPROVE 卻從未在原生 Windows 上跑過）的直系
後代，只是失效點從執行環境搬到了條件式。

**同型第二實例（DEF-101-508）**：`AISDLC_SDD/scripts/ci-gate.ps1` 檔頭第 1 行自稱「Windows
PowerShell 版」，用法示範卻只給 `pwsh scripts/ci-gate.ps1`。使用者在出廠 Windows 11 照抄會拿到
「找不到 pwsh」——與 SDD 閘門完全無關的怪錯，還會誤以為得先裝 PowerShell 7。**與 R57
DEF-101-479（zsh glob）同類**：印給使用者複製貼上的指令本身就是缺陷面，且是**單邊平台**缺陷。

**機械強制**：`tools/tests/test_platform_guard_availability.py`（前瞻掃描，兩條）——
①全 repo git-tracked `test_*.py` 內「只認 `pwsh` 不認 `powershell`」的能力門檻；②active `.ps1`
內只給 pwsh 寫法的用法示範。兩條皆附「豁免須附理由 + stale 自檢 + 偵測器自驗」三件套。
**已登記的合法豁免**：`AISDLC_SDD/scripts/tests/test_install_post_commit_exec_bit.py`——它另有
`skipif(os.name == "nt")` 把 Windows 整個擋在外，只在 macOS/Linux 執行，而那些平台上 PowerShell
的執行檔名**就只有** `pwsh`（兜底一個在該平台不可能存在的名字沒有意義）。這個豁免本身即示範了
判準的正確用法：**問「目標平台是什麼」，而不是「本機有什麼」**。

**共用助手的偏好順序（不是任意選的）**：`tools/tests/_platform_helpers.powershell_exe()` 在
**Windows 上優先 `powershell`（5.1）**、其他平台優先 `pwsh`。理由有二：①出廠可得性（見上）；
②**驗語法要用目標引擎**——若優先用 7 去 parse，只有 7 才接受的語法會通過而在使用者的 5.1 上
炸掉，方向是 fail-open。

## 架構判準：何時該用「離線 golden 差分 oracle」取代近似法，以及它的邊界（R58 Scan-E）

> **為何必須寫在這裡**：R57 連續四輪在同一個地方翻車（PowerShell 註解剝除器的 fail-open），
> 最後定案「切勿再往字元集合補字元——那是 whack-a-mole」並把正解指給 R58。R58 落地了，但**同時
> 發現 R57 對這個解法的適用範圍宣稱過寬**。兩件事都必須留痕，否則下一輪會誤用。

**問題形態**：一支靜態鎖要判斷「某個字樣是**功能碼**還是**註解**」。近似法（前導字元白名單）
有結構性天花板——PowerShell 的 `#` 是否為註解取決於 tokenizer 的 command/argument 對 expression
**解析模式**，與前導字元無關，故白名單原理上不可能完備（實測 FAIL_OPEN=27/64，其中 20 案是
完全合法的日常寫法如 `$a = 1#c`）。方向是 fail-open ⇒ 鎖會假綠。

**解法**：把**真 parser 對全語料的判定**凍結成 golden fixture，測試時離線比對「近似法輸出」vs
「ground truth 輸出」。R58 落地為 `tools/gen_ps_comment_golden.py` +
`tools/tests/ps_comment_golden.json` + `tools/tests/test_ps_comment_golden.py`。

**(1) 適用判準——什麼問題可以 golden 化。**

> 這個判斷是**token 級事實**（同一份 bytes 餵進同一個 parser 永遠得到同一組答案、答案集合小
> 且穩定、不需要人來定義邊界），還是**語意事實**（需要分類判斷或執行期資訊）？

- **token 級事實** → 可完整凍結 ground truth。註解剝除屬此類。
- **語意事實** → **不可**。R58 明確推翻 R57 docstring 的「同法亦可解 `_ci_scan_anchors.py` 的
  同型天花板」這句宣稱：`_ci_scan_anchors` 要回答的是「這個 CI step 列舉了哪幾棵掃描樹」——AST
  不會告訴你 `[System.IO.Directory]::GetFiles()`／`Resolve-Path` **算不算**「列舉一棵掃描樹」
  （那是分類判斷），也不會把 `(Join-Path "AISDLC_SDD" $latestName)` 解成具體路徑（那需要執行期
  變數值）。golden **只解得掉其 cmdlet 計數錨那一條**（`CommandAst.GetCommandName()` 可使別名／
  大小寫歸一），**語意列舉面解不掉**。誤以為「做完 golden 就能拆掉那三條錨」會是淨退化。

**(2) 定位判準——golden 是「差分 oracle」還是「消費端資料源」。** R58 選前者，理由（兩案都
評估過，記於此免後續輪重辯）：消費端改吃 golden 的 span 會新增一條資料相依，而近似法**無論
如何都得繼續維護**——剝除器的鑑別力測試全是**合成字串**（不存在於任何 `.ps1`、golden 天生沒有
它們的條目），故「消費端吃 golden」只會造成「語料走 golden、合成走近似」兩條並存路徑，既沒消掉
天花板又多一個資料相依。差分 oracle 則把 fail-open 從「latent」轉成「**踩到的那一刻立刻翻紅**」
——即 R57 判定「不在該輪修」所依據的那個前提（全語料洩漏數為 0）失效的瞬間。**代價明說**：翻紅
時紅的是差分測試而非那支 fail-open 的錨點鎖本身，診斷需多跳一層，故差分測試的失敗訊息**必須
機械掃出並指名受影響的消費端**（不可寫死名冊——名冊會過期，而過期的名冊指向錯誤檔案比沒有
訊息更糟）。

**(3) 新鮮度必須 fail-closed，且「讓位規則」要寫清楚。** golden 存 per-file sha256：`.ps1` 改了
而 golden 未重生即翻紅。**R58 落地當下就踩到一個自製陷阱並留痕**：差分測試若不先檢查 sha 就
逐檔比對，golden 過期時舊 offset 套在新內容上必然切錯位置 → 會報出**誤導性的「近似法有
fail-open」**，實際只是 golden 過期。故凡「以 offset 為基礎」的斷言都必須**先驗 sha、只比對相符
的檔案、並把跳過的檔案數寫進失敗訊息**（跳過不得靜默，否則變成縮小掃描面），過期本身由專責的
新鮮度測試翻紅並指路重生。

**(4) 離線化的代價與誠實揭露。** 三層斷言中只有第 ③ 層（現場重新 parse 驗 golden 真實性）需要
PowerShell，會在無 PowerShell 的機器（Linux CI runner）skip。**這與本輪修掉的 pwsh-only 缺陷
不同類，理由必須寫出來而非默認**：真正的保護是第 ①②（新鮮度 + 差分），它們**離線、無條件、
每個平台都跑**——這正是把 ground truth 凍結成 golden 的目的；第 ③ 層只驗「golden 有沒有被手改／
跨引擎是否分歧」，且在**兩個有 PowerShell 的平台都會跑**（Windows 出廠 5.1、macOS 的 pwsh），
涵蓋目標平台。**若哪天第 ①② 也變成需要 PowerShell，那就是真的重犯了。**

**(5) 跨引擎量測數字不可互相比較。** golden 記錄產生它的引擎身分（`engine` 欄）。R57 於
pwsh 7.6.3 計得 2,847 個 Comment token（R57 當時語料）、R58 於 Windows PowerShell 5.1 對**落地後**
語料計得的 span 數**刻意不在本文寫死**——依本節自訂的「數字只准住一個家」政策，以
`tools/tests/ps_comment_golden.json` 的 `engine` 欄與條目數為唯一真相源（查法：
`python -c "import json;d=json.load(open('tools/tests/ps_comment_golden.json',encoding='utf-8'));print(len(d['files']),sum(len(v['commentSpans']) for v in d['files'].values()),d['engine'])"`）。
R58 round 1 Architect 抓到本處原寫死 2,880 而落地 golden 已是 3,017（差 137，成因＝量測取自本輪
修改 `.ps1` **之前**的語料、之後重生 golden 卻未回寫散文數字）——**本節正在教後人「跨引擎數字
必須可重現才採信」，卻自己被同一條判準打臉**，故改為指向唯一真相源而非再填一個會過期的數字。
（137 支
tracked `.ps1`；`git ls-files "*.ps1"` 全量，不排除凍結版）——兩者之間同時存在「引擎差異」與
「語料在兩輪之間有變動」兩個變因，R58 本機無 pwsh 故**不歸因**，只誠實記載。凡跨引擎/跨輪的
量測數字，一律連同**引擎身分 + 語料定義 + 量測指令**一起記，否則下一輪重跑得到不同數字時無從
判斷是誰錯了。（R58 另有一項實例：某掃描 agent 回報 5.1 計得 2,735，主控以三種語料定義
〔137 支全量 / 21 支 active / 15 支排除 SDD，三種定義下的 span 數皆與其回報值不符〕**皆無法重現**，故不採用。
**agent 回報的量測值必須可重現才採信**。）

**(6) 實作層的隱蔽陷阱（踩過，留給後人）**：.NET 的 `Extent.StartOffset`／`EndOffset` 以
**UTF-16 code unit** 計數，Python 字串索引以 **code point** 計數。本 repo 的 `.ps1` 內含星體
平面 emoji（🔴 U+1F534 等，.NET 算 2 單位、Python 算 1）。不做換算的後果是**靜默錯位**：R58
實測 137 支中 62 支長度不符、逾半數 span 切出來不是以 `#`／`<#` 開頭（此為**落地前語料**的量測，
僅作為「現象確實存在」的證據，不作為可重現基準——重現方式是拿掉換算後重跑產生器），而 golden
檔案本身「看起來完全正常」。凡跨 .NET／Python（或任何 UTF-16 與 code point 混用）邊界傳遞
offset 者，必須做單位換算並以**含星體平面字元的樣本**釘住。

## 架構判準：**文字錨驗的是「長得對」，不是「跑起來對」**（R58 Scan-E，本輪最重要的一條）

> **為何必須寫在這裡**：這一條回答的是使用者在 R58 提出的質疑——「不是每次都會 QA 測試，為何
> 還會有這麼離譜的錯誤？到底架構哪裡出問題？」。前面幾節談的是「某個守門有洞」，本節談的是
> **守門這件事本身的方法論偏差**，它解釋了為什麼缺陷能連續通過多輪四方 APPROVE。

**鐵證（DEF-101-512 立案依據）**：`tools/install_windows_nightly.ps1` 的 `-Status` 有明確的
結束代碼契約（任務存在→0、不存在→1；帳本 DEF-101-248 宣稱已修）。守它的是兩行文字斷言：

```python
self.assertIn("$loaded = Show-NightlyStatus", status_block)
self.assertIn("if ($loaded) { exit 0 } else { exit 1 }", status_block)
```

這兩行**一直是綠的**。而真實行為是 `-Status` **輸出 0 bytes、恆 exit 0**——PowerShell 的變數
指派會捕獲 success stream，`Write-Output` 印的報告全被吃進 `$loaded`，使它成為元素數 ≥2 的
`Object[]`，PowerShell 對這種陣列一律判真 ⇒ `if ($loaded) { exit 0 }` 恆成立。

**這個缺陷的履歷**（`git log -S` 實查）：在 `3f81d5c`「**R20 真 Windows 11 首輪機器複審**」
那一輪引入 → 在真 Windows 機器上通過四方複審 → 之後歷經多輪四方 APPROVE 都沒被抓到 →
R58 才由修復包在同一支檔案上動手時撞見。

**關鍵推論（必須寫清楚，否則會被歸因到錯的地方）**：

> 這與「在哪個平台開發」**無關**。缺陷在 Windows 輪、macOS 輪都會生，也都活得下來。
> 共同點是：**四位複審者讀的是同一份文字、看的是同一批綠色靜態錨**。文字對了就過，
> 沒有人去執行它、看輸出、比對結束代碼。

R58 另以 `git log -S` 逐一給出各缺陷站點的引入時間，證明年齡分佈橫跨「專案第一個 commit」到
「上一輪」（`ci-gate.ps1` 的 pwsh 用法示範來自 `0cda8aa` 專案首個 commit、存活 45 天；
`_PS_COMMENT_LEAD` 來自 R57、存活 1 天），**不存在「某平台積壓」的集中分佈**。

**(1) 判準。**

> 凡以**文字斷言**宣稱某可執行標的的**結束代碼控制流**者，同一支測試檔內必須另有至少一處
> **行為層**斷言——真的執行它並對觀測到的 `returncode` 表態（或以 `check=True` 讓非零直接拋）。

文字錨本身不是壞東西（便宜、跨平台、能鎖住「這行接線還在」），本判準不禁止它，禁止的是
**只有**它。機械強制：`tools/tests/test_behavioural_lock_required.py`。

**(2) 這條判準的機械化為何刻意做得「窄」——一次失敗的嘗試值得記下來。**
R58 第一版嘗試的是更雄心的判準：「掃出所有 active 腳本中，沒有任何測試真的執行它的」。
實測結果 35 支 active `.ps1`／`.sh` 中 **28 支**被判為「只有文字錨」——但逐一回查發現**大量假
陽性**（`WindowsAppsGuard.ps1`／`windowsapps_guard.sh`／`dev_start.ps1`／`bootstrap.ps1` 等其實
都有測試以 here-string dot-source 或 `-Command` payload 真的執行它們，AST 分類器看不到）。
**該版本因假陽性遠多於真陽性而未採用**。改鎖「結束代碼文字斷言」這個精確病徵後，實掃命中
**2 處**（皆在立案那支檔）、假陽性 0。教訓：

> 機械鎖的價值不等於它掃描面的大小。**一個假陽性率高的寬鎖，會被人學會忽略，等於沒有鎖**；
> 一個窄而精準的鎖才會被信任、才會在翻紅時真的被處理。定案前先量測真陽/假陽比。

**(3) 同源第二條：能力門檻必須登記出處。** DEF-101-507 的作者寫下 `skipUnless(which("pwsh"))`
不是打錯字，而是**以自己開發機的組態當參照系**。pwsh 專屬掃描只擋得住 pwsh 這一個名字；下一
個人探測 `uv`／`docker`／`node` 會重演同一個錯誤。故把判準**前移到登記**：任何在測試檔被
`which()` 探測的能力，都必須在 `test_platform_guard_availability._CAPABILITY_PROVENANCE` 登記
「哪些平台出廠即有、哪些需另裝」。**登記這個動作本身就強迫作者回答他原本沒問的那個問題。**
R58 實測全 repo 只有 7 種被探測的能力（`pwsh`／`powershell`／`git`／`bash`／`claude`／`tar`／
`pytest`），規模適合登記制；配 stale 自檢（已無人探測的條目須移除）。

**(4) 帳本紀律：`fixed@` 必須附可執行證據。** DEF-101-248 當年只以文字斷言結案，帳本狀態欄
沒有任何「跑了什麼、看到什麼」。本輪起（已寫入帳本《格式定義》）：狀態標 `fixed@` 者，狀態欄
須含**可重跑的指令**與**觀測到的輸出**（rc／計數／訊息片段任一）。
**此條刻意不機械化**：判斷「這段文字算不算可執行證據」需要語意理解，做成正則只會產出可繞過
的假宣稱（本 repo 已有多次前例）。它是紀律，靠複審者執行——而 R58 起的四方複審任務書已明文
要求「對每一項修復都要求行為層證據，不接受純文字斷言」。

## 使用方式

- **動工前**：依本輪待辦性質對照上表，決定本輪要跑哪幾維（通常五維皆跑，Scan-A 兜底發現
  未預期問題，B/C/D 針對性複查已知高風險面，Scan-E 由 Architect 角色複核架構慣例本身是否仍合理）。
- **記帳時**：帳本「發現情境」欄援引維度代號（如「R47 Scan-B」「R53 Scan-B＋Architect-Design」），
  供未來審查員／本文件對照，不需每次重新解釋字母含義。
- **擴充新維度**：若未來出現無法歸入 A/B/C/D/E 任一類的常態性掃描焦點，於本表新增一列並
  同步命名慣例（Scan-F…），不需改動既有五維定義。

## 邊界

本文件只定義「維度是什麼」，不規定「每輪必須怎麼跑」——各輪掃描的深度、工具、觸發時機由
`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 與各輪 prompt 自行決定，本檔不越權。
