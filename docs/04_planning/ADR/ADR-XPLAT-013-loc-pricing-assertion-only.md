# ADR-XPLAT-013 — LOC 計價規則改為 assertion-only（棘輪憲法修正案 v4）

- **狀態**：**Accepted（2026-10-09；ADR-XPLAT-012 條文六四方獨立審查補行完成：Architect 鏡／SA／SD／QA 四票結論具名記於 §7.1；機械物 R100 先上生產、程序 R210 後補——補行時回退已不可行（見 §7 開頭〈R210 補行結果〉），故本次審查的實質是對條文與現況落差、U7／U9 處置的追認與訂正，不是「核准／否決上線」二選一；〈§6 未解決缺口〉各項結局以 §7 為準，U7／U9 以症狀驅動結案、不留輪號義務）**
- **日期**：2026-08-22
- **平台**：平台中立
- **性質**：修正 `AutoClaude/tools/check_loc_budget.py::count_loc()` 的**計價規則**——由「空行與行首 `#` 免費、其餘（含 docstring）等價計價」改為「**只算斷言行**」，計價本體委派 `tools/lib/guard_line_taxonomy.classify_file()` 的 `.assertion` 桶。
- **關係**：本案是 ADR-XPLAT-012 條文五 §1 明文要求的「另一次修正案」（把 Phase 1 觀測欄位轉為阻斷判準），落地其 Phase 2 的**方向 (a)**；方向 (b) 已於 R116 落地（分軌計價）；方向 (c) 依 R110 D-4 降級為觀測欄（只印不擋，見 §6 第 7 項）。
- **落地實測與逐檔清單**：[docs/06_quality/CrossPlatform_R100_Scan_Findings.md](../../06_quality/CrossPlatform_R100_Scan_Findings.md)
- **後續修憲（R101）**：R100 收尾窗口的四方唯讀複審（同上檔案 §E）對本案提出五筆新發現（E1~E5），其中 E1／E4 已由四方重投票裁決並於本輪落地（**§9** 揭露與技術債追蹤／**§10** 條文五 cap 解耦），**§11** 條文六同時把 `policy_version` 版號跟上條文一的計價尺變更、且 `pricing_exemption_problems()` 的 provenance 判準改寫本輪已由 E3/DEF-200-208 一併落地（見 §6.2）；E2（DEF-200-209，R116 補 S102 軸）與 E5（DEF-200-217，R126 的 sys.path 洗白＋裸名判準）亦已結案；E3 的資料面回填於 R102 執行（commit 6fea8a3b）；U5～U10 於 R210 全數勾稽，見 §7。

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

⇒ 「門在值域上關閉」這句話在補 M1 之前是**假的**，門只是搬家並變寬，而且方向由懲罰翻成獎勵。修法＝條文一 §1.4（見下），機械物＝`guard_line_taxonomy._shared_code_lines()`。唯一原本擋得住這招的 ruff E701/E702 在 `.claude/hooks/` 沒有任何閘門（見 §6 缺口 ⑥），不能當依靠。（R111 訂正：`.claude/hooks/` 已納 ruff 射程——`.claude/ruff.toml` extend `tools/ruff.toml`，E701/E702 隨 select `E` 生效，執行者＝pre-push 快層④＋root-infra-ci 第 16 道；DEF-200-209。本句原文照舊保全＝寫成當時的現況。）

---

## §2 條文一 — 計價規則

**§1.1** `count_loc(path)` 回傳 `guard_line_taxonomy.classify_file(path).assertion`。判準本體**不得**在 `check_loc_budget.py` 內再實作一份（一份判準一個家）。

**§1.2** 敘事（docstring／裸字串 ∪ tokenize 判定的整行 `#`）與空白行一律**零計價**；行尾附掛註解不影響該行的計價（行的種類由主體決定，＝ADR-XPLAT-012 條文二 §1）。

**§1.3** `SPECIAL_FILES` 的 raw-line 棘輪**不受本案影響**（`count_raw_lines` 逐字未動）——那一層量的是「這份文件最多可以長到幾行」，與「判斷邏輯有多少」是兩個度量面。

**§1.4（否決權複審 M1 補立）** **同一行還有「別人的」statement 起點的行，強制歸斷言**——即使該行被某個 `Expr(Constant(str))` 的 `(lineno, end_lineno)` 涵蓋。機械物＝`guard_line_taxonomy._shared_code_lines()`，立案量測見 §1.5。

- **判準只看 `lineno`、不看 span 涵蓋面**：`ast.stmt` 的 span 會包住自己的 body（`FunctionDef` 的 span 涵蓋它的 docstring），看涵蓋面等於把所有函式／類別的 docstring 全部沒收（整批假紅）。
- **字串節點自己的 `lineno` 必須排除**，否則每個 docstring 的第一行都會被自己打成斷言。
- **只看起點的殘留形態是收支平衡、不是套利**：把語句拆成多物理行、再在最後一行綴 `; ""`，綴出來的那一行免費，但拆行多出來的物理行本身就是斷言 ⇒ 淨額 0。
- **假紅實測（母體限定）**：補上本條（M1 補丁）前後比較，`新值 > 舊值` 的檔數＝**0**（閘門計價母體 286 支）／**0**（全樹 5557 支）。即本條**只往收緊方向動、且對現況零衝擊**。
- 回歸鎖：`AutoClaude/tests/contract/test_loc_budget_tiered.py::test_a_bare_string_prefix_cannot_buy_a_free_line`（合成檔紅綠自證：修前該手法降價、修後計價不變）。

---

## §3 條文二 — unparseable 必須 fail-loud

**§2.1** 分類器對讀檔失敗／`SyntaxError` 的契約是「跳過並標記、三桶歸零」（ADR-XPLAT-012 條文一 §4）。計價器**不得**照抄那個 0：`count_loc()` 一律拋 `UnparseableSourceError`（`ValueError` 子類）。

**§2.2 WHY**：回 0 會讓「語法錯誤」變成**零成本**，也就是「最省預算的手法是把檔弄壞」——那是本案要關的套利門的鏡像版本，失效方向比破線更糟。

