# R90 交棒書 — 多包並行輪（§0.0 為靜止樹憑證；其餘標「量測於 HH:MM:SS」者量於**非靜止樹**）

## 🟢 0.0 靜止樹憑證（收尾單人窗口補寫；**唯一有效的一組數字**）

> 本節由 **R90 收尾單人窗口**在八包全部停工後量得。四方複審已認定移動標的上的數字不具憑證力
> ⇒ **本節的值取代 §1 全部同名數字**（NEW-5／S-2 的兌現）。§1 各值保留為「移動樹讀數」的史料，
> 讀者不得引用它們當收輪憑證。逐條原始整行見〈附錄 Z：靜止樹憑證原始輸出〉。

| 座標 | 值 |
|---|---|
| 量測窗 | 2026-08-15 15:07 起（+08:00），**單一工作者，八包全數停工** |
| HEAD | `be53ff0e2d524bb34e341e1987690b2ace4c1e18` |
| dirty 檔數 | 進場 **23**（20 modified + 3 untracked）→ 收尾窗口自身改動後 **26** |
| 六道憑證 | root unittests `OK (skipped=44)`／pytest `4623 passed, 62 skipped`／lint-imports `9 kept, 0 broken`／crossref rc=0／未結 91／LOC total=20417 —— **六道全 rc=0**，原始整行見〈附錄 Z〉 |

<!-- guard-total:R90 --> **本輪護欄層累積淨額＝ 83578 → 83739（+161）** —— 前段包 +149
（`test_quota_policy.py` +124／`test_context_budget_guard.py` +25）＋ 收尾窗口重釘自身的稽核列 +12。
逐檔清單與「為何判定壓不動」的三條出口實查＝`docs/06_quality/CrossPlatform_R90_Guard_Repin_Evidence.md`。

### 0.0a 收尾窗口補上的四件事（前段各包點名要收尾做的）

| # | 事項 | 落地處 |
|---|---|---|
| A | **ADR-XPLAT-002 R90 列的「18 支紅」補座標** | 該列現載「量測於 2026-08-15 約 14:0x–14:3x、`HEAD=be53ff0`、當時 dirty 17~19 且仍在增長」，並明文「不得引用『18』除非同時引用座標」 |
| B | **包數低估訂正** | 同一列由「四線」訂正為「至少 5 條線（帳本／A／B／C／D）＋包 E＋旁測＋編纂＝**全輪 8 包**」 |
| C | **包 E 的帳本列** | `DEF-200-130`（承接輪次 R91，由收尾窗口代寫——包 E 禁碰帳本）。🔴 **與包 E 自陳的一處出入照實記**：注入自證 `^def test_injection_` 實查 **12 支**，包 E 自陳 14；差 2 未解 |
| D | **包 E 的可裁事項** | 見 §0.0b |

### 0.0b 🔴 待四方複審裁決：`unmeasurable ⇒ 紅` 的 flaky 風險（包 E 提出，收尾窗口複核）

**包 E 的自陳**：三態中 `unmeasurable` 目前判紅（fail-loud）。風險是「宣告了
`SD07_REAL_PG_E2E_ENABLED=true` 但 DB 中途掛掉」會讓閘門轉紅，而那不是欠債狀態改變。
包 E 自陳「這是判斷不是實測結論，可以裁」。

**收尾窗口複核（讀 `AutoClaude/tests/test_conftest_windows_native_skip_report.py` 實作後）**：

1. **風險為真，但射程比包 E 說的窄。** 探針只在 `SD07_REAL_PG_E2E_ENABLED=true`
   **且**連線／查詢拋例外時才回 `unmeasurable`（`test_injection_real_probe_reports_unmeasurable_when_the_query_dies`）；
   未宣告啟用的機器一律 `blocked` 且**不連任何 DB**（`test_injection_real_probe_is_blocked_without_the_env_declaration`）。
   ⇒ 對本輪的 mac 開發機與所有 CI job（皆未宣告啟用），這條路**結構上走不到**，今天的 flaky 面是空的。
2. **本 repo 對「量不到」已有一條相反方向的既有判例**，不可忽略：額度軸「量不到＝**不節流**」是
   刻意選的 fail-open，理由是「猜一個值會製造沒有出處的數字」。兩者不矛盾——那一條的代價是
   「多派幾個 agent」，這一條的代價是「把一筆真實欠債讀成已還」，後者不可逆。
3. **建議：維持 fail-loud，但把 flaky 面收成可觀測的。** 不改判準；改為要求
   `unmeasurable` 的紅燈訊息**逐字帶出探測失敗的例外文字**，讓「DB 掛了」與「債狀態變了」
   在紅燈當下就分得開。理由：把它改成放行等於讓一個宣告啟用卻連不上的環境**靜默**跳過欠債稽核，
   而那正是 `DEF-200-112` 這一族缺陷的原始形狀。

🔴 **本節是建議，不是裁決**——依 CLAUDE.md〈四方審查閉環〉，最終裁決由四方複審做。

### 0.0c 成熟度 M1~M6（判準 SSOT＝[`CrossPlatform_Maturity_Criteria.md`](../06_quality/CrossPlatform_Maturity_Criteria.md)）

🔴 **一格都沒有塗綠**。R89 的判例：M6 是「**不可求值**」不是「量到 0」，那是該判準與 fail-open 的分界線。

