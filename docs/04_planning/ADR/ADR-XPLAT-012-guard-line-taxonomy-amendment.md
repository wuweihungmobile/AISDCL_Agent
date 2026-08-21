# ADR-XPLAT-012 — 棘輪憲法修正案 v3：護欄層行分類（敘事／斷言軸）

- **狀態**：Accepted（四方終審全數 APPROVE，零 blocking；Phase 1 觀察模式本輪落地，Phase 2 阻斷切換須另走複審——見條文五 §6）
- **日期**：2026-08-21
- **平台**：平台中立
- **性質**：修正 `AutoClaude/tools/check_loc_budget.py` 的 LOC 計價政策——把「一行程式碼」的計價從單一維度（`count_loc()` 二分：空白／純 `#` 註解免費，其餘等價計價）拆成敘事（narrative）／斷言（assertion）兩軸，只在**行的種類**這個軸上動刀；護欄層既有的「內容守備標的」分桶（`tools/lib/guard_bucket_policy.py`）與逐檔／總量 shrink-only 棘輪（`_FROZEN_GUARD_LINES` 等）**一律原封不動**。本輪只做 Phase 1（觀察模式，只印不擋）。

---

## 1. 決策與脈絡

### 1.1 問題本體

`AutoClaude/tools/check_loc_budget.py::count_loc()` 的計價規則：

```python
def count_loc(path: Path) -> int:
    """計算實際程式碼行數（排除空行與純註解行）。"""
    ...
    for line in f:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        n += 1
    return n
```

`#` 開頭的整行註解免費（不計入 LOC 預算），但 **docstring 全額計入**——docstring 的每一行在 `count_loc()` 眼裡與一行 `if`／一行函式呼叫**同單價**。這個二分是本 ADR 要修正的對象：兩者都是「解釋為什麼、不是判斷什麼」的敘事文字，卻因為載體是 `"""..."""` 還是 `# ...` 而被計價器判成天壤之別的兩種東西。

### 1.2 實測證據（本輪 2026-08-21 現場重跑，非援引歷史值）

三支「頂格檔」（三者皆卡在自己 tier 預算的**零餘裕**上——`quota_gate.py` 500/500、`block_destructive_git.py` 750/750、`session_resume_planner.py` 750/750，見 `python AutoClaude/tools/check_loc_budget.py` 的 `[*-WARN]` 段——因此是本 ADR 立案動機的第一手素材：這幾支檔今天連一行都加不進去，而它們的體積有極大比例是散文）：

| 檔案 | 總行數 | `count_loc()` | 空白行 | `#` 整行註解（免費，被排除） | docstring 敘事行（收費，被計入） |
|------|-------:|-------:|-------:|-------:|-------:|
| `tools/lib/quota_gate.py` | 919 | 500 | 103 | **316** | **144** |
| `.claude/hooks/block_destructive_git.py` | 1276 | 750 | 141 | **385** | **193** |
| `tools/session_resume_planner.py` | 1487 | 750 | 138 | **599** | **37** |

方法：`count_loc()` 值直接呼叫既有實作；「空白行」＝`line.strip() == ""`；「`#` 整行註解」＝`total − count_loc − 空白行`（`count_loc()` 排除的唯二兩類，扣掉空白即為純註解那一類）；「docstring 敘事行」＝AST 掃描 `ast.Module`／`FunctionDef`／`ClassDef`／`ast.Expr(ast.Constant(str))` 節點涵蓋、且非空白的實體行。三支檔的 `#` 註解與 docstring 敘事行數量級相近（甚至 `quota_gate.py`／`block_destructive_git.py` 的 docstring 敘事都不到一半），但前者對 LOC 預算完全不計價、後者全額計價——這正是「敘事同單價」問題的量化證據。

### 1.3 為什麼「整行 `#` 註解」不能用樸素文字掃描判定

本輪同時重跑了 `session_resume_planner.py` 的 tokenize 版與 naive 版整行註解計數：

| 判法 | 結果 |
|------|-----:|
| tokenize（`tokenize.COMMENT` 且 `#` 前全為空白） | **593** |
| naive（`line.strip().startswith("#")`） | **599** |

差 **6** 行。逐行核對，6 行皆落在該檔內嵌的一段 heredoc 風格多行字串（可重啟任務書範本）裡的 Markdown 標題（如 `## 0. 量測（本工具當場實測，非宣稱）`），naive 掃描把字串**內容**誤判成 Python 註解，tokenize 因為知道當下在字串 token 內部而正確排除。**這是條文一 §4／`guard_line_taxonomy.classify_lines()` 一律走 `tokenize`、不走樸素文字掃描的直接理由**——樸素掃描的誤差不是理論風險，是本 repo 現存檔案裡當場量得到的真實假陽性。