**§2.3** 呼叫端二擇一，兩條都會留下痕跡：①讓例外傳播（`build_reports()`／`root_tools_reports()` 走這條，逐檔迴圈 fail-loud）；②翻譯成一筆具名違規／WARN（PostToolUse hook `loc_budget_check.py` 走這條，exit 0 且經 stdout JSON `additionalContext` 出聲——DEF-200-447：CC 只認 0／2，exit 1 會顯示成 hook error，而只改 `return 0` 則對 CC 靜默；靜默等於「剛寫壞的檔沒有任何訊號」）。

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

**§3.6 🔴 訂正（R100 §E-4；四方複審裁決 `decouple_buffer_from_repin`，本輪已修憲落地）**：上面「出口只有一個且永遠開著」那句把 `--update` 描述成「沒收陳舊餘裕的出口」——**這句話改前是錯的**。改前 `cap = int(baseline × TOTAL_INCREASE_LIMIT)` 一路即時算，`--update` 動 `baseline` 就**順帶**動 `cap`；當回合實測 `17032×1.2=20438` → 執行一次 `--update` 後 `17079×1.2=20494`（**+56**），語意是加碼而非沒收。修法與現況＝**§10 條文五**（cap 與 baseline 重釘解耦）。**本節這句「出口」描述在條文五落地並經一次 `--repin-cap` 獨立審核之前，實務上仍會連動 cap**——見條文五 WHY 段的殘留說明，勿誤讀為已完全解耦。（R210 註：第一次 `--repin-cap` 已於 R102 執行，見 §7 U10；本句寫成當時的現況。）

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

> **R210 註記**：本節為落地當時的缺口原樣保留；各項結局以 §7 U1～U10 為準。

1. **ADR-XPLAT-012 條文六的四方複審尚未補行**。掌舵者裁決「Phase 2 三個方向全做」並授權實作，但條文五 §1 逐字要求「任何要把這些欄位轉為阻斷判準的提案，是另一次修正案，須另走條文六的四方複審程序（不可用『反正資料都印出來了』的理由直接生效）」。本案的〈狀態〉因此是 **Proposed 而非 Accepted**。逐項解鎖條件見 §7。（R210：四方複審已於 2026-10-09 補行，見 §7／§7.1。）
2. **Phase 2 方向 (b)(c) 未落地**，交棒收尾單人窗口／Stage 2。（R210 現況：(b) 分軌計價已於 R116 落地；(c) 依 R110 D-4 降為觀測欄、只印不擋——本 ADR 不含 (c) 轉阻斷，見第 7 項。）
3. **全庫自陳站點未逐一改寫**。普查已於否決權複審 M3 重建（原表的單行 grep 至少漏 7 列，方法與訂正後筆數見 §8）。那些站點在新計價下**不再有套利效果**，但註記文字仍在講一個已經不成立的理由 ⇒ 下一個讀者會照著做一件已經沒有好處的事。本輪已訂正 2 支（`tools/lib/hook_wiring.py:4`、`AutoClaude/autoclaude/models/escalation.py:79`，理由見 §8.3），其餘交棒。（R210：其餘站點不逐一改寫、視為封閉史料，依據與重開症狀見 §7 U7 與 §8 表頭。）
4. **`tools/tests/test_block_destructive_git_r83.py::TestTheHookStaysInsideItsLocTier` 的早期預警靈敏度下降**（該檔由 750/750 變成 558/750）。它現在守的是「判斷邏輯量不得長到 tier 之外」——那才是 tier 本來想守的東西，但「再加一行就破線」這個訊號沒有了。已逐字寫進該類 docstring。
5. **`AutoClaude` tier 與根層 tools tier 的預警帶雙雙變空**，且那三個 `*_WARN_MARGIN` 常數在新值域下是否仍是合適的門檻，**本案未重新評估**。否決權複審 M5 已把記帳切開（原本「非空」與「逐層篩選語意」擠在同一支測試裡，於是那兩層退化成空集合互比卻仍掛在「真實資料驗收」名下）：
   - `test_real_repo_bands_match_production_output`：**只驗一致**（production == 獨立推導），刻意允許任一層為空。
   - `test_the_warn_band_machinery_has_a_live_population`：**只驗母體**（三層聯集非空），並把逐層筆數印進失敗訊息，讓「哪一層在承重」看得見。
   - `test_the_semantic_owners_delegated_to_by_the_real_data_lock_still_exist`：把「語意由合成鎖負責」這句委派**釘住**——合成鎖被刪／改名即紅，否則那句委派是散文。
   - 篩選語意本體仍由本檔既有的**合成資料**鎖負責（`_SEMANTIC_OWNERS` 具名五支），它們對空層照樣有牙。
6. **🔴 行數制計價的共有殘留：多語句擠一行（`a=1;b=2;c=3`）在任何行數制下都是省錢的**（三個 statement 只算一行）。這**不是本案開的門**——舊計價下同樣省錢，而且它同時**減少 raw 行數**，所以在 raw-line 棘輪那一軸也是省的。本案不宣稱關掉它。**擋它的唯一現成工具是 ruff E701/E702，而 `.claude/hooks/`（受 `root_tools` tier 計價）沒有任何 ruff 閘門**——`AutoClaude/` 側 pre-commit 的整檔 ruff 不涵蓋根層 `.claude/hooks/` 與 `tools/`。交棒選項：①把 E701/E702 接到根層 pre-commit 的 `.claude/hooks/`＋`tools/` 面（本包不做：pre-commit dispatcher 與 workflow 不在本包授權檔案面，且該類鎖的常數／史料／消費端分屬不同持有面＝鐵律七）；②在 `guard_line_taxonomy` 加「一行多 statement 起點 ⇒ 按 statement 數計價」的判準（射程更大、假紅風險未量測，須另案立案）。**未做選擇＝缺口原樣登記。**（R111 訂正兩件：ⓐ本段「不涵蓋根層 `.claude/hooks/` 與 `tools/`」的 `tools/` 半句寫下時已過時——`ruff check tools/` 自 R69 起就有 pre-push 快層④＋root-infra-ci 第 16 道兩執行者，見 `tools/ruff.toml` 檔頭；ⓑ`.claude/hooks/` 半句自 DEF-200-209 落地起不再成立——選項①已以 `.claude/ruff.toml`（extend）＋兩執行者擴射程落地，E701/E702 隨 select `E` 生效、存量債 16 筆同批清零；`S102` 刻意不在本次射程（select 動一字兩樹連動，屬 DEF-200-217 E2 軸）。原文照舊保全。）