| # | 判定 | 憑證（皆量於本輪靜止樹） |
|---|---|---|
| **M1** | ❌ | **合取兩半，兩半都不成立**。①UEP 半：`[Scan-H triplet] UEP=5`；ADR-XPLAT-002 §8.1 回執表**列數＝0**（現查該小節，唯一一列是「（尚無回執…）」佔位列），且 ADR 也未宣告 UEP=5 為終態 ⇒ 不成立。②護欄行數半（門檻＝總量連續三輪不上升）：`repin_round_nets()` 現查 R88 **+60**／R89 **−92**／R90 **+161** ⇒ 本輪上升，連續計數歸零 ⇒ 不成立。🔴 **相對 R89 是退步**：R89 曾是「三輪中的第 1 輪」，本輪把它打回 0 |
| **M2** | ❌ | 門檻＝**連續三輪** ≤1 筆且無 P1。①分母＝本輪新帳本列 **5**（`DEF-200-126`~`130`，現查「發現情境」欄提及 R90 的列）。②分子：本輪各包互駁 ＋ 收尾窗口複核合計 ≥4 筆被實測推翻的宣稱（包 C 漏報 `1 failed`／包 A 落款 R89／Architect N3 的 86,901 與量測面不同源／SA N-7 本機不可重現／包 E 自陳注入自證 14 而實查 12／S-1 寫 +149 而實際 +161）。③🔴 **「連續三輪」在結構上不可求值**：R87／R88／R89 三輪皆因額度 halt 而無四方複審，依判準①「未執行四方複審一律判 N/A、禁記 0」 |
| **M3** | ❌ | 門檻＝**第三方**注入 100% 連續兩輪，且抽樣面含既有鎖庫隨機 20 支。現查 `ls docs/06_quality/ \| grep 'R90_Review'` 為**空集合**（本輪只有 `CrossPlatform_R90_Guard_Repin_Evidence.md` 與 `Quota_R90_CrossAccount_Experiment.md`）⇒ 本輪各包新增判準的注入紅綠**全部是作者自證**，依判準「作者自證不計分」第三方分子為空。既有鎖庫隨機 20 支抽樣自 R76 立案至今仍是本判準最大量測缺口 |
| **M4** | ❌ | 門檻＝一輪 0 筆。本輪實測 ≥3 筆「宣稱射程 ≠ 實作射程」：①ADR R90 列把並行包數寫成「四線」而實為 8 包；②交棒書 S-1 把重釘寫成 `+149` 而實際 `+161`（漏算稽核列自身佔的 12 行）；③包 E 自陳「14 支注入自證」而 `^def test_injection_` 實查 12 支。三筆皆已就地訂正 |
| **M5** | ❌ | 現跑載具（**本輪真的跑了**，非「未量」）：`[Xplat injection matrix] Win2mac=8/12 mac2Win=5/10` ⇒ **未攔到題數 Win2mac=4／mac2Win=5**，門檻是兩向各自 ≤1 且連續三輪不回升 ⇒ 兩向皆遠未達標。質性缺口沿用判準表所載：Win→mac 命中全在檔名／路徑／編碼層，**程式碼語意層仍是 0** |
| **M6** | ❌ | 逐字：`[M6 id 集合] tools/tests@darwin：⚠️  不可求值（**不是**通過）（本次 skip 44 支）`。成因現查 `docs/06_quality/skip_id_ledger.json`——頂層鍵只有 `_why` 與 `tools/tests@darwin`，**`tools/tests@win32` 這個剖面沒有 id 落款** ⇒ 判準第③條「三態必須是 `ok`」不成立。🔴 **這是「不可求值」不是「量到 0」**，兩者的差別正是本判準與 fail-open 的分界線。距離＝在一台真 Windows 機器上跑同一支 runner，把它印出的可貼落款填進該 JSON。本輪是 mac 輪 ⇒ 結構上做不到，且依 §2-2 掌舵者裁決，這一項**不該再用輪號記**，應改用平台條件記（同包 E 對 pgvector 那批的處置）。**AutoClaude 那一棵的計數面本輪已補量**（見 Z-7）：`共 62 支：platform=53／tool-absence=3／env-disabled=2／structural-pair=1／debt=3／untagged=0／欠債型 8 支（目標 0）`，`CENSUS_TRUE_RC=0` ⇒ 計數面綠、**集合面仍缺 win32 剖面**，兩者不可互相替代 |

**總判：0 / 6**，與 R80~R89 相同。

🔴 **本輪相對 R89 的兩個方向都要說**：
- **前進**：M5 本輪**真的跑到了**（R86 那一輪是「一次都沒跑」）；M2 的分母第一次是現查值而不是估計。
- **退步**：M1 的護欄行數半由「三輪中的第 1 輪」被本輪的 +161 打回 **0**——而那個 +161 是本輪合法且必要的重釘（見 §0.0 與重釘證據檔），**不是有人偷加行**。這兩件事同時為真，且它們的張力就是 M1 存在的理由。

> **本檔由 R90 交棒書編纂包撰寫，不是主控撰寫。** 理由記在這裡，因為它是本檔的可信度前提：
> 主控本輪在事實上被六個包駁回過（宣稱時鐘推到 R90／cap 語意混用／extras 分歧數字／
> 「五項交付」／判準檔名寫錯／讀交棒書到 245 行就停）。〈可重啟點四條件〉第 3 條要求
> 任務書必含「已驗證什麼（**附實測數字與 rc**）」，而主控轉述的宣稱結構上不滿足它。
> ⇒ **本檔每一條「已驗證」都附本包當回合真跑的輸出；驗不到的一律寫「未驗證」。**

---

## 🔴 0. 讀本檔之前必須先知道的三件事

### 0.1 本份數字量於**非靜止樹**，收尾包必須在靜止樹重量

量測窗＝**2026-08-15 14:38:25 ～ 14:41:13（+08:00）**，`HEAD = be53ff0e2d524bb34e341e1987690b2ace4c1e18`。

**工作樹在量測期間真的在動**，這不是理論風險，是本包實測到的事實：

| 時刻 | `git status --porcelain \| wc -l` | 證據 |
|---|---|---|
| 14:38:25 | **19** | 17 modified + 2 untracked |
| 14:40:03 | — | `git diff --stat` 已含 `AutoClaude/tests/test_conftest_windows_native_skip_report.py`，該檔在 14:38:25 那次列舉中**不存在** |
| 14:40:17 | **20** | 同一棵樹、兩分鐘內多一支檔 |
| 15:00:19 | **23** | 又多 3 支（其中 1 支是本檔自己）⇒ 22 分鐘內 19→23 |

**包 E 當時仍在飛**（掌舵者裁決「平台綁定的欠債改用平台條件記」）。四方複審本輪已一致認定
**移動標的上的數字不具憑證力** ⇒ 本檔所有數字都標了「量測於 HH:MM:SS」，
**收尾包必須在所有包停工後的單人窗口重量一次**，不得引用本檔的值當收輪憑證。

### 0.2 本包在自己身上重現了鐵律六「讀 rc 時接管線」

本包第一次跑 AutoClaude pytest 時寫的是 `python -m pytest tests/ -q 2>&1 | tail -25; echo "PYTEST_RC=$?"`，
螢幕上印出 **`PYTEST_RC=0`**。**那個 0 是 `tail` 的 rc，不是 pytest 的。** 同一次執行的摘要行逐字是
`1 failed, 4607 passed, 62 skipped`——**rc 真值是 1**。不接管線重跑後 `TRUE_RC=1`。

⇒ 這正是 CLAUDE.md 鐵律六表中「讀 rc 時接管線」那一列所描述的形態，而該列**在 Bash／zsh 側今天零攔截器**
（`DEF-200-086` 已立案）。本包是它的又一筆真實樣本：**寫下這條紀律的 repo 裡，讀這條紀律的 agent 照樣踩了。**
下一輪要引用本檔任何 rc 時，請先確認那個 rc 不是管線末端的。

### 0.3 帳本時鐘現查為 **R90**（主控這一條被駁回，但磁碟站在主控這邊）

```
current_round = 90     # 權威源＝tools/check_defect_log_crossref.py::current_round，量測於 14:39:09
```

本包據此判定：**「主控宣稱時鐘推到 R90」這條駁回，就磁碟現況而言不成立**——時鐘確實已在 90。
（駁回可能針對的是「主控在時鐘尚未推進時就先宣稱」這個**時序**問題，那是另一回事，本包無法從磁碟複驗時序。）
🔴 這一條有下游後果，見 §1.2 的 pytest 紅。

---

## 1. 已驗證什麼（每一條附本包當回合實測）

### 1.1 相符的宣稱

