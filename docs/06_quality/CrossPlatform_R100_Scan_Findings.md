# CrossPlatform R100 — 掃描發現與逐檔清單（ADR-XPLAT-013 落地）

<!-- guard-total:R100 --> **本輪護欄層累積淨額＝ 86097 → 86452（+355）** —— 單包（P2-A）落地，
逐檔清單見下方〈§B 逐檔清單〉。

- **輪次**：R100
- **範圍**：Phase 2 方向 (a)＝把 `AutoClaude/tools/check_loc_budget.py::count_loc()` 的計價規則改為 **assertion-only**
- **修憲文件**：[docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md](../04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md)
- **本檔性質**：`_GUARD_LINES_REPIN_LOG` 兩列 R100 逐字指名的「逐檔清單的家」（款(9) `[未附刪除清單]` 要求）

---

## §A 立案事實（當回合實測，非援引歷史值）

改前 `count_loc()` 的判準只有 8 行邏輯：空行免費、行首 `#` 整行註解免費、**docstring 全額計價**且與一行 `if` 同單價。
於是「把 docstring 逐字改寫成 `#` 前綴」可在 **raw 行數與可執行 AST 節點數逐字不變**的前提下大幅降低計價
——一道套利門。而它被工具自己的違規訊息逐字教過（`[TIER-WARN]` 段原文「說明文字請寫成 `#` 註解而非 docstring
——docstring 行會被 count_loc 計入」），該句已於本輪移除。

紅側自證（同一組合成檔，兩套判準對照；當回合實跑）：

| 判準 | docstring 載體 | `#` 載體 | 差額 |
|------|---------------:|---------:|-----:|
| 改前 `count_loc`（硬編二分） | 8 | 5 | **3**（＝套利門） |
| 改後 `count_loc`（assertion 桶） | 5 | 5 | **0** |

`AutoClaude` 總量與三支零餘裕檔的改前／改後實測（`python AutoClaude/tools/check_loc_budget.py --json`）：

| 量 | 改前 | 改後 |
|----|-----:|-----:|
| `total` | 20426 | 16483 |
| `baseline` ／ `cap` | 17032 ／ 20438 | 17032 ／ 20438（依 ADR-XPLAT-013 條文三豁免，**未重釘**） |
| `cap − total`（餘裕） | **12** | **3955** |
| `tools/lib/quota_gate.py`（budget 500） | 500（餘裕 0） | **356**（餘裕 144） |
| `.claude/hooks/block_destructive_git.py`（budget 750） | 750（餘裕 0） | **558**（餘裕 192） |
| `tools/probe/audit_session.py`（budget 750） | 711（餘裕 39） | **532**（餘裕 218） |
| `tools/session_resume_planner.py`（budget 750） | 750（餘裕 0） | **720**（餘裕 30） |

全樹逐檔比對：**`新值 > 舊值` 的檔數＝0**（shebang／PEP 263／pragma 三類整行 `#` 由免費改為計價，
但沒有任何一支檔因此上升）⇒ 換值域**沒有**放寬任何既有門檻，方向只有收緊。

---

## §B 逐檔清單（護欄層 86097 → 86452，+355）

<!-- guard-total:R100 --> 護欄層累積總量現值 **86438 → 86452（+14）**；本段為兩列 R100 稽核痕跡的逐檔對照。

| 檔案 | 淨額 | 內容 |
|------|-----:|------|
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | +346 | 兩組新載體：①計價規則變更輪的零緩衝豁免（`_PRICING_CHANGE_EXEMPT_ROUND` ＋ `pricing_exemption_problems()` ＋方向鎖 ＋五格紅綠自證）；②觀察模式 5 輪時效的到期判準（`_PHASE2_REVIEW_LOG` ＋ `phase2_review_problems()` ＋連續空轉上限 ＋七格紅綠自證）；③兩者共用的輪次時鐘抽成 `live_repin_round()`；④本表自身編修（重釘兩格、追加兩列稽核痕跡、`prefix_len`／指紋更新、指紋改寫帳本追加一列） |
| `tools/tests/test_block_destructive_git_r83.py` | +9 | `TestTheHookStaysInsideItsLocTier` 的語意訂正：該鎖在新計價下由「幾乎貼著上限」變成「離上限很遠」，鑑別力下降這件事逐字寫進 docstring（不寫死餘裕數字，改為指向 `--json` 現查） |

**合法出口逐條實查（款(9) 要求的「不是淨減法輪」之辯護）**：

1. **刪死碼不適用**——兩組載體都是此前不存在的判準面（ADR-XPLAT-012 自己的〈未解決缺口〉節逐字自陳
   「條文五 §6 的 5 輪時效尚未有到期時點的具名常數」），沒有等量的舊判準可以退場去換。
2. **抽共用層已做**——兩組載體都要問「現在是第幾輪」，該取數已抽成 `live_repin_round()`
   （先例：`tools/lib/ci_liveness.py`），而不是各寫一份 `max(...)`。
