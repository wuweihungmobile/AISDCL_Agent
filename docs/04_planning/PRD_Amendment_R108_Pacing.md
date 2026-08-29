# PRD 修憲提案 — R108 配速批（DEF-200-197／198／199 ＋ 配速三改動 (a)(b)(c)）

| 欄位 | 值 |
| :---- | :---- |
| 狀態 | **Proposed（三審＝終審承接修訂完成）**。一審判決＝Architect **REJECT**／SA・SD・QA APPROVE_WITH_CONDITIONS；二審判決＝Architect／SA／SD 三鏡共 7 筆 blocking，紀錄 `docs/06_quality/CrossPlatform_R108_Review.md`；本版逐條承接一審 B9~B19、二審 6 筆 blocking ＋ 兩輪標（→修憲）的 non-blocking |
| 提案輪 | R108（架構輪；本文件產出時**零生產碼改動、零帳本改動、零 PRD 改動**） |
| 標的 PRD | `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` |
| 提議落款版本 | **v2.1.10**。🔴 **狀態欄必須具名寫出前置**（B18／SA→修憲）：本批多處前提取自 **v2.1.8**（§4.1.5／§4.2.4）與 **v2.1.9**（§11.2 (a)~(d)、`:549-555` 訂正），而修訂表現查〔實讀 `:9-14`〕**只有 v2.1.4 標「已生效」**（`:9`）；v2.1.5「待四方複審後生效」、v2.1.6「規格化後待實作」、v2.1.8「僅完成規格化」、v2.1.9「經獨立複審 **REJECT** 承接、逐條修訂後**待再審**」（`:14`，修訂表最後一列）⇒ v2.1.10 是**疊在一疊未生效修憲上**的第五層（🔴 **v2.1.7 刻意不列入這個計數也不算已生效**——它的措辭既非「已生效」亦非任何待審字面，歸類判準與理由的唯一出處＝**§10.2**，三審 QA 承接） |
| 覆蓋缺陷 | `DEF-200-197`（帳本 `:203`）／`DEF-200-198`（`:204`）／`DEF-200-199`（`:205`）；關聯背景 `DEF-200-200`（`:206`） |
| 覆蓋改動 | Playbook §6 第 6 條 (a)(b)(c)（`docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md:248`） |
| 一審承接摘要 | B9 §6.2 除數／B10 §6.1-pre 運算元對映／B11 §3.1 承重句算術（15→14）／B12 §3.6+§6.9+Q6 爆炸半徑／B13 §2.3 retry_after 完整管線（6 落點跨 2 檔）／**B14~B16 §4.2 L2 判準改絕對地板、家改 `quota_pace.windows()`**／B17 §2.5+§6.6 不與 ADR-XPLAT-009 §2.2 造第二個家／B18 §10.2 落款前置逐條清單／B19 §7 P9 改結構斷言。**十一筆全部照修，零 contested。** |
| 一審承接輪自查出的四筆（一審未點到） | ① **§6.2 原「沒有家的字面」被證偽**——`T_MIN_MINUTES` 在 PRD `:732` 有家、`:864-865`／`:868` 有兩個消費端 ⇒ 廢除射程由 2 站點改為 5 站點（附錄 A `:2520` 為史料不動），廢除理由改為「語意重疊」；② **今天的跨軸 max 本身就違反 §4.2.2-b (4)**（手填窗長面 32800 個加軸對取樣中 2670 個讓 rec 變大）；③ ~~429 真正進到快取的路是 `pace_state()` 不是 `refresh_quota_blocking()`~~ ⇒ 🔴 **二審 SD-N6 判此筆自查本身是錯的，本版訂正**：429 今天**兩條路都寫快取**，不是二擇一——`rate_limited_reading()` 回的是**完整 dict（非 `None`）**〔現查碼 `quota_meter.py:730-738`〕⇒ `refresh_quota_blocking()` `:622` 的 `reading is None` 判 **False**、`:625` 的 `write_cache` 照樣執行，而該函式自己的 docstring `:721`／`:724` 逐字自陳「唯一的呼叫端 `quota_gate.refresh_quota_blocking()`……本讀數**會被寫進快取**」；`pace_state()` `:705-707` 是**額外**的第二個寫入端，且是唯一會把 `fp: []` 寫進燃燒落款的那一條（`record_burn()` 的唯一呼叫點在 `pace_report()` `:731`）。⇒ 原自查把「唯一的落款污染路徑」誤寫成「唯一的快取寫入路徑」，與 M197-2 (i)「兩個寫入端」自相矛盾，本版三處同步改寫（§2.3／本欄／§8-6）；④ **Q4 的 `ENABLE_BURSTING=true` 是 PRD 現行條文既有值**（`:766`），不是本案的新主張 |
| 二審承接摘要（本版） | **Architect N1（B14 未解）**：L2 判準的家由 `windows()` 改為 `window_minutes(kind)`——照修，但**附一筆本輪親跑的反證**（見 §0.3／§4.2 L2／§8-11／§10 Q9）：換家只關掉「分類」這一條依賴通道，`windows()` 的鄰軸繼承仍**透過 horizon** 影響 rec ⇒ §4.2.2-b (4) 在今天的 `resolve()` 之下**結構上到不了 0**，本版把 (4) 的射程與 P16 的可綠面同步收窄，並新增 Q9。**Architect N2**：`T_WRAP_MINUTES` 雙角色拆成兩鍵（§6.2／§7 P18／§10 Q5）。**Architect N7**：判準邊界句改「窗長 ≥ 地板即不適用」＋明記 10080 恰等於週窗的邊界風險。**SA-1／-2／-3**：§6.6 (A) 臂逐字複製原文、§6.1-pre 與 PRD `:2241` 合流、對映表補 裸 `C`／`C(t)`。**SD-N6**：見上一列 ③。**七筆全部照修；唯一 contested-with-evidence 是 N1 的「換家即 0」那半句**（照修但不照抄結論）。 |
| 三審（終審）承接摘要（本版） | **QA B-I（§7 P16 第 ④ 臂零鑑別力）**：原「> 0」在封閉面（三 home 建構上等價、皆 0）與擴大面（windows 2796／hybrid 2036 皆 > 0）**都紅不起來** ⇒ 改比較式斷言（**2796 > 2036**〔本輪實測〕），並訂正原括號誤引的「1972」（那是「把 L2 整條拿掉」那一列，不是換家的證據）。**QA B-II（§7 P17 第 ③ 臂恆綠）**：原具名注入 `spend`＋`monthly_all` 在兩個家下都判「不適用」（43200 ≥ 地板）⇒ 換成 `spend`＋`five_hour`（同 `resets_at`），〔本輪實測〕`windows()` 繼承 **300 < 10080** ⇒ 分類由「不適用」翻成「適用」，紅面成立。**Architect B-III（§6.1 (4b) 的單一歸因是假的全稱宣稱）**：存在**第四條通道＝gate 聚合面**——`gate_list` 由空翻非空使煞車軸整批離開聚合面，**與窗長文法完全無關**；本輪逐例重現定向兩例 **4 → 16**（gate 面關閉時同兩例 4 → 4）、母體 `L1` **0 → 7515**／`L2abs` **0 → 8691** ⇒ (4b) 改多歸因並加合取項、刪「取消繼承 ⇒ (4) 歸零」、§7 P16 母體同步加該條件、§10 Q9 補候選 **(iv)**（標明本輪未實測）。**Architect B-IV** 落在 `ADR-XPLAT-013_Phase2_Proposal_R108.md`（方向鎖極性抄反 ＋ 紅綠自證注入隨被判常數滑走），已在該檔修。**四筆全部照修，零 contested。** |

【2026-08-29 訂正注：掌舵者已對 §10 Q1~Q9 完成方向裁決（Q7＝v2.1.9＋v2.1.10 兩版合併同審；逐題見 `AutoSDD_Adjudication_Record_R110.md`）。落款生效待合併同審，本檔 Status 不變。原文保留。】

---

## 0. 本文件是什麼／不是什麼，以及每個數字怎麼來的

**是**：一份可被四方逐條投票的設計提案，含修法值域、狀態字、降級路徑、方向鎖、PRD 修訂文本草案。
**不是**：實作。本輪不改 `.py`／不改帳本／不改 PRD。修憲文本要等四方複審通過後由另一包落款。

### 0.1 取數紀律

本文件所有數字皆為**當回合實測**，來源分三類，逐處標明：

| 標記 | 意思 | 怎麼複現 |
| :---- | :---- | :---- |
| 〔現查碼〕 | 直接 `Read`／`Grep` 生產碼得到的行號或字面 | 文中給出檔案與行號；行號會漂移，複現時以「函式名」為錨 |
| 〔實讀〕 | 直接 `Read` 一份 `.md`（PRD／ADR／Playbook／複審紀錄）得到的行號或字面 | 同上，錨是節號 |
| 〔探針〕 | 本輪在 scratchpad 寫的**唯讀**探針呼叫生產純函式算出來的 | §0.2 給出可貼進 `python -` 的最小重現碼 |
| 〔本輪實測〕 | 一審承接輪（修復包）自己重跑的探針輸出，與提案輪的〔探針〕分得開 | §0.3 給出重跑碼 |
| 〔帳本〕 | 引自 `docs/06_quality/AutoSDD_Defect_Log.md`，**他包回報、本輪未複驗者一律照原樣標注** | 標行號 |

🔴 **本輪零網路呼叫**：不打 metering 端點（`DEF-200-216` 判例——自造 429 不得計為活體驗證，且探針輪詢會製造真事故）。所有配速數字都是對**純函式**餵合成輸入算出來的。

### 0.2 探針最小重現碼（複審者請自己跑一次，不要採信本文件）

```python
import sys, itertools
sys.path.insert(0, r"<repo>/tools/lib")     # 🔴 這兩支模組彼此用**裸名** import，
import quota_policy as P, quota_pace as W   #    必須把 tools/lib 本身放進 sys.path
p = P.DEFAULT_POLICY
BANDS = (P.BAND_FREE, P.BAND_NOTICE, P.BAND_CONVERGE, P.BAND_PREPARE, P.BAND_HALT)
HOR   = (W.AXIS_NEAR, W.AXIS_MID, W.AXIS_FAR, W.AXIS_NONE)
for b in BANDS:                              # ⇒ §3.1 的 cap 值域窮舉表
    print(b, [(h, P._cap_for(b, h, p), P._rec_for(b, h, p)) for h in HOR])
```

### 0.3 方向不變式的重跑探針（一審 B14~B16 ＋ 二審 Architect N1）

#### 0.3.1 🔴 注入面已整個換掉（二審 Architect N1 的機械後果）

一審承接輪的探針把軸注入成 `(band, window_minutes, minutes_to_reset)`——**窗長當成軸的內在屬性手填**。二審 Architect 指出那個注入面**繞過了判準指定的家**：`window_minutes` 一旦是注入值，「窗長從哪裡來」這個問題就在判準的射程外，於是 `L2abs` 必然回 0（恆綠）。本版的注入面改為：

```python
# 軸 = (band, kind, minutes_to_reset)     ← 🔴 kind 是字串，窗長**一律經指定的家取得**
#   resets_at 由 minutes 導出（同 minutes ⇒ 同 resets_at 字串 ⇒ 觸發鄰軸繼承）
#   horizon  由 quota_pace.horizon(minutes, window, accel_abs, far_abs) 導出，不手填
# 三種「家」（home）：
#   windows ：窗長 = quota_pace.windows()        （同 reset 鄰軸繼承最短窗長＝一審指定的家）
#   grammar ：窗長 = quota_pace.window_minutes(kind)（只讀該軸自己的 kind；解不出 = None）
#   hybrid  ：horizon 用 windows()、**只有 L2 的適用性判定**用 window_minutes(kind)
#             ⇒ 這一格才是「production 的 horizon 導出不動、只換 L2 的家」的真實語意
# 取樣：kind ∈ {five_hour(300), weekly_all(10080), monthly_all(43200), spend(None), session(None)}
#       × minutes ∈ {15, 504, 6000} × band ∈ {free,notice,converge,prepare} = 60 軸
#       ⇒ 基底 2 軸（C(61,2)=1830 組）× 加 1 軸（60）= 109,800 個加軸對
# 封閉面對照組：kind 只取窗長皆解得出者 {five_hour, one_day, weekly_all, monthly_all}
#       ⇒ 48 軸、56,448 個加軸對（此面上三個 home 在建構上等價）
```

#### 0.3.2 〔本輪實測〕輸出逐字（含解不出窗長的 kind｜109,800 個加軸對）

```
home=windows today  加軸對數= 109800 違反=  9156
home=windows L1     加軸對數= 109800 違反=  1972  首例 S=(('free','five_hour',15.0),('free','spend',504.0)) + x=('free','weekly_all',504.0) : 4 -> 16
home=windows L2abs  加軸對數= 109800 違反=  2796
home=grammar today  加軸對數= 109800 違反=  7336
home=grammar L1     加軸對數= 109800 違反=     0
home=grammar L2abs  加軸對數= 109800 違反=     0
home=hybrid  today  加軸對數= 109800 違反=  9156
home=hybrid  L1     加軸對數= 109800 違反=  1972
home=hybrid  L2abs  加軸對數= 109800 違反=  2036  首例 S=(('free','five_hour',15.0),('free','spend',504.0)) + x=('free','weekly_all',504.0) : 4 -> 16
```

〔本輪實測〕**封閉面**（窗長皆解得出，56,448 個加軸對）：**三個 home 逐格相同**——`today` 3640／`L1` **0**／`L2abs` **0**。

〔本輪實測〕Architect 反例逐字複現：

```
windows(spend + monthly_all 同 reset) = (43200.0, 43200.0)
windows(spend 單獨)                   = (None,)
window_minutes('spend')               = None
```

#### 0.3.3 🔴 這一次重跑釘住六件事（第 4、5 件是二審才出現的；**第 6 件是三審才出現的，且它推翻了第 4 件的後半句**）

1. **B14 成立、且成立的理由比一審寫的更廣**：`windows()` 當家時，一條軸的窗長會因為「同 reset 的鄰軸有沒有出現」而改變（上方反例逐字：`spend` 單獨是 `None`、旁邊擺一條 `monthly_all` 就變 43200）⇒ 分類依賴輸入集合。
2. **換家（`window_minutes(kind)`）真的改善了 L2 這一面**：`L2abs` 由 2796 降到 2036〔windows-home → hybrid〕，且改善量（760）全部來自「L2 的分類不再隨集合變動」。
3. **今天的跨軸 max 本身就違反這條不變式 9156 次**（射程外附帶發現，記入 §8-9）⇒ §6.1(4) 對**今天**就是一條真的會紅的不變式，L1 是把其中一條通道轉綠的那一步。
4. 🔴 **換家**不會**讓 (4) 歸零，而一審承接輪的探針之所以看得到 0，正是因為它手填窗長**：`hybrid` 的 `L2abs` 殘留 **2036**，而**把 L2 整個拿掉**（`L1`）殘留 **1972** ⇒ 殘留的主體不是 L2，是 `windows()` 的鄰軸繼承**經由 horizon** 影響 rec 這條**獨立通道**（首例逐字：`spend` 剩 504 分在無鄰軸時窗長 `None` ⇒ 絕對門檻 360 ⇒ `far` ×0.5；加一條同 reset 的 `weekly_all` 之後繼承 10080 ⇒ 相對門檻 `near=1008` ⇒ `near` ×2.0 ⇒ rec 4→16）。⇒ **(4) 的完全關閉至少還需要兩件事**：第三件＝把逐軸窗長變成該軸 kind 的純函式（即 `resolve()` `:392` 不再繼承）；🔴 **第四件＝gate 聚合面，由三審 Architect 指出、本輪實測坐實（見下方第 6 件）**。⇒ 🔴 **「做完第三件 (4) 就歸零」這句話本版撤回**（它在第 6 件的實測下為假），本批兩件都**不做**，具名登記於 §8-11 ＋ §6.1 (4b) ＋ §10 **Q9**。
5. 🔴 **只有 `grammar`（連 horizon 一起改成純函式）那一格同時滿足「(4)=0」與「四情境 4/8/8/1」**（🔴 **那個 0 的射程僅限「省略 gate 面」的探針**，見第 6 件）；`hybrid` 那一格的 **A2 由 8 掉回 4**（§4.3 表）——因為 `session` 的窗長文法解不出 ⇒ L2 對它**永遠不適用**，而它與 `five_hour` 是**同一條底層限制被回報兩次**（`quota_pace.py:138-142`〔現查碼〕逐字），`min()` 讓較嚴的那一格勝出 ⇒ L2 在本 repo 最重要的那一對軸上被中和。這是本批**唯一的 contested 半句**，處置見 §10 Q9。
6. 🔴 **第四條通道＝gate 聚合面（三審 Architect A1；本輪逐例實測坐實，判詞成立、無異議）**。上列三個 home 的探針**都省略了 `decide()` 的 `gate` 這一段**（`quota_policy.py:634-635`〔現查碼〕`gate_list = [r for r in readings if _in_cap_gate(r, active_model)]`／`gate = gate_list or readings`）。把它接上之後，**即使每一條軸的窗長都由文法解得出**，(4) 仍會被違反——機制是**成員資格翻面**：`gate_list` 由空翻非空的那一刻，`FALLBACK_KINDS`／未命中的 `MODEL_SCOPED_KINDS` 那些**煞車軸整批離開聚合面** ⇒ rec 變大，與窗長文法**完全無關**。〔本輪實測，逐字〕
   - 定向兩例（Architect 具名，本輪原樣重現 **4 → 16**）：`S = seven_day_overage_included ×2`（free／剩 6000 分）＋ `x = five_hour`（free／剩 15 分）⇒ **gate 關 4→4（不違反）／gate 開 4→16（違反）**；`S = weekly_scoped + seven_day_opus` ＋同一個 `x` ⇒ **同樣 4→4 vs 4→16**。兩例在 `grammar`／`hybrid`／`windows` 三個 home、`L1`／`L2abs` 兩個 mode 下**逐格相同**。
   - 母體普查（**窗長皆由文法解得出**、但含 FALLBACK／MODEL_SCOPED 桶名的 5 個 kind × 3 minutes × 4 band ＝ 60 軸、109,800 個加軸對）：`L1` **gate 關 0 → gate 開 7515**；`L2abs` **0 → 8691**（grammar 與 hybrid 兩 home 逐格相同）。
   - 🔴 **關得住它的合取項本輪也一起量了**：母體再加一條「**基底集合 S 自己的 `gate_list` 非空**」⇒ 上述兩格**雙雙回到 0**（69,840 個加軸對）。⇒ 這就是 §6.1 (4b) 新增的那個合取項與 §7 P16 母體限定的實測依據。
   - 誠實劃界：三審 Architect 自己那一輪在 grammar-home＋gate 下得 **1979**，本輪同一方向的普查得 **2247**（開放面 109,800，含解不出窗長的桶名）。🔴 **兩個數不得互相校驗、不得相減**（gate 模型的射程可能不同：本輪同時排除 `FALLBACK_KINDS` 與未命中的 `MODEL_SCOPED_KINDS`）；**方向一致**（gate 關 0、gate 開 > 0），而方向才是判準要斷言的東西。

---

## 1. 座標校正表（帳本行號 → 本輪現查行號）

帳本立案當時的行號已漂移。本表是本提案的座標 SSOT；下文一律用**本表右欄**。

| 帳本原記 | 本輪現查〔現查碼〕 | 說明 |
| :---- | :---- | :---- |
| `quota_meter.py:716` `rate_limited_reading()` 回 `pct=100.0` | `quota_meter.py:708` 定義／**`:730` 是 `pct: 100.0` 那個字面**／`:738` 是 `posture={} schema_keys=[] account_key=None` 那一行 | 三件事在同一個 return 裡 |
| `quota_policy.py:527-531` `_pace_of` | **`quota_policy.py:546-551`** | 函式體 6 行 |
| — | `_mult` `:394`／`_cap_for` `:424`／`_rec_for` `:441`／`axes_of` `:511`／`decide` `:597` | 199／198 的落點 |
| — | `Policy` 欄位：`cap_notice` `:222`／`max_fanout` `:225`／`degraded_cap` `:232`／`pace_near` `:236`／`pace_far` `:237` | 值域論證用 |
| — | `quota_pace.py`：`thresholds` `:156`／`anchor_margin_pp` `:186`／`lead_pp` `:202`／`burn_step` `:230`／`effective_horizon` `:258`／`row_of` `:555`／`bursting_ok` `:589` | (a)(b) 的落點 |
| — | `quota_gate.py`：`FANOUT_WINDOW_SECONDS` `:140`／`core_signature` `:303`／`record_burn` `:334`／`pace_report` `:719` | (b)(c)／197 下游 |
| — | `quota_messages.py::pace_line` `:247` | 198 的輸出面 |
| — | `quota_meter.py::retry_after_at` `:669`（`DEF-200-196` fixed@R105 的落點在 `:697-698`） | 197 的相容性面 |
| **本版新增（一審承接）** | | |
| `refresh_quota_cache`（提案輪誤植的函式名） | **不存在**。全庫僅存於 `quota_meter.py:753` 的一句過期 docstring〔現查碼〕；真名 **`quota_gate.py::refresh_quota_blocking` `:597`**（SD→修憲 non-blocking） | M197-2／§8-6 的落點 |
| — | `quota_meter.py::measure_detail` `:741`（429 分支 `:767-771`）；**生產呼叫點共 4 處**〔現查碼〕：`quota_meter.py:802`（`measure()`，取 `[0]`）／`:844`（`refresh_detail()`，解 2 元組）／`quota_gate.py:621`（`refresh_quota_blocking()`，解 2 元組）／`quota_gate.py:705`（`pace_state()`，取 `[0]`） | M197-4 管線的第一段（B13） |
| — | `quota_gate.py`：`note_degraded` `:552`（含 `claim_once` TTL 閂鎖 `:567`、痕跡 `append_record` `:570-573`）／`_blank` `:379`／`read_quota` `:389`（TTL 判準 `:413`）／`core_signature` `:318`／`quota_floor_reading` `:631-652`／`pace_state` `:705-708`／`pace_report` `:719`（`record_burn` 呼叫點 `:731`） | M197-2／M197-4 管線的第二、三、四段 |
| — | `quota_pace.py`：`_UNIT_MINUTES` `:77-81`（含 `month/months: 43200`）／`_PERIOD_MINUTES` `:81`（含 `monthly: 43200`）／`window_minutes` `:120`／`windows` `:143`／`amortize` `:309`／`amort_for` `:406` | L2 判準的家（B15／B16） |
| — | `quota_policy.py`：`KNOWN_KINDS` `:143-144`／`NOTE_UNKNOWN` `:153`／`QuotaState.account_key` `:205`／`decide()` unmeasured 分支 `:608-618`；LOC 自陳 `:503-504` | 197／B17 的落點 |
| — | `docs/04_planning/ADR/ADR-XPLAT-009-quota-plan-change-adaptive-amortization.md`：狀態 **Accepted** `:3-4`；§2.2 `:37-55`（`∩ KNOWN_KINDS` 定義 `:42`、「未知桶名增減＝schema 演進、不觸發攤提重置」`:46-49`）〔實讀〕 | B17 的第二個家在哪 |
| — | `tools/tests/test_adr_xplat001_c1c2_lock.py`：`_REPIN_NET_CAP_DUE_ROUND = 109` `:1318`／`_REPIN_NET_CAP_DUE_TARGET = 610` `:1319`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` `:1237`／排程最後一列 `(107, 630)` `:1231`〔現查碼〕 | §9 鐵律七的第三個持有面（SD→修憲） |
| **二審承接新增** | | |
| `T_MIN_MINUTES` 的 5 個站點（標的 PRD） | `:451`（hold 門檻）／`:453`（除數下限）／`:732`（常數定義，`T_MIN_MINUTES = 2.0`）／**`:864-865`（hold 消費端，🔴 兩行，一審承接輪誤壓成一行）**／`:868`（除數消費端）；`:2520` 為史料不得改〔皆實讀〕 | §6.2 廢除射程（B9 ＋ 二審 SA non-blocking） |
| L2 判準的家（本版改） | `quota_pace.py::window_minutes` **`:120`**（該軸 kind 的純函式，✅ 採用）／`::windows` `:143`（鄰軸繼承，❌ 本版撤回）／繼承的立案註解 `:138-142`／`::resolve` **`:392`**（`wins = windows(...)` 的唯一站點＝繼承進入 horizon 的入口）〔皆現查碼〕 | §4.2 L2／§6.5 R-4.2.8-1b／§8-11（二審 Architect N1） |
| 429 的兩個快取寫入端（本版訂正） | `quota_meter.py::rate_limited_reading` `:708`（回值 dict 本體 `:730-738`）／過期 docstring `:721`（「唯一的呼叫端」）與 `:724`（「本讀數會被寫進快取」）；`quota_gate.py::refresh_quota_blocking` `:621-625`／`::pace_state` `:705-707`／`::record_burn` 唯一呼叫點 `:731`〔皆現查碼〕 | §2.3 M197-2 (i)／§8-6（二審 SD-N6） |

---

## 2. DEF-200-197 — 429 的方向本身錯

### 2.1 根因複述（含本輪複驗）

**帳本原文**（`AutoSDD_Defect_Log.md:203`）：429 是 metering 端點的速率限制、非模型額度，而 `rate_limited_reading()` 回 `pct=100.0` ⇒「量不到」被轉譯成「量到 100%」；同函式併回 `posture={}`／`schema_keys=[]`／`account_key=None` ⇒ 指紋抹空、被判換帳號而重新累積攤提。

**本輪複驗**〔探針〕——餵 `{"retry-after": "60"}` 給 `rate_limited_reading()` 再進 `decide()`：

```
axes        = [{'kind': 'rate_limited', 'pct': 100.0, 'resets_at': '…T12:01:00+00:00',
                'severity': 'critical', 'via': 'http-429-floor'}]