| 宣稱（來源包） | 實測 | 判定 |
|---|---|---|
| 未結 **90** 列／總 **206** 列（帳本包） | `未結列數＝90／全部 206 列｜warn=86 fail=98`，**rc=0**，量測於 14:38:31 | ✅ **逐字相符** |
| LOC `total` = **20417**（包 C） | `total = 20417`／`cap = 20438`／`baseline = 17032`／`total_violation = False`，**rc=0**，量測於 14:38:37 | ✅ **逐字相符** |
| pytest **4607 passed／62 skipped**（包 C） | `1 failed, 4607 passed, 62 skipped in 103.93s`，量測於 14:38:23–14:40:07 | ⚠️ **passed／skipped 兩數逐字相符，但漏報一筆 failed**，見 §1.2 |
| PRD `:79` 補通道限定詞（包 B） | `:79` 現含「🔴 **通道限定（R90 補；語意不變，只補「它住在哪」…）**」，逐字指向 `anthropic-ratelimit-unified-status` 與四通道 0 命中，量測於 14:39:20 | ✅ **相符** |
| PRD `:1372` 補通道限定詞（包 B） | §15.5 紅線 7 現含同族限定詞，並逐字寫出「照本條字面寫出的枚舉分支會是一段永遠走不到的死碼」，量測於 14:39:20 | ✅ **相符** |
| 建 `Quota_R90_CrossAccount_Experiment.md`（**331 行**）（包 B） | 檔存在，`331` 行／17,769 bytes／mtime 14:00，量測於 14:38:50 | ✅ **逐字相符** |
| `quota_meter.py` 接上 `is_active`／`severity`（包 A） | `:422-423`／`:433-434` 兩處 `item.get("is_active")`／`.get("severity")` 真的在寫入；`:687-688` 在印出。檔頭 `:354` 逐字自陳「本輪補上的是**接好卻沒有電的線**」，量測於 14:38:51 | ✅ **相符**（🔴 但檔頭落款寫 **R89** 不是 R90，見 §1.3） |
| §6b 補 `:879`（包 D） | `R89_HANDOFF.md:373` 現含 `OVERAGE_MONTHLY_UTILIZATION_HALT=80` 全段，並逐字記載「寫下本列之前全 repo 只有 PRD `:879` 一處…寫下本列之後變成兩處」，量測於 14:39:29 | ✅ **相符** |
| §6a.1 修憲登記簿（包 D） | `R89_HANDOFF.md:336` 標題逐字為「### 6a.1 🔴 待背書：R90 已對 PRD 落下的兩處改動（**修憲動作登記簿**）」，量測於 14:39:29 | ✅ **相符**（注意：字串是「修憲**動作**登記簿」，搜「修憲登記簿」會 0 命中） |
| SC-10 需當前輪覆蓋列（包 D／ADR-XPLAT-002） | ADR 內 `\| R89 \|` 與 `\| R90 \|` **兩列皆存在**，量測於 14:39:51 | ✅ **相符** |
| 旁測 3：autocompact 開啟 | `harness autocompact 開啟`／判定鏈兩條皆「未設＝採用預設 true」／**rc=0**，量測於 14:40:04 | ✅ **相符** |
| 旁測 2：哨兵已武裝 | `launchctl list` 命中 `AutoSDD_Sentinel_7878baa8-0c63-43b4-8416-4cd63a7cbe8a`（status 0），量測於 14:40:04 | ✅ **相符**（🔴 但「reset 後續跑」仍未驗，見 §4） |
| 重釘目標 **83578 → 83727（+149）**（收尾包待辦） | `--print-guard-lines` 尾段逐字印出 `# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 83578, 83727, +149, "<理由>"),`；獨立加總＝**64 支檔／sum 83727**，量測於 14:39:09 與 14:40:56 | ✅ **逐字相符**，且 offender 已具名：`test_quota_policy.py +124`／`test_context_budget_guard.py +25`（合計 +149） |

### 1.2 🔴 本包最重要的一筆駁回：包 C 漏報了一筆 pytest 紅

包 C 宣稱 `4597 passed／73 skipped → 4607 passed／62 skipped`。
**passed 與 skipped 兩個數字逐字正確**（本包獨立重跑得到同樣的 4607／62），
**但同一行摘要還有 `1 failed`，包 C 未提。**

```
量測於 14:38:23–14:40:07（103.93s）
1 failed, 4607 passed, 62 skipped in 103.93s (0:01:43)
FAILED tests/test_conftest_windows_native_skip_report.py::test_every_debt_handover_round_is_still_in_the_future
真 rc = 1（不接管線重讀；接管線時讀到的是 tail 的 0，見 §0.2）
```

**紅的內容（單檔重跑，量測於 14:40:36，`TRUE_RC=1`）**：

```
AssertionError: 以下 `[DEBT]` 的承接輪次已經追平／落後於當前輪 R90：
  [('integration/test_pgvector_hnsw_recall.py', 221, 90),
   ('integration/test_pgvector_hnsw_recall.py', 263, 90),
   ('integration/test_pgvector_real_recall.py',  271, 90)]
```

**歸因（本包判讀，交下一輪複核）**：這**不是**包 C 造成的，是 §0.3 那個時鐘推進的**下游後果**——
三筆 pgvector `[DEBT]` 的承接輪號寫著 R90，而時鐘一走到 R90，它們就從「未來」變成「追平」。
判準檔自己列出的合法出口只有兩條：①把欠債做掉；②**在同一個 commit 顯式把輪號往後推並說明為什麼**。
而 R88 已判定（`DEF-200-112`）**pgvector 那批只可能在 Windows 輪轉綠**（PG17+pgvector staging 只有 Windows 11 環境有）
⇒ 本輪是 mac 輪，出口①結構上做不到 ⇒ **只剩出口②，且必須寫明理由**。這件事沒有人認領，見 §3。

🔴 **同一支檔在兩次量測之間從 1 紅變成 2 紅**（14:40:36 單檔重跑：`2 failed, 6 passed`，多出
`test_the_handover_scan_surface_is_not_silently_empty`）——因為**包 E 當時正在編輯這支檔**。
這是 §0.1「移動標的」最直接的證據，也是為什麼本檔的 pytest 數字**不得**當收輪憑證。

### 1.3 次要駁回三筆

1. **包 A 的落款是 R89 不是 R90。** `tools/lib/quota_meter.py:354` 逐字為「🔴 **R89**：`is_active`／`severity` 是純觀測欄位，
   本輪補上的是『接好卻沒有電的線』」，`:683` 同樣落款 R89。接線本身**確實存在且正確**（見 §1.1），
   但**落款輪號與帳本時鐘（R90）不一致**。CLAUDE.md 記載有一道「輪號超前鎖」（程式碼註解寫的輪號 > 帳本當前輪即紅），
   本例是**落後**不是超前 ⇒ 今天不會轉紅，但下一輪讀到它的人會誤以為這是上一輪的舊碼。**本包未修**（不在持有面）。
2. **Architect N3 的「護欄層 86,901 行」與本包量到的 83,727 不是同一個數。** `--print-guard-lines` 加總＝
   **64 支檔／83,727 行**（量測於 14:40:56），而 N3 引用的是 86,901。兩者差 3,174。
   本包**無法判定哪個對**——極可能是兩種不同的掃描面（`_FROZEN_GUARD_LINES` 登記面 vs 某個更寬的 glob）。
   ⇒ **下一輪要動 N3（給護欄層總量帽）之前，必須先把「護欄層」這個詞的量測面定義清楚**，
   否則會做出一個分母不明的帽子。這一條本身就是待派項，見 §3。
3. **Architect N1／SA N-7 的「`install_hint()` 在 uv venv 下印出必壞指令」在本機不可重現。**
   本機 `.venv` 是 **`python -m venv` 建的**（`pyvenv.cfg` 逐字 `command = … -m venv …`）且
   **`pip 26.2.1` 存在**（量測於 14:41:04，rc=0）⇒ `run_root_unittests.py:426` 回傳的
   `python -m pip install '<pkg>'` 在**這台機器上是可用的**。
   該缺陷的 bug class（uv venv 無 pip 模組）在 CLAUDE.md 有明文記載，**但本輪無法以本機證據支持它** ⇒
   派工時要標成「依文件記載立案、**本機不可重現**」，不得寫成「已實測」。