3. **史料搬遷不適用於本包**——新增的全部是判準與紅綠自證，沒有可搬去證據檔的既有史料。

---

## §C 誠實劃界（本輪**未**做的事）

1. **`AutoClaude/.loc_baseline` 未重釘為改後實測 total**——這是掌舵者裁決的豁免（ADR-XPLAT-013 條文三），
   機械載體＝`_PRICING_CHANGE_EXEMPT_ROUND`；下一輪還想用同一個豁免會直接轉紅。
2. **Phase 2 方向 (b)(c) 未落地**——交棒收尾單人窗口／Stage 2。條文五 §6 的視窗依 §6 重新武裝一次
   （到期輪隨 `_PHASE2_REVIEW_LOG` 末列前移），連續「維持觀察」受 `_PHASE2_MAX_CONSECUTIVE_DEFERRALS` 管。
3. **全庫 30 個「刻意寫成 `#` 以避開 count_loc」的自陳站點未逐一改寫**——那是史料，逐一改寫會製造
   大量無語意 diff；清單交棒 Stage 2（見交件回報）。這些站點在新計價下**不再有套利效果**，
   但它們的註記文字仍在講一個已經不成立的理由。
4. **ADR-XPLAT-012 條文六的四方複審尚未補行**——掌舵者已裁決實作，複審是待補的前置要件，
   逐字記在 ADR-XPLAT-013 的〈狀態〉與〈未解決缺口〉。

---

## §D R100 收尾單人窗口 — 技術債落盤的逐筆證據

> **本節性質**：R100 收尾窗口（唯一在跑的包，所有並行包已停工）把本輪未落盤的技術債
> 寫進 `AutoSDD_Defect_Log.md` 的 `DEF-200-196`~`DEF-200-216`（21 列）時，帳本列受
> `ROW_MAX_BYTES = 700` 限制而只能留索引；本節是那 21 列指向的證據家。
> 🔴 **證據等級逐筆標明**：「當回合實測」＝本窗口自己跑出來的；「〔他包回報，未複驗〕」
> ＝轉述並行包，本窗口沒有重量。兩者不得混淆（鐵律四）。

### §D-1 為什麼是 21 列而不是 30+ 列（合併粒度是被硬上限逼出來的，不是判斷）

原始發現清單有 30+ 項。合併判準＝**「下一輪修的時候會不會分開修？」**（會 ⇒ 分列）。
但真正的**約束**是機械的，必須誠實揭露：

| 量 | 當回合實測 | 出處 |
|---|---|---|
| 未結列數（落盤前） | **76** | `python tools/check_defect_log_crossref.py --unresolved-count` |
| warn 線 | 86 | `tools/lib/defect_ledger_index.py::UNRESOLVED_ROWS_WARN` |
| **fail 線** | **98** | 同檔 `UNRESOLVED_ROWS_FAIL`（`n >= 98` 即 fail，**無逃生口**） |
| ⇒ 本輪可落盤上限 | **21 列**（76+21=97 < 98；第 22 列即撞 fail） | 上兩列相減 |

⇒ 合併到 21 列**不是**「判斷 21 個根因」，是 fail 線把 30+ 項壓進 21 個承接單位。
🔴 該門檻的訊息逐字寫著「**不要調高本門檻**（那是砸溫度計）」，故本窗口未動它。
🔴 **外部阻塞軌不是出口**：`AutoSDD_External_Blocked_Log.md` 檔頭逐字「本表不是規避未結列
警戒線的後門」，合法阻塞源限 `GitHub Actions 帳務`／`Windows 實機`／`上游套件`／`其他-<理由>`
四種；本輪待裁決項卡在**我們自己**的四方複審 ⇒ 不符，未使用。

**⇒ R101 只剩 1 格**（97 → 98 撞 fail）。這是交棒給 R101 的第一順位約束，承接列＝`DEF-200-213`。

被合併的組合與理由：

| 帳本列 | 併入的原始項 | 為什麼不會分開修 |
|---|---|---|
| `DEF-200-197` | A2＋A3＋A14 | 「429 該產出什麼」是一個決定；A3（指紋抹空）與 A14（`KNOWN_KINDS` 詞表）都是該決定的下游，A2 若改成「429 ⇒ unmeasured」則兩者自動消失 |
| `DEF-200-199` | A5＋A13 | A5 是症狀、A13 是「修法屬修憲級」這件事本身；同一次修憲處理 |
| `DEF-200-200` | A6＋A7＋A8＋A9 | 四者都是**同一個欄位** `resets_at` 的「已過去」語意；一個共用述詞同時修掉三處，④ 是驗證前提 |
| `DEF-200-203` | A12＋D1＋D3 | A12 是機制層陳述，D1／D3 是主控自己的兩個實例；同一個「引用量測值不檢查時間軸」根因 |
| `DEF-200-204` | B1＋B2 | 同屬 PRD §4.2.4 未完成交付，下一輪一個工作流 |
| `DEF-200-206` | B4＋B5＋B6 | 七項全部是「PRD 字面 ↔ 實作形態不符」，需要的是**同一個裁決程序**逐項過 |
| `DEF-200-207` | C1＋本輪第 4 支紅 | 同一個常數 `_PRICING_CHANGE_EXEMPT_ROUND`、同一次四方複審 |
| `DEF-200-213` | C7＋C8＋C9 | 三筆帳本治理小缺口，下一輪一個 housekeeping 包一次清 |
| `DEF-200-216` | D5＋D6 | 同一個事件（自造 429）＋對它的錯誤描述；D6 不是獨立可修項，是 D5 的報告面訂正 |