### 1.4 修法方向

不把 docstring 降價、也不把 `#` 註解升價（兩者都可能引發既有預算全面重新校準的連鎖反應，超出本輪範圍），而是**新增一個獨立於計價的觀測軸**：把每一行分類成敘事（narrative）／斷言（assertion）／空白（blank）三桶，先以 **Phase 1 觀察模式**（只印不擋）在 `check_loc_budget.py --json` 並存新欄位，累積實測數據，供未來提案是否要／如何調整計價政策時有依據可查——而不是像今天這樣，`#` 與 docstring 同源異價的事實只能靠人工個案發現。

---

## 2. 條文全文

### 條文一 — 分類器射程與判準（`tools/lib/guard_line_taxonomy.py`）

**§0（射程）** 本條文只管 `AutoClaude/tools/check_loc_budget.py::count_loc()` 這一個計價函式的**觀測補充**。不碰、也不修改：
- `AutoClaude/tools/check_loc_budget.py` 的 `_FROZEN_GUARD_LINES`（不存在於該檔——那張表住 `tools/tests/test_adr_xplat001_c1c2_lock.py`，本條文亦不碰它）；
- `tools/lib/guard_bucket_policy.py` 的分桶棘輪（`BUCKET_TREES`／`WIDE_SURFACE_SPEC` 等）——見條文七的分工聲明。

**§1（三桶二分定義）** 每一行必須落入敘事（narrative）／斷言（assertion）／空白（blank）三桶之一，三桶互斥、聯集覆蓋全檔。docstring／多行字串**區塊內部**的空白行歸空白桶，不歸敘事桶（訂正 3：敘事桶只收非空白的實體行）。

**§2（強制歸斷言，優先序最高）** 下列三種情形，無論是否落在 docstring／註解形式內，一律強制歸斷言，覆蓋 §1 一般判準：
1. Shebang（檔案首行 `#!` 開頭）；
2. PEP 263 編碼宣告（僅前兩行有效：`# -*- coding: xxx -*-` 或簡式 `# coding: xxx`）；
3. `ASSERTION_PRAGMA_COMMENTS` 封閉表（`# noqa`、`# type: ignore`、`# pragma: no cover`）——封閉表，禁止擴表為開放式判準。

WHY：這三類雖然物理上是 `#` 開頭或位於檔案開頭類似「說明」的位置，但語意上是**執行環境／工具鏈契約**（直譯器選擇、原始碼編碼、linter/coverage 抑制指令），拿掉任一行都會改變程式的**可執行語意**或工具鏈行為，與「解釋為什麼」的敘事性質相反，故不論物理形式一律歸斷言。

**§3（`__doc__` 消費不升級）** 即使某模組的 docstring 被程式運行期以 `__doc__` 讀取消費（例如 CLI `--help` 印出模組說明、文件產生工具擷取），該 docstring 仍歸敘事——「被消費」是指運行期有人讀取它的**內容**，不代表它本身是判斷邏輯；升級為斷言會讓分類器的判準從「這行的語法角色」漂移成「這行有沒有被使用」，兩者是不同的問題（Phase 2 若要利用「是否被消費」做差異化政策，走條文五 §7 `doc_consumed` 觀測欄，不是本條文的分類本體）。

**§4（讀檔與容錯）** 讀檔一律使用 `encoding="utf-8-sig"`（正確剝除 BOM，避免 BOM 字元 `﻿` 讓 `ast.parse()` 對合法原始碼誤判 `SyntaxError: invalid non-printable character U+FEFF`——本輪已實測驗證此失敗模式）。`ast.parse()` 拋出 `SyntaxError`（含讀檔階段的 `UnicodeDecodeError`／`OSError`）一律**跳過並標記**（`unparseable=True`，三桶計數歸零），呼叫端的逐檔迴圈**不得中止**——一支壞檔不能讓整支工具停擺。

### 條文二 — 判準邊界與自證

**§1（行尾附掛註解不算敘事）** `x = 1  # 說明 x`——`#` 前若有非空白字元（即註解是附掛在程式碼行尾），該行**不**因為附了一段 `#` 說明就被歸類為敘事；行的種類由行的**主體**（程式碼）決定。技術上由 tokenize 的 `# 前綴是否全為空白` 判準自然涵蓋，不需要額外規則。