### 1.4 額度與 context 現況（量測於 14:38:38，來源＝cache，`量測於=2026-08-15T14:38:24+08:00`）

```
--pace   rc=0：現在可派 1 個 agent（硬上限 cap=1）｜band=prepare｜最緊＝five_hour 41% 剩 201 分鐘
         reset 在 2026-08-15T10:00:00Z（＝18:00 +08:00）
         此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆
--check  rc=0：used 742,681 / window 1,000,000 ⇒ **74.3%**（低於 75%）
         model=claude-opus-5，window 為推斷值（settings 帶 1m 標記，已與逐字稿實跑 model 交叉核對）
```

**燃燒率：本包取到兩點，主控的宣稱在量級上成立、但其精度不可支持。**

| 取樣（`--pace` 自報的 `量測於`） | five_hour 已用 | 距 reset |
|---|---|---|
| 2026-08-15T14:38:24+08:00 | 41% | 201 分鐘 |
| 2026-08-15T14:42:49+08:00 | 43% | 195 分鐘 |

⇒ Δ = **2pp / 4.42 分鐘 = 0.452 pp/分**。主控稱 **0.494 pp/分** ⇒ **量級相符**（差 ~9%）。

🔴 **但「0.494」這個三位有效數字在結構上取不到**：來源百分比是**整數截斷**的，
2pp 的差在 ±1pp 量化誤差下對應的真實區間約 **0.23 ~ 0.68 pp/分** ⇒
**只可說「約 0.4~0.5 pp/分」，不可寫成 0.494。** 這與本 repo 對「Token%→Reset `int()` 截斷」的既有認識同源。

依 0.452 pp/分外推：剩 57pp ⇒ 約 **126 分鐘**燒完，而距 reset **195 分鐘**
⇒ **本窗約在 reset 前 69 分鐘見底**（主控稱 78 分鐘，同樣量級相符、精度不可支持）。

（另注意：`--pace` 讀的是 TTL 180s 的快取，手動連續查詢多半落在同一格 stale 帶，`DEF-200-105` 已立案；
本包兩次取樣間隔 265 秒 > TTL，故確實跨了兩格，不是同一個快取值被讀兩次。）

### 1.5 本包未能複驗的宣稱（誠實劃界，詳見 §5）

- 帳本包的「92→86→90（後段 +4 新列）」**過程**：本包只量到**終值 90**，中間兩個值是歷史狀態，磁碟上量不到。
- 帳本包的「27 列孤兒批次改派」「證據檔補全」「指標 15 條解析 0 失敗」：**未驗**。
- 包 A 的「`Decision` 抹回聲後逐位元不變」：**未驗**（需要跑該包自己的對照腳本）。
- 包 C 的「拆 4 個死接縫」「11 支 skip 真的消除」：**未驗**——skip 由 73→62 的**差值 11 相符**，
  但「真的消除 vs 換一個地方 skip」本包沒有逐支比對。
- 包 D 的「SC-1~SC-10 十一筆已由帳本包修好」：**只驗到 SC-10 那一筆**（R89／R90 兩列存在），其餘十筆未驗。
- 包 E 的交付：**結構上無法驗**——它交件時本包已在寫這份檔，且它仍在改樹。

---

## 2. 本輪的兩個掌舵者裁決（必須帶進下一輪）

1. **未結列衝上 warn 線也要照立缺陷。** 藏起真發現是這個 repo 反覆判紅的形態。
   現況：**未結 90／warn 86／fail 98** ⇒ **已越過 warn 線 4 筆，距 fail 線 8 筆**。
   ⇒ 下一輪開場就在 warn 帶內，**但這不構成「少立缺陷」的理由**，只構成「優先結案」的理由。
2. **繼續 mac、改判準**——平台綁定的欠債改用**平台條件**記，而不是用輪號記。包 E 在做這件事。
   🔴 §1.2 那三筆 pgvector 紅**正是這個裁決要治的東西**：用輪號記平台綁定的債，在 mac 輪上必然到期而做不掉。

---

## 3. 還沒做什麼（待派清單）

### 3.1 必做：收尾包（**需靜止樹**，所有包停工後的單人窗口）

| # | 項目 | 憑證要求 |
|---|---|---|
| S-1 | ✅ **已完成（收尾窗口）**：實際重釘為 **83578 → 83739（+161）**——本欄原寫的 `+149` 是「前段包造成的成長」，**漏算重釘自身的稽核列 +12**（那一列自己也住在護欄層裡）。三條合法出口逐條實查後才重釘，判定與逐檔清單＝`docs/06_quality/CrossPlatform_R90_Guard_Repin_Evidence.md`。代價側現查：R90 上限 2000、連升 streak 1／2、款(12) 到期輪 R91 未到 ⇒ 皆未撞。🔴 **交棒警訊：R91 同時撞「款(12) 上限須降到 ≤1600」與「R92 必須淨額 ≤0」** | CLAUDE.md 明文「一律由收尾包在所有包停工後做一次」。必須同時：①`--print-guard-lines` 重釘表；②`_GUARD_LINES_REPIN_LOG` 補一列（含淨額與理由，不補即紅）；③表尾新總量必須逐字等於 `sum(_FROZEN_GUARD_LINES.values())`；④重跑 `--print-guard-lines` 取新的 `_REPIN_LOG_HISTORY_SHA256`（該 sha 必須在**貼上新列之後**才算得出來）。🔴 注意 `_REPIN_LOG_FROZEN_PREFIX_LEN` 也要跟著改 |
| S-2 | ✅ **已完成（收尾窗口）**：六道憑證見 §0.0 與〈附錄 Z〉，座標＝HEAD `be53ff0`／dirty 26／單一工作者 | 本檔 §1 全部數字**就此作廢為史料**（NEW-5 同一件事） |
| S-3 | ✅ **已完成（包 E，走第三條路）** | 🔴 **本欄原文說「不接受第三條路」，指的是「刪掉那支測試」**——包 E 走的是**另一條**第三路：把記帳模型由輪次改成平台條件，三個站點一支都沒刪。授權來源＝§2-2 掌舵者裁決。詳見 NEW-1 與 `DEF-200-130` |
| S-4 | ✅ **已完成（收尾窗口）**：座標已補進 ADR-XPLAT-002 的 R90 列 | 補的內容＝時刻（14:0x–14:3x）＋`HEAD=be53ff0e2d524bb34e341e1987690b2ace4c1e18`＋當時 dirty 17~19 且在增長，並明文「不得引用『18』除非同時引用座標」。**包數同時由「四線」訂正為全輪 8 包**（帳本／A／B／C／D／E／旁測／編纂） |
| S-5 | ⏳ **未做**（本輪唯一一項收尾必做卻沒做的） | 修憲兩處已落地在 PRD `:79`／`:1372`，登記簿在 `R89_HANDOFF.md` §6a.1，背書欄仍空。🔴 收尾窗口**刻意不自己背書**——修憲程序要求四方全同意，自己給自己背書會讓那道程序失去意義。現查：`ls docs/06_quality/ \| grep 'R90_Review'` 為空集合 |
| S-6 | ✅ **已完成（收尾窗口）**：逐格判定＋憑證見 §0.0c | 六格全部 ❌（0/6），**一格都沒有塗綠**；M6 逐字是「不可求值（**不是**通過）」 |
| S-7 | 🟡 **部分完成（收尾窗口）** | 已補：包數（8）、「18 支紅」的座標、靜止樹憑證指標。**平台版本字串本來就在該列**（`Darwin 25.5.0 arm64`）。**仍未補**：雲端 CI 那一欄——本輪零 `push` 試探 ⇒ 雲端本輪的量測為空，該欄維持「本輪零量測」不得以本機全綠代替 |