posture     = {}          schema_keys = []          account_key = None
decide()   ⇒ cap=0  rec=0  band=halt  binding=rate_limited
'rate_limited' in KNOWN_KINDS ⇒ False        逐軸 note ⇒ 'unknown-kind'
```

三個獨立的錯，帳本併為一列，本節拆開：

- **E1（方向）**：一次**遙測面**的 429 被轉譯成 `band=halt, cap=0` ＝全面停工。這與本 repo 通篇「量不到 ≠ 量到零、也 ≠ 量到 100%」直接相反，而同一支檔 `:759-760`〔現查碼〕自己就逐字寫著「回 0 ＝永遠正常（靜默失明），回 100 ＝永遠 halt。兩個方向都不可接受，所以只能回 `None`」——**`measure_detail()` 對其他所有失效都遵守這句話，只有 429 這一格違反它**。
- **E2（指紋抹空）**：`core_signature()`（`quota_gate.py:303`）只算 `KNOWN_KINDS ∩ axes`；`rate_limited` 不在 `KNOWN_KINDS`〔探針〕⇒ `kinds = ()`，而 `state.account_key is None` 且 `state.usable()` 為真（有 1 軸）⇒ 走 `:321-325` 的 `note_degraded("no-account-key", …)`，回傳 `()`。⇒ ①`core_signature_change_note()` 會印一句「偵測到帳號軸組合改變」＝**假話**；②`record_burn()`（`:334`，前置條件只有 `state.usable()`）**會真的寫一列 `fp: []` 到燃燒落款**——即 `DEF-200-216` 描述的那條合成軸。
- **E3（note 用錯字）**：`unknown-kind` 的定義是「伺服器吐出一個本 repo 從未列舉過的 kind」（`quota_policy.py:151-153`〔現查碼〕）。`rate_limited` 是**本 repo 自己造的**，伺服器一個字都沒說。今天用同一個字面 ⇒ 兩件不同的事共用一個訊號。

### 2.2 「當初為什麼這樣寫」的理由已經被後續修復推翻（這是本節最重要的論證）

`rate_limited_reading()` 的 docstring `:712-715`〔現查碼〕逐字寫：

> 🔴 為什麼是「讀數」而不是「量不到」：`None` 在下游是 `BAND_UNMEASURED` ⇒ `cap=degraded_cap`（**出廠等於 `cap_converge`**）⇒ 429 換來的是比 70% 帶還寬鬆的姿態。

那個前提在 **R100 已經消失**：`Policy.degraded_cap` 出廠值現查 **2**（`quota_policy.py:232`），且 `decide()` `:614` 另夾 `floor = min(max(1, degraded_cap), max(1, cap_prepare))`〔現查碼〕。也就是說**今天回 `None` 換來的是 `cap=2`（＝`cap_prepare`，比 converge 帶更緊），不是「更寬鬆」**。

⇒ 這是與 `DEF-200-193` 同型的一類：**「刻意不做某事」的唯一理由已被後續修復證偽，而那個判斷沒有回頭複查的機制**。本提案建議把它記成一個可重複出現的形態（見 §8）。

### 2.3 修法設計

**M197-1（值域／狀態字）**：`measure_detail()` 遇 429 改回 `(None, REASON_RATE_LIMITED)`，走既有的「量不到」路徑，得 `band=BAND_UNMEASURED`、`cap=rec=degraded_cap`（現查 2）。

- 值域：`cap ∈ {1..cap_prepare}`（由 `decide()` `:614` 的既有夾層保證），**不是 0、不是 None**。
- 狀態字：`reason` 保留既有 `REASON_RATE_LIMITED = "http-429-floor"`〔現查碼 `quota_meter.py:137`〕，**但字面應改名**——`floor` 這個字正是把「量不到」寫成「地板讀數」的來源。建議 `"http-429-unmeasured"`，並在 `quota_limits.py` 的消費端同步（該檔 `:16` 有一個同族的 `quota_floor_reading()` L3 地板，**射程不同、不要一起改**：那一支是 transcript 地板，有真的用量證據）。
- 降級路徑：`read_quota()` 的 TTL 命中即等於「退避一個 TTL 視窗、期間持收緊姿態、零額外呼叫」——**這一段原 docstring `:724-727` 的論證完全成立，逐字保留**，只是姿態從 `halt` 換成 `unmeasured`。

**M197-2（指紋不得抹空）**：429 路徑**不得**產生一份會蓋掉好快取的 payload。兩個等價落點，建議取前者：

- (i) `measure_detail()` 回 `None` ⇒ **兩個**寫入端結構上都不會寫快取。🔴 **本項一審前標「未逐行複驗」，一審承接輪已逐行複驗並訂正座標**（SD→修憲）：函式名不是 `refresh_quota_cache`（該字面全庫只剩 `quota_meter.py:753` 一句過期 docstring），而且**不只一個寫入端**——
  - `quota_gate.py::refresh_quota_blocking` `:621-625`〔現查碼〕：`reading, reason = measure_detail(timeout)`；`if reading is None: note_degraded(...); return False` ⇒ **`write_cache` 在 `None` 分支之後**，回 `None` 即結構上寫不到。
  - `quota_gate.py::pace_state` `:705-707`〔現查碼〕：`reading = measure_detail(...)[0]`；`if reading is not None: write_cache(reading, quota_cache_path())` ⇒ 同樣由 `is not None` 守著。
  - 🔴 **二審 SD-N6 承接（本版訂正，前一版此處寫錯）**：一審承接輪在這裡寫「**這一支才是**今天 429 真的進到快取的那條路」，並據此說 `refresh_quota_blocking` 那一條「射程寫窄了」。**那句話是錯的，兩個獨立現查證偽它**：① `rate_limited_reading()` 回的是**完整 dict**（`quota_meter.py:730-738`〔現查碼〕，`return {"schema": …, "axes": [...], …}`）⇒ `refresh_quota_blocking` `:622` 的 `reading is None` 判 **False**，`:625` 的 `quota_meter.write_cache(...)` **照樣執行**；② 該讀數自己的 docstring 就寫著這件事——`quota_meter.py:721`／`:724`〔現查碼〕逐字「**唯一的呼叫端** `quota_gate.refresh_quota_blocking()` 跑在 PreToolUse／PostToolUse hook 裡」與「**本讀數會被寫進快取**，`read_quota()` 在 `QUOTA_CACHE_TTL_SECONDS` 內直接命中它」。
    ⇒ **正確的說法（三句，各有各自的射程）**：(a) **今天 429 兩條路都寫快取**，不是二擇一 —— 這與 M197-2 (i)「**兩個**寫入端」的說法本來就一致，是那句「才是」自己製造了矛盾；(b) `pace_state` 那一條**額外**是唯一會污染燃燒落款的路（`record_burn()` 的唯一呼叫點在 `pace_report()` `:731`，而它的 state 來自 `pace_state()` `:723`）⇒ E2 描述的「`fp: []` 落款」只從**這一條**發生；(c) `quota_meter.py:721` 那句「唯一的呼叫端」本身**已經過期**（`measure_detail` 現查有 4 個生產呼叫點，見 §1 表）——它不是本批要改的行為，但它是一句**會誤導下一個讀者的假話**，列為 **W1 的順手工作項**（§9；🔴 本批不得改 code，只登記）。
- (ii) 若基於別的理由仍要寫一份 429 痕跡，該痕跡**必須落到與額度快取不同的檔**（同 `autosdd_quota_degraded.jsonl` 的既有先例），不得進 `core_signature()`／`record_burn()` 的輸入面。**M197-4 的管線就是走 (ii)**，見下。

**M197-3（`record_burn` 前置條件補一格）**：`record_burn()` `:336` 現行前置是 `state.usable() and state.measured_at`。改回 `None` 之後 `usable()` 為假 ⇒ 結構上不再寫合成列，本項**自動成立、不需改碼**。這是選 M197-1 而不是「只改 pct 值」的附帶好處，應寫進提案理由。

**M197-4（429 的「何時解除」不得掉」）**：🔴 **這是本節唯一的新缺口，必須與 M197-1 同窗處理**。

`retry_after_at()`（`:669`）算出來的恢復時刻今天掛在那個合成軸的 `resets_at` 上。改回「量不到」之後 `axes == ()` ⇒ `decide()` 回 `binding=None` ⇒ `quota_messages.throttle_horizon_line()` 取不到 `resets_at` ⇒ 走 `escalate` 分支，逐字印「這道節流**不會自己解除**」——而 429 明明會在 `Retry-After` 後解除。**修法把一句真話換成另一句假話，不可接受。**

🔴 **B13 承接（一審 SD 阻塞項）**：提案輪只寫了「`QuotaState` 增一個欄位」，那是**終點不是管線**。SD 的反證本輪逐行複驗成立：M197-1 之後 429 讀數在寫快取之前就被丟掉、unmeasured 的 `QuotaState` 全出自 `_blank()`（`:379-381`〔現查碼〕只傳 4 個位置參數）、而 TTL 180s 視窗內 hook 讀的是**快取**不是那一次 429 ⇒ 欄位加了也永遠是 `None`，P3 判準恆綠。與 `account_key` 先例**不同型**：那個只有一個寫入點且值本來就在讀數 dict 裡。

**⇒ 本版補完完整管線：4 段、跨 2 檔、6 個具名落點。** 「TTL 視窗怎麼活過去」的答案是**走既有的降級痕跡檔**（M197-2 (ii) 的形態），不新開持久檔、不新發明 TTL：

| # | 落點〔現查碼〕 | 改什麼 | 為什麼是這裡 |
| :-- | :---- | :---- | :---- |
| ① | `quota_meter.py::measure_detail` `:741`（429 分支 `:767-771`） | 回傳由 2 元組加寬為 **3 元組** `(None, REASON_RATE_LIMITED_UNMEASURED, {"retry_after": retry_after_at(headers, now)})`；第三格恆為 `dict`（非 429 路徑一律 `{}`） | 🔴 **本檔自己的判例支持在這裡加寬**：`measure()` `:795-802` 的 docstring 逐字寫「既有呼叫端的窄介面……要知道『為什麼量不到』的人改用 `measure_detail()`——把理由塞進本函式的回傳值會逼每一個呼叫端一起改」⇒ **`measure_detail` 就是那個刻意寬的介面**，加寬它正是該判例的預期用法。爆炸半徑現查、不隱藏：4 個生產呼叫點中只有 2 個會解 2 元組（`quota_meter.py:844` `refresh_detail()`、`quota_gate.py:621`），另 2 個取 `[0]`（`:802`、`quota_gate.py:705`）逐字不受影響 ⇒ **2 行改動、皆在本批（W2）射程內** |
| ② | `quota_gate.py::refresh_quota_blocking` `:621-625`；`quota_gate.py::pace_state` `:705-707` | 把 ① 的第三格轉給 `note_degraded(reason, detail, extra=…)` | 這兩支是 429 的**全部**入口（①的呼叫點普查）。轉交不改 rc、不改回傳形狀 |
| ③ | `quota_gate.py::note_degraded` `:552` | 新增 keyword-only 參數 `extra`（型別 `dict` 或 `None`，預設 `None`），併進 `:570-573` 的 `append_record` 記錄（既有 5 鍵 ＋ `retry_after`） | 🔴 **TTL 視窗的載具就在這裡、不需要發明**：`:567` 的 `claim_once(degraded_stamp_path(source), QUOTA_CACHE_TTL_SECONDS)` 與 `read_quota()` `:413` 的新鮮度判準**用同一個常數** `QUOTA_CACHE_TTL_SECONDS` ⇒ 「痕跡列還新鮮」與「快取還新鮮」同窗同長，一個 TTL 視窗內恰好落一列（閂鎖是原子的，42 個平行 hook 只有一個寫） |
| ④ | `quota_gate.py::read_quota` `:389`（四條 `_blank` 臂：`no-cache` `:394`／`bad-cache` `:396,:412`／`schema-mismatch` `:401`／`stale-cache` `:420`）＋ `_blank` `:379-381` | 回 `_blank(...)` 之前讀一次痕跡檔**最後一列**：`at` 距 `now` ≤ `QUOTA_CACHE_TTL_SECONDS` 且 `retry_after` 非空 ⇒ 以 keyword 帶進 `QuotaState.retry_after` | `_blank()` 現行傳 4 個位置參數而 `retry_after` 是第 6 欄（`account_key` 第 5，`:205`）⇒ **必須走 keyword**，位置參數會靜默填錯欄 |
| ⑤ | `quota_policy.QuotaState` `:195` ＋ `Decision`；`decide()` unmeasured 分支 `:608-618` | 兩個 dataclass 各加一個帶預設值的欄位 `retry_after`（型別 `str` 或 `None`，預設 `None`；沿用 `account_key` `:205` 先例）；unmeasured 分支把 `state.retry_after` 原字串帶進 `Decision` | 這一段才是 `account_key` 的同型部分（欄位帶預設值、既有建構點零改動） |
| ⑥ | `quota_messages.py::throttle_horizon_line` | `binding is None` 時改讀 `decision.retry_after`；有值 ⇒ 播報「會在該時刻自己解除」；`None` ⇒ **維持既有** `escalate` 字面 | 一句真話換另一句真話。`None` 那一臂逐字不動＝保護 `DEF-200-196` |

- **零猜測**：④ 讀不到痕跡（檔在 `%TEMP%`／`~/.autosdd`，重開機即消失）⇒ `retry_after` 為 `None` ⇒ 走 `escalate`。「查不到」永遠退回叫人，不退回「假設 N 秒」（同 `retry_after_at()` `:676` 的既有判詞）。
- **不污染指紋**：痕跡檔與額度快取是**不同的檔**，`core_signature()`／`record_burn()` 的輸入面一格都碰不到（M197-2 (ii)）。
- **與 `DEF-200-196`（fixed@R105）的相容性**：R105 的修法是 `secs <= 0 ⇒ continue`（`:697-698`）⇒ `retry_after_at()` 解不出時回 `None` ⇒ ① 的第三格是 `{"retry_after": None}` ⇒ ④ 判「非空」不成立 ⇒ 仍走 `escalate`。**方向一致，零衝突；`retry_after_at()` 函式體一個字不動**。
- 🔴 **與 `ADR-XPLAT-014` §2.4 L4-a 的同畫面互斥（二審 Architect N6 承接，本批側一句劃界）**：⑥ 會在 `binding is None` 那一臂印「**這道節流會在 `<時刻>` 自己解除**」，而 ADR-XPLAT-014 的 L4-a 在同一種姿態下（解不出可等的 reset）要印「**解不出 reset 時刻、拒絕武裝**」。兩句話擺在同一個畫面上會讀成互相否定。**劃界（兩把尺，不是同一把）**：⑥ 量的是**遙測通道**的速率限制（`Retry-After` 是 metering 端點給的，與模型額度無關；同 §6.6 (B) 的立案），L4-a 量的是**模型額度**的 reset 時刻（`resets_at`／`halt_resets_at()`）。⇒ **規範性要求：兩者的字面必須各自具名自己量的是哪一把尺**（例：「遙測通道限流」vs「額度視窗」），不得共用「節流」這個中性詞；且 `Decision.retry_after` **不得**被 `ADR-XPLAT-014` 的 L0~L4 階梯當成 reset 時刻的來源（那會讓一個 60 秒的遙測退避變成一支排程）。本要求同時寫進 ADR-XPLAT-014 §2.4，兩份文件一句對一句、不留兩個家。
- **effort 重估**：本管線讓 M197-4 由 S 升為 **M**（6 個落點 ＋ 一次元組加寬），且**不得**與 M197-1 分包——M197-1 單獨落地就是「把一句真話換成一句假話」，那是 §2.3 開頭已判不可接受的形態。§9 W2 的 effort 欄已同步。

### 2.4 為什麼不是「只把 100.0 改成別的數字」

任何 `pct` 值都是在**發明一個沒有量到的用量**。`pct=0` ⇒ 永遠正常（靜默失明）；`pct=100` ⇒ 永遠 halt；中間任何值都要有一個沒人量過的門檻來辯護。同檔 `:759-760` 已對這個選項寫過判詞。⇒ 值域必須離開 `pct` 這個軸，落到 `band=unmeasured` 這個**已經存在的**狀態字上。

### 2.5 附帶裁決項：`KNOWN_KINDS` 要不要收進 repo 自造的 kind

**建議：不收。改立第二個集合。**

| 選項 | 後果 | 判 |
| :---- | :---- | :---- |
| 收進 `KNOWN_KINDS` | 消掉那句 `unknown-kind`；但 `core_signature()` `:318` 也讀同一個集合 ⇒ 合成軸會**進指紋**，等於用一個假桶名去分區攤提樣本。這比今天更糟 | ❌ |
| 不收、維持現狀 | 每次 429 印一句 `unknown-kind`＝「伺服器吐了個沒看過的桶」＝假話 | ❌ |
| **不收，另立 `SYNTHETIC_KINDS` ＋ 專屬 note 字面** | `KNOWN_KINDS` 維持「**伺服器桶名**的家」這個單一語意；自造 kind 用 `NOTE_SYNTHETIC`（建議字面 `synthetic-reading`）。**射程只有 note 字面那一面**（見下方 B17 承接） | ✅ |

#### 🔴 B17 承接（一審 Architect 阻塞項）：本項不得動 `core_signature()` 的取數面

提案輪原文寫「`core_signature()` 的取數面同時排除兩個集合」。**該句本輪撤回，兩個獨立理由：**

1. **它是死碼**〔現查碼〕：`core_signature()` `:318` 的實作逐字是
   `tuple(sorted({a.kind for a in state.axes if a.kind in quota_policy.KNOWN_KINDS}))`
   ——已經是 `∩ KNOWN_KINDS`。而本項的建議本身就是「自造 kind **不進** `KNOWN_KINDS`」⇒ `− SYNTHETIC_KINDS` 這一步在建構上不可能改變任何回值。寫進 PRD 條文＝入憲一段永遠不會被求值的判準。
2. **它會製造同一份知識的第二個家**〔實讀〕：`∩ KNOWN_KINDS` 這個定義與它的理由（「未知桶名的增減依既有紀律定性為 **schema 演進** ……不該觸發攤提重置」）住在 **`ADR-XPLAT-009` §2.2**（`:37-55`，該 ADR 狀態 `:3-4` 為 **Accepted**）。本提案零 ADR 引用而動它的裁決面，正是本 repo 反覆判過的形態。

**⇒ 改後處置（三條，本批照此執行）**：

- (i) 本項的落地射程**收窄為「note 字面」一面**：新增 `SYNTHETIC_KINDS` ＋ `NOTE_SYNTHETIC`，只影響 `quota_policy` 逐軸 note 的取字（`NOTE_UNKNOWN` `:153` 那一格），`core_signature()` 一個字不動。
- (ii) §6.6 的 `R-8-1-2` 條文改為**引用** `ADR-XPLAT-009` §2.2 既有裁決，不重述定義（見 §6.6 改後文本）。
- (iii) 若未來真要讓 `core_signature()` 的取數面認識 `SYNTHETIC_KINDS`（例如某輪把某個自造 kind 收進 `KNOWN_KINDS`），那是 **`ADR-XPLAT-009` 的修訂**，走 ADR 補記程序，不由 PRD 條文旁路裁決。

#### 另一個仍然活著的自造讀數：`quota_floor_reading()` 的同型性（QA→修憲，本輪已查）

一審 QA 要求把「查 `quota_gate.quota_floor_reading()`（`:631`）同型性」**明列為 197 的結案前置、不留在劃界節**。本輪已逐行讀完 `:631-652`〔現查碼〕，結論逐項對齊 §2.1 的 E1/E2/E3：

| | 同型？ | 依據〔現查碼〕 |
| :---- | :---- | :---- |
| **E1（方向：把「量不到」寫成「量到 100%」）** | ❌ **不同型** | 它的 `pct=100.0` 有**真的用量證據**——前置條件是 `unhandled_limit_event(transcript)` 非 `None`（`:643-645`），即逐字稿裡有一次**未復原的撞線**。docstring `:636-637` 自陳「正是 meter 全死時唯一還算數的證據」。這是有證據的地板，不是替量不到發明的讀數 |
| **E2（指紋抹空／污染落款）** | ⚠️ **部分同型，但今天到不了 `record_burn`** | 它建構 `QuotaState` 只傳 4 個位置參數（`:648-652`）⇒ `account_key` 為 `None`，且 `state.usable()` 為真（1 軸）⇒ `core_signature()` 會走 `:321-325` 的 `note_degraded("no-account-key", …)` ＝ 與 429 **完全相同的那條退化路**。**但**它唯一的呼叫點是 `quota_gate()` `:873`〔現查碼〕，該函式**不呼叫 `record_burn()`**；`record_burn()` 的唯一呼叫點在 `pace_report()` `:731`，而那條路的 state 來自 `pace_state()` `:723`，碰不到地板 ⇒ **今天不會寫出 `fp` 被污染的落款列**。這是「靠呼叫圖恰好沒接上」而不是「靠判準擋住」⇒ 屬可回歸的脆弱，記為結案前置的**觀察項**，不是本批要修的缺陷 |
| **E3（note 用錯字）** | ⚠️ **同型但成因不同** | `kind` 取自逐字稿事件（`kind=str(event.get("kind") or "")` `:649`），不是 repo 寫死的字面。若解出的字面不在 `KNOWN_KINDS`（`:143-144`）⇒ 同樣印 `unknown-kind` ⇒ 同樣是假話（那個字面是**本 repo 的解析器**產的，伺服器沒說）。⇒ (i) 的 `NOTE_SYNTHETIC` 射程應**同時涵蓋** transcript 地板，不只 429 |

🔴 **結案前置（明列，不留劃界節）**：`DEF-200-197` 結案時必須逐項回答上表三格；其中 E3 那一格的處置（`NOTE_SYNTHETIC` 涵蓋 transcript 地板）**併入本批 (i)**，E2 那一格以觀察項形式進 §8。

🔴 採 M197-1 之後 429 不再產生任何軸，本裁決項**在 429 這條路上失去觸發點**；但 transcript 地板仍然活著（上表）⇒ 本項仍須裁決，只是不再阻塞 197。**標注：待掌舵者或四方裁決（§10 Q1）。**

### 2.6 對既修項的相容性檢查

| 既修項 | 相容性 |
| :---- | :---- |
| `DEF-200-196` fixed@R105（`secs<=0` → `continue`） | ✅ 見 §2.3 M197-4 末段。M197 不動 `retry_after_at()` 的函式體一個字 |
| `DEF-200-201` fixed@R107（顯示行自帶語意） | ✅ 429 改走 unmeasured 之後 `pace_line()` 走 `binding is None` 那一臂，既有字面「**量不到任何一軸**（這不是「額度很寬鬆」）」（`quota_messages.py:258`）**正是本修法要的那句話**，一個字不必改 |
| `DEF-200-202` fixed@R105（`decide` 補 `active_model`） | ✅ unmeasured 分支在 `_in_cap_gate()` **之前**就 return（`:608-618`），結構上碰不到 model 過濾 |

---

## 3. DEF-200-198 — cap 從未真的限制過派工

### 3.1 先回答值域問題：cap **結構上可以**小於 `max_fanout`

〔探針〕`_cap_for(band, horizon, DEFAULT_POLICY)` 全笛卡兒積（5 band × 4 horizon＝20 格）：

| band \ horizon | near | mid | far | none |
| :---- | :---- | :---- | :---- | :---- |
| free | **None** | **None** | **None** | **None** |
| notice | **16** | 8 | 4 | 4 |
| converge | 8 | 4 | 2 | 2 |
| prepare | 4 | 2 | 1 | 1 |
| halt | 0 | 0 | 0 | 0 |

- cap 值域 ＝ `{None, 0, 1, 2, 4, 8, 16}`〔探針〕。
- `cap == max_fanout(16)` 的格數 ＝ **1**〔探針〕，就是 `notice × near`。
- ⇒ **答案：是，19/20 格的 cap 要嘛不設限（None，4 格）要嘛 ≤ 8。**「cap 從未真的限制過派工」不是值域問題，是**取樣落點**問題。

🔴 **B11 承接（一審 SA 阻塞項）——承重句的算術訂正**：提案輪寫「帳本記的 15 個取樣點……**全部**落在上表唯二不會擋人的那兩格」，**這句話算錯了，且錯的方向是把承重論證誇大**。逐項核對〔帳本 `:204` 實讀〕：

| 取樣點 | 筆數 | 落在上表哪一格 | 會不會擋人 |
| :---- | :--: | :---- | :---- |
| `cap=None` | 10 | free 列（四格皆 `None`） | ❌ 不擋（真的不設限） |
| `cap=16` | 4 | `notice × near`（唯一等於 `max_fanout` 的格） | ❌ 不擋（等於無節流） |
| `cap=0` | **1** | **halt 列**（四格皆 0） | 🔴 **擋死，不是放行** |

⇒ 正確的承重句是 **14/15**，不是 15/15。而第 15 點本身就是帳本自己記載的：帳本 `:204` 逐字「**那 1 次是複審自己的探針打出的 429（見 DEF-200-202）**」〔帳本實讀〕⇒ 它是**探針自造的事故**，不是生產流量；且 **M197-1 落地後它結構上消失**（429 改回「量不到」⇒ `band=unmeasured`、`cap=degraded_cap`，不再有 `cap=0` 這一格）。

⇒ 訂正後的結論**方向不變、強度稍減**：14/15 個取樣點落在唯二不會擋人的兩格，剩下 1 個是探針自造的 429。「cap 從未真的限制過派工」在生產流量上仍然是 **14/14 成立**（把探針那一筆剔出母體之後，母體裡一次都沒有 `1 ≤ cap < max_fanout` 的格）。

### 3.2 真正的缺陷：加速乘數被套在「煞車」上

`notice × near = 8 × 2.0 = 16 = max_fanout`。也就是說 **50~70% 的節流帶，只要 reset 在 30 分鐘內，節流就被 `pace_near` 完全抹掉**。

這與 `quota_policy.py` 檔頭自陳的設計直接矛盾：`decide()` 的 docstring `:606`〔現查碼〕逐字寫「`cap = min(逐軸 cap)`＝**煞車**；`rec = min(base×pace, cap)`＝**加速**」——`pace` 本該只作用在 rec 這一側。

**M198-1（cap 不吃加速乘數）**：`_cap_for()` `:431` 的 `_mult(horizon, p)` 夾上界 1.0（`min(1.0, _mult(...))`）。

〔探針〕改前／改後逐格對照：

| 改變的格 | cap 改前 → 改後 | rec 改前 → 改後 |
| :---- | :---- | :---- |
| notice × near | 16 → **8** | 8 → **8**（不變） |
| converge × near | 8 → **4** | 4 → **4**（不變） |
| prepare × near | 4 → **2** | 2 → **2**（不變） |
| 其餘 17 格 | 不變 | 不變 |

- **`rec` 一格都沒變**〔探針：`rec 改變的格 = （無）`〕——因為 `_rec_for()` `:444` 是 `min(base×mult, cap)`，而收緊後的 cap 仍 ≥ 對應的 rec。
- **掌舵者錨點① 逐格保留**〔探針〕：`free × near` 的 `cap` 改前改後皆 `None`、`rec` 改前改後皆 `16`。錨點①（「剩 30Min 就 Reset、還有 100% 沒用 ⇒ 加速」）講的是 free 帶，一格未動。
- 改後 `cap == max_fanout` 的格數 ＝ **0**〔探針〕。

⇒ 這是一個**只收緊 cap、完全不動 rec、不動錨點①** 的改動。方向乾淨，是本批風險最低的一項。

### 3.3 M198-2：「等於無節流」必須在輸出面出聲

即使 M198-1 落地，`cap is None`（free 帶，4 格）仍然是真的不設限。今天 `pace_line()` `:250` 只印「硬上限 cap=不設限」——那是**事實描述**，不是**姿態告知**。

設計（`quota_messages.py::pace_line`，純渲染、零決策）：

- `cap is None` ⇒ 既有字面後追加：`⇒ 這一格結構上不擋任何扇出（節流由 rec 諮詢值承擔）`。
- `cap is not None and cap >= p.max_fanout` ⇒ 追加：`⇒ cap 已等於 max_fanout，等同無節流`。
  （M198-1 落地後這一臂在出廠設定下不可達，但 `AUTOSDD_QUOTA_CAP_NOTICE` 等 env 鍵可以把它推回可達 ⇒ **判準留著，不是死碼**。）
- 🔴 這一行**必須帶 `max_fanout` 的值**，不得只寫「無節流」——否則它自己就變成一個沒有值可以對帳的宣稱（`check_claim_provenance.py` 的同型判準）。

### 3.4 為什麼不是「把 `max_fanout` 調小」

`max_fanout` 是**加速後的絕對上界**〔現查碼 `quota_policy_env.py:85-86`〕，調小它會同時砍掉 free 帶的 rec=16（錨點①）。缺陷在「notice 帶的煞車被乘數抹掉」，不在上界本身。調上界＝用一個全域旋鈕去治一個局部格子，是本 repo 判過的「用錯旋鈕」形態（`quota_pace.py` 檔頭〈缺陷 C〉）。

### 3.5 對既修項的相容性檢查

| 既修項 | 相容性 |
| :---- | :---- |
| `DEF-200-196` fixed@R105 | ✅ 無交集（那一支在 `quota_meter`） |
| `DEF-200-201` fixed@R107（顯示行自帶語意） | ⚠️ **同一支函式的鄰行**。M198-2 是**追加**一個子句，不改 R107 落地的既有字面；實作包必須把 R107 的鎖先跑一次確認未破 |
| `DEF-200-202` fixed@R105（`active_model`） | ✅ M198-1 在 `_cap_for()`，在 `_in_cap_gate()` 之前，兩者正交 |
| PRD §11.2「重置後不暴衝」（`cap ≤ cap_notice`） | ⚠️ **本輪順手發現的既有缺口**：`_cap_for(BAND_FREE, *)` 四格皆 `None`〔探針〕⇒ 翻頁後第一拍若落在 free 帶，PRD §11.2 逐字要求的「不設限不得在翻頁後第一拍出現」**今天就不成立**。M198-1 不製造也不修好這一格；**建議另立缺陷列，不併入本批**。🔴 **B12：爆炸半徑比提案輪寫的大一級**，見 §3.6 |

### 3.6 🔴 B12 承接（一審 SA 阻塞項）：free 帶 `cap is None` 的爆炸半徑不只是「另立一列」

提案輪把「free 帶四格 cap 皆 `None`」寫成一個順手發現、建議另立缺陷列（§10 Q6）。**一審 SA 指出爆炸半徑被低估一級，本輪複驗成立**：

PRD **v2.1.9** 在 `:549-555`〔實讀〕訂正 v2.1.8 §11.2 (c) 的論證時，逐字寫下：

> 【v2.1.9 訂正】原文寫「**唯一**沒有中間級」，該字已刪：實查 `_cap_for()` 的階梯，measured 軸**內部**同型的躍遷至少還有一個——`notice → free` 是「有限 cap → `None`（不設限）」……原文用「唯一」去論證「(c) 不需要第三個機制」，論據因此不完整；**結論仍成立，但改由另一個理由承重：那一格已經有既有守衛（§11.2「重置後不暴衝」逐字要求翻頁後第一拍 `cap ≤ cap_notice`，即 `None` 不得在翻頁後第一拍出現）⇒ 不是沒人管，是已經由別條管**，不必在本節再立第三個機制。

⇒ **那個「別條」在實作面不存在**：`_cap_for(BAND_FREE, *)` 四格皆 `None`〔探針〕，即「`None` 不得在翻頁後第一拍出現」今天沒有任何落點。也就是說 v2.1.9 用來替 (c) 不立第三個機制辯護的**承重理由本身不成立**——本案的實測直接證偽它。

**這比「另立一列」重一級的地方**：它不是一個獨立的實作缺口，而是**一條已經寫進修憲文本、正在替另一段條文承重的理由**。放著不處置的後果是：v2.1.9 通過再審 ⇒ §11.2 (c) 以一個假理由入憲 ⇒ 下輪稽核重開（`DEF-200-206` 族）。

**⇒ 本批處置（最小、不擴張射程）**：

- §6 增列一格對 PRD `:549-555` 的處置（**最小版**：標注「該承重理由在 §11.2『重置後不暴衝』真的有實作落點之前不成立」），文本見 **§6.9**。
- §10 **Q6 改寫**：問題從「併入本批還是另立」升級為「v2.1.9 的承重理由已被證偽，(c) 要不要真的立第三個機制」，並補上此事實。
- 本批**仍然不修** free 帶那一格（M198-1 不製造也不修好它）；改的只是**不讓一句已被證偽的理由靜靜留在修憲文本裡**。

---

## 4. DEF-200-199 — `recommended` 與實際餘裕反向

### 4.1 根因複述（機制已由本輪探針獨立重現）

帳本原文（`:205`）：`session 4%／剩 283 分` 建議 **4**、`session 53%／剩 6 分` 建議 **8**〔他包回報，未複驗〕；機制＝`_pace_of` 取**跨軸 max**。

**本輪合成重現**〔探針，`decide()` 真呼叫〕：

| 情境 | 逐軸 horizon | cap | **rec** |
| :---- | :---- | :---- | :---- |
| A　session 4%／剩 283 分 ＋ 7d 40%／剩 6000 分 | session:far(×0.5) five_hour:far(×0.5) **seven_day:far(×0.5)** | None | **4** |
| A2 同上但 7d 剩 5000 分 | session:far(×0.5) five_hour:far(×0.5) **seven_day:mid(×1.0)** | None | **8** |
| B　session 53%／剩 6 分 ＋ 7d 40%／剩 5000 分 | session:near(×2.0) five_hour:near(×2.0) seven_day:mid(×1.0) | 16 | **8** |

⇒ **帳本的 4 vs 8 反向在本輪被完整重現**，且 A ↔ A2 的對照直接證明帳本的機制歸因成立：**session／five_hour 兩軸完全沒動，只把 7 天軸在它自己 10080 分窗裡的位置從「剩 6000 分」移到「剩 5000 分」，rec 就從 4 跳到 8。**

機制拆解（三個獨立的錯，帳本併為一列）：

- **R1（錯位）**：`decide()` `:649` 的 `base = min(_base_rec(r.band))` 取的是**稀缺度最緊的那一軸**；`:686` 的 `_pace_of(gate, p)` 取的是**期程最短的那一軸**。兩者**可以是不同的軸**，而它們的乘積被當成一個數字交出去。A 案裡 `base=8` 來自 session 的 4%（free 帶），`pace=0.5` 來自 7 天軸的位置——**兩個毫不相干的軸的乘積**。
- **R2（擺幅不對等）**：`pace` 的擺幅是 4×（0.5 ↔ 2.0），而 band 階梯每跨一帶只有 2×〔探針：`_base_rec` = free 8 / notice 4 / converge 2 / prepare 1〕。⇒ **時間位置的訊號結構上壓過餘裕訊號兩個帶**，這就是「反向」的算術來源。
- **R3（`far` 一詞承載兩件事）**：`far` 同時被讀成「沒有 use-it-or-lose-it 的急迫感 ⇒ **不要加速**」（正確）與「⇒ **主動減半**」（一個沒有任何燃燒證據支撐的懲罰）。`_mult()` `:388-390` 的註解逐字寫 `far／none ×0.5 ＝「反之則減速」`——那是掌舵者錨點②，但錨點②沒說「減速到足以蓋過餘裕訊號」。

### 4.2 修法設計（三層，刻意分階段；**三層都不動 `pace_far` 常數**）

#### L1 — 同軸聚合（結構修正，不需要任何放寬證據）

`rec` 改為 `min(逐軸 _rec_for(band_x, horizon_x))`，即 **pace 與稀缺度必須來自同一軸**；`AXIS_NONE` 的全域否決（`_pace_of` `:549-550`：期程不明且有煞車力的軸把節奏夾在 1.0）**保留為全域夾層**，套在每一軸的乘數上。

- **方向鎖（機械可查）**〔探針〕：三軸全笛卡兒積（`4 個非 halt band × 4 horizon` 三軸＝ `16³`）＝ **4096 組**，L1 相對今天：**收緊 1422 組／相等 2674 組／放寬 0 組**。
  🔴 這個「0 放寬」是有代價換來的：**只做 min-of-rec 而漏掉 `AXIS_NONE` 全域否決時，實測有 60 組會放寬**（反例：`free×near + notice×none + prepare×near`，今天 1 → 漏掉否決後 2）。⇒ 否決夾層不是可選項，是方向鎖的一部分。
  🔴 **「60」是出廠值的導出量，不是常數**（QA→修憲 non-blocking）：它由 `cap_notice=8`／`cap_converge=4`／`cap_prepare=2`／`pace_near=2.0`／`pace_far=0.5`／`max_fanout=16` 六個可由 `.env` 覆寫的欄位算出，任一被調就會變。⇒ **§7 的 P8 判準只准斷言方向**（「拿掉否決 ⇒ 放寬組數 > 0」），不得把 60 寫進判準；本行的 60 只作為本輪這一組出廠值下的量級證據。同理 1422／2674 兩數亦然。
- **附帶好處**：`AxisReading.recommended`（`quota_policy.py:275`）今天**算了但沒有任何消費端**〔現查碼：`decide()` 只讀 `r.band`／`r.cap`〕；L1 讓它有家。
- **為什麼 R84／SA-01 當年反對 min-of-rec 的理由已消失**：`decide()` `:590-594` 的註解逐字寫「weekly 這種長期程軸的 horizon **幾乎恆為 far** ⇒ 它的 ×0.5 永遠 binding」。那句話成立於**絕對門檻**時代（`far_horizon_minutes=360` 對 10080 分窗＝3.6% ⇒ 96.4% 時間恆 far，見 `quota_pace.py` 檔頭〈缺陷 A〉）。R86 的相對化之後〔探針〕`thresholds(10080, 30, 360) = (1008.0, 5040.0)` ⇒ **週軸的 far 只佔窗的前半**。前提已被自家後續修復證偽——與 §2.2、與 `DEF-200-193` 同型。

#### L2 — `far` 的語意分層：**短窗軸**的 far 由「懲罰」降為「上限」

##### 🔴 L2 判準已整段換掉（B14／B15／B16 三連擊承接）

一審 Architect 對 L2 提出三筆各自獨立成立的 blocking，本輪**逐筆親跑複驗，三筆全部成立、無異議**：

| # | 一審判詞 | 本輪複驗〔本輪實測〕／〔現查碼〕 |
| :-- | :---- | :---- |
| **B14** | L2 判準相對**當次讀數**的軸集合 ⇒ 加一條更長窗軸會把原最長軸重分類為 rate 軸 ⇒ rec 變大 ⇒ 違反本案自己要入憲的 §6.1(4)「加軸 rec 不得變大」。同文件兩條文互相否定 | **成立**（一審承接輪的證據是手填窗長面的 `L2rel` 645／32800——🔴 該數字本版已判為**注入面繞過判準之家、不再引用為依據**，見 §0.3.1 與附註 6；B14 本身仍然成立，改由下一行的現查證據承重）。🔴 **二審 Architect N1 指出「改絕對地板」還不夠、家也錯，本輪複驗成立**：一審指定的家 `windows()` 自己就讓分類依賴輸入集合〔本輪實測逐字〕`windows(spend 單獨) = (None,)` vs `windows(spend + monthly_all 同 reset) = (43200.0, 43200.0)` ⇒ 家改為 `window_minutes(kind)`，詳見下方〈L2 改後判準〉與 §0.3.3 |
| **B15** | 「週軸結構上到不了 L2」是**量測值不是結構事實**——`_UNIT_MINUTES` 已含 month ⇒ 伺服器回月桶那天週軸靜默進入射程 | **成立**〔現查碼 `quota_pace.py:77-81`〕：`_UNIT_MINUTES` 含 `"month": 43200, "months": 43200`、`_PERIOD_MINUTES` `:81` 含 `"monthly": 43200`。〔本輪實測〕`window_minutes("monthly_all") = 43200.0`、`window_minutes("one_month") = 43200.0` ⇒ 文法**現在就解得出**月桶，不需要任何改動 |
| **B16** | 指定的判準之家 `amort_for()` **拿不出逐軸分類**——`amortize()` 只回最短／最長兩個 argmax，中間窗軸無分類；`ratio=None` 時回 `None` | **成立**〔現查碼 `quota_pace.py:309-335`〕：回值 `Amort` 只有 `rate_kind`（`min(窗長)` 的 argmax）與 `total_kind`（`max(窗長)` 的 argmax）兩個桶名欄。〔本輪實測〕餵三個窗長（300／1440／10080）⇒ 回 `('five_hour', 'seven_day')`，**1440 分窗軸（`one_day`）在回值裡沒有任何分類**；餵 `ratio=None` ⇒ 回 `None`（連兩個 argmax 都沒有） |

**⇒ 選路：改判準（不是把 L2 降級為 gated 項）。** 一審承接輪的理由是：§4.2 L2〈前置條件〉測出 **L1 單獨落地會製造新的過度保守**（A2 由 8 收緊到 4），而 §9 W3 據此明訂「L1 與 L2 不得分包」⇒ 把 L2 gate 掉等於連 L1 一起 gate 掉。

🔴 **二審之後這條選路理由本身要重述（因為它的證據被 N1 的換家改掉了）**：換家之後 L2 **不再**把 A2 還原到 8（〔本輪實測〕hybrid 下 A2 = 4，§4.3）⇒ 「L2 是 L1 的必要配套」這個理由**不再成立**。選路結論**不變**，但改由兩條仍然成立的理由承重：① **判準本身可以改對**——B14/B15/B16 三筆指的都是判準的形態，不是 L2 的意圖，而形態可以修（本節就是修完的結果）；② **L2 對 `five_hour` 這一格仍有實質效果**（`window_minutes("five_hour") = 300 < 10080` ⇒ 適用），亦即 L2 的射程只是**比一審承接輪以為的窄**，不是空的。⇒ 把 L2 gate 掉會讓短窗軸的 far 懲罰原樣留著（那正是 `quota_pace.py` 檔頭〈缺陷 C〉的「用錯旋鈕」），而那件事與 A2 那一格是兩回事。**分包判準另議，見 §9 W3 與 §10 Q9。**

##### L2 改後判準（絕對地板，入憲）

- 判準：一軸的窗長 **嚴格小於**一個入憲的絕對地板 `W_TOTAL_FLOOR_MINUTES`（提議出廠值 **10080**，即一週）⇒ 它的 `far`／`none` 乘數由 `pace_far`(0.5) 改為 **`1.0`（中性：不加速也不懲罰）**。🔴 **邊界句照二審 Architect N7 改寫為正面條件**：**窗長 ≥ 地板 ⇒ 不適用**；**窗長解不出（`None`）⇒ 不適用**（兩者都仍是 ×0.5，fail-safe：不確定時不放寬）。
  🔴 **N7 的另一半必須明文記下（本批不改值，只記風險）**：出廠地板 **10080 恰好等於週窗本身**，也就是週軸落在「不適用」那一側**只差一個等號**。若哪天有人把判準從 `<` 誤寫成 `<=`、或伺服器改回一條窗長 **10079** 的桶（文法解得出任意「數量詞 × 單位詞」組合〔現查碼 `window_minutes` `:127-135`〕），週軸就會**靜默進入放寬射程**，而外觀與今天完全相同。⇒ §7 **P10** 必須有一格專測 `窗長 == 地板` 的邊界（期望：不適用），P17 的紅面之一即「把 `<` 改成 `<=`」。
- 🔴 **判準的家＝`quota_pace.window_minutes(kind)`**（`:120`〔現查碼〕，二審 Architect N1 承接；**一審指定的 `windows()` 本版撤回**）。四個候選逐一記錄取捨：

  | 候選 | 判 | 理由〔本輪實測／現查碼〕 |
  | :---- | :--: | :---- |
  | `amort_for()`／`amortize()` | ❌ | B16：只回最短／最長兩個 argmax，中間窗軸無分類；`ratio=None` 整個回 `None` |
  | `max(當次讀數各軸窗長)` | ❌ | B14：判準依賴輸入集合 |
  | `quota_pace.windows()`（`:143`） | ❌ **本版撤回** | 二審 N1：它的「同 reset 鄰軸繼承最短窗長」**本身**就讓分類依賴輸入集合。〔本輪實測逐字〕`windows(spend 單獨) = (None,)`／`windows(spend + monthly_all 同 reset) = (43200.0, 43200.0)` ⇒ 同一條 `spend` 軸，旁邊有沒有一條同 reset 的月桶，決定它的窗長是「解不出」還是 43200 |
  | **`window_minutes(kind)`（`:120`）** | ✅ **採用** | 它是**該軸 kind 的純函式**：`tokens = kind.split("_")` → 文法表查一次 → 回值或 `None`〔現查碼 `:127-135`〕，**函式簽章裡沒有任何其他軸**。⇒ 分類對輸入集合結構性免疫 |
  | 桶名清單 | ❌ | `quota_policy.py` 檔頭既有禁令（窗長由文法導出，不由桶名） |

- **三筆一審 blocking 逐一被這個判準關掉**：
  - **B14 ⇒ 「L2 的分類」這一條通道結構性關閉**：每一軸的 L2 分類只由 `window_minutes(該軸 kind)` 與一個**常數**決定 ⇒ 加軸不改變任何既有軸的**分類**。〔本輪實測〕`L2abs` 的違反數由 windows-home 的 **2796** 降到 hybrid-home 的 **2036**（§0.3.2）。
    🔴 **但它不會歸零，而這一句必須寫在這裡而不是只寫在劃界節**（二審 N1 的判詞只說「換家」、沒說「換完就 0」，本版不替它加那半句）：把 L2 **整個拿掉**（`L1`）的殘留違反是 **1972**〔本輪實測〕⇒ 殘留的主體是 `windows()` 的繼承**經由 horizon**（`resolve()` `:392` → `effective_horizon()` → `thresholds(window,…)`）影響 rec 的**第二條、獨立通道**。⇒ **§6.1(4) 的射程必須收窄**（見下方〈與 §6.1(4) 的關係〉），第三件事（取消繼承）與**第四件事（gate 聚合面，三審 A1）**皆登記於 §8-11 ＋ §6.1 (4b) ＋ §10 **Q9**。
  - **B15 ⇒ 「週軸到不了 L2」由量測值升為結構事實**：〔本輪實測逐字〕`window_minutes('weekly_all') = 10080.0   < floor(10080) ? False`／`window_minutes('seven_day') = 10080.0   < floor(10080) ? False`（對比 `window_minutes('five_hour') = 300.0   < floor(10080) ? True`、`window_minutes('monthly_all') = 43200.0 ? False`、`window_minutes('one_day') = 1440.0 ? True`）⇒ 週軸的**分類**不論伺服器回幾條桶、有沒有回月桶，一格不動。
  - **B16 ⇒ 家換掉，`amortize()` 一個字不動**：L2 不再需要「誰是 rate 軸／誰是 total 軸」這個攤提概念，只需要「這一軸自己的 kind 解出多長的窗」——那正是 `window_minutes()` 回的東西，對每一軸都回一格（沒有中間窗軸失明問題），對 `ratio` 零依賴。
- **`W_TOTAL_FLOOR_MINUTES` 為什麼是 10080**：**它由 L2 自己的論證界定，不是從窗長階梯挑出來的**（🔴 誠實劃界：桶名文法能解出**任意**「數量詞 × 單位詞」組合〔現查碼 `window_minutes` `:127-135`：`_COUNT_WORDS` × `_UNIT_MINUTES`〕，所以「階梯上只有五個刻度」是**觀測**不是結構——那個說法不能拿來當地板值的理由）。真正的理由只有一條：L2 的論證（use-it-or-lose-it、儲蓄零價值）對 5 小時窗成立、對**週**窗不成立（週配額是本 repo 通篇要保護的那一個）⇒ 地板必須恰好卡在週，**週軸自己落在不適用的那一側**。開一個 env 鍵 `AUTOSDD_QUOTA_TOTAL_FLOOR_MINUTES` 讓它可被調，但**方向不變式＝只准調小（更嚴）不准調大**（調大會把週軸拉進射程＝無證據放寬）。這條不變式與 `band_inputs()` 的「只調高不調低」同族。它的證據面誠實劃界見 §8-6c。
- **與 §6.1(4) 的關係必須說白（B14 的成因就是這兩件事被混讀）**：
  - §6.1(4) 量的是「**同一份讀數加一條軸**，rec 不得變大」——這是**聚合律**的不變式。
  - 「L2 前後 rec 是否變大」量的是**兩個不同的聚合律**之間的差，L2 對短窗 far 軸**刻意是一個放寬**（論證見下），它不受 (4) 管，也不該受。
  - 🔴 兩者都要有各自的方向鎖：(4) ⇒ §7 **P16**（新增）；L1 對今天的收緊面 ⇒ P8。
  - 🔴 **(4) 的射程本版收窄（二審 N1 ＋ 三審 A1 的機械後果，兩個合取項）**：(4) 只在「**逐軸窗長皆由該軸 kind 的文法解得出**」**且**「**gate 聚合成員集合非空**」的讀數上成立為 `== 0`〔本輪實測：封閉面 56,448 個加軸對，`L1`／`L2abs` 皆 **0**，且三個 home 逐格相同；含 FALLBACK／MODEL_SCOPED 桶名但窗長皆解得出、並要求 gate 非空的 69,840 個加軸對亦皆 **0**〕。兩個合取項各自被打破時：① 讀數含**文法解不出窗長的 kind**（今天實際有：`session`／`spend`／`nimbus_quill`／`weekly_scoped`）⇒ `windows()` 的鄰軸繼承經由 horizon 讓 (4) 被違反〔本輪實測：`L1` 1972／`L2abs` 2036，母體 109,800〕；② 🔴 gate_list 起初為空（讀數全是超額類／未命中的模型分軌軸）⇒ 加一條軸讓煞車軸整批離開聚合面，**窗長全部解得出也照樣違反**〔本輪實測：`L1` 0 → **7515**／`L2abs` 0 → **8691**，母體 109,800；定向兩例逐字 4 → 16〕。⇒ **條文必須說出這個射程**，否則 (4) 入憲當天就是一條在生產上會紅的條文，而下輪稽核會把它當新發現重開（`DEF-200-206` 族）。改後條文見 §6.1 (4) 與 §6.1(4b)。
- 論證（不變，逐字保留）：短窗（5 小時）配額**未用完即蒸發**，儲蓄零價值 ⇒ 對它施加「省著點用」的乘法懲罰，保護的其實是**週**配額，而那是用錯旋鈕（`quota_pace.py` 檔頭〈缺陷 C〉逐字：「降 `cap` 只讓同一批工作花更久，總消耗不變……用 `cap` 保護週配額是用錯旋鈕」）。週配額的正確保護是**跨窗攤提**（`band_inputs()` 只調高不調低，結構上不可能放寬），而攤提在 R86 就已落地。
- **為什麼這不等於「鬆掉週軸」**〔探針，逐格對照；改判準後逐格**不變**，已於本輪重跑〕：

  | 7 天軸情境 | horizon | note | 今天乘數 | L2 後乘數 |
  | :---- | :---- | :---- | :---- | :---- |
  | 40%／剩 6000 分 | far | （無） | 0.5 | **0.5**（不動） |
  | 40%／剩 5000 分 | mid | burn-thrifty | 1.0 | **1.0**（不動） |
  | 40%／剩 500 分 | near | burn-thrifty | 2.0 | **2.0**（不動） |
  | 70%／剩 6000 分 | far | burn-ahead | 0.5 | **0.5**（不動） |
  | 20%／剩 9000 分 | far | burn-ahead | 0.5 | **0.5**（不動） |

  L2 的射程判準改為「`window_minutes(kind) < W_TOTAL_FLOOR_MINUTES`(10080)」⇒ 週軸（10080）**不小於**地板，一格不動。🔴 這一句的性質由此**從量測值升為結構事實**（B15）：提案輪的理由是「7 天軸在本 repo 觀測到的任何一份讀數裡都是最長窗〔探針：本機落款 8 個 kind，最長者恆為 10080〕」——那是**今天這台機器上的觀測**，伺服器哪天回一個月桶（文法**現在就解得出**：`window_minutes("monthly_all") = 43200.0`〔本輪實測〕）它就不成立。改後的判準只讀該軸自己的 kind 與一個常數，**沒有任何量測值參與**。
- **前置條件**：L1 必須同窗落地。〔探針〕A2 情境在 **L1 單獨落地時會從 8 收緊到 4**（`session` 的 far 變成 binding），L2 才把它還原到 8。⇒ **L1 沒有 L2 會製造一個新的過度保守**，兩者不得分包。
  🔴 **二審 N1 換家之後，這一格的還原**不再成立**（本版的 contested 半句，附反證）**〔本輪實測，§4.3 表 hybrid 列〕：`window_minutes("session") = None` ⇒ L2 對 `session` 軸**永遠不適用** ⇒ A2 在 `L1+L2abs`（hybrid）下是 **4**，不是 8。機制是結構性的、與取樣無關：`session` 與 `five_hour` 是**同一條底層限制被回報兩次**（`quota_pace.py:138-142`〔現查碼〕逐字「今天 `session` 與 `five_hour` 的 `resets_at` 逐字相同……⇒ 它們是同一條底層限制被回報兩次」），而 L2 只認得 `five_hour` 那一格 ⇒ `rec = min(逐軸)` 讓沒被還原的 `session`（×0.5 ⇒ 4）勝出。⇒ **L2 在本 repo 最重要的那一對軸上被自己的新家中和**。三個出路（都需要裁決，本文件不自行結案）見 §10 **Q9**；在 Q9 裁決之前，§4.3 表的 A2 一格**以 hybrid 的 4 為準**，不得引用 8。

#### L3 ＝ 改動 (a) thrifty floor（見 §5.1）

### 4.3 三層疊加後的實測結果〔探針〕

| 情境 | 今天 | L1+L3 | L1+L2+L3 | ＋(c) T_wrap=30 分 |
| :---- | :---- | :---- | :---- | :---- |
| A　session 4%／283 分 ＋ 7d 40%／6000 分（7d far） | 4 | 4 | **4** | 4 |
| A2 session 4%／283 分 ＋ 7d 40%／5000 分（7d mid） | 8 | **4** | 🔴 **4（hybrid）／8（grammar）——見下** | 8 |
| B　session 53%／6 分 ＋ 7d 40%／5000 分 | 8 | 8 | 8 | **2** |
| C　7d 已超前 70%／6000 分（burn-ahead 對照組） | 1 | 1 | **1** | 1 |

🔴 **本表在二審換家之後重跑，四格中三格不變、A2 一格會隨「家」而不同**〔本輪實測，輸出逐字；`home` 的三種語意定義見 §0.3.1〕：

```
情境  home     today  L1  L1+L2abs   逐軸(band/horizon/L2窗長)
A    windows     4   4         4   free/far/300.0,free/far/300.0,free/far/10080.0
A    grammar     8   4         4   free/mid/None,free/far/300.0,free/far/10080.0
A    hybrid      4   4         4   free/far/None,free/far/300.0,free/far/10080.0
A2   windows     8   4         8   free/far/300.0,free/far/300.0,free/mid/10080.0
A2   grammar     8   4         8   free/mid/None,free/far/300.0,free/mid/10080.0
A2   hybrid      8   4         4   free/far/None,free/far/300.0,free/mid/10080.0
B    windows     8   8         8   notice/near/300.0,notice/near/300.0,free/mid/10080.0
B    grammar     8   8         8   notice/near/None,notice/near/300.0,free/mid/10080.0
B    hybrid      8   8         8   notice/near/None,notice/near/300.0,free/mid/10080.0
C    windows     1   1         1   free/far/300.0,free/far/300.0,converge/far/10080.0
C    grammar     1   1         1   free/far/None,free/far/300.0,converge/far/10080.0
C    hybrid      1   1         1   free/far/None,free/far/300.0,converge/far/10080.0
```

（三軸依序為 `session`／`five_hour`／`seven_day`；band 直接注入、horizon 由 `quota_pace.horizon()` 導出，窗長一律經指定的家取得、**不手填**。`＋(c)` 那一欄不受 L2 判準影響，故未重跑。）

- **三格不變的理由**：A 的長窗軸是 7 天（`window_minutes = 10080`，不小於地板 ⇒ 不適用，仍 ×0.5，三個 home 同）；B 的兩條短窗軸都在 `near`（L2 只動 `far`／`none`）；C 的長窗軸是 7 天且 `burn_step = +1`〔本輪實測 `lead_pp = 29.52`、`(1, 'burn-ahead')`〕⇒ 三層修法都碰不到它。
- 🔴 **A2 這一格是本版唯一被換家改動的公布數字，必須被三審抽驗**：`hybrid`（＝production 的 horizon 導出不動、只換 L2 的家＝本版採用的修法）下 A2 是 **4**；只有把「逐軸窗長」整體改成 kind 的純函式（`grammar`）才是 **8**。⇒ 前一版寫的「改判準沒有偷偷改動任何一個已經公布的數字」**本版撤回**：它改動了一個，而且改動的方向是**新的過度保守**（8 → 4）。裁決包＝§10 **Q9**。

### 4.4 🔴 誠實劃界：本設計**翻不動帳本記載的 A 案那個 4**

上表 A 列三個修法全上仍是 4。原因〔探針；本輪已重驗〕：A 案裡 7 天軸自己就是 `far`（剩 6000 分 > `far` 門檻 5040 分）且 `note=''`（既非超前也非節儉——〔本輪實測〕`lead_pp(40.0, 6000.0, 10080.0) = −0.4762`、`burn_step(...) = (0, '')`，而 `anchor_margin_pp(10080) = 0.5952`〔本輪實測〕⇒ 差約 0.12pp 沒越過節儉門檻）⇒ 週軸吃 ×0.5，L1 讓它 binding，**L2 對它不適用（改後判準：10080 不小於地板 10080，這一句現在是結構事實不是觀測）**，L3 不觸發。

**要把 A 案翻成 8，唯一的路是拿掉週軸在「無燃燒證據」時的 ×0.5 —— 那正是帳本 `:205` 逐字否決的「動 `pace_far`」方向的實質等價物。**

⇒ 本提案**不重走**它，改把這件事升成一個具名裁決項（§10 Q3），連同兩個事實一起交給四方：
1. 帳本同一列同時要求「修好 A 案的反向」與「不得鬆掉週軸」，而本輪的分析顯示這兩件事在 A 案這一格**互斥**；
2. 對照組 C（週軸真的超前）在三層修法下仍然收斂到 1〔探針〕⇒ 煞車沒有被拆掉，被討論的只有「無證據時要不要主動懲罰」。

### 4.5 對既修項的相容性檢查

| 既修項 | 相容性 |
| :---- | :---- |
| `DEF-200-196` fixed@R105 | ✅ 無交集 |
| `DEF-200-201` fixed@R107（`pace_index` 顯示行自帶語意） | ✅ L1~L3 不改 `pace_index`／`pace_ceiling` 任何一行；`burn_step()` `:242` 的 ceiling 短路原封不動 |
| `DEF-200-202` fixed@R105（`decide` 補 `active_model`） | 🔴 **有交集，必須明文約束**：L1 的 min 必須跑在 `gate`（`:634-635`，已過濾 `FALLBACK_KINDS` 與未命中的 `MODEL_SCOPED_KINDS`）之上，**不得**改回 `readings`。否則 R105 才修好的「保險池／別的模型不得節流主力」會原樣復發 |
| `DEF-200-200`（open，`resets_at` 已過去四層誤判） | ⚠️ **④ 是本節的前置量測**：`row_of()` `:555` 只落 `ts/pct/live/fp`〔現查碼〕⇒ 燃燒落款**結構上量不到 horizon**。本輪實測本機落款 17 列（跨度 `2026-08-19T02:09:41+08:00` .. `2026-08-28T19:26:51+08:00`）〔探針〕，8 個 kind 皆有 pct，**零列帶 `resets_at`** ⇒ L2／L3 的實際射程（一年裡有多少比例的決策會被它改到）今天**量不到**。見 §9 的排程建議 |
| `DEF-200-200` ②（`_delta_minutes` 把任何負值標 `clock-skew`） | ✅ 負值 ⇒ `horizon()` `:173-174` 強制 `AXIS_MID`(×1.0)，L1 逐軸取值時原樣沿用 |

---

## 5. 配速三改動 (a)(b)(c)

> R107 的判定（`docs/04_planning/R107_RESUME.md:167-173`）逐字：「先慢後快」不適宜，錯不在目標，錯在**用「時刻」當代理變數而不用「燃燒證據」當主控訊號**；早段 throttle 砍到額度最充裕時的主力工作、晚段 ×2 落在 commit／push 等 must-finish 高風險動作上，方向正好相反。以下三改動即這句話的三個落點。

### 5.1 (a) thrifty floor —— S 級；**但本批不先行**（一審 Architect→修憲 non-blocking 承接）

🔴 **提案輪標題寫「可先行」而 §9 把 (a) 綁進 W3，兩處自相矛盾，且改動了 Playbook 的執行序卻沒說明。本輪訂正如下：**

- Playbook 原訂〔實讀 `AutoSDD_TechDebt_Paydown_Playbook.md:248`〕逐字：「**(a) 可先行單包**；(b) 四方複審→收尾窗口；(c) 隨 (b) 同層落地」；同檔 `:257` 逐字：「(a) 先行、(b)(c) 隨修憲批走」。
- **本案主張改變這個執行序**，理由是提案輪自己測出來的一件事：**(a) 對週軸有實質射程**（`anchor_margin_pp(10080) = 0.5952pp`〔本輪實測〕⇒ 週軸落後線性預算約 0.6pp 就算節儉，`far` 的 ×0.5 被收回中性）⇒ 它是不是重走帳本 `:205` 已否決的方向，是 **§10 Q3 的裁決標的**。Playbook 立「(a) 可先行」時（2026-08-27）還沒有這個量測。
- ⇒ **改後結論（唯一一種說法，兩處統一）**：(a) 的**工程規模**仍是 **S 級**（落點是 `effective_horizon()` 的 `step < 0` 分支一行），但**它不是本批可先行的項**——它與 Q3 的裁決綁在一起，故編在 **W3**（見 §9）。
- 🔴 **這是一次對 Playbook 的偏離，本批必須具名交出**：Playbook `:248`／`:257` 的「(a) 可先行」在 Q3 裁決之前**暫緩**；若 Q3 裁定 (a) 不在否決射程內，(a) 立即回復「可先行單包」並可脫離 W3（此時 §9 的 W3 只剩 L1+L2）。裁決落地時由收尾窗口同步 Playbook 該兩行——**Playbook 是本 repo 的執行序真相源，不得由本提案書靜默取代**。

**成立條件**：某一軸自己的 `burn_step()` 回 `-1`（`NOTE_THRIFTY`），即 `lead_pp ≤ −anchor_margin_pp(window)`。**門檻完全複用既有的家**（`quota_pace.py:186`／`:245`），一個新數字都不發明。

**落點**：`quota_pace.effective_horizon()` `:267-268` 的 `step < 0` 分支——今天回 `relative`（可能仍是 `far`），改為回「`relative` 與 `mid` 之中較**鬆**的那一個」。等價一行寫法：`return (relative if relative == AXIS_NEAR else AXIS_MID), note`。

- 值域：只可能把 `far → mid`；`near` 保持 `near`；`none` 到不了這一臂（`lead_pp` 對 `minutes is None` 回 `None` ⇒ `step == 0`）。
- **地板是 1.0＝中性，永遠不是加速**——這是它與被否決的「調 `pace_far` 常數」的分界：後者是**無條件**拿掉懲罰（含正在超前的軸），前者是**逐軸、憑該軸自己的燃燒證據**把懲罰收回到中性。
- **方向鎖**：`step >= 0` 的所有輸入，輸出必須**逐位元**等於今天。
- 🔴 **(a) 對週軸有實質射程，必須明說**：`anchor_margin_pp(10080) = 0.595pp`〔探針〕⇒ 週軸只要落後線性預算 0.6pp 就算節儉。**這是一個真的放寬**（週軸 far+thrifty 時 ×0.5 → ×1.0）。四方必須裁決它是否落在帳本 `:205` 的否決射程內（§10 Q3）。
- 〔探針〕**(a) 在 5 小時軸上的可達區域比直覺小**：`anchor_margin_pp(300) = 20pp` ⇒ 需 `elapsed_min ≥ 60 + pct×3` 才可能判節儉。實測四點：`4%／剩283分`（elapsed 17 分）`lead=−1.67 step=0` ⇒ **不觸發**；`2%／剩200分`（elapsed 100 分）`lead=−31.33 step=−1` ⇒ 觸發（`far` → 本改動後 `mid`）；`10%／剩150分` 與 `30%／剩100分` 皆已是 `mid`，(a) 無作用。

### 5.2 (b) `bursting_ok()` 接線 ＋ `pace_near` ×2 改條件制 —— L 級，**修憲級**

#### 5.2.1 現況

`bursting_ok()`（`quota_pace.py:589`）六條件已實作且自帶紅綠測試〔現查碼 `tools/tests/test_quota_policy.py:3008-3041`〕，但檔頭 `:578-580` 逐字自陳「**只算、不接線**……呼叫端目前只有本檔的單元測試」。〔探針〕`bursting_ok()` 全部缺省 ⇒ `(False, 't_rem_minutes=None ⇒ fail-closed')`；六條件皆給且成立 ⇒ `(True, 'burst')`。

而 `pace_near = 2.0` 今天**只憑 `horizon == near` 一個條件**就給出 ×2——那正是「用時刻當代理變數」。

#### 5.2.2 🔴 接線的真正阻塞：兩個輸入在本 repo 結構上取不到

| `bursting_ok()` 參數 | 在 `pace_report()` 取得到嗎 | 說明 |
| :---- | :---- | :---- |
| `t_rem_minutes` | ✅ | `decide().binding` 那一軸的 `minutes` |
| `u5h_percent`／`u7d_percent` | ✅ | `state.axes` 逐軸 pct |
| `u7d_lead_pp` | ✅ | `quota_pace.lead_pp()` 現成 |
| `queue_has_work` | ❌ **取不到** | 佇列狀態住引擎（AutoClaude）側；`.importlinter` 的 `no-harness-import` 禁止引擎 import 本層，反向也沒有既有通道 |
| `task_interruptible` | ❌ **取不到** | 同上 |
| `enable_bursting` | ⚠️ 需新 env 鍵 | `AUTOSDD_QUOTA_ENABLE_BURSTING`（bool）。🔴 **出廠值不是開放選擇**：標的 PRD §4.2.6 參考實作 `:766` 逐字已是 `enable_bursting: bool = True`〔實讀〕⇒ 實作端沿用即可（見 §10 Q4） |

`bursting_ok()` 的缺省是 fail-closed（不傳＝不放行）⇒ **直接接線 ＋ 把 ×2 改成條件制，會讓 near ×2 在 hook 與 `--pace` 兩條路上結構性消失**，也就是把掌舵者錨點① 整個關掉。這不是「保守」，是靜默地推翻一條已入憲的需求。

三個候選輸入來源，逐一記錄取捨：

| 候選 | 判 |
| :---- | :---- |
| (i) 引擎 → harness 的**反向契約檔**（沿用 `pace_contract.write` 的既有形態，方向相反） | ✅ **建議**。有既有先例、有磁碟痕跡、可被第三方查證 |
| (ii) 由派工者用旗標自陳（`--pace --queue-has-work`） | ❌ 自陳＝承諾不是機制（`DEF-200-190` 同型判例） |
| (iii) 用 `live_dispatches() > 0` 當 `queue_has_work` 的代理 | ❌ **代理變數**——正是 R107 判「先慢後快」不適宜的同一個錯，換個位置再犯一次 |

#### 5.2.3 因此 (b) 必須分兩階段

- **階段 B1（可先行、零行為變更、S 級）**：`pace_report()` 呼叫 `bursting_ok()` 並把 `(是否放行, 理由)` **只印一行、不改 cap／rec**；同時把六條件的實際輸入值一併落進燃燒落款。目的是把「六條件在生產上到底成不成立、多常成立」變成**可量測**——今天 n=0。
  🔴 這正是本 repo 既有判例的形狀（`quota_pace.py` 檔頭〈為什麼本輪不動 far×0.5〉、R95 §2.2、`DEF-200-193`）：**無樣本時把常數化的行為改成條件制，就是發明數字。**
- **階段 B2（需 B1 的樣本 ＋ 四方裁決 ＋ (i) 的反向契約，L 級）**：`pace_near` ×2 改條件制。條件＝`lead 明顯為負 AND reset 臨近 AND bursting_ok() 六條件通過`；不成立時 near 的乘數夾在 **1.0**（中性，不是 0.5——降到 0.5 會同時觸發 (c) 要治的另一個病）。
  出廠 `ENABLE_BURSTING`：🔴 **必須是 `true`**，否則 B2 落地當天就等於關掉錨點①。這一格本身就是一個裁決項（§10 Q4）。

### 5.3 (c) must-finish 收尾保留段 —— M 級

#### 5.3.1 立案：PRD 已有這條規則，實作零對應物

PRD §4.2.2 `:451-452` 逐字：「若 `T_rem < T_MIN_MINUTES (2)`：→ 不派新工，進入短暫 hold，等待重置事件」；PRD §4.2.5 `:695` 逐字：「若 `T_rem ≤ 預估 Step 執行時間`，則新 Step 極可能跨越重置點被截斷 —— 應延後派工至重置後，而非搶跑」。

〔探針〕實作面：`session 53%／剩 6 分鐘` ⇒ `rec = 8`。**兩條 PRD 規則在 `tools/lib/` 這一側都沒有落點**（🔴 一審承接訂正射程：§4.2.2 那一條在 PRD **自己的參考實作**裡有落點；缺的是治理層實作，不是 PRD 全文。§4.2.5 那一條在參考實作裡也查無落點）。

🔴 **二審 SA non-blocking 承接——該處的逐字引述本版訂正**：一審承接輪把它壓成一行寫成「`:864` `if t_rem_min < T_MIN_MINUTES: return cs.state, 0, "reset_imminent_hold"`」，而 PRD 原文是**兩行、跨 `:864-865`**〔實讀〕：

```python
    if t_rem_min < T_MIN_MINUTES:
        return cs.state, 0, "reset_imminent_hold"
