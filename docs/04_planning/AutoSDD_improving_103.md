# AutoSDD_improving_103 — B/C 軌：Mac × Windows 11 相容性 R69

> **本輪柱別**：**B 軌（手腳框架 AISDLC_SDD dogfooding）＋ C 軌（指揮官 AutoClaude）雙柱**——跨平台相容性同時觸及兩子專案與根層整合層。上一份：`AutoSDD_improving_102.md`（R68，**該輪自陳未收輪**）。
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（整合迭代軌道①）。
> **日期**：2026-08-02　**平台**：macOS 26.5.2 arm64 真機（Darwin 25.5.0）；**Windows 側本輪零真機**。
> **基準 HEAD**：`375f291`（R68 收斂 commit）。
> **版本演化**：**無**——只動 LATEST（`AISDLC_SDD_v0.30`）與根層／AutoClaude，零碰凍結版本體，故不觸發 Copy-on-Evolve、不觸發五軌 TLC。
> **本輪缺陷號段**：`DEF-101-711` ~ `DEF-101-748`（38 筆；第四波 `734`~`748` 為終審 R3 與第四波自檢的入帳），另訂正既有 `DEF-101-706`／`DEF-101-701`／`DEF-101-721`／`R68-38`。

---

## §1　本輪最重要的發現（誠實，放在最前面）

### 1.1 R68 押上 main 的 `375f291` 讓雲端四支 CI 由全綠轉為三紅

R68 的 commit message 逐字寫「**收斂為閘門全綠**」。R69 開輪時唯讀 `gh run list` 核對，實況是：

| commit | root-infra-ci | macos-compat-ci | windows-compat-ci | aisdlc-sdd-ci | AutoClaude CI |
|--------|---------------|-----------------|-------------------|---------------|---------------|
| `24c5f34`（R67 收） | success | success | success | success | — |
| `375f291`（R68 收） | **failure** | success | **failure** | **failure** | success |

**那句「閘門全綠」只涵蓋本機 macOS 閘門**——而本機唯一有真機的平台是 macOS，恰好也是雲端唯一沒紅的那一支。

**這正是使用者訴求第 3 點（雙向落差）的活體標本**：不是「有人忘了跑測試」，而是**本機閘門對「非 macOS 面」結構性盲**，且 R68 當輪新設的 Scan-N（雙向落差維度）也沒有把這件事在 push 前攔下來——Scan-N 問的是「單平台開發者的錯誤會不會溜過去」，而它自己的答案（會）在同一輪就以最直接的方式被驗證了一次，代價是 main 上三紅。

三支紅的根因逐一落在本輪帳本：

| 紅掉的 CI | 根因 | 缺陷號 |
|-----------|------|--------|
| `windows-compat-ci` | 測試以 POSIX 絕對路徑字面值斷言 `Path` 內插後的訊息；`str(mock.call(...))` 的 repr 轉義路徑分隔符 | `DEF-101-727`、`DEF-101-723` |
| `aisdlc-sdd-ci` | 子專案測試跨樹 `import autoclaude.*`（`ModuleNotFoundError: pydantic`）；同型隱蔽版以 `try/except ImportError + skipIf` 包住 ⇒ **CI 上永遠 skip** | `DEF-101-728`、`DEF-101-729` |
| `root-infra-ci` | 新落地的 `tools/ruff.toml` 全 repo 零執行者；新增消費檔未同步 compat-CI `paths` | `DEF-101-719`、`DEF-101-721` |

🔴 **這三支的「紅→綠」在本輪的取證強度（誠實標示，收尾包複核）**：**三支皆未經雲端複驗**。依「GitHub CI 只准唯讀」紀律本輪未 push，故上表三個根因的修復憑證一律是**本機實跑**（root-infra 面）或**靜態分析／沙箱模擬**（Windows 面，零真機）。**別把本文件任何一處的「已修」讀成「雲端已轉綠」**——雲端複核是 `DEF-101-727` 明載的承接條件（下次合法 push 後唯讀 `gh run list`）。

**流程病本身（`DEF-101-733`）仍是 partial**：個別根因已修，但「本機綠即宣稱全綠」沒有任何機械物看守。R69 只落地了一小步——**收輪宣稱一律標明射程**（寫「本機 macOS 閘門全綠」而非「閘門全綠」）。

### 1.2 兩個「鎖看起來有、其實不可能抓到」的結構性假鎖

本輪最值得記的不是修了幾筆，而是**兩筆假鎖的形態**——它們都不是寫錯，是**設計上就抓不到要抓的東西**：