7. **條文四的 5 輪時效是同族的輪號時鐘**（R210 登記、不處置）：自 R129 起 `_PHASE2_REVIEW_LOG` 連續十三列全是 [提案]／[維持觀察] 輪流重登、無一列 [落地]，`_PHASE2_DUE_ROUND` 與 U9 退役前的到期輪同為 213。本次 Accepted **不處置**：該時效是 ADR-XPLAT-012 條文五 §6 的字面（5 輪），退役它須修 ADR-XPLAT-012 本身，另案。處置症狀（事件驅動、無日期）：(c) 觀測欄出現可據以轉阻斷的訊號，或下一次 [時效逾期] 紅燈。[時效逾期] 紅燈的**合法回應＝提 ADR-XPLAT-012 條文五 §6 的修憲案**（Architect 鏡方向：退役 5 輪視窗、明文 (c) 永久為觀測欄、轉阻斷須暴露證據）；在 `_PHASE2_REVIEW_LOG` 再登一列不算處置（連續十三列 [提案]／[維持觀察] 交替即為證據）。

---

## §7 解鎖條件（Proposed → Accepted 的可勾稽清單；否決權複審 M6）

🔴 **本案的事實與風險，原樣寫在這裡**：**機械物已先上生產、程序後補**。`count_loc()` 的新計價已在閘門實際生效（`total` 20426 → 16483、`cap` 20438 不變 ⇒ 餘裕由 12 行變成四位數並已被後續包消費），而 ADR-XPLAT-012 條文六要求的四方複審**當時尚未補行**（R210 已補行，見 §7.1）。承擔的風險，照實列：

- **四位數餘裕已被消費**：若複審否決本案、要回退計價規則，回退當下 `total` 會跳回兩萬出頭並**超過 cap**，屆時已經寫下的行沒有地方去 ⇒ 回退的實際成本隨每一輪遞增。這是「先上生產」最貴的一項，且**會自己長大**。
- **§4 條文三的零緩衝豁免已生效**（`.loc_baseline` 未重釘），其到期載體 `_PRICING_CHANGE_EXEMPT_ROUND` 是**單向**的（只准調小），設計上不容許用「複審還沒過」當延期理由。
- **已有兩道判準改寫過的假數字被複審抓到**（§1.4 的「全樹零檔上升」、§1.5 的「門在值域上關閉」）——兩者都是在**沒有**四方複審的情況下寫進判準 docstring 並通過閘門的。這件事本身就是「程序後補」的實測代價。

🔴 **R210 補行結果（現查 2026-10-09，非常數）**：
- 回退成本：舊尺下 AutoClaude/autoclaude 總量 21388 行、高於 cap 20438（超出 950 行；R100 當時 20426，餘 12）⇒ 回退已不可行。本次四方審查因此是**追認＋訂正**，不是上線與否的決定。
- 零緩衝豁免：已於 R102 重釘 baseline 並回填 provenance（`--json` 的 cap_basis_pinned 為 true、baseline_policy_version 與 policy_version 同值）；下一次計價規則變更時 §11 的 provenance 鎖會轉紅。
- 假數字：SA 鏡重測 §1.4 母體宣稱——閘門計價母體 370 支中新值高於舊值者 0 支；全樹 5640 支中 2 支（即 §1.4 表那兩檔）；條文一 §1.4（M1）補丁前後斷言行數不同者 0 支（§1.4 末段的基準是 M1 前後，與 §1.4 表的 pre-013 vs 現行不同，兩處各自寫明基準）。

| # | 解鎖條件 | 現況（R210 現查） | 勾稽方式 |
|---|---------|------|---------|
| U1 | Architect 獨立審查 APPROVE | ▣ 已記錄（§7.1）：由獨立 Architect 鏡投票；主控（U7／U9 處置的提案者）不投票、只記錄提案 | §7.1 具名記錄 |
| U2 | SA 獨立審查 APPROVE | ▣ 已記錄（§7.1）：CONDITIONAL→APPROVE，條件 C1～C6 於同一 commit 落地、由 QA 核對 | 同上 |
| U3 | SD 獨立審查 APPROVE | ▣ 已記錄（§7.1）：CONDITIONAL→APPROVE，條件 C1～C4 於落地 diff 成立、由 QA 核對 | 同上 |
| U4 | QA 獨立審查 APPROVE | ▣ 已記錄（§7.1）：整合後零信任複審，含 SA C1～C6 與 SD C1～C4 逐條核對 | 同上 |
| U5 | §6 缺口 ⑥（多語句擠一行 × `.claude/hooks/` 無 ruff 閘門）已選擇並落地或明文接受 | ▣ 兩軸全收：R111（DEF-200-209）E701／E702 隨 select `E` 生效；R116 補 S102。R210 現查 `.claude`／`tools`／`AutoClaude` 三棵樹的 `ruff check --show-settings` 皆列 E701／E702／S102，合成探針（`a = 1; b = 2`＋`exec(__doc__)`）rc=1 | `ruff check --no-cache --show-settings <檔>`；於 tools/tests 下 `python -m unittest test_subprocess_encoding_hygiene.TestRootToolsLintPolicy`；執行者＝pre-push 快層④／root-infra-ci 第 16 道 |
| U6 | §6 缺口 ⑤（三個 `*_WARN_MARGIN`）已重新評估 | ▣ 已核准（R116／R110 D-5）。R210 現查三層預警帶筆數 tier 0／special 7／root_tools 4（R116 為 0／7／2），門檻 10／6／5 維持現值，未達「母體大幅變動」 | `python AutoClaude/tools/check_loc_budget.py --json` 的 tier_warn_band／special_warn_band／root_tools_warn_band |
| U7 | §8 自陳站點處置方針已定 | ▣ **方針＝不逐一改寫、視為封閉史料**（R210 取代 R116／D-5「逐一改寫」）：現查 21 處未訂正、無機械消費者、來源（TIER-WARN 指引）已於 R100 刪除、新尺下 `#` 與 docstring 同價、改寫須動 15 檔含 3 支守衛面；理由、重開症狀與現查指令見 §8 表頭 | §8 表頭；重開症狀＝條文六 provenance 鎖轉紅（計價規則再變更）時須附 §8.1 判準的現查普查 |
| U8 | R100 §E 五筆（E1~E5）四方重投票已完成 | ▣ 全數完成：E1＝§9（R101）；E2＝DEF-200-209 fixed@R116（S102 軸）；E3＝§11 判準改寫（R101）＋資料面回填（R102，6fea8a3b）；E4＝§10 機制（R101）＋第一次 `--repin-cap`（R102，6fea8a3b）；E5＝DEF-200-217 fixed@R126（sys.path 洗白＋裸名判準） | `--json` 的 policy_version 與 baseline_policy_version 同值、cap_basis_pinned 為 true |
| U9 | §9 四支 `[ROOT-TOOLS]` 檔的技術債已拆到舊尺不破線（或四方明文接受長期掛帳） | ▣ **四方明文接受長期掛帳，到期輪機制退役**（R210 取代 R116／D-5「真拆＋到期輪保底」與 R121 的具名展延）；事實、裁決與守衛射程見 §9.5 | §9.5；現行尺閘門 `python AutoClaude/tools/check_loc_budget.py --json` 的 root_tools_violations 與 special_violations（R210 現查皆空；hook_wiring.py 已入 SPECIAL_FILES，違規落在後者） |
| U10 | §10 條文五落地後的第一次 `--repin-cap` 已執行 | ▣ 已執行（R102，commit 6fea8a3b）：cap_basis_pinned 為 true、cap 基準 17032、cap 20438（與 R100 同值，零加碼）。書面雙簽紀錄＝該 commit 訊息（四方獨立審查一致核准）與 R102 交棒書，無獨立簽核文件 | `python AutoClaude/tools/check_loc_budget.py --json` 的 cap_basis_pinned |