**刻意不合併**（會分開修）：`DEF-200-196`（A1，純 bug、非修憲）與 `DEF-200-197`（A2，修憲級）
——把兩者併列會讓 A1 的一行修法被四方複審程序**扣為人質**，那正是鐵律七要消滅的形態。
同理 `DEF-200-214`（假陰性）不併入 `DEF-200-203`（過期當現值）：方向相反，教訓相反。

### §D-2 429 路徑的方向錯誤（`DEF-200-197`）

`tools/lib/quota_meter.py:716` 當回合實讀，`rate_limited_reading()` 的回傳逐字：

```
"schema_keys": [], "posture": {}, "account_key": None}
```

同函式把單軸 `pct` 釘在 `100.0`。該函式 docstring 自陳這是刻意的（「為什麼是『讀數』而不是
『量不到』」），理由是 `None` 在下游會落進 `BAND_UNMEASURED` ⇒ `degraded_cap` ⇒ 比 70% 帶更鬆。
**本窗口不否認那個顧慮，只指出方向被解成了相反的極端**：429 是 metering 端點自己的速率限制，
與模型額度是兩件事；把它轉譯成「額度用掉 100%」違反本 repo 通篇的「量不到 ≠ 量到零」。
〔他包回報，未複驗〕`23:02:03` 判 `rate_limited pct=100 ⇒ band=halt cap=0`，
而**同一端點** `23:05:07`（3 分 04 秒後）回報 `session=4%`。

附帶：`account_key: None` ＋ `posture: {}` 使指紋變空，工具自己印出的逐字警告
〔他包回報，未複驗〕：`⚠️ 偵測到帳號軸組合改變（account=34cd3507237f+... → (空)）：攤提正在用新樣本重新累積`
⇒ R95 §2.2 的攤提前置條件可被一個**與額度無關的 HTTP 狀態**抹除。

### §D-4 `recommended` 與餘裕反向（`DEF-200-199`）

`tools/lib/quota_policy.py:527-531` 當回合實讀：

```python
def _pace_of(readings: tuple[AxisReading, ...], p: Policy) -> float:
    """此刻的節奏＝**最短期程**那一軸的乘數（見檔頭「兩個角色分開聚合」）。"""
    fastest = max(_mult(r.horizon, p) for r in readings)
```

🔴 **機制歸因必須寫對**（他包曾歸因錯）：取的是**跨軸 max**，所以窗前半的 ×0.5 實際由
**7 天軸**在它自己 10080 分鐘窗裡的位置決定（far 門檻 5040 分）。
⇒ **照「動 `pace_far`」的方向修會同時鬆掉週軸**，該方向已否決。
docstring 逐字說明這是明示的設計選擇 ⇒ 改它屬 PRD §4.2 那張表的修憲級變更。

### §D-5 「已過去的 `resets_at`」四層誤判（`DEF-200-200`）

當回合實讀 `tools/lib/quota_policy.py:294-305`：

```python
    minutes = (when - now).total_seconds() / 60.0
    return minutes, (NOTE_SKEW if minutes < 0 else NOTE_OK)
```

任何負值一律標 `clock-skew`。但「快取的 `resets_at` 已過去」**不是**時鐘偏移
（本機時鐘實測無偏移）⇒ 診斷把 operator 指向錯的子系統。

當回合實讀 `tools/lib/quota_pace.py:551-559` `row_of()`：寫出的鍵只有 `ts`／`pct`／`live`／`fp`
——**不含 `resets_at`** ⇒「端點回報的 reset 有沒有漂掉」在歷史落款上結構性不可回答，
也使 `--reconcile` 長窗軸的假紅率不明。這是驗證①②③ 是否修好的前提，故同列。

### §D-8 量測值當常數（`DEF-200-203`）

〔他包回報，未複驗〕三個複審包各自跑的 22 分鐘內，`r`、長軸燃燒率、窗末樣本數移動 20~73%，
三包各自拿自己那一瞬去推翻別包 ⇒ **三包全錯**。
主控同輪兩個實例：① 把 4 小時前的量測值當現值寫進使用者可見回覆，且未帶量測時間戳
（失效機制＝**資訊源不對稱**：工具每次都印 `量測於=<戳>`，官方面板沒有戳）；
② 引用一條跨兩日、中間有 **31.62 小時**取樣斷層的落款序列，稱之為「同一天五次自洽的量測」。
本輪已落地輸出面 `stale_pace_hits()`（首次發火對象即主控）與輸入面 `--reconcile`；
**缺的是連續性（斷層）判準**——那與鮮度是兩件事，鮮度看單點年齡、斷層看相鄰兩點間距。

