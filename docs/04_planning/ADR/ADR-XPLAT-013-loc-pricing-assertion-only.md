# ADR-XPLAT-013 — LOC 計價規則改為 assertion-only（棘輪憲法修正案 v4）

- **狀態**：**Proposed（掌舵者已裁決實作並落地；ADR-XPLAT-012 條文六的四方複審尚待補行。🔴 機械物已先上生產、程序後補——風險與可勾稽解鎖條件見〈§7 解鎖條件〉）**
- **日期**：2026-08-22
- **平台**：平台中立
- **性質**：修正 `AutoClaude/tools/check_loc_budget.py::count_loc()` 的**計價規則**——由「空行與行首 `#` 免費、其餘（含 docstring）等價計價」改為「**只算斷言行**」，計價本體委派 `tools/lib/guard_line_taxonomy.classify_file()` 的 `.assertion` 桶。
- **關係**：本案是 ADR-XPLAT-012 條文五 §1 明文要求的「另一次修正案」（把 Phase 1 觀測欄位轉為阻斷判準），落地其 Phase 2 的**方向 (a)**；方向 (b)(c) 未落地，交棒收尾單人窗口。
- **落地實測與逐檔清單**：[docs/06_quality/CrossPlatform_R100_Scan_Findings.md](../../06_quality/CrossPlatform_R100_Scan_Findings.md)

---

## §1 立案事實（當回合實測，非援引歷史值）

### 1.1 缺陷本體＝一道被制度化的套利門

改前 `count_loc()` 只有 8 行邏輯：

```python
for line in f:
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    n += 1
```

⇒ 整行 `#` 免費、**docstring 全額計價**，且 docstring 的每一行與一行 `if` 同單價。兩者都是「解釋為什麼、不是判斷什麼」的敘事文字，卻因為載體是 `"""..."""` 還是 `# ...` 而被判成天壤之別的兩種東西。

於是「把 docstring 逐字改寫成 `#` 前綴」可在 **raw 行數與可執行 AST 節點數逐字不變**的前提下大幅降低計價。這道門不是理論上的：

1. **工具自己教過**：`[TIER-WARN]` 段原文逐字寫「說明文字請寫成 `#` 註解而非 docstring——docstring 行會被 count_loc 計入，寫進 docstring 等於再吃掉預算」。該句已於本案同一次變更移除。
2. **全庫有一批程式碼站點自陳在用它**：立案當時以單行 grep 數得 18 個；否決權複審 M3 以跨行判準重建普查後為 **25 個**（原表至少漏 7 列，三種漏法見 §8.1）。逐點座標與分類見〈§8 交棒清單〉。

### 1.2 三支「頂格檔」的改前／改後實測

| 檔案（budget） | 改前 `count_loc`（餘裕） | 改後 `count_loc`（餘裕） |
|------|---:|---:|
| `tools/lib/quota_gate.py`（500） | 500（**0**） | **356**（144） |
| `.claude/hooks/block_destructive_git.py`（750） | 750（**0**） | **558**（192） |
| `tools/probe/audit_session.py`（750） | 711（39） | **532**（218） |
| `tools/session_resume_planner.py`（750） | 750（**0**） | **720**（30） |

`AutoClaude` 總量：`total` 20426 → **16483**；`baseline` 17032、`cap` 20438 不變 ⇒ 餘裕 **12 → 3955** 行。

### 1.3 鑑別力自證（同一組合成檔，兩套判準對照）

| 判準 | docstring 載體 | `#` 載體 | 差額 |
|------|---:|---:|---:|
| 改前（硬編二分） | 8 | 5 | **3**（套利門） |
| 改後（assertion 桶） | 5 | 5 | **0** |

回歸鎖＝`AutoClaude/tests/contract/test_loc_budget_tiered.py::test_narrative_carrier_swap_is_priced_identically`。

### 1.4 換值域**沒有**放寬任何門檻（母體限定；否決權複審 M2 訂正）

分類器的「強制歸斷言」規則（shebang／PEP 263／`ASSERTION_PRAGMA_COMMENTS`）把三類整行 `#` 由免費改為**計價**。

🔴 **本節原文寫「當回合全樹逐檔比對：`新值 > 舊值` 的檔數＝0」——那是一個沒有母體限定的假數字**，複審逐檔重測推翻。訂正後的真值（本輪實測，兩個母體分開報）：