```

⇒ 座標一律改記 **`:864-865`**（本文件 §1 座標表、§6.2 五站點表、本節三處同步改）。壓行會讓下一個人以 `:864` 單行去 grep 而找不到 return 那一半，也讓「逐字」二字不成立。

#### 5.3.2 設計

在 `decide()` 產生 `Decision` 之後（建構順序上與 `model_hint` 同層，結構上讀不到 cap／rec 的輸入面 ⇒ 不可能放寬）追加一段：

```
若 min(逐軸 minutes，忽略 None 與負值) < T_wrap：
    recommended_fanout = min(recommended_fanout, cap_prepare)   # 現查出廠 2
    reason 追加具名字面 "must-finish"
cap 不受本段影響（本段治的是「派了也做不完」，不是「額度不夠」）
```

- 值域：`rec ∈ {0..cap_prepare}`；`cap` 不動；`band` 不動（不造假讀數）。
- **零新常數**：`cap_prepare` 是既有欄位（`:224`）、語意對（prepare＝收尾姿態）。

#### 5.3.3 `T_wrap` 取哪個值 —— 這是 (c) 的全部風險所在

| 候選 | 值 | 〔探針〕對 B 案（剩 6 分）的效果 | 判 |
| :---- | :---- | :---- | :---- |
| `FANOUT_WINDOW_SECONDS / 60` | 5 分 | **不觸發**，rec 仍 8 | 保守下界，但治不到立案情境 |
| `accel_window_minutes` | 30 分 | 觸發，rec **8 → 2** | 對得上 R107 的立案敘述 |
| PRD §9 `autoclaude_step_wall_seconds` 中位數 | — | 今天量不到（該指標 v2.1.8 入憲、未實作） | 正解但無樣本 |

🔴 **取 `accel_window_minutes`(30) 的含意必須說白**：`near` 的門檻就是 30 分鐘 ⇒ **整個 `near` 帶同時是「加速帶」（錨點①）與「收尾帶」（(c)）**，兩者在同一段時間要求相反的動作。

⇒ **這正是 (b) 與 (c) 必須同層落地的結構理由**：`bursting_ok()` 的六條件就是決定「這一次 near 到底該加速還是該收尾」的判準——六條件通過 ⇒ 錨點① 的 ×2 勝出；不通過 ⇒ (c) 的收尾保留段勝出。**任何一邊單獨落地都會在 `near` 帶製造一個沒有裁決者的矛盾。**

本提案建議：`T_wrap` 出廠取 `FANOUT_WINDOW_SECONDS/60`（保守下界、可先行、不與錨點① 打架），並開一個 env 鍵 `AUTOSDD_QUOTA_WRAP_MINUTES`；升到 30 分留給 B2 同窗，屆時有 `bursting_ok` 當裁決者。

#### 5.3.4 🔴 二審 Architect N2 承接：`T_WRAP_MINUTES` 的兩個角色必須拆成兩個鍵

一審承接輪讓 `T_WRAP_MINUTES` 同時承接 **(i) must-finish 門檻**（§4.2.2 原 `:451-452` 的 hold 觸發）與 **(ii) `V_safe` 的除數下限**（原 `:453`）。二審 Architect 指出**那是把本案自己要治的病照抄一次**：本案的核心論證就是「cap 與 rec 兩個角色被當成一個數字」（§3.2）、「`base` 與 `pace` 來自不同軸卻被相乘」（§4.1 R1），而這裡是同一個形態的第三次——**兩個獨立的量共用一個旋鈕**。本輪複驗成立、無異議：

| | 角色 (i)：must-finish 門檻 | 角色 (ii)：`V_safe` 除數下限 |
| :---- | :---- | :---- |
| 它回答的問題 | 「剩這麼點時間，派了也做不完」 | 「`T_rem → 0` 時分母不得發散」 |
| 正確值由什麼決定 | **一個 Step 的預估執行時間**（PRD §9 `autoclaude_step_wall_seconds`，今天量不到 ⇒ 暫用 `FANOUT_WINDOW_SECONDS/60`） | **數值穩定性**（只要嚴格大於 0 即可；原文取 2 是為了讓 `V_safe` 不爆表） |
| 調大它的後果 | 收尾帶變寬（更早停止派新工）＝**行為改變** | 分母變大 ⇒ `V_safe` 變小 ⇒ `C_raw` 變小＝**另一個方向的收緊** |
| 🔴 共用一個鍵的後果 | — | **「把 must-finish 門檻由 5 分升到 30 分」（§10 Q5 明列的路線）會同時把 `V_safe` 的除數下限乘 6**，而那件事從來沒有人論證過、也不在 Q5 的問句裡 |

**⇒ 本版改為兩個鍵（§6.2 改後文本已同步）**：

```
T_WRAP_MINUTES     ← must-finish 門檻。家 = .env 鍵 AUTOSDD_QUOTA_WRAP_MINUTES
                     出廠值 = FANOUT_WINDOW_SECONDS/60（現查 tools/lib/quota_gate.py）