1. **造假直譯器**（`DEF-101-716`）：看守 `DEF-101-628`（版本前置閘）的測試，作法是「用**真的 3.11** 開跑，再於行程內把 `sys.version_info` 改寫成 `(3,9,6,...)`」。它只驗得了**版本判斷分支**，驗不了 **prelude 在真的舊直譯器上載不載得動**。實測憑證最刺眼：`DEF-101-715` 那個缺陷**活著**的時候，`pytest -k TestPickPythonGeMin` 仍 **6 passed**。
2. **`^` 沒有 MULTILINE**（`DEF-101-717`）：本輪自己新造的 P1 哨兵防護寫 `assertNotRegex(step, r"^        if:")`，而 `assertNotRegex` 走 `re.search`、**預設不含 MULTILINE**，`step` 又是多行文字 ⇒ 注入 `if: false` 把頭號哨兵整道停用，該檔仍 **23 passed**。

兩者的共通點：**鎖存在、CI 綠、看起來被守著**。差別只有一種驗法能揭露——**對真檔注入缺陷、看鎖會不會紅**。本輪 12 筆確認缺陷中有 6 筆是這樣抓出來的。

🔴 **收尾包追記（誠實，比上面兩筆更難堪）**：同一形態在本輪**第三度**出現，而且是在它已經被逐字寫進本節之後——`DEF-101-750`：本輪**自己新造**的 ruff 執行者鎖用 `assertIn("ruff check tools/", 非註解行全文)` 判「有沒有人真的跑 ruff」，而 `pre-push` 的失敗訊息 `echo "… ruff check tools/ 失敗 …"` 自己就滿足它（實測：刪掉唯一的執行行、只留 echo ⇒ 仍 `Ran 3 tests … OK`）。它與同輪 `DEF-101-743`（nightly 哨兵鎖可被處置指令 echo 滿足）是**逐字同型**，兩者相隔不到一波。⇒ **「知道這個形態」顯然不足以避免再造一個**；本節的結論因此要往下修一格：唯一有效的不是意識，是**每造一道鎖就當場對真檔注入一次**（`DEF-101-750` 的修復即附上該注入並把它固化成常駐測試）。

---

## §2　流程實錄

```
R68 收斂 commit 375f291（自陳未收輪）
  ↓
R69 開輪：唯讀 gh run list 核對 → 發現雲端三紅（§1.1）
  ↓
四方複審 R1 —— Architect REJECT／SD REJECT／QA REJECT／SA APPROVE_WITH_COMMENTS
  ↓
修復波（9 包並行）
  ↓
四方複審 R2 —— 4 REJECT，12 筆確認缺陷
  ↓
第三波修復（5 包：4 個修復包 + 1 個帳本統一配號包）
  ↓
四方複審 R3（終審）—— Architect APPROVE_WITH_COMMENTS／QA APPROVE_WITH_COMMENTS／SA REJECT／SD REJECT
  ↓（2 筆擋收輪 P1）
第四波（4 包並行；本包＝唯一可改帳本者且最後動工）
  ↓
四方終審 —— 4 × APPROVE_WITH_COMMENTS，0 筆擋收輪，4 筆「本輪核心病同型復發」
  ↓
收尾修復包（收輪前最後一包）—— 修那 4 筆（`DEF-101-749`／`DEF-101-750` ＋ 6 處佔位缺陷號 ＋ 本文件 §7 漏列）
```

**R1 三方 REJECT 的共同理由**：修復宣稱缺乏「能轉紅的回歸鎖」——修了但沒有任何機械物阻止它復發。
**R2 四方 REJECT 的共同理由**升級為更難堪的一層：**本輪新造的鎖自己是假的**（§1.2）。

**R3（終審）的兩筆擋收輪 P1**：① **帳本容量死鎖**——主檔距 262,144 硬線僅約 250 bytes，而 `--plan` 可搬 **0 筆**，下一個「加一列」動作即 rc=1 且**無機械解法**（Architect／QA 各自獨立實測命中）；② **ADR 對缺陷狀態的宣稱與帳本互斥**且 ADR 不在 crossref 掃描面內故機械盲（SD 命中）。兩筆皆由第四波收斂，見 §5.1 與 `DEF-101-734`／`735`。

**第三波刻意的分工設計**：四個修復包各自持有不重疊的檔案集合，第五包（本包）是**唯一可改帳本的包**且**最後動工**——這是對 `DEF-101-701` 記載的「收輪多波次 vs 重釘取當下實測」結構衝突的一次規避（不是修復）。

---

## §3　逐項對照使用者四點訴求

> 🔴 **來源誠實標示**：第 3、4 點的逐字原文保存在 `docs/06_quality/CrossPlatform_Scan_Dimensions.md` §「為何 R68 必須加 Scan-N／Scan-T」；第 1、2 點本文件依本輪流程還原其意旨，**非逐字引用**。