🔴 **U8 與 U1~U7 是兩個不同的四方複審批次，不得互相頂替**：U1~U7 是 ADR-XPLAT-012 條文六要求、對整份 ADR-XPLAT-013 的原始複審；U8 是 R100 §E 節唯讀交件觸發、範圍限定在五筆新發現（E1~E5）的補充複審（§9.1 已裁決 E1、§5.2 已裁決 E4、§6.2 已落地 E3 的 provenance 判準改寫）。U8 完成不代表 U1~U7 完成，反之亦然——本節〈狀態〉的 Proposed→Accepted 判準仍是**兩批皆全數通過**。

**四方全數 APPROVE 且 U5~U10 有明文結論**——此條件已於 2026-10-09 滿足（§7.1），〈狀態〉已由 Proposed 改為 Accepted。（歷史：機械物 R100 先上生產、程序 R210 後補；補行期間的回退成本見本節開頭。）U8 與 U1~U7 是兩個不同批次、不得互相頂替的區分照舊保留（兩批現皆已完成）。

### §7.1 四方獨立審查具名記錄（ADR-XPLAT-012 條文六；補行於 2026-10-09，R210）

| # | 角色 | 審查者 | 結論 | 日期 | 範圍 | 條件／保留意見 | 證據 |
|---|------|--------|------|------|------|----------------|------|
| U1 | Architect | Claude Sonnet 5.5 子代理（Architect 鏡，唯讀；提案者＝主控 Claude Fable 5.1，不投票） | CONDITIONAL→APPROVE | 2026-10-09 | 全 ADR＋落地 diff（U7／U9 處置、時鐘改源、DEF-101-887 修法） | 同意 U7 封閉史料、U9 退役到期輪、時鐘改源；條件（QA 核、主控落地）：C1 U6 special 改現查值；C2 提交前無佔位符；C3 證據〈三〉#6 載明 SC-10 復活；C4 §6 第 7 項補逾期紅燈＝修憲非重登 | CrossPlatform_R210_Debt_Closure_Final_Evidence.md〈一〉 |
| U2 | SA | Claude Sonnet 5.5 子代理（唯讀；R210 包 C） | CONDITIONAL→APPROVE | 2026-10-09 | 條文一～六與活體碼一致性（現查 9 項）；U5～U10 勾稽；U7／U9 處置的獨立判斷 | 條件 C1～C6 於同一 commit 落地，由 QA 末棒逐條核對（SA 未重審） | 同上 |
| U3 | SD | Claude Sonnet 5.5 子代理（唯讀；R210 包 D） | CONDITIONAL→APPROVE | 2026-10-09 | 機制設計與遷移步驟（U9 退役參照稅、U7 處置、守衛射程、條文三／五載體現況） | 條件 C1～C4 於落地 diff 成立即計 APPROVE，由 QA 核對（SD 未重審） | 同上 |
| U4 | QA | Claude Sonnet 5.5 子代理（零信任複審；整合後） | CONDITIONAL→APPROVE | 2026-10-09 | 整合後 diff 全查＋逐條核對 SA C1～C6 與 SD C1～C4（全數成立）；A／B／主控的突變驗紅重做；總結帳以獨立分類器重算全相等 | 對翻 Accepted、U7 不逐一改寫、U9 退役投贊成；條件（主控落地並親跑）：P2-1 DEF-101-887 修法對 nightly 自寫檔誤判 dirty（真實語料重現）須修、P2-2 佔位符清零、P2-3 表② 回填與最終樹全套全綠 | 同上 |

SA 明文表態：同意 (1) U7 不逐一改寫（現查 21 處、零機械消費者、來源已刪、改寫需動 3 支守衛面檔）；(2) U9 以「四方明文接受舊尺長債」結案並退役到期輪機制（到期輪 18 次展延零償還、四檔舊尺 over_by 149→187→354、舊尺指標可由 docstring 改 `#` 歸零而與條文一矛盾、全庫無任何舊尺讀者）。SA 對主控提案的修正：E5 由 DEF-200-217 結案而非 DEF-200-207；替代守衛須如實寫觸發範圍；條文四的輪號時鐘須記錄（§6 第 7 項）。

