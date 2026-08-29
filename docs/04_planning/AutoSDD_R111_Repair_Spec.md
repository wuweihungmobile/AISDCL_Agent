# `R111` 單人窗口修復輪規格（W1 唯讀偵察交件）

> **效力聲明**：本檔數字皆 `R110` 量測值（HEAD `292a8bb` 前的樹）；`R111` 執行時
> **逐項現查重驗，不得引用為常數**（帳本行號、`_FROZEN_GUARD_LINES` 現值、假紅筆數、
> 存量債筆數尤其會漂移）。裁決依據＝`AutoSDD_Adjudication_Record_R110.md`（掌舵者
> 2026-08-29 的 27 題方向裁決；本檔 §1b 191 的上呈建議、209 的 U5 前置定位皆以該檔
> 為準）。
> **命名說明**：檔名刻意不匹配 `R*_HANDOFF` glob——本檔是修復規格不是交棒書，不進
> 「最新交棒書」鎖族的掃描面。
> **暫存腳本蒸發風險**：下方兩支偵察腳本住 session 暫存目錄（重開機／換 session 即
> 消失）；查無檔時依 §1 各節「本回合假紅實測」段內嵌的量測邏輯重建（129/195＝以
> 修改後判準函式對真帳本重跑、轉紅數為輸出；瘦身掃描＝連續 `#` 註解塊 ≥8 行＋史料
> 訊號＋排除豁免標記）。

- **輪次定位**：R111＝護欄層判準修補（Mac）。硬約束＝`tools/tests/`（guard 量測面，非遞迴 `*.py`）**淨額必須 ≤ 0**——重釘稽核痕跡 R108＝+190、R109＝+153 已連續上升 2 輪（`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`），本輪正淨額當場觸發款(11) `[只升不降]`。
- **另一硬到期**：`_REPIN_NET_CAP_DUE_ROUND = 111`（`tools/tests/test_adr_xplat001_c1c2_lock.py:1365`）——本輪只要追加任何 R111 稽核列，款(12) 立刻要求現行 cap 降到 `≤ 595`。⇒ 本輪**必然**要兌現到期義務（見 §3 連鎖）。
- **並行邊界**：結案包正在改 `docs/06_quality/` 帳本與 Playbook。本規格中所有「帳本列拆分／回執／改派」動作屬結案包持有面；129 上鎖等帳本收斂後同窗執行（見 129 節）。
- 偵察量測腳本（可重跑）：
  - `/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/1f557657-6285-4ea1-ae46-3653a9ac5b7c/scratchpad/measure_129_195.py`（129/195 假紅實測）
  - `/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/1f557657-6285-4ea1-ae46-3653a9ac5b7c/scratchpad/scan_lore_blocks.py`（瘦身候選掃描）

---

## §1 逐筆修復規格（quick 六筆＝核心；191/195/217 同族附後）

### DEF-200-116　pace 契約 headroom 混入保險軸

**① 帳本列全文**（`docs/06_quality/AutoSDD_Defect_Log.md:162`）：
> |DEF-200-116|2026-08-14|R89 Architect 複審 B-1（實測 live 快取）|`pace_contract` 的 `headroom_pct` 取 `max(全部軸 pct)`，而 `band`／`cap` 自 R89 起由**非保險軸**導出 ⇒ 同一份 payload 同時對引擎說「還可派 8 個」與「餘裕 0.0」。實測 `band=converge cap=8 binding=five_hour(72%)` 而 `headroom_pct=0.0`，依契約應為 23.0|P2|未修。二選一：`headroom` 改讀 gate（建議），或重新定義該欄並同步兩處 docstring。🔴 R89 收尾依 QA N-7 由 P1 降 P2：全 `autoclaude/` 無邏輯讀該欄（只有 docstring 與測試 fixture）⇒ 潛在契約假話，非活躍誤動作|open（承接輪次：**R95**）→承接R101|

**② Playbook 出口設計逐字**（`docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md:361`）：
> headroom 改讀 gate 面；同步引擎側 docstring 與鏡射鎖

**③ 目標代碼現況**：
- `tools/lib/pace_contract.py:72-73`（病灶本體）：
  ```python
  headroom = (None if not decision.per_axis else
              max(0.0, float(halt_pct) - max(r.axis.pct for r in decision.per_axis)))
  ```
  `decision.per_axis` 含保險軸（`spend`/`extra_usage`，`quota_policy.FALLBACK_KINDS`）；而 `decide()` 的 `binding`/`cap` 取自 `gate_list`（`quota_policy.py:634-644`，保險軸被 `_in_cap_gate()` 排除）。
- `tools/lib/pace_contract.py:61` docstring：「`headroom_pct`＝halt 水位 − 最緊那軸的水位」——「最緊那軸」語意含混，正是兩讀法分歧點。
- 引擎側 docstring：`AutoClaude/autoclaude/core/ports/quota_meter.py:194`：「headroom_pct float|null —— 本窗還能燒多少（halt 水位 − 最緊那軸的水位）」。
- 鏡射鎖：`tools/lib/quota_criteria.py:300 contract_literal_problems()` **只比對** `PACE_CACHE_NAME`/`PACE_SCHEMA` 兩個字面，headroom 語意不在鎖內；`tools/tests/test_quota_policy.py:1784-1804 TestR86ThePaceContractWriterMatchesTheEngineReader` 只斷言鍵存在。⇒ 修復不會撞既有鎖。

**④ 修復規格**：
1. `tools/lib/pace_contract.py`：`headroom` 改讀 gate 面的 binding 軸：
   ```python
   headroom = (None if decision.binding is None else
               max(0.0, float(halt_pct) - float(decision.binding.pct)))
   ```
   同步 `:61-66` docstring：「halt 水位 − **binding（gate 面）軸**的水位；保險軸（`FALLBACK_KINDS`）刻意不進本欄，與 `band`/`cap` 同一取樣面（DEF-200-116）」。邊界確認：unmeasured（`binding=None, per_axis=()`）→ None 不變；halt 帶 binding 100% → `max(0,…)`＝0.0，非負契約保持。