| 母體 | 定義 | 支數 | `新值 > 舊值` |
|------|------|---:|---:|
| **閘門計價母體** | `build_reports()` 207 ＋ `root_tools_reports()` 79（`SPECIAL_FILES` 那 7 支 `.py` 走 `count_raw_lines`、不經 `count_loc`，不在本母體） | **286** | **0** |
| **全樹** | `git ls-files '*.py'` | **5557** | **2** |

全樹那 2 支逐檔列出（方向皆**收緊**，兩支皆**未破線**、皆非受計價閘門管的檔）：

| 檔案 | 舊值 → 新值 |
|------|---:|
| `AutoClaude/tests/tools/test_scaffold_sprint_section.py` | 116 → **118**（+2） |
| `AutoClaude/tests/tools/test_snapshot_sync_sprint_skeleton.py` | 113 → **116**（+3） |

**機制不是上表那三類**（shebang／PEP 263／pragma），而是**指派給變數的字串裡的 Markdown 標題**：兩支檔都有 `SAMPLE_HISTORY = """\ … """` 這種測試素材，內含 `# Sprint 歷史`／`## 1. 主目錄` 等 Markdown heading。舊判準 `line.strip().startswith("#")` 看到行首井號就免費（＝把 Markdown 誤判成 Python 註解）；新判準因該字串**不是裸 `Expr(Constant)`**（它是 `Assign` 的右值）而整段歸斷言。逐行實測：`test_scaffold_sprint_section.py` 有 5 行、`test_snapshot_sync_sprint_skeleton.py` 有 8 行是這種「新計價」的井號行，扣掉同檔 docstring 轉免費的抵銷後淨額為 +2／+3。

tier／`ABSOLUTE_LIMIT`／`SPECIAL_FILES`／`_FROZEN_GUARD_LINES` 全部門檻**一字未動**。

### 1.5 🔴 落地第一版把套利門**搬家並變寬**了（否決權複審 M1；已於同輪修掉）

改用敘事桶的第一版只關掉 docstring↔`#` 那一道（複審量得的門值 37.5%），同一次改動卻開了一道更寬的新門：`ast.Expr(ast.Constant(str))` 的 `(lineno, end_lineno)` 涵蓋整個**物理行**，於是**任一行前面加一個裸字串 ＋ 分號**（`""; x = 1`）就能讓該行整行落進敘事桶 ⇒ **免費**。

在真的受計價檔上機械套用（只在單物理行的 simple statement 前綴，**raw 行數與每一個 AST 邏輯節點皆逐字不變**）：

| 判準 | `.claude/hooks/block_destructive_git.py` |
|------|---|
| 落地第一版（未補 M1） | 558 → **316**（**−43.4%**，被獎勵） |
| 舊計價（pre-013） | `; ` 破壞行首井號 ⇒ 該手法**被懲罰** |
| 補上 M1 之後 | 558 → **558**（**+0.0%**） |

**對抗性探針（補 M1 之後，逐形態實測）**——不只量一種形態，避免「補了一個洞、旁邊還有一個」：

| 形態 | raw | assertion | 對照 baseline | 結論 |
|------|---:|---:|---|---|
| baseline：3 個 simple statement | 3 | **3** | — | 基準 |
| 逐行**前綴**裸字串（M1 主形態） | 3 | **3** | 3 | 門關了 |
| 逐行**後綴**裸字串 | 3 | **3** | 3 | 門關了 |
| 前綴 ＋ 反斜線續行 | 2 | **1** | 1 statement = 1 | 收支平衡（多付 1 raw 行換價格不變） |
| 多行字串的收尾行接語句 | 2 | **1** | 1 | 收支平衡 |
| 拆行 ＋ 尾綴裸字串 | 2 | **1** | 1 | 收支平衡 |
| 括號內插入整行井號註解 | 3 | **2** | 2 | 無變化（該行真的沒有程式碼） |
| **多語句擠一行（分號串三個 assign）** | 1 | **1** | 3 | 🔴 **仍省** —— 見 §6 缺口 ⑥（行數制共有性質，非本案開的門） |
| 對照組：正常 3 行 module docstring | 4 | **1** | 1 | 零假紅（敘事仍免費） |

⇒ 「門在值域上關閉」這句話在補 M1 之前是**假的**，門只是搬家並變寬，而且方向由懲罰翻成獎勵。修法＝條文一 §1.4（見下），機械物＝`guard_line_taxonomy._shared_code_lines()`。唯一原本擋得住這招的 ruff E701/E702 在 `.claude/hooks/` 沒有任何閘門（見 §6 缺口 ⑥），不能當依靠。