SD 明文表態：U9 退役的遷移走「刪除＋把引用改純文字」（刪常數、旗標、lookahead 界與凍結孿生、判準函式與五支測試；鎖檔凍結字串 4 處與交棒書 5 處去反引號；不得在任何 tracked 檔寫出該旗標被設為真的字面——最新交棒書的 absent-if 錨）；守衛射程須如實寫「路徑觸發型」且 hook_wiring.py 看 special_violations；§9.3 第 3 點須同批推翻，否則與帳本 DEF-200-207 的 fixed 矛盾。

---

## §8 交棒清單（自陳「刻意寫成 `#` 以避開 count_loc」的程式碼站點）— **普查已重建（否決權複審 M3）**

**處置方針（🔴 R210 四方複審取代 R116／`AutoSDD_Adjudication_Record_R110.md` §1.4 D-5「逐一改寫」）**：本節是**封閉的歷史清單，不逐一改寫**。理由：①產生它的來源已刪——那批註解多半逐字引用 check_loc_budget 自己印的「docstring 行會被 count_loc 計入」指引，該指引隨本 ADR 落地已刪（R210 現查：現行檔 0 命中；命中行逐行 git blame 皆早於 R100 計價換尺 commit，其後無新增）；②新尺下 `#` 與 docstring 同為免費，照著讀不產生任何套利或預算效果，殘餘風險僅是「讀到過時理由」；③無任何機械消費者（現查：`git grep -n -E "待訂正|loc-pricing-assertion-only|ADR-XPLAT-013-loc" -- '*.py' '*.sh' '*.ps1' '*.yml' '*.json'` 0 行）；④逐一改寫要動 15 檔、跨兩個子專案，其中 3 檔在根 CLAUDE.md〈守衛面准入〉清單上，換不到任何守衛效益。**重開症狀（事件驅動、無日期）**：下一次修改條文一的計價規則（POLICY_VERSION 遞增；§11 的 provenance 鎖屆時轉紅）時，該修正案須在證據檔附本節 §8.1 判準的現查普查；未附＝該修正案不得 Accepted。現查（R210）：§8.1 緊判準（窗 3、排除 tests/）命中 23，扣 2 處已訂正 ⇒ 21 處未訂正；§8.2 表的行號是 R100 快照、已大量漂移，**僅供考古**。

### 8.1 原表怎麼漏的（方法訂正）

原表的 18 列是用**單行 grep** 建的，複審實測至少漏 7 列。三種漏法：

1. **跨行寫法**：`散文寫在**註解**裡（註解不計` 在第 556 行斷句，`count_loc` 在下一行 ⇒ 單行 grep 對它結構性失明。
2. **不寫 `count_loc` 只寫 `LOC`**：`（`#` 不計 LOC，內容一字未改）` 這種形態整批漏掉。
3. **詞彙不在原詞表**：真實語料寫的是「**計** docstring 行、**不計**註解行」，而 M3 指定的詞表（跳過／免費／排除／計入）不含「計／不計」——**指定詞表本身也不夠**，照實記。

重建後的判準（跨行、窗 3 物理行；三者須同段命中）：主詞 `count_loc｜check_loc_budget｜LOC` **∧** 計價動詞 `計入｜不計｜免費｜排除｜跳過｜只計｜零成本｜吃掉` **∧** 載體字 `docstring`；另跑一次把載體放寬為 `docstring ∪ 註解`（窗 8）補抓只提「註解」的形態。

**實測筆數**：緊判準 `.py` 命中 **28**；放寬載體後 **40**，多出的 12 筆中真站點 3（`tools/lib/skip_group_policy.py:556`／`:801`、`tools/lib/quota_meter.py:377`），其餘 9 為假陽性（掃描器自己在講「怎麼剝註解」）。扣掉假陽性與「已是新規則描述」的站點後，**真的自陳舊規則的站點＝25**（原表 18 ＋ 漏掉的 7）。

### 8.2 分類後的清單

> R210：本表「待訂正」為 R100 時點的標記；依本節表頭處置方針現為封閉史料、不再訂正（行號僅供考古）。

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

---

## §9 揭露與技術債追蹤 — 換尺同時把四支 `[ROOT-TOOLS]` 違規檔由 4 筆變 0 筆（R100 §E-1；四方複審裁決 `disclose_and_track_debt`）

**§9.1（事實，四方複審已裁決＝揭露＋掛帳，不撤尺）**：R100 收尾窗口的四方唯讀複審（`docs/06_quality/CrossPlatform_R100_Scan_Findings.md` §E-1）發現本 ADR 落地當下**未揭露**一件事——條文一的計價尺變更，同一次 commit 內**同時**把下列四支檔的 `[ROOT-TOOLS]` 分級違規由 **4 筆變成 0 筆**。四方重投票的結論（對照另一候選 `revert_ruler_change`）：**揭露＋掛技術債**，不撤尺——理由是撤尺會讓 §9.3 已釋出並被後續包消費的餘裕整批沒收（同 §7 開頭〈本案的事實與風險〉的既有分析），且四支檔的違規本質是「舊尺本來就沒有餘裕可以吸收後續合法工作」而非「新尺判準本身錯誤」（條文一 §1.4 已證新尺對現況母體零假紅）。（R210：本節「揭露＋日後真的付掉」的操作性子句已由 §9.5 取代。）

**§9.2（逐檔對照——R100 落地當下 vs 本輪（R101）現查，皆為當回合實測）**：

| 檔案 | tier（budget） | R100 落地當下（HEAD，舊尺） | R101 現查・舊尺 | R101 現查・新尺 |
|------|---|---:|---:|---:|
| `tools/lib/quota_meter.py` | guardrail_lib（400） | 399（貼線，over=0） | **462（over=62）** | 310（over=0） |
| `tools/session_resume_planner.py` | guardrail_cli（750） | 750（貼線，over=0） | **789（over=39）** | 744（over=0） |
| `tools/lib/hook_wiring.py` | guardrail_lib（400） | 395（over=0） | **428（over=28）** | 398（over=0） |
| `tools/lib/quota_gate.py` | guardrail_hub（500） | 500（貼線，over=0） | **520（over=20）** | 366（over=0） |