### §D-11 PRD↔實作歧異（`DEF-200-206`）

當回合逐項實查：

| 鍵 | PRD 側 | 實作側 | 歧異型態 |
|---|---|---|---|
| `STATE_RETAIN_VERSIONS` | §8-4 第 4 列，無前綴 | `file_state_repository.py:37-38` 讀 `AUTOCLAUDE_STATE_RETAIN_VERSIONS`、預設 `"2"` | 前綴 ＋ 值皆不同 |
| `CONFLICT_POLICY` | 三值 `ABORT｜RETRY_WITH_AGENT｜HUMAN_REVIEW` | `boot_self_check.py:36` `CONFLICT_POLICIES = ("HUMAN_REVIEW", "AUTO_AGENT")` | **互有對方沒有的值** |
| `DIRTY_SAVE_RETRIES` | §6 區塊 12（v2.1.9 補入），出廠 1、值域 0~3 | `dirty_worktree_rescue.py:46-47` 常數存在 | **零 env 讀取路徑** |
| `CONFLICT_POLICY`（env 面） | 同上 | `boot_self_check.py` 全檔 `environ`／`getenv` grep **0 命中** | **零 env 讀取路徑** |

⇒ 後兩列的後果相同且使用者無感：**改設定不會生效**。
依憲法（PRD 為最高法）：「實作沒照 PRD 做」修實作、「PRD 與實測不符」才修憲 ⇒ 逐項需裁決。

### §D-12 豁免鎖前提反轉（`DEF-200-207`）

當回合根層閘門第 4 支紅，逐字：

```
FAIL: test_the_next_round_cannot_reuse_the_exemption (test_adr_xplat001_c1c2_lock.TestPricingChangeExemptionExpiresOnItsOwn.test_the_next_round_cannot_reuse_the_exemption)
AssertionError: 17032 not greater than 17070 : 前提已不成立：baseline 已 ≤ total（＝已重釘）⇒ 本注入量不到「未重釘」那一側。此時請把 _PRICING_CHANGE_EXEMPT_ROUND 連同本鎖一起重新評估，不要直接刪
```

🔴 **這一支紅的原因與 `_PRICING_CHANGE_EXEMPT_ROUND` 的到期無關**（`live_repin_round()`
當回合實測 **100**，`100 > 100` 為 `False` ⇒ 到期那一側還沒到）。真因是 AutoClaude 側 `total`
在本輪長過了 `baseline`：`python AutoClaude/tools/check_loc_budget.py --json` 當回合實測
`total=17070`／`baseline=17032`／`cap=20438`／餘裕 `3368`、`violations` 為空。
🔴 **本節這三個數字已被同輪後續變更移動**（收尾窗口修 §E 之外的 checkpoint blocker，使 `total` 17070 → **17079**、餘裕 3359；`baseline`／`cap` 未動）⇒ 引用請以 `python AutoClaude/tools/check_loc_budget.py --json` 現查，勿引用本行。
§A 表記錄改後 total 為 `16483` ⇒ 本輪 AutoClaude 側之後又長了約 587 行（PRD 實作所致）。
⇒ 該鎖的**注入前提**（baseline > total 才量得到「未重釘」那一側）已消失，鎖失去鑑別力。
🔴 依該鎖自己的訊息，處置是「連同 `_PRICING_CHANGE_EXEMPT_ROUND` 一起重新評估，**不要直接刪**」
——本窗口未動它（動它就是為了讓閘門變綠而放寬判準）。

### §D-13 護欄層兩鎖互為死結（`DEF-200-208`）— 本節是本輪最重要的交付

🔴 **兩份取證衝突的定案：兩包各對一半，而且沒有一條不紅的路。**

當回合本窗口自量（`python -c` 直呼判準函式，非轉述）：

| 判準 | 當回合實測 | 結論 |
|---|---|---|
| `guard_line_problems(_FROZEN_GUARD_LINES, guard_lines_in_worktree(), …)` | **2 筆** | 🔴 紅 |
| ↳ ① `[成長]` | `86452 → 87544（+1092）` | 磁碟高於釘住值、未重釘 |
| ↳ ② `[逐檔漂移]` | 6 支檔（容忍 **0**） | `test_check_hooks_liveness.py 3433→3598`、`test_claim_provenance_r86.py 341→618`、`test_context_budget_guard.py 7713→8081`、`test_doc_loc_baseline_freshness_r60.py 7138→7318`、`test_quota_policy.py 2332→2432`、`test_check_pytest_baseline_sites.py 297→299` |
| `repin_growth_problems(_GUARD_LINES_REPIN_LOG)` | **`[]`** | ✅ 綠 |
| `repin_round_nets()` R100 | **355**（cap `net_cap_for_round(100)` = **850**） | 綠 |