**§2（非傳統位置裸字串仍算敘事）** `ast.Expr(ast.Constant(str))`（裸字串常數表達式）不限於模組／函式／類別的**第一個** body 元素（即不限於傳統意義的 docstring 位置）——函式中段插入的說明性字串常數同樣歸敘事。判準以 `ast.walk()` 掃描全樹取得所有此型節點，不使用只認第一個 body 元素的 `ast.get_docstring()`。

**§3（第三道自證鎖）** 分類器必須能在**真實護欄檔**（非合成語料）上證明 §2（條文一）的強制覆寫確實生效：至少一支真實含 shebang 的護欄檔，其第一行必須被判為斷言。本 ADR 選用 `.claude/hooks/block_destructive_git.py`（首行 `#!/usr/bin/env python`）作為錨點；PEP 263 編碼宣告因 repo 現查零支 `.py` 帶真實宣告（`grep` 實測），改以最小合成語料驗證。

**§4（差異須可解釋 ＋ 鑑別力自證）**
(a) 任何「新判準給出的數字」與「既有簡單判準（如樸素文字掃描）給出的數字」之間的差異，必須能逐行指出差在哪、為什麼——不可只留一個對不上的總數（見條文一 §1.3 的 593/599 六行差異逐行核對即為此款的落地範例）。
(b) 分類器必須通過**變異測試**（mutation test）：把一段已知的敘事行人工改寫成斷言（例如把一行純敘事註解替換成一行真實程式碼），敘事行數必須相應下降。若判準對這種變異無感，代表它只是在套套邏輯地回聲輸入，不具備真正的鑑別力。

### 條文三 — 敘事覆寫名冊治理（`NARRATIVE_LEDGER_NAMES`）

`NARRATIVE_LEDGER_NAMES`（供未來「事先核准、即使形式上像斷言仍記為敘事」的具名例外）**現況為空表 Ø**。

**沿革**：起草階段曾提議一筆示範案例入表，用以說明擴表機制如何運作；審查階段對該案例做獨立驗證，發現其「行為不變」的宣稱不成立（見下方〈審查歷程〉2.2 節），該筆示範案例**永久剔除**，表恢復為空。空表本身是刻意的終態，不是尚未填寫——條文一／二的判準已經是判斷「行的種類」的完整規則，這張表是給**判準覆蓋不到、卻有正當理由**的個案開的安全閥，門檻必須夠高，不能靠一個未經驗證的示範案例把閘打開。

**擴表治理（三項，缺一不可）**：
1. `NARRATIVE_LEDGER_NAMES` 的成員數上限 `CAP=0`（現值），**只准調小**——即只能收緊或維持空表，不能無條件放寬；
2. 每一筆申請擴表的登記，必須**同時**附上「行為不變」的證據與**變異測試**證據（同條文二 §4(b) 的鑑別力自證邏輯，用於證明「這筆例外不是在悄悄放寬敘事的定義」）；
3. 機械測試鎖住成員數（不得靜默超過 `CAP`）與理由缺席（每筆登記必須有具名理由字串，不可空白或佔位文字）。

### 條文四 — 與既有棘輪的關係

敘事／斷言分類是**觀測軸**，不是新棘輪。斷言行（連同全檔行數）仍完全受既有 shrink-only 棘輪管轄——`AutoClaude/tools/check_loc_budget.py` 的 tier／`ABSOLUTE_LIMIT`／`SPECIAL_FILES`、以及 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 逐檔行數棘輪——本條文**零加、零減、零緩衝**：不放寬既有門檻、不因為某些行被重新歸類為「敘事」就給它們特殊豁免、也不預留任何新的餘裕空間。Phase 1 觀察模式的 JSON 新欄位是**並存**（additive），現有 rc／violations 判定邏輯逐字不動。

### 條文五 — Phase 1／Phase 2 路線圖

**§1（觀察模式先行）** 本輪（Phase 1）只印不擋：`AutoClaude/tools/check_loc_budget.py --json` 新增敘事／斷言／空白／unparseable 欄位與 `narrative_total` 全域欄位，**不參與** `has_violation`／rc 的計算。任何要把這些欄位轉為阻斷判準的提案，是**另一次修正案**，須另走條文六的四方複審程序（不可用「反正資料都印出來了」的理由直接生效）。

**§2（全量表欄位）** JSON 輸出的逐檔分類欄位覆蓋**護欄檔 SSOT 全集**（見 §5），不是抽樣或僅列違規檔——觀察模式的價值在於累積完整母體的實測分佈，抽樣會讓未來的門檻設定建立在偏誤樣本上。

**§3（未來新上限的取值紀律）** Phase 2 若要把敘事／斷言比例或絕對行數轉為阻斷門檻，新上限的取值紀律逐字比照 `_FROZEN_GUARD_LINES` 既有紀律：「當回合實測直接填入、零加減推算、不留成長緩衡」——不得預先設一個「看起來合理」的數字，必須是納管當下的實測值。