---

## §2 條文一 — 計價規則

**§1.1** `count_loc(path)` 回傳 `guard_line_taxonomy.classify_file(path).assertion`。判準本體**不得**在 `check_loc_budget.py` 內再實作一份（一份判準一個家）。

**§1.2** 敘事（docstring／裸字串 ∪ tokenize 判定的整行 `#`）與空白行一律**零計價**；行尾附掛註解不影響該行的計價（行的種類由主體決定，＝ADR-XPLAT-012 條文二 §1）。

**§1.3** `SPECIAL_FILES` 的 raw-line 棘輪**不受本案影響**（`count_raw_lines` 逐字未動）——那一層量的是「這份文件最多可以長到幾行」，與「判斷邏輯有多少」是兩個度量面。

**§1.4（否決權複審 M1 補立）** **同一行還有「別人的」statement 起點的行，強制歸斷言**——即使該行被某個 `Expr(Constant(str))` 的 `(lineno, end_lineno)` 涵蓋。機械物＝`guard_line_taxonomy._shared_code_lines()`，立案量測見 §1.5。

- **判準只看 `lineno`、不看 span 涵蓋面**：`ast.stmt` 的 span 會包住自己的 body（`FunctionDef` 的 span 涵蓋它的 docstring），看涵蓋面等於把所有函式／類別的 docstring 全部沒收（整批假紅）。
- **字串節點自己的 `lineno` 必須排除**，否則每個 docstring 的第一行都會被自己打成斷言。
- **只看起點的殘留形態是收支平衡、不是套利**：把語句拆成多物理行、再在最後一行綴 `; ""`，綴出來的那一行免費，但拆行多出來的物理行本身就是斷言 ⇒ 淨額 0。
- **假紅實測（母體限定）**：補上本條之後 `新值 > 舊值` 的檔數＝**0**（閘門計價母體 286 支）／**0**（全樹 5557 支）。即本條**只往收緊方向動、且對現況零衝擊**。
- 回歸鎖：`AutoClaude/tests/contract/test_loc_budget_tiered.py::test_a_bare_string_prefix_cannot_buy_a_free_line`（合成檔紅綠自證：修前該手法降價、修後計價不變）。

---

## §3 條文二 — unparseable 必須 fail-loud

**§2.1** 分類器對讀檔失敗／`SyntaxError` 的契約是「跳過並標記、三桶歸零」（ADR-XPLAT-012 條文一 §4）。計價器**不得**照抄那個 0：`count_loc()` 一律拋 `UnparseableSourceError`（`ValueError` 子類）。

**§2.2 WHY**：回 0 會讓「語法錯誤」變成**零成本**，也就是「最省預算的手法是把檔弄壞」——那是本案要關的套利門的鏡像版本，失效方向比破線更糟。

**§2.3** 呼叫端二擇一，兩條都會留下痕跡：①讓例外傳播（`build_reports()`／`root_tools_reports()` 走這條，逐檔迴圈 fail-loud）；②翻譯成一筆具名違規／WARN（PostToolUse hook `loc_budget_check.py` 走這條，rc=1 且印出理由——靜默 `return 0` 等於「剛寫壞的檔沒有任何訊號」）。

**§2.4** 回歸鎖＝`test_count_loc_refuses_to_price_an_unparseable_file`。

---

## §4 條文三 — 零緩衝豁免（**只限計價規則變更當輪**）

**§3.1（豁免內容，窄）** 計價規則變更的那一輪，**不必**把 `AutoClaude/.loc_baseline` 重釘為改後 total 的實測值。ADR-XPLAT-012 條文五 §3 的取值紀律（「當回合實測直接填入、零加減推算、不留成長緩衝」）在那一輪、且僅在那一輪，對這一個檔案暫停適用。

**§3.2（豁免理由）** 換計價器當輪的 total 位移不是「這一輪長了多少」——它是同一份程式碼換了一把尺。立刻重釘會把整段位移一次性沒收，而改前的實測餘裕是 **12 行**（後續包連一行接線都加不進去）。掌舵者裁決：走豁免，不照條文五 §3 立刻重釘為現值。