| # | 訴求 | 本輪達成度 | 誠實說明 |
|---|------|-----------|---------|
| 1 | Mac 與 Windows 11 雙平台相容 | **partial** | macOS 側：全部本機閘門實機全綠（§4）。**Windows 側：零真機**——所有 Windows 結論皆為靜態分析／沙箱模擬／CI 對帳。`windows-compat-ci` 的紅→綠**本輪未經雲端複驗**（依「GitHub CI 只准唯讀」紀律未 push），故 `DEF-101-727` 明載承接條件＝下次合法 push 後唯讀複核 |
| 2 | 四方專家（Architect／SA／SD／QA）獨立複審把關 | **達成（超額）** | R68 是 0/4；R69 執行了 **R1（4/4）＋ R2（4/4）＋ R3 終審（4/4）**，共三輪。R2 的 12 筆確認缺陷中，**6 筆是複審者對本輪新造的鎖做變異測試才抓出來的**——這是四方複審在本 repo 第一次系統性地把「鎖的有效性」而非「程式的正確性」當主軸 |
| 3 | 「Mac 開發時 Windows 不產生落差；反之亦然」 | **未達成（如實）** | 本輪把落差**抓到了**（§1.1 是最直接的證據），但**沒有建立防止它再發生的機械物**。`DEF-101-733` 仍是 partial：push 前仍無任何東西告訴你「你只驗了平台面的 1/5」。R70 的首要待辦 |
| 4 | Developer 清除技術債 | **partial** | 清掉的：`R68-38` 的**根層 `tools/` 半邊**（`tools/ruff.toml` ＋ CI／pre-push 雙執行者，`DEF-101-719`）。**沒清掉的**：`R68-38` 原點名最大實害面 `AISDLC_SDD` 全樹（LATEST v0.30 的 F 類真錯誤 3,486 筆）仍零 ruff 設定、零執行者。**且本輪自己製造了新債**：護欄層淨增（§5.2），生產碼 Δ=0。🔴 **第四波追記**：本輪同時**清掉了一筆真正的結構債**——缺陷帳本主檔的單調增長項（歸檔索引段）外移，見 §5.1；但也**新暴露一筆**：護欄檔的 SPECIAL_FILES 行數棘輪以零餘裕納管，`DEF-101-739` |

---

## §4　收輪判準與實測

> 🔴 **本節刻意不寫死「當場即可現查」的量測 token**（`DEF-101-713` 家族紀律：本 repo 已因此復發四次）。下表只記 **rc 與 live 來源**；具體數字請現跑或讀 `ONBOARDING.md` §7 表① / 表②。

| 閘門 | 指令 | rc | live 來源 |
|------|------|----|-----------|
| 根層 unittest | `python tools/run_root_unittests.py` | **0** | 該工具自身輸出；`ONBOARDING.md` §7 表② |
| AutoClaude pytest | `cd AutoClaude && python -m pytest tests/ -q` | **0** | 同上 |
| import-linter | `cd AutoClaude && PYTHONUTF8=1 lint-imports` | **0** | `Contracts: 8 kept, 0 broken` |
| LOC 預算 | `cd AutoClaude && python tools/check_loc_budget.py` | **0** | `--json` 現查；`ONBOARDING.md` §7 表① live 格 |
| 根層護欄層 lint | `ruff check tools/` | **0** | `All checks passed!`（**R69 新接的執行者**，`DEF-101-719`） |
| 腳本對等 | `python tools/check_script_parity.py` | **0** | — |
| AISDLC_SDD ci-gate | `bash AISDLC_SDD/scripts/ci-gate.sh` | **0** | 該腳本印出的逐軌計數 |
| 整合閘門 | `bash tools/integration_gate.sh` | **0** | `4 PASS / 1 SKIP`（SKIP＝cc-switch CLI 未安裝，`DEF-01-007`） |
| 帳本交叉引用 | `python tools/check_defect_log_crossref.py` | **0** | — |
| 帳本歸檔稽核 | `python tools/archive_defect_log.py --check` | **0** | — |

🔴 **上表全部是 macOS 本機**。**沒有任何一格代表 Windows**——這正是 §1.1 在講的事，寫在收輪判準表裡以免下一輪又把它讀成「全綠」。

---

## §5　本輪副作用與新增技術債（誠實登帳）

### 5.1 帳本容量：R68 的「容量政策解」在 R69 就再度撞牆 → 第四波做了根因級切分

R68 以 `DEF-101-676` 落地了帳本容量政策解（判準②③ 收窄），該輪自陳「輪替吞吐被恢復」。**R69 實況**：本輪新立 23 列後主檔一度超硬線，`--apply` 搬走 19 筆（`archive_48`）後仍需**逐段壓縮敘述**才回到線內；到終審 R3 時 `--plan` 的可搬清單是 **0 筆**、距硬線僅約 250 bytes ⇒ **下一個「加一列」動作即 rc=1，且無機械解法**（終審兩筆擋收輪 P1 之一）。