🔴 **R116 訂正（D-5，7 輪後再現查，惡化持續）**：現查舊尺 over_by 合計已由 R101 的 149 進一步惡化為 **187**（`quota_meter.py` over=67／`session_resume_planner.py` over=45／`hook_wiring.py` over=28／`quota_gate.py` over=47），較 R108 提案當時的 186 又 +1。**零償還、連續 8 輪方向持續惡化**的實況不變（見裁決存證 `AutoSDD_Adjudication_Record_R110.md` §1.4 D-5：「U9 明文掛帳是次佳，真拆才還債」）。本輪（DEF-200-211 落地批）**先落地到期輪常數作機械保底**——_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=121（載體＝`tools/tests/test_adr_xplat001_c1c2_lock.py::root_tools_debt_due_problems()`，到期而未清償即紅），真拆本身尚未做，交下一收尾單人窗口。

🔴 **讀法**：R100 落地當下這四支檔**在舊尺下已經貼著上限、餘裕為 0**（不是「還有空間」）；R100→R101 之間的後續合法工作（在新尺顯示的四位數餘裕下進行）已經讓四支檔在**舊尺下**實際**破線**（超額 20～62 行）。這正是「換尺同時掩蓋既有違規」的技術債本體：**這四支檔現在的行數，若沒有本次計價尺變更，在條文一落地當下就已無法通過**，後續增加的行更是舊尺下的直接違規。新尺下四支皆 over=0，是本 ADR 存在的直接效果，不是巧合。

**§9.3（技術債義務——不得永久免費搭便車）**：四支檔的處置方針比照本檔既有的 `[ROOT-TOOLS]`／`guardrail_hub` 違規訊息一貫要求（`check_loc_budget.py` 的既有措辭：「破線後不是調高預算，而是拆職責／抽共用模組；真的不可壓縮才具名加進 `SPECIAL_FILES` 的 raw-line 棘輪」）——**新尺的貼現不改變這條既有紀律**：

🔴 **R210**：本節第 1～4 點（含 R116 訂正段）已由 §9.5 取代（第 1 點「先現查舊尺 over_by」亦不再是任何人的義務：§9.5 事實 (c)(d)）；原文照舊保全＝寫成當時的現況。

- 日後任一支檔要新增斷言行之前，先現查該檔在**舊尺**下的 over_by（現查：`git show HEAD:tools/lib/guard_line_taxonomy.py` 判準不變的前提下，用改前 `count_loc` 邏輯——空行與行首 `#` 免費、其餘計價——手算或用合成腳本量；本 ADR 不為此另建工具，理由是舊尺已廢，重建它只服務這一項稽核）。
- **目標＝拆職責／抽共用模組，把四支檔的邏輯量降到舊尺（改前判準）下亦不破線**，而不是繼續依賴新尺的便宜計價無限期加碼。這是 disclose_and_track_debt 決策的字面意思：揭露＋要求日後真的付掉，不是揭露完就當作合法額度。
- 追蹤載體＝ [`docs/06_quality/AutoSDD_Defect_Log.md`](../../06_quality/AutoSDD_Defect_Log.md) 既有未結列 `DEF-200-207`（同主題「續報 §E-1/3/4」欄位，R101 已追加本節四檔對照與義務描述——不新開列，理由見該列 R101 追記段的「未結列僅剩 0 格」實況）。該列在四支檔任一支被拆到舊尺不破線之前，不得標記與本項相關的部分為 `fixed`。
- 🔴 **R116 訂正（D-5）：本節「不設具體到期輪」的立場已由裁決推翻**——`AutoSDD_Adjudication_Record_R110.md` §1.4 D-5 明文「U9 真拆 −186 行為目標＋同批先補到期輪常數作機械保底」。到期輪常數已落地：_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=121（`tools/tests/test_adr_xplat001_c1c2_lock.py`，形狀比照 `_PHASE2_REVIEW_LOG`／`_REPIN_NET_CAP_DUE_ROUND` 既有紀律：到期而未清償即由 root_tools_debt_due_problems() 轉紅，出口二擇一——真拆清償或由下一次複審具名展延，刻意不留無條件延期參數）。**這是機械保底，不是「已真拆」的證明**：四支檔本身本輪未動一行，187 行的 over_by 原樣保留，到期輪 R121 前必須有人真的拆完，否則到期即紅。

**§9.4（不涵蓋）**：本節不涵蓋 R100 §E-1 同時指出的「母體級 −22.3%／per-file violations 4→0／預警帶 17→7」等群體統計，那些數字已完整落在 `CrossPlatform_R100_Scan_Findings.md` §E-1，本節僅承接「四支具名檔」這一個可勾稽義務，避免重複維護同一組數字兩個家。

**§9.5（R210 裁決——舊尺長債：四方明文接受，到期輪機制退役；取代 §9.1 操作性子句與 §9.3 第 2～4 點含 R116 訂正段）**

**事實（R210 現查）**：(a) 到期輪常數自 R116 立案（到期 R121）起，經 18 次 commit 層級的具名展延推至 R213，其中多次逐字寫「已達上界」；真拆 0 次。(b) 四支檔舊尺 over_by 合計由 R101 的 149、R116 的 187 變為 354（quota_gate 184／session_resume_planner 65／quota_meter 62／hook_wiring 43；hook_wiring 已於 2026-09-09 起走 SPECIAL_FILES raw-line 棘輪出口）；債的邊界早已不是四支——根層母體舊尺下超過各自 tier 預算者 14 支、合計 1,589 行，現行尺下 0 支。(c) 到期輪判準只比對一個手動布林與輪號，從不計算 over_by；全庫沒有任何程式碼讀取舊尺 over_by。(d) 舊尺 over_by 量的主要是 docstring／裸字串敘事行（條文一宣告為免費）；把 docstring 改成 `#` 註解即可在不動任何斷言行的前提下歸零（§1.1／§1.3 已量過同一轉換），且 §11 §6.3 禁止跨尺直接比大小——該指標正是本 ADR 要關掉的那類可被套利的度量。(e) 到期輪是輪號型義務，與掌舵者 2026-10-07「不製造日期／輪號義務、只由症狀驅動」原則抵觸，且會在下一個重釘輪再轉紅、逼出第 19 次展延。