**§3.3（豁免射程，明文封閉）** 豁免**只**適用於計價規則變更當輪。後續任何輪次一律回到 ADR-XPLAT-012 條文五 §3 的零緩衝要求。豁免不涵蓋：tier／`ABSOLUTE_LIMIT`／`SPECIAL_FILES`／`_FROZEN_GUARD_LINES` 任一門檻的調整（本案對它們零加、零減、零緩衝），也不涵蓋 `TOTAL_INCREASE_LIMIT` 那 20% 的結構性緩衝（那是 ADR-SD07-001 的既有設計，不在本案射程）。

**§3.4（豁免的機械載體——沒有這一格就等於沒有豁免條款）**

| 載體 | 位置 |
|------|------|
| 具名到期常數 `_PRICING_CHANGE_EXEMPT_ROUND`（＋方向鎖基準 `_FROZEN_PRICING_CHANGE_EXEMPT_ROUND`） | `tools/tests/test_adr_xplat001_c1c2_lock.py` |
| 判準 `pricing_exemption_problems()`：`[量不到]`／`[豁免過期]`／`[豁免被延期]` 三款 | 同上 |
| 紅綠自證 `TestPricingChangeExemptionExpiresOnItsOwn`（今日為綠／走過豁免輪為紅／重釘後回綠／延期為紅／量不到為紅） | 同上 |
| 時鐘 | `live_repin_round()`＝`_GUARD_LINES_REPIN_LOG` 的最大輪號（**不另開第二個輪次時鐘**） |

判準語意：稽核痕跡的輪號 **>** `_PRICING_CHANGE_EXEMPT_ROUND` 而 `.loc_baseline` 仍高於實測 total ⇒ **紅**。出口只有一個且永遠開著：`python AutoClaude/tools/check_loc_budget.py --update`（一行 diff）。反向出口已封：`_PRICING_CHANGE_EXEMPT_ROUND` **只准調小**（更早到期＝更嚴），刻意不留延期參數——可延期的到期日不是到期日。

**§3.5 WHY 這一格非有不可**：本 repo 已有實證，散文形態的「只限這一輪」攔阻力為 0（`feedback_promise_without_mechanism_stalls_silently`：說了「reset 後續跑」但無機制 ⇒ 三小時真空轉）。沒有機械載體的豁免＝口頭承諾。

---

## §5 條文四 — ADR-XPLAT-012 條文五 §6「5 輪時效」的到期載體

**§4.1（承接）** ADR-XPLAT-012 的〈未解決缺口〉節逐字自陳：「條文五 §6 的 5 輪時效尚未有到期時點的具名常數——本 ADR 用散文描述『5 輪內未提出 Phase 2 提案須重新 review』，但比照本 repo `_REPIN_NET_CAP_DUE_ROUND` 的既有慣例，這類到期義務應該有一個機械可查的具名常數與判準，本輪未建立。」本條文即該項的落地。

**§4.2（載體）** 全部住 `tools/tests/test_adr_xplat001_c1c2_lock.py`：

- `_PHASE2_REVIEW_LOG`：**append-only** 的 `(輪號, 結局標記, 理由)`；首列＝視窗起算錨（Phase 1 觀察模式落地的那一輪）。
- `_PHASE2_OUTCOMES`：封閉表 `("[提案]", "[維持觀察]", "[落地]")`——條文五 §6 只給兩條合法出路，第三個是「已落地」。
- `_PHASE2_REVIEW_WINDOW = 5`（＝§6 的字面），只准調小。
- `_PHASE2_MAX_CONSECUTIVE_DEFERRALS = 1`：**本表真正的牙**。§6 允許「重新武裝下一個視窗」，若不設上限，每輪貼一行 `[維持觀察]` 就能無限期買下去——而 §6 自己寫的是「不留無限期空轉的觀察機制」。只准調小。
- `_PHASE2_DUE_ROUND`＝**由末列導出**（末列輪號 ＋ 視窗），不另立第二個家。
- 判準 `phase2_review_problems()`：`[空表]`／`[輪號未遞增]`／`[結局不在封閉表]`／`[無理由]`／`[連續空轉]`／`[時效逾期]`／`[視窗被放寬]`／`[上限被放寬]`。
- 紅綠自證 `TestPhase2FiveRoundDeadlineIsMechanical`（七格）。

