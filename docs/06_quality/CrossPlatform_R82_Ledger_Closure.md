# CrossPlatform R82 — 缺陷帳本清債證據檔

> **用途**：R82「全力致力消除技術債」訴求下，缺陷帳本 `docs/06_quality/AutoSDD_Defect_Log.md`
> 的逐列處置憑證。帳本列是**索引**（≤700 bytes、列內禁半形 `|`），所有逐字原文、當回合
> 複驗指令與輸出、以及未結列的結構性阻擋分析，都落在本檔。
>
> 🔴 **檔名史（刻意留著，因為它本身是一筆治理事實）**：本檔開檔時叫 `AutoSDD_R82_*.md`，
> 取的是一個**不**符合 `CrossPlatform_*.md` 慣例的名字——因為 `unregistered_governance_docs()`
> 要求凡符合該慣例者必須登記進 `tools/lib/governance_docs.py::_GOVERNANCE_DOCS`，而開檔那個
> 包的持有面不含 `tools/lib/**`。那不是設計上的選擇，是**沒有登記權的人用改名讓「不受管」
> 變成一個看得見的決定**（該鎖的錯誤訊息自己給的第二條合法出口）。**本輪（帳本包持有
> `tools/lib/`）已改回慣例前綴並完成登記**，本檔自此受 256KB 體積守門與指針稽核兩項管轄。

---

## §1 Q5-ORPHAN-R82：孤兒稽核的「假綠」與 11 筆處置

### 1.1 實測（當回合，唯讀模擬）

模擬腳本把一列合成的 R82 列插進記憶體中的帳本副本（**不寫磁碟**），再各跑一次
`orphan_backlog_problems()`：

```
cur(real)= 81
--- REAL: orphan=0
cur(sim)= 82
--- SIM-R82: orphan=11
   * 帳本 :152 DEF-101-936
   * 帳本 :153 DEF-101-938
   * 帳本 :154 DEF-101-941
   * 帳本 :156 DEF-101-947
   * 帳本 :157 DEF-101-950
   * 帳本 :158 DEF-101-951
   * 帳本 :160 DEF-101-960
   * 帳本 :161 DEF-101-961
   * 帳本 :163 DEF-101-974
   * 帳本 :164 DEF-101-977
   * 帳本 :165 DEF-101-978
```

### 1.2 為什麼一寫新列就浮現（根因，不是巧合）

`current_round()` 取的是帳本「發現情境」欄的最大 `R\d+`。R82 開輪時帳本最末列仍是 R81，
於是時鐘停在 **81**，而這 11 列寫的承接輪次恰好也是 **R81** ⇒ `newest(81) >= cur(81)` 成立、
全數放行。**它們不是合規，只是被一個還沒走的時鐘蓋住**——`lagging_clock_notes()` 逐列
把這個 fail-open 窗口印成 warning（rc 不變），本輪開場實跑即可看到那 11 行逐字警告。

⇒ **正確處置不是修 `current_round()`**（把時鐘改成「由 commit 訊息／分支推得」會讓判準
隨被它所判的動作而變，正是 R75 已立的鐵律所禁）。正解是本輪把 11 列逐筆走完硬規則② 的
合法出口，**並且真的把 R82 首列寫進帳本**（`DEF-101-992`）——窗口因此在本輪關閉，
而不是留給下一個人在開場撞到。

### 1.3 11 筆逐筆處置

| ID | 本輪處置 | 為什麼不是「本輪修掉」 |
|----|---------|--------------------|
| DEF-101-936 | 改派：**未指派**（併入 §5.2 凍結面送審） | 標的在 `AISDLC_SDD_v0.01~v0.29`，需 Copy-on-Evolve 例外授權（歷來三次皆掌舵者明文核准） |
| DEF-101-938 | 改派：**R83** | 接線點 `tools/git-hooks/pre-push` 不在本包持有面，且「載具缺席時該紅還是該 skip」是決策不是實作 |
| DEF-101-941 | `partial@R82` ＋ 改派 **R83** | 見 §2.3：20/22 已有判準，缺的兩條要改 `tools/tests/test_bash32_compat.py`（非本包持有面） |
| DEF-101-947 | 改派：**R83** | 判準形狀要動 `AutoClaude/tools/check_loc_budget.py` |
| DEF-101-950 | 改派：**R83** | 下沉點在 `tools/lib/` 與 `AutoClaude/tools/hooks/`，兩處皆非本包持有面 |
| DEF-101-951 | 改派：**R83** | skip 模組群與三支 workflow 皆非本包持有面 |
| DEF-101-960 | 改派：**R83** | 缺 ubuntu job 與 nightly 兩剖面的 `--census-only` 實測值，本輪無雲端 run |
| DEF-101-961 | **`fixed@R82`** | 見 §2.1：現象「repo 內零載體」今日已不成立 |
| DEF-101-974 | 改派：**R83** | `tools/lib/skip_static_scan.py` 非本包持有面 |
| DEF-101-977 | 改派：**R83** | `tools/archive_defect_log.py` 雖在持有面，但其機械物必須落在 `tools/tests/`（非持有面）⇒ 只改 code 不加判準＝未完成，故不動 |
| DEF-101-978 | **回執** ＋ 改派 **R83** | 「開輪先寫帳本第一列」本輪**已執行**（`DEF-101-992` 落地、時鐘 81→82、窗口關閉）；把它升為機械第一動作那一半仍未動 |

---

## §2 本輪結案的複驗憑證（zero-trust：不採信掃描結論，逐筆自驗）

### 2.1 DEF-101-961 — `fixed@R82`

**原列現象逐字**：「額度水位改用 **%**（帳號不同 ⇒ 絕對量不可比）、80% 少派 agent、
95% 停止並準備喚醒。三方設計完成但 ADR 與實作兩階段皆在額度上限陣亡 ⇒ **本輪零交付且
repo 內零載體**」。

**當回合複驗**（Grep 工具直讀，不經 shell）：

- `.claude/hooks/context_budget_guard.py`
  - `797:QUOTA_THROTTLE_PCT = 80.0`
  - `798:QUOTA_HALT_PCT = 95.0`
  - `812:THROTTLE_FANOUT_CAP = 2`
  - `868:def quota_tier_of(pct: float | None) -> str:`／`879:def fanout_cap(...)`
  - `1276: 🔴 額度 {pct}% ≥ {QUOTA_HALT_PCT}%` 的阻斷分支
- `tools/lib/` 實查（`Get-ChildItem -Filter 'quota*'`）：
  `quota_escalation.py`(13185)／`quota_ledger.py`(10000)／`quota_limits.py`(20999)／
  `quota_meter.py`(21443) —— **四支**，非零載體。
- 該列 `分流去向` 的前置條件（「先解分母的取數管道」）亦已解答並機械化：
  `tools/lib/quota_meter.py:36` 逐字「server 依帳號方案自己算好 utilization 並回百分比
  ⇒ **本機不再自行推導分母**」，`:176 def denominator()` 是可查的取數口徑。

**為何不是假結案**：本列的缺陷本體是「零交付／零載體」，該敘述今日可證偽。**ADR 那一半
沒有被吞掉**——`ADR-XPLAT-005` 第 8 行逐字仍是「**狀態**：Proposed（R81）」，而它由
`DEF-101-980` 具名承接（該列狀態逐字：「解鎖＝① ADR blocking 全收斂並轉 Accepted；
② 載體二交付或明文 wontfix」，承接輪次 R82，仍為未結）。一列一狀態，不合併。

**原狀態欄逐字原文（本輪替換掉的那一段，逐字保全）**：

> open（承接輪次：**R81**）：R80 已把 a/b 登記進 `AutoSDD_improving_104.md` §1（含驗收判準），本列是帳本載體；實作與 ADR 皆未動。實測素材與四個候選分母見 詳見 CrossPlatform_R80_Scan_Findings.md §D

### 2.2 DEF-101-925 — `closed-by-decision@R82`（併入 DEF-101-947）

**兩列逐字對照**（當回合以工具切欄印出，非引述掃描結論）：

- 925 現象：「護欄層行數棘輪自述『淨增一行即紅』，但其稽核列逐字記著 R77 加 3505 行、
  R78 加 2243 行，連兩輪向上重釘且閘門全程綠；精確結論＝它對靜默成長有牙，對『重釘加
  補一列理由』零方向約束」
- 947 現象：「護欄層行數棘輪是收費站不是棘輪：自助放行寫在判準訊息裡（重釘＋補一列理由
  即放行），實測 R77 +3505／R78 +2243／R79 +3080 三輪連升零輪降」

**同一件事**：同一個判準（護欄層行數棘輪）、同一個機制（重釘＋補理由即自助放行）、
同一組實測（R77 +3505／R78 +2243，947 另多一筆 R79 +3080）。

**保留哪一列**：947。它的分流去向（「雙單邊判準：單輪成長綠、相鄰兩輪皆正紅、起算錨
shrink-only」）是 925（「加跨輪累積淨額判準」）的**超集**。

**資訊零損失**：925 的 R77/R78 兩個數字**已逐字存在於 947 原文**（上引），故合併不損失
任何量測值；925 本身未帶 947 沒有的事實。

**原狀態欄逐字原文**：

