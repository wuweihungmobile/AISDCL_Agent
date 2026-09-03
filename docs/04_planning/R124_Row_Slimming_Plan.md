# R124 帳本可寫性修復輪 — 計畫書

> **本輪刻意不結任何一筆缺陷。** 目標是解除「帳本列寫不進字」這個結構瓶頸，讓**後續**每一輪
> 都降得動。
> **性質**：兩種手法併用，**只能由收尾單人窗口串行做，禁派並行包**（鐵律七）。
>
> ## 🔴 掌舵者裁決（2026-09-03，本輪的核心設計）
>
> 原計畫只有「瘦身」一手。掌舵者質疑：
> > 「若是一列 700 有限制，寫兩列不是就好了，變成兩個問題也 OK，不用為了硬擠一列，
> > 把問題變成很困難、很難結案不是嗎？」
>
> **此質疑成立，並且改寫了本輪的主軸。** 當回合查證三點：
>
> 1. **拆列是既有合法動作**——帳本自己的處置指示逐字寫過「真待辦請拆出獨立 DEF 列承接」。
> 2. **會擋的那道鎖，其逃生口正是為此設計**：`tools/lib/ledger_closing_guards.py` 機械物①
>    規定「本輪新增未結列數不得超過本輪結案列數」，但同檔 `:39-40` 逐字寫明——
>    「真正會被擋的是**下一輪若是發現輪**（新缺陷被找出來的速度天然快過修復速度）——這正是
>    它的用意：逼那一輪的操作者**明確**選擇逃生口，而不是讓帳本無聲漲回去」。
>    逃生口＝環境變數 `AUTOSDD_NET_RATCHET_OFF`。⇒ **拆列＋明確用逃生口是設計內的正當用法，
>    不是繞過**；該檔同段還說明為何刻意不做行內註解式豁免（環境變數天生可稽核）。
> 3. **超標與貼線列裡有一半根本是「一列裝好幾件事」**（候選，接手者請現查逐列確認）：
>    `DEF-101-856` 七個子項、`DEF-200-172` 八個、`DEF-101-981` 六個、`DEF-200-065` 三個、
>    `DEF-200-213` 四個。現行規則等於「七件全做完才能結這一筆」——**這就是它們數十輪不動的
>    機制本身**，與缺陷難度無關。
>
> ⇒ 分母會先變大，但**結得動**。這是正確的方向：一個 ID 一件事。

---

## §1 為什麼不降帳本（策略轉向的取證）

「未結列」這把尺**今天沒有牙**——當回合實測：

| 量 | 值 |
|---|---|
| 未結列 | 40 |
| warn 線／fail 線 | 86／98 |
| 帳本主檔 bytes | 153,576 |
| 帳本 warn 線 | 245,760（餘裕 92,184） |

沒有任何一道閘門會因為停在 40 而紅；advisory 帶也結構性靜音。⇒ 為「降幾筆」排隊是優化一個
零壓力的指標。**真正會紅的是完全不同的東西**，其中最堵路的是單列 700 bytes 上限。

---

## §2 真瓶頸實測（本輪工作清單）

判準＝`check_defect_log_crossref.ROW_MAX_BYTES = 700`（現查值）。40 筆未結列：

| 帶 | 筆數 | 意義 |
|---|---|---|
| **餘裕為負（已超標）** | **6** | 靠存量豁免名單活著 |
| 餘裕 ≤ 5B | 19 | 連一個中文字都寫不下 |
| 餘裕 < 60B | 33 | 寫不下一句完整的結案理由 |
| 全部未結列「現象與證據」欄合計 | 15,177B | 主要可搬遷來源 |

**六筆超標列（第一優先，收益最大）**：

| ID | 整列 | 超標 | 現象欄 | 狀態欄 |
|---|---|---|---|---|
| `DEF-101-736` | 2537 | −1837 | 558 | **1835** |
| `DEF-101-856` | 2238 | −1538 | 492 | **1647** |
| `DEF-101-675` | 1319 | −619 | 538 | 467 |
| `DEF-101-803` | 1304 | −604 | **795** | 277 |
| `DEF-101-796` | 1271 | −571 | 531 | 477 |
| `DEF-101-887` | 1024 | −324 | 405 | 516 |