**兩包各對一半**：
- 報「R100 淨額 355／`repin_growth_problems()` 回 `[]`」的那一包 ⇒ **對**，那是重釘日誌的現況。
- 報「R100 淨額 1445／上限 850 ⇒ 超額 595」的那一包 ⇒ **也對**，那是「**若把磁碟重釘進去**」
  的投影值。本窗口自算：`355 + 1092 = 1447 > 850` ⇒ 超額 **597**；該包的 1445／595 是
  早 2 行的磁碟讀數，**同一件事**，不是矛盾。

🔴 **結構性死結**（這才是要交棒的東西）：
1. **不重釘** ⇒ `guard_line_problems()` 那 2 筆紅（4 支測試紅）持續。
2. **重釘** ⇒ R100 淨額變 1447 > cap 850 ⇒ `repin_growth_problems()` 轉紅。
⇒ 在**不動任何常數**的前提下，本輪沒有讓這兩鎖同時綠的路。
本窗口**未重釘**（重釘會把紅換到另一個鎖上，並不解決問題），也**未調 cap／棘輪常數**
（那是為了讓閘門變綠而放寬判準，硬禁令第 4 條）。

分桶側另一筆紅（`prose` shrink-only 桶）當回合逐字：

```
[分桶成長] shrink-only 桶 `prose`：4119 → 4182（+63）——這一桶只准往下。守散文／守自己的鎖要長，先問「該被守的事實能不能移出散文」（棘輪自己列的第三條出口）；真的必須長，請帶四方複審裁決重釘。
```

🔴 成長來源是**真判準**（新增的「跑閘門不得讓 `ONBOARDING.md` 漂移」鎖），不是史料膨脹
⇒ 「搬史料抵銷」這條既有出口在這 63 行上不適用。

**交棒 R101 的三個候選處置（本窗口不自行裁決；承接列＝`DEF-200-208`）**：
(a) 暫緩重釘、接受 (a) 側 4 支紅並在 commit 訊息具名；
(b) 走「四方複審裁決重釘」（棘輪訊息自己指的出口），一次性核准 1447 的淨額；
(c) 把本輪新增的判準搬出護欄層掃描面（若判準本身不該住在 `tools/tests/`）。
🔴 三者皆需裁決，**不得**由任何單包自行調 `net_cap_for_round`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`。

### §D-14 `--reconcile` 紅綠自證：**經實測拒絕落地**（`DEF-200-213` ④）

掌舵者已裁決落地 `scratchpad/READY_TO_LAND_test_quota_reconcile_r100.py`（60 行，他包宣稱
「GREEN/RED 皆已實跑」）。本窗口落地前先實跑，**四個獨立理由否決落地**：

**① 它的「GREEN 已實跑」是假綠——綠的條件在根層閘門上不存在。** 當回合兩組對照實跑：

```
=== ① 不設 RECONCILE_REPO（＝根層閘門的實況）===
  File ".../probe_landing.py", line 12, in <module>
    sys.path.insert(0, os.path.join(os.environ["RECONCILE_REPO"], "tools", "lib"))
KeyError: 'RECONCILE_REPO'
PROBE1_RC=1