2. `AutoClaude/autoclaude/core/ports/quota_meter.py:194` docstring 同句改寫（「最緊那軸」→「binding（gate 面）軸；保險軸不進」）。⚠ 觸碰 AutoClaude 樹：pre-commit 整檔 ruff 適用（記憶條款），該檔須整檔乾淨。
3. 紅綠自證（落 `tools/tests/test_quota_policy.py`，緊鄰 TestR86 類）：注入 gate 軸 72% ＋ 保險軸（`spend`）100%、halt=95 → 斷言 `payload(...)["headroom_pct"] == 23.0`（舊實作回 0.0＝紅側重演，可用行內註記記載當回合實跑值）。**斷言值域而非 docstring 字串**——這就是「鏡射鎖」的實質補法：值域鎖比字面鎖強。
4. 事前驗證步：`grep -rn "headroom_pct" AutoClaude/autoclaude/` 複驗 QA N-7「無邏輯讀該欄」仍成立（讀者只有 docstring/fixture 才可安全改語意）。

**預估淨行數**：`tools/tests/test_quota_policy.py` **+16**；`tools/lib/pace_contract.py` +2（guardrail_lib 400 預算，現 111 行，無虞）；AutoClaude port docstring ±0。
**重釘連鎖**：`_FROZEN_GUARD_LINES["test_quota_policy.py"]`（現值 3152）。

---

### DEF-200-121　DUE_ROUND 無防延期後設鎖

**① 帳本列全文**（`AutoSDD_Defect_Log.md:166`）：
> |DEF-200-121|2026-08-15|R89 收尾／QA 複審 N-3（注入實測）|`_REPIN_NET_CAP_DUE_ROUND`／`_DUE_TARGET`（`test_adr_xplat001_c1c2_lock.py`）**無 `_FROZEN_` 對應常數、不在 `repin_cost_ratchet_problems()` 任何判準內**：到期輪改 500 紅 0、改 9999 紅 0、到期目標 1600→1999 紅 0，而同檔逐字宣稱「刻意沒有『延期』參數」。與同檔的 F3／B-1（`_REPIN_ROUND_CAP_SINCE`）逐字同型：修了 SINCE，沒修 DUE_ROUND|P2|未修。方向：`DUE_ROUND` 只准調小，或上界綁 `live_round + K`。🔴 本輪那次續期實質正當（QA 複驗）⇒ **不要回退它**，只補鎖|open（承接輪次：**R95**）→承接R98→承接R101|

**② Playbook 出口設計逐字**（Playbook:363）：
> 加 due_round 上界判準＋紅綠；DUE=107 恰到期順勢兌現

⚠ Playbook 半句已 stale：現值 `DUE_ROUND=111`（107/109 已分別於 R107/R109 兌現並重新武裝）。「恰到期順勢兌現」的邏輯本輪仍成立——**R111 正是現行到期輪**。

**③ 目標代碼現況**（`tools/tests/test_adr_xplat001_c1c2_lock.py`）：
- `:1365-1366`：`_REPIN_NET_CAP_DUE_ROUND = 111`／`_REPIN_NET_CAP_DUE_TARGET = 595`。
- `:1687-1748 repin_cost_ratchet_problems()`：款(12) `[到期未下修]` 在 `:1729`（`live_round >= due_round and cap > due_target`）；`due_round`/`due_target` 是可注入參數，但**沒有任何判準看 due_round 自己**——改 9999 ⇒ `live_round >= due_round` 永假 ⇒ 款(12) 靜默熄滅（帳本注入實測紅 0）。
- 歷史步調（`_REPIN_NET_CAP_SCHEDULE:1251-1280`）：到期輪一律「上一次兌現輪 +2」——lookahead 常數 K=2 有實證母體（85→87→89→…→109→111 全部間隔 2）。
- repin log 現況：末列 R109、總量 89467；凍結前綴 `_REPIN_LOG_FROZEN_PREFIX_LEN = 80`（`:1426`）≒ 全表長度 ⇒「追加後立即自我凍結」體例（R101/R109 判例，rewrite ledger `:1455-1529`）。

**④ 修復規格**：
1. 新常數（緊鄰 `:1365`）：
   ```python
   _REPIN_DUE_ROUND_MAX_LOOKAHEAD = 2      # 到期輪距最近稽核輪的上界；歷史母體 85..111 全部 +2
   _FROZEN_REPIN_DUE_ROUND_MAX_LOOKAHEAD = 2
   ```
2. `repin_cost_ratchet_problems()` 增兩款（簽名加 `due_lookahead` 可注入參數，預設讀常數）：
   - `[到期日被推遲]`：`due_round > live_round + due_lookahead` 即紅（訊息載明：可延期的到期日不是到期日；出口＝兌現後才重新武裝下一段，且新 due 只能是「兌現輪＋lookahead」以內）。
   - lookahead 自身 shrink-only：`due_lookahead > frozen` 即紅（同 `_REPIN_ROUND_CAP_SINCE` 款式）。
   - 附帶補：`due_target >= cap` 時出聲（到期目標必須嚴格低於現行 cap，`:1364` 註解已宣告此紀律但零判準）——可選項，若行數緊繃可捨。