**§4（不得抽樣）** 同 §2 的推論延伸：Phase 2 的分類覆蓋率必須是護欄檔 SSOT 全集的 100%，不接受任何形式的統計抽樣近似。

**§5（護欄檔 SSOT 公式）** 「護欄檔」的範圍定義為：

```
root_tools_reports() ∪ special_file_reports()
```

（皆為 `AutoClaude/tools/check_loc_budget.py` 既有函式；兩集合已由 `root_tools_reports()` 自身排除已入 `SPECIAL_FILES` 的檔而互斥，見該函式 docstring。）

🔴 **本公式的回傳數字會漂移，禁止援引任何歷史值**——本輪審查期間三次獨立量測分別得到 **82 / 84 / 87**（各次量測間工作樹持續有其他改動落地，集合大小隨之變動），任何核准動作前**必須現查重跑**，不得沿用上一次審查留下的數字。本 ADR 定稿時（2026-08-21，本 ADR 自身的兩個新檔落地**之前**）現查重跑結果為 **87**（`root_tools_reports()` 77 ＋ `special_file_reports()` 10）；落地本 ADR 兩個新檔（`tools/lib/guard_line_taxonomy.py` 進入 `root_tools_reports()`、`tools/tests/test_guard_line_taxonomy_r99.py` 不進入本公式但進入 `guard_bucket_policy.guard_surface_files()`）之後現查為 **88**（78 ＋ 10）——這個 87→88 的位移本身就是 §5 這條警語的即時示範：連本 ADR 自己新增兩個檔案都足以讓這個數字位移，任何人下一次讀到本 ADR 時都必須重新現查，不可引用本段寫死的 87 或 88。

**§6（退出款與時效）** 若 Phase 2（阻斷模式）的提案在 Phase 1 落地後 **5 輪**內未被提出，本觀察模式條文須重新review：要嘛提出 Phase 2 提案並走複審，要嘛具名記錄「決定維持觀察模式」的理由並重新武裝下一個 5 輪視窗。不留無限期空轉的觀察機制——同本 repo `_REPIN_NET_CAP_DUE_ROUND` 的到期義務設計哲學：義務要能被看見、要有到期時點。

**§7（`doc_consumed` 觀測欄，Phase 2 前導）** 未來若要精緻化敘事分類（例如區分「純說明、無人讀取」與「被 `__doc__` 消費、實際發揮運行期作用」的敘事行），對應觀測欄位名稱保留為 `doc_consumed`——本輪不實作（見條文一 §3：消費狀態不影響本輪的敘事／斷言判定），僅保留欄位名稱以避免未來提案各自發明不同名稱造成同一概念兩個家。

**§8（敘事行逐輪記帳）** 比照 `_GUARD_LINES_REPIN_LOG` 的做法，建議（非本輪機械強制）未來每輪落地本 ADR 相關工作時，把當輪的 `narrative_total` 記錄下來，累積跨輪趨勢資料，供 Phase 2 提案決策時參考。本輪（2026-08-21，本 ADR 兩個新檔落地後）現查 `narrative_total = 14790`（覆蓋護欄檔 SSOT 全集 88 檔，其中 3 檔因是 Markdown 而 `unparseable=True`、計 0），此數字即該記帳序列的第一筆資料點。🔴 **此數字同樣會漂移**（與條文五 §5 的 87/88 同理，甚至漂移得更快——它會被護欄檔母體內任何一支檔的散文編修牽動）：同一份文件內後續量測分別得到 14829（見〈第 2.4 節〉附記二）、14763（R99 收斂輪首次現查）、14774（R99 收斂輪本節落筆前再次現查，同一輪內兩次量測就已不同）——四個數字皆為各自量測當下的真實輸出，不是三選一或四選一，任何人要用這個記帳序列前必須現查重跑，不得引用本節或本文件任何一處寫死的數字。

### 條文六 — 生效要件

四方（Architect／SA／SD／QA）獨立審查**全數 APPROVE，零 blocking**，要件已滿足（掌舵者原始裁決：「授權，但須四方全同意」）。詳審查歷程見〈第 2 節〉。

### 條文七 — 與 `guard_bucket_policy.py` 的分工

兩套機制管轄面**實測交集為零**，本輪重驗：