**現查（S-5／S-7 那兩項還開著沒開著，一行問得出來）**：

```bash
cd /Users/wuweihong/Antigravity/AISDCL_Agent
# S-5：四方複審的產物在不在（R85 的體例是四份 CrossPlatform_R<n>_Review_*.md）
ls docs/06_quality/ | grep -c 'R90_Review'   # 🔴 讀**印出來的計數**，不讀 rc（rc 會是 grep 的，
                                             #    正是 §0.2／Z-8 那個陷阱）。0＝還沒跑
# S-5：修憲登記簿的背書欄
grep -n '修憲動作登記簿' -A 12 docs/04_planning/R89_HANDOFF.md
# S-7：雲端 CI 本輪跑過沒有（本機答不出來，只能問雲端）
gh run list --limit 10
# S-1/S-2/S-6 的複驗（做完的那幾項；淨額應為 +0、逐檔漂移 0 支）
./.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines | head -3
```

### 3.2 四方複審挖出、尚未處置

🔴 **下表是量測值不是常數**（本包量於 14:38–14:47 的**移動樹**）。讀到本節的第一動作是重量，不是採信：

```bash
cd /Users/wuweihong/Antigravity/AISDCL_Agent
# N3 的分母（本包量到 64 支／83,727 行，與 N3 引用的 86,901 不同源）
./.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines | tail -5
# N1／SA N-7：本機 builder 與 pip 是否存在（本包量到 venv-built + pip 26.2.1 ⇒ 不可重現）
grep -E '^command' .venv/pyvenv.cfg; ./.venv/bin/python -m pip --version; echo "RC=$?"
# SA N-6：OVERAGE_POLICY 是否仍是零實作
git grep -nF 'OVERAGE_MONTHLY_UTILIZATION_HALT' -- . | cat
# QA N4：根層 skip 數（本包量到 44）
./.venv/bin/python tools/run_root_unittests.py > /tmp/root.log 2>&1; echo "RC=$?"; grep -E 'Ran |FAILED|^OK' /tmp/root.log
```

| 來源 | 項目 | 本包補充 |
|---|---|---|
| Architect **N3** | **給護欄層一個總量帽**（掌舵者 Plugin 問題的真正答案；引擎 4.4 倍、30 commit +55% vs 引擎 +1.5%） | 🔴 **前置未解**：N3 的 86,901 與本包量到的 83,727 不同源（§1.3-2）。**先定義量測面再訂帽**，否則帽子的分母不明 |
| Architect **N1** ＝ SA **N-7** | provenance 加 `builder=uv\|venv` 欄 ＋ `install_hint()` builder-aware | 🔴 **本機不可重現**（§1.3-3）：本機是 venv-built 且有 pip 26.2.1。派工時標「依文件立案、本機不可重現」 |
| Architect **N2** | extras parity 鎖 | 未驗 |
| Architect **N4** | statusLine 當快取寫入器 | 未驗。與 `DEF-200-105`（TTL 180s 短於任何刷新間隔）同族 |
| SA **N-3** | **證據檔指標解析守衛** | 🔴 帳本包本輪**三次命中**自證此缺口為真 ⇒ 優先度應高於其他 N 項 |
| SA **N-6** | `OVERAGE_POLICY` 第 1 步未做（7 筆全是註解） | 與 `R89_HANDOFF.md:373` 記載的 `OVERAGE_MONTHLY_UTILIZATION_HALT` **零實作**同族 |
| QA **N2** | 2 支測試任何 CI job 都跑不到 | 未驗 |
| QA **N4** | 根層 44 支 M6「**不可求值**」（需 Windows 剖面落款） | 本輪是 mac 輪 ⇒ 結構上做不到，**應與 §2-2 裁決合併處理**（改用平台條件記，而非留在 mac 輪等它到期） |
| SD／包 B | `account_key` 實作 | 🔴 **前置未驗**：同帳號跨機器 org/ws 是否穩定。**且污染正在發生**：`r` 由 34 列舊帳號 ＋ 2 列新帳號混算 |

### 3.3 旁測挖出

- `--pace` 印 **7 個 kind 但只有 4 個相異量**（重複計數）。🔴 本包實測佐證：`five_hour` 與 `session` 兩格
  逐字同值（皆 `41% 剩 201 分鐘 band=prepare cap=1`）；`weekly_all` 與 `seven_day` 亦同值（皆 `6% 剩 9561 分鐘`）；
  `weekly_scoped`／`nimbus_quill`／`spend` 三格皆 `0% reset 距離不明 … note=missing`
- 取數降級 stale-cache **無年齡上界**
- 哨兵最壞死等 **900s**
- 每道水位門檻**只喊一次**

### 3.4 帳本包挖出

- 交棒書漏 **6 筆**靜默過期
- **另有 28 列早於 R89 就已靜默過期**

### 3.5 🔴 本包補進清單的項目（原清單沒有）