**第四波逐條查明「為何 0 筆」**：95 筆真為未結（依政策本就留主檔）、8 筆已結但被判準④ 攔下待具名承認 ⇒ **判準沒有過嚴**。真正的根因是**主檔裡有一段永遠搬不走的東西**：歸檔索引段（每次 `--apply` 多一條約 0.9KB 的 bullet，近幾輪每輪 3~5 支 archive ⇒ 每輪 3~5KB **只增不減**，而缺陷列還能靠結案＋歸檔釋出）。**把單調增長項放進有硬上限的檔，數學上保證撞牆**——歷輪「一輪歸檔兩三次」都只是在買下一輪的餘裕。

**處置（`DEF-101-734`）**：索引段逐字外移至 `AutoSDD_Defect_Log_archive_INDEX.md`，主檔留指針。**不是**調高 262,144 硬線（該線＝Read 工具實測上限，調高等於砸溫度計），也**未**放鬆 crossref 任何檢查；檔名刻意落在既有 `AutoSDD_Defect_Log_archive_*.md` glob 內，故帳本家族／指針稽核／體積守門／compat-CI `paths:`／測試沙箱五道守門**零改動即涵蓋**。

🔴 **誠實話：這沒有解決全部**。外移移除的是**單調增長項**，缺陷列本身的增長一字未動。**「下一輪加 20 列會不會撞牆」的算法（不寫死答案，寫可重跑的算式）**：
```bash
python3 -c "
import pathlib,re
p=pathlib.Path('docs/06_quality/AutoSDD_Defect_Log.md'); n=p.stat().st_size
rows=[l for l in p.read_text(encoding='utf-8').split(chr(10)) if l.startswith('| DEF-')]
avg=sum(len(l.encode())+1 for l in rows[-15:])/15   # 以最近 15 列為代表列長
print('現值',n,'加 20 列後',round(n+20*avg),'對硬線 262144 ⇒',
      '撞牆' if n+20*avg>262144 else '不撞')"
```
第四波交件當下以本輪平均列長代入，**答案是「會」**（會越過 262,144）。要讓它變成「不會」只有兩條路：(i) 下一輪動工前先 `--apply`（本輪 9 筆 `fixed@R69` 新列與 8 筆待 `--ack-handoff` 的已結列合計約 26KB 可釋出，但**都需要人真的去執行**，這正是歷輪反覆忘記的動作）；或 (ii) 把每列壓短。真正的下一步是壓縮**每列體積**：R60 已定的「帳本列只寫摘要、完整證據落 Evidence 檔」兩層化政策**至今沒有任何機械守門**，本輪自己寫的列也普遍偏長。

### 5.2 護欄層／生產碼比例續惡化

`375f291` → 交付樹：root `tools/` **+1795**、`AutoClaude/tests` **+333**、`AutoClaude/tools` **+19**、`AISDLC_SDD/scripts` **+167**；**生產碼 `AutoClaude/autoclaude` Δ=0**。⇒ **本輪 100% 的行數增長落在護欄層**（`DEF-101-714`；R68 記 4.81x → 4.92x）。

🔴 量測面本身是髒的（多包並行，收尾複量已漂至 +3079），故**刻意不把成長率常數登進 ADR**。

**這件事該不該擔心，本輪沒有結論**：護欄長是因為本輪抓到的都是「鎖沒牙」型缺陷、補鎖必然長行數；但「補鎖」與「補假鎖」在行數上長得一模一樣，而本輪已經證明後者確實會發生（§1.2）。**沒有訊號能區分兩者**才是真正的技術債。

### 5.3 LOC 硬線餘裕

`tools/dev_start.py` 貼著 SPECIAL 上限 2000（第三波曾一度破線至 2011 行）；monorepo `total` 已落入 `ADR-SD07-001` §6.3 預警帶第 1 輪。**實害已發生**：本波出現過「一包只加 18 行**註解**就打紅全樹 LOC 閘」。詳見 `DEF-101-726`。

🔴 **誠實標示（收尾包複核）**：`autoclaude/` 的 LOC 餘裕**本輪一行都沒有解凍**——`DEF-101-706` 仍是 **partial**，其解鎖條件①（`cap − total` ≥ 100 行）未達標，生產碼凍結**未解除**。本輪 `AutoClaude/autoclaude` 的淨 Δ＝0（§5.2）正是這個凍結的外顯，不是「本輪剛好沒動生產碼」。餘裕的具體數字本文件刻意不寫（`DEF-101-713` 家族紀律），唯一真相源＝`cd AutoClaude && python tools/check_loc_budget.py --json` 現查 ＋ `ONBOARDING.md` §7 表① live 格。

---

## §6　R70 承接（具名待辦）