| | `tools/lib/guard_line_taxonomy.py`（本 ADR） | `tools/lib/guard_bucket_policy.py`（既有，本 ADR 不碰） |
|---|---|---|
| 判斷軸 | **行的種類**——這一行在語法上是敘事還是斷言 | **內容的守備標的**——這一行在守哪一棵樹（生產碼／根層基礎設施／SDD／散文／自己） |
| 掃描面 | `root_tools_reports() ∪ special_file_reports()`（本輪重驗 **88 檔**，落地本 ADR 前為 87 檔） | `guard_surface_files()`＝非遞迴 `tools/tests/*.py`（本輪重驗 **68 檔**，落地本 ADR 前為 67 檔） |
| 交集（本輪重驗） | **0** | **0** |

兩個掃描面的交界，落在 `AutoClaude/tools/check_loc_budget.py` 這一行常數：

```python
ROOT_TOOLS_EXCLUDED_DIRS: frozenset[str] = frozenset({"tests"})
```

`root_tools_reports()`（本 ADR 的掃描面之一）明確排除任何路徑帶 `tests` 目錄成分的檔案；`guard_bucket_policy.guard_surface_files()`（既有機制的掃描面）則**正是** `tools/tests/*.py`——一個排除、一個恰好等於被排除的那塊，兩者結構上互斥，不是巧合式的暫時不重疊。

**不預設優先序**：兩套機制不需要「誰先誰後」的裁決規則，因為它們的射程結構上不會同時判定同一行。本 ADR 承諾以機械測試釘住「交集恆為 0」這個不變量（比照本文〈第 1.3 節〉／〈審查歷程〉的做法：任何會讓這個交集不再為零的改動——例如 `ROOT_TOOLS_EXCLUDED_DIRS` 被縮小、或 `guard_surface_files()` 的掃描面被擴大——即觸發治理事件，須經複審才能生效）；**本輪（Phase 1 實作）尚未落地該機械測試**，列入〈第 4 節〉已知缺口。

---

## 2. 審查歷程

### 2.1 流程摘要

本修正案（棘輪憲法修正案 v3）由 Architect 起草，經 Architect／SA／SD／QA 四方獨立審查，歷經 **3 輪**修訂後全數 APPROVE、零 blocking。掌舵者的原始裁決是「授權，但須四方全同意」——三輪之後要件才滿足，修正案方才生效，進入本輪 Phase 2（實作）。

三輪審查累計推翻 **5 項錯誤宣稱**，其中可從最終版 v3 條文本身的措辭與結構**直接追溯**的計 2 項（下方 2.2／2.3 節，逐項附本輪 Phase 2 落地時的獨立複核）；另 3 項（兩個幽靈路徑＋一項措辭誇大）原不在 Phase 2 實作代理的任務材料內，已由協調 session 於 2.4 節回填，且每一項皆附回填當回合的機械複驗輸出。

### 2.2 被推翻宣稱 #1：`NARRATIVE_LEDGER_NAMES` 示範案例「行為不變」證偽

**原宣稱**：起草階段的草稿曾提議在 `NARRATIVE_LEDGER_NAMES` 中放入一筆示範案例，作為說明「事先核准的敘事覆寫」機制如何運作的具體範例，並宣稱該案例「不改變任何既有判準的行為」。

**審查發現**：獨立驗證該案例時，複核者發現其「行為不變」的宣稱不成立——該案例實際上會讓一行原本應歸斷言的程式邏輯被錯誤歸類為敘事，等同於變相放寬斷言的計價範圍，與該機制「只用於判準結構上覆蓋不到、卻有正當理由的個案」的設計初衷相反。

**處置**：示範案例永久剔除，`NARRATIVE_LEDGER_NAMES` 恢復為空表 Ø，並同時加嚴擴表治理為條文三所述三項（CAP 只准調小、每筆須附行為不變＋變異測試證據、機械測試鎖成員數與理由缺席）——這三項加嚴措施本身即是本次推翻的直接產物：起草階段沒有「變異測試證據」這項要求，審查發現示範案例问题后才補上。

**本輪（Phase 2）獨立複核**：本 ADR 落地時複核 `NARRATIVE_LEDGER_NAMES` 現況——由於該名冊是純 ADR 層級的治理概念（供未來擴表使用），`tools/lib/guard_line_taxonomy.py` 本輪程式碼**未實作、也未消費**此表（表為空，無成員可消費），與條文三「現況為空表」的陳述一致，未發現殘留的示範案例引用。

### 2.3 被推翻宣稱 #2：護欄檔計數「引用固定歷史值」

**原宣稱**：條文五 §5 護欄檔 SSOT 公式的早期草稿版本，直接引用某一輪量測得到的固定數字作為「護欄檔總數」，並以該固定數字作為後續條文（例如上限估算）的計算基礎。

