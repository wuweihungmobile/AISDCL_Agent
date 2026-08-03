# AutoSDD_improving_99 — B 軌/ops：缺陷帳本瘦身（Defect Log 歸檔分檔 + 主表 SSOT 補全）

> **本輪柱別**：**B 軌（ops / 治理層工具摩擦清理）** 單柱聚焦——解 `myPrompt.md` 待辦 Q3「缺陷帳本太大（466KB）如何解決」。下一份：`AutoSDD_improving_100.md`。
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（整合迭代軌道①）。
> **日期**：2026-06-30　**掌舵者裁定本輪 W 方向**：B 軌/ops 缺陷帳本瘦身（AskUserQuestion 三選一，掌舵者選「缺陷帳本瘦身」）。
> **版本演化**：**無**——本輪只動 monorepo 根層 `docs/06_quality/`（整合層文件、可寫工作區），**零碰** AISDLC_SDD 凍結本體、零碰 AutoClaude 任何 `.py`/契約，故**不觸發 Copy-on-Evolve、不觸發五軌 TLC**。

---

## §1　本輪輸入（自上輪繼承）

### 1.1 improving_98 RTM / 實作順序遺留
- improving_98（commit fbf6f1d、tag v2026.06.30-49）已結案：DEF-62-001 真修＝Copy-on-Evolve v0.30 校正 auto_recovery 滯後註解；零退化 3607/0/122、ci-gate 雙軌 exit 0。
- improving_98 結案後一個 nightly-forensic chore（6f00833）。

### 1.2 myPrompt.md 待辦（掌舵者本輪輸入來源）
階段一發現 `docs/myPrompt.md` 有一筆未提交修改（` M`，掌舵者自行新增），底部「目前需確認或解決問題」列三項：
1. AutoClaude Nightly 是否繼續？→ **有**（最新 commit 6f00833＝nightly 取證落盤；地端 `tools/run_local_nightly.ps1` 依紀律持續）。
2. SD_Improving_09.md 執行完畢？可否推進？→ **W0 已結**（task list 22/22 CLOSED、五方終審 APPROVED 2026-05-20）；三觀察期 2026-06-17 到期、**W1（mutation pilot 擴展 GoalSynthesis）現符啟動資格**，惟有 TG「連續 7 次 ≥70% 鎖定」或「明確退出 pilot」二選一前置硬條件（ADR-SD09-002 §2.1.1）；W1~W6 未執行。
3. **缺陷帳本太大（466KB）→ 本輪 W 標的**。
> `myPrompt.md` 屬掌舵者個人工作筆記，**不納入本輪演化 commit**（依〈Source Control 處置慣例〉，由掌舵者自理）。

### 1.3 缺陷帳本 open/routed（階段一複驗，見 §2）
- 跨輪長青未結：DEF-01-007（open，cc-switch GUI 環境缺裝）、DEF-01-009（open watch，sdd_governance_plugin LOC，已自癒）、DEF-19-001（routed，結構天花板實質 closed）、DEF-23-005（routed，RFC 生命週期）、DEF-17-001（routed）、DEF-35-001（routed，C 軌 SD_09 W1）、DEF-25-001（wontfix）。
- DEF-62-001：上輪 fixed@improving_98。

---

## §2　階段一：現況重偵察（Zero-Trust Re-Audit 實測）

> 背景 audit agent 全程 Bash 工具實測（2026-06-30），**硬閘 OVERALL PASS**（九項全綠且 ≥ 上輪基線）；parent 複核無編造。

| 檢查 | 命令 | 實測 | 結論 |
|------|------|------|------|
| AutoClaude 全套 pytest | `python -m pytest tests/ -q`（AutoClaude/） | **3607 passed / 0 failed / 122 skipped**（70.80s） | ✅ ＝上輪基線 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（200 files / 504 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **0 violations**（19947 / cap 20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | OK | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | 真實 **exit 0**；雙軌 v0.01:1478 + v0.30:1665 + scripts/tests:130；LATEST=v0.30；FRAMEWORK_STATUS 新鮮；arch_fitness fail=0（2 advisory FF-16） | ✅ |