| 優先 | 項目 | 對應 DEF | 解鎖條件（可機械查） |
|------|------|---------|---------------------|
| **P0** | **掃描面 fail-open 全面封閉**（R70 只修 3／14 站點；`git ls-files` tracked-only 讓 §8.2 那個違規躲過四輪四方複審） | `DEF-101-752` | 其餘 11 個 FAIL-OPEN 站點逐一判定並改為 tracked ∪ untracked-not-ignored（或具名記錄「加 untracked 反而有害」的理由）；**且每一處都要有 untracked 探針的注入紅綠**，不接受只改掃描面不加自證 |
| **P0** | **落差偵測機械化**——訴求第 3 點的真正答案 | `DEF-101-733` | 收輪閘門新增一道「上一個 main commit 的雲端 CI 結論」唯讀查詢並印在終端（唯讀 `gh run list`，不違反額度紀律）；且該道對「本機綠 × 雲端紅」的組合必須 fail loud |
| **P0** | **帳本容量：每列體積**（單調增長項已於第四波外移，`DEF-101-734`；剩下的是缺陷列本身） | `DEF-101-676`、`DEF-101-734` | R60 已定的「帳本列只寫摘要、證據落 Evidence 檔」兩層化政策**接上機械守門**（例如單列位元組上限＋超限指向 Evidence 檔），並使 `--plan` 的「搬後距 fail 線」≥ 10240 bytes 在**不靠壓縮敘述**的情況下成立 |
| **P0** | **護欄檔棘輪零餘裕**（`run_root_unittests.py` 的 fail-fast 因此被放棄；本包兩檔亦當場撞牆） | `DEF-101-739` | 抽共用模組後把被放棄的 fail-fast 補回；並裁決 SPECIAL_FILES 棘輪是否改計「非註解行」（否則「每道判準寫 WHY」與行數預算持續對衝） |
| **P1** | **`DEF-101-729` 退場鎖的等價替代**（已從已結列內的散文升級為可追蹤的未結列） | `DEF-101-736` | 補上替代鎖並附注入紅綠，或以 `closed-by-decision` 具名裁決 |
| **P1** | **root-infra hook 的 `python3` 回退**（無 venv 的 macOS 上所有 push 被硬擋） | `DEF-101-740` | 在無 venv 的 macOS 上實跑 push 前置驗證（`python`／`python3` 兩種 PATH 形態各一）並附 rc |
| **P2** | **`ONBOARDING.md` §7 表② Windows 欄從未建立基線**（provenance 四項全 `unrecorded`、且刻意不計入本機 rc ⇒ 結構上永久綠） | `DEF-101-747` | 在 Windows 真機執行 `python tools/sync_onboarding_baselines.py --write --with-slow` |
| **P3** | **兩項架構決策沒有 ADR**（跨子專案 import 邊界、根層 ruff 政策，目前只活在測試 docstring 與 toml 註解裡） | `DEF-101-748` | 各補一份 ADR（或合併為一份「根層與子專案的邊界」ADR），並在對應測試 docstring 回指其編號 |
| **P1** | `windows-compat-ci` 雲端複驗 | `DEF-101-727` | 下次合法 push 後唯讀 `gh run list` 確認該 job success，並把結果寫回該列 |
| **P1** | `AISDLC_SDD` 全樹 ruff（`R68-38` 未清的另一半） | `R68-38`（partial@R69） | LATEST v0.30 的 **F 類**（真錯誤）先接：有 ruff 設定 ＋ 有執行者 ＋ `ruff check` rc=0 |
| **P1** | 跨樹一致性鎖的正解 | `DEF-101-729` | `state_loader._sanitize_component` ↔ AutoClaude 側的一致性改以**契約檔／黃金樣本**重建（兩側各讀同一份資料、不互相 import），或明確判定不需要並記錄理由 |
| **P2** | `MIN_TESTS` 雙角色解耦 | `DEF-101-701` | 零相依探針改用獨立門檻常數，或改「收集數 × 相依可用性」二維判定；`MIN_TESTS` 回歸單一「下限」語意 |
| **P2** | 「誰是最後一個工作者」機械判準 | `DEF-101-701` | 把含內容的工作樹指紋（`{ git status --porcelain; git diff HEAD; git ls-files -o --exclude-standard -z \| xargs -0 shasum; } \| shasum`）接進收輪閘門 |
| **P2** | 護欄成長成本訊號 | `DEF-101-714` | 「護欄層／生產碼比例」納入 `check_loc_budget` warn band，或收輪閘門印出雙側 Δ |
| **P2** | `autoclaude/` LOC 餘裕 | `DEF-101-706`、`DEF-101-726` | `cap − total` ≥ 100 行，或走 `ADR-SD07-001` §6.3 正式程序（Architect + SD 雙簽）。🔴 **禁止**直接上調 `.loc_baseline` |
| **P3** | `DEF-101-432` 狀態首詞訂正 | `DEF-101-710` | 回讀全欄確認訂正即現況後依 `DEF-101-433` 體例改首詞，使 crossref 該 warning 消失 |
| **P3** | `run_local_nightly.ps1` 對等缺口 | `DEF-101-652` | 需 Windows 真機實跑（承自 R67、R68 皆未動） |
| — | **Windows 真機** | — | 本輪所有 Windows 結論皆非真機。讀任何「已驗證」宣稱前請先問「在哪個平台驗的」 |