**裁決**：Architect 鏡／SA／SD／QA 明文接受四支 `[ROOT-TOOLS]` 檔的舊尺長債；同一 commit 刪除到期輪常數、清償旗標、lookahead 界與其凍結孿生、判準函式與其紅綠測試（實作清單與參照稅見 CrossPlatform_R210_Debt_Closure_Final_Evidence.md）。本節**取代** §9.1／§9.3 中「揭露＋日後真的付掉」的操作性子句與 §9.3 第 2～4 點（目標＝降到舊尺下不破線；追蹤載體不得標 fixed；R116 訂正段的到期輪保底），並推翻 R110 D-5 對 U9「真拆 −186 行」的裁決與 R121 的具名展延；DEF-200-207 因此 fixed@R210。

**現行守衛（不新增任何機制）**：現行尺 LOC 閘門 `AutoClaude/tools/check_loc_budget.py`（rc=1 即阻塞）——quota_gate.py／quota_meter.py／session_resume_planner.py 由 ROOT_TOOLS_TIERS（500／400／750）判，違規在 JSON 的 root_tools_violations；hook_wiring.py 已入 SPECIAL_FILES（raw-line 棘輪），違規在 special_violations；非阻塞預警在 root_tools_warn_band／special_warn_band（R210 現查：兩個 violations 皆空；warn band 4 支，含 quota_gate 餘 5 行、session_resume_planner 餘 4 行）。閘門紅時訊息即要求「先拆職責／抽共用模組，不可壓縮才具名進 SPECIAL_FILES」。

**射程（誠實劃界）**：自動執行者只有 AutoClaude 子專案 pre-commit／pre-push leg（根 dispatcher 於變更含 `AutoClaude/` 時才進該 leg）、autoclaude-ci.yml 的 test／claude-md-budget job（push／PR 的 paths 含 `AutoClaude/**` 與 `tools/lib/**`，不含 `tools/session_resume_planner.py` 與 `.claude/hooks/**`）、本機 nightly（mac 的 autoclaude_gate stage、Windows 的 local-ci-gate stage）、以及兩支 compat-ci 的 nightly-full 深度回歸 job（排程／手動觸發、continue-on-error 非阻斷，皆經 local_ci_gate 呼叫）；根層 pre-push 與 root-infra-ci 不跑它。⇒ 純根層改動撐破預算時不會在該次 push 當場紅，而是在下一個上述入口才紅（最長約一天）。這是已知且接受的延遲型射程，**未新增守衛**（R197〈守衛面准入〉：零暴露證據），登記為 P4 理論洞。

**重開症狀（事件驅動、無日期）**：①root_tools_violations 或 special_violations 非空且解法是把某檔具名加進或調高 SPECIAL_FILES（走逃生口而非拆職責）⇒ 該次裁決同時判「拆 vs 進棘輪」；②POLICY_VERSION 遞增（計價規則再變更）⇒ §11 的 provenance 鎖轉紅，該修正案須重評四檔對新尺的餘裕；③出現一次「純根層 push 撐破 [ROOT-TOOLS] 預算、事後才被別的 push 或 nightly 發現」的真實事件；④有人提議回退計價規則。

**本節不涵蓋**：ADR-XPLAT-012 條文五 §6 的 Phase 2 視窗（§6 第 7 項）與 `_REPIN_NET_CAP_DUE_ROUND` 各自仍是輪號型到期義務（後者每次兌現都真的把 cap 降到目標，不是同型永動源），各走各自 ADR 的程序。

---

## §10 條文五 — cap 與 baseline 重釘解耦（R100 §E-4；四方複審裁決 `decouple_buffer_from_repin`）

**§5.1（缺陷本體）**：改前 `cap = int(baseline × TOTAL_INCREASE_LIMIT)` 全程**即時**由 `baseline` 算出、從未獨立持久化。於是任何一次 `--update`——不論目的是 ADR-SD07-001 §6.3 的核准成長，還是本 ADR 條文四的「計價規則變更豁免」出口——都會**順帶**把 20% 緩衝（cap）一起抬高，即使呼叫者只想單純把 `baseline` 對齊當回合實測、完全沒有申請新增額度的意圖。R100 §E-4 實測：`17032×1.2=20438` → 執行 `--update` 使 `baseline=17079` <!-- adr-measurement-historical: R100 §E-4 報告當時的實測快照，描述「若跑 --update 會怎樣」的反事實情境，非本 ADR 現況 --> 之後 `→20494`（**+56**）。§4 條文三與 `pricing_exemption_problems()` 皆把這個出口描述成「沒收陳舊餘裕」，實際效果是加碼——這是語意反轉，屬修憲範疇（非單純改程式碼能解，四方複審已裁決見 §5.2）。

**§5.2（決策——與另一候選 `find_real_tightening_exit` 的取捨）**：四方複審裁決 `decouple_buffer_from_repin`：**不**另尋一個「真的會收緊」的出口取代 `--update` 的描述，而是把 cap 的 20% 緩衝基準從「即時派生自 baseline」改為「獨立持久化、需另一個明確步驟才能調整」的量。`--update` 從此**只**動 `baseline`（供條文三～四的豁免與 §6.3 成長校準比對用），不再是移動 cap 的唯一或隱性手段。

**§5.3（機械載體）**：

| 載體 | 位置 | 語意 |
|------|------|------|
| `CAP_BASIS_FILE`（`.loc_cap_basis`） | `AutoClaude/tools/check_loc_budget.py` | cap 的獨立審核基準，與 `.loc_baseline` 是**兩個檔** |
| `read_cap_basis()` / `write_cap_basis()` | 同上 | 讀寫入口各自獨立於 `read_baseline()` / `write_baseline()` |
| `--repin-cap` CLI 旗標 | 同上 `main()` | 唯一能移動 cap 基準的動作；與 `--update` 是兩個不同旗標，不得同義使用 |
| `cap_basis` / `cap_basis_pinned` | `--json` payload | 機讀揭露目前 cap 是「已獨立釘住」還是「仍沿用 baseline 的啟動預設」 |