V_FLOOR_MINUTES    ← V_safe 的除數下限（原 T_MIN_MINUTES 的 (ii) 角色，只換名字不換值）
                     家 = .env 鍵 AUTOSDD_QUOTA_VSAFE_FLOOR_MINUTES，出廠值 = 2
                     🔴 出廠 2 的史料出處＝PRD §4.2.6 常數區 `:732` 逐字
                        `T_MIN_MINUTES = 2.0     # 重置臨界保護`〔實讀〕
                        ——它不是本案挑的數字，是原文的出廠值原樣搬過來
兩鍵的方向不變式各自獨立：
  AUTOSDD_QUOTA_WRAP_MINUTES        ≥ V_FLOOR_MINUTES（收尾帶不得比除數下限還窄）
  AUTOSDD_QUOTA_VSAFE_FLOOR_MINUTES ≥ 2（調到 2 以下會讓 :453 相對原文放寬——唯一不准的方向）
```

- **拆了之後 §10 Q5 的耦合消失**：Q5 問的是「must-finish 門檻取 5 分還是 30 分」，拆鍵之後那個問題**只動 (i)**，`V_safe` 的除數下限一格不動。⇒ Q5 的問句本版不必加註「升 30 分會同時動除數」那個警告（那是**不拆**才需要的）；改為在 Q5 明記「已拆鍵，故本題的射程只有 must-finish 門檻」。
- **除數面自己的方向不變式 ＋ 判準**：§7 新增 **P18**（`V_safe` 除數面的單調收緊 ＋ 下界 2 的雙邊帶）。沒有這一條的話，除數這一半就是「換了名字、沒有人守」。
- **為什麼不是「乾脆不拆、只在 Q5 加一句警告」**：警告是散文（本 repo 反覆判過對當下的模型零攔阻力）；而拆鍵之後這件事**結構上不可能發生**。成本是多一個 env 鍵與多一條判準，兩者都在 W1／W3 的同一個持有面內（§9 鐵律七第一列）。

---

## 6. PRD 修憲文本（提案）

> 體例沿用本 PRD 既有的「原條文 → 改後條文 → 為什麼（含實測數字）」。以下**全部是草案**，四方通過後才由另一包落款。

### 6.1 §4.2.2 —— 新增「多軸聚合律」（本 PRD 從未定義它）

**原條文（`:444-457`，逐字保留供對照）**：整節只有**單軸**公式（`U_rem`／`T_rem`／`V_safe`／`C_raw`／`C_target`），**沒有任何一句說明「有 7~8 條計費軸時怎麼合成一個數字」**。

#### 🔴 6.1-pre 先補運算元對映（B10 承接，一審 SA 阻塞項）

一審 SA 指出：新條文用 `cap`／`rec`，而被插入的 §4.2.2／§4.2.3 用 `C_target`／`C_cap`／`C_raw`／`C_min`／`C_default` 這一族封閉列舉，**兩套詞彙之間沒有任何一句對映語句** ⇒ 落款後讀者無法判斷「新增的第 7b 步」動的是哪一個既有運算元。本輪複驗成立，且**發現既有那份對映表本身就是歧義的來源**〔實讀 PRD `:519-524`〕：v2.1.8 §4.2.4 的〈運算元對照〉表把 `C_target` **同時**對到兩個東西——

> | `C_target` | `decide().cap`（硬上限）／`decide().recommended_fanout`（諮詢值） | `cap` 是**無狀態純函式** …… |

⇒ 一個 PRD 運算元對到兩個實作量，正是本案要治的「兩個角色被當成一個數字」在**文本層**的同型。

**⇒ 落款時先新增小節「4.2.2-c 運算元對映（規範性）」，作為兩套詞彙的唯一真相源**（沿用 v2.1.9 對 `TELEMETRY_UNMEASURED_CAP` ↔ `AUTOSDD_QUOTA_DEGRADED_CAP` 的 `_PAIRS` 對映判例）：

🔴 **二審 SA-3 承接：對映表漏了本節射程內用得最兇的兩個運算元。** 逐字實查〔實讀〕：§4.2.3 的 8 步封閉列舉（`:464-471`）**通篇用裸 `C`** —— `1. HALTED_MANUAL → C = 0`／`6. U7d ≥ WEEKLY_DRAIN_PERCENT → C = min(C_target, 1)`／`8. 其他 → C = C_target`；而 §4.2.8 `:948` 用的是 **`C(t)`** —— `C(t) = clamp(floor(C_default / pace_index), C_min, C_cap(state))`。**兩者原表都沒有列** ⇒ 新增的第 7b 步寫 `C_target = …` 而它的鄰居（第 7、8 步）寫 `C = …`，讀者無法判定「被改的是同一個量嗎」。本版補列，並讓 7b 的賦值對象可判定（§6.3 同步改）。

🔴 **二審 SA-2 承接：`C_default` 那一格與 PRD `:2241` 的既有裁決衝突且零引用。** PRD `:2241` 逐字〔實讀〕：「**原判準的 `C_default` 在本實作沒有對應物，`cap_notice` 是最寬的有限 cap。**」而原表寫 `C_default ↔ _base_rec(band)` ⇒ 同一個運算元，PRD 說「沒有對應物」、本案說「有」。**兩邊都對，因為問的不是同一件事**（`:2241` 那一段的標題是〈重置後不暴衝〉，整段在講 **cap 側**的判準；本案要用的是**諮詢值側**的 base）⇒ 本版改為一句合流並**逐字引用** `:2241`，不撤回也不覆蓋它。

```
【v2.1.10 新增，規範性】§4.2 各節的 C-族運算元 ↔ 本實作量的對映（一對一，唯一真相源）：

  C            ↔ 第 N 步閘門的**輸出併發數**（§4.2.3 八步列舉的左值）。短路後的終值
                 等於 C_target 與該步上限的較小者；本實作面它不是一個獨立欄位，而是
                 「cap 與 rec 兩欄一起交出去」的那一對（見下兩列）。
                 🔴 §4.2.3 第 8 步「C = C_target」即宣告：未被前七步短路時，C 就是 C_target。
  C(t)         ↔ 同 C（§4.2.8 `:948` 的時間參數化寫法，強調它每個控制時點重算）。
                 本實作對應 quota_policy.decide() 的**每次呼叫**（無狀態純函式，不帶記憶）。
  C_cap(state) ↔ cap    = quota_policy.Decision.cap（硬上限／煞車；None＝不設限）
  C_target     ↔ rec    = quota_policy.Decision.recommended_fanout（諮詢值／節奏）
  C_raw        ↔ int(base × pace) 夾界**之前**的中間值（實作面不具名、不落欄位）
  C_min        ↔ _clamp() 的下界 1（非 halt 一律 ≥1，見 §4.1.5 F3）
  C_default    ↔ **分兩側，不是一個對應物**（合流 §11.2〈重置後不暴衝〉`:2241` 的既有裁決）：
                 · **cap 側**：§11.2 `:2241` 逐字「原判準的 C_default 在本實作沒有對應物，
                   cap_notice 是最寬的有限 cap」——該裁決**維持不變**，本表不覆蓋它。
                 · **諮詢值側**（§4.2.2 C_raw 與 §4.2.8 C(t) 兩式裡的那個 C_default）：
                   ↔ _base_rec(band)（band 階梯，不是一個常數）。
                 🔴 兩側之所以不同：cap 側問「最寬的有限上限是多少」（要一個常數），
                    諮詢值側問「這一帶的基準建議是多少」（是 band 的函式）。
  C_current    ↔ **不存在**（見 §4.2.4 的既有判決：本實作無持久併發設定點）