| # | 項目 | 理由 |
|---|---|---|
| **NEW-1** | ✅ **已完成（包 E）**：靜止樹 pytest `4623 passed, 62 skipped`、`PYTEST_TRUE_RC=0`（見〈附錄 Z〉Z-2） | 🔴 **走的是第三條路，且那條路不在判準檔原本列的兩個出口內**：包 E 沒有「把債做掉」也沒有「再推一輪」，而是把**記帳模型**由輪次改成平台條件（登記表 `_PLATFORM_BOUND_DEBTS` ＋ 真探針 `probe_pgvector_bge_m3_staging()` ＋ 三態）。授權來源＝§2-2 掌舵者裁決。與原清單警告的「刪掉那支測試」**不同**——那三個站點都還在，只是 reason 裡的承接欄由輪號換成 `PGVECTOR_BGE_M3_STAGING`。立案補記＝`DEF-200-130`（由收尾窗口代寫；包 E 禁碰帳本），可裁事項見 §0.0b |
| **NEW-2** | **包 A 的落款輪號 R89 → R90**（🔴 收尾窗口複核後**維持未修**，並補上一項編纂包沒看到的成本） | `quota_meter.py:354`／`:683`（§1.3-1）。今天不轉紅（是落後不是超前）。🔴 **新事實：那個「R89」已經不只是落款，它是一個被跨檔引用的錨**——`quota_meter.py` 的節名〈R89 觀測欄〉被 `test_quota_policy.py` 檔頭、`test_context_budget_guard.py` 的 R89 三支測試、測試類別名 `TestR89ObservationFieldsAreWiredButInert`、以及 `_GUARD_LINES_REPIN_LOG` 的 R90 那一列同時指名。改名＝一次跨 4 支檔的連動改動，正是 CLAUDE.md 鐵律七〈跨檔參照稅〉判為「只能由收尾單人窗口做」而本窗口**刻意不做**的那一類（首要交付是靜止樹憑證，非必要重構會換掉 rc 的可歸因性）。⇒ 下一輪處置時請把它當**改錨**而不是改字 |
| **NEW-3** | **鐵律六「讀 rc 時接管線」在 Bash／zsh 側補攔截器**（`DEF-200-086`），🔴 **並把射程擴到「背景工作完成通知的 exit code」** | 本包當回合踩了**三次**：①`pytest \| tail` 讀到 `PYTEST_RC=0`／真值 1（§0.2）；②③根層閘門的 harness 通知逐字回報「exit code 0」／真值 `ROOT_UNITTEST_RC=1`（§6.4）。第②③型的載具**是 harness 自己**，不是指令字串 ⇒ 現行 `waitform_hits()` 那種讀指令字串的判準結構上看不到它。**寫下該紀律的 repo 裡讀該紀律的 agent 照樣踩** ⇒ 樣本數 **+4**（全表見 §6.5）。🔴 附帶：鐵律六推薦的 `until`-loop 體例**沒說迴圈體要睡**，本包的忙等版被 600s 逾時搬到背景並以 rc=144 收場，而那個 rc 看起來像被等的工作失敗了 ⇒ 體例應補「迴圈體必須有 sleep」 |
| **NEW-4** | **定義「護欄層」的量測面** | N3 的前置（§1.3-2）。兩個數字差 3,174，不先收斂就訂帽等於訂一個分母不明的帽 |
| **NEW-5** | ✅ **已完成（收尾窗口）**：靜止樹憑證見 §0.0 與〈附錄 Z〉 | §1 各值**就此作廢為史料**，不得當收輪憑證引用 |
| **NEW-6** | 🟡 **收尾窗口補了第三個取樣點，並推翻了「燃燒率是常數」這個隱含前提** | 三點：`14:38:24 → 41%`／`14:42:49 → 43%`／**`15:23:15 → 53%`**（`--pace` 自報的 `量測於`）。第二段＝10pp／40.43 分＝**0.247 pp/分**，而編纂包量到的第一段是 **0.452 pp/分** ⇒ 🔴 **燃燒率是「同時有幾個工作者」的函數**：第一段在多包並行下量，第二段在單人收尾窗口量，差近一倍。**把任一段當常數外推都是錯的**，主控的 0.494 更是三位有效數字不可支持（來源百分比整數截斷，同 §1.4 的論證）。**仍未做的**：多包並行下的重複取樣（要複驗 0.452 需要再開一次並行波） |

---

## 4. 續航現況：哨兵武裝了，但「reset 後續跑」**這條路本輪仍完全未驗**

| 環節 | 狀態 | 憑證 |
|---|---|---|
| 哨兵已武裝 | ✅ | `launchctl list` 命中 `AutoSDD_Sentinel_7878baa8-0c63-43b4-8416-4cd63a7cbe8a`（status 0），量測於 14:40:04 |
| harness autocompact 開啟 | ✅ | `--check-autocompact` rc=0，判定鏈兩條皆「未設＝預設 true」，量測於 14:40:04 |
| context 水位 | 74.3%（<75%） | `--check` rc=0，量測於 14:38:38 |
| **reset 後自動續跑** | 🔴 **完全未驗證** | 旁測 2 判決：本輪撞的是 `quota_spend`（**無 reset 可等**）⇒ 那條路一次都沒走過 |

🔴 **mac 側的已知邊界（CLAUDE.md 明文，非待修 bug）**：launchd 只在機器醒著時補跑錯過的一輪；
`pmset repeat` 需 sudo 且本專案刻意不碰 ⇒ **reset 落在闔蓋期間時，續航要等到開蓋才會有人動作**。
本次 reset 在 **18:00 (+08:00)**。

---

## 5. 沒驗到什麼（誠實劃界）

**本包結構上驗不到的**：
- 包 E 的任何交付（它在本包寫檔時仍在改樹）
- 任何「過程量」（92→86→90 的中間值、「拆 4 個死接縫」的過程、「11 支 skip 真的消除」vs「換地方 skip」）
- 燃燒率斜率（只有單一取樣點）
- 主控被駁回的**時序**問題（磁碟只留終態，留不下「誰先宣稱」）

**本包有能力驗但沒驗的**（時間／額度所限，cap=1、band=prepare）：
- 帳本包的「27 列孤兒批次改派」「證據檔補全」「指標 15 條解析 0 失敗」
- 包 A 的「`Decision` 抹回聲後逐位元不變」
- 包 D 的 SC-1~SC-9（只驗了 SC-10）
- Architect N2／N4、QA N2 三項
- 帳本包挖出的「6 筆＋28 列靜默過期」的逐筆座標

**根層 unittest 閘門**：見 §6，本包啟動了但在本檔定稿時的狀態記於該節。

---

## 6. 根層 unittest 閘門實測（量測於 14:39:07–14:46:37，**非靜止樹**；🔴 **本節整節已被 §0.0／〈附錄 Z〉Z-1 取代**——靜止樹上是 `Ran 3346 tests` `OK (skipped=44)` `ROOT_TRUE_RC=0`。本節逐字保留為史料，因為 §6.1~§6.5 的**歸因與教訓**仍然有效，只有那三個紅的狀態被 S-1 消掉了）

```
Ran 3346 tests in 435.842s
FAILED (failures=3, skipped=44)
ROOT_UNITTEST_RC = 1
```

### 6.1 三筆紅**全部是同一個根因**：S-1 那個還沒做的重釘

```
FAIL: test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet.test_a_net_zero_swap_is_red
FAIL: test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet.test_the_line_ratchet_took_over_and_has_teeth
FAIL: test_adr_xplat001_c1c2_lock.TestShrinkOnlyRatchet.test_ratchet_is_independent_of_git_state
```

失敗訊息逐字（節錄）：

```
[成長] 護欄層行數由 83578 增為 83727（+149）…
成長最多的幾支：[('test_quota_policy.py', 124), ('test_context_budget_guard.py', 25)]
```

⇒ **這不是三個缺陷，是一個缺陷被三支測試同時看到**，而且它**不是 bug，是設計要的行為**：
棘輪正在要求「擴充既有鎖檔一樣要付代價」。合法出口就是 §3.1 的 **S-1 重釘**（含補 `_GUARD_LINES_REPIN_LOG` 一列）。
🔴 **在做完 S-1 之前，根層閘門必然是紅的，這是預期狀態，不得當成新缺陷去追。**

**現查（S-1 做完前應為 3 紅同根因；做完後這三支應轉綠）**：

```bash
cd /Users/wuweihong/Antigravity/AISDCL_Agent/tools/tests
../../.venv/bin/python -m pytest test_adr_xplat001_c1c2_lock.py -q -k "Ratchet"; echo "RC=$?"
# 分母現值（重釘的目標值）
../../.venv/bin/python test_adr_xplat001_c1c2_lock.py --print-guard-lines | tail -5
```

### 6.2 🔴 駁回包 D 的「18 支紅」

包 D 稱本輪根層有 **18 支紅**；本包實測為 **3 支**（皆同根因）。
本包**無法判定包 D 錯了**——兩者量測時刻不同、樹在動（§0.1），也可能 D 指的是別的閘門或別的計數單位。
⇒ **這正是 S-4 要補「時刻＋HEAD＋dirty 檔數」座標的理由**：沒有座標的紅數在移動樹上不可對帳。
**下一輪不得引用「18」或「3」任一個數字，除非它帶著座標。**

### 6.3 順帶佐證 QA N4