**審查發現**：審查過程中不同輪次的獨立複核者各自重跑同一條公式（`root_tools_reports() ∪ special_file_reports()`），三次量測分別得到 82、84、87——彼此不一致，證明「引用固定歷史值」的做法本身就是錯的：這個數字會隨工作樹的其他並行改動而漂移，任何引用都在被引用的當下就可能已經過期。

**處置**：條文五 §5 加入 🔴 強制警語——「回傳數字會漂移，禁止援引任何歷史值，核准前必須現查重跑」。

**本輪（Phase 2）獨立複核**：本 ADR 定稿前現查重跑得到 **87**；落地本 ADR 兩個新檔（`guard_line_taxonomy.py`／`test_guard_line_taxonomy_r99.py`）後現查得到 **88**——見〈條文五 §5〉全文。這個 87→88 的位移，是條文五 §5 這條警語在本 ADR 自己身上的即時印證：連撰寫本 ADR 這個動作本身都改變了它所描述的數字。

### 2.4 由協調 session 補齊的 3 項（原「未能完整還原」，已回填）

> **回填說明**：本節原由 Phase 2 實作代理標記為「未包含在任務簡報中、拒絕虛構」。逐輪審查的原始記錄
> 只存在於協調 session 的對話脈絡、不在磁碟上，故實作代理**結構上**取不到——它的處置（不虛構、明記落差、
> 請持有記錄者補齊）是正確的。以下由協調 session 回填，且**每一項都在回填當回合重新機械複驗過**，
> 不是把對話內容原樣抄過來。

#### (3) 幽靈路徑 ①：v2 條文一 §0 的管轄邊界指向不存在的檔案

- **v2 原文**：「本修正案僅規範 `tools/lib/check_loc_budget.py`（**此路徑不存在**）內 `count_loc()` 這一把尺」。
- **發現者**：SA 與 QA 在二審**各自獨立**命中（兩人未互通）。
- **SA 的判詞**：「這句話本應是本修正案『機械可查的管轄邊界宣告』，指到不存在的檔案等於這條邊界
  目前無法被任何工具核對。」
- **回填當回合複驗**：

```
$ for p in tools/lib/check_loc_budget.py tools/check_loc_budget.py AutoClaude/tools/check_loc_budget.py; do
    printf '%-42s ' "$p"; test -f "$p" && echo EXISTS || echo ABSENT; done
tools/lib/check_loc_budget.py              ABSENT
tools/check_loc_budget.py                  ABSENT
AutoClaude/tools/check_loc_budget.py       EXISTS
```

- **v3 處置**：全文統一為 `AutoClaude/tools/check_loc_budget.py`（見條文一 §0）。

#### (4) 幽靈路徑 ②：v2 條文二 §3 的路徑與 §0 互相矛盾

- **v2 原文**：條文二 §3 寫 `tools/check_loc_budget.py`（**此路徑不存在**）——與同一份文件條文一 §0 的 `tools/lib/check_loc_budget.py`（**同樣不存在**）
  **彼此不一致，而且兩個都不存在**。
- **發現者**：QA（二審）。
- **本項的教訓值得單獨記**：一份**專門討論「機械可查」的修正案**，自己寫了兩個查不到的路徑，且兩處還互相矛盾。
  修正案在治理的正是這種「宣稱先於查證」，它自己犯了同型錯誤。
- **v3 處置**：同 (3)，並要求起草者對 v3 全文所有路徑逐一 `test -f` 後把結果貼進文件（見本 ADR 第 2 節前言）。
- 🔴 **這兩個幽靈路徑本節改採正式登記**（`_GHOST_PATH_BASELINE` 具名例外，見
  `tools/tests/test_doc_loc_baseline_freshness_r60.py`，天花板 17→18）：回填第一版曾把
  路徑改成〔方括號註記〕以規避 `TestR81GhostPathClaims`（其判準是「反引號指名的路徑必須
  解析得到」，分不出「引用一個幽靈當反例」與「宣稱一個幽靈」），但本 repo 對這類「判準
  結構上覆蓋不到、卻有正當理由」的個案早有正式出口——具名基線豁免表，而不是換一種標點
  繞過判準。R99 收斂輪已改回反引號；兩個路徑中僅 `tools/lib/check_loc_budget.py` 實際需要
  登記——`tools/check_loc_budget.py` 在 `TestR81GhostPathClaims` 的多基準解析下會經由
  `AutoClaude` 子專案基準意外解析到真實存在的 `AutoClaude/tools/check_loc_budget.py`，
  判準視其為子專案相對路徑而非幽靈，故不佔用豁免額度（硬塞入會被 `test_the_baseline_is_
  not_stale` 判 stale）。登記理由「ADR-XPLAT-012 §2.4 引用的歷史錯誤路徑，非現行路徑宣
  稱」，詳見該基線常數上方註解。