736／856 的狀態欄是歷輪訂正註記堆疊（1835B／1647B），搬遷收益最高。

**🔴 三重收益**（這是本輪的價值核心，不只是「讓列變短」）：

1. 列本身回到 700 以下 ⇒ 後續能寫得下結案理由；
2. 該列可從**存量豁免名單移除** ⇒ 名單 42／上限 42（滿載、shrink-only）往下鬆一格；
3. **超標量總和棘輪**（現值 25,520，只准降）直接下降。

三者都是判準指定的正方向，沒有一項是砸溫度計。

---

## §3 執行順序（兩種手法，先分診再動手）

### 步驟 0：分診——每一筆先判它是哪一型

| 型 | 判準 | 手法 |
|---|---|---|
| **A 史料型** | 列很長但講的是**同一件事**，長度來自歷輪訂正註記堆疊 | **瘦身**：史料搬證據檔 |
| **B 收集型** | 一列裡有 ①②③… 多個**彼此獨立**的待辦 | **拆列**：一件事一個 ID |

同一筆可以兩者都做（先拆再瘦，或先瘦再拆）。**不確定就當 A 型**——瘦身不可逆性低。

### 步驟 1：前置（已完成，見 §6.5）

接收檔已建並登記。接手者從步驟 2 開始。

### 步驟 2：A 型（瘦身）

1. 讀該列**全文**（用 Read，不要用 Grep——Grep 在 Windows 會改寫正斜線）；
2. 依 §4 判準挑出可搬史料；搬前抓特徵詞 Grep 全 repo 確認無人在逐字比對；
3. 用 §6.6-B 的 `slim.py` 機械搬遷（它會擋「新列 >700B」與「沒變短」）；
4. 跑 `python tools/check_defect_log_crossref.py`，rc=0 才做下一筆。

### 步驟 3：B 型（拆列）

1. **原列 ID 保留、不結案**——它可能是別處的承接載體（`check_handoff_carriers.py` 把
   「未結」當承接憑證）。做法＝原列**留下最核心的那一個子項**，其餘拆出去。
2. 新 ID 從 `DEF-200-247` 起連號（現查最大號：
   `python -c "import re,pathlib;print(max(int(m) for m in re.findall(r'DEF-200-(\d{3})', pathlib.Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8'))))"`）。
3. 每一個新列都要**自帶完整四欄**：發現情境（🔴 **零輪號**，見 §5 紅線 2）／現象與證據／
   嚴重度／分流去向／狀態（首詞 `open` ＋ 承接輪次或字面「未指派」＋可機械查的解鎖條件）。
4. 原列狀態欄改寫成：保留的那一項 ＋ 一句「其餘子項已拆為 `DEF-200-2xx`／…」＋ 檔名指標。
5. 原列的子項原文搬進接收檔（同 A 型，逐字保全）。
6. 每拆一筆就跑 `check_defect_log_crossref.py`。

🔴 **淨額棘輪會在這一步擋你**（新增未結列 > 結案列數）。合法做法：

```
# 在啟動 claude 之前設好（環境變數必須在行程啟動當下就存在）
$env:AUTOSDD_NET_RATCHET_OFF = "1"
```

並在 commit 訊息裡**明確寫出**「本輪是帳本可寫性修復輪，刻意讓分母上升」＋逐筆拆列理由。
該逃生口的設計意圖逐字見 `tools/lib/ledger_closing_guards.py:39-46`。**不准用行內註解式
豁免**（該判準刻意沒做那種出口，理由同段寫明）。

### 步驟 4：收斂