**§4.3（本輪的兩列）** 起算錨＝Phase 1 落地輪（`[維持觀察]`，當輪未提出 Phase 2 提案，該 ADR 的〈狀態〉節逐字寫「未落地、未提案」）；本輪＝`[落地]`（方向 (a) 落地，(b)(c) 未落地故視窗依 §6 重新武裝一次）。

---

## §6 未解決缺口（本案落地時**未**解決，原樣列出）

1. **ADR-XPLAT-012 條文六的四方複審尚未補行**。掌舵者裁決「Phase 2 三個方向全做」並授權實作，但條文五 §1 逐字要求「任何要把這些欄位轉為阻斷判準的提案，是另一次修正案，須另走條文六的四方複審程序（不可用『反正資料都印出來了』的理由直接生效）」。本案的〈狀態〉因此是 **Proposed 而非 Accepted**。逐項解鎖條件見 §7。
2. **Phase 2 方向 (b)(c) 未落地**，交棒收尾單人窗口／Stage 2。
3. **全庫自陳站點未逐一改寫**。普查已於否決權複審 M3 重建（原表的單行 grep 至少漏 7 列，方法與訂正後筆數見 §8）。那些站點在新計價下**不再有套利效果**，但註記文字仍在講一個已經不成立的理由 ⇒ 下一個讀者會照著做一件已經沒有好處的事。本輪已訂正 2 支（`tools/lib/hook_wiring.py:4`、`AutoClaude/autoclaude/models/escalation.py:79`，理由見 §8.3），其餘交棒。
4. **`tools/tests/test_block_destructive_git_r83.py::TestTheHookStaysInsideItsLocTier` 的早期預警靈敏度下降**（該檔由 750/750 變成 558/750）。它現在守的是「判斷邏輯量不得長到 tier 之外」——那才是 tier 本來想守的東西，但「再加一行就破線」這個訊號沒有了。已逐字寫進該類 docstring。
5. **`AutoClaude` tier 與根層 tools tier 的預警帶雙雙變空**，且那三個 `*_WARN_MARGIN` 常數在新值域下是否仍是合適的門檻，**本案未重新評估**。否決權複審 M5 已把記帳切開（原本「非空」與「逐層篩選語意」擠在同一支測試裡，於是那兩層退化成空集合互比卻仍掛在「真實資料驗收」名下）：
   - `test_real_repo_bands_match_production_output`：**只驗一致**（production == 獨立推導），刻意允許任一層為空。
   - `test_the_warn_band_machinery_has_a_live_population`：**只驗母體**（三層聯集非空），並把逐層筆數印進失敗訊息，讓「哪一層在承重」看得見。
   - `test_the_semantic_owners_delegated_to_by_the_real_data_lock_still_exist`：把「語意由合成鎖負責」這句委派**釘住**——合成鎖被刪／改名即紅，否則那句委派是散文。
   - 篩選語意本體仍由本檔既有的**合成資料**鎖負責（`_SEMANTIC_OWNERS` 具名五支），它們對空層照樣有牙。
6. **🔴 行數制計價的共有殘留：多語句擠一行（`a=1;b=2;c=3`）在任何行數制下都是省錢的**（三個 statement 只算一行）。這**不是本案開的門**——舊計價下同樣省錢，而且它同時**減少 raw 行數**，所以在 raw-line 棘輪那一軸也是省的。本案不宣稱關掉它。**擋它的唯一現成工具是 ruff E701/E702，而 `.claude/hooks/`（受 `root_tools` tier 計價）沒有任何 ruff 閘門**——`AutoClaude/` 側 pre-commit 的整檔 ruff 不涵蓋根層 `.claude/hooks/` 與 `tools/`。交棒選項：①把 E701/E702 接到根層 pre-commit 的 `.claude/hooks/`＋`tools/` 面（本包不做：pre-commit dispatcher 與 workflow 不在本包授權檔案面，且該類鎖的常數／史料／消費端分屬不同持有面＝鐵律七）；②在 `guard_line_taxonomy` 加「一行多 statement 起點 ⇒ 按 statement 數計價」的判準（射程更大、假紅風險未量測，須另案立案）。**未做選擇＝缺口原樣登記。**

---

## §7 解鎖條件（Proposed → Accepted 的可勾稽清單；否決權複審 M6）

🔴 **本案的事實與風險，原樣寫在這裡**：**機械物已先上生產、程序後補**。`count_loc()` 的新計價已在閘門實際生效（`total` 20426 → 16483、`cap` 20438 不變 ⇒ 餘裕由 12 行變成四位數並已被後續包消費），而 ADR-XPLAT-012 條文六要求的四方複審**尚未進行**。承擔的風險，照實列：