> open（承接輪次：**R80**）：改判準形狀要動 CONV 擁有的檔，CONV 已明文延後並附理由，證據見 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-925` 節

### 2.3 DEF-101-941 — `partial@R82`（**不結案**，誠實劃界）

**原列現象逐字**：「BSD vs GNU 差異 22 類（`sed -i`／`readlink -f`／`stat -c`／`base64 -w`／
`grep -P`／`find -printf`／`sha256sum`／`readarray` 等）在 29 支 active 腳本命中 0；…
今天零違規，但**這 22 類無任何機械物在守**」。

**當回合複驗**：

```
python -m unittest tools.tests.test_bash32_compat -v
Ran 27 tests in 1.351s / OK / RC=0
```

Grep `base64|sha256sum|readarray|_PATTERNS` 於 `tools/tests/test_bash32_compat.py`：
命中 `_PATTERNS`（:63 定義、:238／:701 兩個掃描面消費）與 `readarray`（:67），
**`base64` 與 `sha256sum` 零命中**。

⇒ 「無任何機械物在守」今日**大部分為假**（20/22 有判準，且 R81 已補上
`.github/workflows/*.yml` 的 inline `run:` 第二個掃描面），但**不是全假**：該列自己點名
的 8 個代表裡有 2 個（`base64 -w`／`sha256sum`）確實零判準。故只降級為 `partial`，不結案。
補法（要動 `tools/tests/`，非本包持有面）：在 `_PATTERNS` 補
`re.compile(r"\bbase64\s+(?:-[a-zA-Z]+\s+)*-w\b")` 與
`re.compile(r"(?<![\w./-])sha256sum\b")`，並在 `_BAN_TOKEN_SAMPLES` 各補一筆樣本
——`TestProseBanListIsFullyMechanised` 會自動雙向驗。

**原狀態欄逐字原文**：

> open（承接輪次：**R81**）：誠實劃界＝Linux 容器永遠是 GNU coreutils，掃不到不等於 BSD 跑得過。詳見 CrossPlatform_R80_PackF_Posix_Evidence.md BSD 節

### 2.4 DEF-101-234 — `closed-by-decision@R82`

**原列分流去向逐字**：「不建議現在主動重寫；等下次真的要改邏輯時『touch it, fix it』」；
狀態逐字：「open watch（Architect 建議 D）：本輪不排入行動項，維持現狀觀察；下輪若有人
異動其中任一對邏輯，應順手做 Python 核心化搬遷」＝**自述無獨立行動項、無 owner**。

**當回合複驗該列的前提是否仍成立**（Grep `_EXEMPT_PAIRS` 全庫 `.py` → 7 檔命中，
其中判準本體＝`tools/check_script_parity.py`）：

- `:735 "LATEST/tools/init_project": (_TIER3_OS_PRIMITIVE, "legacy v3.x 初始化精靈雙原生
  實作，無 [n/m]/gate 宣告錨點可機械抽取；R12 親讀定類豁免…")` ⇒ 文件化豁免＋決策依據**仍在**。
- `:748 "LATEST/tools/arch_fitness/run_self_evolution": (...)` 亦仍登記。
- **且覆蓋面自 R16 起變好了**：同檔 `:299-348` 已為 `run_self_evolution` 補上
  「退出碼契約三方鎖」（`_check_exit_code_contract()`，比對 spec／`.sh`／`.ps1` 三處），
  該列立案當時（R16）並不存在。

**為何不是假結案**：本列沒有任何殘餘動作項——它要求的是「下次異動時順手做」，那是一條
touch-it-fix-it 慣例而非 backlog；真的有人去動那兩對邏輯時，應**另立新列**承接，而不是
讓一列無 owner 的 watch 永久佔用未結名額。本列同時自 `_UNPINNED_HANDOVER_GRANDFATHERED`
移除（棘輪 18 → 17），見 §3。

**原狀態欄逐字原文**：

> open watch（Architect 建議 D）：本輪不排入行動項，維持現狀觀察；下輪若有人異動其中任一對邏輯，應順手做 Python 核心化搬遷

### 2.5 DEF-101-977 / DEF-101-991 的原狀態欄逐字原文（本輪改寫為索引）

- 977：

  > open（承接輪次：**R81**）：本輪實例已由另一包重釘（清單 98 筆、超標總量 143303 → 140957）；歸檔器側零改動

- 991：狀態欄未改寫，只就地追加改派附記，原文完整留在列上。

---

## §3 `_UNPINNED_HANDOVER_GRANDFATHERED` 棘輪轉動（18 → 17）

`DEF-101-234` 結案後即不再是「未結且無承接語境」的列 ⇒ 依
`stale_grandfather_problems()` 自己的訊息（逐字：「請從 … **刪除**它們，並把
`_UNPINNED_HANDOVER_CEILING` 下修」），本輪自 `tools/check_defect_log_crossref.py` 的
豁免清單移除該 ID，並把 `_UNPINNED_HANDOVER_CEILING` 由 **18 下修為 17**。

這是棘輪**往下**轉，不是放寬：清單只准變小，天花板只准往下改。

---

## §4 為什麼未結列只降了個位數：62/85 與 `tools/lib` 三條基線硬耦合

當回合實測（唯讀探針，母體＝主檔 140 列）：

```
unresolved = 85
unresolved AND oversize-grandfathered = 62
unresolved and NOT oversize = 23 筆
  DEF-101-206/234/863/912/917/918/919/925/926/936/938/941/947/950/951/960/961/974/977/978/980/981/991
```

`tools/lib/defect_ledger_index.py` 對主檔有**三條逐字相等**基線
（`OVERSIZE_ROW_GRANDFATHERED` 集合、`OVERSIZE_ROW_CEILING=98`、
`OVERSIZE_ROW_EXCESS_CEILING=138936`），由
`tools/tests/test_check_defect_log_crossref.py::…::test_the_real_ledger_baselines_are_exact_not_padded`
以 `assertEqual` 三向釘死。後果：

- 改動任何一列**超長豁免列**的位元組數（哪怕只是照硬規則② 就地追加一句「改派」），
  `excess` 就變 ⇒ 那支測試當場紅；
- 把某列瘦身到 700 bytes 以下 ⇒ 集合變 ⇒ 同樣紅；
- 唯一的合法動作是**同一次變更內同步重釘那三個常數**，而它們住在 `tools/lib/`。

⇒ **只持有帳本的包，結構上結不掉那 62 列。** 這不是懶惰也不是保守，是兩道各自正確的鎖
互為對方的違規（`DEF-101-957` 的形態，R80 已實證一次）。本輪把它立為 `DEF-101-992`。

> 🔴 **R82 帳本清債包訂正（上一段有三分之一為假，原文逐字保留不改寫）**：接手三條基線
> 之後第一件事是**真的去改一列再跑判準**，而不是採信這段推論。三種動作各跑一次，結論是
> 「結構上不可結」只對其中兩種成立（逐字輸出見 §9.1）：
>
> | 動作 | 判準怎麼說 |
> |------|-----------|
> | A 純追加結案附記（硬規則② 的合法出口） | **紅**：判準④ 零成長容忍，+132 bytes 即超線 |
> | B 結案 ＋ 把狀態欄長文搬進證據檔，該列仍 >700 | **綠，0 problems，完全不需要動任何常數** |
> | C 結案 ＋ 瘦身到 ≤700 | **紅**：判準② 要求移除豁免並下修兩個常數（需常數編輯權） |
>
> ⇒ 上一段那句「結構上結不掉」對 A 與 C 為真、**對 B 為假**。真正的阻擋不是「狀態字不准
> 改」，而是「**用追加的方式結案**要付位元組」。而 B 這條路今天就通，且它正是判準④ 訊息
> 自己指名的合法出口。本輪 15 列全部走 B／C，帳本主檔 240,097 → 225,272 bytes（當回合實測）。
>
> **更重要的是：判準④ 的方向其實是對的，不是反的。** 追加位元組的動作幾乎都是**改派**
> （把債往下一輪推），而結案的正確形態（把長文搬走、列上只留索引）本來就會讓列變短。
> 也就是說這條棘輪**懲罰延後、獎勵結案**——方向正確。所以本輪**沒有**去「修好它」，
> 改成把真正壞掉的那一半修掉：見 §9.2。

**這一條也解釋了掃描包 §D 類 8 筆為何本輪一筆都沒動**：`214`／`217`／`308`／`309`／
`313`／`333`／`400`／`348`／`055`／`296`／`335`／`401`／`412` 全數落在那 62 筆裡。

---

## §5 送審清單（**不要自己拍板** — 呈掌舵者）

### 5.1 需掌舵者／PM 拍板的 12 題（各一句話＋預設建議）

| # | ID | 一句話 | 預設建議 |
|---|----|-------|---------|
| 1 | DEF-101-268＋296 | 並行 agent 跑測試時 `.pyc` 寫入競態製造假紅：(甲) conftest 全域關寫 bytecode 但排除基線量測／(乙) 只在四方複審時關／(丙) 不做，把手動前綴收成一支腳本？ | (乙) |
| 2 | DEF-101-336 | 凍結版禁改鎖可不可以寫成無條件硬擋（歷來三次經核准打破）？ | 不可，維持可授權例外 |
| 3 | DEF-101-392＋401 | Copy-on-Evolve 政策要不要開一份正式 ADR？ | 要（每多一輪凍結版 +1，決策基期只會更貴） |
| 4 | DEF-101-559 | LATEST `hub-push.yml` sample 升不升版（升＝30 版同一 blob 的不變量首次分裂）？ | 不升 |
| 5 | DEF-101-795 | smoke 排程「退場」還是「降頻」？ | 降頻 |
| 6 | DEF-101-798 | 把 4 支未橋接 hook 橋進根層（會改變每個根 session 的 PreToolUse deny 面）？ | 逐支橋、每支先做 deny 面注入驗證 |
| 7 | DEF-101-802 | UEP 階梯末階的 PM signoff 要不要現在給？ | 給或明文延後，不要留空表 |
| 8 | DEF-101-243② | README badge：補日期新鮮度鎖 vs 刪掉沒人維護的 badge？ | 刪 |
| 9 | DEF-101-324（＋335） | 檔名淨化多對一碰撞要不要加唯一性後綴？ | 不加，維持 backlog |
| 10 | DEF-101-867 | 帳本內部矛盾判準原型訊噪比約 25%，上線即需白名單——上不上？ | 不上，先降訊噪比 |
| 11 | DEF-101-980 | `ADR-XPLAT-005` 的 blocking 要不要現在收斂並轉 Accepted？ | 要（載體二被規格先行擋住） |
| 12 | DEF-101-377 | 工作樹 CRLF renormalize 是破壞性操作，什麼時候做？ | 下一次 clean tree 時 |

### 5.2 凍結面（Copy-on-Evolve）5 筆 — 建議合併成**一個**決策

`DEF-101-936`（116 站點）／`917`（87 筆 exec bit）／`919`（1131 筆目錄項原語）／
`388`（v0.05~v0.29 FF-17 斷言）／`338`（4 支假 SHA 檔仍被追蹤）。

三個選項：① 逐案例外授權（如 R44/R45/R46）；② 訂一條成文規則「凍結版只在會讓使用者
開箱即炸時才回補」；③ 一律不改，但每一筆都要有精確計數的可見欠債登記＋不得靜默增長的鎖。
**選 ③ 的話 936/917/919 今天就能改 `wontfix+理由`**（三者皆已有精確棘輪），388/338 需先補計數鎖。

### 5.3 mac 真機 3 筆 — 具名改派 **R83**，附確切指令

| ID | 在 macOS 上要跑什麼 |
|----|--------------------|
| DEF-101-991 | `python3 -m pytest tools/tests -k quota -q` ＋ `python3 tools/lib/quota_meter.py --check`（本輪已實查 `tools/lib/quota_ledger.py` **確實存在**，10000 bytes ⇒ 掃描包對「該檔是否落地」的疑問已解答，該列前提不需訂正） |
| DEF-101-981 ① | 跑一次全套並貼 `[MAC-NATIVE-ONLY]` 標籤的 skip 明細（本列另外五項不是 mac 卡點，故**整列仍留 R82**，不隨 ① 改派） |
| DEF-101-675 | 把 `macos-compat-ci.yml` 的 zsh 探針改為外側證物檔形態後 dispatch 一次（⚠️ 本列在超長豁免面內，本包結構上動不了，見 §4） |

---

## §6 需別包／下一輪配合（誠實劃界）

1. **把本檔補進 `tools/lib/governance_docs.py::_GOVERNANCE_DOCS` 並改回 `CrossPlatform_R82_*` 前綴**
   ——本檔目前不受體積守門（見檔頭）。
2. **`tools/lib/defect_ledger_index.py` 三條基線的重釘權**：沒有它，62 筆超長未結列
   結構上不可結（§4／`DEF-101-992`）。
3. `DEF-101-941` 的兩條 BSD regex（`tools/tests/test_bash32_compat.py`，§2.3 已給逐字樣式）。
4. `DEF-101-977`／`676` 的歸檔器 `--plan` 三數字與豁免過期偵測：code 在
   `tools/archive_defect_log.py`（本包持有），但機械物必須落 `tools/tests/`（非持有面）。
5. **殘餘 11 筆 R83 程式碼標籤**（見 §7.2）：各自的持有包要嘛改成 `round-label-ok` 行尾
   具名豁免，要嘛改寫措辭；本包不動別人的檔。

---

## §7 收尾實測

### 7.1 閘門與數字（開場 → 收尾）

| 量 | 開場 | 收尾 | 指令 |
|----|-----|-----|------|
| 未結列數 | **85**／140 列 | **83**／141 列 | `check_defect_log_crossref.py --unresolved-count` |
| 帳本當前輪 | R81（fail-open 窗口開著） | **R82**（窗口關閉） | 同上工具的收尾行 |
| R82 首列落地後的孤兒 | 模擬得 **11** | **0** | `orphan_backlog_problems()` |
| `_UNPINNED_HANDOVER` 豁免／上限 | 18／18 | **17／17** | 收尾訊息逐字 |
| 超長豁免列（集合／筆數／超標總量） | 98／98／138936 | **98／98／138936（未動）** | `oversize_row_problems()` |
| crossref 全套 rc | 0（假綠，見 §1.2） | **0（真綠）** | `python tools/check_defect_log_crossref.py` |

淨額誠實揭露：**結案 3 筆**（`234`／`925`／`961`）**新增 1 筆**（`992`）⇒ 未結 −2。
`941` 只降級為 `partial`（仍計未結），`936`／`938`／`947`／`950`／`951`／`960`／`974`／
`977`／`978`／`991` 十筆是改派不是結案——**改派不會讓這個數字變小**，本檔不把它算成成績。

### 7.2 副產物（本輪最大的單一收穫，不在原任務書上）

把 R82 首列寫進帳本，讓 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 的
**全樹違規由 127 筆掉到 11 筆**（同一支掃描器、同一棵樹，只換了「帳本當前輪」這個輸入）：

```
cur=81 (pre-A5 clock) offenders = 127
cur=82 (post-A5 clock) offenders = 11
```

被治好的 116 筆全部是**別包**寫下的 `R82` 標籤（`.claude/hooks/context_budget_guard.py`／
`AutoClaude/**`／`tools/lib/quota_*.py`／`tools/session_resume_planner.py`／`tools/tests/**`
…）——這正是 `DEF-101-978` 逐字描述的形狀：「每包看到的都是**別人造成的紅**，正解卻是
開帳本列」。⚠️ 誠實劃界：那支測試**現在仍是紅的**，殘餘 11 筆全是 `R83` 標籤，
分屬 `tools/tests/test_mac_readiness_r82.py`(6)／`tools/lib/quota_meter.py`(1)／
`tools/install_mac_nightly.sh`(1)／`AutoClaude/tests/**`(3)，**沒有一筆在本包持有面**；
且它在本包動工**之前**就已經是紅的（R83 > R81 同樣成立）。
另記一筆量測雜訊：兩次掃描之間 `AutoClaude/tests/test_conftest_windows_native_skip_report.py`
被並行包改動過（`:112 R83` 只出現在第二次掃描）⇒ 兩組數字不是同一個工作樹快照，
量級可比、逐點不可比。

### 7.3 合成注入紅綠自證（in-memory，不寫磁碟）

| 注入 | 對象判準 | 結果 |
|------|---------|------|
| A：拿掉 `DEF-101-936` 的 R82 改派附記 | `orphan_backlog_problems()` | GREEN → **RED 1**（逐字指名 `:154 DEF-101-936 … 早於當前輪 R82`） |
| B：把 `DEF-101-234` 還原成 `open watch` 原文 | `unpinned_handover_problems()` | GREEN → **RED 1**（`:55 … 既沒有可解析的承接輪號、也沒有字面「未指派」`） |
| C：把 `DEF-101-234` 加回 `_UNPINNED_HANDOVER_GRANDFATHERED` | `stale_grandfather_problems()`＋`grandfather_ceiling_problems()` | GREEN → **RED 1＋1**（前者逐字要求「下修為 17」，後者「膨脹到 18 筆 > 上限 17」） |

另有一次**非合成的真紅**：`DEF-101-992` 第一版寫成 705 bytes，落地前的位元組守門當場
`OVER … ABORT: guard violated -> ['DEF-101-992']`（rc=1），刪掉「當回合」「就地」四個字
後 690 bytes 才放行 ⇒ 700 bytes 那條線不是散文。

---

## §8 被瘦身成索引的那些列的**原列逐字原文**（zero-loss 保全）

> 帳本列被瘦身成索引之後，唯一還能重驗這些結案是否為真的地方就是本節。每一段都是**整列逐字**（含所有欄位），不是節錄。

🔴 **R82 收尾（文件面）對抗稽核訂正兩件事，本節標題原本寫死「13 列」而底下有 15 個 `### §8.x` 子節**
（現查＝數本檔 `^### §8\.` 開頭的行；當回合實測 **15**）。兩個問題各自獨立：

1. **數字與清單不符，而清單才是可現查的那一邊** ⇒ 標題不再寫死條數（同本 repo 對
   `MIN_TESTS`／tier 表／`.importlinter` 條數已判過數次的「寫死的數字必過期」）。
2. **本節不是「本輪結案清單」，只是「原文被搬出來的那些列」** ⇒ 稽核者實測本輪另有
   **3 筆結案不在本節**：`DEF-101-234`（§2.4）／`DEF-101-925`（§2.2）／`DEF-101-961`（§2.1）。
   它們的複驗憑證從一開始就寫在 §2，**不是漏做**；漏的是「本節看起來像完整清單」這個讀法
   ——把兩處加起來才是本包的結案面。🔴 誠實劃界：帳本上狀態欄提到 R82 且已結的列
   **不只本包這些**（當回合以帳本自己的 `_classify()` 逐列實測為 **24 筆**，其中
   `984`／`989`／`990`／`993`／`994` 等屬額度軸與 hook 軸各包，不在本包射程）
   ⇒ 「本輪一共結了幾列」這個數字**不得只讀本節**，現查入口＝
   `python tools/check_defect_log_crossref.py --unresolved-count` 搭配逐列狀態欄。

### §8.1 DEF-101-055

```text
| DEF-101-055 | 2026-07-12 | DEF-101-053 修復收緊 `match=` 時揭露 | **ORM `CheckConstraint(name=...)` 與 DB 實際 constraint 名分歧**：ORM `_pg_models.py` 宣告 `ck_playbook_runs_status`／`ck_kb_outcome`，但 DB（alembic 0001 inline CHECK）實際名為 `playbook_runs_status_check`／`knowledge_entries_outcome_check`（PG 匿名 inline CHECK 預設名）。因 production schema 由 `alembic upgrade` 建置（非 ORM `create_all`），這兩個 ORM CHECK name 對 DB **從未實現＝裝飾性**。影響：任何 migration 若 `DROP CONSTRAINT ck_playbook_runs_status` 會失敗；離線 DDL snapshot 測 ORM name 通過但不保證 DB 有該名。0017/0018 新 CHECK 用顯式 `ck_*` 名故 DB 一致，分歧僅限 0001 兩個 inline CHECK | P3 | 記事存證，不阻塞：CRUD 契約測試已改綁 **DB 實際名**（正確、真測 CHECK）；離線 DDL 測 ORM name（分層合理，二者測不同層）。未來若需對齊，另開 rename migration（屬 cosmetic，PG 未上線無急迫） | open（SD_10 PG-track 記事；本輪貢獻＝辨識 + CRUD 測試改綁真實名 + 探針取證真名） |
```

### §8.2 DEF-101-214

```text
| DEF-101-214 | 2026-07-21 | R15 四方一審（QA／SD 兩位獨立審查各自親歷；Architect 修復階段主控自身重演） | **方法論發現（非程式缺陷）：共享單一工作樹的多 agent 併發審查／修復存在真實交叉污染風險，本輪三度實例佐證**——①QA 親歷 `tools/dev_start.py` 在無自身寫入操作下短暫（約 2 分鐘）恢復成 git HEAD 版本又自行變回 R15 版本，事後對照 Architect 報告「過程中一度誤用 `git checkout` 把整份 R15 改動清空，已重建並還原」證實為同一事件；②SD 親歷 `run_local_nightly.sh.qa-backup` 殘留檔案與「上方註解 14 天／下方功能碼 30 天」暫態內部矛盾，係 QA 進行中的 bug-injection 尚未還原時被撞見（QA 隨後乾淨復原，三方交叉核對真正落地基線一致無誤）；③主控自身在修復 QA-R15-REV-4 時對 `autoclaude-ci.yml` 誤用 `git checkout --` 精確還原單一檔案，未料該檔案本身在 R15 輪已有正常增量修改（concurrency 區塊），指令把整份 R15 異動打回 HEAD（見 DEF-101-213 記載，當場發現並重新套用）。三起事件根因相同：**`git checkout`/`git restore` 對「尚未 commit 的異動」是全有全無的還原，無法選擇性只還原自己剛注入的 bug**，共享工作樹下極易誤傷其他審查者／自己稍早的合法異動。 | P2（方法論／流程風險，非本輪程式缺陷） | **建議下輪起四方複審／一審採 `Agent` 工具的 `isolation: "worktree"` 隔離每位審查者**（各自在獨立 git worktree 工作，互不干擾、bug-injection 還原失誤也不會波及他人或主控本身異動）；若仍需共享工作樹，還原紀律改為「`cp` 精確備份/回填單一檔案」而非 `git checkout`/`git restore`（後者是全域操作，即使目標只寫一個檔名，仍會抹除該檔案自己所有未提交的修改，不只抹除本次注入的部分） | open（記事存證＋流程建議送下輪／未來輪參考；本輪三起事件皆已確認未造成不可回復損害——最終工作樹經逐檔 diff --stat 核對與 git HEAD 基線一致） |
```

### §8.3 DEF-101-217

```text
| DEF-101-217 | 2026-07-21 | R15 四方複審（QA／Architect 各自獨立親歷；SA/SD 兩次背景執行逾時/API中斷佐證同根風險） | **DEF-101-214 併發污染風險於複審輪再次真實重演，且新揭露「共享 scratchpad 目錄本身也有碰撞風險」這個 DEF-101-214 原文未提及的面向**：Architect 複審過程中以 `python3 -m unittest` 平行執行測試時，`test_workflow_permission_concurrency_lock.py::test_workflow_level_contents_read_present` 短暫轉紅（斷言找不到 `aisdlc-sdd-arch-fitness.yml` 的 permissions 區塊），經 `stat` 查 mtime 為複審進行中 2 分鐘前、Architect 自陳全程未編輯此檔，判定為「另一方（同時在跑的 SA/SD/QA 背景 agent）對同一檔案即時 bug-injection 造成的瞬間污染，已自行復原」；同時檢視共享 scratchpad 目錄，發現大量非 Architect 建立的檔案（`qa-backup/`、`imn_injected.sh`、`run_local_nightly.sh.orig_backup`、`repro_tee_exec.sh` 等，數個與其 mtime 幾乎同刻），證實該目錄確為本 session 四位審查者共用而非各自隔離。另主控自身於本輪帳本編輯過程中亦收到至少 2 次「檔案已在磁碟被修改」系統提示（`macos-compat-ci.yml`／`AutoSDD_Defect_Log.md`），逐一核實後確認皆為此同根污染的無害副作用（crossref 58 筆、diff --stat 增量皆與預期吻合，無實質內容遺失）。**複審階段另有 2 次背景 agent 執行逾時/API 中斷**（SA 第一次 stall 600s、SD 第一次 stall 600s＋第二次 API 連線中斷），時間點與內容（SD 中斷前訊息「Now let me inject a bug...」）高度提示同為共享工作樹資源競爭之外顯症狀，經主控立即查核工作樹皆確認未受損（zi 3 次重新派遣皆縮小範圍後於較短時間內成功完成）。 | P3（方法論／流程風險，非本輪程式缺陷；累計本輪已 4 起實例，風險評估由 DEF-101-214 的「觀察」提升為「確認模式」） | **Architect 建議：DEF-101-214 的「未來優先 isolation: worktree」應從「下輪參考」提升為「下輪起強制採用」**；且應一併檢討是否需要為每位審查者分配獨立 scratch 子目錄（本輪 4 起實例中至少 1 起〔SD 兩次逾時/中斷〕與共享 scratchpad 資源競爭時間點高度相關） | open（記事存證＋流程建議累加至 DEF-101-214 同一根因；本輪最終驗證確認全部 4 起實例皆無實損——工作樹與帳本內容經逐項核對與 crossref 機械複核，最終狀態正確完整） |
```

### §8.4 DEF-101-296

```text
| DEF-101-296 | 2026-07-24 | R33 四方一審 Architect；二審 Architect 定位出可重現根因 | **`tools/tests/test_windows_forbidden_filename_parity.py` 在多支 `pytest` 行程並行對同一測試檔執行時，可重現間歇性 FAILED**（一審觀察到 1 次孤立假紅；二審改用「兩支 `pytest` 行程同時起跑同一測試檔」做 40 組對照重驗，**baseline 2/40 fail**，且不只 1 個測試方法——涉及 `test_bash_flags_every_char_in_python_forbidden_set`（1 次）、`test_python_regexes_agree_on_reserved_names`（連續 6 次，此測試**不涉 bash subprocess**、純 Python 靜態比對）、`test_bash_flags_every_reserved_name_python_flags`（連續 4 次），~17 次孤立重跑約 11 次失敗）。**根因高度疑似 `__pycache__` bytecode 快取並行寫入競態**：設 `PYTHONDONTWRITEBYTECODE=1` 後同款 40 組（80 次行程）**0/40 fail**；純序列孤立重跑 100+ 次全綠；純背景 CPU 負載對照組 40 次全綠——三組對照排除「bash 子行程時序」與「一般系統負載」，指向 bytecode 編譯/寫入競態。此條件（多位審查 agent 同時在同一 working tree 對同一測試檔跑 pytest）正是四方複審協定的常態操作，非罕見情境 | P3（不影響本輪其餘驗證結論；純序列執行下未見復發，非阻斷） | 四方複審時避免多位審查員同時對同一測試檔跑 `pytest`，或審查階段統一設 `PYTHONDONTWRITEBYTECODE=1` 環境變數規避競態；若未來仍在純序列執行下復現，才需要進一步用 `strace` 深入根因 | open（backlog，根因假說已有具體對照數據佐證、非阻斷 APPROVE；具體規避手法已記載供下一輪四方複審參考） ｜🔴 R81 改派，承接輪次：**R82**（同 `DEF-101-268`：需掌舵者拍板，三選一方案已列於 R81_Ledger_Triage S1-24） |
```

### §8.5a DEF-101-308

```text
| DEF-101-308 | 2026-07-24 | R35 四方二審 Architect（對追加的靜態一致性鎖再次 bug-injection） | **`TestDevStartPs1BothFailureBranchesSetLastExitCode`（DEF-101-304 修復追加的靜態鎖）純字面計數比對可被刻意繞過**：把「找不到 repo 根」分支的裸 `return` 格式偽裝成 `if ($DotSourced) {  return }`（多一個空格）閃避 `bare` 字面比對，同時在檔案別處插入無害註解行 `# decoy: if ($DotSourced) { $global:LASTEXITCODE = 1; return }` 把 `fixed` 計數補回 2，兩個測試皆維持綠燈，但該分支是貨真價實的回歸。Architect 判定：純字面計數本質上可被同檔案任何位置的字面複製繞過，是這類鎖的結構性限制；真正觸發需「刻意插入 decoy」的對抗性動作，非一般開發者手誤會踩到的情境，且本輪 `dev_start.ps1` 兩分支修復本身正確，此僅為「測試的測試」層面鑑別力縫隙 | P3（低機率對抗性繞過，backlog；Architect 明確判定非阻擋本輪 APPROVE） | 未來若要堵死可改用「解析式」驗證（逐一解析 `if (-not $Root)`／`if (-not $Py)` 兩區塊內容各自含 `$LASTEXITCODE` 賦值語句，而非整檔字面計數），成本較高、超出本輪 P2 缺陷比例原則 | open（backlog，如實記載，列入下一輪追蹤） |
```

### §8.5-R82 `DEF-101-308` 的結案**理由**被實測推翻（結論不動，只換理由）

由 R82 收尾（文件面）的對抗稽核提出、本節作者當回合獨立複驗成立。

**被撤回的是什麼**：該列 `closed-by-decision@R82` 的理由裡，除了「已知繞過手法計 5 個
＜ `DEF-101-400` 訂下的第 6 個門檻」之外，還掛了**第二個佐證**——聲稱根層測試樹裡沒有
現成的 PowerShell 語法樹解析可用，藉此支撐「AST 方案成本較高」。**那半句是假的。**

**當回合反證（兩條，互相獨立）**：

```
# ① 該解析器就住在根層測試樹裡，且是真的在跑的測試
tools/tests/test_install_windows_nightly.py:482
    f"$null = [System.Management.Automation.Language.Parser]::ParseFile("

# ② 它當回合真跑，不是死碼
> python -m unittest test_install_windows_nightly.TestInstallWindowsNightlySyntax -v
test_parses_with_zero_errors ... ok
Ran 1 test in 0.117s
OK                                        # rc=0
```

另有第二個站點 `tools/tests/_platform_helpers.py:390` 以 `Parser::ParseInput` 取
Comment token（現查入口＝用 Grep 工具搜 `Language\.Parser\]::Parse`）。

**為什麼結論仍然成立**：`DEF-101-400` 的準則是**繞過手法計數**（第 6 個出現才評估 AST），
不是成本論證——繞過手法今天仍是 5 個，準則未觸發，所以「本列無行動項」這個結論站得住。
不成立的只有那個順手加上去的成本佐證。⇒ **只改理由，不把整列打回 `open`**（把一列因為
理由有瑕疵就重開，會讓下一個人以為繞過手法數變了）。

🔴 **這一筆的形狀值得記住**：假話沒有出現在**結論**上，出現在**支撐結論的第二個理由**上，
而那個位置沒有任何機械物在看——`TestR81GhostPathClaims` 只驗「以反引號寫出的路徑存不存在」，
這句話裡一個反引號路徑都沒有。它是「宣稱先於查證」那一桶的典型樣本：寫的人**推想**
repo 裡沒有 PS AST，而查一次只要一個 Grep。依本 repo 判例，本節**刻意不逐字複述**那半句
原文（訂正註記逐字引述假話＝製造新假話，下一個人 grep 到它會以為那是現行說法）。

### §8.5b DEF-101-309

```text
| DEF-101-309 | 2026-07-24 | R36 一審 SD 首先發現，二審 Architect（ruff F401 正交防線）／SA（嚴重度精修）／QA 三方獨立覆核交叉確認 | **`test_find_git_bash_parity.py::_extract_py_system32_word()`（DEF-101-307 修復新增）的未錨定 `re.search` 掃全檔文字可被誘餌行內註解繞過**：在 `_has_system32_segment()` 函式內插入一行含 `part.lower() == _spec.SYSTEM32_SEGMENT` 字樣的行內註解，同時把真正執行的 `return` 陳述式改回硬編字面值 `"system32"`，11 個測試仍全數 PASSED——因為該函式現在的邏輯是「①未錨定搜尋確認樣式**存在**於全檔文字（不分辨是否為真正執行的程式碼或僅為註解/docstring），②但實際回傳值不取匹配內容，而是直接 `import bash_probe_spec` 讀取常數本身」。**SA 二審精修嚴重度定性**：舊版（`m.group(1)` 直接回傳匹配到的文字）繞過需要偽造出「內容剛好等於正確值」的誘餌，等同攻擊者需先知道正確答案；新版繞過只需貼上樣式相符的誘餌文字、**不需知道任何正確值**即可讓測試回傳 golden 值放行——比對值與被測程式碼真實行為已完全脫鉤，繞過門檻較舊版**實質降低**，非單純沿用舊限制。**Architect 二審發現正交緩解因子**：`ruff check`（AST-based，CLAUDE.md 明文必跑 CI 檢查）在此特定失效模式下會因 `_spec` import 變成未使用觸發 `F401`，非完全無防線。SD 補充：此縫隙亦有非對抗性的自然觸發路徑（merge conflict／rebase 手誤保留說明性註解但程式碼行被誤還原的「stale comment drift」），非僅限刻意攻擊 | P3（測試鑑別力縫隙，本輪 SSOT 收斂本身正確；有 ruff F401 正交防線；四方一致判定非阻擋） | 建議未來把 `test_find_git_bash_parity.py` 內 `_extract_py_system32_word`（及同檔 `_extract_py_candidates`／`_extract_ps1_candidates`／`_extract_ps1_system32_word`）的搜尋範圍改為先用 `ast.get_source_segment()` 鎖定目標函式的原始碼片段再比對，而非掃全檔文字；範圍明確、成本可控，但超出本輪「收斂一個常數 SSOT」的範圍，依 surgical-changes 原則不在本輪順手處理 | open（backlog，四方一致判定非阻擋，如實記載列入下一輪追蹤） |
```

### §8.5c DEF-101-313

```text
| DEF-101-313 | 2026-07-24 | R37 一審 SD（對 WindowsApps guard 收斂做 bug-injection 找新繞過手法） | **`test_windowsapps_guard_cross_consistency.py`／`test_bootstrap_ps1.py` 對「呼叫端用額外 `-or` 條件覆蓋 `Test-IsRealPython` 共用函式回傳值」這類新繞過手法無鑑別力**：把呼叫端改成 `$isRealPython -or (Get-Command python -ErrorAction SilentlyContinue)`（偽裝成「企業 GPO 環境下 `.Source` 可能為空字串」的防禦性寫法），本輪新增的存在性檢查（純字面 regex 確認呼叫語法存在）與行為測試（只測共用函式本身，不測呼叫端如何消費回傳值）皆抓不到，端到端測試在本機 macOS pwsh 上因既有 PATHEXT 解析侷限本就對此無鑑別力（已知既有限制，非本輪新增）。SD 另行驗證：此類呼叫端邏輯異動會改變 `tools/check_wrapper_thinness.py` 的正規化內容 hash 釘選並正確變紅，構成有效的跨平台正交防線（已接入本機 CI 對等與 pre-push 紀律） | P3（本輪兩份 WindowsApps guard 測試檔本身鑑別力有限，但有正交防線有效補位；觸發需「看似合理的防禦性寫法」，非典型手誤但也非需惡意規避意圖的高門檻）| 若要讓 `test_windowsapps_guard_cross_consistency.py` 自身具備此類鑑別力，可將存在性檢查從 regex 升級為 AST/簡易解析確認 `if` 判斷式的條件運算式恰為 `Test-IsRealPython(...)` 呼叫本身、無其他 `-or`/`-and` 修飾 | open（backlog，SD 明確判定非阻擋本輪 APPROVE，有正交防線緩解） |
```

### §8.5d DEF-101-333

```text
| DEF-101-333 | 2026-07-24 | R40 二審 Architect／QA 各自獨立構造（新角度攻擊，非本輪必須修復） | **DEF-101-332 修復後仍有兩類殘留繞過向量，三方（SD/Architect/QA）分別於一二審獨立構造成立**：(a) 檔案中存在「真實但死碼」的 dot-source SSOT 陳述式，實際生效判斷邏輯是另一個完全獨立重寫的函式，`Test-IsRealPython` 只出現在從未被呼叫的死碼分支（Architect 二審構造）；(b) 把兩段魔法字串包進 PowerShell here-string（`@"..."@`）當誘餌，逐行引號奇偶追蹤不追蹤跨行 here-string 開闔狀態（QA 二審構造）。四方一致判定：這是逐行正則靜態掃描的方法論邊界，需要真正的 PowerShell AST 解析才能完全封閉，依 Rule 2 比例原則本輪不強制修復 | P3（已知限制，非阻擋；已在測試 docstring 誠實記載，防止被誤讀為「已完全防禦」） | 若未來需徹底封閉需 AST 層解析（追蹤變數賦值實際使用、正確處理 here-string 狀態機），列 R41 backlog | open（backlog，四方一致判定非阻擋，已在 `test_windowsapps_guard_cross_consistency.py::TestNoOrphanWindowsAppsImplementation` docstring 誠實記載殘留限制） 🔴 **R60 改派（round 1 QA-R60-04【1】／Scan-G G-02，CONFIRMED／P2）**：本列分流欄的「列 R41 backlog」指向 **19 輪前**，且 R60 反駁者把主檔＋全部 archive 的每一處出現逐一回讀，**零改派、零結案** ⇒ 依 `CrossPlatform_Scan_Dimensions.md:149` R59 自訂硬規則②判為**孤兒**。R60 round 2 實查標的確實未動：兩支 guard 測試雖已 `import ast`（`test_windowsapps_guard_cross_consistency.py:33`／`:1330`），但那是 `_bare_python_command_literals()` 解析 **Python** 原始碼用的，與本列要求的 **PowerShell AST**（追蹤變數賦值實際使用、here-string 狀態機）無關。**改派為：未指派 backlog**（體例比照 R59 `DEF-101-521` 對 `DEF-101-500` 的改派——不改寫歷史原文，以新條目＋就地附記載明改派）。解鎖條件：需引入真 PowerShell AST 層（`System.Management.Automation.Language.Parser` 或等效），屬方法論升級而非缺陷修復。見 DEF-101-555（現居 archive_33）。 |
```

### §8.5e DEF-101-400

```text
| DEF-101-400 | 2026-07-26 | R50 Architect 全面架構複審（跨平台相容性架構深度評估，非缺陷掃描） | WindowsApps guard 的「repo-wide 防增生掃描」測試（`test_windowsapps_guard_bash_parity.py` 682 行＋`test_windowsapps_guard_cross_consistency.py` 964 行，合計 1646 行純測試碼）呈現明顯的「正則軍備競賽」訊號：R37→R40→R43→R44→R46 五輪持續在同一支測試檔疊加更精細的逐行正則掃描，且測試檔內明文自承現存 heredoc 邊界偽裝與死碼函式兩種繞過手法「本檔不做可達性分析」「徹底解決需要真正的 bash 語法解析」，目前選擇不投資 | P3（架構層已知邊界，非缺陷；用逐行正則模擬語法解析，投資報酬率會隨每輪新繞過手法的發現而遞減——每輪修復成本遞增但覆蓋的邊際風險遞減） | 不建議現在投資 AST 解析（比例原則，尚無證據顯示現存繞過手法已被真實利用）；Architect 建議設下決策準則：若出現第 6 個繞過手法，優先評估 AST-based 掃描而非再疊一層正則特例，避免未來輪繼續無上限疊加正則特例 | open（watch item；本輪未修改任何程式碼，純粹記錄決策準則供未來輪參考，呼應本帳本既有「regex 防增生鎖有天生方法論邊界」判例） |
```

### §8.6 DEF-101-335

```text
| DEF-101-335 | 2026-07-24 | R40 一審 SD 對抗式驗證（新呼叫點碰撞情況擴大範圍，同 DEF-101-324 類別） | `hub_sync.py::diff()` 與 `counterfactual_replay.py::write_report()` 兩個新收斂的 SSOT 呼叫點同樣命中既有 DEF-101-324（`_sanitize_component()` 多對一碰撞）：`rule_id="SLV:001"`/`"SLV/001"`/`"SLV\001"` 皆淨化為同一 `SLV_001`；`ac_id="AC:042"`/`"AC/042"`/含 NUL 皆淨化為同一 `AC_042`。SD 評估：`diff()` 情境下呼叫者本就有完整檔案系統存取權，非跨權限邊界的資訊洩漏，與 DEF-101-324 既有判定同級 | P3（同 DEF-101-324 類別，四方一致判定非阻擋） | 併入 DEF-101-324 既有 backlog 追蹤，不需獨立修復 | open（backlog，記錄 DEF-101-324 命中範圍擴大至本輪兩個新呼叫點，現況與既有判定一致） |
```

### §8.7 DEF-101-348

```text
| DEF-101-348 | 2026-07-24 | R42 SA 一審提出「為何本機 pre-push hook 未攔下 DEF-101-343 的 R37 回歸」疑問，主控有限時間查證 | **待查（誠實記載，未能在本輪時限內確認確切根因）**：已確認的正向事實——本機 `git config --get core.hooksPath` 現況正確指向 `tools/git-hooks`（根層 dispatcher），該檔對 push 範圍含 `AutoClaude/` 時會正確轉呼 `AutoClaude/tools/git-hooks/pre-push`，該子 hook 第 5 步跑 `env -u GIT_DIR -u GIT_WORK_TREE python -m pytest tests/ -q --tb=short`（無路徑過濾、無 marker 子集限縮，涵蓋 `test_checkpoint_plugin.py`）；`tools/git-hooks/pre-push` 檔案 mtime 為 `2026-07-22 18:37`，早於引入回歸的 R37 commit `d7164a7`（`2026-07-24 14:59:45`），故 hooks 基礎設施在該次 commit 前即已就緒。**無法確認的部分**：該次 push 是否確實觸發本機 hook 執行（是否用 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1` 跳過）、或該次 push 的來源環境（是否為同一台本機、是否為同一份 `.git` 設定）無法從 git 版本歷史回溯還原（git 不記錄 hook 是否執行或被跳過）。**已排除的替代解釋**：`test_escalation_dump_sanitizes_step_id_with_windows_forbidden_chars`（DEF-101-343）斷言 `ch not in dump.last_log_path` 是對整條路徑字串比對；經程式碼檢視確認此斷言**只有在真正的 Windows 檔案系統路徑（含磁碟機代號 `:` 與 `\` 分隔符）下才可能觸發失敗**——若當時執行 `pytest` 的環境是 POSIX 路徑慣例（如 Linux/WSL/macOS 容器化 agent sandbox），`tmp_path` fixture 產生的路徑不含任何 `_WIN_FORBIDDEN_CHARS` 字元，此斷言會**在任何程式碼版本下都trivially 通過**，即使 hook 確實跑了完整 pytest 也不會抓到——這是本輪能給出、有程式碼層級佐證的最可能解釋，但無法回溯證實 R37 commit 當時的實際執行環境是否即為此情況 | P3（流程／方法論疑問，非程式碼缺陷；不影響本輪任何修復項的正確性） | 待查，非本輪程式碼可解 | open（待查）：若未來要徹底封閉此類回歸，建議兩個方向並行評估（留待下輪）——① 對 Windows 專屬字元/路徑類回歸測試，於 CI／nightly 層級加一道「本測試必須在原生 Windows 檔案系統下執行」的環境前提檢查（防止在非 Windows sandbox 下 trivially 通過而未被察覺）；② 稽核歷次「四方複審」round 的 push 是否確實逐次經過本機 pre-push 完整 pytest（例如檢查各輪 commit 訊息／agent 執行紀錄是否有 `--no-verify` 或 `AUTOCLAUDE_SKIP_HOOKS=1` 使用痕跡）。**R47 複驗（信心層級提升，非狀態變更）**：於 scratch git worktree checkout 出 R37 回歸引入前一支 commit `d7164a7`，對該時點『修復前』版本的 `test_escalation_dump_sanitizes_step_id_with_windows_forbidden_chars` 在本機（macOS/POSIX）原樣重跑，實測 0.97s PASSED——經驗性重現本列「已排除的替代解釋」（斷言比對整條路徑字串，POSIX 路徑不含磁碟機代號 `:` 與 `\` 分隔符，故 trivially 通過）確為可能成因，信心層級由「未經查證之理論」提升為「本機經驗重現、強化該理論為歷史 miss 之解釋」。本列真正尚待解決的一般化方法論缺口（Windows-only 才有意義的測試如何防止在其他平台 trivially 通過，涵蓋未來新測試，非本案已於 R42 修復之舊測試）仍未落地，非本輪 scope，狀態維持不變 |
```

### §8.8 DEF-101-401

```text
| DEF-101-401 | 2026-07-26 | R50 Architect 對 DEF-101-392（Copy-on-Evolve 政策）獨立再覆核（非新缺陷，補記本輪判斷升級） | 實查現況為 29 支凍結（v0.01~v0.29）＋1 支 LATEST（v0.30），與 R48/R49 記載數字一致，本輪未發現版本數異常增長，亦未發現 R49 之後出現第三次被迫打破鐵律回補的新事證。獨立判斷：DEF-101-357/358（R44/R45）兩次破例根因同構（同一份邏輯散落 N 份凍結拷貝），且凍結版本數會隨框架每次演化單調遞增、`ci-gate.sh` 從未機械觸碰中間 28 支——這是結構性、會隨時間持續復發的模式，而非低機率尾端風險 | P3（架構政策層前瞻議題，非現行缺陷；不影響任何現行測試/CI 判準） | 不修改 Copy-on-Evolve 政策本身（不屬本輪掃描修復可自行拍板範圍）；相較 R48/R49「留待未來輪視需要評估」的措辭，本輪 Architect 建議升級為「本輪即建議人工將其排入正式 ADR 決策議程」，理由：每多一輪演化，凍結版本數只會再 +1，決策基期只會更貴、不會更便宜 | open（watch item；本輪僅為獨立再覆核與建議升級，未修改任何 Copy-on-Evolve 相關程式碼或政策文件；DEF-101-392 原文依帳本「只增不刪」政策不予改寫，本列補記本輪判斷供人工擇期決策參考） |
```

### §8.9 DEF-101-412

```text
| DEF-101-412 | 2026-07-26 | R52 Architect 架構最佳化評估（使用者明確要求任務②：全面檢視多平台相容性架構設計是否合理並提出最佳化，非缺陷掃描） | Architect 對現有跨平台相容性架構六要素（dispatcher 模式／薄殼收斂模式／SSOT 收斂／Copy-on-Evolve 凍結政策／CI paths 白名單機制／缺陷帳本基線唯一站點模式）逐項查證後結論**不需大重寫**，但明確記錄一項前瞻性判準供未來輪參考：`evaluator_command` 的產生存在「同進程生成即消費」（evolution 模組，`sys.executable` 絕對路徑安全）與「編譯期產出、執行期可能跨行程/環境/機器消費」（`sdd_to_playbook_adapter.py`／`sdd_compile.py` 兩段式設計，`sys.executable` 不安全）兩種本質不同的場景，R50/R51 建立的「裸 python → sys.executable」修復慣例只適用前者；本輪 DEF-101-403 若未經 Architect 澄清此判準差異，可能被誤套用後者手法（把 rc=127 換成路徑不存在的另一種失敗） | P3（架構層前瞻判準記錄，非現行缺陷；本輪已依此判準正確處置 DEF-101-403，無需修復動作） | 建議將此判準補入 `docs/06_quality/CrossPlatform_Scan_Dimensions.md` 或等效架構文件，作為未來輪處理 evaluator_command 相關跨平台缺陷時的第一道分診問題（「此指令是同進程消費還是可能跨行程/環境重新載入？」），避免未來輪不查場景差異直接套用 R50/R51 慣例 | open（watch item；架構判準記錄，本輪未修改任何架構文件，留待未來輪視需要補入正式文件） |
```



### §8.10 DEF-101-676

```text
| DEF-101-676 | 2026-08-01 | R67 帳本收尾包自查（兩次輪替後以 `tools/archive_defect_log.py --plan` 現查餘裕） | **帳本主檔的「不可搬核心」已逼近硬線，輪替機制的可用餘裕正在結構性歸零**：R67 入帳 44 列後主檔 298365 bytes（硬線 262144）；第一次輪替搬走 34 筆本輪已結列後仍達 258995 bytes，且 `--plan` 現查**可搬 0 筆／0 bytes**（距硬線僅 3149 bytes）；第二次輪替必須動用 `--ack-handoff` 具名承認 6 筆判準④ 誤報才降到 247200 bytes。剩餘 104 列中有 96 列被判準①②③ 永久擋住（`open`／`routed` 未結，或被 crossref 掃描目標做過狀態宣稱）⇒ 每輪新增列的位元組幾乎只能靠**當輪自己的已結列**抵銷，不可搬核心單調成長。本輪若不做第二次輪替，下一輪連新增一列都會撞 `tools/check_defect_log_crossref.py` 的體積硬閘 rc=1 | P2（不影響任何程式行為，但會在下一輪把六道根層閘門之一變成無法通過的死結） | 根層帳本政策面（DEF-99-001）＋ `tools/archive_defect_log.py` 判準面 | open（承接輪次：**R82**）｜🔴 R81 瘦身＋改派（原狀態欄全文逐字保全於 `CrossPlatform_R81_Ledger_Triage.md` §5，一個字未刪）：本列自訂的雙條件（單輪吞吐 ∧ 健康餘裕**同時**成立）今日仍未滿足。本輪新證據＝開場歸檔 `archive_64` 釋出體積的同一刻，三筆超長列豁免當場過期使 crossref rc=1（已由 `DEF-101-977` 立案）⇒ 本列「輪替機制自身是單調成長源、每次釋出都要付索引與訂正成本」的論點再次成立。**本輪做不完**：結構解要動歸檔器與索引體例，非帳本清債包單輪可竟；務實下一步＝讓 `--plan` 同時印出「本次釋出 X bytes／新增索引 Y bytes／淨 Z」，淨值長期為負才是真的解 |
```

### §8.11 DEF-101-977

```text
| DEF-101-977 | 2026-08-08 | R81 開場（歸檔後閘門轉紅） | 歸檔 `--archive-num 64` 把 3 列（DEF-01-007／DEF-101-274／DEF-101-422）搬離主檔，`OVERSIZE_ROW_GRANDFATHERED` 那 3 筆當場過期、判準轉紅。歸檔器自己既不偵測也不提示，要等下一個人跑 crossref 才知道 ⇒ 每輪歸檔都復發、每輪都手動修 | P2 | 建議 `archive_defect_log.py` 在 `--plan`／`--apply` 就地列出「本次會讓哪幾筆豁免過期＋三個常數該下修到多少」 | open（🔴 R82 改派：承接輪次 **R83**；機械物須落 tools/tests，非本包持有面） |
```



---

## §9 帳本包（持有 `tools/lib/`）的接手交件

### §9.1 先判定「超長列基線是不是缺陷」——實測，不採信推論

探針把真實主檔讀進記憶體、對 `DEF-101-335` 一列做三種修改，各跑一次
`defect_ledger_index.oversize_row_problems()`（**唯讀，不寫磁碟**）。當回合逐字輸出：

```
BASE: DEF-101-335 = 843 bytes; grandfathered=True
BASE problems = 0

--- A 追加結案附記（不改原文）: 該列 975 bytes | problems=1
    存量列超標總量 139068 bytes > 棘輪上限 138936（只准往下改、零成長容忍）：既有豁免列被改長了 132 bytes。合法出口＝把該列詳情搬進具名證據檔，或在同一次變更內把別的列縮回等量以上

--- B 結案＋瘦身但仍 >700: 該列 820 bytes | problems=0

--- C 結案＋瘦身到 <=700: 該列 665 bytes | problems=1
    DEF-101-335：列在 OVERSIZE_ROW_GRANDFATHERED，但主檔實測665 bytes ≤ 700⇒ 豁免已過期，請把它從清單移除並同步下修 OVERSIZE_ROW_CEILING 與 OVERSIZE_ROW_EXCESS_CEILING——留著就是日後無聲加回去的額度
```

**裁決**：那條基線**不是**「已存在的超長列連狀態字都不准改」——B 證偽了它（0 problems，
零常數改動）。它是「**列不准變長**」，而結案的正確形態本來就會讓列變短。方向是對的：
它懲罰改派（追加位元組）、獎勵結案（搬走長文）。⇒ 不修判準④，**避免為了讓自己好做事
而把一條方向正確的鎖鬆掉**。

### §9.2 真正壞掉的那一半：三條棘輪的「只准往下改」零觀測者（`DEF-101-993`）

上面那三條基線的散文自 R79 起逐輪寫著「**只准往下改、零成長容忍**」。第二支探針問的是
「那句話有沒有人在看」——把一列改長 85 bytes，**然後把常數調高到新實測值**：

```
目前常數=138936  改長後實測 excess=139021 (+85)
① 不調常數： 1 problems
② 把常數調高到新實測值： 0 problems  <-- 0 就代表沒有觀測者
③ exact 自檢 test_the_real_ledger_baselines_are_exact_not_padded 會不會紅： 不會（全綠）
```

⇒ **零觀測者，而且唯一釘住常數的那支測試是幫兇**：它斷言「常數 == 當回合實測」，所以帳本
一長，它**要求**你把常數調高。三條棘輪因此只擋得住「忘了重釘」，完全不擋「往上重釘」——
而後者正是砸溫度計的那個動作。

**修法**＝把重釘史做成 append-only 的具名序列並判它單調不增，家在
`tools/lib/ledger_rotation.py`：

- 往下釘（追加更小的數）⇒ 綠；往上釘 ⇒ 紅並逐字指名是哪一段、升了多少；
- 改了常數卻不追加史料 ⇒ 末元素與常數不符 ⇒ 紅（否則史料是裝飾品）；
- 空序列 ⇒ 紅（fail-closed，沒有起算錨就無從判方向）。

刻意**不留豁免出口**，也刻意**不**混進 `oversize_row_problems()`：那支的注入測試會把常數
mock 成別的值，混進去等於讓判準的比較對象隨被它所判的動作而變（R75 已立的鐵律）。
呼叫點在 `main()` 內**無條件**執行（與 `grandfather_ceiling_problems()` 同一個理由：
換一本帳本不該能繞過對原始碼常數的斷言）。

紅綠兩向自證：`tools/tests/test_check_defect_log_crossref.py::TestR82RatchetDirectionLock`
（8 支，含一支重演立案時那個「調高到新實測值就全綠」的實際繞道）。

### §9.3 `DEF-101-977`／`DEF-101-676`：歸檔器兩個副作用的預告

兩者同一種病：**歸檔器改變了下游判準的輸入，卻讓下游的人去發現後果**。修法都是純讀計算
（不改判準、不寫檔 ⇒ 不可能製造新的紅），落在 `tools/lib/ledger_rotation.py`、由 `--plan`
與 `--apply` 共用同一份數字：

- `expiring_oversize_waivers()`：逐筆預告「本次會讓哪幾筆豁免過期」＋三個常數該下修到多少。
- `net_volume_triple()` ＋ `rotation_effect_report()`：印出「釋出 X／新增索引 Y／主檔淨變化 Z」。

🔴 **符號寫反被自己的測試抓到**：第一版把 Z 定成 `X−Y` 並把 `z < 0` 標成「真的釋出了容量」，
方向剛好相反。`DEF-101-676` 原文逐字是「**淨值長期為負才是真的解**」，那個「淨值」指的是
**主檔的淨變化**（`Y−X`），不是「釋出減新增」。這是 R79「量測器指標可能符號相反」的同型：
算式看起來對稱，**只有把它綁回一句外部的定性宣稱才判得出方向**。回歸鎖＝
`TestR82RotationSideEffectsAreAnnounced::test_the_sign_is_bound_to_the_ledger_rows_own_wording_not_to_the_formula`
（雙向：搬得多 ⇒ Z 負且說「真的釋出了容量」；寫回去得多 ⇒ Z 正且說「沒有真的釋出容量」）。

### §9.4 `DEF-101-994`：新增一列 `DEF-101-993` 之後，歸檔器測試當場轉紅

`tools/tests/test_archive_defect_log.py` 的沙箱合成列 ID 寫死 `101-`＝**真實帳本正在使用的
家族號**（合成號 992／993／996／997）⇒ 帳本號碼一路加上來就會與合成列撞號。實測：帳本落地
`DEF-101-993` 的那一刻，`test_apply_auto_registers_exactly_one_bullet` 立刻 rc=1，而失敗訊息
是「自動註冊後判準⑤ 仍紅 ⇒ 註冊的 bullet 樣式不被解析」——**與真因（ID 撞號）毫無關聯**。
修法＝抽 `_SYNTH_FAMILY` 常數並改為 `999-`，五個站點共用；合成與真實不再共用號碼空間。

### §9.5 本包的位元組帳（誠實揭露升與降兩邊）

| 量 | 開場 | 收尾 |
|----|-----|-----|
| 未結列數 | **83**／141 列 | **69**／143 列 |
| 帳本主檔 bytes | 240,097 | **225,272** |
| `OVERSIZE_ROW_CEILING` | 98 | **85** |
| `OVERSIZE_ROW_EXCESS_CEILING` | 138,936 | **123,867** |
| `_UNPINNED_HANDOVER_CEILING` | 17 | **6** |
| 具名治理文件 | 24 份 | **25 份**（本檔補登記） |

三條棘輪**全部往下**。淨額的**升**那一側逐筆寫出來，不用「淨額仍下降」蓋過去：
`DEF-101-268`／`324`／`392`／`886` 各追加一句「我吸收了哪一列」（109~210 bytes，這是併列
結案的資訊零損失義務）；`DEF-101-977` 因寫入回執長 66 bytes；`DEF-101-676` 降級為
`partial` 之後**仍是未結列**，硬規則② 因此要求它二擇一，「未指派＋可執行的解鎖條件」
本身又長回 293 bytes。

### §9.6 本包沒有做、也不該由本包做的（具名交棒）

🔴 **下面兩條的「紅／綠」是量測值，本節不再把它寫成常數**（R82 收尾訂正）。此前這兩條各自
逐字宣告「仍紅」並附了一份**寫死的違規站點清單**，而兩者在同輪內都已漂移：一條的違規集合被
並行包換掉了（筆數與檔案分佈全變），另一條已被收斂成綠。清單本身就是會過期的東西，
**每一條都改成「現查指令 ＋ 收尾當回合讀數」**：

1. **`test_no_code_file_claims_a_round_beyond_the_ledger`**——收尾當回合 **rc=1（紅）**
   （2026-08-09）。🔴 **違規集合在單一收尾窗口內就換過兩次**，所以本節**不再登記任何一份
   清單**：同一天相隔數分鐘的兩次量測，第一次 **26 筆**（來源以並行包的額度軸產出為主，
   橫跨 `.claude/hooks/`／`tools/lib/`／`tools/tests/`／`AutoClaude/**`），第二次只剩 **3 筆**
   且**檔案完全不重疊**（換成另一個並行包剛落地的機密外洩防線）。⇒ 這一列的內容物是
   「別人鍵盤的函數」，把它抄進文件就是製造下一句假話（本節原先那份 9 筆清單正是這樣過期的）。
   **紅這件事**與**紅在哪裡**要分開讀：前者本包動工前就成立、且**沒有一筆在本包持有面**；
   後者一律現查，不抄：

   ```powershell
   Push-Location "$r\tools\tests"; & $p -m unittest test_check_defect_log_crossref -k test_no_code_file_claims_a_round_beyond_the_ledger; Pop-Location
   ```

2. **`test_no_root_test_asserts_absence_against_a_whole_live_document`**——收尾當回合
   **rc=0（綠）**（2026-08-09）。此前登記的單一站點 `test_mac_readiness_r82.py:88` 已被
   同輪的具名豁免收斂掉。現查：

   ```powershell
   Push-Location "$r\tools\tests"; & $p -m unittest test_archive_defect_log -k test_no_root_test_asserts_absence_against_a_whole_live_document; Pop-Location
   ```
3. **`DEF-101-400` 的「已知繞過手法計數」目前只有登記、沒有機械物**：五個手法逐個具名在
   §8.5 各列原文內（#1 decoy 註解／#2 未錨定 search＋行內註解／#3 呼叫端 `-or` 覆蓋／
   #4 死碼 dot-source／#5 here-string 誘餌），觸發門檻 6。要把它變成可查的量測值必須動
   `tools/tests/test_windowsapps_guard_*.py`，非本包持有面。
4. **`tools/lib/skip_group_policy.py` 餘裕 0 行、`tools/session_resume_planner.py` 餘裕 1 行**
   （`check_loc_budget` warn 帶）：不是本包造成，但下一個要動那兩支檔的人會當場破線。

---

## §10 R82 收尾（文件面）對抗稽核的四筆處置

> 本節由**收尾的單人窗口**寫，作者不是 A5 包本人。體例沿用本檔既有紀律：
> 每一筆先貼當回合真跑的輸出，再寫處置；沒重跑過的一律標「引用他包」。

| # | 稽核者的發現 | 本節作者當回合複驗 | 處置 |
|---|---|---|---|
| (a) | `tools/lib/ledger_rotation.py` 的 `ratchet_history_problems()` 有繞道：「往上釘且**改寫**史料末元素」全綠 | **成立，且比稽核者報的更寬**（見下方探針四組對照） | 立 `DEF-101-995`（open，承接 **R83**）。程式面不在文件包射程 |
| (b) | 帳本 `:36` 與 `:181` 指向的結案憑證檔名在磁碟上不存在 | **成立**：`Test-Path` 對 `AutoSDD_R82_Ledger_Closure.md` 回 `False`、對 `CrossPlatform_R82_Ledger_Closure.md` 回 `True`；全檔 2 個壞指針（`:36`／`:181`）對 16 個正確指針 | **當回合修畢**（兩處改名）。`DEF-101-992` 列改後 690 → 696 bytes，仍在 700 線內 |
| (c) | `DEF-101-308` 結案理由含可證偽的假話 | **成立**（逐字反證見 §8.5-R82） | **當回合修畢**：只換理由、不改狀態；帳本列改後 673 → 699 bytes |
| (d) | 交件的 closed 清單少報 3 筆 | **成立但性質不同於稽核者的描述**：`234`／`925`／`961` 的複驗憑證本來就在 §2.1／§2.2／§2.4，漏的是 §8 標題讓人以為它是完整清單，且標題寫死「13」而底下有 15 個子節 | **當回合修畢**：§8 標題不再寫死條數 ＋ 補完整性註記 |

### 10.1 (a) 的探針：四組對照（當回合真跑，`ratchet_history_problems()` 直接呼叫）

```
REAL OVERSIZE_ROW_CEILING_HISTORY = (105, 101, 98, 85)
append-down (105,101,98,85)->85    : []                      # 綠（正確：沒動帳本就重釘同值）
append-up   (105,101,98,85,90)->90 : ['X 的重釘史第 3 -> 4 段由 85 **上升**到 90（+5）…']   # 紅（正確）
REWRITE-last(105,101,98,90)->90    : []                      # 🔴 綠 —— 稽核者報的那條繞道
truncate    (999,)->999            : []                      # 🔴 綠 —— 本節作者另外找到的、更寬的一條
```

`truncate` 那一組是本節新增的發現：**把整段史料砍成單一高值元素也是綠的**。
判準只看「相鄰段不上升」＋「末元素 == 現值」，兩者對「史料本身有沒有被抽換」零判準
⇒ 這條棘輪能擋的只有「老實追加一個更大的數」這一種寫法。

而 `tools/lib/ledger_rotation.py:35` 逐字訂了取值紀律（每個元素都是當時的實測值、
歷史不得回填不得改寫）——**規則寫在原始碼註解裡，觀測者一個都沒有**。
這正是本 repo 判過多次的形狀：`DEF-101-993` 才剛因為「散文自稱 shrink-only 而零觀測者」
立案並補上方向鎖，**補上去的那把鎖自己又留了同一種縫**。

🔴 **修法方向（給 R83 的程式面收尾者，本節只給方向不給實作）**：判準要能分辨「追加」與
「改寫」，也就是**已釘過的前綴必須不可變**。可行形狀之一是把每次重釘的值連同輪號一起
釘成具名序列，並斷言新序列的前 n−1 項與舊序列逐字相等（＝只准延長）。
⚠️ 別把它做成「與當回合實測相等」——那正是 `DEF-101-993` 記載的那個幫兇形態。

### 10.2 收尾單人窗口的帳本數字（本節作者當回合實測，非引用）

§7.1 那張表是 **A5 包自己那個窗口**的讀數（開場 85 → 收尾 83／141 列），
本節不改寫它——那是另一個時點的量測值，改寫等於抹掉 A5 那一段的痕跡。
本輪**最終**（所有包停工後的單人窗口）讀數如下：

```
> python tools/check_defect_log_crossref.py --unresolved-count
未結列數＝70／全部 144 列｜warn=86 fail=98      # rc=0
> python tools/check_defect_log_crossref.py
                                               # rc=0（全套閘門）
```

**70 而不是 69**：本節作者為 (a) 立了 `DEF-101-995` 一列（open）⇒ 未結數 +1。
誠實記在這裡，不藏進「本輪淨降 15」那個好看的數字裡。
開場 85 → 收尾 **70**（淨降 15），其中本節作者的貢獻是 **−0／+1**。