`skipped=44` 與 QA N4 所稱「根層 44 支 M6 **不可求值**」**數字相符**（量測於 14:46:37）。
本包未逐支比對那 44 支是否就是 M6 那一族 ⇒ 標為**數字相符、身分未驗**。

### 6.4 本檔自己被守門攔下過一次（照實記）

本檔第一版落地後，`test_doc_loc_baseline_freshness_r60.py::TestR78HandoffClaimsCarryLiveCommands::test_every_not_yet_done_claim_is_checkable`
當場轉紅（量測於 14:47:58，`TARGETED_RC=1`），逐字指出本檔 **§3.2** 與 **§6.1** 兩節
「宣稱某事尚未完成，卻沒有附任何現查指令」。

⇒ 本包**沒有**用逃生口 `<!-- handoff-claim-verified: WHY -->` 關掉它（那是給「真的沒有機械現查管道」的事用的，
本例兩節都查得到），而是**依既有體例補上現查指令**。補完後重跑 `RETEST_RC=0`（262 passed，量測於 14:49:09）。

🔴 **這道鎖的立案理由與本檔 §0.1 是同一件事**：交棒書記的是某一刻的狀態，讀者卻在數天後、由別人動過的樹上讀它。
**它攔下本檔是它正常運作，不是誤判。**

### 6.4b 交棒書落地後的複驗：**本檔為根層閘門新增零筆紅**

```
量測於 14:49:43–14:57:45（本檔已在磁碟上、含 §3.2／§6.1 的補丁）
Ran 3346 tests in 467.525s
FAILED (failures=3, skipped=44)
FINAL_ROOT_RC = 1
```

三筆紅與 §6.1 **逐字同名**（同樣是 `TestGuardLayerRatchet` ×2 ＋ `TestShrinkOnlyRatchet` ×1）
⇒ **本檔沒有引入任何新的紅**，rc=1 的唯一成因仍是那個未做的 S-1 重釘。

### 6.5 本包自己的 rc 陷阱：**四次**（同 §0.2）

本包把根層閘門丟到背景跑**兩次**，harness 的完成通知**兩次都**逐字回報 **「exit code 0」**——
而那是整條複合指令（`python … ; echo "RC=$?"`）最後一個元素 `echo` 的 rc。
**真值（`ROOT_UNITTEST_RC=1`／`FINAL_ROOT_RC=1`）寫在輸出裡，不在通知裡。**

本包當回合的四次全紀錄：

| # | 載具 | 讀到 | 真值 |
|---|---|---|---|
| 1 | `pytest … \| tail -25; echo "RC=$?"` | `PYTEST_RC=0` | **1** |
| 2 | harness 背景工作完成通知（根層閘門第一次） | `exit code 0` | **1** |
| 3 | harness 背景工作完成通知（根層閘門複驗） | `exit code 0` | **1** |
| 4 | 同上，`until ! pgrep …` 忙等迴圈自己被 600s 逾時搬到背景 | 通知回報 `failed / exit code 144` | 那是**迴圈**被砍的 rc，與被等的工作無關（該工作已正常結束、rc=1） |

⇒ 鐵律六那一列的樣本 **+4**，而 #2~#4 的載具是 **harness 自己**，不是指令字串 ⇒
現行 `waitform_hits()` 那種讀指令字串的判準**結構上看不到它們**。
**背景工作的完成通知不得當成 rc 憑證**（`DEF-200-086` 的射程建議擴到這一形態，見 NEW-3）。

🔴 **#4 另有一條獨立教訓**：`until ! pgrep …; do :; done` 是**忙等**（`:` 不睡），
它會燒 CPU 且不會自己結束得漂亮——CLAUDE.md 鐵律六推薦的是「掛 Monitor／until-loop」，
但**沒說迴圈體要睡**。本包實測它在 600s 被搬到背景並以 rc=144 收場，
而那個 rc **看起來像被等的工作失敗了**（實際上那個工作早就正常結束）。
⇒ 建議下一輪把「迴圈體必須有 sleep」補進該列的體例（見 NEW-3）。

---

## 7. 下一步的確切指令（可貼可跑）

```bash
# 0) 先確認樹靜止（所有包停工）——這是 §0.1 的前提，不可跳過
cd /Users/wuweihong/Antigravity/AISDCL_Agent
date '+%H:%M:%S'; git status --porcelain | wc -l; git rev-parse HEAD

# 1) 重量四個關鍵數字（🔴 一律不接管線讀 rc，見 §0.2）
cd /Users/wuweihong/Antigravity/AISDCL_Agent/AutoClaude
/Users/wuweihong/Antigravity/AISDCL_Agent/.venv/bin/python -m pytest tests/ -q > /tmp/pytest.log 2>&1; echo "RC=$?"; tail -5 /tmp/pytest.log

cd /Users/wuweihong/Antigravity/AISDCL_Agent
./.venv/bin/python tools/run_root_unittests.py > /tmp/root.log 2>&1; echo "RC=$?"; tail -30 /tmp/root.log
./.venv/bin/python tools/check_defect_log_crossref.py --unresolved-count; echo "RC=$?"
./.venv/bin/python AutoClaude/tools/check_loc_budget.py --json > /tmp/loc.json 2>&1; echo "RC=$?"

# 2) 護欄層重釘 —— 🔴 R90 的那一次**已由收尾窗口做完**（83578 → 83739，+161）。
#    下面這行現在的用途是**驗證**而不是重做：印出來的淨額應為 +0、逐檔漂移應為 0 支。
./.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
#    R91 要重釘時才需要貼回 _FROZEN_GUARD_LINES／追加 _GUARD_LINES_REPIN_LOG 一列／
#    改 _REPIN_LOG_FROZEN_PREFIX_LEN／重跑本行取新的 _REPIN_LOG_HISTORY_SHA256。
#    🔴 R91 專屬前置：款(12) 到期 ⇒ 必須先往 _REPIN_NET_CAP_SCHEDULE 追加一列 (91, ≤1600)。

# 3) pgvector 三筆 —— 🔴 **已由包 E 消除**（改用平台條件記債），此處保留為回歸驗證
./.venv/bin/python -m pytest AutoClaude/tests/test_conftest_windows_native_skip_report.py -q; echo "RC=$?"
#    現況：靜止樹全樹 pytest 為 4623 passed / 62 skipped / rc=0（附錄 Z-2、Z-7 兩次獨立實測）
#    承接欄已由輪號換成平台條件 PGVECTOR_BGE_M3_STAGING，立案＝DEF-200-130

# 4) 額度／續航現況（零 token，派工前必查，不得沿用本檔的值）
./.venv/bin/python tools/session_resume_planner.py --pace
./.venv/bin/python tools/session_resume_planner.py --check
./.venv/bin/python tools/session_resume_planner.py --check-autocompact
launchctl list | grep AutoSDD_Sentinel_
```

---

## 8. 🔴 禁止事項

1. **不准 `--no-verify`**（任何 git 操作）
2. **不准 `AUTOCLAUDE_SKIP_HOOKS=1`**
3. **不准調高任何天花板**——包含但不限於 `_FROZEN_GUARD_LINES` 的總量、LOC `cap`、
   未結列 `warn`／`fail` 線、`SPECIAL_FILES` 門檻、`MIN_TESTS`。
   🔴 S-1 的重釘**不是**調高天花板：它是把棘輪重釘到**已經發生**的現值並付出「補一列理由」的代價，
   與「因為過不了所以把線拉高」是兩件事。分辨方式：重釘必須伴隨 `_GUARD_LINES_REPIN_LOG` 的一列。