1. 六筆超標列回到 ≤700B 後：從存量豁免名單移除、重釘超標量總和棘輪為新實測值。
2. `python tools/sync_onboarding_baselines.py --write`
3. 三支文件閘門：`check_defect_log_crossref`／`check_archive_required`／`check_handoff_carriers`
4. `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（要零漂移）
5. 最後一次全套 `python tools/run_root_unittests.py`（**必須在最後一次寫文件之後**）
6. commit／push／等雲端全部 completed

---

## §4 可搬／不可搬判準（每一筆都要逐段判）

**可搬**：歷輪訂正註記、前值序列、「當時為什麼這樣改」、某輪誰抓到什麼、已兌現的承接紀錄。

**不可搬（搬走會弄壞別的機械物）**：

- 任何被別的檔**逐字比對**的字串。搬前抓特徵詞 Grep 全 repo（`tools/`、`.github/`、`docs/`）確認無人在讀。
- 該列的**解鎖條件**與**承接輪號／字面「未指派」**——硬規則② 要求未結列二擇一必須在列上。
- 狀態欄**首詞**（分類器讀它）與其後的**日期**。
- `DEF-ID` 交叉引用（`test_defect_id_reference_integrity.py` 守引用完整性）。
- 「發現情境」欄的**零輪號紀律**字樣（見 §5 紅線）。

---

## §5 🔴 紅線（本輪一定會遇到，先寫下來）

1. **不准碰 `DEF-200-207`／`213`／`241` 的狀態欄首詞**（可以瘦身它們的史料，但**不准結案**）：
   `check_handoff_carriers.py` 的承接憑證是「未結」，結掉任一筆會讓該閘門各 +2 紅，而它跑在
   pre-push 上（硬閘）；具名豁免面 5／上限 5 已滿載且 shrink-only。
2. **不准在「發現情境」欄補誠實輪號**：帳本時鐘由最新數列「刻意零輪號」按住在 R100；補一列
   帶輪號的 ⇒ `orphan_backlog_problems()` 由 0 變 **18** 筆紅（那 18 筆現在的綠是空綠）。
   本輪只搬史料，不動輪號紀律。
3. **不准為了讓超標判準轉綠而把 ID 補進存量豁免名單**——判準訊息逐字禁止，且名單已滿載。
   本輪的方向是**從名單移除**。
4. **不准遷軌**（外部阻塞軌／結構性長債軌）：兩軌的上限沒有 frozen 影子（長債軌 7→47 三支
   測試全綠）、外部軌連筆數上限都沒有 ⇒ 遷軌是把受棘輪管的分母換成不受管的分母。
5. **不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`**；push 不帶 `AUTOSDD_NET_RATCHET_OFF`。
6. **逐 commit 淨額棘輪**：判準比的是 `git show HEAD` 對工作樹、**逐 commit** 而非逐輪
   ⇒ 拆列會撞它。**正當做法見 §3 步驟 3 的環境變數逃生口**（那是設計內用法，不是繞過）；
   但 commit 訊息必須明確寫出「本輪刻意讓分母上升」與逐筆理由，否則就是無聲漲回去。

---

## §6 順帶接上的兩個免費槓桿（本輪或下輪）

1. **回歸鎖軌免稅額**：`_REGRESSION_LANE_LOG`（ADR-XPLAT-013 Phase2 (b)，R116 已落地）每輪
   上限 309 行且**不受連續正淨額鎖管**，而 R119／R120／R122／R123 **四輪全申報 0**。
   🔴 合格判準 C1~C4（新行全落 `def test*`／零新方括號標籤／零新或擴大掃描面／零新或變更門檻
   常數）的**分類器未實作** ⇒ 誠實申報制，理由欄須逐項自證。誠實劃界：本輪是淨減法輪，
   沒有回歸鎖可申報；這條是給**下一個修復輪**用的。
2. **結案詞彙選擇**：分類器對七個合法首詞一視同仁，`wontfix`／`no_action_needed` 與
   `closed-by-decision` 同樣離開未結類，但前兩者的既有前置是「明文並附實測」，**不需要
   掌舵者具名裁決** ⇒ 不必排隊等人。這是沒人碰過的槓桿。

---

## §6.5 接手時的工作樹現狀（前置已做，未 commit）

開工前 `git status --short` 應該看到這四項，**它們是前置工序、不是別人的殘留**：