🔴 §4.2.4 的〈運算元對照〉表把 C_target 同時對到 cap 與 recommended_fanout，
   該格改為指向本節（`見 §4.2.2-c`），不在該處維護第二份對映。
🔴 本表是**對映**不是相等宣稱（同 CREDIT_POOL_KEYS／FALLBACK_KINDS 的既有判例）：
   C-族是 PRD 的控制論詞彙，右欄是本實作的量；對映關係入憲，數值不入憲。
```

**改後（新增小節 4.2.2-b「多軸聚合律」）**：

```
本實作同時觀測 N 條計費軸（現查快取實測 7~8 條）。運算元對映見 §4.2.2-c。聚合律：

(1) C_cap（硬上限／煞車）    = min(逐軸 C_cap)，逐軸 C_cap = f(band_x, horizon_x)
(2) C_target（諮詢值／節奏） = min(逐軸 C_target)，逐軸 = g(band_x, horizon_x)，再夾 (1)
    🔴 C_target 的稀缺度與節奏**必須來自同一軸**。禁止「A 軸的 band × B 軸的 horizon」。
(3) 期程不明且仍有煞車力的軸（C_cap is not None 且 horizon 未知）⇒ 全域把節奏夾在 1.0
(4) 方向不變式（加軸單調）：對**同一份讀數**加一條軸進來，C_target 不得變大。
    🔴 本條量的是「加軸」，**不是**「換一套聚合律前後」——(1)(2) 相對舊聚合律
    在短窗 far 軸上是刻意的放寬（見 §4.2.8 R-4.2.8-1），那不受本條約束。
    兩者各有自己的方向鎖（§11.2：加軸不變式 ／ 舊律收緊面）。
(4b) 🔴 (4) 的射程（v2.1.10 具名收窄；沒有這一條，(4) 入憲當天就是一條在生產上
     會紅的條文）：(4) 成立為「零違反」的前提是**下列兩條同時成立**（合取，缺一
     即不成立）——
       (i) **該份讀數的每一條軸，其窗長都由該軸自己的桶名文法解得出**；且
       (ii) 🔴 **該份讀數的 C_cap 聚合成員集合（本實作面＝gate_list）非空**，
            即至少有一條軸既不屬美元計價／超額類（現查 quota_policy.FALLBACK_KINDS）
            亦不是「未命中本次模型的模型分軌軸」（現查 MODEL_SCOPED_KINDS）。
     ⇒ **(4) 今天被違反是多歸因的，至少三條通道，逐條各有各的機制**：
       · 通道 A（聚合律）：跨軸 max —— 稀缺度與節奏來自不同軸。(1)(2) 把它轉綠。
       · 通道 B（分類的家）：(i) 不成立時，逐軸窗長經「同 reset 鄰軸繼承」取得
         （現查 tools/lib/quota_pace.py::windows()）⇒ 繼承改變該軸的 horizon
         ⇒ 加一條軸可以讓既有軸的 horizon 由 far 翻 near ⇒ C_target 變大。
       · 通道 C（**成員資格翻面**）：(ii) 不成立時，加一條非 FALLBACK／已命中的軸
         會讓 gate_list 由空翻非空（現查 quota_policy.py 的 `gate = gate_list or
         readings` fail-safe），於是**原本在聚合面上的煞車軸整批離開** ⇒ C_target
         變大。🔴 **這條通道與窗長文法完全無關**：它在 (i) 成立的讀數上照樣發生。
     實測（出廠值下，皆〔本輪實測〕）：
       · (i) ∧ (ii) 皆成立的面 ⇒ 違反 **0**（封閉面 56,448 個加軸對；再加含
         FALLBACK／MODEL_SCOPED 桶名但窗長皆解得出的 69,840 個加軸對，亦為 0）。
       · (i) 不成立（含解不出窗長的桶名）⇒ 違反 **1972**〔母體 109,800；此數為
         「把 §4.2.8 R-4.2.8-1b 整條拿掉、只留 (1)(2)」那一格，即與 L2 無關〕。
       · (ii) 不成立（窗長皆解得出、但 gate_list 起初為空）⇒ 違反 **7515**
         〔母體 109,800，同一 mode〕；定向兩例逐字 **4 → 16**（gate 面關閉時同兩例
         為 4 → 4）：`seven_day_overage_included ×2 ＋ five_hour`／
         `weekly_scoped ＋ seven_day_opus ＋ five_hour`。
     ⇒ **本條只負責把射程說清楚，使 (4) 不成為一句假的全稱宣稱。** 通道 B、C 的關閉
     各自需要一次獨立裁決（B＝取消繼承，方向未經證據裁決：實測在某些軸上收緊、在
     某些軸上放寬；C＝改動 gate 的 fail-safe 退回語意，那是 R89／R98 兩次憲法裁決的
     持有面）⇒ **兩者皆不由本版入憲**，具名登記於 §8-11（通道 B）／§8-12（通道 C）
     ＋ §10 Q9。
     🔴 本版**不宣稱**「關掉通道 B 之後 (4) 就歸零」——那句話已被通道 C 的實測證偽。
```

**為什麼**：實測（合成輸入，`decide()` 真呼叫）`session 4%／剩 283 分` 在 7 天軸剩 6000 分時 `C_target`=4、剩 5000 分時 =8——**兩個 5 小時軸一格未動，`C_target` 卻 2 倍變化**。原因是 `base` 取自最緊的軸而 `pace` 取自期程最短的軸，兩者可以是不同軸。全笛卡兒積 4096 組驗證：改採同軸聚合後 1422 組收緊、2674 組相等、**0 組放寬**（三個數皆為出廠值導出量，不入憲）。
🔴 **(4) 對今天就是一條會紅的不變式**〔本輪實測，注入面已改為 `(band, kind, minutes)`、窗長經指定的家取得〕：現行跨軸 max 在 **109,800** 個加軸對取樣中有 **9156** 個讓 `C_target` 變大（封閉面 56,448 個加軸對中 3640 個）⇒ (4) 不是為新聚合律訂做的新約束，是把一個今天就被違反的性質寫下來，而 (1)(2) 是把**其中一條通道（A）**轉綠的那一步（另兩條通道 B／C 與 (4) 的完整射程見 (4b)）。

### 6.2 §4.2.2 —— 廢除 `T_MIN_MINUTES`、兩個角色拆成兩個鍵 ＋ 收尾保留段

**原條文（`:451-453`，🔴 B9 承接：射程從兩行擴到三行）**：

```
若 T_rem < T_MIN_MINUTES (2):
    → 不派新工，進入短暫 hold，等待重置事件
V_safe     = U_rem / max(T_MIN_MINUTES, T_rem)          ← :453，提案輪漏掉的那一行
```

🔴 **B9（一審 SA 阻塞項）本輪複驗成立**：`T_MIN_MINUTES` 在原條文裡有**兩個**用途——(i) `:451-452` 的 hold 觸發門檻、(ii) `:453` 的**除數下限**（防 `T_rem→0` 時 `V_safe` 發散）。提案輪只廢了 (i)，`:453` 的 (ii) 沒有同步 ⇒ 落款後 `:453` 變成對一個已被廢除的字面的懸空引用。

🔴 **本輪順帶查出 B9 也沒點到的另一半：提案輪那句「前者是一個沒有家的字面」是錯的，而且射程是 5 個站點不是 2 個。** 全文 `grep T_MIN_MINUTES` 於標的 PRD〔實讀〕：

| 站點 | 內容 | 性質 |
| :---- | :---- | :---- |
| `:451` | `若 T_rem < T_MIN_MINUTES (2):` | hold 門檻（提案輪唯一處理到的） |
| `:453` | `V_safe = U_rem / max(T_MIN_MINUTES, T_rem)` | 除數下限（**B9 指出的那一個**） |
| **`:732`** | **`T_MIN_MINUTES = 2.0     # 重置臨界保護`** | 🔴 **它的家**——就在本 PRD §4.2.6 參考實作的常數區（`V_FLOOR = 0.02` 的鄰行）。⇒ 「沒有家的字面」這句話**被證偽**，該理由本輪撤回 |
| **`:864-865`** | 兩行〔實讀，逐字〕：`    if t_rem_min < T_MIN_MINUTES:` ／ `        return cs.state, 0, "reset_imminent_hold"` | 參考實作裡的 hold 門檻消費端。🔴 **二審 SA non-blocking：一審承接輪把這兩行壓成一行寫，本版訂正座標為 `:864-865`**（§5.3.1 同步） |
| **`:868`** | **`    v_safe = u_rem / max(T_MIN_MINUTES, t_rem_min)`** | 參考實作裡的除數下限消費端 |
| `:2520` | 附錄 A 問題清冊 A-09 逐字「§4.2.2（`T_MIN_MINUTES` hold）」 | 🔴 **史料，不得改**（v1→v2 問題清冊記錄的是**當時**的處置） |

⇒ **廢除理由改寫（原理由被自己的實查證偽，換成一個真的成立的）**：`T_MIN_MINUTES` 不是「沒有家」，而是 **(1) 它的 hold 語意（`C = 0`）與 v2.1.8 才入憲的 §4.1.5「禁止靜默鎖死、`C_cap ≥ 1`」直接衝突**；**(2) 它一個字面承載兩個獨立的量**（hold 門檻 ＋ 除數下限），而本案通篇要治的就是這個形態。⇒ **廢除這個名字，把兩個角色各給一個有 `.env` 家與方向不變式的鍵**（🔴 二審 Architect N2 承接；一審承接輪寫的「兩者語意完全重疊 ⇒ 留一個」**本版撤回**，理由與反證見 §5.3.4）。

🔴 **落款包必須同窗處理 5 個站點（不是 2 個）**：`:451`／`:453`／`:732`／`:864-865`／`:868`。**`:2520` 一個字不動**（史料）。漏掉 `:732` 的後果最嚴重：那是常數定義本身，刪了 `:451`／`:453` 而留著 `:732` ⇒ PRD 裡多一個零消費端的常數；刪了 `:732` 而留著 `:864-865`／`:868` ⇒ 參考實作直接 `NameError`（那段是可貼可跑的 Python）。

**改後（三行一起改，兩個角色兩個鍵）**：

```
若 T_rem < T_WRAP_MINUTES:
    → C_target 收斂到 cap_prepare 語意（現查 tools/lib/quota_policy.py::Policy.cap_prepare），
      並在輸出面具名標示 "must-finish"；C_cap 不受本條影響。
V_safe     = U_rem / max(V_FLOOR_MINUTES, T_rem)        ← 除數下限由**它自己的**鍵承擔

T_WRAP_MINUTES  的家 = .env 鍵 AUTOSDD_QUOTA_WRAP_MINUTES
  出廠值 = FANOUT_WINDOW_SECONDS/60（現查 tools/lib/quota_gate.py；本 PRD 不複寫數字）
  下界不變式：AUTOSDD_QUOTA_WRAP_MINUTES ≥ V_FLOOR_MINUTES（收尾帶不得比除數下限還窄）
V_FLOOR_MINUTES 的家 = .env 鍵 AUTOSDD_QUOTA_VSAFE_FLOOR_MINUTES，出廠值 = 2
  🔴 出廠 2 **不是本案挑的數字**，是原文出廠值原樣搬過來：§4.2.6 常數區 `:732` 逐字
     `T_MIN_MINUTES = 2.0     # 重置臨界保護`。
  下界不變式：AUTOSDD_QUOTA_VSAFE_FLOOR_MINUTES ≥ 2
     （調到 2 以下會讓 :453 相對原文放寬——唯一不准的方向；2 這個界的史料出處同上）
🔴 兩個鍵**不得合併**（v2.1.10 具名裁決）：它們的正確值由不同的東西決定
   （must-finish 門檻由「一個 Step 要跑多久」決定；除數下限由數值穩定性決定），
   合併之後「把收尾帶由 5 分升到 30 分」會連帶把 V_safe 的除數下限乘 6，
   而那件事沒有任何論證支撐。詳細對照表見本提案書 §5.3.4。
🔴 原文的「不派新工（C=0）」廢除：與 §4.1.5「禁止靜默鎖死、C_cap ≥ 1」直接衝突。
🔴 原文的常數 T_MIN_MINUTES 廢除（非改名）：它一個字面承載兩個獨立的量。
   落款時同窗處理五個站點：§4.2.2 兩處（hold 門檻／除數）＋ §4.2.6 三處（常數定義＋
   兩個消費端）。**附錄 A 的 A-09 那一列是史料，一個字不動。**
```

**為什麼（兩條，第二條是 B9 補上的、本版依 N2 改寫）**：

1. 實測 `session 53%／剩 6 分鐘` 今天 rec=8——PRD 這條規則在**實作面**（`tools/lib/`）一個落點都沒有（🔴 精確劃界：它在 PRD **自己的參考實作**裡是有落點的，`:864-865`；沒有落點的是 `tools/lib/` 這一側。提案輪那句「一個落點都沒有」射程寫太寬）；而原文的 `C=0` 若照字面實作，會與 v2.1.8 才入憲的 §4.1.5「禁止靜默鎖死」互相矛盾。
2. **除數角色只換名字、不換值，方向逐位元不動**（拆鍵之後這一條比一審承接輪的版本**更強**）：`V_FLOOR_MINUTES` 出廠 **2 ＝ 原 `T_MIN_MINUTES` 的出廠值**〔實讀 `:732`〕⇒ `:453` 改寫前後**同一組輸入得到同一個 `V_safe`**，不需要任何「方向是收緊」的論證來替它辯護。一審承接輪那條論證（「兩個候選值 5 或 30 都大於 2 ⇒ 分母變大 ⇒ 收緊」）**本版撤回**：它成立，但它成立的前提正是 N2 指出的耦合（除數跟著 must-finish 門檻走），而拆鍵之後那個耦合不存在了 ⇒ 那條論證失去標的。

### 6.3 §4.2.3 —— 閘門優先序補一步 ＋ 「cap 不吃加速乘數」

**原條文（`:461-472`）**：8 步封閉列舉（`:464-471`），**每一步的左值都是裸 `C`**〔實讀，逐字抽三步〕：`1. HALTED_MANUAL                         → C = 0`／`6. U7d ≥ WEEKLY_DRAIN_PERCENT            → C = min(C_target, 1)`／`8. 其他                                   → C = C_target`。

**改後（🔴 B10 ＋ 二審 SA-3 承接：新步驟必須讓「它改的是哪個量」相對鄰居可判定）**：在第 7 步與第 8 步之間插入：

```
7b. T_rem < T_WRAP_MINUTES        → C = min(C_target, C_cap_prepare)，標示 must-finish
                                    （🔴 與第 6 步「C = min(C_target, 1)」逐字同形：
                                      左值是裸 C、右邊夾一個上限，本步只是把上限
                                      由字面 1 換成 cap_prepare 語意。
                                      C_cap 不變；C_cap_prepare 的對映見 §4.2.2-c 與
                                      現查 tools/lib/quota_policy.py::Policy.cap_prepare）
```

🔴 **為什麼左值必須從 `C_target` 改成 `C`**（二審 SA-3）：本節八步的左值一律是裸 `C`，而一審承接輪的 7b 寫 `C_target = min(C_target, cap_prepare)` ⇒ 讀者無法判定它與第 6、8 步動的是不是同一個量（`C` 與 `C_target` 在原文裡是**兩個字面**，而 §4.2.2-c 之前沒有任何一句說它們的關係）。改後 7b 與第 6 步**逐字同形**，同型性一眼可判；而「`C` 未被短路時就等於 `C_target`」這件事由 §4.2.2-c 的第一列與第 8 步共同宣告，不在本節重述。

並在本節末追加一條規範性要求：

```
🔴 R-4.2.3-2（新增）：時間視野（horizon）乘數只作用在 C_target（節奏），**不得**作用在
   C_cap（煞車）。C_cap 對 horizon 的乘數上界為 1.0。
   立案：現行 _cap_for(notice, near) = cap_notice × pace_near = max_fanout
   ⇒ 50~70% 這一整個節流帶，只要 reset 在加速窗內，節流就等於不存在。
   （三個欄位的現值一律現查 tools/lib/quota_policy.py::Policy；本 PRD 不複寫數字。）
   實測（出廠值下）：把 C_cap 側乘數夾在 1.0 之後，20 格中 C_cap 改變 3 格、
   **C_target 改變 0 格**、free×near（掌舵者錨點①）的 C_cap(None)/C_target(max_fanout)
   逐格不變、`C_cap == max_fanout` 的格數 1 → 0。
```

### 6.4 §4.2.5 —— 突刺六條件的接線點與缺輸入姿態入憲

**原條文（`:686-695`）**：只列六條件，**沒有說它在哪裡被求值、缺輸入時怎麼辦**。

**改後**：六條件全文不動，追加：

```
🔴 R-4.2.5-1（新增，接線）：六條件的求值點 = tools/lib/quota_gate.py::pace_report()。
   任一輸入不可得 ⇒ fail-closed（不放行突刺），且**必須在輸出面說出是哪一個輸入不可得**
   ——靜默地不放行與「條件真的不成立」在畫面上必須分得開。
🔴 R-4.2.5-2（新增，輸入來源）：queue_has_work / task_interruptible 是引擎側事實。
   唯一合法通道 = 引擎 → 治理層的檔案契約（與既有 pace_contract 反向、同形態）。
   明文否決兩個替代：①由派工者旗標自陳（承諾不是機制）；
   ②用滾動派發帳 live_dispatches() 當代理（代理變數，正是本節要治的病）。
🔴 R-4.2.5-3（新增，分階段）：在生產樣本 n = 0 之前，六條件**只准出聲、不准參與決策**。
   把一個常數化的行為改成條件制卻沒有樣本，等於發明數字（同 §4.2.4 對 watermark 遲滯的判決）。
```

### 6.5 §4.2.8 —— 補「horizon 乘數層」與 `pace_index` 的關係

**原條文（`:941-948`）**：`pace_index = utilization / max(ε, elapsed_frac)`，並建議「採用 `pace_index` 為主控訊號」。

**改後**：追加：

```
🔴 R-4.2.8-1（新增）：本實作在 pace_index 之外另有一層 **horizon 乘數**
   （near / mid / far / none → 乘數），且它的擺幅（現查 pace_near / pace_far，出廠 4×）
   **大於** band 階梯每跨一帶的 2×。⇒ 時間位置的訊號結構上可以壓過餘裕訊號兩個帶，
   這是「recommended 與實際餘裕反向」的算術來源。
   規範性要求：far 這一檔**必須**拆成兩個語意，且兩者的證據門檻不同：
     · 「沒有 use-it-or-lose-it 急迫感 ⇒ 不加速」  ⇒ 上限 1.0，**零證據即可施加**
     · 「主動減速（乘數 < 1.0）」                  ⇒ **必須**有該軸自己的超前燃燒證據
                                                     （burn_step == +1）
   未用完即蒸發的短窗軸不得因「窗還很長」被施加減速；該軸對長窗配額的保護由跨窗攤提
   承接（§4.2 既有機制），不由併發乘數承接。
🔴 R-4.2.8-1b（新增，B14~B16 ＋ 二審 N1／N7 承接——「短窗」的判準）：
   「短窗軸」＝該軸自己的窗長 **嚴格小於** W_TOTAL_FLOOR_MINUTES（絕對地板；家 = .env 鍵
   AUTOSDD_QUOTA_TOTAL_FLOOR_MINUTES，出廠值 = 一週的分鐘數）。
   🔴 **本條所稱「該軸自己的窗長」的唯一真相源 = tools/lib/quota_pace.py::window_minutes(kind)**
   ——一個**只讀該軸自己桶名**的純函式。適用性的三態必須寫死：
     · 窗長 < 地板        ⇒ 適用（far／none 乘數改 1.0）
     · 窗長 ≥ 地板        ⇒ **不適用**（仍受減速）
     · 窗長解不出（None） ⇒ **不適用**（仍受減速；fail-safe：不確定時不放寬）
   🔴 四條禁令（各自已有一個被證偽的前身，逐條寫下）：
     ① 判準**不得**相對「本次讀數中最長的窗長」——那讓分類依賴輸入集合，
        加一條更長窗軸會把原最長軸重分類 ⇒ 直接違反 §4.2.2-b (4)。
     ② 判準**不得**寄生在跨窗攤提的 rate／total 軸選取（quota_pace.amortize()）：
        該函式只回最短／最長兩個 argmax，**中間窗長的軸沒有分類**，且換算比缺席時
        整個回 None。
     ③ 判準**不得**是桶名清單（既有禁令：窗長由文法導出，不由桶名）。
     ④ 🔴 判準**不得**取 quota_pace.windows()（v2.1.10 新增禁令）：該函式對文法解不出的
        桶名會**由同 reset 的鄰軸繼承最短窗長**，於是同一條軸的分類會隨「旁邊有哪些軸」
        而變 ⇒ 與 ① 同型。實測（出廠值下）：windows(spend 單獨) = (None,)、
        windows(spend + monthly_all 同 reset) = (43200.0, 43200.0)。
   🔴 env 鍵的方向不變式：只准調**小**（更嚴）。調大會把長窗軸拉進放寬射程 ⇒
      那是無證據放寬，與 band_inputs() 的「只調高不調低」同族。
   ⇒ 推論（結構事實，不是觀測）：週窗軸的窗長等於出廠地板本身 ⇒ 不小於地板 ⇒
      **本條的適用性判定**對週軸永遠不適用，且該判定與伺服器回幾條桶、有沒有回月桶無關。
   🔴 **上一句的射程（v2.1.10 具名收窄；沒有這一句它就是一句過寬的宣稱）**：無關的只有
      **本條的適用性判定**這一件事。該軸的 horizon（乘數的另一個輸入）仍可能因同 reset
      鄰軸的出現而改變——那是 §4.2.2-b (4b) 具名的**獨立通道**，不由本條治理，也不因
      本條而消失。凡引用本條為「該軸的乘數與其他軸無關」者，皆為誤讀。
   🔴 **邊界風險（v2.1.10 明記，本版不改值）**：出廠地板恰好等於週窗本身 ⇒ 週軸落在
      「不適用」那一側只差一個嚴格不等號。判準寫成 `<=`、或伺服器改回一條窗長略小於
      一週的桶（文法解得出任意「數量詞 × 單位詞」組合），週軸都會**靜默進入放寬射程**
      而外觀不變 ⇒ §11.2 的判準必須含「窗長 == 地板」這一格（期望：不適用）。
🔴 R-4.2.8-2（新增，節儉地板）：任一軸自身的燃燒證據為「省」（burn_step == −1，門檻
   = 該軸窗長導出的 anchor 邊際，現查 quota_pace.anchor_margin_pp）時，該軸的乘數
   地板為 1.0（中性）。**地板永遠不是加速**，且逐軸判定、不得改動共用常數 pace_far。