4. **不准 `git stash`**（除 `git stash create`）——PreToolUse hook 已阻斷，
   本 repo 有實帳：一個 subagent 的 `git stash -q -u --keep-index` 當場清空 16 改 + 4 未追蹤檔（`DEF-200-007`）
5. **不准以模型判斷推翻機械守衛**——R87 實例：改取數層繞過 halt ⇒ 13 agent 全滅、1.3M tokens 零產出
6. **不准引用本檔 §1 的數字當收輪憑證**（§0.1：非靜止樹）
7. **不准把「未驗證」寫成「已驗證」**——本檔存在的唯一理由就是這一條
8. **不准在讀 rc 時接管線**（§0.2，本包當回合已踩過一次）
9. **不准刪掉判準來讓紅變綠**——§1.2 那支測試的檔內逐字寫明「不接受的第三條是把本支刪掉」

---

## 9. 重啟資訊（〈可重啟點四條件〉第 2 條）

```
session id = 7878baa8-0c63-43b4-8416-4cd63a7cbe8a
重啟指令   = claude -r 7878baa8-0c63-43b4-8416-4cd63a7cbe8a
逐字稿     = /Users/wuweihong/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/7878baa8-0c63-43b4-8416-4cd63a7cbe8a.jsonl
哨兵       = AutoSDD_Sentinel_7878baa8-0c63-43b4-8416-4cd63a7cbe8a（launchctl，status 0，量測於 14:40:04）
本窗 reset = 2026-08-15T10:00:00Z ＝ 18:00 (+08:00)
HEAD       = be53ff0e2d524bb34e341e1987690b2ace4c1e18
```

🔴 **重啟後第一件事是重驗**（〈可重啟點四條件〉第 4 條）：
**不採信本檔任何「已通過」宣稱**，照 §7 的指令重跑一次。本檔對自己的宣稱同樣適用 zero-trust。

---

## 附錄 Z：靜止樹憑證原始輸出（收尾單人窗口）

> 🔴 **貼的是工具自己的原始整行，不拆解重組成摘要**（本輪剛立的紀律：主控曾把
> `1 failed, 4607 passed, 62 skipped` 轉述成「4607 passed / 62 skipped」，`1 failed` 在 headline 消失）。

<!-- guard-total:R90 --> 護欄層累積總量現值 **83578 → 83739（+161）**；
`sum(_FROZEN_GUARD_LINES.values())` 與 `_GUARD_LINES_REPIN_LOG` 表尾逐字對帳。

### Z-1 `python tools/run_root_unittests.py`

🔴 **收尾窗口跑了四次**（重釘後、文件落地後、文件收斂後、Z-1 自身訂正後）。
四次的**判決行逐字相同**，只有牆鐘不同：`430.331s`／`430.061s`／`421.469s`／`429.221s`。
下面貼的是**第四次＝最後一次**：

```
[Scan-H triplet] UEP=5 AC=47 GLC_FILES=64 GLC_LINES=83739
Ran 3346 tests in 429.221s
OK (skipped=44)
[Xplat injection matrix] Win2mac=8/12 mac2Win=5/10
[M6 id 集合] tools/tests@darwin：⚠️  不可求值（**不是**通過）（本次 skip 44 支）
ROOT_V4_TRUE_RC=0
```

跑多次的理由與 §6.4b 同型：**交棒書自己也被守門看著**（本輪實際被 `TestR78HandoffClaimsCarryLiveCommands`
攔下一次——§3.1 的 S-5「未做」宣稱沒附現查指令），改了它就必須重跑一次才知道
「這份檔有沒有替閘門新增紅」。每一次皆 `OK`、皆 `skipped=44` ⇒ 本檔為根層閘門新增零筆紅。

### Z-2 `cd AutoClaude && python -m pytest tests/ -q`

```
4623 passed, 62 skipped in 103.68s (0:01:43)
PYTEST_TRUE_RC=0
```

🔴 這一行取代 §1.1／§1.2 的 `1 failed, 4607 passed, 62 skipped`：那筆 `1 failed`
（三筆 pgvector `[DEBT]` 輪號追平 R90）已由包 E 以**平台條件記債**消除，見 §3.5 NEW-1。

### Z-3 `cd AutoClaude && PYTHONUTF8=1 lint-imports`

```
Contracts: 9 kept, 0 broken.
LINT_RC=0
```

### Z-4 `python tools/check_defect_log_crossref.py`

```
✅ 缺陷帳本跨文件狀態一致：帳本 207 筆有效狀態紀錄、11 份掃描目標皆無矛盾；…具名治理文件 44 份皆已登記且未逾體積上限…未結存量 91 列（唯一量測入口＝`--unresolved-count`；warn 86／fail 98 列）…另 13 筆已結列殘留待辦，見 warning。
RC=0
```

### Z-5 `python tools/check_defect_log_crossref.py --unresolved-count`

```
未結列數＝91／全部 207 列｜warn=86 fail=98
UNRESOLVED_RC=0
```

⚠️ 工具自己的 warning 逐字：「未結列 91 筆…已逼近 fail 線 98（距 7 筆）」。
本輪淨增 1 筆（`DEF-200-130`，包 E 的立案由收尾窗口代寫）。

### Z-6 `python AutoClaude/tools/check_loc_budget.py --json`

```
{'total': 20417, 'baseline': 17032, 'cap': 20438, 'total_violation': False, 'total_warn_band': False, 'total_warn_margin': 10, 'tier_warn_margin': 6, 'special_warn_margin': 5, 'special_stale_slack': 32, 'policy_version': 'v2-tiered+sd08-special', 'absolute_limit': 750}
LOC_RC=0
```

### Z-7 M6 的 AutoClaude 半：`pytest tests -q -rs` ＋ `local_ci_gate.py --census-only`

```
4623 passed, 62 skipped in 103.53s (0:01:43)
PYTEST_RS_TRUE_RC=0
[skip census] AutoClaude/tests@darwin+pg+nested 共 62 支：platform=53／tool-absence=3／env-disabled=2／structural-pair=1／debt=3／untagged=0／欠債型 8 支（目標 0）
CENSUS_TRUE_RC=0
```

這同時是 Z-2 的**獨立第二次**執行（不同旗標、不同時刻），兩次的 `4623 passed, 62 skipped` 逐字相同。

### Z-8 🔴 收尾窗口自己踩到的兩件事（照實記，同 §6.5 的體例）

| # | 形態 | 實況 |
|---|---|---|
| 1 | **讀 rc 時接管線**（鐵律六那一列，本輪第 5 個樣本） | 我寫了 `… --pace 2>&1 \| head -6; echo "PACE_RC=$?"`——那個值是 `head` 的 rc。⇒ 本檔**不宣稱** `--pace` 的 rc，只引用它印出的內容 |
| 2 | 指令缺參數導致量測塌掉 | 第一次 pytest 沒帶 `-rs`，`local_ci_gate.py --census-only` 因而回 `❌ skip 量測塌掉…摘要行宣告 62 支 skip，-rs 區塊卻只解析出 0 支`（rc=1）。**那是我的指令缺參數，不是 repo 缺陷**——該守衛正確地拒絕輸出一份不可信的普查 |