```
 M .claude/output-styles/eli5.md                              ← 與本輪無關（output style 編修）
 M tools/lib/governance_docs.py                               ← 已登記下面那支接收檔
?? docs/04_planning/R124_Row_Slimming_Plan.md                 ← 本計畫書
?? docs/06_quality/CrossPlatform_R124_Row_Slimming.md          ← 接收檔（已建，只有檔頭）
```

🔴 **帳本主檔尚未被動過**（`git diff --stat docs/06_quality/AutoSDD_Defect_Log.md` 應為空）。
接手者從 §3 步驟 2 開始即可。

---

## §6.6 兩支工具腳本（scratchpad 是各 session 獨立的，接手者請照抄重建）

### A. 現查每列餘裕（工作清單產生器，唯讀）

存成 `<你的 scratchpad>/rowsize.py` 後 `python <path>`：

```python
"""現查每一筆未結列的 bytes 與 700 上限餘裕，並列出各欄位佔比（瘦身工作清單）。唯讀。"""
import re
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8")
REPO = pathlib.Path(r"d:\CursorProject\AISDCL_Agent")
sys.path.insert(0, str(REPO / "tools"))

import check_defect_log_crossref as c  # noqa: E402

LEDGER = REPO / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
text = LEDGER.read_text(encoding="utf-8")
CAP = getattr(c, "ROW_MAX_BYTES", 700)
print(f"# ROW_MAX_BYTES = {CAP}")

unresolved = []
for line in text.splitlines():
    m = re.match(r"^\|\s*(DEF-\d+-\d+)\s*\|", line)
    if not m:
        continue
    cells = line.split("|")
    if len(cells) < 4:
        continue
    if c._classify(cells[-2]) in ("None", "open", "routed", None):
        unresolved.append((m.group(1), line, cells))

rows = []
for did, line, cells in unresolved:
    total = len(line.encode("utf-8"))

    def b(i, cells=cells):
        return len(cells[i].encode("utf-8")) if i < len(cells) else 0

    rows.append({"id": did, "total": total, "slack": CAP - total,
                 "situ": b(3), "evid": b(4), "triage": b(6), "status": b(7)})

rows.sort(key=lambda r: r["slack"])
print(f"# 未結列 {len(rows)} 筆\n")
print(f"{'ID':<14}{'整列':>6}{'餘裕':>6}{'情境':>6}{'現象':>6}{'分流':>6}{'狀態':>6}")
for r in rows:
    print(f"{r['id']:<14}{r['total']:>6}{r['slack']:>6}{r['situ']:>6}{r['evid']:>6}"
          f"{r['triage']:>6}{r['status']:>6}")
zero = [r for r in rows if r["slack"] <= 5]
print(f"\n# 餘裕 <60B：{len([r for r in rows if r['slack'] < 60])} 筆")
print(f"# 餘裕 <=5B：{len(zero)} 筆｜{', '.join(r['id'] for r in zero)}")
```

### B. 機械搬遷（原文逐字抽出＋替換新列）

存成 `<你的 scratchpad>/slim.py`，用法
`python <path> <DEF-ID> <新列單行檔路徑>`。它自己會擋「新列 >700B」與「新列沒有變短」：