**§5.4（🔴 落地當下的殘留狀態——誠實揭露，勿誤讀為「已完全解耦」）**：本輪（R101）**只落地機制本身**，尚未執行第一次 `--repin-cap`（那是「獨立於 baseline 重釘的審核步驟」，依 ADR-SD07-001 §6.2/§6.3 的既有紀律仍須 Architect + SD 雙簽核准後人工執行，非本包職權）。`.loc_cap_basis` 檔案目前**不存在**，故 `read_cap_basis()` 回 `None`、`check()` 退回沿用 `baseline` 當 cap 基準（`cap_basis_pinned=False`）——這個退回狀態下的行為與改前逐字相同（`cap = baseline × 1.20`），**零回歸、cap 數值本輪未變（仍是 20438）**。也就是說：**在有人執行第一次 `--repin-cap` 之前，`--update` 實務上仍會間接移動 cap**，§4 條文三的「出口」描述在那之前仍不完全準確。這件事本身即技術債，追蹤載體同 §9.3——掛在 `DEF-200-207`。（R210 註：第一次 `--repin-cap` 與 `--update` 已於 R102（6fea8a3b）依序執行——先 `--repin-cap`（cap 基準釘 17032，cap 維持 20438）、後 `--update`（baseline 重釘並回填 provenance）；現查 cap_basis_pinned 為 true。上文「檔案目前不存在」寫成當時的現況。）

**§5.5（下一步，交棒）**：Architect + SD 雙簽核准後，執行一次 `python AutoClaude/tools/check_loc_budget.py --repin-cap`，把 cap 基準釘為當時的 `baseline`（**不是** `total`——釘的是「已核准的成長上限起點」，不是「今天程式碼實際多重」，兩者概念不同，混用會重新引入 baseline↔cap 的耦合）。此後每次 `--update`（含條文三～四的豁免出口）都不再連動 cap；要調整 cap 須再跑一次獨立的 `--repin-cap`，且應比照 §6.2 的雙簽紀律書面留痕。（R210 註：已於 R102 執行，見 §7 U10。）

---

## §11 條文六 — `policy_version` 標記與通約規則（R100 §E-3；版號本身的修憲＋ provenance 判準改寫，本輪由 E3/DEF-200-208 一併落地）

**§6.1（缺陷本體）**：`count_loc()` 的計價規則本身已由本 ADR 改變（條文一），但 `check_loc_budget.py` 的 `--json` payload 裡 `policy_version` 欄位在本 ADR 落地當下**仍是舊值** `"v2-tiered+sd08-special"`（R100 §E-3「附帶一」逐字指出「本輪 diff 對該行零命中」）。版號沒跟著換，等於「量到的行數是用哪一把尺量的」這件事在資料面上不可辨識——這正是 `pricing_exemption_problems()` 用同一個不等式 `baseline > total` 表達「尚未重釘」與「total 已長過陳舊 baseline」兩件相反事情、導致到期鎖永久靜音（R100 §E-3 主牙）的根本前提之一：兩個數字（`.loc_baseline`＝舊尺釘的、`total`＝新尺量的）被直接相減比大小，卻沒有任何欄位讓人先確認兩者是否可比。

**§6.2（本輪落地——版號本身 ＋ provenance 判準改寫，兩者皆已完成）**：`check_loc_budget.py` 新增具名常數 `POLICY_VERSION = "v3-assertion-only+sd08-special"` 並取代 `--json` payload 內原本寫死的字面值；同時新增 `BASELINE_POLICY_FILE`／`read_baseline_policy_version()`／`write_baseline_policy_version()`，`--json` payload 新增 `baseline_policy_version` 欄位。R100 §E-3 主牙要求的「把 `baseline > total` 這個雙義不等式改判 provenance（仿 `tools/lib/baseline_origin.py` 家族既有處方）」**本輪已由 E3/DEF-200-208 落地**：`pricing_exemption_problems()` 的參數簽章已改為 `baseline_policy_version`／`current_policy_version`，判準由「比大小」改為「比對是否同一把尺釘的」（見下方 §6.3）。🔴 **誠實劃界——落地的是判準，殘留的是磁碟資料**：磁碟上 `.loc_baseline` 檔案早於 `BASELINE_POLICY_FILE` 機制存在，尚未經過一次 `--update` 回填 provenance，故 `read_baseline_policy_version()` 現查回 `None`；`pricing_exemption_problems()` 因此**誠實地判紅**（`None != current_policy_version`），這不是舊的「永久靜音」缺陷復發，而是判準正確運作下「資料尚未補齊」的正常結果。回填動作（執行一次 `--update` 讓 `.loc_baseline` 記下當下 `POLICY_VERSION`）留給 R102 執行，本輪禁止（追蹤＝`DEF-200-207` 續報）。

**§6.3（通約規則——不可通約的兩個版本，禁止直接相減／相除比大小）**：

1. `.loc_baseline` 檔案本身**不記錄**是哪一版 `POLICY_VERSION` 釘的（歷史包袱，本輪機制已補齊寫入入口，但尚未對既有檔案執行回填——見 §6.2 誠實劃界）。任何比較 `.loc_baseline` 與當回合 `total` 大小之前，必須先確認兩者是同一把尺量的；version 標記不同時，該次比較沒有意義。
2. `POLICY_VERSION` **只在計價規則本身變更時**遞增；tier 門檻數字或 `TOTAL_INCREASE_LIMIT` 調整不算（尺不變、門檻變，不影響可比性），版號不做任何場自動換算——換算永遠是人審的責任（同 ADR-XPLAT-012 條文五 §3 的取值紀律，一貫立場）。
3. `v2-tiered+sd08-special → v3-assertion-only+sd08-special` 這一次跨版比較：§1.2 三支頂格檔實測顯示同一份原始碼在兩把尺下可相差 43% 以上，**任何**跨版本的行數差直接拿來當「成長」或「縮減」解讀都是誤讀，必須先扣掉尺差再談。
4. `.loc_baseline` 加上 provenance 標記（記錄「此值是哪一版 `POLICY_VERSION`、哪一輪釘的」）的**判準與寫入入口**已於本輪落地（見 §6.2）；剩下唯一的出口動作是對既有 `.loc_baseline` 執行一次 `--update` 把 provenance 實際回填進磁碟，該執行明確留給 R102（本輪禁止），追蹤同 `DEF-200-207`。（R210 註：回填已於 R102（6fea8a3b）執行；現查 `--json` 的 baseline_policy_version 與 policy_version 同為 v3-assertion-only+sd08-special。）

---