#### (5) 措辭誇大：v1 背景第 2 點的「三輪都逐字記載」

- **v1 原文**：「R89／R97／R98 三輪 commit message 都**逐字**記載『護欄層淨額搬遷抵銷』」。
- **發現者**：SD 與 QA 在一審**各自獨立**命中。
- **回填當回合複驗**（`git log -1 --format='%s'`）：

| commit | 輪 | 標題實際字面 | 是否逐字含該句 |
|---|---|---|---|
| `18dee83` | R89 | `fix(quota): R89 — DEF-200-112 治本（halt 兩型在人機出口分得出來）、射程訂正、護欄層淨額 0` | ✗（寫的是「護欄層淨額 0」） |
| `9cea72a` | R97 | `fix(治理): R97 護欄層淨額搬遷抵銷，收斂 +1023 超額回 881` | ✓ |
| `ea304b2` | R98 | `feat(PRD Token治理/R98): 落地 PRD v2.1 差距分析 + 護欄層 LOC 拆分 + 兩筆真缺陷修復 + 四方複審全部收斂` | ✗（寫的是「LOC 拆分」＝**真拆分**，不是搬遷） |

- **結論方向不變、理由被修正**：「用搬遷或拆分把逾額收斂回棘輪上限內」這個**治理動作**確實被三輪各自實踐過，
  但**手法與用語不同**，三輪不構成「同一句話被反覆驗證」的證據，只構成「同一類動作被三次獨立採用」。
  v3 已據此改寫背景敘事。**結論不變但理由錯了也要說——理由錯了會誤導下一個引用它的人。**

#### 附記：另有一項在 B1 設計階段即被綜合者證偽（不計入上述五項）

某份設計草稿宣稱「把測試檔藏進子目錄可逃過 950 行淨額棘輪」並自稱「已實測驗證的最陰險漏洞」。
綜合者實測推翻其中一半：`guard_surface_escapes()` **早已存在**（回填當回合複驗：定義於
`tools/tests/test_adr_xplat001_c1c2_lock.py`（`def guard_surface_escapes()`，行號隨後續
編修漂移，故不寫死；本輪 R99 現查為 :1578），同檔 6 處引用），且被現行測試斷言為空清單，
是 fail-loud 而非未受管的洞。僅「`unittest discover` 缺 `__init__.py` 會靜默漏跑子目錄測試」那一半為真。

#### 附記二：「81 支護欄檔」這個數字從未有 SSOT

一審 v1 寫「全部 81 支護欄檔」。二審 SD 用三種合理口徑分別量得 **70／63／77**，Architect 用
`root_tools_reports() ∪ special_file_reports()` 量得 **82**；SD 三審重跑同一公式得 **84**；
v3 起草者得 **87**；本 ADR 落地後（`guard_line_taxonomy.py` 自己進入 `root_tools_reports()`）
回填當回合實測 **88**：

```
$ python AutoClaude/tools/check_loc_budget.py --json   # rc=0
guard_taxonomy 筆數 = 88
narrative_total = 14829
```

**同一條公式、六次量測、六個數字。** 這直接支持條文五 §5 的處置：公式是 SSOT，**數字不是**；
核准前必須現查重跑，不得援引本文件或任何歷史文件出現過的任一數字——**包含上面這個 88**。

🔴 **`narrative_total` 犯了本節警語本身要提防的錯**：上面這個代碼區塊與條文五 §8 分別記載
14829、14790 兩個不同值，且皆未加註「這個數字會漂移」的警語——這正是本節這句「不得援引
任何歷史數字」理應防範、卻仍在本文件內部發生的個案。R99 收斂輪複核：第三次現查得到
**14763**，同一收斂輪內、僅隔數次編修再現查一次又得到 **14774**——同一 `guard_taxonomy`
88 筆母體，四次量測、四個數字。處置比照 §5：**不修改前兩處的歷史記載**（14829、14790
各自是各自量測當下的真實輸出，竄改成統一數字反而抹去了「這個量會漂移」這個事實本身的
證據），已於條文五 §8 補上與本段對稱的警語。

---

## 3. 已知缺口（v3 自陳，逐條列出）

以下缺口在 v3 條文本身已自陳，Phase 2（本輪）落地時**未解決**，原樣列出：