=== ② 設了 RECONCILE_REPO（他包宣稱的 GREEN 條件）===
Ran 4 tests in 0.002s
OK
PROBE2_RC=0
```

`tools/run_root_unittests.py` 不會設 `RECONCILE_REPO` ⇒ 落地即 **module-level import error**，
把基線由 `failures=7` 變成 7 紅 ＋ 1 error。該檔第 12 行用的是 `os.environ[...]`（下標式）
而非 `.get()`，故失敗發生在 **import 期**，不是某一個測試紅。

**② 它的受測對象不在版本控制內。** 當回合實查：

```
$ git ls-files --error-unmatch tools/lib/quota_reconcile.py
error: pathspec 'tools/lib/quota_reconcile.py' did not match any file(s) known to git
```

`tools/lib/quota_reconcile.py`（22438 bytes）是本輪新建但**未追蹤**的檔。落地一支
「受測對象不隨 clone 走」的測試 ＝ 在任何新 checkout／CI 上保證紅。
🔴 本窗口禁止任何 git 寫入 ⇒ 無法以 `git add` 消除這一項，**只有主控能**。

**③ 它把機器本地事實寫成 import 期常數。**
第 15 行 `LEDGER = open(os.path.expanduser("~/.autosdd/traces/quota_burn.jsonl"))`
在**模組載入時**讀一個機器本地檔（本機實測 35430 bytes）。CLAUDE.md 對這一類值逐字要求
「不隨 clone 走、不得寫成常數」；且 `CASE_A`／`CASE_B` 兩組斷言綁在該檔**當下的內容**上
（`2026-08-23T22:53`／`22:56` 兩個時刻），資料一輪替就失去意義。

**④ 它會讓 `DEF-200-208` 的死結變嚴重。** `tools/tests/` 磁碟面現值 +1092（見 §D-13）；
再加 60 行 ⇒ +1152，重釘投影由 `1447` 升到 `1507`（cap 850 不變）。本輪禁令明文
「不要新增任何測試檔，除了第【3】項明文指定的那一支」，而該項同時授權
「若判定它讓某個棘輪從『可重釘』變成『不可重釘』，回報並**不要落地**」——本節即該回報。

**⇒ 處置**：檔案留在 scratchpad，**未落地**、未計入本輪護欄層用量。
交棒 R101 的落地前置條件（三者皆須先成立；承接列＝`DEF-200-213`）：
1. `tools/lib/quota_reconcile.py` 進版控（**主控**在 commit 那一刻做）；
2. 第 12 行改為不依賴 env（用 `Path(__file__).resolve().parents[2]` 之類自解 repo 根），
   第 15 行的落款母體改為 **git-tracked fixture**，不讀 `~/.autosdd/`；
3. `DEF-200-208` 的護欄層死結有裁決後再談 +60 行。

---

## §E 四方審查（唯讀）交件的五筆新發現

四方（Architect／QA／SA／Dev 鏡）在收輪前以唯讀身分交件。本節逐筆記載**收尾窗口自己重跑**的
憑證；凡與交件數字不符者一律以本節實測為準並標「🔴 訂正」。

🔴 **本節原定的索引列 `DEF-200-217` 未能落地——帳本容量硬牆的判準是 `>=` 不是 `>`。**
任務書寫「未結列現況 97、`UNRESOLVED_ROWS_FAIL = 98` ⇒ 最多可新增 1 列」，該推導**差一**：
`unresolved_ceiling_problems()` 的條件逐字是 `if n >= UNRESOLVED_ROWS_FAIL`，
故 97 + 1 = 98 **當場撞線**。當回合實跑（先插入該列、再實測）：

```
未結列數＝98／全部 292 列｜warn=86 fail=98
❌ 未結列 98 筆（…）≥ fail 線 98。🔴 **不要調高本門檻**（那是砸溫度計）
```

⇒ 該列已**退出**（未結列回到 97、warn 帶）。可用容量是 **0 格**，不是 1 格。
本節的 ledger 側指針改掛在**同主題**的既有未結列（不新增列、不動任何門檻、不假結案）：

| 筆 | ledger 指針 | 位置 |
|---|---|---|
| E1／E3／E4 | `DEF-200-207`（ADR-XPLAT-013 仍 Proposed ＋豁免鎖前提反轉，同主題）| 狀態欄尾「續報 §E-1/3/4」 |
| E2 | `DEF-200-209`（缺口⑥ ＋ 護欄層無 ruff 閘門，本筆是它的續篇）| 狀態欄尾「四方續報＝§E-2」 |
| E5 | 🔴 **無 ledger 指針** | 帳本零同主題未結列、且不得為它硬塞進不相干的列（那正是 `DEF-200-213` ① 在治的體例違反）⇒ 只由本節 ＋ `R100_HANDOFF.md` 承接 |

🔴 **R101 第一件事**＝先結掉／指派掉至少 1 列，再把下方備好的 `DEF-200-217` 列原文貼進帳本
（逐字備在 `docs/04_planning/R100_HANDOFF.md`，實測 699 bytes ≤ `ROW_MAX_BYTES`）。

### §E-1〔blocker，本節最嚴重〕換尺是這一輪 LOC 閘門變綠的原因，而 ADR-XPLAT-013 沒有揭露

**逐檔（當回合實跑；「舊尺」＝ ADR 前的 `count_loc`，判準逐字＝「空行與行首 `#` 免費、其餘計價」）**：

```
tools/lib/quota_meter.py:        old=462 > 400   (new=310)
tools/session_resume_planner.py: old=789 > 750   (new=744)
tools/lib/hook_wiring.py:        old=428 > 400   (new=398)
tools/lib/quota_gate.py:         old=520 > 500   (new=366)
--- 新尺破線 ---
（空）
```

**同一支尺量 HEAD（＝本輪動工前）**：

```
tools/lib/quota_meter.py:        HEAD_old_ruler=399 budget=400 over=False
tools/session_resume_planner.py: HEAD_old_ruler=750 budget=750 over=False
tools/lib/hook_wiring.py:        HEAD_old_ruler=395 budget=400 over=False
tools/lib/quota_gate.py:         HEAD_old_ruler=500 budget=500 over=False
```

⇒ 四支在 HEAD 全部**貼著上限但未破線**（399/400、750/750、395/400、500/500），
**是本輪的工作把四支同時推破線的**；換尺讓 `[ROOT-TOOLS] 分級違規` 由 4 筆變 0 筆。
舊尺下本輪 LOC 閘門 rc=1，新尺下 rc=0——**這是同一次 commit 內的兩件事**。

**tier 政策自己印的補救手段逐字**——這正是那 4 筆破線在舊尺下會印出來的訊息
（`AutoClaude/tools/check_loc_budget.py:929`，`[ROOT-TOOLS] 分級違規` 那一段）：

> 「破線後不是「調高預算」而是拆職責／抽共用模組；真的不可壓縮才…」