---

## §7　本輪產出索引

- **缺陷帳本**：`docs/06_quality/AutoSDD_Defect_Log.md`（活躍列）＋ `AutoSDD_Defect_Log_archive_48.md`（本輪已結列 19 筆逐字保全）＋ **新增** `AutoSDD_Defect_Log_archive_INDEX.md`（歸檔政策全文與索引 bullet，第四波自主檔逐字外移，`DEF-101-734`）
- **新增共用模組**：`tools/lib/defect_ledger_index.py`（歸檔索引基元 ＋ 散文式結案宣稱判準 ＋ 體積守門純函式；抽出的直接理由是護欄檔行數棘輪零餘裕，見 `DEF-101-739`）
- **掃描判決**：`docs/06_quality/CrossPlatform_R68_Scan_Findings.md`（`R68-38` 狀態已於本輪訂正為 partial）
- **ADR**：`docs/04_planning/ADR/ADR-XPLAT-002`（§4.3.1 R69 段、L32 射程訂正）、`ADR-XPLAT-003`（§3 量測值訂正、§8 歷史段逐字保全）
- **新增機械物**：`TestR69AdrMeasurementTokensAreLive`、`TestRealSubMinInterpreterPrelude`、`TestPy39PreludeStaticScan`、`TestNoMockCallObjectRepr`、`TestRootToolsRuffHasExecutors`、`waiver_expiry_verdict()`、`grandfather_ceiling_problems()`；**第四波追加**：`TestNoPlatformDependentPathStringIdentity`（11 支；**本波最重要的一道**——鎖住 §1 那個 Windows 路徑 key 病灶家族：`Path` 的平台相依字串化不得當識別鍵／比對值，含對真實檔案「修復前形態」的偵測器自證）、`TestArchiveIndexDocIsExternalized`（3 支）、`TestAdrClosureClaimsAreMechanicallyChecked`（3 支）、`TestFullwidthGluedVariableName`（3 支，含對真實 `pre-push` 的注入紅綠）；**收尾包追加**（終審 R3 的兩筆同型復發，`DEF-101-749`／`DEF-101-750`）：`_runs_ruff_over_root_tools()` 純函式取代兩道執行者鎖的全文子字串比對 ＋ `test_the_executor_lock_is_not_satisfied_by_an_echo`（1 支負向自證）（皆加進**既有**測試檔，遵守「不新增 `tools/tests/` .py 檔」棘輪）

---

## §8　收輪後（R70）：`git push` 被阻斷所揭露的兩件事

> **為何獨立成節、且放在最後而非併進 §1**：本節記的事**發生在 R69 宣告收輪、commit `6a453b8` 落地之後**。
> 把它塞進 §1 會抹掉最關鍵的一個事實——**它是在整輪全部把關都通過之後才顯形的**。時序本身就是證據。

### 8.1 唯一的紅燈：R17 鎖住的不變量已被 R69 自己的架構決策推翻（`DEF-101-751`）

```
FAIL: test_platform_utils_dedup.TestNoDuplicateDefinitions.test_platform_judgment_helpers_defined_only_in_platform_utils
AssertionError: Lists differ:
  ['AutoClaude/autoclaude/utils/platform_caps.py', 'tools/lib/platform_utils.py'] != ['tools/lib/platform_utils.py']
```

`ADR-XPLAT-003`（本輪落地）新增的 `platform_caps.py` 必須自帶 `is_windows()`；而 R17 的鎖要求它全 repo 只有一處。
**兩邊都對，錯的是不變量的射程**——`autoclaude` 是可獨立 pip 安裝的套件，結構上搆不到根層 `tools/lib/`
（反方向 import 則會把 pydantic 拉進 hook／`aisdlc-sdd-ci`，正是 R68 讓該 CI 恆紅的形態）。
處置：不變量改寫為「**每一個相依孤島內，各 helper 只准有一個定義點**」，並在 `ADR-XPLAT-003 §7` 立判準、
鎖照判準改寫（含兩島各自的注入紅綠實測）。**刻意不用白名單**——白名單再加一筆即放行，孤島不變量哪一島都紅。

🔴 **這件事的流程教訓不在缺陷本身**：`ADR-XPLAT-003 §1` 第 2 點其實**已經寫下**「跨樹不可共用」這個理由，
但那是**散文**。**鎖讀不到散文，鎖只讀鎖**。⇒ 架構決策若允許某種重複，就必須把「為何允許」寫成**可被鎖引用的判準**
（本輪已補為 §7.3），否則它遲早會被別的鎖當成違規——而發現的時點是隨機的。