- **四位數餘裕已被消費**：若複審否決本案、要回退計價規則，回退當下 `total` 會跳回兩萬出頭並**超過 cap**，屆時已經寫下的行沒有地方去 ⇒ 回退的實際成本隨每一輪遞增。這是「先上生產」最貴的一項，且**會自己長大**。
- **§4 條文三的零緩衝豁免已生效**（`.loc_baseline` 未重釘），其到期載體 `_PRICING_CHANGE_EXEMPT_ROUND` 是**單向**的（只准調小），設計上不容許用「複審還沒過」當延期理由。
- **已有兩道判準改寫過的假數字被複審抓到**（§1.4 的「全樹零檔上升」、§1.5 的「門在值域上關閉」）——兩者都是在**沒有**四方複審的情況下寫進判準 docstring 並通過閘門的。這件事本身就是「程序後補」的實測代價。

| # | 解鎖條件 | 現況 | 勾稽方式 |
|---|---------|------|---------|
| U1 | Architect 獨立審查 APPROVE | ☐ 未進行 | 在本節下方具名記錄（角色／結論／日期） |
| U2 | SA 獨立審查 APPROVE | ☐ 未進行 | 同上 |
| U3 | SD 獨立審查 APPROVE | ☐ 未進行 | 同上 |
| U4 | QA 獨立審查 APPROVE | ☐ 未進行 | 同上 |
| U5 | §6 缺口 ⑥（多語句擠一行 × `.claude/hooks/` 無 ruff 閘門）已做出選擇並落地或明文接受 | ☐ 未選擇 | 缺口 ⑥ 的兩個選項擇一，或四方明文接受該殘留 |
| U6 | §6 缺口 ⑤（三個 `*_WARN_MARGIN` 在新值域下是否合適）已重新評估 | ☐ 未評估 | 附當回合實測的逐層母體筆數 |
| U7 | §8 交棒清單的自陳站點處置方針已定（逐一改寫／保留加註／搬回 docstring） | ☐ 未定 | 方針寫進 §8 表頭；逐點落地可分輪 |

**四方全數 APPROVE 且 U5~U7 有明文結論之後**，才把〈狀態〉由 Proposed 改為 Accepted。**本包不得自行開複審**（那是主控／收尾單人窗口的事），本節只把條件寫成可勾稽的形狀。

---

## §8 交棒清單（自陳「刻意寫成 `#` 以避開 count_loc」的程式碼站點）— **普查已重建（否決權複審 M3）**

**處置方針（U7 待四方確認）**：本案刻意不逐一改寫——那是史料，逐一改寫會製造大量無語意 diff 且與本案的判準改動混在同一批。**例外**：會讓下一個人做出錯誤決定的站點（宣稱一件已被實測推翻的事、或引用一句已被刪除的訊息）當輪修掉，見下表 ✅ 兩列。

### 8.1 原表怎麼漏的（方法訂正）

原表的 18 列是用**單行 grep** 建的，複審實測至少漏 7 列。三種漏法：

1. **跨行寫法**：`散文寫在**註解**裡（註解不計` 在第 556 行斷句，`count_loc` 在下一行 ⇒ 單行 grep 對它結構性失明。
2. **不寫 `count_loc` 只寫 `LOC`**：`（`#` 不計 LOC，內容一字未改）` 這種形態整批漏掉。
3. **詞彙不在原詞表**：真實語料寫的是「**計** docstring 行、**不計**註解行」，而 M3 指定的詞表（跳過／免費／排除／計入）不含「計／不計」——**指定詞表本身也不夠**，照實記。

重建後的判準（跨行、窗 3 物理行；三者須同段命中）：主詞 `count_loc｜check_loc_budget｜LOC` **∧** 計價動詞 `計入｜不計｜免費｜排除｜跳過｜只計｜零成本｜吃掉` **∧** 載體字 `docstring`；另跑一次把載體放寬為 `docstring ∪ 註解`（窗 8）補抓只提「註解」的形態。

**實測筆數**：緊判準 `.py` 命中 **28**；放寬載體後 **40**，多出的 12 筆中真站點 3（`tools/lib/skip_group_policy.py:556`／`:801`、`tools/lib/quota_meter.py:377`），其餘 9 為假陽性（掃描器自己在講「怎麼剝註解」）。扣掉假陽性與「已是新規則描述」的站點後，**真的自陳舊規則的站點＝25**（原表 18 ＋ 漏掉的 7）。