**本輪零退化 floor（禁寫死，取本表實測）**：AutoClaude pytest **≥ 3607 passed / 0 failed**；lint-imports 8 kept；LOC 0；AISDLC_SDD ci-gate exit 0（雙軌不變）。

### 2.1 缺陷帳本結構偵察（本輪 W 標的根因定位）
- 總量：**711 行 / 468KB**（單行極長＝中文長列；瓶頸是位元組數，超過 Read 工具 256KB 上限 → zero-trust 審計讀取摩擦＝**本輪 dogfooding 缺陷 DEF-99-001**）。
- 結構：(A) 1-21 標頭；(B) 22 行起「缺陷總表」主表（26-92 行，66 條 row-leading 列、約 122KB，每列含完整內聯修復證據）；(C) 93-711 行（約 346KB）＝各輪複驗/收尾敘事註記（rounds 24-63，2026-06-17~25）＋ 405 行起「臨時審查塊」（DEF-AGTREV-* 表，agent/* 符規審查，全 fixed@v0.18）。
- **關鍵發現（安全閘）**：主表**並非完整 SSOT**——row-leading 列從 DEF-30-001 直接跳 DEF-59-001，**DEF-31~58 區段及 DEF-25-001/32-002/35-001/62-001 等只活在敘事段、無主表列**。盲目歸檔 93-711 會使仍未結缺陷從 live 索引消失（資料遺失風險）→ **設計必須先把仍未結孤兒補進主表，才可歸檔敘事**（見 §3.2）。
- **機械依賴審查**：全 repo `grep` 確認**無任何程式 parse 此帳本**——`sdd_governance_plugin.py:10`、`integration_gate.ps1:13/80` 僅在註解/docstring 提及 DEF 編號字串，不讀檔內容。歸檔對程式零影響。

---

## §3　階段二：本輪增量設計

### 3.1 設計主張（一句話）
**把 93-711 行歷史敘事註記（rounds 24-63 複驗 + 臨時審查塊）原文搬到新檔 `AutoSDD_Defect_Log_archive_01.md`；搬移前先將仍未結（open/routed/wontfix）的孤兒缺陷補成主表列，使主表成為完整 live SSOT；主檔末加「歷史歸檔指標 + 歸檔輪替政策」。** 零程式變更、零碰 AISDLC_SDD/AutoClaude，純 monorepo 根 `docs/` markdown 重組。**只增不刪**：敘事原文逐字保全於 archive（搬移非刪除，git 亦保歷史）。

### 3.2 W 項
#### W-99-1：孤兒未結缺陷補進主表（SSOT 補全）
- 由 Explore agent 全檔判定每個孤兒缺陷最新權威狀態；**仍未結者**（open/routed/wontfix）補成主表 row-leading 列（沿用主表 7 欄格式，狀態取最新權威陳述 + 佐證載體）。
- **遷移清單（待 Explore agent 回報後填入，動實作前定稿）**：
  - 〔PENDING：DEF-25-001 / DEF-31-001 / DEF-32-002 / DEF-35-001 / DEF-37-001 / DEF-42-003 / DEF-53-001 各自最新狀態 → 仍未結者補列〕
- 已結（fixed@X）孤兒：純歷史，隨敘事歸檔，不補主表（archive 仍保全原文）。

#### W-99-2：歷史敘事歸檔 + 主檔指標
- 新建 `docs/06_quality/AutoSDD_Defect_Log_archive_01.md`：標頭說明（歸檔範圍 rounds 24-63 複驗註記 + 臨時審查塊；皆已被主表 live 狀態取代或為已結歷史；逐字搬移、只增不刪）+ 原 93-711 行內容。
- 主檔 `AutoSDD_Defect_Log.md`：保留 1-92（標頭 + 主表，含 W-99-1 補列）+ DEF-99-001 新列 + 末段「歷史複驗註記已歸檔」指標（連結 archive_01）+ **歸檔輪替政策**（主檔再逼近 256KB 時開 archive_02）。

#### W-99-3：DEF-99-001 入帳（B 軌 dogfooding 行進缺陷）
- 主表補 DEF-99-001 列：「帳本累積 468KB 超 Read 256KB 上限、zero-trust 審計讀取摩擦」｜P3｜ops 治理層｜**fixed@improving_99**（歸檔分檔 + 主表 SSOT 補全 + 輪替政策）。

### 3.3 介面 delta / LOC / importlinter 影響
| 項目 | delta | LOC tier | importlinter |
|------|-------|----------|--------------|
| 新增 `AutoSDD_Defect_Log_archive_01.md` | +1 markdown（原 93-711 行 + 歸檔標頭） | 非 AutoClaude scan | 零影響 |
| 改 `AutoSDD_Defect_Log.md` | 主表補孤兒列 + DEF-99-001 + 移除 93-711 改指標段 | 非 .py | — |
- **零碰**：AutoClaude（ports/plugins/core/infra/playbook_runner/PlaybookCheckpoint/DAL）全未觸；AISDLC_SDD 任一版本目錄全未觸；任何 `*.tla`/FSM `_HAPPY_PATH`/`.cfg` 全未觸。
- **Snapshot**：AutoClaude snapshot 不動（零碰 AutoClaude）。
- **Copy-on-Evolve**：**不觸發**（非框架本體修改，純整合層 docs）。

### 3.4 <Architecture_Design_Review>（寫實質變更前自我驗證）
1. **架構純潔性**：無新 God-object、無 Thin Facade 破壞——本輪零碰任何程式架構，純 docs 重組。
2. **持久化相容**：無新狀態、不碰 PlaybookCheckpoint、DAL 三後端零影響。
3. **安全防護網**：未新增「從文件生成指令」路徑；無 shell 注入面。
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑——無 allowlist/SSRF 考量。
5. **形式化同構**：純 markdown、零碰 `*.tla`/`_HAPPY_PATH`/`.cfg`/FSM → 五軌 TLC 不變式不受影響（N/A 第一型，git diff 為證）。
6. **資料保全（本輪特有風險）**：歸檔＝原文逐字搬移（非刪除）；遷移前先把仍未結孤兒補進主表 → live SSOT 完整、無未結缺陷從可讀區消失；diff 比對 archive 內容＝原 93-711 行逐字一致。

### 3.5 RTM 需求列（實測欄階段三/四回填）
| RTM | 需求 | 驗證 |
|-----|------|------|
| RTM-99-1 | 孤兒未結缺陷全數補成主表列、狀態取最新權威陳述（無誤判結/未結） | Explore agent 狀態判定 + 主表 grep 核對 |
| RTM-99-2 | `AutoSDD_Defect_Log_archive_01.md` 內容＝原 93-711 行逐字一致（只增不刪、零資料遺失） | diff 原檔該行段 vs archive 對應段 |
| RTM-99-3 | 主檔瘦身後 < 256KB、Read 工具可一次讀完；主表 SSOT 涵蓋全部 open/routed/wontfix | `wc -c` + Read 實測 + open/routed 集合 grep 核對 |
| RTM-99-4 | DEF-99-001 入帳 fixed@improving_99 | 主表 grep |
| RTM-99-5 | 零碰 AutoClaude/AISDLC_SDD/任何 .py/.tla（零退化、無 Copy-on-Evolve/TLC 觸發） | git diff 範圍核對 |
| RTM-99-6 | AutoClaude 零退化（≥3607 / lint 8 / LOC 0 / snapshot OK 維持） | 階段四真跑或 diff 證零碰 |

---

## §4　階段三：實作與雙重驗證（已完成）

### 4.1 遷移清單定稿（Explore agent 全檔判定 + parent 零信任核源）
- Explore agent 分段讀完整 468KB 檔，回報孤兒最新狀態；**parent 零信任校源抓出 agent 摘要 2 處 stale 誤判**並校正：
  1. **DEF-62-001**：agent 取帳本內 L97「維持 open」為最新——實為 improving_63 之**過時敘事**；權威最新＝上輪計畫書 **fixed@improving_98**（已校正）。
  2. **DEF-CLDREV-030**：agent 報 routed——直接讀 L632 實為 **fixed@v0.20**（improving_53 就地清償）→**不遷移**（已結）。
- 另直接核源確認 DEF-42-001/53-001 全 routed 無 fixed 取代；DEF-37-001 L290 是 routed 列（同列「fixed@improving_43」係交叉引用他缺陷），遷移時加註與 DEF-59-001 .gitignore 自動化家族重疊待複核。
- **定稿遷移＝7 孤兒列 + 1 本輪 DEF-99-001**：DEF-25-001(wontfix)、**DEF-37-001（初遷 routed→§4.4 audit 校正為 fixed@improving_43）**、DEF-42-001(routed)、DEF-42-003(wontfix)、DEF-52-006(wontfix)、DEF-53-001(routed)、DEF-62-001(**fixed@98** 校正帳本 stale)、DEF-99-001(本輪 fixed@99)。其中 5 未結（25-001/42-001/42-003/52-006/53-001）+ 2 已結補全/校正（37-001/62-001）。

### 4.2 實作（純 markdown 重組，sed 抽取 + cat 組裝，避 Bash here-string 陷阱）
- **新主檔**＝原 1-91 行（標頭 + 缺陷總表 66 列，**逐字不動**）+ 8 新主表列 + 「歷史複驗註記—已歸檔」指標段（含歸檔輪替政策）。
- **兩 archive 檔**（§4.4 F2 audit 後由單檔拆兩檔，確保各 < 256KB）：`AutoSDD_Defect_Log_archive_01.md`＝原 93-543 行（170KB）；`AutoSDD_Defect_Log_archive_02.md`＝原 544-711 行（179KB）。各帶歸檔標頭（含「現況以主檔為唯一權威」讀者須知）+ 原行段**逐字搬移**。
- **DEF-99-001 入帳**：主表新列，fixed@improving_99。

### 4.3 雙重驗證（純文件，行為突變不適用，改以差異/完整性/潔淨度四證）
| 驗證 | 命令 | 結果 |
|------|------|------|
| 主表 SSOT 零變更 | `diff <(sed -n '1,91p' ORIG) <(sed -n '1,91p' 新主檔)` | **IDENTICAL** ✓（缺陷總表 66 列原封不動） |
| 歸檔逐字一致（只增不刪、零資料遺失，RTM-99-2） | `diff <(archive_01 去標頭) <(原 93-543)`、`diff <(archive_02 去標頭) <(原 544-711)` | 兩檔皆 **VERBATIM IDENTICAL** ✓ |
| 主表涵蓋全部未結缺陷（完整 live SSOT，RTM-99-1/3） | open/routed/wontfix ID `grep -cE '^\| ID '` | 全部 **=1** ✓（既有 DEF-01-007/009、17/19/23-005/76-001 + 新補 5 未結 25-001/42-001/42-003/52-006/53-001；DEF-37-001/62-001 補為已結） |
| 三檔皆瘦身可讀（RTM-99-3，含 §4.4 F2） | `wc -c` + Read | 主檔 477,861→**128,261（125KB）**、archive_01 **174,948（170KB）**、archive_02 **183,179（179KB）**，**三檔皆 < 256KB** ✓，Read 一次讀完、表格未破欄 |
| 零碰程式/框架（RTM-99-5） | `git status --short` | 僅 ` M docs/06_quality/AutoSDD_Defect_Log.md` + 4 新增 md（archive_01/02 + 計畫書 + 審計報告）；**零碰** AutoClaude/AISDLC_SDD/任何 `.py`/`.tla` ✓（`docs/myPrompt.md` 為掌舵者個人筆記、非本輪產） |

### 4.4 多專家 audit 驅動之校正（findings → 徹底修完 → 複審）
Architect + SA-SD 雙鏡 zero-trust 複審獨立抓出 2 項，已當輪修完：
- **F1（P2，狀態誤判）**：DEF-37-001 初遷標 `routed`，但原 L290（archive_01 內）權威狀態實為 **`fixed@improving_43`**（improving_43 新增 shared-infra `gitignore_coverage_lint.py` + 12 case + ci-gate 接線，結構性結案）；我階段三零信任只讀 L290 前 600 字、剛好截在 fixed 之前致誤判，違反「不改判定僅遷移」。**已修**：主表 DEF-37-001 改 `fixed@improving_43` + 註明 audit 校正；指標段未結清單移除之；DEF-99-001 列校正計數。
- **F2（P3，徹底性）**：原單一 archive 達 356KB 自身仍 > 256KB Read 上限。**已修**：拆 archive_01（93-543, 170KB）+ archive_02（544-711, 179KB），各 < 256KB；輪替政策補「主檔與每一 archive 皆 < 256KB 為界」。
- 兩鏡其餘所有主張（diff 逐字一致、SSOT 涵蓋、git 潔淨、程式零影響、6/7 遷移列狀態正確）經獨立核源屬實。

---

## §5　階段四：CI 平價收斂 — 零退化驗證矩陣（實測）

> **本輪性質**：純 monorepo 根 `docs/06_quality/` markdown 重組，**git diff 鐵證零碰任何 `.py`/`.tla`/框架本體**。故所有程式/框架閘屬 **N/A 第一型**（條件未觸發、本輪確實未跑；附 git diff 鐵證），floor 取階段一本 session 實測基線（非寫死）。**不重跑**＝避免對 provably markdown-only 變更做驗證劇場（無法揭露不存在的回歸），符誠實 N/A 紀律。

| 檢查 | 命令 | 通過條件（floor 取 §2 實測） | 實測 |
|------|------|------------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3607 passed / 0 failed | **N/A 第一型**（git diff 證零碰 AutoClaude 任何 `.py`/測試；階段一本 session 基線＝3607 passed / 0 failed / 122 skipped，未被本輪觸動） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | **N/A 第一型**（零碰 import 結構；階段一＝8 kept / 0 broken） |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **N/A 第一型**（零碰 `.py`；階段一＝0 violations。本輪改的是 `docs/` markdown，不在 LOC scan） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **N/A 第一型**（零碰 AutoClaude，snapshot 來源不變；階段一＝OK） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌 exit 0 | **N/A 第一型**（git diff 證零碰 AISDLC_SDD 任一版本目錄；階段一本 session＝真實 exit 0、雙軌 v0.01:1478+v0.30:1665+scripts:130、LATEST=v0.30、FRAMEWORK_STATUS 新鮮） |
| DAL 等價 | equivalence job | 三後端等價 | **N/A 第一型**（本輪無新 DAL/checkpoint 改動、零碰 `.py`；git diff 為證） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 第一型**（git diff 證零碰任何 `*.tla`/`.cfg`/`_HAPPY_PATH`/FSM；純 markdown） |

> **N/A 第一型總鐵證**：`git status --short` 僅 ` M docs/06_quality/AutoSDD_Defect_Log.md` + `?? docs/06_quality/AutoSDD_Defect_Log_archive_01.md` + `?? docs/04_planning/AutoSDD_improving_99.md`——三者皆 monorepo 根 `docs/` markdown，**無任何 `.py`/`.tla`/框架本體/AutoClaude/AISDLC_SDD 版本目錄變更**，故零退化由「零碰觸發路徑」結構性保證，非靠重跑。

---

## §6　缺陷帳本本輪處置
- **DEF-99-001**：本輪 dogfooding 新缺陷（帳本體積摩擦），fixed@improving_99（歸檔分檔 + SSOT 補全）。
- 孤兒未結缺陷：補主表列、維持各自最新狀態（不改判定，僅遷移至 live SSOT）。
- DEF-62-001（fixed@98）/ 各長青 open/routed：狀態不變，僅確保主表有列。

---

## §7　Copy-on-Evolve / 版本演化
- **本輪無版本演化**：純 monorepo 根 `docs/06_quality/` markdown 重組，零碰框架本體。
- TLC：N/A 第一型（純 markdown、零碰形式化模型，git diff 證）。

---

## §8　誠實性標記
- 本檔於**階段二先落地**（§1/§2/§3 規格先行，含 `<Architecture_Design_Review>`/介面 delta/RTM）；§3.2 遷移清單待 Explore agent 全檔狀態判定後定稿再動實作；§4/§5 實測欄階段三/四回填。
- 安全閘誠實標記：階段二發現「主表非完整 SSOT」風險，**設計已從『盲目歸檔』修正為『先補 SSOT 再歸檔』**，避免未結缺陷資料遺失。
- 本輪柱別＝**B 軌（ops 治理層工具摩擦清理）**；解 myPrompt.md Q3。