### 8.2 元層級：掃描面的 fail-open 讓 8.1 躲過**全部**把關（`DEF-101-752`）

`tools/tests/test_platform_utils_dedup.py:101` 用 `git ls-files "*.py"` 當掃描面 ⇒ **untracked 的 .py 天然不可見**。
`platform_caps.py` 在 R69 **全程都是 untracked**（新檔，直到收輪 `git add -A` 才入 index）。於是：

| 把關 | 次數／規模 | 對這個衝突的訊號 |
|------|-----------|-----------------|
| 四方複審 | **四輪 × 四方** | **零** |
| `python tools/run_root_unittests.py` 全套實跑（收尾者） | 多次，皆 `OK` | **零** |
| 各修復包自跑的單檔測試 | 數十次 | **零** |
| `git add -A` 之後的 pre-push | 1 次 | **紅** |

**四輪複審為何全部漏掉——機制解釋（不是「大家不夠仔細」）**：

1. **複審者與被審物之間隔著同一具載具**。四位審查員讀的是 diff 與測試結果；`platform_caps.py` 是 untracked，
   `git diff HEAD` 看不到它，測試也掃不到它。**它同時不在「人看的面」與「機器掃的面」上**——兩層防護的盲區
   在此**完全重疊**，而不是互補。這是本輪最該記住的一句：**兩道獨立的防線，如果盲區相同，等於只有一道**。
2. **鎖是「不存在性」斷言**，它的綠燈天然無法區分「真的沒有違規」與「沒看到違規」。`Ran 1581 … OK` 這個輸出，
   對「掃描面塌了一塊」與「掃描面完整且乾淨」**印出來的字一模一樣**。
3. **這個盲區在 repo 內是被當成「刻意取捨」記載的**：`tools/tests/test_extras_quoting_zsh_safety.py` 檔頭逐字寫著
   「未 tracked 的新檔在 `git add` 前掃不到（`git ls-files` 固有性質，**與 `test_platform_utils_dedup.py` 同政策**）」。
   ⇒ 任何複審者查到這裡，讀到的是「已知、已評估、已接受」，**追查就此停止**。**被寫成政策的缺陷，比沒被寫下的缺陷更難發現。**
4. **`git ls-files` 這個選擇當初有正當理由**（R57：排除 `AISDLC_SDD/` 下 4,800+ 支 venv/快取 `.py`），
   而那個理由**其實不需要 tracked-only**——`-o --exclude-standard` 靠 `.gitignore` 一樣排除得掉。
   ⇒ **手段被當成目的**：真正的需求是「排除 ignored」，實作卻選了「只要 tracked」，兩者的差集就是這個盲區。

**處置（本輪只修 3／14，其餘承接 R71）**：三處掃描面改為 **tracked ∪ untracked-not-ignored**；
盲區已封由 `TestScanSurfaceCoversUntrackedFiles` 以真實 untracked 探針證明——**同一支測試內對照兩個掃描面**
（修前的 tracked-only 看不到它／修後看得到且判紅）。只證後者是不夠的：掃描面被改回去時那種鎖不會說話。

### 8.3 對下一輪流程設計的具體建議（本節的目的）

1. **收輪前必跑一次「untracked 盤點」**：`git status --porcelain --untracked-files=all`。本輪若在四方複審**開始前**
   跑過一次並把 `platform_caps.py` 點名，四輪複審每一輪都會看到它。**這是零成本的**。
2. **複審任務書要載明「被審物有幾支還沒 `git add`」**。複審者不該需要自己去發現「我看到的 diff 不完整」。
3. **「不存在性鎖」一律要有掃描面自證**（掃描面規模下限／活體代表／注入探針）。本 repo 已有多處這麼做
   （`_MIN_SDD_SCRIPT_MODULES`、`_MIN_FILES`、`_MIN_SCANNED`），但**沒有一處自證涵蓋「untracked 這一整類」**——
   規模下限對它完全無感（少一支未追蹤檔，數字一樣達標）。
4. **repo 內每一處把盲區寫成「刻意取捨」的註解，都應附「若這個取捨錯了，代價長什麼樣」**。
   `test_extras_quoting_zsh_safety.py` 那句已於 R70 就地訂正並改寫掃描面。

---

## §9　收輪後（R70）：雲端 `windows-compat-ci` 的第三件事（`DEF-101-753`）

`edd5388` 押上 main 後，五支 workflow 中 **root-infra-ci／aisdlc-sdd-ci／AutoClaude CI／macos-compat-ci 皆 success，唯 `windows-compat-ci` failure**
（run `30739865214`，`Windows smoke` job 第 6 步 `FAILED (failures=3, skipped=52)`）。這是 §8 之外、**同樣在收輪後才顯形**的第三件事。

### 9.1 現象與根因

三支紅燈全在 `tools/tests/test_smoke_ci_sync.py::TestMacSmokeCliContract`，錯誤訊息本身就是證據：