### 8.2 分類後的清單

| 檔案:行 | 狀態 |
|---------|------|
| `AutoClaude/autoclaude/core/wiring.py:4` | 待訂正 |
| `AutoClaude/autoclaude/core/orchestration/coordinator.py:4` | 待訂正 |
| `AutoClaude/autoclaude/core/services/auto_resume.py:317` | 待訂正 |
| `AutoClaude/autoclaude/infra/repositories/pg_state_repository.py:48` | 待訂正 |
| `AutoClaude/autoclaude/plugins/token_guard/policy.py:5` / `:179` / `:249` | 待訂正 |
| `AutoClaude/autoclaude/utils/config.py:216` | 待訂正 |
| `AutoClaude/autoclaude/perception/pty_wrapper.py:156` | 待訂正 |
| `AutoClaude/autoclaude/execution/evaluator.py:4` / `:152` | 🔴 **原表漏**（漏法 2） |
| `AutoClaude/autoclaude/execution/mutation_applier/_conditional.py:5` / `:38` | 🔴 **原表漏**（漏法 2） |
| `tools/session_resume_planner.py:4` | 待訂正 |
| `tools/lib/endurance_env.py:2` | 待訂正 |
| `tools/lib/quota_gate.py:789` | 待訂正（原表寫 `:788`，實測 `:789`） |
| `tools/lib/quota_policy.py:477` | 待訂正 |
| `tools/lib/schedule_backend.py:3` / `:265` / `:527` | 待訂正（原表寫 `:264`，實測 `:265`） |
| `tools/lib/skip_group_policy.py:556` | 🔴 **原表漏**（漏法 1：跨行） |
| `tools/lib/skip_group_policy.py:660` / `:801` | 待訂正 |
| `tools/lib/hook_wiring.py:4` | ✅ **本輪已訂正**（原表漏；見 8.3） |
| `AutoClaude/autoclaude/models/escalation.py:79` | ✅ **本輪已訂正**（原表漏；見 8.3） |

**不同軸、非本案射程**：`tools/lib/quota_meter.py:377` 講的是 `tools/tests/*.py` 的 **raw-line 淨額棘輪**（`_FROZEN_GUARD_LINES`），依條文一 §1.3 不受本案影響 ⇒ 不列入待訂正。

### 8.3 為什麼這兩列當輪修掉（不留到後面）

- **`tools/lib/hook_wiring.py:4-9`** 原文逐字寫「⇒ 要加 WHY 請往下寫 `#`；**把這段搬回 docstring 會直接讓 LOC 閘門再紅一次**」，並引 `[TIER-WARN]` 訊息當依據。複審實測：把下方 52 行 essay 逐字搬進 docstring，`count_loc` **367 → 367（+0）** ⇒ 那句宣稱是假的；而它引用的那句 TIER-WARN 指路**正是本案刪掉的** ⇒ 引用懸空。兩件事合起來就是「照著讀會做錯事」，屬當輪必修。
- **`AutoClaude/autoclaude/models/escalation.py:79`** 原文把 R56「行尾併入」手法的成本理由寫成「`count_loc()` 只跳過空行與行首 `#`」——現在還會跳過 docstring／裸字串，該理由已不成立。已改為明記「括號裡原本的理由已不成立、行尾註解不增斷言行那一半仍成立」。

### 8.4 文件面站點（**非套利站點，是史料**，優先度更低）

`AutoClaude/docs/04_planning/ADR/ADR-SD07-001-loc-policy.md:268`、`docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md:719`、`docs/04_planning/ADR/ADR-XPLAT-003-autoclaude-platform-capability-layer.md:111`、`docs/04_planning/ADR/ADR-XPLAT-012-guard-line-taxonomy-amendment.md:28/34/40`、`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md:1804`、`docs/06_quality/CrossPlatform_R96_Closure_Evidence.md:203`、`AutoClaude/docs/05_development/risk_log.md:29`、`AutoClaude/docs/04_planning/SD_Improving_02.md:511`。

放寬載體後的 `.md` 面命中 **35 筆**（含 20 餘筆缺陷帳本 archive 的歷史條目）——那些是**帳本史料，不得改寫**（改了就毀了當時的實測記錄）。