```

### 6.6 §8-1 —— 429 必須分兩個來源（**本批的核心修憲**）

**原條文（`:2171`，🔴 逐字全文，二審 SA-1 承接：一審承接輪此處用刪節號吃掉了退避規格本體）**：

> | 1 | **非預期 429** | 遙測落後於真實用量，或其他裝置同時消耗 | 優先**遵循回應中的重試建議標頭**；無標頭時採 full jitter 退避：`sleep = rand(0, min(300, 10·2^n))`，最多 5 次。v1 的固定 10/30/90s 無 jitter，多 Agent 同時撞牆會同步重試造成雷群。重試耗盡 → `FREEZING`。**且必須把 429 視為遙測低估的證據**，將 `U5h` 推估值上修 |

🔴 **SA-1 的判詞本輪複驗成立、無異議**：一審承接輪把 (A) 臂寫成一句摘要（「維持原條文：遵循重試建議標頭；無標頭時 full jitter 退避；重試耗盡 → `FREEZING`……」），而**摘要即刪除**——落款包照那一格改寫的話，PRD 全文裡唯一寫著 `sleep = rand(0, min(300, 10·2^n))`、「最多 5 次」與「雷群」立案理由的地方就消失了，而 (A) 臂自己宣稱的是「**維持**原條文」。⇒ **改後 (A) 那一格改為原文逐字複製，一個字元不動**（含 `v1 的固定 10/30/90s` 那一句立案史料）。

**改後**：

> | 1 | **429（兩個來源，處置相反）** | **(A) 工作面 429**：模型 API 在派工時回 429 ⇒ 遙測落後於真實用量或其他裝置同時消耗。**(B) 遙測面 429**：`§4.1.1 T5` 這支唯讀 GET 自己被限流 ⇒ 是**量測通道**的速率限制，與模型額度無關 | **(A)【原條文逐字保留，未改一字】** 優先**遵循回應中的重試建議標頭**；無標頭時採 full jitter 退避：`sleep = rand(0, min(300, 10·2^n))`，最多 5 次。v1 的固定 10/30/90s 無 jitter，多 Agent 同時撞牆會同步重試造成雷群。重試耗盡 → `FREEZING`。**且必須把 429 視為遙測低估的證據**，將 `U5h` 推估值上修。<br>**(B)【v2.1.10 修憲】必須回「量不到」語意**：`band = unmeasured`、`cap = degraded_cap`（現查 `Policy.degraded_cap`，上界不變式見 §4.1.5），**不得**合成任何 `pct` 讀數——`pct=0` 是永遠正常、`pct=100` 是永遠 halt，兩個方向皆為本 PRD §1.2 原則 5 所禁。退避手段＝既有 `QUOTA_CACHE_TTL_SECONDS` 命中（零額外呼叫），**不得**在 hook 關鍵路徑上做行程內 sleep 重試（§15.5 紅線 1 的豁免四條件之一即「TTL≥180s 節流」）⇒ 🔴 **(A) 的「full jitter 退避、最多 5 次」明文只適用於 (A)**，不得被讀成對 (B) 的要求。伺服器給的恢復時刻（`Retry-After` 等標頭）**必須帶到 unmeasured 路徑上**，否則呈現層會把一個會自動解除的限流播報成「不會自己解除」 |

🔴 **落款體例要求（給落款包）**：本格是**分流不是改寫**——原文那一格的四個運算元（重試建議標頭／full jitter 公式／最多 5 次／`FREEZING`）全數留在 (A) 臂內，落款時可用「原文不動、在同一列後追加 (B) 分流」的形態實作，避免逐字複製時漏字。兩種形態任選其一，但**不得**用摘要取代原文。

追加規範性要求：

```
🔴 R-8-1-1（新增）：遙測面失效**不得**污染帳號指紋。具體：不得產生
   posture={} / schema_keys=[] / account_key=None 的替代讀數去蓋掉上一份好快取，
   也不得在燃燒落款寫下一列不帶真實桶名的合成軸——後者會讓跨窗攤提把它讀成
   「換了帳號／換了方案」而重新累積樣本。
🔴 R-8-1-2（新增）：本 repo 自己合成的讀數 kind（例：429 地板、transcript 地板）
   **不得**併入「伺服器桶名」的集合（現查 quota_policy.KNOWN_KINDS），且必須有自己的
   note 字面——把自造 kind 標成「伺服器吐了個沒看過的桶」是一句假話。
   🔴 本條的射程**只有 note 字面那一面**。「核心指紋只算 KNOWN_KINDS 內的桶名」這條
   裁決及其理由（未知桶名的增減定性為 schema 演進、不觸發攤提重置）**已有一個家**：
   ADR-XPLAT-009 §2.2（狀態 Accepted）。本條**引用**它，不重述、不重新裁決；
   要改那條裁決一律走 ADR 修訂，不由本 PRD 旁路。
   〔理由：現行 core_signature() 已是「∩ KNOWN_KINDS」，而自造 kind 依本條不進
    KNOWN_KINDS ⇒ 再寫一句「取數面同時排除自造集合」在建構上不可能改變任何回值＝
    入憲一段永遠不會被求值的判準。〕
```

**為什麼**：當回合實測 —— 餵 `{"retry-after": "60"}` 給 `rate_limited_reading()` 得 `pct=100.0`、`posture={}`、`schema_keys=[]`、`account_key=None`；再進 `decide()` 得 `cap=0 rec=0 band=halt`，逐軸 note 為 `unknown-kind`（因 `rate_limited ∉ KNOWN_KINDS`）。而該函式 docstring 為此舉出的唯一理由（「回 `None` 會得到比 70% 帶還寬鬆的姿態」）在 R100 之後已不成立：`degraded_cap` 出廠值現查 **2**，且 `decide()` 另夾 `≤ cap_prepare`。

### 6.7 §9 —— 補兩個指標（沒有它們，本批的效果量不到）

```
| autosdd_burn_ledger_has_reset_at | bool | 【v2.1.10 新增】燃燒落款是否帶 resets_at。
  今天不帶（現查 quota_pace.row_of），⇒ horizon 相關的任何改動（§4.2.8 R-4.2.8-1/2）
  在事後**結構上量不到射程**。本欄是 §11.2 新增判準的前提。
| autosdd_cap_equals_max_fanout_total | counter | 【v2.1.10 新增】C_cap == max_fanout
  的決策次數（＝「這一次節流結構上擋不住任何扇出」）。立案座標＝DEF-200-197/198/199
  批（帳本 DEF-200-198）。
```

🔴 **QA→修憲 non-blocking 承接**：提案輪把「15 取樣點中 `cap=16` 佔 4」寫進 PRD 條文，而那組數字帳本自標〔他包回報，未複驗〕⇒ **未複驗的數字不得入憲**。條文只留缺陷座標；數字與其算術訂正（14/15，見 §3.1）留在本提案書。

### 6.8 §11.2 —— 新增三條模擬器判準

見 §7（本文件把驗收判準集中在一節，避免同一份知識兩個家；落款時整段搬進 §11.2）。

### 6.9 §11.2 (c) 的承重理由訂正（B12 承接；最小版，不擴張射程）

**原條文（v2.1.9 訂正段，`:549-555`，逐字保留供對照）**：見 §3.6 的引文——結尾逐字「⇒ 不是沒人管，是**已經由別條管**，不必在本節再立第三個機制」。

**改後（只加一段訂正註記，原文一字不刪）**：

```
🔴【v2.1.10 訂正 1／2：承重理由】本段末句「已經由別條管」在**實作面**今天不成立：
   那個「別條」＝§11.2「重置後不暴衝」（要求翻頁後第一拍 C_cap ≤ cap_notice，
   即 None 不得出現），而現查 _cap_for(BAND_FREE, *) 皆回 None ⇒ 該要求一個落點都沒有。
   ⇒ 本段的結論（(c) 不必再立第三個機制）目前**沒有承重理由**，而不是有一個弱理由。
   兩條出路擇一，交 §4.2.4 的裁決者：
     (i) 讓「重置後不暴衝」真的有落點（另立缺陷列，非本批射程）；落地後本段結論恢復成立。
     (ii) (c) 真的立第三個機制。
   在 (i) 或 (ii) 之一落地之前，本段結論標記為**待承重**，不得被引用為既成裁決。

🔴【v2.1.10 訂正 2／2：本段自己少算一格 horizon】本段 `:551` 逐字寫
   「且 `BAND_FREE` 在 near／mid／far **三個** horizon 皆為 `None`（`notice` 於 mid 為 8）」
   ——實作面的 horizon 是**四檔**（現查 tools/lib/quota_pace.py 的 AXIS_NEAR／AXIS_MID／
   AXIS_FAR／AXIS_NONE），漏掉的是 `none`（期程不明）那一格，而它同樣回 `None`。
   ⇒ 該句改為「在**四個** horizon（near／mid／far／none）皆為 `None`」。
   🔴 為什麼這一格不是無害的筆誤：`none` 正是**沒有 resets_at 的軸**那一格，而本 repo
   現查實際存在的無 reset 軸（spend／nimbus_quill／weekly_scoped）全都落在它上面
   ⇒ 少算它等於把「最常出現的那一格」排除在論證之外。同一段的結論（(c) 不必立
   第三個機制）本來就已由訂正 1 判為待承重，本訂正只是把它的**輸入**也修正。