同一支檔 `:876`（本輪同一次變更新寫的那句）：

> 「要省預算只有一條路：**少寫斷言**（拆職責／抽共用模組）。」

而換尺達成的效果是「同一批斷言換一把便宜的尺」＝**調高預算**，
**沒付拆職責的代價、沒經人審**，而且是被自己這兩句話逐字禁止的那個方向。

**母體級（291 支計價母體＝`build_reports()` ＋ `root_tools_reports()`，當回合實跑）**：

```
母體檔數 = 291
total: old=39774 new=30915 delta=-8859 pct=-22.3%
per-file violations: old=4 new=0
>=90% warn band: old=17 new=7
```

🔴 **訂正交件數字**：交件寫 `39753→30906`、`違規 5→1`、`警戒帶 18→7`；本節實測為
`39774→30915`、`4→0`、`17→7`。差異來自量測時點不同（本窗口在同輪修了
`AutoClaude/autoclaude/infra/repositories/file_state_repository.py`，該檔在 `build_reports()` 母體內），
**方向與量級一致（−22.3% 逐字相同）**，結論不變。

🔴 **主控失誤照實入帳**：主控在本輪多則交件裡把本變更描述為「關掉套利門、釋出 3955 行真額度」，
**未揭露它同時把當輪四筆破線變成零筆**。這兩件事在同一次變更裡，只講前者就是把
「本輪自己付不出來的帳」寫成「治理改善」。

🔴 **四方票必須重投**：先前的四方票是在不知道「換尺與本輪破線同批」的前提下投的
⇒ 依 `ADR-XPLAT-013:209`（明禁承辦包自行開複審）由**主控**重開，題目必須逐字包含本節。

### §E-2〔blocker〕第三道套利門，比前兩道都寬

**當回合實跑**（合成四支檔，`new_count_loc` ＝ 現行計價器、`old_ruler` ＝ ADR 前判準）：

```
arb_a.py: raw=200 new_count_loc=200 old_ruler=200   # 200 行實碼直寫
arb_b.py: raw=203 new_count_loc=1   old_ruler=203   # 同 200 行搬進 module docstring + exec(__doc__)
arb_c.py: raw=102 new_count_loc=102 old_ruler=102   # 100 筆資料表直寫
arb_d.py: raw=103 new_count_loc=1   old_ruler=103   # 同一張表存進 __doc__ 再解析
```

⇒ `200 → 1`（**−99.5%**）與 `102 → 1`（**−99.0%**），而 raw 行數與可執行語意逐字不變。
**兩招在舊尺下都省不到一分錢（203／103 全額）⇒ 這是本 ADR 新造的門**，且是同一族第三道，
一輪比一輪寬：第一道 docstring↔井號 −37.5%、第二道裸字串＋分號 −51%、第三道 −99.5%。
「以為關了、其實搬家」已經是**第三次**。

**現有防線的實況（當回合實查）**：

- `S102`（`exec` 偵測）**能抓到**：`ruff check --isolated --select S102 arb_b.py` → `S102 Use of \`exec\` detected` rc=1。
- 現行設定下**抓不到**：`ruff check arb_b.py` → `All checks passed!` rc=0。
- 🔴 **訂正交件敘述**：交件寫「`AutoClaude/pyproject.toml` 的 ruff **沒有 `select`**」——不成立，
  `AutoClaude/pyproject.toml:159` 逐字 `select = ["E", "F", "I", "UP", "W"]`，根層另有
  `tools/ruff.toml`（同一份清單，CI 第 16 道 ＋ pre-push 快層④ 為執行者）。**真因是兩處都沒有 `S`（bandit）系列**，
  結論（S102 無人執行）不變、機制敘述須改。
- `.claude/hooks/` 那一面**交件說對了**：`grep -rl ruff .claude/hooks/` → 0 命中；`.claude/settings.json` → 0 命中；
  `tools/ruff.toml` 的射程逐字只到 `tools/`（該檔檔頭自陳）⇒ hook 樹零 ruff 閘門。

**修法方向（QA 提，本節複驗其可行性）**：AST 層看該檔有沒有讀 `__doc__` 或呼叫 `exec`／`eval`，
命中就把該檔的裸字串改判斷言（不是全域禁 `exec`——那會製造假紅）。
🔴 **本輪不修**：淨加判準必落 `tools/tests/`，而該面已因 `DEF-200-208` 死結（磁碟 +1092 未重釘）
無不紅的路，加判準只會讓死結更深。

### §E-3〔blocker〕豁免到期鎖的判準一條件兩相反語意，已永久靜音

主牙＝`tools/tests/test_adr_xplat001_c1c2_lock.py::TestPricingChangeExemption::test_the_next_round_cannot_reuse_the_exemption`，
當回合紅、逐字 `AssertionError: 17032 not greater than 17079`。該 assert 的訊息逐字寫：

> 「前提已不成立：baseline 已 ≤ total（＝已重釘）⇒ 本注入量不到「未重釘」那一側。」