```python
"""列瘦身：把帳本某列的原文逐字搬進接收檔，並以新短列替換。"""
import re
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8")
REPO = pathlib.Path(r"d:\CursorProject\AISDCL_Agent")
LEDGER = REPO / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
SINK = REPO / "docs" / "06_quality" / "CrossPlatform_R124_Row_Slimming.md"

did = sys.argv[1]
new_row = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").strip("\r\n")
if not (new_row.startswith("|") and new_row.endswith("|")):
    sys.exit("新列必須以 | 開頭與結尾")
if "\n" in new_row:
    sys.exit("新列必須是單行")

with open(LEDGER, encoding="utf-8", newline="") as fh:
    text = fh.read()
eol = "\r\n" if "\r\n" in text else "\n"
flat = text.replace("\r\n", "\n")
lines = flat.split("\n")

idx = [i for i, L in enumerate(lines) if re.match(r"^\|\s*" + re.escape(did) + r"\s*\|", L)]
if len(idx) != 1:
    sys.exit(f"{did} 在帳本命中 {len(idx)} 列，預期 1")
i = idx[0]
old = lines[i]
old_b, new_b = len(old.encode("utf-8")), len(new_row.encode("utf-8"))
if new_b > 700:
    sys.exit(f"新列 {new_b}B > 700，先縮短再來")
if new_b >= old_b:
    sys.exit(f"新列 {new_b}B 未小於原列 {old_b}B——瘦身沒有發生")

if not SINK.exists():
    sys.exit(f"接收檔不存在：{SINK}")
sink = SINK.read_text(encoding="utf-8")
if f"## {did}" in sink:
    sys.exit(f"接收檔已有 ## {did} 小節，不重複搬遷")

section = (
    f"\n## {did}\n\n"
    f"**原列 bytes**：{old_b}（上限 700，超標 {old_b - 700}）→ 瘦身後 {new_b}"
    f"（餘裕 {700 - new_b}）。\n"
    f"**原文逐字保全**（由 `slim.py` 機械抽出，一字未改）：\n\n"
    "```\n" + old + "\n```\n"
)
SINK.write_text(sink.rstrip("\n") + "\n" + section, encoding="utf-8", newline="\n")

lines[i] = new_row
flat = "\n".join(lines)
with open(LEDGER, "w", encoding="utf-8", newline="") as fh:
    fh.write(flat.replace("\n", eol) if eol == "\r\n" else flat)

print(f"OK {did}: {old_b}B -> {new_b}B（省 {old_b - new_b}B，餘裕 {700 - new_b}B）")
```

### C. 第一筆的新列（已備好，可直接用）

`DEF-101-736`（原 2537B → 新約 692B）。存成單行檔後餵給 `slim.py`：

```
| DEF-101-736 | 2026-08-02 | R69 終審 R3（P2 #18；QA 覆核 archive_48 已結列的殘留待辦） | **承接項只寫在已結列內 ⇒ 結構上零機械追蹤**：`DEF-101-729` 首詞記 `fixed` 並隨 `archive_48` 歸檔，但它同欄載明的承接項（原鎖退場後「跨樹一致性保障消失」而無等價替代）沒有任何載體——孤兒承接稽核只掃未結列，已結列的殘留待辦結構上進不去 | P2 | 根層護欄層／帳本流程 | open（承接輪次：未指派）：待辦＝為 `DEF-101-729` 退場的跨樹一致性保障補等價替代，或以具名裁決明文「不需要」；本列並承接 `DEF-101-557`／`560`／`649`／`880` 四筆真待辦，不各自新增未結列。解鎖條件全文與歷輪逐筆判讀史料詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-736 |
```

該筆的搬遷安全性**已驗**：要搬的特徵詞（`判別法＝命中詞`／`敘事引述 22`／`真待辦 4`）
當回合 Grep 全 repo **只命中帳本自己** ⇒ 無別的機械物在逐字比對它。

---

## §7 本輪完成的判準（**不是**「降幾筆」——分母預期上升）

- 六筆超標列全部回到 ≤700B，且已從存量豁免名單移除；
- 超標量總和棘輪重釘為新實測值（下降）；
- **B 型收集列已拆**：一個 ID 一件事，每個新列自帶可機械查的解鎖條件；
- ≤5B 那 19 筆中，做到幾筆就誠實記幾筆（每筆獨立可交棒）；
- 三支文件閘門 rc=0、守衛線零漂移、全套 rc=0、雲端全綠；
- 交棒書寫明兩件事，那才是本輪真正的交付物：
  1. 每一筆現在有多少 bytes 可寫（下一個修復輪的可行性）；
  2. 拆出來的新列各自的解鎖條件（下一個修復輪的工作清單）。

🔴 **收輪報表禁止把「未結列上升」寫成退步**。本輪的成功長相是：分母上升、而每一筆都變成
「一件事、寫得下、結得動」。若下一輪開始出現連續淨減，那就是本輪真的成功了。