1. **條文七的機械測試尚未落地**——「兩套機制管轄面交集恆為 0」目前只有本 ADR 與本輪 Phase 2 落地時的手動重驗（見〈第 1.3 節〉表格），沒有機械測試釘住這個不變量。任何未來改動（縮小 `ROOT_TOOLS_EXCLUDED_DIRS`、或擴大 `guard_surface_files()` 的掃描面）都可能讓交集不再為零而無人察覺。
2. **條文五 §7 `doc_consumed` 觀測欄未實作**——僅保留欄位名稱以避免未來提案各自命名，欄位本身在本輪 JSON 輸出中不存在。
3. **條文五 §8 敘事行逐輪記帳未機械化**——本輪僅提供第一筆資料點（`narrative_total = 14790`，2026-08-21 量測；同一份文件內另有 14829／14763／14774 三個不同時刻的量測值，見條文五 §8 與〈第 2.4 節〉附記二——這正說明「未機械化」的後果：連手動記載都做不到彼此一致），沒有類似 `_GUARD_LINES_REPIN_LOG` 的機械化累積帳本；後續輪次若不手動延續記錄，這條記帳鏈會斷。
4. **審查歷程 5 項推翻宣稱中的 3 項未能完整還原**——協調 session 已回填並附機械複驗（見〈第 2.4 節〉），**待下一輪四方或第三方複核簽字後**正式關閉。本輪（R99 收斂）不視為已結案：回填者與判定「已關閉」者為同一協調 session，構成「改的人＝判定的人」——與 ADR-XPLAT-012 自己在〈第 2.4 節〉揭露 Phase 2 實作代理應對材料缺口的紀律（不虛構、明記落差、請持有記錄者補齊）同一條精神，回填動作本身不能同時是自己的驗收人。
5. **條文五 §6 的 5 輪時效尚未有到期時點的具名常數**——本 ADR 用散文描述「5 輪內未提出 Phase 2 提案須重新 review」，但比照本 repo `_REPIN_NET_CAP_DUE_ROUND` 的既有慣例，這類到期義務應該有一個機械可查的具名常數與判準，本輪未建立。
6. **`NARRATIVE_LEDGER_NAMES` 未在程式碼中以任何形式落地**——條文三描述的是純治理概念（空表 Ø），`tools/lib/guard_line_taxonomy.py` 目前沒有消費或引用此名冊的程式碼；若未來真的要用它做覆寫，需要額外的實作工作（讀取名冊、在 `classify_lines()` 中查詢並覆寫判定），本輪未做。

---

## 4. 生效狀態

- 四方（Architect／SA／SD／QA）獨立審查：**全數 APPROVE，零 blocking**。
- Phase 1（觀察模式，本輪落地）：`tools/lib/guard_line_taxonomy.py` ＋ `AutoClaude/tools/check_loc_budget.py --json` 並存欄位 ＋ `tools/tests/test_guard_line_taxonomy_r99.py` 回歸鎖。只印不擋，`has_violation`／rc 邏輯逐字未動（見〈實作驗證〉小節）。
- Phase 2（阻斷模式）：**未落地、未提案**。任何要把 Phase 1 的觀測欄位轉為阻斷判準的動作，須另外走條文六的四方複審程序，不可視為本 ADR 已隱含授權。

### 實作驗證（本輪落地時實測，2026-08-21）

- `ruff check tools/ --no-cache`：rc=0（全部通過）。
- `cd AutoClaude && ruff check tools/check_loc_budget.py`：rc=0。
- `python AutoClaude/tools/check_loc_budget.py`（文字模式）：rc=0（無 violations；與落地前一致，新分類器未改變任何既有判定）。
- `python AutoClaude/tools/check_loc_budget.py --json`：rc=0；新增 `guard_taxonomy`（88 筆逐檔物件，含 `narrative`/`assertion`/`blank`/`unparseable` 四欄）與 `narrative_total`（本段落地當下量測 14790，2026-08-21；同一數字在本文件內另有 14829／14763／14774 三個不同時刻的量測值，見條文五 §8）兩個頂層鍵，其餘既有鍵值逐字未變。
- `python -m unittest tools.tests.test_guard_line_taxonomy_r99 -v`：8 個測試全數 `ok`。
- `python -m pytest tools/tests/test_guard_line_taxonomy_r99.py -q`：`8 passed, 4 subtests passed`。
- `AutoClaude`：既有 73 個 LOC-budget 相關測試（`tests/contract/test_loc_budget_tiered.py` ＋ `tests/tools/test_check_loc_budget_hub_tier_and_special_stale.py` ＋ `tests/tools/test_check_loc_budget_tier_headroom_warn.py` ＋ `tests/tools/hooks/test_loc_budget_check.py`）全數 `73 passed`，證明本輪改動未破壞既有行為。