```

🔴 **相鄰數字並列（二審 SA non-blocking，避免下一個讀者以為兩處在講不同的事）**：本節同時出現兩個數——PRD `:551` 原文的「**三個** horizon」與本提案 §3.6／§8-8 的「`_cap_for(BAND_FREE, *)` **四格**皆 `None`」。**兩者不衝突，是同一件事的兩個計數**：四格＝實作的四檔 horizon（含 `none`），三個＝v2.1.9 撰寫時只列了 near／mid／far。⇒ 本提案一律用**四**（含 `none`），並由上方訂正 2 讓 PRD 那一句同步；引用時不得把「三」與「四」讀成兩個不同的量測。

🔴 **本批為什麼只做這麼小的一步**：free 帶那一格是**既有**缺口（M198-1 不製造也不修好它），修它要另立缺陷列（§10 Q6）。本節唯一的目的是**不讓一句已被實測證偽的理由靜靜留在修憲文本裡**替另一段條文承重——那正是 `DEF-200-206` 族（在不完整／已失效的前提上拍板，下輪稽核重開）的成因。

---

## 7. 驗收判準（對齊 PRD §11.2 模擬器形式；**本輪不寫測試碼**）

體例：每條給「注入什麼 → 期望什麼 → 改前必綠／改後必紅的方向鎖」。所有情境皆為**合成輸入餵純函式**，零網路、零真實額度（同 §11.2 開宗明義）。

| # | 判準 | 注入 | 期望輸出 | 🔴 紅綠自證（沒有這一格就沒有鑑別力） |
| :-- | :---- | :---- | :---- | :---- |
| P1 | 遙測面 429 回「量不到」 | `rate_limited_reading` 路徑的 headers ＝ `{"retry-after":"60"}` | `band == unmeasured`；`1 ≤ cap ≤ cap_prepare`；`state.axes == ()` | 把 429 分支改回合成 `pct=100.0` 的單軸 ⇒ 本條**必須轉紅**（`band` 會變 `halt`） |
| P2 | 429 不得抹空指紋 | 同上，且事前快取有一份帶 `posture`／`account_key` 的好讀數 | 好快取未被覆寫；`core_signature()` 回值不變；燃燒落款**列數不增** | 讓 429 分支去寫快取 ⇒ 落款列數 +1 且 `fp == []` ⇒ 本條轉紅 |
| P3 | 429 的恢復時刻不得掉——**判準改為對「管線存在性」逐段斷言**（B13） | headers 帶可解析的 `Retry-After`，**走完 §2.3 M197-4 表的 ①→⑥ 全程**（不是只呼叫 `decide()`） | 六格逐段斷言，缺一即紅：① `measure_detail()` 回三元組且第三格帶非空 `retry_after`；② `note_degraded` 真的收到 `extra`；③ 痕跡檔最後一列帶 `retry_after`；④ 在 TTL 內呼叫 `read_quota()` 得到的 `QuotaState.retry_after` 非空（**這一格才是「TTL 視窗活過去了」的憑證**）；⑤ `decide()` 的 `Decision.retry_after` 非空；⑥ 呈現層**不出現**「不會自己解除」字面 | 🔴 **提案輪的 P3 只斷言 ⑥，那是恆綠的**（M197-1 後 `axes==()` 就永遠走 `escalate`，⑥ 的紅面靠的是別的東西）。改後每一段都有自己的紅面：拆掉任一段 ⇒ 該段那一格轉紅。另兩臂：**(a)** `Retry-After: 0` ⇒ ①的第三格為 `None`、④⑤ 為 `None`、⑥ 必須**仍然**印「不會自己解除」（保護 `DEF-200-196` fixed@R105）；**(b)** 把痕跡列的 `at` 往前挪超過 `QUOTA_CACHE_TTL_SECONDS` ⇒ ④ 必須轉回 `None`（證明④真的在判新鮮度，不是無條件採信最後一列） |
| P4 | 自造 kind 不進伺服器桶名集合 | 任一合成讀數 | 其 kind ∉ `KNOWN_KINDS`；note 字面 ≠ `unknown-kind` | 把它加進 `KNOWN_KINDS` ⇒ 轉紅（雙向） |
| P5 | cap 不吃加速乘數 | `(band, horizon)` 20 格窮舉 | `∀ 格：cap is None or cap < max_fanout`；且 20 格的 **rec 逐格等於改前** | 把 cap 側乘數上界拿掉 ⇒ `notice×near` 回到 16 ⇒ 轉紅 |
| P6 | 錨點① 未被 P5 損傷 | `band=free, horizon=near` | `cap is None` 且 `rec == max_fanout` | 若實作誤把上界套到 free 帶 ⇒ 轉紅 |
| P7 | 「等於無節流」必須出聲 | `cap is None`；以及 `cap == max_fanout` | 輸出行含 `max_fanout` 的**值**與具名字面 | 拿掉那一句 ⇒ 轉紅。🔴 判準取「值 ＋ 具名字面」而非整句文案（同 PRD F4 既有判例） |
| P8 | 同軸聚合對舊聚合律的收緊面 | 三軸 `(band, horizon)` 全笛卡兒積（排除 halt，母體 4096） | **放寬（`new > old`）的組數 == 0**；**收緊組數 > 0** | ①刪掉 `AXIS_NONE` 全域否決 ⇒ **放寬組數必須 > 0** ⇒ 轉紅；②退回跨軸 max ⇒ **收緊組數必須 == 0** ⇒ 轉紅。🔴 **判準只斷言方向與非空，不寫 60／1422／2674 任何一個數**（QA→修憲）：那三個數是 `cap_notice`／`cap_converge`／`cap_prepare`／`pace_near`／`pace_far`／`max_fanout` 六個可由 `.env` 覆寫欄位的導出量，凍成常數等於讓判準在任何人調 env 那天假紅 |
| P9 | **錯位被治好——改結構斷言**（B19） | 兩軸情境對：只移動 7 天軸的 `resets_at`，5 小時兩軸完全不動 | 🔴 **不是「兩次 rec 相等」**，而是：**`Decision.band` 與供給乘數的 `horizon` 必須來自同一軸**——即 `rec == _rec_for(binding.band, binding.horizon)` 逐格成立（`rec` 是某一條真實軸的自洽輸出，不是兩條軸的乘積） | 退回跨軸 max ⇒ A 案的 `rec = _base_rec(session.band) × _mult(seven_day.horizon)`，與**任何一條軸**的 `_rec_for()` 都不相等 ⇒ 轉紅。🔴 **為什麼改**：提案輪的 P9 期望「兩次 rec 相等」被本文件自己的 §4.3 實測否定（A=4／A2=8，且 §4.4 自承三層修法全上仍翻不動那個 4）⇒ 那條判準要綠必須先讓 Q3 裁定放寬，等於把**未裁決**的前提寫進驗收＝假綠產生器。改後的結構斷言與 Q3 的裁決**正交**：無論 Q3 怎麼裁，「rec 必須是某一條真實軸的自洽輸出」都成立。🔴 A=4／A2=8 這個殘留差異**改記為 known-and-accepted**（§8-1、§10 Q3），不由判準假裝它不存在 |
| P10 | 短窗 far 降級不觸及長窗軸；**含「窗長恰等於地板」的邊界格**（二審 N7） | 7 天軸的 5 個代表點（far/mid/near × ahead/thrifty/中性）；**外加一份帶月桶軸的讀數**（B15）；**外加一條 `window_minutes(kind) == W_TOTAL_FLOOR_MINUTES` 的軸**（N7 邊界） | 週軸乘數**逐格等於改前**；**加入月桶軸之後週軸乘數仍逐格等於改前**；**窗長恰等於地板的那一條軸判「不適用」** | ①把 L2 的判準改成「horizon==far」⇒ 週軸乘數變動 ⇒ 轉紅；②🔴 **把判準從絕對地板退回「窗長 < max(本次讀數窗長)」⇒ 月桶那一臂必須轉紅**（週軸被重分類為短窗軸、far 乘數由 0.5 變 1.0）。第②臂就是 B15 的機械物：`window_minutes("monthly_all")` 現查解得出 43200，不需要任何生產改動就能餵進判準；③🔴 **把嚴格不等號 `<` 改成 `<=` ⇒ 邊界那一格必須轉紅**（N7：地板恰等於週窗，一個等號就把週軸拉進放寬射程） |
| P11 | 節儉地板不加速、不動常數 | `burn_step == −1` 且 `relative == far`／`== near`／`step >= 0` 三臂 | far ⇒ mid；near ⇒ near；`step >= 0` ⇒ **逐位元等於改前** | 把地板寫成 `AXIS_NEAR` ⇒ 第二臂與第三臂皆轉紅 |
| P12 | 超前煞車未被拆掉（對照組） | 7 天軸 70%／剩 6000 分（`burn-ahead`） | 三層修法全開後 rec **仍為 1** | 若 (a) 誤把 `step > 0` 也套地板 ⇒ 轉紅 |
| P13 | 突刺六條件 fail-closed 且**說得出是哪一個** | 逐一抽掉六個輸入 | 六次皆不放行，且輸出行分別具名該輸入 | 把理由字串折成同一句 ⇒ 轉紅 |
| P14 | must-finish 保留段 | `T_rem` 掃過 `T_wrap` 兩側 | 越線側 `rec ≤ cap_prepare` 且 reason 含 `must-finish`；`cap` 兩側相等 | 讓 (c) 去改 cap ⇒ 轉紅 |
| P15 | (c) 不製造靜默鎖死 | `T_rem = 0`，非 halt 帶 | `rec ≥ 1` | 把下界寫成 0 ⇒ 轉紅（保護 PRD §4.1.5 F3） |
| **P16** | **加軸單調不變式（§4.2.2-b (4) 的機械物；B14 的正面）。🔴 注入面與射程兩者本版都改了（二審 N1）** | 「基底 N 軸 ＋ 加 1 軸」的組合窮舉；軸 ＝ **`(band, kind, minutes_to_reset)`**——`kind` 是**字串桶名**，窗長**一律經判準指定的家（`window_minutes(kind)`）取得**，`resets_at` 由 `minutes` 導出，`horizon` 由 `quota_pace.horizon()` 導出。🔴 **禁止把窗長當軸的內在屬性注入**（見右欄第 ③ 臂）。🔴 **母體限定為兩個合取項（三審 A1 補第二項；缺任一即判準對 (4b) 的射程說謊：套了它才不會假紅，不套它就會假綠）**：(i) 每一條軸的 `window_minutes(kind)` 皆非 `None`；(ii) **基底集合自己的 gate 聚合成員集合（`gate_list`）非空**（射程＝§4.2.2-b (4b)） | `rec(S ∪ {x}) ≤ rec(S)` **逐組成立**（違反組數 == 0） | ①把 L2 判準退回「窗長 < max(本次讀數窗長)」⇒ **違反組數必須 > 0** ⇒ 轉紅；②退回跨軸 max ⇒ 違反組數必須 > 0 ⇒ 轉紅（本輪封閉面實測 3640）；③🔴 **把窗長改成注入值（軸 ＝ `(band, window, minutes)`）⇒ 本條必須立刻失去對第 ④ 臂的鑑別力**，這一臂是**對判準自己的紅綠自證**：一審承接輪的探針正是那個注入面，於是它對 `windows()` 當家的缺陷全盲而回 0；④🔴 **本版改為比較式斷言（三審 QA：原「> 0」那一寫法在這一臂零鑑別力）**：判準的家改成 `quota_pace.windows()` ⇒ **在同一個擴大母體（含 `window_minutes(kind) is None` 的桶名 `session`／`spend`）上，windows-home 的違反組數必須嚴格大於 hybrid-home 的違反組數**〔本輪實測 **2796 > 2036**，mode=L2abs、同一取樣面、母體 109,800〕；改回 `windows()` 之後兩者相等 ⇒ 轉紅。**為什麼原寫法不行**：封閉面上三個 home **建構上等價**（實測逐格相同）⇒ 換家與不換家的綠面完全一樣；而擴大母體上 windows(2796) 與 hybrid(2036) **皆 > 0** ⇒ 「> 0」對「家被換掉」全盲。🔴 **並訂正原括號引述的「1972」**：那個數是「**把 L2 整條拿掉、只留 L1**」那一列（§0.3.2），不是換家的證據，本版不再引用它支撐這一臂；⑤🔴 **母體把 (ii) 那個合取項拿掉（允許 `gate_list` 起初為空）⇒ 違反組數必須 > 0**〔本輪實測 **0 → 7515**（`L1`）／**0 → 8691**（`L2abs`），母體 109,800、窗長皆解得出〕——這一臂是三審 A1 的機械物，且它證明 (4b) 的兩個合取項**都**在承重。🔴 判準只斷言「== 0 ／ > 0 ／ A > B」三種形態，**不寫 3640／2796／2036／7515／8691 任何一個數**（同 P8 的理由：取樣面與出廠值一動就變）。🔴 這一條與 P8 量的**不是同一件事**：P8 量「換聚合律前後」，P16 量「同一份讀數加一條軸」 |
| **P17** | **L2 的判準只讀該軸自己的桶名，不讀當次讀數**（B15／B16 ＋ 二審 N1 的正面） | 對同一組軸讀數，(a) 逐一改變「其他軸有哪些」（**含加入一條與某軸同 `resets_at`、但桶名文法解得出更長窗的軸**）；(b) 把 `ratio` 由有值改成 `None`；(c) 🔴 **鄰軸本版換成會翻面的那一種（三審 QA）**：一條 `window_minutes(kind) is None` 的軸（`spend`，剩 504 分），在 **(c1) 無鄰軸** ／ **(c2) 有一條同 `resets_at`、且桶名文法解得出「短於地板」之窗的鄰軸（`five_hour`，300 分）** 兩種情形下 | 每一軸的 **L2 適用性分類**逐格不變（含 (c1)／(c2) 兩種情形下 `spend` 都判「不適用」） | ①判準改讀 `max(當次讀數窗長)` ⇒ (a) 轉紅；②判準改寄生 `quota_pace.amortize()` 的 rate／total 選取 ⇒ (b) 轉紅（`amortize(ratio=None)` 回 `None` ⇒ 分類整批消失）＋ 中間窗長軸（例：1440 分窗）拿不到分類 ⇒ 轉紅；③🔴 **判準改讀 `quota_pace.windows()` ⇒ (c2) 必須轉紅**〔本輪實測逐字：`windows(spend 單獨) = (None,)` ⇒ 不適用；`windows(spend + five_hour 同 reset) = (300.0, 300.0)` ⇒ **300 < 地板 10080 ⇒ 由「不適用」翻成「適用」**；而採用的家 `window_minutes('spend') = None` 在兩種情形下**皆**回「不適用」〕⇒ 這一臂真的會翻面。**附帶好處**：同一組實測顯示該軸的 `horizon` 在 (c1)／(c2) 皆為 `far`〔`horizon(504, None)=far`／`horizon(504, 300.0)=far`〕⇒ 這一臂**只**量 L2 的分類，不與通道 B 的 horizon 效應糾纏。🔴 **原具名案例（`spend` ＋ `monthly_all`）本版撤回、理由記在這裡**：`windows()` 回 43200，而 43200 **≥** 地板 ⇒ 兩個家**都**判「不適用」⇒ 那個注入下本臂**恆綠**（雖然它的 horizon 由 far 翻 near，但那是通道 B、不是 L2 的分類，本條量不到）。⇒ (c) 那一格是 N1 的機械物 |
| **P18** | **`V_safe` 除數面的方向不變式（二審 N2 的機械物；沒有它，拆出來的第二個鍵就是「換了名字沒人守」）** | (a) `V_FLOOR_MINUTES` 出廠值下，`T_rem` 掃過 `[0, 3·V_FLOOR]`，比對 `V_safe` 與**原文 `max(T_MIN_MINUTES=2, T_rem)`** 的值；(b) `AUTOSDD_QUOTA_VSAFE_FLOOR_MINUTES` 由出廠值往上調一格與往下調一格；(c) 把 `AUTOSDD_QUOTA_WRAP_MINUTES` 由 5 調到 30 | (a) **逐點相等**（出廠只換名字不換值）；(b) 往上調 ⇒ `V_safe` **單調不變大**；往下調到 < 2 ⇒ **載入期即拒絕**（下界不變式）；(c) 🔴 **`V_safe` 逐點不變**（兩個鍵已解耦） | ①把 `V_FLOOR_MINUTES` 出廠值改成 5 ⇒ (a) 轉紅（證明 (a) 真的在比對原文值，不是恆綠）；②拿掉下界不變式 ⇒ (b) 的第二臂轉紅；③🔴 **把兩個鍵併回同一個（一審承接輪的形態）⇒ (c) 必須轉紅**——這一臂就是 N2 的機械物：合併之後把收尾帶由 5 升到 30 會讓 `V_safe` 的除數下限乘 6 |

🔴 **P8／P10／P16／P17 四條刻意用「窮舉」而非挑幾個樣本**：本批三個修法都改的是**聚合律**，挑樣本的判準對聚合律結構上失明——這正是 `DEF-200-171`（純缺席型判準）與 R75「閘門自己沒鑑別力」那一族要防的東西。
🔴 **本節新／改判準（P3／P8／P9／P16／P17／P18）的共同紀律**：**判準只斷言方向、結構與非空，不凍任何一個出廠值導出的數**。一審把「數字被凍進判準」點名兩次（P8 的 60、§6.7 的 15/4），一審承接輪逐處拔除；二審在 P16 再加一格 —— 連 `645`／`2670` 這兩個**一審承接輪自己算出來的**數也不得進判準（它們的注入面已被判為繞過判準之家，見 P16 第 ③ 臂）。
🔴 **這條紀律有一個具名例外，必須在這裡劃界（三審 Architect A8），否則 P18 讀起來像自己違反本節末段**：**P18 (a) 臂裡的字面 `2` 不是出廠值導出量，是史料常數**——它是**被廢除的原條文本身**的字面（PRD `:732` 逐字 `T_MIN_MINUTES = 2.0`，`:451`／`:453` 兩個消費端），而 (a) 要斷言的正是「出廠只換名字不換值」⇒ **比較對象必須是那個史料字面**，換成「現查 `V_FLOOR_MINUTES` 的出廠值」會讓 (a) 變成 `x == x` 的恆等式（＝零鑑別力，而且是本節反覆在防的那一種）。判準的分界因此是：**凍「被判準所判的那一側」的出廠值＝禁止**（那個值一動判準就假紅）；**凍「原條文的史料字面」＝必要**（它是一個已經停止演化的常數，且它的家在 PRD 而不在 `.env`）。同一句劃界也適用 P18 (b) 第二臂的下界 `< 2`。
🔴 **P16／P17 的注入面本身就是一條教訓，寫在這裡免得下輪重踩**：判準要驗「某個值從哪裡來」時，**那個值不能是注入參數**——一審承接輪把窗長注入進去，於是「窗長從哪裡來」整件事落在判準射程外，`L2abs` 必然回 0。**判準的注入面必須停在判準指定之家的上游**（本例：注入 `kind`，讓判準自己去呼叫 `window_minutes()`）。

---

## 8. 誠實劃界

1. **本設計翻不動 `DEF-200-199` 帳本記載的 A 案那個 4**（§4.4）。三層修法全上仍是 4，且要翻它就得碰週軸在無證據時的 ×0.5＝帳本已否決方向的實質等價物。⇒ 升為裁決項，不擅自決定。**🔴 B19 承接：這個殘留差異在驗收面改記為 known-and-accepted**——§7 P9 已由「兩次 rec 相等」改成結構斷言，不再把 Q3 的裁決當已通過前提；若 Q3 裁定 (a) 不在否決射程內，A 案會翻成 8，屆時是**判準之外的改善**，不是 P9 由紅轉綠。
   - **1-b（一審承接新增；🔴 二審 SA non-blocking 訂正兩處）：帳本 `:205` 點名的「PRD §4.2 那張表」，本批不處置**。帳本 `:205` 的處置欄逐字「🔴 **修憲級**（PRD §4.2 那張表），非調常數」〔帳本實讀〕。
     - 🔴 **訂正 ①：§4.2 實有三張表，不是兩張。** 一審承接輪寫「只有兩張——(i) §4.2.3 的〈致動器〉表（`:478-486`）、(ii) v2.1.8 §4.2.4 的〈運算元對照〉表（`:519-524`）」，漏了 **(iii) §4.2.4 的〈判決依據〉表（`:508-511`）**〔實讀〕——兩列量測（`SMALL_WOBBLE_REVERSALS=0`／`AVAILABILITY_FLIPS=19`），它就住在 (ii) 的**上方 11 行、同一節內**。⇒ 候選由 2 張變 3 張；本批對 (iii) 亦**不處置**（它是 watermark 遲滯的立案量測，與本批三個根因無交集）。
     - 🔴 **訂正 ②：時序推斷的前提是錯的，該推斷本版整句撤回。** 一審承接輪寫「立案當時 (ii) 尚未存在於 PRD ⇒ 依時序推斷應為 (i)」。實查兩個日期〔皆實讀〕：**v2.1.8 修訂日期＝2026-08-22**（PRD 修訂表 `:13`，(ii) 是 v2.1.8 §4.2.4 引入的），**`DEF-200-199` 立案日期＝2026-08-23**（帳本 `:205` 第二欄）⇒ **(ii) 在立案當天已經存在（早一天）**。原推斷的方向剛好相反。⇒ 「應為 (i)」這個推斷失去依據，本版不改用另一個推斷替代它（那會是同一個錯的第二次）：**三張表哪一張都有可能，缺陷結案時必須由掌舵者指定**。
     - ⇒ 本批的處置不變：**(ii) 有處置**（§6.1-pre：`C_target` 一格對兩個實作量，改為指向新的 §4.2.2-c）；**(i)／(iii) 不處置**。缺陷結案時若掌舵者認定指的是 (i) 或 (iii)，該項需另開一輪，不由本批冒領。
2. **(a) thrifty floor 對週軸有實質射程**（`anchor_margin_pp(10080) = 0.5952pp`〔本輪實測〕，週軸落後約 0.6pp 即算節儉）。它是不是「重走被否決的方向」是一個**判斷**，本文件給論證（逐軸／有證據／地板只到中性）但不自行結案。**🔴 一審 Architect 加了一個本文件沒想到的事實**：那個門檻**低於讀數的量化階 1pp** ⇒ 在週軸上**沒有鑑別力**（等於「沒超前就放行」）⇒ 「有該軸自己的證據」這條辯護在長窗上是空的。裁決包與可解除路徑見 §10.1。
3. **L2／L3 的射程今天量不到**。燃燒落款 `row_of()` 只落 `ts/pct/live/fp`〔現查碼〕；本機實測 17 列、8 個 kind、**零列帶 `resets_at`**〔探針〕⇒ 「一年裡有多少比例的決策會被 L2／L3 改到」在事後**結構上不可查**。⇒ `DEF-200-200` ④ 是本批的前置量測，不是可選的順手項。
4. **本輪零生產流量驗證**。所有數字來自合成輸入餵純函式。真實 payload 的軸組合、`resets_at` 的分佈、`weekly_scoped` 的 `scope_model` 命中率，本文件一個都沒有量（刻意：打端點會製造 `DEF-200-216` 那類自造事故）。
5. **`DEF-200-198` 的 15 個取樣點本輪未複驗**（帳本 `:204` 自標「他包回報，未複驗」）。本文件複驗的是**值域**（可窮舉、與樣本無關），不是那 15 個點。**🔴 B11 承接：本輪複驗的是那 15 個點的「落格算術」而不是點本身**——§3.1 訂正為 14/15，依據是帳本自己那一列的文字（第 15 點＝複審探針打出的 429），不是重新取樣。
6. ~~**M197-2 的 (i) 分支未逐行複驗**~~ ⇒ **一審承接輪已複驗並訂正**（SD→修憲）：函式名誤植（真名 `refresh_quota_blocking`，`quota_gate.py:597`），且寫入端**不只一個**——`refresh_quota_blocking` `:621-625` 與 `pace_state` `:705-707` 兩處皆由 `reading is (not) None` 守著。
   🔴 **二審 SD-N6 訂正該筆訂正本身**：一審承接輪接著寫的「今天 429 真的進到快取的是**後者**那條路」是錯的——`rate_limited_reading()` 回**完整 dict**〔現查碼 `quota_meter.py:730-738`〕⇒ `refresh_quota_blocking` `:622` 的 `reading is None` 判 False、`:625` 的 `write_cache` 照樣執行，且該讀數自己的 docstring `:721`／`:724` 就寫著「唯一的呼叫端 `quota_gate.refresh_quota_blocking()`……本讀數會被寫進快取」。⇒ **今天兩條路都寫快取**；`pace_state` 那一條的獨特之處是**燃燒落款污染**（`record_burn()` 唯一呼叫點在 `pace_report()` `:731`），不是快取寫入。原句把「唯一的落款污染路徑」誤寫成「唯一的快取寫入路徑」，並因此與 M197-2 (i)「兩個寫入端」自相矛盾。詳見 §2.3 M197-2 (i) 的第三個 bullet。
   🔴 **附帶登記（本批不改 code）**：`quota_meter.py:721` 的「唯一的呼叫端」是一句**過期的 docstring**（`measure_detail` 現查 4 個生產呼叫點，§1 表已列）⇒ 列為 **W1 的順手訂正項**（§9）。它今天不造成任何行為錯誤，但它正是讓一審承接輪把射程寫反的那句話。
   - **6-b（一審承接新增）：`quota_floor_reading()`（transcript 地板）的 E2 同型性靠呼叫圖恰好沒接上，不是靠判準擋住**（QA→修憲）：它建構的 `QuotaState` 同樣 `account_key is None` 且 `usable()` 為真 ⇒ 會走 `core_signature()` `:321-325` 那條退化路；今天不會污染燃燒落款，只因為它唯一的呼叫點 `quota_gate()` `:873` 不呼叫 `record_burn()`〔現查碼〕。**任何一輪把地板接進 `pace_report()` 這條路，污染立即出現**，而外觀與今天相同。⇒ 記為 `DEF-200-197` 的結案前置**觀察項**（§2.5 表 E2 格），本批不修。
   - **6-c（一審承接新增）：`W_TOTAL_FLOOR_MINUTES = 10080` 這個出廠值本身沒有燃燒證據支撐**。它由「窗長階梯上唯一有語意的分界」導出（§4.2 L2），而那個論證是**設計論證不是量測**：本 repo 沒有任何一份資料回答「週窗真的不該被 L2 放寬嗎」。誠實的說法是：地板卡在週是**保守側的選擇**（週軸是通篇要保護的那一個），而 env 鍵只准調小（更嚴）就是為了讓這個選擇的錯誤方向可控。
7. **仍然靜默的失效**：①(b) 階段 B1 只出聲不決策 ⇒ 若引擎側契約檔一直沒人寫，六條件永遠 fail-closed，而外觀與「條件真的不成立」相同——這正是 R-4.2.5-1 要求「說出是哪一個輸入不可得」的理由，但**那句話沒人查會不會被讀**；②`T_wrap` 出廠取 5 分鐘時，(c) 在立案情境（剩 6 分）**不觸發** ⇒ 落地後若只跑立案情境會誤判為「沒生效」；③~~本文件對 `quota_gate.quota_floor_reading()` 只做了存在性確認~~ ⇒ **本輪已逐行查完並逐項回答 E1/E2/E3**（§2.5 表；E1 不同型、E2 部分同型見 6-b、E3 同型且已併入本批射程）。
8. **PRD §11.2「重置後不暴衝」今天就不成立**（`_cap_for(BAND_FREE, *)` 四格皆 `None`）。本批不修也不惡化，但發現了就記在這裡；建議另立缺陷列。**🔴 B12 承接：爆炸半徑比原記重一級**——它同時讓 PRD v2.1.9 `:549-555` 替 §11.2 (c) 承重的那句「已經由別條管」不成立（§3.6），故本批增加一格最小處置（§6.9：加訂正註記、標「待承重」），不是純粹「記在這裡」。
9. **今天的跨軸 max 本身就違反 §4.2.2-b (4)**〔本輪實測：109,800 個加軸對取樣中 **9156** 個讓 rec 變大；封閉面 56,448 個中 3640 個〕。這是重跑方向不變式時的**射程外附帶發現**：它不改變本批任何修法的方向（L1 正是把它其中一條通道轉綠的那一步），但它意味著「加一條軸讓建議派工數變多」在**今天的生產上就會發生**。⇒ 建議在 `DEF-200-199` 結案時把這件事寫成該列的一句實測補注（不另立新列——它就是 R1 錯位的同一個機制的另一面）。
10. **本輪重跑的探針是「聚合律模型」不是 `decide()` 本體**。§0.3／§4.3 的三個 mode × 三個 home 用的是把 `_base_rec`／`_mult`／`_base_cap`／`_bound`／`_clamp`／`quota_pace.horizon`／`window_minutes`／`windows`（全部是生產純函式）重新組裝的 `rec(axes, mode, home)`，而不是打補丁跑真的 `decide()`——因為 L1／L2 還沒有實作，`decide()` 裡沒有那兩條路可以呼叫。⇒ **實作包落地後必須用真 `decide()` 重導 §0.3 與 §4.3 兩張表**，本輪的數字只保證「聚合律這樣寫會得到這些值」，不保證「實作寫完之後就是這些值」。這與 §7 P16／P17 的判準是同一件事的兩面。
    - 🔴 **模型與 production 的已知偏差一格，明列**：本探針用 `quota_pace.horizon()`（純門檻）導 horizon，而 production 用 `effective_horizon()`（門檻 ＋ `burn_step` 燃燒證據 ＋「無證據不得比絕對門檻鬆」夾層）。原因是探針的 `band` 是**直接注入**的、沒有對應的 `pct`，而 `burn_step` 需要 `pct`。⇒ 本輪的違反數是**同一個聚合律在較簡模型下的量級**，不是 production 的實際次數；方向（哪一個 home 為 0、哪一個不為 0）不受此影響，因為 `effective_horizon()` 對每一軸的作用只依賴該軸自己的 `(pct, minutes, window)`。🔴 **這一句本輪拿到了獨立佐證**：三審 Architect 自己接上 `effective_horizon()` 那一半重跑，**違反數不受影響、方向宣稱成立**〔他包回報，本輪未重跑該半〕⇒ 照實記，本輪不把它寫成自己量過的。
    - 🔴 **第二格已知偏差（三審 A1 指出，本版補記）：§0.3.2 與 §4.3 兩張表的探針省略了 `decide()` 的 `gate` 那一段**（`gate_list = [...]`／`gate = gate_list or readings`，`quota_policy.py:634-635`〔現查碼〕）。這不是無害的簡化——它正好把 §6.1 (4b) 的**通道 C** 整條藏起來：本輪把 gate 接上之後，**窗長皆解得出**的面上 `L1` 由 0 變 **7515**、`L2abs` 由 0 變 **8691**（母體 109,800），定向兩例逐字 **4 → 16**（見 §0.3.3 第 6 件）。⇒ **誠實劃界：§0.3.2／§4.3 兩張表本版未重製**（它們仍是 gate 面關閉下的值，且四情境 A/A2/B/C 的軸集合本來就不含 FALLBACK／模型分軌軸 ⇒ 那四格在 gate 開關下同值）；gate 面的量級一律引 §0.3.3 第 6 件那一組，不得從 §0.3.2 推算。
11. 🔴 **`windows()` 的鄰軸繼承是 §4.2.2-b (4) 的第二個、獨立於聚合律的違反源（＝(4b) 的通道 B；二審 N1 的機械後果，本批不修、具名登記）**。〔本輪實測〕把 L2 整個拿掉、只留 L1，含解不出窗長桶名的 109,800 個加軸對中仍有 **1972** 個讓 rec 變大；把 L2 加回來（家＝`window_minutes(kind)`）是 **2036**；封閉面（窗長皆由文法解得出）則兩者皆 **0**。首例逐字：`spend` 剩 504 分在無鄰軸時窗長 `None` ⇒ 走絕對門檻（30／360）⇒ `far` ×0.5；加一條同 `resets_at` 的 `weekly_all` 之後繼承 10080 ⇒ 走相對門檻（`near=1008`）⇒ `near` ×2.0 ⇒ rec 4→16。
    - **它為什麼是獨立的**：`resolve()` `:392`〔現查碼〕逐字 `wins = windows(...)`，而那個 `wins` 同時餵給 `band_inputs()` 與 `effective_horizon()` ⇒ 繼承影響的是**horizon**，不是 L2 的分類。⇒ 換 L2 的家關不掉它，這是本批**做不到**的事，不是本批漏做的事。
    - **為什麼本批不修**：取消繼承的方向**不是單向的**——同一次實測裡它在 `spend`(504 分) 上是**收緊**（near→far），在 `session`(283 分) 上是**放寬**（far→mid）。⇒ 「取消繼承」既不是純收緊也不是純放寬，而 `windows()` 自己的檔頭 `:138-142`〔現查碼〕逐字用「短窗會讓 near 門檻更小＝更不容易加速」替繼承辯護——那個辯護只覆蓋方向的一半。無證據不得裁決 ⇒ 升為 **§10 Q9**，並建議另立缺陷列。
    - **它同時是 A2 那一格的成因**：見 §4.3 表的 `hybrid` 列與 §10 Q9。
12. 🔴 **gate 聚合面是 §4.2.2-b (4) 的第三條違反通道（＝(4b) 的通道 C；三審 Architect A1 指出，本輪逐例實測坐實，本批不修、具名登記）**。〔本輪實測〕`gate_list` 由空翻非空的那一刻，`FALLBACK_KINDS`／未命中的 `MODEL_SCOPED_KINDS` 那些煞車軸**整批離開 C_cap／C_target 的聚合面** ⇒ rec 變大：定向兩例 **4 → 16**（gate 面關閉時同兩例為 4 → 4）；窗長皆解得出的面上 `L1` **0 → 7515**、`L2abs` **0 → 8691**（母體 109,800）。
    - **它為什麼獨立於通道 B**：兩例的四個桶名（`seven_day_overage_included`／`weekly_scoped`／`seven_day_opus`／`five_hour`）的窗長**全部由文法解得出**〔`window_minutes` 逐字回 10080／10080／10080／300〕⇒ 繼承一次都沒有發生，違反卻照樣出現。⇒ 換 L2 的家、甚至取消繼承，都關不掉它。
    - **為什麼本批不修**：`gate = gate_list or readings` 這個 fail-safe 的**兩個理由都是憲法級裁決**——R89（保險池不得一票否決主力，掌舵者原話「付費額度是一個保險，你把它當成主要，本末倒置」）與 R98（不得用一個沒在用的模型的水位節流主力），而它的 `or readings` 那一半自己的註解逐字寫「寧可退回舊行為（全部參與、可能過度保守），也不要讓 `min()` 對空序列拋例外而讓整條額度軸消失」〔現查碼 `quota_policy.py:630-633`〕。⇒ 動它＝同時動兩次憲法裁決 ＋ 一個明文的 fail-safe，**無證據不得裁決**，升為 §10 **Q9 (iv)** 的鄰居並建議另立缺陷列。
    - **對本批條文的直接後果**：§6.1 (4b) 的合取項由一條變兩條、§7 P16 的母體限定同步加一條（**不加就會兩面都錯**：套了 gate 面卻不限定母體 ⇒ 落地當天假紅；限定了母體卻不寫進條文 ⇒ (4) 仍是一句假的全稱宣稱）。

---

## 9. 落地排程建議（依賴順序與分包）

| 批 | 內容 | 依賴 | 可否分包 | 建議承接輪 | effort |
| :-- | :---- | :---- | :---- | :---- | :---- |
| **W0** | `DEF-200-200` ④：`row_of()` 落 `resets_at` | 無 | ✅ 可單包 | **R108 同輪**（它是 W2／W3 的量測前提） | S |
| **W1** | `DEF-200-198` M198-1 ＋ M198-2 ＋ 🔴 **順手訂正兩句過期 docstring**（皆只改註解、零行為）：① `quota_meter.py:721` 的「唯一的呼叫端 `quota_gate.refresh_quota_blocking()`」（現查 4 個生產呼叫點，二審 SD-N6 立案）；② `quota_policy.py:503-504` 的「本檔 tier 餘裕個位數」（現值 261/400，見本節下方） | 無 | ✅ 可單包 | R108～R109 | S |
| **W2** | `DEF-200-197` M197-1~4（含 M197-4 的 **6 落點跨 2 檔管線**＋`measure_detail` 元組加寬） | 無（但與 W0 同動 `quota_meter`／`quota_gate`，建議同窗） | ⚠️ 與 W0 同窗較省；🔴 **M197-1 與 M197-4 不得分包**（M197-1 單獨落地＝把一句真話換成一句假話） | R109 | **M**（B13 承接後由 S 升 M） |
| **W2.5** | 🔴 **淨減法輪（新增，SD→修憲）**：護欄層行數淨額 ≤ 0，兌現 `_REPIN_NET_CAP_DUE_ROUND=109` 到期義務 | W1／W2 落地後才知道真實淨增量 | ❌ **只能由收尾單人窗口做**（鐵律七同型結論：淨減法禁止並行） | **R109 同輪、W3 之前** | M |
| **W3** | `DEF-200-199` **L1 ＋ L2 同窗** ＋ (a)＝L3 | W0（量測面）；W2.5（棘輪餘裕）；四方對 §10 Q2/Q3/**Q8**/🔴 **Q9** 的裁決 | ⚠️ **「L1 與 L2 不得分包」的理由在 Q9 之後要重判**：原理由是「L1 單獨落地會讓 A2 由 8 收緊到 4，L2 把它還原到 8」；而換家之後 L2 對 `session` 軸不適用 ⇒ **A2 在 L1+L2 之下也是 4**〔本輪實測 §4.3 hybrid 列〕⇒ 該理由**不再成立**。🔴 **不得因此改判為「可分包」**：分包判準要另找理由（候選＝兩者共動 `decide()` 同一段建構順序、且 P8／P16 兩條判準的母體重疊），或由 Q9 的裁決一併指定。**在 Q9 裁決之前 W3 維持不可分包**（fail-safe：分錯包的代價是兩個半套的聚合律同時在線）。🔴 若 Q3 裁定 (a) 不在否決射程內，(a) 可脫離本批回復「S 級可先行單包」（§5.1） | R109～R110 | L |
| **W4** | (b) 階段 B1（`bursting_ok` 只出聲 ＋ 六條件輸入落款） | W0 | ✅ 可單包 | R110 | S |
| **W5** | (c) `T_wrap = FANOUT_WINDOW_SECONDS/60` 版 | W3（同動 `decide()` 的建構順序） | ⚠️ 建議隨 W3 | R110 | M |
| **W6** | (b) 階段 B2（`pace_near` 條件制）＋ (c) 升到 30 分 ＋ 引擎反向契約 | W4 的樣本 ＋ §10 Q4 裁決 ＋ 引擎側改動 | ❌ 三件必須同窗（`near` 帶的矛盾需要裁決者同時在場） | ≥ R111 | L |

🔴 **鐵律七檢查（鎖的持有面）**：本批要動的機械鎖，其**常數／史料／消費端**分佈——

- `Policy` 欄位（常數）住 `quota_policy.py`；`ENV_SPEC`（消費端之一）住 `quota_policy_env.py`；`.env.example`（生成物）由前者產生；回歸鎖住 `tools/tests/test_quota_policy.py`。⇒ **W1／W3 的新 env 鍵必須由同一個包同窗處理這四處**，不得拆給並行包。
- PRD 文本（史料）住 `docs/01_requirements/`；PRD ↔ 實作的後設鎖（`PrdDrainPercentMapsToTheBandsTest._PAIRS` 一族）住 `tools/tests/`。⇒ **修憲落款與後設鎖必須同窗**，否則落款當天後設鎖轉紅。
- 🔴 **第三個持有面（一審 SD 補上，本輪現查坐實）＝護欄層行數棘輪**：常數住 `tools/tests/test_adr_xplat001_c1c2_lock.py`（`_REPIN_NET_CAP_SCHEDULE` `:1206-1231`／`_REPIN_NET_CAP_DUE_ROUND = 109` `:1318`／`_REPIN_NET_CAP_DUE_TARGET = 610` `:1319`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` `:1237`）〔現查碼〕；史料是各輪的重釘紀錄（同檔的排程列，最後一列 `(107, 630)` `:1231`）；消費端是 `repin_growth_problems()`。**三者同檔 ⇒ 這一面本身不跨包，但它會咬住 W0~W6 每一批**。
  - **W0~W6 是七批，而 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 允許連兩輪上升、第三輪必須淨額 ≤ 0**；且 R109 另有 `_REPIN_NET_CAP_DUE_ROUND = 109`／`_REPIN_NET_CAP_DUE_TARGET = 610` 的到期義務（現行上限 630，`:1231`）⇒ **七批序列若一路上升，第三批就會被棘輪擋住**。
  - ⇒ **§9 新增 W2.5 一格**：在 W2 與 W3 之間插一輪淨減法（兼兌現 R109 到期義務）。這不是額外工作，是把一件無論如何都要在 R109 做的事排進本表——不排進來，W3 會在動工當天撞牆。
- 🔴 **本批生產檔的 LOC 餘裕充足，與 `ADR-XPLAT-014` 的落點情況相反，值得明說**（SD→修憲）〔本輪實測 `python AutoClaude/tools/check_loc_budget.py --json`〕：`tools/lib/quota_policy.py` **assertion=261**（`guardrail_lib` tier 上限 400）／`quota_pace.py` 319／`quota_gate.py` 391／`quota_meter.py` 315／`quota_messages.py` 108。⇒ **W1~W6 不需要「先抽共用模組」的前置格**（`ADR-XPLAT-014` 的落點 `tools/session_resume_planner.py` 同一次量測是 **749/750、headroom=1**，那一份才要先拆）。
  - 🔴 順帶訂正一句已過期的自陳：`quota_policy.py:503-504`〔現查碼〕逐字「本檔 tier 餘裕個位數」，而同一支檔的同檔頭 `:18-21` 早已寫明「它們是 R82 立案當時的量測值，不是常數……一律現查」——**`:503-504` 那句是漏改的第二處**（現值 261/400，餘裕 139 行）。W1／W3 動到該檔時順手訂正該註解（不刪，改成「現查」＋指向 `:18-21` 的判詞）。
- ⇒ 結論：**W1～W6 沒有任何一批可以派給並行包**（每一批都同時碰常數與消費端）；**W2.5 更是只能由收尾單人窗口做**（淨減法的 git 操作限制）。全部走收尾單人窗口，或走「一輪一批、序列」。

---

## 10. 待裁決問題清單（給四方 ＋ 掌舵者）