```
AssertionError: 1 != 2 : W^@i^@n^@d^@o^@w^@s^@ ^@S^@u^@b^@s^@y^@s^@t^@e^@m^@ ^@f^@o^@r^@ ^@L^@i^@n^@u^@x^@ …
```

那是 **UTF-16LE** 的 `Windows Subsystem for Linux has no installed distributions.`——受測腳本 `macos_smoke_local.sh`
**一行都沒被執行**，測試卻把 WSL 啟動器的 rc 當成腳本的 rc 來斷言。

根因不是「PATH 順序讓 WSL 勝出」（這是動工前的假設，**實查後被推翻**），而是更硬的一條：
Windows 上 `subprocess` 以 `CreateProcess(lpApplicationName=NULL)` 解析裸名，搜尋順序是
「應用程式目錄 → 當前目錄 → **System32** → Windows 目錄 → **PATH**」——**System32 排在 PATH 之前**。
只要 argv[0] 是裸名 `"bash"`，`C:\Windows\System32\bash.exe` 就**必定**先命中，PATH 上排多前面的 Git Bash 都救不了。

**推翻假設的是同一次 CI run 內的天然對照組**：`test_dev_start.TestPickPythonGeMin` 用 `shutil.which("bash")`（只查 PATH），
在同一台機器上取得**真 Git Bash** 並全數通過；`test_smoke_ci_sync` 用字面值，取得 WSL 並三支全紅。
同機器、同 PATH、兩種解析路徑、相反結果 ⇒ 「PATH 上沒有 Git Bash」這個解釋被排除。

### 9.2 這一輪的主要價值不在修那三支

全樹掃描（三棵測試樹 + `.ps1` + workflow）另查出 **4 處同型站點**，其中
`AISDLC_SDD/scripts/tests/test_install_post_commit_windowsapps_guard.py` 的 `pytestmark` 只擋 `_PWSH is None`
＝**在 Windows runner 上必跑**，而它的 skipif reason 逐字寫著「Windows 上可由 Git-Bash 提供」——
**意圖與實作不符已寫在檔案裡好幾輪，沒有任何機械物看得到**。

另有 `tools/tests/test_macos_smoke_skip_honesty.py` 的 `_usable_bash()`：五份鏡射中**唯一漏掉 System32 段排除**的一份，
至今沒出事只因為「WSL 無發行版時驗活會 rc=1」——**fail-closed 的僥倖，不是設計**。機器一旦裝了發行版即失效。

### 9.3 落地

- **SSOT 收斂**：`tools/tests/` 內兩份 fixture 用途的探測複本（判準還不一致）＋ 本體檔的零探測，三處收斂為
  `_platform_helpers.usable_bash_for_fixture()`。比照 R57 `strip_ps_comments` 判例。
  **刻意不收斂**兩份生產端獨立重寫回歸鎖——那裡的獨立性本身就是鑑別力。
- **新鎖（本機 macOS 即可判紅）**：`TestWslStubIsNeverAcceptedAsRealBash` 注入**驗活會成功**但住在 `System32` 段的假 bash
  （刻意把 §9.2 那個「僥倖」拿掉，否則鎖到的不是路徑規則）；`TestNoBareBashInvocationInToolsTests` 以 AST 掃三棵測試樹，
  並追蹤三種間接形態（參數預設值／模組變數綁 `shutil.which`／整條 argv 變數）——只認 `run(["bash", …])` 的掃描器對本案原始形態全盲。
- **紅綠實測**：新鎖對 `edd5388` 工作樹判紅並逐一指名 11 處；全部處置後 `Ran 16 tests … OK (skipped=4)`。

### 9.4 與 §8 合看：連續三次「收輪後才顯形」

`DEF-101-751`／`752`／`753` 是同一輪收輪後接連冒出的三件事，且**失效機制各不相同**——
掃描面對 untracked 隱形（752）、不變量射程訂錯（751）、**本機平台根本重現不了**（753）。
第三件對流程的意涵最直接：`macos_smoke_local.sh` 這類腳本的 CLI 契約鎖，在 macOS 上永遠是綠的，
**四輪四方複審全部在一個看不到該缺陷的平台上進行**。§8.3 那四條建議（untracked 盤點、複審任務書載明未 add 檔數、
不存在性鎖要有掃描面自證、盲區註解要寫代價）對 753 全部無效——它需要的是**第五條**：

5. **凡「只在某平台才成立」的判斷，其回歸鎖必須有一條能在開發者本機重現該平台語意的路徑**（stub 注入、
   規則層純函式、AST 靜態掃描），否則該鎖的真實鑑別力等於零，且**沒有任何訊號告訴你它等於零**。
   本輪的兩道新鎖就是照這條做的：路徑規則以假 stub 在 macOS 上驗、呼叫形態以 AST 在任何平台上驗。