🔴 **該歸因是錯的**。`AutoClaude/.loc_baseline` 本輪**一字未動**（當回合實查
`git log -1 -- AutoClaude/.loc_baseline` → `1807474 2026-06-13`，內容仍是 `17032`）。
真因是 **total 長過了那個陳舊 baseline**（17079 > 17032）——同一個不等式 `baseline > total`
被拿來表達「已重釘」與「total 已長過陳舊 baseline」**兩件相反的事**。

**實跑**（`pricing_exemption_problems`，`baseline=17032／total=17079`）：

```
latest_round=101  -> []
latest_round=105  -> []
latest_round=120  -> []
latest_round=1000 -> []
```

⇒ 到期條件 `live > exempt_round and baseline > total` 的後半在今天結構上恆假
**⇒ 這道到期鎖再也不會成立，已永久靜音**。

**repo 內已有這個病的處方**：`tools/lib/baseline_origin.py`（為 `DEF-101-756`「用同一個值表達
兩件相反的事」抽出）⇒ 改判 **provenance**（baseline 是哪一輪、用哪一版尺釘的），
不要從不等式反推狀態。

**附帶一（可通約性）**：`check_loc_budget.py:804` 的 `policy_version` 仍是
`"v2-tiered+sd08-special"`（本輪 diff 對該行零命中）⇒ **尺換了、版號沒換**，
`.loc_baseline`（舊尺 17032）與 `total`（新尺 17079）**不可通約**，兩者相減無意義。

**附帶二（同輪即透支）**：豁免給的額度＝`17032 − 16483 = 549` 行，本輪消費 587 行，**超出 38 行**〔他包回報，未複驗〕。

### §E-4〔major〕`--update` 的語意反轉 ⇒ 屬修憲

`AutoClaude/tools/check_loc_budget.py:119` `TOTAL_INCREASE_LIMIT = 1.20`；
`:752` `cap = int(baseline * TOTAL_INCREASE_LIMIT)`；`:748-750` `--update` 走 `write_baseline(total)`。
⇒ 當回合算式實跑：

```
17032*1.2 -> 20438      # 現況
17079*1.2 -> 20494      # 執行 --update 之後
```

執行 `--update` 會把 baseline `17032 → 17079`、**cap `20438 → 20494`（+56）**。
ADR-XPLAT-013 與 `pricing_exemption_problems()` 的出口敘述都把它描述為「沒收陳舊餘裕的出口」，
**實際是加碼**。照條文做的人會以為自己在收緊 ⇒ 這不是改碼能解決的，屬**修憲**
（要改 ADR 條文：要嘛換一個真的會收緊的出口，要嘛把 20% 緩衝與重釘解耦）。

### §E-5〔major〕Rule 9 的第三種洗白形態無人守

`sys.path.insert` ＋ **裸模組名** import：importlinter 與 AST 兜底判準**都看不到**。

**當回合實跑**（餵 `AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py::_harness_imports`
兩份合成檔，兩者是**同一個相依**）：

```
direct    -> ['tools.lib.quota_limits']
laundered -> []
```

importlinter 那一半：`AutoClaude/.importlinter` 的 Rule 9〈誠實劃界〉逐字只登記
「importlinter 對**解析不到的模組**是沉默的」，而裸模組名對 `root_packages = {autoclaude, tools}`
定義上就解析不到 ⇒ 同一個沉默把這第三種形態一起蓋掉，**該節未登記它**。
（Architect 的合成自證「`import tools.lib.victim` → broken；改走 sys.path＋裸名 → `Contracts: 1 kept, 0 broken`、rc=0」
〔他包回報，未複驗〕——本節只複驗了 AST 判準那一半，那是可零成本量的一半。）

**它已是慣用寫法**：`grep -rln "sys.path.insert" AutoClaude/tools/` 當回合 19 命中，
扣掉 `run_local_nightly.ps1` ＝ **18 支 `.py`**（交件的「18 支」對）；本輪的計價判準跨界
（`check_loc_budget.py` 讀 `tools/lib/guard_line_taxonomy.py`）走的正是這條路。
任何人把這個寫法照抄進 `autoclaude/`，**兩道守衛都保持全綠**。

### §E-6 本節的處置與交棒

| 筆 | 級 | 誰能處置 | 本輪為何不做 |
|---|---|---|---|
| E1 | blocker | 🔴 **主控**（開四方重投票） | ADR-XPLAT-013:209 明禁承辦包自行開複審 |
| E2 | blocker | R101（淨加 AST 判準） | 判準必落 `tools/tests/`，受 `DEF-200-208` 死結阻擋 |
| E3 | blocker | R101（改 provenance 判準）＋ 修憲（`policy_version`） | 同上；且與 E1 的重投票同一批較省 |
| E4 | major | **修憲**（改 ADR 條文，非改碼） | 條文變更須四方，不得由承辦包自行改 |
| E5 | major | R101（`.importlinter` 補登記 ＋ AST 判準擴面） | 同 E2：淨加判準受死結阻擋 |