3. 紅綠自證（同檔測試區）：注入 `due_round=9999, latest_round=111` → 斷言含 `[到期日被推遲]`（＝帳本立案那把注入，改前紅 0、改後紅 1）；注入 `due_round=113, latest_round=111` → 綠。
4. **順勢兌現（本輪義務，與本筆同檔同窗）**：
   - `_REPIN_NET_CAP_SCHEDULE` 追加 `(111, 595)`（cap 610→595，步伐 15；兌現值貼齊到期目標＝R99/R101/R103 判例）。
   - 同輪重新武裝：`_REPIN_NET_CAP_DUE_ROUND = 113`、`_REPIN_NET_CAP_DUE_TARGET = 585`（步伐 10 < 前一段的 15，續守「步伐刻意變小」；113 = 111+2 通過新 lookahead 判準——**紅綠自證的活體對照**）。

**預估淨行數**：`test_adr_xplat001_c1c2_lock.py` 判準+常數 ≈ +18、紅綠測試 ≈ +14、schedule 列+重武裝註解 ≈ +5、本輪稽核列＋凍結前綴延伸＋rewrite ledger 追加 ≈ +8 ⇒ **+45**。
**重釘連鎖**：`_FROZEN_GUARD_LINES["test_adr_xplat001_c1c2_lock.py"]`（現值 6341）；`_REPIN_LOG_FROZEN_PREFIX_LEN` 80→81（或 +N=本輪稽核列數）；`_REPIN_LOG_HISTORY_SHA256` 以 `--print-guard-lines` 重印；`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 `("R111", <舊12>, <新12>, "DEF-200-121")`（DEF-ID 必須真的存在於帳本——121 現存，合格）。

---

### DEF-200-129　自列「改派」出口純布林（與 195 同刀口）

**① 帳本列全文**（`AutoSDD_Defect_Log.md:172`）：
> |DEF-200-129|2026-08-15|R90 帳本單人窗口（硬規則② 關鍵字出口存量普查）|硬規則② 的「改派」關鍵字出口存量**不是個位數**：當回合普查未結列中走該出口者共 **49** 筆，其中 **28 筆早在 R89 之前就已靜默過期**（承接輪號分佈 R79:9／R82:11／R83:7／R85:1）⇒ 交棒書 §5a 把「收緊這條出口」列為另案時所據的量級失實。普查腳本與逐筆見 CrossPlatform_R89_Closure_Evidence.md §DEF-200-129|P2|收緊＝自列「改派」也須指名 ≥ 當前輪的輪號（跨列回執那一半 R84 已做）；上線前先量假紅|open（承接輪次：**R95**）→改派承接R98→改派承接R101

**② Playbook 出口設計逐字**（Playbook:367）：
> 自列出口加輪號下限；🔴 須與批次結案同窗上鎖防大片假紅

**③ 目標代碼現況**（`tools/check_defect_log_crossref.py`）：
- 自列出口＝`orphan_backlog_problems()` 的 `:558-559`：
  ```python
  if _reassign_hit(cells[status_idx]):
      continue
  ```
  純布林——狀態欄命中「改派」即永久免驗，不比輪號。
- 對照組（R84 已修的跨列那一半）＝`:561-570`：跨列回執須 `_ROUND_RE` 取狀態欄最大輪號 ≥ 當前輪，或含 `_UNASSIGNED_LITERAL`（=`"未指派"`，`:614`）。
- **本回合假紅實測**（measure_129_195.py，帳本 HEAD、cur=R100）：未結列 62；走自列出口 26 筆；上鎖（含 @R 前綴排除）後轉紅 **14 筆**——`DEF-101-018/060/398/796/856/863/867/887/938/951/960/974/980/981`（狀態欄最大輪號 79~91）。⚠ 結案包把帳本「發現情境」推到 R111 後 cur 上跳，轉紅數會**再擴大**（26 筆中狀態欄輪號 <111 者全紅）——**上線前必須以結案後帳本重量一次**。

**④ 修復規格**：
1. `tools/check_defect_log_crossref.py` 抽一支共用取值函式（129 與 195 同一個知識家）：
   ```python
   def _receipt_rounds(status_cell: str) -> list[int]:
       """狀態欄裡的輪號，排除 `@R<n>` 時點標籤（fixed@R100 的 @R100 是時點不是承接者）。"""
       return [int(m.group(1)) for m in _ROUND_RE.finditer(status_cell)
               if not (m.start() > 0 and status_cell[m.start() - 1] == "@")]
   ```
2. 自列出口 `:558-559` 改為與跨列同構：
   ```python
   if _reassign_hit(cells[status_idx]) and (
           _UNASSIGNED_LITERAL in cells[status_idx]
           or max(_receipt_rounds(cells[status_idx]), default=-1) >= (cur if cur is not None else -1)):
       continue
   ```
   訊息側：孤兒訊息已載明兩條合法出口，免改。
3. 跨列出口 `:568` 的 `max(...)` 改走 `_receipt_rounds()`（＝195 的修復本體，見 195 節）。
4. 紅綠自證（`tools/tests/test_check_defect_log_crossref.py`）：合成帳本 2×2——自列狀態欄 (a)`改派 **R<cur>**`→綠 (b)`改派 R<cur-2>`→紅 (c)`改派＋未指派`→綠 (d)`fixed@R<cur> 改派 R<cur-2>` 首詞不得自滿→紅。
5. **同窗紀律（Playbook 紅字）**：上鎖 commit 必須排在結案包帳本收斂**之後**；落地前重跑 measure_129_195.py（改為 import 修改後函式直接跑真帳本），**轉紅數必須＝0** 才接進閘門——殘餘轉紅列由帳本側以「改派 ≥`R112`」回執或「未指派＋解鎖條件」清零（帳本編輯屬結案包持有面；若同窗只剩單人，由單人窗口以 append-only 回執清）。⚠ 每列回執受 `ROW_MAX_BYTES=700` 限制（DEF-200-194 判例：頂線列走跨列回執）。

**預估淨行數**：`check_defect_log_crossref.py` ≈ +10/−4（helper +6、自列出口改寫 +4、跨列 :568 換 helper −4+2）——⚠ 該檔是 `check_loc_budget.SPECIAL_FILES` 棘輪（`../tools/check_defect_log_crossref.py: 1479`，計價=assertion 行），改動後現查 `python AutoClaude/tools/check_loc_budget.py --json`，若破線以同檔搬史料（`:428-465` 一帶 30+ 行沿革註解可搬）抵銷。`tools/tests/test_check_defect_log_crossref.py` **+30**（含 195 的 2×2）。
**重釘連鎖**：`_FROZEN_GUARD_LINES["test_check_defect_log_crossref.py"]`（現值 3722）。

---

### DEF-200-195　回執新鮮度被首詞 `fixed@R<當輪>` 自我滿足（129 的孿生，同窗一刀）

**① 帳本列全文**（`AutoSDD_Defect_Log.md:201`）：
> | DEF-200-195 | 2026-08-23 | R100 收尾（`DEF-200-194` 自證副產品） | **跨列回執新鮮度被狀態首詞 `fixed@R<當輪>` 自我滿足**：R84（`DEF-200-088`）要回執列狀態欄輪號 ≥ 當前輪，但取值是對整欄 `_ROUND_RE` 取**最大值**，首詞自帶輪號。當回合 2×2 注入（`check_defect_log_crossref.py:565-570`）：首詞帶 R100＋改派 R98 ⇒ 孤兒 **0**；首詞不帶輪號＋改派 R98 ⇒ 孤兒 **2** | P3 | 取數面應排除首詞 `@R<n>` 時點標籤（該檔 `_REASSIGN_RE` 註解已載明 `@Rnn` 是時點非承接者）。🔴 失效窗口一輪：cur 進 101 回紅 | open（承接輪次：**R101**）：本包唯讀護欄層未加鎖 |

**② Playbook 出口設計逐字**（Playbook:389）：
> max 取值排除 @ 前綴命中＋2×2 注入紅綠自證

**③ 目標代碼現況**：`tools/check_defect_log_crossref.py:566-570`（`max((int(x.group(1)) for x in _ROUND_RE.finditer(c[status_idx])), default=-1)`）；`_ROUND_RE`（`:446`）的否定回顧 `(?<![A-Za-z0-9])` 放行 `@` 前綴 ⇒ `fixed@R111` 的 `@R111` 進 max。`:460-462` 註解早已載明 `@Rnn` 是時點非承接者——判準沒跟上自己的註解。
**本回合假紅實測**：@R 排除後跨列出口失效轉紅＝**0 筆**（measure_129_195.py，帳本 HEAD）——今天上鎖零假紅，正是最便宜的窗口。

**④ 修復規格**：與 129 共用 `_receipt_rounds()`（見 129-④-1/3）；2×2 紅綠注入照帳本列載明的四象限寫進 `test_check_defect_log_crossref.py`（行數已計入 129 的 +30）。本筆即 DEF-200-213 的殘留②「為 195 補鎖」——結案時兩列各自引同一測試座標。

---

### DEF-200-209　`.claude/hooks/` 樹零 ruff 執行者

**① 帳本列全文**（`AutoSDD_Defect_Log.md:213`）：
> | DEF-200-209 | 2026-08-23 | R100 收尾窗口（護欄層 C3） | `ADR-XPLAT-012` 條文一殘留缺口 ⑥ 未處置：「多語句擠一行」除 `"";x = 1` 之外的形態無判準，且 `.claude/hooks/` ＋ `tools/` 面**沒有 ruff E701/E702 閘門**。亦即 ADR-XPLAT-013 §7 的解鎖條件 U5（見 DEF-200-207） | P2 | 淨加判準只能由收尾單人窗口做（鐵律七）；本輪窗口受 DEF-200-208 淨額死結阻擋而未做 | open（承接輪次：**R101**）：未開始。四方續報＝§E-2：第三道套利門 `exec(__doc__)` 200→1（−99.5%）；`S102` 抓得到，但兩份 ruff select 皆無 `S`、`.claude/hooks/` 零 ruff 閘門 |

**② Playbook 出口設計逐字**（Playbook:399）：
> ruff 射程擴到該樹（CI＋pre-push 兩執行者）；訂正過時半句

**③ 目標代碼現況**：
- 執行者現況：`tools/git-hooks/pre-push:403`＝`ruff check tools/ --no-cache`（快層④）；`.github/workflows/root-infra-ci.yml:443-447`＝第 16 道 `ruff check tools/`（ruff 鎖版 `0.15.21`）。兩者射程逐字只到 `tools/`。
- 設定：`tools/ruff.toml`（select=`E,F,I,UP,W`——E701/E702 在 `E` 內；檔頭 `:28-30` 自陳射程「只到根層護欄層本身」）。`.claude/` 樹上方無任何 ruff 設定 ⇒ 直接把路徑塞給執行者會套 ruff 出廠預設＝假綠（`tools/ruff.toml:6-12` 記載過同型病）。
- **存量債實測**（本回合，`ruff check .claude/hooks --config tools/ruff.toml`）：**16 errors**＝9×E501＋3×I001＋2×UP017＋2×UP031；分佈：`context_budget_guard.py` 8、`check_claim_provenance.py` 5、`lint_powershell_command.py` 2、`block_destructive_git.py` 1。E701/E702 現值 **0**。（⚠ `--config` 會挪 project root，此數字是估值；落地後以 `.claude/ruff.toml` 途徑複測。）
- 過時半句的家：(a) `docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md:190`（§6 缺口⑥：「…而 `.claude/hooks/`…沒有任何 ruff 閘門——…不涵蓋根層 `.claude/hooks/` **與 `tools/`**」）與 `:102`；(b) 帳本列本身的「＋ `tools/` 面」半句（Playbook:172 已診斷為過時：pre-push R69 起就跑 `ruff check tools/`）。帳本列屬 append-only——由結案回執載明訂正，不改原文。

**④ 修復規格**：
1. 新檔 `.claude/ruff.toml`（約 8 行）：`extend = "../tools/ruff.toml"` ＋ 檔頭兩行 WHY（ruff 就近尋找設定，`.claude/` 樹沒有這支就退回出廠預設＝假綠；per-file-ignores 兩條 pattern 對本樹無命中，extend 安全）。**先跑對照組**：`ruff check .claude/hooks/`（新設定就位後）與上面 16 筆估值比對，確認無 project-root 錯位。
2. 兩執行者擴射程：
   - `tools/git-hooks/pre-push:403`：`ruff check tools/ --no-cache` → `ruff check tools/ .claude/hooks/ --no-cache`（同段檔頭 `:373-375` 註解同步）。
   - `.github/workflows/root-infra-ci.yml`：第 16 道指令同樣加 `.claude/hooks/`；`:173` 檔頭清單與 `:219` job name 字串同步。
3. 存量債清零（上鎖前置，16 筆）：5 筆 `--fix` 自動（I001×3、UP017×2）；UP031×2 手改；E501×9 逐筆改寫——⚠ `context_budget_guard.py` 是 `SPECIAL_FILES` 棘輪（cap 1089，assertion 計價），**優先縮寫訊息字面，不硬換行**；換行淨增時以同檔史料搬遷抵銷並照棘輪雙邊咬人規則重釘。
4. 同步鎖擴面：`tools/tests/test_subprocess_encoding_hygiene.py::TestRootToolsLintPolicy` 增斷言——(a) `.claude/ruff.toml` 存在且 `extend` 指向 `tools/ruff.toml`（一份規則一個家）；(b) 兩執行者的指令字串含 `.claude/hooks/`（pre-push 與 workflow 各一向，防單邊退回）。
5. 訂正過時半句：ADR-XPLAT-013 `:190`/`:102` 以「R111 訂正」行內附註標明 tools/ 半句自 R69 起已有兩執行者（不重寫決策原文，比照 R69 訂正體例）；§7 U5 表列（`:208`）與 `ADR-XPLAT-013_Phase2_Proposal_R108.md:232` 的 U5 狀態隨落地改「已落地（E701/E702 隨 select E 生效）」。`S` 系列（S102）**本輪不加**——那是 217-E2 的軸，select 動一字兩樹連動（`tools/ruff.toml:35` 宣告與 AutoClaude 逐字同步、有鎖），越出 quick 射程。
6. 驗收：`ruff check tools/ .claude/hooks/ --no-cache` rc=0 逐字貼；pre-push 一次真跑貼 root-infra 快層④ 輸出。

**預估淨行數**：`tools/tests/test_subprocess_encoding_hygiene.py` **+12**；非 guard 面（`.claude/ruff.toml` +8、pre-push +2、workflow +2、hooks E501 改寫 +≈6、ADR 附註 +4）。
**重釘連鎖**：`_FROZEN_GUARD_LINES["test_subprocess_encoding_hygiene.py"]`（現值 1599）。

---

### DEF-200-212　handoff 閘門兩假綠

**① 帳本列全文**（`AutoSDD_Defect_Log.md:215`）：
> | DEF-200-212 | 2026-08-23 | R100 收尾窗口（護欄層 C6） | `tools/check_handoff_carriers.py` 兩個同族假綠：① 判準② 帳本側 `:173-190` `ledger_def_ids()` 無狀態過濾 ⇒ `fixed` 列 ID 即可滿足「有承接載體」，而它要證明的是有**未結**承接單位；② `:237-240` 載體面用 `_REPO_ROOT.glob()`（檔案系統）卻在 `:40`／`:294` 自稱 **tracked** ⇒ 未追蹤檔被計為 tracked（實證：本窗口未追蹤的 `R100_HANDOFF.md` 使普查 85 → 86 並通過驗證） | P3 | 取數面加 `UNRESOLVED_CLASSES` 過濾；需同步紅綠自證（改前該注入必綠） | open（承接輪次：**R101**）：未修 |

**② Playbook 出口設計逐字**（Playbook:401）：
> ①加 _UNRESOLVED_CLASSES 過濾②改 git ls-files 或訂正自稱

**③ 目標代碼現況**（`tools/check_handoff_carriers.py`，418 行）：
- `:172-190 ledger_def_ids()`：走 `_ROW_RE` 收集**全部**列 ID，無 `gate._classify(...) in gate._UNRESOLVED_CLASSES` 過濾（對照：同檔 `:165` 的 `unresolved_carrier_rounds()` 有過濾——同族兩函式一個有濾一個沒濾）。
- `:236-241 carrier_files()`：`_REPO_ROOT.glob(g)`＝檔案系統；docstring 自稱「tracked 交接載體」；`:294` census 亦印「tracked 交接載體＝N 份」。
- 紅綠載體：同檔內建 `--self-test`（`:61`、`_KNOWN_ARGV:113`、合成語料 `:313`）——**紅綠可全落本檔，不進 guard 面**。

**④ 修復規格**：
1. ①狀態過濾：`ledger_def_ids()` 在 `_ROW_RE` 迴圈內加 `if layout is not None and gate._classify(cells[status_idx]) not in gate._UNRESOLVED_CLASSES: continue`（layout 取 `status_idx`；docstring 同步「未結列才算承接載體」）。⚠ 假紅面：判準② 只判「前瞻延後行」（`:262` `n >= cur` 自動祖父化），歷史行不受影響；落地前跑 `--census` 對照改前後 problems 數，>0 的新增紅逐筆核（真紅＝前瞻行指向已結列，本來就該紅）。
2. ②tracked 語意補真：`carrier_files()` 以 `tools/lib/git_paths.ls_files(_REPO_ROOT)` 取 tracked 集合，glob 命中 ∩ tracked 才回（保留 pathlib glob 語意、避免 git pathspec 的 `**` 歧義；git 列舉走 SSOT `git_paths` 免踩 `TestGitPathEnumerationIsQuotepathSafe`）。取不到 git（`ls_files` 空/異常）→ 判準③ 出聲並退回 glob（fail-loud not fail-closed，同檔 `commit_messages()` 既有姿態）。
3. 紅綠自證：`--self-test` 合成語料補兩組——(a) 已結（fixed）列 ID 餵 `ledger_def_ids`：改前在集合內（假綠重演）、改後不在；(b) `carrier_files` 抽出可注入 tracked 集合的純函式 `_tracked_hits(hits, tracked)`，注入含未追蹤路徑的 hits → 改後被剔除。
4. 帳本立案句「改前該注入必綠」照辦：先在改前 HEAD 跑一次 (a) 注入證明綠（貼輸出），再落修復轉紅。

**預估淨行數**：`tools/check_handoff_carriers.py` **+22**（guardrail_cli 750 預算，現 418，無虞）；guard 面 **+0**。

---

### DEF-200-213　帳本治理三殘留

**① 帳本列全文**（`AutoSDD_Defect_Log.md:216`）：
> | DEF-200-213 | 2026-08-23 | R100 收尾窗口（帳本體例 C7／C8／C9 併列） | 帳本治理三筆殘留，下一輪一次清：① `DEF-200-137` 的 F3／F4 兩筆無關發現仍與主發現擠同列（體例違反，且該列 699 bytes 已頂 `ROW_MAX_BYTES` ⇒ 就地拆解必越線）；② `DEF-200-195` 無回歸鎖（本輪禁止新增測試檔）；③ crossref 逐字列出 **18 筆已結列殘留待辦**；④ 待落地的 `--reconcile` 紅綠自證經實測**拒絕落地**（見§D-14） | P3 | ① 拆列須配合 archive 搬遷；② 落 `tools/tests/` 受 DEF-200-208 死結阻擋；③ 真待辦須拆出獨立列 | open（承接輪次：**R101**）：三筆皆未動 |

**② Playbook 出口設計逐字**（Playbook:402）：
> ①拆 137 列配 archive②為 195 補鎖④--reconcile 紅綠

**③ 目標現況與分工**：
- ①（拆 `DEF-200-137` 列，`AutoSDD_Defect_Log.md:176`，699 bytes 頂線）與 ③（18 筆已結列殘留待辦拆獨立列）＝**純帳本編輯 ⇒ 結案包持有面**，本修復包不動（拆列須走 `tools/archive_defect_log.py` 搬遷路徑，F3/F4 各立新列）。修復包只提供驗收：拆完 `python tools/check_defect_log_crossref.py` rc=0。
- ②＝DEF-200-195 補鎖 ⇒ 已併入 129/195 節（同一支 2×2 注入測試，結案回執引同座標）。
- ④ `--reconcile` 紅綠：R100 §D-14 四理由否決的是 scratchpad 版測試（`RECONCILE_REPO` 下標式 env 依賴＝根層閘門必炸；受測物未追蹤；機器本地路徑當 import 常數）。**現況**：`tools/lib/quota_reconcile.py`（356 行）**至今仍未追蹤**（本回合實查 `git ls-files` rc=1），而 tracked 的 `tools/session_resume_planner.py:90` 已 `import quota_reconcile` ⇒ 「tracked 引用 untracked」活體（DEF-200-133 同族）——**任何新 clone 上 planner 直接 ImportError，本筆優先級實質高於 P3**。

**④ 修復規格（④ 那一半）**：
1. 審閱後 `git add tools/lib/quota_reconcile.py`（單人窗口唯一能做 git 寫入的角色；§D-14 理由② 的唯一出口）。guardrail_lib 400 預算：356 現值，餘裕 44。落地前該檔過 `ruff check`＋`py_compile`。
2. 紅綠自證**不新開 tools/tests 檔**（避免 `_FROZEN_GUARD_LINES` 新鍵＝全檔行數入淨額）：
   - 主體落 `quota_reconcile.py --self-test`（合成注入、零 env 依賴、零機器本地路徑；體例照 `check_handoff_carriers.py --self-test`）——行數花在 tools/lib（+~30，356→386 < 400）。
   - guard 面只放薄調用：在 `tools/tests/test_quota_policy.py` 加一支 `test_quota_reconcile_self_test_is_green`（subprocess 跑 `--self-test`、斷 rc=0 且輸出含 RED/GREEN 兩側標記）≈ **+10**。
3. §D-14 理由①③ 的反例寫進 `--self-test` docstring 一行（不得讀 `os.environ[...]` 下標、不得 import 期開機器本地檔）。

**預估淨行數**：guard 面 **+10**；tools/lib +30；帳本側 0（結案包）。

---

## §1b 同族三筆（行有餘力）

### DEF-200-191　「錨不到＝放行」升級裁決（arch，不是 quick）
- 帳本列（`:198`）：錨不到＝放行製造反向誘因；`check_claim_provenance.py:147-149` 已單獨記類（`kind="unanchored"`，`:425`）並落痕跡累計（`:445-456`）；錨不到率實測 31%〔他包回報〕、後續抽樣 unanchored 4 筆（1.2%，`:339`）。
- Playbook（`:387`）：「與 DEF-200-203 同一次裁決：(a)升級承擔假紅或(b)以出聲結案」。
- **規格**：這是裁決筆不是實作筆。建議上呈：(b) 以出聲結案——已可數、已落痕跡，而 (a) 在散文平面結構性分不出「捏的」與「截斷的」（該檔 `:148` 自陳），升級＝31% 錨不到率全轉違規的假紅海嘯；輸入面約束（引述須帶量測時間戳）隨 DEF-200-203 的 `quota_reconcile` 斷層判準落地（④ 已把受測物 track 進來＝203 解鎖前置）。**由掌舵者／四方拍板，單人窗口不得自裁**（記憶條款：僵局交還使用者決策）。

### DEF-200-195　→ 已併核心（見 129 節）。

### DEF-200-217　E2/E5 殘餘判準（dev L）
- 帳本列（`:219`）：E2＝`exec(__doc__)` 第三道套利門 200→1（−99.5%）；E5＝`sys.path.insert`＋裸模組名 import 洗白，importlinter/AST 雙盲。E1/E3/E4 已併 DEF-200-207。
- Playbook（`:405`）：「落 E2 exec(__doc__) 判準＋E5 裸名洗白 AST 擴面＋棘輪抵銷」。
- **規格（行有餘力才做）**：
  - E2：`tools/lib/guard_line_taxonomy.py` 加判準——AST 見檔內讀 `__doc__` 或呼叫 `exec`/`eval` ⇒ 該檔裸字串改判斷言（QA 方向，R100 §E-2:426-427 已複驗可行；**不是**全域禁 exec）。紅綠＝§E-2 的 arb_b/arb_d 合成檔重演（改前 1、改後 203/103）。判準測試落 `AutoClaude/tests/contract/test_loc_budget_tiered.py` 同族（**非 guard 面**）；若必須動 `tools/tests`，預算 +15。
  - E5：`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py::_harness_imports` 擴面——`sys.path.insert` 存在時把裸模組名解析回 repo 相對路徑再比對 Rule 9 邊界（紅綠＝§E-5 的 direct/laundered 對照，laundered 由 `[]` 轉命中）。全落 AutoClaude 樹，guard 面 +0。
  - 「棘輪抵銷」＝E2 若動 guard 面，須同批從瘦身銀行劃扣。
  - 建議：E5 本輪可做（零 guard 淨額）；E2 視 §3 預算餘裕，不足則明文改派 `R112`（載體＝DEF-200-217 回執）。

---

## §2 瘦身盤點（搬史料銀行）

掃描器（scan_lore_blocks.py）判準：`tools/tests/*.py` 連續 `#` 註解塊 ≥8 行、含 DEF-ID/立案/沿革/判例/史料訊號、排除帶豁免標記（`-ok:`/noqa/SSOT 宣告）的塊。**全量掃描結果：92 塊、其中 75 塊（1200 行）無豁免標記**——銀行深度遠超本輪所需。以下為精選提款清單（逐塊人工複核過首段，「可搬行數」為保守估值＝扣除仍在承重的判準說明行）：

| # | 檔:行段 | 塊行數 | 可搬(保守) | 內容 |
|---|---------|-------:|-----------:|------|
| 1 | `tools/tests/test_smoke_ci_sync.py:558-618` | 61 | **44** | R67-C19 覆蓋差集表 WHY＋取證邊界史（(a)~(d) 沿革；保留 :580-584 值形態表） |
| 2 | `tools/tests/test_windowsapps_guard_cross_consistency.py:1630-1671` | 42 | **25** | R67 B3 四實作 parity 立案史（保留四實作清單 ①~④） |
| 3 | `tools/tests/test_subprocess_encoding_hygiene.py:266-304` | 39 | **14** | R74/DEF-101-789 child 編碼方向立案史（保留判準形態段） |
| 4 | `tools/tests/test_windows_forbidden_filename_parity.py:674-702` | 29 | **24** | R66 ADR-XPLAT-002 Phase 2-D 收斂沿革（DEF-101-343/500/521/624） |
| 5 | `tools/tests/test_adr_xplat001_c1c2_lock.py:3973-3997` | 25 | **18** | ADR § 引文塊（DEF-101-561 沿革） |
| 6 | `tools/tests/test_platform_utils_dedup.py:829-850` | 22 | **16** | 2→3 擴面沿革（lint_powershell_command 納管史） |
| 7 | `tools/tests/test_subprocess_encoding_hygiene.py:1099-1117` | 19 | **14** | DEF-101-802/DEF-76-001 沿革 |
| 8 | `tools/tests/test_skip_discoverability_r83.py:128-146` | 19 | **13** | R84 W5/SD-03 立案史 |
| 9 | `tools/tests/test_windows_forbidden_filename_parity.py:374-391` | 18 | **13** | R60 保留名＋前導空白樣本電池立案史 |
| 10 | `tools/tests/test_run_root_unittests.py:1636-1652` | 17 | **12** | DEF-101-803 floor 探針沿革 |
| 11 | `tools/tests/test_ntfs_trailing_space_device_name.py:605-620` | 16 | **11** | R72/DEF-101-770 歸檔轉址沿革 |
| 12 | `tools/tests/test_install_windows_nightly.py:447-461` | 15 | **10** | R59/DEF-101-509 pwsh→5.1 判例史 |
| 13 | `tools/tests/test_schedule_capability_parity.py:105-119` | 15 | **10** | R72 darwin-only 鎖搬家史 |
| 14 | `tools/tests/test_mac_endurance_r83.py:183-195` | 13 | **9** | mac endurance 段落史 |
| | **合計** | 350 | **233** | |

- **銀行 ≥ 修復族正淨額**：233 ≥ 141（見 §3 算式）✓；後備母體另有 ~967 行（1200−233）可續提。
- **搬離目的地**＝`docs/06_quality/CrossPlatform_Guard_Line_History.md`（現 982 行），逐塊立節，節尾照抄既有先例格式（該檔 `:782`）：
  > 「> 搬遷自 `tools/tests/<檔名>`（R111 修復輪抵銷窗口；原文全文保全、知識零刪除；僅指稱詞（本檔→該檔等）隨載體必要調整）。」
- 原址各留 1~2 行指針（「WHY/沿革全文搬至 CrossPlatform_Guard_Line_History.md〈…〉節」，同 `test_adr_xplat001_c1c2_lock.py:1360-1362` 既有體例）。指針成本已計入 §3。
- **搬遷安全程序（每塊必做）**：搬之前 `grep -rn "<塊內獨特字串 2~3 條>" tools/ AutoClaude/tools/ .claude/`——確認無測試以字面斷言該註解（本 repo 多支鎖會讀原始碼文字）；搬完跑 `python tools/run_root_unittests.py` 全套。#5（鎖檔自身）與 #3/#2（混合塊）為高階操作，只搬敘事行、逐行判讀。

---

## §3 單人窗口執行順序＋淨額預算表

### 執行順序（依相依與同窗約束排定）

| 步 | 動作 | 前置 |
|----|------|------|
| 0 | 等結案包收斂帳本／Playbook 並確認（帳本 append-only 動作完畢；`check_defect_log_crossref` rc=0） | 結案包 |
| 1 | 瘦身搬遷（§2 表 #1~#14，按需提款；每塊 grep 安全檢查＋全套 unittest） | — |
| 2 | DEF-200-116 修復＋紅綠（pace_contract＋port docstring＋test_quota_policy） | — |
| 3 | DEF-200-213④：審閱＋`git add tools/lib/quota_reconcile.py`＋`--self-test`＋薄調用測試 | — |
| 4 | DEF-200-212：兩假綠修復＋`--self-test` 注入（改前綠證據先貼） | — |
| 5 | DEF-200-129＋195：helper＋自列/跨列出口改寫＋2×2 紅綠；**上線前以結案後帳本重跑 measure_129_195.py，轉紅=0 才接閘門**（殘餘以回執清零） | 步 0 |
| 6 | DEF-200-209：`.claude/ruff.toml`＋兩執行者擴射程＋16 筆存量債清零＋同步鎖＋ADR 附註訂正 | — |
| 7 | （行有餘力）217-E5（AutoClaude 樹，零 guard 淨額）；217-E2／191 視餘裕，不足即明文改派＋帳本回執 | 步 0 |
| 8 | DEF-200-121：lookahead 判準＋紅綠＋**兌現 (111,595)＋重武裝 DUE=113/585**（步伐 10<15） | 步 1~7 淨額已知 |
| 9 | 重釘收尾：`--print-guard-lines` 重印 `_FROZEN_GUARD_LINES` 全部觸及鍵→追加 R111 稽核列（同輪合併一列為佳）→凍結前綴 80→81＋SHA 重印＋`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 `("R111", 舊12, 新12, "DEF-200-121")` | 步 8 |
| 10 | guard-total 落款兩處（`_GUARD_TOTAL_DOC_MIN_SITES=2`、相異檔）：`docs/04_planning/R111_HANDOFF.md` 頂部＋最新 `CrossPlatform_R*_Scan_Findings.md` R111 標記行，三元組 `89467 → <新總量>（−N）`（負號體例走 `_GUARD_TOTAL_TRIPLE_RE` 已支援 −） | 步 9 |
| 11 | 全套驗證：`python tools/run_root_unittests.py`＋`ruff check tools/ .claude/hooks/ --no-cache`＋`python tools/check_defect_log_crossref.py`＋`python tools/check_handoff_carriers.py`＋AutoClaude `python -m pytest tests/ -q`（動了 port docstring）→ pre-push 全套（背景執行，逐字貼 rc） | 全部 |

### 淨額預算表（guard 量測面＝`tools/tests/*.py` 非遞迴）

| 項 | 檔 | 估值 |
|----|----|-----:|
| 116 紅綠 | test_quota_policy.py | +16 |
| 121 判準＋紅綠＋兌現＋稽核列 | test_adr_xplat001_c1c2_lock.py | +45 |
| 129＋195 紅綠（2×2 ×2 組） | test_check_defect_log_crossref.py | +30 |
| 209 同步鎖擴面 | test_subprocess_encoding_hygiene.py | +12 |
| 213④ 薄調用 | test_quota_policy.py | +10 |
| 212 紅綠 | （全落 check_handoff_carriers --self-test，guard 面） | +0 |
| 瘦身指針殘留（14 塊 × 2 行） | 各檔 | +28 |
| **新增小計 A** | | **+141** |
| 瘦身搬遷（§2 表全提） | 各檔 | **−233** |
| **本輪淨額 = A − 233 = 141 − 233** | | **= −92 ≤ 0 ✓** |

- 驗算式：`141 − 233 = −92`；緩衝 92 行（若 217-E2 落 guard 面 +15，淨額 −77 仍 ≤0；若任一估值超支，銀行後備 ~967 行可續提）。
- 同步滿足款(12)：新 cap 595 ≥ |任何正淨額|——本輪淨額為負，款(10)(11)(12) 三款皆過；連續上升計數歸零（M1 進度）。
- ⚠ 三個非 guard 面預算另行自查：`tools/check_defect_log_crossref.py` SPECIAL_FILES cap 1479（assertion 計價，+改動後現查 `check_loc_budget --json`，必要時同檔搬 `:428-465` 沿革抵銷）；`.claude/hooks/context_budget_guard.py` SPECIAL cap 1089（E501 改寫優先縮字不換行）；`tools/lib/quota_reconcile.py` guardrail_lib 400（356+30=386 ✓）。

### 禁止事項（任務書條款）
- 不准 `--no-verify`、不准調高 `_REPIN_ROUND_NET_CAP`/`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`/新 lookahead 常數（只准下修）、不准為過閘自加 `_REPIN_APPROVED_ROUND_OVERAGE` 條目（須四方核准）。
- 不准在結案包收斂前落 129 上鎖（大片假紅＝守衛被關掉的前奏）。
- 搬史料＝原文全文保全，不准刪知識；每塊搬前 grep、搬後全套 unittest。
- 帳本原文列不准改寫（append-only）；116/121/129/195/209/212/213 結案一律走回執＋引本輪測試/commit 座標。