| # | 問題 | 本文件的建議 | 誰裁 |
| :-- | :---- | :---- | :---- |
| **Q1** | `KNOWN_KINDS` 要不要收進 repo 自造的 kind？ | **不收**，另立 `SYNTHETIC_KINDS` ＋ 專屬 note 字面（§2.5） | 四方；採 M197-1 後不阻塞 197 |
| **Q2** | 同軸聚合（L1）是否推翻 R84／SA-01 當年的判決？ | **不推翻，是承接**：那個判決的前提（「weekly 幾乎恆為 far」）已被 R86 的相對化證偽（`thresholds(10080)=(1008,5040)`） | 四方 |
| **Q3** | 🔴 **(a) thrifty floor ＋ L2 對週軸的放寬，是否落在帳本 `:205`「不得動 `pace_far`」的否決射程內？** 若是，`DEF-200-199` 的 A 案（4%／283 分 → rec 4）就**在憲法上不可修**，該列應改記為「已知且接受的行為」而非缺陷 | 本文件**不自行結案**。論證見 §4.4／§8-1、-2；一審四鏡的獨立意見已整合進 **§10.1**（含量級與「可解除否決的路徑」），裁決請直接在 §10.1 的三個選項上拍板 | **掌舵者 ＋ 四方** |
| **Q4** | `ENABLE_BURSTING` 出廠值 | **`true`**。出廠 `false` ＋ ×2 條件制 ＝ B2 落地當天靜默關掉錨點①。🔴 **一審承接輪順帶查到直接證據**：標的 PRD §4.2.6 參考實作 `:766-769` 逐字已寫 `enable_bursting: bool = True`（連同 `burst_window_minutes: float = 30.0`／`burst_max_u5h: float = 60.0`／`burst_weekly_guard: float = 60.0`）〔實讀〕⇒ **出廠 `true` 不是本提案的新主張，是 PRD 現行條文本來就有的值**，Q4 實質上只需要確認「實作端沿用 PRD 的出廠值」，不是一個開放選擇 | 掌舵者（錨點① 是他的原話） |
| **Q5** | `T_WRAP_MINUTES`（must-finish 門檻）出廠取 5 分（`FANOUT_WINDOW_SECONDS/60`）還是 30 分（`accel_window_minutes`）？🔴 **本題的射程已由二審 N2 收窄**：`V_safe` 的除數下限已拆成自己的鍵 `V_FLOOR_MINUTES`（出廠 2，史料出處＝PRD `:732`）⇒ **本題只動 must-finish 門檻，不再連帶動除數下限**（拆鍵前會乘 6，見 §5.3.4） | 先 **5 分**（保守、可先行、不與錨點① 打架），30 分留給 W6 與 (b) 同窗 | 四方 |
| **Q6** | 🔴 **改寫（B12）**：PRD §11.2「重置後不暴衝」今天就不成立（free 帶 cap 恆 `None`）。**已知的新事實**：v2.1.9 `:549-555` 正拿這條「別條管」替 §4.2.4 (c) 不立第三個機制承重，而該承重理由因此**不成立**（§3.6）。⇒ 兩問：**(i)** free 帶那一格另立缺陷列還是併入本批？**(ii)** §4.2.4 (c) 要不要真的立第三個機制，還是等 (i) 落地後恢復由「別條管」承重？ | **(i) 另立缺陷列**（與本批三筆根因不同，併進來會製造 `DEF-200-213` 型併列，Playbook §6 第 4 條要禁的）。**(ii) 等 (i)**，本批只在 §6.9 加訂正註記把該結論標為「待承重」，不擅自替 (c) 立機制 | 四方 |
| **Q7** | 🔴 **改寫（B18）**：不是「用哪個版號」，而是 **v2.1.9 待再審期間，本批能否落款？先決條件為何？** | 見 **§10.2** 的逐條依賴清單與三個選項 | **掌舵者 ＋ 四方**（原欄寫「收尾窗口」是把一個治理決策當成編號作業） |
| **Q8** | 🔴 **新增（B15／B16 承接）**：L2 的絕對地板 `W_TOTAL_FLOOR_MINUTES` 出廠值取「一週的分鐘數」是否成立？env 鍵的方向不變式取「只准調小」是否成立？ | **兩者皆成立**。地板卡在週＝保守側選擇（週軸是通篇要保護的那一個）；只准調小＝唯一不會製造無證據放寬的方向。🔴 但**這個出廠值沒有燃燒證據支撐**，是設計論證（§8-6c 已誠實劃界）；🔴 二審 N7 另加一格：**地板恰等於週窗，週軸落在安全側只差一個嚴格不等號**（§6.5 已明記，§7 P10 第 ③ 臂已補判準）⇒ 需要一次明示核准，不能靠「沒人反對」通過 | 四方 |
| **Q9** | 🔴 **新增（二審 Architect N1 的下游；本批唯一的 contested 項）**：L2 判準的家改成 `window_minutes(kind)` 之後，**`window_minutes` 解不出的桶名（`session`／`spend`／`nimbus_quill`／`weekly_scoped`）永遠落在「不適用」**。而 `session` 與 `five_hour` 是**同一條底層限制被回報兩次**〔現查碼 `quota_pace.py:138-142`〕⇒ `rec = min(逐軸)` 讓沒被還原的 `session` 勝出 ⇒ **L2 在本 repo 最重要的那一對軸上被中和，A2 由 8 掉回 4**〔本輪實測 §4.3〕。同一組實測另證：`windows()` 的鄰軸繼承是 §4.2.2-b (4) 的**第二條獨立通道**（§8-11）。⇒ 三問：**(i)** 接受 A2＝4（L2 只治 `five_hour` 那一格）？**(ii)** 改為「逐軸窗長整體都由該軸桶名的純函式決定」（取消 `windows()` 繼承）——A2 回到 8，🔴 **但原欄那半句「那樣 (4) 真的歸零」本版撤回**（三審 Architect A1 的 gate 通道實測證偽：窗長皆解得出、繼承一次都沒發生的面上，`L1` 仍有 **7515** 個違反、`L2abs` **8691**〔本輪實測，母體 109,800〕）；且取消繼承的方向**不是單向的**（實測 `spend` 收緊、`session` 放寬）？**(iii)** 讓 L2 的家在解不出時**沿用同 reset 鄰軸的分類**（即回到 `windows()`，但只用於分類）——那會把 N1 指出的集合依賴原樣帶回來？**(iv)** 🔴 **新增候選（三審 Architect A1 提出）**：**在餵給聚合律之前，先按 `resets_at` 去重、每組只留一個「最嚴代表」，再套 grammar-home 的 L2**。它的立案依據是 `windows()` 自己的註解〔現查碼 `quota_pace.py:138-142` 逐字〕——`session` 與 `five_hour` 的 `resets_at` 逐字相同（微秒都一樣）「⇒ 它們是**同一條底層限制被回報兩次**」。若這句自陳為真，那麼 Q9 (i) 那個「L2 被 `session` 中和」的損失**本來就不該存在**（`min()` 對同一條限制的兩份回報取兩次，是重複計數而不是保守）。🔴 **(iv) 本輪未實測**（既沒量它會把 A2／四情境改成什麼，也沒量「同 `resets_at` 但真的是兩條不同限制」時的誤合併率——`windows()` 同一段註解自己就寫著「相同的**結束時刻**不等於相同的**窗長**」）⇒ **本版只登記候選與依據，不給量級、不給傾向**。 | 🔴 **本文件不自行結案。** 傾向 **(i) ＋ 另立缺陷列**：(i) 是四個候選中唯一**不引入新的無證據方向**的選項（L2 少治一格是保守側；(ii) 在 `session` 那一格是放寬、(iii) 是把二審剛擋下的缺陷放回去、**(iv) 本輪未實測 ⇒ 依「無量測不得比較」的既有紀律，本版不把它放進傾向的比較面**——它是一個**待量測的候選**，不是一個被否決的選項）。代價要明說：接受 (i) 等於承認 **L2 對 `session`／`five_hour` 這一對軸的淨效果是 0**，而那正是 `DEF-200-199` 立案情境的那一對 ⇒ §9 W3 的「L1 與 L2 不得分包」理由（L2 把 A2 還原到 8）在 (i) 之下**不再成立**，W3 的分包判準需重寫。**(ii) 應另立缺陷列**（`windows()` 繼承的方向未經證據裁決），不由本批冒領。🔴 **(4) 的第三條通道（gate 聚合面，§8-12）應另立第二列**：它動到 R89／R98 兩次憲法裁決與一個明文 fail-safe，射程與 (ii) 不同，併成一列會製造 `DEF-200-213` 型併列 | **掌舵者 ＋ 四方** |

### 10.1 Q3 裁決包 —— R108 一審 Architect／QA 獨立意見整合

> 以下逐條轉述 `docs/06_quality/CrossPlatform_R108_Review.md`〈Q3（最重裁決項）獨立意見彙整〉（`:73-77`）〔實讀〕。**兩鏡的數字皆為他鏡當回合實測，本輪未重跑，照原樣標注**〔他包回報〕；本輪重跑的只有 `anchor_margin_pp` 那兩格。

**(1) Architect 的判定：(a) 對週軸那一半「在否決射程內」——但否決**可解除**。**

- 理由〔他包回報〕：`anchor_margin_pp(10080) = 0.595pp`【本輪重跑確認 **0.5952**】**低於讀數的量化階 1pp** ⇒ 門檻對週軸**沒有鑑別力**，實質等於「只要沒超前就放行」。也就是說 (a) 在週軸上不是「憑該軸自己的燃燒證據收回懲罰」，而是「幾乎無條件收回懲罰」——那正是帳本 `:205` 否決的方向的實質等價物。
- 量級〔他包回報〕：17,069 格均勻網格實測 **12.1%** 由 `far` 翻 `mid`。
- 連帶發現〔他包回報〕：A 案的**鄰居**會翻（週軸 40%→39% 使 rec 4→8）⇒ **「1pp 的讀數變化讓扇出加倍」本身就該進帳本**。
- 🔴 **可解除否決的路徑（Architect 明示，三條辯護即補齊）**：給 thrifty floor **自己的證據門檻**，使它在長窗上恢復鑑別力。兩個具體形態：
  - (α) **連續 N 筆節儉落款**才准施加地板（把「一次讀數」換成「一段趨勢」）；或
  - (β) 門檻改為 `max(anchor_margin_pp(window), k × 讀數量化階)`，**且 `k` 入憲**（k 是新常數，必須有家、有方向不變式、有紅綠自證）。
- Architect 對帳本的建議〔他包回報〕：帳本 `:205` 改記 A 案＝**known-and-accepted**；**另立一列**記「thrifty 門檻在長窗上低於輸入量化階」。

**(2) QA 的量化：(a) 的實際射程＝ far 區的 24.4%。**

- 〔他包回報〕均勻網格 **2066/8484 格**＝ **24.4%**（far 區內的比例）；FAR 覆蓋率由 **62.7% → 50.6%**。
- 🔴 QA 自標的性質：這是**上界**（均勻網格的性質），**不是機率**——真實讀數不是均勻分佈在網格上，所以 24.4% 是「最壞情況下有多少格會被改到」，不是「有 24.4% 的決策會被改到」。兩者不得互換引用。
- 與 Architect 的 12.1% **不衝突**：分母不同（Architect 的 12.1% 是全網格 17,069 格的比例，QA 的 24.4% 是 far 區 8,484 格的比例）。**兩個數字不得相加、不得互相校驗**。

**(3) L2 的部分：Architect 判「不在否決射程內」，但另有 B14/B15/B16 三筆 blocking。**

- ⇒ 一審結論：**(a) 與 L2 皆不應在本批原樣落款**。本版已把 L2 的三筆 blocking 修掉（§4.2 L2、§6.5 R-4.2.8-1b、§7 P10/P16/P17）⇒ **L2 這一半本版主張可以落款**；**(a) 這一半仍然待裁決**（本節就是那份裁決包）。

**⇒ 請掌舵者／四方在以下三個選項上拍板（本文件不自行結案）：**

| 選項 | 內容 | 後果 |
| :---- | :---- | :---- |
| **A** | (a) 落在否決射程內 ⇒ **本批撤下 (a)＝L3** | `DEF-200-199` 的 A 案改記 known-and-accepted（§8-1 已預先改成這個姿態）；W3 只剩 L1+L2；另立一列記「thrifty 門檻在長窗上低於輸入量化階」（Architect 建議） |
| **B** | (a) 不在否決射程內 ⇒ **本批原樣保留 (a)** | (a) 回復「S 級可先行單包」、脫離 W3（§5.1）；但 Architect 指出的「門檻在長窗上無鑑別力」仍是真的 ⇒ 必須另立一列記它，否則本輪等於明知而不記 |
| **C** | **補齊三條辯護再落款**（Architect 的可解除路徑 (α) 或 (β)） | (a) 的 effort 由 S 升 M（新常數 `k` 或「連續 N 筆」的狀態面，兩者都要有家＋方向鎖＋紅綠自證）；本批 (a) 延到 W3 之後的獨立 gated 項；A 案在裁決前維持 known-and-accepted |

🔴 **本文件的傾向（僅供參考，不算裁決）**：**選 C**。理由是它同時滿足帳本 `:205` 的兩個要求（修好反向／不鬆掉週軸）而不需要在兩者之間選一個，且 Architect 已把路徑寫得夠具體（(β) 只多一個入憲常數）。選 A 的代價是 `DEF-200-199` 永久記為 known-and-accepted；選 B 的代價是明知門檻無鑑別力仍落款。

### 10.2 Q7 的逐條依賴清單（B18 承接）—— 本批依賴哪些**尚未生效**的修憲

修訂表現查〔實讀 PRD `:9-14`〕：**只有 v2.1.4 標「已生效」**（`:9`，R107 四方複審通過）。其餘：v2.1.5「待四方複審後生效」／v2.1.6「規格化後待實作」／v2.1.7「經本輪落地並回歸鎖驗證通過」／v2.1.8「僅完成規格化，實作由後續階段接手」／v2.1.9「經獨立複審 **REJECT** 承接、逐條修訂後**待再審**」（`:14`，最後一列）。

🔴 **v2.1.7 那一列的歸類要統一（三審 QA：本節與 §10.3 原本各暗示一種）**：PRD `:12` 的狀態欄逐字只有「**經本輪落地並回歸鎖驗證通過**」〔實讀〕——它**既沒有**「已生效」那三個字（那個字面全表只出現在 `:9` 的 v2.1.4），**也沒有**「待四方複審」／「待再審」／「待實作」任何一種待審措辭。⇒ **本文件兩節一律照這句逐字引述、不替它歸類**（歸成「已生效」是替四方複審背書、歸成「未生效」是與該列逐字不符）；下文凡出現「未生效」的計數，母體皆為**明文標待審／待實作的那四列**（v2.1.5／v2.1.6／v2.1.8／v2.1.9），v2.1.7 不進該計數也不進「已生效」計數。這一格的最終歸類是落款包要問掌舵者的事，不由本文件裁定。

| 本批的哪一處 | 依賴哪一版的哪一條 | 該版狀態 | 這個依賴是「引用」還是「承重」 |
| :---- | :---- | :---- | :---- |
| §6.2 改後文本「與 §4.1.5『禁止靜默鎖死、C_cap ≥ 1』直接衝突」 | **v2.1.8** §4.1.5 | 僅完成規格化 | 🔴 **承重**——廢除原文 `C=0` 的唯一理由 |
| §6.4 `R-4.2.5-3`「同 §4.2.4 對 watermark 遲滯的判決」 | **v2.1.8** §4.2.4 | 僅完成規格化 | 🔴 **承重**——「無樣本不得把常數化行為改成條件制」的判例來源 |
| §6.6 改後文本「上界不變式見 §4.1.5」 | **v2.1.8** §4.1.5 | 僅完成規格化 | 引用（該不變式在實作面已由 `decide()` `:614` 落地〔現查碼〕⇒ 即使 v2.1.8 未生效，實作面仍成立） |
| §7 P15「保護 PRD §4.1.5 F3」 | **v2.1.8** §4.1.5（F3 於 **v2.1.9** minor 訂正） | 前者僅規格化、後者待再審 | 🔴 **承重**——判準的期望值直接取自該條 |
| §6.9 訂正的標的 | **v2.1.9** `:549-555` | 待再審 | 🔴 **承重**（訂正的對象就是它） |
| §3.6／§10 Q6 的立案 | **v2.1.9** `:549-555` ＋ §11.2 (c) | 待再審 | 🔴 **承重** |
| §6.1-pre 的 `_PAIRS` 對映判例 | **v2.1.9** minor（`TELEMETRY_UNMEASURED_CAP` ↔ `AUTOSDD_QUOTA_DEGRADED_CAP`） | 待再審 | 引用（判例形態，非數值） |
| §6.1-pre 訂正的 `C_target` 一格對兩個量 | **v2.1.8** §4.2.4 `:519-524` 的〈運算元對照〉表 | 僅完成規格化 | 🔴 **承重**（要改的就是它） |
| §6.6 紅線 1 的「豁免四條件」 | **v2.1.4** | ✅ **已生效** | 引用（唯一一個依賴已生效版本的前提） |

**⇒ 三個選項，請裁決：**

| 選項 | 內容 | 代價 |
| :---- | :---- | :---- |
| **①** | **等 v2.1.9 完成再審再落款 v2.1.10** | 本批全部延後；但 v2.1.9 是 REJECT 承接稿，它自己還沒過 ⇒ 疊上去的風險最低 |
| **②** | **v2.1.10 與 v2.1.9 的再審合併成同一次四方複審** | 一次審兩版、範圍變大；但上表 6 個「承重」依賴一次解決，且避免「v2.1.9 再審時又改動本批承重的條文」這個必然要重做的迴圈 |
| **③** | **v2.1.10 先落款，狀態欄具名寫出前置未成立** | 落款當天修訂表就有兩列「待再審」相疊；本批任何一個「承重」依賴在 v2.1.9 再審時被改動，v2.1.10 就要跟著改 ⇒ 這是把返工排進未來，不是消除它 |

🔴 **本文件的傾向（僅供參考）**：**選 ②**。上表 6 個承重依賴全部指向 v2.1.8/v2.1.9 的同一批條文（§4.1.5／§4.2.4／§11.2），分兩次審會讓同一批條文被審兩次而且第二次可能推翻第一次。**明確反對選 ③**：header 的狀態欄照 B18 要求具名寫出前置是**誠實揭露**，不是**解決**——揭露之後那個依賴照樣是假的。

### 10.3 🔴 `ADR-XPLAT-014` §3.5 Q4 那批 PRD 修訂的版號歸屬與審次序（二審 Architect N5 承接）

一審承接輪把 `ADR-XPLAT-014` 當成「次要關聯」而沒有處理一件治理事實：**那份 ADR 的 §3.5 Q4 也在提 PRD 修訂**（現查該 ADR 為 ⑤ 處：① `:1100` `--max-turns` 不存在＋`:2590` B-10 自相矛盾／② `:1843`＋`:1053` `RESET_BUFFER_SECONDS` vs `RESET_SKEW_SECONDS` 兩個家／③ `:1099` `--allowed-tools` 刻意不帶／④ `:1088`＋`:1849` `RESUME_MAX_TRANSCRIPT_TOKENS` 單位不符（登記不處置）／⑤ `:2589` B-09 把 `default` 列為權限模式並標 ✅ 而本機 CLI 無此格）。**兩份文件都要動同一支 PRD，而誰用哪個版號、誰先審，沒有任何一份寫下來。**

| 問題 | 本文件的主張 | 為什麼 |
| :---- | :---- | :---- |
| **版號歸屬** | 🔴 **ADR-XPLAT-014 的 Q4 那批不得併進 v2.1.10。** 它們另起一個版號（建議 **v2.1.11**），由該 ADR 的落款包負責 | 兩批的**射程與裁決者都不同**：v2.1.10 全部落在 §4.2／§8-1（配速與 429，裁決者是四方 ＋ 掌舵者對 Q3）；ADR-014 的 Q4 全部落在 §4.5.4／§9／附錄 B（喚醒指令與 CLI 旗標，裁決者是掌舵者對授權面）。併成一版 ⇒ 一次複審要同時判兩件無關的事，而 R75 已判過「合併不相干射程的批次會讓複審沒有停損線」 |
| **審次序** | 🔴 **v2.1.10 先、v2.1.11 後，且兩者之間無承重依賴**（本輪逐條核對：§10.2 那 9 個依賴一格都不指向 §4.5.4／§9／附錄 B） | 次序可以定，正是**因為**沒有依賴。若哪一天出現交集（例：某輪要同時動 §9 指標區），改為同批並在該批的狀態欄具名寫出 |
| **共用的一格風險** | 🔴 **修訂表是共享資源**：v2.1.10 與 v2.1.11 都要在 PRD `:9-14` 那張表加一列，而該表現況已有**四列明文標待審／待實作**（v2.1.5／v2.1.6／v2.1.8／v2.1.9；🔴 **v2.1.7 不在此計數內、也不算已生效**——它的措辭是 PRD `:12` 逐字「經本輪落地並回歸鎖驗證通過」，本文件對它不作歸類，判準與理由的唯一出處＝**§10.2**）。⇒ **落款包必須先確認 v2.1.9 的再審結果**，否則會出現「五列待審相疊」 | 這是 §10.2 選項 ③ 的代價在**跨文件**面的同一個形態：疊得越高，任何一列被改動時要跟著改的列越多 |
| **本批要做的動作** | 在 `ADR-XPLAT-014` §3.5 Q4 開頭加一句「本批 PRD 修訂的落款版號＝v2.1.11，與 `PRD_Amendment_R108_Pacing`（v2.1.10）**不同批**、次序在後、兩批無承重依賴」——**一句話，寫在 ADR 側不寫在 PRD 側**（PRD 是治理面，本批不動它） | 兩份設計文件各自說出同一件事會製造兩個家；規則是「誰的 Q4 誰記」，本節只負責主張與理由 |

---

## 附註：本文件自身的體例聲明

- 本文件**沒有**引用任何本輪未跑過的閘門輸出，也**沒有**宣稱任何測試通過（提案輪、一審承接輪、二審承接輪、三審承接輪皆一支測試都沒跑——這是架構輪）。
- 所有「實測」二字後面的數字，來源皆為 §0.1 表列**五**類之一，且逐處標記。
- 帳本引用一律標行號；他包回報且本輪未複驗者，沿用帳本自己的標注（`〔他包回報，未複驗〕`）。
- 🔴 **二審承接輪（本版）自己的誠實劃界**：
  1. 本版新增的量化宣稱**全部**標〔本輪實測〕並附探針輸出逐字（§0.3.2／§4.3／§6.2 的常數史料）。兩個例外，皆逐處標記：① **§10.1 轉述 Architect／QA 的數字**（12.1%／17,069 格／24.4%／2066/8484 格／62.7%→50.6%）＝他鏡當回合實測、未重跑〔他包回報〕；② 二審 Architect 給的 **3446／6334**（windows-home 下 L1／L2abs 的違反數）——本輪**用自己的取樣重跑得 1972／2796**。🔴 **兩組數字不得互相校驗、不得相減**（取樣面不同：本輪為 5 個 kind × 3 個 minutes × 4 個 band、母體 109,800）；**方向一致**（windows-home 皆 > 0、grammar-home 皆 == 0**（此 0 的射程＝gate 面關閉，見下一格）**），而方向才是判準要斷言的東西（§7 P16 的紀律）。③ 🔴 **三審 Architect 給的 1979**（grammar-home ＋ gate 面開啟下的 `L1` 違反數）——本輪同一方向自己重跑得 **2247**（開放面 109,800）。**兩組同樣不得互相校驗、不得相減**（gate 模型的射程可能不同：本輪同時排除 `FALLBACK_KINDS` 與未命中的 `MODEL_SCOPED_KINDS`）；**方向一致**（gate 關 0、gate 開 > 0）。本輪自己量到的另兩格（窗長皆解得出的面上 `L1` 0 → **7515**／`L2abs` 0 → **8691**、定向兩例 4 → 16、加合取項後回 0）皆為〔本輪實測〕，不與他鏡的數混用。
  2. 本版**沒有跑任何閘門、沒有動任何 `.py`／測試／帳本／PRD／既有 ADR 條文**：被編輯的檔案只有**五份工作樹新檔**——本文件、`docs/04_planning/ADR-XPLAT-013_Phase2_Proposal_R108.md`、`docs/04_planning/ADR/ADR-XPLAT-014-resume-chain-hardening.md`、`docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md`、`docs/06_quality/CrossPlatform_R108_Sentinel_Forensics.md`；探針住 scratchpad、只呼叫生產純函式，零網路、零寫入生產面。
  3. 本版對二審 7 筆 blocking **全部照修**；一審 B9~B19 十一筆的承接維持不變（其中 B9 那一筆的處置由「留一個常數」改為「拆成兩個鍵」，理由＝二審 N2）。**唯一的 contested 是 Architect N1 的一個半句**：「換家」照修（判詞成立、反例本輪逐字複現），但「換完 §4.2.2-b (4) 就歸零」**未照抄**——本輪實測換家後殘留 2036、把 L2 整個拿掉仍殘留 1972 ⇒ 殘留主體是 `windows()` 繼承經由 horizon 的獨立通道（§8-11）。本版的處置是收窄 (4) 的射程（§6.1 (4b)）＋ 收窄 P16 的可綠面 ＋ 新增 §10 **Q9**，而不是宣稱一個做不到的 0。
  4. **本版改動了一個已公布的數字，具名交出**：§4.3 的 **A2 在 `L1+L2abs` 由 8 變 4**（production 語意 ＝ `hybrid` home）。一審承接輪寫的「改判準沒有偷偷改動任何一個已經公布的數字」本版撤回；連帶 §9 W3 的分包理由也失去依據（該格已改為「Q9 裁決前維持不可分包」）。
  5. §7 P16／P17／P18 三條新／改判準**本輪只有設計、沒有測試碼**（架構輪紀律）。P16／P17 的紅面**已由本輪的探針實跑過**（windows-home 的 1972／2796、`windows(spend 單獨) = (None,)` vs 加同 reset 鄰軸後的 `(43200.0, 43200.0)`、封閉面的 0）⇒ 判準不是「寫起來應該會紅」，是「本輪真的看到它紅了」。**P18 的紅面本輪未跑**（除數面在 `tools/lib/` 尚不存在，只有 PRD 條文）⇒ 這一格誠實標為「設計時未見紅」。
     - 🔴 **這句「已實跑」對其中兩臂本來是假的，三審 QA 抓到，本版逐臂劃界（三審承接輪重跑，值皆〔本輪實測〕）**：**P16 第 ④ 臂**——二審那一版寫的是「> 0」，而擴大母體上 windows(2796) 與 hybrid(2036) **皆 > 0**、封閉面上三個 home **建構上等價**（皆 0）⇒ 那個寫法對「家被換掉」**在任何一個面上都紅不起來**，二審的「已實跑」只跑到了數字、沒跑到鑑別力。本版改成比較式斷言（**2796 > 2036**，同一取樣面）之後才真的有紅面，另補第 ⑤ 臂（gate 母體合取項，**0 → 7515／0 → 8691**）並訂正原括號誤引的「1972」。**P17 第 ③ 臂**——二審具名的注入（`spend` ＋ `monthly_all`）在兩個家下**都**判「不適用」（43200 ≥ 地板 10080）⇒ **恆綠**；本版換成 `spend` ＋ `five_hour`（同 `resets_at`）之後 `windows()` 繼承出 **300 < 10080**、分類由「不適用」翻「適用」，紅面才成立。⇒ **兩臂的「本輪真的看到它紅了」只對本版（三審承接輪）的寫法成立，對二審那一版不成立**，此處不沿用那句話替舊寫法背書。
  6. **一審承接輪的一項探針結論被本版判為無鑑別力**：`L2abs` 在 32800 個加軸對中違反數 0 —— 那個 0 來自「窗長被手填成軸的內在屬性」的注入面，對 `windows()` 當家的缺陷結構上失明。本版在 §0.3.1 說明它為什麼失明，並**不再引用它（含 `L2rel` 的 645）作為任何結論的依據**。
